"""KITAP_AUDIT_2 Adım 3: `ceiling_hazard_v0` sıfırdan (borsai import edilmez).

Girdi: data/training_table.csv, MASTER csv (ipo_size_tl), sessions csv (yalnız ticker/session_number/target_session_date),
models/*.json (karşılaştırma için), registry/inputs/NETGL.json, altın ledger (kalibrasyon).
Yalnız stdlib + numpy (çözücü). Ticker adı dışında kasa kodu yok (H99 açık kohort).
"""
import csv, json, math, sys
from decimal import Decimal, Context, ROUND_HALF_EVEN, ROUND_HALF_UP, localcontext
from fractions import Fraction
from pathlib import Path
import numpy as np

ROOT = Path('/Users/ahmet/Desktop/BorsAi')
OUT = {}

def rd(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

table = rd(ROOT / 'data/training_table.csv')
master = {r['ticker']: r for r in rd(ROOT / 'data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv')}
sess = {}
for r in rd(ROOT / 'data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv'):
    sess.setdefault(r['ticker'], {})[int(r['session_number'])] = r['target_session_date']

# ---------------- özellikler (features.py tanımı: f1 = ipo_size_tl varsa o, yoksa fiyat×pay; f2 = pay/sermaye×100, 10 ondalık HALF_UP)
LEG = Context(prec=28, rounding=ROUND_HALF_EVEN)
Q10 = Decimal(1).scaleb(-10)
def pct(num, den):
    with localcontext(LEG):
        raw = num / den * Decimal(100)
        s = format(raw.quantize(Q10, rounding=ROUND_HALF_UP), 'f').rstrip('0').rstrip('.')
    return Decimal(s or '0')

rows = []
for r in table:
    t = r['ticker']
    size_src = master[t]['ipo_size_tl'].strip()
    price, shares = Decimal(r['ipo_price_tl']), Decimal(r['shares_offered'])
    f1 = Decimal(size_src) if size_src else price * shares
    f2 = pct(shares, Decimal(r['post_ipo_share_capital']))
    f3 = Decimal(r['total_demand_multiple']) if r['total_demand_multiple'].strip() else None
    L = int(r['ceiling_streak_L'])
    closes = [int(r[f'ceiling_close_D{k}']) for k in range(1, 11)]
    assert L == next((i for i, c in enumerate(closes) if c == 0), 10)
    rows.append(dict(ticker=t, ftd=r['first_trading_date'], f1=f1, f2=f2, f3=f3, L=L, closes=closes,
                     dates=[sess[t][k] for k in range(1, 11)], size_from_master=bool(size_src),
                     diff_size=(Decimal(size_src) - price * shares) if size_src else None))
assert len(rows) == 99 and [(r['ftd'], r['ticker']) for r in rows] == sorted((r['ftd'], r['ticker']) for r in rows)
OUT['f1_from_master_n'] = sum(r['size_from_master'] for r in rows)
OUT['f1_master_ne_price_x_shares'] = [(r['ticker'], str(r['diff_size'])) for r in rows if r['diff_size'] is not None and r['diff_size'] != 0]

# ---------------- PP tablosu
def pp_rows(r, cutoff=None):
    out = []
    for d in range(1, 11):
        if d - 1 > r['L']:
            break
        if cutoff is not None and r['dates'][d - 1] >= cutoff:
            break
        out.append((d, 0 if d == 1 else (1 if d <= 3 else 2), int(r['L'] == d - 1)))
    return out

def day_table(rs):
    risk = [0] * 11; ev = [0] * 11
    for r in rs:
        for d, g, e in pp_rows(r):
            risk[d] += 1; ev[d] += e
    return risk[1:], ev[1:]

risk99, ev99 = day_table(rows)
OUT['pp_99'] = dict(risk=risk99, events=ev99, n_rows=sum(risk99), n_events=sum(ev99),
                    hazard=[round(e / n, 3) for e, n in zip(ev99, risk99)],
                    groups={'g1': (risk99[0], ev99[0]), 'g2': (sum(risk99[1:3]), sum(ev99[1:3])), 'g3': (sum(risk99[3:]), sum(ev99[3:]))})
train = [r for r in rows if r['f3'] is not None]
assert len(train) == 97
risk97, ev97 = day_table(train)
OUT['pp_97'] = dict(risk=risk97, events=ev97, n_rows=sum(risk97), n_events=sum(ev97), n_survivals=sum(risk97) - sum(ev97),
                    groups={'g1': (risk97[0], ev97[0]), 'g2': (sum(risk97[1:3]), sum(ev97[1:3])), 'g3': (sum(risk97[3:]), sum(ev97[3:]))},
                    excluded=[r['ticker'] for r in rows if r['f3'] is None], excluded_L=[r['L'] for r in rows if r['f3'] is None])
# g3 içi gün heterojenliği (Pearson ki-kare, 97 eğitim kümesi)
p3 = sum(ev97[3:]) / sum(risk97[3:])
chi = sum((e - n * p3) ** 2 / (n * p3 * (1 - p3)) for e, n in zip(ev97[3:], risk97[3:]))
OUT['g3_day_heterogeneity_chi2_df6'] = chi
p2 = sum(ev97[1:3]) / sum(risk97[1:3])
OUT['g2_day_heterogeneity_chi2_df1'] = sum((e - n * p2) ** 2 / (n * p2 * (1 - p2)) for e, n in zip(ev97[1:3], risk97[1:3]))

# ---------------- Kaplan–Meier (99 arz) -> base_km_expanding / base_km_last10
km_exp_h = [e / n for e, n in zip(ev99, risk99)]
def surv(h):
    out = []; s = 1.0
    for x in h:
        s *= (1 - x); out.append(s)
    return out
km_exp_S = surv(km_exp_h)
km10_h = []
for d in range(1, 11):
    day = sorted(((r['ftd'], r['ticker'], e) for r in rows for dd, g, e in pp_rows(r) if dd == d))[-10:]
    km10_h.append(sum(e for _, _, e in day) / len(day))
km10_S = surv(km10_h)
jkm = json.load(open(ROOT / 'models/base_km_expanding.json'))['survival']['S']
jkm10 = json.load(open(ROOT / 'models/base_km_last10.json'))['survival']['S']
OUT['km_expanding_maxdiff'] = max(abs(a - b) for a, b in zip(km_exp_S, jkm))
OUT['km_last10_maxdiff'] = max(abs(a - b) for a, b in zip(km10_S, jkm10))
OUT['km_expanding_S'] = [round(x, 4) for x in km_exp_S]
OUT['km_last10_S'] = [round(x, 4) for x in km10_S]
OUT['km_cont_j3'] = dict(S4_over_S3=km_exp_S[3] / km_exp_S[2], risk_d4=risk99[3], cont_d4=risk99[3] - ev99[3])
OUT['km_cont_j6'] = dict(S7_over_S6=km_exp_S[6] / km_exp_S[5], risk_d7=risk99[6], cont_d7=risk99[6] - ev99[6])
OUT['km_cont_j0'] = dict(S1=km_exp_S[0], risk_d1=risk99[0], cont_d1=risk99[0] - ev99[0])

# ---------------- ön işleme (CEILING tarifi: f3 winsor type-7 Fraction; f1 ln Decimal 60; z nüfus std ddof=0)
CTX60 = Context(prec=60, rounding=ROUND_HALF_EVEN)
CTX28 = Context(prec=28, rounding=ROUND_HALF_EVEN)
def q7(sorted_vals, p):
    n = len(sorted_vals)
    h = Fraction(n - 1) * p + 1
    lo = h.numerator // h.denominator
    frac = h - lo
    if lo == n:
        return sorted_vals[lo - 1]
    return sorted_vals[lo - 1] + frac * (sorted_vals[lo] - sorted_vals[lo - 1])

def fit_prep(rs):
    n = len(rs)
    f3s = sorted(Fraction(r['f3']) for r in rs)
    lo, hi = q7(f3s, Fraction(1, 20)), q7(f3s, Fraction(19, 20))
    exact = {r['ticker']: {'f2': Fraction(r['f2']), 'f3': min(max(Fraction(r['f3']), lo), hi)} for r in rs}
    with localcontext(CTX60):
        logs = {r['ticker']: Decimal(r['f1']).ln() for r in rs}
        mean1 = sum(logs.values(), Decimal(0)) / Decimal(n)
        var1 = sum(((v - mean1) ** 2 for v in logs.values()), Decimal(0)) / Decimal(n)
        std1 = var1.sqrt()
    prep = {'winsor': (lo, hi), 'mean': {'f1': mean1}, 'std': {'f1': std1}, 'mean_exact': {}, 'z': {t: {} for t in logs}}
    for t in logs:
        with localcontext(CTX28):
            diff = logs[t] - mean1
        with localcontext(CTX60):
            prep['z'][t]['f1'] = float(diff / std1)
    for col in ('f2', 'f3'):
        vals = [exact[r['ticker']][col] for r in rs]
        mean = sum(vals, Fraction(0)) / n
        var = sum(((v - mean) ** 2 for v in vals), Fraction(0)) / n
        with localcontext(CTX60):
            vdec = Decimal(var.numerator) / Decimal(var.denominator)
            std = vdec.sqrt()
            prep['mean'][col] = Decimal(mean.numerator) / Decimal(mean.denominator)
        prep['std'][col] = std
        prep['mean_exact'][col] = mean
        for r in rs:
            dnum = exact[r['ticker']][col] - mean
            with localcontext(CTX60):
                ddec = Decimal(dnum.numerator) / Decimal(dnum.denominator)
                prep['z'][r['ticker']][col] = float(ddec / std)
    return prep

def transform(prep, f1, f2, f3):
    lo, hi = prep['winsor']
    f3c = min(max(Fraction(f3), lo), hi)
    z = {}
    with localcontext(CTX60):
        l1 = Decimal(f1).ln()
    with localcontext(CTX28):
        diff = l1 - prep['mean']['f1']
    with localcontext(CTX60):
        z['f1'] = float(diff / prep['std']['f1'])
    for col, v in (('f2', Fraction(f2)), ('f3', f3c)):
        dnum = v - prep['mean_exact'][col]
        with localcontext(CTX60):
            z[col] = float((Decimal(dnum.numerator) / Decimal(dnum.denominator)) / prep['std'][col])
    return z, f3c != Fraction(f3)

prep = fit_prep(train)
J = json.load(open(ROOT / 'models/ceiling_hazard_v0.json'))
jp = J['preprocessing']
OUT['prep_vs_json'] = {
    'winsor_p05': (float(prep['winsor'][0]), jp['winsor']['f3']['p05']), 'winsor_p95': (float(prep['winsor'][1]), jp['winsor']['f3']['p95']),
    'mean': {c: (float(prep['mean'][c]), jp['mean'][c]) for c in ('f1', 'f2', 'f3')},
    'std': {c: (float(prep['std'][c]), jp['std'][c]) for c in ('f1', 'f2', 'f3')},
}
OUT['prep_maxdiff'] = max(abs(a - b) for pair in [OUT['prep_vs_json']['winsor_p05'], OUT['prep_vs_json']['winsor_p95']] + list(OUT['prep_vs_json']['mean'].values()) + list(OUT['prep_vs_json']['std'].values()) for a, b in [pair])

# ---------------- model: Newton–Raphson, L2 yalnız β, pseudo-satırlar
COLS = ('f1', 'f2', 'f3')
def closed_gamma(ev, risk):
    return math.log((ev + 0.5) / (risk - ev + 0.5))

def build(rs, prep, cutoff=None):
    G, Z, E = [], [], []
    for r in rs:
        for d, g, e in pp_rows(r, cutoff):
            G.append(g); Z.append([prep['z'][r['ticker']][c] for c in COLS]); E.append(e)
    return np.array(G), np.array(Z, dtype=float).reshape(len(G), 3), np.array(E, dtype=float)

def fit(G, Z, E, lam, tol=1e-10, max_iter=100):
    ev = np.bincount(G, weights=E, minlength=3); risk = np.bincount(G, minlength=3)
    gamma0 = np.array([closed_gamma(int(ev[g]), int(risk[g])) for g in range(3)])
    if lam == math.inf:
        return gamma0, np.zeros(3), 0, 0.0
    Gp = np.concatenate([G, [0, 0, 1, 1, 2, 2]]); Ep = np.concatenate([E, [1, 0, 1, 0, 1, 0]])
    W = np.concatenate([np.ones(len(G)), np.full(6, 0.5)]); Zp = np.vstack([Z, np.zeros((6, 3))])
    X = np.hstack([np.eye(3)[Gp], Zp])
    pen = np.array([0, 0, 0, lam, lam, lam], dtype=float)
    theta = np.concatenate([gamma0, np.zeros(3)])
    def obj(th):
        eta = X @ th
        return float(np.sum(W * (np.logaddexp(0, eta) - Ep * eta))) + 0.5 * lam * float(th[3:] @ th[3:])
    Jv = obj(theta); eps = np.finfo(float).eps * len(Ep)
    for it in range(max_iter + 1):
        h = 1 / (1 + np.exp(-(X @ theta)))
        grad = X.T @ (W * (h - Ep)) + pen * theta
        gm = float(np.max(np.abs(grad)))
        if gm <= tol:
            return theta[:3], theta[3:], it, gm
        H = (X * (W * h * (1 - h))[:, None]).T @ X + np.diag(pen)
        delta = np.linalg.solve(H, grad)
        step = 1.0
        for _ in range(31):
            cand = theta - step * delta; Jn = obj(cand)
            if Jn <= Jv + eps * max(abs(Jv), 1.0):
                break
            step *= 0.5
        theta, Jv = cand, Jn
    raise RuntimeError('yakınsamadı')

G, Z, E = build(train, prep)
assert len(E) == 506 and int(E.sum()) == 83
gamma, beta, it, gm = fit(G, Z, E, 10.0)
OUT['final_fit'] = dict(gamma=gamma.tolist(), beta=beta.tolist(), iterations=it, grad_max=gm,
                        json_gamma=J['gamma'], json_beta=[J['beta'][c] for c in COLS],
                        maxdiff=max(max(abs(gamma - np.array(J['gamma']))), max(abs(beta - np.array([J['beta'][c] for c in COLS])))))
# in-sample grup kalibrasyonu (skor denklemi: Σ_g (h − e) = 0, pseudo dahil)
h_in = 1 / (1 + np.exp(-(gamma[G] + Z @ beta)))
OUT['insample_group_calibration'] = {f'g{g+1}': dict(mean_h=float(h_in[G == g].mean()), event_rate=float(E[G == g].mean()), n=int((G == g).sum())) for g in range(3)}
# λ = INF
gI, _, _, _ = fit(G, Z, E, math.inf)
JI = json.load(open(ROOT / 'models/ceiling_hazard_v0@INF.json'))
OUT['inf_fit'] = dict(gamma=gI.tolist(), json_gamma=JI['gamma'], maxdiff=float(np.max(np.abs(gI - np.array(JI['gamma'])))),
                      hazards=[1 / (1 + math.exp(-x)) for x in gI])
# reclose oranları
n_a = a_a = n_b = a_b = 0
for r in train:
    for k in range(2, 11):
        if r['L'] < k:
            if k <= 4: n_a += 1; a_a += r['closes'][k - 1]
            else: n_b += 1; a_b += r['closes'][k - 1]
OUT['reclose'] = dict(mine=(n_a, a_a, n_b, a_b, (a_a + 0.5) / (n_a + 1), (a_b + 0.5) / (n_b + 1)),
                      json=(J['reclose_rates']['n_a'], J['reclose_rates']['a_a'], J['reclose_rates']['n_b'], J['reclose_rates']['a_b'], J['reclose_rates']['r_a'], J['reclose_rates']['r_b']))

# ---------------- iç arz-bırak CV skor tablosu (λ seçimi)
GRID = (0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, math.inf)
if '--cv' in sys.argv:
    tot = {l: 0.0 for l in GRID}; m = 0
    for j in train:
        inner = [r for r in train if r['ticker'] != j['ticker']]
        pj = fit_prep(inner)
        Gi, Zi, Ei = build(inner, pj)
        zj, _ = transform(pj, j['f1'], j['f2'], j['f3'])
        Gj = np.array([g for d, g, e in pp_rows(j)]); Ej = np.array([e for d, g, e in pp_rows(j)], dtype=float)
        zjv = np.array([zj[c] for c in COLS])
        for lam in GRID:
            ga, be, _, _ = fit(Gi, Zi, Ei, lam)
            h = np.clip(1 / (1 + np.exp(-(ga[Gj] + zjv @ be))), 1e-12, 1 - 1e-12)
            tot[lam] += float(-np.sum(Ej * np.log(h) + (1 - Ej) * np.log(1 - h)))
        m += len(Ej)
    mine = {('INF' if l == math.inf else l): tot[l] / m for l in GRID}
    js = {e['lambda']: e['score'] for e in J['lambda_score_table']}
    OUT['cv_table'] = {str(k): (mine[k], js[k], mine[k] - js[k]) for k in mine}
    OUT['cv_maxdiff'] = max(abs(mine[k] - js[k]) for k in mine)
    OUT['cv_selected'] = max((k for k in mine if mine[k] == min(mine.values())), key=lambda k: (math.inf if k == 'INF' else k))

# ---------------- NETGL
inp = json.load(open(ROOT / 'registry/inputs/NETGL.json'))['fields']
v = lambda k: Decimal(inp[k]['value'])
f1n = v('ipo_size_tl'); f2n = pct(v('shares_offered'), v('post_ipo_share_capital')); f3n = v('total_demand_multiple')
zn, clipped = transform(prep, f1n, f2n, f3n)
lin = sum(beta[i] * zn[c] for i, c in enumerate(COLS))
eta = [gamma[0] + lin] + [gamma[1] + lin] * 2 + [gamma[2] + lin] * 7
hz = [1 / (1 + math.exp(-x)) for x in eta]
S = surv(hz)
PL = [1 - S[0]] + [S[l - 1] - S[l] for l in range(1, 10)] + [S[9]]
rec = json.load(open(ROOT / 'registry/records/NETGL/20260922T121936Z_65a39d7392dd.json'))
recS = [e for e in rec['models'] if e['model_id'] == 'ceiling_hazard_v0'][0]['output']['S']
EL = sum(S)
cum = np.cumsum(PL)
OUT['netgl'] = dict(
    f1=str(f1n), f2=str(f2n), f3=str(f3n), z=zn, clipped=clipped, beta_dot_z=lin, eta_groups=[eta[0], eta[1], eta[3]],
    hazards=[hz[0], hz[1], hz[3]], S=S, S_record_maxdiff=max(abs(a - b) for a, b in zip(S, recS)), P_L=PL,
    E_L=EL, mode_l=int(np.argmax(PL)), median_first_cum_ge_half=int(next(i for i, c in enumerate(cum) if c >= 0.5)),
    cont_j0=S[0], cont_j3=S[3] / S[2], cont_j6=S[6] / S[5], cont_j4=S[4] / S[3], cont_j9=S[9] / S[8],
    remaining_j3=sum(S[3:]) / S[2], cond_median_j3=None, p_ge5_given_ge3=S[4] / S[2], p_eq10_given_ge3=S[9] / S[2],
    rps_L3=sum((S[k] - (1.0 if 3 >= k + 1 else 0.0)) ** 2 for k in range(10)) / 10,
)
# koşullu medyan j=3: P(L=l | L≥3) birikimli ≥ 0.5 olan ilk l
condPL = [PL[l] / S[2] for l in range(3, 11)]
cc = np.cumsum(condPL); OUT['netgl']['cond_median_j3'] = 3 + int(next(i for i, c in enumerate(cc) if c >= 0.5))
for name, mdl in (('@INF', 'ceiling_hazard_v0@INF'), ('km_exp', 'base_km_expanding'), ('km10', 'base_km_last10')):
    Sx = [e for e in rec['models'] if e['model_id'] == mdl][0]['output']['S']
    OUT['netgl'][f'rps_L3_{name}'] = sum((Sx[k] - (1.0 if 3 >= k + 1 else 0.0)) ** 2 for k in range(10)) / 10
OUT['netgl']['avg_ipo_g3_cont'] = 1 - 1 / (1 + math.exp(-gamma[2]))
OUT['netgl']['km_g3_cont_pooled'] = 1 - sum(ev99[3:]) / sum(risk99[3:])
OUT['netgl']['km97_g3_cont_pooled'] = 1 - sum(ev97[3:]) / sum(risk97[3:])

# ---------------- altın ledger kalibrasyonu (walk-forward, 87 fold)
led = rd(ROOT / 'tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv')
led = [r for r in led if r['status'] == 'FIT_OK']
assert len(led) == 87
grp = {g: {'pred': [], 'ev': []} for g in (0, 1, 2)}
byday = {d: {'pred': [], 'ev': []} for d in range(1, 11)}
cont = {}
for r in led:
    L = int(r['realized_L']); S_ = [float(r[f'S_{k}']) for k in range(1, 11)]
    for d in range(1, 11):
        if d - 1 > L: break
        g = 0 if d == 1 else (1 if d <= 3 else 2)
        pr = float(r[f'hazard_{d}']); e = int(L == d - 1)
        grp[g]['pred'].append(pr); grp[g]['ev'].append(e); byday[d]['pred'].append(pr); byday[d]['ev'].append(e)
    for j in (0, 1, 2, 3, 4, 5, 6):
        if L >= j:
            cont.setdefault(j, {'pred': [], 'obs': []})
            cont[j]['pred'].append(S_[j] / (S_[j - 1] if j > 0 else 1.0)); cont[j]['obs'].append(int(L >= j + 1))
OUT['ledger_group_calibration'] = {f'g{g+1}': dict(n=len(grp[g]['pred']), mean_pred_hazard=float(np.mean(grp[g]['pred'])), event_rate=float(np.mean(grp[g]['ev']))) for g in (0, 1, 2)}
OUT['ledger_day_calibration'] = {d: dict(n=len(byday[d]['pred']), mean_pred=float(np.mean(byday[d]['pred'])), obs=float(np.mean(byday[d]['ev']))) for d in range(1, 11)}
OUT['ledger_continuation_j'] = {j: dict(n=len(cont[j]['pred']), mean_pred=float(np.mean(cont[j]['pred'])), obs=float(np.mean(cont[j]['obs'])), obs_count=f"{sum(cont[j]['obs'])}/{len(cont[j]['obs'])}") for j in sorted(cont)}
# fold başına hazard sabitliği (g3)
OUT['ledger_g3_constant_all_folds'] = all(len({r[f'hazard_{d}'] for d in range(4, 11)}) == 1 for r in led)
OUT['ledger_selected_lambda_counts'] = {}
for r in led:
    OUT['ledger_selected_lambda_counts'][r['selected_lambda']] = OUT['ledger_selected_lambda_counts'].get(r['selected_lambda'], 0) + 1

def conv(o):
    if isinstance(o, (np.floating, np.integer)): return o.item()
    if isinstance(o, dict): return {str(k): conv(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [conv(x) for x in o]
    if isinstance(o, (Decimal, Fraction)): return str(o)
    return o
print(json.dumps(conv(OUT), indent=1, ensure_ascii=False))

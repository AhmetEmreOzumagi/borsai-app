"""KITAP_AUDIT_2 Adım 5: diğer ailelerin nihai fit'lerini sıfırdan yeniden yap (borsai import edilmez; numpy yalnız çözücü).
Aileler: v1_5_h99 (Ridge kapalı biçim + L2-lojistik Newton), v1_6_h99 D10 Ridge, pb_v0 D5, pb_ceiling_v0, ceiling_hazard_v1_clip/real/pooled(+@INF),
fall_d10_v0_h99/pooled/addsale/@ZERO. Açık küme ticker'ları hiçbir yere yazılmaz (yalnız sayı)."""
import csv, json, math
from decimal import Decimal, Context, ROUND_HALF_EVEN, ROUND_HALF_UP, localcontext
from fractions import Fraction
from pathlib import Path
import numpy as np
ROOT = Path('/Users/ahmet/Desktop/BorsAi')
CTX60 = Context(prec=60, rounding=ROUND_HALF_EVEN); CTX28 = Context(prec=28, rounding=ROUND_HALF_EVEN); LEG = CTX28
Q10 = Decimal(1).scaleb(-10)
OUT = {}
def rd(p):
    with open(p, encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def pct(num, den):
    with localcontext(LEG):
        raw = num / den * Decimal(100)
        s = format(raw.quantize(Q10, rounding=ROUND_HALF_UP), 'f').rstrip('0').rstrip('.')
    return Decimal(s or '0')
def q7(sv, p):
    n = len(sv); h = Fraction(n - 1) * p + 1; lo = h.numerator // h.denominator; fr = h - lo
    return sv[lo - 1] if lo == n else sv[lo - 1] + fr * (sv[lo] - sv[lo - 1])
def frac2dec(x):
    with localcontext(CTX60): return Decimal(x.numerator) / Decimal(x.denominator)

# ---------- genel ön işleme (preprocess.py tarifleri): winsor (Fraction type-7), log (Decimal 60, 28-haneli çıkarma), z (nüfus std)
def fit_prep(raw, cols, winsor=(), log=(), impute=(), indicator=False):
    """raw: ticker -> {col: Decimal|Fraction|None}. impute: medyanla doldurulan sütunlar (V1.5 f3); indicator: f5."""
    tick = list(raw); n = len(tick)
    exact = {t: {} for t in tick}; wins = {}; meds = {}
    for c in cols:
        vals = {t: Fraction(raw[t][c]) for t in tick if raw[t].get(c) is not None}
        if c in winsor:
            sv = sorted(vals.values()); lo, hi = q7(sv, Fraction(1, 20)), q7(sv, Fraction(19, 20)); wins[c] = (lo, hi)
            vals = {t: min(max(v, lo), hi) for t, v in vals.items()}
        if c in impute and len(vals) < n:
            o = sorted(vals.values()); m = len(o); med = o[m // 2] if m % 2 else (o[m // 2 - 1] + o[m // 2]) / 2; meds[c] = med
        for t in tick:
            exact[t][c] = vals.get(t, meds.get(c))
    if indicator:
        for t in tick: exact[t]['f5'] = Fraction(0 if raw[t].get('f3') is not None else 1)
    allc = list(cols) + (['f5'] if indicator else [])
    prep = {'cols': allc, 'winsor': wins, 'med': meds, 'log': log, 'mean': {}, 'std': {}, 'mean_exact': {}, 'z': {t: {} for t in tick}}
    for c in allc:
        if c in log:
            with localcontext(CTX60):
                lv = {t: frac2dec(exact[t][c]).ln() for t in tick}
                mean = sum(lv.values(), Decimal(0)) / Decimal(n); var = sum(((v - mean) ** 2 for v in lv.values()), Decimal(0)) / Decimal(n); std = var.sqrt()
            prep['mean'][c], prep['std'][c] = mean, std
            for t in tick:
                with localcontext(CTX28): d = lv[t] - mean
                with localcontext(CTX60): prep['z'][t][c] = float(d / std)
        else:
            vals = [exact[t][c] for t in tick]; mean = sum(vals, Fraction(0)) / n; var = sum(((v - mean) ** 2 for v in vals), Fraction(0)) / n
            with localcontext(CTX60): std = frac2dec(var).sqrt()
            prep['mean'][c], prep['std'][c], prep['mean_exact'][c] = frac2dec(mean), std, mean
            for t in tick:
                with localcontext(CTX60): prep['z'][t][c] = float(frac2dec(exact[t][c] - mean) / std)
    return prep
def transform(prep, raw1):
    z = {}
    for c in prep['cols']:
        if c == 'f5': v = Fraction(0 if raw1.get('f3') is not None else 1)
        else:
            v = raw1.get(c); v = Fraction(v) if v is not None else prep['med'][c]
            if c in prep['winsor']: lo, hi = prep['winsor'][c]; v = min(max(v, lo), hi)
        if c in prep['log']:
            with localcontext(CTX60): l = frac2dec(v).ln()
            with localcontext(CTX28): d = l - prep['mean'][c]
            with localcontext(CTX60): z[c] = float(d / prep['std'][c])
        else:
            with localcontext(CTX60): z[c] = float(frac2dec(v - prep['mean_exact'][c]) / prep['std'][c])
    return z
def prep_cmp(prep, jp):
    d = 0.0
    for c in prep['cols']:
        d = max(d, abs(float(prep['mean'][c]) - jp['mean'][c]), abs(float(prep['std'][c]) - jp['std'][c]))
    for c, (lo, hi) in prep['winsor'].items():
        d = max(d, abs(float(lo) - jp['winsor'][c]['p05']), abs(float(hi) - jp['winsor'][c]['p95']))
    for c, m in prep['med'].items(): d = max(d, abs(float(m) - jp['medians'][c]))
    return d

# ---------- çözücüler
def newton_logit(X, y, lam, n_free=1, tol=1e-10):
    """min Σ[log(1+e^η) − yη] + (λ/2)‖w‖², ilk n_free sütun (sabit) cezasız."""
    p = X.shape[1]; pen = np.concatenate([np.zeros(n_free), np.full(p - n_free, lam)]); th = np.zeros(p)
    def obj(t): e = X @ t; return float(np.sum(np.logaddexp(0, e) - y * e)) + 0.5 * float(pen @ (t * t))
    J = obj(th)
    for it in range(200):
        h = 1 / (1 + np.exp(-(X @ th))); g = X.T @ (h - y) + pen * th
        if np.max(np.abs(g)) <= tol: return th, it
        H = (X * (h * (1 - h))[:, None]).T @ X + np.diag(pen); d = np.linalg.solve(H, g); s = 1.0
        for _ in range(40):
            c = th - s * d; Jn = obj(c)
            if Jn <= J + 1e-12 * max(abs(J), 1): break
            s *= 0.5
        th, J = c, Jn
    return th, -1
def ridge(X, y, alpha):
    xm, ym = X.mean(axis=0), y.mean(); Xc, yc = X - xm, y - ym
    w = np.linalg.solve(Xc.T @ Xc + alpha * np.eye(X.shape[1]), Xc.T @ yc)
    return float(ym - xm @ w), w
def hazard_fit(rows_pp, Z_of, lam, r_of=None):
    """rows_pp: list of (ticker, day, group, event). Z_of: ticker -> z vector (np). r_of: ticker -> r (pooled). numpy Newton."""
    G = np.array([g for _, _, g, _ in rows_pp]); E = np.array([e for _, _, _, e in rows_pp], dtype=float)
    Z = np.array([Z_of[t] for t, _, _, _ in rows_pp], dtype=float).reshape(len(G), -1); p = Z.shape[1]
    ev = np.bincount(G, weights=E, minlength=3); risk = np.bincount(G, minlength=3)
    g0 = np.array([math.log((ev[g] + 0.5) / (risk[g] - ev[g] + 0.5)) for g in range(3)])
    q = 0 if r_of is None else 1
    if lam == math.inf and q == 0: return g0, np.zeros(p), None
    Gp = np.concatenate([G, [0, 0, 1, 1, 2, 2]]); Ep = np.concatenate([E, [1, 0, 1, 0, 1, 0]]); W = np.concatenate([np.ones(len(G)), np.full(6, 0.5)])
    Zp = np.vstack([Z, np.zeros((6, p))]) if lam != math.inf else np.zeros((len(Gp), 0))
    cols = [np.eye(3)[Gp]]
    if q: cols.append(np.concatenate([[r_of[t] for t, _, _, _ in rows_pp], np.zeros(6)]).reshape(-1, 1))
    X = np.hstack(cols + [Zp]); nf = 3 + q; pp_ = X.shape[1] - nf
    pen = np.concatenate([np.zeros(nf), np.full(pp_, 0.0 if lam == math.inf else lam)])
    th = np.concatenate([g0, np.zeros(q), np.zeros(pp_)])
    def obj(t): e = X @ t; return float(np.sum(W * (np.logaddexp(0, e) - Ep * e))) + 0.5 * float(pen @ (t * t))
    J = obj(th); eps = np.finfo(float).eps * len(Ep)
    for it in range(101):
        h = 1 / (1 + np.exp(-(X @ th))); g = X.T @ (W * (h - Ep)) + pen * th
        if np.max(np.abs(g)) <= 1e-10: break
        H = (X * (W * h * (1 - h))[:, None]).T @ X + np.diag(pen); d = np.linalg.solve(H, g); s = 1.0
        for _ in range(31):
            c = th - s * d; Jn = obj(c)
            if Jn <= J + eps * max(abs(J), 1): break
            s *= 0.5
        th, J = c, Jn
    return th[:3], (th[nf:] if lam != math.inf else np.zeros(p)), (float(th[3]) if q else None)
def pp_of(L, closes=None):
    out = []
    for d in range(1, 11):
        if d - 1 > L: break
        out.append((d, 0 if d == 1 else (1 if d <= 3 else 2), int(L == d - 1)))
    return out

# ---------- veri
tbl = rd(ROOT / 'data/training_table.csv'); master = {r['ticker']: r for r in rd(ROOT / 'data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv')}
tufe = {r['month']: (r['index'], r['release_date']) for r in rd(ROOT / 'data/raw/tuik/tufe_genel_2025_100.csv')}
def month_m2(T):
    y, m = int(T[:4]), int(T[5:7]) - 2
    if m <= 0: y, m = y - 1, m + 12
    return f'{y:04d}-{m:02d}'
def real_size(size, idx):
    with localcontext(CTX60): return size / (Decimal(idx) / Decimal(100))
def feats(r, size_src):
    price, shares, post = Decimal(r['ipo_price_tl']), Decimal(r['shares_offered']), Decimal(r['post_ipo_share_capital'])
    f1 = Decimal(size_src) if size_src else price * shares
    return {'f1': f1, 'f2': pct(shares, post), 'f3': Decimal(r['total_demand_multiple']) if r['total_demand_multiple'].strip() else None,
            'f4': pct(Decimal(r['capital_increase_shares']), shares)}
H = {}
for r in tbl:
    f = feats(r, master[r['ticker']]['ipo_size_tl'].strip()); T = r['first_trading_date']; m = month_m2(T)
    assert tufe[m][1] < T
    f['f1r'] = real_size(f['f1'], tufe[m][0]); f['add_sale'] = Decimal(1 if Decimal(r['additional_sale_shares']) > 0 else 0) if r['additional_sale_shares'].strip() else None
    H[r['ticker']] = dict(f=f, L=int(r['ceiling_streak_L']), closes=[int(r[f'ceiling_close_D{k}']) for k in range(1, 11)], T=T,
                          R={h: float(Fraction(r[f'R_{h}'])) for h in ('D1', 'D3', 'D5', 'D10')}, Y={h: int(r[f'Y_{h}']) for h in ('D1', 'D3', 'D5', 'D10')},
                          regime=0, cohort='H99', status=r['total_demand_filter_status'])
order = [r['ticker'] for r in tbl]
# v2 (açık küme): ticker'lar yalnız bellekte
v2 = rd(ROOT / 'data/training_table_v2.csv'); V2 = {}
for r in v2:
    f = feats(r, r['ipo_size_tl'].strip()); T = r['first_trading_date']; m = month_m2(T)
    assert (r['tufe_month'], Decimal(r['tufe_index'])) == (m, Decimal(tufe[m][0])), 'v2 tufe tutmuyor'
    f['f1r'] = real_size(f['f1'], tufe[m][0]); f['add_sale'] = Decimal(1 if Decimal(r['additional_sale_shares']) > 0 else 0) if r['additional_sale_shares'].strip() else None
    V2[r['ticker']] = dict(f=f, L=int(r['ceiling_streak_L']), closes=[int(r[f'ceiling_close_D{k}']) for k in range(1, 11)], T=T,
                           Y={h: int(r[f'Y_{h}']) for h in ('D1', 'D3', 'D5', 'D10')}, regime=0 if r['alloc_regime'] == 'EQUAL_DIST_20230330' else 1,
                           cohort=r['cohort'], status=r['total_demand_filter_status'])
order2 = [r['ticker'] for r in v2]
assert [t for t in order2 if V2[t]['cohort'] == 'H99'] == order
OUT['v2_counts'] = dict(n=len(order2), open=sum(1 for t in order2 if V2[t]['cohort'] != 'H99'), f3_present=sum(1 for t in order2 if V2[t]['f']['f3'] is not None),
                        f3_and_addsale=sum(1 for t in order2 if V2[t]['f']['f3'] is not None and V2[t]['f']['add_sale'] is not None),
                        addsale_present=sum(1 for t in order2 if V2[t]['f']['add_sale'] is not None),
                        filter_status_counts={s: sum(1 for t in order2 if V2[t]['status'] == s) for s in set(V2[t]['status'] for t in order2)})
def J(mid): return json.load(open(ROOT / f'models/{mid}.json'))

# ---------- v1_5_h99 (99 arz; f1..f5; f3 winsor+medyan; f5)
raw15 = {t: {c: H[t]['f'][c] for c in ('f1', 'f2', 'f3', 'f4')} for t in order}
p15 = fit_prep(raw15, ('f1', 'f2', 'f3', 'f4'), winsor=('f3',), log=('f1',), impute=('f3',), indicator=True)
j15 = J('v1_5_h99'); OUT['v1_5_prep_maxdiff'] = prep_cmp(p15, j15['preprocessing'])
X15 = np.array([[p15['z'][t][c] for c in p15['cols']] for t in order])
res15 = {}
for h in ('D1', 'D3', 'D5', 'D10'):
    hz = j15['horizons'][h]; alpha, C = hz['return']['alpha'], hz['p_up']['C']
    y = np.array([H[t]['R'][h] for t in order]); b0, w = ridge(X15, y, alpha)
    yy = np.array([H[t]['Y'][h] for t in order], dtype=float)
    th, it = newton_logit(np.hstack([np.ones((99, 1)), X15]), yy, 1.0 / C)
    res15[h] = dict(alpha=alpha, C=C, ridge_maxdiff=max(abs(b0 - hz['return']['intercept']), max(abs(w - np.array(hz['return']['coef'])))),
                    logit_maxdiff=max(abs(th[0] - hz['p_up']['intercept']), max(abs(th[1:] - np.array(hz['p_up']['coef'])))), logit_iter=it,
                    ridge=(b0, w.tolist()), logit=(th.tolist()))
OUT['v1_5_h99'] = res15
# NETGL V1.5 D5
inp = json.load(open(ROOT / 'registry/inputs/NETGL.json'))['fields']; V = lambda k: Decimal(inp[k]['value'])
rawN = {'f1': V('ipo_size_tl'), 'f2': pct(V('shares_offered'), V('post_ipo_share_capital')), 'f3': V('total_demand_multiple'), 'f4': pct(V('capital_increase_shares'), V('shares_offered'))}
zN = transform(p15, rawN); zv = np.array([zN[c] for c in p15['cols']])
b0, w = res15['D5']['ridge']; th = np.array(res15['D5']['logit'])
OUT['netgl_v1_5_D5'] = dict(z=zN, ridge=b0 + zv @ np.array(w), p_up=float(1 / (1 + math.exp(-(th[0] + zv @ th[1:])))), record=(0.25515244136301274, 0.797010819748606))
# v1_6 D10 ridge α = 0.001
j16 = J('v1_6_h99'); hz = j16['horizons']['D10']
b0, w = ridge(X15, np.array([H[t]['R']['D10'] for t in order]), hz['return']['alpha'])
OUT['v1_6_D10_ridge'] = dict(alpha=hz['return']['alpha'], maxdiff=max(abs(b0 - hz['return']['intercept']), max(abs(w - np.array(hz['return']['coef'])))))

# ---------- PB: pb_v0 (D1..D10) ve pb_ceiling_v0
pbcsv = {r['ticker']: r for r in rd(ROOT / 'data/raw/PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv')}
def pbfeat(r):
    price, base, post, cap, addl = (Decimal(r[k]) for k in ('ipo_price_try', 'planned_base_offer_shares', 'planned_post_ipo_capital', 'planned_capital_increase_shares', 'planned_additional_sale_ceiling'))
    assert Decimal(r['planned_post_ipo_capital']) == Decimal(r['planned_pre_ipo_capital']) + cap and base == cap + Decimal(r['planned_existing_share_sale']) and Decimal(r['planned_max_offer_shares']) == base + addl
    with localcontext(Context(prec=200, rounding=ROUND_HALF_EVEN)): prod = price * base
    with localcontext(CTX60): pb1 = float(prod.ln())
    n, d = (base * 100 / post).as_integer_ratio() if False else None, None
    def ratio(a, b):
        fa = Fraction(a) * 100 / Fraction(b); return fa.numerator / fa.denominator   # float(Fraction) = doğru yuvarlanmış tamsayı bölmesi
    return {'pb1': Fraction(pb1), 'pb2': Fraction(ratio(base, post)), 'pb3': Fraction(ratio(cap, base))}
rawPB = {t: pbfeat(pbcsv[t]) for t in order}
pPB = fit_prep(rawPB, ('pb1', 'pb2', 'pb3')); jpb = J('pb_v0'); OUT['pb_v0_prep_maxdiff'] = prep_cmp(pPB, jpb['preprocessing'])
XPB = np.array([[pPB['z'][t][c] for c in pPB['cols']] for t in order]); resPB = {}
for h in ('D1', 'D3', 'D5', 'D10'):
    hz = jpb['horizons'][h]; alpha, C = hz['return']['alpha'], hz['p_up']['C']
    b0, w = ridge(XPB, np.array([H[t]['R'][h] for t in order]), alpha)
    th, it = newton_logit(np.hstack([np.ones((99, 1)), XPB]), np.array([H[t]['Y'][h] for t in order], dtype=float), 1.0 / C)
    resPB[h] = dict(alpha=alpha, C=C, ridge_maxdiff=max(abs(b0 - hz['return']['intercept']), max(abs(w - np.array(hz['return']['coef'])))),
                    logit_maxdiff=max(abs(th[0] - hz['p_up']['intercept']), max(abs(th[1:] - np.array(hz['p_up']['coef'])))))
OUT['pb_v0'] = resPB
pPBC = fit_prep({t: {c: rawPB[t][c] for c in ('pb1', 'pb2')} for t in order}, ('pb1', 'pb2')); jpc = J('pb_ceiling_v0'); OUT['pb_ceiling_prep_maxdiff'] = prep_cmp(pPBC, jpc['preprocessing'])
rows_pp = [(t, d, g, e) for t in order for d, g, e in pp_of(H[t]['L'])]
Zc = {t: np.array([pPBC['z'][t][c] for c in ('pb1', 'pb2')]) for t in order}
ga, be, _ = hazard_fit(rows_pp, Zc, 10.0)
OUT['pb_ceiling_v0'] = dict(n_rows=len(rows_pp), n_events=sum(e for *_, e in rows_pp), gamma_maxdiff=float(np.max(np.abs(ga - np.array(jpc['gamma'])))), beta_maxdiff=float(np.max(np.abs(be - np.array([jpc['beta']['pb1'], jpc['beta']['pb2']])))))
gaI, _, _ = hazard_fit(rows_pp, Zc, math.inf); OUT['pb_ceiling_v0@INF_gamma_maxdiff'] = float(np.max(np.abs(gaI - np.array(J('pb_ceiling_v0@INF')['gamma']))))
# NETGL pb_ceiling
rPB_N = {'ipo_price_try': inp['ipo_price_try']['value'], 'planned_base_offer_shares': inp['planned_base_offer_shares']['value'], 'planned_post_ipo_capital': inp['planned_post_ipo_capital']['value'],
         'planned_capital_increase_shares': inp['planned_capital_increase_shares']['value'], 'planned_additional_sale_ceiling': inp['planned_additional_sale_ceiling']['value'],
         'planned_pre_ipo_capital': inp['planned_pre_ipo_capital']['value'], 'planned_existing_share_sale': inp['planned_existing_share_sale']['value'], 'planned_max_offer_shares': inp['planned_max_offer_shares']['value']}
zpn = transform(pPBC, pbfeat(rPB_N)); lin = be @ np.array([zpn['pb1'], zpn['pb2']])
hz_ = [1 / (1 + math.exp(-(ga[g] + lin))) for g in (0, 1, 1, 2, 2, 2, 2, 2, 2, 2)]; s = 1.0; S = []
for h_ in hz_: s *= 1 - h_; S.append(s)
OUT['netgl_pb_ceiling'] = dict(z=zpn, beta_dot_z=float(lin), S=[round(x, 4) for x in S], guide='z 0.4910/0.5847, β·z 0.1328, S_1 0.8079 … S_10 0.0793')

# ---------- Faz 7: v1_clip / v1_real / v1_pooled / pooled@INF
tr97 = [t for t in order if H[t]['f']['f3'] is not None]
for mid, cols, winsor, src, pooled in (('ceiling_hazard_v1_clip', ('f1', 'f2', 'f3'), ('f1', 'f2', 'f3'), H, False), ('ceiling_hazard_v1_real', ('f1r', 'f2', 'f3'), ('f1r', 'f2', 'f3'), H, False),
                                        ('ceiling_hazard_v1_pooled', ('f1r', 'f2', 'f3'), ('f1r', 'f2', 'f3'), V2, True)):
    tick = [t for t in (order2 if pooled else order) if src[t]['f']['f3'] is not None]
    raw = {t: {c: src[t]['f'][c] for c in cols} for t in tick}
    pr = fit_prep(raw, cols, winsor=winsor, log=(cols[0],)); jj = J(mid)
    rows_pp = [(t, d, g, e) for t in tick for d, g, e in pp_of(src[t]['L'])]
    Zc = {t: np.array([pr['z'][t][c] for c in cols]) for t in tick}
    r_of = {t: float(src[t]['regime']) for t in tick} if pooled else None
    ga, be, de = hazard_fit(rows_pp, Zc, 10.0, r_of)
    OUT[mid] = dict(n_ipo=len(tick), n_rows=len(rows_pp), n_events=sum(e for *_, e in rows_pp), prep_maxdiff=prep_cmp(pr, jj['preprocessing']),
                    gamma_maxdiff=float(np.max(np.abs(ga - np.array(jj['gamma'])))), beta_maxdiff=float(np.max(np.abs(be - np.array([jj['beta'][c] for c in cols])))),
                    delta=(de, jj.get('regime', {}).get('delta')), selected_lambda=jj['lambda'])
    if pooled:
        OUT[mid]['n_regime1'] = sum(1 for t in tick if src[t]['regime'] == 1)
        gaI, _, deI = hazard_fit(rows_pp, Zc, math.inf, r_of); jI = J('ceiling_hazard_v1_pooled@INF')
        OUT['ceiling_hazard_v1_pooled@INF'] = dict(gamma_maxdiff=float(np.max(np.abs(gaI - np.array(jI['gamma'])))), delta=(deI, jI['regime']['delta']))
    if mid == 'ceiling_hazard_v1_real':
        rN = {'f1r': real_size(V('ipo_size_tl'), tufe['2026-07'][0]), 'f2': rawN['f2'], 'f3': rawN['f3']}
        OUT['netgl_f1r'] = dict(f1r=str(rN['f1r'])[:20], guide='1 687 703 121', tufe_month='2026-07', index=tufe['2026-07'][0], release=tufe['2026-07'][1])

# ---------- Faz 7C: fall modelleri (L2-lojistik, λ = 1/C, sabit cezasız)
for mid, cols, src, need_f3 in (('fall_d10_v0_h99', ('f1r', 'f3', 'add_sale'), H, True), ('fall_d10_v0_pooled', ('f1r', 'f3', 'add_sale'), V2, True), ('fall_d10_v0_addsale', ('add_sale',), V2, False)):
    tick = [t for t in (order2 if src is V2 else order) if src[t]['f']['add_sale'] is not None and (not need_f3 or src[t]['f']['f3'] is not None)]
    raw = {t: {c: src[t]['f'][c] for c in cols} for t in tick}
    pr = fit_prep(raw, cols, winsor=('f1r', 'f3') if need_f3 else (), log=('f1r', 'f3') if need_f3 else ()); jj = J(mid)
    X = np.array([[pr['z'][t][c] for c in cols] for t in tick]); res = dict(n=len(tick), prep_maxdiff=prep_cmp(pr, jj['preprocessing']))
    for h in ('D5', 'D10'):
        hz = jj['horizons'][h]['p_up']; y = np.array([src[t]['Y'][h] for t in tick], dtype=float)
        th, it = newton_logit(np.hstack([np.ones((len(tick), 1)), X]), y, 1.0 / hz['C'])
        res[h] = dict(C=hz['C'], maxdiff=max(abs(th[0] - hz['intercept']), max(abs(th[1:] - np.array(hz['coef'])))), iter=it, n_events=int(len(y) - y.sum()))
    OUT[mid] = res
tick = [t for t in order2 if V2[t]['f']['add_sale'] is not None and V2[t]['f']['f3'] is not None]; jz = J('fall_d10_v0_pooled@ZERO')
OUT['fall_d10_v0_pooled@ZERO'] = {h: (sum(V2[t]['Y'][h] for t in tick) / len(tick), jz['horizons'][h]['p_up']['value']) for h in ('D5', 'D10')}
# NETGL fall (illüstrasyon; kılavuz: h99 0.163, pooled 0.171, addsale 0.193, @ZERO 0.242)
def fall_pred(mid, cols, src, need_f3):
    tick = [t for t in (order2 if src is V2 else order) if src[t]['f']['add_sale'] is not None and (not need_f3 or src[t]['f']['f3'] is not None)]
    pr = fit_prep({t: {c: src[t]['f'][c] for c in cols} for t in tick}, cols, winsor=('f1r', 'f3') if need_f3 else (), log=('f1r', 'f3') if need_f3 else ())
    jj = J(mid); hz = jj['horizons']['D10']['p_up']
    rN = {'f1r': real_size(V('ipo_size_tl'), tufe['2026-07'][0]), 'f3': rawN['f3'], 'add_sale': Decimal(1 if Decimal(inp['additional_sale_shares']['value']) > 0 else 0)}
    z = transform(pr, {c: rN[c] for c in cols}); eta = hz['intercept'] + sum(hz['coef'][i] * z[c] for i, c in enumerate(cols))
    return 1 - 1 / (1 + math.exp(-eta))
OUT['netgl_fall_P_D10_le_ipo'] = {m: fall_pred(m, c, s, f) for m, c, s, f in (('fall_d10_v0_h99', ('f1r', 'f3', 'add_sale'), H, True), ('fall_d10_v0_pooled', ('f1r', 'f3', 'add_sale'), V2, True), ('fall_d10_v0_addsale', ('add_sale',), V2, False))}
OUT['netgl_fall_P_D10_le_ipo']['@ZERO'] = 1 - jz['horizons']['D10']['p_up']['value']
OUT['netgl_addsale_value'] = inp['additional_sale_shares']['value']

def conv(o):
    if isinstance(o, (np.floating, np.integer)): return o.item()
    if isinstance(o, dict): return {str(k): conv(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [conv(x) for x in o]
    if isinstance(o, (Decimal, Fraction)): return str(o)
    return o
print(json.dumps(conv(OUT), indent=1, ensure_ascii=False))

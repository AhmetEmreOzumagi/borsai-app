"""Adım 6: post_d1_hazard_v0 nihai fit'ini sıfırdan yeniden yap (numpy; borsai import edilmez)."""
from __future__ import annotations
import sys, json, math
from fractions import Fraction
from decimal import Decimal, localcontext, Context, ROUND_HALF_UP
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa

parent = load_json(ROOT / "models/ceiling_hazard_v0.json")
frozen = load_json(ROOT / "models/post_d1_hazard_v0.json")
TT = read_csv(ROOT / "data/training_table.csv")
MASTER = {r["ticker"]: r for r in read_csv(ROOT / "data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv")}
SESS = read_csv(ROOT / "data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv")
D1 = {r["ticker"]: r for r in SESS if int(r["session_number"]) == 1}
CTX = Context(prec=60)

def z_base(row):
    """ceiling_hazard_v0 ön işlemesi: f1 = ln(ipo_size ya da fiyat×pay), f2 = pay/sermaye×100 (10 ondalık HALF_UP), f3 winsor; z = (x−μ)/σ."""
    price = Decimal(row["ipo_price_tl"]); shares = Decimal(row["shares_offered"]); post = Decimal(row["post_ipo_share_capital"])
    size = MASTER[row["ticker"]].get("ipo_size_tl", "")
    f1 = Decimal(size) if size not in ("", None) else shares * price
    with localcontext(CTX):
        f2 = (shares / post * 100).quantize(Decimal("0.0000000001"), rounding=ROUND_HALF_UP)
    f3 = Decimal(row["total_demand_multiple"])
    prep = parent["preprocessing"]
    vals = {"f1": float(f1), "f2": float(f2), "f3": float(f3)}
    z = []
    for col in prep["columns"]:
        x = vals[col]
        if col in prep["winsor"]:
            x = min(max(x, prep["winsor"][col]["p05"]), prep["winsor"][col]["p95"])
        if col in prep["log_transform"]:
            x = math.log(x)
        z.append((x - prep["mean"][col]) / prep["std"][col])
    return z

GROUP = {1: 0, 2: 1, 3: 1}
def eta_of(z):
    lin = sum(b * v for b, v in zip([parent["beta"][c] for c in parent["columns"]], z))
    return [parent["gamma"][GROUP.get(d, 2)] + lin for d in range(1, 11)]

rows = [r for r in TT if r["total_demand_multiple"] not in ("", None) and r["ceiling_close_D1"] == "1"]
print("training ipos (f3 present & D1 ceiling):", len(rows))
feats = {}; pp = {}; eta = {}
n_rows = n_ev = 0
for r in rows:
    t = r["ticker"]; L = int(r["ceiling_streak_L"]); s = D1[t]
    lock = int(Decimal(s["thb_raw_low"]) == Decimal(s["thm_raw_upper_limit"]))
    with localcontext(CTX):
        ratio = Decimal(s["thb_raw_volume"]) / Decimal(r["shares_offered"])
        ln = float(ratio.ln())
    feats[t] = {"d1_lock": lock, "d1_turnover": ln}
    pp[t] = [(d, int(L == d - 1)) for d in range(2, 11) if d - 1 <= L]
    n_rows += len(pp[t]); n_ev += sum(e for _, e in pp[t])
    eta[t] = eta_of(z_base(r))
print(f"PP rows d>=2: {n_rows}, events {n_ev}, survivals {n_rows - n_ev}; locked {sum(f['d1_lock'] for f in feats.values())}/{len(feats)}")
# turnover ratio quantiles (Type-7) for the guide's §5.2.2 claim
def q7(sorted_vals, p):
    n = len(sorted_vals); h = Fraction(n - 1) * p + 1; lo = h.numerator // h.denominator; fr = h - lo
    if lo == n: return sorted_vals[lo - 1]
    return sorted_vals[lo - 1] + fr * (sorted_vals[lo] - sorted_vals[lo - 1])
turn = sorted(Fraction(f["d1_turnover"]) for f in feats.values())
p05, p95 = q7(turn, Fraction(5, 100)), q7(turn, Fraction(95, 100))
print(f"turnover ln p05 {float(p05):.6f} p95 {float(p95):.6f} (frozen {frozen['d1_preprocessing']['clip']['d1_turnover']}); ratio p05 {math.exp(float(p05)):.7f} median {math.exp(float(q7(turn, Fraction(1,2)))):.6f} p95 {math.exp(float(p95)):.4f}")
tick = list(feats)
def prep_of(tks):
    tr = sorted(Fraction(feats[t]["d1_turnover"]) for t in tks)
    a, b = q7(tr, Fraction(5, 100)), q7(tr, Fraction(95, 100))
    vals = {"d1_lock": [Fraction(feats[t]["d1_lock"]) for t in tks], "d1_turnover": [min(max(Fraction(feats[t]["d1_turnover"]), a), b) for t in tks]}
    mean = {c: sum(v, Fraction(0)) / len(tks) for c, v in vals.items()}
    var = {c: sum(((x - mean[c]) ** 2 for x in v), Fraction(0)) / len(tks) for c, v in vals.items()}
    std = {c: math.sqrt(float(var[c])) for c in vals}
    cols = [c for c in ("d1_lock", "d1_turnover") if var[c] != 0]
    def transform(f):
        raw = Fraction(f["d1_turnover"]); v = {"d1_lock": Fraction(f["d1_lock"]), "d1_turnover": min(max(raw, a), b)}
        return [float(v[c] - mean[c]) / std[c] for c in cols]
    return cols, transform, (float(a), float(b), {c: float(mean[c]) for c in mean}, std)
def arrays(tks, transform):
    U, o, e = [], [], []
    for t in tks:
        u = transform(feats[t])
        for d, ev in pp[t]:
            U.append(u); o.append(eta[t][d - 1]); e.append(float(ev))
    return np.array(U), np.array(o), np.array(e)
def sig(x): return 1 / (1 + np.exp(-x))
def newton(U, o, e, lam, tol=1e-10, maxit=100):
    th = np.zeros(U.shape[1])
    for it in range(maxit + 1):
        h = sig(o + U @ th); g = U.T @ (h - e) + lam * th
        if np.max(np.abs(g)) <= tol: return th, it, float(np.max(np.abs(g)))
        H = (U * (h * (1 - h))[:, None]).T @ U + lam * np.eye(U.shape[1])
        th = th - np.linalg.solve(H, g)
    return th, it, float(np.max(np.abs(g)))
GRID = [0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, "INF"]
# inner leave-one-ipo-out CV
scores_cv = {}
for lam in GRID:
    nll = 0.0; m = 0
    for j in tick:
        rest = [t for t in tick if t != j]
        cols, tf, _ = prep_of(rest)
        U, o, e = arrays(rest, tf)
        if lam == "INF": th = np.zeros(len(cols))
        else: th, _, _ = newton(U, o, e, lam)
        uj = np.array(tf(feats[j]))
        for d, ev in pp[j]:
            h = float(sig(eta[j][d - 1] + uj @ th)); h = min(max(h, 1e-12), 1 - 1e-12)
            nll += -(ev * math.log(h) + (1 - ev) * math.log(1 - h)); m += 1
    scores_cv[lam] = nll / m
best = min(scores_cv, key=lambda l: (scores_cv[l], -(float('inf') if l == "INF" else l)))
print("inner CV scores:", {str(k): round(v, 6) for k, v in scores_cv.items()})
print("frozen table:   ", {str(x["lambda"]): round(x["score"], 6) for x in frozen["lambda_score_table"]})
print("selected lambda mine:", best, "frozen:", frozen["lambda"])
cols, tf, (a, b, mean, std) = prep_of(tick)
U, o, e = arrays(tick, tf)
th, it, g = newton(U, o, e, 30.0)
d = dict(zip(cols, th))
print("delta mine:", d, "iterations", it, "grad", g)
print("delta frozen:", frozen["delta"], "| max |Δδ| =", max(abs(d[c] - frozen["delta"][c]) for c in cols))
print("prep mine: p05/p95", a, b, "mean", mean, "std", std)
print("prep frozen:", frozen["d1_preprocessing"]["clip"], frozen["d1_preprocessing"]["mean"], frozen["d1_preprocessing"]["std"])
# ---- NETGL numbers (§5.2.5 of the guide): base record inputs + D1 bulletin fields
rec = load_json(sorted((ROOT / "registry/records/NETGL").glob("*.json"))[0])
mi = rec["model_inputs"]
row = {"ticker": "NETGL", "ipo_price_tl": mi["ipo_price_tl"], "shares_offered": mi["shares_offered"], "post_ipo_share_capital": mi["post_ipo_share_capital"], "total_demand_multiple": mi["total_demand_multiple"]}
MASTER["NETGL"] = {"ipo_size_tl": mi.get("ipo_size_tl") or ""}
z = z_base(row); et = eta_of(z)
print("NETGL z_base", [round(x, 4) for x in z], "eta_2", round(et[1], 4), "eta_4", round(et[3], 4))
sha, hdr, thb = read_bulletin("2026-09-17", "thb"); _, _, thm = read_bulletin("2026-09-17", "thm")
r = thb["NETGL.E"]; l = thm["NETGL.E"]
lock = int(Decimal(r["EN DUSUK FIYAT"]) == Decimal(l["UST LIMIT FIYATI"]))
with localcontext(CTX):
    ln = float((Decimal(r["TOPLAM ISLEM ADEDI"]) / Decimal(mi["shares_offered"])).ln())
fp = frozen["d1_preprocessing"]
u = [(lock - fp["mean"]["d1_lock"]) / fp["std"]["d1_lock"], (min(max(ln, fp["clip"]["d1_turnover"]["p05"]), fp["clip"]["d1_turnover"]["p95"]) - fp["mean"]["d1_turnover"]) / fp["std"]["d1_turnover"]]
shift = frozen["delta"]["d1_lock"] * u[0] + frozen["delta"]["d1_turnover"] * u[1]
haz = [sigmoid(et[0])] + [sigmoid(et[d - 1] + shift) for d in range(2, 11)]
S = []; s = 1.0
for h in haz: s *= (1 - h); S.append(s)
Scond = [S[k - 1] / S[0] for k in range(1, 11)]
base_h = [sigmoid(x) for x in et]; Sb = []; s = 1.0
for h in base_h: s *= (1 - h); Sb.append(s)
Sbc = [Sb[k - 1] / Sb[0] for k in range(1, 11)]
print(f"NETGL: lock {lock}, ln turnover {ln:.4f} (ratio {math.exp(ln):.4f}), u {u[0]:.3f} {u[1]:.3f}, shift {shift:.4f}, h_2 {haz[1]:.4f} (base {base_h[1]:.4f})")
print("S_cond post_d1:", [round(x, 4) for x in Scond[1:]]); print("S_cond base   :", [round(x, 4) for x in Sbc[1:]])
L = 3
rps1 = lambda sc: sum((sc[k-1] - (1.0 if L >= k else 0.0)) ** 2 for k in range(2, 11)) / 9
print(f"NETGL RPS_1 post_d1 {rps1(Scond):.4f} base {rps1(Sbc):.4f}")
# record's ceiling_hazard_v0 output S vs my base S
cell = next(c for c in rec["models"] if c["model_id"] == "ceiling_hazard_v0")
print("record ceiling_hazard_v0 S:", [round(x, 4) for x in cell["output"]["S"]], "| mine:", [round(x, 4) for x in Sb], "| max|Δ|", max(abs(a - b) for a, b in zip(cell["output"]["S"], Sb)))
E_L = sum(Sb); print(f"NETGL E[L] = ΣS_k = {E_L:.4f}; S_1 = {Sb[0]:.4f}; P(L>=4|L>=3)= {Sb[3]/Sb[2]:.4f}; P(L>=7|L>=6)= {Sb[6]/Sb[5]:.4f}; remaining at j=3: {sum(Sb[3:])/Sb[2]:.4f}; P(L>=5|L>=3) {Sb[4]/Sb[2]:.4f}; P(L=10|L>=3) {Sb[9]/Sb[2]:.4f}")

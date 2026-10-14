"""Adım 4: kendi blok bootstrap'ımla hücreleri ledger'lardan yeniden üret (C7: ay blokları, 4000, random.Random(20260921), [100],[3899])."""
from __future__ import annotations
import sys, json, random, math
from pathlib import Path
from collections import Counter
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa

def block_ci(diffs, months, reps=4000, seed=20260921):
    rng = random.Random(seed)
    by = {}
    for m, d in zip(months, diffs):
        by.setdefault(m, []).append(d)
    keys = list(by)
    out = []
    for _ in range(reps):
        s = []
        for k in rng.choices(keys, k=len(keys)):
            s += by[k]
        out.append(sum(s) / len(s))
    out.sort()
    return out[100], out[3899]

def summarize(diffs, months, a, b, label, expect=None):
    n = len(diffs); lo, hi = block_ci(diffs, months)
    res = dict(cell=label, n=n, n_blocks=len(set(months)), model=sum(a)/n, rule=sum(b)/n, diff=sum(diffs)/n, ci=[lo, hi],
               wins=sum(d < 0 for d in diffs), losses=sum(d > 0 for d in diffs), ties=sum(d == 0 for d in diffs),
               verdict=("geçiyor" if hi < 0 else "geçemiyor" if lo > 0 else "ayırt edilemiyor") if n >= 30 else "yetersiz örnek")
    if expect:
        res["expect"] = expect
        res["match"] = (abs(res["diff"] - expect[0]) < 5e-5 and abs(lo - expect[1][0]) < 5e-5 and abs(hi - expect[1][1]) < 5e-5)
    print(json.dumps(res, ensure_ascii=False))
    return res

G = ROOT / "tests/reference"
scores = load_json(ROOT / "scores/scores.json")
def cell_of(mid, hk, metric, rule):
    m = next(x for x in scores["models"] if x["model_id"] == mid)
    for c in m["backtest"]["cells"]:
        if c["horizon_or_k"] == hk and c["metric"] == metric and c["rule_id"] == rule:
            return (c["diff"], c["ci95"], c["n"], c["n_blocks"], c["wins"], c["losses"], c["ties"], c["verdict"])
results = []
# (a) v1_5_h99 D5 MAE − base_train_median (PLAN_V15, report.paired order)
v15 = read_csv(G / "macos_golden/v1_5_h99_fold_ledger.csv")
for rule in ("base_train_median", "base_always_ceiling"):
    rl = {r["fold_id"]: r for r in read_csv(G / f"macos_golden/{rule}_fold_ledger.csv")}
    d, mo, a, b = [], [], [], []
    for r in v15:
        if r["horizon"] != "D5" or r["ridge_status"] != "FIT_OK": continue
        o = rl[r["fold_id"]]; R = float(r["realized_return"])
        ea, eb = abs(float(r["ridge_prediction"]) - R), abs(float(o["rule_return"]) - R)
        a.append(ea); b.append(eb); d.append(ea - eb); mo.append(r["prediction_date"][:7])
    ex = cell_of("v1_5_h99", "D5", "MAE", rule)
    results.append(summarize(d, mo, a, b, f"v1_5_h99 D5 MAE − {rule}", (ex[0], ex[1])))
    print("   scores.json:", ex)
# D10 p_up Brier − base_rate (clipped [0.01,0.99] in backtest tables)
rl = {r["fold_id"]: r for r in read_csv(G / "macos_golden/base_rate_fold_ledger.csv")}
d, mo, a, b = [], [], [], []
clipp = lambda p: min(max(p, 0.01), 0.99)
for r in v15:
    if r["horizon"] != "D10" or r["logit_status"] != "FIT_OK": continue
    o = rl[r["fold_id"]]; y = int(r["realized_direction"])
    ea, eb = (clipp(float(r["logit_probability"])) - y) ** 2, (clipp(float(o["rule_p_up"])) - y) ** 2
    a.append(ea); b.append(eb); d.append(ea - eb); mo.append(r["prediction_date"][:7])
ex = cell_of("v1_5_h99", "D10", "Brier", "base_rate")
results.append(summarize(d, mo, a, b, "v1_5_h99 D10 Brier − base_rate (clip .01/.99)", (ex[0], ex[1]))); print("   scores.json:", ex)

# (b) ceiling_hazard_v0 RPS − KM rules and @INF (faz1b)
def S_of(r): return [float(r[f"S_{k}"]) for k in range(1, 11)]
def rps(S, L): return sum((S[k-1] - (1.0 if L >= k else 0.0)) ** 2 for k in range(1, 11)) / 10
ch = read_csv(G / "macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv")
for rule, f in (("base_km_expanding", "base_km_expanding"), ("base_km_last10", "base_km_last10"), ("ceiling_hazard_v0@INF", "ceiling_hazard_v0@INF")):
    other = {r["ticker"]: r for r in read_csv(G / f"macos_golden_faz1b/{f}_fold_ledger.csv") if r["status"] in ("FIT_OK", "RULE_OK")}
    d, mo, a, b = [], [], [], []
    for r in ch:
        if r["status"] != "FIT_OK" or r["ticker"] not in other: continue
        L = int(r["realized_L"]); la, lb = rps(S_of(r), L), rps(S_of(other[r["ticker"]]), L)
        a.append(la); b.append(lb); d.append(la - lb); mo.append(r["first_trading_date"][:7])
    ex = cell_of("ceiling_hazard_v0", None, "RPS", rule)
    results.append(summarize(d, mo, a, b, f"ceiling_hazard_v0 RPS − {rule}", (ex[0], ex[1]))); print("   scores.json:", ex)
# pb_ceiling_v0
pc = read_csv(G / "macos_golden_faz1b/pb_ceiling_v0_fold_ledger.csv")
other = {r["ticker"]: r for r in read_csv(G / "macos_golden_faz1b/base_km_expanding__pb_ceiling_fold_ledger.csv") if r["status"] in ("FIT_OK", "RULE_OK")}
d, mo, a, b = [], [], [], []
for r in pc:
    if r["status"] != "FIT_OK" or r["ticker"] not in other: continue
    L = int(r["realized_L"]); la, lb = rps(S_of(r), L), rps(S_of(other[r["ticker"]]), L)
    a.append(la); b.append(lb); d.append(la - lb); mo.append(r["first_trading_date"][:7])
ex = cell_of("pb_ceiling_v0", None, "RPS", "base_km_expanding")
results.append(summarize(d, mo, a, b, "pb_ceiling_v0 RPS − base_km_expanding", (ex[0], ex[1]))); print("   scores.json:", ex)

# (c) post_d1 RPS_1 and Brier k=2 / k=10 vs ceiling_hazard_v0 conditional (faz5 ledger vs faz1b ledger)
pd1 = read_csv(G / "macos_golden_faz5/post_d1_hazard_v0_fold_ledger.csv")
v0 = {r["ticker"]: r for r in ch if r["status"] == "FIT_OK"}
def cond(S): return [S[k-1] / S[0] for k in range(1, 11)]  # index k-1 -> S_k/S_1
def rps1(sc, L): return sum((sc[k-1] - (1.0 if L >= k else 0.0)) ** 2 for k in range(2, 11)) / 9
def brk(sc, L, k): return (sc[k-1] - (1.0 if L >= k else 0.0)) ** 2
stat = Counter(r["status"] for r in pd1); print("post_d1 ledger statuses:", dict(stat))
lam = Counter(r["selected_lambda"] for r in pd1 if r["status"] == "FIT_OK"); print("selected lambda:", dict(lam))
neg_lock = sum(1 for r in pd1 if r["status"] == "FIT_OK" and r["selected_lambda"] != "INF" and r["delta_d1_lock"] not in ("", "0.0") and float(r["delta_d1_lock"]) < 0)
tot_lock = sum(1 for r in pd1 if r["status"] == "FIT_OK" and r["selected_lambda"] != "INF" and r["delta_d1_lock"] not in ("", "0.0"))
pos_turn = sum(1 for r in pd1 if r["status"] == "FIT_OK" and r["selected_lambda"] != "INF" and float(r["delta_d1_turnover"]) > 0)
tot_turn = sum(1 for r in pd1 if r["status"] == "FIT_OK" and r["selected_lambda"] != "INF")
print(f"delta_lock<0: {neg_lock}/{tot_lock}; delta_turn>0: {pos_turn}/{tot_turn}")
for metric, fn in (("RPS_1", lambda sc, L: rps1(sc, L)), ("Brier k=2", lambda sc, L: brk(sc, L, 2)), ("Brier k=10", lambda sc, L: brk(sc, L, 10))):
    d, mo, a, b = [], [], [], []
    for r in pd1:
        if r["status"] != "FIT_OK": continue
        L = int(r["realized_L"]); sc_m = [None] + [float(r[f"S_cond_{k}"]) for k in range(2, 11)]
        sc_m = [1.0] + sc_m[1:]  # index0 unused (k=1 -> 1)
        sc_c = cond(S_of(v0[r["ticker"]]))
        la, lb = fn(sc_m, L), fn(sc_c, L)
        a.append(la); b.append(lb); d.append(la - lb); mo.append(r["first_trading_date"][:7])
    results.append(summarize(d, mo, a, b, f"post_d1_hazard_v0 {metric} − ceiling_hazard_v0 cond"))
# h_2 calibration
h2 = [1 - float(r["S_cond_2"]) for r in pd1 if r["status"] == "FIT_OK"]; obs = [1.0 if int(r["realized_L"]) < 2 else 0.0 for r in pd1 if r["status"] == "FIT_OK"]
print(f"post_d1 mean h_2 {sum(h2)/len(h2):.4f}, observed D2 break rate {sum(obs)/len(obs):.4f}")

# (d) break cells (near era)
br = read_csv(ROOT / "docs/faz8/backtest/break_floor_v0_fold_ledger.csv")
print("break statuses:", dict(Counter(r["status"] for r in br)), "selected C F1 (FIT_OK):", dict(Counter(r["selected_C_F1"] for r in br if r["status"] == "FIT_OK")))
f2ok = sum(1 for r in br if r["p_F2"] != "" and r["realized_F2"] != "" and r["first_trading_date"] >= "2024-01-01"); print("F2 near-era scorable:", f2ok)
def num(x): return None if x in ("", None) else float(x)
for label, a_, b_, y_ in (("F1 model − product", "p_F1", "product_F1", "realized_F1"), ("F1 model − @ZERO", "p_F1", "zero_F1", "realized_F1"),
                           ("F1 model − by_type", "p_F1", "by_type_F1", "realized_F1"), ("F2 model − product", "p_F2", "product_F2", "realized_F2"),
                           ("F2 model − @ZERO", "p_F2", "zero_F2", "realized_F2"), ("info product − @ZERO", "product_F1", "zero_F1", "realized_F1")):
    d, mo, a, b = [], [], [], []
    for r in br:
        pa, pb_, y = num(r[a_]), num(r[b_]), num(r[y_])
        if pa is None or pb_ is None or y is None or r["first_trading_date"] < "2024-01-01": continue
        if label.startswith("info") and num(r["p_F1"]) is None: continue
        ea, eb = (pa - y) ** 2, (pb_ - y) ** 2
        a.append(ea); b.append(eb); d.append(ea - eb); mo.append(r["first_trading_date"][:7])
    results.append(summarize(d, mo, a, b, f"break_floor_v0 near-era {label}"))
sb = load_json(ROOT / "scores/scores_break.json")["models"][0]["card"]["backtest_info"]
print("   scores_break.json backtest_info:", json.dumps({k: sb[k] for k in ("F1_product", "F1_zero")}))
# calibration near era
pts = [(num(r["p_F1"]), num(r["realized_F1"]), num(r["test_b_floor"])) for r in br if num(r["p_F1"]) is not None and num(r["realized_F1"]) is not None and r["first_trading_date"] >= "2024-01-01"]
print(f"break calib near-era: n {len(pts)} mean p {sum(p for p,_,_ in pts)/len(pts):.4f} obs {sum(y for _,y,_ in pts)/len(pts):.4f}")
for cls in (0.0, 1.0):
    sub = [(p, y) for p, y, f in pts if f == cls]
    print(f"   b_floor={int(cls)}: n {len(sub)} mean p {sum(p for p,_ in sub)/len(sub):.3f} obs {sum(y for _,y in sub)/len(sub):.3f}")
# (e) faz7 near era: v1_* − v0
for mid in ("ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled"):
    rows = read_csv(G / f"macos_golden_faz7/{mid}_fold_ledger.csv")
    d, mo, a, b = [], [], [], []
    for r in rows:
        if r["status"] != "FIT_OK" or r["first_trading_date"] < "2024-01-01" or r["ticker"] not in v0: continue
        L = int(r["realized_L"]); la, lb = rps(S_of(r), L), rps(S_of(v0[r["ticker"]]), L)
        a.append(la); b.append(lb); d.append(la - lb); mo.append(r["first_trading_date"][:7])
    ne = next(x for x in scores["models"] if x["model_id"] == mid)["backtest"]["near_era"]
    results.append(summarize(d, mo, a, b, f"{mid} near-era RPS − ceiling_hazard_v0", (ne["diff"], ne["ci95"]))); print("   scores.json near_era:", ne["diff"], ne["ci95"], ne["label"], ne["n"], ne["n_blocks"])
# (f) fall pooled − h99 D10 Brier near era
fp = read_csv(G / "macos_golden_faz7c/fall_d10_v0_pooled_fold_ledger.csv"); fh = {r["ticker"]: r for r in read_csv(G / "macos_golden_faz7c/fall_d10_v0_h99_fold_ledger.csv") if r["horizon"] == "D10" and r["logit_probability"] != ""}
d, mo, a, b = [], [], [], []
for r in fp:
    if r["horizon"] != "D10" or r["logit_probability"] == "" or r["prediction_date"] < "2024-01-01" or r["ticker"] not in fh: continue
    y = int(r["realized_direction"]); la, lb = (float(r["logit_probability"]) - y) ** 2, (float(fh[r["ticker"]]["logit_probability"]) - y) ** 2
    a.append(la); b.append(lb); d.append(la - lb); mo.append(r["prediction_date"][:7])
ne = scores["faz7c_near_era"]
results.append(summarize(d, mo, a, b, "fall_d10_v0_pooled − fall_d10_v0_h99 D10 Brier near-era", (ne["diff"], ne["ci95"]))); print("   scores.json:", ne["diff"], ne["ci95"], ne["label"], ne["n"])
# (h) ceiling_path_v0 D5 MAE − base_train_median
cp = read_csv(G / "macos_golden_faz4/ceiling_path_v0_fold_ledger.csv"); rl = {(r["ticker"]): r for r in read_csv(G / "macos_golden/base_train_median_fold_ledger.csv") if r["horizon"] == "D5"}
d, mo, a, b = [], [], [], []
for r in cp:
    if r["status"] != "OK" or r["D5_return"] == "" or r["ticker"] not in rl: continue
    R = float(r["realized_R_D5"]); ea, eb = abs(float(r["D5_return"]) - R), abs(float(rl[r["ticker"]]["rule_return"]) - R)
    a.append(ea); b.append(eb); d.append(ea - eb); mo.append(r["first_trading_date"][:7])
ex = cell_of("ceiling_path_v0", "D5", "MAE", "base_train_median")
results.append(summarize(d, mo, a, b, "ceiling_path_v0 D5 MAE − base_train_median", (ex[0], ex[1]))); print("   scores.json:", ex)

# ---- verdict consistency scan over every cell in scores*.json (CLAUDE.md rule 6)
def check_verdict(c):
    n, ci, v = c.get("n"), c.get("ci95"), c.get("verdict")
    if n is None or n == 0: return v is None
    if n < 10: return v is None
    if n < 30: return v == "yetersiz örnek"
    if ci is None: return v == "aralık için yetersiz"
    lo, hi = ci
    exp = "geçiyor" if hi < 0 else "geçemiyor" if lo > 0 else "ayırt edilemiyor"
    return v in (exp, exp + " (zaman-dışı terazide)")
bad = []; tot = Counter()
for m in scores["models"]:
    for c in m["backtest"]["cells"]:
        tot["backtest"] += 1; tot[("bt", c["verdict"])] += 1
        if not check_verdict(c): bad.append((m["model_id"], c["horizon_or_k"], c["metric"], c["rule_id"], c["n"], c["ci95"], c["verdict"]))
    for c in m["live"]["cells"]:
        tot["live"] += 1
        if not check_verdict(c): bad.append(("live", m["model_id"]))
oot = load_json(ROOT / "scores/scores_oot.json")
for key in ("oot_pre_h99", "oot_pre_h99_sealed", "oot_pre_h99_all"):
    for m in oot[key]["models"]:
        for c in m.get("cells", []):
            tot[key] += 1
            if not check_verdict(c): bad.append((key, m["model_id"], c["horizon_or_k"], c["metric"], c["rule_id"], c["n"], c["ci95"], c["verdict"]))
for key in ("post_d1", "post_d1_sealed", "post_d1_all"):
    for m in oot[key]["models"]:
        for c in m.get("cells", []):
            tot[key] += 1
            if not check_verdict(c): bad.append((key, c.get("metric"), c.get("rule_id"), c["n"], c["ci95"], c["verdict"]))
print("verdict scan totals:", {str(k): v for k, v in tot.items()})
print("verdict rule violations:", len(bad)); [print("   ", x) for x in bad[:20]]
v15m = next(x for x in scores["models"] if x["model_id"] == "v1_5_h99")
print("v1_5_h99 backtest cells:", len(v15m["backtest"]["cells"]), Counter(c["verdict"] for c in v15m["backtest"]["cells"]))
allc = [c for m in scores["models"] for c in m["backtest"]["cells"]]
print("all backtest cells:", len(allc), "geçiyor:", sum(c["verdict"] == "geçiyor" for c in allc))
json.dump(results, open(Path(__file__).parent / "s4_out.json", "w"), indent=1, ensure_ascii=False)

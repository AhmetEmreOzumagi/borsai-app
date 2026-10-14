"""Adım 3: walk-forward kesim kuralı bütün ledger'larda (borsai import edilmez)."""
from __future__ import annotations
import sys, json
from decimal import Decimal
from pathlib import Path
from collections import Counter, defaultdict
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa

TT = read_csv(ROOT / "data/training_table.csv")
ORDER = [r["ticker"] for r in TT]
BY = {r["ticker"]: r for r in TT}
assert [(r["first_trading_date"], r["ticker"]) for r in TT] == sorted((r["first_trading_date"], r["ticker"]) for r in TT)
SESS = read_csv(ROOT / "data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv")
sess = defaultdict(dict)
for r in SESS:
    sess[r["ticker"]][int(r["session_number"])] = r
HOR = {"D1": 1, "D3": 3, "D5": 5, "D10": 10}
def tdate(t, h): return sess[t][HOR[h]]["target_session_date"]
def sdate(t, d): return sess[t][d]["target_session_date"]
PB = {r["ticker"]: r for r in read_csv(ROOT / "data/raw/PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv")}

out = {}
def plan_v15_check(path, cutoff_of, label):
    rows = read_csv(path)
    bad = Counter(); n = 0; scorable = Counter(); hash_ok = 0; targ_ok = 0
    for r in rows:
        h = r["horizon"]; k = r["ticker"]; p = cutoff_of(k)
        training = [j for j in ORDER if tdate(j, h) < p]
        n += 1
        if r["prediction_date"] != p: bad["prediction_date"] += 1
        if int(r["training_n"]) != len(training): bad["training_n"] += 1
        if r["training_tickers_sha256"] == identity_hash(training): hash_ok += 1
        th = identity_hash([f"{t}|{tdate(t, h)}|{BY[t][f'R_{h}']}|{BY[t][f'Y_{h}']}" for t in training])
        if r["training_targets_sha256"] == th: targ_ok += 1
        if any(tdate(j, h) >= p for j in training) or k in training: bad["leak"] += 1
        if any(BY[j]["first_trading_date"] == BY[k]["first_trading_date"] for j in training): bad["same_day"] += 1
        if len(training) >= 10: scorable[h] += 1
    out[label] = dict(rows=n, tickers_hash_ok=hash_ok, targets_hash_ok=targ_ok, bad=dict(bad), scorable=dict(scorable))
    print(label, out[label])

T_of = lambda k: BY[k]["first_trading_date"]
B_of = lambda k: PB[k]["first_bookbuilding_date"]
G = ROOT / "tests/reference"
plan_v15_check(G / "macos_golden/v1_5_h99_fold_ledger.csv", T_of, "v1_5_h99 (PLAN_V15)")
for f in ("base_train_median", "base_rate", "base_always_ceiling", "base_last10_rate", "base_train_mean", "base_zero"):
    plan_v15_check(G / f"macos_golden/{f}_fold_ledger.csv", T_of, f"{f} (PLAN_V15)")
plan_v15_check(G / "macos_golden_faz1b/v1_6_h99_fold_ledger.csv", T_of, "v1_6_h99 (PLAN_V15)")
plan_v15_check(G / "macos_golden_faz1b/v1_5_market20_v0_fold_ledger.csv", T_of, "v1_5_market20_v0 (PLAN_V15)")
plan_v15_check(G / "macos_golden_faz1b/pb_v0_fold_ledger.csv", B_of, "pb_v0 (PLAN_PB)")
for f in ("base_train_median__pb", "base_rate__pb"):
    plan_v15_check(G / f"macos_golden_faz1b/{f}_fold_ledger.csv", B_of, f"{f} (PLAN_PB)")

# PB bookbuilding cutoff leak: training first_trading_date < B
rows = read_csv(G / "macos_golden_faz1b/pb_v0_fold_ledger.csv")
viol = 0
for r in rows:
    k = r["ticker"]; b = B_of(k); h = r["horizon"]
    training = [j for j in ORDER if tdate(j, h) < b]
    if any(not BY[j]["first_trading_date"] < b for j in training): viol += 1
print("pb_v0: folds where a training ipo listed on/after B:", viol)

# ---- ceiling plans: PP rows
L = {t: int(BY[t]["ceiling_streak_L"]) for t in ORDER}
def pp_rows(j, cutoff):
    rows = []
    for d in range(1, 11):
        if d - 1 > L[j]: break
        if sdate(j, d) >= cutoff: break
        rows.append((j, d, int(L[j] == d - 1)))
    return rows

def ceiling_check(path, eligible, cutoff_of, label, day_min=1):
    rows = read_csv(path); n = 0; ok_hash = 0; ok_max = 0; bad = Counter(); scor = 0
    for r in rows:
        k = r["ticker"]; c = cutoff_of(k); n += 1
        cands = [j for j in eligible if BY[j]["first_trading_date"] < c]
        pp = [x for j in cands for x in pp_rows(j, c) if x[1] >= day_min]
        training = list(dict.fromkeys(x[0] for x in pp))
        h = identity_hash([f"{t}|{d}|{e}" for t, d, e in pp])
        if r.get("training_pp_sha256","") == "": pass
        elif r["training_pp_sha256"] == h: ok_hash += 1
        dates = [sdate(j, d) for j, d, _ in pp]
        mx = max(dates) if dates else ""
        if (r["training_max_session_date"] or "") == mx and (mx == "" or mx < c): ok_max += 1
        else: bad["max_date"] += 1
        if r.get("training_n_pp_rows","") == "":
            bad["no_training_cols(status=%s)" % r.get("status")] += 1; continue
        if int(r["training_n_pp_rows"]) != len(pp): bad["n_pp"] += 1
        if int(r["training_n_ipo"]) != len(training): bad["n_ipo"] += 1
        if k in training: bad["self"] += 1
        ev = sum(e for _, _, e in pp)
        if len(training) >= 10 and ev >= 5 and len(pp) - ev >= 5: scor += 1
    out[label] = dict(rows=n, pp_hash_ok=ok_hash, max_date_ok=ok_max, bad=dict(bad), scorable=scor)
    print(label, out[label])

F3 = [t for t in ORDER if BY[t]["total_demand_multiple"] not in ("", None)]
print("f3-present ipos:", len(F3))
for f in ("ceiling_hazard_v0", "ceiling_hazard_v0@INF", "base_km_expanding", "base_km_last10", "base_always_ceiling__ceiling"):
    ceiling_check(G / f"macos_golden_faz1b/{f}_fold_ledger.csv", F3, T_of, f"{f} (PLAN_CEILING)")
for f in ("pb_ceiling_v0", "pb_ceiling_v0@INF", "base_km_expanding__pb_ceiling", "base_km_last10__pb_ceiling"):
    ceiling_check(G / f"macos_golden_faz1b/{f}_fold_ledger.csv", ORDER, B_of, f"{f} (PLAN_PB_CEILING)")
# post_d1: d>=2 rows, same folds
ceiling_check(G / "macos_golden_faz5/post_d1_hazard_v0_fold_ledger.csv", F3, T_of, "post_d1_hazard_v0 (PLAN_POST_D1, d>=2)", day_min=2)
# faz7 clip/real: PLAN_CEILING folds (same pp set as v0)
for f in ("ceiling_hazard_v1_clip", "ceiling_hazard_v1_real"):
    ceiling_check(G / f"macos_golden_faz7/{f}_fold_ledger.csv", F3, T_of, f"{f} (PLAN_CEILING)")
# pooled: only max_session_date < T from ledger
for f in ("ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF", "base_km_expanding__pooled"):
    rows = read_csv(G / f"macos_golden_faz7/{f}_fold_ledger.csv")
    viol = sum(1 for r in rows if r["training_max_session_date"] and not r["training_max_session_date"] < r["prediction_date"])
    print(f"{f} (POOLED): rows {len(rows)}, max_session_date >= T violations: {viol}; n_oot_open range {min(int(r['training_n_oot_open']) for r in rows)}..{max(int(r['training_n_oot_open']) for r in rows)}")
    out[f] = dict(rows=len(rows), viol=viol)

# ---- ceiling path ledgers: cells_max_session_date < first_trading_date
for d, f in (("macos_golden_faz4", "ceiling_path_v0"), ("macos_golden_faz4", "pb_ceiling_path_v0")):
    rows = read_csv(G / d / f"{f}_fold_ledger.csv")
    cut = (lambda r: r["first_trading_date"]) if f == "ceiling_path_v0" else (lambda r: B_of(r["ticker"]))
    viol = sum(1 for r in rows if r["cells_max_session_date"] and not r["cells_max_session_date"] < cut(r))
    print(f"{f}: rows {len(rows)}, cells_max_session_date >= cutoff: {viol}, status counts {Counter(r['status'] for r in rows)}")

# ---- fall ledgers (PLAN_FALL_H99: PLAN_V15 rule on set rows)
for f in ("fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO"):
    rows = read_csv(G / f"macos_golden_faz7c/{f}_fold_ledger.csv")
    # training set hash reproduction only for h99 (H99 rows with f3 present AND... ) try f3-present and all
    ok = Counter(); n = 0
    for r in rows:
        n += 1; h = r["horizon"]; k = r["ticker"]; p = r["prediction_date"]
        for name, cands in (("F3", F3), ("ALL", ORDER)):
            training = [j for j in cands if tdate(j, h) < p]
            if r["training_tickers_sha256"] == identity_hash(training): ok[name] += 1
    print(f"{f}: rows {n}, tickers hash reproduced from H99 f3-set {ok['F3']}, from all-H99 {ok['ALL']}; statuses {Counter(r['logit_status'] for r in rows)}")

# ---- break ledger
def break_table():
    units = {}
    for t in ORDER:
        Lc = 0; b = None
        for h in range(1, 11):
            r = sess[t][h]
            if Decimal(r["thb_raw_close"]) == Decimal(r["thm_raw_upper_limit"]): Lc += 1; continue
            b = h; break
        units[t] = (Lc, b)
    return units
units = break_table()
dist = Counter(b for _, b in units.values()); print("break b distribution:", dict(sorted((k if k is not None else 99, v) for k, v in dist.items())), "L=10:", sum(1 for Lc, b in units.values() if Lc == 10))
rows = read_csv(ROOT / "docs/faz8/backtest/break_floor_v0_fold_ledger.csv")
ok_h = 0; viol = 0; n = 0; stat = Counter()
def label_date(j, head):
    Lj, bj = units[j]
    if bj is None or bj > 9: return None
    hh = bj + (1 if head == "F1" else 2)
    if hh > 10: return None
    return sdate(j, hh)
for r in rows:
    n += 1; k = r["ticker"]; T = r["break_date"]; stat[r["status"]] += 1
    assert T == sdate(k, int(r["b"]))
    train1 = [j for j in ORDER if label_date(j, "F1") is not None and label_date(j, "F1") < T]
    if r["training_tickers_sha256"] == identity_hash(train1): ok_h += 1
    if r["training_max_label_date"] and not r["training_max_label_date"] < T: viol += 1
    if r["cells_max_session_date"] and not r["cells_max_session_date"] < BY[k]["first_trading_date"]: viol += 1
print(f"break_floor_v0: rows {n}, F1 training hash reproduced {ok_h}, max_label/cells date violations {viol}, statuses {dict(stat)}, near-era FIT_OK {sum(1 for r in rows if r['status']=='FIT_OK' and r['first_trading_date']>='2024-01-01')}")
json.dump(out, open(Path(__file__).parent / "s3_out.json", "w"), indent=1)

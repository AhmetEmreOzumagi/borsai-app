#!/usr/bin/env python3
"""Faz 2C koşullu skorlama bağımsız yeniden hesabı (BORSAI_FAZ5_FABLE_REPRO_AUDIT adım 4). `borsai` IMPORT EDİLMEZ; stdlib.
Girdiler (CANLI veri): scores/scores.json (karşılaştırma hedefi + koşulsuz canlı satırların sınıf/kayıt kimliği),
registry/ipos.csv, registry/records/<T>/<kayıt>.json (modellerin ve kuralların S vektörleri), data/outcomes/<T>.csv.
Tanım: SPEC_CEILING_PATH_V0 §7 (S_k / S_j; RPS_j; Brier k = j+1, 10; sınıf mirası; payda L ≥ j; eksik ufuk hep birlikte)."""
import csv, json, sys
from pathlib import Path

ROOT = Path("/Users/ahmet/Desktop/BorsAi")
S = json.load(open(ROOT / "scores" / "scores.json", encoding="utf-8"))
with open(ROOT / "registry" / "ipos.csv", encoding="utf-8", newline="") as fh:
    IPOS = list(csv.DictReader(fh))
OUTC = {}
for p in sorted((ROOT / "data" / "outcomes").glob("*.csv")):
    if p.stem == "COMPLETENESS":
        continue
    with open(p, encoding="utf-8", newline="") as fh:
        OUTC[p.stem] = list(csv.DictReader(fh))
RETRO = {(x["model_id"], x["ticker"]) for x in S["retro_info"]}
TOL = 1e-9
MAXD = 0.0
PROBLEMS = []
STATES = {}


def rec_cells(ticker, record_id):
    rec = json.load(open(ROOT / "registry" / "records" / ticker / record_id, encoding="utf-8"))
    return {c["model_id"]: c for c in rec["models"]}


def membership(rows, j):
    labels = []
    for k in range(1, j + 1):
        r = rows[k - 1]
        ok = r["status"] in ("OK", "NA_LIMIT") and r["ceiling_close"] not in ("", "NA")
        labels.append(int(r["ceiling_close"]) if ok else None)
    if 0 in labels:
        return "NOT_MEMBER"
    return "MEMBER" if all(x == 1 for x in labels) else "UNDETERMINED"


def streak(rows):
    labels = []
    for r in rows:
        if r["status"] in ("OK", "NA_LIMIT"):
            labels.append(None if r["ceiling_close"] == "NA" else int(r["ceiling_close"]))
        else:
            break
    L = 0
    for x in labels:
        if x == 1:
            L += 1
        elif x == 0:
            return L
        else:
            return None
    return L if L == 10 else None   # ilk 0 görülmeden bitti: L bilinmiyor (10 ise tam)


def target(rows, j):
    sts = [rows[k - 1]["status"] for k in range(j + 1, 11)]
    if "PENDING" in sts:
        return "PENDING", None, f"D_{j + 1}..D_10 seanslarından en az birinin sonucu bekleniyor"
    if "TARGET_UNAVAILABLE" in sts:
        return "TARGET_UNAVAILABLE", None, "SESSION_NOT_FORMED"
    L = streak(rows)
    if L is None:
        return "TARGET_UNAVAILABLE", None, "NA_LIMIT"
    return "SCORED", L, None


def l_at_least(rows):
    n = 0
    for r in rows:
        if r["status"] in ("OK", "NA_LIMIT") and r["ceiling_close"] == "1":
            n += 1
        else:
            break
    return n


def s_part(Sv, j, L):
    S0 = [1.0] + [float(x) for x in Sv]
    if S0[j] <= 0:
        return None
    sc = {str(k): S0[k] / S0[j] for k in range(j + 1, 11)}
    out = {"S_cond": sc, "rps_cond": None, "brier_next": None, "brier_10": None}
    if L is not None:
        out["rps_cond"] = sum((sc[str(k)] - (1.0 if L >= k else 0.0)) ** 2 for k in range(j + 1, 11)) / (10 - j)
        out["brier_next"] = (sc[str(j + 1)] - (1.0 if L >= j + 1 else 0.0)) ** 2
        out["brier_10"] = (sc["10"] - (1.0 if L >= 10 else 0.0)) ** 2
    return out


def cmp_num(path, a, b):
    global MAXD
    if a is None or b is None:
        if a != b:
            PROBLEMS.append((path, a, b))
        return
    d = abs(float(a) - float(b))
    MAXD = max(MAXD, d)
    if d > TOL:
        PROBLEMS.append((path, a, b))


def cmp_eq(path, a, b):
    if a != b:
        PROBLEMS.append((path, a, b))


COMPS = {"ceiling_hazard_v0": ["ceiling_hazard_v0@INF", "base_km_expanding", "base_km_last10", "base_always_ceiling"],
         "pb_ceiling_v0": ["pb_ceiling_v0@INF", "base_km_expanding", "base_km_last10", "base_always_ceiling"],
         "ceiling_path_v0": ["ceiling_hazard_v0@INF", "base_km_expanding", "base_km_last10", "base_always_ceiling"],
         "ceiling_path_v0@INF": ["base_km_expanding", "base_km_last10", "base_always_ceiling"],
         "pb_ceiling_path_v0": ["pb_ceiling_v0@INF", "base_km_expanding", "base_km_last10", "base_always_ceiling"]}
n_rows_checked = n_cells = 0
summary = {}
for m in S["models"]:
    if "conditional" not in m:
        continue
    mid = m["model_id"]
    cond = m["conditional"]
    live = {r["ticker"]: r for r in m["live"]["rows"]}
    cmp_eq(f"{mid}.schema_version", cond["schema_version"], "borsai.scores_conditional/1")
    cmp_eq(f"{mid}.scale", cond["scale"], "live_conditional")
    cmp_eq(f"{mid}.comparators.S_cond", cond["comparators"]["S_cond"], COMPS.get(mid, []))
    summary[mid] = {}
    for bj in cond["by_j"]:
        j = bj["j"]
        mine_rows = []
        n = {"n_skipped": 0, "n_retro": 0, "n_no_record": 0, "n_undetermined": 0}
        for ipo in IPOS:
            t = ipo["ticker"]
            if ipo["status"] not in ("FROZEN", "SKIPPED"):
                continue
            rows = OUTC.get(t)
            mem = membership(rows, j) if rows is not None else "UNDETERMINED"
            if mem == "NOT_MEMBER":
                continue
            if ipo["status"] == "SKIPPED":
                n["n_skipped"] += 1
                continue
            if mem == "UNDETERMINED":
                n["n_undetermined"] += 1
                continue
            lr = live.get(t)
            if lr is None:
                n["n_retro" if (mid, t) in RETRO else "n_no_record"] += 1
                continue
            tgt, L, reason = target(rows, j)
            row = {"ticker": t, "class": lr["class"], "record_id": lr["record_id"], "L": L, "L_at_least": l_at_least(rows),
                   "status": tgt, "target_status": tgt, "target_reason": reason, "rules": {}}
            cells = rec_cells(t, lr["record_id"])
            for rid in COMPS.get(mid, []):
                if rid == "base_always_ceiling":
                    row["rules"][rid] = {"record_id": None, **s_part([1.0] * 10, j, L)}
                    continue
                c = cells[rid]
                if c["status"] != "PREDICTED":
                    row["rules"][rid] = {"record_id": lr["record_id"], "refused": c["refusal"]}
                    continue
                sp = s_part(c["output"]["S"], j, L)
                row["rules"][rid] = {"record_id": lr["record_id"], **(sp if sp is not None else {"undefined": f"S_{j} = 0"})}
            mc = cells[mid]
            if lr["status"] == "REFUSED" or mc["status"] != "PREDICTED":
                row["status"] = "REFUSED"
            else:
                sp = s_part(mc["output"]["S"], j, L)
                if sp is None:
                    row["status"] = "CONDITION_UNDEFINED"
                else:
                    row.update(sp)
            mine_rows.append(row)
            STATES.setdefault((t, j), set()).add(tgt)
        got = bj["rows"]
        cmp_eq(f"{mid}.j{j}.tickers", [r["ticker"] for r in got], [r["ticker"] for r in mine_rows])
        for g, r in zip(got, mine_rows):
            n_rows_checked += 1
            pre = f"{mid}.j{j}.{r['ticker']}"
            for k in ("class", "record_id", "L", "L_at_least", "status", "target_status", "target_reason"):
                cmp_eq(f"{pre}.{k}", g.get(k), r.get(k))
            assert (r["L"] if r["L"] is not None else r["L_at_least"]) >= j            # L < j paydada yok
            if r["status"] in ("SCORED", "PENDING", "TARGET_UNAVAILABLE"):
                for k in range(j + 1, 11):
                    cmp_num(f"{pre}.S_cond[{k}]", g["S_cond"][str(k)], r["S_cond"][str(k)])
                for k in ("rps_cond", "brier_next", "brier_10"):
                    cmp_num(f"{pre}.{k}", g[k], r[k])
            for rid, rv in r["rules"].items():
                gv = g["rules"][rid]
                cmp_eq(f"{pre}.rules.{rid}.record_id", gv.get("record_id"), rv.get("record_id"))
                if "S_cond" in rv:
                    for k in range(j + 1, 11):
                        cmp_num(f"{pre}.rules.{rid}.S_cond[{k}]", gv["S_cond"][str(k)], rv["S_cond"][str(k)])
                    for k in ("rps_cond", "brier_next", "brier_10"):
                        cmp_num(f"{pre}.rules.{rid}.{k}", gv.get(k), rv.get(k))
                else:
                    cmp_eq(f"{pre}.rules.{rid}.refused/undefined", {k: v for k, v in gv.items() if k != "record_id"},
                           {k: v for k, v in rv.items() if k != "record_id"})
        scored = [r for r in mine_rows if r["status"] == "SCORED"]
        cnt = {"n_scored": len(scored), "n_refused": sum(r["status"] == "REFUSED" for r in mine_rows),
               "n_target_unavailable": sum(r["status"] == "TARGET_UNAVAILABLE" for r in mine_rows),
               "n_pending": sum(r["status"] == "PENDING" for r in mine_rows),
               "n_undefined": sum(r["status"] == "CONDITION_UNDEFINED" for r in mine_rows),
               "n_live": sum(r["class"] == "LIVE" for r in scored), "n_late": sum(r["class"] == "LATE_RECORD" for r in scored), **n}
        for k, v in cnt.items():
            cmp_eq(f"{mid}.j{j}.{k}", bj[k], v)
        cmp_eq(f"{mid}.j{j}.cells(n<10 -> [])", bj["cells"], [] if len(scored) < 10 else bj["cells"])
        n_cells += len(bj["cells"])
        summary[mid][j] = {"rows": len(mine_rows), "scored": len(scored), "pending": cnt["n_pending"], "undetermined": n["n_undetermined"],
                           "retro": n["n_retro"], "refused": cnt["n_refused"], "cells": len(bj["cells"])}
print("modeller (koşullu blok):", list(summary))
for mid, d in summary.items():
    print(f"  {mid:22s} " + " ".join(f"j{j}:{v['rows']}/{v['scored']}s/{v['pending']}p/{v['undetermined']}u/{v['retro']}r/{v['refused']}ref/{v['cells']}c" for j, v in d.items()))
print(f"karşılaştırılan satır {n_rows_checked}; hücre sayısı (hepsi n < 10 olmalı: 0) {n_cells}; maks |Δ| {MAXD:.3e}; uyuşmazlık {len(PROBLEMS)}")
for p in PROBLEMS[:20]:
    print("  UYUŞMAZLIK:", p)
print("hedef durumu (ticker, j) başına bütün modellerde aynı:", all(len(v) == 1 for v in STATES.values()), "; (ticker, j) çifti sayısı", len(STATES))
pend = sorted({k for k, v in STATES.items() if v == {"PENDING"}})
print("PENDING çiftler (bütün modellerde aynı anda):", pend)
assert not any(m == "borsai" or m.startswith("borsai.") for m in sys.modules)
json.dump({"max_abs_delta": MAXD, "n_rows_checked": n_rows_checked, "n_cells": n_cells, "problems": PROBLEMS, "summary": summary,
           "pending_pairs": pend, "target_status_same_across_models": all(len(v) == 1 for v in STATES.values())},
          open(Path(__file__).with_name("faz2c_recompute_out.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
print("DONE; borsai import:", any(m.startswith("borsai") for m in sys.modules))

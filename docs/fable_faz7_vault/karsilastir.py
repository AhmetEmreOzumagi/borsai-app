#!/usr/bin/env python3
"""BORSAI_FAZ7_FABLE_VAULT_RECOMPUTE — Faz 2: BAGIMSIZ.json ile scores/scores_oot.json karşılaştırması.

Karşılaştırılan: sınıf ve durum sayıları (kasa, 27 model + post_d1), Faz 1'in bütün hücreleri (n, blok, ort. fark,
%95 aralık, K/Kb/E, model/kural değeri, hüküm), `oot_pre_h99_all` (yalnız 19 eski model, n = açık + kasa), yıl kırılımları.
Toleranslar: n/blok/sayımlar birebir; fark ve aralık |Δ| ≤ 1e-9 (aynı üretici); aksi hâlde ≤ 0.005 ve hüküm aynıysa KÜÇÜK.
`borsai` import edilmez; üye kodu basılmaz. Çıktı: karsilastir_cikti.json (yalnız sayı ve hücre adı).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOL = 1e-9
TOL_SMALL = 0.005

mine = json.loads((HERE / "BAGIMSIZ.json").read_text(encoding="utf-8"))
theirs = json.loads((ROOT / "scores" / "scores_oot.json").read_text(encoding="utf-8"))
sealed = {m["model_id"]: m for m in theirs["oot_pre_h99_sealed"]["models"]}
opened = {m["model_id"]: m for m in theirs["oot_pre_h99"]["models"]}
allb = {m["model_id"]: m for m in theirs["oot_pre_h99_all"]["models"]}
pd_sealed = theirs["post_d1_sealed"]["models"][0]
pd_open = theirs["post_d1"]["models"][0]
pd_all = theirs["post_d1_all"]["models"][0]

out = {"head_in_scores": theirs["code"]["git_head"][:7], "generated_at_utc": theirs["generated_at_utc"], "findings": []}
findings = out["findings"]


def note(level, kind, text):
    findings.append({"level": level, "kind": kind, "text": text})


# ---------------------------------------------------------------- sınıf ve durum
row_keys = sorted(sealed["v1_5_h99"]["rows"][0].keys())
out["row_keys"] = row_keys
status_map = {"SCORED": "SCORED", "REFUSED": "REFUSED", "NOT_APPLICABLE_REGIME": "NOT_APPLICABLE_REGIME"}
cls_cmp, st_cmp = {}, {}
for mid, mm in sealed.items():
    rows = mm["rows"]
    cls = Counter(r["class"] for r in rows)
    st = Counter(r["cell_status"] for r in rows)
    cls_cmp[mid] = {"theirs": dict(cls), "mine": mine["class_by_model"][mid], "equal": dict(cls) == mine["class_by_model"][mid]}
    mine_st = mine["status_by_model"][mid]
    # Opus satır durumu: PREDICTED → skorlanan; kendi sayaçlarıyla da karşılaştır
    theirs_st = {"SCORED": mm["n_scored"], "REFUSED": mm["n_refused"], "NOT_APPLICABLE_REGIME": mm["n_not_applicable_regime"]}
    theirs_st = {k: v for k, v in theirs_st.items() if v}
    st_cmp[mid] = {"theirs_counters": theirs_st, "theirs_cell_status": dict(st), "mine": mine_st,
                   "equal": theirs_st == mine_st, "n_rows": len(rows),
                   "zero_counters_ok": mm["n_oot_retro"] == mm["n_pending"] == mm["n_skipped"] == mm["n_target_unavailable"] == 0}
out["class_by_model"] = cls_cmp
out["status_by_model"] = st_cmp
out["class_total_equal"] = all(v["equal"] for v in cls_cmp.values()) and sum(len(m["rows"]) for m in sealed.values()) == 1728
out["status_total_equal"] = all(v["equal"] and v["zero_counters_ok"] and v["n_rows"] == 64 for v in st_cmp.values())
if not out["class_total_equal"]:
    note("KRİTİK", "kod", "kasa sınıf sayıları farklı")
if not out["status_total_equal"]:
    note("ÖNEMLİ", "kod", "kasa durum sayıları farklı")

pd_rows = pd_sealed["rows"]
pd_cls = Counter(r.get("class") for r in pd_rows)
pd_st = Counter(r.get("cell_status") for r in pd_rows)
out["post_d1_sealed"] = {
    "theirs": {"n_rows": pd_sealed["n_rows"], "n_scored": pd_sealed["n_scored"], "n_refused": pd_sealed["n_refused"],
               "n_not_applicable": pd_sealed["n_not_applicable"], "n_oot_retro": pd_sealed["n_oot_retro"],
               "row_class": dict(pd_cls), "row_cell_status": dict(pd_st), "exposure_class": pd_sealed["exposure_class"]},
    "mine": {"class": mine["class_counts_post_d1"], "status": mine["status_by_model"]["post_d1_hazard_v0"]},
}
pd_ok = (pd_sealed["n_scored"] == mine["status_by_model"]["post_d1_hazard_v0"]["SCORED"]
         and pd_sealed["n_refused"] == mine["status_by_model"]["post_d1_hazard_v0"]["REFUSED"]
         and pd_sealed["n_not_applicable"] == mine["status_by_model"]["post_d1_hazard_v0"]["NOT_APPLICABLE:D1_NOT_CEILING"]
         and pd_sealed["n_oot_retro"] == 0 and pd_cls.get("OOT_BLIND", 0) == pd_sealed["n_rows"]
         and mine["class_counts_post_d1"] == {"OOT_BLIND": 64})
out["post_d1_sealed"]["equal"] = pd_ok
if not pd_ok:
    note("ÖNEMLİ", "kod", "post_d1 kasa sınıf/durum sayıları farklı")


# ---------------------------------------------------------------- hücreler
def find_cell(cells, metric, hk, output, rule_id):
    hits = [c for c in cells if c["metric"] == metric and c["horizon_or_k"] == hk and c["output"] == output and c["rule_id"] == rule_id]
    return hits[0] if len(hits) == 1 else None


def spec_of(group, key, c):
    model, metric, _, comp = key.split("|")
    if group == "old_primary":
        if metric == "RPS":
            return model, ("RPS", None, "S", comp)
        return model, ("MAE", c["horizon"], "return", comp)
    if group == "v1":
        if metric == "RPS":
            return model, ("RPS", None, "S", comp)
        return model, ("Brier", 10, "S", comp)
    if group == "c":
        return model, ("Brier", c["horizon"], "p_up", comp)
    if group == "post_d1":
        return model, ("RPS", None, "S_cond", "ceiling_hazard_v0")
    raise ValueError(group)


def close(a, b, tol):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol


def verdict_norm(v):
    if v is None:
        return None
    return v.replace(" (zaman-dışı terazide)", "")


cell_cmp = {}
n_cells = n_exact = n_small = n_big = 0
for group, cells in mine["cells_summary"].items():
    for key, c in cells.items():
        model, (metric, hk, output, rule_id) = spec_of(group, key, c)
        src = pd_sealed["cells"] if group == "post_d1" else sealed[model]["cells"]
        t = find_cell(src, metric, hk, output, rule_id)
        n_cells += 1
        if t is None:
            cell_cmp[f"{group}:{key}"] = {"found": False}
            note("ÖNEMLİ", "bilgi", f"hücre skor dosyasında bulunamadı: {key}")
            n_big += 1
            continue
        d_diff = abs(t["diff"] - c["mean_diff"])
        d_ci = None if (t["ci95"] is None or c["ci95"] is None) else max(abs(t["ci95"][0] - c["ci95"][0]), abs(t["ci95"][1] - c["ci95"][1]))
        same_counts = (t["n"] == c["n"] and t["n_blocks"] == c["n_blocks"] and t["wins"] == c["wins"]
                       and t["losses"] == c["losses"] and t["ties"] == c["ties"])
        same_vals = close(t["model_value"], c["mean_loss_model"], TOL) and close(t["rule_value"], c["mean_loss_rule"], TOL)
        same_verdict = verdict_norm(t["verdict"]) == verdict_norm(c["verdict"])
        exact = same_counts and same_vals and d_diff <= TOL and (d_ci is not None and d_ci <= TOL) and same_verdict
        small = (not exact) and same_counts and d_diff <= TOL_SMALL and (d_ci is not None and d_ci <= TOL_SMALL) and same_verdict
        grade = "BİREBİR" if exact else ("KÜÇÜK" if small else "ÖNEMLİ")
        n_exact += exact
        n_small += small
        n_big += (grade == "ÖNEMLİ")
        cell_cmp[f"{group}:{key}"] = {
            "found": True, "grade": grade, "label_theirs": t["label"],
            "n": [t["n"], c["n"]], "n_blocks": [t["n_blocks"], c["n_blocks"]],
            "wlt": [[t["wins"], t["losses"], t["ties"]], [c["wins"], c["losses"], c["ties"]]],
            "diff": [t["diff"], c["mean_diff"]], "abs_d_diff": d_diff,
            "ci95": [t["ci95"], c["ci95"]], "abs_d_ci": d_ci,
            "model_value": [t["model_value"], c["mean_loss_model"]], "rule_value": [t["rule_value"], c["mean_loss_rule"]],
            "verdict": [t["verdict"], c["verdict"]],
        }
        if grade != "BİREBİR":
            note("ÖNEMLİ" if grade == "ÖNEMLİ" else "KÜÇÜK", "kod", f"hücre farkı {key}: |Δfark|={d_diff:.3g}, |Δaralık|={d_ci}")
out["cells"] = cell_cmp
out["cells_summary"] = {"n": n_cells, "birebir": n_exact, "kucuk": n_small, "onemli": n_big}
out["max_abs_d_diff"] = max((v["abs_d_diff"] for v in cell_cmp.values() if v.get("found")), default=None)
out["max_abs_d_ci"] = max((v["abs_d_ci"] for v in cell_cmp.values() if v.get("found") and v["abs_d_ci"] is not None), default=None)

# yıl kırılımı (birincil hücreler; bilgi)
by_year_cmp = {}
for group in ("old_primary", "v1", "c"):
    for key, c in mine["cells_summary"][group].items():
        model = key.split("|")[0]
        if group == "v1" and not key.endswith("|RPS|vs|base_km_expanding"):
            continue
        if group == "c" and not (key.endswith("|vs|base_rate") and "Brier_D10" in key and model.startswith("fall")):
            continue
        by = sealed[model]["by_year"]
        keyname = next((k for k in ("year", "subset", "key", "value") if k in by[0]), None)
        cmp = {}
        for b in by:
            y = str(b.get(keyname))
            m = c["by_year"].get(y)
            cmp[y] = {"n": [b["n"], m["n"] if m else None], "diff": [b["diff"], m["mean_diff"] if m else None],
                      "equal": bool(m and b["n"] == m["n"] and (b["diff"] is None or close(b["diff"], m["mean_diff"], TOL)))}
        by_year_cmp[key] = cmp
out["by_year_primary"] = by_year_cmp
out["by_year_all_equal"] = all(v["equal"] for cmp in by_year_cmp.values() for v in cmp.values())
out["by_year_keyname_seen"] = sorted({k for b in sealed["v1_5_h99"]["by_year"] for k in b.keys()})

# ---------------------------------------------------------------- oot_pre_h99_all
old19 = mine["definitions"] and [m for m in mine["class_by_model"] if m not in mine["status_by_model"] or True]
OLD = list(sealed.keys())[:19]
all_ids = list(allb.keys())
out["all_block"] = {"model_ids_equal_old19": all_ids == OLD, "n_models": len(all_ids),
                    "excluded": sorted((e["model_id"], e["n_open_oot_blind"], e["n_open_oot_retro"]) for e in theirs["oot_pre_h99_all"]["excluded_models"]),
                    "n_in_table": theirs["oot_pre_h99_all"]["n_in_table"], "n_checks": {}}
ok_all = all_ids == OLD and theirs["oot_pre_h99_all"]["n_in_table"] == 135
for mid in OLD:
    a, o, s = allb[mid], opened[mid], sealed[mid]
    counters_ok = all(a[k] == o[k] + s[k] for k in ("n_scored", "n_refused", "n_not_applicable_regime", "n_oot_retro"))
    rows_ok = len(a["rows"]) == len(o["rows"]) + len(s["rows"])
    cells_ok = True
    for ca in a["cells"]:
        co = find_cell(o["cells"], ca["metric"], ca["horizon_or_k"], ca["output"], ca["rule_id"])
        cs = find_cell(s["cells"], ca["metric"], ca["horizon_or_k"], ca["output"], ca["rule_id"])
        if co is None or cs is None or ca["n"] != co["n"] + cs["n"]:
            cells_ok = False
    out["all_block"]["n_checks"][mid] = {"counters": counters_ok, "rows": rows_ok, "cells_n": cells_ok, "n_cells": len(a["cells"])}
    ok_all = ok_all and counters_ok and rows_ok and cells_ok
out["all_block"]["ok"] = ok_all
if not ok_all:
    note("ÖNEMLİ", "kod", "oot_pre_h99_all: model listesi ya da n = açık + kasa kuralı tutmuyor")
pd_all_ok = (pd_all["n_rows"] == pd_open["n_rows"] + pd_sealed["n_rows"] and pd_all["n_scored"] == pd_open["n_scored"] + pd_sealed["n_scored"]
             and pd_all["n_not_applicable"] == pd_open["n_not_applicable"] + pd_sealed["n_not_applicable"]
             and theirs["post_d1_all"]["excluded_models"] == [])
out["post_d1_all_ok"] = pd_all_ok
if not pd_all_ok:
    note("ÖNEMLİ", "kod", "post_d1_all = açık + kasa kuralı tutmuyor")

# ---------------------------------------------------------------- hüküm dili (dosya ve belge)
verdicts = Counter(c["verdict"] for m in sealed.values() for c in m["cells"])
out["verdict_vocab_sealed_json"] = dict(verdicts)
doc = (ROOT / "docs" / "SCORES_OOT.md").read_text(encoding="utf-8")
sec8 = doc[doc.index("## 8. "):doc.index("## 9. ")]
out["doc_sec8_verdict_counts"] = {
    "geçiyor (zaman-dışı terazide)": sec8.count("geçiyor (zaman-dışı terazide)"),
    "geçiyor_bare": sec8.count("| geçiyor |"),
    "geçemiyor_bare": sec8.count("| geçemiyor |"),
    "geçemiyor (zaman-dışı terazide)": sec8.count("geçemiyor (zaman-dışı terazide)"),
    "ayırt edilemiyor": sec8.count("ayırt edilemiyor"),
    "yetersiz örnek": sec8.count("yetersiz örnek"),
}
bad_vocab = set(verdicts) - {"geçiyor", "geçemiyor", "ayırt edilemiyor", "yetersiz örnek", "aralık için yetersiz", None}
if bad_vocab:
    note("ÖNEMLİ", "bilgi", f"beklenmedik hüküm sözcüğü: {sorted(map(str, bad_vocab))}")
# "geçiyor" yalnız n ≥ 30 ve üst uç < 0
viol = [(mid, c["rule_id"], c["metric"]) for mid, m in sealed.items() for c in m["cells"]
        if c["verdict"] == "geçiyor" and not (c["n"] >= 30 and c["ci95"] and c["ci95"][1] < 0)]
viol += [(mid, c["rule_id"], c["metric"]) for mid, m in sealed.items() for c in m["cells"]
         if c["verdict"] == "geçemiyor" and not (c["n"] >= 30 and c["ci95"] and c["ci95"][0] > 0)]
out["verdict_rule_violations"] = viol
if viol:
    note("KRİTİK", "kod", f"hüküm kuralı ihlali: {viol}")

# ---------------------------------------------------------------- seçim kuralları (kendi sonucum ile rapor)
out["selection_mine"] = {"v1": mine["selection_rules"]["v1"]["result"], "c": mine["selection_rules"]["c"]["result"],
                         "v1_k": {m: [d["k1"], d["k2"], d["k3"]] for m, d in mine["selection_rules"]["v1"]["candidates"].items()},
                         "c_k": {m: [d["k1"], d["k2"], d["k3"]] for m, d in mine["selection_rules"]["c"]["candidates"].items()}}

(HERE / "karsilastir_cikti.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
print("scores head", out["head_in_scores"], "| borsai import:", "borsai" in sys.modules)
print("row keys:", row_keys)
print("class equal:", out["class_total_equal"], "| status equal:", out["status_total_equal"], "| post_d1 equal:", pd_ok)
print("cells:", out["cells_summary"], "| max|Δdiff|", out["max_abs_d_diff"], "| max|Δci|", out["max_abs_d_ci"])
for k, v in cell_cmp.items():
    if not v.get("found") or v["grade"] != "BİREBİR":
        print("  NOT EXACT:", k, v)
print("by_year keys:", out["by_year_keyname_seen"], "| by_year all equal:", out["by_year_all_equal"])
print("all block:", {k: v for k, v in out["all_block"].items() if k != "n_checks"}, "| post_d1_all ok:", pd_all_ok)
print("verdict vocab:", out["verdict_vocab_sealed_json"], "| doc §8:", out["doc_sec8_verdict_counts"], "| violations:", viol)
print("findings:", findings)

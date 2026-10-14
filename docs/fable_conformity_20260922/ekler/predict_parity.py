"""Soru 4: dondurulmuş JSON -> stdlib predict çıktısı, fit tarafı (borsai numpy/sklearn nihai model)
ve bağımsız numpy hesabıyla karşılaştırma; ret kuralları. borsai.predict_* burada bilerek import edilir
(denetlenen şey odur); 'fit tarafı' borsai.fit.fit_with_estimators; 'bağımsız' = independent_repro.py'nin
Prep/hazards mantığı (JSON'daki μ/σ/p05/p95/γ/β kullanılarak elle hesap)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ahmet/Desktop/BorsAi")
from borsai import predict as pr  # noqa: E402
from borsai import predict_hazard as ph  # noqa: E402
from borsai import predict_market20 as pm  # noqa: E402
from borsai import predict_pb as ppb  # noqa: E402
from borsai.data import load_dataset, load_pb  # noqa: E402
from borsai.fit import fit_with_estimators, model_raw_features, select_training_rows  # noqa: E402
from borsai.specs import MODEL_SPECS  # noqa: E402

ROOT = Path("/Users/ahmet/Desktop/BorsAi")
J = lambda m: json.load(open(ROOT / "models" / f"{m}.json", encoding="utf-8"))  # noqa: E731
ds = load_dataset()
pb = load_pb(ds)
by = ds.by_ticker()
GROUP = {1: 0, 2: 1, 3: 1, **{d: 2 for d in range(4, 11)}}
OUT = {}


def manual_hazard(js, values):
    """JSON parametreleriyle elle: z = (x - μ)/σ (f1 ln, f3 kırpma), h_d = σ(γ_g + β·z), S_k çarpım, P_close."""
    prep = js["preprocessing"]
    z = {}
    for c in prep["columns"]:
        x = values[c]
        if c in prep["winsor"]:
            x = min(max(x, prep["winsor"][c]["p05"]), prep["winsor"][c]["p95"])
        if c in prep["log_transform"]:
            x = math.log(x)
        z[c] = (x - prep["mean"][c]) / prep["std"][c]
    lin = sum(js["beta"][c] * z[c] for c in z)
    h = [1 / (1 + math.exp(-(js["gamma"][GROUP[d]] + lin))) for d in range(1, 11)]
    S, s = [], 1.0
    for x in h:
        s *= 1 - x
        S.append(s)
    ra, rb = js["reclose_rates"]["r_a"], js["reclose_rates"]["r_b"]
    Pc = [S[0]] + [S[k - 1] + (1 - S[k - 1]) * (ra if k <= 4 else rb) for k in range(2, 11)]
    return h, S, Pc


def manual_linear(js, values, h):
    prep = js["preprocessing"]
    z = []
    f3_missing = values.get("f3") is None
    for c in prep["columns"]:
        if c == "f5":
            x = 1.0 if f3_missing else 0.0
        else:
            x = values[c]
            if c in prep["winsor"]:
                x = min(max(x, prep["winsor"][c]["p05"]), prep["winsor"][c]["p95"])
            if c in prep["log_transform"]:
                x = math.log(x)
        z.append((x - prep["mean"][c]) / prep["std"][c])
    r = js["horizons"][h]["return"]
    p = js["horizons"][h]["p_up"]
    ret = r["value"] if r["kind"] == "constant" else sum(c * v for c, v in zip(r["coef"], z)) + r["intercept"]
    pu = p["value"] if p["kind"] == "constant" else 1 / (1 + math.exp(-(sum(c * v for c, v in zip(p["coef"], z)) + p["intercept"])))
    return ret, pu


# ---------------------------------------------------------------- tavan modelleri
for mid in ("ceiling_hazard_v0", "pb_ceiling_v0"):
    js = J(mid)
    spec = MODEL_SPECS[mid]
    params, fits = fit_with_estimators(spec, list(ds.rows), dataset_version=ds.data_version_sha256)
    res = fits["hazard"]
    rows = select_training_rows(spec, ds.rows)
    raw = model_raw_features(spec, rows)[0]
    res_out = {"n_compared": 0, "max_abs_diff_fit_vs_stdlib": 0.0, "max_abs_diff_manual_vs_stdlib": 0.0, "cases": {}}
    for r in rows:  # tüm eğitim arzları
        inputs = pb[r.ticker].fields if mid == "pb_ceiling_v0" else r.feature_inputs()
        out = ph.predict(js, inputs)
        mine = res.predict(raw[r.ticker], r.total_demand_filter_status)
        assert out["refused"] is None
        d = max(max(abs(a - b) for a, b in zip(mine["S"], out["S"])), max(abs(a - b) for a, b in zip(mine["P_close"], out["P_close_ceiling"])),
                max(abs(a - b) for a, b in zip(mine["hazards"], out["hazard"])))
        vals = {k: float(v) for k, v in raw[r.ticker].items()}
        h_, S_, Pc_ = manual_hazard(js, vals)
        d2 = max(max(abs(a - b) for a, b in zip(S_, out["S"])), max(abs(a - b) for a, b in zip(Pc_, out["P_close_ceiling"])))
        res_out["n_compared"] += 1
        res_out["max_abs_diff_fit_vs_stdlib"] = max(res_out["max_abs_diff_fit_vs_stdlib"], d)
        res_out["max_abs_diff_manual_vs_stdlib"] = max(res_out["max_abs_diff_manual_vs_stdlib"], d2)
    # uç durumlar
    if mid == "ceiling_hazard_v0":
        base = by["QUICK"].feature_inputs()
        cases = {
            "f3_None": ({**base, "total_demand_multiple": None}, "refuse"),
            "f3_empty": ({**base, "total_demand_multiple": ""}, "refuse"),
            "f3_0.5_clip_low": ({**base, "total_demand_multiple": "0.5"}, "clip"),
            "f3_50_clip_high": ({**base, "total_demand_multiple": "50"}, "clip"),
            "f3_exact_p95_8.332": ({**base, "total_demand_multiple": "8.332"}, "ok"),
            "f1_out_of_range_price_5000": ({**base, "ipo_price_tl": "5000", "ipo_size_tl": None}, "warn"),
            "post_capital_zero": ({**base, "post_ipo_share_capital": "0"}, "refuse"),
            "shares_gt_post": ({**base, "shares_offered": "999999999999"}, "refuse"),
            "negative_price": ({**base, "ipo_price_tl": "-1"}, "refuse"),
            "f3_negative": ({**base, "total_demand_multiple": "-2"}, "refuse"),
            "f3_1e-9_tiny": ({**base, "total_demand_multiple": "1e-9"}, "clip"),
            "huge_f3_1e6": ({**base, "total_demand_multiple": "1000000"}, "clip"),
            "netgl_live_inputs": ({"ipo_price_tl": "25.52", "shares_offered": "87500000", "post_ipo_share_capital": "312500000",
                                   "capital_increase_shares": "62500000", "total_demand_multiple": "2.84"}, "ok"),
        }
        for name, (inp, kind) in cases.items():
            out = ph.predict(js, inp)
            entry = {"refused": out["refused"] and out["refused"]["code"] + ":" + str(out["refused"]["field"]),
                     "clipped": out["clipped"], "warnings": sorted({w["code"] for w in out["warnings"]})}
            if out["refused"] is None:
                # elle: aynı girdiden f1..f3 (fiyat*pay ya da ipo_size_tl) -> manuel S
                from borsai.features import compute_features
                f = compute_features(**{k: inp.get(k) for k in ("ipo_price_tl", "shares_offered", "post_ipo_share_capital",
                                                                   "capital_increase_shares", "total_demand_multiple", "ipo_size_tl")})
                vals = {"f1": float(f.f1), "f2": float(f.f2), "f3": float(f.f3)}
                h_, S_, Pc_ = manual_hazard(js, vals)
                entry["max_abs_diff_manual"] = max(abs(a - b) for a, b in zip(S_, out["S"]))
                entry["S1_S5_S10"] = [round(out["S"][0], 6), round(out["S"][4], 6), round(out["S"][9], 6)]
                entry["monotone"] = all(out["S"][k] >= out["S"][k + 1] for k in range(9)) and abs(sum(out["P_L"]) - 1) < 1e-12
                # kırpılan f3 fit tarafında da aynı sınıra iner mi: fit-tarafı transform ile
                mine = res.predict({"f1": f.f1, "f2": f.f2, "f3": f.f3}, None)
                entry["max_abs_diff_fit"] = max(abs(a - b) for a, b in zip(mine["S"], out["S"]))
                entry["fit_clipped"] = mine["clipped"]
            res_out["cases"][name] = entry
    else:
        base = dict(pb["QUICK"].fields)
        cases = {
            "no_f3_at_all": (base, "ok"),
            "f3_None_ignored": ({**base, "total_demand_multiple": None}, "ok"),
            "field_missing": ({**base, "planned_base_offer_shares": ""}, "refuse"),
            "price_range_10-12": ({**base, "ipo_price_try": "10-12"}, "refuse"),
            "price_range_endash": ({**base, "ipo_price_try": "10 – 12"}, "refuse"),
            "identity_B_broken": ({**base, "planned_existing_share_sale": "5"}, "refuse"),
            "cap_inc_zero_pb3_0": ({**base, "planned_capital_increase_shares": "0", "planned_existing_share_sale": base["planned_base_offer_shares"],
                                    "planned_post_ipo_capital": base["planned_pre_ipo_capital"]}, "refuse"),
            "price_5000_out_of_range": ({**base, "ipo_price_try": "5000"}, "warn"),
            "pb4_positive": (next(dict(r.fields) for r in pb.values() if r.fields["planned_additional_sale_ceiling"] not in ("0", "")), "warn"),
            "price_tiny_0.01": ({**base, "ipo_price_try": "0.01"}, "warn"),
        }
        from borsai.features import PBRefusal, compute_pb_features
        for name, (inp, kind) in cases.items():
            out = ph.predict(js, inp)
            entry = {"refused": out["refused"] and out["refused"]["code"] + ":" + str(out["refused"]["field"]),
                     "warnings": sorted({w["code"] for w in out["warnings"]})}
            if out["refused"] is None:
                f = compute_pb_features(inp)
                h_, S_, Pc_ = manual_hazard(js, {"pb1": f.pb1, "pb2": f.pb2})
                entry["max_abs_diff_manual"] = max(abs(a - b) for a, b in zip(S_, out["S"]))
                mine = res.predict({"pb1": f.pb1, "pb2": f.pb2}, None)
                entry["max_abs_diff_fit"] = max(abs(a - b) for a, b in zip(mine["S"], out["S"]))
                entry["S1_S5_S10"] = [round(out["S"][0], 6), round(out["S"][4], 6), round(out["S"][9], 6)]
            res_out["cases"][name] = entry
    OUT[mid] = res_out
    print(mid, json.dumps(res_out, default=str, ensure_ascii=False), flush=True)

# @INF ve KM: sabit eğri; girdi yok
for mid in ("ceiling_hazard_v0@INF", "pb_ceiling_v0@INF", "base_km_expanding", "base_km_last10"):
    js = J(mid)
    o1 = ph.predict(js)
    o2 = ph.predict(js, {"ipo_price_tl": "abc"})  # girdi okunmaz
    ok = o1["S"] == o2["S"] and o1["refused"] is None
    if mid.endswith("@INF"):
        h = [1 / (1 + math.exp(-js["gamma"][GROUP[d]])) for d in range(1, 11)]
    else:
        h = js["survival"]["hazard"]
    S, s = [], 1.0
    for x in h:
        s *= 1 - x
        S.append(s)
    OUT[mid] = {"constant_regardless_of_inputs": ok, "max_abs_diff_manual": max(abs(a - b) for a, b in zip(S, o1["S"])),
                "S1_S5_S10": [round(o1["S"][0], 6), round(o1["S"][4], 6), round(o1["S"][9], 6)]}
    print(mid, OUT[mid], flush=True)

# ---------------------------------------------------------------- doğrusal modeller
for mid in ("pb_v0", "v1_5_market20_v0", "v1_6_h99"):
    js = J(mid)
    spec = MODEL_SPECS[mid]
    params, fits = fit_with_estimators(spec, list(ds.rows), dataset_version=ds.data_version_sha256)
    raw = model_raw_features(spec, list(ds.rows))[0]
    res_out = {"n_compared": 0, "n_refused": 0, "max_abs_diff_fit_vs_stdlib": 0.0, "max_abs_diff_manual_vs_stdlib": 0.0, "cases": {}}
    for r in ds.rows:
        if mid == "pb_v0":
            inputs = pb[r.ticker].fields
            out = ppb.predict(js, inputs)
        elif mid == "v1_5_market20_v0":
            inputs = {**r.feature_inputs(), "total_demand_filter_status": r.total_demand_filter_status,
                      "f6_market20": js["market20_training"][r.ticker]["f6"]}
            out = pm.predict(js, inputs)
        else:
            inputs = {**r.feature_inputs(), "total_demand_filter_status": r.total_demand_filter_status}
            out = pr.predict(js, inputs)
        if out["refused"]:
            assert out["refused"]["code"] == "F3_MISSING" and r.inputs["total_demand_multiple"] is None
            res_out["n_refused"] += 1
            continue
        vals = {k: (None if v is None else float(v)) for k, v in raw[r.ticker].items()}
        for h in ("D1", "D3", "D5", "D10"):
            hf = fits[h]
            x = np.array([hf.final.matrix_rows([r.ticker])[0]])
            r_sk = hf.ridge.constant if hf.ridge.estimator is None else float(hf.ridge.estimator.predict(x)[0])
            p_sk = hf.logit.constant if hf.logit.estimator is None else float(hf.logit.estimator.predict_proba(x)[0][1])
            d = max(abs(out[h]["return_unclipped"] - r_sk), abs(out[h]["p_up"] - p_sk))
            mr, mp = manual_linear(js, vals, h)
            d2 = max(abs(out[h]["return_unclipped"] - mr), abs(out[h]["p_up"] - mp))
            res_out["max_abs_diff_fit_vs_stdlib"] = max(res_out["max_abs_diff_fit_vs_stdlib"], d)
            res_out["max_abs_diff_manual_vs_stdlib"] = max(res_out["max_abs_diff_manual_vs_stdlib"], d2)
        res_out["n_compared"] += 1
    # uç durumlar
    if mid == "pb_v0":
        base = dict(pb["QUICK"].fields)
        cases = {"field_missing": {**base, "planned_pre_ipo_capital": None}, "price_range": {**base, "ipo_price_try": "12-14"},
                 "identity_A": {**base, "planned_post_ipo_capital": "1"}, "pb3_zero": {**base, "planned_capital_increase_shares": "0",
                 "planned_existing_share_sale": base["planned_base_offer_shares"], "planned_post_ipo_capital": base["planned_pre_ipo_capital"]},
                 "price_5000": {**base, "ipo_price_try": "5000"}, "forbidden_f3_ignored": {**base, "total_demand_multiple": "99"}}
        for name, inp in cases.items():
            out = ppb.predict(js, inp)
            res_out["cases"][name] = {"refused": out["refused"] and out["refused"]["code"] + ":" + str(out["refused"]["field"]),
                                      "warnings": sorted({w["code"] for w in out["warnings"]}),
                                      "D5": None if out["D5"] is None else {k: (round(v, 6) if isinstance(v, float) else v) for k, v in out["D5"].items()}}
    elif mid == "v1_5_market20_v0":
        row = by["QUICK"]
        base = {**row.feature_inputs(), "total_demand_filter_status": row.total_demand_filter_status}
        f6q = js["market20_training"]["QUICK"]["f6"]
        cases = {"f6_None_no_reason": {**base, "f6_market20": None}, "f6_None_CALENDAR": {**base, "f6_market20": None, "f6_market20_refusal": "CALENDAR_NOT_COVERING"},
                 "f6_None_STALE": {**base, "f6_market20": None, "f6_market20_refusal": "STALE_S0"},
                 "f6_None_bogus_reason": {**base, "f6_market20": None, "f6_market20_refusal": "SOMETHING"},
                 "f6_not_numeric": {**base, "f6_market20": "abc"}, "f6_out_of_range_0.3": {**base, "f6_market20": "0.3"},
                 "f6_out_of_range_-0.5": {**base, "f6_market20": "-0.5"}, "f3_None_with_f6": {**base, "f6_market20": f6q, "total_demand_multiple": None},
                 "f3_filter_conflict": {**base, "f6_market20": f6q, "total_demand_filter_status": "FILTERED"},
                 "core_predict_without_f6": "CORE"}
        for name, inp in cases.items():
            out = pr.predict(js, base) if inp == "CORE" else pm.predict(js, inp)
            res_out["cases"][name] = {"refused": out["refused"] and out["refused"]["code"] + ":" + str(out["refused"]["field"]),
                                      "warnings": sorted({w["code"] for w in out["warnings"]}), "D5_return": None if out["D5"] is None else round(out["D5"]["return"], 6)}
    else:
        row = by["QUICK"]
        base = {**row.feature_inputs(), "total_demand_filter_status": row.total_demand_filter_status}
        cases = {"f3_None": {**base, "total_demand_multiple": None}, "f4_zero": {**base, "capital_increase_shares": "0"},
                 "price_5000": {**base, "ipo_price_tl": "5000", "ipo_size_tl": None}, "f3_50": {**base, "total_demand_multiple": "50"}}
        for name, inp in cases.items():
            out = pr.predict(js, inp)
            res_out["cases"][name] = {"refused": out["refused"] and out["refused"]["code"] + ":" + str(out["refused"]["field"]),
                                      "warnings": sorted({w["code"] for w in out["warnings"]}), "D10_return": None if out["D10"] is None else round(out["D10"]["return"], 6)}
    OUT[mid] = res_out
    print(mid, json.dumps(res_out, default=str, ensure_ascii=False), flush=True)

json.dump(OUT, open(Path(__file__).with_name("predict_parity_output.json"), "w"), indent=1, default=str, ensure_ascii=False)
print("DONE")

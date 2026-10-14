"""Bağımsız parite örneklemi (FAZ3_FABLE_APP_AUDIT adım 4).

gen_golden.py KULLANILMAZ ve import edilmez. Yalnız `borsai` stdlib predict yolu (freeze.run_model
dağıtımı) çağrılır. Girdiler seed 20260923 ile üretilir; altın dosyalardaki hiçbir (inputs, extra)
çiftiyle çakışmadıkları kontrol edilir (altın dosyalar yalnız dışlama için OKUNUR).

Çıktı: /tmp/borsai_app_audit/sample.jsonl — satır biçimi altın dosyalarla aynı
({case_id, model_id, params_sha256, inputs, extra, expected}); Rust tarafı `common::run_row` +
`cmp_expected` ile karşılaştırır.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()  # klon kökü (cwd de bu olmalı; borsai buradan yüklenir)
OUT = Path(sys.argv[2])
sys.path.insert(0, str(ROOT))

from borsai import freeze as fz  # noqa: E402

BANNED = {"numpy", "sklearn", "scipy", "pandas"}
INDEX = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
MODELS = []
for e in INDEX["models"]:
    raw = (ROOT / "models" / e["file"]).read_bytes()
    MODELS.append((e["model_id"], hashlib.sha256(raw).hexdigest(), json.loads(raw)))
assert len(MODELS) == 19, len(MODELS)

V15 = ["ipo_price_tl", "shares_offered", "post_ipo_share_capital", "capital_increase_shares",
       "existing_share_sale_shares", "total_demand_multiple", "total_demand_filter_status",
       "additional_sale_shares", "ipo_size_tl"]
PB = ["ipo_price_try", "planned_pre_ipo_capital", "planned_post_ipo_capital", "planned_capital_increase_shares",
      "planned_existing_share_sale", "planned_base_offer_shares", "planned_additional_sale_ceiling",
      "planned_max_offer_shares"]

rng = random.Random(20260923)


def dec(x: float, places: int) -> str:
    return f"{x:.{places}f}"


def valid_row() -> dict:
    price = round(rng.uniform(1, 500), rng.choice([0, 1, 2, 2, 3]))
    shares = int(rng.uniform(1e6, 5e8))
    capital = int(shares * rng.uniform(2, 12))
    ci = int(shares * rng.uniform(0, 1))
    ex = shares - ci
    add = 0 if rng.random() < 0.6 else int(shares * rng.uniform(0.01, 0.15))
    if add:
        shares_total = shares + add
    else:
        shares_total = shares
    f3 = None if rng.random() < 0.12 else round(math.exp(rng.uniform(math.log(0.3), math.log(60))), rng.choice([1, 2, 3]))
    size = None if rng.random() < 0.5 else str(int(price * shares_total * rng.uniform(0.9, 1.1)))
    base = ci + ex
    add_ceiling = 0 if rng.random() < 0.7 else int(base * rng.uniform(0.05, 0.2))
    price_try = str(price) if rng.random() < 0.9 else f"{price}-{round(price * 1.2, 2)}"
    row = {
        "ipo_price_tl": str(price),
        "shares_offered": str(shares_total),
        "post_ipo_share_capital": str(capital),
        "capital_increase_shares": str(ci),
        "existing_share_sale_shares": str(ex),
        "total_demand_multiple": None if f3 is None else str(f3),
        "total_demand_filter_status": rng.choice(["NOT_SPECIFIED", "UNFILTERED", "FILTERED", None]),
        "additional_sale_shares": str(add),
        "ipo_size_tl": size,
        "ipo_price_try": price_try,
        "planned_pre_ipo_capital": str(capital - ci),
        "planned_post_ipo_capital": str(capital),
        "planned_capital_increase_shares": str(ci),
        "planned_existing_share_sale": str(ex),
        "planned_base_offer_shares": str(base),
        "planned_additional_sale_ceiling": str(add_ceiling),
        "planned_max_offer_shares": str(base + add_ceiling),
    }
    return row


def f6_extra() -> dict:
    r = rng.random()
    if r < 0.15:
        return {"f6_market20": None, "f6_market20_refusal": None}
    if r < 0.25:
        return {"f6_market20": None, "f6_market20_refusal": rng.choice(["STALE_S0", "CALENDAR_NOT_COVERING", "PREDICTION_TOO_EARLY"])}
    if r < 0.30:
        return {"f6_market20": dec(rng.uniform(-0.9, 0.9), 6), "f6_market20_refusal": None}  # eğitim aralığı dışı olası
    return {"f6_market20": dec(rng.uniform(-0.2, 0.2), rng.choice([4, 8, 17])), "f6_market20_refusal": None}


cases: list[tuple[str, dict, dict]] = []
for i in range(70):
    cases.append((f"rand/{i:03d}", valid_row(), f6_extra()))

# Uç girdiler (her biri geçerli bir satırdan türetilir)
def edge(tag: str, **mut) -> None:
    row = valid_row()
    row.update(mut)
    cases.append((f"edge/{tag}", row, f6_extra()))

edge("f3_missing", total_demand_multiple=None, total_demand_filter_status=None)
edge("f3_missing_2", total_demand_multiple=None)
edge("pb_pre_missing", planned_pre_ipo_capital=None)
edge("pb_base_missing", planned_base_offer_shares=None)
edge("pb_price_range", ipo_price_try="10-12")
edge("pb_price_range_endash", ipo_price_try="10–12")
edge("pb_id_a_broken", planned_post_ipo_capital="1")
edge("pb_id_c_broken", planned_max_offer_shares="1")
edge("f3_out_of_range_high", total_demand_multiple="500")
edge("f3_out_of_range_low", total_demand_multiple="0.05")
edge("f3_winsor_high", total_demand_multiple="99.9")
edge("f3_winsor_low", total_demand_multiple="0.31")
edge("f1_huge_size", ipo_size_tl="1000000000000000")  # f1 → LOWER kırpma adayı
edge("f1_tiny", ipo_price_tl="0.01", shares_offered="1000000", ipo_size_tl=None)  # f1 küçük → UPPER adayı
edge("f1_1e400", ipo_size_tl="1e400")  # sonlu Decimal, binary64'e taşar
edge("price_zero", ipo_price_tl="0")
edge("price_negative", ipo_price_tl="-3")
edge("price_not_numeric", ipo_price_tl="abc")
edge("price_comma", ipo_price_tl="12,5")
edge("price_inf", ipo_price_tl="inf")
edge("price_nan", ipo_price_tl="nan")
edge("price_missing", ipo_price_tl=None)
edge("price_data_not_found", ipo_price_tl="DATA_NOT_FOUND")
edge("shares_zero", shares_offered="0", ipo_size_tl=None)
edge("capital_zero", post_ipo_share_capital="0")
edge("ci_negative", capital_increase_shares="-5")
edge("ci_gt_shares", capital_increase_shares="99999999999", ipo_size_tl=None)
edge("shares_gt_capital", shares_offered="999999999999", ipo_size_tl=None)
edge("f4_zero", capital_increase_shares="0")
edge("pb4_positive", planned_additional_sale_ceiling="12345678", planned_max_offer_shares=None)
edge("price_exponent", ipo_price_tl="2.552E1", ipo_price_try="2.552E1")
edge("price_tick_boundary_20", ipo_price_tl="20", ipo_price_try="20")
edge("price_tick_boundary_1999", ipo_price_tl="19.999", ipo_price_try="19.999")
edge("price_snap_halfup", ipo_price_tl="25.295", ipo_price_try="25.295")
edge("price_big", ipo_price_tl="2502.50", ipo_price_try="2502.50")
edge("price_long_frac", ipo_price_tl="25." + "5" * 70, ipo_price_try="25." + "5" * 70)  # Inexact
edge("price_1e_minus_400", ipo_price_tl="1e-400", ipo_price_try="1e-400")
edge("unicode_spaces", ipo_price_tl="  42.5  ")
edge("underscore_digits", shares_offered="1_000_000")
edge("filter_filtered", total_demand_multiple="3.3", total_demand_filter_status="FILTERED")
edge("filter_unfiltered", total_demand_multiple="3.3", total_demand_filter_status="UNFILTERED")
edge("f3_28_digits", total_demand_multiple="2.8400000000000000000000000001")
edge("size_many_digits", ipo_size_tl="1234567890123456789012345678901234567890")
edge("pb_all_missing", **{k: None for k in PB})
edge("v15_all_missing", **{k: None for k in V15})
edge("thirds", shares_offered="3", post_ipo_share_capital="9", capital_increase_shares="1", existing_share_sale_shares="2",
     additional_sale_shares="0", ipo_size_tl=None)

# f6 uçları (yalnız market20'yi etkiler; diğer 18 model bit-eşit kalmalı)
for j, f6 in enumerate([
    {"f6_market20": "abc", "f6_market20_refusal": None},
    {"f6_market20": "1e400", "f6_market20_refusal": None},
    {"f6_market20": "-inf", "f6_market20_refusal": None},
    {"f6_market20": "0", "f6_market20_refusal": None},
    {"f6_market20": None, "f6_market20_refusal": "XU100_INTEGRITY"},
    {"f6_market20": "0.05", "f6_market20_refusal": "STALE_S0"},  # ret öncelikli mi
]):
    cases.append((f"f6/{j}", valid_row(), f6))

assert len(cases) >= 50, len(cases)

# altın dosyalarla çakışma denetimi (yalnız okuma; gen_golden kullanılmaz)
golden_keys: set[str] = set()
gdir = ROOT / "app" / "parity" / "golden"
for p in gdir.glob("*.jsonl"):
    if p.name.startswith("_") or ".conditional." in p.name:
        continue
    for line in p.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        golden_keys.add(json.dumps([r.get("inputs"), r.get("extra")], sort_keys=True))
dups = [c for c, row, ex in cases if json.dumps([row, ex], sort_keys=True) in golden_keys]
assert not dups, dups


def jsonable(x):
    if isinstance(x, float):
        if math.isnan(x):
            return "NaN"
        if math.isinf(x):
            return "Infinity" if x > 0 else "-Infinity"
        return x
    if isinstance(x, dict):
        return {k: jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    return x


n_rows = 0
with OUT.open("w", encoding="utf-8") as fh:
    for mid, sha, params in MODELS:
        for case_id, row, extra in cases:
            inputs = {**row, **extra}
            try:
                res = fz.run_model(params, inputs)
                if res["status"] == fz.STATUS_ERROR:
                    expected = {"error": {"code": res["refusal"]["code"]}}
                else:
                    expected = {"output": jsonable(res["output"])}
            except Exception as exc:  # Python'un etiketsiz istisnaları (ValueError, decimal.Inexact/Overflow …)
                expected = {"exception": type(exc).__name__}
            fh.write(json.dumps({"case_id": f"{mid}/{case_id}", "model_id": mid, "params_sha256": sha,
                                 "inputs": row, "extra": extra, "expected": expected}, ensure_ascii=False, sort_keys=True) + "\n")
            n_rows += 1

loaded_banned = sorted(m for m in sys.modules if m.split(".")[0] in BANNED)
print(json.dumps({"cases": len(cases), "models": len(MODELS), "rows": n_rows, "banned_modules_loaded": loaded_banned,
                  "borsai_file": str(Path(fz.__file__).resolve())}))

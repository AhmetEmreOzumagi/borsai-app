"""KITAP_AUDIT_4 adım 1: bağımsız parite girdileri ve Python beklentileri.

Klon kökünde PYTHONPATH=<klon> ile koşar. Yalnız okur; /tmp/borsai_kitap_audit_4/harness/ altına yazar.
Üretici gen_golden.py'den bağımsızdır (kendi tohumu, kendi dağılımı); yalnız predict* modülleri ve
freeze.run_model dağıtımı kullanılır (kayıt yazılmaz).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)

from borsai import freeze as fz  # noqa: E402
from borsai import predict as pr  # noqa: E402
from borsai import predict_path as pth  # noqa: E402
from borsai import predict_post_d1 as pd1  # noqa: E402
from borsai import tufe as tf  # noqa: E402

SEED = 4_2026_10_11
rng = random.Random(SEED)

V15 = ("ipo_price_tl", "shares_offered", "post_ipo_share_capital", "capital_increase_shares",
       "existing_share_sale_shares", "total_demand_multiple", "total_demand_filter_status",
       "additional_sale_shares", "ipo_size_tl")
PB = ("ipo_price_try", "planned_pre_ipo_capital", "planned_post_ipo_capital", "planned_capital_increase_shares",
      "planned_existing_share_sale", "planned_base_offer_shares", "planned_additional_sale_ceiling",
      "planned_max_offer_shares")
F6_REASONS = ["STALE_S0", "CALENDAR_NOT_COVERING", "INSUFFICIENT_HISTORY", "XU100_CLOSE_MISSING",
              "PREDICTION_TOO_EARLY", "XU100_INTEGRITY"]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def encode(x: Any) -> Any:
    if isinstance(x, float):
        if math.isnan(x):
            return "NaN"
        if math.isinf(x):
            return "Infinity" if x > 0 else "-Infinity"
        return x
    if isinstance(x, dict):
        return {k: encode(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [encode(v) for v in x]
    return x


# ---------------------------------------------------------------- modeller
def load_models():
    idx = json.loads((ROOT / "models" / "INDEX.json").read_bytes())
    out = []
    for e in idx["models"]:
        raw = (ROOT / "models" / e["file"]).read_bytes()
        assert sha256_bytes(raw) == e["sha256"], e["model_id"]
        out.append((e["model_id"], json.loads(raw), e["sha256"]))
    return out


MODELS = load_models()
BY_ID = {m: (p, s) for m, p, s in MODELS}
POST_IDX = json.loads((ROOT / "models" / "INDEX_POST_D1.json").read_bytes())
POST_ENTRY = POST_IDX["models"][0]
POST_PARAMS = json.loads((ROOT / "models" / POST_ENTRY["file"]).read_bytes())
PARENT = BY_ID["ceiling_hazard_v0"][0]
PATH = BY_ID["ceiling_path_v0"][0]
TABLE = tf.load(ROOT / "data" / "raw" / "tuik" / "tufe_genel_2025_100.csv") if hasattr(tf, "load") else None

# H99 aralıkları (yalnız girdi sütunları)
rows = list(csv.DictReader((ROOT / "data" / "training_table.csv").open(encoding="utf-8")))


def rng_of(col: str) -> tuple[float, float]:
    vals = [float(r[col]) for r in rows if r[col] not in ("", "DATA_NOT_FOUND")]
    return min(vals), max(vals)


R_PRICE = rng_of("ipo_price_tl")
R_SHARES = rng_of("shares_offered")
R_F3 = rng_of("total_demand_multiple")
T_DATES = sorted(r["first_trading_date"] for r in rows)


def tufe_of(T: str | None) -> dict:
    """freeze.tufe_for_record ile aynı anahtarlar (pin denetimi dâhil)."""
    pins = fz.deflator_pins([(e, p, s) for (m, p, s) in MODELS for e in [{"model_id": m}]])
    try:
        blk = fz.tufe_for_record(T, pins)
    except fz.TufeMissing as exc:  # ay yok: Python kayıt yazmaz; uygulama TUFE_MISSING ile reddeder
        return {"tufe_index": None, "tufe_refusal": tf.TUFE_MISSING, "_tufe_missing_month": getattr(exc, "month", None)}
    except Exception as exc:  # Python etiketsiz istisna (ör. bozuk T): kayıt yolu burada düşer; model koşusu için TUFE_MISSING varsay
        return {"tufe_index": None, "tufe_refusal": tf.TUFE_MISSING, "_tufe_missing_month": None, "_py_exc": type(exc).__name__ + ": " + str(exc)}
    return {"tufe_index": blk["index"], "tufe_refusal": blk["refusal"]}


def logu(a: float, b: float) -> float:
    return 10 ** rng.uniform(math.log10(a), math.log10(b))


def dtxt(x: float, places: int) -> str:
    return f"{x:.{places}f}"


def random_input(i: int) -> tuple[dict, str | None]:
    price = logu(R_PRICE[0], R_PRICE[1])
    shares = int(logu(R_SHARES[0], R_SHARES[1]))
    post = int(shares * rng.uniform(1.5, 15))
    frac = rng.choice([0.0, 1.0, rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0.3, 1), 0.5])
    cap = int(round(shares * frac))
    existing = shares - cap
    addl = rng.choice([0, 0, 0, int(shares * rng.choice([0.05, 0.1, 0.15, 0.2]))])
    f3 = logu(R_F3[0], R_F3[1]) if rng.random() < 0.93 else None
    price_txt = dtxt(price, rng.choice([2, 2, 2, 1, 3]))
    inp: dict[str, Any] = {
        "ipo_price_tl": price_txt,
        "shares_offered": str(shares),
        "post_ipo_share_capital": str(post),
        "capital_increase_shares": str(cap),
        "existing_share_sale_shares": str(existing),
        "total_demand_multiple": None if f3 is None else dtxt(f3, rng.choice([1, 2, 2, 4])),
        "total_demand_filter_status": rng.choice(["NOT_SPECIFIED", "FILTERED", "UNFILTERED", None, "NOT_SPECIFIED"]),
        "additional_sale_shares": str(addl) if rng.random() < 0.9 else None,
        "ipo_size_tl": rng.choice([None, None, str(Decimal(price_txt) * shares), str(int(Decimal(price_txt) * shares))]),
    }
    base = shares if rng.random() < 0.6 else int(shares * rng.uniform(0.6, 1.0))
    cap_p = min(cap, base)
    existing_p = base - cap_p
    addl_p = rng.choice([0, 0, int(base * rng.choice([0.1, 0.15, 0.2, 0.25]))])
    post_p = max(post, base + 1)
    pre_p = post_p - cap_p
    inp.update({
        "ipo_price_try": price_txt if rng.random() < 0.75 else dtxt(price * rng.uniform(0.7, 1.3), 2),
        "planned_pre_ipo_capital": str(pre_p),
        "planned_post_ipo_capital": str(post_p),
        "planned_capital_increase_shares": str(cap_p),
        "planned_existing_share_sale": str(existing_p),
        "planned_base_offer_shares": str(base),
        "planned_additional_sale_ceiling": str(addl_p),
        "planned_max_offer_shares": str(base + addl_p),
    })
    r = rng.random()
    if r < 0.75:
        inp["f6_market20"], inp["f6_market20_refusal"] = repr(rng.uniform(-0.3, 0.3)), None
    elif r < 0.85:
        inp["f6_market20"], inp["f6_market20_refusal"] = rng.uniform(-0.3, 0.3), None
    else:
        inp["f6_market20"], inp["f6_market20_refusal"] = None, rng.choice(F6_REASONS + [None])
    # T: H99 dönemi, 2026 sonbaharı ya da yok
    rr = rng.random()
    if rr < 0.6:
        T = rng.choice(T_DATES)
    elif rr < 0.9:
        T = f"2026-{rng.choice(['09', '10']):s}-{rng.randint(1, 28):02d}"
    elif rr < 0.95:
        T = f"2026-11-{rng.randint(1, 28):02d}"  # ay 2026-09 tabloda yok
    else:
        T = None
    return inp, T


BASE_INPUT, BASE_T = random_input(-1)
BASE_INPUT.update({"ipo_price_tl": "25.52", "shares_offered": "87500000", "post_ipo_share_capital": "312500000",
                   "capital_increase_shares": "62500000", "existing_share_sale_shares": "25000000",
                   "total_demand_multiple": "3.17", "total_demand_filter_status": "NOT_SPECIFIED",
                   "additional_sale_shares": "0", "ipo_size_tl": None, "ipo_price_try": "25.52",
                   "planned_pre_ipo_capital": "250000000", "planned_post_ipo_capital": "312500000",
                   "planned_capital_increase_shares": "62500000", "planned_existing_share_sale": "25000000",
                   "planned_base_offer_shares": "87500000", "planned_additional_sale_ceiling": "0",
                   "planned_max_offer_shares": "87500000", "f6_market20": "0.0123", "f6_market20_refusal": None})
BASE_T = "2026-09-17"


def variant(mods: dict, T: Any = "<base>") -> tuple[dict, Any]:
    d = dict(BASE_INPUT)
    for k, v in mods.items():
        if v == "<DEL>":
            d.pop(k, None)
        else:
            d[k] = v
    return d, (BASE_T if T == "<base>" else T)


P05, P95 = "1.14870997716", "8.332"
EDGES: list[tuple[str, dict, Any]] = [
    ("f3:none", {"total_demand_multiple": None}, "<base>"),
    ("f3:empty", {"total_demand_multiple": ""}, "<base>"),
    ("f3:dnf", {"total_demand_multiple": "DATA_NOT_FOUND"}, "<base>"),
    ("f3:ws", {"total_demand_multiple": "   "}, "<base>"),
    ("f3:zero", {"total_demand_multiple": "0"}, "<base>"),
    ("f3:neg", {"total_demand_multiple": "-2"}, "<base>"),
    ("f3:p05", {"total_demand_multiple": P05}, "<base>"),
    ("f3:p05-", {"total_demand_multiple": "1.14870997715"}, "<base>"),
    ("f3:p95", {"total_demand_multiple": P95}, "<base>"),
    ("f3:p95+", {"total_demand_multiple": "8.3321"}, "<base>"),
    ("f3:huge", {"total_demand_multiple": "1e6"}, "<base>"),
    ("f3:tiny", {"total_demand_multiple": "1e-9"}, "<base>"),
    ("f3:comma", {"total_demand_multiple": "3,17"}, "<base>"),
    ("f3:unicode", {"total_demand_multiple": "３.１７"}, "<base>"),
    ("f3:underscore", {"total_demand_multiple": "3_17"}, "<base>"),
    ("f3:inf", {"total_demand_multiple": "inf"}, "<base>"),
    ("f3:nan", {"total_demand_multiple": "nan"}, "<base>"),
    ("f3:bool", {"total_demand_multiple": True}, "<base>"),
    ("f3:list", {"total_demand_multiple": [3]}, "<base>"),
    ("f3:filtered", {"total_demand_filter_status": "FILTERED"}, "<base>"),
    ("f3:unfiltered", {"total_demand_filter_status": "UNFILTERED"}, "<base>"),
    ("f3:weirdstatus", {"total_demand_filter_status": "WHATEVER"}, "<base>"),
    ("price:zero", {"ipo_price_tl": "0"}, "<base>"),
    ("price:neg", {"ipo_price_tl": "-25.52"}, "<base>"),
    ("price:none", {"ipo_price_tl": None}, "<base>"),
    ("price:empty", {"ipo_price_tl": ""}, "<base>"),
    ("price:comma", {"ipo_price_tl": "25,52"}, "<base>"),
    ("price:ws", {"ipo_price_tl": " 25.52 "}, "<base>"),
    ("price:plus", {"ipo_price_tl": "+25.52"}, "<base>"),
    ("price:exp", {"ipo_price_tl": "2552e-2"}, "<base>"),
    ("price:1e400", {"ipo_price_tl": "1e400"}, "<base>"),
    ("price:1e30", {"ipo_price_tl": "1e30"}, "<base>"),
    ("price:1e-30", {"ipo_price_tl": "1e-30"}, "<base>"),
    ("price:1e-400", {"ipo_price_tl": "1e-400"}, "<base>"),
    ("price:bool", {"ipo_price_tl": False}, "<base>"),
    ("price:num", {"ipo_price_tl": 25.52}, "<base>"),
    ("price:int", {"ipo_price_tl": 25}, "<base>"),
    ("price:offgrid", {"ipo_price_tl": "25.513", "ipo_price_try": "25.513"}, "<base>"),
    ("price:long", {"ipo_price_tl": "25.5200000000000000000000000001"}, "<base>"),
    ("shares:zero", {"shares_offered": "0"}, "<base>"),
    ("shares:gtpost", {"shares_offered": "400000000"}, "<base>"),
    ("shares:eqpost", {"shares_offered": "312500000", "capital_increase_shares": "312500000", "existing_share_sale_shares": "0"}, "<base>"),
    ("shares:frac", {"shares_offered": "87500000.5"}, "<base>"),
    ("post:zero", {"post_ipo_share_capital": "0"}, "<base>"),
    ("post:none", {"post_ipo_share_capital": None}, "<base>"),
    ("cap:zero", {"capital_increase_shares": "0", "existing_share_sale_shares": "87500000"}, "<base>"),
    ("cap:all", {"capital_increase_shares": "87500000", "existing_share_sale_shares": "0"}, "<base>"),
    ("cap:gt", {"capital_increase_shares": "90000000"}, "<base>"),
    ("cap:neg", {"capital_increase_shares": "-1"}, "<base>"),
    ("cap:none", {"capital_increase_shares": None}, "<base>"),
    ("size:given", {"ipo_size_tl": "2233000000"}, "<base>"),
    ("size:zero", {"ipo_size_tl": "0"}, "<base>"),
    ("size:neg", {"ipo_size_tl": "-5"}, "<base>"),
    ("size:huge", {"ipo_size_tl": "1e300"}, "<base>"),
    ("addl:none", {"additional_sale_shares": None}, "<base>"),
    ("addl:empty", {"additional_sale_shares": ""}, "<base>"),
    ("addl:pos", {"additional_sale_shares": "8750000"}, "<base>"),
    ("addl:neg", {"additional_sale_shares": "-1"}, "<base>"),
    ("addl:text", {"additional_sale_shares": "x"}, "<base>"),
    ("addl:negzero", {"additional_sale_shares": "-0"}, "<base>"),
    ("addl:ws", {"additional_sale_shares": " "}, "<base>"),
    ("f6:none", {"f6_market20": None, "f6_market20_refusal": None}, "<base>"),
    ("f6:text", {"f6_market20": "abc"}, "<base>"),
    ("f6:num", {"f6_market20": -0.0924}, "<base>"),
    ("f6:big", {"f6_market20": "5"}, "<base>"),
    ("f6:1e400", {"f6_market20": "1e400"}, "<base>"),
    ("f6:valwithrefusal", {"f6_market20": "0.01", "f6_market20_refusal": "STALE_S0"}, "<base>"),
    ("f6:unknownreason", {"f6_market20": None, "f6_market20_refusal": "SOMETHING_ELSE"}, "<base>"),
    ("f6:nokeys", {"f6_market20": "<DEL>", "f6_market20_refusal": "<DEL>"}, "<base>"),
    ("tufe:none", {}, None),
    ("tufe:empty", {}, ""),
    ("tufe:missing", {}, "2026-11-02"),
    ("tufe:missing_old", {}, "2019-12-15"),
    ("tufe:first", {}, "2020-01-06"),
    ("tufe:malformed", {}, "2026-13-01"),
    ("tufe:malformed2", {}, "17.09.2026"),
    ("tufe:idx:text", {"tufe_index": "abc", "tufe_refusal": None}, "<direct>"),
    ("tufe:idx:zero", {"tufe_index": "0", "tufe_refusal": None}, "<direct>"),
    ("tufe:idx:neg", {"tufe_index": "-1", "tufe_refusal": None}, "<direct>"),
    ("tufe:idx:none", {"tufe_index": None, "tufe_refusal": None}, "<direct>"),
    ("tufe:idx:empty", {"tufe_index": "", "tufe_refusal": None}, "<direct>"),
    ("tufe:idx:num", {"tufe_index": 132.31, "tufe_refusal": None}, "<direct>"),
    ("tufe:idx:tiny", {"tufe_index": "1e-30", "tufe_refusal": None}, "<direct>"),
    ("tufe:idx:huge", {"tufe_index": "1e300", "tufe_refusal": None}, "<direct>"),
    ("tufe:refusal:notpit", {"tufe_index": None, "tufe_refusal": "TUFE_NOT_PIT"}, "<direct>"),
    ("tufe:refusal:mismatch", {"tufe_index": None, "tufe_refusal": "TUFE_FILE_MISMATCH"}, "<direct>"),
    ("tufe:refusal:both", {"tufe_index": "132.31", "tufe_refusal": "TUFE_NOT_PIT"}, "<direct>"),
    ("tufe:nokeys", {"tufe_index": "<DEL>", "tufe_refusal": "<DEL>"}, "<direct>"),
    ("regime:pre", {"alloc_regime": "PRE_20211111"}, "<base>"),
    ("regime:thresh", {"alloc_regime": "THRESH100_20211111"}, "<base>"),
    ("regime:equal", {"alloc_regime": "EQUAL_DIST_20230330"}, "<base>"),
    ("regime:unknown", {"alloc_regime": "FOO"}, "<base>"),
    ("regime:none", {"alloc_regime": None}, "<base>"),
    ("pb:range1", {"ipo_price_try": "10-12"}, "<base>"),
    ("pb:range2", {"ipo_price_try": "10–12"}, "<base>"),
    ("pb:range3", {"ipo_price_try": "10—12"}, "<base>"),
    ("pb:ida", {"planned_post_ipo_capital": "312500001"}, "<base>"),
    ("pb:idb", {"planned_base_offer_shares": "87500001", "planned_max_offer_shares": "87500001"}, "<base>"),
    ("pb:idc", {"planned_max_offer_shares": "87500001"}, "<base>"),
    ("pb:missing", {"planned_base_offer_shares": None}, "<base>"),
    ("pb:empty", {"planned_base_offer_shares": ""}, "<base>"),
    ("pb:addl", {"planned_additional_sale_ceiling": "8750000", "planned_max_offer_shares": "96250000"}, "<base>"),
    ("pb:longdigits", {"planned_base_offer_shares": "1" + "0" * 249 + "1", "planned_max_offer_shares": "1" + "0" * 249 + "1",
                       "planned_capital_increase_shares": "1" + "0" * 249 + "1", "planned_existing_share_sale": "0",
                       "planned_post_ipo_capital": "1" + "0" * 249 + "2", "planned_pre_ipo_capital": "1"}, "<base>"),
    ("pb:price0", {"ipo_price_try": "0"}, "<base>"),
    ("pb:pb2over", {"planned_post_ipo_capital": "87500000", "planned_pre_ipo_capital": "25000000"}, "<base>"),
    ("all:none", {k: None for k in V15 + PB}, "<base>"),
    ("all:empty", {k: "" for k in V15 + PB}, "<base>"),
    ("all:nokeys", {k: "<DEL>" for k in V15 + PB}, "<base>"),
]
TICKS = ["19.99", "20.00", "20", "49.98", "50.00", "99.95", "100.00", "100", "249.90", "250.00", "499.75", "500.00",
         "999.50", "1000.00", "2499.00", "2500.00", "2502.50", "0.01", "0.02", "1.00", "1.5", "135", "18.19", "18.20"]
for t in TICKS:
    EDGES.append((f"tick:{t}", {"ipo_price_tl": t, "ipo_price_try": t}, "<base>"))


# ---------------------------------------------------------------- D1 (post_d1) sentetik bloklar
def synth_d1(price: Decimal, shares: int, mode: str) -> dict:
    snapped = pth.snap(price)
    upper = pth.upper_limit(snapped)
    lower = pth.lower_limit(snapped)
    tk = pth.tick(upper)
    if mode in ("ceiling_locked", "ceiling_unlocked", "ceiling_openlow"):
        close = upper
        high = upper
        if mode == "ceiling_locked":
            low = upper
            open_ = upper
        elif mode == "ceiling_unlocked":
            low = max(upper - tk * rng.randint(1, 40), tk)
            open_ = max(upper - tk * rng.randint(0, 20), low)
        else:
            low = upper
            open_ = max(upper - tk * rng.randint(1, 10), tk)  # kilit tutarsız (low = U, open ≠ U)
    else:
        close = max(upper - tk * rng.randint(1, 50), tk)
        low = max(close - tk * rng.randint(0, 20), tk)
        open_ = min(max(close - tk * rng.randint(-5, 10), low), upper)
        high = min(max(close, open_) + tk * rng.randint(0, 10), upper)
    ratio = 10 ** rng.uniform(-5, math.log10(0.9))
    volume = max(1, int(shares * Decimal(repr(ratio))))
    f = {"open": str(open_), "high": str(high), "low": str(low), "close": str(close), "volume": str(volume),
         "turnover": str((volume * close).quantize(Decimal("0.01"))), "aof": str(close),
         "trade_count": str(rng.randint(1, 80000)), "halt": "0", "special_trade_volume": "0",
         "special_trade_turnover": "0", "reference_price": str(snapped), "upper_limit": str(upper), "lower_limit": str(lower)}
    return {"fields_raw": f, "half_day": 0, "halt_flag": 0}


def d1_edges(base: dict) -> list[tuple[str, dict]]:
    def mod(fields: dict | None = None, top: dict | None = None):
        d = json.loads(json.dumps(base))
        for k, v in (fields or {}).items():
            if v == "<DEL>":
                d["fields_raw"].pop(k, None)
            else:
                d["fields_raw"][k] = v
        for k, v in (top or {}).items():
            if v == "<DEL>":
                d.pop(k, None)
            else:
                d[k] = v
        return d
    U = base["fields_raw"]["upper_limit"]
    return [
        ("d1:half_day", mod(top={"half_day": 1})),
        ("d1:half_day_str", mod(top={"half_day": "1"})),
        ("d1:half_day_half", mod(top={"half_day": 0.5})),
        ("d1:halt", mod(top={"halt_flag": 1})),
        ("d1:halt_text", mod(top={"halt_flag": "x"})),
        ("d1:no_half_key", mod(top={"half_day": "<DEL>"})),
        ("d1:special", mod({"special_trade_volume": "1500"})),
        ("d1:special_neg", mod({"special_trade_volume": "-1"})),
        ("d1:trade0", mod({"trade_count": "0"})),
        ("d1:trade_none", mod({"trade_count": "<DEL>"})),
        ("d1:close_empty", mod({"close": ""})),
        ("d1:close_zero", mod({"close": "0"})),
        ("d1:upper_empty", mod({"upper_limit": ""})),
        ("d1:upper_none", mod({"upper_limit": "<DEL>"})),
        ("d1:not_ceiling", mod({"close": str(Decimal(U) - Decimal("0.02"))})),
        ("d1:vol0", mod({"volume": "0"})),
        ("d1:vol_text", mod({"volume": "abc"})),
        ("d1:vol_huge", mod({"volume": "1e30"})),
        ("d1:vol_tiny", mod({"volume": "1"})),
        ("d1:low_text", mod({"low": "abc"})),
        ("d1:open_empty", mod({"open": ""})),
        ("d1:high_empty", mod({"high": ""})),
        ("d1:low_gt", mod({"low": str(Decimal(U) + Decimal("1"))})),
        ("d1:lock_incons", mod({"low": U, "open": str(Decimal(U) - Decimal("0.5")), "high": U})),
        ("d1:no_fields", {"half_day": 0, "halt_flag": 0}),
        ("d1:empty_fields", mod(fields={k: "<DEL>" for k in base["fields_raw"]})),
    ]


# ---------------------------------------------------------------- koşu
def eval_run(params: dict, inputs: dict) -> dict:
    try:
        return fz.run_model(params, inputs)
    except Exception as exc:  # Python etiketsiz istisna → Rust DOMAIN_ERROR (ERROR)
        return {"kind": fz.model_kind(params), "status": "EXCEPTION", "refusal": {"code": type(exc).__name__, "field": None, "reason": str(exc)}, "output": None}


def eval_post(inputs: dict, d1: dict) -> tuple[dict, bool]:
    """freeze.run_post_d1_model'in model kısmı: path_params yalnız ceiling_path_v0 PREDICTED ise."""
    cell = fz.run_model(PATH, inputs)
    give_path = cell["status"] == fz.STATUS_PREDICTED
    try:
        out = pd1.predict_post_d1(POST_PARAMS, PARENT, inputs, d1, path_params=PATH if give_path else None)
    except pr.PredictError as exc:
        return {"kind": "post_d1", "status": "ERROR", "refusal": {"code": exc.code, "field": None, "reason": str(exc)}, "output": None}, give_path
    except Exception as exc:  # etiketsiz istisna → Rust DOMAIN_ERROR
        return {"kind": "post_d1", "status": "EXCEPTION", "refusal": {"code": type(exc).__name__, "field": None, "reason": str(exc)}, "output": None}, give_path
    status = "REFUSED" if out["refused"] else ("NOT_APPLICABLE" if out["not_applicable"] else "PREDICTED")
    return {"kind": "post_d1", "status": status, "refusal": out["refused"] or out["not_applicable"], "output": out}, give_path


cases: list[dict] = []
N_RANDOM = 240
for i in range(N_RANDOM):
    inp, T = random_input(i)
    cases.append({"case_id": f"rand:{i:03d}", "T": T, "inputs": inp, "tufe_source": "T"})
for tag, mods, T in EDGES:
    inp, TT = variant(mods, T)
    cases.append({"case_id": f"edge:{tag}", "T": (BASE_T if T == "<direct>" else TT), "inputs": inp,
                  "tufe_source": "DIRECT" if T == "<direct>" else "T"})

# TÜFE anahtarları (kayıt yolu gibi): tufe_source == "T" ise T'den; DIRECT ise girdideki gibi bırak
for c in cases:
    if c["tufe_source"] == "T":
        tfe = tufe_of(c["T"])
        c["tufe_missing_month"] = tfe.pop("_tufe_missing_month", None)
        c["tufe_py_exc"] = tfe.pop("_py_exc", None)
        c["inputs"].update(tfe)

# D1 blokları: ilk 120 rastgele vaka + edge'ler tabanda
post_cases: list[dict] = []
modes = ["ceiling_locked", "ceiling_unlocked", "ceiling_openlow", "not_ceiling"]
for c in cases[:120]:
    inp = c["inputs"]
    try:
        price = Decimal(str(inp["ipo_price_tl"]).strip())
        shares = int(Decimal(str(inp["shares_offered"]).strip()))
        if price <= 0 or shares <= 0:
            continue
    except Exception:
        continue
    d1 = synth_d1(price, shares, rng.choice(modes))
    if rng.random() < 0.15:
        d1["half_day"] = 1
    if rng.random() < 0.08:
        d1["halt_flag"] = 1
    post_cases.append({"case_id": "post:" + c["case_id"], "inputs": inp, "d1": d1})
base_d1 = synth_d1(Decimal("25.52"), 87500000, "ceiling_locked")
base_d1["fields_raw"].update({"volume": "8750000", "trade_count": "1200"})
for tag, d1 in d1_edges(base_d1):
    post_cases.append({"case_id": "post:" + tag, "inputs": dict(cases[N_RANDOM]["inputs"] | {"total_demand_multiple": "3.17"}), "d1": d1})
# f3 eksik + D1 (ana model reddeder)
post_cases.append({"case_id": "post:f3none", "inputs": variant({"total_demand_multiple": None})[0] | tufe_of(BASE_T), "d1": base_d1})
post_cases.append({"case_id": "post:shares_none", "inputs": variant({"shares_offered": None})[0] | tufe_of(BASE_T), "d1": base_d1})

# Python beklentileri
with (OUT / "cases.jsonl").open("w", encoding="utf-8") as fc, (OUT / "py_out.jsonl").open("w", encoding="utf-8") as fo:
    for c in cases:
        full = c["inputs"]
        runs = {m: eval_run(p, full) for m, p, s in MODELS}
        fc.write(json.dumps({"case_id": c["case_id"], "T": c["T"], "inputs": full, "tufe_source": c["tufe_source"]},
                            ensure_ascii=False) + "\n")
        fo.write(json.dumps(encode({"case_id": c["case_id"], "runs": runs}), ensure_ascii=False, allow_nan=False) + "\n")
with (OUT / "post_cases.jsonl").open("w", encoding="utf-8") as fc, (OUT / "py_post_out.jsonl").open("w", encoding="utf-8") as fo:
    for c in post_cases:
        res, give_path = eval_post(c["inputs"], c["d1"])
        fc.write(json.dumps({"case_id": c["case_id"], "inputs": c["inputs"], "d1": c["d1"], "give_path": give_path},
                            ensure_ascii=False) + "\n")
        fo.write(json.dumps(encode({"case_id": c["case_id"], "post": res}), ensure_ascii=False, allow_nan=False) + "\n")

# TÜFE beklentileri (uygulama tarafı tufe_for_inputs ile karşılaştırılacak): T → (index, refusal, month)
with (OUT / "tufe_expect.jsonl").open("w", encoding="utf-8") as fo:
    seen = set()
    for c in cases:
        if c["tufe_source"] != "T" or c["T"] in seen:
            continue
        seen.add(c["T"])
        fo.write(json.dumps({"T": c["T"], "tufe_index": c["inputs"].get("tufe_index"), "tufe_refusal": c["inputs"].get("tufe_refusal"),
                             "missing_month": c.get("tufe_missing_month"), "py_exc": c.get("tufe_py_exc")}) + "\n")
print(f"cases={len(cases)} post_cases={len(post_cases)} models={len(MODELS)}")

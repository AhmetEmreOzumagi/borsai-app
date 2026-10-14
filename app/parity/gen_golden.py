#!/usr/bin/env python3
"""Altın vektör üreticisi: Python predict -> app/parity/golden/*.jsonl (SPEC_APP §1.3; U1–U4, U37).

Repo `.venv`'iyle, repo kökünden koşar; `borsai` paketini import eder, hiçbir şey yazmaz (yalnız
app/parity/ altına). Yalnız stdlib predict yolu import edilir (numpy/scikit-learn yüklenmez; U1).

  .venv/bin/python app/parity/gen_golden.py              # golden/*.jsonl, golden/MANIFEST.json, dec_cases.json
  .venv/bin/python app/parity/gen_golden.py --check      # üret ve diskteki dosyalarla bayt bayt karşılaştır
  .venv/bin/python app/parity/gen_golden.py --dec-cases  # yalnız dec_cases.json (U4)

Model kümesi: models/INDEX.json'un 27 kaydı, aşağıda açıkça sabit. 17.–19. kayıtlar Faz 4
tavan-yolu modelleridir (SPEC_APP EK 2 §3.1, Aşama P1); koşullu karışım vektörleri ayrı dosyalarda
(`golden/<model_id>.conditional.jsonl`). 20.–23. kayıtlar Faz 7 `ceiling_hazard_v1` ailesidir (SPEC_APP EK 3
§4, Aşama P1); son dört kayıt Faz 7C düşen arz ailesi `fall_d10_v0` (EK 3 §8.3, Aşama P4). Eski altın dosyalar BAYT-EŞİT
kalır (U46, U55, U80): yeni girdi satırları yalnız yeni modellere `only` ile bağlanır, yeni yamalı satırlar dosyanın sonuna
eklenir.

D1 sonrası güncelleme (SPEC_APP EK 3 §6.4, Aşama P2): ikinci dizin models/INDEX_POST_D1.json'un tek modeli
`post_d1_hazard_v0` ayrı dosyada (`golden/post_d1_hazard_v0.jsonl`; `PINNED_POST_D1_MODEL_IDS`). D1 blokları SENTETİKTİR
(`synth_d1`, ayrı `random.Random(SEED)` akışı: eski satırların rastgele dizisi değişmez); sonuç dosyası okunmaz. Yamalı
satırları `_patched_params.jsonl`'ın sonuna eklenir (ilk 43 satır bayt-eşit).

Okunan veri: models/ (INDEX + 27 JSON), data/training_table.csv'den yalnız girdi sütunları ve ilk işlem
günü, data/raw/ H99 master'dan yalnız ipo_size_tl, PB kanıt CSV'sinden yalnız 8 PB alanı,
registry/inputs/*.json (7 girdi belgesi), registry/records/<T>/*.json'dan yalnız
model_inputs.f6_market20[_refusal], TÜFE tablosu (data/raw/tuik/) ve eski kohortun YALNIZ açık küme
üyelerinin girdi belgeleri (registry/oot/inputs/; kasa (SEALED) satırı bekçiyle dışlanır, kod basılmaz).
Sonuç dosyaları (data/outcomes*/) OKUNMAZ.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import random
import sys
from decimal import ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal, Inexact, localcontext
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from borsai import features as ft  # noqa: E402
from borsai import predict as pr  # noqa: E402
from borsai import predict_fall as pf  # noqa: E402
from borsai import predict_hazard as ph  # noqa: E402
from borsai import predict_market20 as pm  # noqa: E402
from borsai import predict_path as pth  # noqa: E402
from borsai import predict_pb as ppb  # noqa: E402
from borsai import predict_post_d1 as pd1  # noqa: E402
from borsai import registry as reg  # noqa: E402
from borsai import survival as sv  # noqa: E402
from borsai import tufe as tf  # noqa: E402
from borsai.specs import TUFE_PIN  # noqa: E402

SEED = 20260922
N_RANDOM = 80
GOLDEN_DIR = HERE / "golden"
DEC_CASES_PATH = HERE / "dec_cases.json"
TUFE_CASES_PATH = HERE / "tufe_cases.json"
SCHEMA = "borsai.app_golden/1"

PINNED_MODEL_IDS: tuple[str, ...] = (
    "v1_5_h99",
    "base_always_ceiling",
    "base_train_median",
    "base_train_mean",
    "base_zero",
    "base_rate",
    "base_last10_rate",
    "v1_6_h99",
    "v1_5_market20_v0",
    "pb_v0",
    "ceiling_hazard_v0",
    "ceiling_hazard_v0@INF",
    "pb_ceiling_v0",
    "pb_ceiling_v0@INF",
    "base_km_expanding",
    "base_km_last10",
    "ceiling_path_v0",
    "ceiling_path_v0@INF",
    "pb_ceiling_path_v0",
    "ceiling_hazard_v1_clip",
    "ceiling_hazard_v1_real",
    "ceiling_hazard_v1_pooled",
    "ceiling_hazard_v1_pooled@INF",
    "fall_d10_v0_h99",
    "fall_d10_v0_pooled",
    "fall_d10_v0_addsale",
    "fall_d10_v0_pooled@ZERO",
)

# Faz 7 ailesi (EK 3 §4.2): yeni girdi satırları yalnız bu dört modele bağlanır (eski 19 dosya bayt-eşit).
V1_IDS: tuple[str, ...] = ("ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled",
                           "ceiling_hazard_v1_pooled@INF")
DEFLATOR_IDS: tuple[str, ...] = ("ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled")
REGIME_IDS: tuple[str, ...] = ("ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF")
# Faz 7C düşen arz ailesi (EK 3 §8.3, Aşama P4): yeni girdi satırları yalnız bu dört modele bağlanır (eski 23 dosya bayt-eşit).
FALL_IDS: tuple[str, ...] = ("fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO")
FALL_DEFLATOR_IDS: tuple[str, ...] = ("fall_d10_v0_h99", "fall_d10_v0_pooled")

# İkinci dizin (EK 3 §4.1, §6.4; Aşama P2): models/INDEX_POST_D1.json, sırasıyla.
PINNED_POST_D1_MODEL_IDS: tuple[str, ...] = ("post_d1_hazard_v0",)
POST_D1_PARENT_ID = "ceiling_hazard_v0"
POST_D1_PATH_ID = "ceiling_path_v0"

# Yalnız bu üç modele bağlanan girdi satırları (U46: 16 eski dosya bayt-eşit kalır).
PATH_IDS: tuple[str, ...] = ("ceiling_path_v0", "ceiling_path_v0@INF", "pb_ceiling_path_v0")
# Koşullu karışım altın dosyası (§3.4): model başına taban satır sayısı ve H99 seçimi.
N_COND_BASE = 40
N_COND_REGISTRY = 7

# Portun tanımı: bu dosyaların baytları MANIFEST'e yazılır; Rust testi değişikliği yakalar.
PREDICT_SOURCES: tuple[str, ...] = (
    "borsai/predict.py",
    "borsai/predict_hazard.py",
    "borsai/predict_pb.py",
    "borsai/predict_market20.py",
    "borsai/features.py",
    "borsai/horizons.py",
    "borsai/survival.py",
    "borsai/predict_path.py",
    "borsai/tufe.py",
    "borsai/predict_post_d1.py",
    "borsai/predict_fall.py",
)

BANNED_MODULES = ("numpy", "sklearn", "scipy", "joblib", "threadpoolctl", "narwhals")

INPUT_FIELDS = reg.V15_FIELDS + reg.PB_FIELDS
DEL = object()  # girdi anahtarını kaldır (None'dan ayrı: None = JSON null)

# NETGL girdi belgesinin değerleri (registry/inputs/NETGL.json): uç satırların tabanı.
BASE: dict[str, Any] = {
    "ipo_price_tl": "25.52",
    "shares_offered": "87500000",
    "post_ipo_share_capital": "312500000",
    "capital_increase_shares": "62500000",
    "existing_share_sale_shares": "25000000",
    "total_demand_multiple": "2.84",
    "total_demand_filter_status": "NOT_SPECIFIED",
    "additional_sale_shares": "0",
    "ipo_size_tl": "2233000000",
    "ipo_price_try": "25.52",
    "planned_pre_ipo_capital": "250000000",
    "planned_post_ipo_capital": "312500000",
    "planned_capital_increase_shares": "62500000",
    "planned_existing_share_sale": "25000000",
    "planned_base_offer_shares": "87500000",
    "planned_additional_sale_ceiling": "0",
    "planned_max_offer_shares": "87500000",
}
BASE_EXTRA: dict[str, Any] = {"f6_market20": "0.0123", "f6_market20_refusal": None}


# ---------------------------------------------------------------- yardımcılar

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def encode(x: Any) -> Any:
    """JSON'a: sonlu olmayan float -> "NaN"/"Infinity"/"-Infinity" (Rust aynı biçimi üretir)."""
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


def dumps(x: Any) -> str:
    return json.dumps(encode(x), ensure_ascii=False, sort_keys=True, allow_nan=False)


def model_kind(params: dict) -> str:
    """borsai/freeze.py: model_kind ile aynı (INDEX modelleri; POST_D1 ikinci dizindedir)."""
    algorithm = params.get("algorithm")
    feats = list(params.get("features") or [])
    if algorithm == pf.FALL_ALGORITHM:
        return "fall"
    if algorithm == ph.HAZARD_ALGORITHM:
        return "hazard"
    if algorithm == pth.ALGORITHM:
        return "ceiling_path"
    if algorithm in ph.KM_ALGORITHMS:
        return "km"
    if algorithm == "V1_5_RIDGE_LOGIT":
        if "f6" in feats:
            return "market20"
        if any(str(f).startswith("pb") for f in feats):
            return "pb"
        return "linear"
    return "rule"


def call(params: dict, inputs: dict, entry: str) -> dict:
    """freeze.run_model'in dağıtımı; entry == "core": predict.predict doğrudan."""
    if entry == "core":
        return pr.predict(params, inputs)
    kind = model_kind(params)
    if kind in ("hazard", "km"):
        return ph.predict(params, inputs)
    if kind == "ceiling_path":
        return pth.predict(params, inputs)
    if kind == "market20":
        return pm.predict(params, inputs)
    if kind == "pb":
        return ppb.predict(params, inputs)
    if kind == "fall":
        return pf.predict(params, inputs)
    return pr.predict(params, inputs)


def evaluate(params: dict, inputs: dict, entry: str = "run_model") -> dict:
    try:
        out = call(params, inputs, entry)
    except pr.PredictError as exc:
        return {"error": {"code": exc.code}}
    except Exception as exc:  # Python'un etiketsiz istisnası: Rust DOMAIN_ERROR döner
        return {"exception": type(exc).__name__}
    return {"output": out}


def conditional(S: list[float], j: int) -> Optional[dict]:
    """SPEC_APP §3g: S_k/S_j, P_L[k]/S_j, 1 − S_{j+1}/S_j; S_0 = 1; j ≥ 10 ya da S_j = 0 tanımsız."""
    if j >= sv.DAYS:
        return None
    sj = 1.0 if j == 0 else S[j - 1]
    if sj == 0.0:
        return None
    PL = sv.p_streak(S)
    return {
        "j": j,
        "S_cond": [S[k - 1] / sj if k > j else None for k in range(1, sv.DAYS + 1)],
        "P_L_cond": [PL[l] / sj if l >= j else None for l in range(0, sv.DAYS + 1)],
        "p_break_next": 1.0 - S[j] / sj,
    }


def derived_tags(expected: dict) -> list[str]:
    if "error" in expected:
        return [f"error:{expected['error']['code']}"]
    if "exception" in expected:
        return [f"exception:{expected['exception']}"]
    out = expected["output"]
    tags = []
    r = out.get("refused")
    if r:
        tags.append(f"refused:{r['code']}:{r['field']}")
    for w in out.get("warnings", []):
        key = w.get("feature") or w.get("horizon") or w.get("field")
        if w["code"] == pr.WARN_OUT_OF_TRAINING_RANGE:
            side = "low" if not (w["value"] >= w["train_min"]) else "high"
            tags.append(f"warning:{w['code']}:{key}:{side}")
        else:
            tags.append(f"warning:{w['code']}:{key}")
    for h in ("D1", "D3", "D5", "D10"):
        cell = out.get(h)
        if isinstance(cell, dict) and cell.get("return_clipped"):
            tags.append(f"clipped:{h}:{cell['return_clipped']}")
    # tavan yolu (§3.1): kırılma sonrası durum ve havuzlama etiketleri
    for h in range(1, sv.DAYS + 1):
        cell = out.get(f"D{h}")
        pbk = cell.get("post_break") if isinstance(cell, dict) else None
        if not isinstance(pbk, dict):
            continue
        if pbk.get("status") == pth.STATUS_POST_BREAK_INSUFFICIENT:
            tags.append(f"status:D{h}:{pth.STATUS_POST_BREAK_INSUFFICIENT}")
        if any(c.get("pooled") for c in pbk.get("cells", [])):
            tags.append(f"pooled:D{h}")
    # Faz 7 v1 (EK 3 §4.2): rejim ve TÜFE etiketleri; 19 eski modelin çıktısında bu anahtarlar yoktur
    if "regime_value_used" in out:
        tags += [f"regime:{out['regime_value_used']}", f"regime_source:{out['regime_source']}"]
    if out.get("tufe_index_used") is not None:      # v1 çıktısında anahtar yalnız kullanılınca var; (C)'de her zaman (null olabilir)
        tags.append("tufe:USED")
    if out.get("add_sale_used") is not None:        # yalnız (C) çıktısı
        tags.append(f"add_sale:{out['add_sale_used']}")
    if r and str(r["code"]).startswith("TUFE_"):
        tags.append(f"tufe:{r['code']}")
    if isinstance(out.get("limit_path"), dict):
        lp = out["limit_path"]
        # uyarı koşulu DEĞER eşitliğidir ("136" ↔ "136.0" uyarı vermez)
        snap_eq = Decimal(lp["ipo_price"]) == Decimal(lp["snapped_ipo_price"])
        tags.append("snap:equal" if snap_eq else "snap:different")
    return sorted(set(tags))


# ---------------------------------------------------------------- modeller

def load_models() -> tuple[str, list[tuple[dict, dict, str]]]:
    index_bytes = (ROOT / "models" / "INDEX.json").read_bytes()
    index = json.loads(index_bytes)
    entries = index["models"][: len(PINNED_MODEL_IDS)]
    ids = tuple(e["model_id"] for e in entries)
    if ids != PINNED_MODEL_IDS:
        raise SystemExit(f"INDEX'in ilk {len(PINNED_MODEL_IDS)} kaydı sabit listeyle aynı değil: {ids}")
    models = []
    for e in entries:
        raw = (ROOT / "models" / e["file"]).read_bytes()
        sha = sha256_bytes(raw)
        if sha != e["sha256"]:
            raise SystemExit(f"{e['model_id']}: sha256 INDEX ile uyuşmuyor")
        models.append((e, json.loads(raw), sha))
    return sha256_bytes(index_bytes), models


# ---------------------------------------------------------------- girdi planı

class Case:
    def __init__(self, tag: str, inputs: dict, extra: dict, *, entry: str = "run_model",
                 only: Optional[tuple[str, ...]] = None, seq: Optional[tuple[str, int]] = None) -> None:
        self.tags = [tag]
        self.inputs = inputs
        self.extra = extra
        self.entry = entry
        self.only = only
        # (önek, sıra): kodsuz case_id `<model>/<önek>/<sıra>` (eski kohort açık kümesi; EK 3 §4.2)
        self.seq = seq

    def key(self) -> str:
        return dumps([self.inputs, self.extra, self.entry, self.only])


def variant(mods: Optional[dict] = None, extra: Optional[dict] = None, base: Optional[dict] = None) -> tuple[dict, dict]:
    inputs = dict(BASE if base is None else base)
    for k, v in (mods or {}).items():
        if v is DEL:
            inputs.pop(k, None)
        else:
            inputs[k] = v
    ex = dict(BASE_EXTRA)
    for k, v in (extra or {}).items():
        if v is DEL:
            ex.pop(k, None)
        else:
            ex[k] = v
    return inputs, ex


def read_columns(path: Path, columns: tuple[str, ...], key: str = "ticker") -> dict[str, dict[str, str]]:
    """CSV'den yalnız istenen sütunlar (diğer sütunlar hiçbir yerde tutulmaz)."""
    out: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        idx = {c: header.index(c) for c in (key, *columns)}
        for row in reader:
            out[row[idx[key]]] = {c: row[idx[c]] for c in columns}
    return out


def h99_cases(rng: random.Random) -> list[Case]:
    table_cols = ("ipo_price_tl", "shares_offered", "post_ipo_share_capital", "capital_increase_shares",
                  "existing_share_sale_shares", "total_demand_multiple", "total_demand_filter_status",
                  "additional_sale_shares")
    table = read_columns(ROOT / "data" / "training_table.csv", table_cols)
    master = read_columns(ROOT / "data" / "raw" / "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv",
                          ("ipo_size_tl",))
    pb = read_columns(ROOT / "data" / "raw" / "PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv",
                      ft.PB_REQUIRED_FIELDS)
    cases = []
    for tk in table:  # dosya sırası
        inputs = {c: (v if v != "" else None) for c, v in table[tk].items()}
        size = master[tk]["ipo_size_tl"]
        inputs["ipo_size_tl"] = size if size != "" else None
        inputs.update(pb[tk])
        extra = {"f6_market20": repr(round(rng.uniform(-0.2, 0.25), rng.randint(3, 17))), "f6_market20_refusal": None}
        cases.append(Case(f"h99:{tk}", inputs, extra))
    return cases


def registry_cases() -> list[Case]:
    cases = []
    for path in sorted((ROOT / "registry" / "inputs").glob("*.json")):
        doc, _ = reg.load_inputs(path)
        inputs = reg.model_inputs(doc)
        extra = {"f6_market20": None, "f6_market20_refusal": None}
        recs = sorted((ROOT / "registry" / "records" / doc["ticker"]).glob("*.json"))
        for rp in recs:
            rec = json.loads(rp.read_text(encoding="utf-8"))
            if rec.get("record_type") == "PREDICTION":
                mi = rec["model_inputs"]
                extra = {"f6_market20": mi.get("f6_market20"), "f6_market20_refusal": mi.get("f6_market20_refusal")}
        cases.append(Case(f"registry:{doc['ticker']}", inputs, extra))
    return cases


def rand_text(rng: random.Random, value: float, places: int) -> Any:
    """Metin (çoğu), bazen JSON sayı (Python repr yolu)."""
    r = rng.random()
    if r < 0.15:
        return round(value, places)
    return f"{value:.{places}f}"


def random_cases(rng: random.Random) -> list[Case]:
    cases = []
    for i in range(N_RANDOM):
        price = rng.uniform(1, 500)
        shares = rng.randint(1_000_000, 500_000_000)
        post = int(shares * rng.uniform(2, 12))
        frac = rng.choice([0.0, 1.0, rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0.2, 1)])
        cap = int(round(shares * frac))
        existing = shares - cap
        f3 = 10 ** rng.uniform(math.log10(0.3), math.log10(60))
        price_txt = f"{price:.2f}"
        inputs: dict[str, Any] = {
            "ipo_price_tl": price_txt if rng.random() < 0.85 else round(price, 2),
            "shares_offered": str(shares) if rng.random() < 0.85 else shares,
            "post_ipo_share_capital": str(post),
            "capital_increase_shares": str(cap),
            "existing_share_sale_shares": str(existing),
            "total_demand_multiple": rand_text(rng, f3, rng.choice([1, 2, 3])),
            "total_demand_filter_status": rng.choice(["NOT_SPECIFIED", "FILTERED", "UNFILTERED", None]),
            "additional_sale_shares": "0",
            "ipo_size_tl": rng.choice([None, "", str(int(round(Decimal(price_txt) * shares))),
                                       f"{Decimal(price_txt) * shares}"]),
        }
        # planlanan yapı: ID-A/B/C tutar; bazen taban ≠ nihai
        base = shares if rng.random() < 0.7 else int(shares * rng.uniform(0.7, 1.0))
        cap_p = min(cap, base)
        existing_p = base - cap_p
        addl = rng.choice([0, 0, int(base * rng.choice([0.1, 0.15, 0.2]))])
        post_p = max(post, base + 1)
        pre_p = post_p - cap_p
        price_try = price_txt if rng.random() < 0.8 else f"{price * rng.uniform(0.8, 1.2):.2f}"
        inputs.update({
            "ipo_price_try": price_try,
            "planned_pre_ipo_capital": str(pre_p),
            "planned_post_ipo_capital": str(post_p),
            "planned_capital_increase_shares": str(cap_p),
            "planned_existing_share_sale": str(existing_p),
            "planned_base_offer_shares": str(base),
            "planned_additional_sale_ceiling": str(addl),
            "planned_max_offer_shares": str(base + addl),
        })
        r = rng.random()
        if r < 0.7:
            f6: Any = repr(rng.uniform(-0.2, 0.25))
        elif r < 0.85:
            f6 = rng.uniform(-0.2, 0.25)  # JSON sayı
        else:
            f6 = None
        refusal = rng.choice([None, "STALE_S0", "PREDICTION_TOO_EARLY"]) if f6 is None else None
        cases.append(Case(f"random:{i:03d}", inputs, {"f6_market20": f6, "f6_market20_refusal": refusal}))
    return cases


LONG_DIGITS = "1" + "0" * 249 + "1"  # 251 hane: 200 haneli kesin bağlamda toplam kesin değil


def edge_specs() -> list[tuple[str, dict, dict, Optional[tuple[str, ...]], str]]:
    """(etiket, girdi değişikliği, extra değişikliği, yalnız modeller, entry)."""
    E: list[tuple[str, dict, dict, Optional[tuple[str, ...]], str]] = []

    def add(tag: str, mods: Optional[dict] = None, extra: Optional[dict] = None,
            only: Optional[tuple[str, ...]] = None, entry: str = "run_model") -> None:
        E.append((tag, mods or {}, extra or {}, only, entry))

    add("base:NETGL")
    # --- V1.5 girdileri: INPUT_MISSING her zorunlu alan için
    for f in ("ipo_price_tl", "shares_offered", "post_ipo_share_capital", "capital_increase_shares"):
        add(f"missing:{f}:absent", {f: DEL})
        add(f"missing:{f}:null", {f: None})
        add(f"missing:{f}:blank", {f: "   "})
        add(f"missing:{f}:DATA_NOT_FOUND", {f: "DATA_NOT_FOUND"})
    # --- INPUT_NOT_NUMERIC ("" ve DATA_NOT_FOUND eksiktir)
    for f, v in (("ipo_price_tl", "12,5"), ("ipo_price_tl", "abc"), ("shares_offered", "inf"),
                 ("post_ipo_share_capital", "nan"), ("capital_increase_shares", "-Infinity"),
                 ("total_demand_multiple", "sNaN"), ("total_demand_multiple", "12,5"), ("ipo_size_tl", "1e"),
                 ("ipo_price_tl", True), ("shares_offered", [87500000]), ("ipo_price_tl", "25.52​"),
                 ("ipo_price_tl", "_ 25.52"), ("ipo_price_tl", "1e9999999999999999999")):
        add(f"not_numeric:{f}:{v!r}", {f: v})
    # --- Decimal sözdizimi: geçerli ama olağandışı yazımlar
    for f, v in (("ipo_price_tl", " 25.52 "), ("ipo_price_tl", " 25.52　"), ("ipo_price_tl", "２５.５２"),
                 ("ipo_price_tl", "25_52"), ("ipo_price_tl", "+25.52E0"), ("ipo_price_tl", "2552e-2"),
                 ("shares_offered", "8.75e7"), ("ipo_size_tl", "2_233_000_000"), ("ipo_price_tl", 25.52),
                 ("shares_offered", 87500000), ("total_demand_multiple", 2.84), ("ipo_price_tl", "٢٥.٥٢"),
                 ("capital_increase_shares", "-0"), ("total_demand_multiple", "2.840000000000000000000000000000001")):
        add(f"syntax_ok:{f}:{v!r}", {f: v})
    # --- sonlu ama binary64'e taşan / alt taşan
    add("overflow:price:1e400", {"ipo_price_tl": "1e400", "ipo_size_tl": None})
    add("overflow:price:1e400:size", {"ipo_price_tl": "1e400"})
    add("overflow:size:1e400", {"ipo_size_tl": "1e400"})
    add("overflow:f3:1e400", {"total_demand_multiple": "1e400"})
    add("underflow:f3:1e-400", {"total_demand_multiple": "1e-400"})
    add("domain:price:1e-400", {"ipo_price_tl": "1e-400", "ipo_size_tl": None})
    add("domain:size:1e-400", {"ipo_size_tl": "1e-400"})
    add("domain:price:1e999999", {"ipo_price_tl": "1e999999", "ipo_size_tl": None})
    add("nan:f1_inf_f6_inf", {"ipo_price_tl": "1e400", "ipo_size_tl": None}, {"f6_market20": "1e400"})
    # --- INPUT_NOT_POSITIVE
    for f, v in (("ipo_price_tl", "0"), ("ipo_price_tl", "-25.52"), ("shares_offered", "-5"),
                 ("post_ipo_share_capital", "-312500000"), ("total_demand_multiple", "0"),
                 ("total_demand_multiple", "-2.84"), ("ipo_size_tl", "0"), ("ipo_size_tl", "-1")):
        add(f"not_positive:{f}:{v}", {f: v})
    # --- DIVISION_BY_ZERO
    add("div0:shares:0", {"shares_offered": "0"})
    add("div0:shares:0.000", {"shares_offered": "0.000"})
    add("div0:post:0", {"post_ipo_share_capital": "0"})
    add("div0:post:-0", {"post_ipo_share_capital": "-0"})
    # --- INPUT_NEGATIVE, INPUT_INCONSISTENT
    add("negative:cap:-1", {"capital_increase_shares": "-1"})
    add("negative:cap:-62500000", {"capital_increase_shares": "-62500000"})
    add("inconsistent:cap>shares", {"capital_increase_shares": "87500001"})
    add("inconsistent:cap>shares:2", {"capital_increase_shares": "1e9"})
    add("inconsistent:shares>post", {"shares_offered": "312500001", "capital_increase_shares": "62500000"})
    add("inconsistent:shares>post:2", {"post_ipo_share_capital": "87499999.99"})
    # --- f3
    for v in (DEL, None, "", "DATA_NOT_FOUND"):
        add(f"f3_missing:{'absent' if v is DEL else repr(v)}", {"total_demand_multiple": v})
    for st in ("FILTERED", "UNFILTERED", None, "BAŞKA"):
        add(f"filter_status:{st}", {"total_demand_filter_status": st})
    for v in ("1.0", "1.1487", "8.332", "8.3321", "10", "14.6", "20", "0.5", "0.3", "60"):
        add(f"f3:{v}", {"total_demand_multiple": v})
    # --- f4 = 0 ve aralık dışı
    add("f4_zero", {"capital_increase_shares": "0", "existing_share_sale_shares": "87500000"})
    add("f4_zero:0.00", {"capital_increase_shares": "0.00"})
    add("f4_low", {"capital_increase_shares": "8750000"})
    add("f4_100", {"capital_increase_shares": "87500000"})
    # --- f1 / f2 aralık
    add("f1_low:size", {"ipo_size_tl": "100000000"})
    add("f1_low:price", {"ipo_price_tl": "2", "ipo_size_tl": None})
    add("f1_high:size", {"ipo_size_tl": "9000000000"})
    add("f1_high:price", {"ipo_price_tl": "100", "ipo_size_tl": None})
    add("f2_low", {"post_ipo_share_capital": "1000000000"})
    add("f2_low:2", {"post_ipo_share_capital": "1e12"})
    add("f2_high", {"post_ipo_share_capital": "100000000"})
    add("f2_high:100", {"post_ipo_share_capital": "87500000"})
    # --- _pct yuvarlama sınırları
    add("pct:1/3", {"shares_offered": "100000000", "post_ipo_share_capital": "300000000", "capital_increase_shares": "33333333"})
    add("pct:2/3", {"shares_offered": "200000000", "post_ipo_share_capital": "300000000", "capital_increase_shares": "133333333"})
    add("pct:28digits", {"shares_offered": "87500000.00000000000000000000001", "post_ipo_share_capital": "312500000.0000000000000000000000000003"})
    # --- f6 (market20)
    for code in ("CALENDAR_NOT_COVERING", "INSUFFICIENT_HISTORY", "XU100_CLOSE_MISSING", "STALE_S0",
                 "PREDICTION_TOO_EARLY", "XU100_INTEGRITY", "NOT_PROVIDED", "FOO", None):
        add(f"f6_missing:{code}", {}, {"f6_market20": None, "f6_market20_refusal": code})
        add(f"f6_absent:{code}", {}, {"f6_market20": DEL, "f6_market20_refusal": code})
    for v in ("abc", "inf", "12,5", True):
        add(f"f6_not_numeric:{v!r}", {}, {"f6_market20": v})
    for v in ("-0.5", "0.5", "-0.11173129323940226", "0.1548254029482477", "1e400", "-1e400", 0.0123, "",
              "0.02264186974188141185457091630507431651089020677070624555745"):
        add(f"f6:{v!r}", {}, {"f6_market20": v})
    add("f6:with_refusal_code", {}, {"f6_market20": "0.01", "f6_market20_refusal": "STALE_S0"})
    # çekirdek yol (sarmalayıcısız): f6 verilmezse FEATURE_NOT_PROVIDED
    add("core:feature_not_provided", {}, {}, ("v1_5_market20_v0",), "core")
    add("core:feature_not_provided:f3_missing", {"total_demand_multiple": None}, {}, ("v1_5_market20_v0",), "core")
    add("core:feature_not_provided:2", {"ipo_size_tl": None}, {"f6_market20": DEL}, ("v1_5_market20_v0",), "core")
    # --- PB: her alan eksik
    for f in ft.PB_REQUIRED_FIELDS:
        add(f"pb_missing:{f}:null", {f: None})
        add(f"pb_missing:{f}:blank", {f: " "})
    add("pb_missing:price:abc", {"ipo_price_try": "abc"})
    add("pb_missing:price:bool", {"ipo_price_try": False})
    add("pb_missing:base:inf", {"planned_base_offer_shares": "Infinity"})
    add("pb_missing:max:list", {"planned_max_offer_shares": [1]})
    # --- PB fiyat aralığı
    for v in ("10-12", "10–12", "10—12", "10 - 12", "-5-3", "inf-nan", "24.00-26.00"):
        add(f"pb_price_range:{v}", {"ipo_price_try": v})
    for v in ("1e-5", "25.52e0", "-25.52", "25.52-", "-25.52", "25.52"):
        add(f"pb_price_not_range:{v}", {"ipo_price_try": v})
    # --- PB özdeşlikleri
    add("pb_identity:ID-A", {"planned_post_ipo_capital": "312500001"})
    add("pb_identity:ID-A:2", {"planned_pre_ipo_capital": "250000001"})
    add("pb_identity:ID-B", {"planned_base_offer_shares": "87500001", "planned_max_offer_shares": "87500001"})
    add("pb_identity:ID-B:2", {"planned_existing_share_sale": "0"})
    add("pb_identity:ID-C", {"planned_max_offer_shares": "90000000"})
    add("pb_identity:ID-C:2", {"planned_additional_sale_ceiling": "1000"})
    zero_base = {"planned_capital_increase_shares": "0", "planned_existing_share_sale": "0", "planned_base_offer_shares": "0",
                 "planned_max_offer_shares": "0", "planned_pre_ipo_capital": "312500000"}
    add("pb_identity:BASE_POSITIVE", zero_base)
    add("pb_identity:BASE_POSITIVE:2", {"planned_capital_increase_shares": "-5", "planned_existing_share_sale": "0",
                                         "planned_base_offer_shares": "-5", "planned_max_offer_shares": "-5",
                                         "planned_pre_ipo_capital": "312500005"})
    add("pb_identity:POST_POSITIVE", {"planned_pre_ipo_capital": "-100000000", "planned_post_ipo_capital": "-37500000"})
    add("pb_identity:POST_POSITIVE:2", {"planned_pre_ipo_capital": "-62500000", "planned_post_ipo_capital": "0"})
    add("pb_identity:VALUE_POSITIVE", {"ipo_price_try": "0"})
    add("pb_identity:VALUE_POSITIVE:2", {"ipo_price_try": "-25.52"})
    add("pb_identity:PB2_RANGE", {"planned_pre_ipo_capital": "10000000", "planned_post_ipo_capital": "72500000"})
    add("pb_identity:PB2_RANGE:2", {"planned_pre_ipo_capital": "20000000", "planned_post_ipo_capital": "82500000"})
    add("pb_identity:PB3_RANGE", {"planned_capital_increase_shares": "0", "planned_existing_share_sale": "87500000",
                                   "planned_pre_ipo_capital": "312500000"})
    add("pb_identity:PB3_RANGE:2", {"planned_capital_increase_shares": "90000000", "planned_existing_share_sale": "-2500000",
                                     "planned_pre_ipo_capital": "222500000"})
    add("pb_identity:PB4_RANGE", {"planned_additional_sale_ceiling": "-1000", "planned_max_offer_shares": "87499000"})
    add("pb_identity:PB4_RANGE:2", {"planned_additional_sale_ceiling": "-87500000", "planned_max_offer_shares": "0"})
    add("pb_identity:ID-A:neg_post_ok_base", {"planned_pre_ipo_capital": "0", "planned_post_ipo_capital": "62500000"})
    # --- PB kesinlik (200 hane) ve çok haneli girdiler
    add("pb_precision:pre", {"planned_pre_ipo_capital": LONG_DIGITS})
    add("pb_precision:addl", {"planned_additional_sale_ceiling": "1e-300", "planned_max_offer_shares": "87500000"})
    add("pb_precision:price_long", {"ipo_price_try": "25." + "5" * 250})
    add("pb_exact:cancel", {"planned_pre_ipo_capital": "1" + "0" * 200 + "250000000",
                            "planned_capital_increase_shares": "62500000",
                            "planned_post_ipo_capital": "1" + "0" * 200 + "312500000"})
    add("pb_many_digits", {"ipo_price_try": "25.520000000000000000000000000000000000000001"})
    add("pb_many_digits:2", {"planned_pre_ipo_capital": "250000000.000000000000000000000000000001",
                             "planned_post_ipo_capital": "312500000.000000000000000000000000000001"})
    # --- PB uyarıları ve aralık dışı
    add("pb4_positive", {"planned_additional_sale_ceiling": "13125000", "planned_max_offer_shares": "100625000"})
    add("pb4_positive:2", {"planned_additional_sale_ceiling": "0.5", "planned_max_offer_shares": "87500000.5"})
    add("pb1_low", {"ipo_price_try": "1"})
    add("pb1_high", {"ipo_price_try": "1000"})
    add("pb1_overflow:1e400", {"ipo_price_try": "1e400"})
    add("pb1_underflow:1e-400", {"ipo_price_try": "1e-400"})
    add("pb2_low", {"planned_pre_ipo_capital": "1000000000", "planned_post_ipo_capital": "1062500000"})
    add("pb2_high", {"planned_pre_ipo_capital": "100000000", "planned_post_ipo_capital": "162500000"})
    add("pb3_low", {"planned_capital_increase_shares": "8750000", "planned_existing_share_sale": "78750000",
                    "planned_pre_ipo_capital": "303750000"})
    add("pb3_100", {"planned_capital_increase_shares": "87500000", "planned_existing_share_sale": "0",
                    "planned_pre_ipo_capital": "225000000"})
    # --- kurallar (base_*): fiyat yok / ≤ 0 ret, fiyat dolu sabit
    add("rule:price_only", {k: DEL for k in BASE if k != "ipo_price_tl"}, {"f6_market20": DEL, "f6_market20_refusal": DEL})
    add("rule:price_only:2", {**{k: DEL for k in BASE if k != "ipo_price_tl"}, "ipo_price_tl": "0.01"})
    add("rule:empty", {k: DEL for k in BASE}, {"f6_market20": DEL, "f6_market20_refusal": DEL})
    path_specs(add)
    return E


# Fiyat adımı sınırları, üst limit adım geçişi, snap (HALF_UP) ve üs biçimleri (EK 2 §3.1).
PATH_TICK_EDGES: tuple[str, ...] = (
    "19.99", "19.999", "20", "20.01", "49.98", "49.99", "50", "50.05", "99.95", "99.99", "100", "100.10",
    "249.90", "250", "499.75", "500", "999.50", "1000", "2499", "2500", "2502.50",
)
PATH_UPPER_EDGES: tuple[str, ...] = (
    "18.18", "18.19", "18.2", "18.21", "45.45", "45.46", "9.09", "9.10", "9.11", "90.90", "90.95",
    "227.20", "227.30", "454.50", "909.00", "2272.50",
)
PATH_SNAP_EDGES: tuple[str, ...] = (
    "25.29", "25.295", "25.30", "55.08", "37.39", "12345.678", "0.014", "0.009", "0.005", "0.015", "999999999",
)
PATH_EXP_EDGES: tuple[str, ...] = (
    "1E2", "1E3", "1E+1", "2552e-2", "+25.52E0", "25.520", "100.00", "1e+60", "1e400", "1e-5", "1e-400",
    "1" + "0" * 61, "25." + "5" * 70, "12." + "3" * 70, "7." + "7" * 80,
)
# S_h eşiği: f3 merdiveni (ana modelde return == rho geçişleri) × fiyat 25.52
PATH_F3_LADDER: tuple[str, ...] = ("0.3", "0.5", "1.0", "1.1487", "3.5", "8.332", "14.6", "20", "60")
# PB fiyat biçimleri (yalnız pb_ceiling_path_v0'ın limit yolunu etkiler)
PATH_PB_PRICES: tuple[str, ...] = ("25.29", "1E2", "25.520", "10-12")


def path_specs(add: Any) -> None:
    """Yalnız üç tavan yolu modeline bağlı satırlar (`only=PATH_IDS`): limit yolunu ve S_h eşiğini sınar.
    `ipo_price_tl` ve `ipo_price_try` AYNI değere çekilir (PB özdeşlikleri korunur)."""
    for group, values in (
        ("tick", PATH_TICK_EDGES),
        ("upper", PATH_UPPER_EDGES),
        ("snap", PATH_SNAP_EDGES),
        ("exp", PATH_EXP_EDGES),
    ):
        for v in values:
            add(f"path_price:{group}:{v}", {"ipo_price_tl": v, "ipo_price_try": v}, only=PATH_IDS)
    for f3 in PATH_F3_LADDER:
        add(f"path_sh:{f3}", {"ipo_price_tl": "25.52", "ipo_price_try": "25.52", "total_demand_multiple": f3},
            only=PATH_IDS)
    for v in PATH_PB_PRICES:
        add(f"path_pb_price:{v}", {"ipo_price_try": v}, only=PATH_IDS)


# Kırpma hedefleri (RETURN_CLIPPED_TO_PHYSICAL_BOUND her ufukta UPPER ve LOWER): aday değişiklikler
CLIP_SINGLES: list[tuple[str, dict, dict]] = [
    ("f1_inf", {"ipo_price_tl": "1e400", "ipo_size_tl": None}, {}),
    ("f1_tiny", {"ipo_price_tl": "1e-300", "ipo_size_tl": None}, {}),
    ("size_huge", {"ipo_size_tl": "1e300"}, {}),
    ("size_tiny", {"ipo_size_tl": "1e-300"}, {}),
    ("size_1e30", {"ipo_size_tl": "1e30"}, {}),
    ("size_1e3", {"ipo_size_tl": "1000"}, {}),
    ("f2_100", {"post_ipo_share_capital": "87500000"}, {}),
    ("f2_tiny", {"post_ipo_share_capital": "1e20"}, {}),
    ("f4_zero", {"capital_increase_shares": "0"}, {}),
    ("f3_high", {"total_demand_multiple": "1e400"}, {}),
    ("f3_low", {"total_demand_multiple": "1e-400"}, {}),
    ("f6_inf", {}, {"f6_market20": "1e400"}),
    ("f6_ninf", {}, {"f6_market20": "-1e400"}),
    ("f6_50", {}, {"f6_market20": "50"}),
    ("f6_m50", {}, {"f6_market20": "-50"}),
    ("pb1_inf", {"ipo_price_try": "1e400"}, {}),
    ("pb1_tiny", {"ipo_price_try": "1e-300"}, {}),
    ("pb1_1e30", {"ipo_price_try": "1e30"}, {}),
    ("pb1_1e-20", {"ipo_price_try": "1e-20"}, {}),
    ("pb2_100", {"planned_pre_ipo_capital": "25000000", "planned_post_ipo_capital": "87500000"}, {}),
    ("pb3_low", {"planned_capital_increase_shares": "1", "planned_existing_share_sale": "87499999",
                 "planned_pre_ipo_capital": "312499999"}, {}),
]


def clip_cases(models: list[tuple[dict, dict, str]]) -> tuple[list[Case], list[dict]]:
    """Her (model, ufuk, yön) için ilk ulaşan adayı seç; ulaşılamayanları muafiyet olarak döndür."""
    candidates = [(t, m, e) for t, m, e in CLIP_SINGLES]
    for i, (t1, m1, e1) in enumerate(CLIP_SINGLES):
        for t2, m2, e2 in CLIP_SINGLES[i + 1:]:
            if set(m1) & set(m2) or set(e1) & set(e2):
                continue
            candidates.append((f"{t1}+{t2}", {**m1, **m2}, {**e1, **e2}))
    targets = []
    for entry, params, _ in models:
        for h, heads in params.get("horizons", {}).items():
            r = heads.get("return") if isinstance(heads, dict) else None
            # [KARAR] yalnız ridge başlıkları: mixture_median başlığında return_clipped yoktur ve
            # 16 modelde ridge ↔ "constant değil" eşdeğerdir (mevcut satırlar değişmez).
            if r and r.get("kind") == "ridge":
                targets += [(entry["model_id"], h, "UPPER"), (entry["model_id"], h, "LOWER")]
    by_id = {e["model_id"]: p for e, p, _ in models}
    chosen: dict[str, Case] = {}
    reached: set[tuple[str, str, str]] = set()
    for tag, mods, extra in candidates:
        inputs, ex = variant(mods, extra)
        for mid, h, side in targets:
            if (mid, h, side) in reached:
                continue
            res = evaluate(by_id[mid], {**inputs, **ex})
            cell = res.get("output", {}).get(h) if "output" in res else None
            if isinstance(cell, dict) and cell.get("return_clipped") == side:
                reached.add((mid, h, side))
                case = chosen.setdefault(tag, Case(f"clip:{tag}", inputs, ex))
                case.tags.append(f"clip_target:{mid}:{h}:{side}")
    exemptions = [{"model_id": m, "horizon": h, "direction": s,
                   "reason": "aday uç girdilerin hiçbiri bu yönde kırpma üretmedi"}
                  for m, h, s in targets if (m, h, s) not in reached]
    return list(chosen.values()), exemptions


def build_cases(models: list[tuple[dict, dict, str]]) -> tuple[list[Case], list[dict]]:
    rng = random.Random(SEED)
    cases: list[Case] = []
    cases += h99_cases(rng)
    cases += registry_cases()
    cases += random_cases(rng)
    for tag, mods, extra, only, entry in edge_specs():
        inputs, ex = variant(mods, extra)
        cases.append(Case(f"edge:{tag}", inputs, ex, entry=entry, only=only))
    clips, exemptions = clip_cases(models)
    cases += clips
    cases += v1_cases(cases, models)
    cases += fall_cases(cases, models)
    # KM/@INF: girdi değişse de çıktı sabit kalmalı; yukarıdaki bütün satırlar zaten bunu sınar.
    seen: dict[str, Case] = {}
    for c in cases:
        k = c.key()
        if k in seen:
            seen[k].tags += c.tags
        else:
            seen[k] = c
    return list(seen.values()), exemptions


# ---------------------------------------------------------------- Faz 7 v1 girdi satırları (EK 3 §4.2)

def _tufe_of(T: Optional[str], table: Any) -> dict:
    """Kayıt yolunun (`freeze.v1_record_inputs`) girdi anahtarları: tufe_index (metin) ya da tufe_refusal."""
    if not T:
        return {"tufe_index": None, "tufe_refusal": tf.TUFE_MISSING}
    try:
        return {"tufe_index": tf.index_for(T, table)["index"], "tufe_refusal": None}
    except tf.TufeRefusal as exc:
        return {"tufe_index": None, "tufe_refusal": exc.code}


def _assert_open(member: dict) -> None:
    """Hijyen bekçisi: kasa (SEALED) üyesinin hiçbir girdisi altın vektörlere girmez; istenirse DUR (kod basılmaz)."""
    if not reg.is_open(member["vault"]):
        raise SystemExit("HİJYEN: açık kümede olmayan eski kohort üyesi istendi (kod basılmıyor)")


def oot_open_members() -> list[dict]:
    """Eski kohortun etkin MEMBER satırlarından yalnız açık küme (vault != SEALED), (T, ticker) sırasıyla."""
    _, rows = reg.read_cohort()
    return [r for r in reg.cohort_members(rows) if reg.is_open(r["vault"])]


def _dec_text(x: Any) -> Decimal:
    return Decimal(repr(x)) if isinstance(x, float) else Decimal(str(x))


def v1_edge_specs(models: list[tuple[dict, dict, str]]) -> list[tuple[str, dict]]:
    """(etiket, NETGL + TÜFE (T = 2026-09-17 → 2026-07) tabanına girdi değişikliği). Her v1 kırpma sütunu için
    p05 / 2 ve 2 · p95; TÜFE girdi biçimleri ve retleri; rejim etiketleri; f3 boş + TÜFE; birlikte kırpma."""
    by_id = {e["model_id"]: p for e, p, _ in models}
    shares = Decimal(BASE["shares_offered"])
    tufe_q = Decimal("132.31") / Decimal(100)
    E: list[tuple[str, dict]] = [("v1:base", {})]
    for mid in V1_IDS:
        prep = by_id[mid].get("preprocessing") or {}
        for col, w in (prep.get("winsor") or {}).items():
            for side, target in (("low", _dec_text(w["p05"]) / 2), ("high", _dec_text(w["p95"]) * 2)):
                if col == "f1":
                    mods = {"ipo_size_tl": str(target.quantize(Decimal(1)))}
                elif col == "f1r":
                    mods = {"ipo_size_tl": str((target * tufe_q).quantize(Decimal(1)))}
                elif col == "f2":
                    f2 = min(target, Decimal(100))
                    mods = {"post_ipo_share_capital": str((shares * 100 / f2).quantize(Decimal(1)))}
                else:
                    mods = {"total_demand_multiple": str(target.quantize(Decimal("0.001")))}
                E.append((f"v1:winsor:{mid}:{col}:{side}", mods))
    # f1r TÜFE ile de kırpılır: endeks × 10 → f1r / 10 (alt), endeks / 10 → f1r × 10 (üst); f1 aralık içinde kalır
    E += [("v1:f1r_low_by_tufe", {"tufe_index": "1323.1"}), ("v1:f1r_high_by_tufe", {"tufe_index": "13.231"}),
          ("v1:f1r_clip_f1_inside", {"tufe_index": "30"})]
    # iki sütun birden
    E += [("v1:two_cols:f1r_f3", {"ipo_size_tl": "22330000000", "total_demand_multiple": "0.3"}),
          ("v1:two_cols:f2_f3", {"post_ipo_share_capital": "110000000", "total_demand_multiple": "60"})]
    # TÜFE girdisi: yok / null / boş / boşluk / sayı değil / ≤ 0 / sonlu değil / bool → TUFE_MISSING
    for v in (DEL, None, "", "  ", "abc", "0", "-1", "inf", "nan", True):
        E.append((f"v1:tufe_missing:{'absent' if v is DEL else repr(v)}", {"tufe_index": v}))
    for v in ("134.75", "134.750", "1.3475E2", "134,75", 134.75):
        E.append((f"v1:tufe_format:{v!r}", {"tufe_index": v}))
    for code in (tf.TUFE_NOT_PIT, tf.TUFE_FILE_MISMATCH, tf.TUFE_MISSING, "BOGUS"):
        E.append((f"v1:tufe_refusal:{code}", {"tufe_refusal": code}))
    for v in ("PRE_20211111", "THRESH100_20211111", "EQUAL_DIST_20230330", None, "", "UNKNOWN", 1):
        E.append((f"v1:alloc_regime:{v!r}", {"alloc_regime": v}))
    E.append(("v1:f3_missing_with_tufe", {"total_demand_multiple": None}))
    return E


def v1_cases(base_cases: list[Case], models: list[tuple[dict, dict, str]]) -> list[Case]:
    """Yalnız dört v1 modeline bağlı satırlar (`only=V1_IDS`): H99 + TÜFE (99), eski kohort açık kümesi + TÜFE + rejim
    (71, kodsuz), canlı sicil + TÜFE (7), uç durumlar."""
    table = tf.load()
    out: list[Case] = []
    ftd = read_columns(ROOT / "data" / "training_table.csv", ("first_trading_date",))
    for c in base_cases:
        tag = c.tags[0]
        if tag.startswith("h99:"):
            tk = tag[4:]
            inputs = {**c.inputs, **_tufe_of(ftd[tk]["first_trading_date"], table)}
            out.append(Case(f"h99_tufe:{tk}", inputs, dict(c.extra), only=V1_IDS))
    for i, m in enumerate(oot_open_members()):
        _assert_open(m)
        doc, _ = reg.load_inputs(reg.OOT_INPUTS_DIR / f"{m['ticker']}.json")
        if doc.get("ticker") != m["ticker"] or doc["fields"]["first_trading_date"]["value"] != m["first_trading_date"]:
            raise SystemExit(f"açık küme satırı {i}: girdi belgesi kohort satırıyla uyuşmuyor (kod basılmıyor)")
        inputs = {**reg.model_inputs(doc), **_tufe_of(m["first_trading_date"], table),
                  "alloc_regime": reg.parse_regime_tags(m["regime_tags"])["ALLOC_REGIME"]}
        if "ticker" in inputs:
            raise SystemExit("model_inputs ticker taşımamalı")
        out.append(Case(f"oot_open:{i:04d}", inputs, {"f6_market20": None, "f6_market20_refusal": None},
                        only=V1_IDS, seq=("oot", i)))
    for path in sorted((ROOT / "registry" / "inputs").glob("*.json")):
        doc, _ = reg.load_inputs(path)
        base = next(c for c in base_cases if c.tags[0] == f"registry:{doc['ticker']}")
        inputs = {**base.inputs, **_tufe_of(doc["fields"]["first_trading_date"]["value"], table)}
        out.append(Case(f"registry_tufe:{doc['ticker']}", inputs, dict(base.extra), only=V1_IDS))
    tufe_base = {"tufe_index": "132.31", "tufe_refusal": None}
    for tag, mods in v1_edge_specs(models):
        inputs, ex = variant({**tufe_base, **mods})
        out.append(Case(f"edge:{tag}", inputs, ex, only=V1_IDS))
    return out


# ---------------------------------------------------------------- Faz 7C düşen arz girdi satırları (EK 3 §8.3)

def fall_edge_specs(models: list[tuple[dict, dict, str]]) -> list[tuple[str, dict]]:
    """(etiket, NETGL + TÜFE (T = 2026-09-17 → 2026-07) tabanına girdi değişikliği): ek satış alanının bütün yolları
    (KARARLAR_C C4), h99/pooled'ın her kırpma sütunu (f1r, f3; ham değer) için p05 / 2, 2 · p95 ve eğitim aralığı içinde
    kalan kırpma, f1r'nin TÜFE ile kırpılması, birlikte kırpma, TÜFE girdi biçimleri ve retleri, Python ret sırası,
    filtre durumu (dondurulmuş mod NOT_SPECIFIED: çelişki yalnız yamalı satırda)."""
    by_id = {e["model_id"]: p for e, p, _ in models}
    tufe_q = Decimal("132.31") / Decimal(100)
    E: list[tuple[str, dict]] = [("fall:base", {})]
    for v in (DEL, None, "", "   ", "DATA_NOT_FOUND", "abc", "inf", True, "-1", "-0.001", "0", "0.0", "-0", "35000000",
              "1e400", 0.5, 35000000):
        E.append((f"fall:add_sale:{'absent' if v is DEL else repr(v)}", {"additional_sale_shares": v}))
    for mid in FALL_DEFLATOR_IDS:
        prep, ranges = by_id[mid]["preprocessing"], by_id[mid]["feature_ranges"]
        for col, w in prep["winsor"].items():
            lo, hi = _dec_text(w["p05"]), _dec_text(w["p95"])
            targets = (("low", lo / 2), ("high", hi * 2), ("low_in_range", (_dec_text(ranges[col]["min"]) + lo) / 2),
                       ("high_in_range", (hi + _dec_text(ranges[col]["max"])) / 2))
            for side, target in targets:
                if col == "f1r":
                    mods = {"ipo_size_tl": str((target * tufe_q).quantize(Decimal(1)))}
                else:
                    mods = {"total_demand_multiple": str(target.quantize(Decimal("0.001")))}
                E.append((f"fall:winsor:{mid}:{col}:{side}", mods))
    E += [("fall:f1r_low_by_tufe", {"tufe_index": "1323.1"}), ("fall:f1r_high_by_tufe", {"tufe_index": "13.231"}),
          ("fall:two_cols:f1r_f3", {"ipo_size_tl": "22330000000", "total_demand_multiple": "0.3"}),
          ("fall:two_cols:add_sale", {"ipo_size_tl": "22330000000", "total_demand_multiple": "60",
                                      "additional_sale_shares": "35000000"}),
          ("fall:add_sale_with_f3_low", {"total_demand_multiple": "1.05", "additional_sale_shares": "13125000"})]
    for v in (DEL, None, "", "  ", "abc", "0", "-1", "inf", "nan", True):
        E.append((f"fall:tufe_missing:{'absent' if v is DEL else repr(v)}", {"tufe_index": v}))
    for v in ("134.75", "134.750", "1.3475E2", "134,75", 134.75):
        E.append((f"fall:tufe_format:{v!r}", {"tufe_index": v}))
    for code in (tf.TUFE_NOT_PIT, tf.TUFE_FILE_MISMATCH, tf.TUFE_MISSING, "BOGUS"):
        E.append((f"fall:tufe_refusal:{code}", {"tufe_refusal": code}))
    for code in (tf.TUFE_NOT_PIT, tf.TUFE_FILE_MISMATCH):     # kayıt biçimi: ret kodu varken endeks null
        E.append((f"fall:tufe_refusal_no_index:{code}", {"tufe_refusal": code, "tufe_index": None}))
    E += [("fall:order:f3_missing_with_tufe", {"total_demand_multiple": None}),
          ("fall:order:f3_and_add_sale_missing", {"total_demand_multiple": None, "additional_sale_shares": None}),
          ("fall:order:tufe_and_add_sale_missing", {"tufe_index": None, "additional_sale_shares": None}),
          ("fall:order:input_error_first", {"ipo_price_tl": "abc", "tufe_index": None, "additional_sale_shares": None})]
    for st in ("FILTERED", "UNFILTERED", None):
        E.append((f"fall:filter_status:{st}", {"total_demand_filter_status": st}))
    return E


def fall_cases(base_cases: list[Case], models: list[tuple[dict, dict, str]]) -> list[Case]:
    """Yalnız dört (C) modeline bağlı satırlar (`only=FALL_IDS`): H99 + TÜFE (99; ek satış alanı eğitim tablosunun girdi
    sütunundan), eski kohort açık kümesi + TÜFE (71, kodsuz; `alloc_regime` verilmez: (C)'de rejim yok), canlı sicil + TÜFE
    (7), uç durumlar."""
    table = tf.load()
    out: list[Case] = []
    ftd = read_columns(ROOT / "data" / "training_table.csv", ("first_trading_date",))
    for c in base_cases:
        tag = c.tags[0]
        if tag.startswith("h99:") and c.only is None:
            tk = tag[4:]
            inputs = {**c.inputs, **_tufe_of(ftd[tk]["first_trading_date"], table)}
            out.append(Case(f"fall_h99_tufe:{tk}", inputs, dict(c.extra), only=FALL_IDS))
    for i, m in enumerate(oot_open_members()):
        _assert_open(m)
        doc, _ = reg.load_inputs(reg.OOT_INPUTS_DIR / f"{m['ticker']}.json")
        if doc.get("ticker") != m["ticker"] or doc["fields"]["first_trading_date"]["value"] != m["first_trading_date"]:
            raise SystemExit(f"açık küme satırı {i}: girdi belgesi kohort satırıyla uyuşmuyor (kod basılmıyor)")
        inputs = {**reg.model_inputs(doc), **_tufe_of(m["first_trading_date"], table)}
        if "ticker" in inputs:
            raise SystemExit("model_inputs ticker taşımamalı")
        out.append(Case(f"fall_oot_open:{i:04d}", inputs, {"f6_market20": None, "f6_market20_refusal": None},
                        only=FALL_IDS, seq=("oot", i)))
    for path in sorted((ROOT / "registry" / "inputs").glob("*.json")):
        doc, _ = reg.load_inputs(path)
        base = next(c for c in base_cases if c.tags[0] == f"registry:{doc['ticker']}")
        inputs = {**base.inputs, **_tufe_of(doc["fields"]["first_trading_date"]["value"], table)}
        out.append(Case(f"fall_registry_tufe:{doc['ticker']}", inputs, dict(base.extra), only=FALL_IDS))
    tufe_base = {"tufe_index": "132.31", "tufe_refusal": None}
    for tag, mods in fall_edge_specs(models):
        inputs, ex = variant({**tufe_base, **mods})
        out.append(Case(f"edge:{tag}", inputs, ex, only=FALL_IDS))
    return out


# ---------------------------------------------------------------- yamalı parametreler (_patched_params.jsonl)

def patched_specs() -> list[tuple[str, str, list[tuple[list[Any], Any]], dict, dict]]:
    """(etiket, model_id, yamalar [(yol, değer)], girdi değişikliği, extra değişikliği)."""
    short_coef = [-0.006109568237524172, 0.006166132603621725, 0.008170157909692003, -0.0025110682879776573]
    filtered = [(["preprocessing", "f3_filter_mode"], "FILTERED")]
    return [
        ("filter_conflict:UNFILTERED", "v1_5_h99", filtered, {"total_demand_filter_status": "UNFILTERED"}, {}),
        ("filter_conflict:UNFILTERED:v1_6", "v1_6_h99", filtered, {"total_demand_filter_status": "UNFILTERED"}, {}),
        ("filter_conflict:market20", "v1_5_market20_v0", filtered, {"total_demand_filter_status": "UNFILTERED"}, {}),
        ("filter_same:FILTERED", "v1_5_h99", filtered, {"total_demand_filter_status": "FILTERED"}, {}),
        ("filter_not_specified", "v1_5_h99", filtered, {"total_demand_filter_status": "NOT_SPECIFIED"}, {}),
        ("filter_conflict:f3_missing", "v1_5_h99", filtered + [(["input_policy", "f3_missing"], "IMPUTE")],
         {"total_demand_filter_status": "UNFILTERED", "total_demand_multiple": None}, {}),
        ("filter_conflict:policy_allow", "v1_5_h99", filtered + [(["input_policy", "f3_filter_status_conflict"], "ALLOW")],
         {"total_demand_filter_status": "UNFILTERED"}, {}),
        ("f3_missing_imputed", "v1_5_h99", [(["input_policy", "f3_missing"], "IMPUTE")], {"total_demand_multiple": None}, {}),
        ("params_invalid:coef_len", "v1_5_h99", [(["horizons", "D1", "return", "coef"], short_coef)], {}, {}),
        ("params_invalid:coef_len:pb", "pb_v0", [(["horizons", "D5", "p_up", "coef"], [0.1, 0.2])], {}, {}),
        ("params_invalid:kind", "base_zero", [(["horizons", "D3", "return", "kind"], "spline")], {}, {}),
        ("params_invalid:constant", "base_rate", [(["horizons", "D1", "p_up", "value"], "0.9")], {}, {}),
        ("schema_unsupported", "v1_5_h99", [(["schema_version"], "borsai.model/2")], {}, {}),
        ("schema_unsupported:hazard", "ceiling_hazard_v0", [(["schema_version"], None)], {}, {}),
        ("params_invalid:gamma", "ceiling_hazard_v0", [(["gamma"], [0.1, 0.2])], {}, {}),
        ("params_invalid:day_groups", "pb_ceiling_v0", [(["day_groups", "g2"], [2, 3, 4])], {}, {}),
        ("params_invalid:km_S", "base_km_last10", [(["survival", "S"], [0.5] * 9)], {}, {}),
        ("params_invalid:pb_columns", "pb_v0", [(["preprocessing", "columns"], ["pb1", "pb2"])], {}, {}),
        ("market20_refusal_before_check", "v1_5_market20_v0", [(["schema_version"], "x")], {}, {"f6_market20": None}),
    ]


def _empty_path_cells() -> dict[str, dict[str, list]]:
    return {"Z": {str(m): [] for m in range(1, sv.DAYS + 1)}, "B": {str(m): [] for m in range(1, sv.DAYS)}}


def path_patched_specs(by_id: dict[str, tuple[dict, dict, str]]) -> list[tuple[str, str, list[tuple[list[Any], Any]], dict, dict]]:
    """Tavan yolu yamaları (EK 2 §3.2). Dosyanın SONUNA eklenir: ilk 19 satır bayt-eşit kalır (U46)."""
    cells = lambda mid: by_id[mid][1]["post_break"]["cells"]  # noqa: E731
    out: list[tuple[str, str, list[tuple[list[Any], Any]], dict, dict]] = []
    # yetersiz gözlem: bütün hücreler boş, yalnız Z.1'de 5 gözlem -> D1..D10 POST_BREAK_INSUFFICIENT
    for tag, mid in (("path:insufficient", "ceiling_path_v0"), ("path:insufficient:inf", "ceiling_path_v0@INF")):
        c = _empty_path_cells()
        c["Z"]["1"] = cells(mid)["Z"]["1"][:5]
        out.append((tag, mid, [(["post_break", "cells"], c)], {}, {}))
    # havuzlama: B.9 ilk 3, B.8 ilk 4 -> D9/D10 hücrelerinde pooled
    for tag, mid in (("path:pooled", "ceiling_path_v0"), ("path:pooled:pb", "pb_ceiling_path_v0")):
        src = cells(mid)
        out.append((tag, mid, [(["post_break", "cells", "B", "9"], src["B"]["9"][:3]),
                               (["post_break", "cells", "B", "8"], src["B"]["8"][:4])], {}, {}))
    # kırpılmış havuz: D2'de hücre (B,1) n = 10 ve değerler [-0.1, 0.1] içine kırpılır
    src = cells("ceiling_path_v0")
    out.append(("path:clipped_pool", "ceiling_path_v0", [
        (["post_break", "cells", "B", "1"], src["B"]["1"][:2]),
        (["post_break", "cells", "Z", "1"], []),
        (["post_break", "cells", "Z", "2"], []),
        (["post_break", "cells", "B", "2"], [[-0.25, "XX"], [0.30, "YY"]] + src["B"]["2"][:6]),
    ], {}, {}))
    # parametre denetimleri (PARAMS_INVALID / SCHEMA_UNSUPPORTED)
    out += [
        ("path:params:n_min", "ceiling_path_v0", [(["post_break", "N_MIN"], 9)], {}, {}),
        ("path:params:margin", "ceiling_path_v0@INF", [(["limit_path", "margin"], "0.20")], {}, {}),
        ("path:params:price_field", "pb_ceiling_path_v0", [(["limit_path", "price_field"], "ipo_price")], {}, {}),
        ("path:params:survival_id", "ceiling_path_v0", [(["survival_model_id"], "x")], {}, {}),
        ("path:params:survival_gamma", "ceiling_path_v0", [(["survival_model", "gamma"], [0.1])], {}, {}),
        ("path:params:cells_key", "ceiling_path_v0",
         [(["post_break", "cells", "B"], {m: v for m, v in src["B"].items() if m != "9"})], {}, {}),
        ("path:schema", "ceiling_path_v0@INF", [(["schema_version"], "borsai.model/2")], {}, {}),
    ]
    return out


def v1_patched_specs(by_id: dict[str, tuple[dict, dict, str]]) -> list[tuple[str, str, list[tuple[list[Any], Any]], dict, dict]]:
    """Faz 7 v1 yamaları (EK 3 §4.3). Dosyanın SONUNA eklenir: ilk 31 satır bayt-eşit kalır (U55). Silme işlemi yama
    dilinde yoktur: "silinir" olan anahtar null'a (`deflator`, `family`) ya da boş sözlüğe (`reclose_rates`) çekilir,
    kırpma sınırından tek sütun ise sözlüğün o sütunsuz kopyasıyla düşürülür (aynı ret yolu)."""
    clip, real, pooled, inf = V1_IDS
    wins = by_id[clip][1]["preprocessing"]["winsor"]
    return [
        ("v1:features:pb", clip, [(["features"], ["pb1", "pb2"]), (["beta"], {"pb1": 0.1, "pb2": 0.2})], {}, {}),
        ("v1:winsor:missing_f2", clip, [(["preprocessing", "winsor"], {k: v for k, v in wins.items() if k != "f2"})], {}, {}),
        ("v1:deflator:missing", real, [(["deflator"], None)], {}, {}),
        ("v1:regime:penalized", pooled, [(["regime", "penalized"], True)], {}, {}),
        ("v1:regime:live_value", inf, [(["regime", "live_value"], 2)], {}, {}),
        ("v1:regime:delta_bool", pooled, [(["regime", "delta"], True)], {}, {}),
        ("v1:regime:live_value_1", inf, [(["regime", "live_value"], 1)], {}, {}),
        ("v1:features:f1r_no_family", real, [(["family"], None)], {}, {}),
        ("v1:gamma:2", clip, [(["gamma"], [0.1, 0.2])], {}, {}),
        ("v1:schema", pooled, [(["schema_version"], "borsai.model/2")], {}, {}),
        ("v1:reclose:missing", real, [(["reclose_rates"], {})], {}, {}),
        ("v1:winsor:tight_f3", clip, [(["preprocessing", "winsor", "f3"], {"p05": 2.83, "p95": 2.85})], {}, {}),
    ]


def fall_patched_specs(by_id: dict[str, tuple[dict, dict, str]]) -> list[tuple[str, str, list[tuple[list[Any], Any]], dict, dict]]:
    """Faz 7C yamaları (EK 3 §8.3, +10). Dosyanın SONUNA (D1 sonrası satırlarından sonra) eklenir: ilk 51 satır bayt-eşit
    kalır (U80). Silme yerine null (`family`, `deflator`) ya da sütunsuz kopya (kırpma sınırı); girdi NETGL + TÜFE."""
    h99, pooled, addsale, zero = FALL_IDS
    wins = by_id[h99][1]["preprocessing"]["winsor"]
    d10 = by_id[addsale][1]["horizons"]["D10"]
    tufe = {"tufe_index": "132.31", "tufe_refusal": None}
    filtered = [(["preprocessing", "f3_filter_mode"], "FILTERED")]
    return [
        ("fall:family:none", h99, [(["family"], None)], tufe, {}),
        ("fall:deflator:none", pooled, [(["deflator"], None)], tufe, {}),
        ("fall:winsor:missing_f3", h99, [(["preprocessing", "winsor"], {"f1r": wins["f1r"]})], tufe, {}),
        ("fall:horizons:D1", addsale, [(["horizons", "D1"], d10)], tufe, {}),
        ("fall:schema", zero, [(["schema_version"], "borsai.model/2")], tufe, {}),
        ("fall:filter_conflict", h99, filtered, {**tufe, "total_demand_filter_status": "UNFILTERED"}, {}),
        ("fall:filter_same", pooled, filtered, {**tufe, "total_demand_filter_status": "FILTERED"}, {}),
        ("fall:zero:value_bool", zero, [(["horizons", "D10", "p_up", "value"], True)], tufe, {}),
        ("fall:return_head", addsale, [(["horizons", "D5", "return"], {"kind": "constant", "value": 0.0})], tufe, {}),
        ("fall:features:no_add_sale", h99, [(["features"], ["f1r", "f3"])], tufe, {}),
    ]


def fall_patched_rows(models: list[tuple[dict, dict, str]], start: int) -> list[dict]:
    by_id = {e["model_id"]: (e, p, s) for e, p, s in models}
    rows = []
    for tag, mid, patches, mods, extra in fall_patched_specs(by_id):
        _, params, sha = by_id[mid]
        inputs, ex = variant(mods, extra)
        expected = evaluate(apply_patch(params, patches), {**inputs, **ex})
        rows.append({
            "case_id": f"_patched/{start + len(rows):04d}",
            "model_id": mid,
            "params_sha256": sha,
            "params_patch": [[path, value] for path, value in patches],
            "inputs": inputs,
            "extra": ex,
            "expected": expected,
            "tags": [f"patched:{tag}"] + derived_tags(expected),
        })
    return rows


def apply_patch(params: dict, patches: list[tuple[list[Any], Any]]) -> dict:
    p = copy.deepcopy(params)
    for path, value in patches:
        node = p
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = value
    return p


# ---------------------------------------------------------------- satırlar

def rows_for(entry: dict, params: dict, sha: str, cases: list[Case]) -> list[dict]:
    mid = entry["model_id"]
    rows = []
    for c in cases:
        if c.only is not None and mid not in c.only:
            continue
        expected = evaluate(params, {**c.inputs, **c.extra}, c.entry)
        row: dict[str, Any] = {
            "case_id": f"{mid}/{c.seq[0]}/{c.seq[1]:04d}" if c.seq else f"{mid}/{len(rows):04d}",
            "model_id": mid,
            "params_sha256": sha,
            "inputs": c.inputs,
            "extra": c.extra,
            "expected": expected,
            "tags": c.tags + derived_tags(expected),
        }
        if c.entry != "run_model":
            row["entry"] = c.entry
        out = expected.get("output")
        if out is not None and model_kind(params) in ("hazard", "km") and out.get("S") is not None:
            row["conditional"] = [conditional(out["S"], j) for j in range(0, sv.DAYS + 1)]
        rows.append(row)
    return rows


# ---------------------------------------------------------------- koşullu karışım altın dosyası (§3.4)

def _eval_cond(fn: Any, *args: Any) -> dict:
    """Koşullu çağrının beklenen çıktısı; Python `ValueError` → Rust `CONDITIONAL_INVALID`."""
    try:
        return {"output": fn(*args)}
    except pr.PredictError as exc:
        return {"error": {"code": exc.code}}
    except Exception as exc:
        return {"exception": type(exc).__name__}


def _tick_below(text: str) -> str:
    """C_t'nin bir adım altı: gözlenen kapanış limit yolundan sapar (limit_path_mismatch = 1)."""
    c = Decimal(text)
    return str(c - pth.tick(c))


def _has_path_output(row: dict) -> bool:
    out = row.get("expected", {}).get("output")
    return isinstance(out, dict) and not out.get("refused") and isinstance(out.get("limit_path"), dict)


def conditional_base_rows(rows: list[dict]) -> list[dict]:
    """7 sicil + seed ile seçilen H99 satırları (RET edenler atlanıp sıradaki alınır), toplam 40."""
    reg = [r for r in rows if any(t.startswith("registry:") for t in r["tags"]) and _has_path_output(r)]
    h99 = [r for r in rows if any(t.startswith("h99:") for t in r["tags"])]
    order = list(range(len(h99)))
    random.Random(SEED).shuffle(order)
    need = N_COND_BASE - len(reg)
    picked = [h99[i] for i in order if _has_path_output(h99[i])][:need]
    return reg[:N_COND_REGISTRY] + picked


def conditional_rows(entry: dict, params: dict, sha: str, rows: list[dict]) -> list[dict]:
    """Model başına 40 taban satır × (10 durum-1 + 3 sapma + 10 durum-2) vektör; ayrı dosya (§3.4)."""
    mid = entry["model_id"]
    out: list[dict] = []
    for base in conditional_base_rows(rows):
        output = base["expected"]["output"]
        C: list[str] = list(output["limit_path"]["C"])
        P = Decimal(output["limit_path"]["ipo_price"])
        rec: dict[str, Any] = {
            "case_id": f"{mid}/cond/{len(out):04d}",
            "base_case_id": base["case_id"],
            "model_id": mid,
            "params_sha256": sha,
            "output": output,
            "streak_ongoing": [],
            "streak_ongoing_mismatch": [],
            "after_break": [],
        }
        for j in range(sv.DAYS):
            closes = C[:j]
            rec["streak_ongoing"].append({"j": j, "closes": closes, "expected": _eval_cond(pth.conditional, params, output, j, closes)})
        for j in (1, 3, 5):
            closes = C[:j]
            closes[-1] = _tick_below(closes[-1])
            rec["streak_ongoing_mismatch"].append({"j": j, "closes": closes, "expected": _eval_cond(pth.conditional, params, output, j, closes)})
        for t in range(sv.DAYS):
            base_price = P if t == 0 else Decimal(C[t - 1])
            close = (base_price * Decimal("0.95")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            closes = C[:t] + [str(close)]
            rec["after_break"].append({"t": t, "closes": closes, "expected": _eval_cond(pth.conditional_after_break, params, output, t, closes)})
        if not out:
            # ön koşul ihlalleri (Python ValueError → CONDITIONAL_INVALID); yalnız ilk taban satırda
            refused = {**output, "refused": {"code": "F3_MISSING", "field": "total_demand_multiple", "reason": "kurgusal"}}
            no_path = {**output, "limit_path": None}
            rec["invalid"] = [
                {"case": "streak:j=10", "fn": "conditional", "j": sv.DAYS, "closes": C,
                 "expected": _eval_cond(pth.conditional, params, output, sv.DAYS, C)},
                {"case": "streak:short_closes", "fn": "conditional", "j": 3, "closes": C[:2],
                 "expected": _eval_cond(pth.conditional, params, output, 3, C[:2])},
                {"case": "after_break:short_closes", "fn": "conditional_after_break", "t": 3, "closes": C[:3],
                 "expected": _eval_cond(pth.conditional_after_break, params, output, 3, C[:3])},
                {"case": "refused_output", "fn": "conditional", "j": 0, "closes": [], "output": refused,
                 "expected": _eval_cond(pth.conditional, params, refused, 0, [])},
                {"case": "no_limit_path", "fn": "conditional", "j": 0, "closes": [], "output": no_path,
                 "expected": _eval_cond(pth.conditional, params, no_path, 0, [])},
            ]
        out.append(rec)
    return out


def patched_rows(models: list[tuple[dict, dict, str]]) -> list[dict]:
    by_id = {e["model_id"]: (e, p, s) for e, p, s in models}
    rows = []
    for tag, mid, patches, mods, extra in patched_specs() + path_patched_specs(by_id) + v1_patched_specs(by_id):
        entry, params, sha = by_id[mid]
        inputs, ex = variant(mods, extra)
        expected = evaluate(apply_patch(params, patches), {**inputs, **ex})
        rows.append({
            "case_id": f"_patched/{len(rows):04d}",
            "model_id": mid,
            "params_sha256": sha,
            "params_patch": [[path, value] for path, value in patches],
            "inputs": inputs,
            "extra": ex,
            "expected": expected,
            "tags": [f"patched:{tag}"] + derived_tags(expected),
        })
    return rows


# ---------------------------------------------------------------- D1 sonrası (EK 3 §6.4, Aşama P2)

def load_post_d1_models() -> tuple[str, list[tuple[dict, dict, str]]]:
    """models/INDEX_POST_D1.json (sabit liste) ve dosyaları; sha256 dizinle denetlenir."""
    index_bytes = (ROOT / "models" / "INDEX_POST_D1.json").read_bytes()
    entries = json.loads(index_bytes)["models"]
    ids = tuple(e["model_id"] for e in entries)
    if ids != PINNED_POST_D1_MODEL_IDS:
        raise SystemExit(f"INDEX_POST_D1 kayıtları sabit listeyle aynı değil: {ids}")
    models = []
    for e in entries:
        raw = (ROOT / "models" / e["file"]).read_bytes()
        sha = sha256_bytes(raw)
        if sha != e["sha256"]:
            raise SystemExit(f"{e['model_id']}: sha256 INDEX_POST_D1 ile uyuşmuyor")
        models.append((e, json.loads(raw), sha))
    return sha256_bytes(index_bytes), models


def _dec_or(value: Any, fallback: str) -> Decimal:
    """Girdi metninden Decimal (float repr'i); ayrıştırılamaz ya da pozitif sonlu değilse yedek değer."""
    try:
        d = Decimal(repr(value)) if isinstance(value, float) else Decimal(str(value).strip())
    except Exception:  # noqa: BLE001 — yalnız sentetik D1 tabanı
        return Decimal(fallback)
    return d if d.is_finite() and d > 0 else Decimal(fallback)


def synth_d1(rng: random.Random, price: Decimal, shares: Decimal) -> dict:
    """Sentetik D_1 bloğu (EK 3 §6.4; kayıttaki `d1` alt kümesi: fields_raw, half_day, halt_flag). Üst limit =
    `predict_path` limit yolunun C_1'i (snap(P) × 1.10 adıma FLOOR); kapanış = üst limit (P = 0.85) ya da altında;
    kilitli (low = üst limit, P = 0.8) ya da değil; hacim ∈ [pay × 1e-4, pay × 0.6] log-tekdüze; sözleşme ∈ [1, 50 000]."""
    snapped = pth.snap(price)
    upper = pth.upper_limit(snapped)
    lower = pth.lower_limit(snapped)
    tk = pth.tick(upper)
    if rng.random() < 0.85:
        close = upper
        locked = rng.random() < 0.8
        low = upper if locked else max(upper - tk * rng.randint(1, 30), tk)
        open_ = upper if locked or rng.random() < 0.5 else max(upper - tk * rng.randint(1, 15), low)
        high = upper
    else:
        close = max(upper - tk * rng.randint(1, 40), tk)
        low = max(close - tk * rng.randint(0, 20), tk)
        open_ = min(max(close - tk * rng.randint(-5, 10), low), upper)
        high = min(max(close, open_) + tk * rng.randint(0, 10), upper)
    ratio = 10 ** rng.uniform(-4, math.log10(0.6))
    volume = max(1, int(shares * Decimal(repr(ratio))))
    trades = rng.randint(1, 50_000)
    fields = {"open": str(open_), "high": str(high), "low": str(low), "close": str(close), "volume": str(volume),
              "turnover": str((volume * close).quantize(Decimal("0.01"))), "aof": str(close), "trade_count": str(trades),
              "halt": "0", "special_trade_volume": "0", "special_trade_turnover": "0", "reference_price": str(snapped),
              "upper_limit": str(upper), "lower_limit": str(lower)}
    return {"fields_raw": fields, "half_day": 0, "halt_flag": 0}


# NETGL tabanının D_1'i (P = 25.52 → C_1 = 28.06): uç satırların tabanı (kilitli, tavan, oran 0.1).
BASE_D1_FIELDS: dict[str, Any] = {
    "open": "28.06", "high": "28.06", "low": "28.06", "close": "28.06", "volume": "8750000", "turnover": "245525000.00",
    "aof": "28.06", "trade_count": "1200", "halt": "0", "special_trade_volume": "0", "special_trade_turnover": "0",
    "reference_price": "25.52", "upper_limit": "28.06", "lower_limit": "22.98",
}


def d1_variant(fields: Optional[dict] = None, top: Optional[dict] = None) -> dict:
    f = dict(BASE_D1_FIELDS)
    for k, v in (fields or {}).items():
        if v is DEL:
            f.pop(k, None)
        else:
            f[k] = v
    d = {"fields_raw": f, "half_day": 0, "halt_flag": 0}
    for k, v in (top or {}).items():
        if v is DEL:
            d.pop(k, None)
        else:
            d[k] = v
    return d


def post_d1_edge_specs() -> list[tuple[str, dict, dict, dict, bool]]:
    """(etiket, girdi değişikliği (NETGL tabanı), D_1 alan değişikliği, D_1 üst alan değişikliği, path_params verilir mi)."""
    E: list[tuple[str, dict, dict, dict, bool]] = []

    def add(tag: str, mods: Optional[dict] = None, fields: Optional[dict] = None, top: Optional[dict] = None,
            path: bool = True) -> None:
        E.append((tag, mods or {}, fields or {}, top or {}, path))

    add("base")
    # D1_NOT_TRADED (PredictError; kayıt yazılmaz)
    add("not_traded:trade_count_0", fields={"trade_count": "0"})
    add("not_traded:trade_count_empty", fields={"trade_count": ""})
    add("not_traded:trade_count_text", fields={"trade_count": "abc"})
    add("not_traded:close_empty", fields={"close": ""})
    add("not_traded:no_fields", top={"fields_raw": DEL})
    # D1_LIMIT_NA
    add("limit_na:empty", fields={"upper_limit": ""})
    add("limit_na:zero", fields={"upper_limit": "0"})
    add("limit_na:missing", fields={"upper_limit": DEL})
    add("limit_na:before_not_ceiling", fields={"upper_limit": "", "close": "28.04"})
    # D1_NOT_CEILING (kapsam dışı; ret değil)
    add("not_ceiling:one_tick", fields={"close": "28.04"})
    add("not_ceiling:far", fields={"close": "25.00", "high": "26.10", "low": "24.50", "open": "25.52"})
    add("not_ceiling:tiny_diff", fields={"close": "28.0600000000000000001"})
    add("not_ceiling:before_volume", fields={"close": "28.04", "volume": "0"})
    # değer eşitliği (metin farkı): tavan ve kilitli
    add("ceiling:text_equal", fields={"close": "28.060", "low": "28.0600", "open": "28.06", "high": "2.806E1"})
    # D1_VOLUME_INVALID
    add("volume_invalid:zero", fields={"volume": "0"})
    add("volume_invalid:empty", fields={"volume": ""})
    add("volume_invalid:grouped", fields={"volume": "8,750,000"})
    add("volume_invalid:before_field", fields={"volume": "0", "low": ""})
    # D1_FIELD_INVALID (sıra low → open → high)
    for name in ("low", "open", "high"):
        add(f"field_invalid:{name}:empty", fields={name: ""})
        add(f"field_invalid:{name}:negative", fields={name: "-1"})
    add("field_invalid:order", fields={"high": "", "open": "0"})
    # uyarılar
    add("lock_inconsistent:open", fields={"open": "27.50"})
    add("lock_inconsistent:high", fields={"high": "28.04"})
    add("half_day:1", top={"half_day": 1})
    add("half_day:text", top={"half_day": "1"})
    add("halt:1", top={"halt_flag": 1})
    add("halt:true", top={"halt_flag": True})
    add("special:small", fields={"special_trade_volume": "1500"})
    add("special:large", fields={"special_trade_volume": "2500000.0"})
    # d1_turnover kırpma ve aralık dışı (p05 −6.92, p95 −0.62; eğitim [−7.22, 0.67])
    add("turnover:low_clip_oor", fields={"volume": "43750"})
    add("turnover:low_clip_tiny", fields={"volume": "1"})
    add("turnover:low_clip_in_range", fields={"volume": "75000"})
    add("turnover:high_clip", fields={"volume": "78750000"})
    add("turnover:high_clip_oor", fields={"volume": "262500000"})
    add("turnover:exp_volume", fields={"volume": "8.75E6"})
    add("turnover:inexact", fields={"volume": "29166667"})
    # sayı olarak JSON alanları (repr yolu)
    add("numeric_fields", fields={"close": 28.06, "upper_limit": 28.06, "low": 28.06, "open": 28.06, "high": 28.06,
                                  "volume": 8750000, "trade_count": 1200})
    # ana model: ret önce gelir (F3_MISSING); ana model uyarıları ve kırpma aynen
    add("f3_missing", {"total_demand_multiple": None})
    add("f3_missing:not_ceiling", {"total_demand_multiple": None}, fields={"close": "28.04"})
    add("f3_missing:not_traded", {"total_demand_multiple": None}, fields={"trade_count": "0"})
    add("input_shares_offered:unreached", {"shares_offered": None})
    add("base_warning:f1_high", {"ipo_size_tl": "68250000000"})
    add("base_warning:f3_clip", {"total_demand_multiple": "60"})
    add("path:price_off_grid", {"ipo_price_tl": "25.515"})
    # path_params verilmeden: path_conditional null
    add("no_path:base", path=False)
    add("no_path:not_ceiling", fields={"close": "28.04"}, path=False)
    add("no_path:low_clip", fields={"volume": "43750"}, path=False)
    return E


def evaluate_post_d1(params: dict, parent: dict, inputs: dict, d1: dict, path: Optional[dict]) -> dict:
    try:
        out = pd1.predict_post_d1(params, parent, inputs, d1, path_params=path)
    except pr.PredictError as exc:
        return {"error": {"code": exc.code}}
    except Exception as exc:  # Python'un etiketsiz istisnası: Rust DOMAIN_ERROR döner
        return {"exception": type(exc).__name__}
    return {"output": out}


def post_d1_tags(expected: dict) -> list[str]:
    tags = derived_tags(expected)
    out = expected.get("output")
    if out is None:
        return tags
    if out.get("not_applicable"):
        tags.append(f"not_applicable:{out['not_applicable']['code']}")
    tags.append("path_conditional:" + ("null" if out.get("path_conditional") is None else "set"))
    f = out.get("d1_features")
    if f:
        tags.append(f"d1_lock:{f['d1_lock']}")
        if f["clipped"]:
            tags.append("d1_turnover:clipped:" + ("low" if f["d1_turnover_ln"] < f["d1_turnover_used"] else "high"))
    return sorted(set(tags))


def post_d1_rows(entry: dict, params: dict, sha: str, cases: list[Case], by_id: dict) -> list[dict]:
    """99 H99 + 7 sicil + 80 rastgele girdi tabanı × sentetik D_1 (path_params verilir) + NETGL tabanlı uç satırlar."""
    mid = entry["model_id"]
    parent = by_id[POST_D1_PARENT_ID][1]
    path = by_id[POST_D1_PATH_ID][1]
    rng = random.Random(SEED)
    plan: list[tuple[str, dict, dict, bool]] = []
    for c in cases:
        tag = c.tags[0]
        if not tag.startswith(("h99:", "registry:", "random:")) or c.only is not None:
            continue
        price = _dec_or(c.inputs.get("ipo_price_tl"), "25.52")
        shares = _dec_or(c.inputs.get("shares_offered"), "87500000")
        plan.append((tag, dict(c.inputs), synth_d1(rng, price, shares), True))
    for tag, mods, fields, top, with_path in post_d1_edge_specs():
        inputs, _ = variant(mods)
        plan.append((f"edge:post_d1:{tag}", inputs, d1_variant(fields, top), with_path))
    rows = []
    for tag, inputs, d1, with_path in plan:
        expected = evaluate_post_d1(params, parent, inputs, d1, path if with_path else None)
        rows.append({
            "case_id": f"{mid}/{len(rows):04d}",
            "model_id": mid,
            "params_sha256": sha,
            "inputs": inputs,
            "extra": {},
            "d1": d1,
            "path_params": with_path,
            "expected": expected,
            "tags": [tag] + post_d1_tags(expected),
        })
    return rows


def post_d1_patched_specs(post: dict) -> list[tuple[str, list[tuple[list[Any], Any]]]]:
    """D1 sonrası yamalar (EK 3 §6.4, +8). NETGL girdisi, taban D_1 ve path_params ile; dosyanın SONUNA eklenir."""
    return [
        ("post_d1:parent_gamma", [(["parent", "gamma", 0], post["parent"]["gamma"][0] + 0.001)]),
        ("post_d1:delta_missing_key", [(["delta"], {"d1_lock": post["delta"]["d1_lock"]})]),
        ("post_d1:updated_days", [(["updated_days"], list(range(2, 10)))]),
        ("post_d1:columns_order", [(["d1_preprocessing", "columns"], ["d1_turnover", "d1_lock"])]),
        ("post_d1:clip_order", [(["d1_preprocessing", "clip", "d1_turnover"], {"p05": 1.0, "p95": -1.0})]),
        ("post_d1:stage", [(["stage"], "PRE")]),
        ("post_d1:path_secondary", [(["path_secondary", "model_id"], "x")]),
        ("post_d1:schema", [(["schema_version"], "borsai.model/2")]),
    ]


def post_d1_patched_rows(post_models: list[tuple[dict, dict, str]], by_id: dict, start: int) -> list[dict]:
    parent = by_id[POST_D1_PARENT_ID][1]
    path = by_id[POST_D1_PATH_ID][1]
    rows = []
    for entry, params, sha in post_models:
        for tag, patches in post_d1_patched_specs(params):
            inputs, _ = variant()
            d1 = d1_variant()
            expected = evaluate_post_d1(apply_patch(params, patches), parent, inputs, d1, path)
            rows.append({
                "case_id": f"_patched/{start + len(rows):04d}",
                "model_id": entry["model_id"],
                "params_sha256": sha,
                "params_patch": [[p, v] for p, v in patches],
                "inputs": inputs,
                "extra": {},
                "d1": d1,
                "path_params": True,
                "expected": expected,
                "tags": [f"patched:{tag}"] + derived_tags(expected),
            })
    return rows


# ---------------------------------------------------------------- U4: ondalık anlam birim durumları

LEGACY = Context(prec=28, rounding=ROUND_HALF_EVEN)
EXACT = Context(prec=200, rounding=ROUND_HALF_EVEN)


def dtuple(d: Decimal) -> str:
    sign, digits, exp = d.as_tuple()
    return f"{sign}|{int(''.join(map(str, digits)))}|{exp}"


def dec_cases() -> dict:
    parse_texts = [
        "2.84", "25.52", "  12 ", " 12　", "１２", "٢٥.٥٢", "1_000", "_1", "1_", "1__0", "1_.5", "1e1_0",
        "_ 5", "5 _", " _5", "1e400", "+5", ".5", "5.", "1E5", "1e+5", "-0", "+.5e-3", "0.000", "0012e5",
        "Infinity", "inf", "-INF", "Infinityx", "nan", "-NaN12", "sNaN", "NaNx", "12,5", "abc", "1 0", "0x10",
        "1e", "e5", ".", "1e+", "1.2.3", "1e5e3", "1e5.3", "12\x00", "5​",
        "1e999999999999999999", "10e999999999999999999", "1.0e999999999999999999", "1e9999999999999999999",
        "1e-1999999999999999997", "1e-1999999999999999998", "10e-1999999999999999998", "0e999999999999999999",
        "0e1000000000000000000", "0e-1999999999999999998", "1e-0000000000000000000000005",
        "0.02264186974188141185457091630507431651089020677070624555745", "123456789012345678901234567890.123",
    ]
    parse = []
    for t in parse_texts:
        try:
            d = Decimal(t.strip())
            parse.append({"text": t, "result": "finite" if d.is_finite() else "nonfinite",
                          "tuple": dtuple(d) if d.is_finite() else None})
        except Exception:
            parse.append({"text": t, "result": "error", "tuple": None})
    pct_pairs = [("1", "3"), ("2", "3"), ("5", "1e11"), ("1", "7"), ("62500000", "87500000"), ("87500000", "312500000"),
                 ("0", "87500000"), ("5", "1e13"), ("4.9999999999999999999999999999", "1e13"),
                 ("12345678901499999999999999999999999", "1e36"), ("1", "1"), ("33333333", "100000000"),
                 ("1234567890123456789012345678901", "9876543210987654321098765432109"),
                 ("87500000.00000000000000000000001", "312500000.0000000000000000000000000003"),
                 ("1e-999999", "1e999999"), ("2", "2.0000000000000000000000000001")]
    pct = [{"num": a, "den": b, "value": str(ft._pct(Decimal(a), Decimal(b))),
            "float": float(ft._pct(Decimal(a), Decimal(b)))} for a, b in pct_pairs]
    mul_pairs = [("87500000", "25.52"), ("1234567890123456789", "98765432109876543.21"), ("1e400", "87500000"),
                 ("9.999999999999999999999999999999", "1"), ("1e999990", "1e9"), ("1e999990", "1e10"),
                 ("0.5", "0.5"), ("99999999999999999999999999995", "1")]
    mul28 = []
    for a, b in mul_pairs:
        try:
            with localcontext(LEGACY):
                r = Decimal(a) * Decimal(b)
            mul28.append({"a": a, "b": b, "result": str(r)})
        except ArithmeticError as exc:
            mul28.append({"a": a, "b": b, "result": type(exc).__name__.upper()})
    float_texts = ["0.1", "2.84", "25.52", "9007199254740993", "9007199254740995", "1e400", "-1e400", "1e-400",
                   "2.4703282292062327e-324", "2.4703282292062328e-324", "4.9406564584124654e-324",
                   "2.2250738585072011e-308", "1.7976931348623157e308", "1.7976931348623158e308",
                   "1.7976931348623159e308", "0.300000000000000044408920985006261616945266723632812500000001",
                   "0.02264186974188141185457091630507431651089020677070624555745",
                   "-0.092426990008977120101141297657234466055005263165174860190691", "71.4285714286", "-0"]
    to_float = [{"text": t, "float": float(Decimal(t))} for t in float_texts]
    rng = random.Random(SEED + 1)
    sum_lists: list[list[float]] = [[1e16, 1.0, -1e16], [0.1] * 10, [1e308, 1e308, -1e308], [float("inf"), 1.0],
                                    [float("inf"), float("-inf")], [], [-0.0], [1e-320, 1e-320], [3.0, -3.0, 1e-17]]
    for _ in range(20):
        sum_lists.append([rng.uniform(-3, 3) * 10 ** rng.randint(-3, 3) for _ in range(rng.randint(2, 6))])
    fsum = [{"items": items, "sum": sum(items)} for items in sum_lists]
    ratio_pairs = [(1, 3), (2**53 - 1, 3), (2**60 + 1, 3), (10**400, 10**399 + 7), (1, 10**400), (3, 2**1076),
                   (10**400, 1), (-7, 3), (2**53 + 1, 2**53 + 3), (87500000 * 100, 312500000), (1, 2**1075),
                   (3, 2**1075), (2**1024 - 2**970, 1), (2**1024 - 2**970 - 1, 1), (10**30 + 1, 10**29)]
    int_ratio = []
    for n, d in ratio_pairs:
        try:
            int_ratio.append({"n": str(n), "d": str(d), "float": n / d})
        except OverflowError:
            int_ratio.append({"n": str(n), "d": str(d), "float": "OVERFLOW"})
    exact_ops = [("add", "1e300", "1"), ("add", "1", "0"), ("add", "1e200", "-1e200"), ("add", "1", "1e-199"),
                 ("add", "1", "1e-200"), ("add", "1e999999", "0"), ("add", "1e1000000", "0"),
                 ("add", "1e-1000198", "0"), ("add", "1e-1000199", "0"), ("add", str(10**200 + 5), "-5"),
                 ("add", LONG_DIGITS, "62500000"), ("add", "250000000", "62500000"), ("mul", "1e999999", "10"),
                 ("mul", "25.52", "87500000"), ("mul", "25." + "5" * 250, "87500000"), ("mul", "1e-300", "87500000")]
    exact200 = []
    for op, a, b in exact_ops:
        try:
            with localcontext(EXACT) as ctx:
                ctx.traps[Inexact] = True
                r = Decimal(a) + Decimal(b) if op == "add" else Decimal(a) * Decimal(b)
            exact200.append({"op": op, "a": a, "b": b, "result": str(r)})
        except Inexact:
            exact200.append({"op": op, "a": a, "b": b, "result": "INEXACT"})
    ln_pairs = [("25.52", "87500000"), ("76.60", "48312950"), ("1", "1"), ("1e400", "87500000"),
                ("1e-400", "87500000"), ("0.01", "1000000"), ("500", "500000000"), ("25." + "5" * 150, "87500000")]
    pb1 = []
    for price, base in ln_pairs:
        with localcontext(EXACT) as ctx:
            ctx.traps[Inexact] = True
            value = Decimal(price) * Decimal(base)
        with localcontext(Context(prec=60, rounding=ROUND_HALF_EVEN)):
            pb1.append({"price": price, "base": base, "pb1": float(value.ln())})
    return encode({"schema_version": "borsai.app_dec_cases/1", "parse": parse, "pct": pct, "mul28": mul28,
                   "to_float": to_float, "fsum": fsum, "int_ratio": int_ratio, "exact200": exact200, "pb1_ln": pb1,
                   "limit_path": limit_path_cases(), "real_size": real_size_cases()})


# ---------------------------------------------------------------- U56: f1r = büyüklük / (TÜFE / 100), 60 hane (EK 3 §4.2)

REAL_SIZE_PAIRS: tuple[tuple[str, str], ...] = (
    ("2233000000", "134.75"), ("2233000000", "13.736052"), ("521400000", "1E2"), ("1", "3"),
    ("12345678901234567890123456789", "7"), ("2233000000", "134.750"), ("4466000000", "269.5"),
    ("2233000000", "132.31"), ("87500000.00000000000000000000001", "1.3475E2"), ("1E+999990", "1E-20"),
)


def real_size_cases() -> list[dict]:
    """`predict_hazard.real_size`: metin (`str(Decimal)`) ve binary64 birebir; taşma (`decimal.Overflow`) ayrı yazılır.
    k-katı değişmezliği: ("4466000000", "269.5") ile ("2233000000", "134.75") aynı float."""
    out = []
    for size, idx in REAL_SIZE_PAIRS:
        try:
            v = ph.real_size(Decimal(size), idx)
            out.append({"size": size, "tufe_index": idx, "f1r_dec": str(v), "float": float(v)})
        except ArithmeticError as exc:
            out.append({"size": size, "tufe_index": idx, "f1r_dec": type(exc).__name__.upper(), "float": None})
    return out


# ---------------------------------------------------------------- U56: TÜFE tablosu (EK 3 §3.2, §3.5)

MONTH_FOR_TS: tuple[str, ...] = ("2026-09-25", "2026-10-01", "2020-01-06", "2026-01-15", "2026-02-01", "2026-03-31",
                                 "2026-12-31", "2023-11-02")


def tufe_base() -> bytes:
    """Gerçek dosyanın `TUFE_PIN.through_month`'a kadarki öneki (sha pinle aynı): durumlar aylık eklemeyle değişmez."""
    table = tf.load()
    base = table.prefix_bytes(TUFE_PIN["through_month"])
    if sha256_bytes(base) != TUFE_PIN["prefix_sha256"]:
        raise SystemExit("TÜFE öneki pinle uyuşmuyor")
    return base


def _edit(base: bytes, ops: list) -> bytes:
    """Durum düzenlemeleri (Rust testi aynı dili uygular): ["replace", eski, yeni] ilk geçiş · ["append", satır] ·
    ["crlf"] · ["delete_line", önek]."""
    out = base
    for op in ops:
        if op[0] == "replace":
            assert op[1].encode() in out, op
            out = out.replace(op[1].encode(), op[2].encode(), 1)
        elif op[0] == "append":
            out = out + op[1].encode() + b"\n"
        elif op[0] == "crlf":
            out = out.replace(b"\n", b"\r\n")
        elif op[0] == "delete_line":
            lines = out.split(b"\n")
            idx = next(i for i, l in enumerate(lines) if l.startswith(op[1].encode()))
            out = b"\n".join(lines[:idx] + lines[idx + 1:])
        else:
            raise ValueError(op)
    return out


SYNTH_SHA = "0" * 64
SYNTH_URL = "https://example.invalid/tufe"
APPEND_2026_09 = f"2026-09,136.5,2026-10-05,99999,{SYNTH_URL},{SYNTH_SHA}"
APPEND_2026_10 = f"2026-10,138.1,2026-11-03,99998,{SYNTH_URL},{SYNTH_SHA}"


def tufe_cases() -> dict:
    base = tufe_base()
    pin = {"through_month": TUFE_PIN["through_month"], "prefix_sha256": TUFE_PIN["prefix_sha256"]}
    variants = [
        ("base", []),
        ("append_2026_09", [["append", APPEND_2026_09]]),
        ("append_2026_09_10", [["append", APPEND_2026_09], ["append", APPEND_2026_10]]),
        ("old_row_changed", [["replace", "2020-01,14.025066,", "2020-01,14.025067,"]]),
        ("crlf", [["crlf"]]),
        ("missing_month", [["delete_line", "2020-02,"]]),
        ("bad_index_three_dots", [["replace", "2019-11,13.736052,", "2019-11,13.736.052,"]]),
        ("bad_index_space", [["replace", "2019-11,13.736052,", "2019-11, 13.736052,"]]),
        ("bad_index_zero", [["replace", "2019-11,13.736052,", "2019-11,0,"]]),
        ("release_day_2", [["replace", "2019-11,13.736052,2019-12-03,", "2019-11,13.736052,2019-12-02,"]]),
        ("release_wrong_month", [["replace", "2019-11,13.736052,2019-12-03,", "2019-11,13.736052,2020-01-03,"]]),
        ("bulletin_not_digit", [["replace", ",30859,", ",3085A,"]]),
        ("url_http", [["replace", "2019-11,13.736052,2019-12-03,30859,https://", "2019-11,13.736052,2019-12-03,30859,http://"]]),
        ("header", [["replace", "month,index,", "month,endeks,"]]),
        ("append_gap", [["append", APPEND_2026_10]]),
    ]
    parse_cases, prefix_cases, index_cases = [], [], []
    for name, ops in variants:
        raw = _edit(base, ops)
        try:
            table = tf.parse(raw)
        except tf.TufeError:
            parse_cases.append({"name": name, "ops": ops, "result": "error"})
            continue
        parse_cases.append({"name": name, "ops": ops, "result": "ok", "months": len(table.rows),
                            "last_month": table.months[-1], "file_sha256": table.file_sha256})
        for m in ("2019-11", "2026-08"):
            prefix_cases.append({"variant": name, "month": m, "prefix_sha256": table.prefix_sha256(m)})
        try:
            tf.verify_pin(table, pin)
            prefix_cases.append({"variant": name, "pin": pin, "result": "ok"})
        except tf.TufeRefusal as exc:
            prefix_cases.append({"variant": name, "pin": pin, "result": exc.code})
        for T in ("2026-09-17", "2026-10-15", "2026-11-10", "2026-12-01", "2020-01-06", "2019-12-31"):
            try:
                got = tf.index_for(T, table)
                index_cases.append({"variant": name, "t": T, "result": "ok", "month": got["month"], "index": got["index"],
                                    "release_date": got["release_date"]})
            except tf.TufeRefusal as exc:
                index_cases.append({"variant": name, "t": T, "result": exc.code, "month": exc.month})
    # bekçi (kural gereği olamaz): biçim denetimsiz tabloda yayım günü T'ye eşit ya da bir gün önce
    guard = []
    for release, T in (("2026-09-17", "2026-09-17"), ("2026-09-16", "2026-09-17"), ("2026-09-18", "2026-09-17")):
        row = tf.TufeRow("2026-07", "132.31", release, "58297", SYNTH_URL, SYNTH_SHA)
        table = tf.TufeTable(rows={"2026-07": row}, raw=b"", file_sha256="", path=tf.TUFE_REL)
        try:
            got = tf.index_for(T, table)
            guard.append({"release_date": release, "t": T, "result": "ok", "month": got["month"]})
        except tf.TufeRefusal as exc:
            guard.append({"release_date": release, "t": T, "result": exc.code, "month": exc.month})
    return {
        "schema_version": "borsai.app_tufe_cases/1",
        "file": tf.TUFE_REL,
        "base": {"through_month": TUFE_PIN["through_month"], "prefix_sha256": TUFE_PIN["prefix_sha256"]},
        "append_command": tf.APPEND_COMMAND,
        "append_command_example": tf.append_command("2026-09"),
        "month_for": [{"t": t, "month": tf.month_for(t)} for t in MONTH_FOR_TS],
        "parse": parse_cases,
        "prefix": prefix_cases,
        "index_for": index_cases,
        "index_for_guard": guard,
    }


# ---------------------------------------------------------------- U47: kesin bağlam ve limit yolu

_EXACT60 = Context(prec=60, rounding=ROUND_HALF_EVEN, traps=[Inexact])

LIMIT_PATH_TEXTS: tuple[str, ...] = (
    "25.52", "25.5", "25.520", "100", "1E2", "1E3", "25.29", "19.999", "45.45", "18.19", "0.014", "1e-400",
    "1e400", "999999999", "1" + "0" * 61, "25." + "5" * 70,
)
TICK_PROBES: tuple[str, ...] = (
    "0.01", "19.999", "20", "49.99", "50", "99.99", "100", "249.99", "250", "499.99", "500", "999.99", "1000",
    "2499.99", "2500", "10000", "1e400",
)
UPPER_PROBES: tuple[str, ...] = ("18.18", "18.19", "18.2", "18.21", "9.09", "9.10", "9.11", "45.45", "45.46")
DIV_EXACT_PAIRS: tuple[tuple[str, str], ...] = (
    ("30.2500", "0.02"), ("1E+2", "0.10"), ("100", "0.10"), ("1", "0.25"), ("0", "0.10"), ("110.0", "0.10"),
    ("1E+400", "2.50"), ("1", "3"), ("2552", "0.02"), ("0.0000", "0.01"),
)
TO_INTEGRAL_TEXTS: tuple[str, ...] = ("1E+3", "1512.50", "0.5", "0.05", "0.005", "-1.5", "4E+399", "1.0")
PY_STR_TEXTS: tuple[str, ...] = (
    "1E2", "0.0000001", "0.000001", "10", "1.0", "0E-2", "0E+2", "25.520", "1e400", "4E+399", "-25.52", "0",
)
CTX_ROUND_TEXTS: tuple[str, ...] = ("1" + "0" * 61, "1" + "0" * 60 + "1", "1.5", "1E+400")


def limit_path_cases() -> dict:
    """EK 2 §2.2–§2.3 ölçümleri: kesin bölmenin üs kuralı, `to_integral`, `str(Decimal)`, bağlam
    yuvarlaması ve limit yolu tablosu. Rust `dec_semantics` testi bu beklentileri okur."""
    rows = []
    for text in LIMIT_PATH_TEXTS:
        P = Decimal(text)
        try:
            lp = pth.limit_path(P)
        except Exception as exc:
            rows.append({"text": text, "exception": type(exc).__name__})
            continue
        rows.append({
            "text": text,
            "ipo_price": str(P),
            "snapped": str(lp["snapped_ipo_price"]),
            "tick": str(lp["tick"]),
            "C": [str(c) for c in lp["C"]],
            "rho": lp["rho"],
            "scale": lp["scale"],
            "warning": lp["snapped_ipo_price"] != P,
        })
    ticks = [{"x": x, "tick": str(pth.tick(Decimal(x)))} for x in TICK_PROBES]
    upper = [{"base": b, "upper": str(pth.upper_limit(Decimal(b)))} for b in UPPER_PROBES]
    div = []
    for a, b in DIV_EXACT_PAIRS:
        try:
            with localcontext(_EXACT60):
                q = Decimal(a) / Decimal(b)
            div.append({"a": a, "b": b, "result": str(q)})
        except ArithmeticError as exc:
            div.append({"a": a, "b": b, "result": type(exc).__name__.upper()})
    integral = [{"text": t, "floor": str(Decimal(t).to_integral_value(rounding=ROUND_FLOOR)),
                 "half_up": str(Decimal(t).to_integral_value(rounding=ROUND_HALF_UP))} for t in TO_INTEGRAL_TEXTS]
    py_str = [{"text": t, "str": str(Decimal(t))} for t in PY_STR_TEXTS]
    ctx = []
    for t in CTX_ROUND_TEXTS:
        try:
            with localcontext(_EXACT60):
                r = Decimal(t) * Decimal(1)
            ctx.append({"text": t, "result": str(r)})
        except ArithmeticError as exc:
            ctx.append({"text": t, "result": type(exc).__name__.upper()})
    bounds = [{"m": m, "lo": pth.physical_bounds(m)[0], "hi": pth.physical_bounds(m)[1]} for m in range(1, sv.DAYS + 1)]
    return {"rows": rows, "ticks": ticks, "upper": upper, "div_exact": div, "to_integral": integral,
            "py_str": py_str, "ctx_round": ctx, "physical_bounds": bounds}


# ---------------------------------------------------------------- ana akış

def generate() -> dict[str, bytes]:
    index_sha, models = load_models()
    cases, exemptions = build_cases(models)
    files: dict[str, bytes] = {}
    counts = {}
    cond_counts = {}
    for entry, params, sha in models:
        rows = rows_for(entry, params, sha, cases)
        counts[entry["model_id"]] = len(rows)
        files[f"golden/{entry['model_id']}.jsonl"] = "".join(dumps(r) + "\n" for r in rows).encode("utf-8")
        if model_kind(params) == "ceiling_path":
            crows = conditional_rows(entry, params, sha, rows)
            cond_counts[entry["model_id"]] = len(crows)
            files[f"golden/{entry['model_id']}.conditional.jsonl"] = "".join(dumps(r) + "\n" for r in crows).encode("utf-8")
    post_index_sha, post_models = load_post_d1_models()
    by_id = {e["model_id"]: (e, p, s) for e, p, s in models}
    post_counts = {}
    for entry, params, sha in post_models:
        prows_d1 = post_d1_rows(entry, params, sha, cases, by_id)
        post_counts[entry["model_id"]] = len(prows_d1)
        files[f"golden/{entry['model_id']}.jsonl"] = "".join(dumps(r) + "\n" for r in prows_d1).encode("utf-8")
    prow = patched_rows(models)
    prow += post_d1_patched_rows(post_models, by_id, len(prow))
    prow += fall_patched_rows(models, len(prow))
    files["golden/_patched_params.jsonl"] = "".join(dumps(r) + "\n" for r in prow).encode("utf-8")
    manifest = {
        "schema_version": SCHEMA,
        "seed": SEED,
        "generator": "app/parity/gen_golden.py",
        "python": sys.version.split()[0],
        "models_index_sha256": index_sha,
        "model_ids": list(PINNED_MODEL_IDS),
        "rows": counts,
        "conditional_rows": cond_counts,
        "patched_rows": len(prow),
        "n_cases": len(cases),
        "predict_sources_sha256": {p: sha256_bytes((ROOT / p).read_bytes()) for p in PREDICT_SOURCES},
        "tufe_prefix_sha256": TUFE_PIN["prefix_sha256"],
        "tufe_through_month": TUFE_PIN["through_month"],
        "oot_open_rows": sum(1 for c in cases if c.seq and c.seq[0] == "oot" and c.only == V1_IDS),
        "fall_model_ids": list(FALL_IDS),
        "fall_oot_open_rows": sum(1 for c in cases if c.seq and c.seq[0] == "oot" and c.only == FALL_IDS),
        "post_d1_model_ids": list(PINNED_POST_D1_MODEL_IDS),
        "post_d1_rows": post_counts,
        "models_index_post_d1_sha256": post_index_sha,
        "post_d1_parent": {"model_id": POST_D1_PARENT_ID, "sha256": by_id[POST_D1_PARENT_ID][2]},
        "post_d1_path": {"model_id": POST_D1_PATH_ID, "sha256": by_id[POST_D1_PATH_ID][2]},
        "post_d1_synthetic_d1": {"seed": SEED, "rule": "synth_d1: C_1 = predict_path limit yolu; kapanış = C_1 (P 0.85); "
                                 "kilit P 0.8; hacim pay × [1e-4, 0.6] log-tekdüze; sonuç dosyası okunmaz"},
        "oot_sealed_rows_excluded_by_guard": True,
        "coverage_exemptions": exemptions + [
            {"code": "S_H_THRESHOLD", "model_id": "ceiling_path_v0@INF",
             "reason": "sıfır model: özellik yoktur, S sabittir; S_h eşiğinin iki yanı aynı dosyada bulunamaz"},
            {"code": "POST_BREAK_POOLING", "where": "_patched_params.jsonl",
             "reason": "dondurulmuş hücrelerde havuzlama tetiklenmez: her hücre ≥ 11 gözlem; "
                       "havuzlama ve kırpma yalnız yamalı parametrelerle sınanır"},
            {"code": "OUT_OF_TRAINING_RANGE", "feature": "f4", "side": "high",
             "reason": "f4 = sermaye artırımı / satılan × 100 ≤ 100 (INPUT_INCONSISTENT) ve eğitim üst sınırı 100"},
            {"code": "OUT_OF_TRAINING_RANGE", "feature": "pb3", "side": "high",
             "reason": "pb3 > 100 PB3_RANGE ile reddedilir; eğitim üst sınırı 100"},
            {"code": "F3_FILTER_STATUS_CONFLICT", "where": "_patched_params.jsonl",
             "reason": "kayıtlı hiçbir modelde f3_filter_mode açık (FILTERED/UNFILTERED) değil; ret yolu yalnız yamalı parametreyle sınanır"},
            {"code": "REGIME_UNKNOWN", "only_models": list(REGIME_IDS),
             "reason": "rejim terimi yalnız pooled ve pooled@INF'te; öteki modeller alloc_regime anahtarını okumaz"},
            {"code": "TUFE_*", "only_models": list(DEFLATOR_IDS),
             "reason": "deflatör (f1r) yalnız real ve pooled'da; clip ve @INF TÜFE istemez"},
            {"code": "FEATURE_CLIPPED_TO_TRAINING_P05_P95", "feature": "f1", "only_models": ["ceiling_hazard_v1_clip"],
             "reason": "f1 (ham TL) yalnız clip'te; real/pooled f1r kullanır"},
            {"code": "FEATURE_CLIPPED_TO_TRAINING_P05_P95", "feature": "f1r", "only_models": list(DEFLATOR_IDS),
             "reason": "f1r yalnız real ve pooled'da"},
            {"code": "FEATURE_CLIPPED_TO_TRAINING_P05_P95", "model_id": "ceiling_hazard_v1_pooled@INF",
             "reason": "@INF'te özellik yok: kırpma yok, clipped ve clipped_features her satırda null"},
            {"code": "F3_MISSING", "model_id": "ceiling_hazard_v1_pooled@INF", "reason": "@INF girdi kullanmaz"},
            {"code": "INPUT_SHARES_OFFERED", "model_id": "post_d1_hazard_v0",
             "reason": "ana model (ceiling_hazard_v0) shares_offered'ı önce reddeder; dal evaluate_d1 birim testinde sınanır"},
            {"code": "OUT_OF_TRAINING_RANGE", "feature": "d1_lock", "model_id": "post_d1_hazard_v0",
             "reason": "d1_lock ∈ {0, 1} ve eğitim aralığı [0, 1]"},
            {"code": "OUT_OF_TRAINING_RANGE", "feature": "add_sale", "side": "low", "only_models": list(FALL_IDS[:3]),
             "reason": "add_sale ∈ {0, 1} ve eğitim aralığı [0, 1]"},
            {"code": "OUT_OF_TRAINING_RANGE", "feature": "add_sale", "side": "high", "only_models": list(FALL_IDS[:3]),
             "reason": "add_sale ∈ {0, 1} ve eğitim aralığı [0, 1]"},
            {"code": "F3_MISSING", "model_id": "fall_d10_v0_addsale", "reason": "addsale f3 kullanmaz (yalnız ek satış)"},
            {"code": "F3_MISSING", "model_id": "fall_d10_v0_pooled@ZERO", "reason": "@ZERO girdi okumaz"},
            {"code": "TUFE_*", "only_models": list(FALL_DEFLATOR_IDS),
             "reason": "(C)'de deflatör (f1r) yalnız h99 ve pooled'da; addsale ve @ZERO TÜFE istemez"},
            {"code": "FEATURE_CLIPPED_TO_TRAINING_P05_P95", "feature": "f1r|f3", "only_models": list(FALL_DEFLATOR_IDS),
             "reason": "(C)'de kırpma yalnız h99 ve pooled'da (f1r, f3; ham değer, ln öncesi)"},
            {"code": "ADDITIONAL_SALE_MISSING", "model_id": "fall_d10_v0_pooled@ZERO",
             "reason": "@ZERO hiçbir girdi okumaz; ret yok"},
            {"code": "F3_FILTER_STATUS_CONFLICT", "only_models": list(FALL_DEFLATOR_IDS), "where": "_patched_params.jsonl",
             "reason": "dondurulmuş (C) modellerinde f3_filter_mode NOT_SPECIFIED; çelişki yolu yamalı parametreyle"},
        ],
    }
    files["golden/MANIFEST.json"] = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    files["dec_cases.json"] = (json.dumps(dec_cases(), ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")
    files["tufe_cases.json"] = tufe_cases_bytes()
    return files


def tufe_cases_bytes() -> bytes:
    return (json.dumps(tufe_cases(), ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="diskteki dosyalarla bayt bayt karşılaştır, yazma")
    ap.add_argument("--dec-cases", action="store_true", help="yalnız dec_cases.json")
    ap.add_argument("--tufe-cases", action="store_true", help="yalnız tufe_cases.json")
    args = ap.parse_args(argv)
    if args.dec_cases:
        files = {"dec_cases.json": (json.dumps(dec_cases(), ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")}
    elif args.tufe_cases:
        files = {"tufe_cases.json": tufe_cases_bytes()}
    else:
        files = generate()
    if args.check:
        bad = [rel for rel, data in files.items() if not (HERE / rel).exists() or (HERE / rel).read_bytes() != data]
        print(json.dumps({"checked": len(files), "different": bad}, ensure_ascii=False))
        return 1 if bad else 0
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        (HERE / rel).write_bytes(data)
    print(json.dumps({"written": sorted(files)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

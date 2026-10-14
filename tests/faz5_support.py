"""Faz 5 (SPEC_POST_D1_V0) test yardımcıları.

T1 anlık görüntüsü: `predict_hazard.py`'nin davranışı değiştirmeyen refactor'undan (doğrusal öngörücü yardımcısı)
ÖNCE, temiz ağaçta (HEAD 72a000f) üretilen çıktılar. Girdiler dosyanın içinde saklanır; test aynı girdileri bugünkü
kodla yeniden çalıştırıp çıktıları `==` ile karşılaştırır (bit-eşit). Üretim komutu (bir kez, refactor'dan önce):

    .venv/bin/python tests/faz5_support.py

Kapsam: INDEX'teki bütün `hazard` ve `km` türü modeller (6) × (H99'un 99 arzı + 14 uç durum + 200 tohumlu rastgele
girdi). `ceiling_path` modelleri seri bileşenini aynı `predict_hazard.predict` ile alır; onların paritesi Faz 4 altın
ledger'ları ve dondurulmuş dosya testleriyle ayrıca sınanır (anlık görüntüye alınmadı: boyut).
"""
from __future__ import annotations

import json
import random
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SNAPSHOT_PATH = ROOT / "tests" / "reference" / "faz5_pre_refactor" / "predict_hazard_snapshot.json"
SNAPSHOT_SEED = 20260924
N_RANDOM = 200
V15_FIELDS = ("ipo_price_tl", "shares_offered", "post_ipo_share_capital", "capital_increase_shares",
              "total_demand_multiple", "ipo_size_tl")
HAZARD_KINDS = ("hazard", "km")


def _h99_inputs() -> list[dict[str, Any]]:
    from borsai.data import load_dataset, load_pb

    ds = load_dataset()
    pb = load_pb(ds)
    out = []
    for r in ds.rows:
        doc = {k: r.inputs[k] for k in V15_FIELDS}
        doc["total_demand_filter_status"] = r.total_demand_filter_status
        doc.update(pb[r.ticker].fields)
        out.append({"id": f"H99|{r.ticker}", "inputs": doc})
    return out


def _edge_inputs(base: dict[str, Any]) -> list[dict[str, Any]]:
    """Ret, kırpma ve uyarı yolları (H99'un ilk arzının girdileri üzerinde tek alan değişikliği)."""
    cases = {
        "f3_missing": {"total_demand_multiple": None},
        "f3_clipped_high": {"total_demand_multiple": "500"},
        "f3_clipped_low": {"total_demand_multiple": "0.5"},
        "f3_not_positive": {"total_demand_multiple": "-1"},
        "shares_zero": {"shares_offered": "0"},
        "shares_missing": {"shares_offered": None},
        "price_not_numeric": {"ipo_price_tl": "abc"},
        "shares_gt_capital": {"post_ipo_share_capital": "1"},
        "size_out_of_range": {"ipo_size_tl": "900000000000"},
        "pb_field_missing": {"planned_base_offer_shares": None},
        "pb_price_range": {"ipo_price_try": "10-12"},
        "pb4_positive": {"planned_additional_sale_ceiling": "1000000"},
        "price_off_tick_grid": {"ipo_price_tl": "25.29", "ipo_price_try": "25.29"},
        "size_given_shares_zero": {"shares_offered": "0", "ipo_size_tl": "100000000"},
    }
    return [{"id": f"EDGE|{name}", "inputs": {**base, **change}} for name, change in cases.items()]


def _random_inputs(h99: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random(SNAPSHOT_SEED)
    out = []
    for i in range(N_RANDOM):
        doc = dict(rng.choice(h99)["inputs"])
        for k in ("ipo_price_tl", "shares_offered", "total_demand_multiple", "ipo_size_tl"):
            if doc.get(k) is not None:
                doc[k] = str((Decimal(doc[k]) * Decimal(repr(rng.uniform(0.3, 3.0)))).quantize(Decimal("0.0001")))
        if doc.get("shares_offered") is not None and doc.get("post_ipo_share_capital") is not None:
            doc["post_ipo_share_capital"] = str(max(Decimal(doc["post_ipo_share_capital"]), Decimal(doc["shares_offered"])))
            doc["capital_increase_shares"] = str(min(Decimal(doc["capital_increase_shares"]), Decimal(doc["shares_offered"])))
        out.append({"id": f"RANDOM|{i}", "inputs": doc})
    return out


def snapshot_cases() -> list[dict[str, Any]]:
    h99 = _h99_inputs()
    return h99 + _edge_inputs(h99[0]["inputs"]) + _random_inputs(h99)


def run_case(params: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    from borsai import predict_hazard as ph

    try:
        return ph.predict(params, inputs)
    except ph.PredictError as exc:
        return {"error": exc.code}


def index_models() -> list[tuple[str, str, dict[str, Any], str]]:
    """(model_id, tür, parametreler, dosya sha256) — INDEX'teki hazard/km modelleri."""
    from borsai import freeze as fz
    from borsai.provenance import sha256_file

    index = json.loads(fz.INDEX_PATH.read_text(encoding="utf-8"))
    out = []
    for e in index["models"]:
        params = json.loads((fz.MODELS_DIR / e["file"]).read_text(encoding="utf-8"))
        kind = fz.model_kind(params)
        if kind in HAZARD_KINDS:
            out.append((e["model_id"], kind, params, sha256_file(fz.MODELS_DIR / e["file"])))
    return out


def build_snapshot() -> dict[str, Any]:
    from borsai.provenance import code_version

    cases = snapshot_cases()
    models = index_models()
    results: dict[str, dict[str, Any]] = {}
    for model_id, _, params, _ in models:
        results[model_id] = {c["id"]: run_case(params, c["inputs"]) for c in cases}
    return {
        "description": ("T1 (BORSAI_FAZ5_POST_D1_IMPL): predict_hazard refactor'undan ÖNCE üretilen çıktılar; "
                        "girdiler aynen saklıdır, test bugünkü kodla == karşılaştırır."),
        "code_version": code_version(),
        "models": {m: {"kind": k, "params_sha256": sha} for m, k, _, sha in models},
        "cases": cases,
        "outputs": results,
    }


def load_snapshot() -> dict[str, Any]:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- varyant sayacı (SPEC_DEVIATIONS E16, F10; Faz 5 H)

FAZ5_BASE_COMMIT = "72a000f48917946fc7a84da74767dca734f19f8a"   # scores/scores.json'ı Faz 5'ten önce son yazan durum


def faz5_variants(data_version: str, log_path: Path = ROOT / "experiments" / "log.jsonl") -> int:
    """Aynı veri sürümünde günlüğe düşmüş POST_D1 modeli (model_id, spec_sha256) varyant sayısı. `scores.json` Faz 5
    görevinde yeniden üretilmediği için kartlardaki veri geneli sayaç bu kadar geride kalır (tam olarak bu kadar)."""
    from borsai.specs import POST_D1_MODEL_SPECS

    seen = set()
    for line in Path(log_path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            if e.get("kind") == "backtest" and e.get("data_version_sha256") == data_version and e.get("model_id") in POST_D1_MODEL_SPECS:
                seen.add((e["model_id"], e["spec_sha256"]))
    return len(seen)


def scores_json_is_pre_faz5() -> bool:
    import subprocess

    old = subprocess.run(["git", "show", f"{FAZ5_BASE_COMMIT}:scores/scores.json"], cwd=ROOT, check=True, capture_output=True).stdout
    return (ROOT / "scores" / "scores.json").read_bytes() == old


if __name__ == "__main__":
    if SNAPSHOT_PATH.exists():
        raise SystemExit(f"{SNAPSHOT_PATH} zaten var; anlık görüntü yalnız refactor'dan önce bir kez üretilir")
    snap = build_snapshot()
    if snap["code_version"].get("borsai_dirty"):
        raise SystemExit("borsai/ kirli; anlık görüntü temiz ağaçta üretilmeli")
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(snap, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
                             + "\n", encoding="utf-8")
    print(SNAPSHOT_PATH, sum(len(v) for v in snap["outputs"].values()), "çıktı")

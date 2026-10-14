"""Faz 5 (commit B): `post_d1_hazard_v0`'ın resmi walk-forward koşusu, altın ledger'ı, nihai fit önizlemesi ve MODELS.md
Faz 5 bölümü. Bu dosyadaki testler gerçek δ fit'ini ve walk-forward'u koşar (commit A'dan sonra)."""
from __future__ import annotations

import json
from collections import Counter

import pytest

from borsai import backtest as bt
from borsai import post_d1 as pd
from borsai import predict_hazard as ph
from borsai import predict_post_d1 as pd1
from borsai import report_faz1b as rf
from borsai import report_faz5 as r5
from borsai.provenance import ROOT, sha256_bytes, sha256_file
from borsai.specs import PLAN_POST_D1, POST_D1_MODEL_SPECS, SPEC_DOCUMENTS_FAZ5, spec_sha256

MODEL = "post_d1_hazard_v0"
GOLDEN = pd.GOLDEN_FAZ5_DIR
VOLATILE = ("created_at", "code_version", "runtime")


@pytest.fixture(scope="module")
def golden():
    ledger, manifest, preview = r5.load_faz5()
    return ledger, manifest, preview


@pytest.fixture(scope="module")
def rerun(dataset, tmp_path_factory):
    """Aynı kodla yeniden koşu; kendi geçici günlüğüne yazar (oturumun run_all günlüğü yalnız kayıtlı modelleri sayar)."""
    log = tmp_path_factory.mktemp("faz5_log") / "log.jsonl"
    res = pd.run_backtest(dataset, log_path=log, context="pytest")
    assert len(log.read_text(encoding="utf-8").splitlines()) == 1
    return res


@pytest.fixture(scope="module")
def parent():
    return pd.load_frozen(POST_D1_MODEL_SPECS[MODEL]["parent"])[0]


def test_backtest_byte_identical_to_faz5_golden(rerun, golden):
    assert rerun.ledger_csv == (GOLDEN / pd.golden_filename()).read_bytes()
    assert rerun.log_entry["ledger_sha256"] == golden[1]["runs"][MODEL]["ledger_sha256"]


def test_manifest_and_sha256sums(golden):
    _, manifest, _ = golden
    files = {manifest["runs"][MODEL]["file"]: manifest["runs"][MODEL]["ledger_sha256"],
             manifest["final_fit_preview"]["file"]: manifest["final_fit_preview"]["sha256"]}
    for name, sha in files.items():
        assert sha256_file(GOLDEN / name) == sha
    lines = (GOLDEN / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert sorted(lines) == sorted(f"{sha}  {name}" for name, sha in files.items())
    assert manifest["runs"][MODEL]["plan_id"] == PLAN_POST_D1 and manifest["runs"][MODEL]["spec_sha256"] == spec_sha256(POST_D1_MODEL_SPECS[MODEL])
    assert manifest["borsai_dirty"] is False and manifest["git_commit"] == "7ce0593f8b80afac7ca9c6b9117f9079f7abb662"


def test_official_log_has_one_post_d1_backtest_line(golden, dataset):
    entries = [json.loads(x) for x in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    hits = [e for e in entries if e.get("model_id") == MODEL]
    assert len(hits) == 1
    e = hits[0]
    spec = POST_D1_MODEL_SPECS[MODEL]
    assert e["kind"] == "backtest" and e["context"] == "faz5_golden" and e["plan_id"] == PLAN_POST_D1
    assert e["ledger_sha256"] == golden[1]["runs"][MODEL]["ledger_sha256"] == golden[1]["log_entry"]["ledger_sha256"]
    assert e["spec_sha256"] == spec_sha256(spec)
    assert e["spec_document_sha256"] == SPEC_DOCUMENTS_FAZ5["SPEC_POST_D1_V0"]["sha256"]
    assert e["survival_ledger_sha256"] == spec["survival_ledger"]["sha256"] and e["path_ledger_sha256"] == spec["path_ledger"]["sha256"]
    assert e["data_version_sha256"] == dataset.data_version_sha256 and e["borsai_dirty"] is False
    assert e["metrics"] == json.loads(json.dumps(pd.compute_metrics([_typed(r) for r in golden[0]])))


def _typed(r):
    """Ledger CSV satırı -> compute_metrics'in beklediği tipler."""
    out = dict(r)
    out["realized_L"] = int(r["realized_L"])
    for k in range(1, 11):
        out[f"S_{k}"] = float(r[f"S_{k}"]) if r[f"S_{k}"] != "" else None
    out["selected_lambda"] = r["selected_lambda"] if r["selected_lambda"] in ("", "INF") else float(r["selected_lambda"])
    return out


def test_ledger_fold_set_statuses_and_leakage(golden):
    ledger, _, _ = golden
    src = rf.load_runs()["ceiling_hazard_v0"]
    assert [r["fold_id"] for r in ledger] == [r["fold_id"] for r in src] and len(ledger) == 87
    assert list(ledger[0]) == pd.ledger_columns()
    st = Counter(r["status"] for r in ledger)
    assert st["NOT_APPLICABLE"] == 16 and st["FIT_OK"] + st["INSUFFICIENT_TRAINING_HISTORY"] + st["MODEL_NOT_FIT_DID_NOT_CONVERGE"] == 71
    for r in ledger:
        if r["training_max_session_date"]:
            assert r["training_max_session_date"] < r["prediction_date"] == r["first_trading_date"]
        if r["status"] == "FIT_OK" and r["selected_lambda"] != "INF":
            assert float(r["solver_grad_max"]) <= 1e-10


def test_t7_and_parity_failure_d_on_golden(golden):
    ledger, _, _ = golden
    fs = r5.fold_summary(ledger, rf.load_runs())
    assert fs["h1_mismatch"] == []
    assert fs["t7_max_abs"] in (None, 0.0)


def test_final_fit_preview_reproducible(dataset, golden):
    _, _, preview = golden
    fresh = json.loads(json.dumps(pd.fit_params(dataset)))
    strip = lambda d: {k: v for k, v in d.items() if k not in VOLATILE}   # noqa: E731
    assert strip(fresh) == strip(preview)
    assert preview["parent"]["sha256"] == POST_D1_MODEL_SPECS[MODEL]["parent"]["sha256"]
    # dondurma (BORSAI_FAZ5_FREEZE) sonrası donmuş dosya bu önizlemenin aynısıdır: tests/test_faz5_frozen.py


def test_10_final_fit_numpy_vs_stdlib_81(dataset, golden, parent):
    """§11-10 (81 arz, gerçek nihai fit): numpy nihai model ile stdlib predict_post_d1 |Δ| ≤ 1e-12; h_1 bit-eşit."""
    _, _, preview = golden
    numpy_side = pd.final_predictions(dataset, preview)
    d1 = pd.h99_d1(dataset)
    worst = 0.0
    rows = pd.final_training_rows(dataset)
    assert len(rows) == 81 == len(numpy_side)
    for r in rows:
        inputs = pd.model_inputs_of(r)
        a = numpy_side[r.ticker]
        b = pd1.predict_post_d1(preview, parent, inputs, d1[r.ticker].row.block())
        for key in ("hazard", "S"):
            worst = max(worst, max(abs(x - y) for x, y in zip(a[key], b[key])))
        for key in ("S_cond", "P_L_cond"):
            worst = max(worst, max(abs(a["conditional_j1"][key][k] - b["conditional_j1"][key][k]) for k in a["conditional_j1"][key]))
        assert a["hazard"][0] == b["hazard"][0] == ph.predict(parent, inputs)["hazard"][0]
    assert worst <= 1e-12


def test_models_md_faz5_section(golden):
    text = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
    section = text.split("## Faz 5: D1 sonrası güncelleme")[1]
    for rule in r5.OPERATIONAL_RULES_FAZ5:
        assert rule in section
    for heading in ("### Birincil hücre", "### Başarısızlık tanımları (§5) ve canlı akış koşulu",
                    "### §5 beklentisi ile gerçekleşen (satır satır)", "### Bütün §4 hücreleri", "### Fold özeti",
                    "### Nihai fit önizlemesi (dondurulmadı)", "### Faz 5 koşusu ve deney günlüğü"):
        assert heading in section
    for letter in ("(a)", "(b)", "(c)", "(d)"):
        assert f"**{letter}" in section
    assert "**Canlı akış koşulu (proje sahibi kararı 3): kurulur**" in section or \
           "**Canlı akış koşulu (proje sahibi kararı 3): kurulmaz**" in section
    table = section.split("### §5 beklentisi ile gerçekleşen (satır satır)")[1].split("Etiket sayıları")[0]
    rows = [l for l in table.splitlines() if l.startswith("| ") and not l.startswith("| Hücre")]
    assert len(rows) == 18 and all(("tuttu" in l or "tutmadı" in l or "kısmen" in l) for l in rows)
    assert "Model **dondurulmadı**" in section and "koşulsuz tablolarla" in section

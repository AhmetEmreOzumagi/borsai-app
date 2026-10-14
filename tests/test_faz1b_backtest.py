"""Faz 1B backtest koşuları: altın ledger'larla bayt eşitliği, resmi günlük (K4)."""
from __future__ import annotations

import json

import pytest

from borsai import backtest as bt
from borsai.provenance import ROOT, sha256_file
from borsai.specs import MODEL_SPECS, spec_sha256

from faz1b_support import CROSS_RUNS, cross_plan_results, faz1b_results

RUN_KEYS = [bt.run_key(m, p) for m, p in bt.FAZ1B_RUNS]


@pytest.fixture(scope="module")
def manifest():
    return json.loads((bt.GOLDEN_FAZ1B_DIR / "MANIFEST.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def runs(backtest_results):
    return faz1b_results(backtest_results)


def _official_log():
    return [json.loads(x) for x in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]


def test_run_list():
    assert len(RUN_KEYS) == len(set(RUN_KEYS)) == 19
    assert len(CROSS_RUNS) == 10


def test_golden_files_intact(manifest):
    sums = (bt.GOLDEN_FAZ1B_DIR / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert sorted(manifest["runs"]) == sorted(RUN_KEYS) and len(sums) == len(RUN_KEYS)
    for line in sums:
        sha, name = line.split("  ")
        assert sha256_file(bt.GOLDEN_FAZ1B_DIR / name) == sha
    for key, (m, p) in zip(RUN_KEYS, bt.FAZ1B_RUNS):
        info = manifest["runs"][key]
        assert (info["model_id"], info["plan_id"], info["spec_sha256"]) == (m, p, spec_sha256(MODEL_SPECS[m]))
        assert sha256_file(bt.GOLDEN_FAZ1B_DIR / info["file"]) == info["ledger_sha256"]


@pytest.mark.parametrize("key", RUN_KEYS)
def test_backtest_byte_identical_to_faz1b_golden(key, runs, manifest):
    golden = (bt.GOLDEN_FAZ1B_DIR / manifest["runs"][key]["file"]).read_bytes()
    assert runs[key].ledger_csv == golden, key


def test_official_log_contains_every_golden_run(manifest):
    entries = _official_log()
    for key, info in manifest["runs"].items():
        hits = [e for e in entries if e["model_id"] == info["model_id"] and e["plan_id"] == info["plan_id"]
                and e["ledger_sha256"] == info["ledger_sha256"] and e.get("run_key", e["model_id"]) == key]
        assert hits, key
        assert any(e["context"] == "faz1b_golden" for e in hits), key
        spec = MODEL_SPECS[info["model_id"]]
        if "spec_document" in spec:
            assert all(e["spec_document_sha256"] == spec["spec_document"]["sha256"] for e in hits)


def test_cross_plan_runs_logged_once_each():
    log, results = cross_plan_results()
    entries = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert [e["run_key"] for e in entries] == [bt.run_key(m, p) for m, p in CROSS_RUNS] == list(results)

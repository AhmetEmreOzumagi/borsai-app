"""K2/K5 (Faz 1B): Faz 1A altın ledger'ları, v1_5_h99 ve basit kural JSON'ları, docs/specs/
değişmedi; 2026-08-19 sonrası veri yok."""
from __future__ import annotations

import csv
import json
import subprocess

import pytest

from borsai import market20 as m20
from borsai.data import PB_PATH
from borsai.provenance import ROOT
from borsai.specs import FAZ1A_MODEL_IDS, FAZ1B_MODEL_IDS, SPEC_DOCUMENTS

FAZ1A_COMMIT = "5fa849d27c330786db928edab18888c1f888dfb5"
SPECS_COMMIT = "d3fabada3a4b3b7ada1b03681c57c29a7e303be5"
OUTCOME_CUTOFF = "2026-08-19"
LISTING_CUTOFF = "2026-08-06"


def _git_bytes(rev: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


@pytest.mark.requires_git_history
def test_faz1a_model_files_and_index_entries_unchanged():
    old_index = {e["model_id"]: e for e in json.loads(_git_bytes(FAZ1A_COMMIT, "models/INDEX.json"))["models"]}
    new_index = {e["model_id"]: e for e in json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]}
    assert set(old_index) == set(FAZ1A_MODEL_IDS)
    for m in FAZ1A_MODEL_IDS:
        assert new_index[m] == old_index[m], m
        assert (ROOT / "models" / f"{m}.json").read_bytes() == _git_bytes(FAZ1A_COMMIT, f"models/{m}.json"), m
    order = [e["model_id"] for e in json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]]
    assert order[:7] == list(old_index)  # yalnız sona eklendi


@pytest.mark.requires_git_history
def test_faz1a_golden_ledgers_unchanged():
    files = sorted(p.name for p in (ROOT / "tests" / "reference" / "macos_golden").iterdir())
    listed = sorted(_git("ls-tree", "--name-only", FAZ1A_COMMIT, "tests/reference/macos_golden/").split())
    assert ["tests/reference/macos_golden/" + f for f in files] == listed
    for f in files:
        assert (ROOT / "tests" / "reference" / "macos_golden" / f).read_bytes() == \
            _git_bytes(FAZ1A_COMMIT, f"tests/reference/macos_golden/{f}"), f


@pytest.mark.requires_git_history
def test_spec_documents_unchanged():
    assert _git("status", "--porcelain", "--untracked-files=all", "--", "docs/specs") == ""
    for doc in SPEC_DOCUMENTS.values():
        assert (ROOT / doc["path"]).read_bytes() == _git_bytes(SPECS_COMMIT, doc["path"])
    specs = sorted(p.name for p in (ROOT / "docs" / "specs").rglob("*") if p.is_file())
    assert len(specs) == 11


def test_new_inputs_have_no_data_after_cutoff(dataset):
    records, _ = m20.load_xu100()
    assert max(r.date for r in records) <= OUTCOME_CUTOFF
    assert m20.load_calendar_b().last_date <= OUTCOME_CUTOFF
    with PB_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
        pb = list(csv.DictReader(fh))
    assert max(r["canonical_first_trading_date"] for r in pb) <= LISTING_CUTOFF
    assert max(d for r in dataset.rows for d in r.session_dates) <= OUTCOME_CUTOFF


@pytest.mark.parametrize("model_id", FAZ1B_MODEL_IDS)
def test_frozen_models_cutoff(model_id):
    params = json.loads((ROOT / "models" / f"{model_id}.json").read_text(encoding="utf-8"))
    assert params["training"]["cutoff_date"] <= OUTCOME_CUTOFF
    assert params["training"]["first_trading_date_range"][1] <= LISTING_CUTOFF
    for rec in params.get("market20_training", {}).values():
        assert rec["S0_date"] < rec["ref_date"] <= LISTING_CUTOFF

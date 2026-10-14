"""K5: legacy/ değişmedi; bu repoda 2026-08-19 sonrası veri yok."""
from __future__ import annotations

import re
import subprocess

from borsai.provenance import ROOT, sha256_file

OUTCOME_CUTOFF = "2026-08-19"
LISTING_CUTOFF = "2026-08-06"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def test_legacy_files_match_provenance_hashes():
    text = (ROOT / "docs" / "PROVENANCE.md").read_text(encoding="utf-8")
    listed = dict(re.findall(r"\| `(legacy/[^`]+)` \| `([0-9a-f]{64})` \|", text))
    assert len(listed) == 34
    on_disk = {p.relative_to(ROOT).as_posix() for p in (ROOT / "legacy").rglob("*")
               if p.is_file() and "__pycache__" not in p.parts}
    assert on_disk == set(listed)
    for path, sha in listed.items():
        assert sha256_file(ROOT / path) == sha, path


def test_legacy_and_data_have_no_working_tree_changes():
    assert _git("status", "--porcelain", "--untracked-files=all", "--", "legacy", "data") == ""


def test_no_data_after_sequence_cutoff(dataset, frozen_models):
    assert dataset.outcome_sessions_through <= OUTCOME_CUTOFF
    assert max(r.first_trading_date for r in dataset.rows) <= LISTING_CUTOFF
    assert all(t.session_date <= OUTCOME_CUTOFF for r in dataset.rows for t in r.targets.values())
    for params in frozen_models.values():
        cutoff = params["training"]["cutoff_date"]
        assert cutoff is None or cutoff <= OUTCOME_CUTOFF

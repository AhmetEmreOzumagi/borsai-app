"""Faz 1B testleri için ortak yardımcılar (test modülü değil).

Yeni modellerin kendi planlarındaki koşuları conftest'teki `backtest_results`
(`run_all`) içindedir. Basit kuralların başka planlardaki koşuları (PB kesimi,
tavan planları) burada bir kez koşulur ve süreç boyunca önbellekte tutulur;
günlükleri geçici dizine yazılır (experiments/README.md: test koşuları resmi
günlüğe yazmaz).
"""
from __future__ import annotations

import functools
import json
import sys
import tempfile
from pathlib import Path

from borsai import backtest as bt
from borsai.data import load_dataset
from borsai.provenance import ROOT

CROSS_RUNS = tuple((m, p) for m, p in bt.FAZ1B_RUNS if bt.run_key(m, p) != m)


@functools.lru_cache(maxsize=None)
def cross_plan_results():
    log = Path(tempfile.mkdtemp(prefix="borsai_faz1b_cross_")) / "log.jsonl"
    return log, bt.run_suite(CROSS_RUNS, load_dataset(), log_path=log, context="pytest")


def faz1b_results(backtest_results) -> dict:
    """run_key -> BacktestResult, FAZ1B_RUNS sırasıyla."""
    _, cross = cross_plan_results()
    out = {}
    for m, p in bt.FAZ1B_RUNS:
        key = bt.run_key(m, p)
        out[key] = backtest_results[m] if key == m else cross[key]
    return out


def legacy_import():
    """legacy/ değiştirilmeden import edilir; bytecode yazılmaz (tests/test_port_vs_legacy.py ile aynı)."""
    sys.dont_write_bytecode = True
    path = str(ROOT / "legacy")
    if path not in sys.path:
        sys.path.insert(0, path)


def frozen(model_id: str) -> dict:
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
    (entry,) = [e for e in index["models"] if e["model_id"] == model_id]
    return json.loads((ROOT / "models" / entry["file"]).read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def refit(model_id: str):
    """Aynı 99 satırla yeniden fit: (params, final modeller). Süreç başına bir kez."""
    from borsai.fit import fit_with_estimators
    from borsai.specs import MODEL_SPECS

    ds = load_dataset()
    return fit_with_estimators(MODEL_SPECS[model_id], list(ds.rows), dataset_version=ds.data_version_sha256)

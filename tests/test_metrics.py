"""Eşleşik fark aralığı yöntemi (AUDIT §1.2-c) ve metrik yardımcıları."""
from __future__ import annotations

import random

from borsai import metrics as mx

import refcompare as rc

# AUDIT §1.2-c tablosu (Windows BLB fold ledger'ı; ortalama [alt, üst]), 3-4 ondalık.
AUDIT_TABLE = {
    ("V1_BASE_MEDIAN", "D1"): (+0.0046, +0.0015, +0.0079),
    ("V1_BASE_MEDIAN", "D3"): (-0.0157, -0.051, +0.020),
    ("V1_BASE_MEDIAN", "D5"): (-0.084, -0.136, -0.028),
    ("V1_BASE_MEDIAN", "D10"): (-0.116, -0.201, -0.022),
    ("V1_BASE_ZERO", "D1"): (-0.059, -0.075, -0.043),
    ("V1_BASE_ZERO", "D3"): (-0.118, -0.173, -0.071),
    ("V1_BASE_ZERO", "D5"): (-0.122, -0.214, -0.039),
    ("V1_BASE_ZERO", "D10"): (-0.050, -0.228, +0.151),
    ("V1_BASE_RATE", "D1"): (-0.008, -0.028, +0.011),
    ("V1_BASE_RATE", "D3"): (-0.036, -0.081, +0.010),
    ("V1_BASE_RATE", "D5"): (-0.034, -0.076, +0.012),
    ("V1_BASE_RATE", "D10"): (-0.039, -0.076, +0.003),
}


def _decimals(x: float) -> int:
    return len(repr(abs(x)).split(".")[1])


def test_block_bootstrap_reproduces_audit_table():
    """AUDIT'in betiği tek bir tohumlu RNG'yi sırayla kullandı; aynı sırayla aynı sayılar çıkar."""
    blb = rc.blb_ledger()
    rng = random.Random(mx.BOOTSTRAP_SEED)
    for (bid, h), expected in AUDIT_TABLE.items():
        col = "paired_brier_difference_v1_5_minus_baseline" if bid == "V1_BASE_RATE" else "paired_abs_error_difference_v1_5_minus_baseline"
        rows = [r for r in blb if r["baseline_id"] == bid and r["horizon"] == h and r[col] != ""
                and (bid != "V1_BASE_RATE" or r["in_v1_5_logistic_matched_fitted_set"] == "TRUE")]
        diffs = [float(r[col]) for r in rows]
        lo, hi = mx.block_bootstrap_ci(diffs, [r["prediction_date"][:7] for r in rows], rng=rng)
        for got, exp in zip((sum(diffs) / len(diffs), lo, hi), expected):
            assert round(got, _decimals(exp)) == exp, (bid, h, got, exp)


def test_paired_difference_is_independent_of_call_order():
    diffs = [0.1, -0.2, 0.05, -0.01, 0.3, -0.4, 0.2]
    months = ["2024-01", "2024-01", "2024-02", "2024-03", "2024-03", "2024-04", "2024-05"]
    a = mx.paired_difference(diffs, months)
    mx.paired_difference([1.0, 2.0], ["x", "y"])
    b = mx.paired_difference(diffs, months)
    assert a == b
    assert a["n"] == 7 and a["n_months"] == 5
    assert a["model_better_n"] + a["rule_better_n"] + a["tie_n"] == 7


def test_verdict_requires_interval_to_exclude_zero():
    assert mx.paired_difference([-1.0] * 12, [f"m{i}" for i in range(12)])["verdict"] == "MODEL_DAHA_IYI"
    assert mx.paired_difference([1.0] * 12, [f"m{i}" for i in range(12)])["verdict"] == "KURAL_DAHA_IYI"
    mixed = [(-1.0 if i % 2 else 1.0) for i in range(12)]
    assert mx.paired_difference(mixed, [f"m{i}" for i in range(12)])["verdict"] == "AYIRT_EDILEMIYOR"


def test_probability_clip_only_in_scoring():
    assert mx.brier_term(1.0, 1) == (0.99 - 1) ** 2
    assert mx.brier_term(0.0, 1) == (0.01 - 1) ** 2

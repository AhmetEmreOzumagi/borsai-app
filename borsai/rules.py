"""Basit kurallar: eğitim hedeflerinden sabit tahmin. Yalnız stdlib.

Sayısal tanımlar legacy `scripts/modeling/baselines.py` ile aynıdır: getiriler
float(R_h) üzerinden `statistics.median` / `statistics.mean`; oran sum(Y)/n.
ALWAYS_CEILING ve LAST10_BASE_RATE legacy'de yoktu (AUDIT §3b, §3e).
"""
from __future__ import annotations

import statistics
from typing import Optional, Sequence

from .horizons import physical_return_bounds

LAST_N = 10


def rule_return(algorithm: str, horizon: str, returns: Sequence[float]) -> Optional[float]:
    """Kuralın getiri tahmini; getiri vermeyen kural için None."""
    if algorithm == "ALWAYS_CEILING":
        return physical_return_bounds(horizon)[1]
    if algorithm == "ZERO":
        return 0.0
    if algorithm == "TRAIN_MEDIAN":
        if not returns:
            raise ValueError("TRAIN_MEDIAN boş eğitim kümesi")
        return statistics.median(returns)
    if algorithm == "TRAIN_MEAN":
        if not returns:
            raise ValueError("TRAIN_MEAN boş eğitim kümesi")
        return statistics.mean(returns)
    if algorithm in ("BASE_RATE", "LAST10_BASE_RATE"):
        return None
    raise ValueError(f"bilinmeyen kural {algorithm}")


def rule_p_up(algorithm: str, labels: Sequence[int]) -> Optional[float]:
    """Kuralın P(kapanış > arz) tahmini; olasılık vermeyen kural için None.
    `labels` eğitim sırasındadır (first_trading_date, ticker)."""
    if algorithm == "ALWAYS_CEILING":
        return 1.0
    if algorithm == "BASE_RATE":
        if not labels:
            raise ValueError("BASE_RATE boş eğitim kümesi")
        return sum(labels) / len(labels)
    if algorithm == "LAST10_BASE_RATE":
        if len(labels) < LAST_N:
            raise ValueError(f"LAST10_BASE_RATE en az {LAST_N} eğitim satırı ister")
        last = list(labels)[-LAST_N:]
        return sum(last) / len(last)
    if algorithm in ("TRAIN_MEDIAN", "TRAIN_MEAN", "ZERO"):
        return None
    raise ValueError(f"bilinmeyen kural {algorithm}")


def direction(p_up: float) -> int:
    """Legacy: p > 0.5 ise 1 (UP); tam 0.5 → 0."""
    return 1 if p_up > 0.5 else 0

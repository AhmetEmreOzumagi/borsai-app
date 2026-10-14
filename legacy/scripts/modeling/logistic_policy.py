"""Logistic class-degeneracy POLICY DECISION ONLY (V1.1 §7.4).

This module contains no model-fitting code whatsoever — it never imports or
calls any logistic-regression implementation. It exists so the degeneracy
policy boundary (single-class / minority<2 / minority>=2) can be exercised and
tested against real fold data without ever fitting `V1_LOGIT`, which is out of
scope for this implementation task.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

FIT_OK = "FIT_OK"
MODEL_NOT_FIT_SINGLE_CLASS = "MODEL_NOT_FIT_SINGLE_CLASS"

TUNED_INNER_LOOCV = "TUNED_INNER_LOOCV"
TUNING_SKIPPED_MINORITY_COUNT_LT_2 = "TUNING_SKIPPED_MINORITY_COUNT_LT_2"
TUNING_NOT_APPLICABLE = "TUNING_NOT_APPLICABLE"

FALLBACK_C = 0.01
C_GRID = (0.01, 0.1, 1.0, 10.0)


@dataclass(frozen=True)
class LogisticFitDecision:
    fit_status: str
    tuning_status: str
    fallback_C: float | None
    n_class_0: int
    n_class_1: int


def decide_logistic_fit(training_y: Sequence[int]) -> LogisticFitDecision:
    """Pure decision function — no fitting is ever performed here."""
    if not training_y:
        raise ValueError("decide_logistic_fit called with an empty training set")
    n1 = sum(training_y)
    n0 = len(training_y) - n1

    if n0 == 0 or n1 == 0:
        return LogisticFitDecision(MODEL_NOT_FIT_SINGLE_CLASS, TUNING_NOT_APPLICABLE, None, n0, n1)

    minority = min(n0, n1)
    if minority < 2:
        return LogisticFitDecision(FIT_OK, TUNING_SKIPPED_MINORITY_COUNT_LT_2, FALLBACK_C, n0, n1)

    return LogisticFitDecision(FIT_OK, TUNED_INNER_LOOCV, None, n0, n1)

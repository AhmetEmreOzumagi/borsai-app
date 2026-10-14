"""Part G — preregistered baselines only. NO Ridge, NO Logistic fitting here.

Every baseline is computed EXCLUSIVELY from the training fold's TARGET
distribution. None of them consume any feature at all, so none of them can
leak through a feature — the only input surface is `training_targets`, a list
of the training tickers' TargetRecord objects for this fold/horizon. The
predict_* functions have no parameter through which a test-ticker target could
even be passed, which is the structural (not merely conventional) enforcement
required by the task for `no_test_target_read_before_prediction`.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Sequence

from .target_extraction import TargetRecord

V1_BASE_ZERO = "V1_BASE_ZERO"
V1_BASE_MEDIAN = "V1_BASE_MEDIAN"
V1_BASE_MEAN = "V1_BASE_MEAN"
V1_BASE_MAJORITY = "V1_BASE_MAJORITY"
V1_BASE_RATE = "V1_BASE_RATE"

REGRESSION_BASELINES = (V1_BASE_ZERO, V1_BASE_MEDIAN, V1_BASE_MEAN)
CLASSIFICATION_BASELINES = (V1_BASE_MAJORITY, V1_BASE_RATE)


@dataclass(frozen=True)
class RegressionPrediction:
    model_version: str
    point_prediction: float


@dataclass(frozen=True)
class ClassificationPrediction:
    model_version: str
    direction_prediction: int  # 0 = AT_OR_BELOW_IPO, 1 = ABOVE_IPO
    prob_above_ipo: float


def _r_h_values(training_targets: Sequence[TargetRecord]) -> list[float]:
    return [float(t.R_h) for t in training_targets]


def _y_h_values(training_targets: Sequence[TargetRecord]) -> list[int]:
    return [int(t.Y_h) for t in training_targets]


def predict_v1_base_zero(training_targets: Sequence[TargetRecord]) -> RegressionPrediction:
    if not training_targets:
        raise ValueError("V1_BASE_ZERO requires a non-empty training fold")
    return RegressionPrediction(model_version=V1_BASE_ZERO, point_prediction=0.0)


def predict_v1_base_median(training_targets: Sequence[TargetRecord]) -> RegressionPrediction:
    values = _r_h_values(training_targets)
    if not values:
        raise ValueError("V1_BASE_MEDIAN requires a non-empty training fold")
    return RegressionPrediction(model_version=V1_BASE_MEDIAN, point_prediction=statistics.median(values))


def predict_v1_base_mean(training_targets: Sequence[TargetRecord]) -> RegressionPrediction:
    values = _r_h_values(training_targets)
    if not values:
        raise ValueError("V1_BASE_MEAN requires a non-empty training fold")
    return RegressionPrediction(model_version=V1_BASE_MEAN, point_prediction=statistics.mean(values))


def predict_v1_base_majority(training_targets: Sequence[TargetRecord]) -> ClassificationPrediction:
    """Majority-class baseline. Equal-count tie -> deterministic 0 (AT_OR_BELOW_IPO), fixed in advance."""
    values = _y_h_values(training_targets)
    if not values:
        raise ValueError("V1_BASE_MAJORITY requires a non-empty training fold")
    count_1 = sum(values)
    count_0 = len(values) - count_1
    majority = 1 if count_1 > count_0 else 0  # equal counts (count_1 == count_0) -> 0, by this comparison
    prob = 1.0 if majority == 1 else 0.0
    return ClassificationPrediction(model_version=V1_BASE_MAJORITY, direction_prediction=majority, prob_above_ipo=prob)


def predict_v1_base_rate(training_targets: Sequence[TargetRecord]) -> ClassificationPrediction:
    values = _y_h_values(training_targets)
    if not values:
        raise ValueError("V1_BASE_RATE requires a non-empty training fold")
    rate = sum(values) / len(values)
    direction = 1 if rate > 0.5 else 0
    return ClassificationPrediction(model_version=V1_BASE_RATE, direction_prediction=direction, prob_above_ipo=rate)


REGRESSION_PREDICTORS = {
    V1_BASE_ZERO: predict_v1_base_zero,
    V1_BASE_MEDIAN: predict_v1_base_median,
    V1_BASE_MEAN: predict_v1_base_mean,
}
CLASSIFICATION_PREDICTORS = {
    V1_BASE_MAJORITY: predict_v1_base_majority,
    V1_BASE_RATE: predict_v1_base_rate,
}

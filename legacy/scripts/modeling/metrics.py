"""Part H — baseline evaluation metrics, computed only in Phase 2 (post-unlock).

Regression: MAE / median AE / RMSE on R_h (return space, the model's native
output); MAPE / median APE computed on PRICE LEVEL (predicted vs actual close)
per V1.1 §8.1, never on returns (returns pass through zero).

Classification: above-IPO accuracy, Brier score, log loss (probability
clipped to [0.01, 0.99]).

Every result below MIN_OOS_FOR_CONCLUSIVE (20) is labelled
NOT_STATISTICALLY_CONCLUSIVE. No headline "beats baseline" claim is computed
anywhere in this module — it reports numbers, not verdicts.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from decimal import Decimal

MIN_OOS_FOR_CONCLUSIVE = 20
PROB_CLIP = (0.01, 0.99)


@dataclass
class RegressionScoredPoint:
    ticker: str
    predicted_r_h: float
    actual_r_h: float
    ipo_price: Decimal
    actual_close: Decimal


@dataclass
class ClassificationScoredPoint:
    ticker: str
    predicted_direction: int
    predicted_prob_above_ipo: float
    actual_y_h: int


@dataclass
class RegressionMetrics:
    n_oos: int
    mae: float
    median_ae: float
    rmse: float
    mape_price_level: float
    median_ape_price_level: float
    interval_coverage: str = "NOT_APPLICABLE_V1_1"
    conclusiveness: str = field(init=False)

    def __post_init__(self):
        self.conclusiveness = "NOT_STATISTICALLY_CONCLUSIVE" if self.n_oos < MIN_OOS_FOR_CONCLUSIVE else "CONCLUSIVE_ELIGIBLE"


@dataclass
class ClassificationMetrics:
    n_oos: int
    above_ipo_accuracy: float
    brier_score: float
    log_loss: float
    conclusiveness: str = field(init=False)

    def __post_init__(self):
        self.conclusiveness = "NOT_STATISTICALLY_CONCLUSIVE" if self.n_oos < MIN_OOS_FOR_CONCLUSIVE else "CONCLUSIVE_ELIGIBLE"


def compute_regression_metrics(points: list[RegressionScoredPoint]) -> RegressionMetrics | None:
    if not points:
        return None
    abs_errors_return = [abs(p.predicted_r_h - p.actual_r_h) for p in points]
    sq_errors_return = [(p.predicted_r_h - p.actual_r_h) ** 2 for p in points]

    price_apes = []
    for p in points:
        predicted_close = float(p.ipo_price) * (1.0 + p.predicted_r_h)
        actual_close = float(p.actual_close)
        price_apes.append(abs(predicted_close - actual_close) / actual_close * 100.0)

    return RegressionMetrics(
        n_oos=len(points),
        mae=statistics.mean(abs_errors_return),
        median_ae=statistics.median(abs_errors_return),
        rmse=math.sqrt(statistics.mean(sq_errors_return)),
        mape_price_level=statistics.mean(price_apes),
        median_ape_price_level=statistics.median(price_apes),
    )


def compute_classification_metrics(points: list[ClassificationScoredPoint]) -> ClassificationMetrics | None:
    if not points:
        return None
    correct = sum(1 for p in points if p.predicted_direction == p.actual_y_h)
    accuracy = correct / len(points)

    brier_terms = []
    log_loss_terms = []
    lo, hi = PROB_CLIP
    for p in points:
        prob = min(max(p.predicted_prob_above_ipo, lo), hi)
        y = p.actual_y_h
        brier_terms.append((prob - y) ** 2)
        log_loss_terms.append(-(y * math.log(prob) + (1 - y) * math.log(1 - prob)))

    return ClassificationMetrics(
        n_oos=len(points),
        above_ipo_accuracy=accuracy,
        brier_score=statistics.mean(brier_terms),
        log_loss=statistics.mean(log_loss_terms),
    )

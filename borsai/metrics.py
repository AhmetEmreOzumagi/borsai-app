"""Skorlama tanımları ve eşleşik fark aralığı. Yalnız stdlib.

CLAUDE.md kural 6: tanımlar ilk skorlamadan önce kodda yazılıdır. Buradaki
tanımlar legacy `scripts/modeling/metrics.py` ile birebir aynıdır (aynı
statistics çağrıları, aynı [0.01, 0.99] raporlama kırpması); böylece H99
benchmark sayıları yeniden üretilir.

Getiri (R_h uzayı): MAE, medyan AE, RMSE. Fiyat düzeyi: MAPE ve medyan APE,
tahmin kapanışı = arz fiyatı × (1 + tahmin), yüzde olarak.
Yön/olasılık: isabet (p > 0.5 ise UP), Brier ve log kaybı; olasılık yalnız
bu iki metrikte [0.01, 0.99]'a kırpılır.

Eşleşik fark: fark = model − kural (negatif = model daha iyi). %95 aralık
AUDIT §1.2-c yöntemiyle: ilk işlem ayına (YYYY-MM) göre blok bootstrap, ayları
iadeli çek, çekilen ayların bütün farklarını birleştir, ortalamasını al;
4000 tekrar; sıralı dağılımın 100. ve 3899. elemanı. "Geçiyor" yalnız aralık
0'ı dışlıyorsa denir.
"""
from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Optional, Sequence

PROB_CLIP = (0.01, 0.99)
WINDOWS: tuple[tuple[str, Optional[int]], ...] = (("LAST_5", 5), ("LAST_10", 10), ("LAST_20", 20), ("ALL", None))
BOOTSTRAP_REPS = 4000
BOOTSTRAP_SEED = 20260921
BOOTSTRAP_LO_INDEX = 100
BOOTSTRAP_HI_INDEX = 3899


@dataclass(frozen=True)
class RegressionPoint:
    ticker: str
    prediction_date: str
    predicted: float
    actual: float
    ipo_price: Decimal
    actual_close: Decimal


@dataclass(frozen=True)
class ClassificationPoint:
    ticker: str
    prediction_date: str
    probability: float
    direction: int
    actual: int


def clip_probability(p: float) -> float:
    lo, hi = PROB_CLIP
    return min(max(p, lo), hi)


def price_ape(predicted: float, ipo_price: Decimal, actual_close: Decimal) -> float:
    predicted_close = float(ipo_price) * (1.0 + predicted)
    close = float(actual_close)
    return abs(predicted_close - close) / close * 100.0


def regression_metrics(points: Sequence[RegressionPoint]) -> Optional[dict]:
    if not points:
        return None
    abs_err = [abs(p.predicted - p.actual) for p in points]
    sq_err = [(p.predicted - p.actual) ** 2 for p in points]
    apes = [price_ape(p.predicted, p.ipo_price, p.actual_close) for p in points]
    return {
        "n": len(points),
        "mae": statistics.mean(abs_err),
        "median_ae": statistics.median(abs_err),
        "rmse": math.sqrt(statistics.mean(sq_err)),
        "mape_price_level_pct": statistics.mean(apes),
        "median_ape_price_level_pct": statistics.median(apes),
    }


def brier_term(p: float, y: int) -> float:
    return (clip_probability(p) - y) ** 2


def log_loss_term(p: float, y: int) -> float:
    q = clip_probability(p)
    return -(y * math.log(q) + (1 - y) * math.log(1 - q))


def classification_metrics(points: Sequence[ClassificationPoint]) -> Optional[dict]:
    if not points:
        return None
    return {
        "n": len(points),
        "accuracy": sum(1 for p in points if p.direction == p.actual) / len(points),
        "brier": statistics.mean(brier_term(p.probability, p.actual) for p in points),
        "log_loss": statistics.mean(log_loss_term(p.probability, p.actual) for p in points),
    }


def windowed(points: Sequence, fn) -> dict[str, Optional[dict]]:
    """LAST_5/10/20/ALL; sıra (prediction_date, ticker)."""
    ordered = sorted(points, key=lambda p: (p.prediction_date, p.ticker))
    return {name: fn(ordered if n is None else ordered[-n:]) for name, n in WINDOWS}


def block_bootstrap_ci(
    values: Sequence[float], blocks: Sequence[str], *, rng: random.Random, reps: int = BOOTSTRAP_REPS
) -> tuple[float, float]:
    """AUDIT §1.2-c: bloklar ilk görünüş sırasıyla; `rng.choices` ile iadeli çekim."""
    if len(values) != len(blocks) or not values:
        raise ValueError("block_bootstrap_ci: boş ya da uzunluk uyuşmazlığı")
    by_block: dict[str, list[float]] = {}
    for b, v in zip(blocks, values):
        by_block.setdefault(b, []).append(v)
    keys = list(by_block)
    out: list[float] = []
    for _ in range(reps):
        sample: list[float] = []
        for k in rng.choices(keys, k=len(keys)):
            sample += by_block[k]
        out.append(sum(sample) / len(sample))
    out.sort()
    lo_i = BOOTSTRAP_LO_INDEX * reps // BOOTSTRAP_REPS
    hi_i = BOOTSTRAP_HI_INDEX * reps // BOOTSTRAP_REPS
    return out[lo_i], out[hi_i]


def paired_difference(
    diffs: Sequence[float], months: Sequence[str], *, seed: int = BOOTSTRAP_SEED, reps: int = BOOTSTRAP_REPS
) -> dict:
    """fark = model − kural. Her karşılaştırma kendi `random.Random(seed)`'iyle
    çalışır; sonuç çağrı sırasına bağlı değildir."""
    lo, hi = block_bootstrap_ci(diffs, months, rng=random.Random(seed), reps=reps)
    if lo > 0:
        verdict = "KURAL_DAHA_IYI"
    elif hi < 0:
        verdict = "MODEL_DAHA_IYI"
    else:
        verdict = "AYIRT_EDILEMIYOR"
    return {
        "n": len(diffs),
        "n_months": len(set(months)),
        "mean": sum(diffs) / len(diffs),
        "ci95": [lo, hi],
        "model_better_n": sum(1 for d in diffs if d < 0),
        "rule_better_n": sum(1 for d in diffs if d > 0),
        "tie_n": sum(1 for d in diffs if d == 0),
        "verdict": verdict,
        "bootstrap": {"method": "MONTHLY_BLOCK_BY_FIRST_TRADING_MONTH", "reps": reps, "seed": seed},
    }


def mean_or_none(values: Iterable[float]) -> Optional[float]:
    values = list(values)
    return statistics.mean(values) if values else None

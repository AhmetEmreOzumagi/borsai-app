"""Ufuklar ve fiziksel getiri sınırı. Yalnız stdlib.

D_h: ilk işlem gününden itibaren h'inci resmi BIST Pay Piyasası seansı (docs/DATA.md).
R_h = kapanış(D_h) / arz fiyatı − 1.

Fiziksel sınır: günlük fiyat marjı ±%10 olduğu için R_h ∈ [0.9^h − 1, 1.1^h − 1].
Sınırlar Decimal ile kesin hesaplanır, sonra bir kez binary64'e çevrilir.
Not: üst limit fiyat adımına yuvarlandığından ve 4 arzda D1 referansı arz
fiyatından bir adım farklı olduğundan gerçekleşen R_D1 0.1'i çok az aşabilir
(LILAK 0.10029, BORLS 0.10004; docs/DATA.md "Tavan"). Sınır tahmin çıktısı
içindir; skorlama ham gerçekleşen değeri kullanır.
"""
from __future__ import annotations

from decimal import Decimal

HORIZONS: tuple[str, ...] = ("D1", "D3", "D5", "D10")
HORIZON_DAYS: dict[str, int] = {"D1": 1, "D3": 3, "D5": 5, "D10": 10}

_UP = Decimal("1.1")
_DOWN = Decimal("0.9")


def physical_return_bounds(horizon: str) -> tuple[float, float]:
    """(alt, üst) = (0.9^h − 1, 1.1^h − 1), kesin Decimal'den binary64'e."""
    h = HORIZON_DAYS[horizon]
    return float(_DOWN ** h - 1), float(_UP ** h - 1)

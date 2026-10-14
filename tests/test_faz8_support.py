"""Faz 8 test yardımcıları (test içermez): sentetik kırılma tabloları ve tavan yolu birimleri. Görev kuralı yeni test dosyalarını
`tests/test_faz8_*.py` adıyla sınırladığı için yardımcı modül bu adı taşır (Faz 7C'nin `faz7c_support.py` kalıbı).

Sentetik veri gerçek veriden hiçbir sonuç taşımaz: fiyatlar `predict_path` limit aritmetiğiyle üretilir, etiket olasılığı yalnız
b_floor'a bağlıdır (sinyal sentetiktir; model davranışını sınamak içindir)."""
from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from borsai import post_break as pbk
from borsai import predict_path as pth


def business_days(start: date, n: int) -> list[str]:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _inside(lower: Decimal, upper: Decimal, rng: random.Random, *, min_ticks: int = 5) -> Decimal:
    """Alt limitin en az `min_ticks` adım üstünde, üst limitin altında bir fiyat (adım alt limit seviyesinden)."""
    step = pth.tick(lower)
    k_max = int((upper - lower) / step) - 1
    k = rng.randint(min(min_ticks, k_max), k_max)
    return lower + step * k


def make_path(P: Decimal, L: int, b_floor: Optional[int], after_floor: list[int], rng: random.Random) -> tuple[list[Decimal], dict]:
    """(kapanış D1..D10, D_b alanları). L tavan, b = L + 1 günü taban (b_floor = 1) ya da taban üstü; sonraki günler `after_floor`."""
    closes: list[Decimal] = []
    base = pth.snap(P)
    day = None
    for h in range(1, 11):
        ref = base if h == 1 else closes[-1]
        up, lo = pth.upper_limit(ref), pth.lower_limit(ref)
        if h <= L:
            c = up
        elif h == L + 1:
            c = lo if b_floor else _inside(lo, up, rng)
            day = {"ref": ref, "up": up, "lo": lo, "close": c}
        else:
            c = lo if after_floor[h - L - 2] else _inside(lo, up, rng, min_ticks=1)
        closes.append(c)
    return closes, day


def make_unit(ticker: str, d1: date, *, L: int, b_floor: int = 0, after_floor: tuple[int, ...] = (0,) * 9, P: str = "10.00",
              shares: str = "20000000", turnover: float = 1.0, seed: int = 0, half_day: int = 0,
              high_at_lower: bool = False) -> tuple[pbk.BreakUnit, Optional[pbk.BreakLabels], pth.PathUnit]:
    rng = random.Random(seed)
    price = Decimal(P)
    dates = business_days(d1, 10)
    closes, day = make_path(price, L, b_floor if L < 10 else None, list(after_floor) + [0] * 9, rng)
    b = None if L == 10 else L + 1
    status = pbk.UNIT_NO_BREAK if b is None else (pbk.UNIT_B10 if b == 10 else pbk.UNIT_BREAK)
    block = None
    if b is not None:
        vol = int(Decimal(shares) * Decimal(str(turnover)))
        high = day["lo"] if high_at_lower else max(day["close"], day["lo"] + pth.tick(day["lo"]))
        block = {"session_h": b, "session_date": dates[b - 1], "half_day": half_day, "halt_flag": 0,
                 "fields_raw": {"open": str(day["close"]), "high": str(high), "low": str(min(day["close"], day["lo"])),
                                "close": str(day["close"]), "volume": str(max(vol, 1)), "trade_count": "1234",
                                "reference_price": str(day["ref"]), "upper_limit": str(day["up"]), "lower_limit": str(day["lo"])}}
    unit = pbk.BreakUnit(ticker, dates[0], P, shares, L, b, status,
                         tuple(str(c) for c in (closes[:b] if b is not None and b <= 9 else closes)), tuple(dates), block)
    labels = None
    if status == pbk.UNIT_BREAK:
        def floor_at(h: int) -> int:
            return int(closes[h - 1] == pth.lower_limit(closes[h - 2]))
        y1 = floor_at(b + 1)
        y2 = y2_date = None
        if b <= 8:
            y2_date = dates[b + 1]
            y2 = 0 if y1 == 0 else floor_at(b + 2)
        labels = pbk.BreakLabels(y1, dates[b], y2, y2_date)
    return unit, labels, pth.PathUnit(ticker, dates[0], L, price, tuple(closes), tuple(dates))


def synthetic_table(n: int = 64, seed: int = 20261001, start: date = date(2023, 6, 5), gap_days: int = 17,
                    signal: tuple[float, float] = (0.6, 0.1)) -> tuple[pbk.BreakTable, list[pth.PathUnit]]:
    """n arz; listeleme aralığı `gap_days` takvim günü (2023'ten 2026'ya). L dağılımı H99'unkine benzer (0 … 10); b_floor ≈ %45;
    ertesi gün taban olasılığı b_floor = 1 için signal[0], 0 için signal[1]."""
    rng = random.Random(seed)
    Ls = [0, 0, 1, 2, 3, 3, 4, 4, 5, 6, 7, 8, 10, 9]
    prices = ["10.00", "12.50", "24.00", "33.30", "8.88", "51.00", "17.36"]
    units, labels, path = [], {}, []
    for i in range(n):
        L = Ls[i % len(Ls)] if i % 5 else rng.choice(Ls)
        bf = int(rng.random() < 0.45)
        after = tuple(int(rng.random() < (signal[0] if bf else signal[1])) for _ in range(9))
        turnover = round(rng.lognormvariate(0.0, 0.9), 6)
        u, lbl, pu = make_unit(f"SY{i:03d}", start + timedelta(days=gap_days * i), L=L, b_floor=bf, after_floor=after,
                               P=prices[i % len(prices)], shares=str(rng.randint(5, 60) * 1_000_000), turnover=turnover, seed=seed + i,
                               half_day=int(i == 7), high_at_lower=bool(bf and i % 9 == 0))
        units.append(u)
        path.append(pu)
        if lbl is not None:
            labels[u.ticker] = lbl
    return pbk.BreakTable(units, labels, {"sessions_file": "synthetic", "sessions_file_sha256": None}), path


def table_of(items: list[tuple[pbk.BreakUnit, Optional[pbk.BreakLabels], pth.PathUnit]]) -> tuple[pbk.BreakTable, list[pth.PathUnit]]:
    units = sorted((u for u, _, _ in items), key=lambda u: (u.first_trading_date, u.ticker))
    labels = {u.ticker: lbl for u, lbl, _ in items if lbl is not None}
    return pbk.BreakTable(units, labels, {}), [p for _, _, p in items]

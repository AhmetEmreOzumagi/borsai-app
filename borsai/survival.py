"""Tavan serisi (ceiling streak) için ortak tanımlar. Yalnız stdlib.

SPEC_CEILING_V0 §2, §3, §8, §10 ve SPEC_SCORING §7:
- Kişi-dönem (PP) satırı: arz i, gün d ∈ 1..10 için ancak d − 1 ≤ L_i ise vardır;
  event = 1[L_i == d − 1] (seri d. gün bozuldu). Walk-forward'da (i, d) satırı ancak
  seans tarihi < kesim ise girer; ilk geçmeyen günde durulur (sağdan sansür).
- Gün grupları: g1 = {1}, g2 = {2, 3}, g3 = {4..10}.
- S_k = Π_{d ≤ k} (1 − h_d); P(L = l); P(Dk'de tavan kapanışı) = S_k + (1 − S_k)·r_{b(k)},
  r = (a + 0.5)/(n + 1), b = a (k ∈ 2..4) ya da b (k ∈ 5..10).
- Kaplan–Meier kuralları (genişleyen, son-10) ve RPS.

Bu modül hem numpy fit'inde (borsai/hazard.py) hem stdlib tahminde
(borsai/predict_hazard.py) kullanılır; bu yüzden yalnız stdlib import eder.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

DAYS = 10
DAY_GROUPS: dict[str, tuple[int, ...]] = {"g1": (1,), "g2": (2, 3), "g3": (4, 5, 6, 7, 8, 9, 10)}
GROUP_NAMES: tuple[str, ...] = ("g1", "g2", "g3")
GROUP_OF_DAY: dict[int, int] = {d: i for i, g in enumerate(GROUP_NAMES) for d in DAY_GROUPS[g]}
RECLOSE_GROUPS: dict[str, tuple[int, ...]] = {"a": (2, 3, 4), "b": (5, 6, 7, 8, 9, 10)}
RECLOSE_GROUP_OF_DAY: dict[int, str] = {k: g for g, ks in RECLOSE_GROUPS.items() for k in ks}
LAST_N = 10


@dataclass(frozen=True)
class Unit:
    """Bir arzın tavan etiketleri ve seans tarihleri (fiyat yok)."""

    ticker: str
    first_trading_date: str
    streak: int                       # L ∈ 0..10
    session_dates: tuple[str, ...]    # D1..D10
    ceiling_close: tuple[int, ...]    # D1..D10, 0/1


@dataclass(frozen=True)
class PPRow:
    ticker: str
    first_trading_date: str
    day: int
    group: int  # 0, 1, 2
    event: int  # 1: seri bu gün bozuldu


def unit_of(row) -> Unit:
    """borsai.data.IPORow -> Unit."""
    return Unit(row.ticker, row.first_trading_date, row.ceiling_streak, tuple(row.session_dates), tuple(row.ceiling_close))


def pp_rows(unit: Unit, cutoff: Optional[str] = None) -> list[PPRow]:
    out: list[PPRow] = []
    for d in range(1, DAYS + 1):
        if d - 1 > unit.streak:
            break
        if cutoff is not None and unit.session_dates[d - 1] >= cutoff:
            break
        out.append(PPRow(unit.ticker, unit.first_trading_date, d, GROUP_OF_DAY[d], int(unit.streak == d - 1)))
    return out


def pp_table(units: Sequence[Unit], cutoff: Optional[str] = None) -> list[PPRow]:
    return [r for u in units for r in pp_rows(u, cutoff)]


def group_counts(rows: Sequence[PPRow]) -> tuple[list[int], list[int]]:
    """(olay_g, risk_g), g = g1, g2, g3."""
    events, risk = [0, 0, 0], [0, 0, 0]
    for r in rows:
        risk[r.group] += 1
        events[r.group] += r.event
    return events, risk


def closed_form_gamma(events: int, risk: int) -> float:
    """λ = INF: γ_g = logit((olay_g + 0.5)/(risk_g + 1)) = ln((olay_g + 0.5)/(risk_g − olay_g + 0.5))."""
    return math.log((events + 0.5) / (risk - events + 0.5))


def reclose_counts(units: Sequence[Unit], cutoff: Optional[str] = None) -> dict[str, float]:
    """Seri bozulduktan sonra yeniden tavan oranı (SPEC_CEILING_V0 §8). n: L < k olan
    arz-günleri (seans tarihi < kesim), a: bunlardan ceiling_close_Dk = 1 olanlar."""
    n = {"a": 0, "b": 0}
    a = {"a": 0, "b": 0}
    for u in units:
        for k in range(2, DAYS + 1):
            if u.streak < k and (cutoff is None or u.session_dates[k - 1] < cutoff):
                g = RECLOSE_GROUP_OF_DAY[k]
                n[g] += 1
                a[g] += u.ceiling_close[k - 1]
    return {"n_a": n["a"], "a_a": a["a"], "r_a": (a["a"] + 0.5) / (n["a"] + 1),
            "n_b": n["b"], "a_b": a["b"], "r_b": (a["b"] + 0.5) / (n["b"] + 1)}


def survival(hazards: Sequence[float]) -> list[float]:
    """S_k = Π_{d ≤ k} (1 − h_d), soldan sağa çarpım."""
    out: list[float] = []
    s = 1.0
    for h in hazards:
        s = s * (1.0 - h)
        out.append(s)
    return out


def p_streak(S: Sequence[float]) -> list[float]:
    """P(L = l), l = 0..10."""
    return [1.0 - S[0]] + [S[l - 1] - S[l] for l in range(1, DAYS)] + [S[DAYS - 1]]


def p_close(S: Sequence[float], r_a: float, r_b: float) -> list[float]:
    """P(Dk'de tavan kapanışı): k = 1 -> S_1; k ≥ 2 -> S_k + (1 − S_k)·r_{b(k)}."""
    out = [S[0]]
    for k in range(2, DAYS + 1):
        r = r_a if RECLOSE_GROUP_OF_DAY[k] == "a" else r_b
        out.append(S[k - 1] + (1.0 - S[k - 1]) * r)
    return out


def km_hazards(rows: Sequence[PPRow], last_n: Optional[int] = None) -> list[float]:
    """Kaplan–Meier gün hazard'ları. `last_n`: her d için yalnız (j, d) satırı olan son
    N arz, (first_trading_date, ticker) sırasıyla. risk_d = 0 ise önceki günün hazard'ı."""
    out: list[float] = []
    for d in range(1, DAYS + 1):
        day_rows = sorted((r for r in rows if r.day == d), key=lambda r: (r.first_trading_date, r.ticker))
        if last_n is not None:
            day_rows = day_rows[-last_n:]
        if day_rows:
            out.append(sum(r.event for r in day_rows) / len(day_rows))
        elif out:
            out.append(out[-1])
        else:
            raise ValueError("Kaplan–Meier: 1. günde risk altında arz yok")
    return out


def sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def rps(S: Sequence[float], streak: int) -> float:
    """RPS = (1/10) Σ_k (S_k − 1[L ≥ k])² (SPEC_CEILING_V0 §1-7, SPEC_SCORING §7)."""
    return sum((S[k - 1] - (1.0 if streak >= k else 0.0)) ** 2 for k in range(1, DAYS + 1)) / DAYS

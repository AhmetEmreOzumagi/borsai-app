"""Part A — deterministic target extraction (R_h, Y_h) for D1/D3/D5/D10.

Source of truth: V1.1 preregistration §4, machine spec `targets` block.

- official_close and ipo_price are parsed as exact Decimal from their source
  CSV strings — never through a binary float.
- Y_h uses TIE_IS_ZERO_AT_OR_BELOW_IPO with exact-decimal comparison; no
  round(float*100), no epsilon.
- A target is usable only if row_status == OFFICIAL_VERIFIED and
  conflict_status == NO_CONFLICT; otherwise TARGET_NOT_AVAILABLE with the
  underlying reason recorded for audit.
- Target imputation of any kind is not implemented anywhere in this module.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
from decimal import Decimal
from pathlib import Path
from typing import Optional

from . import common

OFFICIAL_VERIFIED = "OFFICIAL_VERIFIED"
NO_CONFLICT = "NO_CONFLICT"
TARGET_NOT_AVAILABLE = "TARGET_NOT_AVAILABLE"
TARGET_AVAILABLE = "TARGET_AVAILABLE"

TARGET_FIELDS = [
    "ticker", "first_trading_date", "horizon", "target_session_date",
    "target_status", "underlying_row_status", "underlying_conflict_status",
    "ipo_price_exact", "official_close_exact", "R_h", "Y_h",
    "thb_source_url", "thb_source_sha256",
]


class TickSizeViolationError(ValueError):
    """Raised when an official price does not scale to an integral kurus value."""


def assert_integral_kurus(value: Decimal, label: str) -> int:
    scaled = value * 100
    as_int = int(scaled)
    if Decimal(as_int) != scaled:
        raise TickSizeViolationError(f"{label}={value} does not scale to an integral kurus value (tick-size violation)")
    return as_int


@dataclass(frozen=True)
class TargetRecord:
    ticker: str
    first_trading_date: str
    horizon: str
    target_session_date: str
    target_status: str
    underlying_row_status: str
    underlying_conflict_status: str
    ipo_price_exact: str
    official_close_exact: Optional[str]
    R_h: Optional[str]
    Y_h: Optional[int]
    thb_source_url: Optional[str]
    thb_source_sha256: Optional[str]

    def as_csv_row(self) -> dict:
        return asdict(self)


def _index_full20_by_ticker_day(rows: list[dict]) -> dict[tuple[str, int], dict]:
    index: dict[tuple[str, int], dict] = {}
    for row in rows:
        index[(row["ticker"], int(row["trade_day_number"]))] = row
    return index


def extract_targets() -> list[TargetRecord]:
    universe = common.load_universe()
    full20_rows = common.load_full20_snapshot_rows()
    full20_index = _index_full20_by_ticker_day(full20_rows)

    records: list[TargetRecord] = []
    for ticker in sorted(universe):
        master = universe[ticker]
        assert_integral_kurus(master.ipo_price, f"{ticker}.ipo_price")
        for horizon in common.HORIZONS:
            day = common.HORIZON_DAY[horizon]
            row = full20_index.get((ticker, day))
            if row is None:
                raise KeyError(f"FULL20 snapshot missing expected row for {ticker} D{day}")

            row_status = row["row_status"]
            conflict_status = row["conflict_status"]
            usable = row_status == OFFICIAL_VERIFIED and conflict_status == NO_CONFLICT

            if not usable:
                records.append(TargetRecord(
                    ticker=ticker, first_trading_date=master.first_trading_date, horizon=horizon,
                    target_session_date=row["trade_date"], target_status=TARGET_NOT_AVAILABLE,
                    underlying_row_status=row_status, underlying_conflict_status=conflict_status,
                    ipo_price_exact=str(master.ipo_price), official_close_exact=None,
                    R_h=None, Y_h=None, thb_source_url=None, thb_source_sha256=None,
                ))
                continue

            close = common.parse_exact_decimal(row["official_close"])
            if close is None:
                raise ValueError(f"{ticker} D{day}: row_status=OFFICIAL_VERIFIED but official_close is unparseable: {row['official_close']!r}")
            assert_integral_kurus(close, f"{ticker}.D{day}.official_close")

            r_h = (close / master.ipo_price) - Decimal(1)
            y_h = 1 if close > master.ipo_price else 0  # exact Decimal comparison; tie -> 0

            records.append(TargetRecord(
                ticker=ticker, first_trading_date=master.first_trading_date, horizon=horizon,
                target_session_date=row["trade_date"], target_status=TARGET_AVAILABLE,
                underlying_row_status=row_status, underlying_conflict_status=conflict_status,
                ipo_price_exact=str(master.ipo_price), official_close_exact=str(close),
                R_h=str(r_h), Y_h=y_h,
                thb_source_url=row.get("thb_source_url") or None,
                thb_source_sha256=row.get("thb_source_sha256") or None,
            ))
    return records


def write_target_csv(records: list[TargetRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=TARGET_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(record.as_csv_row())


def summarize_availability(records: list[TargetRecord]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {h: {"available": 0, "not_available": 0} for h in common.HORIZONS}
    for record in records:
        key = "available" if record.target_status == TARGET_AVAILABLE else "not_available"
        summary[record.horizon][key] += 1
    return summary

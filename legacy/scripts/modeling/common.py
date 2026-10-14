"""Shared paths, loaders, and exact-decimal helpers for the V1.1 baseline harness.

Every function here is read-only with respect to protected inputs: it never
writes to the FULL20 snapshot, the canonical pre-trade master, the FROZEN
registry, or config/model_v1_spec.json / config/model_v1_1_spec.json.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]

FULL20_RUN_ID = "20260814_101901"
FULL20_SNAPSHOT_DIR = ROOT / "artifacts" / "ohlcv" / "full20" / "snapshots" / FULL20_RUN_ID
FULL20_SNAPSHOT_CSV = FULL20_SNAPSHOT_DIR / "first10_ohlcv_20_snapshot.csv"

MASTER_PATH = ROOT / "artifacts" / "ipo_master" / "consolidated" / "ipo_master_20_pretrade_canonical.csv"
CONSOLIDATED_PROVENANCE_PATH = ROOT / "artifacts" / "ipo_master" / "consolidated" / "ipo_master_20_provenance_canonical.csv"
BATCH_PROVENANCE_PATHS = [
    ROOT / "artifacts" / "ipo_master" / "batches" / "batch_01_provenance.csv",
    ROOT / "artifacts" / "ipo_master" / "batches" / "batch_02_provenance.csv",
    ROOT / "artifacts" / "ipo_master" / "batches" / "batch_03_provenance.csv",
    ROOT / "artifacts" / "ipo_master" / "batches" / "batch_04_provenance.csv",
]

V1_SPEC_PATH = ROOT / "config" / "model_v1_spec.json"
V1_1_SPEC_PATH = ROOT / "config" / "model_v1_1_spec.json"
EXPECTED_V1_1_SPEC_SHA256 = "3c7c4336903924fa6f898413804564ba146d8a9ce7016e556d8a7bd82ba0be7c"

HORIZON_DAY = {"D1": 1, "D3": 3, "D5": 5, "D10": 10}
HORIZONS = ("D1", "D3", "D5", "D10")

DATA_NOT_FOUND = "DATA_NOT_FOUND"


class SpecHashMismatchError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_v1_1_spec() -> dict:
    """Load config/model_v1_1_spec.json and hard-verify its hash before returning it.

    Per task instruction: the expected hash must be recomputed independently at
    task start, not blindly trusted. If it does not match, the caller must stop.
    """
    actual = sha256_file(V1_1_SPEC_PATH)
    if actual != EXPECTED_V1_1_SPEC_SHA256:
        raise SpecHashMismatchError(
            f"config/model_v1_1_spec.json sha256 mismatch: expected {EXPECTED_V1_1_SPEC_SHA256}, got {actual}"
        )
    with V1_1_SPEC_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_full20_snapshot_rows() -> list[dict]:
    return read_csv_rows(FULL20_SNAPSHOT_CSV)


def load_master_rows() -> list[dict]:
    return read_csv_rows(MASTER_PATH)


def load_consolidated_provenance_rows() -> list[dict]:
    return read_csv_rows(CONSOLIDATED_PROVENANCE_PATH)


def load_batch_provenance_rows() -> list[dict]:
    rows: list[dict] = []
    for path in BATCH_PROVENANCE_PATHS:
        rows.extend(read_csv_rows(path))
    return rows


def parse_exact_decimal(raw: Optional[str]) -> Optional[Decimal]:
    """Parse a CSV cell into an exact Decimal, never through a binary float.

    Returns None for empty strings, the DATA_NOT_FOUND sentinel, or any value
    that is not a valid decimal literal. Never raises on missing data — missing
    data is a normal, expected outcome that callers must handle explicitly.
    """
    if raw is None:
        return None
    text = raw.strip()
    if text == "" or text == DATA_NOT_FOUND:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


@dataclass(frozen=True)
class MasterRow:
    ticker: str
    first_trading_date: str
    ipo_price: Decimal


def load_universe() -> dict[str, MasterRow]:
    """ticker -> MasterRow, for the 20 canonical pre-trade universe members."""
    out: dict[str, MasterRow] = {}
    for row in load_master_rows():
        price = parse_exact_decimal(row["ipo_price"])
        if price is None:
            raise ValueError(f"Canonical master ipo_price missing/unparseable for {row['ticker']}")
        out[row["ticker"]] = MasterRow(ticker=row["ticker"], first_trading_date=row["first_trading_date"], ipo_price=price)
    return out


def same_day_groups(universe: dict[str, MasterRow]) -> dict[str, str]:
    """ticker -> group_key (its first_trading_date). Two tickers with the same
    group_key are in the same same-day IPO group and must never cross-train.
    Derived dynamically from the canonical master, never hardcoded.
    """
    return {ticker: row.first_trading_date for ticker, row in universe.items()}


def prediction_cutoff_date(first_trading_date: str) -> str:
    """prediction_cutoff_date = first_trading_date - 1 calendar day (ISO date string in, ISO date string out)."""
    from datetime import date, timedelta

    y, m, d = (int(part) for part in first_trading_date.split("-"))
    cutoff = date(y, m, d) - timedelta(days=1)
    return cutoff.isoformat()

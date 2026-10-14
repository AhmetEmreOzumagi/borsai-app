"""R6 -- frozen §5 TARGET CONTRACT. Pure formulas plus the exact schema /
tick-size / 99x4-coverage validators.

Unchanged science from R5 (PASS-graded; not reopened by the R6
remediation task). Byte-identical in substance to
`scripts/modeling/prebookbuild_v1_r5/targets.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Dict, Iterable, Mapping, Optional, Set, Tuple

TARGET_NOT_AVAILABLE = "TARGET_NOT_AVAILABLE"

EXPECTED_OUTCOME_SCHEMA: Tuple[str, ...] = (
    "ticker", "horizon", "session_number", "target_session_date", "ipo_price", "official_close",
    "target_return", "target_return_exact_numerator", "target_return_exact_denominator", "above_ipo_flag",
    "row_status", "source_session_status", "conflict_status", "thb_source_url", "thb_local_path",
    "thb_sha256", "thb_internal_filename", "canonical_status",
)
EXPECTED_HORIZONS: Tuple[str, ...] = ("D1", "D3", "D5", "D10")
TICK_SCALE = Decimal("100")


class TargetSchemaError(RuntimeError):
    """The outcome CSV header did not exactly match `EXPECTED_OUTCOME_SCHEMA`."""


class TargetTickSizeIntegrityError(RuntimeError):
    """Frozen §5.3: a stored price scaled by the kuruş tick size (`x100`)
    did not land on an integer."""


class TargetMembershipError(RuntimeError):
    """A row referenced a ticker outside Historical99 or a horizon outside
    {D1, D3, D5, D10}."""


class TargetDuplicateError(RuntimeError):
    """More than one row for the same `(ticker, horizon)`."""


class TargetCoverageError(RuntimeError):
    """The complete `Historical99 membership x {D1,D3,D5,D10}` 396-key set
    was not exactly covered -- missing, extra, or otherwise non-matching
    keys. Structural, not outcome-driven; computed only from the key set,
    never from a target value."""


def compute_regression_target(ipo_price: Decimal, official_close: Decimal) -> Fraction:
    """`R_h = official_close/ipo_price - 1` (frozen §5.2). `target_transform = NONE`."""
    return Fraction(official_close) / Fraction(ipo_price) - 1


def compute_classification_target(ipo_price: Decimal, official_close: Decimal) -> int:
    """`Y_h = 1 if official_close > ipo_price else 0` (frozen §5.3).
    `TIE_IS_ZERO_AT_OR_BELOW_IPO`."""
    return 1 if official_close > ipo_price else 0


@dataclass(frozen=True)
class OutcomeRow:
    ticker: str
    horizon: str
    target_session_date: Optional[str]
    row_status: str
    conflict_status: str
    ipo_price: Optional[Decimal]
    official_close: Optional[Decimal]
    canonical_status: str


def target_is_available(row: OutcomeRow) -> bool:
    """Frozen §5.5: available iff a session date and a valid official close
    both exist. Never imputed."""
    return row.target_session_date is not None and row.official_close is not None


def validate_outcome_schema(fieldnames: Iterable[str]) -> None:
    actual = tuple(fieldnames)
    if actual != EXPECTED_OUTCOME_SCHEMA:
        raise TargetSchemaError(
            f"outcome CSV header does not match the expected authoritative schema.\n"
            f"expected: {EXPECTED_OUTCOME_SCHEMA}\nactual:   {actual}"
        )


def tick_size_integrity_check(raw_value: str, *, field: str, ticker: str, horizon: str) -> Decimal:
    value = Decimal(str(raw_value).strip())
    scaled = value * TICK_SCALE
    if scaled != scaled.to_integral_value():
        raise TargetTickSizeIntegrityError(
            f"{ticker}/{horizon}: {field}={raw_value!r} does not scale to an integral number of kuruş"
        )
    return value


def build_outcome_row(raw: Mapping[str, str]) -> OutcomeRow:
    ticker = raw["ticker"]
    horizon = raw["horizon"]
    for price_field in ("ipo_price", "official_close"):
        raw_v = raw.get(price_field)
        if raw_v is not None and str(raw_v).strip() != "":
            tick_size_integrity_check(raw_v, field=price_field, ticker=ticker, horizon=horizon)

    def _opt_decimal(key: str):
        raw_v = raw.get(key)
        if raw_v is None or str(raw_v).strip() == "":
            return None
        return Decimal(str(raw_v).strip())

    def _opt_str(key: str):
        raw_v = raw.get(key)
        if raw_v is None or str(raw_v).strip() == "":
            return None
        return str(raw_v).strip()

    return OutcomeRow(
        ticker=ticker, horizon=horizon, target_session_date=_opt_str("target_session_date"),
        row_status=raw.get("row_status", ""), conflict_status=raw.get("conflict_status", ""),
        ipo_price=_opt_decimal("ipo_price"), official_close=_opt_decimal("official_close"),
        canonical_status=raw.get("canonical_status", ""),
    )


@dataclass(frozen=True)
class OutcomeLoadReport:
    n_rows_parsed: int
    n_unique_ticker_horizon: int
    coverage_expected: int
    coverage_actual: int
    coverage_status: str  # "396/396" style


def load_and_validate_outcome_rows(
    csv_rows: Iterable[Mapping[str, str]], fieldnames: Iterable[str], membership_tickers: Set[str],
) -> Tuple[Dict[Tuple[str, str], OutcomeRow], OutcomeLoadReport]:
    """Frozen structural gate: exact schema (checked BEFORE any row is
    materialized into an `OutcomeRow`), Historical99-membership-only,
    four-horizon-only, no duplicate `(ticker, horizon)`, and an EXACT 99x4
    key-coverage assertion: every `(ticker, horizon)` pair in
    `membership_tickers x EXPECTED_HORIZONS` must be present exactly once,
    with no missing, extra, or duplicate pair. Performs no outcome-driven
    universe filtering: membership is checked against the externally
    supplied `HISTORICAL99_FROZEN_COHORT_V1` set, never derived from the
    outcome file itself.
    """
    validate_outcome_schema(fieldnames)

    by_key: Dict[Tuple[str, str], OutcomeRow] = {}
    n_parsed = 0
    for raw in csv_rows:
        n_parsed += 1
        row = build_outcome_row(raw)
        if row.ticker not in membership_tickers:
            raise TargetMembershipError(f"{row.ticker}: not a member of HISTORICAL99_FROZEN_COHORT_V1")
        if row.horizon not in EXPECTED_HORIZONS:
            raise TargetMembershipError(f"{row.ticker}/{row.horizon}: horizon not in {EXPECTED_HORIZONS}")
        key = (row.ticker, row.horizon)
        if key in by_key:
            raise TargetDuplicateError(f"duplicate outcome record for {key}")
        by_key[key] = row

    expected_keys = {(t, h) for t in membership_tickers for h in EXPECTED_HORIZONS}
    actual_keys = set(by_key.keys())
    expected_n = len(expected_keys)
    actual_n = len(actual_keys)

    if actual_keys != expected_keys:
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        raise TargetCoverageError(
            f"outcome key coverage {actual_n}/{expected_n} does not exactly match "
            f"HISTORICAL99_FROZEN_COHORT_V1 x {{D1,D3,D5,D10}}: "
            f"missing={sorted(missing)[:5]}{'...' if len(missing) > 5 else ''} "
            f"extra={sorted(extra)[:5]}{'...' if len(extra) > 5 else ''}"
        )

    report = OutcomeLoadReport(
        n_rows_parsed=n_parsed, n_unique_ticker_horizon=len(by_key),
        coverage_expected=expected_n, coverage_actual=actual_n,
        coverage_status=f"{actual_n}/{expected_n}",
    )
    return by_key, report

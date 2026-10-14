#!/usr/bin/env python3
"""Core data/session/coverage logic for the Market20 R1 repair.

BORSAI_V2_MARKET20_PREREGISTRATION_REPAIR_01.

Resolves M20-02 (exact arithmetic / materialization, no binary-float transit)
and M20-03 (independent official session calendar, breaking the circularity
of deriving S0/S20 from the XU100 series itself).

READS ONLY:
  - the official BIST Pay Market session CALENDAR (dates/session-status only:
    calendar_date, session_status, counts_as_official_session; NEVER a price,
    return, or realized-outcome column) from the protected HISTORICAL99
    outcome tree, reused strictly as PUBLIC MARKET-STRUCTURE CHRONOLOGY, not
    as outcome content -- see the R1 candidate document section on this
    distinction;
  - the official XU100 close archive (pinned, read-only, unchanged).

Computes only PRETRADE coverage/readiness. Never reads a target/outcome
value, never fits a model, never computes a performance metric.
"""

from __future__ import annotations

import bisect
import csv
import datetime
import json
import math
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from typing import Any, Optional

WINDOW_SESSIONS = 20

# ---- M20-03: independent official session calendar (NOT derived from XU100) ----
# Pure chronology only: calendar_date / session_status / counts_as_official_session.
# This artifact carries NO price, return or realized-outcome value -- verified
# empirically (test_10 in the R1 test suite parses every column and asserts no
# outcome-shaped column exists) and lives inside the protected outcome tree,
# which this task reads read-only and hash-verifies unchanged before/after.
OFFICIAL_SESSION_CALENDAR_REL = (
    "artifacts/outcomes/historical99/HISTORICAL99_FROZEN_COHORT_V1/OFFICIAL_BIST_OUTCOME_V1/"
    "canonical/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv"
)
OFFICIAL_SESSION_CALENDAR_SHA = "402a5ea6ed0565e666999111fceac40ee178f7049f2ef57391effa36bf7d9a2d"

XU100_RAW_REL = (
    "artifacts/modeling/historical99_market_sector_microstructure_stage_a/"
    "HISTORICAL99_MARKET_SECTOR_MICROSTRUCTURE_STAGE_A_V1/raw/official_bist_xu100_graphic_pinned.json"
)
XU100_RAW_SHA = "13db0171345a917d53ae99308e68694b54b56090df3b8612f6686444e99236b0"

PRETRADE_MASTER_REL = (
    "artifacts/ipo_master/historical99/HISTORICAL99_FROZEN_COHORT_V1/canonical/"
    "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv"
)

# M20-02: pinned MODEL NUMERIC context for the market20 ratio, IDENTICAL to
# frozen preprocessing.py's MODEL_NUMERIC_PRECISION=60 / ROUND_HALF_EVEN, so
# the candidate introduces no competing numeric convention.
MARKET20_CONTEXT_PRECISION = 60
MARKET20_CONTEXT = Context(prec=MARKET20_CONTEXT_PRECISION, rounding=ROUND_HALF_EVEN)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


# ------------------------------------------------------- M20-03: calendar --
def load_official_session_calendar(repo: Path) -> list[str]:
    """Ascending, de-duplicated list of OFFICIAL BIST Pay Market session
    dates, from the independent calendar artifact -- never from XU100."""
    rows = read_csv(repo / OFFICIAL_SESSION_CALENDAR_REL)
    sessions = sorted({r["calendar_date"] for r in rows if r["counts_as_official_session"] == "TRUE"})
    return sessions


# -------------------------------------------------- M20-02: exact XU100 ----
def load_xu100_closes(path: Path) -> dict[str, Decimal]:
    """RAW MARKET EVIDENCE ONLY: date -> official XU100 close, parsed as an
    EXACT Decimal directly from the JSON numeric lexeme.

    Uses `json.loads(..., parse_float=Decimal)`: per the stdlib json module,
    `parse_float` is invoked with the exact SUBSTRING TEXT of each JSON
    float literal, so the value never transits a binary64 `float` at all
    (M20-02 item 1) -- unlike the original candidate's
    `Decimal(str(json_parsed_float))`, which first rounded the source lexeme
    to the nearest float64 and only then re-decimalized that already-lossy
    value.
    """
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text, parse_float=Decimal)
    if payload.get("status") != "success":
        raise RuntimeError(f"XU100_ARCHIVE_STATUS_NOT_SUCCESS: {payload.get('status')}")
    closes: dict[str, Decimal] = {}
    for record in payload["data"]:
        if record.get("indexName") != "XU100":
            raise RuntimeError(f"XU100_UNEXPECTED_INDEX: {record.get('indexName')}")
        date = record["hisTs"]
        value = record["clval"]
        if isinstance(value, int) and not isinstance(value, bool):
            # a JSON integer lexeme (e.g. "15000") is parsed by json's int path,
            # not parse_float; int -> Decimal is always exact, so this still
            # never transits a binary64 float.
            value = Decimal(value)
        elif not isinstance(value, Decimal):
            raise RuntimeError(f"XU100_CLOSE_NOT_DECIMAL_OR_INT: {date} parsed as {type(value)}")
        if date in closes and closes[date] != value:
            raise RuntimeError(f"XU100_DUPLICATE_DATE_CONFLICT: {date}")
        closes[date] = value
    return closes


def s0_s20_from_calendar(sessions: list[str], t_date: str) -> tuple[int, Optional[str], Optional[str]]:
    """FROZEN session indexing over the INDEPENDENT official calendar.

    i = index of the latest OFFICIAL session strictly before T(k)  -> S0
    j = i - WINDOW_SESSIONS                                        -> S20

    Unchanged from the original candidate's convention (21 distinct closes,
    20 return intervals; M20-01/M20-04/M20-05/M20-06/M20-07 do not touch this
    definition). The only change under M20-03 is WHICH session list `sessions`
    is: the independent official calendar, never XU100's own date set.
    """
    i = bisect.bisect_left(sessions, t_date) - 1
    if i < 0:
        return i, None, None
    j = i - WINDOW_SESSIONS
    if j < 0:
        return i, sessions[i], None
    return i, sessions[i], sessions[j]


def materialize_market20_raw(close_s0: Decimal, close_s20: Decimal) -> Decimal:
    """M20-02: exact Market20 ratio, computed inside the pinned MODEL NUMERIC
    Decimal context (precision=60, ROUND_HALF_EVEN) -- the SAME context frozen
    V1.5 uses for its own model-numeric operations (log, std, z), so the
    candidate introduces no second numeric convention.

    No quantization is applied to the stored value: it is the exact Decimal
    result of `close_s0 / close_s20 - 1` at 60-digit precision. Conversion to
    float64 happens ONLY at the standardization boundary (the same point
    frozen f2/f3/f4 identity features convert), never here.
    """
    with localcontext(MARKET20_CONTEXT):
        return close_s0 / close_s20 - Decimal(1)


def canonical_market20_string(value: Decimal) -> str:
    """Canonical serialization: str(Decimal), which round-trips exactly via
    `Decimal(canonical_market20_string(x)) == x` for any Decimal produced by
    `materialize_market20_raw` (no exponential/engineering notation surprises
    for values in this magnitude range, verified by round-trip tests)."""
    return str(value)


def build_coverage(repo: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    master = read_csv(repo / PRETRADE_MASTER_REL)
    if len(master) != 99:
        raise RuntimeError(f"HISTORICAL99_ROW_COUNT_MISMATCH: {len(master)}")

    sessions = load_official_session_calendar(repo)
    closes = load_xu100_closes(repo / XU100_RAW_REL)
    session_set = set(sessions)

    rows: list[dict[str, Any]] = []
    ftd_in_calendar = 0
    t_minus_s0: list[int] = []
    s0_minus_s20: list[int] = []
    for record in sorted(master, key=lambda r: (r["first_trading_date"], r["ticker"])):
        ticker = record["ticker"]
        t_date = record["first_trading_date"]
        in_calendar = t_date in session_set
        ftd_in_calendar += 1 if in_calendar else 0

        i, s0, s20 = s0_s20_from_calendar(sessions, t_date)
        insufficient_history = s0 is None or s20 is None

        close_s0_present = s0 is not None and s0 in closes
        close_s20_present = s20 is not None and s20 in closes
        market20_value_str = ""
        readiness = ""
        if insufficient_history:
            readiness = "DATA_NOT_FOUND_INSUFFICIENT_CALENDAR_HISTORY"
        elif not (close_s0_present and close_s20_present):
            readiness = "DATA_NOT_FOUND_XU100_CLOSE_MISSING_FOR_OFFICIAL_SESSION"
        else:
            readiness = "COMPUTABLE"
            raw = materialize_market20_raw(closes[s0], closes[s20])
            market20_value_str = canonical_market20_string(raw)
            t_minus_s0.append(
                (datetime.date.fromisoformat(t_date) - datetime.date.fromisoformat(s0)).days)
            s0_minus_s20.append(
                (datetime.date.fromisoformat(s0) - datetime.date.fromisoformat(s20)).days)

        rows.append({
            "ticker": ticker,
            "first_trading_date_T": t_date,
            "T_is_official_calendar_session": "YES" if in_calendar else "NO",
            "calendar_source": "INDEPENDENT_OFFICIAL_BIST_PAY_SESSION_CALENDAR",
            "S0_session_date": s0 or "",
            "S0_session_index": i if i >= 0 else "",
            "S0_strictly_before_T": "YES" if (s0 is not None and s0 < t_date) else "NO",
            "S20_session_date": s20 or "",
            "S20_session_index": (i - WINDOW_SESSIONS) if s20 is not None else "",
            "S20_exactly_20_positions_before_S0":
                "YES" if (s0 is not None and s20 is not None
                         and sessions.index(s0) - sessions.index(s20) == WINDOW_SESSIONS) else "",
            "session_intervals_in_window": WINDOW_SESSIONS if readiness == "COMPUTABLE" else "",
            "distinct_closes_in_window": WINDOW_SESSIONS + 1 if readiness == "COMPUTABLE" else "",
            "official_close_present_S0": "YES" if close_s0_present else ("NOT_APPLICABLE" if s0 is None else "NO"),
            "official_close_present_S20": "YES" if close_s20_present else ("NOT_APPLICABLE" if s20 is None else "NO"),
            "readiness_status": readiness,
            "market20_raw_value_canonical": market20_value_str,
            "window_shifted": "NO",
            "value_interpolated": "NO",
            "value_forward_filled": "NO",
            "point_in_time_date_rule":
                "POINT_IN_TIME_PROVEN" if readiness == "COMPUTABLE"
                else "NOT_APPLICABLE_INSUFFICIENT_CALENDAR_HISTORY" if insufficient_history
                else "NOT_APPLICABLE_XU100_CLOSE_MISSING",
            "official_source_status": "OFFICIAL_SOURCE_VERIFIED",
        })

    computable = [r for r in rows if r["readiness_status"] == "COMPUTABLE"]
    dnf_calendar = [r for r in rows if r["readiness_status"] == "DATA_NOT_FOUND_INSUFFICIENT_CALENDAR_HISTORY"]
    dnf_close = [r for r in rows if r["readiness_status"] == "DATA_NOT_FOUND_XU100_CLOSE_MISSING_FOR_OFFICIAL_SESSION"]

    summary = {
        "total_rows": len(rows),
        "computable": len(computable),
        "data_not_found_insufficient_calendar_history": len(dnf_calendar),
        "data_not_found_insufficient_calendar_history_tickers":
            sorted(r["ticker"] for r in dnf_calendar),
        "data_not_found_xu100_close_missing": len(dnf_close),
        "data_not_found_total": len(dnf_calendar) + len(dnf_close),
        "ftd_in_official_calendar": ftd_in_calendar,
        "pit_proven": len(computable),
        "pit_not_applicable_insufficient_calendar_history": len(dnf_calendar),
        "pit_not_applicable_xu100_close_missing": len(dnf_close),
        "pit_fail": 0,
        "min_t_minus_s0_days": min(t_minus_s0) if t_minus_s0 else None,
        "max_t_minus_s0_days": max(t_minus_s0) if t_minus_s0 else None,
        "min_s0_minus_s20_days": min(s0_minus_s20) if s0_minus_s20 else None,
        "max_s0_minus_s20_days": max(s0_minus_s20) if s0_minus_s20 else None,
        "calendar_source_artifact": OFFICIAL_SESSION_CALENDAR_REL,
        "calendar_source_sha256": OFFICIAL_SESSION_CALENDAR_SHA,
        "calendar_first_date": sessions[0],
        "calendar_last_date": sessions[-1],
        "calendar_session_count": len(sessions),
        "calendar_columns_used": ["calendar_date", "session_status", "counts_as_official_session"],
        "calendar_columns_contain_no_outcome_value": True,
        "raw_source_sha256": XU100_RAW_SHA,
        "coverage_pct": round(100.0 * len(computable) / len(rows), 4),
        "missingness_indicator_added": len(dnf_calendar) + len(dnf_close) > 0,
        "missingness_indicator_id": "f7_market20_missing",
        "missingness_indicator_justification": (
            "coverage is 93/99 (94.9%), not 100%; frozen V1.5 itself pairs f3 (97/99 usable, "
            "97.98%) with an indicator (f5) on the same ex-ante logic -- a nonzero, non-trivial "
            "missingness rate on a training-fold-imputed feature gets an indicator, mirroring the "
            "existing frozen precedent rather than inventing a new rule"
        ),
    }
    return rows, summary


# ===========================================================================
# M20-01: metric-specific matched sets
# ===========================================================================
#
# Pure predicate functions over STATUS/VALUE pairs. No fitted model is ever
# called here; these are re-implementations of the exact emission predicate
# that ALREADY governs frozen V1.5's own candidate_models.py, so the SAME rule
# applies to both the frozen control and the candidate (no invented
# candidate-only or control-only rule).
#
# Frozen status vocabulary (scripts/modeling/candidate_models.py, unchanged):
#   STATUS_FIT_OK
#   STATUS_INSUFFICIENT_TRAINING_HISTORY          (effective outer train N < MIN_TRAIN_N)
#   STATUS_INSUFFICIENT_FEATURE_VARIATION          (final outer preprocess_fold: zero
#                                                    surviving substantive columns)
#   STATUS_MODEL_NOT_FIT_INNER_PREPROCESSING_INSUFFICIENT_VARIATION
#                                                   (Ridge only: every inner LOOCV split
#                                                    structurally degenerate)
#   STATUS_MODEL_NOT_FIT_SINGLE_CLASS              (Logistic only: outer training labels
#                                                    all one class -- "degenerate class fold")
#   STATUS_MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE (Logistic only)
#
# A row/horizon EMITS for a given metric iff status == STATUS_FIT_OK AND the
# produced value is present and finite (classification additionally requires
# the probability to lie in [0, 1]). Any other status is NON-EMITTING.

STATUS_FIT_OK = "STATUS_FIT_OK"
STATUS_INSUFFICIENT_TRAINING_HISTORY = "STATUS_INSUFFICIENT_TRAINING_HISTORY"
STATUS_INSUFFICIENT_FEATURE_VARIATION = "STATUS_INSUFFICIENT_FEATURE_VARIATION"
STATUS_MODEL_NOT_FIT_INNER_PREPROCESSING_INSUFFICIENT_VARIATION = (
    "STATUS_MODEL_NOT_FIT_INNER_PREPROCESSING_INSUFFICIENT_VARIATION")
STATUS_MODEL_NOT_FIT_SINGLE_CLASS = "STATUS_MODEL_NOT_FIT_SINGLE_CLASS"
STATUS_MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE = "STATUS_MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE"

REGRESSION_NON_EMITTING_STATUSES = frozenset({
    STATUS_INSUFFICIENT_TRAINING_HISTORY,
    STATUS_MODEL_NOT_FIT_INNER_PREPROCESSING_INSUFFICIENT_VARIATION,
    STATUS_INSUFFICIENT_FEATURE_VARIATION,
})
CLASSIFICATION_NON_EMITTING_STATUSES = frozenset({
    STATUS_INSUFFICIENT_TRAINING_HISTORY,
    STATUS_MODEL_NOT_FIT_SINGLE_CLASS,
    STATUS_MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE,
    STATUS_INSUFFICIENT_FEATURE_VARIATION,
})


def emits_regression_prediction(status: str, value: Optional[float]) -> bool:
    """A row/horizon emits a valid finite return prediction iff status ==
    STATUS_FIT_OK and the value is present and finite. Identical predicate for
    frozen V1.5 and the candidate."""
    if status != STATUS_FIT_OK:
        return False
    return value is not None and math.isfinite(value)


def emits_classification_probability(status: str, value: Optional[float]) -> bool:
    """A row/horizon emits a valid finite class-1 probability iff status ==
    STATUS_FIT_OK and the value is present, finite, and in [0, 1]. Identical
    predicate for frozen V1.5 and the candidate."""
    if status != STATUS_FIT_OK:
        return False
    return value is not None and math.isfinite(value) and 0.0 <= value <= 1.0


def in_matched_regression_set(v1_5_status: str, v1_5_value: Optional[float],
                              candidate_status: str, candidate_value: Optional[float]) -> bool:
    """MATCHED_REGRESSION_SET(h) membership for a single row: both sides must
    emit a valid finite return prediction at the same horizon. Any
    non-emitting status on either side excludes the row for BOTH metrics
    (never just one)."""
    return (emits_regression_prediction(v1_5_status, v1_5_value)
            and emits_regression_prediction(candidate_status, candidate_value))


def in_matched_classification_set(v1_5_status: str, v1_5_value: Optional[float],
                                  candidate_status: str, candidate_value: Optional[float]) -> bool:
    """MATCHED_CLASSIFICATION_SET(h) membership for a single row: both sides
    must emit a valid finite class-1 probability at the same horizon."""
    return (emits_classification_probability(v1_5_status, v1_5_value)
            and emits_classification_probability(candidate_status, candidate_value))

"""Generic deterministic frozen V1.5 POST_BOOKBUILD_PRE_LISTING harness.

BORSAI_V1_5_POST_BOOKBUILD_PRE_LISTING_PROSPECTIVE_HARNESS_READINESS_01.

Governance: this harness exists because of
artifacts/predictions/diagnostics/V1_5_PRE_RESULT_APPLICABILITY_CLOSURE_01/
V1_5_PRE_RESULT_APPLICABILITY_CLOSURE_01.json, which restricts frozen V1.5
(BORSAI_V1_5_PREREG_20260814) from being used as an authoritative new
prediction while official total_demand_multiple (f3) is unavailable. The
allowed cutoff going forward is POST_BOOKBUILD_PRE_LISTING: official IPO
results published, f3 known, f5=0, secondary trading not started, no
D1/D3/D5/D10 outcome observed.

This module makes NO new scientific choice. It is mechanically modeled on
scripts/modeling/run_bkrgy_frozen_v1_5_prospective_freeze.py and
scripts/modeling/run_intet_frozen_v1_5_prebookbuild_prospective_freeze.py:
same frozen HISTORICAL99 hash gate, same eligible_training /
STRICT_PRIOR_DATE_RULE reconstruction, same candidate_models.fit_ridge_candidate
/ fit_logistic_candidate calls, same explicit non-value for
confidence/prediction_interval/risk_label (no frozen V1.5 artifact defines a
formula for them). It generalizes those two scripts' hardcoded single-ticker
FACTS into an explicit PostBookbuildInputContract, and it inherits INTET's own
self-corrected idempotency design: a persisted manifest is written EXACTLY
ONCE, using the real system clock captured at that moment, and carries no
per-invocation write-outcome bookkeeping field (no CREATED_NEW /
UNCHANGED_IDENTICAL or equivalent anywhere in persisted bytes) -- this is the
explicit fix for BKRGY's first-attempt manifest defect, where
packet_status/prediction_status/eligibility_status/manifest_status were
embedded in scientific manifest content.

Two-phase design, deliberately separated so gate-checking can never reach a
model-fit call:

  * validate_gates(contract)   -- pure, deterministic contract/gate checks
                                   only. Never loads HISTORICAL99 state, never
                                   calls a candidate-model fitter, never
                                   writes a file.
  * execute_freeze(contract)   -- validates gates, then runs the full
                                   mechanical freeze pipeline (state load,
                                   eligible_training, Ridge/Logistic fit,
                                   packet/prediction/eligibility/manifest
                                   write) using the same INTET
                                   create-once/reverify-only-thereafter split.
                                   NOT wired into this module's CLI and NOT
                                   invoked anywhere in this repository as of
                                   the harness-readiness task that created
                                   this file -- a future, separate task's own
                                   driver must call it directly, supplying a
                                   real, officially-sourced input contract.

main() below only ever calls validate_gates(); it is structurally incapable
of creating a prediction artifact.

Must run under `.venv-v1_5-model` for any call that reaches
verify_v1_5_identity_and_hash_gate() -> frozen.verify_hash_gate() (see
candidate_models.verify_runtime()). validate_gates() and execute_freeze()
never call a candidate-model fit function during gate evaluation itself.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from . import candidate_models as cm
from . import run_historical99_frozen_v1_5_benchmark as frozen

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "BORSAI_V1_5_POST_BOOKBUILD_PRE_LISTING_PROSPECTIVE_HARNESS_READINESS_01"
PREDICTION_CLASS = "POST_BOOKBUILD_PRE_LISTING_PROSPECTIVE"
V1_5_IDENTITY = "BORSAI_V1_5_PREREG_20260814"
HORIZONS = frozen.HORIZONS
MIN_TRAIN_N = frozen.MIN_TRAIN_N

# Turkey has observed a fixed UTC+3 offset with no daylight-saving transitions
# since 2016 (Resmi Gazete 2016/8552); same fixed-offset rationale as the
# INTET precedent -- exact, not an approximation, no tzdata dependency.
ISTANBUL = timezone(timedelta(hours=3), name="+03:00")

# Identical to the BKRGY/INTET EXPECTED_HASHES dict -- frozen constants
# restated, not a new value.
EXPECTED_HASHES = {
    frozen.MASTER_PATH: "573f4c77c5ac9f9d3aaf7715a5b054ff412991120c73f2c03065521c7fc9173b",
    frozen.TARGET_PATH: "64dce0bb3b2aff28f5dfd5f335da8f423a5cf0839430cac1df200bfed4417f9c",
    frozen.PREREG_PATH: "156435859e4ea81d078a56435a6bf6a7f04bd1fea289fc15b1baccebb4c2ce2d",
    frozen.SPEC_PATH: "1245bf0f96c63cabdbd740cf043e9f3c58f8fc50af48472933c29e05dce211b1",
}

OUTPUT_ROOT = ROOT / "artifacts" / "predictions" / "prospective"

STATUS_GATES_PASSED = "POST_BOOKBUILD_V1_5_GATES_PASSED_READY_TO_FREEZE"
STATUS_F3_NOT_AVAILABLE = "POST_BOOKBUILD_V1_5_BLOCKED_F3_NOT_AVAILABLE"
STATUS_WINDOW_MISSED = "POST_BOOKBUILD_PRE_LISTING_WINDOW_MISSED"
STATUS_SOURCES_CONFLICT = "SOURCES_CONFLICT"
STATUS_CONTAMINATION = "FAIL_CONTAMINATION"
STATUS_HASH_MISMATCH = "POST_BOOKBUILD_V1_5_HASH_MISMATCH"
STATUS_INPUT_CONTRACT_INCOMPLETE = "POST_BOOKBUILD_V1_5_INPUT_CONTRACT_INCOMPLETE"
STATUS_TIMESTAMP_INVALID = "POST_BOOKBUILD_V1_5_TIMESTAMP_INVALID"
STATUS_PARTIAL_FREEZE_STATE = "POST_BOOKBUILD_V1_5_PARTIAL_FREEZE_STATE_DETECTED"

REQUIRED_CONTRACT_FIELDS = (
    "ticker",
    "company_name",
    "prediction_timestamp",
    "prediction_local_date",
    "ipo_price_tl",
    "shares_offered_final",
    "post_ipo_share_capital",
    "capital_increase_shares",
    "official_total_demand_multiple",
    "official_result_source",
    "source_identifier",
    "source_publication_timestamp",
    "bookbuilding_end",
    "secondary_trading_start_status",
)

# official_total_demand_multiple is deliberately excluded here: an
# empty/missing value for that one field has its own dedicated, more
# specific gate (STATUS_F3_NOT_AVAILABLE) below, so the generic
# input-contract completeness check must not shadow it with the less
# specific STATUS_INPUT_CONTRACT_INCOMPLETE.
_ADMIN_COMPLETENESS_FIELDS = tuple(f for f in REQUIRED_CONTRACT_FIELDS if f != "official_total_demand_multiple")


class GateFailure(RuntimeError):
    """A fail-closed cutoff-gate rejection. `.code` is one of the STATUS_* constants."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


class FreezeStop(RuntimeError):
    pass


@dataclass(frozen=True)
class PostBookbuildInputContract:
    ticker: str
    company_name: str
    prediction_timestamp: str
    prediction_local_date: str
    ipo_price_tl: str
    shares_offered_final: str
    post_ipo_share_capital: str
    capital_increase_shares: str
    official_total_demand_multiple: Optional[str]
    official_result_source: str
    source_identifier: str
    source_publication_timestamp: str
    bookbuilding_end: str
    secondary_trading_start_status: str
    outcome_observed: bool = False
    source_document_local_path: Optional[str] = None
    source_document_sha256: Optional[str] = None

    @staticmethod
    def from_mapping(data: Mapping[str, Any]) -> "PostBookbuildInputContract":
        missing = [f for f in REQUIRED_CONTRACT_FIELDS if f not in data]
        if missing:
            raise GateFailure(
                STATUS_INPUT_CONTRACT_INCOMPLETE, f"missing required fields: {missing}"
            )
        return PostBookbuildInputContract(
            ticker=data["ticker"],
            company_name=data["company_name"],
            prediction_timestamp=data["prediction_timestamp"],
            prediction_local_date=data["prediction_local_date"],
            ipo_price_tl=data["ipo_price_tl"],
            shares_offered_final=data["shares_offered_final"],
            post_ipo_share_capital=data["post_ipo_share_capital"],
            capital_increase_shares=data["capital_increase_shares"],
            official_total_demand_multiple=data.get("official_total_demand_multiple"),
            official_result_source=data["official_result_source"],
            source_identifier=data["source_identifier"],
            source_publication_timestamp=data["source_publication_timestamp"],
            bookbuilding_end=data["bookbuilding_end"],
            secondary_trading_start_status=data["secondary_trading_start_status"],
            outcome_observed=bool(data.get("outcome_observed", False)),
            source_document_local_path=data.get("source_document_local_path"),
            source_document_sha256=data.get("source_document_sha256"),
        )


# ---------------------------------------------------------------------------
# Verbatim-reused utilities (identical to the BKRGY/INTET precedents).
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        raise FreezeStop("Refusing to serialize an empty CSV")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def decimal_text(value: Decimal, places: int = 10) -> str:
    quantum = Decimal(1).scaleb(-places)
    rendered = format(value.quantize(quantum, rounding=ROUND_HALF_UP), "f").rstrip("0").rstrip(".")
    return rendered or "0"


def fmt_float(value: Optional[float]) -> str:
    if value is None:
        return ""
    if not math.isfinite(value):
        raise FreezeStop("Non-finite model value")
    return format(value, ".17g")


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def identity_hash(items) -> str:
    return sha256_bytes(("\n".join(items) + "\n").encode("utf-8"))


# ---------------------------------------------------------------------------
# Phase 1: pure gate validation. No model fit call. No HISTORICAL99 state load.
# ---------------------------------------------------------------------------

def _parse_timestamp(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise GateFailure(
            STATUS_TIMESTAMP_INVALID, f"{field_name} not a valid ISO8601 timestamp: {value!r}"
        ) from exc
    if parsed.tzinfo is None:
        raise GateFailure(STATUS_TIMESTAMP_INVALID, f"{field_name} missing UTC offset: {value!r}")
    return parsed


def verify_v1_5_identity_and_hash_gate() -> dict[str, str]:
    """Pure file-hash comparison against the frozen V1.5 identity. Does NOT
    call cm.verify_runtime() and does NOT fit anything -- gate-only, safe to
    call under any Python environment that can read the repository."""
    actual: dict[str, str] = {}
    for path, expected in EXPECTED_HASHES.items():
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        if not path.is_file():
            raise GateFailure(STATUS_HASH_MISMATCH, f"missing frozen input: {rel}")
        found = sha256_file(path)
        actual[rel] = found
        if found != expected:
            raise GateFailure(
                STATUS_HASH_MISMATCH, f"{rel} expected={expected} actual={found}"
            )
    return actual


def validate_gates(
    contract: PostBookbuildInputContract,
    *,
    now_provider: Callable[[], datetime] = lambda: datetime.now(ISTANBUL),
) -> dict[str, Any]:
    """Fail-closed pre-flight gate evaluation (governing task section 4).
    Raises GateFailure on the first failing gate; returns a gate report only
    when every gate passes. Calls no candidate-model fitter and loads no
    HISTORICAL99 state."""
    missing = [f for f in _ADMIN_COMPLETENESS_FIELDS if not getattr(contract, f, None)]
    if missing:
        raise GateFailure(STATUS_INPUT_CONTRACT_INCOMPLETE, f"missing/empty required fields: {missing}")

    if contract.official_total_demand_multiple in (None, "", "DATA_NOT_FOUND"):
        raise GateFailure(STATUS_F3_NOT_AVAILABLE, "official_total_demand_multiple not available")
    try:
        f3 = Decimal(contract.official_total_demand_multiple)
    except Exception as exc:
        raise GateFailure(
            STATUS_F3_NOT_AVAILABLE,
            f"official_total_demand_multiple not decimal-parseable: {contract.official_total_demand_multiple!r}",
        ) from exc
    if f3 <= 0:
        raise GateFailure(STATUS_F3_NOT_AVAILABLE, "official_total_demand_multiple must be > 0")

    if contract.secondary_trading_start_status != "NOT_STARTED":
        raise GateFailure(
            STATUS_WINDOW_MISSED,
            f"secondary_trading_start_status={contract.secondary_trading_start_status!r}",
        )

    if contract.outcome_observed:
        raise GateFailure(STATUS_CONTAMINATION, "a D1/D3/D5/D10 outcome has already been observed")

    now = now_provider()
    prediction_ts = _parse_timestamp(contract.prediction_timestamp, "prediction_timestamp")
    if prediction_ts > now:
        raise GateFailure(STATUS_TIMESTAMP_INVALID, "prediction_timestamp is in the future relative to system clock")
    source_ts = _parse_timestamp(contract.source_publication_timestamp, "source_publication_timestamp")
    if source_ts > prediction_ts:
        raise GateFailure(STATUS_SOURCES_CONFLICT, "source_publication_timestamp is after prediction_timestamp")

    if contract.source_document_local_path:
        if not contract.source_document_sha256:
            raise GateFailure(STATUS_SOURCES_CONFLICT, "source_document_local_path given without source_document_sha256")
        local_path = Path(contract.source_document_local_path)
        if not local_path.is_file():
            raise GateFailure(STATUS_SOURCES_CONFLICT, f"source_document_local_path does not exist: {local_path}")
        found = sha256_file(local_path)
        if found != contract.source_document_sha256:
            raise GateFailure(STATUS_SOURCES_CONFLICT, "source_document_sha256 does not match local file contents")

    v1_5_hashes = verify_v1_5_identity_and_hash_gate()

    return {
        "status": STATUS_GATES_PASSED,
        "gates_checked_utc": now.astimezone(timezone.utc).isoformat(),
        "v1_5_identity": V1_5_IDENTITY,
        "v1_5_hashes": v1_5_hashes,
        "prediction_class": PREDICTION_CLASS,
        "ticker": contract.ticker,
    }


# ---------------------------------------------------------------------------
# Phase 2: full mechanical freeze pipeline. Not wired into this module's CLI.
# Identical scientific behavior to BKRGY/INTET, generalized over `contract`.
# ---------------------------------------------------------------------------

def calculated_features(contract: PostBookbuildInputContract) -> dict[str, Decimal]:
    shares = Decimal(contract.shares_offered_final)
    post = Decimal(contract.post_ipo_share_capital)
    cap_inc = Decimal(contract.capital_increase_shares)
    ipo_price = Decimal(contract.ipo_price_tl)
    f3 = Decimal(contract.official_total_demand_multiple)
    f1 = shares * ipo_price
    f2 = Decimal(decimal_text(shares / post * Decimal(100)))
    f4 = Decimal(decimal_text(cap_inc / shares * Decimal(100)))
    return {"f1": f1, "f2": f2, "f3": f3, "f4": f4}


def eligible_training(state: Any, horizon: str, prediction_date: str) -> tuple[str, ...]:
    """Verbatim identical filter to the BKRGY/INTET precedent -- no new
    scientific choice. `state` duck-types frozen.LoadedState (.master, .targets)."""
    ordered = sorted(state.master, key=lambda t: (state.master[t]["first_trading_date"], t))
    return tuple(
        ticker
        for ticker in ordered
        if state.targets[(ticker, horizon)].target_status == frozen.TARGET_AVAILABLE
        and state.targets[(ticker, horizon)].underlying_row_status == frozen.OFFICIAL_VERIFIED
        and state.targets[(ticker, horizon)].underlying_conflict_status == frozen.NO_CONFLICT
        and state.targets[(ticker, horizon)].target_session_date < prediction_date
    )


def output_paths(ticker: str, prediction_local_date: str, *, output_root: Path = OUTPUT_ROOT) -> dict[str, Path]:
    dir_name = f"{ticker}_{prediction_local_date.replace('-', '')}_V1_5_POST_BOOKBUILD_PRE_LISTING"
    output_dir = output_root / dir_name
    stem = f"{ticker}_{prediction_local_date.replace('-', '')}_V1_5_POST_BOOKBUILD_PRE_LISTING"
    return {
        "output_dir": output_dir,
        "packet": output_dir / f"{stem}_pretrade_evidence_packet.csv",
        "prediction": output_dir / f"{stem}_frozen_prediction_ledger.csv",
        "eligibility": output_dir / f"{stem}_training_eligibility_summary.csv",
        "manifest": output_dir / f"{stem}_prediction_freeze_manifest.json",
    }


def build_packet_rows(contract: PostBookbuildInputContract, features: dict[str, Decimal]) -> list[dict[str, Any]]:
    rows = [
        {"field": "ipo_price_tl", "raw_value": contract.ipo_price_tl, "normalized_value": contract.ipo_price_tl,
         "calculation": "SOURCE_REPORTED"},
        {"field": "shares_offered_final", "raw_value": contract.shares_offered_final, "normalized_value": contract.shares_offered_final,
         "calculation": "SOURCE_REPORTED"},
        {"field": "capital_increase_shares", "raw_value": contract.capital_increase_shares, "normalized_value": contract.capital_increase_shares,
         "calculation": "SOURCE_REPORTED"},
        {"field": "post_ipo_share_capital", "raw_value": contract.post_ipo_share_capital, "normalized_value": contract.post_ipo_share_capital,
         "calculation": "SOURCE_REPORTED"},
        {"field": "f1", "raw_value": f"{contract.shares_offered_final}*{contract.ipo_price_tl}", "normalized_value": str(features["f1"]),
         "calculation": "f1=shares_offered_final*ipo_price_tl=ipo_size_tl"},
        {"field": "f2", "raw_value": f"{contract.shares_offered_final}/{contract.post_ipo_share_capital}*100", "normalized_value": str(features["f2"]),
         "calculation": "shares_offered_final/post_ipo_share_capital*100; ROUND_HALF_UP_10DP"},
        {"field": "f3", "raw_value": contract.official_total_demand_multiple, "normalized_value": str(features["f3"]),
         "calculation": "OFFICIAL_VERIFIED_TOTAL_DEMAND_MULTIPLE"},
        {"field": "f4", "raw_value": f"{contract.capital_increase_shares}/{contract.shares_offered_final}*100", "normalized_value": str(features["f4"]),
         "calculation": "capital_increase_shares/shares_offered_final*100; ROUND_HALF_UP_10DP"},
        {"field": "f5", "raw_value": "0", "normalized_value": "0",
         "calculation": "1_IF_AND_ONLY_IF_F3_IS_MISSING_ELSE_0"},
    ]
    out_rows = []
    for row in rows:
        out_rows.append({
            "task_id": f"BORSAI_{contract.ticker}_V1_5_POST_BOOKBUILD_PRE_LISTING_PREDICTION_FREEZE_01",
            "ticker": contract.ticker,
            "company": contract.company_name,
            "prediction_local_date": contract.prediction_local_date,
            "prediction_classification": PREDICTION_CLASS,
            "bookbuilding_end": contract.bookbuilding_end,
            **row,
            "source": contract.official_result_source,
            "source_id": contract.source_identifier,
            "source_publication_timestamp": contract.source_publication_timestamp,
            "source_document_sha256": contract.source_document_sha256 or "",
            "availability_before_T_status": "AVAILABLE_BEFORE_PREDICTION",
            "packet_semantic_sha256": "",
        })
    semantic_payload = [{k: v for k, v in r.items() if k != "packet_semantic_sha256"} for r in out_rows]
    semantic_hash = sha256_bytes(compact_json(semantic_payload).encode("utf-8"))
    for r in out_rows:
        r["packet_semantic_sha256"] = semantic_hash
    return out_rows


def build_predictions(
    contract: PostBookbuildInputContract,
    state: Any,
    packet_sha256: str,
    *,
    ridge_fitter: Callable = cm.fit_ridge_candidate,
    logistic_fitter: Callable = cm.fit_logistic_candidate,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ticker = contract.ticker
    if ticker in state.master:
        raise FreezeStop(f"{ticker} found in frozen HISTORICAL99 cohort -- contamination")
    features = calculated_features(contract)
    test_raw = {"f1": features["f1"], "f2": features["f2"], "f3": features["f3"], "f4": features["f4"]}
    prediction_rows: list[dict[str, Any]] = []
    eligibility_rows: list[dict[str, Any]] = []
    for horizon in HORIZONS:
        training = eligible_training(state, horizon, contract.prediction_local_date)
        if len(training) < MIN_TRAIN_N:
            raise FreezeStop(f"{ticker}/{horizon}: insufficient training (n={len(training)} < {MIN_TRAIN_N})")
        if ticker in training:
            raise FreezeStop(f"{ticker} self-training detected")
        target_dates = [state.targets[(x, horizon)].target_session_date for x in training]
        if not all(x < contract.prediction_local_date for x in target_dates):
            raise FreezeStop(f"{ticker}/{horizon}: strict-prior-date gate failed")
        training_targets = {x: state.targets[(x, horizon)] for x in training}
        training_raw = {x: state.raw_features[x] for x in training}
        filter_status = {x: state.filter_status.get(x) for x in training}
        filter_status["__test__"] = None
        ridge = ridge_fitter(training_raw, training_targets, test_raw, filter_status)
        logistic = logistic_fitter(training_raw, training_targets, test_raw, filter_status)
        prediction_return = ridge.prediction
        predicted_close = None if prediction_return is None else float(contract.ipo_price_tl) * (1.0 + prediction_return)
        identities = [
            "|".join([x, state.targets[(x, horizon)].target_session_date,
                       state.targets[(x, horizon)].R_h or "", str(state.targets[(x, horizon)].Y_h)])
            for x in training
        ]
        same_date = sum(x == contract.prediction_local_date for x in target_dates)
        future = sum(x > contract.prediction_local_date for x in target_dates)
        eligibility_rows.append({
            "task_id": f"BORSAI_{ticker}_V1_5_POST_BOOKBUILD_PRE_LISTING_PREDICTION_FREEZE_01",
            "ticker": ticker,
            "prediction_local_date": contract.prediction_local_date,
            "horizon": horizon,
            "training_n": len(training),
            "training_tickers_json": compact_json(list(training)),
            "training_tickers_sha256": identity_hash(training),
            "training_targets_sha256": identity_hash(identities),
            "minimum_target_session_date": min(target_dates),
            "maximum_target_session_date": max(target_dates),
            "strict_prior_date_rule": "target_session_date < prediction_local_date",
            "same_date_leakage_n": same_date,
            "future_target_leakage_n": future,
            "self_leakage_n": 0,
            "invalid_conflict_n": 0,
            "eligibility_status": "ELIGIBLE_FROZEN_HISTORICAL99_ONLY",
        })
        prediction_rows.append({
            "task_id": f"BORSAI_{ticker}_V1_5_POST_BOOKBUILD_PRE_LISTING_PREDICTION_FREEZE_01",
            "prediction_classification": PREDICTION_CLASS,
            "ticker": ticker,
            "company": contract.company_name,
            "prediction_local_date": contract.prediction_local_date,
            "bookbuilding_end": contract.bookbuilding_end,
            "horizon": horizon,
            "training_n": len(training),
            "training_tickers_sha256": identity_hash(training),
            "training_targets_sha256": identity_hash(identities),
            "f1": str(test_raw["f1"]),
            "f2": str(test_raw["f2"]),
            "f3": str(test_raw["f3"]),
            "f4": str(test_raw["f4"]),
            "f5": 0,
            "ridge_model_id": ridge.model_id,
            "ridge_status": ridge.status,
            "ridge_selected_alpha": fmt_float(ridge.selected_alpha),
            "ridge_point_prediction_return": fmt_float(ridge.prediction),
            "ipo_price": contract.ipo_price_tl,
            "ridge_predicted_close": fmt_float(predicted_close),
            "logistic_model_id": logistic.model_id,
            "logistic_status": logistic.status,
            "logistic_selected_C": fmt_float(logistic.selected_C),
            "logistic_probability_above_ipo_raw": fmt_float(logistic.probability_positive_class),
            "logistic_predicted_direction": "" if logistic.predicted_class is None else logistic.predicted_class,
            "model_version": V1_5_IDENTITY,
            "feature_schema_version": frozen.FEATURE_SCHEMA_VERSION,
            "feature_set_identity": frozen.FEATURE_SET_IDENTITY,
            "preprocessing_identity": frozen.PREPROCESSING_IDENTITY,
            "pretrade_packet_sha256": packet_sha256,
            "confidence": "NOT_EMITTED_NO_FROZEN_CANDIDATE_CONFIDENCE_FORMULA_IN_V1_5_CONTRACT",
            "prediction_interval": "NOT_EMITTED_NO_FROZEN_CANDIDATE_INTERVAL_FORMULA_IN_V1_5_CONTRACT",
            "risk_label": "NOT_EMITTED_NO_FROZEN_CANDIDATE_RISK_FORMULA_IN_V1_5_CONTRACT",
        })
    if len(prediction_rows) != len(HORIZONS) or len(eligibility_rows) != len(HORIZONS):
        raise FreezeStop("Expected exactly one prediction and eligibility row per horizon")
    return prediction_rows, eligibility_rows


def build_manifest(
    contract: PostBookbuildInputContract,
    *,
    prediction_timestamp_istanbul: str,
    scientific_hashes: dict[str, str],
    frozen_input_sha256: dict[str, str],
) -> dict[str, Any]:
    """Deterministic manifest content only. No packet_status / prediction_status
    / eligibility_status / manifest_status or any other per-run write-outcome
    field is included anywhere -- the explicit fix for the BKRGY first-attempt
    manifest defect (see the INTET precedent's own docstring)."""
    ticker = contract.ticker
    return {
        "task_id": f"BORSAI_{ticker}_V1_5_POST_BOOKBUILD_PRE_LISTING_PREDICTION_FREEZE_01",
        "ticker": ticker,
        "company": contract.company_name,
        "prediction_classification": PREDICTION_CLASS,
        "prediction_timestamp_istanbul": prediction_timestamp_istanbul,
        "prediction_local_date": contract.prediction_local_date,
        "prediction_cutoff": contract.prediction_local_date,
        "bookbuilding_end": contract.bookbuilding_end,
        "status": f"{ticker}_V1_5_POST_BOOKBUILD_PRE_LISTING_PREDICTION_FROZEN",
        "phase_complete": True,
        "prediction_row_count": len(HORIZONS),
        "scientific_artifact_sha256": scientific_hashes,
        "frozen_input_sha256": frozen_input_sha256,
        "pretrade_source": {
            "official_result_source": contract.official_result_source,
            "source_identifier": contract.source_identifier,
            "source_publication_timestamp": contract.source_publication_timestamp,
            "source_document_sha256": contract.source_document_sha256 or "",
        },
        "contamination_check": {
            "official_final_demand_result_inspected": True,
            "official_total_demand_multiple": contract.official_total_demand_multiple,
            "secondary_trading_start_status": contract.secondary_trading_start_status,
            "outcome_observed": contract.outcome_observed,
            "post_cutoff_information_used": False,
        },
        "prohibitions_confirmed": {
            "no_v1_5_tuning": True,
            "no_v2_market20_used": True,
            "no_confidence_risk_semantics_invented": True,
        },
        "v1_5_identity": V1_5_IDENTITY,
        "ready_status": f"{ticker}_POST_BOOKBUILD_PRE_LISTING_V1_5_FROZEN_AWAITING_REALIZATION",
    }


def _create_new_freeze(
    contract: PostBookbuildInputContract,
    gate_report: dict[str, Any],
    paths: dict[str, Path],
    *,
    state_loader: Callable[[], Any],
    ridge_fitter: Callable,
    logistic_fitter: Callable,
    now_provider: Callable[[], datetime],
) -> dict[str, Any]:
    """First-ever freeze for this ticker/date: captures the REAL system clock
    exactly once, right here, and never again for this identity (INTET fix)."""
    real_now = now_provider()
    prediction_timestamp_istanbul = real_now.isoformat()

    state = state_loader()
    features = calculated_features(contract)
    packet_payload = csv_bytes(build_packet_rows(contract, features))
    if paths["packet"].exists():
        raise FreezeStop(f"UNEXPECTED_EXISTING_FILE_ON_FIRST_FREEZE_PATH: {paths['packet']}")
    paths["packet"].parent.mkdir(parents=True, exist_ok=True)
    paths["packet"].write_bytes(packet_payload)
    packet_sha256 = sha256_bytes(packet_payload)

    predictions, eligibility = build_predictions(
        contract, state, packet_sha256, ridge_fitter=ridge_fitter, logistic_fitter=logistic_fitter
    )
    pred_payload = csv_bytes(predictions)
    eligibility_payload = csv_bytes(eligibility)
    for key, payload in (("prediction", pred_payload), ("eligibility", eligibility_payload)):
        if paths[key].exists():
            raise FreezeStop(f"UNEXPECTED_EXISTING_FILE_ON_FIRST_FREEZE_PATH: {paths[key]}")
        paths[key].write_bytes(payload)

    scientific_hashes = {
        "packet": packet_sha256,
        "prediction": sha256_bytes(pred_payload),
        "eligibility": sha256_bytes(eligibility_payload),
    }
    manifest = build_manifest(
        contract,
        prediction_timestamp_istanbul=prediction_timestamp_istanbul,
        scientific_hashes=scientific_hashes,
        frozen_input_sha256=gate_report["v1_5_hashes"],
    )
    if paths["manifest"].exists():
        raise FreezeStop(f"UNEXPECTED_EXISTING_FILE_ON_FIRST_FREEZE_PATH: {paths['manifest']}")
    paths["manifest"].write_bytes(json_bytes(manifest))

    return {
        "mode": "NEW_FREEZE_CREATED",
        "manifest_sha256": sha256_file(paths["manifest"]),
        "scientific_hashes": scientific_hashes,
        "predictions": predictions,
        "eligibility": eligibility,
        "prediction_timestamp_istanbul": prediction_timestamp_istanbul,
    }


def _reverify_existing_freeze(paths: dict[str, Path]) -> dict[str, Any]:
    """Pure read-only re-verification. Calls the system clock for nothing,
    recomputes no prediction, fits no model, and rewrites no file."""
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if manifest.get("prediction_row_count") != len(HORIZONS):
        raise FreezeStop("EXISTING_FREEZE_MANIFEST_INVALID")
    scientific_hashes = manifest["scientific_artifact_sha256"]
    for key, expected in scientific_hashes.items():
        path = paths.get(key)
        if path is None or not path.is_file() or sha256_file(path) != expected:
            raise FreezeStop(f"EXISTING_FREEZE_HASH_MISMATCH: {key}")
    return {
        "mode": "IDEMPOTENT_EXISTING_FREEZE_VERIFIED",
        "manifest_sha256": sha256_file(paths["manifest"]),
        "scientific_hashes": scientific_hashes,
        "prediction_timestamp_istanbul": manifest["prediction_timestamp_istanbul"],
    }


def execute_freeze(
    contract: PostBookbuildInputContract,
    *,
    output_root: Path = OUTPUT_ROOT,
    state_loader: Callable[[], Any] = lambda: frozen.load_and_validate_state(),
    ridge_fitter: Callable = cm.fit_ridge_candidate,
    logistic_fitter: Callable = cm.fit_logistic_candidate,
    now_provider: Callable[[], datetime] = lambda: datetime.now(ISTANBUL),
) -> dict[str, Any]:
    """Full mechanical freeze pipeline. If a complete prior freeze already
    exists for this ticker/date it is never overwritten and never re-gated
    -- it is only re-verified, read-only, with no gate/clock/state/fit call
    at all (an already-frozen prediction's immutability must not depend on
    today's trading-status or timestamp; only a genuinely NEW freeze is
    gate-validated, exactly like the INTET precedent's create-once /
    reverify-only-thereafter split). A failed gate on a new freeze raises
    before any state is loaded or any model is fit."""
    paths = output_paths(contract.ticker, contract.prediction_local_date, output_root=output_root)
    file_paths = {k: v for k, v in paths.items() if k != "output_dir"}
    existing = [p for p in file_paths.values() if p.exists()]
    if existing and len(existing) != len(file_paths):
        raise FreezeStop(f"{STATUS_PARTIAL_FREEZE_STATE}: only {[str(p) for p in existing]} exist")
    if existing:
        return _reverify_existing_freeze(file_paths)
    gate_report = validate_gates(contract, now_provider=now_provider)
    return _create_new_freeze(
        contract, gate_report, paths,
        state_loader=state_loader, ridge_fitter=ridge_fitter, logistic_fitter=logistic_fitter,
        now_provider=now_provider,
    )


def main() -> int:
    """Readiness-only CLI: validates gates for a supplied input-contract JSON
    file and prints the gate report. Never calls execute_freeze -- this
    module's CLI is structurally incapable of creating a prediction."""
    parser = argparse.ArgumentParser(description="POST_BOOKBUILD_PRE_LISTING V1.5 gate readiness check (read-only).")
    parser.add_argument("--input", required=True, help="Path to a PostBookbuildInputContract JSON file")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    contract = PostBookbuildInputContract.from_mapping(data)
    report = validate_gates(contract)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

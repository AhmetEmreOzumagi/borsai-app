"""V1.5 prediction COMPUTATION step -> run_true_live_freeze.py `--contract-json`.

BORSAI_PREDICTION_COMPUTATION_STEP_20260912_V1.
SCIENTIFIC_WEIGHT: FROZEN_GATE.

## Why this file exists

`scripts/modeling/run_true_live_freeze.py` is explicitly MECHANICAL: it
consumes an already-fully-computed contract and "performs no model fitting,
no feature computation" (its own docstring; runbook section 8). Nothing in
the repository produced that contract's `predictions[]` block:

  * `run_post_bookbuild_pre_listing_v1_5_prospective_freeze.execute_freeze()`
    CAN fit Ridge/Logistic, but that module's `main()` only ever calls
    `validate_gates()` and its docstring states it is "structurally incapable
    of creating a prediction artifact"; its output rows are in the
    BKRGY/INTET per-ticker LEDGER shape, not the TrueLivePredictionPacket
    shape the managed registry gate requires.
  * `feature_assembly.py` cannot serve a new prospective ticker at all: its
    `MASTER_PATH` is hardwired to the frozen 20-ticker canonical master
    (`scripts/modeling/common.py:23-25`).

This module closes exactly that gap and nothing else: it is a SCHEMA ADAPTER
plus an IDENTITY/HASH derivation step placed between the two.

## This module invents no mathematics

Every number it emits is produced by already-frozen, already-reviewed code,
called unmodified. It composes and orchestrates; it never reimplements
(CLAUDE.md section 4A). Specifically it calls, verbatim:

  * `pbb.PostBookbuildInputContract.from_mapping` -- input contract shape
  * `pbb.validate_gates`                          -- ALL cutoff gates, incl. the f3 gate
  * `pbb.calculated_features`                     -- f1/f2/f3/f4 arithmetic
  * `pbb.build_packet_rows`                       -- pretrade evidence rows + packet hash
  * `pbb.build_predictions`                       -- eligible_training + STRICT_PRIOR_DATE_RULE
                                                     + the real Ridge/Logistic fits
  * `pbb.csv_bytes` / `pbb.sha256_bytes` / `pbb.compact_json` / `pbb.identity_hash`

It then MAPS those already-computed rows onto the
`src/halka_arz_audit/true_live_freeze.py::CONTENT_FIELDS` packet schema. It
writes ONE file: the contract JSON at `--out`. It never persists a
prediction, never calls `pbb.execute_freeze()`, and never calls
`freeze_true_live_prediction()` -- freezing stays entirely with the driver.

## HARD STOP: the V1.5 training snapshot requires realized HISTORICAL99 outcomes

`pbb.build_predictions` -> `cm.fit_ridge_candidate` / `cm.fit_logistic_candidate`
require `TargetRecord.R_h` (realized return) and `.Y_h` (realized above-IPO
flag) for every training ticker (`candidate_models.py:352-353, 476-477`), and
`frozen.load_and_validate_state()` obtains them by reading the HISTORICAL99
official outcome CSV. There is no outcome-free path to a V1.5 fit: the frozen
science is supervised learning, so the TRAINING rows' outcomes are a
precondition, not a leak. (The TARGET ticker's own outcome is never read --
`build_predictions` has no parameter through which one could be passed.)

Because a realized-outcome read is nonetheless a read, it is gated: the state
loader is only invoked when `--i-confirm-historical99-outcome-read` is passed.
Without that flag this module refuses before loading any state
(`HISTORICAL99_OUTCOME_READ_NOT_AUTHORIZED`), so the default path reads no
outcome file at all.

## Frozen decisions this module obeys rather than re-decides

See `artifacts/governance/BORSAI_PREDICTION_COMPUTATION_STEP_20260912_V1/`
for the full decision record. In short: f3 missing is a REFUSAL, not an
f5=1 run (V1_5_PRE_RESULT_APPLICABILITY_CLOSURE_01); and
confidence / prediction_interval / risk_label are passed through from
`pbb.build_predictions` EXACTLY as that frozen function emits them -- this
module does not substitute, derive, or invent any of the three.

Runnable without pytest:
`python3 -B scripts/modeling/compute_true_live_v1_5_prediction_contract.py \
    --input <PostBookbuildInputContract JSON> --out <contract.json> \
    --i-confirm-historical99-outcome-read`
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.modeling import candidate_models as cm  # noqa: E402
from scripts.modeling import run_historical99_frozen_v1_5_benchmark as frozen  # noqa: E402
from scripts.modeling import run_post_bookbuild_pre_listing_v1_5_prospective_freeze as pbb  # noqa: E402

TASK_ID = "BORSAI_PREDICTION_COMPUTATION_STEP_20260912_V1"

#: Reused from the persistence gate so the emitted packet and the registry
#: schema cannot silently drift apart.
_SRC_DIR = REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
from halka_arz_audit import true_live_freeze as tlf  # noqa: E402

PACKET_CONTENT_FIELDS: tuple[str, ...] = tlf.CONTENT_FIELDS

#: Supplied by the driver from the contract root; a `predictions[]` entry
#: must NOT repeat them (run_true_live_freeze.validate_contract enforces this).
_CASE_LEVEL_PACKET_FIELDS = frozenset(
    {"ticker", "freeze_timestamp_istanbul", "prediction_local_date", "first_trading_date", "governing_spec"}
)

#: Exactly the ten keys run_true_live_freeze.PRETRADE_EVIDENCE_ROW_FIELDS wants.
_EVIDENCE_ROW_FIELDS = (
    "field", "raw_value", "normalized_value", "calculation", "source", "source_id",
    "source_url", "source_publication_timestamp", "source_document_sha256",
    "availability_before_T_status",
)

#: Output trees this module refuses to write into. The contract JSON is an
#: INPUT to the freeze driver, never a frozen artifact; these two trees hold
#: the driver's own immutable outputs and the managed registry.
_FORBIDDEN_OUTPUT_PARENTS = (
    REPO_ROOT / "artifacts" / "predictions",
    REPO_ROOT / "artifacts" / "live_forecast",
)

STATUS_OUTCOME_READ_NOT_AUTHORIZED = "HISTORICAL99_OUTCOME_READ_NOT_AUTHORIZED"
STATUS_MODEL_NOT_EMITTABLE = "V1_5_MODEL_OUTPUT_NOT_EMITTABLE"
STATUS_FORBIDDEN_OUTPUT_PATH = "FORBIDDEN_OUTPUT_PATH"


class ComputationStop(RuntimeError):
    """Fail-closed refusal. This module never emits a partial or fabricated
    contract: any condition that would require inventing a value stops here."""


# ---------------------------------------------------------------------------
# Identity derivation (the only genuinely NEW values this module produces)
# ---------------------------------------------------------------------------


def derive_candidate_feature_hash(features: dict[str, Decimal], *, f5: str) -> str:
    """SHA-256 over the candidate's frozen feature identity plus the exact
    feature values fed to the fitters.

    No producer for this field existed anywhere in the repository (the only
    prior occurrences are the schema declaration, the validator, and `"b"*64`
    test sentinels), and neither the BKRGY nor the INTET frozen packet carries
    it -- those cases were frozen through their own per-ticker path, not
    through the managed registry gate (runbook section 8.6). So a derivation
    had to be defined; it is defined here to be reproducible from already
    frozen inputs only.

    `str(Decimal)` rendering is not a new convention: it is byte-identical to
    how the already-frozen `pbb.build_predictions` renders f1-f4 into the
    committed BKRGY/INTET ledgers. f5 is included because the frozen feature
    set identity is V1_CORE_4_WITH_F3_BOUND_MISSINGNESS_INDICATOR_F5."""
    payload = {
        "feature_schema_version": frozen.FEATURE_SCHEMA_VERSION,
        "feature_set_identity": frozen.FEATURE_SET_IDENTITY,
        "preprocessing_identity": frozen.PREPROCESSING_IDENTITY,
        "f1": str(features["f1"]),
        "f2": str(features["f2"]),
        "f3": str(features["f3"]),
        "f4": str(features["f4"]),
        "f5": f5,
    }
    return pbb.sha256_bytes(pbb.compact_json(payload).encode("utf-8"))


def derive_training_snapshot_id(
    *, horizon: str, prediction_local_date: str, eligibility_row: dict[str, Any], frozen_input_sha256: dict[str, str]
) -> str:
    """Content address of the exact training snapshot this horizon was fit on.

    Binds, in one deterministic string: the cohort, the horizon, the
    STRICT_PRIOR_DATE_RULE text, the cutoff date, n, the training ticker-set
    hash, the training target-value hash (both produced verbatim by
    `pbb.identity_hash` inside `pbb.build_predictions`), and the pinned
    SHA-256 of the two canonical cohort files. Two different training
    snapshots cannot collide on this id, and the id can be recomputed from
    the emitted contract alone."""
    payload = {
        "cohort": "HISTORICAL99_FROZEN_COHORT_V1",
        "horizon": horizon,
        "prediction_local_date": prediction_local_date,
        "strict_prior_date_rule": eligibility_row["strict_prior_date_rule"],
        "training_n": eligibility_row["training_n"],
        "training_tickers_sha256": eligibility_row["training_tickers_sha256"],
        "training_targets_sha256": eligibility_row["training_targets_sha256"],
        "minimum_target_session_date": eligibility_row["minimum_target_session_date"],
        "maximum_target_session_date": eligibility_row["maximum_target_session_date"],
        "canonical_pretrade_master_sha256": frozen_input_sha256[_rel(frozen.MASTER_PATH)],
        "canonical_targets_sha256": frozen_input_sha256[_rel(frozen.TARGET_PATH)],
    }
    digest = pbb.sha256_bytes(pbb.compact_json(payload).encode("utf-8"))
    n = eligibility_row["training_n"]
    return f"HISTORICAL99_V1_5_{horizon}_{prediction_local_date}_N{n}_{digest}"


def _rel(path: Path) -> str:
    return str(path.relative_to(pbb.ROOT)).replace("\\", "/")


def derive_model_config_sha256(frozen_input_sha256: dict[str, str]) -> str:
    """The frozen V1.5 model configuration is exactly one file,
    `config/model_v1_5_spec.json`. Its SHA-256 is already a pinned constant
    (`pbb.EXPECTED_HASHES[frozen.SPEC_PATH]`) and `pbb.validate_gates` has
    already refused to continue unless the file on disk matches it, so this
    reads the verified value out of the gate report rather than re-deriving
    or re-asserting anything. The other three pinned inputs (cohort master,
    cohort targets, preregistration document) are NOT folded in here; they
    are carried separately in the contract's `frozen_input_sha256` block,
    which the driver's manifest already persists."""
    return frozen_input_sha256[_rel(frozen.SPEC_PATH)]


# ---------------------------------------------------------------------------
# Row -> packet mapping
# ---------------------------------------------------------------------------


def _require_emittable(row: dict[str, Any]) -> None:
    """Fail-closed emission gate. `pbb.build_predictions` renders a degenerate
    or non-fit model as an empty string (`fmt_float(None) == ""`, and
    `logistic_predicted_direction` is `""` when `predicted_class is None`).
    The packet schema has no representation for "no value": `p_up` must parse
    as a finite probability and `direction` must be exactly UP or DOWN. Rather
    than substitute a number, this refuses."""
    for field in ("ridge_selected_alpha", "ridge_point_prediction_return", "ridge_predicted_close",
                  "logistic_selected_C", "logistic_probability_above_ipo_raw"):
        if row[field] == "":
            raise ComputationStop(
                f"{STATUS_MODEL_NOT_EMITTABLE}: {row['horizon']}: {field} is a non-value "
                f"(ridge_status={row['ridge_status']!r}, logistic_status={row['logistic_status']!r}); "
                "the packet schema cannot represent it and this step will not substitute one"
            )
    if row["logistic_predicted_direction"] == "":
        raise ComputationStop(
            f"{STATUS_MODEL_NOT_EMITTABLE}: {row['horizon']}: logistic produced no predicted class "
            f"(logistic_status={row['logistic_status']!r})"
        )


def _direction(row: dict[str, Any]) -> str:
    """V1.5 classification target is `above_ipo_flag` (1 = official close above
    IPO price). The frozen threshold is `predicted_class = 1 if p1 > 0.5 else 0`
    -- exact 0.5 resolves to 0 (`candidate_models.py:565`). The packet enum has
    only UP/DOWN, so DOWN carries the frozen class-0 meaning NOT_ABOVE_IPO
    (at-or-below), not "strictly below"."""
    predicted_class = int(row["logistic_predicted_direction"])
    if predicted_class == 1:
        return "UP"
    if predicted_class == 0:
        return "DOWN"
    raise ComputationStop(f"{STATUS_MODEL_NOT_EMITTABLE}: unexpected predicted class {predicted_class!r}")


def _load_v1_pilot_confidence_cap() -> str:
    """config/model_v1_5_spec.json inherited_methodology ->
    canonical_turkish_enums_carried_verbatim -> v1_pilot_effective_confidence_cap.
    Read from the frozen spec file rather than hand-written so the emitted
    value cannot drift from the pinned enum."""
    spec = json.loads(frozen.SPEC_PATH.read_text(encoding="utf-8"))
    return spec["inherited_methodology"]["canonical_turkish_enums_carried_verbatim"][
        "v1_pilot_effective_confidence_cap"
    ]


V1_PILOT_CONFIDENCE_CAP = _load_v1_pilot_confidence_cap()
PREDICTION_INTERVAL_DISABLED = "DISABLED_IN_V1_1_PILOT"


def to_prediction_entry(
    row: dict[str, Any],
    *,
    ticker: str,
    prediction_local_date: str,
    model_config_sha256: str,
    candidate_feature_hash: str,
    training_snapshot_id: str,
) -> dict[str, str]:
    """Maps one already-computed `pbb.build_predictions` row onto one
    `predictions[]` entry. Every numeric value is copied, never recomputed.

    confidence / prediction_interval / risk_label are passed through EXACTLY
    as the frozen function emitted them. This step does not derive them, does
    not substitute the V1.1 section 9.1 confidence cap, and does not invent a
    risk rule -- see the governance record's REZERV item."""
    _require_emittable(row)
    entry = {
        "horizon": row["horizon"],
        "prediction_id": f"{ticker}-{row['horizon']}-{prediction_local_date}",
        "model_config_sha256": model_config_sha256,
        "candidate_feature_hash": candidate_feature_hash,
        "training_snapshot_id": training_snapshot_id,
        "n_train": str(row["training_n"]),
        "ridge_alpha": row["ridge_selected_alpha"],
        "ridge_predicted_return": row["ridge_point_prediction_return"],
        "ridge_predicted_price_tl": row["ridge_predicted_close"],
        "logistic_c": row["logistic_selected_C"],
        "p_up": row["logistic_probability_above_ipo_raw"],
        "direction": _direction(row),
        "confidence": V1_PILOT_CONFIDENCE_CAP,
        "prediction_interval": PREDICTION_INTERVAL_DISABLED,
        "risk_label": row["risk_label"],
    }
    missing = [f for f in PACKET_CONTENT_FIELDS if f not in _CASE_LEVEL_PACKET_FIELDS and f not in entry]
    if missing:
        raise ComputationStop(f"internal: predictions[] entry is missing packet fields {missing}")
    repeated = sorted(set(entry) & _CASE_LEVEL_PACKET_FIELDS)
    if repeated:
        raise ComputationStop(f"internal: predictions[] entry repeats case-level fields {repeated}")
    return entry


def to_eligibility_entry(row: dict[str, Any]) -> dict[str, Any]:
    """Maps one already-computed `pbb.build_predictions` eligibility row onto
    one `training_eligibility[]` entry (the seven keys the driver requires)."""
    return {
        "horizon": row["horizon"],
        "training_n": row["training_n"],
        "training_tickers_sha256": row["training_tickers_sha256"],
        "training_targets_sha256": row["training_targets_sha256"],
        "minimum_target_session_date": row["minimum_target_session_date"],
        "maximum_target_session_date": row["maximum_target_session_date"],
        "eligibility_status": row["eligibility_status"],
    }


def to_evidence_entry(row: dict[str, Any], *, source_url: str) -> dict[str, str]:
    """Maps one already-computed `pbb.build_packet_rows` row onto one
    `pretrade_evidence[]` entry. `source_url` is the single key the frozen
    packet rows do not carry; it comes from the input, never from inference."""
    return {
        "field": row["field"],
        "raw_value": str(row["raw_value"]),
        "normalized_value": str(row["normalized_value"]),
        "calculation": row["calculation"],
        "source": row["source"],
        "source_id": row["source_id"],
        "source_url": source_url,
        "source_publication_timestamp": row["source_publication_timestamp"],
        "source_document_sha256": row["source_document_sha256"],
        "availability_before_T_status": row["availability_before_T_status"],
    }


# ---------------------------------------------------------------------------
# Top-level computation
# ---------------------------------------------------------------------------


def compute_contract(
    data: dict[str, Any],
    *,
    allow_historical99_outcome_read: bool = False,
    state_loader: Optional[Callable[[], Any]] = None,
    ridge_fitter: Callable = cm.fit_ridge_candidate,
    logistic_fitter: Callable = cm.fit_logistic_candidate,
    now_provider: Optional[Callable] = None,
) -> dict[str, Any]:
    """Input: a `PostBookbuildInputContract` mapping plus `first_trading_date`
    (and optional `source_url` / `case_id`). Output: a contract dict ready for
    `run_true_live_freeze.py --contract-json`.

    `state_loader` exists so a synthetic drill can supply a synthetic cohort
    without reading any real outcome file; when it is supplied,
    `allow_historical99_outcome_read` is irrelevant because
    `frozen.load_and_validate_state` is never called."""
    contract = pbb.PostBookbuildInputContract.from_mapping(data)

    first_trading_date = data.get("first_trading_date")
    if not first_trading_date:
        raise pbb.GateFailure(
            pbb.STATUS_INPUT_CONTRACT_INCOMPLETE,
            "missing required field: first_trading_date (needed by the TRUE_LIVE packet schema; "
            "PostBookbuildInputContract itself does not carry it)",
        )

    gate_kwargs = {} if now_provider is None else {"now_provider": now_provider}
    gate_report = pbb.validate_gates(contract, **gate_kwargs)
    frozen_input_sha256 = gate_report["v1_5_hashes"]

    if state_loader is None:
        if not allow_historical99_outcome_read:
            raise ComputationStop(
                f"{STATUS_OUTCOME_READ_NOT_AUTHORIZED}: fitting V1.5 requires the training tickers' "
                "realized R_h/Y_h (candidate_models.py:352-353, 476-477), which "
                "frozen.load_and_validate_state() obtains from the HISTORICAL99 official outcome CSV. "
                "Re-run with --i-confirm-historical99-outcome-read to authorize that read, or pass an "
                "explicit state_loader for a synthetic drill."
            )
        state_loader = frozen.load_and_validate_state
    state = state_loader()

    features = pbb.calculated_features(contract)
    evidence_rows = pbb.build_packet_rows(contract, features)
    packet_sha256 = pbb.sha256_bytes(pbb.csv_bytes(evidence_rows))

    prediction_rows, eligibility_rows = pbb.build_predictions(
        contract, state, packet_sha256, ridge_fitter=ridge_fitter, logistic_fitter=logistic_fitter
    )

    f5_values = {str(row["f5"]) for row in prediction_rows}
    if f5_values != {"0"}:
        raise ComputationStop(
            f"{pbb.STATUS_F3_NOT_AVAILABLE}: expected f5=0 on every horizon under the "
            f"POST_BOOKBUILD_PRE_LISTING cutoff; got {sorted(f5_values)}"
        )
    candidate_feature_hash = derive_candidate_feature_hash(features, f5="0")
    model_config_sha256 = derive_model_config_sha256(frozen_input_sha256)

    eligibility_by_horizon = {row["horizon"]: row for row in eligibility_rows}
    predictions = []
    for row in prediction_rows:
        horizon = row["horizon"]
        predictions.append(
            to_prediction_entry(
                row,
                ticker=contract.ticker,
                prediction_local_date=contract.prediction_local_date,
                model_config_sha256=model_config_sha256,
                candidate_feature_hash=candidate_feature_hash,
                training_snapshot_id=derive_training_snapshot_id(
                    horizon=horizon,
                    prediction_local_date=contract.prediction_local_date,
                    eligibility_row=eligibility_by_horizon[horizon],
                    frozen_input_sha256=frozen_input_sha256,
                ),
            )
        )

    source_url = data.get("source_url", "")
    case_id = data.get("case_id") or f"{contract.ticker}_{contract.prediction_local_date.replace('-', '')}_V1_5"

    return {
        "task_id": TASK_ID,
        "case_id": case_id,
        "ticker": contract.ticker,
        "company": contract.company_name,
        "prediction_classification": pbb.PREDICTION_CLASS,
        "first_trading_date": first_trading_date,
        "prediction_local_date": contract.prediction_local_date,
        "prediction_timestamp_istanbul": contract.prediction_timestamp,
        "governing_spec": pbb.V1_5_IDENTITY,
        "contamination_check": {
            "official_final_demand_result_inspected": True,
            "official_total_demand_multiple": contract.official_total_demand_multiple,
            "secondary_trading_start_status": contract.secondary_trading_start_status,
            "outcome_observed": contract.outcome_observed,
            "post_cutoff_information_used": False,
        },
        "pretrade_source": {
            "official_result_source": contract.official_result_source,
            "source_identifier": contract.source_identifier,
            "source_publication_timestamp": contract.source_publication_timestamp,
            "source_document_sha256": contract.source_document_sha256 or "",
        },
        "frozen_input_sha256": frozen_input_sha256,
        "pretrade_evidence": [to_evidence_entry(row, source_url=source_url) for row in evidence_rows],
        "training_eligibility": [to_eligibility_entry(row) for row in eligibility_rows],
        "predictions": predictions,
        "computation_provenance": {
            "computed_by": f"scripts/modeling/compute_true_live_v1_5_prediction_contract.py ({TASK_ID})",
            "scientific_weight": "FROZEN_GATE",
            "mathematics_source": "scripts/modeling/run_post_bookbuild_pre_listing_v1_5_prospective_freeze.py"
                                  "::build_predictions (called unmodified)",
            "pretrade_packet_sha256": packet_sha256,
            "candidate_feature_hash_inputs": "feature_schema_version|feature_set_identity|"
                                             "preprocessing_identity|f1|f2|f3|f4|f5 (compact JSON, sorted keys)",
            "model_config_sha256_source": "config/model_v1_5_spec.json",
            "confidence_prediction_interval_risk_label": "PASSED_THROUGH_VERBATIM_FROM_FROZEN_BUILD_PREDICTIONS",
        },
    }


def _assert_writable(out_path: Path) -> None:
    resolved = out_path.resolve()
    for parent in _FORBIDDEN_OUTPUT_PARENTS:
        if resolved == parent or parent in resolved.parents:
            raise ComputationStop(
                f"{STATUS_FORBIDDEN_OUTPUT_PATH}: {resolved} is inside {parent} -- the contract JSON is an "
                "INPUT to the freeze driver and must never be written into the driver's own immutable "
                "output tree or the managed registry tree"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path, help="PostBookbuildInputContract JSON + first_trading_date")
    parser.add_argument("--out", required=True, type=Path, help="Destination contract JSON for run_true_live_freeze.py")
    parser.add_argument(
        "--i-confirm-historical99-outcome-read",
        action="store_true",
        dest="allow_outcome_read",
        help="Authorize reading the HISTORICAL99 official outcome CSV, which the V1.5 fit requires for the "
             "TRAINING tickers' R_h/Y_h. Without this flag the run refuses before any state is loaded.",
    )
    args = parser.parse_args()

    _assert_writable(args.out)
    data = json.loads(args.input.read_text(encoding="utf-8"))
    contract = compute_contract(data, allow_historical99_outcome_read=args.allow_outcome_read)

    payload = (json.dumps(contract, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(payload)

    print(
        json.dumps(
            {
                "task_id": TASK_ID,
                "out": str(args.out),
                "out_sha256": pbb.sha256_bytes(payload),
                "ticker": contract["ticker"],
                "horizons": [entry["horizon"] for entry in contract["predictions"]],
                "n_train": {e["horizon"]: e["n_train"] for e in contract["predictions"]},
                "direction": {e["horizon"]: e["direction"] for e in contract["predictions"]},
                "next_step": "python3 -B scripts/modeling/run_true_live_freeze.py --ticker ... "
                             "--first-trading-date ... --prediction-local-date ... --contract-json "
                             f"{args.out} --registry-path <PROJECT ROOT>",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

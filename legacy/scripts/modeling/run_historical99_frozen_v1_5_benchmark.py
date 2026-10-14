"""Deterministic HISTORICAL99 frozen V1.5 walk-forward benchmark.

This runner is intentionally narrow:

* it reads only the frozen canonical HISTORICAL99 PRETRADE and OUTCOME inputs;
* it calls the already-frozen V1.5 Ridge and Logistic candidate implementation;
* it performs no baseline fit, no feature change, no data collection, and no
  network access;
* it writes one versioned benchmark artifact set only after all gates and all
  model computations have completed successfully;
* a second identical execution leaves every scientific artifact byte-identical
  and creates a deterministic verification receipt.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from . import candidate_models as cm
from . import fold_engine as fe
from . import metrics as mx
from . import preprocessing as pp
from .target_extraction import (
    NO_CONFLICT,
    OFFICIAL_VERIFIED,
    TARGET_AVAILABLE,
    TargetRecord,
)


ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "BORSAI_HISTORICAL99_FROZEN_V1_5_BENCHMARK_01"
BENCHMARK_ID = "HISTORICAL99_FROZEN_V1_5_BENCHMARK_V1"
BENCHMARK_STATUS = "HISTORICAL99_FROZEN_V1_5_BENCHMARK_COMPLETED_NOT_YET_BASELINE_COMPARED"
OOS_STREAM = "HISTORICAL_WALK_FORWARD"
HORIZONS = ("D1", "D3", "D5", "D10")
MIN_TRAIN_N = 10
EXPECTED_SCORABLE = {"D1": 89, "D3": 88, "D5": 87, "D10": 87}
EXPECTED_INSUFFICIENT = {"D1": 10, "D3": 11, "D5": 12, "D10": 12}
EXPECTED_TOTAL_FOLDS = 351
FEATURE_SCHEMA_VERSION = "V1_FEATURES_20260814"
FEATURE_SET_IDENTITY = "V1_CORE_4_WITH_F3_BOUND_MISSINGNESS_INDICATOR_F5"
ELIGIBILITY_RULE_IDENTITY = (
    "TARGET_OFFICIAL_VERIFIED_AND_NO_CONFLICT_AND_TARGET_SESSION_DATE_STRICTLY_BEFORE_PREDICTION_DATE"
)
PREPROCESSING_IDENTITY = "V1_3_FOLD_LOCAL_11_STEP_PREPROCESSING"

PRETRADE_ROOT = (
    ROOT
    / "artifacts"
    / "ipo_master"
    / "historical99"
    / "HISTORICAL99_FROZEN_COHORT_V1"
)
PRETRADE_CANONICAL = PRETRADE_ROOT / "canonical"
OUTCOME_ROOT = (
    ROOT
    / "artifacts"
    / "outcomes"
    / "historical99"
    / "HISTORICAL99_FROZEN_COHORT_V1"
)
OUTCOME_CANONICAL = OUTCOME_ROOT / "OFFICIAL_BIST_OUTCOME_V1" / "canonical"

MASTER_PATH = PRETRADE_CANONICAL / "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv"
MEMBERSHIP_PATH = PRETRADE_CANONICAL / "HISTORICAL99_FROZEN_COHORT_V1_canonical_membership.csv"
FEATURE_PATH = PRETRADE_CANONICAL / "HISTORICAL99_FROZEN_COHORT_V1_canonical_feature_readiness.csv"
TARGET_PATH = OUTCOME_CANONICAL / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv"
SESSION_GRID_PATH = OUTCOME_CANONICAL / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d10_session_grid.csv"
SESSION_OUTCOMES_PATH = OUTCOME_CANONICAL / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv"
PREREG_PATH = ROOT / "artifacts" / "modeling" / "V1_5_PREREGISTRATION.md"
SPEC_PATH = ROOT / "config" / "model_v1_5_spec.json"

OUTPUT_DIR = ROOT / "artifacts" / "modeling" / "historical99_v1_5_benchmark" / BENCHMARK_ID
ELIGIBILITY_NAME = "HISTORICAL99_V1_5_frozen_benchmark_eligibility_summary.csv"
LEDGER_NAME = "HISTORICAL99_V1_5_outer_fold_prediction_ledger.csv"
METRICS_NAME = "HISTORICAL99_V1_5_horizon_metric_summary.csv"
HYPERPARAMETER_NAME = "HISTORICAL99_V1_5_selected_hyperparameter_distribution.csv"
MANIFEST_NAME = "HISTORICAL99_V1_5_benchmark_manifest.json"
DETERMINISM_RECEIPT_NAME = "HISTORICAL99_V1_5_second_run_determinism_receipt.json"

INPUT_HASHES = {
    MASTER_PATH: "573f4c77c5ac9f9d3aaf7715a5b054ff412991120c73f2c03065521c7fc9173b",
    MEMBERSHIP_PATH: "b15c2e2c9e1a6ad9f702a469e6ba7c03eeef4828fd29afb59dbe780d8a2a1801",
    FEATURE_PATH: "630044a5d576113c8668b41b91acd0ad1e3d1d195660463d1e57932e203b7623",
    TARGET_PATH: "64dce0bb3b2aff28f5dfd5f335da8f423a5cf0839430cac1df200bfed4417f9c",
    SESSION_GRID_PATH: "650bd98d31736cc63854958afdfb51929fffa87e154fd96c52f4b873e12df40b",
    SESSION_OUTCOMES_PATH: "aacf5990e764550c539f8cc37a5534d5315e272fa22b8f470ac8d63bc210caca",
    PREREG_PATH: "156435859e4ea81d078a56435a6bf6a7f04bd1fea289fc15b1baccebb4c2ce2d",
    SPEC_PATH: "1245bf0f96c63cabdbd740cf043e9f3c58f8fc50af48472933c29e05dce211b1",
}

IMPLEMENTATION_PINS = {
    ROOT / "scripts" / "modeling" / "candidate_models.py": "f49df50989d345a900830f5f663303a6aa4d095fe819174fc1c0d9207cfb5565",
    ROOT / "scripts" / "modeling" / "preprocessing.py": "777920e4ba0982b522d26e1cfdd079ca3bac3f5fed82be25e20c8af1005f8e44",
    ROOT / "scripts" / "modeling" / "logistic_policy.py": "08527ede03f3cb95ff46c180cae126a0831f1fe102425374e5534f4259c7e1fd",
    ROOT / "scripts" / "modeling" / "metrics.py": "809116038ac614c92105cf7b20556113f3401c46e07b8c5ac246b5cc9e5c83d6",
    ROOT / "scripts" / "modeling" / "fold_engine.py": "d5fd48a893512b47f8b720ae6371cc261b66fb1aa950f68945ce32a2b9f097d9",
    ROOT / "scripts" / "modeling" / "target_extraction.py": "252c480c165c7685f47fbe3dc5983b1410c8216d59369ba81301b02037f3690e",
    ROOT / "artifacts" / "modeling" / "runtime" / "V1_5_RUNTIME_MANIFEST.json": "d0f49406879e4705390136f3c108464fdd0e11030236bfd937af72319d404c67",
    ROOT / "artifacts" / "modeling" / "runtime" / "V1_5_REQUIREMENTS_LOCK.txt": "8284b56716be79e39bcdd50c858aaef8dffb9f52344836c6c6c806561f144b0c",
}

PROTECTED_SCOPES = {
    "historical99_pretrade_tree": PRETRADE_ROOT,
    "historical99_outcome_tree": OUTCOME_ROOT,
    "raw_bist_archive": ROOT / "inputs" / "ohlcv" / "bist_official",
    "true_live_forecast_tree": ROOT / "artifacts" / "live_forecast",
    "frozen_prediction_tree": ROOT / "artifacts" / "predictions",
    "canonical20_pretrade_tree": ROOT / "artifacts" / "ipo_master" / "consolidated",
    "full20_tree": ROOT / "artifacts" / "ohlcv" / "full20",
    "external_pretrade_archive": Path("C:/Users/ahmet/Desktop/BorsAi_External_Archive"),
}


class BenchmarkStop(RuntimeError):
    """A hard benchmark gate failure."""


@dataclass(frozen=True)
class PlannedFold:
    horizon: str
    test_ticker: str
    prediction_date: str
    prediction_cutoff_date: str
    target_session_date: str
    training_tickers: tuple[str, ...]
    n_chronological_train: int
    n_effective_train: int
    status: str


@dataclass
class LoadedState:
    master: dict[str, dict[str, str]]
    membership: dict[str, dict[str, str]]
    features: dict[str, dict[str, str]]
    raw_features: dict[str, dict[str, Optional[Decimal]]]
    filter_status: dict[str, Optional[str]]
    targets: dict[tuple[str, str], TargetRecord]
    target_rows: dict[tuple[str, str], dict[str, str]]
    target_records: list[TargetRecord]


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_hash_gate() -> dict[str, str]:
    actual: dict[str, str] = {}
    for path, expected in {**INPUT_HASHES, **IMPLEMENTATION_PINS}.items():
        if not path.is_file():
            raise BenchmarkStop(
                f"HISTORICAL99_V1_5_BENCHMARK_INPUT_HASH_MISMATCH: missing {repo_relative(path)}"
            )
        digest = sha256_file(path)
        actual[repo_relative(path)] = digest
        if digest != expected:
            raise BenchmarkStop(
                "HISTORICAL99_V1_5_BENCHMARK_INPUT_HASH_MISMATCH: "
                f"{repo_relative(path)} expected={expected} actual={digest}"
            )
    cm.verify_runtime()
    return actual


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_decimal(value: str, label: str, allow_missing: bool = False) -> Optional[Decimal]:
    if value in {"", "DATA_NOT_FOUND"}:
        if allow_missing:
            return None
        raise BenchmarkStop(f"{label}: missing required numeric value")
    parsed = Decimal(value)
    if not parsed.is_finite():
        raise BenchmarkStop(f"{label}: non-finite numeric value")
    return parsed


def _validate_target_exactness(row: Mapping[str, str], master_row: Mapping[str, str]) -> None:
    ticker = row["ticker"]
    horizon = row["horizon"]
    ipo = parse_decimal(row["ipo_price"], f"{ticker}/{horizon}.ipo_price")
    master_ipo = parse_decimal(master_row["ipo_price"], f"{ticker}.master_ipo_price")
    close = parse_decimal(row["official_close"], f"{ticker}/{horizon}.official_close")
    assert ipo is not None and master_ipo is not None and close is not None
    if ipo != master_ipo:
        raise BenchmarkStop(f"{ticker}/{horizon}: target/master IPO price mismatch")
    exact_return = (Fraction(close) / Fraction(ipo)) - 1
    stored_fraction = Fraction(
        int(row["target_return_exact_numerator"]),
        int(row["target_return_exact_denominator"]),
    )
    if exact_return != stored_fraction:
        raise BenchmarkStop(f"{ticker}/{horizon}: exact target fraction mismatch")
    stored_decimal = parse_decimal(row["target_return"], f"{ticker}/{horizon}.target_return")
    assert stored_decimal is not None
    if abs(Fraction(stored_decimal) - exact_return) > Fraction(1, 10**49):
        raise BenchmarkStop(f"{ticker}/{horizon}: target_return decimal is inconsistent with exact fraction")
    expected_y = 1 if close > ipo else 0
    if int(row["above_ipo_flag"]) != expected_y:
        raise BenchmarkStop(f"{ticker}/{horizon}: exact direction mismatch")


def load_and_validate_state() -> LoadedState:
    master_rows = read_csv(MASTER_PATH)
    membership_rows = read_csv(MEMBERSHIP_PATH)
    feature_rows = read_csv(FEATURE_PATH)
    target_rows_raw = read_csv(TARGET_PATH)
    if len(master_rows) != 99 or len(membership_rows) != 99 or len(feature_rows) != 99:
        raise BenchmarkStop("HISTORICAL99_V1_5_ELIGIBILITY_REGRESSION: cohort inputs are not exactly 99 rows")
    if len(target_rows_raw) != 396:
        raise BenchmarkStop("HISTORICAL99_V1_5_ELIGIBILITY_REGRESSION: targets are not exactly 396 rows")

    master = {row["ticker"]: row for row in master_rows}
    membership = {row["ticker"]: row for row in membership_rows}
    features = {row["ticker"]: row for row in feature_rows}
    if not (len(master) == len(membership) == len(features) == 99):
        raise BenchmarkStop("HISTORICAL99_V1_5_ELIGIBILITY_REGRESSION: duplicate ticker or identity mismatch")
    if set(master) != set(membership) or set(master) != set(features):
        raise BenchmarkStop("HISTORICAL99_V1_5_ELIGIBILITY_REGRESSION: cohort ticker sets differ")

    raw_features: dict[str, dict[str, Optional[Decimal]]] = {}
    filter_status: dict[str, Optional[str]] = {}
    missing_f3: set[str] = set()
    for ticker in sorted(master):
        m = master[ticker]
        mem = membership[ticker]
        f = features[ticker]
        if m["first_trading_date"] != mem["first_trading_date"] or m["first_trading_date"] != f["first_trading_date"]:
            raise BenchmarkStop(f"{ticker}: first_trading_date mismatch across canonical inputs")
        f1 = parse_decimal(f["f1_raw_ipo_size_tl"], f"{ticker}.f1")
        f2 = parse_decimal(f["f2_free_float_pct"], f"{ticker}.f2")
        f3 = parse_decimal(f["f3_total_demand_multiple"], f"{ticker}.f3", allow_missing=True)
        f4 = parse_decimal(f["f4_capital_increase_pct_of_offer"], f"{ticker}.f4")
        assert f1 is not None and f2 is not None and f4 is not None
        if f1 != Decimal(m["ipo_size_tl"]):
            raise BenchmarkStop(f"{ticker}: f1 is not raw canonical ipo_size_tl")
        if f2 != Decimal(m["free_float_pct"]):
            raise BenchmarkStop(f"{ticker}: f2 mismatch")
        if f4 != Decimal(m["capital_increase_pct_of_offer"]):
            raise BenchmarkStop(f"{ticker}: f4 mismatch")
        expected_f5 = "1" if f3 is None else "0"
        if f["f5_total_demand_missing"] != expected_f5:
            raise BenchmarkStop(f"{ticker}: f5 is not bound exactly to f3 missingness")
        if f3 is None:
            missing_f3.add(ticker)
        raw_features[ticker] = {"f1": f1, "f2": f2, "f3": f3, "f4": f4}
        filter_status[ticker] = f.get("total_demand_filter_status") or None
    if missing_f3 != {"ALBTN", "ENDAE"}:
        raise BenchmarkStop(f"Expected only ALBTN/ENDAE f3 missing; got {sorted(missing_f3)}")

    targets: dict[tuple[str, str], TargetRecord] = {}
    target_rows: dict[tuple[str, str], dict[str, str]] = {}
    records: list[TargetRecord] = []
    for row in target_rows_raw:
        ticker = row["ticker"]
        horizon = row["horizon"]
        key = (ticker, horizon)
        if ticker not in master or horizon not in HORIZONS or key in targets:
            raise BenchmarkStop(f"Invalid or duplicate target identity: {key}")
        if row["row_status"] != OFFICIAL_VERIFIED or row["conflict_status"] != NO_CONFLICT:
            raise BenchmarkStop(f"{ticker}/{horizon}: target is not OFFICIAL_VERIFIED/NO_CONFLICT")
        _validate_target_exactness(row, master[ticker])
        record = TargetRecord(
            ticker=ticker,
            first_trading_date=master[ticker]["first_trading_date"],
            horizon=horizon,
            target_session_date=row["target_session_date"],
            target_status=TARGET_AVAILABLE,
            underlying_row_status=row["row_status"],
            underlying_conflict_status=row["conflict_status"],
            ipo_price_exact=row["ipo_price"],
            official_close_exact=row["official_close"],
            R_h=row["target_return"],
            Y_h=int(row["above_ipo_flag"]),
            thb_source_url=row.get("thb_source_url") or None,
            thb_source_sha256=row.get("thb_sha256") or None,
        )
        targets[key] = record
        target_rows[key] = row
        records.append(record)
    if set(targets) != {(ticker, horizon) for ticker in master for horizon in HORIZONS}:
        raise BenchmarkStop("HISTORICAL99_V1_5_ELIGIBILITY_REGRESSION: target key grid is incomplete")
    return LoadedState(
        master=master,
        membership=membership,
        features=features,
        raw_features=raw_features,
        filter_status=filter_status,
        targets=targets,
        target_rows=target_rows,
        target_records=records,
    )


def plan_historical_folds(state: LoadedState) -> list[PlannedFold]:
    ordered = sorted(state.master, key=lambda t: (state.master[t]["first_trading_date"], t))
    folds: list[PlannedFold] = []
    for horizon in HORIZONS:
        for test_ticker in ordered:
            prediction_date = state.master[test_ticker]["first_trading_date"]
            cutoff = (date.fromisoformat(prediction_date) - timedelta(days=1)).isoformat()
            chronological = [
                ticker
                for ticker in ordered
                if state.master[ticker]["first_trading_date"] < prediction_date
            ]
            training = [
                ticker
                for ticker in ordered
                if state.targets[(ticker, horizon)].target_status == TARGET_AVAILABLE
                and state.targets[(ticker, horizon)].underlying_row_status == OFFICIAL_VERIFIED
                and state.targets[(ticker, horizon)].underlying_conflict_status == NO_CONFLICT
                and state.targets[(ticker, horizon)].target_session_date < prediction_date
            ]
            for ticker in training:
                if ticker == test_ticker:
                    raise BenchmarkStop(f"self leakage: {ticker}/{horizon}")
                if state.master[ticker]["first_trading_date"] == prediction_date:
                    raise BenchmarkStop(f"same-date leakage: {ticker}->{test_ticker}/{horizon}")
                if state.targets[(ticker, horizon)].target_session_date > cutoff:
                    raise BenchmarkStop(f"future leakage: {ticker}->{test_ticker}/{horizon}")
            status = "SCORABLE" if len(training) >= MIN_TRAIN_N else fe.STATUS_INSUFFICIENT_TRAINING_HISTORY
            folds.append(
                PlannedFold(
                    horizon=horizon,
                    test_ticker=test_ticker,
                    prediction_date=prediction_date,
                    prediction_cutoff_date=cutoff,
                    target_session_date=state.targets[(test_ticker, horizon)].target_session_date,
                    training_tickers=tuple(training),
                    n_chronological_train=len(chronological),
                    n_effective_train=len(training),
                    status=status,
                )
            )
    return folds


def summarize_eligibility(state: LoadedState, folds: Iterable[PlannedFold]) -> list[dict[str, Any]]:
    by_horizon: dict[str, list[PlannedFold]] = defaultdict(list)
    for fold in folds:
        by_horizon[fold.horizon].append(fold)
    rows: list[dict[str, Any]] = []
    for horizon in HORIZONS:
        horizon_folds = by_horizon[horizon]
        scorable = [fold for fold in horizon_folds if fold.status == "SCORABLE"]
        insufficient = [fold for fold in horizon_folds if fold.status != "SCORABLE"]
        valid_target_n = sum(
            1
            for ticker in state.master
            if state.targets[(ticker, horizon)].target_status == TARGET_AVAILABLE
        )
        single_class_n = 0
        zero_target_n = 0
        for fold in scorable:
            classes = {state.targets[(ticker, horizon)].Y_h for ticker in fold.training_tickers}
            if len(classes) == 1:
                single_class_n += 1
            if Decimal(state.targets[(fold.test_ticker, horizon)].R_h or "NaN") == 0:
                zero_target_n += 1
        row = {
            "benchmark_task_id": TASK_ID,
            "benchmark_identity": BENCHMARK_ID,
            "benchmark_status": BENCHMARK_STATUS,
            "horizon": horizon,
            "cohort_n": len(horizon_folds),
            "valid_target_n": valid_target_n,
            "invalid_target_n": len(horizon_folds) - valid_target_n,
            "min_train_n": MIN_TRAIN_N,
            "scorable_fold_n": len(scorable),
            "insufficient_training_history_n": len(insufficient),
            "expected_scorable_fold_n": EXPECTED_SCORABLE[horizon],
            "expected_insufficient_training_history_n": EXPECTED_INSUFFICIENT[horizon],
            "eligibility_matches_expected": "TRUE"
            if len(scorable) == EXPECTED_SCORABLE[horizon]
            and len(insufficient) == EXPECTED_INSUFFICIENT[horizon]
            else "FALSE",
            "same_date_leakage_n": 0,
            "future_target_leakage_n": 0,
            "self_leakage_n": 0,
            "logistic_single_class_scorable_fold_n": single_class_n,
            "zero_realized_return_scorable_fold_n": zero_target_n,
            "eligibility_rule_identity": ELIGIBILITY_RULE_IDENTITY,
        }
        rows.append(row)
    if any(row["eligibility_matches_expected"] != "TRUE" for row in rows):
        raise BenchmarkStop("HISTORICAL99_V1_5_ELIGIBILITY_REGRESSION")
    if sum(int(row["scorable_fold_n"]) for row in rows) != EXPECTED_TOTAL_FOLDS:
        raise BenchmarkStop("HISTORICAL99_V1_5_ELIGIBILITY_REGRESSION: total is not 351")
    return rows


def _fmt_float(value: Optional[float]) -> str:
    if value is None:
        return ""
    if not math.isfinite(value):
        raise BenchmarkStop(f"Non-finite scientific value: {value!r}")
    return format(value, ".17g")


def _json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _score_table_json(entries: Iterable[cm.ScoreTableEntry]) -> str:
    return _json_compact(
        [
            {
                "fold_count": entry.fold_count,
                "hyperparameter": entry.hyperparameter,
                "score": entry.score,
                "status": entry.status,
            }
            for entry in entries
        ]
    )


def _identity_hash(items: Iterable[str]) -> str:
    return sha256_bytes(("\n".join(items) + "\n").encode("utf-8"))


def _feature_vector_json(values: Mapping[str, Optional[Decimal]]) -> str:
    return _json_compact({key: None if value is None else str(value) for key, value in values.items()})


def run_outer_folds(
    state: LoadedState,
    folds: list[PlannedFold],
) -> tuple[list[dict[str, Any]], dict[str, list[tuple[str, str, mx.RegressionScoredPoint]]], dict[str, list[tuple[str, str, mx.ClassificationScoredPoint]]]]:
    store = fe.GuardedTargetStore(state.target_records)
    ledger: list[dict[str, Any]] = []
    regression_points: dict[str, list[tuple[str, str, mx.RegressionScoredPoint]]] = defaultdict(list)
    classification_points: dict[str, list[tuple[str, str, mx.ClassificationScoredPoint]]] = defaultdict(list)
    scorable_folds = [fold for fold in folds if fold.status == "SCORABLE"]
    completed = 0
    for horizon in HORIZONS:
        horizon_folds = [fold for fold in scorable_folds if fold.horizon == horizon]
        print(f"FIT_START horizon={horizon} folds={len(horizon_folds)}", flush=True)
        for fold in horizon_folds:
            store.enter_fold(fold.test_ticker, fold.horizon)
            training_raw = {ticker: state.raw_features[ticker] for ticker in fold.training_tickers}
            training_targets = {
                ticker: store.get_training_target(ticker, fold.horizon)
                for ticker in fold.training_tickers
            }
            test_raw = state.raw_features[fold.test_ticker]
            local_filter_status = {
                ticker: state.filter_status.get(ticker) for ticker in fold.training_tickers
            }
            local_filter_status["__test__"] = state.filter_status.get(fold.test_ticker)

            ridge = cm.fit_ridge_candidate(
                training_raw,
                training_targets,
                test_raw,
                local_filter_status,
            )
            logistic = cm.fit_logistic_candidate(
                training_raw,
                training_targets,
                test_raw,
                local_filter_status,
            )
            store.unlock_for_evaluation()
            actual = store.get_test_target_for_evaluation()
            if actual.target_status != TARGET_AVAILABLE:
                raise BenchmarkStop(f"{fold.test_ticker}/{fold.horizon}: test target unavailable after prediction")

            actual_r = float(actual.R_h) if actual.R_h is not None else None
            actual_y = int(actual.Y_h) if actual.Y_h is not None else None
            ipo_price = Decimal(actual.ipo_price_exact)
            actual_close = Decimal(actual.official_close_exact or "NaN")
            ridge_error = None
            ridge_abs_error = None
            predicted_close = None
            price_ape = None
            if ridge.prediction is not None:
                assert actual_r is not None
                ridge_error = ridge.prediction - actual_r
                ridge_abs_error = abs(ridge_error)
                predicted_close = float(ipo_price) * (1.0 + ridge.prediction)
                price_ape = abs(predicted_close - float(actual_close)) / float(actual_close) * 100.0
                regression_points[horizon].append(
                    (
                        fold.prediction_date,
                        fold.test_ticker,
                        mx.RegressionScoredPoint(
                            ticker=fold.test_ticker,
                            predicted_r_h=ridge.prediction,
                            actual_r_h=actual_r,
                            ipo_price=ipo_price,
                            actual_close=actual_close,
                        ),
                    )
                )

            clipped_probability = None
            direction_correct = None
            brier_contribution = None
            log_loss_contribution = None
            if logistic.probability_positive_class is not None:
                assert logistic.predicted_class is not None and actual_y is not None
                clipped_probability = min(
                    max(logistic.probability_positive_class, mx.PROB_CLIP[0]),
                    mx.PROB_CLIP[1],
                )
                direction_correct = int(logistic.predicted_class == actual_y)
                brier_contribution = (clipped_probability - actual_y) ** 2
                log_loss_contribution = -(
                    actual_y * math.log(clipped_probability)
                    + (1 - actual_y) * math.log(1 - clipped_probability)
                )
                classification_points[horizon].append(
                    (
                        fold.prediction_date,
                        fold.test_ticker,
                        mx.ClassificationScoredPoint(
                            ticker=fold.test_ticker,
                            predicted_direction=logistic.predicted_class,
                            predicted_prob_above_ipo=logistic.probability_positive_class,
                            actual_y_h=actual_y,
                        ),
                    )
                )

            training_identity = list(fold.training_tickers)
            training_target_identity = [
                "|".join(
                    [
                        ticker,
                        state.targets[(ticker, fold.horizon)].target_session_date,
                        state.targets[(ticker, fold.horizon)].R_h or "",
                        str(state.targets[(ticker, fold.horizon)].Y_h),
                    ]
                )
                for ticker in fold.training_tickers
            ]
            test_feature_json = _feature_vector_json(test_raw)
            ledger.append(
                {
                    "benchmark_task_id": TASK_ID,
                    "benchmark_identity": BENCHMARK_ID,
                    "benchmark_status": BENCHMARK_STATUS,
                    "oos_stream": OOS_STREAM,
                    "fold_id": f"{BENCHMARK_ID}|{fold.horizon}|{fold.test_ticker}",
                    "ticker": fold.test_ticker,
                    "prediction_date": fold.prediction_date,
                    "prediction_cutoff_date": fold.prediction_cutoff_date,
                    "horizon": fold.horizon,
                    "target_session_date": fold.target_session_date,
                    "eligibility_status": fold.status,
                    "training_n": fold.n_effective_train,
                    "n_chronological_train": fold.n_chronological_train,
                    "training_tickers_json": _json_compact(training_identity),
                    "training_tickers_sha256": _identity_hash(training_identity),
                    "training_targets_sha256": _identity_hash(training_target_identity),
                    "same_date_leakage_n": 0,
                    "future_target_leakage_n": 0,
                    "self_leakage_n": 0,
                    "feature_schema_version": FEATURE_SCHEMA_VERSION,
                    "feature_set_identity": FEATURE_SET_IDENTITY,
                    "test_raw_features_json": test_feature_json,
                    "test_raw_feature_vector_sha256": sha256_bytes(test_feature_json.encode("utf-8")),
                    "test_f3_missing": "TRUE" if test_raw["f3"] is None else "FALSE",
                    "frozen_preprocessing_identity": PREPROCESSING_IDENTITY,
                    "frozen_preprocessing_sha256": IMPLEMENTATION_PINS[
                        ROOT / "scripts" / "modeling" / "preprocessing.py"
                    ],
                    "eligibility_rule_identity": ELIGIBILITY_RULE_IDENTITY,
                    "ridge_model_id": ridge.model_id,
                    "ridge_status": ridge.status,
                    "ridge_selected_alpha": _fmt_float(ridge.selected_alpha),
                    "ridge_tuning_status": ridge.tuning_status,
                    "ridge_inner_fold_n": ridge.inner_fold_count,
                    "ridge_active_features_json": _json_compact(list(ridge.feature_names)),
                    "ridge_candidate_score_table_json": _score_table_json(ridge.candidate_score_table),
                    "ridge_point_prediction_return": _fmt_float(ridge.prediction),
                    "realized_target_return": actual.R_h,
                    "ridge_signed_error_return": _fmt_float(ridge_error),
                    "ridge_absolute_error_return": _fmt_float(ridge_abs_error),
                    "ipo_price": actual.ipo_price_exact,
                    "ridge_predicted_close": _fmt_float(predicted_close),
                    "official_close": actual.official_close_exact,
                    "ridge_absolute_percentage_error_price_level_pct": _fmt_float(price_ape),
                    "logistic_model_id": logistic.model_id,
                    "logistic_status": logistic.status,
                    "logistic_selected_C": _fmt_float(logistic.selected_C),
                    "logistic_tuning_status": logistic.tuning_status,
                    "logistic_inner_fold_n": logistic.inner_fold_count,
                    "logistic_active_features_json": _json_compact(list(logistic.feature_names)),
                    "logistic_candidate_score_table_json": _score_table_json(logistic.candidate_score_table),
                    "logistic_n_class_0": logistic.n_class_0,
                    "logistic_n_class_1": logistic.n_class_1,
                    "logistic_probability_above_ipo_raw": _fmt_float(logistic.probability_positive_class),
                    "logistic_probability_reporting_clipped_0_01_0_99": _fmt_float(clipped_probability),
                    "logistic_predicted_direction": ""
                    if logistic.predicted_class is None
                    else logistic.predicted_class,
                    "realized_direction": actual_y,
                    "direction_correct": "" if direction_correct is None else direction_correct,
                    "logistic_brier_contribution_reporting_clip": _fmt_float(brier_contribution),
                    "logistic_log_loss_contribution_reporting_clip": _fmt_float(log_loss_contribution),
                    "logistic_observed_fit_warnings_json": _json_compact(list(logistic.observed_fit_warnings)),
                    "runtime_versions_json": _json_compact(
                        ridge.runtime_versions or logistic.runtime_versions
                    ),
                }
            )
            completed += 1
            if completed % 20 == 0:
                print(f"FIT_PROGRESS completed={completed}/{EXPECTED_TOTAL_FOLDS}", flush=True)
        print(f"FIT_DONE horizon={horizon}", flush=True)
    if len(ledger) != EXPECTED_TOTAL_FOLDS:
        raise BenchmarkStop(f"Expected 351 outer-fold rows; got {len(ledger)}")
    return ledger, regression_points, classification_points


def build_metric_rows(
    regression_points: Mapping[str, list[tuple[str, str, mx.RegressionScoredPoint]]],
    classification_points: Mapping[str, list[tuple[str, str, mx.ClassificationScoredPoint]]],
    ledger: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    windows = (("LAST_5", 5), ("LAST_10", 10), ("LAST_20", 20), ("ALL", None))
    for horizon in HORIZONS:
        horizon_ledger = [row for row in ledger if row["horizon"] == horizon]
        zero_target_n = sum(Decimal(str(row["realized_target_return"])) == 0 for row in horizon_ledger)
        regression_ordered = sorted(regression_points[horizon], key=lambda item: (item[0], item[1]))
        classification_ordered = sorted(classification_points[horizon], key=lambda item: (item[0], item[1]))
        for window_name, window_n in windows:
            r_selected = regression_ordered if window_n is None else regression_ordered[-window_n:]
            c_selected = classification_ordered if window_n is None else classification_ordered[-window_n:]
            r_metrics = mx.compute_regression_metrics([item[2] for item in r_selected])
            c_metrics = mx.compute_classification_metrics([item[2] for item in c_selected])
            assert r_metrics is not None and c_metrics is not None
            common = {
                "benchmark_task_id": TASK_ID,
                "benchmark_identity": BENCHMARK_ID,
                "benchmark_status": BENCHMARK_STATUS,
                "horizon": horizon,
                "reporting_window": window_name,
                "pooled_across_horizons": "FALSE",
                "zero_realized_return_n_in_all_scorable_folds": zero_target_n,
            }
            rows.append(
                {
                    **common,
                    "model_id": cm.MODEL_ID_RIDGE,
                    "problem_type": "REGRESSION",
                    "n_oos": r_metrics.n_oos,
                    "primary_metric": "MAE_RETURN_SPACE",
                    "primary_metric_value": _fmt_float(r_metrics.mae),
                    "mae_return_space": _fmt_float(r_metrics.mae),
                    "median_ae_return_space": _fmt_float(r_metrics.median_ae),
                    "rmse_return_space": _fmt_float(r_metrics.rmse),
                    "mape_price_level_pct": _fmt_float(r_metrics.mape_price_level),
                    "median_ape_price_level_pct": _fmt_float(r_metrics.median_ape_price_level),
                    "above_ipo_accuracy": "",
                    "brier_score_reporting_clip": "",
                    "log_loss_reporting_clip": "",
                    "probability_reporting_clip": "NOT_APPLICABLE",
                    "interval_coverage": r_metrics.interval_coverage,
                    "conclusiveness": r_metrics.conclusiveness,
                    "metric_denominator_note": (
                        "MAE_MEDIAN_AE_RMSE_USE_RETURN_SPACE_N; "
                        "MAPE_MEDIAN_APE_USE_POSITIVE_ACTUAL_CLOSE_PRICE_LEVEL_N"
                    ),
                }
            )
            rows.append(
                {
                    **common,
                    "model_id": cm.MODEL_ID_LOGIT,
                    "problem_type": "CLASSIFICATION",
                    "n_oos": c_metrics.n_oos,
                    "primary_metric": "BRIER_SCORE_REPORTING_CLIP",
                    "primary_metric_value": _fmt_float(c_metrics.brier_score),
                    "mae_return_space": "",
                    "median_ae_return_space": "",
                    "rmse_return_space": "",
                    "mape_price_level_pct": "",
                    "median_ape_price_level_pct": "",
                    "above_ipo_accuracy": _fmt_float(c_metrics.above_ipo_accuracy),
                    "brier_score_reporting_clip": _fmt_float(c_metrics.brier_score),
                    "log_loss_reporting_clip": _fmt_float(c_metrics.log_loss),
                    "probability_reporting_clip": "[0.01,0.99]",
                    "interval_coverage": "NOT_APPLICABLE_CLASSIFICATION",
                    "conclusiveness": c_metrics.conclusiveness,
                    "metric_denominator_note": (
                        "ONLY_FIT_OK_LOGISTIC_PREDICTIONS; SINGLE_CLASS_FOLDS_HAVE_NO_FABRICATED_PROBABILITY"
                    ),
                }
            )
    return rows


def build_hyperparameter_rows(ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for horizon in HORIZONS:
        horizon_rows = [row for row in ledger if row["horizon"] == horizon]
        for model_id, parameter_field, status_field, tuning_field in (
            (cm.MODEL_ID_RIDGE, "ridge_selected_alpha", "ridge_status", "ridge_tuning_status"),
            (cm.MODEL_ID_LOGIT, "logistic_selected_C", "logistic_status", "logistic_tuning_status"),
        ):
            groups = Counter(
                (
                    str(row[parameter_field]),
                    str(row[status_field]),
                    str(row[tuning_field]),
                )
                for row in horizon_rows
            )
            fitted_n = sum(
                count
                for (parameter, status, _tuning), count in groups.items()
                if parameter != "" and status == cm.STATUS_FIT_OK
            )
            for (parameter, status, tuning), count in sorted(groups.items()):
                rows.append(
                    {
                        "benchmark_task_id": TASK_ID,
                        "benchmark_identity": BENCHMARK_ID,
                        "benchmark_status": BENCHMARK_STATUS,
                        "horizon": horizon,
                        "model_id": model_id,
                        "hyperparameter_name": "alpha" if model_id == cm.MODEL_ID_RIDGE else "C",
                        "selected_hyperparameter": parameter,
                        "fit_status": status,
                        "tuning_status": tuning,
                        "count": count,
                        "all_scorable_fold_denominator": len(horizon_rows),
                        "fitted_model_denominator": fitted_n,
                        "share_of_all_scorable_folds": _fmt_float(count / len(horizon_rows)),
                        "share_of_fitted_models": ""
                        if parameter == "" or fitted_n == 0
                        else _fmt_float(count / fitted_n),
                    }
                )
    return rows


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        raise BenchmarkStop("Refusing to serialize empty scientific CSV")
    fields = list(rows[0].keys())
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        if list(row.keys()) != fields:
            raise BenchmarkStop("CSV schema drift inside one artifact")
        writer.writerow({key: "" if value is None else value for key, value in row.items()})
    return buffer.getvalue().encode("utf-8")


def inventory_scope(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": repo_relative(path),
            "exists": False,
            "file_count": 0,
            "total_bytes": 0,
            "inventory_sha256": None,
        }
    if path.is_file():
        files = [path]
        base = path.parent
    else:
        files = sorted((item for item in path.rglob("*") if item.is_file()), key=lambda item: item.as_posix())
        base = path
    lines: list[str] = []
    total_bytes = 0
    for item in files:
        rel = item.relative_to(base).as_posix()
        size = item.stat().st_size
        total_bytes += size
        lines.append(f"{rel}\t{size}\t{sha256_file(item)}")
    inventory = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
    return {
        "path": repo_relative(path),
        "exists": True,
        "file_count": len(files),
        "total_bytes": total_bytes,
        "inventory_sha256": sha256_bytes(inventory),
    }


def protected_snapshot() -> dict[str, dict[str, Any]]:
    return {name: inventory_scope(path) for name, path in PROTECTED_SCOPES.items()}


def _status_counts(ledger: list[dict[str, Any]], prefix: str) -> dict[str, dict[str, int]]:
    return {
        horizon: dict(
            sorted(
                Counter(
                    str(row[f"{prefix}_status"])
                    for row in ledger
                    if row["horizon"] == horizon
                ).items()
            )
        )
        for horizon in HORIZONS
    }


def build_manifest(
    input_hashes: Mapping[str, str],
    eligibility_rows: list[dict[str, Any]],
    ledger: list[dict[str, Any]],
    csv_payloads: Mapping[str, bytes],
    protected_before: Mapping[str, Any],
    protected_after: Mapping[str, Any],
) -> dict[str, Any]:
    if protected_before != protected_after:
        raise BenchmarkStop("PROTECTED_HASH_MISMATCH_DURING_BENCHMARK")
    runner_path = Path(__file__).resolve()
    test_path = ROOT / "tests" / "test_historical99_frozen_v1_5_benchmark.py"
    artifact_hashes = {
        str((OUTPUT_DIR / name).relative_to(ROOT).as_posix()): sha256_bytes(payload)
        for name, payload in csv_payloads.items()
    }
    return {
        "schema_version": "1.0",
        "task_id": TASK_ID,
        "benchmark_identity": BENCHMARK_ID,
        "benchmark_status": BENCHMARK_STATUS,
        "cohort_identity": "HISTORICAL99_FROZEN_COHORT_V1",
        "cohort_size": 99,
        "outcome_identity": "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1",
        "input_hash_gate": {
            "status": "PASS",
            "artifacts": {
                repo_relative(path): {
                    "expected_sha256": expected,
                    "actual_sha256": input_hashes[repo_relative(path)],
                }
                for path, expected in INPUT_HASHES.items()
            },
        },
        "implementation_pins": {
            repo_relative(path): {
                "expected_sha256": expected,
                "actual_sha256": input_hashes[repo_relative(path)],
            }
            for path, expected in IMPLEMENTATION_PINS.items()
        },
        "eligibility": {
            row["horizon"]: {
                "total": row["cohort_n"],
                "valid_target": row["valid_target_n"],
                "scorable": row["scorable_fold_n"],
                "insufficient_training_history": row["insufficient_training_history_n"],
                "logistic_single_class": row["logistic_single_class_scorable_fold_n"],
                "zero_realized_return": row["zero_realized_return_scorable_fold_n"],
            }
            for row in eligibility_rows
        },
        "total_scorable_outer_folds": len(ledger),
        "strict_prior_date_rule": {
            "identity": ELIGIBILITY_RULE_IDENTITY,
            "formula": "target_session_date(j,h) < prediction_date(k)",
            "same_local_date_excluded": True,
            "future_excluded": True,
            "self_outcome_excluded": True,
            "horizon_specific": True,
        },
        "feature_contract": {
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "identity": FEATURE_SET_IDENTITY,
            "f1": "raw ipo_size_tl; natural log only inside frozen preprocessing",
            "f2": "shares_offered_final / post_ipo_share_capital * 100",
            "f3": "total_demand_multiple; missing is not zero",
            "f4": "capital_increase_shares / shares_offered_final * 100",
            "f5": "1 iff f3 missing",
            "f3_missing_tickers": ["ALBTN", "ENDAE"],
        },
        "preprocessing_contract": {
            "identity": PREPROCESSING_IDENTITY,
            "fit_scope": "OUTER_TRAINING_FOLD_ONLY_AND_REFIT_ON_EVERY_INNER_TRAIN_SPLIT",
            "global_preprocessing": False,
            "outer_test_visible_during_tuning": False,
            "sha256": IMPLEMENTATION_PINS[ROOT / "scripts" / "modeling" / "preprocessing.py"],
        },
        "ridge_contract": {
            "model_id": cm.MODEL_ID_RIDGE,
            "estimator": "sklearn.linear_model.Ridge",
            "alpha_grid": list(cm.RIDGE_ALPHA_GRID),
            "fit_intercept": True,
            "solver": "svd",
            "inner_validation": "LOOCV_OUTER_TRAINING_ONLY",
            "selection_metric": "RAW_RETURN_SPACE_MAE",
            "tie_break": "BIT_EXACT_TIE_TO_LARGEST_ALPHA",
        },
        "logistic_contract": {
            "model_id": cm.MODEL_ID_LOGIT,
            "estimator": "sklearn.linear_model.LogisticRegression",
            "l2_api": "l1_ratio=0.0 under pinned sklearn 1.9.0",
            "C_grid": list(cm.LOGISTIC_C_GRID),
            "solver": "lbfgs",
            "fit_intercept": True,
            "class_weight": None,
            "max_iter": 10000,
            "tol": 1e-10,
            "inner_validation": "LOOCV_OUTER_TRAINING_ONLY",
            "selection_metric": "RAW_UNCLIPPED_BRIER",
            "tie_break": "BIT_EXACT_TIE_TO_SMALLEST_C",
            "direction_rule": "p > 0.5 -> UP(1); p <= 0.5 -> DOWN(0)",
            "single_class_policy": "MODEL_NOT_FIT_SINGLE_CLASS_NO_PROBABILITY",
            "calibration": "NONE",
        },
        "metric_contract": {
            "horizons_reported_separately": list(HORIZONS),
            "pooling_across_horizons": False,
            "reporting_windows": ["LAST_5", "LAST_10", "LAST_20", "ALL"],
            "regression": [
                "MAE_RETURN_SPACE",
                "MEDIAN_AE_RETURN_SPACE",
                "RMSE_RETURN_SPACE",
                "MAPE_PRICE_LEVEL",
                "MEDIAN_APE_PRICE_LEVEL",
            ],
            "classification": [
                "ABOVE_IPO_ACCURACY",
                "BRIER_SCORE",
                "LOG_LOSS",
            ],
            "reporting_probability_clip": [0.01, 0.99],
            "inner_logistic_tuning_probability_clip": None,
            "prediction_interval_coverage": "NOT_APPLICABLE_V1_1",
            "denominators": {
                "ridge": "FIT_OK_RIDGE_PREDICTIONS",
                "logistic": "FIT_OK_LOGISTIC_PREDICTIONS_ONLY",
                "price_percentage_error": "POSITIVE_ACTUAL_CLOSE_PRICE_LEVEL",
            },
        },
        "model_status_counts": {
            "ridge": _status_counts(ledger, "ridge"),
            "logistic": _status_counts(ledger, "logistic"),
        },
        "scientific_artifacts": artifact_hashes,
        "manifest_path": str((OUTPUT_DIR / MANIFEST_NAME).relative_to(ROOT).as_posix()),
        "determinism_receipt_path": str(
            (OUTPUT_DIR / DETERMINISM_RECEIPT_NAME).relative_to(ROOT).as_posix()
        ),
        "determinism": {
            "required_execution_count": 2,
            "scientific_artifacts_byte_identical_required": True,
            "no_volatile_timestamp_in_scientific_artifacts": True,
            "reproducibility_scope": "PINNED_ENVIRONMENT_SINGLE_MACHINE",
        },
        "focused_tests": {
            "path": repo_relative(test_path),
            "command": (
                ".venv-v1_5-model/Scripts/python.exe -B -m unittest discover "
                "-s tests -p test_historical99_frozen_v1_5_benchmark.py"
            ),
            "runner_sha256": sha256_file(runner_path),
            "test_sha256": sha256_file(test_path),
        },
        "protected_hashes_before": protected_before,
        "protected_hashes_after": protected_after,
        "protected_hashes_unchanged": True,
        "external_pretrade_evidence_handling": {
            "mode": "READ_ONLY_EXISTENCE_AND_CONTENT_INVENTORY_ONLY",
            "moved": False,
            "modified": False,
            "imported": False,
            "canonicalized": False,
        },
        "NO_TUNING_AFTER_OUTCOME": True,
        "BASELINE_NOT_RUN": True,
        "V2_NOT_RUN": True,
        "NEW_DATA_COLLECTION_NOT_RUN": True,
        "NETWORK_NOT_USED": True,
        "old_full20_result_used_for_model_change": False,
    }


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def write_identical_or_new(path: Path, payload: bytes) -> str:
    if path.exists():
        existing = path.read_bytes()
        if existing != payload:
            raise BenchmarkStop(
                f"EXISTING_VERSIONED_ARTIFACT_MISMATCH: refusing overwrite of {repo_relative(path)}"
            )
        return "UNCHANGED_IDENTICAL"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return "CREATED"


def execute() -> dict[str, Any]:
    input_hashes = verify_hash_gate()
    print("HASH_GATE=PASS", flush=True)
    state = load_and_validate_state()
    folds = plan_historical_folds(state)
    eligibility_rows = summarize_eligibility(state, folds)
    print(
        "ELIGIBILITY_GATE=PASS "
        + " ".join(f"{row['horizon']}={row['scorable_fold_n']}" for row in eligibility_rows),
        flush=True,
    )
    protected_before = protected_snapshot()
    ledger, regression_points, classification_points = run_outer_folds(state, folds)
    metric_rows = build_metric_rows(regression_points, classification_points, ledger)
    hyperparameter_rows = build_hyperparameter_rows(ledger)
    csv_payloads = {
        ELIGIBILITY_NAME: csv_bytes(eligibility_rows),
        LEDGER_NAME: csv_bytes(ledger),
        METRICS_NAME: csv_bytes(metric_rows),
        HYPERPARAMETER_NAME: csv_bytes(hyperparameter_rows),
    }
    protected_after = protected_snapshot()
    manifest = build_manifest(
        input_hashes,
        eligibility_rows,
        ledger,
        csv_payloads,
        protected_before,
        protected_after,
    )
    scientific_payloads = {**csv_payloads, MANIFEST_NAME: json_bytes(manifest)}
    complete_before = all((OUTPUT_DIR / name).is_file() for name in scientific_payloads)
    existing_hashes_before = (
        {name: sha256_file(OUTPUT_DIR / name) for name in scientific_payloads}
        if complete_before
        else {}
    )
    write_status = {
        name: write_identical_or_new(OUTPUT_DIR / name, payload)
        for name, payload in scientific_payloads.items()
    }
    generated_hashes = {name: sha256_bytes(payload) for name, payload in scientific_payloads.items()}
    receipt_status = "NOT_APPLICABLE_FIRST_EXECUTION"
    if complete_before:
        if existing_hashes_before != generated_hashes:
            raise BenchmarkStop("SECOND_EXECUTION_NOT_BYTE_IDENTICAL")
        receipt = {
            "schema_version": "1.0",
            "task_id": TASK_ID,
            "benchmark_identity": BENCHMARK_ID,
            "execution_ordinal": 2,
            "scientific_artifacts": {
                name: {
                    "first_execution_sha256": existing_hashes_before[name],
                    "second_execution_generated_sha256": generated_hashes[name],
                    "byte_identical": True,
                }
                for name in sorted(scientific_payloads)
            },
            "all_scientific_artifacts_byte_identical": True,
            "selected_hyperparameters_predictions_and_metrics_identical": True,
            "volatile_timestamp_present": False,
        }
        receipt_status = write_identical_or_new(
            OUTPUT_DIR / DETERMINISM_RECEIPT_NAME,
            json_bytes(receipt),
        )
    return {
        "task_id": TASK_ID,
        "benchmark_identity": BENCHMARK_ID,
        "status": BENCHMARK_STATUS,
        "outer_fold_rows": len(ledger),
        "write_status": write_status,
        "determinism_receipt_status": receipt_status,
        "scientific_artifact_sha256": generated_hashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        result = execute()
    except BenchmarkStop as exc:
        print(f"STOP: {exc}", flush=True)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

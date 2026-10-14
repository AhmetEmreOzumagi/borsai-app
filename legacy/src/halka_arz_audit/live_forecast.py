"""LIVE_FORECAST_TRACK için deterministik takvim, kayıt ve performans korumaları."""

from __future__ import annotations

import csv
import hashlib
import json
import tomllib
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .guards import PolicyViolation


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise PolicyViolation(f"CSV başlığı yok: {path}")
        return list(reader.fieldnames), [dict(row) for row in reader]


def load_config(project_root: Path) -> dict[str, Any]:
    with (project_root / "config" / "live_forecast.toml").open("rb") as handle:
        return tomllib.load(handle)["live_forecast"]


def verify_protected_sources(
    project_root: Path, config: Mapping[str, Any]
) -> dict[str, str]:
    results: dict[str, str] = {}
    for entry in config["protected_source"]:
        relative = str(entry["path"])
        path = (project_root / relative).resolve()
        expected = str(entry["sha256"]).lower()
        if not path.is_file():
            raise PolicyViolation(f"Korunan kaynak bulunamadı: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise PolicyViolation(
                f"Korunan kaynak SHA-256 değişti: {relative}; "
                f"beklenen={expected}, bulunan={actual}"
            )
        results[relative] = actual
    return results


def trading_day_number(
    first_trading_date: str,
    target_trading_date: str,
    *,
    excluded_market_closure_dates: Iterable[str] = (),
) -> int:
    """Başlangıç günü dahil, hafta sonu ve açıkça verilen kapalı seansları dışlar."""
    first = date.fromisoformat(first_trading_date)
    target = date.fromisoformat(target_trading_date)
    if target < first:
        raise PolicyViolation(
            f"Hedef tarih ilk işlem tarihinden önce: {first_trading_date}>{target_trading_date}"
        )
    excluded = {date.fromisoformat(value) for value in excluded_market_closure_dates}
    count = 0
    current = first
    while current <= target:
        if current.weekday() < 5 and current not in excluded:
            count += 1
        current += timedelta(days=1)
    return count


def calculate_candidates(
    config: Mapping[str, Any], universe_rows: Sequence[Mapping[str, str]]
) -> list[dict[str, Any]]:
    universe_by = {row["ticker"]: row for row in universe_rows}
    target = str(config["next_live_target_date"])
    calendar = config["calendar"]
    lower = int(calendar["first_ten_inclusive_min"])
    upper = int(calendar["first_ten_inclusive_max"])
    rows: list[dict[str, Any]] = []
    candidate_tickers = config.get(
        "candidate_tickers", config["candidate_tickers_2026_08_10"]
    )
    for ticker in candidate_tickers:
        if ticker not in universe_by:
            raise PolicyViolation(f"Canlı aday donmuş evrende yok: {ticker}")
        source = universe_by[ticker]
        number = trading_day_number(
            source["first_trading_date"],
            target,
            excluded_market_closure_dates=calendar["excluded_market_closure_dates"],
        )
        rows.append(
            {
                "ticker": ticker,
                "first_trading_date": source["first_trading_date"],
                "target_trading_date": target,
                "trading_day_number": number,
                "within_first_10_trading_days": lower <= number <= upper,
            }
        )
    return rows


def build_registry_rows(
    config: Mapping[str, Any],
    frozen_rows: Sequence[Mapping[str, str]],
    universe_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    legacy = config["legacy"]
    universe_by = {row["ticker"]: row for row in universe_rows}
    fields = list(config["registry_fields"])
    rows: list[dict[str, str]] = []
    for source in frozen_rows:
        ticker = source["ticker"]
        if ticker not in universe_by:
            raise PolicyViolation(f"Donmuş tahmin ticker'ı evrende yok: {ticker}")
        row = {field: "" for field in fields}
        for field in legacy["copy_exact_fields"]:
            row[field] = source.get(field, "")
        row["target_trading_date"] = str(legacy["target_trading_date"])
        row["trading_day_number"] = str(
            trading_day_number(
                universe_by[ticker]["first_trading_date"],
                row["target_trading_date"],
                excluded_market_closure_dates=config["calendar"][
                    "excluded_market_closure_dates"
                ],
            )
        )
        row["model_version"] = ""
        row["freeze_status"] = str(legacy["freeze_status"])
        rows.append(row)
    return rows


def canonical_record_hash(row: Mapping[str, Any], fields: Sequence[str]) -> str:
    payload = {field: str(row.get(field, "")) for field in fields}
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _decimal(value: Any) -> Decimal | None:
    if value in {None, ""}:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _bool_event(value: Any) -> int | None:
    normalized = str(value).strip().upper()
    if normalized == "TRUE":
        return 1
    if normalized == "FALSE":
        return 0
    return None


def _rounded(value: float | Decimal | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 10)


def _rate(values: Sequence[bool]) -> float | None:
    if not values:
        return None
    return _rounded(sum(1 for value in values if value) / len(values))


def _average(values: Sequence[Decimal]) -> float | None:
    if not values:
        return None
    return _rounded(mean(values))


def _window_metrics(
    joined: Sequence[tuple[Mapping[str, str], Mapping[str, str]]]
) -> dict[str, Any]:
    absolute_errors: list[Decimal] = []
    ape_values: list[Decimal] = []
    direction_results: list[bool] = []
    above_ipo_results: list[bool] = []
    interval_results: list[bool] = []
    brier_reference: list[Decimal] = []
    brier_ipo: list[Decimal] = []
    brier_limit_up: list[Decimal] = []
    brier_limit_down: list[Decimal] = []
    naive1_errors: list[Decimal] = []
    naive2_errors: list[Decimal] = []
    naive1_results: list[bool] = []
    naive2_results: list[bool] = []

    for prediction, evaluation in joined:
        actual = _decimal(evaluation.get("actual_close"))
        point = _decimal(prediction.get("point_prediction"))
        reference = _decimal(prediction.get("reference_price"))
        lower = _decimal(prediction.get("lower_bound"))
        upper = _decimal(prediction.get("upper_bound"))
        if actual is None or point is None or reference is None:
            continue
        model_error = abs(point - actual)
        absolute_errors.append(model_error)
        if actual != 0:
            ape_values.append(model_error / abs(actual) * Decimal(100))
        if lower is not None and upper is not None:
            interval_results.append(lower <= actual <= upper)

        actual_direction = "UP" if actual > reference else "DOWN" if actual < reference else "FLAT"
        predicted_direction = prediction.get("direction_prediction", "").strip().upper()
        if predicted_direction in {"UP", "DOWN", "FLAT"}:
            direction_results.append(predicted_direction == actual_direction)

        prob_reference = _decimal(prediction.get("prob_above_reference"))
        if prob_reference is not None:
            event = Decimal(1 if actual > reference else 0)
            brier_reference.append((prob_reference - event) ** 2)

        ipo_price = _decimal(evaluation.get("ipo_price"))
        prob_ipo = _decimal(prediction.get("prob_above_ipo"))
        if ipo_price is not None and prob_ipo is not None:
            event = Decimal(1 if actual > ipo_price else 0)
            above_ipo_results.append((prob_ipo >= Decimal("0.5")) == bool(event))
            brier_ipo.append((prob_ipo - event) ** 2)

        for probability_field, actual_field, target in (
            ("prob_limit_up", "actual_limit_up", brier_limit_up),
            ("prob_limit_down", "actual_limit_down", brier_limit_down),
        ):
            probability = _decimal(prediction.get(probability_field))
            event = _bool_event(evaluation.get(actual_field))
            if probability is not None and event is not None:
                target.append((probability - Decimal(event)) ** 2)

        naive1_error = abs(reference - actual)
        naive1_errors.append(naive1_error)
        naive1_results.append(model_error < naive1_error)
        previous = _decimal(evaluation.get("previous_official_close"))
        if previous is not None:
            naive2_error = abs(previous - actual)
            naive2_errors.append(naive2_error)
            naive2_results.append(model_error < naive2_error)

    count = len(absolute_errors)
    return {
        "status": "CALCULATED" if count else "NOT_EVALUABLE",
        "prediction_count": count,
        "direction_evaluable_count": len(direction_results),
        "direction_accuracy": _rate(direction_results),
        "above_ipo_evaluable_count": len(above_ipo_results),
        "above_ipo_accuracy": _rate(above_ipo_results),
        "mae": _average(absolute_errors),
        "mape": _average(ape_values),
        "median_ape": _rounded(median(ape_values)) if ape_values else None,
        "interval_evaluable_count": len(interval_results),
        "interval_coverage": _rate(interval_results),
        "brier_scores": {
            "above_reference": _average(brier_reference),
            "above_ipo": _average(brier_ipo),
            "limit_up": _average(brier_limit_up),
            "limit_down": _average(brier_limit_down),
        },
        "naive1_evaluable_count": len(naive1_results),
        "naive1_mae": _average(naive1_errors),
        "model_beats_naive1_rate": _rate(naive1_results),
        "naive2_evaluable_count": len(naive2_results),
        "naive2_mae": _average(naive2_errors),
        "model_beats_naive2_rate": _rate(naive2_results),
    }


def compute_performance_summary(
    config: Mapping[str, Any],
    registry_rows: Sequence[Mapping[str, str]],
    evaluation_rows: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    predictions = {row["prediction_id"]: row for row in registry_rows}
    admissible_statuses = set(
        config["performance"]["admissible_actual_verification_statuses"]
    )
    joined: list[tuple[Mapping[str, str], Mapping[str, str]]] = []
    seen: set[str] = set()
    for evaluation in evaluation_rows:
        prediction_id = evaluation.get("prediction_id", "")
        if prediction_id in seen or prediction_id not in predictions:
            continue
        seen.add(prediction_id)
        if evaluation.get("evaluation_status") != config["performance"][
            "completed_evaluation_status"
        ]:
            continue
        if evaluation.get("actual_close_verification_status") not in admissible_statuses:
            continue
        if evaluation.get("actual_close_conflict_status") != config["performance"][
            "required_no_conflict_status"
        ]:
            continue
        if evaluation.get("leakage_status") != config["performance"][
            "required_leakage_status"
        ]:
            continue
        joined.append((predictions[prediction_id], evaluation))

    joined.sort(
        key=lambda pair: (
            pair[0].get("target_trading_date", ""),
            pair[0].get("prediction_timestamp", ""),
            pair[0].get("prediction_id", ""),
        )
    )
    windows: dict[str, Any] = {}
    for size in config["performance"]["windows"]:
        size_int = int(size)
        windows[f"last_{size_int}"] = {
            "window_size": size_int,
            **_window_metrics(joined[-size_int:]),
        }
    if config["performance"]["include_all_window"]:
        windows["all"] = {"window_size": None, **_window_metrics(joined)}
    return {
        "status": "CALCULATED" if joined else "NOT_EVALUATED_NO_LIVE_EVALUATION_RECORDS",
        "completed_admissible_evaluation_count": len(joined),
        "windows": windows,
    }


def build_initial_summary(
    config: Mapping[str, Any],
    registry_rows: Sequence[Mapping[str, str]],
    candidates: Sequence[Mapping[str, Any]],
    protected_hashes: Mapping[str, str],
) -> dict[str, Any]:
    fields = list(config["registry_fields"])
    performance = compute_performance_summary(config, registry_rows, [])
    return {
        "schema_version": int(config["schema_version"]),
        "track_id": config["track_id"],
        "track_status": config["track_status"],
        "as_of_date": config["as_of_date"],
        "timezone": config["timezone"],
        "standard_cutoff_local_time": config["standard_cutoff_local_time"],
        "next_live_target_date": config["next_live_target_date"],
        "registered_prediction_count": len(registry_rows),
        "legacy_frozen_prediction_count": len(registry_rows),
        "new_prediction_created_today": bool(config["new_prediction_created_today"]),
        "model_update_allowed": bool(config["model_update_allowed"]),
        f"candidate_schedule_{str(config['next_live_target_date']).replace('-', '_')}": list(candidates),
        "performance": {
            "status": "NOT_EVALUATED_NO_LIVE_EVALUATION_RECORDS",
            **performance,
        },
        "registry_record_sha256": {
            row["prediction_id"]: canonical_record_hash(row, fields)
            for row in registry_rows
        },
        "protected_source_sha256": dict(sorted(protected_hashes.items())),
    }


def validate_registry_records(
    config: Mapping[str, Any],
    frozen_rows: Sequence[Mapping[str, str]],
    universe_rows: Sequence[Mapping[str, str]],
    registry_headers: Sequence[str],
    registry_rows: Sequence[Mapping[str, str]],
) -> list[str]:
    issues: list[str] = []
    fields = list(config["registry_fields"])
    if list(registry_headers) != fields:
        issues.append("REGISTRY_SCHEMA_MISMATCH")
    forbidden = set(config["realization_field_names_forbidden_in_registry"])
    overlap = forbidden.intersection(registry_headers)
    if overlap:
        issues.append(f"REALIZATION_FIELDS_IN_REGISTRY:{sorted(overlap)}")
    ids = [row.get("prediction_id", "") for row in registry_rows]
    if len(ids) != len(set(ids)):
        issues.append("DUPLICATE_PREDICTION_ID")

    legacy = config["legacy"]
    expected_ids = list(legacy["expected_prediction_ids"])
    if config["track_status"] == "INFRASTRUCTURE_READY_NO_NEW_FORECAST" and ids != expected_ids:
        issues.append("INFRASTRUCTURE_REGISTRY_MUST_CONTAIN_ONLY_LEGACY5")
    frozen_by = {row["prediction_id"]: row for row in frozen_rows}
    registry_by = {row.get("prediction_id", ""): row for row in registry_rows}
    universe_by = {row["ticker"]: row for row in universe_rows}
    for prediction_id in expected_ids:
        source = frozen_by.get(prediction_id)
        row = registry_by.get(prediction_id)
        if source is None or row is None:
            issues.append(f"LEGACY_REFERENCE_MISSING:{prediction_id}")
            continue
        for field in legacy["copy_exact_fields"]:
            if row.get(field, "") != source.get(field, ""):
                issues.append(f"LEGACY_FIELD_MISMATCH:{prediction_id}:{field}")
        if row.get("target_trading_date") != legacy["target_trading_date"]:
            issues.append(f"LEGACY_TARGET_DATE_MISMATCH:{prediction_id}")
        expected_day = trading_day_number(
            universe_by[row["ticker"]]["first_trading_date"],
            row["target_trading_date"],
            excluded_market_closure_dates=config["calendar"][
                "excluded_market_closure_dates"
            ],
        )
        if row.get("trading_day_number") != str(expected_day):
            issues.append(f"LEGACY_TRADING_DAY_NUMBER_MISMATCH:{prediction_id}")
        if row.get("model_version", "") != "":
            issues.append(f"LEGACY_MODEL_VERSION_MUST_REMAIN_BLANK:{prediction_id}")
        if row.get("freeze_status") != legacy["freeze_status"]:
            issues.append(f"LEGACY_FREEZE_STATUS_MISMATCH:{prediction_id}")

    legacy_ids = set(expected_ids)
    allowed_freeze = set(config["allowed_freeze_statuses"])
    allowed_risk = set(config["allowed_risk_labels"])
    allowed_confidence = set(config["allowed_confidence_levels"])
    forbidden_targets = set(config["forbidden_retroactive_target_dates"])
    timezone = ZoneInfo(config["timezone"])
    standard_time = datetime.strptime(
        config["standard_cutoff_local_time"], "%H:%M:%S"
    ).time()
    nonstandard_cutoffs = [
        config.get("late_cutoff_2026_08_10", {}),
        config.get("actual_timestamp_2026_08_11", {}),
        config.get("eod_next_day_2026_08_12", {}),
    ]

    for row in registry_rows:
        prediction_id = row.get("prediction_id", "")
        is_legacy = prediction_id in legacy_ids
        if row.get("freeze_status") not in allowed_freeze:
            issues.append(f"INVALID_FREEZE_STATUS:{prediction_id}")
        if row.get("target_trading_date") in forbidden_targets:
            issues.append(f"FORBIDDEN_RETROACTIVE_TARGET:{prediction_id}")
        if row.get("risk_label") not in allowed_risk:
            issues.append(f"INVALID_RISK_LABEL:{prediction_id}")
        if row.get("confidence") not in allowed_confidence:
            issues.append(f"INVALID_CONFIDENCE:{prediction_id}")
        if not is_legacy and not row.get("model_version", "").strip():
            issues.append(f"MODEL_VERSION_REQUIRED:{prediction_id}")
        if not is_legacy and row.get("direction_prediction", "").upper() not in set(
            config["allowed_new_direction_labels"]
        ):
            issues.append(f"EXPLICIT_DIRECTION_REQUIRED:{prediction_id}")

        probability_fields = (
            "prob_above_reference",
            "prob_above_ipo",
            "prob_limit_up",
            "prob_limit_down",
        )
        for field in probability_fields:
            value = _decimal(row.get(field))
            if value is None or not (Decimal(0) <= value <= Decimal(1)):
                issues.append(f"INVALID_PROBABILITY:{prediction_id}:{field}")
        reference = _decimal(row.get("reference_price"))
        lower = _decimal(row.get("lower_bound"))
        upper = _decimal(row.get("upper_bound"))
        point = _decimal(row.get("point_prediction"))
        if reference is None or reference <= 0:
            issues.append(f"INVALID_REFERENCE_PRICE:{prediction_id}")
        if None in {lower, upper, point}:
            issues.append(f"MISSING_FORECAST_VALUE:{prediction_id}")
        elif not (lower <= point <= upper):
            issues.append(f"POINT_OUTSIDE_INTERVAL:{prediction_id}")

        try:
            prediction_timestamp = datetime.fromisoformat(row["prediction_timestamp"])
            cutoff_timestamp = datetime.fromisoformat(row["data_cutoff_timestamp"])
            target_date = date.fromisoformat(row["target_trading_date"])
        except (ValueError, KeyError):
            issues.append(f"INVALID_TIMESTAMP_OR_TARGET_DATE:{prediction_id}")
            continue
        if cutoff_timestamp > prediction_timestamp:
            issues.append(f"CUTOFF_AFTER_PREDICTION:{prediction_id}")
        if target_date < prediction_timestamp.date():
            issues.append(f"TARGET_BEFORE_PREDICTION:{prediction_id}")
        if not is_legacy:
            if prediction_timestamp.tzinfo is None or cutoff_timestamp.tzinfo is None:
                issues.append(f"TIMEZONE_REQUIRED:{prediction_id}")
            else:
                local_prediction = prediction_timestamp.astimezone(timezone)
                is_allowed_nonstandard_cutoff = any(
                    bool(exception.get("allowed_nonstandard_cutoff"))
                    and row.get("target_trading_date") in set(
                        exception.get(
                            "target_trading_dates",
                            [exception.get("target_trading_date")],
                        )
                    )
                    and row.get("data_cutoff_timestamp") == exception.get("data_cutoff_timestamp")
                    and row.get("model_version") == exception.get("model_version")
                    for exception in nonstandard_cutoffs
                )
                if not is_allowed_nonstandard_cutoff and local_prediction.time().replace(tzinfo=None) != standard_time:
                    issues.append(f"NONSTANDARD_CUTOFF_TIME:{prediction_id}")
                if is_allowed_nonstandard_cutoff and prediction_timestamp <= cutoff_timestamp:
                    issues.append(f"LATE_CUTOFF_NOT_FORWARD_LOOKING:{prediction_id}")
    return issues


def validate_summary(
    config: Mapping[str, Any],
    registry_rows: Sequence[Mapping[str, str]],
    candidates: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> list[str]:
    issues: list[str] = []
    if summary.get("track_id") != config["track_id"]:
        issues.append("SUMMARY_TRACK_ID_MISMATCH")
    if summary.get("registered_prediction_count") != len(registry_rows):
        issues.append("SUMMARY_REGISTRY_COUNT_MISMATCH")
    if summary.get("new_prediction_created_today") is not bool(
        config["new_prediction_created_today"]
    ):
        issues.append("SUMMARY_NEW_PREDICTION_FLAG_MISMATCH")
    if summary.get("model_update_allowed") is not False:
        issues.append("MODEL_UPDATE_LOCK_MISSING")
    schedule_key = f"candidate_schedule_{str(config['next_live_target_date']).replace('-', '_')}"
    if summary.get(schedule_key) != list(candidates):
        issues.append("CANDIDATE_SCHEDULE_MISMATCH")
    expected_hashes = {
        row["prediction_id"]: canonical_record_hash(row, config["registry_fields"])
        for row in registry_rows
    }
    if summary.get("registry_record_sha256") != expected_hashes:
        issues.append("REGISTRY_RECORD_HASH_MISMATCH")
    expected_window_names = {
        *(f"last_{int(size)}" for size in config["performance"]["windows"]),
        "all",
    }
    actual_windows = set(summary.get("performance", {}).get("windows", {}))
    if actual_windows != expected_window_names:
        issues.append("PERFORMANCE_WINDOWS_MISMATCH")
    return issues


def validate_files(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    config = load_config(project_root)
    protected_before = verify_protected_sources(project_root, config)
    frozen_headers, frozen_rows = read_csv(project_root / config["legacy"]["source_path"])
    if sha256(project_root / config["legacy"]["source_path"]) != config["legacy"][
        "source_sha256"
    ]:
        raise PolicyViolation("Legacy donmuş tahmin kaynağı hash eşleşmiyor")
    _, universe_rows = read_csv(project_root / config["universe_path"])
    registry_headers, registry_rows = read_csv(project_root / config["registry_path"])
    summary = json.loads(
        (project_root / config["performance_summary_path"]).read_text(encoding="utf-8")
    )
    candidates = calculate_candidates(config, universe_rows)
    issues = validate_registry_records(
        config, frozen_rows, universe_rows, registry_headers, registry_rows
    )
    issues.extend(validate_summary(config, registry_rows, candidates, summary))
    protected_after = verify_protected_sources(project_root, config)
    if protected_before != protected_after:
        raise PolicyViolation("Korunan kaynaklar validation sırasında değişti")
    return {
        "valid": not issues,
        "issues": issues,
        "registry_prediction_count": len(registry_rows),
        "legacy_prediction_count": len(frozen_rows),
        "legacy_source_headers": frozen_headers,
        "legacy_predictions_linked": [row["prediction_id"] for row in registry_rows[:5]]
        == list(config["legacy"]["expected_prediction_ids"]),
        f"candidate_schedule_{str(config['next_live_target_date']).replace('-', '_')}": candidates,
        "standard_cutoff": f"{config['standard_cutoff_local_time']} {config['timezone']}",
        "new_prediction_created_today": bool(config["new_prediction_created_today"]),
        "model_update_allowed": False,
        "protected_source_count": len(protected_before),
        "protected_sources_unchanged": True,
        "registry_sha256": sha256(project_root / config["registry_path"]),
        "performance_summary_sha256": sha256(
            project_root / config["performance_summary_path"]
        ),
    }


def result_json(result: Mapping[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)

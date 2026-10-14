"""Dondurulmuş tahminler için deterministik ve geriye dönük güvenli değerlendirme."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import statistics
import tempfile
import tomllib
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable, Mapping

from .guards import (
    PolicyViolation,
    assert_safe_output_path,
    load_source_registry,
    verify_registered_sources,
)
from .inventory import file_fingerprint


PREDICTION_REQUIRED_FIELDS = [
    "prediction_id",
    "ticker",
    "prediction_timestamp",
    "data_cutoff_timestamp",
    "reference_price",
    "direction_prediction",
    "lower_bound",
    "upper_bound",
    "point_prediction",
    "prob_above_reference",
    "prob_above_ipo",
    "prob_limit_up",
    "prob_limit_down",
]

REALIZED_REQUIRED_FIELDS = [
    "ticker",
    "trading_date",
    "official_close",
    "close_source_name",
    "close_source_url",
    "source_type",
    "verification_status",
]

DIRECTION_RULES: dict[str, tuple[str, ...]] = {
    "yatay / hafif aşağı": ("BELOW", "EQUAL"),
    "yatay / hafif yukarı": ("ABOVE", "EQUAL"),
    "yatay / tavan korunabilir": ("EQUAL",),
}

EVALUATION_FIELDS = [
    "prediction_id",
    "ticker",
    "prediction_timestamp",
    "data_cutoff_timestamp",
    "reference_price",
    "direction_prediction",
    "direction_allowed_outcomes",
    "lower_bound",
    "upper_bound",
    "point_prediction",
    "prob_above_ipo",
    "prob_above_reference",
    "prob_limit_up",
    "prob_limit_down",
    "actual_close",
    "actual_trading_date",
    "actual_close_source_name",
    "actual_close_source_url",
    "actual_source_type",
    "actual_verification_status",
    "matching_status",
    "validation_warnings",
    "absolute_error",
    "absolute_percentage_error_pct",
    "interval_covered",
    "actual_vs_reference",
    "direction_correct",
    "ipo_above_event_actual",
    "ipo_above_prediction_correct",
    "limit_up_event_actual",
    "limit_down_event_actual",
    "brier_reference_event",
    "brier_ipo_event",
    "brier_limit_up_event",
    "brier_limit_down_event",
    "evaluation_status",
]

BENCHMARK_FIELDS = [
    "prediction_id",
    "ticker",
    "actual_close",
    "model_prediction",
    "model_absolute_error",
    "naive_1_prediction",
    "naive_1_absolute_error",
    "model_beats_naive_1",
    "naive_2_prediction",
    "naive_2_absolute_error",
    "model_beats_naive_2",
    "naive_2_status",
    "actual_verification_status",
]

SIX_DP = Decimal("0.000001")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise PolicyViolation(f"CSV başlığı yok: {path}")
        rows = [dict(row) for row in reader]
        return rows, list(reader.fieldnames)


def _require_fields(actual: Iterable[str], required: Iterable[str], label: str) -> None:
    missing = [field for field in required if field not in actual]
    if missing:
        raise PolicyViolation(f"{label} zorunlu sütunları eksik: {missing}")


def _unique_by_ticker(rows: Iterable[Mapping[str, str]], label: str) -> dict[str, Mapping[str, str]]:
    indexed: dict[str, Mapping[str, str]] = {}
    for row in rows:
        ticker = (row.get("ticker") or "").strip().upper()
        if not ticker:
            raise PolicyViolation(f"{label} içinde boş ticker var")
        if ticker in indexed:
            raise PolicyViolation(f"{label} içinde yinelenen ticker: {ticker}")
        indexed[ticker] = row
    return indexed


def _decimal(value: str | None, field: str, ticker: str) -> Decimal:
    if value is None or not value.strip():
        raise PolicyViolation(f"{ticker} için eksik sayısal alan: {field}")
    try:
        return Decimal(value.strip())
    except InvalidOperation as exc:
        raise PolicyViolation(f"{ticker} için geçersiz sayısal alan {field}: {value}") from exc


def _probability(value: str | None, field: str, ticker: str) -> Decimal:
    parsed = _decimal(value, field, ticker)
    if parsed < 0 or parsed > 1:
        raise PolicyViolation(f"{ticker} için olasılık [0,1] dışında: {field}")
    return parsed


def _relation(actual: Decimal, reference: Decimal) -> str:
    if actual > reference:
        return "ABOVE"
    if actual < reference:
        return "BELOW"
    return "EQUAL"


def _normalized_direction(value: str) -> str:
    return " ".join(value.split()).casefold()


def _direction_result(direction: str, actual_relation: str) -> tuple[str, str]:
    allowed = DIRECTION_RULES.get(_normalized_direction(direction))
    if allowed is None:
        return "NOT_EVALUABLE_UNMAPPED_DIRECTION", ""
    return ("TRUE" if actual_relation in allowed else "FALSE"), "|".join(allowed)


def _quantized(value: Decimal) -> Decimal:
    return value.quantize(SIX_DP, rounding=ROUND_HALF_UP)


def _decimal_text(value: Decimal | None) -> str:
    if value is None:
        return ""
    quantized = _quantized(value)
    text = format(quantized, "f").rstrip("0").rstrip(".")
    return text or "0"


def _mean(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def _rate(true_count: int, eligible_count: int) -> Decimal | None:
    if eligible_count == 0:
        return None
    return Decimal(true_count) / Decimal(eligible_count) * Decimal("100")


def _metric(value: Decimal | int | None, eligible_count: int, unit: str, status: str = "CALCULATED") -> dict[str, Any]:
    if value is None:
        return {"status": status, "value": None, "eligible_count": eligible_count, "unit": unit}
    if isinstance(value, Decimal):
        numeric: int | float = float(_quantized(value))
    else:
        numeric = value
    return {"status": status, "value": numeric, "eligible_count": eligible_count, "unit": unit}


def _csv_text(rows: Iterable[Mapping[str, Any]], fieldnames: list[str]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _atomic_write(
    path: Path,
    content: str,
    *,
    output_dir: Path,
    allowed_extensions: Iterable[str],
    bom: bool = False,
) -> None:
    assert_safe_output_path(path, output_dir, allowed_extensions)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8-sig" if bom else "utf-8",
        newline="",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(content)
        temporary = handle.name
    os.replace(temporary, path)


def _evaluate_pair(
    prediction: Mapping[str, str],
    realized: Mapping[str, str],
    accepted_actual_statuses: set[str],
) -> tuple[dict[str, str], dict[str, str], dict[str, Decimal | bool | str]]:
    ticker = prediction["ticker"].strip().upper()
    warnings: list[str] = []
    actual_status = realized["verification_status"].strip()
    if actual_status not in accepted_actual_statuses:
        raise PolicyViolation(f"{ticker} gerçekleşme statüsü değerlendirmeye uygun değil: {actual_status}")
    if actual_status == "SECONDARY_VERIFIED":
        warnings.append("SECONDARY_VERIFIED_NOT_OFFICIAL_BIST")

    prediction_timestamp = prediction["prediction_timestamp"].strip()
    cutoff_timestamp = prediction["data_cutoff_timestamp"].strip()
    if cutoff_timestamp > prediction_timestamp:
        raise PolicyViolation(f"{ticker} veri kesim zamanı tahmin zamanından sonra")

    reference = _decimal(prediction["reference_price"], "reference_price", ticker)
    lower = _decimal(prediction["lower_bound"], "lower_bound", ticker)
    upper = _decimal(prediction["upper_bound"], "upper_bound", ticker)
    point = _decimal(prediction["point_prediction"], "point_prediction", ticker)
    actual = _decimal(realized["official_close"], "official_close", ticker)
    if lower > upper:
        raise PolicyViolation(f"{ticker} alt bant üst banttan büyük")
    if actual == 0:
        raise PolicyViolation(f"{ticker} gerçek kapanış sıfır; yüzde hata hesaplanamaz")

    prob_reference = _probability(prediction["prob_above_reference"], "prob_above_reference", ticker)
    prob_ipo = _probability(prediction["prob_above_ipo"], "prob_above_ipo", ticker)
    prob_limit_up = _probability(prediction["prob_limit_up"], "prob_limit_up", ticker)
    prob_limit_down = _probability(prediction["prob_limit_down"], "prob_limit_down", ticker)

    absolute_error = abs(point - actual)
    absolute_percentage_error = absolute_error / abs(actual) * Decimal("100")
    interval_covered = lower <= actual <= upper
    actual_relation = _relation(actual, reference)
    direction_correct, allowed_outcomes = _direction_result(
        prediction["direction_prediction"], actual_relation
    )
    if direction_correct.startswith("NOT_EVALUABLE"):
        warnings.append(direction_correct)

    reference_event = Decimal("1") if actual_relation == "ABOVE" else Decimal("0")
    brier_reference = (prob_reference - reference_event) ** 2
    naive_1_error = abs(reference - actual)
    model_beats_naive_1 = absolute_error < naive_1_error

    evaluation_row = {
        "prediction_id": prediction["prediction_id"],
        "ticker": ticker,
        "prediction_timestamp": prediction_timestamp,
        "data_cutoff_timestamp": cutoff_timestamp,
        "reference_price": prediction["reference_price"].strip(),
        "direction_prediction": prediction["direction_prediction"],
        "direction_allowed_outcomes": allowed_outcomes,
        "lower_bound": prediction["lower_bound"].strip(),
        "upper_bound": prediction["upper_bound"].strip(),
        "point_prediction": prediction["point_prediction"].strip(),
        "prob_above_ipo": prediction["prob_above_ipo"].strip(),
        "prob_above_reference": prediction["prob_above_reference"].strip(),
        "prob_limit_up": prediction["prob_limit_up"].strip(),
        "prob_limit_down": prediction["prob_limit_down"].strip(),
        "actual_close": realized["official_close"].strip(),
        "actual_trading_date": realized["trading_date"],
        "actual_close_source_name": realized["close_source_name"],
        "actual_close_source_url": realized["close_source_url"],
        "actual_source_type": realized["source_type"],
        "actual_verification_status": actual_status,
        "matching_status": "MATCHED_BY_TICKER",
        "validation_warnings": ";".join(warnings),
        "absolute_error": _decimal_text(absolute_error),
        "absolute_percentage_error_pct": _decimal_text(absolute_percentage_error),
        "interval_covered": "TRUE" if interval_covered else "FALSE",
        "actual_vs_reference": actual_relation,
        "direction_correct": direction_correct,
        "ipo_above_event_actual": "NOT_EVALUABLE_MISSING_FROZEN_IPO_PRICE",
        "ipo_above_prediction_correct": "NOT_EVALUABLE_MISSING_FROZEN_IPO_PRICE",
        "limit_up_event_actual": "NOT_EVALUABLE_MISSING_VERIFIED_LIMIT_BASE",
        "limit_down_event_actual": "NOT_EVALUABLE_MISSING_VERIFIED_LIMIT_BASE",
        "brier_reference_event": _decimal_text(brier_reference),
        "brier_ipo_event": "NOT_EVALUABLE_MISSING_FROZEN_IPO_PRICE",
        "brier_limit_up_event": "NOT_EVALUABLE_MISSING_VERIFIED_LIMIT_BASE",
        "brier_limit_down_event": "NOT_EVALUABLE_MISSING_VERIFIED_LIMIT_BASE",
        "evaluation_status": "CALCULATED_SECONDARY_VERIFIED_NOT_OFFICIAL_BIST",
    }
    benchmark_row = {
        "prediction_id": prediction["prediction_id"],
        "ticker": ticker,
        "actual_close": realized["official_close"].strip(),
        "model_prediction": prediction["point_prediction"].strip(),
        "model_absolute_error": _decimal_text(absolute_error),
        "naive_1_prediction": prediction["reference_price"].strip(),
        "naive_1_absolute_error": _decimal_text(naive_1_error),
        "model_beats_naive_1": "TRUE" if model_beats_naive_1 else "FALSE",
        "naive_2_prediction": "",
        "naive_2_absolute_error": "",
        "model_beats_naive_2": "NOT_EVALUABLE",
        "naive_2_status": "NOT_EVALUABLE_MISSING_PREVIOUS_OFFICIAL_CLOSE",
        "actual_verification_status": actual_status,
    }
    raw_metrics: dict[str, Decimal | bool | str] = {
        "absolute_error": absolute_error,
        "absolute_percentage_error": absolute_percentage_error,
        "interval_covered": interval_covered,
        "direction_correct": direction_correct,
        "model_beats_naive_1": model_beats_naive_1,
        "brier_reference": brier_reference,
    }
    return evaluation_row, benchmark_row, raw_metrics


def _report(
    *,
    evaluation_id: str,
    evaluation_rows: list[dict[str, str]],
    benchmark_rows: list[dict[str, str]],
    metrics: Mapping[str, Any],
    input_integrity: Mapping[str, Any],
    protected_integrity: Mapping[str, Any],
) -> str:
    lines = [
        f"# {evaluation_id}",
        "",
        "> İlk performans değerlendirmesi beş `SECONDARY_VERIFIED` kapanışla yapılmıştır. Bu statü resmî Borsa İstanbul doğrulaması değildir ve raporda öyle gösterilmemiştir.",
        "",
        "## Eşleştirme ve kapsam",
        "",
        "Tahmin ve gerçekleşme satırları yalnız `ticker` ile, bire bir ve tekil kayıt koşuluyla eşleştirildi. QUICK, METEN, ALBTN, MASFN ve KARCL dışında kayıt değerlendirilmedi.",
        "",
        "Gerçekleşen kapanışlar yalnız sonuç değişkenidir; geçmiş tahmin girdileri veya yön kuralları değiştirilmedi.",
        "",
        "## Yön değerlendirme kuralı",
        "",
        "Gerçek yön, `actual_close` ile `reference_price` değerlerinin tam Decimal karşılaştırmasıyla `ABOVE`, `BELOW` veya `EQUAL` olarak belirlendi. Bileşik tahmin ifadeleri tek sınıfa zorlanmadı; aşağıdaki izinli sonuç kümeleri kullanıldı:",
        "",
        "| Dondurulmuş ifade | Kabul edilen gerçekleşmeler |",
        "|---|---|",
        "| Yatay / hafif aşağı | BELOW veya EQUAL |",
        "| Yatay / hafif yukarı | ABOVE veya EQUAL |",
        "| Yatay / tavan korunabilir | EQUAL |",
        "",
        "Bu üç ifade dışında bir yön metni görülürse sonuç `NOT_EVALUABLE_UNMAPPED_DIRECTION` olur.",
        "",
        "Kaynak tahmin ve gerçekleşme değerleri çıktı tablolarında aynen korunmuştur. Hesaplamalar bu ham Decimal değerleriyle yapılmış, hesaplanan hata ve metrik sunumları `ROUND_HALF_UP` yöntemiyle altı ondalığa yuvarlanmıştır.",
        "",
        "## Hisse bazında değerlendirme",
        "",
        "| Hisse | Tahmin zamanı | Cutoff | Referans | Yön / izinli | Bant | Nokta | P(arz üstü) | P(ref üstü) | P(tavan) | P(taban) | Gerçek kapanış | Doğrulama | Mutlak hata | APE % | Kapsama | Ref ilişkisi | Yön doğru |",
        "|---|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---|---|---|",
    ]
    for row in evaluation_rows:
        lines.append(
            f"| {row['ticker']} | {row['prediction_timestamp']} | {row['data_cutoff_timestamp']} | "
            f"{row['reference_price']} | {row['direction_prediction']} / {row['direction_allowed_outcomes']} | "
            f"{row['lower_bound']}–{row['upper_bound']} | {row['point_prediction']} | "
            f"{row['prob_above_ipo']} | {row['prob_above_reference']} | {row['prob_limit_up']} | "
            f"{row['prob_limit_down']} | {row['actual_close']} | {row['actual_verification_status']} | "
            f"{row['absolute_error']} | {row['absolute_percentage_error_pct']} | "
            f"{row['interval_covered']} | {row['actual_vs_reference']} | {row['direction_correct']} |"
        )
    lines.extend([
        "",
        "## Naif benchmarklar",
        "",
        "| Hisse | Model hata | Naif 1 hata | Model Naif 1'i geçti | Naif 2 |",
        "|---|---:|---:|---|---|",
    ])
    for row in benchmark_rows:
        lines.append(
            f"| {row['ticker']} | {row['model_absolute_error']} | {row['naive_1_absolute_error']} | "
            f"{row['model_beats_naive_1']} | {row['naive_2_status']} |"
        )
    lines.extend([
        "",
        "## Toplu metrikler",
        "",
        "| Metrik | Değer | Uygun gözlem | Durum |",
        "|---|---:|---:|---|",
    ])
    for name, metric in metrics.items():
        lines.append(
            f"| `{name}` | {metric['value'] if metric['value'] is not None else 'NOT_EVALUABLE'} | "
            f"{metric['eligible_count']} | {metric['status']} |"
        )
    lines.extend([
        "",
        "## Hesaplanamayan olaylar",
        "",
        "- Arz üstü/altı doğruluğu ve Brier skoru: dondurulmuş tahmin CSV'sinde halka arz fiyatı yok.",
        "- Tavan ve taban olayları/Brier skorları: doğrulanmış baz fiyat veya günlük limit bilgisi yok.",
        "- Naif 2 ve Naif 2 karşılaştırma oranı: önceki resmî kapanış yok.",
        "",
        "## Giriş dosyası SHA-256 kayıtları",
        "",
        "| Dosya | Beklenen | Önce | Sonra | Durum |",
        "|---|---|---|---|---|",
    ])
    for name, record in input_integrity.items():
        lines.append(
            f"| `{name}` | `{record['expected_sha256']}` | `{record['before_sha256']}` | "
            f"`{record['after_sha256']}` | **{record['status']}** |"
        )
    lines.extend([
        "",
        "## Korunan kaynak Excel dosyaları",
        "",
        "| Dosya | Önce | Sonra | Durum |",
        "|---|---|---|---|",
    ])
    for name, record in protected_integrity.items():
        lines.append(
            f"| `{name}` | `{record['before_sha256']}` | `{record['after_sha256']}` | **{record['status']}** |"
        )
    lines.extend([
        "",
        "Model ağırlıkları, tahmin kayıtları, gerçekleşme dosyası ve kaynak Excel dosyaları değiştirilmedi. Yeni tahmin veya benzer şirket seçimi yapılmadı.",
        "",
    ])
    return "\n".join(lines)


def run_evaluation(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    with (project_root / "config" / "evaluation_2026-08-06_1335.toml").open("rb") as handle:
        config = tomllib.load(handle)["evaluation"]
    with (project_root / "config" / "audit.toml").open("rb") as handle:
        audit_config = tomllib.load(handle)
    policy = audit_config["policy"]

    prediction_path = (project_root / config["prediction_input"]).resolve()
    realized_path = (project_root / config["realized_input"]).resolve()
    if not prediction_path.is_relative_to(project_root) or not realized_path.is_relative_to(project_root):
        raise PolicyViolation("Giriş dosyaları proje kökü dışında olamaz")
    input_paths = {
        prediction_path.name: (prediction_path, config["prediction_input_sha256"]),
        realized_path.name: (realized_path, config["realized_input_sha256"]),
    }
    input_before = {name: file_fingerprint(path) for name, (path, _) in input_paths.items()}
    for name, (_, expected) in input_paths.items():
        if input_before[name]["sha256"] != expected:
            raise PolicyViolation(
                f"Giriş SHA-256 beklenen değerle eşleşmiyor: {name}; "
                f"beklenen={expected}, bulunan={input_before[name]['sha256']}"
            )

    registry = load_source_registry(project_root / policy["source_registry"])
    protected_paths = sorted(project_root / name for name in registry)
    protected_before = {path: file_fingerprint(path) for path in protected_paths}
    verify_registered_sources(
        protected_paths,
        protected_before,
        registry,
        require_exact_set=True,
        frozen_name_markers=policy["frozen_name_markers"],
    )

    predictions, prediction_headers = _read_csv(prediction_path)
    realized_rows, realized_headers = _read_csv(realized_path)
    _require_fields(prediction_headers, PREDICTION_REQUIRED_FIELDS, "Tahmin CSV")
    _require_fields(realized_headers, REALIZED_REQUIRED_FIELDS, "Gerçekleşme CSV")
    predictions_by_ticker = _unique_by_ticker(predictions, "Tahmin CSV")
    realized_by_ticker = _unique_by_ticker(realized_rows, "Gerçekleşme CSV")

    target_tickers = list(config["target_tickers"])
    target_set = set(target_tickers)
    if set(predictions_by_ticker) != target_set:
        raise PolicyViolation(
            f"Tahmin ticker kümesi hedefle eşleşmiyor: {sorted(predictions_by_ticker)}"
        )
    if set(realized_by_ticker) != target_set:
        raise PolicyViolation(
            f"Gerçekleşme ticker kümesi hedefle eşleşmiyor: {sorted(realized_by_ticker)}"
        )

    evaluation_rows: list[dict[str, str]] = []
    benchmark_rows: list[dict[str, str]] = []
    raw_metrics: list[dict[str, Decimal | bool | str]] = []
    accepted_actual_statuses = set(config["accepted_actual_statuses"])
    for ticker in target_tickers:
        prediction = predictions_by_ticker[ticker]
        realized = realized_by_ticker[ticker]
        if realized["trading_date"] != config["target_trading_date"]:
            raise PolicyViolation(
                f"{ticker} gerçekleşme tarihi hedefle eşleşmiyor: {realized['trading_date']}"
            )
        evaluation_row, benchmark_row, raw = _evaluate_pair(
            prediction,
            realized,
            accepted_actual_statuses,
        )
        evaluation_rows.append(evaluation_row)
        benchmark_rows.append(benchmark_row)
        raw_metrics.append(raw)

    absolute_errors = [item["absolute_error"] for item in raw_metrics]
    percentage_errors = [item["absolute_percentage_error"] for item in raw_metrics]
    direction_results = [item["direction_correct"] for item in raw_metrics]
    evaluable_directions = [value for value in direction_results if value in {"TRUE", "FALSE"}]
    coverage_values = [bool(item["interval_covered"]) for item in raw_metrics]
    naive_1_values = [bool(item["model_beats_naive_1"]) for item in raw_metrics]
    reference_brier = [item["brier_reference"] for item in raw_metrics]

    metrics = {
        "prediction_count": _metric(len(raw_metrics), len(raw_metrics), "count"),
        "direction_accuracy_pct": _metric(
            _rate(evaluable_directions.count("TRUE"), len(evaluable_directions)),
            len(evaluable_directions),
            "percent",
        ),
        "mean_absolute_error": _metric(_mean(absolute_errors), len(absolute_errors), "price"),
        "mean_absolute_percentage_error_pct": _metric(
            _mean(percentage_errors), len(percentage_errors), "percent"
        ),
        "median_absolute_percentage_error_pct": _metric(
            statistics.median(percentage_errors), len(percentage_errors), "percent"
        ),
        "interval_coverage_pct": _metric(
            _rate(sum(coverage_values), len(coverage_values)), len(coverage_values), "percent"
        ),
        "model_beats_naive_1_pct": _metric(
            _rate(sum(naive_1_values), len(naive_1_values)), len(naive_1_values), "percent"
        ),
        "model_beats_naive_2_pct": _metric(
            None,
            0,
            "percent",
            "NOT_EVALUABLE_MISSING_PREVIOUS_OFFICIAL_CLOSE",
        ),
        "brier_reference_above": _metric(
            _mean(reference_brier), len(reference_brier), "brier_score"
        ),
        "brier_ipo_above": _metric(
            None, 0, "brier_score", "NOT_EVALUABLE_MISSING_FROZEN_IPO_PRICE"
        ),
        "brier_limit_up": _metric(
            None, 0, "brier_score", "NOT_EVALUABLE_MISSING_VERIFIED_LIMIT_BASE"
        ),
        "brier_limit_down": _metric(
            None, 0, "brier_score", "NOT_EVALUABLE_MISSING_VERIFIED_LIMIT_BASE"
        ),
    }

    input_after = {name: file_fingerprint(path) for name, (path, _) in input_paths.items()}
    protected_after = {path: file_fingerprint(path) for path in protected_paths}
    if input_before != input_after:
        raise PolicyViolation("Giriş CSV parmak izi değerlendirme sırasında değişti")
    if protected_before != protected_after:
        raise PolicyViolation("Kaynak Excel parmak izi değerlendirme sırasında değişti")
    verify_registered_sources(
        protected_paths,
        protected_after,
        registry,
        require_exact_set=True,
        frozen_name_markers=policy["frozen_name_markers"],
    )

    input_integrity = {
        name: {
            "path": str(path),
            "expected_sha256": expected,
            "before_sha256": input_before[name]["sha256"],
            "after_sha256": input_after[name]["sha256"],
            "status": "UNCHANGED",
        }
        for name, (path, expected) in input_paths.items()
    }
    protected_integrity = {
        path.name: {
            "path": str(path),
            "before_sha256": protected_before[path]["sha256"],
            "after_sha256": protected_after[path]["sha256"],
            "status": "UNCHANGED",
        }
        for path in protected_paths
    }
    metrics_payload = {
        "schema_version": 1,
        "evaluation_id": config["evaluation_id"],
        "evaluation_status": "PRELIMINARY_SECONDARY_VERIFIED_NOT_OFFICIAL_BIST",
        "target_tickers": target_tickers,
        "matching": {
            "key": "ticker",
            "prediction_rows": len(predictions),
            "realized_rows": len(realized_rows),
            "matched_rows": len(evaluation_rows),
            "unmatched_rows": 0,
        },
        "direction_rule": {
            "actual_relation": "exact Decimal comparison: ABOVE, BELOW, EQUAL",
            "frozen_label_rules": {
                label: list(outcomes) for label, outcomes in DIRECTION_RULES.items()
            },
            "unmapped_label": "NOT_EVALUABLE_UNMAPPED_DIRECTION",
        },
        "metrics": metrics,
        "non_evaluable": {
            "ipo_above": "missing frozen IPO price in the two authorized input files",
            "limit_up": "missing verified limit/base-price information",
            "limit_down": "missing verified limit/base-price information",
            "naive_2": "missing previous official close",
        },
        "source_integrity": {
            "inputs": input_integrity,
            "protected_excel": protected_integrity,
            "all_unchanged": True,
        },
    }

    output_dir = (project_root / config["output_dir"]).resolve()
    allowed_extensions = policy["allowed_output_extensions"]
    outputs = {
        "evaluation": output_dir / "evaluation_2026-08-06_1335.csv",
        "benchmark": output_dir / "benchmark_comparison_2026-08-06_1335.csv",
        "metrics": output_dir / "evaluation_metrics_2026-08-06_1335.json",
        "report": output_dir / "EVALUATION_REPORT_2026-08-06_1335.md",
    }
    report = _report(
        evaluation_id=config["evaluation_id"],
        evaluation_rows=evaluation_rows,
        benchmark_rows=benchmark_rows,
        metrics=metrics,
        input_integrity=input_integrity,
        protected_integrity=protected_integrity,
    )
    _atomic_write(
        outputs["evaluation"],
        _csv_text(evaluation_rows, EVALUATION_FIELDS),
        output_dir=output_dir,
        allowed_extensions=allowed_extensions,
        bom=True,
    )
    _atomic_write(
        outputs["benchmark"],
        _csv_text(benchmark_rows, BENCHMARK_FIELDS),
        output_dir=output_dir,
        allowed_extensions=allowed_extensions,
        bom=True,
    )
    _atomic_write(
        outputs["metrics"],
        json.dumps(metrics_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        output_dir=output_dir,
        allowed_extensions=allowed_extensions,
    )
    _atomic_write(
        outputs["report"],
        report,
        output_dir=output_dir,
        allowed_extensions=allowed_extensions,
    )
    return {
        "evaluation_status": metrics_payload["evaluation_status"],
        "metrics": metrics,
        "source_integrity_all_unchanged": True,
        "outputs": {name: str(path) for name, path in outputs.items()},
    }

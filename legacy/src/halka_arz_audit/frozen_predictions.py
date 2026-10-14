"""13:35 dondurulmuş tahminlerini formül hesaplamadan çıkarır."""

from __future__ import annotations

import csv
import io
import os
import tempfile
import tomllib
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable, Mapping

from .guards import (
    PolicyViolation,
    assert_safe_output_path,
    load_source_registry,
    verify_registered_sources,
)
from .inventory import file_fingerprint
from .ooxml_reader import CellRecord, SheetRecords, read_workbook_cells


OUTPUT_FIELDS = [
    "prediction_id",
    "ticker",
    "prediction_timestamp",
    "data_cutoff_timestamp",
    "reference_price",
    "data_age_minutes",
    "forecast_target",
    "direction_prediction",
    "lower_bound",
    "upper_bound",
    "point_prediction",
    "prob_above_reference",
    "prob_above_ipo",
    "prob_limit_up",
    "prob_limit_down",
    "risk_label",
    "confidence",
    "source_workbook",
    "source_sheet",
    "source_cells",
    "extraction_status",
]

FIELD_HEADERS: OrderedDict[str, str] = OrderedDict([
    ("prediction_id", "Kayıt ID"),
    ("ticker", "Hisse"),
    ("prediction_timestamp", "Tahmin Saati"),
    ("data_cutoff_timestamp", "Kullanılan Veri Saati"),
    ("reference_price", "Tahmin Anındaki Fiyat (TL)"),
    ("data_age_minutes", "Verinin Tahmin Anındaki Yaşı (dk)"),
    ("forecast_target", "Hedef"),
    ("direction_prediction", "Tahmin Anındaki Fiyattan Kapanışa Beklenen Yön"),
    ("lower_bound", "Beklenen Kapanış Alt (TL)"),
    ("upper_bound", "Beklenen Kapanış Üst (TL)"),
    ("point_prediction", "Model Nokta Tahmini (TL)"),
    ("prob_above_reference", "P(Kapanış > Tahmin Fiyatı)"),
    ("prob_above_ipo", "P(Kapanış > Halka Arz Fiyatı)"),
    ("prob_limit_up", "Tavan Kapanış Olasılığı"),
    ("prob_limit_down", "Taban Kapanış Olasılığı"),
    ("risk_label", "Risk Etiketi"),
    ("confidence", "Güven Düzeyi"),
])

PROVENANCE_FIELDS = [
    "prediction_id",
    "field_name",
    "workbook",
    "sheet",
    "cell_coordinate",
    "raw_value",
    "formula_if_any",
]

CONFLICT_FIELDS = [
    "prediction_id",
    "ticker",
    "field_name",
    "main_workbook",
    "main_sheet",
    "main_cell",
    "main_raw_value",
    "main_formula_if_any",
    "ic_workbook",
    "ic_sheet",
    "ic_cell",
    "ic_raw_value",
    "ic_formula_if_any",
    "conflict_type",
]


def _normalized_label(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()


def _column_letters(number: int) -> str:
    letters: list[str] = []
    while number > 0:
        number, remainder = divmod(number - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))


def _cell_coordinate(column: int, row: int) -> str:
    return f"{_column_letters(column)}{row}"


def _header_columns(sheet: SheetRecords, header_row: int) -> dict[str, int]:
    columns = {
        _normalized_label(cell.value): cell.column
        for cell in sheet.cells.values()
        if cell.row == header_row and cell.value not in {None, ""}
    }
    missing = [
        source_header
        for source_header in FIELD_HEADERS.values()
        if _normalized_label(source_header) not in columns
    ]
    if missing:
        raise PolicyViolation(f"Dondurulmuş sayfada beklenen başlıklar eksik: {missing}")
    return columns


def _source_field_cells(
    sheet: SheetRecords,
    row_number: int,
    header_columns: Mapping[str, int],
) -> dict[str, tuple[str, CellRecord | None]]:
    result: dict[str, tuple[str, CellRecord | None]] = {}
    for field_name, source_header in FIELD_HEADERS.items():
        column = header_columns[_normalized_label(source_header)]
        coordinate = _cell_coordinate(column, row_number)
        result[field_name] = (coordinate, sheet.cells.get(coordinate))
    return result


def _extract_rows(
    *,
    workbook_name: str,
    sheet: SheetRecords,
    header_row: int,
    target_timestamp: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, dict[str, Any]]]:
    header_columns = _header_columns(sheet, header_row)
    timestamp_column = header_columns[_normalized_label(FIELD_HEADERS["prediction_timestamp"])]
    candidate_rows = sorted({
        cell.row
        for cell in sheet.cells.values()
        if cell.row > header_row
        and cell.column == timestamp_column
        and cell.value == target_timestamp
    })
    if not candidate_rows:
        raise PolicyViolation(f"{target_timestamp} için tahmin satırı bulunamadı")

    extracted: list[dict[str, str]] = []
    provenance: list[dict[str, str]] = []
    raw_by_prediction: dict[str, dict[str, Any]] = {}
    for row_number in candidate_rows:
        source_fields = _source_field_cells(sheet, row_number, header_columns)
        values: dict[str, str] = {}
        missing: list[str] = []
        formula_fields: list[str] = []
        source_cells: list[str] = []
        raw_fields: dict[str, dict[str, str]] = {}
        for field_name, (coordinate, cell) in source_fields.items():
            value = "" if cell is None or cell.value is None else str(cell.value)
            raw_value = "" if cell is None or cell.raw_value is None else str(cell.raw_value)
            formula = "" if cell is None or not cell.formula else f"={cell.formula}"
            values[field_name] = value
            source_cells.append(f"{field_name}={coordinate}")
            raw_fields[field_name] = {
                "coordinate": coordinate,
                "raw_value": raw_value,
                "formula": formula,
            }
            if not value:
                missing.append(field_name)
            if formula:
                formula_fields.append(field_name)

        prediction_id = values["prediction_id"]
        ticker = values["ticker"]
        if not prediction_id or not ticker:
            raise PolicyViolation(f"Satır {row_number} tahmin kimliği veya hisse kodu içermiyor")
        status_parts = ["extracted_read_only"]
        if formula_fields:
            status_parts.append("cached_formula_value:" + "+".join(formula_fields))
        if missing:
            status_parts.append("missing:" + "+".join(missing))

        output_row = {
            **values,
            "source_workbook": workbook_name,
            "source_sheet": sheet.name,
            "source_cells": ";".join(source_cells),
            "extraction_status": ";".join(status_parts),
        }
        extracted.append(output_row)
        raw_by_prediction[prediction_id] = {
            "ticker": ticker,
            "fields": raw_fields,
        }
        for field_name, raw_field in raw_fields.items():
            provenance.append({
                "prediction_id": prediction_id,
                "field_name": field_name,
                "workbook": workbook_name,
                "sheet": sheet.name,
                "cell_coordinate": raw_field["coordinate"],
                "raw_value": raw_field["raw_value"],
                "formula_if_any": raw_field["formula"],
            })
    return extracted, provenance, raw_by_prediction


def _compare_frozen_fields(
    main: Mapping[str, Mapping[str, Any]],
    cross_check: Mapping[str, Mapping[str, Any]],
    *,
    main_workbook: str,
    cross_check_workbook: str,
    sheet_name: str,
) -> list[dict[str, str]]:
    conflicts: list[dict[str, str]] = []
    for prediction_id, main_record in main.items():
        ic_record = cross_check.get(prediction_id)
        if ic_record is None:
            conflicts.append({
                "prediction_id": prediction_id,
                "ticker": str(main_record["ticker"]),
                "field_name": "__prediction__",
                "main_workbook": main_workbook,
                "main_sheet": sheet_name,
                "main_cell": "",
                "main_raw_value": "present",
                "main_formula_if_any": "",
                "ic_workbook": cross_check_workbook,
                "ic_sheet": sheet_name,
                "ic_cell": "",
                "ic_raw_value": "",
                "ic_formula_if_any": "",
                "conflict_type": "missing_in_cross_check",
            })
            continue
        for field_name in FIELD_HEADERS:
            main_field = main_record["fields"][field_name]
            ic_field = ic_record["fields"][field_name]
            value_differs = main_field["raw_value"] != ic_field["raw_value"]
            formula_differs = main_field["formula"] != ic_field["formula"]
            if not value_differs and not formula_differs:
                continue
            conflict_type = (
                "value_and_formula_difference"
                if value_differs and formula_differs
                else "value_difference" if value_differs else "formula_difference"
            )
            conflicts.append({
                "prediction_id": prediction_id,
                "ticker": str(main_record["ticker"]),
                "field_name": field_name,
                "main_workbook": main_workbook,
                "main_sheet": sheet_name,
                "main_cell": main_field["coordinate"],
                "main_raw_value": main_field["raw_value"],
                "main_formula_if_any": main_field["formula"],
                "ic_workbook": cross_check_workbook,
                "ic_sheet": sheet_name,
                "ic_cell": ic_field["coordinate"],
                "ic_raw_value": ic_field["raw_value"],
                "ic_formula_if_any": ic_field["formula"],
                "conflict_type": conflict_type,
            })
    for prediction_id, ic_record in cross_check.items():
        if prediction_id in main:
            continue
        conflicts.append({
            "prediction_id": prediction_id,
            "ticker": str(ic_record["ticker"]),
            "field_name": "__prediction__",
            "main_workbook": main_workbook,
            "main_sheet": sheet_name,
            "main_cell": "",
            "main_raw_value": "",
            "main_formula_if_any": "",
            "ic_workbook": cross_check_workbook,
            "ic_sheet": sheet_name,
            "ic_cell": "",
            "ic_raw_value": "present",
            "ic_formula_if_any": "",
            "conflict_type": "extra_in_cross_check_not_added_to_main",
        })
    return conflicts


def _csv_text(rows: Iterable[Mapping[str, Any]], fieldnames: list[str]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _atomic_write_text(
    path: Path,
    content: str,
    *,
    output_dir: Path,
    allowed_extensions: Iterable[str],
    utf8_bom: bool = False,
) -> None:
    assert_safe_output_path(path, output_dir, allowed_extensions)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoding = "utf-8-sig" if utf8_bom else "utf-8"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        newline="",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(content)
        temporary = handle.name
    os.replace(temporary, path)


def _report_markdown(
    *,
    main_workbook: str,
    cross_check_workbook: str,
    hash_only_workbook: str,
    source_sheet: str,
    target_timestamp: str,
    rows: list[dict[str, str]],
    conflicts: list[dict[str, str]],
    before: Mapping[Path, Mapping[str, Any]],
    after: Mapping[Path, Mapping[str, Any]],
) -> str:
    tickers = [row["ticker"] for row in rows]
    missing_by_prediction: list[str] = []
    for row in rows:
        missing = [field for field in FIELD_HEADERS if not row[field]]
        if missing:
            missing_by_prediction.append(f"- `{row['prediction_id']}`: {', '.join(missing)}")
    lines = [
        "# 13:35 Dondurulmuş Tahmin Çıkarım Raporu",
        "",
        "> Bu çalışma salt-okunur bir kayıt çıkarımıdır. Formüller yeniden hesaplanmadı; gerçekleşen kapanışlar, performans değerlendirmesi ve yeni tahminler dahil edilmedi.",
        "",
        "## Kaynak kapsamı",
        "",
        f"- Ana kaynak: `{main_workbook}` / `{source_sheet}`",
        f"- Çapraz kontrol: `{cross_check_workbook}` / `{source_sheet}`",
        f"- Yalnız hash kontrolü; çıkarıma katılmadı: `{hash_only_workbook}`",
        f"- Hedef dondurma zamanı: `{target_timestamp}`",
        "- Tahmin satırları, kaynak sayfadaki `Tahmin Saati` alanı hedef zamana eşit olan satırlardan kendiliğinden seçildi.",
        "",
        "## Sonuç",
        "",
        f"- Bulunan dondurulmuş tahmin: **{len(rows)}**",
        f"- Hisseler: **{', '.join(tickers)}**",
        f"- IC alan çatışması: **{len(conflicts)}**",
        "- Nokta tahminleri: XML içinde kayıtlı önbellek değerleri alındı; `AVERAGE(...)` formülleri provenance dosyasında saklandı ve çalıştırılmadı.",
        "",
        "## Eksik alanlar",
        "",
    ]
    lines.extend(missing_by_prediction or ["Kaynakta istenen 17 tahmin alanının tamamı beş kayıt için de bulundu."])
    lines.extend([
        "",
        "## Kaynak sütun eşlemesi",
        "",
        "| Çıktı alanı | Kaynak başlığı |",
        "|---|---|",
    ])
    for field_name, source_header in FIELD_HEADERS.items():
        lines.append(f"| `{field_name}` | {source_header} |")
    lines.extend([
        "",
        "## SHA-256 bütünlük kontrolü",
        "",
        "| Dosya | Önce | Sonra | Durum |",
        "|---|---|---|---|",
    ])
    for path in sorted(before, key=lambda item: item.name):
        before_hash = before[path]["sha256"]
        after_hash = after[path]["sha256"]
        status = "AYNI" if before[path] == after[path] else "FARKLI"
        lines.append(f"| `{path.name}` | `{before_hash}` | `{after_hash}` | **{status}** |")
    lines.extend([
        "",
        "## Veri sızıntısı sınırı",
        "",
        "Çıkarım kodu yalnız `13_35_Dondurma` sayfasını hücre düzeyinde okudu. `Kapanis_Sonrasi`, `Kapanis_Degerlendirme_v2` ve diğer gerçekleşme/değerlendirme sayfaları tahmin alanlarına kaynak yapılmadı.",
        "",
    ])
    return "\n".join(lines)


def run_frozen_extraction(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    with (project_root / "config" / "audit.toml").open("rb") as handle:
        configuration = tomllib.load(handle)
    policy = configuration["policy"]
    extraction = configuration["frozen_extraction"]
    registry_path = (project_root / policy["source_registry"]).resolve()
    registry = load_source_registry(registry_path)

    main_workbook = extraction["main_workbook"]
    cross_check_workbook = extraction["cross_check_workbook"]
    hash_only_workbook = extraction["hash_only_workbook"]
    configured_names = {main_workbook, cross_check_workbook, hash_only_workbook}
    if len(configured_names) != 3:
        raise PolicyViolation("Ana, çapraz kontrol ve hash-only çalışma kitapları farklı olmalıdır")
    if configured_names != set(registry):
        raise PolicyViolation("Dondurulmuş çıkarım kapsamı sabit kaynak kaydıyla eşleşmiyor")

    sources = sorted(project_root / name for name in registry)
    before = {path: file_fingerprint(path) for path in sources}
    registry_results = verify_registered_sources(
        sources,
        before,
        registry,
        require_exact_set=True,
        frozen_name_markers=policy["frozen_name_markers"],
    )
    if not registry_results[main_workbook]["frozen"]:
        raise PolicyViolation("Ana kaynak frozen=true olarak kayıtlı değil")
    if not registry_results[cross_check_workbook]["frozen"]:
        raise PolicyViolation("Çapraz kontrol kaynağı frozen=true olarak kayıtlı değil")

    sheet_name = extraction["source_sheet"]
    main_sheets = read_workbook_cells(
        project_root / main_workbook,
        include_sheets=[sheet_name],
    )
    cross_sheets = read_workbook_cells(
        project_root / cross_check_workbook,
        include_sheets=[sheet_name],
    )
    if sheet_name not in main_sheets or sheet_name not in cross_sheets:
        raise PolicyViolation(f"Çapraz kontrolde gerekli sayfa yok: {sheet_name}")

    rows, provenance, main_raw = _extract_rows(
        workbook_name=main_workbook,
        sheet=main_sheets[sheet_name],
        header_row=int(extraction["header_row"]),
        target_timestamp=extraction["target_prediction_timestamp"],
    )
    _, _, cross_raw = _extract_rows(
        workbook_name=cross_check_workbook,
        sheet=cross_sheets[sheet_name],
        header_row=int(extraction["header_row"]),
        target_timestamp=extraction["target_prediction_timestamp"],
    )
    conflicts = _compare_frozen_fields(
        main_raw,
        cross_raw,
        main_workbook=main_workbook,
        cross_check_workbook=cross_check_workbook,
        sheet_name=sheet_name,
    )

    after = {path: file_fingerprint(path) for path in sources}
    if before != after:
        raise PolicyViolation("Kaynak dosya parmak izi çıkarım sırasında değişti")
    verify_registered_sources(
        sources,
        after,
        registry,
        require_exact_set=True,
        frozen_name_markers=policy["frozen_name_markers"],
    )

    output_dir = (project_root / extraction["output_dir"]).resolve()
    allowed_extensions = policy["allowed_output_extensions"]
    outputs = {
        "predictions": output_dir / "frozen_predictions_2026-08-06_1335.csv",
        "conflicts": output_dir / "frozen_prediction_conflicts.csv",
        "provenance": output_dir / "frozen_prediction_provenance.csv",
        "report": output_dir / "FROZEN_EXTRACTION_REPORT.md",
    }
    report = _report_markdown(
        main_workbook=main_workbook,
        cross_check_workbook=cross_check_workbook,
        hash_only_workbook=hash_only_workbook,
        source_sheet=sheet_name,
        target_timestamp=extraction["target_prediction_timestamp"],
        rows=rows,
        conflicts=conflicts,
        before=before,
        after=after,
    )
    _atomic_write_text(
        outputs["predictions"],
        _csv_text(rows, OUTPUT_FIELDS),
        output_dir=output_dir,
        allowed_extensions=allowed_extensions,
        utf8_bom=True,
    )
    _atomic_write_text(
        outputs["conflicts"],
        _csv_text(conflicts, CONFLICT_FIELDS),
        output_dir=output_dir,
        allowed_extensions=allowed_extensions,
        utf8_bom=True,
    )
    _atomic_write_text(
        outputs["provenance"],
        _csv_text(provenance, PROVENANCE_FIELDS),
        output_dir=output_dir,
        allowed_extensions=allowed_extensions,
        utf8_bom=True,
    )
    _atomic_write_text(
        outputs["report"],
        report,
        output_dir=output_dir,
        allowed_extensions=allowed_extensions,
    )
    return {
        "prediction_count": len(rows),
        "tickers": [row["ticker"] for row in rows],
        "conflict_count": len(conflicts),
        "missing_fields": {
            row["prediction_id"]: [field for field in FIELD_HEADERS if not row[field]]
            for row in rows
        },
        "source_hashes_unchanged": before == after,
        "outputs": {name: str(path) for name, path in outputs.items()},
    }


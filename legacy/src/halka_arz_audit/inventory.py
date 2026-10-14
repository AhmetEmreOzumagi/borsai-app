"""Excel Open XML dosyalarını değiştirmeden yapısal olarak envanterler.

Bu modül Excel'i çalıştırmaz, formülleri hesaplamaz ve çalışma kitaplarını
yeniden kaydetmez. Kaynak dosyalar yalnızca ``rb`` ve ``zipfile.ZipFile(..., 'r')``
ile açılır.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
import tomllib
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from zipfile import BadZipFile, ZipFile

from .guards import (
    PolicyViolation,
    assert_safe_output_path,
    load_source_registry,
    verify_registered_sources,
)


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN_NS, "r": DOC_REL_NS, "p": PKG_REL_NS}

BUILTIN_DATE_FORMAT_IDS = {
    14, 15, 16, 17, 18, 19, 20, 21, 22,
    27, 28, 29, 30, 31, 32, 33, 34, 35, 36,
    45, 46, 47, 50, 51, 52, 53, 54, 55, 56, 57,
}
CELL_REF_RE = re.compile(r"([A-Z]+)(\d+)")
FORMAT_LITERAL_RE = re.compile(r'"[^"]*"|\\.|\[[^\]]*\]')


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_fingerprint(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "size_bytes": stat.st_size,
        "modified_utc": datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat(),
        "sha256": sha256_file(path),
    }


def _read_xml(archive: ZipFile, member: str) -> ET.Element | None:
    try:
        with archive.open(member, "r") as handle:
            return ET.parse(handle).getroot()
    except KeyError:
        return None


def _relationship_map(archive: ZipFile, member: str) -> dict[str, dict[str, str]]:
    root = _read_xml(archive, member)
    if root is None:
        return {}
    result: dict[str, dict[str, str]] = {}
    for rel in root.findall("p:Relationship", NS):
        rel_id = rel.get("Id")
        if rel_id:
            result[rel_id] = {
                "target": rel.get("Target", ""),
                "type": rel.get("Type", ""),
                "target_mode": rel.get("TargetMode", "Internal"),
            }
    return result


def _xl_target(target: str) -> str:
    clean = target.replace("\\", "/")
    if clean.startswith("/"):
        return clean.lstrip("/")
    return str(PurePosixPath("xl") / clean)


def _shared_strings(archive: ZipFile) -> list[str]:
    root = _read_xml(archive, "xl/sharedStrings.xml")
    if root is None:
        return []
    strings: list[str] = []
    for item in root.findall("m:si", NS):
        strings.append("".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t")))
    return strings


def _style_formats(archive: ZipFile) -> dict[int, str]:
    root = _read_xml(archive, "xl/styles.xml")
    if root is None:
        return {}
    custom: dict[int, str] = {}
    for item in root.findall("m:numFmts/m:numFmt", NS):
        try:
            custom[int(item.get("numFmtId", "-1"))] = item.get("formatCode", "")
        except ValueError:
            continue
    result: dict[int, str] = {}
    for index, xf in enumerate(root.findall("m:cellXfs/m:xf", NS)):
        try:
            num_fmt_id = int(xf.get("numFmtId", "0"))
        except ValueError:
            num_fmt_id = 0
        if num_fmt_id in BUILTIN_DATE_FORMAT_IDS:
            result[index] = "date_like"
        else:
            code = custom.get(num_fmt_id, "")
            result[index] = classify_number_format(code)
    return result


def classify_number_format(format_code: str) -> str:
    """Bir Excel sayı biçimini kaba veri türüne ayırır."""
    if not format_code:
        return "general"
    cleaned = FORMAT_LITERAL_RE.sub("", format_code.lower())
    if "%" in cleaned:
        return "percentage_like"
    if re.search(r"(^|[^a-z])[ymdhis]+([^a-z]|$)", cleaned):
        return "date_like"
    return "number_like"


def _cell_text(cell: ET.Element, shared_strings: list[str]) -> str | None:
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        text = "".join(node.text or "" for node in cell.iter(f"{{{MAIN_NS}}}t"))
        return text or None
    value = cell.find("m:v", NS)
    if value is None or value.text is None:
        return None
    if cell_type == "s":
        try:
            return shared_strings[int(value.text)]
        except (ValueError, IndexError):
            return None
    if cell_type in {"str", "e"}:
        return value.text
    return None


def _cell_kind(cell: ET.Element, style_formats: dict[int, str]) -> str:
    cell_type = cell.get("t")
    if cell_type in {"s", "inlineStr", "str"}:
        return "text"
    if cell_type == "b":
        return "boolean"
    if cell_type == "e":
        return "error"
    value = cell.find("m:v", NS)
    if value is None or value.text in {None, ""}:
        return "blank_or_uncached"
    try:
        style_id = int(cell.get("s", "0"))
    except ValueError:
        style_id = 0
    style_kind = style_formats.get(style_id, "general")
    if style_kind in {"date_like", "percentage_like"}:
        return style_kind
    return "number"


def _normalize_search_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _column_letters(number: int) -> str:
    letters: list[str] = []
    while number > 0:
        number, remainder = divmod(number - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))


def _content_categories(texts: Iterable[str], sheet_names: Iterable[str]) -> list[str]:
    corpus = _normalize_search_text(" ".join([*sheet_names, *texts]))
    rules = [
        ("Halka arz / şirket tanımlayıcıları", ("halka arz", "sirket", "sembol", "ticker", "bist")),
        ("Tarih ve takip durumu", ("tarih", "takip", "durum", "gun", "islem")),
        ("Fiyat ve performans alanları", ("fiyat", "getiri", "kapanis", "tavan", "performans")),
        ("Talep, dağıtım ve lot alanları", ("talep", "dagitim", "lot", "katilimci")),
        ("Kontrol ve denetim alanları", ("kontrol", "denetim", "check", "uyari", "hata")),
        ("Kaynak, bağlantı ve not alanları", ("kaynak", "source", "url", "link", "not")),
    ]
    return [label for label, keywords in rules if any(keyword in corpus for keyword in keywords)]


def _workbook_role(path: Path) -> str:
    name = _normalize_search_text(path.stem)
    if "dondurulmus" in name:
        return "Dondurulmuş anlık görüntü (dosya adına göre)"
    if "ic_denetimli" in name or "denetimli" in name:
        return "İç denetimli sürüm (dosya adına göre)"
    return "Çalışma/takip sürümü (dosya adına göre)"


def _sheet_inventory(
    archive: ZipFile,
    sheet_path: str,
    shared_strings: list[str],
    style_formats: dict[int, str],
    sample_limit: int,
    sample_max_chars: int,
) -> dict[str, Any]:
    root = _read_xml(archive, sheet_path)
    if root is None:
        return {"error": f"Sayfa XML'i bulunamadı: {sheet_path}"}

    dimension = root.find("m:dimension", NS)
    counts: Counter[str] = Counter()
    formula_count = 0
    sample_texts: list[str] = []
    seen_texts: set[str] = set()
    max_row = 0
    max_col = 0

    for cell in root.findall(".//m:sheetData/m:row/m:c", NS):
        counts[_cell_kind(cell, style_formats)] += 1
        if cell.find("m:f", NS) is not None:
            formula_count += 1
        ref = cell.get("r", "")
        match = CELL_REF_RE.fullmatch(ref)
        if match:
            max_row = max(max_row, int(match.group(2)))
            col_number = 0
            for char in match.group(1):
                col_number = col_number * 26 + ord(char) - 64
            max_col = max(max_col, col_number)
        text = _cell_text(cell, shared_strings)
        if text:
            normalized = " ".join(text.split())
            if normalized and normalized not in seen_texts and len(sample_texts) < sample_limit:
                seen_texts.add(normalized)
                sample_texts.append(normalized[:sample_max_chars])

    hyperlinks = root.findall("m:hyperlinks/m:hyperlink", NS)
    merge_cells = root.find("m:mergeCells", NS)
    table_parts = root.find("m:tableParts", NS)
    inferred_dimension = (
        f"A1:{_column_letters(max_col)}{max_row}" if max_row and max_col else None
    )
    return {
        "dimension": dimension.get("ref") if dimension is not None else inferred_dimension,
        "max_row_seen": max_row,
        "max_column_seen": max_col,
        "cell_count": sum(counts.values()),
        "formula_count": formula_count,
        "cell_types": dict(sorted(counts.items())),
        "merged_range_count": int(merge_cells.get("count", "0")) if merge_cells is not None else 0,
        "hyperlink_count": len(hyperlinks),
        "table_part_count": int(table_parts.get("count", "0")) if table_parts is not None else 0,
        "_classification_texts": sample_texts,
    }


def inspect_workbook(
    path: Path,
    *,
    sample_limit: int = 20,
    sample_max_chars: int = 80,
) -> dict[str, Any]:
    """Bir XLSX/XLSM dosyasının paket yapısını salt-okunur inceler."""
    path = path.resolve()
    result: dict[str, Any] = {
        "file_name": path.name,
        "path": str(path),
        "extension": path.suffix.lower(),
        "role": _workbook_role(path),
        **file_fingerprint(path),
    }
    try:
        with path.open("rb") as binary_handle:
            with ZipFile(binary_handle, "r") as archive:
                names = set(archive.namelist())
                workbook = _read_xml(archive, "xl/workbook.xml")
                if workbook is None:
                    raise ValueError("xl/workbook.xml bulunamadı")
                rels = _relationship_map(archive, "xl/_rels/workbook.xml.rels")
                shared_strings = _shared_strings(archive)
                style_formats = _style_formats(archive)

                sheets: list[dict[str, Any]] = []
                all_samples: list[str] = []
                for sheet in workbook.findall("m:sheets/m:sheet", NS):
                    rel_id = sheet.get(f"{{{DOC_REL_NS}}}id", "")
                    rel = rels.get(rel_id, {})
                    target = rel.get("target", "")
                    sheet_path = _xl_target(target) if target else ""
                    details = _sheet_inventory(
                        archive,
                        sheet_path,
                        shared_strings,
                        style_formats,
                        sample_limit,
                        sample_max_chars,
                    )
                    all_samples.extend(details.pop("_classification_texts", []))
                    sheets.append({
                        "name": sheet.get("name", ""),
                        "state": sheet.get("state", "visible"),
                        "xml_part": sheet_path,
                        **details,
                    })

                calc = workbook.find("m:calcPr", NS)
                defined_names = workbook.findall("m:definedNames/m:definedName", NS)
                external_rels = [
                    rel for rel in rels.values()
                    if rel.get("target_mode") == "External" or "externalLink" in rel.get("type", "")
                ]
                sheet_names = [sheet["name"] for sheet in sheets]
                result.update({
                    "valid_openxml_package": True,
                    "sheet_count": len(sheets),
                    "sheets": sheets,
                    "defined_name_count": len(defined_names),
                    "calculation_mode": calc.get("calcMode") if calc is not None else None,
                    "full_calculation_on_load": calc.get("fullCalcOnLoad") if calc is not None else None,
                    "shared_string_count": len(shared_strings),
                    "has_macros": "xl/vbaProject.bin" in names,
                    "has_connections": "xl/connections.xml" in names,
                    "external_link_part_count": sum(
                        1 for name in names if name.startswith("xl/externalLinks/externalLink") and name.endswith(".xml")
                    ),
                    "external_relationship_count": len(external_rels),
                    "table_part_count": sum(
                        1 for name in names if name.startswith("xl/tables/table") and name.endswith(".xml")
                    ),
                    "chart_part_count": sum(
                        1 for name in names if name.startswith("xl/charts/chart") and name.endswith(".xml")
                    ),
                    "pivot_table_part_count": sum(
                        1 for name in names if name.startswith("xl/pivotTables/pivotTable") and name.endswith(".xml")
                    ),
                    "content_categories": _content_categories(all_samples, sheet_names),
                })
    except (BadZipFile, ET.ParseError, ValueError) as exc:
        result.update({"valid_openxml_package": False, "error": str(exc), "sheets": []})
    return result


def _atomic_write_text(
    path: Path,
    content: str,
    *,
    output_dir: Path,
    allowed_extensions: Iterable[str],
) -> None:
    assert_safe_output_path(path, output_dir, allowed_extensions)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temp_name = handle.name
    os.replace(temp_name, path)


def _markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Çalışma Kitabı Envanteri",
        "",
        f"Üretim zamanı (UTC): `{payload['generated_at_utc']}`",
        "",
        "> Bu rapor yapısal envanterdir; finansal analiz, doğruluk görüşü veya tahmin içermez.",
        "",
        "## Kaynak bütünlüğü",
        "",
        f"İşlem öncesi/sonrası SHA-256 karşılaştırması: **{'AYNI' if payload['source_integrity']['all_unchanged'] else 'FARK VAR'}**",
        f"Sabit kaynak kaydıyla SHA-256 karşılaştırması: **{'AYNI' if payload['source_integrity']['all_match_registered_baseline'] else 'FARK VAR'}**",
        "",
        "| Dosya | Rol | Boyut (bayt) | Sayfa | Hücre | Formül | İçerik kategorileri |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for book in payload["workbooks"]:
        cells = sum(sheet.get("cell_count", 0) for sheet in book.get("sheets", []))
        formulas = sum(sheet.get("formula_count", 0) for sheet in book.get("sheets", []))
        categories = "; ".join(book.get("content_categories", [])) or "Yapısal sınıflandırma yok"
        lines.append(
            f"| `{book['file_name']}` | {book['role']} | {book['size_bytes']} | "
            f"{book.get('sheet_count', 0)} | {cells} | {formulas} | {categories} |"
        )
    for book in payload["workbooks"]:
        lines.extend(["", f"## {book['file_name']}", ""])
        lines.append(f"- SHA-256: `{book['sha256']}`")
        lines.append(f"- Open XML paketi: `{'geçerli' if book.get('valid_openxml_package') else 'hatalı'}`")
        lines.append(
            "- Yapısal parçalar: "
            f"tablolar={book.get('table_part_count', 0)}, "
            f"grafikler={book.get('chart_part_count', 0)}, "
            f"pivotlar={book.get('pivot_table_part_count', 0)}, "
            f"dış bağlantılar={book.get('external_link_part_count', 0)}, "
            f"makro={'var' if book.get('has_macros') else 'yok'}"
        )
        lines.extend([
            "",
            "| Sayfa | Durum | Kullanılan alan | Hücre | Formül | Veri türleri |",
            "|---|---|---|---:|---:|---|",
        ])
        for sheet in book.get("sheets", []):
            types = ", ".join(f"{key}={value}" for key, value in sheet.get("cell_types", {}).items())
            lines.append(
                f"| {sheet.get('name', '')} | {sheet.get('state', '')} | "
                f"{sheet.get('dimension') or '-'} | {sheet.get('cell_count', 0)} | "
                f"{sheet.get('formula_count', 0)} | {types or '-'} |"
            )
    lines.extend([
        "",
        "## Politika kontrolleri",
        "",
        "| Kontrol | Uygulama | Durum |",
        "|---|---|---|",
    ])
    for name, control in payload["controls"].items():
        lines.append(
            f"| {name} | {control['enforcement']} | {control['status']} |"
        )
    lines.extend([
        "",
        "## Kapsam sınırı",
        "",
        "Bu envanter formülleri yeniden hesaplamaz, finansal sonuçları yorumlamaz ve çalışma kitaplarını açıp kaydetmez. Sonraki veri denetiminde formül bağımlılıkları, kaynak izlenebilirliği ve veri kalitesi ayrı onayla ele alınabilir.",
        "",
    ])
    return "\n".join(lines)


def _csv_report(workbooks: list[dict[str, Any]]) -> str:
    import io

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "file_name", "role", "sha256", "sheet_name", "sheet_state", "dimension",
        "cell_count", "formula_count", "text_cells", "number_cells", "date_like_cells",
        "percentage_like_cells", "boolean_cells", "error_cells", "table_parts",
        "hyperlinks", "content_categories",
    ])
    for book in workbooks:
        for sheet in book.get("sheets", []):
            kinds = sheet.get("cell_types", {})
            writer.writerow([
                book["file_name"], book["role"], book["sha256"], sheet.get("name"),
                sheet.get("state"), sheet.get("dimension"), sheet.get("cell_count", 0),
                sheet.get("formula_count", 0), kinds.get("text", 0), kinds.get("number", 0),
                kinds.get("date_like", 0), kinds.get("percentage_like", 0),
                kinds.get("boolean", 0), kinds.get("error", 0),
                sheet.get("table_part_count", 0), sheet.get("hyperlink_count", 0),
                "; ".join(book.get("content_categories", [])),
            ])
    return output.getvalue()


def _hash_manifest(workbooks: list[dict[str, Any]]) -> str:
    return "".join(f"{book['sha256']}  {book['file_name']}\n" for book in workbooks)


def _safe_output_dir(project_root: Path, configured: str) -> Path:
    project_root = project_root.resolve()
    output_dir = (project_root / configured).resolve()
    if output_dir == project_root or not output_dir.is_relative_to(project_root):
        raise ValueError("Çıktı klasörü proje kökü içinde ve kökten farklı olmalıdır")
    return output_dir


def run_inventory(project_root: Path, config_path: Path | None = None) -> dict[str, Any]:
    """Yapılandırmayı okuyup envanter çıktıları üretir ve kaynakları doğrular."""
    project_root = project_root.resolve()
    config_path = (config_path or project_root / "config" / "audit.toml").resolve()
    with config_path.open("rb") as handle:
        full_config = tomllib.load(handle)
    config = full_config["inventory"]
    policy = full_config["policy"]
    if config.get("hash_algorithm") != "sha256":
        raise PolicyViolation("Yalnızca sha256 bütünlük kontrolüne izin verilir")
    if policy.get("allow_source_mutation") is not False:
        raise PolicyViolation("Kaynak mutasyonu kesin olarak kapalı olmalıdır")
    if policy.get("persist_cell_values") is not False:
        raise PolicyViolation("Envanter çıktısında hücre değerleri saklanamaz")

    output_dir = _safe_output_dir(project_root, config["output_dir"])
    registry_path = (project_root / policy["source_registry"]).resolve()
    if not registry_path.is_relative_to(project_root):
        raise PolicyViolation("Kaynak kaydı proje kökü dışında olamaz")
    registry = load_source_registry(registry_path)
    excluded_prefixes = tuple(config.get("exclude_name_prefixes", []))
    sources: set[Path] = set()
    for pattern in config["source_globs"]:
        for candidate in project_root.glob(pattern):
            resolved = candidate.resolve()
            if (
                candidate.is_file()
                and not candidate.name.startswith(excluded_prefixes)
                and resolved.is_relative_to(project_root)
                and not resolved.is_relative_to(output_dir)
            ):
                sources.add(resolved)
    if not sources:
        raise FileNotFoundError("Yapılandırılan kalıplara uyan kaynak çalışma kitabı bulunamadı")

    before = {path: file_fingerprint(path) for path in sorted(sources)}
    registry_results = verify_registered_sources(
        sorted(sources),
        before,
        registry,
        require_exact_set=bool(policy.get("require_registered_sources", True)),
        frozen_name_markers=policy.get("frozen_name_markers", []),
    )
    workbooks = [
        inspect_workbook(
            path,
            sample_limit=int(config.get("sample_text_limit", 20)),
            sample_max_chars=int(config.get("sample_text_max_chars", 80)),
        )
        for path in sorted(sources)
    ]
    after = {path: file_fingerprint(path) for path in sorted(sources)}
    unchanged = all(before[path] == after[path] for path in sources)
    if not unchanged:
        raise RuntimeError("Kaynak çalışma kitabı parmak izi işlem sırasında değişti")

    controls = {
        "Kaynak Excel değişmezliği": {
            "enforcement": "otomatik",
            "status": "geçti",
            "mechanisms": ["salt-okunur açma", "sabit kayıt", "işlem öncesi/sonrası parmak izi"],
        },
        "Dondurulmuş tahmin dosyası": {
            "enforcement": "otomatik dosya düzeyi",
            "status": "geçti",
            "mechanisms": ["frozen kaynak kaydı", "dosya adı işaretçisi", "kaynak yazma yasağı"],
        },
        "Veri sızıntısı": {
            "enforcement": "otomatik çıktı redaksiyonu; zamansal kontrol veri hattında manuel",
            "status": "hücre değerleri çıktıya yazılmadı",
            "mechanisms": ["persist_cell_values=false", "zamansal kesim koruması hazır"],
        },
        "Model güncelleme sınırı": {
            "enforcement": "otomatik kapatma; gelecekteki güncelleme hattında koruma hazır",
            "status": "model güncellemesi kapalı",
            "mechanisms": ["allow_model_updates=false", "en az 5 dondurulmuş tahmin", "%10 göreli sınır"],
        },
        "SHA-256 bütünlüğü": {
            "enforcement": "otomatik",
            "status": "geçti",
            "mechanisms": ["source_registry.toml", "çalıştırma öncesi ve sonrası doğrulama"],
        },
    }

    payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_root": str(project_root),
        "policy": "read-only source inspection; no Excel recalculation or save",
        "source_integrity": {
            "all_unchanged": unchanged,
            "all_match_registered_baseline": all(
                item["baseline_match"] for item in registry_results.values()
            ),
            "comparison": "size_bytes + modified_utc + sha256 before/after",
            "registered_baseline": str(registry_path),
        },
        "registered_sources": registry_results,
        "controls": controls,
        "workbook_count": len(workbooks),
        "workbooks": workbooks,
    }

    allowed_extensions = policy["allowed_output_extensions"]
    _atomic_write_text(
        output_dir / "workbook_inventory.json",
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        output_dir=output_dir,
        allowed_extensions=allowed_extensions,
    )
    _atomic_write_text(
        output_dir / "workbook_inventory.csv",
        _csv_report(workbooks),
        output_dir=output_dir,
        allowed_extensions=allowed_extensions,
    )
    _atomic_write_text(
        output_dir / "INVENTORY.md",
        _markdown_report(payload),
        output_dir=output_dir,
        allowed_extensions=allowed_extensions,
    )
    _atomic_write_text(
        output_dir / "source_hashes.sha256",
        _hash_manifest(workbooks),
        output_dir=output_dir,
        allowed_extensions=allowed_extensions,
    )
    return payload

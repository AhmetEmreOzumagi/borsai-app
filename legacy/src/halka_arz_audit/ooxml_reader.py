"""Excel Open XML hücrelerini formül hesaplamadan salt-okunur okur."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from zipfile import ZipFile


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN_NS, "r": DOC_REL_NS, "p": PKG_REL_NS}
CELL_REF_RE = re.compile(r"^([A-Z]+)(\d+)$")
FORMAT_LITERAL_RE = re.compile(r'"[^"]*"|\\.|\[[^\]]*\]')
BUILTIN_DATE_FORMAT_IDS = {
    14, 15, 16, 17, 18, 19, 20, 21, 22,
    27, 28, 29, 30, 31, 32, 33, 34, 35, 36,
    45, 46, 47, 50, 51, 52, 53, 54, 55, 56, 57,
}


@dataclass(frozen=True)
class CellRecord:
    coordinate: str
    row: int
    column: int
    raw_value: str | None
    value: str | None
    formula: str | None
    cell_type: str | None
    style_id: int
    number_format: str | None


@dataclass(frozen=True)
class SheetRecords:
    name: str
    state: str
    xml_part: str
    cells: dict[str, CellRecord]


def _read_xml(archive: ZipFile, member: str) -> ET.Element | None:
    try:
        with archive.open(member, "r") as handle:
            return ET.parse(handle).getroot()
    except KeyError:
        return None


def _relationship_map(archive: ZipFile, member: str) -> dict[str, str]:
    root = _read_xml(archive, member)
    if root is None:
        return {}
    return {
        item.get("Id", ""): item.get("Target", "")
        for item in root.findall("p:Relationship", NS)
        if item.get("Id")
    }


def _xl_target(target: str) -> str:
    clean = target.replace("\\", "/")
    if clean.startswith("/"):
        return clean.lstrip("/")
    return str(PurePosixPath("xl") / clean)


def _shared_strings(archive: ZipFile) -> list[str]:
    root = _read_xml(archive, "xl/sharedStrings.xml")
    if root is None:
        return []
    return [
        "".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
        for item in root.findall("m:si", NS)
    ]


def _style_number_formats(archive: ZipFile) -> dict[int, tuple[int, str | None]]:
    root = _read_xml(archive, "xl/styles.xml")
    if root is None:
        return {}
    custom: dict[int, str] = {}
    for item in root.findall("m:numFmts/m:numFmt", NS):
        try:
            custom[int(item.get("numFmtId", "-1"))] = item.get("formatCode", "")
        except ValueError:
            continue
    result: dict[int, tuple[int, str | None]] = {}
    for index, xf in enumerate(root.findall("m:cellXfs/m:xf", NS)):
        try:
            number_format_id = int(xf.get("numFmtId", "0"))
        except ValueError:
            number_format_id = 0
        result[index] = (number_format_id, custom.get(number_format_id))
    return result


def _is_date_format(number_format_id: int, format_code: str | None) -> bool:
    if number_format_id in BUILTIN_DATE_FORMAT_IDS:
        return True
    if not format_code:
        return False
    cleaned = FORMAT_LITERAL_RE.sub("", format_code.casefold())
    return bool(re.search(r"(^|[^a-z])[ymdhis]+([^a-z]|$)", cleaned))


def _column_number(letters: str) -> int:
    result = 0
    for char in letters:
        result = result * 26 + ord(char) - 64
    return result


def _cell_position(reference: str) -> tuple[int, int]:
    match = CELL_REF_RE.fullmatch(reference)
    if not match:
        raise ValueError(f"Geçersiz hücre koordinatı: {reference}")
    return int(match.group(2)), _column_number(match.group(1))


def _decode_excel_serial(raw: str, *, date_1904: bool) -> str:
    try:
        serial = float(raw)
    except ValueError:
        return raw
    base = datetime(1904, 1, 1) if date_1904 else datetime(1899, 12, 30)
    value = base + timedelta(days=serial)
    if value.time() == datetime.min.time():
        return value.date().isoformat()
    return value.isoformat(timespec="seconds")


def _read_cell(
    element: ET.Element,
    shared_strings: list[str],
    style_formats: dict[int, tuple[int, str | None]],
    *,
    date_1904: bool,
) -> CellRecord:
    coordinate = element.get("r", "")
    row, column = _cell_position(coordinate)
    cell_type = element.get("t")
    try:
        style_id = int(element.get("s", "0"))
    except ValueError:
        style_id = 0
    formula_element = element.find("m:f", NS)
    formula = formula_element.text if formula_element is not None else None
    value_element = element.find("m:v", NS)
    stored = value_element.text if value_element is not None else None
    number_format_id, number_format = style_formats.get(style_id, (0, None))

    raw_value = stored
    value: str | None = stored
    if cell_type == "inlineStr":
        raw_value = "".join(
            node.text or "" for node in element.iter(f"{{{MAIN_NS}}}t")
        )
        value = raw_value
    elif cell_type == "s" and stored is not None:
        try:
            raw_value = shared_strings[int(stored)]
            value = raw_value
        except (ValueError, IndexError):
            value = None
    elif cell_type == "b" and stored is not None:
        value = "true" if stored == "1" else "false"
    elif stored is not None and cell_type not in {"str", "e"}:
        if _is_date_format(number_format_id, number_format):
            value = _decode_excel_serial(stored, date_1904=date_1904)

    return CellRecord(
        coordinate=coordinate,
        row=row,
        column=column,
        raw_value=raw_value,
        value=value,
        formula=formula,
        cell_type=cell_type,
        style_id=style_id,
        number_format=number_format,
    )


def read_workbook_cells(
    path: Path,
    *,
    include_sheets: Iterable[str] | None = None,
) -> dict[str, SheetRecords]:
    """Çalışma kitabındaki tüm hücreleri, değer ve formülü ayırarak okur."""
    path = path.resolve()
    included = set(include_sheets) if include_sheets is not None else None
    with path.open("rb") as binary_handle:
        with ZipFile(binary_handle, "r") as archive:
            workbook = _read_xml(archive, "xl/workbook.xml")
            if workbook is None:
                raise ValueError("xl/workbook.xml bulunamadı")
            relationships = _relationship_map(archive, "xl/_rels/workbook.xml.rels")
            shared_strings = _shared_strings(archive)
            style_formats = _style_number_formats(archive)
            workbook_properties = workbook.find("m:workbookPr", NS)
            date_1904 = (
                workbook_properties is not None
                and workbook_properties.get("date1904") in {"1", "true", "True"}
            )
            result: dict[str, SheetRecords] = {}
            for sheet in workbook.findall("m:sheets/m:sheet", NS):
                name = sheet.get("name", "")
                if included is not None and name not in included:
                    continue
                relationship_id = sheet.get(f"{{{DOC_REL_NS}}}id", "")
                target = relationships.get(relationship_id, "")
                xml_part = _xl_target(target)
                root = _read_xml(archive, xml_part)
                if root is None:
                    continue
                cells: dict[str, CellRecord] = {}
                for element in root.findall(".//m:sheetData/m:row/m:c", NS):
                    record = _read_cell(
                        element,
                        shared_strings,
                        style_formats,
                        date_1904=date_1904,
                    )
                    cells[record.coordinate] = record
                result[name] = SheetRecords(
                    name=name,
                    state=sheet.get("state", "visible"),
                    xml_part=xml_part,
                    cells=cells,
                )
            return result


def row_groups(sheet: SheetRecords) -> dict[int, list[CellRecord]]:
    rows: dict[int, list[CellRecord]] = {}
    for cell in sheet.cells.values():
        if cell.raw_value not in {None, ""} or cell.formula:
            rows.setdefault(cell.row, []).append(cell)
    for cells in rows.values():
        cells.sort(key=lambda item: item.column)
    return dict(sorted(rows.items()))

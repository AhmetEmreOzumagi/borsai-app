from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile
from decimal import Decimal, localcontext
from fractions import Fraction


TASK_ID = "BORSAI_HISTORICAL99_OFFICIAL_BIST_OUTCOME_EXPANSION_01"
COHORT_NAME = "HISTORICAL99_FROZEN_COHORT_V1"
STATUS = "HISTORICAL99_OFFICIAL_OUTCOME_CANDIDATE_NOT_PROMOTED"
ROOT = Path.cwd()
CANONICAL_ROOT = (
    ROOT
    / "artifacts"
    / "ipo_master"
    / "historical99"
    / COHORT_NAME
    / "canonical"
)
ARCHIVE_ROOT = (
    ROOT
    / "BorsAi_External_Archive"
    / "BIST_OUTCOME"
    / "HISTORICAL99_V1"
)
RAW_ROOT = ARCHIVE_ROOT / "raw"
INDEX_ROOT = ARCHIVE_ROOT / "index"
EXISTING_CACHE_ROOT = ROOT / "inputs" / "ohlcv" / "bist_official"
COLLECTION_RESULT_PATH = INDEX_ROOT / "historical99_v1_collection_result.json"

INPUTS = {
    "pretrade": CANONICAL_ROOT / f"{COHORT_NAME}_canonical_pretrade_master.csv",
    "membership": CANONICAL_ROOT / f"{COHORT_NAME}_canonical_membership.csv",
    "provenance": CANONICAL_ROOT / f"{COHORT_NAME}_canonical_provenance.csv",
    "feature_readiness": CANONICAL_ROOT / f"{COHORT_NAME}_canonical_feature_readiness.csv",
    "promotion_manifest": CANONICAL_ROOT
    / f"{COHORT_NAME}_canonical_promotion_manifest.json",
}

EXPECTED_INPUT_HASHES = {
    "pretrade": "573f4c77c5ac9f9d3aaf7715a5b054ff412991120c73f2c03065521c7fc9173b",
    "membership": "b15c2e2c9e1a6ad9f702a469e6ba7c03eeef4828fd29afb59dbe780d8a2a1801",
    "provenance": "c54aee2c392a0113e6ad66df28baa441f336fabab5b65b9a127a49197f5e3123",
    "feature_readiness": "630044a5d576113c8668b41b91acd0ad1e3d1d195660463d1e57932e203b7623",
    "promotion_manifest": "86559c296109eeec3b0a165ad3796996c4c4f24a0c64c828a87cf3e397566700",
}

FULL20_PATH = (
    ROOT
    / "artifacts"
    / "ohlcv"
    / "full20"
    / "snapshots"
    / "20260814_231842"
    / "first10_ohlcv_20_snapshot.csv"
)
EXPECTED_FULL20_HASH = "54781b2d9e225372227c2f75f3a2e405c2ae2f7a7794f1f12f933ed72cd2a5da"

CALENDAR_EVIDENCE = {
    "2023": {
        "url": "https://borsaistanbul.com/files/2023_tatil-duyurusu.pdf",
        "path": RAW_ROOT / "calendar" / "bist_pay_holidays_2023_RAW.pdf",
        "acquisition_status": "DOWNLOADED_BY_TASK",
    },
    "2024": {
        "url": "https://borsaistanbul.com/files/duyuru-22379.pdf",
        "path": RAW_ROOT / "calendar" / "bist_pay_holidays_2024_RAW.pdf",
        "acquisition_status": "DOWNLOADED_BY_TASK",
    },
    "2025": {
        "url": "https://www.borsaistanbul.com/files/Duyuru-31449.pdf",
        "path": RAW_ROOT / "calendar" / "bist_pay_holidays_2025_RAW.pdf",
        "acquisition_status": "DOWNLOADED_BY_TASK",
    },
    "2026": {
        "url": "https://www.borsaistanbul.com/tr/sayfa/143/resmi-tatil-gunleri",
        "path": EXISTING_CACHE_ROOT
        / "reference"
        / "pay-piyasasi-2026-yili-tatil-tablosu_RAW.pdf",
        "acquisition_status": "REUSED_EXISTING_REPO_CACHE",
        "expected_sha256": "e45fa97e2f67d85b3571ce9e6c4758292a57379c2216fc88183f32504584e680",
    },
}

# Frozen from the official Borsa Istanbul Pay Market annual holiday tables.
# Weekend dates are retained in this evidence set but are independently excluded as weekends.
OFFICIAL_FULL_CLOSURES = {
    "2023-01-01",
    "2023-04-21",
    "2023-04-22",
    "2023-04-23",
    "2023-05-01",
    "2023-05-19",
    "2023-06-28",
    "2023-06-29",
    "2023-06-30",
    "2023-07-01",
    "2023-07-15",
    "2023-08-30",
    "2023-10-28",
    "2023-10-29",
    "2024-01-01",
    "2024-04-10",
    "2024-04-11",
    "2024-04-12",
    "2024-04-23",
    "2024-05-01",
    "2024-05-19",
    "2024-06-17",
    "2024-06-18",
    "2024-06-19",
    "2024-07-15",
    "2024-08-30",
    "2024-10-29",
    "2025-01-01",
    "2025-03-29",
    "2025-03-30",
    "2025-03-31",
    "2025-04-01",
    "2025-04-23",
    "2025-05-01",
    "2025-05-19",
    "2025-06-06",
    "2025-06-07",
    "2025-06-08",
    "2025-06-09",
    "2025-07-15",
    "2025-08-30",
    "2025-10-29",
    "2026-01-01",
    "2026-03-20",
    "2026-03-21",
    "2026-03-22",
    "2026-04-23",
    "2026-05-01",
    "2026-05-19",
    "2026-05-27",
    "2026-05-28",
    "2026-05-29",
    "2026-05-30",
    "2026-07-15",
    "2026-10-29",
}

OFFICIAL_HALF_DAYS = {
    "2023-04-20",
    "2023-06-27",
    "2024-04-09",
    "2024-10-28",
    "2025-06-05",
    "2025-10-28",
    "2026-03-19",
    "2026-05-26",
    "2026-10-28",
}

THB_COLUMNS = {
    "security_trading_status": "GECICI DURDURMA",
    "open": "ACILIS FIYATI",
    "high": "EN YUKSEK FIYAT",
    "low": "EN DUSUK FIYAT",
    "close": "KAPANIS FIYATI",
    "volume": "TOPLAM ISLEM ADEDI",
    "turnover": "TOPLAM ISLEM HACMI",
    "aof": "A.O.F",
    "trade_count": "TOPLAM SOZLESME SAYISI",
}
THM_COLUMNS = {
    "reference_price": "REFERANS FIYATI",
    "upper_limit": "UST LIMIT FIYATI",
    "lower_limit": "ALT LIMIT FIYATI",
}
KEY_COLUMNS = {"ticker": "ISLEM  KODU", "date": "TARIH"}

PROTECTED_PATHS = [
    *INPUTS.values(),
    ROOT
    / "artifacts"
    / "ipo_master"
    / "historical99"
    / COHORT_NAME
    / f"{COHORT_NAME}_membership.csv",
    ROOT
    / "artifacts"
    / "ipo_master"
    / "historical99"
    / COHORT_NAME
    / f"{COHORT_NAME}_pretrade_canonical_candidate.csv",
    ROOT
    / "artifacts"
    / "ipo_master"
    / "historical99"
    / COHORT_NAME
    / f"{COHORT_NAME}_provenance_candidate.csv",
    ROOT
    / "artifacts"
    / "ipo_master"
    / "historical99"
    / COHORT_NAME
    / f"{COHORT_NAME}_feature_readiness_candidate.csv",
    ROOT
    / "artifacts"
    / "ipo_master"
    / "historical99"
    / COHORT_NAME
    / f"{COHORT_NAME}_manifest.json",
    ROOT
    / "artifacts"
    / "ipo_master"
    / "consolidated"
    / "ipo_master_20_pretrade_canonical.csv",
    ROOT
    / "artifacts"
    / "ipo_master"
    / "consolidated"
    / "ipo_master_20_provenance_canonical.csv",
    ROOT
    / "artifacts"
    / "ipo_master"
    / "consolidated"
    / "pretrade_feature_availability_20.csv",
    FULL20_PATH,
    ROOT / "artifacts" / "predictions" / "frozen_predictions_2026-08-06_1335.csv",
    ROOT / "artifacts" / "modeling" / "V1_5_PREREGISTRATION.md",
    ROOT / "config" / "model_v1_5_spec.json",
    ROOT / "artifacts" / "live_forecast" / "live_forecast_registry.csv",
    ROOT / "src" / "halka_arz_audit" / "true_live_freeze.py",
    ROOT
    / "artifacts"
    / "live_forecast"
    / "TRUE_LIVE_V1_5_GOVERNANCE_CORRECTION_01.md",
    ROOT / "artifacts" / "universe" / "ipo_universe_last20_2026-08-07.csv",
    ROOT
    / "BorsAi_External_Archive"
    / "PRETRADE_ACQUISITION_LEDGER_EXACT100_EVIDENCE_FINAL_20260821.txt",
    ROOT
    / "BorsAi_External_Archive"
    / "PRETRADE_ACQUISITION_LEDGER_ADDENDUM_05_20260821.txt",
    ROOT
    / "BorsAi_External_Archive"
    / "SPECS"
    / "TKNKA_TRUE_LIVE_V1_5_FREEZE_20260819.md",
]


def sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(file_path: Path) -> str:
    try:
        return file_path.relative_to(ROOT).as_posix()
    except ValueError:
        return file_path.as_posix()


def hash_protected() -> dict[str, str]:
    result: dict[str, str] = {}
    for file_path in PROTECTED_PATHS:
        if not file_path.is_file():
            raise RuntimeError(f"Protected file missing: {rel(file_path)}")
        result[rel(file_path)] = sha256_file(file_path)
    return result


def verify_input_hashes() -> None:
    for key, file_path in INPUTS.items():
        actual = sha256_file(file_path)
        if actual != EXPECTED_INPUT_HASHES[key]:
            raise RuntimeError("HISTORICAL99_OUTCOME_INPUT_HASH_MISMATCH")
    if sha256_file(FULL20_PATH) != EXPECTED_FULL20_HASH:
        raise RuntimeError("HISTORICAL99_OUTCOME_INPUT_HASH_MISMATCH")


def read_csv(file_path: Path) -> list[dict[str, str]]:
    with file_path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def date_range(start: str, end: str):
    from datetime import date, timedelta

    cursor = date.fromisoformat(start)
    final = date.fromisoformat(end)
    while cursor <= final:
        yield cursor
        cursor += timedelta(days=1)


def generate_session_dates(first_trading_date: str) -> list[str]:
    sessions: list[str] = []
    cursor = next(date_range(first_trading_date, first_trading_date))
    from datetime import timedelta

    while len(sessions) < 10:
        text = cursor.isoformat()
        if cursor.weekday() < 5 and text not in OFFICIAL_FULL_CLOSURES:
            sessions.append(text)
        cursor += timedelta(days=1)
    return sessions


def archive_names(market_date: str, kind: str) -> tuple[str, str]:
    compact = market_date.replace("-", "")
    return f"{kind}{compact}1_RAW.zip", f"{kind}{compact}1.csv"


def source_url(market_date: str, kind: str) -> str:
    compact = market_date.replace("-", "")
    return (
        f"https://www.borsaistanbul.com/data/{kind}/"
        f"{market_date[:4]}/{market_date[5:7]}/{kind}{compact}1.zip"
    )


def download_bytes(url: str, attempts: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "BorsAi-Historical99-Official-BIST/1.0"},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP_STATUS_{response.status}")
                data = response.read()
                if len(data) <= 100:
                    raise RuntimeError(f"OFFICIAL_RESPONSE_TOO_SHORT_{len(data)}")
                return data
        except Exception as error:  # bounded retry; exact error is returned after exhaustion
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    assert last_error is not None
    raise last_error


def write_new_bytes(file_path: Path, data: bytes) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp = file_path.with_name(f"{file_path.name}.download-{os.getpid()}")
    with temp.open("xb") as stream:
        stream.write(data)
    try:
        temp.rename(file_path)
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def collect_calendar_evidence() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for year, item in CALENDAR_EVIDENCE.items():
        file_path = Path(item["path"])
        if not file_path.is_file():
            if item["acquisition_status"] != "DOWNLOADED_BY_TASK":
                raise RuntimeError(f"Required calendar evidence missing: {file_path}")
            data = download_bytes(str(item["url"]))
            if not data.startswith(b"%PDF"):
                raise RuntimeError(f"Official calendar response is not a PDF: {item['url']}")
            write_new_bytes(file_path, data)
        data_prefix = file_path.read_bytes()[:4]
        if data_prefix != b"%PDF":
            raise RuntimeError(f"Calendar evidence is not a PDF: {file_path}")
        actual_hash = sha256_file(file_path)
        expected = item.get("expected_sha256")
        if expected and actual_hash != expected:
            raise RuntimeError(f"Official calendar hash mismatch: {year}")
        rows.append(
            {
                "source_kind": "BIST_PAY_MARKET_HOLIDAY_TABLE",
                "market_date": f"{year}-YEAR",
                "official_url": item["url"],
                "local_path": rel(file_path),
                "sha256": actual_hash,
                "file_size": file_path.stat().st_size,
                "internal_filename": "NOT_APPLICABLE",
                "schema_width": "NOT_APPLICABLE",
                "acquisition_status": item["acquisition_status"],
                "parse_status": "PDF_VISUAL_AND_TEXT_VERIFICATION_REQUIRED",
                "failure_detail": "",
            }
        )
    return rows


def parse_archive_bytes(data: bytes, expected_internal: str) -> dict[str, object]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if names != [expected_internal]:
            raise RuntimeError(
                f"ZIP internal filename mismatch: expected {expected_internal}, found {names}"
            )
        text = archive.read(expected_internal).decode("cp1254")
    reader = csv.reader(io.StringIO(text.lstrip("\ufeff")), delimiter=";")
    records = [row for row in reader if any(cell != "" for cell in row)]
    if len(records) <= 2:
        raise RuntimeError("Official archive CSV has no data rows")
    headers = records[0]
    english_headers = records[1]
    if len(headers) != len(english_headers):
        raise RuntimeError("Official archive dual-header width mismatch")
    data_rows = records[2:]
    if any(len(row) != len(headers) for row in data_rows):
        raise RuntimeError("Official archive data-row width mismatch")
    return {
        "headers": headers,
        "english_headers": english_headers,
        "rows": data_rows,
        "schema_width": len(headers),
    }


def validate_required_schema(parsed: dict[str, object], kind: str) -> None:
    headers = set(parsed["headers"])
    required = set(KEY_COLUMNS.values())
    required.update(THB_COLUMNS.values() if kind == "thb" else THM_COLUMNS.values())
    missing = sorted(required - headers)
    if missing:
        raise RuntimeError(f"{kind.upper()} required name-based columns missing: {missing}")


def collect_one_source(market_date: str, kind: str) -> dict[str, object]:
    archive_name, internal_name = archive_names(market_date, kind)
    url = source_url(market_date, kind)
    cached_path = EXISTING_CACHE_ROOT / market_date / archive_name
    outcome_path = RAW_ROOT / market_date / archive_name
    try:
        if cached_path.is_file():
            local_path = cached_path
            acquisition_status = "REUSED_EXISTING_REPO_CACHE"
            data = local_path.read_bytes()
        elif outcome_path.is_file():
            local_path = outcome_path
            acquisition_status = "DOWNLOADED_BY_TASK"
            data = local_path.read_bytes()
        else:
            local_path = outcome_path
            acquisition_status = "DOWNLOADED_BY_TASK"
            data = download_bytes(url)
            parse_archive_bytes(data, internal_name)
            write_new_bytes(local_path, data)
        parsed = parse_archive_bytes(data, internal_name)
        validate_required_schema(parsed, kind)
        return {
            "source_kind": kind.upper(),
            "market_date": market_date,
            "official_url": url,
            "local_path": rel(local_path),
            "sha256": hashlib.sha256(data).hexdigest(),
            "file_size": len(data),
            "internal_filename": internal_name,
            "schema_width": parsed["schema_width"],
            "acquisition_status": acquisition_status,
            "parse_status": "PARSED_NAME_BASED",
            "failure_detail": "",
            "parsed": parsed,
        }
    except urllib.error.HTTPError as error:
        return {
            "source_kind": kind.upper(),
            "market_date": market_date,
            "official_url": url,
            "local_path": rel(outcome_path),
            "sha256": "",
            "file_size": 0,
            "internal_filename": internal_name,
            "schema_width": "",
            "acquisition_status": "DOWNLOAD_FAILED",
            "parse_status": "SOURCE_FILE_NOT_AVAILABLE",
            "failure_detail": f"HTTP_{error.code}",
            "parsed": None,
        }
    except Exception as error:
        return {
            "source_kind": kind.upper(),
            "market_date": market_date,
            "official_url": url,
            "local_path": rel(outcome_path),
            "sha256": "",
            "file_size": 0,
            "internal_filename": internal_name,
            "schema_width": "",
            "acquisition_status": "DOWNLOAD_OR_PARSE_FAILED",
            "parse_status": "PARSE_ERROR",
            "failure_detail": f"{type(error).__name__}: {error}",
            "parsed": None,
        }


def exact_matches(
    parsed: dict[str, object] | None, market_date: str, ticker: str
) -> list[dict[str, str]]:
    if parsed is None:
        return []
    headers: list[str] = parsed["headers"]  # type: ignore[assignment]
    ticker_index = headers.index(KEY_COLUMNS["ticker"])
    date_index = headers.index(KEY_COLUMNS["date"])
    exact_code = f"{ticker}.E"
    rows = [
        row
        for row in parsed["rows"]  # type: ignore[index]
        if row[ticker_index] == exact_code
    ]
    for row in rows:
        if row[date_index] != market_date:
            raise RuntimeError(
                f"Official source date mismatch for exact ticker {ticker}: {market_date}"
            )
    return [dict(zip(headers, row, strict=True)) for row in rows]


def canonical_decimal(raw: str) -> str | None:
    text = str(raw).strip()
    if text == "":
        return None
    try:
        value = Decimal(text)
    except Exception:
        return None
    if not value.is_finite():
        return None
    output = format(value, "f")
    if "." in output:
        output = output.rstrip("0").rstrip(".")
    return "0" if output in {"", "-0"} else output


def exact_return(close: str, ipo_price: str) -> tuple[str, str, str, str]:
    close_fraction = Fraction(Decimal(close))
    ipo_fraction = Fraction(Decimal(ipo_price))
    if ipo_fraction <= 0:
        raise RuntimeError("IPO price must be positive")
    result = close_fraction / ipo_fraction - 1
    if result == 0:
        decimal_text = "0"
    else:
        with localcontext() as context:
            context.prec = 50
            decimal_text = format(
                Decimal(result.numerator) / Decimal(result.denominator), "f"
            ).rstrip("0").rstrip(".")
    above_flag = "1" if result > 0 else "0"
    return decimal_text, str(result.numerator), str(result.denominator), above_flag


def build_session_record(
    expected: dict[str, object],
    thb_source: dict[str, object],
    thm_source: dict[str, object],
) -> dict[str, object]:
    base = dict(expected)
    base.update(
        {
            "security_trading_status": "",
            "thb_raw_open": "",
            "thb_raw_high": "",
            "thb_raw_low": "",
            "thb_raw_close": "",
            "thb_raw_volume": "",
            "thb_raw_turnover": "",
            "thb_raw_aof": "",
            "thb_raw_trade_count": "",
            "thm_raw_reference_price": "",
            "thm_raw_upper_limit": "",
            "thm_raw_lower_limit": "",
            "open": "",
            "high": "",
            "low": "",
            "close": "",
            "volume": "",
            "turnover": "",
            "aof": "",
            "trade_count": "",
            "reference_price": "",
            "upper_limit": "",
            "lower_limit": "",
            "row_status": "",
            "target_availability_status": "",
            "conflict_status": "NO_CONFLICT",
            "thb_source_url": thb_source["official_url"],
            "thb_local_path": thb_source["local_path"],
            "thb_sha256": thb_source["sha256"],
            "thb_internal_filename": thb_source["internal_filename"],
            "thm_source_url": thm_source["official_url"],
            "thm_local_path": thm_source["local_path"],
            "thm_sha256": thm_source["sha256"],
            "thm_internal_filename": thm_source["internal_filename"],
        }
    )
    if thb_source["parse_status"] == "SOURCE_FILE_NOT_AVAILABLE" or thm_source[
        "parse_status"
    ] == "SOURCE_FILE_NOT_AVAILABLE":
        base["row_status"] = "SOURCE_FILE_NOT_AVAILABLE"
        base["target_availability_status"] = "SOURCE_FILE_NOT_AVAILABLE"
        return base
    if thb_source["parse_status"] != "PARSED_NAME_BASED" or thm_source[
        "parse_status"
    ] != "PARSED_NAME_BASED":
        base["row_status"] = "PARSE_ERROR"
        base["target_availability_status"] = "PARSE_ERROR"
        return base
    ticker = str(expected["ticker"])
    market_date = str(expected["target_session_date"])
    thb_matches = exact_matches(thb_source["parsed"], market_date, ticker)
    thm_matches = exact_matches(thm_source["parsed"], market_date, ticker)
    if len(thb_matches) > 1 or len(thm_matches) > 1:
        base["row_status"] = "SOURCE_CONFLICT"
        base["target_availability_status"] = "SOURCE_CONFLICT"
        base["conflict_status"] = "SOURCE_CONFLICT"
        return base
    if len(thb_matches) == 0 or len(thm_matches) == 0:
        base["row_status"] = "SECURITY_ROW_NOT_FOUND"
        base["target_availability_status"] = "TARGET_NOT_AVAILABLE"
        return base
    thb = thb_matches[0]
    thm = thm_matches[0]
    for output_name, source_name in THB_COLUMNS.items():
        raw_name = f"thb_raw_{output_name}"
        raw_value = thb[source_name]
        base[raw_name] = raw_value
        if output_name == "security_trading_status":
            base["security_trading_status"] = (
                "ACTIVE_NOT_SUSPENDED"
                if raw_value == "0"
                else "SUSPENDED"
                if raw_value == "1"
                else f"UNKNOWN_OFFICIAL_CODE:{raw_value}"
            )
        else:
            base[output_name] = canonical_decimal(raw_value) or ""
    for output_name, source_name in THM_COLUMNS.items():
        raw_name = f"thm_raw_{output_name}"
        raw_value = thm[source_name]
        base[raw_name] = raw_value
        base[output_name] = canonical_decimal(raw_value) or ""
    close = str(base["close"])
    if close == "" or Decimal(close) <= 0:
        base["row_status"] = "TARGET_NOT_AVAILABLE"
        base["target_availability_status"] = "TARGET_NOT_AVAILABLE"
        return base
    numeric_fields = ["open", "high", "low", "volume", "turnover", "aof", "trade_count"]
    if any(str(base[field]) == "" for field in numeric_fields):
        base["row_status"] = "PARSE_ERROR"
        base["target_availability_status"] = "PARSE_ERROR"
        return base
    low = Decimal(str(base["low"]))
    high = Decimal(str(base["high"]))
    opening = Decimal(str(base["open"]))
    closing = Decimal(close)
    if not (low <= opening <= high and low <= closing <= high):
        base["row_status"] = "SOURCE_CONFLICT"
        base["target_availability_status"] = "SOURCE_CONFLICT"
        base["conflict_status"] = "SOURCE_CONFLICT"
        return base
    base["row_status"] = "OFFICIAL_VERIFIED"
    base["target_availability_status"] = "OFFICIAL_VERIFIED"
    return base


def stable_write_json(file_path: Path, value: object) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    encoded = text.encode("utf-8")
    if file_path.is_file():
        if file_path.read_bytes() != encoded:
            raise RuntimeError(
                f"Versioned collection result exists with different bytes: {file_path}"
            )
        return "UNCHANGED_IDENTICAL"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp = file_path.with_name(f"{file_path.name}.tmp-{os.getpid()}")
    with temp.open("xb") as stream:
        stream.write(encoded)
    temp.rename(file_path)
    return "CREATED"


def main() -> None:
    verify_input_hashes()
    protected_before = hash_protected()
    pretrade_rows = read_csv(INPUTS["pretrade"])
    membership_rows = read_csv(INPUTS["membership"])
    if len(pretrade_rows) != 99 or len(membership_rows) != 99:
        raise RuntimeError("Canonical Historical99 membership count mismatch")
    if [row["ticker"] for row in pretrade_rows] != [row["ticker"] for row in membership_rows]:
        raise RuntimeError("Canonical membership/pretrade order mismatch")

    calendar_evidence = collect_calendar_evidence()
    evidence_by_year = {row["market_date"][:4]: row for row in calendar_evidence}
    session_grid: list[dict[str, object]] = []
    for company in pretrade_rows:
        for index, market_date in enumerate(generate_session_dates(company["first_trading_date"]), 1):
            session_grid.append(
                {
                    "ticker": company["ticker"],
                    "first_trading_date": company["first_trading_date"],
                    "session_number": index,
                    "target_session_date": market_date,
                    "session_type": "OPEN_HALF_DAY" if market_date in OFFICIAL_HALF_DAYS else "OPEN_FULL_DAY",
                    "calendar_source_url": evidence_by_year[market_date[:4]]["official_url"],
                    "calendar_source_sha256": evidence_by_year[market_date[:4]]["sha256"],
                    "calendar_status": "OFFICIAL_SESSION_RESOLVED",
                }
            )
    if len(session_grid) != 990:
        raise RuntimeError(f"Expected 990 sessions, found {len(session_grid)}")
    keys = {(row["ticker"], row["session_number"]) for row in session_grid}
    if len(keys) != 990:
        raise RuntimeError("Duplicate ticker+session key")

    unique_dates = sorted({str(row["target_session_date"]) for row in session_grid})
    source_pairs = [(market_date, kind) for market_date in unique_dates for kind in ("thb", "thm")]
    collected: list[dict[str, object]] = []
    print(
        f"COLLECTION_START unique_dates={len(unique_dates)} source_files={len(source_pairs)}",
        flush=True,
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {
            executor.submit(collect_one_source, market_date, kind): (market_date, kind)
            for market_date, kind in source_pairs
        }
        for completed, future in enumerate(concurrent.futures.as_completed(future_map), 1):
            collected.append(future.result())
            if completed % 25 == 0 or completed == len(source_pairs):
                print(f"COLLECTION_PROGRESS {completed}/{len(source_pairs)}", flush=True)
    collected.sort(key=lambda row: (str(row["market_date"]), str(row["source_kind"])))
    source_by_key = {
        (str(row["market_date"]), str(row["source_kind"]).lower()): row
        for row in collected
    }
    session_records = [
        build_session_record(
            row,
            source_by_key[(str(row["target_session_date"]), "thb")],
            source_by_key[(str(row["target_session_date"]), "thm")],
        )
        for row in session_grid
    ]
    pretrade_by_ticker = {row["ticker"]: row for row in pretrade_rows}
    target_records: list[dict[str, object]] = []
    for row in session_records:
        if row["session_number"] not in {1, 3, 5, 10}:
            continue
        source_status = str(row["row_status"])
        target_status = (
            "OFFICIAL_VERIFIED"
            if row["target_availability_status"] == "OFFICIAL_VERIFIED"
            else "TARGET_NOT_AVAILABLE"
            if source_status in {"SECURITY_ROW_NOT_FOUND", "TARGET_NOT_AVAILABLE"}
            else source_status
        )
        ipo_price = pretrade_by_ticker[str(row["ticker"])]["ipo_price"]
        target_return = numerator = denominator = above_flag = ""
        if target_status == "OFFICIAL_VERIFIED":
            target_return, numerator, denominator, above_flag = exact_return(
                str(row["close"]), ipo_price
            )
        target_records.append(
            {
                "ticker": row["ticker"],
                "horizon": f"D{row['session_number']}",
                "session_number": row["session_number"],
                "target_session_date": row["target_session_date"],
                "ipo_price": ipo_price,
                "official_close": row["close"] if target_status == "OFFICIAL_VERIFIED" else "",
                "target_return": target_return,
                "target_return_exact_numerator": numerator,
                "target_return_exact_denominator": denominator,
                "above_ipo_flag": above_flag,
                "row_status": target_status,
                "source_session_status": source_status,
                "conflict_status": row["conflict_status"],
                "thb_source_url": row["thb_source_url"],
                "thb_local_path": row["thb_local_path"],
                "thb_sha256": row["thb_sha256"],
                "thb_internal_filename": row["thb_internal_filename"],
            }
        )
    if len(target_records) != 396:
        raise RuntimeError(f"Expected 396 targets, found {len(target_records)}")

    public_sources = [
        {key: value for key, value in row.items() if key != "parsed"} for row in collected
    ]
    all_source_rows = sorted(
        [*calendar_evidence, *public_sources],
        key=lambda row: (str(row["market_date"]), str(row["source_kind"])),
    )
    protected_after_collection = hash_protected()
    if protected_before != protected_after_collection:
        raise RuntimeError("Protected input changed during official BIST collection")
    result = {
        "task_id": TASK_ID,
        "cohort_name": COHORT_NAME,
        "status": STATUS,
        "input_hashes": EXPECTED_INPUT_HASHES,
        "full20_hash": EXPECTED_FULL20_HASH,
        "session_semantics_version": "BIST_PAY_NTH_OFFICIAL_OPEN_SESSION_V1",
        "official_full_closures": sorted(OFFICIAL_FULL_CLOSURES),
        "official_half_days": sorted(OFFICIAL_HALF_DAYS),
        "calendar_evidence": calendar_evidence,
        "session_grid": session_grid,
        "session_records": session_records,
        "target_records": target_records,
        "source_inventory": all_source_rows,
        "unique_market_dates": unique_dates,
        "protected_hashes_before": protected_before,
        "protected_hashes_after_collection": protected_after_collection,
        "decimal_return_contract": "EXACT_RATIONAL_FROM_DECIMAL_INPUTS_WITH_50_DIGIT_DECIMAL_RENDERING",
        "pretrade_modified": False,
    }
    write_result = stable_write_json(COLLECTION_RESULT_PATH, result)
    session_counts = {
        status: sum(1 for row in session_records if row["row_status"] == status)
        for status in [
            "OFFICIAL_VERIFIED",
            "TARGET_NOT_AVAILABLE",
            "SOURCE_FILE_NOT_AVAILABLE",
            "SECURITY_ROW_NOT_FOUND",
            "SOURCE_CONFLICT",
            "PARSE_ERROR",
        ]
    }
    print(
        json.dumps(
            {
                "task_id": TASK_ID,
                "unique_market_dates": len(unique_dates),
                "source_files": len(collected),
                "downloaded": sum(
                    1 for row in collected if row["acquisition_status"] == "DOWNLOADED_BY_TASK"
                ),
                "reused": sum(
                    1
                    for row in collected
                    if row["acquisition_status"] == "REUSED_EXISTING_REPO_CACHE"
                ),
                "failed": sum(
                    1 for row in collected if row["parse_status"] != "PARSED_NAME_BASED"
                ),
                "session_counts": session_counts,
                "collection_result": rel(COLLECTION_RESULT_PATH),
                "collection_result_write": write_result,
            },
            indent=2,
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"COLLECTION_FATAL {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        raise

"""BORSAI_BATCH_VALIDATOR_20260906_T2 — pretrade-extension batch self-consistency validator.

Checks an offer-level CSV and a demand-category CSV against
PRETRADE_EXTENSION_COLLECTION_SPEC.json for schema, enum, sentinel,
provenance and format discipline ONLY. This script never compares a
batch against canonical/answer-key data and never reads any outcome
file. See scripts/validation/README.md for the full rule list and the
REZERV interpretation decisions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

# --- literal rule tokens dictated directly by the task text (not spec-JSON enums) ---

ALLOWED_SENTINELS = ("DATA_NOT_FOUND", "SOURCES_CONFLICT", "NOT_APPLICABLE")

# Absence-encoding tokens the spec's own conflict_rules.forbidden_absence_encodings
# names as forbidden. "0" is intentionally excluded here: the spec states
# explicit_source_zero_is_a_real_zero = true, and a validator with no semantic
# knowledge of the field cannot tell a real reported zero from a lazy zero.
_FALLBACK_FORBIDDEN_TOKENS = ["N/A", "NA", "-", "yok", "bilinmiyor", "null", "None", "—", "–"]

GENERIC_SEARCH_SCOPE_TOKENS = {
    "aranmadı", "aranmadi",
    "yok", "yoktur",
    "bilinmiyor",
    "bulunamadı", "bulunamadi",
    "none", "n/a", "na", "null",
}

# a search_scope made of nothing but punctuation/symbols (e.g. "-", "--", "...", "?")
# is exactly as uninformative as the generic words above.
PUNCTUATION_ONLY_RE = re.compile(r"^[\W_]+$", re.UNICODE)

# field_dictionary "type" values that check_numeric_decimal_separator treats as numeric.
NUMERIC_FIELD_TYPES = ("decimal", "integer")

# column name -> key in spec_json["enums_reused_verbatim"], for the cases where
# the column name and the JSON key are not spelled identically.
COLUMN_TO_ENUM_KEY = {
    "unit": "unit",
    "scope_tag": "scope_tag",
    "source_document_type": "source_document_type",
    "source_priority": "source_priority",
    "field_status": "field_status",
    "normalized_category": "normalized_categories",
    "category_level": "category_levels",
}

BOOLEAN_ENUM_KEY = "allowed_boolean_values"

# --- Section 8 checks 11 and 12 (BORSAI_R2_CONSISTENCY_CHECKS_20260906_T9C) ---

# Check 11's additive demand-category fields: every one of the 15 data fields
# EXCEPT demand_multiple, which section 2.2 explicitly forbids deriving from a
# sum ("demand_multiple is filled only where the source states a category
# multiple. It is never derived from demand_nominal / planned_allocation_shares").
# Every other field is defined by the schema as a count or a share of a common
# total (ipo_demand_category_schema.md: "Toplam talepteki pay" etc.), so leaf
# rows under one aggregate can be summed and compared to that aggregate's own
# cell for the SAME field. normalized_category/source_category_label/etc. are
# identity columns, not summable data, and are excluded structurally.
AGGREGATE_LEAF_ADDITIVE_FIELDS = (
    "applicant_count", "allocated_investor_count", "order_count",
    "planned_allocation_shares", "planned_allocation_pct",
    "demand_nominal", "demand_share_pct",
    "distributed_nominal", "distributed_pct",
)

# Check 12 field names, taken verbatim from section 2.1 items 1-4.
DEMAND_SHARES_FIELDS = ("demand_shares_unfiltered", "demand_shares_filtered")
SHARES_OFFERED_DENOMINATOR_FIELD = "shares_offered_denominator"
TOTAL_DEMAND_MULTIPLE_FIELD = "total_demand_multiple_value"

# Rounding convention for both checks' "source's stated precision" comparison.
# Section 8 does not name a rounding mode; ROUND_HALF_UP is the ordinary
# convention for a printed financial ratio and is declared once, here, per
# README.md's REZERV note.
ARITHMETIC_ROUNDING = ROUND_HALF_UP

# --- Section 8 check 11, R4 text (BORSAI_R4_IMPLEMENTATION_20260909_V1) ---
# R4 splits check 11 into Branch A (additive, unchanged in every respect from
# R2/R3) and Branch B (percentage, new - per-cell base reconstruction, never a
# family sum of printed leaves). AGGREGATE_LEAF_ADDITIVE_FIELDS above is left
# exactly as written and stays reachable via --check11-revision r2r3, which
# reruns the R2/R3 definition exactly as it was actually in force when
# B00_codex_r2...B04 were accepted (mirrors --check12-revision r2/r3's
# already-established pattern for the same reason).
AGGREGATE_LEAF_ADDITIVE_FIELDS_R4 = (
    "applicant_count", "allocated_investor_count", "order_count",
    "planned_allocation_shares", "demand_nominal", "distributed_nominal",
)

# Branch B pairing - each percentage field with its nominal partner in the
# SAME row (section 2.2 / R4 section 8 check 11(a); not invented here).
PERCENTAGE_FIELD_TO_NOMINAL = {
    "planned_allocation_pct": "planned_allocation_shares",
    "demand_share_pct": "demand_nominal",
    "distributed_pct": "distributed_nominal",
}
PERCENTAGE_FIELDS = tuple(PERCENTAGE_FIELD_TO_NOMINAL)

# --- Section 8 check 8, R4 text in full (BORSAI_R4_IMPLEMENTATION_20260909_V1) ---
# Never implemented before this task: R2/R3 stated four uniqueness keys but no
# function in this file enforced any of them (grep for DUPLICATE_ROW_KEY prior
# to this revision finds nothing). R4 replaces R2/R3's check 8 in full: three
# keys stay unchanged FAIL gates, the fourth (the duration key, section 2.1
# #15/#16/#17) becomes report-only because section 2.1.1 item 2 of this same
# specification requires exactly the row pairs that key would reject - see
# CHANGELOG_R3_TO_R4.md section 2 for the full defect and measurement.
OFFER_NON_DURATION_DUPLICATE_KEY_COLUMNS = ("ticker", "field_name", "scope_tag", "source_url")
OFFER_DURATION_DUPLICATE_KEY_COLUMNS = (
    "ticker", "field_name", "scope_tag", "duration_start_reference",
    "undertaking_scope", "source_url",
)
CATEGORY_DUPLICATE_KEY_COLUMNS = (
    "ticker", "normalized_category", "source_category_label", "source_url",
)
REGISTER_DUPLICATE_KEY_COLUMNS = (
    "ticker", "normalized_category", "source_category_label", "field_name",
)

# --- Section 8 check 12, R3 text (BORSAI_CHECK12_R3_IMPLEMENTATION_20260908_V1) ---
# §2.1 item 5, read verbatim from the frozen enum of §1.6 - not extended here.
TOTAL_DEMAND_FILTER_STATUS_FIELD = "total_demand_filter_status"
FILTER_STATUS_UNFILTERED = "UNFILTERED"
FILTER_STATUS_FILTERED = "FILTERED"
FILTER_STATUS_NOT_SPECIFIED = "NOT_SPECIFIED"
FILTER_STATUS_DATA_NOT_FOUND = "DATA_NOT_FOUND"
FILTER_STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"

# Step B's designation table (R3 §8 check 12): the one numerator #5 says the
# source itself divided by. NOT_SPECIFIED/DATA_NOT_FOUND (undetermined) and
# NOT_APPLICABLE (no numerator at all, Step E) are deliberately absent here -
# they are not a designation, they are routed to different steps entirely.
FILTER_STATUS_TO_DESIGNATED_NUMERATOR = {
    FILTER_STATUS_UNFILTERED: "demand_shares_unfiltered",
    FILTER_STATUS_FILTERED: "demand_shares_filtered",
}

# --- Section 8 checks 2, 9, 13, 14 (BORSAI_VALIDATOR_INTEGRITY_GATES_20260908_V1) ---
# These four are integrity gates, not R2-content checks: membership against the
# frozen batch table, canonical-artifact hash immutability, the outcome
# firewall, and the per-batch file manifest. Checks 6, 7, 8, 10 (derivation,
# conflict integrity, duplicates, canonical agreement) are explicitly out of
# scope for this task and are not touched.

# Repo-relative paths, never hardcoded as absolute and never resolved from the
# process's cwd - always anchored on this file's own location, two directories
# below the repo root (scripts/validation/validate_batch.py).
CONFIG_SCHEMA_TOML_PATHS = ("config/ipo_master_schema.toml", "config/ipo_master_schema_v2.toml")

# Every *_canonical_promotion_manifest.json under a Historical99 cohort's own
# canonical/ directory already records the sha256 of the files it promoted
# (BORSAI_HISTORICAL99_CANONICAL_PROMOTION_01). This is check 9's "kayitli hash
# listesi" for the Historical99 canonical artifacts - found by glob, not by
# naming one cohort here, so a future cohort's manifest is picked up unchanged.
HISTORICAL99_CANONICAL_PROMOTION_MANIFEST_GLOB = (
    "artifacts/ipo_master/historical99/*/canonical/*_canonical_promotion_manifest.json"
)

# No existing recorded hash for the two config schema TOMLs was found anywhere
# in the repo (searched before writing this). This validator owns the
# bootstrap baseline for them; it is generated once, under artifacts/governance/
# (an allowed write), and every later run compares against it rather than
# regenerating it.
VALIDATOR_CONFIG_SCHEMA_BASELINE_PATH = (
    "artifacts/governance/BORSAI_VALIDATOR_CONFIG_SCHEMA_HASH_BASELINE.json"
)

# Check 13(a) - column half. Matched as a whole underscore-delimited token
# against each header column name (never a bare substring, so e.g. "disclosed"
# never matches "close").
OUTCOME_FIREWALL_FORBIDDEN_COLUMN_TOKENS = {
    "close", "open", "high", "low", "volume", "turnover", "ohlcv",
    "return", "getiri", "tavan", "taban", "drawdown",
    "d1", "d3", "d5", "d10",
}

# Check 13(a) - value half. Only the free-text columns that legitimately quote
# source prose are scanned (never a structured/typed column, which checks 3-5
# already govern). "notes" is the only one of these three present on the
# demand-category and register schemas; raw_value/verbatim_source_phrase are
# offer-level-only, and the scan functions filter to whichever of the three
# actually exist on the file's header.
OUTCOME_FIREWALL_TEXT_COLUMNS = ("raw_value", "verbatim_source_phrase", "notes")

# Deliberately narrow, multi-word or otherwise unambiguous phrases only. A
# bare "fiyat" (price) is excluded on purpose: it is the ordinary vocabulary of
# legitimate offer-side fields (price_determination_method,
# price_stability_undertaking) and would swamp the scan with false positives -
# mirrors the same design choice already made for _FALLBACK_FORBIDDEN_TOKENS
# excluding a bare "0" above.
OUTCOME_FIREWALL_FORBIDDEN_TEXT_PHRASES = (
    "kapanış fiyatı", "kapanis fiyati",
    "ilk işlem günü kapanış", "ilk islem gunu kapanis",
    "tavan fiyat", "tavan yaptı", "tavan yapti",
    "taban yaptı", "taban yapti",
    "getiri oranı", "getiri orani",
    "ohlcv",
    "d1 getiri", "d3 getiri", "d5 getiri", "d10 getiri",
    "drawdown",
)

# Check 7 - conflict integrity (BORSAI_VALIDATOR_CHECK7_AND_COVERAGE_20260912_T19).
# The three field_status values the spec JSON's conflict_rules defines as
# "both rows recorded" outcomes: SOURCES_CONFLICT, SCOPE_DIFFERENCE and
# SEMANTIC_DIFFERENCE. SEMANTICALLY_AMBIGUOUS and SPEC_EDGE_CASE_UNRESOLVED
# are also conflict_rules entries but describe a single escalated row, not a
# conflict_group_id-bound pair, so they are out of this check's scope.
CONFLICT_STATUS_FIELD_STATUSES = ("SOURCES_CONFLICT", "SCOPE_DIFFERENCE", "SEMANTIC_DIFFERENCE")

# SPEC R5 §R5.1 (D1, BORSAI_D1_POINT_IN_TIME_GATE_20260912_V1). The only two
# scope_tag values §R5.1 makes a point-in-time claim about on a
# KAP_COMPANY_RECORD row: AS_OF_RETRIEVAL (always compliant, item 1) and
# AS_OF_LISTING (compliant only under item 3's newly-listed-issuer
# exception). Any other scope_tag on such a row (NOT_APPLICABLE in practice)
# asserts no listing/retrieval claim at all and is out of this gate's scope.
D1_RELEVANT_SCOPE_TAGS = ("AS_OF_LISTING", "AS_OF_RETRIEVAL")

# Matches the leading YYYY-MM-DD of an ISO datetime like
# "2026-09-12T11:30:22+03:00" - retrieval_timestamp_istanbul's format -
# unlike DATE_RE (defined below), which anchors both ends for a bare date
# cell such as source_publication_date.
ISO_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


@dataclass
class Violation:
    file: str
    row: int  # 1-indexed data row (header excluded); 0 for file-level
    column: str
    found_value: str
    rule_code: str
    message: str

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "row": self.row,
            "column": self.column,
            "found_value": self.found_value,
            "rule_code": self.rule_code,
            "message": self.message,
        }


@dataclass
class Warning_:
    """Reported, counted separately, never a violation and never a gate input."""
    file: str
    row: int
    column: str
    found_value: str
    rule_code: str
    message: str

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "row": self.row,
            "column": self.column,
            "found_value": self.found_value,
            "rule_code": self.rule_code,
            "message": self.message,
        }


@dataclass
class Report:
    violations: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    multiple_undertakings: list = field(default_factory=list)
    register_seen: bool = False
    register_required_cells: int = 0
    register_covered_cells: int = 0
    spec_enum_missing: list = field(default_factory=list)
    # R4/R5 are measurement-only exposure counters (BORSAI_SPEC_CLARIFY_20260906_T7).
    # They never become violations and never affect the gate verdict.
    # Each is reported twice: including order_count, and excluding it. order_count is
    # DATA_NOT_FOUND on essentially every row in practice, so the including-variant is
    # dominated by that one field and the excluding-variant is the informative number.
    r4_exposure_count: int = 0
    r4_exposure_count_excl_order_count: int = 0
    r5_exposure_count: int = 0
    r5_exposure_count_excl_order_count: int = 0
    # Check 11 (aggregate/leaf guard) and check 12 (arithmetic consistency) are
    # both "report only" per section 8: a found divergence IS a Violation (it
    # counts toward the gate, unlike MULTIPLE_UNDERTAKINGS, which section 8
    # item 15 itself labels "informational, not a failure" - checks 11/12 carry
    # no such label), but the script must never guess past a sentinel input
    # (BORSAI_R2_CONSISTENCY_CHECKS_20260906_T9C). These counters record how
    # much of each check's surface was actually computable, separate from any
    # violation found.
    check11_families_evaluated: int = 0
    check11_uncheckable_field_comparisons: int = 0
    check11_uncheckable_breakdown: dict = field(default_factory=dict)
    check12_pairs_evaluated: int = 0
    check12_uncheckable_pairs: int = 0
    check12_uncheckable_breakdown: dict = field(default_factory=dict)
    # Check 12, R3 text (BORSAI_CHECK12_R3_IMPLEMENTATION_20260908_V1) - a
    # separate counter set, never mixed with the R2 counters above, so a run
    # under --check12-revision r2 (check_arithmetic_consistency, untouched)
    # and a run under the R3 default (check_arithmetic_consistency_r3) each
    # report their own, honest coverage instead of one function's zeros
    # silently padding the other's totals.
    check12_r3_pairs_evaluated: int = 0
    check12_r3_uncheckable_pairs: int = 0
    check12_r3_uncheckable_breakdown: dict = field(default_factory=dict)
    # Per-ticker audit trail (R3 §8 check 12, "the per-batch report states, for
    # every ticker, the #5 value it applied and the numerator it designated,
    # so a reader can audit the gate rather than infer it").
    check12_r3_ticker_filter_applications: list = field(default_factory=list)
    # Check 11 Branch B, R4 text (BORSAI_R4_IMPLEMENTATION_20260909_V1) - a
    # separate counter set from check11_families_evaluated/check11_uncheckable_*
    # above, which stay Branch A's own counters (reused unchanged in name and
    # meaning under --check11-revision r4, per R4 section 8 check 11's own
    # "keeps its existing shape and its existing counters" instruction).
    check11_r4_percentage_cells_checked: int = 0
    check11_r4_percentage_cells_matched: int = 0
    check11_r4_percentage_base_cells: int = 0
    check11_r4_percentage_cells_uncheckable: int = 0
    check11_r4_percentage_uncheckable_breakdown: dict = field(default_factory=dict)
    # Per (ticker, percentage field) audit trail, mirroring
    # check12_r3_ticker_filter_applications above: "the base row identified for
    # each percentage field and its nominal" (R4 section 8 check 11 coverage
    # reporting).
    check11_r4_percentage_base_applications: list = field(default_factory=list)
    # Check 13(b) - outcome firewall date gate (BORSAI_CHECK13_UNCHECKABLE_AND_B05_20260911_V1).
    # check_outcome_firewall_date_gate has always excluded a sentinel/malformed
    # source_publication_date or an unmapped ticker from "checked" via a silent
    # `continue` - never counted as a pass, matching checks 11/12's own rule. But
    # unlike checks 11/12, it recorded no counter for *how many* rows that was or
    # *why*, so a reader could only reconstruct the exclusion by re-deriving it
    # outside the validator (as the B03/B04 task reports' Adım 5 did by hand).
    # These fields give check 13(b) the same uncheckable-bucket visibility check
    # 11/12 already have; they do not change which rows are excluded.
    check13_date_gate_rows_checked: int = 0
    check13_date_gate_violations: int = 0
    check13_date_gate_uncheckable_rows: int = 0
    check13_date_gate_uncheckable_breakdown: dict = field(default_factory=dict)
    # Check 7 - conflict integrity (BORSAI_VALIDATOR_CHECK7_AND_COVERAGE_20260912_T19).
    # checked/passed describe rule 1's conflict_group_id-sharing coverage
    # only (a row whose field_status is one of CONFLICT_STATUS_FIELD_STATUSES
    # and whose conflict_group_id is not NOT_APPLICABLE); violations
    # aggregates both rule 1 (CONFLICT_GROUP_ORPHAN) and rule 2
    # (CONFLICT_GROUP_UNMARKED_SIBLING) findings. out_of_scope counts
    # conflict_group_id = NOT_APPLICABLE rows, which never enter this check
    # at all - not checked, not uncheckable.
    check7_checked: int = 0
    check7_passed: int = 0
    check7_violations: int = 0
    check7_out_of_scope_not_applicable: int = 0
    # Check 7's denominator (BORSAI_D1_POINT_IN_TIME_GATE_20260912_V1, O6):
    # rows_in_file is every data row check_conflict_group_integrity actually
    # iterates (both files it runs on, cumulative); rows_with_conflict_family
    # is how many of those carry a CONFLICT_STATUS_FIELD_STATUSES value
    # (checked's source, before the NOT_APPLICABLE carve-out). Without this,
    # "checked=0 / out_of_scope=0" cannot be told apart from "0 rows in the
    # file" and "135 rows, none of them conflict-family".
    check7_rows_in_file: int = 0
    check7_rows_with_conflict_family_status: int = 0
    # R5 §R5.1 (D1) - point-in-time source constraint on a live company
    # record (BORSAI_D1_POINT_IN_TIME_GATE_20260912_V1). Not one of section
    # 8's 17 numbered checks. checked/passed/violations describe
    # KAP_COMPANY_RECORD rows scope-tagged AS_OF_LISTING that could be
    # compared against the ticker's canonical first_trading_date;
    # AS_OF_RETRIEVAL rows are unconditionally compliant (passed, no
    # comparison needed). out_of_scope rows never carry a listing/retrieval
    # claim about a live source at all.
    d1_checked: int = 0
    d1_passed: int = 0
    d1_violations: int = 0
    d1_uncheckable: int = 0
    d1_uncheckable_breakdown: dict = field(default_factory=dict)
    d1_out_of_scope_not_kap_company_record: int = 0
    d1_out_of_scope_scope_tag_not_a_claim: int = 0

    def add(self, v: Violation) -> None:
        self.violations.append(v)

    def warn(self, w: "Warning_") -> None:
        self.warnings.append(w)


class SpecLoadError(Exception):
    pass


def load_spec(spec_path: str) -> dict:
    try:
        with open(spec_path, "r", encoding="utf-8-sig") as fh:
            spec = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecLoadError(f"cannot parse spec JSON at {spec_path}: {exc}") from exc

    required_top = ["output_schema", "enums_reused_verbatim", "field_dictionary"]
    for key in required_top:
        if key not in spec:
            raise SpecLoadError(f"spec JSON missing required top-level key: {key}")
    if "offer_level_csv" not in spec["output_schema"] or "demand_category_csv" not in spec["output_schema"]:
        raise SpecLoadError("spec JSON output_schema missing offer_level_csv/demand_category_csv")
    return spec


def build_spec_registry(specs: list) -> dict:
    """Index loaded specs by the `spec_version` string each one declares.

    Routing is by what a spec says about itself, never by filename or CLI order,
    so a mixed R1/R2 file (§7.4 item 4) can be validated row by row.
    """
    registry = {}
    for spec in specs:
        version = spec.get("spec_version")
        if not version:
            raise SpecLoadError("spec JSON has no spec_version string; cannot route rows to it")
        if version in registry:
            raise SpecLoadError(f"two specs both declare spec_version {version}")
        registry[version] = spec
    return registry


def resolve_file_spec(header: list[str], table_key: str, registry: dict, default: dict) -> dict:
    """Pick the spec whose column list for `table_key` matches this file's header.

    The header is one shape per file, so schema validation is file-level; only the
    per-row semantics (§8 check 1) are resolved by spec_version.
    """
    for spec in registry.values():
        table = spec.get("output_schema", {}).get(table_key)
        if table and table.get("columns") == header:
            return spec
    return default


def spec_for_row(row_version: str, registry: dict, file_spec: dict, label: str,
                  row_idx: int, report: Report) -> dict:
    """Route one row to the spec revision it declares (§8 check 1, §7.4 item 4)."""
    if not row_version or row_version == file_spec.get("spec_version"):
        return file_spec
    spec = registry.get(row_version)
    if spec is None:
        report.add(Violation(label, row_idx, "spec_version", row_version, "SPEC_VERSION_UNKNOWN",
                              "row declares a spec_version with no spec loaded; pass its "
                              "--spec-json so the row can be validated against its own revision"))
        return file_spec
    return spec


def duration_field_names(spec: dict) -> set:
    """Offer fields governed by §2.1.1, read from the spec, never hardcoded.

    Empty for R1, which defines no duration undertaking field — so §8 check 15 is
    inert on an R1 delivery rather than misfiring on it.
    """
    return {f["field_name"] for f in spec.get("field_dictionary", {}).get("offer_level_fields", [])
            if f.get("duration_start_reference_required")}


def duration_units(spec: dict) -> list:
    block = spec.get("output_schema", {}).get("derived_duration_fields_r2") or {}
    for f in spec.get("field_dictionary", {}).get("offer_level_fields", []):
        if f.get("duration_start_reference_required") and isinstance(f.get("unit"), list):
            return list(f["unit"])
    return list(block.get("units") or [])


def spec_has_register(spec: dict) -> bool:
    return "category_cell_status_csv" in spec.get("output_schema", {})


def read_raw_csv_text(path: str) -> tuple[str, bool, str]:
    """Returns (text_without_bom, had_bom, newline_style)."""
    with open(path, "rb") as fh:
        raw = fh.read()
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    if had_bom:
        raw = raw[len(b"\xef\xbb\xbf"):]
    text = raw.decode("utf-8")
    crlf = text.count("\r\n")
    lf_total = text.count("\n")
    newline_style = "CRLF" if crlf > 0 and crlf == lf_total else ("LF" if lf_total > 0 else "NONE")
    return text, had_bom, newline_style


def parse_csv_rows(text: str) -> list[list[str]]:
    reader = csv.reader(io.StringIO(text))
    return [row for row in reader]


def get_enum_values(spec: dict, key: str) -> list | None:
    val = spec.get("enums_reused_verbatim", {}).get(key)
    if isinstance(val, list):
        return val
    return None


def get_category_data_fields(spec: dict) -> list:
    """The 15 demand-category data fields, read from the frozen spec JSON.

    Source of truth: field_dictionary.demand_category_data_fields (§2.2 / §5.5).
    These are the columns that carry a cell-level DATA_NOT_FOUND sentinel; the
    remaining 16 columns of the 31-column schema are provenance/audit columns.
    """
    val = spec.get("field_dictionary", {}).get("demand_category_data_fields")
    if isinstance(val, list) and val:
        return list(val)
    return []


def check_format(path: str, label: str, report: Report) -> tuple[list[str], list[list[str]]]:
    text, had_bom, newline_style = read_raw_csv_text(path)
    if not had_bom:
        report.add(Violation(label, 0, "<file>", "no BOM", "FORMAT_BOM",
                              "file is not UTF-8 with BOM as required by output_schema.encoding"))
    if newline_style != "CRLF":
        report.add(Violation(label, 0, "<file>", newline_style, "FORMAT_LINE_ENDING",
                              "line endings are not CRLF as required by output_schema.line_ending"))

    rows = parse_csv_rows(text)
    if not rows:
        return [], []
    header = rows[0]
    data_rows = rows[1:]
    return header, data_rows


NUMERIC_JUNK_RE = re.compile(r"[₺$€]|(?<=\d),(?=\d{3}\b)")
LEADING_TRAILING_WS_RE = re.compile(r"^\s|\s$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DECIMAL_COMMA_RE = re.compile(r"\d,\d(?!\d{3})")


def check_cell_format(label: str, row_idx: int, column: str, value: str, report: Report) -> None:
    """Format checks that apply to every cell regardless of the field's data type.

    FORMAT_DECIMAL_SEPARATOR is deliberately NOT here: it only makes sense for a
    cell that is supposed to hold a normalized number. See
    check_numeric_decimal_separator(), which is gated on the field's frozen
    field_dictionary type and is called only for such cells.
    """
    if LEADING_TRAILING_WS_RE.search(value):
        report.add(Violation(label, row_idx, column, value, "FORMAT_WHITESPACE",
                              "cell has leading or trailing whitespace"))
    if "," in value and re.search(r"\d,\d{3}(\D|$)", value):
        report.add(Violation(label, row_idx, column, value, "FORMAT_THOUSANDS_SEPARATOR",
                              "value appears to retain a thousands separator"))
    if re.search(r"[₺$€]", value):
        report.add(Violation(label, row_idx, column, value, "FORMAT_CURRENCY_SYMBOL",
                              "value retains a currency symbol"))
    if column.endswith("_date") and value not in ALLOWED_SENTINELS and value != "" and not DATE_RE.match(value):
        report.add(Violation(label, row_idx, column, value, "FORMAT_DATE",
                              "date field is not in YYYY-MM-DD format"))


def check_numeric_decimal_separator(label: str, row_idx: int, column: str, value: str, report: Report) -> None:
    """FORMAT_DECIMAL_SEPARATOR, restricted to cells the frozen spec says hold a
    numeric (decimal/integer) field's normalized value. Never applied to
    raw_value (which legitimately preserves the source's own notation, comma
    included), verbatim_source_phrase or notes (free Turkish prose)."""
    if DECIMAL_COMMA_RE.search(value):
        report.add(Violation(label, row_idx, column, value, "FORMAT_DECIMAL_SEPARATOR",
                              "value appears to use a comma as decimal separator instead of '.'"))


def check_schema(label: str, header: list[str], expected_columns: list[str], report: Report) -> bool:
    ok = True
    if header != expected_columns:
        ok = False
        if len(header) != len(expected_columns):
            report.add(Violation(label, 0, "<header>", f"{len(header)} columns", "SCHEMA_COLUMN_COUNT",
                                  f"expected {len(expected_columns)} columns, found {len(header)}"))
        max_len = max(len(header), len(expected_columns))
        for i in range(max_len):
            got = header[i] if i < len(header) else "<missing>"
            want = expected_columns[i] if i < len(expected_columns) else "<extra>"
            if got != want:
                report.add(Violation(label, 0, f"col[{i}]", got, "SCHEMA_COLUMN_MISMATCH",
                                      f"expected column '{want}' at position {i}, found '{got}'"))
    return ok


def near_miss(value: str, allowed: list[str]) -> str | None:
    for candidate in allowed:
        if value == candidate:
            return None
    upper_value = value.upper()
    for candidate in allowed:
        if upper_value == candidate.upper() and value != candidate:
            return candidate
    for candidate in allowed:
        if len(value) > 3 and (value in candidate or candidate in value) and value != candidate:
            return candidate
    return None


def check_enum_cell(label: str, row_idx: int, column: str, value: str, enum_key: str,
                     spec: dict, report: Report, allow_sentinels: bool = False) -> None:
    allowed = get_enum_values(spec, enum_key)
    if allowed is None:
        if enum_key not in report.spec_enum_missing:
            report.spec_enum_missing.append(enum_key)
        return
    if allow_sentinels and value in ALLOWED_SENTINELS:
        return
    if value in allowed:
        return
    nm = near_miss(value, allowed)
    if nm is not None:
        report.add(Violation(label, row_idx, column, value, "ENUM_NEAR_MISS",
                              f"value '{value}' is not an exact match for allowed enum value '{nm}' (case/typo variant)"))
    else:
        report.add(Violation(label, row_idx, column, value, "ENUM_VIOLATION",
                              f"value '{value}' is not in the frozen enum for {enum_key}: {allowed}"))


def check_sentinel_and_empty(label: str, row_idx: int, column: str, value: str, report: Report) -> None:
    if value == "":
        report.add(Violation(label, row_idx, column, value, "SENTINEL_EMPTY_CELL",
                              "empty cell; use one of DATA_NOT_FOUND / SOURCES_CONFLICT / NOT_APPLICABLE or a real value"))
        return
    if value in ALLOWED_SENTINELS:
        return
    for token in _FALLBACK_FORBIDDEN_TOKENS:
        if value.strip().lower() == token.lower():
            report.add(Violation(label, row_idx, column, value, "SENTINEL_FORBIDDEN_TOKEN",
                                  f"'{value}' is a forbidden absence encoding; only DATA_NOT_FOUND, "
                                  f"SOURCES_CONFLICT or NOT_APPLICABLE are valid sentinels"))
            return


def is_generic_search_scope(stripped_value: str) -> bool:
    """Content-based SEARCH_SCOPE_GENERIC test (F2 fix).

    A search_scope is generic only if it is one of a fixed set of known
    non-answers (case-insensitive) or consists entirely of punctuation. A
    single, specific document-family token such as "KAP_SONUC_BILDIRIMI" is
    NOT generic — token count is no longer used as a proxy for content.
    """
    if stripped_value.lower() in GENERIC_SEARCH_SCOPE_TOKENS:
        return True
    if PUNCTUATION_ONLY_RE.match(stripped_value):
        return True
    return False


def build_field_name_closure(spec: dict) -> set[str]:
    names = {f["field_name"] for f in spec["field_dictionary"]["offer_level_fields"]}
    identity = spec["field_dictionary"].get("identity_completion_field")
    if identity and "field_name" in identity:
        names.add(identity["field_name"])
    return names


def build_field_type_map(spec: dict) -> dict[str, str]:
    return {f["field_name"]: f.get("type") for f in spec["field_dictionary"]["offer_level_fields"]}


def validate_offer_csv(path: str, spec: dict, report: Report,
                        registry: dict | None = None,
                        canonical_first_trading_dates: dict | None = None) -> list[list[str]]:
    label = "offer_level"
    if registry is None:
        registry = {spec.get("spec_version"): spec}
    header, data_rows = check_format(path, label, report)
    if not header:
        return []
    file_spec = resolve_file_spec(header, "offer_level_csv", registry, spec)
    check_schema(label, header, file_spec["output_schema"]["offer_level_csv"]["columns"], report)

    col_index = {name: i for i, name in enumerate(header)}

    def cell(row: list[str], name: str) -> str:
        idx = col_index.get(name)
        if idx is None or idx >= len(row):
            return ""
        return row[idx]

    seen_undertakings: dict = {}

    for r, row in enumerate(data_rows, start=1):
        if len(row) != len(header):
            report.add(Violation(label, r, "<row>", f"{len(row)} cells", "SCHEMA_ROW_LENGTH",
                                  f"row has {len(row)} cells, header has {len(header)}"))
            continue

        row_spec = spec_for_row(cell(row, "spec_version"), registry, file_spec, label, r, report)
        field_names = build_field_name_closure(row_spec)
        field_types = build_field_type_map(row_spec)

        for name in header:
            value = cell(row, name)
            check_sentinel_and_empty(label, r, name, value, report)
            check_cell_format(label, r, name, value, report)

        field_name = cell(row, "field_name")
        if field_name and field_name not in field_names:
            report.add(Violation(label, r, "field_name", field_name, "FIELD_NAME_CLOSURE",
                                  "field_name is not one of the frozen 22 offer-level fields or "
                                  "company_name for the spec revision this row declares"))

        for col_name, enum_key in COLUMN_TO_ENUM_KEY.items():
            if col_name in col_index:
                check_enum_cell(label, r, col_name, cell(row, col_name), enum_key, row_spec, report)
        if "duration_start_reference" in col_index:
            check_enum_cell(label, r, "duration_start_reference",
                             cell(row, "duration_start_reference"),
                             "duration_start_reference", row_spec, report)

        check_duration_integrity(label, r, row, cell, col_index, row_spec, report, seen_undertakings)

        field_type = field_types.get(field_name)
        normalized_value = cell(row, "normalized_value")
        field_status = cell(row, "field_status")
        if field_status == "VALUE_RECORDED" and field_type == "enum":
            check_enum_cell(label, r, "normalized_value (field_name=" + field_name + ")",
                             normalized_value, field_name, spec, report)
        elif field_status == "VALUE_RECORDED" and field_type == "boolean":
            check_enum_cell(label, r, "normalized_value (field_name=" + field_name + ")",
                             normalized_value, BOOLEAN_ENUM_KEY, spec, report)

        # field_type is None both when field_name is unrecognized (already flagged by
        # FIELD_NAME_CLOSURE above) and when field_dictionary carries no "type" for it
        # (e.g. the company_name identity field). Per F3, missing type information
        # means "treat as non-numeric", never a BLOCKED condition.
        if field_status == "VALUE_RECORDED" and field_type in NUMERIC_FIELD_TYPES:
            check_numeric_decimal_separator(label, r, "normalized_value", normalized_value, report)

        if field_status == "DATA_NOT_FOUND":
            search_scope = cell(row, "search_scope")
            stripped = search_scope.strip()
            if not stripped:
                report.add(Violation(label, r, "search_scope", search_scope, "SEARCH_SCOPE_EMPTY",
                                      "search_scope must be filled for every DATA_NOT_FOUND row"))
            elif is_generic_search_scope(stripped):
                report.add(Violation(label, r, "search_scope", search_scope, "SEARCH_SCOPE_GENERIC",
                                      "search_scope is a generic non-answer (rejected literal or "
                                      "punctuation-only), not a named document family actually opened"))

    for key, entries in seen_undertakings.items():
        if len(entries) > 1:
            ticker, field_name = key
            report.multiple_undertakings.append({
                "ticker": ticker, "field_name": field_name,
                "undertaking_count": len(entries),
                "undertakings": entries,
                "note": "informational, not a failure - section 2.1.1 item 2 makes this the "
                        "correct recording; resolution is the derivation script's "
                        "MULTIPLE_UNDERTAKINGS_NOT_REDUCIBLE (section 5.4.1 item 3)"})

    check_c1(label, header, col_index, data_rows, report)
    check_order(label, "batch_id", spec, header, col_index, data_rows, report, ticker_col="ticker")
    check_price_stability_consistency(label, header, col_index, data_rows, report)
    check_membership(label, header, col_index, data_rows, spec, report)
    check_outcome_firewall_columns(label, header, report)
    check_outcome_firewall_text(label, header, col_index, data_rows, report)
    check_outcome_firewall_date_gate(label, header, col_index, data_rows,
                                      canonical_first_trading_dates or {}, report)
    check_conflict_group_integrity(label, header, col_index, data_rows, report)
    check_point_in_time_source_constraint(label, header, col_index, data_rows,
                                           canonical_first_trading_dates or {}, report)
    return data_rows


PLAIN_DECIMAL_RE = re.compile(r"^-?\d+(\.\d+)?$")


def check_duration_integrity(label: str, r: int, row: list[str], cell, col_index: dict,
                              row_spec: dict, report: Report, seen: dict) -> None:
    """Section 8 check 15 - duration-field integrity, applied exactly as R2 states it.

    Inert on a revision that defines no duration undertaking field (i.e. R1).
    """
    duration_fields = duration_field_names(row_spec)
    if not duration_fields:
        return
    if "duration_start_reference" not in col_index or "undertaking_scope" not in col_index:
        return

    field_name = cell(row, "field_name")
    unit = cell(row, "unit")
    start_ref = cell(row, "duration_start_reference")
    scope = cell(row, "undertaking_scope")
    normalized_value = cell(row, "normalized_value")

    if field_name not in duration_fields:
        # "For every other field name, both R2 columns are NOT_APPLICABLE."
        for col_name, value in (("duration_start_reference", start_ref),
                                 ("undertaking_scope", scope)):
            if value != "NOT_APPLICABLE":
                report.add(Violation(label, r, col_name, value, "DURATION_COLUMN_NOT_APPLICABLE",
                                      f"{col_name} must be NOT_APPLICABLE on a non-duration field "
                                      f"(field_name={field_name})"))
        return

    allowed_units = duration_units(row_spec) or ["DAYS", "MONTHS", "YEARS"]
    if unit not in allowed_units:
        report.add(Violation(label, r, "unit", unit, "DURATION_UNIT_INVALID",
                              f"unit on a duration field must be one of {allowed_units}"))
    for col_name, value in (("duration_start_reference", start_ref),
                             ("undertaking_scope", scope)):
        if value == "NOT_APPLICABLE":
            report.add(Violation(label, r, col_name, value, "DURATION_COLUMN_REQUIRED",
                                  f"{col_name} is mandatory on a duration field and must not be "
                                  f"NOT_APPLICABLE (field_name={field_name})"))

    # "normalized_value is a plain decimal or DATA_NOT_FOUND". A 0 is a legitimate
    # source-stated value and is never reported as an absence.
    if normalized_value != "DATA_NOT_FOUND" and not PLAIN_DECIMAL_RE.match(normalized_value):
        report.add(Violation(label, r, "normalized_value", normalized_value,
                              "DURATION_VALUE_NOT_PLAIN_DECIMAL",
                              "normalized_value on a duration field must be a plain decimal "
                              "or DATA_NOT_FOUND"))

    entry = {"normalized_value": normalized_value, "unit": unit,
             "duration_start_reference": start_ref, "undertaking_scope": scope}
    bucket = seen.setdefault((cell(row, "ticker"), field_name), [])
    if entry not in bucket:
        bucket.append(entry)


def check_price_stability_consistency(label: str, header: list[str], col_index: dict,
                                       data_rows: list[list[str]], report: Report) -> None:
    """WARNING only - the spec does not require this, so it is never a violation.

    price_stability_planned = FALSE alongside a non-zero price_stability_undertaking
    is internally odd and worth a human glance, but no provision of R1 or R2 makes
    it an error, so it is reported in its own channel and touches no gate.
    """
    needed = ("ticker", "field_name", "normalized_value")
    if any(c not in col_index for c in needed):
        return

    def cell(row, name):
        idx = col_index[name]
        return row[idx] if idx < len(row) else ""

    planned_false, undertakings = set(), []
    for r, row in enumerate(data_rows, start=1):
        if len(row) != len(header):
            continue
        name, value = cell(row, "field_name"), cell(row, "normalized_value")
        if name == "price_stability_planned" and value == "FALSE":
            planned_false.add(cell(row, "ticker"))
        elif name == "price_stability_undertaking":
            undertakings.append((r, cell(row, "ticker"), value))

    for r, ticker, value in undertakings:
        if ticker not in planned_false or value == "DATA_NOT_FOUND":
            continue
        try:
            if Decimal(value) == 0:
                continue
        except (InvalidOperation, ValueError):
            continue
        report.warn(Warning_(label, r, "normalized_value", value,
                             "PRICE_STABILITY_PLANNED_VS_UNDERTAKING",
                             f"{ticker}: price_stability_planned is FALSE but "
                             f"price_stability_undertaking is {value} (non-zero). Not a spec "
                             f"violation - no provision requires these to agree - but worth "
                             f"a human check."))


def check_c1(label: str, header: list[str], col_index: dict[str, int], data_rows: list[list[str]],
             report: Report) -> None:
    if "ticker" not in col_index or "batch_id" not in col_index or "field_name" not in col_index:
        return
    groups: dict[tuple[str, str], dict[str, list[str]]] = {}
    for r, row in enumerate(data_rows, start=1):
        if len(row) != len(header):
            continue
        key = (row[col_index["batch_id"]], row[col_index["ticker"]])
        groups.setdefault(key, {})
        field_name = row[col_index["field_name"]]
        if field_name in ("total_demand_multiple_value", "total_demand_filter_status"):
            groups[key][field_name] = row

    for key, fields in groups.items():
        multiple_row = fields.get("total_demand_multiple_value")
        status_row = fields.get("total_demand_filter_status")
        if multiple_row is None or status_row is None:
            continue
        multiple_norm = multiple_row[col_index["normalized_value"]]
        multiple_status = multiple_row[col_index["field_status"]]
        status_value = status_row[col_index["normalized_value"]]
        is_absent = multiple_status == "DATA_NOT_FOUND" or multiple_norm in ("", "DATA_NOT_FOUND")
        # F1: per CLARIFICATION.md C1, NOT_APPLICABLE is the ONE correct value when the
        # multiple has no referent. Every other value is a violation, not only
        # UNFILTERED/FILTERED — this includes DATA_NOT_FOUND and SOURCES_CONFLICT,
        # which a narrower check would wrongly let through as a false negative.
        if is_absent and status_value != "NOT_APPLICABLE":
            row_num = None
            for r, row in enumerate(data_rows, start=1):
                if row is status_row:
                    row_num = r
                    break
            report.add(Violation(label, row_num or 0, "total_demand_filter_status", status_value, "C1_VIOLATION",
                                  f"ticker {key[1]}: total_demand_multiple_value is sentinel/absent "
                                  f"but total_demand_filter_status is '{status_value}' instead of NOT_APPLICABLE"))


def check_order(label: str, batch_col: str, spec: dict, header: list[str], col_index: dict[str, int],
                 data_rows: list[list[str]], report: Report, ticker_col: str) -> None:
    if batch_col not in col_index or ticker_col not in col_index:
        return
    batches = spec.get("batch_plan", {}).get("batches", {})
    seen_order: dict[str, list[str]] = {}
    for row in data_rows:
        if len(row) != len(header):
            continue
        batch_id = row[col_index[batch_col]]
        ticker = row[col_index[ticker_col]]
        order_list = seen_order.setdefault(batch_id, [])
        if not order_list or order_list[-1] != ticker:
            if ticker not in order_list:
                order_list.append(ticker)

    for batch_id, observed_order in seen_order.items():
        expected = batches.get(batch_id)
        if expected is None:
            continue
        expected_present = [t for t in expected if t in observed_order]
        if observed_order != expected_present:
            report.add(Violation(label, 0, ticker_col, ",".join(observed_order), "SIRA_TICKER_ORDER_MISMATCH",
                                  f"batch {batch_id}: ticker order {observed_order} does not match the frozen "
                                  f"first_trading_date-ascending order {expected_present}"))


def check_membership(label: str, header: list[str], col_index: dict[str, int],
                      data_rows: list[list[str]], spec: dict, report: Report) -> None:
    """Section 8 check 2 - bidirectional ticker/batch membership against the
    frozen section 7.2 table, read from spec['batch_plan']['batches'] (the
    same field check_order already reads - never a list embedded here).

    A batch_id absent from that table (B00, the calibration batch of section 6,
    which section 7.2 does not cover) is out of scope for this check, exactly
    as check_order already treats an unrecognised batch_id.
    """
    if "batch_id" not in col_index or "ticker" not in col_index:
        return
    batches = spec.get("batch_plan", {}).get("batches", {})
    observed: dict[str, set] = {}
    for row in data_rows:
        if len(row) != len(header):
            continue
        batch_id = row[col_index["batch_id"]]
        observed.setdefault(batch_id, set()).add(row[col_index["ticker"]])

    for batch_id, observed_tickers in observed.items():
        expected = batches.get(batch_id)
        if expected is None:
            continue
        expected_set = set(expected)
        for ticker in sorted(expected_set - observed_tickers):
            report.add(Violation(label, 0, "ticker", ticker, "MEMBERSHIP_TICKER_MISSING",
                                  f"batch {batch_id}: ticker '{ticker}' is listed in the frozen "
                                  f"section 7.2 table for this batch but does not appear in the "
                                  f"file"))
        for ticker in sorted(observed_tickers - expected_set):
            report.add(Violation(label, 0, "ticker", ticker, "MEMBERSHIP_TICKER_EXTRA",
                                  f"batch {batch_id}: ticker '{ticker}' appears in the file under "
                                  f"batch_id={batch_id} but is not listed in the frozen section "
                                  f"7.2 table for that batch"))


def _repo_root() -> Path:
    """scripts/validation/validate_batch.py -> repo root, two directories up.

    Never derived from the process's cwd, so discovery below behaves the same
    regardless of where the validator is invoked from.
    """
    return Path(__file__).resolve().parents[2]


def sha256_of_file(path) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _discover_historical99_canonical_registry(repo_root: Path) -> tuple[dict, str | None]:
    """Section 8 check 9, first half - the Historical99 canonical artifacts.

    Locates the existing recorded sha256 list by globbing for the one
    *_canonical_promotion_manifest.json under
    artifacts/ipo_master/historical99/*/canonical/ (never a hardcoded cohort
    name) and reading its own canonical_outputs section, which already records
    the sha256 of every file it promoted.

    artifacts/outcomes/ is deliberately never searched here: the outcome
    firewall (check 13 / section 0.4) forbids reading anything from that tree
    beyond ticker/first_trading_date, and a promotion manifest's
    canonical_outputs are not scoped to those two columns.

    Returns ({repo-relative path: recorded sha256}, manifest's own
    repo-relative path, or None if zero or more than one manifest was found).
    """
    matches = sorted(repo_root.glob(HISTORICAL99_CANONICAL_PROMOTION_MANIFEST_GLOB))
    if len(matches) != 1:
        return {}, None
    manifest_path = matches[0]
    try:
        with open(manifest_path, "r", encoding="utf-8-sig") as fh:
            manifest = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}, None
    registry = {}
    for entry in manifest.get("canonical_outputs", {}).values():
        path, sha = entry.get("path"), entry.get("sha256")
        if path and sha:
            registry[path] = sha
    return registry, str(manifest_path.relative_to(repo_root))


def _load_or_generate_config_schema_baseline(repo_root: Path) -> tuple[dict, bool]:
    """Section 8 check 9, second half - the config schema TOMLs.

    No existing recorded hash for these two files was found anywhere in the
    repo (searched before writing this validator). On first run this
    generates a baseline manifest under artifacts/governance/ (an allowed
    write, per ADIM 3); every later run compares against it instead of
    regenerating it. The baseline, once written, is never silently
    overwritten - a later mismatch is check 9's hard STOP, not a cue to
    regenerate.

    Returns ({repo-relative path: sha256}, True if generated this run).
    """
    baseline_path = repo_root / VALIDATOR_CONFIG_SCHEMA_BASELINE_PATH
    if baseline_path.exists():
        with open(baseline_path, "r", encoding="utf-8-sig") as fh:
            baseline = json.load(fh)
        return baseline.get("sha256_by_path", {}), False

    sha256_by_path = {}
    for rel_path in CONFIG_SCHEMA_TOML_PATHS:
        full_path = repo_root / rel_path
        if full_path.exists():
            sha256_by_path[rel_path] = sha256_of_file(full_path)
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    with open(baseline_path, "w", encoding="utf-8") as fh:
        json.dump({
            "task_id": "BORSAI_VALIDATOR_INTEGRITY_GATES_20260908_V1",
            "purpose": "section 8 check 9 (canonical immutability) genesis baseline for the "
                       "config schema TOMLs - no pre-existing recorded hash was found in the "
                       "repo for these two files. Never regenerated automatically; a future "
                       "mismatch against these values is a hard STOP (CLAUDE.md section 8), "
                       "not a reason to overwrite this file.",
            "sha256_by_path": sha256_by_path,
        }, fh, indent=2, ensure_ascii=False)
    return sha256_by_path, True


def check_canonical_immutability(report: Report, repo_root: Path | None = None) -> dict:
    """Section 8 check 9. Recomputes sha256 of every frozen canonical
    Historical99 artifact and of the config schema TOMLs, and compares each
    against its recorded value. Any change is a hard STOP (CLAUDE.md section
    8): a mismatch is reported as CANONICAL_IMMUTABILITY_HASH_MISMATCH, which
    - like every other Violation - drives the batch verdict to FAIL. This
    function never repairs, regenerates, overwrites or normalizes away a
    mismatch; it only reports one.
    """
    repo_root = repo_root or _repo_root()
    historical99_registry, manifest_rel_path = _discover_historical99_canonical_registry(repo_root)
    config_registry, baseline_generated = _load_or_generate_config_schema_baseline(repo_root)

    def _verify_group(registry: dict, group: str) -> list:
        group_results = []
        for rel_path, recorded in registry.items():
            full_path = repo_root / rel_path
            if not full_path.exists():
                report.add(Violation("canonical_immutability", 0, rel_path, "<missing>",
                                      "CANONICAL_IMMUTABILITY_FILE_MISSING",
                                      f"[{group}] {rel_path}: recorded in the canonical hash "
                                      f"registry but the file no longer exists on disk"))
                group_results.append({"path": rel_path, "group": group, "status": "MISSING",
                                       "recorded": recorded})
                continue
            actual = sha256_of_file(full_path)
            if actual != recorded:
                report.add(Violation("canonical_immutability", 0, rel_path, actual,
                                      "CANONICAL_IMMUTABILITY_HASH_MISMATCH",
                                      f"[{group}] {rel_path}: recorded sha256 {recorded} does not "
                                      f"match current sha256 {actual}. CLAUDE.md section 8 hard "
                                      f"STOP - do not repair, regenerate, overwrite or normalize "
                                      f"this away; report and escalate."))
                group_results.append({"path": rel_path, "group": group, "status": "MISMATCH",
                                       "recorded": recorded, "actual": actual})
            else:
                group_results.append({"path": rel_path, "group": group, "status": "MATCH",
                                       "sha256": actual})
        return group_results

    files = (_verify_group(historical99_registry, "historical99_canonical")
             + _verify_group(config_registry, "config_schema"))

    return {
        "historical99_canonical_registry_source": manifest_rel_path,
        "historical99_canonical_files_checked": len(historical99_registry),
        "config_schema_baseline_path": VALIDATOR_CONFIG_SCHEMA_BASELINE_PATH,
        "config_schema_baseline_generated_this_run": baseline_generated,
        "config_schema_files_checked": len(config_registry),
        "files": files,
    }


def discover_historical99_first_trading_date_source(repo_root: Path):
    """Section 8 check 13(b) support. Locates the canonical ticker /
    first_trading_date source under artifacts/outcomes/historical99/**/ by
    header content, never a hardcoded filename: every *canonical*.csv there is
    opened for its header row ONLY (a header names columns; it carries no
    ticker's outcome value) and kept as a candidate if it names both 'ticker'
    and 'first_trading_date'. Among candidates, the file with the FEWEST
    columns is chosen - deterministic, and it minimizes the width of unrelated
    (on at least one candidate, genuinely price-bearing: OHLCV) columns a
    csv.reader's per-row buffer transiently holds while only ticker /
    first_trading_date are ever extracted from it.

    Returns (chosen_path_or_None, chosen_header_or_[], all_candidate_repo_relative_paths).
    """
    base = repo_root / "artifacts" / "outcomes" / "historical99"
    if not base.exists():
        return None, [], []
    candidates = []
    for path in sorted(base.rglob("*canonical*.csv")):
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            header = next(csv.reader(fh), [])
        if "ticker" in header and "first_trading_date" in header:
            candidates.append((path, header))
    if not candidates:
        return None, [], []
    candidates.sort(key=lambda pair: (len(pair[1]), str(pair[0])))
    chosen_path, chosen_header = candidates[0]
    all_candidate_paths = [str(p.relative_to(repo_root)) for p, _ in candidates]
    return chosen_path, chosen_header, all_candidate_paths


def load_canonical_first_trading_dates(path: Path, header: list[str]) -> dict[str, str]:
    """Reads ONLY the ticker and first_trading_date columns, by index, from
    the discovered canonical file. No other column's value is ever assigned
    to a variable here (ADIM 1b's own rule: no other column is read)."""
    ticker_idx = header.index("ticker")
    date_idx = header.index("first_trading_date")
    result: dict[str, str] = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        next(reader, None)
        for row in reader:
            if len(row) <= max(ticker_idx, date_idx):
                continue
            ticker = row[ticker_idx]
            if ticker and ticker not in result:
                result[ticker] = row[date_idx]
    return result


def check_outcome_firewall_columns(label: str, header: list[str], report: Report) -> None:
    """Section 8 check 13(a), column half."""
    for column in header:
        tokens = {t for t in re.split(r"[^a-z0-9]+", column.lower()) if t}
        hit = tokens & OUTCOME_FIREWALL_FORBIDDEN_COLUMN_TOKENS
        if hit:
            report.add(Violation(label, 0, column, column, "OUTCOME_FIREWALL_COLUMN",
                                  f"column '{column}' names a post-listing outcome token "
                                  f"{sorted(hit)}; no post-listing price/return/OHLCV field is "
                                  f"permitted in a collection batch (section 0.4)"))


def check_outcome_firewall_text(label: str, header: list[str], col_index: dict[str, int],
                                 data_rows: list[list[str]], report: Report) -> int:
    """Section 8 check 13(a), value half. Scans only the free-text columns
    that legitimately quote source prose for a narrow set of unambiguous
    post-listing phrases. Returns the number of hits found."""
    scan_columns = [c for c in OUTCOME_FIREWALL_TEXT_COLUMNS if c in col_index]
    if not scan_columns:
        return 0
    hits = 0
    for r, row in enumerate(data_rows, start=1):
        if len(row) != len(header):
            continue
        for column in scan_columns:
            value = row[col_index[column]]
            lowered = value.lower()
            for phrase in OUTCOME_FIREWALL_FORBIDDEN_TEXT_PHRASES:
                if phrase in lowered:
                    hits += 1
                    report.add(Violation(label, r, column, value, "OUTCOME_FIREWALL_TEXT",
                                          f"'{column}' contains the post-listing phrase "
                                          f"'{phrase}'; section 0.4 forbids recording any "
                                          f"post-listing fact, even one quoted from a source "
                                          f"document that also carries offer-result data"))
    return hits


def check_outcome_firewall_date_gate(label: str, header: list[str], col_index: dict[str, int],
                                      data_rows: list[list[str]],
                                      canonical_first_trading_dates: dict,
                                      report: Report) -> tuple[int, int]:
    """Section 8 check 13(b) - the date gate.

    For every row, compares source_publication_date against that ticker's
    canonical first_trading_date. source_publication_date > first_trading_date
    is a FAIL: the source could not have been read before the ticker started
    trading. Uncheckable rows (sentinel/malformed date, or no canonical anchor
    for that ticker) are neither a pass nor a fail - never guessed. Per
    BORSAI_CHECK13_UNCHECKABLE_AND_B05_20260911_V1, that exclusion is now also
    counted and bucketed on report.check13_date_gate_uncheckable_breakdown,
    mirroring checks 11/12's own uncheckable-bucket pattern, instead of being
    a silent `continue` a reader could only reconstruct by hand.

    Returns (rows_checked, violations_found) - unchanged for any existing
    caller that reads the return value directly.

    BORSAI_VALIDATOR_CHECK7_AND_COVERAGE_20260912_T19: a file whose schema has
    no source_publication_date column at all (the section 5.6 register) used
    to fall through the "ticker"/"source_publication_date" pre-check below
    and return (0, 0) with no accounting entry anywhere - the gap was
    invisible. Every data row is now individually bucketed
    REGISTER_HAS_NO_DATE_COLUMN instead, so it reads as uncheckable, never as
    a silent pass.
    """
    if "ticker" not in col_index:
        return 0, 0
    if "source_publication_date" not in col_index:
        for _ in data_rows:
            _bump(report.check13_date_gate_uncheckable_breakdown,
                  "REGISTER_HAS_NO_DATE_COLUMN")
            report.check13_date_gate_uncheckable_rows += 1
        return 0, 0
    if not canonical_first_trading_dates:
        return 0, 0
    checked = 0
    violations = 0
    for r, row in enumerate(data_rows, start=1):
        if len(row) != len(header):
            continue
        ticker = row[col_index["ticker"]]
        pub_date = row[col_index["source_publication_date"]]
        if pub_date in ALLOWED_SENTINELS or not DATE_RE.match(pub_date):
            _bump(report.check13_date_gate_uncheckable_breakdown,
                  "NO_PUBLICATION_DATE_UNCHECKABLE")
            report.check13_date_gate_uncheckable_rows += 1
            continue
        anchor = canonical_first_trading_dates.get(ticker)
        if not anchor or not DATE_RE.match(anchor):
            _bump(report.check13_date_gate_uncheckable_breakdown,
                  "NO_CANONICAL_ANCHOR_UNCHECKABLE")
            report.check13_date_gate_uncheckable_rows += 1
            continue
        checked += 1
        report.check13_date_gate_rows_checked += 1
        if pub_date > anchor:
            violations += 1
            report.check13_date_gate_violations += 1
            report.add(Violation(label, r, "source_publication_date", pub_date,
                                  "OUTCOME_FIREWALL_DATE_GATE",
                                  f"{ticker}: source_publication_date {pub_date} is after this "
                                  f"ticker's canonical first_trading_date {anchor}; the source "
                                  f"could not have been read pre-first-trade (section 0.4)"))
    return checked, violations


def check_conflict_group_integrity(label: str, header: list[str], col_index: dict[str, int],
                                    data_rows: list[list[str]], report: Report) -> None:
    """Section 8 check 7 - conflict integrity (BORSAI_VALIDATOR_CHECK7_AND_COVERAGE_20260912_T19).

    Two rules, both scoped to rows whose field_status is one of
    CONFLICT_STATUS_FIELD_STATUSES:

    CONFLICT_GROUP_ORPHAN - such a row's conflict_group_id is not shared by
    any other row in this file (a lone conflict-status row has nothing to be
    mechanically bound to; conflict_group_id_rationale in the spec JSON).

    CONFLICT_GROUP_UNMARKED_SIBLING - the same identity - (ticker, field_name,
    scope_tag) where both columns exist (the offer CSV); (ticker,
    normalized_category, source_category_label) where they do not but the
    category identity columns do (the demand-category CSV) - carries both a
    conflict-status row and exactly one other, unmarked/resolved row (any
    field_status not in CONFLICT_STATUS_FIELD_STATUSES).

    conflict_group_id = NOT_APPLICABLE rows never enter either rule: not
    counted as checked, not counted as uncheckable, tallied separately on
    report.check7_out_of_scope_not_applicable.

    Not applicable to a file with no conflict_group_id column (the section
    5.6 register): returns immediately.
    """
    if "conflict_group_id" not in col_index or "field_status" not in col_index:
        return

    def cell(row: list[str], name: str) -> str:
        idx = col_index.get(name)
        return row[idx] if idx is not None and idx < len(row) else ""

    if "field_name" in col_index and "scope_tag" in col_index:
        identity_cols: tuple[str, ...] | None = ("ticker", "field_name", "scope_tag")
    elif "normalized_category" in col_index and "source_category_label" in col_index:
        identity_cols = ("ticker", "normalized_category", "source_category_label")
    else:
        identity_cols = None

    group_rows: dict[str, list[int]] = {}
    identity_rows: dict[tuple, list[tuple[int, str, str]]] = {}

    for r, row in enumerate(data_rows, start=1):
        if len(row) != len(header):
            continue
        status = cell(row, "field_status")
        cg = cell(row, "conflict_group_id")
        is_conflict_status = status in CONFLICT_STATUS_FIELD_STATUSES
        report.check7_rows_in_file += 1
        if is_conflict_status:
            report.check7_rows_with_conflict_family_status += 1
        if is_conflict_status and cg == "NOT_APPLICABLE":
            report.check7_out_of_scope_not_applicable += 1
            category = None
        elif is_conflict_status:
            report.check7_checked += 1
            group_rows.setdefault(cg, []).append(r)
            category = "conflict"
        else:
            category = "resolved"
        if identity_cols is not None and category is not None:
            key = tuple(cell(row, c) for c in identity_cols)
            identity_rows.setdefault(key, []).append((r, category, status))

    for cg, rows in group_rows.items():
        if len(rows) < 2:
            for r in rows:
                report.check7_violations += 1
                report.add(Violation(label, r, "conflict_group_id", cg,
                                      "CONFLICT_GROUP_ORPHAN",
                                      f"field_status is a conflict-family value but "
                                      f"conflict_group_id '{cg}' is not shared by any other "
                                      f"row in this file"))
        else:
            report.check7_passed += len(rows)

    if identity_cols is not None:
        for key, entries in identity_rows.items():
            conflict_rows = [r for r, category, _status in entries if category == "conflict"]
            resolved = [(r, status) for r, category, status in entries if category == "resolved"]
            if conflict_rows and len(resolved) == 1:
                sibling_row, sibling_status = resolved[0]
                conflict_row_numbers = sorted(conflict_rows)
                report.check7_violations += 1
                report.add(Violation(label, sibling_row, "field_status", sibling_status,
                                      "CONFLICT_GROUP_UNMARKED_SIBLING",
                                      f"identity {dict(zip(identity_cols, key))} carries both a "
                                      f"conflict-status row (rows {conflict_row_numbers}) and "
                                      f"exactly one other, unmarked resolved row (row "
                                      f"{sibling_row}) for the same identity"))


def check_point_in_time_source_constraint(label: str, header: list[str], col_index: dict[str, int],
                                           data_rows: list[list[str]],
                                           canonical_first_trading_dates: dict,
                                           report: Report) -> None:
    """SPEC R5 §R5.1 (D1) - point-in-time source constraint on a live company
    record (BORSAI_D1_POINT_IN_TIME_GATE_20260912_V1). This is NOT one of
    section 8's 17 numbered checks; it audits R5's own binding rule.

    A row whose source_document_type is KAP_COMPANY_RECORD may carry
    scope_tag AS_OF_LISTING only when its retrieval_timestamp_istanbul's
    date part is on or before the ticker's canonical first_trading_date
    (§R5.1 item 3, the newly-listed-issuer exception); otherwise the row is
    POINT_IN_TIME_UNVERIFIED - a live page retrieved after listing cannot
    represent the listing moment. AS_OF_RETRIEVAL rows are always compliant
    (§R5.1 item 1) and need no date comparison. POINT_IN_TIME_UNVERIFIED is
    a rule code only, never added to field_status or any other vocabulary
    (§R5.1 item 4) - no delivered cell is read as anything but what it says.

    Requires ticker, source_document_type, scope_tag and
    retrieval_timestamp_istanbul all present in this file's schema. A file
    missing any of them is entirely out of scope and returns immediately,
    touching no counter - e.g. the demand-category CSV has
    source_document_type but no scope_tag (measured, not assumed), and the
    section 5.6 register has neither.
    """
    needed = ("ticker", "source_document_type", "scope_tag", "retrieval_timestamp_istanbul")
    if any(c not in col_index for c in needed):
        return

    def cell(row: list[str], name: str) -> str:
        idx = col_index.get(name)
        return row[idx] if idx is not None and idx < len(row) else ""

    for r, row in enumerate(data_rows, start=1):
        if len(row) != len(header):
            continue
        doc_type = cell(row, "source_document_type")
        if doc_type != "KAP_COMPANY_RECORD":
            report.d1_out_of_scope_not_kap_company_record += 1
            continue
        scope_tag = cell(row, "scope_tag")
        if scope_tag not in D1_RELEVANT_SCOPE_TAGS:
            report.d1_out_of_scope_scope_tag_not_a_claim += 1
            continue
        if scope_tag == "AS_OF_RETRIEVAL":
            report.d1_passed += 1
            continue
        # scope_tag == "AS_OF_LISTING": needs the first_trading_date comparison.
        ticker = cell(row, "ticker")
        anchor = canonical_first_trading_dates.get(ticker)
        if not anchor or not DATE_RE.match(anchor):
            _bump(report.d1_uncheckable_breakdown, "NO_CANONICAL_ANCHOR_UNCHECKABLE")
            report.d1_uncheckable += 1
            continue
        retrieval_ts = cell(row, "retrieval_timestamp_istanbul")
        match = ISO_DATE_PREFIX_RE.match(retrieval_ts)
        if not match:
            _bump(report.d1_uncheckable_breakdown, "RETRIEVAL_TIMESTAMP_UNPARSEABLE_UNCHECKABLE")
            report.d1_uncheckable += 1
            continue
        retrieval_date = match.group(0)
        report.d1_checked += 1
        if retrieval_date > anchor:
            report.d1_violations += 1
            report.add(Violation(label, r, "scope_tag", scope_tag, "POINT_IN_TIME_UNVERIFIED",
                                  f"{ticker}: KAP_COMPANY_RECORD row scope-tagged AS_OF_LISTING "
                                  f"but retrieved {retrieval_date}, after this ticker's canonical "
                                  f"first_trading_date {anchor} (SPEC R5 §R5.1 items 2-3); a live "
                                  f"page retrieved after listing cannot represent the listing "
                                  f"moment"))
        else:
            report.d1_passed += 1


def build_manifest_block(args, offer_rows: list, category_rows: list,
                          register_rows: list | None) -> dict:
    """Section 8 check 14. sha256 and row counts for every batch CSV, all
    derived from the actual files on disk (CLAUDE.md section 23) - never
    compared against a hardcoded historical constant. Row counts reuse the
    already-parsed data_rows rather than re-reading the file a second time."""
    manifest = {
        "offer_level_csv": {
            "path": args.offer,
            "sha256": sha256_of_file(args.offer),
            "row_count": len(offer_rows),
        },
        "demand_category_csv": {
            "path": args.category,
            "sha256": sha256_of_file(args.category),
            "row_count": len(category_rows),
        },
    }
    if args.cell_status:
        manifest["category_cell_status_csv"] = {
            "path": args.cell_status,
            "sha256": sha256_of_file(args.cell_status),
            "row_count": len(register_rows or []),
        }
    return manifest


def count_r4_r5_exposure(row: list[str], col_index: dict[str, int],
                          category_data_fields: list, report: Report) -> None:
    """Measurement-only R4/R5 exposure counters for one demand-category row.

    R4 — rows carrying a cell-level absence that has nowhere to declare its
    search scope. The demand-category schema has no `search_scope` column
    (COLLECTOR_INSTRUCTION §10.1), while §4.4 requires a non-empty search scope
    on every DATA_NOT_FOUND. A row is counted when **at least one** of the 15
    data fields is DATA_NOT_FOUND.

    R5 — rows whose 15 data fields are of **mixed** status (at least one
    DATA_NOT_FOUND and at least one real value), so the single row-level
    `field_status` column cannot describe them (COLLECTOR_INSTRUCTION §10.2).

    Both are counted twice, with and without `order_count`. `order_count` is
    DATA_NOT_FOUND on essentially every row, so it alone would drive both
    counters to "every row" and hide the real distribution.

    Neither counter is a violation. Neither affects the gate verdict.
    """
    if not category_data_fields:
        return

    def status(name: str) -> str | None:
        idx = col_index.get(name)
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    for exclude_order_count in (False, True):
        fields = [f for f in category_data_fields
                  if not (exclude_order_count and f == "order_count")]
        values = [v for v in (status(f) for f in fields) if v is not None]
        if not values:
            continue
        has_absent = any(v == "DATA_NOT_FOUND" for v in values)
        has_value = any(v != "DATA_NOT_FOUND" for v in values)
        if exclude_order_count:
            if has_absent:
                report.r4_exposure_count_excl_order_count += 1
            if has_absent and has_value:
                report.r5_exposure_count_excl_order_count += 1
        else:
            if has_absent:
                report.r4_exposure_count += 1
            if has_absent and has_value:
                report.r5_exposure_count += 1


def validate_category_csv(path: str, spec: dict, report: Report,
                           registry: dict | None = None,
                           canonical_first_trading_dates: dict | None = None) -> list[list[str]]:
    label = "demand_category"
    if registry is None:
        registry = {spec.get("spec_version"): spec}
    header, data_rows = check_format(path, label, report)
    if not header:
        return []
    file_spec = resolve_file_spec(header, "demand_category_csv", registry, spec)
    check_schema(label, header, file_spec["output_schema"]["demand_category_csv"]["columns"], report)

    col_index = {name: i for i, name in enumerate(header)}

    def cell(row: list[str], name: str) -> str:
        idx = col_index.get(name)
        if idx is None or idx >= len(row):
            return ""
        return row[idx]

    category_data_fields = get_category_data_fields(file_spec)

    for r, row in enumerate(data_rows, start=1):
        if len(row) != len(header):
            report.add(Violation(label, r, "<row>", f"{len(row)} cells", "SCHEMA_ROW_LENGTH",
                                  f"row has {len(row)} cells, header has {len(header)}"))
            continue

        for name in header:
            value = cell(row, name)
            check_sentinel_and_empty(label, r, name, value, report)
            check_cell_format(label, r, name, value, report)

        for col_name, enum_key in COLUMN_TO_ENUM_KEY.items():
            if col_name in col_index:
                check_enum_cell(label, r, col_name, cell(row, col_name), enum_key, spec, report)

        if "is_aggregate" in col_index:
            check_enum_cell(label, r, "is_aggregate", cell(row, "is_aggregate"), BOOLEAN_ENUM_KEY, spec, report)

        source_parent_label = cell(row, "source_parent_label")
        if source_parent_label == "NOT_APPLICABLE" or source_parent_label.strip() == "":
            report.add(Violation(label, r, "source_parent_label", source_parent_label, "C2_VIOLATION",
                                  "source_parent_label absence must be encoded as DATA_NOT_FOUND, "
                                  "never NOT_APPLICABLE or blank"))

        count_r4_r5_exposure(row, col_index, category_data_fields, report)

    check_order(label, "batch_id", spec, header, col_index, data_rows, report, ticker_col="ticker")
    check_membership(label, header, col_index, data_rows, spec, report)
    check_outcome_firewall_columns(label, header, report)
    check_outcome_firewall_text(label, header, col_index, data_rows, report)
    check_outcome_firewall_date_gate(label, header, col_index, data_rows,
                                      canonical_first_trading_dates or {}, report)
    check_conflict_group_integrity(label, header, col_index, data_rows, report)
    check_point_in_time_source_constraint(label, header, col_index, data_rows,
                                           canonical_first_trading_dates or {}, report)
    return data_rows


def validate_register_csv(path: str, spec: dict, report: Report,
                           registry: dict | None = None,
                           canonical_first_trading_dates: dict | None = None
                           ) -> tuple[list[str], list[list[str]]]:
    """Section 5.6 - the demand-category cell-status register, 9 columns.

    Only revisions that declare category_cell_status_csv have one; handing this a
    file under a revision that does not define it is a schema failure, not a crash.
    """
    label = "category_cell_status"
    if registry is None:
        registry = {spec.get("spec_version"): spec}
    table = None
    for candidate in list(registry.values()) + [spec]:
        if spec_has_register(candidate):
            table = candidate["output_schema"]["category_cell_status_csv"]
            reg_spec = candidate
            break
    if table is None:
        report.add(Violation(label, 0, "<file>", path, "REGISTER_NOT_DEFINED_BY_SPEC",
                              "a cell-status register was supplied but no loaded spec revision "
                              "defines category_cell_status_csv"))
        return [], []

    header, data_rows = check_format(path, label, report)
    if not header:
        return [], []
    check_schema(label, header, table["columns"], report)
    col_index = {name: i for i, name in enumerate(header)}
    data_fields = set(get_category_data_fields(reg_spec))

    def cell(row, name):
        idx = col_index.get(name)
        if idx is None or idx >= len(row):
            return ""
        return row[idx]

    for r, row in enumerate(data_rows, start=1):
        if len(row) != len(header):
            report.add(Violation(label, r, "<row>", f"{len(row)} cells", "SCHEMA_ROW_LENGTH",
                                  f"row has {len(row)} cells, header has {len(header)}"))
            continue

        for name in header:
            check_sentinel_and_empty(label, r, name, cell(row, name), report)
            check_cell_format(label, r, name, cell(row, name), report)

        row_spec = spec_for_row(cell(row, "spec_version"), registry, reg_spec, label, r, report)
        check_enum_cell(label, r, "field_status", cell(row, "field_status"),
                        "field_status", row_spec, report)
        check_enum_cell(label, r, "normalized_category", cell(row, "normalized_category"),
                        "normalized_categories", row_spec, report)

        field_name = cell(row, "field_name")
        if field_name not in data_fields:
            report.add(Violation(label, r, "field_name", field_name, "REGISTER_FIELD_NAME_CLOSURE",
                                  "field_name must be one of the 15 demand-category data fields"))

        # "every register row with field_status = DATA_NOT_FOUND has a non-empty,
        # non-generic search_scope" (section 8 check 16)
        if cell(row, "field_status") == "DATA_NOT_FOUND":
            search_scope = cell(row, "search_scope")
            stripped = search_scope.strip()
            if not stripped:
                report.add(Violation(label, r, "search_scope", search_scope,
                                      "SEARCH_SCOPE_EMPTY",
                                      "search_scope must be filled on every DATA_NOT_FOUND "
                                      "register row"))
            elif is_generic_search_scope(stripped):
                report.add(Violation(label, r, "search_scope", search_scope,
                                      "SEARCH_SCOPE_GENERIC",
                                      "search_scope is a generic non-answer, not a named "
                                      "document family actually opened"))

    check_outcome_firewall_columns(label, header, report)
    check_outcome_firewall_text(label, header, col_index, data_rows, report)
    check_outcome_firewall_date_gate(label, header, col_index, data_rows,
                                      canonical_first_trading_dates or {}, report)
    return header, data_rows


def register_key(row, col_index):
    def get(name):
        idx = col_index.get(name)
        return row[idx] if idx is not None and idx < len(row) else ""
    return (get("ticker"), get("normalized_category"), get("source_category_label"),
            get("field_name"))


def check_register_completeness(category_rows, category_header, register_header,
                                 register_rows, registry, spec, report: Report) -> None:
    """Section 8 check 16 - cell-status register completeness.

    Applies only to rows whose spec_version declares a register (section 7.4 item 6),
    so an R1 delivery with no third file is not a failure.
    """
    if not category_header:
        return
    cat_index = {name: i for i, name in enumerate(category_header)}
    reg_index = {name: i for i, name in enumerate(register_header)} if register_header else {}
    needed = ("ticker", "normalized_category", "source_category_label", "spec_version")
    if any(c not in cat_index for c in needed):
        return

    def cat(row, name):
        idx = cat_index.get(name)
        return row[idx] if idx is not None and idx < len(row) else ""

    register_index = {}
    for r, row in enumerate(register_rows or [], start=1):
        if len(row) != len(register_header):
            continue
        register_index.setdefault(register_key(row, reg_index), []).append(r)

    category_triples = set()
    required = []
    for row in category_rows:
        if len(row) != len(category_header):
            continue
        row_spec = registry.get(cat(row, "spec_version"), spec)
        triple = (cat(row, "ticker"), cat(row, "normalized_category"),
                  cat(row, "source_category_label"))
        category_triples.add(triple)
        if not spec_has_register(row_spec):
            continue  # section 7.4 item 6 - V1 rows are out of scope for this check
        for fname in get_category_data_fields(row_spec):
            idx = cat_index.get(fname)
            if idx is None or idx >= len(row):
                continue
            if row[idx] == "DATA_NOT_FOUND":
                required.append(triple + (fname,))

    report.register_required_cells += len(required)
    for key in required:
        hits = register_index.get(key, [])
        report.register_covered_cells += 1 if len(hits) == 1 else 0
        if not hits:
            report.add(Violation("demand_category", 0, key[3], "DATA_NOT_FOUND",
                                  "REGISTER_ROW_MISSING",
                                  f"{key[0]} / {key[1]} / {key[2]}: cell {key[3]} is "
                                  f"DATA_NOT_FOUND but has no cell-status register row; the "
                                  f"search-scope obligation is unmet"))
        elif len(hits) > 1:
            report.add(Violation("category_cell_status", hits[1], key[3], "DUPLICATE",
                                  "REGISTER_ROW_DUPLICATE",
                                  f"{key[0]} / {key[1]} / {key[2]}: cell {key[3]} has "
                                  f"{len(hits)} register rows; exactly one is required"))

    # "every register row resolves to an existing category row"
    for r, row in enumerate(register_rows or [], start=1):
        if len(row) != len(register_header):
            continue
        key = register_key(row, reg_index)
        if key[:3] not in category_triples:
            report.add(Violation("category_cell_status", r, "source_category_label", key[2],
                                  "REGISTER_ROW_ORPHAN",
                                  f"register row names {key[0]} / {key[1]} / {key[2]}, which is "
                                  f"not a row of this batch's demand-category CSV"))


def check_cross_file(offer_rows: list[list[str]], offer_header: list[str],
                      category_rows: list[list[str]], category_header: list[str], report: Report) -> None:
    if not offer_header or not category_header:
        return
    if "ticker" not in offer_header or "ticker" not in category_header:
        return
    offer_idx = offer_header.index("ticker")
    category_idx = category_header.index("ticker")
    offer_tickers = {row[offer_idx] for row in offer_rows if len(row) == len(offer_header)}
    seen = set()
    for r, row in enumerate(category_rows, start=1):
        if len(row) != len(category_header):
            continue
        ticker = row[category_idx]
        if ticker in seen:
            continue
        seen.add(ticker)
        if ticker not in offer_tickers:
            report.add(Violation("demand_category", r, "ticker", ticker, "CROSS_FILE_TICKER_MISSING",
                                  f"ticker '{ticker}' appears in demand-category CSV but not in offer-level CSV"))


def check_duplicates(offer_header: list[str], offer_rows: list[list[str]],
                      category_header: list[str], category_rows: list[list[str]],
                      register_header: list[str], register_rows: list[list[str]],
                      registry: dict, report: Report) -> None:
    """Section 8 check 8, R4 text in full (BORSAI_R4_IMPLEMENTATION_20260909_V1),
    replaces R2/R3's check 8 in full. Never implemented before this task: R2/R3
    stated four uniqueness keys but no function in this file enforced any of
    them (BORSAI_COLLECTION_SPEC_R4_20260909_T14 section 2, "none of check 8's
    four keys is enforced today").

    Three FAIL gates, unchanged in key/meaning/severity from R2/R3:

      - offer-level rows whose field_name is NOT one of section 2.1
        #15/#16/#17 (the duration fields):
        (ticker, field_name, scope_tag, source_url) must be unique;
      - demand-category rows:
        (ticker, normalized_category, source_category_label, source_url)
        must be unique;
      - section 5.6 register rows:
        (ticker, normalized_category, source_category_label, field_name) must
        be unique - left deliberately untouched, since section 5.6 binding
        rule 1 ("two rows for one cell is a FAIL, section 8 check 8") depends
        on it.

    One report-only observation, R4 (D2): offer-level rows whose field_name IS
    one of #15/#16/#17. Coded as a FAIL, the extended key
    (ticker, field_name, scope_tag, duration_start_reference, undertaking_scope,
    source_url) produces 11 violations across the five delivered batches, every
    one on shareholder_lockup_undertaking, every one a row pair section 2.1.1
    item 2 of this same specification declares correct (two undertakings of one
    field, from one document, differing only in duration and unit - the
    extended key does not carry duration or unit and cannot separate them).
    Measured true-positive rate: 0 in 101 duration rows. A repeat of this key
    is reported as DURATION_ROW_KEY_COLLISION - report-only, never
    gate-affecting; row preservation itself remains enforced by the 1:1
    derivation counter gate and by check 15's existing MULTIPLE_UNDERTAKINGS,
    neither of which any uniqueness key can weaken.

    Which offer-level field names fall under #15/#16/#17 is read from every
    loaded spec revision's own field_dictionary (duration_field_names), never
    hardcoded - the union across the registry, so a mixed R1/R2 delivery is
    handled without re-resolving each row's own spec_version (already done,
    with its own violation side effects, by validate_offer_csv).

    A second report-only case, R6 (D1) (BORSAI_VALIDATOR_R6_D1_IMPLEMENTATION
    _20260912_V1): within the offer-level non-duration FAIL gate above, a
    colliding key group of more than one row is reported as
    CONFLICT_FAMILY_ROW_KEY_COLLISION - report-only, never gate-affecting -
    instead of DUPLICATE_ROW_KEY when, and only when, ALL THREE hold: every
    row's conflict_group_id is present and not NOT_APPLICABLE; those values
    are all identical; and every row's field_status is a member of
    CONFLICT_STATUS_FIELD_STATUSES. The key itself is unchanged, and every
    other colliding group - including one tagged asymmetrically - remains
    DUPLICATE_ROW_KEY, FAIL. See _conflict_family_group() below for the exact
    reading of an absent/empty conflict_group_id or a missing column.
    """
    duration_fields: set = set()
    for spec in registry.values():
        duration_fields |= duration_field_names(spec)

    def _conflict_family_group(row_nums: list[int]) -> tuple[str, list[dict]] | None:
        """(R6, D1) - SPEC R6 section 8 check 8 / R6.1 lines 247-268: for a
        colliding offer-level non-duration key group of more than one row,
        report-only CONFLICT_FAMILY_ROW_KEY_COLLISION applies only where ALL
        THREE hold: (1) every row's conflict_group_id is present and not
        NOT_APPLICABLE, (2) those values are all identical, (3) every row's
        field_status is a member of CONFLICT_STATUS_FIELD_STATUSES (SOURCES_
        CONFLICT / SCOPE_DIFFERENCE / SEMANTIC_DIFFERENCE). R6's own text
        states that a conflict_group_id that is absent or empty fails
        condition 1 exactly like NOT_APPLICABLE; an entirely missing
        conflict_group_id or field_status column is read the same way here
        (not-tagged), a reading choice R6 does not separately state since it
        does not address that structural case. Any failure of any condition
        means the group is not a conflict family and stays DUPLICATE_ROW_KEY,
        FAIL, unchanged. Returns (shared conflict_group_id, per-row detail
        dicts naming field_status/normalized_value/page_or_section per the
        frozen text) when the group qualifies, else None.
        """
        if "conflict_group_id" not in off_idx or "field_status" not in off_idx:
            return None
        cg_values: set[str] = set()
        details = []
        for r in row_nums:
            row = offer_rows[r - 1]
            cg = row[off_idx["conflict_group_id"]]
            status = row[off_idx["field_status"]]
            if not cg or cg == "NOT_APPLICABLE":
                return None
            if status not in CONFLICT_STATUS_FIELD_STATUSES:
                return None
            cg_values.add(cg)
            details.append({
                "row": r,
                "field_status": status,
                "normalized_value": row[off_idx["normalized_value"]] if "normalized_value" in off_idx else "",
                "page_or_section": row[off_idx["page_or_section"]] if "page_or_section" in off_idx else "",
            })
        if len(cg_values) != 1:
            return None
        return next(iter(cg_values)), details

    def _report_fail_duplicates(label: str, rows: list[list[str]], header: list[str],
                                 key_columns: tuple, cite_column: str) -> None:
        idx = {name: i for i, name in enumerate(header)}
        if any(c not in idx for c in key_columns):
            return
        groups: dict[tuple, list[int]] = {}
        for r, row in enumerate(rows, start=1):
            if len(row) != len(header):
                continue
            key = tuple(row[idx[c]] for c in key_columns)
            groups.setdefault(key, []).append(r)
        for key, row_nums in groups.items():
            if len(row_nums) <= 1:
                continue
            first = row_nums[0]
            for r in row_nums[1:]:
                report.add(Violation(
                    label, r, cite_column, key[key_columns.index(cite_column)],
                    "DUPLICATE_ROW_KEY",
                    f"{key_columns} = {key} already appears at row {first}; section 8 check 8"))

    off_idx = {name: i for i, name in enumerate(offer_header)}
    if ("field_name" in off_idx
            and all(c in off_idx for c in OFFER_NON_DURATION_DUPLICATE_KEY_COLUMNS)):
        non_duration_groups: dict[tuple, list[int]] = {}
        duration_groups: dict[tuple, list[int]] = {}
        duration_key_ok = all(c in off_idx for c in OFFER_DURATION_DUPLICATE_KEY_COLUMNS)
        for r, row in enumerate(offer_rows, start=1):
            if len(row) != len(offer_header):
                continue
            field_name = row[off_idx["field_name"]]
            if field_name in duration_fields:
                if not duration_key_ok:
                    continue
                key = tuple(row[off_idx[c]] for c in OFFER_DURATION_DUPLICATE_KEY_COLUMNS)
                duration_groups.setdefault(key, []).append(r)
            else:
                key = tuple(row[off_idx[c]] for c in OFFER_NON_DURATION_DUPLICATE_KEY_COLUMNS)
                non_duration_groups.setdefault(key, []).append(r)

        for key, row_nums in non_duration_groups.items():
            if len(row_nums) <= 1:
                continue
            first = row_nums[0]
            conflict_family = _conflict_family_group(row_nums)
            if conflict_family is not None:
                shared_cg, details = conflict_family
                detail_text = "; ".join(
                    f"row {d['row']}: field_status={d['field_status']}, "
                    f"normalized_value={d['normalized_value']!r}, "
                    f"page_or_section={d['page_or_section']!r}"
                    for d in details)
                for r in row_nums[1:]:
                    report.warn(Warning_(
                        "offer_level", r, "field_name", key[1],
                        "CONFLICT_FAMILY_ROW_KEY_COLLISION",
                        f"(ticker, field_name, scope_tag, source_url) = {key} already appears "
                        f"at row {first}; shared conflict_group_id={shared_cg!r}; report-only "
                        f"per SPEC R6 D1 (section 8 check 8) - every row in this group carries "
                        f"the same conflict_group_id and a conflict-family field_status "
                        f"({', '.join(CONFLICT_STATUS_FIELD_STATUSES)}); not gate-affecting. "
                        f"{detail_text}"))
                continue
            for r in row_nums[1:]:
                report.add(Violation(
                    "offer_level", r, "field_name", key[1], "DUPLICATE_ROW_KEY",
                    f"(ticker, field_name, scope_tag, source_url) = {key} already appears at "
                    f"row {first}; section 8 check 8"))

        for key, row_nums in duration_groups.items():
            if len(row_nums) <= 1:
                continue
            first = row_nums[0]
            for r in row_nums[1:]:
                report.warn(Warning_(
                    "offer_level", r, "field_name", key[1], "DURATION_ROW_KEY_COLLISION",
                    "(ticker, field_name, scope_tag, duration_start_reference, "
                    f"undertaking_scope, source_url) = {key} already appears at row {first}; "
                    f"report-only per R4 D2 - section 2.1.1 item 2 makes two rows of one "
                    f"duration field, from one document, differing in duration and unit, two "
                    f"correct rows, and this extended key cannot separate that pair from a "
                    f"genuine duplicate. Not gate-affecting."))

    _report_fail_duplicates("demand_category", category_rows, category_header,
                             CATEGORY_DUPLICATE_KEY_COLUMNS, "source_category_label")

    if register_header:
        _report_fail_duplicates("category_cell_status", register_rows, register_header,
                                 REGISTER_DUPLICATE_KEY_COLUMNS, "field_name")


def _bump(counter: dict, key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def _decimal_places(value_str: str) -> int:
    """Digits after the decimal point in a plain-decimal string; 0 if none."""
    return len(value_str.split(".", 1)[1]) if "." in value_str else 0


def _parse_plain_decimal(value_str: str) -> Decimal | None:
    """A real, checkable number - never a sentinel, never free text.

    Returns None for DATA_NOT_FOUND / SOURCES_CONFLICT / NOT_APPLICABLE and for
    anything that is not a plain decimal, so callers treat all of those
    identically: "cannot compute", never "compute as zero" or "skip silently".
    """
    if not PLAIN_DECIMAL_RE.match(value_str):
        return None
    try:
        return Decimal(value_str)
    except InvalidOperation:
        return None


def check_aggregate_leaf_guard(category_header: list[str], category_rows: list[list[str]],
                                report: Report,
                                fields: tuple = AGGREGATE_LEAF_ADDITIVE_FIELDS) -> None:
    """Section 8 check 11 - aggregate/leaf guard, report-only.

    "Where both exist, compare the leaf sum against the aggregate row per
    category family and report divergence. Report only; never 'fix' by
    dropping a row."

    A "category family" is identified the way section 2.2 / the reused
    ipo_demand_category_schema.md define nesting: an AGGREGATE row's
    source_category_label is the source_parent_label its LEAF children carry,
    within one (batch_id, ticker). A family only exists, and is only compared,
    when at least one LEAF row actually names that AGGREGATE row's label as
    its parent ("where both exist").

    `fields` defaults to AGGREGATE_LEAF_ADDITIVE_FIELDS (all nine of R2/R3's
    fields, including the three percentages) - the unmodified R2/R3 behavior,
    reachable via --check11-revision r2r3. Under --check11-revision r4 this
    function is called with fields=AGGREGATE_LEAF_ADDITIVE_FIELDS_R4 (the six
    additive-only fields) for Branch A, which R4 section 8 check 11 states is
    "unchanged in every respect" from R2/R3 other than scope; Branch B (the
    three percentage fields) is check_percentage_base_reconstruction, below.
    Passing a narrower `fields` changes only which fields are iterated - the
    family-detection and comparison logic itself is untouched.

    Precision: the leaf sum is rounded to the number of decimal places the
    aggregate row's OWN cell is printed at (ROUND_HALF_UP - a documented
    convention, not stated by section 8; see README.md REZERV). This mirrors
    check 12's explicit "at the source's stated precision" wording rather than
    inventing an unrelated fixed tolerance, and reduces to exact integer
    equality for the count fields (0 decimal places).

    A family/field combination where the aggregate cell or any leaf cell is
    not a plain numeric value (DATA_NOT_FOUND, SOURCES_CONFLICT,
    NOT_APPLICABLE, or otherwise unparsable) cannot be summed. It is never
    treated as a match or a divergence - only counted, separately, in
    report.check11_uncheckable_breakdown.
    """
    needed = ("batch_id", "ticker", "source_category_label", "source_parent_label",
              "category_level")
    col_index = {name: i for i, name in enumerate(category_header)}
    if any(c not in col_index for c in needed):
        return

    def cell(row: list[str], name: str) -> str:
        idx = col_index.get(name)
        return row[idx] if idx is not None and idx < len(row) else ""

    groups: dict[tuple[str, str], list[tuple[int, list[str]]]] = {}
    for r, row in enumerate(category_rows, start=1):
        if len(row) != len(category_header):
            continue
        key = (cell(row, "batch_id"), cell(row, "ticker"))
        groups.setdefault(key, []).append((r, row))

    for (_batch_id, ticker), rows in groups.items():
        aggregates = [(r, row) for r, row in rows if cell(row, "category_level") == "AGGREGATE"]
        leaves = [(r, row) for r, row in rows if cell(row, "category_level") == "LEAF"]
        for agg_r, agg_row in aggregates:
            agg_label = cell(agg_row, "source_category_label")
            family_leaves = [(r, row) for r, row in leaves
                              if cell(row, "source_parent_label") == agg_label]
            if not family_leaves:
                continue  # "where both exist" - no leaf names this aggregate as its parent
            report.check11_families_evaluated += 1

            for field_name in fields:
                if field_name not in col_index:
                    continue
                agg_value_str = cell(agg_row, field_name)
                agg_value = _parse_plain_decimal(agg_value_str)
                if agg_value is None:
                    _bump(report.check11_uncheckable_breakdown, "aggregate_cell_not_numeric")
                    report.check11_uncheckable_field_comparisons += 1
                    continue

                leaf_values: list[Decimal] = []
                uncheckable = False
                for _, leaf_row in family_leaves:
                    leaf_value = _parse_plain_decimal(cell(leaf_row, field_name))
                    if leaf_value is None:
                        uncheckable = True
                        break
                    leaf_values.append(leaf_value)
                if uncheckable:
                    _bump(report.check11_uncheckable_breakdown, "leaf_cell_not_numeric")
                    report.check11_uncheckable_field_comparisons += 1
                    continue

                leaf_sum = sum(leaf_values, Decimal(0))
                precision = _decimal_places(agg_value_str)
                quantum = Decimal(1).scaleb(-precision)
                rounded_leaf_sum = leaf_sum.quantize(quantum, rounding=ARITHMETIC_ROUNDING)
                if rounded_leaf_sum != agg_value:
                    report.add(Violation(
                        "demand_category", agg_r, field_name, agg_value_str,
                        "AGGREGATE_LEAF_DIVERGENCE",
                        f"{ticker} / '{agg_label}': {field_name} on the aggregate row is "
                        f"{agg_value_str} but the sum of its {len(family_leaves)} leaf row(s) "
                        f"is {rounded_leaf_sum} (leaf sum rounded to {precision} decimal "
                        f"place(s), the aggregate's own stated precision); report-only, no row "
                        f"dropped or corrected"))


def check_percentage_base_reconstruction(category_header: list[str],
                                          category_rows: list[list[str]],
                                          report: Report) -> None:
    """Section 8 check 11, Branch B, R4 text in full
    (BORSAI_R4_IMPLEMENTATION_20260909_V1) - replaces R2/R3's percentage
    treatment inside check 11. Runs only under --check11-revision r4.

    R2/R3 compared the SUM OF PRINTED LEAF PERCENTAGES against the printed
    aggregate percentage - an equality the source never asserts, since each
    printed percentage is independently rounded. This branch compares EACH
    PRINTED PERCENTAGE CELL AGAINST ITSELF: its own nominal partner (section
    2.2's own pairing, PERCENTAGE_FIELD_TO_NOMINAL) divided by the ticker's
    percentage base nominal, at the cell's own printed precision. It never
    uses the family relation (source_parent_label) - unlike Branch A, it
    evaluates every row of the ticker, including tickers whose leaves declare
    no parent at all.

    Step A - the percentage base (per (batch_id, ticker, percentage field),
    independently): the row for which, in THAT field, category_level =
    AGGREGATE, is_aggregate = TRUE, and the printed cell parses as a plain
    decimal equal to 100 at its own precision - the row the source designates
    as the whole by printing the whole. Identified structurally; no
    source_category_label string ever participates.

      - zero or more than one such row -> every numeric percentage cell of
        that ticker/field is uncheckable, bucket no_unique_percentage_base;
      - the base row exists but its own nominal partner is not a plain
        decimal, or is zero -> same consequence, bucket
        percentage_base_nominal_unusable.

    Step B - per-cell reconstruction, for every row of the ticker whose
    percentage cell parses as a plain decimal:

      - the base row itself is counted under base_cells and not compared
        (base / base x 100 = 100 by construction, no information);
      - a non-base row whose own nominal partner is not a plain decimal is
        uncheckable, bucket cell_nominal_not_numeric - never passed;
      - otherwise round(own nominal / base nominal x 100, p), p = THIS cell's
        own printed decimal places, ROUND_HALF_UP, compared to the printed
        cell.

    Step C - severity: a disagreement is PERCENTAGE_BASE_RECONSTRUCTION_MISMATCH,
    a violation, gate-affecting - calculation_mismatch_policy governs
    correction, never severity (exactly as R3 section 8 check 12 Step C states).

    An uncheckable cell is never reported as a pass and never as a mismatch -
    only counted, in report.check11_r4_percentage_uncheckable_breakdown.
    """
    needed = ("batch_id", "ticker", "category_level", "is_aggregate")
    col_index = {name: i for i, name in enumerate(category_header)}
    if any(c not in col_index for c in needed):
        return
    if any(f not in col_index for f in PERCENTAGE_FIELDS):
        return

    def cell(row: list[str], name: str) -> str:
        idx = col_index.get(name)
        return row[idx] if idx is not None and idx < len(row) else ""

    groups: dict[tuple[str, str], list[tuple[int, list[str]]]] = {}
    for r, row in enumerate(category_rows, start=1):
        if len(row) != len(category_header):
            continue
        key = (cell(row, "batch_id"), cell(row, "ticker"))
        groups.setdefault(key, []).append((r, row))

    for (_batch_id, ticker), rows in groups.items():
        for pct_field in PERCENTAGE_FIELDS:
            nominal_field = PERCENTAGE_FIELD_TO_NOMINAL[pct_field]

            # The surface is numeric percentage cells only - a cell whose own
            # printed value is a sentinel or otherwise unparsable is not part
            # of this field's 245-cell count at all (never uncheckable,
            # never checked - it simply is not a percentage cell to reconstruct).
            numeric_rows: list[tuple[int, list[str], Decimal]] = []
            for r, row in rows:
                pct_val = _parse_plain_decimal(cell(row, pct_field))
                if pct_val is not None:
                    numeric_rows.append((r, row, pct_val))
            if not numeric_rows:
                continue

            # Step A.
            base_candidates = [
                (r, row) for r, row, pct_val in numeric_rows
                if cell(row, "category_level") == "AGGREGATE"
                and cell(row, "is_aggregate") == "TRUE"
                and pct_val == Decimal(100)
            ]
            if len(base_candidates) != 1:
                for r, _row, _pct_val in numeric_rows:
                    _bump(report.check11_r4_percentage_uncheckable_breakdown,
                          "no_unique_percentage_base")
                    report.check11_r4_percentage_cells_uncheckable += 1
                report.check11_r4_percentage_base_applications.append({
                    "ticker": ticker, "percentage_field": pct_field,
                    "base_row_found": False, "base_row_count": len(base_candidates),
                    "base_nominal": None,
                })
                continue

            base_r, base_row = base_candidates[0]
            base_nominal_str = cell(base_row, nominal_field)
            base_nominal = _parse_plain_decimal(base_nominal_str)
            if base_nominal is None or base_nominal == 0:
                for r, _row, _pct_val in numeric_rows:
                    _bump(report.check11_r4_percentage_uncheckable_breakdown,
                          "percentage_base_nominal_unusable")
                    report.check11_r4_percentage_cells_uncheckable += 1
                report.check11_r4_percentage_base_applications.append({
                    "ticker": ticker, "percentage_field": pct_field,
                    "base_row_found": True, "base_row": base_r,
                    "base_nominal": base_nominal_str, "base_nominal_usable": False,
                })
                continue

            report.check11_r4_percentage_base_applications.append({
                "ticker": ticker, "percentage_field": pct_field,
                "base_row_found": True, "base_row": base_r,
                "base_nominal": base_nominal_str, "base_nominal_usable": True,
            })

            # Step B/C.
            for r, row, pct_val in numeric_rows:
                if r == base_r:
                    report.check11_r4_percentage_base_cells += 1
                    continue

                own_nominal_str = cell(row, nominal_field)
                own_nominal = _parse_plain_decimal(own_nominal_str)
                if own_nominal is None:
                    _bump(report.check11_r4_percentage_uncheckable_breakdown,
                          "cell_nominal_not_numeric")
                    report.check11_r4_percentage_cells_uncheckable += 1
                    continue

                pct_str = cell(row, pct_field)
                precision = _decimal_places(pct_str)
                quantum = Decimal(1).scaleb(-precision)
                reconstructed = (own_nominal / base_nominal * 100).quantize(
                    quantum, rounding=ARITHMETIC_ROUNDING)
                report.check11_r4_percentage_cells_checked += 1
                if reconstructed == pct_val:
                    report.check11_r4_percentage_cells_matched += 1
                else:
                    report.add(Violation(
                        "demand_category", r, pct_field, pct_str,
                        "PERCENTAGE_BASE_RECONSTRUCTION_MISMATCH",
                        f"{ticker} row {r}: {pct_field} is {pct_str} but its own "
                        f"{nominal_field} ({own_nominal_str}) / the percentage base row's "
                        f"{nominal_field} ({base_nominal_str}, row {base_r}) x 100 reconstructs "
                        f"to {reconstructed} at this cell's own {precision} decimal place(s); "
                        f"gate-affecting, nothing corrected (calculation_mismatch_policy governs "
                        f"correction, never severity)"))


def check_arithmetic_consistency(offer_header: list[str], offer_rows: list[list[str]],
                                  report: Report) -> None:
    """Section 8 check 12 - arithmetic consistency, report-only.

    "Where #1/#2, #3 and #4 are all present, check demand_shares_* /
    shares_offered_denominator against total_demand_multiple_value at the
    source's stated precision, and report divergence without correcting
    anything (calculation_mismatch_policy = REPORT_ONLY_NO_AUTOMATIC_CORRECTION)."

    #1 (demand_shares_unfiltered), #2 (demand_shares_filtered) and #3
    (shares_offered_denominator) all carry a MANDATORY scope_tag (section 2.1);
    #4 (total_demand_multiple_value) does not - its scope_tag defaults to
    NOT_APPLICABLE "unless the source itself makes scope material" (section
    2.1). The matching rule below is deterministic and never guesses a
    magnitude, only which recorded rows form one triple:

      - a #1/#2 row is paired with a #3 row of the SAME scope_tag (they are
        the numerator/denominator of one division; pairing across scopes is
        not a division the source performed, so it is never attempted);
      - that pairing is compared against a #4 row of the same scope_tag if one
        exists, else the ticker's single #4 row if there is exactly one
        (the ordinary case - #4 is not scope-tagged by default), else the
        pairing is uncheckable (ambiguous which #4 value applies).

    Only field_status = VALUE_RECORDED rows are used. DATA_NOT_FOUND,
    SOURCES_CONFLICT and every other field_status make a row "not present" for
    this check - never guessed, never averaged (section 9 item 4) - and are
    counted, separately, in report.check12_uncheckable_breakdown; they are
    never reported as a divergence.
    """
    needed = ("batch_id", "ticker", "field_name", "scope_tag", "normalized_value", "field_status")
    col_index = {name: i for i, name in enumerate(offer_header)}
    if any(c not in col_index for c in needed):
        return

    def cell(row: list[str], name: str) -> str:
        idx = col_index.get(name)
        return row[idx] if idx is not None and idx < len(row) else ""

    groups: dict[tuple[str, str], list[tuple[int, list[str]]]] = {}
    for r, row in enumerate(offer_rows, start=1):
        if len(row) != len(offer_header):
            continue
        key = (cell(row, "batch_id"), cell(row, "ticker"))
        groups.setdefault(key, []).append((r, row))

    for (_batch_id, ticker), rows in groups.items():
        by_field: dict[str, list[tuple[int, list[str]]]] = {}
        for r, row in rows:
            by_field.setdefault(cell(row, "field_name"), []).append((r, row))
        denom_rows = by_field.get(SHARES_OFFERED_DENOMINATOR_FIELD, [])
        multiple_rows = by_field.get(TOTAL_DEMAND_MULTIPLE_FIELD, [])
        if not denom_rows or not multiple_rows:
            continue  # #3 and/or #4 not present at all for this ticker

        for numerator_field in DEMAND_SHARES_FIELDS:
            for num_r, num_row in by_field.get(numerator_field, []):
                num_scope = cell(num_row, "scope_tag")

                matching_denoms = [(r, row) for r, row in denom_rows
                                    if cell(row, "scope_tag") == num_scope]
                if len(matching_denoms) != 1:
                    _bump(report.check12_uncheckable_breakdown,
                          "no_unique_denominator_for_scope")
                    report.check12_uncheckable_pairs += 1
                    continue
                denom_r, denom_row = matching_denoms[0]

                scope_matched_multiples = [(r, row) for r, row in multiple_rows
                                            if cell(row, "scope_tag") == num_scope]
                if len(scope_matched_multiples) == 1:
                    mult_r, mult_row = scope_matched_multiples[0]
                elif not scope_matched_multiples and len(multiple_rows) == 1:
                    mult_r, mult_row = multiple_rows[0]
                else:
                    _bump(report.check12_uncheckable_breakdown,
                          "no_unique_total_demand_multiple_for_scope")
                    report.check12_uncheckable_pairs += 1
                    continue

                report.check12_pairs_evaluated += 1

                if not (cell(num_row, "field_status") == "VALUE_RECORDED"
                        and cell(denom_row, "field_status") == "VALUE_RECORDED"
                        and cell(mult_row, "field_status") == "VALUE_RECORDED"):
                    _bump(report.check12_uncheckable_breakdown, "non_value_recorded_status")
                    report.check12_uncheckable_pairs += 1
                    continue

                num_value = _parse_plain_decimal(cell(num_row, "normalized_value"))
                denom_value = _parse_plain_decimal(cell(denom_row, "normalized_value"))
                multiple_str = cell(mult_row, "normalized_value")
                multiple_value = _parse_plain_decimal(multiple_str)
                if num_value is None or denom_value is None or multiple_value is None:
                    _bump(report.check12_uncheckable_breakdown, "non_numeric_value")
                    report.check12_uncheckable_pairs += 1
                    continue
                if denom_value == 0:
                    _bump(report.check12_uncheckable_breakdown, "zero_denominator")
                    report.check12_uncheckable_pairs += 1
                    continue

                precision = _decimal_places(multiple_str)
                quantum = Decimal(1).scaleb(-precision)
                computed = (num_value / denom_value).quantize(quantum, rounding=ARITHMETIC_ROUNDING)
                if computed != multiple_value:
                    report.add(Violation(
                        "offer_level", num_r, "normalized_value",
                        cell(num_row, "normalized_value"),
                        "ARITHMETIC_CONSISTENCY_DIVERGENCE",
                        f"{ticker}: {numerator_field} / {SHARES_OFFERED_DENOMINATOR_FIELD} "
                        f"(scope_tag={num_scope}, row {denom_r}) = {computed} (rounded to "
                        f"{precision} decimal place(s), the precision {TOTAL_DEMAND_MULTIPLE_FIELD} "
                        f"is stated at in row {mult_r}) but the source publishes {multiple_str}; "
                        f"report-only, nothing corrected"))


def check_arithmetic_consistency_r3(offer_header: list[str], offer_rows: list[list[str]],
                                     report: Report) -> None:
    """Section 8 check 12, R3 text in full - filter-status-aware, replaces R2's
    check 12 in full (BORSAI_CHECK12_R3_IMPLEMENTATION_20260908_V1).

    check_arithmetic_consistency (R2, above) is left untouched and stays
    reachable via --check12-revision r2, so a batch already accepted under R2
    (B00_codex_r2, B01, B02) can still be re-checked against the rule that was
    actually in force when it was accepted. This function is the R3
    replacement and is the CLI default from this task onward, per R3.3.1: "R3
    applies to validation from B03 onward."

    Source: artifacts/governance/BORSAI_PRETRADE_EXTENSION_COLLECTION_SPEC_20260908_R3/
    PRETRADE_EXTENSION_COLLECTION_SPEC.md, section 8 item 12, Steps A-F.

    Step A (pairing) and Step C (comparison) are unchanged from R2: a #1/#2 row
    pairs with the #3 row of the same scope_tag; that pair compares against a
    #4 row of the same scope_tag if one exists, else the ticker's single #4
    row, else the pairing is uncheckable. The comparison quantizes to #4's own
    printed precision and requires exact equality - no tolerance, since R3's
    directional/limited-scope claim depends on it.

    Step B reads #5 (total_demand_filter_status) before comparing anything,
    and restricts the comparison to the numerator #5 designates:
      UNFILTERED       -> demand_shares_unfiltered compared, demand_shares_filtered
                          suppressed (NOT_APPLICABLE for this check - counted
                          under filter_status_excludes_numerator, never a pass,
                          never a divergence);
      FILTERED          -> the mirror image;
      NOT_SPECIFIED / DATA_NOT_FOUND -> undetermined, Step D;
      NOT_APPLICABLE    -> no numerator is designated at all, Step E.

    Step D (undetermined #5): both numerators are compared. If at least one
    compared pairing matches #4, a diverging pairing is
    ARITHMETIC_CONSISTENCY_UNDETERMINED_FILTER - report-only, names the
    matching numerator. If none match - including when only one numerator was
    recorded at all - it is ARITHMETIC_CONSISTENCY_DIVERGENCE, a violation.

    Step E (#5 = NOT_APPLICABLE, the C1 ruling): #4 VALUE_RECORDED is a
    contradiction - FILTER_STATUS_MULTIPLE_CONTRADICTION, a FAIL - the source
    cannot both publish no multiple and record one. #5 in {FILTERED,
    UNFILTERED} with #4 not VALUE_RECORDED is the same contradiction in mirror
    image, same rule code. Otherwise consistent: no triple exists, nothing to
    compare. (This is a new rule code, distinct from the pre-existing,
    out-of-scope check_c1's C1_VIOLATION, which this task does not touch.)

    Step F (designated numerator absent): where #5 designates a numerator
    whose row is not VALUE_RECORDED while the other numerator's row is,
    ARITHMETIC_CONSISTENCY_NOT_COMPARABLE - report-only, never a divergence,
    since the source's own designated numerator was never published and there
    is no comparable multiple for the other one to be checked against.

    REZERV (this task). Every real batch inspected while writing this function
    (B00, B00_codex, B00_codex_r2, B01, B02, B03) carries exactly one
    total_demand_filter_status row per ticker, and R3's text assumes this
    ("read the ticker's #5 row", singular) without defining a branch for zero
    or more than one such row. This function treats that structural case
    defensively as unresolved - the identical epistemic position Step D
    describes for an undetermined #5, neither designated nor excluded - and
    counts it separately under filter_status_row_not_unique, rather than
    guessing which row to trust (section 9 item 4). This is a structural
    safety net for an input shape R3's text does not address; it does not
    reinterpret the meaning of any of the five enum members, and every
    fixture/batch this task actually ran against has exactly one #5 row.
    """
    needed = ("batch_id", "ticker", "field_name", "scope_tag", "normalized_value", "field_status")
    col_index = {name: i for i, name in enumerate(offer_header)}
    if any(c not in col_index for c in needed):
        return

    def cell(row: list[str], name: str) -> str:
        idx = col_index.get(name)
        return row[idx] if idx is not None and idx < len(row) else ""

    groups: dict[tuple[str, str], list[tuple[int, list[str]]]] = {}
    for r, row in enumerate(offer_rows, start=1):
        if len(row) != len(offer_header):
            continue
        key = (cell(row, "batch_id"), cell(row, "ticker"))
        groups.setdefault(key, []).append((r, row))

    def evaluate_pairing(num_r: int, num_row: list[str],
                          denom_rows: list[tuple[int, list[str]]],
                          multiple_rows: list[tuple[int, list[str]]]):
        """Steps A and C, exactly as R2. Returns ("uncheckable", bucket_name)
        or ("computed", computed, multiple_value, multiple_str, precision,
        mult_r, denom_r)."""
        num_scope = cell(num_row, "scope_tag")
        matching_denoms = [(r, row) for r, row in denom_rows
                            if cell(row, "scope_tag") == num_scope]
        if len(matching_denoms) != 1:
            return ("uncheckable", "no_unique_denominator_for_scope")
        denom_r, denom_row = matching_denoms[0]

        scope_matched_multiples = [(r, row) for r, row in multiple_rows
                                    if cell(row, "scope_tag") == num_scope]
        if len(scope_matched_multiples) == 1:
            mult_r, mult_row = scope_matched_multiples[0]
        elif not scope_matched_multiples and len(multiple_rows) == 1:
            mult_r, mult_row = multiple_rows[0]
        else:
            return ("uncheckable", "no_unique_total_demand_multiple_for_scope")

        if not (cell(num_row, "field_status") == "VALUE_RECORDED"
                and cell(denom_row, "field_status") == "VALUE_RECORDED"
                and cell(mult_row, "field_status") == "VALUE_RECORDED"):
            return ("uncheckable", "non_value_recorded_status")

        num_value = _parse_plain_decimal(cell(num_row, "normalized_value"))
        denom_value = _parse_plain_decimal(cell(denom_row, "normalized_value"))
        multiple_str = cell(mult_row, "normalized_value")
        multiple_value = _parse_plain_decimal(multiple_str)
        if num_value is None or denom_value is None or multiple_value is None:
            return ("uncheckable", "non_numeric_value")
        if denom_value == 0:
            return ("uncheckable", "zero_denominator")

        precision = _decimal_places(multiple_str)
        quantum = Decimal(1).scaleb(-precision)
        computed = (num_value / denom_value).quantize(quantum, rounding=ARITHMETIC_ROUNDING)
        return ("computed", computed, multiple_value, multiple_str, precision, mult_r, denom_r)

    for (_batch_id, ticker), rows in groups.items():
        by_field: dict[str, list[tuple[int, list[str]]]] = {}
        for r, row in rows:
            by_field.setdefault(cell(row, "field_name"), []).append((r, row))

        denom_rows = by_field.get(SHARES_OFFERED_DENOMINATOR_FIELD, [])
        multiple_rows = by_field.get(TOTAL_DEMAND_MULTIPLE_FIELD, [])
        filter_rows = by_field.get(TOTAL_DEMAND_FILTER_STATUS_FIELD, [])

        has_recorded_multiple = any(cell(row, "field_status") == "VALUE_RECORDED"
                                     for _, row in multiple_rows)

        if len(filter_rows) == 1:
            filter_r, filter_row = filter_rows[0]
            filter_value = cell(filter_row, "normalized_value")
        else:
            # REZERV above: zero or more than one #5 row is a structural case
            # R3's text does not define a branch for. Treated as unresolved,
            # never guessed.
            filter_r, filter_row = filter_rows[0] if filter_rows else (0, None)
            filter_value = None
            _bump(report.check12_r3_uncheckable_breakdown, "filter_status_row_not_unique")

        report.check12_r3_ticker_filter_applications.append({
            "ticker": ticker,
            "total_demand_filter_status": (filter_value if filter_value is not None
                                            else f"AMBIGUOUS_ROW_COUNT({len(filter_rows)})"),
            "designated_numerator": FILTER_STATUS_TO_DESIGNATED_NUMERATOR.get(filter_value),
        })

        # Step E - the C1 contradiction gate. Applies only to NOT_APPLICABLE
        # and to {FILTERED, UNFILTERED}; NOT_SPECIFIED/DATA_NOT_FOUND assert
        # nothing about whether a multiple exists, so Step E does not apply
        # to them (falls through to the undetermined/Step D branch below).
        if filter_value == FILTER_STATUS_NOT_APPLICABLE:
            if has_recorded_multiple:
                report.add(Violation(
                    "offer_level", filter_r, "total_demand_filter_status", filter_value,
                    "FILTER_STATUS_MULTIPLE_CONTRADICTION",
                    f"{ticker}: total_demand_filter_status is NOT_APPLICABLE (per "
                    f"CLARIFICATION.md C1, no total demand multiple was published at all) but "
                    f"{TOTAL_DEMAND_MULTIPLE_FIELD} is VALUE_RECORDED; the two rows cannot both "
                    f"be right"))
            continue  # Step B table: "none - Step E applies"; no numerator designated.

        if filter_value in (FILTER_STATUS_UNFILTERED, FILTER_STATUS_FILTERED):
            if not has_recorded_multiple:
                report.add(Violation(
                    "offer_level", filter_r, "total_demand_filter_status", filter_value,
                    "FILTER_STATUS_MULTIPLE_CONTRADICTION",
                    f"{ticker}: total_demand_filter_status is {filter_value} (a filter status "
                    f"asserted about a total demand multiple) but "
                    f"{TOTAL_DEMAND_MULTIPLE_FIELD} is not VALUE_RECORDED; the two rows cannot "
                    f"both be right"))

            designated_field = FILTER_STATUS_TO_DESIGNATED_NUMERATOR[filter_value]
            other_field = next(f for f in DEMAND_SHARES_FIELDS if f != designated_field)

            # Step B gate: the other numerator is NOT_APPLICABLE for this
            # check - never compared, never passed, never failed.
            for _other_r, _other_row in by_field.get(other_field, []):
                _bump(report.check12_r3_uncheckable_breakdown, "filter_status_excludes_numerator")
                report.check12_r3_uncheckable_pairs += 1

            designated_rows = by_field.get(designated_field, [])
            designated_recorded = any(cell(row, "field_status") == "VALUE_RECORDED"
                                       for _, row in designated_rows)
            other_recorded = any(cell(row, "field_status") == "VALUE_RECORDED"
                                  for _, row in by_field.get(other_field, []))

            if not designated_recorded and other_recorded:
                # Step F.
                cite_r, cite_row = designated_rows[0] if designated_rows else (0, None)
                cite_val = cell(cite_row, "normalized_value") if cite_row is not None else ""
                report.warn(Warning_(
                    "offer_level", cite_r, "normalized_value", cite_val,
                    "ARITHMETIC_CONSISTENCY_NOT_COMPARABLE",
                    f"{ticker}: total_demand_filter_status designates {designated_field}, but "
                    f"its row is not VALUE_RECORDED while {other_field} is; the source's own "
                    f"designated numerator was never published, so there is no comparable "
                    f"multiple to check {other_field} against - report-only, never a divergence"))
                _bump(report.check12_r3_uncheckable_breakdown,
                      "designated_numerator_not_value_recorded")
                report.check12_r3_uncheckable_pairs += 1
                continue

            if not denom_rows or not multiple_rows:
                continue  # #3 and/or #4 not present at all for this ticker.

            for num_r, num_row in designated_rows:
                result = evaluate_pairing(num_r, num_row, denom_rows, multiple_rows)
                if result[0] == "uncheckable":
                    _bump(report.check12_r3_uncheckable_breakdown, result[1])
                    report.check12_r3_uncheckable_pairs += 1
                    continue
                _, computed, multiple_value, multiple_str, precision, mult_r, denom_r = result
                report.check12_r3_pairs_evaluated += 1
                if computed != multiple_value:
                    report.add(Violation(
                        "offer_level", num_r, "normalized_value",
                        cell(num_row, "normalized_value"),
                        "ARITHMETIC_CONSISTENCY_DIVERGENCE",
                        f"{ticker}: {designated_field} / {SHARES_OFFERED_DENOMINATOR_FIELD} "
                        f"(scope_tag={cell(num_row, 'scope_tag')}, row {denom_r}) = {computed} "
                        f"(rounded to {precision} decimal place(s), the precision "
                        f"{TOTAL_DEMAND_MULTIPLE_FIELD} is stated at in row {mult_r}) but the "
                        f"source publishes {multiple_str}; total_demand_filter_status="
                        f"{filter_value} designates this numerator - the source's own reading, "
                        f"gate-affecting, nothing corrected"))
            continue

        # Undetermined (NOT_SPECIFIED / DATA_NOT_FOUND / structurally ambiguous
        # #5) - Step D. Both numerators are compared.
        if not denom_rows or not multiple_rows:
            continue  # #3 and/or #4 not present at all for this ticker.

        candidates = []
        for numerator_field in DEMAND_SHARES_FIELDS:
            for num_r, num_row in by_field.get(numerator_field, []):
                result = evaluate_pairing(num_r, num_row, denom_rows, multiple_rows)
                if result[0] == "uncheckable":
                    _bump(report.check12_r3_uncheckable_breakdown, result[1])
                    report.check12_r3_uncheckable_pairs += 1
                    continue
                _, computed, multiple_value, multiple_str, precision, mult_r, denom_r = result
                report.check12_r3_pairs_evaluated += 1
                candidates.append({
                    "numerator_field": numerator_field, "num_r": num_r, "num_row": num_row,
                    "computed": computed, "multiple_str": multiple_str,
                    "denom_r": denom_r, "mult_r": mult_r,
                    "matched": computed == multiple_value,
                })

        if not candidates:
            continue

        any_match = any(c["matched"] for c in candidates)
        matching_fields = [c["numerator_field"] for c in candidates if c["matched"]]
        for c in candidates:
            if c["matched"]:
                continue
            if any_match:
                report.warn(Warning_(
                    "offer_level", c["num_r"], "normalized_value",
                    cell(c["num_row"], "normalized_value"),
                    "ARITHMETIC_CONSISTENCY_UNDETERMINED_FILTER",
                    f"{ticker}: total_demand_filter_status is {filter_value} (undetermined - "
                    f"which numerator produced the published multiple is unknown); "
                    f"{c['numerator_field']} / {SHARES_OFFERED_DENOMINATOR_FIELD} (row "
                    f"{c['denom_r']}) = {c['computed']} but the source publishes "
                    f"{c['multiple_str']} (row {c['mult_r']}), while {', '.join(matching_fields)} "
                    f"matches it exactly - the same definitional artefact Step B excludes where "
                    f"#5 is explicit; report-only, not gate-affecting"))
            else:
                report.add(Violation(
                    "offer_level", c["num_r"], "normalized_value",
                    cell(c["num_row"], "normalized_value"),
                    "ARITHMETIC_CONSISTENCY_DIVERGENCE",
                    f"{ticker}: total_demand_filter_status is {filter_value} (undetermined); "
                    f"{c['numerator_field']} / {SHARES_OFFERED_DENOMINATOR_FIELD} (row "
                    f"{c['denom_r']}) = {c['computed']} but the source publishes "
                    f"{c['multiple_str']} (row {c['mult_r']}), and no available reading of the "
                    f"source's own numerators matches it"))


def build_json_report(report: Report, canonical_immutability: dict | None = None,
                       outcome_firewall: dict | None = None,
                       manifest: dict | None = None,
                       check12_revision: str | None = None,
                       check11_revision: str | None = None) -> dict:
    by_rule: dict[str, int] = {}
    for v in report.violations:
        by_rule[v.rule_code] = by_rule.get(v.rule_code, 0) + 1
    payload = {
        "task_id": "BORSAI_BATCH_VALIDATOR_20260906_T2",
        "violation_count": len(report.violations),
        "violations_by_rule_code": by_rule,
        "violations": [v.to_dict() for v in report.violations],
        "warning_count": len(report.warnings),
        "warnings": [w.to_dict() for w in report.warnings],
        "multiple_undertakings": report.multiple_undertakings,
        "spec_enum_missing": sorted(report.spec_enum_missing),
        "exposure_counters": {
            "definition_revision": "BORSAI_SPEC_CLARIFY_20260906_T7",
            "affects_gate": False,
            "r4_category_rows_with_any_data_field_data_not_found": {
                "incl_order_count": report.r4_exposure_count,
                "excl_order_count": report.r4_exposure_count_excl_order_count,
            },
            "r5_category_rows_with_mixed_data_field_status": {
                "incl_order_count": report.r5_exposure_count,
                "excl_order_count": report.r5_exposure_count_excl_order_count,
            },
            "r4_closure_by_cell_status_register": {
                "register_supplied": report.register_seen,
                "data_not_found_cells_requiring_a_register_row": report.register_required_cells,
                "cells_with_exactly_one_register_row": report.register_covered_cells,
                "closure_rate": (round(report.register_covered_cells
                                       / float(report.register_required_cells), 4)
                                 if report.register_required_cells else None),
                "note": "R4 counts rows whose cells had nowhere to declare a search scope. "
                        "The section 5.6 register is what closes it; this is how much of the "
                        "exposure is actually closed in this batch.",
            },
        },
        "check_11_12_coverage": {
            "definition_revision": "BORSAI_R2_CONSISTENCY_CHECKS_20260906_T9C",
            "note": "A divergence found by check 11 or 12 IS a Violation above "
                    "(AGGREGATE_LEAF_DIVERGENCE / ARITHMETIC_CONSISTENCY_DIVERGENCE) and "
                    "affects the gate. These coverage counters are separate: they say how "
                    "much of the check's surface was actually computable, since a sentinel "
                    "or absent input on either side makes a comparison 'cannot be checked', "
                    "never 'passes' and never 'fails'.",
            "check_11_aggregate_leaf_guard": {
                "families_evaluated": report.check11_families_evaluated,
                "field_comparisons_uncheckable": report.check11_uncheckable_field_comparisons,
                "uncheckable_breakdown": report.check11_uncheckable_breakdown,
            },
            "check_12_arithmetic_consistency": {
                "pairs_evaluated": report.check12_pairs_evaluated,
                "pairs_uncheckable": report.check12_uncheckable_pairs,
                "uncheckable_breakdown": report.check12_uncheckable_breakdown,
            },
        },
        "check_7_conflict_integrity": {
            "definition_revision": "BORSAI_VALIDATOR_CHECK7_AND_COVERAGE_20260912_T19",
            "spec_section": "section 8 check 7",
            "note": "A found violation (CONFLICT_GROUP_ORPHAN or "
                    "CONFLICT_GROUP_UNMARKED_SIBLING) IS a Violation above and affects the "
                    "gate. 'checked'/'passed' describe rule 1's conflict_group_id-sharing "
                    "coverage only; 'violations' aggregates both rule 1 and rule 2 findings. "
                    "conflict_group_id = NOT_APPLICABLE rows never enter this check at all - "
                    "not checked, not uncheckable - and are reported separately under "
                    "out_of_scope. 'uncheckable' is empty: unlike checks 11/12/13(b), this "
                    "check has no row-level input that is knowable-but-not-yet-computable; "
                    "a row either carries a conflict-family field_status or it does not.",
            "checked": report.check7_checked,
            "uncheckable": {},
            "passed": report.check7_passed,
            "violations": report.check7_violations,
            "out_of_scope": {
                "conflict_group_not_applicable": report.check7_out_of_scope_not_applicable,
            },
            "denominator": {
                "definition_revision": "BORSAI_D1_POINT_IN_TIME_GATE_20260912_V1",
                "note": "checked=0 and out_of_scope=0 cannot otherwise be told apart from "
                        "'this file has 0 rows' - these three counters are the same rows "
                        "categorized by whether they carry a conflict-family field_status, "
                        "cumulative across every file check 7 runs on.",
                "rows_in_file": report.check7_rows_in_file,
                "rows_with_conflict_family_status": report.check7_rows_with_conflict_family_status,
                "rows_without_conflict_family_status": (
                    report.check7_rows_in_file - report.check7_rows_with_conflict_family_status),
            },
        },
        "r5_d1_point_in_time": {
            "definition_revision": "BORSAI_D1_POINT_IN_TIME_GATE_20260912_V1",
            "spec_section": "SPEC R5 §R5.1",
            "note": "Not one of section 8's 17 numbered checks - an audit of R5's own "
                    "binding rule. A found violation (POINT_IN_TIME_UNVERIFIED) IS a "
                    "Violation above and affects the gate. POINT_IN_TIME_UNVERIFIED is a "
                    "rule code only, never added to field_status or any other vocabulary "
                    "(§R5.1 item 4). 'checked'/'passed' apply only to KAP_COMPANY_RECORD "
                    "rows scope-tagged AS_OF_LISTING (the only ones needing a "
                    "first_trading_date comparison); AS_OF_RETRIEVAL rows are "
                    "unconditionally 'passed' with no comparison. 'uncheckable' is never "
                    "counted as passed. out_of_scope rows make no listing/retrieval claim "
                    "about a live source at all - not KAP_COMPANY_RECORD, or a "
                    "KAP_COMPANY_RECORD row scope-tagged something other than "
                    "AS_OF_LISTING/AS_OF_RETRIEVAL (NOT_APPLICABLE in practice).",
            "checked": report.d1_checked,
            "uncheckable": report.d1_uncheckable_breakdown,
            "passed": report.d1_passed,
            "violations": report.d1_violations,
            "out_of_scope": {
                "not_kap_company_record": report.d1_out_of_scope_not_kap_company_record,
                "kap_company_record_scope_tag_not_a_listing_or_retrieval_claim":
                    report.d1_out_of_scope_scope_tag_not_a_claim,
            },
        },
    }
    if check11_revision is not None:
        payload["check_11_revision"] = check11_revision
    if check11_revision == "r4":
        payload["check_11_12_coverage"]["check_11_percentage_base_reconstruction"] = {
            "definition_revision": "BORSAI_R4_IMPLEMENTATION_20260909_V1",
            "spec_section": "R4 §8.11 Branch B",
            "note": "check_11_aggregate_leaf_guard above is Branch A's own counters, reused "
                    "unchanged in name and meaning under r4 (scoped to the six additive fields "
                    "only - AGGREGATE_LEAF_ADDITIVE_FIELDS_R4). This block is Branch B's own "
                    "coverage: PERCENTAGE_BASE_RECONSTRUCTION_MISMATCH is a gate-affecting "
                    "violation above. base_cells reconstruct to 100 by construction and are "
                    "never counted as a check; an uncheckable cell is never a pass.",
            "cells_checked": report.check11_r4_percentage_cells_checked,
            "cells_matched": report.check11_r4_percentage_cells_matched,
            "base_cells": report.check11_r4_percentage_base_cells,
            "cells_uncheckable": report.check11_r4_percentage_cells_uncheckable,
            "uncheckable_breakdown": report.check11_r4_percentage_uncheckable_breakdown,
            "ticker_percentage_base_applications": report.check11_r4_percentage_base_applications,
        }
    if check12_revision is not None:
        payload["check_12_revision"] = check12_revision
    if check12_revision == "r3":
        payload["check_12_r3_arithmetic_consistency_filter_aware"] = {
            "definition_revision": "BORSAI_CHECK12_R3_IMPLEMENTATION_20260908_V1",
            "spec_section": "R3 §8.12",
            "note": "check_12_arithmetic_consistency above is R2's counters, untouched and "
                    "unused when this revision runs. This block is check 12's own coverage "
                    "under the R3, filter-status-aware definition: ARITHMETIC_CONSISTENCY_"
                    "DIVERGENCE and FILTER_STATUS_MULTIPLE_CONTRADICTION are gate-affecting "
                    "violations above; ARITHMETIC_CONSISTENCY_UNDETERMINED_FILTER and "
                    "ARITHMETIC_CONSISTENCY_NOT_COMPARABLE are report-only warnings above, "
                    "never gate-affecting.",
            "pairs_evaluated": report.check12_r3_pairs_evaluated,
            "pairs_uncheckable": report.check12_r3_uncheckable_pairs,
            "uncheckable_breakdown": report.check12_r3_uncheckable_breakdown,
            "ticker_filter_status_applications": report.check12_r3_ticker_filter_applications,
        }
    if canonical_immutability is not None:
        payload["canonical_immutability"] = canonical_immutability
    if outcome_firewall is not None:
        payload["outcome_firewall"] = outcome_firewall
        # BORSAI_VALIDATOR_CHECK7_AND_COVERAGE_20260912_T19: these were
        # previously merged under one misnamed top-level key,
        # REALIZED_OUTCOME_READS, conflating two different things: the count
        # of canonical first_trading_date values loaded for check 13(b)'s
        # date gate (schedule metadata, knowable pre-listing) and the count
        # of actual post-listing outcome values read (price/return/OHLCV),
        # which section 8 check 13 forbids this validator from ever doing.
        # Each now has its own, honestly-named key.
        payload["canonical_first_trading_dates_loaded"] = outcome_firewall.get(
            "canonical_first_trading_dates_loaded", 0)
        # Literal 0, not a measured count: this validator never reads any
        # post-listing outcome value (price/return/OHLCV/tavan/drawdown) -
        # section 8 check 13's own firewall forbids it structurally.
        payload["REALIZED_OUTCOME_READS"] = 0
    if manifest is not None:
        payload["manifest"] = manifest
    return payload


def print_human_summary(report: Report, canonical_immutability: dict | None = None,
                         outcome_firewall: dict | None = None,
                         manifest: dict | None = None) -> None:
    by_rule: dict[str, int] = {}
    for v in report.violations:
        by_rule[v.rule_code] = by_rule.get(v.rule_code, 0) + 1
    print("=== BORSAI batch validator summary ===")
    if not report.violations:
        print("No violations found.")
    else:
        print(f"Total violations: {len(report.violations)}")
        for code in sorted(by_rule):
            print(f"  {code}: {by_rule[code]}")
    if report.spec_enum_missing:
        print(f"SPEC_ENUM_MISSING (skipped, not scored): {sorted(report.spec_enum_missing)}")
    print("--- R4/R5 exposure counters (report only, do not affect gate) ---")
    print("  R4 = category rows where at least one of the 15 data fields is DATA_NOT_FOUND")
    print("       (no search_scope column exists in the category schema to declare it)")
    print(f"       incl order_count: {report.r4_exposure_count}"
          f"   excl order_count: {report.r4_exposure_count_excl_order_count}")
    print("  R5 = category rows whose 15 data fields are of mixed status (>=1 absent and")
    print("       >=1 real value), which one row-level field_status cannot express")
    print(f"       incl order_count: {report.r5_exposure_count}"
          f"   excl order_count: {report.r5_exposure_count_excl_order_count}")
    if report.multiple_undertakings:
        print("--- MULTIPLE_UNDERTAKINGS (informational, not a failure) ---")
        for item in report.multiple_undertakings:
            print(f"  {item['ticker']} / {item['field_name']}: "
                  f"{item['undertaking_count']} distinct undertakings")
    if report.warnings:
        print(f"--- WARNINGS ({len(report.warnings)}) — reported, never a violation, "
              f"no gate effect ---")
        for w in report.warnings:
            print(f"  {w.rule_code} row {w.row}: {w.message}")
    if report.register_required_cells or report.register_seen:
        covered, required = report.register_covered_cells, report.register_required_cells
        rate = f"{100.0 * covered / required:.1f}%" if required else "n/a"
        print("--- R4 closure via the cell-status register ---")
        print(f"  DATA_NOT_FOUND cells requiring a register row: {required}")
        print(f"  cells with exactly one register row:           {covered}  ({rate})")
    if report.check11_families_evaluated or report.check12_pairs_evaluated:
        print("--- Checks 11/12 coverage (divergences, if any, are Violations above) ---")
        print(f"  check 11 aggregate/leaf families evaluated: {report.check11_families_evaluated}"
              f"   field comparisons uncheckable: {report.check11_uncheckable_field_comparisons}"
              f"  {report.check11_uncheckable_breakdown}")
        print(f"  check 12 numerator/denominator/multiple triples evaluated: "
              f"{report.check12_pairs_evaluated}"
              f"   uncheckable: {report.check12_uncheckable_pairs}"
              f"  {report.check12_uncheckable_breakdown}")
    if canonical_immutability is not None:
        mismatches = [f for f in canonical_immutability["files"] if f["status"] != "MATCH"]
        print("--- Check 9: canonical immutability ---")
        print(f"  historical99 canonical files checked: "
              f"{canonical_immutability['historical99_canonical_files_checked']}"
              f"  (registry: {canonical_immutability['historical99_canonical_registry_source']})")
        print(f"  config schema TOMLs checked: {canonical_immutability['config_schema_files_checked']}"
              f"  (baseline generated this run: "
              f"{canonical_immutability['config_schema_baseline_generated_this_run']})")
        if mismatches:
            print(f"  HARD STOP: {len(mismatches)} file(s) changed - {mismatches}")
    if outcome_firewall is not None:
        print("--- Check 13: outcome firewall ---")
        print(f"  canonical_first_trading_dates_loaded: "
              f"{outcome_firewall['canonical_first_trading_dates_loaded']}"
              f"  (source: {outcome_firewall['canonical_first_trading_date_source']})")
        print("  REALIZED_OUTCOME_READS: 0")
        dgc = outcome_firewall.get("date_gate_coverage")
        if dgc is not None:
            print(f"  check 13(b) date gate rows checked: {dgc['rows_checked']}"
                  f"   violations: {dgc['violations']}"
                  f"   passed: {dgc['passed']}"
                  f"   uncheckable: {dgc['rows_uncheckable']}"
                  f"  {dgc['uncheckable_breakdown']}")
    if report.check7_checked or report.check7_out_of_scope_not_applicable or report.check7_rows_in_file:
        print("--- Check 7: conflict integrity (violations, if any, are Violations above) ---")
        print(f"  checked: {report.check7_checked}"
              f"   passed: {report.check7_passed}"
              f"   violations: {report.check7_violations}"
              f"   out_of_scope (conflict_group_id=NOT_APPLICABLE): "
              f"{report.check7_out_of_scope_not_applicable}")
        print(f"  denominator: rows_in_file={report.check7_rows_in_file}"
              f"   rows_with_conflict_family_status={report.check7_rows_with_conflict_family_status}"
              f"   rows_without_conflict_family_status="
              f"{report.check7_rows_in_file - report.check7_rows_with_conflict_family_status}")
    if (report.d1_checked or report.d1_passed or report.d1_violations
            or report.d1_out_of_scope_not_kap_company_record
            or report.d1_out_of_scope_scope_tag_not_a_claim):
        print("--- SPEC R5 §R5.1 (D1): point-in-time source constraint "
              "(not one of the 17 numbered checks; violations above) ---")
        print(f"  checked: {report.d1_checked}"
              f"   passed: {report.d1_passed}"
              f"   violations: {report.d1_violations}"
              f"   uncheckable: {report.d1_uncheckable}  {report.d1_uncheckable_breakdown}")
        print(f"  out_of_scope: not_kap_company_record="
              f"{report.d1_out_of_scope_not_kap_company_record}"
              f"   scope_tag_not_a_listing_or_retrieval_claim="
              f"{report.d1_out_of_scope_scope_tag_not_a_claim}")
    if manifest is not None:
        print("--- Check 14: manifest ---")
        for key, entry in manifest.items():
            print(f"  {key}: {entry['row_count']} rows, sha256={entry['sha256']}")
    verdict = "FAIL" if report.violations else "PASS"
    print(f"RESULT: {verdict}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BORSAI pretrade-extension batch self-consistency validator")
    parser.add_argument("--offer", required=True, help="path to the offer-level CSV")
    parser.add_argument("--category", required=True, help="path to the demand-category CSV")
    parser.add_argument("--spec-json", required=True, action="append",
                        help="path to a PRETRADE_EXTENSION_COLLECTION_SPEC.json. Repeat it to "
                             "load more than one revision; rows are routed to the revision "
                             "their spec_version names (section 7.4 item 4).")
    parser.add_argument("--cell-status", help="path to the section 5.6 demand-category "
                                              "cell-status register CSV (R2 deliveries only; "
                                              "an R1 delivery has no third file)")
    parser.add_argument("--check12-revision", choices=("r2", "r3"), default="r3",
                        help="which section 8 check 12 definition to run: r3 (default) is the "
                             "filter-status-aware replacement in force per R3.3.1 'R3 applies to "
                             "validation from B03 onward'; r2 reruns the original, unmodified "
                             "definition, for re-checking a batch (B00_codex_r2/B01/B02) against "
                             "the rule actually in force when it was accepted. This is a "
                             "per-invocation choice, not a per-row one: unlike spec_version "
                             "(section 7.4 item 4), R3 changed no schema and no spec_version "
                             "string (R3.2), so there is no row-level signal to route on - which "
                             "check-12 definition applies is a property of which revision is "
                             "validating the batch, decided by the caller.")
    parser.add_argument("--check11-revision", choices=("r2r3", "r4"), default="r4",
                        help="which section 8 check 11 definition to run: r4 (default) is the "
                             "percentage-base-reconstruction replacement of "
                             "BORSAI_R4_IMPLEMENTATION_20260909_V1 - Branch A (six additive "
                             "fields) unchanged from R2/R3, Branch B (three percentage fields) "
                             "reconstructed per-cell from its own nominal and the ticker's "
                             "percentage base row, never from a family sum of printed leaves; "
                             "r2r3 reruns the original, unmodified nine-field family-sum "
                             "definition, for re-checking a batch against the rule actually in "
                             "force when it was accepted. Mirrors --check12-revision's "
                             "already-established r2/r3 pattern: this is a per-invocation "
                             "choice, not a per-row one - R4 changed no schema and no "
                             "spec_version string, so there is no row-level signal to route on.")
    parser.add_argument("--out", required=True, help="path to write the machine-readable JSON report")
    args = parser.parse_args(argv)

    try:
        specs = [load_spec(path) for path in args.spec_json]
        registry = build_spec_registry(specs)
    except SpecLoadError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    spec = specs[0]

    report = Report()
    repo_root = _repo_root()

    # Section 8 check 9 - runs unconditionally, independent of whether the
    # batch CSVs themselves are readable, since it verifies repo-wide state
    # rather than anything about this batch.
    canonical_immutability = check_canonical_immutability(report, repo_root)

    # Section 8 check 13(b) support - discovered once per run, never hardcoded.
    ftd_path, ftd_header, ftd_candidates = discover_historical99_first_trading_date_source(repo_root)
    canonical_dates: dict[str, str] = {}
    ftd_source_rel = None
    if ftd_path is not None:
        canonical_dates = load_canonical_first_trading_dates(ftd_path, ftd_header)
        ftd_source_rel = str(ftd_path.relative_to(repo_root))
    else:
        report.warn(Warning_("outcome_firewall", 0, "<repo>", "",
                              "OUTCOME_FIREWALL_DATE_GATE_SOURCE_NOT_FOUND",
                              "no canonical ticker/first_trading_date source was found under "
                              "artifacts/outcomes/historical99/**/; the date gate (section 8 "
                              "check 13b) could not run this batch"))

    try:
        offer_rows = validate_offer_csv(args.offer, spec, report, registry, canonical_dates)
        with open(args.offer, "rb") as fh:
            offer_raw = fh.read()
        offer_header = parse_csv_rows(offer_raw.decode("utf-8-sig"))[0] if offer_raw else []

        category_rows = validate_category_csv(args.category, spec, report, registry, canonical_dates)
        with open(args.category, "rb") as fh:
            category_raw = fh.read()
        category_header = parse_csv_rows(category_raw.decode("utf-8-sig"))[0] if category_raw else []

        register_header, register_rows = [], []
        if args.cell_status:
            report.register_seen = True
            register_header, register_rows = validate_register_csv(
                args.cell_status, spec, report, registry, canonical_dates)

        check_cross_file(offer_rows, offer_header, category_rows, category_header, report)
        check_register_completeness(category_rows, category_header, register_header,
                                     register_rows, registry, spec, report)
        check_duplicates(offer_header, offer_rows, category_header, category_rows,
                          register_header, register_rows, registry, report)
        if args.check11_revision == "r4":
            check_aggregate_leaf_guard(category_header, category_rows, report,
                                        fields=AGGREGATE_LEAF_ADDITIVE_FIELDS_R4)
            check_percentage_base_reconstruction(category_header, category_rows, report)
        else:
            check_aggregate_leaf_guard(category_header, category_rows, report)
        if args.check12_revision == "r3":
            check_arithmetic_consistency_r3(offer_header, offer_rows, report)
        else:
            check_arithmetic_consistency(offer_header, offer_rows, report)

        manifest = build_manifest_block(args, offer_rows, category_rows, register_rows)
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        print(f"BLOCKED: cannot read input CSV: {exc}", file=sys.stderr)
        return 2

    outcome_firewall = {
        "canonical_first_trading_date_source": ftd_source_rel,
        "canonical_first_trading_date_candidates_considered": ftd_candidates,
        "canonical_first_trading_dates_loaded": len(canonical_dates),
        "date_gate_coverage": {
            "definition_revision": "BORSAI_CHECK13_UNCHECKABLE_AND_B05_20260911_V1",
            "spec_section": "section 8 check 13(b)",
            "note": "A found violation (OUTCOME_FIREWALL_DATE_GATE) IS a Violation above "
                    "and affects the gate. rows_checked/rows_uncheckable are separate: an "
                    "uncheckable row (sentinel/malformed source_publication_date, or a "
                    "ticker with no canonical first_trading_date anchor yet) is never "
                    "counted as a pass and never as a fail - only as uncheckable, same "
                    "rule as checks 11/12.",
            "rows_checked": report.check13_date_gate_rows_checked,
            "violations": report.check13_date_gate_violations,
            "passed": report.check13_date_gate_rows_checked - report.check13_date_gate_violations,
            "rows_uncheckable": report.check13_date_gate_uncheckable_rows,
            "uncheckable_breakdown": report.check13_date_gate_uncheckable_breakdown,
        },
    }

    payload = build_json_report(report, canonical_immutability=canonical_immutability,
                                 outcome_firewall=outcome_firewall, manifest=manifest,
                                 check12_revision=args.check12_revision,
                                 check11_revision=args.check11_revision)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    print_human_summary(report, canonical_immutability=canonical_immutability,
                        outcome_firewall=outcome_firewall, manifest=manifest)
    return 1 if report.violations else 0


if __name__ == "__main__":
    raise SystemExit(main())

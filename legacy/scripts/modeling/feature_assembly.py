"""Part B — raw V1_CORE_4 pre-trade feature assembly with eligibility gating.

Only the frozen substantive features f1-f4 are assembled here (f5, the
missingness indicator for f3, is a fold-internal preprocessing artifact, not a
raw sourced field — see preprocessing.py). This module produces a RAW feature
table only; transformed/standardized fold matrices are built separately in
preprocessing.py and must never be conflated with this raw table.

Eligibility gate (V1.1 spec `feature_eligibility` + preregistration §3):
  source_publication_date <= prediction_cutoff_date
  AND available_before_first_trade == TRUE
  AND officially sourced (OFFICIAL_VERIFIED)
  AND not derived from any post-first-trade value (structural, by construction)

f1 (ipo_size_tl), f2 (free_float_pct), f4 (capital_increase_pct_of_offer) are
CALCULATED fields in the canonical master (0 source-reported, 20 calculated
per pretrade_feature_availability_20.csv) with no individual provenance row of
their own in the consolidated provenance file. Their eligibility is therefore
derived from their underlying structural offer-term constituents, which DO
have per-field provenance in the batch provenance files. This derivation is
recorded explicitly (never silently assumed) via `derivation_note`.

f3 (total_demand_multiple) has a direct provenance row in the consolidated
provenance file and is used as-is.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
from decimal import Decimal
from pathlib import Path
from typing import Optional

from . import common

# Canonical verification_status enum (config/ipo_master_schema.toml `verification_statuses`):
#   OFFICIAL_VERIFIED, AUTHORIZED_INTERMEDIARY_VERIFIED, SECONDARY_VERIFIED,
#   DATA_NOT_FOUND, SOURCE_CONFLICT
# V1.1's official_source_hierarchy (SPK/KAP/BORSA_ISTANBUL/MKK/CONSORTIUM) is
# AGENTS.md source-priority tiers 1-5; AUTHORIZED_INTERMEDIARY_VERIFIED is the
# verification status recorded for tier-5 (consortium / yetkili aracı kurum)
# evidence, so it is eligible. SECONDARY_VERIFIED corresponds to tier 6
# ("güvenilir ikincil kaynak"), which the hierarchy explicitly excludes, and
# remains ineligible, as do DATA_NOT_FOUND and SOURCE_CONFLICT.
ELIGIBLE_VERIFICATION_STATUSES = ("OFFICIAL_VERIFIED", "AUTHORIZED_INTERMEDIARY_VERIFIED")

FEATURE_FIELDS = ["f1", "f2", "f3", "f4"]
SOURCE_FIELD = {
    "f1": "ipo_size_tl",
    "f2": "free_float_pct",
    "f3": "total_demand_multiple",
    "f4": "capital_increase_pct_of_offer",
}
# Underlying structural constituents whose provenance governs eligibility of a
# calculated field. Derived once, documented here, never invented per-row.
CALCULATED_FIELD_CONSTITUENTS = {
    "f1": ("shares_offered", "ipo_price"),
    "f2": ("capital_increase_shares", "existing_share_sale", "post_ipo_share_capital"),
    "f4": ("capital_increase_shares", "shares_offered"),
}

RAW_FEATURE_FIELDS = [
    "ticker", "feature_id", "source_field", "first_trading_date", "prediction_cutoff_date",
    "raw_value_exact", "eligible", "eligibility_reason", "source_publication_date",
    "available_before_first_trade", "verification_status", "derivation_note",
    "total_demand_filter_status",
]


@dataclass(frozen=True)
class RawFeatureRecord:
    ticker: str
    feature_id: str
    source_field: str
    first_trading_date: str
    prediction_cutoff_date: str
    raw_value_exact: Optional[str]
    eligible: bool
    eligibility_reason: str
    source_publication_date: Optional[str]
    available_before_first_trade: Optional[str]
    verification_status: Optional[str]
    derivation_note: str
    total_demand_filter_status: Optional[str] = None

    def as_csv_row(self) -> dict:
        row = asdict(self)
        row["eligible"] = "TRUE" if self.eligible else "FALSE"
        return row


def _index_provenance(rows: list[dict]) -> dict[tuple[str, str], dict]:
    index: dict[tuple[str, str], dict] = {}
    for row in rows:
        index[(row["ticker"], row["field_name"])] = row
    return index


def _direct_provenance_eligibility(prow: Optional[dict], cutoff: str) -> tuple[bool, str, Optional[str], Optional[str], Optional[str]]:
    if prow is None:
        return False, "NO_PROVENANCE_ROW_FOUND", None, None, None
    pub_date = prow.get("source_publication_date")
    avail = prow.get("available_before_first_trade")
    verified = prow.get("verification_status")
    if verified not in ELIGIBLE_VERIFICATION_STATUSES:
        return False, f"VERIFICATION_STATUS_{verified}", pub_date, avail, verified
    if avail != "TRUE":
        return False, f"AVAILABLE_BEFORE_FIRST_TRADE_{avail}", pub_date, avail, verified
    if not pub_date or pub_date > cutoff:
        return False, f"PUBLICATION_DATE_AFTER_CUTOFF({pub_date}>{cutoff})", pub_date, avail, verified
    return True, "ELIGIBLE", pub_date, avail, verified


def _combined_verification_label(statuses: list[str]) -> str:
    distinct = sorted(set(statuses))
    return distinct[0] if len(distinct) == 1 else f"MIXED({'+'.join(distinct)})"


def _calculated_field_eligibility(ticker: str, constituents: tuple[str, ...], batch_index: dict[tuple[str, str], dict], cutoff: str):
    dates: list[str] = []
    statuses: list[str] = []
    all_available = True
    all_verified = True
    missing_constituents: list[str] = []
    for field in constituents:
        row = batch_index.get((ticker, field))
        if row is None:
            missing_constituents.append(field)
            continue
        dates.append(row.get("source_publication_date") or "")
        statuses.append(row.get("verification_status") or "UNKNOWN")
        if row.get("available_before_first_trade") != "TRUE":
            all_available = False
        if row.get("verification_status") not in ELIGIBLE_VERIFICATION_STATUSES:
            all_verified = False
    if missing_constituents:
        return False, f"MISSING_CONSTITUENT_PROVENANCE({','.join(missing_constituents)})", None, None, None
    max_date = max(dates) if dates else None
    verified_label = _combined_verification_label(statuses)
    if not all_verified:
        return False, "CONSTITUENT_NOT_OFFICIAL_VERIFIED", max_date, str(all_available).upper(), verified_label
    if not all_available:
        return False, "CONSTITUENT_NOT_AVAILABLE_BEFORE_FIRST_TRADE", max_date, "FALSE", verified_label
    if not max_date or max_date > cutoff:
        return False, f"PUBLICATION_DATE_AFTER_CUTOFF({max_date}>{cutoff})", max_date, "TRUE", verified_label
    return True, "ELIGIBLE_DERIVED_FROM_CONSTITUENTS", max_date, "TRUE", verified_label


def assemble_raw_features() -> list[RawFeatureRecord]:
    universe = common.load_universe()
    master_rows = {row["ticker"]: row for row in common.load_master_rows()}
    consolidated_index = _index_provenance(common.load_consolidated_provenance_rows())
    batch_index = _index_provenance(common.load_batch_provenance_rows())

    records: list[RawFeatureRecord] = []
    for ticker in sorted(universe):
        master = universe[ticker]
        cutoff = common.prediction_cutoff_date(master.first_trading_date)
        master_row = master_rows[ticker]

        for feature_id in FEATURE_FIELDS:
            source_field = SOURCE_FIELD[feature_id]
            raw_value = common.parse_exact_decimal(master_row.get(source_field))

            if feature_id == "f3":
                prow = consolidated_index.get((ticker, source_field))
                filter_status_row = consolidated_index.get((ticker, "total_demand_filter_status"))
                total_demand_filter_status = filter_status_row["normalized_value"] if filter_status_row else master_row.get("total_demand_filter_status")
                if raw_value is None:
                    records.append(RawFeatureRecord(
                        ticker=ticker, feature_id=feature_id, source_field=source_field,
                        first_trading_date=master.first_trading_date, prediction_cutoff_date=cutoff,
                        raw_value_exact=None, eligible=False, eligibility_reason="NO_VALUE_DATA_NOT_FOUND",
                        source_publication_date=None, available_before_first_trade=None, verification_status=None,
                        derivation_note="DIRECT_PROVENANCE_LOOKUP",
                        total_demand_filter_status=total_demand_filter_status,
                    ))
                    continue
                eligible, reason, pub_date, avail, verified = _direct_provenance_eligibility(prow, cutoff)
                records.append(RawFeatureRecord(
                    ticker=ticker, feature_id=feature_id, source_field=source_field,
                    first_trading_date=master.first_trading_date, prediction_cutoff_date=cutoff,
                    raw_value_exact=str(raw_value), eligible=eligible, eligibility_reason=reason,
                    source_publication_date=pub_date, available_before_first_trade=avail, verification_status=verified,
                    derivation_note="DIRECT_PROVENANCE_LOOKUP",
                    total_demand_filter_status=total_demand_filter_status,
                ))
                continue

            # f1, f2, f4: calculated fields, eligibility derived from constituents
            constituents = CALCULATED_FIELD_CONSTITUENTS[feature_id]
            eligible, reason, pub_date, avail, verified = _calculated_field_eligibility(ticker, constituents, batch_index, cutoff)
            records.append(RawFeatureRecord(
                ticker=ticker, feature_id=feature_id, source_field=source_field,
                first_trading_date=master.first_trading_date, prediction_cutoff_date=cutoff,
                raw_value_exact=str(raw_value) if raw_value is not None else None,
                eligible=eligible, eligibility_reason=reason,
                source_publication_date=pub_date, available_before_first_trade=avail, verification_status=verified,
                derivation_note=f"DERIVED_FROM_CONSTITUENTS({'+'.join(constituents)})",
            ))
    return records


def write_raw_feature_csv(records: list[RawFeatureRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=RAW_FEATURE_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(record.as_csv_row())


def as_feature_matrix(records: list[RawFeatureRecord]) -> dict[str, dict[str, Optional[Decimal]]]:
    """ticker -> {feature_id -> Decimal value or None (ineligible/missing)}.

    Ineligible values are treated identically to missing values downstream —
    an ineligible feature must never leak into the model even if a raw value
    technically exists in the master CSV.
    """
    matrix: dict[str, dict[str, Optional[Decimal]]] = {}
    for record in records:
        matrix.setdefault(record.ticker, {})
        if record.eligible and record.raw_value_exact is not None:
            matrix[record.ticker][record.feature_id] = Decimal(record.raw_value_exact)
        else:
            matrix[record.ticker][record.feature_id] = None
    return matrix


def total_demand_filter_status_map(records: list[RawFeatureRecord]) -> dict[str, Optional[str]]:
    return {r.ticker: r.total_demand_filter_status for r in records if r.feature_id == "f3"}

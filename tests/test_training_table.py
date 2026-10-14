"""Data acceptance test for data/training_table.csv.

Expected counts come from the independent audit (docs: AUDIT.md §1.1, §1.2-f,
§3 "veri kabul testi"). The test reads the raw sources itself and never
imports the builder, so a builder bug cannot hide from it.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "training_table.csv"
VERSION = ROOT / "data" / "data_version.json"
RAW = ROOT / "data" / "raw"
TARGETS = RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv"
SESSIONS = RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv"

HORIZONS = ("D1", "D3", "D5", "D10")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def rows() -> list[dict[str, str]]:
    return read_csv(TABLE)


@pytest.fixture(scope="module")
def by_ticker(rows) -> dict[str, dict[str, str]]:
    return {r["ticker"]: r for r in rows}


def test_99_rows_unique_tickers(rows):
    assert len(rows) == 99
    assert len({r["ticker"] for r in rows}) == 99


def test_point_in_time_status(rows):
    assert Counter(r["point_in_time_status"] for r in rows) == {"UNKNOWN": 79, "PASS": 20}


def test_396_targets_decimal_equal_to_targets_csv(by_ticker):
    targets = read_csv(TARGETS)
    assert len(targets) == 396
    compared = 0
    for t in targets:
        row = by_ticker[t["ticker"]]
        assert Decimal(row[f"R_{t['horizon']}"]) == Decimal(t["target_return"]), (t["ticker"], t["horizon"])
        assert row[f"Y_{t['horizon']}"] == t["above_ipo_flag"], (t["ticker"], t["horizon"])
        compared += 1
    assert compared == 396
    assert {(t["ticker"], t["horizon"]) for t in targets} == {(tk, h) for tk in by_ticker for h in HORIZONS}


def test_total_demand_multiple_filled_97_missing_albtn_endae(rows):
    filled = [r for r in rows if r["total_demand_multiple"] != ""]
    assert len(filled) == 97
    assert {r["ticker"] for r in rows if r["total_demand_multiple"] == ""} == {"ALBTN", "ENDAE"}
    for r in filled:
        assert Decimal(r["total_demand_multiple"]) > 0


def test_additional_sale_filled_95_zero_89_positive_6(rows):
    filled = [Decimal(r["additional_sale_shares"]) for r in rows if r["additional_sale_shares"] != ""]
    assert len(filled) == 95
    assert sum(v == 0 for v in filled) == 89
    assert sum(v > 0 for v in filled) == 6


def test_capital_increase_shares_filled_99(rows):
    assert sum(r["capital_increase_shares"] != "" for r in rows) == 99


def test_ceiling_close_counts(rows):
    counts = {h: sum(r[f"ceiling_close_D{h}"] == "1" for r in rows) for h in (1, 3, 5, 10)}
    assert counts == {1: 81, 3: 67, 5: 48, 10: 25}


def test_ceiling_streak_counts_and_distribution(rows):
    streaks = [int(r["ceiling_streak_L"]) for r in rows]
    assert {k: sum(s >= k for s in streaks) for k in (1, 3, 5, 10)} == {1: 81, 3: 66, 5: 41, 10: 14}
    assert dict(Counter(streaks)) == {0: 18, 1: 11, 2: 4, 3: 13, 4: 12, 5: 8, 6: 6, 7: 6, 8: 4, 9: 3, 10: 14}


def test_ceiling_labels_recomputed_from_official_sessions(by_ticker):
    """close == upper_limit as Decimals, per session, from the THB/THM-derived source."""
    sessions = defaultdict(dict)
    for s in read_csv(SESSIONS):
        sessions[s["ticker"]][int(s["session_number"])] = s
    assert set(sessions) == set(by_ticker)
    for tk, row in by_ticker.items():
        assert sorted(sessions[tk]) == list(range(1, 11))
        flags = [Decimal(sessions[tk][k]["close"]) == Decimal(sessions[tk][k]["upper_limit"]) for k in range(1, 11)]
        assert [row[f"ceiling_close_D{k}"] for k in range(1, 11)] == ["1" if f else "0" for f in flags], tk
        streak = next((i for i, f in enumerate(flags) if not f), 10)
        assert int(row["ceiling_streak_L"]) == streak, tk


def test_data_version_matches_table_and_sources():
    version = json.loads(VERSION.read_text(encoding="utf-8"))
    assert version["sha256"] == hashlib.sha256(TABLE.read_bytes()).hexdigest()
    assert version["row_count"] == 99
    with TABLE.open("r", encoding="utf-8", newline="") as fh:
        header = next(csv.reader(fh))
    assert version["columns"] == header
    for src in version["sources"]:
        assert hashlib.sha256((ROOT / src["path"]).read_bytes()).hexdigest() == src["sha256"], src["path"]

"""SPEC_MARKET20_V0 §4 (Faz 2A): 2026-08-19 sonrası XU100 ve takvim uzatması.
Eski 9682 kaydın birebir örtüşmesi, yalnız XU100, takvim ↔ XU100 gün kümesi çapraz denetimi."""
from __future__ import annotations

import csv
import json
from dataclasses import replace
from decimal import Decimal

import pytest

from borsai import market20 as m20
from borsai.provenance import ROOT, sha256_file

NEW_PATH, NEW_SHA = m20.XU100_PINNED[-1]
URL = "https://www.borsaistanbul.com/graphic.php?veriTuru=endeks-graphic&indexCode=XU100"


@pytest.fixture(scope="module")
def old():
    return m20.load_xu100()[0]


@pytest.fixture(scope="module")
def new():
    return m20.load_xu100(NEW_PATH, NEW_SHA)[0]


def test_new_file_pinned_raw_and_same_format_as_old(new):
    assert NEW_PATH.relative_to(ROOT).as_posix() == "data/raw/xu100/xu100_graphic_20260922.json"
    assert sha256_file(NEW_PATH) == NEW_SHA
    raw_new = json.loads(NEW_PATH.read_text(encoding="utf-8"), parse_float=Decimal)
    raw_old = json.loads(m20.XU100_PATH.read_text(encoding="utf-8"), parse_float=Decimal)
    assert set(raw_new) == set(raw_old) == {"status", "source", "data"}
    assert {tuple(sorted(r)) for r in raw_new["data"]} == {("clval", "hisTs", "indexName")}
    assert {r.index_name for r in new} == {"XU100"}  # XHARZ vb. yok (kural 6, §4-c)


def test_old_9682_records_overlap_exactly(old, new):
    assert len(old) == 9682 and len(new) == 9705
    m20.check_revision(old, new)  # DUR koşulu yok
    oc, nc = m20.closes_by_date(old), m20.closes_by_date(new)
    assert all(nc[d] == v for d, v in oc.items())
    added = sorted(set(nc) - set(oc))
    assert (len(added), added[0], added[-1]) == (23, "2026-08-20", "2026-09-21")


def test_revision_check_detects_change(old, new):
    tampered = [replace(r, close=r.close + 1) if r.date == "2026-08-19" else r for r in new]
    with pytest.raises(m20.Market20IntegrityError):
        m20.check_revision(old, tampered)


def test_latest_loader_runs_revision_chain(new):
    records, sha = m20.load_xu100_latest()
    assert sha == NEW_SHA and len(records) == len(new)


def test_calendar_extension_matches_official_holidays_and_xu100(new):
    base = m20.load_calendar_b()
    assert base.last_date == "2026-08-19"  # H99 takvimi değişmedi
    cal = m20.load_calendar_b_extended()
    assert cal.days[: len(base.days)] == base.days and cal.last_date == "2026-12-31"
    with m20.CALENDAR_B_EXT_PATH.open(encoding="utf-8", newline="") as fh:
        rows = {r["calendar_date"]: r for r in csv.DictReader(fh)}
    assert list(rows)[0] == "2026-08-20" and len(rows) == 134
    assert rows["2026-08-30"]["full_closure"] == "YES" and rows["2026-10-29"]["counts_as_official_session"] == "NO"
    assert rows["2026-10-28"]["half_day"] == "YES" and rows["2026-10-28"]["counts_as_official_session"] == "YES"
    assert {r["source_pdf_sha256"] for r in rows.values()} == {"e45fa97e2f67d85b3571ce9e6c4758292a57379c2216fc88183f32504584e680"}
    m20.check_calendar_vs_xu100(cal, new, "2026-08-20", "2026-09-21")
    with pytest.raises(m20.Market20IntegrityError):
        m20.check_calendar_vs_xu100(cal, [r for r in new if r.date != "2026-09-01"], "2026-08-20", "2026-09-21")


def test_live_f6_for_registry_ipos():
    calendar, records, sha = m20.load_live_sources()
    for t, s0 in {"2026-08-18": "2026-08-17", "2026-08-21": "2026-08-20", "2026-09-01": "2026-08-31",
                  "2026-09-02": "2026-09-01", "2026-09-17": "2026-09-16"}.items():
        r = m20.market20(t, calendar, records, xu100_sha256=sha)
        assert r.refusal is None and r.S0_date == s0 and r.S0_date < r.ref_date
        # as_of: T ve sonrası okunmaz
        spoiled = records + [m20.XU100Record(date=t, index_name="XU100", close=Decimal("1e9"))]
        assert m20.market20(t, calendar, spoiled, xu100_sha256=sha).f6 == r.f6
    # takvim bittikten sonra RET (2027 için yeni duyuru gerekir)
    assert m20.market20("2027-01-05", calendar, records).refusal == m20.CALENDAR_NOT_COVERING

"""registry/ipos.csv (SPEC_SCORING §4, §10-7): şema, bilinen 7 arz, FROZEN olmayan satırda neden,
append-only, resmi 'işlem görmeye başlama' taramasıyla tamlık."""
from __future__ import annotations

import csv
import json

import pytest

from borsai import registry as reg
from borsai.provenance import ROOT

ENUM = json.loads((ROOT / "registry" / "source_docs" / "_ENUMERATION" / "ENUMERATION.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ipos():
    return reg.read_ipos()


def test_schema_and_values(ipos):
    header, rows = ipos
    assert tuple(header) == reg.IPOS_COLUMNS
    assert reg.validate_ipos(header, rows) == []
    assert (reg.IPOS_PATH.read_bytes()).count(b"\r") == 0


def test_known_seven_present_and_match_inputs(ipos):
    _, rows = ipos
    ipo_rows = {r["ticker"]: r for r in rows if r["status"] in reg.IPO_STATUSES}
    assert set(reg.KNOWN_TICKERS) <= set(ipo_rows)
    for t in reg.KNOWN_TICKERS:
        doc = reg.load_inputs(reg.INPUTS_DIR / f"{t}.json")[0]
        ftd = doc["fields"]["first_trading_date"]
        assert ipo_rows[t]["first_trading_date"] == ftd["value"]
        assert ipo_rows[t]["listing_source_id"] == ftd["source_id"]
        assert ipo_rows[t]["company"] == doc["company"]


def test_non_frozen_rows_have_reason(ipos):
    _, rows = ipos
    for r in rows:
        if r["status"] != "FROZEN":
            assert reg.valid_skip_reason(r["skip_reason"]) and r["note"], r


def test_completeness_against_official_trading_start_notices(ipos):
    """Tamlık denetimi (§4): dönemin resmi 'Payların İşlem Görmeye Başlaması' bildirimlerinin her biri
    (ilk işlemi kapsamda olan) bir arz satırına karşılık gelir; eksik = hata."""
    _, rows = ipos
    by_source = {r["listing_source_id"]: r for r in rows}
    in_scope = []
    for n in ENUM["paylarin_islem_gormeye_baslamasi"]:
        row = by_source.get(f"KAP_{n['kap_id']}")
        if row is None:
            # kapsam dışı tek istisna: ilk işlemi 2026-08-07'den önce olan H99 üyesi
            assert n["related_stocks"] == "QUICK", n
            continue
        assert row["ticker"] == n["related_stocks"] and row["status"] in reg.IPO_STATUSES
        in_scope.append(row["ticker"])
    assert sorted(in_scope) == sorted(reg.KNOWN_TICKERS)
    for n in ENUM["listing_like_bist_notices"]:
        if n["decision"].startswith("OUT_OF_SCOPE"):
            assert by_source[f"KAP_{n['kap_id']}"]["status"] == "OUT_OF_SCOPE", n


def test_append_only_writer(tmp_path):
    path = tmp_path / "ipos.csv"
    row = {"ticker": "ZZZZ", "company": "Test A.Ş.", "first_trading_date": "2026-10-01", "listing_source_id": "KAP_1",
           "status": "SKIPPED", "skip_reason": "INPUTS_NOT_AVAILABLE", "note": "test", "added_at": "2026-09-22T15:00:00+03:00"}
    reg.append_ipos([row], path)
    first = path.read_bytes()
    with pytest.raises(reg.RegistryError):
        reg.append_ipos([row], path)  # aynı arz ikinci kez
    with pytest.raises(reg.RegistryError):
        reg.append_ipos([{**row, "ticker": "YYYY", "status": "SKIPPED", "skip_reason": ""}], path)
    with pytest.raises(reg.RegistryError):
        reg.append_ipos([{**row, "ticker": "XXXX", "status": "FROZEN", "skip_reason": "", "first_trading_date": "2026-08-01"}], path)
    assert path.read_bytes() == first
    reg.append_ipos([{**row, "ticker": "WWWW"}], path)
    assert path.read_bytes().startswith(first)
    with path.open(encoding="utf-8", newline="") as fh:
        assert [r["ticker"] for r in csv.DictReader(fh)] == ["ZZZZ", "WWWW"]

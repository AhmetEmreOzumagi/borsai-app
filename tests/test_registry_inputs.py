"""registry/inputs (şema borsai.inputs/1), inputs_pit_ok (SPEC_SCORING §5), kaynak belgeler ve
legacy rolleri (SPEC_SCORING §6)."""
from __future__ import annotations

import copy
import csv
import json
from decimal import Decimal

import pytest

from borsai import registry as reg
from borsai.features import compute_pb_features
from borsai.provenance import ROOT, sha256_file

INPUT_FILES = sorted(reg.INPUTS_DIR.glob("*.json"))
TICKERS = [p.stem for p in INPUT_FILES]


def load(ticker):
    return reg.load_inputs(reg.INPUTS_DIR / f"{ticker}.json")[0]


def test_one_input_file_per_known_ipo():
    assert set(TICKERS) == set(reg.KNOWN_TICKERS)


@pytest.mark.requires_raw_sources
@pytest.mark.parametrize("ticker", TICKERS)
def test_inputs_structure_and_pit(ticker):
    doc = load(ticker)
    assert doc["ticker"] == ticker
    assert reg.validate_inputs(doc) == []
    assert reg.inputs_pit_problems(doc) == []
    t = doc["fields"]["first_trading_date"]["value"]
    for name in reg.INPUT_FIELDS:
        f = doc["fields"][name]
        if f["value"] is None:
            assert f["missing_reason"]
            continue
        # her alan: kaynak kimliği + yayın zamanı (< ilk işlem günü) + belge sha256
        assert f["source_id"] and f["source_document"]
        assert reg.istanbul_date(f["source_published_at"]) < t
        assert sha256_file(ROOT / f["source_path"]) == f["source_sha256"]


@pytest.mark.requires_raw_sources
@pytest.mark.parametrize("ticker", TICKERS)
def test_source_manifest_matches_files(ticker):
    d = ROOT / "registry" / "source_docs" / ticker
    manifest = json.loads((d / "MANIFEST.json").read_text(encoding="utf-8"))
    files = {p.name for p in d.iterdir()} - {"MANIFEST.json"}
    assert {ROOT.joinpath(m["path"]).name for m in manifest["documents"].values()} == files
    doc = load(ticker)
    for sid, m in manifest["documents"].items():
        assert sha256_file(ROOT / m["path"]) == m["sha256"]
        assert m["url"].startswith(("https://www.kap.org.tr/", "https://spk.gov.tr/"))
        assert doc["sources"][sid]["sha256"] == m["sha256"]
        assert doc["sources"][sid]["published_at"] == m["published_at"]
        if m["kind"] == "KAP_ATTACHMENT_PDF":
            assert (ROOT / m["path"]).read_bytes()[:5] == b"%PDF-" and m["download_sha256"] != m["sha256"]


@pytest.mark.parametrize("ticker", TICKERS)
def test_pb_planned_structure_valid_and_prebookbuild(ticker):
    doc = load(ticker)
    inputs = reg.model_inputs(doc)
    compute_pb_features(inputs)  # ID-A/B/C ve aralıklar tutuyor
    b = doc["fields"]["bookbuilding_start"]["value"]
    for name in reg.PB_FIELDS:
        f = doc["fields"][name]
        assert f["source_id"].startswith("SPK_BULTEN_")  # H99 PB tanımıyla aynı kaynak türü
        assert reg.istanbul_date(f["source_published_at"]) < b  # talep toplamadan önce


@pytest.mark.requires_raw_sources
def test_pit_check_catches_violations():
    doc = load("CITAS")
    late = copy.deepcopy(doc)
    late["fields"]["ipo_price_tl"]["source_published_at"] = "2026-08-18T09:00:00+03:00"
    late["sources"][late["fields"]["ipo_price_tl"]["source_id"]]["published_at"] = "2026-08-18T09:00:00+03:00"
    assert any("ipo_price_tl" in p for p in reg.inputs_pit_problems(late))
    bad_sha = copy.deepcopy(doc)
    sid = bad_sha["fields"]["shares_offered"]["source_id"]
    bad_sha["sources"][sid]["sha256"] = "0" * 64
    for f in bad_sha["fields"].values():
        if f.get("source_id") == sid:
            f["source_sha256"] = "0" * 64
    assert any("sha256" in p for p in reg.inputs_pit_problems(bad_sha))
    no_reason = copy.deepcopy(doc)
    no_reason["fields"]["ipo_size_tl"] = {"value": None}
    assert any("missing_reason" in p for p in reg.validate_inputs(no_reason))
    missing = copy.deepcopy(doc)
    del missing["fields"]["total_demand_multiple"]
    assert any("total_demand_multiple" in p for p in reg.validate_inputs(missing))
    future = copy.deepcopy(doc)
    assert any("kayıt zamanından sonra" in p for p in reg.inputs_pit_problems(future, as_of="2026-08-10T00:00:00+03:00"))


def test_veyas_f3_left_empty_not_derived():
    f = load("VEYAS")["fields"]
    assert f["total_demand_multiple"]["value"] is None and "TÜRETİLMEZ" in f["total_demand_multiple"]["missing_reason"]
    assert f["total_demand_filter_status"]["value"] is None


LEGACY_VALUES = {  # dondurma kayıtlarındaki girdiler (registry/legacy_frozen)
    "NETGL": ("NETGL_20260916_V1_5/NETGL_20260916_V1_5_pretrade_evidence_packet.csv", "shares_offered_final"),
    "BKRGY": ("BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING/BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING_pretrade_evidence_packet.csv", "shares_offered_final"),
    "INTET": ("INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING/INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING_pretrade_evidence_packet.csv", "shares_offered_final"),
}


@pytest.mark.parametrize("ticker", sorted(LEGACY_VALUES))
def test_inputs_agree_with_legacy_frozen_packets(ticker):
    rel, shares_key = LEGACY_VALUES[ticker]
    with (reg.LEGACY_DIR / rel).open(encoding="utf-8-sig", newline="") as fh:
        packet = {r["field"]: r["normalized_value"] for r in csv.DictReader(fh)}
    f = {k: v["value"] for k, v in load(ticker)["fields"].items()}
    D = Decimal
    assert D(f["ipo_price_tl"]) == D(packet["ipo_price_tl"])
    assert D(f["shares_offered"]) == D(packet[shares_key])
    assert D(f["post_ipo_share_capital"]) == D(packet["post_ipo_share_capital"])
    assert D(f["capital_increase_shares"]) == D(packet["capital_increase_shares"])
    assert D(f["total_demand_multiple"]) == D(packet["f3"])


def test_tknka_agrees_with_legacy_freeze_document():
    text = (reg.LEGACY_DIR / "TKNKA_20260819_V1_5_FULL20" / "TKNKA_TRUE_LIVE_V1_5_FREEZE_20260819.md").read_text(encoding="utf-8")
    packet = json.loads(text[text.index("{\n  \"packet_type\""): text.index("Q. Repository Safety")].strip())
    f = {k: v["value"] for k, v in load("TKNKA")["fields"].items()}
    assert Decimal(f["total_demand_multiple"]) == Decimal(packet["f1_f5"]["f3_total_demand_multiple"])
    assert Decimal(f["ipo_size_tl"]) == Decimal(packet["f1_f5"]["f1_raw_ipo_size_tl"])
    assert f["first_trading_date"] == packet["first_trading_date"]


def test_legacy_roles_per_spec():
    doc = reg.load_legacy_roles()
    assert reg.validate_legacy_roles(doc) == []
    roles = {e["record"]: (e["ticker"], e["model_id"], e["role"], e["time_proof"]) for e in doc["records"]}
    assert roles == {
        "NETGL_20260916_V1_5": ("NETGL", "v1_5_h99", "PRIMARY", "GIT_PUSH"),
        "BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING": ("BKRGY", "v1_5_h99", "PRIMARY", "SELF_REPORTED"),
        "INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING": ("INTET", "v1_5_h99", "PRIMARY", "SELF_REPORTED"),
        "TKNKA_20260819_V1_5_FULL20": ("TKNKA", "v1_5_full20", "PRIMARY_SEPARATE_MODEL", "SELF_REPORTED"),
        "BKRGY_20260825_V1_5": ("BKRGY", "v1_5_h99", "INVALID_USE", "SELF_REPORTED"),
        "BKRGY_20260825_V1_5_R2": ("BKRGY", "v1_5_h99", "INVALID_USE", "SELF_REPORTED"),
        "INTET_20260825_V1_5": ("INTET", "v1_5_h99", "INVALID_USE", "SELF_REPORTED"),
    }
    netgl = next(e for e in doc["records"] if e["record"] == "NETGL_20260916_V1_5")
    assert netgl["push_proof_created_at"] == "2026-09-16T11:32:27Z"


D1 = "2026-09-02"


def cand(record_id, model_id, track, **kw):
    base = dict(has_official_f3=True, recorded_at="2026-09-22T12:00:00Z")
    base.update(kw)
    return reg.Candidate(record_id=record_id, model_id=model_id, track=track, **base)


def test_primary_selection_f3_models():
    cands = [
        cand("R1_PRE", "v1_5_h99", "SELF_REPORTED", has_official_f3=False, invalid_use=True, recorded_at="2026-08-25T00:00:00+03:00"),
        cand("R2_PRE", "v1_5_h99", "SELF_REPORTED", has_official_f3=False, invalid_use=True, recorded_at="2026-08-25T00:00:00+03:00"),
        cand("POST", "v1_5_h99", "SELF_REPORTED", recorded_at="2026-08-27T16:34:21+03:00"),
        cand("LATE", "v1_5_h99", "REGISTRY"),
    ]
    sel = reg.select_primary("v1_5_h99", cands, D1)
    assert sel["proven"] == {"record_id": "LATE", "rule": "EARLIEST_LATE_RECORD"}
    assert sel["self_reported"]["record_id"] == "POST"  # R1/R2 geçersiz kullanım: hiç aday değil
    # D_1'den önce push kanıtlı iki kayıt: EN SON olan
    live = cands + [cand("LIVE_A", "v1_5_h99", "REGISTRY", push_created_at="2026-08-28T08:00:00Z"),
                    cand("LIVE_B", "v1_5_h99", "REGISTRY", push_created_at="2026-08-31T08:00:00Z"),
                    cand("TOO_LATE", "v1_5_h99", "REGISTRY", push_created_at="2026-09-01T22:00:00Z")]  # İstanbul 09-02
    assert reg.select_primary("v1_5_h99", live, D1)["proven"] == {"record_id": "LIVE_B", "rule": "LATEST_PUSH_PROVEN_BEFORE_D1"}
    # iptal edilen ve f3'süz kayıt skorlanmaz
    only = [cand("X", "ceiling_hazard_v0", "REGISTRY", cancelled=True), cand("Y", "ceiling_hazard_v0", "REGISTRY", has_official_f3=False)]
    assert reg.select_primary("ceiling_hazard_v0", only, D1)["proven"]["record_id"] is None
    # pit başarısız kayıt LATE adayı değil
    assert reg.select_primary("v1_6_h99", [cand("Z", "v1_6_h99", "REGISTRY", inputs_pit_ok=False)], D1)["proven"]["record_id"] is None


def test_primary_selection_pb_and_rules_earliest():
    cands = [cand("A", "pb_v0", "REGISTRY", recorded_at="2026-08-20T09:00:00+03:00", bookbuilding_start="2026-08-24", has_official_f3=False),
             cand("B", "pb_v0", "REGISTRY", recorded_at="2026-08-27T09:00:00+03:00", bookbuilding_start="2026-08-24")]
    sel = reg.select_primary("pb_v0", cands, D1)["proven"]
    assert sel == {"record_id": "A", "rule": "EARLIEST_RECORD", "pb_after_bookbuild_start": 0}
    assert reg.select_primary("pb_v0", cands[1:], D1)["proven"]["pb_after_bookbuild_start"] == 1
    assert reg.select_primary("base_rate", [cand("C", "base_rate", "REGISTRY")], D1)["proven"]["record_id"] == "C"

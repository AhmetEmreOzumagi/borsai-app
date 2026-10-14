"""f1–f5 tanımı (borsai/features.py) ve f3 filtre modu."""
from __future__ import annotations

import csv
import itertools
import json
from decimal import Decimal

import pytest

from borsai import features as ft
from borsai.preprocess import filter_mode
from borsai.provenance import ROOT, canonical_sha256

READY = ROOT / "data" / "raw" / "HISTORICAL99_FROZEN_COHORT_V1_canonical_feature_readiness.csv"
NETGL_PACKET = ROOT / "registry" / "legacy_frozen" / "NETGL_20260916_V1_5" / "NETGL_20260916_V1_5_pretrade_evidence_packet.csv"
NETGL_LEDGER = ROOT / "registry" / "legacy_frozen" / "NETGL_20260916_V1_5" / "NETGL_20260916_V1_5_frozen_prediction_ledger.csv"
NETGL_CONTRACT = ROOT / "tests" / "reference" / "netgl_input_contract.json"


def _read(path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def netgl_inputs() -> dict:
    c = json.loads(NETGL_CONTRACT.read_text(encoding="utf-8"))
    return {
        "ipo_price_tl": c["ipo_price_tl"], "shares_offered": c["shares_offered_final"],
        "post_ipo_share_capital": c["post_ipo_share_capital"], "capital_increase_shares": c["capital_increase_shares"],
        "total_demand_multiple": c["official_total_demand_multiple"],
    }


def test_features_equal_h99_training_values_99_of_99(dataset):
    """Eğitim yolu: V1.5'in okuduğu feature_readiness değerleriyle Decimal-eşit."""
    ready = {r["ticker"]: r for r in _read(READY)}
    for row in dataset.rows:
        f = ft.compute_features(**row.feature_inputs())
        c = ready[row.ticker]
        assert f.f1 == Decimal(c["f1_raw_ipo_size_tl"]), row.ticker
        assert f.f2 == Decimal(c["f2_free_float_pct"]), row.ticker
        assert f.f4 == Decimal(c["f4_capital_increase_pct_of_offer"]), row.ticker
        f3 = c["f3_total_demand_multiple"]
        assert f.f3 == (None if f3 == "DATA_NOT_FOUND" else Decimal(f3)), row.ticker
        assert str(f.f5) == c["f5_total_demand_missing"]
        assert (row.total_demand_filter_status or "") == c["total_demand_filter_status"]


def test_f1_source_reported_differs_from_product_only_in_four_rows(dataset):
    differ = {}
    for row in dataset.rows:
        product = Decimal(row.inputs["ipo_price_tl"]) * Decimal(row.inputs["shares_offered"])
        size = Decimal(row.inputs["ipo_size_tl"])
        if size != product:
            differ[row.ticker] = abs(size - product)
        no_size = {**row.feature_inputs(), "ipo_size_tl": None}
        assert ft.compute_features(**no_size).f1 == product
    assert set(differ) == {"OBAMS", "AKFIS", "DSTKF", "KLYPV"}
    assert max(differ.values()) <= Decimal("0.46")


def test_live_path_equals_pbb_evidence_packet_and_feature_hash():
    """Canlı yol: NETGL kanıt paketindeki normalize değerler ve legacy candidate_feature_hash."""
    f = ft.compute_features(**netgl_inputs())
    packet = {r["field"]: r["normalized_value"] for r in _read(NETGL_PACKET)}
    assert {k: str(v) for k, v in f.as_dict().items()} == {k: packet[k] for k in ("f1", "f2", "f3", "f4")}
    assert str(f.f5) == packet["f5"]
    payload = {
        "feature_schema_version": "V1_FEATURES_20260814",
        "feature_set_identity": "V1_CORE_4_WITH_F3_BOUND_MISSINGNESS_INDICATOR_F5",
        "preprocessing_identity": "V1_3_FOLD_LOCAL_11_STEP_PREPROCESSING",
        **{k: str(v) for k, v in f.as_dict().items()},
        "f5": "0",
    }
    expected = {r["candidate_feature_hash"] for r in _read(NETGL_LEDGER)}
    assert {canonical_sha256(payload)} == expected


def test_f4_zero_is_accepted_as_number_and_text():
    base = netgl_inputs()
    for zero in (0, "0", 0.0):
        f = ft.compute_features(**{**base, "capital_increase_shares": zero})
        assert f.f4 == 0


@pytest.mark.parametrize(
    "patch, code, field",
    [
        ({"post_ipo_share_capital": "0"}, ft.DIVISION_BY_ZERO, "post_ipo_share_capital"),
        ({"shares_offered": 0}, ft.DIVISION_BY_ZERO, "shares_offered"),
        ({"ipo_price_tl": "-1"}, ft.INPUT_NOT_POSITIVE, "ipo_price_tl"),
        ({"ipo_price_tl": None}, ft.INPUT_MISSING, "ipo_price_tl"),
        ({"shares_offered": "abc"}, ft.INPUT_NOT_NUMERIC, "shares_offered"),
        ({"shares_offered": "NaN"}, ft.INPUT_NOT_NUMERIC, "shares_offered"),
        ({"shares_offered": True}, ft.INPUT_NOT_NUMERIC, "shares_offered"),
        ({"capital_increase_shares": "-5"}, ft.INPUT_NEGATIVE, "capital_increase_shares"),
        ({"capital_increase_shares": "90000000"}, ft.INPUT_INCONSISTENT, "capital_increase_shares"),
        ({"post_ipo_share_capital": "80000000"}, ft.INPUT_INCONSISTENT, "shares_offered"),
        ({"total_demand_multiple": "0"}, ft.INPUT_NOT_POSITIVE, "total_demand_multiple"),
        ({"ipo_size_tl": "0"}, ft.INPUT_NOT_POSITIVE, "ipo_size_tl"),
    ],
)
def test_bad_inputs_raise_labeled_errors(patch, code, field):
    with pytest.raises(ft.FeatureError) as exc:
        ft.compute_features(**{**netgl_inputs(), **patch})
    assert exc.value.code == code and exc.value.field == field


def test_f3_missing_is_not_zero():
    for missing in (None, "", "DATA_NOT_FOUND"):
        f = ft.compute_features(**{**netgl_inputs(), "total_demand_multiple": missing})
        assert f.f3 is None and f.f5 == 1


def test_filter_mode_is_deterministic_on_ties():
    statuses = ["UNFILTERED", "NOT_SPECIFIED", "FILTERED", "UNFILTERED", "FILTERED", "NOT_SPECIFIED"]
    results = {filter_mode(list(p)) for p in itertools.permutations(statuses)}
    assert results == {("FILTERED", True)}
    assert filter_mode(["UNFILTERED", "NOT_SPECIFIED", "UNFILTERED"]) == ("UNFILTERED", False)
    assert filter_mode([None, None]) == (None, False)

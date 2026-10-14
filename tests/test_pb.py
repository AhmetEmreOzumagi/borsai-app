"""SPEC_PB_V0 §11 kabul testleri 1–7 (`pb_v0`). Test 8 (`pb_ceiling_v0`) tests/test_ceiling.py'de."""
from __future__ import annotations

import statistics
from collections import Counter
from decimal import Decimal

import numpy as np
import pytest

from borsai import backtest as bt
from borsai import fit as fitmod
from borsai import predict as pr
from borsai import predict_pb as ppb
from borsai.data import load_pb
from borsai.features import (
    PB_FIELD_MISSING, PB_IDENTITY, PB_PRICE_RANGE, PB_REQUIRED_FIELDS, PBRefusal, compute_pb_features,
)
from borsai.preprocess import PB_RECIPE

from faz1b_support import faz1b_results, frozen, legacy_import, refit

PB_RULES = ("base_always_ceiling", "base_train_median", "base_train_mean", "base_zero", "base_rate", "base_last10_rate")


@pytest.fixture(scope="module")
def pb(dataset):
    return load_pb(dataset)


@pytest.fixture(scope="module")
def runs(backtest_results):
    return faz1b_results(backtest_results)


# ---------------------------------------------------------------- 1. özellikler

def test_1_all_99_rows_produce_features(pb):
    feats = {t: compute_pb_features(r.fields) for t, r in pb.items()}
    assert len(feats) == 99
    for r in pb.values():  # ID-A/B/C (Decimal, tam eşitlik) 99/99
        v = {f: Decimal(r.fields[f]) for f in PB_REQUIRED_FIELDS}
        assert v["planned_post_ipo_capital"] == v["planned_pre_ipo_capital"] + v["planned_capital_increase_shares"]
        assert v["planned_base_offer_shares"] == v["planned_capital_increase_shares"] + v["planned_existing_share_sale"]
        assert v["planned_max_offer_shares"] == v["planned_base_offer_shares"] + v["planned_additional_sale_ceiling"]
    assert sum(1 for f in feats.values() if f.pb4 != 0) == 7
    assert sum(1 for f in feats.values() if f.pb3 == 100) == 17
    assert Counter(round(f.pb4, 2) for f in feats.values()) == {0.0: 92, 20.0: 5, 18.4: 1, 10.0: 1}


# ---------------------------------------------------------------- 2. legacy paritesi

def test_2_parity_with_legacy_pb_core4(pb):
    legacy_import()
    import csv

    from borsai.data import PB_PATH
    from scripts.modeling.prebookbuild_v1_r6 import pb_core4

    with PB_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
        raw = {r["ticker"]: r for r in csv.DictReader(fh)}
    for t, r in pb.items():
        mine, ref = compute_pb_features(r.fields), pb_core4.build_pb_core4(raw[t])
        assert (mine.pb2, mine.pb3, mine.pb4) == (ref.pb2, ref.pb3, ref.pb4), t  # bit-eşit (Fraction -> float)
        assert abs(mine.pb1 - ref.pb1) <= 1e-12, t


# ---------------------------------------------------------------- 3. fold sayıları

def test_3_fold_counts_and_no_leak(dataset, pb):
    folds = bt.plan_folds_pb(dataset, pb)
    scorable = [f for f in folds if f.status == bt.SCORABLE]
    assert Counter(f.horizon for f in scorable) == {"D1": 87, "D3": 87, "D5": 87, "D10": 84}
    assert min(len(f.training) for f in scorable) == 12
    by = dataset.by_ticker()
    for f in folds:
        b = pb[f.test_ticker].first_bookbuilding_date
        assert f.prediction_date == b
        assert all(by[t].targets[f.horizon].session_date < b and by[t].first_trading_date < b for t in f.training)


def test_3_pb_ledger_uses_bookbuilding_cutoff(runs, pb):
    ledger = runs["pb_v0"].ledger
    assert len(ledger) == 87 * 3 + 84
    assert all(r["prediction_date"] == pb[r["ticker"]].first_bookbuilding_date < r["first_trading_date"] for r in ledger)


# ---------------------------------------------------------------- 4. yasak girdi

class _Recorder(dict):
    def __init__(self, data):
        super().__init__(data)
        self.read: set[str] = set()

    def get(self, key, default=None):
        self.read.add(key)
        return super().get(key, default)

    def __getitem__(self, key):
        self.read.add(key)
        return super().__getitem__(key)


def test_4_forbidden_inputs_are_never_read(pb, dataset):
    row = dataset.by_ticker()["QUICK"]
    fields = dict(pb["QUICK"].fields)
    forbidden_free = _Recorder(fields)
    f = compute_pb_features(forbidden_free)
    assert forbidden_free.read == set(PB_REQUIRED_FIELDS)
    poisoned = _Recorder({**fields, "total_demand_multiple": "x", "shares_offered": "x", "additional_sale_shares": "x",
                          **{f"R_{h}": "x" for h in ("D1", "D3", "D5", "D10")},
                          **{f"Y_{h}": "x" for h in ("D1", "D3", "D5", "D10")},
                          **{f"ceiling_close_D{k}": "x" for k in range(1, 11)}, "ceiling_streak_L": "x"})
    assert compute_pb_features(poisoned) == f and poisoned.read == set(PB_REQUIRED_FIELDS)
    out = ppb.predict(frozen("pb_v0"), _Recorder(fields))
    assert out["refused"] is None and out["D5"]["return"] is not None
    assert row.inputs["total_demand_multiple"] is not None  # QUICK'in f3'ü var ama PB yolu onu görmez


# ---------------------------------------------------------------- 5. ret

def test_5_refusals_are_labeled(pb):
    params = frozen("pb_v0")
    base = dict(pb["QUICK"].fields)
    cases = [
        ({"planned_base_offer_shares": ""}, PB_FIELD_MISSING, "planned_base_offer_shares"),
        ({"planned_pre_ipo_capital": None}, PB_FIELD_MISSING, "planned_pre_ipo_capital"),
        ({"ipo_price_try": "abc"}, PB_FIELD_MISSING, "ipo_price_try"),
        ({"planned_existing_share_sale": "1"}, PB_IDENTITY, "ID-B"),
        ({"planned_post_ipo_capital": "1"}, PB_IDENTITY, "ID-A"),
        ({"planned_max_offer_shares": "1"}, PB_IDENTITY, "ID-C"),
        ({"ipo_price_try": "10-12"}, PB_PRICE_RANGE, "ipo_price_try"),
        ({"ipo_price_try": "10 – 12"}, PB_PRICE_RANGE, "ipo_price_try"),
        ({"ipo_price_try": "-5"}, PB_IDENTITY, "VALUE_POSITIVE"),
    ]
    for patch, code, field in cases:
        with pytest.raises(PBRefusal) as exc:
            compute_pb_features({**base, **patch})
        assert (exc.value.code, exc.value.field) == (code, field), patch
        out = ppb.predict(params, {**base, **patch})
        assert (out["refused"]["code"], out["refused"]["field"]) == (code, field)
        assert all(out[h] is None for h in ("D1", "D3", "D5", "D10"))
    # Tutarlı ama aralık dışı yapı: sermaye artırımı 0 -> pb3 = 0 -> (0, 100] dışı
    zero_cap = {**base, "planned_capital_increase_shares": "0",
                "planned_existing_share_sale": base["planned_base_offer_shares"],
                "planned_post_ipo_capital": base["planned_pre_ipo_capital"]}
    assert ppb.predict(params, zero_cap)["refused"]["field"] == "PB3_RANGE"


def test_5_warnings(pb):
    params = frozen("pb_v0")
    with_ceiling = next(r.fields for r in pb.values() if Decimal(r.fields["planned_additional_sale_ceiling"]) > 0)
    out = ppb.predict(params, with_ceiling)
    assert out["refused"] is None and ppb.WARN_PB4_POSITIVE in {w["code"] for w in out["warnings"]}
    big = {**pb["QUICK"].fields, "ipo_price_try": "5000"}
    out = ppb.predict(params, big)
    assert out["refused"] is None and "pb1" in {w.get("feature") for w in out["warnings"]}
    for h in ("D1", "D3", "D5", "D10"):
        lo, hi = pr.physical_return_bounds(h)
        assert lo <= out[h]["return"] <= hi


# ---------------------------------------------------------------- 6. JSON <-> sklearn paritesi

def test_6_json_matches_sklearn_99_rows(dataset, pb):
    _, fits = refit("pb_v0")
    params = frozen("pb_v0")
    for r in dataset.rows:
        out = ppb.predict(params, pb[r.ticker].fields)
        assert out["refused"] is None
        for h in ("D1", "D3", "D5", "D10"):
            hf = fits[h]
            x = np.array([hf.final.matrix_rows([r.ticker])[0]], dtype=np.float64)
            r_sk = hf.ridge.constant if hf.ridge.estimator is None else float(hf.ridge.estimator.predict(x)[0])
            p_sk = hf.logit.constant if hf.logit.estimator is None else float(hf.logit.estimator.predict_proba(x)[0][1])
            assert abs(out[h]["return_unclipped"] - r_sk) <= 1e-12, (r.ticker, h)
            assert abs(out[h]["p_up"] - p_sk) <= 1e-12, (r.ticker, h)


def test_6_inf_zero_endpoints_give_training_mean_and_rate(pb, dataset):
    """Yalnız INF/ZERO adaylı ızgarayla sentetik durum: çıktı eğitim ortalaması / oranı (fit ve JSON)."""
    grid = fitmod.GridConfig("v1_6", (fitmod.INF,), (fitmod.ZERO,), fitmod.POLICY_CANDIDATE, fitmod.ZERO)
    rows = list(dataset.rows)[:40]
    raw = {r.ticker: compute_pb_features(pb[r.ticker].fields).as_dict() for r in rows}
    order = [r.ticker for r in rows]
    R = {r.ticker: r.targets["D5"].R_float for r in rows}
    Y = {r.ticker: r.targets["D5"].Y for r in rows}
    test = compute_pb_features(pb["QUICK"].fields).as_dict()
    hf = fitmod.fit_v1_5_horizon(order, raw, R, Y, {}, test_raw=test, grid=grid, recipe=PB_RECIPE)
    assert hf.ridge.selected_alpha == fitmod.INF and hf.logit.selected_C == fitmod.ZERO
    assert hf.ridge.prediction == statistics.mean(R.values())
    assert hf.logit.probability == sum(Y.values()) / len(Y)
    heads = fitmod.linear_heads(hf, grid)
    assert heads["return"]["alpha"] == "INF" and heads["p_up"]["C"] == "ZERO"
    assert heads["return"]["coef"] == [0.0] * len(heads["return"]["columns"])
    ret, p = pr.head_values(heads, [0.3, -1.2, 2.0])
    assert ret == hf.ridge.prediction and abs(p - hf.logit.probability) <= 1e-15


# ---------------------------------------------------------------- 7. kurallar PB kesimiyle

def test_7_rules_on_pb_cutoff_same_folds(runs):
    model = runs["pb_v0"].ledger
    for rule in PB_RULES:
        ledger = runs[f"{rule}__pb"].ledger
        assert [r["fold_id"] for r in ledger] == [r["fold_id"] for r in model]
        assert [r["training_tickers_sha256"] for r in ledger] == [r["training_tickers_sha256"] for r in model]
        assert runs[f"{rule}__pb"].log_entry["plan_id"] == runs["pb_v0"].log_entry["plan_id"]

"""Aynı makinede port ile legacy kodun bit düzeyinde eşitliği.

legacy/ değiştirilmeden import edilir (bytecode yazılmaz). Tam 351 fold'luk
karşılaştırma geliştirme sırasında bir kez koşuldu (351/351 aynı); burada uç
durumları kapsayan bir örnek koşar: tek sınıflı, fallback C, f3'süz test arzı,
f5'li eğitim kümesi, yakınsamayan D3|BETAE. Örnek fold'lar ayrıca paralel koşan
backtest ledger'ıyla da karşılaştırılır (paralel = sıralı).
"""
from __future__ import annotations

import json
import sys

import pytest

from borsai import backtest as bt
from borsai import preprocess as pp
from borsai.provenance import ROOT

SAMPLE = [
    "D1|EKOS", "D1|PATEK", "D1|HOROZ", "D3|AVPGY", "D3|BETAE", "D3|ENDAE", "D5|ALBTN", "D5|ORZAX",
    "D10|QUICK", "D10|ALBTN", "D10|AVPGY", "D1|QUICK",
]


@pytest.fixture(scope="module")
def legacy():
    sys.dont_write_bytecode = True
    path = str(ROOT / "legacy")
    if path not in sys.path:
        sys.path.insert(0, path)
    from scripts.modeling import candidate_models as cm
    from scripts.modeling import preprocessing as lpp
    from scripts.modeling.target_extraction import TargetRecord

    return cm, lpp, TargetRecord


@pytest.fixture(scope="module")
def plan(dataset):
    folds = [f for f in bt.plan_folds(dataset) if f.status == bt.SCORABLE]
    payloads = bt._v15_payloads(dataset, folds)
    return {f.fold_id: (f, p) for f, p in zip(folds, payloads)}


def _legacy_fit(legacy, dataset, fold, payload):
    cm, _, TargetRecord = legacy
    by = dataset.by_ticker()
    h = fold.horizon
    targets = {
        t: TargetRecord(
            ticker=t, first_trading_date=by[t].first_trading_date, horizon=h, target_session_date=by[t].targets[h].session_date,
            target_status="TARGET_AVAILABLE", underlying_row_status="OFFICIAL_VERIFIED", underlying_conflict_status="NO_CONFLICT",
            ipo_price_exact=by[t].inputs["ipo_price_tl"], official_close_exact=by[t].targets[h].close,
            R_h=by[t].targets[h].R, Y_h=by[t].targets[h].Y, thb_source_url=None, thb_source_sha256=None,
        )
        for t in fold.training
    }
    status = {**payload["status"], "__test__": payload["test_status"]}
    return (cm.fit_ridge_candidate(payload["raw"], targets, payload["test_raw"], status),
            cm.fit_logistic_candidate(payload["raw"], targets, payload["test_raw"], status))


@pytest.mark.parametrize("fold_id", SAMPLE)
def test_fold_bit_identical_to_legacy_and_parallel_run(fold_id, legacy, dataset, plan, backtest_results):
    fold, payload = plan[fold_id]
    mine = bt._v15_task(payload)
    lr, lg = _legacy_fit(legacy, dataset, fold, payload)
    assert mine["ridge_prediction"] == lr.prediction
    assert mine["ridge_selected_alpha"] == lr.selected_alpha and mine["ridge_status"] == lr.status
    assert json.loads(mine["ridge_columns"]) == list(lr.feature_names)
    assert [(e["hyperparameter"], e["score"]) for e in json.loads(mine["ridge_score_table"])] == \
        [(e.hyperparameter, e.score) for e in lr.candidate_score_table]
    assert mine["logit_status"] == lg.status and mine["logit_selected_C"] == lg.selected_C
    assert mine["logit_probability"] == lg.probability_positive_class
    assert mine["logit_predicted_class"] == lg.predicted_class
    assert mine["logit_tuning_status"] == lg.tuning_status
    assert [(e["hyperparameter"], e["score"]) for e in json.loads(mine["logit_score_table"])] == \
        [(e.hyperparameter, e.score) for e in lg.candidate_score_table]
    parallel = next(r for r in backtest_results["v1_5_h99"].ledger if r["fold_id"] == fold_id)
    assert {k: parallel[k] for k in mine} == mine


def _compare_preprocessing(legacy_result, fitted, test):
    assert list(legacy_result.active_substantive_features) + list(legacy_result.active_indicator_features) == list(fitted.columns)
    assert legacy_result.dropped_features == fitted.dropped
    assert legacy_result.train_matrix == fitted.train_matrix
    assert legacy_result.test_vector == test["z"]
    assert legacy_result.winsor_bounds == {k: (float(a), float(b)) for k, (a, b) in fitted.winsor_exact.items()}
    assert legacy_result.training_medians == {k: float(v) for k, v in fitted.median_exact.items()}
    assert {k: v[1] for k, v in legacy_result.standardization.items()} == fitted.params()["std"]


def test_preprocessing_bit_identical_full_99_with_netgl_row(legacy, dataset):
    _, lpp, _ = legacy
    from borsai.features import compute_features
    from test_features import netgl_inputs

    raw = {r.ticker: compute_features(**r.feature_inputs()).as_dict() for r in dataset.rows}
    status = {r.ticker: r.total_demand_filter_status for r in dataset.rows}
    test_raw = compute_features(**netgl_inputs()).as_dict()
    legacy_result = lpp.preprocess_fold(raw, test_raw, {**status, "__test__": None})
    fitted, test = pp.preprocess_fold(raw, test_raw, {**status, "__test__": None})
    _compare_preprocessing(legacy_result, fitted, test)


@pytest.mark.parametrize("fold_id", ["D1|EKOS", "D3|ENDAE", "D5|ALBTN", "D10|QUICK"])
def test_preprocessing_bit_identical_on_folds(fold_id, legacy, plan):
    _, lpp, _ = legacy
    fold, p = plan[fold_id]
    status = {**p["status"], "__test__": p["test_status"]}
    legacy_result = lpp.preprocess_fold(p["raw"], p["test_raw"], status)
    fitted, test = pp.preprocess_fold(p["raw"], p["test_raw"], status)
    _compare_preprocessing(legacy_result, fitted, test)

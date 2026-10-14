"""SPEC_V1_6 §10 kabul testleri 1–8 (`v1_6_h99`). Test 9 (seçim dağılımı raporu) tests/test_report.py'de."""
from __future__ import annotations

import statistics
from collections import Counter

import numpy as np
import pytest
from sklearn.linear_model import Ridge

from borsai import backtest as bt
from borsai import fit as fitmod
from borsai import predict as pr
from borsai import preprocess as pp
from borsai.fit import INF, ZERO, ScoreEntry
from borsai.specs import MODEL_SPECS

from faz1b_support import frozen, refit
from test_features import netgl_inputs

import refcompare as rc


@pytest.fixture(scope="module")
def v16(backtest_results):
    return backtest_results["v1_6_h99"]


@pytest.fixture(scope="module")
def golden_v15():
    return {r["fold_id"]: r for r in rc.read_csv(bt.GOLDEN_DIR / bt.golden_filename("v1_5_h99"))}


@pytest.fixture(scope="module")
def plan(dataset):
    folds = [f for f in bt.plan_folds(dataset) if f.status == bt.SCORABLE]
    return {f.fold_id: p for f, p in zip(folds, bt._v15_payloads(dataset, folds))}


# ---------------------------------------------------------------- 1. fold kimliği

def test_1_fold_identity_351(v16, golden_v15):
    assert len(v16.ledger) == 351
    assert sum(r["training_tickers_sha256"] == golden_v15[r["fold_id"]]["training_tickers_sha256"] for r in v16.ledger) == 351


# ---------------------------------------------------------------- 2. ızgara sabitleri

def test_2_grid_constants_and_json():
    assert fitmod.V1_6_ALPHA_GRID == (0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0, INF)
    assert fitmod.V1_6_C_GRID == (ZERO, 0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0)
    assert fitmod.RIDGE_ALPHA_GRID == (0.1, 1.0, 10.0, 100.0) and fitmod.LOGISTIC_C_GRID == (0.01, 0.1, 1.0, 10.0)
    spec = MODEL_SPECS["v1_6_h99"]
    assert fitmod.grid_from_spec(spec) == fitmod.V1_6_GRID
    assert fitmod.grid_from_spec(MODEL_SPECS["v1_5_h99"]) == fitmod.V1_5_GRID
    params = frozen("v1_6_h99")
    assert params["spec"]["grid_version"] == "v1_6"
    assert params["spec"]["ridge"]["alpha_grid"] == [0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0, "INF"]
    assert params["spec"]["logit"]["C_grid"] == ["ZERO", 0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0]
    for h in ("D1", "D3", "D5", "D10"):  # V1.5 ile aynı özellik ve ön işleme
        assert params["horizons"][h]["return"]["columns"] == ["f1", "f2", "f3", "f4", "f5"]
    assert {k: v for k, v in spec.items() if k in ("algorithm", "features", "preprocessing_id")} == \
        {k: v for k, v in MODEL_SPECS["v1_5_h99"].items() if k in ("algorithm", "features", "preprocessing_id")}


# ---------------------------------------------------------------- 3. V1.5'e indirgeme

def test_3_same_code_with_v1_5_grid_reproduces_macos_golden(backtest_results, plan, golden_v15, monkeypatch):
    golden = (bt.GOLDEN_DIR / bt.golden_filename("v1_5_h99")).read_bytes()
    assert backtest_results["v1_5_h99"].ledger_csv == golden  # tam ledger, bayt bayt
    calls = Counter()
    real_ridge, real_logit = fitmod._fit_ridge, fitmod._fit_logit

    def spy_ridge(order, R, inner, final, test, grid):
        calls["ridge:" + grid.name] += 1
        return real_ridge(order, R, inner, final, test, grid)

    def spy_logit(order, Y, inner, final, test, grid):
        calls["logit:" + grid.name] += 1
        return real_logit(order, Y, inner, final, test, grid)

    monkeypatch.setattr(fitmod, "_fit_ridge", spy_ridge)
    monkeypatch.setattr(fitmod, "_fit_logit", spy_logit)
    for fold_id in ("D1|EKOS", "D3|BETAE", "D5|ALBTN", "D10|QUICK"):
        explicit = bt._v15_task({**plan[fold_id], "grid": fitmod.V1_5_GRID, "recipe": pp.V1_5_RECIPE})
        g = golden_v15[fold_id]
        assert {k: bt._fmt(v) for k, v in explicit.items()} == {k: g[k] for k in explicit}, fold_id
        bt._v15_task({**plan[fold_id], "grid": fitmod.V1_6_GRID, "recipe": pp.V1_5_RECIPE})
    assert calls == {"ridge:v1_5": 4, "ridge:v1_6": 4, "logit:v1_5": 4, "logit:v1_6": 4}  # iki ızgara, tek kod yolu


# ---------------------------------------------------------------- 4. uç noktaların kapalı biçimi

def test_4_endpoint_scores_are_closed_form(plan):
    p = plan["D10|QUICK"]
    hf = fitmod.fit_v1_5_horizon(p["order"], p["raw"], p["R"], p["Y"], p["status"], test_raw=p["test_raw"],
                                 test_filter_status=p["test_status"], grid=fitmod.V1_6_GRID)
    order = p["order"]
    inf_entry = next(e for e in hf.ridge.score_table if e.hyperparameter == INF)
    errors = [abs(p["R"][j] - statistics.mean([p["R"][t] for t in order if t != j])) for j in order]
    assert inf_entry.score == sum(errors) / len(errors)
    zero_entry = next(e for e in hf.logit.score_table if e.hyperparameter == ZERO)
    terms = [(sum(p["Y"][t] for t in order if t != j) / (len(order) - 1) - p["Y"][j]) ** 2 for j in order]
    assert zero_entry.score == sum(terms) / len(terms)
    X = np.array(hf.final.matrix_rows(order), dtype=np.float64)
    x = np.array([[hf.test["z"][c] for c in hf.final.columns]], dtype=np.float64)
    big = Ridge(alpha=1e12, fit_intercept=True, solver="svd").fit(X, [p["R"][t] for t in order])
    assert abs(float(big.predict(x)[0]) - statistics.mean(p["R"][t] for t in order)) <= 1e-9


# ---------------------------------------------------------------- 5. eşitlik kuralı

def test_5_ties_choose_inf_and_zero():
    assert fitmod.select_alpha([ScoreEntry(10.0, 0.5, 9), ScoreEntry(INF, 0.5, 9), ScoreEntry(0.1, 0.6, 9)]) == INF
    assert fitmod.rank_C([ScoreEntry(0.01, 0.2, 9), ScoreEntry(ZERO, 0.2, 9), ScoreEntry(1.0, 0.1, 9)]) == [1.0, ZERO, 0.01]
    assert fitmod.rank_C([ScoreEntry(0.01, 0.2, 9), ScoreEntry(ZERO, 0.2, 9)])[0] == ZERO
    skipped = ScoreEntry(0.0001, None, 9, fitmod.STATUS_CANDIDATE_NOT_CONVERGED)
    assert fitmod.rank_C([skipped, ScoreEntry(0.1, 0.3, 9)]) == [0.1]


def test_5_constant_target_ridge_tie_selects_inf(plan):
    p = plan["D5|ORZAX"]
    R = {t: 0.25 for t in p["order"]}
    hf = fitmod.fit_v1_5_horizon(p["order"], p["raw"], R, p["Y"], p["status"], test_raw=p["test_raw"],
                                 test_filter_status=p["test_status"], grid=fitmod.V1_6_GRID)
    assert {e.score for e in hf.ridge.score_table} == {0.0} and hf.ridge.selected_alpha == INF
    assert hf.ridge.prediction == 0.25


# ---------------------------------------------------------------- 6. aday başına yakınsamama

def _forced(real, fail):
    def wrapper(estimator, X, y):
        conv, other = real(estimator, X, y)
        return (["FORCED_CONVERGENCE_WARNING"] + conv if fail(estimator, X) else conv), other
    return wrapper


def test_6_candidate_level_non_convergence(plan, monkeypatch):
    p = plan["D5|ORZAX"]
    kwargs = dict(test_raw=p["test_raw"], test_filter_status=p["test_status"])
    args = (p["order"], p["raw"], p["R"], p["Y"], p["status"])
    real = fitmod._fit_logistic
    monkeypatch.setattr(fitmod, "_fit_logistic", _forced(real, lambda est, X: est.C == 100.0))
    hf = fitmod.fit_v1_5_horizon(*args, grid=fitmod.V1_6_GRID, **kwargs)
    status = {e.hyperparameter: e.status for e in hf.logit.score_table}
    assert hf.logit.status == fitmod.STATUS_FIT_OK and status[100.0] == fitmod.STATUS_CANDIDATE_NOT_CONVERGED
    assert all(s == fitmod.STATUS_SCORED for c, s in status.items() if c != 100.0)
    ranked = fitmod.rank_C(hf.logit.score_table)
    assert 100.0 not in ranked and hf.logit.selected_C == ranked[0]
    # Aynı zorlama V1.5 politikasında bütün fold'u düşürür
    v15 = fitmod.fit_v1_5_horizon(*args, grid=fitmod.GridConfig("v1_5", fitmod.RIDGE_ALPHA_GRID, (0.1, 100.0),
                                                              fitmod.POLICY_FOLD, 0.01), **kwargs)
    assert v15.logit.status == fitmod.STATUS_NOT_CONVERGED
    # Nihai (dış) fit yakınsamazsa sıradaki aday. ZERO kapalı biçimdir, hiç yakınsamazlık
    # üretmez; zorlama sklearn adayına düşsün diye aynı politika ZERO'suz ızgarayla koşar.
    no_zero = fitmod.GridConfig("v1_6", fitmod.V1_6_ALPHA_GRID, fitmod.V1_6_C_GRID[1:], fitmod.POLICY_CANDIDATE, 0.01)
    monkeypatch.setattr(fitmod, "_fit_logistic", _forced(real, lambda est, X: est.C == 100.0))
    ranked = fitmod.rank_C(fitmod.fit_v1_5_horizon(*args, grid=no_zero, **kwargs).logit.score_table)
    first, second = ranked[0], ranked[1]
    n = len(p["order"])
    monkeypatch.setattr(fitmod, "_fit_logistic", _forced(real, lambda est, X: est.C == 100.0 or (est.C == first and X.shape[0] == n)))
    hf2 = fitmod.fit_v1_5_horizon(*args, grid=no_zero, **kwargs)
    assert hf2.logit.status == fitmod.STATUS_FIT_OK and hf2.logit.selected_C == second
    assert hf2.logit.final_attempts[0] == (fitmod.hp_label(first, "C"), fitmod.STATUS_NOT_CONVERGED)
    assert hf2.logit.final_attempts[-1] == (fitmod.hp_label(second, "C"), fitmod.STATUS_FIT_OK)


# ---------------------------------------------------------------- 7. BETAE

def test_7_betae_d3_is_scored_and_d3_logit_n_is_81(v16):
    row = next(r for r in v16.ledger if r["fold_id"] == "D3|BETAE")
    import json

    table = json.loads(row["logit_score_table"])
    dropped = [e["hyperparameter"] for e in table if e["status"] == fitmod.STATUS_CANDIDATE_NOT_CONVERGED]
    assert row["logit_status"] == fitmod.STATUS_FIT_OK, dropped
    assert sum(1 for r in v16.ledger if r["horizon"] == "D3" and r["logit_status"] == fitmod.STATUS_FIT_OK) == 81
    # V1.6'da Logit fold'u yalnız tek sınıfta düşer
    assert {r["logit_status"] for r in v16.ledger if r["logit_status"] != fitmod.STATUS_FIT_OK} <= {fitmod.STATUS_SINGLE_CLASS}


# ---------------------------------------------------------------- 8. predict paritesi

def test_8_json_matches_sklearn_99_rows_and_netgl(dataset):
    _, fits = refit("v1_6_h99")
    params = frozen("v1_6_h99")
    compared = 0
    for row in dataset.rows:
        inputs = {**row.feature_inputs(), "total_demand_filter_status": row.total_demand_filter_status}
        out = pr.predict(params, inputs)
        if row.inputs["total_demand_multiple"] is None:
            assert out["refused"]["code"] == pr.REFUSED_F3_MISSING
            continue
        for h in ("D1", "D3", "D5", "D10"):
            hf = fits[h]
            x = np.array([hf.final.matrix_rows([row.ticker])[0]], dtype=np.float64)
            r_sk = hf.ridge.constant if hf.ridge.selected_alpha == INF else float(hf.ridge.estimator.predict(x)[0])
            p_sk = hf.logit.constant if hf.logit.selected_C == ZERO else float(hf.logit.estimator.predict_proba(x)[0][1])
            assert abs(out[h]["return_unclipped"] - r_sk) <= 1e-12 and abs(out[h]["p_up"] - p_sk) <= 1e-12, (row.ticker, h)
        compared += 1
    assert compared == 97
    netgl = pr.predict(params, netgl_inputs())
    assert netgl["refused"] is None
    for h in ("D1", "D3", "D5", "D10"):  # INF/ZERO seçilmiş ufukta çıktı sabittir
        heads = params["horizons"][h]
        if heads["return"]["alpha"] == "INF":
            assert netgl[h]["return_unclipped"] == heads["return"]["intercept"] == fits[h].ridge.constant
        if heads["p_up"]["C"] == "ZERO":
            assert abs(netgl[h]["p_up"] - fits[h].logit.constant) <= 1e-15
    assert pr.predict(params, {**netgl_inputs(), "total_demand_multiple": None})["refused"]["code"] == pr.REFUSED_F3_MISSING

"""SPEC_CEILING_V0 §13 kabul testleri 1–11 (`ceiling_hazard_v0`) ve SPEC_PB_V0 §11-8
(`pb_ceiling_v0` için 1, 3–8, 10–11; f3 = None iken RET ETMEZ)."""
from __future__ import annotations

import json
import math
import random

import numpy as np
import pytest
from scipy.optimize import minimize

from borsai import backtest as bt
from borsai import hazard as hz
from borsai import predict_hazard as ph
from borsai import survival as sv
from borsai.data import load_pb
from borsai.fit import model_raw_features, select_training_rows
from borsai.predict import REFUSED_F3_MISSING
from borsai.provenance import ROOT, sha256_file
from borsai.specs import MODEL_SPECS, PLAN_CEILING, PLAN_PB_CEILING, spec_sha256

from faz1b_support import faz1b_results, frozen, refit

DAY_TABLE = {1: (99, 18), 2: (81, 11), 3: (70, 4), 4: (66, 13), 5: (53, 12), 6: (41, 8), 7: (33, 6), 8: (27, 6),
             9: (21, 4), 10: (17, 3)}
HAZARD_MODELS = ("ceiling_hazard_v0", "pb_ceiling_v0")
SPEC_DOC = {"ceiling_hazard_v0": "docs/specs/SPEC_CEILING_V0.md", "pb_ceiling_v0": "docs/specs/SPEC_PB_V0.md"}


@pytest.fixture(scope="module")
def units(dataset):
    return [sv.unit_of(r) for r in dataset.rows]


@pytest.fixture(scope="module")
def pb(dataset):
    return load_pb(dataset)


@pytest.fixture(scope="module")
def runs(backtest_results):
    return faz1b_results(backtest_results)


# ---------------------------------------------------------------- 1. PP sayımı

def test_1_person_period_counts(units, dataset):
    rows = sv.pp_table(units)
    assert len(rows) == 508 and sum(r.event for r in rows) == 85
    for d, (risk, events) in DAY_TABLE.items():
        day = [r for r in rows if r.day == d]
        assert (len(day), sum(r.event for r in day)) == (risk, events), d
    assert sv.group_counts(rows) == ([18, 15, 52], [99, 151, 258])
    f3 = [sv.unit_of(r) for r in dataset.rows if r.inputs["total_demand_multiple"] is not None]
    rows97 = sv.pp_table(f3)
    assert len(f3) == 97 and len(rows97) == 506 and sum(r.event for r in rows97) == 83
    # L = 10 olan arz 10 satır, hepsi event = 0
    full = [u for u in units if u.streak == 10]
    assert full and all([r.event for r in sv.pp_rows(u)] == [0] * 10 for u in full)


# ---------------------------------------------------------------- 2. fold kurulumu

def _independent_fold_count(dataset, pb, plan):
    """m2_fold_pb_market.py mantığıyla, plan kodundan bağımsız sayım."""
    rows = dataset.rows
    eligible = [r for r in rows if plan == PLAN_PB_CEILING or r.inputs["total_demand_multiple"] is not None]
    out = []
    for k in eligible:
        c = k.first_trading_date if plan == PLAN_CEILING else pb[k.ticker].first_bookbuilding_date
        ev = sv_ = nipo = 0
        for j in eligible:
            if j.first_trading_date >= c:
                continue
            got = False
            for d in range(1, 11):
                if d - 1 > j.ceiling_streak or j.session_dates[d - 1] >= c:
                    break
                got = True
                ev += j.ceiling_streak == d - 1
                sv_ += j.ceiling_streak != d - 1
            nipo += got
        if nipo >= 10 and ev >= 5 and sv_ >= 5:
            out.append((k.ticker, nipo, ev, sv_))
    return out


def test_2_fold_setup_ceiling(runs, dataset, pb):
    res = runs["ceiling_hazard_v0"]
    scorable = [f for f in res.folds if f.status == bt.SCORABLE]
    assert len(res.folds) == 97 and len(scorable) == 87
    first = scorable[0]
    assert (first.test_ticker, first.first_trading_date) == ("EKOS", "2023-11-21")
    assert (len(first.training), first.n_events, first.n_survivals) == (10, 6, 64)
    for f in res.folds:
        assert f.test_ticker not in ("ALBTN", "ENDAE") and not {"ALBTN", "ENDAE"} & set(f.training)
    assert [(f.test_ticker, len(f.training), f.n_events, f.n_survivals) for f in scorable] == \
        _independent_fold_count(dataset, pb, PLAN_CEILING)
    for r in res.ledger:  # sızıntı: her fold'da max(eğitim seans tarihi) < T
        assert r["training_max_session_date"] < r["prediction_date"] == r["first_trading_date"]


def test_2_fold_setup_pb_ceiling(runs, dataset, pb):
    res = runs["pb_ceiling_v0"]
    scorable = [f for f in res.folds if f.status == bt.SCORABLE]
    assert len(res.folds) == 99
    assert [(f.test_ticker, len(f.training), f.n_events, f.n_survivals) for f in scorable] == \
        _independent_fold_count(dataset, pb, PLAN_PB_CEILING)
    for r in res.ledger:  # kesim B(k)
        assert r["prediction_date"] == pb[r["ticker"]].first_bookbuilding_date
        assert r["training_max_session_date"] < r["prediction_date"]


# ---------------------------------------------------------------- 3. sansür

SYN_DATES = ("2025-03-03", "2025-03-04", "2025-03-05", "2025-03-06", "2025-03-07", "2025-03-10", "2025-03-11",
             "2025-03-12", "2025-03-13", "2025-03-14")


@pytest.mark.parametrize("streak, expected", [(10, [(1, 0), (2, 0), (3, 0)]), (5, [(1, 0), (2, 0), (3, 0)]),
                                              (1, [(1, 0), (2, 1)]), (0, [(1, 1)])])
def test_3_censoring_three_sessions_before_cutoff(streak, expected, units):
    cutoff = SYN_DATES[3]  # D1–D3 kesimden önce
    closes = tuple(1 if k < streak else 0 for k in range(10))
    syn = sv.Unit("SYNTH", SYN_DATES[0], streak, SYN_DATES, closes)
    assert [(r.day, r.event) for r in sv.pp_rows(syn, cutoff)] == expected
    # Bir eğitim kümesinin içinde de aynı: eklenen satır sayısı değişmez
    base = [u for u in units if u.first_trading_date < "2025-03-01"]
    with_syn = sv.pp_table(base + [syn], cutoff)
    assert len(with_syn) - len(sv.pp_table(base, cutoff)) == len(expected)


# ---------------------------------------------------------------- 4. tutarlılık

def _random_v15_inputs(rng: random.Random) -> dict:
    shares = rng.randint(5_000_000, 600_000_000)
    return {
        "ipo_price_tl": f"{rng.uniform(2, 300):.2f}",
        "shares_offered": str(shares),
        "post_ipo_share_capital": str(int(shares / rng.uniform(0.05, 0.6))),
        "capital_increase_shares": str(int(shares * rng.uniform(0.0, 1.0))),
        "total_demand_multiple": f"{rng.uniform(0.3, 80):.2f}",
    }


def _random_pb_inputs(rng: random.Random) -> dict:
    base = rng.randint(5_000_000, 600_000_000)
    cap_inc = int(base * rng.uniform(0.05, 1.0))
    pre = int(base / rng.uniform(0.05, 0.6))
    addl = rng.choice([0, 0, int(base * 0.2)])
    return {
        "ipo_price_try": f"{rng.uniform(2, 300):.2f}", "planned_pre_ipo_capital": str(pre),
        "planned_post_ipo_capital": str(pre + cap_inc), "planned_capital_increase_shares": str(cap_inc),
        "planned_existing_share_sale": str(base - cap_inc), "planned_base_offer_shares": str(base),
        "planned_additional_sale_ceiling": str(addl), "planned_max_offer_shares": str(base + addl),
    }


def _check_consistency(out: dict) -> None:
    S, P_L, Pc = out["S"], out["P_L"], out["P_close_ceiling"]
    assert 1.0 >= S[0] and all(S[k] >= S[k + 1] for k in range(9)) and S[9] >= 0.0
    assert len(P_L) == 11 and abs(sum(P_L) - 1.0) <= 1e-12
    assert all(Pc[k] >= S[k] for k in range(10)) and Pc[0] == S[0]


@pytest.mark.parametrize("model_id", HAZARD_MODELS + ("ceiling_hazard_v0@INF", "pb_ceiling_v0@INF",
                                                      "base_km_expanding", "base_km_last10"))
def test_4_consistency_1000_random_plus_99_training(model_id, dataset, pb):
    params = frozen(model_id)
    rng = random.Random(20260921)
    make = _random_pb_inputs if model_id.startswith("pb_") else _random_v15_inputs
    inputs = [make(rng) for _ in range(1000)]
    inputs += [pb[r.ticker].fields if model_id.startswith("pb_") else r.feature_inputs() for r in dataset.rows]
    scored = 0
    for inp in inputs:
        out = ph.predict(params, inp)
        if out["refused"] is not None:
            assert model_id == "ceiling_hazard_v0" and out["refused"]["code"] == REFUSED_F3_MISSING
            continue
        _check_consistency(out)
        scored += 1
    assert scored == (1099 if model_id != "ceiling_hazard_v0" else 1099 - 2)


# ---------------------------------------------------------------- 5. λ = INF kapalı biçim

def test_5_inf_closed_form_whole_cohort(units, dataset):
    rows = sv.pp_table(units)
    g = np.array([r.group for r in rows], dtype=np.intp)
    e = np.array([r.event for r in rows], dtype=np.float64)
    fit = hz.fit_rows(g, np.zeros((len(rows), 0)), e, hz.INF, ())
    events, risk = sv.group_counts(rows)
    for i in range(3):
        p = (events[i] + 0.5) / (risk[i] + 1)
        assert fit.gamma[i] == sv.closed_form_gamma(events[i], risk[i])
        assert abs(fit.gamma[i] - math.log(p / (1 - p))) <= 1e-12
    S = sv.survival(fit.hazards({}))
    assert abs(S[0] - (1 - 18.5 / 100)) <= 1e-15
    # Dondurulmuş @INF uçları: pb_ceiling_v0@INF 99 arz, ceiling_hazard_v0@INF f3 dolu 97 arz (D1: 16/97)
    assert abs(ph.predict(frozen("pb_ceiling_v0@INF"))["S"][0] - (1 - 18.5 / 100)) <= 1e-15
    assert abs(ph.predict(frozen("ceiling_hazard_v0@INF"))["S"][0] - (1 - 16.5 / 98)) <= 1e-15


# ---------------------------------------------------------------- 6. çözücü

def _synthetic(seed: int, m: int = 400, p: int = 3):
    rng = np.random.default_rng(seed)
    g = rng.integers(0, 3, size=m)
    Z = rng.normal(size=(m, p))
    eta = np.array([-1.5, -2.0, -1.2])[g] + Z @ np.array([0.8, -0.5, 0.3])
    e = (rng.random(m) < 1 / (1 + np.exp(-eta))).astype(np.float64)
    return g, Z, e


@pytest.mark.parametrize("lam", [0.5, 3.0, 100.0])
def test_6_solver_matches_bfgs_without_pseudo_rows(lam):
    g, Z, e = _synthetic(7)
    fit = hz.fit_rows(g, Z, e, lam, ("a", "b", "c"), pseudo=False)
    assert fit.status == hz.CONVERGED and fit.grad_max <= 1e-10
    X = hz.design(g, Z)
    w = np.ones(len(e))
    pen = np.r_[np.zeros(3), np.full(3, lam)]

    def J(t):
        return hz.objective(X, e, w, t, lam)

    def grad(t):
        h = 1 / (1 + np.exp(-(X @ t)))
        return X.T @ (h - e) + pen * t

    ref = minimize(J, np.zeros(6), jac=grad, method="BFGS", options={"gtol": 1e-11, "maxiter": 10000})
    theta = np.r_[fit.gamma, fit.beta]
    assert np.max(np.abs(theta - ref.x)) <= 1e-6


def test_6_gamma_is_not_penalized():
    g, Z, e = _synthetic(11)
    huge = hz.fit_rows(g, Z, e, 1e9, ("a", "b", "c"))
    inf = hz.fit_rows(g, Z, e, hz.INF, ("a", "b", "c"))
    assert huge.status == hz.CONVERGED
    assert np.max(np.abs(huge.gamma - inf.gamma)) <= 1e-6
    assert float(np.linalg.norm(huge.beta)) <= 1e-6


# ---------------------------------------------------------------- 7. seçim kuralı

def test_7_tie_goes_to_largest_lambda_and_inf_is_in_grid():
    assert hz.LAMBDA_GRID == (0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, hz.INF)
    assert [hz.lambda_parse(x) for x in MODEL_SPECS["ceiling_hazard_v0"]["lambda_grid"]] == list(hz.LAMBDA_GRID)
    table = [{"lambda": 1.0, "score": 0.31, "status": hz.SCORED}, {"lambda": 10.0, "score": 0.3, "status": hz.SCORED},
             {"lambda": 30.0, "score": 0.3, "status": hz.SCORED}, {"lambda": "INF", "score": 0.4, "status": hz.SCORED}]
    assert hz.choose_lambda(table) == 30.0
    table[3]["score"] = 0.3
    assert hz.choose_lambda(table) == hz.INF
    table[3]["status"], table[3]["score"] = hz.CANDIDATE_NOT_CONVERGED, None
    assert hz.choose_lambda(table) == 30.0


def test_7_constant_features_select_inf(units, dataset):
    """Üç özellik de sıfır varyanslıysa her λ yalnız sabitlere iner, skorlar bit-eşit, INF seçilir."""
    train = [u for u in units if u.first_trading_date < "2024-06-01"]
    const = {"f1": 1e9, "f2": 25, "f3": 3}
    from borsai.preprocess import CEILING_RECIPE
    from decimal import Decimal
    raw = {u.ticker: {k: Decimal(v) for k, v in const.items()} for u in train}
    res = hz.fit_training_set(train, raw, {}, cutoff=None, features=("f1", "f2", "f3"), recipe=CEILING_RECIPE)
    assert len({e["score"] for e in res.score_table}) == 1 and res.selected_lambda == hz.INF


# ---------------------------------------------------------------- 8. JSON <-> fit paritesi

@pytest.mark.parametrize("model_id", HAZARD_MODELS)
def test_8_json_matches_numpy_final_model(model_id, dataset, pb):
    spec = MODEL_SPECS[model_id]
    params, fits = refit(model_id)
    res = fits["hazard"]
    rows = select_training_rows(spec, dataset.rows)
    raw = model_raw_features(spec, rows)[0]
    frozen_params = frozen(model_id)
    assert len(rows) == (97 if model_id == "ceiling_hazard_v0" else 99)
    for r in rows:
        mine = res.predict(raw[r.ticker], r.total_demand_filter_status)
        inputs = pb[r.ticker].fields if model_id == "pb_ceiling_v0" else r.feature_inputs()
        out = ph.predict(frozen_params, inputs)
        assert out["refused"] is None
        for key_numpy, key_json in (("hazards", "hazard"), ("S", "S"), ("P_close", "P_close_ceiling")):
            assert max(abs(a - b) for a, b in zip(mine[key_numpy], out[key_json])) <= 1e-12, (r.ticker, key_json)


# ---------------------------------------------------------------- 9. ret ve uyarı

def test_9_refusal_and_warnings_ceiling(dataset):
    params = frozen("ceiling_hazard_v0")
    base = dataset.by_ticker()["QUICK"].feature_inputs()
    for missing in (None, "", "DATA_NOT_FOUND"):
        out = ph.predict(params, {**base, "total_demand_multiple": missing})
        assert out["refused"]["code"] == REFUSED_F3_MISSING and out["S"] is None
    w = params["preprocessing"]["winsor"]["f3"]
    for f3 in ("0.5", "50"):
        out = ph.predict(params, {**base, "total_demand_multiple": f3})
        assert out["refused"] is None and out["clipped"] is True and out["S"] is not None
        assert ph.WARN_F3_CLIPPED in {x["code"] for x in out["warnings"]}
        expected_used = w["p05"] if f3 == "0.5" else w["p95"]
        assert [x["used"] for x in out["warnings"] if x["code"] == ph.WARN_F3_CLIPPED] == [expected_used]
    out = ph.predict(params, {**base, "ipo_price_tl": "5000", "ipo_size_tl": None})
    assert out["refused"] is None and out["S"] is not None and out["clipped"] is False
    assert [x["feature"] for x in out["warnings"] if x["code"] == ph.WARN_OUT_OF_TRAINING_RANGE] == ["f1"]
    for patch, code in (({"post_ipo_share_capital": "0"}, "DIVISION_BY_ZERO"), ({"ipo_price_tl": "-3"}, "INPUT_NOT_POSITIVE"),
                        ({"shares_offered": "abc"}, "INPUT_NOT_NUMERIC")):
        assert ph.predict(params, {**base, **patch})["refused"]["code"] == code


def test_9_pb_ceiling_does_not_refuse_without_f3(pb):
    params = frozen("pb_ceiling_v0")
    fields = dict(pb["QUICK"].fields)
    for extra in ({}, {"total_demand_multiple": None}, {"total_demand_multiple": ""}):
        out = ph.predict(params, {**fields, **extra})
        assert out["refused"] is None and out["S"] is not None
    assert ph.predict(params, {**fields, "planned_base_offer_shares": ""})["refused"]["code"] == "PB_FIELD_MISSING"


# ---------------------------------------------------------------- 10. kurallar aynı fold'da

@pytest.mark.parametrize("model_id, plan_key, n", [("ceiling_hazard_v0", "ceiling", 87), ("pb_ceiling_v0", "pb_ceiling", None)])
def test_10_rules_on_same_folds(model_id, plan_key, n, runs):
    model = runs[model_id]
    tickers = [r["ticker"] for r in model.ledger]
    if n is not None:
        assert len(tickers) == n
    at_inf = runs[f"{model_id}@INF"]
    rules = [at_inf, runs[bt.run_key("base_always_ceiling", model.log_entry["plan_id"])],
             runs[bt.run_key("base_km_expanding", model.log_entry["plan_id"])],
             runs[bt.run_key("base_km_last10", model.log_entry["plan_id"])]]
    for rule in rules:
        assert [r["ticker"] for r in rule.ledger] == tickers
        assert [r["training_tickers_sha256"] for r in rule.ledger] == [r["training_tickers_sha256"] for r in model.ledger]
        assert [r["training_pp_sha256"] for r in rule.ledger] == [r["training_pp_sha256"] for r in model.ledger]
    assert all(r["status"] == hz.STATUS_FIT_OK for r in model.ledger + at_inf.ledger)
    assert all(r["S_1"] == 1.0 and r["P_close_10"] == 1.0 for r in rules[1].ledger)


def test_10_inf_rule_equals_closed_form_of_fold_counts(runs, dataset):
    units = {r.ticker: sv.unit_of(r) for r in dataset.rows}
    res = runs["ceiling_hazard_v0@INF"]
    folds = {f.fold_id: f for f in res.folds}
    for r in res.ledger:
        f = folds[r["fold_id"]]
        events, risk = sv.group_counts(sv.pp_table([units[t] for t in f.training], f.cutoff_date))
        assert [r[f"gamma_{g}"] for g in sv.GROUP_NAMES] == [sv.closed_form_gamma(events[i], risk[i]) for i in range(3)]


# ---------------------------------------------------------------- 11. deney günlüğü

@pytest.mark.parametrize("model_id", ["ceiling_hazard_v0@INF", "pb_ceiling_v0@INF"])
def test_11_backtest_appends_one_log_line_with_spec_document_sha(model_id, dataset, tmp_path):
    log = tmp_path / "log.jsonl"
    log.write_text('{"sentinel": 1}\n', encoding="utf-8")
    res = bt.run_backtest(model_id, dataset, log_path=log, context="pytest", workers=1)
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 and json.loads(lines[0]) == {"sentinel": 1}
    entry = json.loads(lines[1])
    doc = MODEL_SPECS[model_id]["spec_document"]["path"]
    assert entry["spec_document_sha256"] == sha256_file(ROOT / doc) == MODEL_SPECS[model_id]["spec_document"]["sha256"]
    assert entry["spec_sha256"] == spec_sha256(MODEL_SPECS[model_id]) and entry["ledger_sha256"] == res.log_entry["ledger_sha256"]


@pytest.mark.parametrize("model_id", HAZARD_MODELS)
def test_11_session_runs_logged_with_spec_document(model_id, backtest_results, test_log_path):
    entries = [json.loads(x) for x in test_log_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    (entry,) = [e for e in entries if e["model_id"] == model_id]
    assert entry["spec_document"] == SPEC_DOC[model_id]
    assert entry["spec_document_sha256"] == sha256_file(ROOT / SPEC_DOC[model_id])
    assert entry["ledger_sha256"] == backtest_results[model_id].log_entry["ledger_sha256"]

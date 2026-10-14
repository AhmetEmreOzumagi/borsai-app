"""SPEC_MARKET20_V0 §11 kabul testleri 1–11 (`v1_5_market20_v0`, f6_market20)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pytest

from borsai import backtest as bt
from borsai import market20 as m20
from borsai import predict as pr
from borsai import predict_market20 as pm
from borsai.specs import MODEL_SPECS

from faz1b_support import frozen, legacy_import, refit

import refcompare as rc

A6 = {"HATSN", "DMRGD", "MEKAG", "DOFER", "MHRGY", "BORLS"}


@pytest.fixture(scope="module")
def cal_b():
    return m20.load_calendar_b()


@pytest.fixture(scope="module")
def xu100():
    return m20.load_xu100()


@pytest.fixture(scope="module")
def h99(dataset):
    return m20.h99_market20([(r.ticker, r.first_trading_date) for r in dataset.rows])


# ---------------------------------------------------------------- 1. kapsam

def test_1_coverage_calendar_b_99_calendar_a_refuses_six(dataset, h99, xu100):
    assert all(r.f6 is not None and r.refusal is None for r in h99.values()) and len(h99) == 99
    records, sha = xu100
    cal_a = m20.load_calendar_a()
    refused = {r.ticker: m20.market20(r.first_trading_date, cal_a, records, xu100_sha256=sha) for r in dataset.rows}
    assert {t for t, x in refused.items() if x.refusal} == A6
    assert {x.refusal for t, x in refused.items() if t in A6} == {m20.INSUFFICIENT_HISTORY}
    f6 = sorted(float(r.f6) for r in h99.values())
    assert (round(f6[0], 4), round(f6[49], 3), round(f6[-1], 4)) == (-0.1117, 0.023, 0.1548)
    # T − S0: 1–3 gün, en erken S20 2023-08-23 (m3_cikti.txt:3)
    assert {(date.fromisoformat(x.ref_date) - date.fromisoformat(x.S0_date)).days for x in h99.values()} <= {1, 2, 3}
    assert min(x.S20_date for x in h99.values()) == "2023-08-23"


# ---------------------------------------------------------------- 2. legacy paritesi

def test_2_parity_with_legacy_repair_01_core(dataset, h99, cal_b, xu100):
    legacy_import()
    from scripts.modeling import v2_market20_repair_01_core as core

    closes = core.load_xu100_closes(m20.XU100_PATH)
    for r in dataset.rows:
        _, s0, s20 = core.s0_s20_from_calendar(list(cal_b.sessions), r.first_trading_date)
        assert core.materialize_market20_raw(closes[s0], closes[s20]) == h99[r.ticker].f6, r.ticker
        assert (s0, s20) == (h99[r.ticker].S0_date, h99[r.ticker].S20_date)
    # Düzeltilen hata: legacy takvim sonunu denetlemiyor
    assert core.s0_s20_from_calendar(list(cal_b.sessions), "2026-09-30")[1] == "2026-08-19"


# ---------------------------------------------------------------- 3. takvim sonu

def test_3_calendar_end(cal_b, xu100):
    records, sha = xu100
    assert m20.market20("2026-09-30", cal_b, records).refusal == m20.CALENDAR_NOT_COVERING
    ok = m20.market20("2026-08-20", cal_b, records)
    assert ok.refusal is None and ok.S0_date == "2026-08-19"
    assert m20.market20("2026-08-21", cal_b, records).refusal == m20.CALENDAR_NOT_COVERING


# ---------------------------------------------------------------- 4. pencere içi eksik

def test_4_missing_close_inside_window(dataset, cal_b, xu100, h99):
    records, _ = xu100
    t = dataset.by_ticker()["QUICK"]
    x = h99["QUICK"]
    i = cal_b.sessions.index(x.S0_date)
    middle = cal_b.sessions[i - 10]
    thinned = [r for r in records if r.date != middle]
    assert x.S0_date in {r.date for r in thinned} and x.S20_date in {r.date for r in thinned}
    assert m20.market20(t.first_trading_date, cal_b, thinned).refusal == m20.XU100_CLOSE_MISSING
    assert m20.market20("2023-02-20", cal_b, records).refusal == m20.XU100_CLOSE_MISSING


# ---------------------------------------------------------------- 5. bayat S0

def test_5_stale_s0(cal_b, xu100):
    records, _ = xu100
    last = date.fromisoformat(cal_b.last_date)
    extra = [((last + timedelta(days=k)).isoformat(), False) for k in range(1, 14)]  # 13 gün tam kapanış
    cal = cal_b.extended(extra, "B+13_KAPANIS")
    ref = (last + timedelta(days=14)).isoformat()
    assert m20.market20(ref, cal, records).refusal == m20.STALE_S0
    ref12 = (last + timedelta(days=12)).isoformat()
    assert m20.market20(ref12, cal, records).refusal is None


# ---------------------------------------------------------------- 6. as_of

def test_6_as_of_guard(dataset, cal_b, xu100, h99):
    records, _ = xu100
    for tk in ("QUICK", "EKOS", "HATSN"):
        ref = dataset.by_ticker()[tk].first_trading_date
        future = date.fromisoformat(ref)
        poison = [m20.XU100Record((future + timedelta(days=k)).isoformat(), "XU100", Decimal("1e9")) for k in range(0, 40)]
        poison.append(m20.XU100Record(ref, "XHARZ", Decimal("-1")))
        assert m20.market20(ref, cal_b, records + poison).f6 == h99[tk].f6


# ---------------------------------------------------------------- 7. bütünlük

def test_7_integrity(dataset, cal_b, xu100, h99):
    records, _ = xu100
    ref = dataset.by_ticker()["QUICK"].first_trading_date
    s0 = h99["QUICK"].S0_date
    xharz = records + [m20.XU100Record("2026-01-05", "XHARZ", Decimal("100"))]
    assert m20.market20(ref, cal_b, xharz).refusal == m20.XU100_INTEGRITY
    conflict = records + [m20.XU100Record(s0, "XU100", Decimal("1"))]
    assert m20.market20(ref, cal_b, conflict).refusal == m20.XU100_INTEGRITY
    nonpos = records + [m20.XU100Record("2026-01-06", "XU100", Decimal("0"))]
    assert m20.market20(ref, cal_b, [r for r in nonpos if r.date != "2026-01-06" or r.close == 0]).refusal == m20.XU100_INTEGRITY
    with pytest.raises(m20.Market20IntegrityError):
        m20.closes_by_date(xharz)
    # Pinli dosyanın tamamı kural 6'yı geçer
    assert len(m20.closes_by_date(records)) == 9682


# ---------------------------------------------------------------- 8. fold kimliği

def test_8_fold_identity_equals_v15_golden(backtest_results):
    golden = {r["fold_id"]: r for r in rc.read_csv(bt.GOLDEN_DIR / bt.golden_filename("v1_5_h99"))}
    ledger = backtest_results["v1_5_market20_v0"].ledger
    assert len(ledger) == 351
    assert sum(r["training_tickers_sha256"] == golden[r["fold_id"]]["training_tickers_sha256"] for r in ledger) == 351


# ---------------------------------------------------------------- 9. tek değişken

COMPARED = ("ridge_status", "ridge_selected_alpha", "ridge_columns", "ridge_score_table", "ridge_prediction",
            "logit_status", "logit_selected_C", "logit_columns", "logit_score_table", "logit_probability",
            "logit_predicted_class", "logit_tuning_status", "ridge_tuning_status")


def test_9_constant_f6_reproduces_v1_5_golden(dataset):
    spec = MODEL_SPECS["v1_5_market20_v0"]
    folds = [f for f in bt.plan_folds(dataset) if f.status == bt.SCORABLE]
    from borsai.fit import model_raw_features

    raw, _ = model_raw_features(spec, list(dataset.rows))
    const = {t: {**v, "f6": Decimal("0.0123")} for t, v in raw.items()}
    parts = bt._run_linear(spec, dataset, folds, bt.default_workers(), const)
    golden = rc.read_csv(bt.GOLDEN_DIR / bt.golden_filename("v1_5_h99"))
    assert len(parts) == len(golden) == 351
    for part, g in zip(parts, golden):
        for k in COMPARED:
            assert bt._fmt(part[k]) == g[k], (g["fold_id"], k)


# ---------------------------------------------------------------- 10. predict

def _inputs(row, f6):
    return {**row.feature_inputs(), "total_demand_filter_status": row.total_demand_filter_status, "f6_market20": f6}


def test_10_predict_refusals_and_warnings(dataset, h99):
    params = frozen("v1_5_market20_v0")
    row = dataset.by_ticker()["QUICK"]
    for code in ("CALENDAR_NOT_COVERING", "STALE_S0", None):
        out = pm.predict(params, {**_inputs(row, None), "f6_market20_refusal": code})
        assert out["refused"]["code"] == "MARKET20_" + (code or "NOT_PROVIDED")
        assert all(out[h] is None for h in ("D1", "D3", "D5", "D10"))
    assert pr.predict(params, row.feature_inputs())["refused"]["code"] == pr.REFUSED_FEATURE_NOT_PROVIDED
    out = pm.predict(params, {**_inputs(row, str(h99["QUICK"].f6)), "total_demand_multiple": None})
    assert out["refused"]["code"] == pr.REFUSED_F3_MISSING
    out = pm.predict(params, _inputs(row, "0.3"))
    assert out["refused"] is None
    assert [w["feature"] for w in out["warnings"] if w["code"] == pr.WARN_OUT_OF_TRAINING_RANGE] == ["f6"]
    ok = pm.predict(params, _inputs(row, str(h99["QUICK"].f6)))
    assert ok["refused"] is None and ok["f6_market20"] == float(h99["QUICK"].f6)
    assert [w for w in ok["warnings"] if w["code"] != pr.WARN_RETURN_CLIPPED] == []


def test_10_json_matches_sklearn_99_rows(dataset, h99):
    spec = MODEL_SPECS["v1_5_market20_v0"]
    _, fits = refit("v1_5_market20_v0")
    params = frozen("v1_5_market20_v0")
    assert params["preprocessing"]["columns"] == ["f1", "f2", "f3", "f4", "f5", "f6"]
    compared = refused = 0
    for row in dataset.rows:
        out = pm.predict(params, _inputs(row, str(h99[row.ticker].f6)))
        for h in ("D1", "D3", "D5", "D10"):
            hf = fits[h]
            x = np.array([hf.final.matrix_rows([row.ticker])[0]], dtype=np.float64)
            r_sk, p_sk = float(hf.ridge.estimator.predict(x)[0]), float(hf.logit.estimator.predict_proba(x)[0][1])
            if row.inputs["total_demand_multiple"] is None:
                assert out["refused"]["code"] == pr.REFUSED_F3_MISSING
                refused += 1
                continue
            assert abs(out[h]["return_unclipped"] - r_sk) <= 1e-12 and abs(out[h]["p_up"] - p_sk) <= 1e-12, (row.ticker, h)
            compared += 1
    assert compared == 97 * 4 and refused == 2 * 4


# ---------------------------------------------------------------- 11. revizyon denetimi

def test_11_revision_check(xu100):
    records, _ = xu100
    appended = records + [m20.XU100Record("2026-08-20", "XU100", Decimal("14500.12"))]
    m20.check_revision(records, appended)
    changed = [m20.XU100Record(r.date, r.index_name, r.close + Decimal("0.01")) if r.date == "2025-06-02" else r for r in records]
    with pytest.raises(m20.Market20IntegrityError):
        m20.check_revision(records, changed)
    with pytest.raises(m20.Market20IntegrityError):
        m20.check_revision(records, [r for r in records if r.date != "2024-01-02"])

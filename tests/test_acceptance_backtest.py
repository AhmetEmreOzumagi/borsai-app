"""Faz 1A kabul testleri 1-4 (AUDIT §3a): port H99 benchmark'ını yeniden üretir.

1. Fold kurulumu: 351 fold'un training_tickers_sha256'sı V15B ledger'ıyla 351/351.
2. Fold tahminleri toleranslı: α 351/351, C ≥ 350/351, |Δ Ridge| ≤ 1e-12,
   |Δ Logit p| ≤ 1e-7; tek beklenen sapma adıyla D3|BETAE.
3. Metrikler: 4 ufuk × Ridge/Logit ve n'ler; beş BLB kuralı.
4. macOS altın ledger'ı: birebir (bayt) regresyon.
"""
from __future__ import annotations

import json
from collections import Counter

import pytest

from borsai import backtest as bt
from borsai import metrics as mx
from borsai.fit import STATUS_FIT_OK, STATUS_NOT_CONVERGED
from borsai.horizons import HORIZONS
from borsai.provenance import sha256_file

import refcompare as rc

EXPECTED_SCORABLE = {"D1": 89, "D3": 88, "D5": 87, "D10": 87}
EXPECTED_INSUFFICIENT = {"D1": 10, "D3": 11, "D5": 12, "D10": 12}


@pytest.fixture(scope="module")
def v15(backtest_results):
    return backtest_results["v1_5_h99"]


@pytest.fixture(scope="module")
def ref_ledger():
    return rc.v15b_ledger()


@pytest.fixture(scope="module")
def comparison(v15, ref_ledger):
    return rc.compare_v15_folds(v15.ledger, ref_ledger)


# ---------------------------------------------------------------- 1. fold kurulumu

def test_1_fold_plan_counts(v15):
    by_h = Counter((f.horizon, f.status) for f in v15.folds)
    for h in HORIZONS:
        assert by_h[(h, bt.SCORABLE)] == EXPECTED_SCORABLE[h]
        assert by_h[(h, bt.INSUFFICIENT)] == EXPECTED_INSUFFICIENT[h]
    assert len(v15.ledger) == 351


def test_1_training_tickers_sha256_351_of_351(v15, ref_ledger, comparison):
    assert {r["fold_id"] for r in v15.ledger} == set(ref_ledger)
    assert comparison["folds"] == 351
    assert comparison["tickers_sha_equal"] == 351
    # Ek: eğitim hedeflerinin kimliği (ticker|seans|R_h|Y_h) de aynı.
    assert comparison["targets_sha_equal"] == 351


def test_1_fold_metadata_equal(comparison):
    assert comparison["other_differ"] == []


# ---------------------------------------------------------------- 2. fold tahminleri

def test_2_alpha_351_of_351(comparison):
    assert comparison["alpha_equal"] == 351


def test_2_C_at_least_350_and_only_named_deviation(comparison):
    assert comparison["C_equal"] >= 350
    assert comparison["C_differ"] == [rc.DEVIATION_FOLD]


def test_2_status_only_named_deviation(comparison, v15):
    assert comparison["status_differ"] == [(rc.DEVIATION_FOLD, "logit", STATUS_NOT_CONVERGED, STATUS_FIT_OK)]
    row = next(r for r in v15.ledger if r["fold_id"] == rc.DEVIATION_FOLD)
    assert row["logit_probability"] is None and row["logit_selected_C"] is None
    assert rc.DEVIATION_FOLD in rc.EXPECTED_DEVIATIONS


def test_2_ridge_predictions_within_1e12(comparison):
    assert comparison["max_ridge_delta"] <= rc.TOL_RIDGE
    assert comparison["max_ridge_score_delta"] <= rc.TOL_RIDGE


def test_2_logit_probabilities_within_1e7(comparison):
    assert comparison["max_logit_delta"] <= rc.TOL_LOGIT
    assert comparison["max_logit_score_delta"] <= rc.TOL_LOGIT


def test_2_f3_filter_inert_on_h99(v15):
    """AUDIT §1.2-j: H99'da tam 'FILTERED' yok; filtre hiçbir fold'da (iç ve dış) f3 boşaltmaz."""
    assert all(r["f3_filter_nulled_n"] == 0 for r in v15.ledger)


# ---------------------------------------------------------------- 3. metrikler

def _cmp(mine: dict, ref_row: dict, fields: dict, tol: float) -> None:
    assert mine["n"] == int(ref_row["n_oos"])
    for ours, theirs in fields.items():
        assert abs(mine[ours] - float(ref_row[theirs])) <= tol, (ours, mine[ours], ref_row[theirs])


def test_3_metric_definitions_reproduce_reference_summary(ref_ledger):
    """Metrik tanımları, Windows ledger'ına uygulanınca Windows özetini aynen verir."""
    summary = rc.read_csv(rc.V15B_SUMMARY)
    rows = list(ref_ledger.values())
    for s in summary:
        hl = [r for r in rows if r["horizon"] == s["horizon"]]
        if s["model_id"] == "V1_RIDGE":
            pts = rc.regression_points_from_ref([r for r in hl if r["ridge_status"] == "FIT_OK"], "ridge_point_prediction_return")
            got = mx.windowed(pts, mx.regression_metrics)[s["reporting_window"]]
            _cmp(got, s, rc.REG_FIELDS, 0.0)
        else:
            pts = rc.classification_points_from_ref([r for r in hl if r["logistic_status"] == "FIT_OK"],
                                                    "logistic_probability_above_ipo_raw", "logistic_predicted_direction")
            got = mx.windowed(pts, mx.classification_metrics)[s["reporting_window"]]
            _cmp(got, s, rc.CLS_FIELDS, 0.0)


def test_3_v15_metrics_8_cells_and_windows(v15, ref_ledger):
    summary = rc.read_csv(rc.V15B_SUMMARY)
    assert len(summary) == 32
    for s in summary:
        h, w = s["horizon"], s["reporting_window"]
        if s["model_id"] == "V1_RIDGE":
            _cmp(v15.metrics[h]["return"][w], s, rc.REG_FIELDS, rc.TOL_RIDGE)
        elif h == "D3":
            # Adıyla sapma: beklenen değer, Windows ledger'ından D3|BETAE çıkarılarak hesaplanır.
            ref_rows = [r for k, r in ref_ledger.items()
                        if r["horizon"] == "D3" and r["logistic_status"] == "FIT_OK" and k != rc.DEVIATION_FOLD]
            expected = mx.windowed(rc.classification_points_from_ref(
                ref_rows, "logistic_probability_above_ipo_raw", "logistic_predicted_direction"), mx.classification_metrics)[w]
            mine = v15.metrics[h]["p_up"][w]
            if w == "ALL":
                assert int(s["n_oos"]) == 81 and mine["n"] == 80
            assert mine["n"] == expected["n"]
            for k in rc.CLS_FIELDS:
                assert abs(mine[k] - expected[k]) <= rc.TOL_LOGIT, (w, k)
        else:
            _cmp(v15.metrics[h]["p_up"][w], s, rc.CLS_FIELDS, rc.TOL_LOGIT)


def test_3_headline_values(v15):
    assert v15.metrics["D1"]["return"]["ALL"]["mae"] == pytest.approx(0.029704488696585943, abs=rc.TOL_RIDGE)
    assert [v15.metrics[h]["return"]["ALL"]["n"] for h in HORIZONS] == [89, 88, 87, 87]
    assert [v15.metrics[h]["p_up"]["ALL"]["n"] for h in HORIZONS] == [80, 80, 81, 81]


def test_3_blb_fold_predictions_identical(backtest_results):
    blb = rc.blb_ledger()
    majority = [r for r in blb if r["baseline_id"] == "V1_BASE_MAJORITY"]
    assert majority and all(r["baseline_probability_above_ipo_raw"] == "1" and r["baseline_predicted_direction"] == "1"
                            for r in majority)
    ours = {m: {r["fold_id"]: r for r in backtest_results[m].ledger} for m, _ in rc.BLB_TO_BORSAI.values()}
    checked = Counter()
    for r in blb:
        model, output = rc.BLB_TO_BORSAI[r["baseline_id"]]
        k = f"{r['horizon']}|{r['ticker']}"
        mine = ours[model][k]
        assert mine["training_tickers_sha256"] == r["training_tickers_sha256"]
        if output == "return":
            assert mine["rule_return"] == float(r["baseline_point_prediction_return"]), (model, k)
        else:
            assert mine["rule_p_up"] == float(r["baseline_probability_above_ipo_raw"]), (model, k)
            assert mine["rule_direction"] == int(r["baseline_predicted_direction"]), (model, k)
        checked[r["baseline_id"]] += 1
    assert set(checked.values()) == {351}


def test_3_blb_metrics(backtest_results, v15):
    """Beş BLB kuralının özet değerleri (ör. TRAIN_MEDIAN D1 MAE 0.025107817206684563,
    BASE_RATE D1 Brier 0.10215057076590381), aynı toleransla."""
    summary = rc.read_csv(rc.BLB_SUMMARY)
    blb = rc.blb_ledger()
    ridge_ok = {r["fold_id"] for r in v15.ledger if r["ridge_status"] == STATUS_FIT_OK}
    logit_ok = {r["fold_id"] for r in v15.ledger if r["logit_status"] == STATUS_FIT_OK}
    for s in summary:
        model, output = rc.BLB_TO_BORSAI[s["baseline_id"]]
        h, w, eval_set = s["horizon"], s["reporting_window"], s["evaluation_set"]
        rows = [r for r in backtest_results[model].ledger if r["horizon"] == h]
        if eval_set == "V1_RIDGE_MATCHED_SCORABLE_SET":
            rows = [r for r in rows if r["fold_id"] in ridge_ok]
        elif eval_set == "V1_LOGIT_MATCHED_FITTED_SET":
            rows = [r for r in rows if r["fold_id"] in logit_ok]
        if output == "return":
            pts = bt._regression_points(rows, "rule_return", lambda r: True)
            _cmp(mx.windowed(pts, mx.regression_metrics)[w], s, rc.REG_FIELDS, rc.TOL_RIDGE)
            continue
        mine = mx.windowed(bt._classification_points(rows, "rule_p_up", "rule_direction", lambda r: True),
                           mx.classification_metrics)[w]
        if eval_set == "V1_LOGIT_MATCHED_FITTED_SET" and h == "D3":
            ref_rows = [r for r in blb if r["baseline_id"] == s["baseline_id"] and r["horizon"] == "D3"
                        and r["in_v1_5_logistic_matched_fitted_set"] == "TRUE" and r["ticker"] != "BETAE"]
            expected = mx.windowed(rc.classification_points_from_ref(
                ref_rows, "baseline_probability_above_ipo_raw", "baseline_predicted_direction"), mx.classification_metrics)[w]
            assert mine["n"] == expected["n"]
            for k in rc.CLS_FIELDS:
                assert abs(mine[k] - expected[k]) <= rc.TOL_LOGIT
        else:
            _cmp(mine, s, rc.CLS_FIELDS, rc.TOL_LOGIT)


# ---------------------------------------------------------------- 4. macOS altın ledger

def test_4_golden_files_intact():
    sums = (bt.GOLDEN_DIR / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    manifest = json.loads((bt.GOLDEN_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    assert len(sums) == len(manifest["models"]) == 7
    for line in sums:
        sha, name = line.split("  ")
        assert sha256_file(bt.GOLDEN_DIR / name) == sha
        model_id = name.removesuffix("_fold_ledger.csv")
        assert manifest["models"][model_id]["ledger_sha256"] == sha


def test_4_backtest_byte_identical_to_golden(backtest_results):
    # Faz 1A altın dizinindeki modeller; Faz 1B koşuları tests/test_faz1b_backtest.py'de.
    manifest = json.loads((bt.GOLDEN_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    for model_id in manifest["models"]:
        res = backtest_results[model_id]
        golden = (bt.GOLDEN_DIR / bt.golden_filename(model_id)).read_bytes()
        assert res.ledger_csv == golden, model_id

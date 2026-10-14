"""Windows referans ledger'larıyla karşılaştırma yardımcıları (testler ve rapor).

Referanslar (tests/reference/, docs/PROVENANCE.md §4):
- V15B: HISTORICAL99_FROZEN_V1_5_BENCHMARK_V1 (Windows, Python 3.12.13).
- BLB : HISTORICAL99_PREDEFINED_BASELINE_BENCHMARK_V1 (aynı fold'lar).

Toleranslar ve adıyla yazılmış tek beklenen sapma AUDIT §1.2-b / §3a'dan gelir.
"""
from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path

from borsai import metrics as mx

REF = Path(__file__).resolve().parent / "reference"
V15B_LEDGER = REF / "v1_5_benchmark" / "HISTORICAL99_V1_5_outer_fold_prediction_ledger.csv"
V15B_SUMMARY = REF / "v1_5_benchmark" / "HISTORICAL99_V1_5_horizon_metric_summary.csv"
BLB_LEDGER = REF / "baseline_benchmark" / "HISTORICAL99_predefined_baseline_fold_ledger.csv"
BLB_SUMMARY = REF / "baseline_benchmark" / "HISTORICAL99_predefined_baseline_metric_summary.csv"

TOL_RIDGE = 1e-12
TOL_LOGIT = 1e-7

# Adıyla yazılmış beklenen sapma (AUDIT §1.2-b). Başka her sapma testi düşürür.
EXPECTED_DEVIATIONS = {
    "D3|BETAE": (
        "Logit: bu makinede (macOS arm64, Python 3.12.14, aynı paket sürümleri) iç LOOCV'de lbfgs "
        "yakınsamıyor -> MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE; Windows ledger'ında FIT_OK, C = 1, "
        "p = 0.99178712098749289. Legacy kod da bu makinede aynı sonucu veriyor (AUDIT §1.2-b, "
        "tests/reference/q3a_macos_yeniden_kosu_cikti.json). Sonuç: D3 Logit n'i 81 -> 80."
    ),
}
DEVIATION_FOLD = "D3|BETAE"

# BLB kural adı -> borsai modeli ve çıktısı.
BLB_TO_BORSAI = {
    "V1_BASE_ZERO": ("base_zero", "return"),
    "V1_BASE_MEDIAN": ("base_train_median", "return"),
    "V1_BASE_MEAN": ("base_train_mean", "return"),
    "V1_BASE_RATE": ("base_rate", "p_up"),
    # MAJORITY H99'da her fold'da sınıf 1'dir (testte doğrulanır); olasılığı 1.0,
    # yönü UP: ALWAYS_CEILING'in p_up çıktısıyla aynı kural.
    "V1_BASE_MAJORITY": ("base_always_ceiling", "p_up"),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def fold_key(fold_id: str) -> str:
    """'HISTORICAL99_FROZEN_V1_5_BENCHMARK_V1|D1|EKOS' -> 'D1|EKOS'."""
    parts = fold_id.split("|")
    return f"{parts[-2]}|{parts[-1]}"


def v15b_ledger() -> dict[str, dict[str, str]]:
    return {fold_key(r["fold_id"]): r for r in read_csv(V15B_LEDGER)}


def blb_ledger() -> list[dict[str, str]]:
    return read_csv(BLB_LEDGER)


def f(value: str):
    return None if value == "" else float(value)


def regression_points_from_ref(rows, pred_key: str) -> list[mx.RegressionPoint]:
    return [
        mx.RegressionPoint(
            ticker=r["ticker"], prediction_date=r["prediction_date"], predicted=float(r[pred_key]),
            actual=float(r["realized_target_return"]), ipo_price=Decimal(r["ipo_price"]),
            actual_close=Decimal(r["official_close"]),
        )
        for r in rows
    ]


def classification_points_from_ref(rows, p_key: str, dir_key: str) -> list[mx.ClassificationPoint]:
    return [
        mx.ClassificationPoint(
            ticker=r["ticker"], prediction_date=r["prediction_date"], probability=float(r[p_key]),
            direction=int(r[dir_key]), actual=int(r["realized_direction"]),
        )
        for r in rows
    ]


REG_FIELDS = {
    "mae": "mae_return_space",
    "median_ae": "median_ae_return_space",
    "rmse": "rmse_return_space",
    "mape_price_level_pct": "mape_price_level_pct",
    "median_ape_price_level_pct": "median_ape_price_level_pct",
}
CLS_FIELDS = {"accuracy": "above_ipo_accuracy", "brier": "brier_score_reporting_clip", "log_loss": "log_loss_reporting_clip"}


def compare_v15_folds(ours: list[dict], ref: dict[str, dict[str, str]]) -> dict:
    """Fold düzeyi karşılaştırma; ölçülen farkları ve sapmaları döndürür."""
    out = {
        "folds": 0, "alpha_equal": 0, "C_equal": 0, "C_differ": [], "status_differ": [],
        "max_ridge_delta": 0.0, "max_ridge_delta_fold": None, "ridge_differ_n": 0,
        "max_logit_delta": 0.0, "max_logit_delta_fold": None, "logit_differ_n": 0,
        "max_ridge_score_delta": 0.0, "max_logit_score_delta": 0.0, "other_differ": [],
        "tickers_sha_equal": 0, "targets_sha_equal": 0,
    }
    for r in ours:
        k = r["fold_id"]
        o = ref[k]
        out["folds"] += 1
        out["tickers_sha_equal"] += r["training_tickers_sha256"] == o["training_tickers_sha256"]
        out["targets_sha_equal"] += r["training_targets_sha256"] == o["training_targets_sha256"]
        for mine, theirs in (("training_n", "training_n"), ("n_chronological_train", "n_chronological_train"),
                             ("ridge_tuning_status", "ridge_tuning_status"), ("ridge_inner_fold_n", "ridge_inner_fold_n"),
                             ("logit_n_class_0", "logistic_n_class_0"), ("logit_n_class_1", "logistic_n_class_1"),
                             ("target_session_date", "target_session_date"), ("prediction_date", "prediction_date")):
            if str(r[mine]) != o[theirs]:
                out["other_differ"].append((k, mine, r[mine], o[theirs]))
        if json.loads(r["ridge_columns"]) != json.loads(o["ridge_active_features_json"]):
            out["other_differ"].append((k, "ridge_columns"))
        if r["ridge_status"] != o["ridge_status"]:
            out["status_differ"].append((k, "ridge", r["ridge_status"], o["ridge_status"]))
        if r["ridge_selected_alpha"] == f(o["ridge_selected_alpha"]):
            out["alpha_equal"] += 1
        d = abs(r["ridge_prediction"] - float(o["ridge_point_prediction_return"]))
        out["ridge_differ_n"] += d != 0
        if d > out["max_ridge_delta"]:
            out["max_ridge_delta"], out["max_ridge_delta_fold"] = d, k
        for mine_e, ref_e in zip(json.loads(r["ridge_score_table"]), json.loads(o["ridge_candidate_score_table_json"])):
            if mine_e["hyperparameter"] != ref_e["hyperparameter"]:
                out["other_differ"].append((k, "ridge_score_grid"))
            out["max_ridge_score_delta"] = max(out["max_ridge_score_delta"], abs(mine_e["score"] - ref_e["score"]))

        if r["logit_status"] != o["logistic_status"]:
            out["status_differ"].append((k, "logit", r["logit_status"], o["logistic_status"]))
        if r["logit_selected_C"] == f(o["logistic_selected_C"]):
            out["C_equal"] += 1
        else:
            out["C_differ"].append(k)
        if r["logit_status"] == o["logistic_status"]:
            if r["logit_tuning_status"] != o["logistic_tuning_status"]:
                out["other_differ"].append((k, "logit_tuning_status"))
            if json.loads(r["logit_columns"]) != json.loads(o["logistic_active_features_json"]):
                out["other_differ"].append((k, "logit_columns"))
            if r["logit_probability"] is not None:
                d = abs(r["logit_probability"] - float(o["logistic_probability_above_ipo_raw"]))
                out["logit_differ_n"] += d != 0
                if d > out["max_logit_delta"]:
                    out["max_logit_delta"], out["max_logit_delta_fold"] = d, k
                if str(r["logit_predicted_class"]) != o["logistic_predicted_direction"]:
                    out["other_differ"].append((k, "logit_predicted_class"))
            for mine_e, ref_e in zip(json.loads(r["logit_score_table"]), json.loads(o["logistic_candidate_score_table_json"])):
                out["max_logit_score_delta"] = max(out["max_logit_score_delta"], abs(mine_e["score"] - ref_e["score"]))
    return out

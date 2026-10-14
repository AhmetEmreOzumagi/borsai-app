"""Kayıtlı model şartnameleri. Yalnız stdlib.

CLAUDE.md kural 5: özellik, ön işleme, ızgara, eğitim kesimi ya da veri sürümü
değişirse yeni model_id. Şartname bu alanların hepsini içerir; `spec_sha256`
kanonik JSON'unun hash'idir. `fit` veri sürümü şartnameyle tutmazsa durur.

Bu dosyadaki bir şartname değiştirilmez; değişiklik yeni model_id ile eklenir.
"""
from __future__ import annotations

import copy
from typing import Any

from .features import FEATURE_IDS, FEATURE_VERSION, PB_FEATURE_VERSION
from .horizons import HORIZONS
from .predict_fall import FALL_ALGORITHM, FAMILY_FALL, TARGET_DEFINITION
from .preprocess import (CEILING_RECIPE, CEILING_V1_CLIP_RECIPE, CEILING_V1_REAL_RECIPE, FALL_V0_ADDSALE_RECIPE, FALL_V0_RECIPE,
                         MARKET20_RECIPE, PB_CEILING_RECIPE, PB_RECIPE, PREPROCESSING_ID)
from .provenance import canonical_sha256

SCHEMA_VERSION = "borsai.model/1"

# data/data_version.json dosyasının sha256'sı (tablo + beş kaynak + üretici).
H99_DATA_VERSION_SHA256 = "a0c7d082dacdbde03f53d1c4af1ce9f7983f9946abc80062de570f4a1df1f977"

H99_TRAINING = {
    "set": "H99_ALL_ROWS",
    "description": "data/training_table.csv'nin 99 satırının hepsi, tablo sırasıyla (first_trading_date, ticker)",
    "n": 99,
    "data_version_sha256": H99_DATA_VERSION_SHA256,
}

RUNTIME_PINS = {
    "python": "3.12",
    "scikit-learn": "1.9.0",
    "numpy": "2.5.2",
    "scipy": "1.18.0",
    "joblib": "1.5.3",
    "threadpoolctl": "3.6.0",
}

V1_5_H99: dict[str, Any] = {
    "model_id": "v1_5_h99",
    "algorithm": "V1_5_RIDGE_LOGIT",
    "description": "V1.5 (BORSAI_V1_5_PREREG_20260814) portu: ufuk başına Ridge (getiri) ve L2-lojistik (P(kapanış > arz)), f1–f5, fold içi V1.3 ön işleme, iç LOOCV ile hiperparametre seçimi.",
    "legacy_identity": "BORSAI_V1_5_PREREG_20260814",
    "legacy_spec_sha256": "1245bf0f96c63cabdbd740cf043e9f3c58f8fc50af48472933c29e05dce211b1",
    "features": list(FEATURE_IDS),
    "feature_version": FEATURE_VERSION,
    "preprocessing_id": PREPROCESSING_ID,
    "horizons": list(HORIZONS),
    "min_train_n": 10,
    "ridge": {
        "estimator": "sklearn.linear_model.Ridge",
        "alpha_grid": [0.1, 1.0, 10.0, 100.0],
        "fit_intercept": True,
        "solver": "svd",
        "tuning": "INNER_LOOCV_MAE_RETURN_SPACE",
        "tie_break": "BIT_EXACT_TIE_TO_LARGEST_ALPHA",
    },
    "logit": {
        "estimator": "sklearn.linear_model.LogisticRegression",
        "C_grid": [0.01, 0.1, 1.0, 10.0],
        "l1_ratio": 0.0,
        "solver": "lbfgs",
        "fit_intercept": True,
        "class_weight": None,
        "max_iter": 10000,
        "tol": 1e-10,
        "tuning": "INNER_LOOCV_RAW_UNCLIPPED_BRIER",
        "tie_break": "BIT_EXACT_TIE_TO_SMALLEST_C",
        "minority_lt_2_policy": "NO_TUNING_FIXED_C_0.01",
        "single_class_policy": "MODEL_NOT_FIT_SINGLE_CLASS",
        "non_convergence_policy": "MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE",
        "direction_rule": "UP iff p > 0.5",
    },
    "training": H99_TRAINING,
    "input_policy": {
        "f3_missing": "REFUSE",
        "f3_missing_reason": "AUDIT §1.2-d: f5 katsayısı yalnız 2 gözlemden (ALBTN, ENDAE) öğrenildi; f3'süz çağrı 'talep bilgisi henüz yok' durumunu 'hiç gelmedi' diye okur.",
        "f3_filter_status_conflict": "REFUSE",
        "out_of_training_range": "WARN",
        "return_output": "CLIP_TO_PHYSICAL_BOUNDS_AND_FLAG",
    },
    "runtime_pins": RUNTIME_PINS,
}

_RULE_BASE: dict[str, Any] = {
    "features": [],
    "horizons": list(HORIZONS),
    "min_train_n": 10,
    "training": H99_TRAINING,
    "input_policy": {"required_inputs": ["ipo_price_tl"], "return_output": "CLIP_TO_PHYSICAL_BOUNDS_AND_FLAG"},
}


def _rule(model_id: str, algorithm: str, description: str, *, uses_training: bool, outputs: list[str]) -> dict[str, Any]:
    spec = copy.deepcopy(_RULE_BASE)
    spec.update({"model_id": model_id, "algorithm": algorithm, "description": description, "outputs": outputs})
    if not uses_training:
        spec["training"] = {"set": "NONE", "description": "kural eğitim verisi kullanmaz", "n": 0,
                            "data_version_sha256": H99_DATA_VERSION_SHA256}
    return spec


BASE_ALWAYS_CEILING = _rule(
    "base_always_ceiling", "ALWAYS_CEILING",
    "Her seans tavan: getiri = 1.1^h − 1; P(kapanış > arz) = 1.",
    uses_training=False, outputs=["return", "p_up"],
)
BASE_TRAIN_MEDIAN = _rule(
    "base_train_median", "TRAIN_MEDIAN",
    "Getiri = eğitimdeki R_h'lerin medyanı (legacy V1_BASE_MEDIAN).",
    uses_training=True, outputs=["return"],
)
BASE_TRAIN_MEAN = _rule(
    "base_train_mean", "TRAIN_MEAN",
    "Getiri = eğitimdeki R_h'lerin ortalaması (legacy V1_BASE_MEAN).",
    uses_training=True, outputs=["return"],
)
BASE_ZERO = _rule(
    "base_zero", "ZERO",
    "Getiri = 0 (legacy V1_BASE_ZERO).",
    uses_training=False, outputs=["return"],
)
BASE_RATE = _rule(
    "base_rate", "BASE_RATE",
    "P(kapanış > arz) = eğitimdeki Y_h ortalaması (legacy V1_BASE_RATE).",
    uses_training=True, outputs=["p_up"],
)
BASE_LAST10_RATE = _rule(
    "base_last10_rate", "LAST10_BASE_RATE",
    "P(kapanış > arz) = eğitim sırasındaki (first_trading_date, ticker) son 10 arzın Y_h ortalaması (AUDIT §3b).",
    uses_training=True, outputs=["p_up"],
)

# ---------------------------------------------------------------------------
# Faz 1B: Fable şartnameleri (docs/specs/, commit d3fabad). Şartname belgesi sha256'sı
# spec'e yazılır; belge değişirse spec_sha256 da değişir (tests/test_faz1b_specs.py).
# ---------------------------------------------------------------------------

SPEC_DOCUMENTS: dict[str, dict[str, str]] = {
    "SPEC_CEILING_V0": {"path": "docs/specs/SPEC_CEILING_V0.md",
                        "sha256": "d78cb234f6b3fedfd451ea5aafd31f14022d225ff4b981770868d45a963fc731"},
    "SPEC_PB_V0": {"path": "docs/specs/SPEC_PB_V0.md",
                   "sha256": "098805765ef1d7cff32bfa81cf42226c2c3c61d53c365bc4bafcc05558f3d81c"},
    "SPEC_MARKET20_V0": {"path": "docs/specs/SPEC_MARKET20_V0.md",
                         "sha256": "7aff795ffd92c642d06289f8b558c2e39203fec70610e39ffefd94e95e61938a"},
    "SPEC_V1_6": {"path": "docs/specs/SPEC_V1_6.md",
                  "sha256": "3901d4804b2ab9f7f0683915cc33d17425733cfc160eba5eb84e7d6549b26f8f"},
}

# Backtest planları (fold kuralı + bilgi kesimi). Faz 1A şartnamelerinde plan alanı yok;
# onların planı PLAN_V15'tir (borsai/backtest.py PLAN_ID ile aynı metin).
PLAN_V15 = "H99_WALK_FORWARD_STRICT_PRIOR_DATE_MIN_TRAIN_10"
PLAN_PB = "H99_PB_WALK_FORWARD_BOOKBUILD_CUTOFF_MIN_TRAIN_10"
PLAN_CEILING = "H99_CEILING_PP_WALK_FORWARD_T_CUTOFF_F3_PRESENT_MIN10IPO_5EV_5SV"
PLAN_PB_CEILING = "H99_PB_CEILING_PP_WALK_FORWARD_B_CUTOFF_MIN10IPO_5EV_5SV"
# Faz 4 (SPEC_CEILING_PATH_V0 §8): S_k kaynak tavan ledger'larından aynen; hücreler fold içinde walk-forward.
PLAN_CEILING_PATH = "H99_CEILING_PATH_T_CUTOFF_REUSE_CEILING_LEDGER"
PLAN_PB_CEILING_PATH = "H99_PB_CEILING_PATH_B_CUTOFF_REUSE_PB_CEILING_LEDGER"
PLAN_KEYS: dict[str, str] = {PLAN_V15: "v15", PLAN_PB: "pb", PLAN_CEILING: "ceiling", PLAN_PB_CEILING: "pb_ceiling",
                             PLAN_CEILING_PATH: "ceiling_path", PLAN_PB_CEILING_PATH: "pb_ceiling_path"}

H99_F3_TRAINING = {
    "set": "H99_F3_PRESENT",
    "description": "data/training_table.csv'nin total_demand_multiple dolu 97 satırı (ALBTN ve ENDAE hariç), tablo sırasıyla",
    "n": 97,
    "data_version_sha256": H99_DATA_VERSION_SHA256,
}
PB_SOURCE = {
    "path": "data/raw/PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv",
    "sha256": "5e52d4d23b4f196ef0fd44fb6d4f4edab0ea326241288b036952c30c5e24a613",
    "note": "data_version.json dışında; sha256 borsai/data.py PB_SHA256 ile denetlenir (SPEC_PB_V0 §1)",
}
MARKET20_SOURCES = {
    "calendar": {"path": "data/raw/v2_market20_official_pay_calendar_evidence_r4.csv",
                 "sha256": "49b58029715881a7f1a304afb7e41fcff3d5c1c7a8896de3ed9bb555fb02d159", "name": "Takvim B"},
    "xu100": {"path": "data/raw/official_bist_xu100_graphic_pinned_through_20260819.json",
              "sha256": "34859d7eefdb552a31f6476e2230a07a825ada3ee769a2a7646f12399c303fdf",
              "source_authority": "BORSA_ISTANBUL_OFFICIAL"},
}

_V1_6_RIDGE_ALPHA_GRID = [0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0, "INF"]
_V1_6_LOGIT_C_GRID = ["ZERO", 0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0]
_CANDIDATE_POLICY = "CANDIDATE_NOT_CONVERGED_DROPPED_FINAL_FIT_FALLS_BACK_TO_NEXT_RANKED"


def _v1_x(model_id: str, description: str) -> dict[str, Any]:
    spec = copy.deepcopy(V1_5_H99)
    for k in ("legacy_identity", "legacy_spec_sha256"):
        spec.pop(k)
    spec.update({"model_id": model_id, "description": description})
    return spec


def _v1_6_grid(spec: dict[str, Any], *, minority_policy: str) -> None:
    spec["grid_version"] = "v1_6"
    spec["ridge"].update({
        "alpha_grid": list(_V1_6_RIDGE_ALPHA_GRID),
        "tie_break": "BIT_EXACT_TIE_TO_LARGEST_ALPHA_INF_LARGEST",
        "endpoint_INF": "yalnız sabit terim: tahmin = eğitim hedeflerinin aritmetik ortalaması (statistics.mean), coef = 0; kapalı biçim",
    })
    spec["logit"].update({
        "C_grid": list(_V1_6_LOGIT_C_GRID),
        "tie_break": "BIT_EXACT_TIE_TO_SMALLEST_C_ZERO_SMALLEST",
        "endpoint_ZERO": "yalnız sabit terim: p = n_1/n, intercept = ln(p/(1 − p)), coef = 0; kapalı biçim",
        "non_convergence_policy": _CANDIDATE_POLICY,
        "minority_lt_2_policy": minority_policy,
    })


V1_6_H99 = _v1_x(
    "v1_6_h99",
    "V1.5 + genişletilmiş ızgara (SPEC_V1_6): Ridge α ∈ {0.001 … 10000, INF}, Logit C ∈ {ZERO, 0.0001 … 100}; "
    "INF/ZERO kapalı biçim sabit terim; aday başına yakınsamama. Özellikler, ön işleme ve fold planı V1.5 ile aynı.",
)
_v1_6_grid(V1_6_H99, minority_policy="NO_TUNING_FIXED_C_0.01")
V1_6_H99.update({"plan_id": PLAN_V15, "spec_document": SPEC_DOCUMENTS["SPEC_V1_6"]})

V1_5_MARKET20_V0 = _v1_x(
    "v1_5_market20_v0",
    "V1.5 aynen + f6 = XU100(S0)/XU100(S20) − 1 (20 seanslık endeks getirisi, Takvim B, ref_date = T; SPEC_MARKET20_V0). "
    "f6 impute edilmez; hesaplanamıyorsa RET.",
)
V1_5_MARKET20_V0.update({
    "features": list(FEATURE_IDS) + ["f6"],
    "preprocessing_id": MARKET20_RECIPE.recipe_id,
    "market20": {
        "definition": "i = bisect_left(seanslar, ref_date) − 1; S0 = seanslar[i]; S20 = seanslar[i − 20]; f6 = XU100[S0]/XU100[S20] − 1",
        "arithmetic": "Decimal, prec 60, ROUND_HALF_EVEN; XU100 json.loads(parse_float=Decimal)",
        "window_sessions": 20,
        "ref_date_backtest_and_fit": "first_trading_date (T)",
        "ref_date_live": "prediction_date (dondurma kaydının yerel tarihi, Europe/Istanbul)",
        "validity_rules": ["CALENDAR_NOT_COVERING", "INSUFFICIENT_HISTORY", "XU100_CLOSE_MISSING", "STALE_S0",
                           "PREDICTION_TOO_EARLY", "XU100_INTEGRITY", "AS_OF_STRICTLY_BEFORE_REF_DATE"],
        "max_stale_days": 12,
        "max_lead_days_live": 12,
        "preprocessing": "fold içi z-skor (popülasyon std); log, winsor, imputasyon, eksiklik göstergesi yok",
        "sources": MARKET20_SOURCES,
        "code": "borsai/market20.py",
    },
    "plan_id": PLAN_V15,
    "spec_document": SPEC_DOCUMENTS["SPEC_MARKET20_V0"],
})
V1_5_MARKET20_V0["input_policy"].update({
    "f6_missing": "REFUSE_WITH_MARKET20_REASON",
    "f6_imputation": "NONE",
    "f6_out_of_training_range": "WARN",
})

PB_V0 = _v1_x(
    "pb_v0",
    "Talep toplama öncesi model (SPEC_PB_V0): ufuk başına Ridge (getiri) ve L2-lojistik (P(kapanış > arz)), "
    "SPK onaylı planlanan yapıdan pb1–pb3, V1.6 ızgarası; bilgi kesimi ilk talep toplama günü B(k).",
)
_v1_6_grid(PB_V0, minority_policy="NO_TUNING_FIXED_C_ZERO")
PB_V0.update({
    "features": ["pb1", "pb2", "pb3"],
    "feature_version": PB_FEATURE_VERSION,
    "preprocessing_id": PB_RECIPE.recipe_id,
    "non_features": {"pb4": "planned_additional_sale_ceiling / planned_base_offer_shares × 100; yalnız doğrulama ve uyarı"},
    "sources": {"prebookbuild": PB_SOURCE},
    "information_cutoff": "first_bookbuilding_date (B(k)): eğitim satırı (j, h) ancak target_session_date(j, D_h) < B(k)",
    "plan_id": PLAN_PB,
    "spec_document": SPEC_DOCUMENTS["SPEC_PB_V0"],
    "input_policy": {
        "field_missing": "REFUSE PB_FIELD_MISSING:<alan>",
        "identity_or_range_violation": "REFUSE PB_IDENTITY:<ad>",
        "price_range": "REFUSE PB_PRICE_RANGE",
        "out_of_training_range": "WARN",
        "pb4_positive": "WARN",
        "return_output": "CLIP_TO_PHYSICAL_BOUNDS_AND_FLAG",
    },
})

_HAZARD_COMMON: dict[str, Any] = {
    "algorithm": "discrete_time_hazard_logit_l2",
    "outputs": ["hazard", "S", "P_L", "P_close_ceiling"],
    "days": 10,
    "day_groups": {"g1": [1], "g2": [2, 3], "g3": [4, 5, 6, 7, 8, 9, 10]},
    "model": "logit h_d(x) = gamma_{g(d)} + beta·z(x); S_k = prod_{d<=k}(1 - h_d)",
    "penalty": "L2 yalnız beta'da, (lambda/2)·||beta||²; gamma cezasız",
    "pseudo_rows": {"weight": 0.5, "rows": "her grup için z = 0'da bir event = 1 ve bir event = 0 satırı"},
    "solver": {"method": "NEWTON_RAPHSON_NUMPY", "init": "beta = 0, gamma_g = logit((olay_g + 0.5)/(risk_g + 1))",
               "grad_tol": 1e-10, "max_iter": 100, "max_halvings": 30,
               "descent_check": "J_new <= J_old + m·eps·max(|J_old|, 1) (toplama yuvarlama sınırı)",
               "non_convergence": "MODEL_NOT_FIT_DID_NOT_CONVERGE"},
    "lambda_grid": [0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, "INF"],
    "lambda_INF": "beta ≡ 0; gamma_g = logit((olay_g + 0.5)/(risk_g + 1))",
    "selection": {"method": "INNER_LEAVE_ONE_IPO_OUT", "preprocessing": "her iç bölmede kalan arzlardan yeniden kurulur",
                  "objective": "satır başına ortalama log-kayıp; h [1e-12, 1 − 1e-12]'ye kırpılır",
                  "tie_break": "BIT_EXACT_TIE_TO_LARGEST_LAMBDA_INF_LARGEST",
                  "non_convergence": "CANDIDATE_NOT_CONVERGED_DROPPED_INF_ALWAYS_KEPT"},
    "reclose": {"groups": {"a": [2, 3, 4], "b": [5, 6, 7, 8, 9, 10]}, "rate": "(a + 0.5)/(n + 1)",
                "P_close": "k = 1: S_1; k >= 2: S_k + (1 − S_k)·r_{b(k)}"},
    "scorability": {"min_ipo": 10, "min_events": 5, "min_survivals": 5},
    "min_train_n": 10,
    "runtime_pins": RUNTIME_PINS,
}


def _hazard(model_id: str, description: str, **fields: Any) -> dict[str, Any]:
    spec = copy.deepcopy(_HAZARD_COMMON)
    spec.update({"model_id": model_id, "description": description, **copy.deepcopy(fields)})
    return spec


CEILING_HAZARD_V0 = _hazard(
    "ceiling_hazard_v0",
    "Tavan serisi, ayrık zamanlı hazard (SPEC_CEILING_V0): 3 gün-grubu sabiti + f1 (ln arz büyüklüğü), f2 (halka açıklık), "
    "f3 (talep katı) katsayıları, L2 (λ iç arz-bırak CV ile). Çıktı S_k = P(seri ≥ k), k = 1..10.",
    features=["f1", "f2", "f3"],
    feature_version=FEATURE_VERSION,
    preprocessing_id=CEILING_RECIPE.recipe_id,
    training=H99_F3_TRAINING,
    plan_id=PLAN_CEILING,
    spec_document=SPEC_DOCUMENTS["SPEC_CEILING_V0"],
    input_policy={"f3_missing": "REFUSE", "f3_outside_train_p05_p95": "CLIP_AND_FLAG",
                  "out_of_training_range": "WARN", "invalid_f1_f2": "LABELED_REFUSAL"},
)
CEILING_HAZARD_V0_AT_INF = _hazard(
    "ceiling_hazard_v0@INF",
    "ceiling_hazard_v0 ızgarasının uç noktası (λ = INF) kural olarak: yalnız 3 gün-grubu sabiti, özellik yok "
    "(SPEC_CEILING_V0 §10-4). Eğitim kümesi ve kesim modelinkiyle aynı.",
    features=[],
    lambda_grid=["INF"],
    parent_model_id="ceiling_hazard_v0",
    training=H99_F3_TRAINING,
    plan_id=PLAN_CEILING,
    spec_document=SPEC_DOCUMENTS["SPEC_CEILING_V0"],
    input_policy={"required_inputs": []},
)
PB_CEILING_V0 = _hazard(
    "pb_ceiling_v0",
    "Talep toplama öncesi tavan serisi (SPEC_PB_V0 §9): SPEC_CEILING_V0 hazard modeli, özellikler pb1, pb2 "
    "(2 katsayı + 3 gün sabiti), 99 arz, bilgi kesimi ilk talep toplama günü B(k).",
    features=["pb1", "pb2"],
    feature_version=PB_FEATURE_VERSION,
    preprocessing_id=PB_CEILING_RECIPE.recipe_id,
    sources={"prebookbuild": PB_SOURCE},
    training=H99_TRAINING,
    plan_id=PLAN_PB_CEILING,
    spec_document=SPEC_DOCUMENTS["SPEC_PB_V0"],
    input_policy={"field_missing": "REFUSE PB_FIELD_MISSING:<alan>", "identity_or_range_violation": "REFUSE PB_IDENTITY:<ad>",
                  "price_range": "REFUSE PB_PRICE_RANGE", "f3": "KULLANILMAZ; f3 yokken RET ETMEZ",
                  "out_of_training_range": "WARN", "pb4_positive": "WARN"},
)
PB_CEILING_V0_AT_INF = _hazard(
    "pb_ceiling_v0@INF",
    "pb_ceiling_v0 ızgarasının uç noktası (λ = INF) kural olarak: yalnız 3 gün-grubu sabiti, özellik yok "
    "(SPEC_PB_V0 §9). Eğitim kümesi ve kesim modelinkiyle aynı.",
    features=[],
    lambda_grid=["INF"],
    parent_model_id="pb_ceiling_v0",
    training=H99_TRAINING,
    plan_id=PLAN_PB_CEILING,
    spec_document=SPEC_DOCUMENTS["SPEC_PB_V0"],
    input_policy={"required_inputs": []},
)


def _km(model_id: str, algorithm: str, description: str, **fields: Any) -> dict[str, Any]:
    return {
        "model_id": model_id,
        "algorithm": algorithm,
        "description": description,
        "features": [],
        "outputs": ["hazard", "S", "P_L", "P_close_ceiling"],
        "days": 10,
        "reclose": copy.deepcopy(_HAZARD_COMMON["reclose"]),
        "training": H99_TRAINING,
        "plan_id": PLAN_CEILING,
        "spec_document": SPEC_DOCUMENTS["SPEC_CEILING_V0"],
        "input_policy": {"required_inputs": []},
        **fields,
    }


BASE_KM_EXPANDING = _km(
    "base_km_expanding", "KM_EXPANDING",
    "Tavan serisi Kaplan–Meier (SPEC_CEILING_V0 §10-1): S_k = Π_{d≤k}(1 − olay_d/risk_d), eğitimdeki tüm arzların "
    "kişi-dönem satırlarından; risk_d = 0 ise önceki günün hazard'ı.",
)
BASE_KM_LAST10 = _km(
    "base_km_last10", "KM_LAST10",
    "Tavan serisi son-10 Kaplan–Meier (SPEC_CEILING_V0 §10-2): her d için yalnız (j, d) satırı eğitimde bulunan son 10 arz "
    "(first_trading_date, ticker sırasıyla).",
    last_n=10,
)

# ---------------------------------------------------------------------------
# Faz 4: tavan yolu modelleri (docs/specs_faz4/SPEC_CEILING_PATH_V0.md, commit 52e1567, uygulamadan önce
# push edildi). docs/specs/ değişmedi; belge sha256'sı ayrı sözlükte.
# ---------------------------------------------------------------------------

SPEC_DOCUMENTS_FAZ4: dict[str, dict[str, str]] = {
    "SPEC_CEILING_PATH_V0": {"path": "docs/specs_faz4/SPEC_CEILING_PATH_V0.md",
                             "sha256": "0798366047247c750a3cf6160e06bf7c0ff833628815d31ea1dd9dbe0ebfee5d"},
}
CEILING_PATH_ALGORITHM = "CEILING_PATH_MIXTURE_EQ_V0"
_RULE_SOURCE = {
    "url": "https://www.borsaistanbul.com/piyasalar/pay-piyasasi/piyasa-isleyisi",
    "accessed": "2026-09-22",
    "page_sha256": "af1976338cc311b0cbdd5d89384d82cf97690e9feafd739a287fe4e8ec34cfa5",
    "quote_file": "docs/specs_faz4/ekler/kural_metni_borsaistanbul_20260922.md",
}
_CEILING_PATH_COMMON: dict[str, Any] = {
    "algorithm": CEILING_PATH_ALGORITHM,
    "outputs": ["hazard", "S", "P_L", "P_close_ceiling", "limit_path",
                "D1..D10: return (karışım medyanı), p_up, mean, q10, q50, q90, limit_path_return, S_h, post_break"],
    "days": 10,
    "limit_path": {
        "margin": "0.10",
        "tick_table": [{"below": "20", "tick": "0.01"}, {"below": "50", "tick": "0.02"}, {"below": "100", "tick": "0.05"},
                       {"below": "250", "tick": "0.10"}, {"below": "500", "tick": "0.25"}, {"below": "1000", "tick": "0.50"},
                       {"below": "2500", "tick": "1.00"}, {"below": None, "tick": "2.50"}],
        "upper_rounding": "FLOOR_TO_TICK_AT_LIMIT_LEVEL",
        "lower_rounding": "CEIL_TO_TICK_AT_LIMIT_LEVEL",
        "d1_base": "HALF_UP_TO_TICK",
        "definition": "C_0 = P; b_1 = snap(P); C_1 = U(b_1); C_k = U(C_{k-1}); rho_k = C_k / P - 1 (Decimal; 1.1^h kullanılmaz)",
        "rule_source": _RULE_SOURCE,
    },
    "post_break": {
        "N_MIN": 10,
        "groups": ["Z", "B"],
        "group_definition": "Z: t = 0 (D1 tavan değil), m = h in 1..10; B: 1 <= t <= 9 (seri t gün sürdü), m = h - t in 1..9",
        "observation": "G = kapanış(D_{t+m}) / baz - 1, baz = P (t = 0) ya da kapanış(D_t); seans(D_{t+m}) < kesim (kesin), ilk geçmeyende dur",
        "universe": "99 arzın hepsi (f3 şartı yok; bileşen kovaryatsız)",
        "pooling_ladder": "kendi hücresi; diğer grubun aynı m'si; sonra m-1, m+1, m-2, m+2, ... (her adımda iki grup); adım sonunda n >= N_MIN ise dur",
        "clip": "havuzlanan değer hedef m'nin fiziksel sınırına: min(max(G, 0.9^m - 1), 1.1^m - 1)",
        "insufficient": "POST_BREAK_INSUFFICIENT: S ve P_L üretilir; getiri/p_up/kuantil üretilmez",
    },
    "mixture": "atoms(h) = [(rho_h, S_h)] + t = 0: [(v, P(L=0)/n)], v in G(Z, h) + t = 1..h-1: [((C_t/P)(1+v) - 1, P(L=t)/n)], v in G(B, h-t)",
    "quantile_rule": {"order": "r artan, eşitlikte ekleme sırası (kararlı)", "rule": "Q(q) = F >= q - 1e-12 sağlayan ilk atomun r'si",
                      "point": "return = Q(0.5) (medyan; MAE ile skorlanır)", "p_up": "sum(w : r > 0)",
                      "mean": "sum(w r) (ikincil gösterim)", "quantiles": [0.1, 0.5, 0.9]},
    "horizons_out": [f"D{h}" for h in range(1, 11)],
    "conditional_update": "SPEC_CEILING_PATH_V0 §7: borsai/predict_path.py conditional / conditional_after_break",
    "training": H99_TRAINING,
    "free_parameters": 0,
    "spec_document": SPEC_DOCUMENTS_FAZ4["SPEC_CEILING_PATH_V0"],
}


def _ceiling_path(model_id: str, description: str, **fields: Any) -> dict[str, Any]:
    spec = copy.deepcopy(_CEILING_PATH_COMMON)
    for k, v in copy.deepcopy(fields).items():
        if isinstance(v, dict) and isinstance(spec.get(k), dict):
            spec[k].update(v)
        else:
            spec[k] = v
    spec.update({"model_id": model_id, "description": description})
    return spec


CEILING_PATH_V0 = _ceiling_path(
    "ceiling_path_v0",
    "Tavan yolu (SPEC_CEILING_PATH_V0): dondurulmuş ceiling_hazard_v0'ın S_k'sı + deterministik limit yolu C_h + "
    "kırılma sonrası ampirik hücreler; R_h dağılımının medyanı, p_up ve kuantilleri, h = 1..10. Yeni serbest parametre 0.",
    features=["f1", "f2", "f3"],
    survival_model_id="ceiling_hazard_v0",
    survival_model_sha256="caa4dc867a9fc20d9f57cf6269e157ee1fafc9527c5144e53797bf48af0ffb67",
    survival_ledger={"path": "tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv",
                     "sha256": "976b4dcea9819160bf863873a0a3e3a639942bdfeec6f9229e015047c904665b"},
    limit_path={"price_field": "ipo_price_tl"},
    plan_id=PLAN_CEILING_PATH,
    input_policy={"survival": "gömülü ceiling_hazard_v0 kuralları aynen (f3 yoksa RET F3_MISSING)",
                  "ipo_price_not_on_tick_grid": "WARN IPO_PRICE_NOT_ON_TICK_GRID (snap uygulanır)"},
)
CEILING_PATH_V0_AT_INF = _ceiling_path(
    "ceiling_path_v0@INF",
    "Tavan yolu sıfır modeli (MECHANICS_BASE; SPEC_CEILING_PATH_V0): ceiling_hazard_v0@INF'in yalnız gün-grubu sabitleri "
    "+ aynı limit yolu ve hücreler; özellik yok.",
    features=[],
    survival_model_id="ceiling_hazard_v0@INF",
    survival_model_sha256="c5ac8085fd76b5bcdee328e51a4114ef85d5cae1cab23b51ea9b1232bc660c7e",
    survival_ledger={"path": "tests/reference/macos_golden_faz1b/ceiling_hazard_v0@INF_fold_ledger.csv",
                     "sha256": "90b610463de417c702cfae8032957aa4745aefcb4814a2745459da90bddb2f93"},
    limit_path={"price_field": "ipo_price_tl"},
    plan_id=PLAN_CEILING_PATH,
    input_policy={"survival": "girdi istemez, ret etmez",
                  "ipo_price_tl": "limit yolu için gerekli; eksik/geçersizse etiketli RET (SPEC_DEVIATIONS F2)",
                  "ipo_price_not_on_tick_grid": "WARN IPO_PRICE_NOT_ON_TICK_GRID (snap uygulanır)"},
)
PB_CEILING_PATH_V0 = _ceiling_path(
    "pb_ceiling_path_v0",
    "Talep toplama öncesi tavan yolu (SPEC_CEILING_PATH_V0): dondurulmuş pb_ceiling_v0'ın S_k'sı + aynı limit yolu ve "
    "hücreler; backtest kesimi ilk talep toplama günü B(k); f3 istemez.",
    features=["pb1", "pb2"],
    survival_model_id="pb_ceiling_v0",
    survival_model_sha256="7fb7a41e48ea2259acbbfc754063be3dbdd23525aff34b574278b3f00dcbc5aa",
    survival_ledger={"path": "tests/reference/macos_golden_faz1b/pb_ceiling_v0_fold_ledger.csv",
                     "sha256": "c92ce859ac67dfca4984cbd248c53379771f9bed50194bef2825f2d8d2b3cf16"},
    limit_path={"price_field": "ipo_price_try"},
    plan_id=PLAN_PB_CEILING_PATH,
    input_policy={"survival": "gömülü pb_ceiling_v0 kuralları aynen (PB_FIELD_MISSING, PB_IDENTITY, PB_PRICE_RANGE); f3 istemez",
                  "ipo_price_not_on_tick_grid": "WARN IPO_PRICE_NOT_ON_TICK_GRID (snap uygulanır)"},
)

FAZ1A_MODEL_IDS: tuple[str, ...] = (
    "v1_5_h99", "base_always_ceiling", "base_train_median", "base_train_mean", "base_zero", "base_rate", "base_last10_rate",
)
# Faz 1B'nin dokuz modeli (sabit liste: sıra kuralı bekçisi Faz 1'in 16 modelini bağlar, SPEC_DEVIATIONS E18).
FAZ1B_MODEL_IDS: tuple[str, ...] = (
    "v1_6_h99", "v1_5_market20_v0", "pb_v0", "ceiling_hazard_v0", "ceiling_hazard_v0@INF", "pb_ceiling_v0",
    "pb_ceiling_v0@INF", "base_km_expanding", "base_km_last10",
)
FAZ4_MODEL_IDS: tuple[str, ...] = ("ceiling_path_v0", "ceiling_path_v0@INF", "pb_ceiling_path_v0")
MODEL_SPECS: dict[str, dict[str, Any]] = {
    s["model_id"]: s
    for s in (
        V1_5_H99,
        BASE_ALWAYS_CEILING,
        BASE_TRAIN_MEDIAN,
        BASE_TRAIN_MEAN,
        BASE_ZERO,
        BASE_RATE,
        BASE_LAST10_RATE,
        V1_6_H99,
        V1_5_MARKET20_V0,
        PB_V0,
        CEILING_HAZARD_V0,
        CEILING_HAZARD_V0_AT_INF,
        PB_CEILING_V0,
        PB_CEILING_V0_AT_INF,
        BASE_KM_EXPANDING,
        BASE_KM_LAST10,
        CEILING_PATH_V0,
        CEILING_PATH_V0_AT_INF,
        PB_CEILING_PATH_V0,
    )
}
if tuple(MODEL_SPECS) != FAZ1A_MODEL_IDS + FAZ1B_MODEL_IDS + FAZ4_MODEL_IDS:
    raise AssertionError("MODEL_SPECS sırası FAZ1A + FAZ1B + FAZ4 değil")
RULE_MODEL_IDS: tuple[str, ...] = (
    "base_always_ceiling", "base_train_median", "base_train_mean", "base_zero", "base_rate", "base_last10_rate",
    "ceiling_hazard_v0@INF", "pb_ceiling_v0@INF", "base_km_expanding", "base_km_last10",
)
HAZARD_ALGORITHM = "discrete_time_hazard_logit_l2"
KM_ALGORITHMS = ("KM_EXPANDING", "KM_LAST10")

# ---------------------------------------------------------------------------
# Faz 5: D1 sonrası güncelleme (docs/specs_faz5/SPEC_POST_D1_V0.md, commit c20c092, push kanıtı 2026-09-24T00:44:25Z,
# uygulamadan önce). Kayıt aşaması POST_D1: bu modeller listeleme öncesi `MODEL_SPECS`'e ve `models/INDEX.json`'a GİRMEZ;
# dondurulunca `models/INDEX_POST_D1.json`'a eklenir (proje sahibi kararı 4, SPEC_DEVIATIONS H).
# ---------------------------------------------------------------------------

SPEC_DOCUMENTS_FAZ5: dict[str, dict[str, str]] = {
    "SPEC_POST_D1_V0": {"path": "docs/specs_faz5/SPEC_POST_D1_V0.md",
                        "sha256": "a5b4675d84784b4a9db9c3b0f7fe3b6a1c1014e823c66b237b4613b51f7ead34"},
}
STAGE_POST_D1 = "POST_D1"
POST_D1_ALGORITHM = "discrete_time_hazard_offset_logit_l2"
PLAN_POST_D1 = "H99_POST_D1_PP_WALK_FORWARD_T_CUTOFF_F3_PRESENT_L_GE_1_MIN10IPO_5EV_5SV"
PLAN_KEYS[PLAN_POST_D1] = "post_d1"
H99_F3_L_GE_1_TRAINING = {
    "set": "H99_F3_PRESENT_L_GE_1",
    "description": "data/training_table.csv'nin total_demand_multiple dolu VE ceiling_close_D1 = 1 olan 81 satırı, tablo sırasıyla",
    "n": 81,
    "data_version_sha256": H99_DATA_VERSION_SHA256,
}
POST_D1_HAZARD_V0: dict[str, Any] = {
    "model_id": "post_d1_hazard_v0",
    "algorithm": POST_D1_ALGORITHM,
    "stage": STAGE_POST_D1,
    "description": ("D1 sonrası güncelleme (SPEC_POST_D1_V0): dondurulmuş ceiling_hazard_v0'ın doğrusal öngörücüsü sabit ofset; "
                    "d = 2..10 hazard'ına δ·u (u = z-skorlu d1_lock, d1_turnover), L2 (λ iç arz-bırak CV ile). h_1 ana modelden "
                    "aynen. Yalnız D1'i tavanda kapatan arzlarda tanımlı; birincil çıktı koşullu S_cond[k] = S_k / S_1."),
    "features": ["d1_lock", "d1_turnover"],
    "d1_features": {
        "d1_lock": "1[Decimal(EN DUSUK FIYAT) == Decimal(UST LIMIT FIYATI)], D_1 satırı, ham metin (adım/yuvarlama yok)",
        "d1_turnover": "ln(TOPLAM ISLEM ADEDI / shares_offered): Decimal 60 hane, bir kez binary64",
        "lock_consistency": "kilit => açılış = en yüksek = kapanış = üst limit; tutmazsa WARN_D1_LOCK_INCONSISTENT",
    },
    "d1_preprocessing": {"d1_lock": "z-skor (ortalama, popülasyon std, ddof = 0); σ = 0 ise düşer (katsayı 0)",
                         "d1_turnover": "Type-7 [p05, p95] kırpma (eğitim kümesinden, arz düzeyinde) -> z-skor; σ = 0 ise düşer",
                         "arithmetic": "kantil/ortalama/varyans kesin Fraction, std ve z 60 haneli Decimal (f3 ile aynı yöntem)"},
    "parent": {"model_id": "ceiling_hazard_v0", "file": "ceiling_hazard_v0.json",
               "sha256": "caa4dc867a9fc20d9f57cf6269e157ee1fafc9527c5144e53797bf48af0ffb67",
               "preprocessing_id": CEILING_RECIPE.recipe_id, "index": "models/INDEX.json"},
    "path_secondary": {"model_id": "ceiling_path_v0", "file": "ceiling_path_v0.json",
                       "sha256": "3e97e8788266f807a06604316d562de939a3e84ab6fcc9c0be1ce87790c6952d", "index": "models/INDEX.json"},
    "days": 10,
    "updated_days": [2, 3, 4, 5, 6, 7, 8, 9, 10],
    "model": "logit h_d = eta_base_d(x) + delta·u(w), d = 2..10; h_1 = sigmoid(eta_base_1) (ana modelden aynen); "
             "eta_base_d = gamma_{g(d)} + beta·z(x) dondurulmuş ceiling_hazard_v0'dan (ofset, sabit)",
    "penalty": "L2 yalnız delta'da, (lambda/2)·||delta||²; yeni kesişim yok",
    "pseudo_rows": None,
    "solver": {"method": "NEWTON_RAPHSON_NUMPY_OFFSET", "init": "delta = 0", "grad_tol": 1e-10, "max_iter": 100,
               "max_halvings": 30, "descent_check": "J_new <= J_old + m·eps·max(|J_old|, 1) (SPEC_DEVIATIONS A2)",
               "non_convergence": "MODEL_NOT_FIT_DID_NOT_CONVERGE"},
    "lambda_grid": [0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, "INF"],
    "lambda_INF": "delta ≡ 0 (karşılaştırıcının kendisi; ayrı sıfır model yok, SPEC_POST_D1_V0 §3.4)",
    "selection": {"method": "INNER_LEAVE_ONE_IPO_OUT", "rows": "j'nin bütün d ≥ 2 satırları dışarıda",
                  "preprocessing": "D1 ön işlemesi (p05/p95, μ, σ) kalan arzlardan yeniden; ofset değişmez",
                  "objective": "satır başına ortalama log-kayıp; h [1e-12, 1 − 1e-12]'ye kırpılır",
                  "tie_break": "BIT_EXACT_TIE_TO_LARGEST_LAMBDA_INF_LARGEST",
                  "non_convergence": "CANDIDATE_NOT_CONVERGED_DROPPED_INF_ALWAYS_KEPT"},
    "pp_rows": "SPEC_CEILING_V0 §2 kişi-dönem satırlarından d ≥ 2 olanlar (satır ancak d − 1 ≤ L; event = 1[L = d − 1])",
    "scorability": {"min_ipo": 10, "min_events": 5, "min_survivals": 5},
    "training": H99_F3_L_GE_1_TRAINING,
    "plan_id": PLAN_POST_D1,
    "spec_document": SPEC_DOCUMENTS_FAZ5["SPEC_POST_D1_V0"],
    "survival_ledger": {"path": "tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv",
                        "sha256": "976b4dcea9819160bf863873a0a3e3a639942bdfeec6f9229e015047c904665b"},
    "path_ledger": {"path": "tests/reference/macos_golden_faz4/ceiling_path_v0_fold_ledger.csv",
                    "sha256": "1f45365ee2d84612c7a1882d98bd46697405030b003aa3db379b4fcf450e2e15"},
    "sessions_source": {"path": "data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv",
                        "session_1_columns": ["thb_raw_open", "thb_raw_high", "thb_raw_low", "thb_raw_close", "thb_raw_volume",
                                              "thb_raw_trade_count", "thm_raw_upper_limit", "session_type",
                                              "security_trading_status", "target_session_date"],
                        "other_session_columns": ["target_session_date"],
                        "half_day": "session_type == OPEN_HALF_DAY (OPEN_FULL_DAY -> 0; başka kod durur)",
                        "halt_flag": "security_trading_status != ACTIVE_NOT_SUSPENDED (başka kod durur)"},
    "outputs": ["hazard", "S", "P_L", "P_close_ceiling", "conditional_j1: S_cond (k = 2..10), p_break_next, P_L_cond (l = 1..10)",
                "path_conditional (ikincil; ceiling_path_v0 hücreleri + bu modelin S'i, j = 1) | null"],
    "input_policy": {"parent": "ceiling_hazard_v0 kuralları aynen (f3 yoksa RET F3_MISSING)",
                     "d1_not_traded": "D1_NOT_TRADED: kayıt yazılmaz", "d1_limit_na": "REFUSE D1_LIMIT_NA",
                     "d1_not_ceiling": "NOT_APPLICABLE D1_NOT_CEILING (ret değil)", "d1_volume_invalid": "REFUSE D1_VOLUME_INVALID",
                     "shares_offered_invalid": "REFUSE INPUT_SHARES_OFFERED", "half_day": "WARN", "intraday_halt": "WARN",
                     "special_trades": "WARN (hacim düzeltilmez)", "lock_inconsistent": "WARN",
                     "d1_turnover_outside_train_p05_p95": "CLIP_AND_FLAG", "out_of_training_range": "WARN"},
    "runtime_pins": RUNTIME_PINS,
}
FAZ5_MODEL_IDS: tuple[str, ...] = ("post_d1_hazard_v0",)
POST_D1_MODEL_SPECS: dict[str, dict[str, Any]] = {s["model_id"]: s for s in (POST_D1_HAZARD_V0,)}
if tuple(POST_D1_MODEL_SPECS) != FAZ5_MODEL_IDS or set(POST_D1_MODEL_SPECS) & set(MODEL_SPECS):
    raise AssertionError("POST_D1_MODEL_SPECS FAZ5_MODEL_IDS değil ya da listeleme öncesi modellerle çakışıyor")


def _spec_of(model_id: str) -> dict[str, Any]:
    if model_id in MODEL_SPECS:
        return MODEL_SPECS[model_id]
    if model_id in POST_D1_MODEL_SPECS:
        return POST_D1_MODEL_SPECS[model_id]
    if model_id in FAZ7_MODEL_SPECS:
        return FAZ7_MODEL_SPECS[model_id]
    if model_id in POST_BREAK_MODEL_SPECS:          # Faz 8 (sözlük aşağıda; çağrı anında çözülür; SPEC_DEVIATIONS N23)
        return POST_BREAK_MODEL_SPECS[model_id]
    return FAZ7C_MODEL_SPECS[model_id]


def plan_of(model_id: str) -> str:
    return _spec_of(model_id).get("plan_id", PLAN_V15)


def model_kind(model_id: str) -> str:
    """linear (Ridge + Logit), hazard, km, ceiling_path, post_d1 (D1 sonrası güncelleme), fall (Faz 7C: Ridge'siz L2-lojistik
    p_up; `@ZERO` kural satırı dahil) ya da rule (sabit kural)."""
    # post_break (Faz 8 kırılma akşamı, `@ZERO` dahil): algoritma adı fall ile ortak (`l2_logit_v1_6_grid`); aşama ve aile algoritmadan
    # önce denetlenir (`freeze.model_kind` ile aynı sınıflama; SPEC_DEVIATIONS N23).
    spec = _spec_of(model_id)
    if spec.get("stage") == STAGE_POST_BREAK and spec.get("family") == FAMILY_BREAK:
        return "post_break"
    algorithm = _spec_of(model_id)["algorithm"]
    if algorithm == "V1_5_RIDGE_LOGIT":
        return "linear"
    if algorithm == HAZARD_ALGORITHM:
        return "hazard"
    if algorithm in KM_ALGORITHMS:
        return "km"
    if algorithm == CEILING_PATH_ALGORITHM:
        return "ceiling_path"
    if algorithm == POST_D1_ALGORITHM:
        return "post_d1"
    if algorithm == FALL_ALGORITHM:
        return "fall"
    return "rule"


def spec_sha256(spec: dict[str, Any]) -> str:
    return canonical_sha256(spec)


# ---------------------------------------------------------------------------
# Faz 7: tavan serisi v1 ailesi (docs/specs_faz7/SPEC_HAZARD_V1.md, commit 6a16c16, push kanıtı 2026-09-25T18:09:45Z,
# uygulamadan önce; proje sahibi kararları docs/specs_faz7/KARARLAR.md, çeliştiği yerde bağlayıcı). Üç aday + bir kural satırı.
# Bu görevde dondurulmaz: `MODEL_SPECS`'e ve `models/INDEX.json`'a GİRMEZ (dondurma ayrı görev; INDEX'e 4 giriş orada).
# Uygulama yorumları docs/SPEC_DEVIATIONS.md J.
# ---------------------------------------------------------------------------


SPEC_DOCUMENTS_FAZ7: dict[str, dict[str, str]] = {
    "SPEC_HAZARD_V1": {"path": "docs/specs_faz7/SPEC_HAZARD_V1.md",
                       "sha256": "25229cea8f6f235db6562f3dee4992e6b8e22e0cbc23b44b25eeb6d2704d0944"},
    "KARARLAR_FAZ7": {"path": "docs/specs_faz7/KARARLAR.md",
                      "sha256": "eb6ac63cce3efdd05c824e474d9be53ccd70e992ce952f9f58c77a391f70ff36"},
}
FAMILY_V1 = "ceiling_hazard_v1"
# data/data_version_v2.json dosyasının sha256'sı (v2 tablosu + kaynak pinleri + üretici; borsai.data.version_v2).
V2_DATA_VERSION_SHA256 = "2ee8d51be3f026ad05ff7b4894f9512809556b3da2fd2d0b06256b7de5ee525a"
PLAN_CEILING_POOLED = "H99_PLUS_OOT_OPEN_CEILING_PP_WALK_FORWARD_T_CUTOFF_F3_PRESENT_MIN10IPO_5EV_5SV"
PLAN_KEYS[PLAN_CEILING_POOLED] = "pooled"
# TÜFE pini (append-only: başlık + ilk satırdan through_month'a kadarki baytlar; borsai.tufe.verify_pin).
TUFE_PIN = {"path": "data/raw/tuik/tufe_genel_2025_100.csv", "series": "TUIK_TUFE_GENEL_2025_100", "through_month": "2026-08",
            "prefix_sha256": "3d61cbcfca2453cfce476d4cfaae38a3c77c68a4d168641162d1627e731a567b"}
DEFLATOR = {
    "series": "TUIK_TUFE_GENEL_2025_100",
    "month_rule": "T_MONTH_MINUS_2",
    "file": TUFE_PIN["path"],
    "file_sha256": TUFE_PIN["prefix_sha256"],
    "through_month": TUFE_PIN["through_month"],
    "unit": "2025 TL",
    "definition": "f1r_ham = büyüklük_TL / (TÜFE[T'nin ayı − 2] / 100), büyüklük_TL f1 ile tek tanım (borsai.features); "
                  "Decimal 60 hane (borsai.predict_hazard.real_size); ön işlemede winsor -> ln -> z (f1 ile aynı yol)",
    "append_rule": "yeni ay dosyanın sonuna ek satırdır; file_sha256 başlık dahil through_month satırına kadarki baytların sha256'sı "
                   "(borsai.tufe.prefix_sha256); eski satır, temel yıl ya da zincirleme değişirse yeni veri sürümü = yeni model_id",
    "source": "TÜİK veri portalı, 'Tüketici fiyat endeksi ve değişim oranları' [2025=100]; yayım günleri her ayın kendi bülteninden",
}
REGIME = {
    "column": "r_pre_equal",
    "definition": "1[ALLOC_REGIME != EQUAL_DIST_20230330] (PRE_20211111 ve THRESH100_20211111 -> 1)",
    "alloc_regime": "borsai.data.alloc_regime(talep toplama başlangıcı) = kohort dosyasının ALLOC_REGIME etiketi (SPEC_DEVIATIONS I8, J)",
    "penalized": False,
    "z_scored": False,
    "live_value": 0,
    "pseudo_row_value": 0,
    "h99_value": 0,
}
F3_FILTER_RULE = ("SPEC_CEILING_V0 §4 filtre adımı aynen; bir eğitim kümesinde (iç CV dahil) f3'lü birimlerin filtre modu açık ve "
                  "birimin durumu ona açıkça zıtsa o birimin f3'ü boşalır ve birim o kümede kullanılmaz (§7; proje sahibi kararı, "
                  "SPEC_DEVIATIONS J); iç CV'de tutulan birimin f3'ü boşalıyorsa o birim skorlanmaz")
POOLED_TRAINING = {
    "set": "H99_F3_PRESENT+OOT_OPEN_F3_PRESENT",
    "description": "data/training_table_v2.csv'nin total_demand_multiple dolu 165 satırı: H99'un 97'si ve eski kohortun açık kümesinin "
                   "(kasa dışı) 68'i, tablo sırasıyla",
    "n": 165,
    "table": "data/training_table_v2.csv",
    "cohort_counts": {"H99": 97, "OOT_OPEN": 68},
    "data_version_sha256": V2_DATA_VERSION_SHA256,
}
_V1_INPUT_POLICY = {"f3_missing": "REFUSE F3_MISSING (miras; PB aynası yok)", "invalid_f1_f2": "LABELED_REFUSAL",
                    "outside_train_p05_p95": "CLIP_AND_FLAG FEATURE_CLIPPED_TO_TRAINING_P05_P95 (feature, value, used); "
                                             "clipped, clipped_features",
                    "out_of_training_range": "WARN OUT_OF_TRAINING_RANGE (ham değer, kırpma sonrası da yazılır)"}
_V1_TUFE_POLICY = {"tufe_index": "girdi tufe_index (T'nin ayı − 2 endeksi, borsai.tufe.index_for; dondurma/kayıt hazırlar)",
                   "tufe_missing": "REFUSE TUFE_MISSING", "tufe_not_pit": "REFUSE TUFE_NOT_PIT",
                   "tufe_file_mismatch": "REFUSE TUFE_FILE_MISMATCH"}
_V1_REGIME_POLICY = {"regime_live": "r = live_value (0); girdi istemez; çıktı regime_value_used",
                     "regime_oot_record": "girdi alloc_regime (kohort etiketi) -> r; bilinmeyen/boş etiket REFUSE REGIME_UNKNOWN"}


def _v1(model_id: str, variant: str, description: str, **fields: Any) -> dict[str, Any]:
    return _hazard(model_id, description, family=FAMILY_V1, variant=variant, feature_version=FEATURE_VERSION,
                   spec_document=SPEC_DOCUMENTS_FAZ7["SPEC_HAZARD_V1"], decisions_document=SPEC_DOCUMENTS_FAZ7["KARARLAR_FAZ7"],
                   f3_filter_rule=F3_FILTER_RULE, **fields)


_POOLED_MODEL = {
    "model": "logit h_d(x) = gamma_{g(d)} + delta·r + beta·z(x); S_k = prod_{d<=k}(1 - h_d)",
    "penalty": "L2 yalnız beta'da, (lambda/2)·||beta||²; gamma ve delta (rejim) cezasız",
    "pseudo_rows": {"weight": 0.5, "rows": "her grup için z = 0, r = 0'da bir event = 1 ve bir event = 0 satırı"},
    "lambda_INF": "beta ≡ 0; (gamma, delta) pseudo-satırlı MLE, Newton (kapalı biçim yok; SPEC_HAZARD_V1 §3.3)",
}
_POOLED_SOLVER = dict(copy.deepcopy(_HAZARD_COMMON["solver"]), init="beta = 0, delta = 0, gamma_g = logit((olay_g + 0.5)/(risk_g + 1))")

CEILING_HAZARD_V1_CLIP = _v1(
    "ceiling_hazard_v1_clip", "clip",
    "Tavan serisi v1 (a) kırpma (SPEC_HAZARD_V1): ceiling_hazard_v0 aynen, ama f1 (ham TL), f2, f3 üçü de eğitim Type-7 [p05, p95]'ine "
    "kırpılır; H99'un f3'lü 97 arzı; 3 gün sabiti + 3 katsayı.",
    features=["f1", "f2", "f3"],
    preprocessing_id=CEILING_V1_CLIP_RECIPE.recipe_id,
    preprocessing_winsor=["f1", "f2", "f3"],
    training=H99_F3_TRAINING,
    plan_id=PLAN_CEILING,
    input_policy=dict(_V1_INPUT_POLICY),
)
CEILING_HAZARD_V1_REAL = _v1(
    "ceiling_hazard_v1_real", "real",
    "Tavan serisi v1 (b) reel büyüklük (SPEC_HAZARD_V1): f1 yerine f1r = ln(büyüklük / (TÜFE_{T−2} / 100)) (TÜİK TÜFE 2025=100); "
    "f1r, f2, f3 eğitim [p05, p95]'ine kırpılır; H99'un f3'lü 97 arzı; 3 gün sabiti + 3 katsayı.",
    features=["f1r", "f2", "f3"],
    preprocessing_id=CEILING_V1_REAL_RECIPE.recipe_id,
    preprocessing_winsor=["f1r", "f2", "f3"],
    deflator=DEFLATOR,
    training=H99_F3_TRAINING,
    plan_id=PLAN_CEILING,
    input_policy={**_V1_INPUT_POLICY, **_V1_TUFE_POLICY},
)
CEILING_HAZARD_V1_POOLED = _v1(
    "ceiling_hazard_v1_pooled", "pooled",
    "Tavan serisi v1 (c) havuz (SPEC_HAZARD_V1): f1r, f2, f3 (kırpmalı) + cezasız rejim terimi r = 1[tahsis rejimi ≠ EQUAL_DIST_20230330]; "
    "eğitim H99 + eski kohortun açık kümesi (165 arz, training_table_v2); canlıda r = 0.",
    features=["f1r", "f2", "f3"],
    preprocessing_id=CEILING_V1_REAL_RECIPE.recipe_id,
    preprocessing_winsor=["f1r", "f2", "f3"],
    deflator=DEFLATOR,
    regime=REGIME,
    training=POOLED_TRAINING,
    plan_id=PLAN_CEILING_POOLED,
    solver=_POOLED_SOLVER,
    input_policy={**_V1_INPUT_POLICY, **_V1_TUFE_POLICY, **_V1_REGIME_POLICY},
    **_POOLED_MODEL,
)
CEILING_HAZARD_V1_POOLED_AT_INF = _v1(
    "ceiling_hazard_v1_pooled@INF", "pooled@INF",
    "ceiling_hazard_v1_pooled ızgarasının uç noktası (λ = INF) kural olarak: 3 gün-grubu sabiti + rejim sabiti δ, özellik yok "
    "(SPEC_HAZARD_V1 §2); (γ, δ) Newton. Eğitim kümesi ve kesim modelinkiyle aynı.",
    features=[],
    lambda_grid=["INF"],
    parent_model_id="ceiling_hazard_v1_pooled",
    regime=REGIME,
    training=POOLED_TRAINING,
    plan_id=PLAN_CEILING_POOLED,
    solver=_POOLED_SOLVER,
    input_policy={"required_inputs": [], **_V1_REGIME_POLICY},
    **_POOLED_MODEL,
)
FAZ7_MODEL_IDS: tuple[str, ...] = ("ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled",
                                   "ceiling_hazard_v1_pooled@INF")
FAZ7_MODEL_SPECS: dict[str, dict[str, Any]] = {
    s["model_id"]: s for s in (CEILING_HAZARD_V1_CLIP, CEILING_HAZARD_V1_REAL, CEILING_HAZARD_V1_POOLED, CEILING_HAZARD_V1_POOLED_AT_INF)
}
if tuple(FAZ7_MODEL_SPECS) != FAZ7_MODEL_IDS or set(FAZ7_MODEL_SPECS) & (set(MODEL_SPECS) | set(POST_D1_MODEL_SPECS)):
    raise AssertionError("FAZ7_MODEL_SPECS FAZ7_MODEL_IDS değil ya da var olan modellerle çakışıyor")
# v1_clip@INF ve v1_real@INF iç hesapları ceiling_hazard_v0@INF ile bit-eşittir (aynı eğitim kümesi, özelliksiz): ayrıca kaydedilmez.
V1_AT_INF_EQUALS = {"ceiling_hazard_v1_clip": "ceiling_hazard_v0@INF", "ceiling_hazard_v1_real": "ceiling_hazard_v0@INF"}


# ---------------------------------------------------------------------------
# Faz 7C: düşen arz modeli v0 ailesi (docs/specs_faz7_c/SPEC_C_V0.md, commit 4fe4e51, push kanıtlı, uygulamadan önce; bağlayıcı
# kararlar docs/specs_faz7_c/KARARLAR_C.md, çeliştiği yerde geçerli). Üç aday + bir kural satırı. Bu görevde dondurulmaz:
# `MODEL_SPECS`'e ve `models/INDEX.json`'a GİRMEZ (dondurma ayrı görev; INDEX'e 4 giriş orada). Uygulama yorumları
# docs/SPEC_DEVIATIONS.md K.
# ---------------------------------------------------------------------------

SPEC_DOCUMENTS_FAZ7C: dict[str, dict[str, str]] = {
    "SPEC_C_V0": {"path": "docs/specs_faz7_c/SPEC_C_V0.md",
                  "sha256": "d75c17cfec09712174c86ac8619b5d51fb5681fc161f48455423b84d9e8db5ac"},
    "KARARLAR_C": {"path": "docs/specs_faz7_c/KARARLAR_C.md",
                   "sha256": "2b60bec41924ac357b359a151737b9bc4a5a3b8fba30a1f75dab1e2eca2744a9"},
}
# Keşif varyantları (SPEC_C_V0 §8, §10; KARARLAR_C "Çokluk"): günlüğe `kind: exploration` satırları olarak (commit B). Model değildir.
FAZ7C_EXPLORATION = {"path": "docs/specs_faz7_c/ekler/denenenler.csv",
                     "sha256": "25edc9a6e40c59a518cf54fa5a28fb4fe9d891bbac511cfa2fdb7f2b5e046f5b", "n": 2054,
                     "source_commit": "4fe4e51", "data_version_sha256": V2_DATA_VERSION_SHA256}
FALL_HORIZONS: tuple[str, ...] = ("D5", "D10")
# Planlar (SPEC_C_V0 §5.1): PLAN_V15 kuralı (ufuk başına eğitim satırı ancak D_h seansı < T; eğitim n ≥ 10), test arzları H99'dan.
PLAN_FALL_H99 = "H99_F3_AS_PRESENT_FALL_WALK_FORWARD_STRICT_PRIOR_DATE_MIN_TRAIN_10"
PLAN_FALL_POOLED = "H99_PLUS_OOT_OPEN_F3_AS_PRESENT_FALL_WALK_FORWARD_STRICT_PRIOR_DATE_MIN_TRAIN_10"
PLAN_FALL_ADDSALE = "H99_PLUS_OOT_OPEN_AS_PRESENT_FALL_WALK_FORWARD_STRICT_PRIOR_DATE_MIN_TRAIN_10"
PLAN_KEYS.update({PLAN_FALL_H99: "fall_h99", PLAN_FALL_POOLED: "fall_pooled", PLAN_FALL_ADDSALE: "fall_addsale"})
FALL_SET_H99 = "H99_F3_AS_PRESENT"
FALL_SET_POOLED = "H99_PLUS_OOT_OPEN_F3_AS_PRESENT"
FALL_SET_ADDSALE = "H99_PLUS_OOT_OPEN_AS_PRESENT"

FALL_H99_TRAINING = {
    "set": FALL_SET_H99,
    "description": "data/training_table.csv'nin total_demand_multiple VE additional_sale_shares dolu 94 satırı, tablo sırasıyla",
    "n": 94,
    "table": "data/training_table.csv",
    "cohort_counts": {"H99": 94, "OOT_OPEN": 0},
    "events_D5": 18,
    "events_D10": 26,
    "event_definition": TARGET_DEFINITION,
    "data_version_sha256": H99_DATA_VERSION_SHA256,
}
FALL_POOLED_TRAINING = {
    "set": FALL_SET_POOLED,
    "description": "data/training_table_v2.csv'nin total_demand_multiple VE additional_sale_shares dolu 161 satırı: H99'un 94'ü ve eski "
                   "kohortun açık kümesinin (kasa dışı) 67'si, tablo sırasıyla",
    "n": 161,
    "table": "data/training_table_v2.csv",
    "cohort_counts": {"H99": 94, "OOT_OPEN": 67},
    "events_D5": 29,
    "events_D10": 39,
    "event_definition": TARGET_DEFINITION,
    "data_version_sha256": V2_DATA_VERSION_SHA256,
}
FALL_ADDSALE_TRAINING = {
    "set": FALL_SET_ADDSALE,
    "description": "data/training_table_v2.csv'nin additional_sale_shares dolu 165 satırı (f3 istenmez): H99'un 95'i ve açık kümenin 70'i, "
                   "tablo sırasıyla",
    "n": 165,
    "table": "data/training_table_v2.csv",
    "cohort_counts": {"H99": 95, "OOT_OPEN": 70},
    "events_D5": 30,
    "events_D10": 40,
    "event_definition": TARGET_DEFINITION,
    "data_version_sha256": V2_DATA_VERSION_SHA256,
}
FALL_F3_FILTER_RULE = ("V1.5 f3 filtre adımı (preprocess.fit_preprocessing adım 1) aynen; tarifte imputasyon yok: bir eğitim kümesinde (iç "
                       "CV dahil) f3'lü arzların filtre modu açık ve arzın durumu ona açıkça zıtsa o arz o kümede kullanılmaz; iç CV'de "
                       "tutulan arzın f3'ü o iç kümenin moduyla boşalıyorsa o arz skorlanmaz (SPEC_DEVIATIONS J10 kuralı aynen, K); "
                       "tahminde açık uyuşmazlık RET F3_FILTER_STATUS_CONFLICT")
_FALL_LOGIT = dict(copy.deepcopy(V1_6_H99["logit"]),
                   label="Y_h = 1[kapanış(D_h) > arz fiyatı] (p_up başlığı; olay y_h = 1 − Y_h, düşme olasılığı = 1 − p_up)")
_FALL_FEATURE_POLICY = {"f3_missing": "REFUSE", "additional_sale_missing": "REFUSE", "f3_filter_status_conflict": "REFUSE",
                        "codes": "F3_MISSING; ADDITIONAL_SALE_MISSING (0 varsayılmaz, KARARLAR_C C4); INPUT_NEGATIVE (ek satış < 0); "
                                 "F3_FILTER_STATUS_CONFLICT",
                        "outside_train_p05_p95": "CLIP_AND_FLAG FEATURE_CLIPPED_TO_TRAINING_P05_P95 (f1r, f3); clipped, clipped_features",
                        "out_of_training_range": "WARN OUT_OF_TRAINING_RANGE (ham değer)", **_V1_TUFE_POLICY}
_FALL_ADDSALE_POLICY = {"f3_missing": "NOT_USED", "additional_sale_missing": "REFUSE", "f3_filter_status_conflict": "NOT_USED",
                        "codes": "ADDITIONAL_SALE_MISSING (0 varsayılmaz, KARARLAR_C C4); INPUT_NEGATIVE (ek satış < 0)",
                        "out_of_training_range": "WARN OUT_OF_TRAINING_RANGE (ham değer)"}
_FALL_COMMON: dict[str, Any] = {
    "algorithm": FALL_ALGORITHM,
    "family": FAMILY_FALL,
    "target_definition": TARGET_DEFINITION,
    "outputs": ["p_up"],
    "output_note": "p_up(D_h) = P(kapanış > arz) = 1 − P(y_h = 1); düşme olasılığı = 1 − p_up; getiri başlığı yok",
    "horizons": list(FALL_HORIZONS),
    "primary_horizon": "D10",
    "secondary_horizon": "D5",
    "min_train_n": 10,
    "grid_version": "v1_6",
    "logit": _FALL_LOGIT,
    "ridge": None,
    "spec_document": SPEC_DOCUMENTS_FAZ7C["SPEC_C_V0"],
    "decisions_document": SPEC_DOCUMENTS_FAZ7C["KARARLAR_C"],
    "runtime_pins": RUNTIME_PINS,
}


def _fall(model_id: str, variant: str, description: str, **fields: Any) -> dict[str, Any]:
    spec = copy.deepcopy(_FALL_COMMON)
    spec.update({"model_id": model_id, "variant": variant, "description": description, **copy.deepcopy(fields)})
    return spec


_FALL_FULL = dict(features=["f1r", "f3", "add_sale"], feature_version=FEATURE_VERSION, preprocessing_id=FALL_V0_RECIPE.recipe_id,
                  preprocessing_winsor=["f1r", "f3"], preprocessing_log=["f1r", "f3"], deflator=DEFLATOR,
                  f3_filter_rule=FALL_F3_FILTER_RULE, free_parameters_per_head=4, input_policy=_FALL_FEATURE_POLICY)
FALL_D10_V0_H99 = _fall(
    "fall_d10_v0_h99", "h99",
    "Düşen arz v0 (SPEC_C_V0): D10 ve D5'te P(kapanış > arz) için L2-lojistik (V1.6 C ızgarası, iç LOOCV Brier); özellikler f1r "
    "(TÜFE ile reel büyüklük), ln f3 (talep katı), ek satış bayrağı; H99'un f3 ve ek satış alanı dolu 94 arzı. "
    "Düşme olasılığı = 1 − p_up.",
    training=FALL_H99_TRAINING, plan_id=PLAN_FALL_H99, **_FALL_FULL,
)
FALL_D10_V0_POOLED = _fall(
    "fall_d10_v0_pooled", "pooled",
    "Düşen arz v0 (SPEC_C_V0): h99 ile aynı özellikler ve model (f1r, ln f3, ek satış bayrağı; L2-lojistik, V1.6 C ızgarası); eğitim "
    "H99 + eski kohortun açık kümesi (161 arz, training_table_v2); rejim terimi yok.",
    training=FALL_POOLED_TRAINING, plan_id=PLAN_FALL_POOLED, **_FALL_FULL,
)
FALL_D10_V0_ADDSALE = _fall(
    "fall_d10_v0_addsale", "addsale",
    "Düşen arz v0 (SPEC_C_V0): yalnız ek satış bayrağı (1[additional_sale_shares > 0]) ile L2-lojistik (V1.6 C ızgarası); eğitim "
    "H99 + açık küme, ek satış alanı dolu 165 arz; f3 istemez.",
    features=["add_sale"], feature_version=FEATURE_VERSION, preprocessing_id=FALL_V0_ADDSALE_RECIPE.recipe_id,
    preprocessing_winsor=[], preprocessing_log=[], free_parameters_per_head=2, training=FALL_ADDSALE_TRAINING,
    plan_id=PLAN_FALL_ADDSALE, input_policy=_FALL_ADDSALE_POLICY,
)
FALL_D10_V0_POOLED_ZERO = _fall(
    "fall_d10_v0_pooled@ZERO", "pooled@ZERO",
    "fall_d10_v0_pooled ızgarasının uç noktası (C = ZERO) kural olarak: ufuk başına sabit p_up = eğitim oranı (kapalı biçim), özellik "
    "yok (SPEC_C_V0 §2). Eğitim kümesi, plan ve f3 filtre dışlaması modelinkiyle aynı.",
    features=[], parent_model_id="fall_d10_v0_pooled", free_parameters_per_head=1, training=FALL_POOLED_TRAINING,
    plan_id=PLAN_FALL_POOLED, input_policy={"required_inputs": []},
)
FALL_D10_V0_POOLED_ZERO["logit"]["C_grid"] = ["ZERO"]
FAZ7C_MODEL_IDS: tuple[str, ...] = ("fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO")
FAZ7C_MODEL_SPECS: dict[str, dict[str, Any]] = {
    s["model_id"]: s for s in (FALL_D10_V0_H99, FALL_D10_V0_POOLED, FALL_D10_V0_ADDSALE, FALL_D10_V0_POOLED_ZERO)
}
if tuple(FAZ7C_MODEL_SPECS) != FAZ7C_MODEL_IDS or set(FAZ7C_MODEL_SPECS) & (set(MODEL_SPECS) | set(POST_D1_MODEL_SPECS) |
                                                                            set(FAZ7_MODEL_SPECS)):
    raise AssertionError("FAZ7C_MODEL_SPECS FAZ7C_MODEL_IDS değil ya da var olan modellerle çakışıyor")
# fall_d10_v0_h99@ZERO (H99 taban oranı, 94 satır) ve fall_d10_v0_addsale@ZERO ayrıca kaydedilmez (SPEC_C_V0 §2): karşılaştırıcı
# `base_rate`'tir.


# ---------------------------------------------------------------------------
# Faz 8: kırılma akşamı modeli (docs/specs_faz8/SPEC_BREAK_V0.md, commit 7d78d43, uygulamadan önce; bağlayıcı kararlar
# docs/specs_faz8/KARARLAR.md, §C proje sahibi kararları C1–C5 commit 5d84e88; çeliştiği yerde KARARLAR geçerli). Bir model + bir
# kural satırı. Kayıt aşaması POST_BREAK: `MODEL_SPECS`'e, `models/INDEX.json`'a ve `INDEX_POST_D1.json`'a GİRMEZ; dondurma ayrı
# görevde `models/INDEX_POST_BREAK.json`'a (§7.3). Bu görevde dondurulmaz. Uygulama yorumları docs/SPEC_DEVIATIONS.md N.
# Var olan sözlükler ve fonksiyonlar (`_spec_of`, `model_kind`, `PLAN_KEYS`) değişmedi: Faz 8 kimlikleri yalnız aşağıdaki
# sözlüklerdedir (dondurma görevi `model_kind → post_break` dalını ekler; §9.6).
# Dondurma görevi (BORSAI_FAZ8_FREEZE_20261002; yalnız ekleme): `_spec_of` POST_BREAK_MODEL_SPECS'i tanır, `model_kind` aşama/aile ile
# "post_break" döner (fall denetiminden önce); dondurma `freeze.freeze_post_break` -> models/INDEX_POST_BREAK.json (SPEC_DEVIATIONS N21–N23).
# ---------------------------------------------------------------------------

from . import predict_path as _pth  # noqa: E402
from .predict_break import (ALGORITHM as BREAK_ALGORITHM, EVENT_DEFINITION as BREAK_EVENT_DEFINITION,  # noqa: E402
                            FAMILY as FAMILY_BREAK, REGIME_FON_KRIZI_2026, STAGE as STAGE_POST_BREAK,
                            TARGET_DEFINITION as BREAK_TARGET_DEFINITION)

SPEC_DOCUMENTS_FAZ8: dict[str, dict[str, str]] = {
    "SPEC_BREAK_V0": {"path": "docs/specs_faz8/SPEC_BREAK_V0.md",
                      "sha256": "da98351c2b1bb4d7ef3c9ee5954ff4daade0960eab0ec44daa0b4ba540001f31"},
    "KARARLAR_FAZ8": {"path": "docs/specs_faz8/KARARLAR.md",
                      "sha256": "8d8bbc971b01472f498cc96d5eddd26cdb868406512426a355df213e74d89ce7"},
}
# §7.2: test birimi b ≤ 9 olan her H99 arzı; kesim T_k = E_b(k) (kırılma akşamı); eğitim satırı ancak hedef seansı (F1: D_{b+1},
# F2: D_{b+2}) T_k'den KESİN önce; skorlanabilirlik ≥ 10 satır, ≥ 5 olay, ≥ 5 olay-dışı (başlık başına).
PLAN_BREAK_H99 = "H99_BREAK_WALK_FORWARD_E_CUTOFF_B_LE_9_MIN10ROWS_5EV_5NE"
BREAK_SET_H99 = "H99_BREAK_B_LE_9"
BREAK_HEADS: tuple[str, ...] = ("F1", "F2")
SESSIONS_SOURCE_PATH = "data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv"

H99_BREAK_TRAINING = {
    "set": BREAK_SET_H99,
    "description": ("SESSIONS dosyasından kurulan kırılma tablosu (§7.1): H99'un b ≤ 9 olan 82 arzı (F1), F2 başlığı b ≤ 8 olan 78 "
                    "arz; shares_offered ve arz fiyatı data/training_table.csv'den; tablo sırası (first_trading_date, ticker)"),
    "n_F1": 82,
    "n_F2": 78,
    "cutoff_date": "2026-08-19",
    "data_version_sha256": H99_DATA_VERSION_SHA256,
    "sessions_file": SESSIONS_SOURCE_PATH,
    "sessions_file_sha256": "eca620d3a5e8fed0b118bab556da5ce519257a4b2e14efcd22065f5bcdc93da9",
}
_BREAK_LOGIT = dict(copy.deepcopy(V1_6_H99["logit"]),
                    label="y_h = 1[ertesi işlem görmüş seans(lar)ın kapanışı alt limitte] (p_floor başlığı; F1 ve F2 bağımsız)")
_BREAK_FEATURE_DEFINITIONS = {
    "b_floor": "1[Decimal(KAPANIS FIYATI)_b == Decimal(ALT LIMIT FIYATI)_b]: D_b THB/THM ham metni, Decimal eşitliği (adım/yuvarlama "
               "yok; tavan etiketinin aynası); z-skor (popülasyon std), σ = 0 ise düşer",
    "b_turnover": "ln(TOPLAM ISLEM ADEDI_b / shares_offered): 60 haneli Decimal, bir kez binary64; eğitim [p05, p95]'ine (Type-7, ln "
                  "ölçeğinde) kırpılır, z-skor",
}
_BREAK_INPUT_POLICY = {
    "codes": "B_LIMIT_NA; B_VOLUME_INVALID; B_FIELD_INVALID; INPUT_SHARES_OFFERED (B3 biçimi, öneksiz); D_b işlem görmediyse "
             "B_NOT_TRADED (kayıt yazılmaz)",
    "not_applicable": "b = 10 → B10; L = 10 → NO_BREAK (ret değil); b = 9 → F2 TARGET_UNDEFINED_F2",
    "warnings": "WARN_B_HALF_DAY; WARN_B_INTRADAY_HALT; WARN_B_SPECIAL_TRADES (hacim düzeltilmez); WARN_B_FLOOR_LOCK_ALLDAY (bilgi); "
                "B_TURNOVER_CLIPPED_TO_TRAINING_P05_P95; OUT_OF_TRAINING_RANGE; BAND_RULE_MISMATCH (rozet gizli, BAND_CHANGED)",
    "shares_offered_not_pit": "tahmin üretilir, inputs_pit_ok = false → sınıf RETRO (§9.3)",
}
_BREAK_COMMON: dict[str, Any] = {
    "algorithm": BREAK_ALGORITHM,
    "family": FAMILY_BREAK,
    "stage": STAGE_POST_BREAK,
    "heads": list(BREAK_HEADS),
    "primary_head": "F1",
    "outputs": ["p_floor"],
    "target_definition": dict(BREAK_TARGET_DEFINITION),
    "event_definition": BREAK_EVENT_DEFINITION,
    "min_train_n": 10,
    "scorability": {"min_rows": 10, "min_events": 5, "min_nonevents": 5},
    "grid_version": "v1_6",
    "logit": _BREAK_LOGIT,
    "ridge": None,
    "training": H99_BREAK_TRAINING,
    "plan_id": PLAN_BREAK_H99,
    "structural_zero_rule": {"name": "D10_STRUCTURAL_ZERO", "margin": _pth.MARGIN, "tick_table": _pth.tick_table_json(),
                             "lower_rounding": _pth.LOWER_ROUNDING,
                             "note": "gösterim sabiti; parametre değil, skorlanmaz (§2.4)"},
    "band_rule": {"lower_over_reference": ["0.9", "0.9020"], "upper_over_reference": ["1.098", "1.1"],
                  "on_mismatch": "BAND_RULE_MISMATCH; yastık rozeti gizli; regime_tags BAND_CHANGED"},
    "regime_warning": dict(REGIME_FON_KRIZI_2026),
    "spec_document": SPEC_DOCUMENTS_FAZ8["SPEC_BREAK_V0"],
    "decisions_document": SPEC_DOCUMENTS_FAZ8["KARARLAR_FAZ8"],
    "runtime_pins": RUNTIME_PINS,
}
BREAK_FLOOR_V0: dict[str, Any] = dict(copy.deepcopy(_BREAK_COMMON), **{
    "model_id": "break_floor_v0",
    "description": ("Kırılma akşamı modeli (SPEC_BREAK_V0): seri bozulduğu akşam (b = L + 1 ≤ 9) ertesi işlem görmüş seansın taban "
                    "kapanışı (F1) ve iki ardışık taban (F2) için başlık başına L2-lojistik (V1.6 C ızgarası, iç arz-bırak Brier); "
                    "özellikler kırılma gününün taban kapanışı (b_floor) ve el değiştirmesi (b_turnover); H99'un 82 kırılma akşamı."),
    "features": ["b_floor", "b_turnover"],
    "feature_definitions": _BREAK_FEATURE_DEFINITIONS,
    "preprocessing_id": "BREAK_V0_B_FLOOR_B_TURNOVER_WINSOR_B_TURNOVER_P05_P95_NO_IMPUTATION_NO_F5",
    "preprocessing_winsor": ["b_turnover"],
    "preprocessing_log": [],
    "preprocessing_scope": "başlık başına (F1 ve F2'nin eğitim kümeleri farklıdır; SPEC_DEVIATIONS N)",
    "free_parameters_per_head": 3,
    "comparators": {
        "PRODUCT_BREAK_FLOOR": "tavan yolu durum-2 karışımı (predict_path.conditional_after_break atomları); P_ürün(F1) = Σ{w : r ≤ "
                               "Lo(kapanış_b)/P − 1 + 1e-12}, h = b + 1; F2 Lo∘Lo eşiğiyle, h = b + 2; backtest'te hücreler "
                               "build_cells(cutoff = D_1(k))",
        "break_floor_v0@ZERO": "başlık başına eğitim oranı (kapalı biçim)",
        "base_floor_by_type": "eğitimde test arzının b_floor sınıfındaki F1 oranı (yalnız backtest; canlıda dondurulmuş sınıf oranları)",
    },
    "input_policy": _BREAK_INPUT_POLICY,
})
BREAK_FLOOR_V0_ZERO: dict[str, Any] = dict(copy.deepcopy(_BREAK_COMMON), **{
    "model_id": "break_floor_v0@ZERO",
    "description": ("break_floor_v0 ızgarasının uç noktası (C = ZERO) kural olarak: başlık başına sabit p_floor = eğitim oranı "
                    "(kırılmalar arasındaki taban oranı; kapalı biçim), özellik yok (§4.2). Eğitim kümesi ve plan modelinkiyle aynı."),
    "features": [],
    "parent_model_id": "break_floor_v0",
    "free_parameters_per_head": 1,
    "input_policy": {"required_inputs": [], "note": "kırılma günü alanlarını okumaz; kapsam (b) kuralları aynı"},
})
BREAK_FLOOR_V0_ZERO["logit"]["C_grid"] = ["ZERO"]
FAZ8_MODEL_IDS: tuple[str, ...] = ("break_floor_v0", "break_floor_v0@ZERO")
POST_BREAK_MODEL_SPECS: dict[str, dict[str, Any]] = {s["model_id"]: s for s in (BREAK_FLOOR_V0, BREAK_FLOOR_V0_ZERO)}
if tuple(POST_BREAK_MODEL_SPECS) != FAZ8_MODEL_IDS or set(POST_BREAK_MODEL_SPECS) & (
        set(MODEL_SPECS) | set(POST_D1_MODEL_SPECS) | set(FAZ7_MODEL_SPECS) | set(FAZ7C_MODEL_SPECS)):
    raise AssertionError("POST_BREAK_MODEL_SPECS FAZ8_MODEL_IDS değil ya da var olan modellerle çakışıyor")

# Duyarlılıklar (§7.2; `kind: sensitivity`, model değil): aynı plan, farklı özellik kümesi. `group_Z` = 1[L = 0] (b = 1; §1.2
# Z/B grubu, bütçe nedeniyle özellik değil).
FAZ8_SENSITIVITIES: dict[str, dict[str, Any]] = {
    "break_floor_v0__sens_floor_only": {"features": ["b_floor"], "winsor": []},
    "break_floor_v0__sens_turnover_only": {"features": ["b_turnover"], "winsor": ["b_turnover"]},
    "break_floor_v0__sens_with_group_Z": {"features": ["b_floor", "b_turnover", "group_Z"], "winsor": ["b_turnover"]},
}

# Sonuçlar görülmeden (commit A) sabitlenen değerlendirme kuralları (§5.2, §6, §8; Faz 5 H16 ve Faz 7C T6 kalıbı).
# `borsai/report_faz8.py` bu sabitlerle değerlendirir ve metni MODELS.md'ye aynen yazar.
FAZ8_NEAR_ERA_START = "2024-01-01"
FAZ8_RULES: dict[str, Any] = {
    "ci_min_n": 10,
    "ci_min_months": 6,
    "too_good_primary_diff": -0.160,
    "too_good_primary_ci_hi": -0.080,
    "too_good_zero_diff": -0.090,
    "calibration_expected": 0.06,
    "fail_d_calibration": 0.15,
    "fail_d_min_n": 30,
    "floor_sign_share": 0.90,
    "final_C_likely": (0.1, 1.0),
    "zero_share_max": 0.20,
    "fail_c_zero_share": 0.50,
    "n_F1_range": (60, 69),
    "n_F2_range": (55, 65),
}
OPERATIONAL_RULES_FAZ8: tuple[str, ...] = (
    "Birincil hücre (§5.2; tek): F1 Brier, `break_floor_v0 − PRODUCT_BREAK_FLOOR`, yakın dönem fold'ları (ilk işlem ≥ 2024-01-01). "
    "Brier kırpmasızdır (karşılaştırıcı tam 0/1 verebilir). Eşleşik küme: modelin F1 başlığı FIT_OK, karşılaştırılanın değeri var "
    "(ürün karşılaştırıcısında `POST_BREAK_INSUFFICIENT` ise çift düşer, sayılır), gerçekleşen y_F1 dolu; fark = model − "
    "karşılaştırılan (negatif = model iyi). %95 aralık SPEC_DEVIATIONS C7: ilk işlem ayı blokları, 4000 tekrar, "
    "`random.Random(20260921)`; n < 10 ya da < 6 ay ise aralık yok.",
    "İlan edilmiş ikinciller (aynı yakın dönem fold'ları): F1 − `break_floor_v0@ZERO` (fold'un eğitim oranı), F2 − "
    "`PRODUCT_BREAK_FLOOR`, F2 − `@ZERO`, F1 − `base_floor_by_type` (fold eğitiminde test arzının b_floor sınıfındaki F1 oranı; "
    "sınıf eğitimde yoksa çift düşer). Bilgi: `PRODUCT_BREAK_FLOOR − @ZERO` (F1, birincil hücrenin arzlarında). Keşif (hüküm yok): "
    "bütün fold'lar, 2023 fold'ları, b = 1 ve 2 ≤ b ≤ 9, b_floor sınıfına göre kalibrasyon, ilk işlem yılı. Aralık dili "
    "backtest'tir (\"aralık 0'ın altında / üstünde / 0'ı içeriyor\"); canlı hüküm sözcükleri kullanılmaz.",
    "§6 fark satırları (ilk altı satır): \"Aralık\" sütunu [alt, üst] kapalıdır; \"Beklenen fark\" (nokta) değerlendirilmez. "
    "Gerçekleşen fark alt ucun altındaysa **tutmadı (daha iyi)** (konum: altında — beklentiden çok iyi), üst ucun üstündeyse "
    "**tutmadı (daha kötü)** (konum: üstünde). Aralık içindeyse \"Aralık 0'ı\" ifadesinin kesin kısmına bakılır: \"dışlaması "
    "olası\" ve \"dışlaması olası, garanti değil (alt uç ≤ 0)\" → %95 aralığın alt ucu ≤ 0; \"içerir\" → alt ≤ 0 ≤ üst; \"içerir "
    "ya da negatif dışlar\" → alt uç ≤ 0; \"pozitif dışlar ya da içerir (alt uç ≥ 0)\" → üst uç ≥ 0 (sözcüklerden; parantezdeki "
    "\"alt uç ≥ 0\" sözcüklerle çeliştiği için hükme girmez, ayrı sütunda yazılır — SPEC_DEVIATIONS N). Kesin kısım tutuyorsa "
    "**tuttu**, tutmuyorsa **tutmadı (aralık)**; aralık yoksa **tutmadı (aralık yok)**. İfadenin tamamı (\"dışlaması olası\" → "
    "üst uç < 0; \"içerir\" → 0'ı içerir; \"içerir ya da negatif dışlar\" → alt uç ≤ 0; \"pozitif dışlar ya da içerir\" → üst uç "
    "≥ 0) ayrı sütunda yazılır.",
    "Kalibrasyon satırı: yakın dönem F1 FIT_OK fold'larında (gerçekleşen y_F1 dolu) |ort(p_F1) − gözlenen y_F1 oranı| ≤ 0.06 → "
    "**tuttu**; aksi halde **tutmadı (model yüksek / model düşük)**.",
    "β_floor işareti (iki parça): nihai fit F1'de β_floor > 0; bütün F1 FIT_OK fold'larından C ≠ ZERO ve b_floor düşmemiş olanlarda "
    "β_floor > 0 payı ≥ %90 (düşen ve ZERO fold'ları paydada değil, ayrıca sayılır). İkisi tutarsa **tuttu**, hiçbiri tutmazsa "
    "**tutmadı**, aksi halde **kısmen** (tutmayan parça adıyla).",
    "β_turn işareti: nihai fit F1'de β_turn < 0 → **tuttu**; aksi halde **tutmadı** (> 0 ya da = 0 yönüyle). Fold payı bilgi "
    "olarak yazılır.",
    "Seçilen C (nihai fit F1): C ∈ [0.1, 1] → **tuttu**; C = ZERO → **tutmadı (ZERO)**; diğer → **tutmadı (daha küçük C / daha "
    "büyük C)**. Fold'lar: yakın dönem F1 FIT_OK fold'larında ZERO payı ≤ %20 → **tuttu**.",
    "n satırları: birincil hücrenin eşleşik n'i [60, 69] → **tuttu**; F2 satırı F2 − `PRODUCT_BREAK_FLOOR` hücresinin yakın dönem "
    "eşleşik n'i [55, 65] → **tuttu**; dışında **tutmadı (az / çok)**.",
    "Başarısızlık tanımları (§6, aynen): (a) yakın dönem F1 − `@ZERO` aralığı 0'ı içeriyor (alt ≤ 0 ≤ üst) ya da aralık yok → "
    "\"basit kuraldan ayırt edilemiyor\" (dondurulur, öne çıkarılmaz); (b) birincil aralığın alt ucu > 0 → \"zarar veriyor\" "
    "(kartta \"ürünün cevabından kötü\"); (c) nihai fit F1'de C = ZERO ya da yakın dönem F1 FIT_OK fold'larının ≥ %50'sinde ZERO → "
    "\"özellikler bilgi eklemiyor\"; (d) n ≥ 30 iken |ort(p_F1) − gözlenen| > 0.15 → \"düzey kayması\" notu.",
    "Ön eleme (k1, §8 aşama 1): birincil aralığın üst ucu < 0 VE F1 − `@ZERO` aralığının üst ucu < 0 → \"backtest'te geçiyor "
    "(tasarıma maruz)\"; kart bu durumda modeli \"ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = k\" etiketiyle öne "
    "çıkarabilir. Aksi halde k1 sağlanmaz (tutmayan ayak adıyla yazılır). Eski dönem hiçbir aşamada kullanılmaz.",
    "Beklentiden çok iyi (§6): birincil fark < −0.160 ya da birincil aralığın üst ucu < −0.080 ya da F1 − `@ZERO` farkı < −0.090 → "
    "raporda açıkça yazılır; dondurma bu görevde yoktur. Tetiklense de tetiklenmese de sıradaki adım Fable'ın bu şartnameden bağımsız, "
    "sıfırdan yeniden üretimidir (ledger'lar |Δ| ≤ 1e-9).",
    "Kazanç/kayıp/eşitlik: arz başına Brier farkının işareti; fark bit-eşit 0 ise eşitlik; |fark| ≤ 1e-12 eşitlik sayısı ayrıca "
    "yazılır.",
    "Terazi: bu bölümdeki her sayı backtest'tir (H99 walk-forward, scale = backtest_break) ve tasarıma maruzdur (hipotez ve özellik "
    "seçimi H99'dan; SPEC_BREAK_V0 §12). Canlı terazi (`live_break`, makine sıralı) ve eski dönem bu bölümde yoktur; hiçbir "
    "tabloda toplanmaz.",
)

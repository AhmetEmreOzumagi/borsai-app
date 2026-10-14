"""Düşen arz modeli v0 ailesi (`fall_d10_v0_h99`, `_pooled`, `_addsale`, kural satırı `fall_d10_v0_pooled@ZERO`) tahmini.
Yalnız stdlib (SPEC_C_V0 §2, §3, §8; KARARLAR_C; docs/SPEC_DEVIATIONS.md K).

Çıktı V1.5'in p_up başlığıyla aynı yoldan okunur (`borsai.predict.head_values`): ufuk başına (D5, D10) p_up = P(kapanış > arz);
"düşme olasılığı" (D_h kapanışı ≤ arz fiyatı) = 1 − p_up olarak gösterilir. Getiri başlığı yoktur (`return` = None).

Özellikler (fit ve tahmin aynı tanım):
  f1r      = büyüklük_TL / (TÜFE[T'nin ayı − 2] / 100)  (`predict_hazard.real_size`, SPEC_HAZARD_V1 §3.2 aynen; ceiling_hazard_v1_real
             ile tek tanım); eğitim [p05, p95]'ine ham değerde kırpılır, sonra ln, z-skor.
  f3       = total_demand_multiple (`features.compute_features`); eğitim [p05, p95]'ine kırpılır, sonra ln, z-skor.
  add_sale = 1[Decimal(additional_sale_shares) > 0] (`additional_sale_flag`; SPEC_C_V0 §3.1); z-skor.
`addsale` varyantı yalnız add_sale kullanır (f3 istemez); `@ZERO` hiçbir girdi istemez (sabit başlık = eğitim oranı).

Ret kuralları (etiketli; J5 kalıbı: sabitler `REFUSED_*`, değerler öneksiz), sırası:
  1. V1.5 girdi hataları (`compute_features`: INPUT_MISSING, INPUT_NOT_NUMERIC, …) — f1r/f3 kullanan modellerde;
  2. f3 boş → F3_MISSING; 3. f3 filtre durumu eğitim moduna açıkça zıt → F3_FILTER_STATUS_CONFLICT;
  4. TÜFE (`tufe_index` girdisi; ya da `tufe_refusal` ∈ {TUFE_MISSING, TUFE_NOT_PIT, TUFE_FILE_MISMATCH}) → o kod;
  5. ek satış alanı boş / DATA_NOT_FOUND → ADDITIONAL_SALE_MISSING (0 varsayılmaz; KARARLAR_C C4); negatif → INPUT_NEGATIVE;
     sayı değil → INPUT_NOT_NUMERIC.
Uyarılar: f1r/f3 eğitim p05/p95 dışındaysa kırpılır (FEATURE_CLIPPED_TO_TRAINING_P05_P95; `clipped`, `clipped_features`);
eğitim min/max dışı ham değer OUT_OF_TRAINING_RANGE.

`additional_sale_flag` bu modüldedir (şartname `borsai.features` der; görev kararı T2: pinli `features.py` değişmez; eğitim ve tahmin
aynı fonksiyonu kullanır — SPEC_DEVIATIONS K).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping, Optional

from .features import INPUT_NEGATIVE, FeatureError, compute_features, parse_decimal
from .predict import (EXPLICIT_FILTER_STATUSES, REFUSED_F3_FILTER_CONFLICT, REFUSED_F3_MISSING, SUPPORTED_SCHEMA_VERSIONS,
                      PredictError, _warn, head_values, z_vector)
from .predict_hazard import WARN_FEATURE_CLIPPED, WARN_OUT_OF_TRAINING_RANGE, _tufe_input, real_size

FAMILY_FALL = "fall_d10_v0"
FALL_ALGORITHM = "l2_logit_v1_6_grid"
FALL_HORIZONS: tuple[str, ...] = ("D5", "D10")
FALL_FEATURES: list[str] = ["f1r", "f3", "add_sale"]
ADDSALE_FEATURES: list[str] = ["add_sale"]
WINSOR_LOG_FEATURES: tuple[str, ...] = ("f1r", "f3")
ADDITIONAL_SALE_FIELD = "additional_sale_shares"
ADDITIONAL_SALE_MISSING = "ADDITIONAL_SALE_MISSING"
REFUSED_ADDITIONAL_SALE_MISSING = ADDITIONAL_SALE_MISSING
TARGET_DEFINITION = "1 - Y_h (close(D_h) <= ipo_price)"


def additional_sale_flag(value: Any) -> int:
    """SPEC_C_V0 §3.1: 1[Decimal(additional_sale_shares) > 0]. Boş, None ve DATA_NOT_FOUND → FeatureError
    ADDITIONAL_SALE_MISSING (0 varsayılmaz); negatif → INPUT_NEGATIVE; sayı değil → INPUT_NOT_NUMERIC."""
    parsed = parse_decimal(value, ADDITIONAL_SALE_FIELD, required=False)
    if parsed is None:
        raise FeatureError(ADDITIONAL_SALE_MISSING, ADDITIONAL_SALE_FIELD,
                           "ek satış alanı boş; 'yok' ile 'bulunamadı' karışmaz, 0 varsayılmaz (KARARLAR_C C4)")
    if parsed < 0:
        raise FeatureError(INPUT_NEGATIVE, ADDITIONAL_SALE_FIELD, f"negatif olamaz: {parsed}")
    return 1 if parsed > 0 else 0


def _check_params(params: Mapping[str, Any]) -> None:
    if not isinstance(params, Mapping):
        raise PredictError("PARAMS_INVALID", "params bir sözlük değil")
    if params.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        raise PredictError("SCHEMA_UNSUPPORTED", f"schema_version={params.get('schema_version')!r}")
    if params.get("family") != FAMILY_FALL or params.get("algorithm") != FALL_ALGORITHM:
        raise PredictError("PARAMS_INVALID", f"düşen arz modeli değil: {params.get('family')!r} / {params.get('algorithm')!r}")
    features = list(params.get("features", []))
    if features not in ([], FALL_FEATURES, ADDSALE_FEATURES):
        raise PredictError("PARAMS_INVALID", f"desteklenmeyen özellik listesi {features}")
    horizons = params.get("horizons")
    if not isinstance(horizons, Mapping) or sorted(horizons) != sorted(FALL_HORIZONS):     # JSON anahtarları sıralı yazılır (D10, D5)
        raise PredictError("PARAMS_INVALID", f"ufuklar {list(FALL_HORIZONS)} değil")
    prep = params.get("preprocessing")
    if features:
        if not isinstance(prep, Mapping) or not set(prep.get("columns", [])) <= set(features):
            raise PredictError("PARAMS_INVALID", "ön işleme kolonları özelliklerle uyuşmuyor")
        expect = [f for f in WINSOR_LOG_FEATURES if f in features]
        if sorted(prep.get("winsor", {})) != sorted(expect) or sorted(prep.get("log_transform", [])) != sorted(expect):
            raise PredictError("PARAMS_INVALID", f"kırpma/log özellikleri {expect} değil")
        if "f1r" in features and not isinstance(params.get("deflator"), Mapping):
            raise PredictError("PARAMS_INVALID", "f1r var ama deflator bloğu yok")
    for h, heads in horizons.items():
        if not isinstance(heads, Mapping) or heads.get("return") is not None:
            raise PredictError("PARAMS_INVALID", f"{h}: getiri başlığı olmamalı")
        head = heads.get("p_up")
        kind = head.get("kind") if isinstance(head, Mapping) else None
        if kind == "constant":
            if not isinstance(head.get("value"), (int, float)) or isinstance(head.get("value"), bool):
                raise PredictError("PARAMS_INVALID", f"{h}.p_up: sabit değer yok")
        elif kind == "logit":
            if not features or list(head["columns"]) != list(prep["columns"]) or len(head["coef"]) != len(head["columns"]):
                raise PredictError("PARAMS_INVALID", f"{h}.p_up: kolonlar ön işlemeyle uyuşmuyor")
        else:
            raise PredictError("PARAMS_INVALID", f"{h}.p_up: bilinmeyen kind {kind!r}")


def _emit(params: Mapping[str, Any], z: Optional[list[float]], out: dict[str, Any]) -> dict[str, Any]:
    """V1.5 ufuk girdisi şekli (getiri alanları None): p_up ve yön (UP iff p > 0.5)."""
    for h in FALL_HORIZONS:
        _, p = head_values(params["horizons"][h], z)
        out[h] = {"return": None, "return_unclipped": None, "return_clipped": None, "price": None, "p_up": p,
                  "direction": None if p is None else ("UP" if p > 0.5 else "DOWN")}
    return out


def predict(params: Mapping[str, Any], inputs: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """inputs: V1.5 alanları (ipo_price_tl, shares_offered, post_ipo_share_capital, capital_increase_shares, total_demand_multiple,
    isteğe bağlı total_demand_filter_status, ipo_size_tl) + `tufe_index` (ya da `tufe_refusal`) + `additional_sale_shares`.
    Modelin kullanmadığı alanlar okunmaz. Dönen: {"model_id", "D5", "D10": {return: None, …, p_up, direction} | None,
    "warnings", "refused": None | {code, field, reason}, "clipped", "clipped_features", "f1r_raw", "tufe_index_used",
    "add_sale_used"}."""
    _check_params(params)
    inputs = inputs or {}
    out: dict[str, Any] = {"model_id": params.get("model_id"), "D5": None, "D10": None, "warnings": [], "refused": None,
                           "clipped": None, "clipped_features": None, "f1r_raw": None, "tufe_index_used": None,
                           "add_sale_used": None}

    def refuse(code: str, field: Optional[str], reason: str) -> dict[str, Any]:
        out["refused"] = {"code": code, "field": field, "reason": reason}
        return out

    features = list(params["features"])
    if not features:
        return _emit(params, None, out)
    policy = params.get("input_policy", {})
    prep = params["preprocessing"]
    values: dict[str, float] = {}
    if "f3" in features:
        try:
            feats = compute_features(
                ipo_price_tl=inputs.get("ipo_price_tl"), shares_offered=inputs.get("shares_offered"),
                post_ipo_share_capital=inputs.get("post_ipo_share_capital"),
                capital_increase_shares=inputs.get("capital_increase_shares"),
                total_demand_multiple=inputs.get("total_demand_multiple"), ipo_size_tl=inputs.get("ipo_size_tl"),
            )
        except FeatureError as exc:
            return refuse(exc.code, exc.field, str(exc))
        if feats.f3 is None:
            return refuse(REFUSED_F3_MISSING, "total_demand_multiple",
                          "Toplam talep katı (f3) yok; bu model f3'süz tahmin vermez. f3'süz düşüş tahmini fall_d10_v0_addsale'den "
                          "gelir.")
        status, mode = inputs.get("total_demand_filter_status"), prep.get("f3_filter_mode")
        if status in EXPLICIT_FILTER_STATUSES and mode in EXPLICIT_FILTER_STATUSES and status != mode \
                and policy.get("f3_filter_status_conflict") == "REFUSE":
            return refuse(REFUSED_F3_FILTER_CONFLICT, "total_demand_filter_status",
                          f"f3 filtre durumu {status}, eğitimdeki mod {mode}: talep katları karşılaştırılamaz.")
        idx, code, reason = _tufe_input(inputs)
        if code is not None:
            return refuse(code, "tufe_index", reason)
        values["f1r"] = float(real_size(feats.f1, idx))
        values["f3"] = float(feats.f3)
        out["f1r_raw"], out["tufe_index_used"] = values["f1r"], str(idx)
    try:
        flag = additional_sale_flag(inputs.get(ADDITIONAL_SALE_FIELD))
    except FeatureError as exc:
        return refuse(exc.code, exc.field, str(exc))
    values["add_sale"] = float(flag)
    out["add_sale_used"] = flag
    for fid, rng in params.get("feature_ranges", {}).items():
        v = values.get(fid)
        if v is not None and not (rng["min"] <= v <= rng["max"]):
            out["warnings"].append(_warn(
                WARN_OUT_OF_TRAINING_RANGE, f"{fid} = {v!r} eğitim aralığı dışında [{rng['min']!r}, {rng['max']!r}]",
                feature=fid, value=v, train_min=rng["min"], train_max=rng["max"],
            ))
    clipped: list[str] = []
    for col in prep["columns"]:
        w = prep["winsor"].get(col)
        if w is not None and not (w["p05"] <= values[col] <= w["p95"]):
            used = min(max(values[col], w["p05"]), w["p95"])
            clipped.append(col)
            out["warnings"].append(_warn(WARN_FEATURE_CLIPPED, f"{col} = {values[col]!r} eğitim p05/p95 sınırına kırpıldı: {used!r}",
                                         feature=col, value=values[col], used=used))
    out["clipped"], out["clipped_features"] = bool(clipped), clipped
    return _emit(params, z_vector(prep, values), out)


def fall_probability(p_up: float) -> float:
    """Gösterim: P(D_h kapanışı ≤ arz fiyatı) = 1 − p_up (SPEC_C_V0 §2, §9)."""
    return 1.0 - p_up


def feature_values_exact(f1_tl: Optional[Decimal], f3: Optional[Decimal], tufe_index: Any, additional_sale: Any,
                         features: list[str]) -> dict[str, Any]:
    """Eğitim tarafının ham değerleri (Decimal / int; ön işleme kesin aritmetikle yürür): tahminle aynı fonksiyonlar
    (`real_size`, `additional_sale_flag`)."""
    out: dict[str, Any] = {}
    if "f1r" in features:
        out["f1r"] = real_size(f1_tl, tufe_index)
    if "f3" in features:
        out["f3"] = f3
    if "add_sale" in features:
        out["add_sale"] = Decimal(additional_sale_flag(additional_sale))
    return out

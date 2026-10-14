"""Tavan serisi tahmini: `ceiling_hazard_v0`, `pb_ceiling_v0`, @INF uçları ve Kaplan–Meier
kuralları (SPEC_CEILING_V0 §7, §8; SPEC_PB_V0 §9). Yalnız stdlib.

Çıktı (liste indeksi k − 1; P_L için l):
  hazard[d]          d = 1..10, h_d = sigmoid(γ_{g(d)} + β·z)
  S[k]               P(seri ≥ k) = Π_{d≤k}(1 − h_d)          (birincil çıktı)
  P_L[l]             P(L = l), l = 0..10 (toplam 1)
  P_close_ceiling[k] P(Dk'de tavan kapanışı) = S_k + (1 − S_k)·r   (ikincil, türetilmiş)
Beklenen getiri eşlemesi v0'da yoktur (SPEC_CEILING_V0 §8).

Girdi kuralları:
- ceiling_hazard_v0: V1.5 girdileri (borsai.features.compute_features). f3 yoksa RET
  (F3_MISSING); f3 eğitim p05/p95 dışındaysa kırpılır, `clipped = True` + uyarı;
  f1–f3 eğitim min/max dışındaysa tahmin + uyarı; hesaplanamayan girdi etiketli RET.
- pb_ceiling_v0: 8 planlanan yapı alanı (borsai.features.compute_pb_features);
  f3 istenmez. PB RET kuralları borsai/predict_pb.py ile aynı.
- @INF ve KM kuralları: girdi kullanmaz (sabit eğri).

Faz 7 `ceiling_hazard_v1_*` (SPEC_HAZARD_V1 §3, §9; JSON `family = "ceiling_hazard_v1"`):
- clip: f1, f2, f3 üçü de eğitim p05/p95'ine kırpılır; her kırpma için uyarı FEATURE_CLIPPED_TO_TRAINING_P05_P95
  (feature, value, used); `clipped` = herhangi biri, `clipped_features` = liste (v0'ın F3_CLIPPED kodu v0'da aynen kalır).
- real / pooled: f1 yerine f1r = büyüklük / (TÜFE / 100) (`real_size`, Decimal 60 hane; tek tanım). TÜFE değeri girdi
  `tufe_index`'tir (T'nin ayı − 2; `borsai.tufe.index_for`, dondurma/kayıt hazırlar). Yoksa RET TUFE_MISSING; girdi
  `tufe_refusal` ∈ {TUFE_MISSING, TUFE_NOT_PIT, TUFE_FILE_MISMATCH} ise o kodla RET.
- pooled (+ @INF): η_d = γ_{g(d)} + δ·r + β·z. `alloc_regime` girdisi yoksa canlı: r = regime.live_value (0); varsa (eski
  kohort kaydı) r = 1[etiket ≠ EQUAL_DIST_20230330], bilinmeyen/boş etiket RET REGIME_UNKNOWN. Çıktı regime_value_used.
- OUT_OF_TRAINING_RANGE ham değer üzerinden (kırpma sonrası da yazılır; bilgi).
v0/PB/KM çıktıları (anahtarlar ve değerler) değişmez.
"""
from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation, localcontext
from typing import Any, Mapping, Optional

from . import survival as sv
from .features import FeatureError, PBRefusal, compute_features, compute_pb_features
from .predict import REFUSED_F3_MISSING, SUPPORTED_SCHEMA_VERSIONS, PredictError, _warn, z_vector

HAZARD_ALGORITHM = "discrete_time_hazard_logit_l2"
KM_ALGORITHMS = frozenset({"KM_EXPANDING", "KM_LAST10"})
CEILING_FEATURES = ["f1", "f2", "f3"]
PB_CEILING_FEATURES = ["pb1", "pb2"]
CEILING_V1_REAL_FEATURES = ["f1r", "f2", "f3"]
WARN_OUT_OF_TRAINING_RANGE = "OUT_OF_TRAINING_RANGE"
WARN_F3_CLIPPED = "F3_CLIPPED_TO_TRAINING_P05_P95"
WARN_PB4_POSITIVE = "PB4_ADDITIONAL_SALE_CEILING"
# Faz 7
FAMILY_V1 = "ceiling_hazard_v1"
WARN_FEATURE_CLIPPED = "FEATURE_CLIPPED_TO_TRAINING_P05_P95"
REFUSED_TUFE_MISSING = "TUFE_MISSING"
REFUSED_TUFE_NOT_PIT = "TUFE_NOT_PIT"
REFUSED_TUFE_FILE_MISMATCH = "TUFE_FILE_MISMATCH"
TUFE_REFUSALS = frozenset({REFUSED_TUFE_MISSING, REFUSED_TUFE_NOT_PIT, REFUSED_TUFE_FILE_MISMATCH})
REFUSED_REGIME_UNKNOWN = "REGIME_UNKNOWN"
EQUAL_DIST = "EQUAL_DIST_20230330"
# Tahsis rejimi etiketi -> r (SPEC_HAZARD_V1 §3.3: r = 1[ALLOC_REGIME != EQUAL_DIST_20230330]; etiket kümesi registry.REGIME_VALUES).
REGIME_R: dict[str, int] = {"PRE_20211111": 1, "THRESH100_20211111": 1, EQUAL_DIST: 0}
REGIME_SOURCE_LIVE = "LIVE_VALUE"
REGIME_SOURCE_INPUT = "ALLOC_REGIME_INPUT"
_REAL_CTX = Context(prec=60, rounding=ROUND_HALF_EVEN)


def real_size(size_tl: Decimal, tufe_index: Any) -> Decimal:
    """f1r'nin ham değeri (2025 TL): büyüklük_TL / (TÜFE / 100), Decimal 60 hane, tek bölme yuvarlaması (SPEC_HAZARD_V1 §3.2).
    Eğitim (borsai/backtest.py) ve tahmin aynı fonksiyonu kullanır; ön işleme winsor -> ln -> z'yi uygular."""
    idx = Decimal(repr(tufe_index)) if isinstance(tufe_index, float) else Decimal(str(tufe_index).strip())
    if not idx.is_finite() or idx <= 0 or not size_tl.is_finite() or size_tl <= 0:
        raise ValueError(f"real_size: pozitif sonlu değil ({size_tl!r}, {tufe_index!r})")
    with localcontext(_REAL_CTX):
        return size_tl / (idx / Decimal(100))


def regime_value(label: Any) -> int:
    """Tahsis rejimi etiketi -> r; bilinmeyen etiket ValueError."""
    if label not in REGIME_R:
        raise ValueError(f"bilinmeyen tahsis rejimi {label!r}")
    return REGIME_R[label]


def _check_params(params: Mapping[str, Any]) -> None:
    if not isinstance(params, Mapping):
        raise PredictError("PARAMS_INVALID", "params bir sözlük değil")
    if params.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        raise PredictError("SCHEMA_UNSUPPORTED", f"schema_version={params.get('schema_version')!r}")
    algorithm = params.get("algorithm")
    if algorithm in KM_ALGORITHMS:
        curve = params.get("survival", {}).get("S")
        if not isinstance(curve, list) or len(curve) != sv.DAYS:
            raise PredictError("PARAMS_INVALID", "survival.S 10 değer değil")
        return
    if algorithm != HAZARD_ALGORITHM:
        raise PredictError("PARAMS_INVALID", f"tavan modeli değil: {algorithm!r}")
    features = list(params.get("features", []))
    v1 = params.get("family") == FAMILY_V1
    if features not in (([], CEILING_FEATURES, CEILING_V1_REAL_FEATURES) if v1 else ([], CEILING_FEATURES, PB_CEILING_FEATURES)):
        raise PredictError("PARAMS_INVALID", f"desteklenmeyen özellik listesi {features}")
    if v1:
        if features and set(params.get("preprocessing", {}).get("winsor", {})) != set(features):
            raise PredictError("PARAMS_INVALID", "v1: kırpma sınırları üç özelliğin hepsi için değil")
        if "f1r" in features and not isinstance(params.get("deflator"), Mapping):
            raise PredictError("PARAMS_INVALID", "v1: f1r var ama deflator bloğu yok")
        reg = params.get("regime")
        if reg is not None and (not isinstance(reg.get("delta"), (int, float)) or isinstance(reg.get("delta"), bool)
                                or reg.get("penalized") is not False or reg.get("live_value") not in (0, 1)):
            raise PredictError("PARAMS_INVALID", "v1: regime bloğu geçersiz (delta, penalized, live_value)")
    if {k: list(v) for k, v in params.get("day_groups", {}).items()} != {k: list(v) for k, v in sv.DAY_GROUPS.items()}:
        raise PredictError("PARAMS_INVALID", "gün grupları şartnameyle aynı değil")
    if len(params.get("gamma", [])) != len(sv.GROUP_NAMES) or set(params.get("beta", {})) != set(features):
        raise PredictError("PARAMS_INVALID", "gamma/beta boyutu tutmuyor")
    prep = params.get("preprocessing")
    if features and (prep is None or not set(prep["columns"]) <= set(features)):
        raise PredictError("PARAMS_INVALID", "ön işleme kolonları özelliklerle uyuşmuyor")
    if not {"r_a", "r_b"} <= set(params.get("reclose_rates", {})):
        raise PredictError("PARAMS_INVALID", "reclose_rates yok")


def _range_warnings(params: Mapping[str, Any], values: Mapping[str, Optional[float]], out: dict[str, Any]) -> None:
    for fid, rng in params.get("feature_ranges", {}).items():
        v = values.get(fid)
        if v is not None and not (rng["min"] <= v <= rng["max"]):
            out["warnings"].append(_warn(
                WARN_OUT_OF_TRAINING_RANGE, f"{fid} = {v!r} eğitim aralığı dışında [{rng['min']!r}, {rng['max']!r}]",
                feature=fid, value=v, train_min=rng["min"], train_max=rng["max"],
            ))


def _curves(hazards: list[float], rates: Mapping[str, float], out: dict[str, Any]) -> dict[str, Any]:
    S = sv.survival(hazards)
    out.update(hazard=hazards, S=S, P_L=sv.p_streak(S), P_close_ceiling=sv.p_close(S, rates["r_a"], rates["r_b"]))
    return out


def predict(params: Mapping[str, Any], inputs: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Dönen: {"model_id", "hazard", "S", "P_L", "P_close_ceiling" (listeler) | None, "clipped",
    "warnings": [...], "refused": None | {code, field, reason}}."""
    _check_params(params)
    inputs = inputs or {}
    out: dict[str, Any] = {"model_id": params.get("model_id"), "hazard": None, "S": None, "P_L": None,
                           "P_close_ceiling": None, "clipped": None, "warnings": [], "refused": None}
    if params["algorithm"] in KM_ALGORITHMS:
        curve = params["survival"]
        return _curves([float(h) for h in curve["hazard"]], params["reclose_rates"], out)
    lp = _linear(params, inputs)
    out.update(clipped=lp["clipped"], warnings=lp["warnings"], refused=lp["refused"])
    if params.get("family") == FAMILY_V1:
        out.update({k: lp[k] for k in _V1_OUTPUT_KEYS if k in lp})
    if lp["refused"]:
        return out
    hazards = [sv.sigmoid(eta) for eta in lp["eta"]]
    return _curves(hazards, params["reclose_rates"], out)


def linear_predictor(params: Mapping[str, Any], inputs: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Hazard modelinin doğrusal öngörücüsü: η_d = γ_{g(d)} + β·z, d = 1..10 (`predict` ile tek hesap yolu; h_d =
    sigmoid(η_d)). Dönen: {"model_id", "refused", "warnings", "clipped", "z": {kolon: z} | None, "lin": β·z | None,
    "eta": [η_1..η_10] | None}. D1 sonrası modelin ofseti buradan gelir (SPEC_POST_D1_V0 §3.1); logit(hazard) geri
    dönüşümü kullanılmaz. KM kurallarının doğrusal öngörücüsü yoktur (PARAMS_INVALID)."""
    _check_params(params)
    if params["algorithm"] != HAZARD_ALGORITHM:
        raise PredictError("PARAMS_INVALID", f"doğrusal öngörücü yalnız hazard modelinde: {params['algorithm']!r}")
    return _linear(params, inputs or {})


_V1_OUTPUT_KEYS = ("clipped_features", "f1r_raw", "tufe_index_used", "regime_value_used", "regime_source")


def _linear(params: Mapping[str, Any], inputs: Mapping[str, Any]) -> dict[str, Any]:
    if params.get("family") == FAMILY_V1:
        return _linear_v1(params, inputs)
    out: dict[str, Any] = {"model_id": params.get("model_id"), "refused": None, "warnings": [], "clipped": None,
                           "z": None, "lin": None, "eta": None}

    def refuse(code: str, field: Optional[str], reason: str) -> dict[str, Any]:
        out["refused"] = {"code": code, "field": field, "reason": reason}
        return out

    features = list(params["features"])
    z: dict[str, float] = {}
    if features == CEILING_FEATURES:
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
                          "Toplam talep katı (f3) yok; bu model f3'süz tahmin vermez. f3'süz tavan tahmini pb_ceiling_v0'dan gelir.")
        values = {k: float(v) for k, v in feats.as_dict().items() if k in CEILING_FEATURES}
        _range_warnings(params, values, out)
        w = params["preprocessing"]["winsor"].get("f3")
        out["clipped"] = bool(w is not None and not (w["p05"] <= values["f3"] <= w["p95"]))
        if out["clipped"]:
            used = min(max(values["f3"], w["p05"]), w["p95"])
            out["warnings"].append(_warn(WARN_F3_CLIPPED, f"f3 = {values['f3']!r} eğitim p05/p95 sınırına kırpıldı: {used!r}",
                                         feature="f3", value=values["f3"], used=used))
    elif features == PB_CEILING_FEATURES:
        try:
            pb = compute_pb_features(inputs)
        except PBRefusal as exc:
            return refuse(exc.code, exc.field, str(exc))
        values = {"pb1": pb.pb1, "pb2": pb.pb2}
        _range_warnings(params, values, out)
        if pb.pb4 > 0:
            out["warnings"].append(_warn(WARN_PB4_POSITIVE, f"ek satış tavanı var (pb4 = {pb.pb4!r}); eğitimde 7 örnek.",
                                         feature="pb4", value=pb.pb4))
    if features:
        prep = params["preprocessing"]
        z = dict(zip(prep["columns"], z_vector(prep, values)))
    lin = sum(params["beta"][c] * z[c] for c in z)
    gamma = params["gamma"]
    out.update(z=z, lin=lin, eta=[gamma[sv.GROUP_OF_DAY[d]] + lin for d in range(1, sv.DAYS + 1)])
    return out


def _tufe_input(inputs: Mapping[str, Any]) -> tuple[Optional[Decimal], Optional[str], str]:
    """(endeks, ret kodu, açıklama). Dondurma/kayıt `tufe_index` (metin) ya da `tufe_refusal` (TUFE_* kodu) verir."""
    code = inputs.get("tufe_refusal")
    raw = inputs.get("tufe_index")
    if code is not None:
        code = code if code in TUFE_REFUSALS else REFUSED_TUFE_MISSING
        return None, code, f"TÜFE (T'nin ayı − 2) kullanılamıyor: {code}. Bu model deflatörsüz tahmin vermez; imputasyon yok."
    if raw is None or (isinstance(raw, str) and raw.strip() == "") or isinstance(raw, bool):
        return None, REFUSED_TUFE_MISSING, "TÜFE endeksi (T'nin ayı − 2) verilmedi. Bu model deflatörsüz tahmin vermez; imputasyon yok."
    try:
        idx = Decimal(repr(raw)) if isinstance(raw, float) else Decimal(str(raw).strip())
    except (InvalidOperation, ValueError):
        return None, REFUSED_TUFE_MISSING, f"TÜFE endeksi sayı değil: {raw!r}"
    if not idx.is_finite() or idx <= 0:
        return None, REFUSED_TUFE_MISSING, f"TÜFE endeksi pozitif sonlu değil: {raw!r}"
    return idx, None, ""


def _linear_v1(params: Mapping[str, Any], inputs: Mapping[str, Any]) -> dict[str, Any]:
    """`ceiling_hazard_v1_*` doğrusal öngörücüsü: η_d = γ_{g(d)} (+ δ·r) + β·z (SPEC_HAZARD_V1 §12)."""
    out: dict[str, Any] = {"model_id": params.get("model_id"), "refused": None, "warnings": [], "clipped": None,
                           "clipped_features": None, "z": None, "lin": None, "eta": None}

    def refuse(code: str, field: Optional[str], reason: str) -> dict[str, Any]:
        out["refused"] = {"code": code, "field": field, "reason": reason}
        return out

    features = list(params["features"])
    z: dict[str, float] = {}
    if features:
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
                          "Toplam talep katı (f3) yok; bu model f3'süz tahmin vermez. f3'süz tavan tahmini pb_ceiling_v0'dan gelir.")
        if "f1r" in features:
            idx, code, reason = _tufe_input(inputs)
            if code is not None:
                return refuse(code, "tufe_index", reason)
            f1r = real_size(feats.f1, idx)
            values = {"f1r": float(f1r), "f2": float(feats.f2), "f3": float(feats.f3)}
            out["f1r_raw"] = values["f1r"]
            out["tufe_index_used"] = str(idx)
        else:
            values = {"f1": float(feats.f1), "f2": float(feats.f2), "f3": float(feats.f3)}
        _range_warnings(params, values, out)
        prep = params["preprocessing"]
        clipped: list[str] = []
        for col in prep["columns"]:
            w = prep["winsor"].get(col)
            if w is not None and not (w["p05"] <= values[col] <= w["p95"]):
                used = min(max(values[col], w["p05"]), w["p95"])
                clipped.append(col)
                out["warnings"].append(_warn(WARN_FEATURE_CLIPPED, f"{col} = {values[col]!r} eğitim p05/p95 sınırına kırpıldı: {used!r}",
                                             feature=col, value=values[col], used=used))
        out["clipped"] = bool(clipped)
        out["clipped_features"] = clipped
        z = dict(zip(prep["columns"], z_vector(prep, values)))
    regime = params.get("regime")
    dr = None
    if regime is not None:
        if "alloc_regime" in inputs:
            label = inputs.get("alloc_regime")
            if label not in REGIME_R:
                return refuse(REFUSED_REGIME_UNKNOWN, "alloc_regime",
                              f"tahsis rejimi etiketi bilinmiyor ({label!r}); eski kohort kaydı kohort satırındaki ALLOC_REGIME'i verir.")
            r, source = REGIME_R[label], REGIME_SOURCE_INPUT
        else:
            r, source = regime["live_value"], REGIME_SOURCE_LIVE
        out["regime_value_used"], out["regime_source"] = r, source
        dr = regime["delta"] * r
    lin = sum(params["beta"][c] * z[c] for c in z)
    gamma = params["gamma"]
    if dr is None:
        eta = [gamma[sv.GROUP_OF_DAY[d]] + lin for d in range(1, sv.DAYS + 1)]
    else:
        eta = [gamma[sv.GROUP_OF_DAY[d]] + dr + lin for d in range(1, sv.DAYS + 1)]
    out.update(z=z, lin=lin, eta=eta)
    return out

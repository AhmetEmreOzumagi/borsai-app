"""predict(params, inputs): dondurulmuş parametre dosyasıyla tahmin.

SAF: yalnız Python stdlib (math; f1–f4 tanımı için borsai.features -> decimal).
numpy / scikit-learn / scipy import edilmez (tests/test_predict.py bunu
alt süreçte sınar).

Kurallar:
- V1.5'te f3 (talep katı) boşsa RET (AUDIT §1.2-d; gerekçe yanıtta).
- f3'ün filtre durumu eğitim moduna açıkça zıtsa f3 kullanılamaz: RET.
- f4 = 0 kabul edilir; "eğitimde örneği yok" uyarısı verilir.
- f1–f4 eğitim aralığı dışındaysa girdi başına uyarı. f3 p05/p95 dışındaysa
  winsor sınırına kırpılır ve uyarılır (eğitimdeki ön işlemeyle aynı).
- Getiri fiziksel sınıra [0.9^h − 1, 1.1^h − 1] kırpılır ve işaretlenir;
  kırpılmamış değer de döner.
- Girdi hataları (eksik, sayı değil, sıfıra bölme, tutarsız) etiketli RET olur;
  parametre dosyası hatası etiketli PredictError fırlatır. Çıplak exception yok.

Aynı fonksiyon `v1_6_h99`'u da çalıştırır (INF/ZERO uçlarında katsayılar 0,
sabit terim ortalama/log-oran). `v1_5_market20_v0` borsai/predict_market20.py
üzerinden çağrılır: f6 hazır değer olarak `extra_features` ile gelir; gelmezse
etiketli RET (FEATURE_NOT_PROVIDED). pb_v0 ve tavan modelleri kendi stdlib
modüllerindedir (predict_pb.py, predict_hazard.py).

Sayısal alan: binary64. Ön işleme parametreleri (μ, σ, p05/p95) JSON'da
binary64'tür; eğitimdeki 60 haneli Decimal hesabından farkı ~1e-15 düzeyindedir
(parite testi |Δ| ≤ 1e-12).
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Optional

from .features import FeatureError, compute_features, parse_decimal
from .horizons import physical_return_bounds

SUPPORTED_SCHEMA_VERSIONS = frozenset({"borsai.model/1"})
EXPLICIT_FILTER_STATUSES = frozenset({"FILTERED", "UNFILTERED"})

REFUSED_F3_MISSING = "F3_MISSING"
REFUSED_F3_FILTER_CONFLICT = "F3_FILTER_STATUS_CONFLICT"
REFUSED_FEATURE_NOT_PROVIDED = "FEATURE_NOT_PROVIDED"
WARN_OUT_OF_TRAINING_RANGE = "OUT_OF_TRAINING_RANGE"
WARN_F4_ZERO = "F4_ZERO_NO_TRAINING_EXAMPLE"
WARN_F3_WINSORIZED = "F3_WINSORIZED"
WARN_RETURN_CLIPPED = "RETURN_CLIPPED_TO_PHYSICAL_BOUND"


class PredictError(ValueError):
    """Parametre dosyası geçersiz ya da desteklenmiyor."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def _check_params(params: Mapping[str, Any]) -> None:
    if not isinstance(params, Mapping):
        raise PredictError("PARAMS_INVALID", "params bir sözlük değil")
    if params.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        raise PredictError("SCHEMA_UNSUPPORTED", f"schema_version={params.get('schema_version')!r}")
    horizons = params.get("horizons")
    if not isinstance(horizons, Mapping) or not horizons:
        raise PredictError("PARAMS_INVALID", "horizons yok")
    prep = params.get("preprocessing")
    for h, heads in horizons.items():
        for name in ("return", "p_up"):
            head = heads.get(name)
            if head is None:
                continue
            kind = head.get("kind")
            if kind == "constant":
                if not isinstance(head.get("value"), (int, float)):
                    raise PredictError("PARAMS_INVALID", f"{h}.{name}: sabit değer yok")
            elif kind in ("ridge", "logit"):
                if prep is None or list(head["columns"]) != list(prep["columns"]) or len(head["coef"]) != len(head["columns"]):
                    raise PredictError("PARAMS_INVALID", f"{h}.{name}: kolonlar ön işlemeyle uyuşmuyor")
            else:
                raise PredictError("PARAMS_INVALID", f"{h}.{name}: bilinmeyen kind {kind!r}")


def _sigmoid(d: float) -> float:
    if d >= 0:
        return 1.0 / (1.0 + math.exp(-d))
    e = math.exp(d)
    return e / (1.0 + e)


def z_vector(prep: Mapping[str, Any], feats: Mapping[str, Optional[float]]) -> list[float]:
    """Ön işleme parametrelerini tek satıra uygular (binary64). f3 None ise eğitim
    medyanı ve f5 = 1 kullanılır; bu yol yalnız model matematiği içindir,
    `predict` f3'süz girdiyi bu noktaya gelmeden reddeder."""
    z: list[float] = []
    f3_missing = feats.get("f3") is None
    for col in prep["columns"]:
        if col == "f5":
            x = 1.0 if f3_missing else 0.0
        else:
            x = feats.get(col)
            if x is None:
                x = prep["medians"][col]
            if col in prep["winsor"]:
                w = prep["winsor"][col]
                x = min(max(x, w["p05"]), w["p95"])
            if col in prep["log_transform"]:
                x = math.log(x)
        z.append((x - prep["mean"][col]) / prep["std"][col])
    return z


def head_values(heads: Mapping[str, Any], z: Optional[list[float]]) -> tuple[Optional[float], Optional[float]]:
    """(ham getiri, p_up). Doğrusal kısım: sabit + Σ katsayı·z (sklearn ile aynı sıra)."""
    ret = p = None
    rh = heads.get("return")
    if rh is not None:
        ret = float(rh["value"]) if rh["kind"] == "constant" else sum(c * v for c, v in zip(rh["coef"], z)) + rh["intercept"]
    ph = heads.get("p_up")
    if ph is not None:
        p = float(ph["value"]) if ph["kind"] == "constant" else _sigmoid(sum(c * v for c, v in zip(ph["coef"], z)) + ph["intercept"])
    return ret, p


def _warn(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **extra}


def predict(params: Mapping[str, Any], inputs: Mapping[str, Any], *,
            extra_features: Optional[Mapping[str, float]] = None) -> dict[str, Any]:
    """inputs: ipo_price_tl, shares_offered, post_ipo_share_capital,
    capital_increase_shares, total_demand_multiple, isteğe bağlı
    total_demand_filter_status ve ipo_size_tl (kaynakta bildirilen arz büyüklüğü).
    Değerler metin ya da sayı olabilir. `extra_features`: f1–f4 dışında modelin
    kullandığı, çağıranın hazır verdiği özellikler (market20 için f6).

    Dönen: {"model_id", "D1".."D10": {return, return_unclipped, return_clipped,
    price, p_up, direction} | None, "warnings": [...], "refused": None | {code, field, reason}}."""
    _check_params(params)
    horizons = list(params["horizons"])
    out: dict[str, Any] = {"model_id": params.get("model_id"), "warnings": [], "refused": None}
    for h in horizons:
        out[h] = None

    def refuse(code: str, field: Optional[str], reason: str) -> dict[str, Any]:
        out["refused"] = {"code": code, "field": field, "reason": reason}
        return out

    uses_features = bool(params.get("features"))
    try:
        price = parse_decimal(inputs.get("ipo_price_tl"), "ipo_price_tl")
        if price <= 0:
            raise FeatureError("INPUT_NOT_POSITIVE", "ipo_price_tl", f"pozitif olmalı: {price}")
        feats = None
        if uses_features:
            feats = compute_features(
                ipo_price_tl=inputs.get("ipo_price_tl"),
                shares_offered=inputs.get("shares_offered"),
                post_ipo_share_capital=inputs.get("post_ipo_share_capital"),
                capital_increase_shares=inputs.get("capital_increase_shares"),
                total_demand_multiple=inputs.get("total_demand_multiple"),
                ipo_size_tl=inputs.get("ipo_size_tl"),
            )
    except FeatureError as exc:
        return refuse(exc.code, exc.field, str(exc))

    z = None
    if uses_features:
        policy = params.get("input_policy", {})
        prep = params["preprocessing"]
        if feats.f3 is None and policy.get("f3_missing") == "REFUSE":
            return refuse(
                REFUSED_F3_MISSING, "total_demand_multiple",
                "Toplam talep katı (f3) yok; bu model f3'süz tahmin vermez. " + policy.get("f3_missing_reason", ""),
            )
        status = inputs.get("total_demand_filter_status")
        mode = prep.get("f3_filter_mode")
        if feats.f3 is not None and status in EXPLICIT_FILTER_STATUSES and mode in EXPLICIT_FILTER_STATUSES and status != mode:
            if policy.get("f3_filter_status_conflict") == "REFUSE":
                return refuse(
                    REFUSED_F3_FILTER_CONFLICT, "total_demand_filter_status",
                    f"f3 filtre durumu {status}, eğitimdeki mod {mode}: talep katları karşılaştırılamaz.",
                )
        values = {k: (None if v is None else float(v)) for k, v in feats.as_dict().items()}
        values.update(extra_features or {})
        for col in prep["columns"]:
            if col != "f5" and values.get(col) is None and col not in prep["medians"]:
                return refuse(REFUSED_FEATURE_NOT_PROVIDED, col, f"{col} modelin girdisidir ve verilmedi; impute edilmez.")
        for fid, rng in params.get("feature_ranges", {}).items():
            v = values.get(fid)
            if v is not None and not (rng["min"] <= v <= rng["max"]):
                out["warnings"].append(_warn(
                    WARN_OUT_OF_TRAINING_RANGE, f"{fid} = {v!r} eğitim aralığı dışında [{rng['min']!r}, {rng['max']!r}]",
                    feature=fid, value=v, train_min=rng["min"], train_max=rng["max"],
                ))
        if values["f4"] == 0.0 and params.get("feature_ranges", {}).get("f4", {}).get("min", 0.0) > 0.0:
            out["warnings"].append(_warn(
                WARN_F4_ZERO, "f4 = 0 (sermaye artırımı yok): eğitimde f4 = 0 olan arz yok; tahmin dışdeğerlemedir.",
                feature="f4", value=0.0,
            ))
        w = prep["winsor"].get("f3")
        if w is not None and values["f3"] is not None and not (w["p05"] <= values["f3"] <= w["p95"]):
            clamped = min(max(values["f3"], w["p05"]), w["p95"])
            out["warnings"].append(_warn(
                WARN_F3_WINSORIZED, f"f3 = {values['f3']!r} eğitim p05/p95 sınırına kırpıldı: {clamped!r}",
                feature="f3", value=values["f3"], used=clamped,
            ))
        z = z_vector(prep, values)

    return emit_horizons(params, z, float(price), out)


def emit_horizons(params: Mapping[str, Any], z: Optional[list[float]], price_f: float, out: dict[str, Any]) -> dict[str, Any]:
    """Ufuk başına getiri (fiziksel sınıra kırpılmış ve ham), fiyat, p_up, yön."""
    for h in params["horizons"]:
        raw_ret, p = head_values(params["horizons"][h], z)
        entry: dict[str, Any] = {"return": None, "return_unclipped": raw_ret, "return_clipped": None,
                                 "price": None, "p_up": p, "direction": None}
        if raw_ret is not None:
            lo, hi = physical_return_bounds(h)
            ret = min(max(raw_ret, lo), hi)
            if ret != raw_ret:
                entry["return_clipped"] = "UPPER" if raw_ret > hi else "LOWER"
                out["warnings"].append(_warn(
                    WARN_RETURN_CLIPPED, f"{h} getirisi {raw_ret!r} fiziksel sınıra kırpıldı: {ret!r}",
                    horizon=h, value=raw_ret, used=ret,
                ))
            entry["return"] = ret
            entry["price"] = price_f * (1.0 + ret)
        if p is not None:
            entry["direction"] = "UP" if p > 0.5 else "DOWN"
        out[h] = entry
    return out

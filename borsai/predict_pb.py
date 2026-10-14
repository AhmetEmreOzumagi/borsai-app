"""`pb_v0` tahmini: talep toplama öncesi, SPK onaylı planlanan yapıdan (SPEC_PB_V0). Yalnız stdlib.

Girdiler (8 sayısal alan, metin ya da sayı): ipo_price_try, planned_pre_ipo_capital,
planned_post_ipo_capital, planned_capital_increase_shares, planned_existing_share_sale,
planned_base_offer_shares, planned_additional_sale_ceiling, planned_max_offer_shares.
Başka hiçbir alan okunmaz (f3, nihai pay sayısı, ek satış kullanılmaz).

Kurallar (SPEC_PB_V0 §5):
- alan boş/ayrıştırılamıyor -> RET PB_FIELD_MISSING (field = alan adı); imputasyon yok
- ID-A/B/C ya da aralık ihlali -> RET PB_IDENTITY (field = ID-A, …, PB2_RANGE)
- fiyat tek değer değil (aralık) -> RET PB_PRICE_RANGE
- eğitim min/max dışı -> tahmin + uyarı; pb4 > 0 -> tahmin + uyarı
- getiri [0.9^h − 1, 1.1^h − 1]'e kırpılır ve işaretlenir (borsai/predict.py ile aynı)
"""
from __future__ import annotations

from typing import Any, Mapping

from .features import PBRefusal, compute_pb_features, parse_pb_decimal
from .predict import PredictError, _check_params, _warn, emit_horizons, z_vector

WARN_OUT_OF_TRAINING_RANGE = "OUT_OF_TRAINING_RANGE"
WARN_PB4_POSITIVE = "PB4_ADDITIONAL_SALE_CEILING"


def predict(params: Mapping[str, Any], inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Dönen: {"model_id", "D1".."D10": {return, return_unclipped, return_clipped, price, p_up,
    direction} | None, "features": {pb1..pb4} | None, "warnings": [...], "refused": None | {code, field, reason}}."""
    _check_params(params)
    if not any(str(f).startswith("pb") for f in params.get("features", [])):
        raise PredictError("PARAMS_INVALID", "PB modeli değil (özellikler pb1..)")
    out: dict[str, Any] = {"model_id": params.get("model_id"), "warnings": [], "refused": None, "features": None}
    for h in params["horizons"]:
        out[h] = None
    try:
        f = compute_pb_features(inputs)
    except PBRefusal as exc:
        out["refused"] = {"code": exc.code, "field": exc.field, "reason": str(exc)}
        return out
    values = f.as_dict()
    out["features"] = {**values, "pb4": f.pb4}
    for fid, rng in params.get("feature_ranges", {}).items():
        v = values.get(fid)
        if v is not None and not (rng["min"] <= v <= rng["max"]):
            out["warnings"].append(_warn(
                WARN_OUT_OF_TRAINING_RANGE, f"{fid} = {v!r} eğitim aralığı dışında [{rng['min']!r}, {rng['max']!r}]",
                feature=fid, value=v, train_min=rng["min"], train_max=rng["max"],
            ))
    if f.pb4 > 0:
        out["warnings"].append(_warn(
            WARN_PB4_POSITIVE, f"ek satış tavanı var (pb4 = {f.pb4!r}); eğitimde 7 örnek.", feature="pb4", value=f.pb4,
        ))
    z = z_vector(params["preprocessing"], values)
    return emit_horizons(params, z, float(parse_pb_decimal(inputs.get("ipo_price_try"), "ipo_price_try")), out)

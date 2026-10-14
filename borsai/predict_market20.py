"""`v1_5_market20_v0` tahmini (SPEC_MARKET20_V0 §7, §10). Yalnız stdlib.

f6'yı bu modül hesaplamaz: Python tarafı (borsai/market20.py) üretir ve dondurma
girdisine yazar; uygulama hazır değeri verir. Girdiler V1.5'inkiler + şunlar:
  f6_market20          f6 değeri (metin ya da sayı) ya da None
  f6_market20_refusal  f6 hesaplanamadıysa market20 neden kodu
                       (CALENDAR_NOT_COVERING, INSUFFICIENT_HISTORY, XU100_CLOSE_MISSING,
                       STALE_S0, PREDICTION_TOO_EARLY, XU100_INTEGRITY)
f6 yoksa RET: `MARKET20_<NEDEN>` (neden verilmemişse MARKET20_NOT_PROVIDED); imputasyon
yok. Sonra V1.5 kuralları (f3 yoksa RET, aralık dışı uyarı, fiziksel sınır) aynen
borsai/predict.py'den; f6 eğitim aralığı dışındaysa uyarı.
"""
from __future__ import annotations

from typing import Any, Mapping

from .features import FeatureError, parse_decimal
from .predict import predict as _predict_core

REFUSED_MARKET20_PREFIX = "MARKET20_"
MARKET20_NOT_PROVIDED = "NOT_PROVIDED"
MARKET20_REASONS = frozenset({
    "CALENDAR_NOT_COVERING", "INSUFFICIENT_HISTORY", "XU100_CLOSE_MISSING", "STALE_S0",
    "PREDICTION_TOO_EARLY", "XU100_INTEGRITY", MARKET20_NOT_PROVIDED,
})


def predict(params: Mapping[str, Any], inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Dönen yapı borsai.predict.predict ile aynı; ek olarak `f6_market20` (kullanılan değer)."""
    horizons = list(params.get("horizons") or [])
    reason = inputs.get("f6_market20_refusal")
    try:
        f6 = parse_decimal(inputs.get("f6_market20"), "f6_market20", required=False)
    except FeatureError as exc:
        return {"model_id": params.get("model_id"), "warnings": [], **{h: None for h in horizons},
                "refused": {"code": REFUSED_MARKET20_PREFIX + "NOT_NUMERIC", "field": "f6_market20", "reason": str(exc)},
                "f6_market20": None}
    if f6 is None:
        code = reason if reason in MARKET20_REASONS else MARKET20_NOT_PROVIDED
        return {"model_id": params.get("model_id"), "warnings": [], **{h: None for h in horizons},
                "refused": {"code": REFUSED_MARKET20_PREFIX + code, "field": "f6_market20",
                            "reason": f"f6 (20 seanslık XU100 getirisi) yok: {code}. Bu model f6'sız tahmin vermez; imputasyon yok."},
                "f6_market20": None}
    out = _predict_core(params, inputs, extra_features={"f6": float(f6)})
    out["f6_market20"] = float(f6)
    return out

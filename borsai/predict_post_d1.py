"""D1 sonrası güncelleme tahmini: `post_d1_hazard_v0` (SPEC_POST_D1_V0 §1.3, §2, §3.1, §9, §12). Yalnız stdlib.

Model (§3.1): arz i, gün d ∈ 2..10, x = (f1, f2, f3), w = (d1_lock, d1_turnover):
    η^base_d(x) = γ^base_{g(d)} + β^base·z^base(x)      dondurulmuş ceiling_hazard_v0 (ofset, sabit; yeniden fit yok)
    logit h_d   = η^base_d(x) + δ·u(w),  d = 2..10          u = z-skorlu (d1_lock, d1_turnover)
    h_1         = sigmoid(η^base_1(x))                      ana modelden aynen
Ofset `predict_hazard.linear_predictor`'dan gelir (`predict_hazard.predict` ile tek hesap yolu); logit(hazard) geri dönüşümü
kullanılmaz. δ = 0 için özel dal yoktur: λ = INF ucunun karşılaştırıcıya bit-eşitliği genel yoldan gelir.

Çıktı: standart hazard şeması (hazard, S, P_L, P_close_ceiling; P_close ana modelin reclose_rates'iyle) + `conditional_j1`
{S_cond (k = 2..10), p_break_next = 1 − S_cond[2], P_L_cond (l = 1..10)} (tek tanım: `predict_path.conditional_weights(S, 1)`)
+ `path_conditional` (ikincil: `predict_path.conditional(ceiling_path_v0, çıktı ⊕ bu modelin S'i, j = 1, [kapanış(D_1)])`,
tek tanım) ya da None.

Girdi: `parent` = models/ceiling_hazard_v0.json nesnesinin tamamı (ofsetin sayıları yalnız buradan); `path_params` =
ceiling_path_v0 nesnesi (isteğe bağlı); `inputs` = listeleme öncesi kaydın `model_inputs`'u; `d1` = D_1 bülten bloğu
{"fields_raw": {open, high, low, close, volume, trade_count, upper_limit, special_trade_volume?, …} (ham metin),
"half_day": 0/1, "halt_flag": 0/1}. Dosyaların sha256'sını INDEX.json ile denetlemek çağıranın işidir; burada JSON'daki
kopya alanlar (parent: model_id, gamma, beta, preprocessing_id; miras feature_ranges) verilen parent'la birebir eşit
değilse PARAMS_INVALID.

Sıra (§12): ana model reddi aynen döner → D_1 işlem görmediyse D1_NOT_TRADED (kayıt yazılmaz; PredictError) → üst limit
yok/≤ 0 RET D1_LIMIT_NA → kapanış ≠ üst limit NOT_APPLICABLE D1_NOT_CEILING (ret değil) → hacim yok/≤ 0 RET
D1_VOLUME_INVALID → fiyat alanı yok RET D1_FIELD_INVALID → shares_offered geçersiz RET INPUT_SHARES_OFFERED. Uyarılar:
WARN_D1_HALF_DAY, WARN_D1_INTRADAY_HALT, WARN_D1_SPECIAL_TRADES (hacim düzeltilmez), WARN_D1_LOCK_INCONSISTENT,
D1_TURNOVER_CLIPPED_TO_TRAINING_P05_P95, OUT_OF_TRAINING_RANGE. Kodlar SPEC_DEVIATIONS B3 biçiminde (öneksiz).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, DivisionByZero, InvalidOperation, Overflow, localcontext
from typing import Any, Mapping, Optional, Sequence

from . import predict_hazard as ph
from . import predict_path as pth
from . import survival as sv
from .features import FeatureError, parse_decimal
from .predict import SUPPORTED_SCHEMA_VERSIONS, PredictError, _warn

ALGORITHM = "discrete_time_hazard_offset_logit_l2"
STAGE = "POST_D1"
PARENT_MODEL_ID = "ceiling_hazard_v0"
PATH_MODEL_ID = "ceiling_path_v0"
D1_COLUMNS: tuple[str, ...] = ("d1_lock", "d1_turnover")
UPDATED_DAYS: tuple[int, ...] = tuple(range(2, sv.DAYS + 1))
CONDITION_J = 1

D1_NOT_TRADED = "D1_NOT_TRADED"
REFUSED_D1_LIMIT_NA = "D1_LIMIT_NA"
REFUSED_D1_VOLUME_INVALID = "D1_VOLUME_INVALID"
REFUSED_D1_FIELD_INVALID = "D1_FIELD_INVALID"
REFUSED_INPUT_SHARES_OFFERED = "INPUT_SHARES_OFFERED"
NOT_APPLICABLE_D1_NOT_CEILING = "D1_NOT_CEILING"
WARN_D1_HALF_DAY = "WARN_D1_HALF_DAY"
WARN_D1_INTRADAY_HALT = "WARN_D1_INTRADAY_HALT"
WARN_D1_SPECIAL_TRADES = "WARN_D1_SPECIAL_TRADES"
WARN_D1_LOCK_INCONSISTENT = "WARN_D1_LOCK_INCONSISTENT"
WARN_D1_TURNOVER_CLIPPED = "D1_TURNOVER_CLIPPED_TO_TRAINING_P05_P95"
WARN_OUT_OF_TRAINING_RANGE = ph.WARN_OUT_OF_TRAINING_RANGE

# ln(hacim / arz edilen pay): 60 haneli Decimal, bir kez binary64 (§12).
_LN = Context(prec=60, rounding=ROUND_HALF_EVEN, traps=[InvalidOperation, DivisionByZero, Overflow])


class D1Refusal(ValueError):
    """Etiketli ret (RET kodu, alan, neden)."""

    def __init__(self, code: str, field: Optional[str], reason: str) -> None:
        self.code, self.field = code, field
        super().__init__(f"{code}: {reason}")


class D1NotApplicable(ValueError):
    """D1 tavanda kapanmadı: model tanımlı değil (ret değil, kapsam dışı; §1.2)."""

    code = NOT_APPLICABLE_D1_NOT_CEILING


@dataclass(frozen=True)
class D1Values:
    """D_1 satırından iki özellik ve tutarlılık bilgisi (ham metinden Decimal)."""

    ceiling_close: int
    lock: int
    turnover_ratio: Decimal       # hacim / arz edilen pay (60 hane)
    turnover_ln: float            # ln(oran), bir kez binary64
    lock_consistency: dict[str, bool]
    warnings: tuple[dict[str, Any], ...]

    def features(self) -> dict[str, float]:
        return {"d1_lock": float(self.lock), "d1_turnover": self.turnover_ln}


def _raw(fields: Mapping[str, Any], name: str) -> Optional[Decimal]:
    """Bülten alanı: boş, eksik ya da sayı olmayan metin -> None."""
    try:
        return parse_decimal(fields.get(name), name, required=False)
    except FeatureError:
        return None


def evaluate_d1(d1: Mapping[str, Any], shares_offered: Any) -> D1Values:
    """§2 tanımları ve ret/uyarı tablosu (tek tanım: backtest ve tahmin aynı fonksiyonu çağırır).
    Yükseltir: PredictError(D1_NOT_TRADED), D1Refusal, D1NotApplicable."""
    f = d1.get("fields_raw") or {}
    close, trades = _raw(f, "close"), _raw(f, "trade_count")
    if close is None or close <= 0 or trades is None or trades <= 0:
        raise PredictError(D1_NOT_TRADED, "D_1 işlem görmemiş (sözleşme sayısı ya da kapanış yok/≤ 0; SPEC_SCORING §2): "
                                          "D_1 henüz oluşmadı, POST_D1 kaydı yazılamaz")
    upper = _raw(f, "upper_limit")
    if upper is None or upper <= 0:
        raise D1Refusal(REFUSED_D1_LIMIT_NA, "upper_limit", "D_1 THM üst limiti yok ya da ≤ 0 (tavan etiketi NA; SPEC_SCORING §3)")
    if close != upper:
        raise D1NotApplicable(f"D_1 kapanışı {close} ≠ üst limit {upper}: model yalnız D1'i tavanda kapatan arzlarda tanımlı")
    volume = _raw(f, "volume")
    if volume is None or volume <= 0:
        raise D1Refusal(REFUSED_D1_VOLUME_INVALID, "volume", "TOPLAM ISLEM ADEDI boş/≤ 0 iken sözleşme sayısı > 0 (veri "
                                                              "tutarsızlığı; bülten satırı elle incelenir)")
    prices = {name: _raw(f, name) for name in ("low", "open", "high")}
    for name, value in prices.items():
        if value is None or value <= 0:
            raise D1Refusal(REFUSED_D1_FIELD_INVALID, name, f"D_1 THB {name} alanı yok ya da ≤ 0 (veri tutarsızlığı)")
    try:
        shares = parse_decimal(shares_offered, "shares_offered")
    except FeatureError as exc:
        raise D1Refusal(REFUSED_INPUT_SHARES_OFFERED, "shares_offered", str(exc)) from exc
    if shares <= 0:
        raise D1Refusal(REFUSED_INPUT_SHARES_OFFERED, "shares_offered", f"arz edilen pay pozitif değil: {shares}")
    lock = int(prices["low"] == upper)
    consistency = {"open_at_U": prices["open"] == upper, "high_at_U": prices["high"] == upper, "close_at_U": close == upper}
    warnings: list[dict[str, Any]] = []
    if lock and not all(consistency.values()):
        warnings.append(_warn(WARN_D1_LOCK_INCONSISTENT, "en düşük = üst limit ama açılış/en yüksek/kapanış üst limite eşit "
                                                         "değil; bülten satırı elle incelenmeli", **consistency))
    if int(d1.get("half_day") or 0):
        warnings.append(_warn(WARN_D1_HALF_DAY, "D1 yarım gün: el değiştirme kısa seansta ölçüldü (H99'da örnek yok)"))
    if int(d1.get("halt_flag") or 0):
        warnings.append(_warn(WARN_D1_INTRADAY_HALT, "D1'de gün içi geçici durdurma (H99'da örnek yok)"))
    special = _raw(f, "special_trade_volume")
    if special is not None and special > 0:
        warnings.append(_warn(WARN_D1_SPECIAL_TRADES, "özel işlem bildirimi hacmi > 0; hacim düzeltilmedi (resmi toplam)",
                              special_trade_volume=str(special), volume=str(volume)))
    with localcontext(_LN):
        ratio = volume / shares
        ln = ratio.ln()
    return D1Values(ceiling_close=1, lock=lock, turnover_ratio=ratio, turnover_ln=float(ln),
                    lock_consistency=consistency, warnings=tuple(warnings))


# ============================================================ ortak hesap (numpy fit'i de bunu çağırır)

def d1_transform(prep: Mapping[str, Any], values: Mapping[str, float]) -> tuple[dict[str, float], bool, float]:
    """JSON ön işlemesi (binary64): d1_turnover [p05, p95]'e kırpılır; aktif kolonlar z-skor. (u, kırpıldı mı, kullanılan)."""
    clip = prep["clip"]["d1_turnover"]
    raw = values["d1_turnover"]
    used = min(max(raw, clip["p05"]), clip["p95"])
    x = {"d1_lock": values["d1_lock"], "d1_turnover": used}
    u = {c: (x[c] - prep["mean"][c]) / prep["std"][c] for c in prep["columns"]}
    return u, not (clip["p05"] <= raw <= clip["p95"]), used


def updated_hazards(eta: Sequence[float], delta: Mapping[str, float], u: Mapping[str, float], columns: Sequence[str]) -> list[float]:
    """h_1 = sigmoid(η_1) (ana modelle aynı işlem); h_d = sigmoid(η_d + δ·u), d = 2..10."""
    shift = sum(delta[c] * u[c] for c in columns)
    return [sv.sigmoid(eta[0])] + [sv.sigmoid(eta[d - 1] + shift) for d in UPDATED_DAYS]


def curves(hazards: Sequence[float], reclose: Mapping[str, float]) -> dict[str, Any]:
    """Standart hazard şeması + j = 1 koşullu görünüm (tek tanım: predict_path.conditional_weights)."""
    S = sv.survival(hazards)
    s_cond, pl_cond = pth.conditional_weights(S, CONDITION_J)
    return {"hazard": list(hazards), "S": S, "P_L": sv.p_streak(S), "P_close_ceiling": sv.p_close(S, reclose["r_a"], reclose["r_b"]),
            "conditional_j1": {"S_cond": {str(k): v for k, v in s_cond.items()}, "p_break_next": 1.0 - s_cond[2],
                               "P_L_cond": {str(t): v for t, v in pl_cond.items()}}}


def path_conditional(path_params: Mapping[str, Any], path_output: Mapping[str, Any], S: Sequence[float],
                     close_d1: Any) -> Optional[dict[str, Any]]:
    """İkincil çıktı (§1.3): ceiling_path_v0'ın hücreleri ve limit yolu, S yerine bu modelin S'i, j = 1. Kaynak çıktı
    reddedilmişse ya da limit yolu yoksa None."""
    if path_output.get("refused") or path_output.get("limit_path") is None:
        return None
    return pth.conditional(path_params, {**path_output, "S": list(S)}, CONDITION_J, [close_d1])


# ============================================================ parametre denetimi

def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def check_params(params: Mapping[str, Any], parent: Mapping[str, Any], path_params: Optional[Mapping[str, Any]] = None) -> None:
    if not isinstance(params, Mapping) or not isinstance(parent, Mapping):
        raise PredictError("PARAMS_INVALID", "params/parent bir sözlük değil")
    if params.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        raise PredictError("SCHEMA_UNSUPPORTED", f"schema_version={params.get('schema_version')!r}")
    if params.get("algorithm") != ALGORITHM or params.get("stage") != STAGE:
        raise PredictError("PARAMS_INVALID", f"D1 sonrası model değil: {params.get('algorithm')!r} / {params.get('stage')!r}")
    copy = params.get("parent") or {}
    if copy.get("model_id") != PARENT_MODEL_ID or parent.get("model_id") != PARENT_MODEL_ID \
            or parent.get("algorithm") != ph.HAZARD_ALGORITHM:
        raise PredictError("PARAMS_INVALID", "parent ceiling_hazard_v0 değil")
    if copy.get("gamma") != parent.get("gamma") or copy.get("beta") != parent.get("beta") \
            or copy.get("preprocessing_id") != (parent.get("preprocessing") or {}).get("preprocessing_id"):
        raise PredictError("PARAMS_INVALID", "parent kopya alanları (gamma, beta, preprocessing_id) verilen parent'la aynı değil")
    ranges = params.get("feature_ranges") or {}
    if any(ranges.get(f) != r for f, r in (parent.get("feature_ranges") or {}).items()):
        raise PredictError("PARAMS_INVALID", "miras feature_ranges parent'ınkiyle aynı değil")
    if list(params.get("updated_days", [])) != list(UPDATED_DAYS):
        raise PredictError("PARAMS_INVALID", "güncellenen günler 2..10 değil")
    delta, prep = params.get("delta") or {}, params.get("d1_preprocessing") or {}
    columns = list(prep.get("columns", []))
    if set(delta) != set(D1_COLUMNS) or not all(_finite(v) for v in delta.values()):
        raise PredictError("PARAMS_INVALID", "delta iki D1 katsayısı değil")
    if not set(columns) <= set(D1_COLUMNS) or columns != [c for c in D1_COLUMNS if c in columns]:
        raise PredictError("PARAMS_INVALID", "d1_preprocessing.columns D1 özelliklerinin sıralı alt kümesi değil")
    if any(delta[c] != 0.0 for c in D1_COLUMNS if c not in columns):
        raise PredictError("PARAMS_INVALID", "düşen özelliğin katsayısı 0 değil")
    clip = (prep.get("clip") or {}).get("d1_turnover") or {}
    if not (_finite(clip.get("p05")) and _finite(clip.get("p95")) and clip["p05"] <= clip["p95"]):
        raise PredictError("PARAMS_INVALID", "d1_turnover kırpma sınırları yok")
    if not all(_finite(prep.get("mean", {}).get(c)) and _finite(prep.get("std", {}).get(c)) and prep["std"][c] > 0 for c in columns):
        raise PredictError("PARAMS_INVALID", "aktif D1 kolonunun ortalama/std'si yok ya da std ≤ 0")
    if path_params is not None:
        sec = params.get("path_secondary") or {}
        if (path_params.get("algorithm") != pth.ALGORITHM or path_params.get("model_id") != PATH_MODEL_ID
                or sec.get("model_id") != PATH_MODEL_ID or path_params.get("survival_model_sha256") != copy.get("sha256")):
            raise PredictError("PARAMS_INVALID", "path_conditional kaynağı ceiling_path_v0 değil ya da gömülü seri modeli parent değil")


# ============================================================ predict

def predict_post_d1(params: Mapping[str, Any], parent: Mapping[str, Any], inputs: Optional[Mapping[str, Any]],
                    d1: Mapping[str, Any], *, path_params: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Dönen: {"model_id", "stage", "refused": None | {code, field, reason}, "not_applicable": None | {code, reason},
    "warnings", "clipped" (f3, ana modelden), "hazard", "S", "P_L", "P_close_ceiling", "conditional_j1",
    "path_conditional", "d1_features"}. D_1 işlem görmediyse PredictError(D1_NOT_TRADED)."""
    check_params(params, parent, path_params)
    inputs = inputs or {}
    base = ph.linear_predictor(parent, inputs)
    out: dict[str, Any] = {"model_id": params.get("model_id"), "stage": STAGE, "refused": None, "not_applicable": None,
                           "warnings": list(base["warnings"]), "clipped": base["clipped"], "hazard": None, "S": None,
                           "P_L": None, "P_close_ceiling": None, "conditional_j1": None, "path_conditional": None,
                           "d1_features": None}
    if base["refused"]:
        out["refused"] = base["refused"]
        return out
    try:
        values = evaluate_d1(d1, inputs.get("shares_offered"))
    except D1Refusal as exc:
        out["refused"] = {"code": exc.code, "field": exc.field, "reason": str(exc)}
        return out
    except D1NotApplicable as exc:
        out["not_applicable"] = {"code": exc.code, "reason": str(exc)}
        return out
    out["warnings"] += list(values.warnings)
    prep = params["d1_preprocessing"]
    raw = values.features()
    for fid in D1_COLUMNS:
        rng = params["feature_ranges"].get(fid)
        if rng is not None and not (rng["min"] <= raw[fid] <= rng["max"]):
            out["warnings"].append(_warn(WARN_OUT_OF_TRAINING_RANGE, f"{fid} = {raw[fid]!r} eğitim aralığı dışında "
                                                                     f"[{rng['min']!r}, {rng['max']!r}]",
                                         feature=fid, value=raw[fid], train_min=rng["min"], train_max=rng["max"]))
    u, clipped, used = d1_transform(prep, raw)
    if clipped:
        out["warnings"].append(_warn(WARN_D1_TURNOVER_CLIPPED, f"d1_turnover = {raw['d1_turnover']!r} eğitim p05/p95 sınırına "
                                                               f"kırpıldı: {used!r}", feature="d1_turnover",
                                     value=raw["d1_turnover"], used=used))
    hazards = updated_hazards(base["eta"], params["delta"], u, prep["columns"])
    out.update(curves(hazards, parent["reclose_rates"]))
    out["d1_features"] = {"d1_lock": values.lock, "d1_turnover_ratio": str(values.turnover_ratio),
                          "d1_turnover_ln": values.turnover_ln, "clipped": clipped, "d1_turnover_used": used, "z": u,
                          "ceiling_close_D1": values.ceiling_close, "lock_consistency": dict(values.lock_consistency)}
    if path_params is not None:
        out["path_conditional"] = path_conditional(path_params, pth.predict(path_params, inputs), out["S"],
                                                   d1["fields_raw"]["close"])
    return out

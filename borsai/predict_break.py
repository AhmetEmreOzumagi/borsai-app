"""Kırılma akşamı modeli `break_floor_v0` (kural satırı `break_floor_v0@ZERO`) tahmini, yastık kuralı ve ürün karşılaştırıcısı.
Yalnız stdlib (SPEC_BREAK_V0 §1–§5, §11; KARARLAR C1–C5; docs/SPEC_DEVIATIONS.md N).

Olay (§1.2): L = D1'den başlayan kesintisiz tavan sayısı, b = L + 1 = ilk tavan olmayan işlem görmüş kapanışın seans numarası.
Kırılma akşamı E_b = D_b'nin tarihi (THB yayımından sonra). Kapsam b ∈ 1..9; b = 10 → `not_applicable` B10, L = 10 →
`not_applicable` NO_BREAK (ret değil). b = 9'da F2 tanımsız (`TARGET_UNDEFINED_F2`).

Hedefler (§2): F1 = 1[kapanış(D_{b+1}) == alt limit(D_{b+1})] (ertesi seans taban kapanışı), F2 = F1 ve D_{b+2} taban. Çıktı
`p_floor` (başlık başına). D10 ≤ arz için model çıktısı yoktur; yalnız yastık kuralı `D10_STRUCTURAL_ZERO` (§2.4; parametre değil).

Özellikler (§3; fit ve tahmin aynı fonksiyon `evaluate_break_day`):
  b_floor    = 1[Decimal(KAPANIS)_b == Decimal(ALT LIMIT)_b]  (ham metin; adım/yuvarlama yok, tavan etiketinin aynası)
  b_turnover = ln(TOPLAM ISLEM ADEDI_b / shares_offered)      (60 haneli Decimal, bir kez binary64)
Ön işleme başlık başınadır (F1 ve F2'nin eğitim kümeleri farklı; SPEC_DEVIATIONS N): b_turnover eğitim [p05, p95]'ine
kırpılır, iki kolon z-skor; σ = 0 olan kolon düşer. JSON z yolu `predict.z_vector` (tek tanım).

Ret (B3 biçimi, öneksiz; sırası): D_b işlem görmediyse PredictError(B_NOT_TRADED) → alt limit yok/≤ 0 B_LIMIT_NA → hacim
yok/≤ 0 (sözleşme > 0) B_VOLUME_INVALID → açılış/en yüksek/en düşük yok/≤ 0 B_FIELD_INVALID → shares_offered geçersiz
INPUT_SHARES_OFFERED. Uyarılar: WARN_B_HALF_DAY, WARN_B_INTRADAY_HALT, WARN_B_SPECIAL_TRADES (hacim düzeltilmez),
WARN_B_FLOOR_LOCK_ALLDAY (bilgi), B_TURNOVER_CLIPPED_TO_TRAINING_P05_P95, OUT_OF_TRAINING_RANGE, BAND_RULE_MISMATCH
(alt limit/referans ∉ [0.9, 0.9020] ya da üst limit/referans ∉ [1.098, 1.1]: yastık rozeti gizlenir, `regime_tags` BAND_CHANGED;
tahmin yine üretilir).

Ürün karşılaştırıcısı `PRODUCT_BREAK_FLOOR` (§5.1): tavan yolu durum-2 karışımı (`predict_path.conditional_after_break` ile aynı
atomlar; atomlar `predict_path.mixture_atoms`'tan, ikinci karışım kodu yok); P_ürün(F1) = Σ{w : r ≤ Lo(kapanış_b)/P − 1 + 1e-12},
h = b + 1; F2 aynı biçimde Lo∘Lo eşiğiyle, h = b + 2.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, DivisionByZero, InvalidOperation, Overflow, localcontext
from typing import Any, Mapping, Optional, Sequence

from . import predict_path as pth
from .features import FeatureError, parse_decimal
from .predict import SUPPORTED_SCHEMA_VERSIONS, PredictError, _sigmoid, _warn, z_vector

ALGORITHM = "l2_logit_v1_6_grid"
FAMILY = "break_floor_v0"
STAGE = "POST_BREAK"
HEADS: tuple[str, ...] = ("F1", "F2")
FEATURES: tuple[str, ...] = ("b_floor", "b_turnover")
WINSOR_FEATURES: tuple[str, ...] = ("b_turnover",)
DAYS = pth.DAYS
B_MAX = DAYS - 1                       # b ∈ 1..9 (D_{b+1} ≤ D10)
F2_B_MAX = DAYS - 2                    # F2 b ≤ 8
TARGET_DEFINITION = {"F1": "close(D_{b+1}) == lower_limit(D_{b+1})",
                     "F2": "F1 and close(D_{b+2}) == lower_limit(D_{b+2})"}
EVENT_DEFINITION = "b = L + 1, first traded non-ceiling close; b in 1..9"

B_NOT_TRADED = "B_NOT_TRADED"
REFUSED_B_LIMIT_NA = "B_LIMIT_NA"
REFUSED_B_VOLUME_INVALID = "B_VOLUME_INVALID"
REFUSED_B_FIELD_INVALID = "B_FIELD_INVALID"
REFUSED_INPUT_SHARES_OFFERED = "INPUT_SHARES_OFFERED"
NOT_APPLICABLE_B10 = "B10"
NOT_APPLICABLE_NO_BREAK = "NO_BREAK"
TARGET_UNDEFINED_F2 = "TARGET_UNDEFINED_F2"
WARN_B_HALF_DAY = "WARN_B_HALF_DAY"
WARN_B_INTRADAY_HALT = "WARN_B_INTRADAY_HALT"
WARN_B_SPECIAL_TRADES = "WARN_B_SPECIAL_TRADES"
WARN_B_FLOOR_LOCK_ALLDAY = "WARN_B_FLOOR_LOCK_ALLDAY"
WARN_B_TURNOVER_CLIPPED = "B_TURNOVER_CLIPPED_TO_TRAINING_P05_P95"
WARN_OUT_OF_TRAINING_RANGE = "OUT_OF_TRAINING_RANGE"
WARN_BAND_RULE_MISMATCH = "BAND_RULE_MISMATCH"
TAG_BAND_CHANGED = "BAND_CHANGED"

# §1.3 bant koruması (THM'den ölçülür; H99'da alt 0.90000…0.90183, üst 1.09817…1.10000).
BAND_LOWER: tuple[Decimal, Decimal] = (Decimal("0.9"), Decimal("0.9020"))
BAND_UPPER: tuple[Decimal, Decimal] = (Decimal("1.098"), Decimal("1.1"))

# §11 rejim uyarısı (KARARLAR C4: bitiş tarihi proje sahibi verene kadar açık). Model girdisi değildir; n'den düşülmez.
REGIME_FON_KRIZI_2026 = {
    "tag": "FON_KRIZI_2026",
    "start_d1": "2026-09-16",
    "end_d1": None,
    "text": ("Bu arzın ilk seansları Eylül 2026 fon krizi penceresine düşüyor; eğitim kümesinde (2023-09…2026-08) böyle bir "
             "stres yok. Beklenti (önceden yazıldı): model tabanı az tahmin eder."),
}

# §2.4 yastık kuralı (gösterim sabiti; parametre değil, skorlanmaz).
STRUCTURAL_ZERO_RULE = "D10_STRUCTURAL_ZERO"
PRODUCT_COMPARATOR = "PRODUCT_BREAK_FLOOR"
PRODUCT_OK = pth.STATUS_OK
PRODUCT_INSUFFICIENT = pth.STATUS_POST_BREAK_INSUFFICIENT
PRODUCT_EPS = 1e-12

# ln ve oranlar: 60 haneli Decimal, bir kez binary64 (predict_post_d1 ile aynı bağlam).
_LN = Context(prec=60, rounding=ROUND_HALF_EVEN, traps=[InvalidOperation, DivisionByZero, Overflow])
_LN_STEP_TEXT = "1/0.9"


class BreakRefusal(ValueError):
    """Etiketli ret (RET kodu, alan, neden)."""

    def __init__(self, code: str, field: Optional[str], reason: str) -> None:
        self.code, self.field = code, field
        super().__init__(f"{code}: {reason}")


@dataclass(frozen=True)
class BreakValues:
    """D_b satırından iki özellik ve bilgi alanları (ham metinden Decimal)."""

    b_floor: int
    turnover_ratio: Decimal       # hacim / arz edilen pay (60 hane)
    turnover_ln: float            # ln(oran), bir kez binary64
    floor_lock_allday: int        # en yüksek == alt limit (bilgi)
    half_day: int
    halt_flag: int
    band_ratio_lower: Optional[Decimal]
    band_ratio_upper: Optional[Decimal]
    band_rule_ok: bool
    warnings: tuple[dict[str, Any], ...]

    def features(self) -> dict[str, float]:
        return {"b_floor": float(self.b_floor), "b_turnover": self.turnover_ln}


def _raw(fields: Mapping[str, Any], name: str) -> Optional[Decimal]:
    """Bülten alanı: boş, eksik ya da sayı olmayan metin -> None."""
    try:
        return parse_decimal(fields.get(name), name, required=False)
    except FeatureError:
        return None


def band_ratios(fields: Mapping[str, Any]) -> tuple[Optional[Decimal], Optional[Decimal], bool]:
    """(alt limit / referans, üst limit / referans, bant kuralı tutuyor mu). Referans ya da limit yoksa kural tutmuyor sayılır."""
    ref, lo, up = _raw(fields, "reference_price"), _raw(fields, "lower_limit"), _raw(fields, "upper_limit")
    if ref is None or ref <= 0 or lo is None or lo <= 0 or up is None or up <= 0:
        return None, None, False
    with localcontext(_LN):
        rl, ru = lo / ref, up / ref
    ok = BAND_LOWER[0] <= rl <= BAND_LOWER[1] and BAND_UPPER[0] <= ru <= BAND_UPPER[1]
    return rl, ru, ok


def evaluate_break_day(day: Mapping[str, Any], shares_offered: Any) -> BreakValues:
    """§3 tanımları ve ret/uyarı tablosu (tek tanım: fit, backtest ve tahmin aynı fonksiyonu çağırır). `day` =
    {"fields_raw": {open, high, low, close, volume, trade_count, reference_price, upper_limit, lower_limit,
    special_trade_volume?}, "half_day": 0/1, "halt_flag": 0/1}. Yükseltir: PredictError(B_NOT_TRADED), BreakRefusal."""
    f = day.get("fields_raw") or {}
    close, trades = _raw(f, "close"), _raw(f, "trade_count")
    if close is None or close <= 0 or trades is None or trades <= 0:
        raise PredictError(B_NOT_TRADED, "D_b işlem görmemiş (sözleşme sayısı ya da kapanış yok/≤ 0; SPEC_SCORING §2): "
                                         "kırılma günü işlem görmüş ilk tavan-dışı kapanıştır")
    lower = _raw(f, "lower_limit")
    if lower is None or lower <= 0:
        raise BreakRefusal(REFUSED_B_LIMIT_NA, "lower_limit", "D_b THM alt limiti yok ya da ≤ 0 (b_floor tanımsız)")
    volume = _raw(f, "volume")
    if volume is None or volume <= 0:
        raise BreakRefusal(REFUSED_B_VOLUME_INVALID, "volume", "TOPLAM ISLEM ADEDI boş/≤ 0 iken sözleşme sayısı > 0 (veri "
                                                              "tutarsızlığı; bülten satırı elle incelenir)")
    prices = {name: _raw(f, name) for name in ("open", "high", "low")}
    for name, value in prices.items():
        if value is None or value <= 0:
            raise BreakRefusal(REFUSED_B_FIELD_INVALID, name, f"D_b THB {name} alanı yok ya da ≤ 0 (veri tutarsızlığı)")
    try:
        shares = parse_decimal(shares_offered, "shares_offered")
    except FeatureError as exc:
        raise BreakRefusal(REFUSED_INPUT_SHARES_OFFERED, "shares_offered", str(exc)) from exc
    if shares <= 0:
        raise BreakRefusal(REFUSED_INPUT_SHARES_OFFERED, "shares_offered", f"arz edilen pay pozitif değil: {shares}")
    floor = int(close == lower)
    lock = int(prices["high"] == lower)
    warnings: list[dict[str, Any]] = []
    half, halt = int(day.get("half_day") or 0), int(day.get("halt_flag") or 0)
    if half:
        warnings.append(_warn(WARN_B_HALF_DAY, "D_b yarım gün: el değiştirme kısa seansta ölçüldü (H99'da 1 örnek)"))
    if halt:
        warnings.append(_warn(WARN_B_INTRADAY_HALT, "D_b'de gün içi geçici durdurma (H99'da örnek yok)"))
    special = _raw(f, "special_trade_volume")
    if special is not None and special > 0:
        warnings.append(_warn(WARN_B_SPECIAL_TRADES, "özel işlem bildirimi hacmi > 0; hacim düzeltilmedi (resmi toplam)",
                              special_trade_volume=str(special), volume=str(volume)))
    if lock:
        warnings.append(_warn(WARN_B_FLOOR_LOCK_ALLDAY, "en yüksek = alt limit: gün boyu tabanda (bilgi; özellik değil)"))
    rl, ru, band_ok = band_ratios(f)
    if not band_ok:
        warnings.append(_warn(WARN_BAND_RULE_MISMATCH, "alt limit / referans [0.9, 0.9020] ya da üst limit / referans "
                                                       "[1.098, 1.1] dışında: ±%10 bant varsayımı tutmuyor; yastık rozeti "
                                                       "gösterilmez (model tahmini yine üretilir)",
                              lower_ratio=None if rl is None else str(rl), upper_ratio=None if ru is None else str(ru)))
    with localcontext(_LN):
        ratio = volume / shares
        ln = ratio.ln()
    return BreakValues(b_floor=floor, turnover_ratio=ratio, turnover_ln=float(ln), floor_lock_allday=lock, half_day=half,
                       halt_flag=halt, band_ratio_lower=rl, band_ratio_upper=ru, band_rule_ok=band_ok, warnings=tuple(warnings))


def regime_tags(first_trading_date: Optional[str], band_rule_ok: bool = True) -> list[str]:
    """`regime_tags` (§6, §11): D_1 ≥ 2026-09-16 → FON_KRIZI_2026 (bitiş yok, C4); bant kuralı tutmuyorsa BAND_CHANGED."""
    tags = []
    r = REGIME_FON_KRIZI_2026
    if first_trading_date is not None and first_trading_date >= r["start_d1"] and (r["end_d1"] is None or first_trading_date <= r["end_d1"]):
        tags.append(r["tag"])
    if not band_rule_ok:
        tags.append(TAG_BAND_CHANGED)
    return tags


# ============================================================ §2.4 yastık kuralı (kod; parametre değil)

def structural_zero_d10(close_b: Any, b: int, ipo_price: Any) -> dict[str, Any]:
    """min10 = Lo^{(10 − b)}(kapanış_b) (alt limit zinciri, kesin Decimal; `predict_path.lower_limit`). min10 > P ise
    P(D10 ≤ arz) = 0 yapısal (`impossible`). k_b = ln(kapanış_b / P) / ln(1/0.9) (60 hane, bir kez binary64), r_b = 10 − b:
    "arz altı için kalan r_b seansta ≈ ⌈k_b⌉ taban gerekir" metninin sayıları. Bant kuralı tutmuyorsa rozet çağıran tarafından
    gizlenir (§1.3)."""
    if not 1 <= b <= B_MAX:
        raise ValueError(f"b = {b} 1..9 dışında")
    cb, P = Decimal(str(close_b)), Decimal(str(ipo_price))
    if cb <= 0 or P <= 0:
        raise ValueError("kapanış ve arz fiyatı pozitif olmalı")
    x = cb
    for _ in range(DAYS - b):
        x = pth.lower_limit(x)
    with localcontext(_LN):
        k = (cb / P).ln() / (Decimal(1) / Decimal("0.9")).ln()
    return {"rule": STRUCTURAL_ZERO_RULE, "min10": str(x), "P": str(P), "impossible": x > P, "k_b": float(k), "r_b": DAYS - b,
            "approx_impossible": float(k) >= DAYS - b}


def structural_zero_badge(close_b: Any, b: int, ipo_price: Any, band_rule_ok: bool) -> dict[str, Any]:
    """Kart gösterimi (§8-3): yastık kuralı + `shown` (BAND_RULE_MISMATCH'te rozet gizli, §1.3)."""
    return {**structural_zero_d10(close_b, b, ipo_price), "shown": bool(band_rule_ok)}


# §9.3 sınıf kuralı (saf formül; skorlama görevi git kanıtlarını hesaplar ve bunu çağırır). Ölçek `live_break`: LIVE ∪ MACHINE_SEQUENCED.
CLASS_LIVE, CLASS_MACHINE_SEQUENCED, CLASS_RETRO = "LIVE", "MACHINE_SEQUENCED", "RETRO"


def class_break(model_prospective: bool, record_live: bool, inputs_pit_ok: bool) -> str:
    """class_break(m, a) = LIVE (prospektif ∧ insan kaydı T_open'dan önce push kanıtlı ∧ girdiler PIT) | MACHINE_SEQUENCED (prospektif
    ∧ insan kaydı yok ∧ girdiler PIT) | RETRO (diğer). v0'da insan kaydı üreticisi yoktur."""
    if model_prospective and inputs_pit_ok:
        return CLASS_LIVE if record_live else CLASS_MACHINE_SEQUENCED
    return CLASS_RETRO


# ============================================================ §5.1 ürün karşılaştırıcısı

def product_thresholds(close_b: Any, ipo_price: Any) -> tuple[float, float]:
    """(eşik_F1, eşik_F2) = (Lo(kapanış_b)/P − 1, Lo(Lo(kapanış_b))/P − 1), 60 haneden bir kez binary64."""
    cb, P = Decimal(str(close_b)), Decimal(str(ipo_price))
    lo1 = pth.lower_limit(cb)
    return pth.ratio_minus_one(lo1, P), pth.ratio_minus_one(pth.lower_limit(lo1), P)


def product_atoms(cells: Mapping[tuple[str, int], Sequence[tuple[float, str]]], ipo_price: Any, L: int,
                  closes: Sequence[Any], h: int) -> tuple[list[tuple[float, float]], list[pth.PooledCell], bool]:
    """Durum-2 karışımının D_h atomları (`predict_path.conditional_after_break` ile aynı parça: t = L, ağırlık 1, ölçek
    kapanış(D_L)/P; L = 0'da ölçek yok). `closes` = kapanış(D_1..D_b)."""
    if not 0 <= L < DAYS or len(closes) < L + 1:
        raise ValueError(f"L = {L} için kapanış(D_1..D_{L + 1}) gerekir")
    P = Decimal(str(ipo_price))
    scale = None if L == 0 else pth.ratio(Decimal(str(closes[L - 1])), P)
    return pth.mixture_atoms(None, [(L, 1.0, scale)], cells, h)


def product_from_cells(cells: Mapping[tuple[str, int], Sequence[tuple[float, str]]], ipo_price: Any, L: int,
                       closes: Sequence[Any]) -> dict[str, Any]:
    """P_ürün(F1) ve (b ≤ 8 ise) P_ürün(F2). Dönen: {"F1", "F2" (None: tanımsız ya da hücre yetersiz), "status"
    (OK | POST_BREAK_INSUFFICIENT: tanımlı bir başlıkta havuz < N_MIN), "thresholds", "cells" (havuz kaynakları), "n_atoms"}."""
    b = L + 1
    if not 1 <= b <= B_MAX:
        raise ValueError(f"b = {b} 1..9 dışında")
    thr = dict(zip(HEADS, product_thresholds(closes[b - 1], ipo_price)))
    out: dict[str, Any] = {"F1": None, "F2": None, "status": PRODUCT_OK, "thresholds": thr, "cells": {}, "n_atoms": {}}
    for head, h in (("F1", b + 1), ("F2", b + 2)):
        if h > DAYS:
            continue
        atoms, used, ok = product_atoms(cells, ipo_price, L, closes, h)
        out["cells"][head] = [c.as_json() for c in used]
        if not ok:
            out["status"] = PRODUCT_INSUFFICIENT
            continue
        out["n_atoms"][head] = len(atoms)
        out[head] = sum(w for r, w in atoms if r <= thr[head] + PRODUCT_EPS)
    return out


def product_break_floor(path_params: Mapping[str, Any], path_output: Mapping[str, Any], L: int,
                        closes: Sequence[Any]) -> dict[str, Any]:
    """Canlı biçim: `path_params` = listeleme öncesi kayıttaki tavan yolu modeli (dondurulmuş hücreleriyle), `path_output` = o
    kaydın çıktısı (limit_path). Parametre ve gözlem denetimi `predict_path.conditional_after_break`'in kendisidir; atomlar aynı
    hücrelerden `product_atoms` ile (§5.1). Dönen `product_from_cells` + `conditional` (durum-2 özeti)."""
    cond = pth.conditional_after_break(path_params, path_output, L, closes)
    out = product_from_cells(pth.cells_of(path_params), path_output["limit_path"]["ipo_price"], L, closes)
    out["limit_path_mismatch"] = cond["limit_path_mismatch"]
    out["conditional"] = cond
    return out


# ============================================================ parametre denetimi ve tahmin

def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def check_params(params: Mapping[str, Any]) -> None:
    if not isinstance(params, Mapping):
        raise PredictError("PARAMS_INVALID", "params bir sözlük değil")
    if params.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        raise PredictError("SCHEMA_UNSUPPORTED", f"schema_version={params.get('schema_version')!r}")
    if (params.get("algorithm"), params.get("stage"), params.get("family")) != (ALGORITHM, STAGE, FAMILY):
        raise PredictError("PARAMS_INVALID", f"kırılma akşamı modeli değil: {params.get('algorithm')!r} / {params.get('stage')!r} / "
                                             f"{params.get('family')!r}")
    features = list(params.get("features", []))
    if features not in ([], list(FEATURES)):
        raise PredictError("PARAMS_INVALID", f"desteklenmeyen özellik listesi {features}")
    heads = params.get("horizons")
    if not isinstance(heads, Mapping) or sorted(heads) != sorted(HEADS):          # JSON anahtarları sıralı yazılır
        raise PredictError("PARAMS_INVALID", f"başlıklar {list(HEADS)} değil")
    preps = params.get("preprocessing") or {}
    for h in HEADS:
        head = (heads.get(h) or {}).get("p_floor")
        kind = head.get("kind") if isinstance(head, Mapping) else None
        if kind == "constant":
            if not _finite(head.get("value")) or not 0.0 < head["value"] < 1.0:
                raise PredictError("PARAMS_INVALID", f"{h}.p_floor: sabit değer (0, 1) içinde değil")
            continue
        if kind != "logit" or not features:
            raise PredictError("PARAMS_INVALID", f"{h}.p_floor: bilinmeyen kind {kind!r} ya da özelliksiz logit")
        prep = preps.get(h)
        if not isinstance(prep, Mapping):
            raise PredictError("PARAMS_INVALID", f"{h}: ön işleme bloğu yok")
        cols = list(prep.get("columns", []))
        if cols != [c for c in FEATURES if c in cols] or list(head.get("columns", [])) != cols or len(head.get("coef", [])) != len(cols):
            raise PredictError("PARAMS_INVALID", f"{h}: kolonlar ön işlemeyle uyuşmuyor")
        if list(prep.get("log_transform", [])) or sorted(prep.get("winsor", {})) != list(WINSOR_FEATURES):
            raise PredictError("PARAMS_INVALID", f"{h}: kırpma yalnız b_turnover'da, log yok olmalı")
        w = prep["winsor"]["b_turnover"]
        if not (_finite(w.get("p05")) and _finite(w.get("p95")) and w["p05"] <= w["p95"]):
            raise PredictError("PARAMS_INVALID", f"{h}: b_turnover kırpma sınırları yok")
        if not all(_finite(prep.get("mean", {}).get(c)) and _finite(prep.get("std", {}).get(c)) and prep["std"][c] > 0 for c in cols):
            raise PredictError("PARAMS_INVALID", f"{h}: aktif kolonun ortalama/std'si yok ya da std ≤ 0")
        if not (_finite(head.get("intercept")) and all(_finite(c) for c in head["coef"])):
            raise PredictError("PARAMS_INVALID", f"{h}: katsayılar sonlu değil")


def head_probability(head: Mapping[str, Any], prep: Optional[Mapping[str, Any]], values: Optional[Mapping[str, float]]
                     ) -> tuple[float, Optional[list[float]], bool, Optional[float]]:
    """(p_floor, z, b_turnover kırpıldı mı, kullanılan b_turnover). Sabit başlıkta z yok."""
    if head["kind"] == "constant":
        return float(head["value"]), None, False, None
    z = z_vector(prep, values)
    w = prep["winsor"]["b_turnover"]
    raw = values["b_turnover"]
    used = min(max(raw, w["p05"]), w["p95"])
    return _sigmoid(sum(c * v for c, v in zip(head["coef"], z)) + head["intercept"]), z, not (w["p05"] <= raw <= w["p95"]), used


def predict_break(params: Mapping[str, Any], day: Optional[Mapping[str, Any]], shares_offered: Any, *, b: Optional[int],
                  first_trading_date: Optional[str] = None) -> dict[str, Any]:
    """Dönen: {"model_id", "stage", "b", "refused": None | {code, field, reason}, "not_applicable": None | {code, reason},
    "warnings", "regime_tags", "F1": {"p_floor"} | None, "F2": {"p_floor"} | None, "f2_status": None | TARGET_UNDEFINED_F2,
    "features": None | {...}}. `b` = None: seri bozulmadı (L = 10). `@ZERO` (özelliksiz) kırılma günü alanlarını okumaz."""
    check_params(params)
    out: dict[str, Any] = {"model_id": params.get("model_id"), "stage": STAGE, "b": b, "refused": None, "not_applicable": None,
                           "warnings": [], "regime_tags": regime_tags(first_trading_date), "F1": None, "F2": None,
                           "f2_status": None, "features": None}
    if b is None:
        out["not_applicable"] = {"code": NOT_APPLICABLE_NO_BREAK, "reason": "seri D10'a kadar bozulmadı (L = 10): kırılma akşamı yok"}
        return out
    if b == DAYS:
        out["not_applicable"] = {"code": NOT_APPLICABLE_B10, "reason": "b = 10: D_{b+1} yok, hedef tanımsız"}
        return out
    if not 1 <= b <= B_MAX:
        raise PredictError("PARAMS_INVALID", f"b = {b} 1..10 dışında")
    heads = [h for h in HEADS if h == "F1" or b <= F2_B_MAX]
    if b > F2_B_MAX:
        out["f2_status"] = TARGET_UNDEFINED_F2
    features = list(params["features"])
    values = None
    if features:
        try:
            v = evaluate_break_day(day or {}, shares_offered)
        except BreakRefusal as exc:
            out["refused"] = {"code": exc.code, "field": exc.field, "reason": str(exc)}
            return out
        out["warnings"] += list(v.warnings)
        out["regime_tags"] = regime_tags(first_trading_date, v.band_rule_ok)
        values = v.features()
        for fid, rng in (params.get("feature_ranges") or {}).items():
            x = values.get(fid)
            if x is not None and not (rng["min"] <= x <= rng["max"]):
                out["warnings"].append(_warn(WARN_OUT_OF_TRAINING_RANGE, f"{fid} = {x!r} eğitim aralığı dışında "
                                                                         f"[{rng['min']!r}, {rng['max']!r}]",
                                             feature=fid, value=x, train_min=rng["min"], train_max=rng["max"]))
        out["features"] = {"b_floor": v.b_floor, "b_turnover_ratio": str(v.turnover_ratio), "b_turnover_ln": v.turnover_ln,
                           "floor_lock_allday": v.floor_lock_allday, "half_day": v.half_day, "halt_flag": v.halt_flag,
                           "band_ratio_lower": None if v.band_ratio_lower is None else str(v.band_ratio_lower),
                           "band_ratio_upper": None if v.band_ratio_upper is None else str(v.band_ratio_upper),
                           "band_rule_ok": v.band_rule_ok, "clipped": {}, "b_turnover_used": {}, "z": {}}
    clipped_any = False
    for h in heads:
        p, z, clipped, used = head_probability(params["horizons"][h]["p_floor"], (params.get("preprocessing") or {}).get(h), values)
        out[h] = {"p_floor": p}
        if out["features"] is not None and z is not None:
            cols = params["preprocessing"][h]["columns"]
            out["features"]["z"][h] = dict(zip(cols, z))
            out["features"]["clipped"][h] = clipped
            out["features"]["b_turnover_used"][h] = used
            clipped_any = clipped_any or clipped
    if clipped_any:
        out["warnings"].append(_warn(WARN_B_TURNOVER_CLIPPED, "b_turnover eğitim p05/p95 sınırına kırpıldı (başlık başına sınırlar)",
                                     feature="b_turnover", value=values["b_turnover"], used=out["features"]["b_turnover_used"]))
    return out

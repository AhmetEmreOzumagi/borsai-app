"""f1–f5: V1.5 girdilerinin TEK tanımı. Yalnız stdlib (decimal).

Kaynak davranış (legacy, değiştirilmeden taşındı):
- canlı yol: `pbb.calculated_features` (legacy/scripts/modeling/
  run_post_bookbuild_pre_listing_v1_5_prospective_freeze.py:349-358);
- eğitim yolu: H99 `feature_readiness.csv` değerleri. 99 arzın hepsinde
  aşağıdaki formüllerle Decimal olarak eşit (tests/test_features.py).

Tanımlar:
  f1 = arz büyüklüğü, TL. Kaynakta bildirilen `ipo_size_tl` verilmişse o değer,
       yoksa ipo_price_tl × shares_offered.
       H99'da kaynak değer 95 arzda fiyat×pay'a eşit; OBAMS, AKFIS, DSTKF, KLYPV'de
       tam TL'ye yuvarlanmış (fark ≤ 0.46 TL). V1.5 bu kaynak değerlerle eğitildi
       (provenance notu: "Preserve source-reported size"); port bunu korur.
  f2 = shares_offered / post_ipo_share_capital × 100, 10 ondalığa ROUND_HALF_UP.
  f3 = total_demand_multiple (toplam talep katı). Eksik olabilir; eksik ≠ 0.
  f4 = capital_increase_shares / shares_offered × 100, 10 ondalığa ROUND_HALF_UP.
  f5 = 1 yalnız f3 eksikse, değilse 0. Ön işlemede türetilir.

Legacy aritmetiği: pbb bölme ve çarpmayı Python'un varsayılan Decimal bağlamında
(28 anlamlı hane, ROUND_HALF_EVEN) yaptı, sonra 10 ondalığa ROUND_HALF_UP ile
yuvarladı. Burada aynı bağlam açıkça kurulur; ortam bağlamına bağlı değildir.
Kesin rasyonel yuvarlamadan farkı yalnız bir yuvarlama sınırına 1e-26 göreli
yakınlıktaki değerlerde doğabilir.

Ön işleme (winsor, medyan, log, z) burada değil, borsai/preprocess.py'dedir.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal, Inexact, InvalidOperation, localcontext
from typing import Any, Mapping, Optional

FEATURE_IDS: tuple[str, ...] = ("f1", "f2", "f3", "f4", "f5")
SUBSTANTIVE_FEATURE_IDS: tuple[str, ...] = ("f1", "f2", "f3", "f4")
FEATURE_VERSION = "BORSAI_FEATURES_V1_5_PORT_1"

# Python'un varsayılan Decimal bağlamı (pbb bu bağlamda hesapladı).
LEGACY_DECIMAL_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)
PCT_PLACES = 10
_PCT_QUANTUM = Decimal(1).scaleb(-PCT_PLACES)

FEATURE_DEFINITIONS: dict[str, str] = {
    "f1": "arz büyüklüğü TL: kaynakta bildirilen ipo_size_tl, yoksa ipo_price_tl × shares_offered; ön işlemede doğal log",
    "f2": "shares_offered / post_ipo_share_capital × 100; 10 ondalık ROUND_HALF_UP",
    "f3": "total_demand_multiple (toplam talep katı); eksik ≠ 0; ön işlemede fold içi p05/p95 winsor",
    "f4": "capital_increase_shares / shares_offered × 100; 10 ondalık ROUND_HALF_UP",
    "f5": "1 yalnız f3 eksikse, değilse 0",
}

RAW_INPUT_FIELDS: tuple[str, ...] = (
    "ipo_price_tl",
    "shares_offered",
    "post_ipo_share_capital",
    "capital_increase_shares",
    "total_demand_multiple",
)

# Etiketli hata kodları
INPUT_MISSING = "INPUT_MISSING"
INPUT_NOT_NUMERIC = "INPUT_NOT_NUMERIC"
INPUT_NOT_POSITIVE = "INPUT_NOT_POSITIVE"
INPUT_NEGATIVE = "INPUT_NEGATIVE"
DIVISION_BY_ZERO = "DIVISION_BY_ZERO"
INPUT_INCONSISTENT = "INPUT_INCONSISTENT"


class FeatureError(ValueError):
    """Girdi hatası: `code` makine tarafından okunur, `field` hangi alan."""

    def __init__(self, code: str, field: str, message: str) -> None:
        self.code = code
        self.field = field
        super().__init__(f"{code}: {field}: {message}")


@dataclass(frozen=True)
class RawFeatures:
    """Ön işleme öncesi f1–f4 (kesin Decimal). f5 f3'ten türer."""

    f1: Decimal
    f2: Decimal
    f3: Optional[Decimal]
    f4: Decimal

    @property
    def f5(self) -> int:
        return 1 if self.f3 is None else 0

    def as_dict(self) -> dict[str, Optional[Decimal]]:
        return {"f1": self.f1, "f2": self.f2, "f3": self.f3, "f4": self.f4}


def parse_decimal(value: Any, field: str, *, required: bool = True) -> Optional[Decimal]:
    """Metin ya da sayıdan kesin Decimal. float kabul edilir ama repr'i üzerinden
    (örn. 2.84 -> Decimal('2.84')). Boş, None ve DATA_NOT_FOUND eksik sayılır."""
    if value is None or (isinstance(value, str) and value.strip() in ("", "DATA_NOT_FOUND")):
        if required:
            raise FeatureError(INPUT_MISSING, field, "değer yok")
        return None
    if isinstance(value, bool):
        raise FeatureError(INPUT_NOT_NUMERIC, field, f"sayı değil: {value!r}")
    try:
        parsed = Decimal(repr(value)) if isinstance(value, float) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise FeatureError(INPUT_NOT_NUMERIC, field, f"sayı değil: {value!r}") from exc
    if not parsed.is_finite():
        raise FeatureError(INPUT_NOT_NUMERIC, field, f"sonlu değil: {value!r}")
    return parsed


def _require_positive(value: Decimal, field: str, *, denominator: bool = False) -> Decimal:
    if value == 0 and denominator:
        raise FeatureError(DIVISION_BY_ZERO, field, "payda sıfır")
    if value <= 0:
        raise FeatureError(INPUT_NOT_POSITIVE, field, f"pozitif olmalı: {value}")
    return value


def _pct(numerator: Decimal, denominator: Decimal) -> Decimal:
    """pbb: Decimal(decimal_text(num / den * 100)) — 28 haneli bağlamda bölme ve
    çarpma, 10 ondalığa ROUND_HALF_UP, sondaki sıfırlar atılır ("28", "71.4285714286").
    Metin biçimi de legacy kanıt paketleriyle aynı olsun diye korunur."""
    with localcontext(LEGACY_DECIMAL_CONTEXT):
        raw = numerator / denominator * Decimal(100)
        rendered = format(raw.quantize(_PCT_QUANTUM, rounding=ROUND_HALF_UP), "f").rstrip("0").rstrip(".")
    return Decimal(rendered or "0")


def compute_features(
    *,
    ipo_price_tl: Any,
    shares_offered: Any,
    post_ipo_share_capital: Any,
    capital_increase_shares: Any,
    total_demand_multiple: Any = None,
    ipo_size_tl: Any = None,
) -> RawFeatures:
    """Ham girdilerden f1–f4. Hatalı girdi FeatureError (etiketli) verir;
    çıplak ZeroDivisionError / InvalidOperation dışarı sızmaz."""
    price = _require_positive(parse_decimal(ipo_price_tl, "ipo_price_tl"), "ipo_price_tl")
    shares = _require_positive(parse_decimal(shares_offered, "shares_offered"), "shares_offered", denominator=True)
    post = _require_positive(
        parse_decimal(post_ipo_share_capital, "post_ipo_share_capital"), "post_ipo_share_capital", denominator=True
    )
    cap_inc = parse_decimal(capital_increase_shares, "capital_increase_shares")
    if cap_inc < 0:
        raise FeatureError(INPUT_NEGATIVE, "capital_increase_shares", f"negatif olamaz: {cap_inc}")
    if cap_inc > shares:
        raise FeatureError(
            INPUT_INCONSISTENT, "capital_increase_shares", f"satılan paydan büyük: {cap_inc} > {shares}"
        )
    if shares > post:
        raise FeatureError(
            INPUT_INCONSISTENT, "shares_offered", f"arz sonrası sermayeden büyük: {shares} > {post}"
        )
    f3 = parse_decimal(total_demand_multiple, "total_demand_multiple", required=False)
    if f3 is not None and f3 <= 0:
        raise FeatureError(INPUT_NOT_POSITIVE, "total_demand_multiple", f"pozitif olmalı: {f3}")

    size = parse_decimal(ipo_size_tl, "ipo_size_tl", required=False)
    if size is not None:
        f1 = _require_positive(size, "ipo_size_tl")
    else:
        with localcontext(LEGACY_DECIMAL_CONTEXT):
            f1 = shares * price
    return RawFeatures(f1=f1, f2=_pct(shares, post), f3=f3, f4=_pct(cap_inc, shares))


# ---------------------------------------------------------------------------
# PB (talep toplama öncesi) özellikleri: SPEC_PB_V0 §2. Tek tanım.
#
# Kaynak: legacy/scripts/modeling/prebookbuild_v1_r6/pb_core4.py:98-160 (aynen):
#   pb1 = ln(ipo_price_try × planned_base_offer_shares)       (Decimal, 60 hane) -> binary64
#   pb2 = planned_base_offer_shares / planned_post_ipo_capital × 100   (kesin rasyonel) -> binary64
#   pb3 = planned_capital_increase_shares / planned_base_offer_shares × 100
#   pb4 = planned_additional_sale_ceiling / planned_base_offer_shares × 100  (özellik değil; uyarı)
# Kesin rasyonelin binary64'e çevrimi legacy'deki `float(Fraction)` ile aynıdır:
# Fraction.__float__ pay/payda tamsayı bölmesidir ve Python'da tamsayı bölmesi
# doğru yuvarlanır. Burada pay ve payda Decimal.as_integer_ratio()'dan gelir
# (fractions modülü predict yolunun import kümesine girmesin diye).
# Legacy'deki `additional_sale_semantics` metin denetimi TAŞINMAZ (SPEC_PB_V0 §2).
# ---------------------------------------------------------------------------

PB_FEATURE_IDS: tuple[str, ...] = ("pb1", "pb2", "pb3")
PB_FEATURE_VERSION = "BORSAI_PB_FEATURES_PB_CORE4_PORT_1"
PB_REQUIRED_FIELDS: tuple[str, ...] = (
    "ipo_price_try",
    "planned_pre_ipo_capital",
    "planned_post_ipo_capital",
    "planned_capital_increase_shares",
    "planned_existing_share_sale",
    "planned_base_offer_shares",
    "planned_additional_sale_ceiling",
    "planned_max_offer_shares",
)
PB_FEATURE_DEFINITIONS: dict[str, str] = {
    "pb1": "ln(ipo_price_try × planned_base_offer_shares); Decimal 60 hane, sonra binary64",
    "pb2": "planned_base_offer_shares / planned_post_ipo_capital × 100; kesin rasyonel -> binary64",
    "pb3": "planned_capital_increase_shares / planned_base_offer_shares × 100; kesin rasyonel -> binary64",
    "pb4": "planned_additional_sale_ceiling / planned_base_offer_shares × 100; özellik değil, yalnız doğrulama ve uyarı",
}

PB_FIELD_MISSING = "PB_FIELD_MISSING"
PB_IDENTITY = "PB_IDENTITY"
PB_PRICE_RANGE = "PB_PRICE_RANGE"

_PB_CONTEXT = Context(prec=60, rounding=ROUND_HALF_EVEN)
_EXACT_CONTEXT = Context(prec=200, rounding=ROUND_HALF_EVEN)
_RANGE_SEPARATORS = ("-", "–", "—")


class PBRefusal(ValueError):
    """PB girdisi reddi: `code` (PB_FIELD_MISSING / PB_IDENTITY / PB_PRICE_RANGE), `field`."""

    def __init__(self, code: str, field: str, message: str) -> None:
        self.code = code
        self.field = field
        super().__init__(f"{code}:{field}: {message}")


@dataclass(frozen=True)
class PBFeatures:
    pb1: float
    pb2: float
    pb3: float
    pb4: float

    def as_dict(self) -> dict[str, float]:
        return {"pb1": self.pb1, "pb2": self.pb2, "pb3": self.pb3}


def parse_pb_decimal(value: Any, field: str) -> Decimal:
    if value is None or isinstance(value, bool) or (isinstance(value, str) and value.strip() in ("", "DATA_NOT_FOUND")):
        raise PBRefusal(PB_FIELD_MISSING, field, "değer yok")
    text = repr(value) if isinstance(value, float) else str(value).strip()
    if field == "ipo_price_try":
        for sep in _RANGE_SEPARATORS:
            parts = text[1:].split(sep, 1)
            if len(parts) == 2:
                lo, hi = text[0] + parts[0], parts[1]
                try:
                    Decimal(lo.strip()), Decimal(hi.strip())
                except (InvalidOperation, ValueError):
                    continue
                raise PBRefusal(PB_PRICE_RANGE, field, f"fiyat tek değer değil (aralık): {value!r}")
    try:
        parsed = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise PBRefusal(PB_FIELD_MISSING, field, f"ayrıştırılamıyor: {value!r}") from exc
    if not parsed.is_finite():
        raise PBRefusal(PB_FIELD_MISSING, field, f"sonlu değil: {value!r}")
    return parsed


def _pct_ratio(numerator: Decimal, denominator: Decimal) -> tuple[int, int]:
    """numerator / denominator × 100 kesin rasyonel (pay, payda > 0)."""
    n1, d1 = numerator.as_integer_ratio()
    n2, d2 = denominator.as_integer_ratio()
    num, den = n1 * d2 * 100, d1 * n2
    return (num, den) if den > 0 else (-num, -den)


def compute_pb_features(row: Mapping[str, Any]) -> PBFeatures:
    """8 planlanan yapı alanından pb1–pb4. Yalnız PB_REQUIRED_FIELDS anahtarları okunur
    (f3, nihai pay sayısı, ek satış, sonuç sütunları okunmaz: SPEC_PB_V0 §11-4).
    İhlal PBRefusal (etiketli) verir; çıplak exception sızmaz."""
    v = {f: parse_pb_decimal(row.get(f), f) for f in PB_REQUIRED_FIELDS}
    price, base, post = v["ipo_price_try"], v["planned_base_offer_shares"], v["planned_post_ipo_capital"]
    cap_inc, addl = v["planned_capital_increase_shares"], v["planned_additional_sale_ceiling"]
    with localcontext(_EXACT_CONTEXT) as ctx:
        ctx.traps[Inexact] = True
        try:
            id_a = post == v["planned_pre_ipo_capital"] + cap_inc
            id_b = base == cap_inc + v["planned_existing_share_sale"]
            id_c = v["planned_max_offer_shares"] == base + addl
            value = price * base
        except Inexact as exc:
            raise PBRefusal(PB_FIELD_MISSING, "precision", "kesin hesaplanamıyor") from exc
    for ok, name in ((id_a, "ID-A"), (id_b, "ID-B"), (id_c, "ID-C"), (base > 0, "BASE_POSITIVE"),
                     (post > 0, "POST_POSITIVE"), (value > 0, "VALUE_POSITIVE")):
        if not ok:
            raise PBRefusal(PB_IDENTITY, name, "planlanan yapı özdeşliği ya da aralığı tutmuyor")
    ratios = {"pb2": _pct_ratio(base, post), "pb3": _pct_ratio(cap_inc, base), "pb4": _pct_ratio(addl, base)}
    for name in ("pb2", "pb3"):
        num, den = ratios[name]
        if not (0 < num <= 100 * den):
            raise PBRefusal(PB_IDENTITY, f"{name.upper()}_RANGE", f"{name} (0, 100] dışında")
    if ratios["pb4"][0] < 0:
        raise PBRefusal(PB_IDENTITY, "PB4_RANGE", "pb4 < 0")
    with localcontext(_PB_CONTEXT):
        pb1 = float(value.ln())
    return PBFeatures(pb1=pb1, **{k: n / d for k, (n, d) in ratios.items()})

"""Fold içi ön işleme: legacy V1.3 11 adımlı ön işlemenin portu. Yalnız stdlib.

Kaynak: legacy/scripts/modeling/preprocessing.py (`preprocess_fold`). Aritmetik
birebir taşındı; aynı makinede legacy ile bit düzeyinde aynı sonucu verir
(tests/test_port_vs_legacy.py). Tek davranış farkı f3 filtre modunun eşitlik
kuralıdır (aşağıda).

Adımlar (yalnız eğitim fold'undan öğrenilir):
  1. f3 karşılaştırılabilirlik filtresi: eğitimdeki f3 dolu satırların
     `total_demand_filter_status` modu bulunur; durumu ve mod'u açıkça zıt
     (FILTERED/UNFILTERED) olan satırın f3'ü boşaltılır (AUDIT §1.2-j).
  2-3. eksiklik; eksik oranı %40'tan büyükse özellik fold'dan düşer.
  4. f3 için Type-7 p05/p95 winsor sınırları (kesin Fraction).
  5. winsorlu değerlerin medyanıyla doldurma (kesin Fraction).
  6. f5 = 1[f3 eksik], yalnız f3 düşmediyse.
  7. f1'e doğal log (Decimal, 60 hane).
  8. sıfır varyans (kesin; f1 log öncesi değerlerle). f3 düşerse f5 de düşer.
  9. z-skor, nüfus varyansı (ddof = 0). f1: ortalama/varyans/std 60 haneli
     Decimal'de; f2/f3/f4/f5: ortalama/varyans kesin Fraction, std ve z 60 haneli
     Decimal. binary64'e dönüşüm z'den sonra bir kez yapılır.

Tarif (`Recipe`): aynı adımlar farklı modellerde farklı özellik kümeleriyle
koşar. `V1_5_RECIPE` varsayılandır ve yukarıdaki davranışın birebir aynısıdır
(altın ledger'lar ve legacy karşılaştırması bunu sınar). Diğer tarifler:
- MARKET20 (SPEC_MARKET20_V0 §2): f1–f5 aynen + f6 f5'ten sonra; f6'ya log,
  winsor, imputasyon, eksiklik göstergesi yok; yalnız sıfır varyans ve z-skor.
- CEILING (SPEC_CEILING_V0 §4): f1, f2, f3; imputasyon yok, f5 yok, f4 yok.
  Eksik değer hatadır (tahmin tarafı eksik f3'ü önceden reddeder).
- PB (SPEC_PB_V0 §2, §9): pb1–pb3 ya da pb1–pb2; yalnız sıfır varyans ve z-skor.
- CEILING_V1_CLIP / CEILING_V1_REAL (SPEC_HAZARD_V1 §3.1): CEILING gibi; üç sütun da (f1 ya da f1r, f2, f3) eğitim
  [p05, p95]'ine ham değerde kırpılır (`Recipe.winsor`), log (`Recipe.log`) f1 ya da f1r'ye kırpmadan sonra.
  Varsayılan `winsor = ("f3",)`, `log = ("f1",)`: eski tariflerin davranışı bayt düzeyinde aynıdır.
- FALL_V0 / FALL_V0_ADDSALE (SPEC_C_V0 §3.2): f1r, f3, add_sale; f1r ve f3 kırpılır ve ln'lenir (f3'ün ln'i f1'inkiyle aynı
  yoldan: 60 hane ln, 28 haneli ortam çıkarması), add_sale yalnız z-skor; addsale varyantında yalnız add_sale.

İki legacy ayrıntısı bilerek korunur:
- f1'in z payı `log − ortalama` legacy'de Python'un ortam Decimal bağlamında
  (varsayılan 28 hane) hesaplanıyordu; burada aynı 28 haneli bağlam açıkça kurulur.
- Test satırının f3 filtresi, filtre SONRASI eğitim satırlarının moduna bakar.

f3 filtre modu, eşitlik (bu port ile gelen tek fark):
  Legacy `max(set(statuses), key=statuses.count)` eşitlikte Python'un küme
  sırasına, yani str hash tohumuna (PYTHONHASHSEED) bağlıydı. Burada mod
  deterministiktir: en yüksek sayı; eşitlikte alfabetik olarak en küçük durum
  metni. Eşitlik olmayan her durumda legacy ile aynıdır. H99'da tam "FILTERED"
  literal'i hiç geçmediği için filtre hiçbir satırı boşaltmaz; bu, backtest
  ledger'ındaki `f3_filter_nulled_n` sütunuyla her fold için sınanır.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Context, Decimal, DivisionByZero, InvalidOperation, Overflow, localcontext
from fractions import Fraction
from typing import Any, Mapping, Optional

MODEL_NUMERIC_PRECISION = 60
LEGACY_AMBIENT_PRECISION = 28
PREPROCESSING_ID = "V1_3_FOLD_LOCAL_11_STEP_PREPROCESSING+DETERMINISTIC_F3_MODE"

SUBSTANTIVE_FEATURES: tuple[str, ...] = ("f1", "f2", "f3", "f4")
INDICATOR_FEATURE = "f5"
MISSINGNESS_FOLD_DROP_THRESHOLD = Fraction(40, 100)  # kesin "büyüktür"
WINSORIZE_FEATURES: tuple[str, ...] = ("f3",)
LOG_TRANSFORM_FEATURES: tuple[str, ...] = ("f1",)
WINSOR_P05 = Fraction(1, 20)
WINSOR_P95 = Fraction(19, 20)
EXPLICIT_FILTER_STATUSES = frozenset({"FILTERED", "UNFILTERED"})


@dataclass(frozen=True)
class Recipe:
    """Hangi özelliklerin hangi adımlardan geçtiği. `substantive` sütun sırasıdır;
    `extra` göstergeden (f5) sonra gelen, yalnız z-skorlanan özelliklerdir.
    `winsor`: eğitim kümesinin Type-7 [p05, p95]'ine ham değerde kırpılan özellikler (varsayılan ("f3",): V1.5/v0/PB
    davranışı aynen); `log`: winsor'dan sonra doğal log alınan özellikler (varsayılan ("f1",)). Faz 7 (SPEC_HAZARD_V1 §3.1):
    `CEILING_V1_CLIP`, `CEILING_V1_REAL`."""

    recipe_id: str
    substantive: tuple[str, ...]
    extra: tuple[str, ...] = ()
    indicator: bool = True
    impute: bool = True
    missingness_drop: bool = True
    winsor: tuple[str, ...] = WINSORIZE_FEATURES
    log: tuple[str, ...] = LOG_TRANSFORM_FEATURES

    @property
    def features(self) -> tuple[str, ...]:
        return self.substantive + self.extra


V1_5_RECIPE = Recipe(PREPROCESSING_ID, SUBSTANTIVE_FEATURES)
MARKET20_RECIPE = Recipe(PREPROCESSING_ID + "+F6_PLAIN_Z_NO_IMPUTATION", SUBSTANTIVE_FEATURES, extra=("f6",))
CEILING_RECIPE = Recipe(
    "V1_3_STEPS_F1_F2_F3_IPO_LEVEL_NO_IMPUTATION_NO_F5", ("f1", "f2", "f3"),
    indicator=False, impute=False, missingness_drop=False,
)
PB_RECIPE = Recipe("PB_PLAIN_Z_POPULATION_STD_NO_IMPUTATION", ("pb1", "pb2", "pb3"),
                   indicator=False, impute=False, missingness_drop=False)
PB_CEILING_RECIPE = Recipe("PB_PLAIN_Z_POPULATION_STD_NO_IMPUTATION", ("pb1", "pb2"),
                           indicator=False, impute=False, missingness_drop=False)
# Faz 7 (SPEC_HAZARD_V1 §3.1, §3.2): üç sütun da eğitim [p05, p95]'ine kırpılır (f1/f1r ham TL'de, log'dan önce); f1r = reel büyüklük.
CEILING_V1_CLIP_RECIPE = Recipe(
    "V1_STEPS_F1_F2_F3_IPO_LEVEL_WINSOR_F1_F2_F3_P05_P95_NO_IMPUTATION_NO_F5", ("f1", "f2", "f3"),
    indicator=False, impute=False, missingness_drop=False, winsor=("f1", "f2", "f3"), log=("f1",),
)
CEILING_V1_REAL_RECIPE = Recipe(
    "V1_STEPS_F1R_F2_F3_IPO_LEVEL_WINSOR_F1R_F2_F3_P05_P95_NO_IMPUTATION_NO_F5", ("f1r", "f2", "f3"),
    indicator=False, impute=False, missingness_drop=False, winsor=("f1r", "f2", "f3"), log=("f1r",),
)
# Faz 7C (SPEC_C_V0 §3.2): f1r ve f3 eğitim [p05, p95]'ine ham değerde kırpılır, sonra ln (ikisi de); ek satış bayrağı yalnız z-skor.
# İmputasyon, f5 ve eksiklik düşürmesi yok (eksik değer hatadır; eğitim kümeleri f3 ve ek satış dolu satırlardır).
FALL_V0_RECIPE = Recipe(
    "FALL_V0_F1R_F3_ADD_SALE_WINSOR_LOG_F1R_F3_P05_P95_NO_IMPUTATION_NO_F5", ("f1r", "f3", "add_sale"),
    indicator=False, impute=False, missingness_drop=False, winsor=("f1r", "f3"), log=("f1r", "f3"),
)
FALL_V0_ADDSALE_RECIPE = Recipe(
    "FALL_V0_ADD_SALE_PLAIN_Z_NO_IMPUTATION", ("add_sale",),
    indicator=False, impute=False, missingness_drop=False, winsor=(), log=(),
)
RECIPES: dict[str, Recipe] = {
    "V1_5": V1_5_RECIPE, "MARKET20": MARKET20_RECIPE, "CEILING": CEILING_RECIPE,
    "PB": PB_RECIPE, "PB_CEILING": PB_CEILING_RECIPE,
    "CEILING_V1_CLIP": CEILING_V1_CLIP_RECIPE, "CEILING_V1_REAL": CEILING_V1_REAL_RECIPE,
    "FALL_V0": FALL_V0_RECIPE, "FALL_V0_ADDSALE": FALL_V0_ADDSALE_RECIPE,
}

STATUS_MISSINGNESS_FOLD_DROP = "MISSINGNESS_FOLD_DROP"
STATUS_ZERO_VARIANCE_FOLD_DROP = "ZERO_VARIANCE_FOLD_DROP"
STATUS_F3_COUPLED_DROP = "F3_COUPLED_DROP"

_REPRESENTATION_FAILURES = (OverflowError, Overflow, InvalidOperation, DivisionByZero)


class NonPositiveLogInputError(ValueError):
    """f1 ≤ 0: log alınamaz; kırpılmaz, hata verir."""


class NumericRepresentationIntegrityError(RuntimeError):
    """Sayısal temsil sınırı ihlali (legacy I1–I4); tolerans ya da onarım yok."""


class MissingValueError(ValueError):
    """İmputasyonsuz tarifte eksik değer (tahmin tarafı bu girdiyi önceden reddeder)."""


def _model_ctx(precision: int = MODEL_NUMERIC_PRECISION) -> Context:
    return Context(prec=precision, rounding=ROUND_HALF_EVEN)


_AMBIENT_CTX = Context(prec=LEGACY_AMBIENT_PRECISION, rounding=ROUND_HALF_EVEN)


def _fail(exc: Exception, feature: str, stage: str, scope: str) -> NumericRepresentationIntegrityError:
    return NumericRepresentationIntegrityError(
        f"NUMERIC_REPRESENTATION_INTEGRITY_ERROR: feature={feature} stage={stage} scope={scope} "
        f"cause={type(exc).__name__}: {exc}"
    )


def _frac_to_dec(value: Fraction, ctx: Context, feature: str, stage: str, scope: str) -> Decimal:
    try:
        with localcontext(ctx):
            return Decimal(value.numerator) / Decimal(value.denominator)
    except _REPRESENTATION_FAILURES as exc:
        raise _fail(exc, feature, stage, scope) from exc


def _ln(value: Decimal, ctx: Context, feature: str, scope: str) -> Decimal:
    try:
        with localcontext(ctx):
            return value.ln()
    except _REPRESENTATION_FAILURES as exc:
        raise _fail(exc, feature, "LOG", scope) from exc


def _sqrt(value: Decimal, ctx: Context, feature: str, scope: str) -> Decimal:
    try:
        with localcontext(ctx):
            return value.sqrt()
    except _REPRESENTATION_FAILURES as exc:
        raise _fail(exc, feature, "SQRT", scope) from exc


def _sum(values, ctx: Context, feature: str, stage: str, scope: str) -> Decimal:
    try:
        with localcontext(ctx):
            return sum(values, Decimal(0))
    except _REPRESENTATION_FAILURES as exc:
        raise _fail(exc, feature, stage, scope) from exc


def _div(num: Decimal, den: Decimal, ctx: Context, feature: str, stage: str, scope: str) -> Decimal:
    try:
        with localcontext(ctx):
            return num / den
    except _REPRESENTATION_FAILURES as exc:
        raise _fail(exc, feature, stage, scope) from exc


def _ambient_sub(a: Decimal, b: Decimal) -> Decimal:
    """Legacy'de ortam bağlamında yapılan çıkarma (varsayılan 28 hane)."""
    with localcontext(_AMBIENT_CTX):
        return a - b


def _to_float(value: Any, feature: str, stage: str, scope: str) -> float:
    try:
        result = float(value)
    except _REPRESENTATION_FAILURES as exc:
        raise _fail(exc, feature, stage, scope) from exc
    if not math.isfinite(result):
        raise NumericRepresentationIntegrityError(
            f"NUMERIC_REPRESENTATION_INTEGRITY_ERROR: feature={feature} stage={stage} scope={scope} "
            f"cause=NON_FINITE_CONVERSION: float({value!r}) = {result!r}"
        )
    return result


def _finite_dec(value: Decimal, label: str) -> Decimal:
    if not value.is_finite():
        raise NumericRepresentationIntegrityError(f"I1_FINITE violated: {label}={value!r}")
    return value


def quantile_type7(sorted_values: list[Fraction], p: Fraction) -> Fraction:
    """R type 7 / numpy 'linear': h = (n−1)p + 1 (1 tabanlı), kesin Fraction."""
    n = len(sorted_values)
    if n == 0:
        raise ValueError("quantile_type7: boş girdi")
    if n == 1:
        return sorted_values[0]
    h = Fraction(n - 1) * p + 1
    lo = h.numerator // h.denominator
    frac = h - lo
    if lo == n:
        return sorted_values[lo - 1]
    return sorted_values[lo - 1] + frac * (sorted_values[lo] - sorted_values[lo - 1])


def median_exact(values: list[Fraction]) -> Fraction:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    return ordered[mid] if n % 2 == 1 else (ordered[mid - 1] + ordered[mid]) / 2


def filter_mode(statuses: list[Optional[str]]) -> tuple[Optional[str], bool]:
    """Deterministik mod: (mod, eşitlik_var_mı). En yüksek sayı; eşitlikte
    alfabetik en küçük durum metni. Boşsa (None, False)."""
    usable = [s for s in statuses if s is not None]
    if not usable:
        return None, False
    counts = Counter(usable)
    best = max(counts.values())
    tied = sorted(s for s, c in counts.items() if c == best)
    return tied[0], len(tied) > 1


def opposite_explicit_status(a: Optional[str], b: Optional[str]) -> bool:
    return a in EXPLICIT_FILTER_STATUSES and b in EXPLICIT_FILTER_STATUSES and a != b


@dataclass
class FittedPreprocessing:
    """Eğitim fold'undan öğrenilen ön işleme. `train_matrix` eğitim satırlarının
    z değerleri; `transform` aynı parametreleri yeni bir satıra uygular."""

    n_train: int
    train_tickers: tuple[str, ...]
    active_after_missingness: tuple[str, ...]
    columns: tuple[str, ...] = ()
    dropped: dict[str, str] = field(default_factory=dict)
    create_f5: bool = False
    insufficient_feature_variation: bool = False
    f3_filter_mode: Optional[str] = None
    f3_filter_mode_tie: bool = False
    f3_filter_mode_after: Optional[str] = None
    f3_filter_mode_after_tie: bool = False
    f3_filter_nulled: tuple[str, ...] = ()
    winsor_exact: dict[str, tuple[Fraction, Fraction]] = field(default_factory=dict)
    median_exact: dict[str, Fraction] = field(default_factory=dict)
    mean_exact: dict[str, Fraction] = field(default_factory=dict)
    mean_dec: dict[str, Decimal] = field(default_factory=dict)
    std_dec: dict[str, Decimal] = field(default_factory=dict)
    train_matrix: dict[str, dict[str, float]] = field(default_factory=dict)
    precision: int = MODEL_NUMERIC_PRECISION
    recipe_id: str = PREPROCESSING_ID
    log_features: tuple[str, ...] = LOG_TRANSFORM_FEATURES

    def transform(self, raw: Mapping[str, Optional[Decimal]], filter_status: Optional[str]) -> dict[str, Any]:
        """Tek satır (legacy'deki test satırı yolu). Dönen: {"z": {kolon: float},
        "f3_imputed": bool, "f3_nulled_by_filter": bool, "f3_winsorized": bool,
        "winsorized": {kırpılan-özellik: bool}} (son anahtar genel kırpma bayrağı; Faz 7)."""
        if self.insufficient_feature_variation:
            raise ValueError("insufficient_feature_variation: dönüştürülecek kolon yok")
        ctx = _model_ctx(self.precision)
        working = dict(raw)
        nulled = False
        test_f3 = working.get("f3")
        if (
            test_f3 is not None
            and "f3" in self.active_after_missingness
            and opposite_explicit_status(filter_status, self.f3_filter_mode_after)
        ):
            working["f3"] = None
            nulled = True

        structural: dict[str, Fraction] = {}
        missing_f3 = False
        winsorized: dict[str, bool] = {}
        for fid in self.active_after_missingness:
            v = working.get(fid)
            v_frac = Fraction(v) if v is not None else None
            if v_frac is not None and fid in self.winsor_exact:
                lo, hi = self.winsor_exact[fid]
                clamped = min(max(v_frac, lo), hi)
                winsorized[fid] = clamped != v_frac
                v_frac = clamped
            if v_frac is None:
                v_frac = self.median_exact.get(fid)
                if fid == "f3":
                    missing_f3 = True
                if v_frac is None:
                    raise ValueError(f"test satırında {fid} eksik ve eğitim medyanı yok")
            structural[fid] = v_frac
        if self.create_f5:
            structural[INDICATOR_FEATURE] = Fraction(1) if missing_f3 else Fraction(0)

        for fid in self.log_features:
            if fid in structural and structural[fid] <= 0:
                raise NonPositiveLogInputError(f"test.{fid}={structural[fid]} pozitif değil; log alınamaz")

        log_values: dict[str, Decimal] = {}
        for col in self.columns:
            if col in self.log_features:
                v_dec = _frac_to_dec(structural[col], ctx, col, "FRACTION_TO_DECIMAL", "TEST")
                log_values[col] = _finite_dec(_ln(v_dec, ctx, col, "TEST"), f"test.{col}.log_input")

        z: dict[str, float] = {}
        for col in self.columns:
            if col in self.log_features:
                z_dec = _finite_dec(
                    _div(_ambient_sub(log_values[col], self.mean_dec[col]), self.std_dec[col], ctx, col, "Z_DIVIDE", "TEST"),
                    f"test.{col}.z",
                )
            else:
                diff = _frac_to_dec(structural[col] - self.mean_exact[col], ctx, col, "Z_NUMERATOR", "TEST")
                z_dec = _finite_dec(_div(diff, self.std_dec[col], ctx, col, "Z_DIVIDE", "TEST"), f"test.{col}.z")
            z[col] = _to_float(z_dec, col, "Z_TO_BINARY64", "TEST")
        return {"z": z, "f3_imputed": missing_f3, "f3_nulled_by_filter": nulled,
                "f3_winsorized": winsorized.get("f3", False), "winsorized": winsorized}

    def matrix_rows(self, order: Optional[list[str]] = None) -> list[list[float]]:
        order = list(self.train_tickers) if order is None else order
        return [[self.train_matrix[t][c] for c in self.columns] for t in order]

    def params(self) -> dict[str, Any]:
        """JSON'a yazılacak parametreler; hepsi binary64 (en kısa gidiş-dönüş).
        μ ve σ z-skorun kullandığı değerlerdir: f1 için log uzayında."""
        cols = list(self.columns)
        mean: dict[str, float] = {}
        for col in cols:
            if col in self.log_features:
                mean[col] = _to_float(self.mean_dec[col], col, "MEAN", "REPORTING")
            else:
                mean[col] = _to_float(self.mean_exact[col], col, "MEAN", "REPORTING")
        return {
            "preprocessing_id": self.recipe_id,
            "columns": cols,
            "log_transform": [c for c in self.log_features if c in cols],
            "winsor": {
                f: {"p05": _to_float(lo, f, "WINSOR_LO", "REPORTING"), "p95": _to_float(hi, f, "WINSOR_HI", "REPORTING")}
                for f, (lo, hi) in self.winsor_exact.items()
            },
            "medians": {f: _to_float(v, f, "MEDIAN", "REPORTING") for f, v in self.median_exact.items()},
            "mean": mean,
            "std": {col: _to_float(self.std_dec[col], col, "STD", "REPORTING") for col in cols},
            "dropped": dict(self.dropped),
            "f5_created": self.create_f5,
            "f3_filter_mode": self.f3_filter_mode_after,
            "f3_filter_mode_tie": self.f3_filter_mode_after_tie,
            "f3_filter_nulled_tickers": list(self.f3_filter_nulled),
            "n_train": self.n_train,
        }


def fit_preprocessing(
    training_raw: Mapping[str, Mapping[str, Optional[Decimal]]],
    filter_status: Mapping[str, Optional[str]],
    *,
    precision: int = MODEL_NUMERIC_PRECISION,
    recipe: Recipe = V1_5_RECIPE,
) -> FittedPreprocessing:
    """training_raw: ticker -> {özellik: Decimal|Fraction|float|None}; sözlük sırası satır
    sırasıdır. filter_status: ticker -> total_demand_filter_status (eğitim satırları)."""
    tickers = list(training_raw)
    n = len(tickers)
    if n == 0:
        raise ValueError("fit_preprocessing: boş eğitim fold'u")
    ctx = _model_ctx(precision)
    uses_f3 = "f3" in recipe.substantive

    # Adım 1: f3 karşılaştırılabilirlik filtresi.
    training_f3 = {t: (training_raw[t].get("f3") if uses_f3 else None) for t in tickers}
    mode, mode_tie = filter_mode([filter_status.get(t) for t in tickers if training_f3[t] is not None])
    nulled: list[str] = []
    filtered_f3: dict[str, Optional[Decimal]] = dict(training_f3)
    for t in tickers:
        if training_f3[t] is not None and opposite_explicit_status(filter_status.get(t), mode):
            filtered_f3[t] = None
            nulled.append(t)
    mode_after, mode_after_tie = filter_mode([filter_status.get(t) for t in tickers if filtered_f3[t] is not None])

    working: dict[str, dict[str, Optional[Decimal]]] = {t: dict(training_raw[t]) for t in tickers}
    if uses_f3:
        for t in tickers:
            working[t]["f3"] = filtered_f3[t]

    # Adım 2-3: eksiklik ve %40 düşürme.
    active = list(recipe.substantive)
    dropped: dict[str, str] = {}
    for fid in recipe.substantive:
        missing = sum(1 for t in tickers if working[t].get(fid) is None)
        if recipe.missingness_drop and Fraction(missing, n) > MISSINGNESS_FOLD_DROP_THRESHOLD:
            active.remove(fid)
            dropped[fid] = STATUS_MISSINGNESS_FOLD_DROP
    create_f5 = recipe.indicator and "f3" in active
    extras = list(recipe.extra)
    for fid in (active if not recipe.impute else []) + extras:
        absent = [t for t in tickers if working[t].get(fid) is None]
        if absent:
            raise MissingValueError(f"{fid}: {len(absent)} eğitim satırında eksik (ilk {absent[0]}); bu tarifte imputasyon yok")

    # Adım 4: winsor (tarifin `winsor` özellikleri; varsayılan yalnız f3).
    winsor: dict[str, tuple[Fraction, Fraction]] = {}
    winsorized: dict[str, dict[str, Optional[Fraction]]] = {t: {} for t in tickers}
    for fid in active + extras:
        raw_vals = {t: Fraction(working[t][fid]) for t in tickers if working[t].get(fid) is not None}
        if fid in recipe.winsor and raw_vals:
            ordered = sorted(raw_vals.values())
            lo = quantile_type7(ordered, WINSOR_P05)
            hi = quantile_type7(ordered, WINSOR_P95)
            winsor[fid] = (lo, hi)
            for t, v in raw_vals.items():
                winsorized[t][fid] = min(max(v, lo), hi)
            for t in tickers:
                if working[t].get(fid) is None:
                    winsorized[t][fid] = None
        else:
            for t in tickers:
                v = working[t].get(fid)
                winsorized[t][fid] = Fraction(v) if v is not None else None

    # Adım 5: medyanla doldurma.
    exact: dict[str, dict[str, Fraction]] = {t: {} for t in tickers}
    f3_missing_flag = {t: False for t in tickers}
    medians: dict[str, Fraction] = {}
    for fid in active + extras:
        present = [winsorized[t][fid] for t in tickers if winsorized[t].get(fid) is not None]
        med = median_exact(present) if present and recipe.impute and fid not in extras else None
        if med is not None:
            medians[fid] = med
        for t in tickers:
            v = winsorized[t][fid]
            if v is None:
                if med is None:
                    raise ValueError(f"{fid}: doldurulacak eğitim değeri yok")
                exact[t][fid] = med
                if fid == "f3":
                    f3_missing_flag[t] = True
            else:
                exact[t][fid] = v

    # Adım 6: f5.
    indicator: list[str] = []
    if create_f5:
        indicator.append(INDICATOR_FEATURE)
        for t in tickers:
            exact[t][INDICATOR_FEATURE] = Fraction(1) if f3_missing_flag[t] else Fraction(0)

    for fid in recipe.log:
        if fid in active:
            for t in tickers:
                if exact[t][fid] <= 0:
                    raise NonPositiveLogInputError(f"{t}.{fid}={exact[t][fid]} pozitif değil; log alınamaz")

    # Adım 8: sıfır varyans (kesin) ve f3/f5 birlikte düşme.
    surviving: list[str] = []
    for col in list(active) + indicator + extras:
        if len({exact[t][col] for t in tickers}) <= 1:
            dropped[col] = STATUS_ZERO_VARIANCE_FOLD_DROP
        else:
            surviving.append(col)
    if "f3" in dropped and INDICATOR_FEATURE in surviving:
        surviving.remove(INDICATOR_FEATURE)
        dropped[INDICATOR_FEATURE] = STATUS_F3_COUPLED_DROP

    substantive = [c for c in surviving if c in recipe.substantive]
    columns = tuple(substantive + [c for c in surviving if c not in recipe.substantive])

    result = FittedPreprocessing(
        n_train=n,
        train_tickers=tuple(tickers),
        active_after_missingness=tuple(active + extras),
        columns=columns,
        dropped=dropped,
        create_f5=create_f5,
        f3_filter_mode=mode,
        f3_filter_mode_tie=mode_tie,
        f3_filter_mode_after=mode_after,
        f3_filter_mode_after_tie=mode_after_tie,
        f3_filter_nulled=tuple(nulled),
        winsor_exact=winsor,
        median_exact=medians,
        precision=precision,
        recipe_id=recipe.recipe_id,
        log_features=tuple(recipe.log),
    )
    if not (substantive or [c for c in surviving if c in extras]):
        result.insufficient_feature_variation = True
        result.columns = ()
        return result

    # Adım 7: log (tarifin `log` özellikleri, varsayılan f1; yapısal katman tamamlandıktan sonra).
    log_values: dict[str, dict[str, Decimal]] = {}
    for col in columns:
        if col in recipe.log:
            log_values[col] = {}
            for t in tickers:
                v_dec = _frac_to_dec(exact[t][col], ctx, col, "FRACTION_TO_DECIMAL", "TRAIN")
                log_values[col][t] = _finite_dec(_ln(v_dec, ctx, col, "TRAIN"), f"{t}.{col}.log_input")

    # Adım 9: z-skor.
    train_z: dict[str, dict[str, Decimal]] = {t: {} for t in tickers}
    for col in columns:
        if col in recipe.log:
            values = [log_values[col][t] for t in tickers]
            mean = _finite_dec(
                _div(_sum(values, ctx, col, "MEAN_SUM", "TRAIN"), Decimal(n), ctx, col, "MEAN_DIVIDE", "TRAIN"),
                f"{col}.mean",
            )
            variance = _finite_dec(
                _div(
                    _sum(((v - mean) ** 2 for v in values), ctx, col, "VARIANCE_SUM", "TRAIN"),
                    Decimal(n), ctx, col, "VARIANCE_DIVIDE", "TRAIN",
                ),
                f"{col}.variance",
            )
            if not variance > 0:
                raise NumericRepresentationIntegrityError(f"I2_POSITIVE_STD violated: {col} variance={variance!r}")
            std = _finite_dec(_sqrt(variance, ctx, col, "TRAIN"), f"{col}.std")
            if not std > 0:
                raise NumericRepresentationIntegrityError(f"I2_POSITIVE_STD violated: {col} std={std!r}")
            result.mean_dec[col], result.std_dec[col] = mean, std
            for t in tickers:
                train_z[t][col] = _finite_dec(
                    _div(_ambient_sub(log_values[col][t], mean), std, ctx, col, "Z_DIVIDE", "TRAIN"), f"{t}.{col}.z"
                )
        else:
            values_frac = [exact[t][col] for t in tickers]
            mean_frac = sum(values_frac, Fraction(0)) / n
            variance_frac = sum(((v - mean_frac) ** 2 for v in values_frac), Fraction(0)) / n
            if not variance_frac > 0:
                raise NumericRepresentationIntegrityError(f"I2_POSITIVE_STD violated: {col} variance={variance_frac!r}")
            variance_dec = _frac_to_dec(variance_frac, ctx, col, "VARIANCE_FRACTION_TO_DECIMAL", "TRAIN")
            std = _finite_dec(_sqrt(variance_dec, ctx, col, "TRAIN"), f"{col}.std")
            if not std > 0:
                raise NumericRepresentationIntegrityError(f"I2_POSITIVE_STD violated: {col} std={std!r}")
            result.std_dec[col] = std
            result.mean_exact[col] = mean_frac
            result.mean_dec[col] = _frac_to_dec(mean_frac, ctx, col, "MEAN_FRACTION_TO_DECIMAL", "REPORTING")
            for t in tickers:
                diff_dec = _frac_to_dec(exact[t][col] - mean_frac, ctx, col, "Z_NUMERATOR", "TRAIN")
                train_z[t][col] = _finite_dec(_div(diff_dec, std, ctx, col, "Z_DIVIDE", "TRAIN"), f"{t}.{col}.z")

    # I3: kesin ayrık değer sayısı binary64'te korunmalı.
    for col in columns:
        exact_distinct = {exact[t][col] for t in tickers}
        floats: list[float] = []
        for t in tickers:
            fv = _to_float(train_z[t][col], col, "Z_TO_BINARY64", "TRAIN")
            result.train_matrix.setdefault(t, {})[col] = fv
            floats.append(fv)
        if len(set(floats)) != len(exact_distinct):
            raise NumericRepresentationIntegrityError(
                f"I3_DISTINCTNESS_PRESERVATION violated: {col}: {len(exact_distinct)} kesin ayrık değer, "
                f"{len(set(floats))} ayrık binary64 z"
            )
    return result


def preprocess_fold(
    training_raw: Mapping[str, Mapping[str, Optional[Decimal]]],
    test_raw: Mapping[str, Optional[Decimal]],
    filter_status: Mapping[str, Optional[str]],
    *,
    recipe: Recipe = V1_5_RECIPE,
) -> tuple[FittedPreprocessing, Optional[dict[str, Any]]]:
    """Legacy imzası: filter_status test satırının durumunu "__test__" anahtarında taşır."""
    fitted = fit_preprocessing(training_raw, {t: filter_status.get(t) for t in training_raw}, recipe=recipe)
    if fitted.insufficient_feature_variation:
        return fitted, None
    return fitted, fitted.transform(test_raw, filter_status.get("__test__"))

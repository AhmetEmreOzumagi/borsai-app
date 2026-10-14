"""fit(model_spec, training_rows) -> params (dict). numpy + scikit-learn.

V1.5 fit'i legacy `scripts/modeling/candidate_models.py`'nin (fit_ridge_candidate,
fit_logistic_candidate) portudur: aynı ızgara, aynı iç LOOCV, aynı eşitlik
kuralları, aynı sklearn çağrıları ve aynı matris sırası. Legacy'den farkı:
- iç LOOCV ön işlemesi Ridge ve Logit için bir kez hesaplanıp paylaşılır
  (deterministik olduğu için sonuç aynıdır; legacy iki kez hesaplıyordu);
- final modelin katsayıları, sabiti ve ön işleme parametreleri dışa aktarılır
  (legacy bunları atıyordu, CHECKUP §A.0).

Tek kod yolu, birden çok ızgara (SPEC_V1_6 §4, kabul testi 3): `GridConfig`
ızgarayı ve iki politikayı taşır. `V1_5_GRID` V1.5'in kendisidir (altın ledger'ı
bayt bayt üretir). `V1_6_GRID`: genişletilmiş ızgara, INF/ZERO kapalı biçim uçlar,
aday başına yakınsamama. `PB_GRID`: V1.6 ızgarası, azınlık < 2'de C = ZERO
(SPEC_PB_V0 §3). Aynı çekirdek `v1_5_market20_v0` (f1–f6) ve `pb_v0`'ı (pb1–pb3)
farklı ön işleme tarifleriyle (borsai/preprocess.py) fit eder.

`fit_v1_5_horizon` backtest'in fold çekirdeğidir; `fit` 99 arzla dondurulacak
parametre dosyasını üretir. Tavan modelleri borsai/hazard.py'dedir.
"""
from __future__ import annotations

import math
import statistics
import warnings
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression, Ridge

from . import preprocess as pp
from .data import IPORow
from .features import FEATURE_DEFINITIONS, FEATURE_IDS as FEATURE_IDS_V15, SUBSTANTIVE_FEATURE_IDS, compute_features
from .horizons import HORIZONS
from .provenance import code_version, identity_hash, now_istanbul, runtime_versions
from .rules import rule_p_up, rule_return
from .specs import CEILING_PATH_ALGORITHM, HAZARD_ALGORITHM, KM_ALGORITHMS, RUNTIME_PINS, SCHEMA_VERSION, spec_sha256

RIDGE_ALPHA_GRID: tuple[float, ...] = (0.1, 1.0, 10.0, 100.0)
LOGISTIC_C_GRID: tuple[float, ...] = (0.01, 0.1, 1.0, 10.0)
LOGISTIC_FALLBACK_C = 0.01
MIN_TRAIN_N = 10

# SPEC_V1_6 §3: INF = yalnız sabit terim (eğitim ortalaması); ZERO = yalnız sabit terim
# (eğitim oranı). Sıralamada INF tüm sonlu α'lardan büyük, ZERO tüm pozitif C'lerden küçük.
INF = math.inf
ZERO = 0.0
V1_6_ALPHA_GRID: tuple[float, ...] = (0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0, INF)
V1_6_C_GRID: tuple[float, ...] = (ZERO, 0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0)
POLICY_FOLD = "MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE"
POLICY_CANDIDATE = "CANDIDATE_NOT_CONVERGED_DROPPED_FINAL_FIT_FALLS_BACK_TO_NEXT_RANKED"
FALLBACK_POLICY = {"NO_TUNING_FIXED_C_0.01": 0.01, "NO_TUNING_FIXED_C_ZERO": ZERO}
STATUS_SCORED = "SCORED"
STATUS_CANDIDATE_NOT_CONVERGED = "CANDIDATE_NOT_CONVERGED"


@dataclass(frozen=True)
class GridConfig:
    name: str
    alpha_grid: tuple[float, ...]
    C_grid: tuple[float, ...]
    convergence_policy: str
    fallback_C: float

    @property
    def legacy_format(self) -> bool:
        """V1.5 ledger/JSON biçimi (altın ledger'la bayt eşitliği için)."""
        return self.name == "v1_5"


V1_5_GRID = GridConfig("v1_5", RIDGE_ALPHA_GRID, LOGISTIC_C_GRID, POLICY_FOLD, LOGISTIC_FALLBACK_C)
V1_6_GRID = GridConfig("v1_6", V1_6_ALPHA_GRID, V1_6_C_GRID, POLICY_CANDIDATE, LOGISTIC_FALLBACK_C)
PB_GRID = GridConfig("pb_v0", V1_6_ALPHA_GRID, V1_6_C_GRID, POLICY_CANDIDATE, ZERO)


def hp_label(value: Optional[float], kind: str) -> Any:
    """JSON/ledger biçimi: INF ve ZERO metin, diğerleri sayı."""
    if value is None:
        return None
    if kind == "alpha" and value == INF:
        return "INF"
    if kind == "C" and value == ZERO:
        return "ZERO"
    return value


def hp_parse(value: Any) -> float:
    return INF if value == "INF" else ZERO if value == "ZERO" else float(value)


def grid_from_spec(spec: Mapping[str, Any]) -> GridConfig:
    """Şartnamedeki ızgara ve politikalardan GridConfig; bilinen üç yapılandırmadan biri olmalı."""
    cfg = GridConfig(
        name=spec.get("grid_version", "v1_5") if spec["logit"]["minority_lt_2_policy"] != "NO_TUNING_FIXED_C_ZERO" else "pb_v0",
        alpha_grid=tuple(hp_parse(a) for a in spec["ridge"]["alpha_grid"]),
        C_grid=tuple(hp_parse(c) for c in spec["logit"]["C_grid"]),
        convergence_policy=spec["logit"]["non_convergence_policy"],
        fallback_C=FALLBACK_POLICY[spec["logit"]["minority_lt_2_policy"]],
    )
    if cfg not in (V1_5_GRID, V1_6_GRID, PB_GRID):
        raise ValueError(f"tanınmayan ızgara yapılandırması: {cfg}")
    return cfg


_LOGIT_KWARGS = dict(l1_ratio=0.0, solver="lbfgs", fit_intercept=True, class_weight=None, max_iter=10000, tol=1e-10)

STATUS_FIT_OK = "FIT_OK"
STATUS_INSUFFICIENT_TRAINING_HISTORY = "INSUFFICIENT_TRAINING_HISTORY"
STATUS_INSUFFICIENT_FEATURE_VARIATION = "INSUFFICIENT_FEATURE_VARIATION"
STATUS_INNER_INSUFFICIENT_VARIATION = "MODEL_NOT_FIT_INNER_PREPROCESSING_INSUFFICIENT_VARIATION"
STATUS_SINGLE_CLASS = "MODEL_NOT_FIT_SINGLE_CLASS"
STATUS_INNER_SINGLE_CLASS = "MODEL_NOT_FIT_INNER_SINGLE_CLASS"
STATUS_NOT_CONVERGED = "MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE"
TUNED_INNER_LOOCV = "TUNED_INNER_LOOCV"
TUNING_SKIPPED_MINORITY_LT_2 = "TUNING_SKIPPED_MINORITY_COUNT_LT_2"
TUNING_NOT_APPLICABLE = "TUNING_NOT_APPLICABLE"


class RuntimeContractMismatchError(RuntimeError):
    pass


class FitError(RuntimeError):
    pass


def verify_runtime() -> dict[str, str]:
    """pyproject.toml'daki birebir sürümler. Uymazsa durur (legacy verify_runtime)."""
    versions = runtime_versions()
    mismatches = [
        f"{k}: beklenen {v}, bulunan {versions[k]}"
        for k, v in RUNTIME_PINS.items()
        if (versions[k] if k != "python" else ".".join(versions[k].split(".")[:2])) != v
    ]
    if mismatches:
        raise RuntimeContractMismatchError("; ".join(mismatches))
    return versions


def _finite(value: float, label: str) -> float:
    if not math.isfinite(value):
        raise pp.NumericRepresentationIntegrityError(f"NUMERIC_REPRESENTATION_INTEGRITY_ERROR: {label}={value!r}")
    return value


@dataclass(frozen=True)
class ScoreEntry:
    hyperparameter: float
    score: Optional[float]
    fold_count: int
    status: str = STATUS_SCORED


@dataclass
class RidgeFit:
    status: str
    effective_n: int
    selected_alpha: Optional[float] = None
    tuning_status: str = TUNING_NOT_APPLICABLE
    inner_fold_n: int = 0
    score_table: tuple[ScoreEntry, ...] = ()
    columns: tuple[str, ...] = ()
    estimator: Any = None
    prediction: Optional[float] = None
    constant: Optional[float] = None  # α = INF: eğitim ortalaması

    def intercept_coef(self) -> tuple[float, list[float]]:
        if self.selected_alpha == INF:
            return self.constant, [0.0] * len(self.columns)
        return float(self.estimator.intercept_), [float(c) for c in self.estimator.coef_]


@dataclass
class LogitFit:
    status: str
    effective_n: int
    selected_C: Optional[float] = None
    tuning_status: str = TUNING_NOT_APPLICABLE
    inner_fold_n: int = 0
    score_table: tuple[ScoreEntry, ...] = ()
    columns: tuple[str, ...] = ()
    estimator: Any = None
    probability: Optional[float] = None
    predicted_class: Optional[int] = None
    n_class_0: int = 0
    n_class_1: int = 0
    observed_fit_warnings: tuple[str, ...] = ()
    constant: Optional[float] = None  # C = ZERO: eğitim oranı
    final_attempts: tuple[tuple[Any, str], ...] = ()  # aday başına politikada nihai fit denemeleri

    def intercept_coef(self) -> tuple[float, list[float]]:
        if self.selected_C == ZERO:
            p = self.constant
            return math.log(p / (1.0 - p)), [0.0] * len(self.columns)
        return float(self.estimator.intercept_[0]), [float(c) for c in self.estimator.coef_[0]]


@dataclass
class _InnerFold:
    held_out: str
    inner_train: list[str]
    fitted: pp.FittedPreprocessing
    val: Optional[dict[str, Any]]


@dataclass
class V15HorizonFit:
    order: tuple[str, ...]
    final: Optional[pp.FittedPreprocessing]
    test: Optional[dict[str, Any]]
    ridge: RidgeFit
    logit: LogitFit
    filter_stats: dict[str, int] = field(default_factory=dict)


class _InnerCache:
    """İç LOOCV ön işlemesi: her iç bölmede yalnız o bölmenin eğitim satırlarından
    öğrenilir (dış test satırı hiç görülmez). Bir kez hesaplanır, Ridge ve Logit
    paylaşır."""

    def __init__(self, order: Sequence[str], raw: Mapping[str, Mapping], status: Mapping[str, Optional[str]],
                 recipe: pp.Recipe = pp.V1_5_RECIPE):
        self._order, self._raw, self._status, self._recipe = list(order), raw, status, recipe
        self._folds: Optional[list[_InnerFold]] = None

    def folds(self) -> list[_InnerFold]:
        if self._folds is None:
            folds = []
            for held_out in self._order:
                inner_train = [t for t in self._order if t != held_out]
                fitted = pp.fit_preprocessing({t: self._raw[t] for t in inner_train}, {t: self._status.get(t) for t in inner_train},
                                              recipe=self._recipe)
                val = None if fitted.insufficient_feature_variation else fitted.transform(self._raw[held_out], self._status.get(held_out))
                folds.append(_InnerFold(held_out, inner_train, fitted, val))
            self._folds = folds
        return self._folds

    @property
    def computed(self) -> bool:
        return self._folds is not None


def _matrix(fitted: pp.FittedPreprocessing, order: Sequence[str]) -> np.ndarray:
    return np.array(fitted.matrix_rows(list(order)), dtype=np.float64)


def _row(z: Mapping[str, float], columns: Sequence[str]) -> np.ndarray:
    return np.array([z[c] for c in columns], dtype=np.float64).reshape(1, -1)


def _fit_logistic(estimator: LogisticRegression, X: np.ndarray, y: np.ndarray) -> tuple[list, list[str]]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        estimator.fit(X, y)
    convergence = [w for w in caught if issubclass(w.category, ConvergenceWarning)]
    other = [str(w.message) for w in caught if not issubclass(w.category, ConvergenceWarning)]
    return convergence, other


def _p1(estimator: LogisticRegression, x: np.ndarray) -> float:
    proba = estimator.predict_proba(x)[0]
    return float(proba[list(estimator.classes_).index(1)])


def _brier_term(p1: float, y: int, label: str) -> float:
    diff = _finite(p1 - y, f"{label} brier_difference")
    return _finite(diff ** 2, f"{label} brier_term")


def select_alpha(entries: Sequence[ScoreEntry]) -> float:
    """En küçük iç LOOCV MAE; bit-eşit eşitlikte en büyük α (INF en büyük)."""
    best = min(e.score for e in entries)
    return max(e.hyperparameter for e in entries if e.score == best)


def rank_C(entries: Sequence[ScoreEntry]) -> list[float]:
    """Skorlanan C'ler (skor artan, eşitlikte C artan; ZERO en küçük). İlki seçilen C'dir;
    aday başına politikada nihai fit yakınsamazsa sıradaki denenir."""
    scored = [e for e in entries if e.status == STATUS_SCORED]
    return [e.hyperparameter for e in sorted(scored, key=lambda e: (e.score, e.hyperparameter))]


def train_mean(values: Sequence[float]) -> float:
    """α = INF adayının tahmini: eğitim hedeflerinin aritmetik ortalaması (statistics.mean;
    `base_train_mean` kuralıyla aynı tanım)."""
    return statistics.mean(values)


def _fit_ridge(order, R, inner: _InnerCache, final, test, grid: GridConfig = V1_5_GRID) -> RidgeFit:
    n = len(order)
    if n < MIN_TRAIN_N:
        return RidgeFit(status=STATUS_INSUFFICIENT_TRAINING_HISTORY, effective_n=n)
    folds = inner.folds()
    if any(f.fitted.insufficient_feature_variation for f in folds):
        return RidgeFit(status=STATUS_INNER_INSUFFICIENT_VARIATION, effective_n=n, inner_fold_n=n)
    table: list[ScoreEntry] = []
    for alpha in grid.alpha_grid:
        abs_errors: list[float] = []
        for f in folds:
            if alpha == INF:
                yhat = _finite(train_mean([R[t] for t in f.inner_train]), f"alpha=INF {f.held_out} yhat")
            else:
                est = Ridge(alpha=alpha, fit_intercept=True, solver="svd")
                est.fit(_matrix(f.fitted, f.inner_train), np.array([R[t] for t in f.inner_train], dtype=np.float64))
                yhat = _finite(float(est.predict(_row(f.val["z"], f.fitted.columns))[0]), f"alpha={alpha} {f.held_out} yhat")
            abs_errors.append(_finite(abs(R[f.held_out] - yhat), f"alpha={alpha} {f.held_out} abs_error"))
        table.append(ScoreEntry(alpha, _finite(sum(abs_errors) / len(abs_errors), f"alpha={alpha} MAE"), len(folds)))
    selected = select_alpha(table)
    if final.insufficient_feature_variation:
        return RidgeFit(status=STATUS_INSUFFICIENT_FEATURE_VARIATION, effective_n=n, inner_fold_n=len(folds), score_table=tuple(table))
    common = dict(status=STATUS_FIT_OK, effective_n=n, selected_alpha=selected, tuning_status=TUNED_INNER_LOOCV,
                  inner_fold_n=len(folds), score_table=tuple(table), columns=final.columns)
    if selected == INF:
        constant = _finite(train_mean([R[t] for t in order]), "final_constant")
        return RidgeFit(**common, constant=constant, prediction=None if test is None else constant)
    est = Ridge(alpha=selected, fit_intercept=True, solver="svd")
    est.fit(_matrix(final, order), np.array([R[t] for t in order], dtype=np.float64))
    prediction = None
    if test is not None:
        prediction = _finite(float(est.predict(_row(test["z"], final.columns))[0]), "final_prediction")
    return RidgeFit(**common, estimator=est, prediction=prediction)


def train_rate(labels: Sequence[int]) -> float:
    """C = ZERO adayının olasılığı: n_1 / n (cezasız sabit terimli lojistiğin tam çözümü)."""
    return sum(labels) / len(labels)


def _fit_logit(order, Y, inner: _InnerCache, final, test, grid: GridConfig = V1_5_GRID) -> LogitFit:
    n = len(order)
    if n < MIN_TRAIN_N:
        return LogitFit(status=STATUS_INSUFFICIENT_TRAINING_HISTORY, effective_n=n)
    y_seq = [Y[t] for t in order]
    n1 = sum(y_seq)
    n0 = n - n1
    counts = dict(n_class_0=n0, n_class_1=n1)
    if n0 == 0 or n1 == 0:
        return LogitFit(status=STATUS_SINGLE_CLASS, effective_n=n, **counts)
    per_candidate = grid.convergence_policy == POLICY_CANDIDATE
    table: tuple[ScoreEntry, ...] = ()
    inner_n = 0
    if min(n0, n1) < 2:
        selected, tuning = grid.fallback_C, TUNING_SKIPPED_MINORITY_LT_2
        ranked = [selected] + ([ZERO] if selected != ZERO else [])
    else:
        folds = inner.folds()
        for f in folds:
            if f.fitted.insufficient_feature_variation:
                return LogitFit(status=STATUS_INNER_INSUFFICIENT_VARIATION, effective_n=n, inner_fold_n=n, **counts)
            if len({Y[t] for t in f.inner_train}) < 2:
                return LogitFit(status=STATUS_INNER_SINGLE_CLASS, effective_n=n, inner_fold_n=n, **counts)
        entries: list[ScoreEntry] = []
        for C in grid.C_grid:
            terms: list[float] = []
            dropped = False
            for f in folds:
                if C == ZERO:
                    p1 = _finite(train_rate([Y[t] for t in f.inner_train]), f"C=ZERO {f.held_out} p1")
                else:
                    est = LogisticRegression(C=C, **_LOGIT_KWARGS)
                    conv, _ = _fit_logistic(est, _matrix(f.fitted, f.inner_train), np.array([Y[t] for t in f.inner_train], dtype=np.float64))
                    if conv:
                        if not per_candidate:
                            return LogitFit(status=STATUS_NOT_CONVERGED, effective_n=n, inner_fold_n=len(folds), **counts)
                        dropped = True
                        break
                    p1 = _finite(_p1(est, _row(f.val["z"], f.fitted.columns)), f"C={C} {f.held_out} p1")
                terms.append(_brier_term(p1, Y[f.held_out], f"C={C} {f.held_out}"))
            if dropped:
                entries.append(ScoreEntry(C, None, len(folds), STATUS_CANDIDATE_NOT_CONVERGED))
                continue
            entries.append(ScoreEntry(C, _finite(sum(terms) / len(terms), f"C={C} Brier"), len(folds)))
        ranked = rank_C(entries)
        selected = ranked[0]
        tuning, table, inner_n = TUNED_INNER_LOOCV, tuple(entries), len(folds)
    common = dict(effective_n=n, tuning_status=tuning, inner_fold_n=inner_n, score_table=table, **counts)
    if final.insufficient_feature_variation:
        return LogitFit(status=STATUS_INSUFFICIENT_FEATURE_VARIATION, selected_C=selected, **common)
    attempts: list[tuple[Any, str]] = []
    for C in (ranked if per_candidate else [selected]):
        if C == ZERO:
            p = _finite(train_rate(y_seq), "final ZERO rate")
            probability = predicted = None
            if test is not None:
                probability, predicted = p, (1 if p > 0.5 else 0)
            attempts.append((hp_label(C, "C"), STATUS_FIT_OK))
            return LogitFit(status=STATUS_FIT_OK, selected_C=ZERO, columns=final.columns, probability=probability,
                            predicted_class=predicted, constant=p, final_attempts=tuple(attempts), **common)
        est = LogisticRegression(C=C, **_LOGIT_KWARGS)
        conv, other = _fit_logistic(est, _matrix(final, order), np.array(y_seq, dtype=np.float64))
        if conv:
            attempts.append((hp_label(C, "C"), STATUS_NOT_CONVERGED))
            continue
        attempts.append((hp_label(C, "C"), STATUS_FIT_OK))
        probability = predicted = None
        if test is not None:
            probability = _finite(_p1(est, _row(test["z"], final.columns)), "final p1")
            predicted = 1 if probability > 0.5 else 0
        return LogitFit(
            status=STATUS_FIT_OK, selected_C=C, columns=final.columns, estimator=est, probability=probability,
            predicted_class=predicted, observed_fit_warnings=tuple(other),
            final_attempts=tuple(attempts) if per_candidate else (), **common,
        )
    return LogitFit(status=STATUS_NOT_CONVERGED, selected_C=selected,
                    final_attempts=tuple(attempts) if per_candidate else (), **common)


def fit_v1_5_horizon(
    order: Sequence[str],
    raw: Mapping[str, Mapping[str, Optional[Decimal]]],
    R: Mapping[str, float],
    Y: Mapping[str, int],
    filter_status: Mapping[str, Optional[str]],
    *,
    test_raw: Optional[Mapping[str, Optional[Decimal]]] = None,
    test_filter_status: Optional[str] = None,
    grid: GridConfig = V1_5_GRID,
    recipe: pp.Recipe = pp.V1_5_RECIPE,
) -> V15HorizonFit:
    """Bir ufuk için Ridge + Logit (V1.5 sınıfı). `order` eğitim satır sırasıdır
    (first_trading_date, ticker); dış test hedefi hiçbir argümanla verilemez.
    `grid`/`recipe` varsayılanları V1.5'in kendisidir."""
    order = list(order)
    inner = _InnerCache(order, raw, filter_status, recipe)
    final = test = None
    if len(order) >= MIN_TRAIN_N:
        final = pp.fit_preprocessing({t: raw[t] for t in order}, {t: filter_status.get(t) for t in order}, recipe=recipe)
        if test_raw is not None and not final.insufficient_feature_variation:
            test = final.transform(test_raw, test_filter_status)
    ridge = _fit_ridge(order, R, inner, final, test, grid)
    logit = _fit_logit(order, Y, inner, final, test, grid)
    stats = {"f3_filter_nulled_n": 0, "f3_filter_mode_ties_n": 0}
    preps = ([f.fitted for f in inner.folds()] if inner.computed else []) + ([final] if final is not None else [])
    for p in preps:
        stats["f3_filter_nulled_n"] += len(p.f3_filter_nulled)
        stats["f3_filter_mode_ties_n"] += int(p.f3_filter_mode_tie) + int(p.f3_filter_mode_after_tie)
    if inner.computed:
        stats["f3_filter_nulled_n"] += sum(int(f.val["f3_nulled_by_filter"]) for f in inner.folds() if f.val)
    if test is not None:
        stats["f3_filter_nulled_n"] += int(test["f3_nulled_by_filter"])
    return V15HorizonFit(order=tuple(order), final=final, test=test, ridge=ridge, logit=logit, filter_stats=stats)


# ---------------------------------------------------------------------------
# Dondurulacak parametre dosyası
# ---------------------------------------------------------------------------

MARKET20_FEATURE_DEFINITION = (
    "XU100(S0)/XU100(S20) − 1; S0 = ref_date'ten kesin önceki son resmi seans (Takvim B), S20 = 20 seans öncesi; "
    "Decimal 60 hane; ref_date = T (eğitim), tahmin tarihi (canlı); impute edilmez (borsai/market20.py)"
)


def training_raw_features(rows: Sequence[IPORow]) -> dict[str, dict[str, Optional[Decimal]]]:
    return {r.ticker: compute_features(**r.feature_inputs()).as_dict() for r in rows}


def feature_ranges(raw: Mapping[str, Mapping[str, Optional[Decimal]]],
                   features: Sequence[str] = SUBSTANTIVE_FEATURE_IDS) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for fid in features:
        values = [v[fid] for v in raw.values() if v[fid] is not None]
        out[fid] = {"min": float(min(values)), "max": float(max(values)), "n": len(values),
                    "n_missing": len(raw) - len(values)}
    return out


def recipe_for(spec: Mapping[str, Any]) -> pp.Recipe:
    """Şartnamenin ön işleme kimliği ve özellik listesinden tarif (f5 göstergedir, listede sayılmaz)."""
    feats = tuple(f for f in spec["features"] if f != "f5")
    for recipe in pp.RECIPES.values():
        if recipe.recipe_id == spec["preprocessing_id"] and recipe.features == feats:
            return recipe
    raise FitError(f"{spec['model_id']}: ön işleme tarifi bulunamadı ({spec['preprocessing_id']}, {feats})")


def uses_pb_features(spec: Mapping[str, Any]) -> bool:
    return any(f.startswith("pb") for f in spec["features"])


def model_raw_features(spec: Mapping[str, Any], rows: Sequence[IPORow]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Şartnamenin özellikleri için ham değerler (ön işleme öncesi) ve kaynak bilgisi.
    V1.5 özellikleri borsai.features.compute_features'tan, PB özellikleri
    compute_pb_features'tan (yalnız 8 planlanan yapı alanı), f6 borsai.market20'den."""
    from .features import compute_pb_features

    info: dict[str, Any] = {}
    if uses_pb_features(spec):
        from .data import load_pb

        pb = load_pb(rows)
        return {r.ticker: compute_pb_features(pb[r.ticker].fields).as_dict() for r in rows}, info
    raw = training_raw_features(rows)
    if "f6" in spec["features"]:
        from .market20 import h99_market20

        m20 = h99_market20([(r.ticker, r.first_trading_date) for r in rows])
        refused = {t: m.refusal for t, m in m20.items() if m.f6 is None}
        if refused:
            raise FitError(f"f6 hesaplanamayan eğitim satırları (şartname: satır dışlanır, n yeniden sayılır): {refused}")
        for t in raw:
            raw[t] = {**raw[t], "f6": m20[t].f6}
        info["market20_training"] = {t: m.as_record() for t, m in m20.items()}
    return raw, info


def select_training_rows(spec: Mapping[str, Any], rows: Sequence[IPORow]) -> list[IPORow]:
    if spec["training"]["set"] == "H99_F3_PRESENT":
        return [r for r in rows if r.inputs["total_demand_multiple"] is not None]
    return list(rows)


def _training_block(spec: Mapping[str, Any], rows: Sequence[IPORow], dataset_version: str) -> dict[str, Any]:
    tickers = [r.ticker for r in rows]
    uses = spec["training"]["set"] != "NONE"
    block: dict[str, Any] = {
        "set": spec["training"]["set"],
        "tickers": tickers if uses else [],
        "tickers_sha256": identity_hash(tickers) if uses else None,
        "n": len(tickers) if uses else 0,
        "cutoff_date": max(r.targets[h].session_date for r in rows for h in HORIZONS) if uses else None,
        "first_trading_date_range": [rows[0].first_trading_date, rows[-1].first_trading_date] if uses else None,
        "data_version_sha256": dataset_version,
    }
    if uses:
        block["targets_sha256"] = {
            h: identity_hash([f"{r.ticker}|{r.targets[h].session_date}|{r.targets[h].R}|{r.targets[h].Y}" for r in rows])
            for h in HORIZONS
        }
    return block


def _survival_training_block(spec: Mapping[str, Any], rows: Sequence[IPORow], dataset_version: str) -> dict[str, Any]:
    tickers = [r.ticker for r in rows]
    return {
        "set": spec["training"]["set"],
        "tickers": tickers,
        "tickers_sha256": identity_hash(tickers),
        "n": len(tickers),
        "n_ipo": len(tickers),
        "cutoff_date": max(d for r in rows for d in r.session_dates),
        "first_trading_date_range": [rows[0].first_trading_date, rows[-1].first_trading_date],
        "data_version_sha256": dataset_version,
        "labels_sha256": identity_hash([
            f"{r.ticker}|{r.ceiling_streak}|{','.join(r.session_dates)}|{''.join(str(c) for c in r.ceiling_close)}" for r in rows
        ]),
    }


def _check_training_rows(spec: Mapping[str, Any], rows: Sequence[IPORow], dataset_version: str) -> None:
    if dataset_version != spec["training"]["data_version_sha256"]:
        raise FitError(
            f"veri sürümü şartnameyle tutmuyor ({dataset_version} != {spec['training']['data_version_sha256']}); "
            "CLAUDE.md kural 5: yeni model_id gerekir"
        )
    if spec["training"]["set"] != "NONE" and len(rows) != spec["training"]["n"]:
        raise FitError(f"eğitim n'i {len(rows)} != şartname {spec['training']['n']}")
    order = [(r.first_trading_date, r.ticker) for r in rows]
    if order != sorted(order) or len({r.ticker for r in rows}) != len(rows):
        raise FitError("eğitim satırları (first_trading_date, ticker) sırasında ve tekil olmalı")


def _envelope(spec: Mapping[str, Any], rows: Sequence[IPORow], dataset_version: str, training: Optional[dict] = None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "model_id": spec["model_id"],
        "algorithm": spec["algorithm"],
        "description": spec["description"],
        "spec": dict(spec),
        "spec_sha256": spec_sha256(dict(spec)),
        "features": list(spec["features"]),
        "training": training if training is not None else _training_block(spec, rows, dataset_version),
        "code_version": code_version(),
        "created_at": now_istanbul(),
    }


def _table_key(value: float, kind: str) -> str:
    label = hp_label(value, kind)
    return label if isinstance(label, str) else repr(label)


def linear_heads(hf: V15HorizonFit, grid: GridConfig) -> dict[str, Any]:
    """Bir ufkun JSON kafaları. V1.5 biçimi (grid.legacy_format) dondurulmuş v1_5_h99 ile aynıdır."""
    r_int, r_coef = hf.ridge.intercept_coef()
    l_int, l_coef = hf.logit.intercept_coef()
    ret = {
        "kind": "ridge",
        "alpha": hf.ridge.selected_alpha if grid.legacy_format else hp_label(hf.ridge.selected_alpha, "alpha"),
        "intercept": r_int,
        "coef": r_coef,
        "columns": list(hf.ridge.columns),
        "inner_loocv_mae": {(repr(e.hyperparameter) if grid.legacy_format else _table_key(e.hyperparameter, "alpha")): e.score
                            for e in hf.ridge.score_table},
    }
    p_up = {
        "kind": "logit",
        "C": hf.logit.selected_C if grid.legacy_format else hp_label(hf.logit.selected_C, "C"),
        "intercept": l_int,
        "coef": l_coef,
        "columns": list(hf.logit.columns),
        "inner_loocv_brier": {(repr(e.hyperparameter) if grid.legacy_format else _table_key(e.hyperparameter, "C")): e.score
                              for e in hf.logit.score_table},
        "tuning_status": hf.logit.tuning_status,
        "n_class_0": hf.logit.n_class_0,
        "n_class_1": hf.logit.n_class_1,
    }
    if not grid.legacy_format:
        p_up["inner_loocv_status"] = {_table_key(e.hyperparameter, "C"): e.status for e in hf.logit.score_table}
        p_up["final_fit_attempts"] = [list(a) for a in hf.logit.final_attempts]
    return {"return": ret, "p_up": p_up}


def _feature_definitions(spec: Mapping[str, Any]) -> dict[str, str]:
    from .features import PB_FEATURE_DEFINITIONS

    if uses_pb_features(spec):
        return {f: PB_FEATURE_DEFINITIONS[f] for f in list(spec["features"]) + ["pb4"]}
    defs = {f: FEATURE_DEFINITIONS[f] for f in spec["features"] if f in FEATURE_DEFINITIONS}
    if "f6" in spec["features"]:
        defs["f6"] = MARKET20_FEATURE_DEFINITION
    return defs


def fit_with_estimators(
    spec: Mapping[str, Any], rows: Sequence[IPORow], *, dataset_version: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """`fit` ile aynı; ek olarak final modelleri döndürür (testler): Ridge/Logit için
    ufuk -> V15HorizonFit, hazard için {"hazard": TrainingResult}."""
    if spec["algorithm"] in (HAZARD_ALGORITHM, *KM_ALGORITHMS):
        return _fit_survival(spec, rows, dataset_version)
    if spec["algorithm"] == CEILING_PATH_ALGORITHM:  # SPEC_CEILING_PATH_V0: yeni fit yok; hücreler + gömülü seri modeli
        from .ceiling_path import fit_params

        return fit_params(spec, rows, dataset_version), {}
    _check_training_rows(spec, rows, dataset_version)
    params = _envelope(spec, rows, dataset_version)
    fits: dict[str, Any] = {}
    if spec["algorithm"] == "V1_5_RIDGE_LOGIT":
        params["runtime"] = verify_runtime()
        grid = grid_from_spec(spec)
        recipe = recipe_for(spec)
        raw, info = model_raw_features(spec, rows)
        order = [r.ticker for r in rows]
        status = {r.ticker: r.total_demand_filter_status for r in rows}
        horizons: dict[str, Any] = {}
        prep_params = None
        for h in spec["horizons"]:
            R = {r.ticker: r.targets[h].R_float for r in rows}
            Y = {r.ticker: r.targets[h].Y for r in rows}
            hf = fit_v1_5_horizon(order, raw, R, Y, status, grid=grid, recipe=recipe)
            if hf.ridge.status != STATUS_FIT_OK or hf.logit.status != STATUS_FIT_OK:
                raise FitError(f"{h}: ridge={hf.ridge.status} logit={hf.logit.status}; dondurulacak model yok")
            this_prep = hf.final.params()
            if prep_params is None:
                prep_params = this_prep
            elif this_prep != prep_params:
                raise FitError(f"{h}: ön işleme parametreleri ufuklar arasında farklı (eğitim kümesi aynı olmalı)")
            fits[h] = hf
            horizons[h] = linear_heads(hf, grid)
        params["preprocessing"] = prep_params
        params["horizons"] = horizons
        params["feature_definitions"] = _feature_definitions(spec) if spec["features"] != list(FEATURE_IDS_V15) else dict(FEATURE_DEFINITIONS)
        params["feature_ranges"] = feature_ranges(raw, [f for f in spec["features"] if f != "f5"])
        params["input_policy"] = dict(spec["input_policy"])
        params.update(info)
    else:
        horizons = {}
        for h in spec["horizons"]:
            returns = [r.targets[h].R_float for r in rows]
            labels = [r.targets[h].Y for r in rows]
            ret, p = rule_return(spec["algorithm"], h, returns), rule_p_up(spec["algorithm"], labels)
            horizons[h] = {
                "return": None if ret is None else {"kind": "constant", "value": ret},
                "p_up": None if p is None else {"kind": "constant", "value": p},
            }
        params["preprocessing"] = None
        params["horizons"] = horizons
        params["feature_definitions"] = {}
        params["feature_ranges"] = {}
        params["input_policy"] = dict(spec["input_policy"])
    return params, fits


def _fit_survival(spec: Mapping[str, Any], rows: Sequence[IPORow], dataset_version: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Tavan modelleri (hazard, @INF) ve Kaplan–Meier kuralları: 10 günlük seri çıktısı."""
    from . import hazard as hz
    from . import survival as sv

    selected = select_training_rows(spec, rows)
    _check_training_rows(spec, selected, dataset_version)
    units = [sv.unit_of(r) for r in selected]
    params = _envelope(spec, selected, dataset_version, _survival_training_block(spec, selected, dataset_version))
    # Ortak şema: tavan modelleri D_h getirisi ve P(kapanış > arz) üretmez; çıktıları 10 günlük seridir.
    params["horizons"] = {h: {"return": None, "p_up": None} for h in HORIZONS}
    fits: dict[str, Any] = {}
    if spec["algorithm"] == HAZARD_ALGORITHM:
        params["runtime"] = verify_runtime()
        features = tuple(spec["features"])
        recipe = recipe_for(spec) if features else None
        raw = model_raw_features(spec, selected)[0] if features else {r.ticker: {} for r in selected}
        status = {r.ticker: r.total_demand_filter_status for r in selected}
        grid = tuple(hz.lambda_parse(x) for x in spec["lambda_grid"])
        res = hz.fit_training_set(units, raw, status, cutoff=None, features=features, recipe=recipe, grid=grid)
        if res.status != hz.STATUS_FIT_OK:
            raise FitError(f"{spec['model_id']}: nihai hazard fit'i {res.status}")
        fits["hazard"] = res
        params["training"].update(n_pp_rows=res.n_pp_rows, n_events=res.n_events, n_survivals=res.n_survivals)
        params.update({
            "day_groups": spec["day_groups"],
            "gamma": [float(g) for g in res.fit.gamma],
            "beta": res.beta_by_feature(),
            "columns": list(res.fit.columns),
            "lambda": hz.lambda_label(res.selected_lambda),
            "lambda_score_table": res.score_table,
            "reclose_rates": res.reclose,
            "pseudo_rows": {"weight": hz.PSEUDO_WEIGHT},
            "solver": {"iterations": res.fit.iterations, "grad_max": res.fit.grad_max},
            "preprocessing": res.prepared.prep.params() if res.prepared.prep is not None else None,
            "feature_definitions": _feature_definitions(spec) if features else {},
            "feature_ranges": feature_ranges(raw, features) if features else {},
            "input_policy": dict(spec["input_policy"]),
        })
    else:
        pp_rows = sv.pp_table(units)
        hazards = sv.km_hazards(pp_rows, last_n=spec.get("last_n"))
        S = sv.survival(hazards)
        rec = sv.reclose_counts(units)
        n_events = sum(r.event for r in pp_rows)
        params["training"].update(n_pp_rows=len(pp_rows), n_events=n_events, n_survivals=len(pp_rows) - n_events)
        params.update({
            "survival": {"hazard": hazards, "S": S, "P_L": sv.p_streak(S), "P_close_ceiling": sv.p_close(S, rec["r_a"], rec["r_b"])},
            "reclose_rates": rec,
            "preprocessing": None,
            "feature_definitions": {},
            "feature_ranges": {},
            "input_policy": dict(spec["input_policy"]),
        })
    return params, fits


def fit(model_spec: Mapping[str, Any], training_rows: Sequence[IPORow], *, dataset_version: str) -> dict[str, Any]:
    """Şartname + eğitim satırları -> JSON'a yazılabilir parametre sözlüğü."""
    return fit_with_estimators(model_spec, training_rows, dataset_version=dataset_version)[0]


# ---------------------------------------------------------------------------
# Faz 7C: düşen arz modeli v0 (SPEC_C_V0 §2, §4; SPEC_DEVIATIONS K). Ridge'siz Logit yolu: ufuk başına (D5, D10) bağımsız
# L2-lojistik, V1.6 C ızgarası, iç LOOCV Brier, aday başına yakınsamama; `_fit_logit`, `_InnerCache` ve `fit_preprocessing`
# DEĞİŞMEZ. Etiket tablonun Y_h'sidir (p_up başlığı; olay y_h = 1 − Y_h; L2-lojistik etiket çevirmesine simetriktir, SPEC_DEVIATIONS
# K). Tarifte imputasyon olmadığından f3 filtre adımının boşaltacağı arz o kümede kullanılmaz (J10 kuralı aynen; iç CV dahil).
# `@ZERO` kural satırı: V1.6 ZERO ucu, kapalı biçim eğitim oranı.
# ---------------------------------------------------------------------------

STATUS_TEST_F3_FILTER_CONFLICT = "TEST_F3_FILTER_STATUS_CONFLICT"


@dataclass
class FallHorizonFit:
    order: tuple[str, ...]                 # f3 filtre dışlamasından sonra kullanılan eğitim arzları (sıra korunur)
    excluded: tuple[str, ...]              # bu kümede kullanılmayan arzlar (J10 kuralı); @ZERO ve addsale'de boş
    final: Optional[pp.FittedPreprocessing]
    test: Optional[dict[str, Any]]
    logit: LogitFit
    stats: dict[str, int] = field(default_factory=dict)


class _FallInnerCache(_InnerCache):
    """`_InnerCache` arayüzü (folds(), computed) aynen; fark (J10 kuralı, SPEC_DEVIATIONS K): her iç kümede f3'ü o kümenin filtre
    moduna açıkça zıt olan arz kullanılmaz; tutulan arzın f3'ü iç kümenin moduyla boşalıyorsa o arz skorlanmaz (listeye girmez).
    f3 kullanmayan tarifte `_InnerCache` ile aynı iç bölmeler."""

    def __init__(self, order: Sequence[str], raw: Mapping[str, Mapping], status: Mapping[str, Optional[str]], recipe: pp.Recipe):
        super().__init__(order, raw, status, recipe)
        self.stats = {"inner_filter_excluded_n": 0, "inner_held_out_not_scored_n": 0}

    def folds(self) -> list[_InnerFold]:
        from .hazard import f3_filter_excluded

        if self._folds is None:
            folds = []
            uses_f3 = "f3" in self._recipe.substantive
            for held_out in self._order:
                inner_train = [t for t in self._order if t != held_out]
                excluded = set(f3_filter_excluded(inner_train, self._raw, self._status)) if uses_f3 else set()
                if excluded:
                    inner_train = [t for t in inner_train if t not in excluded]
                    self.stats["inner_filter_excluded_n"] += len(excluded)
                fitted = pp.fit_preprocessing({t: self._raw[t] for t in inner_train}, {t: self._status.get(t) for t in inner_train},
                                              recipe=self._recipe)
                if (not fitted.insufficient_feature_variation and uses_f3 and "f3" in fitted.active_after_missingness
                        and pp.opposite_explicit_status(self._status.get(held_out), fitted.f3_filter_mode_after)):
                    self.stats["inner_held_out_not_scored_n"] += 1
                    continue
                val = None if fitted.insufficient_feature_variation else fitted.transform(self._raw[held_out], self._status.get(held_out))
                folds.append(_InnerFold(held_out, inner_train, fitted, val))
            self._folds = folds
        return self._folds


def fall_grid(spec: Mapping[str, Any]) -> Optional[GridConfig]:
    """Şartnamenin logit bloğu: V1.6'nınkiyle aynıysa `V1_6_GRID`; C ızgarası yalnız ZERO ise kural satırı (None, kapalı biçim)."""
    logit = {k: v for k, v in spec["logit"].items() if k != "label"}
    if logit["C_grid"] == ["ZERO"]:
        return None
    grid = GridConfig("v1_6", V1_6_ALPHA_GRID, tuple(hp_parse(c) for c in logit["C_grid"]), logit["non_convergence_policy"],
                      FALLBACK_POLICY[logit["minority_lt_2_policy"]])
    if grid != V1_6_GRID:
        raise FitError(f"{spec['model_id']}: logit ızgarası V1.6 değil ({grid})")
    return grid


def fit_fall_horizon(
    order: Sequence[str],
    raw: Mapping[str, Mapping[str, Any]],
    Y: Mapping[str, int],
    filter_status: Mapping[str, Optional[str]],
    *,
    recipe: Optional[pp.Recipe],
    grid: Optional[GridConfig] = V1_6_GRID,
    test_raw: Optional[Mapping[str, Any]] = None,
    test_filter_status: Optional[str] = None,
) -> FallHorizonFit:
    """Bir ufuk (D5 ya da D10) için Ridge'siz L2-lojistik (SPEC_C_V0 §4). `order` eğitim satır sırasıdır; `Y` tablonun Y_h'si
    (1 = kapanış > arz). `recipe` None ise (`@ZERO`) p = eğitim oranı. Test arzının hedefi hiçbir argümanla verilemez."""
    order = list(order)
    if recipe is None or grid is None:
        n = len(order)
        y = [Y[t] for t in order]
        n1 = sum(y)
        counts = dict(n_class_0=n - n1, n_class_1=n1)
        if n < MIN_TRAIN_N:
            logit = LogitFit(status=STATUS_INSUFFICIENT_TRAINING_HISTORY, effective_n=n)
        elif n1 in (0, n):
            logit = LogitFit(status=STATUS_SINGLE_CLASS, effective_n=n, **counts)
        else:
            p = _finite(train_rate(y), "ZERO rate")
            logit = LogitFit(status=STATUS_FIT_OK, effective_n=n, selected_C=ZERO, tuning_status=TUNING_NOT_APPLICABLE, constant=p,
                             probability=None if test_raw is None else p,
                             predicted_class=None if test_raw is None else (1 if p > 0.5 else 0), **counts)
        return FallHorizonFit(order=tuple(order), excluded=(), final=None, test=None, logit=logit)
    from .hazard import f3_filter_excluded

    excluded = tuple(f3_filter_excluded(order, raw, filter_status)) if "f3" in recipe.substantive else ()
    used = [t for t in order if t not in set(excluded)]
    inner = _FallInnerCache(used, raw, filter_status, recipe)
    final = test = None
    if len(used) >= MIN_TRAIN_N:
        final = pp.fit_preprocessing({t: raw[t] for t in used}, {t: filter_status.get(t) for t in used}, recipe=recipe)
        if test_raw is not None and not final.insufficient_feature_variation:
            if ("f3" in final.active_after_missingness and test_raw.get("f3") is not None
                    and pp.opposite_explicit_status(test_filter_status, final.f3_filter_mode_after)):
                raise FitError(f"{STATUS_TEST_F3_FILTER_CONFLICT}: test arzının f3 filtre durumu eğitim moduna açıkça zıt "
                               "(tahminde RET; PLAN_FALL_* test arzları H99'dur, bu durum oluşmamalı)")
            test = final.transform(test_raw, test_filter_status)
    logit = _fit_logit(used, Y, inner, final, test, grid)
    stats = {"filter_excluded_n": len(excluded), "f3_filter_mode_ties_n": 0, **inner.stats}
    preps = ([f.fitted for f in inner.folds()] if inner.computed else []) + ([final] if final is not None else [])
    for p in preps:
        if p.f3_filter_nulled:
            raise FitError("f3 filtre adımı dışlamadan sonra arz boşalttı (J10 kuralı ihlali)")
        stats["f3_filter_mode_ties_n"] += int(p.f3_filter_mode_tie) + int(p.f3_filter_mode_after_tie)
    return FallHorizonFit(order=tuple(used), excluded=excluded, final=final, test=test, logit=logit, stats=stats)


def fall_head(hf: FallHorizonFit) -> dict[str, Any]:
    """Bir ufkun JSON başlığı (`horizons.D_h`): getiri başlığı yok; p_up V1.6 biçimi (C = ZERO seçilirse katsayılar 0, sabit
    ln(p/(1 − p)); kural satırında kind constant = eğitim oranı, bit-eşit)."""
    g = hf.logit
    if not hf.final and g.selected_C == ZERO and g.constant is not None and not g.columns:
        return {"return": None, "p_up": {"kind": "constant", "value": g.constant, "C": "ZERO", "rule": "n_1 / n (eğitim oranı)",
                                         "n_class_0": g.n_class_0, "n_class_1": g.n_class_1}}
    intercept, coef = g.intercept_coef()
    return {"return": None, "p_up": {
        "kind": "logit",
        "C": hp_label(g.selected_C, "C"),
        "intercept": intercept,
        "coef": coef,
        "columns": list(g.columns),
        "inner_loocv_brier": {_table_key(e.hyperparameter, "C"): e.score for e in g.score_table},
        "inner_loocv_status": {_table_key(e.hyperparameter, "C"): e.status for e in g.score_table},
        "inner_loocv_folds": g.inner_fold_n,
        "final_fit_attempts": [list(a) for a in g.final_attempts],
        "tuning_status": g.tuning_status,
        "n_class_0": g.n_class_0,
        "n_class_1": g.n_class_1,
    }}

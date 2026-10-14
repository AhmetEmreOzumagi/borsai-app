"""Part J — V1_RIDGE / V1_LOGIT candidate-model implementation (BORSAI_V1_5_PREREG_20260814).

This module performs NO historical fitting on its own: it is a pure, callable
implementation of the frozen V1.5 estimator/tuning contract, exercised only
against synthetic fixtures by tests/test_v1_5_candidate_models.py. Running it
against real FULL20-derived targets is a separate, still-gated task (V1.5
section 11 / CLAUDE.md section 10).

RUNTIME CONTRACT (V1.5 section 2, config/model_v1_5_spec.json
`candidate_model_runtime`): this module MUST run under the isolated
`.venv-v1_5-model` environment (python 3.12.13, scikit-learn 1.9.0, numpy
2.5.2, scipy 1.18.0, joblib 1.5.3, threadpoolctl 3.6.0), never under
`codex-primary-runtime` or system Python, which do not have scikit-learn
installed. To keep this module IMPORTABLE (but not USABLE) under a runtime
without scikit-learn -- so the existing sklearn-free test suite can still be
discovered and imported without crashing -- the sklearn-family imports below
are guarded; `verify_runtime()` (called at the top of every public entry
point) is what actually enforces the hard-fail-on-wrong-runtime requirement.

METHODOLOGY (frozen, not altered by this implementation task):
  - Ridge:    alpha in {0.1, 1.0, 10.0, 100.0}; fit_intercept=True; solver="svd";
              no target transform; inner-LOOCV tuning objective = mean absolute
              error (MAE) in native R_h space; tie -> largest alpha.
  - Logistic: C in {0.01, 0.1, 1.0, 10.0}; l1_ratio=0.0 (L2-equivalent, V1.5
              section 3.2 / section 9 -- NOT explicit penalty="l2", which is
              deprecated since sklearn 1.8 and removed in 1.10); solver="lbfgs";
              fit_intercept=True; class_weight=None; max_iter=10000; tol=1e-10;
              inner-LOOCV tuning objective = Brier score on raw unclipped
              P(y=1); tie -> smallest C. Degeneracy policy delegated verbatim
              to the existing scripts/modeling/logistic_policy.py (untouched).
  - Both:     inner LOOCV preprocessing is REFIT from raw rows on every inner
              training split (V1.5 section 6 / section 5 binding rule) -- the
              outer-training preprocessed matrix is never reused for tuning,
              and the outer test row is invisible throughout tuning. Ties are
              decided by bit-exact score equality only; no epsilon, no
              tolerance. All scores/predictions/probabilities must be finite;
              a non-finite value hard-fails via preprocessing's own
              NumericRepresentationIntegrityError, never repaired.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping, Optional, Sequence

from . import fold_engine as fe
from . import logistic_policy as lp
from . import preprocessing as pp
from .target_extraction import TargetRecord

# ---------------------------------------------------------------------------
# Guarded scikit-learn family import. Importing this module must NEVER crash
# just because scikit-learn is absent (so the existing sklearn-free test
# suite stays importable/discoverable under codex-primary-runtime); using any
# candidate-model function under the wrong runtime DOES hard-fail, via
# verify_runtime() below, called at the top of every public entry point.
# ---------------------------------------------------------------------------
_IMPORT_ERROR: Optional[BaseException] = None
try:
    import numpy as _np
    import scipy as _scipy
    import joblib as _joblib
    import threadpoolctl as _threadpoolctl
    import sklearn as _sklearn
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.exceptions import ConvergenceWarning
except ImportError as exc:  # pragma: no cover -- exercised under codex-primary-runtime only
    _IMPORT_ERROR = exc
    _np = _scipy = _joblib = _threadpoolctl = _sklearn = None  # type: ignore[assignment]
    Ridge = LogisticRegression = ConvergenceWarning = None  # type: ignore[assignment]


# Pinned exactly to artifacts/modeling/runtime/V1_5_RUNTIME_MANIFEST.json
# (resolved_dependencies_exact), which is itself governed by
# config/model_v1_5_spec.json `candidate_model_runtime`. A mismatch of ANY of
# these is a runtime-contract violation, not a warning.
EXPECTED_PYTHON_MAJOR_MINOR = (3, 12)
EXPECTED_SKLEARN_VERSION = "1.9.0"
EXPECTED_NUMPY_VERSION = "2.5.2"
EXPECTED_SCIPY_VERSION = "1.18.0"
EXPECTED_JOBLIB_VERSION = "1.5.3"
EXPECTED_THREADPOOLCTL_VERSION = "3.6.0"

# Frozen grids (V1.5 section 1 / section 12; config/model_v1_5_spec.json
# ridge.grid / logistic.grid). Ridge has no existing shared constant in this
# package; Logistic's grid/fallback are reused verbatim from the existing
# logistic_policy module (single source of truth, never restated/duplicated).
RIDGE_ALPHA_GRID: tuple[float, ...] = (0.1, 1.0, 10.0, 100.0)
LOGISTIC_C_GRID: tuple[float, ...] = lp.C_GRID

# MIN_TRAIN_N = 10 gates the effective OUTER candidate-training fold only
# (V1.5 section 13 / V1.4 section 7); inner LOOCV auxiliary fits at n-1 are
# never gated by this. Value frozen since V1.1 (fold_engine.plan_folds is
# parameterised by min_train_n at the call site, so this module restates the
# frozen project-wide value rather than importing a call-site parameter).
MIN_TRAIN_N = 10

MODEL_ID_RIDGE = "V1_RIDGE"
MODEL_ID_LOGIT = "V1_LOGIT"

STATUS_FIT_OK = "FIT_OK"
STATUS_INSUFFICIENT_TRAINING_HISTORY = fe.STATUS_INSUFFICIENT_TRAINING_HISTORY
STATUS_INSUFFICIENT_FEATURE_VARIATION = pp.STATUS_INSUFFICIENT_FEATURE_VARIATION
STATUS_MODEL_NOT_FIT_SINGLE_CLASS = lp.MODEL_NOT_FIT_SINGLE_CLASS

# New statuses closed by V1.4/V1.5 (config/model_v1_5_spec.json
# `fit_status_values_added_in_v1_4`, `inner_validation.insufficient_variation_policy`,
# `inner_validation.inner_single_class_policy`, `optimizer_non_convergence_policy`).
STATUS_MODEL_NOT_FIT_INNER_PREPROCESSING_INSUFFICIENT_VARIATION = "MODEL_NOT_FIT_INNER_PREPROCESSING_INSUFFICIENT_VARIATION"
STATUS_MODEL_NOT_FIT_INNER_SINGLE_CLASS = "MODEL_NOT_FIT_INNER_SINGLE_CLASS"
STATUS_MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE = "MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE"

TUNING_NOT_APPLICABLE = lp.TUNING_NOT_APPLICABLE
TUNING_SKIPPED_MINORITY_COUNT_LT_2 = lp.TUNING_SKIPPED_MINORITY_COUNT_LT_2
TUNED_INNER_LOOCV = lp.TUNED_INNER_LOOCV

SCORE_STATUS_SCORED = "SCORED"


class RuntimeContractMismatchError(RuntimeError):
    """config/model_v1_5_spec.json `candidate_model_runtime` / `setup_time_verification_requirements`.

    Raised when the executing interpreter does not satisfy the pinned V1.5
    candidate-model runtime contract. No fallback environment, no auto-install,
    no silent continuation under a mismatched runtime -- ever."""


def verify_runtime() -> None:
    """Hard-fail if this interpreter is not the pinned V1.5 candidate-model
    runtime. Called at the top of every public entry point in this module
    (never only at import time), so a caller cannot bypass the check by
    importing the module in one runtime and only later invoking it."""
    if _IMPORT_ERROR is not None:
        raise RuntimeContractMismatchError(
            "V1.5 candidate-model runtime contract violated: scikit-learn (or one of "
            "numpy/scipy/joblib/threadpoolctl) is not importable in this interpreter. "
            "Candidate-model code MUST run under the isolated .venv-v1_5-model "
            f"environment, never codex-primary-runtime or system Python. Original import error: {_IMPORT_ERROR!r}"
        ) from _IMPORT_ERROR

    import sys

    mismatches: list[str] = []
    if sys.version_info[:2] != EXPECTED_PYTHON_MAJOR_MINOR:
        mismatches.append(f"python major.minor: expected {EXPECTED_PYTHON_MAJOR_MINOR}, got {sys.version_info[:2]}")
    if _sklearn.__version__ != EXPECTED_SKLEARN_VERSION:
        mismatches.append(f"scikit-learn: expected {EXPECTED_SKLEARN_VERSION}, got {_sklearn.__version__}")
    if _np.__version__ != EXPECTED_NUMPY_VERSION:
        mismatches.append(f"numpy: expected {EXPECTED_NUMPY_VERSION}, got {_np.__version__}")
    if _scipy.__version__ != EXPECTED_SCIPY_VERSION:
        mismatches.append(f"scipy: expected {EXPECTED_SCIPY_VERSION}, got {_scipy.__version__}")
    if _joblib.__version__ != EXPECTED_JOBLIB_VERSION:
        mismatches.append(f"joblib: expected {EXPECTED_JOBLIB_VERSION}, got {_joblib.__version__}")
    if _threadpoolctl.__version__ != EXPECTED_THREADPOOLCTL_VERSION:
        mismatches.append(f"threadpoolctl: expected {EXPECTED_THREADPOOLCTL_VERSION}, got {_threadpoolctl.__version__}")

    if mismatches:
        raise RuntimeContractMismatchError(
            "V1.5 candidate-model runtime contract violated (no fallback, no auto-install, "
            "no silent continuation): " + "; ".join(mismatches)
        )


def _runtime_versions() -> dict[str, str]:
    return {
        "python": ".".join(str(p) for p in __import__("sys").version_info[:3]),
        "scikit-learn": _sklearn.__version__,
        "numpy": _np.__version__,
        "scipy": _scipy.__version__,
        "joblib": _joblib.__version__,
        "threadpoolctl": _threadpoolctl.__version__,
    }


# ---------------------------------------------------------------------------
# Shared result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScoreTableEntry:
    """One grid candidate's inner-LOOCV score (V1.5 section 15: `candidate_score_table`)."""
    hyperparameter: float
    score: Optional[float]
    fold_count: int
    status: str


@dataclass(frozen=True)
class RidgeCandidateResult:
    model_id: str = MODEL_ID_RIDGE
    status: str = STATUS_FIT_OK
    effective_outer_train_n: int = 0
    feature_names: tuple[str, ...] = ()
    selected_alpha: Optional[float] = None
    tuning_status: str = TUNING_NOT_APPLICABLE
    inner_fold_count: int = 0
    candidate_score_table: tuple[ScoreTableEntry, ...] = ()
    prediction: Optional[float] = None
    runtime_versions: dict = field(default_factory=dict)


@dataclass(frozen=True)
class LogisticCandidateResult:
    model_id: str = MODEL_ID_LOGIT
    status: str = STATUS_FIT_OK
    effective_outer_train_n: int = 0
    feature_names: tuple[str, ...] = ()
    selected_C: Optional[float] = None
    tuning_status: str = TUNING_NOT_APPLICABLE
    inner_fold_count: int = 0
    candidate_score_table: tuple[ScoreTableEntry, ...] = ()
    probability_positive_class: Optional[float] = None
    predicted_class: Optional[int] = None
    n_class_0: int = 0
    n_class_1: int = 0
    observed_fit_warnings: tuple[str, ...] = ()
    runtime_versions: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _require_finite(value: float, label: str) -> float:
    if not math.isfinite(value):
        raise pp.NumericRepresentationIntegrityError(
            f"NUMERIC_REPRESENTATION_INTEGRITY_ERROR: {label}={value!r} is not finite (candidate_models.py)"
        )
    return value


def _finite_brier_term(p1: float, y_val: float, *, model: str, c: float, held_out: str) -> float:
    """Brier term `(p - y)^2`, exactly V1.5's frozen formula -- no clipping,
    no scaling, no alternate formula. `_require_finite` alone is insufficient
    here: unlike `+`/`-`/`*`/`/` (which silently saturate to `inf` on
    overflow and are already caught by a post-hoc finite check), Python's
    `**` operator can RAISE `OverflowError` while COMPUTING its result, so an
    overflow inside the very expression passed to `_require_finite` never
    reaches it (independent audit
    artifacts/modeling/V1_5_CANDIDATE_MODEL_INDEPENDENT_AUDIT.md section 8/25:
    finite mock p1=1e308 with y=0 raised a raw OverflowError before
    `_require_finite` was ever entered). Each arithmetic step below is
    therefore individually boundary-checked -- an OverflowError raised while
    computing a step is normalized with the cause chained; a step that
    completes without raising but returns a non-finite value is caught by
    the existing `_require_finite` check. Narrow to this one call site
    (Ridge's abs/sum/divide and Logistic's own aggregation never raise --
    see the sibling audit in the accompanying fix report -- only squaring
    does), not a generic numeric framework."""
    try:
        diff = p1 - y_val
    except OverflowError as exc:
        raise pp.NumericRepresentationIntegrityError(
            f"NUMERIC_REPRESENTATION_INTEGRITY_ERROR: model={model} stage=BRIER_DIFFERENCE scope=INNER "
            f"C={c} inner_val={held_out} cause={type(exc).__name__}: {exc}"
        ) from exc
    diff = _require_finite(diff, f"C={c} inner_val={held_out} brier_difference")

    try:
        squared = diff ** 2
    except OverflowError as exc:
        raise pp.NumericRepresentationIntegrityError(
            f"NUMERIC_REPRESENTATION_INTEGRITY_ERROR: model={model} stage=BRIER_SQUARE scope=INNER "
            f"C={c} inner_val={held_out} cause={type(exc).__name__}: {exc}"
        ) from exc
    return _require_finite(squared, f"C={c} inner_val={held_out} brier_term")


def _inner_filter_status(
    outer_filter_status: Mapping[str, Optional[str]], inner_train_tickers: Sequence[str], held_out: str,
) -> dict[str, Optional[str]]:
    out: dict[str, Optional[str]] = {t: outer_filter_status.get(t) for t in inner_train_tickers}
    out["__test__"] = outer_filter_status.get(held_out)
    return out


def _columns_of(result: pp.FoldPreprocessingResult) -> list[str]:
    """V1.5 `determinism.feature_column_order`: active_substantive_features
    THEN active_indicator_features, in preprocess_fold's own return order."""
    return list(result.active_substantive_features) + list(result.active_indicator_features)


def _row_order(training_raw: Mapping[str, dict]) -> list[str]:
    """V1.5 `determinism.training_row_order`: the caller's own dict insertion
    order IS the row order (fold_engine's training_tickers is already sorted
    first_trading_date ASC / ticker ASC; this module does not re-sort, since
    it has no access to first_trading_date metadata -- callers MUST pass
    dicts already in that order)."""
    return list(training_raw.keys())


def _matrix(result: pp.FoldPreprocessingResult, row_order: Sequence[str], columns: Sequence[str]):
    return _np.array([[result.train_matrix[t][c] for c in columns] for t in row_order], dtype=_np.float64)


def _vector(values: Sequence[float]):
    return _np.array(values, dtype=_np.float64)


# ---------------------------------------------------------------------------
# RIDGE
# ---------------------------------------------------------------------------

def _ridge_inner_folds(
    outer_training_raw: Mapping[str, dict], outer_filter_status: Mapping[str, Optional[str]], outer_order: Sequence[str],
) -> Optional[list[tuple]]:
    """Precompute every inner LOOCV split's leakage-safe preprocessing ONCE
    (V1.5 section 6): each split is built from RAW outer-training rows, with
    V1.3 preprocessing fit strictly on that split's inner-training rows and
    applied to the held-out inner-validation row. Preprocessing has no
    dependence on the candidate hyperparameter, so precomputing once and
    reusing the same K prepared folds across every alpha in the grid is
    mathematically identical to (and only more efficient than) refitting
    preprocessing separately per (alpha, inner split) pair -- the leakage
    guarantee is unchanged either way, since it comes from which RAW rows
    each `preprocess_fold` call receives, not from how many times a
    numerically-identical result is recomputed.

    Returns None if any inner split hits INSUFFICIENT_FEATURE_VARIATION
    (caller must then emit the whole-outer-fold not-fit status)."""
    folds = []
    for held_out in outer_order:
        inner_train_tickers = [t for t in outer_order if t != held_out]
        inner_train_raw = {t: outer_training_raw[t] for t in inner_train_tickers}
        inner_val_raw = outer_training_raw[held_out]
        inner_status = _inner_filter_status(outer_filter_status, inner_train_tickers, held_out)
        result = pp.preprocess_fold(inner_train_raw, inner_val_raw, inner_status)
        if result.insufficient_feature_variation:
            return None
        folds.append((held_out, inner_train_tickers, result))
    return folds


def fit_ridge_candidate(
    outer_training_raw: Mapping[str, dict[str, Optional[Decimal]]],
    outer_training_targets: Mapping[str, TargetRecord],
    outer_test_raw: Mapping[str, Optional[Decimal]],
    outer_filter_status: Mapping[str, Optional[str]],
) -> RidgeCandidateResult:
    """V1_RIDGE (V1.5 sections 1-2, 5-7). Never accepts an outer-test target
    -- there is no parameter through which one could even be passed."""
    verify_runtime()

    outer_order = _row_order(outer_training_raw)
    n = len(outer_order)
    if n < MIN_TRAIN_N:
        return RidgeCandidateResult(status=STATUS_INSUFFICIENT_TRAINING_HISTORY, effective_outer_train_n=n)

    for t in outer_order:
        if outer_training_targets[t].R_h is None:
            raise ValueError(f"{t}: training target R_h is None; caller must supply only realized, available targets")
    outer_y = {t: _require_finite(float(outer_training_targets[t].R_h), f"{t}.R_h") for t in outer_order}

    inner_folds = _ridge_inner_folds(outer_training_raw, outer_filter_status, outer_order)
    if inner_folds is None:
        return RidgeCandidateResult(
            status=STATUS_MODEL_NOT_FIT_INNER_PREPROCESSING_INSUFFICIENT_VARIATION,
            effective_outer_train_n=n, inner_fold_count=n,
        )
    K = len(inner_folds)

    score_table: list[ScoreTableEntry] = []
    for alpha in RIDGE_ALPHA_GRID:
        abs_errors: list[float] = []
        for held_out, inner_train_tickers, result in inner_folds:
            columns = _columns_of(result)
            X_train = _matrix(result, inner_train_tickers, columns)
            y_train = _vector([outer_y[t] for t in inner_train_tickers])
            x_val = _vector([result.test_vector[c] for c in columns]).reshape(1, -1)
            ridge = Ridge(alpha=alpha, fit_intercept=True, solver="svd")
            ridge.fit(X_train, y_train)
            yhat = _require_finite(float(ridge.predict(x_val)[0]), f"alpha={alpha} inner_val={held_out} yhat")
            abs_errors.append(_require_finite(abs(outer_y[held_out] - yhat), f"alpha={alpha} inner_val={held_out} abs_error"))
        mae = _require_finite(sum(abs_errors) / len(abs_errors), f"alpha={alpha} MAE")
        score_table.append(ScoreTableEntry(hyperparameter=alpha, score=mae, fold_count=K, status=SCORE_STATUS_SCORED))

    best_score = min(entry.score for entry in score_table)
    tied = [entry for entry in score_table if entry.score == best_score]
    selected_alpha = max(entry.hyperparameter for entry in tied)  # tie -> largest alpha, bit-exact equality only

    final_result = pp.preprocess_fold(dict(outer_training_raw), dict(outer_test_raw), dict(outer_filter_status))
    if final_result.insufficient_feature_variation:
        return RidgeCandidateResult(
            status=STATUS_INSUFFICIENT_FEATURE_VARIATION, effective_outer_train_n=n,
            inner_fold_count=K, candidate_score_table=tuple(score_table),
        )
    final_columns = _columns_of(final_result)
    X_final = _matrix(final_result, outer_order, final_columns)
    y_final = _vector([outer_y[t] for t in outer_order])
    x_test = _vector([final_result.test_vector[c] for c in final_columns]).reshape(1, -1)

    final_ridge = Ridge(alpha=selected_alpha, fit_intercept=True, solver="svd")
    final_ridge.fit(X_final, y_final)
    prediction = _require_finite(float(final_ridge.predict(x_test)[0]), "final_prediction")

    return RidgeCandidateResult(
        status=STATUS_FIT_OK, effective_outer_train_n=n, feature_names=tuple(final_columns),
        selected_alpha=selected_alpha, tuning_status=TUNED_INNER_LOOCV, inner_fold_count=K,
        candidate_score_table=tuple(score_table), prediction=prediction, runtime_versions=_runtime_versions(),
    )


# ---------------------------------------------------------------------------
# LOGISTIC
# ---------------------------------------------------------------------------

def _positive_class_probability(classes_, proba_row) -> float:
    """Explicit `classes_` lookup for P(y=1) -- never a fixed column-position
    assumption (V1.5 section 3.2 / section 9, test L9)."""
    classes = list(classes_)
    idx = classes.index(1)
    return float(proba_row[idx])


def _fit_logistic_and_check_convergence(estimator, X, y) -> tuple[list, list[str]]:
    """Fit `estimator` and classify warnings raised during the real fit call.
    Isolated as its own function (not inlined) specifically so tests can
    monkeypatch it to simulate a convergence failure without needing to force
    LBFGS into genuine non-convergence on tiny synthetic data (V1.5 section 9,
    test L17)."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        estimator.fit(X, y)
    convergence = [w for w in caught if issubclass(w.category, ConvergenceWarning)]
    other = [str(w.message) for w in caught if not issubclass(w.category, ConvergenceWarning)]
    return convergence, other


def _logistic_inner_folds(
    outer_training_raw: Mapping[str, dict], outer_filter_status: Mapping[str, Optional[str]],
    outer_order: Sequence[str], outer_y: Mapping[str, int],
) -> tuple[Optional[list[tuple]], Optional[str]]:
    """Same precomputation pattern as `_ridge_inner_folds`, plus the explicit
    per-split class-presence verification V1.5 section 11 requires (outer
    minority>=2 mathematically guarantees every leave-one-out inner-training
    split retains both classes, but the implementation must verify this
    rather than assume it).

    Returns (folds, None) on success, or (None, status) on a whole-outer-fold
    not-fit condition."""
    folds = []
    for held_out in outer_order:
        inner_train_tickers = [t for t in outer_order if t != held_out]
        inner_train_raw = {t: outer_training_raw[t] for t in inner_train_tickers}
        inner_val_raw = outer_training_raw[held_out]
        inner_status = _inner_filter_status(outer_filter_status, inner_train_tickers, held_out)
        result = pp.preprocess_fold(inner_train_raw, inner_val_raw, inner_status)
        if result.insufficient_feature_variation:
            return None, STATUS_MODEL_NOT_FIT_INNER_PREPROCESSING_INSUFFICIENT_VARIATION
        inner_y = [outer_y[t] for t in inner_train_tickers]
        if len(set(inner_y)) < 2:
            return None, STATUS_MODEL_NOT_FIT_INNER_SINGLE_CLASS
        folds.append((held_out, inner_train_tickers, result, inner_y))
    return folds, None


def fit_logistic_candidate(
    outer_training_raw: Mapping[str, dict[str, Optional[Decimal]]],
    outer_training_targets: Mapping[str, TargetRecord],
    outer_test_raw: Mapping[str, Optional[Decimal]],
    outer_filter_status: Mapping[str, Optional[str]],
) -> LogisticCandidateResult:
    """V1_LOGIT (V1.5 sections 3, 4, 8-11). Never accepts an outer-test
    target. Degeneracy branching delegated verbatim to
    scripts/modeling/logistic_policy.py (untouched by this task)."""
    verify_runtime()

    outer_order = _row_order(outer_training_raw)
    n = len(outer_order)
    if n < MIN_TRAIN_N:
        return LogisticCandidateResult(status=STATUS_INSUFFICIENT_TRAINING_HISTORY, effective_outer_train_n=n)

    for t in outer_order:
        if outer_training_targets[t].Y_h is None:
            raise ValueError(f"{t}: training target Y_h is None; caller must supply only realized, available targets")
    outer_y: dict[str, int] = {t: int(outer_training_targets[t].Y_h) for t in outer_order}
    training_y_seq = [outer_y[t] for t in outer_order]

    decision = lp.decide_logistic_fit(training_y_seq)

    if decision.fit_status == lp.MODEL_NOT_FIT_SINGLE_CLASS:
        # No LogisticRegression.fit() call anywhere on this path.
        return LogisticCandidateResult(
            status=STATUS_MODEL_NOT_FIT_SINGLE_CLASS, effective_outer_train_n=n,
            tuning_status=decision.tuning_status, n_class_0=decision.n_class_0, n_class_1=decision.n_class_1,
        )

    score_table: tuple[ScoreTableEntry, ...] = ()
    inner_fold_count = 0

    if decision.tuning_status == lp.TUNING_SKIPPED_MINORITY_COUNT_LT_2:
        selected_C = decision.fallback_C
        tuning_status = lp.TUNING_SKIPPED_MINORITY_COUNT_LT_2
    else:
        inner_folds, failure_status = _logistic_inner_folds(outer_training_raw, outer_filter_status, outer_order, outer_y)
        if inner_folds is None:
            return LogisticCandidateResult(
                status=failure_status, effective_outer_train_n=n, inner_fold_count=n,
                n_class_0=decision.n_class_0, n_class_1=decision.n_class_1,
            )
        K = len(inner_folds)

        table: list[ScoreTableEntry] = []
        for C in LOGISTIC_C_GRID:
            brier_terms: list[float] = []
            for held_out, inner_train_tickers, result, inner_y in inner_folds:
                columns = _columns_of(result)
                X_train = _matrix(result, inner_train_tickers, columns)
                y_train = _vector(inner_y)
                x_val = _vector([result.test_vector[c] for c in columns]).reshape(1, -1)
                clf = LogisticRegression(
                    C=C, l1_ratio=0.0, solver="lbfgs", fit_intercept=True,
                    class_weight=None, max_iter=10000, tol=1e-10,
                )
                convergence, _other = _fit_logistic_and_check_convergence(clf, X_train, y_train)
                if convergence:
                    return LogisticCandidateResult(
                        status=STATUS_MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE, effective_outer_train_n=n,
                        inner_fold_count=K, n_class_0=decision.n_class_0, n_class_1=decision.n_class_1,
                    )
                proba_row = clf.predict_proba(x_val)[0]
                p1 = _require_finite(
                    _positive_class_probability(clf.classes_, proba_row), f"C={C} inner_val={held_out} p1"
                )
                y_val = outer_y[held_out]
                brier_terms.append(_finite_brier_term(p1, y_val, model=MODEL_ID_LOGIT, c=C, held_out=held_out))
            brier = _require_finite(sum(brier_terms) / len(brier_terms), f"C={C} Brier")
            table.append(ScoreTableEntry(hyperparameter=C, score=brier, fold_count=K, status=SCORE_STATUS_SCORED))

        best_score = min(entry.score for entry in table)
        tied = [entry for entry in table if entry.score == best_score]
        selected_C = min(entry.hyperparameter for entry in tied)  # tie -> smallest C, bit-exact equality only
        tuning_status = lp.TUNED_INNER_LOOCV
        score_table = tuple(table)
        inner_fold_count = K

    final_result = pp.preprocess_fold(dict(outer_training_raw), dict(outer_test_raw), dict(outer_filter_status))
    if final_result.insufficient_feature_variation:
        return LogisticCandidateResult(
            status=STATUS_INSUFFICIENT_FEATURE_VARIATION, effective_outer_train_n=n,
            selected_C=selected_C, tuning_status=tuning_status, inner_fold_count=inner_fold_count,
            candidate_score_table=score_table, n_class_0=decision.n_class_0, n_class_1=decision.n_class_1,
        )
    final_columns = _columns_of(final_result)
    X_final = _matrix(final_result, outer_order, final_columns)
    y_final = _vector(training_y_seq)
    x_test = _vector([final_result.test_vector[c] for c in final_columns]).reshape(1, -1)

    final_clf = LogisticRegression(
        C=selected_C, l1_ratio=0.0, solver="lbfgs", fit_intercept=True,
        class_weight=None, max_iter=10000, tol=1e-10,
    )
    convergence, other_warnings = _fit_logistic_and_check_convergence(final_clf, X_final, y_final)
    if convergence:
        return LogisticCandidateResult(
            status=STATUS_MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE, effective_outer_train_n=n,
            selected_C=selected_C, tuning_status=tuning_status, inner_fold_count=inner_fold_count,
            candidate_score_table=score_table, n_class_0=decision.n_class_0, n_class_1=decision.n_class_1,
        )

    proba_row = final_clf.predict_proba(x_test)[0]
    p1 = _require_finite(_positive_class_probability(final_clf.classes_, proba_row), "final p1")
    predicted_class = 1 if p1 > 0.5 else 0  # exact 0.5 -> 0 (V1.5 section 3.3 / section 9)

    return LogisticCandidateResult(
        status=STATUS_FIT_OK, effective_outer_train_n=n, feature_names=tuple(final_columns),
        selected_C=selected_C, tuning_status=tuning_status, inner_fold_count=inner_fold_count,
        candidate_score_table=score_table, probability_positive_class=p1, predicted_class=predicted_class,
        n_class_0=decision.n_class_0, n_class_1=decision.n_class_1,
        observed_fit_warnings=tuple(other_warnings), runtime_versions=_runtime_versions(),
    )

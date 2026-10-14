"""Part E — the V1.3 11-step fold-internal preprocessing pipeline.

This module is built and unit-tested standalone. It is NOT wired into the
baseline harness execution path in this task, because V1_BASE_* baselines are
computed purely from the training-fold TARGET distribution and consume no
features at all (V1.1 preregistration Section 7.1). It exists so that (a) it is
ready for the future Ridge/Logit implementation task, and (b) its behavior --
drops, zero-variance handling, bound computation -- can be verified against
the real fold data produced by fold_engine.py, independent of whether a model
is ever fit on top of it.

Step order (config/model_v1_3_spec.json `preprocessing_order_unchanged.steps`,
unchanged from V1.1/V1.2):
  1. feature eligibility / comparability filter         (already applied upstream + f3 comparability here)
  2. missingness determination                            TRAINING FOLD ONLY
  3. deterministic fold-drop if missing > 40%              TRAINING FOLD ONLY
  4. winsorization bounds (p05/p95), remaining non-missing TRAINING FOLD ONLY
  5. training-fold median imputation                       TRAINING FOLD ONLY
  6. missingness indicator (f5, bound to f3)
  7. preregistered transform (log f1)                      MODEL NUMERIC, never structural
  8. zero-variance check                                    TRAINING FOLD ONLY, EXACT, f1 on PRE-LOG values
  9. standardization (z-score), fit on train, applied to test  FEATURE-AWARE (see below)
 10. fit model                                              (out of scope here)
 11. apply train parameters to test row, predict            (out of scope here)

TWO ARITHMETIC LAYERS (config/model_v1_3_spec.json `structural_numeric_domain`,
`standardization`), enforced here by construction, not merely by comment:

  STRUCTURAL layer -- steps 1-6, 8, and the f3/f5 co-drop -- runs entirely in
  `fractions.Fraction`, an exact rational type. Every source value is a finite
  decimal literal (parsed upstream via common.parse_exact_decimal, never
  through a binary float), and `Fraction(Decimal(...))` converts it losslessly.
  All structural arithmetic -- comparison, ordering, Type-7 interpolation,
  clamping, median averaging, missingness/drop counting, zero-variance
  distinctness -- is EXACT and precision-independent: no fixed-precision
  Decimal context and no binary float ever participates in a structural
  decision. In particular, per V1.3 Section 1/Section 5, f1's zero-variance
  decision is made on the EXACT PRE-LOG Fraction values (log is injective on
  x>0, so this is mathematically equivalent to a post-log decision and
  requires no logarithm evaluation at all).

  MODEL NUMERIC layer -- step 7 (log), and step 9's std/z for every feature,
  plus f1's mean/variance (irrational post-log moments) -- runs in a frozen
  Decimal context (60 significant digits, ROUND_HALF_EVEN; see
  MODEL_NUMERIC_PRECISION below). This layer is NOT claimed exact: `ln` and
  `sqrt` are irrational in general. For the identity features f2/f3/f4/f5,
  whose transform is the identity, mean and population variance ARE exact
  rational (V1.3 Section 3) because no irrational operation intervenes before
  them; only their std (a square root) and z (a division) enter the model
  numeric layer. Binary64 conversion happens exactly once, after
  standardization is complete, and is followed by the I1-I4 numeric-integrity
  invariants (config/model_v1_3_spec.json `model_numeric_representation`),
  replacing the prior implementation's narrower "whole column collapsed to a
  single float" guard with genuine per-feature distinctness-preservation
  (I3), which also catches partial collisions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, Overflow, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from typing import Optional

# Frozen, deterministic precision for the MODEL NUMERIC layer only (step 7's
# log transform; step 9's std/z for every feature; f1's post-log mean and
# variance). This number never participates in, and never determines, any
# STRUCTURAL decision (missingness, fold-drop, winsorization bounds, median,
# zero-variance, co-drop) -- those are computed in exact `Fraction` arithmetic
# and are therefore precision-independent by construction. Per V1.3 Section
# 8/Section 9, this value is a representation parameter only; changing it must
# never change a structural decision (tests/test_v1_1_baseline_harness.py
# `PreprocessingTests.test_K_*` exercises this as an explicit structural-
# invariance check, using a non-default precision passed only to that test,
# never to production code).
MODEL_NUMERIC_PRECISION = 60

SUBSTANTIVE_FEATURES = ("f1", "f2", "f3", "f4")
MISSINGNESS_FOLD_DROP_THRESHOLD_PCT = 40  # strictly greater-than
WINSORIZE_FEATURES = ("f3",)
LOG_TRANSFORM_FEATURES = ("f1",)

STATUS_MISSINGNESS_FOLD_DROP = "MISSINGNESS_FOLD_DROP"
STATUS_ZERO_VARIANCE_FOLD_DROP = "ZERO_VARIANCE_FOLD_DROP"
STATUS_INSUFFICIENT_FEATURE_VARIATION = "INSUFFICIENT_FEATURE_VARIATION"


class NonPositiveLogInputError(ValueError):
    """f1 (ipo_size_tl) must be strictly positive; a non-positive value is a
    data/integrity error and must raise, never be silently clipped
    (V1.1 Section 5.6, carried unchanged through V1.3)."""
    pass


class NumericRepresentationIntegrityError(RuntimeError):
    """config/model_v1_3_spec.json `numeric_integrity.status` =
    NUMERIC_REPRESENTATION_INTEGRITY_ERROR.

    Raised when a structurally ACTIVE feature fails one of the I1-I4 numeric
    integrity invariants at the MODEL NUMERIC layer or the Decimal->binary64
    boundary. This is an accepted safety boundary, not a model result: no
    epsilon, no tolerance, no rounding repair, no silent drop, and no
    precision change in response to this failure are ever permitted as a fix
    (V1.3 Section 5, Section 9)."""
    pass


# The specific, narrow set of exception classes that can legitimately arise
# from a magnitude the MODEL NUMERIC representation layer cannot hold --
# Decimal-context overflow, an invalid decimal operation (e.g. from an
# exponent that cannot be represented at all), and division-by-zero at the
# representation boundary. This is deliberately NOT `except Exception`: any
# other exception (a programming error, a KeyError, a TypeError, ...) must
# keep propagating unchanged. Python's default-constructed `decimal.Context`
# traps exactly these three decimal exception classes (Overflow,
# InvalidOperation, DivisionByZero); `OverflowError` is the separate built-in
# raised by `float(Decimal)` / `float(Fraction)` on magnitude overflow.
_NUMERIC_REPRESENTATION_FAILURE_TYPES = (OverflowError, Overflow, InvalidOperation, DivisionByZero)


def _numeric_representation_failure(
    exc: Exception, *, feature: str, stage: str, scope: str
) -> NumericRepresentationIntegrityError:
    """Build a `NumericRepresentationIntegrityError` carrying which feature,
    which MODEL NUMERIC stage, and which scope (TRAIN/TEST/REPORTING) failed,
    with the original exception preserved via `raise ... from exc` at every
    call site (config/model_v1_3_spec.json `numeric_integrity`: hard fail,
    never epsilon/tolerance/rounding/silent-drop; never a model result)."""
    return NumericRepresentationIntegrityError(
        f"NUMERIC_REPRESENTATION_INTEGRITY_ERROR: feature={feature} stage={stage} scope={scope} "
        f"cause={type(exc).__name__}: {exc}"
    )


def quantile_linear(sorted_values: list[float], p: float) -> float:
    """R type 7 / numpy 'linear' quantile -- order-statistic interpolation.

    h = (n-1)*p + 1 (1-based); Q = x[lo] + frac*(x[lo+1]-x[lo]).
    Float reference implementation kept for reporting/back-compat only; no
    structural decision may use it (see `_fraction_quantile_linear` below).
    """
    n = len(sorted_values)
    if n == 0:
        raise ValueError("quantile_linear called with empty input")
    if n == 1:
        return sorted_values[0]
    h = (n - 1) * p + 1
    lo = math.floor(h)
    frac = h - lo
    lo_idx = lo - 1  # convert 1-based to 0-based
    if lo == n:
        return sorted_values[lo_idx]
    return sorted_values[lo_idx] + frac * (sorted_values[lo_idx + 1] - sorted_values[lo_idx])


def _fraction_quantile_linear(sorted_values: list[Fraction], p: Fraction) -> Fraction:
    """STRUCTURAL Type-7 quantile in exact rational arithmetic.

    Identical mathematical definition as `quantile_linear` above (h = (n-1)*p
    + 1, floor/frac interpolation between order statistics -- V1.3
    `winsorization.quantile_formula_1_based`), executed entirely in
    `Fraction` so the result is exact and precision-independent: no fixed
    Decimal context, no float, no rounding anywhere in this function.
    """
    n = len(sorted_values)
    if n == 0:
        raise ValueError("_fraction_quantile_linear called with empty input")
    if n == 1:
        return sorted_values[0]
    h = (Fraction(n - 1) * p) + 1
    lo = h.numerator // h.denominator  # exact floor for a non-negative Fraction
    frac = h - lo
    lo_idx = lo - 1
    if lo == n:
        return sorted_values[lo_idx]
    return sorted_values[lo_idx] + frac * (sorted_values[lo_idx + 1] - sorted_values[lo_idx])


def _fraction_median(values: list[Fraction]) -> Fraction:
    """STRUCTURAL exact-rational median -- odd n: middle exact value; even n:
    (a+b)/2 exact rational (V1.3 Section 4). No float, no Decimal rounding."""
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _fraction_clamp(value: Fraction, lo: Fraction, hi: Fraction) -> Fraction:
    return min(max(value, lo), hi)


def _missing_fraction_exceeds_threshold(
    missing: int, n_train: int, threshold_pct: int = MISSINGNESS_FOLD_DROP_THRESHOLD_PCT
) -> bool:
    """STRUCTURAL missingness/fold-drop decision (config/model_v1_3_spec.json
    `preprocessing.fold_drop_comparison = STRICTLY_GREATER_THAN`): True iff
    `missing / n_train` is STRICTLY greater than `threshold_pct / 100`,
    decided by exact `Fraction` cross-multiplication -- never a binary float.
    Exactly at the threshold (e.g. 2/5 or 4/10) compares equal, never
    greater, so it is correctly NOT a drop.

    Extracted as a standalone pure function (rather than left inline) so its
    exactness is directly testable at arbitrary `n_train` magnitude without
    needing to construct a training fold of that literal size -- this is
    what a binary-float `100.0 * missing / n_train > threshold_pct` computation
    gets wrong once `n_train` exceeds `2**53` (float64's exact-integer limit),
    even though the decision is unaffected for any realistic canonical fold
    size, which is exactly why the defect could hide in review."""
    return Fraction(missing, n_train) > Fraction(threshold_pct, 100)


def _fraction_mean(values: list[Fraction]) -> Fraction:
    """STRUCTURAL exact-rational mean, ddof = 0 (V1.3 `standardization`:
    identity_features.mean_arithmetic = EXACT_RATIONAL). No float, no Decimal
    rounding -- summation and division by the integer count `n` are both
    exact in `Fraction`."""
    return sum(values, Fraction(0)) / len(values)


def _fraction_population_variance(values: list[Fraction], mean: Fraction) -> Fraction:
    """STRUCTURAL exact-rational population variance, ddof = 0 (V1.3
    `standardization`: identity_features.variance_arithmetic = EXACT_RATIONAL).
    `mean` must be the exact mean of `values` (from `_fraction_mean`); passed
    in rather than recomputed so callers that already have it avoid a second
    pass, and so this function's exactness is trivially auditable in
    isolation."""
    return sum(((v - mean) ** 2 for v in values), Fraction(0)) / len(values)


def _to_fraction(value: Decimal) -> Fraction:
    """Lossless Decimal -> Fraction conversion (the sole, one-time entry point
    from the source's finite-decimal literals into the exact structural
    domain)."""
    return Fraction(value)


def _model_numeric_context(precision: int = MODEL_NUMERIC_PRECISION) -> Context:
    """The single construction point for the MODEL NUMERIC Decimal context
    (V1.3 `model_numeric_representation.evaluation_context`): frozen at 60
    significant digits, ROUND_HALF_EVEN, in production. A representation
    parameter only -- it never defines structural exactness and never
    determines a structural decision (see `preprocess_fold`'s
    `model_numeric_precision` argument, which exists solely so a test can
    verify that changing this value changes numeric representation but no
    structural decision)."""
    return Context(prec=precision, rounding=ROUND_HALF_EVEN)


def _fraction_to_model_decimal(value: Fraction, ctx, *, feature: str, stage: str = "FRACTION_TO_DECIMAL", scope: str = "REPORTING") -> Decimal:
    """Convert an exact Fraction into the MODEL NUMERIC Decimal domain, at the
    frozen context's precision. This is the boundary where exactness is
    deliberately given up in exchange for a usable finite representation
    (V1.3 Section 9.2: "does NOT claim log/sqrt evaluation is exact").

    A magnitude the context cannot represent at all raises a normalized
    `NumericRepresentationIntegrityError` (never a raw `decimal.Overflow`),
    with the original exception preserved via chaining."""
    try:
        with localcontext(ctx):
            return Decimal(value.numerator) / Decimal(value.denominator)
    except _NUMERIC_REPRESENTATION_FAILURE_TYPES as exc:
        raise _numeric_representation_failure(exc, feature=feature, stage=stage, scope=scope) from exc


def _model_ln(value: Decimal, ctx, *, feature: str, scope: str) -> Decimal:
    """MODEL NUMERIC natural log, at the frozen context's precision, with
    overflow/invalid-operation normalized to `NumericRepresentationIntegrityError`."""
    try:
        with localcontext(ctx):
            return value.ln()
    except _NUMERIC_REPRESENTATION_FAILURE_TYPES as exc:
        raise _numeric_representation_failure(exc, feature=feature, stage="LOG", scope=scope) from exc


def _model_sqrt(value: Decimal, ctx, *, feature: str, scope: str) -> Decimal:
    """MODEL NUMERIC square root, at the frozen context's precision, with
    overflow/invalid-operation normalized to `NumericRepresentationIntegrityError`."""
    try:
        with localcontext(ctx):
            return value.sqrt()
    except _NUMERIC_REPRESENTATION_FAILURE_TYPES as exc:
        raise _numeric_representation_failure(exc, feature=feature, stage="SQRT", scope=scope) from exc


def _model_sum(values, ctx, *, feature: str, stage: str, scope: str) -> Decimal:
    """MODEL NUMERIC summation (used for f1's post-log mean/variance), at the
    frozen context's precision, with overflow normalized to
    `NumericRepresentationIntegrityError`."""
    try:
        with localcontext(ctx):
            return sum(values, Decimal(0))
    except _NUMERIC_REPRESENTATION_FAILURE_TYPES as exc:
        raise _numeric_representation_failure(exc, feature=feature, stage=stage, scope=scope) from exc


def _model_divide(numerator: Decimal, denominator: Decimal, ctx, *, feature: str, stage: str, scope: str) -> Decimal:
    """MODEL NUMERIC division (used for both the plain n-division in
    mean/variance and the final z-score division), at the frozen context's
    precision, with overflow/division-by-zero normalized to
    `NumericRepresentationIntegrityError`."""
    try:
        with localcontext(ctx):
            return numerator / denominator
    except _NUMERIC_REPRESENTATION_FAILURE_TYPES as exc:
        raise _numeric_representation_failure(exc, feature=feature, stage=stage, scope=scope) from exc


def _to_float(value, *, feature: str, stage: str, scope: str) -> float:
    """Decimal/Fraction -> binary64 conversion, with magnitude overflow
    normalized to `NumericRepresentationIntegrityError` instead of a raw
    `OverflowError` -- covers both model-facing standardized values and
    audit-only reporting metadata (winsorization bounds, training medians,
    standardization mean/std) alike, since V1.3's safety boundary applies to
    representation failures generally, not only to the final estimator
    matrix.

    Two distinct failure shapes must both normalize to the same defined
    status: `float(Fraction)` raises `OverflowError` on magnitude overflow
    (caught below, cause chained), but `float(Decimal)` does NOT raise --
    IEEE-754 overflow-to-infinity conversion returns `inf`/`-inf` silently
    (and a `Decimal('NaN')` would silently return `nan`), regardless of the
    Decimal context's own trap settings, since the Decimal->float boundary is
    plain Python float-construction machinery, not a decimal-context
    operation. A successful-but-non-finite conversion is therefore checked
    explicitly here; there is no exception to chain in that case, which is
    expected (`NumericRepresentationIntegrityError.__cause__` stays `None`)."""
    try:
        result = float(value)
    except _NUMERIC_REPRESENTATION_FAILURE_TYPES as exc:
        raise _numeric_representation_failure(exc, feature=feature, stage=stage, scope=scope) from exc
    if not math.isfinite(result):
        raise NumericRepresentationIntegrityError(
            f"NUMERIC_REPRESENTATION_INTEGRITY_ERROR: feature={feature} stage={stage} scope={scope} "
            f"cause=NON_FINITE_CONVERSION_WITHOUT_EXCEPTION: float({value!r}) produced {result!r}"
        )
    return result


def _require_finite_decimal(value: Decimal, label: str) -> Decimal:
    if not value.is_finite():
        raise NumericRepresentationIntegrityError(
            f"I1_FINITE violated: {label}={value!r} is not finite"
        )
    return value


def _opposite_explicit_status(a: Optional[str], b: Optional[str]) -> bool:
    explicit = {"FILTERED", "UNFILTERED"}
    return a in explicit and b in explicit and a != b


def apply_f3_comparability_filter(
    training_f3: dict[str, Optional[Decimal]],
    filter_status: dict[str, Optional[str]],
) -> tuple[dict[str, Optional[Decimal]], list[str]]:
    """Training-fold-only modal filter-status rule (V1.1 Section 3.2 /
    preregistration Section 3.4). Unchanged by V1.3 -- this is a structural
    eligibility decision made on categorical status strings, not a numeric
    arithmetic domain.

    Returns the (possibly nulled-out) f3 values and the list of tickers whose
    value was nulled because their status opposed the training-fold mode.
    """
    statuses = [filter_status.get(t) for t, v in training_f3.items() if v is not None]
    usable_statuses = [s for s in statuses if s is not None]
    if not usable_statuses:
        return dict(training_f3), []
    mode = max(set(usable_statuses), key=usable_statuses.count)
    out: dict[str, Optional[Decimal]] = dict(training_f3)
    nulled: list[str] = []
    for ticker, value in training_f3.items():
        if value is None:
            continue
        status = filter_status.get(ticker)
        if _opposite_explicit_status(status, mode):
            out[ticker] = None
            nulled.append(ticker)
    return out, nulled


@dataclass
class FoldPreprocessingResult:
    active_substantive_features: list[str] = field(default_factory=list)
    active_indicator_features: list[str] = field(default_factory=list)
    dropped_features: dict[str, str] = field(default_factory=dict)  # feature_id -> status
    f3_comparability_nulled_tickers: list[str] = field(default_factory=list)
    winsor_bounds: dict[str, tuple[float, float]] = field(default_factory=dict)
    training_medians: dict[str, float] = field(default_factory=dict)
    standardization: dict[str, tuple[float, float]] = field(default_factory=dict)  # feature_id -> (mean, std)
    insufficient_feature_variation: bool = False
    train_matrix: dict[str, dict[str, float]] = field(default_factory=dict)  # ticker -> {feature: standardized value}
    test_vector: dict[str, float] = field(default_factory=dict)


def preprocess_fold(
    training_raw: dict[str, dict[str, Optional[Decimal]]],
    test_raw: dict[str, Optional[Decimal]],
    filter_status: dict[str, Optional[str]],
    *,
    model_numeric_precision: int = MODEL_NUMERIC_PRECISION,
) -> FoldPreprocessingResult:
    """training_raw: ticker -> {f1..f4: Decimal|None} for the training fold only.
    test_raw: {f1..f4: Decimal|None} for the single held-out test observation.
    filter_status: ticker -> total_demand_filter_status (training + test tickers).
    model_numeric_precision: MODEL NUMERIC layer precision. Defaults to the
        frozen production value (MODEL_NUMERIC_PRECISION = 60). Exposed as a
        parameter SOLELY so tests can verify structural invariance under a
        different precision (V1.3 requirement K); production call sites must
        never override it.
    """
    result = FoldPreprocessingResult()
    n_train = len(training_raw)
    if n_train == 0:
        raise ValueError("preprocess_fold called with an empty training fold")

    ctx = _model_numeric_context(model_numeric_precision)

    # Step 1 (f3 comparability): fold-internal modal-status filter.
    training_f3 = {t: vals.get("f3") for t, vals in training_raw.items()}
    training_f3_filtered, nulled = apply_f3_comparability_filter(training_f3, filter_status)
    result.f3_comparability_nulled_tickers = nulled

    working: dict[str, dict[str, Optional[Decimal]]] = {
        t: dict(vals) for t, vals in training_raw.items()
    }
    for t in working:
        working[t]["f3"] = training_f3_filtered[t]

    # Step 2 + 3: missingness determination (training-fold only) + >40% drop.
    # STRUCTURAL decision -- see `_missing_fraction_exceeds_threshold`: exact
    # Fraction comparison, never a binary float.
    active = list(SUBSTANTIVE_FEATURES)
    for feature_id in SUBSTANTIVE_FEATURES:
        missing = sum(1 for t in working if working[t].get(feature_id) is None)
        if _missing_fraction_exceeds_threshold(missing, n_train):
            active.remove(feature_id)
            result.dropped_features[feature_id] = STATUS_MISSINGNESS_FOLD_DROP

    # f5 is only ever CREATED when f3 survived missingness-drop (step 3).
    # Whether it ultimately SURVIVES the fold is decided later, once and for
    # all, by the unconditional co-drop enforcement after step 8 -- which also
    # covers f3 being removed there (e.g. by zero-variance).
    create_f5 = "f3" in active

    # =========================================================================
    # STRUCTURAL layer (steps 4-6, 8, co-drop): exact Fraction arithmetic only.
    # No fixed-precision Decimal context, no binary float, no epsilon, no
    # tolerance, no rounding anywhere below until explicitly entering the
    # MODEL NUMERIC layer (step 7's log, and step 9's std/z).
    # =========================================================================
    p05, p95 = Fraction(1, 20), Fraction(19, 20)

    # Step 4: winsorization bounds (exact Fraction Type-7 quantile; f3 only).
    winsor_bounds_frac: dict[str, tuple[Fraction, Fraction]] = {}
    winsorized: dict[str, dict[str, Optional[Fraction]]] = {t: {} for t in working}
    for feature_id in active:
        raw_vals = {t: _to_fraction(working[t][feature_id]) for t in working if working[t].get(feature_id) is not None}
        if feature_id in WINSORIZE_FEATURES and raw_vals:
            ordered = sorted(raw_vals.values())
            lo_frac = _fraction_quantile_linear(ordered, p05)
            hi_frac = _fraction_quantile_linear(ordered, p95)
            winsor_bounds_frac[feature_id] = (lo_frac, hi_frac)
            result.winsor_bounds[feature_id] = (
                _to_float(lo_frac, feature=feature_id, stage="WINSOR_BOUND_LO", scope="REPORTING"),
                _to_float(hi_frac, feature=feature_id, stage="WINSOR_BOUND_HI", scope="REPORTING"),
            )  # reporting only; never re-enters a decision
            for t, v in raw_vals.items():
                winsorized[t][feature_id] = _fraction_clamp(v, lo_frac, hi_frac)
            for t in working:
                if working[t].get(feature_id) is None:
                    winsorized[t][feature_id] = None
        else:
            for t in working:
                v = working[t].get(feature_id)
                winsorized[t][feature_id] = _to_fraction(v) if v is not None else None

    # Step 5: training-fold median imputation (exact Fraction, on winsorized values).
    imputed: dict[str, dict[str, Fraction]] = {t: {} for t in working}
    missingness_flags: dict[str, bool] = {t: False for t in working}
    training_medians_frac: dict[str, Fraction] = {}
    for feature_id in active:
        present = [winsorized[t][feature_id] for t in working if winsorized[t].get(feature_id) is not None]
        median_frac = _fraction_median(present) if present else None
        if median_frac is not None:
            training_medians_frac[feature_id] = median_frac
            result.training_medians[feature_id] = _to_float(
                median_frac, feature=feature_id, stage="TRAINING_MEDIAN", scope="REPORTING"
            )  # reporting only
        for t in working:
            v = winsorized[t][feature_id]
            if v is None:
                if median_frac is None:
                    raise ValueError(f"feature {feature_id} has no non-missing training values to impute from")
                imputed[t][feature_id] = median_frac
                if feature_id == "f3":
                    missingness_flags[t] = True
            else:
                imputed[t][feature_id] = v

    # Step 6: missingness indicator f5 (exact binary {0,1}, bound to f3).
    # Whether it ultimately SURVIVES the fold is decided solely by the
    # unconditional co-drop enforcement after step 8 below.
    if create_f5:
        result.active_indicator_features.append("f5")
        for t in working:
            imputed[t]["f5"] = Fraction(1) if missingness_flags[t] else Fraction(0)

    # `imputed` now holds the EXACT STRUCTURAL values for every active column,
    # including f1's exact PRE-LOG values. This dict is the single source of
    # truth for step 8's zero-variance decision (f1 included) and is never
    # itself replaced by a transformed value.
    exact_structural = imputed

    # Data-integrity precondition for the log transform: f1 must be strictly
    # positive for every training row. This is an EXACT Fraction comparison
    # against 0 -- not a model-numeric operation, no logarithm is evaluated
    # here -- so it belongs to the structural layer and is checked
    # unconditionally for every row with f1 still `active`, regardless of
    # whether f1 later survives step 8's zero-variance check (V1.1 Section
    # 5.6 / V1.3 `log_transform_non_positive_action = RAISE_DATA_ERROR_NEVER_CLIP`,
    # unchanged). This must NOT be confused with step 7's actual `ln()`
    # evaluation, which is deferred below until structural completion.
    for feature_id in LOG_TRANSFORM_FEATURES:
        if feature_id not in active:
            continue
        for t in working:
            v = exact_structural[t][feature_id]
            if v <= 0:
                raise NonPositiveLogInputError(f"{t}.{feature_id}={v} is non-positive; cannot log-transform")

    # Step 8: zero-variance check (training-fold only) -- EXACT Fraction
    # comparison. f1 uses its exact PRE-LOG values (log injectivity on x>0
    # makes this equivalent to a post-log decision without evaluating any
    # logarithm here); f2/f3/f4/f5 use their exact post-structural values.
    # No tolerance, no rounding, no float or fixed-Decimal-context conversion.
    all_columns = list(active) + result.active_indicator_features
    surviving_columns: list[str] = []
    for col in all_columns:
        distinct = {exact_structural[t][col] for t in working}
        if len(distinct) <= 1:
            result.dropped_features[col] = STATUS_ZERO_VARIANCE_FOLD_DROP
        else:
            surviving_columns.append(col)

    # Binding co-drop rule, enforced unconditionally as the single source of
    # truth regardless of WHY f3 was dropped (missingness at step 3, or
    # zero-variance just above): f5 exists solely to carry f3's missingness
    # and must never survive f3's removal.
    if "f3" in result.dropped_features and "f5" in surviving_columns:
        surviving_columns.remove("f5")
        result.dropped_features["f5"] = "F3_COUPLED_DROP"

    result.active_substantive_features = [c for c in surviving_columns if c in SUBSTANTIVE_FEATURES]
    result.active_indicator_features = [c for c in surviving_columns if c not in SUBSTANTIVE_FEATURES]

    if not result.active_substantive_features:
        result.insufficient_feature_variation = True
        return result

    # ---- STRUCTURAL LAYER COMPLETE. `surviving_columns` (equivalently
    # `active_substantive_features` + `active_indicator_features`) is now
    # final. Only from this point on does any MODEL NUMERIC operation run. ----

    # Step 7 (f1 only, MODEL NUMERIC, DEFERRED): the natural log is evaluated
    # only for a column that has already survived every structural decision
    # above (missingness, >40% drop, and exact pre-log zero variance) --
    # never earlier. A feature that would have been structurally dropped
    # never reaches this line, so its post-log representability is never
    # required (config/model_v1_3_spec.json
    # `structural_numeric_domain.structural_layer_must_complete_before_model_numeric_layer`;
    # V1.3 Section 2.2: "For f1, and only after the structural layer has
    # completed: evaluate the natural logarithm"). `log_values` feeds ONLY
    # standardization below and is never read by any structural decision.
    log_values: dict[str, Decimal] = {}
    if "f1" in surviving_columns:
        for t in working:
            v_dec = _fraction_to_model_decimal(exact_structural[t]["f1"], ctx, feature="f1", stage="FRACTION_TO_DECIMAL", scope="TRAIN")
            log_values[t] = _require_finite_decimal(
                _model_ln(v_dec, ctx, feature="f1", scope="TRAIN"), f"{t}.f1.log_input"
            )

    # =========================================================================
    # Step 9: standardization -- FEATURE-AWARE arithmetic domain (V1.3
    # `standardization`).
    #   f1:                mean/variance/std/z all MODEL_NUMERIC_FINITE_PRECISION,
    #                      computed on the TRANSFORMED log values.
    #   f2/f3/f4/f5:       mean/variance EXACT_RATIONAL (Fraction); std/z
    #                      MODEL_NUMERIC_FINITE_PRECISION.
    # Both branches use POPULATION variance, ddof = 0. Binary64 conversion
    # happens exactly once, after standardization, followed by I1-I4.
    # =========================================================================
    n = len(working)
    mean_dec: dict[str, Decimal] = {}
    mean_exact: dict[str, Fraction] = {}  # identity features only; f1's mean is MODEL NUMERIC only
    std_dec: dict[str, Decimal] = {}
    train_z_dec: dict[str, dict[str, Decimal]] = {t: {} for t in working}

    for col in surviving_columns:
        if col == "f1":
            values_dec = [log_values[t] for t in working]
            mean = _require_finite_decimal(
                _model_divide(_model_sum(values_dec, ctx, feature="f1", stage="MEAN_SUM", scope="TRAIN"), Decimal(n), ctx, feature="f1", stage="MEAN_DIVIDE", scope="TRAIN"),
                "f1.mean",
            )
            variance = _require_finite_decimal(
                _model_divide(
                    _model_sum(((v - mean) ** 2 for v in values_dec), ctx, feature="f1", stage="VARIANCE_SUM", scope="TRAIN"),
                    Decimal(n), ctx, feature="f1", stage="VARIANCE_DIVIDE", scope="TRAIN",
                ),
                "f1.variance",
            )
            if not (variance.is_finite() and variance > 0):
                raise NumericRepresentationIntegrityError(
                    "I2_POSITIVE_STD violated: f1 passed exact pre-log zero-variance check "
                    f"but MODEL NUMERIC post-log variance is {variance!r} (not finite and > 0)"
                )
            std = _require_finite_decimal(_model_sqrt(variance, ctx, feature="f1", scope="TRAIN"), "f1.std")
            if not (std.is_finite() and std > 0):
                raise NumericRepresentationIntegrityError(
                    f"I2_POSITIVE_STD violated: f1 std={std!r} is not finite and > 0"
                )
            mean_dec[col], std_dec[col] = mean, std
            for t in working:
                train_z_dec[t][col] = _require_finite_decimal(
                    _model_divide(log_values[t] - mean, std, ctx, feature="f1", stage="Z_DIVIDE", scope="TRAIN"), f"{t}.f1.z"
                )
        else:
            values_frac = [exact_structural[t][col] for t in working]
            mean_frac = _fraction_mean(values_frac)
            variance_frac = _fraction_population_variance(values_frac, mean_frac)
            if not variance_frac > 0:
                # Structurally unreachable: step 8 already verified >=2 exact-
                # distinct values for this column, which guarantees an exact
                # rational variance strictly greater than zero. A real logic
                # defect must fail loudly, never divide by zero silently.
                raise NumericRepresentationIntegrityError(
                    f"I2_POSITIVE_STD violated: {col} passed exact zero-variance check "
                    f"but exact rational variance computed as {variance_frac!r} (not > 0)"
                )
            variance_dec = _fraction_to_model_decimal(variance_frac, ctx, feature=col, stage="VARIANCE_FRACTION_TO_DECIMAL", scope="TRAIN")
            std = _require_finite_decimal(_model_sqrt(variance_dec, ctx, feature=col, scope="TRAIN"), f"{col}.std")
            if not (std.is_finite() and std > 0):
                raise NumericRepresentationIntegrityError(
                    f"I2_POSITIVE_STD violated: {col} std={std!r} is not finite and > 0 "
                    "at the frozen MODEL NUMERIC precision"
                )
            std_dec[col] = std
            mean_exact[col] = mean_frac  # EXACT — used for both train and test z-numerator subtraction
            mean_dec[col] = _fraction_to_model_decimal(mean_frac, ctx, feature=col, stage="MEAN_FRACTION_TO_DECIMAL", scope="REPORTING")
            for t in working:
                diff_frac = exact_structural[t][col] - mean_frac
                diff_dec = _fraction_to_model_decimal(diff_frac, ctx, feature=col, stage="Z_NUMERATOR_FRACTION_TO_DECIMAL", scope="TRAIN")
                train_z_dec[t][col] = _require_finite_decimal(
                    _model_divide(diff_dec, std, ctx, feature=col, stage="Z_DIVIDE", scope="TRAIN"), f"{t}.{col}.z"
                )

    # --- I3 (training fold): exact-structural distinctness must be preserved
    # by the binary64-converted standardized values, for EVERY active column,
    # not merely "did the whole column collapse to one value" (the prior
    # implementation's guard). ---
    for col in surviving_columns:
        exact_source = (
            {exact_structural[t]["f1"] for t in working} if col == "f1"
            else {exact_structural[t][col] for t in working}
        )
        result.standardization[col] = (
            _to_float(mean_dec[col], feature=col, stage="STANDARDIZATION_MEAN", scope="REPORTING"),
            _to_float(std_dec[col], feature=col, stage="STANDARDIZATION_STD", scope="REPORTING"),
        )
        column_floats: list[float] = []
        for t in working:
            fv = _to_float(train_z_dec[t][col], feature=col, stage="Z_TO_BINARY64", scope="TRAIN")
            if not math.isfinite(fv):
                raise NumericRepresentationIntegrityError(
                    f"I1_FINITE violated: {t}.{col} standardized value did not convert to a finite float"
                )
            result.train_matrix.setdefault(t, {})[col] = fv
            column_floats.append(fv)
        if len(set(column_floats)) != len(exact_source):
            raise NumericRepresentationIntegrityError(
                f"I3_DISTINCTNESS_PRESERVATION violated: {col} has {len(exact_source)} exact-distinct "
                f"structural training values but only {len(set(column_floats))} distinct binary64 "
                "standardized values -- a genuine distinction was lost at the numeric representation boundary"
            )

    # --- Apply the SAME fitted (train-only) parameters to the test row. ---
    test_working = dict(test_raw)
    test_f3 = test_working.get("f3")
    test_status = filter_status.get("__test__")
    if test_f3 is not None and "f3" in active and _opposite_explicit_status(test_status, _mode_or_none(training_f3_filtered, filter_status)):
        test_working["f3"] = None

    test_structural: dict[str, Fraction] = {}
    test_missing_f3 = False
    for feature_id in active:
        v = test_working.get(feature_id)
        v_frac = _to_fraction(v) if v is not None else None
        if feature_id in WINSORIZE_FEATURES and v_frac is not None and feature_id in winsor_bounds_frac:
            lo_frac, hi_frac = winsor_bounds_frac[feature_id]
            v_frac = _fraction_clamp(v_frac, lo_frac, hi_frac)
        if v_frac is None:
            v_frac = training_medians_frac.get(feature_id)
            if feature_id == "f3":
                test_missing_f3 = True
            if v_frac is None:
                raise ValueError(f"test observation missing {feature_id} with no training median available")
        test_structural[feature_id] = v_frac

    if create_f5:
        test_structural["f5"] = Fraction(1) if test_missing_f3 else Fraction(0)

    # Same data-integrity precondition as the training rows: an exact
    # Fraction comparison, unconditional on `surviving_columns`, checked
    # before any model-numeric operation runs for the test row.
    for feature_id in LOG_TRANSFORM_FEATURES:
        if feature_id not in test_structural:
            continue
        if test_structural[feature_id] <= 0:
            raise NonPositiveLogInputError(f"test.{feature_id}={test_structural[feature_id]} is non-positive; cannot log-transform")

    # Deferred MODEL NUMERIC log evaluation for the test row -- only if f1
    # actually survived the structural layer (same F-02 rule as training).
    test_log_value: Optional[Decimal] = None
    if "f1" in surviving_columns:
        v_dec = _fraction_to_model_decimal(test_structural["f1"], ctx, feature="f1", stage="FRACTION_TO_DECIMAL", scope="TEST")
        test_log_value = _require_finite_decimal(
            _model_ln(v_dec, ctx, feature="f1", scope="TEST"), "test.f1.log_input"
        )

    for col in surviving_columns:
        if col == "f1":
            z_dec = _require_finite_decimal(
                _model_divide(test_log_value - mean_dec[col], std_dec[col], ctx, feature="f1", stage="Z_DIVIDE", scope="TEST"),
                "test.f1.z",
            )
        else:
            # Subtract in the EXACT Fraction domain using the same exact
            # training mean the training rows used (mean_exact), not the
            # already-rounded reporting value in mean_dec -- otherwise the
            # test row would be double-rounded relative to the training
            # rows' z-computation above.
            diff_frac = test_structural[col] - mean_exact[col]
            diff_dec = _fraction_to_model_decimal(diff_frac, ctx, feature=col, stage="Z_NUMERATOR_FRACTION_TO_DECIMAL", scope="TEST")
            z_dec = _require_finite_decimal(
                _model_divide(diff_dec, std_dec[col], ctx, feature=col, stage="Z_DIVIDE", scope="TEST"), f"test.{col}.z"
            )
        test_fv = _to_float(z_dec, feature=col, stage="Z_TO_BINARY64", scope="TEST")
        if not math.isfinite(test_fv):
            raise NumericRepresentationIntegrityError(
                f"I4_TEST_ROW_FINITE violated: test.{col} standardized value did not convert to a finite float"
            )
        result.test_vector[col] = test_fv

    return result


def _mode_or_none(training_f3_filtered: dict[str, Optional[Decimal]], filter_status: dict[str, Optional[str]]) -> Optional[str]:
    statuses = [filter_status.get(t) for t, v in training_f3_filtered.items() if v is not None]
    usable = [s for s in statuses if s is not None]
    if not usable:
        return None
    return max(set(usable), key=usable.count)

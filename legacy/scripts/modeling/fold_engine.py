"""Parts C+D — historical walk-forward fold planner and test-target isolation.

oos_stream for every fold produced here is HISTORICAL_WALK_FORWARD (V1.1 §9).
No real freeze ever occurred for these 20 IPOs; `prediction_cutoff_date` is a
date-level information boundary, not a reconstructed clock.

Leakage controls implemented here (V1.1 §6.3, §6.4, §14):
  - realized-target-only rule: a training observation is only admissible if
    its target realized (target_session_date) at or before the TEST IPO's
    prediction_cutoff_date, AND the underlying row is OFFICIAL_VERIFIED /
    NO_CONFLICT.
  - same-day IPO group rule: no ticker may train on another ticker sharing the
    same first_trading_date. This is implied by strict chronological
    ordering (first_trading_date(j) < first_trading_date(k)) but is ALSO
    enforced by an explicit hard assertion so the guarantee does not rely on
    that implication alone.
  - MIN_TRAIN_N gate: folds with n_effective_train < MIN_TRAIN_N are marked
    INSUFFICIENT_TRAINING_HISTORY and produce no baseline prediction.
  - GuardedTargetStore: a runtime guard (not merely a naming convention) that
    raises if a fold's held-out target is read before that fold's Phase 1
    prediction has been explicitly unlocked for evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import common
from .target_extraction import TargetRecord, TARGET_AVAILABLE

OOS_STREAM_HISTORICAL = "HISTORICAL_WALK_FORWARD"
STATUS_OK = "OK"
STATUS_INSUFFICIENT_TRAINING_HISTORY = "INSUFFICIENT_TRAINING_HISTORY"


class SameDayCrossTrainingError(RuntimeError):
    """Hard-fail: a training observation shares first_trading_date with the test IPO."""


class FutureTargetLeakageError(RuntimeError):
    """Hard-fail: a training observation's target realized after the test IPO's cutoff."""


class TestTargetAccessedTooEarlyError(RuntimeError):
    """Hard-fail: the held-out test target was read before its fold was unlocked for evaluation."""


@dataclass(frozen=True)
class Fold:
    oos_stream: str
    horizon: str
    test_ticker: str
    test_first_trading_date: str
    prediction_cutoff_date: str
    same_day_group_id: str
    training_tickers: tuple[str, ...]
    n_chronological_train: int
    n_effective_train: int
    status: str


def _target_index(records: list[TargetRecord]) -> dict[tuple[str, str], TargetRecord]:
    return {(r.ticker, r.horizon): r for r in records}


def check_no_same_day_cross_training(cand_group: str, test_group: str, cand: str, test_ticker: str) -> None:
    """Hard assertion #2. Extracted as a standalone, directly unit-testable
    (positive AND negative/mutation) function — not inlined only."""
    if cand_group == test_group:
        raise SameDayCrossTrainingError(
            f"{cand} shares first_trading_date={cand_group} with test ticker {test_ticker}"
        )


def check_no_future_target(target_session_date: str, prediction_cutoff_date: str, cand: str, horizon: str) -> None:
    """Hard assertion #1. Extracted as a standalone, directly unit-testable
    (positive AND negative/mutation) function — not inlined only."""
    if target_session_date > prediction_cutoff_date:
        raise FutureTargetLeakageError(
            f"{cand}/{horizon} target_session_date={target_session_date} > cutoff={prediction_cutoff_date}"
        )


def plan_folds(target_records: list[TargetRecord], min_train_n: int) -> list[Fold]:
    universe = common.load_universe()
    groups = common.same_day_groups(universe)
    tix = _target_index(target_records)

    # Chronological order for walk-forward candidacy; ticker ASC is a pure
    # tie-break for deterministic serialization/reporting, never informational.
    ordered_tickers = sorted(universe, key=lambda t: (universe[t].first_trading_date, t))

    folds: list[Fold] = []
    for horizon in common.HORIZONS:
        for idx, test_ticker in enumerate(ordered_tickers):
            test_ftd = universe[test_ticker].first_trading_date
            cutoff = common.prediction_cutoff_date(test_ftd)

            # Chronological candidate pool: strictly earlier first_trading_date.
            # This alone already excludes the test ticker's same-day group.
            chronological_candidates = [t for t in ordered_tickers[:idx] if universe[t].first_trading_date < test_ftd]
            n_chronological = len(chronological_candidates)

            effective: list[str] = []
            for cand in chronological_candidates:
                # Same-day cross-training must be structurally impossible for
                # ANY candidate in the pool — a real violation here is always a
                # code defect, so this stays a hard-fail, not a filter.
                check_no_same_day_cross_training(groups[cand], groups[test_ticker], cand, test_ticker)
                rec = tix.get((cand, horizon))
                if rec is None or rec.target_status != TARGET_AVAILABLE:
                    continue
                # Realized-target-only rule as a FILTER, not a crash trigger:
                # first_trading_date ordering alone does not guarantee a given
                # horizon's target realizes in the same order (e.g. an IPO's
                # later D-day can realize on/after a subsequent IPO's own
                # first trading day). Excluding such a candidate is the
                # correct, expected outcome (it reduces n_effective_train,
                # exactly as the preregistration anticipates for D3/D5/D10) —
                # it must never be relaxed into inclusion.
                if rec.target_session_date > cutoff:
                    continue
                effective.append(cand)

            # Post-hoc hard-fail verification: the invariant must hold for
            # everything actually selected. This is what would catch a real
            # code defect (e.g. a future refactor that broke the filter above)
            # without firing on the expected, legitimate exclusions handled
            # by the `continue` above.
            for cand in effective:
                rec = tix[(cand, horizon)]
                check_no_future_target(rec.target_session_date, cutoff, cand, horizon)

            n_effective = len(effective)
            status = STATUS_OK if n_effective >= min_train_n else STATUS_INSUFFICIENT_TRAINING_HISTORY

            folds.append(Fold(
                oos_stream=OOS_STREAM_HISTORICAL, horizon=horizon, test_ticker=test_ticker,
                test_first_trading_date=test_ftd, prediction_cutoff_date=cutoff,
                same_day_group_id=groups[test_ticker], training_tickers=tuple(effective),
                n_chronological_train=n_chronological, n_effective_train=n_effective, status=status,
            ))
    return folds


class GuardedTargetStore:
    """Structural enforcement of `no_test_target_read_before_prediction`.

    Training targets are always readable. The single (ticker, horizon) pair
    designated as the active fold's held-out test observation is UNREADABLE
    until `unlock_for_evaluation()` is called — which the harness only calls
    after a Phase 1 prediction has been generated and persisted. Any earlier
    read raises, so this is a runtime guard, not a naming convention.
    """

    def __init__(self, target_records: list[TargetRecord]):
        self._all = _target_index(target_records)
        self._locked_key: Optional[tuple[str, str]] = None
        self._unlocked = False

    def enter_fold(self, test_ticker: str, horizon: str) -> None:
        self._locked_key = (test_ticker, horizon)
        self._unlocked = False

    def get_training_target(self, ticker: str, horizon: str) -> TargetRecord:
        key = (ticker, horizon)
        if key == self._locked_key and not self._unlocked:
            raise TestTargetAccessedTooEarlyError(
                f"Attempted to read held-out target {key} before its fold's prediction was unlocked for evaluation"
            )
        return self._all[key]

    def unlock_for_evaluation(self) -> None:
        if self._locked_key is None:
            raise RuntimeError("No fold entered; call enter_fold() first")
        self._unlocked = True

    def get_test_target_for_evaluation(self) -> TargetRecord:
        if self._locked_key is None:
            raise RuntimeError("No fold entered; call enter_fold() first")
        if not self._unlocked:
            raise TestTargetAccessedTooEarlyError(
                f"Attempted to read held-out target {self._locked_key} before unlock_for_evaluation() was called"
            )
        return self._all[self._locked_key]

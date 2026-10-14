"""R6 -- frozen §2, §11, §12, §13: chronology, walk-forward membership,
`STRICT_PRIOR_DATE_RULE`, `MIN_TRAIN_N`. Unchanged in substance from R5
(not among the R6 remediation corrections). Import path updated to
`scripts.modeling.prebookbuild_v1_r6`.

Sort key is `first_bookbuilding_date` ASC then `ticker` ASC (frozen §11) --
NOT `first_trading_date`.

`TrainingMembership` here remains a plain, publicly constructible metadata
dataclass -- it carries ticker IDs, counts, and dates only, never a
realized outcome VALUE, so constructing one directly is harmless for
eligibility computation. R6 closes the R5 finding by never accepting
ANY `TrainingMembership` (bare, or a caller-supplied evidence/eligibility
pair used to derive one) as PROOF of legal training-value access: the
value-bearing accessor (`outcome_firewall.GuardedOutcomeStore.legal_training_view`)
requires an opaque, registry-issued membership HANDLE minted only by
`capability.ExecutionCapability.verify_and_issue_membership`, which
independently recomputes this exact structure from the CAPABILITY's own
internally hash-verified evidence copy and a capability-owned outcome
store (see `capability.py`) -- never from caller-supplied evidence or
eligibility parameters.

`strict_prior_date_rule` is duck-typed on `.target_session_date`/
`.row_status`/`.conflict_status`: it is called both with the full
`OutcomeRow` (only ever for training-eligible tickers, via the verified
membership path) and with the lighter `outcome_firewall.EligibilityMetadata`
(used for the metadata-only scan every candidate's membership computation
must perform, which never exposes a held-out candidate's realized VALUE).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from scripts.modeling.prebookbuild_v1_r6.identity_gate import MIN_TRAIN_N, NO_CONFLICT, OFFICIAL_VERIFIED
from scripts.modeling.prebookbuild_v1_r6.targets import OutcomeRow

STATUS_OK = "OK"
STATUS_INSUFFICIENT_TRAINING_HISTORY = "INSUFFICIENT_TRAINING_HISTORY"


class PITViolationError(RuntimeError):
    """Frozen §2.3/§19.4: `spk_publication_date < first_bookbuilding_date`
    or `first_bookbuilding_date < first_trading_date` failed to hold
    strictly. Same-date publication (§2.3 SAME_DATE_PUBLICATION_FAILS_CLOSED)
    is included: equality fails the strict `<` check."""


class SameBookbuildingDateCrossTrainingError(RuntimeError):
    """Hard assertion (frozen §11.1, §19.4): no same-bookbuilding-date peer
    may ever appear in an effective training fold."""


class SortKeyViolationError(RuntimeError):
    """Frozen §11/§19.4: sort key must be `first_bookbuilding_date` ASC
    then `ticker` ASC."""


def sort_key(evidence_row: Mapping[str, str]) -> Tuple[str, str]:
    return (evidence_row["first_bookbuilding_date"], evidence_row["ticker"])


def assert_sort_order(evidence_rows) -> None:
    keys = [sort_key(r) for r in evidence_rows]
    if keys != sorted(keys):
        raise SortKeyViolationError("evidence rows are not ordered by (first_bookbuilding_date ASC, ticker ASC)")


def assert_pit_admissible(evidence_row: Mapping[str, str]) -> None:
    ticker = evidence_row.get("ticker", "<unknown>")
    pub = evidence_row["spk_publication_date"]
    t_k = evidence_row["first_bookbuilding_date"]
    trading = evidence_row["canonical_first_trading_date"]
    if not (pub < t_k):
        raise PITViolationError(f"{ticker}: spk_publication_date={pub!r} not strictly before first_bookbuilding_date={t_k!r}")
    if not (t_k < trading):
        raise PITViolationError(f"{ticker}: first_bookbuilding_date={t_k!r} not strictly before first_trading_date={trading!r}")


def strict_prior_date_rule(candidate_outcome: Optional[OutcomeRow], cutoff_date: str) -> bool:
    """Frozen §12, binding, no exceptions."""
    if candidate_outcome is None:
        return False
    if candidate_outcome.target_session_date is None:
        return False
    if not (candidate_outcome.target_session_date < cutoff_date):
        return False
    if candidate_outcome.row_status != OFFICIAL_VERIFIED:
        return False
    if candidate_outcome.conflict_status != NO_CONFLICT:
        return False
    return True


def check_no_same_bookbuilding_date_cross_training(
    candidate_bookbuilding_date: str, test_bookbuilding_date: str, candidate_ticker: str, test_ticker: str
) -> None:
    if candidate_bookbuilding_date == test_bookbuilding_date:
        raise SameBookbuildingDateCrossTrainingError(
            f"{candidate_ticker} shares first_bookbuilding_date={candidate_bookbuilding_date} with test ticker {test_ticker}"
        )


@dataclass(frozen=True)
class TrainingMembership:
    horizon: str
    test_ticker: str
    prediction_local_date: str
    training_tickers: Tuple[str, ...]
    n_chronological_train: int
    n_effective_train: int
    status: str


def build_training_membership(
    test_ticker: str, horizon: str, evidence_by_ticker: Mapping[str, Mapping[str, str]],
    outcome_by_ticker_horizon,
) -> TrainingMembership:
    """Frozen §11 steps 1-3. `outcome_by_ticker_horizon` must expose
    `.get((ticker, horizon))`."""
    test_row = evidence_by_ticker[test_ticker]
    t_k = test_row["first_bookbuilding_date"]

    pool = [t for t in evidence_by_ticker if t != test_ticker]
    n_chronological_train = len(pool)

    effective = []
    for cand in pool:
        outcome = outcome_by_ticker_horizon.get((cand, horizon))
        if strict_prior_date_rule(outcome, t_k):
            effective.append(cand)

    for cand in effective:
        check_no_same_bookbuilding_date_cross_training(
            evidence_by_ticker[cand]["first_bookbuilding_date"], t_k, cand, test_ticker
        )

    n_effective_train = len(effective)
    status = STATUS_OK if n_effective_train >= MIN_TRAIN_N else STATUS_INSUFFICIENT_TRAINING_HISTORY

    return TrainingMembership(
        horizon=horizon, test_ticker=test_ticker, prediction_local_date=t_k,
        training_tickers=tuple(sorted(effective, key=lambda t: (evidence_by_ticker[t]["first_bookbuilding_date"], t))),
        n_chronological_train=n_chronological_train, n_effective_train=n_effective_train, status=status,
    )

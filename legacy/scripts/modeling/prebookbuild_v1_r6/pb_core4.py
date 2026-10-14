"""R6 -- frozen §6.1-§6.6, §8.1: `PB_CORE_4` construction, exact
identities, forbidden-feature assertion, and the fail-closed field policy.

Unchanged science from R5 (PASS-graded by the R5 bounded independent
verification, SHA256 `adf619a93b2fd1cd348933b35c8341bcdef898e0db838163d458b57d6076952d`;
not reopened by the R6 remediation task, which is scoped to implementation
integrity only). Byte-identical in substance to
`scripts/modeling/prebookbuild_v1_r5/pb_core4.py`, reproduced here so that
R6 remains self-contained (imports nothing outside
`scripts.modeling.prebookbuild_v1_r6`).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from typing import Optional, Tuple

PB_CORE_4_FEATURE_NAMES: Tuple[str, ...] = ("pb1", "pb2", "pb3", "pb4")

FORBIDDEN_FEATURE_NAMES = frozenset(
    {
        "shares_offered_final", "shares_offered", "additional_sale_shares",
        "f3", "total_demand_multiple", "f5", "ipo_price_try",
        "planned_existing_sale_pct_of_base", "planned_post_ipo_capital",
        "planned_base_offer_shares", "planned_max_offer_shares",
        "ceiling_indicator", "additional_sale_ceiling_indicator",
    }
)

CEILING_ZERO_TOKENS = frozenset(
    {
        "SPK_TABLE_EXPLICIT_DASH__NO_PLANNED_ADDITIONAL_SALE",
        "SPK_TABLE_DASH__NO_PLANNED_ADDITIONAL_SALE",
        "KAP_APPROVED_PROSPECTUS_SECTION_25_2_5__EK_SATIS_YOKTUR",
    }
)
CEILING_NONZERO_TOKENS = frozenset(
    {
        "SPK_EXPLICIT_CONDITIONAL_ADDITIONAL_SALE_CEILING",
        "SPK_EXPLICIT_CONDITIONAL_ADDITIONAL_SALE_CEILING_IF_EXCESS_DEMAND",
    }
)

_REQUIRED_NUMERIC_FIELDS = (
    "ipo_price_try", "planned_pre_ipo_capital", "planned_post_ipo_capital",
    "planned_capital_increase_shares", "planned_existing_share_sale",
    "planned_base_offer_shares", "planned_additional_sale_ceiling", "planned_max_offer_shares",
)


class FieldUnavailableError(RuntimeError):
    def __init__(self, field: str):
        super().__init__(f"REQUIRED_FIELD_UNAVAILABLE:{field}")
        self.field = field


class IdentityContractViolation(RuntimeError):
    """Frozen §6.1/§6.4: an exact identity or range contract failed to hold
    bit-exactly. Hard, loud failure -- never a clamp, never a silent repair."""


class CeilingTokenError(RuntimeError):
    """Frozen §6.6 rule 3: unrecognised/blank/unparseable `additional_sale_semantics`
    must fail closed, never be silently converted to a zero ceiling."""


def parse_exact_decimal(raw: Optional[str], *, field: str) -> Decimal:
    if raw is None or raw.strip() == "":
        raise FieldUnavailableError(field)
    try:
        return Decimal(raw.strip())
    except InvalidOperation as exc:
        raise FieldUnavailableError(field) from exc


@dataclass(frozen=True)
class PBCore4Row:
    ticker: str
    pb1: float
    pb2: float
    pb3: float
    pb4: float
    # Exact structural layer, used for §6.7 rank gates and the §8.4
    # constant-column decision. Never used directly as model input.
    planned_base_offer_value_tl_exact: Decimal
    pb2_exact: Fraction
    pb3_exact: Fraction
    pb4_exact: Fraction


@dataclass(frozen=True)
class FailClosedResult:
    ticker: str
    reason: str


def build_pb_core4(row: dict, *, fail_closed: bool = False):
    """Frozen §6.1-§6.6, §8.1. `fail_closed=False` (historical replay,
    contractually complete evidence): raise loudly on any violation.
    `fail_closed=True` (prospective new-IPO row): return `FailClosedResult`
    (§16 `NO_AUTHORITATIVE_PREDICTION`) instead of raising."""
    ticker = row.get("ticker", "<unknown>")
    try:
        values = {f: parse_exact_decimal(row.get(f), field=f) for f in _REQUIRED_NUMERIC_FIELDS}
        semantics_raw = row.get("additional_sale_semantics")
        if semantics_raw is None or semantics_raw.strip() == "":
            raise FieldUnavailableError("additional_sale_semantics")
        semantics = semantics_raw.strip()

        ipo_price_try = values["ipo_price_try"]
        pre_ipo_capital = values["planned_pre_ipo_capital"]
        post_ipo_capital = values["planned_post_ipo_capital"]
        capital_increase_shares = values["planned_capital_increase_shares"]
        existing_share_sale = values["planned_existing_share_sale"]
        base_offer_shares = values["planned_base_offer_shares"]
        additional_sale_ceiling = values["planned_additional_sale_ceiling"]
        max_offer_shares = values["planned_max_offer_shares"]

        if post_ipo_capital != pre_ipo_capital + capital_increase_shares:
            raise IdentityContractViolation(f"{ticker}: ID-A violated")
        if base_offer_shares != capital_increase_shares + existing_share_sale:
            raise IdentityContractViolation(f"{ticker}: ID-B violated")
        if max_offer_shares != base_offer_shares + additional_sale_ceiling:
            raise IdentityContractViolation(f"{ticker}: ID-C violated")
        if base_offer_shares == 0:
            raise IdentityContractViolation(f"{ticker}: planned_base_offer_shares == 0")
        if post_ipo_capital == 0:
            raise IdentityContractViolation(f"{ticker}: planned_post_ipo_capital == 0")

        planned_base_offer_value_tl = ipo_price_try * base_offer_shares
        if planned_base_offer_value_tl <= 0:
            raise IdentityContractViolation(f"{ticker}: planned_base_offer_value_tl <= 0")

        pb2_exact = (Fraction(base_offer_shares) / Fraction(post_ipo_capital)) * 100
        pb3_exact = (Fraction(capital_increase_shares) / Fraction(base_offer_shares)) * 100
        pb4_exact = (Fraction(additional_sale_ceiling) / Fraction(base_offer_shares)) * 100

        if not (Fraction(0) < pb2_exact <= Fraction(100)):
            raise IdentityContractViolation(f"{ticker}: pb2={pb2_exact} outside (0,100]")
        if not (Fraction(0) < pb3_exact <= Fraction(100)):
            raise IdentityContractViolation(f"{ticker}: pb3={pb3_exact} outside (0,100]")
        if pb4_exact < 0:
            raise IdentityContractViolation(f"{ticker}: pb4={pb4_exact} < 0")

        if pb4_exact == 0:
            if semantics not in CEILING_ZERO_TOKENS:
                raise CeilingTokenError(f"{ticker}: pb4==0 but token {semantics!r} not recognised zero-state")
        else:
            if semantics not in CEILING_NONZERO_TOKENS:
                raise CeilingTokenError(f"{ticker}: pb4={pb4_exact}!=0 but token {semantics!r} not recognised ceiling-state")

        with localcontext() as ctx:
            ctx.prec = 60
            pb1_decimal = planned_base_offer_value_tl.ln()
        pb1 = float(pb1_decimal)
        pb2 = float(pb2_exact)
        pb3 = float(pb3_exact)
        pb4 = float(pb4_exact)

        return PBCore4Row(
            ticker=ticker, pb1=pb1, pb2=pb2, pb3=pb3, pb4=pb4,
            planned_base_offer_value_tl_exact=planned_base_offer_value_tl,
            pb2_exact=pb2_exact, pb3_exact=pb3_exact, pb4_exact=pb4_exact,
        )
    except (FieldUnavailableError, IdentityContractViolation, CeilingTokenError) as exc:
        if fail_closed:
            return FailClosedResult(ticker=ticker, reason=str(exc))
        raise


def assert_no_forbidden_features(feature_names) -> None:
    present = set(feature_names) & FORBIDDEN_FEATURE_NAMES
    if present:
        raise AssertionError(f"Forbidden PRE_BOOKBUILD V1 feature(s) present: {sorted(present)}")
    unknown = set(feature_names) - set(PB_CORE_4_FEATURE_NAMES)
    if unknown:
        raise AssertionError(f"Non-PB_CORE_4 feature(s) present: {sorted(unknown)}")

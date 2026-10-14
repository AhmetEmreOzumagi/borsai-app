"""R6 -- mandatory input identity gate. Self-contained: no import from any
V1/R2/R3/R4/R5 module. Also defines the FIXED (non-caller-overridable)
production paths for the R6 implementation manifest, the R6 implementation
receipt, the R6 bounded final independent verification human report AND
its machine-readable JSON attestation, the future execution preflight
report, and the fixed R6 execution output root.

Correction 1 (R5 FAIL): a normal caller must never be able to point
production capability minting at an alternate manifest, receipt,
attestation, preflight report, or output root. Every one of those
locations is a fixed constant referenced by qualified name
(`identity_gate.FIXED_...`) at the point of use in `authorization_package.py`
/ `trust_chain.py` / `capability.py` -- never imported by value -- so there
is no caller-facing override parameter anywhere in the production call
surface. Tests substitute synthetic content by patching these module
attributes (`unittest.mock.patch.object(identity_gate, "FIXED_R6_..._PATH", ...)`),
which is monkeypatching and explicitly outside the production threat model.
"""
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parents[3]

FROZEN_PREREG_PATH = (
    ROOT / "artifacts" / "modeling" / "prebookbuild_v1_frozen_preregistration"
    / "BORSAI_PREBOOKBUILD_V1_PREREG_20260825" / "PREBOOKBUILD_V1_PREREGISTRATION_FROZEN.md"
)
FROZEN_PREREG_SHA256 = "1a50a67362dcdccef9beb7117c04c6bf14320359bd3509383f1d7bcccf9d4da8"
FROZEN_PREREG_IDENTITY = "BORSAI_PREBOOKBUILD_V1_PREREG_20260825"

FROZEN_PREREG_FINAL_VERIFICATION_PATH = (
    ROOT / "artifacts" / "modeling" / "prebookbuild_v1_frozen_preregistration_verification"
    / "BORSAI_PREBOOKBUILD_V1_FROZEN_PREREGISTRATION_FINAL_INDEPENDENT_VERIFICATION_01"
    / "PREBOOKBUILD_V1_FROZEN_PREREGISTRATION_FINAL_INDEPENDENT_VERIFICATION.md"
)
FROZEN_PREREG_FINAL_VERIFICATION_SHA256 = "4dcc26dec0926bebdb5a20f56395ca1793d1258cdc068a339d8bb8008e89e731"

CANONICAL_EVIDENCE_CSV_PATH = (
    ROOT / "artifacts" / "data" / "prebookbuild_point_in_time_canonical"
    / "BORSAI_PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_20260825"
    / "PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv"
)
CANONICAL_EVIDENCE_CSV_SHA256 = "b1e9d96e89bb078addd4185dd6a33bc7b7cd79a6b092abe1dac4c8b13634d8f2"
CANONICAL_EVIDENCE_IDENTITY = "BORSAI_PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_20260825"

CANONICAL_EVIDENCE_FINAL_VERIFICATION_PATH = (
    ROOT / "artifacts" / "data" / "prebookbuild_point_in_time_canonical_audit"
    / "BORSAI_PREBOOKBUILD_EVIDENCE_V1_1_CANONICAL_R2_FINAL_INDEPENDENT_VERIFICATION_01"
    / "PREBOOKBUILD_EVIDENCE_V1_1_CANONICAL_R2_FINAL_INDEPENDENT_VERIFICATION.md"
)
CANONICAL_EVIDENCE_FINAL_VERIFICATION_SHA256 = "6f0271f17f4688392b49f521d45b03a0a7c57ec515d84e7b69e5e2e3ad51b54f"

HISTORICAL99_MEMBERSHIP_PATH = (
    ROOT / "artifacts" / "ipo_master" / "historical99" / "HISTORICAL99_FROZEN_COHORT_V1"
    / "canonical" / "HISTORICAL99_FROZEN_COHORT_V1_canonical_membership.csv"
)
HISTORICAL99_MEMBERSHIP_SHA256 = "b15c2e2c9e1a6ad9f702a469e6ba7c03eeef4828fd29afb59dbe780d8a2a1801"

OUTCOME_TARGETS_PATH = (
    ROOT / "artifacts" / "outcomes" / "historical99" / "HISTORICAL99_FROZEN_COHORT_V1"
    / "OFFICIAL_BIST_OUTCOME_V1" / "canonical"
    / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv"
)
OUTCOME_TARGETS_SHA256 = "64dce0bb3b2aff28f5dfd5f335da8f423a5cf0839430cac1df200bfed4417f9c"

OUTCOME_PROMOTION_MANIFEST_PATH = (
    ROOT / "artifacts" / "outcomes" / "historical99" / "HISTORICAL99_FROZEN_COHORT_V1"
    / "OFFICIAL_BIST_OUTCOME_V1" / "canonical"
    / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_promotion_manifest.json"
)
OUTCOME_PROMOTION_MANIFEST_SHA256 = "d4ff36bc23f6616eeeb2ae4cdde1d8ba4d20191d526d3cbca3a28d8eb949e7d2"

# --- immutable predecessor-round evidence (R5 bounded FAIL is the direct
#     authoritative predecessor of this R6 remediation task) ---

R5_BOUNDED_FINAL_VERIFICATION_PATH = (
    ROOT / "artifacts" / "modeling" / "prebookbuild_v1_evaluator_verification"
    / "BORSAI_PREBOOKBUILD_V1_EVALUATOR_R5_BOUNDED_FINAL_INDEPENDENT_VERIFICATION_01"
    / "PREBOOKBUILD_V1_EVALUATOR_R5_BOUNDED_FINAL_INDEPENDENT_VERIFICATION.md"
)
R5_BOUNDED_FINAL_VERIFICATION_SHA256 = "adf619a93b2fd1cd348933b35c8341bcdef898e0db838163d458b57d6076952d"

R5_MANIFEST_PATH = (
    ROOT / "artifacts" / "modeling" / "prebookbuild_v1_evaluator_implementation"
    / "BORSAI_PREBOOKBUILD_V1_EVALUATOR_IMPL_R5_20260826" / "PREBOOKBUILD_V1_EVALUATOR_IMPL_R5_MANIFEST.json"
)
R5_MANIFEST_SHA256 = "9892db5b3693bc7794a10815dad10f6356626269cb9bffa1a7864d75062e4459"

R5_RECEIPT_PATH = (
    ROOT / "artifacts" / "modeling" / "prebookbuild_v1_evaluator_implementation"
    / "BORSAI_PREBOOKBUILD_V1_EVALUATOR_IMPL_R5_20260826" / "PREBOOKBUILD_V1_EVALUATOR_IMPL_R5_RECEIPT.txt"
)
R5_RECEIPT_SHA256 = "75c7405c644c8b8f0a08bbdf428cfb866b69a366dd8e98817b88a71fae300b92"

MANDATORY_INPUT_IDENTITIES: Tuple[Tuple[str, Path, str], ...] = (
    ("FROZEN_PREREGISTRATION_DOCUMENT", FROZEN_PREREG_PATH, FROZEN_PREREG_SHA256),
    ("FROZEN_PREREGISTRATION_FINAL_VERIFICATION", FROZEN_PREREG_FINAL_VERIFICATION_PATH, FROZEN_PREREG_FINAL_VERIFICATION_SHA256),
    ("CANONICAL_EVIDENCE_CSV", CANONICAL_EVIDENCE_CSV_PATH, CANONICAL_EVIDENCE_CSV_SHA256),
    ("CANONICAL_EVIDENCE_FINAL_VERIFICATION", CANONICAL_EVIDENCE_FINAL_VERIFICATION_PATH, CANONICAL_EVIDENCE_FINAL_VERIFICATION_SHA256),
    ("HISTORICAL99_MEMBERSHIP", HISTORICAL99_MEMBERSHIP_PATH, HISTORICAL99_MEMBERSHIP_SHA256),
    ("R5_BOUNDED_FINAL_VERIFICATION_FAIL_AUDIT", R5_BOUNDED_FINAL_VERIFICATION_PATH, R5_BOUNDED_FINAL_VERIFICATION_SHA256),
    ("R5_IMPLEMENTATION_MANIFEST", R5_MANIFEST_PATH, R5_MANIFEST_SHA256),
    ("R5_IMPLEMENTATION_RECEIPT", R5_RECEIPT_PATH, R5_RECEIPT_SHA256),
)

EXECUTION_INPUT_IDENTITIES: Tuple[Tuple[str, Path, str], ...] = (
    ("OUTCOME_TARGETS_CSV", OUTCOME_TARGETS_PATH, OUTCOME_TARGETS_SHA256),
    ("OUTCOME_PROMOTION_MANIFEST", OUTCOME_PROMOTION_MANIFEST_PATH, OUTCOME_PROMOTION_MANIFEST_SHA256),
)

HORIZONS: Tuple[str, ...] = ("D1", "D3", "D5", "D10")
MIN_TRAIN_N = 10
OFFICIAL_VERIFIED = "OFFICIAL_VERIFIED"
NO_CONFLICT = "NO_CONFLICT"

# --- FIXED (non-caller-overridable) production anchor paths ---

IMPLEMENTATION_IDENTITY = "BORSAI_PREBOOKBUILD_V1_EVALUATOR_IMPL_R6_20260826"

FIXED_R6_MANIFEST_PATH = (
    ROOT / "artifacts" / "modeling" / "prebookbuild_v1_evaluator_implementation"
    / "BORSAI_PREBOOKBUILD_V1_EVALUATOR_IMPL_R6_20260826" / "PREBOOKBUILD_V1_EVALUATOR_IMPL_R6_MANIFEST.json"
)
FIXED_R6_RECEIPT_PATH = (
    ROOT / "artifacts" / "modeling" / "prebookbuild_v1_evaluator_implementation"
    / "BORSAI_PREBOOKBUILD_V1_EVALUATOR_IMPL_R6_20260826" / "PREBOOKBUILD_V1_EVALUATOR_IMPL_R6_RECEIPT.txt"
)
# The R6 implementation receipt's job is to bind the R6 manifest's physical
# SHA-256 and the R6 implementation identity, in a strict `KEY=VALUE`
# grammar (never substring-searched) -- see `trust_chain.parse_strict_receipt`.

FIXED_R6_VERIFICATION_TASK_ID = "BORSAI_PREBOOKBUILD_V1_EVALUATOR_R6_BOUNDED_FINAL_INDEPENDENT_VERIFICATION_01"
FIXED_R6_VERIFICATION_VERDICT = "PREBOOKBUILD_V1_EVALUATOR_R6_BOUNDED_FINAL_INDEPENDENT_VERIFICATION_PASS"

FIXED_R6_VERIFICATION_REPORT_PATH = (
    ROOT / "artifacts" / "modeling" / "prebookbuild_v1_evaluator_verification"
    / "BORSAI_PREBOOKBUILD_V1_EVALUATOR_R6_BOUNDED_FINAL_INDEPENDENT_VERIFICATION_01"
    / "PREBOOKBUILD_V1_EVALUATOR_R6_BOUNDED_FINAL_INDEPENDENT_VERIFICATION.md"
)
# Human-readable only. Correction 1: this file is NEVER read by any
# production trust decision -- `trust_chain.resolve_fixed_trust_chain`
# only physically hashes it (to bind `human_report_sha256` inside the
# JSON attestation below) and never opens/parses its text.

FIXED_R6_VERIFICATION_ATTESTATION_PATH = (
    ROOT / "artifacts" / "modeling" / "prebookbuild_v1_evaluator_verification"
    / "BORSAI_PREBOOKBUILD_V1_EVALUATOR_R6_BOUNDED_FINAL_INDEPENDENT_VERIFICATION_01"
    / "PREBOOKBUILD_V1_EVALUATOR_R6_BOUNDED_FINAL_INDEPENDENT_VERIFICATION_ATTESTATION.json"
)
# The FIXED machine-readable trust artifact (Correction 1). Strict,
# duplicate-key-rejecting, exact-schema JSON -- see `trust_chain.py`.
# This file MUST NOT exist as of the R6 implementation task -- it is a
# separate, future, independently-produced artifact. Its absence makes a
# real Historical99 capability grant impossible until it exists AND PASSes.

FIXED_PREFLIGHT_TASK_ID = "BORSAI_PREBOOKBUILD_V1_HISTORICAL_EVALUATION_EXECUTION_PREFLIGHT_01"
FIXED_PREFLIGHT_VERDICT = "PREBOOKBUILD_V1_HISTORICAL_EVALUATION_EXECUTION_PREFLIGHT_PASS"
FIXED_PREFLIGHT_REPORT_PATH = (
    ROOT / "artifacts" / "modeling" / "prebookbuild_v1_historical_evaluation_execution_preflight"
    / "BORSAI_PREBOOKBUILD_V1_HISTORICAL_EVALUATION_EXECUTION_PREFLIGHT_01"
    / "PREBOOKBUILD_V1_HISTORICAL_EVALUATION_EXECUTION_PREFLIGHT_01_REPORT.json"
)
# This file also MUST NOT exist as of the R6 implementation task.

FIXED_R6_EXECUTION_OUTPUT_ROOT = (
    ROOT / "artifacts" / "modeling" / "prebookbuild_v1_r6_historical_execution_output"
)
# Correction: production capability minting does not accept a
# caller-selected output root at all -- every real execution writes under
# this single fixed constant. There is no "output_base_dir" parameter
# anywhere on the R6 production grant/writer surface.

FIXED_R6_RESERVATION_ROOT = (
    ROOT / "artifacts" / "modeling" / "prebookbuild_v1_execution_reservations_r6"
)
# A namespace SEPARATE from the execution output root: the one-shot
# reservation ledger is global to this evaluator lineage and is never
# derived from, or scoped by, the (also fixed) output directory. A
# distinct namespace from R5's own reservation root, so R6 cannot be
# confused with, or silently reuse, an R5 reservation marker.


class IdentityMismatchError(RuntimeError):
    """A mandatory input identity did not match. STOP with
    `BLOCKED_INPUT_IDENTITY_MISMATCH`."""


@dataclass(frozen=True)
class IdentityCheck:
    name: str
    path: Path
    expected_sha256: str
    actual_sha256: str

    @property
    def match(self) -> bool:
        return self.expected_sha256 == self.actual_sha256


def sha256_file(path: Path) -> str:
    if not path.exists():
        return "FILE_NOT_FOUND"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_identities(identities: Tuple[Tuple[str, Path, str], ...]):
    checks = []
    for name, path, expected in identities:
        checks.append(IdentityCheck(name, path, expected, actual_sha256=sha256_file(path)))
    return checks


def require_identities(identities: Tuple[Tuple[str, Path, str], ...]):
    checks = verify_identities(identities)
    mismatches = [c for c in checks if not c.match]
    if mismatches:
        detail = "; ".join(f"{c.name}: expected={c.expected_sha256} actual={c.actual_sha256}" for c in mismatches)
        raise IdentityMismatchError(f"BLOCKED_INPUT_IDENTITY_MISMATCH: {detail}")
    return checks


def require_mandatory_input_identities():
    return require_identities(MANDATORY_INPUT_IDENTITIES)


def verify_execution_input_identities():
    return verify_identities(EXECUTION_INPUT_IDENTITIES)


def read_csv_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_canonical_evidence_rows():
    require_identities((("CANONICAL_EVIDENCE_CSV", CANONICAL_EVIDENCE_CSV_PATH, CANONICAL_EVIDENCE_CSV_SHA256),))
    return read_csv_rows(CANONICAL_EVIDENCE_CSV_PATH)


def load_membership_rows():
    require_identities((("HISTORICAL99_MEMBERSHIP", HISTORICAL99_MEMBERSHIP_PATH, HISTORICAL99_MEMBERSHIP_SHA256),))
    rows = read_csv_rows(HISTORICAL99_MEMBERSHIP_PATH)
    tickers = [r["ticker"] for r in rows]
    if len(tickers) != 99 or len(set(tickers)) != 99:
        raise ValueError(
            f"HISTORICAL99_FROZEN_COHORT_V1 membership must be 99 unique tickers; got {len(tickers)} rows, "
            f"{len(set(tickers))} unique"
        )
    return rows

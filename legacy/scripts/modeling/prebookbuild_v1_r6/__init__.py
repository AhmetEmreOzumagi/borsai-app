"""PRE_BOOKBUILD V1 evaluator — R6 additive remediation implementation.

Implementation identity: `BORSAI_PREBOOKBUILD_V1_EVALUATOR_IMPL_R6_20260826`.

R6 closes the exact six minimum implementation corrections raised by the
independent R5 bounded final verification
(`BORSAI_PREBOOKBUILD_V1_EVALUATOR_R5_BOUNDED_FINAL_INDEPENDENT_VERIFICATION_01`,
verdict FAIL, SHA256 `adf619a93b2fd1cd348933b35c8341bcdef898e0db838163d458b57d6076952d`):

1. FIXED_TRUST_CHAIN: the fixed R6 self-trust chain (`trust_chain.py`,
   `authorization_package.py`) no longer parses PASS text or hashes out of
   free-form Markdown via substring search. The R6 implementation receipt
   is parsed with a strict line-oriented `KEY=VALUE` grammar
   (`trust_chain.parse_strict_receipt`) that rejects duplicate/malformed
   keys. The FUTURE R6 bounded verification's machine-trust artifact is a
   fixed-schema, duplicate-key-rejecting JSON attestation
   (`trust_chain.validate_attestation_payload`) -- the human-readable
   Markdown report is preserved for people but is never consulted by any
   production trust decision.
2. VERIFIED_MEMBERSHIP_ISSUANCE / HELDOUT_TRAINING_VIEW: membership
   issuance (`capability.py`) no longer accepts caller-supplied
   `evidence_rows_by_ticker` or `eligibility_view`. The capability loads
   and hash-verifies its own canonical evidence copy at grant time and
   accepts only a capability-OWNED `outcome_firewall.GuardedOutcomeStore`
   (verified to belong to this exact capability) as the source of
   eligibility metadata. The caller-facing membership is an opaque,
   immutable `str` handle; ALL authoritative membership state (candidate,
   horizon, legal ticker IDs, m, U(k), issuance sequence) lives in a
   closure-private registry keyed by that handle, never on a
   caller-visible/-mutable object.
3. FIT_BUDGET_ENFORCEMENT / FIT_EVENT_SINGLE_USE: fit authorization is
   also an opaque `str` handle; the full fit context (execution ID,
   candidate, horizon, head, model kind, hyperparameter, role, inner fold,
   sequence, counters, consumed flag) lives only in the closure-private
   fit-authorization registry. Ordinary attribute assignment on a returned
   handle cannot alter any of it (a `str` has no such attributes to begin
   with), and a second consumption of the same or a copied handle fails
   closed.
4. ORCHESTRATION_RESULT_PROOF / HELDOUT_FIREWALL: the public string-keyed
   `record_model_attempt(membership, model_id)` completion API is REMOVED.
   Model-result events require a two-step, single-use
   `begin_model_result(...)` / `finish_model_result(...)` ticket; for the
   four fitted heads, `finish_model_result` cross-checks the presented
   fit-event references against ACTUAL recorded FINAL-role fit-ledger
   entries for that exact (candidate, horizon, head); for the five
   baselines, it requires that the firewall-gated legal training view was
   actually read for that exact membership handle first. Fold completion
   requires the exact nine registry-issued result events for that exact
   membership handle -- never a bare membership + string.
5. PROVENANCE_COMPLETENESS: `provenance.py` independently reconstructs and
   cross-validates every contextual/proof field (ticker/horizon/cutoff,
   m/U(k)/legal ticker set, model/status/hyperparameter/output
   consistency, fit/result/completion event references, per-record metric
   membership, Logistic diagnostics) against the capability's own private
   registries -- never trusting a caller-supplied record's self-reported
   values for any protected field.
6. RESULT_RECEIPT terminal completion: `reservation.mark_completed` now
   REQUIRES the execution output directory and independently
   re-verifies -- by reading the filesystem -- that every required
   artifact physically exists and that `EXECUTION_RECEIPT.txt`'s declared
   per-file SHA-256 matches the actual current bytes, and that the
   manifest's own `execution_id` matches, before transitioning
   `RESERVED_FOR_EXECUTION -> COMPLETED_CONSUMED`; a repeated call after
   completion is rejected (idempotent, not reusable). Terminal completion
   is therefore structurally impossible without validated, atomically
   written artifacts, regardless of who calls the transition function or
   when.

R6 is self-contained like R5: it imports nothing project-local outside
`scripts.modeling.prebookbuild_v1_r6` itself. R1-R5 are preserved
unmodified as historical evidence.
"""
from __future__ import annotations

IMPLEMENTATION_IDENTITY = "BORSAI_PREBOOKBUILD_V1_EVALUATOR_IMPL_R6_20260826"
IMPLEMENTATION_STATUS = "IMPLEMENTED_NOT_EXECUTED_PENDING_INDEPENDENT_VERIFICATION"
SUPERSEDES_FAILED_IMPLEMENTATION = "BORSAI_PREBOOKBUILD_V1_EVALUATOR_IMPL_R5_20260826"
R5_BOUNDED_FINAL_VERIFICATION_SHA256 = "adf619a93b2fd1cd348933b35c8341bcdef898e0db838163d458b57d6076952d"
R5_MANIFEST_SHA256_PRESERVED = "9892db5b3693bc7794a10815dad10f6356626269cb9bffa1a7864d75062e4459"
R5_RECEIPT_SHA256_PRESERVED = "75c7405c644c8b8f0a08bbdf428cfb866b69a366dd8e98817b88a71fae300b92"
SUPERSESSION_REASON = "R5_BOUNDED_FINAL_INDEPENDENT_VERIFICATION_IMPLEMENTATION_INTEGRITY_REMEDIATION"

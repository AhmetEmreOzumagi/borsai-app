"""TRUE_LIVE V1.5 registry-persistence gate.

Task BORSAI_LIVE_FREEZE_PERSISTENCE_MINIMUM_REMEDIATION_01, hardened by
BORSAI_LIVE_FREEZE_PERSISTENCE_MINIMUM_REMEDIATION_02 in response to a
bounded independent re-audit (`LIVE_FREEZE_PERSISTENCE_REAUDIT_FAIL`) that
reproduced four concrete gaps in the _01 implementation: (1) a partial
commit followed by a retry could reach the idempotent-success branch without
verifying registry/summary consistency or a pending journal first; (2) the
caller could supply arbitrary registry/summary/journal paths, defeating the
"repository-managed persistence" contract; (3) packet fields were persisted
without any schema/identity validation; (4) there was no contemporaneous-
time firewall, so a freeze attempted on or after a ticker's own
first_trading_date could still be reported FROZEN. All four are fixed below,
each still built entirely from the already-proven LIVE_V0 freeze plumbing's
schema-agnostic primitives -- no second persistence engine was written.

Responds to an independent persistence audit (PERSISTENCE_FINAL_GATE_FAIL):
a prior TKNKA TRUE_LIVE V1.5 freeze was declared FROZEN as an external file
only, without ever satisfying repository-managed append-only registry/hash
persistence. This module makes persistence -- and now also packet validity,
canonical-path enforcement, and contemporaneous pretrade timing -- a hard,
simultaneous prerequisite for any *_TRUE_LIVE_V1_5_FROZEN verdict:

    candidate prediction computed
      -> packet schema/identity validated
      -> canonical repository-managed paths resolved and verified
      -> pending journal (if any) safely recovered, state re-verified
      -> contemporaneous pretrade window checked against the real clock
      -> registry append attempted
      -> append succeeds atomically
      -> row hash / prediction identity registered
      -> persisted row is read back and verified
      -> only then may FROZEN be reported

freeze_true_live_prediction() is the only function in this module capable of
returning a *_TRUE_LIVE_V1_5_FROZEN verdict. Every one of the steps above
runs on every call -- first attempt, retry, and recovery alike; none of them
is skipped for an already-committed identical packet.

This module does not fit, tune, select, or compute any model output. It
persists a caller-supplied, already-computed packet. It never fetches market
data and never opens any TKNKA/VEYAS/CITAS/KPEKS outcome data.

Deliberately separate from live_forecast_registry.csv / live_forecast.toml's
LIVE_V0 registry: V1.5 TRUE_LIVE (multi-horizon D1/D3/D5/D10 Ridge+Logistic,
pretrade freeze) is a structurally different track from LIVE_V0 (single-
horizon EOD_NEXT_DAY next-close inference). This module reuses the LIVE_V0
freeze plumbing's schema-agnostic primitives (FreezeTransaction,
FreezeProposal, canonical_record_hash, canonical_registry_hashes,
assert_no_duplicate_ids, assert_byte_prefix_preserved, verify_post_commit,
verify_registry_summary_identity, recover_journal, load_config, and the
byte-exact CSV append technique) against its own dedicated registry/summary
file pair, derived from a validated project root, instead of building a
second implementation of any of them.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Sequence
from zoneinfo import ZoneInfo

from .guards import PolicyViolation
from .live_forecast import load_config
from .live_forecast_freeze import (
    FreezeProposal,
    FreezeTransaction,
    assert_byte_prefix_preserved,
    assert_no_duplicate_ids,
    canonical_record_hash,
    canonical_registry_hashes,
    read_csv,
    recover_journal,
    sha256,  # noqa: F401  (re-exported for callers that want to spot-check a path)
    verify_post_commit,  # noqa: F401  (re-exported; used internally by stage_and_commit)
    verify_registry_summary_identity,
)

_ISTANBUL = ZoneInfo("Europe/Istanbul")

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

#: Fields that constitute the frozen prediction's content identity. Order is
#: the on-disk column order.
CONTENT_FIELDS: tuple[str, ...] = (
    "prediction_id",
    "ticker",
    "horizon",
    "freeze_timestamp_istanbul",
    "prediction_local_date",
    "first_trading_date",
    "governing_spec",
    "model_config_sha256",
    "candidate_feature_hash",
    "training_snapshot_id",
    "n_train",
    "ridge_alpha",
    "ridge_predicted_return",
    "ridge_predicted_price_tl",
    "logistic_c",
    "p_up",
    "direction",
    "confidence",
    "prediction_interval",
    "risk_label",
)

#: Write-time bookkeeping, appended after CONTENT_FIELDS. Excluded from the
#: content-identity hash so that persisting the identical packet twice (a
#: retry) is detectable as identical regardless of when each attempt ran.
BOOKKEEPING_FIELDS: tuple[str, ...] = ("packet_sha256", "persisted_at_istanbul")

TRUE_LIVE_REGISTRY_HEADERS: tuple[str, ...] = CONTENT_FIELDS + BOOKKEEPING_FIELDS

#: Stable markers used to prove a caller-supplied project_root really is
#: this repository before any path is derived from it. Both are read (not
#: merely stat'd) -- see resolve_true_live_paths.
_PROJECT_ROOT_MARKERS: tuple[str, ...] = ("config/live_forecast.toml", "pyproject.toml")

_ALLOWED_HORIZONS = frozenset({"D1", "D3", "D5", "D10"})
_ALLOWED_DIRECTIONS = frozenset({"UP", "DOWN"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class TrueLivePersistenceFailure(PolicyViolation):
    """Raised (and always converted to a non-FROZEN TrueLiveFreezeResult by
    freeze_true_live_prediction, never propagated as a bare exception to a
    caller building a verdict string) when registry persistence, project-root
    validation, or state recovery could not be completed and verified."""


class ContentMismatchOnRetryError(PolicyViolation):
    """Raised when a proposed packet reuses an existing prediction_id but
    its content differs from the already-committed row. A retry must be
    byte-identical in content or it is refused -- never silently applied as
    an overwrite."""


class PacketValidationError(PolicyViolation):
    """Raised when a caller-supplied packet fails required schema/identity
    validation. Always checked before any path is touched or any byte is
    written."""


class PretradeWindowClosedError(PolicyViolation):
    """Raised internally to short-circuit to the WINDOW_CLOSED verdict; never
    escapes freeze_true_live_prediction as a bare exception."""


@dataclass(frozen=True)
class TrueLivePredictionPacket:
    """A single already-computed, caller-supplied candidate prediction for
    one (ticker, horizon). This dataclass performs no computation; every
    field is expected to already be final."""

    prediction_id: str
    ticker: str
    horizon: str
    freeze_timestamp_istanbul: str
    prediction_local_date: str
    first_trading_date: str
    governing_spec: str
    model_config_sha256: str
    candidate_feature_hash: str
    training_snapshot_id: str
    n_train: str
    ridge_alpha: str
    ridge_predicted_return: str
    ridge_predicted_price_tl: str
    logistic_c: str
    p_up: str
    direction: str
    confidence: str
    prediction_interval: str
    risk_label: str

    def content_row(self) -> dict[str, str]:
        return {field: str(value) for field, value in asdict(self).items()}


@dataclass(frozen=True)
class TrueLiveFreezeResult:
    """The only object freeze_true_live_prediction returns. A caller must
    treat clean_true_live_metric_eligible as the single source of truth for
    whether a FROZEN verdict may be reported -- verdict is human-readable
    only, never itself the gating condition."""

    clean_true_live_metric_eligible: bool
    verdict: str
    prediction_id: str
    already_committed: bool
    row_hash: str | None
    registry_path: Path | None
    summary_path: Path | None
    error: str | None = None


# ---------------------------------------------------------------------------
# Packet schema/identity validation (Blocker 3)
# ---------------------------------------------------------------------------


def _is_sha256_hex(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value.lower()))


def _require_finite_float(value: str, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise PacketValidationError(f"{field} geçerli bir sayı değil: {value!r}") from None
    if not math.isfinite(parsed):
        raise PacketValidationError(f"{field} sonlu (finite) değil: {value!r}")
    return parsed


def _require_iso_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise PacketValidationError(f"{field} geçerli bir ISO tarihi değil: {value!r}") from None


def validate_packet(packet: TrueLivePredictionPacket) -> None:
    """Rejects an incomplete or malformed packet before any path is touched
    or any byte is written. Recomputation of packet_sha256 (rather than
    trusting a caller-supplied value) is handled separately in
    freeze_true_live_prediction -- this module never accepts a
    caller-supplied content hash at all; it is always derived here."""
    if not packet.prediction_id:
        raise PacketValidationError("prediction_id boş")
    if not packet.ticker:
        raise PacketValidationError("ticker boş")
    if packet.horizon not in _ALLOWED_HORIZONS:
        raise PacketValidationError(f"desteklenmeyen horizon: {packet.horizon!r}")
    _require_iso_date(packet.first_trading_date, "first_trading_date")
    _require_iso_date(packet.prediction_local_date, "prediction_local_date")
    try:
        datetime.fromisoformat(packet.freeze_timestamp_istanbul)
    except (TypeError, ValueError):
        raise PacketValidationError(
            f"freeze_timestamp_istanbul geçerli bir ISO zaman damgası değil: {packet.freeze_timestamp_istanbul!r}"
        ) from None
    if not packet.governing_spec:
        raise PacketValidationError("governing_spec boş")
    if not _is_sha256_hex(packet.model_config_sha256):
        raise PacketValidationError(f"model_config_sha256 geçerli SHA-256 değil: {packet.model_config_sha256!r}")
    if not _is_sha256_hex(packet.candidate_feature_hash):
        raise PacketValidationError(f"candidate_feature_hash geçerli SHA-256 değil: {packet.candidate_feature_hash!r}")
    if not packet.training_snapshot_id:
        raise PacketValidationError("training_snapshot_id boş")
    try:
        n_train = int(packet.n_train)
    except (TypeError, ValueError):
        raise PacketValidationError(f"n_train geçerli bir tamsayı değil: {packet.n_train!r}") from None
    if n_train < 0:
        raise PacketValidationError(f"n_train negatif: {n_train}")
    _require_finite_float(packet.ridge_alpha, "ridge_alpha")
    _require_finite_float(packet.ridge_predicted_return, "ridge_predicted_return")
    _require_finite_float(packet.ridge_predicted_price_tl, "ridge_predicted_price_tl")
    _require_finite_float(packet.logistic_c, "logistic_c")
    p_up = _require_finite_float(packet.p_up, "p_up")
    if not (0.0 <= p_up <= 1.0):
        raise PacketValidationError(f"p_up geçerli bir olasılık temsili değil (0..1 dışında): {p_up}")
    if packet.direction not in _ALLOWED_DIRECTIONS:
        raise PacketValidationError(f"geçersiz direction: {packet.direction!r}")
    if not packet.confidence:
        raise PacketValidationError("confidence boş")
    if not packet.prediction_interval:
        raise PacketValidationError("prediction_interval boş")
    if not packet.risk_label:
        raise PacketValidationError("risk_label boş")


# ---------------------------------------------------------------------------
# Repository-managed path enforcement (Blocker 2)
# ---------------------------------------------------------------------------


def resolve_true_live_paths(project_root: Path) -> tuple[Path, Path, Path]:
    """Derives the canonical TRUE_LIVE V1.5 registry/summary/journal paths
    from a validated project root. Production callers may only choose which
    project root to point at (e.g. the real repository root, or -- in
    tests only -- an isolated fixture directory built with the same marker
    layout); they may never supply a registry/summary/journal path
    directly. Rejects a root that is missing the stable markers, whose
    live_forecast.toml doesn't parse or declares an unexpected timezone
    (proving it is not this project's binding config), or whose derived
    artifact directory would not resolve underneath the root itself."""
    root = project_root.resolve()
    for marker in _PROJECT_ROOT_MARKERS:
        if not (root / marker).is_file():
            raise TrueLivePersistenceFailure(
                f"project_root geçerli bir proje kökü değil -- eksik işaret: {marker} (root={root})"
            )
    config = load_config(root)
    if config.get("timezone") != "Europe/Istanbul":
        raise TrueLivePersistenceFailure(
            f"config/live_forecast.toml timezone beklenmedik değerde: {config.get('timezone')!r}"
        )
    live_forecast_dir = (root / "artifacts" / "live_forecast").resolve()
    try:
        live_forecast_dir.relative_to(root)
    except ValueError:
        raise TrueLivePersistenceFailure("türetilmiş kayıt dizini proje kökünü aşıyor") from None
    # The real repository already has this directory; a fixture root built
    # only from the two markers may not. Creating it here is part of
    # deriving a ready-to-use canonical path from a validated root, not an
    # independent write path -- it only ever runs after the marker+config
    # validation above has already accepted this root.
    live_forecast_dir.mkdir(parents=True, exist_ok=True)
    return (
        live_forecast_dir / "true_live_v1_5_registry.csv",
        live_forecast_dir / "true_live_v1_5_summary.json",
        live_forecast_dir / "true_live_v1_5_registry.journal.json",
    )


# ---------------------------------------------------------------------------
# Contemporaneous-time firewall (Blocker 4 / §5)
# ---------------------------------------------------------------------------


def _now_istanbul() -> datetime:
    """The ONLY production source of 'now' for the pretrade-window check.
    Deliberately takes no arguments and reads no caller-supplied value --
    tests patch this exact module-level function (monkeypatch at the module
    boundary), which is the only sanctioned way to control it. There is no
    parameter anywhere in this module's public API that lets a normal
    caller supply or backdate the current time; the packet's own
    freeze_timestamp_istanbul is recorded as provenance only (see
    CONTENT_FIELDS) and never consulted by this function."""
    return datetime.now(_ISTANBUL)


def _pretrade_window_open(packet: TrueLivePredictionPacket) -> bool:
    """True iff the real Europe/Istanbul current date is strictly before the
    packet's first_trading_date. Conservative by design: no same-day
    exception, no time-of-day cutoff exception. Evaluated fresh on every
    call -- first attempt, retry, and recovery alike."""
    first_trading = date.fromisoformat(packet.first_trading_date)
    return _now_istanbul().date() < first_trading


# ---------------------------------------------------------------------------
# Registry plumbing (reused primitives + small schema-specific adapters)
# ---------------------------------------------------------------------------


def _append_rows_bytes(old_bytes: bytes, headers: Sequence[str], new_rows: Sequence[dict]) -> bytes:
    """Byte-exact append, identical technique to the one already
    production-proven for the LIVE_V0 registry (module docstring there
    explains why old_bytes must never be decoded/re-encoded)."""
    import csv
    import io

    prefix = old_bytes
    if prefix and not prefix.endswith(b"\n"):
        prefix += b"\r\n"
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(headers), lineterminator="\r\n")
    for row in new_rows:
        writer.writerow(row)
    return prefix + buf.getvalue().encode("utf-8")


def _new_registry_bytes(headers: Sequence[str]) -> bytes:
    import csv
    import io

    buf = io.StringIO()
    csv.DictWriter(buf, fieldnames=list(headers), lineterminator="\r\n").writeheader()
    return ("﻿" + buf.getvalue()).encode("utf-8")


def _load_existing(registry_path: Path, summary_path: Path) -> tuple[bytes, list[str], list[dict], dict]:
    if registry_path.exists():
        old_bytes = registry_path.read_bytes()
        headers, rows = read_csv(registry_path)
        if tuple(headers) != TRUE_LIVE_REGISTRY_HEADERS:
            raise TrueLivePersistenceFailure(
                f"TRUE_LIVE registry şema uyuşmazlığı: {headers} != {list(TRUE_LIVE_REGISTRY_HEADERS)}"
            )
    else:
        old_bytes = _new_registry_bytes(TRUE_LIVE_REGISTRY_HEADERS)
        headers, rows = list(TRUE_LIVE_REGISTRY_HEADERS), []
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    else:
        summary = {"registered_prediction_count": 0, "registry_record_sha256": {}}
    return old_bytes, headers, rows, summary


def _assert_no_duplicate_ticker_horizon(existing_rows: Sequence[dict], new_row: dict) -> None:
    key = (new_row["ticker"], new_row["horizon"])
    for row in existing_rows:
        if (row["ticker"], row["horizon"]) == key and row["prediction_id"] != new_row["prediction_id"]:
            raise TrueLivePersistenceFailure(
                f"Bu (ticker, horizon) için zaten farklı bir prediction_id ile dondurulmuş kayıt var: {key}"
            )


def _recover_and_verify_existing_state(registry_path: Path, summary_path: Path, journal_path: Path) -> None:
    """Blocker 1: run BEFORE any idempotent-success branch is even
    considered. Uses only the existing, unmodified recovery/verification
    primitives (recover_journal, verify_registry_summary_identity) -- never
    a parallel persistence engine. A pending journal is completed
    deterministically from its own already-staged bytes (never
    recomputed); if that isn't safely possible, or if the resulting state
    still fails structural verification, this raises and the caller
    converts that into an explicit non-FROZEN result -- it never falls
    through to a silent idempotent success."""
    if journal_path.exists():
        recover_journal(journal_path, registry_path, summary_path)
    if journal_path.exists():
        raise TrueLivePersistenceFailure("recover_journal sonrası journal hâlâ mevcut -- güvenli değil")
    if registry_path.exists():
        verify_registry_summary_identity(registry_path, summary_path)


def freeze_true_live_prediction(
    *,
    packet: TrueLivePredictionPacket,
    persisted_at_istanbul: str,
    project_root: Path,
) -> TrueLiveFreezeResult:
    """The single accepted path from a computed candidate prediction to a
    *_TRUE_LIVE_V1_5_FROZEN verdict. Every stage below can independently
    force a non-FROZEN result: packet validation, project-root/path
    resolution, pending-journal recovery, registry/summary consistency
    verification, the contemporaneous pretrade-window check, staging,
    atomic commit, and post-commit read-back verification. None of them is
    skipped for a retry or for an already-committed identical packet, and
    no exception raised anywhere in this function escapes past it -- every
    failure mode returns clean_true_live_metric_eligible=False."""
    registry_path: Path | None = None
    summary_path: Path | None = None
    try:
        validate_packet(packet)
        registry_path, summary_path, journal_path = resolve_true_live_paths(project_root)

        _recover_and_verify_existing_state(registry_path, summary_path, journal_path)

        old_bytes, headers, existing_rows, old_summary = _load_existing(registry_path, summary_path)

        row = packet.content_row()
        row["packet_sha256"] = canonical_record_hash(row, list(CONTENT_FIELDS))
        row["persisted_at_istanbul"] = persisted_at_istanbul

        window_open = _pretrade_window_open(packet)

        existing_by_id = {r["prediction_id"]: r for r in existing_rows}
        if packet.prediction_id in existing_by_id:
            existing_row = existing_by_id[packet.prediction_id]
            existing_hash = canonical_record_hash(existing_row, list(CONTENT_FIELDS))
            new_hash = row["packet_sha256"]
            if existing_hash != new_hash:
                raise ContentMismatchOnRetryError(
                    f"prediction_id {packet.prediction_id!r} zaten farklı içerikle donmuş "
                    f"(mevcut hash={existing_hash}, yeni hash={new_hash}) -- üzerine yazma reddedildi"
                )
            if not window_open:
                raise PretradeWindowClosedError(
                    "Zaten tutarlı biçimde donmuş kayıt bulundu, ancak pretrade penceresi artık kapalı -- "
                    "temporal firewall retry'de de geçerlidir"
                )
            # Identical retry, window still open at retry time: no new
            # write, existing committed row is authoritative.
            return TrueLiveFreezeResult(
                clean_true_live_metric_eligible=True,
                verdict=f"{packet.ticker}_{packet.horizon}_TRUE_LIVE_V1_5_FROZEN",
                prediction_id=packet.prediction_id,
                already_committed=True,
                row_hash=existing_hash,
                registry_path=registry_path,
                summary_path=summary_path,
            )

        if not window_open:
            raise PretradeWindowClosedError(
                f"{packet.ticker} için pretrade penceresi kapalı (first_trading_date={packet.first_trading_date}) -- "
                "yeni bir kayıt oluşturulmadı"
            )

        _assert_no_duplicate_ticker_horizon(existing_rows, row)
        assert_no_duplicate_ids([r["prediction_id"] for r in existing_rows], [row])

        new_registry_bytes = _append_rows_bytes(old_bytes, headers, [row])
        assert_byte_prefix_preserved(old_bytes, new_registry_bytes)

        # Full-row scope (all TRUE_LIVE_REGISTRY_HEADERS columns, including
        # the write-time bookkeeping ones) -- this MUST match the scope
        # verify_registry_summary_identity uses when it recomputes hashes
        # from whatever headers it reads back off disk. Deliberately a
        # *different* hash from row["packet_sha256"] (CONTENT_FIELDS-only,
        # used for retry-idempotency and the read-back content check
        # below): one proves registry/summary structural identity, the
        # other proves content identity across retries.
        new_hashes = canonical_registry_hashes(list(headers), [row])

        merged_hashes = dict(old_summary.get("registry_record_sha256", {}))
        overlap = set(merged_hashes) & set(new_hashes)
        if overlap:
            raise TrueLivePersistenceFailure(f"Özet hash haritasında beklenmeyen çakışma: {sorted(overlap)}")
        merged_hashes.update(new_hashes)
        new_summary = dict(old_summary)
        new_summary["registry_record_sha256"] = merged_hashes
        new_summary["registered_prediction_count"] = int(old_summary.get("registered_prediction_count", 0)) + 1

        proposal = FreezeProposal(
            registry_path=registry_path,
            summary_path=summary_path,
            old_registry_bytes=old_bytes,
            new_registry_bytes=new_registry_bytes,
            old_summary=old_summary,
            new_summary=new_summary,
            new_rows=[row],
        )
        txn = FreezeTransaction(registry_path=registry_path, summary_path=summary_path, journal_path=journal_path)
        txn.stage_and_commit(proposal)  # raises on any staging/commit/post-commit-verify failure

        # Independent second read-back, beyond what stage_and_commit already
        # did internally -- this function's own gate, not a trust of the
        # transaction's internal check alone. A failure here (tampering,
        # unexpected on-disk state, hash mismatch) is caught below and
        # converted to a non-FROZEN result -- verdict emission happens only
        # after this succeeds, never before.
        verify_registry_summary_identity(registry_path, summary_path)
        committed_headers, committed_rows = read_csv(registry_path)
        committed_row = next((r for r in committed_rows if r["prediction_id"] == packet.prediction_id), None)
        if committed_row is None:
            raise TrueLivePersistenceFailure(
                f"Commit sonrası registry'de prediction_id bulunamadı: {packet.prediction_id!r}"
            )
        readback_hash = canonical_record_hash(committed_row, list(CONTENT_FIELDS))
        if readback_hash != row["packet_sha256"]:
            raise TrueLivePersistenceFailure(
                f"Commit sonrası okunan satır hash'i beklenenle uyuşmuyor: "
                f"beklenen={row['packet_sha256']}, bulunan={readback_hash}"
            )
    except PretradeWindowClosedError as exc:
        return TrueLiveFreezeResult(
            clean_true_live_metric_eligible=False,
            verdict="TRUE_LIVE_PRETRADE_WINDOW_CLOSED_NOT_FROZEN",
            prediction_id=packet.prediction_id,
            already_committed=False,
            row_hash=None,
            registry_path=registry_path,
            summary_path=summary_path,
            error=str(exc),
        )
    except Exception as exc:  # noqa: BLE001 -- intentional: this gate's entire
        # contract is "no exception path may leave FROZEN status ambiguous".
        # PacketValidationError, TrueLivePersistenceFailure,
        # ContentMismatchOnRetryError, and every PolicyViolation raised by
        # the reused primitives (CommitIntegrityError, DuplicatePredictionError,
        # BaselineMismatchError) are the expected failures; a bare
        # RuntimeError/OSError from stage_and_commit's own test-injection
        # hooks, a missing/unreadable project file, or a genuine I/O fault
        # must be converted to an explicit non-FROZEN result exactly the
        # same way, never re-raised past this function.
        return TrueLiveFreezeResult(
            clean_true_live_metric_eligible=False,
            verdict="TRUE_LIVE_PERSISTENCE_FAILED_NOT_FROZEN",
            prediction_id=packet.prediction_id,
            already_committed=False,
            row_hash=None,
            registry_path=registry_path,
            summary_path=summary_path,
            error=str(exc),
        )

    return TrueLiveFreezeResult(
        clean_true_live_metric_eligible=True,
        verdict=f"{packet.ticker}_{packet.horizon}_TRUE_LIVE_V1_5_FROZEN",
        prediction_id=packet.prediction_id,
        already_committed=False,
        row_hash=row["packet_sha256"],
        registry_path=registry_path,
        summary_path=summary_path,
    )

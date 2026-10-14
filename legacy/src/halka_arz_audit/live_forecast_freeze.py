"""Freeze-only LIVE_V0 EOD_NEXT_DAY primitives.

Deliberately kept separate from live_forecast.py (left byte-unmodified by
task LIVE_V0_FREEZE_ONLY_PLUMBING_FIX_01 -- its source is not hash-pinned by
any protected-source list, but historical source identity is preserved on
principle). This module's own dependency surface is intentionally narrow: it
must never call the sibling module's scoring routine and must never open the
realization file that tracks the LIVE_FORECAST_TRACK's actual-outcome data --
a dedicated boundary test (see tests/test_live_forecast_freeze.py) scans this
file's own source text for the two literal identifiers that would indicate
either dependency and fails if either is present. To keep that scan
meaningful (not merely lexical), this docstring itself does not spell out
either literal name.

Reused, unmodified, from live_forecast.py: sha256, read_csv, load_config,
trading_day_number, canonical_record_hash, verify_protected_sources.

Everything in this module is pure inference / staging / commit plumbing.
Nothing here fits, tunes, or selects a parameter -- every numeric constant
consumed by v0_prediction_values() comes from the caller-supplied frozen
LIVE_V0 config mapping, never from a literal in this file.
"""
from __future__ import annotations

import hashlib
import json
import math
import zipfile
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

from .guards import PolicyViolation
from .live_forecast import (  # noqa: F401  (re-exported for callers)
    canonical_record_hash,
    load_config,
    read_csv,
    sha256,
    trading_day_number,
    verify_protected_sources,
)

# ---------------------------------------------------------------------------
# Summary-file field classification (Part E / boundary enforcement)
# ---------------------------------------------------------------------------

# Keys inside live_performance_summary.json that this module's staged commit
# is permitted to touch -- registry identity/bookkeeping only. Every other
# top-level key must be carried forward byte-for-byte unchanged; a staged
# commit that would need to touch anything outside this set must abort
# rather than silently widen its own footprint.
SUMMARY_INTEGRITY_KEYS = frozenset({
    "registered_prediction_count",
    "registry_record_sha256",
    "registry_sha256",
    "registry_prefix_sha256",
    "registry_prefix_preserved",
    "current_batch",
    "forecast_batch_history",
})

# Keys that must be byte/structurally identical before and after any
# freeze-only commit -- the performance/evaluation surface this module must
# never touch, plus the historical per-batch schedule/EOD keys that only a
# scoring pass may legitimately update.
SUMMARY_FROZEN_KEYS = frozenset({
    "performance",
    "performance_history",
    "performance_by_cutoff_variant",
})


class FreezeOnlyBoundaryError(PolicyViolation):
    """Raised when a proposed summary mutation would touch a key outside
    SUMMARY_INTEGRITY_KEYS, or when SUMMARY_FROZEN_KEYS content would
    change."""


class BaselineMismatchError(PolicyViolation):
    """Raised when the pinned historical baseline (old registry rows) does
    not match the live registry's current content -- signals either an
    already-corrupted live state or a stale/wrong baseline pin. Must abort
    before any staging occurs."""


class DuplicatePredictionError(PolicyViolation):
    """Raised when a proposed new prediction_id collides with an existing
    (baseline or already-frozen) id, or when two proposed new rows collide
    with each other -- detected BEFORE any dict/map collapse that could
    silently keep only one."""


class DuplicateTargetError(PolicyViolation):
    """Raised when a proposed new row targets the exact same
    (ticker, target_trading_date, forecast_target, model_version) tuple as
    an existing row."""


class CommitIntegrityError(PolicyViolation):
    """Raised by post-commit verification when the on-disk state does not
    exactly match what was staged. Never auto-repaired."""


# ---------------------------------------------------------------------------
# Pure LIVE_V0 inference (byte-identical formulas to the ones already used
# for every prior frozen LIVE_V0 batch in scripts/complete_live_cycle_2026_08_11.py
# and scripts/prepare_live_forecast_2026_08_11_actual_timestamp.py -- moved
# here as a reusable, testable unit rather than copy-pasted per one-off
# script. No formula, threshold, or weight is changed.)
# ---------------------------------------------------------------------------


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def format_price(value: float, tick: Decimal) -> str:
    return str(Decimal(str(value)).quantize(tick))


def format_probability(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def v0_prediction_values(
    *, reference: Decimal, previous: Decimal, ipo: Decimal, trading_day: int,
    model: Mapping[str, Any],
) -> dict[str, str]:
    """Pure frozen LIVE_V0 inference. Every constant consulted here
    (`model[...]`) is read from the caller-supplied frozen config mapping --
    this function reads config, it never embeds a parameter value itself."""
    ref = float(reference)
    daily_return = float(reference / previous - Decimal(1))
    change_pct = daily_return * 100.0
    tick = Decimal(str(model["price_tick"]))
    floor = float(model["probability_floor"])
    ceiling = float(model["probability_ceiling"])
    point_raw = ref * (1.0 + float(model["point_momentum_weight"]) * daily_return)
    half_band = ref * (
        float(model["base_band_pct"])
        + float(model["band_abs_daily_return_weight"]) * abs(daily_return)
    )
    predicted_return = point_raw / ref - 1.0
    threshold = float(model["direction_threshold_pct"])
    direction = "UP" if predicted_return > threshold else "DOWN" if predicted_return < -threshold else "FLAT"
    prob_ref = clamp(
        0.5 + float(model["probability_above_reference_slope"]) * daily_return,
        floor, ceiling,
    )
    logistic_input = (point_raw - float(ipo)) / max(half_band, float(tick))
    prob_ipo = clamp(1.0 / (1.0 + math.exp(-logistic_input)), floor, ceiling)
    near = float(model["limit_near_threshold_daily_change_pct"])
    if change_pct >= near:
        prob_up = float(model["limit_near_probability"])
        prob_down = float(model["limit_opposite_probability"])
    elif change_pct <= -near:
        prob_up = float(model["limit_opposite_probability"])
        prob_down = float(model["limit_near_probability"])
    else:
        prob_up = clamp(
            float(model["limit_base_probability"])
            + float(model["limit_positive_change_weight"]) * max(change_pct, 0.0),
            floor, float(model["limit_non_near_cap_probability"]),
        )
        prob_down = clamp(
            float(model["limit_base_probability"])
            + float(model["limit_positive_change_weight"]) * max(-change_pct, 0.0),
            floor, float(model["limit_non_near_cap_probability"]),
        )
    ipo_discount = ref / float(ipo) - 1.0
    if ipo_discount <= float(model["risk_ipo_discount_red_threshold"]) or change_pct <= -near:
        risk = "Kırmızı"
    elif (
        abs(change_pct) >= float(model["risk_absolute_daily_change_orange_threshold_pct"])
        or trading_day <= int(model["risk_early_trading_day_orange_max"])
    ):
        risk = "Turuncu"
    else:
        risk = "Sarı"
    return {
        "direction_prediction": direction,
        "lower_bound": format_price(point_raw - half_band, tick),
        "upper_bound": format_price(point_raw + half_band, tick),
        "point_prediction": format_price(point_raw, tick),
        "prob_above_reference": format_probability(prob_ref),
        "prob_above_ipo": format_probability(prob_ipo),
        "prob_limit_up": format_probability(prob_up),
        "prob_limit_down": format_probability(prob_down),
        "risk_label": risk,
        "confidence": str(model["confidence"]),
    }


# ---------------------------------------------------------------------------
# Official reference input loading (identity/EOD fields only -- no
# realization of the TARGET session is ever read by this function; it loads
# the REFERENCE session, which by construction is required to be at or
# before the freeze's own data-cutoff timestamp -- enforced by the caller,
# see FreezePreflight.check_cutoff_ordering).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OfficialReferenceRow:
    ticker: str
    trade_date: str
    close: Decimal
    previous_close: Decimal
    raw_row: Mapping[str, str]


def load_official_reference_rows(
    *, archive_path: Path, expected_sha256: str, expected_trade_date: str,
    tickers: Sequence[str],
) -> dict[str, OfficialReferenceRow]:
    """Deterministic, generic re-implementation of the official-bulletin
    parsing pattern already used for every prior frozen LIVE_V0 batch
    (cp1254-encoded, ';'-delimited BIST bulletin CSV inside a single-entry
    ZIP). Generalized over ticker list / expected date / archive path --
    no ticker or date is hardcoded here."""
    if not archive_path.is_file():
        raise PolicyViolation(f"Resmi EOD arşivi bulunamadı: {archive_path}")
    actual_hash = sha256(archive_path)
    if actual_hash != expected_sha256:
        raise PolicyViolation(
            f"Resmi EOD arşivi SHA-256 uyuşmuyor: beklenen={expected_sha256}, bulunan={actual_hash}"
        )
    wanted = set(tickers)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != 1:
            raise PolicyViolation(f"Beklenmeyen resmi ZIP içeriği: {names}")
        with archive.open(names[0]) as raw:
            lines = (line.decode("cp1254").rstrip("\r\n") for line in raw)
            header = next(lines).split(";")
            next(lines)  # English header line, not used for matching
            if header[0] != "TARIH":
                raise PolicyViolation("Resmi bülten başlığı beklenen şemada değil")
            rows: dict[str, OfficialReferenceRow] = {}
            for line in lines:
                if not line:
                    continue
                values = line.split(";")
                row = dict(zip(header, values, strict=True))
                code = row.get("ISLEM  KODU", "")
                ticker = code.removesuffix(".E")
                if ticker not in wanted:
                    continue
                if ticker in rows:
                    raise PolicyViolation(f"Resmi bültende duplicate ticker: {ticker}")
                if row["TARIH"] != expected_trade_date:
                    raise PolicyViolation(
                        f"Resmi bülten tarihi beklenenle uyuşmuyor: {ticker} -> {row['TARIH']!r} != {expected_trade_date!r}"
                    )
                rows[ticker] = OfficialReferenceRow(
                    ticker=ticker, trade_date=row["TARIH"],
                    close=Decimal(row["KAPANIS FIYATI"].replace(",", ".")),
                    previous_close=Decimal(row["ONCEKI KAPANIS FIYATI"].replace(",", ".")),
                    raw_row=row,
                )
    missing = wanted - set(rows)
    if missing:
        raise PolicyViolation(f"Resmi bültende hedef ticker eksik: {sorted(missing)}")
    return rows


# ---------------------------------------------------------------------------
# Duplicate / target checks (Part C responsibility 5)
# ---------------------------------------------------------------------------


def assert_no_duplicate_ids(existing_ids: Sequence[str], new_rows: Sequence[Mapping[str, str]]) -> None:
    new_ids = [row["prediction_id"] for row in new_rows]
    seen: set[str] = set()
    for pid in new_ids:
        if pid in seen:
            raise DuplicatePredictionError(f"Yeni satırlar arasında duplicate prediction_id: {pid}")
        seen.add(pid)
    collisions = seen & set(existing_ids)
    if collisions:
        raise DuplicatePredictionError(f"Yeni prediction_id mevcut registry ile çakışıyor: {sorted(collisions)}")


def assert_no_duplicate_targets(
    existing_rows: Sequence[Mapping[str, str]], new_rows: Sequence[Mapping[str, str]],
) -> None:
    def key(row: Mapping[str, str]) -> tuple[str, str, str, str]:
        return (row["ticker"], row["target_trading_date"], row["forecast_target"], row["model_version"])

    existing_keys = {key(row) for row in existing_rows}
    seen: set[tuple[str, str, str, str]] = set()
    for row in new_rows:
        k = key(row)
        if k in existing_keys:
            raise DuplicateTargetError(f"Hedef zaten donmuş registry'de var: {k}")
        if k in seen:
            raise DuplicateTargetError(f"Yeni satırlar arasında duplicate hedef: {k}")
        seen.add(k)


# ---------------------------------------------------------------------------
# Registry / summary staging + crash-safe commit
# ---------------------------------------------------------------------------


def canonical_registry_hashes(headers: Sequence[str], rows: Sequence[Mapping[str, str]]) -> dict[str, str]:
    return {row["prediction_id"]: canonical_record_hash(row, headers) for row in rows}


@dataclass
class FreezeProposal:
    """Fully-computed in-memory proposed next state. Nothing here has been
    written to disk yet."""
    registry_path: Path
    summary_path: Path
    old_registry_bytes: bytes
    new_registry_bytes: bytes
    old_summary: dict[str, Any]
    new_summary: dict[str, Any]
    new_rows: list[dict[str, str]] = field(default_factory=list)


def build_new_summary(
    old_summary: Mapping[str, Any], *, new_registry_bytes: bytes, old_registry_bytes: bytes,
    new_row_hashes: Mapping[str, str], batch_record: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a new summary dict identical to old_summary except for the
    keys in SUMMARY_INTEGRITY_KEYS. Every key outside that set -- most
    importantly every key in SUMMARY_FROZEN_KEYS -- is carried over via
    identity copy, never recomputed."""
    new_summary = dict(old_summary)
    merged_hashes = dict(old_summary.get("registry_record_sha256", {}))
    overlap = set(merged_hashes) & set(new_row_hashes)
    if overlap:
        raise DuplicatePredictionError(f"Yeni hash anahtarları mevcutla çakışıyor: {sorted(overlap)}")
    merged_hashes.update(new_row_hashes)
    new_summary["registry_record_sha256"] = merged_hashes
    new_summary["registry_sha256"] = hashlib.sha256(new_registry_bytes).hexdigest()
    new_summary["registry_prefix_sha256"] = hashlib.sha256(old_registry_bytes).hexdigest()
    new_summary["registry_prefix_preserved"] = True
    new_summary["registered_prediction_count"] = (
        int(old_summary.get("registered_prediction_count", 0)) + len(new_row_hashes)
    )
    new_summary["current_batch"] = dict(batch_record)
    new_summary["forecast_batch_history"] = [
        *old_summary.get("forecast_batch_history", []), dict(batch_record),
    ]
    return new_summary


def assert_summary_boundary_respected(old_summary: Mapping[str, Any], new_summary: Mapping[str, Any]) -> None:
    """Structural proof that no key outside SUMMARY_INTEGRITY_KEYS changed,
    and that every SUMMARY_FROZEN_KEYS subtree is byte-identical (via
    canonical JSON comparison) before and after."""
    old_keys = set(old_summary)
    new_keys = set(new_summary)
    unexpected_new = new_keys - old_keys
    if unexpected_new:
        raise FreezeOnlyBoundaryError(f"Yeni özet beklenmeyen üst-düzey anahtar içeriyor: {sorted(unexpected_new)}")
    for key in old_keys:
        if key in SUMMARY_INTEGRITY_KEYS:
            continue
        old_val = old_summary[key]
        new_val = new_summary.get(key)
        if json.dumps(old_val, sort_keys=True, ensure_ascii=False) != json.dumps(new_val, sort_keys=True, ensure_ascii=False):
            raise FreezeOnlyBoundaryError(
                f"Freeze-only commit izin verilen bütünlük alanları dışında bir alanı değiştirdi: {key!r}"
            )
    for key in SUMMARY_FROZEN_KEYS:
        if key in old_summary and old_summary[key] != new_summary.get(key):
            raise FreezeOnlyBoundaryError(f"Dondurulmuş alt-ağaç değişti: {key!r}")


def assert_baseline_unmutated(
    baseline_hashes: Mapping[str, str], current_registry_headers: Sequence[str],
    current_registry_rows: Sequence[Mapping[str, str]],
) -> None:
    """BaselineMismatchError if any pinned baseline row's canonical hash no
    longer matches the live registry -- must run BEFORE any staging."""
    current_hashes = canonical_registry_hashes(current_registry_headers, current_registry_rows)
    missing = set(baseline_hashes) - set(current_hashes)
    if missing:
        raise BaselineMismatchError(f"Pinlenmiş temel satırlar canlı registry'de bulunamadı: {sorted(missing)}")
    changed = {
        pid: (expected, current_hashes[pid])
        for pid, expected in baseline_hashes.items()
        if current_hashes[pid] != expected
    }
    if changed:
        raise BaselineMismatchError(f"Pinlenmiş temel satır(lar) mutasyona uğramış: {changed}")


def assert_byte_prefix_preserved(old_bytes: bytes, new_bytes: bytes) -> None:
    if not new_bytes.startswith(old_bytes):
        raise CommitIntegrityError(
            "Yeni registry dosyası eski dosyanın byte-prefix'i değil -- append-only ihlali"
        )


# ---------------------------------------------------------------------------
# Crash-safe staged commit
# ---------------------------------------------------------------------------


@dataclass
class FreezeTransaction:
    registry_path: Path
    summary_path: Path
    journal_path: Path

    def stage_and_commit(
        self, proposal: FreezeProposal, *, fail_after_stage: bool = False,
        fail_after_registry_commit: bool = False,
    ) -> None:
        """Write both targets via atomic temp-file replace, guarded by a
        journal file that records exactly what was staged so a crash
        between the two renames is detectable (never silently accepted as
        healthy) on the next verification pass.

        `fail_after_stage` / `fail_after_registry_commit` exist only to let
        tests inject a forced failure at each specific point in the
        sequence; production callers never set them."""
        registry_tmp = self.registry_path.with_suffix(self.registry_path.suffix + ".freezetmp")
        summary_tmp = self.summary_path.with_suffix(self.summary_path.suffix + ".freezetmp")

        registry_tmp.write_bytes(proposal.new_registry_bytes)
        summary_text = json.dumps(proposal.new_summary, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
        # newline="" disables Path.write_text's platform newline translation
        # (which would otherwise silently rewrite every embedded "\n" in the
        # JSON indent output to "\r\n" on Windows) -- without it, the
        # immediate post-write hash re-check three lines below would fail
        # non-deterministically depending on OS, comparing a CRLF-translated
        # on-disk byte stream against an LF-only in-memory expected hash.
        summary_tmp.write_text(summary_text, encoding="utf-8", newline="")

        staged_registry_hash = hashlib.sha256(registry_tmp.read_bytes()).hexdigest()
        staged_summary_hash = hashlib.sha256(summary_tmp.read_bytes()).hexdigest()
        expected_registry_hash = hashlib.sha256(proposal.new_registry_bytes).hexdigest()
        expected_summary_hash = hashlib.sha256(summary_text.encode("utf-8")).hexdigest()
        if staged_registry_hash != expected_registry_hash or staged_summary_hash != expected_summary_hash:
            registry_tmp.unlink(missing_ok=True)
            summary_tmp.unlink(missing_ok=True)
            raise CommitIntegrityError("Staged dosyalar beklenen içerikle eşleşmiyor -- commit iptal edildi")

        journal = {
            "state": "PREPARED",
            "registry_path": str(self.registry_path),
            "summary_path": str(self.summary_path),
            "pre_registry_sha256": hashlib.sha256(proposal.old_registry_bytes).hexdigest(),
            "pre_summary_sha256": hashlib.sha256(
                json.dumps(proposal.old_summary, ensure_ascii=False, indent=2, sort_keys=False).encode("utf-8")
                + b"\n"
            ).hexdigest(),
            "staged_registry_sha256": staged_registry_hash,
            "staged_summary_sha256": staged_summary_hash,
        }
        self.journal_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8", newline="")

        if fail_after_stage:
            raise RuntimeError("INJECTED_TEST_FAILURE_AFTER_STAGE")

        registry_tmp.replace(self.registry_path)
        journal["state"] = "REGISTRY_COMMITTED"
        self.journal_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8", newline="")

        if fail_after_registry_commit:
            raise RuntimeError("INJECTED_TEST_FAILURE_AFTER_REGISTRY_COMMIT")

        summary_tmp.replace(self.summary_path)
        journal["state"] = "COMMITTED"
        self.journal_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8", newline="")

        verify_post_commit(
            self.registry_path, self.summary_path,
            expected_registry_sha256=staged_registry_hash,
            expected_summary_sha256=staged_summary_hash,
        )
        self.journal_path.unlink(missing_ok=True)


def verify_post_commit(
    registry_path: Path, summary_path: Path, *, expected_registry_sha256: str, expected_summary_sha256: str,
) -> None:
    actual_registry = sha256(registry_path)
    actual_summary = sha256(summary_path)
    if actual_registry != expected_registry_sha256:
        raise CommitIntegrityError(
            f"Commit sonrası registry SHA-256 uyuşmuyor: beklenen={expected_registry_sha256}, bulunan={actual_registry}"
        )
    if actual_summary != expected_summary_sha256:
        raise CommitIntegrityError(
            f"Commit sonrası özet SHA-256 uyuşmuyor: beklenen={expected_summary_sha256}, bulunan={actual_summary}"
        )
    verify_registry_summary_identity(registry_path, summary_path)


def verify_registry_summary_identity(registry_path: Path, summary_path: Path) -> None:
    """The invariant that must hold for ANY healthy state, committed or not:
    the registry's prediction_id set exactly equals the summary's
    registry_record_sha256 key set, and every canonical row hash matches its
    registered hash. A crash that lands between the two renames leaves this
    check failing -- by construction it can never validate as healthy."""
    headers, rows = read_csv(registry_path)
    registry_ids = [row["prediction_id"] for row in rows]
    if len(registry_ids) != len(set(registry_ids)):
        dupes = sorted({pid for pid in registry_ids if registry_ids.count(pid) > 1})
        raise CommitIntegrityError(f"Registry'de duplicate prediction_id bulundu: {dupes}")
    if any(not pid for pid in registry_ids):
        raise CommitIntegrityError("Registry'de boş prediction_id bulundu")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary_hashes = summary.get("registry_record_sha256", {})
    registry_id_set = set(registry_ids)
    summary_id_set = set(summary_hashes)
    missing_in_summary = registry_id_set - summary_id_set
    extra_in_summary = summary_id_set - registry_id_set
    if missing_in_summary:
        raise CommitIntegrityError(f"Registry satırları özet hash haritasında eksik: {sorted(missing_in_summary)}")
    if extra_in_summary:
        raise CommitIntegrityError(f"Özet hash haritasında registry'de olmayan fazladan anahtar: {sorted(extra_in_summary)}")
    current_hashes = canonical_registry_hashes(headers, rows)
    wrong = {
        pid: (summary_hashes[pid], current_hashes[pid])
        for pid in registry_id_set
        if summary_hashes[pid] != current_hashes[pid]
    }
    if wrong:
        raise CommitIntegrityError(f"Registry/özet hash uyuşmazlığı: {wrong}")


def recover_journal(journal_path: Path, registry_path: Path, summary_path: Path) -> str:
    """Given a journal left behind by an interrupted stage_and_commit, either
    finishes the commit using the ALREADY-STAGED bytes (never recomputes
    inference) or reports that no recovery is possible/needed. Returns a
    short status string. This function performs the minimal deterministic
    completion described in journal['state']; it never invents new content."""
    if not journal_path.exists():
        return "NO_JOURNAL_PRESENT"
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    registry_tmp = registry_path.with_suffix(registry_path.suffix + ".freezetmp")
    summary_tmp = summary_path.with_suffix(summary_path.suffix + ".freezetmp")
    state = journal["state"]
    if state == "PREPARED":
        # Neither target was renamed. Both current files are still the
        # pre-transaction state (or absent tmp files) -- safe to discard.
        registry_tmp.unlink(missing_ok=True)
        summary_tmp.unlink(missing_ok=True)
        journal_path.unlink(missing_ok=True)
        return "DISCARDED_UNCOMMITTED_STAGE"
    if state == "REGISTRY_COMMITTED":
        # Registry was renamed; summary was not. Complete deterministically
        # using the already-staged summary bytes (no recomputation).
        if not summary_tmp.exists():
            raise CommitIntegrityError(
                "Journal REGISTRY_COMMITTED durumda ama staged özet dosyası artık yok -- otomatik onarım güvenli değil"
            )
        if sha256(registry_path) != journal["staged_registry_sha256"]:
            raise CommitIntegrityError("Kurtarma: registry dosyası journal'daki staged hash ile eşleşmiyor")
        summary_tmp.replace(summary_path)
        if sha256(summary_path) != journal["staged_summary_sha256"]:
            raise CommitIntegrityError("Kurtarma sonrası özet hash uyuşmuyor")
        journal_path.unlink(missing_ok=True)
        return "COMPLETED_FROM_REGISTRY_COMMITTED"
    if state == "COMMITTED":
        journal_path.unlink(missing_ok=True)
        return "ALREADY_COMMITTED_JOURNAL_CLEARED"
    raise CommitIntegrityError(f"Bilinmeyen journal durumu: {state!r}")

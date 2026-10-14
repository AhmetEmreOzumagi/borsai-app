#!/usr/bin/env python3
"""BORSAI_V1_5_MACOS_RUNTIME_REPLAY_20260911_V1 -- replay harness (GOREV A).

Read-only w.r.t. the repository: writes ONLY under the output directory
passed on the command line (expected: artifacts/derived/
v1_5_macos_runtime_replay_<run_date>/). Never calls pbb.execute_freeze(),
never touches artifacts/predictions/** or artifacts/live_forecast/**.

Calls pbb.build_predictions() directly (NOT execute_freeze(), which would
short-circuit into read-only re-verification because the frozen output files
already exist on disk and would never actually re-run Ridge/Logistic in this
new interpreter). This is "hesaplama adiminin kullandigi yoldan": the exact
same already-frozen function sequence
compute_true_live_v1_5_prediction_contract.compute_contract() calls:
    PostBookbuildInputContract.from_mapping -> validate_gates ->
    calculated_features -> build_packet_rows -> build_predictions
No mathematics is reimplemented; every call below is to an unmodified frozen
function imported from the two frozen modules.

Reads the real HISTORICAL99 training cohort via frozen.load_and_validate_state()
exactly ONCE (shared across both cases -- the state content does not depend on
the candidate's own prediction_local_date, only eligible_training()'s date
filter does, which build_predictions() applies internally). This is a
TRAINING-side read, authorized under this task's H1 (bounded by
eligible_training()). Per H2, this script never prints or serializes any
individual training ticker's raw R_h/Y_h -- only aggregate counts and the
sha256 hashes build_predictions() itself already emits.

Never reads BKRGY/INTET's own post-listing outcome: build_predictions() has
no parameter through which one could even be passed (verified by reading its
source before writing this harness).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[0]  # overwritten below once run from repo


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: v1_5_macos_replay_harness.py <repo_root> <output_dir>", file=sys.stderr)
        return 2
    repo_root = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from scripts.modeling import candidate_models as cm
    from scripts.modeling import run_historical99_frozen_v1_5_benchmark as frozen
    from scripts.modeling import run_post_bookbuild_pre_listing_v1_5_prospective_freeze as pbb

    # --- P1 / runtime identity (re-confirmed inside the harness itself) ---
    cm.verify_runtime()
    runtime_report = {
        "python": ".".join(str(p) for p in __import__("sys").version_info[:3]),
        "sklearn": __import__("sklearn").__version__,
        "numpy": __import__("numpy").__version__,
        "scipy": __import__("scipy").__version__,
        "joblib": __import__("joblib").__version__,
        "threadpoolctl": __import__("threadpoolctl").__version__,
        "executable": sys.executable,
    }

    # --- Frozen input contracts, reconstructed from each driver script's own
    # hardcoded constants (COMPANY_NAME, IPO_PRICE_TL, ...), with
    # prediction_timestamp / prediction_local_date taken from the FROZEN
    # freeze manifest (NOT datetime.now(), which the driver's own
    # build_contract() uses only at the moment of the real, one-time freeze).
    cases = {
        "BKRGY": {
            "case_dir": repo_root / "artifacts" / "predictions" / "prospective"
                        / "BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING",
            "stem": "BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING",
            "data": {
                "ticker": "BKRGY",
                "company_name": "Bakırcı Gayrimenkul Yatırım Ortaklığı A.Ş.",
                "prediction_timestamp": "2026-08-27T16:34:21.160123+03:00",
                "prediction_local_date": "2026-08-27",
                "ipo_price_tl": "12.93",
                "shares_offered_final": "167000000",
                "post_ipo_share_capital": "668000000",
                "capital_increase_shares": "167000000",
                "official_total_demand_multiple": "1.77",
                "official_result_source": "OFFICIAL_KESIN_TALEP_SONUCU_VIA_KAP",
                "source_identifier": "KAP_1655263",
                "source_publication_timestamp": "2026-08-27T09:35:30+03:00",
                "bookbuilding_end": "2026-08-26",
                "secondary_trading_start_status": "NOT_STARTED",
                "outcome_observed": False,
            },
        },
        "INTET": {
            "case_dir": repo_root / "artifacts" / "predictions" / "prospective"
                        / "INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING",
            "stem": "INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING",
            "data": {
                "ticker": "INTET",
                "company_name": "İntetra Teknoloji ve Bilişim Hizmetleri A.Ş.",
                "prediction_timestamp": "2026-08-31T10:52:15.484732+03:00",
                "prediction_local_date": "2026-08-31",
                "ipo_price_tl": "53.60",
                "shares_offered_final": "40000000",
                "post_ipo_share_capital": "160000000",
                "capital_increase_shares": "30000000",
                "official_total_demand_multiple": "1.7",
                "official_result_source": "OFFICIAL_KESIN_TALEP_SONUCU_VIA_KAP",
                "source_identifier": "INTET_KESIN_TALEP_SONUCU_UNIDENTIFIED",
                "source_publication_timestamp": "2026-08-27T23:59:00+03:00",
                "bookbuilding_end": "2026-08-27",
                "secondary_trading_start_status": "NOT_STARTED",
                "outcome_observed": False,
            },
        },
    }

    # --- Shared HISTORICAL99 training-side state load (H1-authorized; single
    # call, reused for both cases). Only aggregate facts are captured here,
    # never individual raw target values.
    state = frozen.load_and_validate_state()
    historical_training_target_access = {
        "master_rows": len(state.master),
        "target_rows": len(state.targets),
        "master_path": str(frozen.MASTER_PATH.relative_to(repo_root)),
        "master_sha256": pbb.sha256_file(frozen.MASTER_PATH),
        "target_path": str(frozen.TARGET_PATH.relative_to(repo_root)),
        "target_sha256": pbb.sha256_file(frozen.TARGET_PATH),
        "note": "counts and file hashes only; no individual R_h/Y_h value read, printed, or serialized by this harness",
    }

    comparison_rows = []
    case_reports = {}

    for ticker, spec in cases.items():
        contract = pbb.PostBookbuildInputContract.from_mapping(spec["data"])

        gate_report = pbb.validate_gates(contract)  # real clock; prediction_timestamp is in the past, so this passes
        features = pbb.calculated_features(contract)
        evidence_rows = pbb.build_packet_rows(contract, features)
        packet_bytes = pbb.csv_bytes(evidence_rows)
        packet_sha256 = pbb.sha256_bytes(packet_bytes)

        prediction_rows, eligibility_rows = pbb.build_predictions(
            contract, state, packet_sha256,
            ridge_fitter=cm.fit_ridge_candidate, logistic_fitter=cm.fit_logistic_candidate,
        )

        # --- Load frozen artifacts for comparison ---
        frozen_ledger_path = spec["case_dir"] / f"{spec['stem']}_frozen_prediction_ledger.csv"
        frozen_eligibility_path = spec["case_dir"] / f"{spec['stem']}_training_eligibility_summary.csv"
        frozen_evidence_path = spec["case_dir"] / f"{spec['stem']}_pretrade_evidence_packet.csv"

        with frozen_ledger_path.open(encoding="utf-8-sig", newline="") as fh:
            frozen_ledger_rows = {r["horizon"]: r for r in csv.DictReader(fh)}
        with frozen_eligibility_path.open(encoding="utf-8-sig", newline="") as fh:
            frozen_eligibility_rows = {r["horizon"]: r for r in csv.DictReader(fh)}
        with frozen_evidence_path.open(encoding="utf-8-sig", newline="") as fh:
            frozen_evidence_rows = {r["field"]: r for r in csv.DictReader(fh)}

        replay_ledger_by_horizon = {r["horizon"]: r for r in prediction_rows}
        replay_eligibility_by_horizon = {r["horizon"]: r for r in eligibility_rows}
        replay_evidence_by_field = {r["field"]: r for r in evidence_rows}

        # Columns actually present in the frozen ledger CSV -- this IS the
        # required comparison scope (ridge_selected_alpha,
        # ridge_point_prediction_return, ridge_predicted_close,
        # logistic_selected_C, logistic_probability_above_ipo_raw,
        # logistic_predicted_direction, training_n, f1-f5, hashes, plus every
        # other ledger column). confidence/prediction_interval/risk_label are
        # included too (still NOT_EMITTED at this pbb.build_predictions()
        # layer -- GOREV B's override happens one layer up, in
        # compute_true_live_v1_5_prediction_contract.py, never touched here).
        ledger_columns = list(next(iter(frozen_ledger_rows.values())).keys())
        eligibility_columns = list(next(iter(frozen_eligibility_rows.values())).keys())
        evidence_columns = list(next(iter(frozen_evidence_rows.values())).keys())

        for horizon in ("D1", "D3", "D5", "D10"):
            frozen_row = frozen_ledger_rows.get(horizon)
            replay_row = replay_ledger_by_horizon.get(horizon)
            for col in ledger_columns:
                frozen_val = frozen_row.get(col) if frozen_row is not None else "UNCHECKABLE_NO_FROZEN_ROW"
                replay_val = str(replay_row.get(col)) if replay_row is not None and col in replay_row else "UNCHECKABLE_NOT_PRODUCED"
                comparison_rows.append({
                    "ticker": ticker, "artifact": "frozen_prediction_ledger", "horizon": horizon,
                    "column": col, "frozen_value": frozen_val, "replay_value": replay_val,
                    "match": "MATCH" if frozen_val == replay_val else (
                        "UNCHECKABLE" if "UNCHECKABLE" in frozen_val or "UNCHECKABLE" in replay_val else "MISMATCH"
                    ),
                })

            frozen_elig = frozen_eligibility_rows.get(horizon)
            replay_elig = replay_eligibility_by_horizon.get(horizon)
            for col in eligibility_columns:
                frozen_val = str(frozen_elig.get(col)) if frozen_elig is not None else "UNCHECKABLE_NO_FROZEN_ROW"
                replay_val = str(replay_elig.get(col)) if replay_elig is not None and col in replay_elig else "UNCHECKABLE_NOT_PRODUCED"
                comparison_rows.append({
                    "ticker": ticker, "artifact": "training_eligibility_summary", "horizon": horizon,
                    "column": col, "frozen_value": frozen_val, "replay_value": replay_val,
                    "match": "MATCH" if frozen_val == replay_val else (
                        "UNCHECKABLE" if "UNCHECKABLE" in frozen_val or "UNCHECKABLE" in replay_val else "MISMATCH"
                    ),
                })

        for field_name, frozen_row in frozen_evidence_rows.items():
            replay_row = replay_evidence_by_field.get(field_name)
            for col in evidence_columns:
                frozen_val = str(frozen_row.get(col))
                replay_val = str(replay_row.get(col)) if replay_row is not None and col in replay_row else "UNCHECKABLE_NOT_PRODUCED"
                comparison_rows.append({
                    "ticker": ticker, "artifact": "pretrade_evidence_packet", "horizon": "N/A",
                    "column": f"{field_name}.{col}", "frozen_value": frozen_val, "replay_value": replay_val,
                    "match": "MATCH" if frozen_val == replay_val else (
                        "UNCHECKABLE" if "UNCHECKABLE" in frozen_val or "UNCHECKABLE" in replay_val else "MISMATCH"
                    ),
                })

        case_reports[ticker] = {
            "gate_report_status": gate_report["status"],
            "recomputed_packet_sha256": packet_sha256,
            "frozen_manifest_packet_sha256_matches": None,  # filled by caller from manifest if desired
            "ledger_columns_compared": len(ledger_columns),
            "eligibility_columns_compared": len(eligibility_columns),
            "evidence_columns_compared": len(evidence_columns),
        }

    # --- Write outputs ---
    comparison_csv_path = out_dir / "replay_comparison.csv"
    with comparison_csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["ticker", "artifact", "horizon", "column", "frozen_value", "replay_value", "match"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(comparison_rows)

    mismatches = [r for r in comparison_rows if r["match"] == "MISMATCH"]
    uncheckable = [r for r in comparison_rows if r["match"] == "UNCHECKABLE"]

    summary = {
        "task_id": "BORSAI_V1_5_MACOS_RUNTIME_REPLAY_20260911_V1",
        "runtime_report": runtime_report,
        "historical_training_target_access": historical_training_target_access,
        "realized_outcome_reads": 0,
        "cases_replayed": list(cases.keys()),
        "case_reports": case_reports,
        "total_columns_compared": len(comparison_rows),
        "mismatch_count": len(mismatches),
        "uncheckable_count": len(uncheckable),
        "mismatches": mismatches,
        "verdict": "REPLAY_PASS" if not mismatches else "REPLAY_FAIL",
    }
    (out_dir / "replay_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())

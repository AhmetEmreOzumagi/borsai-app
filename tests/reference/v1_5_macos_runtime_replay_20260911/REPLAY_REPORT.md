# BORSAI_V1_5_MACOS_RUNTIME_REPLAY_20260911_V1 -- replay report

Run date: 2026-09-11, Europe/Istanbul. HARD STOP encountered during GOREV A;
GOREV B/C not executed (see main task report for the full P0-P6 record and
the HARD STOP rationale).

## Method

`v1_5_macos_replay_harness.py` reconstructs the frozen `PostBookbuildInputContract`
for BKRGY and INTET from each ticker's own driver script's hardcoded constants
(`scripts/modeling/run_bkrgy_post_bookbuild_pre_listing_v1_5_prospective_freeze.py`,
`scripts/modeling/run_intet_post_bookbuild_pre_listing_v1_5_prospective_freeze.py`),
substituting each case's FROZEN `prediction_timestamp` / `prediction_local_date`
(read from that case's own `..._prediction_freeze_manifest.json`) in place of
the driver's own `datetime.now()` call (which is only correct at the one real,
historical moment of freezing). It then calls, unmodified, exactly the
function sequence `compute_true_live_v1_5_prediction_contract.compute_contract()`
uses: `PostBookbuildInputContract.from_mapping -> validate_gates ->
calculated_features -> build_packet_rows -> build_predictions`, under the new
macOS `.venv-v1_5-model-macos` interpreter (Python 3.12.14 / scikit-learn
1.9.0 / numpy 2.5.2 / scipy 1.18.0 / joblib 1.5.3 / threadpoolctl 3.6.0 --
verify_runtime() PASS). `execute_freeze()` was deliberately NOT called: its
output paths already exist on disk, so it would take the read-only
`_reverify_existing_freeze` branch and never actually re-run Ridge/Logistic in
this interpreter at all.

`frozen.load_and_validate_state()` (the HISTORICAL99 training-side read) was
called exactly once, shared across both cases, authorized under this task's
H1. Only aggregate counts and file hashes were captured from it; no
individual ticker's raw R_h/Y_h was read, printed, or serialized anywhere in
this harness or its outputs (H2). BKRGY/INTET's own post-listing data was
never read -- `build_predictions()` has no parameter through which it could
be (verified by reading its source before writing this harness).

## Result

688 columns compared across both cases' `frozen_prediction_ledger.csv`,
`training_eligibility_summary.csv`, and `pretrade_evidence_packet.csv`
(comparison scope: every column present in each frozen CSV, matched by
ticker+horizon or ticker+field; see `replay_comparison.csv` for the full
row-by-row table). **9 mismatches, 0 uncheckable.**

All 9 mismatches are last-1-to-2-significant-digit floating point
differences (of ~17 significant digits rendered) in three columns only:

| ticker | horizon | column | frozen | replay |
|---|---|---|---|---|
| BKRGY | D1 | ridge_point_prediction_return | 0.066104265198569254 | 0.066104265198569268 |
| BKRGY | D3 | ridge_point_prediction_return | 0.1432792430364192 | 0.14327924303641923 |
| BKRGY | D3 | logistic_probability_above_ipo_raw | 0.69801187368060746 | 0.69801187368060735 |
| BKRGY | D5 | ridge_point_prediction_return | 0.16834151533215258 | 0.16834151533215264 |
| BKRGY | D10 | ridge_point_prediction_return | 0.063650349829948771 | 0.063650349829948716 |
| INTET | D5 | ridge_point_prediction_return | 0.17523359058729854 | 0.17523359058729848 |
| INTET | D10 | ridge_point_prediction_return | 0.11657961915696524 | 0.11657961915696513 |
| INTET | D10 | ridge_predicted_close | 59.848667586813342 | 59.848667586813328 |
| INTET | D10 | logistic_probability_above_ipo_raw | 0.46957214414699289 | 0.469572144146993 |

Every other compared column matched byte-for-byte, including:
`ridge_selected_alpha`, `logistic_selected_C`, `logistic_predicted_direction`,
`training_n`, `training_tickers_sha256`, `training_targets_sha256`, `f1`-`f5`,
`ipo_price`, `ridge_model_id`, `ridge_status`, `logistic_model_id`,
`logistic_status`, `model_version`, `feature_schema_version`,
`feature_set_identity`, `preprocessing_identity`, `pretrade_packet_sha256`,
`confidence`, `prediction_interval`, `risk_label`, every
`training_eligibility_summary.csv` column, and every
`pretrade_evidence_packet.csv` column.

## Disposition

Per this task's own HARD STOP rule ("Replay'de herhangi bir sutun uyusmuyor.
Fark tablosunu raporla; tolerans UYGULAMA, 'yuvarlama' ya da 'onemsiz' etiketi
KOYMA."), this is reported as-is: a MISMATCH, not rounding, not
insignificant, and no tolerance was applied. No judgment is offered here on
whether the discrepancy stems from the frozen manifest's own pre-declared
`cross_machine_bit_level_reproducibility_claimed: false` scope note
(`V1_5_RUNTIME_MANIFEST.json`) -- that interpretation is out of this
MECHANICAL task's scope and is left to a governance decision.

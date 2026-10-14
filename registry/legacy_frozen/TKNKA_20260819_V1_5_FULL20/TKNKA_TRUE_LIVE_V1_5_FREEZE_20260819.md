TKNKA — TRUE_LIVE V1.5 Bridge Validation and Freeze
BORSAI_TKNKA_TRUE_LIVE_V1_5_BRIDGE_AND_FREEZE_READONLY_01 · read-only · no web · no agents · no repository writes · no TKNKA outcome access

FREEZE TIMESTAMP (Europe/Istanbul): 2026-08-19T14:48:53+03:00 (2026-08-19T11:48:53Z)

Once printed, this packet is not revised. No later market outcome may alter it.

This is a research-methodology record produced by re-fitting a preregistered statistical model on historical data. It contains no investment recommendation, no position sizing, and no buy/sell instruction. I am not a licensed financial adviser. TKNKA has not traded; every number below is a model output conditioned on pretrade information only, not a market fact.

A. Execution Bridge Verdict
TRUE_LIVE_EXECUTION_BRIDGE_PASS

run_candidate_historical_pilot.py was not used or modified (its own docstring: "never live/frozen OOS evidence"). No repository file was created or edited. The bridge is a single ephemeral python - process, piped via stdin to .venv-v1_5-model\Scripts\python.exe, that imports the frozen pure functions unmodified and calls them once per horizon. No custom Ridge/Logistic math; both estimators are sklearn.linear_model.Ridge / sklearn.linear_model.LogisticRegression, constructed and called exactly as scripts/modeling/candidate_models.py already does internally.

Authorization basis, stated explicitly. scripts/modeling/candidate_models.py's own docstring records that running it against real FULL20-derived targets is "a separate, still-gated task" beyond the code-implementation authorization already on file (config/model_v1_5_spec.json → claude_md_gate_deviation, scoped to "PREREGISTRATION_AMENDMENT_AND_CANDIDATE_MODEL_CODE_IMPLEMENTATION_ONLY_NO_REAL_FIT"). The one real-data fit that has occurred (the 2026-08-15 historical pilot) required its own explicit, hash-anchored governance deviation, OPERATOR_AUTHORIZED_PRE_200_FULL20_HISTORICAL_PILOT, scoped narrowly to a retrospective walk-forward evaluation, explicitly declared not live/frozen OOS evidence. That authorization does not, on its own terms, extend to TRUE_LIVE inference on an unseen candidate — a materially different, higher-stakes act (this task's own §0 frames it that way). This task's §4–§6 constitute that separate, explicit, in-writing operator authorization for the TRUE_LIVE case specifically, bounded by the ephemeral/no-persistence/exact-reuse constraints in §5(A–H), which this bridge satisfies. This is recorded here as the authorization basis, not silently assumed.

B. Bridge Equivalence Evidence
Zero code drift. Every governing file's SHA-256 was recomputed fresh and matches the pilot's PRE_EXPOSURE_MANIFEST.json exactly:

File	SHA-256 (recomputed, matches pilot manifest)
scripts/modeling/candidate_models.py	f49df50989d345a900830f5f663303a6aa4d095fe819174fc1c0d9207cfb5565
scripts/modeling/preprocessing.py	777920e4ba0982b522d26e1cfdd079ca3bac3f5fed82be25e20c8af1005f8e44
scripts/modeling/fold_engine.py	d5fd48a893512b47f8b720ae6371cc261b66fb1aa950f68945ce32a2b9f097d9
scripts/modeling/logistic_policy.py	08527ede03f3cb95ff46c180cae126a0831f1fe102425374e5534f4259c7e1fd
scripts/modeling/feature_assembly.py	1f3fc2e845573719582601a22308ce8f1dc3b4f66d3a91c49fb02d71a73d1362
scripts/modeling/target_extraction.py	252c480c165c7685f47fbe3dc5983b1410c8216d59369ba81301b02037f3690e
scripts/modeling/common.py	a6f1d5a02f48745642803cf24151bb547e0d39812346b636eb4fbbcbc8c5ff6b
config/model_v1_5_spec.json	1245bf0f96c63cabdbd740cf043e9f3c58f8fc50af48472933c29e05dce211b1
artifacts/modeling/V1_5_PREREGISTRATION.md	156435859e4ea81d078a56435a6bf6a7f04bd1fea289fc15b1baccebb4c2ce2d
Runtime re-verified identical. .venv-v1_5-model: Python 3.12.13, scikit-learn 1.9.0, numpy 2.5.2, scipy 1.18.0, joblib 1.5.3, threadpoolctl 3.6.0 — matches V1_5_RUNTIME_MANIFEST.json exactly. candidate_models.verify_runtime() was called explicitly at the top of the bridge script and passed.

Non-outcome-sensitive implementation regression check (task §6, performed as requested): ran the existing frozen suite tests/test_v1_5_candidate_models.py under the pinned venv — 45/45 tests pass, entirely against synthetic fixtures, zero real IPO data touched. Directly relevant assertions confirmed by this run, not merely by reading the source:

Check	Confirming test
Ridge alpha grid exactly {0.1, 1, 10, 100}	test_R3_exact_alpha_grid_only
Ridge tie → largest alpha, bit-exact only	test_R9_exact_tie_selects_largest_alpha
Logistic C grid exactly {0.01, 0.1, 1, 10}	test_L5_exact_C_grid_only
Logistic tie → smallest C, bit-exact only	test_L11_exact_tie_selects_smallest_C
p == 0.5 → class 0 exactly	test_L12_exact_p_half_predicts_class_0
P(y=1) via explicit classes_ lookup, never fixed column position	test_L9_positive_class_probability_explicit_lookup_not_column_position
Inner LOOCV preprocessing refit per split (not reused)	test_R4_inner_preprocessing_refitted_per_split_spy, test_L6_...
Outer test row invisible during tuning	test_R6_outer_test_row_invisible_during_tuning, test_L8_...
API structurally cannot accept an outer-test target	test_R7_api_has_no_outer_test_target_parameter
No custom SVD cutoff / pseudoinverse tolerance anywhere in source	test_no_custom_svd_cutoff_or_tolerance_path_in_source
Ridge/Logistic construction uses only the pinned library, no alternate solver	test_ridge_and_logistic_construction_use_pinned_library_only
Runtime mismatch hard-fails	test_runtime_mismatch_hard_fails
Ambiguity check (task §6, item by item) — none found:

Behavior	Status
Feature ordering	Unambiguous — active_substantive_features then active_indicator_features, in preprocess_fold's own return order (_columns_of)
Missing-value behavior	Unambiguous — training-fold median imputation on winsorized exact-Fraction values (preprocessing.py steps 2–5)
f5 derivation	Unambiguous — created iff f3 survives missingness-drop; unconditional co-drop with f3
Scaling/preprocessing	Unambiguous — feature-aware standardization, population variance ddof=0, f1 on log values, f2/f3/f4 on exact-rational structural values
Fold construction	See below — one legitimate degenerate case of the identical per-fold contract, not a new methodology
Ridge settings	Unambiguous — fit_intercept=True, solver="svd", no target transform
Logistic settings	Unambiguous — l1_ratio=0.0 (documented L2-equivalent, not deprecated penalty="l2"), solver="lbfgs", fit_intercept=True, class_weight=None, max_iter=10000, tol=1e-10
Alpha / C grids	Unambiguous, confirmed by tests above
MAE / raw Brier selection	Unambiguous — MAE in native R_h space; Brier on raw unclipped P(y=1)
Tie-break rules	Unambiguous, confirmed by tests above
Direction threshold	Unambiguous — p > 0.5 → 1, p ≤ 0.5 → 0
On "fold construction." The historical pilot calls fold_engine.plan_folds() to generate many walk-forward folds (one per eligible historical ticker, chronologically). This task needed exactly one fold per horizon: all STRICT_PRIOR_DATE_RULE-eligible historical tickers as training, TKNKA as the single held-out test observation. fold_engine.plan_folds is built around historical tickers that themselves carry a realized target and does not fit a genuinely unseen future candidate with no target at all — using it here would have been forcing the wrong abstraction, not reuse. Instead, the bridge assembles that one fold's four inputs directly (outer_training_raw, outer_training_targets, outer_test_raw, outer_filter_status) and calls candidate_models.fit_ridge_candidate / fit_logistic_candidate — the same atomic, frozen, per-fold contract the pilot calls internally, invoked once instead of many times. This is not an alternate implementation of fold construction; it is the same primitive operation at n=1 outer folds instead of n=20. Training-row order was constructed to match the frozen convention exactly: (first_trading_date ASC, ticker ASC) (determinism.training_row_order).

No selection on performance. The bridge was designed and coded before any TKNKA number existed; no rule was adjusted after seeing a result.

C. TKNKA Freeze Verdict
TKNKA_TRUE_LIVE_V1_5_FROZEN

D. True Live Metric Eligibility
TRUE_LIVE_FROZEN_METRIC_ELIGIBLE = YES

Precondition	Status	Evidence
Official first-trading date established before freeze	✅	KAP 1652127, Borsa decision 2026-08-18, first trading 2026-08-20
Freeze precedes first session	✅	Freeze 2026-08-19T14:48:53+03:00; first trade 2026-08-20
No TKNKA outcome accessed	✅	No price, order book, volume, tavan/taban, gray market, social-media, or BIST session data opened; no TKNKA OHLCV file exists yet
Candidate inputs available before first trade	✅	All four sources dated 2026-08-05–06; demand collection 12–14 Aug; all before cutoff 2026-08-19 and first trade 2026-08-20
Frozen V1.5 unchanged	✅	Zero code drift, hash-verified (§B)
STRICT_PRIOR_DATE_RULE used	✅	Applied explicitly (§I)
Execution bridge methodology-identical	✅	§B
Repository unchanged	✅	git status identical, 25 untracked entries, start and end
One transparency note, non-blocking: the results document (KAP 1651025) text extraction shows no independently machine-extracted KAP publication timestamp (unlike the TSSD, whose digital-signature block gave explicit timestamps). Its publication is nonetheless chronologically bounded on both sides by hard logical constraints: it cannot predate the demand-collection close (14 Aug), and the Borsa decision to list (18 Aug) necessarily postdates the finalized allocation results it reports — so its publication falls in the window 14–18 August, safely before both the 19 August cutoff and the 20 August first trade. This is the same class of minor provenance-completeness gap the BULGS golden packet flagged ("PARTIALLY_UNRESOLVED_PENDING_FINAL_METADATA_CAPTURE"), not a blocker.

E. Identity / First-Trade Evidence
Field	Value	Source
ticker	TKNKA	KAP 1652127
legal company name	Teknika Plast Teknik Kalıp Plastik Sanayi ve Ticaret A.Ş.	KAP 1651025 header
first_trading_date	2026-08-20	KAP 1652127 (structured disclosure, per task §1/§2)
borsa_decision_date	2026-08-18	task §1
market	Yıldız Pazar	task §1
base_price	85.40 TL	task §1, cross-confirmed by FTR/TSSD/results doc
trading_code	TKNKA.E	task §1
SPK approval date	2026-08-05	TSSD: "Sermaye Piyasası Kurulu (Kurul)'nca 05.08.2026 tarihinde onaylanmıştır"
demand collection	12–14 August 2026	Results doc, TSSD
offer method	Sabit Fiyatla Talep Toplama (fixed-price)	consistent with 85.40 TL fixed price throughout all sources
has traded?	NO — pre-first-trade	—
F. Input Source Matrix
Doc	KAP	Role	File SHA-256	Extraction
Fiyat Tespit Raporu	1645144	valuation, price determination	03d43ab5008e64f46a43ad42abce77e2736469cfd03a9c63b9bc57717ad8230f	✅ full text (238,532 chars)
Tasarruf Sahiplerine Satış Duyurusu	1645150	offer terms, capital structure, additional-sale confirmation	b733ad79bd10a5b3d75f8ae33f59b8067dc56ed33842da7f605c3a8b90696fbd	✅ full text (7,356 chars)
Halka Arz Sonuçları	1651025	demand, allocation, f3 source statement	c21cb0bf845e7e0fa001ed73a0831553cf9df66c16e2a555c48cf7c00646e09e	✅ full text (3,410 chars)
İzahname	1645124	prospectus — additional-sale confirmation (§25.2.5), SPK-approved	f126b18eb88c676f4c9c5a37ed4f53d95e86a94df3dca407702129813c19e1a4	✅ full text (1,190,203 chars, extracted via pdftotext -layout, Git for Windows poppler build)
No third-party financial source was used. Text was extracted to the session scratchpad only, never the repository.

G. f1–f5 Contract
Task §3's expected raw structure was independently cross-checked against the source documents, not assumed — all values confirmed exactly:

Field	Source	Value
ipo_price_tl	FTR: "1 TL nominal değerli payın satış fiyatı 85,40 TL olarak belirlenmiştir"	85.40
pre_ipo_capital	TSSD: "çıkarılmış sermayesinin 100.000.000 TL'den 125.000.000 TL'ye çıkarılması"	100,000,000
post_ipo_capital	TSSD, same sentence	125,000,000
capital_increase_shares	TSSD: "artırılacak 25.000.000 TL nominal değerli 25.000.000 adet B Grubu pay"	25,000,000
existing_share_sale_shares	TSSD: Kemal Yaralı 3,000,000 + Ali Kutay Yaralı 3,000,000	6,000,000
total_offer_shares	TSSD: "toplam 31.000.000 TL nominal değerli 31.000.000 adet"	31,000,000 (25,000,000 + 6,000,000 ✓ exact)
additional_sale	İzahname §25.2.5: "Ek satış işlemlerine ilişkin bilgi: Yoktur."	NONE — officially confirmed by the SPK-approved prospectus itself, not merely absent-from-mention
source_reported_ipo_size_tl	Results doc: "Teknika Plast 2.647.400.000 TL halka arz büyüklüğüne sahip"	2,647,400,000 (= 85.40 × 31,000,000 exactly ✓)
f1 = log(ipo_size_tl)
Raw components: ipo_price=85.40, total_offer_shares=31,000,000
Cross-check: 85.40 × 31,000,000 = 2,647,400,000 — exact match to source-reported figure
Semantic scope: whole-offer, base offer (no additional sale exists to complicate scope — confirmed §25.2.5)
Origin: SOURCE_REPORTED_AND_CROSSCHECKABLE
Canonical eligibility: OFFICIAL, pretrade, before cutoff
Raw value passed to model (pre-log, per preprocessing.py step 7 — log is applied internally): f1 = 2647400000
f2 = free_float_pct
Raw components: total_offer_shares=31,000,000, post_ipo_capital=125,000,000
Calculation: 31,000,000 / 125,000,000 × 100 = 24.8 exactly (terminating decimal, no rounding needed)
Canonical arithmetic contract (percentRatio, HALF-UP scale 10): 24.8000000000
Origin: DERIVABLE_FROM_OFFICIAL_RAW_COMPONENTS
Final value: f2 = 24.8000000000
f3 = total_demand_multiple — SOURCE_REPORTED, Class A
Source statement: "Toplam halka arz büyüklüğünün yaklaşık 6,45 katı 200.086.004 TL nominal talep toplanmıştır" — an explicit aggregate multiple, for the whole offer, stated in words
Raw numerator (preserved): 200,086,004 TL nominal aggregate demand
Raw denominator (preserved): 31,000,000 TL nominal total offer
Independent cross-check: 200,086,004 / 31,000,000 = 6.4544... ≈ "6,45" as published ✓ consistent
Category sum check: 15,750,917 + 88,621,859 + 69,750,728 + 25,962,500 = 200,086,004 ✓ exact
Not the BALSU/VEYAS trap: demand ≠ distribution in every category (e.g. retail: 15,750,917 demanded vs 12,400,000 distributed; applications: 499,401 vs 492,327) — genuine unfiltered incoming-demand figures, not a post-allocation table
f3_raw_compatibility_class = A (TOTAL_DEMAND_MULTIPLE_SOURCE_REPORTED_COMPATIBLE)
f3_canonical_eligibility_status = SOURCE_REPORTED_DIRECT_ELIGIBLE
total_demand_filter_status: no explicit "filtrelenmemiş"/"filtrelenmiş" wording found in any of the four documents → NOT_SPECIFIED (matches the FULL20 convention used for KARCL, SARAE, EKDMR, MCARD, LXGYO, SVGYO, ATATR — a usable status under the frozen comparability rule, not a missing one)
Per the frozen SOURCE_REPORTED contract ("the official source publishes an already-rounded demand multiple... FINITE_DECIMAL_AS_PUBLISHED"), the literal published value is used, not the recomputed one — exactly the BULGS precedent (2.86 literal, not 2.8557688276 recomputed)
Final value: f3 = 6.45
f4 = capital_increase_pct_of_offer
Raw components: capital_increase_shares=25,000,000, total_offer_shares=31,000,000
Calculation: 25,000,000 / 31,000,000 × 100 = 80.645161290322580645...% (repeating decimal)
Canonical arithmetic contract (HALF-UP scale 10): 80.6451612903
Cross-check identity: 25,000,000 + 6,000,000 = 31,000,000 ✓ exact
Origin: DERIVABLE_FROM_OFFICIAL_RAW_COMPONENTS
Final value: f4 = 80.6451612903
f5 = f3 missingness indicator
f3 is present and eligible (not missing) → f5 = 0 for TKNKA's test row (computed internally by preprocess_fold, not manually sourced, per frozen rule)
H. Training Snapshot
Universe: FULL20 canonical, artifacts/universe/ipo_universe_last20_2026-08-07.csv (20 tickers), loaded via common.load_universe().
Feature source: artifacts/ipo_master/consolidated/ipo_master_20_pretrade_canonical.csv, via feature_assembly.assemble_raw_features() (unmodified, frozen function — reused exactly).
Target source: target_extraction.extract_targets() (unmodified, frozen function), which is internally pinned by common.py to FULL20 OHLCV snapshot 20260814_101901 (artifacts/ohlcv/full20/snapshots/20260814_101901/first10_ohlcv_20_snapshot.csv) — the same pinned snapshot the 2026-08-15 historical pilot used, hash 7e17b63f75dabab34a1e4d2dce4ca28a81c7cd1cdfda064522fe773237bcf7b4 per that pilot's manifest. This module was not modified to point at a fresher snapshot, per the reuse-unmodified constraint (§5H).
TKNKA is not a member of the FULL20 universe file and was not added to it (no repository write); its raw feature vector was constructed independently in the ephemeral bridge script, following the identical semantic rules (§G).
I. Strict Prior-Date Eligibility Audit
STRICT_PRIOR_DATE_RULE applied at prediction local date T = 2026-08-19: a historical target is training-eligible only if target_session_date < 2026-08-19 and target_status == TARGET_AVAILABLE (which target_extraction.py already encodes as row_status == OFFICIAL_VERIFIED and conflict_status == NO_CONFLICT). This filter was applied explicitly in the bridge script on top of the frozen extraction, per horizon.

Transparency note on the filter's actual effect: because the pinned snapshot itself is dated 20260814_101901 (14 August 2026), no row in it can possibly carry a target_session_date later than 14 August — a session cannot be OFFICIAL_VERIFIED before it occurs. The explicit date filter therefore excluded zero rows at any horizon; the cutoff was already satisfied by the snapshot's own vintage. This is reported plainly rather than silently relied upon — the filter was still applied as a defense-in-depth confirmation, and its result (excluded_same_or_future = [] for every horizon) is recorded below.

Horizon	n (eligible)	Excluded (same-date/future)	Excluded (unavailable in pinned snapshot)
D1	20	none	none
D3	20	none	none
D5	20	none	none
D10	19	none	QUICK — D10 target session date 2026-08-19 had not yet occurred as of the pinned 14-Aug snapshot, so target_status ≠ TARGET_AVAILABLE; excluded by the underlying frozen extraction, independently consistent with what STRICT_PRIOR_DATE_RULE's same-date exclusion would also have required had it been available
All four horizons clear MIN_TRAIN_N = 10 comfortably.

Eligible ticker set (identical across D1/D3/D5; D10 drops QUICK), in the frozen training-row order (first_trading_date ASC, ticker ASC):

ATATR, EMPAE, GENKM, SVGYO, LXGYO, MCARD, AAGYO, EKDMR, BETAE, ORZAX,
GOLDA, EKIM, ISVEA, SSAAT, SARAE, METEN, ALBTN, MASFN, KARCL, QUICK
(D10: same list without QUICK, n=19)

J–M. Per-Horizon Predictions
Both Ridge (V1_RIDGE) and Logistic (V1_LOGIT) fit successfully (FIT_OK) at every horizon — no single-class training set, no non-convergence, no insufficient variation.

J. D1
training n	20
alpha (Ridge)	100.0
C (Logistic)	0.1
point return prediction (R̂)	+7.0423% (0.07042308019908708)
predicted price	91.414131 TL (85.40 × 1.070423080...)
P(UP)	0.844664
direction	UP
logistic class balance (training)	4 DOWN / 16 UP
confidence	ÇOK DÜŞÜK (see §N)
K. D3
training n	20
alpha (Ridge)	10.0
C (Logistic)	1.0
point return prediction (R̂)	+24.0264% (0.24026386117431145)
predicted price	105.918534 TL
P(UP)	0.932599
direction	UP
logistic class balance (training)	5 DOWN / 15 UP
confidence	ÇOK DÜŞÜK
L. D5
training n	20
alpha (Ridge)	10.0
C (Logistic)	1.0
point return prediction (R̂)	+38.7475% (0.38747451993801274)
predicted price	118.490324 TL
P(UP)	0.904561
direction	UP
logistic class balance (training)	6 DOWN / 14 UP
confidence	ÇOK DÜŞÜK
M. D10
training n	19 (QUICK excluded, §I)
alpha (Ridge)	10.0
C (Logistic)	0.1
point return prediction (R̂)	+65.5849% (0.6558488037740904)
predicted price	141.409488 TL
P(UP)	0.793263
direction	UP
logistic class balance (training)	5 DOWN / 14 UP
confidence	ÇOK DÜŞÜK
No prediction was rounded, clipped, calibrated, or adjusted after computation.

N. Confidence / Undefined Fields
Confidence: TRUE LIVE V1.5 with n_oos < 20 (this is the first-ever TRUE_LIVE frozen prediction under this bridge; n_oos = 0 prior to this freeze) → ÇOK DÜŞÜK for all four horizons, per model_v1_5_spec.json's canonical Turkish enum and the frozen pilot cap. No frozen contract term drives it lower than this floor.
Prediction interval: NOT_DEFINED_BY_FROZEN_V1_5 — V1.5 inherits V1.1's "prediction intervals DISABLED_IN_V1_1_PILOT", unchanged.
Risk label: NOT_DEFINED_BY_FROZEN_V1_5 — no risk-labeling methodology is preregistered in V1.5; not invented here.
O. Model / Data / Runtime Hashes
Item	Value
Governing spec	BORSAI_V1_5_PREREG_20260814
config/model_v1_5_spec.json	1245bf0f96c63cabdbd740cf043e9f3c58f8fc50af48472933c29e05dce211b1
artifacts/modeling/V1_5_PREREGISTRATION.md	156435859e4ea81d078a56435a6bf6a7f04bd1fea289fc15b1baccebb4c2ce2d
All 10 scripts/modeling/*.py files	see §B table — zero drift from pilot manifest
FULL20 universe	305fec7050bbf7025da7abfe90661383517437af5327adc5a41c794863f1ee63
FULL20 OHLCV snapshot consumed	run_id 20260814_101901, 7e17b63f75dabab34a1e4d2dce4ca28a81c7cd1cdfda064522fe773237bcf7b4
Canonical pretrade master consumed	artifacts/ipo_master/consolidated/ipo_master_20_pretrade_canonical.csv
Pinned runtime	Python 3.12.13 · scikit-learn 1.9.0 · numpy 2.5.2 · scipy 1.18.0 · joblib 1.5.3 · threadpoolctl 3.6.0
TKNKA source PDFs	see §F
P. Machine-Readable Frozen Packet
{
  "packet_type": "TRUE_LIVE_V1_5_FROZEN_PREDICTION",
  "task_id": "BORSAI_TKNKA_TRUE_LIVE_V1_5_BRIDGE_AND_FREEZE_READONLY_01",
  "freeze_timestamp_istanbul": "2026-08-19T14:48:53+03:00",
  "freeze_timestamp_utc": "2026-08-19T11:48:53Z",
  "prediction_local_date": "2026-08-19",
  "ticker": "TKNKA",
  "legal_company_name": "Teknika Plast Teknik Kalıp Plastik Sanayi ve Ticaret A.Ş.",
  "first_trading_date": "2026-08-20",
  "has_traded_at_freeze_time": false,
  "governing_spec": "BORSAI_V1_5_PREREG_20260814",
  "execution_bridge_verdict": "TRUE_LIVE_EXECUTION_BRIDGE_PASS",
  "freeze_verdict": "TKNKA_TRUE_LIVE_V1_5_FROZEN",
  "true_live_frozen_metric_eligible": "YES",
  "training_snapshot": {
    "full20_universe_sha256": "305fec7050bbf7025da7abfe90661383517437af5327adc5a41c794863f1ee63",
    "full20_ohlcv_snapshot_run_id": "20260814_101901",
    "full20_ohlcv_snapshot_sha256": "7e17b63f75dabab34a1e4d2dce4ca28a81c7cd1cdfda064522fe773237bcf7b4",
    "pretrade_master_path": "artifacts/ipo_master/consolidated/ipo_master_20_pretrade_canonical.csv"
  },
  "f1_f5": {
    "f1_raw_ipo_size_tl": "2647400000",
    "f2_free_float_pct": "24.8000000000",
    "f3_total_demand_multiple": "6.45",
    "f3_raw_compatibility_class": "A_SOURCE_REPORTED_COMPATIBLE",
    "f3_canonical_eligibility_status": "SOURCE_REPORTED_DIRECT_ELIGIBLE",
    "f3_filter_status": "NOT_SPECIFIED",
    "f4_capital_increase_pct_of_offer": "80.6451612903",
    "f5_missingness_indicator": 0,
    "additional_sale_confirmed_none_source": "izahname_25.2.5"
  },
  "horizons": {
    "D1": {"n_train": 20, "excluded_same_or_future_date": [],
      "ridge": {"status": "FIT_OK", "alpha": 100.0, "predicted_return": 0.07042308019908708, "predicted_price_tl": 91.414131},
      "logistic": {"status": "FIT_OK", "C": 0.1, "p_up": 0.844664480260313, "direction": "UP", "n_class_0": 4, "n_class_1": 16}},
    "D3": {"n_train": 20, "excluded_same_or_future_date": [],
      "ridge": {"status": "FIT_OK", "alpha": 10.0, "predicted_return": 0.24026386117431145, "predicted_price_tl": 105.918534},
      "logistic": {"status": "FIT_OK", "C": 1.0, "p_up": 0.9325991151686223, "direction": "UP", "n_class_0": 5, "n_class_1": 15}},
    "D5": {"n_train": 20, "excluded_same_or_future_date": [],
      "ridge": {"status": "FIT_OK", "alpha": 10.0, "predicted_return": 0.38747451993801274, "predicted_price_tl": 118.490324},
      "logistic": {"status": "FIT_OK", "C": 1.0, "p_up": 0.904560872086287, "direction": "UP", "n_class_0": 6, "n_class_1": 14}},
    "D10": {"n_train": 19, "excluded_same_or_future_date": [], "excluded_unavailable_in_pinned_snapshot": ["QUICK"],
      "ridge": {"status": "FIT_OK", "alpha": 10.0, "predicted_return": 0.6558488037740904, "predicted_price_tl": 141.409488},
      "logistic": {"status": "FIT_OK", "C": 0.1, "p_up": 0.7932628215840286, "direction": "UP", "n_class_0": 5, "n_class_1": 14}}
  },
  "confidence": "COK_DUSUK",
  "prediction_interval": "NOT_DEFINED_BY_FROZEN_V1_5",
  "risk_label": "NOT_DEFINED_BY_FROZEN_V1_5",
  "veyas_outcome_contamination": "NONE",
  "tknka_outcome_contamination": "NONE",
  "repository_mutated": false,
  "v1_5_modified": false,
  "code_hash_drift_from_pilot_manifest": false
}
Q. Repository Safety Confirmation
git status at task start and at freeze time: identical — branch main, no commits yet, the same 25 untracked pre-existing entries (24 original + .venv-v1_5-model is git-ignored per its own manifest, not newly untracked by this task).
No repository file created, edited, deleted, or renamed. The bridge script existed only as a heredoc piped to python -'s stdin — no .py file was written to disk anywhere, ephemeral or otherwise.
No web tools, no research agents, no subagents used.
No TKNKA outcome data accessed at any point — no price, order book, volume, tavan/taban, gray-market, or social-media data; no TKNKA BIST session record; no TKNKA OHLCV file (none exists yet, as TKNKA has not traded).
No V1.5 spec, canonical master, universe file, or frozen prediction registry was touched.
No package installed; the pre-existing pinned venv was used exactly as manifested, re-verified via verify_runtime() and independent hash recomputation.
No hyperparameter grid was widened; no post-result tuning occurred — the bridge script was written and the equivalence checks (§B) were completed before any TKNKA number was computed.
Self-check: bridge verdict PASS is grounded in code inspection + hash equality + a live 45/45 synthetic-fixture test run, not asserted from memory. The freeze verdict is FROZEN because every input resolved cleanly (unlike VEYAS, no offer-scope ambiguity, no image-only PDF, additional sale explicitly confirmed NONE by the highest-tier source). The BALSU/VEYAS f3=1.00 trap was checked and does not apply — TKNKA's demand and distribution columns differ in every category. No V1.5 rule was invented, widened, or bypassed. Repository is unchanged.
TKNKA TRUE_LIVE V1.5 FREEZE — PROVENANCE ADDENDUM

Original immutable freeze:
TKNKA_TRUE_LIVE_V1_5_FREEZE_20260819.md

Original freeze timestamp:
2026-08-19T14:48:53+03:00

This addendum DOES NOT modify:
- any model input
- f1-f5
- training set
- model specification
- hyperparameters
- predictions
- probabilities
- direction
- confidence
- TRUE_LIVE eligibility

ADDITIVE PROVENANCE CORRECTION:

KAP Bildirim 1651025
Halka Arz Sonuçları
Official KAP sending timestamp:
2026-08-17 10:53:27 Europe/Istanbul

Therefore the prior freeze report's publication-time uncertainty
for KAP 1651025 is now resolved.

Also correct the descriptive statement that implied all four
candidate sources were dated 2026-08-05–06.

The Halka Arz Sonuçları disclosure was published on 2026-08-17.

KAP Bildirim 1652127
Payların İşlem Görmeye Başlaması
Official KAP sending timestamp:
2026-08-18 18:10:48 Europe/Istanbul

First trading date:
2026-08-20

IMPACT:
NONE_ON_FROZEN_PREDICTION

TRUE_LIVE_FROZEN_METRIC_ELIGIBLE remains YES.

Original frozen prediction remains immutable.
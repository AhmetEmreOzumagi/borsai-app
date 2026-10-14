# SPEC_POST_D1_V0 → kod eşlemesi (BORSAI_FAZ5_POST_D1_IMPL_20260924, commit A)

Şartname `docs/specs_faz5/SPEC_POST_D1_V0.md` (sha256 `a5b4675d…`, commit `c20c092`). Her madde, onu uygulayan
dosya:fonksiyon ve onu sınayan test. Kararlar ve yorumlar `docs/SPEC_DEVIATIONS.md` H bölümünde (H1–H22).
Testler `tests/test_faz5_post_d1.py` (A) ve `tests/test_faz5_golden.py` (B, altın ledger'ı okur).

| Şartname | Madde | Kod | Test |
|---|---|---|---|
| §1.1 | model_id, algorithm, stage, parent (sha INDEX'ten) | `borsai/specs.py: POST_D1_HAZARD_V0`, `POST_D1_MODEL_SPECS`, `SPEC_DOCUMENTS_FAZ5`, `model_kind` → `post_d1`; `borsai/freeze.py: model_kind` | `test_t4_freeze_…`, `test_14_…`, `test_15b_…` |
| §1.2 | yalnız D1 tavan kapatan arzlar; f3'süz ret | `predict_post_d1.evaluate_d1` (`D1NotApplicable`), `predict_post_d1.predict_post_d1` (ana model reddi aynen); `post_d1.final_training_rows` | `test_1_…`, `test_9_…` |
| §1.3 | standart şema; h_1 ana modelden; S_cond, p_break_next, P_L_cond (`conditional_weights`); P_close ana modelin reclose_rates'i; path_conditional (`predict_path.conditional`) | `predict_post_d1.updated_hazards`, `curves`, `path_conditional`, `predict_post_d1` | `test_5_t2_…`, `test_11_…`, `test_10_…` |
| §1.4 | yalnız D1 (j ≥ 2 güncellemesi yok) | `predict_post_d1.CONDITION_J = 1` | — |
| §2 | `d1_lock` (ham metin Decimal eşitliği), `d1_turnover` = ln(hacim / shares_offered) (60 hane → binary64), tutarlılık uyarısı | `predict_post_d1.evaluate_d1` (tek tanım: backtest ve tahmin) | `test_2_…` |
| §2 | dönüşüm: d1_lock z-skor; d1_turnover Type-7 p05/p95 kırpma → z; σ = 0 düşer | `post_d1.fit_d1_prep`, `D1Prep.transform` (kesin), `D1Prep.params`; stdlib `predict_post_d1.d1_transform` | `test_7b_…`, `test_10_…`, `test_8b_…` |
| §2 | eksik/işlemsiz/durdurma tablosu (D1_NOT_TRADED, D1_LIMIT_NA, NOT_APPLICABLE, D1_VOLUME_INVALID, INPUT_SHARES_OFFERED, F3_MISSING, WARN_D1_HALF_DAY, WARN_D1_INTRADAY_HALT, WARN_D1_SPECIAL_TRADES, kırpma, OUT_OF_TRAINING_RANGE) | `predict_post_d1.evaluate_d1`, `predict_post_d1.predict_post_d1` (H8, H9) | `test_9_…` |
| §3.1 | η^base ofset (γ, β, ön işleme aynen), logit h_d = η + δ·u (d = 2..10), h_1 değişmez | `predict_hazard.linear_predictor` (+ `hazard.HazardFit.linear_predictors`), `predict_post_d1.updated_hazards` | `test_t1_…` (3 test), `test_3_…`, `test_5_t2_…` |
| §3.1 | J(δ), Newton (∇ ≤ 1e-10, ≤ 100, yarılama, A2), yakınsamama | `post_d1.objective`, `newton_offset`, `fit_delta`, `row_nll` | `test_6_…` |
| §3.1 | λ ızgarası, iç arz-bırak CV (D1 ön işlemesi kalanlardan, ofset sabit), eşitlikte büyük λ, yakınsamayan aday çıkar, INF kalır | `post_d1.select_lambda`, `fit_delta_set`; `hazard.choose_lambda` | `test_7_…` |
| §3.4 | λ = INF ucu karşılaştırıcıya bit-eşit (ayrı sıfır model yok) | genel yol (özel dal yok): `updated_hazards` | `test_5_t2_…`, `test_5b_…`, `test_t2_t7_pipeline_…` |
| §3.5 | eğitim kümesi `H99_F3_PRESENT_L_GE_1` (81), D1 alanları SESSIONS 1. seans, 2..10 yalnız tarih; JSON ek alanları | `post_d1.final_training_rows`, `final_delta_set`, `fit_params`, `build_params`, `load_frozen`; `post_d1.load_d1_sessions` (beyaz liste) | `test_1_…`, `test_8_…`, B: `test_faz5_golden.py` |
| §4 | birincil hücre (koşullu RPS_1 vs `ceiling_hazard_v0` koşullu), kurallar, ikinciller (Brier k = 2, 10; kalibrasyon; path_conditional), keşif | `report_faz5.paired_conditional`, `conditional_obs`, `cond_loss` (ortak `predict_path.conditional_rps/brier`), `calibration`, `path_obs`, `path_comparator`, `render_faz5` | `test_12_…`, `test_t6_…`, `test_15c_…` |
| §4 | aralık SPEC_DEVIATIONS C7; ölçek ayrımı | `metrics.paired_difference`; `report_faz5.summarize` → `scoring._one_scale` (`backtest_conditional`, `ScaleMixError`) | `test_12b_…` |
| §5 | beklenti tablosu (aynen), tuttu/tutmadı, (a)–(e), çok iyi, canlı akış koşulu | `report_faz5.expectation_rows`, `EXPECTED_ROWS`, `CI_CATEGORY`, `diff_label`, `evaluate`, `fold_summary`, `OPERATIONAL_RULES_FAZ5` | `test_15_…`, `test_15c_…` |
| §6.1 | PLAN_POST_D1; fold kümesi Faz 1B tavan ledger'ı; NOT_APPLICABLE | `specs.PLAN_POST_D1`; `post_d1.fold_parts`, `backtest_ledger`, `_ledger_row` | `test_4_…`, `test_t2_t7_pipeline_…` |
| §6.1-2 | ofset = fold'un kendi ceiling_hazard_v0 fit'i, ledger'la \|Δ\| ≤ 1e-9 | `post_d1._fold_task` (`hazard.fit_training_set`), `_parity` | `test_3_…`, `test_3b_…` |
| §6.1-3/4/5 | δ eğitim kümesi d ≥ 2, D1(j) < T, ≥ 10/5/5, fold içi ön işleme | `post_d1.delta_set_of`, `_fold_task` | `test_4_…`, `test_8b_…` |
| §6.1-6 | path_conditional yalnız Faz 4 fold'u OK ise, o fold'un hücreleriyle | `post_d1.path_cells_by_fold`, `fold_path_params`, `fold_path_output`, `path_summary` | `test_t2_t7_pipeline_…`, `test_11_…` |
| §6.1-7 | sızıntı noktaları (i)–(vi) | (i) `load_d1_sessions`; (ii) `_fold_task` yalnız eğitim arzlarının özellikleri; (iii) `_ledger_row` denetimi; (iv) `realized_L` yalnız etiket; (v) karşılaştırıcılar Faz 1B ledger'ından (`report_faz5`); (vi) `backtest.plan_ceiling_folds` (kesin <) | `test_8_…`, `test_8b_…`, `test_4_…` |
| §6.1-8 | ledger sütunları (sıra sabit) | `post_d1.ledger_columns` | `test_t2_t7_pipeline_…` |
| §6.1-9 | metrikler, MODELS.md bölümü, günlük satırı | `post_d1.compute_metrics`, `run_backtest`, `write_golden`; `report_faz5.render_faz5`; `report.render` (H21) | `test_15b_…`, B |
| §6.1-10 | `ScaleMixError`, `scale = backtest_conditional` | `report_faz5.SCALE`, `summarize` | `test_12b_…` |
| §6.2 | dondurma: parent sha ön koşulu; INDEX.json yerine INDEX_POST_D1.json (karar 4, H4) | `freeze.freeze`, `freeze_post_d1`, `_parent_ok`, `INDEX_POST_D1_PATH` | `test_t4_freeze_…` |
| §7 | canlı kayıt aşaması (POST_D1) | canlı akış görevi (T10); bu görevde yalnız ayrı dizin desteği: `outcomes.sequence_guard`, `scoring.sequence_violations` (H5) | `test_t4_sequence_guard_…`, `tests/test_outcome_guard.py::test_10e/10f` |
| §9 | ret/uyarı kodları | `predict_post_d1` sabitleri (H8) | `test_9_…` |
| §11-1…12 | kabul testleri | yukarıdaki testler (`test_1_…` … `test_12_…`) | — |
| §11-13 | POST_D1 kayıt ve sınıf | kapsam dışı (T10: canlı akış görevi) | — |
| §11-14 | bekçiler (bu göreve düşen) | — | `test_t11_…`, `test_14_…`, `tests/test_outcome_guard.py` |
| §11-15 | günlük ve rapor (kod tarafı) | `post_d1.run_backtest`, `report_faz5.OPERATIONAL_RULES_FAZ5` | `test_15_…`, `test_15b_…`, B |
| §11-16 | uygulama | kapsam dışı (EK 3) | — |
| §12 | sözde kod | `d1_fields` → `load_d1_sessions`; `d1_features` → `evaluate_d1`; `offset` → `linear_predictor` / `HazardFit.linear_predictors`; `prep_d1` → `fit_d1_prep`; `fit_delta`; `select_lambda`; `predict_post_d1`; backtest fold → `_fold_task` + `_ledger_row` | — |

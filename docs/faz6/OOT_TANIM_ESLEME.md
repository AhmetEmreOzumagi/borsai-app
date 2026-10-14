# Faz 6 tanım eşlemesi: SPEC_OOT_PRE_H99_V0 ve KARARLAR → kod

Görev: BORSAI_FAZ6_OOT_INFRA_20260924. Şartname `docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md` (`b8763fc`), proje sahibi kararları `docs/specs_faz6/KARARLAR.md` (`94ad4e8`; şartnameyle çeliştiği yerde geçerli). Her madde → dosya:fonksiyon ve sınayan test. Boşluk ya da iki okumalı yerler `docs/SPEC_DEVIATIONS.md` bölüm I'dedir (I1–I27); burada numarasıyla anılır.

Bu görevde yazılan kod sonuçsuz ve ağsızdır. Hiçbir tahmin kaydı, D_1 satırı, bülten ya da sonuç dosyası yazılmadı. Gerçek skor üretilmedi.

## §1 Kohort üyeliği

| Madde | Kod | Test |
|---|---|---|
| Kaynak ve üyelik kuralı (K1, bildirim alanları, OUT_OF_SCOPE nedenleri) | Üyelik kararı S0 eki `docs/specs_faz6/ekler/evren_listesi.csv`'dedir (kod yeniden sorgulamaz); satırlar `registry.build_cohort_rows` ile kohort dosyasına çevrilir | `test_real_cohort_validates_and_reproduces_from_code` (S1 sonrası) |
| `K_başlangıç` = 2020-01-01, pencere sonu 2023-09-21 (D1) | `registry.COHORT_START`, `COHORT_END`; `validate_cohort` pencere denetimi | `test_validate_cohort_accepts_valid_and_rejects_each_violation` |
| Payda dosyası `registry/oot/cohort_pre_h99.csv`, sütunlar | `registry.COHORT_PATH`, `COHORT_COLUMNS`, `read_cohort`, `validate_cohort`, `cohort_bytes` | aynı |
| Durumlar {MEMBER, OUT_OF_SCOPE, PENDING}; append-only; hata → CANCELLED satırı, eski satır kalır | `registry.COHORT_STATUSES`, `append_cohort`, `active_cohort`, `cohort_append_only_problems` (I5) | `test_cancelled_rule_and_single_active_row`, `test_append_cohort_is_append_only`, `test_cohort_file_is_append_only_in_history` |
| `vault` değer kümesi | `registry.VAULT_VALUES` = {OPEN, SEALED, EXPOSED_ARCHIVE, EXPOSED_CODEX} (I3) | `test_validate_cohort_…` |
| `listing_source_id = KAP_<id>`, `listing_source_sha256` | `validate_cohort` biçim denetimi; belgeyle eşitlik | `test_real_listing_source_matches_pinned_document` |
| Her üye bir satır; girdisi olmayan üye SKIPPED: INPUTS_NOT_AVAILABLE | `freeze.build_oot_records` (`skipped`), `scoring.oot_model_rows` (`ROW_SKIPPED`) | `test_oot_batch_skips_duplicates_and_members_without_inputs` |
| Gerçekleşen D_1 = sözleşme > 0 olan ilk resmi seans, KAP bildirim tarihinden önce değil | `outcomes_oot.resolve_member` → `outcomes.resolve_sessions(start = first_trading_date)` (I17) | `test_extracted_rows_equal_outcomes_definitions` |

## §2 Sıra ve bekçiler (KARARLAR D6 ile)

| Madde | Kod | Test |
|---|---|---|
| S1 G1: registry/oot/ sonuç alanı taşımaz; kaynak yayını < ilk işlem günü; belge sha | `registry.oot_outcome_key_problems`, `OOT_OUTCOME_KEYS`; `registry.inputs_pit_problems` | `test_oot_registry_carries_no_outcome_fields`, `test_real_inputs_validate_and_are_byte_equal_imports` |
| S2 G2: kayıt bütün INDEX modellerini içerir; model commit'lerinin torunu; yeniden yazılmaz | `freeze.build_oot_record` (her INDEX modeli), `_write_new` ('xb'), `record_filename` (içerik adresli) | `test_oot_batch_one_record_per_member_with_every_model`, `test_oot_records_hold_every_index_model_and_follow_model_commits` |
| S3 G3: d1_rows yalnız `<T>.E`, yalnız D_1; zip sha pinli; S3 kohort kapısından sonra | `outcomes_oot.extract_d1_rows`, `d1_row_doc`, `d1_rows_problems` (tek tanım `registry.post_d1_record_problems`), `download_gate` | `test_d1_rows_and_oot_post_d1_record`, `test_oot_d1_rows_and_post_d1_records_carry_only_d1` |
| S5 (D6 yerine): zip repoya girmez; karantina; yalnız açık küme ayıklanır; MANIFEST_OOT pinleri | `outcomes_oot.quarantine_dir`, `fetch_quarantine`, `extract_code_row`, `extract_open_members`, `append_manifest_oot` | `test_quarantine_dir_is_outside_repo_and_configurable`, `test_extractor_reads_only_open_codes_and_never_opens_sealed`, `test_no_cohort_window_bulletin_anywhere_in_repo` |
| G5′ (D6-5): sonuç commit'i kohortun bütün S2 kayıtlarının torunu, S2 kanıtı önce; SEALED satır hiçbir dosyada yok | `outcomes_oot.s2_gate_problems` (indirme anı), `scoring.cohort_gate_ok`, `class_oot` (skor anı) | `test_download_gate_requires_committed_and_pushed_s2_records`, `test_oot_outcomes_follow_every_s2_record_and_its_push_proof`, `test_sealed_codes_absent_from_every_extracted_file` |
| S6 G6: ölçek karışımı reddi | `scoring._one_scale`, `merge_scales` (değişmedi; `SCALE_OOT` yeni değer) | `test_scale_mixing_with_oot_is_rejected` |
| `class_oot` sözde kodu; `oot_ingest_commit` | `scoring.oot_ingest_commit` (I10), `class_oot` (I13), `cohort_gate_ok` | `test_class_oot_requires_dag_order_and_proof_order`, `test_class_oot_cohort_gate_and_outcome_before_record` |
| post_d1 için ek koşul (d1_rows sha, zip pini) | `scoring.oot_post_d1_block` (`extra_ok`) | `test_d1_rows_and_oot_post_d1_record` |
| Var olan bekçilerle uyum; `test_new_ipos_appear_in_data_only_as_outcomes` kalıbı kohort kodlarına | `tests/test_outcome_guard.py`: kayıt taraması `registry/oot/d1_rows` ve `post_d1`'i kendi bekçisine bırakır | `test_cohort_codes_appear_in_data_only_as_outcomes` |

## §3 Üçüncü ölçek

| Madde | Kod | Test |
|---|---|---|
| Ad `OOT_PRE_H99`; backtest/canlı ile birleşmez | `registry.OOT_SCALE`, `scoring.SCALE_OOT`; post_d1 alt tablosu `SCALE_OOT_POST_D1` (I24) | `test_scale_mixing_with_oot_is_rejected` |
| `scores.json`'da ayrı üst anahtar | **Sapma I1:** ayrı dosya `scores/scores_oot.json` (şema `borsai.scores_oot/1`); `scoring.build_oot_scores`, `write_oot_scores`; `main()` yazmaz | `test_build_oot_scores_synthetic` (scores.json değişmez) |
| Blok alanları `as_of`, `cohort_sha256`, `n_member/…` | `build_oot_scores` (`generated_at_utc`, `cohort_sha256`), `cohort_counters` | aynı |
| Uygulamada üçüncü panel | kapsam dışı (bu görev altyapı; uygulama salt okunur) | — |

## §4 Girdiler

| Madde | Kod | Test |
|---|---|---|
| Şema `borsai.inputs/1` aynen | `registry.validate_inputs`, `inputs_pit_problems` (değişmedi) | `test_real_inputs_validate_and_are_byte_equal_imports` |
| Girdi dosyası `regime_tags` ve `vault` taşır | **Sapma I2:** yalnız kohort dosyasında; girdiler bayt-eşit | aynı (`"vault" not in doc`) |
| f6: XU100 + Takvim C, `ref_date = first_trading_date` | `market20.CALENDAR_C_PATH`, `calendar_c_rows`, `load_calendar_c`, `load_oot_sources`, `oot_market20`; kayıtta `market20.ref_date_rule` | `test_oot_market20_ref_date_is_first_trading_date_on_calendar_c`, `test_calendar_c_…` |
| Tavan yolu: dönemin fiyat adımı tablosu | `registry.TICK_TABLE_T2015`, `limit_path_with`, `tick_table_mismatch` | `test_limit_path_with_json_table_equals_frozen_predict_path`, `test_tick_table_mismatch_only_where_path_reaches_250` |
| D1 alanları: D_1 satırı (S3) | `outcomes_oot.d1_row_doc` (POST_D1 `d1` bloğu şeması) | `test_d1_rows_and_oot_post_d1_record` |

## §5 Tahmin kayıtları `borsai.oot_record/1`

| Alan / kural | Kod |
|---|---|
| `record_type`, `record_stage = OOT_PRE_LISTING`, `scale = OOT_PRE_H99`, `ticker` | `freeze.build_oot_record` |
| `cohort_file_sha256`, `inputs_sha256`, `models_index {path, sha256}` | aynı (+ `model_ids`) |
| `models[] {model_id, params_sha256, status ∈ {PREDICTED, REFUSED, NOT_APPLICABLE_REGIME}, refusal, output}` | `freeze._oot_cell` (+ `not_applicable`, `model_status`; I6, I19) |
| `comparators` (8 donmuş H99 kuralı) + `comparator_note` | `freeze.OOT_COMPARATOR_RULES`, `COMPARATOR_NOTE_LAST10` / `COMPARATOR_NOTE_FROZEN` |
| `regime_tags`, `vault`, `recorded_at_utc`, `code {git_head, borsai_source_sha256}` | aynı (+ `borsai_dirty`) |
| Dizin `registry/oot/records/<T>/` | `registry.OOT_RECORDS_DIR`; `record_filename` |
| Tek toplu koşu `python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv`; tek commit | `freeze.write_oot_records` (önce hepsi bellekte, sonra 'xb'), CLI `--oot` |
| Ön koşul: kohort ve girdiler commit'li (temiz ağaç) | `freeze.oot_precondition_problems` (kohort, girdiler, kaynak belgeler, modeller; I26) |
| PENDING → MEMBER sonradan: yeni koşu, yinelenen yazılmaz | `build_oot_records` `duplicates` |
| İptal kaydı | `freeze.cancel_oot_record` (sonuç ya da D_1 satırı repoya girdiyse yapılamaz) |

Testler: `test_oot_batch_one_record_per_member_with_every_model`, `test_oot_regime_cells_and_refusals`, `test_oot_batch_requires_committed_clean_tree_and_is_all_or_nothing`, `test_oot_cancel_record_only_before_outcome`, `test_freeze_cli_oot_calls_batch_writer`, `test_real_dry_run_builds_every_member_without_writing`.

## §6 Skorlama

| Madde | Kod |
|---|---|
| D_h, tavan etiketi, L, R_h, Y_h aynen (THM'den; sabit %10 yok) | `outcomes.outcome_rows` (değişmedi) → `outcomes_oot.outcome_rows_oot` (+ `outcome_basis`; I16) |
| Metrikler ve aralık (§7–§8, B = 4000, aynı seed) | `scoring.paired_metric`, `block_bootstrap_ci` (değişmedi); `oot_obs`, `oot_cells` |
| Birincil hücreler | `scoring.OOT_PRIMARY_CELLS` (I11), `OOT_POST_D1_PRIMARY` |
| n kuralları: birincil tablo açık küme; yıl kırılımı ikincil; rejim alt kümeleri keşif; SEALED/all ayrı anahtar | `scoring.oot_model_block` (`subset = oot_pre_h99`), `oot_breakdowns` (`by_year`, `by_regime`) |
| Sayaçlar + `n_exposed_codex`, `n_spk_corporate_action_seen` | `scoring.oot_counters`, `cohort_counters` (I14) |
| Parite (kayıttaki değer skora girer) | `scoring.prediction_of_cell` (kayıt hücresi; yeniden hesap yok) |

Testler: `test_build_oot_scores_synthetic`, `test_oot_primary_cells_follow_spec_6`.

## §7 Rejim etiketleri

| Etiket | Kod | Kural kaynağı (kodda not) |
|---|---|---|
| `SALE_ON_EXCHANGE` | `registry.compute_regime_tags` | KAP BIST bildirimi "Halka Arz Yöntemi" (evren listesi `sale_method_kap`) |
| `PRICE_RANGE_BOOKBUILD` | `registry.price_is_range` (`features.parse_pb_decimal`, SPEC_PB_V0 §5 ile tek tanım) | SPK A.1 satış fiyatı |
| `TICK_TABLE_EPOCH` + `TICK_TABLE_MISMATCH` | `tick_table_epoch`, `tick_table_mismatch`, `limit_path_with` (I7) | PPP Rev. 39 cetveli; Duyuru 2023/19412 |
| `MARGIN_RULE` (+ `MARGIN_NOT_10PCT`) | `MARGIN_CHANGE = 2020-03-13` (I6, I21) | Duyuru 2020/20; 2019/65 |
| `SHORT_SELL_BAN` (+ `SHORT_SELL_BAN_2020_END_NOT_FOUND`) | `SHORT_SELL_BANS`, `calendar_window` (I9) | SPK 28/02/2020 ve 02/03/2020; SPK-B 2023/6-7 |
| `ALLOC_REGIME` | `ALLOC_REGIMES` (I8) | Karar 59/1669 (SPK-B 2021/57); i-SPK.128.21 (SPK-B 2023/21) |
| `MARKET` | kohort satırı `market` | BIST bildirimi |
| `EXPOSED_*` | kasa değeri (`EXPOSED_TICKERS`, `EXPOSURE_CLASS`; I18) | KARARLAR D2 |
| R3 ve marj → `NOT_APPLICABLE_REGIME` | `registry.regime_not_applicable`, `PATH_MODELS`, `MARGIN_MODELS` (I6) | §7 tablosu |

Testler: `test_regime_tags_follow_rule_dates`, `test_regime_not_applicable_models`, `test_exposed_archive_set_equals_members_whose_calendar_d10_is_in_archive`.

## §10 Uygulama etkisi

| Madde | Karşılık |
|---|---|
| `registry.py`: `OOT_DIR`, `read_cohort`, `validate_cohort`, `regime_tags` doğrulaması | `registry.OOT_DIR`, `read_cohort`, `validate_cohort`, `parse_regime_tags` |
| `freeze.py`: `--oot`, `record_stage = OOT_PRE_LISTING`, `--oot-post-d1` | `freeze.write_oot_records`, `write_oot_post_d1_record`, CLI |
| `outcomes.py`: `sequence_guard_oot`, `quarantine_dir` | **yeni modül** `borsai/outcomes_oot.py` (`download_gate`, `quarantine_dir`); `outcomes.py` değişmedi (var olan akış aynen) |
| `market20.py`: Takvim C | `market20.CALENDAR_C_*`, `HOLIDAY_TABLES_2020_2023`, `XU100_GAP_CLOSURES` (I15) |
| `scoring.py`: `Scale`, `class_oot`, `oot_pre_h99` bloğu, `ScaleMixError` | `SCALE_OOT`, `class_oot`, `build_oot_scores` (ayrı dosya, I1) |
| `tests/test_outcome_guard.py`: G1, G3, G5, G6 | G1, G3, G5′ ve pencere/kod/append-only bekçileri; G6 `tests/test_faz6_oot.py` |
| Uygulama: üçüncü panel | yok (sonraki görev) |

## KARARLAR D1–D8

| Karar | Kod | Test |
|---|---|---|
| D1 kohort 2020-01-01; 135 üye + GMTAS OUT_OF_SCOPE | `registry.COHORT_START`; `build_cohort_rows` evren listesinden | `test_real_cohort_validates_and_reproduces_from_code` |
| D2 kasa %50, yıl tabakalı, `PCG64(20260924)`, sıra (first_trading_date, ticker); maruz kodlar önceden çıkarılıp açık | `registry.draw_vault`, `VAULT_SEED`, `EXPOSED_TICKERS` (I4) | `test_vault_draw_is_deterministic_stratified_and_exposed_stay_open`, `test_vault_draw_on_universe_counts` |
| D3 CLAUDE.md metinleri | `CLAUDE.md` kural 3 ilk cümlesi ve sıra kuralı ek cümlesi (aynen) | `git diff` (rapor) |
| D4 eğitimde kullanım | kodda karşılık yok (bu görevde eğitim yok); SEALED küme hiçbir dosyaya ayıklanmaz | `test_sealed_codes_absent_from_every_extracted_file` |
| D5 post_d1 `MACHINE_SEQUENCED`, ayrı alt tablo; `n_exposed_archive`, `n_exposed_codex` görünür | `freeze.build_oot_post_d1_record` (`exposure_class`), `scoring.oot_post_d1_block`, `cohort_counters` | `test_d1_rows_and_oot_post_d1_record`, `test_build_oot_scores_synthetic` |
| D6-1 zip repoya girmez, karantina | `outcomes_oot.quarantine_dir`, `fetch_quarantine` | `test_no_cohort_window_bulletin_anywhere_in_repo`, `test_quarantine_dir_…` |
| D6-2 yalnız OPEN satırları; `data/outcomes_oot/<T>.csv`, ham kopyalar, `MANIFEST_OOT.csv` | `extract_code_row`, `extract_open_members`, `raw_copies`, `append_manifest_oot` | `test_extractor_reads_only_open_codes_and_never_opens_sealed` |
| D6-3 SEALED satırı hiçbir yere yazılmaz; istenirse hata | `outcomes_oot.assert_extractable` (bülten açılmadan `SealedAccessError`) | aynı |
| D6-4 kasa açılışında yeniden indirme + sha eşitliği | `outcomes_oot.open_vault` (iskelet, çağrılmaz) | `test_open_vault_skeleton` |
| D6-5 sıra kapısı ayıklanmış sonuç commit'i üzerinde; indirme de kapıya bağlı | `outcomes_oot.download_gate`, `scoring.class_oot`, `cohort_gate_ok` | `test_download_gate_…`, `test_class_oot_…` |
| D6-6 `outcome_basis = MACHINE_EXTRACTED` | `outcomes_oot.OUTCOME_BASIS`, `OOT_OUTCOME_COLUMNS`, `read_outcome_oot` | `test_extracted_rows_equal_outcomes_definitions` |
| D7 girdi toplama (Codex + doğrulayıcı) | içe aktarım bayt-eşit (S1); aday özellikler ayrı dizin (`registry/oot/candidate_features/`), model girdisi değil | `test_real_inputs_validate_and_are_byte_equal_imports` |
| D8-1 SPK kurumsal işlem satırı maruziyeti sayılır; üyeler kasaya girebilir | `registry.SPK_CORPORATE_ACTION_ROW_SEEN`, `N_SPK_CORPORATE_ACTION_ROW_SEEN`; `cohort_counters` (I14) | `test_build_oot_scores_synthetic` |
| D8-2…4 | girdi dosyalarının içinde (doğrulayıcı kararı); kod değişmez | — |
| D8-5 repoya alınacaklar | commit B: `registry/oot/{inputs,source_docs,candidate_features}`, `docs/faz6/dogrulama/` | raporda sha denetimi |

## Takvim C kaynağı (`data/raw/pay_calendar_c_20200101_20230921.csv`)

- sha256 `6dfd6134584a1a14211c3a56b5b274fef321f666bf870ce99605a97bee16fe4e`, 1360 gün, 930 seans (2020: 252, 2021: 249, 2022: 252, 2023: 177), 9 yarım gün. Sütunlar Takvim B uzatmasıyla aynı.
- Tatil tabloları (BIST Pay Piyasası, yıllık): URL ve sha256 `docs/specs_faz6/ekler/takvim_2020_2023.md` ile aynı ve dosyanın `source_pdf`, `source_pdf_sha256` sütunlarında. PDF'ler repoda değil ve bu görevde indirilmedi. Şartname görevinin yerel kopyaları (sha256'ları bu dört değerle birebir eşleşti) macOS PDFKit ile metne çevrildi; her "seans yapılmayacaktır" günü (hafta sonu dahil) tam kapanış, her "yarım gün seans yapılacaktır" günü yarım gün olarak `market20.HOLIDAY_TABLES_2020_2023`'e döküldü. Dosya bu sabitlerden üretilir (`market20.calendar_c_bytes`; test bayt eşitliği).
- Tabloda olmayan hafta içi kapanışlar: 2023-02-09, 02-10, 02-13, 02-14 (Şubat 2023 depremi) ve 2023-04-24. Kanıt yalnız pinli XU100 serisinde kapanış olmaması (resmi kapatma duyurusu bulunamadı: `ekler/kurallar_arastirma.md` §13). `source_locator = NOT_LISTED_IN_HOLIDAY_TABLE_NO_XU100_CLOSE_UNANNOUNCED_CLOSURE`, `verification_status = FAZ6_XU100_GAP_ONLY_THB_HEAD_PROBE_PENDING_S5`. S5 indirmeden önce bu beş günün THB'sini HEAD ile yoklar; yayımlanmışsa DUR (`outcomes_oot.check_xu100_gap_closures`).
- Denetim: hafta içi XU100 boşlukları (42) = Takvim C kapanışları = tablonun hafta içi tam kapanışları ∪ beş XU100-boşluk günü; yarım günlerde XU100 kapanışı var. Takvim B ile ortak aralıkta (2023-01-01…2023-09-21) tek fark bu beş gündür: B onları seans sayar (SPEC_MARKET20_V0 §1'de ölçülmüş eksik; B değiştirilmedi, H99 pencerelerine dokunmaz).
- Kullanım: eski kohort f6'sı (`market20.oot_market20`) ve D_h (`outcomes_oot.load_calendar_oot` = Takvim C ∪ H99 takvimi ∪ Faz 2A uzatması).

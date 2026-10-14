# SPEC_POST_D1_V0 §7 → kod eşlemesi (BORSAI_FAZ5_POST_D1_LIVE_20260924, commit A)

Şartname `docs/specs_faz5/SPEC_POST_D1_V0.md` §7 (değişmedi), §9, §11-13, §11-14 (`registry/post_d1/` kısmı). Bu tablo kod
yazılmadan önce çıkarıldı (görev adım 1); "Kod" sütunu uygulamadan sonra dosya:fonksiyon adlarıyla dolduruldu, satır
ve karar kümesi değişmedi. İki okumalı ya da boşluklu yerlerde lafza göre karar verildi; kararlar `docs/SPEC_DEVIATIONS.md`
H bölümünde **H28–H47** (görev kararları L1–L10 dahil). Testler `tests/test_faz5_live.py` (yeni), `tests/test_outcome_guard.py`
(§11-14 eki), `tests/test_outcomes.py` (L5).

| § | Cümle / tanım | Kod (dosya:fonksiyon) | Test | Karar |
|---|---|---|---|---|
| 7.1 | POST_D1 ayrı kayıt aşaması; SPEC_SCORING §5 `record_live` (< D_1) bu aşamaya uygulanmaz | `borsai/scoring.py: class_post_d1` (ayrı formül, `pair_class` kullanılmaz); `freeze.POST_D1_RECORD_SCHEMA` | `test_13a_…`–`test_13c_…` | — |
| 7.2 | açılış emir toplama 09:40 (tam ve yarım gün); THB D_1 akşamı yayımlanır; D2 THM kayda ALINMAZ | `registry.T_OPEN_TIME` (`09:40:00`), `registry.T_OPEN_OFFSET` (+03:00); `freeze.build_post_d1_record` yalnız D_1 tarihli THB+THM okur | `test_13g_…`, `test_record_uses_only_d1_bulletins` | H31 |
| 7.3 | `D2_cal(a)` = resmi takvimde (ilan dışı kapanışlar düşülmüş) D_1'den sonraki ilk seans; durdurmaya bakılmaz | `registry.d2_cal(d1, calendar)`; takvim `outcomes.load_calendar()` | `test_13g_…`, `test_13h_…`, `test_l6_…` | H31, H32 |
| 7.3 | `T_open(a)` = D2_cal + 09:40:00 Europe/Istanbul; yerel saat yok | `registry.t_open(d1, calendar)`; takvim dışı → `CalendarNotAvailable` (`CALENDAR_NOT_AVAILABLE`) | `test_13j_…`, `test_l6_calendar_end_…` | H31 (L6) |
| 7.3 | `record_live_post_d1` = push kanıtı(commit_record).created_at < T_open (Istanbul'a çevrilmiş) | `scoring.record_live_post_d1` (saat dilimli an karşılaştırması; kanıt `scoring.proof_time`, torun kanıtı geçerli) | `test_13a_…`, `test_13b_…` | H33 |
| 7.3 | `outcome_ingest_commit_post_d1(a)` = min(tarihi > D_1 ilk THB/THM'yi ekleyen commit, `data/outcomes/<a>.csv`'ye h ≥ 2 dolu satırı ilk yazan commit) | `scoring.outcome_ingest_commit_post_d1`, `scoring.Git.bulletin_added_commits`, `Git.first_commit_with` | `test_13a_…`, `test_13c_…`, `test_ingest_commit_post_d1_…` | H34 |
| 7.3 | bekçi: h ≥ 2 OK satırı o tarihli bülten commit'inden önce olamaz | `scoring.post_d1_outcome_order_violations` | `tests/test_outcome_guard.py::test_outcome_rows_h_ge_2_follow_bulletin_commits` (+ sentetik) | H34 |
| 7.3 | `model_prospective_post_d1` = is_ancestor(commit_frozen(m), outcome_ingest_commit_post_d1) VE kanıt var | `scoring.model_prospective_post_d1` (sonuç commit'siz → HEAD'e karşı, E15 kalıbı) | `test_13a_…`, `test_13c_…` | — |
| 7.3 | `inputs_pit_ok_post_d1` (i) base_record inputs_pit_ok (ii) her bülten atfı tam D_1 (iii) sha MANIFEST'e ve dosyaya eşit (iv) D_1 dışı seans alanı yok | `scoring.inputs_pit_problems_post_d1`; (iv) `registry.post_d1_record_problems` (tek tanım; bekçi testi de onu çağırır) | `test_13d_…`, `test_pit_post_d1_each_condition` | H35 |
| 7.3 | `class_post_d1` = LIVE / LATE_RECORD / RETRO (formül) | `scoring.class_post_d1` → `scoring.classify` (aynı saf formül) | `test_13a_…`–`test_13d_…` | — |
| 7.3 | yalnız h ≥ 2 hedefler (k = 2..10; path h ∈ {3, 5, 10}); D1 hiçbir zaman skorlanmaz; `kind = post_d1`; `_need_names` D1'i içermez | `scoring._need_names("post_d1", path=…)`, `scoring._needs`; satır hedefi `scoring.conditional_target(realized, 1)` | `test_need_names_post_d1_never_d1` | — |
| 7.3 | H99'un 99 arzı RETRO (kayıt yok) | backtest ayrı terazi (`docs/MODELS.md`); canlı blokta H99 yok (payda `ipos.csv`) | — | — |
| 7.4 | dizin `registry/post_d1/<TICKER>/<UTC-zaman>_<kısa-sha>.json` | `registry.POST_D1_DIR`; `freeze.write_post_d1_record` (`record_filename`, 'xb') | `test_record_schema_is_7_4_exactly` | — |
| 7.4 | şema `borsai.post_d1_record/1`: üst düzey alanlar, `base_record`, `d1` (thb/thm atıfları, `fields_raw` ham metin, `ceiling_close_D1`, `lock_consistency`), `d1_features`, `models_index`, `models[]`, `comparators_conditional`, `summary` | `freeze.build_post_d1_record`, `freeze.d1_block`, `freeze.POST_D1_FIELDS` | `test_record_schema_is_7_4_exactly`, L4 prova | H36, H37 |
| 7.4 | bekçi: `registry/post_d1/` altında yalnız `d1` bloğunda ve yalnız D_1 tarihli alanlar; h ≥ 2 anahtarı ya da D_1 dışı bülten sha'sı → kırmızı | `registry.post_d1_record_problems`; gerçek repo taraması `tests/test_outcome_guard.py::test_post_d1_records_carry_only_d1_fields` | `test_post_d1_guard_red_on_*` (sentetik) | H35 |
| 7.4 | `base_record` = SPEC_SCORING §6 `ceiling_hazard_v0` birincil kaydı (D_1'den önce kanıtlı f3'lü en son; yoksa en erken LATE adayı); f1–f3 o kaydın `model_inputs`'undan | `freeze.select_base_record` → `registry.select_primary` (aynı kural), adaylar `scoring.registry_candidates` | `test_base_record_selection_…`, `test_13e_…` | H38 |
| 7.4 | uygun kayıt yoksa POST_D1 kaydı yazılmaz; payda `SKIPPED_POST_D1: NO_PRE_LISTING_RECORD` | `freeze.NoBaseRecord`; payda `scoring.post_d1_denominator` | `test_13e_…` | — |
| 7.4 | `models[]`: INDEX_POST_D1.json'daki her model; parent sha INDEX.json ile denetlenir | `freeze._post_d1_models` (INDEX_POST_D1 sha'ları + parent/path INDEX.json), `predict_post_d1.predict_post_d1` | `test_record_models_equal_direct_predict` | H36 |
| 7.4 | `comparators_conditional` kayıttan kopya, `conditional_weights` ile S_cond; skorlamada Faz 2C j = 1 satırıyla \|Δ\| ≤ 1e-12 parite | `freeze.comparators_conditional`; `scoring.post_d1_comparator_parity` | `test_13i_…`, L4 prova | H39 |
| 7.4 | birincil POST_D1 kaydı = T_open'dan önce kanıtlı en erken; yoksa inputs_pit_ok_post_d1 olan en erken | `registry.select_primary_post_d1` | `test_select_primary_post_d1` | — |
| 7.4 | `DUPLICATE_RECORD`: aynı base_record sha + iki bülten sha + INDEX sha | `freeze.write_post_d1_record` (`DuplicateRecord`) | `test_duplicate_post_d1_record` | — |
| 7.4 | iptal `record_type = CANCELLATION` aynı dizinde; T_open'dan itibaren yapılamaz | `freeze.cancel_post_d1_record` (`registry.post_d1_cancel_allowed`) | `test_13f_…` | — |
| 7.4 | akış: `outcomes update --through <D_1>` → commit → `freeze --post-d1 <T>` → commit → push → push_proof | `outcomes.update`, `freeze.main --post-d1`, `push_proof.main`; `docs/faz5/POST_D1_AKISI.md` | `test_update_downloads_d1_bulletins_…` | L10 |
| 7.4 | `sequence_guard`, `registry/post_d1/` altındaki commit edilmemiş dosyaları da engeller | `outcomes.sequence_guard` | `test_sequence_guard_blocks_on_uncommitted_post_d1` | L7 |
| 7.5 | FROZEN her arz için POST_D1 aşaması satırı: D1 tavan → kayıt beklenir (yoksa `SKIPPED_POST_D1: NO_POST_D1_RECORD`); D1 değil → `NOT_APPLICABLE`; D1 NA → `NOT_SCORABLE_D1_LABEL_NA` | `scoring.post_d1_denominator` | `test_denominator_rows_…` | H29 (L2) |
| 7.5 | j = 1 koşullu blokta `n_scored / n_refused / n_skipped / n_not_applicable / n_target_unavailable / n_live / n_late` | `scoring.post_d1_block` → `scores/scores_post_d1.json` (`borsai.scores_post_d1/1`) | `test_post_d1_block_counts_…`, B | H28 (L1), H29 |
| 7.5 | bugünkü 7 arz RETRO → `retro_info`, hiçbir n'e girmez | `scoring.post_d1_block` (RETRO önce) | `test_real_seven_are_retro_info_only` | H30 (L3) |
| 7.6 | `THB_COLUMNS` eki (8 ad + H19 iki özel işlem alanı), `ThbRow` ham alanları, `REQUIRED` genişler, `OUTCOME_COLUMNS` değişmez | `outcomes.THB_COLUMNS`, `THB_D1_COLUMNS`, `REQUIRED`, `ThbRow`, `parse_bulletin` | `test_l5_…` (başlık birebir, sonuç CSV bayt-eşit) | L5 |
| 7.6 | `registry.py`: `POST_D1_DIR`, `select_primary_post_d1`, `t_open` | aynı adlar | yukarıda | — |
| 7.6 | `freeze.py`: `build_post_d1_record`, `--post-d1`; `model_kind` → `post_d1`; `run_model` yeni tür | `freeze.build_post_d1_record`, `run_post_d1_model`, `main` | yukarıda | — |
| 7.6 | `scoring.py`: `pair_class_post_d1`, `outcome_ingest_commit_post_d1`, j = 1 koşullu bloğa POST_D1 satırı, `_need_names("post_d1")` | `scoring.class_post_d1` (= `pair_class_post_d1`), `post_d1_block`, `post_d1_row` | yukarıda | H28 |
| 7.6 | `tests/test_outcome_guard.py`: `registry/post_d1/` istisnası; h ≥ 2 OK satırı bülten commit'inden önce olamaz | iki yeni test + sentetik | — | — |
| §4 | birincil hücre: koşullu RPS_1 vs `ceiling_hazard_v0` koşullu; kurallar; ikincil Brier k = 2, 10; kalibrasyon; path h ∈ {3, 5, 10} | `scoring.POST_D1_CELL_SPECS`, `post_d1_cells`, `post_d1_descriptive` (ortak `predict_path.conditional_rps/brier`, `_s_part`, `_path_part`) | `test_post_d1_cells_…` | H40 |
| §4, §6.1-10 | ölçek ayrımı: `live_post_d1` hiçbir şeyle birleşmez | `scoring.SCALE_LIVE_POST_D1`, `_one_scale`, `merge_scales` | `test_scale_mix_post_d1` | — |
| SPEC_SCORING §8 | n < 10 yalnız satır; 10 ≤ n < 30 "yetersiz örnek"; aralık n ≥ 10 ve ≥ 6 blok | `scoring.paired_metric`, `verdict` (aynı) | `test_post_d1_cells_…` | — |
| §9 | ret/uyarı kodları kayıtta; `D1_NOT_TRADED` kayıt yazılmaz; `PARAMS_INVALID` / `SCHEMA_UNSUPPORTED` kayıt yazılmaz | `freeze.run_post_d1_model` (ERROR → `FreezeError`) | `test_record_refusal_codes_…` | H23 (errata), H41 |
| §11-11 | `path_conditional` null → satır `NOT_PRODUCED` (TARGET_UNAVAILABLE değil) | `scoring.post_d1_row` (`path_status`) | `test_path_not_produced` | H42 |
| §11-13 | (a)–(j) geçici git depolarında | `tests/test_faz5_live.py::test_13a…test_13j` | — | — |
| L4 | NETGL uçtan uca prova (geçici klon) | `tests/test_faz5_live.py::test_l4_netgl_end_to_end` → `docs/faz5/ekler/prova_netgl.txt` | — | — |
| L8 | donmuş JSON `training.cutoff_date` = 2026-08-13 (δ eğitim arzlarının 10 seansının en geç tarihi; kesim değil) | `scoring.post_d1_card` (`training_last_session_date`, `training_cutoff_spec`) | `test_l8_card_does_not_call_it_cutoff` | H43 |
| L9 | skor yeniden üretiminde kart sayacı 20; H22 istisnası kendiliğinden kapanır | `tests/test_faz5_live.py::test_l9_…`; `tests/test_faz4_ceiling_path.py`, `tests/test_scoring.py` sayaç satırları | — | H44 |

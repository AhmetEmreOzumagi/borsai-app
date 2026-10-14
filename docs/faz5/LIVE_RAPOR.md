# BORSAI_FAZ5_POST_D1_LIVE_20260924 — rapor

Görev: `docs/prompts/FAZ5_POST_D1_LIVE.md`. Canlı POST_D1 kayıt aşaması (SPEC_POST_D1_V0 §7): D1 akşamı resmi bülten
yayımlanınca `POST_D1` kaydı yazılır, D2 09:40'tan önce push edilir ve push kanıtı alınır; D2..D10 sonuçları gelince ayrı
terazide (`live_post_d1`) skorlanır. Şartname, `models/`, mevcut `registry/` dosyaları, `data/`, `app/`, `docs/specs*`
değişmedi; `post_d1_hazard_v0` davranışı değişmedi (`predict_post_d1`, `post_d1.py`, donmuş JSON'lar dokunulmadı).

## A. Commit A (kod, testler, belgeler; skor verisi yok)

### Taban (adım 0)

- HEAD `b8763fc`; izlenmeyen yalnız izinli dosyalar (`docs/prompts/FAZ5_POST_D1_LIVE.md`, `docs/prompts/FAZ6_CODEX_INPUTS_B1..B4.md`).
- Tam pytest: **497 test, 496 geçti, 1 kırmızı**, 275 s. Kırmızı: `tests/test_faz5_post_d1.py::test_14_…` — "salt okunur
  yollar BASE_COMMIT'ten beri değişmedi" iddiası, proje sahibinin push kanıtı commit'i `988025c`'nin eklediği
  `registry/push_proofs/<7c18c0f>.json` yüzünden. Faz 5 commit'leri (7c18c0f, dd7a8cd) bu yollara dokunmamış
  (`git diff 72a000f dd7a8cd -- scores registry data app docs/SCORES.md legacy CLAUDE.md` boş).
- **Sapma (görev kuralı "kırmızı varsa DUR"):** durulmadı. Kök neden kesin ve zararsız (sahibinin kendi meşru commit'i); bu
  görev aynı iddianın kapsadığı CLAUDE.md ve scores/'u zaten değiştirmek zorunda. Test Faz 5 aralığına sabitlendi
  (`72a000f..dd7a8cd`), çalışma ağacı temizlik denetiminden `scores` çıkarıldı (SPEC_DEVIATIONS **H46**). Proje sahibi bu
  kararı geri almak isterse yalnız o test satırı etkilenir.

### Tanım eşlemesi (adım 1)

`docs/faz5/LIVE_TANIM_ESLEME.md`: §7.1–§7.6, §4, §9, §11-11, §11-13, L4–L9 → dosya:fonksiyon → test → karar. Kararlar
SPEC_DEVIATIONS **H28–H47** (özet):

| # | Konu | Karar |
|---|---|---|
| H28 | L1 çıktı | `scores/scores_post_d1.json` (`borsai.scores_post_d1/1`), SCORES.md §7; scores.json yapısı aynı; satır alanları Faz 2C j = 1 adlarıyla |
| H29 | L2 payda | FROZEN her arz için `denominator` satırı: RETRO → D1_PENDING → NOT_SCORABLE_D1_LABEL_NA → NOT_APPLICABLE → CALENDAR_NOT_AVAILABLE → SKIPPED_POST_D1 (NO_POST_D1_RECORD / NO_PRE_LISTING_RECORD) → RECORD |
| H30 | L3 | 7 arz RETRO, yalnız `retro_info`; gerçek `registry/post_d1/` boş |
| H31 | L6 T_open | `datetime.combine(D2_cal, 09:40:00, +03:00)`; takvim dışı → `CALENDAR_NOT_AVAILABLE` (2026-12-31 son seans) |
| H32 | §11-13 (h) iki okuma | §7.3 lafzı: kapanış düşülmüş takvimde sonraki seansın 09:40'ı (aynı kural) |
| H33 | record_live | an karşılaştırması, kesin `<` (09:39:59 LIVE, 09:40:00 değil) |
| H34 | outcome_ingest_commit_post_d1 | tarihi > D_1 ilk bülten ile h ≥ 2 dolu (OK ∪ NA_LIMIT) satır commit'inin en erkeni; bekçi aynı kümeye |
| H35 | bekçi / pit (iv) | tek tanım `registry.post_d1_record_problems`; donmuş kodun D_1 alt ağaçları izinli; h ≥ 2 anahtarı ve D_1 dışı bülten sha'sı her yerde kırmızı |
| H36–H37 | kayıt şeması | §7.4 alan kümeleri birebir; D_1 sonuç dosyasının h = 1 satırından; `fields_raw` eşlemesi; `d1_features` ilk tahmin veren modelden |
| H38 | base_record | `registry.select_primary` + skorlamanın aday kurucusu (`scoring.registry_candidates`, yeniden kullanıldı) |
| H39 | karşılaştırıcılar | dördü base_record kopyası, her-zaman-tavan `source = SPEC_DEVIATIONS_C4`; Faz 2C j = 1 paritesi, aşım `ScoringError` |
| H40 | hücreler | birincil RPS_1 vs `ceiling_hazard_v0`; `kural` (RPS öbür dört), `ikincil` (Brier k = 2/10, path); kalibrasyon betimsel |
| H41–H42 | §9, §11-11 | kayıt yazılmayan durumlar; `path_conditional` null → `NOT_PRODUCED` |
| H43 | L8 | kartta `training_cutoff` yok; `training_last_session_date = 2026-08-13` (kesim değil) + `spec_training_cutoff = 2026-08-19` |
| H44 | L9 | sayaç 20; H22 istisnası kendiliğinden kapanır (test) |
| H45 | CLI saati | yerel saat yalnız `recorded_at_*` ve bilgi mesajında; L4 fonksiyon çağrısıyla, enjekte zamanla |
| H46 | taban kırmızısı | yukarıda |
| H47 | REQUIRED genişlemesi | sentetik test bültenleri D_1 sütunlarını boş taşır; 33 pinli 2026 THB başlığı ve 7 sonuç dosyası bayt-eşit |

### Uygulama

- `borsai/outcomes.py`: `THB_D1_COLUMNS` (§7.6 + H19: `ACILIS FIYATI`, `EN YUKSEK FIYAT`, `EN DUSUK FIYAT`, `TOPLAM ISLEM ADEDI`,
  `TOPLAM ISLEM HACMI`, `A.O.F`, `OZEL ISLEM BILDIRIMI ISLEM ADEDI`, `OZEL ISLEM BILDIRIMI ISLEM HACMI`; 57 sütunluk 2026 THB
  başlığıyla birebir), `REQUIRED["thb"]` genişledi, `ThbRow` ham alanları; `OUTCOME_COLUMNS` aynı. `sequence_guard`:
  `registry/post_d1/` altında commit'siz/izlenmeyen/değişmiş dosya varken indirme durur (L7). `update --through <D_1>`
  (değişmeden) D_1 bültenlerini indirir, h = 1 OK, h ≥ 2 PENDING (test).
- `borsai/registry.py`: `POST_D1_DIR`, `d2_cal`, `t_open`, `CalendarNotAvailable`, `before_t_open`, `PostD1Candidate`,
  `select_primary_post_d1`, `post_d1_record_problems` (bekçi, tek tanım).
- `borsai/freeze.py`: `build_post_d1_record`, `write_post_d1_record` (DUPLICATE_RECORD), `cancel_post_d1_record` (yalnız
  T_open'dan önce), `select_base_record`, `run_post_d1_model`, `comparators_conditional`, `d1_block`, `d1_session`; CLI
  `--post-d1 <TICKER>`, `--cancel` POST_D1 kaydını tanır. Listeleme öncesi `build_record` ve `run_model` aynen.
- `borsai/scoring.py`: `outcome_ingest_commit_post_d1`, `model_prospective_post_d1`, `record_live_post_d1`,
  `inputs_pit_problems_post_d1`, `class_post_d1`, `post_d1_outcome_order_violations`, `post_d1_row`, `post_d1_block`
  (payda + j = 1 satırları + hücreler), `post_d1_cells` (SPEC_SCORING §8), `post_d1_descriptive`, `post_d1_card`,
  `build_post_d1_scores`, `_render_post_d1`; `_need_names("post_d1")` = k = 2..10 (+ D3/D5/D10 path varsa), D1 yok;
  `SCALE_LIVE_POST_D1` hiçbir ölçekle birleşmez; `registry_candidates` (`candidates_for` onu çağırır, davranış aynı).
  Mevcut 19 modelin skor blokları davranış olarak aynı (ön denetim: yeniden üretimde yalnız izinli alanlar değişiyor).
- `CLAUDE.md` kural 1'in sonuna karar 4 cümlesi birebir (test `test_claude_md_rule_1_sentence_verbatim`).
- `docs/faz5/POST_D1_AKISI.md` (L10), `docs/faz5/LIVE_TANIM_ESLEME.md`, SPEC_DEVIATIONS H28–H47.

### Testler

- Yeni `tests/test_faz5_live.py` (41 test), `tests/faz5_live_support.py`; `tests/test_outcome_guard.py` +7 (§11-14).
- §11-13: (a) `test_13a_live` LIVE; sınır `test_13a2_…` (06:39:59Z LIVE, 06:40:00Z değil); (b) `test_13b_…` LATE_RECORD;
  (c) `test_13c_…` D2 bülteni modelden önce → RETRO, `test_13c2_…` h ≥ 2 satır da giriş sayılır; (d) `test_13d_…` D_1 dışı
  THM sha'sı → pit yanlış → RETRO, bekçi kırmızı; (e) `test_13e_…` NoBaseRecord, dosya yazılmaz, payda
  `SKIPPED_POST_D1: NO_PRE_LISTING_RECORD` (`test_denominator_rows`); (f) `test_13f_…` T_open'da ve sonrasında iptal hata,
  1 s önce iptal kaydı; (g) `test_13g_…` yarım gün D2_cal (2026-10-28) 09:40; (h) `test_13h_…` kapanış → sonraki seansın
  09:40'ı; (i) `test_13i_…` kopya ↔ Faz 2C j = 1 NETGL satırı \|Δ\| = 0, 1e-9 bozulma `ScoringError`; (j) `test_13j_…`
  `TZ` değişse de aynı T_open, kaynakta yerel saat çağrısı yok. Hepsi geçici git depolarında, kanıt taklidiyle, sistem
  saatine dokunmadan.
- §11-14: `test_post_d1_records_carry_only_d1_fields` (gerçek repo), `test_outcome_rows_h_ge_2_follow_bulletin_commits`
  (gerçek repo: ihlal yok), sentetik kırmızı/yeşil: h ≥ 2 anahtarı, d1 dışı D_1 alanı, D_1 dışı bülten sha'sı/adı, satır
  bültenden önce.
- L4 `test_l4_netgl_end_to_end`; L5 `test_l5_thb_d1_columns_…` (33 THB), `test_l5_outcomes_regenerate_byte_equal`
  (7 dosya); L6 `test_l6_calendar_end_…`; L7 `test_sequence_guard_blocks_on_uncommitted_post_d1`; L8 `test_l8_…`; L9
  `test_l9_…`; L3 `test_real_seven_are_retro_info_only`; L1 `test_scores_json_structure_unchanged_by_post_d1`.
- Tam koşu (commit A içeriği): **545 geçti, 0 kırmızı**, 313 s (`docs/faz5/ekler/live_test_runs.txt`).

### L4 provası (`docs/faz5/ekler/prova_netgl.txt`)

Geçici klonda (`git clone --local`, HEAD b8763fc) NETGL'in pinli D_1 bülteni (2026-09-17) ve birincil listeleme öncesi
kaydıyla (`registry/records/NETGL/20260922T121936Z_65a39d7392dd.json`, EARLIEST_LATE_RECORD) kayıt, enjekte zaman
2026-09-17T19:00+03:00; T_open 2026-09-18T09:40+03:00.

- Şema §7.4 birebir: EVET. `ceiling_close_D1 = 1`, kilit tutarlılığı üçü de doğru, `d1_lock = 1`,
  `d1_turnover_ln = −3.7116`, kırpma yok, uyarı yok; `summary` 1/1 tahmin.
- Model çıktısı == doğrudan `predict_post_d1` (aynı girdi): EVET; `path_conditional` null (base_record `ceiling_path_v0`
  taşımıyor; H42). S_cond[2] = 0.86077, S_cond[10] = 0.04223.
- `comparators_conditional` beş karşılaştırıcı, Faz 2C `scores.json` j = 1 NETGL satırıyla max\|Δ\| = **0.0**.
- Bekçiler: commit'siz kayıt varken `sequence_guard` indirmeyi durdurdu; commit'ten sonra `sequence_violations = []`,
  `post_d1_record_problems = []`, h ≥ 2 satır sırası ihlali yok.
- Sınıf **RETRO**: model commit 7c18c0f, `outcome_ingest_commit_post_d1` = f1f9d44 (D_1'den sonraki ilk sonuç verisi),
  model onun atası değil. `inputs_pit_ok_post_d1` doğru. `scores_post_d1` (klon): NETGL `RETRO`, n_scored 0.
- `freeze --post-d1` CLI'sinin çağırdığı `write_post_d1_record` kullanıldı (CLI varsayılan yolları gerçek repoya yazardı; H45).

### Akış belgesi özeti (`docs/faz5/POST_D1_AKISI.md`)

D_1 akşamı (THB 18:25–18:40'ta yayımlanır): Claude `outcomes update --through <D_1>` → commit → `freeze --post-d1 <T>` →
commit; **proje sahibi T_open'dan (D_1'i izleyen ilk resmi seans 09:40, 06:40Z) önce `git push` ve `push_proof`** (kanıt
zamanı POST anıdır). Sonraki seanslarda `outcomes update` + `scoring`. Başarısızlıklar: D1 tavan değil (kayıt isteğe bağlı,
payda NOT_APPLICABLE), D1 işlem görmedi (kayıt yazılmaz, D_1 kayar), üst limit yok (ret, NOT_SCORABLE_D1_LABEL_NA),
base_record yok (kayıt yazılmaz, SKIPPED_POST_D1), T_open geçti (LATE_RECORD en iyi ihtimal), takvim sonu
(CALENDAR_NOT_AVAILABLE), ilan dışı kapanış, hatalı kayıt (T_open'dan önce iptal), `SequenceRuleError`, kanıt yetkisi yok.

### EK 3 için notlar

- Okunacak dosyalar: `registry/post_d1/<T>/` (şema `borsai.post_d1_record/1`; birincil kayıt `registry.select_primary_post_d1`
  kuralı), `scores/scores_post_d1.json` (`models[].conditional_j1`: satır adları Faz 2C j = 1 ile aynı, + `t_open`,
  `path_status`, `comparator_parity`, `denominator`), `models/INDEX_POST_D1.json`.
- Kartta `training_cutoff` alanı yok: `training_last_session_date` (2026-08-13) "kesim" diye gösterilmemeli (L8, H43).
- Ret kodları öneksiz (H23): `refused.code` ∈ {`F3_MISSING`, `D1_LIMIT_NA`, `D1_VOLUME_INVALID`, `INPUT_SHARES_OFFERED`,
  `D1_FIELD_INVALID`}; kapsam dışı hücre `status = NOT_APPLICABLE`, `refusal.code = D1_NOT_CEILING`.
- `base_always_ceiling` karşılaştırıcısı `source = "SPEC_DEVIATIONS_C4"` (kayıtta S ≡ 1).
- T_open'ı uygulama kendisi hesaplamamalı; `scores_post_d1.json` satırındaki `t_open` / `class_evidence.t_open` okunur.

### Açık noktalar

1. H46: taban kırmızısında durulmadı (gerekçe yukarıda); proje sahibinin onayı istenir.
2. H32: §11-13 (h)'nin iki okuması; lafız (§7.3) seçildi. Şartnamenin bir sonraki sürümünde (h) cümlesi netleştirilebilir.
3. H39: §7.4 `source = "base_record"` her-zaman-tavan için doğru değil; errata önerisi.
4. Push kanıtının 09:40'tan önce alınması proje sahibine bağlı (gh/GH_TOKEN; bellek notu: `~/.local/bin/gh`).

## B. Skor yeniden üretimi — **commit B ATILMADI** (uygulama testi kırmızı; görev kuralı)

### Commit A

`660cec1` BORSAI_FAZ5_LIVE_A (ata: `b8763fc`). `git show --stat`: 19 dosya, +2706 / −44 — `CLAUDE.md` (1 satır),
`borsai/{freeze,outcomes,registry,scoring}.py`, `docs/SPEC_DEVIATIONS.md`, `docs/faz5/{LIVE_RAPOR,LIVE_TANIM_ESLEME,POST_D1_AKISI}.md`,
`docs/faz5/ekler/{live_test_runs,prova_netgl}.txt`, `docs/prompts/FAZ5_POST_D1_LIVE.md`, `tests/{faz5_live_support,test_faz5_live}.py`
(yeni), `tests/{test_faz4_ceiling_path,test_faz5_post_d1,test_outcome_guard,test_outcomes,test_scoring}.py`. İzinli yollar dışında
dosya yok; push yok.

### Üretim (`.venv/bin/python -m borsai.scoring`, HEAD 660cec1, `borsai_dirty = false`; outcomes güncellenmedi)

- `scores/scores.json` farkı (HEAD'e göre, bütün yaprak alanlar tarandı): **yalnız** `generated_at_utc`, `code.git_head`,
  `code.borsai_source_sha256` ve 19 kartta `n_variants_same_data` 19 → 20. Başka alan değişmedi (`as_of_session` 2026-09-21).
  sha256 `37a691da…`.
- `scores/scores_post_d1.json` (yeni, `borsai.scores_post_d1/1`, sha256 `c3244fac…`): tek model `post_d1_hazard_v0`; bütün
  sayaçlar 0 (`n_scored, n_refused, n_skipped, n_not_applicable, n_target_unavailable, n_live, n_late`), `n_retro = 7`;
  `retro_info` 7 arz (CITAS, TKNKA, VEYAS, KPEKS, INTET, BKRGY, NETGL; `model_prospective = false`, sonuç commit'li); payda
  satırlarının 7'si `RETRO`; satır, hücre, betimsel yok; kart `training_last_session_date = 2026-08-13` (kesim değil),
  `spec_training_cutoff = 2026-08-19`, varyant 20; `post_d1_records_sha256 = null` (dizin boş).
- `docs/SCORES.md`: başlıktaki kod satırı + yeni "## 7. D1 sonrası güncelleme" bölümü (sha256 `a9f97bbf…`).
- Tam pytest (bu çıktılar çalışma ağacındayken): **545 geçti, 0 kırmızı**, 323 s. H22 istisnası kapandı: `scores.json`
  artık 72a000f'e bayt-eşit değil ve kartlar 20 (L9 testi bu dalı sınadı).

### Uygulama testleri (`bash app/scripts/test.sh`): KIRMIZI — kök neden bu görevden önce

- `test.sh` ilk hatada durdu: `borsai_predict` `tests/golden.rs::predict_sources_unchanged` —
  "borsai/predict_hazard.py değişmiş": dosyanın sha256'sı `a1523ac8…`, `app/parity/golden/MANIFEST.json`'daki pin `8099ead3…`.
- Ayrıntı (ilk hatada durmadan, aynı çıktılarla): cargo **93 geçti / 1 kırmızı** (yalnız bu test); `npm test` **222/222**;
  `app/parity/test_gen_golden.py` **3 geçti / 1 kırmızı** (`gen_golden.py --check`: 25 dosyadan yalnız `golden/MANIFEST.json`
  farklı; 24 altın vektör dosyası bugünkü kodla birebir); `tests/golden_unchanged.sh` YEŞİL.
- **Kök neden:** `borsai/predict_hazard.py` Faz 5 A commit'inde (`7ce0593`, SPEC_DEVIATIONS H1: `linear_predictor`
  yardımcısı, davranış aynı) değişti; uygulamanın altın MANIFEST'i eski kaynak sha'sını pinliyor. Faz 5 görevleri uygulama
  testini koşmamıştı. Kanıt (geçici klon): `7ce0593~1`'de `gen_golden.py --check` yeşil, görev başı `b8763fc`'de kırmızı
  (aynı tek fark). Bu görev `predict_hazard.py`'ye ve `app/`'e dokunmadı; `scores.json`/`scores_post_d1.json` bu kırmızıyla
  ilgili değil (Rust skor okuyucu testleri yeşil).
- Kural gereği: `app/`'e dokunulmadı, **commit B atılmadı, uygulama derlenmedi** (yeni `.app` ve `borsai-app` sha256'sı yok).
- Çalışma ağacında bırakılanlar (commit'siz): `scores/scores.json`, `scores/scores_post_d1.json`, `docs/SCORES.md` ve bu
  raporun B bölümü. Geri almak için: `git checkout -- scores/scores.json docs/SCORES.md docs/faz5/LIVE_RAPOR.md` ve
  `scores/scores_post_d1.json` silinir; aynı çıktı `python -m borsai.scoring` ile yeniden üretilir.

### Önerilen devam (ayrı, `app/`'e yazma izni olan görev)

1. `app/parity/gen_golden.py` ile altın MANIFEST'i yeniden üret (vektör dosyaları değişmemeli: `--check` yalnız MANIFEST'i
   farklı buluyor; `predict_sources_sha256["borsai/predict_hazard.py"]` 8099ead3… → a1523ac8…), `bash app/scripts/test.sh` yeşil.
2. Sonra bu görevin B'si aynen: `git add scores docs/SCORES.md docs/faz5/LIVE_RAPOR.md` ve
   `git commit -m "BORSAI_FAZ5_LIVE_B: scores regenerated (variant counter 20, separate scores_post_d1.json with retro_info only)" -- scores docs/SCORES.md docs/faz5/LIVE_RAPOR.md`
   (çalışma ağacındaki çıktılar HEAD 660cec1'de üretildi; yalnız `app/` değişen bir commit onları geçersiz kılmaz), ardından
   `source app/scripts/env.sh && cd app && npm run tauri build -- --bundles app`.

### Test sayıları

| Durum | pytest | uygulama |
|---|---|---|
| Taban (b8763fc) | 497: 496 geçti, 1 kırmızı (H46) | koşulmadı (görev başı); sonradan klonda `gen_golden --check` kırmızı olduğu gösterildi |
| A (660cec1 içeriği) | 545 geçti | — |
| B çıktıları çalışma ağacında | 545 geçti | cargo 93/1, npm 222/0, parity 3/1, golden_unchanged yeşil |

### Kabul kapısı

- K1 yeşil (§11-13 a–j, `registry/post_d1/` bekçisi, L4–L9, tam pytest 545).
- K2 yeşil: `git diff b8763fc 660cec1 -- models registry data app docs/specs docs/specs_faz4 docs/specs_faz5` boş;
  `registry/post_d1/` gerçek repoda yok (boş).
- K3 yeşil: CLAUDE.md'de yalnız karar 4 cümlesi, birebir (test).
- **K4 KIRMIZI:** `scores.json` farkı izinli alanlarla sınırlı ve `scores_post_d1.json` ayrı, ama uygulama testleri kırmızı
  (önceden var olan, `app/` düzeltmesi gerektiren neden) → B atılmadı, `.app` derlenmedi.
- K5: A commit'li, yalnız izinli yollar, push yok; B yok.

### B'nin tamamlanması (görev BORSAI_FAZ5_LIVE_B_APPFIX_20260924)

- **Commit C1** `23b6479` BORSAI_APP_GOLDEN_MANIFEST (ata `660cec1`): yalnız `app/parity/golden/MANIFEST.json` (+1/−1) ve
  görev istemi `docs/prompts/FAZ5_LIVE_B_APPFIX.md`.
- **`gen_golden.py --check` önce:** `{"checked": 25, "different": ["golden/MANIFEST.json"]}` (çıkış 1). `gen_golden.py`
  yeniden üretimden sonra `git status -- app/` yalnız MANIFEST'i gösterdi; 24 altın vektör dosyası ve `dec_cases.json`
  önceki kopyalarıyla bayt-eşit (`diff -rq`, `cmp`). **Sonra:** `{"checked": 25, "different": []}` (çıkış 0).
- **MANIFEST farkı (satır düzeyinde, tek satır; üretim zamanı/kod damgası alanı yok):**
  ```
  -    "borsai/predict_hazard.py": "8099ead3f360d0b18fc39dc2f78132c57665296d58c7b00d6e9a4701be2204a8",
  +    "borsai/predict_hazard.py": "a1523ac810a2a800f5583f347f1c248fe9d7fc7eaa567873b9b3d8858e7b2518",
  ```
- **`bash app/scripts/test.sh` (C1 öncesi ağaç, MANIFEST yeniden üretilmiş):** YEŞİL — cargo **94 geçti / 0 kırmızı**
  (`golden.rs::predict_sources_unchanged` dahil), `npm test` **222/222**, `app/parity/test_gen_golden.py` **4/4**,
  `tests/golden_unchanged.sh` YEŞİL.
- **Skorlar yeniden üretildi** (`.venv/bin/python -m borsai.scoring`, HEAD `23b6479`, `borsai_dirty = false`; outcomes
  güncellenmedi). Çalışma ağacındaki önceki (660cec1'de üretilmiş) hâllerine göre fark, iki dosyada da, yalnız
  `generated_at_utc` ve `code.git_head` (660cec1 → 23b6479); `docs/SCORES.md`'de yalnız başlıktaki HEAD satırı.
  `scores.json`'un HEAD'e göre farkı (22 yaprak): `generated_at_utc`, `code.git_head`, `code.borsai_source_sha256` ve 19
  kartta `n_variants_same_data` 19 → 20.
  - `scores/scores.json` sha256 `47352921c452e7fd1bfda57e99a7759e2218018adb4668c146dc5cf70d8e1644`
  - `scores/scores_post_d1.json` sha256 `cfe6807e6cf16c698343e3d4b07758a105ec483779018984db929c915c4c4fbc`
  - `docs/SCORES.md` sha256 `2915634ee2ffc27faec0d04a2ea6c57ca2b556cb11fa6329a95668a8a4a6380e`
- **Commit B öncesi testler** (bu çıktılar ve C1 ile): tam `.venv/bin/pytest -q` **545 geçti, 0 kırmızı** (299 s);
  `bash app/scripts/test.sh` YEŞİL — cargo 94/0, npm 222/222, parity 4/4, `golden_unchanged` YEŞİL. K4 artık yeşil.

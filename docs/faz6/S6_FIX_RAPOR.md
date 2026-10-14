# BORSAI_FAZ6_S6_FIX_20260925 — eski kohort POST_D1 bloğu canlı tanıma uyduruldu (B1, B2, B3)

Uygulayıcı: Claude Code (Opus 5.5), yeni oturum (S6'yı koşan oturum değil). Tarih: 2026-09-25. Ağ kullanılmadı. push, tag ve amend
yapılmadı.

Bu görev sonuçlara bakmadı. Gerçek repoda `python -m borsai.scoring --oot` ya da `build_oot_scores` koşulmadı. `data/outcomes_oot/`,
`registry/oot/d1_rows/`, `registry/oot/post_d1/` ve `docs/fable_faz6_s6/` açılmadı. Bütün doğrulama sentetik git deposunda yapıldı
(`tests/test_faz6_oot.py` `scored_repo` kalıbı). Tam pytest kendi gerçek-repo testlerini (bekçiler) koştu. Bu raporda hiçbir üyenin
kodu, fiyatı ya da hücre değeri yok. Geçen kodlar (SYNA, SYNZ …) sentetiktir.

## 1. Commit

| Commit | İçerik |
|---|---|
| bu raporu ekleyen commit | `BORSAI_FAZ6_S6_FIX`: `borsai/scoring.py`, `tests/test_faz6_s6_fix.py` (yeni), `tests/test_outcome_guard.py`, `docs/SPEC_DEVIATIONS.md` (I42–I45), bu rapor, görev dosyası. Bir commit kendi hash'ini içeremez; `git log -1 --format=%H -- docs/faz6/S6_FIX_RAPOR.md` ile okunur. |

Taban: HEAD `e79a4b7`. Çalışma ağacında yalnız izinli izlenmeyenler vardı: `docs/faz6/ekler/s6_denetim.txt`,
`docs/faz6/ekler/s6_test_runs.txt` (S6 oturumunun dosyaları; bu commit'e girmedi) ve görev dosyası.

Hiçbir model, kayıt, sonuç satırı ya da skor tanımı değişmedi. Kod şartnameye uyduruldu; model_id'ler aynı kalır. `borsai/scoring.py`
içinde değişen yerler: `oot_post_d1_block`, onun iki yeni yardımcısı (`_oot_post_d1_params`, `_oot_d1_label_agrees`) ve
`build_oot_scores`'taki tek `retro_info` satırı. Canlı `post_d1_block`, `post_d1_row`, `_d1_label`, `post_d1_cell_specs`,
`scores.json` ve `scores_post_d1.json` üreticileri ile `render_oot_doc` aynen kaldı.

## 2. Adım 0: taban

- `app/parity/gen_golden.py --check`: 25 dosya denetlendi, fark yok.
- `.venv/bin/pytest -q -p no:cacheprovider` (önbellek dizini yazılmasın diye; test kümesi `pytest -q` ile aynı): 625 passed,
  6 dk 38 s, çıkış 0.
- `bash app/scripts/test.sh`: cargo 94 geçti / 0 kaldı; npm 222; parity 4; golden_unchanged YEŞİL; çıkış 0.

## 3. Düzeltmeler (F1, F2, F3)

| Karar | Bulgu | Uygulama | Test (`tests/test_faz6_s6_fix.py`) |
|---|---|---|---|
| F1 | B1 (KRİTİK): D1'i tavan kapanmayan açık üye `post_d1_row`'a giriyordu; `conditional_rps` L < j için ValueError veriyordu | Canlı kapının aynısı. Önce model düzeyi RETRO (`model_prospective_post_d1`, canlı fonksiyon; ingest I10). Sonra `_d1_label`: bekleniyor → `n_undetermined`, NA → `n_d1_label_na`, 0 → `n_not_applicable`. Yalnız etiketi 1 olan üye kayıt → sınıf → `post_d1_row` yolundan geçer. Kayıt yoksa `n_skipped` artar, S2 kaydı varsa `n_no_record` de artar. Blok canlının payda ve satır sayaçlarını taşır. Ek denetim `_oot_d1_label_agrees`: kayıttaki hücre NOT_APPLICABLE ⇔ gerçekleşen D1 etiketi 0; uyuşmazlık `ScoringError` verir. | T-B1 `test_b1_post_d1_block_gates_on_d1_label_like_live`, `test_b1_undetermined_when_d1_outcome_missing`; T-B1b `test_b1b_record_state_and_realized_d1_label_must_agree[SYNC-1]`, `[SYNA-0]`, `test_b1b_refused_record_carries_no_d1_ceiling_claim`, `test_b1b_label_check_only_for_the_record_of_the_same_d1_session`; F4 `test_model_frozen_after_outcome_is_retro_before_the_label_gate` |
| F2 | B2 (ÖNEMLİ, hijyen): üst düzey `retro_info` kasa üyelerini de taşıyordu (gerçek repoda 64 × 19 = 1216 çift) | `build_oot_scores`: `retro_all`'a yalnız açık küme (OPEN ∪ EXPOSED_*) çiftleri eklenir. Kasa bilgisi yalnız `n_sealed` sayacında kalır. | T-B2 `test_b2_sealed_code_absent_from_scores_oot_and_doc`, `test_b2_retro_info_carries_open_set_pairs_only`; gerçek repo bekçisi (§5.3) |
| F3 | B3 (KÜÇÜK): `path_params = None`, bu yüzden `ceiling_path_v0` karşılaştırıcısı her satırda `not_produced` idi | `_oot_post_d1_params`: POST_D1 model dosyasının sha256'sı INDEX_POST_D1.json ile denetlenir (canlı `load_post_d1_context` gibi). `path_secondary.model_id` models/INDEX.json'daysa o JSON `post_d1_row`'a `path_params` olarak verilir. | T-B3 `test_b3_path_comparator_produced_with_ceiling_path_json`, `test_b3_path_comparator_row_below_n_rule_has_no_cell`; F4 `test_post_d1_model_file_sha_is_checked_like_live` |

**F1 ek denetiminin kapsamı (bir okuma kararı; proje sahibinin onayına açık).** Görev metni "kayıttaki hücre durumu NOT_APPLICABLE
(D1_NOT_CEILING) ⇔ gerçekleşen D1 etiketi 0" diyor. Üç durumda denetim yapılmıyor:

1. **Ret hücresi.** SPEC_POST_D1_V0 §12 sırasında ana modelin reddi (örn. F3_MISSING) ve D1_LIMIT_NA reddi tavan denetiminden önce
   gelir. Yani ret hücresi D1 tavanı hakkında hüküm taşımaz. Lafzi ⇔ burada da uygulansaydı, ana modeli reddedilmiş ve D1'i tavan
   olmayan bir üye komutu B1 gibi yeniden çökertirdi. Canlı blok bu üyeyi `n_not_applicable`'a koyar; eski kohort da artık öyle yapar
   (test `test_b1b_refused_record_carries_no_d1_ceiling_claim`).
2. **Etiketi beklenen üye.** Karşılaştırılacak gerçekleşen etiket yok; üye `n_undetermined`'a düşer.
3. **D_1'i gerçekleşen D_1 olmayan kayıt.** Kayıt başka bir seans hakkındadır. Etiketi 1 ise I13'ün `d1_ok` terimiyle zaten
   OOT_RETRO olur; e79a4b7'deki davranış budur. Denetim yapılsaydı bu durumda sınıf formülü yerine çökme gelirdi (test
   `test_b1b_label_check_only_for_the_record_of_the_same_d1_session`).

Denetim PREDICTED ve NOT_APPLICABLE hücrelerde tam ⇔ olarak uygulanır. Her iki yöndeki uyuşmazlık `ScoringError` verir (T-B1b).

## 4. F4: canlı `post_d1_block` + `post_d1_row` + hücre üretimi ile `oot_post_d1_block` satır satır

Sütun "eski kohort", düzeltmeden sonraki kodu anlatır. Satır içeriği iki tarafta da aynı fonksiyondan (`post_d1_row`) gelir. Farklar
yalnız ona verilen girdilerde ve bloğun kapısında.

| # | Konu | Canlı | Eski kohort | Gerekçe | Karar |
|---|---|---|---|---|---|
| 1 | Payda kümesi | `registry/ipos.csv`'de FROZEN her arz | Kohortun açık küme üyeleri (OPEN ∪ EXPOSED_*); kasadakiler bloğa hiç girmez | Şartname §6 (birincil tablo OPEN küme); I3; D6-3 (kasanın sonucu yok) | Meşru; değişiklik yok |
| 2 | POST_D1 model dosyası | `load_post_d1_context`: sha256 INDEX_POST_D1.json ile denetlenir, uyuşmazlık `ScoringError` | e79a4b7'de dosya hiç okunmuyordu. Şimdi `_oot_post_d1_params` aynı denetimi yapar | F3'ün "canlı bloktaki gibi yükler" kararının parçası | Düzeltildi (F3); test var |
| 3 | `path_params` | `params["path_secondary"]["model_id"]` INDEX.json'daysa o JSON | e79a4b7'de `None` idi; şimdi aynı | SPEC_POST_D1_V0 §4, I11 (B3) | Düzeltildi (F3); T-B3 |
| 4 | Sonuç giriş commit'i | `outcome_ingest_commit_post_d1`: tarihi > D_1 olan ilk bülteni ya da `data/outcomes/<a>.csv`'de h ≥ 2 dolu satırı ilk yazan commit | `oot_ingest_commit(tarih > D_1, include_d1_rows=False)`: csv'yi ya da ham json'ı ekleyen commit, ya da tarihi (D_1, D_10] olan zip | I10. Eski kohort dosyası bir kerede bütün girer; ham kopya da sonuç taşır; `d1_rows` modelin girdisidir | Meşru (bilinen); değişiklik yok |
| 5 | Model düzeyi RETRO | Etiket kapısından ÖNCE: `model_prospective_post_d1` yanlışsa RETRO; `retro_info`'ya kayıt kimliği olmadan yazılır, hiçbir n'e girmez | e79a4b7'de yoktu: model şartı yalnız `class_oot` içinde ve yalnız kaydı olan üyede aranıyordu. Şimdi aynı fonksiyon aynı yerde (ingest I10) | SPEC_POST_D1_V0 §7.5 ("hepsi RETRO → retro_info, hiçbir n'e girmez"); I13 (a); şartname §2 ("OOT_RETRO hiçbir n'e girmez"). Kapı önce gelseydi, model sonuçtan sonra dondurulmuş bir çift `n_not_applicable` gibi bir n'e girebilirdi | Düzeltildi; test `test_model_frozen_after_outcome_is_retro_before_the_label_gate` |
| 6 | D1 etiketi kapısı | `_d1_label`: bekleniyor → `n_undetermined` (D1_PENDING), NA → `n_d1_label_na`, 0 → `n_not_applicable`; yalnız 1 satır olur | e79a4b7'de kapı yoktu: kaydı ve D_1'i olan her üye satırdı (B1 çökmesi); sonucu ya da kaydı olmayan üye sayaçsız atlanıyordu. Şimdi aynı | §7.5, görev F1 (B1) | Düzeltildi; T-B1 |
| 7 | Kayıt ↔ etiket tutarlılığı | Denetim yok. Etiketi 1 ama hücresi NOT_APPLICABLE olan satır `ROW_NOT_APPLICABLE` olur ve `n_not_applicable`'a eklenir | Hücre NOT_APPLICABLE ⇔ etiket 0 denetlenir, uyuşmazlık `ScoringError` (kapsam §3). `n_not_applicable` formülü canlıyla aynı; `ROW_NOT_APPLICABLE` sayısı burada hep 0 | Görev F1 ek denetimi | Eklendi; T-B1b |
| 8 | Takvim ve T_open | T_open sınıfın girdisi; takvim yoksa `n_calendar_not_available` | T_open yalnız satırdaki bilgi alanıdır, sınıfa girmez. Takvim (`load_calendar_oot`) kohort penceresini kapsar; takvim eksikse `CalendarNotAvailable` açık hata olarak yükselir; sayaç yok | I23 (zaman sınırı yok); I34 | Meşru; değişiklik yok |
| 9 | Kayıt seçimi | `select_primary_post_d1`: T_open'dan önce push kanıtlı en erken kayıt, yoksa pit'li en erken; iptaller düşülür; aday yalnız modeli içeren kayıtlar | En erken etkin kayıt (iptaller düşülür). S3 kapısıyla tek tanım olsun diye `outcomes_oot.oot_post_d1_primary` çağrılır (e79a4b7 aynı kuralı satır içinde yazıyordu). Her kaydın INDEX_POST_D1'deki bütün modelleri içermesini G2 zorlar | I12, I23 | Meşru (bilinen); tek tanıma bağlandı |
| 10 | Kayıt yok | `n_skipped`; listeleme öncesi birincil kayıt varsa `n_no_record`, yoksa SKIP_NO_PRE_LISTING_RECORD | e79a4b7'de sessiz atlamaydı. Şimdi `n_skipped`, S2 (I12) kaydı varsa `n_no_record` de | §7.5, görev F1 | Düzeltildi; T-B1 (SYNE) |
| 11 | pit (`inputs_pit_problems_post_d1` (i)–(iv)) | LATE_RECORD'un koşulu; satırda `inputs_pit_problems` | `[]` verilir. Gerekçe: LATE sınıfı yok (I13: iki sınıf). (ii) ve (iii)'ün pin kısmı `class_oot`'un ek koşulu `d1_ok`'ta. (iii)'ün dosya kısmı uygulanamaz (zip repoda yok, D6-1). (iv) S3 kapısında (`d1_rows_problems` → `post_d1_record_problems`). (i) S1–S2 bekçilerinde | I13, I23 | Meşru; değişiklik yok |
| 12 | Sınıf | `class_post_d1`: LIVE / LATE_RECORD / RETRO | `class_oot`: OOT_BLIND / OOT_RETRO, ek koşul `d1_ok` | I13 | Meşru (bilinen) |
| 13 | RETRO satırı | `n_retro` + `retro_info` (pit dahil); dosyanın üst düzey `retro_info`'suna toplanır | `n_retro` + blok içi `retro_info` (sınıf kanıtıyla); üst düzey `retro_info` 19 modelin çiftlerini taşır. `n_oot_retro` = `n_retro` (belge onu okur) | Gösterim | Meşru |
| 14 | Faz 2C paritesi | Kaydın karşılaştırıcı kopyası Faz 2C j = 1 satırıyla \|Δ\| ≤ 1e-12 | `faz2c_row = None` → `NOT_AVAILABLE`; eski kohortta Faz 2C j = 1 bloğu yok | Görevde bilinen fark | Meşru (bilinen) |
| 15 | Satır içeriği | `post_d1_row` | Aynı fonksiyon (hedef, L, S_cond, kayıplar, karşılaştırıcılar, path) | — | Aynı |
| 16 | Maruziyet etiketi | Yok (insan-kör) | `exposure_class = MACHINE_SEQUENCED` satırda ve blokta | KARARLAR D5, I23 | Meşru (bilinen) |
| 17 | Ölçek | `live_post_d1` | `OOT_PRE_H99_POST_D1_MACHINE_SEQUENCED`; `_one_scale` ve `merge_scales` birleştirmeyi reddeder | I24 | Meşru (bilinen) |
| 18 | Hücre gözlemleri | `post_d1_obs`: SCORED ve sınıf ∈ {LIVE, LATE_RECORD} | SCORED ve sınıf OOT_BLIND (satırlar zaten yalnız OOT_BLIND) | I13 | Meşru |
| 19 | Hücre n kuralı | Skorlanan < 10 ise hiç hücre yok; her hücre n ≥ 10 | Her hücre n ≥ 10. Gözlemler skorlanan satırların alt kümesi olduğundan iki kural eşdeğer | SPEC_SCORING §8 | Aynı |
| 20 | Hücre listesi, etiket, metrik | `post_d1_cell_specs`, `_post_d1_label`, `paired_metric`, `_cond_losses` | Aynı fonksiyonlar | — | Aynı |
| 21 | §4 kalibrasyon satırları (`descriptive`) | `post_d1_descriptive`: ort(h_2) ve ort(S_cond[k]) ile gözlenen oranlar (betimsel, aralık ve hüküm yok) | Üretilmiyor. Canlı fonksiyon satırları PROSPECTIVE_CLASSES ile süzdüğü için eski kohort satırlarında boş döner. Eklemek ya ikinci bir tanım ya da canlı fonksiyonda değişiklik ister | SPEC_OOT §6 ve I11 "hücreler"den söz eder; kalibrasyon hücre değil, betimsel satırdır. 19 modelin eski kohort bloğunda da `live_descriptive` karşılığı yok. Şartnameye açıkça aykırı değil, ama yorum gerektiriyor | **Düzeltilmedi. DUR ile raporlandı: proje sahibi kararı** |
| 22 | Payda satır listesi (`denominator`) | Arz başına aşama durumu listesi | Yok; aynı bilgi sayı olarak sayaçlarda (görev F1 sayaçları istiyor) | Gösterim | Meşru; değişiklik yok |
| 23 | Blok sayaçları | `n_live`, `n_late`, `n_calendar_not_available` de var | Bu üçü yok (sınıflar ve takvim sayacı uygulanmaz); öbür sayaçlar aynı adla | I13, I23 | Meşru |
| 24 | Tanım metinleri | Blokta `definition`, `class_definition`, `comparators` | `title` post_d1 düzeyinde; `primary_cell` (= `POST_D1_PRIMARY`); sınıf tanımı dosyanın `definitions.class` alanında, post_d1 ek koşulu I13'te | Gösterim | Meşru |

Açıklanmamış fark yok. Yorum gerektiren tek fark 21. satır; düzeltilmedi, proje sahibine bırakıldı.

## 5. Testler: önce kırmızı, sonra yeşil

### 5.1 `e79a4b7` kodunda (kırmızı)

`borsai/scoring.py` geçici olarak `git show e79a4b7:borsai/scoring.py` ile değiştirildi (`git diff --quiet` = e79a4b7). Yeni test dosyası
koşuldu, sonra düzeltilmiş dosya yedekten geri kondu (`cmp` bayt-eşit). Komut:
`.venv/bin/pytest -q -p no:cacheprovider tests/test_faz6_s6_fix.py -rf --tb=line`.

| Test | e79a4b7'de | Neden |
|---|---|---|
| `test_b1_post_d1_block_gates_on_d1_label_like_live` | kırmızı | `ValueError: koşullu RPS yalnız L ≥ j ve j ≤ 9 için tanımlı` (B1) |
| `test_b1_undetermined_when_d1_outcome_missing` | kırmızı | aynı ValueError |
| `test_b1b_record_state_and_realized_d1_label_must_agree[SYNC-1]` | kırmızı | `Failed: DID NOT RAISE ScoringError` (denetim yok) |
| `test_b1b_record_state_and_realized_d1_label_must_agree[SYNA-0]` | kırmızı | aynı ValueError |
| `test_b1b_refused_record_carries_no_d1_ceiling_claim` | kırmızı | aynı ValueError |
| `test_b1b_label_check_only_for_the_record_of_the_same_d1_session` | kırmızı | `assert (['SYNA', 'SYND'] == ['SYNA']`: D1 etiketi NA olan üye satır olmuş |
| `test_model_frozen_after_outcome_is_retro_before_the_label_gate` | kırmızı | `KeyError: 'n_retro'` |
| `test_b2_sealed_code_absent_from_scores_oot_and_doc` | kırmızı | `assert 'SYNZ' not in '{…}'`: kasa kodu `retro_info`'da (B2) |
| `test_b2_retro_info_carries_open_set_pairs_only` | kırmızı | `retro_info` çiftleri açık küme × 19 değil (kasa üyesinin 19 çifti fazla) |
| `test_b3_path_comparator_produced_with_ceiling_path_json` | kırmızı | `assert 'not_produced' not in {'record_id': '…', 'not_produced': True}` (B3) |
| `test_b3_path_comparator_row_below_n_rule_has_no_cell` | kırmızı | aynı ValueError |
| `test_post_d1_model_file_sha_is_checked_like_live` | kırmızı | aynı ValueError |

Özet satırı: `12 failed in 14.95s`. Ham çıktının `E` satırları (sırayla, test sırasıyla aynı):

```
E   ValueError: koşullu RPS yalnız L ≥ j ve j ≤ 9 için tanımlı
E   ValueError: koşullu RPS yalnız L ≥ j ve j ≤ 9 için tanımlı
E   Failed: DID NOT RAISE ScoringError
E   ValueError: koşullu RPS yalnız L ≥ j ve j ≤ 9 için tanımlı
E   ValueError: koşullu RPS yalnız L ≥ j ve j ≤ 9 için tanımlı
E   AssertionError: assert (['SYNA', 'SYND'] == ['SYNA']
E   KeyError: 'n_retro'
E   assert 'SYNZ' not in '{\n  "code"..._oot/1"\n}\n'
E   AssertionError: assert [('base_alway... 'SYNF'), ...] == [('base_alway... 'SYNF'), ...]
E   AssertionError: assert 'not_produced' not in {'record_id': '20260925T090000Z_65e17045fd18.json', 'not_produced': True}
E   ValueError: koşullu RPS yalnız L ≥ j ve j ≤ 9 için tanımlı
E   ValueError: koşullu RPS yalnız L ≥ j ve j ≤ 9 için tanımlı
12 failed in 14.95s
```

### 5.2 Düzeltmeyle (yeşil)

Aynı komut: `12 passed in 17.14s`. Her testin ne sınadığı:

- **T-B1.** Küçük sentetik depoda dört açık üye var: SYNA (D1 tavan), SYNC (D1 tavan değil, kaydı NOT_APPLICABLE D1_NOT_CEILING),
  SYND (D1 üst limiti yok: etiket NA, kaydı REFUSED D1_LIMIT_NA), SYNE (D1 tavan, POST_D1 kaydı yazılmadı). Bir de kasa üyesi SYNZ.
  `build_oot_scores` çökmez. Tek post_d1 satırı SYNA (OOT_BLIND, SCORED). Sayaçlar: `n_not_applicable` 1, `n_d1_label_na` 1,
  `n_skipped` 1, `n_no_record` 1, `n_retro` 0, `n_undetermined` 0. Listeleme öncesi 19 model etkilenmez (v1_5_h99'da dört açık üye
  satırı var). Sonuç dosyası yoksa üye `n_undetermined`'a düşer.
- **T-B1b.** Kayıt NOT_APPLICABLE ama gerçekleşen etiket 1 olursa (SYNC) `ScoringError`; tersi, kayıt PREDICTED ama etiket 0 olursa
  (SYNA) yine `ScoringError`. Ret hücresi etiket 0 ile çökmez, `n_not_applicable`'a düşer. Kaydın D_1'i gerçekleşen D_1 değilse
  karşılaştırma yapılmaz, üye OOT_RETRO olur (`extra_ok = false`).
- **T-B2.** Büyük sentetik depoda 12 açık üye (hepsi D1 tavan) ve kasada SYNZ var. Yazılmış `scores_oot.json` metninde ve
  `render_oot_doc` çıktısında SYNZ hiç geçmez; `n_sealed` = 1. S3 ve S5 commit'leri kanıtsızken her açık çift OOT_RETRO olur;
  `retro_info` tam olarak 19 model × 12 açık üye çiftidir, kasa çifti yoktur.
- **T-B3.** Base_record'da `ceiling_path_v0` hücresi PREDICTED olan her satırda karşılaştırıcı `not_produced` değildir. Değeri, models/
  ceiling_path_v0.json ile `_path_part`'ın çıktısına eşittir. D3/D5/D10 MAE ve p_up Brier altı ikincil hücresi n = 12 ile üretilir
  (etiket "ikincil", ölçek `OOT_PRE_H99_POST_D1_MACHINE_SEQUENCED`). Tek satırlı depoda karşılaştırıcı satırda vardır ama n = 1 < 10
  olduğu için hücre yoktur.
- **F4 testleri.** Push kanıtı yoksa her açık üye model düzeyi RETRO olur (kayıt kimliği yok, `model_prospective = false`), payda
  sayaçlarına girmez. POST_D1 model dosyasının sha256'sı INDEX_POST_D1.json'dan saparsa `ScoringError`.

### 5.3 Gerçek repo bekçisi

`tests/test_outcome_guard.py::test_sealed_codes_absent_from_every_extracted_file`'ın dosya listesine `scores/scores_oot.json` ve
`docs/SCORES_OOT.md` eklendi (`x.is_file()` süzgeci aynen). Bugün iki dosya da yok; test yeşil. S6 dosyaları yazınca bekçi onları da
tarar.

## 6. Test sayıları

| Koşu | Sonuç |
|---|---|
| Taban (HEAD e79a4b7): tam pytest | 625 passed (6 dk 38 s) |
| Taban: `bash app/scripts/test.sh` | cargo 94 / 0; npm 222; parity 4; golden_unchanged YEŞİL |
| `tests/test_faz6_s6_fix.py` tek başına, e79a4b7 kodu | 12 failed |
| `tests/test_faz6_s6_fix.py` tek başına, düzeltme | 12 passed |
| `test_outcome_guard.py`, `test_faz6_oot.py`, `test_faz6_s6.py`, `test_faz6_s6_fix.py` birlikte | 111 passed (düzeltme; 12. test eklenmeden önce) |
| Düzeltme: tam pytest (14:40:27 → 14:47:54 UTC) | 637 passed (625 + 12 yeni; 7 dk 27 s); çıkış 0 |
| Düzeltme: `bash app/scripts/test.sh` (14:47:54 → 14:48:21 UTC) | cargo 94 / 0; npm 222; parity 4; golden_unchanged YEŞİL; çıkış 0 |

Canlı skor üreticileri değişmedi. Tam pytest'in canlı testleri (`tests/test_scoring.py`, `tests/test_faz5_live.py`,
`tests/test_scoring_conditional.py` ve bayt-eşitlik testleri) aynen geçti.

## 7. S6 oturumunun devamı için not

- S6'nın adım 2–4'ü bu commit'in üstünde yeniden koşulur. T1–T3 kodu (`main_oot`, `render_oot_doc`, `spk_corporate_action_members`)
  değişmedi.
- **T4'te post_d1 için yeni beklentiler.** Satırlar yalnız D1 etiketi 1 ve kaydı olan açık üyelerdir. Hücresi NOT_APPLICABLE olan her
  kayıt (S3b'de 9 idi) `n_not_applicable`'da sayılmalıdır. Etiketi 0 değilse komut `ScoringError` ile durur; bu bir DUR'dur (kayıt ile
  resmi sonuç uyuşmuyor). Ret hücreli üyeler etiketlerine göre ya satırdır (REFUSED) ya da payda sayacındadır. Açık küme toplamı
  şöyle tutmalı: satır + `n_not_applicable` + `n_d1_label_na` + `n_undetermined` + `n_skipped` + `n_retro` = 71.
- **T4'teki "üst düzey retro_info boş" denetimi** artık ölçülebilir: kasa çiftleri yazılmıyor. Açık kümede her çift OOT_BLIND ise 0
  beklenir.
- **B3'ten sonra** post_d1'de altı path_conditional ikincil hücresi (D3/D5/D10 MAE ve p_up Brier, `ceiling_path_v0`'a karşı) n ≥ 10 ise
  üretilir. Birincil hücre (RPS_1 vs `ceiling_hazard_v0`) tanım olarak etkilenmedi.
- **Belge (render) güncellenmeli; bu görevin yazma izni dışında.** `render_oot_doc` §6'daki "Satır: D_1 satırı ve D1 sonrası kaydı
  olan her açık üye (ret ve uygulanamaz dahil)" cümlesi artık doğru değil: D1'i tavan olmayan üye satır değil, `n_not_applicable`'dır.
  Yeni sayaçlar (`n_not_applicable`, `n_d1_label_na`, `n_undetermined`, `n_skipped` / `n_no_record`, `n_retro`) belgede görünmüyor.
  Bu yalnız gösterimdir; skor değişmez. `render_oot_doc` I40'ın kodudur ve S6 devamında düzeltilmesi gerekir. Belge JSON'dan
  üretildiği için değişiklik yalnız render'ı ve onun testini ilgilendirir.
- **Proje sahibi kararı bekleyen iki madde:** (a) §4 kalibrasyon satırlarının eski kohortta üretilip üretilmeyeceği (F4 satır 21);
  (b) F1 ek denetiminin ret hücresini kapsamaması (§3). Lafzi ⇔ istenirse değişiklik küçük, ama gerçek veride komutu çökertme riski
  taşır.
- S6 görevinin kendi açık adımları (T5 §8 karşılaştırması, T6 f6 duyarlılığı) bu görevin konusu değildi.

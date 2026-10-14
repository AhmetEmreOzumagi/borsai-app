# BORSAI_FAZ8_LIVE_BREAK_20261002 — kırılma akşamı canlı aşaması `POST_BREAK` (makine sıralı): rapor

Görev `docs/prompts/FAZ8_LIVE_BREAK.md` (Opus 5.5). Ağ yok; push, tag, amend yok. Bağlayıcı metin `docs/specs_faz8/SPEC_BREAK_V0.md`
§5, §8, §9, §11, §13-11..13; görev kararları K-LB-1..10; kayıtlı sapmalar `docs/SPEC_DEVIATIONS.md` N26–N33. **Model ve skor tanımı
değişmedi**: `predict_break.py`, `post_break.py`, `specs.py`, donmuş JSON'lar ve `models/` dokunulmadı.

## 0. Kısa sonuç

- `python -m borsai.scoring --break` yazıldı: (i) eksik makine kayıtları `registry/post_break/<T>/machine_<UTC>_<kısa-sha>.json`,
  (ii) `scores/scores_break.json` (şema `borsai.scores_break/1`, ölçek `live_break`), (iii) yazılmış JSON'dan `docs/SCORES_BREAK.md`.
  Bayraksız `main()` aynı.
- İlk gerçek koşu 7 kayıt yazdı (arz başına bir). b, D_b ve b_floor beklenen tabloyla birebir; p_F1 ve p_F2 farkı 0.0. İkinci koşu
  0 kayıt yazdı; skor dosyasında yalnız `generated_at_utc` değişti.
- 7/7 arz RETRO'dur (model `4d3c9a2`, bütün sonuçlardan sonra donduruldu). `n_scored` = `n_machine` = `n_live` = 0. Paydada 7 satır
  var, hepsi RETRO; özdeşlik tutuyor. NETGL'de b = 4, `b_floor` = 1, `FON_KRIZI_2026`. Ürün karşılaştırıcısı 7/7 `NOT_AVAILABLE`.
- Taban (fd88be3) kırmızıydı (`test_b7`). Ayrıca B'de bir koruma testinin kırılacağı önceden görüldü. İkisi de proje sahibine
  soruldu; kararlar §2'de.
- Son kabul (deselect'siz, sıralı): **952 passed** (sıralı, deselect'siz, 0:18:18); `test.sh` yeşil; `gen_golden --check` 35/0.

## 1. Commit'ler (sıra A → B → R; push yok)

| Commit | Hash | Üst | İçerik |
|---|---|---|---|
| A | `71cf0791d53d3b48e5914f760fa075a7626c6a15` | `fd88be3` | kod (`scoring.py`, `freeze.py`, `registry.py`), `tests/test_faz8_live.py` (sentetik), `test_outcome_guard.py` ekleri, K-PIN-L, SPEC_DEVIATIONS N26–N33, `docs/faz8/live_test_runs.txt`, görev dosyası |
| B | `7ee0027031964397e81583c947d8a6117edd9604` | `71cf079` | 7 makine kaydı, `scores/scores_break.json`, `docs/SCORES_BREAK.md`, gerçek dosya testleri, `docs/faz8/POST_BREAK_AKISI.md`, test günlüğü |
| R | (bu raporu içeren commit) | `7ee0027` | `docs/faz8/LIVE_RAPOR.md`, `docs/faz8/live_test_runs.txt` |

```
commit 71cf0791d53d3b48e5914f760fa075a7626c6a15
parent fd88be398a0cee1177494a9230f9d75a49b9969f
BORSAI_FAZ8_LIVE_A: POST_BREAK live stage code before outputs (machine record writer and guard, outcome_ingest_commit_after, class_break evidence, scores_break.json builder and SCORES_BREAK.md via scoring --break, sequence guard for INDEX_POST_BREAK), synthetic tests (spec 13-11..13), pre-approved pin updates (K-PIN-L), SPEC_DEVIATIONS N26+

 borsai/freeze.py                | 265 ++++++++++++++++++++++++
 borsai/registry.py              | 100 ++++++++++
 borsai/scoring.py               | 877 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 docs/SPEC_DEVIATIONS.md         |  15 ++
 docs/faz8/live_test_runs.txt    |  49 +++++
 docs/prompts/FAZ8_LIVE_BREAK.md | 240 ++++++++++++++++++++++
 tests/test_faz8_golden.py       |  15 +-
 tests/test_faz8_live.py         | 635 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_faz8_model.py        |  34 +++-
 tests/test_outcome_guard.py     |  93 ++++++++-
 10 files changed, 2310 insertions(+), 13 deletions(-)
```

```
commit 7ee0027031964397e81583c947d8a6117edd9604
parent 71cf0791d53d3b48e5914f760fa075a7626c6a15
BORSAI_FAZ8_LIVE_B: first scoring --break run (7 machine records, all RETRO; scores/scores_break.json live_break n_scored 0; docs/SCORES_BREAK.md), real-file tests, POST_BREAK flow note

 docs/SCORES_BREAK.md                                                 |  74 +++++
 docs/faz8/POST_BREAK_AKISI.md                                        |  55 ++++
 docs/faz8/live_test_runs.txt                                         |  27 ++
 registry/post_break/BKRGY/machine_20261002T161730Z_0ffe802ead07.json | 165 +++++++++++
 registry/post_break/CITAS/machine_20261002T161730Z_af6ce6567cc6.json | 240 +++++++++++++++
 registry/post_break/INTET/machine_20261002T161730Z_82475cb4213b.json | 225 ++++++++++++++
 registry/post_break/KPEKS/machine_20261002T161730Z_1510442bfbdf.json | 240 +++++++++++++++
 registry/post_break/NETGL/machine_20261002T161730Z_c5a61ad0cf26.json | 221 ++++++++++++++
 registry/post_break/TKNKA/machine_20261002T161730Z_130557515e13.json | 270 +++++++++++++++++
 registry/post_break/VEYAS/machine_20261002T161730Z_b4d19ca74cdc.json | 165 +++++++++++
 scores/scores_break.json                                             | 688 +++++++++++++++++++++++++++++++++++++++++++
 tests/test_faz8_live.py                                              |  96 ++++++
 12 files changed, 2466 insertions(+)
```

## 2. Taban ve proje sahibi kararları (adım 0)

Taban `fd88be3` = origin/main; ağaçta yalnız görev dosyası vardı.

- Paralel pytest: 920 passed, **1 failed**.
  - Kırmızı test: `tests/test_faz8_golden.py::test_b7_old_outputs_unchanged`.
  - Neden: proje sahibinin push kanıtı commit'i `fd88be3` `registry/push_proofs/4d3c9a26….json` ekledi. Test ise
    `git diff 5d84e88 -- … registry …` çıktısında yalnız üç models/ dosyası bekliyordu.
- `test.sh` yeşil (cargo 151, vitest 305, parity 8); `gen_golden --check` 35/0.
- Kasa testi temiz ağaçta yeşildi.

DUR kuralı gereği iş durduruldu ve iki soru AskUserQuestion ile proje sahibine soruldu.

- **DUR-1 (`test_b7`).**
  - Karar: testin bütün yol listesi sabit `5d84e88..57dcd0c` aralığına bağlanır. O aralıkta yalnız üç dondurma dosyası vardır.
  - Çalışma ağacına karşı yeni bir "sonrası" iddiası yazılmaz.
  - Bu görevin değişiklikleri `test_faz8_live.py`'de yalnız konusu `BORSAI_FAZ8_LIVE_` ile başlayan commit'ler üzerinden sınanır.
    registry ve scores'ta yalnız eklenen `registry/post_break/**` ve `scores/scores_break.json` kabul edilir.
  - log.jsonl "yalnız ekleme" ayağı aynen kalır.
- **DUR-2 (öngörülen).**
  - Sorun: `test_outcome_guard.py::test_registry_carries_no_outcome_fields` registry/ altında `close` ve `upper_limit` anahtarlarını
    yasaklıyor. §9.2 şeması (K-LB-2 "aynen") ise makine kaydında `break_day.fields_raw` içinde bu anahtarları istiyor.
  - Karar: hariç tutma demetine `"registry/post_break/"` eklendi (H35 kalıbı). Dizini yeni bekçi denetler; bunun için ek gerçek dosya
    testi ve mutasyon testi yazıldı.

## 3. Prova (adım 0b; ayrıntı `live_test_runs.txt`)

Geçici klonda şu sıra izlendi: A commit'i → `--break` → çıktılar ve gerçek dosya testleri commit'i → tam paralel pytest.

| Ölçüm | Sonuç |
|---|---|
| pytest (952 test) | 951 passed, 1 failed |
| `test.sh` | exit 0 |
| `gen_golden` | 35/0 |

Tek kırmızı test `test_faz8_break::test_14b` idi. `git status -- app` klondaki `app/node_modules` sembolik bağını izlenmeyen dosya
olarak gösterdi. Bu bir prova ortamı artefaktıdır; bağ klonda dışlanınca test yeşil oldu.

Kırmızıların sınıflaması:
- (i) K-PIN-L türü: adım 0'da bulunan üçü dışında yok.
- (ii) Kod hatası: yok.
- (iii) Başka: yok.

Yeni testlerin 10 mutasyonu 10/10 kırmızı oldu. M6 ("F1 = 0 iken F2 okunur") ilk koşuda yakalanmadı. Sentetik senaryo güçlendirildi
(D3'ü taban olan ZBB) ve mutasyon kırmızıya döndü. Klonlar silindi.

## 4. K-PIN-L (önceden onaylı) ve K-GUARD — her test için bir satır

| Test | İddia | Önce | Sonra |
|---|---|---|---|
| `test_faz8_model.py::test_5c_old_goldens_and_app_pins_unchanged` | `scoring.py`, `registry.py` değişmedi; `freeze.py` yalnız K'dan | `scoring`/`registry` 7d78d43'ten beri aynı; `freeze.py` farkı yalnız `BORSAI_FAZ8_FREEZE_K:` | üçü 7d78d43..6d3f674 aynı; sonrası yalnız konusu `BORSAI_FAZ8_FREEZE_K:` ya da `BORSAI_FAZ8_LIVE_A:` olan commit'ler (her biri en çok bir kez; ağaç en sona eşit; A'dan önceki koşu istisnası); `specs.py` kuralı aynen |
| `test_faz8_golden.py::test_b7_old_outputs_unchanged` | `git diff 5d84e88 -- tests/reference models registry data scores app docs/specs*` yalnız üç dondurma dosyası | çalışma ağacına karşı | sabit `5d84e88..57dcd0c` aralığı (DUR-1 kararı); diff-filter=A ayağı aynı aralıkta; log.jsonl ayağı aynen |
| `test_outcome_guard.py::test_registry_carries_no_outcome_fields` | registry/'de sonuç anahtarı yok | `post_d1`, `oot/d1_rows`, `oot/post_d1` hariç | + `registry/post_break/` (DUR-2 kararı); dizini `test_post_break_records_carry_only_d1_to_db` denetler |
| `test_outcome_guard.py` (K-GUARD) | sıra bekçisi | — | yalnız yeni testler: `test_10g` (listelenen ama commit'lenmemiş POST_BREAK modeli → ihlal; commit'ten sonra temiz), `test_10h` (model → sonuç temiz; paralel dal → ihlal), `test_post_break_records_carry_only_d1_to_db`, `test_post_break_guard_red_cases_and_mutation` |

Kapsam dışı bekçilerin hiçbiri kırmızı olmadı: var olan `test_outcome_guard` iddiaları, `test_faz7_vault`, `test_scoring` içerik
pinleri ve N19 istisnası. Bunlara dokunulmadı.

## 5. Kod (A)

- **`registry.py`**
  - `POST_BREAK_DIR`, `POST_BREAK_RECORD_SCHEMA` eklendi.
  - `post_break_inputs_pit_problems`: `inputs_pit_problems` + `shares_offered` kaynağı gerçekleşen D_1'den önce.
  - `post_break_record_problems` (K-LB-4): `post_d1_record_problems` değişmedi; ortak yardımcılar kullanılıyor.
- **`freeze.py`**
  - `break_streak` eklendi.
  - `build_post_break_machine_record`: §9.2 alanları. D_1..D_b bültenleri MANIFEST'le, sonuç satırları pinli bültenle denetlenir.
    Girdi `registry/inputs`'tan, takvim `t_open`'dan gelir. INDEX_POST_BREAK'in her modeli `predict_break` ile koşar.
  - `post_break_product`: §5.1 kuralı; 7/7 `NOT_AVAILABLE`.
  - `write_post_break_machine_record`: `'xb'` ile yazar, mükerrer kaydı reddeder.
  - Diğer yeni yardımcılar: `machine_record_filename`, `post_break_record_key`, `list_post_break_records`.
  - CLI değişmedi.
- **`scoring.py`**
  - `outcome_ingest_commit_after` (K-LB-5): `outcome_ingest_commit_post_d1` değişmedi; 7 arzda bit-eşit.
  - Sınıf: `model_prospective_break`, `record_live_break` (v0'da hep False), `inputs_pit_problems_break`, `class_break_evidence`
    (saf formül `predict_break.class_break`).
  - Skor: `BreakContext`, `break_block` (payda K-LB-8, satır, hücreler §5.2, betimsel), `break_record_parity` (K-LB-3),
    `break_promotion` (§8), `build_break_scores`, `ensure_post_break_records`, `main_break`, `render_break_doc`.
  - Sıra bekçisi `sequence_violations`'a INDEX_POST_BREAK dalı yalnız ekleme olarak girdi (K-LB-9).
  - `main()`'e `--break` bayrağı eklendi; `--oot` ile birlikte verilemez.
- **Yeni testler (A)**
  - `tests/test_faz8_live.py` (23 test): §13-11 (a)–(g) ve bekçi mutasyonu; kayıt şeması; `@ZERO`'nun kırılma alanlarını okumaması;
    yazıcı ve mükerrer kayıt.
  - Aynı dosyada uçtan uca sentetik depo (14 sentetik arz). Payda dallarının hepsi ve özdeşlik sınanır: RETRO (PIT), RECORD satırları
    SCORED / PENDING / TARGET_LABEL_NA / REFUSED; b = 9'da F2 yok.
  - Aynı dosyada K-LB-3 (ikinci koşu 0 kayıt; bozulan p → `ScoringError`), "kanıt yok / sonuç önce → RETRO", `main_break` ve belge
    render'ı, §13-13 (ScaleMixError, "geçiyor" yalnız n ≥ 30, öne çıkan etiket aşama 1/2, belge), görev commit'lerinin yol denetimi
    ve hijyen.
  - `tests/test_outcome_guard.py`'ye 4 ek test.

## 6. Yedi makine kaydı (B; `registry/post_break/<T>/`)

| Arz | Dosya | sha256 | b | D_b | b_floor | p_F1 | p_F2 | uyarı | beklenenle fark |
|---|---|---|---|---|---|---|---|---|---|
| CITAS | `machine_20261002T161730Z_af6ce6567cc6.json` | `af6ce6567cc6facfa26d5c5a8db0f3ac444bfd60026700f4a7d28e98be0e84ff` | 6 | 2026-08-25 | 0 | 0.13833264286466687 | 0.09464223345801025 | — | 0 / 0 |
| TKNKA | `machine_20261002T161730Z_130557515e13.json` | `130557515e13056ab555eb9d8970752ecddc9fd352db588de2506b91af9e81fa` | 8 | 2026-08-31 | 0 | 0.13817491254287276 | 0.09521214961923939 | — | 0 / 0 |
| VEYAS | `machine_20261002T161730Z_b4d19ca74cdc.json` | `b4d19ca74cdcf8a6afc32aab06f53bebdcd67ab26acc5fcdc0577b3d32133342` | 1 | 2026-08-20 | 0 | 0.1376436522563838 | 0.09715847417357594 | — | 0 / 0 |
| KPEKS | `machine_20261002T161730Z_1510442bfbdf.json` | `1510442bfbdf84c323d0f439d559a2580fc2016bba0bd6e1cfe34140c356b599` | 6 | 2026-08-28 | 1 | 0.5389117003850694 | 0.16401056260438845 | — | 0 / 0 |
| INTET | `machine_20261002T161730Z_82475cb4213b.json` | `82475cb4213b7b33677242745932d4a1c5259de73274e90ab091e23bf0e5e435` | 5 | 2026-09-07 | 0 | 0.14182539930275256 | 0.08290496022647753 | — | 0 / 0 |
| BKRGY | `machine_20261002T161730Z_0ffe802ead07.json` | `0ffe802ead07ea897a8724e79fdedc37a3c3bcaf0f8818d13704e80cdda890e0` | 1 | 2026-09-02 | 1 | 0.5432679533511754 | 0.15231130173471372 | — | 0 / 0 |
| NETGL | `machine_20261002T161730Z_c5a61ad0cf26.json` | `c5a61ad0cf26c489a886af3f5a3be915e9093d6a725a02d1b25c5828aa90996e` | 4 | 2026-09-22 | 1 | 0.4990578357497034 | 0.30432770420243327 | `B_TURNOVER_CLIPPED_TO_TRAINING_P05_P95` | 0 / 0 |

Ortak özellikler:
- D_1 ve L değerleri görev tablosuyla aynı; b, D_b ve b_floor birebir; maks |Δp| = 0.0.
- `@ZERO` F1 0.3048780487804878, F2 0.14102564102564102 (= 25/82, 11/78).
- `exposure_class = MACHINE_SEQUENCED`; `models_index` sha'sı `899cf90c805d…`; `inputs_pit_ok` true.
- Bekçi 7/7 temiz.
- `code.git_head` = A, `borsai_dirty` false.
- Ürün 7/7 `NOT_AVAILABLE`: kayıtlar yalnız 16 Faz 1 modelini taşıyor (N31).

## 7. `scores/scores_break.json` (B)

- **Sayaçlar.** `n_retro` 7. Şu sayaçların hepsi 0: `n_scored`, `n_machine`, `n_live`, `n_rows`, `n_refused`, `n_pending`,
  `n_target_label_na`, `n_target_unavailable`, `n_streak_pending`, `n_streak_target_unavailable`, `n_not_scorable_streak_na`,
  `n_not_applicable_no_break`, `n_not_applicable_b10`, `n_bulletin_not_pinned`, `n_inputs_not_available`,
  `n_calendar_not_available`.
- **Payda.** 7 satır (CITAS … NETGL), her biri `stage_status` = `class` = RETRO. Özdeşlik: 7 = 7 RETRO + 0 satır.
- **`retro_info`.** 7 satır; her biri kayıttan b, b_floor, p, karşılaştırıcılar, rejim ve uyarıları taşır; bellek paritesi
  |Δ| = 0.
  - Sınıf kanıtı: CITAS, TKNKA, VEYAS, KPEKS, INTET ve BKRGY için sonuç commit'i `f1f9d44` (BORSAI_FAZ2B_B, 2026-09-22). NETGL için
    `c1eb7ae` (NETGL D4–D10, D_b 2026-09-22'den sonraki bültenler).
  - Model commit'i `4d3c9a2` bunların atası değil → RETRO.
- **Hücreler.** Hücre ve betimsel satır yok (n < 10).
- **Kart.**
  - Model commit'i `4d3c9a26…`; push kanıtı 2026-10-02T14:45:08Z.
  - Öne çıkan durum aşama 1, etiket "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0".
  - Backtest bilgi satırı (`backtest_break`, toplanmaz): F1 − ürün −0.1904 [−0.2520, −0.1247] n 69; F1 − `@ZERO` −0.0281
    [−0.0453, −0.0074] n 69. Etiket "backtest'te geçiyor (tasarıma maruz)".
- **İkinci koşu.** 0 yeni kayıt. JSON farkı yalnız `generated_at_utc` satırında (16:17:30Z → 16:17:54Z); `code` aynı (HEAD = A, temiz).
  Belgede yalnız "Üretim …" satırı değişti. Commit'lenen çıktı ikinci koşunun çıktısıdır.

## 8. Test sayıları ve süreleri (ayrıntı `live_test_runs.txt`)

| Aşama | pytest | `test.sh` | `gen_golden` |
|---|---|---|---|
| Taban (fd88be3), paralel | 920 passed, 1 failed (`test_b7`), 530 s | yeşil, 57 s | 35/0 |
| Prova (klon), paralel | 951 passed, 1 failed (klon artefaktı), 631 s | yeşil, 132 s | 35/0 |
| A öncesi, paralel, kasa testi ayrıldı | 947 passed, 1 deselected, 1142 s | yeşil, 39 s | 35/0 |
| A sonrası: kasa testi tek başına (+ test_5c, görev commit testi) | 3 passed, 91 s | — | — |
| B öncesi, paralel, ayrılan yok | 946 passed, 6 failed (altısı da `git status` temizlik iddiası; yalnız commit'siz B çıktıları), 676 s | yeşil, 58 s | 35/0 |
| Son kabul (B sonrası), **sıralı, deselect'siz** | **952 passed**, 1099 s (0:18:18) | yeşil, 56 s (cargo 151 / 0, npm 305, parity 8, golden_unchanged) | 35/0 |

Test sayısı 952'dir: taban 921, A'nın 27 testi (`test_faz8_live.py` 23, `test_outcome_guard.py` 4) ve B'nin 4 gerçek dosya testi.

## 9. Sapmalar (SPEC_DEVIATIONS N26–N33)

| # | Konu |
|---|---|
| N26 | K-LB-1: ayrı dosya/belge (`scores_break.json`, `SCORES_BREAK.md`), `--break`, bayraksız `main()` aynı |
| N27 | K-LB-3: mükerrer kayıt yok (INDEX + D_1..D_b bülten + girdi sha'ları); birincil = en erken; parite bellekte (\|Δ\| > 1e-12 → ScoringError) |
| N28 | K-LB-4: ayrı bekçi `post_break_record_problems`; `post_d1_record_problems` değişmedi |
| N29 | K-LB-5: yeni `outcome_ingest_commit_after`; post_d1 fonksiyonu değişmedi, (f) bit-eşit |
| N30 | Sınıfın sonuç günü b belirsizken HEAD'e karşı; L = 10'da D_10/h ≥ 11; yeni payda durumu `STREAK_TARGET_UNAVAILABLE`; v0 record_live hep False; PIT tanımı; etiket ayrıntıları |
| N31 | K-LB-7: ürün `NOT_AVAILABLE` nedeni (7 kayıt 16 Faz 1 modeli); `@ZERO`, `by_type` kaynakları |
| N32 | §8 öne çıkan durum ve backtest bilgi satırı kartta; hücre dili; betimsel bloklar |
| N33 | Proje sahibi kararları (test_b7 sabit aralık, post_break hariç tutması) + K-PIN-L + K-GUARD |

## 10. Yeni arz geldiğinde kırılma akşamı için komut

`outcomes update` sonuç commit'inden sonra (akşam yükü yok, push kanıtı gerekmez):

```
.venv/bin/python -m borsai.scoring --break
```

Ardından `registry/post_break`, `scores/scores_break.json` ve `docs/SCORES_BREAK.md` commit'lenir. Ayrıntı
`docs/faz8/POST_BREAK_AKISI.md`'de.

## 11. Kabul kapısı

- **K1:** 7 kayıt; |Δp| = 0 ≤ 1e-12; b, D_b ve b_floor birebir; ikinci koşu 0 kayıt. **Sağlandı.**
- **K2:** 7/7 RETRO; `n_scored` 0; payda özdeşliği; NETGL b = 4 ve `b_floor` = 1. **Sağlandı.**
- **K3:** §13-11 (a)–(g), §13-12 ve §13-13 testleri var ve yeşil; bekçi mutasyonu kırmızı. `post_d1_record_problems` ve
  `outcome_ingest_commit_post_d1` değişmedi (görev başlangıcındaki metinle aynı, testli). **Sağlandı.**
- **K4:** Bayraksız `main()` aynı (testli). `scores.json`, `scores_post_d1.json`, `SCORES.md`, `models/` ve `app/` değişmedi
  (`git diff fd88be3 -- …` boş; görev commit testi). **Sağlandı.**
- **K5:** Son kabul yeşil: 952 passed (sıralı, deselect'siz); `test.sh` ve `gen_golden` yeşil. Pinler yalnız K-PIN-L, K-GUARD ve iki proje sahibi kararıyla değişti. Commit'ler izinli yollarda; push yok.

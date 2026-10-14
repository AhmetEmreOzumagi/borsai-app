# BORSAI_FAZ5_FREEZE_20260924 — `post_d1_hazard_v0` dondurma raporu

Görev: `docs/prompts/FAZ5_FREEZE.md`. Dayanak: Fable bağımsız yeniden üretim ve denetim `docs/fable_faz5_audit/AUDIT.md`
(`fe8ed54`), hüküm **FREEZE_OK**. Push, tag, amend yok (proje sahibinin işi).

## 0. Kısa sonuç

- `post_d1_hazard_v0` temiz ağaçta (`borsai_dirty = false`) donduruldu; donmuş JSON altın nihai fit önizlemesiyle
  `created_at`, `code_version`, `runtime` dışında `==`. Kayıt ayrı dizinde: `models/INDEX_POST_D1.json` (tek kayıt).
- `models/INDEX.json` ve 19 listeleme öncesi model dosyası bayt-eşit; `scores/`, `docs/SCORES.md`, `registry/`, `data/`, `app/`
  değişmedi. `borsai/` altında yalnız `borsai/report_faz5.py` (MODELS.md render'ı) değişti — proje sahibi onayıyla, §7.
- İki commit: **F1** `7c18c0f` (yalnız iki model dosyası), **F2** bu raporu içeren commit (testler, günlük, errata, MODELS.md,
  `borsai/report_faz5.py`). F1, F2'nin atasıdır. Tam test: taban yeşil, F1 sonrası yeşil, F2 öncesi yeşil (§5).

## 1. Taban (adım 0)

- HEAD `fe8ed54`; izlenmeyen yalnız `docs/prompts/FAZ5_FREEZE.md` ve `docs/prompts/FAZ6_FABLE_OLD_COHORT_SPEC.md` (izinli).
- Altın `tests/reference/macos_golden_faz5/MANIFEST.json`: `borsai_source_sha256 = 5804e5cdbfde…`, `git_commit = 7ce0593`,
  `borsai_dirty = false`. HEAD'in `borsai/` kaynak sha'sı (`provenance.source_tree_sha256`) **aynı**:
  `5804e5cdbfdedd021525be051bd86c42654873dbe1bdb9339c716b5698558ab8`; `git diff 7ce0593 HEAD -- borsai` boş.

## 2. Dondurma (adım 1) ve commit F1

Komut: `.venv/bin/python -m borsai.freeze --models post_d1_hazard_v0` (temiz `borsai/`, 0.6 sn).

| Dosya | sha256 |
|---|---|
| `models/post_d1_hazard_v0.json` | `3f7640267cd0f6b114ec88cf29e811587daa18c191866f9fa2d6910bc949e5dc` |
| `models/INDEX_POST_D1.json` | `94ac36faffac6017d54ff406b97b37623c27633c847bd0117fb51bf42975b820` |

`models/INDEX_POST_D1.json` (şema `borsai.model_index/1`, tek kayıt):

```json
{
  "models": [
    {
      "algorithm": "discrete_time_hazard_offset_logit_l2",
      "data_version_sha256": "a0c7d082dacdbde03f53d1c4af1ce9f7983f9946abc80062de570f4a1df1f977",
      "file": "post_d1_hazard_v0.json",
      "frozen_at": "2026-09-24T16:28:40+03:00",
      "frozen_at_basis": "LOCAL_CLOCK_SELF_REPORTED: zaman kanıtı bu dosyayı içeren commit'in push'udur (CLAUDE.md kural 1)",
      "model_id": "post_d1_hazard_v0",
      "parent_model_id": "ceiling_hazard_v0",
      "parent_sha256": "caa4dc867a9fc20d9f57cf6269e157ee1fafc9527c5144e53797bf48af0ffb67",
      "schema_version": "borsai.model/1",
      "sha256": "3f7640267cd0f6b114ec88cf29e811587daa18c191866f9fa2d6910bc949e5dc",
      "spec_sha256": "9d01c3c08cabe1bb6611c599edfe713319faec3e048a6491e649c32ba68898f4",
      "stage": "POST_D1",
      "status": "FROZEN",
      "training_cutoff_date": "2026-08-13",
      "training_n": 81,
      "training_tickers_sha256": "7fd2e60018a1770234068f294cc41713a1e0eea9f490d02d9c87232ce6fc2989"
    }
  ],
  "schema_version": "borsai.model_index/1"
}
```

**Pinler** (kodun ön koşulu `freeze._parent_ok` ve ayrıca elle doğrulandı):

| Pin | JSON'daki | Dosyanın sha256'sı | INDEX.json | Şartname/spec |
|---|---|---|---|---|
| `parent` (`ceiling_hazard_v0.json`) | `caa4dc867a9f…ffb67` | aynı | aynı | aynı |
| `path_secondary` (`ceiling_path_v0.json`) | `3e97e8788266…6c952d` | aynı | aynı | aynı |
| `spec_document` (`docs/specs_faz5/SPEC_POST_D1_V0.md`) | `a5b4675d8478…7ead34` | aynı | — | `SPEC_DOCUMENTS_FAZ5` aynı |

`spec_sha256` (kanonik şartname sözlüğü, H15) `9d01c3c08cab…`; eğitim 81 arz, δ kümesi 409 satır, 67 olay, 342 sağ kalım,
en son eğitim seansı 2026-08-13; λ = 30, δ_lock = −0.3278985872465678, δ_turn = +0.25106109793882575.

**Önizleme ↔ donmuş JSON:** anahtar kümeleri aynı; `created_at`, `code_version`, `runtime` dışındaki bütün alanlar `==`.
Bu üç alanın durumu:

| Alan | Önizleme | Donmuş |
|---|---|---|
| `created_at` | 2026-09-24T14:53:59+03:00 | 2026-09-24T16:28:40+03:00 (farklı) |
| `code_version.git_commit` | `7ce0593f8b80…` | `fe8ed5462c9a…` (farklı) |
| `code_version.borsai_source_sha256` | `5804e5cdbfde…` | `5804e5cdbfde…` (aynı) |
| `code_version.borsai_dirty` | false | false (aynı) |
| `runtime` | python 3.12.14, numpy 2.5.2, scipy 1.18.0, scikit-learn 1.9.0, joblib 1.5.3, threadpoolctl 3.6.0 | aynı |

**Bayt-eşitlik:** dondurmadan önce ve sonra `shasum -a 256 models/*.json` karşılaştırıldı: yalnız iki yeni satır; `INDEX.json` ve
19 model dosyasının sha'sı aynı. `INDEX.json` 72a000f ile bayt-eşit (test: `test_faz5_frozen.py::test_pre_listing_index_and_models_byte_identical`).

**Hızlı kontrol** (`test_faz5_post_d1.py`, `test_faz5_golden.py`, yeni `test_faz5_frozen.py`), F1'den önce: 45 geçti, 1 kırmızı
(`test_14`: "iki POST_D1 dosyası 72a000f'e göre commit'le eklenmiş" satırı — dosyalar henüz commit'siz; F1'den sonra yeşil).
İlk hızlı koşuda yeni testin kendi hatası da kırmızıydı (`models/.gitkeep`'i dosya listesine sayıyordu); `.json` süzgeciyle düzeltildi.

**Commit F1** `7c18c0f58ed1b686d3580165eef70b0e71640e26`:

```
BORSAI_FAZ5_FREEZE: post_d1_hazard_v0 frozen into models/INDEX_POST_D1.json after independent reproduction (Fable FREEZE_OK)
 models/INDEX_POST_D1.json     |  23 +++
 models/post_d1_hazard_v0.json | 452 ++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 475 insertions(+)
```

## 3. Denetimin bıraktığı işler (adım 3; hepsi aynı model_id)

- **K3** (`test_2`): "10.12" / "10.1200000000000000001" → kilit 0 (ikisi binary64'te aynı float; test bunu da sınar);
  "10.12" / "10.120" → 1. Mutasyon gösterimi yerel klonda (scratchpad; gerçek `borsai/`'ye dokunulmadı), HEAD `fe8ed54` +
  yeni test dosyası, `predict_post_d1.evaluate_d1`: `lock = int(prices["low"] == upper)` →
  `lock = int(float(prices["low"]) == float(upper))`:

  ```
  == K3 mutasyonu (g2: float eşitliği), klon fe8ed54 + yeni test_2
  >       assert pd1.evaluate_d1(_block("10.12", low="10.1200000000000000001"), "1000000").lock == 0
  E       AssertionError: assert 1 == 0
  1 failed in 0.16s
  == geri alındı; git diff borsai: ''
  1 passed in 0.04s
  == aynı mutasyon, commit'li (eski) test_2:
  1 passed in 0.09s
  ```
  Yeni test mutasyonda kırmızı, eski test yeşil (AUDIT §3 g2 ile aynı), geri alınınca yeşil. Klon silindi.
- **K4** (`test_15`): `LAMBDA_FINAL_LIKELY == (10.0, 100.0)`, `LAMBDA_FOLD_INF_SHARE == (0.20, 0.50)`, `LOCK_SIGN_SHARE == 0.80`,
  `N_FOLDS_RANGE == (65, 71)`; ayrıca §5 satır metinleri ("10–100 en olası", "fold'ların %20–50'sinde INF",
  "(fold'ların ≥ %80'inde)", "65–71") şartnameden okunan satırlarda.
- **Donmuş model testleri** (`tests/test_faz5_frozen.py`, 8 test): önizlemeyle eşitlik ve kod damgası; pinler; `INDEX_POST_D1.json`
  şeması, tek kayıt, sha'lar (`freeze.index_entry` ile birebir); `INDEX.json` ve 19 dosya 72a000f'e bayt-eşit; donmuş dosyayla
  numpy nihai model ↔ stdlib `predict_post_d1` 81 arzda |Δ| ≤ 1e-12, h_1 ana modelle bit-eşit (var olan `final_predictions`
  altyapısı); donmuş ön işlemeyle δ = 0 ucu `ceiling_hazard_v0`'a bit-eşit (81 arz × kilitli/kilitsiz D1 = 162 durum);
  MODELS.md dondurma notu.
- **Duyarlılık satırları:** `experiments/log.jsonl` 65 → 67 satır, yalnız sona ekleme; iki satır denetimin
  `ekler/sensitivity_runs.jsonl` içeriğiyle aynı sözlük (Faz 4 kalıbı: `backtest.append_log`, kanonik JSON; Faz 4'ün beş satırının
  da kaynak sözlüğün kanonik JSON'u olduğu doğrulandı). `test_experiment_log.py` bu türü **kabul etmiyordu** (Faz 4 alan kümesi ve
  `base_model_id ∈ MODEL_SPECS`); genişletildi — ayrıntı SPEC_DEVIATIONS H "Bu görevde yapılan test ve kod düzenlemeleri".
  Satırlar `kind: sensitivity`; varyant sayacına girmez (yalnız `kind: backtest` sayılır), skor ve belgelere girmez (test).
- **Errata** (`docs/SPEC_DEVIATIONS.md` H devam): H23 (K1, B3 kod adları), H24 (K2, `D1_FIELD_INVALID`), H25 (K6, §12
  `eta = linear_predictor(parent, inputs)`), H26 (K8, eşitlik yalnız aynı kod yolunda bit-eşit farkla), H27 (K9, §6.1-7 (i) yalnız D1
  yükleyicisi; path hücreleri SPEC_CEILING_PATH_V0 §8'e göre kesimli). Şartname ve v0 kimliği değişmedi.
- **MODELS.md:** `python -m borsai.report` ile yeniden üretildi; fark yalnız Faz 5 bölümünün (dosyanın) sonuna eklenen 8 satır:
  "### Dondurma" — bağımsız yeniden üretim 2026-09-24, maks |Δ| = 1.5e-11, `docs/fable_faz5_audit/`; donmuş model sha256'sı
  (tam); k = 10 dipnotu (görev metnindeki cümle, AUDIT §5-3'e bağlı). Mevcut bölümler bayt olarak aynı (önceki "dondurulmadı"
  ifadeleri backtest anının kaydı olarak kaldı; notta söylenir).
- K5 ve K7 bu görevde yok (canlı akış görevi).

## 4. Skorlar (adım 4)

Yeniden üretilmedi. `scores/scores.json` ve `docs/SCORES.md` değişmedi; H22 istisnası geçerli (günlükteki `kind: backtest`
satırları değişmedi; yeni satırlar `kind: sensitivity`).

## 5. Testler

| Koşu | Sonuç | Süre |
|---|---|---|
| Taban (HEAD `fe8ed54`) | 490 geçti | 285 sn |
| Dondurmadan sonra, F1'den önce (bilgi) | 493 geçti, 3 kırmızı — beklenen: `test_outcome_guard::test_sequence_rule_outcomes_follow_models_and_records`, `test_outcomes::test_sequence_guard_blocks_post_cutoff_download_without_committed_models` (commit'siz POST_D1 model dosyası, doğru davranış) ve `test_faz5_post_d1::test_14` (aynı neden) | 387 sn |
| F1 sonrası (`7c18c0f` + commit'siz test/günlük değişiklikleri) | **496 geçti** | 354 sn |
| F2 öncesi (bütün değişiklikler) | **497 geçti** | 318 sn |

## 6. Kabul kapısı

- K1: dondu; önizlemeyle (üç alan dışında) `==`; `INDEX_POST_D1.json` tek kayıt, doğru sha. **Tamam.**
- K2: `INDEX.json`, 19 model dosyası, `scores/`, `registry/`, `data/`, `app/` değişmedi. `borsai/`: **istisna** — yalnız
  `borsai/report_faz5.py` (MODELS.md render'ı), proje sahibi onayıyla (§7-1). Hesap, tahmin, fit ve freeze kodu değişmedi.
- K3: K3/K4 testleri eklendi; duyarlılık satırları günlükte; errata H'de; MODELS.md güncel. **Tamam.**
- K4: F1 sonrası ve F2 öncesi tam test yeşil; F1 F2'nin atası; commit'ler yalnız izinli yollarda (+ onaylı `borsai/report_faz5.py`);
  push yok. **Tamam.**

## 7. Sapmalar

1. **K2 istisnası — `borsai/report_faz5.py`.** Görev MODELS.md'nin Faz 5 bölümüne not eklenmesini istiyordu, ama `docs/MODELS.md`
   tamamen `borsai.report.render()`'dan üretilir ve `test_report::test_models_md_is_up_to_date` bayt-eşitlik ister; not ancak
   render kodunda yazılabilir (Faz 4 dondurması da `report_faz4.py`'de yapmıştı). F1'den sonra durulup proje sahibine soruldu;
   onay koşulları: `borsai/` altında yalnız `report_faz5.py`, yalnız MODELS.md render'ı; hiçbir hesap/tahmin/fit/freeze kodu
   değişmez; `borsai/report_faz5.py` F2 yol listesine eklenir; `tests/reference/macos_golden_faz5/MANIFEST.json`'a dokunulmaz;
   bir test altın kod damgasının HEAD'e eşitliğini isterse durulur. Böyle bir test yok (taranan: `borsai_source_sha256` geçen
   bütün testler); MANIFEST değişmedi. Donmuş JSON bu değişiklikten önce, temiz ağaçta yazıldı; `code_version`'ı F1'in atası
   `fe8ed54`'ün kaynağını (`5804e5cd…`) adlandırır. F2'den sonra HEAD'in `borsai/` kaynak sha'sı farklıdır; bu beklenen ve
   testlenmeyen bir durumdur (bkz. Faz 4 dondurma notu: JSON kendi commit'ini adlandıramaz).
2. **Durum iddia eden testler F1'den önce güncellendi.** `test_faz5_post_d1::test_14` ("models/'de 20 dosya, INDEX_POST_D1 yok"),
   `test_faz5_golden::test_final_fit_preview_reproducible` ("models/'de POST_D1 dosyası yok") ve `_copy_models` (geçici dizine
   bütün `models/`'i kopyalıyordu; donmuş dosyalar gelince `test_t4_freeze_post_d1…` "zaten dondurulmuş" hatası verirdi) dondurulmamış
   durumu iddia ediyordu; F1 sonrası tam testin yeşil olabilmesi için bu düzenlemeler dondurmadan hemen sonra, F1'den önce çalışma
   ağacında yapıldı ve F2'ye girdi. F1 yalnız iki model dosyasını içerir (görev metni); F1 sonrası koşu, F1 + commit'siz test ve
   günlük değişiklikleriyle yapıldı.
3. **Duyarlılık satırlarının alan kümesi.** Denetimin satırları Faz 4 satırlarının altı alanını (`is_model`, `variant`, `note`,
   `git_commit`, `finished_at`, `borsai_source_sha256`) taşımıyor. Günlük satırı denetimin içeriğiyle aynen yazıldı (alan uydurulmadı);
   test, POST_D1 duyarlılık satırlarını denetimin alan kümesiyle kabul edecek biçimde genişletildi ("model değil" bilgisi
   `variation.note`'ta).
4. Görev metni pre-F1 hızlı kontrolün yeşil olmasını bekliyordu; `test_14`'ün commit'e bağlı tek satırı F1'e kadar kırmızıydı
   (§2), F1'den sonra yeşil.

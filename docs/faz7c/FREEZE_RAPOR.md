# BORSAI_FAZ7C_FREEZE_20260928 — `fall_d10_v0` ailesinin ("düşen arz") dondurulması: rapor

Görev `docs/prompts/FAZ7C_FREEZE.md` (Opus 5.5, bağımsız el: sonuçları gören uygulayıcıdan ayrı oturum). Ağ yok; push, tag, amend
yok. Bağlayıcı metinler `docs/specs_faz7_c/SPEC_C_V0.md` (sha256 `d75c17cfec09712174c86ac8619b5d51fb5681fc161f48455423b84d9e8db5ac`)
ve `docs/specs_faz7_c/KARARLAR_C.md` (sha256 `2b60bec41924…`); denetim `docs/fable_faz7c_audit/AUDIT.md` (`80670cb`: dört kimlik
FREEZE_OK). **Model davranışı değişmedi**: bütün değişiklikler "kodu şartnameye uydurmak = aynı model_id" sınıfındadır; şartname
değişmedi.

## 0. Kısa sonuç

- Dört kimlik donduruldu: `fall_d10_v0_h99`, `fall_d10_v0_pooled`, `fall_d10_v0_addsale`, `fall_d10_v0_pooled@ZERO` (şartname
  gereği dördü; yakın dönem birincil hücresi `pooled − h99` "belirsiz", dondurma kararına girmez).
- Donmuş JSON'lar nihai fit önizlemeleriyle `created_at`, `code_version`, `runtime` dışında `==` (gerçekte yalnız `created_at` ve
  `code_version` farklı; `runtime` de aynı); dondurma temiz ağaçta (`borsai_dirty` false), JSON'lar K'nın kodunu adlandırır.
- `models/INDEX.json` 23 → 27 giriş; ilk 23 giriş metin olarak aynı; 23 eski model dosyası, `post_d1_hazard_v0.json` ve
  `INDEX_POST_D1.json` bayt-eşit.
- Denetim bulguları F1–F9 kapandı (kod, test ya da belge; §3). F5 render düzeltmesi MODELS.md'de yalnız `@ZERO` fold özeti satırını
  değiştirdi. F9'un iki semantik testi denetimin d ve p mutasyonlarında kırmızı.
- Proje sahibine bu görevde iki soru soruldu (§8): (C) INDEX'e girince çöken iki kod yeri için **asgari düzeltme K'da** (K22) ve J30
  istisnasına **`faz7c_near_era` bloğunun** eklenmesi (K19). İkisi de onaylandı.
- Tam test her aşamada yeşil (F1 sonrası 817 passed); uygulama yeniden pinden (APPPIN) sonra `test.sh` ve `gen_golden --check` yeşil.

## 1. Commit'ler (sıra K → F1 → APPPIN → F2)

| Commit | Hash | Üst | İçerik |
|---|---|---|---|
| K | `5494f70809b74470e59fdd7e5e2da8b30555b96b` | `80670cb` | `borsai/` (freeze, registry, report, report_faz7c, scoring), testler (yeni `test_faz7c_freeze.py`, 16 dosyada uyarlama), `experiments/log.jsonl` (+5), MODELS.md (yalnız F5 satırı), SPEC_DEVIATIONS (K3/K6/K9/K14 ekleri, K16–K23), `docs/faz7c/ekler/` (3 dosya), görev dosyası — 27 dosya, +785 / −79 |
| F1 | `ce569a8ecf98578af508eb75713da4776ef1a3cc` | `5494f70` | yalnız `models/fall_d10_v0_{h99,pooled,addsale,pooled@ZERO}.json` ve `models/INDEX.json` — 5 dosya, +1802 |
| APPPIN | `6bbbb61cca8cd92bedfcc2b2d08eebbd06038f34` | `ce569a8` | `app/parity/golden/MANIFEST.json` (1 satır), `app/tests/fixtures/ui/preflight_{ok,blocked}.json` (INDEX sha), `app/src-tauri/tests/build_embed.rs` (beklenen yok sayılan liste) — 4 dosya, +11 / −7 |
| F2 | (bu raporu içeren commit) | `6bbbb61` | `tests/test_faz7c_frozen.py` (yeni), `borsai/report_faz7c.py` (dondurma notu), `docs/MODELS.md` (INDEX'in 4 yeni satırı + not), `docs/faz7c/` |

Model dosya adları `freeze`'in yazdığı, görev metnindeki adlardır.

## 2. F1 · dondurma

`.venv/bin/python -m borsai.freeze --models fall_d10_v0_h99 fall_d10_v0_pooled fall_d10_v0_addsale fall_d10_v0_pooled@ZERO`
(HEAD `5494f70`, ağaç temiz, `borsai_dirty` false; 9 sn).

| model_id | sha256 | Eğitim n | Veri sürümü | spec_sha256 (ilk 12) |
|---|---|---|---|---|
| `fall_d10_v0_h99` | `b15eaa8cb1f76441088173e7582f636afe281855d924d23220d6ae076fe89beb` | 94 (kesim 2026-08-19) | `a0c7d082…` (H99) | `e21c0a32bb98` |
| `fall_d10_v0_pooled` | `d2c5d549961173468486c159045c9d4361bd034e2a5c6bb5494aad68477f7c64` | 161 | `2ee8d51b…` (v2) | `1054f2c22147` |
| `fall_d10_v0_addsale` | `b95fc3ecee262f7b58441215d9c65ba682808c5a2cddd643f2e05f64640b8e09` | 165 | `2ee8d51b…` (v2) | `b0b04566f987` |
| `fall_d10_v0_pooled@ZERO` | `7c23b9236c0a0ccc4192d8da58f0e1745fbd7443f1a6e78e2a056580fbfd8c3d` | 161 | `2ee8d51b…` (v2) | `0c96245fb80f` |

INDEX'e eklenen dört giriş (`FAZ7C_MODEL_IDS` sırası) `freeze.index_entry` alanlarıyla: algorithm `l2_logit_v1_6_grid`, file,
sha256 (yukarıda), schema_version `borsai.model/1`, spec_sha256, training_n, training_cutoff_date 2026-08-19, training_tickers_sha256
(h99 `afa8b051…`, pooled ve @ZERO `ab563e21…`, addsale `13beb5da…`), data_version_sha256, frozen_at 2026-09-28T21:27:17 / 21:27:22 /
21:27:24 / 21:27:24 +03:00, frozen_at_basis, status FROZEN. Yeni INDEX sha256
`7e636e8bf64b25d79bac04f4bf78b9f870cded8d4d1c10009b6926941e4edb59` (önce `53265dd5…`). Her JSON'da `spec.spec_document.sha256` =
`d75c17cf…db5ac` = şartname dosyasının sha'sı; `decisions_document` KARARLAR_C.md'nin sha'sı.

**Önizleme ↔ donmuş JSON:** dördünde de yalnız `created_at` ve `code_version` farklı (`code_version` = {git_commit `5494f70…`,
borsai_dirty false, borsai_source_sha256 `cdcb3e0b2ee3…` = K'nın `borsai/` ağacı}); `runtime` dahil öteki bütün alanlar `==`.
Uyuşmazlık yok. Commit öncesi hızlı kontrol (`test_faz7c_golden.py`, `test_faz7c_model.py`, `test_models.py`): 71 passed, 3 failed —
üçü de commit'siz durumdan (`models/` çalışma ağacında commit'lenmemiş: iki temizlik denetimi; MODELS.md yeniden üretilmemiş:
`text == render()`); F1 ve MODELS.md yeniden üretiminden sonra yeşil (tam koşu §6).

## 3. Denetim bulguları F1–F9

| # | Bulgu | Ne yapıldı |
|---|---|---|
| F1 | K3: etiket yönü simetrisi, lbfgs'nin sayısal yolu | SPEC_DEVIATIONS K3'e ek: ölçülen fark (addsale D5 \|Δp\| 8.7e-9; iç LOOCV \|Δ\| ≤ 5.3e-10; β_up + β_down ≤ 2.2e-16), eşik Y_h fit'inde tanımlı ve öyle kalır. Kod ve şartname değişmedi. |
| F2 | K9: günlükteki `spec_sha256` belge sha'sı değil | SPEC_DEVIATIONS K9'a not; donmuş JSON'larda belge sha'sı `spec.spec_document.sha256` (testli: `test_frozen_files_equal_previews_and_clean_code`); MODELS.md dondurma notu belge sha'sını bu alandan yazar. |
| F3 | K10: `h99` kartının sayacı aile keşfini saymıyor | Orkestratör kararıyla sıradaki skorlama görevinde (K23); bu görevde sayaç, kart, `scores/` değişmedi. |
| F4 | K6 seçeneğine duyarlılık (D5 h99 hücresi) | SPEC_DEVIATIONS K6'ya bilgi eki (B'de −0.0259 [−0.0653, +0.0085]); duyarlılık satırları günlükte (K21). |
| F5 | MODELS.md `@ZERO` fold özeti "ek satış … düşen fold 94" | `report_faz7c.fold_summary(rows, features)`: kural satırı alanı yazmaz (K17). Fark: yalnız `@ZERO` satırı, iki ifade çıktı (D10 ve D5); başka bayt yok. |
| F6 | Parite testleri yazılmış JSON'dan koşmalı (süreç) | SPEC_DEVIATIONS K14'e kalıp notu; bu görevin bütün parite testleri yazılmış dosyadan (önizleme baytlarıyla kurulan geçici INDEX; diskteki donmuş dosyalar). |
| F7 | K6'nın yeri, KARARLAR_C ve push kanıtı (süreç) | SPEC_DEVIATIONS K6'ya: K6 **bağlayıcı proje sahibi kararıdır**, KARARLAR_C'nin yanında okunur; sıra kanıtı git DAG'ı; F1'in push'u A'yı ata olarak kapsar. |
| F8 | Kasa kodunun bir H99 unvan sözcüğü olarak geçmesi (bilgi) | K23'te not; bu görevin yeni dosyalarında kasa kodu ve bülten adı kalıbı yok (bekçi testleri; `test_no_sealed_code_in_training_tables_or_new_files` `docs/faz7c/`'yi tarar). |
| F9 | Etiket yönü ve kırpma sınırlarının test arzını dışlaması yalnız altın regresyonla pinli | `tests/test_faz7c_freeze.py`'de iki semantik test (K18). Denetimin mutasyonları (çapalar aynen): d → test arzı değişmezliği 3/3 kırmızı; p → işaret testi 2/2 kırmızı (fold ve nihai fit kısımları ayrı ayrı da kırmızı); mutasyonsuz 5/5 yeşil; `borsai/` ağacı önce/sonra `6f96e741…` (`docs/faz7c/ekler/k3_f9_mutasyon.txt`). |

## 4. K · kod, test ve belge değişiklikleri

- **K1 · dondurma yönlendirmesi (K16):** `freeze.freeze` FAZ7C kimliklerini `freeze.fit_fall` → `backtest.final_fit_fall`'a yönlendirir
  (kod yolu önizlemeninkiyle aynı); `freeze.model_kind` → `fall` (`specs.model_kind` ile aynı; testli), `run_model` →
  `predict_fall.predict`; CLI `--models` tanır. `registry.F3_MODELS` += `fall_d10_v0_h99`, `fall_d10_v0_pooled`.
- **`build_record` (C) girdilerini zaten yazıyor** (sentetik testle gösterildi, `test_faz7c_freeze.py`): `additional_sale_shares`
  V1.5 alanıdır (`model_inputs`'ta), `tufe` bloğu h99/pooled'ı da pinler (deflatör bloğu `ceiling_hazard_v1_real`'inkiyle aynı),
  `tufe_index` onlara gider; ret yolları kayıt içinde (f3 boş → h99/pooled F3_MISSING; ek satış boş → üç aday
  ADDITIONAL_SALE_MISSING; TÜFE önek pini tutmazsa deflatörlü v1 ve (C) hücreleri TUFE_FILE_MISMATCH); TÜFE ön koşulu v1 ile ortak,
  yeniden yazılmadı (INDEX'te deflatörlü model olarak yalnız (C) olsa da ay yoksa `TufeMissing`). Nihai fit'lerin f3 filtre modu
  NOT_SPECIFIED: açık durumlu girdi (ör. canlı sicildeki UNFILTERED arz) uyuşmazlık reddi almaz (V1.5 kuralı).
- **K22 (proje sahibi kararı):** `report.py` "Kayıtlı modeller" satırı D1'i olmayan modelde D10 başlığını okur; `scoring.prediction_of_cell`
  `fall` hücresinde yalnız D5/D10 p_up'ı okur. (C) hücre tanımları değişmedi (sıradaki skorlama görevi).
- **K2 · F5:** §3. **K3 · F9:** §3. **K4 · belgeler:** SPEC_DEVIATIONS K3, K6, K9, K14 ekleri ve K16–K23.
- **K5:** denetimin 5 duyarlılık satırı günlüğe aynen (kanonik biçim; 2 137 → 2 142 satır; K21).
- **K6 · INDEX 27 hazırlığı (K19, K20):** "23 giriş" varsayan testler INDEX'ten sayar (`faz7_support.frozen_tail_ids`,
  `frozen_faz7c_ids`); J30 istisnası sekiz karta ve `faz7c_near_era` bloğuna, aynı koşullarla; `test_app_golden_pins_unchanged` F1 ile
  APPPIN arasındaki tek geçiş durumunu (yalnız MANIFEST'in INDEX sha'sı eski) kabul eder, APPPIN'den sonra kesin koşul.
- **Geçici klonda dondurma provası** (oturum scratchpad'i; `docs/faz7c/ekler/freeze_test_runs.txt`): yalnız yönlendirmeyle F1 sonrası
  42 failed + 3 error (test varsayımları, iki kod çökmesi, J30 bloğu, uygulama pini); bütün K ile 1 failed (dondurma notunun
  varlığına bağlanan "kasa: bekliyor" sayısı, düzeltildi); aynı klonda F2 notu ve donmuş-model testleri yeşil.

## 5. Bayt-eşitlikler

- `models/INDEX.json` eski metnin son girişine kadarki önekiyle başlar; ilk 23 giriş `80670cb`'dekiyle aynı; 23 eski model dosyası,
  `post_d1_hazard_v0.json`, `INDEX_POST_D1.json`: 25/25 bayt-eşit (`tests/test_faz7c_frozen.py` ayrıca `80670cb`'yle sınar).
- MODELS.md: K'da yalnız `@ZERO` fold özeti satırı; F2'de yalnız "Kayıtlı modeller" tablosunun 4 yeni satırı ve Faz 7C bölümünün sonundaki
  "### Dondurma" notu (21 satır). Faz 7, Faz 4, Faz 5 bölümleri aynen (bölüm testleri).
- `experiments/log.jsonl`: yalnız sona 5 satır (eski 2 137 satır bayt-eşit önek).
- `tests/reference/`, `scores/`, `docs/SCORES.md`, `registry/`, `data/`, `docs/specs*`, `docs/fable_faz7c_audit/`, `docs/app/`,
  `legacy/`, `CLAUDE.md` değişmedi. `app/`'te yalnız APPPIN'in dört dosyası (Rust mantığı yok; 16 eski altın dosya bayt-eşit, U46).

## 6. Test sayıları (ayrıntı `docs/faz7c/ekler/freeze_test_runs.txt`)

| Aşama | pytest | test.sh | gen_golden --check |
|---|---|---|---|
| Taban (80670cb) | 806 passed, 642.2 s | yeşil (cargo 94, npm 222, parity 4, U46) | 25/0 |
| K öncesi (commit'siz; eşzamanlı prova koşusu) | 817 passed, 976.7 s | yeşil (cargo 94, npm 222, parity 4, U46) | 25/0 |
| F1 sonrası (HEAD ce569a8; MODELS.md çalışma ağacında yeniden üretilmiş) | 817 passed, 663.5 s | — | — |
| APPPIN öncesi (F1 = ce569a8) | — | exit 101; cargo `--no-fail-fast` 92 passed / 2 failed (`build_embed::plan_pins_first_19_index_entries`, `stage3::wizard_fixtures`), npm 222, parity 3 passed / 1 failed (`test_golden_files_are_reproducible`: MANIFEST) | 25 / ["golden/MANIFEST.json"] |
| APPPIN sonrası (6bbbb61) | — | yeşil, 25 s (cargo `--no-fail-fast` 94 / 0, npm 222, parity 4, U46) | 25/0 |
| F2 öncesi (HEAD 6bbbb61; F2 değişiklikleri ağaçta) | 829 passed, 648.7 s (+12: `tests/test_faz7c_frozen.py`) | yeşil, 36 s (cargo 94, npm 222, parity 4, U46) | 25/0 |

## 7. Uygulama etkisi (EK3 girdisi)

- APPPIN öncesi kırılan dört yer Faz 7'dekiyle aynı: golden MANIFEST `models_index_sha256`, iki UI preflight fikstürü (INDEX sha),
  `build_embed` testinin beklenen yok sayılan listesi. Yeniden pinden sonra `build_embed` sabit 19 kaydı gömer, 8 kaydı (4 v1 + 4 (C))
  `ignored_model_ids`'e alır; gömülü INDEX 27 girişli (sha `7e636e8b…`).
- [ÇIKARIM, bu görevde ayrıca ölçülmedi] Faz 7 §9'da ölçülen davranışın aynısı beklenir: bugünkü derlenmiş ikili yeni INDEX'le
  `INDEX_SHA` ön koşulunda durur; yeniden derlenince (C) hücrelerini içeren bir kaydın paritesinde (C) hücreleri `unsupported`
  listesine düşer (uyuşmazlık değil).
- EK3'ün işi: Rust (C) desteği (`predict_fall` portu, ret sırası, `@ZERO` sabit başlık), `PINNED_MODEL_IDS` ve `predict_sources_sha256`'ya
  `borsai/predict_fall.py`, altın vektörler, "Düşüş (D10)" kartı (SPEC_C_V0 §9; aile keşif sayısı kartta ayrıca).

## 8. Sapmalar ve kararlar

1. **K22 — iki kod düzeltmesi görevin K1–K3 listesi dışında** (`borsai/report.py`, `borsai/scoring.py`): (C) INDEX'e girince D1 ufku
   varsayan iki yer çöküyordu (MODELS.md üretilemez; eski kohort skorlamasının sentetik testleri KeyError). Proje sahibine soruldu:
   **asgari düzeltme K'da** onaylandı. Skor tanımları ve gerçek skorlar değişmedi.
2. **K19 — J30 istisnasına `faz7c_near_era` bloğu:** yeniden hesap (C) INDEX'teyken bu bloğu yazıyor; proje sahibine soruldu, aynı
   koşulla (scores.json 8e3a623 ile bayt-eşitken) çıkarılması onaylandı. Sekiz kart için genişleme görev metninde önceden onaylıydı.
3. **K20 — `test_app_golden_pins_unchanged` geçiş durumu:** görevin sırası (tam test F1 sonrası, APPPIN ondan sonra) ile bu Faz 7C
   testinin `gen_golden --check`'i çelişiyordu; yalnız MANIFEST'in INDEX sha'sı eskiyken ve öteki her şey aynıyken geçer. APPPIN'den
   sonra kesin koşul.
4. **Dondurma notu F2'de** (`report_faz7c.py`, görev metnindeki yer); bu yüzden `test_models_md_faz7c_section`'daki "kasa: bekliyor"
   sayısı notun varlığına bağlandı (K commit'inde), notun kendisi `test_faz7c_frozen.py`'de sınanır.
5. **K öncesi tam koşudan sonra bir test satırı değişti** (yukarıdaki madde; yalnız o test 1 passed); F1 sonrası tam koşu K'nın
   commit'li halini kapsar.
6. Eski kohort ek kayıtları, model başına kapı, `oot_pre_h99_sealed/_all`, skorların yeniden üretimi, F3 sayacı ve Rust desteği
   yapılmadı (orkestratör kararı; sıradaki görevler).
7. Hijyen: yeni metinlerde bülten adı kalıbı ve kasa kodu yok (bekçi testleri yeşil); F9 denetim çıktısında test adları dışında kod yok.

## 9. Push'tan sonra proje sahibinin koşacağı kanıt komutu

Zaman kanıtı push'tur: dalı (F1 `ce569a8` ve sonrasını) push ettikten sonra

```
.venv/bin/python -m borsai.push_proof ce569a8
```

Canlı sicilde (C) için n, bu dondurma commit'inin push kanıtından sonra listelenen arzlarla başlar.

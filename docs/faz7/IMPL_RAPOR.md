# BORSAI_FAZ7_HAZARD_V1_IMPL_20260925 — uygulama ve backtest raporu

Görev: `docs/prompts/FAZ7_HAZARD_V1_IMPL.md`. Şartname `docs/specs_faz7/SPEC_HAZARD_V1.md` (sha256 `25229cea8f6f…`, commit
`6a16c16`, push kanıtı 2026-09-25T18:09:45Z) ve proje sahibi kararları `docs/specs_faz7/KARARLAR.md` (sha256 `eb6ac63cce3e…`;
çeliştiği yerde bağlayıcı) **değiştirilmedi**. Dört model (`ceiling_hazard_v1_clip`, `_real`, `_pooled`, `_pooled@INF`)
**dondurulmadı**: `models/`, `INDEX.json`, `INDEX_POST_D1.json` değişmedi. `registry/`, `scores/`, `legacy/`, `docs/specs*`
değişmedi; `app/`'te yalnız T2 pini. push/tag/amend yok.

Bütün sayılar **backtest terazisindedir** (retrospektif walk-forward, H99 test arzları) ve **tasarıma maruzdur** (şartname
§10: gün grupları H99'dan, v0'ın H99 sonucu şartname yazılırken biliniyordu). Kasa (§5.2) ve canlı (§5.3) teraziler bu raporda
yoktur; hiçbir sayı toplanmaz. Fark = aday − karşılaştırılan; negatif = aday iyi.

## 0. Kısa sonuç

- **Yakın dönem birincil hücreleri** (aday − `ceiling_hazard_v0`, RPS, ilk işlem ≥ 2024-01-01; n = 78 fold, 22 ay bloğu):

  | Aday | fark [%95] | etiket (§5.1) | §6.2 beklentisi | konum (T6) |
  |---|---|---|---|---|
  | `ceiling_hazard_v1_clip` | −0.0011 [−0.0066, +0.0049] | **tolerans içinde** | −0.003 [−0.010, +0.005], "tolerans içinde" | **aralık içinde** |
  | `ceiling_hazard_v1_real` | +0.0104 [+0.0028, +0.0183] | **bozuyor** | −0.004 [−0.015, +0.008], "tolerans içinde ya da belirsiz" | **üstünde** |
  | `ceiling_hazard_v1_pooled` | +0.0289 [+0.0089, +0.0518] | **bozuyor** | +0.002 [−0.010, +0.015], "belirsiz olası; bozuyor beklenmiyor" | **üstünde** |
  | `v1_pooled` − KM (§6.2 ikincil satırı) | −0.0253 [−0.0386, −0.0099] | — | −0.05 [−0.08, −0.02] | **aralık içinde** |

- **Beklentiden çok iyi (T6): yok** — hiçbir nokta §6.2 aralığının altında değil.
- **Proje sahibinin sorusu** ("eski arzları eğitime katmak bugünkü tahminleri bozmaz mı?"): yakın dönem terazisinde cevap
  **"evet, bozuyor"** (§6.4 (b); `v1_pooled` − v0 = +0.0289 [+0.0089, +0.0518]). Dönüşüm sorusu: `v1_clip` "tolerans içinde"
  (kırpma yakın dönemi bozmuyor), `v1_real` "bozuyor" (kırpma + TÜFE deflasyonu yakın dönemi bozuyor).
- **Sonucun kurala etkisi (§5.5, önceden yazılı):** k3 ("yakın dönem hücresi bozuyor değil") `v1_real` ve `v1_pooled` için
  sağlanmıyor; ikisi kasa sonucu ne olursa olsun uygulama birincili olamaz. Üç aday da dondurulur, canlıda skorlanır ve listede
  kalır (§5.5-4, §6.4, KARARLAR K4). `v1_clip` için k3 engeli yok; k1 ve k2 kasayı bekler.
- **Merdiven (§5.4, yalnız pay):** kırpmanın payı −0.0011 [−0.0066, +0.0049]; deflasyonun payı +0.0115 [+0.0045, +0.0190];
  havuz + rejimin payı +0.0185 [+0.0005, +0.0389].
- **İç tutarlılık (§8):** `v1_real`'in fold hesabı f1r := f1 ile `v1_clip` ledger'ına, havuz planı yalnız H99 satırlarıyla
  `v1_real` ledger'ına **bit-eşit**; merdiven farkları yalnız deflatörden ve açık küme satırları + rejim teriminden gelir,
  kod yolundan değil (testli).
- **Beklenen sayılar tablosu:** 9 denetimin 9'u tuttu (§2).
- Sıradaki adım (görev yolu): Fable'ın bu şartnameden sıfırdan yeniden üretimi (ledger'lar |Δ| ≤ 1e-9), sonra dondurma.

## 1. Commit'ler

| Commit | Hash | İçerik |
|---|---|---|
| A | `2a21a96c950579cd56f4983f72175f130c1b3bb0` | kod, TÜFE serisi, `training_table_v2`, kurallar (etiket, §6.2 konumu), sentetik ve birim testler, SPEC_DEVIATIONS J, KARARLAR; gerçek veride walk-forward skoru ve nihai fit YOK |
| B | `70b67d11319f5e46c18e94541e0ea17786298940` | dört resmi koşu (`experiments/log.jsonl` +4 satır, context `faz7_golden`, `git_commit` = A, `borsai_dirty = false`); `tests/reference/macos_golden_faz7/` (12 dosya); MODELS.md "Faz 7: tavan serisi v1" bölümü (+135 satır, yalnız ekleme); `tests/test_faz7_golden.py` (17 test); J16 istisnasının beşinci teste uygulanması (§9); `docs/faz7/ekler/impl_test_runs.txt` |
| R | bu raporu içeren commit (dosya kendi hash'ini taşıyamaz) | bu rapor; `docs/faz7/ekler/olcum_beklenen_sayilar.py` ve `.txt` |

A → B → R sırası korundu; B, A'nın doğrudan çocuğudur. **`borsai/` A'dan beri değişmedi** (`git diff 2a21a96 -- borsai` boş):
sonuçlar görüldükten sonra hiçbir kod, tanım, eşik ya da ızgara değişmedi. `git show --stat 2a21a96`:

```
 app/parity/golden/MANIFEST.json                    |   2 +-
 borsai/backtest.py                                 | 549 ++++++++++++++++++++-
 borsai/data.py                                     | 293 +++++++++++
 borsai/hazard.py                                   | 176 +++++--
 borsai/predict_hazard.py                           | 151 +++++-
 borsai/preprocess.py                               |  97 ++--
 borsai/report.py                                   |   8 +-
 borsai/report_faz7.py                              | 392 +++++++++++++++
 borsai/specs.py                                    | 154 +++++-
 borsai/tufe.py                                     | 174 +++++++
 data/build_training_table_v2.py                    |  50 ++
 data/data_version_v2.json                          | 106 ++++
 data/raw/tuik/build_tufe_csv.py                    | 355 +++++++++++++
 data/raw/tuik/tufe_bultenleri.csv                  |  83 ++++
 .../tufe_degisim_oranlari_bulten_58290.source.json |  20 +
 .../tuik/tufe_degisim_oranlari_bulten_58290.xls    | Bin 0 -> 58368 bytes
 data/raw/tuik/tufe_genel_2025_100.csv              |  83 ++++
 data/training_table_v2.csv                         | 171 +++++++
 docs/PROVENANCE.md                                 |  14 +
 docs/SPEC_DEVIATIONS.md                            |  29 ++
 docs/faz7/ekler/impl_test_runs.txt                 |  36 ++
 docs/faz7/ekler/t4_mutation.txt                    |  17 +
 docs/prompts/FAZ7_HAZARD_V1_IMPL.md                | 128 +++++
 docs/specs_faz7/KARARLAR.md                        |  27 +
 tests/faz7_support.py                              | 101 ++++
 tests/test_faz4_ceiling_path.py                    |   6 +-
 tests/test_faz5_live.py                            |  11 +-
 tests/test_faz7_backtest.py                        | 202 ++++++++
 tests/test_faz7_model.py                           | 289 +++++++++++
 tests/test_faz7_table_v2.py                        | 183 +++++++
 tests/test_faz7_tufe.py                            | 141 ++++++
 tests/test_outcome_guard.py                        | 100 +++-
 tests/test_scoring.py                              |  15 +-
 33 files changed, 4069 insertions(+), 94 deletions(-)
```

`git show --stat 70b67d1`:

```
 docs/MODELS.md                                     | 135 +++++
 docs/faz7/ekler/impl_test_runs.txt                 |  28 +
 experiments/log.jsonl                              |   4 +
 tests/faz7_support.py                              |   7 +
 tests/reference/macos_golden_faz7/MANIFEST.json    | 119 ++++
 tests/reference/macos_golden_faz7/SHA256SUMS       |  10 +
 .../base_km_expanding__pooled_fold_ledger.csv      |  98 ++++
 .../base_km_last10__pooled_fold_ledger.csv         |  98 ++++
 .../ceiling_hazard_v1_clip_final_fit_preview.json  | 467 ++++++++++++++++
 .../ceiling_hazard_v1_clip_fold_ledger.csv         |  88 +++
 ...ing_hazard_v1_pooled@INF_final_fit_preview.json | 424 +++++++++++++++
 .../ceiling_hazard_v1_pooled@INF_fold_ledger.csv   |  98 ++++
 ...ceiling_hazard_v1_pooled_final_fit_preview.json | 599 +++++++++++++++++++++
 .../ceiling_hazard_v1_pooled_fold_ledger.csv       |  98 ++++
 .../ceiling_hazard_v1_real_final_fit_preview.json  | 497 +++++++++++++++++
 .../ceiling_hazard_v1_real_fold_ledger.csv         |  88 +++
 tests/test_faz5_live.py                            |  16 +-
 tests/test_faz7_golden.py                          | 318 +++++++++++
 18 files changed, 3189 insertions(+), 3 deletions(-)
```

### Hash'ler

| Nesne | sha256 |
|---|---|
| `docs/specs_faz7/SPEC_HAZARD_V1.md` | `25229cea8f6f235db6562f3dee4992e6b8e22e0cbc23b44b25eeb6d2704d0944` |
| `docs/specs_faz7/KARARLAR.md` | `eb6ac63cce3efdd05c824e474d9be53ccd70e992ce952f9f58c77a391f70ff36` |
| şartname sözlüğü (`spec_sha256`): `v1_clip` / `v1_real` / `v1_pooled` / `v1_pooled@INF` | `6103d3c9189cf70dd92e65e0bba62d482e71b4d4e7ac5248aca120069684af19` / `fea051b617520b9fedcfe2876abbf8f80614250e4fd527e182479e7bf920f327` / `2a088b0d86d7c9868558d3004b6b7de9545734cf4155b51a67f8ac2ce0eb6845` / `f53ad4cf1ba9dd08ab03678e86e5a49b56b1363d8205b27c00113d280ab82872` |
| `data/training_table_v2.csv` | `5adda8b2003d0d10a7245e06cb6bc3b126260c3a84dabc27cac966b781da3e6a` |
| `data/data_version_v2.json` (v2 veri sürümü) | `2ee8d51be3f026ad05ff7b4894f9512809556b3da2fd2d0b06256b7de5ee525a` |
| `data/data_version.json` (H99 veri sürümü; değişmedi) | `a0c7d082dacdbde03f53d1c4af1ce9f7983f9946abc80062de570f4a1df1f977` |
| `data/raw/tuik/tufe_genel_2025_100.csv` (= 2026-08'e kadarki önek pini) | `3d61cbcfca2453cfce476d4cfaae38a3c77c68a4d168641162d1627e731a567b` |
| `data/raw/tuik/tufe_degisim_oranlari_bulten_58290.xls` | `6f7ee8e4ce7e8a7ac79a332db375c4a3179d02162a5d72f684d352aa6c70ff86` |
| ledger `ceiling_hazard_v1_clip` / `_real` / `_pooled` / `_pooled@INF` | `ca711a6c029c9e3e6c51a233511b4e862e4b33b86bc0277385d16e6d5fbc533b` / `026598438264298a89a587fecfbbb9c7b4cada37141725cd56a54b86688f632c` / `45a3e2dfe5f57851e9686bb0c9128d09a658958b06f6df91b68bcf1e74dbf6c5` / `08cec307684d4da7aaa863fc5d3e22827a6032834a34c1d52914cfb5475a4128` |
| havuz planı KM ledger'ı `base_km_expanding__pooled` / `base_km_last10__pooled` | `cd77d9fec3d6446d38d56a007642837b3e012ae417b4719ef697e994273f6738` / `e93ffc42a75ee8c8e5b3587351e1d91f4e2b2f890911b65e4908074c89f3f525` |
| nihai fit önizlemesi `clip` / `real` / `pooled` / `pooled@INF` | `18fdfb92d286602796e41f5ca6888b55b137bb86cd77518f2e3a25b928050e81` / `212a4075da6c306b9e7d234f7ef2b98b8cb0ae87c97e1b33e290d8d4913cef55` / `4fab0d630259aaf3054b32eae481e90b667212bea9a154ca7db16472cec35f9a` / `88c069584f7214c9c2323e61e7e8e3ab58b61076d0f4ca584cb4c66925a8f2ad` |
| `tests/reference/macos_golden_faz7/MANIFEST.json` / `SHA256SUMS` | `46c401b5a50b4b38737735677e24e713f87c58290755fde571ae5207e772d0cc` / `38f35891df7c3e86c980ba8e4b385a89fb6d1ebe53ffb153438e910cc94ac50f` |
| v0 karşılaştırıcı ledger'ı (Faz 1B, pinli) | `976b4dcea9819160bf863873a0a3e3a639942bdfeec6f9229e015047c904665b` |
| `borsai/` kaynak sha'sı (resmi koşu, `code_version`) | `41f5ad27fcad84047d40e1eeeb95857c0cb113695500849d6fa8cb60173b150b` |
| uygulama pini `predict_hazard.py` (T2) | `a1523ac810a2…` → `6ceeeb46ff8576ee7ee020b2155b19ed8f2fdf38f5a91a80345fb7ddec184cd9` |


## 2. Beklenen sayılar (görev tablosu; ölçülen)

Ölçüm `docs/faz7/ekler/olcum_beklenen_sayilar.py` (yalnız okur; çıktıda arz kodu yok; kasa üyelerinin dosyaları okunmaz), ham
çıktı `docs/faz7/ekler/olcum_beklenen_sayilar.txt`. Aynı sayılar A ve B testlerinde assert'lidir.

| Denetim | Beklenen | Ölçülen | Sonuç |
|---|---|---|---|
| `training_table_v2.csv` | 170 satır; H99'un 99 satırı paylaşılan sütunlarda bayt-eşit; `training_table.csv` ve `data_version.json` sha'sı değişmez | 170 satır (H99 99, OOT_OPEN 71); 31 paylaşılan sütunda 99/99 bayt-eşit; `training_table.csv` `b307cd0e…`, `data_version.json` `a0c7d082…`, `build_training_table.py` 6a16c16'dakiyle aynı | tuttu |
| açık 71 üyenin L dağılımı | {0: 9, 1: 11, 2: 5, 3: 4, 4: 3, 5: 8, 6: 5, 7: 6, 8: 5, 9: 6, 10: 9} | aynı; her üyenin L'si `data/outcomes_oot` ile birebir (A testi) | tuttu |
| `alloc_regime` | tek fonksiyondan; kohort etiketiyle 135/135 | v2'nin 170 satırı `data.alloc_regime`'den; açık kümede kohort etiketiyle 71/71, H99'da 99/99 EQUAL_DIST; fonksiyon `registry.compute_regime_tags` ile 2019-01-01…2026-12-31'in 2922/2922 gününde eşdeğer; 135/135 = bu eşdeğerlik + `test_real_cohort_validates_and_reproduces_from_code` (kohort etiketleri `compute_regime_tags(bookbuilding_start)`'tan). İlk işlem günü okumasında etiket 4 üyede farklı (2021-11-11 sınırı), ikili r 135/135 aynı (J2) | tuttu (J2 okumasıyla) |
| kasa kodu | `data/` altında 0 | T4 bekçisi (bütün `data/`, 64 kasa kodu): 0 sorun; yeni altı dosyada 0. Önceden var olan tek satır `data/outcomes/COMPLETENESS.csv`'de (Faz 2B, kasa çekilişinden önce yazıldı; kapsam dışı bir 2026 enstrümanı; J18 istisnası, sayısı 1'e pinli) | tuttu (J18 notuyla) |
| TÜFE | 2019-11'den güncele kesintisiz; 2025 ortalaması 100.00 ± 0.05; `month_for` örnekleri; `release_date < T` 170/170 | 2019-11…2026-08, 82 ay, kesintisiz; 2025 ortalaması 100.0000; `release_date` ≥ izleyen ayın 3'ü 82/82; `month_for` 4/4 (2026-09-02 → 2026-07, 2026-09-25 → 2026-07, 2026-10-01 → 2026-08, 2020-01-06 → 2019-11); `release_date < T` 170/170; v2'nin `tufe_month`/`tufe_index`'i `tufe.index_for(T)` ile 170/170 | tuttu |
| PP | H99 f3'lü 506 / 83; açık f3'lü 374 / 59; havuz 880 / 142; grup olay/risk 25/165, 31/258, 86/457 | 506 / 83; 374 / 59; 880 / 142 (165 arz: H99 97, OOT_OPEN 68); 25/165, 31/258, 86/457 | tuttu |
| fold planları | clip ve real: 87 fold, v0 ile aynı ticker kümesi; pooled 87'nin hepsini içerir; yakın dönem 78 fold, 22 blok, üçünde aynı ticker'lar | clip ve real 87 fold, v0'ınkiyle aynı ticker'lar (sıra dahil); pooled 97 fold (beklenen, ölçülmemişti), 87'nin hepsini içerir; yakın dönem 78 fold, 22 blok, dört koşuda aynı ticker'lar; sızıntı (max eğitim seansı ≥ T) 0 | tuttu |
| v0 karşılaştırıcısı | ledger sha pinli; 87-fold ortalama RPS 0.1503 (\|Δ\| ≤ 1e-9) | `976b4dcea981…`; ledger'daki S_1..S_10'dan 0.1503154629, Faz 1B günlük değerine \|Δ\| = 2.8e-17 | tuttu |
| bayt-eşitlik | v0, `@INF`, PB tavan ledger'ları ve 16 eski altın dosya bayt-eşit; `gen_golden --check` yeşil | Faz 1A/1B/4/5 altın dizinleri (9 + 21 + 5 + 4 dosya) 6a16c16'dan beri değişmedi ve yeniden koşularda bayt-eşit (`test_faz1b_backtest.py::test_backtest_byte_identical_to_faz1b_golden` vb., tam paket yeşil); `app/parity/golden/`'da değişen yalnız `MANIFEST.json` (T2); `gen_golden --check` {"checked": 25, "different": []}; `test.sh` U46 yeşil | tuttu |

## 3. Yakın dönem birincil hücreleri ve §6.2 konumu (T6)

Kural (commit A'da sabit; `borsai/report_faz7.py: OPERATIONAL_RULES_FAZ7`, `borsai/backtest.py: near_era_label`; J13, J14):
aday ledger'ı Faz 1B'nin v0 altın ledger'ıyla (yeniden koşulmaz) ticker ile eşleşir, ikisi de FIT_OK, ilk işlem ≥ 2024-01-01;
aralık C7 (ilk işlem ayı blokları, 4000 tekrar, `random.Random(20260921)`). Etiket: alt > 0 → "bozuyor"; üst ≤ +0.010 →
"tolerans içinde"; diğer → "belirsiz". Konum: nokta §6.2 aralığının (kapalı) içinde / altında ("beklentiden çok iyi") /
üstünde.

| Aday | n (ay) | aday RPS | v0 RPS | fark | %95 aralık | aday iyi / v0 iyi / eşit | Etiket | §6.2 beklenen | §6.2 aralık | §6.2 beklenen etiket | Konum |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | 78 (22) | 0.1427 | 0.1438 | −0.0011 | [−0.0066, +0.0049] | 46 / 32 / 0 | **tolerans içinde** | −0.003 | [−0.010, +0.005] | tolerans içinde | **aralık içinde** |
| `ceiling_hazard_v1_real` | 78 (22) | 0.1542 | 0.1438 | +0.0104 | [+0.0028, +0.0183] | 24 / 54 / 0 | **bozuyor** | −0.004 | [−0.015, +0.008] | tolerans içinde ya da belirsiz | **üstünde** |
| `ceiling_hazard_v1_pooled` | 78 (22) | 0.1728 | 0.1438 | +0.0289 | [+0.0089, +0.0518] | 25 / 53 / 0 | **bozuyor** | +0.002 | [−0.010, +0.015] | **belirsiz** olası; "bozuyor" beklenmiyor | **üstünde** |
| `v1_pooled` − `base_km_expanding` (§6.2 ikincil) | 78 (22) | 0.1728 | 0.1981 | −0.0253 | [−0.0386, −0.0099] | 45 / 33 / 0 | — | −0.05 | [−0.08, −0.02] | — | **aralık içinde** |

Hiçbir hücrede bit-eşit ya da \|fark\| ≤ 1e-12 eşitlik yok. Kural satırı `ceiling_hazard_v1_pooled@INF` − v0 (aday değil):
+0.0547 [+0.0287, +0.0806], n = 78.

§6.2 ile yan yana okuma:

- `v1_clip`: nokta ve etiket beklentiyle aynı (test arzı kırpılan fold 20/87; eğitim kümelerinde de kırpma var).
- `v1_real`: nokta aralığın üst ucunun 0.0024 üstünde; etiket "bozuyor" (beklenen "tolerans içinde ya da belirsiz"). §6.2 yönü
  belirsiz saymıştı; gerçekleşen yön deflasyonun yakın dönemi kötüleştirmesi.
- `v1_pooled`: nokta aralığın üst ucunun 0.0139 üstünde; "bozuyor" beklenmiyordu. §6.4 (b) gereği proje sahibine cevap "evet,
  bozuyor"; aday yine dondurulur, k3 ile birincil olamaz.
- `v1_pooled − KM`: aralık içinde, üst ucuna yakın (v0'ın aynı fold'larda KM'ye karşı farkı 0.1438 − 0.1981 = −0.0543; havuzlu
  aday bunun yaklaşık yarısını koruyor).

## 4. İlan edilmiş ikinciller (§5.1; aynı 78 fold)

| Aday | Karşılaştırılan | Metrik | aday | karş. | fark | %95 aralık | aday iyi / karş. iyi / eşit |
|---|---|---|---|---|---|---|---|
| `v1_clip` | `base_km_expanding` | RPS | 0.1427 | 0.1981 | −0.0554 | [−0.0826, −0.0283] | 52 / 26 / 0 |
| `v1_clip` | `ceiling_hazard_v0@INF` | RPS | 0.1427 | 0.1943 | −0.0516 | [−0.0765, −0.0265] | 54 / 24 / 0 |
| `v1_clip` | `ceiling_hazard_v0` | Brier k = 1 | 0.1289 | 0.1294 | −0.0004 | [−0.0023, +0.0016] | 49 / 29 / 0 |
| `v1_clip` | `ceiling_hazard_v0` | Brier k = 3 | 0.1500 | 0.1538 | −0.0038 | [−0.0142, +0.0037] | 53 / 25 / 0 |
| `v1_clip` | `ceiling_hazard_v0` | Brier k = 5 | 0.1804 | 0.1780 | +0.0024 | [−0.0087, +0.0177] | 56 / 22 / 0 |
| `v1_clip` | `ceiling_hazard_v0` | Brier k = 10 | 0.0932 | 0.0992 | −0.0060 | [−0.0222, +0.0049] | 49 / 29 / 0 |
| `v1_real` | `base_km_expanding` | RPS | 0.1542 | 0.1981 | −0.0439 | [−0.0692, −0.0170] | 47 / 31 / 0 |
| `v1_real` | `ceiling_hazard_v0@INF` | RPS | 0.1542 | 0.1943 | −0.0401 | [−0.0634, −0.0146] | 50 / 28 / 0 |
| `v1_real` | `ceiling_hazard_v0` | Brier k = 1 | 0.1343 | 0.1294 | +0.0049 | [−0.0003, +0.0104] | 57 / 21 / 0 |
| `v1_real` | `ceiling_hazard_v0` | Brier k = 3 | 0.1609 | 0.1538 | +0.0070 | [−0.0072, +0.0206] | 49 / 29 / 0 |
| `v1_real` | `ceiling_hazard_v0` | Brier k = 5 | 0.1907 | 0.1780 | +0.0127 | [−0.0015, +0.0272] | 31 / 47 / 0 |
| `v1_real` | `ceiling_hazard_v0` | Brier k = 10 | 0.1069 | 0.0992 | +0.0077 | [−0.0106, +0.0254] | 18 / 60 / 0 |
| `v1_pooled` | `base_km_expanding` | RPS | 0.1728 | 0.1981 | −0.0253 | [−0.0386, −0.0099] | 45 / 33 / 0 |
| `v1_pooled` | `ceiling_hazard_v0@INF` | RPS | 0.1728 | 0.1943 | −0.0216 | [−0.0347, −0.0062] | 44 / 34 / 0 |
| `v1_pooled` | `ceiling_hazard_v0` | Brier k = 1 | 0.1528 | 0.1294 | +0.0235 | [+0.0059, +0.0435] | 37 / 41 / 0 |
| `v1_pooled` | `ceiling_hazard_v0` | Brier k = 3 | 0.1998 | 0.1538 | +0.0459 | [+0.0169, +0.0854] | 21 / 57 / 0 |
| `v1_pooled` | `ceiling_hazard_v0` | Brier k = 5 | 0.2180 | 0.1780 | +0.0400 | [+0.0096, +0.0738] | 25 / 53 / 0 |
| `v1_pooled` | `ceiling_hazard_v0` | Brier k = 10 | 0.1047 | 0.0992 | +0.0056 | [−0.0199, +0.0327] | 17 / 61 / 0 |

Kural satırı (bilgi): `v1_pooled@INF` − `base_km_expanding` +0.0004 [−0.0058, +0.0063]; − `ceiling_hazard_v0@INF` +0.0042
[−0.0008, +0.0093]; Brier k = 1 / 3 / 5 / 10 − v0: +0.0329, +0.0826, +0.0707, +0.0169 (tam tablo MODELS.md Faz 7 bölümünde).

Okuma (backtest dili, MODELS.md'deki gibi): üç aday da yakın dönemde KM'ye ve `ceiling_hazard_v0@INF`'e karşı aralığı 0'ın
altında; v0'a karşı Brier'de `v1_clip`'in dört aralığı 0'ı içeriyor, `v1_pooled`'ın k = 1, 3, 5 aralıkları 0'ın üstünde.

## 5. Merdiven (§5.4; yalnız pay, aynı 78 fold)

- kırpmanın payı (`v1_clip` − `ceiling_hazard_v0`): fark −0.0011 [−0.0066, +0.0049], n = 78 (22 ay).
- deflasyonun payı (`v1_real` − `v1_clip`): fark +0.0115 [+0.0045, +0.0190], n = 78 (22 ay).
- havuz + rejimin payı (`v1_pooled` − `v1_real`): fark +0.0185 [+0.0005, +0.0389], n = 78 (22 ay).

## 6. Keşif (hüküm yok)

- Bütün eşleşik fold'lar (87; aday − v0): `v1_clip` −0.0024 [−0.0079, +0.0036]; `v1_real` +0.0081 [+0.0006, +0.0159];
  `v1_pooled` +0.0270 [+0.0076, +0.0486]; `v1_pooled@INF` +0.0520 [+0.0268, +0.0761]. 2023 fold'ları (9, 2 ay; aralık yok;
  sırasıyla clip, real, pooled, @INF): −0.0140, −0.0122, +0.0103, +0.0285.
- Koşu başına ortalama RPS (günlük satırı): `v1_clip` 0.1479 (87 fold), `v1_real` 0.1584 (87), `v1_pooled` 0.1729 (97),
  `v1_pooled@INF` 0.1982 (97); v0 0.1503 (87).
- Havuz planının KM kuralları (aynı fold'ların aynı eğitim kümelerinden): `v1_pooled` − `base_km_expanding__pooled` yakın dönem
  −0.0201 [−0.0365, −0.0013], 97 fold −0.0217 [−0.0395, −0.0021], 2023'ün 19 fold'u −0.0280; `v1_pooled` −
  `base_km_last10__pooled` yakın dönem −0.0210 [−0.0527, +0.0151]; `v1_pooled@INF` − `base_km_expanding__pooled` yakın dönem
  +0.0057 [−0.0064, +0.0166].
- [ÇIKARIM, test edilmedi] H99'un 97 f3'lü arzında ln(f1) ile ilk işlem tarihi arasındaki korelasyon +0.29, ln(f1r) ile −0.15;
  nihai fit'te boyut katsayısı 0.463'ten (f1) 0.265'e (f1r) iniyor. Nominal büyüklük H99 içinde dönem bilgisi de taşıyor;
  deflasyon bu bileşeni çıkarıyor. Havuzlu adayda f3'ün eğitim p95'i 8.33'ten 18.02'ye çıkıyor (eski dönemin talep katları) ve
  rejim terimi δ = +0.911 (eski rejimde tavan serisi daha kısa). Bunlar farkların olası kaynaklarıdır; hüküm değildir.

## 7. Fold özeti

- `v1_clip`: 87 fold, FIT_OK 87; seçilen λ 0.1: 18, 1: 12, 3: 21, 10: 36; test arzı kırpılan fold 20.
- `v1_real`: 87 fold, FIT_OK 87; seçilen λ 0.1: 20, 1: 10, 3: 21, 10: 36; test arzı kırpılan fold 20.
- `v1_pooled`: 97 fold, FIT_OK 97; seçilen λ 10: 97; test arzı kırpılan fold 7; δ > 0 97/97; f3 filtre dışlaması olan fold 44
  (J10; eğitimdeki açık küme arzı 65 ya da 68).
- `v1_pooled@INF`: 97 fold, FIT_OK 97; λ INF 97; δ > 0 97/97; plan `v1_pooled`'ınkiyle aynı (44 fold dışlamalı).
- Yakınsamayan λ adayı 0; bütün ledger'larda max(eğitim seansı) < T; pooled test arzlarında r = 0 (97/97).
- Resmi koşu 65 sn (9 süreç), `--suite faz7 --write-golden --context faz7_golden`.

## 8. İç tutarlılık denetimleri (sonuçlar beklenti aralığının üstünde çıktığı için; kod değişmedi)

`v1_real` ve `v1_pooled`'ın §6.2 aralığının üstüne düşmesi bir uygulama hatasından mı geliyor? Merdiven basamakları birbirine
yalnız bir parça eklediği için bu doğrudan sınanabildi; ikisi de commit B'de kalıcı test oldu (`tests/test_faz7_golden.py`):

- **D1 — deflasyon tek fark** (`test_deflator_is_the_only_difference_between_clip_and_real`): `v1_real`'in fold hesabı (aynı
  tarif, ızgara, iç CV) f1r := f1 (TÜFE sabit 100) ile koşulunca 87 fold'da seçilen λ'lar ve S_1..S_10 `v1_clip` altın ledger'ıyla
  metin olarak aynı (maks \|ΔS\| = 0).
- **D2 — havuz planı ve v2 yolu** (`test_pooled_plan_on_h99_rows_reproduces_real`): `PLAN_CEILING_POOLED` + `training_table_v2`
  yalnız H99 satırlarıyla, rejimsiz ve `v1_real` özellikleriyle: fold'lar PLAN_CEILING'in skorlanabilir 87'si (aynı eğitim
  kümesi, PP sha'sı, max seans), ledger `v1_real` altın ledger'ıyla λ ve S'de aynı.
- Ek olarak: `v1_real` ve `v1_pooled` ledger'larındaki test arzının TÜFE ayı T'nin m − 2'si ve endeksi dosyadaki değer
  (184/184 satır), yayım T'den önce; §11-6 gerçek veride: `v1_pooled` λ = 1e9 → ‖β‖ ≤ 1e-6, (γ, δ) λ = INF Newton çözümüne
  \|Δ\| ≤ 1e-6 ve `@INF` önizlemesine \|Δ\| ≤ 1e-12.

Bu yüzden (b) ve (c) basamaklarının payları deflatörün ve açık küme satırları + rejim teriminin kendisinden gelir; kalan risk
şartnamenin kendisindeki bir tanım hatasıdır ve bunu sıradaki bağımsız yeniden üretim sınar.

## 9. Görev kurallarına göre notlar ve sapmalar

- **J16 istisnasının beşinci testi.** A'da proje sahibi kararıyla (2026-09-25, H22 kalıbı) dört teste yazılan varyant sayacı
  istisnası, B'nin iki H99 günlük satırıyla (`v1_clip`, `v1_real`) kırmızı olan beşinci bir testi kapsamıyordu:
  `tests/test_faz5_live.py::test_committed_post_d1_scores_match_recomputation` (commit'li `scores_post_d1.json` kartında
  `n_variants_same_data` = 20, yeniden hesapta 22). Aynı kalıp uygulandı: istisna yalnız `scores.json` ve `scores_post_d1.json`
  8e3a623'teki halleriyle bayt-eşitken ve fark tam olarak günlükteki Faz 7 varyant sayısı (2) kadarken; yeniden üretilen dosya
  tam karşılaştırılır (`tests/faz7_support.py: scores_post_d1_is_pre_faz7`). **SPEC_DEVIATIONS J16'nın test listesine bu satır
  eklenmelidir**; `docs/SPEC_DEVIATIONS.md` B ve R commit yollarında olmadığı için kayıt burada.
- Havuzlu iki önizleme (`…pooled_final_fit_preview.json`, `…pooled@INF_final_fit_preview.json`) `training.tickers`'ta 165 eğitim
  arzını taşır (68'i açık küme; v0'ın donmuş JSON'u da 97 eğitim arzını listeler). Kasa kodu hiçbir yeni dosyada yok (tarama:
  altın dizinin 12 dosyası, MODELS.md, günlük farkı, test dosyası: 0); bülten adı kalıbı yok.
- Pooled planında KM kuralları ayrı günlük satırı yazmadı; sha'ları ve metrikleri `v1_pooled` satırının `comparator_ledgers`
  alanında (J12).
- Proje sahibine soru: yok (bu adımda yeni karar gerekmedi).

## 10. Nihai fit önizlemesi (dondurulmadı; `models/`'e yazılmadı)

`backtest.final_fit_v1` (dondurmanın kullanacağı fonksiyon) bütün eğitim kümesinde; dosyalar `tests/reference/macos_golden_faz7/`
altında; yeniden koşu `created_at`, `code_version`, `runtime` dışında aynı (testli) ve stdlib `predict_hazard.predict` ile
eğitim arzlarının hepsinde \|Δ\| ≤ 1e-12 (§11-11, testli).

| model_id | λ | γ (g1, g2, g3) | β | δ (rejim) | arz / PP satırı / olay | kırpma [p05, p95] (ham) | reclose r_a / r_b | Newton |
|---|---|---|---|---|---|---|---|---|
| `v1_clip` | 10 | −1.8191, −2.1417, −0.9953 | f1 +0.4634, f2 −0.1795, f3 −0.5611 | — | 97 / 506 / 83 | f1 [5.214e+08, 4.88799e+09] TL; f2 [11.1619, 35.1166]; f3 [1.14871, 8.332] | 0.0146 / 0.1430 | 5 yineleme, max\|∇\| 1.8e-14 |
| `v1_real` | 10 | −1.7659, −2.1292, −1.0813 | f1r +0.2645, f2 −0.2530, f3 −0.5267 | — | 97 / 506 / 83 | f1r [7.31271e+08, 6.09189e+09] 2025 TL; f2, f3 aynı | 0.0146 / 0.1430 | 5, 1.1e-14 |
| `v1_pooled` | 10 | −2.1155, −2.2445, −1.5441 | f1r +0.2265, f2 −0.1727, f3 −0.4959 | +0.9111 | 165 / 880 / 142 (H99 97, açık 68) | f1r [5.65833e+08, 6.23722e+09]; f2 [15.0127, 37.543]; f3 [1.1616, 18.02] | 0.0480 / 0.1088 | 5, 1.5e-14 |
| `v1_pooled@INF` | INF | −1.7832, −2.0499, −1.5279 | — | +0.2277 | 165 / 880 / 142 | — | 0.0480 / 0.1088 | 4, 1.4e-13 |

λ iç CV skorları (ortalama PP satırı NLL; seçilen **kalın**): `v1_clip` 0.1: 0.40540, 1: 0.40517, 3: 0.40480, **10: 0.40458**,
30: 0.40718, 100: 0.41764, 300: 0.43048, 1000: 0.43950, INF: 0.44482; `v1_real` 0.1: 0.41510, 1: 0.41489, 3: 0.41455,
**10: 0.41412**, 30: 0.41552, 100: 0.42288, 300: 0.43284, 1000: 0.44027, INF: 0.44482; `v1_pooled` 0.1: 0.42367, 1: 0.42361,
3: 0.42352, **10: 0.42337**, 30: 0.42384, 100: 0.42723, 300: 0.43313, 1000: 0.43844, INF: 0.44210. Nihai fit'lerde f3 filtre
modu NOT_SPECIFIED, filtre dışlaması yok (J10). `@INF` önizlemesi β taşımaz; canlı girdide r = 0 ile S'i `ceiling_hazard_v0@INF`'ten
farklıdır (testli).

## 11. TÜFE dosyası özeti

- **Dosya:** `data/raw/tuik/tufe_genel_2025_100.csv`, sha256 `3d61cbcf…a567b`; sütunlar `month, index, release_date,
  bulletin_id, source_url, source_sha256`; **82 ay, 2019-11…2026-08**, kesintisiz; 2025 ortalaması 100.0000.
- **Kaynak:** TÜİK veri portalı, "Tüketici Fiyat Endeksi, Ağustos 2026" bülteni (sayı 58290, yayım 2026-09-03 10:00), tablo
  "Tüketici fiyat endeksi ve değişim oranları" [2025=100] — ham xls `data/raw/tuik/tufe_degisim_oranlari_bulten_58290.xls`
  (58368 bayt, sha256 `6f7ee8e4…ff86`; indirme 2026-09-25T18:22:51Z; bağlantı ve HTTP başlıkları `.source.json`'da). Komut satırı
  istemcisi 403 aldığı için dosya bülten sayfasının kendi oturumunda (yerleşik tarayıcı) okundu; baytlar değiştirilmedi.
- **Yayım günleri:** her ayın kendi bülteni (82 sayfa, `data/raw/tuik/tufe_bultenleri.csv`); 78 ay "izleyen ayın 3'ü ya da ilk iş
  günü", 4 ay bayram nedeniyle daha geç (2020-07 → 2020-08-04, 2022-04 → 2022-05-05, 2023-06 → 2023-07-05, 2026-05 →
  2026-06-05); hepsi izleyen ayın ≥ 3'ü.
- **Üretim ve pin:** `data/raw/tuik/build_tufe_csv.py` (stdlib; OLE2/BIFF8 okuyucu dahil; `--check` bayt-eşit); 2025 ortalaması ve
  tablonun aylık oranlarıyla tutarlılık (259/259 ay ±0.0051) denetimli. Pin öneklidir: `{through_month: 2026-08, prefix_sha256}`
  (J4); ay eklemek pini bozmaz, eski satır ya da temel yıl değişirse `TUFE_FILE_MISMATCH`.
- 2025 ve öncesi ayların değerleri TÜİK'in 2026'da 2025=100'e yeniden ölçeklediği seridir (o aylar yayımlandıklarında 2003=100
  idi); sabit çarpan olduğundan f1r'nin T anındaki sırası ve oranları değişmez (J3; PROVENANCE §11).
- Ağ: yalnız TÜİK veri portalı (`veriportali.tuik.gov.tr`).

## 12. Test sayıları

| Koşu | Sonuç | Süre |
|---|---|---|
| Adım 0 taban (41b7e7d) | 638 passed | 386.68 sn |
| A öncesi, deselect yok (izlenmeyen yeni `data/` dosyalarıyla) | 684 passed, 3 failed (üçü de yalnız izlenmeyen `data/` yüzünden temizlik bekçisi) | 657.63 sn |
| A öncesi, üç temizlik bekçisi deselect (görev adım 6) | 684 passed, 3 deselected | 714.11 sn |
| A sonrası (commit'li, deselect yok) | 687 passed | 642.54 sn |
| B öncesi 1 (resmi koşu + altın + MODELS.md + yeni testler) | 703 passed, 1 failed (§9: J16'nın beşinci testi) | 478.17 sn |
| B öncesi 2 (istisna uygulandı) | 704 passed | 491.71 sn |
| B sonrası (commit'li) | 704 passed | 507.36 sn |

`bash app/scripts/test.sh`: adım 0 yeşil (cargo 94, npm 222, parity 4, U46); T2 pininden sonra yeşil (47 sn); B öncesi
yeşil (cargo 94, npm 222, parity 4, U46; 38 sn). `gen_golden --check`: adım 0 25/0; A'da pin öncesi yalnız MANIFEST farklı,
pin sonrası 25/0; R anında (HEAD 70b67d1) 25/0. Faz 7 testlerinin sayısı: A'da 48 (tufe 9, tablo v2 11, model 19, backtest 9) + 1 T4
mutasyon testi (`test_cohort_guard_t4_mutation`; 638 + 49 = 687); B'de +17 (`test_faz7_golden.py`, ≈ 45 sn; 687 + 17 = 704).
Ham son satırlar: `docs/faz7/ekler/impl_test_runs.txt`.

## 13. Hijyen ve maruziyet

- Kasa (SEALED, 64) üyelerinin hiçbir dosyası açılmadı; kasa hakkında yalnız kohort listesi ve bekçi fonksiyonu kullanıldı; hiçbir
  çıktıya kasa kodu yazılmadı (bekçi mesajları ve ölçüm betiği yalnız sayı basar; pytest'in assert içgözlemi kod listesi basmasın
  diye listeler yerel değişkende). `docs/faz6/dogrulama/EXPOSURE.md` §3 ve Codex `exposure_log`'ları okunmadı.
- **J18 maruziyet notu (A'dan):** `data/outcomes/COMPLETENESS.csv`'deki önceden var olan bir satır bir kasa üyesinin 2026 kurumsal
  işlemini gösteriyor (kim olduğu yazılmadı); (C) tasarımı için bilinmeli. **Ek (R):** J18'in metnindeki tarih ve neden, tamlık
  dosyasında o satırı tek başına belirleyebiliyor; bu rapor ve ölçüm çıktısı onları tekrarlamaz. J18'in bu ayrıntısının bir
  sonraki SPEC_DEVIATIONS düzenlemesinde genelleştirilmesi önerilir (SPEC_DEVIATIONS bu görevin B/R commit yollarında değil).
- Uygulayıcı yakın dönem sonuçlarını commit A'dan sonra, B koşusunun çıktısında gördü; sonra kodda, tanımlarda ve kurallarda
  değişiklik yok (yalnız test paketine B testleri ve §9'daki istisna).
- Ağ yalnız TÜİK; push/tag/amend yok; `git add -A` kullanılmadı; paralel oturumun görev dosyaları
  (`docs/prompts/FAZ7_VERIFY_PROSPECTUS.md`, `FAZ7_CODEX_PROSPECTUS_B1..B4.md`) commit'lere girmedi.

## 14. Dondurma görevi için notlar

**Python (dondurma):**
- `models/INDEX.json` sonuna 4 giriş (`FAZ7_MODEL_IDS` sırası); `INDEX_POST_D1.json` değişmez. JSON'lar `backtest.final_fit_v1`
  ile üretilmeli (önizlemeyle `created_at`, `code_version`, `runtime` dışında bit-eşit; `tests/test_faz7_golden.py` bunu sınıyor).
  `fit.fit` v1 kimliklerini bilmiyor: `freeze.py` v1'i `final_fit_v1`'e yönlendirmeli (ya da fonksiyon `fit.py`'ye taşınmalı —
  taşınırsa kod yolu aynı kalmalı).
- Dondurma sırası tuzağı: `code_version().borsai_dirty` yalnız `borsai/`'yi izler. `freeze.py` değişikliği ayrı bir kod
  commit'inde olmalı, dondurma temiz ağaçta koşmalı (JSON'un `borsai_source_sha256`'sı o kod commit'ini gösterir).
- `freeze.build_record`: `tufe` bloğu (market20 kalıbı) ve `model_inputs["tufe_index"]` (metin; `tufe.index_for(T)` —
  `release_date < T` bekçisi dahil) ya da `tufe_refusal` kodu; `model_inputs["alloc_regime"]` **yalnız eski kohort kayıtlarında**
  (kohort satırından; canlıda anahtar yok → r = `live_value` = 0; J6). `--oot --only-missing-models` ikinci kayıtları (§7.1-3,
  §11-12: 135 üyede 4 modelli ikinci kayıt, girdiler ilk kayıtla bayt-eşit).
- TÜFE ayı eksikse (m − 2 henüz yayımlanmadıysa) kayıt ön koşulu önceden durmalı; ay ekleme = dosyaya ek satır (pin önektir).
- `scoring.py`: model başına kohort kapısı (§7.3), `oot_pre_h99_sealed` / `_all`, "modeli içeren en erken aktif kayıt"; yakın
  dönem etiketleri SCORES.md backtest panelinde ayrı satır. `scores.json` bir sonraki üretiminde H99 veri sürümündeki kartlar
  22 varyant yazacak (v2 sürümünde `v1_pooled` ve `@INF` ayrı sayılır: 2); o görev J16 istisnalarını (beş test) kendiliğinden
  devre dışı bırakır, sabit sayıları gözden geçirmeli.
- MODELS.md Faz 7 bölümüne dondurma notu `report_faz7.py` değişikliği gerektirir (Faz 5 dondurmasındaki gibi proje sahibi onayı).

**Uygulama (Rust, `app/src-tauri/crates/borsai_predict/`):**
- `params.rs`: `family = "ceiling_hazard_v1"`, `variant`, `features` ∈ {[f1, f2, f3], [f1r, f2, f3], []}, `preprocessing.winsor`
  (üç sütun), `deflator` bloğu, `regime` bloğu (`live_value`, `delta`, sütun `r_pre_equal`); Python `_check_params`'ın v1
  doğrulamalarının karşılığı.
- `features.rs`/`hazard.rs`: f1r = `real_size(f1, tufe_index)` = f1 / (endeks / 100), **Decimal 60 hane, ROUND_HALF_EVEN**, sonra
  binary64 (`dec.rs`'de `div_round` var; Python `idx / 100` ve ardından bölme — iki işlem, ilki kesin). Kırpma genel: her
  winsor'lu sütun için `clipped`, `clipped_features` (liste), uyarı `FEATURE_CLIPPED_TO_TRAINING_P05_P95` {feature, value, used};
  v0'ın f3 uyarı kodu aynen. ln binary64 (`math.log` ile aynı yol). η_d = (γ_{g(d)} + δ·r) + β·z — toplama sırası stdlib'le aynı
  olmalı (bit-eşitlik).
- Yeni çıktı alanları (yalnız v1): `clipped_features`, `f1r_raw`, `tufe_index_used`, `regime_value_used`, `regime_source`
  (`LIVE_VALUE` / `ALLOC_REGIME_INPUT`). Retler: `TUFE_MISSING` (alan `tufe_index`), `TUFE_NOT_PIT` / `TUFE_FILE_MISMATCH`
  (`tufe_refusal` girdisi), `REGIME_UNKNOWN` (alan `alloc_regime`), `F3_MISSING` (miras).
- Uygulamanın etkileşimli tahmini TÜFE'yi nereden alacağı bir tasarım kararıdır: gömülü TÜFE dosyası (önek pini denetimiyle,
  `tufe.index_for` karşılığı: m − 2 ve `release_date < T`) ya da kullanıcı girdisi. Kayıtlı tahminler `model_inputs`'taki
  `tufe_index`'i kullanır.
- **Altın vektör planı:** `gen_golden.py` `PINNED_MODEL_IDS` 19 → 23 (INDEX sırası), `bit_equal_floor.json`'a 4 taban,
  `MANIFEST.json` `predict_sources_sha256` (predict_hazard.py A'da yeniden pinlendi: `6ceeeb46…`); U46: 16 eski dosya bayt-eşit
  kalmalı → yeni girdi satırları yalnız yeni modellere bağlanır (Faz 4 kalıbı). Önerilen satırlar: H99 99 arz + `tufe_index`
  (f3'süzler RET); açık kümenin 71 arzı + `tufe_index` + `alloc_regime` (pooled'ın rejim yolu; r = 1 satırları); canlı satırlar
  (anahtarsız, r = 0); uç durumlar: her özellik için p05/2 ve 2·p95 (kırpma uyarısı), `tufe_index` eksik / sayı değil / ≤ 0,
  `tufe_refusal` = `TUFE_NOT_PIT` / `TUFE_FILE_MISMATCH`, bilinmeyen `alloc_regime` etiketi; `@INF` için özelliksiz satırlar.
  Kasa üyelerinin girdileri altın vektörlere **girmez** (kasa açılmadan).

**Denetim (Fable yeniden üretimi):** dört ledger (sütunlar J11) ve havuz KM ledger'ları; önizlemeler; yakın dönem hücreleri ve
etiketleri; `tests/test_faz7_golden.py`'nin D1/D2 denetimleri bağımsız üretimde de kurulabilir (merdiven basamaklarının
yalnız bir parça farklı olduğu).

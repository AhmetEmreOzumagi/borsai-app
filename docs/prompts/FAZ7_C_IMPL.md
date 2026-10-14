# TASK_ID: BORSAI_FAZ7_C_IMPL_20260927

Model: Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ yok. push/tag/amend yok.

## Bağlam
- **Şartname:** `docs/specs_faz7_c/SPEC_C_V0.md` (`4fe4e51`, Fable; push kanıtlı).
- **Bağlayıcı kararlar:** `docs/specs_faz7_c/KARARLAR_C.md`. Çelişkide KARARLAR_C geçerli. Bu görev dosyayı commit eder, içeriğini değiştirmez.
- **Üç aday:** L2 lojistik, D5 ve D10 için yalnız p_up başlığı, V1.6 C ızgarası:
  - `fall_d10_v0_h99`: özellikler f1r, ln f3, ek satış bayrağı; eğitim H99 (94).
  - `fall_d10_v0_pooled`: aynı özellikler; eğitim H99 + açık küme (161).
  - `fall_d10_v0_addsale`: yalnız ek satış bayrağı; eğitim havuz (165).
  - Kural satırı `fall_d10_v0_pooled@ZERO` (havuz oranı).
- **Hedef:** y4 = 1 − Y_D10, yani D10 kapanışı ≤ arz fiyatı; ikincil y3 = 1 − Y_D5. Model p_up verir; düşme olasılığı = 1 − p_up.
- **Yol:** bu görev (A kod ve kurallar → B backtest) → Fable sıfırdan yeniden üretim → dondurma (INDEX'e 4 giriş) → eski kohort ek kayıtları (v1 ve (C) birlikte) ve model başına kapı → kasa açılışı (tek sefer).
- **Kalıp:** `docs/prompts/FAZ7_HAZARD_V1_IMPL.md` ve onun raporu `docs/faz7/IMPL_RAPOR.md`. Aynı A/B/R sırası, aynı kurallar.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.**
- **Hijyen:**
  - kasa (SEALED, 64) üyelerinin hiçbir dosyası açılmaz; eğitim tablolarında kasa kodu yoktur;
  - `docs/faz6/dogrulama/EXPOSURE.md`, `docs/faz7/prospectus/EXPOSURE.md` ve Codex `exposure_log`'ları okunmaz;
  - hangi kodun kasada olduğu yazılmaz ve ekrana basılmaz. Kohort dosyası yalnız betikle ve `vault != SEALED` süzgeciyle okunur; ilk satırları bile basılmaz.

## Orkestratörün ölçtükleri
- Olaylar (`data/training_table_v2.csv`): y4 H99 29/99, açık 13/71.
- Ek satış bayrağı: 170 arzda 19 arz 1; bunların 12'si düştü. H99'da 4/6, açık kümede 8/13.
- Önceki dondurma (`66adbca`, `ecd8973`) sonrası: INDEX 23 giriş; uygulama `build_embed` testleri INDEX'in sonundaki kayıtları `ignored_model_ids` olarak listeliyor. Yeni 4 giriş bu listeyi ve INDEX sha pinlerini dondurma görevinde yeniden etkileyecek. **Bu görevde INDEX değişmez**; o yüzden bu görevin `app/` etkisi yalnız T2 pinidir (aşağıda).

## Görev kararları (SPEC_DEVIATIONS'a yeni bölüm K olarak)
- **T1 · kapsam:** şartname §8'in `borsai/` ve `docs/` satırları: features, preprocess, specs, fit, data, backtest, predict (ya da `predict_fall.py`), scoring (yalnız hücre tanımları ve SCORES.md backtest panel satırı; skorlar yeniden üretilmez), `report_faz7c.py` ve MODELS.md bölümü.
  - **Bu görevde YOK:** `models/` ve `INDEX.json` (dondurma görevi); `app/` Rust (EK3); eski kohort ek kayıtları ve model başına kapı (sonraki görev); `registry/`; `scores/`.
- **T2 · uygulama pini:** pinli bir kaynak (`app/parity/golden/MANIFEST.json` `predict_sources_sha256`: features, horizons, predict, predict_hazard, predict_market20, predict_path, predict_pb, survival) değişirse yalnız o alan yeniden pinlenir.
  - Koşul: bütün altın vektörler ve 16 eski dosya bayt-eşit (`gen_golden --check` 25/0).
  - Vektör değişirse DUR.
  - Yeni kod mümkünse ayrı modülde (`predict_fall.py`) olsun, pin değişmesin.
- **T3 · iki commit:**
  - A = kod, kurallar, sentetik ve birim testler, SPEC_DEVIATIONS K, KARARLAR_C. **A'da hiçbir walk-forward skoru yok.**
  - B = backtest koşuları, altın ledger'lar `tests/reference/macos_golden_faz7c/` (+ MANIFEST, SHA256SUMS), günlük satırları, MODELS.md bölümü, nihai fit önizlemeleri (`models/`'e yazılmaz).
- **T4 · keşif varyantları:** şartname §8 ve KARARLAR_C'ye göre `docs/specs_faz7_c/ekler/denenenler.csv`'nin 2 054 satırı günlüğe `kind: exploration` satırları olarak eklenir. Dosya sha'sı ve kaynak yolu satırlarda bulunur. **Bu B'de yapılır**; A'da günlük değişmez.
  - Kart `n_variants_same_data` sayaçları buna göre değişir. Hangi veri sürümüne sayıldığını şartnameye göre sen belirle ve SPEC_DEVIATIONS K'ya yaz.
  - Var olan kartlarda sayaç değişecekse, J16/J30 kalıbında sınırlı ve koşullu bir istisna yazılabilir: yalnız `scores.json` bayt-eşitken, fark tam sayıya eşitken. Yeni bir gevşetme değil, aynı kalıp.
- **T5 · karar etiketi A'da kodlanır:** §5.1 kuralı, δ = 0.008 sabiti (`NEAR_ERA_TOLERANCE_FALL`), sentetik test §11-8 ve eşik mutasyonu kırmızı. Sonuç B'de.
- **T6 · §6 karşılaştırması:** B raporunda her yakın dönem hücresi §6.2 beklentisiyle yan yana: "aralık içinde" / "altında" / "üstünde". Nokta §6.2 aralığının altındaysa "beklentiden çok iyi" diye işaretle; sıradaki adım zaten Fable'ın yeniden üretimi.

## Beklenen sayılar (şartname §11; tutmazsa commit etme, DUR)

| Denetim | Beklenen |
|---|---|
| ek satış bayrağı | "0" → 0; "35000000" → 1; boş → `REFUSED_ADDITIONAL_SALE_MISSING`; "-1" → `INPUT_NEGATIVE`; bayrak = 1: H99 6, açık 13 |
| eğitim kümeleri | `H99_F3_AS_PRESENT` 94 (D10 olay 26, D5 18); `H99_PLUS_OOT_OPEN_F3_AS_PRESENT` 161 (39, 29); `H99_PLUS_OOT_OPEN_AS_PRESENT` 165 (40, 30) |
| tablolar | `training_table.csv`, `training_table_v2.csv`, `data_version*.json` sha'ları değişmez; kasa kodu `data/`'da 0 |
| f1r | eğitim satırlarında `ceiling_hazard_v1_real`'in f1r ham değerleriyle bit-eşit |
| `@ZERO` | D10 p_up = 1 − 39/161, D5 = 1 − 29/161 (Fraction, bit-eşit) |
| fold planları | `PLAN_FALL_H99` ve `PLAN_FALL_POOLED` 94 test arzı; yakın dönem 75 fold, 22 ay bloğu, iki planda aynı ticker'lar; `PLAN_FALL_ADDSALE` 95 test arzı; her fold'da eğitim D10 seansı < T |
| karşılaştırıcılar | `base_rate` ve `v1_5_h99` ledger sha'ları pinli; V1.5 D10 Brier 0.1883 (81 fold) ledger'dan yeniden üretilir (\|Δ\| ≤ 1e-9) |
| bayt-eşitlik | V1.5/V1.6/PB/market20/v0/v1 altın ledger'ları ve 16 eski altın dosya bayt-eşit; `gen_golden --check` 25/0 |
| günlük (B) | backtest satırlarında `spec_sha256` = SPEC_C_V0.md sha'sı; `exploration` satırları 2 054 ve `denenenler.csv` sha'sı |

## İzinli izlenmeyen (adım 0)
- bu görev dosyası;
- `docs/specs_faz7_c/KARARLAR_C.md`;
- `docs/prompts/FAZ7_FABLE_APP_EK3_SPEC.md` ve `docs/app/` altındaki yeni dosyalar (paralel Fable oturumu).

Başka bir şey varsa DUR.

## Paralel
Bir Fable oturumu `docs/prompts/FAZ7_FABLE_APP_EK3_SPEC.md`'yi koşuyor. Yalnız `docs/app/` altına yeni dosya yazar ve kendi yollarıyla commit eder. Onun dosyalarını commit'ine koyma. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.

ÖNCE OKU:
- CLAUDE.md
- docs/specs_faz7_c/SPEC_C_V0.md (tamamı), KARARLAR_C.md, KESIF.md (§1 ve sade özet)
- docs/specs/SPEC_V1_6.md (Logit yolu), docs/specs/SPEC_SCORING.md
- docs/specs_faz7/SPEC_HAZARD_V1.md §3.2 (f1r), docs/SPEC_DEVIATIONS.md J (özellikle J16, J23–J31)
- docs/prompts/FAZ7_HAZARD_V1_IMPL.md ve docs/faz7/IMPL_RAPOR.md (kalıp), docs/faz7/FREEZE_RAPOR.md
- borsai/features.py, preprocess.py, fit.py, specs.py, data.py, backtest.py, predict.py, tufe.py, scoring.py, report_faz7.py, registry.py (`V15_FIELDS`)
- tests/test_experiment_log.py, tests/test_outcome_guard.py, tests/faz7_support.py, app/parity/gen_golden.py

## Adımlar
0. **Taban.**
   - HEAD, `ecd8973`'ün ya da push kanıtı commit'inin torunu. İzinli izlenmeyenler dışında temiz.
   - Tam `.venv/bin/pytest -q`, `bash app/scripts/test.sh`, `gen_golden --check` (25/0).
   - Sayılar `docs/faz7c/ekler/impl_test_runs.txt`'ye.
1. **Özellik ve tarif:** `additional_sale_flag`, `FALL_V0_RECIPE`, `FALL_V0_ADDSALE_RECIPE` (winsor ve log yalnız f1r, f3); eski tarifler bayt-eşit. Testler §11-1, 3.
2. **specs ve data:** 4 kimlik, `FAZ7C_MODEL_IDS`, eğitim kümeleri, üç plan, `SPEC_DOCUMENTS_FAZ7C` (SPEC_C_V0 + KARARLAR_C). Testler §11-2, 6.
3. **fit ve predict:** Ridge'siz Logit yolu (`_fit_logit` değişmez); stdlib tahmin (`predict_fall.py` önerilir), §9 retleri, `@ZERO` sabit başlık. Testler §11-5, 9 (sentetik; donmuş JSON yok).
4. **backtest altyapısı ve kurallar:** yakın dönem hücresi `pooled − h99` (D10 Brier), ikinciller (§5.1), T5 etiketi, `report_faz7c.py` kural metni sabitlerden. Testler §11-7, 8, 13.
5. **scoring:** üç aday için birincil ve ikincil hücre tanımları (canlı ve zaman-dışı); kasa anahtarı `oot_pre_h99_sealed` bu görevde yok. Sentetik testler.
6. **T2 pini** (gerekiyorsa); 25 dosyanın bayt-eşitliğini göster.
7. **Commit A.**
   - Tam pytest + test.sh yeşil.
   - Temizlik bekçileri yalnız bu görevin yeni dosyaları yüzünden kırmızıysa: deselect → commit → deselect'siz tam koşu.
   - Eski kohort bekçileri asla deselect edilmez.
8. **B:**
   - üç adayın ve kural satırının walk-forward koşuları (günlüğe);
   - ledger'lar `tests/reference/macos_golden_faz7c/`;
   - yakın dönem birincil hücresi ve etiketi; ilan edilmiş ikinciller; merdiven farkları (§5.4, yalnız "payı");
   - nihai fit önizlemesi (C, katsayılar, ön işleme, n ve olay sayıları; `models/`'e yazılmaz);
   - T4 keşif satırları;
   - MODELS.md "Faz 7C: düşen arz modeli v0" bölümü (var olan bölümlere dokunma; kartta "kasa: bekliyor");
   - T6 karşılaştırması.
   
   Tam pytest + test.sh yeşil → **commit B**.
9. **Rapor** `docs/faz7c/IMPL_RAPOR.md` (commit R):
   - hash'ler;
   - beklenen sayılar tablosu (ölçülen);
   - yakın dönem hücreleri (fark [%95], n, blok, etiket; §6.2 konumu), ikinciller, merdiven;
   - nihai fit önizlemesi;
   - test sayıları;
   - dondurma görevi için notlar: INDEX 23 → 27, `app/` pin etkisi (`build_embed` `ignored_model_ids`, INDEX sha fikstürleri), eski kohort ek kayıtları;
   - EK3 için notlar: Rust'ta gerekecekler.

## Tek oturumda bitmezse
A yeşil ve commit'liyse orada dur. B yeniden koşulabilir (ledger'lar deterministik).

## Kurallar
- **Yazılabilir:**
  - `borsai/` (T1 listesi);
  - `tests/` (yeni dosyalar ve `tests/reference/macos_golden_faz7c/`; var olan testlerde yalnız T4 kalıbındaki istisna);
  - `experiments/log.jsonl` (yalnız ekleme), `docs/MODELS.md` (yalnız yeni bölüm), `docs/SPEC_DEVIATIONS.md` (K), `docs/faz7c/`;
  - `docs/specs_faz7_c/KARARLAR_C.md` (yalnız commit; içerik değişmez);
  - `app/parity/golden/MANIFEST.json` (yalnız T2 pini);
  - bu görev dosyası.
- **Salt okunur:** `models/`, `registry/`, `scores/`, `data/`, `app/` (T2 hariç), `legacy/`, `CLAUDE.md`, `docs/specs*` (KARARLAR_C commit'i hariç), `docs/app/`.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit'ler:
  ```
  git add borsai tests docs/SPEC_DEVIATIONS.md docs/specs_faz7_c/KARARLAR_C.md docs/faz7c app/parity/golden/MANIFEST.json docs/prompts/FAZ7_C_IMPL.md
  git commit -m "BORSAI_FAZ7C_A: falling-IPO model v0 code, recipes, plans, rules and tests, no backtest results" -- borsai tests docs/SPEC_DEVIATIONS.md docs/specs_faz7_c/KARARLAR_C.md docs/faz7c app/parity/golden/MANIFEST.json docs/prompts/FAZ7_C_IMPL.md
  git add tests experiments/log.jsonl docs/MODELS.md docs/faz7c
  git commit -m "BORSAI_FAZ7C_B: falling-IPO model v0 walk-forward backtest, near-era cell, golden ledgers, exploration log lines and MODELS.md section (not frozen)" -- tests experiments/log.jsonl docs/MODELS.md docs/faz7c
  git add docs/faz7c/IMPL_RAPOR.md docs/faz7c/ekler
  git commit -m "BORSAI_FAZ7C_REPORT: implementation and backtest report" -- docs/faz7c/IMPL_RAPOR.md docs/faz7c/ekler
  ```
  Değişmeyen bir yol pathspec'te hata verirse o yolu çıkar. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Oturum içinde proje sahibine bir karar sorman gerekirse, soruyu ve seçenekleri açıkça yaz. Proje sahibi cevabı orkestratöre danışarak verecek.
- Rapor Türkçe.

## Kabul kapısı
- **K1 · A:** beklenen sayılar tablosu birebir; eski ledger'lar ve 16 altın dosya bayt-eşit; etiket kuralı ve mutasyonu gösterildi; tam pytest + test.sh yeşil; A'da skor yok.
- **K2 · B:** üç aday ve kural satırı koşuldu ve günlükte; keşif satırları 2 054; yakın dönem hücresi etiketiyle; §6.2 karşılaştırması raporda; nihai fit önizlemesi var; `models/` değişmedi.
- **K3:** sıra A → B → R; yalnız izinli yollar; push yok.

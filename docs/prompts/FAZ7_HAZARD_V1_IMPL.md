# TASK_ID: BORSAI_FAZ7_HAZARD_V1_IMPL_20260925

Model: Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi.
- **Ağ:** yalnız TÜİK (tuik.gov.tr, data.tuik.gov.tr): TÜFE genel endeks serisi (2025=100) ve aylık bültenlerin yayım tarihleri. Başka ağ yok.
- push/tag/amend yok.

## Bağlam
- **Şartname:** `docs/specs_faz7/SPEC_HAZARD_V1.md` (`6a16c16`, Fable; push kanıtlı) ve **`docs/specs_faz7/KARARLAR.md`** (bağlayıcı; çelişkide KARARLAR geçerli). Üç aday:
  - `ceiling_hazard_v1_clip`: f1, f2, f3 eğitim p05/p95'ine kırpılır.
  - `ceiling_hazard_v1_real`: f1r = TÜFE ile reel büyüklük.
  - `ceiling_hazard_v1_pooled`: f1r + H99 ve açık küme havuzu + rejim terimi r.
  
  Ayrıca kural satırı `ceiling_hazard_v1_pooled@INF`.
- **Proje sahibi kararları (KARARLAR K1–K5, özet):**
  - kasa, (C) ile birlikte tek seferde açılır;
  - `pb_ceiling_v1` yok, aday bütçesi 3;
  - deflatör TÜİK TÜFE, ay kuralı T − 2;
  - uygulama seçim kuralı kabul; birincil yalnız karttaki vurgu, hiçbir model listeden kalkmaz;
  - `post_d1_hazard_v1` kasa seçiminden sonra.
- **Yol:** bu görev (A kod ve kurallar → B backtest) → Fable sıfırdan yeniden üretim → dondurma (INDEX'e 4 giriş, uygulama Rust desteği ve altın vektörler) → eski kohort ikinci kayıtları ve model başına kapı → (C) → kasa.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.**
- **Hijyen:**
  - Kasa (SEALED, 64) üyelerinin hiçbir dosyası açılmaz; `training_table_v2`'de kasa kodu yoktur.
  - `docs/faz6/dogrulama/EXPOSURE.md` §3 ve Codex `exposure_log`'ları okunmaz.
  - Hangi kodun kasada olduğu yazılmaz.

## Orkestratörün ölçtükleri
- v0 altın fold ledger'ı `tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv`: 87 fold. Şartname §5.1: yakın dönem 78 fold, 22 ay bloğu, v0 87-fold ortalama RPS 0.1503.
- Açık küme 71 üye, 68'i f3'lü. `data/outcomes_oot/*.csv`: 710 satır, hepsi OK, her üyede 10 seans.
- Uygulamanın altın MANIFEST'i (`app/parity/golden/MANIFEST.json`, `predict_sources_sha256`) şu kaynakları pinler: `features.py`, `horizons.py`, `predict.py`, `predict_hazard.py`, `predict_market20.py`, `predict_path.py`, `predict_pb.py`, `survival.py`. `predict_hazard.py` değişirse bu pin kırılır.
- `tests/test_outcome_guard.py::test_cohort_codes_appear_in_data_only_as_outcomes`, `data/` altında kohort kodlarını sonuç dizinleri dışında yasaklar; `training_table_v2.csv` açık küme kodlarını taşıyacak (§T4).

## Görev kararları (SPEC_DEVIATIONS'a yeni bölüm J olarak)
- **T1 Kapsam.** Bu görev şartname §8'in şu satırlarını uygular:
  - `data/training_table_v2.csv`, `data_version_v2.json`, `build_training_table_v2.py`;
  - `data/raw/tuik/tufe_genel_2025_100.csv` + PROVENANCE;
  - `borsai/tufe.py`, `preprocess.py`, `hazard.py`, `specs.py`, `data.py`, `backtest.py`, `predict_hazard.py`;
  - `report_faz7.py` ve MODELS.md bölümü.
  
  **Bu görevde yapılmayanlar:**
  - `models/` ve `INDEX.json` (dondurma görevi);
  - `app/` Rust değişiklikleri;
  - `freeze.py` (tufe bloğu, `--only-missing-models`);
  - `scoring.py` (model başına kapı, `oot_pre_h99_sealed/_all`);
  - `registry/`, `scores/`.
- **T2 Uygulama pini.** `predict_hazard.py` (ya da başka bir pinli kaynak) değişirse `app/parity/golden/MANIFEST.json`'ın yalnız `predict_sources_sha256` alanı yeniden pinlenir. Koşul: 19 modelin bütün altın vektörleri ve 16 eski dosya **bayt-eşit** (`gen_golden --check` 25/0). Kalıp `23b6479`. Vektör değişirse DUR.
- **T3 İki commit.** Faz 5 kalıbı (`FAZ5_POST_D1_IMPL.md`):
  - A = kod, veri, kurallar, sentetik ve birim testler, SPEC_DEVIATIONS J, KARARLAR. **A'da hiçbir walk-forward skoru ve nihai fit sonucu yoktur.**
  - B = backtest koşuları, altın ledger'lar `tests/reference/macos_golden_faz7/` (+ MANIFEST, SHA256SUMS), `experiments/log.jsonl`, MODELS.md Faz 7 bölümü, nihai fit önizlemesi (models/'e yazılmaz).
- **T4 Bekçi uyarlaması.** `test_cohort_codes_appear_in_data_only_as_outcomes`: yalnız `data/training_table_v2.csv` (tam yol) açık küme kodlarını taşıyabilir. Kasa kodları `data/`'nın hiçbir yerinde olamaz (yeni assert). Mutasyon gösterimi: v2'ye bir kasa kodu eklenince test kırmızı. Başka hiçbir bekçi gevşetilmez.
- **T5 Karar etiketi A'da kodlanır.** Etiketler şartname §5.1 kuralıyla ("bozuyor" / "tolerans içinde" / "belirsiz"), sentetik test §11-9 ile. Sonuç B'de.
- **T6 §6.2 karşılaştırması.** B raporunda her adayın yakın dönem hücresi §6.2 beklentisiyle yan yana: "aralık içinde" / "altında" / "üstünde". Nokta tahmini §6.2 aralığının altındaysa "beklentiden çok iyi" diye işaretle; Fable'ın yeniden üretimi zaten sıradaki adım.

## Beklenen sayılar (şartname §11; tutmazsa commit etme, DUR)
| Denetim | Beklenen |
|---|---|
| `training_table_v2.csv` | 170 satır; H99'un 99 satırı `training_table.csv` ile paylaşılan sütunlarda bayt-eşit; `training_table.csv` ve `data_version.json` sha'sı değişmez |
| açık 71 üyenin L dağılımı | {0: 9, 1: 11, 2: 5, 3: 4, 4: 3, 5: 8, 6: 5, 7: 6, 8: 5, 9: 6, 10: 9} |
| `alloc_regime` | tek fonksiyondan; kohort etiketiyle 135/135 eşit |
| kasa kodu | `data/` altında 0 |
| TÜFE | 2019-11'den güncele kesintisiz; 2025 ortalaması 100.00 ± 0.05; `month_for` örnekleri (§11-2); `release_date < T` 170/170 |
| PP | H99 f3'lü 506 satır / 83 olay; açık f3'lü 374 / 59; havuz 880 / 142; grup olay/risk 25/165, 31/258, 86/457 |
| fold planları | clip ve real: 87 fold, v0 ile aynı ticker kümesi; pooled: 87'nin hepsini içerir; yakın dönem 78 fold, 22 blok, üçünde aynı ticker'lar |
| v0 karşılaştırıcısı | ledger sha pinli; 87-fold ortalama RPS 0.1503 (|Δ| ≤ 1e-9) |
| bayt-eşitlik | v0, `@INF`, PB tavan ledger'ları ve 16 eski altın dosya bayt-eşit; `gen_golden --check` yeşil |

## İzinli izlenmeyen (adım 0)
- Bu görev dosyası;
- `docs/specs_faz7/KARARLAR.md`;
- `docs/prompts/FAZ7_VERIFY_PROSPECTUS.md` (paralel doğrulama görevi; repo dışında yazar);
- `docs/prompts/FAZ7_CODEX_PROSPECTUS_B1..B4.md`.

Başka bir şey varsa DUR.

## Paralel
Bir Opus oturumu `docs/prompts/FAZ7_VERIFY_PROSPECTUS.md`'yi koşuyor. O oturum repoya hiçbir şey yazmaz (çıktısı `~/Desktop/BorsAi_codex/verified_faz7/`). Onun görev dosyasını commit'e koyma.

ÖNCE OKU: CLAUDE.md; docs/specs_faz7/SPEC_HAZARD_V1.md (tamamı) ve KARARLAR.md; docs/specs/SPEC_CEILING_V0.md, SPEC_SCORING.md; docs/specs_faz6/KARARLAR.md (D4); docs/prompts/FAZ5_POST_D1_IMPL.md (kalıp); borsai/features.py, preprocess.py, hazard.py, survival.py, predict_hazard.py, specs.py, data.py, backtest.py, report_faz5.py; data/build_training_table.py; tests/test_outcome_guard.py; app/parity/gen_golden.py.

## Adımlar
0. **Taban.** HEAD `6a16c16` ya da yalnız push kanıtı commit'i eklenmiş torunu. İzinli izlenmeyenler dışında temiz. Tam `.venv/bin/pytest -q` (638), `bash app/scripts/test.sh` (yeşil), `gen_golden --check` (25/0). Sayılar `docs/faz7/ekler/impl_test_runs.txt`'ye.
1. **TÜFE:** veri dosyası (resmi kaynaktan, sha pinli, PROVENANCE satırı) + `borsai/tufe.py` + testler (§11-2).
2. **Eğitim tablosu v2** + builder + testler (§11-1) + T4 bekçi uyarlaması ve mutasyonu.
3. **Model kodu:** `preprocess` (Recipe.winsor; v0/PB bayt-eşit), `hazard` (cezasız sütunlar; λ = INF'te (γ, δ) Newton), `specs` (FAZ7 kimlikleri, pooled plan, spec belgesi sha'sı), `data.load_dataset_v2`, `predict_hazard` (f1r, rejim bloğu, genel kırpma uyarısı; v0/PB çıktıları bayt-eşit). Testler §11-3…6, 10, 11.
4. **Backtest altyapısı:** pooled plan, v0 ledger'ından eşleşik yakın dönem hücresi, T5 etiketi. Testler §11-7, 8, 9, 14.
5. **T2 pini:** gerekiyorsa MANIFEST pinini yenile; 25 dosyanın bayt-eşitliğini göster.
6. **Commit A.** Tam pytest + test.sh yeşil. Temizlik bekçileri yalnız bu görevin yeni `data/` dosyaları yüzünden kırmızıysa deselect → commit → deselect'siz tam koşu. Eski kohort bekçileri asla deselect edilmez.
7. **B:**
   - dört modelin walk-forward koşuları (günlüğe);
   - ledger'lar `tests/reference/macos_golden_faz7/`;
   - yakın dönem birincil hücreleri ve etiketleri; ilan edilmiş ikinciller; merdiven farkları (§5.4, yalnız "payı");
   - nihai fit önizlemesi: λ, katsayılar, δ, satır/olay sayıları; `models/`'e yazılmaz;
   - MODELS.md "Faz 7: tavan serisi v1" bölümü (`report_faz7.py`; var olan bölümlere dokunma; kartta "kasa: bekliyor");
   - T6 karşılaştırması.
   
   Tam pytest + test.sh yeşil → **commit B**.
8. **Rapor** `docs/faz7/IMPL_RAPOR.md` (commit R): hash'ler, beklenen sayılar tablosu (ölçülen), yakın dönem hücreleri (fark [%95], n, blok, etiket; §6.2 konumu), ikinciller, merdiven, nihai fit önizlemesi, TÜFE dosyası özeti (aylar, kaynak, sha), test sayıları, dondurma görevi için notlar (Rust'ta gerekecekler, altın vektör planı).

## Tek oturumda bitmezse
A yeşil ve commit'liyse orada dur. B yeniden koşulabilir (ledger'lar deterministik).

## Kurallar
- **Yazılabilir:**
  - `borsai/` (T1 listesi ve `report_faz7.py`);
  - `tests/` (yeni dosyalar, `tests/reference/macos_golden_faz7/`, T4 için `tests/test_outcome_guard.py`);
  - `data/training_table_v2.csv`, `data/data_version_v2.json`, `data/build_training_table_v2.py`, `data/raw/tuik/`;
  - `docs/PROVENANCE.md` (yalnız ekleme), `experiments/log.jsonl` (yalnız ekleme), `docs/MODELS.md` (yalnız yeni bölüm), `docs/SPEC_DEVIATIONS.md` (J);
  - `docs/faz7/`, `docs/specs_faz7/KARARLAR.md` (yalnız commit; içerik değişmez);
  - `app/parity/golden/MANIFEST.json` (yalnız T2 pini);
  - bu görev dosyası.
- **Salt okunur:** `models/`, `registry/`, `scores/`, `app/` (T2 hariç), `legacy/`, `CLAUDE.md`, `docs/specs*` (KARARLAR commit'i hariç), `data/training_table.csv`, `data/data_version.json`, `data/build_training_table.py`, `data/outcomes_oot/`, `data/raw/` (tuik hariç).
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit'ler:
  ```
  git add borsai tests data/training_table_v2.csv data/data_version_v2.json data/build_training_table_v2.py data/raw/tuik docs/PROVENANCE.md docs/SPEC_DEVIATIONS.md docs/specs_faz7/KARARLAR.md docs/faz7 app/parity/golden/MANIFEST.json docs/prompts/FAZ7_HAZARD_V1_IMPL.md
  git commit -m "BORSAI_FAZ7_A: ceiling hazard v1 code, CPI series, training table v2, rules and tests, no backtest results" -- borsai tests data/training_table_v2.csv data/data_version_v2.json data/build_training_table_v2.py data/raw/tuik docs/PROVENANCE.md docs/SPEC_DEVIATIONS.md docs/specs_faz7/KARARLAR.md docs/faz7 app/parity/golden/MANIFEST.json docs/prompts/FAZ7_HAZARD_V1_IMPL.md
  git add tests experiments/log.jsonl docs/MODELS.md docs/faz7
  git commit -m "BORSAI_FAZ7_B: ceiling hazard v1 walk-forward backtest, near-era cells, golden ledgers and MODELS.md Faz 7 section (not frozen)" -- tests experiments/log.jsonl docs/MODELS.md docs/faz7
  git add docs/faz7/IMPL_RAPOR.md docs/faz7/ekler
  git commit -m "BORSAI_FAZ7_REPORT: implementation and backtest report" -- docs/faz7/IMPL_RAPOR.md docs/faz7/ekler
  ```
  Değişmeyen bir yol pathspec'te hata verirse o yolu çıkar. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Rapor Türkçe.

## Kabul kapısı
- **K1** A: beklenen sayılar tablosu birebir; v0/PB/@INF ve 16 altın dosya bayt-eşit; T4 mutasyonla gösterildi; tam pytest + test.sh yeşil; A'da skor yok.
- **K2** B: dört model koşuldu ve günlükte; yakın dönem hücreleri etiketleriyle; §6.2 karşılaştırması raporda; nihai fit önizlemesi var; `models/` değişmedi.
- **K3** Sıra A → B → R; yalnız izinli yollar; push yok.

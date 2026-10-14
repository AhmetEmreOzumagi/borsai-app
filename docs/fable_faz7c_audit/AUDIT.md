# BORSAI_FAZ7C_FABLE_REPRO_AUDIT_20260927 — düşen arz modeli v0 ailesinin bağımsız yeniden üretimi ve uygunluk denetimi

Görev: `docs/prompts/FAZ7C_FABLE_REPRO_AUDIT.md`. Yazım: 2026-09-27, Fable. Denetlenen: `3c93f9c` (A), `1239e45` (A2), `77d0ee5` (A3), `acaca2d` (B), `197a741` (R; HEAD). Şartname `docs/specs_faz7_c/SPEC_C_V0.md` (`4fe4e51`, sha256 `d75c17cfec09…`, push kanıtı 2026-09-27T15:30:43Z) ve `KARARLAR_C.md` (sha256 `2b60bec41924…`). Ağ yok; yalnız okuma git komutları; `registry/`, `data/`, `scores/`, `models/`, `app/` dokunulmadı (koruma ölçümü `ekler/koruma_once.txt` / `koruma_sonra.txt`). Yeniden üretim betiği `ekler/repro_fall.py` `borsai` paketini import etmez (dosyada import satırı yok; koşu sonunda `sys.modules` denetimi: yok). Çözücü olarak şartnamenin tanımladığı scikit-learn `LogisticRegression` (L2, lbfgs, `tol=1e-10`, `max_iter=10000`, `l1_ratio=0`, sabit cezasız) doğrudan çağrıldı; optimumun çözücüden bağımsızlığı kendi Newton çözümümle gösterildi.

İşaretler: **[ÖLÇTÜM]** = bu oturumda betik/komut çıktısı; **[ÇIKARIM]** = yorum. Sayılar backtest terazisindedir (H99 walk-forward, tasarıma maruz); kasa ve canlı teraziler bu belgede yoktur. Fark = model − karşılaştırılan (Brier, p_up, kırpmasız); negatif = model iyi.

**Hijyen.** Kasa (SEALED, 64) üyelerinin hiçbir dosyası açılmadı; kasa kümesi yalnız `registry/oot/records/*/*.json` dosyalarının `vault` alanından bellekte kuruldu (kohort dosyası bir kez, yalnız `vault` sütunu sayımı için betikle okundu, satır basılmadı). `EXPOSURE.md` dosyaları ve Codex `exposure_log`'ları okunmadı. Hiçbir çıktıda kasa kodu yok (`ekler/vault_check_out.txt`); açık kümenin kodları yalnız ledger/CSV dosyalarında (altın ledger'larda da yoktur; v2 tablosunda vardır). `thb`/`thm` + tarih kalıbı yazılmadı.

## 0. Hüküm

| model_id | Hüküm | Dayanak |
|---|---|---|
| `fall_d10_v0_h99` | **FREEZE_OK** | ledger 164/164 satır alan alan birebir, p / sabit / katsayı / iç LOOCV tablosu maks \|Δ\| = 0; önizleme birebir; hücreler birebir; sızıntı yok; 16 mutasyonun hepsi kırmızı |
| `fall_d10_v0_pooled` | **FREEZE_OK** | ledger 188/188 birebir (maks \|Δ\| = 0); önizleme birebir; birincil hücre −0.0058 [−0.0340, +0.0219] "belirsiz" birebir; J10 dışlaması bağımsız hesapla aynı |
| `fall_d10_v0_addsale` | **FREEZE_OK** | ledger 190/190 birebir; önizleme birebir; hücreler birebir |
| `fall_d10_v0_pooled@ZERO` | **FREEZE_OK** | ledger 188/188 birebir; D10 = 1 − 39/161, D5 = 1 − 29/161 Fraction ile bit-eşit; plan ve dışlama havuzla aynı |

Hüküm koşulları: yeniden üretim (§1) tam; sızıntı ve sıra kanıtları (§2) tam; mutasyon (§5) 16/16 kırmızı; tam test koşusu (§9) yeşil. Bulgular (§7) KÜÇÜK düzeyindedir; hiçbiri kodu ya da şartnameyi değiştirmeyi gerektirmez; dondurma görevine notlar §8'de.

## 1. Sıfırdan yeniden üretim [ÖLÇTÜM] — `ekler/repro_fall.py`, çıktı `ekler/repro_stdout.txt`, `ekler/repro_output.json`, `ekler/repro_ledgers/`

Betik yalnız şu dosyaları okur: `data/training_table.csv`, H99 ana tablosu (`ipo_size_tl`), SESSIONS dosyası (yalnız tarih ve kapanış sütunları), `data/raw/tuik/tufe_genel_2025_100.csv`, `data/training_table_v2.csv`, `data/outcomes_oot/<açık üye>.csv` (yalnız v2'de `OOT_OPEN` olan 71 kod), Faz 1A karşılaştırıcı ledger'ları (sha pinli), Faz 7 ve Faz 7C altın dosyaları (yalnız karşılaştırma), MODELS.md ve günlük (yalnız karşılaştırma). Kendi uygulamam: f1 (kaynak büyüklük ya da pay × fiyat, 28 hane), f1r = f1 / (TÜFE[m−2]/100) (60 hane), ek satış bayrağı = 1[Decimal > 0] (boş → küme dışı), Type-7 [p05, p95] kırpma ham değerde → ln (60 hane) → z (ddof = 0; add_sale yalnız z, kesin), J10 dışlaması (mod: en çok sayı, eşitlikte alfabetik; açıkça zıt durum dışarı; iç CV'de her iç küme için yeniden), iç arz-bırak LOOCV Brier ile C ∈ {ZERO, 1e-4 … 100} seçimi (eşitlikte küçük C, ZERO en küçük; azınlık < 2 → C = 0.01 ayarsız; aday başına yakınsamama), PLAN_V15 kuralı ufuk başına (K6-A: D5 fold'unda D5 seansı < T; n ≥ 10), C7 ay-blok bootstrap (`random.Random(20260921)`, 4000, indeks 100/3899).

### 1a. Eğitim kümeleri ve özellikler (§1.3, §3, §11-1..3)

| Denetim | Beklenen | Ölçülen | Sonuç |
|---|---|---|---|
| `H99_F3_AS_PRESENT` | 94 (D10 26, D5 18) | 94 (26, 18); H99 94 | tuttu |
| `H99_PLUS_OOT_OPEN_F3_AS_PRESENT` | 161 (39, 29) | 161 (39, 29); H99 94 + açık 67 | tuttu |
| `H99_PLUS_OOT_OPEN_AS_PRESENT` | 165 (40, 30) | 165 (40, 30); H99 95 + açık 70 | tuttu |
| ek satış bayrağı = 1 | H99 6, açık 13 | 6 / 13 (alan boş: H99 4, açık 1) | tuttu |
| f1r bit-eşitliği | `ceiling_hazard_v1_real` ham f1r | kendi f1r'imden Type-7 p05/p95 ve min/max, v1_real (97) ve v1_pooled (165) altın önizlemelerinin float değerleriyle bit-eşit; TÜFE ay/endeks v2 tablosuyla 170/170 aynı | tuttu |
| v2 H99 satırları | training_table.csv ile aynı | 31 sütun × 99 satır hücre-eşit, sıra aynı | tuttu |
| ön işleme sırası | ham kırpma → ln → z | bağımsız uygulama; önizleme `winsor`, `mean`, `std` maks \|Δ\| = 0 (§1d) | tuttu |

### 1b. Fold planları (§5.1, §11-6; K6-A)

| Plan | Test arzı | Skorlanabilir D10 / D5 | Yakın dönem D10 (ay) | f3 dışlamalı fold D10 / D5 |
|---|---|---|---|---|
| `fall_h99` | 94 | 82 / 82 (ilk 12 fold eğitim n < 10) | 75 (22) | 0 / 0 |
| `fall_pooled` (pooled ve @ZERO) | 94 | 94 / 94 | 75 (22) | 41 / 39 |
| `fall_addsale` | 95 | 95 / 95 | 76 (22) | 0 / 0 |

Yakın dönem ticker kümesi h99 = pooled (75) ve test kümeleri h99 = pooled: evet. Beklenen fold sayıları IMPL_RAPOR'dakilerle aynı. Havuz fold'larında dışlananlar hep açık kümenin 3 FILTERED üyesi (mod UNFILTERED olan fold'larda; bütün havuzda NOT_SPECIFIED 89 > UNFILTERED 71 olduğundan nihai fitte dışlama yok).

### 1c. Ledger'lar (dört model × iki ufuk) — `tests/reference/macos_golden_faz7c/` ile

Karşılaştırılan alanlar: birebir — `fold_id`, ufuk, ticker, T, kesim, hedef seans tarihi, `training_n`, `n_chronological_train`, `training_tickers_sha256`, `training_targets_sha256`, fiyat, gerçekleşen getiri/yön/olay, `training_n_oot_open`, `training_n_filter_excluded` ve sha'sı, `test_f1r_raw`, `test_f3`, `test_add_sale`, TÜFE ayı/endeksi, `logit_status`, `logit_selected_C`, ayar durumu, iç fold sayısı, sütunlar, sınıf sayıları, tahmin sınıfı, kırpma bayrakları, mod eşitliği ve iç dışlama sayaçları, nihai fit denemeleri; sayısal — `logit_probability`, `logit_intercept`, `logit_coef`, `logit_score_table` (8 aday skoru).

| Model | Satır (benim / altın) | Birebir uyuşmazlık | maks \|Δ\| p | maks \|Δ\| sabit | maks \|Δ\| katsayı | maks \|Δ\| iç LOOCV | Sonuç |
|---|---|---|---|---|---|---|---|
| `fall_d10_v0_h99` | 164 / 164 (FIT_OK 152, tek sınıf 12) | yok | 0 | 0 | 0 | 0 | **tuttu** |
| `fall_d10_v0_pooled` | 188 / 188 (hepsi FIT_OK) | yok | 0 | 0 | 0 | 0 | **tuttu** |
| `fall_d10_v0_addsale` | 190 / 190 | yok | 0 | 0 | 0 | 0 | **tuttu** |
| `fall_d10_v0_pooled@ZERO` | 188 / 188 | yok | 0 | 0 | — | — | **tuttu** |

[ÇIKARIM] Bit-eşitlik (\|Δ\| = 0) beklenenden güçlüdür: aynı z matrisi (kesin ön işleme + binary64) aynı sklearn sürümüne (1.9.0) girince aynı çıktı doğar; kodun 28 haneli "ortam çıkarması" (K4) ile benim 60 haneli çıkarmam z'nin binary64 değerini değiştirmedi. Tek "uyuşmazlık" ilk koşumda ayar durumu etiketimin metniydi (`…MINORITY_LT_2` vs kodun `…MINORITY_COUNT_LT_2`; 2 satır, azınlık < 2 → C = 0.01); etiket düzeltildi, davranış aynıydı.

**Çözücüden bağımsızlık (Newton, sabit cezasız L2 amaç):** 4 fold'da \|Δp\| ≤ 3.0e-10 (maks \|Δβ\| ≤ 1.8e-8); 6 nihai fit'te maks \|Δβ\| ≤ 2.2e-9, eğitim satırlarında maks \|Δp\| ≤ 6.5e-10 — optimum sklearn'e bağlı değil (eşik 1e-6).

### 1d. Nihai fit önizlemeleri (§2.3, §11-5)

| Model | C (D5 / D10) birebir | maks \|Δ\| sabit, katsayı, iç LOOCV | ön işleme (winsor p05/p95, μ, σ) maks \|Δ\| | eğitim bloğu (n, olaylar, kohort, sha, ticker listesi, dışlama, tarih aralığı) | özellik aralıkları | Sonuç |
|---|---|---|---|---|---|---|
| `h99` | evet (1 / 1) | 0 / 0 / 0 | 0 | aynı | aynı | tuttu |
| `pooled` | evet (1 / 1) | 0 / 0 / 0 | 0 | aynı | aynı | tuttu |
| `addsale` | evet (1 / 1) | 0 / 0 / 0 | — | aynı | aynı | tuttu |
| `pooled@ZERO` | ZERO / ZERO | — | — | aynı | — | tuttu; D10 `0.7577639751552795` == float(1 − 39/161), D5 `0.8198757763975155` == float(1 − 29/161) |

Belge sha'ları (`spec.spec_document`, `spec.decisions_document`) dosyalarla aynı. JSON alanları §2.3 listesinin tamamını taşıyor (`algorithm`, `features`, `horizons.{D5,D10}.p_up {kind, columns, coef, intercept}`, `return: null`, `preprocessing {columns, winsor, log_transform, mean, std, f3_filter_mode}`, `input_policy`, `feature_ranges`, `deflator`, `training {set, table, cohort_counts, n, events_D5, events_D10}`, `family`, `variant`, `target_definition`, `spec_sha256`).

### 1e. Hücreler (§5.1, §5.4, §6.2)

33 hücre (birincil, 10 ilan edilmiş ikincil, 3 merdiven, 4 keşif, 7 çift × {2023, bütün} kapsam) hem benim ledger'larımdan hem Opus'un altın ledger'larından hesaplandı: fark, aralık, model/karşılaştırıcı Brier'i maks \|Δ\| = 0; n, ay, olay, kazanç/kayıp/eşit birebir. Günlükteki tam hassasiyetli birincil hücreyle \|Δ\| = 0. MODELS.md Faz 7C bölümünün basılı 4 ondalıklı 26 değeri (birincil, ikinciller, merdiven; n, ay, kazanç/kayıp) birebir.

| Hücre | n (ay, olay) | model | karş. | fark | %95 aralık | k/k/e | Etiket / okuma | §6.2 konumu |
|---|---|---|---|---|---|---|---|---|
| **`pooled − h99` D10 (birincil)** | 75 (22, 21) | 0.1624 | 0.1682 | **−0.0058** | **[−0.0340, +0.0219]** | 33/42/0 | **belirsiz** | aralık içinde (beklenen −0.002 [−0.015, +0.012]) |
| `h99 − base_rate` D10 | 75 (22, 21) | 0.1682 | 0.2116 | −0.0434 | [−0.0773, −0.0048] | 56/19/0 | aralık 0'ın altında | aralık içinde |
| `h99 − base_rate` D5 | 75 (22, 15) | 0.1243 | 0.1648 | −0.0405 | [−0.0742, −0.0074] | 59/16/0 | aralık 0'ın altında | — |
| `h99 − v1_5_h99` D10 | 75 (22, 21) | 0.1682 | 0.1737 | −0.0055 | [−0.0228, +0.0154] | 55/20/0 | 0'ı içeriyor | aralık içinde |
| `pooled − base_rate` D10 | 75 (22, 21) | 0.1624 | 0.2116 | −0.0492 | [−0.0670, −0.0296] | 63/12/0 | aralık 0'ın altında | aralık içinde |
| `pooled − base_rate` D5 | 75 (22, 15) | 0.1340 | 0.1648 | −0.0308 | [−0.0495, −0.0170] | 62/13/0 | aralık 0'ın altında | — |
| `pooled − v1_5_h99` D10 | 75 (22, 21) | 0.1624 | 0.1737 | −0.0113 | [−0.0465, +0.0281] | 55/20/0 | 0'ı içeriyor | aralık içinde |
| `addsale − base_rate` D10 | 76 (22, 22) | 0.2087 | 0.2153 | −0.0065 | [−0.0301, +0.0161] | 56/20/0 | 0'ı içeriyor | aralık içinde |
| `addsale − base_rate` D5 | 76 (22, 16) | 0.1699 | 0.1707 | −0.0008 | [−0.0186, +0.0153] | 60/16/0 | 0'ı içeriyor | — |
| `addsale − v1_5_h99` D10 | 76 (22, 22) | 0.2087 | 0.1782 | +0.0305 | [−0.0131, +0.0808] | 41/35/0 | 0'ı içeriyor | aralık içinde |
| `pooled − pooled@ZERO` D10 | 75 (22, 21) | 0.1624 | 0.2073 | −0.0449 | [−0.0629, −0.0262] | 61/14/0 | aralık 0'ın altında | — |
| merdiven `h99 − addsale` D10 | 75 (22, 21) | 0.1682 | 0.2023 | −0.0341 | [−0.0768, +0.0060] | 48/27/0 | bilgi | — |

Etiket kuralı (alt > 0 → bozuyor; üst ≤ +0.008 → tolerans içinde; diğer → belirsiz) bağımsız uygulamamda aynı etiketleri verdi; §6.2 tablosu şartname dosyasından ayrıştırılarak okundu (5 satır, aynen) ve yedi konumun yedisi "aralık içinde"; "beklentiden çok iyi" yok. Karşılaştırıcılar: `base_rate` (`898d2d84…`) ve `v1_5_h99` (`5c56da37…`) sha'ları pinle aynı; V1.5 D10 Brier ledger'dan 0.1883429652 (81 fold; yayımlı 0.1883). Hiçbir fold'da \|fark\| ≤ 1e-12 eşitlik yok (bağımsız yeniden fit bit-eşit çıktığından bu sayı Opus'unkiyle de aynı: 0).

## 2. Sızıntı, sıra ve uygunluk [ÖLÇTÜM]

- **(i) Test arzı** (`repro_stdout.txt` "2-i"): ön işleme ve fit yalnız eğitim satırlarından kurulur (yapısal); üç fold'da (h99 D10, pooled D10, addsale D5) test arzının f1r × 7, f3 / 3, bayrak çevrilmiş ve sonucu çevrilmiş olarak yeniden fit: sabit, katsayılar, iç LOOCV tablosu, seçilen C ve ön işleme parametreleri bit-eşit; yalnız test olasılığı değişti (0.937 → 0.087; 0.903 → 0.203; 0.868 → 0.475).
- **(ii) Eğitim kesimi:** her fold'da her eğitim satırında D_h seansı < T ihlali 0 (dört model, iki ufuk); aynı gün satırı 0. D5 fold'larında D10 seansı ≥ T olan (fold, satır) çifti h99 94, havuz 98, addsale 103, @ZERO 98 — K6 kaydıyla aynı (sızıntı değil: D5 fold'u yalnız D5 etiketini kullanır; proje sahibi kararı K6-A).
- **(iii) TÜFE:** ay kuralı m − 2 (örn. 2026-08-06 → 2026-06); her satırın kendi T'sine göre yayım günü < T 170/170; her skorlanabilir fold'da eğitim ∪ test satırlarının yayım günü < fold T'si: ihlal 0.
- **(iv) Kasa** (`ekler/vault_check.py`, `vault_check_out.txt`): SEALED kümesi kayıtlardan 64, kohort dosyasından 64, aynı. Kasa kodu geçen dosya: `tests/reference/macos_golden_faz7c/` 0, `docs/MODELS.md` 0, `experiments/log.jsonl` 0 (2 054 keşif satırı dahil 0), `docs/faz7c/` 0, `docs/SPEC_DEVIATIONS.md` 0, `docs/specs_faz7_c/` 0, `borsai/` 0, Faz 7C testleri 0, bu denetimin dosyaları 0; `data/` 1 (J18 istisnası dışında; `data/raw/PREBOOKBUILD…R2_99.csv`'de bir H99 unvanının sözcüğü — Faz 7 denetimi B9, bu görevden önce var, Faz 7C'nin dosyası değil). v2 tablosunda açık küme kodu 71/71, kasa 0; altın havuz ledger'ında açık kod 0 (yalnız H99 test arzları).
- **(v) Çalışma zamanı dosya izi** (`ekler/runtime_file_trace.py`, `runtime_file_trace_out.txt`; Opus'un HEAD kodu, dört koşu + dört önizleme, `open`/`io.open`/`os.open` sarmalı): depo içinde 210 dosya açıldı: `borsai/*.py` (kaynak sha için), `data/data_version*.json`, H99 ham dosyaları (ana tablo, SESSIONS, hedefler, hazırlık/kaynak, PB kanıtı), TÜFE csv, iki eğitim tablosu, iki şartname belgesi, iki karşılaştırıcı ledger'ı, `registry/oot/cohort_pre_h99.csv` (v2 yükleyicinin önek-sha bekçisi ve açık üye listesi; sonuç alanı yok), `registry/oot/inputs/` **açık 71, kasa 0** (v2 yükleyicinin dosya-sha bütünlük denetimi), `data/outcomes_oot/` **açık 71, kasa 0**, `registry/oot/records/` 0, **`data/outcomes/` (H99 + canlı ham sonuçlar) 0, `scores/` 0**. HEAD koduyla (A2 + A3 dahil) dört ledger altınla **bayt-eşit** (sha'lar MANIFEST ile aynı); süre 890 sn (paralel koşular altında).
- **(vi) Sıra kanıtları** (`ekler/sira_kanitlari.sh`, `sira_kanitlari.txt`): şartname commit'i `4fe4e51` 17:12:26+03:00, push kanıtı (GitHub commit status `created_at`) 2026-09-27T15:30:43Z; A `3c93f9c` 20:45:02+03:00 = 17:45:02Z → kanıt < A; `4fe4e51` A'nın atası. Resmi koşunun `git_commit` = A, `borsai_dirty` = false, `started_at` 20:45:13. `git diff 4fe4e51 197a741 -- SPEC_C_V0.md` 0 bayt; KESIF.md ve ekler değişmedi. `KARARLAR_C.md` tek commit'te (A) girdi, HEAD içeriği A'dakiyle aynı. A ağacında `macos_golden_faz7c` 0 dosya, MODELS.md'de "## Faz 7C" 0, günlükte `fall_d10_v0`/`exploration` satırı 0 (günlük A'da 79, B'de +2 058 = 4 backtest + 2 054 keşif; A2/A3'te günlük değişmedi).
- **(vii) A2 ve A3:** `git diff 3c93f9c 197a741 -- borsai` yalnız `predict_fall.py` (1 satır: ufuk **sırası** yerine **kümesi**) ve `report.py` (bölüm sırası: Faz 4 ile Faz 7 arası). B ve R'de `borsai/` değişmedi. **A2'nin yakaladığı hata gerçek** (`ekler/a2_check_out.txt`): A'nın `predict_fall._check_params`'ı yazılmış dört önizleme dosyasını da (`horizons` anahtarları sıralı: D10, D5) `PARAMS_INVALID: ufuklar ['D5', 'D10'] değil` diye reddediyor; bellekteki (D5, D10) sıralı sözlükle çalışıyor — A'nın sentetik parite testi `pretty_json_bytes` gidiş-dönüşü yapmadığı için görmedi; HEAD kodu dosyayı kabul ediyor (D10 p_up 0.9493 örnek girdiyle). Resmi koşu, ledger'lar, önizlemeler ve günlük satırları `_check_params`'ı çağırmaz (backtest yalnız `feature_values_exact`/`additional_sale_flag` kullanır); HEAD koduyla yeniden koşu bayt-eşit (madde v ve tam testteki `test_backtest_byte_identical_to_faz7c_golden`). **Hüküm:** A2 ve A3 "skor koduna dokunan düzeltme" değildir (tahmin yolu ve belge sırası); bağımsız el kuralı ihlali yok — sonuçlar görüldükten sonra yapılmış olsalar da hiçbir sayıyı etkileyemezler ve bu bayt-eşitlikle kanıtlıdır. A2 "kodu şartnameye uydurmak"tır (aynı model_id); A3 yalnız belge düzeni.

**Kurallar ↔ şartname:** `NEAR_ERA_TOLERANCE_FALL = 0.008` (sabit; kural metni sabitten üretiliyor, üç test + mutasyon h); üç etiket aynen (§5.1 sözcükleri); §5.4 merdiven "yalnız bilgi, hüküm dili yok" (MODELS.md'de öyle); §6.2 tablosu şartnameden aynen okunuyor (`report_faz7c.expectation_rows`, sıra ve metin denetimli); `report_faz7c.py` metni `OPERATIONAL_RULES_FAZ7C` sabitlerinden. **Kod ↔ şartname:** §2.3 alanları (§1d); §3 (bayrak, f1r v1_real ile tek fonksiyon, ln f3 kırpmadan sonra, filtre kuralı J10); §4 (V1.6 ızgarası `fall_grid` ile V1_6_GRID'e eşitlik zorunlu, iç LOOCV Brier, eşitlikte küçük C / ZERO en küçük, aday başına yakınsamama, azınlık < 2 → 0.01, iç bölmede ön işleme yalnız iç eğitimden — `_FallInnerCache`); §9 ret sırası ve kodları (`predict_fall`: V1.5 girdi hataları → F3_MISSING → F3_FILTER_STATUS_CONFLICT → TÜFE → ADDITIONAL_SALE_MISSING / INPUT_NEGATIVE / INPUT_NOT_NUMERIC); §13 sözde kodu (etiket, fold süzgeci FIT_OK ve T ≥ 2024-01-01, blok = ay).

## 3. K1–K15 hükümleri

| K | Davranış değiştiriyor mu | Lafza aykırı mı | Hüküm |
|---|---|---|---|
| K1 (yerleşim: bayrak `predict_fall.py`'de, `select_fall_training_rows`) | hayır (eğitim ve tahmin aynı fonksiyon; T2 pini korunuyor) | evet (§8 `features.py` der) | kabul; tek tanım korunmuş |
| K2 (ret kodları/sırası) | hayır | hayır (J5 kalıbı; C4) | kabul |
| K3 (etiket yönü: Y_h ile fit, p_up başlığı) | hayır — L2-lojistik etiket çevirmesine simetrik; ölçtüm: β_up + β_down ≤ 2.2e-16 (h99, pooled), 1.6e-8 (addsale D5); iç LOOCV tabloları \|Δ\| ≤ 5.3e-10 (`ekler/k3_flip_check_out.txt`) | §13 `Y_h = 1 − Y_h_table` der | kabul; §2'nin "p_up = 1 − P(y = 1)" tanımıyla tutarlı. Not: lafız izlenseydi lbfgs'nin sayısal yolu değişir, addsale D5 nihai fitte \|Δp\| 8.7e-9 ile 1e-9 yeniden üretim eşiği aşılırdı (model aynı) — eşik Y_h fit'i üzerinde tanımlıdır, öyle kalmalı |
| K4 (`missingness_drop=False`, ln yolu, add_sale z) | hayır | hayır | kabul |
| K5 (J10 dışlaması; proje sahibi kararı 2026-09-25) | evet: havuz D10 41/94 fold'da açık kümenin 3 FILTERED üyesi eğitim dışı | şartname "V1.5 kuralı aynen" + `impute=False` çelişkisini J10 çözer | kabul (v1 emsali). Duyarlılık s2: dışlama kapalıyken birincil hücre −0.0058 → −0.0048 [−0.0332, +0.0227], etiket "belirsiz" değişmez |
| K6 (D5 fold'unda D5 seansı < T; proje sahibi kararı 2026-09-27, sonuç görülmeden) | evet, yalnız D5 hücreleri | §11-6 "her fold'da eğitim D10 seansı < T" lafzından sapar | kabul (önceden karar). Duyarlılık s1 (seçenek B): `h99 − base_rate` D5 −0.0405 [−0.0742, −0.0074] → −0.0259 [−0.0653, +0.0085] (aralık 0'ı içerir); pooled −0.0308 → −0.0295 [−0.0512, −0.0132]; addsale −0.0008 → −0.0005. D5 h99 hücresinin "0'ın altında" okuması K6 seçeneğine duyarlıdır (bilgi; §7 F4) |
| K7 (karşılaştırıcılar Faz 1A ledger'larından, kırpmasız Brier) | hayır | hayır | kabul; sha'lar ve 0.1883 doğrulandı |
| K8 (hücre kodu, etiket, T6 konumu) | hayır | hayır | kabul; hepsi bağımsız hesapla birebir |
| K9 (`spec_sha256` = şartname sözlüğü hash'i; belge sha'sı ayrı alanda) | hayır | §11-11 lafzından sapar (J15 emsali) | kabul; bilgi kaybı yok (§7 F2) |
| K10 (keşif satırları v2 veri sürümüne) | sayaçlar: v2 kartları +2 057, H99 kartları +1 | §9 "aynı veri sürümü" lafzına uygun | kabul; **öneri aşağıda** |
| K11 (ayrı hücre sözlükleri) | hayır | hayır | kabul; dondurmada `PRIMARY_CELLS`/`OOT_PRIMARY_CELLS` ile birleştirme (§8) |
| K12 (MODELS.md bölümü; sayaç yazılmaz) | hayır | hayır | kabul |
| K13 (önizleme JSON'u) | hayır | hayır | kabul; alanlar §1d |
| K14 (A2: ufuk kümesi) | hayır (tahmin yolu; backtest'e girmez) | hayır | kabul; hata gerçek ve düzeltme doğru (§2-vii) |
| K15 (A3: bölüm sırası) | hayır | hayır | kabul |

**K10 önerisi.** `denenenler.csv`'nin 2 054 satırının `subset` alanı [ÖLÇTÜM]: "LOO H99+açık" 480, "H99→açık" 480, "açık→H99" 480, "H99+açık" 224, "H99" 116, "H99→OOT_OPEN" 66, "OOT_OPEN→H99" 66, yalnız "açık" 142. Yani **1 912 / 2 054 varyant H99 sonuçlarına dokundu** (H99'da fit ya da H99'da skor). `fall_d10_v0_h99`'un özellikleri bu keşiften seçildi; kartının sayacının (H99 sürümü: 23) keşfi saymaması CLAUDE.md kural 4'ün amacına ("denenen varyant sayısı dürüst yazılır") **uygun değildir**, şartname §9'un "aynı veri sürümü" lafzına uygundur. Öneri (skorlama/gösterim kuralı; model değil, şartname değişikliği değil; SPEC_DEVIATIONS'a K notu): (1) `scoring._n_variants_same_data` (C) ailesi kartlarında keşif satırlarını **`family` eşleşmesiyle, veri sürümünden bağımsız** saysın ve iki sayı yazsın: "aynı veri sürümü: N" + "aile keşfi: 2 054 (1 912'si H99 sonuçlarını kullandı; v2)"; (2) alternatif olarak keşif satırlarına `data_versions: [H99, v2]` alanı eklenemez (günlük append-only), bu yüzden sayaç kuralı kodda değişmeli; (3) EK3 kartı (uygulama) her (C) kartında aile keşif sayısını zaten göstermeli (IMPL_RAPOR §12); dondurma görevi bunu `scores.json` yeniden üretilirken uygulasın. Veri sürümü etiketi "v2" doğru kalır (keşif `training_table_v2.csv` üzerinde yapıldı).

**Var olan testlerde A/B istisnaları:** yalnız J16/J30 kalıbı: `faz7c_support.faz7c_variants` (veri sürümü başına Faz 7C backtest + keşif satırları) `scores_json_is_pre_faz7()` (scores.json `8e3a623` ile bayt-eşit — ölçtüm: evet, sha `47352921…` aynı) iken düşülür; fark tam sayıya eşit: H99 sürümünde `_n_variants_same_data` 23 = 20 (kart) + 2 (Faz 7) + 1 (Faz 7C); v2'de `faz7c_variants` 2 057 = 3 + 2 054. Beş test (`test_scoring.py` ×2, `test_faz5_live.py` ×2, `test_faz4_ceiling_path.py` ×1) ve `test_experiment_log.py` (tür kabulü, sayaç denkliğine keşif eklenmesi) diff'te görüldü; başka hiçbir bekçi gevşetilmedi (`git diff 3c93f9c^ 197a741 -- tests` yalnız bu altı dosya + yeni Faz 7C dosyaları). Skorlar yeniden üretilince istisna kendiliğinden düşer.

## 4. Tam test [ÖLÇTÜM] — `ekler/test_out.txt`

HEAD `197a741`, ana ağaç (yeniden üretim, mutasyon ve iz koşularıyla eşzamanlı): `.venv/bin/pytest -q` **806 passed** (1 721 sn); `bash app/scripts/test.sh` yeşil: cargo testleri hepsi `ok`, vitest 16 dosya / 222 test, parite 4 passed, 16 eski altın dosya bayt-eşit, `golden_unchanged: YEŞİL (U46)`. Bu koşu HEAD'deki `test_backtest_byte_identical_to_faz7c_golden` (A2 + A3 koduyla bayt-eşit yeniden koşu) ve `test_code_after_official_run_changed_only_predict_fall_and_report_order` testlerini de kapsar.

## 5. Mutasyon denetimi [ÖLÇTÜM] — `ekler/mutate.sh`, `ekler/mutasyon_ciktilari.txt` (klon `/tmp/borsai_faz7c_audit/clone`, HEAD `197a741`)

Mutasyonsuz taban: 19 hedef test (31 parametreli koşu) yeşil, 370 sn. Her mutasyon ayrı uygulanıp geri alındı; klon temiz. (e), (f), (p) ilk sürücüde uygulanamadı (hedef satır PLAN_V15 kodunda da geçiyor, çapa tek değildi → rc = 0 mutasyonsuz kodla); çapalar düzeltildi, `ekler/mutate_efp.sh` ile yeniden koşuldu; `mutate.sh` düzeltilmiş çapaları taşır.

| # | Mutasyon | Hedef test(ler) | Sonuç |
|---|---|---|---|
| a | ek satış boşken 0 kabul (`additional_sale_flag` → 0) | bayrak ret testleri, gerçek tablolarda sayımlar, ret yolları | **KIRMIZI** (5 failed) |
| b | bayrak `≥ 0` (0 → 1) | bayrak değer testleri, sayımlar | **KIRMIZI** (5 failed) |
| c | ln kırpmadan önce (log özellikleri için sınırlar ln uzayında) | Type-7 sınır testi, h99 önizleme paritesi | **KIRMIZI** (2 failed) |
| d | kırpma sınırları ve z istatistikleri test arzını içerir (`fit_fall_horizon` nihai ön işlemeye test satırı) | altın ledger bayt-eşitliği | **KIRMIZI** (1 failed) |
| e | D5 fold'unda D10 kesimi (K6 tersi) | fold planı testi (94 → 0), altın ledger | **KIRMIZI** (2 failed: `assert 0 == 94`, ledger farklı) |
| f | eğitim kesimi `<=` | fold planı testi, ledger fold kümesi, altın ledger | **KIRMIZI** (2 error: plan bekçisi `BacktestStop: gelecek sızıntısı … /D5` — aynı gün seansı olan satır yakalanıyor) |
| g | f1r T − 1 ayı | TÜFE ay örnekleri, 170 satırda PIT, h99 önizleme paritesi | **KIRMIZI** (3 failed) |
| h | yakın dönem eşiği 0.015 | sabit testi, sentinel aralıklar, kural metni, MODELS.md bölümü | **KIRMIZI** (4 failed) |
| i | yakın dönem sınırı 2023-12-01 | fold planı (75), ledger fold kümesi, birincil hücre | **KIRMIZI** (3 failed) |
| j | `@ZERO` 94 satırdan (yalnız H99) | Fraction bit-eşitliği, @ZERO önizleme paritesi | **KIRMIZI** (2 failed) |
| k | C eşitliğinde büyük C (şartname: bit-eşit eşitlikte en küçük C, ZERO en küçük; mutasyon kuralı tersine çevirir) | V1.6 eşitlik testi (`[1.0, ZERO, 0.01]` bekler, `[1.0, 0.01, ZERO]` geldi); V1.5-yolu eşitlik testi | **KIRMIZI** (1 failed, 1 passed — ikinci test bit-eşit eşitlik içermeyen sentetik veri; gerçek ledger'larda bit-eşit eşitlik yok, bkz. F9) |
| l | `base_rate` ledger sha pini atlanır | karşılaştırıcı pin testi | **KIRMIZI** (1 failed) |
| m | keşif satırı sayısı 2 053 | keşif satırları ve sayaç testi | **KIRMIZI** (1 failed) |
| n | `data/training_table_v2.csv`'ye bir kasa kodu satırı (kod bellekte seçildi, basılmadı) | kohort kodu bekçisi, yeni dosyalarda kasa kodu testi, tablo sha testi | **KIRMIZI** (3 failed) |
| o | bootstrap tohumu 20260922 | birincil hücre (günlükle eşitlik), MODELS.md bölümü | **KIRMIZI** (2 failed) |
| p | etiket yönü ters (K3): başlıklar y = 1 − Y_h ile fit, olasılık p_up diye yazılır (backtest ve nihai fit) | altın ledger bayt-eşitliği, h99 önizleme paritesi | **KIRMIZI** (2 failed) |

16/16 kırmızı; kırmızı olmayan mutasyon yok. Not: (p) ve (d) yalnız altın regresyonla yakalanıyor (F9).

## 6. Tanı (model seçimine girmez; şartname değişmez) [ÖLÇTÜM, ÇIKARIM]

**addsale yakın dönemde neden zayıf (−0.0065 [−0.0301, +0.0161])?** 76 yakın dönem fold'unun yalnız **4'ünde test arzının bayrağı 1** (3'ü düştü); 72 fold'da bayrak 0 (19 olay). Bayraklı 4 fold'da model taban orana karşı ortalama −0.199 kazanıyor, bayraksız 72 fold'da +0.004 kaybediyor: tek ikili özellikle model bayraksız arzlara havuzun bayraksız oranını (fold içinde tek değer) veriyor, bu değer H99'un yakın dönem taban oranından bir miktar uzak (eğitim ağırlıkla açık küme: bayraklı 19 arzın 13'ü açıkta; fold başına H99'dan bayraklı eğitim arzı 2…6). Kazancın tamamı 4 fold'dan geliyor; aralık bu yüzden geniş ve 0'ı içeriyor. [ÇIKARIM] Kasada ≈ 12 bayraklı üye (açık oranla) beklendiğinden addsale'in kasa hücresi daha bilgilendirici olabilir; bu model seçimi değil, §6.1'in yazdığı beklentidir.

**pooled − h99 "belirsiz": fark nereden geliyor?** 75 fold'da ortalama p_up pooled 0.793, h99 0.740, gözlenen yukarı oranı 0.720 → havuz **daha yüksek düzeyde** (açık kümenin düşük düşme oranı sabiti yukarı çeker) ve gözlenene göre h99 daha iyi kalibre (Murphy güvenilirlik pooled 0.0325 / h99 0.0264). Ayırma gücü ise havuzda daha yüksek: AUC 0.869 / 0.804, çözünürlük 0.0692 / 0.0551. h99'un p'leri havuzun ortalama düzeyine logit ötelemesiyle kaydırılınca Brier 0.1682 → 0.1772: **düzey payı +0.0090 (havuz aleyhine), ayırma payı −0.0148 (havuz lehine)** → net −0.0058. Yıl kırılımı: 2024 n = 33 (olay 9) −0.0230 (pooled iyi 21), 2025 n = 17 (7) −0.0205 (8), **2026 n = 25 (5) +0.0270 (pooled iyi 4)** — havuzun kazancı 2024–2025'te, 2026'da h99 daha iyi; h99'un eğitim n'i 19…93 iken havuzunki 83…160 (erken fold'larda h99 C = 0.01/0.001 seçiyor, havuz hep 1). [ÇIKARIM] "Eski veri bugünü bozuyor mu?" sorusunun cevabı zamanla değişiyor: h99 büyüdükçe havuzun düzey kayması avantajını yiyor; kasa terazisi bunu ölçmez (kasa eski dönemdir), canlı sicil ölçer.

**Kasa için gerçekçi güç (n ≈ 60, ≈ 12 olay; kasa verisi YOK):** (a) yakın dönem `h99 − base_rate` D10 farklarının sd'si 0.197; iid %95 genişlik n = 75'te 0.089, ay-blok genişlik 0.073 (oran 0.81); n = 60 için ≈ 0.081–0.100. (b) Benzetim: `fall_d10_v0_h99` nihai fiti (H99'da eğitildi) açık kümenin f3'lü ve ek satışlı 67 arzında skorlanınca Brier − taban (H99 oranı 0.7071) = −0.0099 [−0.0617, +0.0400] (aktarım; keşifteki −0.023'ten daha zayıf — keşif λ = 10 standartlaştırılmış lojistikti, burada C = 1 ve H99 kırpma sınırları); 67'den 60'lık 200 alt örnekte ay-blok aralık genişliği medyan **0.109** (IQR 0.102–0.113), olay medyan 12. [ÇIKARIM] Kasada gerçek fark −0.03 (§6.1 beklentisi) olsa bile aralık büyük olasılıkla 0'ı içerir; "geçiyor (zaman-dışı terazide)" için \|fark\| ≳ 0.055 gerekir. §6.1'in "en olası sonuç: ayırt edilemiyor" beklentisi ölçüyle uyumlu.

**Duyarlılıklar** (`ekler/sensitivity_runs.jsonl`, 5 satır `kind: sensitivity`; model değil, hiçbir tabloya girmez): s1 K6-B (D5 fold'unda D10 < T; h99 / pooled / addsale D5) — yukarıda; s2 J10 kapalı (pooled ve @ZERO D10) — birincil −0.0048 [−0.0332, +0.0227] "belirsiz", `pooled − base_rate` −0.0482, `pooled − @ZERO` −0.0444; s3 aralık üreteci — SPEC_SCORING §8 lafzındaki `numpy Generator(PCG64(20260921))` ile birincil [−0.0336, +0.0214], `random.Random(1)` ile [−0.0338, +0.0222]; dört hücrenin etiketi/okuması üreteçten bağımsız.

## 7. Bulgular

| # | Önem | Bulgu | Tür | Öneri |
|---|---|---|---|---|
| F1 | KÜÇÜK | K3: §13 sözde kodu y = 1 − Y_h ile fit der, kod Y_h ile fit eder; matematiksel olarak aynı model (β → −β, iç LOOCV aynı), fakat lbfgs'nin sayısal yolu etiketle değişir: addsale D5 nihai fitte \|Δp\| 8.7e-9 (`k3_flip_check_out.txt`). | kod ↔ şartname lafzı; **kod değişmez, şartname değişmez** (davranış aynı) | SPEC_DEVIATIONS K3'e ölçülen simetri farkını ekle; yeniden üretim eşiği (1e-9) Y_h fit'i üzerinde tanımlıdır, öyle kalsın. |
| F2 | KÜÇÜK | K9: günlükte `spec_sha256` §11-11'in lafzındaki belge sha'sı değil, şartname sözlüğünün hash'i; belge sha'sı `spec_document_sha256`'da. | lafız; **değişiklik gerekmez** | Dondurma JSON'unda ve kartta belge sha'sı `spec.spec_document.sha256` olarak zaten var; MODELS.md ve EK3 kartı bunu göstersin. |
| F3 | KÜÇÜK (gösterim dürüstlüğü) | K10: `fall_d10_v0_h99` kartının sayacı (H99 sürümü, 23) 2 054 keşif satırını saymıyor; 1 912'si H99 sonuçlarını kullandı. | skorlama/gösterim kuralı; **kodu amaca uydurmak** (model ve şartname değişmez) | §3'teki K10 önerisi: (C) kartlarında aile keşfi ayrı sayaç; dondurma/skorlama görevinde uygula. |
| F4 | KÜÇÜK (bilgi) | K6 seçeneğine duyarlılık: `h99 − base_rate` D5 ikincil hücresinin "aralık 0'ın altında" okuması seçenek B'de "0'ı içeriyor"a döner (−0.0259 [−0.0653, +0.0085]). Karar sonuç görülmeden verildi ve belgeli. | bilgi; **değişiklik yok** | MODELS.md/IMPL_RAPOR bu duyarlılığı bilgi satırı olarak taşıyabilir; D5 hücresi ikincildir, hüküm dili yoktur. |
| F5 | KÜÇÜK | MODELS.md Faz 7C fold özetinde `pooled@ZERO` satırı "ek satış sütunu sıfır varyansla düşen fold 94" yazıyor (kural satırının sütunu yok; `report_faz7c.fold_summary` `logit_columns`'ta `add_sale` arıyor). IMPL_RAPOR §8'de bilinen. | render kusuru; **kodu şartnameye uydurmak** (aynı model_id; hiçbir sayı etkilenmez) | Dondurma görevinde `report_faz7c.py` kural satırında bu alanı yazmasın; MODELS.md yeniden üretilir. |
| F6 | KÜÇÜK (süreç) | A'nın sentetik parite testi JSON yazıcısı gidiş-dönüşü yapmadığı için gerçek hata (K14) ancak B'nin gerçek dosya testlerinde görüldü; A2 sonuçlar görüldükten sonra yapıldı (etkisizliği bayt-eşitlikle kanıtlı). | süreç; **değişiklik gerekmez** (A2 zaten gidiş-dönüşü ekledi) | Kalıp: her tahmin parite testi yazılmış JSON'dan (`pretty_json_bytes` → `json.loads`) koşsun; sonuç sonrası her düzeltme, B'deki gibi, bayt-eşit yeniden koşu kanıtıyla gelsin. |
| F7 | KÜÇÜK (süreç) | `KARARLAR_C.md` kodla aynı commit'te (A) girdi ve B'den önce ayrı push kanıtı yok; K6 kararı KARARLAR_C'de değil SPEC_DEVIATIONS'ta. Sıra kanıtı git DAG'ıdır (A < B, resmi koşu A'da). | süreç; **değişiklik yok** | Dondurma push kanıtı A'yı (atası olarak) kapsayacak; dondurma raporu K6'yı bağlayıcı proje sahibi kararı olarak KARARLAR_C'nin yanında ansın. |
| F8 | KÜÇÜK (hijyen, bu görevden önce) | `data/raw/PREBOOKBUILD…R2_99.csv`'de bir kasa kodu bir H99 unvanının sözcüğü olarak geçiyor (Faz 7 denetimi B9). Faz 7C dosyalarında 0. | bilgi | Faz 7 B9 önerisi geçerli. |
| F9 | KÜÇÜK (test kapsamı) | Etiket yönü (K3) ve kırpma sınırlarının test arzını dışlaması yalnız altın ledger regresyonuyla pinli (mutasyon d, p); semantik birim testi yok. | test; **kod değişmez** | Dondurma görevine küçük bir test: eğitim satırlarında yüksek f3 → yüksek p_up işareti; fold'da test arzı değişince fit'in bit-eşitliği (repro 2-i kalıbı). |

KRİTİK: yok. ÖNEMLİ: yok. Hiçbir bulgu "şartname değişikliği = yeni model_id" gerektirmez.

## 8. Dondurma görevi için notlar

- **INDEX 23 → 27:** `FAZ7C_MODEL_IDS` sırası (`h99`, `pooled`, `addsale`, `pooled@ZERO`); önceki 23 giriş metin olarak aynı; `INDEX_POST_D1.json` değişmez. JSON'lar `backtest.final_fit_fall` ile (önizlemeyle `created_at`, `code_version`, `runtime` dışında `==`; bu denetimde bağımsız hesapla da birebir).
- **`freeze.model_kind` yönlendirmesi:** `freeze.model_kind(params)` bugün `algorithm == "l2_logit_v1_6_grid"` + `family fall_d10_v0` JSON'unu tanımıyor (`post_d1`/`hazard`/`ceiling_path`/`km`/`V1_5_RIDGE_LOGIT` dallarından sonra "rule"a düşer); `"fall"` dalı eklenip `predict_fall.predict` çağrılmalı (`specs.model_kind` "fall" döndürüyor; iki fonksiyon tutarlı olmalı, test). `fit.fit` (C) kimliklerini bilmez: J25 kalıbıyla `final_fit_fall`'a yönlendirme (veri kümesi h99 → `load_dataset`, ötekiler → `load_dataset_v2`; ek satış `data.additional_sale_shares`).
- **`registry.F3_MODELS`:** f3 isteyen `fall_d10_v0_h99` ve `fall_d10_v0_pooled` eklenmeli (J24 kalıbı; birincil kayıt kuralı "D_1'den önce push kanıtlı en son kayıt"); `addsale` ve `@ZERO` f3 istemez (en erken kayıt). Kayıt yazıcı: `model_inputs["additional_sale_shares"]` şemada var; `tufe` bloğu ve `tufe_index` v1 yolundan (J26).
- **Uygulama pinleri (J31 kalıbı):** INDEX değişince `app/parity/golden/MANIFEST.json` `models_index_sha256` (`53265dd5…`), `app/tests/fixtures/ui/preflight_ok.json` / `preflight_blocked.json` INDEX sha'sı (`BORSAI_UPDATE_UI_FIXTURES=1`), `app/src-tauri/tests/build_embed.rs` yok sayılan liste (`ignored_model_ids`: 4 Faz 7 + 4 Faz 7C, EK3 öncesi); `gen_golden.py` `PINNED_MODEL_IDS` ve `predict_sources_sha256`'ya `borsai/predict_fall.py` (bugün pinli değil). Prova dondurma + tam test geçici klonda; "23 model" varsayan testler ve `strip_frozen_faz7c` (J30 kalıbı).
- **MODELS.md `@ZERO` satırı** (F5): `report_faz7c.fold_summary` kural satırında "ek satış sütunu … düşen fold" alanını yazmasın; dondurma notu Faz 7C bölümüne (Faz 4 ile Faz 7 arası; Faz 7 testleri "### Dondurma"yı yalnız Faz 7 → Faz 5 aralığında sayar).
- **Eski kohort ek kayıtlarında (C) girdileri:** `python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv --only-missing-models` 135 üyede; kasa üyeleri için yalnız `registry/oot/inputs/<T>.json` (ek satış alanı orada; kasada 2 üyede boş → `ADDITIONAL_SALE_MISSING` RET, h99/pooled ayrıca f3 ve TÜFE isteyecek); girdiler ilk kayıtla bayt-eşit; açık küme OOT_RETRO (`n_oot_retro = 71`), kasa OOT_BLIND; model başına kapı; `oot_pre_h99_sealed` 19 + 4 v1 + 4 (C).
- **Skorlama:** `FAZ7C_PRIMARY_CELLS` / `FAZ7C_OOT_PRIMARY_CELLS` / ikinciller `PRIMARY_CELLS` / `OOT_PRIMARY_CELLS` ile birleştirilir (anahtar kümesini pinleyen iki test güncellenir); SCORES.md "(C) yakın dönem" satırı (C) INDEX'teyken kendiliğinden; skorlar yeniden üretilince J16/J30/K10 istisnaları düşer (H99 kartları 23, v2 kartları 2 059) — ve F3 önerisi (aile keşfi sayacı) aynı görevde.
- **Yeniden üretim betiği** (`ekler/repro_fall.py`, 105 sn) dondurma sonrası JSON'ları da denetleyebilir: `models/fall_d10_v0_*.json` önizlemeyle `created_at`/`code_version`/`runtime` dışında `==` ise bu denetimin hükmü dondurulmuş dosyalara taşınır.

## 9. Ekler

`ekler/koruma_once.txt`, `koruma_sonra.txt` (koruma ölçümü); `repro_fall.py`, `repro_stdout.txt`, `repro_output.json`, `repro_ledgers/` (dört model + duyarlılık ledger'ları, kompakt); `sensitivity_runs.jsonl` (5 satır); `vault_check.py`, `vault_check_out.txt`; `runtime_file_trace.py`, `runtime_file_trace_out.txt`, `runtime_file_trace_out.json`; `sira_kanitlari.sh`, `sira_kanitlari.txt`; `a2_check_out.txt`; `k3_flip_check_out.txt`; `mutate.sh`, `mutate_efp.sh` (e, f, p yeniden koşusu), `mutasyon_ciktilari.txt`; `test_out.txt`. Geçici dosyalar `/tmp/borsai_faz7c_audit/` silindi.

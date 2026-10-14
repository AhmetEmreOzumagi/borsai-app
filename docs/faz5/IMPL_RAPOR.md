# BORSAI_FAZ5_POST_D1_IMPL_20260924 — rapor

Görev: `docs/prompts/FAZ5_POST_D1_IMPL.md`. Şartname `docs/specs_faz5/SPEC_POST_D1_V0.md` (sha256 `a5b4675d…`, commit
`c20c092`) **değiştirilmedi**. Model `post_d1_hazard_v0` **dondurulmadı**; `models/INDEX_POST_D1.json` oluşmadı; `app/`,
`models/`, `registry/`, `data/`, `scores/`, `docs/specs*` dokunulmadı; push/tag/amend yok.

## 0. Kısa sonuç

- Birincil hücre (koşullu RPS_1, `post_d1_hazard_v0` − `ceiling_hazard_v0` koşullu): **fark −0.0105, %95 aralık [−0.0264,
  +0.0058], n = 70** (22 ay) → "ayırt edilemiyor"; §5 beklentisi (−0.020 … +0.003, "büyük olasılıkla içerir") **tuttu**.
- Başarısızlık (a)–(d): **hiçbiri gerçekleşmedi**. (b): nihai λ = 30, INF 2/70 FIT_OK fold (%3) → **canlı akış koşulu:
  kurulur** (proje sahibi kararı 3).
- **"Beklentiden çok iyi" TETİKLENDİ** (tek koşul: Brier k = 2 farkı −0.0512 < −0.040). Şartname gereği bu, sıradaki
  Fable yeniden üretimini |Δ| ≤ 1e-9 eşleşme eşiğine bağlar; dondurma o üretimden sonra, ayrı görevde.
- §5 tablosu: 18 satırdan 11 tuttu, 7 tutmadı (4'ü "daha iyi", 3'ü "daha kötü"/aralık dışı; ayrıntı §6).
- (d) paritesi: λ = INF fold'larında S_cond farkı tam 0 (2 fold); h_1 70/70 fold'da ana modele bit-eşit.

## 1. Commit'ler

| Commit | Hash | İçerik |
|---|---|---|
| A | `7ce0593f8b80afac7ca9c6b9117f9079f7abb662` | kod, testler, beklenti kuralları (`OPERATIONAL_RULES_FAZ5`), ayrı POST_D1 dizin desteği, SPEC_DEVIATIONS H; gerçek veride δ fit'i / walk-forward skoru / nihai fit YOK |
| B | bu raporu içeren commit (dosya kendi commit hash'ini taşıyamaz; `git log`) | resmi walk-forward koşusu, altın ledger + nihai fit önizlemesi, `experiments/log.jsonl` satırı, MODELS.md Faz 5 bölümü, altını okuyan testler (`tests/test_faz5_golden.py`) |

A2 gerekmedi. A, B'nin atasıdır (B, A'nın doğrudan çocuğu). `git show --stat 7ce0593`:

```
 borsai/__init__.py                                 |   4 +-
 borsai/freeze.py                                   |  61 +-
 borsai/hazard.py                                   |   8 +-
 borsai/outcomes.py                                 |   7 +-
 borsai/post_d1.py                                  | 929 +++++++++++++++++++++
 borsai/predict_hazard.py                           |  33 +-
 borsai/predict_post_d1.py                          | 279 +++++++
 borsai/report.py                                   |   7 +-
 borsai/report_faz5.py                              | 692 +++++++++++++++
 borsai/scoring.py                                  |  14 +-
 borsai/specs.py                                    | 100 ++-
 docs/SPEC_DEVIATIONS.md                            |  31 +
 docs/faz5/TANIM_ESLEME.md                          |  40 +
 docs/faz5/ekler/test_runs.txt                      |  14 +
 docs/prompts/FAZ5_POST_D1_IMPL.md                  | 133 +++
 tests/faz5_support.py                              | 170 ++++
 .../faz5_pre_refactor/predict_hazard_snapshot.json |   1 +
 tests/test_faz4_ceiling_path.py                    |   4 +-
 tests/test_faz5_post_d1.py                         | 889 ++++++++++++++++++++
 tests/test_outcome_guard.py                        |  40 +
 tests/test_scoring.py                              |  10 +
 21 files changed, 3446 insertions(+), 20 deletions(-)
```

B'nin yolları: `tests/test_faz5_golden.py`, `tests/reference/macos_golden_faz5/` (4 dosya), `experiments/log.jsonl` (+1 satır),
`docs/MODELS.md` (+140 satır, yalnız sona yeni bölüm), `docs/faz5/IMPL_RAPOR.md`, `docs/faz5/ekler/test_runs.txt`.

## 2. Tanım eşlemesi ve H kararları

Şartname §1–§6, §9, §11–§12'nin her maddesinin kod ve test karşılığı: `docs/faz5/TANIM_ESLEME.md` (commit A). Ana dosyalar:
`borsai/predict_post_d1.py` (stdlib tahmin: `evaluate_d1`, `d1_transform`, `updated_hazards`, `curves`, `path_conditional`,
`predict_post_d1`), `borsai/post_d1.py` (D1 yükleyicisi, D1 ön işlemesi, ofsetli Newton, λ seçimi, walk-forward, nihai fit
önizlemesi), `borsai/report_faz5.py` (§4 hücreleri, §5 kuralları, MODELS.md bölümü), `borsai/predict_hazard.py`
(`linear_predictor`), `borsai/freeze.py` (`freeze_post_d1`), `borsai/specs.py` (`POST_D1_MODEL_SPECS`).

`docs/SPEC_DEVIATIONS.md` H bölümü (A'da, sonuçlardan önce):

- **H1 (T1)** ofset `predict_hazard.linear_predictor` / `HazardFit.linear_predictors`; `predict` aynı yardımcıyı kullanır;
  logit(hazard) yok. **H2 (T2)** δ = 0 için özel dal yok. **H3 (T3)** parent nesnesi açık argüman; kopya alanlar
  uyuşmazsa PARAMS_INVALID; dosya sha'sı çağıranda.
- **H4 (sapma, karar 4)** §6.2 "INDEX.json sonuna" yerine `models/INDEX_POST_D1.json`. **H5** karar 4-4'ün bekçi okuması
  (aşağıda açık nokta). **H6** skorlama değişmedi; klon ağaçta test. **H7** ayrı `POST_D1_MODEL_SPECS`; `model_kind` →
  `post_d1`.
- **H8** kodlar B3 biçiminde (öneksiz; `not_applicable` alanı; `D1_NOT_TRADED` etiketli PredictError). **H9** denetim sırası;
  yeni etiket `D1_FIELD_INVALID`; `INPUT_SHARES_OFFERED` tahmin yolunda ana modelin reddinden sonra gelir. **H10**
  `p_break_next = 1 − S_cond[2]`. **H11** D1 ön işlemesinin sayısal biçimi (f3 yöntemi, ln ölçeğinde kantil).
- **H12** ledger `training_*` = δ eğitim kümesi. **H13** durum önceliği; parite hatasında koşu durur. **H14**
  `path_conditional` Faz 4 hücreleriyle. **H15** günlükte `spec_sha256` C6 anlamında + `spec_document_sha256`. **H16**
  `OPERATIONAL_RULES_FAZ5` yorumları. **H17** profil kantilleri (4 hane basılı). **H18** `d1_fields_sha256`. **H19**
  `half_day`/`halt_flag` eşlemesi. **H20** sızıntı testi. **H21** MODELS.md bölümü yalnız altın varsa. **H22** varyant
  sayacı ve iki test düzenlemesi.

## 3. Test sayıları

| Koşu | Sonuç | Süre |
|---|---|---|
| Taban (72a000f) | 448 passed | 5 dk 3 sn |
| A öncesi | 482 passed | 11 dk 44 sn |
| B öncesi | 490 passed | 10 dk 12 sn |

Ham son satırlar ve B koşusunun en yavaş 12 testi: `docs/faz5/ekler/test_runs.txt`. Faz 5 testlerinin kendisi ≈ 1 dk
(en yavaşları: klonda iki `build_scores` 20.6 sn, altın yeniden koşusu 11.0 sn, sızıntı testi 8.9 sn, λ = INF boru hattı 8.8 sn,
ofset paritesi fold'ları 7.6 sn). Toplamın çoğu mevcut `run_all` oturum fikstürüdür (B koşusunda 371 sn; kodu yalnız
`HazardFit.linear_predictors` ayrımıyla değişti, altınlar bayt-eşit). Taban koşunun toplamı 303 sn idi; aradaki farkın nedenini
ölçmedim (koşular sırasında makine yükü yüksekti, load average 12–14).

## 4. Kabul testleri (şartname §11) ve görev testleri

| Test | Sonuç | Kanıt (test adı) |
|---|---|---|
| §11-1 eğitim kümesi | yeşil | 81 arz; d ≥ 2: 409 satır, 67 olay, 342 sağ kalım; gün başına risk/olay §2 tablosuyla aynı; kilit 70/81; 99/99 tam gün, 0 durdurma, 99/99 sözleşme > 0 (`test_1_…`) |
| §11-2 özellik | yeşil | "10.12" = "10.120" → 1, "10.11" → 0; 70 kilitli arzda 0 tutarsızlık; oran p05/p50/p95 profil yöntemiyle \|Δ\| ≤ 1e-9 ve basılı 0.0009841 / 0.004202 / 0.5402 (`test_2_…`) |
| §11-3 ofset paritesi | yeşil | 71 fold'da γ, β, λ ve test hazard'ları Faz 1B ledger'ıyla maks \|Δ\| = **0.0**; nihai fit ofseti `predict_hazard.predict`'e bit-eşit (`test_3_…`, `test_3b_…`) |
| §11-4 fold kümesi | yeşil | 87 fold, L ≥ 1: 71, NOT_APPLICABLE 16; INSUFFICIENT 1 (EKOS); her fold'da eğitim seansları ve D1(j) < T (`test_4_…`) |
| §11-5 / T2 INF paritesi | yeşil | 81 eğitim arzı + 1000 rastgele girdi: hazard, S, `conditional_weights(S, 1)` `==`; Π(1 − h_d) ≤ 1e-12; ΣP_L_cond = 1; özel dal yok (sayaç); gerçek boru hattı λ = {INF}: 70 fold bit-eşit (`test_5_…`, `test_5b_…`, `test_t2_t7_…`) |
| §11-6 çözücü | yeşil | BFGS ile \|Δ\| ≤ 1e-6, max\|∇\| ≤ 1e-10; λ = 1e9 → ‖δ‖ ≤ 1e-6, S_cond INF ucuyla ≤ 1e-6; ofset dokunulmadı (`test_6_…`) |
| §11-7 seçim | yeşil | eşitlikte büyük λ; yakınsamayan aday çıkar, INF kalır; kolon kalmazsa INF (`test_7_…`, `test_7b_…`) |
| §11-8 sızıntı | yeşil | 2..10. seanslarda erişilen sütunlar yalnız {ticker, session_number, target_session_date}; test arzının D1'i değişince kendi fold'unun μ/σ/p05/p95'i aynı, onu eğitimde gören fold'unki değişir (`test_8_…`, `test_8b_…`) |
| §11-9 ret/uyarı | yeşil | F3_MISSING, D1_LIMIT_NA, D1_NOT_CEILING (NOT_APPLICABLE), WARN_D1_HALF_DAY, WARN_D1_INTRADAY_HALT, WARN_D1_SPECIAL_TRADES (hacim aynı), kırpma, D1_VOLUME_INVALID, D1_NOT_TRADED, WARN_D1_LOCK_INCONSISTENT, INPUT_SHARES_OFFERED, PARAMS_INVALID (`test_9_…`) |
| §11-10 JSON ↔ predict | yeşil | A: sabit δ ile 81 arzda ≤ 1e-12; B: gerçek nihai fit ile 81 arzda ≤ 1e-12, h_1 bit-eşit; stdlib import kapanışı ve numpy'siz alt süreç (`test_10_…`, `test_10b_…`, `test_faz5_golden.py::test_10_…`) |
| §11-11 path_conditional | yeşil | tek tanım (`predict_path.conditional`, sayaç); S ≡ ana model S'i → ceiling_path_v0'ın j = 1 çıktısına bit-eşit; null → NOT_PRODUCED (`test_11_…`) |
| §11-12 koşullu metrikler | yeşil | ortak fonksiyonlar (sayaç > 0); S ≡ 1[L ≥ k] → 0; S ≡ 1, L = 1 → 1; ScaleMixError (`test_12_…`, `test_12b_…`) |
| §11-14 (bu göreve düşen) | yeşil | kayıt/girdi/ipos sonuç alanı yok (mevcut test); `docs/specs` 11 dosya ve temiz; `docs/specs_faz4` 52e1567'yle bayt-eşit; INDEX.json ve 19 model dosyası 72a000f'yle bayt-eşit; Faz 1A/1B/4 altınları bayt-eşit; `scores/ registry/ data/ app/ legacy/` değişmedi; günlük yalnız ekleme; eğitim ≤ 2026-08-19 (`test_14_…`, `test_t11_…`) |
| §11-15 günlük ve rapor | yeşil | `kind: backtest`, `spec_document_sha256` = a5b4675d…, `survival_ledger_sha256` = 976b4dce…; MODELS.md 18 satırın her biri için tuttu/tutmadı (`test_15_…`, `test_15b_…`, `test_15c_…`, `test_faz5_golden.py`) |
| T1 | yeşil | §5 aşağıda |
| T4 | yeşil | dondurma yalnız INDEX_POST_D1.json'a (şema, ön koşullar, tekrar/karma çağrı reddi); listeleme öncesi kayıt sahte dizinle bayt-eşit; `sequence_guard` dizini okur (geçici git deposu); `test_outcome_guard.py::test_10e/10f`; `build_scores` klonda sahte dizinle aynı |
| T6 | yeşil | MODELS.md j = 1 satırı: n = 71, RPS_1 0.1706, dört fark ve aralık basılı hassasiyette birebir; Brier k = 2 ve k = 10 satırları da (`test_t6_…`) |
| T11 | yeşil | `docs/specs_faz5/` c20c092'yle bayt-eşit (dosya kümesi dahil) (`test_t11_…`) |
| §11-13, §11-16, §11-14'ün `registry/post_d1/` bekçisi | kapsam dışı (T10) | canlı akış ve EK 3 görevleri |

## 5. T1 kanıtı

- Refactor'dan önce (temiz ağaç, HEAD 72a000f, `borsai_dirty = false`) üretilen anlık görüntü:
  `tests/reference/faz5_pre_refactor/predict_hazard_snapshot.json` (sha256 `d115264d9d8d…`). INDEX'teki bütün hazard ve km
  modelleri (**6**: `ceiling_hazard_v0`, `@INF`, `pb_ceiling_v0`, `@INF`, `base_km_expanding`, `base_km_last10`) ×
  (**99** H99 + **14** uç durum + **200** tohumlu rastgele girdi) = **1878 çıktı `==`** (hazard, S, P_L, P_close, uyarılar,
  ret, clipped; 17 ret yolu dahil).
- 7 resmi kayıt × 6 hazard/km modeli = **42 çıktı**, kaydın `model_inputs`'u ile yeniden çalıştırılınca saklı çıktıyla `==`.
- Faz 1B ve Faz 4 altın ledger'ları bayt-eşit (tam test paketi).

## 6. Sonuçlar (docs/MODELS.md "Faz 5: D1 sonrası güncelleme")

### Fold özeti ve T7

87 fold: FIT_OK 70, INSUFFICIENT_TRAINING_HISTORY 1 (EKOS), NOT_APPLICABLE 16, SURVIVAL_NOT_AVAILABLE 0,
MODEL_NOT_FIT_DID_NOT_CONVERGE 0; yakınsamayan λ adayı 0. Seçilen λ: 3 → 22, 10 → 14, 30 → 32, INF → 2 (AGROT ve MEGMT: 1. ve 7.
FIT_OK fold; ikisinde de d1_lock σ = 0 ile düşmüş, yalnız d1_turnover aktif). δ işaretleri (λ < INF, 68 fold): δ_lock < 0 63/63 (d1_lock σ = 0 ile düşen 5: SKYMD, CATES, BEGYO, KBORU, SURGY),
medyan −0.289 [−0.512, −0.135]; δ_turn > 0 68/68, medyan +0.256 [+0.053, +0.655]. Test arzının el değiştirmesi kırpılan fold 16.
Çözücü en çok 5 yineleme, max|∇| ≤ 9.6e-11. `path_conditional` 70/70 OK.

**T7:** λ = INF fold'larında (2) modelin S_cond'u ile aynı fold'un karşılaştırıcı S_cond'u arasındaki en büyük |Δ| = **0.0**.
**T9:** (b)'nin paydası δ fit'i yapılan FIT_OK fold = 70; paydaya girmeyen INSUFFICIENT 1, NOT_APPLICABLE 16.

### §4 hücreleri (koşullu ölçek, j = 1; fark = model − karşılaştırılan; n = 70, 22 ay)

| Metrik | Karşılaştırılan | model | karş. | fark | %95 aralık | iyi / kötü / eşit | hüküm (backtest) |
|---|---|---|---|---|---|---|---|
| **RPS_1 (BİRİNCİL)** | `ceiling_hazard_v0` koşullu | 0.1591 | 0.1695 | **−0.0105** | **[−0.0264, +0.0058]** | 38 / 30 / 2 | ayırt edilemiyor |
| RPS_1 | `base_km_expanding` | 0.1591 | 0.2072 | −0.0481 | [−0.0892, −0.0050] | 43 / 27 / 0 | backtest'te geçiyor (tasarıma maruz) |
| RPS_1 | `base_km_last10` | 0.1591 | 0.2118 | −0.0527 | [−0.0934, −0.0116] | 41 / 29 / 0 | backtest'te geçiyor (tasarıma maruz) |
| RPS_1 | `ceiling_hazard_v0@INF` | 0.1591 | 0.2007 | −0.0417 | [−0.0806, −0.0009] | 43 / 27 / 0 | backtest'te geçiyor (tasarıma maruz) |
| RPS_1 | her-zaman-tavan | 0.1591 | 0.5698 | −0.4108 | [−0.5150, −0.2902] | 59 / 11 / 0 | backtest'te geçiyor (tasarıma maruz) |
| Brier k = 2 | `ceiling_hazard_v0` koşullu | 0.0784 | 0.1296 | −0.0512 | [−0.1010, −0.0097] | 50 / 18 / 2 | backtest'te geçiyor (tasarıma maruz) |
| Brier k = 2 | `base_km_expanding` | 0.0784 | 0.1426 | −0.0642 | [−0.1199, −0.0169] | 53 / 17 / 0 | backtest'te geçiyor (tasarıma maruz) |
| Brier k = 2 | `base_km_last10` | 0.0784 | 0.1700 | −0.0916 | [−0.1530, −0.0353] | 42 / 28 / 0 | backtest'te geçiyor (tasarıma maruz) |
| Brier k = 2 | `ceiling_hazard_v0@INF` | 0.0784 | 0.1435 | −0.0651 | [−0.1300, −0.0110] | 46 / 24 / 0 | backtest'te geçiyor (tasarıma maruz) |
| Brier k = 2 | her-zaman-tavan | 0.0784 | 0.1571 | −0.0787 | [−0.1557, −0.0129] | 11 / 59 / 0 | backtest'te geçiyor (tasarıma maruz) |
| Brier k = 10 | `ceiling_hazard_v0` koşullu | 0.1402 | 0.1307 | +0.0095 | [−0.0034, +0.0233] | 33 / 35 / 2 | ayırt edilemiyor |
| Brier k = 10 | `base_km_expanding` | 0.1402 | 0.1361 | +0.0042 | [−0.0493, +0.0640] | 44 / 26 / 0 | ayırt edilemiyor |
| Brier k = 10 | `base_km_last10` | 0.1402 | 0.1350 | +0.0053 | [−0.0535, +0.0683] | 42 / 28 / 0 | ayırt edilemiyor |
| Brier k = 10 | `ceiling_hazard_v0@INF` | 0.1402 | 0.1364 | +0.0038 | [−0.0501, +0.0631] | 43 / 27 / 0 | ayırt edilemiyor |
| Brier k = 10 | her-zaman-tavan | 0.1402 | 0.8571 | −0.7169 | [−0.8385, −0.5693] | 60 / 10 / 0 | backtest'te geçiyor (tasarıma maruz) |

Kalibrasyon: ort(h_2) model 0.1556 / karşılaştırıcı 0.0916 / gözlenen D2 kırılma oranı 0.1571; ort(S_cond[k]) model /
karşılaştırıcı / gözlenen: k = 2: 0.8444 / 0.9084 / 0.8429; k = 3: 0.7595 / 0.8316 / 0.7857; k = 5: 0.5024 / 0.5309 / 0.4571;
k = 10: 0.2495 / 0.2358 / 0.1429.

`path_conditional` (karşılaştırılan `ceiling_path_v0`'ın kendi j = 1 karışımı): D3 MAE −0.0234 [−0.0495, +0.0000]; D3 p_up
Brier +0.0073 [−0.0288, +0.0510]; D5 MAE −0.0086 [−0.0317, +0.0130]; D5 p_up Brier +0.0044 [−0.0311, +0.0461]; **D10 MAE
+0.0361 [+0.0002, +0.0767] (karşılaştırılan daha iyi)**; D10 p_up Brier −0.0038 [−0.0203, +0.0153].
Keşif Brier k = 3..9 (`ceiling_hazard_v0` koşullu): −0.0342, −0.0233 (aralık [−0.0430, −0.0013]), −0.0122, +0.0024, +0.0010,
+0.0042, +0.0093; k = 4 dışında aralıklar 0'ı içeriyor.

### §5 beklentisi satır satır

| Hücre | Karşılaştırılan | Beklenen (§5) | Aralık 0'ı (§5) | Gerçekleşen | %95 aralık | Etiket | Aralık ifadesi gerçekleşti mi |
|---|---|---|---|---|---|---|---|
| **RPS_1 (BİRİNCİL)** | `ceiling_hazard_v0` koşullu | −0.020 … +0.003 | büyük olasılıkla içerir | −0.0105 | [−0.0264, +0.0058] | **tuttu** | evet |
| RPS_1 | `@INF` koşullu | −0.055 … −0.015 | dışlaması olası | −0.0417 | [−0.0806, −0.0009] | tuttu | evet |
| RPS_1 | `base_km_expanding` | −0.060 … −0.020 | dışlaması olası | −0.0481 | [−0.0892, −0.0050] | tuttu | evet |
| RPS_1 | `base_km_last10` | −0.065 … −0.025 | dışlaması olası | −0.0527 | [−0.0934, −0.0116] | tuttu | evet |
| RPS_1 | her-zaman-tavan | −0.42 … −0.36 | dışlar | −0.4108 | [−0.5150, −0.2902] | tuttu | evet |
| Brier k = 2 | `ceiling_hazard_v0` koşullu | −0.025 … 0.000 | içerir ya da negatif dışlar | −0.0512 | [−0.1010, −0.0097] | tutmadı (daha iyi) | evet |
| Brier k = 2 | `@INF` koşullu | −0.040 … −0.010 | dışlayabilir | −0.0651 | [−0.1300, −0.0110] | tutmadı (daha iyi) | evet |
| Brier k = 2 | `base_km_last10` | −0.065 … −0.030 | dışlar (olası) | −0.0916 | [−0.1530, −0.0353] | tutmadı (daha iyi) | evet |
| Brier k = 10 | `ceiling_hazard_v0` koşullu | −0.006 … +0.006 | içerir | +0.0095 | [−0.0034, +0.0233] | tutmadı (daha kötü) | evet |
| Brier k = 3 (keşif) | `ceiling_hazard_v0` koşullu | −0.020 … +0.003 | içerir | −0.0342 | [−0.0745, +0.0042] | tutmadı (daha iyi) | evet |
| `path_conditional` h = 5 MAE | `ceiling_path_v0` (j = 1) | −0.015 … +0.005 | içerir | −0.0086 | [−0.0317, +0.0130] | tuttu | evet |
| `path_conditional` h = 3 p_up Brier | `ceiling_path_v0` | −0.015 … +0.005 | içerir | +0.0073 | [−0.0288, +0.0510] | tutmadı (daha kötü) | evet |
| Kalibrasyon | ort(h_2) − gözlenen | \|Δ\| ≤ 0.05 | — | −0.0015 (n = 70) | — | tuttu | — |
| λ | nihai fit | 10–100 en olası; INF olası | — | 30 | — | tuttu | — |
| λ | fold'lar | erken fold'larda INF; %20–50'sinde INF | — | INF 2/70 (%3); ilk 20 fold'da 2 (%10) | — | tutmadı (iki parça da) | — |
| δ_lock işareti | nihai + λ < INF fold'ları | < 0 (≥ %80) | — | nihai −0.3279; 63/63 | — | tuttu | — |
| δ_turn işareti | nihai fit | > 0 (düşük güven) | — | +0.2511 | — | tuttu | — |
| n (fold) | — | 65–71 | — | 70 | — | tuttu | — |

Etiketler: tuttu 11, tutmadı 7. "Kazanç en olası Brier k = 2'de" cümlesi (dört `ceiling_hazard_v0` hücresinden en negatif
fark: RPS_1 −0.0105, Brier k = 2 −0.0512, k = 3 −0.0342, k = 10 +0.0095) → **tuttu**.

### Başarısızlık tanımları, canlı akış koşulu, "çok iyi"

- (a) birincil aralık tamamen 0'ın üstünde: [−0.0264, +0.0058] → **gerçekleşmedi**.
- (b) nihai λ = INF ya da FIT_OK fold'ların ≥ %80'inde INF: nihai λ = 30; INF 2/70 (%3) → **gerçekleşmedi**.
- (c) |ort(h_2) − gözlenen| > 0.10 (n ≥ 30): 0.0015 → **gerçekleşmedi**.
- (d) parite: INF ucu maks |Δ| = 0.0 (2 fold), h_1 uyuşmazlığı 0/70; nihai fit h_1 bit-eşit (81/81) → **gerçekleşmedi**.
- (e) prospektif: canlı n = 0, hüküm yok.
- **Canlı akış koşulu: kurulur** (λ sonlu, (b) yok). Model yine de önce Fable yeniden üretimi, sonra ayrı görevle dondurulur.
- **Beklentiden çok iyi: TETİKLENDİ** — yalnız Brier k = 2 farkı −0.0512 < −0.040 (birincil fark −0.0105 ≥ −0.040; birincil
  aralığın üst ucu +0.0058 ≥ −0.020). Şartname: dondurmadan önce Fable'ın bu şartnameden bağımsız, sıfırdan yeniden üretimi;
  ledger'lar |Δ| ≤ 1e-9 eşleşmeli.

## 7. Nihai fit önizlemesi (T8; dondurulmadı)

81 arz (`H99_F3_PRESENT_L_GE_1`), δ eğitim kümesi 81 arz, 409 satır (d ≥ 2), 67 olay, 342 sağ kalım; en son eğitim seansı
2026-08-13 (≤ 2026-08-19). Ofset `models/ceiling_hazard_v0.json`'dan (`caa4dc867a9f…`), `predict_hazard.linear_predictor` ile.
**λ = 30; δ_lock = −0.3278985872465678, δ_turn = +0.25106109793882575**; kolonlar [d1_lock, d1_turnover] (düşen yok);
d1_turnover kırpma [−6.923783040059334, −0.6157622757273886]; çözücü 4 yineleme, max|∇| 2.1e-14.

| λ | 0.1 | 1 | 3 | 10 | **30** | 100 | 300 | 1000 | INF |
|---|---|---|---|---|---|---|---|---|---|
| iç CV log-kayıp | 0.39516 | 0.39390 | 0.39189 | 0.38871 | **0.38788** | 0.39328 | 0.40058 | 0.40531 | 0.40792 |

Dosya: `tests/reference/macos_golden_faz5/post_d1_hazard_v0_final_fit_preview.json` (`models/`'e yazılmadı). Önizleme
aynı kodla yeniden üretilebilir (`created_at`, `code_version`, `runtime` dışında `==`; `test_faz5_golden.py`).

## 8. Altın ledger ve günlük satırı

| Dosya | sha256 |
|---|---|
| `tests/reference/macos_golden_faz5/post_d1_hazard_v0_fold_ledger.csv` (87 satır, §6.1-8 sütunları) | `579cf2ae4a359ea7e40a9d7f764a5e781a8b00af7c2c1bb17b7fee2a981397e4` |
| `tests/reference/macos_golden_faz5/post_d1_hazard_v0_final_fit_preview.json` | `3054f97da8d3fead3c9358bf268811693b382e01057ca7a4a230500d42a6e959` |
| `tests/reference/macos_golden_faz5/MANIFEST.json` | `66c5debd63775083145e1c4e5e1bbfe04be011560097ef188597e778a92bd698` |
| `tests/reference/macos_golden_faz5/SHA256SUMS` | `b9262366ee1deb8b08feab1c93efc5dc2802d05f8004dcd916457437d055f247` |
| `experiments/log.jsonl` 65. satır (sonundaki LF hariç) | `c3421458fc5e657f3c28ac5cb1132c921a4ebaf680ecbfa1e94357bd6d45cc13` |

Günlük satırı: `kind: backtest`, `context: faz5_golden`, `model_id: post_d1_hazard_v0`, `plan_id: PLAN_POST_D1`,
`spec_sha256` (kanonik) `9d01c3c08cab…`, `spec_document_sha256` `a5b4675d…`, `survival_ledger_sha256` `976b4dcea981…`,
`path_ledger_sha256` `1f45365ee2d8…`, `ledger_sha256` `579cf2ae4a35…`, `git_commit` 7ce0593 (A), `borsai_dirty: false`,
2026-09-24T14:53:48+03:00 → 14:53:59. Günlükte bu model için tek satır vardır (tek resmi koşu).

## 9. Sapmalar, açık noktalar, Fable denetimine notlar

1. **H5 — karar 4-4'ün bekçi okuması.** "Yeni dizindeki model dosyaları da sonuç commit'lerinin atası olmalı" lafzen her sonuç
   dosyasına uygulanırsa, sonuçları repoda olan 7 arz yüzünden ilk POST_D1 dondurması `test_outcome_guard` bekçisini kırmızı
   yapardı. Uygulanan okuma: dizindeki model commit'li olmalı; her hedef ya modelden sonra (model atası) ya da önce (o arz
   RETRO) girmeli; paralel daldan birleşen ya da commit'siz modelli durum ihlal. Proje sahibi lafzi okumayı istiyorsa yalnız bu
   bekçi değişir, model değişmez.
2. **H22 — varyant sayacı.** B'nin günlük satırı aynı veri sürümündeki (model_id, spec) sayacını 19 → 20 yapar; `scores.json`
   bu görevde salt okunur olduğu için kartlarda 19 kalır. İki test (`test_scoring.py`, `test_faz4_ceiling_path.py`) A'da, farkın
   yalnız bu alanda ve tam olarak günlükteki POST_D1 varyant sayısı kadar olmasına izin verecek biçimde düzenlendi; istisna
   `scores.json` 72a000f'deki haliyle bayt-eşitken geçerli. Bir sonraki skor üretimi (ör. canlı akış görevi) 20 yazar.
3. **"Beklentiden çok iyi" tetiklendi** (Brier k = 2). Yeniden üretimde ledger'lar |Δ| ≤ 1e-9 eşleşmeli; önerilen
   karşılaştırma: `post_d1_hazard_v0_fold_ledger.csv`'nin hazard_1..10, S_1..10, S_cond_2..10, selected_lambda, δ sütunları ve
   nihai fit önizlemesinin δ/λ/skor tablosu.
4. Birincil hücre "ayırt edilemiyor"; D1 bilgisinin katkısı "yarın" (Brier k = 2) ve kısa ufukta (k = 3, 4) yoğun; k ≥ 6'da
   fark ≈ 0 ya da hafif pozitif, k = 10'da +0.0095 (beklenen aralığın dışında, aralık 0'ı içeriyor). `path_conditional` D10 MAE'de
   karşılaştırılan daha iyi (+0.0361 [+0.0002, +0.0767]); ikincil hücredir, birincili etkilemez. Kalibrasyon k = 10'da model
   0.2495, gözlenen 0.1429 (karşılaştırıcı 0.2358; ofsetin mirası).
5. "λ fold'lar" beklentisi tutmadı: INF yalnız 2/70 fold'da (AGROT ve MEGMT; 1. ve 7. FIT_OK fold), %3. İlk 7 FIT_OK
   fold'un hepsinde d1_lock σ = 0 ile düştü (eğitimdeki bütün arzlar kilitli); bunların 5'inde δ_turn sonlu λ ile fit edildi.
6. **H9:** `D1_FIELD_INVALID` şartnamede olmayan yeni etiket (en düşük/açılış/en yüksek yok ya da ≤ 0; H99'da hiç olmadı).
   `INPUT_SHARES_OFFERED` `predict_post_d1` yolunda erişilemez (ana model shares_offered'ı önce doğrular ve kendi etiketiyle
   reddeder); `evaluate_d1` tek başına bu kodu verir.
7. **H19:** SESSIONS dosyasında özel işlem hacmi yok; H99'da `WARN_D1_SPECIAL_TRADES` üretilemez (tahmini etkilemez). Canlı
   akış bülten alanını (`OZEL ISLEM BILDIRIMI ISLEM ADEDI`) kayda taşımalı (§7.6 `THB_COLUMNS` eki, kapsam dışı).
8. **Test süresi** 5 dk (taban) → 11 dk 44 sn (A) / 10 dk 12 sn (B); Faz 5 testleri ≈ 1 dk, kalan artış ölçülmedi (§3).
   Hiçbir test gevşetilmedi; H22'deki iki düzenleme tek alanla ve tam sayıyla sınırlı.
9. Kapsam dışı (T10): §11-13 (POST_D1 kayıt ve canlı sınıf), §11-16 (uygulama), `registry/post_d1/` bekçisi, CLAUDE.md kural 1
   cümlesi (canlı akış commit'inde), `THB_COLUMNS` eki, `scoring` POST_D1 satırları.
10. Sıradaki adım: Fable'ın sıfırdan yeniden üretimi (§5; "çok iyi" tetiklendiği için eşik |Δ| ≤ 1e-9) → dondurma görevi
    (`python -m borsai.freeze --models post_d1_hazard_v0` temiz ağaçta; `models/INDEX_POST_D1.json`; önizlemeyle bit-eşitlik)
    → canlı POST_D1 akışı (koşul: kurulur).

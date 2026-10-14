# BORSAI_FAZ5_FABLE_REPRO_AUDIT_20260924 — `post_d1_hazard_v0` bağımsız yeniden üretim ve uygunluk denetimi

Denetleyen: Fable (şartnamenin yazarı; uygulamayı görmeden, yalnız `docs/specs_faz5/SPEC_POST_D1_V0.md`'den kodlanmış bağımsız betikle). Denetlenen: Opus'un `7ce0593` (A) ve `7d08169` (B) commit'leri. HEAD `7d08169`; çalışma ağacında yalnız görev dosyası izlenmeyen. Ağ yok; git yalnız okuma; `registry/`, `data/`, `scores/`, `models/` ağaçları koşu öncesi ve sonrası aynı (`ekler/koruma_once.txt`, `ekler/koruma_sonra.txt`).

İşaretler: **[ÖLÇTÜM]** = bu oturumda komut/dosyadan; **[ÇIKARIM]** = yorum. Bütün sayılar `ekler/` altındaki betik ve çıktılardan; MODELS.md'den ya da IMPL_RAPOR'dan alınan hiçbir sayı yeniden hesaplanmadan kullanılmadı.

## 0. Hükümler

| Konu | Hüküm | Dayanak |
|---|---|---|
| `post_d1_hazard_v0` | **FREEZE_OK** | 87 fold'un ledger'ı sıfırdan yeniden üretildi: `status` 87/87 ve `selected_lambda` 70/70 birebir, bütün sayısal sütunlar maks \|Δ\| = 1.5e-11 ≤ 1e-9; nihai fit λ = 30 birebir, δ maks \|Δ\| 1.1e-16; §4'ün 15 hücresi + 6 `path_conditional` + 7 keşif hücresinin farkı ve aralık uçları basılı hassasiyette 28/28; §5'in 18 satırının etiketi bağımsız okumamla 18/18 aynı; (a)–(d) yok; sızıntı yok; 12 Faz 5 mutasyonunun 11'i kırmızı (tek istisna eşdeğer mutant, §4). |
| Canlı akış koşulu (proje sahibi kararı 3) | **TEYİT: kurulur** | Nihai λ = 30 (sonlu); FIT_OK 70 fold'da INF 2 (%2.9) < %80; (b) gerçekleşmedi. Payda T9'a göre FIT_OK fold'lar (INSUFFICIENT 1 ve NOT_APPLICABLE 16 paydada değil); paydaya 71 alınsa da %2.8. |
| Faz 2C koşullu skorlama | **UYGUN** | G1–G12'nin her biri SPEC_CEILING_PATH_V0 §7 ve EK2 §5 lafzına uyuyor (§6); 9 modelin bütün koşullu satırları (144) `registry/records/` ve `data/outcomes/`'tan `borsai` import edilmeden yeniden hesaplandı: maks \|Δ\| = 0; n < 10'da hiçbir j'de hücre yok; L < j hiçbir satırda yok; PENDING (NETGL, j = 1..3) bütün modellerde aynı anda; 5 Faz 2C mutasyonunun 5'i kırmızı. |

**"Beklentiden çok iyi" (§5):** bağımsız hesapla da yalnız Brier k = 2 koşuluyla tetikleniyor (−0.0512 < −0.040); birincil fark −0.0105 ≥ −0.040, aralığın üst ucu +0.0058 ≥ −0.020. Bu denetimin şartı olan \|Δ\| ≤ 1e-9 ledger eşleşmesi sağlandı (§1).

**Uygulama için bir cümle:** koşullu sekmede "D1 sonrası (`post_d1_hazard_v0`)" satırının altında, koşulsuz tablodan ayrı ve "Geçmiş veri testi (retrospektif, tasarıma maruz; koşullu ölçek, j = 1, n = 70)" başlığıyla yalnız iki hücre gösterilmeli: birincil "koşullu RPS_1 − `ceiling_hazard_v0`: −0.0105 [−0.0264, +0.0058] → ayırt edilemiyor" ve ikincil "yarın (k = 2) Brier: −0.0512 [−0.1010, −0.0097] → backtest'te geçiyor (tasarıma maruz)"; canlı sicil ayrı panelde "n = 0" ile, "geçiyor" sözcüğü yalnız "backtest'te geçiyor (tasarıma maruz)" ekiyle.

## 1. Sıfırdan yeniden üretim (`ekler/repro_post_d1.py`) [ÖLÇTÜM]

Betik `borsai`'yi import etmez (betikte `import`/`from … borsai` satırı 0; alt süreçte `sys.modules` denetimi: `ekler/repro_subprocess_check.txt` → "ALT SÜREÇ sys.modules içinde borsai: YOK"; numpy var, scipy/sklearn yok). Yalnız stdlib + numpy; 63 s. Girdiler: `data/training_table.csv`, pretrade master (`ipo_size_tl`), SESSIONS dosyası, Faz 1B altın ledger'ları, `models/ceiling_hazard_v0.json`; `data/outcomes`, `data/raw/bist`, `scores`, `docs/SCORES.md` okunmadı. Bağımsız hesaplananlar: 71 fold'un ana model ofseti (ön işleme, iç arz-bırak CV, Newton; Faz 1B betiğimin parçaları), D1 özellikleri (ham metin Decimal; ln 60 hane), fold içi D1 ön işlemesi (Type-7 kırpma, z; float64 — Opus'un kesin Fraction/Decimal yolundan bağımsız), ofsetli Newton (δ0 = 0, ∇ ≤ 1e-12'ye kadar), iç CV ve λ seçimi (eşitlikte büyük λ), test tahmini, S, S_cond, P_L_cond, `path_conditional` (Faz 4 betiğimin hücre/merdiven/karışım kodu, §7 durum 1 j = 1 uyarlaması).

### 1.1 (a) Fold ledger'ı — `tests/reference/macos_golden_faz5/post_d1_hazard_v0_fold_ledger.csv`

| Karşılaştırma | Sonuç |
|---|---|
| `status` (87 fold) | 87/87 birebir: FIT_OK 70, INSUFFICIENT_TRAINING_HISTORY 1 (EKOS), NOT_APPLICABLE 16 |
| `selected_lambda` (70 FIT_OK) | 70/70 birebir (3: 22, 10: 14, 30: 32, INF: 2 — AGROT, MEGMT) |
| `training_n_ipo/pp_rows/events/survivals`, `training_max_session_date`, `training_tickers_sha256`, `training_pp_sha256` (71) | 71/71 birebir |
| parent γ(3), β(3), test hazard_1..10 (Faz 1B ledger'ı ve Opus'un `parent_*` sütunları) | maks \|Δ\| 5.0e-11; parent λ 71/71 birebir |
| `lambda_score_table` (9 × 70) | maks \|Δ\| 3.3e-13 |
| `delta_*`, `d1_clip_*`, `d1_mean_*`, `d1_std_*`, `test_d1_turnover_ratio`, `hazard_1..10`, `S_1..10`, `S_cond_2..10` | **maks \|Δ\| 1.5e-11** (en kötü sütun S_10); |Δ| > 1e-9 sayısı **0** |
| `columns`, `test_d1_lock`, `test_d1_turnover_clipped`, `path_cond_status` | 70/70 birebir |
| `path_cond_h{3,5,10}_median` | \|Δ\| = 0 (medyanlar atom değerleridir; atomlar bit-eşit) |
| `path_cond_h{3,5,10}_p_up` | maks \|Δ\| 3.7e-12 |

### 1.2 (b) Nihai fit önizlemesi — `post_d1_hazard_v0_final_fit_preview.json`

δ eğitim kümesi 81 arz, **409 satır (d ≥ 2), 67 olay, 342 sağ kalım** (benim / Opus: aynı); en son eğitim seansı 2026-08-05 ≤ 2026-08-19. Ofset dondurulmuş JSON'un γ, β ve ön işleme sabitlerinden (kendi hesabım); h_1 ana modelin kendi h_1'iyle 81/81 bit-eşit. λ **30 / 30 birebir**; δ_lock −0.3278985872465677 vs −0.3278985872465678 (\|Δ\| 1.1e-16), δ_turn 0.25106109793882575 birebir; kırpma [−6.923783040059334, −0.6157622757273886] \|Δ\| 0; μ \|Δ\| 0; σ \|Δ\| 2.2e-16; λ skor tablosu maks \|Δ\| 2.0e-14; kolon `[d1_lock, d1_turnover]`, düşen yok; parent sha pini dosya sha'sıyla eşit.

### 1.3 (c) §4'ün bütün hücreleri ve §5'in 18 satırı

Aralık: C7 (ilk işlem ayı blokları, 4000, `random.Random(20260921)`, sıralı dağılımın 100. ve 3899. elemanı), kendi `boot`umla. **28/28 hücrede fark ve aralık uçları MODELS.md ile basılı (4 hane) hassasiyette aynı** (15 §4 + 6 `path_conditional` + 7 keşif Brier k = 3..9); n = 70, 22 ay hepsinde. Birincil: **−0.0105 [−0.0264, +0.0058]**, model 0.1591 / karşılaştırıcı 0.1695; Brier k = 2 **−0.0512 [−0.1010, −0.0097]**; Brier k = 10 +0.0095 [−0.0034, +0.0233]; `path_conditional` D10 MAE +0.0361 [+0.0002, +0.0767] (karşılaştırılan iyi). Kalibrasyon: ort(h_2) 0.1556 / karş. 0.0916 / gözlenen 0.1571; k = 2/3/5/10 ort S_cond 0.8444/0.7595/0.5024/0.2495 vs gözlenen 0.8429/0.7857/0.4571/0.1429 (MODELS.md ile aynı).

Kazanç/kayıp/eşitlik: 28 hücrenin 16'sında bit-eşit sayımla aynı; `ceiling_hazard_v0` koşullu karşısındaki 12 hücrede MODELS.md'nin 2 "eşitlik"i benim sayımımda kazanç/kayıp çıkıyor. **Kök neden benim tarafımda ve tanım gereği:** MODELS.md kuralı "fark bit-eşit 0 ise eşitlik"tir; iki eşitlik λ = INF fold'larıdır (AGROT, MEGMT: model ≡ karşılaştırıcı) ve Opus'un ledger'ında S bit-eşittir çünkü aynı kod yolu; benim bağımsız ana model refit'im Faz 1B ledger metninden ~1e-16 farklıdır, dolayısıyla fark bit-eşit 0 değil. \|d\| ≤ 1e-12 eşitlik sayılınca 28/28 aynı. Hüküm ve aralıklar etkilenmez.

§5'in 18 satırı, kendi okumamla (şartname metninden; Opus'un `OPERATIONAL_RULES_FAZ5`'i kullanılmadan): **11 tuttu, 7 tutmadı; MODELS.md ile 18/18 aynı etiket** (tutmadı: Brier k = 2 üç hücre "daha iyi", Brier k = 3 "daha iyi", Brier k = 10 "daha kötü", path h = 3 p_up "daha kötü", λ fold'lar; ayrıntı `ekler/repro_stdout.txt`).

### 1.4 (d) "Çok iyi", (a)–(d), (b)'nin paydası, canlı akış

- Çok iyi: birincil fark < −0.040 **hayır**; üst uç < −0.020 **hayır**; Brier k = 2 < −0.040 **evet** → TETİKLENDİ (Opus ile aynı).
- (a) birincil aralık alt ucu > 0: hayır. (b) nihai λ = INF: hayır; INF payı 2/70 = %2.9 (T9 paydası FIT_OK; 71 alınsa %2.8): hayır. (c) n = 70 ≥ 30, \|0.1556 − 0.1571\| = 0.0015 ≤ 0.10: hayır. (d) INF fold'larında Opus'un S_cond'u karşılaştırıcının S_cond'una \|Δ\| = 0 (2 fold; benimki 3.9e-16); h_1 Opus ledger metni = Faz 1B ledger metni 70/70: hayır.
- **Canlı akış koşulu: kurulur.** "Kazanç en olası Brier k = 2'de": tuttu (−0.0512 en negatif).

### 1.5 (e) `path_conditional`

h = 3, 5, 10 medyan ve p_up bağımsız kodla yeniden üretildi (1.1); karşılaştırılan (`ceiling_path_v0`'ın kendi j = 1 karışımı, aynı fold'un hücreleri ve Faz 1B S'i) de benim kodumla; 6 hücre basılı hassasiyette aynı. D10 MAE'de karşılaştırılan daha iyi (§5 tanısı).

## 2. Sızıntı ve uygunluk [ÖLÇTÜM]

### 2.1 §6.1-7 (i)–(vi)

| Madde | Kanıt |
|---|---|
| (i) SESSIONS'tan 2..10. seansların fiyat/hacim sütunları okunmuyor | Çalışma zamanı izi (`ekler/runtime_file_trace.py`, Opus'un `backtest_ledger(workers=1)` + `fit_params`'ı; `ekler/runtime_file_trace_out.txt`): `post_d1:load_d1_sessions` 2..10. seanslarda yalnız `{ticker, session_number, target_session_date}`; 1. seansta `thb_raw_open/high/low/close/volume/trade_count`, `thm_raw_upper_limit`, `session_type`, `security_trading_status`. Not: `ceiling_path:load_sessions` (Faz 4 yükleyicisi) 2..10. seansların `close/upper_limit/lower_limit/reference_price` sütunlarını okur — yalnız `path_conditional` hücreleri için ve kesim T ile (Opus `path_cells_by_fold` hücre sayılarını ve `cells_max_session_date`'i Faz 4 ledger'ıyla denetler; benim betiğimde `assert max_date < T` 70/70). Birincil çıktı (S) bu okumaya bağlı değildir (S, path'ten önce hesaplanır; mutasyon (d) yükleyiciyi test eder). |
| (ii) test arzının D1 alanı hiçbir fold'da eğitime/ön işlemeye girmiyor | Betiğimde δ kümesi yalnız `FTD(j) < T` olan arzlar (`assert k not in tickers`); ön işleme yalnız δ kümesinden. Opus'ta `_fold_task` prep'i `ds.tickers`'tan kurar; test_8b yeşil; mutasyon (c) kırmızı. |
| (iii) her fold'da `training_max_session_date < T`; her eğitim arzında D1(j) < T | Betiğimde iki assert 71/71; ledger `training_max_session_date` 71/71 birebir ve < `prediction_date`. |
| (iv) `realized_L`, `ceiling_close_Dk` yalnız etiket/skor | Kod okuması: `row.ceiling_streak` yalnız NOT_APPLICABLE kararı (= D1 etiketi, §1.2 girdi koşulu) ve `realized_L` sütunu; `ceiling_close` k ≥ 2 yalnız PP olayları (kesimli) ve `reclose_counts` (ana modelin P_close, kesimli). |
| (v) kurallar/karşılaştırıcı aynı fold'un Faz 1B ledger satırından | Günlük 65. satırının `evaluated` sha'ları 6/6 dosyalarla eşit (`ekler/sira_kanitlari.txt`); `report_faz5` yeniden koşmaz. |
| (vi) aynı gün listelenenler birbirini eğitmez | H99'da 3 aynı-gün çifti var (2023-12-14, 2025-02-13, 2026-03-06); betiğimde `assert FTD(j) < T` 71/71; fold planı hash'leri Faz 1B ledger'ıyla birebir. |

Yasak dizin okuması (izde): `data/outcomes`, `data/raw/bist`, `scores`, `docs/SCORES` → **YOK**; repoya yazma → yok; in-process (workers = 1) yeniden koşu altın ledger'la bayt-eşit.

### 2.2 Sıra kanıtları (`ekler/sira_kanitlari.txt`)

`c20c092` push kanıtı `created_at` 2026-09-24T00:44:25Z < `7ce0593` 2026-09-24T14:53:40+03:00 ✓; `c20c092` → `7ce0593` → `7d08169` ata zinciri ✓; `git diff c20c092 7d08169 -- docs/specs_faz5` boş ✓ (docs/specs, docs/specs_faz4 de boş); şartname sha256 `a5b4675d…` çalışma ağacı = c20c092 ✓; `7ce0593` ağacında altın faz5 dizini 0 dosya, MODELS.md'de "Faz 5" 0, günlükte post_d1 satırı 0 (64 satır) ✓; `git diff 7ce0593 7d08169 -- borsai` boş → **OPERATIONAL_RULES_FAZ5 ve eşikler sonuçtan sonra değişmedi** ✓ (`report_faz5.py` 7ce0593 ile bayt-eşit); B'nin dokunduğu yollar yalnız MODELS.md, docs/faz5, log.jsonl (+1), altın dizin, test_faz5_golden.py.

### 2.3 §5 değerlendirme kuralları (`OPERATIONAL_RULES_FAZ5`, 13 kural → 18 satır)

Her kuralı şartname metninin lafzıyla karşılaştırdım; **uymayan satır yok**. Notlar: (1) fark satırlarında [alt, üst] kapalı aralık, "(nokta ≈ x)" değerlendirilmez — şartname noktayı bilgi olarak verir ✓. (2) "Aralık 0'ı" ifadelerinin kesin kısmı: "içerir" → 0 ∈ aralık; "dışlar" → üst < 0; "içerir ya da negatif dışlar" → alt ≤ 0; "dışlaması olası / dışlayabilir / dışlar (olası)" → alt ≤ 0 (yalnız "pozitif tarafta dışlamıyor"), "büyük olasılıkla içerir" → kesin kısım yok; olasılık ifadesinin tamamı ayrı sütunda ("Aralık ifadesi gerçekleşti mi"). Bu okuma **hoşgörülüdür** ama iki sütun birlikte basıldığı ve kural sonuçtan önce sabitlendiği (H16, commit A) için lafza aykırı değildir. (3) λ nihai [10, 100] ∪ {INF}; λ fold'lar iki parça ("erken" = ilk 20 FIT_OK, Faz 1B tanımı) — şartname "erken"i tanımlamaz; H16'daki tanım makul ve önceden. (4) δ_lock iki parça, δ_turn tek, n ∈ [65, 71], kalibrasyon ≤ 0.05, (a)–(d), çok iyi eşikleri (−0.040/−0.020/−0.040), canlı akış: hepsi şartname sayılarıyla aynı. (5) Etiketler bağımsız okumamla 18/18 aynı (§1.3).

### 2.4 Kod ↔ şartname

- **§1.3:** h_1 = sigmoid(η_1) ana modelin `linear_predictor`'ından (`updated_hazards`), ana modelin `predict`'iyle aynı işlem → bit-eşit (T1 denetimim: 1644/1644). S_cond tek tanım (`predict_path.conditional_weights`); `p_break_next = 1 − S_cond[2]` (H10). `P_close` parent `reclose_rates` ✓. `path_conditional` = `predict_path.conditional(…, j = 1, [kapanış(D_1)])` tek tanım ✓ (test_11).
- **§2:** `evaluate_d1`: `d1_lock` = Decimal(ham en düşük) == Decimal(ham üst limit) ✓; `d1_turnover` = ln(hacim/shares_offered), 60 hane, bir kez binary64 ✓ (81 arzda oran kantilleri 0.0009841/0.004202/0.5402 profil ile aynı — kendi hesabım); ret/uyarı tablosu tamamı (H8 adlarıyla), `WARN_D1_LOCK_INCONSISTENT` ✓, özel işlem hacmi düzeltilmez ✓, kırpma bayrağı ✓, `OUT_OF_TRAINING_RANGE` ✓. Sıra H9.
- **§3.1:** ofset sabit (η parent'tan; γ/β yeniden fit edilmez, yeniden merkezlenmez) ✓; yeni kesişim yok ✓; pseudo-satır yok (`newton_offset`) ✓; ızgara SPEC_CEILING ile aynı (assert) ✓; iç CV: j'nin bütün d ≥ 2 satırları dışarıda, D1 ön işlemesi kalanlardan, ofset sabit ✓; nll kırpma [1e-12, 1 − 1e-12] ✓; eşitlikte büyük λ (`hz.choose_lambda`) ✓; yakınsamayan aday düşer, INF kalır ✓.
- **§6.1:** fold kümesi ve sırası Faz 1B ledger'ı (plan hash denetimleri) ✓; NOT_APPLICABLE ✓; ofset paritesi 1e-9 tutmazsa durur ✓; δ kümesi d ≥ 2 ✓; ≥ 10/5/5 ✓; fold içi ön işleme ✓; path yalnız Faz 4 fold'u OK ✓; D1(j) < T ve seans < T denetimleri ✓; ledger sütunları §6.1-8 sırası ✓; metrikler ortak fonksiyonlar ✓; günlük satırı ✓; `ScaleMixError` ✓.
- **§9:** kodlar B3 biçiminde (öneksiz: `D1_LIMIT_NA`, `D1_VOLUME_INVALID`, `INPUT_SHARES_OFFERED`, `F3_MISSING`; kapsam dışı `D1_NOT_CEILING`), şartnamenin `REFUSED_*` yazımından farklı ad, aynı davranış (H8).
- **§12:** sözde kodun `eta = logit(base.hazard)` satırı uygulanmadı; §3.1'in "aynı sayısal yol" ve §5 (d)'nin bit-eşitlik şartı gereği `linear_predictor` (H1). Doğru tercih; sözde kod şartnamenin bağlayıcı metniyle çelişiyordu (bulgu K6).
- **T1:** kendi denetimim (`ekler/t1_independent_check.py`): 72a000f'teki paket (`git archive` → `borsai_old`) ile HEAD paketi 6 hazard/km modeli × 411 girdide (H99 99 + 7 kayıt + 300 rastgele + 5 uç) **2466/2466 `==`**; 7 kaydın saklı 42 çıktısı bugünkü `predict` ile `==`; `linear_predictor` → sigmoid == `predict` hazard 1644/1644.
- **T2:** `updated_hazards`'ta ve `predict_post_d1`'de δ = 0 dalı yok (kod okuması); mutasyon (b) kırmızı (sayaç testi); bit-eşitlik genel yoldan (test_5, 70 fold INF boru hattı).
- **T4:** `models/INDEX_POST_D1.json` yok (koruma listesi 203 dosya, öncesi = sonrası); `freeze_post_d1` yalnız ayrı dizine yazar (mutasyon (j) kırmızı); `sequence_guard`/`sequence_violations` dizini okur (mutasyon (i1)/(i2) kırmızı).

### 2.5 H1–H22

| H | Davranış değiştiriyor mu | Lafza aykırı mı | Değerlendirme |
|---|---|---|---|
| H1 ofset `linear_predictor` | Hayır (T1: 2466/2466, 42/42) | §12 sözde koduna aykırı, §3.1/§5(d)'ye uygun | Kabul; şartname erratası (K6) |
| H2 δ = 0 özel dal yok | Hayır | Hayır | Kabul (mutasyon b) |
| H3 parent nesnesi açık argüman, PARAMS_INVALID | Yalnız yanlış parent'ta (daha sıkı) | Hayır | Kabul |
| H4 ayrı dizin | Dondurma yolu (karar 4) | §6.2'den sapma, proje sahibi kararı | Kabul; model kimliği değil |
| H5 bekçi okuması | Bekçi | Karar 4-4'ün lafzından esnek | Doğru ve işler; ifade açık değil (K7) |
| H6 skorlama değişmedi | Hayır | Hayır | Kabul |
| H7 ayrı `POST_D1_MODEL_SPECS` | Hayır (19 model yolu aynen) | Hayır | Kabul |
| H8 öneksiz kodlar | Ad, davranış değil | §9 tablosu `REFUSED_*` yazar | Kabul; belge notu (K1) |
| H9 sıra + `D1_FIELD_INVALID` | Yalnız bozuk girdide (H99'da 0) | Şartnamede olmayan etiket | Kabul; belge notu (K2) |
| H10 `p_break_next = 1 − S_cond[2]` | ulp düzeyi | Hayır (§1.3 iki ifadeyi eşitler) | Kabul |
| H11 kesin aritmetik, ln ölçeğinde kantil | Hayır (float64 yeniden üretimim 1e-16) | Hayır | Kabul |
| H12 `training_*` = δ kümesi | Ledger anlamı | Hayır (belirsizdi) | Kabul |
| H13 durum önceliği, parite hatasında dur | Daha sıkı | Hayır | Kabul |
| H14 path hücreleri kesim T'de yeniden | Hayır (Faz 4 ledger'ıyla denetli) | Hayır | Kabul; (i) notu |
| H15 `spec_sha256` C6 anlamı | Hayır | C6 ile aynı | Kabul |
| H16 kural yorumları | Etiketler | Hayır (önceden sabit) | Kabul; hoşgörülü okuma notu (§2.3) |
| H17 profil kantili | Hayır | Hayır | Kabul (kendi hesabım aynı) |
| H18 `d1_fields_sha256` alanları | Hayır | "4 ham metin" belirsizdi | Kabul |
| H19 half_day/halt eşlemesi; özel işlem hacmi yok | H99'da 0/0 | Hayır | Kabul; canlı akışta bülten alanı gerekir |
| H20 sızıntı testleri | Hayır | Hayır | Kabul |
| H21 MODELS.md yalnız altın varsa | Hayır | Hayır | Kabul |
| H22 varyant sayacı test istisnası | Test | Hayır | Kabul, geçici (K5) |

Tam test paketi: **490 geçti, 535.67 s (8 dk 56 s)**, `ekler/pytest_out.txt`.

## 3. Mutasyon denetimi (`ekler/mutate.sh`, `ekler/mutate_faz2c.sh`; çıktılar `ekler/mutasyon_ciktilari.txt`) [ÖLÇTÜM]

Klon `/tmp/borsai_faz5_audit/clone` (HEAD 7d08169); her mutasyon uygulandı, test koştu, geri alındı; klon sonda temiz.

| # | Mutasyon | Test(ler) | Kırmızı mı |
|---|---|---|---|
| a1 | tahmin yolunda ofset `logit(sigmoid(η))` gidiş-dönüşü | test_5_t2 (bit-eşit), test_10 | **evet** (2/2) |
| a2 | fold ofseti `logit(hazard)` (eğitim ve test η) | test_t2_t7 boru hattı, altın bayt-eşitlik | **evet** (2/2) |
| b | `predict_post_d1`'e δ = 0 erken dönüş | test_5b (sayaç), test_5_t2 | **evet** (sayaç testi kırmızı; sayısal test yeşil — beklenen: dal sayıyı değiştirmez, sayaç yakalar) |
| c | test arzının D1 özelliği prep istatistiklerine girer | test_8b, altın | **evet** (2/2) |
| d | yükleyici 2. seans hacmini okur | test_8 beyaz liste | **evet** |
| e | λ eşitliğinde küçük λ | test_7 | **evet** |
| f | kesim `<` → `<=` | test_4, altın | **evet** (2 error: `BacktestStop: gelecek sızıntısı: DMRGD` — Faz 1B plan bekçisi fold kurulumunda durdurur) |
| g1 | `d1_lock` düzeltilmiş `low`/`upper_limit` sütunlarından | test_8, test_2 | **evet** (beyaz liste kırmızı; test_2 yeşil: H99'da ham = düzeltilmiş metin 990/990) |
| g2 | `d1_lock` float karşılaştırmasıyla | test_2, test_9, altın | **HAYIR** (3/3 yeşil) → bulgu K3 |
| h | h_1 de δ ile güncellenir | test_5_t2, test_10, altın | **evet** (test_10 ve altın kırmızı; test_5_t2 δ = 0 olduğundan yeşil) |
| i1 | `sequence_guard` `INDEX_POST_D1.json`'u yok sayar | test_t4_sequence_guard | **evet** |
| i2 | `sequence_violations` dizini yok sayar | test_outcome_guard 10e, 10f | **evet** (2/2) |
| j | `freeze_post_d1` `INDEX.json`'a da ekler | test_t4_freeze | **evet** |
| k1 | §5 fark sınırı +0.001 (`parse_range`) | test_15 | **evet** |
| k2 | çok iyi eşiği −0.040 → −0.060 | test_15, test_models_md_faz5_section | **evet** (2/2) |
| k3 | λ nihai "olası" aralığı (10, 100) → (10, 29) | test_15, test_models_md_faz5_section, test_report::test_models_md_is_up_to_date | **evet**, ama yalnız MODELS.md bayt-eşitliği yakalar (1 failed, 2 passed) → bulgu K4 |
| l1 | bootstrap tohumu 20260921 → 20260922 | test_t6 | **evet** |
| l2 | ay bloğu anahtarı YYYY-MM → YYYY | test_t6 | **evet** |
| m1 | n < 10 iken hücre üretimi (Faz 2C) | t1 küçük-n, real_no_cell_below_ten | **evet** (2/2) |
| m2 | sınıf mirası kırılır (hep LIVE) | t3, real_blocks_integrity | **evet** (2/2) |
| m3 | L < j arz paydaya girer | t5, real_blocks_integrity | **evet** (1 failed, 1 error) |
| m4 | PENDING hedef tek modelde SCORED | t4, real_pair_status_same | **evet** (2/2) |
| m5 | S_j = 0 tanımsız çift skorlanır | t5b | **evet** |

Faz 5: 18 koşu (12 istenen madde, a/g/i/k ikişer varyant), 17 kırmızı; Faz 2C: 5/5 kırmızı.

## 4. Bulgular ve öneriler

Kod düzeltmesi gerektiren (ret, sızıntı, hesap hatası) bulgu **yok**. Aşağıdakiler test/belge düzeyindedir; hiçbiri model_id'yi değiştirmez (kod ya da test değişikliği = aynı model_id; şartname metni değişikliği önerileri errata/yeni sürüm notudur, v0'ın kimliğine dokunmaz).

| # | Önem | Bulgu | Öneri | Tür |
|---|---|---|---|---|
| K3 | ÖNEMLİ (görev kuralı: kırmızı olmayan mutasyon) | (g2) `d1_lock`'un Decimal ham-metin eşitliği yerine float eşitliği koyulunca hiçbir test kırmızı olmuyor. Pratik risk: H99 ve gerçekçi bültenlerde binary64 çözünürlüğü içinde iki metin aynı float'a düşer; **eşdeğer mutant**. Korumasız kalan davranış: §2 "Decimal, ham metin; adım/yuvarlama uygulanmaz" kuralının aritmetik semantiği. | `test_2`'ye binary64'te ayırt edilemeyen ama Decimal'de farklı bir çift ekle (ör. "10.12" vs "10.1200000000000000001" → 0; "10.12" vs "10.120" → 1). Test; aynı model_id. | kodu şartnameye uydurma (test) |
| K4 | KÜÇÜK | (k3) `LAMBDA_FINAL_LIKELY`, `LAMBDA_FOLD_INF_SHARE`, `N_FOLDS_RANGE`, `LOCK_SIGN_SHARE` sabitleri `test_15`'te doğrulanmıyor; yalnız MODELS.md bayt-eşitliği (test_report) yakalıyor. | `test_15`'e sabitlerin şartname değerlerini ekle. Test; aynı model_id. | test |
| K1 | KÜÇÜK | H8: ret kodları şartname §9'daki `REFUSED_*` adları yerine B3 biçimi (öneksiz). Davranış aynı; okuyucular (EK 3, kayıt şeması §7.4) kod adlarını B3 biçimiyle yazmalı. | Şartnamenin bir sonraki sürümünde §9 tablosuna "kod alanı öneksiz, B3" notu (errata; v0 kimliği değişmez). | belge |
| K2 | KÜÇÜK | H9: `D1_FIELD_INVALID` şartnamede yok; yalnız bozuk bülten satırında (H99'da 0). | Aynı errata notu. | belge |
| K5 | KÜÇÜK | H22: `test_scoring.py` ve `test_faz4_ceiling_path.py`'deki varyant sayacı istisnası `scores.json` 72a000f'e bayt-eşitken geçerli; bir sonraki skor üretiminde kart sayacı 20 olmalı ve istisna kendiliğinden kapanmalı. | Canlı akış / skor üretimi görevinde istisnanın devre dışı kaldığını (kart 20) doğrulayan bir satır. | test |
| K6 | KÜÇÜK | Şartname §12 sözde kodu `eta = logit(base.hazard)` diyor; §3.1 ("aynı sayısal yol") ve §5 (d) (bit-eşitlik) ile çelişir. Opus doğru olanı seçti (H1). | Errata: §12'de `eta = linear_predictor(parent, inputs)` yazılmalı (yeni sürüm notu; kimlik değişmez). | belge |
| K7 | KÜÇÜK | H5: karar 4-4'ün lafzı ("model dosyaları sonuç commit'lerinin atası olmalı") ilk POST_D1 dondurmasında 7 arzın var olan sonuçları yüzünden bekçiyi kırmızı yapardı; Opus'un "sıralı olmalı (ata ya da torun), paralel dal ihlal" okuması doğru ve Faz 1 ilkesiyle (sonradan dondurulan model bağlanmaz, o arz RETRO) tutarlı. Ancak karar metni bunu söylemiyor. | Proje sahibi CLAUDE.md kural 1'e girecek cümleyi (karar 4-5) "…POST_D1 modeli, kendisinden sonra repoya giren her sonuç commit'inin atasıdır; önce girmiş sonuçlar o model için RETRO'dur" biçiminde yazarak okumayı onaylasın. | karar/belge |
| K8 | KÜÇÜK (bilgi) | Kazanç/kayıp/eşitlik "bit-eşit 0" kuralı yalnız aynı kod yolunda anlamlıdır; bağımsız yeniden üretim eşitlikleri üretemez (§1.3). | MODELS.md kural metnine "eşitlik yalnız aynı kod yolunda bit-eşit farkla (λ = INF fold'ları)" açıklaması; sayı değişmez. | belge |
| K9 | KÜÇÜK (bilgi) | Sızıntı (i)'nin lafzı "SESSIONS dosyasından yalnız 1. seansın fiyat/hacim sütunları okunur"; Faz 4 yükleyicisi ikincil çıktı için 2..10. seans kapanışlarını (kesimli) okur. Birincil çıktı etkilenmez; §6.1-6 bunu gerektirir. | Şartname erratası: (i) "D1 yükleyicisi için; path hücreleri SPEC_CEILING_PATH_V0 §8'e göre kesimli okur". | belge |

## 5. Tanı: "neden bu kadar iyi?" (model seçimine girmez) [ÖLÇTÜM + ÇIKARIM]

1. **Brier k = 2 kazancının kaynağı kilitsiz arzlardır.** 70 arzın 11'i kilitsiz (`d1_lock = 0`); fark toplamının %100.8'i onlardan (−3.61), kilitli 59 arzın katkısı ≈ 0 (+0.03). Gözlenen D2 kırılma: kilitli 0.034, kilitsiz **0.818**; ort h_2 model 0.081 / 0.556, karşılaştırıcı 0.080 / 0.154. En çok katkı veren 10 arzın 8'i kilitsiz, L = 1 (SMRVA, EGEGY, BIGEN, LILAK, MOPAS, KOTON, ORZAX, SOHOE; Δ −0.35 … −0.70).
2. **Ayırt etme, kalibrasyon değil.** Murphy ayrıştırması (0.05 kutu): model güvenilirlik 0.040 / çözünürlük 0.094; karşılaştırıcı 0.012 / 0.013; belirsizlik 0.132. Karşılaştırıcının ortalama kalibrasyon açığı² 0.0043 (toplam farkın %8'i); karşılaştırıcının h_2'si ortalamaya kaydırılsa Brier 0.1253 olur, model 0.0784: kalan −0.0469 (%92) ayırt etme payıdır. Yıllara göre: 2023 −0.001 (n 7), 2024 −0.063 (27), 2025 −0.095 (12), 2026 −0.030 (24) → tek döneme bağlı değil.
3. **k = 10'daki hafif kötüleşme (+0.0095) ve path D10 MAE (+0.0361) aynı mekanizmadan:** δ bütün d = 2..10'da ortaktır (§3.1 "orantılı etki, gün-grubu etkileşimi yok"). Kilitli arzlarda (z_lock = +0.40) logit −0.13 kayar; D2–D3'te doğru olan bu düşüş D4–D10'a da taşınır: kilitli arzlarda ort S_cond_10 model 0.294 vs karş. 0.270, gözlenen L ≥ 10 oranı tüm kümede 0.143. k = 10 farkı L < 10 olan 60 arzdan (+0.93), L = 10 olan 10 arz kazanır (−0.27). Path'te S_10 yükselince limit-yolu atomu (ρ_10 ≈ +1.59) medyanı 16 fold'da (karş. 10) ele geçiriyor; L < 10 arzlarda büyük hata. Duyarlılık bunu doğrular: yalnız `d1_lock` varyantında k = 10 farkı +0.0171 [+0.0057, +0.0302] (0'ı pozitif dışlar). Bu bir tasarım sonucudur (bütçe 2 parametre), hata değil; gün-grubu etkileşimi yeni model_id'dir.
4. **§5 beklentim neden düşük kaldı; 1B ve 4 ile ortak neden.** Beklentiyi iki-sınıf mekanikle türetirken sınıf hazard'larını a = 0.06–0.10 (kilitli), b = 0.36–0.62 (kilitsiz) varsaydım ve "ideal kazancın üçte biri–yarısı kalır" dedim. Gerçekte a = 0.034, b = 0.818: ideal iki-sınıf Brier 0.051, karşılaştırıcı 0.130 → ideal kazanç −0.078; gerçekleşen −0.051 ≈ ideal'in üçte ikisi. Yani büzme varsayımım doğru, **sınıf ayrımı varsayımım yanlış çapalanmıştı**: özellik–sonuç ilişkisine bakmadan yazılan şartname, kilidin D2 için neredeyse belirleyici olduğunu bilemezdi. Faz 1B'de f3–L ilişkisi (Spearman 0.55), Faz 4'te limit-yolu atomlarının gerçekleşen getiriye tam oturması aynı kalıptır: **H99'da tavan mekaniği, "ılımlı etki" öncüllerinden çok daha belirleyicidir; sonuç görülmeden yazılan beklentiler, çözünürlüğü (n = 70'te ±0.03) ve bilinen karşılaştırıcı sayılarını çapa alıp etkinin gücünü sistematik küçümsüyor.** Ayrıca üç fazda da tasarım H99 marjinallerine maruzdu (gün grupları, hücre grupları, kilit göstergesi profil_d1'den seçildi); tasarıma maruz backtest'te etkinin büyük görünmesi beklenir, kanıt değeri prospektiftedir. Ortak neden şartname kalibrasyonudur; kod ya da veri hatası değil.
5. **λ fold'lar beklentisi tutmadı** (INF 2/70): ilk 7 FIT_OK fold'da `d1_lock` σ = 0 ile düştü ama `d1_turnover` sonlu λ ile fit edildi; iç CV'de INF'i seçtiren "küçük eğitim kümesi" argümanım tek özellikte de tutmadı (0.1–10 aralığındaki λ'lar INF'den daha iyi CV skoru verdi). Beklentim, iki özelliğin birlikte gürültü olacağını varsaymıştı.

**Duyarlılık (bilgi; model DEĞİL, şartname değişmez; `ekler/sensitivity_runs.jsonl`, `sens_*_fold_ledger.csv`):**

| Varyant | Birincil RPS_1 − `ceiling_hazard_v0` | Brier k = 2 | Brier k = 10 | λ dağılımı |
|---|---|---|---|---|
| şartname v0 (iki özellik) | −0.0105 [−0.0264, +0.0058] | −0.0512 [−0.1010, −0.0097] | +0.0095 [−0.0034, +0.0233] | 3: 22, 10: 14, 30: 32, INF: 2 |
| yalnız `d1_lock` | −0.0074 [−0.0227, +0.0082] | −0.0561 [−0.1088, −0.0125] | **+0.0171 [+0.0057, +0.0302]** | 0.1: 19, 1: 1, 3: 15, 10: 28, INF: 7 |
| yalnız `d1_turnover` | −0.0064 [−0.0205, +0.0093] | −0.0252 [−0.0591, −0.0010] | +0.0023 [−0.0125, +0.0180] | 1: 7, 3: 19, 10: 10, 30: 32, INF: 2 |

Okuma: k = 2 kazancı kilit göstergesinden gelir (tek başına daha da büyük), k = 10 kötüleşmesi de ondan; el değiştirme tek başına kazancın yarısını verir ve k = 10'u bozmaz; birincil hücre her varyantta "ayırt edilemiyor". Hiçbir varyant hükmü değiştirmiyor.

## 6. Faz 2C koşullu skorlama (adım 4; canlı veri yalnız burada okundu) [ÖLÇTÜM]

**G1–G12 ↔ SPEC_CEILING_PATH_V0 §7 ve EK2 §5:** G1 (bütün D_{j+1}..D_10 girmeden skorlanmaz; PENDING ≠ TARGET_UNAVAILABLE; NA → TARGET_UNAVAILABLE) lafzın kendisi, muhafazakâr; G2 (S vektörü olan 9 tür blok alır) durum 3'ü liste değil ölçek notu okur — çelişki yok; G3 (karşılaştırılanlar koşulsuz bloğun aynası; @INF = S kaynağının sıfır modeli; `v1_5_p_up_as_ceiling` alınmadı) §7'nin kural listesiyle birebir; G4 (birincil = RPS_j vs iki KM) §7 karşılaştırılanı adlandırmadığından SPEC_SCORING §7 kalıbı, koşullu skor üretilmeden ilan edilmiş; G5 j = 9 tek hücre + iki satır alanı, iki metni birlikte sağlar; G6 S_j = 0 tanımsız (kayıp atanmaz) formülün gereği; G7 payda (D_1..D_j resmi etiketleri 1), `n_skipped` muhafazakâr, özdeşlikler (n_live + n_late = n_scored) EK2'nin bütünlük şartı; G8 sınıf AYNEN miras, RETRO satır olmaz; G9 ek alanlar EK2 "alan eklenebilir"; G10 `ScaleMixError` j karışımına da; G11 SCORES.md yalnız satır tablosu (§8); G12 gözlenen kapanış `close_raw` (Decimal). **Davranışı lafzın dışına çıkaran madde yok**; G1'in "hepsi girmeden skorlama yok" okuması skorlamayı geciktirir ama §7 metninin kendisidir.

**Bağımsız yeniden hesap (`ekler/faz2c_recompute.py`, borsai import edilmedi):** 9 modelin `models[].conditional` bloklarındaki bütün satırlar (j = 1..9; 144 satır: 6 S-tabanlı model × (5+5+5+4+3+1+1) + path modelleri 0 satır/RETRO sayımı) kayıtlardan (`registry/records/<T>/…json` S vektörleri) ve sonuçlardan (`data/outcomes/<T>.csv`) yeniden hesaplandı: `S_cond` (k = j+1..10), `rps_cond`, `brier_next`, `brier_10` (model ve dört kural), `status`, `target_status/reason`, `L`, `L_at_least`, sınıf ve kayıt kimliği (koşulsuz canlı satırla aynı), j başına 11 sayaç: **maks \|Δ\| = 0.0, uyuşmazlık 0**. n < 10 iken hiçbir j'de hücre yok (hücre sayısı 0); L < j hiçbir satırda yok (VEYAS, BKRGY L = 0 → payda dışı; CITAS L = 5 j ≤ 5; KPEKS L = 5; INTET L = 4; TKNKA L = 7); PENDING hedef (NETGL j = 1..3) ve bütün hedef durumları (ticker, j) başına 9 modelde aynı (24 çift). Sınıf mirası: 7 kaydın hepsi LATE_RECORD (kayıtlar 2026-09-22, D_1'lerden sonra → LIVE olamaz; koşulsuz satırla aynen). Orkestratörün `ceiling_hazard_v0` için bulduğu 2.8e-17 burada 0 (aynı float bölmesi).

**Mutasyonlar (m1–m5):** 5/5 kırmızı (§3).

## 7. Açık konular

1. K7: karar 4-4'ün yazılı ifadesi (CLAUDE.md kural 1 cümlesi, canlı akış commit'inde) Opus'un okumasını açıkça taşımalı; proje sahibi onayı.
2. Canlı POST_D1 akışı kurulurken H19 (bülten `OZEL ISLEM BILDIRIMI ISLEM ADEDI` alanı kayda) ve §7.4 kayıt şeması; bu denetimin kapsamı dışı (T10).
3. Dondurma görevi: `python -m borsai.freeze --models post_d1_hazard_v0` temiz ağaçta; önizlemeyle (`created_at`, `code_version`, `runtime` dışında) bit-eşitlik; `experiments/log.jsonl`'a `ekler/sensitivity_runs.jsonl`'daki 2 `kind: sensitivity` satırı eklenebilir; K3/K4 test sertleştirmeleri aynı commit'te olabilir (aynı model_id).
4. Bir sonraki model (yeni model_id, v0'dan sonra ve canlı n biriktikten sonra): δ'yı g2 günleriyle sınırlamak ya da gün-grubu etkileşimi (k ≥ 4 kötüleşmesini giderir); yalnız `d1_turnover` varyantı k = 10'u bozmayan ama k = 2'de yarı kazançlı bir alternatif.

## 8. Ekler (`ekler/`)

`repro_post_d1.py` (bağımsız betik), `repro_stdout.txt`, `repro_output.json`, `repro_post_d1_fold_ledger.csv` (benim ledger'ım, §6.1-8 sütunları), `repro_subprocess_check.txt`, `sens_lock_only_fold_ledger.csv`, `sens_turnover_only_fold_ledger.csv`, `sensitivity_runs.jsonl`, `runtime_file_trace.py` + `_out.txt` + `_out.json`, `sira_kanitlari.txt`, `t1_independent_check.py` + `_out.txt`, `mutate.sh`, `mutate_faz2c.sh`, `mutasyon_ciktilari.txt`, `faz2c_recompute.py` + `_out.txt` + `_out.json`, `pytest_out.txt`, `koruma_once.txt`, `koruma_sonra.txt`. Toplam < 1 MB.

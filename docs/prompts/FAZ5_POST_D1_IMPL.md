# TASK_ID: BORSAI_FAZ5_POST_D1_IMPL_20260924

Model: Opus 5.5 (arayüzdeki en yeni Opus) · Extra. Klasör: ~/Desktop/BorsAi. Ağ gerekmez. push/tag/amend yok.

## Bağlam
- Fable'ın şartnamesi `docs/specs_faz5/SPEC_POST_D1_V0.md` (+ `ekler/`). Commit `c20c092`, push kanıtı 2026-09-24T00:44:25Z. Dosya sha256 `a5b4675d84784b4a9db9c3b0f7fe3b6a1c1014e823c66b237b4613b51f7ead34`. Önceden yazılmış beklenti §5'te, sonuç görülmeden yazıldı.
- Kurulacak tek model: `post_d1_hazard_v0`. Dondurulmuş `ceiling_hazard_v0`'ın doğrusal öngörücüsü sabit ofset; d = 2..10 hazard'ına δ ∈ R² (`d1_lock`, `d1_turnover`); λ ızgarası + iç arz-bırak CV. λ = INF ucu karşılaştırıcının kendisidir.
- Bu görev: **uygulama + walk-forward backtest + rapor.** Dondurma YOK (Fable yeniden üretim ve denetimden sonra ayrı görev). Canlı POST_D1 akışı YOK (koşullu, aşağıda). Uygulamaya (`app/`) dokunulmaz.
- Orkestratörün ölçtükleri (2026-09-24, HEAD `72a000f`):
  - `data/training_table.csv` 99 arz; f3 dolu ve `ceiling_close_D1 = 1`: **81**. Bunların `d1_lock` (ham metin Decimal, `thb_raw_low == thm_raw_upper_limit`): **70/81**.
  - SESSIONS dosyası (`data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv`) `session_number == 1`: 99 satır; `session_type` 99/99 `OPEN_FULL_DAY`; `security_trading_status` 99/99 `ACTIVE_NOT_SUSPENDED`; 99/99 `thb_raw_trade_count > 0`. Şartnamedeki `half_day` / `halt` alanları bu dosyada bu iki sütundur (eşlemeyi sen yaz).
  - Faz 1B tavan ledger'ı `tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv`: 87 fold, 87 `FIT_OK`, `realized_L ≥ 1` olan test arzı **71** (şartname §11-4 ile aynı). Değerler repr biçiminde (float gidiş-dönüşü kayıpsız).
  - `docs/MODELS.md` "Koşullu güncelleme (keşif): H99, j = 1..9" tablosunun j = 1 satırı: n = 71, RPS_1 0.1706 ve dört fark (şartname §5'teki sayılar).

## Proje sahibinin Faz 5 kararları (bağlayıcı; aynen)
2026-09-24 03:47:
1. Şartname §13'ün 5 açık sorusu, Fable önerileriyle: (1) POST_D1 zaman sınırı **D1'i izleyen ilk resmi seans günü 09:40:00 Europe/Istanbul**; (2) PB/f3'süz varyant (`pb_post_d1_hazard_v0`) sonra, ayrı model_id; (3) D1 tavan kapatmayan arzlar v0'da kapsam dışı; (4) POST_Dj (j ≥ 2) canlı n ≥ 10 olmadan açılmaz; (5) `path_conditional` v0'da kalır, ikincil çıktı, birincil hücreyi etkilemez.
2. **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.**
3. **Canlı akış koşullu:** backtest'te şartname §5 başarısızlık (b) gerçekleşirse (nihai fit λ = INF, ya da fold'ların ≥ %80'inde INF) model yine dondurulur ama canlı POST_D1 akışı (outcomes/registry/freeze genişlemesi) şimdi kurulmaz. λ sonlu ve (b) yoksa kurulur. Bu görev yalnız (b)'nin gerçekleşip gerçekleşmediğini ölçer ve yazar.

2026-09-24 ~12:30 (orkestratörün sorusuna cevap; gerekçe: INDEX.json değişirse uygulamanın dondur sihirbazı `INDEX_SHA` ile durur (`app/src-tauri/src/commands/freeze.rs` 68–71) ve yeniden derlenirse Rust yeni algoritmayı `Kind::Rule`'a düşürür (`crates/borsai_predict/src/params.rs` `model_kind`); orkestratör ikisini de kodda gördü):
4. **POST_D1 modelleri ayrı dizinde:**
   1. Dosya `models/INDEX_POST_D1.json`, şema `borsai.model_index/1`. `models/INDEX.json` ve listeleme öncesi kayıtlar değişmez.
   2. `docs/SPEC_DEVIATIONS.md`'ye Faz 5 sapma satırı: şartname §6.2 "INDEX.json sonuna" yerine ayrı dizin. Model kimliğini değiştirmez (§1.1 listesinde yok), sonuç görülmeden karar verildi.
   3. POST_D1 kaydının `models_index` alanı bu dosyayı gösterir. Parent (`ceiling_hazard_v0`) sha'sı `INDEX.json` ile denetlenir.
   4. Sıra kuralı bekçisi (`tests/test_outcome_guard.py`) ve skorlama iki dizini birlikte okur; yeni dizindeki model dosyaları da sonuç commit'lerinin atası olmalı.
   5. CLAUDE.md kural 1'e canlı akış commit'inde girecek cümle: "Her kayıt kendi aşamasının dizinindeki tüm modelleri içerir (listeleme öncesi: models/INDEX.json; POST_D1: models/INDEX_POST_D1.json). POST_D1 kaydının zaman sınırı D1'i izleyen ilk seans günü 09:40 (Europe/Istanbul), zaman kanıtı push kanıtıdır." **Bu görevde CLAUDE.md'ye dokunma.**
   6. Uygulama ikinci dizini EK 3'te okur. O zamana kadar uygulama 19 modelle aynen çalışır.

## Orkestratörün bulduğu noktalar (kodda ölçüldü)
- O1 `borsai/freeze.py` `model_kind`: tanımadığı algoritmayı `"rule"` sayar; `run_model` onu V1.5 doğrusal yoluna yollar. POST_D1 modeli `INDEX.json`'a girseydi listeleme öncesi `build_record` kırılırdı. Karar 4 bunu çözer; bu görevde ayrı dizin desteği yazılır (T4).
- O2 `borsai/outcomes.py` `sequence_guard` (397–403) ve `tests/test_outcome_guard.py` (74) yalnız `INDEX.json`'u okur (karar 4-4).
- O3 `borsai/predict_hazard.py` `predict` doğrusal öngörücüyü (`lin`, `gamma`) dışarı vermiyor. Şartname §12 sözde kodu `eta = logit(base.hazard)` diyor; bu gidiş-dönüş bit-eşit değildir, §5 (d) ise INF ucunun ve h_1'in bit-eşit olmasını ister (T1, T2).
- O4 Şartname §3.5 model JSON'unda `parent: {model_id, file, sha256, gamma, beta, preprocessing_id}` diyor; ofseti hesaplamak için parent'ın ön işleme sabitleri (winsor, ortalama, std), `feature_ranges` ve `reclose_rates` de gerekir (T3).

## Görev kararları (Fable denetimi bunları şartname sayar; `docs/SPEC_DEVIATIONS.md` yeni "H. Faz 5" bölümüne H1… olarak yaz)
- **T1 Ofset yolu.** `predict_hazard.py`'ye davranışı değiştirmeyen bir yardımcı çıkar (ör. `linear_predictor(params, inputs)` → özellikler, z, `lin`, uyarılar/ret) ve `predict` onu kullansın; `predict_post_d1` aynı yardımcıyla η_d = γ_{g(d)} + lin hesaplar. `logit(hazard)` geri dönüşümü YASAK. Kanıt: INDEX'teki bütün `hazard` ve `km` türü modellerin çıktıları (hazard, S, P_L, P_close_ceiling, uyarılar, ret) **bit-eşit** (`==`): (i) 7 resmi kayıtta saklı çıktılarla (`registry/records/`, kaydın `model_inputs`'u ile yeniden çalıştırarak); (ii) H99'un 99 arzında, refactor'dan ÖNCE üretilip A'ya fixture olarak giren anlık görüntüyle. Rust tarafı ve `app/` değişmez.
- **T2 INF bit-eşitliği.** Donmuş tahmin yolunda δ = 0 iken `predict_post_d1`'in hazard[2..10], S ve `conditional_weights(S, 1)` çıktısı `ceiling_hazard_v0`'ınkiyle **bit-eşit** (`==`; 81 eğitim arzı + 1000 rastgele girdi). Test 5'in 1e-12 toleransı yalnız `S_cond` ile çarpım formülü (Π(1 − h_d)) karşılaştırması için kalır. Kodda δ = 0 için özel dal (erken dönüş) OLMAZ; eşitlik genel yoldan gelmeli (Fable mutasyonla bakacak). h_1 her koşulda ana modelden kopya.
- **T3 Parent parametreleri.** `predict_post_d1` parent parametrelerini (`models/ceiling_hazard_v0.json` nesnesinin tamamı) ve `path_conditional` için `ceiling_path_v0` parametrelerini açık argüman olarak alır. Post-D1 JSON'u parent dosyasının sha256'sını ve §3.5'teki kopya alanları taşır; `predict_post_d1` kopya alanlar verilen parent'la birebir eşit değilse `PARAMS_INVALID` verir. Dosyayı yükleyip sha'yı `INDEX.json` ile denetlemek çağıranın işi (backtest, ileride freeze). Başka bir yol seçersen gerekçesini H'ye yaz; ofsetin sayıları tek kaynaktan gelmeli.
- **T4 Ayrı dizin desteği (karar 4), gerçek dosya oluşturmadan.**
  - `borsai/freeze.py`: `INDEX_POST_D1_PATH`; `freeze()` `stage == "POST_D1"` modelleri yalnız `INDEX_POST_D1.json`'a ekler (yoksa oluşturur, şema `borsai.model_index/1`), `INDEX.json`'a asla. Ön koşul: parent `ceiling_hazard_v0.json` ve `ceiling_path_v0.json` sha'ları `INDEX.json` ile eşit; değilse `FreezeError`.
  - Listeleme öncesi `build_record` yalnız `INDEX.json`'u okur (bugünkü davranış). Test: geçici dizinde sahte bir `INDEX_POST_D1.json` varken listeleme öncesi kayıt, zaman damgaları dışında bayt-eşit.
  - `outcomes.sequence_guard`: `INDEX_POST_D1.json` varsa o ve listelediği model dosyaları da commit'li olmalı. Geçici git deposunda sentetik test (commit'siz POST_D1 model dosyası → indirme durur).
  - `tests/test_outcome_guard.py`: `INDEX_POST_D1.json` varsa ondaki model dosyaları da sonuç commit'lerinin atası olmalı; sentetik kırmızı örnek.
  - Skorlama: bu görevde `scores.json` üretimi değişmez. Test: sahte `INDEX_POST_D1.json` varken `build_scores` çıktısı `generated_at_utc` ve `code` dışında aynı. POST_D1 kayıtlarının skorlanması (iki dizini birlikte okuma) canlı akış görevinde.
  - Gerçek `models/` altına hiçbir şey yazılmaz; `models/INDEX_POST_D1.json` bu görevde OLUŞMAZ.
- **T5 İki commit, sıra.** A = kod + birim/sentetik testler + §5 beklenti tablosunun kod karşılığı (tablo ayrıştırma, "tuttu / tutmadı" kuralları, "çok iyi" eşikleri, (a)–(d) kuralları; `OPERATIONAL_RULES_FAZ5`) + T4 + SPEC_DEVIATIONS H. A'da hiçbir walk-forward skoru ve nihai fit sayısı yok. **Gerçek veride walk-forward ve nihai fit ilk kez A commit edildikten sonra koşar**; hata ayıklama sentetik veriyle. Karşılaştırıcı ve veri tanımı testleri (§11-1, 2, 3, 4, 8; T6) A'da gerçek veriyle koşabilir, bunlar yeni modelin sonucu değildir. Gerçek nihai fit isteyen testler (ör. §11-10'un 81 arzlık hâli) B'ye; A'da aynı test elle verilmiş sabit δ ile koşar. A'dan sonra kod hatası çıkarsa ayrı düzeltme commit'i (A2) ve mesajında ne değiştiği; düzeltme §5 değerlendirme kurallarına ya da eşiklere dokunuyorsa DUR, B'yi atma, raporla. B = backtest koşusu + altın ledger + deney günlüğü + MODELS.md Faz 5 bölümü + altını okuyan testler. A (ve varsa A2), B'nin atası.
- **T6 Karşılaştırıcı yeniden üretimi (A'da test).** Faz 1B ledger'larından ve ortak fonksiyonlardan (`predict_path.conditional_rps`, `conditional_brier`, MODELS.md aralık yöntemi) MODELS.md j = 1 satırı yeniden üretilir: n = 71, RPS_1 ve dört fark + aralık, basılı hassasiyette birebir. Tutmazsa DUR: karşılaştırıcı tanımı Faz 4 ile aynı değil demektir.
- **T7 INF fold'ları.** λ = INF seçilen her fold'da modelin S_cond'u ile aynı fold'un karşılaştırıcı S_cond'u arasındaki en büyük |Δ| raporlanır (beklenen 0). Sıfır değilse nedenini yaz; kazanç/kayıp/eşitlik sayımı var olan MODELS.md kuralıyla, yeni kural icat etme.
- **T8 Nihai fit önizlemesi.** B'de 81 arzla nihai fit dondurmanın kullanacağı fonksiyonla koşulur; λ, δ, λ skor tablosu, satır/olay sayısı MODELS.md Faz 5 bölümüne ve rapora yazılır. `models/`'e yazılmaz. Dondurma görevi bu önizlemeyle bit-eşitliği sınayacak.
- **T9 Başarısızlık (b)'nin paydası:** "fold'ların ≥ %80'i" = δ fit'i yapılan (`FIT_OK`) fold'lar; `INSUFFICIENT_TRAINING_HISTORY` ve `NOT_APPLICABLE` paydaya girmez. Rapor iki sayıyı da verir.
- **T10 Kapsam dışı kabul testleri:** §11-13 (POST_D1 kayıt ve canlı sınıf) ve §11-16 (uygulama) canlı akış ve EK 3 görevlerinde. §11-14'ün `registry/post_d1/` bekçisi de canlı akışta; geri kalanı bu görevde.
- **T11 Şartname pini:** `docs/specs_faz5/` `c20c092`'deki hâliyle bayt-eşit (Faz 4'ün `SPEC_COMMIT` testi kalıbı); `docs/specs/` 11 dosya ve temiz; `docs/specs_faz4/` bayt-eşit.

Şartnamede başka boşluk ya da iki okumalı yer bulursan: lafza göre karar ver, sonuç verisine bakarak seçim yapma, H'ye yaz.

ÖNCE OKU:
- CLAUDE.md
- docs/specs_faz5/SPEC_POST_D1_V0.md (tamamı, bağlayıcı) ve `ekler/` (`m5_d1_profil.py`, `profil_d1.txt`)
- docs/specs/SPEC_CEILING_V0.md (§2, §4, §5, §8, §9, §12), docs/specs/SPEC_SCORING.md (§1–§3, §8)
- docs/specs_faz4/SPEC_CEILING_PATH_V0.md §7, §8
- docs/SPEC_DEVIATIONS.md (A2, C7, F, G)
- docs/prompts/FAZ4_CEILING_PATH_IMPL.md ve docs/prompts/FAZ2C_CONDITIONAL_SCORING.md (kalıp)
- borsai/: predict_hazard.py, hazard.py, survival.py, preprocess.py, predict_path.py (koşullu fonksiyonlar), ceiling_path.py (§7 keşif bölümü), backtest.py (`plan_ceiling_folds`, `_run_hazard`, `append_log`, `run_backtest`), report_faz4.py (beklenti ayrıştırma kalıbı), freeze.py, outcomes.py (`sequence_guard`), specs.py, metrics.py
- tests/test_faz4_ceiling_path.py (bekçi ve pin kalıpları), tests/test_outcome_guard.py
- tests/reference/macos_golden_faz1b/ (ceiling_hazard_v0, @INF, base_km_expanding, base_km_last10, base_always_ceiling__ceiling ledger'ları), tests/reference/macos_golden_faz4/ceiling_path_v0_fold_ledger.csv

## Adımlar
0. **Taban**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3` ve `git status --porcelain`. Beklenen HEAD `72a000f` (ya da onun torunu).
   - İzinli izlenmeyen: yalnız `docs/prompts/FAZ5_POST_D1_IMPL.md`. Başka bir şey varsa DUR.
   - `.venv/bin/pytest -q` tam koşu; sayı ve süreyi yaz, son satırları `docs/faz5/ekler/test_runs.txt`'ye ekle. Kırmızı varsa DUR.
1. **Tanım eşlemesi (kod yazmadan):** şartname §1–§6, §9, §11–§12'nin her maddesini koddaki karşılığına (dosya:fonksiyon) eşleyen tablo. T1–T11 ve bulduğun yeni kararlar H'ye.
2. **Uygulama** (şartnameyi DEĞİŞTİRME)
   - Stdlib tahmin: `predict_post_d1` (yalnız stdlib + `predict_hazard` / `survival` / `predict_path`; numpy yok, Faz 1A K2 import kalıbı). Çıktı: standart hazard şeması + `conditional_j1 {S_cond, p_break_next, P_L_cond}` (tek tanım `conditional_weights`) + `path_conditional` (tek tanım `predict_path.conditional`) ya da `null`.
   - D1 özellikleri: ham metinden Decimal; `d1_lock`, `d1_turnover`; §2 ret/uyarı tablosunun tamamı; `WARN_D1_LOCK_INCONSISTENT`.
   - Fit (numpy): ofsetli Newton (SPEC_CEILING_V0 §5, A2), λ ızgarası, iç arz-bırak CV, fold içi ön işleme; SESSIONS yükleyicisi sütun beyaz listesiyle (2..10. seanslardan yalnız `target_session_date`).
   - Model tanımı `specs.py`'ye (Faz 5 spec belgesi + sha pini), `model_kind`'a `"post_d1"`.
   - T4 ayrı dizin desteği.
   - `ScaleMixError`: bu modelin hücreleri `scale = backtest_conditional`.
3. **Testler (A):** şartname §11'in 1–12'si, §11-14'ün bu göreve düşen kısmı, §11-15'in kod tarafı; T1, T2, T4, T6, T11 testleri. Tam pytest yeşil → `docs/faz5/ekler/test_runs.txt`'ye son satırlar → **commit A**.
4. **Backtest (B)** (§6): PLAN_POST_D1; her fold'da ofset paritesi (test 3); `path_conditional` ceiling_path_v0 fold'u `OK` ise; ledger sütunları §6.1-8 sırasıyla; altın ledger `tests/reference/macos_golden_faz5/` (+ `MANIFEST.json`, `SHA256SUMS`, Faz 4 kalıbı); `experiments/log.jsonl`'a `kind: backtest` (`spec_sha256`, `survival_ledger_sha256`, `plan_id`). Nihai fit önizlemesi (T8).
5. **MODELS.md "Faz 5: D1 sonrası güncelleme" bölümü** (üretilmiş rapor; mevcut bölümlere dokunma; koşullu ölçek, koşulsuz tablolarla toplanmaz):
   - §4'teki bütün hücreler: fark, %95 aralık, n, kazanç/kayıp/eşitlik; birincil hücre ayrıca vurgulu.
   - §5 beklenti tablosunun HER satırı gerçekleşenle yan yana: "tuttu / tutmadı" (ve yön).
   - Başarısızlık (a)–(d) tek tek; (b) için nihai λ ve INF payı (T9) açıkça: "canlı akış koşulu: kurulur / kurulmaz".
   - "Beklentiden çok iyi" denetimi (§5 tanımı: birincil fark < −0.040, ya da aralığın üst ucu < −0.020, ya da Brier k = 2 farkı < −0.040): sonucu yaz. Tetiklense de tetiklenmese de sıradaki adım Fable'ın sıfırdan yeniden üretimidir.
   - Fold özeti: fold sayısı, `FIT_OK` / `INSUFFICIENT_TRAINING_HISTORY` / `NOT_APPLICABLE`, λ dağılımı, δ işaretleri; T7.
6. **(d) parite hatası** (INF ucu ya da h_1 bit-eşit değil): kodu şartnameye uydur (aynı model_id). Gideremezsen DUR, B'yi atma.
7. Testler (B): altın ledger'ı okuyan testler; tam pytest yeşil → `test_runs.txt` → **commit B**.
8. Rapor.

Tek oturumda bitmezse: A yeşil ve commit'liyse orada dur, B'yi raporda bırak. A da bitmediyse yalnız yeşil kısmı `BORSAI_FAZ5_A (partial): …` mesajıyla commit et ve kalanı yaz.

## Kurallar
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.**
- Yazılabilir: `borsai/`, `tests/` (yeni dosyalar, `tests/reference/macos_golden_faz5/` ve T4 için `tests/test_outcome_guard.py`; başka mevcut test dosyasını değiştirmen gerekirse nedenini H'ye yaz), `experiments/log.jsonl` (yalnız ekleme), `docs/MODELS.md` (yalnız yeni bölüm), `docs/SPEC_DEVIATIONS.md` (yalnız H bölümü), `docs/faz5/` (rapor ve ekler), bu görev dosyası.
- Salt okunur: `CLAUDE.md`, `docs/specs/`, `docs/specs_faz4/`, `docs/specs_faz5/`, `docs/app/`, `app/`, `models/`, `registry/`, `data/`, `scores/`, `docs/SCORES.md`, `legacy/`, `tests/reference/` altındaki mevcut dosyalar.
- Mevcut 19 modelin çıktıları, altın ledger'ları ve `scores.json` değişmez. Yeni model dondurulmaz; `models/INDEX_POST_D1.json` oluşmaz.
- 2026-08-19 sonrası veri eğitime girmez. SESSIONS'tan yalnız 1. seansın fiyat/hacim alanları okunur.
- Testi gevşetme. Kök nedeni bul; gerekirse DUR.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma (`tests/test_outcome_guard.py`).
- `git add -A` yok. Commit'ler (yalnız kendi yolların):
  ```
  git add borsai tests docs/SPEC_DEVIATIONS.md docs/faz5 docs/prompts/FAZ5_POST_D1_IMPL.md
  git commit -m "BORSAI_FAZ5_A: post_d1_hazard_v0 code, tests, expectation rules and separate POST_D1 model index support, no backtest results" -- borsai tests docs/SPEC_DEVIATIONS.md docs/faz5 docs/prompts/FAZ5_POST_D1_IMPL.md
  git add tests experiments/log.jsonl docs/MODELS.md docs/faz5
  git commit -m "BORSAI_FAZ5_B: post_d1_hazard_v0 walk-forward backtest, golden ledger and MODELS.md Faz 5 section (not frozen)" -- tests experiments/log.jsonl docs/MODELS.md docs/faz5
  ```
  A2 gerekirse: `BORSAI_FAZ5_A_FIX: <ne değişti>` ile yalnız ilgili yollar. B `borsai/`'yi değiştirmez; gerekiyorsa o bir A2'dir.
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Rapor Türkçe.

## Teslim (rapor)
Raporu hem sohbete hem **`docs/faz5/IMPL_RAPOR.md`**'ye yaz (orkestratör sohbeti görmez, diskten okur); commit B'ye (B yoksa A'ya) girer. İçerik:
- Commit hash'leri, `git show --stat`, A'nın B'nin atası olduğu.
- Tanım eşleme tablosu; H kararları.
- Test sayıları: taban / A / B (sayı, süre); ham son satırlar `docs/faz5/ekler/test_runs.txt`'de.
- Kabul testleri 1–12, 14 (bu göreve düşen), 15 ve T1, T2, T4, T6, T11 sonuçları.
- T1 kanıtı: kaç model × kaç girdi bit-eşit.
- Fold özeti ve T7.
- Birincil hücre ve bütün §4 hücreleri; §5 satır satır "tuttu / tutmadı".
- (a)–(d); (b) ve "canlı akış koşulu" hükmü; "çok iyi" denetimi.
- Nihai fit önizlemesi (λ, δ, skor tablosu).
- Altın ledger ve günlük satırının sha256'ları.
- Sapmalar, açık noktalar, Fable denetimine notlar.

## Kabul kapısı
- K1 Kabul testleri (1–12, 14'ün bu göreve düşen kısmı, 15) ve T testleri yeşil; tam pytest yeşil, eski testler dahil.
- K2 `models/` (19 dosya + INDEX.json), `tests/reference/` mevcut dosyalar, `scores/`, `registry/`, `data/`, `app/`, `docs/specs*` bayt-eşit; `models/INDEX_POST_D1.json` yok.
- K3 T1 (hazard/km modellerinin çıktıları refactor öncesiyle bit-eşit) ve T2 (INF ucu ve h_1 bit-eşit) kanıtlı.
- K4 §5 beklenti karşılaştırması satır satır yazılı; (a)–(d) ve (b) hükmü yazılı; (d) varsa B yok.
- K5 A (ve A2), B'nin atası; değerlendirme kuralları A'da; commit'ler yalnız izinli yollarda; push yok.

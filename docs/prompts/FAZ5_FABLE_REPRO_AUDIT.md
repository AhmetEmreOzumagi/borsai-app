# TASK_ID: BORSAI_FAZ5_FABLE_REPRO_AUDIT_20260924

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi. Ağ gerekmez.
- Git: YALNIZ okuma komutları ve her zaman `GIT_OPTIONAL_LOCKS=0` öneki (`log`, `show`, `diff`, `status --porcelain`, `merge-base --is-ancestor`, `clone --local`). Sonda tek commit, yalnız kendi yollarınla. push/tag/amend yok.
- Yazma: YALNIZ `docs/fable_faz5_audit/` (AUDIT.md ve `ekler/`) ve bu görev dosyası. Geçici işler (klon, mutasyon kopyaları, büyük çıktılar) `/tmp/borsai_faz5_audit/` altında. `ekler/` toplamı ≤ 3 MB.
- Paralel oturum yok. Koşu öncesi ve sonrası `git status --porcelain` ve `registry/`, `data/`, `scores/`, `models/` ağaç sha'larını ölç; eşit olmalı.

## Bağlam
- Senin şartnamen `docs/specs_faz5/SPEC_POST_D1_V0.md`: commit `c20c092`, push kanıtı `created_at` 2026-09-24T00:44:25Z, dosya sha256 `a5b4675d84784b4a9db9c3b0f7fe3b6a1c1014e823c66b237b4613b51f7ead34`.
- Uygulama Opus'a ait (görev `docs/prompts/FAZ5_POST_D1_IMPL.md`):
  - `7ce0593` (A, 2026-09-24T14:53:40+03:00): kod, testler, §5 değerlendirme kuralları (`borsai/report_faz5.py: OPERATIONAL_RULES_FAZ5`, eşikler), ayrı POST_D1 dizin desteği, SPEC_DEVIATIONS H1–H22. Sonuç yok.
  - `7d08169` (B): walk-forward, altın ledger `tests/reference/macos_golden_faz5/`, nihai fit önizlemesi (dondurulmadı), `experiments/log.jsonl` 65. satır, MODELS.md "Faz 5" bölümü, rapor `docs/faz5/IMPL_RAPOR.md`.
- Opus'un sonuçları (backtest, tasarıma maruz, n = 70, 22 ay):
  - Birincil koşullu RPS_1, `ceiling_hazard_v0` koşulluya karşı: **−0.0105 [−0.0264, +0.0058]** → ayırt edilemiyor (beklentin tuttu).
  - Brier k = 2: **−0.0512 [−0.1010, −0.0097]** → §5 "beklentiden çok iyi" **TETİKLENDİ** (tek koşul: < −0.040).
  - Brier k = 10: +0.0095 [−0.0034, +0.0233]. `path_conditional` D10 MAE +0.0361 [+0.0002, +0.0767] (karşılaştırılan iyi).
  - Nihai fit önizlemesi λ = 30, δ_lock −0.3279, δ_turn +0.2511. Fold'lar: FIT_OK 70, INSUFFICIENT 1 (EKOS), NOT_APPLICABLE 16; INF 2/70.
  - (a)–(d) yok → **canlı akış koşulu: kurulur.** Bu hüküm sıradaki büyük işi (canlı POST_D1 akışı) belirler; bağımsız teyit et.
- Orkestratör §4'ün 15 hücresini (fark, aralık, n, kazanç/kayıp/eşitlik) altın ledger + Faz 1B ledger'larından kendi betiğiyle yeniden hesapladı: basılı hassasiyette hepsi tuttu. Bu, Opus'un kendi ledger'ından hesaptır; **bağımsız yeniden üretimin yerini TUTMAZ.**
- Şartname §5: "çok iyi" tetiklendiğinden dondurmadan önce senin sıfırdan yeniden üretimin zorunlu ve ledger'lar **|Δ| ≤ 1e-9** eşleşmeli.

## Proje sahibi kararları (bağlayıcı; şartname sayılır)
1. §13'ün 5 sorusu: (1) POST_D1 zaman sınırı D1'i izleyen ilk resmi seans günü 09:40:00 Europe/Istanbul; (2) `pb_post_d1_hazard_v0` sonra, ayrı model_id; (3) D1 tavan kapatmayanlar v0'da kapsam dışı; (4) POST_Dj (j ≥ 2) canlı n ≥ 10 olmadan açılmaz; (5) `path_conditional` v0'da kalır, ikincil.
2. **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.**
3. Canlı akış koşullu: §5 (b) gerçekleşirse (nihai λ = INF ya da fold'ların ≥ %80'inde INF) model dondurulur ama canlı akış kurulmaz.
4. POST_D1 modelleri ayrı dizinde: `models/INDEX_POST_D1.json` (şema `borsai.model_index/1`); `INDEX.json` ve listeleme öncesi kayıtlar değişmez; POST_D1 kaydının `models_index`'i bu dosyayı gösterir, parent sha'sı `INDEX.json` ile denetlenir; sıra bekçisi ve skorlama iki dizini birlikte okur; uygulama ikinci dizini EK 3'te okur. (SPEC_DEVIATIONS H4 sapması.)
- Görev dosyasındaki T1–T11 görev kararları ve H1–H22 de şartname sayılır; ama her birinin davranışı değiştirip değiştirmediğini ve şartnamenin lafzıyla çelişip çelişmediğini sen değerlendir.
- H5 (karar 4-4'ün bekçi okuması: sonradan gelen sonuç modelin torunu olmalı, önceden gelenler o arz için RETRO) orkestratörce kabul edildi, proje sahibi itiraz etmedikçe geçerli. Doğru mu, açık mı, değerlendir.

ÖNCE OKU:
- CLAUDE.md
- docs/specs_faz5/SPEC_POST_D1_V0.md ve `ekler/`
- docs/specs/SPEC_CEILING_V0.md, docs/specs/SPEC_SCORING.md §1–§3, §5–§8
- docs/specs_faz4/SPEC_CEILING_PATH_V0.md §7, §8; docs/app/SPEC_APP_EK2.md §5
- docs/SPEC_DEVIATIONS.md: A2, C6, C7, G, H
- docs/prompts/FAZ5_POST_D1_IMPL.md (T1–T11), docs/faz5/IMPL_RAPOR.md, docs/faz5/TANIM_ESLEME.md, docs/MODELS.md Faz 5 bölümü
- Kendi önceki denetimlerin (kalıp): docs/fable_conformity_20260922/ (1B, `independent_repro.py`), docs/fable_faz4_audit/ (Faz 4, `repro_ceiling_path.py`, `runtime_file_trace.py`), docs/fable_app_audit/ekler/mutate.sh (mutasyon sürücüsü)
- Denetlenecek kod (yeniden üretimde KULLANILMAZ): borsai/post_d1.py, predict_post_d1.py, report_faz5.py, predict_hazard.py (`linear_predictor`), hazard.py (`linear_predictors`), freeze.py (`freeze_post_d1`), outcomes.py (`sequence_guard`), scoring.py (`sequence_violations`), specs.py; tests/test_faz5_post_d1.py, test_faz5_golden.py, faz5_support.py, test_outcome_guard.py

## Adımlar
Sıra önemli: 1–3 canlı sonuç verisine bakmadan yapılır; 4 (Faz 2C) canlı veriyi okur ve en sona kalır.

**1. Sıfırdan yeniden üretim** — `docs/fable_faz5_audit/ekler/repro_post_d1.py`
- `borsai` paketini IMPORT ETMEZ (stdlib, gerekirse numpy). Yalnız şartnameden kodlanır. Faz 1B'deki kendi bağımsız betiğinin (ana model ön işlemesi, PP satırları) parçalarını kullanabilirsin.
- Girdiler (yalnız H99, ≤ 2026-08-19): `data/training_table.csv`; SESSIONS dosyası (1. seansın ham D1 alanları; 2..10. seanslardan yalnız `target_session_date`); Faz 1B altın ledger'ları (parent γ/β/λ ve karşılaştırıcıların S'i: `ceiling_hazard_v0`, `@INF`, `base_km_expanding`, `base_km_last10`, `base_always_ceiling__ceiling`); `models/ceiling_hazard_v0.json` (nihai fit ofseti); `path_conditional` için Faz 4 ledger'ı ve kendi Faz 4 betiğin.
- **Bütün fold'lar** (87) ve nihai fit (81 arz). Bağımsız hesaplanacaklar: parent ofseti (fold başına ön işleme dahil), D1 özellikleri (ham metin Decimal), fold içi D1 ön işlemesi (Type-7 kırpma, z), ofsetli Newton, iç arz-bırak CV ve λ seçimi (eşitlikte büyük λ), test tahmini, S, S_cond, P_L_cond.
- Karşılaştırmalar:
  - (a) Fold ledger'ı `tests/reference/macos_golden_faz5/post_d1_hazard_v0_fold_ledger.csv` ile: `status` ve `selected_lambda` birebir; `delta_*`, `d1_clip_*`, `d1_mean_*`, `d1_std_*`, `test_d1_*`, `hazard_1..10`, `S_1..10`, `S_cond_2..10`, `lambda_score_table` değerleri |Δ| ≤ 1e-9; `training_n_*` birebir.
  - (b) Nihai fit önizlemesi `post_d1_hazard_v0_final_fit_preview.json` ile: λ birebir, δ, kırpma, μ/σ, skor tablosu |Δ| ≤ 1e-9; 409 satır, 67 olay, 342 sağ kalım.
  - (c) §4'ün bütün hücreleri ve §5'in 18 satırı: fark, %95 aralık (C7: ilk işlem ayı blokları, 4000, `random.Random(20260921)`, alt/üst indeks 100/3899), n, kazanç/kayıp/eşitlik → MODELS.md ile fark ve aralık uçları |Δ| ≤ 1e-9.
  - (d) "Çok iyi" denetiminin üç koşulu, (a)–(d) başarısızlıkları, (b)'nin paydası (T9) ve **canlı akış koşulu** hükmü.
  - (e) `path_conditional` h = 3, 5, 10 medyan ve p_up (ikincil). Yapamazsan nedenini yaz; FREEZE hükmü birincil ve S tarafına dayanır.
- Tutmayan her şeyin kök nedenini ölç: senin kodun mu, Opus'unki mi, şartname belirsizliği mi. Tahmin etme.

**2. Sızıntı ve uygunluk**
- §6.1-7'nin (i)–(vi) maddelerinin her biri, komut ve çıktıyla. Özellikle: test arzının D1 alanı hiçbir fold'da eğitime ya da ön işlemeye girmiyor; her eğitim arzında D1(j) < T; 2..10. seansların fiyat/hacim sütunları okunmuyor (çalışma zamanı dosya/sütun izi, Faz 4 `runtime_file_trace.py` kalıbı); `data/outcomes/`, `data/raw/bist/`, `scores/` okunmuyor.
- Sıra kanıtları: `c20c092` push kanıtı `created_at` < `7ce0593` commit zamanı; `git diff c20c092 7d08169 -- docs/specs_faz5` boş; `7ce0593` ağacında altın faz5 dizini, MODELS.md Faz 5 bölümü ve günlükte post_d1 satırı YOK; `git diff 7ce0593 7d08169 -- borsai` boş (değerlendirme kuralları ve eşikler sonuçtan sonra değişmedi).
- §5 değerlendirmesi: `OPERATIONAL_RULES_FAZ5`'in 18 satırının her biri şartname metninin lafzına uyuyor mu, "tuttu / tutmadı" etiketleri doğru mu? Uymayan her satır bulgudur.
- Kod ↔ şartname: §1.3 (h_1 ana modelden, S_cond tek tanım), §2 (özellikler, ret/uyarı tablosu), §3.1 (ofset sabit, yeni kesişim yok, pseudo-satır yok, ızgara, CV), §6.1, §9, §12. T1 (predict_hazard refactor'u 19 modelin çıktısını değiştirmedi; kendi yolunla doğrula, ör. 7 resmi kaydın saklı çıktılarına karşı), T2 (δ = 0 için özel dal yok), T4 (ayrı dizin; gerçek dosya yok).
- H1–H22'nin her biri: davranış değiştiriyor mu, lafza aykırı mı, kabul edilebilir mi.
- Tam test: `.venv/bin/pytest -q` → `ekler/pytest_out.txt` (sayı, süre).

**3. Mutasyon denetimi** — klonda (`git clone --local` → `/tmp/borsai_faz5_audit/clone`, `.venv` bağla); her mutasyon ayrı uygulanır, ilgili test koşar, KIRMIZI olduğu gösterilir, geri alınır. Sürücü `ekler/mutate.sh`, çıktılar `ekler/mutasyon_ciktilari.txt`. En az şunlar:
- (a) ofset `logit(hazard)` gidiş-dönüşüyle (T1/T2 testleri)
- (b) `predict_post_d1`'e δ = 0 için erken dönüş dalı
- (c) test arzının D1 özelliği fold ön işleme istatistiklerine katılır
- (d) SESSIONS yükleyicisi 2. seansın hacmini okur
- (e) λ eşitliğinde küçük λ seçilir
- (f) eğitim kesimi `<` yerine `<=`
- (g) `d1_lock` ham metin yerine düzeltilmiş `low`/`upper_limit` sütunundan ya da float karşılaştırmayla
- (h) h_1 δ ile güncellenir (d = 1 de ofsete δ eklenir)
- (i) `sequence_guard` / `sequence_violations` `INDEX_POST_D1.json`'u yok sayar
- (j) `freeze_post_d1` modeli `INDEX.json`'a ekler
- (k) `OPERATIONAL_RULES_FAZ5`'te bir beklenti sınırı 0.001 kaydırılır; ayrıca "çok iyi" eşiği −0.040 → −0.060
- (l) bootstrap tohumu ya da ay bloğu anahtarı değişir
Kırmızı olmayan her mutasyon ÖNEMLİ ya da KRİTİK bulgudur (hangi davranışın korumasız kaldığıyla).

**4. Faz 2C koşullu skorlama kontrolü** (canlı veriyi okur; 1–3 bittikten sonra)
- `docs/SPEC_DEVIATIONS.md` G1–G12'nin her biri SPEC_CEILING_PATH_V0 §7'nin ve EK2 §5'in lafzına uyuyor mu; davranış değiştiren var mı.
- `scores/scores.json` `models[].conditional` bloklarındaki BÜTÜN satırlar (9 model, j = 1..9) kayıtlardan (`registry/records/`) ve sonuçlardan (`data/outcomes/`) `borsai` import etmeden yeniden hesaplanır: S_cond, rps_cond, brier_next, brier_10, sınıf mirası, `status`, j başına sayaçlar. Maks |Δ| raporlanır. (Orkestratör `ceiling_hazard_v0`'ın 21 satırını yeniden hesapladı: maks 2.8e-17.)
- n < 10 iken hiçbir j'de hücre ya da hüküm olmadığı; L < j arzın paydada olmadığı; PENDING hedefin bütün modellerde aynı anda düştüğü.
- En az 3 mutasyon (ör. n < 10'da hücre üretimi, sınıf mirasının kırılması, L < j arzın paydaya girmesi), aynı sürücüyle.

**5. "Neden bu kadar iyi?" (tanı; model seçimine GİRMEZ)**
- Brier k = 2 kazancını ayrıştır: kilitli / kilitsiz arzların katkısı; karşılaştırıcının d = 2'deki kalibrasyon açığının (ort h_2 0.0916, gözlenen 0.1571; g2 grubu d = 2 ve 3'ü paylaşıyor) payı ile ayırt etme gücünün payı (ör. Brier'in güvenilirlik/çözünürlük ayrıştırması); yıllara göre; en çok katkı veren 10 arz.
- k = 10'daki hafif kötüleşme ve `path_conditional` D10 MAE'nin kötü çıkması neden?
- §5 beklentin neden düşük kaldı? Faz 1B ve Faz 4'te de beklentin düşük kalmıştı; ortak bir neden var mı?
- Duyarlılık (bilgi; model DEĞİL, şartname değişmez): birincil hücre ve Brier k = 2 için (i) yalnız `d1_lock`, (ii) yalnız `d1_turnover`. Her koşu `ekler/sensitivity_runs.jsonl`'a `experiments/log.jsonl` biçiminde, model_id `post_d1_hazard_v0__sens_<ad>`, `kind: sensitivity` (dondurma görevi bunları günlüğe ekleyecek).

**6. Hüküm** — `docs/fable_faz5_audit/AUDIT.md`
- `post_d1_hazard_v0`: `FREEZE_OK` ya da `FREEZE_BLOCKED` + neden.
- Canlı akış koşulu: teyit / ret.
- Faz 2C: `UYGUN` / `DÜZELTMEYLE UYGUN` / `UYGUN DEĞİL`.
- Yeniden üretim tablosu (her karşılaştırma için maks |Δ|), sızıntı bulguları, mutasyon tablosu (mutasyon · test · kırmızı mı), tanı paragrafı, duyarlılık tablosu.
- Bulgular önem derecesiyle (KRİTİK / ÖNEMLİ / KÜÇÜK) ve her biri için öneri; "kodu şartnameye uydurmak" mı "şartname değişikliği = yeni model_id" mi olduğu açıkça.
- Uygulama için bir cümle: bu backtest sonucu "tasarıma maruz" etiketiyle koşullu sekmede nasıl gösterilmeli.

Tek oturumda bitmezse: 1–3 tamamsa hükmü yaz, 4–5'i açık bırak; 1 bitmediyse hüküm `FREEZE_BLOCKED (denetim tamamlanmadı)`. Her durumda eldekini `(partial)` mesajıyla commit et.

## Kurallar
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Sen kodu düzeltmezsin; bulguyu ve öneriyi yazarsın.
- Mevcut hiçbir dosyayı değiştirme: `borsai/`, `tests/`, `models/`, `docs/specs*/`, `docs/app/`, `experiments/`, `registry/`, `data/`, `scores/`, `app/` salt okunur.
- Yeniden üretim betiği `borsai`'yi import etmez (kanıt: betikte `borsai` geçen import satırı yok ve alt süreçte `sys.modules` denetimi).
- 1–3 ve 5 sırasında `data/outcomes/`, `data/raw/bist/`, `scores/`, `docs/SCORES.md` OKUNMAZ; yalnız adım 4 okur.
- Metinde `thb`/`thm` + 8 haneli tarih kalıbı yazma (`tests/test_outcome_guard.py`).
- Rapor Türkçe.
- `git add -A` yok. Commit:
  ```
  git add docs/fable_faz5_audit docs/prompts/FAZ5_FABLE_REPRO_AUDIT.md
  git commit -m "BORSAI_FAZ5_FABLE_REPRO_AUDIT: independent reproduction and conformity audit of post_d1_hazard_v0, mutation run, Faz 2C conditional scoring check" -- docs/fable_faz5_audit docs/prompts/FAZ5_FABLE_REPRO_AUDIT.md
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.

## Adım 0
- `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3` (beklenen HEAD `7d08169` ya da torunu), `git status --porcelain`.
- İzinli izlenmeyen: yalnız `docs/prompts/FAZ5_FABLE_REPRO_AUDIT.md`. Başka bir şey varsa DUR.
- `registry/`, `data/`, `scores/`, `models/` ağaç sha'ları (`git rev-parse HEAD:<yol>` ve çalışma ağacı dosya sha'ları) → `ekler/koruma_once.txt`; sonda `koruma_sonra.txt`.

## Teslim (rapor)
- Commit hash'i ve `git show --stat`; `docs/fable_faz5_audit/` dosyaları ve sha256'ları (`SHA256SUMS`).
- Hükümler (FREEZE, canlı akış koşulu, Faz 2C).
- Yeniden üretim maks |Δ| tablosu.
- Sızıntı ve sıra kanıtları.
- Mutasyon tablosu.
- Tanı özeti (5 satır) ve duyarlılık tablosu.
- Bulgular ve öneriler; açık konular.

## Kabul kapısı
- K1 87 fold'un ledger'ı, nihai fit önizlemesi, §4'ün bütün hücreleri ve §5'in 18 satırı bağımsız betikle eşleşti (durum ve λ birebir, sayılar |Δ| ≤ 1e-9); ya da eşleşmeyen her şeyin kök nedeni yazılı ve hüküm `FREEZE_BLOCKED`.
- K2 Sızıntı (i)–(vi) ve sıra kanıtlarının her biri komut ve çıktıyla yazılı.
- K3 En az 12 Faz 5 + 3 Faz 2C mutasyonu koşuldu, her birinin sonucu çıktıyla; kırmızı olmayanlar bulgu olarak yazılı.
- K4 Faz 2C: G1–G12'nin her biri hükümlü; bütün koşullu satırlar bağımsız yeniden hesaplandı, maks |Δ| yazılı.
- K5 Commit yalnız `docs/fable_faz5_audit/` ve bu görev dosyası; `registry/`, `data/`, `scores/`, `models/` önce/sonra eşit.

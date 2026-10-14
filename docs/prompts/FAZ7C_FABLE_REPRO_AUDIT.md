# TASK_ID: BORSAI_FAZ7C_FABLE_REPRO_AUDIT_20260927

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi. Ağ yok.
- **Git:** YALNIZ okuma komutları ve her zaman `GIT_OPTIONAL_LOCKS=0` öneki. Sonda tek commit, yalnız kendi yollarınla. push/tag/amend yok.
- **Yazma:** YALNIZ `docs/fable_faz7c_audit/` (AUDIT.md ve `ekler/`) ve bu görev dosyası. Geçici işler `/tmp/borsai_faz7c_audit/` altında, sonda silinir. `ekler/` ≤ 3 MB.
- **Paralel oturum:** yok.
- **Koruma:** koşu öncesi ve sonrası `registry/`, `data/`, `scores/`, `models/`, `app/` ağaç sha'ları ve `git status --porcelain`; eşit olmalı.

## Bağlam
- **Şartnamen** `docs/specs_faz7_c/SPEC_C_V0.md`: `4fe4e51`, push kanıtı 2026-09-27T15:30:43Z. Bağlayıcı kararlar `docs/specs_faz7_c/KARARLAR_C.md` (A'da commit'lendi).
- **Uygulama Opus'a ait** (görev `docs/prompts/FAZ7_C_IMPL.md`, rapor `docs/faz7c/IMPL_RAPOR.md`):
  - `3c93f9c` (A): kod, tarifler, planlar, kurallar, SPEC_DEVIATIONS K1–K13.
  - `1239e45` (A2): `predict_fall._check_params` sıralı anahtarlı JSON'u kabul eder (K14).
  - `77d0ee5` (A3): MODELS.md bölümünün yeri (K15).
  - `acaca2d` (B): walk-forward, altın ledger'lar `tests/reference/macos_golden_faz7c/`, önizlemeler, günlük (backtest satırları + 2 054 `exploration` satırı), MODELS.md bölümü.
  - `197a741` (R): rapor.
  - **Dikkat:** resmi koşu A'nın koduyla yapıldı (günlük `git_commit`). A2 ve A3, sonuçlar görüldükten sonra aynı oturumda yapıldı. İkisi de model, backtest ve skor sayısını değiştirmediğini söylüyor; bunu bağımsız doğrula (bkz. adım 2).
- **Opus'un sonuçları** (backtest, H99, tasarıma maruz; yakın dönem = ilk işlem ≥ 2024-01-01):
  - Birincil `fall_d10_v0_pooled − fall_d10_v0_h99`, D10 Brier: **−0.0058 [−0.0340, +0.0219]**, n = 75 (22 ay, 21 olay) → **belirsiz**; §6.2 aralığı içinde.
  - İkinciller, D10 Brier − `base_rate`:
    - h99 −0.0434 (aralık 0'ın altında);
    - pooled −0.0492 (aralık 0'ın altında);
    - addsale −0.0065 (aralık 0'ı içeriyor).
    - `v1_5_h99`'a karşı üçünün de aralığı 0'ı içeriyor.
  - Yedi hücrenin yedisi §6.2 aralığında; "beklentiden çok iyi" yok.
  - **Orkestratör kontrolü:** birincil hücrenin n, ay, olay ve farkını altın ledger'lardan yeniden hesapladı; tuttu. Bu Opus'un ledger'ından hesaptır; **bağımsız yeniden üretimin yerini TUTMAZ.**
- **Oturumda proje sahibi kararı (K6):** D5 fold'larında eğitim kesimi PLAN_V15 kuralı, yani D5 seansı < T. D10 fold'larında D10 < T.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.**
- **Hijyen:**
  - kasa üyelerinin hiçbir dosyası açılmaz;
  - kohort dosyası yalnız betikle ve `vault != SEALED` süzgeciyle okunur; hiçbir satırı basılmaz;
  - hangi kodun kasada olduğu yazılmaz ve basılmaz;
  - `EXPOSURE.md` dosyaları ve Codex `exposure_log`'ları okunmaz.

ÖNCE OKU:
- CLAUDE.md
- docs/specs_faz7_c/SPEC_C_V0.md (tamamı), KARARLAR_C.md, KESIF.md
- docs/specs/SPEC_V1_6.md (Logit yolu), docs/specs/SPEC_SCORING.md §2, §3, §7, §8
- docs/SPEC_DEVIATIONS.md K1–K15 ve J10, J16, J30
- docs/faz7c/IMPL_RAPOR.md, docs/MODELS.md "Faz 7C" bölümü
- Kendi önceki betiklerin (kalıp): docs/fable_faz7_audit/ekler/ (`repro_hazard_v1.py`, `mutate.sh`, `runtime_file_trace.py`, `vault_check.py`), docs/fable_conformity_20260922/
- Denetlenecek kod (yeniden üretimde KULLANILMAZ): borsai/predict_fall.py, features.py, preprocess.py, fit.py, specs.py, data.py, backtest.py (Faz 7C bölümü), scoring.py (Faz 7C hücreleri), report_faz7c.py, report.py; tests/test_faz7c_*.py, tests/faz7c_support.py ve A/B'de değişen var olan testler

## Adım 0
- `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -6`: HEAD `197a741` ya da torunu. `git status --porcelain`.
- İzinli izlenmeyen: bu görev dosyası. Başka bir şey varsa DUR.
- Koruma ölçümü → `ekler/koruma_once.txt`.

## Adımlar

**1. Sıfırdan yeniden üretim** — `docs/fable_faz7c_audit/ekler/repro_fall.py`
- **Kurallar:** `borsai` import edilmez. Kanıt: import satırı yok ve alt süreçte `sys.modules` denetimi.
- **Çözücü:** şartname algoritmayı V1.6 Logit yolu, yani scikit-learn L2 `LogisticRegression`, olarak tanımlar. Yeniden üretim scikit-learn'ü **doğrudan** aynı hiperparametrelerle çağırabilir.
  - Hiperparametreler şartnameden ve SPEC_V1_6'dan alınır; kodun kendisinden değil.
  - Ek olarak birkaç fold'da kendi Newton çözümünle optimumun çözücüden bağımsız olduğunu göster (|Δp| ≤ 1e-6).
- **1a · Eğitim kümeleri ve özellikler:**
  - `H99_F3_AS_PRESENT` 94 (D10 olay 26, D5 18);
  - `H99_PLUS_OOT_OPEN_F3_AS_PRESENT` 161 (39, 29);
  - `H99_PLUS_OOT_OPEN_AS_PRESENT` 165 (40, 30).
  - Ek satış bayrağı: H99'da 6, açık kümede 13.
  - f1r, `ceiling_hazard_v1_real`'in eğitim satırlarındaki ham değerlerle bit-eşit.
  - ln f3: Type-7 [p05, p95] kırpma ham değerde, sonra ln, sonra z (ddof = 0).
  - f3 filtre kuralı: K5, J10 kalıbı.
- **1b · Fold planları:**
  - `PLAN_FALL_H99`, `_POOLED`, `_ADDSALE`; ufuk başına eğitim kesimi K6.
  - Yakın dönem fold'ları (75, 22 ay) iki planda aynı ticker'lar.
  - Beklenen fold sayıları IMPL_RAPOR'dakiler. Farklıysa kök neden.
- **1c · Ledger'lar:** dört model × iki ufuk, `tests/reference/macos_golden_faz7c/` ile karşılaştır.
  - `logit_status`, `logit_selected_C`, sınıf sayıları, `training_n*` ve kimlik sha'ları birebir;
  - `logit_probability`, `logit_score_table`, `logit_intercept`, `logit_coef` |Δ| ≤ 1e-9.
- **1d · Nihai fit önizlemeleri (4):** C birebir; katsayılar, ön işleme ve kırpma sınırları |Δ| ≤ 1e-9. `@ZERO` Fraction ile: D10 1 − 39/161, D5 1 − 29/161.
- **1e · Hücreler:** MODELS.md Faz 7C bölümünün bütün hücreleri; birincil, ikinciller, merdiven, keşif.
  - Hücre başına fark, %95 aralık (C7: ay blokları, 4000, `random.Random(20260921)`, indeks 100/3899), n, blok, olay ve kazanç/kayıp/eşit, |Δ| ≤ 1e-9.
  - Etiket (§5.1, δ = 0.008) ve §6.2 konumları.
  - Karşılaştırıcılar: `base_rate` ve `v1_5_h99` ledger'ları sha pinli; V1.5 D10 Brier 0.1883 (81 fold).

Tutmayan her şeyin kök nedenini ölç: senin kodun mu, Opus'unki mi, şartname belirsizliği mi. Tahmin etme.

**2. Sızıntı, sıra ve uygunluk** (her madde komut ve çıktıyla)
- **(i) Test arzı:** özellikleri ve sonucu hiçbir fold'da eğitime, kırpma sınırlarına ya da z istatistiklerine girmiyor. 3 fold'da test arzını değiştirip fit'in bit-eşit kaldığını göster.
- **(ii) Eğitim kesimi:** her eğitim satırında D_h seansı < T (ufuk başına, K6).
- **(iii) TÜFE:** her kullanımda `release_date < T`.
- **(iv) Kasa:** SEALED kod sayısı 0 olmalı (bellekte küme; yalnız sayı). Bakılacak yerler: `data/`, `tests/reference/macos_golden_faz7c/`, `docs/MODELS.md`, `experiments/log.jsonl` (keşif satırları dahil), `docs/faz7c/`, `docs/SPEC_DEVIATIONS.md`.
- **(v) Çalışma zamanı dosya izi:** kod yalnız izinli sonuç dosyalarını okuyor (açık 71 + H99); canlı sonuçlar ve `scores/` okunmuyor.
- **(vi) Sıra kanıtları:**
  - şartname push kanıtı < A commit zamanı;
  - `git diff 4fe4e51 197a741 -- docs/specs_faz7_c/SPEC_C_V0.md` boş;
  - KARARLAR_C tek commit'te ve sonra değişmedi;
  - A ağacında faz7c altın dizini, MODELS.md bölümü ve günlükte faz7c satırı yok.
- **(vii) A2 ve A3 (sonuç sonrası düzeltmeler):**
  - `git diff 3c93f9c 197a741 -- borsai` yalnız `predict_fall.py` ve `report.py`;
  - bu iki değişiklik hiçbir ledger, önizleme, hücre ya da etiketi değiştirmiyor. Kanıt: A'nın koduyla ve HEAD koduyla aynı koşunun bayt-eşit olduğunu göster (klonda);
  - A2'nin yakaladığı hata gerçek mi: sıralı anahtarlı JSON gerçekten reddediliyor muydu?
  - Hüküm: bunlar "skor koduna dokunan düzeltme" sayılır mı? Sayılırsa bağımsız el kuralı ihlali mi?
- **Kurallar ↔ şartname:**
  - `NEAR_ERA_TOLERANCE_FALL` = 0.008;
  - üç etiket;
  - §5.4 merdiveni hüküm dilsiz;
  - §6.2 tablosu aynen;
  - `report_faz7c.py` metni sabitlerden.
- **Kod ↔ şartname:** §2.3 (JSON alanları), §3 (özellikler), §4 (ızgara, iç LOOCV, eşitlik kuralı, yakınsamama politikası), §9 (retler), §13.
- **K1–K15'in her biri:** davranış değiştiriyor mu, lafza aykırı mı, kabul edilebilir mi. Özellikle:
  - **K3:** etiket yönü;
  - **K6:** proje sahibi kararı;
  - **K10:** keşif satırlarının hangi veri sürümüne sayıldığı. Soru şu: `fall_d10_v0_h99` da aynı keşiften doğdu (keşif H99 + açık kümede yapıldı). Onun kartının sayacı bu 2 054 satırı saymıyorsa bu, CLAUDE.md kural 4'ün "denenen varyant sayısı dürüst yazılır" amacına uygun mu? Öneri yaz.
  - **K14, K15.**
- **Var olan testlerde A/B'de yapılan istisnalar:** hiçbir bekçi gevşetilmedi. J16/J30 kalıbı aynen, fark tam sayıya eşit, `scores.json` bayt-eşitken.
- **Tam test:** `.venv/bin/pytest -q` ve `bash app/scripts/test.sh` → `ekler/test_out.txt`.

**3. Mutasyon denetimi**
Klonda çalış (`git clone --local` → `/tmp/borsai_faz7c_audit/clone`, `.venv` bağla). Her mutasyon ayrı uygulanır, ilgili test koşar, KIRMIZI olduğu gösterilir, geri alınır. Sürücü `ekler/mutate.sh`, çıktı `ekler/mutasyon_ciktilari.txt`. En az şunlar:
- (a) ek satış boşken 0 kabul;
- (b) bayrak `≥ 0` ile (0 → 1);
- (c) f3 log'u kırpmadan önce;
- (d) kırpma sınırları test arzını içerir;
- (e) D5 fold'unda D10 kesimi (K6 tersi);
- (f) eğitim kesimi `<=`;
- (g) f1r T − 1 ayı;
- (h) yakın dönem eşiği 0.008 yerine 0.015;
- (i) yakın dönem sınırı 2023-12-01;
- (j) `@ZERO` 94 satırdan hesaplanır;
- (k) C eşitliğinde küçük C;
- (l) `base_rate` ledger sha pini atlanır;
- (m) keşif satırı sayısı 2 053;
- (n) `data/`'ya bir kasa kodu (kod bellekte seçilir, yazılmaz);
- (o) bootstrap tohumu;
- (p) etiket yönü ters (K3).

Kırmızı olmayan her mutasyon ÖNEMLİ ya da KRİTİK bulgudur.

**4. Tanı** (model seçimine GİRMEZ; şartname değişmez)
- **addsale neden yakın dönemde zayıf** (−0.0065, aralık 0'ı içeriyor)? H99'da bayrak yalnız 6 arzda. Yakın dönem fold'larının kaçında test arzının bayrağı 1?
- **pooled − h99 "belirsiz":** fark nereden geliyor? Düzey ile ayırma gücünü ayrıştır; yıl kırılımı.
- **Kasa için gerçekçi güç:** beklenen ≈ 12 olayla birincil hücrenin %95 aralığının tahmini genişliği. Açık küme dağılımından ya da benzetimle; kasa verisi YOK.
- **Duyarlılıklar** (bilgi; model değil): gerekli gördüğün en çok 3 koşu. Her biri `ekler/sensitivity_runs.jsonl`'a `kind: sensitivity` ile.

**5. Hüküm** — `docs/fable_faz7c_audit/AUDIT.md`
- Dört model_id için ayrı ayrı `FREEZE_OK` ya da `FREEZE_BLOCKED` + neden.
- Yeniden üretim tablosu: her karşılaştırma için maks |Δ|.
- Sızıntı ve sıra kanıtları; A2/A3 hükmü.
- K1–K15 hükümleri; K10 önerisi.
- Mutasyon tablosu.
- Tanı ve güç notu.
- Bulgular önem derecesiyle (KRİTİK / ÖNEMLİ / KÜÇÜK) ve her biri için öneri. Her bulguda "kodu şartnameye uydurmak" mı, "şartname değişikliği = yeni model_id" mi olduğu açıkça yazılır.
- **Dondurma görevi için notlar:**
  - INDEX 23 → 27;
  - `freeze.model_kind` yönlendirmesi, `F3_MODELS`;
  - uygulama pinleri (J31 kalıbı);
  - MODELS.md `@ZERO` satırındaki "ek satış sütunu düşen fold 94" metin hatası;
  - eski kohort ek kayıtlarında (C) girdileri.

**Tek oturumda bitmezse:** 1–3 tamamsa hükmü yaz, 4'ü açık bırak. 1 bitmediyse hüküm `FREEZE_BLOCKED (denetim tamamlanmadı)`. Eldekini `(partial)` mesajıyla commit et.

## Kurallar
- Mevcut hiçbir dosyayı değiştirme; kodu düzeltmezsin, bulguyu ve öneriyi yazarsın.
- Metinde `thb`/`thm` + 8 haneli tarih kalıbı yazma. Rapor Türkçe.
- `git add -A` yok. Commit:
  ```
  git add docs/fable_faz7c_audit docs/prompts/FAZ7C_FABLE_REPRO_AUDIT.md
  git commit -m "BORSAI_FAZ7C_FABLE_REPRO_AUDIT: independent reproduction and conformity audit of the falling-IPO model v0 family, mutation run, diagnosis" -- docs/fable_faz7c_audit docs/prompts/FAZ7C_FABLE_REPRO_AUDIT.md
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.

## Kabul kapısı
- **K1** Eğitim kümeleri, dört ledger (iki ufuk), dört önizleme ve MODELS.md Faz 7C hücreleri bağımsız betikle eşleşti; ya da eşleşmeyen her şeyin kök nedeni yazılı ve hüküm `FREEZE_BLOCKED`.
- **K2** Sızıntı (i)–(vii) komut ve çıktıyla; A2/A3 hükmü yazılı.
- **K3** En az 15 mutasyon; kırmızı olmayanlar bulgu.
- **K4** K1–K15 hükümlü; K10 için öneri.
- **K5** Commit yalnız izinli yollarda; `registry/`, `data/`, `scores/`, `models/`, `app/` önce/sonra eşit.

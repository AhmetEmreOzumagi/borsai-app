# TASK_ID: BORSAI_FAZ1A_CORE_AND_V1_5_PORT_20260921

Model: Opus 5, akıl yürütme yüksek. Çalışma klasörü ~/Desktop/BorsAi, ek dizin ~/Desktop/Halka_Arz_Modeli (arşiv; SALT OKUNUR). Ağ yok (paket gerekirse yalnız kurulum için). push/tag/amend yok.

## Bağlam

Yeni repo iskeleti hazır (commit ff3eee6). CLAUDE.md'deki altı kural geçerli. Bu task model çekirdeğini kurar ve V1.5'i yeni yapıya taşır. Tavan modeli ve diğer yeni modeller AYRI bir task'ta (Faz 1B) gelecek. Bu task onları yapmaz.

ÖNCE OKU:
- CLAUDE.md, docs/DATA.md, docs/DATA_NOTES.md, docs/PROVENANCE.md
- ~/Desktop/Halka_Arz_Modeli/docs/fable_audit_20260921/AUDIT.md: özellikle §1.2 (b, d, e, g, j), §3a, §3c, §3d, §3e. Kabul testinin tasarımı §3a'dan gelir.
- ~/Desktop/Halka_Arz_Modeli/docs/checkup_20260921/CHECKUP.md: §A.1–A.3, §H.

Aynı anda aynı klasörde bir Fable oturumu docs/specs/ altına model şartnameleri yazıyor olabilir. docs/specs/ dizinine DOKUNMA, commit'e ekleme. Commit'e yalnız aşağıda adı geçen yolları ekle; `git add -A` ya da `git add .` KULLANMA.

## Hedef yapı (borsai/ paketi)

- `features.py`: f1–f5'in TEK tanımı. Kaynak: V1.5 davranışı (legacy `pbb` calculated_features, `preprocessing.py`). f3 filtre durumu argümanını taşı (AUDIT §1.2-j); eşitlikte küme sırasına bağlı `mode` davranışını deterministik yap ve bunu belgele.
- `preprocess.py`: fold içi ön işleme; ürettiği tüm parametreleri (winsor p05/p95, medyanlar, μ, σ) dict olarak döndürür.
- `fit.py`: `fit(model_spec, training_rows) -> params (dict)`. sklearn ve legacy fonksiyonları kullanabilir. Çıktı: model_id, algorithm, features, preprocessing params, ufuk başına ridge {alpha, intercept, coef[]} ve logit {C, intercept, coef[]}, training {tickers[], tickers_sha256, n, cutoff_date, data_version_sha256}, feature_ranges (eğitimdeki min/max, uyarı eşikleri için), code_version (git commit), created_at, schema_version.
- `predict.py`: `predict(params, inputs) -> {D1..D10: {return, price, p_up}, warnings[], refused?}`. SAF: yalnız Python stdlib (math); numpy/sklearn YOK. Kurallar:
  - f3 (talep katı) boşsa V1.5 için RET (AUDIT §1.2-d; gerekçeyi yanıtta yaz).
  - f4 = 0 kabul edilir, "eğitimde örneği yok" uyarısı verir (legacy'deki falsy-0 hatası taşınmaz).
  - Her girdi eğitim aralığı dışındaysa satır başına uyarı.
  - Getiri çıktısı fiziksel sınıra [0.9^h − 1, 1.1^h − 1] kırpılır ve kırpıldığı işaretlenir.
  - Sıfıra bölme gibi durumlar etiketli hata verir, çıplak exception değil.
- `backtest.py`: legacy H99 benchmark'ıyla aynı walk-forward (kesin öncelik, MIN_TRAIN_N = 10, aynı fold planı). Fold ledger ve metrikleri üretir. Her koşu `experiments/log.jsonl` dosyasına otomatik bir satır ekler: model_id, spec sha, veri sha, metrikler, zaman, git commit (CLAUDE.md kural 4).
- Basit kurallar aynı şemada birer model: ALWAYS_CEILING, TRAIN_MEDIAN, TRAIN_MEAN, ZERO, BASE_RATE ve LAST10_BASE_RATE. Hepsi backtest'ten aynı fold'larda geçer.

legacy/ değiştirilmez. Gerekirse oradan import edilir, ya da mantık borsai/'ye taşınır. Hangisini yaptığını raporda yaz.

## Kabul testleri (tests/; AUDIT §3a)

1. **Fold kurulumu:** 351 fold'un training_tickers_sha256 değeri tests/reference/v1_5_benchmark ledger'ıyla 351/351 eşit.
2. **Fold tahminleri, toleranslı:**
   - Seçilen α 351/351 eşit; seçilen C en az 350/351 eşit.
   - |Δ Ridge| ≤ 1e-12; |Δ Logit p| ≤ 1e-7.
   - D3|BETAE yakınsama farkı ADIYLA beklenen sapma olarak yazılır. Başka sapma varsa test kalır.
3. **Metrikler:** 4 ufuk × Ridge/Logit = 8 hücre ve n'leri; tolerans Ridge için 1e-12, Logit için 1e-7. Beş basit kuralın BLB değerleri aynı toleransla (örn. TRAIN_MEDIAN D1 MAE 0.025107817206684563, BASE_RATE D1 Brier 0.10215057076590381).
4. **Altın referans:** 1–3 geçince bu makinede macOS altın ledger'ı üret, `tests/reference/macos_golden/` altına yaz, sha256'sını kaydet. Regresyon testi bundan sonra ona karşı BİREBİR çalışır. Windows değerleri "tarihsel, tolerans içinde" kalır.
5. **predict paritesi (JSON ↔ sklearn):**
   - NETGL: tests/reference/netgl_input_contract.json ve A_v1_5_probe_cikti.json değerleri; aynı makinede üretildikleri için |Δ| ≤ 1e-12.
   - ZZTEST girdisi.
   - 99 eğitim satırının hepsi: JSON-predict ile sklearn final modeli |Δ| ≤ 1e-12.
   - Uç vektörler: f3 < p05, f3 > p95 (kırpma yolu), f4 = 0, f4 = 100, f1 eğitim aralığı dışı, R_h fiziksel sınır dışı.
   - f3 = None → RET beklenir.
6. `training.tickers_sha256` alanı JSON'da doğru.

Tutmayan bir test varsa önce kök nedeni bul. Testi gevşetme; toleransı değiştirmek gerekiyorsa DUR ve gerekçesiyle raporla.

## Dondurma (bu task'ın sonunda)

- `models/v1_5_h99.json`: V1.5, 99 arzın hepsiyle fit edilmiş; model_id `v1_5_h99`.
- Basit kuralların JSON'ları: 99 arzla hesaplanmış medyan, ortalama, taban oranı, son-10 taban oranı. model_id'ler: `base_always_ceiling`, `base_train_median`, `base_train_mean`, `base_zero`, `base_rate`, `base_last10_rate`.
- `models/INDEX.json`: her model için model_id, dosya, sha256, eğitim n'i, cutoff, frozen_at.
- `docs/MODELS.md`: her modelin kısa tanımı ve backtest metrikleri. Metrikler fark + blok bootstrap %95 aralığı + n ile verilir (aylık blok, AUDIT §1.2-c yöntemi, 4000 tekrar, sabit seed). "Geçiyor" yalnız aralık 0'ı dışlıyorsa.

## YAPMA

- 2026-08-19 sonrası veri indirme ya da ekleme (CLAUDE.md sıra kuralı).
- Tavan, PB ya da market modeli (Faz 1B).
- Uygulama kodu.

## Commit

Tek commit, yalnız: borsai/, tests/, models/, experiments/, docs/MODELS.md, docs/prompts/FAZ1A_V1_5_PORT.md ve gerekirse pyproject.toml / requirements.lock.
Mesaj: "BORSAI_FAZ1A: core package, V1.5 port with tolerance acceptance tests, frozen v1_5_h99 and baseline models". Push yok.

## Teslim (rapor)

- Commit hash'i ve `git show --stat` özeti.
- Test sonuçları (kaç test, hepsi yeşil mi); kabul testlerinin 1–6 ayrı ayrı sonucu ve ölçülen maks |Δ| değerleri.
- models/INDEX.json içeriği.
- docs/MODELS.md'deki metrik tablosu.
- legacy'den import mu edildi, taşındı mı; nedeni.
- Belirsizlikler ve verdiğin kararlar.

## Kabul kapısı

- K1 Kabul testlerinin altısı yeşil; D3|BETAE dışında adıyla yazılmamış sapma yok.
- K2 predict.py yalnız stdlib kullanıyor (import listesiyle kanıtla).
- K3 Modeller dondurulup INDEX.json'a yazıldı.
- K4 experiments/log.jsonl her backtest koşusunu içeriyor.
- K5 legacy/ ve docs/specs/ değişmedi; yeni repoda 2026-08-19 sonrası veri yok.
- K6 Push, tag, amend yok.

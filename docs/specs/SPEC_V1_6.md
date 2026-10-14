# SPEC_V1_6 — V1.5 + genişletilmiş ızgara (`v1_6_h99`)

## Özet (≤ 10 satır)

1. V1.5 aynen: aynı f1–f5, aynı ön işleme, aynı fold planı (351 fold), aynı amaçlar ve eşitlik kuralları. Değişen YALNIZ hiperparametre ızgarası (AUDIT §1.2-e) ve onun zorunlu kıldığı iki politika.
2. Ridge α ∈ {0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000, INF}. INF = yalnız sabit terim = eğitim **ortalaması**.
3. Logit C ∈ {ZERO, 0.0001, 0.001, 0.01, 0.1, 1, 10, 100}. ZERO = yalnız sabit terim = eğitim **oranı**.
4. Zorunlu politika 1: yakınsamama ADAY başına ele alınır (o C ızgaradan düşer); V1.5'te tek iç fit yakınsamazsa bütün fold düşüyordu. Geniş C'de bu sık olur; kural olmadan V1.6 fold kaybeder.
5. Zorunlu politika 2: INF/ZERO kapalı biçimle hesaplanır (sklearn'e sıfır sütunlu matris verilmez).
6. V1.5 ızgara kenarına yapışıyordu: D1 Ridge 84/89 fold'da α = 100; D10 59/87 fold'da α = 0.1; D1 Logit 37/80 fold'da C = 0.01.
7. **Beklenti: D1 sorunu çözülmez.** Yalnız-sabit uç noktası ortalamadır ve D1'de ortalama (MAE 0.0332) V1.5'ten (0.0297) de medyandan (0.0251) da kötüdür. Kazanç beklenen yer D10 (küçük α) — o da belirsiz.
8. Geriye dönük sonuç tasarıma maruzdur (ızgara, V1.5'in H99 seçim dağılımı görülerek genişletildi). Asıl ölçüm prospektiftir.

İşaretler: **[ÖLÇTÜM]** / **[ÇIKARIM]**.

---

## 1. Kimlik

- `model_id`: `v1_6_h99`. `algorithm`, `features`, `preprocessing`: `v1_5_h99` ile aynı değerler; `grid_version: "v1_6"`.
- Eğitim: 99 arz, kesim 2026-08-19, `data_version.sha256 = b307cd0e…`.
- `v1_5_h99` dokunulmadan referans olarak kalır (kural 5).

## 2. V1.5'ten devralınanlar (değişmez)

Kaynak: `legacy/scripts/modeling/candidate_models.py:19-40`, `preprocessing.py`, `fold_engine.py`, `logistic_policy.py`; yeni repoda `borsai/{features,preprocess,fit,predict,backtest}.py` (Faz 1A portu).
- Özellikler f1–f5 ve 11 adımlı fold içi ön işleme (f1 log, f3 [p05, p95] kırpma, medyan imputasyon + f5, z-skor, > %40 eksik ve sıfır varyans düşürme, f3 filtre durumu).
- Ridge: `fit_intercept=True`, `solver="svd"`; iç LOOCV amaç MAE (R_h uzayında); eşitlikte **en büyük α**.
- Logit: `l1_ratio=0.0`, `solver="lbfgs"`, `max_iter=10000`, `tol=1e-10`, `class_weight=None`; iç LOOCV amaç ham Brier; eşitlikte **en küçük C**. Tek sınıf → `MODEL_NOT_FIT_SINGLE_CLASS`; azınlık < 2 → ayarsız, yedek C = 0.01 (`logistic_policy.py:20, 44-46`) — V1.6'da da 0.01 kalır.
- İç LOOCV'de ön işleme her iç bölmede ham satırlardan yeniden kurulur. Eşitlik yalnız bit-eşit skorla.
- Fold planı: kesin öncelik (hedef seansı < T), MIN_TRAIN_N = 10, sıra (first_trading_date, ticker).
- `predict` kuralları: f3 boş → RET; f4 = 0 kabul + uyarı; aralık dışı uyarı; fiziksel sınıra kırpma.

## 3. Izgara (şimdi sabitlendi)

| Kafa | V1.5 | V1.6 |
|---|---|---|
| Ridge α | 0.1, 1, 10, 100 | **0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000, INF** |
| Logit C | 0.01, 0.1, 1, 10 | **ZERO, 0.0001, 0.001, 0.01, 0.1, 1, 10, 100** |

Gerekçe [ÖLÇTÜM, AUDIT §1.2-e; `tests/reference/v1_5_benchmark/…selected_hyperparameter_distribution.csv`]: D1 Ridge α = 100 → 84/89 fold (üst kenar); D3 α = 10 → 70, 100 → 18; D10 α = 0.1 → 59/87 (alt kenar); D1 Logit C = 0.01 → 37/80 (alt kenar).
- Her iki yöne 2 onluk genişletildi; V1.5'in dört değeri ızgarada kalır (V1.5 çözümü her zaman erişilebilir bir adaydır).
- z-skorlu 5 özellik ve n ≤ 99'da α = 10000 katsayıları ~%1'e büzer [ÇIKARIM: büzme ≈ n/(n + α)]; α = 0.001 pratikte OLS'tir. α = 0 ızgarada YOK (svd ile tanımlı ama eşdoğrusal erken fold'larda kararsız).
- Sıralama ve eşitlik: INF tüm sonlu α'lardan büyük; ZERO tüm pozitif C'lerden küçük sayılır. Yani eşitlikte yine "daha çok büzen" kazanır.

### Uç noktaların tanımı (kapalı biçim)
- Ridge INF: tahmin = (iç ya da dış) eğitim hedeflerinin aritmetik ortalaması; `coef = [0,…]`, `intercept = mean`.
- Logit ZERO: p = n_1/n (cezasız sabit terimli lojistiğin tam çözümü); `coef = [0,…]`, `intercept = ln(p/(1 − p))`. İç bölmede p ∈ {0, 1} olamaz (azınlık ≥ 2 iken LOOCV her bölmede iki sınıfı korur; V1.5 bunu doğruluyor, `candidate_models.py:436-456`).
- JSON'da: `"alpha": "INF"` / `"C": "ZERO"` (string), diğerleri sayı. `predict` için fark yok (katsayılar sıfır).

## 4. Zorunlu politika farkları (ızgaranın sonucu)

1. **Aday başına yakınsamama.** V1.5: herhangi bir (C, iç bölme) fit'i `ConvergenceWarning` verirse tüm fold `MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE` (`candidate_models.py:517-523`). V1.6: o C adayı `CANDIDATE_NOT_CONVERGED` olur ve skor tablosundan çıkar; seçim kalan adaylar arasında yapılır. Seçilen C'nin nihai (dış) fit'i yakınsamazsa skor sırasındaki bir sonraki aday denenir. ZERO her zaman geçerlidir → Logit fold'u yalnız tek sınıfta düşer. Ledger her adayın durumunu yazar.
   - Sonuç: `D3|BETAE` (macOS'ta V1.5'te yakınsamıyor, AUDIT §1.2-b) V1.6'da skorlanır. V1.5–V1.6 eşleşik kümesi = V1.5'in skorlanabildiği fold'lar.
2. **Kapalı biçim uçlar** (§3).
Bunlar dışında V1.5'ten sapma YOKTUR. Kabul testi 3 bunu sınar.

## 5. Parametre bütçesi

V1.5 ile aynı: 5 katsayı + sabit; azınlık (Y = 0) D1 10, D3 19, D5 22, D10 29 (`docs/specs/ekler/m2_cikti.txt:16-23`; `docs/DATA.md` "Y = 1 sayıları: 89/80/77/70"). Bütçe üstü (AUDIT §3b); V1.6 bunu düzeltmez, yalnız büzme aralığını açar. Izgara 4 → 9 (8) aday: iç LOOCV'nin seçim gürültüsü artar; n = 99'da bu, walk-forward skorunu hafif iyimser yapabilir [ÇIKARIM]. Deney günlüğü bu yüzden zorunlu.

## 6. Eksik veri davranışı

V1.5 ile aynı (f3 boş → RET; f4 = 0 → kabul + uyarı; aralık dışı → uyarı; fiziksel sınır → kırp + işaretle).

## 7. Walk-forward ve kurallar

- Fold planı V1.5 ile birebir: 351 fold, aynı `training_tickers_sha256`.
- Kurallar: çekirdekteki altı basit kural, aynı fold'larda. Ek eşleşik karşılaştırma: `v1_5_h99` (asıl soru: ızgara fark ediyor mu).
- Raporlanacak ek tablo: ufuk × kafa başına seçilen hiperparametre dağılımı; kenara yapışma oranı (uç değer seçilen fold yüzdesi).

## 8. Sonuç görülmeden yazılan beklenti

2026-09-21'de, hiçbir V1.6 fit'i görülmeden yazıldı. Izgara, V1.5'in H99 üzerindeki seçim dağılımı görülerek genişletildi → geriye dönük sonuçlar **tasarıma maruzdur**.

[ÖLÇTÜM, `tests/reference/baseline_benchmark/…metric_summary.csv`, D1, n = 89] MAE: medyan 0.0251, V1.5 0.0297, ortalama 0.0332, sıfır 0.0885.

Beklenti [ÇIKARIM]:
- **D1 Ridge:** çoğu fold α ∈ {1000, 10000, INF} seçer; MAE 0.0297 ile 0.0332 arasına, yani V1.5'e eşit ya da **daha kötü** tarafa gider; medyana yenilgi sürer. Neden: D1 getirileri +%10'da yığılı; MAE'yi medyan en küçükler, Ridge'in sabiti ortalamadır. Bu bir ızgara sorunu değil kayıp fonksiyonu sorunudur; çözümü ayrı bir model_id ister (ör. medyan sabitli / kantil regresyon) ve bu şartnamenin kapsamı dışındadır.
- **D3:** değişim ≈ 0 (V1.5 iç noktada: α = 10).
- **D5:** küçük değişim.
- **D10 Ridge:** α ∈ {0.001, 0.01} sık seçilir; MAE değişimi ±0.01 içinde, yönü belirsiz (aşırı uyum riski).
- **Logit D1:** ZERO/0.0001/0.001 sık; Brier taban oranına yaklaşır (0.0943 → ~0.10). Diğer ufuklarda |ΔBrier| < 0.005.
- Kenara yapışma: yeni ızgarada hiçbir ufukta tek bir uç değer fold'ların > %50'sinde seçilmemeli — INF/ZERO hariç (onlar "model yok" demektir ve meşru sonuçtur).

Başarı (prospektif, n ≥ 30): `v1_5_h99`'a karşı D10 MAE eşleşik farkı, aralık 0'ı dışlayarak negatif. Birincil ufuk: D10.
Başarısızlık: herhangi bir ufukta aynı aralık 0'ı pozitif tarafta dışlıyor → "geniş ızgara zarar veriyor" yazılır.
Ara durum: "V1.5'ten ayırt edilemiyor" — en olası sonuç. Backtest ne çıkarsa çıksın bu şartnameyle dondurulur.

## 9. Sözde kod (yalnız V1.5'ten farklar)

```
ALPHA_GRID = (0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0, INF)
C_GRID     = (ZERO, 0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0)

def ridge_predict_candidate(alpha, X_tr, y_tr, x):
    if alpha is INF: return mean(y_tr)
    return Ridge(alpha, fit_intercept=True, solver="svd").fit(X_tr, y_tr).predict(x)

def logit_candidate_p(C, X_tr, y_tr, x):
    if C is ZERO: return sum(y_tr)/len(y_tr), CONVERGED
    clf = LogisticRegression(C=C, l1_ratio=0.0, solver="lbfgs", max_iter=10000, tol=1e-10)
    fit with warnings captured -> if ConvergenceWarning: return None, NOT_CONVERGED
    return p1, CONVERGED

def select_C(inner_folds):
    table = {}
    for C in C_GRID:
        terms = []
        for fold in inner_folds:
            p, st = logit_candidate_p(C, ...)
            if st is NOT_CONVERGED: table[C] = CANDIDATE_NOT_CONVERGED; break
            terms.append((p - y)**2)
        else: table[C] = mean(terms)
    ranked = sort(scored C, key=(score asc, C asc))         # ZERO < 0.0001 < ...
    for C in ranked:                                         # nihai dış fit de yakınsamalı
        if final_fit_converges(C): return C
    # ZERO her zaman yakınsar -> buraya düşülmez

select_alpha: V1.5 ile aynı; sıralama anahtarı (score asc, alpha desc), INF = +inf
```

## 10. Kabul testleri

1. **Fold kimliği:** 351 fold'un `training_tickers_sha256` değeri V1.5 altın ledger'ıyla 351/351 eşit.
2. **Izgara sabitleri:** kod sabitleri §3 tablosuna birebir eşit; JSON'da `grid_version = "v1_6"` ve ızgara listeleri yazılı.
3. **V1.5'e indirgeme:** aynı kod V1.5 ızgarasıyla ve "fold düzeyi yakınsamama" bayrağıyla çalıştırılınca macOS altın ledger'ını BİREBİR üretir (tek kod yolu, iki ızgara; ayrı kopya kod yok).
4. **Uç nokta kapalı biçimi:** INF adayının iç LOOCV skoru = "iç eğitim ortalaması" tahmincisinin LOOCV MAE'sine bit-eşit; ZERO için aynı şey oranla. α = 1e12 ile sklearn Ridge tahmini INF'e |Δ| ≤ 1e-9.
5. **Eşitlik kuralı:** skorları eşitlenmiş sentetik tabloda Ridge INF'i, Logit ZERO'yu seçer.
6. **Aday başına yakınsamama:** `_fit_logistic_and_check_convergence` monkeypatch ile C = 100'de uyarı üretilince fold düşmez; C = 100 tabloda `CANDIDATE_NOT_CONVERGED`; seçim kalanlardan. Nihai fit'te uyarı → sıradaki aday.
7. **BETAE:** `D3|BETAE` V1.6'da `FIT_OK` (ya da hangi adayların düştüğü ledger'da adıyla yazılı); D3 Logit n = 81.
8. **predict paritesi:** 99 eğitim satırı + NETGL girdisi: JSON-predict ≡ sklearn nihai model, |Δ| ≤ 1e-12; INF/ZERO seçilmiş ufuk varsa çıktı sabit. f3 = None → RET.
9. **Seçim dağılımı raporu** üretilir ve `docs/MODELS.md`'ye girer; deney günlüğüne satır düşer.

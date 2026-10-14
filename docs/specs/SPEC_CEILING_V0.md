# SPEC_CEILING_V0 — tavan serisi modeli v0 (`ceiling_hazard_v0`)

## Özet (≤ 10 satır)

1. Tek model: ayrık zamanlı hazard. h_d(x) = "seri d−1 gün sürdüyse d. gün bozulur mu". Çıktı S_k = P(seri ≥ k) = Π_{d≤k}(1 − h_d), k = 1..10. Tutarlılık (S_1 ≥ S_2 ≥ … ≥ S_10) çarpımdan kendiliğinden gelir.
2. Yalnız listeleme öncesi bilgi: 3 paylaşılan katsayı (f1 = ln arz büyüklüğü, f2 = halka açıklık %, f3 = talep katı) + 3 gün sabiti: {D1}, {D2–D3}, {D4–D10}. Toplam 6 parametre; 508 risk-günü, 85 olay → parametre başına ≈ 14 olay.
3. L2 cezası yalnız 3 katsayıda; sabitler cezasız. Izgara λ ∈ {0.1, 1, 3, 10, 30, 100, 300, 1000, INF}; INF = "yalnız gün sabitleri". Seçim: iç "bir arzı dışarıda bırak" CV, log-kayıp; eşitlikte büyük λ.
4. f3 boşsa RET (V1.5 ile aynı kural). f3'süz tavan tahmini `pb_ceiling_v0`'dan gelir (SPEC_PB_V0 §9).
5. Walk-forward: sansürlü kısmi seriler eğitime girer (seans tarihi < T(k)); min-eğitim azınlık sayısına bağlı (≥ 10 arz, ≥ 5 olay, ≥ 5 sağ kalım). Ölçülen skorlanabilir fold: 87.
6. P(Dk'de tavan kapanışı) ikincil, türetilmiş çıktıdır: S_k + (1 − S_k)·r_k; r iki sabit. Beklenen getiri eşlemesi v0'da YOK (§8).
7. Birincil metrik: RPS = (1/10) Σ_k (S_k − 1[L ≥ k])². Yenilecek çizgi: son-10 ve genişleyen Kaplan–Meier taban oranlarının İKİSİ de.
8. Geriye dönük sonuç "tasarıma maruz"dur (gün grupları H99 marjinallerine bakılarak seçildi). Asıl ölçüm prospektiftir; n < 30'da hüküm yok.

İşaretler: **[ÖLÇTÜM]** = bu oturumda dosyadan/komuttan; **[ÇIKARIM]** = yorum. Ölçüm script'leri ve çıktıları: `docs/specs/ekler/` (salt okur; hiçbir model fit edilmedi, özellik–sonuç ilişkisine bakılmadı).

---

## 1. Kimlik

- `model_id`: `ceiling_hazard_v0`. `algorithm`: `discrete_time_hazard_logit_l2`. `schema_version`: çekirdekle aynı.
- Eğitim: `data/training_table.csv` (sha256 `b307cd0e…`, `data/data_version.json:3`), 99 satırdan f3'ü dolu 97'si. Kesim: sonuç seansları ≤ 2026-08-19.
- Bu şartnamedeki herhangi bir şey (özellik, gün grubu, ızgara, pseudo-gözlem, fold kuralı) değişirse yeni `model_id` (CLAUDE.md kural 5).

## 2. Veri ve etiket

Kaynak sütunlar (`data/training_table.csv`, tanımlar `docs/DATA.md`):
- `ceiling_streak_L` ∈ 0..10: 1. seanstan başlayan kesintisiz tavan kapanışı sayısı. Etiket THM üst limitiyle Decimal eşitliğinden (SPEC_SCORING §3).
- Seans tarihleri: `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv` sütunları `ticker, session_number, target_session_date`. Yalnız walk-forward sansürü için okunur; fiyat sütunları okunmaz.

Kişi-dönem (person-period, PP) tablosu: arz i, gün d ∈ 1..10 için satır ancak `d − 1 ≤ L_i` ise vardır (arz d. güne "risk altında" girmiştir). `event = 1[L_i == d − 1]` (seri d. gün bozuldu), değilse 0. L_i = 10 olan arz 10 satır, hepsi event = 0.

[ÖLÇTÜM] `ekler/m1_cikti.txt:3-16`: tüm kohortta 508 risk-günü, 85 olay (= 99 − 14).

| gün d | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| risk | 99 | 81 | 70 | 66 | 53 | 41 | 33 | 27 | 21 | 17 |
| olay | 18 | 11 | 4 | 13 | 12 | 8 | 6 | 6 | 4 | 3 |
| hazard | .182 | .136 | .057 | .197 | .226 | .195 | .182 | .222 | .190 | .176 |

## 3. Gün sabitlerinin gruplanması ve gerekçesi

`g(d)`: g1 = {1}, g2 = {2, 3}, g3 = {4, …, 10}.

[ÖLÇTÜM] `ekler/m1_cikti.txt:14-16`: g1 99 risk / 18 olay (0.182); g2 151 / 15 (0.099); g3 258 / 52 (0.202).

Gerekçe [ÇIKARIM]:
- D1 yapısal olarak ayrıdır (ilk fiyat oluşumu; dağıtım alan herkes ilk kez satabilir) → kendi sabiti.
- D4–D10 hazard'ı 0.18–0.23 bandında düz; 10 ayrı sabit olay başına bütçeyi tüketir (gün başına 3–13 olay).
- D2–D3 belirgin düşük (0.10); g3 ile birleştirmek S_3'ü sistematik düşürür. 4 gruba bölmek ({4,5} ve {6..10}: 0.21 ve 0.195) ayırt edilemez iki sabit üretir.
- Her grupta ≥ 15 olay → 10–15 olay/parametre kuralı sabitler için de tutuyor.
- **Tasarıma maruziyet:** bu gruplama H99'un marjinal hazard tablosuna bakılarak seçildi. Özellik–sonuç ilişkisine bakılmadı.

## 4. Özellikler

| Ad | Tanım | Kaynak sütun | Ön işleme |
|---|---|---|---|
| f1 | ln(`ipo_price_tl` × `shares_offered`) | training_table | ln → z-skor |
| f2 | `shares_offered` / `post_ipo_share_capital` × 100 | training_table | z-skor |
| f3 | `total_demand_multiple` | training_table | [p05, p95] kırpma → z-skor |

- Tanımlar `borsai/features.py`'deki TEK tanımdan gelir (V1.5 ile aynı f1, f2, f3). f3 filtre durumu argümanı V1.5'teki gibi taşınır (H99'da etkisiz, AUDIT §1.2-j).
- Ön işleme V1.5'in adımlarıyla aynı sayısal kurallar: p05/p95 Type-7 doğrusal kantil, eğitim kümesinden; z-skor eğitim ortalaması ve **popülasyon** std'si (ddof = 0) ile (`legacy/scripts/modeling/preprocessing.py:222, 455-463`). Fark: **imputasyon yok, f5 yok, f4 yok.** `borsai/preprocess.py` özellik alt kümesini desteklemiyorsa, V1.5 davranışını değiştirmeden (altın testler yeşil kalarak) genişletilir.
- Ön işleme ARZ düzeyinde (arz başına bir satır) hesaplanır, PP satırlarında değil; uzun serili arzlar μ/σ'yı ağırlıklandırmaz.
- Sıfır varyanslı özellik (σ = 0) o fit'te düşer (katsayı 0 yazılır); üçü de düşerse yalnız sabitler.

Neden bu üçü [ÇIKARIM, sonuç görülmeden]: talep fazlası (f3) karşılanmamış talebin doğrudan ölçüsü; küçük arz (f1) ve düşük halka açıklık (f2) tavanda satıcı arzını kısar. f4 (sermaye artırımı payı) için serinin süresine dair a priori mekanizma zayıf → bütçe dışı. Beklenen işaretler (hazard üzerinde): β_f3 < 0, β_f1 > 0, β_f2 > 0.

Bilinen zayıflık: f1 nominal TL'dir; 2023–2026 enflasyonu f1'i kaydırır. V1.5 ile eşlik için v0'da düzeltilmez.

## 5. Model, amaç fonksiyonu, çözücü

logit h_d(x) = γ_{g(d)} + β·z(x), β ∈ R³, γ ∈ R³.

Amaç (en küçüklenir): `J(γ, β) = −Σ_r w_r [e_r ln h_r + (1 − e_r) ln(1 − h_r)] + (λ/2)·‖β‖²`
- r: gerçek PP satırları (w = 1) **ve** 6 pseudo-satır: her grup g için z = 0'da bir event = 1 ve bir event = 0 satırı, w = 0.5. Amaç: erken fold'larda bir grupta hiç olay yokken γ_g'nin −∞'a gitmesini önlemek (ilk 19 arzda D1 olayı 1: AUDIT §2.4 "18/19"). Büyük örnekte etkisi ihmal edilir. Pseudo-satırlar nihai fit'te de vardır (tek tanım).
- γ cezasız. sklearn `LogisticRegression` seçici ceza veremediği için KULLANILMAZ.
- Çözücü: tam Newton–Raphson, numpy. Başlangıç: β = 0, γ_g = logit((olay_g + 0.5)/(risk_g + 1)). Adım: Δ = H⁻¹∇ (`numpy.linalg.solve`); J azalmıyorsa adımı yarıla (en çok 30 kez). Dur: max|∇| ≤ 1e-10. 100 yinelemede durmazsa durum `MODEL_NOT_FIT_DID_NOT_CONVERGE` (fold skorlanmaz, adıyla raporlanır; 6 parametreli dışbükey problemde beklenmez).
- λ = INF: β ≡ 0; γ_g kapalı biçim: logit((olay_g + 0.5)/(risk_g + 1)).

### Izgara ve seçim
- λ ∈ {0.1, 1, 3, 10, 30, 100, 300, 1000, INF}. Ölçek gerekçesi [ÇIKARIM]: β_j için Fisher bilgisi ≈ Σ h(1−h) ≈ 508 × 0.14 ≈ 70; λ ≈ 70 katsayıyı kabaca yarılar. Izgara bunun iki yanına ≥ 1 onluk taşar; INF uç noktası "özellikler işe yaramıyor" seçeneğidir (AUDIT §1.2-e'nin tekrarı olmasın).
- İç CV: eğitimdeki her arz j için: j'nin TÜM PP satırları dışarıda; ön işleme kalan arzlardan yeniden kurulur (V1.5 bağlayıcı kuralı); her λ için fit; j'nin satırlarında log-kayıp toplanır. Skor(λ) = Σ_j Σ_{r∈j} nll_r / Σ_j |r∈j|. h, log-kayıpta [1e-12, 1 − 1e-12]'ye kırpılır.
- Seçim: en küçük skor; bit-eşit eşitlikte **en büyük λ** (INF en büyük).
- Bir λ için herhangi bir iç fit yakınsamazsa o λ ızgaradan o fold için çıkar (`CANDIDATE_NOT_CONVERGED`); INF her zaman kalır.

## 6. Parametre bütçesi

[ÖLÇTÜM] Olay 85, sağ kalım 423 (`m1_cikti.txt:13`); f3'ü dolu 97 arzda 83 olay. 6 parametre → 13.8 olay/parametre (AUDIT §3b'nin 10–15 kuralı). Walk-forward test kümesinde (87 fold) azınlık sayıları: L < 1: 16; L < 3: 31; L ≥ 5: 33 (= 87 − 54); L ≥ 10: 11 (`m2_cikti.txt:1`). S_10 için 11 olayla yalnız sabit terim anlamlıdır; model bunu paylaşılan katsayılarla "ödünç" alır, ayrıca doğrulanamaz [ÇIKARIM].

## 7. Eksik veri ve aralık dışı davranış

| Durum | Davranış |
|---|---|
| f3 boş | **RET** `REFUSED_F3_MISSING`. Eğitimde f3'ü boş 2 arz (ALBTN, ENDAE; ikisi de L = 0, `m1_cikti.txt:28-29`) kullanılmaz; walk-forward'da test satırı olarak "ret" sayılır, kurallar da bu iki arzda skorlanmaz (eşleşik küme) |
| f1/f2 hesaplanamıyor (payda 0, fiyat ≤ 0) | etiketli hata, çıplak exception değil |
| Girdi eğitim min/max dışında | tahmin verilir + satır başına uyarı (`feature_ranges` JSON'da) |
| f3 p05 altı / p95 üstü | kırpılır, `clipped: true` işaretlenir |

## 8. Çıktılar

`predict(params, inputs)` (yalnız stdlib) şunu döndürür:
- `hazard[d]`, d = 1..10; `S[k]` = Π_{d ≤ k} (1 − hazard[d]), k = 1..10. **Birincil çıktı.**
- `P_L[l]` = P(L = l): l = 0 → 1 − S_1; 1 ≤ l ≤ 9 → S_l − S_{l+1}; l = 10 → S_10. Toplam 1 (test).
- `P_close_ceiling[k]`, k = 1..10. **İkincil, türetilmiş.** k = 1: S_1. k ≥ 2: `S_k + (1 − S_k)·r_{b(k)}`; b = a for k ∈ {2,3,4}, b = b for k ∈ {5..10}; `r = (a + 0.5)/(n + 1)`, n = eğitimde (L < k) olan arz-gün sayısı, a = bunlardan `ceiling_close_Dk = 1` olanlar, grup içinde toplanır. [ÖLÇTÜM] `m1_cikti.txt:18-27`: k = 2..4 → 2/108; k = 5..10 → 61/441; yani r_a ≈ 0.023, r_b ≈ 0.139. Varsayım: seri bozulduktan sonra yeniden tavan olasılığı x'ten ve bozulma gününden bağımsız — kaba; bu yüzden ikincil. Walk-forward'da r yalnız seans tarihi < T(k) olan arz-günlerden.
- **Beklenen getiri eşlemesi v0'da yok.** Neden: E[R_h] = Σ_l P(L = l)·E[R_h | L = l] ister; koşullu hücreler 99 arzda 11 × 4'e bölünür (hücre başına 3–18 arz) ve seri bozulduktan sonraki getiri ayrı bir modeldir. Uygulama yalnız şu bilgiyi gösterebilir: "seri k gün sürerse kapanış ≈ arz fiyatı × 1.1^k (fiyat adımı yuvarlamasıyla yaklaşık)". Getiri tahmini V1.5/V1.6'nın işidir.

## 9. Walk-forward planı (V1.5'ten farkı)

Test arzı k (T = `first_trading_date`, f3 dolu). Aday eğitim arzı j: `first_trading_date(j) < T` ve f3 dolu.
- j'nin PP satırı (j, d) eğitime ancak `target_session_date(j, d) < T` ise girer (kesin öncelik; V1.5'in `≤ T − 1 gün` kuralıyla aynı sınır: `legacy/scripts/modeling/fold_engine.py:112` ve `common.py:136-143`). İlk geçmeyen d'de durulur: j sağdan sansürlenir.
- **Fark:** V1.5 ufuk başına "hedefi tümüyle gerçekleşmiş" arzları alır; burada kısmi seriler de girer. Sansür takvimle belirlenir, sonuçla değil → hazard tahmini yansız [ÇIKARIM].
- Aynı gün listelenen arzlar birbirini eğitmez (kesin `<`).
- Skorlanabilirlik: eğitim PP kümesinde **≥ 10 arz, ≥ 5 olay, ≥ 5 sağ kalım**. Değilse `INSUFFICIENT_TRAINING_HISTORY`. [ÖLÇTÜM] `m2_cikti.txt:1`: 87 fold; ilki EKOS 2023-11-21 (eğitim: 10 arz, 6 olay, 64 sağ kalım). Grup başına olay eşiği 56–78 fold'a düşürdüğü için seçilmedi (`m1_cikti.txt:30-33`); onun yerine pseudo-satırlar var.
- Her fold: iç CV ile λ seç → fold eğitimiyle nihai fit → test arzı için S_1..S_10, P_close.
- Fold ledger sütunları: test_ticker, T, n_train_ipo, n_pp_rows, n_events, training_tickers_sha256, selected_lambda, λ skor tablosu, γ(3), β(3), hazard_1..10, S_1..10, P_close_1..10, L_gerçek, durum.
- Koşu `experiments/log.jsonl`'a otomatik düşer (kural 4).

## 10. Aynı fold'larda skorlanacak basit kurallar

Hepsi aynı 87 fold'da, aynı PP eğitim kümesinden, aynı şemada (S_1..S_10 üretir):
1. `base_km_expanding`: Kaplan–Meier, S_k = Π_{d ≤ k}(1 − olay_d/risk_d), eğitimdeki tüm arzlar. risk_d = 0 ise o gün için hazard = önceki günün hazard'ı.
2. `base_km_last10`: aynı, ama her d için yalnız (j, d) satırı eğitimde bulunan **son 10 arz** (first_trading_date, ticker sırasıyla).
3. `base_always_ceiling`: S_k = 1, tüm k.
4. `ceiling_hazard_v0@INF` (yalnız gün-grubu sabitleri): ızgaranın uç noktası ayrıca bir kural satırı olarak raporlanır.
5. `v1_5_p_up_as_ceiling`: yalnız k ∈ {1, 3, 5, 10} ve yalnız `P_close_ceiling` hedefinde; V1.5 Logit'in aynı fold'daki p_up'ı (AUDIT §3b). V1.5'in skorlanamadığı fold'larda eşleşik küme küçülür, n raporlanır.

## 11. Sonuç görülmeden yazılan beklenti

Bu bölüm hiçbir tavan modeli fit edilmeden yazıldı (2026-09-21). Backtest H99 üzerinde ve tasarım H99 marjinalleri görülerek yapıldığı için geriye dönük sonuçlar **tasarıma maruzdur**; kanıt değeri düşüktür. Asıl ölçüm prospektiftir (CITAS, VEYAS, TKNKA, KPEKS, INTET, BKRGY, NETGL ve sonrası).

Beklenti [ÇIKARIM]:
- Backtest RPS farkı (model − en iyi KM kuralı): −0.005 … −0.02; blok bootstrap %95 aralığı büyük olasılıkla 0'ı içerir (V1.5 Logit'in D1 Brier farkı −0.008 [−0.028, +0.011], AUDIT §1.2-c; çözünürlük ~0.02, AUDIT §3b).
- En çok kazanç k = 3…5'te (azınlık 31–33); k = 1'de küçük; k = 10'da ≈ 0 ya da hafif kötü.
- Seçilen λ çoğu fold'da 10–300; erken fold'larda INF sık.
- Nihai fit'te işaretler: β_f3 < 0, β_f1 > 0, β_f2 > 0.

Başarı sayılacak (yalnız prospektif, n ≥ 30): RPS eşleşik farkı, `base_km_last10` **ve** `base_km_expanding`'in ikisine karşı da, blok bootstrap %95 aralığı 0'ı dışlayarak negatif.
Başarısızlık sayılacak: (a) prospektif n ≥ 30'da aralık 0'ı pozitif tarafta dışlıyor; ya da (b) |ortalama S_1 − gözlenen D1 tavan oranı| > 0.15 (kalibrasyon); ya da (c) backtest'te model `@INF` kuralından noktasal olarak kötü → "özellikler bilgi eklemiyor" diye yazılır.
Ara durum (aralık 0'ı içeriyor): "ayırt edilemiyor". n < 30'da hüküm verilmez; n < 10'da yalnız satır tablosu (SPEC_SCORING §8).
**Backtest kötü çıksa da v0 bu şartnameyle dondurulur.** Sonuca bakıp özellik/grup/ızgara değiştirmek = yeni model_id + deney günlüğü satırı; v0'ın yerine geçmez.

## 12. Sözde kod

```
def build_pp(ipos, cutoff_T=None):            # ipos: f3 dolu arzlar, (ftd, ticker) sıralı
    rows = []
    for i in ipos:
        for d in 1..10:
            if d - 1 > i.L: break
            if cutoff_T is not None and session_date(i, d) >= cutoff_T: break
            rows.append((i.ticker, d, g(d), event = int(i.L == d - 1)))
    return rows

def fit_hazard(ipos_train, pp_rows, lam):
    prep = preprocess_ipo_level(ipos_train, features=[f1, f2, f3])   # ln, kırpma, z; μ,σ,p05,p95 döner
    Z = {ticker: z-vektörü}
    data = [(Z[t], g, e, w=1.0) for (t, d, g, e) in pp_rows]
    data += [(0-vektör, g, e, w=0.5) for g in (1,2,3) for e in (0,1)]
    if lam == INF: gamma_g = logit((ev_g + 0.5)/(risk_g + 1)); beta = 0
    else: (gamma, beta) = newton(J, init=(gamma_INF, 0), tol=1e-10, max_iter=100)
    return {prep, gamma[3], beta[3], lam}

def select_lambda(ipos_train, pp_rows):
    for lam in GRID:
        nll = 0; m = 0
        for j in ipos_train (en az bir PP satırı olanlar):
            fit = fit_hazard(ipos_train - {j}, pp_rows - rows(j), lam)   # ön işleme yeniden
            for r in rows(j): nll += -log_clip(p(event_r | fit)); m += 1
        score[lam] = nll / m
    return argmin(score, tie -> max lam)

def predict(params, inputs):                  # stdlib
    if inputs.f3 is None: return REFUSED_F3_MISSING
    z = standardize(clip(features(inputs)))   # uyarılar toplanır
    for d in 1..10: hazard[d] = sigmoid(gamma[g(d)] + dot(beta, z))
    S[k] = prod_{d<=k}(1 - hazard[d])
    Pclose[1] = S[1]; Pclose[k>=2] = S[k] + (1 - S[k]) * r[b(k)]
```

Model JSON ek alanları: `day_groups: {"g1":[1],"g2":[2,3],"g3":[4,…,10]}`, `gamma`, `beta`, `lambda`, `lambda_score_table`, `reclose_rates: {r_a, r_b, n_a, a_a, n_b, a_b}`, `pseudo_rows: {weight: 0.5}`, `training.{tickers, tickers_sha256, n_ipo, n_pp_rows, n_events, cutoff_date, data_version_sha256}`, `feature_ranges`.

## 13. Kabul testleri

1. **PP sayımı:** tüm kohort → 508 satır, 85 olay; gün başına risk/olay §2 tablosuyla eşit; grup toplamları 99/18, 151/15, 258/52. f3 dolu 97 arzla: 506 satır, 83 olay.
2. **Fold kurulumu:** 87 skorlanabilir fold; ilki EKOS (10 arz, 6 olay, 64 sağ kalım); ALBTN ve ENDAE hiçbir eğitim kümesinde ve test kümesinde yok. Sızıntı testi: her fold'da max(eğitim seans tarihi) < T.
3. **Sansür:** T'den 3 seans önce listelenmiş sentetik arz eğitime tam 3 satırla (ya da seri daha önce bozulduysa daha azıyla) girer.
4. **Tutarlılık:** rastgele 1000 girdi + 99 eğitim satırı: 1 ≥ S_1 ≥ … ≥ S_10 ≥ 0; ΣP_L = 1 (|Δ| ≤ 1e-12); P_close[k] ≥ S[k]; P_close[1] = S[1].
5. **λ = INF kapalı biçim:** γ_g = logit((olay_g + 0.5)/(risk_g + 1)); tüm kohortla S_1 = 1 − 18.5/100.
6. **Çözücü:** sentetik veride (pseudo-satırsız, λ > 0) sonuç, aynı amaç fonksiyonunun `scipy.optimize.minimize(BFGS)` çözümüyle |Δ| ≤ 1e-6; ∇ normu ≤ 1e-10. Ceza γ'ya uygulanmıyor: λ = 1e9 ile fit edilen γ, λ = INF kapalı biçimine |Δ| ≤ 1e-6 eşit ve ‖β‖ ≤ 1e-6.
7. **Seçim kuralı:** iki λ'nın skoru eşitlenmiş sentetik tabloda büyük olan seçilir; INF ızgarada.
8. **JSON ↔ fit paritesi:** 97 eğitim arzında stdlib `predict` ile numpy nihai model |Δ| ≤ 1e-12.
9. **Ret/uyarı:** f3 = None → `REFUSED_F3_MISSING`; f3 = 0.5 ve 50 → kırpma işareti; f1 aralık dışı → uyarı; tahmin yine üretilir.
10. **Kurallar aynı fold'da:** `base_km_*` ledger'ındaki test_ticker kümesi modelinkine eşit (87).
11. **Deney günlüğü:** backtest koşusu `experiments/log.jsonl`'a bir satır ekler; spec sha = bu dosyanın sha256'sı.

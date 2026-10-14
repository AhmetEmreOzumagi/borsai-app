# SPEC_PB_V0 — talep toplama öncesi modeller (`pb_v0`, `pb_ceiling_v0`)

## Özet (≤ 10 satır)

1. Amaç: f3 (talep katı) henüz yokken, yalnız SPK onaylı **planlanan** arz yapısından tahmin. V1.5'in f3'süz kullanımının (geçersiz kullanım, AUDIT §1.2-d) yerini alır.
2. `pb_v0`: V1.5 ile aynı sınıf (ufuk başına Ridge → R_h, L2-Logit → p_up; h = D1, D3, D5, D10), özellikler pb1, pb2, pb3; ızgara V1.6'nınki ("yalnız sabit terim" dahil).
3. `pb_ceiling_v0`: SPEC_CEILING_V0'ın aynısı, özellikler yalnız pb1, pb2 (2 katsayı + 3 gün sabiti). Aynı kod, farklı özellik listesi ve kesim.
4. pb4 (ek satış tavanı) özellik DEĞİL: 99 arzın 92'sinde 0. Doğrulama ve uyarı alanı olarak kalır.
5. Bilgi kesimi listeleme değil **ilk talep toplama günü** B(k): eğitim satırı ancak hedef seansı < B(k) ise girer. Ölçülen fold: D1/D3/D5 87, D10 84.
6. Eksik ya da özdeşliği bozuk girdi → RET (imputasyon yok). Fiyat aralıklı arz → RET (H99'da örneği yok).
7. Beklenti: D1'de taban oranından/medyandan ayırt edilemez; olası küçük kazanç D5–D10 getirisinde. Geriye dönük sonuç tasarıma maruzdur; asıl ölçüm prospektiftir.
8. Bu model f3'lü modellerle aynı arzda yan yana skorlanır; "PB" sütunu uygulamada f3 boşken dolu olan tek model sütunudur (AUDIT §3d).

İşaretler: **[ÖLÇTÜM]** / **[ÇIKARIM]**. Ölçümler: `docs/specs/ekler/m2_cikti.txt` (script `m2_fold_pb_market.py`). Hiçbir PB modeli fit edilmedi.

---

## 1. Kimlik ve veri

- `model_id`: `pb_v0` ve `pb_ceiling_v0`. Değişiklik = yeni kimlik.
- Girdi kaynağı: `data/raw/PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv` (sha256 `5e52d4d2…`, `docs/PROVENANCE.md` §1 satır 9). 99 satır; ticker kümesi ve ilk işlem tarihleri `training_table.csv` ile birebir [ÖLÇTÜM `m2_cikti.txt:5`]. Tüm satırlarda `pit_status = PASS`, kural `SPK_PUBLICATION_DATE < FIRST_BOOKBUILDING_DATE` [ÖLÇTÜM `:15`].
- Hedefler: `training_table.csv`'den `R_Dh`, `Y_Dh`, `ceiling_streak_L`; seans tarihleri SESSIONS dosyasından (SPEC_CEILING_V0 §2).
- Birleştirme anahtarı: `ticker`. Opus `data/build_training_table.py`'ye DOKUNMAZ; PB sütunları `borsai/` içinde okunur (yeni tablo = yeni veri sürümü olurdu).

## 2. Özellikler

Tanımlar `legacy/scripts/modeling/prebookbuild_v1_r6/pb_core4.py:98-160`'tan aynen; `borsai/features.py`'ye tek tanım olarak taşınır.

| Ad | Tanım | PB CSV sütunları | Ön işleme |
|---|---|---|---|
| pb1 | ln(`ipo_price_try` × `planned_base_offer_shares`) | aynı adlar | z-skor |
| pb2 | `planned_base_offer_shares` / `planned_post_ipo_capital` × 100 | | z-skor |
| pb3 | `planned_capital_increase_shares` / `planned_base_offer_shares` × 100 | | z-skor |
| pb4 | `planned_additional_sale_ceiling` / `planned_base_offer_shares` × 100 | | **özellik değil**; yalnız doğrulama + uyarı |

[ÖLÇTÜM `m2_cikti.txt:7-11`] pb1 19.49–22.64 (medyan 21.13); pb2 10.01–40.47; pb3 22.2–100 (17 arzda 100); pb4: 92 arzda 0, 5'te 20, birer arzda 18.4 ve 10.
pb4'ün dışlanma gerekçesi: bilgi içeriği 7 satır (AUDIT §1.2-f ile aynı mantık). Winsorize ve log (pb1 dışında) yok. z-skor eğitim ortalaması ve popülasyon std'si (ddof = 0).

Zorunlu doğrulamalar (hepsi Decimal, tam eşitlik; `pb_core4.py:122-150`):
- ID-A: post = pre + capital_increase. ID-B: base = capital_increase + existing_sale. ID-C: max = base + additional_sale_ceiling.
- base > 0, post > 0, fiyat × base > 0; pb2, pb3 ∈ (0, 100]; pb4 ≥ 0.
- [ÖLÇTÜM] 99/99 satırda üç özdeşlik tutuyor (script'te assert; `m2_fold_pb_market.py`).
- Legacy'deki `additional_sale_semantics` token denetimi TAŞINMAZ (form alanı serbest metin değil, sayı olacak). pb4 > 0 ise uyarı: "ek satış tavanı var; eğitimde 7 örnek".

Planlanan ≠ nihai [ÖLÇTÜM `:12`]: fiyat 0/99 arzda farklı; pay adedi 10/99; sermaye artırımı payı 2/99. Yani pb1–pb3 çoğu arzda f1, f2, f4'e eşittir; PB'nin V1.5'ten asıl farkı f3/f5'in yokluğu ve bilgi kesimidir [ÇIKARIM].

## 3. `pb_v0`: model sınıfı, ızgara, seçim

Ufuk başına iki bağımsız kafa, V1.5 ile aynı sözleşme (`legacy/scripts/modeling/candidate_models.py:19-40`):
- Ridge: `fit_intercept=True`, `solver="svd"`, hedef dönüşümü yok; iç LOOCV amaç = MAE; eşitlikte büyük α.
- Logit: `l1_ratio=0.0`, `lbfgs`, `max_iter=10000`, `tol=1e-10`, `class_weight=None`; iç LOOCV amaç = ham Brier; eşitlikte küçük C. Tek sınıflı eğitim → `MODEL_NOT_FIT_SINGLE_CLASS`; azınlık < 2 → ayarsız, C = "yalnız sabit terim" (V1.5'teki 0.01 yedeği yerine; PB'de en muhafazakâr seçenek ızgaranın kendisinde var).
- Izgara **SPEC_V1_6 §3 ile birebir**: α ∈ {0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000, INF}; C ∈ {ZERO, 0.0001, 0.001, 0.01, 0.1, 1, 10, 100}. INF/ZERO = yalnız sabit terim (kapalı biçim: eğitim ortalaması / eğitim oranı). Aday başına yakınsamama kuralı da oradan.
- İç LOOCV'de ön işleme her iç bölmede ham satırlardan yeniden kurulur.

## 4. Parametre bütçesi

[ÖLÇTÜM `m2_cikti.txt:16-23`] Azınlık (Y = 0) sayıları, tüm kohort / skorlanabilir: D1 10/10, D3 19/19, D5 22/22, D10 29/27.
- Ridge: 3 katsayı + sabit, n = 99 sürekli hedef → katsayı başına ≈ 25 gözlem; kabul.
- Logit: 3 katsayı D1'de (10 olay) bütçenin ÜSTÜNDE (10–15 kuralı 1 katsayıya izin verir); D3–D10'da sınırda (19–29 olay → 2). Kafa başına ayrı özellik listesi tutmak yerine tek liste + güçlü büzme + ZERO uç noktası seçildi; D1'de beklenti "ZERO ya da C ≤ 0.001 seçilir, taban oranından ayırt edilemez" [ÇIKARIM]. Bu bir taviz; raporda D1 p_up'ı "bütçe üstü" notuyla gösterilir.

## 5. Eksik veri ve ret davranışı

| Durum | Davranış |
|---|---|
| 8 sayısal alandan biri boş/ayrıştırılamıyor | **RET** `REFUSED_PB_FIELD_MISSING:<alan>` (imputasyon yok) |
| ID-A/B/C ya da aralık ihlali | **RET** `REFUSED_PB_IDENTITY:<ad>` |
| Fiyat tek değer değil (fiyat aralığı) | **RET** `REFUSED_PB_PRICE_RANGE` (H99'da 99/99 `SPK_APPROVED_PLANNED_IPO_PRICE`, tek fiyat) |
| Girdi eğitim min/max dışında | tahmin + uyarı |
| pb4 > 0 | tahmin + uyarı |
| R_h çıktısı fiziksel sınır dışı | [0.9^h − 1, 1.1^h − 1]'e kırp + işaretle (çekirdek kuralı) |

Ret, dondurma kaydında o model için "ret + neden" olarak yazılır; arz sicilden düşmez (kural 2).

## 6. Walk-forward planı (V1.5'ten farkı)

- Test arzı k için bilgi kesimi **B(k) = `first_bookbuilding_date`** (PB CSV). Eğitim satırı (j, h) ancak `target_session_date(j, D_h) < B(k)` ise girer. V1.5'te kesim T(k)'dır. [ÖLÇTÜM `:14`] T − B: min 4, medyan 8, maks 12 gün.
- `first_trading_date(j) < B(k)` zaten bunun sonucudur; yine de açık assert.
- MIN_TRAIN_N = 10 (ufuk başına etkin n). [ÖLÇTÜM] fold sayısı D1 87, D3 87, D5 87, D10 84; n_eff 12…95/94/94/92.
- Sıra: (first_trading_date, ticker). Aynı B(k)'li arzlar birbirini eğitemez (hedefleri B'den sonra).
- Nihai fit (dondurulacak JSON): 99 arzın hepsi, hedef seansları ≤ 2026-08-19.
- Prospektif kullanımda kesim anlamı: JSON sabit kesimlidir; yeni arzın B(k)'si 2026-08-19'dan sonra olduğu için sızıntı yoktur.

## 7. Aynı fold'larda basit kurallar

`base_always_ceiling`, `base_train_median`, `base_train_mean`, `base_zero`, `base_rate`, `base_last10_rate` — hepsi **PB kesimiyle** (B(k)) kurulan aynı eğitim kümesinden, aynı test arzlarında. Çekirdek backtest'in kesim fonksiyonu parametre almalı (`cutoff = "first_trading_date" | "first_bookbuilding_date"`).
Ek karşılaştırma (kural değil, bilgi): `v1_5_h99` ile eşleşik küme = iki modelin de skorlandığı test arzları. Beklenen: f3'lü model daha iyi; fark "talep katının değeri"dir.

## 8. Sonuç görülmeden yazılan beklenti (`pb_v0`)

2026-09-21'de, hiçbir PB fit'i görülmeden yazıldı. Eski PB V1 hiç metrik üretmedi (CHECKUP `detay/A2_PB_V1_ve_V2.md:162`); önceden bilinen PB sonucu yok. Backtest H99 üzerinde ve özellik seçimi H99'un pb dağılımları görülerek yapıldığı için geriye dönük sonuçlar **tasarıma maruzdur**.

Beklenti [ÇIKARIM]:
- D1 MAE: `base_train_median`'a YENİK ya da eşit (V1.5 bile f3'le yeniliyor: +0.0046 [+0.0015, +0.0079], AUDIT §1.2-c). D1 p_up: taban oranından ayırt edilemez.
- D5/D10 MAE: medyana karşı noktasal küçük kazanç mümkün (V1.5'in −0.084 / −0.116'sının en çok üçte biri); aralık büyük olasılıkla 0'ı içerir.
- V1.5'e karşı: her ufukta daha kötü ya da eşit.
- Seçilen α çoğunlukla ≥ 100; D1'de INF sık.

Başarı (prospektif, n ≥ 30): D5 **ya da** D10 MAE'de `base_train_median`'a karşı eşleşik fark aralığı 0'ı dışlayarak negatif. Birincil ufuk önceden: **D5**.
Başarısızlık: prospektif n ≥ 30'da D5 MAE farkı aralığı 0'ı pozitif tarafta dışlıyor → uygulama PB sütununda "basit kural daha iyi" yazar; model listede kalır.
Backtest kötü çıksa da v0 bu şartnameyle dondurulur; değişiklik = yeni model_id.

## 9. `pb_ceiling_v0`

SPEC_CEILING_V0'ın tamamı geçerli; yalnız şu farklar:
- Özellikler: pb1, pb2 (z-skor; kırpma yok). 2 katsayı + 3 gün sabiti = 5 parametre. pb3 bütçe ve a priori zayıflık nedeniyle dışarıda.
- Eğitim: 99 arzın hepsi (f3 şartı yok; ALBTN ve ENDAE dahil).
- Walk-forward kesimi B(k): PP satırı (j, d) ancak `target_session_date(j, d) < B(k)` ise girer. Skorlanabilirlik kuralı aynı (≥ 10 arz, ≥ 5 olay, ≥ 5 sağ kalım). Fold sayısı bu oturumda ÖLÇÜLMEDİ; Opus ledger'dan raporlar (beklenen 84–89).
- Ret kuralları §5'teki gibi (f3 şartı yok).
- Kurallar: `base_km_expanding`, `base_km_last10`, `base_always_ceiling`, `@INF` — B(k) kesimiyle.
- Beklenti: RPS'te KM kurallarından ayırt edilemez; `ceiling_hazard_v0`'dan kötü ya da eşit. Başarı/başarısızlık ölçütü SPEC_CEILING_V0 §11 ile aynı.
- Gerekçe: kullanıcı arzı talep toplamadan önce gördüğünde tavan olasılığını da soracak; şimdi dondurulmazsa 7 arz bu model için harcanır (AUDIT §3, "önce dondur"). Maliyet: aynı kodun ikinci çağrısı.

## 10. Sözde kod (`pb_v0`)

```
def pb_features(row):                          # Decimal/Fraction; ihlalde PBRefusal
    v = {f: parse_decimal(row[f]) for f in REQUIRED_8}      # boş -> REFUSED_PB_FIELD_MISSING
    check ID-A, ID-B, ID-C, pozitiflik, aralıklar           # -> REFUSED_PB_IDENTITY
    pb1 = ln(v.price * v.base)  (Decimal prec 60 -> float)
    pb2 = base/post*100; pb3 = capinc/base*100; pb4 = addl/base*100
    return pb1, pb2, pb3, warnings(pb4 > 0)

def plan_folds_pb(h):
    for k in sorted(ipos, key=(ftd, ticker)):
        train = [j for j in ipos if session_date(j, D_h) < B(k)]
        status = OK if len(train) >= 10 else INSUFFICIENT_TRAINING_HISTORY

def fit_head(train, h):                        # V1.6 ile aynı fonksiyon, özellik listesi [pb1,pb2,pb3]
    alpha = select_by_inner_loocv(GRID_ALPHA, objective=MAE, tie=max)      # INF -> mean
    C     = select_by_inner_loocv(GRID_C, objective=Brier, tie=min)        # ZERO -> rate
    return ridge{alpha, intercept, coef[3]}, logit{C, intercept, coef[3]}

predict(params, inputs): features -> z -> her h: return=clip(intercept+coef·z), price=ipo*(1+return), p_up=sigmoid(...)
```

## 11. Kabul testleri

1. 99 PB satırının hepsi özellik üretir; ID-A/B/C 99/99; pb4 sıfır olmayan tam 7 arz; pb3 = 100 olan 17 arz.
2. `pb_core4.build_pb_core4` (legacy, import ederek) ile pb1–pb4 paritesi 99/99: pb2–pb4 bit-eşit (Fraction→float), pb1 |Δ| ≤ 1e-12.
3. Fold sayıları: D1 87, D3 87, D5 87, D10 84; min n_eff 12. Sızıntı: her fold'da max(eğitim hedef seans tarihi) < B(k).
4. Yasak girdi testi: `pb_v0` özellik vektörü kurulurken `total_demand_multiple`, `shares_offered`, `additional_sale_shares` ve herhangi bir `R_*`, `Y_*`, `ceiling_*` sütunu okunmaz (özellik fonksiyonuna bu sütunlar olmadan satır verilir, geçer).
5. Ret: bir alan boş → `REFUSED_PB_FIELD_MISSING`; base ≠ capinc + existing → `REFUSED_PB_IDENTITY`; fiyat "10-12" → `REFUSED_PB_PRICE_RANGE`. Çıplak exception yok.
6. JSON ↔ sklearn paritesi 99 satırda |Δ| ≤ 1e-12; INF/ZERO seçilmiş sentetik durumda çıktı = eğitim ortalaması/oranı.
7. Kurallar PB kesimiyle aynı test kümesinde (ledger ticker kümeleri eşit).
8. `pb_ceiling_v0`: SPEC_CEILING_V0 §13 testleri 1 (99 arz → 508/85), 3–8, 10–11; f3 = None iken RET ETMEZ.

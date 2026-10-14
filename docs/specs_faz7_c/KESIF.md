# KEŞİF — "Düşen halka arzların ortak özellikleri" (C sorusu)

Görev: BORSAI_FAZ7_FABLE_C_SPEC_20260927. Yazım: 2026-09-27, Fable. **Etiket: keşif, H99 + açık küme, doğrulanmadı.** Kasa (64 arz) açılmadı; hiçbir kasa üyesinin dosyası okunmadı. Betik ve ham çıktı: `ekler/kesif_c.py`, `ekler/kesif_c_cikti.txt`; denenen her varyant `ekler/denenenler.csv` (2 054 satır). Şartname: `SPEC_C_V0.md`.

## Sade özet (proje sahibi için)

1. "Düşen" derken ilk 10 seansın sonunda (D10) arz fiyatının altında ya da arz fiyatında kapanan arzları aldım. Bu, elimizdeki 170 arzın 42'sinde oldu: yeni dönemde (H99, 2023-09'dan bugüne) 99 arzın 29'u, eski dönemde (2020–2023 açık küme) 71 arzın 13'ü.
2. **Düşenlerin en belirgin ortak yanı ek satış hakkının kullanılmış olması.** Ek satış yapılan 19 arzın 12'si D10'da arz fiyatının altındaydı (%63); yapılmayan 151 arzın yalnız 30'u (%20). Bu iki dönemde de aynı yönde: yeni dönemde 6 arzın 4'ü, eski dönemde 13 arzın 8'i. Ama ek satışlı arz sayısı az (19), bu yüzden güven sınırlı.
3. **İkinci ortak yan düşük talep katı.** Talep katı 2'nin altında olan 42 arzın 19'u düştü (%45); 2'nin üstünde olan 123 arzın 21'i (%17). Yeni dönemde bu ayrım güçlü, eski dönemde zayıf (eski dönemde talep katları genelde çok yüksekti ve düşenleri ayırmıyor).
4. **Üçüncü ortak yan büyük arz.** Reel büyüklüğü (bugünkü fiyatlarla) 2 milyar TL'yi aşan 73 arzın 28'i düştü (%38); daha küçük 97 arzın 14'ü (%14). Her iki dönemde de aynı yön.
5. Yükselenlerden ayrılmayan ya da dönemden döneme işaret değiştiren yanlar: halka açıklık oranı, sermaye artırımı payı, arz fiyatının düzeyi, borsa endeksinin son 20 seans getirisi, aynı hafta listelenen arz sayısı, fiyat istikrarı planı, ihraççı ve ortak satmama süreleri, bireysele eşit/oransal dağıtım, GYO olma. Bunlar tek başına ayırt edici çıkmadı ya da yalnız bir dönemde göründü.
6. İlk gün tavan yapmamayı (D1) en iyi yine düşük talep katı ve büyük reel arz büyüklüğü açıklıyor; bunu var olan tavan modeli (`ceiling_hazard_v0`) zaten görüyor (iki dönemde de ayırma gücü yüksek). Ek satış burada az şey ekliyor.
7. Var olan getiri modeli (V1.5) D10'da düşüşü yeni dönemde bir miktar görüyor ama eski dönemde taban orandan iyi değil. Yani bugünkü modeller "düşer mi" sorusunu eski dönemde göremiyor; yeni bir küçük model için yer var.
8. **Ne kadar güvenilir:** Bu sayılar 170 arzdan, sonuçlar görüldükten sonra ve 2 054 varyant denenerek çıktı; bir kısmı şans eseri olabilir. Üç özelliği (ek satış, talep katı, reel büyüklük) birlikte kullanan küçük bir model, yalnız yeni dönemde eğitilip eski dönemde denendiğinde taban orandan iyi çıkıyor ama fark küçük ve aralık 0'ı içeriyor; tersi yönde (eski → yeni) aralık 0'ı dışlıyor. Kesin hüküm ancak kasadaki 64 arzda, önceden yazılmış şartnameyle verilecek; orada beklenen düşen sayısı yaklaşık 12'dir, bu yüzden kasa testinin de "ayırt edilemiyor" demesi olasıdır.
9. Kişi başına dağıtılan pay (yatırımcı sayısı) eski dönemde güçlü görünüyor ama yeni dönemin yalnız 20 arzında elimizde var; önce 79 arz için toplanmalı (ön koşul görevi).
10. Sonuç: "Düşenler: ek satış yapılmış, talep katı düşük, reel büyüklüğü yüksek arzlar" — dönemler arası tutarlı ama zayıf-orta güçte bir işaret. Şartname bu üç özellikle 1–3 küçük aday model tanımlar; doğruluk iddiası kasa açılınca ve canlı sicilde ölçülür.

---

## 1. Kümeler ve olay tanımları [ÖLÇTÜM]

Keşif kümesi: H99 (99 arz, ilk işlem 2023-09-22…2026-08-06) + eski kohortun açık kümesi (71 arz; `data/outcomes_oot/*.csv`, ilk işlem 2020-08…2023-09). Veri: `data/training_table_v2.csv` (girdiler, sonuçlar, TÜFE), `registry/oot/candidate_features{,_faz7}/` (yalnız açık üyeler), H99 ana tablosu (aday alanlar yalnız 20 üyede), donmuş model tahminleri (H99: walk-forward ledger'ları; açık: S2 kayıtları).

Hedef tanımları (SPEC_SCORING §3 alanlarıyla; sonuç = resmi THB/THM):

| hedef | tanım | H99 (99) | açık (71) | kesin-altı (R_h < 0) H99 / açık |
|---|---|---|---|---|
| y1 | D1'de tavan yok (`ceiling_close_D1 = 0`, L = 0) | 18 (%18) | 9 (%13) | — |
| y2 | D1 kapanışı ≤ arz (`1 − Y_D1`) | 10 (%10) | 2 (%3) | 10 / 1 |
| y3 | D5 kapanışı ≤ arz (`1 − Y_D5`) | 22 (%22) | 11 (%15) | 19 / 11 |
| **y4** | **D10 kapanışı ≤ arz (`1 − Y_D10`)** | **29 (%29)** | **13 (%18)** | 29 / 12 |

Yıl kırılımı (y1 / y4): H99 2023: 1/5 (n 19), 2024: 6/9 (33), 2025: 6/8 (18), 2026: 5/7 (29); açık 2020: 0/0 (4), 2021: 6/8 (26), 2022: 3/4 (20), 2023: 0/1 (21). Tahsis rejimi (açık): PRE_20211111 5/7 (25), THRESH100 4/5 (31), EQUAL_DIST 0/1 (15). Satış yöntemi (açık): borsada satış 1/3 (27), borsa dışı 8/10 (44).

**Kasa için beklenen olay sayısı** (kasanın yıl sayımları 2020: 4, 2021: 26, 2022: 18, 2023: 16 × açık kümenin yıl oranları; kasa sonucu yoktur):

| hedef | yıl ağırlıklı | rejim ağırlıklı | açık havuz oranı | H99 oranı (üst sınır) |
|---|---|---|---|---|
| y1 | 8.7 | 8.8 | 8.1 | 11.6 |
| y2 | 1.9 | 1.9 | 1.8 | 6.5 |
| y3 | 10.5 | 10.7 | 9.9 | 14.2 |
| **y4** | **12.4** | **12.6** | **11.7** | **18.7** |

**Birincil hedef seçimi [KARAR]: y4.** Gerekçe: (i) hüküm eşiği: kasada n ≈ 60–62 skorlanabilir arz (SPEC_SCORING §8 n ≥ 30 sağlanır) ve en çok olay (≈ 12) y4'tedir; y2'de beklenen 2 olay ile hiçbir hücre hüküm veremez; (ii) ürün değeri: proje sahibinin sorusu "düşer mi"dir, D10'da arz altı kapanış bunun en doğrudan ve en sık ölçümüdür; (iii) var olan modeller: `ceiling_hazard_v0` y1'i iki dönemde de iyi görüyor (AUC 0.81 / 0.80), V1.5 y4'ü eski dönemde görmüyor (açık kümede Brier taban orandan +0.014 kötü, AUC 0.51) → boşluk y4'tedir. **İlan edilmiş ikincil hedef: y3** (D5 kapanışı ≤ arz; aynı model ailesinin D5 başlığı). y1 ve y2 yalnız keşif.

Not: 1 − Y_h tanımı kapanış = arz fiyatı durumunu da "düştü" sayar (H99'da fark yok; açık kümede D10'da 1 arz). Kesin-altı tanımı açık soru 1'dedir.

## 2. Özellik envanteri ve tanım uyumu

| alan | H99 | açık | kasa (dolu) | tanım uyumu | canlı (registry/inputs) |
|---|---|---|---|---|---|
| f1 = ln büyüklük (nominal TL); **f1r** = ln(büyüklük / TÜFE_{m−2}) | 99 | 71 | 64 | tek tanım (`borsai.features`, `borsai.tufe`; v1_real ile aynı) | var (v1 dondurmasıyla TÜFE bloğu) |
| f2 halka açıklık % | 99 | 71 | 64 | tek tanım | var |
| f3 talep katı | 97 | 68 | 62 | tek tanım; borsada satışta çoğunlukla yok → RET | var |
| f4 sermaye artırımı payı % | 99 | 71 | 64 | tek tanım | var |
| **ek satış** = 1[`additional_sale_shares` > 0] | 95 (4 boş) | 70 (1 boş) | 62 | tek tanım (SPK bülteni dipnotu / sonuç bildirimi; H99 ve eski kohortta aynı alan) | **var** (`V15_FIELDS`) |
| arz fiyatı (ln) | 99 | 71 | 64 | tek tanım | var |
| f6 XU100 20 seans | 99 | 71 | — | Takvim B / Takvim C (aynı kural) | var (market20) |
| aynı hafta arz sayısı (±5 iş günü; H99 + kohort tarihleri) | 99 | 71 | — | deterministik; canlıda "sonraki 5 gün" duyuruya bağlı (nedensellik) | yok |
| tahsis rejimi | 99 (hepsi EQUAL) | 71 | 64 | `registry.alloc_regime` tek tanım | canlıda sabit (EQUAL) |
| satış yöntemi (borsada / borsa dışı), pazar | **20** | 71 | 64 | BIST listeleme bildirimi "Halka Arz Yöntemi" | yok (şema genişlemesi) |
| Faz 7: fiyat istikrarı (planlı, gün), ihraççı ve ortak satmama günü, dağıtım yöntemi, sektör | **20** | 71 | 64 | REPORT §3 kuralları açık kümede; H99'un 20'sinde eski repo kodlaması (hepsi 365; `components` yok) → **uyum doğrulanamaz** | yok |
| Faz 7: katılım endeksi uygunluğu | 0 | 16 (55 boş) | 15 | yapısal boşluk (2022-06 öncesi beyan yok) → **dışlandı** | yok |
| Faz 6: yatırımcı sayısı, kişi başı lot, bireysel tahsisat %, grup talep katları, lider aracı kurum | **20 / 17 / 16** | 71 / 70 / 44 | 64 / 63 / 42 | aynı ad ve anlam (ALLOCATED_INVESTOR_COUNT) | yok |

Tanım notları:
- `shareholder_lockup_days`: açık kümede "herhangi bir ortağın borsada satış kısıtının ilk gevşediği gün" (REPORT §3, `components` ile yeniden hesaplanabilir; 40 × 365, 25 × 180, 6 diğer). H99'un 20'sinde tek değer 365; kural belgelenmemiş. 30.03.2023 tarihli 20/412 ilke kararının 180 günlük zorunlu kısıtı EQUAL_DIST rejimiyle çakışır; açık kümede 180 değerleri ağırlıkla 2021–2022'de (14 + 9) ve 2023'te yalnız 3 → rejimle karışma sınırlı ama H99'da alan varyanssız. **Sonuç:** bu alan v0 adaylarına giremez; H99'da `components` düzeyinde yeniden türetme ön koşul görevidir (§5).
- `distribution_method`: açık kümede 8 kalıp; ikili türevler (bireysele eşit / oransal / borsada satış-tahsisatsız) H99'un 20 kalıbıyla eşlenebilir ama H99'da 79 boş.
- `sector`: 67 farklı ifade / 71 arz → yalnız GYO ikilisi anlamlı (6 açık, 3 H99-20).
- H99'un 79 üyesinde aday alanların hiçbiri yok (`DATA_NOT_FOUND`); eski repo yalnız son 20 arz için toplamış.

## 3. Tek değişkenli keşif [KEŞİF]

AUC > 0.5: özellik büyüdükçe olay olasılığı artar. "Dönem" sütunu: H99 / açık ayrı hesaplandığında işaret aynı mı.

### 3.1 y4 (D10 ≤ arz), 170 arz

| özellik | AUC H99+açık | H99 | açık | dönem uyumu | not |
|---|---|---|---|---|---|
| **ek satış** (ikili) | oran 0.63 vs 0.20 | 0.67 vs 0.27 (6 / 93) | 0.62 vs 0.09 (13 / 58) | **aynı yön, her ikisi güçlü** | 19 arz; 2021: 4/6, 2022: 3/4, 2023: 1/3; H99 2023–2025: 4/6 |
| **f1r** (reel büyüklük) | 0.705 | 0.745 | 0.633 | aynı yön | rejim: PRE 0.67, THRESH 0.78, EQUAL-açık 0.43 (n 15, 1 olay) |
| f1 (nominal) | 0.664 | 0.746 | 0.556 | aynı yön, açıkta zayıf | deflasyon açık kümede ayrımı artırıyor |
| **ln f3** (talep katı) | 0.327 | 0.243 | 0.480 | **yalnız H99'da** | eski dönemde talep katları çok yüksek (medyan 4–8), ayırmıyor |
| ln fiyat | 0.617 | 0.619 | 0.527 | zayıf | |
| f2 halka açıklık | 0.447 | 0.406 | 0.570 | **işaret değiştiriyor** | |
| f4 sermaye artırımı | 0.433 | 0.469 | 0.340 | zayıf | |
| f6 XU100 20 seans | 0.456 | 0.499 | 0.418 | yok | |
| aynı hafta arz sayısı | 0.528 | 0.611 | 0.342 | **işaret değiştiriyor** | |
| borsada satış (91) | oran 0.13 vs 0.25 | (3 arz) | 0.11 vs 0.23 | yalnız açık | borsada satış → daha az düşüş; ek satışla ilişkili (borsada satışta ek satış 1/27) |
| fiyat istikrarı planlı (91) | 0.20 vs 0.22 | 0.42 vs 0.12 (12 / 8) | 0.14 vs 0.24 | **işaret değiştiriyor** | |
| ortak satmama < 365 (91) | 0.31 vs 0.17 | varyans yok | 0.31 vs 0.11 | yalnız açık; H99'da sabit | yıl içinde de aynı yön (2021: 0.36 vs 0.25; 2022: 0.33 vs 0.09) |
| ln kişi başı reel TL (91) | 0.681 | 0.821 (n 20) | 0.707 | aynı yön | 2021 içinde ayırmıyor (üst/alt yarı 0.31 / 0.31) |
| bireysel talep katı (60) | 0.384 | 0.240 (16) | 0.425 | zayıf | |
| GYO (91) | 0.22 vs 0.21 | — | 0.17 vs 0.18 | yok | |

### 3.2 y1 (D1 tavan yok), 170 arz

ln f3 AUC 0.166 (H99 0.161, açık 0.183: **iki dönemde güçlü ve aynı**); f1r 0.753 (0.730 / 0.783); f2 0.313 (0.262 / 0.434); ek satış 0.32 vs 0.14 (H99 0.50 vs 0.16; açık 0.23 vs 0.10); kişi başı reel TL 0.80 (0.83 / 0.92); ortak satmama < 365 açıkta 0.27 vs 0.04. Kural: f3 < 2 → 19/42 (%45) tavan yapmadı, ≥ 2 → 6/123 (%5); iki dönemde aynı (H99 0.43 / 0.04; açık 0.50 / 0.05).

### 3.3 y3 (D5 ≤ arz)

y4 ile aynı sıra: ek satış 0.53 vs 0.15 (H99 0.50 / 0.20; açık 0.54 / 0.07); f1r 0.712 (0.749 / 0.650); ln f3 0.310 (0.205 / 0.470: yalnız H99).

### 3.4 y2 (D1 ≤ arz)

Açık kümede 2 olay; yalnız sayım. f1 / fiyat / f3 yönleri y1 ile aynı.

## 4. Var olan donmuş modeller bu olayları ne kadar görüyor [KEŞİF]

H99: walk-forward ledger tahminleri; açık: S2 kaydındaki donmuş tahmin. Fark = Brier(model) − Brier(kural); negatif = model iyi; aralık ay-blok bootstrap (keşif).

| hedef | model → kural | H99 | açık |
|---|---|---|---|
| y1 | `ceiling_hazard_v0` 1 − S_1 → KM | −0.032 [−0.050, −0.015], n 87, AUC 0.81 | −0.010 [−0.023, +0.005], n 68, AUC 0.80 |
| y2 | V1.5 1 − p_up D1 → taban | −0.008 [−0.028, +0.012], n 80 | −0.005, n 68 (2 olay) |
| y3 | V1.5 1 − p_up D5 → taban | −0.034 [−0.076, +0.010], n 81, AUC 0.73 | **+0.010** [−0.019, +0.046], AUC 0.51 |
| **y4** | **V1.5 1 − p_up D10 → taban** | −0.039 [−0.077, +0.003], n 81, AUC 0.74 (MODELS.md ile aynı) | **+0.014** [−0.029, +0.063], n 68, **AUC 0.51** |

Okuma: y1 için var olan tavan modeli yeter; y4 için V1.5'in bilgisi H99'a özgü (f1 nominal, f3; eski dönemde ayırmıyor).

## 5. Çok değişkenli küçük modeller [KEŞİF]

L2 lojistik (standartlaştırılmış özellikler, cezasız sabit; λ ∈ {1, 10}); **arz-bırak (LOO)** havuzda; **aktarım**: yalnız H99'da fit → açık kümede skor (kasa testinin en yakın benzeri) ve tersi. Fark = Brier(model) − Brier(taban oranı; LOO ya da eğitim kohortu oranı). Aralıklar ay-blok bootstrap, keşif.

### 5.1 y4 (D10 ≤ arz)

| özellikler | λ | LOO fark [%95] (n) | H99 → açık (68–71) | açık → H99 (97–99) | AUC açık (H99 fit) |
|---|---|---|---|---|---|
| **f1r + ln f3 + ek satış** | 10 | **−0.036 [−0.057, −0.016]** (165) | **−0.023 [−0.066, +0.016]** | **−0.012 [−0.022, −0.002]** | 0.723 |
| f1r + ln f3 + ek satış | 1 | −0.038 [−0.065, −0.012] | −0.012 [−0.068, +0.039] | −0.012 [−0.028, +0.003] | 0.712 |
| ln f3 + ek satış | 10 | −0.031 [−0.049, −0.015] | −0.026 [−0.060, +0.004] | −0.008 [−0.018, +0.001] | 0.731 |
| f1r + ek satış | 10 | −0.022 [−0.041, −0.005] (170) | −0.023 [−0.055, +0.008] | −0.004 [−0.015, +0.007] | 0.784 |
| **ek satış** (tek) | 10 | −0.016 [−0.031, −0.003] | **−0.024 [−0.049, −0.002]** | +0.001 [−0.009, +0.011] | 0.765 |
| f1r + ln f3 | 10 | −0.019 [−0.035, −0.002] | **+0.001** [−0.038, +0.041] | −0.011 [−0.017, −0.005] | 0.599 |
| f1r | 10 | −0.012 [−0.024, +0.001] | −0.004 [−0.028, +0.023] | −0.010 [−0.017, −0.004] | 0.633 |
| ln f3 | 10 | −0.009 [−0.021, +0.002] | +0.005 [−0.025, +0.035] | −0.003 | 0.520 |
| f1r + ln f3 + ek satış + rejim terimi | 10 | −0.035 | −0.023 | **+0.005** | — |
| ham f3 (winsor, log'suz) + f1r + ek satış | 10 | −0.031 | −0.020 | −0.009 | 0.710 |
| ek satış payı (%; ikili yerine) + f1r + ln f3 | 10 | −0.035 | −0.022 | −0.015 | 0.720 |
| f1r + ln kişi başı reel TL (91) | 10 | −0.008 | **+0.013** (H99-20 fit) | −0.006 | — |
| f1r + ortak satmama < 365 (91) | 10 | −0.005 | −0.007 | +0.001 | — |
| fiyat istikrarı, dağıtım, ihraççı satmama tekli (91) | | 0 ya da pozitif | | | |

Havuz katsayıları (λ = 10, standartlaştırılmış): y4: f1r +0.41, ln f3 −0.52, ek satış +0.56 (ham logit farkı ≈ +1.8). İşaretler beklenen yönde ve iki dönemde aynı.

Okuma [ÇIKARIM]: (i) ek satış y4 için iki dönemde de en tutarlı tek özellik; ama 19 arzdan geliyor ve H99'daki 6 arz tek başına katsayıyı belirleyemiyor (açık → H99 aktarımı ≈ 0). (ii) f1r + ln f3 yalnız H99'da öğrenilirse eski döneme aktarılmıyor (+0.001); ek satış eklenince aktarım −0.023 oluyor. (iii) Rejim terimi y4'te bilgi eklemiyor (LOO −0.035 vs −0.036) ve açık → H99 aktarımını bozuyor; v0 adaylarında rejim terimi yok. (iv) Ham f3 yerine ln f3 daha iyi aktarıyor. (v) Kişi başı reel TL H99'un 20 arzıyla öğrenilemiyor; ön koşul görevi sonrası aday.

### 5.2 y3 (D5 ≤ arz)

f1r + ln f3 + ek satış (λ 10): LOO −0.027 [−0.045, −0.010]; H99 → açık −0.017 [−0.055, +0.017]; açık → H99 −0.010 [−0.022, +0.000]. Ek satış tek: aktarım −0.018 [−0.038, −0.003]. Sıra y4 ile aynı, etkiler biraz küçük.

### 5.3 y1 (D1 tavan yok)

f1r + ln f3 (λ 10): LOO −0.030 [−0.047, −0.014]; H99 → açık −0.032 [−0.064, −0.009]; açık → H99 −0.019 [−0.033, −0.005]; AUC 0.86. Ek satış eklenmesi: −0.033 (fark ≈ 0). Bu bilgi `ceiling_hazard_v0`'ın S_1'inde zaten var (§4). y1 için yeni model önerilmez.

## 6. Tek eşikli kurallar [KEŞİF] (y4)

| kural | H99+açık seçilen / dışarıda | H99 | açık |
|---|---|---|---|
| ek satış kullanıldı | 12/19 (0.63) / 30/151 (0.20) | 4/6 / 25/93 | 8/13 / 5/58 |
| f3 < 2 | 19/42 (0.45) / 21/123 (0.17) | 15/30 / 12/67 | 4/12 / 9/56 |
| f3 < 3 | 25/69 (0.36) / 15/96 (0.16) | 20/44 / 7/53 | 5/25 / 8/43 (**ayırmıyor**) |
| reel büyüklük > 2 mlr (2025 TL) | 28/73 (0.38) / 14/97 (0.14) | 20/45 / 9/54 | 8/28 / 5/43 |
| reel büyüklük > 4 mlr | 8/26 (0.31) / 34/144 (0.24) | 6/15 / 23/84 | 2/11 / 11/60 |
| halka açıklık > 25 | 19/84 (0.23) / 23/86 (0.27) | 10/43 / 19/56 | 9/41 / 4/30 (**ters**) |
| XU100 20 seans negatif | 14/60 (0.23) / 28/110 (0.25) | 9/38 / 20/61 | 5/22 / 8/49 |
| ortak satmama < 365 (açık) | — | varyans yok | 8/26 / 5/45 |

## 7. Çokluk

Denenen varyant sayısı **2 054** (`ekler/denenenler.csv`; tür: tek değişkenli AUC/oran farkı 4 hedef × 3 küme × 23 özellik, kategorik seviye tabloları, 4 karşılaştırıcı × 3 küme, ≤ 4 özellikli 51 küme × 2 λ × 3 hedef × 3 değerlendirme, odak 11 küme × 2 λ × 3 hedef × 3 değerlendirme, 14 eşik kuralı × 3 hedef × 3 küme). Seçim kuralı (önceden değil, keşifte uygulanan): (a) birincil hedef y4; (b) özellik iki dönemde aynı yönde ve tek tanımla 170 arzda mevcut; (c) LOO ve **her iki** aktarım hücresinde negatif ortalama; (d) en çok 3 özellik. Bu süzgeçten yalnız {f1r, ln f3, ek satış} ve alt kümeleri {ln f3 + ek satış}, {f1r + ek satış}, {ek satış} geçti. Şartnamenin adayları bunlardan seçildi; keşifteki aralıklar hüküm değildir.

## 8. Ön koşul görevleri (özet; ayrıntı SPEC_C_V0 §12)

- **P1 (büyük):** H99'un 79 üyesi için Faz 7'nin 7 izahname alanı + Faz 6 aday alanları (yatırımcı sayısı ve grup kırılımı, tahsisat oranları, grup talep katları, lider aracı kurum, satış yöntemi, pazar) — Faz 7 doğrulama kalıbıyla (Codex çıkarır, Claude doğrular; `components` ile). Sonrası: `shareholder_lockup_days`, kişi başı lot / reel TL, dağıtım yöntemi türevleri ancak bu görev bitince (C) v1 adayı olabilir.
- **P2 (küçük):** H99'un 79 üyesi için BIST listeleme bildiriminden satış yöntemi ve pazar.
- v0 adayları (SPEC_C_V0) bu görevleri **gerektirmez**: f1r, f3 ve ek satış 170 arzda ve canlı şemada zaten var.

## 9. Maruziyet (bu belge için)

Yazar açık kümenin sonuçlarını S6'dan beri biliyor; H99 sonuçları yayımlı. Kasa üyesi hiçbir özellik dosyası, girdi, kayıt ya da MANIFEST açılmadı; kasa için yalnız kohort dosyasındaki yıl/rejim/satış sayımları ve iki `coverage.csv`'den alan başına dolu sayıları betikle alındı (`ekler/kasa_sayim_cikti.txt`). Aynı-hafta özelliği için kohortun 135 üyesinin ilk işlem tarihleri (kasa dahil; yalnız tarih) okundu. Oturum başında kohort dosyasının ilk üç satırı başlık incelemesi için ekrana basıldı ve iki SEALED satırın kodu göründü; bu kodlar hiçbir dosyaya yazılmadı ve keşifte kullanılmadı (tam beyan SPEC_C_V0 §10). `EXPOSURE.md` dosyaları, Codex `exposure_log` satırları, `~/Desktop/BorsAi_quarantine` ve `~/Desktop/BorsAi_codex` okunmadı. Canlı sicilin 7 arzı keşfe girmedi.

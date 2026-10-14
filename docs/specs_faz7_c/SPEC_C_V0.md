# SPEC_C_V0 — "düşen arz" modeli v0 ailesi (`fall_d10_v0_h99`, `fall_d10_v0_pooled`, `fall_d10_v0_addsale`)

Görev: BORSAI_FAZ7_FABLE_C_SPEC_20260927. Yazım: 2026-09-27, Fable. Uygulayıcı: Opus (A kod ve kurallar, B backtest); sonra Fable sıfırdan yeniden üretim; dondurma; eski kohort kayıtları; kasa açılışı `ceiling_hazard_v1` ailesiyle **birlikte, tek seferde** (SPEC_HAZARD_V1 §7.1, §7.4; KARARLAR K1). Bu belge `docs/specs_faz7_c/` altındadır; `docs/specs*` (Faz 1–7) değişmemiştir. Kod yok; keşif betiği ve çıktısı `ekler/`, keşif raporu `KESIF.md`.

**Durum: tamamlanmış şartname taslağı; proje sahibinin §14'teki kararlarından sonra bağlayıcı olur ve push edilir. Bu belge push edilmeden kasa açılmaz.**

**Beyan.** Bu şartname yazılırken dondurulacak hiçbir model fit edilmedi, hiçbir walk-forward skoru hesaplanmadı, kasa (SEALED) üyelerinin hiçbir dosyası açılmadı, `docs/faz6/dogrulama/EXPOSURE.md`, `docs/faz7/prospectus/EXPOSURE.md` ve Codex `exposure_log` satırları okunmadı. Keşif (H99 + açık küme, `KESIF.md`) sonuçlar görüldükten sonra yapıldı; oradaki her sayı **keşif** etiketlidir ve hüküm değildir. Maruziyetin tamamı §10'dadır.

İşaretler: **[ÖLÇTÜM]** = bu oturumda dosyadan/komuttan; **[KEŞİF]** = açık küme ve H99 sonuçları görüldükten sonra hesaplanan sayı (hüküm değildir); **[ÇIKARIM]** = yorum; **[KARAR]** = bu şartnamenin bağlayıcı kararı. Görev metnindeki adım 4 maddeleri → bölüm: model kimlikleri §2; hedef/özellikler/eğitim §1, §3; model biçimi §4; testler §5; beklenti §6; başarısızlık §6.4; kasa planı §7; maruziyet §10; uygulama §8; gösterim §9; kabul testleri §11; sözde kod §13; açık sorular §14; ön koşul görevleri §12.

## Özet (10 satır)

1. **Soru:** "D1'de tavan yapmayan ya da arz fiyatının altına düşen azınlığı ayıran bir listeleme öncesi özellik var mı?" (SPEC_OOT_PRE_H99_V0 §9; proje sahibi: "düşen halka arzların ortak özellikleri ne?").
2. **Birincil hedef [KARAR]: y4 = 1[D10 kapanışı ≤ arz fiyatı] = 1 − Y_D10** (SPEC_SCORING §3). Olay sayıları [ÖLÇTÜM]: H99 29/99, açık küme 13/71, kasa **beklenen ≈ 12/64** (yıl ağırlıklı 12.4; H99 oranıyla üst sınır 18.7). İlan edilmiş ikincil hedef: y3 = 1 − Y_D5 (H99 22, açık 11, kasa ≈ 10.5). y1 (D1 tavan yok) ve y2 (D1 ≤ arz) yalnız keşif: y1'i `ceiling_hazard_v0` zaten görüyor; y2 kasada ≈ 2 olay.
3. **Keşif bulgusu [KEŞİF]:** iki dönemde de aynı yönde ve 170 arzda tek tanımla var olan üç özellik: **ek satış kullanıldı** (`additional_sale_shares` > 0; düşme oranı 0.63 vs 0.20), **reel arz büyüklüğü** (f1r, AUC 0.75 / 0.63) ve **talep katı** (ln f3; yalnız H99'da güçlü). Üçü birlikte: arz-bırak Brier farkı −0.036 [−0.057, −0.016]; yalnız H99'da fit → açık kümede −0.023 [−0.066, +0.016]; tersi −0.012 [−0.022, −0.002]. İzahname alanları (fiyat istikrarı, satmama süreleri, dağıtım, sektör) ya H99'da yok (79/99) ya da dönemler arası işaret değiştiriyor.
4. **Üç aday, az parametreli [KARAR]:** `fall_d10_v0_h99` (f1r, ln f3, ek satış; H99 eğitimi, 94 arz), `fall_d10_v0_pooled` (aynı özellikler; H99 + açık küme, 161 arz; rejim terimi **yok**), `fall_d10_v0_addsale` (yalnız ek satış; havuz 165 arz; f3 istemez). Her aday D5 ve D10 için birer L2-lojistik başlık (V1.6 C ızgarası, iç LOOCV). Kural satırı: `fall_d10_v0_pooled@ZERO` (havuz oranı). Yeni canlı girdi alanı gerekmez: üç alan da `registry/inputs` şemasında var.
5. **Bütçe:** `h99` 26 olay / 4 parametre = 6.5 (D10), `pooled` 39/4 = 9.8, `addsale` 40/2 = 20. `h99` SPEC_HAZARD_V1'in ≥ 10 kuralının altındadır; merdiven karşılaştırıcısı olarak tutulur (§2.2, açık soru 2).
6. **Yakın dönem testi (i):** H99 walk-forward (V1.5 planı, kesin önce tarih kuralı), ilk işlem ≥ 2024-01-01 fold'ları (beklenen 75); hücre `pooled − h99` D10 Brier; karar: alt > 0 "bozuyor", üst ≤ **+0.008** "tolerans içinde", diğer "belirsiz".
7. **Kasa testi (ii; tek seferlik, n ≈ 60):** her aday için birincil hücre D10 Brier − `base_rate` (kayıttaki donmuş H99 taban oranı); ilan edilmiş ikincil: − `v1_5_h99`, − `base_last10_rate`, D5 aynı üçlü, `pooled − pooled@ZERO`, merdiven `pooled − h99`, `h99 − addsale`. **Canlı (iii):** SPEC_SCORING kalıbı, birincil D10 Brier − `base_rate`.
8. **Beklenti (kasa; Brier farkı, negatif = model iyi):** `v1_5_h99` − taban +0.010 [−0.030, +0.050]; `h99` − taban −0.020 [−0.060, +0.020]; `pooled` − taban **−0.030 [−0.070, +0.010]**; `addsale` − taban −0.025 [−0.060, +0.010]. En olası sonuç üçü için de "ayırt edilemiyor" (≈ 12 olay). Tam tablo §6.
9. **Kasa planı [KARAR]:** (C) adayları dondurulur → 135 üyelik ikinci kayıtlar (`--only-missing-models`) commit + push → kasa `ceiling_hazard_v1` ile birlikte tek seferde açılır; açık küme satırları formülle **OOT_RETRO**; model başına kapı; `oot_pre_h99_sealed` anahtarı. Uygulama kartı seçim kuralı önceden yazılı (§5.5).
10. **Ön koşul görevleri (v0 için gerekmez):** P1 H99'un 79 üyesi için izahname ve katılımcı alanları (Faz 7 kalıbı); P2 satış yöntemi/pazar. Bunlar bitmeden `shareholder_lockup_days`, kişi başı lot ve dağıtım yöntemi hiçbir (C) modeline giremez (§12).

---

## 1. Hedef, kümeler ve olay sayıları [ÖLÇTÜM]

### 1.1 Aday hedefler ve sayımlar

Tanımlar SPEC_SCORING §3'ten (Y_h = 1[close(D_h) > ipo_price]; tavan etiketi THM üst limitiyle Decimal eşitliği):

| hedef | tanım | H99 (99) | açık (71) | kasa beklenen (64; yıl ağırlıklı / rejim ağırlıklı / H99 oranı) |
|---|---|---|---|---|
| y1 | D1'de tavan yok (L = 0) | 18 | 9 | 8.7 / 8.8 / 11.6 |
| y2 | D1 kapanışı ≤ arz (1 − Y_D1) | 10 | 2 | 1.9 / 1.9 / 6.5 |
| y3 | D5 kapanışı ≤ arz (1 − Y_D5) | 22 | 11 | 10.5 / 10.7 / 14.2 |
| **y4** | **D10 kapanışı ≤ arz (1 − Y_D10)** | **29** | **13** | **12.4 / 12.6 / 18.7** |

Kasa beklentisi: kasanın yıl sayımları (2020: 4, 2021: 26, 2022: 18, 2023: 16; kohort dosyasından yalnız sayım) × açık kümenin yıl oranları. Kasanın sonuç satırı yoktur ve açılmadı. Yıl ve rejim kırılımları `KESIF.md` §1.

### 1.2 Birincil hedef [KARAR]

**y4.** Gerekçe: (i) hüküm eşiği (SPEC_SCORING §8): kasada f3'lü ve ek satış alanı dolu ≈ 60 arz (n ≥ 30 sağlanır) ve en çok olay (≈ 12) y4'te; y2'nin ≈ 2 olayıyla hiçbir hücre hüküm veremez, y1'de ≈ 9, y3'te ≈ 10.5; (ii) ürün değeri: "düşer mi" sorusunun en doğrudan ölçümü; (iii) var olan modeller y4'ü eski dönemde görmüyor: V1.5'in 1 − p_up(D10) açık kümede taban orandan +0.014 kötü, AUC 0.51 [KEŞİF]; y1'i ise `ceiling_hazard_v0` iki dönemde de görüyor (AUC 0.81 / 0.80) ve (C) özellikleri (f1r, f3) onun bilgisiyle aynı. **İkincil hedef:** y3 (aynı modelin D5 başlığı; ikincil hücreler §5). y1 ve y2 için model tanımlanmaz.

Eşitlik durumu: 1 − Y_h tanımı close = ipo_price'ı da olay sayar (H99'da fark yok; açık kümede D10'da 1 arz). Kod tanımıyla (Y_h) ve karşılaştırıcılarla (p_up) uyum için bu tanım seçildi; alternatif açık soru 1.

### 1.3 Eğitim kümeleri [KARAR]

| küme | tanım | n | y4 olay | y3 olay |
|---|---|---|---|---|
| `H99_F3_AS_PRESENT` | `training_table.csv` satırları, f3 dolu VE `additional_sale_shares` dolu | 94 | 26 | 18 |
| `H99_PLUS_OOT_OPEN_F3_AS_PRESENT` | `training_table_v2.csv` (H99 99 + açık 71), f3 dolu VE ek satış dolu | 161 | 39 | 29 |
| `H99_PLUS_OOT_OPEN_AS_PRESENT` | `training_table_v2.csv`, ek satış dolu (f3 istenmez) | 165 | 40 | 30 |

[ÖLÇTÜM: H99'da ek satış alanı boş 4 (hepsi 2026-07; biri f3'süz), açık kümede 1.] H99 mı havuz mu sorusu önceden yazılmış yakın dönem testiyle (§5.1) cevaplanır; iki aday da dondurulur (v1 kalıbı).

## 2. Aday model kimlikleri (3) [KARAR]

Ortak: `algorithm = l2_logit_v1_6_grid` (V1.5/V1.6 Logit yolu: `sklearn LogisticRegression` L2, `borsai.fit._fit_logit`, `V1_6_GRID` C ∈ {ZERO, 0.0001, …, 100}, iç arz-bırak (LOOCV) Brier ile seçim, aday başına yakınsamama politikası), ufuk başlıkları **D5 ve D10** yalnız `p_up` (getiri başlığı yok), ön işleme z-skor (ddof = 0; SPEC_V1_6 kalıbı), ret kuralları §9. Şartnamedeki herhangi bir şey değişirse yeni model_id (CLAUDE.md kural 5).

| model_id | Eğitim kümesi | Özellikler (z-skor) | Kırpma [p05, p95] | Serbest parametre / başlık | D10 olay | Olay/param. |
|---|---|---|---|---|---|---|
| `fall_d10_v0_h99` | `H99_F3_AS_PRESENT` (94) | f1r, ln f3, ek satış | f1r, f3 (ham; log öncesi) | 3 β + 1 sabit = 4 | 26 | 6.5 |
| `fall_d10_v0_pooled` | `H99_PLUS_OOT_OPEN_F3_AS_PRESENT` (161) | f1r, ln f3, ek satış | f1r, f3 | 4 | 39 | 9.8 |
| `fall_d10_v0_addsale` | `H99_PLUS_OOT_OPEN_AS_PRESENT` (165) | ek satış | — | 1 β + 1 sabit = 2 | 40 | 20 |
| `fall_d10_v0_pooled@ZERO` (kural satırı, aday değil) | `H99_PLUS_OOT_OPEN_F3_AS_PRESENT` | yok | — | sabit (kapalı biçim: eğitim oranı) | 39 | — |

`fall_d10_v0_h99@ZERO` = H99 taban oranı; `base_rate`'in D5/D10 p_up'ıyla bit-eşit değildir (94 satır, 99 değil) ama aynı bilgidir; ayrıca kaydedilmez, `base_rate` karşılaştırıcı olur. `fall_d10_v0_addsale@ZERO` = `pooled@ZERO` ile 4 satır farkı taşır; kaydedilmez.

Çıktı: `p_up(D_h) = 1 − P(y_h = 1)`; uygulama ve skorlama V1.5'in p_up başlığıyla aynı yoldan okur (§8, §9). Model "P(kapanış > arz)" verir; "düşme olasılığı" = 1 − p_up olarak gösterilir.

### 2.1 Mekanizma gerekçeleri [ÇIKARIM]

- **Ek satış kullanıldı** (`additional_sale_shares` > 0): ek satış hakkının kullanılması iki şeyi birlikte gösterir: satıcı ortaklar arza ek pay vermiştir (arz sonrası dolaşımdaki pay ve satıcı tarafı büyür) ve ek paylar çoğunlukla kurumsal tahsisata gittiği için ilk günlerde elden çıkarılabilir stok artar. Keşifte iki dönemde de aynı yön (H99 4/6, açık 8/13). Sayı azdır (19 arz); katsayı ağırlıkla açık kümeden öğrenilir.
- **f1r (reel büyüklük):** SPEC_HAZARD_V1 §2.1 (b) mekanizması: büyük arz → satıcı arzı bol; tavan serisi kısa, D10'da arz altı olasılığı yüksek. Deflatör TÜİK TÜFE, ay kuralı m − 2 (KARARLAR K3); v1_real ile **tek tanım**.
- **ln f3 (talep katı):** düşük talep katı → yetersiz fazla talep, ikincil piyasada alıcı yok. H99'da güçlü (AUC 0.24), açık kümede zayıf (0.48; eski dönemde talep katları çok yüksek ve ayırmıyor). Log dönüşümü: ham winsor'lu f3'e göre iki aktarım hücresinde de daha iyi [KEŞİF §5.1]; V1.5'in ham f3 kullanımından farkı yeni tarifle belgelenir.
- **Rejim terimi yok:** keşifte r = 1[tahsis rejimi ≠ EQUAL_DIST] y4'te bilgi eklemedi (LOO −0.035 vs −0.036) ve açık → H99 aktarımını bozdu; y4 taban oranı dönemler arası f1r ve ek satış ile büyük ölçüde açıklanıyor. (v1_pooled'ın dersi, AUDIT §6: rejim/dönem terimi H99'un uzun 2023 serilerini bugünkü rejim sanabilir; burada böyle bir terim yoktur, dönem farkı özelliklerin işi olur ve yakın dönem testi §5.1 bunu ölçer.)

### 2.2 Değerlendirilip elenen seçenekler [KARAR]

| Seçenek | Karar | Gerekçe |
|---|---|---|
| y1 (D1 tavan yok) için model | ret | `ceiling_hazard_v0` 1 − S_1 zaten iki dönemde AUC ≈ 0.8; (C) özellikleri aynı bilgi; ek satış y1'e ≈ 0 ekliyor [KEŞİF §5.3] |
| Kişi başı lot / reel TL (yatırımcı sayısı) | ertelendi (P1 sonrası) | H99'da 20/99; H99-20 ile öğrenilen model açık kümeye aktarılamıyor (+0.013); tanım uyumu var, kapsama yok |
| Ortak satmama süresi, fiyat istikrarı, dağıtım yöntemi, sektör | ret (v0) | H99'da 20/99 ve eski repo kodlaması `components` içermiyor (tanım uyumu doğrulanamaz); açık kümede fiyat istikrarı işaret değiştiriyor; satmama H99'da varyanssız |
| Satış yöntemi (borsada / borsa dışı) | ret (v0) | H99'da 20/99 (P2); ek satışla ilişkili (borsada satışta ek satış 1/27) |
| Halka açıklık f2, sermaye artırımı f4, fiyat, f6, aynı hafta arz sayısı | ret | dönemler arası işaret değiştiriyor ya da ≈ 0 |
| Rejim terimi (pooled) | ret | §2.1 |
| Ek satış payı (%; ikili yerine) | ret | ikiliyle eşdeğer (LOO −0.035 vs −0.036); 19 arzda oran 8–17 arasında, bilgi yok |
| Ham winsor'lu f3 (V1.5 kalıbı) | ret | log daha iyi aktarıyor; V1.5 tarifi değişmez, yeni tarif |
| Dört aday (+ `fall_d10_v0_h99_addsale_only`) | ret | aday bütçesi 3; kasa tek seferlik |

### 2.3 Kimlik ve JSON alanları

Her JSON `borsai.model/1` şemasında V1.5 alanlarını taşır: `algorithm`, `features`, `horizons.{D5,D10}.p_up {kind: logit | constant, columns, coef, intercept}` (getiri başlığı yok), `preprocessing {columns, winsor.{f1r,f3}.{p05,p95}, log_transform: [f1r, f3], mean, std, f3_filter_mode}`, `input_policy {f3_missing: REFUSE | NOT_USED, additional_sale_missing: REFUSE, f3_filter_status_conflict: REFUSE}`, `feature_ranges` (f1r 2025 TL biriminde, f3 ham, add_sale {0, 1}), `deflator` (SPEC_HAZARD_V1 §2.3 bloğu aynen), `training {set, table, cohort_counts {H99, OOT_OPEN}, n, events_D5, events_D10}`, ek alanlar `family: "fall_d10_v0"`, `variant ∈ {h99, pooled, addsale}`, `target_definition: "1 - Y_h (close(D_h) <= ipo_price)"`, `spec_sha256` (bu dosya).

## 3. Özellik ve veri tanımları

### 3.1 Ek satış bayrağı [KARAR]

```
add_sale = 1[Decimal(additional_sale_shares) > 0]          # girdi alanı: registry/inputs V15_FIELDS["additional_sale_shares"]
alan boş / DATA_NOT_FOUND → RET REFUSED_ADDITIONAL_SALE_MISSING   (0 varsayılmaz; açık soru 4)
alan negatif → RET INPUT_NEGATIVE (features kalıbı)
```
Kaynak: H99 ana tablosu `additional_sale_shares` (SPK bülteni A.1 "Ek Pay Satışı" ve sonuç bildirimi; DATA_NOTES kuralı aynen); eski kohort `registry/oot/inputs/<T>.json` aynı ad; canlı `registry/inputs/<T>.json` aynı ad (NETGL: "0"). Üç kümede tek tanım [ÖLÇTÜM §2 tablosu]. z-skorlanır (V1.5'in f5 kalıbı; sabit değilse). Eğitimde ve tahminde bayrak aynı fonksiyondan (`borsai.features.additional_sale_flag`).

### 3.2 f1r ve ln f3

- **f1r** SPEC_HAZARD_V1 §3.2 **aynen**: `size_TL / (TUFE[m−2]/100)`, ham değerde eğitim [p05, p95] kırpması, sonra ln; `borsai.tufe.index_for(T)`; ret kodları `REFUSED_TUFE_*` aynen; kayıtta `tufe` bloğu (v1 dondurmasıyla gelen alan). v1_real'in eğitim satırlarındaki f1r değerleriyle bit-eşit (test).
- **ln f3**: `total_demand_multiple` ham değeri eğitim [p05, p95]'ine kırpılır (Type-7, `preprocess.quantile_type7`), sonra ln; z-skor. Yeni tarif `FALL_V0_RECIPE`: `substantive = ("f1r", "f3", "add_sale")`, `winsor = ("f1r", "f3")`, `log = ("f1r", "f3")`, `indicator = False`, `impute = False`. `addsale` varyantı için `FALL_V0_ADDSALE_RECIPE`: `substantive = ("add_sale",)`, winsor/log boş. V1.5/PB/v0/v1 tarifleri değişmez; altın dosyalar bayt-eşit kalır (test).
- f3 filtre durumu: V1.5 kuralı aynen (`f3_filter_mode` eğitim modu; açık uyuşmazlıkta RET `REFUSED_F3_FILTER_CONFLICT`). Havuzda mod `training_table_v2`'den hesaplanır; test sayıları raporlanır.

### 3.3 Eğitim tabloları

`training_table.csv` (h99) ve `training_table_v2.csv` (pooled, addsale) **değişmez**; satır seçimi §1.3 kurallarıyla kodda (`specs.py` set adı → `select_training_rows`). Havuz satırlarının seans tarihleri v2'dedir (SPEC_HAZARD_V1 §3.4). Kasa üyesi hiçbir satır yoktur (bekçi).

## 4. Model, amaç, çözücü, ızgara

SPEC_V1_6 §3 Logit yolu aynen: her ufuk için bağımsız L2-lojistik, `C ∈ V1_6_C_GRID = (ZERO, 0.0001, 0.001, 0.01, 0.1, 1, 10, 100)`; ZERO = yalnız sabit (eğitim oranı, kapalı biçim); iç arz-bırak LOOCV Brier ile seçim, eşitlikte `rank_C` kuralı; aday başına yakınsamama politikası (`POLICY_CANDIDATE`); azınlık sınıfı < 2 → `fallback_C`; ön işleme her iç bölmede yalnız o bölmenin eğitim satırlarından. Ridge başlığı yoktur (`horizons.D_h.return` alanı yazılmaz; predict `return = None` verir). Tek fark: özellik listesi ve tarif (§3.2). `_fit_logit`, `_InnerCache`, `fit_preprocessing` kodu değişmez; yeni giriş noktası `fit_fall_horizon` (Ridge'siz) ya da `fit_v1_5_horizon`'un R'siz çağrısı — Opus seçer, V1.5/V1.6 altın ledger'ları bayt-eşit kalır (kabul testi 4).

## 5. Önceden yazılmış testler ve birincil hücreler [KARAR]

Her hücre: eşleşik fark (model − karşılaştırılan; negatif = model iyi), Brier (p_up, kırpmasız; skorlama SPEC_SCORING §7 kalıbı), ay-blok bootstrap (blok = ilk işlem ayı; B = 4000; SPEC_SCORING §8 üretici/tohum; SPEC_DEVIATIONS C7 backtest'te), n ve kazanç/kayıp/eşit. Dil SPEC_SCORING §8: "geçiyor" yalnız n ≥ 30 ve aralık 0'ı dışlarsa; zaman-dışı hükmü daima "(zaman-dışı terazide)" ekiyle; üç terazi toplanmaz.

### 5.1 (i) Yakın dönem testi — H99 walk-forward

- Plan `PLAN_FALL_H99` = `PLAN_V15` kuralları (kesin önce tarih: eğitim satırı ancak D10 seansı test arzının T'sinden önce ise; eğitim n ≥ 10) test arzları `H99_F3_AS_PRESENT`'ın 94'ü; `PLAN_FALL_POOLED` aynı test arzları, eğitim = v2'de D_h seansı < T olan H99 + açık satırlar (açık üyelerin son seansı ≤ 2023-10-04 < ilk fold → daima tam girer); `PLAN_FALL_ADDSALE` test arzları `H99 ∩ ek satış dolu` (95), eğitim v2 havuzu.
- **Birincil hücre:** `fall_d10_v0_pooled − fall_d10_v0_h99`, **D10 Brier**, ilk işlem ≥ 2024-01-01 olan fold'lar (beklenen 75 fold, 22 ay bloğu, 21 olay [ÖLÇTÜM v2 tablosundan; fit yapılmadı]).
- **Karar kuralı (önceden):** d = ortalama fark, [alt, üst] = %95 aralık: alt > 0 → **"bozuyor"** (eski veri yakın dönemi bozuyor); üst ≤ **+0.008** → **"tolerans içinde"**; diğer → **"belirsiz"**. δ = 0.008 gerekçesi [ÖLÇTÜM]: V1.5'in yakın dönemde `base_rate`'e karşı D10 Brier kazancı −0.039 (MODELS.md; 81 fold); δ bunun beşte biridir.
- İkincil (ilan edilmiş, aynı fold'lar): her aday − `base_rate` (D10 ve D5), − `v1_5_h99` p_up (aynı fold'larda V1.5 ledger'ı `macos_golden/v1_5_h99_fold_ledger.csv`, sha pinli), `pooled − pooled@ZERO`; 2023 fold'ları keşif. Bu hücreler "yeni model yakın dönemde taban oranı geçiyor mu" bilgisidir; hüküm sözcüğü backtest etiketiyle.
- **H99 tasarıma maruzdur:** özellikler H99 + açık kümenin sonuçlarına bakılarak seçildi (§10); kanıt değeri kasadan ve canlıdan düşüktür.

### 5.2 (ii) Kasa testi — 64 arz, tek seferlik

Skorlama `python -m borsai.scoring --oot` `oot_pre_h99_sealed` anahtarıyla; sınıf `class_oot` formülüyle (SPEC_HAZARD_V1 §7.2); beklenen n: f3 ve ek satış dolu kasa üyeleri ≈ 60 (kasada f3 dolu 62, ek satış dolu 62 [ÖLÇTÜM coverage sayımı]); `addsale` için ≈ 62.

| Aday | **Birincil** | İlan edilmiş ikincil |
|---|---|---|
| `fall_d10_v0_h99` | D10 Brier − `base_rate` (kayıttaki donmuş H99 oranı) | D10 − `v1_5_h99`, − `base_last10_rate`; D5 Brier − `base_rate`, − `v1_5_h99`; − `fall_d10_v0_addsale` (merdiven) |
| `fall_d10_v0_pooled` | aynı | aynı + − `fall_d10_v0_h99` (havuzun payı), − `fall_d10_v0_pooled@ZERO` (özelliklerin payı) |
| `fall_d10_v0_addsale` | aynı | D10 − `v1_5_h99`, − `base_last10_rate`; D5 aynı üçlü |

Yıl, rejim ve satış yöntemi kırılımları (her biri n < 30) "yetersiz örnek" etiketiyle; diğer hücreler keşif. Kalibrasyon satırı: ort. P(y4) ve gözlenen oran (bilgi; hüküm yok). `v1_5_h99 − base_rate` (D10, kasa) bilgi satırı olarak yanında.

### 5.3 (iii) Canlı

SPEC_SCORING §5–§8 aynen. Birincil: D10 Brier − `base_rate` (kayıttaki kural değeri). İkincil: − `v1_5_h99` (f3 isteyen adaylarda aynı ret kümesi), − `base_last10_rate`, D5 aynı. Birincil kayıt kuralı: f3 isteyen `h99` ve `pooled` için f3 isteyen modellerin kuralı (D_1'den önce push kanıtlı en son kayıt); `addsale` için de aynı kayıt (ek satış alanı sonuç bildiriminde gelir; PB kuralı uygulanmaz). Sayaçlar `n_scored / n_refused / n_skipped / n_target_unavailable`, `n_live / n_late`. Hüküm n ≥ 30'da.

### 5.4 Merdiven (ikincil; üç terazide aynı arzlar)

`addsale → h99` (f1r ve f3'ün payı), `h99 → pooled` (eski verinin payı), `pooled@ZERO → pooled` (özelliklerin payı). Yalnız bilgi; hüküm dili yok.

### 5.5 Uygulama kartı seçim kuralı (önceden yazılı) [KARAR]

Kasa skorları yayımlandıktan sonra, tek seferde:
1. Aday **uygun** sayılır ancak: (k1) kasa birincil hücresi "geçiyor (zaman-dışı terazide)" (aralık tamamen 0'ın altında) VE (k2) kasada D10 Brier − `v1_5_h99` aralığının üst ucu < 0 VE (k3) `pooled` için yakın dönem hücresi "bozuyor" değil; `h99` ve `addsale` için yakın dönem − `base_rate` hücresi tamamen 0'ın üstünde değil.
2. Uygun adaylar arasında kasa D10 Brier noktası en düşük olan uygulamanın "düşüş" kartında **öne çıkarılır**; |Δ| < 0.002 eşitliğinde en basit (`addsale` < `h99` < `pooled`).
3. Uygun aday yoksa kart hiçbir (C) modelini öne çıkarmaz; "kasada geçen aday yok" yazar; V1.5'in p_up sütunu olduğu gibi kalır.
4. KARARLAR K4 aynen: hiçbir model listeden kalkmaz, terfi yok; üç aday sonuç ne olursa olsun dondurulmuş kalır ve canlıda skorlanır.

## 6. ÖNCEDEN YAZILMIŞ BEKLENTİ

Bu bölüm 2026-09-27'de, dondurulacak modeller için hiçbir kod ve skor yokken yazıldı; sonradan değiştirilmez. **Beyan:** yazar keşif kümesini (H99 + açık küme, 170 arzın sonuçları) gördü, kasayı görmedi. Kasa üyeleri açık kümeyle aynı yıl tabakalı çekilişten geldiği için açık kümedeki sayılar kasa beklentisinin temelidir; kasa açık kümeden biraz daha "eski" (PRE 29/64'e karşı 25/71) ve borsada satış payı benzer (22/64'e karşı 27/71). Keşifteki en yakın benzer hücre "yalnız H99'da fit → açık kümede skor"dur (§KESIF 5.1); aralıklar buna göre ve geniş yazıldı. Birim: Brier farkı (kesir); negatif = model iyi.

### 6.1 Kasa (n ≈ 60; hüküm dili yalnız aralıkla)

| Hücre | Beklenen fark | Aralık | Aralık 0'ı | Gerekçe (kısa) |
|---|---|---|---|---|
| `v1_5_h99` − `base_rate` D10 (bilgi) | +0.010 | [−0.030, +0.050] | içerir | açık kümede +0.014; V1.5'in f1 nominal ve f3 bilgisi eski döneme aktarılmıyor |
| `fall_d10_v0_h99` − `base_rate` **(birincil)** | −0.020 | [−0.060, +0.020] | içerir | H99→açık aktarımı −0.023 [−0.066, +0.016]; kasa açık kümeye benzer |
| `fall_d10_v0_h99` − `v1_5_h99` | −0.030 | [−0.080, +0.010] | büyük olasılıkla içerir | |
| `fall_d10_v0_pooled` − `base_rate` **(birincil)** | **−0.030** | **[−0.070, +0.010]** | **büyük olasılıkla içerir** | havuz sabiti eski dönemin düşük oranını taşır (kalibrasyon payı) + özellikler |
| `fall_d10_v0_pooled` − `pooled@ZERO` | −0.020 | [−0.060, +0.020] | içerir | özelliklerin payı; LOO havuzda −0.036 ama kasa 12 olay |
| `fall_d10_v0_pooled` − `fall_d10_v0_h99` | −0.010 | [−0.035, +0.015] | içerir | eski verinin payı; aktarım hücreleri arası fark |
| `fall_d10_v0_addsale` − `base_rate` **(birincil)** | −0.025 | [−0.060, +0.010] | içerir; negatif dışlaması olası | ek satış tek: H99→açık −0.024 [−0.049, −0.002]; kasada ≈ 12 ek satışlı üye (açık oranla) |
| `fall_d10_v0_addsale` − `v1_5_h99` | −0.035 | [−0.085, +0.010] | içerir | |
| D5 (ikincil), her aday − `base_rate` | −0.015 | [−0.050, +0.020] | içerir | y3 etkileri y4'ün biraz altında |
| Kalibrasyon (bilgi) | `pooled` ort. P(y4) − gözlenen | [−0.08, +0.08] | — | |

Hangi hücrede kazanç en olası: `addsale − base_rate` ve `pooled − base_rate` (eşleşik; kalibrasyon + ek satış). En az olası: herhangi bir adayın "geçiyor" demesi (≈ 12 olay; aralık genişliği ≈ 0.08).

### 6.2 Yakın dönem (75 fold; D10 Brier)

| Hücre | Beklenen | Aralık | Beklenen etiket | Gerekçe |
|---|---|---|---|---|
| `pooled − h99` **(birincil)** | −0.002 | [−0.015, +0.012] | **"belirsiz"** ya da "tolerans içinde" | açık → H99 aktarımı −0.012 [−0.022, −0.002] havuzun H99'a zarar vermediğini söylüyor; ama fold'larda eğitim n küçükken 67 eski satır ağır basar |
| `h99 − base_rate` (ikincil) | −0.025 | [−0.055, +0.005] | — | ln f3 H99'da güçlü |
| `pooled − base_rate` (ikincil) | −0.025 | [−0.055, +0.005] | — | |
| `addsale − base_rate` (ikincil) | −0.005 | [−0.020, +0.010] | — | H99'da ek satış 6 arz |
| her aday − `v1_5_h99` (ikincil) | +0.010 | [−0.020, +0.040] | — | V1.5 H99 içinde f1, f2, f4 ile daha çok bilgi kullanır; (C) yakın dönemde V1.5'i geçmesi beklenmez |

### 6.3 Canlı (ilk n ≥ 30; ≈ 10–12 ay)

Her aday − `base_rate`: −0.020 [−0.060, +0.020] (ayırt edilemiyor); − `v1_5_h99`: −0.010 [−0.050, +0.030]. Canlı dönem H99 dönemidir; asıl ayrım kasadadır ve o da düşük çözünürlüklüdür.

### 6.4 Başarısızlık tanımları (aynı sözcüklerle)

- (a) **"taban orandan kötü":** kasada birincil hücre aralığı tamamen 0'ın üstünde → aday listede kalır, kartı bunu yazar, kartta öne çıkarılamaz.
- (b) **"bozuyor":** yakın dönem `pooled − h99` alt > 0 → proje sahibine cevap "eski arzları eğitime katmak bugünkü tahmini bozuyor"; `pooled` k3 ile öne çıkarılamaz.
- (c) **"ek satış bilgi eklemiyor":** kasada `addsale − base_rate` noktası ≥ 0 → kart bunu yazar. **"özellikler bilgi eklemiyor":** kasada `pooled − pooled@ZERO` noktası ≥ 0.
- (d) **Kalibrasyon:** kasada |ort. P(y4) − gözlenen oran| > 0.15 → "düzey kayması" notu.
- (e) **Beklentiden çok iyi:** kasa birincilinde fark < −0.08 ya da aralığın üst ucu < −0.04 → kasa skorunun bağımsız yeniden hesabı (S6 denetimi kalıbı) kart değişmeden önce zorunludur.
- Ara durum: "ayırt edilemiyor" (beklenen). **Her durumda üç aday bu şartnameyle dondurulur**; sonuca bakıp özellik/eşik/tanım değiştirmek = yeni model_id + günlük satırı.

## 7. Kasa planı [KARAR]

### 7.1 Sıra (SPEC_HAZARD_V1 §7.1 adım 3–6 ile tutarlı)

1. Bu şartname (+ §14 kararları) commit + push (proje sahibi) + push kanıtı.
2. Opus A (kod, tarifler, kurallar, testler) → B (backtest, yakın dönem hücreleri, günlük; keşif varyantları günlüğe `kind: exploration`) → Fable sıfırdan yeniden üretim (|Δ| ≤ 1e-9) → dondurma (INDEX'e 4 giriş: 3 aday + `pooled@ZERO`) → push + kanıt.
3. **Eski kohort kayıtları (135 üye):** `python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv --only-missing-models` — üye başına yalnız eksik modelleri içeren ek kayıt (v1'in ikinci kaydıyla aynı komut; v1 ve (C) aynı koşuda ya da ayrı kayıtlarda olabilir, `delta_of` zinciri). Girdiler ilk kayıtla bayt-eşit (test); `tufe` bloğu; **kasa üyeleri için yalnız listeleme öncesi girdiler okunur** (`registry/oot/inputs/<T>.json`; ek satış bu dosyadadır), sonuç yok, aday özellik dosyası gerekmez. Tek commit; push; kanıt. Bu commit kasa sonuçlarından önce gelir ve kanıtı önce olmalıdır.
4. v1 kayıtları (SPEC_HAZARD_V1 §7.1-3) push kanıtlı; **model başına kapı** (§7.3 orada): INDEX'teki her model × her MEMBER için o modeli içeren aktif kayıt ingest'in atası ve kanıtı önce; değilse indirme başlamaz.
5. **Kasa açılışı, tek seferde:** karantina zip'leri pinli sha ile; SEALED satırlar ayıklanır; tek commit; push; kanıt. `scoring --oot`: `oot_pre_h99_sealed` (19 eski + 4 v1 + 4 (C) satırı), `oot_pre_h99_all` yalnız 19 eski model.
6. Seçim kuralları (v1 §5.5; (C) §5.5) uygulanır; MODELS.md ve uygulama güncellenir.

### 7.2 Açık küme satırları OOT_RETRO

`class_oot` formülüyle: (C) modellerinin `commit_frozen` değeri S5 ingest commit'i `77b54f7`'den sonradır → `frozen_ok = False` → 71 açık satır **OOT_RETRO** (`n_oot_retro = 71`; yalnız bilgi). Açık küme (C) için tasarım (h99) ya da eğitim (pooled, addsale) kümesidir, test değildir. Kasa üyeleri için ingest adım 5'tir → OOT_BLIND.

### 7.3 Açılış ön koşulları

(i) v1 kayıtları push kanıtlı; (ii) bu şartname push kanıtlı ve (C) kayıtları (adım 3) push kanıtlı; (iii) `oot_pre_h99_sealed` kodu sentetik testte yeşil; (iv) model başına kapı yeşil. Kasa açıldıktan sonra (C) için ikinci temiz küme ancak canlı sicilden kurulabilir; SEALED küme D4 gereği ancak doğrulaması yayımlanınca ve yalnız yeni kimliklerin eğitimine girebilir.

## 8. Uygulama (Opus için)

| Parça | İş |
|---|---|
| `borsai/features.py` | `additional_sale_flag(value) -> int` (Decimal; boş → `FeatureError(ADDITIONAL_SALE_MISSING)`, negatif → `INPUT_NEGATIVE`); `f1–f4` fonksiyonları değişmez |
| `borsai/preprocess.py` | `FALL_V0_RECIPE`, `FALL_V0_ADDSALE_RECIPE` (§3.2); winsor/log listeleri `substantive` içindeki f1r ve f3'e uygulanır; eski tarifler bayt-eşit davranış |
| `borsai/specs.py` | `FALL_D10_V0_H99`, `FALL_D10_V0_POOLED`, `FALL_D10_V0_ADDSALE`, `FALL_D10_V0_POOLED_ZERO` (kural); `FAZ7C_MODEL_IDS`; eğitim kümeleri §1.3; planlar `PLAN_FALL_H99`, `PLAN_FALL_POOLED`, `PLAN_FALL_ADDSALE`; `SPEC_DOCUMENTS_FAZ7C` (bu dosya + `KARARLAR_C.md` varsa) |
| `borsai/fit.py` | Ridge'siz Logit fit yolu (`fit_fall_horizon` ya da `fit_v1_5_horizon` R'siz); `V1_6_GRID`; `_fit_logit` değişmez |
| `borsai/data.py` | `select_training_rows` yeni set adları (f3 ∧ ek satış dolu; ek satış dolu); v2 yükleyici aynen |
| `borsai/backtest.py` | üç plan; yakın dönem hücresi `pooled − h99` (eşleşik, aynı fold'lar; δ = 0.008 sabiti `NEAR_ERA_TOLERANCE_FALL`); `base_rate` ve `v1_5_h99` ledger'larından eşleşik ikincil hücreler (sha pinli); günlük satırı (`kind: backtest`, `spec_sha256`); **keşif varyantlarının içe aktarımı:** `docs/specs_faz7_c/ekler/denenenler.csv` satırları günlüğe `kind: exploration` (2 054 satır, özet satır değil; alanlar id, target, features, method, param, subset, n, metric, value; `source: docs/specs_faz7_c/ekler/denenenler.csv`, dosya sha) — kart `n_variants` sayacı bu türü sayar (CLAUDE.md kural 4; `test_experiment_log.py` türü kabul etmeli) |
| `borsai/predict.py` (ya da `predict_fall.py`, stdlib) | girdi: V1.5 alanları + `tufe_index` (v1 yolu) + `additional_sale_shares`; §9 retleri; çıktı V1.5 şekli `{model_id, D5, D10: {p_up, direction, return: None, …}, warnings, refused}`; `@ZERO` sabit başlık |
| `borsai/freeze.py` | `--models` 4 kimlik; `build_record`: `model_inputs["additional_sale_shares"]` zaten var, `tufe` bloğu v1'den; `--oot --only-missing-models` aynen |
| `borsai/scoring.py` | `PRIMARY_CELLS` / `OOT_PRIMARY_CELLS`: üç aday için `{output: "p_up", horizon_or_k: "D10", metric: "Brier", rule_ids: ["base_rate"]}`; ikincil listeler §5.2; yakın dönem etiketleri; `SCORES.md` backtest panelinde "(C) yakın dönem" satırı; canlı/oot p_up hücreleri V1.5 yoluyla |
| `models/INDEX.json` | 4 giriş sonuna (`FAZ7C_MODEL_IDS` sırası); önceki girişler metin olarak aynı |
| `app/` | bu görevde değişmez; `build_embed` yeni kayıtları `ignored_model_ids`'e alır (Faz 7 EK3 kalıbı); (C) kartı EK4 görevi (§9) |
| `docs/MODELS.md` | `report_faz7c.py` (Faz 7 kalıbı): kartlar, yakın dönem hücreleri ve §6.2 konumu, "kasa: bekliyor" |
| `docs/SPEC_DEVIATIONS.md` | bölüm K: yorum kararları |

**Canlı girdi şeması:** genişleme **gerekmez**; `additional_sale_shares`, `total_demand_multiple`, `ipo_size_tl`/fiyat/pay `V15_FIELDS`'ta; TÜFE bloğu v1 dondurmasıyla kayda giriyor. PIT kuralı: ek satış alanının kaynağı sonuç bildirimi (`source_published_at < D_1`, `inputs_pit_ok` aynen). Gelecek (C) v1 için şema önerisi §12.

## 9. Uygulamadaki gösterim (kısa; EK4 görevi)

- Yer: sicil ve senaryo ekranlarında V1.5 p_up sütununun yanında **"Düşüş (D10)"** kartı. Metin: "P(D10 kapanışı ≤ arz fiyatı) = %k" (= 1 − p_up, 0 ondalık), altında "P(kapanış > arz) = %(100 − k)". Yalnız izinli sözcükler (SPEC_APP §4: "tahmin", "olasılık", "basit kural", "fark", "%95 aralık", "ayırt edilemiyor"); yasak liste aynen ("sinyal", "al/sat" yok).
- Kart satırları: model_id, "ne yapar" (INDEX açıklaması: "ek satış, reel büyüklük ve talep katından D10'da arz altı kapanış olasılığı"), eğitim n ve kesim, sha ilk 8, varyant sayısı (günlükteki `exploration` + `backtest` satırları, aynı veri sürümü), birincil hücre "D10 Brier − taban oran".
- Üç terazi etiketi, ayrı renk, toplanmaz: "Geçmiş veri testi (retrospektif, tasarıma maruz)"; "Zaman-dışı test (kasa; tek seferlik; H99 öncesi kohort)"; "Canlı sicil (prospektif, n = k; atlanan = s)". Kasa açılmadan: "kasa: bekliyor". §5.5 sonucu: öne çıkarılan aday ya da "kasada geçen aday yok".
- Ret hücresi: "ek satış alanı boş → bu model tahmin vermez" / "talep katı yok → …" (V1.5 ret kalıbı).

## 10. Maruziyet beyanı

1. **Keşif kümesi:** yazar H99'un 99 ve açık kümenin 71 arzının sonuçlarını gördü ve `KESIF.md`'deki bütün sayıları onlar üzerinde hesapladı (2 054 varyant). Açık kümenin skorlarını S6 denetiminden (`docs/fable_faz6_s6/AUDIT.md`) beri biliyor. Bu yüzden açık küme (C) için **test değildir**; H99 tasarıma maruzdur.
2. **Kasa:** hiçbir kasa üyesinin özellik dosyası, girdisi, kaydı ya da MANIFEST'i açılmadı. Kasa hakkında kullanılanlar: kohort dosyasından yıl / tahsis rejimi / satış yöntemi / pazar sayımları; `docs/faz7/prospectus/coverage.csv` ve `docs/faz6/dogrulama/coverage.csv`'den alan başına dolu değer sayıları (betikle; `ekler/kasa_sayim_cikti.txt`; değer ya da kod basılmadı). Aynı-hafta özelliği için kohortun 135 üyesinin ilk işlem tarihleri okundu (kasa dahil; yalnız tarih, kod basılmadı; özellik elendi).
3. **İstenmeyen görüntü:** oturum başında `registry/oot/cohort_pre_h99.csv`'nin ilk üç satırı başlık incelemesi amacıyla ekrana basıldı; iki satır SEALED üyeye aitti ve kodları göründü. Bu kodlar hiçbir dosyaya yazılmadı, hiçbir keşif hesabında kullanılmadı ve bu belgede yer almaz; sonraki bütün okumalar `vault != SEALED` süzgeciyle yapıldı. Bu, kasa sonucu maruziyeti değildir (kod dışında hiçbir bilgi görülmedi) ama kural gereği beyan edilir.
4. **Okunmayanlar:** `docs/faz6/dogrulama/EXPOSURE.md`, `docs/faz7/prospectus/EXPOSURE.md`, Codex `exposure_log` satırları, `~/Desktop/BorsAi_quarantine`, `~/Desktop/BorsAi_codex`. Canlı sicilin 7 arzı keşfe girmedi. Ağ yok.
5. **Genel ön bilgi:** SPEC_OOT_PRE_H99_V0 §8 ve SPEC_HAZARD_V1 §10-4 beyanı aynen.
6. **Bekçi:** `ekler/kesif_c.py` açık küme dışındaki bir eski kohort üyesinin dosyası istendiğinde durur (`_assert_open`); yeni dosyalarda kasa kodu ve bülten adı kalıbı yoktur (betikle denetlendi).

## 11. Kabul testleri (Opus için, kanıtlanabilir)

1. **Ek satış bayrağı:** "0" → 0; "35000000" → 1; "" / None → `REFUSED_ADDITIONAL_SALE_MISSING`; "-1" → `INPUT_NEGATIVE`. H99'da bayrak = 1 olan 6, açık kümede 13 arz [ÖLÇTÜM].
2. **Eğitim kümeleri:** `H99_F3_AS_PRESENT` 94 satır (y4 26, y3 18); `H99_PLUS_OOT_OPEN_F3_AS_PRESENT` 161 (39, 29); `H99_PLUS_OOT_OPEN_AS_PRESENT` 165 (40, 30); kasa kodu yok (bekçi); `training_table.csv`, `training_table_v2.csv` sha değişmez.
3. **f1r:** eğitim satırlarında `ceiling_hazard_v1_real`'in f1r ham değerleriyle bit-eşit (aynı `tufe.index_for`); winsor sınırları Type-7; log winsor'dan sonra; f3 için de aynı sıra.
4. **Bayt-eşitlik:** V1.5/V1.6/PB/market20/v0/v1 altın ledger'ları ve 16 eski altın dosya bayt-eşit; `gen_golden --check` yeşil; Rust golden paritesi mevcut model sayısıyla.
5. **Fit yolu:** `_fit_logit` çağrısı V1.6 ızgarası ve aday başına politika; her başlıkta seçilen C ve iç LOOCV tablosu ledger'da; `@ZERO` = eğitim oranı (Fraction ile 1 − 39/161 D10, 1 − 29/161 D5 bit-eşit).
6. **Fold planları:** `PLAN_FALL_H99` test kümesi 94 arz; `PLAN_FALL_POOLED` aynı test kümesi; yakın dönem alt kümesi ikisinde de aynı ticker'lar (beklenen 75, 22 ay bloğu); sızıntı: her fold'da eğitim D10 seansı < T (açık üyeler dahil); `PLAN_FALL_ADDSALE` 95 test arzı.
7. **Karşılaştırıcılar:** `base_rate` ve `v1_5_h99` ledger sha'ları pinli; V1.5'in yayımlı D10 Brier'i (0.1883, 81 fold) ledger'dan yeniden üretilir (|Δ| ≤ 1e-9).
8. **Karar etiketi:** sentetik aralıklar: [+0.001, +0.02] → "bozuyor"; [−0.02, +0.007] → "tolerans içinde"; [−0.005, +0.02] → "belirsiz"; [+0.000, +0.02] → "belirsiz"; eşik sabiti 0.008 (mutasyon 0.015 kırmızı).
9. **JSON ↔ stdlib predict:** üç adayın eğitim arzlarında |Δ| ≤ 1e-12; `@ZERO` sabit; ret yolları (f3 boş, ek satış boş, TÜFE eksik/PIT değil, filtre uyuşmazlığı).
10. **Eski kohort ek kayıt:** 135 üyede (C) 4 kimliğini içeren kayıt; girdiler ilk kayıtla bayt-eşit; model başına kapı: bir üyenin kaydı eksikken indirme kapısı kırmızı; açık küme sınıfı OOT_RETRO (`n_oot_retro = 71`), kasa senaryosunda OOT_BLIND (geçici git deposu).
11. **Günlük:** backtest satırlarında `spec_sha256` = bu dosyanın sha256'sı; `exploration` satırları 2 054 ve `denenenler.csv` sha'sı; kart `n_variants` bu satırları sayar.
12. **Bekçiler:** yeni dosyalarda kasa kodu ve bülten adı kalıbı yok; `registry/` sonuç alanı taşımaz; `ekler/kesif_c.py` `_assert_open` sentetik kapalı kodda durur.
13. **Gösterim metni:** SCORES.md/MODELS.md'de "geçiyor" yalnız n ≥ 30 ve aralık 0'ı dışlarsa; zaman-dışı satırda "(zaman-dışı terazide)" eki.

## 12. Ön koşul görevleri (v0 için gerekmez; (C) v1 için zorunlu)

- **P1 — H99'un 79 üyesi için izahname ve katılımcı alanları.** Kapsam: Faz 7'nin 7 alanı (`distribution_method`, `price_stability_planned/days`, `issuer_lockup_days`, `shareholder_lockup_days` **`components` ile**, `sector`, `participation_index_eligible`) + Faz 6 aday alanları (`investor_count` ve grup kırılımı, `distributed_by_group`, tahsisat oranları, grup talep katları, `lead_broker`). Kaynak: KAP izahname/TSSD ve sonuç bildirimleri (T'den önce yayımlanmış; sha pinli). Kalıp: `docs/prompts/FAZ7_CODEX_PROSPECTUS_B*.md` + `FAZ7_VERIFY_PROSPECTUS.md` (Codex çıkarır, Claude doğrular). Maliyet [ÇIKARIM, Faz 7 raporundan ölçekle]: 79/135 × (~10 saat doğrulayıcı + Codex partileri) ≈ 6–8 saat; ~750 PDF. Kim: Codex + Claude Code (Opus). Çıktı: `registry/h99/candidate_features_faz7/<T>.json` ve MANIFEST; H99'un mevcut 20 satırı da aynı kuralla yeniden türetilir (365'lerin `components` düzeyinde doğrulanması). **Bu görev bitmeden** `shareholder_lockup_days`, kişi başı lot / reel TL, dağıtım yöntemi türevleri hiçbir (C) modeline giremez.
- **P2 — satış yöntemi ve pazar (H99 79 üye).** BIST "Payların İşlem Görmeye Başlaması" bildirimi "Halka Arz Yöntemi" ve pazar alanı; FEASIBILITY §1.1 sorgu kalıbı; ≈ 1–2 saat; çıktı H99 tablosuna ek sütun değil, ayrı dosya (`registry/h99/listing_fields.csv`); `training_table.csv` dokunulmaz.
- **Canlı girdi şeması genişlemesi (P1 ile birlikte, `borsai.inputs/2`):** alanlar `sale_method` (ON_EXCHANGE | OFF_EXCHANGE_BOOKBUILD; BIST bildirimi), `market`, `investor_count` (+ `semantic`), `retail_allocation_pct`, `retail_demand_multiple`, 7 izahname alanı (`components` dahil); her alan `source_id/published_at/sha256`; PIT kuralı `published_at < D_1`; izahname alanları için ayrıca `published_at ≤ bookbuilding_start`. Eski şema dosyaları geçerli kalır (alan yoksa `missing_reason`).
- Kasa tek seferlik olduğundan P1 sonrası yazılacak (C) v1 adayları kasada test edilemez; yalnız canlı teraziyle ölçülür. Bu maliyet açıkça kabul edilmelidir (açık soru 5).

## 13. Sözde kod

```
# --- özellikler (fit ve tahmin aynı yol) ---
raw = compute_features(...)                         # f1 (TL), f2, f3, f4 (değişmez)
f1r_raw = raw.f1_raw_TL / (tufe.index_for(T).index / 100)      # v1_real ile aynı
add_sale = additional_sale_flag(inputs["additional_sale_shares"])   # boş → RET
# --- ön işleme (eğitimden öğrenilir; iç bölmede yalnız bölmenin eğitim satırları) ---
for col in ("f1r", "f3"): bounds[col] = type7_p05_p95(train_raw[col])
z[f1r] = zscore(ln(clip(f1r_raw))); z[f3] = zscore(ln(clip(f3))); z[add_sale] = zscore(add_sale)
# --- fit (ufuk başına, D5 ve D10) ---
for h in (D5, D10): logit[h] = _fit_logit(order, Y_h = 1 − Y_h_table, inner, final, test, grid = V1_6_GRID)
#   C = ZERO → p = eğitim oranı (Fraction); kural satırı pooled@ZERO
# --- tahmin (stdlib) ---
p_up(D_h) = sigmoid(intercept + coef · z)          # P(kapanış > arz); düşme olasılığı = 1 − p_up
# --- yakın dönem hücresi ---
folds = [f for f in ledger_pooled if f.T >= "2024-01-01" and f.status == FIT_OK]          # 75 bekleniyor
d = [brier(p_pooled[f], Y[f]) − brier(p_h99[f], Y[f]) for f in folds]
lo, hi = block_bootstrap(d, blocks = month(T))
label = "bozuyor" if lo > 0 else "tolerans içinde" if hi <= 0.008 else "belirsiz"
# --- kasa sonrası kart seçimi (§5.5) ---
ok = [c for c in (addsale, h99, pooled) if vault(c).vs_base.hi < 0 and vault(c).vs_v15.hi < 0 and near_ok(c)]
featured = min(ok, key = lambda c: (round(vault(c).brier_point, 3), ORDER[c])) if ok else None
```

## 14. Açık sorular (proje sahibine; her birine öneri; orkestratör cevaplar)

1. **Hedef eşitlik durumu.** y4 = 1 − Y_D10 (kapanış ≤ arz) mi, kesin altı (R_D10 < 0) mı? Öneri: **1 − Y_D10** (kod tanımı hazır, `base_rate`/V1.5 p_up ile birebir karşılaştırılabilir; fark açık kümede 1 arz). Kesin altı seçilirse yeni hedef alanı ve karşılaştırıcı türevi gerekir.
2. **`fall_d10_v0_h99`'un bütçesi** (6.5 olay/parametre < 10). Öneri: **kabul** (yakın dönem testinin karşılaştırıcısı ve merdivenin H99 basamağı olarak gerekli; kart adayı olması zorunlu değil). Alternatif: h99 düşürülür, aday bütçesi 2 olur ve yakın dönem hücresi `pooled − base_rate`'e döner.
3. **İkincil hedef** D5 (y3) mi, D1 tavan yok (y1) mı? Öneri: **D5** (aynı model ailesinin başlığı; ek çıktı türü gerekmez; y1'i tavan ailesi zaten kapsıyor).
4. **Ek satış alanı boş** → RET mi, 0 kabul mü? Öneri: **RET** (`REFUSED_ADDITIONAL_SALE_MISSING`; H99'da 4, açık kümede 1, kasada 2 üye kaybı; "yok" ile "bulunamadı" karıştırılmaz).
5. **Ön koşul P1'in zamanlaması ve kasa maliyeti.** Öneri: P1 **şimdi** başlatılır, kasa açılışını beklemez; P1 sonrası (C) v1 adayları kasada test edilemeyecek, yalnız canlı teraziyle ölçülecek — bu yazılı olarak kabul edilir. Alternatif (önerilmez): kasa açılışını P1 ve (C) v1 şartnamesine kadar ertelemek (v1 hazard ailesinin kasa hükmü de aylarca bekler).

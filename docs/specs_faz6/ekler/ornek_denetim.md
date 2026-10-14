# Örnek denetim: 8 arz, yalnız listeleme öncesi resmi belgeler (K2)

Seçim kuralı (sonuca bakmadan, deterministik): her yıl için kohort penceresindeki EN ERKEN ve EN GEÇ ilk işlem tarihli üye (eşitlikte alfabetik kod). 2020: ARDYZ, ARZUM; 2021: ISKPL, PSGYO; 2022: PNLSN, AHGAZ; 2023: ONCSM, REEDR. Yöntem karışımı rastlantısaldır ama 3 borsada satış / 5 borsa dışı ve 1 fiyat aralıklı arz içerir.

Yöntem: KAP `byCriteria` (memberType IGS, 3 günlük parçalar) ile talep toplamanın 21 gün öncesinden ilk işlem gününün 1 gün öncesine kadar bütün bildirimler listelendi, `relatedStocks` alanı örnek kodla eşleşenler tutuldu (`ornek_denetim_kap_bildirimleri.json`, sorgu günlüğü `ornek_denetim_kap_sorgu_gunlugu.json`). Yalnız izahname/TSSD/fiyat tespit/sonuç/BIST bildirimleri açıldı; hiçbir fiyat-hareketi bildirimi açılmadı. Sonuç bildirimleri talep toplama sonrası, listeleme öncesidir (KAP yayın zamanı < ilk işlem günü). PDF sha256 değerleri KAP `BildirimPdf` baytlarına, ek sha256 değerleri Java sarmalı çözülmüş PDF baytlarına aittir; erişim zamanları `kaynaklar.json`.

Zaman damgası kaynağı: KAP liste API `publishDate` (Europe/Istanbul). 2022 sonrası PDF başlıklarında "KAP'ta yayınlanma tarihi ve saati" da var ve liste ile ±4 sn uyumlu (AHGAZ, ONCSM, REEDR); 2020–2021 PDF başlıklarında bu alan farklı biçimde/yok → liste API zamanı kullanılır (yine KAP sunucu zamanı).


## ARDYZ (2020; Borsada (birincil piyasa, sabit fiyatla talep toplama); Ana Pazar; talep toplama 29-30/01/2020; ilk işlem 2020-02-06)

| Alan / belge | Kaynak ve yayın zamanı (Istanbul) | Değer / not | sha256 (ilk 16) |
|---|---|---|---|
| SPK haftalık bülteni A.1 İlk Halka Arzlar (PB planlanan yapı) | 2020/6, 16/01/2020 — https://spk.gov.tr/data/61e0b4f31b41c613a0d633e0/2020-6.pdf | Ard Grup … 18.000.000 | 22.000.000 | 4.000.000 (bedelli) | – | 3.500.000 (mevcut pay satışı) | – | 5,30 | `38bc1ac63e2d04aa…` |
| İzahname (SPK onaylı, KAP) | KAP 814433…814440, 24.01.2020 19:52–19:53 | çok parçalı; indirilmedi (zaman damgası liste API) | — |
| Tasarruf Sahiplerine Satış Duyurusu | KAP 814441, 24.01.2020 19:54:04 | planlanan yapı; talep toplama öncesi | `a0c362afb4778250…` |
| Fiyat tespit raporu | KAP 814442, 24.01.2020 19:54:16 | — | — |
| BIST birincil piyasa duyurusu | KAP 814665 Payların Borsa Birincil Piyasada Halka Arzı, 27.01.2020 20:27:22 | borsada satış: birincil piyasa günleri = talep toplama günleri | — |
| Talep toplama sonuç bildirimi | KAP 816932 ÖDA (Genel) "Halka Arz sonuçları", 04.02.2020 11:25:10 | 7.500.000 TL nominal tamamı 5,30 TL; grup bazında dağıtılan nominal ve talebi karşılanan başvuru sayısı (toplam 18.055 yatırımcı); TALEP KATI YAZILMIYOR | bildirim `a2a75260fcbad6bb…` |
| BIST Payların İşlem Görmeye Başlaması | KAP 817020, 04.02.2020 18:07:35 | first_trading_date, baz fiyat, pazar, nominal, sermaye | `0c1a302ef2b0e632…` |
| `ipo_price_tl` | | 5,30 (SPK-B, TSSD, sonuç) | |
| `shares_offered` | | 7.500.000 (sonuç ÖDA); ek satış yok | |
| `post_ipo_share_capital` | | 22.000.000 (SPK-B Yeni Sermaye; KAP 817020 metni "sermayesini temsil eden") | |
| `capital_increase_shares` / `existing_share_sale_shares` | | 4.000.000 / 3.500.000 (SPK-B; sonuç ÖDA tamamı satıldı → taşıma kuralı DATA_NOTES §2) | |
| `total_demand_multiple` (f3) | | YOK birincil belgede (SPK yıllık tablosu 17 kat yazar: ikincil, listeleme sonrası derleme) → REFUSED_F3_MISSING adayı; iş planı: BIST birincil piyasa sonuç duyurusu aranacak | |
| PB alanları | | 8 alan SPK-B 2020/6 tablosundan; tek fiyat → PB uygulanabilir | |

## ARZUM (2020; Borsa dışı, fiyat aralığıyla talep toplama; Yıldız Pazar; talep toplama 17-18/12/2020; ilk işlem 2020-12-24)

| Alan / belge | Kaynak ve yayın zamanı (Istanbul) | Değer / not | sha256 (ilk 16) |
|---|---|---|---|
| SPK haftalık bülteni A.1 İlk Halka Arzlar (PB planlanan yapı) | 2020/75, 10/12/2020 — https://spk.gov.tr/data/61e0b4f31b41c613a0d633e0/2020-75.pdf | Arzum … 32.210.000 | 32.210.000 | – | – | 13.306.475 (mevcut) | 1.995.971 (ek) | 15,50-17 | `e2782f0711b16314…` |
| İzahname (SPK onaylı, KAP) | KAP 892902…, 11.12.2020 23:38 | çok parçalı; indirilmedi (zaman damgası liste API) | — |
| Tasarruf Sahiplerine Satış Duyurusu | KAP 892908, 11.12.2020 23:47:38 | planlanan yapı; talep toplama öncesi | `d3cce86de92cd2cc…` |
| Fiyat tespit raporu | KAP 892907, 11.12.2020 23:45:15 | — | — |
| Talep toplama sonuç bildirimi | KAP 893966 ÖDA + 2 ek, 21.12.2020 08:41:10 | birim fiyat 17,00; 13.306.475 + ek satış 1.995.971 = 15.302.446 satıldı; toplam talep 662.267.333 nominal; grup katları 53,6 / 18,7 / 1,5; 207.206 talep sahibi | bildirim `7a2a69867579b89e…`; ek `bf9851c9d32f4bb6…` |
| BIST Payların İşlem Görmeye Başlaması | KAP 894223, 22.12.2020 15:45:01 | first_trading_date, baz fiyat, pazar, nominal, sermaye | `f09607b03a8bb7a9…` |
| `ipo_price_tl` | | 17,00 (sonuç); SPK-B aralık 15,50-17 | |
| `shares_offered` | | 15.302.446 (ek satış DAHİL; H99 6-arz kuralıyla aynı) | |
| `post_ipo_share_capital` | | 32.210.000 (değişmez: yalnız ortak satışı) | |
| `capital_increase_shares` / `existing_share_sale_shares` | | 0 / 13.306.475 (+ ek 1.995.971) | |
| `total_demand_multiple` (f3) | | HESAPLANABİLİR: 662.267.333 / 13.306.475 = 49,77 (ek satış hariç payda) ya da / 15.302.446 = 43,28 (dahil) → CALCULATED_FROM_SOURCE_TOTALS + tanım etiketi zorunlu (DATA_NOTES §5 sorunu burada da var) | |
| PB alanları | | ipo_price_try aralık → REFUSED_PB_PRICE_RANGE (SPEC_PB_V0 §5); diğer 7 alan tabloda | |

## ISKPL (2021; Borsada (birincil piyasa, sabit fiyatla talep toplama); Ana Pazar; talep toplama 21-22/01/2021; ilk işlem 2021-01-28)

| Alan / belge | Kaynak ve yayın zamanı (Istanbul) | Değer / not | sha256 (ilk 16) |
|---|---|---|---|
| SPK haftalık bülteni A.1 İlk Halka Arzlar (PB planlanan yapı) | 2021/3, 14/01/2021 — https://spk.gov.tr/data/61e0b50a1b41c613a0d633e4/2021-3.pdf | Işık Plastik … 43.741.000 | 51.802.638 | 8.061.638 | – | 3.224.655 | – | 16,10 | `7e87278907d1abe9…` |
| Tasarruf Sahiplerine Satış Duyurusu | KAP listesinde TSSD ayrı görünmedi (izahname/TSSD 14–19.01.2021 aralığında, sorgu penceresi 31.12.2020'den başlar; analist raporları 19–22.01) | planlanan yapı; talep toplama öncesi | — |
| BIST birincil piyasa duyurusu | KAP 903309 Payların Borsa Birincil Piyasada Halka Arzı, 19.01.2021 17:49:06 | borsada satış: birincil piyasa günleri = talep toplama günleri | — |
| Talep toplama sonuç bildirimi | KAP 904444 ÖDA + 2 ek (Garanti Yatırım), 26.01.2021 15:35:59 | 16,10 TL; 11.286.293 satıldı; "Borsa İstanbul tarafından paylaşılan verilere göre … 14,2 katına denk gelen filtre edilmemiş 160.411.855 TL nominal talep"; 401.153 yatırımcı; grup tahsisatı yok | bildirim `5fb5e7044a2c5625…`; ek `4508a87acf08330c…` |
| BIST Payların İşlem Görmeye Başlaması | KAP 904453, 26.01.2021 16:18:25 | first_trading_date, baz fiyat, pazar, nominal, sermaye | `fae230dc49597e86…` |
| `ipo_price_tl` | | 16,10 | |
| `shares_offered` | | 11.286.293 | |
| `post_ipo_share_capital` | | 51.802.638 (SPK-B) | |
| `capital_increase_shares` / `existing_share_sale_shares` | | 8.061.638 / 3.224.655 (SPK-B ve sonuç metni) | |
| `total_demand_multiple` (f3) | | 14,2 SOURCE_REPORTED, UNFILTERED (kaynak BIST verisi, aracı kurum ÖDA'sında) | |
| PB alanları | | 8 alan SPK-B 2021/3; tek fiyat | |

## PSGYO (2021; Borsa dışı, sabit fiyatla talep toplama; Yıldız Pazar; talep toplama 09-10/12/2021; ilk işlem 2021-12-16)

| Alan / belge | Kaynak ve yayın zamanı (Istanbul) | Değer / not | sha256 (ilk 16) |
|---|---|---|---|
| SPK haftalık bülteni A.1 İlk Halka Arzlar (PB planlanan yapı) | BULUNAMADI: SPK 2021 dizininde 38–59 numaralı bültenler listelenmiyor (onay ≈ Kasım–Aralık 2021); SPK yıllık 2021 tablosu Ağustos'ta kesik | — | yok |
| İzahname (SPK onaylı, KAP) | KAP 980982…981009, 03.12.2021 18:25–19:11 | çok parçalı; indirilmedi (zaman damgası liste API) | — |
| Tasarruf Sahiplerine Satış Duyurusu | KAP 980992, 03.12.2021 18:37:12 | planlanan yapı; talep toplama öncesi | — |
| Fiyat tespit raporu | KAP 981481, 07.12.2021 13:00:26 | — | — |
| Talep toplama sonuç bildirimi | KAP 982811 ÖDA + 2 ek (Tera), 13.12.2021 07:39:27 | 16,38 TL; 67.500.000 tamamı; "yaklaşık 1,8 katına denk gelen 118.882.670 TL nominal filtrelenmemiş talep"; 48.428 yatırımcı; tahsisat bireysel %40→%55,9 | bildirim `0e4e257dd6c7f6dd…`; ek `ab51e87cac6b1d5e…` |
| BIST Payların İşlem Görmeye Başlaması | KAP 983147, 14.12.2021 18:13:07 | first_trading_date, baz fiyat, pazar, nominal, sermaye | `69edafd673769b34…` |
| `ipo_price_tl` | | 16,38 | |
| `shares_offered` | | 67.500.000 | |
| `post_ipo_share_capital` | | izahname/TSSD (indirilmedi) — KAP 983147 metninde sermaye | |
| `capital_increase_shares` / `existing_share_sale_shares` | | TSSD/izahname; SPK-B bulunamadı | |
| `total_demand_multiple` (f3) | | 1,8 SOURCE_REPORTED_APPROX (kesin 118.882.670/67.500.000 = 1,7612), UNFILTERED | |
| PB alanları | | SPK-B bulunamadığında TSSD (03.12.2021) planlanan yapı kaynağı olur; pit: TSSD < talep toplama ilk günü (09.12) ✓ | |

## PNLSN (2022; Borsa dışı, sabit fiyatla talep toplama; Ana Pazar; talep toplama 09-11/02/2022; ilk işlem 2022-02-18)

| Alan / belge | Kaynak ve yayın zamanı (Istanbul) | Değer / not | sha256 (ilk 16) |
|---|---|---|---|
| SPK haftalık bülteni A.1 İlk Halka Arzlar (PB planlanan yapı) | BULUNAMADI: onay 27/01/2022 (SPK yıllık tablo); 2022 dizininde 1–44 numaralı bültenler listelenmiyor | — | yok |
| İzahname (SPK onaylı, KAP) | KAP 997145…997165, 28.01.2022 23:16–23:38 | çok parçalı; indirilmedi (zaman damgası liste API) | — |
| Tasarruf Sahiplerine Satış Duyurusu | KAP 997169, 28.01.2022 23:40:15 | planlanan yapı; talep toplama öncesi | `22d0e59c7553b974…` |
| Fiyat tespit raporu | KAP 997165 (özet "F…"), 28.01.2022 23:38:01 | — | — |
| Talep toplama sonuç bildirimi | KAP 1001418 ÖDA + ek (Gedik), 14.02.2022 09:26:01 | 10,20 TL; taban 19.250.000 + ek satış 1.750.000 = 21.000.000; talep 167.899.308 nominal; "toplam halka arz büyüklüğünün yaklaşık 8 katı"; 42.122 yatırımcı; grup katları 11,47 / 4,89 / 2,86 | bildirim `f7df9fa55bce828b…`; ek `2f3b319c176d83ea…` |
| BIST Payların İşlem Görmeye Başlaması | KAP 1001895, 15.02.2022 18:00:14 | first_trading_date, baz fiyat, pazar, nominal, sermaye | `149f802b22557ab0…` |
| `ipo_price_tl` | | 10,20 | |
| `shares_offered` | | 21.000.000 (ek satış DAHİL) | |
| `post_ipo_share_capital` | | 75.000.000 (SPK yıllık tablo; izahname) | |
| `capital_increase_shares` / `existing_share_sale_shares` | | 17.500.000 / 3.500.000 (SPK yıllık tablo; sonuç eki) | |
| `total_demand_multiple` (f3) | | "yaklaşık 8" SOURCE_REPORTED_APPROX; kesin 167.899.308/21.000.000 = 7,995 (ek satış dahil payda) / 19.250.000 = 8,72 (hariç) → tanım etiketi | |
| PB alanları | | SPK-B yoksa TSSD (28.01.2022 23:40 < 09.02.2022) planlanan yapı; ek satış tavanı 1.750.000 → pb4 > 0 uyarısı | |

## AHGAZ (2022; Borsa dışı, sabit fiyatla talep toplama; Yıldız Pazar; talep toplama 14-16/12/2022; ilk işlem 2022-12-22)

| Alan / belge | Kaynak ve yayın zamanı (Istanbul) | Değer / not | sha256 (ilk 16) |
|---|---|---|---|
| SPK haftalık bülteni A.1 İlk Halka Arzlar (PB planlanan yapı) | 2022/69, 09/12/2022 — https://spk.gov.tr/data/639371df8f95db131098a051/2022-69.pdf | Ahlatcı … 168.500.000 | 208.000.000 | 39.500.000 | – | 13.250.000 | – | 66 | `9dc135f8f3b92604…` |
| İzahname (SPK onaylı, KAP) | KAP 1086486…, 09.12.2022 22:13 | çok parçalı; indirilmedi (zaman damgası liste API) | — |
| Tasarruf Sahiplerine Satış Duyurusu | KAP 1086492, 09.12.2022 22:17:19 | planlanan yapı; talep toplama öncesi | `1b2b35517ad29ce5…` |
| Fiyat tespit raporu | KAP 1086510/1086511, 09.12.2022 23:32–23:42 | — | — |
| Talep toplama sonuç bildirimi | KAP 1088372 ÖDA + ek (Ahlatcı Yatırım), 19.12.2022 11:20:02 | 66,00 TL; 52.750.000; "4,35 katına denk gelen 229.317.193 TL nominal talep"; grup katları filtrelenmemiş 9,60 / 6,50 / 2,04 / 1,04; 419.904 talep sahibi | bildirim `36ebd37a3e0d904d…`; ek `3a2290996e241f74…` |
| BIST Payların İşlem Görmeye Başlaması | KAP 1088538, 19.12.2022 19:15:28 | first_trading_date, baz fiyat, pazar, nominal, sermaye | `2d7eb568fc23d205…` |
| `ipo_price_tl` | | 66,00 | |
| `shares_offered` | | 52.750.000 | |
| `post_ipo_share_capital` | | 208.000.000 (SPK-B) | |
| `capital_increase_shares` / `existing_share_sale_shares` | | 39.500.000 / 13.250.000 (SPK-B) | |
| `total_demand_multiple` (f3) | | 4,35 SOURCE_REPORTED (toplam; filtre ifadesi yalnız grup katlarında → NOT_SPECIFIED/UNFILTERED kararı kural ister) | |
| PB alanları | | 8 alan SPK-B 2022/69; tek fiyat | |

## ONCSM (2023; Borsa dışı, sabit fiyatla talep toplama; Ana Pazar; talep toplama 28-29/12/2022; ilk işlem 2023-01-04)

| Alan / belge | Kaynak ve yayın zamanı (Istanbul) | Değer / not | sha256 (ilk 16) |
|---|---|---|---|
| SPK haftalık bülteni A.1 İlk Halka Arzlar (PB planlanan yapı) | 2022/70, 15/12/2022 — https://spk.gov.tr/data/639b40dc8f95db142c294e53/2022-70.pdf | Oncosem … 19.900.000 | 23.850.000 | 3.950.000 | – | 2.000.000 | – | 17.50 | `683358aec73f3a00…` |
| İzahname (SPK onaylı, KAP) | KAP 1089305…1089311, 22.12.2022 20:36–20:37 | çok parçalı; indirilmedi (zaman damgası liste API) | — |
| Tasarruf Sahiplerine Satış Duyurusu | KAP 1089312, 22.12.2022 20:37:59 | planlanan yapı; talep toplama öncesi | — |
| Fiyat tespit raporu | KAP 1089313, 22.12.2022 20:38:15 | — | — |
| Talep toplama sonuç bildirimi | KAP 1092046 ÖDA + 2 ek (İnfo), 02.01.2023 12:44:42 | 17,50 TL; 5.950.000; "toplamda 17,7 kat filtrelenmemiş talep" (105.567.156 nominal); 36.103 talep sahibi; grup katları 3,7 / 41,4 / 5,5 | bildirim `96a15342c899b062…`; ek `d41e2727f2ade787…` |
| BIST Payların İşlem Görmeye Başlaması | KAP 1092294, 02.01.2023 18:10:09 | first_trading_date, baz fiyat, pazar, nominal, sermaye | `971f724a85ab4e42…` |
| `ipo_price_tl` | | 17,50 | |
| `shares_offered` | | 5.950.000 | |
| `post_ipo_share_capital` | | 23.850.000 (SPK-B) | |
| `capital_increase_shares` / `existing_share_sale_shares` | | 3.950.000 / 2.000.000 | |
| `total_demand_multiple` (f3) | | 17,7 SOURCE_REPORTED, UNFILTERED (kesin 105.567.156/5.950.000 = 17,74) | |
| PB alanları | | 8 alan SPK-B 2022/70; tek fiyat | |

## REEDR (2023; Borsa dışı, sabit fiyatla talep toplama (i-SPK.128.21 sonrası: eşit dağıtım); Yıldız Pazar; talep toplama 13-15/09/2023; ilk işlem 2023-09-21)

| Alan / belge | Kaynak ve yayın zamanı (Istanbul) | Değer / not | sha256 (ilk 16) |
|---|---|---|---|
| SPK haftalık bülteni A.1 İlk Halka Arzlar (PB planlanan yapı) | 2023/53, 07/09/2023 — https://spk.gov.tr/data/64fa268e8f95db2304d13207/53-2023.pdf | Reeder … 780.000.000 | 950.000.000 | 170.000.000 | – | 45.000.000 | – | 9,30 | `802b011c0e5ef4a1…` |
| İzahname (SPK onaylı, KAP) | KAP 1193505…1193537, 09.09.2023 00:52–03:33 | çok parçalı; indirilmedi (zaman damgası liste API) | — |
| Tasarruf Sahiplerine Satış Duyurusu | KAP 1193538, 09.09.2023 03:40:00 | planlanan yapı; talep toplama öncesi | — |
| Talep toplama sonuç bildirimi | KAP 1195620 ÖDA + ek (TSKB), 18.09.2023 11:44:21 | 9,30 TL; 215.000.000; "4.262.914 yatırımcıdan … 3,95 katına denk gelen 848.216.796 TL nominal talep"; grup katları 2,41 / 12,63 | bildirim `49e211018f60eb08…`; ek `1a3cbb2075e05cc0…` |
| BIST Payların İşlem Görmeye Başlaması | KAP 1195976, 18.09.2023 18:12:10 | first_trading_date, baz fiyat, pazar, nominal, sermaye | `60ba08142d08d405…` |
| `ipo_price_tl` | | 9,30 | |
| `shares_offered` | | 215.000.000 | |
| `post_ipo_share_capital` | | 950.000.000 (SPK-B) | |
| `capital_increase_shares` / `existing_share_sale_shares` | | 170.000.000 / 45.000.000 | |
| `total_demand_multiple` (f3) | | 3,95 SOURCE_REPORTED (kesin 848.216.796/215.000.000 = 3,945) | |
| PB alanları | | 8 alan SPK-B 2023/53; tek fiyat | |

## Toplu bulgular

- 8/8 arzda ilk işlem tarihi, baz fiyat, pazar ve arz sonrası sermaye BIST bildiriminden; 8/8 arzda sonuç bildirimi listeleme öncesi yayımlanmış (en geç ilk işlem gününden 2 gün önce).
- f3: 6/8 kaynakta yazılı (ISKPL 14,2; PSGYO ≈1,8; PNLSN ≈8; AHGAZ 4,35; ONCSM 17,7; REEDR 3,95), 1/8 hesaplanabilir (ARZUM), 1/8 birincil belgede yok (ARDYZ, 2020 borsada satış). "Yaklaşık" ve "filtrelenmemiş" ifadeleri H99'daki `origin`/`filter_status` etiketleriyle aynen kodlanabilir; ek satışlı arzlarda payda tanımı belirsizliği (ARZUM, PNLSN) H99'daki sorunun aynısıdır.
- PB: SPK bülteni tablosu 2020'den beri aynı sütunlarla var; 8 örneğin 6'sında bülten bulundu, 2'sinde SPK dizini eksik (PSGYO, PNLSN) → TSSD yedek kaynak (talep toplamadan önce yayımlanmış). Fiyat aralıklı arz (ARZUM) PB'de ret.
- Point-in-time: KAP bildirimleri değiştirilemez, düzeltme yeni bildirimle gelir (evrende SNICA örneği); SPK bülten PDF'leri URL kimliğinde oluşturulma zamanı taşır; SPK yıllık xlsx tabloları sonradan derlenmiştir (2022-05 / 2023-10 tarihli) → yalnız çapraz denetim.
- Katılımcı sayısı (aday özellik f-1) 8/8 sonuç belgesinde; grup bazında tahsisat/dağıtım tablosu 7/8 (borsada satışta grup tahsisatı yok).

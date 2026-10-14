# Borsa İstanbul Pay Piyasası ve SPK halka arz kuralları — 2020-01-01 … 2026-09-24 değişiklik araştırması

Hazırlanma: 2026-09-24, 13:30–13:50 UTC. Yalnız resmi kaynaklar (borsaistanbul.com, spk.gov.tr, kap.org.tr, resmigazete.gov.tr). Erişim zamanları `date -u` ile alınmış toplu indirme zamanlarıdır; WebFetch/WebSearch ile açılan sayfalar için ilgili tur zamanı "≈" ile verilmiştir.

Erişim notu: borsaistanbul.com'un HTML sayfaları bu oturumda curl ile "Empty reply", WebFetch ile çoğunlukla "socket hang up" verdi; yalnız birkaç HTML sayfa (11645, 14113, /en/markets/equity-market/market-functioning, /en/markets/equity-market/markets, /en/.../sales-methods) açılabildi. borsaistanbul.com/files altındaki PDF'ler sorunsuz indi. Bu yüzden ana kaynak, 21/09/2026 tarihli Rev. 54 Pay Piyasası Prosedürü (revizyon karşılaştırma cetvelleri dahil), Rev. 18 Pay Piyasası Yönergesi ve Rev. 10/13 Kotasyon Yönergesi PDF'leridir.

Kısaltmalar: PPP = Pay Piyasası Prosedürü (02.PRO.01, Rev. 54, 21/09/2026, Sürüm 3.34); PPY = Pay Piyasası Yönergesi (Rev. 18, 21/09/2026); KY = Kotasyon Yönergesi; RG = Resmî Gazete; SPK-B = SPK Haftalık Bülteni.

---

## 1. Günlük fiyat marjı (Yıldız / Ana / Alt Pazar / YİP / PÖİP)

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı (≤ 40 kelime) |
|---|---|---|---|---|
| 04/11/2019 (yürürlük; duyuru 02/10/2019, 2019/65) | Yeni pazar yapısı: Yıldız G1 %20, Yıldız G2 %20, Ana G1 %20, Ana G2 %15, GİP %10, YİP %10, PÖİP %10. Alt Pazar henüz yok. | https://www.borsaistanbul.com/duyuru/11645/pay-piyasasi-yeni-pazar-yapisinda-uygulanacak-degerlendirme-kriterleri-ve-islem-esaslari ve PPY eski md. 39 tablosu (https://www.borsaistanbul.com/files/borsa-istanbul-as-pay-piyasasi-yonergesi.pdf) | ≈13:32 (WebFetch); PDF 13:36:56 | PPY eski tablo: "Fiyat Marjı %20 %20 %20 %15 %10 %10 %10" (sütunlar: Yıldız G1, G2, Ana G1, G2, GİP, YİP, PÖİP). |
| 13/03/2020 (Duyuru 2020/20, 12/03/2020) — COVID dönemi | Yıldız ve Ana Pazar (tüm gruplar) fiyat marjı %10'a indirildi; BYF/GMS/GMF/GSYF %20→%10; YPAH %50 kaldı. "İkinci bir duyuruya kadar" geçerli. | https://www.borsaistanbul.com/files/2020-20-Daily-Price-Limits.pdf (resmi İngilizce çeviri) | 13:46:33 | "Price margin ... of the shares traded in BIST Stars and BIST Main Market has been reduced to 10%" … "changed as of 13/03/2020 to be valid until a second announcement". |
| 01/10/2020 (Duyuru 2020/58, 17/09/2020) | Yeni yapı Yıldız/Ana/Alt: genel kural Yıldız %20, Ana %15, Alt/YİP/PÖİP %10 (Ana Pazar Grup 2 → Alt Pazar). | PPP s.23 dipnot 5 ve Tablo-4; PPY md. 39 (aynı PDF'ler) | 13:32:05 / 13:36:56 | "Paylarda Yıldız Pazar'da ±%20'den, Ana Pazar'da ±%15'ten; Alt Pazar, YİP ve PÖİP'te ±%10'dan … farklı olamaz." |
| 2020-03-13'ten bugüne | 2020/20 geçici uygulaması hâlâ yürürlükte olarak referans veriliyor: Yıldız ve Ana Pazar için fiilen %10. | PPP Tablo-4 dipnot 10; https://www.borsaistanbul.com/en/markets/equity-market/market-functioning | 13:32:05; ≈13:40 | PPP: "ikinci bir duyuruya kadar geçerli olduğu ilan edilen duyurularda (2020/20, 2020/21, 2020/50, 2025/38860) yer alan kurallar…"; EN sayfa: "Price margin is 10% for equities in BIST Stars, BIST Main…". |
| 28/07/2025 (Duyuru 2025/37905) | Gayrimenkul sertifikalarında marj değişikliği (GMS %5); paylara etkisi yok. | PPP rev. 50 satırı | 13:32:05 | "Gayrimenkul Sertifikalarında Fiyat Marjı Değişikliği Hk." |

Alt Pazar 2020–2023 cevabı: 01/10/2020'den itibaren Alt Pazar marjı genel kural olarak %10 (PPY md. 39, PPP Tablo-4); 04/11/2019–30/09/2020 arasında bu paylar "Ana Pazar Grup 2" idi (%15; 13/03/2020'den sonra 2020/20 ile %10). 2020 Mart geçici değişikliği: EVET (2020/20). 2020/20'nin resmî geri alındığına dair bir duyuru bulunamadı; PPP Rev. 54 (21/09/2026) hâlâ "ikinci duyuruya kadar" listesinde tutuyor.

---

## 2. İlk işlem günü baz fiyatı (borsada satış vs. talep toplama; birincil/ikincil ayrımı)

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| 01/04/2011 (Genelge 366, 11/03/2011) — tarihsel başlangıç | "Borsa Birincil Piyasada İlk Halka Arz Uygulaması" başladı (borsada satış yöntemi). | PPP "21 – BİAŞ Pay Piyasası Tarihsel Gelişimi" tablosu | 13:32:05 | "01.04.2011 Borsa Birincil Piyasada İlk Halka Arz Uygulaması Genelge No: 366 11.03.2011" |
| Yürürlükte (PPP 4.1.1; 2021–2026 revizyon cetvellerinde değişiklik yok) | Borsada satış (sürekli işlem) ile halka arzda birincil piyasa ilk gün baz fiyatı = izahnamedeki halka arz fiyatının en yakın fiyat adımına yuvarlanmış hâli; marj = ikincil piyasa oranları; süre 2 gün (uzatılamaz). | https://www.borsaistanbul.com/files/pay-piyasasi-proseduru.pdf s.17 | 13:32:05 | "birincil piyasadaki ilk işlem gününde uygulanacak baz fiyat, izahnamede yer alan halka arz fiyatının en yakın fiyat adımına yuvarlanmasıyla bulunan fiyattır." |
| Yürürlükte (PPP 4.1.1) | İkincil piyasa ilk seansı baz fiyatı = birincil piyasadaki son seansın KAPANIŞ fiyatı (AOF değil); ikincil piyasa ilk gün fiyat sınırları bu baz fiyattan hesaplanır. Halka arz sürerken ikincil işlem başlatılamaz. | aynı, s.17 | 13:32:05 | "ikincil piyasadaki işlem göreceği ilk seansta uygulanacak baz fiyat, birincil piyasadaki son seansta oluşan kapanış fiyatı olarak alınır" |
| Yürürlükte (PPP 4.1.1, dipnot 1) | Borsada satış süresi 2 iş günü ile sınırlı (SPK 08/07/2010, BİAŞ YK 16/07/2010). | aynı, s.18 | 13:32:05 | "Borsada satış yönteminin kullanıldığı halka arzların süresi 2 iş günü ile sınırlandırılmıştır." |
| Yürürlükte (PPP 4.1.1 Talep Toplama Yöntemleri – SFY/DFY) | Borsada talep toplama (SFY/DFY; ".HE" sırası): emir toplama en az 1, en fazla 3 iş günü; dağıtım 18:15 sonrası; MKK sicil ile tekleştirme. DFY'de satış fiyatı arzın tamamının karşılandığı fiyat seviyesi. | aynı, s.18–21 | 13:32:05 | "Emir toplama süresi en az bir iş günü, en fazla üç iş günüdür. Süre şirketin talebi üzerine BİAŞ Yönetim Kurulu tarafından belirlenir." |
| Borsa dışı talep toplama ile arz edilen payların ikincil piyasa ilk gün baz fiyatı | PPP'de açık hüküm BULUNAMADI. Uygulamada Borsa, KAP'ta "Payların İşlem Görmeye Başlaması" bildiriminde "Baz Fiyat" alanını ilan ediyor; bildirimde "Halka Arz Fiyatı" alanı yok, dolayısıyla "adıma yuvarlanmış halka arz fiyatı mı" sorusu bu kaynaklardan doğrulanamadı. | https://kap.org.tr/tr/Bildirim/1542557 (14/01/2026, ZGYO, DKB) | ≈13:35 ve ≈13:46 | Alanlar: "Borsa Karar Tarihi … Baz Fiyat (9,77 TL) … İşlem Göreceği Pazar (Ana Pazar) … Halka Arz Yöntemi (Borsa Dışında)". |
| İlgili ayrım (PPP 5.1.8) | Genel kural: baz fiyat = önceki işlem gününün kapanış fiyatı; baz fiyat yoksa tek fiyatta ilk eşleşme fiyatı, sürekli işlemde ilk işlem fiyatı. GSP'de ilk gün ihraç fiyatı esas (PPP 4.2.7). | aynı, s.51–52 ve s.32 | 13:32:05 | "BISTECH Sistemi'nde önceki işlem gününün kapanış fiyatı, baz fiyat olarak belirlenmektedir." / "GSP'de paylar için işlemlerin başlayacağı ilk gün baz fiyatın tespitinde ihraç fiyatı esas alınır." |
| Not: II-5.2 md. 17/2'deki "son iki işlem gününde birincil piyasada oluşan AOF" kuralı YPAH sonrası kalan payların borsa dışı satışına ilişkindir, ilk halka arz baz fiyatı değildir. | | https://spk.gov.tr/data/61e3664d1b41c61270320801/ba1adc3a-0abd-4616-bfb0-58b457d931ff.pdf | 13:32:18 | "…borsada halka arz süresinin son iki işlem gününde borsa birincil piyasasında oluşan günlük ağırlıklı ortalama fiyatlarının ağırlıklı ortalaması üzerinden satılması zorunludur." |

borsaistanbul.com/tr/sayfa/234 ve /244: açılamadı (socket hang up / empty reply) — BULUNAMADI (kaynak yerine PPP kullanıldı). Genelge 366 metni ayrıca açılmadı.

---

## 3. Fiyat adımı tablosu

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| 30/11/2015 (BISTECH geçişi; Dış Duyuru 2015/88) → 05/11/2023'e kadar geçerli | Paylar ve YPAH: 0,010–19,999→0,010; 20,000–49,999→0,020; 50,000–99,999→0,050; 100,000 ve üzeri→0,100. (2020'de geçerli tablo buydu.) | PPP Rev. 39 karşılaştırma cetveli "ESKİ METİN" (s.320) | 13:32:05 | "0,010 - 19,999 0,010 / 20,000 - 49,999 0,020 / 50,000 - 99,999 0,050 / 100,000 - üzeri 0,100" |
| 06/11/2023 (Duyuru 2023/19412, 28/08/2023; web kimliği duyuru/5892) | Yeni kademeler eklendi: 100,000–249,999→0,10; 250,000–499,999→0,25; 500,000–999,999→0,50; 1000,000–2499,999→1,00; 2500,000+→2,50. BYF tablosu da genişletildi (…0,25/0,50/1,00). | PPP Rev. 39 cetveli "YENİ METİN" + revizyon listesi satırı; duyuru sayfası https://borsaistanbul.com/tr/duyuru/5892/... (açılamadı) | 13:32:05 | "06/11/2023 Pay Piyasasında Fiyat Adımı ve Kotasyon Yayılma Aralıkları Düzenlemeleri … Duyuru 2023/19412 28/08/2023" |
| Yürürlükte (PPP 5.1.9, Tablo-7) | Mevcut tablo yukarıdaki yeni tablodur; adım baz fiyata değil fiyat seviyesine bağlı. Varant/sertifika/TAS'ta her seviyede 1 kuruş. | PPP s.52 | 13:32:05 | "Fiyat adımları baz fiyata bağlı olmaksızın ilgili fiyat seviyesine göre belirlenir." |

2020–2023-11 arasında başka adım değişikliği: PPP revizyon cetvellerinde (Rev. 17–38) 5.1.9'a dokunan tek değişiklik 17/11/2022 (emtia sertifikaları 1 kuruş) — pay tablosu değişmedi.

---

## 4. Fiyat limitlerinin hesabı: içeri doğru yuvarlama; baz fiyat = önceki kapanış

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| Yürürlükte (PPP 5.1.11 ve 5.6.2) | Üst limit aşağı adıma, alt limit yukarı adıma yuvarlanır (aralık daraltılır). | PPP s.53 | 13:32:05 | "Fiyat değişim sınırları hesaplanırken yuvarlama, işlem yapılabilecek fiyat aralığını daraltıcı şekilde içeri doğru yapılır. … üst fiyat limiti bulunurken aşağı adıma, alt fiyat limiti bulunurken yukarı adıma" |
| Başlangıç tarihi | BULUNAMADI. 01/03/2021–21/09/2026 arası tüm revizyon karşılaştırma cetvellerinde (Rev. 17–54) bu cümleye dokunan bir değişiklik yok; 2021 öncesi sürüm metnine erişilemedi. | PPP revizyon cetvelleri | 13:32:05 | (Rev. 27/50/52'de 5.1.11'e yapılan değişiklikler yalnız emtia/GMS/varant satırlarıdır.) |
| Yürürlükte (PPP 5.1.8) | Baz fiyat = önceki işlem gününün kapanış fiyatı; gün içinde işlem olmazsa aynı baz fiyat ertesi güne taşınır; temettü/sermaye artırımında teorik fiyatın en yakın adıma yuvarlanmış hâli. Değişiklik kaydı yok. | PPP s.51–52 | 13:32:05 | "bir önceki günden baz fiyata sahip bir payda gün içerisinde herhangi bir işlem gerçekleşmemişse bu baz fiyat, yine ertesi günün baz fiyatı olacaktır." |
| Kapanış seansı marjı | Sürekli işlem bölümündeki son işlem fiyatı üzerine ±%3. | PPP s.53 | 13:32:05 | "Kapanış seansında uygulanan ve sürekli işlem bölümünde gerçekleşen son işlem fiyatı üzerine ±%3 olarak uygulanır." |

THM bülteninin kendisinde formül değişikliği: bkz. madde 14 (dosya biçimi sürüm tarihçesi; 2020–2023'te alan değişikliği yok).

---

## 5. Pazar yapısı ve eşikler (dönemsel değerlendirme kriterleri + ilk kotasyon eşikleri)

### 5a. Pazar yapısı ve dönemsel değerlendirme (PPY md. 37 / PPP Tablo-3)

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| 04/11/2019 (2019/65; SPK 19/09/2019 sayı 52) | ABCD kalktı; Yıldız G1/G2, Ana G1/G2, GİP, YİP, PÖİP. | https://www.borsaistanbul.com/duyuru/11645/... ; PPP dipnot 9 | ≈13:32; 13:32:05 | "04/11/2019 itibarıyla ABCD gruplandırma düzenlemesi yürürlükten kalkmıştır." |
| 01/10/2020 (2020/58, 17/09/2020; SPK 14/09/2020) | Gruplar kaldırıldı: Yıldız, Ana, Alt Pazar (Ana G2 → Alt). Kriterler: Yıldız PD>500 mn, FDPD>100 mn; Ana PD>60 mn, FDPD>30 mn; yerli bireysel >1000/>500; likidite <2,5/<7,5. | PPP dipnot 5; PPP Rev. 20 cetveli "ESKİ METİN" | 13:32:05 | "Yıldız Pazar Grup 1 ve Yıldız Pazar Grup 2, Yıldız Pazar olarak; Ana Pazar Grup 1, Ana Pazar olarak; ve Ana Pazar Grup 2, Alt Pazar olarak değiştirilmiştir." |
| 01/04/2021 (2021/17, 11/03/2021) | FDO'su %5'in altında olan paylar PÖİP'e alınabilir. | PPP revizyon listesi; PPY md. 37(5) | 13:32:05; 13:36:56 | "FDO'su %5'in altında olan paylar PÖİP'e alınabilir." |
| 28/05/2021 (2021/38) | Yeni işlem görmeye başlayan şirketler ilk 3 ay pazar değerlendirmesine alınmaz; ilk 10 iş günü likidite hesabına girmez. | PPP Rev. 19 cetveli | 13:32:05 | "Payları yeni işlem görmeye başlayan şirketler, Borsada işlem görmeye başladıkları tarihi takip eden 3 ay içindeki pazar değerlendirmelerine dahil edilmez" |
| 10/09/2021 (2021/65) | Yıldız PD>1 mlr, FDPD>150 mn; Ana PD>150 mn, FDPD>60 mn; yerli bireysel >1.500/>750 (eşik 500→1.000 TL); yerli fon >5 mn; likidite <1,5/<5. | PPP Rev. 20 cetveli | 13:32:05 | "Piyasa Değeri (PD) > 1 milyar TL > 150 milyon TL / Fiili Dolaşımdaki Payların Piyasa Değeri (FDPD) > 150 milyon TL > 60 milyon TL" |
| 18/03/2022 (2022/7515) | Alt→Ana istisnası: FDPD>250 mn & likidite<1,5 → FDPD>120 mn & likidite<3. | PPP Rev. 24 cetveli | 13:32:05 | "Alt Pazar'da yer alan FDPD'si 120 milyon TL'nin üstünde ve likiditesi 3'ten küçük olanlar … Ana Pazar'a alınır." |
| 22/09/2023 (2023/20030, 21/09/2023) | Yıldız PD>3 mlr, FDPD>450 mn; Ana PD>450 mn, FDPD>180 mn; yerli fon >15 mn; likidite <0,5/<1,5. | PPP Rev. 37 cetveli | 13:32:05 | "Piyasa Değeri (PD) > 3 milyar TL > 450 milyon TL … FDPD > 450 milyon TL > 180 milyon TL" |
| 10/06/2024 (YK 03/04/2024, SPK onayı 04/06/2024 sayı 54987) | Pazarları belirleme kriterlerinde güncelleme (Rev. 44); GSP düzenlemeleri. | PPP Rev. 44 satırı | 13:32:05 | "Pazarları Belirleme Kriterlerinde detayları değişiklik cetvelinde belirtilen güncellemeler yapılmıştır." |
| 29/11/2024 (YK 10/10/2024, SPK onayı 29/11/2024) | Yıldız PD>6 mlr, FDPD>1 mlr; Ana PD>1 mlr, FDPD>400 mn; yerli fon >30 mn; likidite <0,15/<0,5; "Yerli Bireysel Yatırımcı Sayısı" kriteri tablodan çıktı. | PPP Rev. 45 cetveli | 13:32:05 | "Piyasa Değeri (PD) > 6 milyar TL > 1 milyar TL … FDPD > 1 milyar TL > 400 milyon TL" |
| 21/09/2026 (PPY Rev. 18) | Güncel PPY md. 37: PD>6 mlr/>1 mlr; FDPD>1 mlr/>400 mn; likidite <500/<1000 (baz puan); Volatilite ve Özsermaye kriterleri Yıldız için. | PPY s.16–17 | 13:36:56 | "Volatilite En yüksek oynaklık diliminde yer almamak / Özsermaye > Değerlendirmeye tabi tüm şirketlerin özsermaye medyan değeri" |

### 5b. İlk kotasyonda "halka arz edilen payların piyasa değeri" asgarileri (Kotasyon Yönergesi md. 8 / tanımlar)

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| 19/09/2019 (KY Rev. 5) / 04/11/2019 | Tanım: Yıldız = FDO'ya göre PD ≥150 mn; Ana <150 mn. Duyuru 11645: asgari halka arz PD Yıldız 100→150 mn, Ana 25→30 mn. | https://www.borsaistanbul.com/files/borsa-istanbul-kotasyon-yonergesi.pdf (Rev.10, 29/09/2023; revizyon ekleri) | 13:40:16 | "ee) Yıldız Pazar: fiili dolaşım oranına göre piyasa değeri 150.000.000 TL ve üzeri olan payların kota alındığı pazarı" |
| 14/09/2020 (KY Rev. 7) / 01/10/2020 | Tanım: Yıldız ≥200 mn; Ana 50–200 mn; Alt <50 mn (Alt Pazar'da ilk kotasyon mümkün). Tablo: Yıldız 200 mn, Ana 50 mn, Alt 20 mn (Rev. 8 "eski metin"). | aynı | 13:40:16 | "i) Alt Pazar: Fiili dolaşım oranına göre piyasa değeri 50.000.000 TL'nin altında olan payların kota alındığı pazarı" |
| 11/02/2021 (KY Rev. 8) | Asgari halka arz PD: Yıldız 300 mn, Ana 75 mn, Alt 40 mn; kârlılık şartı sağlanamazsa Yıldız için asgari 500 mn. | aynı | 13:40:16 | "Halka arz edilen payların piyasa değeri Asgari 300.000.000 TL / Asgari 75.000.000 TL / Asgari 40.000.000 TL" |
| 29/12/2023 (KY Rev. 11) | Tanım: Alt <250 mn; Ana 250 mn–1 mlr; Yıldız ≥1 mlr. | https://www.borsaistanbul.com/files/kotasyon_yonergesi.pdf (Rev.13, 21/09/2026) | 13:44:06 | "a) Alt Pazar: Halka arz edilen kısmının piyasa değeri 250 milyon TL'nin altında olan payların kota alındığı pazarı" |
| 31/12/2024 (KY Rev. 12) | Tanım: Alt <500 mn; Ana 500 mn–2 mlr; Yıldız ≥2 mlr. | aynı | 13:44:06 | "b) Ana Pazar: Halka arz edilen kısmının piyasa değeri 500 milyon TL - 2 milyar TL arasında" |
| 21/09/2026 (KY Rev. 13) | Tanım: Alt <1 mlr; Ana 1–4 mlr; Yıldız ≥4 mlr. Tablo: Yıldız asgari 4 mlr, Ana 1 mlr, Alt 400 mn; nominal/sermaye asgari %10/%20/%25. | aynı, md. 8 | 13:44:06 | "Halka arz edilen payların piyasa değeri Asgari 4 milyar TL / Asgari 1 milyar TL / Asgari 400 milyon TL" |

"Alt Pazar'da ilk halka arz mümkün müydü?": Evet — KY md. 8 tablosunda 01/10/2020'den beri Alt Pazar sütunu var. PPP Tablo-4'e göre Alt Pazar'da açığa satış/kredili işlem yok, brüt takas var, marj %10.

---

## 6. Tahsis ve dağıtım (II-5.2 md. 18–20; SPK ilke kararları)

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| 28/06/2013 (RG 28691), md. 18(4) değişik 01/12/2017 (RG 30257) | Asgari tahsisat: nominalin en az %10'u yurt içi bireysel, %10'u yurt içi kurumsal; borsada satış ve talep toplamasız arzlarda uygulanmaz; Kurul sıfıra indirebilir/bir kata kadar artırabilir. 2020–2026'da tebliğ değişikliği yok (değişiklik listesinde yalnız 2017). | https://spk.gov.tr/data/61e3664d1b41c61270320801/ba1adc3a-0abd-4616-bfb0-58b457d931ff.pdf | 13:32:18 | "nominal değerinin, en az yüzde onunun yurt içi bireysel yatırımcılara ve yüzde onunun yurt içi kurumsal yatırımcılara tahsis edilmesi zorunludur." |
| Yürürlükte, md. 20 | (2) eşit dağıtım (talep eden yatırımcı sayısına bölerek, tam karşılanana kadar); (3) istenirse oransal dağıtım; (4) bireysellere asgari tutar belirlenebilir. md. 19: grup içinde eşit ve adil. | aynı | 13:32:18 | "satışa sunulan toplam tutar, talep eden yatırımcı sayısına bölünür ve bu suretle bulunan tutar ve altındaki alım talepleri karşılanır." |
| 11/11/2021 (Kurul Kararı 59/1669; SPK-B 2021/57) | İlk halka arzlarda halka arz edilen payların PD ≤100 mn TL ise "Borsa'da Satış" yöntemi zorunlu (ç bendi). Ayrıca analist raporu asgari 2; finansal tablo süreleri. (ç) bendi 30/03/2023'te kaldırıldı. | https://spk.gov.tr/data/61e0b50a1b41c613a0d633e4/bd8f64f47f48f7d5c6fbed75a4bd7361.pdf | 13:44:05 | "halka arz edilen payların piyasa değerinin 100.000.000 TL ve altında olması durumunda 'Borsa'da Satış' yönteminin uygulanmasına" |
| 19/01/2023 (i-SPK 5.2, 3/96) | İçeriği alınamadı; 30/03/2023'te yürürlükten kaldırıldığı belirtiliyor. — İçerik BULUNAMADI | SPK-B 2023/21 s.7 | 13:42:21 | "i-SPK 5.2 (19/01/2023 tarihli ve 3/96 s.k.) sayılı İlke Kararı ile 11.11.2021 tarih ve 59/1669 sayılı Kararı'nın (ç) bendi yürürlükten kaldırılmıştır." |
| 30/03/2023 (i-SPK.128.21, 20/412; SPK-B 2023/21) | PD ≤750 mn: borsada satış zorunlu. >750 mn ve borsa dışı talep toplama: bireysel gruba eşit dağıtım zorunlu, oransal yasak; yatırımcı başına talep grup tahsisatının 1/4'ü; kurumsal başına %1 (PYŞ fonları %3); kaydırma kısıtı; 90/180 gün satış kısıtı. | https://spk.gov.tr/data/6425db2d8f95db1e9c11aef6/21-2023.pdf | 13:42:21 | "Bireysel yatırımcı grubundaki tüm yatırımcılara Tebliğ md. 20/2'de belirtilen esaslara göre eşit dağıtım yapılacak olup, Tebliğ md. 20/3'te öngörülen oransal dağıtım yöntemi uygulanmayacaktır." |
| 19/09/2024 (i-SPK.128.23, 1508; SPK-B 2024/48) | 750 mn eşiği korundu; yurt içi bireysele eşit dağıtım; "yüksek talepte bulunacak yatırımcı grubu"na %10'a kadar tahsis (eşit veya oransal, %100 nakit/%120 BIST-30 teminat); kurumsal tahsisatın ≥%50'si fonlara; %1/%3/%2 limitleri; 90/180 gün; 128.21 kaldırıldı. | https://spk.gov.tr/data/66ec7a468f95db223cb0e1a1/2024-48.pdf | 13:32:14 | "Yurt içi bireysel yatırımcı grubundaki yatırımcılara, Tebliğ'in 20'nci maddesinin ikinci fıkrasında yer alan esaslara göre eşit dağıtım yapılacaktır." |
| i-SPK.128.20 | BULUNAMADI (spk.gov.tr aramaları, 2021/2024 bültenleri, Halka Arz kitapçığı; hiçbir belgede geçmiyor). | — | ≈13:36–13:42 | — |
| 2021–2022'de bireysele eşit dağıtım zorunluluğu başlangıcı | Bulunan resmi kaynaklarda ilk zorunlu eşit dağıtım hükmü 30/03/2023 (i-SPK.128.21). 2021 kararı (59/1669) dağıtım yöntemi içermiyor. Daha erken bir zorunluluk BULUNAMADI. | yukarıdaki bültenler | — | — |
| Yurt içi bireysel asgari tahsisat %30 / %50 | BULUNAMADI. Tebliğdeki asgari %10'dur; ilke kararlarında bireysel için oran artışı yok (yalnız kurumsal içi %50 fon payı). | II-5.2; SPK-B 2023/21, 2024/48 | — | — |

---

## 7. Satış yöntemi tanımları, zorunluluk eşikleri, talep süresi

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| Yürürlükte, II-5.2 md. 12–16 | Yöntemler: talep toplama (sabit fiyat / fiyat aralığı / fiyat teklifi alma), talep toplanmaksızın satış, borsada satış (md. 16: esasları Borsa belirler). | II-5.2 PDF | 13:32:18 | "Borsada satış yöntemi, sermaye piyasası araçlarının borsa düzenlemeleri çerçevesinde borsada satışını ifade eder." |
| Yürürlükte, II-5.2 md. 10(7)-(8) | Halka arz satış süresi 2–20 iş günü; borsada satış: talep toplamasız 2 iş günü; talep toplamalı en az 2 en fazla 3 iş günü. Değişiklik: 2017 sonrası yok (değişiklik listesi). | aynı | 13:32:18 | "Satışın talep toplama suretiyle gerçekleşmesi durumunda talep toplama süresi, en az iki iş günü en fazla üç iş günüdür." |
| Yürürlükte, PPP 4.1.1 | Borsada SFY/DFY: emir toplama en az 1 en fazla 3 iş günü (BİAŞ YK belirler); erken dağıtım mümkün. 28/05/2021 (2021/38): maksimum emir değeri PPOD/PPD belirler. | PPP s.18–19; Rev. 19 cetveli | 13:32:05 | "Emir toplama süresi en az bir iş günü, en fazla üç iş günüdür." |
| 11/11/2021 | ≤100 mn TL → borsada satış zorunlu. | SPK-B 2021/57 | 13:44:05 | (bkz. madde 6) |
| 30/03/2023 → 19/09/2024 | ≤750 mn TL → borsada satış zorunlu (her iki ilke kararında). | SPK-B 2023/21; 2024/48 | 13:42:21; 13:32:14 | "Halka arz edilen payların piyasa değeri 750.000.000 TL ve altı olan halka arzlarda borsada satış yönteminin uygulanması zorunludur." |
| 2020-01-01 … 2021-11-10 arası eşik | BULUNAMADI (bu dönem için piyasa değeri eşikli bir zorunluluk kararı resmi kaynaklarda bulunamadı; tebliğdeki tek zorunluluk GİP için md. 17(4)). | II-5.2 md. 17(4) | 13:32:18 | "GİP'te ilk defa işlem görmek üzere başvuruda bulunan ortaklıkların paylarının satışında borsada satış yönteminin kullanılması zorunludur." |
| Sabit fiyatla talep toplama asgari gün değişikliği | BULUNAMADI (II-5.2'de 2017 sonrası değişiklik yok; PPP'de 1–3 iş günü kuralına dokunan revizyon yok). | — | — | — |

---

## 8. Fiyat istikrarı işlemleri (Pay Tebliği VII-128.1 md. 11 — not: md. 12/13 değil)

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| 22/06/2013 (RG 28685); 2020–2026'da md. 11 değişmedi | En çok 30 gün; ortaklık hesabına yapılacaksa fon brüt gelirin %20'si ve nominalin %20'si ile sınırlı; halka arz fiyatının üzerinde alım emri verilemez; izahnamede süre, aracı kurum, garanti olmadığı zorunlu açıklanır; sona erince ertesi iş günü KAP. | https://spk.gov.tr/data/61e3664d1b41c61270320801/73793d5c-b73a-4da7-81c5-0aedf963ae99.pdf | 13:32:17 | "Halka arz sonrası fiyat istikrarını sağlayıcı işlemler, ilgili payların borsada işlem görmeye başladığı tarihten itibaren en çok otuz gün süreyle gerçekleştirilebilir." |
| Değişiklik listesi | Tebliğ değişiklikleri: 27/2/2015, 6/3/2015, 30/6/2016, 26/1/2018, 13/2/2018, 24/7/2020 (VII-128.1.d: yalnız md. 27 pay satış bilgi formu), 18/5/2023 (VII-128.1.e: yalnız md. 5/3 kaldırıldı). 2024–2026 değişikliği aramalarda BULUNAMADI. | aynı; https://www.resmigazete.gov.tr/eskiler/2020/07/20200724-22.htm ; https://www.resmigazete.gov.tr/eskiler/2023/05/20230518-2.htm | 13:32:17; 13:35:28; 13:35:29 | RG 24/7/2020: "Pay Tebliği (VII-128.1)'nin mülga 27 nci maddesi aşağıdaki şekilde yeniden düzenlenmiştir." / RG 18/5/2023: "5 inci maddesinin üçüncü fıkrası yürürlükten kaldırılmıştır." |
| Borsa tarafı (PPP 4.1.3) | İstikrar işlemleri md. 11'e uygun, ayrı hesaptan; halka arz fiyatı üzerinde alım emri yok. 2004'ten beri uygulama (Genelge 194, 29/01/2004). | PPP s.22–23 ve tarihsel tablo | 13:32:05 | "fiyat istikrarını sağlayıcı işlemlerde halka arz fiyatının üzerinde alım emri verilemez." |

---

## 9. Satmama (lock-up) taahhüdü

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| 22/06/2013; 2020–2026'da md. 8 değişmedi | md. 8(1): %10+ ortaklar ve yönetim kontrolü sahipleri, borsada işlem başlangıcından itibaren 1 yıl halka arz fiyatının ALTINDA borsada satamaz (fiyata bağlı kısıt); borsa dışı alıcılar da bağlı. md. 8(6): ihtiyari olarak 1 yıl hiçbir şekilde satmama taahhüdü verilebilir. md. 8(4): fiyat düzeltmesi halka arz fiyatına da uygulanır. | Pay Tebliği PDF s.6–7 | 13:32:17 | "bir yıl süreyle halka arz fiyatının altındaki bir fiyattan borsada satamazlar ve bu payları halka arz fiyatının altında borsada satılması sonucunu doğuracak şekilde herhangi bir işleme tabi tutamazlar." |
| md. 5(8) ve md. 9(3) | Yüklenimle portföye alınan paylar: 6 ay halka arz fiyatı altında satılamaz. Satışa hazır bekletilen pay varsa (PD<40 mn) ortaklar 1 yıl mutlak satamaz. | aynı s.5, s.7 | 13:32:17 | "izahnamenin KAP'ta ilan edildiği tarihten itibaren bir yıl boyunca borsada satamazlar" |
| 30/03/2023 (i-SPK.128.21) ve 19/09/2024 (i-SPK.128.23) | Dağıtımdan pay alan yatırımcılar: 90 gün borsa dışı satış/virman/özel emir/toptan satış yasağı. Mevcut ortaklar: izahname onay tarihinden itibaren 180 gün, borsada satış dahil. | SPK-B 2023/21; 2024/48 | 13:42:21; 13:32:14 | "mevcut ortaklarının sahip oldukları paylar için (varsa halka arz edilen kısım hariç) bu kısıtlama, izahname onay tarihinden itibaren 180 gün boyunca ve borsada satışı da kapsayacak şekilde uygulanır." |
| "Fiyat tavanı %200" kuralı | BULUNAMADI (Pay Tebliği, II-5.2, SPK-B 2021/57, 2023/21, 2024/48, Halka Arz kitapçığında yok). | — | — | — |
| 2021/2022 Pay Tebliği değişikliği | Yok: RG değişiklik listesinde 2020 ve 2023 dışında kayıt yok. | Pay Tebliği PDF s.1 | 13:32:17 | "6- 24/7/2020 tarihli ve 31195 sayılı Resmi Gazete'de …" |

---

## 10. Açığa satış yasakları (piyasa geneli) ve yeni halka arzlara özgü kural

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| 28/02/2020 (Kurul kararı) | Pay piyasalarında açığa satış yasağı; gün içi açığa satış tuşuna basılmadan yapılan ve aynı gün kapatılan pozisyonlar dahil. | https://spk.gov.tr/duyurular/basin-duyurulari/2020/borsa-istanbul-a-s-pay-piyasalarinda-aciga-satis-islemlerine-iliskin-alinan-kurul-karari-duyurusu | 13:33:11 | "Borsa İstanbul A.Ş pay piyasalarında 28.02.2020 tarihinde; 1. Açığa satış işlemlerinin yasaklanmasına" |
| 02/03/2020 (duyuru) | 28/02/2020 kararı 02/03/2020'den itibaren ikinci duyuruya kadar devam. | https://spk.gov.tr/duyurular/basin-duyurulari/2020/borsa-istanbul-a-s-pay-piyasalarinda-aciga-satis-islemlerine-iliskin-duyuru | ≈13:32 | "02 Mart 2020 itibaren (ikinci bir duyuru yapılıncaya kadar devam edecek)" (WebFetch özeti) |
| 30/06/2020 (karar), 01/07/2020 yürürlük | BIST-30 paylarında yasak kaldırıldı; BIST-30 dışında devam. Kaynak sayfa (spk.gov.tr/Duyuru/Goster/20200630/1) artık 404 — yalnız arama özetinden; doğrulanamadı. | https://www.spk.gov.tr/Duyuru/Goster/20200630/1 (404) | ≈13:44 | (arama özeti) "01.07.2020 tarihinden itibaren BIST-30 Endeksinde yer alan pay piyasalarında yasakların kaldırılmasına" |
| BIST-30 dışı paylarda 2020 yasağının kaldırılma tarihi | BULUNAMADI (spk.gov.tr basın duyuruları 2020 listesi, bülten listeleri; 13/07/2020 "Açığa Satış Duyurusu" yalnız ceza/uyarı içeriyor). | https://spk.gov.tr/data/61e224131b41c61238836057/187280f60a02f9bb407df30cb5508832.pdf | 13:40:18 | "7 aracı kurum ve 18 yatırımcıya toplam 16.711.762 TL idari para cezası" |
| 06/02/2023 (Kurul kararı 6/155; SPK-B 2023/6, 2023/7) | Geçici açığa satış yasağı (+ depo şartı ve satış kanalı kısıtı; bu iki bent 07/02/2023'te kaldırıldı, yasak devam). | https://spk.gov.tr/data/63e15ce18f95db22acf5133e/7-2023.pdf ; https://spk.gov.tr/data/63e0a31d8f95db1e80628edc/6-2023.pdf | 13:32:15–16 | "(2) ve (3) numaralı bentlerinin 07.02.2023 tarihinden itibaren yürürlükten kaldırılmasına, (1) ve (4) numaralı bentlerindeki uygulamanın ise devam etmesine" |
| 05/12/2024 (62/1863; SPK-B 2024/55), yürürlük 02/01/2025 | 2023 yasağı yalnız BIST 50 paylarında kaldırıldı. | https://spk.gov.tr/data/675211f38f95db2adc0f1d57/2024-55.pdf | 13:42:22 | "02/01/2025 tarihinden itibaren, Borsa İstanbul AŞ tarafından ilan edilen BIST 50 endeksinde yer alan pay piyasaları ile sınırlı olarak kaldırılmasına" |
| 23/03/2025 (18/574; SPK-B 2025/18) | 24/03/2025–25/04/2025 tüm pay piyasalarında açığa satış yasağı; 2025/24 ile 30/05/2025 seans sonuna kadar uzatıldı. | https://spk.gov.tr/data/67e0635d8f95db24685d2486/2025-18.pdf ; https://spk.gov.tr/data/6802b3918f95db1c64570efe/2025-24.pdf ; https://spk.gov.tr/data/67e03a828f95db24685d246e/23032025_SPK-Duyuru.pdf | 13:45:28–29; 13:37:06 | "açığa satış işlemlerinin 24.03.2025 tarihinden 25.04.2025 tarihi seans sonuna kadar yasaklanmasına" / "30.05.2025 tarihi seans sonuna kadar uygulanmasına devam edilmesine" |
| 2025 sonu – 2026 | BIST 50 dışı paylarda 2023 yasağı sürüyor (2025/57 bülteninde "BIST 50 Endeksi dışındaki pay piyasalarında Kurul kararlarına aykırı açığa satış" cezaları). 17/09/2026 (SPK-B 2026/60): yalnız özkaynak esnekliği; açığa satışa ilişkin yeni karar yok. | https://spk.gov.tr/data/690e4fc58f95db2a787fafa0/2025-57.pdf ; https://spk.gov.tr/data/6aab8e7b8f95db07100fd7b4/2026-60.pdf | 13:32:19; 13:37:06 | 2026/60: "02.10.2026 tarihi seans sonuna kadar … özkaynak oranı asgari %20 olacak şekilde esnek olarak uygulanabilmesine" |
| Yeni halka arz edilen paylarda ilk günlere özgü açığa satış/kredili yasağı | BULUNAMADI. PPP 5.8.1: liste pazar bazlı (Yıldız, Ana, GSP + BYF'ler; Alt/PÖİP/YİP hariç). PPP 5.8.2: açılış seansında açığa satış emri girilemez. Gün sayısına bağlı özel kural yok. | PPP s.97–98 | 13:32:05 | "Yıldız Pazar, Ana Pazar ve Girişim Sermayesi Pazarında işlem gören paylar, buna ek olarak BYF'ler hem kredili alıma hem de açığa satış işlemine konu olabilir." |

---

## 11. Devre kesici (pay bazında ve endekse bağlı)

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| 30/11/2015 (BISTECH; 2015/88) ve 17/07/2017 (2017/54) | Pay bazında devre kesici başladı; 2017 işleyiş değişikliği. | PPP tarihsel tablo | 13:32:05 | "30.11.2015 … • Devre kesici" / "17.07.2017 Devre Kesici İşleyişinde Yapılacak Değişiklik Dış Duyuru: 2017/54" |
| 04/11/2019 | Tetikleme: Yıldız G1/G2 %10, Ana G1 %10, Ana G2 %7,5; emir toplama 5/5/15/25 dk. | PPY eski md. 39 tablosu; 2020/20 PDF "current practice" | 13:36:56; 13:46:33 | "Price Change Triggering Circuit Breaker 10% 10% 10% 7,5% … Call Period 5 / 5 / 15 / 25 minutes" |
| 13/03/2020 (2020/20) | Yıldız+Ana: tetikleme %5, emir toplama 30 dk, eşleşme 2 dk; ikinci duyuruya kadar. | https://www.borsaistanbul.com/files/2020-20-Daily-Price-Limits.pdf | 13:46:33 | "Price change triggering circuit breaker in BIST Stars and BIST Main Market has been reduced to 5%, Circuit breaker call period will be 30 minutes" |
| 2020/21 (tarih BULUNAMADI; 2020/20'den sonra) | Tüm paylarda devre kesici %5 ve yalnız aşağı yönlü; (EN sayfaya göre emir toplama 15 dk); ikinci duyuruya kadar; PPP Rev. 54 hâlâ referans veriyor. | https://www.borsaistanbul.com/en/markets/equity-market/market-functioning ; PPP dipnot 10 | ≈13:40; 13:32:05 | "Circuit breaker for all equities is triggered 5% and in downward trend only." |
| 01/10/2020 (2020/58) genel kural | Tetikleme Yıldız %10, Ana %7,5, Alt %5; emir toplama 5/15/15 dk; eşleşme 2 dk. | PPP Tablo-4; PPY md. 39 | 13:32:05 | "Devre Kesici Tetikleme Oranı %10 %7,5 %5 - - / Devre Kesici Sonrası Emir Toplama Süresi 5 dakika 15 dakika 15 dakika" |
| 10/08/2020 (2020/50, duyuru 07/08/2020; web 14113) | Endekse Bağlı Devre Kesici (EBDKS): BIST 100 önceki kapanışa göre %5 (1. eşik) ve %7 (2. eşik) düşüş; paylar 20 dk durdurma. | https://www.borsaistanbul.com/duyuru/14113/endekse-bagli-devre-kesici-sistemi-hakkinda | ≈13:32 | "5% or more … 7% or more" (WebFetch özeti); PPP: "10.08.2020 Endekse Bağlı Devre Kesici Sistemi Duyuru 2020/50 07.08.2020" |
| 09/02/2022 (2022/25, 08/02/2022) | EBDKS 17:00–18:00 arasında devreye girerse kapanış seansına kadar durdurma (önceden 17:30 sonrası seans sonlandırılıyordu); EBDKS sonrası yukarı adım kuralı. | PPP Rev. 23 cetveli | 13:32:05 | "EBDKS'nin devreye girmesi halinde açığa satış yapılabilen işlem sıralarında açığa satış işlemlerinde seans sonuna kadar yukarı adım kuralı uygulanır." |
| 11/01/2023 (2023/14260, 10/01/2023) | Pay bazında devre kesici çalışınca seans sonuna kadar yukarı adım kuralı. | PPP Rev. 30 satırı ve 5.3.4 | 13:32:05 | "Devre kesici uygulamasının başladığı açığa satış yapılabilen işlem sıralarında açığa satış işlemlerinde seans sonuna kadar yukarı adım kuralı uygulanır." |
| 03/02/2023 (2023/14904) | BIST 100 %3 düşünce yukarı adım kuralı (2025'te %2'ye indirildi). | PPP Rev. 31; 2025/38860 PDF | 13:32:05; 13:40:09 | "BIST 100 Endeksi düşüş değeri %3'ten %2'ye çekilecektir." |
| 01/09/2025 (2025/38860, 29/08/2025) | Pay bazında emir toplama tüm paylarda 10 dk (Yıldız 5→10; Ana/Alt/GSP 15→10); EBDKS tek aşama %6; durdurma 20→10 dk (.E vb.), 30→20 dk (.V/.C/.F/.R); 17:30 sonrası kuralı. | https://www.borsaistanbul.com/files/duyuru-38860-TR.pdf | 13:40:09 | "EBDKS uygulaması tek aşamalı olarak uygulanmaya başlayacak ve endeks değerinin %6 veya daha fazla düşmesi halinde devreye girecektir." |
| Yeni halka arz paylarında ilk günlerde devre kesici istisnası | BULUNAMADI. PPP'de yalnız PÖİP/NYİP/GSP'ye alınan paylarda ilk gün "serbest marj" hükmü var; ilk halka arz paylarına özgü devre kesici istisnası yok. | PPP 4.2.7–4.2.8, 5.3.4 | 13:32:05 | "Platformda işlemlerin başlayacağı ilk gün, ortaklık payları serbest marj ile işlem görmeye başlar" (PÖİP) |

---

## 12. İlk işlem günü özel tedbirleri (brüt takas, kredili yasağı, emir iptali)

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| 01/10/2020'den beri (pazar bazlı) | Brüt takas: Alt Pazar, YİP, PÖİP'te VAR; Yıldız/Ana'da YOK. Açığa satış/kredili: yalnız Yıldız ve Ana. Dolayısıyla Alt Pazar'da başlayan halka arz payı ilk günden brüt takasa tabidir (pazar kuralı gereği, ilk-gün kuralı değil). | PPP Tablo-4; PPY md. 39 | 13:32:05 | "Açığa Satış ve Kredili İşlem VAR VAR YOK YOK YOK / Brüt Takas YOK YOK VAR VAR VAR" |
| Yürürlükte (PPP 6.1.1) | Brüt takas, Takasbank'ın netleştirmeyi kaldırdığı paylarda (VBTS/SPK/Borsa tedbiri) uygulanır. | PPP s.100–101 | 13:32:05 | "Netleştirme uygulaması kaldırılan paylarda Takasbank tarafından BT uygulaması yapılmakta" |
| VBTS (tedbir sırası) | 1. aşama açığa satış ve kredili işlem yasağı, 2. aşama brüt takas, 3. aşama emir paketi (süreler arama özetinde 1 ay; sayfa açılamadı — doğrulanamadı). | https://www.borsaistanbul.com/en/sayfa/2372/volatility-based-measures-system-vbts (socket hang up) | ≈13:46 | (arama özeti) "'Prohibition of Short Selling and Margin Trading' as the first stage measure for 1 month, 'Gross Settlement' as the second stage measure for 1 month" |
| 01/03/2021 (2021/4, 05/02/2021) | Açılış seansının son 5 dakikasında emir iptali/kötüleştirme/miktar azaltımı yasak; açılışta piyasa/piyasadan limite emir yok (tüm pazarlar). | PPP Rev. 17 cetveli | 13:32:05 | "açılış seansının son 5 dakikasında emir iptali yapılamaz" |
| 15/02/2023 (2023/15151, 14/02/2023) | Açılış seansının tamamında emir iptali/kötüleştirme/miktar azaltımı yasak (emtia sertifikaları hariç). | PPP Rev. 32 cetveli; KAP https://www.kap.org.tr/tr/Bildirim/1113112 | 13:32:05; ≈13:45 | "açılış seansı uygulanan tüm sermaye piyasası araçlarında, açılış seansında emir iptali yapılamaz." |
| 25/09/2023 (2023/19885, 15/09/2023) | Yıldız ve Ana Pazar'da açılış seansında piyasa ve piyasadan limite emir yeniden serbest. | PPP dipnot 15 | 13:32:05 | "25/09/2023 tarihi itibarıyla geçerli olmak üzere, Yıldız Pazarda, Ana Pazarda … açılış seansında piyasa ve piyasadan limite emir türleri ile emir girilebilir." |
| 25/09/2020 (2020/62) | Borsada halka arzlarda: birden fazla hesabı olan yatırımcının talebi tek hesaptan; MKK sicil ile tekleştirme. | PPP s.18–19 | 13:32:05 | "birden fazla hesabı bulunan yatırımcıların taleplerinin yatırımcı bazında konsolide edilerek tek hesaptan iletilmesi gerekmektedir." |
| "Yeni halka arzlarda ilk X gün brüt takas / kredili yasağı / emir iptali yasağı" kuralı | BULUNAMADI (PPP Rev. 54 tam metin, PPY, KY, 2023–2026 revizyon cetvelleri; borsaistanbul.com HTML duyuru aramaları). | — | — | — |

---

## 13. Piyasa kapanışları (Şubat 2023 depremi) ve 2020 seans saatleri

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| 08/02/2023 kapatma kararı (BIST duyurusu) | BULUNAMADI: borsaistanbul.com HTML erişilemedi; KAP aramalarında 08/02/2023 tarihli Borsa İstanbul kapatma bildirimi bulunamadı. Kapanışın 5 iş günü olduğu yalnız dolaylı: PPP 4.3.1 "beş işlem gününe kadar" YK yetkisi. | PPP s.39 | 13:32:05 | "piyasaların, pazarların, platformların veya sistemlerin beş işlem gününe kadar geçici olarak kapatılmasına Yönetim Kurulu karar verebilir." |
| 06/02/2023 (SPK-B 2023/6, 2023/7) | Açığa satış yasağı, depo şartı (07/02'de kaldırıldı), deprem bölgesi müşterilerine kredili işlem esnekliği. | https://spk.gov.tr/data/63e15ce18f95db22acf5133e/7-2023.pdf | 13:32:15 | "06.02.2023 tarihi itibariyle mücbir halin yaşandığı bu yerlerde ikametgâhı, işyeri adresi veya şubede hesabı bulunan müşterilere" |
| 09/02/2023 (SPK-B 2023/9, karar 8/174) | Deprem bağışlarına ilişkin kolaylıklar (piyasa kapanışına dair karar metni bültende yok). | https://spk.gov.tr/data/63e538958f95db0968f0b932/9-2023.pdf | 13:47:29 | "depremler nedeniyle bağışta bulunmak isteyen şirketler bakımından" |
| 14/02/2023 (SPK-B 2023/10, karar 9/176; i-SPK.22.7 geri alım) | Tüm yatırımcılara kredili işlem esnekliği (özkaynak koruma %20; 19.03.2020 tarihli 17/400 kararına atıf), geri alım kolaylığı, pay satış bilgi formu eşiği %3 (i-SPK.128.19). | https://spk.gov.tr/data/63eb7d9b8f95db27b0ec6712/10-2023.pdf | 13:32:16 | "Kurulumuzun 19.03.2020 tarihli ve 17/400 sayılı Kararı uyarınca %35 olarak belirlenen başlangıç özkaynak koruma oranının, 10.04.2023 tarihine kadar %20 olarak uygulanmasına" |
| 15/02/2023 açılış (BIST 2023/15151, 14/02/2023; KAP DKB 14/02/2023 16:04) | Açılış seansında emir iptali/kötüleştirme/miktar azaltımı yasağı; emir/işlem oranı 15:1→5:1, eşik aşım ücreti 0,03→0,25 kuruş; İAK ücretleri +%20; VİOP seans sonu 18:10; yatırım aracı bazındaki tüm mevcut tedbirler kaldırıldı; geri alım endeksi. Marj/devre kesici değişikliği belirtilmiyor. | https://www.kap.org.tr/tr/Bildirim/1113112 ; PPP Rev. 32 | ≈13:45; 13:32:05 | "Açılış seansında emir iptali, fiyat kötüleştirme ve miktar azaltımına izin verilmemesine" … "tüm tedbirlerin kaldırılmasına karar verilmiştir" (WebFetch özeti) |
| 2020 seans saatleri (COVID) | Değişiklik kaydı BULUNAMADI: PPP tarihsel gelişim tablosunda 2020'de yalnız 30/03/2020 (BYF'lerin kapanış seansına dahil edilmesi, 2020/25) ve 10/08/2020 EBDKS var; seans süresi kısaltma kaydı yok. SPK 19/03/2020 COVID tedbirleri seans saatine değinmiyor. | PPP tarihsel tablo; https://spk.gov.tr/duyurular/basin-duyurulari/2020/covid-19-salgini-nedeniye-alinan-tedbirler | 13:32:05; ≈13:36 | "30.03.2020 Borsa Yatırım Fonlarının Kapanış Seansına Dahil Edilmesi Hk. Duyuru 2020/25 26/03/2020" |

---

## 14. THB/THM günlük bülten dosya biçimi (Pay Piyasası Veri Bildirim ve Kabul Formatları)

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| 19/10/2017 (Sürüm 1.12) | Bülten (2.1.4), Sabah Marj (2.1.5) ve Akşam Marj (2.1.6) tablolarına "ACIGA SATIS" alanı eklendi. 2020-01-01'de geçerli sürüm buydu. | https://www.borsaistanbul.com/files/pay-piyasasi-veri-bildirim-ve-kabul-formatlari.pdf | 13:32:13 | "1.12 19.10.2017 2.1.4 Bülten 2.1.5 Sabah Marj Bilgileri ve 2.1.6 Akşam Marj Bilgileri tablolarına 'ACIGA SATIS' alanı eklendi." |
| 20/09/2023 (Sürüm 1.13) | Bülten tablosuna "BIST KATILIM TUM ENDEKS" alanı eklendi. (2020-01-01 … 2023-09-19 arasında bülten sütunlarında değişiklik kaydı yok.) | aynı | 13:32:13 | "1.13 20.09.2023 2.1.4 Bülten tablosuna 'BIST KATILIM TUM ENDEKS' alanı eklendi." |
| 29/04/2024 (Sürüm 1.14, güncel) | Yalnız 3.1 Referans Tabloları güncellendi. | aynı | 13:32:13 | "1.14 29.04.2024 3.1 Referans Tabloları güncellendi." |
| Yürürlükte (PPP 5.8.4) | Bültende açığa satış sütunları: en düşük/en yüksek açığa satış fiyatı, AOF, hacim, adet, sözleşme sayısı. | PPP s.99 | 13:32:05 | "Açığa satış işlemleri Bültende pay bazında aşağıdaki sütun başlıklarıyla ilan edilir." |
| Ayrıca | DataStore sürümü: "DataStore_Veri_Bildirim_ve_Kabul_Formatları.pdf" (datastore.borsaistanbul.com) — açılmadı. Teknik dokümanlar sayfası (sayfa/441) açılamadı. | https://datastore.borsaistanbul.com/assets/files/DataStore_Veri_Bildirim_ve_Kabul_Formatlar%C4%B1.pdf | — | — |

Not: Bu doküman üyelere dağıtılan CSV dosyalarını tanımlar; borsaistanbul.com/data/thb ve /data/thm altındaki günlük zip'ler bu araştırmada indirilmedi (yasak).

---

## 15. KAP bildirim şablonları

| Tarih | Değişiklik | Kaynak URL | Erişim (UTC) | Alıntı |
|---|---|---|---|---|
| Güncel örnek 14/01/2026 (ZGYO) | "Payların İşlem Görmeye Başlaması / Stocks Starting To Trade" şablonu; gönderen Borsa İstanbul (DKB). Alanlar: Borsa Karar Tarihi, ünvan, nominal tutar, Baz Fiyat, Pazar, Maksimum Emir Değeri, işlem başlangıç tarihi, Halka Arz Yöntemi, Halka Arz Tarihi, kod. | https://kap.org.tr/tr/Bildirim/1542557 | ≈13:35 | "Şablon Adı: Payların İşlem Görmeye Başlaması / Stocks Starting To Trade" (WebFetch özeti) |
| 2020–2023'te bu şablonun varlığı | BULUNAMADI (kap.org.tr aramaları 2020–2021 örneğine ulaşamadı; bildirim sorgu arayüzü açılmadı). | — | ≈13:44 | — |
| 31/08/2021 (Orçay) | ÖDA, "Halka Arz Sonuçları" şablonu ile (alanlar: Bildirim İçeriği, Açıklamalar, güncelleme/düzeltme bayrakları). | https://www.kap.org.tr/tr/Bildirim/960955 | ≈13:38 | "Şablon Adı: 'Halka Arz Sonuçları' şablonu kullanılmıştır" (WebFetch özeti) |
| 22/11/2021 (Konya Kağıt) ve 05/03/2026 (Luxera GYO) | Sonuçlar "Özel Durum Açıklaması (Genel)" + PDF ek olarak veriliyor; yani şablon zorunlu tek biçim değil. | https://www.kap.org.tr/tr/Bildirim/978872 ; https://www.kap.org.tr/tr/Bildirim/1566741 | ≈13:44; ≈13:38 | "Ek Dokuman: 'Özel Durum Açıklaması_1_SatisSonuclari.pdf'" |
| "Halka Arz Sonuçları" şablonunun ilk kullanım tarihi | BULUNAMADI (en erken doğrulanan kullanım 31/08/2021). | — | — | — |

---

## Özet sayaç

- 15 kuralın 15'i için en az bir resmi kaynak ve tarih bulundu.
- Tamamen veya kısmen BULUNAMADI olarak işaretlenen alt sorular (12): 2/borsa dışı talep toplamada ilk gün baz fiyat kuralı; 4/içeri yuvarlamanın başlangıç tarihi; 6/i-SPK.128.20 ve i-SPK 5.2 içeriği, 2021–22 eşit dağıtım zorunluluğu, %30/%50 bireysel asgari; 7/2021 öncesi eşik ve talep süresi değişikliği; 9/%200 fiyat tavanı; 10/2020 yasağının BIST-30 dışı kaldırılma tarihi ve ilk-gün açığa satış kuralı; 11/2020/21 duyuru tarihi ve yeni arz istisnası; 12/"ilk X gün brüt takas" kuralı; 13/08-02-2023 kapatma duyurusu ve 2020 seans saati değişikliği; 15/şablonların 2020–2023 varlığı.

---

## Maruziyet (istenmeden görülen listeleme-sonrası bilgi)

Fiyat, getiri, tavan, hacim veya performans bilgisi içeren hiçbir sayfa açılmadı ve arama özetlerinde böyle bir veri görülmedi. Sınırda kalan görüntüler:

1. WebSearch (kap.org.tr, "Halka Arz Sonuçları" sorguları, ≈13:38 ve ≈13:44): sonuç başlıklarında şirket adları göründü — Orçay (31/08/2021), Reeder (18/09/2023), Ebebek, Barem Ambalaj, Katılım Evim (KTLEV), SDT, LDR Turizm, A1 Capital, Konya Kağıt, Albayrak (2026), Luxera (2026). Yalnız başlık/tarih; fiyat veya getiri yok. Reeder ve Konya Kağıt/Orçay sayfaları hariç hiçbiri açılmadı.
2. KAP 960955 (Orçay, 2021) ve 978872 (Konya Kağıt, 2021) açıldı: talep toplama sonuç bildirimleri (listeleme öncesi bilgi). WebFetch özetleri fiyat/performans içermediğini açıkça belirtti; sayısal dağıtım verisi alınmadı.
3. SPK-B 2021/57 ve 2023/21 indirildi; "İlk Halka Arzlar" onay tablolarında bazı şirket/ortak adları ve nominal tutarlar grep çıktısında göründü (ör. Bera Holding'e ait paylar). Listeleme öncesi onay bilgisidir; fiyat/performans yok.
4. KAP 1138804 (Tera Yatırım, 14/04/2023 genel kurul ÖDA'sı) yanlışlıkla açıldı: bedelsiz sermaye artırımı ve yönetim kurulu bilgileri; borsa fiyatı/getirisi yok.
5. SPK-B 2024/50 grep'inde bir aracı kuruma açığa satış yasağı ihlali cezası satırı göründü; halka arz performansıyla ilgisiz.

---

## Açılan URL listesi (erişim zamanı UTC, 2026-09-24)

Toplu indirmeler (curl; kesin zamanlar):
- https://www.borsaistanbul.com/files/pay-piyasasi-proseduru.pdf — 13:32:05
- https://www.borsaistanbul.com/files/pay-piyasasi-veri-bildirim-ve-kabul-formatlari.pdf — 13:32:13
- https://spk.gov.tr/data/66ec7a468f95db223cb0e1a1/2024-48.pdf — 13:32:14
- https://spk.gov.tr/data/63e15ce18f95db22acf5133e/7-2023.pdf — 13:32:15
- https://spk.gov.tr/data/63eb7d9b8f95db27b0ec6712/10-2023.pdf — 13:32:16
- https://spk.gov.tr/data/63e0a31d8f95db1e80628edc/6-2023.pdf — 13:32:16
- https://spk.gov.tr/data/61e3664d1b41c61270320801/73793d5c-b73a-4da7-81c5-0aedf963ae99.pdf (Pay Tebliği) — 13:32:17
- https://spk.gov.tr/data/61e3664d1b41c61270320801/ba1adc3a-0abd-4616-bfb0-58b457d931ff.pdf (II-5.2) — 13:32:18
- https://spk.gov.tr/data/658f25ff8f95db27604610b0/82-2023.pdf — 13:32:19
- https://spk.gov.tr/data/690e4fc58f95db2a787fafa0/2025-57.pdf — 13:32:19
- https://www.borsaistanbul.com/files/duyuru-17538-tr.pdf — 13:32:21
- https://www.resmigazete.gov.tr/eskiler/2020/07/20200724-22.htm — 13:33:08 ve 13:35:28
- https://www.resmigazete.gov.tr/eskiler/2023/05/20230518-2.htm — 13:33:09 ve 13:35:29
- https://spk.gov.tr/duyurular/basin-duyurulari/2020/borsa-istanbul-a-s-pay-piyasalarinda-aciga-satis-islemlerine-iliskin-alinan-kurul-karari-duyurusu — 13:33:11
- https://www.borsaistanbul.com/duyuru/14113/endekse-bagli-devre-kesici-sistemi-hakkinda — 13:33:12 (curl; metin boş) ve ≈13:32 (WebFetch)
- https://www.borsaistanbul.com/files/borsa-istanbul-as-pay-piyasasi-yonergesi.pdf — 13:36:56
- https://www.borsaistanbul.com/file/file-media/endekse-bagli-devre-kesici-sistemi-2020-53.pdf — 13:36:58 (metin çıkarılamadı, görüntü PDF)
- https://spk.gov.tr/data/67e03a828f95db24685d246e/23032025_SPK-Duyuru.pdf — 13:37:06
- https://spk.gov.tr/data/6aab8e7b8f95db07100fd7b4/2026-60.pdf — 13:37:06
- https://spk.gov.tr/data/640a1f468f95db19ec0e92a5/14-2023.pdf — 13:37:07
- https://spk.gov.tr/data/61e34f9a1b41c61270320792/Halka%20Arz.pdf — 13:38:50
- https://www.borsaistanbul.com/files/duyuru-38860-TR.pdf — 13:40:09
- https://www.borsaistanbul.com/files/duyuru-35703-TR.pdf — 13:40:13
- https://www.borsaistanbul.com/files/pay-piyasasi-pazar-yapilanmasi-2020-5-8.pdf — 13:40:15 (metin çıkarılamadı)
- https://www.borsaistanbul.com/files/borsa-istanbul-kotasyon-yonergesi.pdf — 13:40:16
- https://spk.gov.tr/data/61e224131b41c61238836057/187280f60a02f9bb407df30cb5508832.pdf — 13:40:18
- https://spk.gov.tr/data/66feee308f95db0d04afd09d/2024-50.pdf — 13:40:19
- https://spk.gov.tr/data/6425db2d8f95db1e9c11aef6/21-2023.pdf — 13:42:21
- https://spk.gov.tr/data/675211f38f95db2adc0f1d57/2024-55.pdf — 13:42:22
- https://spk.gov.tr/data/61e0b50a1b41c613a0d633e4/bd8f64f47f48f7d5c6fbed75a4bd7361.pdf (2021/57) — 13:44:05
- https://www.borsaistanbul.com/files/kotasyon_yonergesi.pdf — 13:44:06
- https://spk.gov.tr/data/67e0635d8f95db24685d2486/2025-18.pdf — 13:45:28
- https://spk.gov.tr/data/6802b3918f95db1c64570efe/2025-24.pdf — 13:45:29
- https://spk.gov.tr/data/695546ca8f95db281807a9c3/2025-68.pdf — 13:45:30
- https://www.borsaistanbul.com/files/2020-20-Daily-Price-Limits.pdf — 13:46:33
- https://www.resmigazete.gov.tr/eskiler/2025/01/20250108-5.htm — 13:46:36 (VII-128.7.g lisanslama; ilgisiz)
- https://spk.gov.tr/data/63e538958f95db0968f0b932/9-2023.pdf — 13:47:29

WebFetch ile açılanlar (≈ tur zamanı):
- https://www.borsaistanbul.com/duyuru/11645/pay-piyasasi-yeni-pazar-yapisinda-uygulanacak-degerlendirme-kriterleri-ve-islem-esaslari — ≈13:32
- https://spk.gov.tr/duyurular/basin-duyurulari/2020/borsa-istanbul-a-s-pay-piyasalarinda-aciga-satis-islemlerine-iliskin-duyuru — ≈13:32
- https://spk.gov.tr/duyurular/basin-duyurulari/2020/covid-19-salgini-nedeniye-alinan-tedbirler — ≈13:36
- https://kap.org.tr/tr/Bildirim/1542557 — ≈13:35 ve ≈13:46
- https://spk.gov.tr/spk-bultenleri/gecmis-yillara-ait-bultenler/2023-yili-spk-bultenleri (ve ?page=2) — ≈13:36, ≈13:44
- https://spk.gov.tr/spk-bultenleri/gecmis-yillara-ait-bultenler/2020-yili-spk-bultenleri — ≈13:36
- https://spk.gov.tr/spk-bultenleri/gecmis-yillara-ait-bultenler/2021-yili-spk-bultenleri — ≈13:36
- https://www.kap.org.tr/tr/Bildirim/960955 — ≈13:38
- https://www.kap.org.tr/tr/Bildirim/1566741 — ≈13:38
- https://www.borsaistanbul.com/en/markets/equity-market/market-functioning — ≈13:38, ≈13:40, ≈13:45
- https://spk.gov.tr/duyurular/basin-duyurulari/2020 — ≈13:40
- https://spk.gov.tr/duyurular/basin-duyurulari/2023 — ≈13:40
- https://www.borsaistanbul.com/en/technology-services/risk-management/circuit-breaker — ≈13:42
- https://www.borsaistanbul.com/en/markets/equity-market/markets — ≈13:42
- https://www.borsaistanbul.com/en/markets/equity-market/trading-hours — ≈13:42
- https://www.borsaistanbul.com/en/companies/public-offering-and-listing-borsa-istanbul/sales-methods — ≈13:42
- https://www.borsaistanbul.com/en/companies/public-offering-and-listing-borsa-istanbul/being-traded-without-going-public — ≈13:42
- https://www.kap.org.tr/tr/Bildirim/1113112 — ≈13:44, ≈13:45
- https://www.kap.org.tr/tr/Bildirim/1138804 — ≈13:44
- https://www.kap.org.tr/tr/Bildirim/978872 — ≈13:44
- https://borsaistanbul.com/en/announcement/15193/... — ≈13:47 (içerik yok)

Açılamayan / 404 (denendi):
- borsaistanbul.com/tr/duyuru/5892, /tr/duyuru/3029, /tr/duyuru/2850, /tr/duyuru/3157, /tr/duyuru/3097, /tr/sayfa/464, /tr/sayfa/234, /tr/sayfa/244, /tr/sayfa/332, /tr/sayfa/441, /tr/sayfa/493, /tr/sayfa/334, /en/sayfa/2372 — socket hang up / empty reply (13:33–13:47)
- borsaistanbul.com/files/duyuru-{15151,19412,20030,14260,14904,7515,15948}-TR.pdf, kotasyon-yonergesi.pdf, 2020-20-Gunluk-Fiyat-Limitleri.pdf, 2020-21-*.pdf — 404
- spk.gov.tr/Duyuru/Goster/20200630/1 ve .../aciga-satis-islemlerine-iliskin-alinan-kurul-karari-duzenlemesi — 404
- Claude tarayıcı paneli: borsaistanbul.com navigasyonu reddedildi (2 deneme).

WebSearch sorguları (tümü allowed_domains ile borsaistanbul.com / spk.gov.tr / kap.org.tr / resmigazete.gov.tr'ye sınırlı; ≈13:31–13:47): fiyat marjı/adımı, 5892, 14113, deprem 2023, Pay Tebliği değişiklikleri, pazar yapısı, ilk gün tedbirleri, veri formatları, i-SPK.128.20/21/23, açığa satış 2020/2023/2025, KAP şablonları, kotasyon eşikleri, 2020/20-21, 15151, 38860, 2020/58, 2020/62, SPK bülten 2023/21, 8-2023/9-2023, VBTS, VII-128.1.f, II-5.2.b.

# TASK_ID: BORSAI_FAZ6_CODEX_INPUTS_B4_20260924

AYAR: Codex + GPT-6 Astra · repo DIŞINDA · ağ açık · oturum hafızası kapalı. Çalışma klasörü: `~/Desktop/BorsAi_codex/` (yoksa oluştur). Zaman sınırı: 4 saat; bitmeyen arzlar `status: "PARTIAL"` ile teslim edilir.

## Ne istiyoruz
Borsa İstanbul'da **2023 (2023-09-21'e kadar)** döneminde halka arz edilen **37 şirket** için, **yalnız listeleme öncesi yayımlanmış resmi belgelerden**, aşağıdaki alanları çıkar. Her değer için resmi kaynak URL'si, KAP yayın zamanı, erişim zamanı ve belgeden birebir alıntı ver. Bulamadığını uydurma: `"BULUNAMADI"` yaz ve nerelere baktığını listele.

Bu veriler, dondurulmuş tahmin modellerini bu eski arzlarda **sonuçlarına bakmadan** test etmek için kullanılacak. Bu yüzden aşağıdaki körlük kuralı her şeyden önce gelir.

## SONUÇ KÖRLÜĞÜ (kesin kural)
- Bu şirketlerin **ilk işlem gününden sonraki hiçbir fiyat, getiri, tavan, taban, hacim ya da performans bilgisine bakma, yazma, özetleme.**
- Açma: haber siteleri, forumlar, sosyal medya, aracı kurum bültenleri ve performans raporları, investing.com / tradingview / isyatirim fiyat sayfaları, "halka arz performansı", "kaç tavan yaptı", "en çok kazandıran" türü her sayfa. Arama sonuçlarında böyle bir bilgi istemeden görürsen `exposure_log`'a yaz (ne, nerede); değerini yazma.
- İzinli kaynaklar (resmi): **KAP** (kap.org.tr bildirim sayfaları, `api/BildirimPdf/<id>` PDF'leri ve ekleri), **SPK** (spk.gov.tr haftalık bültenleri, onaylı izahname ve tasarruf sahiplerine satış duyurusu), **Borsa İstanbul** duyuruları (yalnız listeleme öncesi). Şirket ya da aracı kurum sitesindeki izahname/TSSD kopyası yalnız KAP'ta bulunamazsa, `secondary: true` etiketiyle.
- SPK'nın yıllık "Payların İlk Halka Arzı" Excel tabloları sonradan derlenmiştir: değer kaynağı OLARAK KULLANILMAZ, yalnız `cross_check` alanına yazılabilir.
- Belgenin KAP yayın zamanı, şirketin ilk işlem gününden (İstanbul saati) **önce** olmalı. Değer yalnız sonraki bir belgede varsa `status: "YALNIZ_LISTELEME_SONRASI"` yaz, değeri verme.

## Nereye bakılır (ipucu)
1. KAP'ta şirketin "Halka Arz Sonuçları" / "Talep Toplama Sonuçları" bildirimi (aracı kurum ya da şirket gönderir; talep toplamadan 1–4 gün sonra, ilk işlemden önce). Kesin fiyat, satılan pay, ek satış, talep katı, katılımcı sayısı ve dağıtım tablosu buradadır (2020–2021'de serbest metin + PDF ek).
2. SPK haftalık bülteni "A.1 İlk Halka Arzlar" tablosu (izahname onay haftası): planlanan yapı (sermaye öncesi/sonrası, bedelli, ortak satışı, ek satış, fiyat).
3. İzahname ve Tasarruf Sahiplerine Satış Duyurusu (TSSD): fiyat istikrarı, satmama taahhüdü, satış yöntemi, lider aracı kurum, tahsisat oranları, sektör.
4. Borsa İstanbul'un "Payların İşlem Görmeye Başlaması" bildirimi (tabloda linki var): baz fiyat, ilk işlem tarihi, pazar, arz sonrası sermaye.
- KAP API'si hızlı istekte 429 döndürür: istekler arasında 3–4 saniye bekle, 429'da geri çekil.

## Alanlar (her arz için)
Değerleri belgede yazdığı gibi (metin) ver; birim yaz; hesaplanmış değer ise `derived: true` ve formülü `note`'a yaz.

**A. Kesin yapı (sonuç bildirimi)**
- `ipo_price_tl`: kesin halka arz fiyatı (TL/pay)
- `shares_offered`: satılan toplam pay (nominal TL; ek satış DAHİL) ve `includes_additional_sale` (true/false)
- `additional_sale_shares`: kullanılan ek satış (nominal); yoksa "0"
- `capital_increase_shares`: sermaye artırımıyla satılan pay (nominal)
- `existing_share_sale_shares`: ortak satışıyla satılan pay (nominal)
- `post_ipo_share_capital`: halka arz sonrası çıkarılmış sermaye (TL)
- `ipo_size_tl`: belgede yazılıysa toplam satış tutarı (TL); yoksa "BULUNAMADI" (hesaplama)
- `total_demand_multiple`: toplam talep / satılan pay (kat). `origin` ∈ {`SOURCE_REPORTED`, `SOURCE_REPORTED_APPROX` ("yaklaşık"), `COMPUTED_FROM_NOMINALS` (talep nominal / arz nominal; ikisi de belgede), `NOT_FOUND`}; `definition`: belgede talebin nasıl tanımlandığı (birebir); `filter_status` ∈ {`UNFILTERED`, `FILTERED`, `NOT_SPECIFIED`}
- `retail_demand_multiple`, `domestic_institutional_demand_multiple`, `foreign_institutional_demand_multiple`: grup başına talep katı (belgede varsa)
- `investor_count`: toplam katılımcı (kişi/başvuru) sayısı; ayrıca `investor_count_by_group` (grup → sayı)
- `distributed_by_group`: grup → dağıtılan nominal; `retail_allocation_pct`, `domestic_institutional_allocation_pct`, `foreign_institutional_allocation_pct` (yüzde)
- `distribution_method`: dağıtım yöntemi metni (ör. "eşit dağıtım", "oransal", "borsada satış")
- `bookbuilding_start`, `bookbuilding_end` (YYYY-MM-DD)

**B. Planlanan yapı (talep toplamadan ÖNCE yayımlanmış: SPK bülteni A.1, izahname ya da TSSD)**
- `ipo_price_try`: planlanan fiyat; aralıksa `"ALT-ÜST"` biçiminde ve `price_is_range: true`
- `planned_pre_ipo_capital`, `planned_post_ipo_capital`, `planned_capital_increase_shares`, `planned_existing_share_sale`, `planned_additional_sale_ceiling`, `planned_base_offer_shares`, `planned_max_offer_shares` (nominal TL)
- `planned_source_published_at`: bu belgenin yayın zamanı (talep toplama başlangıcından önce olmalı)

**C. Diğer listeleme öncesi özellikler (izahname / TSSD)**
- `price_stability_planned` (true/false), `price_stability_days`
- `issuer_lockup_days`, `shareholder_lockup_days` (satmama taahhüdü; kapsamı `note`'a)
- `lead_broker` (konsorsiyum lideri/lideri); `sale_method` (borsada satış / talep toplama / diğer)
- `sector` (izahnamedeki faaliyet alanı, kısa)
- `participation_index_eligible`: izahname ya da TSSD'de katılım endeksi / faizsiz finans uyumu beyanı varsa (true/false + alıntı); yoksa "BULUNAMADI"
- `market`: pazar (Yıldız / Ana / Alt) — listeleme bildiriminden

## Her değer için kayıt biçimi
```json
{"value": "12,25", "unit": "TL/pay", "status": "OK | BULUNAMADI | YALNIZ_LISTELEME_SONRASI | PARTIAL",
 "source_url": "https://www.kap.org.tr/tr/Bildirim/…", "source_type": "KAP_SONUC | KAP_BIST_LISTELEME | SPK_BULTEN | IZAHNAME | TSSD | DIGER",
 "kap_notice_id": "…", "published_at": "YYYY-MM-DDTHH:MM:SS+03:00", "accessed_at_utc": "YYYY-MM-DDTHH:MM:SSZ",
 "page": 3, "quote": "belgeden birebir, en çok 200 karakter", "derived": false, "secondary": false, "note": ""}
```

## Teslim
Tek dosya: `~/Desktop/BorsAi_codex/BORSAI_FAZ6_CODEX_INPUTS_B4_20260924.json`
```json
{"task_id": "BORSAI_FAZ6_CODEX_INPUTS_B4_20260924", "generated_at_utc": "…", "model": "…",
 "ipos": [ {"ticker": "…", "company": "…", "first_trading_date": "YYYY-MM-DD", "status": "OK | PARTIAL",
            "fields": {"<alan>": { …kayıt… }},
            "documents": [ {"url": "…", "type": "…", "kap_notice_id": "…", "published_at": "…", "accessed_at_utc": "…", "title": "…"} ],
            "issues": ["…"] } ],
 "exposure_log": [ {"what": "…", "where": "…", "when_utc": "…"} ],
 "summary": {"n_ipos": 0, "n_ok": 0, "n_partial": 0, "fields_not_found": {"<alan>": 0}}}
```
Kurallar: her iddia için URL ve erişim zamanı; bulunamayana "BULUNAMADI"; tahmin, ortalama, ilişki analizi YOK; listeleme sonrası sonuç bilgisi YOK.

## Arzlar (37)
Kaynak: KAP "Payların İşlem Görmeye Başlaması" bildirimleri (Borsa İstanbul). Satış yöntemi: `ON_EXCHANGE` = Borsa'da satış, diğerleri borsa dışı talep toplama.

| # | ticker | şirket | ilk işlem | satış yöntemi (KAP) | talep toplama | SPK onay | BIST listeleme bildirimi |
|---|---|---|---|---|---|---|---|
| 1 | ONCSM | Oncosem Onkolojik Sistemler Sanayi ve Ticaret A.Ş. | 2023-01-04 | OFF_EXCHANGE_BOOKBUILD | 28-29/12/2022 | 2022-12-15 | https://www.kap.org.tr/tr/Bildirim/1092294 |
| 2 | SDTTR | SDT Uzay ve Savunma Teknolojileri A.Ş. | 2023-01-04 | OFF_EXCHANGE_BOOKBUILD | 28-29/12/2022 | 2022-12-22 | https://www.kap.org.tr/tr/Bildirim/1092297 |
| 3 | TNZTP | Tapdi Oksijen Özel Sağlık ve Eğitim Hizmetleri Sanayi Ticaret A.Ş. | 2023-01-11 | ON_EXCHANGE | 05-06/01/2023 | 2022-12-29 | https://www.kap.org.tr/tr/Bildirim/1098377 |
| 4 | SOKE | Söke Değirmencilik Sanayi ve Ticaret A.Ş. | 2023-01-12 | OFF_EXCHANGE_BOOKBUILD | 04-05-06/01/2023 | 2022-12-22 | https://www.kap.org.tr/tr/Bildirim/1098380 |
| 5 | ASTOR | Astor Enerji A.Ş. | 2023-01-18 | OFF_EXCHANGE_BOOKBUILD | 11-13/01/2023 | 2022-12-22 | https://www.kap.org.tr/tr/Bildirim/1102649 |
| 6 | MACKO | Mackolik İnternet Hizmetleri Ticaret A.Ş. | 2023-01-26 | OFF_EXCHANGE_BOOKBUILD | 19-20/01/2023 | 2022-12-29 | https://www.kap.org.tr/tr/Bildirim/1104287 |
| 7 | BVSAN | Bülbüloğlu Vinç Sanayi ve Ticaret A.Ş. | 2023-02-06 | OFF_EXCHANGE_BOOKBUILD | 26-30/01/2023 | 2023-01-19 | https://www.kap.org.tr/tr/Bildirim/1109196 |
| 8 | GOKNR | Göknur Gıda Maddeleri Enerji İmalat İthalat İhracat Ticaret ve Sanayi A.Ş. | 2023-03-09 | OFF_EXCHANGE_BOOKBUILD | 1-3/03/2023 | 2023-02-02 | https://www.kap.org.tr/tr/Bildirim/1120552 |
| 9 | AKFYE | Akfen Yenilenebilir Enerji A.Ş. | 2023-03-16 | OFF_EXCHANGE_BOOKBUILD | 8-10/03/2023 | 2023-03-02 | https://www.kap.org.tr/tr/Bildirim/1124554 |
| 10 | EKSUN | Eksun Gıda Tarım Sanayi ve Ticaret A.Ş. | 2023-03-24 | OFF_EXCHANGE_BOOKBUILD | 15-17/03/2023 | 2023-03-09 | https://www.kap.org.tr/tr/Bildirim/1127128 |
| 11 | CVKMD | CVK MADEN İŞLETMELERİ SANAYİ VE TİCARET A.Ş. | 2023-04-13 | OFF_EXCHANGE_BOOKBUILD | 06-07/04/2023 | 2023-03-30 | https://www.kap.org.tr/tr/Bildirim/1136533 |
| 12 | KOPOL | Koza Polyester Sanayi ve Ticaret A.Ş. | 2023-04-13 | OFF_EXCHANGE_BOOKBUILD | 05-07/04/2023 | 2023-03-30 | https://www.kap.org.tr/tr/Bildirim/1136531 |
| 13 | EUPWR | Europower Enerji ve Otomasyon Teknolojileri Sanayi Ticaret A.Ş. | 2023-04-20 | OFF_EXCHANGE_BOOKBUILD | 12-14/04/2023 | 2023-04-06 | https://www.kap.org.tr/tr/Bildirim/1139805 |
| 14 | GRTRK | Graınturk Tarım A.Ş. | 2023-04-26 | ON_EXCHANGE | 18-19/04/2023 | 2023-04-13 | https://www.kap.org.tr/tr/Bildirim/1140527 |
| 15 | CWENE | CW Enerji Mühendislik Ticaret ve Sanayi A.Ş. | 2023-05-05 | OFF_EXCHANGE_BOOKBUILD | 26-27-28/04/2023 | 2023-04-13 | https://www.kap.org.tr/tr/Bildirim/1144878 |
| 16 | BIGCH | Büyük Şefler Gıda Turizm Tekstil Danışmanlık Organizasyon Eğitim Sanayi ve Ticaret A.Ş. | 2023-05-10 | OFF_EXCHANGE_BOOKBUILD | 03-05/05/2023 | 2023-04-27 | https://www.kap.org.tr/tr/Bildirim/1148193 |
| 17 | BIENY | Bien Yapı Ürünleri Sanayi Turizm ve Ticaret A.Ş. | 2023-05-18 | OFF_EXCHANGE_BOOKBUILD | 11-12/05/2023 | 2023-05-05 | https://www.kap.org.tr/tr/Bildirim/1151760 |
| 18 | KAYSE | Kayseri Şeker Fabrikası A.Ş. | 2023-05-18 | OFF_EXCHANGE_BOOKBUILD | 10-11-12/05/2023 | 2023-05-05 | https://www.kap.org.tr/tr/Bildirim/1151757 |
| 19 | KTLEV | Katılımevim Tasarruf Finansman A.Ş. | 2023-06-12 | ON_EXCHANGE | 6-7/06/2023 | 2023-06-01 | https://www.kap.org.tr/tr/Bildirim/1157361 |
| 20 | FORTE | Forte Bilgi İletişim Teknolojileri ve Savunma Sanayi A.Ş. | 2023-06-14 | ON_EXCHANGE | 08-09/06/2023 | 2023-06-01 | https://www.kap.org.tr/tr/Bildirim/1158081 |
| 21 | PASEU | Pasifik Eurasia Lojistik Dış Ticaret A.Ş. | 2023-06-14 | OFF_EXCHANGE_BOOKBUILD | 6-7/06/2023 | 2023-06-01 | https://www.kap.org.tr/tr/Bildirim/1157808 |
| 22 | A1CAP | A1 Capital Yatırım Menkul Değerler A.Ş. | 2023-06-15 | OFF_EXCHANGE_BOOKBUILD | 07-09/06/2023 | 2023-06-01 | https://www.kap.org.tr/tr/Bildirim/1158082 |
| 23 | ATAKP | Atakey Patates Gıda Sanayi ve Ticaret A.Ş. | 2023-07-27 | OFF_EXCHANGE_BOOKBUILD | 19-21/07/2023 | 2023-07-13 | https://www.kap.org.tr/tr/Bildirim/1174704 |
| 24 | KLSER | Kaleseramik, Çanakkale Kalebodur Seramik Sanayi A.Ş. | 2023-07-27 | OFF_EXCHANGE_BOOKBUILD | 19-21/07/2023 | 2023-07-13 | https://www.kap.org.tr/tr/Bildirim/1174705 |
| 25 | FZLGY | Fuzul Gayrimenkul Yatırım Ortaklığı A.Ş. | 2023-07-28 | OFF_EXCHANGE_BOOKBUILD | 20-21/07/2023 | 2023-07-13 | https://www.kap.org.tr/tr/Bildirim/1175085 |
| 26 | ASGYO | ASCE Gayrimenkul Yatırım Ortaklığı A.Ş. | 2023-08-03 | OFF_EXCHANGE_BOOKBUILD | 27-28/07/2023 | 2023-07-20 | https://www.kap.org.tr/tr/Bildirim/1177591 |
| 27 | IZENR | İzdemir Enerji Elektrik Üretim A.Ş. | 2023-08-16 | OFF_EXCHANGE_BOOKBUILD | 08-10/08/2023 | 2023-08-03 | https://www.kap.org.tr/tr/Bildirim/1184602 |
| 28 | OFSYM | Ofis Yem Gıda Sanayi Ticaret A.Ş. | 2023-08-16 | ON_EXCHANGE | 10-11/08/2023 | 2023-08-03 | https://www.kap.org.tr/tr/Bildirim/1185338 |
| 29 | TATEN | Tatlıpınar Enerji Üretim A.Ş. | 2023-08-17 | OFF_EXCHANGE_BOOKBUILD | 10-11/08/2023 | 2023-08-03 | https://www.kap.org.tr/tr/Bildirim/1185339 |
| 30 | BYDNR | Baydöner Restoranları A.Ş. | 2023-08-21 | ON_EXCHANGE | 15-16/08/2023 | 2023-08-09 | https://www.kap.org.tr/tr/Bildirim/1186515 |
| 31 | ENERY | Enerya Enerji A.Ş. | 2023-08-23 | OFF_EXCHANGE_BOOKBUILD | 14-15-16/08/2023 | 2023-08-09 | https://www.kap.org.tr/tr/Bildirim/1187228 |
| 32 | KZGYO | Kuzugrup Gayrimenkul Yatırım Ortaklığı A.Ş. | 2023-08-29 | OFF_EXCHANGE_BOOKBUILD | 21-23/08/2023 | 2023-08-16 | https://www.kap.org.tr/tr/Bildirim/1189723 |
| 33 | EBEBK | Ebebek Mağazacılık A.Ş. | 2023-09-07 | OFF_EXCHANGE_BOOKBUILD | 29/08-01/09/2023 | 2023-08-24 | https://www.kap.org.tr/tr/Bildirim/1191428 |
| 34 | TARKM | Tarkim Bitki Koruma Sanayi ve Ticaret A.Ş. | 2023-09-12 | ON_EXCHANGE | 05-06/09/2023 | 2023-08-31 | https://www.kap.org.tr/tr/Bildirim/1192776 |
| 35 | GIPTA | Gıpta Ofis Kırtasiye ve Promosyon Ürünleri İmalat Sanayi A.Ş. | 2023-09-14 | OFF_EXCHANGE_BOOKBUILD | 06-07-08/09/2023 | 2023-08-31 | https://www.kap.org.tr/tr/Bildirim/1193926 |
| 36 | ADGYO | Adra Gayrimenkul Yatırım Ortaklığı A.Ş. | 2023-09-20 | ON_EXCHANGE | 14-15/09/2023 | 2023-09-07 | https://www.kap.org.tr/tr/Bildirim/1196007 |
| 37 | REEDR | Reeder Teknoloji Sanayi ve Ticaret A.Ş. | 2023-09-21 | OFF_EXCHANGE_BOOKBUILD | 13-15/09/2023 | 2023-09-07 | https://www.kap.org.tr/tr/Bildirim/1195976 |

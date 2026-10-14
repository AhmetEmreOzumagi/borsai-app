# TASK_ID: BORSAI_FAZ6_CODEX_INPUTS_B3_20260924

AYAR: Codex + GPT-6 Astra · repo DIŞINDA · ağ açık · oturum hafızası kapalı. Çalışma klasörü: `~/Desktop/BorsAi_codex/` (yoksa oluştur). Zaman sınırı: 4 saat; bitmeyen arzlar `status: "PARTIAL"` ile teslim edilir.

## Ne istiyoruz
Borsa İstanbul'da **2022** döneminde halka arz edilen **38 şirket** için, **yalnız listeleme öncesi yayımlanmış resmi belgelerden**, aşağıdaki alanları çıkar. Her değer için resmi kaynak URL'si, KAP yayın zamanı, erişim zamanı ve belgeden birebir alıntı ver. Bulamadığını uydurma: `"BULUNAMADI"` yaz ve nerelere baktığını listele.

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
Tek dosya: `~/Desktop/BorsAi_codex/BORSAI_FAZ6_CODEX_INPUTS_B3_20260924.json`
```json
{"task_id": "BORSAI_FAZ6_CODEX_INPUTS_B3_20260924", "generated_at_utc": "…", "model": "…",
 "ipos": [ {"ticker": "…", "company": "…", "first_trading_date": "YYYY-MM-DD", "status": "OK | PARTIAL",
            "fields": {"<alan>": { …kayıt… }},
            "documents": [ {"url": "…", "type": "…", "kap_notice_id": "…", "published_at": "…", "accessed_at_utc": "…", "title": "…"} ],
            "issues": ["…"] } ],
 "exposure_log": [ {"what": "…", "where": "…", "when_utc": "…"} ],
 "summary": {"n_ipos": 0, "n_ok": 0, "n_partial": 0, "fields_not_found": {"<alan>": 0}}}
```
Kurallar: her iddia için URL ve erişim zamanı; bulunamayana "BULUNAMADI"; tahmin, ortalama, ilişki analizi YOK; listeleme sonrası sonuç bilgisi YOK.

## Arzlar (38)
Kaynak: KAP "Payların İşlem Görmeye Başlaması" bildirimleri (Borsa İstanbul). Satış yöntemi: `ON_EXCHANGE` = Borsa'da satış, diğerleri borsa dışı talep toplama.

| # | ticker | şirket | ilk işlem | satış yöntemi (KAP) | talep toplama | SPK onay | BIST listeleme bildirimi |
|---|---|---|---|---|---|---|---|
| 1 | PNLSN | Panelsan Çatı Cephe Sistemleri Sanayi ve Ticaret A.Ş. | 2022-02-18 | OFF_EXCHANGE_BOOKBUILD | 9-11/02/2022 | 2022-01-27 | https://www.kap.org.tr/tr/Bildirim/1001895 |
| 2 | HUNER | Hun Yenilenebilir Enerji Üretim A.Ş. | 2022-02-21 | ON_EXCHANGE | 15-16/02/2022 | 2022-02-10 | https://www.kap.org.tr/tr/Bildirim/1002467 |
| 3 | DAPGM | DAP GAYRİMENKUL GELİŞTİRME A.Ş. | 2022-02-24 | OFF_EXCHANGE_BOOKBUILD | 15-18/02/2022 | 2022-02-10 | https://www.kap.org.tr/tr/Bildirim/1003254 |
| 4 | INVES | Investco Holding A.Ş. | 2022-03-01 | ON_EXCHANGE | 22-23/02/2022 |  | https://www.kap.org.tr/tr/Bildirim/1004618 |
| 5 | HTTBT | Hitit Bilgisayar Hizmetleri A.Ş. | 2022-03-03 | OFF_EXCHANGE_BOOKBUILD | 23-25/02/2022 | 2022-02-17 | https://www.kap.org.tr/tr/Bildirim/1005149 |
| 6 | KLSYN | Koleksiyon Mobilya Sanayi A.Ş. | 2022-03-04 | OFF_EXCHANGE_BOOKBUILD | 24-25/02/2022 | 2022-02-17 | https://www.kap.org.tr/tr/Bildirim/1005287 |
| 7 | GZNMI | Gezinomi Seyahat Turizm Ticaret A.Ş. | 2022-03-08 | OFF_EXCHANGE_BOOKBUILD | 01-02/03/2022 | 2022-02-24 | https://www.kap.org.tr/tr/Bildirim/1006991 |
| 8 | GRSEL | Gür-Sel Turizm Taşımacılık ve Servis Ticaret A.Ş. | 2022-03-09 | ON_EXCHANGE | 03-04/03/2022 | 2022-02-24 | https://www.kap.org.tr/tr/Bildirim/1007910 |
| 9 | ENSRI | Ensari Deri Gıda Sanayi ve Ticaret A.Ş. | 2022-03-22 | ON_EXCHANGE | 16-17/03/2022 | 2022-03-10 | https://www.kap.org.tr/tr/Bildirim/1011427 |
| 10 | SMRTG | Smart Güneş Enerjisi Teknolojileri Araştırma Geliştirme Üretim Sanayi ve Ticaret A.Ş. | 2022-03-24 | OFF_EXCHANGE_BOOKBUILD | 16-17-18/03/2022 | 2022-03-10 | https://www.kap.org.tr/tr/Bildirim/1012058 |
| 11 | LIDER | LDR Turizm A.Ş. | 2022-04-04 | ON_EXCHANGE | 29-30/03/2022 | 2022-03-24 | https://www.kap.org.tr/tr/Bildirim/1014682 |
| 12 | CONSE | Consus Enerji İşletmeciliği ve Hizmetleri A.Ş. | 2022-04-20 | ON_EXCHANGE | 14-15/04/2022 | 2022-04-07 | https://www.kap.org.tr/tr/Bildirim/1021541 |
| 13 | SUWEN | Suwen Tekstil Sanayi Pazarlama A.Ş. | 2022-04-21 | OFF_EXCHANGE_BOOKBUILD | 13-15/04/2022 | 2022-04-07 | https://www.kap.org.tr/tr/Bildirim/1021543 |
| 14 | BMSTL | BMS Birleşik Metal Sanayi ve Ticaret A.Ş. | 2022-04-27 | ON_EXCHANGE | 21-22/04/2022 | 2022-04-14 | https://www.kap.org.tr/tr/Bildirim/1023551 |
| 15 | KMPUR | Kimteks Poliüretan Sanayi ve Ticaret A.Ş. | 2022-04-28 | OFF_EXCHANGE_BOOKBUILD | 20-22/04/2022 | 2022-04-14 | https://www.kap.org.tr/tr/Bildirim/1024003 |
| 16 | IMASM | İmaş Makina Sanayi A.Ş. | 2022-04-29 | OFF_EXCHANGE_BOOKBUILD | 20-22/04/2022 | 2022-04-14 | https://www.kap.org.tr/tr/Bildirim/1024015 |
| 17 | SUNTK | Sun Tekstil Sanayi ve Ticaret A.Ş. | 2022-05-20 | OFF_EXCHANGE_BOOKBUILD | 11-13/05/2022 | 2022-04-28 | https://www.kap.org.tr/tr/Bildirim/1030619 |
| 18 | YYLGD | Yayla Agro Gıda Sanayi ve Ticaret A.Ş. | 2022-05-20 | OFF_EXCHANGE_BOOKBUILD | 11-12-13/05/2022 | 2022-04-22 | https://www.kap.org.tr/tr/Bildirim/1030618 |
| 19 | SEGYO | Şeker Gayrimenkul Yatırım Ortaklığı A.Ş. | 2022-06-07 | ON_EXCHANGE | 01-02/06/2022 | 2022-05-26 | https://www.kap.org.tr/tr/Bildirim/1034640 |
| 20 | EUREN | Europen Endüstri İnşaat Sanayi ve Ticaret A.Ş. | 2022-06-08 | ON_EXCHANGE | 02-03/06/2022 | 2022-05-26 | https://www.kap.org.tr/tr/Bildirim/1034974 |
| 21 | PRDGS | Pardus Girişim Sermayesi Yatırım Ortaklığı A.Ş. | 2022-06-15 | ON_EXCHANGE | 09-10/06/2022 | 2022-06-02 | https://www.kap.org.tr/tr/Bildirim/1036999 |
| 22 | MAKIM | Makim Makina Teknolojileri Sanayi ve Ticaret A.Ş. | 2022-06-17 | OFF_EXCHANGE_BOOKBUILD | 09-10/06/2022 | 2022-06-02 | https://www.kap.org.tr/tr/Bildirim/1037272 |
| 23 | KCAER | Kocaer Çelik Sanayi ve Ticaret A.Ş. | 2022-06-30 | OFF_EXCHANGE_BOOKBUILD | 22-24/06/2022 | 2022-06-16 | https://www.kap.org.tr/tr/Bildirim/1039804 |
| 24 | RUBNS | Rubenis Tekstil Sanayi Ticaret A.Ş. | 2022-07-06 | OFF_EXCHANGE_BOOKBUILD | 29-30/06/2022 | 2022-06-23 | https://www.kap.org.tr/tr/Bildirim/1040771 |
| 25 | KLRHO | Kiler Holding A.Ş. | 2022-07-07 | OFF_EXCHANGE_BOOKBUILD | 30/06/2022-01/07/2022 | 2022-06-23 | https://www.kap.org.tr/tr/Bildirim/1041306 |
| 26 | KRPLS | Koroplast Temizlik Ambalaj Ürünleri Sanayi ve Dış Ticaret A.Ş. | 2022-07-28 | OFF_EXCHANGE_BOOKBUILD | 20-22/07/2022 | 2022-06-30 | https://www.kap.org.tr/tr/Bildirim/1047823 |
| 27 | OBASE | Obase Bilgisayar ve Danışmanlık Hizmetleri Ticaret A.Ş. | 2022-08-03 | ON_EXCHANGE | 28-29/07/2022 | 2022-07-21 | https://www.kap.org.tr/tr/Bildirim/1050472 |
| 28 | BARMA | Barem Ambalaj Sanayi ve Ticaret A.Ş. | 2022-08-10 | ON_EXCHANGE | 03-04/08/2022 | 2022-07-28 | https://www.kap.org.tr/tr/Bildirim/1052471 |
| 29 | AZTEK | Aztek Teknoloji Ürünleri Ticaret A.Ş. | 2022-08-17 | OFF_EXCHANGE_BOOKBUILD | 10-12/08/2022 | 2022-08-04 | https://www.kap.org.tr/tr/Bildirim/1055553 |
| 30 | HKTM | Hidropar Hareket Kontrol Teknolojileri Merkezi Sanayi ve Ticaret A.Ş. | 2022-08-18 | OFF_EXCHANGE_BOOKBUILD | 10-12/08/2022 | 2022-08-04 | https://www.kap.org.tr/tr/Bildirim/1055556 |
| 31 | ALFAS | Alfa Solar Enerji Sanayi ve Ticaret A.Ş. | 2022-11-16 | OFF_EXCHANGE_BOOKBUILD | 09-11/11/2022 | 2022-11-03 | https://www.kap.org.tr/tr/Bildirim/1079840 |
| 32 | SNICA | Sanica Isı Sanayi A.Ş. | 2022-11-24 | OFF_EXCHANGE_BOOKBUILD | 15-18/11/2022 | 2022-11-11 | https://www.kap.org.tr/tr/Bildirim/1081456 |
| 33 | OZSUB | Özsu Balık Üretim A.Ş. | 2022-11-29 | ON_EXCHANGE | 22-23/11/2022 | 2022-11-11 | https://www.kap.org.tr/tr/Bildirim/1082359 |
| 34 | PLTUR | Platform Turizm Taşımacılık Gıda İnşaat Temizlik Hizmetleri Sanayi ve Ticaret A.Ş. | 2022-12-14 | ON_EXCHANGE | 08-09/12/2022 | 2022-12-02 | https://www.kap.org.tr/tr/Bildirim/1086666 |
| 35 | BRKVY | Birikim Varlık Yönetim A.Ş. | 2022-12-15 | OFF_EXCHANGE_BOOKBUILD | 08-09/12/2022 | 2022-12-02 | https://www.kap.org.tr/tr/Bildirim/1086669 |
| 36 | AHGAZ | Ahlatcı Doğal Gaz Dağıtım Enerji ve Yatırım A.Ş. | 2022-12-22 | OFF_EXCHANGE_BOOKBUILD | 14-15-16/12/2022 | 2022-12-09 | https://www.kap.org.tr/tr/Bildirim/1088538 |
| 37 | TERA | Tera Yatırım Menkul Değerler A.Ş. | 2022-12-22 | OFF_EXCHANGE_BOOKBUILD | 15-16/12/2022 | 2022-12-09 | https://www.kap.org.tr/tr/Bildirim/1088529 |
| 38 | EYGYO | EYG Gayrimenkul Yatırım Ortaklığı A.Ş. | 2022-12-29 | ON_EXCHANGE | 22-23/12/2022 | 2022-12-15 | https://www.kap.org.tr/tr/Bildirim/1090293 |

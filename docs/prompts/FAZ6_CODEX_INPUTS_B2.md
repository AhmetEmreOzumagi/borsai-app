# TASK_ID: BORSAI_FAZ6_CODEX_INPUTS_B2_20260924

AYAR: Codex + GPT-6 Astra · repo DIŞINDA · ağ açık · oturum hafızası kapalı. Çalışma klasörü: `~/Desktop/BorsAi_codex/` (yoksa oluştur). Zaman sınırı: 4 saat; bitmeyen arzlar `status: "PARTIAL"` ile teslim edilir.

## Ne istiyoruz
Borsa İstanbul'da **2021 ikinci yarı** döneminde halka arz edilen **26 şirket** için, **yalnız listeleme öncesi yayımlanmış resmi belgelerden**, aşağıdaki alanları çıkar. Her değer için resmi kaynak URL'si, KAP yayın zamanı, erişim zamanı ve belgeden birebir alıntı ver. Bulamadığını uydurma: `"BULUNAMADI"` yaz ve nerelere baktığını listele.

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
Tek dosya: `~/Desktop/BorsAi_codex/BORSAI_FAZ6_CODEX_INPUTS_B2_20260924.json`
```json
{"task_id": "BORSAI_FAZ6_CODEX_INPUTS_B2_20260924", "generated_at_utc": "…", "model": "…",
 "ipos": [ {"ticker": "…", "company": "…", "first_trading_date": "YYYY-MM-DD", "status": "OK | PARTIAL",
            "fields": {"<alan>": { …kayıt… }},
            "documents": [ {"url": "…", "type": "…", "kap_notice_id": "…", "published_at": "…", "accessed_at_utc": "…", "title": "…"} ],
            "issues": ["…"] } ],
 "exposure_log": [ {"what": "…", "where": "…", "when_utc": "…"} ],
 "summary": {"n_ipos": 0, "n_ok": 0, "n_partial": 0, "fields_not_found": {"<alan>": 0}}}
```
Kurallar: her iddia için URL ve erişim zamanı; bulunamayana "BULUNAMADI"; tahmin, ortalama, ilişki analizi YOK; listeleme sonrası sonuç bilgisi YOK.

## Arzlar (26)
Kaynak: KAP "Payların İşlem Görmeye Başlaması" bildirimleri (Borsa İstanbul). Satış yöntemi: `ON_EXCHANGE` = Borsa'da satış, diğerleri borsa dışı talep toplama.

| # | ticker | şirket | ilk işlem | satış yöntemi (KAP) | talep toplama | SPK onay | BIST listeleme bildirimi |
|---|---|---|---|---|---|---|---|
| 1 | KARYE | Kartal Yenilenebilir Enerji Üretim A.Ş. | 2021-07-16 | ON_EXCHANGE | 09-12/07/2021 | 2021-07-01 | https://www.kap.org.tr/tr/Bildirim/950856 |
| 2 | MANAS | Manas Enerji Yönetimi Sanayi ve Ticaret A.Ş. | 2021-07-27 | ON_EXCHANGE | 13-14/07/2021 | 2021-07-01 | https://www.kap.org.tr/tr/Bildirim/951548 |
| 3 | GENIL | Gen İlaç ve Sağlık Ürünleri Sanayi ve Ticaret A.Ş. | 2021-08-05 | OFF_EXCHANGE_BOOKBUILD | 28-30/07/2021 | 2021-07-08 | https://www.kap.org.tr/tr/Bildirim/954206 |
| 4 | KZBGY | Kızılbük Gayrimenkul Yatırım Ortaklığı A.Ş. | 2021-08-12 | OFF_EXCHANGE_BOOKBUILD | 04-06/08/2021 | 2021-07-14 | https://www.kap.org.tr/tr/Bildirim/957001 |
| 5 | GESAN | Girişim Elektrik Sanayi Taahhüt ve Ticaret A.Ş. | 2021-08-19 | OFF_EXCHANGE_BOOKBUILD | 11-12-13/08/2021 | 2021-07-29 | https://www.kap.org.tr/tr/Bildirim/958338 |
| 6 | BRLSM | Birleşim Mühendislik Isıtma Soğutma Havalandırma Sanayi ve Ticaret A.Ş. | 2021-08-20 | OFF_EXCHANGE_BOOKBUILD | 11-12-13/08/2021 | 2021-08-05 | https://www.kap.org.tr/tr/Bildirim/958344 |
| 7 | EGEPO | Nasmed Özel Sağlık Hizmetleri Ticaret A.Ş. | 2021-09-01 | ON_EXCHANGE | 25-26/08/2021 |  | https://www.kap.org.tr/tr/Bildirim/960857 |
| 8 | ORCAY | Orçay Ortaköy Çay Sanayi ve Ticaret A.Ş. | 2021-09-02 | ON_EXCHANGE | 26-27/08/2021 |  | https://www.kap.org.tr/tr/Bildirim/961005 |
| 9 | YEOTK | YEO Teknoloji Enerji ve Endüstri A.Ş. | 2021-09-03 | ON_EXCHANGE | 27-31/08/2021 |  | https://www.kap.org.tr/tr/Bildirim/961251 |
| 10 | TEZOL | Europap Tezol Kağıt Sanayi ve Ticaret A.Ş. | 2021-09-15 | OFF_EXCHANGE_BOOKBUILD | 8-10/09/2021 |  | https://www.kap.org.tr/tr/Bildirim/963539 |
| 11 | KIMMR | Ersan Alışveriş Hizmetleri ve Gıda Sanayi Ticaret A.Ş. | 2021-09-22 | ON_EXCHANGE | 16-17/09/2021 |  | https://www.kap.org.tr/tr/Bildirim/964579 |
| 12 | MAREN | Margün Enerji Üretim Sanayi ve Ticaret A.Ş. | 2021-09-30 | ON_EXCHANGE | 22-23/09/2021 |  | https://www.kap.org.tr/tr/Bildirim/965391 |
| 13 | ANGEN | Anatolia Tanı ve Biyoteknoloji Ürünleri Araştırma Geliştirme Sanayi ve Ticaret A.Ş. | 2021-10-21 | OFF_EXCHANGE_BOOKBUILD | 14-15/10/2021 |  | https://www.kap.org.tr/tr/Bildirim/971306 |
| 14 | GLCVY | Gelecek Varlık Yönetimi A.Ş. | 2021-10-21 | OFF_EXCHANGE_BOOKBUILD | 14-15/10/2021 |  | https://www.kap.org.tr/tr/Bildirim/971307 |
| 15 | HEDEF | Hedef Holding A.Ş. | 2021-10-22 | OFF_EXCHANGE_BOOKBUILD | 14-15/10/2021 |  | https://www.kap.org.tr/tr/Bildirim/971308 |
| 16 | IHAAS | İhlas Haber Ajansı A.Ş. | 2021-11-03 | ON_EXCHANGE | 26-27/10/2021 |  | https://www.kap.org.tr/tr/Bildirim/973648 |
| 17 | ARASE | Doğu Aras Enerji Yatırımları A.Ş. | 2021-11-11 | OFF_EXCHANGE_BOOKBUILD | 04-05/11/2021 |  | https://www.kap.org.tr/tr/Bildirim/976327 |
| 18 | ULUFA | Ulusal Faktoring A.Ş. | 2021-11-11 | OFF_EXCHANGE_BOOKBUILD | 04-05/11/2021 |  | https://www.kap.org.tr/tr/Bildirim/976329 |
| 19 | ELITE | Elite Naturel Organik Gıda Sanayi ve Ticaret A.Ş. | 2021-11-15 | OFF_EXCHANGE_BOOKBUILD | 08-09/11/2021 |  | https://www.kap.org.tr/tr/Bildirim/977081 |
| 20 | ISSEN | İşbir Sentetik Dokuma Sanayi A.Ş. | 2021-11-18 | OFF_EXCHANGE_BOOKBUILD | 10-12/11/2021 |  | https://www.kap.org.tr/tr/Bildirim/978115 |
| 21 | MIATK | Mia Teknoloji A.Ş. | 2021-11-22 | ON_EXCHANGE | 15-16/11/2021 |  | https://www.kap.org.tr/tr/Bildirim/978546 |
| 22 | MOBTL | Mobiltel İletişim Hizmetleri Sanayi ve Ticaret A.Ş. | 2021-11-25 | OFF_EXCHANGE_BOOKBUILD | 18-19/11/2021 |  | https://www.kap.org.tr/tr/Bildirim/979022 |
| 23 | KONKA | Konya Kağıt Sanayi ve Ticaret A.Ş. | 2021-11-26 | OFF_EXCHANGE_BOOKBUILD | 18-19/11/2021 |  | https://www.kap.org.tr/tr/Bildirim/979024 |
| 24 | PCILT | PC İletişim ve Medya Hizmetleri Sanayi Ticaret A.Ş. | 2021-12-01 | ON_EXCHANGE | 24-25/11/2021 |  | https://www.kap.org.tr/tr/Bildirim/979917 |
| 25 | RNPOL | Rainbow Polikarbonat Sanayi Ticaret A.Ş. | 2021-12-06 | ON_EXCHANGE | 30/11/2021-01/12/2021 |  | https://www.kap.org.tr/tr/Bildirim/980714 |
| 26 | PSGYO | Pasifik Gayrimenkul Yatırım Ortaklığı A.Ş. | 2021-12-16 | OFF_EXCHANGE_BOOKBUILD | 09-10/12/2021 |  | https://www.kap.org.tr/tr/Bildirim/983147 |

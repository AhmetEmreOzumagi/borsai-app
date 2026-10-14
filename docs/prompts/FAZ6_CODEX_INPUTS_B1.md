# TASK_ID: BORSAI_FAZ6_CODEX_INPUTS_B1_20260924

AYAR: Codex + GPT-6 Astra · repo DIŞINDA · ağ açık · oturum hafızası kapalı. Çalışma klasörü: `~/Desktop/BorsAi_codex/` (yoksa oluştur). Zaman sınırı: 4 saat; bitmeyen arzlar `status: "PARTIAL"` ile teslim edilir.

## Ne istiyoruz
Borsa İstanbul'da **2020 + 2021 ilk yarı** döneminde halka arz edilen **34 şirket** için, **yalnız listeleme öncesi yayımlanmış resmi belgelerden**, aşağıdaki alanları çıkar. Her değer için resmi kaynak URL'si, KAP yayın zamanı, erişim zamanı ve belgeden birebir alıntı ver. Bulamadığını uydurma: `"BULUNAMADI"` yaz ve nerelere baktığını listele.

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
Tek dosya: `~/Desktop/BorsAi_codex/BORSAI_FAZ6_CODEX_INPUTS_B1_20260924.json`
```json
{"task_id": "BORSAI_FAZ6_CODEX_INPUTS_B1_20260924", "generated_at_utc": "…", "model": "…",
 "ipos": [ {"ticker": "…", "company": "…", "first_trading_date": "YYYY-MM-DD", "status": "OK | PARTIAL",
            "fields": {"<alan>": { …kayıt… }},
            "documents": [ {"url": "…", "type": "…", "kap_notice_id": "…", "published_at": "…", "accessed_at_utc": "…", "title": "…"} ],
            "issues": ["…"] } ],
 "exposure_log": [ {"what": "…", "where": "…", "when_utc": "…"} ],
 "summary": {"n_ipos": 0, "n_ok": 0, "n_partial": 0, "fields_not_found": {"<alan>": 0}}}
```
Kurallar: her iddia için URL ve erişim zamanı; bulunamayana "BULUNAMADI"; tahmin, ortalama, ilişki analizi YOK; listeleme sonrası sonuç bilgisi YOK.

## Arzlar (34)
Kaynak: KAP "Payların İşlem Görmeye Başlaması" bildirimleri (Borsa İstanbul). Satış yöntemi: `ON_EXCHANGE` = Borsa'da satış, diğerleri borsa dışı talep toplama.

| # | ticker | şirket | ilk işlem | satış yöntemi (KAP) | talep toplama | SPK onay | BIST listeleme bildirimi |
|---|---|---|---|---|---|---|---|
| 1 | ARDYZ | ARD Grup Bilişim Teknolojileri A.Ş. | 2020-02-06 | ON_EXCHANGE | 29-30/01/2020 | 2020-01-16 | https://www.kap.org.tr/tr/Bildirim/817020 |
| 2 | BAYRK | Bayrak EBT Taban Sanayi ve Ticaret A.Ş. | 2020-06-04 | ON_EXCHANGE | 28-29/05/2020 | 2020-05-21 | https://www.kap.org.tr/tr/Bildirim/848611 |
| 3 | FADE | Fade Gıda Yatırım Sanayi Ticaret A.Ş. | 2020-08-06 | ON_EXCHANGE | 29-30/07/2020 | 2020-07-23 | https://www.kap.org.tr/tr/Bildirim/864942 |
| 4 | DNISI | Dinamik Isı Makina Yalıtım Malzemeleri Sanayi ve Ticaret A.Ş. | 2020-09-03 | ON_EXCHANGE | 27-28/08/2020 | 2020-08-20 | https://www.kap.org.tr/tr/Bildirim/872784 |
| 5 | ESEN | Esenboğa Elektrik Üretim A.Ş. | 2020-10-09 | ON_EXCHANGE | 01-02/10/2020 | 2020-09-24 | https://www.kap.org.tr/tr/Bildirim/879366 |
| 6 | KONTR | Kontrolmatik Teknoloji Enerji ve Mühendislik A.Ş. | 2020-10-19 | OFF_EXCHANGE_BOOKBUILD | 12-13/10/2020 | 2020-09-24 | https://www.kap.org.tr/tr/Bildirim/882009 |
| 7 | KRVGD | Kervan Gıda Sanayi ve Ticaret A.Ş. | 2020-12-04 | OFF_EXCHANGE_BOOKBUILD | 26-27/11/2020 | 2020-11-19 | https://www.kap.org.tr/tr/Bildirim/890999 |
| 8 | ARZUM | Arzum Elektrikli Ev Aletleri Sanayi ve Ticaret A.Ş. | 2020-12-24 | OFF_EXCHANGE_BOOKBUILD | 17-18/12/2020 | 2020-12-10 | https://www.kap.org.tr/tr/Bildirim/894223 |
| 9 | ISKPL | Işık Plastik Sanayi ve Dış Ticaret Pazarlama A.Ş. | 2021-01-28 | ON_EXCHANGE | 21-22/01/2021 | 2021-01-14 | https://www.kap.org.tr/tr/Bildirim/904453 |
| 10 | TRILC | Turk İlaç ve Serum Sanayi A.Ş. | 2021-03-05 | OFF_EXCHANGE_BOOKBUILD | 25-26/02/2021 | 2021-02-18 | https://www.kap.org.tr/tr/Bildirim/914831 |
| 11 | NTGAZ | Naturelgaz Sanayi ve Ticaret A.Ş. | 2021-04-01 | OFF_EXCHANGE_BOOKBUILD | 25-26/03/2021 | 2021-03-18 | https://www.kap.org.tr/tr/Bildirim/921905 |
| 12 | MTRKS | Matriks Bilgi Dağıtım Hizmetleri A.Ş. | 2021-04-06 | ON_EXCHANGE | 30-31/03/2021 | 2021-03-25 | https://www.kap.org.tr/tr/Bildirim/922962 |
| 13 | TUREX | Tureks Turizm Taşımacılık A.Ş. | 2021-04-08 | ON_EXCHANGE | 01-02/04/2021 | 2021-03-25 | https://www.kap.org.tr/tr/Bildirim/923959 |
| 14 | QUAGR | QUA GRANITE HAYAL YAPI VE ÜRÜNLERİ SANAYİ TİCARET A.Ş. | 2021-04-09 | ON_EXCHANGE | 05-06/04/2021 | 2021-03-25 | https://www.kap.org.tr/tr/Bildirim/924439 |
| 15 | GWIND | Galata Wind Enerji A.Ş. | 2021-04-22 | OFF_EXCHANGE_BOOKBUILD | 15-16/04/2021 | 2021-04-08 | https://www.kap.org.tr/tr/Bildirim/929710 |
| 16 | BIOEN | Biotrend Çevre ve Enerji Yatırımları A.Ş. | 2021-04-28 | OFF_EXCHANGE_BOOKBUILD | 19-20-21/04/2021 | 2021-04-15 | https://www.kap.org.tr/tr/Bildirim/930962 |
| 17 | AYDEM | Aydem Yenilenebilir Enerji A.Ş. | 2021-04-29 | OFF_EXCHANGE_BOOKBUILD | 19-22/04/2021 | 2021-04-08 | https://www.kap.org.tr/tr/Bildirim/930966 |
| 18 | CANTE | Çan2 Termik A.Ş. | 2021-04-30 | OFF_EXCHANGE_BOOKBUILD | 21-22/04/2021 | 2021-04-15 | https://www.kap.org.tr/tr/Bildirim/930973 |
| 19 | ZRGYO | Ziraat Gayrimenkul Yatırım Ortaklığı A.Ş. | 2021-05-06 | OFF_EXCHANGE_BOOKBUILD | 28-29-30/04/2021 | 2021-04-22 | https://www.kap.org.tr/tr/Bildirim/934472 |
| 20 | PENTA | Penta Teknoloji Ürünleri Dağıtım Ticaret A.Ş. | 2021-05-17 | OFF_EXCHANGE_BOOKBUILD | 06-07/05/2021 | 2021-04-29 | https://www.kap.org.tr/tr/Bildirim/935940 |
| 21 | KLKIM | Kalekim Kimyevi Maddeler Sanayi ve Ticaret A.Ş. | 2021-05-18 | OFF_EXCHANGE_BOOKBUILD | 06-07/05/2021 | 2021-04-29 | https://www.kap.org.tr/tr/Bildirim/935941 |
| 22 | MERCN | MERCAN KİMYA SANAYİ VE TİCARET A.Ş. | 2021-05-27 | ON_EXCHANGE | 20-21/05/2021 | 2021-05-06 | https://www.kap.org.tr/tr/Bildirim/937987 |
| 23 | BOBET | Boğaziçi Beton Sanayi ve Ticaret A.Ş. | 2021-06-03 | OFF_EXCHANGE_BOOKBUILD | 26-28/05/2021 | 2021-05-20 | https://www.kap.org.tr/tr/Bildirim/939093 |
| 24 | ATATP | ATP Ticari Bilgisayar Ağı ve Elektrik Güç Kaynakları Üretim Pazarlama ve Ticaret A.Ş. | 2021-06-04 | OFF_EXCHANGE_BOOKBUILD | 27-28/05/2021 | 2021-05-20 | https://www.kap.org.tr/tr/Bildirim/939094 |
| 25 | UNLU | Ünlü Yatırım Holding A.Ş. | 2021-06-07 | OFF_EXCHANGE_BOOKBUILD | 31/05/2021-01/06/2021 | 2021-05-27 | https://www.kap.org.tr/tr/Bildirim/939957 |
| 26 | BMSCH | BMS Çelik Hasır Sanayi ve Ticaret A.Ş. | 2021-06-08 | ON_EXCHANGE | 31/05-01/06/2021 | 2021-05-27 | https://www.kap.org.tr/tr/Bildirim/939961 |
| 27 | OYYAT | Oyak Yatırım Menkul Değerler A.Ş. | 2021-06-10 | OFF_EXCHANGE_BOOKBUILD | 02-04/06/2021 | 2021-05-27 | https://www.kap.org.tr/tr/Bildirim/941172 |
| 28 | BASGZ | Başkent Doğalgaz Dağıtım Gayrimenkul Yatırım Ortaklığı A.Ş. | 2021-06-11 | OFF_EXCHANGE_BOOKBUILD | 03-04/06/2021 | 2021-05-27 | https://www.kap.org.tr/tr/Bildirim/941465 |
| 29 | SELVA | Selva Gıda Sanayi A.Ş. | 2021-06-25 | OFF_EXCHANGE_BOOKBUILD | 17-18/06/2021 | 2021-06-10 | https://www.kap.org.tr/tr/Bildirim/943848 |
| 30 | MEDTR | Meditera Tıbbi Malzeme Sanayi ve Ticaret A.Ş. | 2021-07-02 | OFF_EXCHANGE_BOOKBUILD | 23-24-25/06/2021 | 2021-06-17 | https://www.kap.org.tr/tr/Bildirim/944905 |
| 31 | EDATA | E-Data Teknoloji Pazarlama A.Ş. | 2021-07-05 | ON_EXCHANGE | 29-30.06.2021 | 2021-06-24 | https://www.kap.org.tr/tr/Bildirim/945601 |
| 32 | KTSKR | Kütahya Şeker Fabrikası A.Ş. | 2021-07-08 | ON_EXCHANGE | 01-02/07/2021 | 2021-06-24 | https://www.kap.org.tr/tr/Bildirim/947014 |
| 33 | VBTYZ | VBT YAZILIM A.Ş. | 2021-07-12 | ON_EXCHANGE | 05-06/07/2021 | 2021-06-24 | https://www.kap.org.tr/tr/Bildirim/949088 |
| 34 | ESCAR | Escar Turizm Taşımacılık Ticaret A.Ş. | 2021-07-13 | ON_EXCHANGE | 07-08/07/2021 | 2021-07-01 | https://www.kap.org.tr/tr/Bildirim/950059 |

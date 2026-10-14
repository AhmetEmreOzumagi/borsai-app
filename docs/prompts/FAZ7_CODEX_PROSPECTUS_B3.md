# TASK_ID: BORSAI_FAZ7_CODEX_PROSPECTUS_B3_20260925

AYAR: Codex + GPT-6 Astra · repo DIŞINDA · ağ açık · oturum hafızası kapalı. Çalışma klasörü: `~/Desktop/BorsAi_codex/` (yoksa oluştur). Zaman sınırı: 4 saat; bitmeyen arzlar `status: "PARTIAL"` ile teslim edilir.

## Ne istiyoruz
Aşağıdaki **38 şirketin** her biri için izahnameden ve Tasarruf Sahiplerine Satış Duyurusu'ndan (TSSD) 7 alan çıkar. Alan listesi aşağıda. Kaynak yalnız **listeleme öncesi yayımlanmış resmi belgeler**dir. Her değer için şunları ver: resmi kaynak URL'si, KAP yayın zamanı, erişim zamanı, sayfa ve belgeden birebir alıntı. Bulamadığını uydurma: `"BULUNAMADI"` yaz ve nerelere baktığını listele.

Bu alanlar, "hangi halka arzlar ilk günlerde düşüyor?" sorusu için aday özelliklerdir. Önce keşfedilecekler, sonra ayrı ve sonuçları hiç görülmemiş bir kümede tek seferde doğrulanacaklar. Bu yüzden aşağıdaki körlük kuralı her şeyden önce gelir.

## SONUÇ KÖRLÜĞÜ (kesin kural)
- Bu şirketlerin **ilk işlem gününden sonraki hiçbir fiyat, getiri, tavan, taban, hacim ya da performans bilgisine bakma, yazma, özetleme.**
- Açma: haber siteleri, forumlar, sosyal medya, aracı kurum bültenleri ve performans raporları, investing.com / tradingview / isyatirim fiyat sayfaları, "halka arz performansı", "kaç tavan yaptı", "en çok kazandıran" türü her sayfa. Arama sonuçlarında böyle bir bilgiyi istemeden görürsen `exposure_log`'a yaz (ne, nerede); değerini yazma.
- İzinli kaynaklar (resmi):
  - **KAP:** kap.org.tr bildirim sayfaları, `api/BildirimPdf/<id>` PDF'leri ve ekleri. İzahname ve TSSD çoğunlukla şirket ya da aracı kurum bildiriminin eki olarak buradadır.
  - **SPK:** spk.gov.tr; onaylı izahname/TSSD duyuruları, haftalık bülten.
  - **Borsa İstanbul:** yalnız listeleme öncesi duyurular.
  
  Şirket ya da aracı kurum sitesindeki izahname/TSSD kopyası, KAP'ta bulunamazsa ve yalnız `secondary: true` etiketiyle kullanılır.
- Belgenin KAP yayın zamanı, şirketin ilk işlem gününden (İstanbul saati) **önce** olmalı. Değer yalnız sonraki bir belgede varsa `status: "YALNIZ_LISTELEME_SONRASI"` yaz, değeri verme.
- İzahnamenin **finansal tablolar, fiyat tespit raporu değerleme sonuçları ve geçmiş performans** bölümlerinden değer alma. Bu görevin alanları bunlar değil.

## Nereye bakılır (ipucu)
1. **TSSD** (Tasarruf Sahiplerine Satış Duyurusu): dağıtım esasları (eşit / oransal / karma), fiyat istikrarı, satmama taahhüdü. Genellikle 20–40 sayfa; en hızlı kaynak.
2. **İzahname:** fiyat istikrarı ve satmama taahhüdü bölümleri (2020–2023 şablonunda genellikle "halka arza ilişkin bilgiler" kısmı, yaklaşık §23–§25), faaliyet alanı ("ihraççının faaliyetleri"), faizsiz finans / katılım endeksi uygunluğu beyanı (varsa).
3. Taranmış PDF'lerde OCR kullan; alıntıyı OCR metninden ver ve `ocr: true` yaz.
4. KAP API'si hızlı istekte 429 döndürür: istekler arasında 3–4 saniye bekle, 429'da geri çekil.

## Alanlar (her arz için, 7 alan)
Değerleri belgede yazdığı gibi (metin) ver ve birim yaz. Hesaplanmış bir değerde `derived: true` yaz ve formülü `note`'a koy.
- `distribution_method`: yatırımcı gruplarına ve grup içine dağıtım yöntemi, belgedeki ifadeyle ("eşit dağıtım", "oransal dağıtım", "karma", "borsada satış"). Grup başına farklıysa her grubu `note`'a yaz.
- `price_stability_planned`: fiyat istikrarı işlemleri planlanmış mı (true/false + alıntı).
- `price_stability_days`: fiyat istikrarı süresi (gün; belgede "30 gün" gibi). Planlanmamışsa boş bırak ve `status: "OK"` yaz; `note: "planlanmamış"`.
- `issuer_lockup_days`: ihraççının (şirketin) sermaye artırımı / pay satmama taahhüdü süresi (gün). Kapsamı ve istisnaları `note`'a.
- `shareholder_lockup_days`: mevcut ortakların pay satmama taahhüdü süresi (gün). Ortaklar arasında farklıysa en kısa süreyi ver, hepsini `note`'a yaz.
- `sector`: izahnamedeki faaliyet alanı, kısa (ör. "enerji üretimi", "gıda", "yazılım"). Alıntı zorunlu.
- `participation_index_eligible`: izahname ya da TSSD'de katılım endeksine / faizsiz finans ilkelerine uygunluk beyanı varsa true/false + alıntı. Yoksa "BULUNAMADI".

Ek olarak her arz için bulunan izahname ve TSSD belgelerini `documents` listesine yaz (URL, tür, KAP bildirim no, yayın zamanı, sayfa sayısı, sha256 hesaplayabildiysen).

## Her değer için kayıt biçimi
```json
{"value": "30", "unit": "gün", "status": "OK | BULUNAMADI | YALNIZ_LISTELEME_SONRASI | PARTIAL",
 "source_url": "https://www.kap.org.tr/tr/Bildirim/…", "source_type": "TSSD | IZAHNAME | KAP_DIGER | SPK | DIGER",
 "kap_notice_id": "…", "published_at": "YYYY-MM-DDTHH:MM:SS+03:00", "accessed_at_utc": "YYYY-MM-DDTHH:MM:SSZ",
 "page": 12, "quote": "belgeden birebir, en çok 300 karakter", "ocr": false, "derived": false, "secondary": false, "note": ""}
```

## Teslim
Tek dosya: `~/Desktop/BorsAi_codex/BORSAI_FAZ7_CODEX_PROSPECTUS_B3_20260925.json`
```json
{"task_id": "BORSAI_FAZ7_CODEX_PROSPECTUS_B3_20260925", "generated_at_utc": "…", "model": "…",
 "ipos": [ {"ticker": "…", "company": "…", "first_trading_date": "YYYY-MM-DD", "status": "OK | PARTIAL",
            "fields": {"<alan>": { …kayıt… }},
            "documents": [ {"url": "…", "type": "IZAHNAME | TSSD | …", "kap_notice_id": "…", "published_at": "…", "accessed_at_utc": "…", "title": "…", "pages": 0, "sha256": "…"} ],
            "issues": ["…"] } ],
 "exposure_log": [ {"what": "…", "where": "…", "when_utc": "…"} ],
 "summary": {"n_ipos": 0, "n_ok": 0, "n_partial": 0, "fields_not_found": {"<alan>": 0}}}
```
Kurallar:
- Her iddia için URL ve erişim zamanı.
- Bulunamayana "BULUNAMADI".
- Tahmin, ortalama ya da ilişki analizi YOK.
- Listeleme sonrası sonuç bilgisi YOK.
- Başka bir arzın bilgisini bu arza taşıma.

## Arzlar (38)
Kaynak: KAP "Payların İşlem Görmeye Başlaması" bildirimleri (Borsa İstanbul). Satış yöntemi: `ON_EXCHANGE` = Borsa'da satış, diğerleri borsa dışı talep toplama. Tablodaki bağlantı listeleme bildirimidir; izahname ve TSSD aynı şirketin daha önceki KAP bildirimlerindedir.

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

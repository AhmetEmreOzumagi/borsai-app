# TASK_ID: BORSAI_FAZ7_CODEX_PROSPECTUS_B2_20260925

AYAR: Codex + GPT-6 Astra · repo DIŞINDA · ağ açık · oturum hafızası kapalı. Çalışma klasörü: `~/Desktop/BorsAi_codex/` (yoksa oluştur). Zaman sınırı: 4 saat; bitmeyen arzlar `status: "PARTIAL"` ile teslim edilir.

## Ne istiyoruz
Aşağıdaki **26 şirketin** her biri için izahnameden ve Tasarruf Sahiplerine Satış Duyurusu'ndan (TSSD) 7 alan çıkar. Alan listesi aşağıda. Kaynak yalnız **listeleme öncesi yayımlanmış resmi belgeler**dir. Her değer için şunları ver: resmi kaynak URL'si, KAP yayın zamanı, erişim zamanı, sayfa ve belgeden birebir alıntı. Bulamadığını uydurma: `"BULUNAMADI"` yaz ve nerelere baktığını listele.

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
Tek dosya: `~/Desktop/BorsAi_codex/BORSAI_FAZ7_CODEX_PROSPECTUS_B2_20260925.json`
```json
{"task_id": "BORSAI_FAZ7_CODEX_PROSPECTUS_B2_20260925", "generated_at_utc": "…", "model": "…",
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

## Arzlar (26)
Kaynak: KAP "Payların İşlem Görmeye Başlaması" bildirimleri (Borsa İstanbul). Satış yöntemi: `ON_EXCHANGE` = Borsa'da satış, diğerleri borsa dışı talep toplama. Tablodaki bağlantı listeleme bildirimidir; izahname ve TSSD aynı şirketin daha önceki KAP bildirimlerindedir.

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

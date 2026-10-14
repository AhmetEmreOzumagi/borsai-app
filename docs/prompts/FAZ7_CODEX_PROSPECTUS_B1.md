# TASK_ID: BORSAI_FAZ7_CODEX_PROSPECTUS_B1_20260925

AYAR: Codex + GPT-6 Astra · repo DIŞINDA · ağ açık · oturum hafızası kapalı. Çalışma klasörü: `~/Desktop/BorsAi_codex/` (yoksa oluştur). Zaman sınırı: 4 saat; bitmeyen arzlar `status: "PARTIAL"` ile teslim edilir.

## Ne istiyoruz
Aşağıdaki **34 şirketin** her biri için izahnameden ve Tasarruf Sahiplerine Satış Duyurusu'ndan (TSSD) 7 alan çıkar. Alan listesi aşağıda. Kaynak yalnız **listeleme öncesi yayımlanmış resmi belgeler**dir. Her değer için şunları ver: resmi kaynak URL'si, KAP yayın zamanı, erişim zamanı, sayfa ve belgeden birebir alıntı. Bulamadığını uydurma: `"BULUNAMADI"` yaz ve nerelere baktığını listele.

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
Tek dosya: `~/Desktop/BorsAi_codex/BORSAI_FAZ7_CODEX_PROSPECTUS_B1_20260925.json`
```json
{"task_id": "BORSAI_FAZ7_CODEX_PROSPECTUS_B1_20260925", "generated_at_utc": "…", "model": "…",
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

## Arzlar (34)
Kaynak: KAP "Payların İşlem Görmeye Başlaması" bildirimleri (Borsa İstanbul). Satış yöntemi: `ON_EXCHANGE` = Borsa'da satış, diğerleri borsa dışı talep toplama. Tablodaki bağlantı listeleme bildirimidir; izahname ve TSSD aynı şirketin daha önceki KAP bildirimlerindedir.

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

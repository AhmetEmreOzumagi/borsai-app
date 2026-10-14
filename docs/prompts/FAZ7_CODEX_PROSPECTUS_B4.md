# TASK_ID: BORSAI_FAZ7_CODEX_PROSPECTUS_B4_20260925

AYAR: Codex + GPT-6 Astra · repo DIŞINDA · ağ açık · oturum hafızası kapalı. Çalışma klasörü: `~/Desktop/BorsAi_codex/` (yoksa oluştur). Zaman sınırı: 4 saat; bitmeyen arzlar `status: "PARTIAL"` ile teslim edilir.

## Ne istiyoruz
Aşağıdaki **37 şirketin** her biri için izahnameden ve Tasarruf Sahiplerine Satış Duyurusu'ndan (TSSD) 7 alan çıkar. Alan listesi aşağıda. Kaynak yalnız **listeleme öncesi yayımlanmış resmi belgeler**dir. Her değer için şunları ver: resmi kaynak URL'si, KAP yayın zamanı, erişim zamanı, sayfa ve belgeden birebir alıntı. Bulamadığını uydurma: `"BULUNAMADI"` yaz ve nerelere baktığını listele.

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
Tek dosya: `~/Desktop/BorsAi_codex/BORSAI_FAZ7_CODEX_PROSPECTUS_B4_20260925.json`
```json
{"task_id": "BORSAI_FAZ7_CODEX_PROSPECTUS_B4_20260925", "generated_at_utc": "…", "model": "…",
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

## Arzlar (37)
Kaynak: KAP "Payların İşlem Görmeye Başlaması" bildirimleri (Borsa İstanbul). Satış yöntemi: `ON_EXCHANGE` = Borsa'da satış, diğerleri borsa dışı talep toplama. Tablodaki bağlantı listeleme bildirimidir; izahname ve TSSD aynı şirketin daha önceki KAP bildirimlerindedir.

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

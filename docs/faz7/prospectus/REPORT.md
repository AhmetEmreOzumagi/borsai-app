# BORSAI_FAZ7_VERIFY_PROSPECTUS_20260925 — Rapor

Doğrulayıcı: Claude Code (Opus 5.5).
- Süre: 2026-09-25 21:05 – 2026-09-26 07:05 (İstanbul). İlk KAP isteği 18:12Z, son istek 04:03Z.
- Kesintiler: Mac pilde uykuya geçti (~1,5 saat) ve oturum bir kez kullanım sınırına takıldı.
- Repoya hiçbir şey yazılmadı, commit yok. Bütün çıktılar `~/Desktop/BorsAi_codex/verified_faz7/` altında.

## 0. Kabul kapısı
| Kapı | Durum |
|---|---|
| **K1** 135 ticker için `candidate_features_faz7/<T>.json`, her alanda durum | 135/135; 945 hücrenin hepsinde `status` (VERIFIED/CORRECTED/FILLED/MISSING) |
| **K2** her dolu değer resmi, pinli, listeleme öncesi belgede birebir | 841 dolu hücre. Bağımsız denetim (`_tools/scripts/audit_outputs.py`) 135/135 sorunsuz. Denetlenenler: alıntı ilgili sayfanın metninde birebir; dosya sha256'sı hem diskteki PDF'le hem MANIFEST'le eşleşiyor; KAP yayın zamanı ilk işlem gününden önce; `ocr` bayrağı doğru |
| **K3** kapsama, Codex doğruluk oranı, boşluk nedenleri | §1, §2, §4 |
| **K4** sonuç körlüğü, `EXPOSURE.md` | korundu; `EXPOSURE.md`'de Codex'in 8 satırı aynen, doğrulayıcı maruziyeti 0 değer |
| **K5** repoda dosya değişmedi | Bu görev repoya yazmadı. `git status` farkları (`docs/MODELS.md`, `experiments/log.jsonl`, `tests/…faz7_golden…`) ve `2a21a96` commit'i paralel hazard oturumuna ait |

## 1. Alan başına kapsama (önce = Codex OK; sonra = doğrulanmış dolu)
| Alan | Codex OK | Sonra | VERIFIED | CORRECTED | FILLED | MISSING |
|---|---|---|---|---|---|---|
| `distribution_method` | 85 | **135** | 80 | 5 | 50 | 0 |
| `price_stability_planned` | 99 | **135** | 99 | 0 | 36 | 0 |
| `price_stability_days` | 93 | **135** | 93 | 0 | 42 | 0 |
| `issuer_lockup_days` | 76 | **135** | 73 | 3 | 59 | 0 |
| `shareholder_lockup_days` | 83 | **135** | 80 | 3 | 52 | 0 |
| `sector` | 89 | **135** | 89 | 0 | 46 | 0 |
| `participation_index_eligible` | 7 | **31** | 7 | 0 | 24 | 104 |
| **toplam (945)** | 532 | **841** | 521 | 11 | 309 | 104 |

Değer dağılımı (biçim denetimi için; özellik–sonuç ilişkisine bakılmadı):
- Fiyat istikrarı planlı: TRUE 80 / FALSE 55. Süre (gün): 30 → 72, 0 → 55, 15 → 5, 10 → 2 (iş günü), 20 → 1.
- İhraççı satmama süresi (gün): 365 → 88, 180 → 40, 540 → 3, 730 → 2, 0 → 2.
- Ortak satmama süresi (gün): 365 → 72, 180 → 52, 540 → 6, 730 → 3, 450 → 1, 120 → 1.
- Katılım endeksi uygunluğu: TRUE 31, boş 104.

## 2. Codex doğruluk oranı
Codex'in OK verdiği **532** değerin **521**'i VERIFIED (**%97,9**), **11**'i CORRECTED, **0**'ı UNVERIFIABLE.

| Alan | Codex OK | VERIFIED | CORRECTED | Doğruluk |
|---|---|---|---|---|
| dağıtım yöntemi | 85 | 80 | 5 | %94,1 |
| fiyat istikrarı planlı mı | 99 | 99 | 0 | %100 |
| fiyat istikrarı süresi | 93 | 93 | 0 | %100 |
| ihraççı satmama süresi | 76 | 73 | 3 | %96,1 |
| ortak satmama süresi | 83 | 80 | 3 | %96,4 |
| sektör | 89 | 89 | 0 | %100 |
| katılım endeksi | 7 | 7 | 0 | %100 |

Parti bazında (VERIFIED / CORRECTED): B1 101/2 · B2 126/2 · B3 183/2 · B4 111/5.

**11 düzeltme:**
- **Dağıtım yöntemi (5):** ASGYO, CVKMD, KZGYO, PASEU ve ZRGYO. Codex bu alana satış yöntemini ("Sabit Fiyatla Talep Toplama") yazmış. Dördünde kaynağı sonuç bildirimi, ZRGYO'da yalnız grup adlarını da eklemiş. Belgede grup tahsisatı ve dağıtım esası var.
- **İhraççı satmama süresi (3):**
  - ANGEN 365 → 180 ve GIPTA 180 → 365: Codex ortakların taahhüt cümlesini ihraççınınki sanmış.
  - BRKVY 365 → 730: ihraççının bedelli sermaye artırımı yapmama süresi 2 yıl.
- **Ortak satmama süresi (3):**
  - BASGZ 365 → 180 ve ISSEN 365 → 180: aynı ortağın daha kısa ve iç içe olmayan bir taahhüdü var.
  - OBASE 180 → 365: Codex'in 180 günü yalnız fiyat istikrarıyla sonradan edinilecek paylara ait.

**Codex'in belgeleri:**
- Codex'in andığı 402 belgenin hepsi resmi URL'den yeniden indirildi. KAP yayın zamanı 402/402 aynı; Codex'in yerel kopyasıyla sha 402/402 aynı.
- Codex'in beyan ettiği sha 401/402 eşleşiyor. Tek uyuşmazlıkta Codex aynı bildirimin başka ekinin sha'sını yazmış (`_tools/logs/sha_compare.json`).
- Codex'in alıntıları çoğunlukla birebir değil ("…" ile kısaltılmış ya da kötü OCR); bazı alıntılar başka bir kişiye ya da bağlı ortaklığa ait. Doğrulama değer düzeyinde yapıldı, alıntılarımız bizim metnimizden.

## 3. Kategori ve biçim eşleme kuralları (H99 ana tablosuyla uyum)
H99 tablosu yalnız biçim için okundu: `data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv`'nin 6 sütununun benzersiz değerleri.

**`distribution_method`**: H99'daki kısa Türkçe kalıplar kullanıldı.
- `Borsa İstanbul Birincil Piyasa; yatırımcı grubu bazında tahsisat ve dağıtım yapılmadı` (45 arz): Borsa'da satış; belge grup tahsisatı yapılmayacağını söylüyor ve eşit/oransal adlandırmıyor. Dağıtımı Borsa yapıyor: her emre birer lot, zaman önceliğiyle.
- `Borsa'da satış; yatırımcı grubu tahsisatı yok; eşit dağıtım` (4): belge "eşit" diyor.
- Talep toplama: `<gruplar> eşit|oransal; kurumsala takdire bağlı dağıtım`.
  - Grup adları: yurt içi bireysel, çalışanlar, yüksek başvurulu.
  - "Takdire bağlı": kurumsal yatırımcılara dağıtımı ihraççı, yetkili kuruluş ya da satıcı ortak belirliyor; H99'daki "diğer gruplar izahname esaslarına göre" karşılığı. Kimin takdiri olduğu `note`'ta.
  - Ajan yazımları `_tools/scripts/normalize.py` ile tek biçime çekildi; ajanın yazımı `note`'ta.

**`price_stability_planned`** `TRUE`/`FALSE`. **`price_stability_days`**:
- Gün olarak; planlanmamışsa `0` (H99'da FALSE ↔ 0).
- "İş günü" yazılmışsa `unit: "iş günü"` (PCILT, YEOTK).
- Halka arz teşvikleri (günlük alım emri, geri alım, FAVÖK garantisi) fiyat istikrarı sayılmadı; `note`'ta.

**Süre dönüşümü:** 1 yıl = 365; 12'nin katı ay yıl sayılır (12 ay = 365, 24 ay = 730); diğer aylar ay × 30 (6 ay = 180, 15 ay = 450, 18 ay = 540). Codex'in "12 ay = 360" kodlaması biçim farkı sayıldı (FOUND_SAME).

**`issuer_lockup_days`:**
- İhraççının bedelli sermaye artırımı yapmama / dolaşımdaki payı artırmama süresi.
- Farklı süreli başka ihraççı taahhütleri (kendi paylarını satmama, bedelsiz artırım, geri alım) `note`'ta.
- "Yoktur" → 0.

**`shareholder_lockup_days`:** mevcut ortakların borsada satış kısıtları.
- Kapsam: gönüllü taahhütler (b) ve mevzuat gereği kısıtlar. Mevzuat kısıtları: Pay Tebliği 8/1, 9/3 ve 30.03.2023 tarihli 20/412 ilke kararı ("izahname onayından itibaren 180 gün, borsada satışı da kapsayacak şekilde").
- Türler:
  - `FIYAT_ALTI`: halka arz fiyatının altında satmama.
  - `MUTLAK`: borsada hiç satmama / dolaşımdaki payı artıracak şekilde satmama.
  - `DIGER`: yalnız borsa dışı satış / virman / özel emir kısıtı; değeri belirlemez.
- **Değer = herhangi bir ortağın borsada satış kısıtının ilk gevşediği gün.** Bileşenlerin en kısası alınır. Aynı ortağın daha uzun ve en az o kadar sıkı bir kısıtı tarafından kapsanan bileşen hesaba girmez:
  - MUTLAK 180 + MUTLAK 365 → 365
  - FIYAT_ALTI 365 + MUTLAK 540 → 540
  - MUTLAK 180 + FIYAT_ALTI 365 → 180
- Hariç tutulanlar: yetkili kuruluş (aracı kurum) taahhütleri ve ortağın sonradan (teşvik ya da fiyat istikrarıyla) edineceği paylara ilişkin beyanlar.
- Her taahhüt `components` listesinde (kim, gün, tür, dayanak, başlangıç). Böylece başka bir toplama kuralıyla yeniden hesaplanabilir.
- Not: bu kural ortada netleşti. Önce saf "en kısa bileşen" uygulanıyordu. 15 arz kapsanan bileşen kuralına, 27 arz (2023-04 sonrası) 20/412 kuralına göre yeniden düzenlendi. Değişiklikler `_tools/logs/verifier_interventions.jsonl` ve alan `note`'larında.

**`sector`:**
- H99 üslubunda kısa, cümle başı büyük ifade (ör. `Yenilenebilir enerji üretimi`, `Gayrimenkul yatırım ortaklığı`).
- Dayanak ihraççının kendi faaliyet cümlesi. Codex'in alıntısı bağlı ortaklığa aitse (KARYE, BRLSM, GENIL, KCAER, MOBTL) ihraççınınki kullanıldı; değer kategorisi aynı olduğu için Codex'e VERIFIED.

**`participation_index_eligible`:** `TRUE`/`FALSE` yalnız belgede açık beyan varsa.
- Dayanak: izahnamedeki Borsa İstanbul görüşünün Mayıs 2022'den itibaren içerdiği cümle: "… Katılım Finans İlkeleri Bilgi Formu'nda … verilen bilgiler dikkate alındığında … BIST Katılım Tüm Endeksinde yer alma şartlarını sağladığının değerlendirildiği …". Bu cümle 31 arzda var ve hepsi TRUE.
- "Sağlamadığı" beyanı hiçbir belgede görülmedi, dolayısıyla FALSE yok.
- Beyan sayılmayanlar: yalnız oran tablosundan oluşan Katılım Finans Formu, katılım bankası adları, helal sertifikası. Oranlardan eşik kıyasıyla değer türetilmedi.

## 4. Kalan boşlukların nedenleri
Tek boşluk `participation_index_eligible` alanında: **104** arz, hepsi "belgede açık beyan yok".
- **İlk işlem günü 2022-06 öncesi 77 arz:** Borsa İstanbul görüşünde katılım endeksi cümlesi uygulaması henüz yoktu; izahname, TSSD ve eklerde de uygunluk beyanı bulunmadı.
- **2022-06 ve sonrası 27 arz:** Borsa görüşü yalnız pazar, hukukçu raporu ve sorumluluk maddelerini içeriyor.
  - 4'ünde (PRDGS, SDTTR, MACKO, GIPTA) Katılım Finans Formu belge setinde var ama yalnız soru-cevap ve oran tablosu, sonuç cümlesi yok.
  - GIPTA'nın formu (Ek-8, KAP 1191129) doğrulayıcı tarafından ayrıca indirildi.

Diğer 6 alanda boş yok. Mühür ya da imza altında kalıp OCR'da bozulan 6 ifade, doğrulayıcı tarafından sayfa görüntüsünden gözle doğrulandı. Bunlar `verifier_visual_check` alanıyla ya da `note`'ta işaretli:
- KRVGD, KONKA: fiyat istikrarı 30 gün.
- PRDGS: fiyat istikrarı "planlanmamaktadır".
- PLTUR: ortak süresi 1 yıl.
- FORTE: ihraççı süresi 2 yıl.
- AHGAZ: yüksek başvurulu grup "oransal".

**Belge sorunları:**
- BASGZ izahnamesinin 1–3. parçaları KAP'ta "kişisel veri nedeniyle yayından kaldırılmış"; değerler 4., 12. ve 14. parçalardan.
- AKFYE izahnamesinin 201–300. sayfaları KAP konu listesinde bulunamadı; gerekli bölümler (§25–27, Borsa görüşü, ekler listesi) eldeki parçalarda.
- EYGYO'da §27.3 c)/d) bu PDF parçasında yok; ortak değeri b) maddesine ve risk faktörlerine dayanıyor.

## 5. Rastgele 10 arzda ikinci kontrol
Örneklem: `random.Random(20260925).sample(sorted(135 ticker), 10)` = KZBGY, DNISI, UNLU, CVKMD, QUAGR, HTTBT, TERA, ORCAY, BMSCH, YEOTK (`_tools/logs/sample10.txt`).
- İki ajan, ilk kararları görmeden bütün alanları baştan belirledi (`_tools/decisions2/`).
- **70 hücrenin 63'ü birebir aynı, 70'i anlamca aynı.** 7 fark sektör ifadesinin ayrıntı düzeyinde; aynı faaliyet.
- Fiyat istikrarı, bütün süreler, dağıtım yöntemi ve katılım 10/10 aynı. Düzeltme gerekmedi.
- Kayıtlar `verification_log.jsonl`'de `pass: 2` satırları (70 satır) ve `_tools/logs/recheck_log.jsonl`.

## 6. Maruziyet
Ayrıntı `EXPOSURE.md`'de. Codex'in `exposure_log`'undan 8 satır aynen taşındı. Doğrulayıcı tarafında hiçbir fiyat, getiri, tavan/taban ya da hacim değeri görülmedi.
- KAP listeleri bellekte süzüldü; kohortun listeleme sonrası 53 satırı (2020 gün taraması) gösterilmeden atıldı.
- 2023-08'de AHGAZ etiketli 23 satır atıldı. Hedefli sorguyla bunların Enerya'nın (ENERY) kendi listeleme öncesi izahname/TSSD satırları olduğu anlaşıldı.
- THB/THM, haber, forum, aracı kurum raporu ve fiyat sayfası açılmadı.

## 7. Yöntem, belgeler, süre ve istek sayısı
- **Evren eşleşmesi:** `docs/specs_faz6/ekler/evren_listesi.csv`'deki 135 MEMBER, Codex'in 4 partisindeki 135 ticker ile birebir; ilk işlem günleri 135/135 aynı.
- **Keşif:**
  - KAP `byCriteria` konu filtreli aylık sorgular (İzahname-Onaylanan ve alt türleri, İzahname değişikliği, TSSD, "Payların Borsa Birincil Piyasada Halka Arzı"): 48 sorgu + 1 hedefli ENERY sorgusu. 2020 için ayrıca 71 gün sorgusu.
  - Codex'in 463 bildirimine ek **758** bildirim bulundu: izahname ana parçaları, TSSD, Borsa duyuruları, taahhüt ve katılım formu ekleri. Codex çoğu arzda izahnamenin yalnız 1–2 parçasını almıştı.
- **İndirme:** **1.238** bildirim, **1.284** PDF, **3,19 GB**. Hepsi `source_docs/<T>/`'de; `MANIFEST.json`'da URL, bildirim URL'si, tür, KAP no, yayın zamanı, erişim zamanı, sha256, bayt, sayfa, metin katmanı.
  - 265 ek, adından belli bağımsız denetim, değerleme ya da hukukçu raporu, esas sözleşme veya iç yönerge olduğu için indirilmedi; adları ve URL'leri kayıtlı.
  - KAP eklerinde Java sarmalı açıldı; ham sarmalın sha'sı da MANIFEST'te.
- **Metin:** 40.380 sayfa; 38.066'sı Apple Vision OCR (tr-TR, doğru mod).
  - Bozuk gömülü metin katmanı ya da yönü yanlış algılanmış sayfalar çok ölçekli OCR ile yeniden okundu.
  - Eski metin `alt_text` olarak saklandı; denetçi ikisini de kabul ediyor, `ocr` bayrağı eşleşen metne göre.
- **İstekler:** KAP'a **2.691** istek (istek arası ≥ 3,5 sn; 15 geçici bağlantı hatası yeniden denendi; 429 alınmadı). Toplam 3,37 GB.
- **Karar süreci:**
  - Her arz için belge listesi, Codex değerleri ve aday pasajlardan oluşan bir dosya hazırlandı (`_tools/dossier/`).
  - 25 karar partisi, 2 bağımsız ikinci kontrol ve 2 uyumlaştırma ajanı ağsız çalıştı. Kararlar `_tools/decisions/`'da; her karar `check.py` denetiminden geçti.
  - 32 doğrulayıcı müdahalesi yapıldı, 23'ü değer değiştirdi (`_tools/logs/verifier_interventions.jsonl`).
- **Teslim dosyaları:** `candidate_features_faz7/` (135), `source_docs/<T>/MANIFEST.json` (135; toplam 1,5 MB), `coverage.csv`, `verification_log.jsonl` (1.015 satır: 945 pass=1 + 70 pass=2), `EXPOSURE.md`, bu rapor.
- Repoya daha sonra yalnız `candidate_features_faz7/*.json` ve `source_docs/<T>/MANIFEST.json` alınacak; PDF'ler URL + sha256 ile yeniden indirilip eşlenebilir.

## 8. Kalan liste
Tamamlanmamış iş yok.

Sahibin kararı gerekebilecek tanım noktası: `shareholder_lockup_days` toplama kuralı (§3). Başka bir kural (ör. ortak başına en uzun süre ya da yalnız MUTLAK) istenirse `components`'ten yeniden hesaplanabilir.

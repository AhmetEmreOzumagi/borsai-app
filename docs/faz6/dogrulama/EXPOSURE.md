# Maruziyet kaydı — BORSAI_FAZ6_VERIFY_CODEX_INPUTS_20260924

Doğrulayıcı: Claude Code (Opus 5.5), 2026-09-24 20:05–22:05 (İstanbul). Bu dosya boş değildir; aşağıdaki her satır değer yazılmadan tutulmuştur.

## 1. Hiç yapılmayanlar
- THB/THM bülteni **indirilmedi, açılmadı, HEAD isteği bile atılmadı** (istek günlüğü: `_tools/logs/requests.jsonl`; `borsaistanbul.com` alan adına 0 istek).
- Haber, forum, aracı kurum performans raporu, fiyat sayfası, arama motoru **açılmadı**. Web'e çıkan tek alan adları `www.kap.org.tr` ve `spk.gov.tr`.
- Alt ajanlar (6 parti + 1 gözden geçirme) ağ kullanmadı; yalnız yerel inceleme dosyalarını (listeleme öncesi belgelerin metinleri) okudu.

## 2. KAP sorgu listeleri (program içinde süzüldü)
- `byCriteria` sorguları (394 istek, 92.737 satır) her kohort üyesinin `[talep toplama başlangıcı − 7 gün, ilk işlem günü − 1]` penceresini kapsadı. Yanıt **bellekte** süzüldü; diske ve ekrana yalnız (a) ilgili kohort kodlarının hepsi o gün listeleme öncesinde olan satırlar ya da (b) ilgili şirket alanı boş ve metninde "halka arz" geçen, riskli sözcük (istikrar, devre kesici, tedbir, tavan, taban, getiri, performans…) içermeyen satırlar yazıldı.
- **2.333 satır** bir kohort üyesine o üyenin ilk işlem gününden sonra ait olduğu için hiç gösterilmeden ve kaydedilmeden atıldı (yalnız sayısı tutuldu, `_tools/logs/days_stats.jsonl`). 5 satır karışıktı (listeleme öncesi ve sonrası üyeler birlikte); riskli sözcük yoksa tutuldu.
- ENERY ("ENRYA" geçici koduyla yayımlanmış belgeler) ve A1CAP (izahname satırları grup şirketlerinin kodlarıyla etiketli) için 7 hedefli sorgu yapıldı; ekrana yalnız hedef unvanı içeren ya da listeleme öncesi kohort satırları basıldı. Görülen başlıklar: TSSD, izahname parçaları, fiyat tespit/analist raporu, halka arz sonucu, şirket genel bilgi formu, 2023/6 aylık finansal rapor ve faaliyet raporu başlıkları (ENERY, ilk işlem gününden 1 gün önce yayımlanmış) — hiçbirinde fiyat/getiri/hacim yok.
- **Listeleme sonrası bildirim başlığı görülmedi** (devre kesici vb. dahil).

## 3. SPK bülteni kesitleri (fiyat/getiri değil; kurumsal işlem satırları)
İnceleme dosyalarına SPK bülteninin A.1 tablosundan sonraki ~1.800 karakter ("dipnotlar") da girdi. Bu kesitlerde A.2 "Halka Açık Ortaklıkların Pay İhraçları" ve A.3 "Borçlanma Araçları" satırları bulunur. Programla yapılan ad eşleşmesine göre aşağıdaki 28 kohort üyesinin **listeleme tarihinden sonraki** bir bültende adı geçen satır(lar)ı bu kesitlerde yer aldı (yani doğrulayıcı ve/veya alt ajan tarafından görülmüş olabilir). Satırların içeriği sermaye artırımı/bedelsiz ya da borçlanma aracı ihraç başvurusudur; **fiyat, getiri, tavan/taban, hacim ya da performans bilgisi değildir**. Bazı eşleşmeler aracı kurum adı olabilir (ör. OYYAT = OYAK Yatırım, bir ihracın aracısı olarak). Değer yazılmadı.

| Kohort üyesi | Bülten | Kesitin ait olduğu inceleme dosyası |
|---|---|---|
| AHGAZ | 2023/47 | BYDNR, ENERY |
| ALFAS | 2023/50 | EBEBK |
| ANGEN | 2023/26 | BIENY, KAYSE |
| ARDYZ | 2021/59 | RNPOL |
| AYDEM | 2021/36 | KZBGY |
| BAYRK | 2023/13 | AKFYE |
| BIOEN | 2021/57 | KONKA, MIATK, MOBTL |
| CANTE | 2023/25 | BIGCH |
| DNISI | 2022/37 | BARMA |
| ELITE | 2023/21 | CVKMD, KOPOL |
| ENSRI | 2023/25 | BIGCH |
| EUREN | 2022/66 | BRKVY, PLTUR |
| GESAN | 2023/21 | CVKMD, KOPOL |
| GWIND | 2023/39 | ATAKP, FZLGY, KLSER |
| GZNMI | 2022/63 | OZSUB, SNICA |
| HEDEF | 2022/37 | BARMA |
| ISKPL | 2021/44 | KIMMR |
| KMPUR | 2023/45 | IZENR, OFSYM, TATEN |
| KRVGD | 2021/44 | KIMMR |
| KZBGY | 2022/33 | KRPLS |
| MEDTR | 2022/8 | HTTBT, INVES, KLSYN |
| NTGAZ | 2023/48 | KZGYO |
| OYYAT | 2021/44, 2022/30 | KIMMR, KCAER |
| PSGYO | 2023/50 | EBEBK |
| SMRTG | 2023/41 | ASGYO |
| SUWEN | 2023/39 | ATAKP, FZLGY, KLSER |
| YEOTK | 2022/37 | BARMA |
| YYLGD | 2023/45 | IZENR, OFSYM, TATEN |

Değerlendirme orkestratöründür (KARARLAR D2'deki `EXPOSED_*` sınıfları sonuç başlığı içindir; bu satırlar sonuç değildir). Kasa listesi değiştirilmedi.

## 4. Codex partilerinden devralınan maruziyet
Codex'in `exposure_log`'undaki 5 satır (KAP liste yanıtlarında listeleme sonrası "Pay Bazında Devre Kesici Bildirimi" başlıkları; yalnız PNLSN adıyla anılmış; KARARLAR D2 → `EXPOSED_CODEX`) bu görevde yeniden görülmedi; Codex'in günlüğü yalnız okundu.

## 5. Model bilgisi
Doğrulayıcı bir dil modelidir; 2020–2023 halka arz dalgası hakkında genel ön bilgisi olabilir (şartname §8'deki not aynen geçerlidir). Bu görevde hiçbir arzın gerçekleşen sonucu okunmadı, yazılmadı, tahmin edilmedi.

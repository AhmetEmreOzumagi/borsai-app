# BORSAI_FAZ7_VERIFY_PROSPECTUS_20260925 — Maruziyet kaydı

Kural: 135 arzın ilk işlem gününden sonraki fiyat/getiri/tavan/taban/hacim/performans bilgisine bakılmadı, yazılmadı. THB/THM bültenleri indirilmedi; haber, forum, aracı kurum performans raporu, fiyat sayfası açılmadı. Bu dosya (1) Codex'in `exposure_log` satırlarını aynen, (2) doğrulayıcının kendi maruziyet kayıtlarını içerir.

## 1. Codex `exposure_log` (8 satır, aynen)

| Parti | what | where | when_utc |
|---|---|---|---|
| B1 | ARZUM için listeleme sonrası sermaye artırımı bildirim özetleri arama sonuçlarında istemeden görüldü; içerik ve değerler kullanılmadı. | https://www.kap.org.tr/tr/Bildirim/1484846 | 2026-09-25T17:13:01Z |
| B1 | TRILC için listeleme sonrası sermaye artırımı bildirimi arama sonuçlarında istemeden görüldü; içerik ve değerler kullanılmadı. | https://www.kap.org.tr/tr/Bildirim/1564381 | 2026-09-25T17:13:01Z |
| B1 | AYDEM için listeleme sonrası devre kesici bildirimi arama sonuçlarında istemeden görüldü; içerik ve değerler kullanılmadı. | https://www.kap.org.tr/tr/Bildirim/1534217 | 2026-09-25T17:13:01Z |
| B1 | CANTE için listeleme sonrası toptan pay satışı bildirimi arama sonuçlarında istemeden görüldü; içerik ve değerler kullanılmadı. | https://www.kap.org.tr/tr/Bildirim/1476799 | 2026-09-25T17:13:01Z |
| B1 | CANTE için listeleme sonrası sermaye artırımı bildirimi arama sonuçlarında istemeden görüldü; içerik ve değerler kullanılmadı. | https://www.kap.org.tr/tr/Bildirim/1559061 | 2026-09-25T17:13:01Z |
| B2 | KAP indeks sorgusunda ULUFA için ilk işlem günü/sonrası devre kesici bildirim başlıkları istemeden görüldü; fiyat, getiri, hacim veya performans değeri kaydedilmedi. | Yerel resmî KAP API indeks önbelleği sorgusu | 2026-09-25T17:27:03Z |
| B3 | Listeleme sonrası fiyat istikrarı sürecinin sona ermesine ilişkin KAP bildirim başlığı görüldü; hiçbir sonuç veya değer okunmadı ya da kullanılmadı. | KAP bildirim sorgusu, bildirim 1037998 | 2026-09-25T17:58:38Z |
| B4 | Geniş KAP API çıktısında listeleme sonrası devre kesici/volatilite konu başlıkları istemeden göründü; hiçbir değer açılmadı veya kaydedilmedi. | KAP resmi bildirim API'sinin yerel filtreleme öncesi terminal çıktısı | 2026-09-25T17:44:16Z |

## 2. Doğrulayıcı (Claude) kayıtları

- **Gün taraması (byCriteria, 2020-01-13…2020-12-01, 71 sorgu, 20.459 satır):** yanıtlar bellekte süzüldü; kohort üyelerinin listeleme sonrası 53 satırı ekrana basılmadan ve diske yazılmadan atıldı (yalnız sayıları `_tools/logs/days_stats.jsonl`'de). Görülmedi.
- **Konu filtreli tarama (İzahname, İzahname değişikliği, TSSD, Borsa birincil piyasa duyurusu; 2019-11…2023-09, 48 sorgu, 4.635 satır):** 2023-08'de 23 satır "ilgili şirket" alanında listelenmiş bir kohort üyesinin kodu (AHGAZ) geçtiği için atıldı. Hedefli sorguyla bunların Enerya'nın (ENERY, geçici kod ENRYA) listeleme öncesi izahname/TSSD satırları olduğu görüldü; AHGAZ'a ait listeleme sonrası bildirim başlığı görülmedi. 2023-04'te 18 "karışık" (bir kohort kodu listeleme öncesi, biri sonrası) izahname satırı tutuldu; yalnız listeleme öncesi pencerelerde eşleşenler ekrana basıldı.
- THB/THM bülteni, haber, forum, aracı kurum performans raporu ve fiyat sayfası açılmadı. Ajanlar ağsız çalıştı; raporlarında listeleme sonrası bilgi yok (Borsa birincil piyasa duyurularında yalnız halka arz fiyatı).
- Maruziyet sayısı (doğrulayıcı): 0 değer; 1 kayıt (yukarıdaki AHGAZ etiketli Enerya satırları, içerik listeleme öncesi).

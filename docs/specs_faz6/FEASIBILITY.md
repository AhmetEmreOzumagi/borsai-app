# FEASIBILITY — H99 öncesi halka arz kohortu (2020-01-01…2023-09-21): ne var, ne yok, ne kadar sürer

Görev: BORSAI_FAZ6_FABLE_OLD_COHORT_SPEC_20260924. Tarih: 2026-09-24. Kanıtlar `ekler/` altında; her URL ve erişim zamanı `ekler/kaynaklar.json`. İşaretler: **[ÖLÇTÜM]** (bu görevde, ekler'de kanıtı var), **[ÇIKARIM]**, **[İKİNCİL]** (resmi olmayan ya da sonradan derlenmiş kaynak).

**Sonuç körlüğü beyanı (özet; ayrıntı §9).** Kohort penceresinde tarihli hiçbir THB/THM bülteni indirilmedi ve açılmadı; biçim probu yalnız 2019-12-31 tarihli iki dosyayla yapıldı. Pencere içi bülten URL'lerine yalnız HTTP HEAD (gövde yok) atıldı. Hiçbir arzın listeleme sonrası fiyat/getiri/tavan/hacim bilgisi okunmadı. Model eğitimi, tahmin ya da skor hesabı yapılmadı. Paralel oturum bu görev sırasında `post_d1_hazard_v0`'ı dondurdu (`models/INDEX_POST_D1.json`, commit 7c18c0f, push kanıtı 988025c); bu belge onu "donmuş" sayar.

## Özet (≤ 12 satır)

1. **Evren [ÖLÇTÜM]:** KAP'taki Borsa İstanbul "Payların İşlem Görmeye Başlaması" bildirimlerinden 2020-01-01…2023-09-21 penceresinde 136 kayıt; 135 halka arz üyesi + 1 kapsam dışı (GMTAS: halka arzsız kotasyon). Yıllara göre üye: **2020: 8, 2021: 52, 2022: 38, 2023: 37.** SPK resmi yıllık tablolarıyla 114 satır birebir eşleşti; kalan 21'i SPK'nın 2021 tablosunun Ağustos'ta kesik olmasından (SPK dosyasındaki eksiklik, KAP tam).
2. **H99 sınırı [ÖLÇTÜM]:** 2023-09-15…2026-08-06 bildirimlerinde H99'un 99 üyesinin hepsi var; fazladan yalnız ADGYO (2023-09-20) ve REEDR (2023-09-21). H99'un eksik 100. üyesi **REEDR**'dir; eski repo onu "unresolved" diye dışarıda bırakmış. İkisi de bu kohortun üyesidir.
3. **Girdiler:** V1.5 alanları (fiyat, satılan pay, sermaye, ayrım, talep katı) 8 örnek arzın hepsinde listeleme öncesi KAP belgelerinde; f3 6/8'de yazılı, 1/8 hesaplanabilir, 1/8 (2020 borsada satış) birincil belgede yok. PB alanları SPK haftalık bülteninin A.1 tablosunda 2020'den beri aynı sütunlarla var (6/8 bülten bulundu; SPK dizini 2021-H2, 2022-H1, 2023-H1 için eksik listeliyor, yedek kaynak TSSD). Point-in-time kanıtı KAP yayın zamanıdır (sunucu).
4. **Sonuç verisi:** THB/THM arşivi 2020–2023 için aynı URL kalıbıyla erişilebilir (8 tarihte HEAD 200); 2019 başlığı 2026 ile aynı (THB'de tek fark 2026'da eklenen bir sütun; THM bayt-eşit); `borsai/outcomes.py` eşlemesi değişmeden çalışır. THM'nin `FIYAT ADIMI` alanı o günkü adım tablosunu taşır.
5. **Rejim farkları:** fiyat marjı 13/03/2020'ye kadar Yıldız/Ana %20 (Ana G2 %15), sonra %10; fiyat adımı tablosu 06/11/2023'e kadar dört kademe (kohortun tamamı); borsada satış zorunluluğu 11/11/2021 (≤100 mn) ve 30/03/2023 (≤750 mn) + eşit dağıtım; açığa satış yasakları 2020-03 ve 2023-02; deprem kapanışı 2023-02-08…14. Model etkileri §4 tablosunda; hiçbir kural donmuş modellerin tanımını değiştirmez, üç durumda "uygulanamaz" etiketi doğar.
6. **Eski repo maruziyeti:** 2023-09-22 öncesi hiçbir arzın girdisi ya da sonucu toplanmamış, incelenmemiş, modelde kullanılmamış [ÖLÇTÜM]. Tek fiziksel maruziyet: arşivdeki 2023-09-22 ve sonrası ham bültenler, D_10'u 22 Eylül'den sonra biten 4 üyenin (TARKM, GIPTA, ADGYO, REEDR) D2–D10 satırlarını içerir; okunduğuna dair iz yok.
7. **İş planı:** girdi toplama 135 arz için ≈ 30–40 saat aracı çalışması (yıl başına paralel 4 kol), kod + bekçi ≈ 2–3 gün, sonuç indirme + skorlama ≈ 1 gün; commit sırası §7.
8. Protokol (üyelik, sıra, bekçiler, üçüncü ölçek, skorlama, beklenti, kasa) `SPEC_OOT_PRE_H99_V0.md`'de.

---

## 1. Evren (1a)

### 1.1 Kaynaklar

| Kaynak | Ne verir | Erişim | Sınırı |
|---|---|---|---|
| KAP `byCriteria` (Borsa İstanbul, konu "Payların İşlem Görmeye Başlaması") + her bildirimin PDF'i | ticker, unvan, işlem görecek nominal, baz fiyat, pazar, ilk işlem tarihi, halka arz yöntemi, talep toplama tarihleri, arz sonrası sermaye (metinde) | 2019-12…2023-10 aylık 47 sorgu, 146 PDF (sha256'lar `ekler/kap/`) | API 50 PDF'ten sonra 429 verir (3–4 s aralık + geri çekilme ile çözüldü) |
| SPK "Payların İlk Halka Arzı YYYY.xlsx" (resmi yıllık özet) | şirket, onay tarihi, talep toplama tarihi, ilk işlem tarihi, aracı kurum, pazar, sermaye öncesi/sonrası, arz nominal, artırım/ortak satışı, fiyat, **talep nominal ve talep katı, yatırımcı sayısı**, satış yöntemi | 2019–2023 beş dosya, `ekler/spk_tablolar/` | 2021 dosyası 32 satırda (Ağustos 2021) kesiliyor; sonradan derlenmiş (son değişiklik 2022-05 / 2023-10) → point-in-time değil, yalnız çapraz denetim; ticker yok |
| SPK haftalık bülteni A.1 "İlk Halka Arzlar" | izahname onayı; planlanan yapı (PB alanları) | dizin 2020 tam (78), 2021: 40/60, 2022: 29/74, 2023: 30/82 (`ekler/spk_bulten_dizini_2020_2023.json`); eksikler arama motoruyla tek tek bulunabiliyor | eksik dizin sayfaları; ObjectId'li URL tahmin edilemez |
| BIST tatil tabloları 2020–2023 + XU100 serisi | seans takvimi (tam/yarım gün) | `ekler/takvim_2020_2023.md` | 2023 tablosu deprem kapanışını içermez (XU100 boşluğuyla doğrulanır) |

BIST'in kendi HTML sayfaları (halka arz, satış yöntemleri, tatil sayfası) bu oturumda çoğunlukla açılamadı (boş yanıt); `/files` ve `/data` altındaki dosyalar sorunsuz indi.

### 1.2 Sayılar [ÖLÇTÜM `ekler/evren_listesi.csv`]

| Yıl | KAP üye | Borsada satış (birincil piyasa) | Borsa dışı talep toplama | Yıldız / Ana | SPK yıllık tabloda var |
|---|---|---|---|---|---|
| 2020 | 8 | 5 | 3 | 3 / 5 | 8 |
| 2021 | 52 | 21 | 31 | 30 / 22 | 31 (tablo Ağustos'ta kesik; 21 eksik) |
| 2022 | 38 | 15 | 23 | 26 / 12 | 38 (INVES dahil) |
| 2023 (→09-21) | 37 | 8 | 29 | 25 / 12 | 37 |
| **Toplam** | **135** | **49** | **86** | **84 / 51** | **114** |

- Kapsam dışı satır: GMTAS (Gimat, 2021-11-12, Alt Pazar): "Halka Arz Yöntemi: –", Kotasyon Yönergesi md. 9 ile kota alma, serbest marj → halka arz değil. Kohortta Alt Pazar/GİP üyesi yok.
- Düzeltme bildirimi: SNICA (2022-11-22, "Baz Fiyat Düzeltmesi", 20,03 → 20,04); tek satır kalır.
- Tarih tutarsızlığı: INVES bildiriminin alanı "01/03/2021" yazar, metni ve SPK tablosu 2022-03-01 (yazım hatası; `note` sütununda).
- KAP–SPK ilk işlem tarihi uyuşmazlığı: 0/114. Fiyat uyuşmazlığı: 0 (HTTBT'de SPK aralık 11,50–12,50 yazar, KAP baz fiyat 12,25 = kesin fiyat).
- 2019 tablosunda "İşlemden Kaldırma/Olumsuz Sonuçlanma" sütunlu 9 tamamlanmamış başvuru var; 2020'ye sarkan yok. 2019-12-06'da listelenen PAPIL pencere dışıdır.
- İkincil sayılarla karşılaştırma [İKİNCİL, görev metni]: 2021 için 52 tutuyor; 2022 için "40 civarı" → 38; 2023 için "54–55, ~19'u H99'da" → 37 + H99'daki 19 = 56.

### 1.3 H99 sınırı ve 100. üye [ÖLÇTÜM]

2023-09-01…2026-08-06 aylık KAP sorgusunda (`ekler/kap/kap_listeleme_sorgu_gunlugu_202309_202608.json`) 101 tekil kod: H99'un 99'u + ADGYO + REEDR. QUICK'ten geriye sayılan 100. arz REEDR'dir (ilk işlem 2023-09-21; SPK-B 2023/53 onayı 07/09/2023, HATSN ve ADGYO ile aynı bültende). Eski repo: `scripts/build_historical99_frozen_cohort_v1.mjs:563` REEDR ve MARMR'ı "excluded/unresolved" olarak dışarıda tutar (`ekler/arsiv/arsiv_tarama_1.txt` §5). HISTORICAL99 dondurma kuralı gereği H99'a eklenmez; bu kohortun en geç iki üyesidir.

### 1.4 Evren listesi
`ekler/evren_listesi.csv` (136 satır): ticker, şirket, ilk işlem tarihi, yıl, pazar, satış yöntemi (KAP ve SPK), KAP baz fiyat / SPK arz fiyatı, talep toplama tarihleri, SPK onay tarihi, durum, neden, KAP bildirim no/URL/yayın zamanı, PDF URL + sha256 + erişim zamanı (UTC), SPK tablo eşleşmesi + dosya URL'si + erişim zamanı, not. Ham KAP alanları `ekler/kap/kap_paylarin_islem_gormeye_baslamasi_bildirimleri.json`.

## 2. Girdi alanları (1b)

Örnek denetim: 8 arz (yıl başına en erken ve en geç ilk işlem; ARDYZ, ARZUM, ISKPL, PSGYO, PNLSN, AHGAZ, ONCSM, REEDR), yalnız listeleme öncesi belgelerle; belge, yayın zamanı ve sha256 tablosu `ekler/ornek_denetim.md`.

| Alan grubu | Model(ler) | Belge (eski kohort) | Yayın zamanı | Örnekte bulunma | Point-in-time / tanım sorunları |
|---|---|---|---|---|---|
| `ipo_price_tl` | V1.5 ailesi, tavan, yol | Sonuç bildirimi (aracı kurum ÖDA + ek); BIST bildirimi "Baz Fiyat"; SPK-B; TSSD | Sonuç: talep toplamadan 1–4 gün sonra, ilk işlemden ≥ 2 gün önce (8/8) | 8/8 | Fiyat aralıklı arzlarda kesin fiyat yalnız sonuç bildiriminde (ARZUM 17,00; HTTBT 12,25); baz fiyat = kesin fiyat (8/8) |
| `shares_offered` (kesin, ek satış dahil) | f1, f2, f4, post_d1 | Sonuç bildirimi ("… TL nominal payların tamamı satılmıştır"; ek satış ayrı yazılır) | aynı | 8/8; ek satış kullanılan 2/8 (ARZUM, PNLSN) | H99 kuralı aynen: ek satış dahil; alan başına `includes_additional_sale` etiketi |
| `post_ipo_share_capital` | f2 | SPK-B "Yeni Sermaye"; BIST bildirimi metni ("sermayesini temsil eden … TL"); izahname | SPK-B: onay günü; BIST: ilk işlemden 2–3 gün önce | 8/8 (7 SPK-B/BIST, 1 yalnız BIST/TSSD) | Yalnız ortak satışı olan arzda değişmez (ARZUM) |
| `capital_increase_shares`, `existing_share_sale_shares` | f4 | SPK-B tablosu (Bedelli / Mevcut Pay Satışı); sonuç metni bazen ayrıştırır (ISKPL, ONCSM, REEDR) | SPK-B onay günü | 8/8 (6 SPK-B; 2 TSSD/izahname) | DATA_NOTES §2 taşıma kuralı (tamamı satıldı + ek satış yok) aynen; ek satışlı arzlarda ek satışın hangi ortaktan geldiği SPK-B dipnotunda |
| `total_demand_multiple` (+origin, filter) | v1_5_h99, v1_6_h99, market20, ceiling_hazard, ceiling_path, post_d1 (ofset) | Sonuç bildirimi metni/eki | aynı | **6/8 yazılı** (ISKPL 14,2 UNFILTERED; PSGYO ≈1,8; PNLSN ≈8; AHGAZ 4,35; ONCSM 17,7; REEDR 3,95), **1/8 hesaplanabilir** (ARZUM: talep nominal / arz nominal), **1/8 yok** (ARDYZ, 2020 borsada satış: yalnız dağıtım tablosu ve yatırımcı sayısı) | "yaklaşık" → SOURCE_REPORTED_APPROX; "filtre edilmemiş" → UNFILTERED; ek satışlı arzlarda payda belirsizliği (DATA_NOTES §5) aynen; borsada satış arzlarında kat BIST verisine dayanır (ISKPL örneği), 2020'de yazılmamış olabilir → ret adayı. SPK yıllık tablodaki kat girdi olarak ALINMAZ (listeleme sonrası derleme) |
| PB 8 alanı (`ipo_price_try`, `planned_*`) | pb_v0, pb_ceiling_v0, pb_ceiling_path_v0 | SPK-B A.1 tablosu (2020/6, 2020/75, 2021/3, 2022/69, 2022/70, 2023/53 doğrulandı: aynı 7 sütun) → yoksa TSSD | SPK-B onay günü < talep toplama (8/8'de en az 7 gün) | 6/8 SPK-B; 2/8 dizin eksik (TSSD yedek) | Fiyat aralığı → `REFUSED_PB_PRICE_RANGE` (ARZUM; SPK yıllık tablolarına göre 2021'de 6, 2022'de ≥1 böyle arz var) |
| `first_trading_date`, `bookbuilding_start/end` | hepsi | BIST bildirimi | ilk işlemden 2–3 gün önce (8/8) | 8/8 | Borsada satış arzlarında "Halka Arz Tarihi" = birincil piyasa günleri; ikincil piyasa ilk günü = bildirim tarihi |
| f6 (XU100 20 seans) | market20 | XU100 pinli seri + Takvim C | — | 2020–2023 her seans gününde kapanış var; hafta içi boşluklar = resmi kapanışlar [ÖLÇTÜM `ekler/takvim_2020_2023.md`] | Takvim C yeni dosya (tatil tabloları + XU100 gün kümesi; yarım günler: 2020-07-30, 2020-10-28, 2021-05-12, 2021-07-19, 2021-10-28, 2022-07-08, 2022-10-28, 2023-04-20, 2023-06-27); deprem kapanışı 2023-02-09…14 |
| Fiyat adımı (limit yolu) | ceiling_path, pb_ceiling_path | Kural metni (§4-3) | — | tamamı T2015 tablosu | JSON tablosuyla yol farkı yalnız ≥ 250 TL seviyesinde; kohortta arz fiyatları ≤ 66 TL örneklerde; deterministik denetim S1'de |
| D1 alanları | post_d1_hazard_v0 | D_1 THB/THM satırı | — | başlıklar 2019'da mevcut | S3 makine-sıralı ayıklama (SPEC §2) |

**Point-in-time kanıtı.** KAP bildirimleri değiştirilemez; düzeltme yeni bildirimdir (SNICA). Yayın zamanı iki yerden alınır: liste API `publishDate` ve (2022 sonrası PDF'lerde) başlıktaki "KAP'ta yayınlanma tarihi ve saati"; örneklerde ±4 sn uyumlu. 2020–2021 PDF başlıklarında bu alan yoktur; liste API zamanı (sunucu) yeterlidir. SPK bülten PDF'i: bülten tarihi başlıkta, URL ObjectId'sinde oluşturulma zamanı (Faz 2A yöntemi). Eski belgelerin sonradan güncellenmesi: KAP'ta yok; SPK yıllık xlsx'ler güncellenmiş derlemelerdir (bu yüzden girdi değil).

**Yayın zamanı sınırı [ÖLÇTÜM].** 8/8 örnekte sonuç bildirimi ilk işlem gününden en az 2 takvim günü önce; TSSD/izahname talep toplamanın en az 5 gün önce.

## 3. Sonuç verisi (1c) [ÖLÇTÜM `ekler/bulten_probu/`]

- **URL kalıbı:** SPEC_SCORING §1 ile aynı (`/data/{thb|thm}/YYYY/MM/…1.zip`). HEAD probları (gövde yok): 2020-01-02, 2020-03-23, 2021-01-04, 2021-06-01, 2022-01-03, 2022-12-30, 2023-01-02, 2023-09-21 → hepsi 200, Content-Length 20–123 KB; Last-Modified THB için bülten günü akşamı (15:16–16:10 UTC), THM için sabahı (~05:00 UTC). İstisna: 2021-01-04 THB Last-Modified 2021-02-16 (yeniden yayımlanmış olabilir; sha pinlerken not).
- **Biçim (2019-12-31 probu):** zip içinde tek CSV, ad kalıbı aynı; cp1254; ";"; iki başlık satırı (TR/EN). THB 56 sütun (2026: 57; tek fark sona eklenen `BIST KATILIM TUM ENDEKS`, resmi biçim dokümanı sürüm 1.13, 20/09/2023 — `ekler/kurallar_arastirma.md` §14); ortak sütunların sırası aynı; `outcomes.py` `REQUIRED` ve SPEC_POST_D1 ek sütunlarının hepsi mevcut. THM 19 sütun, başlık bayt-eşit. THM `FIYAT ADIMI` alanı: 2019-12-31'de bütün `.E` serilerinde `&0.01:0.01-19.999&0.02:20.0-49.999&0.05:50.0-99.999&0.1:100.0-999999.999` (dönemin dört kademeli tablosu; §4-3 ile tutarlı).
- **Kod farkı:** yok; `parse_archive_bytes` ad tabanlıdır. Eklenecek: MANIFEST'e `schema_width` (56/57) ve `tick_table_field` kaydı; 2021-01-04 türü Last-Modified anomalisi için uyarı.
- **sha pinleme planı:** S5'te indirilen her zip `data/raw/bist/MANIFEST.csv`'ye (tarih, tür, URL, sha256, bayt, Last-Modified, indirme zamanı); OPEN üyelerin D_1…D_10 aralığını kapsayan tarihler (≈ 135 üye × 10 seans, çakışmalarla ≈ 400–500 seans günü × 2 tür); SEALED üyelerin penceresine denk gelen tarihler indirilmez (SPEC §2 G5). Toplam ≈ 60–90 MB.
- **Birincil piyasa günleri:** borsada satış arzlarında THB'de birincil piyasa serisinin nasıl göründüğü (`.HE` sırası; PPP 4.1.1) pencere içi bülten açmadan doğrulanamaz; D_1 tanımı KAP tarihine bağlandığı için (SPEC §1) skorlamayı etkilemez, S5'te raporlanır.

## 4. Kural ve rejim farkları (1d) — kaynaklar ve alıntılar `ekler/kurallar_arastirma.md`

| # | Kural | Dönem içi durum (2020-01-01…2023-09-21) | Bugün | Etki: donmuş modellere |
|---|---|---|---|---|
| 1 | Günlük fiyat marjı | 04/11/2019–12/03/2020: Yıldız %20, Ana G1 %20, Ana G2 %15; **13/03/2020'den itibaren Yıldız ve Ana %10** (Duyuru 2020/20, "ikinci duyuruya kadar"); 01/10/2020 yeni yapı genel kuralı %20/%15/%10 yazılı ama 2020/20 uygulaması sürüyor | aynı (%10 fiilen) | 2020-03-13 öncesi tek üye ARDYZ (2020-02-06): `base_always_ceiling`, `@INF` kuralları ve `ceiling_path_v0`/`pb_ceiling_path_v0` limit yolu **uygulanamaz** (`MARGIN_NOT_10PCT`); hazard ve V1.5 ailesi uygulanabilir, etiketle. Diğer 134 üye: etkisiz |
| 2 | İlk gün baz fiyatı | Borsada satış: birincil piyasa ilk gün baz = arz fiyatının en yakın adıma yuvarlanmışı; ikincil piyasa ilk seans baz = birincil piyasadaki son kapanış (PPP 4.1.1). Borsa dışı talep toplama: BIST bildirimindeki "Baz Fiyat" (8/8 örnekte = kesin arz fiyatı) | aynı | Borsada satış üyelerinde (49) ikincil piyasa D_1 baz fiyatı arz fiyatından farklı OLABİLİR (birincil piyasa kapanışı) → `ceiling_path` snap(P) varsayımı bozulur: D_1 THM referansı ≠ snap(P) ise `limit_path_mismatch = 1` (Faz 4 §7 mekanizması); R_h tanımı (arz fiyatına göre) değişmez. Etiket: `SALE_ON_EXCHANGE` |
| 3 | Fiyat adımı tablosu | 30/11/2015–05/11/2023: 0,01 / 0,02 / 0,05 / 0,10 (≥100 tek adım) | 06/11/2023'ten itibaren 8 kademe (JSON'daki tablo) | Kohortun tamamı eski tablo; yol farkı yalnız ≥ 250 TL seviyesinde → arz fiyatı × 1.1^10 ≥ 250 olan üye varsa S1'de deterministik denetim (`TICK_TABLE_MISMATCH` → uygulanamaz); örnek fiyatlar 5,30–66 TL |
| 4 | Limit yuvarlama ve baz fiyat | "İçeri doğru yuvarlama" ve baz = önceki kapanış: 2021–2026 revizyon cetvellerinde değişiklik yok; 2021 öncesi metin BULUNAMADI | aynı | Tavan etiketi THM'den okunduğu için etkisiz; `ceiling_path` yolu S5'te 2019-12-31 probundaki gibi 990/990 denetimiyle doğrulanır |
| 5 | Pazar yapısı / eşikler | 04/11/2019 Yıldız-Ana grupları; 01/10/2020 Yıldız/Ana/Alt; kotasyon eşikleri 2021-02 (300/75/40 mn) | 2026: 4 mlr / 1 mlr / 400 mn | Etkisiz (pazar etiketi taşınır); kohortta Alt Pazar üyesi yok |
| 6 | Tahsis / dağıtım | Tebliğ II-5.2 md. 18 (%10 bireysel, %10 kurumsal asgari) değişmedi; **30/03/2023 i-SPK.128.21: bireysele eşit dağıtım zorunlu, oransal yasak** | 19/09/2024 i-SPK.128.23 (aynı esas + yüksek talep grubu) | Etiket `ALLOC_REGIME` (2023-03-30 öncesi/sonrası; H99'un tamamı sonrası rejimde); model girdisi değil; (C) için aday |
| 7 | Satış yöntemi zorunluluğu | 11/11/2021: PD ≤ 100 mn → borsada satış zorunlu; 30/03/2023: ≤ 750 mn | 19/09/2024 aynı eşik | f3 tanımı borsada satışta BIST verisine dayanır; 2020–2021 küçük arzların bir kısmında f3 yok olabilir → `REFUSED_F3_MISSING` sayısı H99'dan yüksek beklenir |
| 8 | Fiyat istikrarı | Pay Tebliği md. 11 (≤ 30 gün, %20 sınırı) değişmedi | aynı | Etkisiz; aday özellik (§6) |
| 9 | Satmama taahhüdü | md. 8: 1 yıl arz fiyatı altında satmama (fiyata bağlı); ihtiyari mutlak taahhüt; **30/03/2023'ten itibaren 180 gün mutlak (mevcut ortaklar) + 90 gün (dağıtım alanlar)** | aynı | Etkisiz; aday özellik; 2023-03-30 öncesi üyelerde değişkenlik var |
| 10 | Açığa satış yasakları | 02/03/2020'den itibaren tüm paylarda (BIST-30 için 01/07/2020'de kalktı; diğerleri için kaldırılma tarihi BULUNAMADI); 06/02/2023'ten itibaren tüm paylarda (yeni arzlar BIST-50 dışı → sürüyor) | 2025-01-02 yalnız BIST-50'de kaldırıldı; 2025-03/05 genel yasak | Etiket `SHORT_SELL_BAN`; model uygulanabilir; canlı sicil de yasak rejimindedir |
| 11 | Devre kesici | 13/03/2020: %5, 30 dk; 2020/21: tüm paylarda %5 yalnız aşağı; EBDKS 10/08/2020 | 2025-09: 10 dk, EBDKS %6 | Etkisiz (gün içi mekanik; kapanış tanımı değişmez) |
| 12 | İlk gün özel tedbirler | Yeni arzlara özgü kural BULUNAMADI; açılış seansında emir iptali yasağı 2021-03 (son 5 dk), 2023-02-15 (tamamı) | aynı | Etkisiz |
| 13 | Piyasa kapanışları | 2023-02-08…14 deprem (XU100 boşluğu 02-09…02-14); 2020'de seans saati değişikliği kaydı yok | — | D_h takvimden; kapanış günleri seans sayılmaz; kapanışın hemen öncesinde listelenen üye varsa D_h kayar (raporlanır) |
| 14 | Bülten biçimi | 2017-10 sürüm 1.12'den 2023-09-20 sürüm 1.13'e kadar değişiklik yok | 1.14 (2024) referans tabloları | Etkisiz; §3 |
| 15 | KAP şablonları | "Payların İşlem Görmeye Başlaması" şablonu 2019-12'den beri aynı alanlarla [ÖLÇTÜM 146 PDF]; sonuç bildirimleri 2020–2021'de serbest metin ÖDA (+ek), "Halka Arz Sonuçları" şablonu en erken 2021-08 | şablon + ek karışık | Girdi toplama maliyeti: serbest metin ayrıştırma; `total_demand_definition` metni saklanır |

BULUNAMADI kalan alt sorular (12) `ekler/kurallar_arastirma.md` "Özet sayaç"ta; hiçbiri model tanımını etkilemez.

## 5. Eski repo maruziyeti (1e) — `ekler/arsiv/`

| Denetim | Sonuç |
|---|---|
| Ham bülten dosyaları (`th*` adlı 890 dosya) | En eski tarih **2023-09-22** (HATSN D_1); 2023: 71, 2024: 164, 2025: 86, 2026: 136 THB (THM benzer). 2020–2022 hiç yok |
| Arz verisi dosyaları (`ipo_master`, `pretrade_extension`, PB kanıtı, H99 master/provenance) | H99 dışı ticker yok; 2020-01-01…2023-09-21 arasında `first_trading_date` içeren satır yok |
| CSV/JSON tarih taraması (2020-01-01…2023-09-21) | 73 dosya isabet; hepsi XU100 serisi, takvim, deprem/tatil tarihleri, calendar-provenance ve mutation harness tarihleri; arz sonucu yok |
| 138 kohort kodunun taranması (ham bültenler hariç 2 332 dosya) | İsabet: HATSN (H99 üyesi), ADGYO (36 dosya: EXP100 keşfinde KAP şirket sayfasından kimlik + ilk işlem tarihi; sonuç yok), REEDR (3: H99 kurucu script "excluded/unresolved"), UNLU/HEDEF (yanlış pozitif: ÜNLÜ Menkul aracı kurum adı, "hedef" sözcüğü), EYGYO/GOKNR/TRILC (bir 2025 KAP duyurusunun ilgili-şirket alanında). 130 kodda hiç isabet yok |
| EXP100 evren keşfi (2026-08-15) | 108 adaylık liste QUICK'ten geriye sayar; en eski dolu tarih 2026-02-11; ADGYO ve HATSN "buffer"; hiçbir 2023-09-21 öncesi arz için girdi/sonuç toplanmamış |
| Git geçmişi | 2026-09-06'da başlar (`d7e8453`); öncesi yok |

**Hüküm:** Eski repo 2023-09-22 öncesi hiçbir arzın girdisini ya da sonucunu toplamamış, incelememiş, modelde kullanmamış. Kimlik düzeyinde temas yalnız ADGYO/REEDR (ilk işlem tarihi). (A) için tek kısıt: arşivdeki 2023-09-22 ve sonrası ham bültenler, D_10'u 22 Eylül'den sonra biten **TARKM (D_10 2023-09-25), GIPTA (09-27), ADGYO (10-03), REEDR (10-04)** için D2–D10 satırlarını fiziksel olarak içerir; H99 toplayıcısı yalnız H99 kodlarını ayıkladı, bu satırların okunduğuna dair iz yok. Bu 4 üye `EXPOSED_ARCHIVE` etiketiyle OPEN'da kalır, kasaya giremez (SPEC §7, §11-5).

## 6. Yeni aday özellikler (1f) — (C) için; ilişkiye bakılmadı

| Özellik | Resmi kaynak (listeleme öncesi) | Yayın zamanı | Eski kohort / H99 | Toplama maliyeti | Mekanizma gerekçesi (sonuç görmeden) |
|---|---|---|---|---|---|
| f-1 Katılımcı sayısı (toplam ve grup başına) | Sonuç bildirimi dağıtım tablosu ("Kişi"/"Başvuru sayısı") | Talep toplama sonrası, ilk işlemden ≥ 2 gün önce | 8/8 örnekte var (18 bin – 4,26 mn); H99'da sonuç bildirimleri zaten toplanmış (aynı belgeler) | Düşük–orta: 2020–2021 serbest metin tablo; 2022+ çoğunlukla yapılı | Tavan kuyruğu mekaniği: dağıtılan pay çok sayıda küçük hesaba bölündüğünde (ISKPL: 223 938 yatırımcıya 29'ar pay) elden çıkarma kararı çok sayıda küçük karara dağılır; ilk gün satış baskısı hesap başına lot ve katılımcı sayısıyla ilişkili olmalı. Yön a priori belirsiz (kalabalık = talep fazlası mı, hızlı kâr realizasyonu mu) |
| f-2 Kişi başı lot ve bireysel tahsisat payı | Aynı tablo: bireysele dağıtılan nominal / bireysel kişi sayısı; bireysel tahsisat oranı (%) | aynı | 7/8 (borsada satışta grup tahsisatı yok → kişi başı lot toplamdan) | Düşük (türetilmiş) | Kişi başı lot × fiyat = tipik pozisyon büyüklüğü; küçük pozisyonlar +%10'da satılmaya daha yatkın (flipper) hipotezi; 2023-03-30 sonrası eşit dağıtımla mekanik olarak küçüldü → rejim etiketiyle birlikte okunmalı |
| f-3 Aynı hafta listelenen arz sayısı | Kohort listesi (deterministik; `first_trading_date` ± 5 iş günü) | Listeleme öncesi bilinen (BIST bildirimleri 2–3 gün önce) | 135/135 ve H99 99/99 | Sıfır | Perakende likidite ve dikkat rekabeti; 2021'de aynı güne 3 listeleme var; canlıda "T'den önceki 5 iş günü + duyurulmuş sonraki 3 iş günü" tanımı gerekir (nedensellik yönü) |
| f-4 Katılım endeksine uygunluk | İzahname beyanı / Katılım Finans ilkeleri uyum bilgisi; THB `BIST KATILIM TUM ENDEKS` bayrağı **listeleme sonrası** (D_1 bülteni; yalnız post_d1 için) | İzahname: talep toplama öncesi | Kısmen: izahnamede her zaman yok; H99'da D_1 THB bayrağı 2023-09-20'den itibaren var | Orta–yüksek (izahname metni) | Katılım fonlarının talep havuzu ve tutma davranışı; yön belirsiz |
| f-5 Fiyat istikrarı (var/yok, süre, tutar) | İzahname "fiyat istikrarı" bölümü, TSSD | Talep toplama öncesi | 135/135 ve H99'da izahname var; çıkarım metinsel | Orta | Aracı kurumun 30 güne kadar arz fiyatı altında alım taahhüdü aşağı yönlü kırılmayı sınırlar → D10'da arz altı olasılığını düşürmesi beklenir; tavan serisiyle ilişkisi dolaylı |
| f-6 Satmama taahhüdü (kapsam, süre) | İzahname / TSSD; SPK-B dipnotu; 2023-03-30 sonrası zorunlu 180 gün | aynı | 2023-03-30 öncesi değişken (ihtiyari), sonrası sabit | Orta | Arz sonrası satılabilir pay stoku; taahhüt uzunsa satıcı arzı azalır → seri uzar hipotezi; H99'da varyans az (zorunlu rejim), eski kohortta var → keşif için asıl değer eski kohortta |
| f-7 Lider aracı kurum | KAP bildirimi göndericisi; SPK yıllık tablo; SPK-B | Onay günü | 135/135, 99/99 | Sıfır–düşük | Dağıtım ağı ve müşteri tabanı → katılımcı sayısı ve tutma davranışı; kategorik (≈ 25 kurum) → küçük n'de aşırı uyum riski; yalnız gruplanmış (banka kökenli / bağımsız) düşünülmeli |

Bu özelliklerin hiçbiri bu görevde hesaplanmadı; yalnız kaynak ve elde edilebilirlik belirlendi. (C) tasarımı: keşif OPEN ∪ H99, doğrulama SEALED (SPEC §9).

## 7. İş planı (1g)

**Görev bölümü (paralel koşabilir; yıl başına bir kol):**

| Kol | İş | Girdi kaynağı | Süre (tahmin) |
|---|---|---|---|
| K0 | Şartname kararları (SPEC §11) + `cohort_pre_h99.csv` + kasa listesi + regime_tags; commit + push (S0, S1-a) | bu belge, `evren_listesi.csv` | 0,5 gün |
| K1–K4 | Yıl başına girdi toplama: her üye için TSSD/izahname (PB, planlanan yapı), SPK-B (bulunabiliyorsa), sonuç bildirimi (+ek; f3, kesin yapı, katılımcı), BIST bildirimi; `registry/oot/inputs/<T>.json` + `source_docs` | KAP API (3–4 s/istek; 429'a karşı geri çekilme), SPK dizini + arama | Üye başına ≈ 15 dk (2020–2021 serbest metin) / 10 dk (2022–2023) → 2020: 2 s, 2021: 13 s, 2022: 7 s, 2023: 6 s; 4 kol paralel ≈ 1,5 iş günü |
| K5 | Takvim C (2020-01-01…2023-09-21): tatil tabloları + XU100 gün kümesi; yarım gün ve deprem kapanışı; pinleme | `ekler/takvim_2020_2023.md` | 0,5 gün |
| K6 | Kod: `registry.py` (oot), `freeze.py --oot`, `outcomes.py` (kohort kapısı, karantina, D_1 satır ayıklama), `market20.py` (Takvim C), `scoring.py` (`Scale`, `class_oot`, `oot_pre_h99` bloğu), `test_outcome_guard.py` G1/G3/G5/G6; uygulama paneli | SPEC §2, §10 | 2–3 gün |
| K7 | S2: 19 modelin toplu kayıtları (135 × 19), commit, push, kanıt | K1–K4 çıktısı | 0,5 gün |
| K8 | S3: D_1 satırları (OPEN ≈ 69) + post_d1 kayıtları; push | karantina indirme | 0,5 gün |
| K9 | S5: OPEN pencere bültenleri (≈ 250–300 seans günü × 2), `outcomes_oot`, sha pinleri | `outcomes.py` | 0,5 gün (indirme hız sınırına bağlı) |
| K10 | S6: skorlama + SCORES/MODELS güncellemesi + rapor | `scoring.py` | 0,5 gün |

**Commit sırası (her biri push + `push_proofs/`):** S0 şartname → S1 üyelik/kasa/regime_tags (girdisiz) → S1-b girdiler + belgeler (yıl kollarından ayrı commit'ler olabilir; hepsi S2'den önce) → K6 kod (S2'den önce; sonuç dosyası içermez) → S2 kayıtlar (tek commit) → S3 D_1 satırları + post_d1 → S5 bültenler + outcomes (OPEN) → S6 skorlar. SEALED açılışı ayrı görev.

**Toplam:** ≈ 5–7 iş günü takvim süresi; ≈ 35–45 saat aracı çalışması. Ana risk: KAP hız sınırı (bu görevde 96 kez 429) ve 2020–2021 serbest metin sonuç bildirimleri.

## 8. Var / kısmen / yok tablosu

| Öğe | Durum | Not |
|---|---|---|
| Evren listesi (resmi, ticker + tarih + kaynak) | **VAR** | 135 üye; K1 |
| V1.5 girdileri: fiyat, satılan pay, sermaye, ayrım | **VAR** | KAP sonuç + BIST bildirimi + SPK-B |
| f3 (talep katı) | **KISMEN** | borsa dışı: var; borsada satış 2021+: çoğunlukla var (BIST verisi); 2020 borsada satış: yok olabilir |
| PB 8 alanı | **VAR** | SPK-B (dizin eksikleri TSSD ile kapanır); fiyat aralıklı arzlarda ret |
| f6 (XU100 + takvim) | **VAR** | Takvim C kurulacak |
| Fiyat adımı / marj rejimi | **VAR** | kural metni; 1 üye marj ≠ %10 |
| D1 alanları (post_d1) | **VAR (makine sıralı)** | SPEC §2 S3 |
| THB/THM 2020–2023 | **VAR** | HEAD 200; biçim aynı; içerik bu görevde açılmadı |
| Seans takvimi 2020–2023 | **KISMEN** | tatil tabloları + XU100; THB HEAD probuyla çapraz denetim iş planında |
| SPK haftalık bülten dizini | **KISMEN** | 2020 tam; 2021/2022/2023 eksik sayfalar; tek tek aranabilir |
| KAP sonuç şablonu 2020–2021 | **KISMEN** | serbest metin ÖDA + PDF ek |
| Aday özellikler f-1, f-2, f-3, f-7 | **VAR** | sonuç bildirimi / kohort listesi |
| Aday özellikler f-5, f-6 | **KISMEN** | izahname metni |
| Aday özellik f-4 (katılım) | **YOK/KISMEN** | listeleme öncesi güvenilir kaynak belirsiz |
| Eski repoda eski kohort verisi | **YOK** | §5 |

## 9. Maruziyet beyanı

1. **Bülten:** Kohort penceresinde (2020-01-01…2023-09-21) tarihli hiçbir THB/THM dosyası indirilmedi, açılmadı. Biçim probu 2019-12-31 (kohort öncesi) ile yapıldı; pencere içi 8 tarihe yalnız HTTP HEAD (durum kodu, Content-Length, Last-Modified) atıldı. Repo içi 2026 bültenlerinden yalnız başlık satırı okundu.
2. **Web:** Açılan sayfalar yalnız KAP bildirim listeleri/PDF'leri (listeleme öncesi türler: izahname, TSSD, fiyat tespit, sonuç, BIST bildirimleri), SPK yıllık tablolar/bültenler/tebliğler/duyurular, BIST kural PDF'leri ve tatil tabloları. "Performans", "kaç tavan", "en çok kazandıran" türü sayfa açılmadı; arama sonuçlarında böyle bir snippet görülmedi. Kural araştırması alt ajanının sınırda gördükleri `ekler/kurallar_arastirma.md` "Maruziyet" bölümünde (şirket adları, iki 2021 sonuç bildirimi, bir genel kurul ÖDA'sı; hiçbirinde fiyat/getiri yok).
3. **SPK yıllık tabloları:** talep katı ve yatırımcı sayısı sütunları okundu; bunlar talep toplama sonucu, listeleme öncesi bilgidir. Tablolarda fiyat performansı sütunu yoktur (başlıklar `ekler/spk_tablolar/` dosyalarından doğrulanabilir).
4. **Sonuç bildirimleri:** 8 örnek için açıldı (talep, dağıtım, kesin fiyat/yapı); hepsi ilk işlem gününden önce yayımlanmış belgelerdir.
5. **Arşiv:** taramalar dosya adı, sütun adı ve kod/tarih düzeyindeydi; hiçbir 2023-09-22 sonrası bülten satırı okunmadı.
6. **LLM ön bilgisi:** Yazar, 2020–2023 Türkiye halka arz dalgasına ilişkin genel kamuoyu izlenimine (yüksek bireysel katılım, sık ilk gün tavanı) sahiptir; sayısal sonuç bilgisi değildir ama maruziyettir; SPEC §8 beklentileri bu izlenimden bağımsız mekanizma gerekçesiyle ve geniş aralıklarla yazıldı. Evren oluştururken KAP kodlarını şirket adlarıyla eşleştirirken bu ön bilgi kullanılmadı (eşleşme tarih + ad benzerliğiyle yapıldı).
7. **Model:** hiçbir model çağrılmadı, hiçbir tahmin ya da skor üretilmedi; `models/`, `data/`, `registry/`, `borsai/` dokunulmadı.

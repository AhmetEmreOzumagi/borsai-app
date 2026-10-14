# Resmi veri serisi kontrolü (2026-09-25; yalnız varlık ve yayım zamanı; veri İNDİRİLMEDİ)

Görev kuralı: ağ yalnız resmi kaynaklarda bir serinin var olup olmadığını ve yayım zamanını görmek için. Aşağıdaki sayfalar okundu; hiçbir seri dosyası indirilmedi, repoya hiçbir değer yazılmadı.

## 1. TÜİK — Tüketici Fiyat Endeksi (TÜFE)

| Kontrol | Gözlenen | Kaynak (okunan sayfa) |
|---|---|---|
| Bülten | "Tüketici Fiyat Endeksi, Ağustos 2026", Sayı 58290, **Yayım Tarihi: 03 Eylül 2026 10:00** | `https://veriportali.tuik.gov.tr/tr/press/58290` |
| Sıradaki yayım | "Bu konu ile ilgili bir sonraki haber bülteninin yayımlanma tarihi: **05 Ekim 2026**" (3 Ekim cumartesi → ilk iş günü) | aynı sayfa |
| Temel yıl | **2025=100** ("TÜFE'deki (2025=100) değişim…"; metaveri §3.9 "2025=100"). 2003=100 serisi bu temel yıla zincirlenmiş; metaveri §3.8 "1982 yılından itibaren veri mevcuttur" | `…/tr/press/58290/metadata` §3.7–§3.9 |
| Yayımlama sıklığı | Aylık (metaveri §9) | aynı |
| Zamanlılık | "Nihai sonuçların yayımlandığı tarih ile referans döneminin son tarihi arasındaki fark: ortalama 3 gün"; dakiklik: önceden duyurulan tarih ve saate uyulur (§14) | aynı |
| Revizyon | "Veride revizyon uygulanmamaktadır" (§17.2) | aynı |
| Yayım takvimi | Yıllık Ulusal Veri Yayınlama Takvimi web sitesinde ilan edilir (§8.1–8.2); eski `data.tuik.gov.tr/Bulten/Takvim` adresi 404 (portal `veriportali.tuik.gov.tr`'ye taşınmış) | aynı |
| Seri tablosu | Bülten sayfasında "Tablolar → Tüketici fiyat endeksi ve değişim oranları" (aylık genel endeks) ve "Raporlar → TÜFE metodoloji dokümanı" bağlantıları var | `…/tr/press/58290` |
| Örnek düzey | Ağustos 2026 özel kapsamlı göstergeler tablosunda endeks düzeyleri 132–138 (2025=100); yıllık %31,51 | aynı |

Sonuç: TÜFE genel endeksi (2025=100, aylık, revizyonsuz, sabit takvimli) resmi kaynakta mevcut; ay m'nin endeksi m+1'in 3. günü (hafta sonuna denk gelirse ilk iş günü) 10:00'da yayımlanıyor. Bu, şartnamedeki "T ayının iki öncesi" (m−2) kuralının her zaman yayımlanmış olmasını garanti eder (m−2 endeksi en geç m−1 ayının ~5'inde yayımlanır; T ise m ayındadır).

**Dikkat (2026 temel yıl değişimi):** 2003=100 serisi 2026'da 2025=100'e taşınmış. Uygulama, TÜİK'in 2025=100 zincirlenmiş uzun serisini kullanır; temel yıl ya da zincirleme değişirse yeni veri sürümü = yeni model_id (CLAUDE.md kural 5).

## 2. TCMB — gösterge döviz kurları (alternatif deflatör; seçilmedi)

| Kontrol | Gözlenen | Kaynak |
|---|---|---|
| Bugünkü bülten | `Tarih="25.09.2026" Bulten_No="2026/181"`; USD ForexBuying 48.7901 | `https://www.tcmb.gov.tr/kurlar/today.xml` |
| Arşiv, kohort başlangıcı | `Tarih="02.01.2020" Bulten_No="2020/1"`; USD ForexBuying 5.9478 | `https://www.tcmb.gov.tr/kurlar/202001/02012020.xml` |
| Arşiv, 2021 | `Tarih="04.01.2021" Bulten_No="2021/1"`; USD ForexBuying 7.3602 | `https://www.tcmb.gov.tr/kurlar/202101/04012021.xml` |

Sonuç: günlük, tarihli, arşivli resmi seri; gösterge kur 15:30'da ilan edilir (bilinen kural; bu oturumda ayrıca doğrulanmadı). Deflatör olarak reddedilme gerekçesi şartname §3.2'de.

## 3. TCMB EVDS

`https://evds2.tcmb.gov.tr/…` → `https://evds3.tcmb.gov.tr/` yönlendirmesi; sayfa JavaScript uygulaması, statik metinde seri listesi yok. Seri kodları (TÜFE için TP.FG.J0, kur için TP.DK.USD.A.YTL) bu oturumda EVDS üzerinden DOĞRULANMADI; TÜFE için birincil kaynak TÜİK veri portalı, kur için TCMB `kurlar` XML arşividir.

## 4. Borsa İstanbul

Bu şartname Borsa İstanbul'dan yeni bir seri istemez (XU100 zaten repoda; deflatör olarak reddedildi, §3.2).

# Sade görünüm — onaylı tasarım (UI v2)

Proje sahibi 3 Ekim 2026'da onayladı ("Tamam yapalım bu arayüzü"). Tasarım Claude Design kanvasında üretildi; bu klasör onun repodaki kopyasıdır. Uygulama görevi: `docs/prompts/FAZ9_APP_UI.md`.

Eski arayüz silinmez: uygulamada **Ayrıntılı görünüm** adıyla, kodu ve testleriyle aynen kalır. Sade görünüm varsayılandır.

## Dosyalar

| Yol | Ne |
|---|---|
| `boards/*.dc.html` | Panoların kaynağı (12 pano). Biçim: Design Component (`<x-dc>`, `{{ delik }}`, `<sc-if>`, sınıf içinde `renderVals()`). Çalışma zamanı (`support.js`) repoda yok; dosyalar **referans olarak okunur**, tarayıcıda açılmaz. Stiller satır içidir; renkler aşağıdaki belirteçlerdir. |
| `boards/canvas.json` | Kanvas dizini (pano sırası, başlıklar, boyutlar). |
| `png/*.png` | Panoların durağan görüntüsü (1440 px genişlik). **Yedek yazı tipiyle** çizildi (IBM Plex yüklenmeden); satır kırılmaları uygulamada farklı olabilir. Etkileşimli panolar varsayılan hâlinde: `Sonuc` j = 0, `Arz` j = 3, `Giris` talep sonrası (`Giris_pre.png`: talep öncesi). |

## Panolar

| Pano | Başlık | Eski ekran karşılığı |
|---|---|---|
| `Main` | Monitör | yok (yeni; sicil, sonuç dosyaları ve skorlardan derlenir) |
| `Giris` | Yeni arz girişi | Girdi (§3a) |
| `Sonuc` | Tahmin sonucu | Sonuç (§3b, §3c, §3g varsayımsal j) |
| `Arz` | Analiz (arz sayfası) | Sicil → arz sayfası (§3g resmi görünüm) + kırılma kartı (EK 5 içeriği, makine kaydından) |
| `Dogruluk` | Model performansı | Doğruluk (§3d), zaman-dışı ve D1 sonrası bölümleri |
| `Sicil` | Sicil | Sicil listesi + kayıt künyesi (§3e, §3g) |
| `Dondur` | Resmi kayıt sihirbazı | Dondur sihirbazı (§3e, 6 adım) |
| `D1Sonrasi` | D1 sonrası kayıt | D1 sonrası sihirbazı (EK 3 §6.6) |
| `Kayitlarim` | Kayıtlarım | Kişisel kayıtlar (§3f) |
| `Ayarlar` | Ayarlar ve Hakkında | Ayarlar, Hakkında |
| `Stil` | Stil rehberi | — |
| `Palet` | Palet seçenekleri | — (uygulanan: Safir) |

## Belirteçler (Safir paleti)

| Rol | Değer |
|---|---|
| Zemin | `#0A0F1A` |
| Üst bar | `#0D1423` |
| Pano | `#131C2F`; kenar `#22304A`; köşe 10 px; üst iç ışık `inset 0 1px 0 rgba(255,255,255,0.04)` |
| Kuyu (giriş alanı, segment zemini) | `#0D1423`; giriş kenarı `#2E3F61` |
| Satır çizgisi | `#1A2539`; seçili satır `#16284A` + solda 3 px `#5B9BFF` |
| Metin | birincil `#F4F7FC`, ikincil `#B7C3D7`, not ve eksen `#8C9AB3` |
| Eylem (birincil düğme) | `#2F6FEB`, yazı `#FFFFFF`; etkin sekme alt çizgisi, bağlantı ve odak halkası `#5B9BFF` |
| **Model çıktısı** | `#FFB648` (altın). Yalnız bizim modelimizin çıktısı; kural ve gerçekleşen asla altın olmaz |
| Yukarı, tavan, geçti | `#1ECB8A`; yazı `#5FE4B0`; zemin `rgba(30,203,138,0.17)` |
| Aşağı, taban | `#FF5D6E`; yazı `#FF9AA5`; zemin `rgba(255,93,110,0.15)` |
| Karşılaştırma (basit kural) | `#8C9BB6`; ince çizgi `#50607D` |
| Rejim uyarısı | şerit zemini `#1D140E`, kenar `#47301C`, yazı `#FFC38F`; rozet `#FF8A3D` üzerine `#1F0E05` |

Renk tek başına bilgi taşımaz: renkli her değerin yanında sözcük ya da işaret vardır.

## Yazı

- **IBM Plex Sans**: arayüz metni (400/500/600/700).
- **IBM Plex Sans Condensed**: tablolar, ana sayılar, tarihler (eşit genişlikli rakam, `font-variant-numeric: tabular-nums`).
- **IBM Plex Mono**: yalnız model kimlikleri, dosya adları, sha önekleri.
- Ölçek: sayfa başlığı 26/700; pano başlığı 16/600 + 13 alt satır; tablo 14; not 12; ana sayı 34–46 Condensed 600.
- Etiketler cümle düzeninde. BÜYÜK HARF yalnız hisse kodlarında.

## Bileşenler

- **Üst bar:** marka · sekmeler (Monitör, Analiz, Model performansı, Sicil, Kayıtlarım) · kod arama · mod göstergesi (Senaryo / Resmi kayıt / Resmi kayıt hazırlanıyor / Doğruluk, salt okuma) · veri tarihi ve yerel saat · "Yeni arz gir" (birincil) · Ayarlar düğmesi (dişli).
- **Veri şeridi:** özet okumalar dikey çizgiyle ayrılır; kart değildir.
- **Pano:** birincil içerik panoda; ikincil bilgi (olay akışı, üretimdeki modeller, arşiv) doğrudan zeminde, ince çizgiyle.
- **Hüküm işaretleri:** ✓ yeşil, ≈ gri, × kırmızı, ◐ kısmen. Hüküm metni uygulamada **skor dosyasındaki `verdict`** alanıdır (U19); sade açıklama ayrı satırdadır.
- **Seri hesaplayıcı** ("Seri j gün sürdüyse yarın ne olur?"): 0–9 düğmeleri, D1–D10 şeridi (geçmiş günler yeşil, yarın altın kesikli), dört okuma (yarın da tavan, beklenen kalan gün ve koşullu medyan, en az 5 gün, 10 gün), koşullu ve koşulsuz eğri. Resmi görünümde bültende gözlenen seri ve "Gözlenene dön".
- **Giriş alanı:** etiket, sağa hizalı Condensed değer, birim eki, altında okunur tekrar ("312,5 milyon pay", "17 Eylül 2026, Perşembe") ve geçerlilik işareti.
- **Adım göstergesi** (sihirbazlar): tamamlanan ✓, etkin mavi daire, bekleyen gri.
- **Alt bilgi:** her ekranda `DISCLAIMER` ve sürüm.

## Hareket

Tek açılış anı: çizgiler soldan sağa çizilir, çubuklar tabandan büyür, noktalar en son belirir (yalnız CSS; `prefers-reduced-motion` açıksa hiç oynamaz). Paneller kaymaz. Kullanıcının açtığı şey (satır açıklaması, aşama değişimi) kısa geçişle görünür.

**Uygulamada sayı sayma animasyonu yoktur:** tasarımdaki sayaç ön uçta aritmetik ister (U25, `no_frontend_math`).

## Tasarımdan uygulamaya geçerken (bağlayıcı)

1. Panolardaki sayılar **örnektir**. NETGL ve sicilin 3 Ekim hâlinden alındı; uygulamada her sayı Rust komutundan ya da skor ve kayıt dosyasından gelir.
2. Sayı biçimleri SPEC_APP §4'e uyar (ör. olasılık 0 ondalık yüzde). Tasarımdaki `0,499` gibi yazımlar biçim örneği değildir.
3. Ön uç hesap yapmaz. Tasarımdaki şu öğeler uygulamada **çizilmez** ya da sayımla değiştirilir (orkestratör ölçtü):
   - "Ortalama seri 3,43 / modelin ortalaması 3,67" (ortalama; U25) → sayım okumaları;
   - "model hatası %25 daha düşük" (oran) → yalnız iki değer yan yana;
   - Monitör özet cümlesindeki "en güçlü seyir" → yok;
   - "BIST kapalı" göstergesi → yok (veri tarihi kalır);
   - Analiz'deki işlem adedi çubukları → işlem sayısı sonuç dosyasında var (`trade_count_raw`); çizildi (FAZ9_UI_FIX);
   - Model performansındaki kalibrasyon grafiği ve D1 sonrası geçmiş test satırları → skor dosyalarında yok;
   - sayı sayma animasyonu → yok.
4. Ana ekran kapısı veri-güdümlüdür: bir sayı öne çıkan olarak ancak önceden ilan edilmiş birincil hücresinin `verdict`'i "geçiyor" ise görünür. Aksi hâlde ilgili panelde "≈ fark net değil" işaretiyle durur (ör. V1.5 D10 arz üstü olasılığı).
5. `Kayitlarim` panosundaki satır **örnek**tir; uygulama gerçek kişisel kayıtları listeler.

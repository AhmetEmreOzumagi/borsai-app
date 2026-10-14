# Bant ve baz fiyat doğrulaması — Pay Piyasası Prosedürü rev. 54 (KARARLAR C5)

Görev: BORSAI_FAZ8_BREAK_IMPL_20261001, adım 0b. Tarih: 2026-10-01. Soru (SPEC_BREAK_V0 §1.3 (i), §14-5; KARARLAR C5): 21.09.2026
revizyonu günlük fiyat marjını (±%10), limitlerin fiyat adımına yuvarlanmasını ya da ilk gün baz fiyat kuralını değiştirdi mi?
Bu sabitlere yalnız yastık kuralı (§2.4) ve ürün karşılaştırıcısının eşiği (§5.1) dayanır; model özellikleri dayanmaz.

**Sonuç: doğrulandı — 21.09.2026 revizyonları bant, yuvarlama ve baz fiyat kurallarını değiştirmedi.** İki belgenin bu tarihli
değişiklik cetvelleri yalnız pazar belirleme kriterlerini (likidite, volatilite, özsermaye) değiştirir. §2.4 ve §5.1 sabitleri
(`MARGIN = "0.10"`, içe yuvarlama, D1 baz fiyatı = arz fiyatının adıma oturtulmuş hali, adım tablosu) olduğu gibi kalır.

Bir çekince (sonucu değiştirmez): belgedeki **genel** marj kuralı pazara göredir (Yıldız ±%20, Ana ±%15, Alt ±%10). Bütün
pazarlarda ±%10 uygulaması, belgenin dipnotunda adı geçen "ikinci bir duyuruya kadar" geçerli duyurulardan gelir (2020/20,
2020/21, 2020/50, 2025/38860). Bu duyurular bu görevin ağ izni dışındadır ve açılmadı. Bu dipnot ve tablo 21.09.2026'da değişmedi.
H99'un 85 kırılma gününde THM limitleri ±%10'dur (alt limit / referans 0.90000…0.90183, `ekler/profil_kirilma.txt` §7). Canlıda
`BAND_RULE_MISMATCH` koruması (§1.3) her kırılma akşamı bu oranı THM'den ölçer.

## Kaynak dosyalar

Dosyalar repoya girmedi. Metin macOS PDFKit ile çıkarıldı (`PDFDocument.string`, sayfa sayfa); bu makinede `pdftotext` yoktu.

| Dosya | Kaynak | Bayt | Sayfa | sha256 |
|---|---|---|---|---|
| `pay-piyasasi-proseduru.pdf` | `https://www.borsaistanbul.com/files/pay-piyasasi-proseduru.pdf` (HTTP 200, 2026-10-01) | 6 096 847 | 380 | `675881bfad6268418fb53d8e1db692172393e37c8d51d013defa87f391333a2d` |
| `borsa-istanbul-as-pay-piyasasi-yonergesi.pdf` | `https://www.borsaistanbul.com/files/borsa-istanbul-as-pay-piyasasi-yonergesi.pdf` (HTTP 200, 2026-10-01) | 623 294 | 40 | `52f964d5b38bf03700f33ab2d2feb265785dc500373bfc51c16424292f25fb2f` |

Aşağıda prosedür "P", yönerge "Y" diye anılır. Alıntılar kısa tutuldu; sayfa numaraları PDF sayfasıdır.

## 1. Revizyon numarası ve tarihi

- P, s. 1 (kapak): "Revizyon Tarihi 21/09/2026", "Revizyon Numarası 54", "Sürüm: 3.34".
- Y, s. 1 (kapak): "Revizyon Tarihi 21/09/2026", "Revizyon Numarası 18".

## 2. Rev. 54 (21.09.2026) maddeleri

- P'nin s. 242–255'teki özet revizyon tablosu ("DÜZENLEME ÜZERİNDE GERÇEKLEŞTİRİLEN SON DEĞİŞİKLİKLER") rev. 53'te
  (05/01/2026, EK 3 varantlar) biter. Rev. 54 yalnız belge sonundaki karşılaştırma cetvelinde yer alır.
- P, s. 376: "21.09.2026 tarihi itibarıyla düzenleme üzerinde yapılan değişiklikler…". Cetvel başlığı "Revizyon No:54, Sürüm 3.34
  ile yapılan değişiklikler". Tek bölüm başlığı "4.2 İkincil Piyasa İşlemleri ve Seans Saatleri".
- Cetvelin içeriği (s. 376–380):
  - "Tablo-3: Pazarları Belirleme Kriterleri": Yıldız ve Ana Pazar likidite eşikleri (0,15 / 0,5 → 500 / 1000). Yıldız'a
    "Volatilite" ve "Özsermaye" kriterleri eklendi.
  - Kriter açıklamaları: likidite tanımı Amihud oranından emir defteri likidite maliyetine (baz puan) geçti. Volatilite ve
    özsermaye kriterleri tanımlandı.
  - İstisnalar ve değerlendirme esasları: yeni işlem görmeye başlayan şirketler ilk 3 ayda pazar değerlendirmesine "dahil
    edilmeyebilir".
  - Cetvelde Tablo-4 ("Pazarlarda Uygulanacak İşlem Esasları"; fiyat marjı satırı), §5.1.8 (baz fiyat), §5.1.9 (fiyat adımları),
    §5.1.11 / §5.6.2 (fiyat değişme sınırları) ve §4.1.1 (halka arzda baz fiyat) **yoktur**. P'nin metninde "Tablo-4" bu cetvelde
    geçmez; yalnız içindekiler, s. 26 ve rev. 17/18 (2021) cetvellerinde geçer.
- Y, s. 39–40: "21/09/2026 tarihinde Revizyon 18 ile belgede aşağıdaki değişiklikler yapılmıştır". Tek madde "MADDE 37 –
  Pazarları Belirleme Kriterleri" (aynı likidite, volatilite ve özsermaye değişikliği). Madde 18 (baz fiyat), Madde 19 (fiyat
  adımları), Madde 20 (fiyat değişme sınırları) ve Madde 39 tablosu (fiyat marjı) cetvelde yoktur.

## 3. Fiyat marjı ve ±%10 uygulaması

- P, s. 26, Tablo-4 "Pazarlarda Uygulanacak İşlem Esasları": "Fiyat Marjı %20 %15 %10 %10 %10" (Yıldız, Ana, Alt, YİP, PÖİP).
  Dipnot 10: "Tabloda belirtilen işlem esasları genel kurallardır, ikinci bir duyuruya kadar geçerli olduğu ilan edilen
  duyurularda (2020/20, 2020/21, 2020/50, 2025/38860) yer alan kurallar…" yayımlanmaktadır.
- P, s. 53, §5.1.11: fiyatlar baz fiyattan "Paylarda Yıldız Pazar'da±%20'den, Ana Pazar'da ±%15'ten; Alt Pazar, YİP ve PÖİP'te
  ±%10'dan" farklı olamaz (genel kural; Tablo-4 ile aynı).
- Y, s. 17, Madde 39 tablosu: "Fiyat Marjı %20 %15 %10 %10 %10" (aynı satır). Y, s. 10, Madde 20 (1): oranı Yönetim Kurulu
  belirler; (4): Genel Müdür sınırları "kaldırabilir veya değiştirebilir".
- **Okuma:** belgelerde genel kural pazara göredir. ±%10'un bütün pazarlarda uygulanması dipnot 10'daki duyurulardandır. Bu
  satırlar ve dipnot 21.09.2026'da değişmedi (§2). H99'da ölçülen limitler ±%10 ile birebirdir (§1.3; alt limit zinciri
  85/85). Duyuru metinleri açılmadı (ağ izni yalnız bu iki PDF).

## 4. İlk gün baz fiyat kuralı

- P, s. 17, §4.1.1 (Sürekli İşlem Yöntemi): birincil piyasadaki ilk işlem günü baz fiyatı "izahnamede yer alan halka arz
  fiyatının en yakın fiyat adımına yuvarlanmasıyla bulunan fiyattır".
- P, s. 17: ikincil piyasadaki ilk seansın baz fiyatı "birincil piyasadaki son seansta oluşan kapanış fiyatı olarak alınır"; o
  seansın alt ve üst sınırları "bu baz fiyat üzerinden hesaplanır".
- P, s. 51, §5.1.8: "BISTECH Sistemi'nde önceki işlem gününün kapanış fiyatı, baz fiyat olarak belirlenmektedir." Y, s. 9,
  Madde 18 (1): aynı tanım (Yönetim Kurulu kararına göre önceki seans kapanışı ya da ağırlıklı ortalama).
- **Okuma:** D1 baz fiyatı = arz fiyatının adıma oturtulmuş hali (sabit fiyatlı satışta birincil piyasanın son kapanışı), sonraki
  günler önceki kapanış (SPEC_CEILING_PATH_V0 §2, `predict_path.snap` / `limit_path`; H99'da referans_b = kapanış_{b−1} 67/67).
  21.09.2026 cetvellerinde bu bölümler yoktur.

## 5. Limitlerin fiyat adımına yuvarlanması

- P, s. 53, §5.1.11: "yuvarlama, işlem yapılabilecek fiyat aralığını daraltıcı şekilde içeri doğru yapılır… üst fiyat limiti
  bulunurken aşağı adıma, alt fiyat limiti bulunurken yukarı adıma".
- P, s. 92, §5.6.2: alt sınır "en yakın yukarı fiyat adımına", üst sınır "en yakın aşağı fiyat adımına" yuvarlanır.
- P, s. 52, §5.1.9 Tablo-7 (paylar): 0,010–19,999 → 0,010; 20–49,999 → 0,020; 50–99,999 → 0,050; 100–249,999 → 0,100;
  250–499,999 → 0,250; 500–999,999 → 0,500; 1000–2499,999 → 1,000; 2500 ve üzeri → 2,500. Bu tablo
  `predict_path.TICK_TABLE` ile birebirdir. Adım, "baz fiyata bağlı olmaksızın ilgili fiyat seviyesine göre" belirlenir
  (`lower_limit`/`upper_limit` adımı yuvarlanacak değerin kendi seviyesinden alır).
- **Okuma:** `predict_path.lower_limit` (CEIL_TO_TICK_AT_LIMIT_LEVEL) ve `upper_limit` (FLOOR_TO_TICK_AT_LIMIT_LEVEL) bu kurallarla
  aynıdır. 21.09.2026 cetvellerinde bu bölümler yoktur.

## 6. Sonuç ve etkisi

| Kural | 21.09.2026'da değişti mi? | §2.4 / §5.1 sabiti |
|---|---|---|
| Fiyat marjı (Tablo-4, §5.1.11, Y Madde 20/39) | Hayır | `MARGIN = "0.10"` aynen |
| İçe yuvarlama (§5.1.11, §5.6.2) | Hayır | `lower_limit` yukarı adım, `upper_limit` aşağı adım aynen |
| Fiyat adımı tablosu (Tablo-7) | Hayır | `TICK_TABLE` aynen |
| İlk gün baz fiyat (§4.1.1, §5.1.8, Y Madde 18) | Hayır | `snap(P)` aynen |

Görev kuralı ("bant ya da baz fiyat kuralı değiştiyse DUR") tetiklenmedi; görev devam etti. Dondurmadan önce isterse orkestratör
dipnot 10'daki duyuruları ayrıca doğrulayabilir. Yönetim kurulu ±%10 duyurusunu kaldırırsa Yıldız ve Ana Pazar paylarında limitler
değişir; bu durumda `BAND_RULE_MISMATCH` satırı işaretler ve yastık rozetini gizler (§1.3).

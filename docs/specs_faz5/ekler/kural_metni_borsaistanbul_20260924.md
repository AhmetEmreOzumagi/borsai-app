# Kural metni alıntıları: Borsa İstanbul Pay Piyasası seans saatleri, bülten ve fiyat marjı

Görev: BORSAI_FAZ5_FABLE_POST_D1_SPEC_20260924. Erişim 2026-09-24 (curl, HTTP 200). Yalnız KURAL metni indirildi; hiçbir fiyat ya da bülten verisi indirilmedi. Alıntılar etiketler temizlenerek aynen alınmıştır; "[…]" atlanan kısımdır.

## Kaynaklar

| # | Kaynak | sha256 (indirilen dosya) | Not |
|---|---|---|---|
| K1 | https://www.borsaistanbul.com/piyasalar/pay-piyasasi/piyasa-isleyisi (HTML, 154 817 bayt) | `e79abb77ed2d6456337e6ae926b75c1b30e4e1b2dc2d93adf24d56a051c14942` | Faz 4 ekindeki sayfanın 2026-09-24 sürümü (Faz 4'te sha `af197633…`; sayfa değişmiş, fiyat marjı/adım hükümleri aynı metin). Kapanış seansı saatleri burada. |
| K2 | https://www.borsaistanbul.com/piyasalar/pay-piyasasi/islem-saatleri (HTML, 89 719 bayt) | `1565c707e07f98bf59804a946997606e3ac04ff06946917deaec8fba3f6d39f3` | Saat çizelgesi sayfada GÖRSEL olarak yer alıyor (`1-pay-piyasasi-surekli-islem-yontemi-(tam-is-gunlerinde).png` vb.; HTML'de "Görsel kaldırıldı"); metin olarak yalnız dipnotlar okunabildi. |
| K3 | https://www.borsaistanbul.com/files/pay-piyasasi-proseduru.pdf (PDF, 6 096 847 bayt, 380 sayfa) | `675881bfad6268418fb53d8e1db692172393e37c8d51d013defa87f391333a2d` | "Pay Piyasası Direktörlüğü Prosedür". Metin PDFKit ile çıkarıldı. Seans saatleri Ek-9 (s. 154–155), Tablo-10 (s. 56–57), §4.2.11 (s. 38–39), §5.10 Günlük Bülten (s. 99), Ek-10 seans akışı (s. 156). |

## A. Seans saatleri — tam iş günleri (K3, Ek-9 "Pay Piyasası'nda Pazarlar ve Seans Saatleri Çizelgeleri", s. 154)

> TAM İŞ GÜNLERİNDE — PAZARLAR: Yıldız Pazar, Ana Pazar, Alt Pazar, Yapılandırılmış Ürünler ve Fon Pazarı (YÜFP)*, Yakın İzleme Pazarı (YİP), Girişim Sermayesi Pazarı (GSP), Piyasa Öncesi İşlem Platformu (PÖİP), Emtia Pazarı (EP) — SAATLER: 09:40 – 18:10
>
> SEANSIN BÖLÜMLERİ — SAATLER
> a) Açılış (Varant, Sertifika ve YPAH'ler hariç tüm yatırım araçları ile tüm pazarlar dâhil) 09:40 – 10:00
> i) Emir Toplama Süreci 09:40 – 09:55
> ii) Açılış Fiyatının Belirlenmesi 09:55 (+)**
> b) Sürekli İşlem Bölümü 10:00 – 18:00
> c) Kapanış (Varant, Sertifika ve YPAH'ler hariç tüm yatırım araçları ile tüm pazarlar dâhil) 18:00 – 18:07
> i) Kapanış Marj Yayını 18:00 – 18:01
> ii) Emir Toplama 18:01 – 18:05
> iii) Kapanış Fiyatının Belirlenmesi 18:05 (+)**
> ç) Kapanış Fiyatından / Tek Fiyattan İşlemler Bölümü 18:07 – 18:10
> i) Marj Yayını 18:07 – 18:08
> ii) Kapanış Fiyatından / Tek Fiyattan İşlemler 18:08 – 18:10
> […]
> * : BYF'ler için açılış emir toplama süreci 09:40 - 09:56 (+) arasındadır. Varantlar ve sertifikalar için seans başlangıç saati 10:00:10'dur.
> ** : (+) İşlemlerin tamamlanmasına bağlı olarak değişebilecek bir saati ifade eder.

K1 aynı kapanış saatlerini verir: "Kapanış seansı aşamalarının süreleri ve saatleri aşağıdadır: • Emir toplama aşaması – (4 dakika, 18:01 – 18:05) • Fiyat belirleme ve kapanış seansı işlemleri aşaması – (2 dakika, 18:05 – 18:07) • Kapanış fiyatından/ tek fiyattan işlemler aşaması – (2 dakika, 18:08 – 18:10)".

K2 dipnotu (tek okunabilen metin): "Emir toplama süreci, belirtilen saatlerden sonra 30 saniye içerisinde rastlantısal olarak kesilmektedir. Açılış emir toplama bölümü BYF'ler özelinde 09:40 - 09:56 arasıdır."

## B. Seans saatleri — yarım iş günleri (K3, Ek-9, s. 155)

> YARIM İŞ GÜNLERİNDE — […] SAATLER: 09:40 – 12:40
> a) Açılış […] 09:40 – 10:00; i) Emir Toplama Süreci 09:40 – 09:55; ii) Açılış Fiyatının Belirlenmesi 09:55 (+)**
> b) Sürekli İşlem Bölümü 10:00 – 12:30
> ç) Kapanış […] 12:30 – 12:37; i) Kapanış Marj Yayını 12:30 – 12:31; ii) Emir Toplama 12:31 – 12:35; iii) Kapanış Fiyatının Belirlenmesi 12:35 (+)**
> d) Kapanış Fiyatından / Tek Fiyattan İşlemler Bölümü 12:37 – 12:40

K3 §4.2.11 (s. 38): "BISTECH geçişi ile birlikte tüm güne yayılan tek bir seans yapılmaktadır. Resmî/idari tatil veya yarım iş günü olması nedeniyle yarım seans yapılacak günlerde işlemler, kapanış bölümü ile bitirilecektir."

K3 §4.3 (s. 39): "[…] Genel Müdür, […] seansın açılış ve kapanış saatlerini değiştirmek, işlemleri durdurmak veya kısıtlamak, günlük fiyat değişim limitlerini değiştirmek gibi geçici değişiklikler yapmaya […] yetkilidir." ve "[…] seans yapılacak günler ve seans saatleri piyasa, pazar, platform ve sistem bazında Genel Müdür tarafından belirlenebilir ve KAP'ta duyurulur."

Ek-10 seans akış çizelgesi (K3, s. 156, "PAY, EMTİA SERTİFİKASI (Sürekli İşlem)") ilk üç satır: "1 P_MARJ_YAYIN 07:00:00 — 2 P_ARA 07:30:00 — 3 P_ACILIS_EMIR_TPL 09:40:00". Uyarı (aynı sayfa): "Çizelgelerde yer alan saat ve seans bilgileri, bu düzenleme hazırlandığında geçerli olan son bilgilere göre verilmiştir. Bu bilgilerin değişebileceği hususu göz önünde bulundurulmalıdır."

## C. Günlük Bülten (K3 §5.10, s. 99)

> BISTECH Sistemine geçişle birlikte BİAŞ internet sayfasında "excel" formatında yayınlanan Pay Piyasası Günlük Bültenine yeni alanlar eklenmiştir ve "csv" formatına dönüştürülmüştür. Söz konusu Bültende bulunan alanlar ve açıklamaları, BİAŞ internet sayfasının (https://www.borsaistanbul.com/tr/sayfa/441/teknik-dokumanlar) adresinde bulunan "Borsa İstanbul PP Veri Bildirim ve Kabul Formatları" dosyasında yer almaktadır.

K3 Tanımlar (s. 7): "Borsa Bülteni : Pay Piyasası tarafından yayımlanan günlük bülten". K3 §5.8.4 (s. 99): açığa satış işlemleri "Günlük Bülten'de pay bazında […] ilan edilir".

**Bülten yayım SAATİ kural metninde yoktur** (K1, K2, K3'te arandı: "bülten", "Günlük Bülten", "yayım"). Ölçüm [ÖLÇTÜM, `data/raw/bist/MANIFEST.csv` `http_last_modified`, Europe/Istanbul'a çevrilmiş; bu görev yalnız zaman damgalarını okudu, bülten içeriğini okumadı]:
- THB (fiyat bülteni): 33 dosya (2026-08-06 … 2026-09-21), sunucu "son değişiklik" saati 18:25 – 18:40, hepsi bültenin kendi seans gününde (medyan ≈ 18:28).
- THM (marj/limit bülteni): 26 dosya (2026-08-17 … 2026-09-21), 08:01 – 08:03, hepsi kendi seans gününün sabahı (Ek-10'daki 07:00 marj yayınıyla uyumlu; dosya sunucuya ~1 saat sonra düşüyor).

## D. Fiyat marjı ve fiyat adımı (K1; Faz 4 ekiyle aynı metin)

> "Baz fiyat" bir payın gün boyunca işlem görebileceği alt ve üst fiyat limitlerinin belirlenmesine esas teşkil eden fiyattır. Baz fiyat bir önceki işlem gününün kapanış fiyatı ile hesaplanır.
> […] Fiyat marjı Yıldız Pazar, Ana Pazar, borsa yatırım fonları, gayrimenkul sertifikaları, gayrimenkul yatırım fonları ve girişim sermayesi yatırım fonlarında %10'dur.
> Fiyat limitleri hesaplanırken yuvarlama işlemi içeri doğru yapılacaktır: Üst fiyat limiti bulunurken yuvarlama aşağı adıma, alt fiyat limiti bulunurken yuvarlama yukarı adıma yapılacaktır.

Fiyat adımı tablosu Faz 4 ekindedir (`docs/specs_faz4/ekler/kural_metni_borsaistanbul_20260922.md`); değişmemiştir.

## E. Bu görevde kural metninden türetilen tanımlar

- **D2 açılış anı** = D_1'i izleyen ilk resmi seans gününde (tam ya da yarım gün fark etmez) saat **09:40:00 Europe/Istanbul** (Ek-9 "Emir Toplama Süreci 09:40"). Bu andan itibaren D2 emir defteri (teorik açılış fiyatı ve miktarı) piyasaya görünür; bu yüzden POST_D1 kaydının zaman kanıtı bu andan ÖNCE olmalıdır (SPEC_POST_D1_V0 §7).
- **D1 bülteninin kullanılabilirlik penceresi** [ÇIKARIM]: THB ≈ 18:30 (ölçüm) → ertesi resmi seans 09:40 (kural). Yaklaşık 15 saat; hafta sonu ve tatilde daha uzun.
- **D1 kapanış fiyatının oluştuğu son an** = 18:10 (Ek-9 ç-ii). Kapanış fiyatı 18:05(+)'te belirlenir; 18:08–18:10 yalnız kapanış fiyatından işlem.
- **Yarım gün D1**: seans 09:40–12:40; alanlar aynı bültende aynı adlarla gelir (H99'da yarım gün D1 yok; `profil_d1.txt` §1).

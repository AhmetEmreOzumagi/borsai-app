# Tavan serileri kısaldı, piyasa rejimi belirleyici oldu

Borsa İstanbul'da halka arz getirisi ilk günde görünmez; tavan serisinin uzunluğunda ortaya çıkar. Bu uzunluk 2023'ten bu yana hem kısaldı hem dağıldı. 2023'te seriler 5–15 gündü (rekor Ofis Yem, 15 gün). 2025'te adı geçen 12 arzda medyan 2,5–3 güne indi. 2026'da dağılım iki tepeli oldu: bir grup 7–10 tavan yaptı, bir grup ilk gün tabana indi. Piyasa dört dalgadan geçti. 2023'te 54–56 arz yapıldı ve arz başına ~2,2 milyon (tekil olmayan) katılımcı vardı. 2024'te 33–34 arz yapıldı ve katılım ikinci yarıda arz başına ~500 bine çöktü. 2025'te 16–19 arz yapıldı ve 21 Şubat–11 Eylül arasında hiç listeleme olmadı. 2026'nın ilk sekiz ayında 34 arz 82,4 milyar TL topladı; Temmuz 12 arzla rekor kırdı. Arz fiyatının altına düşme oranı kohorta ve rejime göre değişti: 2024 ve 2025 kohortlarında aylar sonra ~%41, 2026 kohortunda Temmuz sonunda %18, 1 Ekim'de zayıf bir izleyiciye göre ~%64. Hiçbir dış kaynak bu oranı D10'da ölçmüyor; ölçüm ekibin kendi verisiyle yapılmalı. Modeller için en sağlam bulgu mekaniktir: ±%10 bantta D1'den başlayan 6 ya da daha uzun bir tavan serisinden sonra D10 kapanışının arz fiyatının altında olması aritmetik olarak imkânsızdır. Bu yüzden D10 düşüş riski kısa serilerde ve bozulmadan sonraki taban kilitlerinde toplanır. Türkiye'deki tek güçlü regresyon çalışmasının (154 arz, 2020–2023) bulguları şöyle: büyük arz, yurt içi kurumsal pay ve kredili işlem bolluğu ilk getiriyi düşürüyor; yabancı kurumsal pay ve 2023 eşit dağıtım kuralı yükseltiyor. Uluslararası fiyat limiti literatürüne göre ise kapanışta limite kilitlenme, özellikle taban yönünde, ertesi güne taşınıyor. Bugünün koşulunun eğitim verisinde karşılığı yok. Eylül 2026 fon krizinde 130 fon tasfiyeye alındı, Tera Yatırım'ın faaliyetleri durduruldu ve BIST100 Eylül'de %16,65 düştü. Eğitim kümesinde 2025 Mart şoku hiçbir arzın ilk on seansına denk gelmedi; 2026 savaş şoku yalnız ~3 arza denk geldi. Canlı sicilde kalibrasyon kayması beklenmeli.

*Okuma anahtarı:*
- **[R]**: resmî metin, birincil veri (TCMB, TÜİK, KAP, BIST, SPK karar metni, TSPB) ya da hakemli çalışma.
- **[B]**: basın, aracı kurum ya da danışmanlık iddiası. MKK verisinin basından aktarılması da buna dahil.
- **[Ç]**: çıkarım ya da bu rapor için yapılmış hesap.
- **[P]**: projenin kendi ölçümü (`claude/STRATEJI.md`, `claude/HANDOFF.md`); dış kaynakla doğrulanmadı.

Bazı hakemli çalışmalar yalnız özet düzeyinde okunabildi ve metinde öyle işaretlendi. Proje kuralı gereği buradaki her sayı modele girmeden önce repo verisinde yeniden ölçülmelidir.

## Modeller için yedi kısa cevap

| Soru | Kısa cevap | Kanıt |
|---|---|---|
| İlk gün getirisi ne kadar? | Fiyat bandı nedeniyle ~+%9,95 ile sınırlı (Arf Bio: 19,50 → 21,44 TL). Gerçek "ilk getiri" ilk tavan-dışı kapanışa kadar ölçülmeli. | [R] kural, [B] örnek |
| Seri ne kadar sürüyor? | 2023: 5–15 gün. 2025: medyan 2,5–3 (n=12, liste eksik). 2026: iki tepeli. Proje ölçümü: 2021'de ortalama 3,4 gün, 2023'te 7,2 gün. | [B], [Ç], [P] |
| Seri nasıl bozuluyor? | İçeriden satış ve açığa satış yok. Arz sahiplerinin ve ikincil alıcıların alış kuyruğu tükeniyor. Arz bolluğu seriyi kısaltıyor. VBTS 1. kademe (kredili işlem yasağı) seans ~6–9'da geliyor. | [R] kurallar, [B] vakalar, [Ç] mekanizma |
| Bozulunca ne oluyor? | Kısa vadede yön sürüyor: Çin'de tabanda kapanan günden sonraki gün ~%86 aynı yön. Orta vadede geri dönüş var. Türkiye için nicel çalışma yok. | [R] uluslararası, [B] Türkiye |
| D10'da arz altı neye bağlı? | Seri uzunluğu (mekanik), arz büyüklüğü, piyasa yönü, takvim yoğunluğu, ek satış [P], fiyat istikrarı. | karışık |
| Hangi kural dönemi bölüyor? | Eğitim penceresinde tek dağıtım kırılması 19.09.2024. ±%10 bant, arz paylarında açığa satış yokluğu ve bireysele eşit dağıtım sabit. | [R] |
| Şimdi farklı olan ne? | Fon krizi, aracı kurum riski, arz bolluğu, yeni SPK öncelik kuralı ve 21.09.2026 tarihli BIST mevzuat revizyonu. | [R], [B], [Ç] |

## 2023'ten 2026'ya dört dalga: çılgınlık, soğuma, duruş, rekor

Arz ve talep birlikte dalgalandı. Her dalgayı bir makro şok ya da SPK'nın onay temposu bitirdi.

**2023 seçim sonrası "çılgınlık" yılıydı.** 5 Eylül'e kadar BIST100 yılbaşına göre **+%49,5** yükselmiş, CDS 370'e inmiş ve 32 arz ~43 milyar TL toplamıştı ([Cumhuriyet](https://www.cumhuriyet.com.tr/ekonomi/borsa-istanbulda-halka-arz-cilginligi-yasaniyor-2116841)) [B]. MKK verisine göre yıl **56 arz, 79,79 milyar TL ve 123,9 milyon tekil olmayan katılımcı** ile kapandı ([Paratic](https://paratic.com/halka-arzin-2023-bilancosu-aciklandi/)) [B]. PwC de 56 arz ve 3,26 milyar dolar veriyor ([PwC](https://www.pwc.com.tr/tr/Hizmetlerimiz/danismanlik/pdf/halka-arz-raporu_2025.pdf)) [B]. TSPB ise **54 arz ve 63,3 milyar TL** sayıyor ([TSPB Bahar 2025](https://tspb.org.tr/wp-content/uploads/2025/05/Gosterge_Bahar_2025-1-1.pdf)) [R]. Fark büyük olasılıkla listeleme tarihi ya da pazar kapsamı gibi tanım farklarından geliyor [Ç].
- Katılım rekoru Eylül 2023'te Reeder'in **4,26 milyon** başvurusuydu ([Capital](https://www.capital.com.tr/haberler/tum-haberler/reeder-teknolojinin-halka-arzinda-rekor-kirildi)) [B].
- Seriler yıl içinde de düz gitmedi. Mayıs 2023'te BigChefs tek tavan yaptı, Bien Yapı hiç yapmadı ([Diken](https://www.diken.com.tr/?p=1314284)) [B]. Sonra seriler geri döndü.
- Aralık 2023'te basın "çılgınlık bitti mi" diye soruyordu. Ekos 12, 1000 Yatırımlar 9 tavan yapmıştı, ama son arzlar yılın başındaki "ortalama 10 günlük" serileri tutturamıyordu ([Paratic](https://paratic.com/cilginlik-bitti-mi-yeni-halka-arzlar-tavanda-duramiyor)) [B].
- Projenin eğitim penceresi (2023-09 sonrası) bu sıcak dönemin kuyruğunda başlıyor.

**2024 soğuma yılıydı.** Arz sayısında kaynaklar ayrışıyor:
- MKK: 33 arz ve 57,31 milyar TL ([Bloomberg HT](https://www.bloomberght.com/mkk-2024-yilinda-33-halka-arzdan-57-31-milyar-tl-toplandi-3739188)) [B].
- Akalın Finans: 34 arz ([Foreks](https://www.foreks.com/haber/detay/677cebf134d8dd2293fc0bfe/PICNEWS/tr/akalin-finans-halka-arz-egilimleri-2024-raporu-orta-olcekli-sirketler-ve-sanayi-sektoru-halka-arzlarda-one-cikti/)) [B].
- TSPB Yaz 2026: 22 pay arzı ve 1 yatırım ortaklığı ([TSPB Yaz 2026](https://tspb.org.tr/wp-content/uploads/2026/09/Gosterge_Yaz_2026_.pdf)) [R]. Bu, aynı birliğin Bahar 2025 sayısındaki "34" ile çelişiyor.

Katılım, Akalın Finans'a göre ilk yarıdaki arz başına ~2,5 milyondan ikinci yarıda ~500 bine indi [B]:
- Altınay Savunma Mayıs'ta 3,63 milyon katılımcı topladı ([Borsagündem](https://www.borsagundem.com.tr/halka-arzlarda-katilimci-sayisi-dusuyor)) [B].
- Temmuz başındaki arzlarda katılım 540 bine düştü ([Bloomberg HT](https://www.bloomberght.com/halka-arzlar-tavansiz-kaldi-katilimcisi-azaldi-2356021)) [B].
- Ekim'de Bin Ulaşım 279 bin katılımcıda kaldı ([Ekonomim](https://www.ekonomim.com/kose-yazisi/halka-arzlara-katilimlar-dusen-borsayla-geriledi/773355)) [B].

Halka arz endeksi üç ayda 117.939'dan 99.526'ya geriledi. Basın, düşük talep katı yüzünden küçük kârların bile satışı tetiklediğini yazdı ([Hürriyet](https://www.hurriyet.com.tr/ekonomi/halka-arzda-secici-olmak-sart-42462512)) [B]. Bu çöküş Mart 2025 şokundan önce yaşandı: BIST100 Temmuz 2024'teki ~11.200 zirvesinden Aralık'ta 9.830'a gerilemişti ([TSPB Bahar 2025](https://tspb.org.tr/wp-content/uploads/2025/05/Gosterge_Bahar_2025-1-1.pdf)) [R].

**2025 "fren yılı" oldu.**
- SPK 6 Şubat'tan sonra yeni arz onayı vermedi ([Finansopia](https://www.finansopia.com/ekonomi/spk-halka-arzlara-ara-mi-verdi/)) [B].
- 19 Mart'taki siyasi şoktan sonra BIST100 17 Mart'taki 10.862'den 27 Mart'ta 9.612'ye düştü (**−%11,5**). Gösterge tahvil faizi iki günde ~%35'ten ~%45'e çıktı ([TSPB Kış 2026](https://tspb.org.tr/wp-content/uploads/2026/03/Gosterge_Kis_2026_-1.pdf)) [R].
- Politika faizi 18 Nisan'da %46'ya çıkarıldı ([TCMB](https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Temel+Faaliyetler/Para+Politikasi/Merkez+Bankasi+Faiz+Oranlari/1+Hafta+Repo)) [R].
- 21 Şubat (Bulls GSYO) ile 11 Eylül (Dof Robotik) arasında hiç listeleme olmadı ([Yeni Şafak](https://www.yenisafak.com/halka-arz-takvimi-2025-hangi-sirketler-halka-arz-oldu-sirketler-kac-lot-verdi-iste-tum-arzlarin-detayli-dokumu-h-4769922)) [B].

Yıl sonu sayıları kaynağa göre değişiyor:
- Forbes: 18 arz ve 45,15 milyar TL ([Forbes Türkiye](https://www.forbes.com.tr/haberler/ilk-sekiz-ayda-34-halka-arz-piyasadan-82-4-milyar-lira-cekti)) [B].
- hisse.net, 22 Aralık: 17 arz ve 42,95 milyar TL ([hisse.net](https://www.hisse.net/haber/borsada-fren-yili-halka-arzlarda-tavan-serisi-neden-kisa-surdu-42562)) [B].
- Paradergi: 19 arz [B].
- TSPB: 16 pay arzı ve 2 yatırım ortaklığı, 41,0 milyar TL [R].

Arz başına katılımcı ~330 bine indi [Ç]. PwC'ye göre arz başına başvuru 126 bin ile 708 bin, talep katı 1,0x ile 8,9x arasındaydı ([PwC](https://www.pwc.com.tr/tr/Hizmetlerimiz/danismanlik/pdf/halka-arz-raporu_2025.pdf)) [B]. Buna rağmen halka arz endeksi XHARZ yılı **+%72,5** ile kapattı; BIST100 ise +%15 yükseldi. Bu rakam kohort hakkında yanıltıcıdır, çünkü endeksin ~%19'u tek bir hisse (DSTKF) ([hisse.net](https://www.hisse.net/haber/amp/borsada-fren-yili-halka-arzlarda-tavan-serisi-neden-kisa-surdu-42562)) [B]. 24 Kasım itibarıyla verilen rakam da farklıydı: XHARZ +%82,14, BIST100 +%11,11 ([Ekonomi Gazetesi](https://www.ekonomigazetesi.com/finans/halka-arzlarda-tavan-serisi-geri-dondu-65312)) [B].

**2026 toparlanma ve rekor yılı oldu.**
- Ocak–Şubat'ta 13 arz 10,44 milyon katılımcı topladı ([Forbes Türkiye](https://www.forbes.com.tr/dergi/halka-arz-talebi-guclu-kalirken-piyasa-kosullari-sureci-zorluyor)) [B].
- İlk çeyrekte 14 ya da 15 arz yapıldı; kaynaklar ayrışıyor. 9 Nisan itibarıyla hepsi arz fiyatının en az %10 üstündeydi ([Finansopia](https://www.finansopia.com/ekonomi/2026nin-ilk-ceyreginde-halka-arzlara-yogun-ilgi/)) [B].
- Mart'taki savaş akışı kesti. İkinci çeyrekte yalnız 2 arz yapıldı ([GZT](https://www.gzt.com/ekonomi/hangi-sirketler-halka-arz-olabilir-spk-onayladi-borsada-yeni-halka-arz-dalgasi-basliyor-4240491)) [B].
- **Temmuz 12 arz ve 38,4 milyar TL** ile rekor kırdı. İlk yedi ayda 28 arz, ~63 milyar TL ve 22,11 milyon katılımcı vardı ([Politikam](https://www.politikam.com/borsa-istanbul-halka-arz-piyasasinda-temmuz-ayinda-rekor-kirildi-2026)) [B].
- Ağustos sonunda arz sayısı 34'e, toplam **82,4 milyar TL**'ye ulaştı. Bunun 61,16 milyar TL'si sermaye artırımıydı ([Forbes Türkiye](https://www.forbes.com.tr/haberler/ilk-sekiz-ayda-34-halka-arz-piyasadan-82-4-milyar-lira-cekti)) [B].
- Arz başına katılımcı ~790 bine çıktı [Ç]; bu, 2023'ün üçte biri kadar.
- SPK'da onay bekleyen ~150 şirket var [B].

| Yıl | Arz sayısı (kaynağa göre) | Hasılat (milyar TL) | Arz başına katılımcı [Ç] | Arz altı payı (anlık) |
|---|---|---|---|---|
| 2023 | 56 (MKK, PwC) / 54 (TSPB) | 79,79 (MKK) / 63,3 (TSPB) | ~2,21 milyon | Oran bulunamadı; Eylül'de 33 arzın 29'u zirvesinin altında |
| 2024 | 33 (MKK) / 34 (Akalın) / 22+1 (TSPB 2026) | 57,31 / 58,3 / 59,5 | ~1,79 milyon (1. yarı ~2,5 m, 2. yarı ~0,5 m) | 14/34 ≈ %41 (Ocak 2025) |
| 2025 | 18 / 17 / 19 / 16+2 | 45,15 / 42,95 / 44,4 / 41,0 | ~0,33 milyon | 7/17 ≈ %41 (Kasım 2025) |
| 2026 (Oca–Ağu) | 34 | 82,4 | ~0,79 milyon (Oca–Tem) | %18 (Temmuz sonu) → ~%64 (1 Ekim, zayıf kaynak) |

Kaynaklardaki açıklamalar dört sürücüde birleşiyor ([GCM Yatırım](https://www.gcmyatirim.com.tr/arastirma-analiz/ozel-raporlar/2025-02-18-halka-arzlarda-yavaslama-endisesi); [Ekonomi Gazetesi](https://www.ekonomigazetesi.com/ekonomi/arz-bollugu-tavan-serisini-kirdi-83503)) [B]:
- BIST'in yönü,
- mevduat ve para piyasası getirisinin yarattığı fırsat maliyeti,
- aynı anda gelen arz sayısı,
- 2024 kayıplarından sonra hızlanan kâr satışı.

Politika faizinin eğitim penceresindeki seyri şöyle oldu ([TCMB](https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Temel+Faaliyetler/Para+Politikasi/Merkez+Bankasi+Faiz+Oranlari/1+Hafta+Repo)) [R]:
- Pencerenin başında %30'du (22.09.2023).
- 22.03.2024'te %50'ye çıktı ve Aralık 2024'e kadar orada kaldı.
- Mart 2025'te %42,5'e indi, şokla %46'ya döndü.
- 23.01.2026'da %37'ye indi ve Temmuz 2026'ya kadar sabit kaldı ([GZT](https://www.gzt.com/ekonomi/merkez-bankasi-faiz-karari-2026-tcmb-duyurdu-politika-faizi-degisti-mi-sabit-mi-kaldi-temmuz-ayi-tcmb-faiz-karari-ne-oldu-tcmb-politika-faizi-yuzde-kac-4243709)) [B].

TÜFE Mayıs 2024'te **%75,45** ile zirve yaptı ([Bloomberg HT](https://www.bloomberght.com/2024-enflasyonu-belli-oldu-3738394)) [B]. Aralık 2025'te %30,89'a, Ağustos 2026'da %31,51'e indi ([Ekonomi Gazetesi](https://www.ekonomigazetesi.com/ekonomi/2025-enflasyonu-3089-69017); [Trading Economics](https://tradingeconomics.com/turkey/inflation-cpi)) [B].

SPK Başkanı Kasım 2023'te, mevduat faizi yükselirken borsadan çıkış olursa arzlara ilginin yavaşlayacağını söyledi. SPK'nın başarısız arzları önlemek için onayları zaman zaman yavaşlattığını da kabul etti ([Diken](https://www.diken.com.tr/?p=1382060)) [B].

Bir düzeltme: araştırma notlarındaki "2024–2025 yavaşlaması güçlü pozitif geriye dönük reel faizle çakıştı" çıkarımı 2024 ortası için doğru değil. Mayıs 2024'te %50'lik politika faizi, %75,45'lik yıllık enflasyonun 25 puan altındaydı. O dönemde pozitif olan, düşen aylık enflasyona göre hesaplanan ileriye dönük reel faizdi [Ç]. Reel faiz özelliği kurulacaksa hangi tanımın kullanıldığı açıkça yazılmalı.

## Getiri ilk günde değil, tavan kuyruğunda birikiyor

### İlk gün +%10 ile kilitli

BIST Pay Piyasası Yönergesi segmentlere ±%20/±%15/±%10 marj yazıyor. Ancak 13.03.2020'den beri "ikinci bir duyuruya kadar" tüm pazarlarda **±%10** uygulanıyor ([BIST Yönerge](https://www.borsaistanbul.com/files/borsa-istanbul-as-pay-piyasasi-yonergesi.pdf); [Hürriyet](https://www.hurriyet.com.tr/ekonomi/borsa-istanbuldan-marjlara-tedbir-41467941)) [R/B].
- İlk gün baz fiyatı, arz fiyatının en yakın fiyat adımına yuvarlanmasıyla bulunuyor ([BIST Pay Piyasası Prosedürü](https://www.borsaistanbul.com/files/pay-piyasasi-proseduru.pdf)) [R].
- Limitler içe yuvarlandığı için gerçek tavan çoğu zaman %10'un biraz altında kalıyor. Arf Bio 19,50 TL'den açılış seansında **21,44 TL'de (+%9,95)** tavana kilitlendi ([Dünya](https://www.dunya.com/finans/borsa/arf-bio-halka-arzi-tavanla-basladi-haberi-810042)) [B].
- Albayrak Beton Temmuz 2026'da ilk gün **−%10** ile tabana kilitlendi ([YatırımX](https://www.yatirimx.com.tr/sirket-haberleri/albayrak-beton-ilk-islem-gununde-tabana-kilitlendi/22653)) [B]. Bu, bandın o tarihte de ±%10 olduğunu gösteriyor [Ç]. Yine de 2026'da geçici tedbirin resmen yürürlükte olduğunu doğrulayan bir BIST duyurusu bulunamadı.

Bu yapı Türk düşük fiyatlamasını çok günlü serilere yayıyor.
- Arslan, Colak ve Pirgaip 2020–2023'teki 154 arzda bu yüzden 5. gün piyasa-düzeltilmiş getiriyi ölçüt alıyor ve ortalama **%35** buluyor ([Borsa Istanbul Review 2025](https://www.sciencedirect.com/science/article/pii/S2214845025000821)) [R].
- 2010–2019'da ortalama ilk gün anormal getirisi yalnız **%5**'ti ve arzların ~%38'i negatif başlıyordu ([Avcı, Akdoğu & Şimşir 2020](https://research.sabanciuniv.edu/id/eprint/41701/1/borsa-istanbul-ilk-halka-arz-piyasa-dinamikleri-ve-dusuk-fiyatlama.pdf)) [R]. Bu dönem eşit dağıtım öncesine ait ve bugüne kalibrasyon için kullanılamaz.
- Çin'de ilk gün getirisi +%44 ile sınırlı. Qian, Ritter ve Shao bu yüzden "ilk getiri"yi limite değmeyen ilk günün kapanışına kadar ölçüyor ([Qian, Ritter & Shao, JFQA 2024](https://site.warrington.ufl.edu/ritter/files/IPO-Chinese-style.pdf)) [R]. BorsAi'deki doğal karşılığı, ilk getiriyi seri artı bozulma günü olarak tanımlamaktır [Ç].

### Seri uzunluğu: 15 günden medyan üçe, sonra iki tepeye

Yıl bazında resmî bir ortalama yok. Tablo tek tek basın vakalarından ve projenin kendi ölçümünden kuruluyor.
- **2023:** Ofis Yem **15**, Tatlıpınar 14, Ekos 12, Baydöner 12, Söke Un 12 tavan yaptı ([Ekonomi Gazetesi](https://www.ekonomigazetesi.com/finans/borsa/zirveden-en-cok-dusenler-secim-sonrasi-halka-arzlar-19909); [Paratic](https://paratic.com/cilginlik-bitti-mi-yeni-halka-arzlar-tavanda-duramiyor); [Ekonomim](https://www.ekonomim.com/ekonomi/zirveden-en-cok-dusenler-secim-sonrasi-halka-arzlar-haberi-708107); [Diken](https://www.diken.com.tr/?p=1314284)) [B].
- **2024:** Pasifik Donanım 8, Gündoğdu Gıda 7 tavan gördü ([Halk TV](https://halktv.com.tr/ekonomi/biri-yeni-halka-arz-toplam-4-hisseye-ay-boyunca-yasak-uygulandi-borsa-istanbul-tedbir-karari-uygulayacak-808674h); [Paratic](https://paratic.com/bir-haftada-yuzde-60-yukselen-halka-arza-tedbir-geldi/)) [B]. Temmuz 2024 manşeti ise "Halka arzlar tavansız kaldı" idi [B].
- **2025:** Adı geçen 11 arzın seri değerleri {11, 10, 5, 4, 3, 3, 2, 1, 1, 1, 1} ([Borsamatik](https://www.borsamatik.com.tr/halka-arzlarda-tavan-serileri-geri-mi-dondu-haber-175248); [Ekonomi Gazetesi](https://www.ekonomigazetesi.com/finans/halka-arzlarda-tavan-serisi-geri-dondu-65312)) [B]. Zeray GYO'nun 2 tavanı eklenince **medyan 2,5, ortalama 3,7** çıkıyor [Ç]. Gülermak, Akfen İnşaat, Enda, Kalyon ve Balsu listede olmadığı için bu tahmin eksik.
- **2026:** Dağılım iki tepeli. SVGYO en az 8, Beta Enerji 10, Golda Gıda 7, İsvea 3, Orzax 2 tavan yaptı. Ekim Turizm, Soho Giyim ve Saat ve Saat ise tabana indi ([hisse.net](https://www.hisse.net/haber/svgyo-fire-vermiyor-tavan-serisi-8-gunde-66067); [Ekonomi Gazetesi](https://www.ekonomigazetesi.com/ekonomi/arz-bollugu-tavan-serisini-kirdi-83503)) [B].

Proje ölçümü bu tabloyla uyumlu [P]:
- H99'da arzların ~%82'si ilk gün tavan kapatıyor.
- Ortalama seri dönemden döneme ~2 kat oynuyor: 2021'de 3,4 gün, 2023'te 7,2 gün.

### Seriyi ne uzatıyor?

Mekanizma tarafında en açık aday eşit dağıtımın yarattığı küçük tahsisatlar.
- 30.03.2023'ten beri bireysel yatırımcı grubunda oransal dağıtım yasak; herkes eşit pay alıyor ([SPK i-SPK.128.21 metni, Ahlatcı derlemesi](https://ahlatciyatirim.com.tr/medya/icerik/dosyalar/duyuru-ve-ilke-kararlari.pdf)) [R].
- Arf Bio'da 175 milyon pay **508.401 yatırımcıya** dağıtıldı; kişi başı ortalama **47 lot (916 TL)** ([Dünya](https://www.dunya.com/finans/borsa/arf-bio-halka-arzi-tavanla-basladi-haberi-810042)) [B].
- Savur GYO'da planlanan %40'lık bireysel dilim 701 bin başvuruya eşit dağıtıldıysa, kişi başı ~610 TL eder [Ç] ([Paradergi](https://www.paradergi.com.tr/is-dunyasi-kulis/2026/03/04/savur-gyonun-halka-arzi-tamamlandi-planlanan-tahsisatin-733-kati-talep-geldi/amp)).
- Toplam talep katı yüksek görünse de bireysel dilim çoğu zaman yalnız 2–3 kat karşılanıyor. Savur'da toplam 7,33x, bireysel 2,64x idi [B]. Bu, 2023'e göre daha büyük bireysel tahsisat demek; dolayısıyla ikincil piyasaya taşan karşılanmamış talep de daha az [Ç].

Ancak basındaki küçük örnek bu hikâyeyi tek başına doğrulamıyor. [Yeni Şafak](https://www.yenisafak.com/halka-arz-takvimi-2025-hangi-sirketler-halka-arz-oldu-sirketler-kac-lot-verdi-iste-tum-arzlarin-detayli-dokumu-h-4769922) tablosundaki 2025'in 11 arzında, seri uzunluğuyla Spearman korelasyonları [Ç]:
- kişi başı TL (arz büyüklüğü / katılımcı): **−0,08**,
- arz büyüklüğü: **−0,08**,
- katılımcı sayısı: **−0,23**.

Bu örnekte sıralamayı daha çok zamanlama açıklıyor [Ç]:
- Yedi aylık duruştan sonraki ilk arz Dof Robotik 10 tavan yaptı.
- Yaklaşık yedi hafta sonra gelen Eco Green 11 tavan yaptı.
- Takvim doldukça Vakıf Faktoring 2, Pasifik Holding 1, Zeray 2 tavanda kaldı.

Projenin `ceiling_hazard_v0` modeli H99'da talep katı yükselince serinin uzadığını, arz büyüdükçe kısaldığını buluyor [P]. Yani ilişki büyük örnekte var, ama takvim ve piyasa bağlamı birlikte modellenmezse görünmez olabiliyor. Basın da Temmuz 2026'daki kısalmayı "arz bolluğu" ile açıkladı: yatırımcı seçici davranabildiği için talep her arzda toplanmıyor ([Ekonomi Gazetesi](https://www.ekonomigazetesi.com/ekonomi/arz-bollugu-tavan-serisini-kirdi-83503)) [B]. Yine de bolluk tek başına yetmiyor. 13 arzlık Ocak–Şubat 2026 dalgası güçlü getirilerle bitti ([hisse.net](https://www.hisse.net/haber/2026-halka-arz-performans-raporu-zgyo-ve-meysu-yatirimcisini-ihy-etti-55939)) [B]. Yoğunluk etkisi büyük olasılıkla piyasa yönüyle etkileşiyor [Ç].

### Seri nasıl bozuluyor?

D1–D10 arasında satıcı tarafını kurallar daraltıyor:
- Mevcut ortaklar 30.03.2023'ten beri, izahname onayından itibaren **180 gün, borsada satış dahil**, pay satamıyor ([Ahlatcı](https://ahlatciyatirim.com.tr/medya/icerik/dosyalar/duyuru-ve-ilke-kararlari.pdf)) [R].
- Standart izahname taahhüdüyle mevcut ortaklar **1 yıl arz fiyatının altında** satmıyor ve ihraççı 1 yıl sermaye artırımı yapmıyor ([KAP, Ata Turizm](https://kap.org.tr/tr/api/file/download/4028328d9b827481019c474d38527865)) [R].
- Arz paylarında açığa satış eğitim penceresinin tamamında fiilen yoktu ([Capital](https://www.capital.com.tr/haberler/tum-haberler/spkdan-aciga-satis-karari); [CNBC-e](https://www.cnbce.com/piyasalar/spk-duyurdu-borsada-5-gun-aciga-satis-islemleri-yasaklandi-h25925)) [R/B]. Şubat 2023'ten 1 Ocak 2025'e tam yasak vardı; sonra yalnız BIST-50 hisseleri açığa satılabildi; iki stres döneminde tam yasak geri geldi. Arzlar listelendiklerinde BIST-50'de değil.

Yani tavana karşı satan ne içeriden kişi var ne de açığa satıcı. Seriyi arz sahiplerinin ve ikincil alıcıların satış kararları ile tavandaki alış kuyruğunun tükenmesi bitiriyor [Ç].
- Çin IPO'larında seri sırasında devir hızı düşükse seri uzuyor ve sonraki getiriler düşüyor ([Wu, Wang & Li 2018](https://www.sciencedirect.com/science/article/abs/pii/S0378437117308257)) [R, özet düzeyi]. Bu, tek yönlü emir defterinin doğal sonucu.
- Yüz binlerce hesaba dağılmış küçük pozisyonların çıkış kararları aynı anda gelirse seri ani biter [Ç, test edilmedi].
- Analistler serinin "genelde 3–5 günden sonra zayıfladığını" söylüyor ([Paradergi](https://www.paradergi.com.tr/finans/2025/12/18/halka-arzdan-hisse-alacaklara-oneriler)) [B, görüş].
- 90 günlük kısıt yalnız borsa dışı satışı, virmanı ve özel emirleri engelliyor; olağan borsa satışına dokunmuyor [R]. Bu yüzden D1–D10 satışını mekanik olarak sınırlamıyor.
- Fiyat istikrarı yalnız arz fiyatının altında alım yapıyor; seri sırasında etkisi yok.

### VBTS seriye seans 6–9 civarında yetişiyor

Volatilite Bazlı Tedbir Sistemi 15.11.2021'den beri beş kademeli ve her kademe bir ay sürüyor ([KAP/BIST duyurusu](https://kap.org.tr/tr/api/BildirimPdf/976897)) [R]:
1. açığa satış ve kredili işlem yasağı,
2. brüt takas,
3. emir paketi,
4. tek fiyat,
5. internet emir yasağı.

Tetikleme kriterleri yayımlanmıyor. Tavan serisindeki arzlarda 1. kademe yaklaşık 6–9 seans sonra geliyor [B]:
- DMRGD: ~7 seans ([Diken](https://www.diken.com.tr/?p=1367805)).
- PATEK: 8 ardışık tavan.
- GUNDG: 7 seanslık seri.

Açığa satış zaten mümkün olmadığından bu kademe arz için fiilen yalnız kredili işlem yasağı demek. 2. kademe bir ay dolmadan gelemeyeceği için ilk 10 seansta VBTS durumu 0 ya da 1 olur [Ç]. Kredili işlem bakiyesi az sayıda elde toplandığı için yasak, kullanıcı sayısının düşündürdüğünden daha etkili olabilir: 2025 sonunda 109,9 milyar TL, 44.165 kullanıcı, kişi başı 2,49 milyon TL ([TSPB Yaz 2026](https://tspb.org.tr/wp-content/uploads/2026/09/Gosterge_Yaz_2026_.pdf)) [R]. Tedbirin KAP'ta akşam ilan edilmesi de kamuya açık bir sinyal [Ç].

## Tavan bozulunca kilit sürüyor, yastık sonucu belirliyor

Türkiye'de tavan serisinden sonraki dinamikleri ölçen hakemli bir çalışma bulunamadı. Elimizdeki kanıt üç parçadan oluşuyor: uluslararası literatür, Türk basınındaki vakalar ve bant aritmetiği.

### Uluslararası kanıt: kısa vadede devam, orta vadede geri dönüş

- **Çin A-payları, 2000–2011, ~106 bin limit olayı:** Taban gününden sonraki gün **%75,9**, tavan gününden sonraki gün **%63,7** oranında aynı yönde hareket var. Kapanışta limitte kalınan günlerde bu oranlar **%85,8 (taban)** ve **%79,4 (tavan)**. Taban yönündeki süreklilik piyasa değeri büyüdükçe azalıyor ([PLOS ONE 2015](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0120312)) [R]. Burada "devam" aynı işaretli getiri demek, ikinci bir limit günü değil. %79,4 ve %85,8 özetten çıkarıldı; makaledeki tablodan doğrulanmalı.
- **İstanbul (Bildik ve Gülay):** Limitte kilitlenme, limite yalnız dokunmaktan çok daha güçlü etki taşıyor. Fiyat limitleri volatilite taşmasına, gecikmiş fiyat keşfine ve işlem engeline yol açıyor ([Journal of Financial Research 2006](https://ideas.repec.org/a/bla/jfnres/v29y2006i3p383-403.html)) [R].
- **Tayvan:** Limite yaklaşan fiyatın limite gitme olasılığı artıyor (mıknatıs etkisi). Bilgiye dayalı işlem alt limitte bu etkiyi güçlendiriyor ([Hsieh, Kim & Yang 2009](https://ideas.repec.org/a/eee/empfin/v16y2009i5p830-837.html)) [R].
- **Shenzhen hesap verisi:** Büyük yatırımcılar tavan gününde serbest dolaşımın %0,69'unu alıp ertesi gün %0,51'ini satıyor; küçük yatırımcılar tersini yapıyor ([Chen vd. 2019](https://voxchina.org/show-3-49.html)) [R].
- **Çin IPO'ları:** Limit açıldıktan sonraki getiriler "W" biçiminde. Açılış gününden sonraki gün yeniden limite gitme olasılığı yüksek ([Wu, Wang & Li 2017](https://www.sciencedirect.com/science/article/abs/pii/S0378437116305659)) [R, özet düzeyi].
- **Tayvan IPO'ları:** Tarihsel olarak "ardışık tavanların ardından ciddi geri dönüş" gösterdi ([Chin, Lin & Syu 2011](https://scholars.lib.ntu.edu.tw/handle/123456789/459464)) [R].

Model için anlamı [Ç]:
- Bozulma günü kapanışının *tipi* (tabanda kilitli mi, aralıkta mı, yeniden tavanda mı) ertesi günün en güçlü tekil göstergesi olmalı.
- Bozulmadan sonra yeniden tavan görülmesi etiket tanımında ayrı bir durum olarak ele alınmalı.

### Türkiye vakaları aynı yönü gösteriyor, ama nicel değil

- Zeray GYO 13,00 TL'den iki tavan yaptıktan sonra üçüncü gün tabanda bekleyen satış emirlerinin baskısıyla **−%9,98** kapattı ([hisse.net](https://www.hisse.net/haber/borsada-fren-yili-halka-arzlarda-tavan-serisi-neden-kisa-surdu-42562)) [B].
- Eylül 2023 ortasında yılın 33 arzının 29'u zirvesinin altındaydı. 11'i zirveden %30–51 düşmüştü ve bunların 10'u seçim sonrasında, yani döngünün geç evresinde yapılan arzlardı ([Ekonomi Gazetesi](https://www.ekonomigazetesi.com/finans/borsa/zirveden-en-cok-dusenler-secim-sonrasi-halka-arzlar-19909)) [B].
- Basında "rekor tavan serisinden sonra çakılan" ve "taban serisine başlayan" yeni şirket manşetleri var ([Diken](https://www.diken.com.tr/?p=1360130); [Ekonomi Gazetesi](https://www.ekonomigazetesi.com/finans/borsa/borsanin-4-yeni-sirketi-taban-serisine-basladi-19465)) [B, yalnız başlık].
- Proje canlı sicilinde NETGL tavanı bozduktan sonra art arda taban yaptı. "Bozulma sonrası rejim" fikri buradan çıktı [P].

### Yastık aritmetiği D10 sorusunun yarısını mekanik olarak çözüyor

±%10 bantta D1'den başlayan N günlük tavan serisi fiyatı arz fiyatının 1,1^N katına taşır. Bu yastığı silmek için yaklaşık N × ln(1,1)/ln(1/0,9) ≈ **0,905 × N** tam taban gerekir [Ç]. D10 kapanışının arz fiyatının altında olabilmesi için 1,1^N × 0,9^(10−N) < 1, yani **N ≤ 5** olmalı. N=5'te bile kalan beş seansın hepsi taban olmalı; o durumda D10 fiyatı arz fiyatının 0,951 katı olur [Ç]. Fiyat adımının içe yuvarlanması iki yönü de ~%9,95'e çektiği için sonuç değişmiyor (N=5 için yine 0,951) [Ç].

| D1'den seri (N) | Arz fiyatına göre yastık | Silmek için gereken taban sayısı | D10'da mümkün en düşük fiyat / arz fiyatı |
|---|---|---|---|
| 2 | +%21 | 1,8 | 0,52 |
| 3 | +%33 | 2,7 | 0,64 |
| 4 | +%46 | 3,6 | 0,78 |
| 5 | +%61 | 4,5 | 0,95 |
| 6 | +%77 | 5,4 | 1,16 (arz altı imkânsız) |
| 8 | +%114 | 7,2 | 1,74 (arz altı imkânsız) |

Aynı kontrol her akşam genel biçimde yapılabilir [Ç]:
- k_t = ln(P_t / arz fiyatı) / ln(1/0,9): arz fiyatına olan mesafe, limit adımı cinsinden.
- r_t = 10 − t: D10'a kalan seans sayısı.
- k_t ≥ r_t ise D10'da arz altına inme olasılığı yapısal olarak sıfırdır.

Çin'de yastık çoğu zaman %100'ü aştığı için arz altında kalan "ilk getiri" oranı %5'in altında, kısıtlı dönemlerde %1,2 ([Qian, Ritter & Shao](https://site.warrington.ufl.edu/ritter/files/IPO-Chinese-style.pdf)) [R]. Türk serileri daha kısa olduğu için bu taban oranı Türkiye'ye aktarılamaz [Ç].

### Fiyat istikrarı arz fiyatının hemen üstünde yumuşak bir taban olabilir

- Fiyat istikrarı isteğe bağlıdır ve izahnamede tanımlanır. Uygulamada ilk işlem gününden itibaren **30 gün** sürer, yani D10'u kapsar.
- Ata Turizm'de mevcut ortağın satış gelirinden **arz büyüklüğünün %10'u** bu amaçla ayrıldı ([KAP](https://kap.org.tr/tr/api/file/download/4028328d9b827481019c474d38527865)) [R].
- Yalnız fiyat arz fiyatının altına indiğinde alım yapılıyor ([Fintables](https://fintables.com/arastirma/yazilar/trading/halka-arz-nedir)) [B].
- Sık sık hiç kullanılmıyor: İsvea'nın 30 günlük penceresinde hiç işlem yapılmadı ([KAP](https://kap.org.tr/tr/api/BildirimPdf/1646149)) [R].
- 30 günün düzenleyici bir üst sınır mı, piyasa pratiği mi olduğu doğrulanamadı.

Test edilebilir sonucu: istikrar fonu olan arzlarda D10 kapanışları arz fiyatının hemen üstünde toplanmalı [Ç].

## D10'da arz altı: kohort, büyüklük ve takvim yoğunluğu belirliyor

Dış kaynaklar arz altı oranını sabit bir ufukta değil, belirli tarihlerdeki fotoğraflarla veriyor. Aşağıdaki oranlar D10 oranı değil; kohortun o tarihteki durumu.

| Kohort | Ölçüm tarihi | Arz altı | Kaynak |
|---|---|---|---|
| 2024 1. çeyrek (8 arz) | Temmuz 2024 | 7/8 hâlâ arz fiyatının üstünde | [Bloomberg HT](https://www.bloomberght.com/halka-arzlar-tavansiz-kaldi-katilimcisi-azaldi-2356021) [B] |
| 2024 tümü | 9 Ocak 2025 | 14/34 ≈ %41 (en kötü Koton −%32) | [Midas](https://www.getmidas.com/midasin-kulaklari/halka-arz-fiyatinin-altina-dusen-hisseler-2-p-80818) [B] |
| 2025 | 24 Kasım 2025 | 7/17 ≈ %41 (−%8,3 ile −%79,6 arası) | [Ekonomi Gazetesi](https://www.ekonomigazetesi.com/finans/halka-arzlarda-tavan-serisi-geri-dondu-65312) [B] |
| 2025 | yıl sonu | %40 zararda; son 10 arzın yarısından fazlası arz altında | [Forbes Türkiye](https://www.forbes.com.tr/dergi/2025-yili-halka-arzlar-acisindan-turkiye-de-kayip-yil-olarak-kayda-gecti); [Borsagündem](https://www.borsagundem.com.tr/halka-arz-edilen-son-hisselerde-arz-sonrasi-getiriler-4) [B] |
| 2026 1. çeyrek | 9 Nisan 2026 | 0/15 (hepsi en az +%10) | [Finansopia](https://www.finansopia.com/ekonomi/2026nin-ilk-ceyreginde-halka-arzlara-yogun-ilgi/) [B] |
| 2026 | 31 Temmuz 2026 | 5/28 ≈ %18 | [CNBC-e](https://www.cnbce.com/borsa/borsada-temmuz-firtinasi-2026nin-ilk-7-ayinda-rekor-5-hisse-halka-arz-fiyatinin-altinda-g34278) [B] |
| 2026 | 1 Ekim 2026 | 23/36 ≈ %64; ortalama −%5; en kötü EKIM −%61 | [Hoca İle Borsa](https://www.hocaileborsa.com/halka-arz/tavan-serisi) [B, yöntemi belirsiz, düşük kalite] |

**Oranın arttığı dönemlerde ortak bir desen var:** BIST düşüyor ya da yatay gidiyor, arz başına katılım azalıyor, takvim yığılıyor ve arzlar büyüyor.
- 2024'ün ikinci yarısında katılım çöktü. Düşük talep katı yüzünden küçük kârlar bile satışı tetikledi ([Hürriyet](https://www.hurriyet.com.tr/ekonomi/halka-arzda-secici-olmak-sart-42462512)) [B]. Geride kalanlar arasında Koton, Rönesans Gayrimenkul, IC Enterra ve Lila Kağıt gibi büyük ya da tanınmış arzlar vardı ([Midas](https://www.getmidas.com/midasin-kulaklari/halka-arz-fiyatinin-altina-dusen-hisseler-2-p-80818)) [B].
- 2025'in en kötüleri arasında geç gelen büyük arzlar (Vakıf Faktoring, 3,2 milyar TL) ile Zeray, Enda ve Kalyon var. Kazananlar küçük ve uzun serili arzlar: Bulls GSYO +%254, Vişne +%150, Eco Green +%109, Dof +%78 ([Borsagündem](https://www.borsagundem.com.tr/halka-arz-edilen-son-hisselerde-arz-sonrasi-getiriler-4)) [B].
- Temmuz 2026'nın 12 arzlık yığılmasında Soho −%13,9'a, Ekim Turizm −%21,7'ye, Saat ve Saat −%19'a indi ([Ekonomi Gazetesi](https://www.ekonomigazetesi.com/ekonomi/arz-bollugu-tavan-serisini-kirdi-83503)) [B].

**Oranın düştüğü dönemler, yeni bir dalganın ilk arzlarıydı:** 2024'ün ve 2026'nın ilk çeyrekleri. 2026'nın ilk çeyreği özellikle dikkat çekici. Mart 2026 savaş şokunda BIST100 iki haftada **−%4,56** düşerken halka arz endeksi **+%5,35** yükseldi ([Ekonomim](https://www.ekonomim.com/ekonomi/borsada-savasin-yarattigi-erime-20-milyar-dolar-haberi-882016)) [B]. SVGYO da savaşın ortasında en az 8 tavan yaptı [B]. Yani yeni arz getirileri kısa vadede endeksten kopabiliyor. BIST100 tek başına yeterli bir piyasa değişkeni değil [Ç].

**Akademik kanıt arz büyüklüğünü ve talebin kimden geldiğini öne çıkarıyor.** Arslan, Colak ve Pirgaip'in bulguları (154 arz, 2020–2023, R² ≈ 0,22; [Borsa Istanbul Review](https://www.sciencedirect.com/science/article/pii/S2214845025000821)) [R]:

| Değişken | Etki (5. gün anormal getiri) |
|---|---|
| log hasılat | **−0,11** |
| Yurt içi kurumsal tahsisat payı | **−0,26 / −0,27** |
| Yabancı kurumsal tahsisat payı | **+0,76 / +0,81** |
| Kredili işlem | **−3,21 / −4,21** |
| 24.03.2022 kuralı (takastaki kredili ya da teminatlı işlemle arz talebi yasağı) | **+16 puan** |
| 30.03.2023 eşit dağıtım kuralı | **+12 puan** |
| Aracı kurum kalitesi, konsorsiyum büyüklüğü | anlamsız |

İki uyarı [Ç]:
- Eşit dağıtım rejimine düşen yalnız 46 arz var; bu rejimin etkisi zayıf tahmin ediliyor.
- Küçük arzlarda yabancı pay çoğunlukla sıfır. Bu değişken, büyük ve kaliteli arzı işaretleyen bir gösterge gibi davranabilir.

**Fon kullanım yeri de bir aday.** 2013–2022'de işletme sermayesi için para toplayan şirketlerin medyan ilk gün düşük fiyatlaması %14 ile en yüksekti. Aynı şirketlerin 2 yıllık BHAR'ı ise **−%62** idi; yatırım için toplayanlarda +%195 ([Akalın-Ayyıldız & Oran 2026](https://www.sciencedirect.com/science/article/pii/S2214845026000785)) [R]. 10 günlük ufuktaki etkisi bilinmiyor.

**İskonto paradoksu.** 2024'te ortalama iskonto %27 ile dört yılın en yükseğiydi ([PwC](https://www.pwc.com.tr/tr/Hizmetlerimiz/danismanlik/pdf/halka-arz-raporu_2025.pdf)) [B]. Buna rağmen kohortun ~%41'i arz altına düştü [Ç]. Fiyat tespit raporundaki iskonto şirketin kendi değerlemesine göre hesaplanıyor; piyasa ve talep kötüleşince koruma sağlamıyor.

**Projenin en güçlü iç bulgusu dış literatürde yok.** Ek satış kullanılan arzların D10'da %63'ü arz fiyatının altında; kullanılmayanlarda bu oran %20. Yön iki dönemde de aynı [P]. Okunabilen Türk çalışmalarında ek satış değişkeni yok. Olası mekanizma: ek satış D1'de dolaşımdaki pay miktarını büyütüp karşılanmamış talebi eritiyor ve mevcut ortağın satma isteğini işaret ediyor [Ç].

## Kuralların çoğu ilk on seansta sabit; tek dağıtım kırılması 19 Eylül 2024

Eğitim penceresi (2023-09 sonrası) için kritik ayrım şu: hangi kurallar sabit kaldı, hangileri değişti? Sabit kurallar özellik olamaz ama mekanizmayı belirler. Değişenler rejim bayrağı adayıdır.

| Yürürlük | Değişiklik | İlk 10 seansa etkisi | Eğitim penceresinde |
|---|---|---|---|
| 13.03.2020 | Tüm pazarlarda ±%10 bant, "ikinci duyuruya kadar"; yönerge 20/15/10 yazıyor ([Hürriyet](https://www.hurriyet.com.tr/ekonomi/borsa-istanbuldan-marjlara-tedbir-41467941)) | D1 ~+%10'da tavan | Sabit |
| 15.11.2021 | VBTS beş kademe, her biri 1 ay ([KAP](https://kap.org.tr/tr/api/BildirimPdf/976897)) | Kademe 0 ya da 1 | Sabit yapı |
| 24.03.2022 | Arz talebinde takastaki kredili ya da teminatlı işlem yasağı ([Arslan vd.](https://www.sciencedirect.com/science/article/pii/S2214845025000821)) | Kaldıraçlı talep yok | Sabit |
| ~06.02.2023 | Piyasa genelinde açığa satış yasağı ([Capital](https://www.capital.com.tr/haberler/tum-haberler/spkdan-aciga-satis-karari)) | Tavana karşı açığa satıcı yok | Arz payları için sabit |
| 30/31.03.2023 | i-SPK.128.21: bireysele eşit dağıtım; borsada satış eşiği 250 → **750 milyon TL**; 90 ve 180 günlük kısıtlar ([Ahlatcı](https://ahlatciyatirim.com.tr/medya/icerik/dosyalar/duyuru-ve-ilke-kararlari.pdf); [Bloomberg HT](https://www.bloomberght.com/spk-ilk-halka-arzlarda-bireysel-yatirimcilari-esitledi-2329119)) | Küçük tahsisatlar; içeriden satış yok | Sabit (pencereden önce başladı) |
| 06.11.2023 | 250 TL üstü fiyatlara yeni fiyat adımı kademeleri ([Midas](https://www.getmidas.com/midasin-kulaklari/borsa-istanbuldan-fiyat-adimi-duzenlemesi-p-29150)) | Tavan çarpanı | İçinde; az sayıda arzı etkiler |
| 19.09.2024 | i-SPK.128.23 ([Lexpera](https://www.lexpera.com.tr/mevzuat/kurul-kararlari/sermaye-piyasasi-kurulu-nun-i-spk-128-23-19-09-2024-tarih-ve-1508-s-k-sayili-ilke-karari-i-spk-128)): yüksek başvurulu grup ≤%10; kurumsal dilimin ≥%50'si fonlara; PYŞ kendi hesabı ≤%2; içeriden kişiler yalnız bireysel gruptan; artan paylar gruplar arasında serbestçe kaydırılabilir | Kurumsal ve yüksek başvurulu talebin yapısı | **Tek dağıtım kırılması** |
| 31.12.2024 / 01.01.2025 | Kotasyon ve SPK eşikleri yaklaşık ikiye katlandı (Yıldız 2 milyar, Ana 500 milyon, Alt 200 milyon TL; [Erdem & Erdem](https://www.erdem-erdem.av.tr/bilgi-bankasi/borsa-istanbul-as-tarafindan-kotasyon-esikleri-guncellendi)) | Büyüklük ile pazar arasındaki eşleşme değişti | İçinde |
| 23.03 → 29.08.2025 | Tam açığa satış yasağı; kredili işlem özkaynak oranı %35 → %20; OTR 3:1 ve aşım ücreti 0,50 TL (24.03–25.04) ([Karar](https://www.karar.com/ekonomi-haberleri/spkdan-aciga-satis-karari-yasak-29-agustosa-kadar-uzatildi-1971550); [Halk TV](https://halktv.com.tr/ekonomi/borsadan-emirislem-orani-ve-ucretinde-degisiklik-923957h)) | Kaldıraç rahatlaması | **İlk 10 seansı bu pencereye düşen arz yok** [Ç] |
| 02.03 → 26.06.2026 | Tam yasak; özkaynak oranı %20; OTR 3:1 ([CNBC-e](https://www.cnbce.com/borsa/bistte-algoritma-onlemi-yuksek-frekansli-islemlerde-emirislem-orani-degistirildi-h25923); [Habertürk](https://www.haberturk.com/ekonomi/borsa-istanbul-da-aciga-satis-yasagi-kaldirildi-3894811)) | Aynı | ~3 arz (SVGYO, AAGYO, Mayıs'ta 1 arz) [Ç] |
| 27.08.2026 | i-SPK.128.30: ilk başvuru önceliği ([Erdem & Erdem](https://www.erdem-erdem.av.tr/bilgi-bankasi/ilk-halka-arz-basvurularinda-oncelik-taninmasina-iliskin-yeni-spk-ilke-karari)) | Arz bileşimi | Canlı dönem |
| 21.09.2026 | BIST Yönergesi ve Pay Piyasası Prosedürü (rev. 54) revize edildi ([Prosedür](https://www.borsaistanbul.com/files/pay-piyasasi-proseduru.pdf)) | İçerik doğrulanmadı | Canlı dönem; **farkı kontrol edilmeli** |

**Maruziyet tablosu en önemli sonucu veriyor.** 2025 stres penceresinde ilk on seansı geçen hiçbir arz yok: duruştan önceki son arz Bulls GSYO'nun (21 Şubat) D10'u seans sayımıyla 6 Mart'ta, yani 19 Mart şokundan önce bitti [Ç]. 2026 savaş penceresine yaklaşık 3 arz düşüyor ve sonuçları zıt: SVGYO yılın en iyi getirisi (+%419, Mayıs), AAGYO ise arz fiyatının %16 altında ([Borsagündem](https://www.borsagundem.com.tr/2026-halka-arzlarinda-getiri-sampiyonu-belli-oldu-iste-o-hisseler)) [B]. Stres bayrakları bu veriyle öğrenilemez.

**Notlar arasındaki çelişkiler ve düzeltmeler** (eski notları ya da özetleri kullananlar için):
- Makro notlardaki bir özet 750 milyon TL borsada satış eşiğini 2024 değişikliğine bağlıyor. SPK metnine göre eşik **30.03.2023**'ten beri var [R].
- Bir hukuk bürosu özeti 90 günlük kısıtı "yurt içi bireysel yatırımcılara" bağlıyor ([Mondaq](https://www.mondaq.com/turkey/commoditiesderivativesstock-exchanges/1527302/halka-arzda-uygulanacak-sat%C4%B1%C5%9F-y%C3%B6ntemleri-ve-da%C4%9F%C4%B1t%C4%B1m-esaslar%C4%B1na-ili%C5%9Fkin-de%C4%9Fi%C5%9Fiklikler)). Karar metni ise pay alan yatırımcıların borsa dışı satış, virman ve özel emirlerini kısıtlıyor; olağan borsa satışını değil. SPK Bülteni 2024/48'den doğrulanmalı.
- Arslan vd. kurumsal tahsisat sınırını "%3" diye özetliyor. Resmî metinde sınır yatırımcı başına %1, PYŞ fonları için %3.
- Karar tarihi 19.09.2024; basın 20.09.2024'te duyurdu.
- Yüksek başvurulu grubun teminatı ("nakit ve/veya %120 BIST-30") özetlerde farklı ifade ediliyor.
- Açığa satış yasağının 29.06.2026 sonrasında yeniden yalnız BIST-50'ye mi döndüğü belirtilmemiş.
- Mart 2025 OTR indiriminin 25.04.2025'ten sonra uzatılıp uzatılmadığı doğrulanmadı.
- VBTS kriterleri kamuya açık değil.

## Test edilebilir öneriler

Öneriler projenin ilkelerine göre yazıldı. Her fikir bir mekanizmayla gelir, tek bir önceden ilan edilmiş hipotezle sınanır ve dondurulduktan sonra canlıda ölçülür. Örnek ~100 arz olduğu için aday sayısı az tutulmalı.

Kanıt gücü ölçeği:
- **Güçlü:** mekanik kural ya da birden çok hakemli çalışma.
- **Orta:** tek Türkiye çalışması, tutarlı uluslararası kanıt ya da proje içi ölçüm.
- **Zayıf:** yalnız basın, uygulayıcı görüşü ya da çıkarım.

"PIT" sütunu, değerin tahmin anında (zaman damgası) bilinip bilinmediğini söyler.

### A. Yapısal kısıtlar ve etiket tanımları (öğrenilmez, kodlanır)

| # | Aday | Model | Mekanizma | Veri ve PIT | Kanıt |
|---|---|---|---|---|---|
| A1 | Fiyat adımına göre doğru hesaplanmış limit fiyatı; "tavan günü" = kapanış üst limitte (dokunma değil) | Tümü | ±%10 içe yuvarlanır; 06.11.2023 adım kademeleri; kilitlenme dokunmadan farklıdır (Bildik & Gülay) | Önceki kapanış ve adım tablosu; t−1 akşamı bilinir | Güçlü [R] |
| A2 | D10 yapısal sıfırı: k_t ≥ r_t ise P(D10 < arz fiyatı) = 0 | D10 düşüş, bozulma sonrası | Bant aritmetiği; D1'den N ≥ 6 tavan sonrası arz altı imkânsız | Kendi fiyat verisi; her akşam | Güçlü, mekanik [Ç]; bant ya da D10 tanımı değişirse geçersiz |
| A3 | İlk getiri = arz fiyatından ilk tavan-dışı kapanışa | Getiri, seri | Düşük fiyatlama seriye yayılıyor (Qian, Ritter & Shao tanımı) | Kendi veri | Güçlü, yöntem [R] |
| A4 | D1–D10 serbest dolaşımı = arz edilen lot (+ ek satış); devir hızı = hacim / arz lotu | Seri, bozulma | İçeriden satış 180 gün ve 1 yıl boyunca kapalı | İzahname, KAP sonuçları, günlük hacim | Kural güçlü [R]; etkisi test edilmedi |

### B. Listeleme öncesi özellikler

| # | Aday | Model | Mekanizma | Veri ve PIT | Kanıt |
|---|---|---|---|---|---|
| B1 | Bireysel kişi başı tahsisat (lot ve TL); bireysel dilim talep katı | Seri (küçükse +), D10 (−) | Eşit dağıtım nedeniyle karşılanmamış talep ikincil piyasaya taşıyor | KAP "Halka Arz Sonuçları", D1 öncesi; yayın saati kaydedilmeli; H99'da 20/99 dolu [P] | Orta-zayıf: talep katı v0'da çalışıyor [P]; 2025 kontrolünde ρ ≈ 0 (n=11) [Ç] |
| B2 | log arz büyüklüğü (reel TL ya da dolar) | Seri (−), D10 (+) | Büyük dolaşım, agresif fiyatlama | İzahname ve fiyat tespit raporu; talep toplama öncesi | Orta: −0,11 [R]; v0 [P] |
| B3 | Yabancı kurumsal, yurt içi kurumsal ve yüksek başvurulu grup payları | Seri, D10 | Yurt içi kurumsal satış baskısı; yabancı talep kalite sinyali | KAP sonuçları, D1 öncesi | Orta: tek çalışma, 2020–23 [R]; büyüklükle birlikte sınanmalı |
| B4 | Ek satış kullanıldı mı ve oranı | D10 (+) | Dolaşımı büyütüyor; mevcut ortağın satma isteğini gösteriyor | KAP sonuçları, D1 öncesi | Orta: %63'e karşı %20 [P]; dış kanıt yok |
| B5 | Fiyat istikrarı: var mı, fon oranı (ör. %10), yürütücü kurum | D10 (−), arz fiyatı etrafında yığılma | Arz fiyatının altında alım, 30 gün | İzahname; günlük KAP işlem bildirimleri (ertesi gün) | Zayıf: uygulama kanıtı [R]; İsvea hiç kullanmadı |
| B6 | Satış yöntemi (borsada satış ≤750 milyon TL ya da talep toplama) ve pazar | Seri | Küçük arz; borsada satışta takastaki bakiye kullanılabiliyor | İzahname | Zayıf, yalnız kural mekaniği [R] |
| B7 | Fon kullanım yeri; ortak satışı payı | D10, uzun vade | Borç ya da işletme sermayesi için toplanan arzlar uzun vadede zayıf | İzahname | Zayıf: 10 günlük ufukta test yok; 2013–22 [R] |

### C. D1 akşamı ve bozulma günü özellikleri

| # | Aday | Model | Mekanizma | Veri ve PIT | Kanıt |
|---|---|---|---|---|---|
| C1 | Bozulma günü kapanış tipi: tabanda kilitli / tabana ≤1 adım / aralıkta / yeniden tavanda | Bozulma sonrası, D10 | Satış kuyruğu ertesi güne taşınıyor; mıknatıs etkisi | Günlük OHLC ve kapanış seansı; aynı akşam | Orta-güçlü [R]: PLOS ONE, Bildik & Gülay |
| C2 | Bozulma günü hacmi / arz lotu ve seri ortalamasına oranı; işlem sayısı | Bozulma sonrası | Yüksek hacim: satıcı kuyruğu boşaldı. Düşük hacimle tabanda kapanış: kuyruk sürüyor | Günlük | Orta; BIST'te yönü belirsiz, tek bir yön önceden kaydedilmeli [Ç] |
| C3 | Seri sırasında tavan günlerindeki devir hızı | Seri hazard | Düşük devir: uzun seri, düşük sonraki getiri | Günlük | Orta: Çin IPO'ları, özet düzeyi [R] |
| C4 | Limit adımı cinsinden mesafe k_t ve kalan seans r_t | D10 | Mekanik | Her akşam | Güçlü |
| C5 | VBTS kademesi ve tedbir başlangıcından beri geçen seans | Seri hazard, bozulma | Kredili işlem yasağı ve kamuya açık sinyal | KAP; t kapanışından sonra ilan, t+1'de etkin, t akşamı bilinir | Zayıf: 3 vaka, kriterler gizli [B] |
| C6 | İstikrar penceresi aktif × fiyat arz fiyatına ≤1 adım uzaklıkta | D10 | Yumuşak taban | İzahname ve fiyat | Zayıf [Ç] |

Aracı kurum dağılımı (AKD) yoğunlaşması da bir aday. Mekanizması Chen vd.'nin gösterdiği büyük yatırımcı satışı. Ancak veri büyük olasılıkla ücretli; tavandaki bekleyen alış emri gibi kapsam dışı sayılmalı [P].

### D. Piyasa bağlamı ve rejim

| # | Aday | Model | Mekanizma | Veri ve PIT | Kanıt |
|---|---|---|---|---|---|
| D1 | Sıcak piyasa: son 5–10 arzın seri uzunluğu, D5/D10 getirisi, arz altı oranı (yalnız D10'u T'den önce bitmiş arzlar) | Tümü | Talep kalıcılığı; öğrenilmiş davranış | Kendi veri; as-of kaydı | Orta-zayıf: XHARZ ile bireysel portföy arasında iki yönlü Granger nedenselliği ([Aydoğdu & Durmaz](https://dergipark.org.tr/tr/download/article-file/5484216)) [R]; 2010–17'de sıcak ve soğuk piyasa farkı yok ([Tuncay vd.](https://ojs.wsb.wroclaw.pl/index.php/WSBRJ/article/view/871)) [R] |
| D2 | Takvim yoğunluğu: önceki 20 seansta listelenen ve aynı hafta talep toplayan arz sayısı; önceki listelemeden bu yana geçen seans | Seri (−), D10 (+) | Talep seyrelmesi; duruştan sonra birikmiş talep | KAP ve halkarz.com takvimi; talep toplama başında bilinir | Zayıf: Temmuz 2026 [B]; Dof ve Eco Green [Ç]. Test etmesi ucuz |
| D3 | Kendi eşit ağırlıklı yeni arz endeksi ve BIST100: 20 günlük getiri, 52 haftalık zirveden düşüş | Tümü | Piyasa bağımlılığı (Çin); Mart 2026'da ayrışma | Günlük | Orta [R]; XHARZ yoğun (DSTKF %19), kullanılmamalı |
| D4 | Kredili işlem bakiyesi ve "özkaynak oranı rahatlaması" bayrağı | Seri, D10 | Kaldıraçlı talep; Türkiye'de negatif katsayı | TSPB haftalık; yayın gecikmesine uyulmalı | Orta: tek çalışma [R] |
| D5 | Faiz: politika faizi (karar günü 14:00), 1–3 ay mevduat (TCMB haftalık), 2 yıllık tahvil (günlük); reel faiz TÜFE yayın günüyle | Tümü | Fırsat maliyeti | TCMB, TÜİK; TÜFE m−2 [P] | Zayıf: eğitimde 5–6 rejim var, aşırı uyum riski yüksek |
| D6 | Rejim bayrakları: dağıtım_2024 (≥ 19.09.2024); stres (tam açığa satış yasağı ya da OTR 3:1); fon_krizi_2026 (≥ 16.09.2026) | Uyarı ya da ret | Kural değişiklikleri | Resmî tarihler | Kural [R]; stres pencerelerinde ~0 ve ~3 arz var, etkisi öğrenilemez. Model girdisi olarak değil, uyarı olarak kullanılmalı |

### Önerilen sıra (proje hattıyla eşleşik)

1. **A1, A2 ve C4 bedava ve mekanik.** D10 düşüş modeli iki aşamaya bölünebilir: "serinin ≤5 gün olma olasılığı" ve "kısa seri ile bozulma yolu verildiğinde düşüş olasılığı". Böylece model kesin bilinen bir sıfırı öğrenmeye veri harcamaz.
2. **Bozulma modeli (b) için tek ön-kayıtlı hipotez C1:** "Bozulma günü tabanda kilitli kapanış, ertesi gün taban olasılığını tabana kilitli olmayan kapanışa göre yükseltir." Etiket A1'deki kilit tanımıyla kurulmalı.
3. **Sıcak piyasa (a) ve bağlam (d) için D2 ile D1.** Temmuz 2026'nın 12 arzlık yığılması ve 2025'teki yedi aylık duruş, yoğunluk hipotezi için doğal deneyler.
4. **(c) KAP grup verisi:** B1, B3 ve B4 için. H99'daki 20/99 doluluk tamamlanmalı.
5. **(e):** B5 için "arz fiyatı etrafında yığılma" testi ve B4'ün genişletilmesi.

Her adımda, sonuç bilinmeden beklenen işaret ve aralık yazılmalı.

## Eylül 2026 sonu: yaklaşan arzlar eğitim verisinde olmayan bir rejime giriyor

| Koşul | Durum | Modele olası etkisi | İzlenecek gösterge |
|---|---|---|---|
| Fon krizi ve endeks çöküşü | 16.09: Tera Portföy, TP2 para piyasası fonu dahil iki fonda geri ödeme temerrüdüne düştü. 17.09: SPK yedi PYŞ'nin (Tera, Pusula, Hedef, Atlas, A1, Pardus, Bulls) 130 fonunu tasfiyeye aldı ve TEFAS işlemlerini durdurdu ([Milli Gazete](https://www.milligazete.com.tr/tera-hisse-neden-dusuyor-para-piyasasi-fonu-ne-oldu-temerrut-neden-yasandi-spk-hangi-karari-aldi)) [B]. 25.09: Tera Yatırım'ın faaliyetleri durduruldu, tasfiye ödemelerine 1 milyon TL sınırı kondu ([Paratic](https://paratic.com/borsada-fon-krizinin-bilancosu-endeks-aylik-yuzde-11-geriledi/)) [B]. BIST100 Eylül'de **−%16,65** ile 11.947'de kapandı; 15.204,92'lik zirveden **−%21,4** ([Trading Economics](https://tradingeconomics.com/turkey/stock-market)) [B/Ç] | Eğitimde karşılığı yok. Kurumsal dilimin ≥%50'si fonlara ayrıldığı için kurumsal talep zayıflayabilir. Tasfiye edilen fonlar ellerindeki yeni arz paylarını satabilir [Ç] | Tasfiye takvimi, fon portföy dökümleri, eşit ağırlıklı yeni arz endeksi |
| Aracı kurum riski | Tera 2026'da 5 arza aracılık etti: 13,4 milyar TL arz, 70,8 milyar TL talep, 3,9 milyon bireysel yatırımcı ([hisse.net](https://www.hisse.net/haber/halka-arzlarda-guclu-ivme-gecen-yilin-tamami-simdiden-asildi-85507)) [B]. Tera Yatırım, Ata Turizm'in istikrar yürütücüsüydü [R]. Bulls Yatırım, INTET'in (01.09.2026) 30 günlük istikrar yürütücüsü ([Fintables/KAP](https://fintables.com/borsa-haber-akisi/618b55c1-c971-4b99-97f4-e9f0685d07ee/bls-ozel-durum-aciklamasi-genel)) [R]. "Bulls" PYŞ'si de tasfiye listesinde [B] | Konsorsiyum lideri ve istikrar yürütücüsünün kimliği yeni bir risk değişkeni. Dağıtım kanalı daralabilir [Ç] | Yürütücü KAP bildirimleri, konsorsiyum listeleri |
| 2026 kohortunun kötüleşmesi | Arz altı oranı Temmuz sonunda %18 iken 1 Ekim'de ~%64 (zayıf kaynak) [B]. NETGL'nin D10'u (30.09) ekranda tabanda görüldü; resmî değer bültenden bekleniyor [P] | Sıcak piyasa özellikleri hızla negatife döndü. 2026'nın ilk yarısındaki olumlu kohortla öğrenen modeller iyimser kalır [Ç] | Kendi D10 sonuçları |
| Arz bolluğu ve yeni öncelik kuralı | Temmuz'da 12, Ağustos'ta 6 arz; onay bekleyen ~150 başvuru [B]. i-SPK.128.30 (27.08.2026) üç tür başvuruya öncelik veriyor: ilinden ilk kez listelenen şirket, kamu kontrolündeki şirket, ya da 15 milyar TL üstü ve ≥%50 yabancı tahsisatlı arz [R] | 15 milyar TL, notlarda geçen en büyük arzların (2026: Şa-Ra 6,23 milyar TL; 2025: Pasifik 6 milyar TL) iki katından fazla; büyük olasılıkla eğitim aralığının dışında, ekstrapolasyon gerekir. Yabancı payı yüksek arzlar Arslan vd.'ye göre olumlu. SPK şoklardan sonra onayları yavaşlattı (2025'te 7 ay; 2026'nın 2. çeyreğinde 2 arz), canlı sicil yavaş büyüyecek [Ç] | SPK haftalık bülteni (onaylar), arz büyüklüğü dağılımı |
| Faiz ve enflasyon | Politika faizi %37; Ocak–Temmuz arasında sabit kaldı, 10 Eylül kararı doğrulanmadı, konsensüs yıl sonu %35 ([bne IntelliNews](https://www.intellinews.com/turkey-s-central-bank-expected-to-stay-put-at-september-10-rate-setting-meeting-465821/)) [B]. Mevduat faizi %37,3 ile üç yılın en düşüğünde ([Forbes Türkiye](https://www.forbes.com.tr/ekonomi/tl-mevduat-faizi-uc-yilin-en-dusuk-seviyesinde)) [B]. TÜFE Ağustos'ta %31,51 ([Capital](https://www.capital.com.tr/haberler/tum-haberler/tuik-2026-yili-agustos-ayi-enflasyon-rakamlarini-acikladi)) [B]. Sonraki PPK toplantıları 22 Ekim ve 10 Aralık | Fırsat maliyeti 2024'ten düşük, ama reel olarak pozitif (~+5,8 puan) [Ç]. Para piyasası fonundaki temerrüt tasarrufların nereye kayacağını belirsizleştiriyor | PPK kararları, haftalık mevduat faizi |
| Stres tedbirleri | Mart 2025'te ve Mart 2026'da SPK birkaç gün içinde tam açığa satış yasağı, özkaynak oranında %35 → %20 indirim ve OTR 3:1 getirdi ([The Edge/Bloomberg](https://theedgemalaysia.com/node/749034); [CNBC-e](https://www.cnbce.com/piyasalar/spk-duyurdu-borsada-5-gun-aciga-satis-islemleri-yasaklandi-h25925)) [B]. Eylül 2026'da benzer bir tedbir olup olmadığı notlarda yok | Arz paylarında açığa satış zaten yok. Özkaynak oranı rahatlaması kaldıraçlı alımı artırabilir [Ç] | SPK bülteni |
| BIST mevzuat revizyonu | Yönerge ve Pay Piyasası Prosedürü (rev. 54) 21.09.2026'da revize edilmiş [R]; içeriği kontrol edilmedi | Fiyat marjı ya da ilk gün baz fiyatı değiştiyse A2 ve bütün seri modelleri bozulur [Ç] | İki PDF'in önceki sürümle farkı |
| Kaldıraç yoğunluğu | Kredili işlem bakiyesi 109,9 milyar TL, kişi başı 2,49 milyon TL [R] | Düşüşte teminat tamamlama satışları taban kilitlerini uzatabilir [Ç] | TSPB haftalık |
| Vergi | 27.03.2026'dan itibaren TEFAS dışı serbest hisse yoğun fonlarda stopaj %0 → %17,5 ([PwC](https://www.pwc.com.tr/tr/sektorler/bankacilik-sermaye-piyasalari/bultenler/2026/gvk-gecici-67nci-madde-uyarinca-uygulanan-stopaj-oranlarinda-degisiklikler.html)) [R] | Yüksek başvurulu ve kurumsal talep kanalını etkiler; etkisi küçük [Ç] | — |

**Bu koşulların pratik sonucu: canlı sicil artık ortalama doğruluğu değil, rejim dayanıklılığını sınıyor.**
- Canlı sicil zaten kriz rejiminde. INTET 1 Eylül'de listelendi. NETGL'nin D10'u 30 Eylül olduğuna göre D1'i 17 Eylül, yani TEFAS işlemlerinin durdurulduğu gün [P, Ç].
- Eğitim kümesinde ise benzer bir stres altında ilk on seansını geçiren arz yok ya da çok az.
- Bu yüzden önceden yazılması gereken iki beklenti var [Ç]: D10 düşüş modelleri arz altına inmeyi olduğundan düşük tahmin edecek; "kaç gün tavan" modeli de seriyi olduğundan uzun görecek.
- `fon_krizi_2026` bayrağı model girdisi olmamalı; kartta bir "rejim dışı" uyarısı olarak gösterilmeli.

İki kontrol hemen yapılmalı: 21.09.2026 BIST revizyonunun farkı ve SPK'nın Eylül 2026'da piyasa geneline yeni tedbir getirip getirmediği. Mekanik kısıt A2'nin geçerliliği doğrudan bant kuralına bağlı.

## Sonuç

Türk halka arzlarında fiyat yolu, ±%10 bantla sınırlanmış bir kuyruk süreci. Bunun iki sonucu var. Birincisi, en güvenilir yapı öğrenilmesi gereken bir şey değil, kodlanması gereken bir kural. Limit adımı cinsinden mesafe, D10'daki yapısal sıfır ve kilit-dokunma ayrımı modele hazır verilirse, ~100 arzlık kıt veri ancak gerçekten belirsiz olan birkaç mekanizmaya ayrılabilir: kişi başı tahsisat, takvim yoğunluğu, ek satış ve bozulma günü kapanış tipi. İkincisi, D10 düşüşü ile "tavan bozulunca ne olur" aynı sorunun iki farklı zamandaki görünümü. Mekanik olarak D10 riski yalnız kısa serilerde ve bozulmadan sonraki taban kilitlerinde doğabiliyor. Bu yüzden iki modelin zincirlenmesi, ayrı ayrı eğitilmelerinden daha tutarlı olasılıklar üretir.

Literatürün de basının da serinin uzunluğunu ya da D10'da arz altına inmeyi sistematik olarak ölçmemesi bir eksiklik gibi görünse de aslında projenin sınırını gösteriyor. Ek satış bulgusunun hiçbir dış kaynakta olmaması, KAP grup verisi ve istikrar bildirimleriyle zenginleşmiş kendi verinin bu alandaki en ileri kaynak olduğunu gösteriyor. Aynı nedenle önümüzdeki aylarda canlı sicilde görülecek hatalar, ortalama bir dönemin değil eğitim kümesinin hiç görmediği bir stres rejiminin hataları olacak. Önceden yazılmış beklentilerle okunursa bu hatalar, hangi modelin rejim değişimine dayandığını gösteren ilk temiz kanıt olur.

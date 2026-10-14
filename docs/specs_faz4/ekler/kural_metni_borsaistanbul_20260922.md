# Kural metni alıntısı: Borsa İstanbul, Pay Piyasası, "Piyasa İşleyişi"

- Kaynak URL: https://www.borsaistanbul.com/piyasalar/pay-piyasasi/piyasa-isleyisi
- Erişim: 2026-09-22 (curl, HTTP 200). İndirilen HTML'nin sha256'sı: af1976338cc311b0cbdd5d89384d82cf97690e9feafd739a287fe4e8ec34cfa5
- Aşağıdaki satırlar sayfanın "Fiyat Aralığı ve Fiyat Marjları" ve "Fiyat Adımları" başlıklarından, etiketler temizlenerek aynen alınmıştır. Fiyat ya da bülten verisi indirilmemiştir.
- Sayfada halka arz edilen payın ilk işlem günü baz fiyatına dair açık bir hüküm YOKTUR (yalnız "baz fiyat yoksa" genel kuralı ve yeni pay alma hakları hükmü var). H99'da D1 referansı 95/99 arzda arz fiyatına eşit, 4 arzda arz fiyatının fiyat adımına yuvarlanmış hali (m4_cikti.txt §11).

## Alıntı

Fiyat Aralığı ve Fiyat Marjları
Baz Fiyat, Fiyat Aralığı
"Baz fiyat" bir payın gün boyunca işlem görebileceği alt ve üst fiyat limitlerinin belirlenmesine esas teşkil eden fiyattır. Baz fiyat bir önceki işlem gününün kapanış fiyatı ile hesaplanır. "Fiyat adımı" her pay fiyatı için bir defada gerçekleşebilecek en küçük fiyat değişimidir.
Baz fiyat yoksa (önceki kapanış yoksa veya fiyat serbest bırakılmışsa):
Tek fiyat işlem yöntemi ile işlem gören sıralar için ilk fiyatın oluştuğu emir toplama aşaması sonrasında belirlenen eşleşme fiyatı baz fiyat olacaktır.
Sürekli işlem yöntemi ile işlem gören sıralar için ilk işlemin fiyatı baz fiyat olarak alınacaktır (Açılış seansında fiyat oluşmuşsa bu fiyat, oluşmamışsa sürekli işlem aşamasında gerçekleşen ilk işlemin fiyatı baz fiyat olarak alınacaktır).
İşlem görecek yeni pay alma haklarında ilk gün sonuna kadar (ilk işlem günü dahil) baz fiyat uygulanmayacak ve işlem gördüğü ilk günün kapanış fiyatı ertesi günün baz fiyatını oluşturacaktır.
Ayrıca, bir önceki günden baz fiyata sahip bir payda gün içerisinde herhangi bir işlem gerçekleşmemişse bu baz fiyat, yine ertesi günün baz fiyatı olacaktır.
Varant ve sertifika sıralarında baz fiyat uygulanmaz.
Fiyat Marjı ve Fiyat Limitleri
Fiyat limitlerinin belirlenmesi amacıyla baz fiyata (bir önceki gün kapanış fiyatı) uygulanacak marjlar:
Yıldız Pazar’da %20, Ana Pazar’da %15,
Alt Pazar, YİP ve PÖİP’te %10
BYF’lerde %20
Yeni pay alma haklarında ve ISKUR.E’de %50
Varant ve sertifikalar için serbest marj
Emtia sertifikalarında %5
olarak belirlenmiştir.
Fiyat limitleri hesaplanırken yuvarlama işlemi içeri doğru yapılacaktır: Üst fiyat limiti bulunurken yuvarlama aşağı adıma, alt fiyat limiti bulunurken yuvarlama yukarı adıma yapılacaktır.

01/10/2020 tarihinden itibaren geçerli olmak üzere, Pay Piyasası’nda pazar yapılanması, pazarlardaki işlem görme esasları ve pazarlar arası geçiş kriterleri ile kota alma şartlarında bazı değişiklikler yapılmış ve bu değişiklikler Borsamızın 17/09/2020 tarihli ve 2020/58 sayılı duyurusu ile bilgilerinize sunulmuştur. Fiyat marjları ve devre kesici uygulamaları ile ilgili olarak da yeni pazar yapılanmasında genel esaslar belirlenmiş olmakla birlikte yeni bir duyuru yapılana kadar aşağıda özetlenen mevcut uygulama devam edecektir:
Fiyat marjı Yıldız Pazar, Ana Pazar, borsa yatırım fonları, gayrimenkul sertifikaları, gayrimenkul yatırım fonları ve girişim sermayesi yatırım fonlarında %10’dur.

Fiyat Adımları
PP’de işlem gören paylar, yeni pay alma hakları ve BYF’ler için aşağıdaki 1 ve 2 nolu tablolarda belirtilen fiyat seviyeleri ve fiyat adımları uygulanmaktadır.
Varantlarda, sertifikalarda ve Toptan Satış işlemlerinde her fiyat seviyesi için fiyat adımı 1 kuruş olarak uygulanmaktadır.
Kuruş altı hassasiyette (10 bps) fiyat gösterimi yöntemi uygulanmaktadır.
Paylarda ve Yeni Pay Alma Hakkı Kuponlarında Uygulanan Baz Fiyat Aralıkları ve Fiyat Adımları:

Fiyat Seviyesi (TL) — Fiyat Adımı (TL):
- 0,010 – 19,999: 0,010
- 20,000 – 49,999: 0,020
- 50,000 – 99,999: 0,050
- 100,000 – 249,999: 0,100
- 250,000 – 499,999: 0,250
- 500,000 – 999,999: 0,500
- 1.000,000 – 2.499,999: 1,000
- 2.500,000 – üzeri: 2,500

Not: "Fiyat Seviyesi" sütunu başlıkta "Baz Fiyat Aralıkları" diye anılır. H99 ölçümü (m4_cikti.txt §3): üst limit = referans × 1,10 değerinin, o değerin KENDİ fiyat seviyesindeki adıma aşağı yuvarlanması 990/990 seansta tutar; adımı referans fiyatın seviyesinden almak 931/990 tutar. Alt limit için yukarı yuvarlama 990/990 tutar.

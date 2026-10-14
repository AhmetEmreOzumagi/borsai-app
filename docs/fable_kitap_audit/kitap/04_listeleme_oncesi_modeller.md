# 4. Listeleme öncesi modeller

Bu bölüm, BorsAi'nin bir halka arz borsada **ilk kez işlem görmeden önce** tahmin üreten bütün modellerini ve basit kurallarını anlatır. "Listeleme öncesi" sözünün projedeki anlamı kesindir: tahmin, arzın ilk işlem günü T'den önce dondurulmuş bir kayda yazılır, bu kayıt commit edilir ve uzak depoya push edilir. Zaman kanıtı push'tur, bilgisayarın saati değil (`CLAUDE.md` kural 1). Bu aşamanın bütün modelleri tek bir dizinde listelenir: `models/INDEX.json`. Dizinde 27 giriş vardır. Her listeleme öncesi kayıt, o an dizinde bulunan modellerin **hepsinin** çıktısını ve her modelin parametre dosyasının sha256'sını içerir.

Projede iki aşama daha vardır: D1 akşamı güncellemesi (`models/INDEX_POST_D1.json`, `post_d1_hazard_v0`) ve kırılma akşamı modeli (`models/INDEX_POST_BREAK.json`, `break_floor_v0`). Onlar bu bölümün konusu değildir; yalnız bağlam için anılır.

Bölümün dili şudur: önce sezgi, sonra formül, sonra gerçek bir sayı. Gerçek sayıların neredeyse hepsi repodaki dosyalardan okunmuştur; elle hesapladığım örneklerde bunu açıkça yazıyorum. Örnek arz olarak NETGL'i kullanıyorum. NETGL 2026-09-17'de işlem görmeye başladı; listeleme öncesi kaydı `registry/records/NETGL/` altındadır.

---

## 4.1 Harita: hangi soru için hangi model

### 4.1.1 Temel kavramlar ve gösterim

Bütün bölüm boyunca şu gösterimi kullanıyorum (tanımlar `docs/specs/SPEC_SCORING.md` §2–§3 ve `borsai/horizons.py`'dendir):

| Sembol | Anlamı |
|---|---|
| T | Arzın ilk işlem günü (`first_trading_date`) |
| B(k) | k arzının ilk talep toplama günü (`first_bookbuilding_date`); talep toplama öncesi modellerin bilgi kesimi |
| D_h | İlk işlem gününden itibaren h'inci resmi Borsa İstanbul seansı (D1 = T) |
| P | Kesin arz fiyatı |
| R_h | Getiri: R_h = kapanış(D_h) / P − 1 |
| Y_h | "Yukarıda kapandı mı": Y_h = 1[kapanış(D_h) > P] |
| p_up_h | Modelin Y_h = 1 için verdiği olasılık, yani P(kapanış > arz fiyatı) |
| L | Tavan serisi: D1'den başlayan kesintisiz tavan kapanışı sayısı, 0..10 |
| S_k | P(L ≥ k): serinin en az k gün sürme olasılığı |
| H99 | Eğitim kohortu: ilk işlemi 2023-09-22 ile 2026-08-06 arasında olan 99 arz |

"Tavan kapanışı", kapanış fiyatının o seansın resmi üst fiyat limitine (THM bülteni) Decimal olarak tam eşit olmasıdır. Borsa İstanbul'da bu dönemde günlük fiyat marjı ±%10'dur; bu yüzden getirinin fiziksel sınırı vardır:

```
0.9^h − 1 ≤ R_h ≤ 1.1^h − 1        (D1: [−0.10, +0.10]; D10: [−0.651, +1.594])
```

Fiyat adımı yuvarlaması yüzünden gerçekleşen R_D1 bu sınırı çok az aşabilir (LILAK 0.10029, BORLS 0.10004; `borsai/horizons.py` notu).

### 4.1.2 Altı soru, altı aile

Listeleme öncesi modeller altı farklı soruya cevap verir:

1. **"D1, D3, D5, D10'da getiri ne olur?"** Çıktı R_h'nin nokta tahmini. Aile: V1.5 (`v1_5_h99`) ve ondan türeyenler (`v1_6_h99`, `v1_5_market20_v0`), talep toplama öncesi karşılığı `pb_v0`.
2. **"Kapanış arz fiyatının üstünde mi olur?"** Çıktı p_up_h. Aynı ailenin lojistik kafası.
3. **"Tavan serisi kaç gün sürer?"** Çıktı S_1..S_10. Aile: ayrık zamanlı tehlike modelleri (`ceiling_hazard_v0`, `pb_ceiling_v0`, `ceiling_hazard_v1_*`).
4. **"Tavan serisini bilerek getiri dağılımı ne olur?"** Çıktı R_h'nin bütün dağılımı (medyan, p_up, %10/%90 kuantil). Aile: tavan yolu (`ceiling_path_v0` ve iki varyantı).
5. **"Talep toplama bitmeden, yalnız SPK onaylı plandan ne söylenebilir?"** Talep katı (f3) henüz yokken çalışan PB modelleri (`pb_v0`, `pb_ceiling_v0`, `pb_ceiling_path_v0`).
6. **"Arz D10'da arz fiyatının altına düşer mi?"** Çıktı 1 − p_up_D10. Aile: düşen arz (C) modelleri (`fall_d10_v0_*`).

### 4.1.3 Dizindeki 27 giriş

Aşağıdaki tablo `models/INDEX.json`'dan doğrudan okunmuştur (sıra dizin sırasıdır). "Rol" sütunu benim sınıflandırmamdır: **model** özellik kullanır ve parametre öğrenir; **kural** özellik kullanmaz; **uç nokta** bir modelin ceza ızgarasının "özellik yok" ucudur ve kural gibi raporlanır.

| # | model_id | Algoritma | Eğitim n | Dondurma (yerel saat) | Rol | Soru |
|---|---|---|---|---|---|---|
| 1 | `v1_5_h99` | V1_5_RIDGE_LOGIT | 99 | 2026-09-21 | model | getiri, p_up |
| 2 | `base_always_ceiling` | ALWAYS_CEILING | 0 | 2026-09-21 | kural | getiri, p_up, tavan |
| 3 | `base_train_median` | TRAIN_MEDIAN | 99 | 2026-09-21 | kural | getiri |
| 4 | `base_train_mean` | TRAIN_MEAN | 99 | 2026-09-21 | kural | getiri |
| 5 | `base_zero` | ZERO | 0 | 2026-09-21 | kural | getiri |
| 6 | `base_rate` | BASE_RATE | 99 | 2026-09-21 | kural | p_up |
| 7 | `base_last10_rate` | LAST10_BASE_RATE | 99 | 2026-09-21 | kural | p_up |
| 8 | `v1_6_h99` | V1_5_RIDGE_LOGIT | 99 | 2026-09-22 | model | getiri, p_up |
| 9 | `v1_5_market20_v0` | V1_5_RIDGE_LOGIT | 99 | 2026-09-22 | model | getiri, p_up |
| 10 | `pb_v0` | V1_5_RIDGE_LOGIT | 99 | 2026-09-22 | model | getiri, p_up (PB) |
| 11 | `ceiling_hazard_v0` | discrete_time_hazard_logit_l2 | 97 | 2026-09-22 | model | tavan |
| 12 | `ceiling_hazard_v0@INF` | discrete_time_hazard_logit_l2 | 97 | 2026-09-22 | uç nokta | tavan |
| 13 | `pb_ceiling_v0` | discrete_time_hazard_logit_l2 | 99 | 2026-09-22 | model | tavan (PB) |
| 14 | `pb_ceiling_v0@INF` | discrete_time_hazard_logit_l2 | 99 | 2026-09-22 | uç nokta | tavan (PB) |
| 15 | `base_km_expanding` | KM_EXPANDING | 99 | 2026-09-22 | kural | tavan |
| 16 | `base_km_last10` | KM_LAST10 | 99 | 2026-09-22 | kural | tavan |
| 17 | `ceiling_path_v0` | CEILING_PATH_MIXTURE_EQ_V0 | 99 | 2026-09-22 | model | getiri dağılımı |
| 18 | `ceiling_path_v0@INF` | CEILING_PATH_MIXTURE_EQ_V0 | 99 | 2026-09-22 | uç nokta | getiri dağılımı |
| 19 | `pb_ceiling_path_v0` | CEILING_PATH_MIXTURE_EQ_V0 | 99 | 2026-09-22 | model | getiri dağılımı (PB) |
| 20 | `ceiling_hazard_v1_clip` | discrete_time_hazard_logit_l2 | 97 | 2026-09-27 | model | tavan |
| 21 | `ceiling_hazard_v1_real` | discrete_time_hazard_logit_l2 | 97 | 2026-09-27 | model | tavan |
| 22 | `ceiling_hazard_v1_pooled` | discrete_time_hazard_logit_l2 | 165 | 2026-09-27 | model | tavan |
| 23 | `ceiling_hazard_v1_pooled@INF` | discrete_time_hazard_logit_l2 | 165 | 2026-09-27 | uç nokta | tavan |
| 24 | `fall_d10_v0_h99` | l2_logit_v1_6_grid | 94 | 2026-09-28 | model | düşüş |
| 25 | `fall_d10_v0_pooled` | l2_logit_v1_6_grid | 161 | 2026-09-28 | model | düşüş |
| 26 | `fall_d10_v0_addsale` | l2_logit_v1_6_grid | 165 | 2026-09-28 | model | düşüş |
| 27 | `fall_d10_v0_pooled@ZERO` | l2_logit_v1_6_grid | 161 | 2026-09-28 | uç nokta | düşüş |

Hepsinin `training_cutoff_date` değeri 2026-08-19'dur (eğitimde kullanılan en son sonuç seansı); iki sabit kuralda (`base_always_ceiling`, `base_zero`) kesim yoktur. Dizindeki `frozen_at` alanı yerel saattir ve kendisi bunu söyler: "zaman kanıtı bu dosyayı içeren commit'in push'udur".

### 4.1.4 Neden bu kadar çok model var?

Yirmi yedi giriş ilk bakışta fazla görünür. Sayıyı dört proje kuralı üretir:

- **Değişiklik = yeni model_id** (`CLAUDE.md` kural 5). Özellik, ön işleme, ızgara, eğitim kesimi ya da veri sürümü değişirse eski model silinmez, yeni bir kimlik açılır. `v1_6_h99` yalnız ızgarası genişletilmiş V1.5'tir; yine de ayrı modeldir. Bu, "sonuca bakıp modeli sessizce düzeltme" yolunu kapatır.
- **Her model basit kurallarla eşleşik skorlanır** (kural 6). Kurallar da dondurulmuş dosyalardır; canlıda kuralın değeri de kayda girer, sonradan hesaplanmaz.
- **Izgara uç noktaları ayrı satırdır.** Ceza parametresi sonsuza giderse model "özellik yok" modeline döner. `@INF` ve `@ZERO` satırları bu ucu kural olarak kaydeder. Böylece "özellikler bir şey katıyor mu?" sorusu her zaman doğrudan ölçülür.
- **Terfi yok, yan yana modeller.** Faz 7 kararlarında bu açıkça yazılıdır: "Hiçbir model listeden kalkmaz ve başka bir modelin yerine geçmez" (`docs/specs_faz7/KARARLAR.md` K4). Uygulama bir modeli "öne çıkarabilir"; geri kalanlar listede ve kayıtlarda kalır.

Bir de "tasarıma maruziyet" kavramı var. H99'un sonuçları biliniyordu; gün grupları, özellikler ve ızgaralar bu sonuçlar görülerek seçildi. Bu yüzden H99 üzerindeki her backtest sayısı **tasarıma maruzdur**: model kendi gördüğü veride sınanmıştır, kanıt değeri düşüktür. Asıl ölçüm prospektiftir (canlı sicil) ya da hiç görülmemiş eski kohorttur (kasa). Bölümün sonuç tablolarını okurken bunu unutmayın.

Kaynak dosyalar: `models/INDEX.json`, `CLAUDE.md`, `docs/MODELS.md` ("Kayıtlı modeller"), `docs/specs/SPEC_SCORING.md` §2–§3, `docs/specs_faz7/KARARLAR.md`, `borsai/horizons.py`.

### 4.1.5 Basit kurallar

"Basit kural", hiçbir arz özelliğine bakmayan, yalnız eğitim hedeflerinden (ya da hiçbir şeyden) sabit bir tahmin üreten modeldir. Kuralların işi çıtayı koymaktır: bir model kuralı aralığı 0'ı dışlayacak biçimde yenemiyorsa, karmaşıklığı bir şey kazandırmıyor demektir. Getiri ve p_up kurallarının kodu `borsai/rules.py`'dedir (yalnız stdlib); tavan kuralları `borsai/survival.py`'dedir.

Getiri kuralları:

| Kural | Tanım | Dondurulmuş değer D1 / D3 / D5 / D10 |
|---|---|---|
| `base_always_ceiling` | Her seans tavan: R_h = 1.1^h − 1 | 0.1000 / 0.3310 / 0.6105 / 1.5937 |
| `base_train_median` | Eğitimdeki R_h'lerin medyanı | 0.1000 / 0.3297 / 0.3738 / 0.2471 |
| `base_train_mean` | Eğitimdeki R_h'lerin aritmetik ortalaması | 0.0774 / 0.2097 / 0.3121 / 0.4725 |
| `base_zero` | R_h = 0 | 0 / 0 / 0 / 0 |

Olasılık kuralları:

| Kural | Tanım | Dondurulmuş p_up D1 / D3 / D5 / D10 |
|---|---|---|
| `base_always_ceiling` | p_up = 1 | 1 / 1 / 1 / 1 |
| `base_rate` | Eğitimdeki Y_h ortalaması ("taban oranı") | 0.8990 / 0.8081 / 0.7778 / 0.7071 |
| `base_last10_rate` | (first_trading_date, ticker) sırasındaki son 10 eğitim arzının Y_h ortalaması | 0.6 / 0.5 / 0.4 / 0.5 |

Sezgi: `base_train_median` D1'de 0.1000'dır, çünkü H99 arzlarının çoğu ilk gün tavan kapanır ve medyan bu yığının içine düşer. Ortalama ise birkaç düşen arz yüzünden aşağı çekilir (0.0774). Bu fark önemlidir: **mutlak hatanın (MAE) en küçük olduğu sabit, medyandır**. Bir sabit tahmin c için Σ|y_i − c| fonksiyonu, c medyana eşitken en küçük değerini alır (c medyandan uzaklaştıkça noktaların en az yarısının hatası büyür, en çok yarısınınki küçülür). Ortalama ise kare hatayı en küçükler. Bu yüzden D1'de MAE ile ölçülen her doğrusal model, sabit terimi ortalamaya yakın olduğu için medyan kuralına yenilmeye yatkındır. Aşağıda V1.5'te bunun tam olarak gerçekleştiğini göreceğiz.

`base_last10_rate` kayan bir taban oranıdır; rejim değişirse hızlı tepki verir ama gürültülüdür. Dondurulmuş haliyle D5'te 0.4 vermesi (son 10 eğitim arzının yalnız 4'ü D5'te arz fiyatının üstünde kapanmış) bu gürültüyü gösterir.

Tavan kuralları S_1..S_10 üretir:

- `base_always_ceiling`: S_k = 1 (her arz 10 gün tavan).
- `base_km_expanding`: Kaplan–Meier tahmincisi, eğitimdeki **bütün** arzların kişi-dönem satırlarından (4.4'te ayrıntı). Gün başına tehlike h_d = olay_d / risk_d, S_k = Π_{d≤k}(1 − h_d). Bir günde risk altında arz yoksa önceki günün tehlikesi kullanılır.
- `base_km_last10`: Aynısı, ama her gün d için yalnız o günün satırı eğitimde bulunan **son 10 arz** kullanılır.

Dondurulmuş KM eğrileri (99 arz, kesim 2026-08-19):

| k | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| `base_km_expanding` S_k | 0.8182 | 0.7071 | 0.6667 | 0.5354 | 0.4141 | 0.3333 | 0.2727 | 0.2121 | 0.1717 | 0.1414 |
| `base_km_last10` S_k | 0.5000 | 0.4000 | 0.3200 | 0.2560 | 0.2048 | 0.1638 | 0.1311 | 0.1049 | 0.0734 | 0.0587 |

`base_km_last10`'un S_1 = 0.5 değeri, dondurma anındaki son 10 arzın 5'inin ilk gün tavan yapmadığını söyler; genişleyen KM ise bütün kohortu kullanır ve 0.8182 verir.

Uç nokta satırları da birer kuraldır: `ceiling_hazard_v0@INF`, `pb_ceiling_v0@INF`, `ceiling_hazard_v1_pooled@INF`, `ceiling_path_v0@INF` ve `fall_d10_v0_pooled@ZERO`. Bunlar ilgili model bölümlerinde anlatılıyor. Bir de yalnız backtest'te kullanılan, dosyası olmayan bir karşılaştırıcı vardır: `v1_5_p_up_as_ceiling`. V1.5 Logit'in aynı fold'daki p_up'ını "Dk'de tavan kapanışı olasılığı" yerine koyar (k ∈ {1, 3, 5, 10}); amacı, tavan modelinin V1.5'in zaten bildiğinden fazlasını söyleyip söylemediğini görmektir.

NETGL kaydındaki kural değerleri, dosyalardaki sabitlerin aynısıdır: örneğin `base_train_median` D5 için 0.3738 getiri, yani 25.52 TL × 1.3738 ≈ 35.06 TL fiyat.

Kaynak dosyalar: `borsai/rules.py`, `borsai/survival.py` (`km_hazards`), `models/base_*.json`, `registry/records/NETGL/20260922T121936Z_65a39d7392dd.json`, `docs/specs/SPEC_CEILING_V0.md` §10.

---

## 4.2 Ortak istatistik araç kutusu

Bu alt bölüm, sonraki bütün modellerde kullanılan yapı taşlarını sıfırdan anlatır. Her birinde önce sezgiyi, sonra formülü, sonra projedeki karşılığını veriyorum.

### 4.2.1 Lojistik regresyon

Bir olayın (örneğin "D10 kapanışı arz fiyatının üstünde") olasılığını özelliklerden tahmin etmek istiyoruz. Olasılık 0 ile 1 arasında kalmalıdır; doğrusal bir formül ise her değeri alabilir. Lojistik regresyon bu ikisini **sigmoid** fonksiyonuyla bağlar:

```
σ(η) = 1 / (1 + e^(−η))           η = b₀ + β₁x₁ + … + β_p x_p   ("doğrusal öngörücü")
p = σ(η)        ⟺        η = logit(p) = ln(p / (1 − p))
```

ln(p/(1−p)) "log-odds"tur. Bir katsayı β_j, x_j bir birim arttığında log-odds'un β_j kadar arttığını söyler; odds ise e^(β_j) katına çıkar. Örnek: β = −0.55 ise odds e^(−0.55) ≈ 0.577 katına iner.

Katsayılar **en çok olabilirlik** (maximum likelihood) ile bulunur. Gözlem i için gerçek etiket y_i ∈ {0, 1} ve tahmin p_i ise, negatif log-olabilirlik (log-kayıp) şudur:

```
NLL = −Σ_i [ y_i ln p_i + (1 − y_i) ln(1 − p_i) ]
```

NLL küçüldükçe model gözlenen etiketlere daha yüksek olasılık vermiş olur. Bu fonksiyon katsayılar açısından dışbükeydir; yani tek bir en küçük noktası vardır ve Newton–Raphson gibi yöntemlerle güvenle bulunur.

### 4.2.2 L2 cezası, Ridge ve "büzme"

Az veriyle çok katsayı kestirirsek model eğitim verisinin gürültüsünü öğrenir (aşırı uyum). L2 cezası buna karşı katsayıların karelerini amaca ekler:

```
J(β) = NLL(β) + (λ/2)·‖β‖²          ‖β‖² = β₁² + … + β_p²
```

λ büyüdükçe katsayılar 0'a doğru "büzülür" (shrinkage). λ → ∞ iken bütün β'lar 0 olur ve model yalnız sabit terimden ibaret kalır: bu, "özellik yok" modelidir. Sabit terim (projede γ ya da b₀) cezalandırılmaz; cezalandırılsaydı model taban oranını bile öğrenemezdi.

**Ridge regresyon** aynı fikrin sürekli hedefli halidir: ‖y − Xβ‖² + α‖β‖² en küçüklenir. α, λ'nın rolündedir. Projede getiri kafası Ridge'tir (`sklearn.linear_model.Ridge`, `solver="svd"`, sabit terim cezasız).

Bir isim karışıklığı: scikit-learn'ün lojistik regresyonu ceza gücünü **C** ile verir ve C, λ'nın tersi gibi çalışır (sklearn'ün amacı C·Σ log-kayıp + ½‖w‖²'dir; C'ye bölünce λ = 1/C olur). Yani **küçük C = güçlü büzme**, **büyük α = güçlü büzme**, **büyük λ = güçlü büzme**. V1.6 ızgarasındaki "C = ZERO" ve "α = INF" bu yüzden aynı şeyi söyler: yalnız sabit terim.

### 4.2.3 Ön işleme: log, kırpma (winsor), z-skor

Özellikler model tarafından görülmeden önce üç dönüşümden geçebilir:

- **Doğal log.** Arz büyüklüğü TL cinsinden yüz milyonlardan milyarlara uzanır; log bu ölçeği sıkıştırır: f1 = ln(büyüklük).
- **Kırpma (winsorize).** Eğitim kümesinin %5 ve %95 kuantilleri p05, p95 bulunur; bunların dışındaki değerler sınıra çekilir: x' = min(max(x, p05), p95). Uç değerlerin modeli sürüklemesini önler. Kuantil "Type-7" tanımıyla hesaplanır (R'ın varsayılanı, numpy'ın "linear" yöntemi): n sıralı değer için h = (n − 1)·p + 1; tam kısım j, kesir kısım g ise Q(p) = x_(j) + g·(x_(j+1) − x_(j)). Projede bu hesap kesin kesirlerle (`Fraction`) yapılır (`borsai/preprocess.py: quantile_type7`).
- **z-skor.** z = (x − μ) / σ; μ ve σ eğitim kümesinin ortalaması ve **popülasyon** standart sapmasıdır (ddof = 0, yani n'e bölünür). z-skor, farklı ölçekteki özellikleri karşılaştırılabilir yapar ve L2 cezasının hepsine eşit davranmasını sağlar.

Altın kural: bu parametrelerin (p05, p95, μ, σ) hepsi **yalnız eğitim kümesinden** öğrenilir, test arzına aynen uygulanır. Test arzının değeri hiçbir zaman μ'ya ya da σ'ya karışmaz. İç çapraz doğrulamada bile ön işleme her iç bölmede yeniden kurulur.

### 4.2.4 Çapraz doğrulama, LOOCV ve walk-forward

λ'yı (ya da α'yı, C'yi) nasıl seçeriz? Eğitim verisinde en iyi λ her zaman en küçük cezadır; bu bir şey söylemez. Görülmemiş veride nasıl davrandığını taklit etmek gerekir. **Çapraz doğrulama** (cross-validation) eğitim kümesini parçalara böler, her parçayı sırayla dışarıda tutar, kalanla fit eder ve dışarıdakini skorlar.

**LOOCV** (leave-one-out): her seferinde **bir** gözlem dışarıda kalır; n gözlem için n fit yapılır. Tavan modelinde bunun karşılığı "**bir arzı dışarıda bırak**"tır: bir arzın bütün kişi-dönem satırları birlikte dışarıda kalır, çünkü aynı arzın satırları birbirinden bağımsız değildir.

Projede iki katmanlı (iç içe) bir yapı vardır:

- **Dış katman: walk-forward backtest.** Arzlar ilk işlem tarihine göre sıralanır. Her test arzı k için eğitim kümesi, sonucu k'nın bilgi kesiminden (T ya da B(k)) **kesin önce** gerçekleşmiş arzlardır. Model o fold'da sıfırdan fit edilir ve yalnız k skorlanır. Bu, "o gün elimizde ne vardıysa onunla tahmin etseydik ne olurdu" sorusunun taklididir. Bir fold'un eğitimi çok küçükse (örneğin V1.5'te n < 10) fold skorlanmaz (`INSUFFICIENT_TRAINING_HISTORY`).
- **İç katman: LOOCV ile hiperparametre seçimi.** Her dış fold'un eğitim kümesi içinde, ızgaradaki her aday için iç LOOCV skoru hesaplanır; en iyi aday seçilir ve bütün eğitim kümesiyle son kez fit edilir.

Eşitlik kuralları önceden yazılıdır ve "daha çok büzen" tarafı seçer: Ridge'te eşit skorda en büyük α, lojistikte en küçük C, tehlike modelinde en büyük λ. Eşitlik yalnız bit düzeyinde eşit skorla tanınır; tolerans yoktur.

### 4.2.5 Skor ölçüleri

| Ölçü | Formül | Ne için |
|---|---|---|
| MAE | (1/n) Σ \|R̂_i − R_i\| | Getiri nokta tahmini |
| Brier | (1/n) Σ (p_i − y_i)² | Olasılık; 0 mükemmel, 0.25 "her zaman 0.5 de" |
| RPS | (1/10) Σ_{k=1..10} (S_k − 1[L ≥ k])² | Tavan serisi eğrisinin tamamı |
| Log-kayıp | −(1/n) Σ [y ln p + (1−y) ln(1−p)] | Olasılık (ikincil) |

**RPS** (ranked probability score) sıralı bir sonucun bütün dağılımını tek sayıyla ölçer: her k için "serinin en az k gün sürme olasılığı" ile gerçekte sürüp sürmediği arasındaki kare fark, 10 güne ortalanır. Seri L = 3 olduysa doğru eğri (1, 1, 1, 0, …, 0)'dır; model S'yi buna ne kadar yaklaştırırsa RPS o kadar küçük olur.

Backtest'te p_up Brier'i skorlamadan önce [0.01, 0.99]'a kırpılır (Faz 1A tablolarıyla aynı kural); tavan çıktılarında (S_k, RPS) kırpma yoktur. Faz 7 ve 7C hücrelerinde Brier kırpmasızdır.

### 4.2.6 Eşleşik fark, blok bootstrap ve hüküm sözcükleri

İki tahmini karşılaştırırken her arz için **fark = model kaybı − kural kaybı** hesaplanır ve ortalanır; **negatif fark = model iyi**. Bu "eşleşik" farktır: iki taraf da aynı arzlarda skorlanır.

Ortalama farkın belirsizliği **blok bootstrap** ile ölçülür. Sıradan bootstrap, gözlemleri birbirinden bağımsız sayıp iadeli yeniden çeker. Ama aynı ay listelenen arzlar aynı piyasa havasını paylaşır; bağımsız değildirler. Bu yüzden çekiliş **ay blokları** halinde yapılır: arzların ilk işlem ayları iadeli çekilir, çekilen ayların bütün farkları birleştirilip ortalanır. Backtest'te bu 4000 kez tekrarlanır, her karşılaştırma `random.Random(20260921)` ile ayrı başlar ve %95 aralık, sıralanmış 4000 değerin 100. ve 3899. elemanıdır (`docs/MODELS.md` "Backtest yöntemi"; SPEC_DEVIATIONS C7). Canlı ve zaman-dışı terazide aynı fikir numpy PCG64 üreticisiyle ve [2.5, 97.5] yüzdelikleriyle uygulanır (`docs/specs/SPEC_SCORING.md` §8).

Hüküm sözcükleri yalnız aralığa bakar:

- Aralık tamamen 0'ın altında → **"geçiyor"** (model daha iyi).
- Aralık tamamen 0'ın üstünde → **"geçemiyor"** (kural daha iyi).
- Aralık 0'ı içeriyor → **"ayırt edilemiyor"**.

Canlıda bu sözcükler ancak n ≥ 30 iken kullanılır; 10 ≤ n < 30'da "yetersiz örnek", n < 10'da yalnız satır tablosu gösterilir. Her modelin önceden ilan edilmiş **tek bir birincil hücresi** vardır; geri kalan hücreler "keşif" etiketi taşır. Bunun nedeni çoklu karşılaştırmadır: onlarca hücreye bakılırsa bazıları şans eseri "geçiyor" çıkar.

Kaynak dosyalar: `borsai/preprocess.py`, `borsai/fit.py`, `borsai/hazard.py`, `borsai/survival.py` (`rps`), `docs/specs/SPEC_SCORING.md` §7–§8, `docs/MODELS.md` ("Backtest yöntemi"), `scores/scores.json` (`definitions`).

---

## 4.3 Getiri ve p_up ailesi: V1.5, V1.6 ve market20

### 4.3.1 V1.5'in kökeni: ön kayıt

V1.5, projenin eski deposunda (`~/Desktop/Halka_Arz_Modeli`) doğmuş ve **ön kayıtla** dondurulmuş bir modeldir. Ön kayıt (preregistration), modelin bütün kurallarının (özellikler, ızgara, seçim amacı, eşitlik kuralı, yakınsamama politikası) **hiçbir fit yapılmadan önce** yazılıp mühürlenmesidir. `legacy/config/model_v1_5_spec.json` bunu kendi alanlarıyla söyler: `spec_version` = `BORSAI_V1_5_PREREG_20260814`, `status` = `FROZEN_PREREGISTRATION_NO_FIT_PERFORMED_NO_INSTALL_PERFORMED`. V1.5, V1'den V1.4'e uzanan bir zincirin son halidir; V1.4'ten farkı yalnız çalışma zamanı ve Ridge çözücü sözleşmesidir (V1.4 yazarının kendi eklediği bir "tekil değer kesme eşiği" geri çekilmiş, scikit-learn 1.9.0 sürümü sabitlenmiştir). Belge, değişikliğin hiçbir model sonucu görülmeden yapıldığını kayda geçirir.

Yeni repo bu modeli bit düzeyinde taşıdı (`docs/MODELS.md` "Port kabulü"): 351 fold'un hepsinde eğitim kümesi kimliği eşit, seçilen α 351/351, seçilen C 350/351 eşit; tek beklenen sapma macOS'ta D3|BETAE fold'unda iç LOOCV'nin yakınsamamasıdır. `legacy/` klasörü eski repodan birebir kopyadır ve değiştirilmez.

### 4.3.2 Özellikler f1–f5

Tanımlar `borsai/features.py`'dedir ve projede tek yerden gelir:

| Özellik | Tanım | NETGL değeri |
|---|---|---|
| f1 | Arz büyüklüğü TL: kaynakta bildirilen `ipo_size_tl`, yoksa fiyat × arz edilen pay; ön işlemede ln | 2 233 000 000 TL → ln = 21.5266 |
| f2 | Halka açıklık: arz edilen pay / arz sonrası sermaye × 100 | 87.5 mn / 312.5 mn × 100 = 28.0 |
| f3 | Toplam talep katı (`total_demand_multiple`); eksik ≠ 0 | 2.84 |
| f4 | Sermaye artırımı payı: sermaye artırımı payı / arz edilen pay × 100 | 62.5 / 87.5 × 100 = 71.4286 |
| f5 | 1 yalnız f3 eksikse, değilse 0 | 0 |

Sezgi: f3, talep toplamada arzın kaç kat talep gördüğüdür; karşılanmamış talep ilk günlerde ikincil piyasaya alıcı olarak döner. f1 büyüdükçe dağıtılan pay çoktur ve satıcı tarafı güçlenir. f2 ve f4 arzın yapısını anlatır.

### 4.3.3 Ön işleme (legacy V1.3, 11 adım)

`borsai/preprocess.py`'nin başındaki açıklama adımları sayar. Hepsi yalnız eğitim fold'undan öğrenilir:

| Adım | İş |
|---|---|
| 1 | f3 karşılaştırılabilirlik filtresi: eğitimdeki f3 dolu satırların `total_demand_filter_status` modu bulunur; durumu bu moda açıkça zıt (FILTERED / UNFILTERED) olan satırın f3'ü boşaltılır. H99'da "FILTERED" değeri hiç geçmediği için bu adım hiçbir satırı boşaltmaz. |
| 2–3 | Eksiklik oranı %40'tan büyük özellik fold'dan düşer. |
| 4 | f3 için Type-7 p05/p95 kırpma sınırları. |
| 5 | Kırpılmış değerlerin medyanıyla eksik doldurma (imputasyon). |
| 6 | f5 = 1[f3 eksik] (f3 düşmediyse). |
| 7 | f1'e doğal log (60 haneli Decimal). |
| 8 | Sıfır varyanslı özelliğin düşürülmesi (f3 düşerse f5 de düşer). |
| 9 | z-skor (popülasyon std); binary64'e dönüşüm z'den sonra bir kez yapılır. |

Dondurulmuş V1.5 parametreleri (99 arz): f3 kırpma [1.1487, 8.332]; ortalamalar f1 21.1775, f2 24.0627, f3 3.5510, f4 74.9579, f5 0.0202; standart sapmalar 0.7041, 6.5711, 2.0402, 17.7515, 0.1407; f3 medyanı 3.24.

### 4.3.4 İki kafa: Ridge ve L2-lojistik

Her ufuk h ∈ {D1, D3, D5, D10} için birbirinden bağımsız iki model fit edilir:

- **Ridge (getiri):** R̂_h = b₀ + Σ_j β_j z_j. α ızgarası {0.1, 1, 10, 100}. İç LOOCV amacı R_h uzayında MAE; eşitlikte en büyük α.
- **L2-lojistik (p_up):** p_up = σ(b₀ + Σ_j β_j z_j). C ızgarası {0.01, 0.1, 1, 10}; `lbfgs`, `max_iter = 10000`, `tol = 1e-10`, sınıf ağırlığı yok. İç LOOCV amacı ham (kırpılmamış) Brier; eşitlikte en küçük C.

Lojistik kafa için önceden yazılmış yozlaşma politikası vardır (`legacy/scripts/modeling/logistic_policy.py`): eğitimde tek sınıf varsa model fit edilmez (`MODEL_NOT_FIT_SINGLE_CLASS`); azınlık sınıfında 2'den az gözlem varsa ayar yapılmaz, C = 0.01 sabitlenir; V1.5'te herhangi bir iç fit yakınsamazsa bütün fold düşer.

Nihai fit (99 arz):

| Ufuk | α (Ridge) | C (Logit) | Logit sınıfları (Y=0 / Y=1) |
|---|---|---|---|
| D1 | 100 | 0.1 | 10 / 89 |
| D3 | 10 | 1 | 19 / 80 |
| D5 | 10 | 1 | 22 / 77 |
| D10 | 0.1 | 1 | 29 / 70 |

D1'de α = 100 ızgaranın üst ucu, D10'da α = 0.1 alt ucudur. Seçimin ızgara kenarına yapışması, ızgaranın yeterince geniş olmadığının işaretidir; V1.6 bunun için yazıldı.

D5 kafalarının katsayıları (z ölçeğinde, sıra f1..f5):

```
Ridge D5:  b₀ = 0.3121,  β = [−0.0897, +0.0338, +0.1221, −0.0072, −0.0586]
Logit D5:  b₀ = 1.9800,  β = [−0.7792, +0.2994, +1.3791, +0.0962, −0.6579]
```

Okuma: f3'ün (talep katı) katsayısı her iki kafada da en büyük ve pozitiftir; f1'in (büyüklük) katsayısı negatiftir. Yani büyük ve az talep gören arz, D5'te daha düşük getiri ve daha düşük "yukarıda kapanma" olasılığı alır.

**NETGL örneği (elle hesap, kayıtla eşit).** z = (x − μ)/σ ile z = [0.4959, 0.5992, −0.3485, −0.1988, −0.1436]. D5 Ridge:

```
R̂_D5 = 0.3121 + (−0.0897)(0.4959) + (0.0338)(0.5992) + (0.1221)(−0.3485) + (−0.0072)(−0.1988) + (−0.0586)(−0.1436)
     = 0.3121 − 0.0445 + 0.0202 − 0.0425 + 0.0014 + 0.0084 = 0.2552
```

D5 Logit doğrusal öngörücüsü 1.3677, p_up = σ(1.3677) = 0.797. Kayıttaki değerler: D1 getiri 0.0770 / p_up 0.913, D3 0.1847 / 0.8575, D5 0.2552 / 0.797, D10 0.2583 / 0.6023. (NETGL'in gerçekleşen D5 getirisi 0.0784, D10 getirisi −0.3617 oldu; tek arz bir değerlendirme değildir.)

### 4.3.5 Tahmin kuralları ve ret

`borsai/predict.py` yalnız Python standart kütüphanesiyle çalışır (numpy/sklearn import etmez; uygulamaya gömülebilsin diye). Kurallar:

- **f3 boşsa RET** (`F3_MISSING`). Gerekçe dosyada yazılıdır: f5'in katsayısı yalnız iki arzdan (ALBTN, ENDAE) öğrenildi; f3'süz çağrı "talep bilgisi henüz yok" durumunu "talep hiç gelmedi" diye okur. Backtest ise bu iki arzı legacy ile aynı biçimde f3 medyanı ve f5 = 1 ile tahmin edip skorlamıştır (8 fold).
- f3'ün filtre durumu eğitim moduna açıkça zıtsa RET.
- f1–f4 eğitim min/max dışında ise tahmin verilir, uyarı yazılır; f3 kırpılırsa uyarı.
- f4 = 0 kabul edilir ama "eğitimde örneği yok" uyarısı verilir.
- Getiri fiziksel sınıra [0.9^h − 1, 1.1^h − 1] kırpılır ve işaretlenir; kırpılmamış değer de döner. Backtest kırpmasız skorlar (351 tahminin 19'u sınır dışıydı).

### 4.3.6 V1.5'in backtest sonucu

Plan: `H99_WALK_FORWARD_STRICT_PRIOR_DATE_MIN_TRAIN_10`. Bir eğitim satırı (j, h) ancak j'nin D_h seansı test arzının T'sinden kesin önceyse girer; eğitim n ≥ 10. Skorlanabilir fold: D1 89, D3 88, D5 87, D10 87 (toplam 351). Lojistik kafa tek sınıflı eğitim fold'larında fit edilmediği için olasılık karşılaştırmaları daha az fold'dadır (D1 80, D3 80, D5 81, D10 81).

| Ufuk | Kural | Fark (MAE) | %95 aralık | n | Hüküm |
|---|---|---|---|---|---|
| D1 | `base_train_median` | +0.0046 | [+0.0015, +0.0079] | 89 | kural daha iyi |
| D1 | `base_train_mean` | −0.0035 | [−0.0060, −0.0011] | 89 | geçiyor |
| D3 | `base_train_median` | −0.0157 | [−0.0524, +0.0190] | 88 | ayırt edilemiyor |
| **D5** | **`base_train_median` (birincil)** | **−0.0839** | **[−0.1343, −0.0321]** | **87** | **geçiyor** |
| D10 | `base_train_median` | −0.1163 | [−0.1996, −0.0208] | 87 | geçiyor |
| D10 | `base_zero` | −0.0498 | [−0.2283, +0.1514] | 87 | ayırt edilemiyor |

| Ufuk | Kural | Fark (Brier) | %95 aralık | n | Hüküm |
|---|---|---|---|---|---|
| D1 | `base_rate` | −0.0078 | [−0.0286, +0.0115] | 80 | ayırt edilemiyor |
| D3 | `base_rate` | −0.0359 | [−0.0817, +0.0104] | 80 | ayırt edilemiyor |
| D5 | `base_rate` | −0.0343 | [−0.0773, +0.0106] | 81 | ayırt edilemiyor |
| D10 | `base_rate` | −0.0391 | [−0.0756, +0.0023] | 81 | ayırt edilemiyor |
| D10 | `base_last10_rate` | −0.0908 | [−0.1527, −0.0287] | 81 | geçiyor |

Okuma: V1.5'in birincil hücresi geçiyor. D1 MAE'de medyan kuralına yenilmesi 4.1.5'teki mekanizmanın ta kendisidir: D1 getirileri +%10'da yığılıdır, MAE'yi medyan en küçükler, Ridge'in sabit terimi ise ortalamadır. p_up kafası taban oranından hiçbir ufukta ayırt edilemiyor.

### 4.3.7 V1.6 (`v1_6_h99`): genişletilmiş ızgara

V1.6, V1.5'in **tek değişkenli** bir değişikliğidir: özellikler, ön işleme ve fold planı aynı; yalnız ızgara ve onun zorunlu kıldığı iki politika değişir (`docs/specs/SPEC_V1_6.md`).

| Kafa | V1.5 | V1.6 |
|---|---|---|
| Ridge α | 0.1, 1, 10, 100 | 0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000, INF |
| Logit C | 0.01, 0.1, 1, 10 | ZERO, 0.0001, 0.001, 0.01, 0.1, 1, 10, 100 |

- **INF / ZERO kapalı biçimdir.** α = INF tahmini eğitim ortalamasıdır; C = ZERO olasılığı eğitim oranıdır (n₁/n; cezasız sabitli lojistiğin tam çözümü). sklearn'e sıfır sütunlu matris verilmez.
- **Yakınsamama aday başına ele alınır.** V1.5'te bir iç fit yakınsamazsa bütün fold düşüyordu; V1.6'da yalnız o C adayı tablodan çıkar (`CANDIDATE_NOT_CONVERGED`). Nihai fit yakınsamazsa skor sırasındaki sonraki aday denenir. ZERO her zaman geçerlidir.

Nihai fit: D1 α = 100, C = 0.1; D3 α = 10, C = 1; D5 α = 10, C = 1; D10 α = 0.001, C = 1. NETGL'de V1.6, V1.5 ile D10 getirisi dışında aynı sayıları verdi (D10: 0.2579 ve 0.2583).

Sonuç (birincil hücre D10 MAE, `v1_5_h99`'a karşı): **+0.0008 [−0.0003, +0.0028], n = 87 → ayırt edilemiyor.** Sekiz hücrenin hepsi V1.5'ten ayırt edilemiyor; D3 ve D5 Brier'de fark tam sıfır (aynı C seçilmiş). Seçim dağılımı ilginçtir: D10 Ridge fold'larının %66'sında (57/87) α = 0.001, yani yeni ızgaranın alt ucu seçildi. Şartname "kenara yapışma > %50 olmamalı" demişti; bu beklenti **tutmadı**. D1 Ridge'te beklenen "çoğu fold α ∈ {1000, 10000, INF}" de tutmadı (%12); fold'ların 73/89'u α = 100 seçti.

### 4.3.8 market20 (`v1_5_market20_v0`): piyasa rejimi özelliği

Bu model V1.5'e tek bir özellik ekler (`docs/specs/SPEC_MARKET20_V0.md`):

```
f6 = XU100(S0) / XU100(S20) − 1
S0  = ref_date'ten KESİN önceki son resmi seans
S20 = ondan 20 seans önceki seans                (21 kapanış, 20 aralık)
```

Sezgi: arzdan önceki bir ayda borsa yükseldiyse ilgi canlıdır. f6 bir sonuç değil, tahmin anındaki girdidir. Ön işlemede yalnız z-skorlanır; log, kırpma, imputasyon ve eksiklik göstergesi yoktur. Izgara V1.5'inkiyle aynıdır (soru "f6 bilgi ekliyor mu" olduğu için ikinci bir değişken değiştirilmez).

Şartnamenin asıl işi bir takvim hatasını kapatmaktı: legacy kod takvimin bittiği yeri denetlemiyor, ileri bir tarih için sessizce bayat bir S0 döndürüyordu. Yeni kurallar f6'yı ancak şunların hepsi tutarsa üretir; aksi halde model RET eder: takvim ref_date − 1'i kapsıyor (`CALENDAR_NOT_COVERING`), en az 20 seans geçmiş var (`INSUFFICIENT_HISTORY`), 21 kapanışın hepsi var (`XU100_CLOSE_MISSING`), ref_date − S0 ≤ 12 gün (`STALE_S0`), canlıda T − tahmin tarihi ≤ 12 gün (`PREDICTION_TOO_EARLY`) ve kayıtlar yalnız XU100'den (`XU100_INTEGRITY`).

Backtest'te ref_date = T; canlıda ref_date = tahmin (dondurma) tarihidir. NETGL geç kaydedildiği için ref_date = T = 2026-09-17 alındı: S0 = 2026-09-16 (13122.58), S20 = 2026-08-19 (14458.98), f6 = 13122.58 / 14458.98 − 1 = −0.0924. Bu değer H99 aralığının [−0.1117, +0.1548] içindedir. Negatif f6, NETGL'in D10 getiri tahminini V1.5'in 0.2583'ünden 0.1436'ya indirdi.

Sonuç (birincil hücre D5 MAE, `v1_5_h99`'a karşı): **−0.0008 [−0.0178, +0.0137], n = 87 → ayırt edilemiyor.** Sekiz hücrenin sekizi de V1.5'ten ayırt edilemiyor. Beklenti "|ΔBrier| < 0.005" D10'da tutmadı (+0.0054); f6'nın Ridge katsayısı dört ufukta da pozitif ve küçük (beklendiği gibi). Şartname bu modelin sonucunun eski repoda zaten görüldüğünü açıkça yazar: kanıt değeri yoktur.

Kaynak dosyalar: `legacy/config/model_v1_5_spec.json`, `legacy/scripts/modeling/candidate_models.py`, `legacy/scripts/modeling/logistic_policy.py`, `borsai/features.py`, `borsai/preprocess.py`, `borsai/fit.py`, `borsai/predict.py`, `borsai/predict_market20.py`, `borsai/horizons.py`, `models/v1_5_h99.json`, `models/v1_6_h99.json`, `models/v1_5_market20_v0.json`, `docs/specs/SPEC_V1_6.md`, `docs/specs/SPEC_MARKET20_V0.md`, `docs/MODELS.md`, `scores/scores.json`.

---

## 4.4 Tavan serisi modeli: `ceiling_hazard_v0`

Bu model projenin listeleme öncesi ailesinde en çok emek verilmiş ve en çok kullanılan modeldir. Soru basittir: **"Bu arz kaç gün üst üste tavan kapanır?"** Cevap tek bir sayı değil, bir olasılık eğrisidir.

### 4.4.1 Neden "tehlike" (hazard) modeli?

L ∈ {0, 1, …, 10} sıralı bir sonuçtur. Her k için ayrı bir lojistik model (P(L ≥ 1), P(L ≥ 2), …) fit etmek mümkündü ama iki sorunu var: on model on kat parametre ister ve tahminler çelişebilir (P(L ≥ 5) > P(L ≥ 4) gibi). Tehlike modeli bunu yapısal olarak çözer.

**Ayrık zamanlı tehlike** h_d, "seri d − 1 gün sürdüyse d. gün bozulur mu" sorusunun olasılığıdır:

```
h_d = P(L = d − 1 | L ≥ d − 1)          d = 1..10
```

Seri ancak her gün "bozulmazsa" sürer; bu yüzden hayatta kalma olasılığı tehlikelerin çarpımıdır:

```
S_k = P(L ≥ k) = Π_{d=1..k} (1 − h_d)
```

Her çarpan 0 ile 1 arasında olduğu için S_1 ≥ S_2 ≥ … ≥ S_10 kendiliğinden sağlanır. Bu, hayatta kalma analizinin (survival analysis) ayrık zamanlı halidir; "hayatta kalan" burada hâlâ tavan serisinde olan arzdır.

Eğriden türeyen büyüklükler (`borsai/survival.py`):

```
P(L = 0)  = 1 − S_1
P(L = l)  = S_l − S_{l+1}            1 ≤ l ≤ 9
P(L = 10) = S_10
E[L]      = Σ_{k=1..10} S_k          (çünkü L = Σ_k 1[L ≥ k])
P(L ≥ k | L ≥ j) = S_k / S_j         ("j gün sürdü, k'ya ulaşır mı")
```

Son satır uygulamadaki "bugün tavan gitti, yarın ne olur" sorusunun cevabıdır ve yeni bir fit gerektirmez.

### 4.4.2 Kişi-dönem (person-period) veri yapısı

Tehlike modelini sıradan bir lojistik regresyonla fit etmenin hilesi veriyi yeniden düzenlemektir. Her arz, risk altında olduğu her gün için bir satır olur (`docs/specs/SPEC_CEILING_V0.md` §2):

- Arz i, gün d için satır ancak d − 1 ≤ L_i ise vardır (arz d. güne "risk altında" girmiştir).
- Olay: e = 1[L_i = d − 1], yani seri tam o gün bozuldu.

Üç örnek arz:

| Arz | L | Satırlar (d: olay) |
|---|---|---|
| A | 0 | d=1: 1 |
| B | 3 | d=1: 0, d=2: 0, d=3: 0, d=4: 1 |
| C | 10 | d=1..10: hepsi 0 |

C'nin bütün satırları 0'dır: seri 10 gün boyunca bozulmadı. 10'dan sonrası gözlenmediği için C **sağdan sansürlenmiştir** ("en az 10" biliyoruz, fazlasını bilmiyoruz). Kişi-dönem yapısı sansürü doğal olarak taşır.

H99'un 99 arzında 508 risk-günü ve 85 olay vardır (99 − 14; 14 arz 10 gün tavan kapandı):

| Gün d | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Risk | 99 | 81 | 70 | 66 | 53 | 41 | 33 | 27 | 21 | 17 |
| Olay | 18 | 11 | 4 | 13 | 12 | 8 | 6 | 6 | 4 | 3 |
| Ham tehlike | .182 | .136 | .057 | .197 | .226 | .195 | .182 | .222 | .190 | .176 |

Bu ham tehlikelerin çarpımı, genişleyen Kaplan–Meier eğrisidir (`base_km_expanding`): S_1 = 1 − 18/99 = 0.8182, S_2 = 0.8182 × (1 − 11/81) = 0.7071, … Kaplan–Meier, tehlikeyi her gün için "o gün bozulan / o gün risk altında olan" oranıyla tahmin eden, hiçbir özellik kullanmayan klasik yöntemdir.

Model f3'ü dolu 97 arzla eğitilir (ALBTN ve ENDAE'nin f3'ü yok; ikisi de L = 0): 506 satır, 83 olay, 423 sağ kalım.

### 4.4.3 Gün grupları

On gün için on ayrı sabit, gün başına 3–13 olayla bütçeyi tüketir. Şartname günleri üç gruba toplar:

```
g1 = {1}          g2 = {2, 3}          g3 = {4, …, 10}
```

Gerekçe (§3): D1 yapısal olarak ayrıdır (ilk fiyat oluşumu; dağıtım alan herkes ilk kez satabilir). D2–D3'ün tehlikesi belirgin düşüktür (grup toplamı 15/151 = 0.099). D4–D10 0.18–0.23 bandında düzdür (52/258 = 0.202). Her grupta en az 15 olay vardır. Şartname bu gruplamanın H99'un marjinal tehlike tablosuna bakılarak seçildiğini, yani **tasarıma maruz** olduğunu açıkça yazar; özellik–sonuç ilişkisine bakılmamıştır.

### 4.4.4 Özellikler ve ön işleme

| Ad | Tanım | Ön işleme |
|---|---|---|
| f1 | ln(arz büyüklüğü TL) | ln → z-skor |
| f2 | Halka açıklık % | z-skor |
| f3 | Toplam talep katı | eğitim [p05, p95]'ine kırpma → z-skor |

Tanımlar V1.5 ile aynı tek kaynaktan gelir. V1.5'ten farklar: imputasyon yok, f4 yok, f5 yok. Ön işleme **arz düzeyinde** hesaplanır (arz başına bir satır), kişi-dönem satırlarında değil; aksi halde uzun serili arzlar ortalamayı ve sapmayı ağırlıklandırırdı. Dondurulmuş değerler: ortalama f1 21.1717, f2 24.0539, f3 3.5574; std 0.7092, 6.6190, 2.0607; f3 kırpma [1.1487, 8.332].

Önceden yazılmış mekanizma (§4): talep fazlası (f3) karşılanmamış talebin ölçüsüdür, seriyi uzatmalı (β_f3 < 0, tehlikeyi azaltır); küçük arz (f1 düşük) ve düşük halka açıklık (f2 düşük) tavanda satıcıyı kısar (β_f1 > 0, β_f2 > 0). Şartname bir zayıflığı da önceden kaydeder: f1 nominal TL'dir ve 2023–2026 enflasyonu onu kaydırır. v0'da V1.5 ile eşlik için düzeltilmedi; bu not 4.7'deki v1 ailesinin tohumudur.

### 4.4.5 Model ve amaç fonksiyonu

```
logit h_d(x) = γ_{g(d)} + β · z(x)         β ∈ R³ (f1, f2, f3),  γ ∈ R³ (g1, g2, g3)

J(γ, β) = −Σ_r w_r [ e_r ln h_r + (1 − e_r) ln(1 − h_r) ] + (λ/2) · ‖β‖²
```

- r, kişi-dönem satırlarıdır (w = 1). Toplam 6 parametre; 83 olay → parametre başına ≈ 14 olay. Proje "10–15 olay/parametre" kuralını kullanır (AUDIT §3b'ye atıfla): bir lojistik modelde her katsayı için kabaca 10–15 azınlık olayı gerekir, yoksa kestirimler kararsızdır.
- β aynı anda bütün günlerde çarpan olarak etkir (**orantılı odds** varsayımı): özellik, her gün tehlikenin log-odds'unu aynı miktarda kaydırır.
- L2 cezası **yalnız β'ya** uygulanır; γ cezasızdır. sklearn seçici ceza veremediği için kullanılmaz; çözücü numpy ile yazılmış tam Newton–Raphson'dur.

**Pseudo-satırlar.** Her grup için z = 0'da bir olay (e = 1) ve bir olaysız (e = 0) satır, ağırlık 0.5 ile eklenir (6 satır). Neden? Erken walk-forward fold'larında bir grupta hiç olay olmayabilir (ilk 19 arzda D1 olayı 1'dir); o zaman γ_g'nin en çok olabilirlik değeri −∞'a kaçar. Pseudo-satırlar her gruba "yarım olay, yarım sağ kalım" ekleyerek bunu önler. Büyük örnekte etkileri ihmal edilir. Bir yan sonuç: λ = ∞ (β ≡ 0) iken her grup sabiti kapalı biçimde çözülür:

```
γ_g = logit( (olay_g + 0.5) / (risk_g + 1) ) = ln( (olay_g + 0.5) / (risk_g − olay_g + 0.5) )
```

**Newton–Raphson.** θ = (γ, β) için tasarım matrisi X = [G | Z] (G gün grubu kuklaları, Z z-skorları). Her yinelemede (`borsai/hazard.py: newton`):

```
h  = σ(Xθ)
∇  = Xᵀ( w ∘ (h − e) ) + pen ∘ θ               pen = (0, 0, 0, λ, λ, λ)
H  = Xᵀ diag( w ∘ h ∘ (1 − h) ) X + diag(pen)
Δ  = H⁻¹ ∇ ;   θ ← θ − s·Δ
```

s = 1 ile başlanır; J azalmazsa s yarılanır (en çok 30 kez; "azalmıyor" karşılaştırması toplama yuvarlaması kadar bir pay içinde yapılır). Başlangıç β = 0, γ = kapalı biçim. Durma: max|∇| ≤ 1e-10. 100 yinelemede durmazsa `MODEL_NOT_FIT_DID_NOT_CONVERGE`. Dondurulmuş nihai fit 5 yinelemede, max|∇| = 6.2e-15 ile durdu. Problem dışbükey olduğu için bu nokta tektir.

### 4.4.6 λ seçimi

Izgara: λ ∈ {0.1, 1, 3, 10, 30, 100, 300, 1000, INF}. Şartnamenin ölçek gerekçesi: bir β için Fisher bilgisi ≈ Σ h(1 − h) ≈ 508 × 0.14 ≈ 70; λ ≈ 70 katsayıyı kabaca yarılar; ızgara bunun iki yanına en az bir onluk taşar.

Seçim **iç arz-bırak çapraz doğrulama** ile yapılır: eğitimdeki her arz j için j'nin bütün satırları dışarıda tutulur, ön işleme kalan arzlardan yeniden kurulur, her λ için fit yapılır ve j'nin satırlarında log-kayıp toplanır. Skor = satır başına ortalama log-kayıp (h, [1e-12, 1 − 1e-12]'ye kırpılarak). En küçük skor kazanır; bit-eşit eşitlikte en büyük λ (INF en büyüktür). Bir λ'nın herhangi bir iç fit'i yakınsamazsa o λ o fold için ızgaradan çıkar; INF her zaman kalır.

Dondurulmuş nihai fit'in skor tablosu (`models/ceiling_hazard_v0.json`):

| λ | 0.1 | 1 | 3 | **10** | 30 | 100 | 300 | 1000 | INF |
|---|---|---|---|---|---|---|---|---|---|
| Skor | 0.40642 | 0.40618 | 0.40578 | **0.40543** | 0.40767 | 0.41761 | 0.43027 | 0.43937 | 0.44482 |

Seçilen λ = 10. INF (yalnız gün sabitleri) 0.44482 ile en kötüsüdür: özellikler satır başına log-kayıpta yaklaşık 0.039 kazandırıyor.

### 4.4.7 Dondurulmuş katsayılar ve yorumları

```
λ = 10
γ = [−1.8095, −2.1470, −1.0071]                  (g1, g2, g3)
β_f1 = +0.4489    β_f2 = −0.1787    β_f3 = −0.5499
```

- Ortalama arzın (z = 0) gün tehlikeleri σ(γ): g1 0.1407, g2 0.1046, g3 0.2675. Ortalama arzın eğrisi S = [0.859, 0.769, 0.689, 0.505, 0.370, 0.271, 0.198, 0.145, 0.106, 0.078].
- f1 bir standart sapma (ln ölçeğinde 0.709) artarsa her günün bozulma odds'u e^0.4489 ≈ 1.57 katına çıkar: büyük arzın serisi kısa.
- f3 bir standart sapma (2.06 kat talep) artarsa odds e^(−0.5499) ≈ 0.58 katına iner: yüksek talep seriyi uzatır.
- f2'nin işareti beklenenin tersidir (−0.1787; odds × 0.84): yüksek halka açıklık bu veride seriyi biraz uzatıyor. Şartnamenin "β_f2 > 0" beklentisi tutmadı.

**Yeniden tavan oranları.** İkincil çıktı P(Dk'de tavan kapanışı), serinin bozulduktan sonra yeniden tavan kapanabileceğini hesaba katar:

```
P_close_1 = S_1
P_close_k = S_k + (1 − S_k) · r_{b(k)}         b(k) = a (k ∈ 2..4), b (k ∈ 5..10)
r = (a + 0.5) / (n + 1)
```

n, eğitimde L < k olan arz-günleri, a bunlardan tavan kapananlardır. v0'da r_a = (1 + 0.5)/(102 + 1) = 0.0146, r_b = (61 + 0.5)/(429 + 1) = 0.1430. Varsayım kabadır (yeniden tavan olasılığı özelliklerden ve bozulma gününden bağımsız); bu yüzden ikincil çıktıdır.

### 4.4.8 Örnek: NETGL, adım adım

NETGL'in girdileri: büyüklük 2 233 000 000 TL, halka açıklık 28.0, talep katı 2.84 (kırpma aralığının içinde). Elle hesap (kaydın değerleriyle eşit):

```
z_f1 = (21.5266 − 21.1717) / 0.7092 = +0.5004     katkı  0.4489 × 0.5004 = +0.2247
z_f2 = (28.0    − 24.0539) / 6.6190 = +0.5962     katkı −0.1787 × 0.5962 = −0.1066
z_f3 = (2.84    − 3.5574)  / 2.0607 = −0.3481     katkı −0.5499 × −0.3481 = +0.1914
β·z = +0.3095   (büyük arz ve ortalamanın altındaki talep katı tehlikeyi artırıyor; yüksek halka açıklık biraz azaltıyor)

η_g1 = −1.8095 + 0.3095 = −1.5000   →  h_1      = σ(−1.5000) = 0.1824
η_g2 = −2.1470 + 0.3095 = −1.8375   →  h_2 = h_3 = 0.1373
η_g3 = −1.0071 + 0.3095 = −0.6976   →  h_4..h_10 = 0.3324
```

Hayatta kalma eğrisi ve türevleri:

| k | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| S_k | 0.8176 | 0.7053 | 0.6084 | 0.4062 | 0.2712 | 0.1811 | 0.1209 | 0.0807 | 0.0539 | 0.0360 |
| P(L = k) | 0.1123 | 0.0969 | 0.2022 | 0.1350 | 0.0901 | 0.0602 | 0.0402 | 0.0268 | 0.0179 | 0.0360 |

P(L = 0) = 0.1824. Beklenen seri E[L] = Σ S_k = 3.28 gün. Birikimli olasılık 0.1824, 0.2947, 0.3916, 0.5938 olduğu için birikimlinin ilk kez 0.5'i geçtiği değer (bu bölümde "medyan seri" dediğim değer) L = 3'tür. Koşullu okuma: üç gün tavan geldikten sonra dördüncü günün de tavan olma olasılığı S_4/S_3 = 0.668; seriyi 10'a taşıma olasılığı S_10/S_3 = 0.059.

NETGL'in gerçekleşen tavan dizisi 1110000000'dır, yani L = 3. Bu tek arz için RPS'ler: `ceiling_hazard_v0` 0.0570, `@INF` 0.0953, `base_km_expanding` 0.0968, `base_km_last10` 0.1244. Bu hesap yalnız formülü göstermek içindir; tek arz hüküm vermez ve NETGL kaydı LATE_RECORD sınıfındadır.

### 4.4.9 `ceiling_hazard_v0@INF`: özelliksiz uç

Aynı eğitim kümesinde λ = INF: β ≡ 0, γ kapalı biçim. Dondurulmuş γ = [−1.5972, −2.1755, −1.3695], yani tehlikeler g1 (16 + 0.5)/(97 + 1) = 0.1684, g2 (15 + 0.5)/(151 + 1) = 0.1020, g3 (52 + 0.5)/(258 + 1) = 0.2027. Girdi kullanmaz ve RET etmez; her arza aynı eğriyi verir (S = [0.8316, 0.7468, 0.6707, 0.5347, 0.4263, …, 0.1374]). Bu satır "üç özelliği eklemek, gün gruplu sabit bir eğriye göre ne kazandırıyor?" sorusunun ölçüsüdür.

### 4.4.10 Ret ve uyarılar

| Durum | Davranış |
|---|---|
| f3 boş | RET `F3_MISSING`; f3'süz tavan tahmini `pb_ceiling_v0`'dan gelir |
| f1/f2 hesaplanamıyor | etiketli RET |
| Girdi eğitim min/max dışında | tahmin + `OUT_OF_TRAINING_RANGE` uyarısı |
| f3 p05 altı / p95 üstü | kırpılır, `clipped = true`, uyarı |

### 4.4.11 Walk-forward planı

Plan kimliği: `H99_CEILING_PP_WALK_FORWARD_T_CUTOFF_F3_PRESENT_MIN10IPO_5EV_5SV`. V1.5'ten farkı, kısmi serilerin de eğitime girmesidir:

- Test arzı k (T = ilk işlem günü). Aday eğitim arzı j'nin satırı (j, d) ancak j'nin D_d seansı < T ise girer; ilk geçmeyen günde durulur. Yani T'den 3 seans önce listelenmiş bir arz eğitime en çok 3 satırla, sağdan sansürlü olarak girer. Sansürü sonuç değil takvim belirlediği için tehlike tahmini yansızdır (şartnamenin çıkarımı).
- Aynı gün listelenen arzlar birbirini eğitemez.
- Skorlanabilirlik: eğitim kişi-dönem kümesinde en az 10 arz, 5 olay ve 5 sağ kalım. 87 fold skorlanabilir; ilki EKOS (2023-11-21; eğitim 10 arz, 6 olay, 64 sağ kalım).
- Her fold'da iç CV ile λ seçilir, fold eğitimiyle nihai fit yapılır, test arzı için S_1..S_10 üretilir. Basit kurallar aynı fold'larda, aynı kişi-dönem eğitim kümesinden hesaplanır.

87 fold'da seçilen λ: 1 → 9, 3 → 40, 10 → 38 fold; INF hiç seçilmedi. Test kümesinin azınlıkları: L < 1: 16, L < 3: 31, L ≥ 5: 33, L ≥ 10: 11.

### 4.4.12 Backtest sonuçları

Birincil metrik RPS; şartname modelin **iki KM kuralını birden** yenmesini ister.

| Karşılaştırılan | n (ay) | Model | Kural | Fark | %95 aralık | Model iyi / kural iyi | Hüküm |
|---|---|---|---|---|---|---|---|
| `base_km_expanding` (birincil) | 87 (24) | 0.1503 | 0.2072 | −0.0569 | [−0.0833, −0.0286] | 59 / 28 | geçiyor |
| `base_km_last10` (birincil) | 87 (24) | 0.1503 | 0.1999 | −0.0496 | [−0.0751, −0.0219] | 52 / 35 | geçiyor |
| `ceiling_hazard_v0@INF` | 87 (24) | 0.1503 | 0.2006 | −0.0503 | [−0.0724, −0.0263] | 58 / 29 | geçiyor |
| `base_always_ceiling` | 87 (24) | 0.1503 | 0.5966 | −0.4462 | [−0.5488, −0.3236] | 74 / 13 | geçiyor |

Gün başına Brier (S_k), en iyi KM kuralına (`base_km_last10`) karşı: k = 1 −0.0271, k = 3 −0.0939, k = 5 −0.0726 (hepsinin aralığı 0'ın altında); k = 8, 9, 10'da −0.0204, −0.0105, −0.0055 (aralıklar 0'ı içeriyor). Kazanç ilk günlerde ve ortada yoğun, sonda kayboluyor.

Kalibrasyon (ortalama S_k ile gözlenen oran): k = 1 model 0.8655 / gözlenen 0.8161; k = 3 0.7041 / 0.6437; k = 5 0.4342 / 0.3793; k = 10 0.1874 / 0.1264. Model her k'da gözlenenden biraz yüksek; seriyi hafifçe uzun görüyor.

İkincil çıktı P(Dk tavan kapanışı): k = 1, 3, 5'te dört kuralı da geçiyor; V1.5'in p_up'ını tavan olasılığı sayan karşılaştırıcıya karşı k = 1, 5, 10'da geçiyor, k = 3'te ayırt edilemiyor (−0.0290 [−0.0668, +0.0036]); k = 10'da KM'lerden ve @INF'ten ayırt edilemiyor.

Koşullu keşif (yeni model değil; "seri j. günde sürüyor" iken S_k/S_j): j = 1'de model `base_km_last10`'a karşı koşullu RPS'te −0.0408 [−0.0735, −0.0073] ile önde, j ≥ 2'de iki KM kuralından ve `@INF`'ten ayırt edilemiyor (`base_always_ceiling`'e karşı aralık j ≤ 7'de 0'ın altında kalıyor). Okumam: modelin üstünlüğünün büyük kısmı "seriye başlayacak mı ve ilk günleri geçecek mi" ayrımından geliyor; seri birkaç gün sürdükten sonra özellikler eğriyi KM'den belirgin farklı kılmıyor.

**Önceden yazılmış beklenti ile gerçekleşen** (şartname §11, sonuçlar görülmeden 2026-09-21'de yazıldı):

| Beklenti (aynen) | Gerçekleşen | Tuttu mu |
|---|---|---|
| RPS farkı (model − en iyi KM): −0.005 … −0.02; aralık büyük olasılıkla 0'ı içerir | −0.0496 [−0.0751, −0.0219] | tutmadı (beklenenden iyi) |
| En çok kazanç k = 3…5'te; k = 1'de küçük; k = 10'da ≈ 0 ya da hafif kötü | en çok k = 3; k = 1'de −0.0271 (küçük değil); k = 10'da −0.0055 | kısmen |
| Seçilen λ çoğu fold'da 10–300; erken fold'larda INF sık | {10..300} payı %44; ilk 20 fold'da INF %0 | tutmadı |
| Nihai işaretler β_f3 < 0, β_f1 > 0, β_f2 > 0 | +0.4489, −0.1787, −0.5499 | kısmen (β_f2 ters) |
| Başarısızlık (c): model @INF'ten noktasal kötü | −0.0503 | gerçekleşmedi |

Bu tablo dürüstlüğün kendisidir: model, yazarının beklediğinden **daha iyi** çıktı. Proje bunu iyi haber diye değil, "aşırı iyi sonuç denetlenmeli" diye okur; v0 için bağımsız uygunluk ve sızıntı denetimi yapıldı (`GITLOG.txt`: BORSAI_FAZ1B_CONFORMITY, "all models PUSH_OK"). Asıl ölçüm prospektiftir; şartnamenin başarı ölçütü canlı n ≥ 30'da iki KM kuralına karşı aralığın 0'ı negatif tarafta dışlamasıdır.

Kaynak dosyalar: `docs/specs/SPEC_CEILING_V0.md`, `borsai/hazard.py`, `borsai/survival.py`, `borsai/predict_hazard.py`, `models/ceiling_hazard_v0.json`, `models/ceiling_hazard_v0@INF.json`, `models/base_km_expanding.json`, `models/base_km_last10.json`, `registry/records/NETGL/20260922T121936Z_65a39d7392dd.json`, `docs/MODELS.md` (`ceiling_hazard_v0`, koşullu keşif), `docs/SCORES.md` §1, `scores/scores.json`, `GITLOG.txt`.

---

## 4.5 Talep toplama öncesi (PB) modeller: `pb_v0` ve `pb_ceiling_v0`

### 4.5.1 Neden ayrı bir aile?

V1.5 ve `ceiling_hazard_v0` talep katını (f3) ister. Ama f3 ancak talep toplama bittikten sonra, sonuç bildirimiyle açıklanır. Kullanıcı bir arzı SPK onayından hemen sonra, talep toplamaya katılıp katılmamaya karar verirken görür. Eski depoda bu boşluk V1.5'in f3'süz çağrılmasıyla doldurulmuştu; denetim bunu geçersiz kullanım saydı (AUDIT §1.2-d): f5 katsayısı yalnız iki arzdan öğrenilmişti. PB ("pre-bookbuilding") modelleri bu boşluğu yalnız **SPK onaylı planlanan yapıyla** doldurur (`docs/specs/SPEC_PB_V0.md`).

**Bilgi kesimi B(k).** Test arzı k için eğitim satırı ancak hedef seansı k'nın ilk talep toplama gününden (B(k)) kesin önceyse girer. V1.5'te kesim T'dir. H99'da T − B en az 4, medyan 8, en çok 12 gündür; yani PB modelleri V1.5'e göre birkaç arz daha az eğitim verisi görür.

### 4.5.2 Girdiler ve özellikler

Sekiz sayısal alan okunur, başka hiçbir alan okunmaz (kabul testi bunu sınar): `ipo_price_try`, `planned_pre_ipo_capital`, `planned_post_ipo_capital`, `planned_capital_increase_shares`, `planned_existing_share_sale`, `planned_base_offer_shares`, `planned_additional_sale_ceiling`, `planned_max_offer_shares`. Hepsi Decimal olarak kesin eşitlikle üç özdeşliği sağlamalıdır:

```
ID-A:  planlanan arz sonrası sermaye = arz öncesi sermaye + sermaye artırımı payı
ID-B:  baz arz payı = sermaye artırımı payı + ortak satışı payı
ID-C:  azami arz payı = baz arz payı + ek satış tavanı
```

Özellikler (`borsai/features.py: compute_pb_features`):

| Ad | Tanım | NETGL |
|---|---|---|
| pb1 | ln(fiyat × baz arz payı) | 21.5266 |
| pb2 | baz arz payı / arz sonrası sermaye × 100 | 28.0 |
| pb3 | sermaye artırımı payı / baz arz payı × 100 | 71.4286 |
| pb4 | ek satış tavanı / baz arz payı × 100 — **özellik değil** | 0 |

pb4 özellik değildir çünkü 99 arzın 92'sinde 0'dır; bilgi içeriği 7 satırdır. pb4 > 0 ise yalnız "ek satış tavanı var; eğitimde 7 örnek" uyarısı verilir. H99'da planlanan değerler çoğu arzda nihai değerlere eşittir (fiyat 0/99 arzda farklı, pay adedi 10/99, sermaye artırımı payı 2/99); PB'nin V1.5'ten asıl farkı f3'ün yokluğu ve bilgi kesimidir.

Ret kuralları: bir alan boşsa `PB_FIELD_MISSING` (imputasyon yok); özdeşlik ya da aralık bozuksa `PB_IDENTITY`; fiyat tek değer değilse (fiyat aralığı) `PB_PRICE_RANGE`. Ön işleme yalnız z-skordur (pb1'in log'u tanımın içindedir).

### 4.5.3 `pb_v0`: getiri ve p_up

V1.5 ile aynı sınıf (ufuk başına Ridge + L2-lojistik), özellikler pb1–pb3, ızgara V1.6'nınki. Tek fark: azınlık sınıfı 2'den azsa C = ZERO (yalnız sabit) seçilir (`PB_GRID`); PB'de en muhafazakâr seçenek zaten ızgaradadır. Bütçe açıkça yazılmış bir tavizdir: D1'de 10 azınlık olayıyla 3 katsayı "10–15 olay/parametre" kuralının üstündedir; rapor D1 p_up'ını "bütçe üstü" notuyla gösterir.

Nihai fit (99 arz): D1 α = 10, C = 0.1; D3 α = 1, C = 0.1; D5 α = 0.001, C = 0.1; D10 α = 0.001, C = 0.1. z-skor parametreleri: ortalama pb1 21.1800, pb2 24.1184, pb3 74.8182; std 0.7058, 6.6387, 17.2487. NETGL için: D1 0.0730 / 0.8922, D3 0.1896 / 0.8101, D5 0.2680 / 0.7755, D10 0.3335 / 0.6732 (getiri / p_up).

Backtest (plan `H99_PB_WALK_FORWARD_BOOKBUILD_CUTOFF_MIN_TRAIN_10`; fold D1 87, D3 87, D5 87, D10 84; kurallar aynı PB kesimiyle aynı fold'larda):

| Hücre | Fark | %95 aralık | n | Hüküm |
|---|---|---|---|---|
| **D5 MAE − `base_train_median` (birincil)** | **−0.0355** | **[−0.0775, +0.0102]** | **87** | **ayırt edilemiyor** |
| D1 MAE − `base_train_median` | +0.0083 | [+0.0047, +0.0125] | 87 | kural daha iyi |
| D10 MAE − `base_train_median` | −0.0478 | [−0.1067, +0.0146] | 84 | ayırt edilemiyor |
| D1 Brier − `base_rate` | −0.0025 | [−0.0080, +0.0018] | 80 | ayırt edilemiyor |
| D10 Brier − `base_rate` | −0.0147 | [−0.0259, −0.0042] | 80 | geçiyor |

"Talep katının değeri" bilgi hücresiyle ölçülür: `pb_v0 − v1_5_h99`, aynı test arzlarında. MAE farkları D1 +0.0036, D3 +0.0229, D5 +0.0530 [+0.0337, +0.0726], D10 +0.0880 [−0.0062, +0.1732]: D1–D5'te V1.5 belirgin iyi. Brier farkları dört ufukta da ayırt edilemiyor.

Beklentiler (§8): "D1 MAE medyana yenik ya da eşit, D1 p_up taban oranından ayırt edilemez" tuttu; "V1.5'e karşı her ufukta kötü ya da eşit" tuttu; "seçilen α çoğunlukla ≥ 100" tutmadı (%27); "D5/D10'da medyana karşı kazanç V1.5 kazancının en çok üçte biri olur" tutmadı: noktasal kazançlar (D5 −0.0355, D10 −0.0478) bu sınırdan büyük çıktı, aralıklar ise 0'ı içerdi.

### 4.5.4 `pb_ceiling_v0`: talep toplama öncesi tavan serisi

`ceiling_hazard_v0`'ın aynı kodu; farklar: özellikler pb1 ve pb2 (2 katsayı + 3 gün sabiti = 5 parametre; pb3 bütçe ve zayıf mekanizma yüzünden dışarıda), eğitim 99 arzın hepsi (f3 şartı yok; ALBTN ve ENDAE dahil, 508 satır, 85 olay), walk-forward kesimi B(k), kırpma yok.

Dondurulmuş fit: λ = 10 (iç CV skoru 0.43240; INF 0.44996); γ = [−1.5693, −2.1625, −1.1973]; β_pb1 = +0.4445, β_pb2 = −0.1462. Yeniden tavan oranları r_a = (2 + 0.5)/(108 + 1) = 0.0229, r_b = (61 + 0.5)/(441 + 1) = 0.1391. İşaretler f1 ve f2'ninkilerle aynı yönde.

NETGL: z_pb1 = 0.4910, z_pb2 = 0.5847, β·z = +0.1328; S = [0.8079, 0.7141, 0.6312, 0.4693, 0.3490, 0.2595, 0.1929, 0.1435, 0.1067, 0.0793]. f3 bilgisi olmadığı için eğri `ceiling_hazard_v0`'ınkinden daha "ortalama"dır (S_10 0.079'a karşı 0.036).

`pb_ceiling_v0@INF`: γ = [−1.4828, −2.1755, −1.3695]; g1 tehlikesi (18 + 0.5)/(99 + 1) = 0.185 (99 arzın 18'i D1'de tavan yapmadı).

Backtest (87 fold, ilki SKYMD; seçilen λ: 1 → 1, 3 → 23, 10 → 62, 30 → 1):

| Karşılaştırılan | Fark (RPS) | %95 aralık | n | Hüküm |
|---|---|---|---|---|
| `base_km_expanding` (birincil) | −0.0324 | [−0.0544, −0.0114] | 87 | geçiyor |
| `base_km_last10` (birincil) | −0.0335 | [−0.0612, −0.0019] | 87 | geçiyor |
| `pb_ceiling_v0@INF` | −0.0235 | [−0.0367, −0.0083] | 87 | geçiyor |
| `ceiling_hazard_v0` (bilgi; talep katının değeri) | +0.0342 | [+0.0180, +0.0515] | 85 | v0 daha iyi |

Şartname "KM kurallarından ayırt edilemez; v0'dan kötü ya da eşit" demişti. İkinci parça tuttu; birinci parça tutmadı (model KM'leri geçti). Talep katının tavan serisindeki değeri RPS'te yaklaşık 0.034'tür.

Kaynak dosyalar: `docs/specs/SPEC_PB_V0.md`, `borsai/features.py` (`compute_pb_features`), `borsai/predict_pb.py`, `borsai/predict_hazard.py`, `borsai/fit.py` (`PB_GRID`), `borsai/preprocess.py` (`PB_RECIPE`, `PB_CEILING_RECIPE`), `models/pb_v0.json`, `models/pb_ceiling_v0.json`, `models/pb_ceiling_v0@INF.json`, `docs/MODELS.md` (`pb_v0`, `pb_ceiling_v0`), `scores/scores.json`.

---

## 4.6 Tavan yolu modelleri: `ceiling_path_v0`, `@INF`, `pb_ceiling_path_v0`

### 4.6.1 Fikir

Tavan modeli "seri kaç gün sürer" der ama "D5'te getiri ne olur" demez. V1.5 getiriyi söyler ama Borsa İstanbul'un mekaniğini bilmez: bir arz D1–D5 tavan kapanırsa D5 kapanışı neredeyse kesin olarak bellidir. Tavan yolu modeli ikisini birleştirir (`docs/specs_faz4/SPEC_CEILING_PATH_V0.md`):

```
R_h'nin dağılımı = [ seri h gün sürer: limit yolu getirisi ρ_h, ağırlık S_h ]
                 + [ seri t < h günde kırılır: kırılma sonrası ampirik getiriler, ağırlık P(L = t) ]
```

Üç bileşen vardır: (1) dondurulmuş bir tavan modelinin S_k'sı (yeniden fit yok; JSON'un içine sha'sıyla birebir gömülür), (2) deterministik limit yolu C_h, (3) kovaryatsız, ampirik kırılma sonrası hücreler. **Yeni serbest parametre sayısı 0'dır.** Üç kimlik: ana model `ceiling_hazard_v0`'ın S'ini kullanır (f3 ister); sıfır model `ceiling_hazard_v0@INF`'in sabit S'ini kullanır (girdi istemez, "katkı yalnız mekanik mi" sorusunun ölçüsü); PB varyantı `pb_ceiling_v0`'ın S'ini ve planlanan fiyatı kullanır.

### 4.6.2 Limit yolu C_h

Seri h gün sürerse D_h kapanışı, art arda h üst limittir. Üst limit "%10 yukarı, sonra fiyat adımına aşağı yuvarla" kuralıyla hesaplanır. Kural metni ve adım tablosu borsaistanbul.com'un Pay Piyasası işleyiş sayfasından alınmış, sayfanın sha256'sıyla kaydedilmiştir:

| Fiyat aralığı | [0.01, 20) | [20, 50) | [50, 100) | [100, 250) | [250, 500) | [500, 1000) | [1000, 2500) | ≥ 2500 |
|---|---|---|---|---|---|---|---|---|
| Adım | 0.01 | 0.02 | 0.05 | 0.10 | 0.25 | 0.50 | 1.00 | 2.50 |

```
adım(x)  = x'in düştüğü aralığın adımı
U(b)     = floor( b·1.10 / adım(b·1.10) ) · adım(b·1.10)     (üst limit; adım limitin kendi seviyesinden)
snap(P)  = round_half_up( P / adım(P) ) · adım(P)              (D1 baz fiyatı)
C_1 = U(snap(P)),   C_k = U(C_{k−1}),   ρ_h = C_h / P − 1
```

Bu yol H99'da seri ≥ h olan her arzın gerçek kapanışını **424/424** Decimal eşitlikle üretir. Basit 1.1^h formülü D10'da medyanda yaklaşık 0.8 puan fazla tahmin ederdi; düşük fiyatlı arzlarda fark daha büyüktür. D1 baz fiyatı 95/99 arzda arz fiyatının kendisidir; 4 arzda (BORLS, AVPGY, ARTMS, LILAK) adıma yuvarlanmış halidir ve HALF_UP seçimi bu dördüyle tutar.

NETGL (P = 25.52; adım 0.02): C = 28.06, 30.86, 33.94, 37.32, 41.04, …; ρ = 0.0995, 0.2092, 0.3299, 0.4624, 0.6082, … Örneğin C_1 = floor(28.072 / 0.02) × 0.02 = 28.06.

### 4.6.3 Kırılma sonrası hücreler

Seri t < h günde sürüp D_{t+1}'de kırılırsa getiri yol bağımlıdır:

```
R_h = (C_t / P) · (1 + G) − 1          G = kapanış(D_h) / kapanış(D_t) − 1     (t = 0'da C_0 = P)
```

G, son limit-yolu gününden D_h'ye kadar olan getiridir. G'nin dağılımı ampirik olarak, eğitim arzlarının gerçekleşmiş yollarından "hücrelere" toplanır:

- **Grup Z** (t = 0): D1 tavan kapanmadı; fiyat ilk gün serbest oluştu. m = h ∈ 1..10.
- **Grup B** (1 ≤ t ≤ 9): seri t gün sürdü, D_{t+1}'de kırıldı. m = h − t ∈ 1..9 (t'ye göre ayrıca bölünmez).

m, son limit-yolu gününden bu yana geçen seans sayısıdır. Gerekçe ölçümle desteklenir: m = 1'de Z medyanı −0.0011 (18 arzın 8'i arz fiyatının üstünde), B medyanı −0.0949 (kırılma günü çoğunlukla alt limitte). B içinde t'ye göre bölmek m = 1 medyanlarını değiştirmiyor (−0.089 / −0.0995 / −0.094), yalnız hücreleri küçültüyor. Gruplama, eşik ve havuzlama sırası bu ölçümler görüldükten sonra seçildi; tasarıma maruzdur.

Dondurulmuş hücreler (99 arz, kesim 2026-08-19, toplam 567 gözlem): Z'nin her m hücresinde 18 gözlem; B için m = 1..9: 67, 64, 60, 54, 48, 40, 28, 15, 11. Hücre medyanları Z m = 1..10: −0.0011, −0.0517, −0.0496, −0.0557, −0.0718, −0.0895, −0.0979, −0.0752, −0.0692, −0.0824; B m = 1..9: −0.0949, −0.1294, −0.1308, −0.1539, −0.1589, −0.1508, −0.1534, −0.1653, −0.1663.

**Havuzlama merdiveni** (N_MIN = 10). Bir hücre (g, m) 10'dan az gözlem içerirse deterministik olarak genişletilir: önce kendi hücresi; sonra diğer grubun aynı m'si; sonra m − 1, m + 1, m − 2, m + 2, … sırasıyla iki grubun o m hücreleri. n ≥ 10 olunca durulur. Havuzlanan değerler hedef m'nin fiziksel sınırına [0.9^m − 1, 1.1^m − 1] kırpılır. Hücreler tükenip n < 10 kalırsa getiri üretilmez (`POST_BREAK_INSUFFICIENT`); backtest'in 87 fold'unda bu hiç olmadı.

### 4.6.4 Karışım, medyan ve p_up

Her ufuk h için ayrık atom listesi kurulur (ağırlık toplamı 1):

```
(ρ_h,                    S_h)                                 limit yolu atomu
(v,                      P(L = 0) / n_Z)        v ∈ hücre(Z, h)
((C_t/P)(1 + v) − 1,     P(L = t) / n_B)        v ∈ hücre(B, h − t),  t = 1..h−1
```

- **Nokta tahmini = karışımın medyanı** (MAE için doğru seçim; şartnamede sonuç görülmeden yazıldı). Kuantil kuralı: atomlar r'ye göre sıralanır, birikimli ağırlık F; Q(q), F ≥ q − 1e-12 olan ilk atomun r'sidir. Ayrıca q10 ve q90 verilir.
- **p_up = Σ{w : r > 0}** (kesin >).
- Ortalama (Σ w·r) yalnız ikincil gösterimdir.

Kendiliğinden gelen özellikler: getiri ≤ ρ_h; **S_h ≥ 0.5 ise medyan = ρ_h** (limit atomu tek başına yarıyı geçer); p_up ≥ S_h.

**NETGL örneği** (illüstrasyon: bu model NETGL için RETRO'dur, kaydı yoktur; değerler `borsai.predict_path.predict` ile hesaplandı):

- D1: S_1 = 0.8176 ≥ 0.5, bu yüzden medyan = ρ_1 = 0.0995. p_up = S_1 + P(L = 0) × (Z m = 1 hücresinde v > 0 olanların payı) = 0.8176 + 0.1824 × 8/18 ≈ 0.8986.
- D3: S_3 = 0.6084 ≥ 0.5 → medyan ρ_3 = 0.3299; p_up 0.7897; q10 −0.1083.
- D5: S_5 = 0.2712 < 0.5 → medyan limit atomundan çıkar: 0.2361; p_up 0.7436; q10 −0.1618, q90 0.6082.
- D10: S_10 = 0.0360 → medyan 0.1324; p_up 0.6785; q10 −0.1980, q90 1.1184.

Aynı girdiyle sıfır model D5 için 0.3519, PB varyantı 0.3166 verir: NETGL'in ortalamanın üstündeki büyüklüğü ve altındaki talep katı ana modelde S'yi, dolayısıyla medyanı aşağı çeker. (Gerçekleşen R_D5 = 0.0784, L = 3.)

### 4.6.5 Koşullu güncelleme

Model, dondurulmuş kayıt ve resmi bültenlerle "bugün tavan gitti, yarın ne olur" sorusunu yeni fit yapmadan cevaplar (§7): seri j. günde sürüyorsa P(L ≥ k | L ≥ j) = S_k / S_j ve h > j için koşullu karışım kurulur; seri t. günde kırıldıysa S kısmı düşer ve yalnız hücre atomları kalır. Canlı skorlaması j başına ayrıdır; farklı j'ler ve koşulsuz tablolar asla toplanmaz (aynı arz birden çok j'de bulunur).

### 4.6.6 Backtest ve "beklentiden çok iyi"

Backtest S_k'yı yeniden fit etmez: her fold'da kaynak tavan ledger'ından okur; yalnız hücreler her fold'da kesimden önceki gözlemlerle kurulur. Birincil hücre önceden ilan edilmişti: **`ceiling_path_v0` − `base_train_median`, D5 getiri MAE.**

| Hücre | Fark | %95 aralık | n | Hüküm | Şartname beklentisi |
|---|---|---|---|---|---|
| **D5 MAE − medyan (birincil)** | **−0.1158** | **[−0.1611, −0.0738]** | **85** | **geçiyor** | −0.090 … −0.020 |
| D1 MAE − `base_always_ceiling` | +0.0002 | [−0.0002, +0.0010] | 87 | ayırt edilemiyor | beraberlik |
| D5 MAE − `v1_5_h99` | −0.0360 | [−0.0579, −0.0176] | 85 | geçiyor | −0.020 … +0.050 |
| D5 MAE − sıfır model | −0.1033 | [−0.1462, −0.0628] | 87 | geçiyor | −0.050 … −0.005 |
| D10 MAE − `v1_5_h99` | −0.0595 | [−0.1447, +0.0157] | 85 | ayırt edilemiyor | −0.020 … +0.100 |
| D3 Brier − `base_rate` | −0.0362 | [−0.0553, −0.0163] | 86 | geçiyor | −0.040 … −0.005 |
| D10 Brier − `v1_5_h99` | −0.0311 | [−0.0695, +0.0032] | 79 | ayırt edilemiyor | +0.010 … +0.060 |

D1 beraberliği önceden yazılmıştı ve tuttu: 87 fold'un 84'ünde fark bit-eşit 0 ya da |fark| < 0.001 (şart ≥ 80/87). Dört başarısızlık tanımının (yalnız mekanik, mekanik eşleme katmıyor, eşleme hatası, kalibrasyon) hiçbiri gerçekleşmedi.

Şartname bir güvenlik kuralı içeriyordu: birincil fark < −0.120 ya da aralığın üst ucu < −0.060 ise ("beklentiden çok iyi") dondurmadan önce ilk uygulamayı görmeyen ayrı bir oturum modeli şartnameden **sıfırdan** yeniden üretmeli. Üst uç −0.0738 olduğu için kural tetiklendi (toplam 10 koşul). Fable oturumu `borsai` import etmeden yeniden üretti: 870 (fold × ufuk) hücrede maks |Δ| = 0, 36 beklenti satırında fark yok, sızıntı yok; hüküm FREEZE_OK. Modeller ancak bundan sonra donduruldu (2026-09-22). Duyarlılık (N_MIN 5/20, tek grup, havuzsuz) birincil farkı −0.112 … −0.122 aralığında tuttu.

Önemli bir dipnot: D10'daki kazanç L = 10 arzlarında yoğunlaşıyor (denetim: dört L = 10 arzı toplam farkın yaklaşık üçte birini veriyor). D10 keşif hücresidir.

PB varyantı: D5 MAE − `pb_v0` −0.0124 [−0.0391, +0.0162] (ayırt edilemiyor, beklenti tuttu); bilgi amaçlı `ceiling_path_v0`'a karşı D5 MAE +0.0728 [+0.0421, +0.1088]: talep katı burada da yaklaşık 7 puanlık değer taşıyor. PB varyantı kendi basit kurallarını (medyan, her zaman tavan) D3, D5 ve D10 MAE'de geçiyor.

İlk 7 canlı arz (CITAS…NETGL) bu modeller için RETRO'dur: modeller onların sonuçları repoya girdikten sonra donduruldu; kayıtlarında bu modellerin satırı yoktur.

Kaynak dosyalar: `docs/specs_faz4/SPEC_CEILING_PATH_V0.md`, `borsai/predict_path.py`, `borsai/ceiling_path.py`, `models/ceiling_path_v0.json`, `models/ceiling_path_v0@INF.json`, `models/pb_ceiling_path_v0.json`, `docs/MODELS.md` (Faz 4), `docs/fable_faz4_audit/AUDIT.md` (dipnot), `scores/scores.json`.

---

## 4.7 Tavan serisi v1 ailesi: kırpma, reel büyüklük, havuz

### 4.7.1 Neden yapıldı?

Faz 6'da eski kohortun (2020–2023 arzları) "açık kümesi" (71 arz) zaman-dışı terazide skorlandı ve `ceiling_hazard_v0` orada KM kuralından kötü çıktı (RPS farkı +0.069 [+0.001, +0.131], f3'lü 68 arz). Faz 7 şartnamesi (`docs/specs_faz7/SPEC_HAZARD_V1.md` §1) bu hatayı keşif olarak ikiye ayırdı:

1. **Ekstrapolasyon (hatanın yaklaşık yarısı).** f1 nominal TL'dir. Eski dönemin arzları TL olarak küçüktür: açık kümenin 68 skorlanan arzının 28'i H99 eğitim minimumunun, 40'ı p05'inin altında; z_f1 medyanı −1.97, en düşüğü −4.86. Doğrusal model eğitim desteğinin dışına taşar ve bu arzlara "çok uzun seri" der. Donmuş v0'da yalnız z_f1 ve z_f2 kırpılınca açık kümede RPS 0.269'dan 0.231'e iniyor (KM 0.200).
2. **Dönem etkisi (kalan yarı).** 2021–2022 arzlarının serileri kısadır: dönem KM'sinde S_10 0.04–0.05, H99'da 0.14. Bunu ancak dönem bilgisi taşıyan bir eğitim kapatabilir.

Bu tanıdan iç içe üç basamaklı bir **merdiven** doğdu. Her basamak bir öncekine tek bir şey ekler ve katkısı ayrı ölçülür.

### 4.7.2 Üç aday ve kural satırı

| model_id | Eğitim | Özellikler | Kırpma [p05, p95] | Rejim terimi | Parametre / olay |
|---|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | H99, f3 dolu 97 | f1, f2, f3 | **f1, f2, f3** | yok | 6 / 83 |
| `ceiling_hazard_v1_real` | H99, f3 dolu 97 | **f1r**, f2, f3 | f1r, f2, f3 | yok | 6 / 83 |
| `ceiling_hazard_v1_pooled` | **H99 97 + açık küme 68 = 165** | f1r, f2, f3 | f1r, f2, f3 | **r (cezasız δ)** | 7 / 142 |
| `ceiling_hazard_v1_pooled@INF` | aynı 165 | yok | — | r | 4 (γ + δ) / 142 |

Gün grupları, pseudo-satırlar, λ ızgarası, iç arz-bırak CV ve ret kuralları v0'dan aynen devralınır. Kırpma, v0'ın f3'e uyguladığı kuralın f1 ve f2'ye (ya da f1r'ye) genişletilmesidir; ham değer üzerinde, log'dan önce yapılır. `v1_clip@INF` ve `v1_real@INF` `ceiling_hazard_v0@INF` ile bit-eşittir, bu yüzden ayrıca kaydedilmez.

**f1r: reel arz büyüklüğü.** Mekanizma "büyük arz → satıcı bol → seri kısa"dır; ama "büyük" dönemin alım gücüne göredir. Deflatör TÜİK TÜFE genel endeksidir (2025 = 100):

```
f1r_ham = büyüklük_TL / ( TÜFE[m − 2] / 100 )        m = T'nin ayı;  birim: 2025 ortalama fiyatlarıyla TL
f1r     = ln( kırp(f1r_ham) )                         sonra z-skor
```

Neden m − 2? Ay m'nin endeksi m + 1'in 3. günü civarında yayımlanır; m − 2'nin endeksi en geç m − 1'in başında yayımlanmıştır, yani T ayın 1'i olsa bile tahmin anında bilinir (point-in-time). Dosya `data/raw/tuik/tufe_genel_2025_100.csv`'dir; kayıtta `release_date < T` bekçisi vardır. NETGL örneği: T = 2026-09-17 → endeks ayı 2026-07, endeks 132.31 (yayım 2026-08-03); f1r_ham = 2 233 000 000 / 1.3231 ≈ 1 687 703 121 TL (2025 fiyatlarıyla). USD ve XU100 deflatörleri gerekçeyle reddedildi (devalüasyon sıçramaları; borsa döngüsünü büyüklüğe karıştırma).

**Rejim terimi r** (yalnız pooled): r = 1[tahsis rejimi ≠ EQUAL_DIST_20230330]. 30.03.2023'ten beri bireysel yatırımcıya eşit dağıtım kuralı vardır; öncesindeki iki rejim (PRE_20211111, THRESH100_20211111) r = 1 alır. r, γ gibi **cezasız** bir sütundur; katsayısı δ'dır. H99 fold'larında ve canlıda r = 0'dır (T ≥ 2023-09-22). Yani δ, eski dönem satırlarının düzey farkını emer; bugünkü tahminin sabiti γ'dır.

```
logit h_d = γ_{g(d)} + δ·r + β·z
```

λ = INF iken β ≡ 0 ama (γ, δ) kapalı biçimle değil Newton ile çözülür (dört boyutlu MLE).

### 4.7.3 Dondurulmuş katsayılar

| model_id | λ | γ (g1, g2, g3) | β | δ |
|---|---|---|---|---|
| `v1_clip` | 10 | −1.8191, −2.1417, −0.9953 | f1 +0.4634, f2 −0.1795, f3 −0.5611 | — |
| `v1_real` | 10 | −1.7659, −2.1292, −1.0813 | f1r +0.2645, f2 −0.2530, f3 −0.5267 | — |
| `v1_pooled` | 10 | −2.1155, −2.2445, −1.5441 | f1r +0.2265, f2 −0.1727, f3 −0.4959 | +0.9111 |
| `v1_pooled@INF` | INF | −1.7832, −2.0499, −1.5279 | — | +0.2277 |

Kırpma sınırları: `v1_clip` f1 [521.4 mn, 4 888.0 mn TL], f2 [11.16, 35.12], f3 [1.149, 8.332]; `v1_pooled` f1r [565.8 mn, 6 237.2 mn], f2 [15.01, 37.54], f3 [1.162, 18.02]. Pooled'da δ = +0.91, eski rejim satırlarında bozulma odds'unu e^0.91 ≈ 2.5 katına çıkarır: eski dönemin kısa serileri bu terimde toplanır. Reel büyüklüğün katsayısı nominalinkinden küçüktür (+0.26'ya karşı +0.45).

NETGL (illüstrasyon; v1 bu arz için RETRO'dur): S_10 değerleri clip 0.034, real 0.097, pooled 0.153, pooled@INF 0.170; S_1 sırasıyla 0.817, 0.859, 0.879, 0.856. Kırpma NETGL'i etkilemez (girdileri sınırların içinde); reel büyüklük ve havuz eğriyi yukarı (daha uzun seri) iter.

### 4.7.4 Yakın dönem testi: "eski veri bugünü bozuyor mu?"

Proje sahibinin sorusu açıktı: eski arzları eğitime katmak bugünkü tahminleri bozmaz mı? Şartname bunu önceden yazılmış bir hücreyle cevaplar: **aday − `ceiling_hazard_v0`, RPS, ilk işlemi 2024-01-01 ve sonrası olan H99 fold'ları** (78 fold, 22 ay). v0'ın değerleri Faz 1B altın ledger'ından okunur, yeniden koşulmaz. Etiket kuralı:

```
aralığın alt ucu > 0          → "bozuyor"
aralığın üst ucu ≤ +0.010     → "tolerans içinde"
diğer                         → "belirsiz"
```

δ = 0.010, v0'ın yakın dönemde KM'ye karşı kazancının (≈ −0.056) yaklaşık beşte biridir.

| Aday | Fark (RPS) | %95 aralık | Etiket | §6.2 beklentisi |
|---|---|---|---|---|
| `v1_clip` | −0.0011 | [−0.0066, +0.0049] | **tolerans içinde** | −0.003 [−0.010, +0.005] → aralık içinde |
| `v1_real` | +0.0104 | [+0.0028, +0.0183] | **bozuyor** | −0.004 [−0.015, +0.008] → üstünde |
| `v1_pooled` | +0.0289 | [+0.0089, +0.0518] | **bozuyor** | +0.002 [−0.010, +0.015] → üstünde |
| `v1_pooled@INF` (bilgi) | +0.0547 | [+0.0287, +0.0806] | bozuyor | — |

Merdiven payları (aynı 78 fold): kırpmanın payı −0.0011 [−0.0066, +0.0049]; deflasyonun payı (real − clip) +0.0115 [+0.0045, +0.0190]; havuz + rejimin payı (pooled − real) +0.0185 [+0.0005, +0.0389]. Pooled'ın gün başına Brier'i v0'a karşı k = 1, 3, 5'te aralığı 0'ın üstünde kötü. Buna karşın üç aday da yakın dönemde `base_km_expanding`'i geçiyor (clip −0.0554, real −0.0439, pooled −0.0253; hepsinin aralığı 0'ın altında).

Cevap: H99'un yakın döneminde **kırpma zarar vermiyor; reel büyüklük ve havuz zarar veriyor**. Bu, şartnamenin beklentisinin tersidir ve dürüstçe öyle yazılmıştır. Bağımsız denetim (Fable) yeniden üretimi maks |Δ| = 4.3e-11 ile doğruladı; dört kimlik 2026-09-27'de birlikte donduruldu (etiketler dondurma kararına girmez).

### 4.7.5 Kasa testi ve seçim kuralı

Kasa, eski kohortun 2026-09-29'a kadar kapalı tutulan 64 arzıdır; tahminler sonuçlar repoya girmeden push edildi ve kasa 2026-09-29'da bir kez açıldı. Bu ayrı bir terazidir (zaman-dışı) ve ayrıntısı §6.12'nin konusudur; burada yalnız seçim kuralını besleyen hücreler var (`docs/faz7_vault/SKOR_RAPOR.md` §9.1; bağımsız denetim hükmü `VAULT_SCORE_OK`):

| Aday | k1: kasa RPS − KM (birincil) | k2: kasa RPS − v0 | k3: yakın dönem etiketi | Uygun mu |
|---|---|---|---|---|
| `v1_clip` | +0.0334 [−0.0260, +0.0886], ayırt edilemiyor → hayır | −0.0395 [−0.0640, −0.0161] → evet | tolerans içinde → evet | hayır |
| `v1_real` | −0.0110 [−0.0500, +0.0259], ayırt edilemiyor → hayır | −0.0839 [−0.1279, −0.0347] → evet | bozuyor → hayır | hayır |
| `v1_pooled` | −0.0400 [−0.0671, −0.0122], geçiyor (zaman-dışı terazide) → evet | −0.1128 [−0.1808, −0.0381] → evet | bozuyor → hayır | hayır |

Seçim kuralı kasa açılmadan önce yazılmıştı (§5.5): aday ancak k1, k2 ve k3'ün üçü de tutarsa uygulamanın tavan kartında birincil olabilir. Uygun aday yok; **`ceiling_hazard_v0` birincil kalır.** Aynı tabloda v0'ın kendisi kasada KM'den ayırt edilemiyor: +0.0728 [−0.0008, +0.1388], n = 62. Yani her v1 adayı kasada v0'dan iyi, ama yakın dönemde (bugünün rejiminde) reel ve havuz adayları v0'dan kötü. Kural tam bu çatışmayı çözmek için yazılmıştı: bugünü bozan model, eski dönemde ne kadar iyi olursa olsun öne çıkmaz.

Kaynak dosyalar: `docs/specs_faz7/SPEC_HAZARD_V1.md`, `docs/specs_faz7/KARARLAR.md`, `borsai/hazard.py`, `borsai/predict_hazard.py` (`real_size`, `_linear_v1`), `borsai/preprocess.py` (`CEILING_V1_*`), `data/raw/tuik/tufe_genel_2025_100.csv`, `models/ceiling_hazard_v1_*.json`, `docs/MODELS.md` (Faz 7), `docs/SCORES.md` §5.1, `scores/scores.json` (`near_era`), `docs/faz7_vault/SKOR_RAPOR.md`, `docs/fable_faz7_vault/AUDIT.md`.

---

## 4.8 Düşen arz modelleri: `fall_d10_v0_*`

### 4.8.1 Soru ve hedef

Proje sahibinin sorusu: "Düşen halka arzların ortak özellikleri ne?" Faz 7C şartnamesi bunu ölçülebilir bir hedefe çevirdi (`docs/specs_faz7_c/SPEC_C_V0.md` §1; KARARLAR_C C1):

```
y4 = 1[ kapanış(D10) ≤ arz fiyatı ] = 1 − Y_D10        (birincil)
y3 = 1 − Y_D5                                          (ikincil)
```

Neden D10? Olay sayısı en çok burada (H99 29/99, açık küme 13/71; kasada beklenen ≈ 12). D1'de arz altı kapanış kasada ≈ 2 olay verirdi; hiçbir hüküm çıkmazdı. "D1'de tavan yok" (y1) için model tanımlanmadı, çünkü `ceiling_hazard_v0`'ın 1 − S_1'i bunu iki dönemde de iyi ayırıyor (AUC 0.81 / 0.80). Model "P(kapanış > arz)" verir; "düşme olasılığı" = 1 − p_up olarak gösterilir.

### 4.8.2 Keşif: ne bulundu, ne kadar güvenilir?

Özellikler H99 ve açık kümenin 170 arzının sonuçları görülerek, **2 054 varyant** denenerek seçildi (`docs/specs_faz7_c/KESIF.md`; her varyant `ekler/denenenler.csv`'de ve `experiments/log.jsonl`'da `kind: exploration` satırı olarak kayıtlı). Bu yüzden H99 sonuçları burada hem tasarıma maruz hem çoklu denemeye açıktır. Keşfin üç bulgusu (hepsi keşif, hüküm değil):

- **Ek satış kullanıldı** (`additional_sale_shares` > 0): ek satışlı 19 arzın 12'si D10'da arz fiyatının altında ya da eşitinde (0.63); ek satışsız 151 arzın 30'u (0.20). İki dönemde de aynı yön (H99 4/6, açık 8/13).
- **Düşük talep katı:** f3 < 2 olan 42 arzın 19'u düştü (0.45); f3 ≥ 2 olanların 21/123'ü (0.17). Yeni dönemde güçlü, eski dönemde zayıf.
- **Büyük reel arz:** f1r > 2 milyar (2025 TL) olan 73 arzın 28'i düştü (0.38); küçüklerin 14/97'si.

Seçim süzgeci (keşifte uygulanan): özellik iki dönemde aynı yönde, 170 arzda tek tanımla mevcut, arz-bırak ve her iki aktarım hücresinde (yalnız H99'da fit → açık kümede skor; tersi) negatif ortalama, en çok 3 özellik. Yalnız {f1r, ln f3, ek satış} ve alt kümeleri geçti. Rejim terimi y4'te bilgi eklemedi ve açık → H99 aktarımını bozdu; bu yüzden (C) modellerinde rejim terimi yoktur.

### 4.8.3 Üç aday ve kural satırı

Ortak: her ufuk (D5, D10) için ayrı **L2-lojistik**, V1.6 C ızgarası {ZERO, 0.0001, …, 100}, iç LOOCV Brier, aday başına yakınsamama; getiri kafası yok.

| model_id | Eğitim | Özellikler | D10 olay / parametre |
|---|---|---|---|
| `fall_d10_v0_h99` | H99, f3 ve ek satış dolu 94 | f1r, ln f3, ek satış | 26 / 4 = 6.5 |
| `fall_d10_v0_pooled` | H99 + açık, 161 | f1r, ln f3, ek satış | 39 / 4 = 9.8 |
| `fall_d10_v0_addsale` | H99 + açık, ek satış dolu 165 | ek satış | 40 / 2 = 20 |
| `fall_d10_v0_pooled@ZERO` (kural) | 161 | yok; p_up = eğitim oranı | — |

`h99`'un bütçesi projenin 10 olay/parametre çizgisinin altındadır; bu bilerek kabul edildi (KARARLAR_C C2), çünkü yakın dönem testinin karşılaştırıcısıdır. Ön işleme (`FALL_V0_RECIPE`): f1r ve f3 ham değerde eğitim [p05, p95]'ine kırpılır, sonra **ikisi de** ln'lenir (V1.5'ten farkı: f3'ün log'u; keşifte daha iyi aktarıldı), sonra z-skor. Ek satış bayrağı yalnız z-skorlanır. f1r tanımı `ceiling_hazard_v1_real` ile tektir.

Ret kuralları: f3 boş (`F3_MISSING`; addsale hariç), TÜFE ayı yok ya da yayımlanmamış (`TUFE_*`), **ek satış alanı boş → RET** (`ADDITIONAL_SALE_MISSING`; "yok" ile "bulunamadı" karışmasın diye 0 varsayılmaz; KARARLAR_C C4).

Dondurulmuş katsayılar (z ölçeğinde, p_up kafası; **pozitif katsayı düşme olasılığını azaltır**):

| model_id | Ufuk | C | Sabit | f1r | ln f3 | ek satış |
|---|---|---|---|---|---|---|
| `h99` | D10 | 1 | +1.4371 | −0.8566 | +1.1093 | −0.4207 |
| `h99` | D5 | 1 | +2.4245 | −1.0007 | +1.5284 | −0.4451 |
| `pooled` | D10 | 1 | +1.4939 | −0.5237 | +0.8520 | −0.8028 |
| `pooled` | D5 | 1 | +2.0526 | −0.5850 | +0.9604 | −0.8166 |
| `addsale` | D10 | 1 | +1.2082 | — | — | −0.6144 |
| `pooled@ZERO` | D10 / D5 | ZERO | p_up = 0.7578 / 0.8199 | — | — | — |

İşaretler keşifle tutarlıdır: büyük reel arz ve ek satış p_up'ı düşürür (düşme olasılığını artırır), yüksek talep katı p_up'ı yükseltir. Havuzda ek satışın ağırlığı artıyor (−0.80'e karşı −0.42): ek satışlı arzların çoğu açık kümededir.

NETGL (illüstrasyon; (C) bu arz için RETRO): P(D10 ≤ arz) = 1 − p_up: `h99` 0.163, `pooled` 0.171, `addsale` 0.193, `pooled@ZERO` 0.242. NETGL'in ek satışı yok, talep katı 2.84; modeller onu ortalamanın altında riskli görüyor. Gerçekleşen R_D10 = −0.3617 oldu (düştü). Tek arz değerlendirme değildir; olasılık modeli 0.17 dediği olayın altı arzdan birinde gerçekleşmesini bekler.

### 4.8.4 Sonuçlar

Yakın dönem birincil hücresi (`pooled − h99`, D10 Brier, ilk işlem ≥ 2024-01-01; tolerans 0.008): **−0.0058 [−0.0340, +0.0219], n = 75 → "belirsiz".** Eski arzları eğitime katmanın bugünü bozup bozmadığı bu veride söylenemiyor; beklenen etiket de "belirsiz ya da tolerans içinde" idi.

İlan edilmiş ikinciller (aynı yakın dönem fold'ları, D10 Brier):

| Aday | − `base_rate` | − `v1_5_h99` |
|---|---|---|
| `h99` | −0.0434 [−0.0773, −0.0048] | −0.0055 [−0.0228, +0.0154] |
| `pooled` | −0.0492 [−0.0670, −0.0296] | −0.0113 [−0.0465, +0.0281] |
| `addsale` | −0.0065 [−0.0301, +0.0161] | +0.0305 [−0.0131, +0.0808] |

Okuma: f1r + ln f3 taşıyan iki aday taban oranını yakın dönemde geçiyor; yalnız ek satış bayrağı geçemiyor (H99'da yalnız 6 ek satışlı arz var). Hiçbir aday V1.5'in p_up kafasından ayırt edilemiyor. Merdiven: özelliklerin payı (pooled − pooled@ZERO) −0.0449 [−0.0629, −0.0262].

Kasa (zaman-dışı terazi; `docs/faz7_vault/SKOR_RAPOR.md` §9.2): D10 Brier − `base_rate`: `h99` −0.0398 [−0.0878, +0.0043] ayırt edilemiyor; `pooled` −0.0452 [−0.0923, −0.0020] **geçiyor (zaman-dışı terazide)**; `addsale` −0.0058 [−0.0541, +0.0358] ayırt edilemiyor. Ama seçim kuralının k2 koşulu (kasada V1.5'e karşı aralığın üst ucu < 0) üç adayda da tutmadı (pooled: −0.0304 [−0.1003, +0.0320]). **Uygun aday yok:** uygulamanın "Düşüş (D10)" kartı hiçbir (C) modelini öne çıkarmaz ve "kasada geçen aday yok" yazar. Denetimin bir bilgi notu: pooled'ın kasa kazancı 2023-03 öncesi rejimlerden geliyor; eşit dağıtım rejimindeki 12 kasa üyesinde işaret pozitif (n küçük, hüküm yok).

Kaynak dosyalar: `docs/specs_faz7_c/SPEC_C_V0.md`, `docs/specs_faz7_c/KARARLAR_C.md`, `docs/specs_faz7_c/KESIF.md`, `borsai/predict_fall.py`, `borsai/fit.py` (`fit_fall_horizon`), `borsai/preprocess.py` (`FALL_V0_*`), `models/fall_d10_v0_*.json`, `docs/MODELS.md` (Faz 7C), `scores/scores.json` (`faz7c_near_era`, `near_era`), `docs/SCORES.md` §5, `docs/faz7_vault/SKOR_RAPOR.md`, `docs/fable_faz7_vault/AUDIT.md`.

---

## 4.9 Sonuç tablosu: kim geçiyor, kim ayırt edilemiyor

Aşağıdaki tablo her modelin **önceden ilan edilmiş** birincil hücresini toplar. Sol blok geçmiş veri testidir (H99 walk-forward, tasarıma maruz; `scores/scores.json` ve `docs/MODELS.md`). Sağdaki sütun yalnız bilgi içindir: aynı modelin kasadaki (zaman-dışı terazi) birincil hücresi. **İki terazi toplanmaz ve karşılaştırılmaz**; yan yana durmaları yalnız okumayı kolaylaştırır. Fark = model − karşılaştırılan; negatif = model iyi.

| Model | Birincil hücre (backtest) | Fark [%95 aralık], n | Hüküm | Önceden yazılmış beklenti | Kasa birincili (bilgi) |
|---|---|---|---|---|---|
| `v1_5_h99` | D5 MAE − `base_train_median` | −0.0839 [−0.1343, −0.0321], 87 | geçiyor | — (ön kayıt; beklenti tablosu yok) | −0.0119 [−0.0706, +0.0412], ayırt edilemiyor |
| `v1_6_h99` | D10 MAE − `v1_5_h99` | +0.0008 [−0.0003, +0.0028], 87 | ayırt edilemiyor | "V1.5'ten ayırt edilemiyor, en olası" tuttu; kenara yapışma tutmadı | +0.0004 [+0.0001, +0.0007], geçemiyor |
| `v1_5_market20_v0` | D5 MAE − `v1_5_h99` | −0.0008 [−0.0178, +0.0137], 87 | ayırt edilemiyor | kısmen (D10 \|ΔBrier\| 0.0054 > 0.005) | −0.0061 [−0.0186, +0.0056], ayırt edilemiyor |
| `pb_v0` | D5 MAE − `base_train_median` | −0.0355 [−0.0775, +0.0102], 87 | ayırt edilemiyor | kısmen | +0.0303 [−0.0263, +0.0883], ayırt edilemiyor |
| `ceiling_hazard_v0` | RPS − `base_km_expanding` / − `base_km_last10` | −0.0569 [−0.0833, −0.0286] / −0.0496 [−0.0751, −0.0219], 87 | geçiyor / geçiyor | tutmadı (beklenenden iyi) | +0.0728 [−0.0008, +0.1388] (KM genişleyen), ayırt edilemiyor |
| `pb_ceiling_v0` | RPS − iki KM kuralı | −0.0324 [−0.0544, −0.0114] / −0.0335 [−0.0612, −0.0019], 87 | geçiyor / geçiyor | kısmen (KM'den ayırt edilemez denmişti) | +0.0653 [−0.0042, +0.1329], ayırt edilemiyor |
| `ceiling_path_v0` | D5 MAE − `base_train_median` | −0.1158 [−0.1611, −0.0738], 85 | geçiyor | "beklentiden çok iyi" tetiklendi → bağımsız yeniden üretim → FREEZE_OK | +0.0019 [−0.0704, +0.0684], ayırt edilemiyor |
| `pb_ceiling_path_v0` | `scores.json`'da birincil ilan edilmemiş; D5 MAE − medyan keşif | −0.0479 [−0.0838, −0.0113], 87 | (keşif) | − `pb_v0` hücresi tuttu | +0.0346 [−0.0366, +0.1018], ayırt edilemiyor |
| `ceiling_hazard_v1_clip` | yakın dönem RPS − v0 (etiket) | −0.0011 [−0.0066, +0.0049], 78 | tolerans içinde | tuttu | +0.0334 [−0.0260, +0.0886], ayırt edilemiyor |
| `ceiling_hazard_v1_real` | yakın dönem RPS − v0 (etiket) | +0.0104 [+0.0028, +0.0183], 78 | bozuyor | tutmadı (üstünde) | −0.0110 [−0.0500, +0.0259], ayırt edilemiyor |
| `ceiling_hazard_v1_pooled` | yakın dönem RPS − v0 (etiket) | +0.0289 [+0.0089, +0.0518], 78 | bozuyor | tutmadı (üstünde) | −0.0400 [−0.0671, −0.0122], geçiyor (zaman-dışı) |
| `fall_d10_v0_h99` | yakın dönem D10 Brier − `base_rate` | −0.0434 [−0.0773, −0.0048], 75 | aralık 0'ın altında | aralık içinde | −0.0398 [−0.0878, +0.0043], ayırt edilemiyor |
| `fall_d10_v0_pooled` | yakın dönem D10 Brier − `fall_d10_v0_h99` (etiket) | −0.0058 [−0.0340, +0.0219], 75 | belirsiz | aralık içinde | −0.0452 [−0.0923, −0.0020], geçiyor (zaman-dışı) |
| `fall_d10_v0_addsale` | yakın dönem D10 Brier − `base_rate` | −0.0065 [−0.0301, +0.0161], 76 | aralık 0'ı içeriyor | aralık içinde | −0.0058 [−0.0541, +0.0358], ayırt edilemiyor |

Notlar: v1 ve (C) satırlarında "birincil" hücre şartnamelerde kasa hücresidir; geçmiş veri terazisinde onların önceden yazılmış hücresi yakın dönem etiketidir. `scores.json` (C) adaylarının yakın dönem satırlarına da aynı etiket kuralını uygular (`fall_d10_v0_h99` − `base_rate` için "tolerans içinde", `addsale` için "belirsiz", `@ZERO` için "tolerans içinde"); bu etiket orada §5.5 k3 koşulunun girdisidir, bir hüküm değildir. Kural satırlarının (`base_*`, KM, `@INF`, `@ZERO`) birincil hücresi yoktur.

Toplu okuma:

- Geçmiş veri testinde **en güçlü ve en tutarlı sonuç tavan ailesindedir**: `ceiling_hazard_v0` ve `ceiling_path_v0` birincil hücrelerinde aralığı 0'dan uzak biçimde geçiyor. V1.5'in getiri kafası D5'te geçiyor; olasılık kafası hiçbir ufukta taban oranından ayırt edilemiyor.
- **Tek değişkenli genişletmeler bilgi eklemiyor:** V1.6 (ızgara) ve market20 (piyasa getirisi) V1.5'ten ayırt edilemiyor.
- **Talep katı değerlidir:** PB varyantları her ailede f3'lü kardeşlerinden kötüdür (tavan RPS'inde +0.034, tavan yolunda D5 MAE'de +0.073, getiride D5 MAE'de +0.053).
- **Kasa başka bir hikâye anlatıyor:** H99'da parlayan modellerin hiçbiri kasada birincil hücresini geçmiyor; kasada geçen iki model (`v1_pooled`, `fall_pooled`) ise eski dönemle eğitilmiş adaylardır. Okumam: bu, dönemler arası kaymanın gerçek olduğunu ve H99 backtest'inin iyimser olabileceğini gösteren en önemli işarettir.

Kaynak dosyalar: `scores/scores.json` (`models[].primary_cell`, `backtest.cells`, `near_era`), `docs/SCORES.md` §5, `docs/MODELS.md`, `docs/faz7_vault/SKOR_RAPOR.md` §3, §9.

---

## 4.10 Üretimde ne var: öne çıkan modeller ve nedenleri

"Üretim" bu projede iki şey demektir: (1) dondurulmuş kayıt, (2) masaüstü uygulamasında kullanıcıya gösterilen ve öne çıkarılan çıktı.

**Kayıt: hepsi.** Kural 1 gereği her listeleme öncesi kayıt, o an `models/INDEX.json`'da bulunan bütün modellerin çıktısını içerir. NETGL kaydı (2026-09-22) o günkü dizinin 16 modelini taşır; Faz 7 ve 7C'den sonra dizin 27 modeldir ve uygulama 27 modeli gömülü taşır (`GITLOG.txt`: BORSAI_APP_P34_C3, "embed 27"). Öne çıkarma bir modeli kayıttan çıkarmaz; yalnız ekranda ilk satıra ve renkli işarete koyar.

**Uygulamada öne çıkanlar** (kodda sabit kurallar; skorlar dosyadan okunur, uygulama skor hesaplamaz):

| Kart / çıktı | Öne çıkan | Neden (kod ve belge) |
|---|---|---|
| Tavan serisi (S_k) | `ceiling_hazard_v0` | Faz 7 seçim kuralı §5.5: kasa açık, hiçbir v1 adayı k1–k3'ü birlikte sağlamıyor → neden kodu `RULE_5_5_NONE_ELIGIBLE_V0` (`app/src-tauri/src/commands/scores.rs: featured_ceiling`). Kasa kapalıyken de varsayılan v0'dı (`VAULT_CLOSED_V0_DEFAULT`). |
| Sade görünümün başlık hücreleri | `ceiling_hazard_v0` S ve `v1_5_h99` D5 getirisi | Bir çıktı yalnız modelin birincil hücresiyse ve bütün birincil satırlarının hükmü "geçiyor" ise öne çıkar (`sade.rs: gate_entry`). v0'ın iki KM hücresi ve V1.5'in D5 MAE hücresi bu şartı sağlıyor. V1.5'in öbür ufukları ve p_up'ı birincil olmadığı için "yaklaşık" işaretiyle gösterilir. |
| Düşüş (D10) kartı | yok | (C) seçim kuralı §5.5: `fall_d10_v0_pooled` kasada k1'i sağlıyor ama hiçbir aday k2'yi (kasada V1.5'e karşı aralığın üst ucu < 0) sağlamıyor → `RULE_5_5_NONE_ELIGIBLE`; kart "kasada geçen aday yok" yazar ve V1.5'in p_up sütunu olduğu gibi kalır. |
| f3 henüz yokken | PB modelleri | Talep toplama sonucu açıklanmadan f3 isteyen modeller RET eder; PB sütunu o anda dolu olan tek model sütunudur (SPEC_PB_V0 Özet 8). |

**Canlı sicil.** 2026-09-30 itibarıyla canlı skorlanan arz sayısı en çok 7'dir (CITAS, TKNKA, VEYAS, KPEKS, INTET, BKRGY, NETGL) ve bunların çoğu LATE_RECORD sınıfındadır (kayıt D1'den sonra yazılmış); n < 10 olduğu için yalnız satır tablosu vardır, metrik ve hüküm yoktur (`docs/SCORES.md`). Tavan yolu, v1 ve (C) modelleri bu yedi arz için RETRO'dur; canlı n'leri dondurmadan sonra listelenen arzlarla başlar. Yani bugün **hiçbir listeleme öncesi model prospektif olarak kanıtlanmış değildir**; öne çıkarma kararları geçmiş veri testine, yakın dönem etiketine ve tek seferlik kasaya dayanır.

Kaynak dosyalar: `CLAUDE.md`, `models/INDEX.json`, `app/src-tauri/src/commands/scores.rs`, `app/src-tauri/src/commands/sade.rs`, `app/src-tauri/tests/stage2.rs` (gerçek dosyalarla öne çıkarma testleri), `docs/specs_faz7/SPEC_HAZARD_V1.md` §5.5, `docs/specs_faz7_c/SPEC_C_V0.md` §5.5, `docs/faz7_vault/SKOR_RAPOR.md` §9, `docs/SCORES.md` §1–§3, `scores/scores.json` (`live`), `GITLOG.txt`.

---

## 4.11 Sınırlar ve dürüstlük notları

- **Tasarıma maruziyet.** Gün grupları, tavan yolu hücreleri, v1 merdiveni ve (C) özellikleri H99'un (ve (C) için açık kümenin) sonuçları görülerek seçildi. H99 backtest'i bu modeller için bir ön elemedir, kanıt değildir.
- **Çokluk.** Kart sayaçları bunu saklamaz: aynı veri sürümünde denenen varyant sayısı `training_table.csv` (ilk veri sürümü) ile eğitilen modellerde 23, `training_table_v2.csv` ile eğitilenlerde (`v1_pooled`, `fall_pooled`, `addsale`, `@ZERO`'lar) 2 059'dur; bunun 2 054'ü (C) keşfinin `kind: exploration` satırlarıdır (`scores/scores.json` → `card`). Çok deneme yapılan yerde şans eseri "geçiyor" çıkma olasılığı artar; birincil hücre ilanı buna karşı tek savunmadır.
- **Küçük n.** H99 99 arzdır; olasılık kafalarında azınlık olayı D1'de 10'dur. Ay blokları 22–24 tanedir. Aralıklar geniştir ve "ayırt edilemiyor" çoğu zaman en dürüst cevaptır.
- **Beklentiden iyi sonuçlar şüpheyle karşılanır.** `ceiling_hazard_v0` beklentiden iyi çıktı; `ceiling_path_v0`'da "beklentiden çok iyi" kuralı tetiklendi ve dondurma, ilk uygulamayı görmeyen bir oturumun sıfırdan bit-eşit yeniden üretimine bağlandı. v1 ve (C) aileleri de dondurmadan önce aynı yeniden üretimden geçti.
- **Bilinen zayıflıklar yazılıdır:** β_f2'nin işareti beklenenin tersidir; tavan modeli kalibrasyonda seriyi hafifçe uzun görüyor (ort. S_5 0.434, gözlenen 0.379); tavan yolunun D10 kazancı az sayıda L = 10 arzında yoğunlaşıyor; v0'ın f1'i nominal TL'dir ve eski dönemde ekstrapolasyon yapar.
- **Terazi ayrılığı.** Geçmiş veri testi, canlı sicil ve zaman-dışı test (kasa) asla toplanmaz. Bu bölümde kasa sayıları yalnız öne çıkarma kurallarını açıklamak için, ayrı sütunda verildi.
- **Belirsiz kalanlar.** V1.5'in kendi ön kaydında H99 için sayısal bir beklenti tablosu bulamadım; bu yüzden 4.9'da "—" yazdım (belirsiz). `pb_ceiling_path_v0`'ın geçmiş veri terazisinde neden birincil hücre taşımadığını `scores.json`'dan okudum (`primary_cell: null`); gerekçesini bir belgede görmedim (belirsiz).

Kaynak dosyalar: `docs/MODELS.md`, `docs/SCORES.md`, `scores/scores.json`, `docs/specs/SPEC_CEILING_V0.md` §11, `docs/specs_faz4/SPEC_CEILING_PATH_V0.md` §6, §10, `docs/specs_faz7/SPEC_HAZARD_V1.md` §6, §10, `docs/specs_faz7_c/SPEC_C_V0.md` §6, §10, `docs/fable_faz4_audit/AUDIT.md`.

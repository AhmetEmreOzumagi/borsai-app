# 5. Listeleme sonrası modeller: D1 akşamı ve kırılma akşamı

Önceki bölümlerdeki modellerin hepsi (Bölüm 4) **listeleme öncesi** çalışır. Arz fiyatı, arz büyüklüğü, talep katı gibi izahname ve KAP bilgisiyle ilk işlem gününden önce bir tahmin üretirler. Bu bölüm iki farklı anı anlatır. İkisinde de pay artık işlem görmektedir ve Borsa İstanbul'un resmi günlük bülteni yeni bilgi taşır:

| | D1 akşamı | Kırılma akşamı |
|---|---|---|
| Ne oldu? | İlk işlem günü (D1) tavanda kapandı | Tavan serisi bir gün bozuldu |
| Soru | "Seri yarın ve sonra nasıl sürer?" | "Yarın (ve öbür gün) taban mı?" |
| Model | `post_d1_hazard_v0` | `break_floor_v0` (+ kural satırı `break_floor_v0@ZERO`) |
| Aşama adı | `POST_D1` | `POST_BREAK` |
| Model dizini | `models/INDEX_POST_D1.json` | `models/INDEX_POST_BREAK.json` |
| Kayıt dizini | `registry/post_d1/<T>/` (bugün yok) | `registry/post_break/<T>/` (7 makine kaydı) |
| Kaydı kim yazar? | İnsan; D2 sabahı 09:40'tan önce push edilir | Makine, skorlama anında; insan değer girmez |
| Skor dosyası | `scores/scores_post_d1.json` | `scores/scores_break.json` |
| Bugünkü canlı n | 0 (7 arzın hepsi RETRO) | 0 (7 arzın hepsi RETRO) |

Bölümün sırası şöyle: önce iki modelin ortak sözlüğü (5.1), sonra D1 sonrası model (5.2), kırılma modeli (5.3), D10 için yapısal sıfır kuralı (5.4), makine kayıtları (5.5), bağımsız denetimler (5.6) ve özet (5.7). Bütün sayılar repodaki dosyalardan okundu ya da bu dosyalardan yeniden hesaplandı. Kendi hesabım olan yerler "yeniden hesap" ya da "türetme" diye işaretlidir.

## 5.1 Ortak zemin: kavramlar

### 5.1.1 Seans, seri ve kırılma günü

- **D_h:** payın işlem gördüğü h'inci resmi seans. D1 ilk işlem günüdür. Tam gün durdurulan bir seans sayılmaz; o zaman D_h bir gün kayar.
- **Tavan kapanış:** kapanış fiyatı o günün **üst limitine** tam eşitse gün "tavan"dır. **Taban kapanış** da kapanışın **alt limite** eşit olmasıdır.
- **L (seri uzunluğu):** D1'den başlayarak kesintisiz kaç gün tavan kapanış olduğu. L = 0, D1'in tavan olmadığı demektir. L = 10, ilk on günün hepsinin tavan olduğu demektir.
- **b (kırılma günü):** b = L + 1. Tavan olmayan ilk işlem görmüş kapanışın seans numarasıdır. NETGL'de L = 3, b = 4'tür: D1–D3 tavan, D4'te seri bozuldu.
- **Hazard h_d:** "seri d − 1 gün sürdüyse d. günde bozulma olasılığı". Kesikli zamanlı sağ kalım analizinin temel nesnesidir.
- **Sağ kalım S_k:** P(L ≥ k), yani serinin en az k gün sürme olasılığı.

```
S_k = Π_{d=1..k} (1 − h_d)
P(L = l) = S_l − S_{l+1}            (S_0 = 1, S_11 = 0)
```

Kaynak dosyalar: `docs/specs_faz8/SPEC_BREAK_V0.md` §1.2; `docs/specs_faz5/SPEC_POST_D1_V0.md` §1.2, §3.1; `docs/specs/SPEC_SCORING.md` §2–§3 (şartnamelerin atıfladığı tanımlar).

### 5.1.2 Bültenler ve "ham metin Decimal eşitliği"

Borsa İstanbul her gün iki resmi dosya yayımlar:

- **THB (fiyat bülteni):** açılış, en yüksek, en düşük, kapanış, `TOPLAM ISLEM ADEDI` (işlem gören pay adedi), sözleşme sayısı, AOF (ağırlıklı ortalama fiyat) gibi alanlar. Gün akşamı yayımlanır; ölçülen yayım saati 18:25–18:40'tır.
- **THM (limit bülteni):** o günün referans fiyatı, üst ve alt limitleri. Aynı günün sabahı, seans başlamadan yayımlanır (ölçülen ~08:00).

Dosyalar `data/raw/bist/thb/…` ve `data/raw/bist/thm/…` altında `th?YYYYMMDD1.zip` kalıbıyla adlandırılmış zip'lerdir (§3.2.1). Her birinin sha256'sı `data/raw/bist/MANIFEST.csv`'de pinlidir. "Pinli" demek şudur: dosyanın içeriği değişirse hash tutmaz ve kod durur.

Tavan, taban ve kilit etiketleri **ham metnin `Decimal` eşitliğiyle** hesaplanır. "10.12" ile "10.120" eşittir. "10.12" ile "10.1200000000000000001" eşit değildir. Float (ikili kayan nokta) kullanılmaz, çünkü float bu iki sayıyı aynı değere yuvarlar. Bu ayrım Faz 5 denetiminde bir teste dönüştü (5.6).

**Fiyat limitleri.** Günlük marj ±%10'dur. Limitler fiyat adımına "içe" yuvarlanır: üst limit aşağı, alt limit yukarı. Adım fiyat seviyesine göre değişir (20 TL altı 0.01, 20–50 TL 0.02, 50–100 TL 0.05, 100–250 TL 0.10, …). Kodda alt limit işlevi şudur:

```
Lo(x) = ⌈ x·0.9 / adım(x·0.9) ⌉ · adım(x·0.9)        (borsai/predict_path.py: lower_limit)
```

Ertesi günün referans fiyatı bugünün kapanışıdır. Bu yüzden ertesi günün alt limiti Lo(bugünkü kapanış)'tır. H99'da referans kuralı 67/67, alt limit zinciri 85/85 tutar.

Kaynak dosyalar: `docs/specs_faz5/SPEC_POST_D1_V0.md` §2, §7.2; `data/raw/bist/MANIFEST.csv`; `borsai/predict_path.py` (`tick`, `lower_limit`); `docs/specs_faz8/ekler/profil_kirilma.txt` §7.

### 5.1.3 İstatistik araç kutusu

- **Logit ve sigmoid.** logit(p) = ln(p / (1 − p)) olasılığı (−∞, +∞) aralığına açar. Tersi sigmoid(η) = 1 / (1 + e^(−η)). Lojistik modelde η "doğrusal öngörücü"dür: η = sabit + Σ katsayı × özellik.
- **z-skor.** z = (x − μ) / σ. μ ve σ eğitim kümesinden hesaplanır (σ popülasyon standart sapması, ddof = 0). Özelliklerin ölçeği eşitlenir; böylece L2 cezası her katsayıya aynı ölçekte davranır. σ = 0 olursa (eğitimde herkes aynı değeri taşıyorsa) özellik düşer ve katsayısı 0 yazılır.
- **Kırpma (winsor).** Eğitim kümesinin 5. ve 95. yüzdelikleri (p05, p95) hesaplanır. Yüzdelik tanımı "Type-7" doğrusal kantildir. Dışarıda kalan değer sınıra çekilir. Böylece uç değerler modeli sürüklemez. Canlıda kırpılan değer `clipped: true` ve bir uyarıyla işaretlenir.
- **L2 cezası.** Kayıp fonksiyonuna (λ/2)·‖katsayılar‖² eklenir. Katsayılar sıfıra doğru "büzülür". λ büyüdükçe büzülme artar; λ = ∞'da katsayılar tam sıfır olur. scikit-learn'ün `C` parametresi bunun tersidir: C büyüdükçe ceza azalır. Projede `C = ZERO` "yalnız sabit terim" demektir.
- **İç arz-bırak çapraz doğrulama (iç LOOCV).** Ceza gücünü seçmek için eğitim kümesindeki her arz sırayla dışarıda bırakılır. Model kalan arzlarla, ön işleme dahil, yeniden kurulur ve dışarıdaki arz tahmin edilir. En iyi ortalama skoru veren ceza seçilir.
- **Brier skoru.** (p − y)². p tahmin edilen olasılık, y gerçekleşen 0/1. Küçük olan iyidir. Bu bölümde Brier **kırpmasızdır**: p = 0 ya da 1 de olduğu gibi skorlanır.
- **RPS (sıralı olasılık skoru).** Bir dağılımın bütününü tek sayıyla skorlar. D1 sonrası modelde koşullu biçimi kullanılır:

```
RPS_1 = (1/9) · Σ_{k=2..10} ( S_cond[k] − 1[L ≥ k] )²
```

- **Eşleşik fark.** Aynı arzlarda "model skoru − karşılaştırılanın skoru". Negatif fark model lehinedir.
- **Blok bootstrap aralığı.** Arzlar ilk işlem aylarına göre bloklanır. Bloklar 4000 kez yerine koyarak çekilir (backtest'te `random.Random(20260921)`, canlıda aynı tohumla numpy üreteci). Farkın %2.5 ve %97.5 yüzdelikleri %95 aralığı verir. Aynı aydaki arzlar birbirine bağımlı olabileceği için tek tek değil, ay ay örneklenir.
- **Walk-forward (ileri yürüyen) backtest.** Her test arzı için, o arzın kesim anından önce bilinen veriyle model sıfırdan kurulur. Her test arzı bir **fold**'dur. Sonuç **ledger** denen tabloya satır satır yazılır.

Kaynak dosyalar: `borsai/fit.py` (`V1_6_C_GRID`, `_fit_logit`); `borsai/predict_path.py` (`conditional_rps`, `conditional_brier`); `docs/SPEC_DEVIATIONS.md` C7 (bootstrap), H11 (kırpma ve z aritmetiği); `docs/MODELS.md` Faz 5 ve Faz 8 değerlendirme kuralları.

### 5.1.4 Teraziler, sınıflar ve zaman kanıtı

Projede doğruluk üç ayrı terazide ölçülür ve teraziler asla toplanmaz: backtest (geçmiş veriyle), canlı (prospektif) ve zaman-dışı eski kohort. Bu bölümün iki modeli canlı terazide ayrıca kendi **ölçeklerini** kullanır: `live_post_d1` ve `live_break`. Backtest tarafında `backtest_conditional` ve `backtest_break` vardır. Kod, bu ölçekleri birleştirmeye çalışan her çağrıda `ScaleMixError` verir.

- **Prospektif:** model, arzın sonucu repoya girmeden önce dondurulmuş ve push edilmiştir.
- **RETRO:** model sonuçtan sonra dondurulmuştur. Satır yalnız "bilgi" olarak görünür ve hiçbir n'e girmez.
- **LIVE / LATE_RECORD:** prospektif bir modelin kaydı, zaman sınırından önce ya da sonra push kanıtı almıştır.
- **MACHINE_SEQUENCED:** kaydı insan değil makine, yalnız pinli resmi dosyalardan üretmiştir (5.5).
- **Tasarıma maruz:** hipotez ya da özellik, aynı veriye (H99) bakılarak seçilmiştir. O veride yapılan backtest kanıt değildir, yalnız **ön eleme**dir.

**Zaman kanıtı push'tur, yerel saat değil.** `python -m borsai.push_proof <sha>` GitHub'a bir commit durumu (commit status) yazar. GitHub sunucusunun verdiği `created_at` alanı kanıttır. Kanıt o commit'i ve bütün atalarını kapsar. Kanıt dosyaları `registry/push_proofs/<sha>.json` altında durur.

**Git atalığı.** "A, B'nin atasıdır" demek, B'nin geçmişinde A'nın bulunması demektir (`git merge-base --is-ancestor A B`). Kural basittir: model commit'i, arzın sonucunu repoya sokan commit'in atasıysa model sonuçtan önce vardı. Tarihler karşılaştırılmaz; commit grafiği (DAG) karşılaştırılır.

Kaynak dosyalar: `CLAUDE.md` (kural 1, 3, 5, 6); `borsai/push_proof.py` (`is_ancestor`); `registry/push_proofs/`; `docs/specs_faz8/SPEC_BREAK_V0.md` §12 (maruziyet).

## 5.2 D1 sonrası model: `post_d1_hazard_v0`

### 5.2.1 Soru ve kapsam

D1 tavanda kapandı. Yatırımcının sorusu "yarın da tavan mı, seri kaç gün sürer?"dir. Ürün bu soruya bu model gelmeden önce de bir cevap veriyordu: listeleme öncesi dondurulmuş `ceiling_hazard_v0` kaydının eğrisi koşullandırılıyordu.

```
P(L ≥ k | L ≥ 1) = S_k / S_1
```

Bu cevap D1'in **nasıl** geçtiğini hiç kullanmaz. Gün boyu tavanda kilitli kalan bir arz ile gün içinde düşüp kapanışta tavana dönen bir arz aynı eğriyi alır. `post_d1_hazard_v0` bu boşluğu D1'in resmi bülteninden iki özellikle doldurur.

Kapsam bilinçli olarak dardır:

- Model yalnız **D1'i tavanda kapatan** arzlarda tanımlıdır (`ceiling_close_D1 = 1`). H99'da bu 81 arzdır.
- D1 tavan değilse sonuç `NOT_APPLICABLE` (kod `D1_NOT_CEILING`) olur. Bu bir ret değildir, kapsam dışıdır. O arzın akşamı kırılma modelinin akşamıdır (b = 1; 5.3).
- Talep katı (f3) olmayan arzda ana model reddeder; bu model de reddeder (`F3_MISSING`).
- D1 hedefi bu modelde hiç skorlanmaz. Yalnız D2..D10 skorlanır.

Kaynak dosyalar: `docs/specs_faz5/SPEC_POST_D1_V0.md` özet ve §1.

### 5.2.2 Özellikler: `d1_lock` ve `d1_turnover`

İki özellik de D_1 tarihli THB ve THM'nin `<TICKER>.E` satırından gelir. Değerler ham metinden `Decimal`'e çevrilir.

| Ad | Formül | Bülten alanı | Ön işleme |
|---|---|---|---|
| `d1_lock` | 1[`EN DUSUK FIYAT` == `UST LIMIT FIYATI`] | THB `EN DUSUK FIYAT`, THM `UST LIMIT FIYATI` | z-skor |
| `d1_turnover` | ln(`TOPLAM ISLEM ADEDI` / `shares_offered`) | THB `TOPLAM ISLEM ADEDI`; `shares_offered` girdi belgesinden | [p05, p95] kırpma → z-skor |

**`d1_lock` (kilit).** Gün içindeki en düşük fiyat üst limite eşitse fiyat gün boyu tavanda durmuştur. Tavanda alış emirleri kuyruk oluşturur; işlem ancak bir satıcı kuyruğa vurunca olur. Kilit, kuyruğun gün boyunca hiç tükenmediğini gösterir. Bu, karşılanmamış talebin bültenden okunabilen doğrudan ölçüsüdür. H99'da tavan kapanan 81 D1'in 70'i kilitlidir. Kilit varsa açılış = en yüksek = kapanış = üst limit olmalıdır; biri tutmazsa `WARN_D1_LOCK_INCONSISTENT` uyarısı verilir (H99'da 70/70 tutar).

**`d1_turnover` (el değiştirme).** Kilitli bir günde hacmi satıcılar belirler, çünkü alıcı kuyruğu sınırsız gibidir. "Hacim / arz edilen pay" oranı, tahsisat alanların ne kadarının ilk gün satmayı seçtiğini gösterir. Oran çok sağa çarpık olduğu için logaritması alınır. H99 kantilleri (oran olarak): p05 0.0009841, medyan 0.004202, p95 0.5402. Yani tipik bir D1'de arz edilen payların yalnız binde dördü el değiştirir. Kilitli arzlarda medyan 0.0028, kilitsizlerde 0.53'tür.

**Beklenen işaretler** (sonuç görülmeden yazıldı): δ_lock < 0 (kilit sonraki günlerin bozulma riskini düşürür) ve δ_turn > 0 (ilk gün çok satan kohort satmaya devam eder). Şartname ikinci işaret için karşı-mekanizmayı da yazar ("yüksek hacim talebin derin olduğunu gösterebilir") ve işareti başarı ölçütü saymaz.

**Alınmayan alanlar.** Sözleşme sayısı hacimle aynı bilgiyi taşır. AOF'nin limite uzaklığı kilitli günde tam sıfırdır ve kilitle örtüşür. Gün içi düşüşün büyüklüğü H99'da yalnız 11 arzda sıfırdan farklıdır; 11 gözlemle bir eğim tahmin edilemez. TL ciro arz büyüklüğüyle karışır.

**Ret ve uyarılar.** Kodlar B3 biçimindedir, yani öneksizdir (`refused.code`):

| Durum | Sonuç |
|---|---|
| D_1 işlem görmedi | kayıt yazılmaz (`D1_NOT_TRADED`); D_1 bir gün kayar |
| THM üst limiti yok | RET `D1_LIMIT_NA` |
| Kapanış ≠ üst limit | kapsam dışı `D1_NOT_CEILING` |
| Hacim boş/≤ 0, sözleşme > 0 | RET `D1_VOLUME_INVALID` |
| Açılış/en yüksek/en düşük yok | RET `D1_FIELD_INVALID` (şartnamede yoktu; uygulamada eklendi, H24) |
| Yarım gün, gün içi durdurma, özel işlem hacmi > 0 | tahmin + uyarı; hacim düzeltilmez |
| `d1_turnover` p05/p95 dışında | kırpılır, `clipped: true` |

Kaynak dosyalar: `docs/specs_faz5/SPEC_POST_D1_V0.md` §2, §9; `docs/specs_faz5/ekler/profil_d1.txt`; `borsai/predict_post_d1.py` (`evaluate_d1`, `d1_transform`); `docs/SPEC_DEVIATIONS.md` H8, H9, H23, H24.

### 5.2.3 Ofset fikri

Modelin en önemli tasarım kararı **ofset**tir. Listeleme öncesi `ceiling_hazard_v0` her gün için bir doğrusal öngörücü üretir:

```
η^base_d(x) = γ_g(d) + β · z^base(x)          x = (f1, f2, f3)
```

f1 arz büyüklüğüdür (TL, doğal log). f2 arz edilen payın arz sonrası sermayeye oranıdır (%). f3 toplam talep katıdır. γ üç gün grubunun sabitidir: g1 = {1}, g2 = {2, 3}, g3 = {4..10}. Donmuş değerler γ = (−1.8095, −2.1470, −1.0071) ve β = (f1: +0.4489, f2: −0.1787, f3: −0.5499).

D1 sonrası model bu η'yı **hiç değiştirmeden** alır ve yalnız d = 2..10 günlerine bir düzeltme ekler:

```
logit h_d = η^base_d(x) + δ · u(w),    d = 2..10
h_1       = sigmoid(η^base_1(x))       (değişmez; D1 zaten gözlendi)
u(w)      = z-skorlu (d1_lock, d1_turnover)
```

Neden ofset? Soru "D1 bilgisi bugünkü cevaba bir şey katıyor mu?"dur. Ofset tasarımında δ = 0, karşılaştırıcının kendisidir. Aradaki her fark yalnız D1 bilgisine atfedilir. γ ve β yeniden fit edilseydi fark "yeniden fit" ile "D1 bilgisi" arasında bölünemezdi; üstelik 8 parametre bütçeyi aşardı.

İki küçük ama önemli ayrıntı var:

- u eğitim ortalamasında sıfırdır. Bu yüzden ayrı bir sabit terim yoktur. "Ortalama D1 profilli" bir arzda model karşılaştırıcıyla aynı sayıyı verir.
- δ bütün d = 2..10 günlerinde **ortaktır**. Gün grubuna göre ayrı δ yoktur. Faz 5 denetimi k = 10'daki hafif kötüleşmeyi bu tasarım kararıyla açıkladı (5.6).

**Sayısal yol.** Şartnamenin sözde kodu ofseti `logit(hazard)` diye geri hesaplıyordu. Uygulama bunun yerine ana modelin doğrusal öngörücüsünü doğrudan alır (`predict_hazard.linear_predictor`). Nedeni: `logit(sigmoid(η))` binary64'te η'yı bit-eşit geri vermez. Şartname ise λ = ∞ ucunun ve h_1'in karşılaştırıcıya **bit-eşit** olmasını ister (H1; errata H25).

Kaynak dosyalar: `docs/specs_faz5/SPEC_POST_D1_V0.md` §3.1–§3.4; `models/ceiling_hazard_v0.json`; `borsai/predict_hazard.py` (`linear_predictor`); `docs/SPEC_DEVIATIONS.md` H1, H2, H25.

### 5.2.4 Fit: amaç, λ seçimi ve donmuş katsayılar

**Eğitim kümesi.** `H99_F3_PRESENT_L_GE_1`: f3'ü dolu ve D1'i tavan kapatan 81 arz. Bu arzların d ≥ 2 "kişi-dönem" (person-period, PP) satırları kullanılır. Bir arz, serisi sürdüğü sürece her gün için bir satır verir; satırın olayı "seri o gün bozuldu mu?"dur. Sayılar: 409 satır, 67 olay (bozulma), 342 sağ kalım. 2 parametreye 67 olay, parametre başına 33.5 olay demektir. Yaygın "parametre başına 10–15 olay" kuralının çok üstündedir.

**Amaç fonksiyonu.**

```
J(δ) = − Σ_r [ e_r · ln h_r + (1 − e_r) · ln(1 − h_r) ] + (λ/2) · ‖δ‖²
```

Çözücü Newton–Raphson'dur (2 boyut, gradyan ≤ 1e-10, en çok 100 yineleme, adım yarılama). Ofset sabit olduğu ve sonlu λ'da L2 cezası δ'nın sonsuza kaçmasını engellediği için ek "pseudo-satır"a gerek yoktur.

**λ seçimi.** Izgara {0.1, 1, 3, 10, 30, 100, 300, 1000, INF}. İç arz-bırak CV'de her arz j için j'nin bütün d ≥ 2 satırları dışarıda bırakılır. D1 ön işlemesi (p05, p95, μ, σ) kalan arzlardan yeniden hesaplanır; ofset değişmez. Skor satır başına ortalama log-kayıptır. En küçük skor kazanır. Eşitlikte **büyük λ** seçilir, yani daha temkinli olan. INF her zaman ızgarada kalır.

Donmuş nihai fit (`models/post_d1_hazard_v0.json`):

| λ | 0.1 | 1 | 3 | 10 | **30** | 100 | 300 | 1000 | INF |
|---|---|---|---|---|---|---|---|---|---|
| iç CV log-kayıp | 0.39516 | 0.39390 | 0.39189 | 0.38871 | **0.38788** | 0.39328 | 0.40058 | 0.40531 | 0.40792 |

| Alan | Değer |
|---|---|
| Seçilen λ | 30 |
| δ_lock | −0.3278985872465678 |
| δ_turn | +0.25106109793882575 |
| `d1_lock` μ / σ | 0.8641975 / 0.3425787 |
| `d1_turnover` p05 / p95 (ln) | −6.923783 / −0.615762 |
| `d1_turnover` μ / σ | −4.858983 / 1.976497 |
| Çözücü | 4 yineleme, max\|∇\| = 2.1e-14 |
| Eğitim | 81 arz, 409 satır, 67 olay, 342 sağ kalım |
| Dosya sha256 | `3f7640267cd0…` (INDEX_POST_D1.json'da kayıtlı) |
| Ebeveyn sha256 | `caa4dc867a9f…` (`ceiling_hazard_v0.json`) |

İki işaret de beklenen yöndedir. Ölçeğe çevrilmiş bir okuma (kendi cebirsel türetmem): kilitli bir D1, kilitsize göre d ≥ 2 günlerinin logit'ini δ_lock/σ_lock ≈ −0.96 kaydırır. Bu, bozulma oranında (odds) yaklaşık 0.38 kat demektir. Toplam kayma δ·u, eğitim aralığında yaklaşık −0.39 (kilitli, çok düşük hacim) ile +1.37 (kilitsiz, çok yüksek hacim) arasındadır.

**`training.cutoff_date` tuzağı.** JSON'daki `training.cutoff_date = 2026-08-13` bir kesim değildir. δ eğitim arzlarının 10 seansının en geç tarihidir. Şartnamenin veri kesimi 2026-08-19'dur. Skor kartı bu yüzden alanı `training_last_session_date` adıyla ve açıklamasıyla gösterir (H43). Fable denetimi "en son eğitim seansı"nı 2026-08-05 olarak yazar; bu, yalnız PP satırlarının son tarihi olarak okunabilir. İki sayının tanım farkını repoda açıkça çözen bir satır bulamadım (belirsiz).

Kaynak dosyalar: `models/post_d1_hazard_v0.json`, `models/INDEX_POST_D1.json`, `docs/faz5/IMPL_RAPOR.md` §7, `docs/fable_faz5_audit/AUDIT.md` §1.2, `docs/SPEC_DEVIATIONS.md` H43.

### 5.2.5 Çıktı: S_cond ve bir örnek hesap

Model standart hazard şemasını döndürür (`hazard[1..10]`, `S[1..10]`, `P_L`, `P_close_ceiling`). Birincil çıktı koşullu eğridir:

```
S_cond[k]    = S[k] / S[1] = Π_{d=2..k} (1 − h_d),   k = 2..10
p_break_next = 1 − S_cond[2]      (= h_2; "yarın bozulur mu?")
P_L_cond[l]  = P(L = l | L ≥ 1)
```

Koşullu görünüm projede tek bir fonksiyonla tanımlıdır (`predict_path.conditional_weights(S, 1)`). Bu yüzden yeni bir çıktı türü yoktur; uygulama ve skorlama bu modeli `ceiling_hazard_v0` gibi okur.

**Örnek: NETGL'in D1 akşamı (canlı akış provası).** NETGL D1'i (2026-09-17) tavanda kilitli kapattı. Prova geçici bir klon depoda yapıldı; gerçek repoya kayıt yazılmadı. Adımlar:

1. **Ana model ofseti.** NETGL'in listeleme öncesi girdileri: arz büyüklüğü 2 233 000 000 TL, arz edilen pay 87 500 000, arz sonrası sermaye 312 500 000, talep katı 2.84. z^base ≈ (+0.500, +0.596, −0.348) ve β·z ≈ +0.3095 olur. Buradan η_2 = η_3 = −2.1470 + 0.3095 = −1.8375 ve η_4..10 = −1.0071 + 0.3095 = −0.6976 çıkar (yeniden hesap; kayıttaki hazard'larla tutarlı).
2. **D1 özellikleri.** `d1_lock = 1`. `d1_turnover_ln = −3.7116`; yani oran ≈ 0.0244: arz edilen payların %2.4'ü D1'de el değiştirmiş. Kırpma yok.
3. **z.** u_lock = (1 − 0.8642)/0.3426 = +0.396. u_turn = (−3.7116 + 4.8590)/1.9765 = +0.581.
4. **Kayma.** δ·u = −0.3279·0.396 + 0.2511·0.581 = −0.130 + 0.146 = **+0.016**. Kilit riski düşürüyor, ortalamanın üstündeki el değiştirme artırıyor; ikisi neredeyse birbirini götürüyor.
5. **Sonuç.** h_2 = sigmoid(−1.8375 + 0.016) = **0.1392** (ana model 0.1373). S_cond[2] = 0.8608, S_cond[10] = 0.0422. Provadaki kayıt çıktısı bu sayılarla aynıdır.

| k | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|
| `post_d1_hazard_v0` S_cond | 0.8608 | 0.7409 | 0.4921 | 0.3268 | 0.2170 | 0.1441 | 0.0957 | 0.0636 | 0.0422 |
| `ceiling_hazard_v0` S_k/S_1 | 0.8627 | 0.7442 | 0.4968 | 0.3317 | 0.2215 | 0.1479 | 0.0987 | 0.0659 | 0.0440 |

RPS formülünü somut görmek için (yalnız gösterim; NETGL bu model için RETRO'dur ve bu sayı hiçbir skora girmez): NETGL'de gerçekleşen L = 3'tür. Gösterge 1[L ≥ k], k = 2 ve 3'te 1, sonra 0'dır. Model için RPS_1 = 0.0576, karşılaştırıcı için 0.0587 çıkar (yeniden hesap). Fark küçüktür, çünkü NETGL'in D1 profili ortalamaya yakındı.

Kaynak dosyalar: `docs/faz5/ekler/prova_netgl.txt`; `registry/records/NETGL/…json` (`ceiling_hazard_v0` çıktısı ve `model_inputs`); `borsai/predict_post_d1.py` (`updated_hazards`, `curves`).

### 5.2.6 Karşılaştırmalar, önceden yazılmış beklenti ve backtest

**Birincil hücre.** Koşullu RPS_1 (k = 2..10): `post_d1_hazard_v0` − `ceiling_hazard_v0` koşullu, aynı arzlar ve aynı fold'lar. Gerekçe: model basit kuralları geçse bile ürünün bugünkü cevabını geçmiyorsa ürüne bir şey katmaz. Kurallar (her zaman tavan, iki Kaplan–Meier, `@INF`) ve ikincil hücreler (Brier k = 2 "yarın", Brier k = 10 "sonuna kadar") ayrıca raporlanır.

**Önceden yazılmış beklenti.** 2026-09-24'te, hiçbir kod ve skor yokken yazıldı; sonradan değiştirilmedi. Birincil fark −0.020 … +0.003, "aralık büyük olasılıkla 0'ı içerir". Kazanç en olası Brier k = 2'de (−0.025 … 0.000). "Beklentiden çok iyi" eşiği: birincil fark < −0.040 ya da üst uç < −0.020 ya da Brier k = 2 farkı < −0.040. Eşik aşılırsa dondurmadan önce bağımsız yeniden üretim zorunludur.

**Backtest planı.** Faz 1B tavan fold'ları aynen kullanılır (kesim T = test arzının ilk işlem günü). Her fold'da ofset, o fold'un kendi `ceiling_hazard_v0` fit'idir; Faz 1B ledger'ıyla |Δ| ≤ 1e-9 eşleşmezse koşu durur. D1 özellikleri yalnız 1. seanstan okunur. Yükleyici 2..10. seanslarda yalnız {ticker, session_number, target_session_date} sütunlarına erişir; bu, erişimleri sayan bir testle sınanır.

**Sonuç** (87 fold: FIT_OK 70, yetersiz eğitim 1, kapsam dışı 16; n = 70, 22 ay):

| Hücre | Karşılaştırılan | Fark | %95 aralık | Hüküm (backtest) |
|---|---|---|---|---|
| **RPS_1 (birincil)** | `ceiling_hazard_v0` koşullu | **−0.0105** | **[−0.0264, +0.0058]** | ayırt edilemiyor |
| RPS_1 | `ceiling_hazard_v0@INF` | −0.0417 | [−0.0806, −0.0009] | backtest'te geçiyor (tasarıma maruz) |
| RPS_1 | `base_km_expanding` | −0.0481 | [−0.0892, −0.0050] | backtest'te geçiyor (tasarıma maruz) |
| Brier k = 2 | `ceiling_hazard_v0` koşullu | **−0.0512** | [−0.1010, −0.0097] | backtest'te geçiyor (tasarıma maruz) |
| Brier k = 10 | `ceiling_hazard_v0` koşullu | +0.0095 | [−0.0034, +0.0233] | ayırt edilemiyor |

Okuma: model "yarın"ı belirgin biçimde daha iyi bilir. Bu kazanç dokuz günün ortalamasına bölününce birincil hücrede kaybolur. Seçilen λ'lar: 3 → 22 fold, 10 → 14, 30 → 32, INF → 2. δ_lock 63/63 fold'da negatif, δ_turn 68/68 fold'da pozitiftir. Kalibrasyon: ortalama h_2 0.1556, gözlenen D2 kırılma oranı 0.1571.

§5 tablosunun 18 satırından 11'i tuttu, 7'si tutmadı. Tutmayanların dördü "daha iyi" yöndedir (Brier k = 2'de üç hücre ve Brier k = 3). Üçü "daha kötü" ya da yanlış çıktı (k = 10, `path_conditional` D3 p_up, "erken fold'larda INF" beklentisi). Brier k = 2 farkı −0.0512 < −0.040 olduğu için **"beklentiden çok iyi" tetiklendi**. Bu yüzden model, Fable'ın bağımsız yeniden üretiminden sonra donduruldu (5.6).

Kaynak dosyalar: `docs/specs_faz5/SPEC_POST_D1_V0.md` §4–§6; `docs/faz5/IMPL_RAPOR.md` §6; `docs/MODELS.md` "Faz 5: D1 sonrası güncelleme".

### 5.2.7 Canlı kayıt aşaması `POST_D1`

**Neden yeni aşama?** Listeleme öncesi kayıtların sınırı "push < D_1"dir. D1 bülteni D_1 akşamı çıktığı için POST_D1 kaydı o kurala göre hep geç kalırdı. Bu aşamanın kendi sınırı vardır: D2'ye dair ilk piyasa bilgisinin oluştuğu an.

**Zaman noktaları.** Pay Piyasası Prosedürü Ek-9'a göre açılış emir toplama 09:40'ta başlar. O andan itibaren D2'nin teorik açılış fiyatı piyasaya görünür.

```
D2_cal(a)           = resmi takvimde D_1(a)'dan sonraki ilk seans (ilan dışı kapanışlar düşülmüş)
T_open(a)           = D2_cal(a) 09:40:00 Europe/Istanbul   (+03:00 sabit ofset)
record_live_post_d1 = push_proof(kayıt commit'i).created_at < T_open   (kesin <)
```

09:39:59'da alınan kanıt LIVE'dır; tam 09:40:00'da alınan değildir (H33). D2'nin THM'si D1 kapanışından deterministik olarak hesaplanır, yeni bilgi taşımaz ve kayda alınmaz. Pencere D_1 akşamı ~18:30'dan ertesi sabah 09:40'a, yaklaşık 15 saattir.

**Sınıf formülü.**

```
outcome_ingest_commit_post_d1(a) = min( tarihi > D_1 olan ilk THB/THM'yi ekleyen commit,
                                        h ≥ 2 için dolu sonuç satırını ilk yazan commit )
model_prospective = is_ancestor(model commit'i, outcome_ingest_commit) VE model push kanıtlı
class = LIVE          prospektif VE record_live
      = LATE_RECORD   prospektif VE geç VE inputs_pit_ok_post_d1
      = RETRO         aksi
```

`inputs_pit_ok_post_d1`: kayıt yalnız D_1 tarihli, MANIFEST'e eşit sha'lı bültenleri taşır ve D_1 dışında hiçbir seansın alanını içermez.

**Kayıt dosyası.** `registry/post_d1/<TICKER>/<UTC>_<kısa-sha>.json`, şema `borsai.post_d1_record/1`. Ana blokları:

- `base_record`: arzın listeleme öncesi birincil kaydı ve sha'sı. f1–f3 girdileri bu kaydın `model_inputs`'undan alınır. Böylece ofset, karşılaştırıcının S'iyle bit-eşit olur. Uygun kayıt yoksa POST_D1 kaydı yazılmaz (`SKIPPED_POST_D1: NO_PRE_LISTING_RECORD`).
- `d1`: D_1'in THB ve THM dosya atfı (yol, sha256, URL, indirme zamanı), `fields_raw` (14 ham alan), `ceiling_close_D1`, kilit tutarlılığı.
- `d1_features`: kilit, oran (Decimal metin), ln, kırpma, z, uyarılar.
- `models`: INDEX_POST_D1.json'daki her model ve çıktısı.
- `comparators_conditional`: beş karşılaştırıcının S'i base_record'dan kopyadır; S_cond hesaplanır. Kural 1 gereği kuralların değeri de kayıttadır.

Bekçi (`registry.post_d1_record_problems`) h ≥ 2 sonucunu adlandıran bir anahtar ya da D_1 dışı bir bülten sha'sı görürse kırmızı verir. Aynı girdilerle ikinci bir kayıt `DUPLICATE_RECORD`'dur. T_open'dan sonra iptal yapılamaz.

**Akış (proje sahibinin D1 akşamı).** `docs/faz5/POST_D1_AKISI.md`:

1. D_1 akşamı THB çıkınca: `python -m borsai.outcomes update --through <D_1>` → commit.
2. `python -m borsai.freeze --post-d1 <TICKER>` → kayıt → commit.
3. **T_open'dan önce** proje sahibi `git push` ve `python -m borsai.push_proof <sha>` çalıştırır.
4. D2..D10 sonuçları geldikçe `python -m borsai.scoring`.

Uygulamada aynı akış Sicil ekranında dört adımlı **"D1 sonrası kayıt" sihirbazıdır** (SPEC_APP_EK3 §6.6). Sihirbaz ön koşulları denetler, T_open'ı Python'dan alır, `freeze --post-d1`'i çağırır, Rust tahmini ile kaydı karşılaştırır (parite) ve commit/push/kanıt komut bloğunu gösterir. Yerel saat yalnız bilgi olarak gösterilir. Uygulama bülten indirmez ve push yapmaz.

Kaynak dosyalar: `docs/specs_faz5/SPEC_POST_D1_V0.md` §7; `docs/faz5/POST_D1_AKISI.md`, `docs/faz5/LIVE_RAPOR.md`; `docs/SPEC_DEVIATIONS.md` H28–H47; `docs/app/SPEC_APP_EK3.md` §6.6.

### 5.2.8 Skor dosyası ve bugünkü durum: neden D1 sonrası kayıt yok?

`scores/scores_post_d1.json` (şema `borsai.scores_post_d1/1`, ölçek `live_post_d1`) bugün şunu söyler: `n_scored = 0`, `n_live = 0`, `n_late = 0`, `n_retro = 7`. Payda satırlarının yedisi de RETRO'dur. Hücre ve satır yoktur. `registry/post_d1/` dizini repoda hiç oluşmadı.

Nedeni tek bir sıralamadır:

| Olay | Commit | Zaman |
|---|---|---|
| 7 arzın D2+ sonuçları repoya girdi | `f1f9d44` | 2026-09-22 18:20 (+03:00) |
| `post_d1_hazard_v0` donduruldu | `7c18c0f` | 2026-09-24 16:36 (+03:00); push kanıtı 2026-09-24T14:13:55Z |

Model, sonuçları içeren commit'in atası değildir. Bu yüzden 7 arzın hepsi bu model için RETRO'dur (`class_evidence.basis = MODEL_FROZEN_AFTER_D2_OUTCOME`). RETRO olacağı baştan belli bir kaydı yazmak anlamsızdır. Dondurmadan sonra ise `registry/ipos.csv`'ye yeni bir halka arz girmedi. Son FROZEN arz NETGL'dir (D1 2026-09-17). Sonraki satırlar varant, fon, kod ya da pazar değişikliğidir (`OUT_OF_SCOPE`). Kısacası: model hazır, akış hazır, ama dondurmadan beri bir D1 akşamı yaşanmadı.

İki küçük not daha: VEYAS ve BKRGY'de L = 0'dır; bu model için zaten kapsam dışıdırlar. VEYAS'ın talep katı da yoktur (şartname §13 açık soru 2).

**Başka bir terazide sonuç var.** Zaman-dışı eski kohortta (H99 öncesi, 2020–2023 arzları) model, makine sıralı kayıtlarla ayrıca skorlandı. Bu ayrı bir ölçektir (`OOT_PRE_H99_POST_D1_MACHINE_SEQUENCED`) ve canlıyla toplanmaz. Açık kümede birincil fark −0.0418 [−0.0664, −0.0201], n = 59: "geçiyor (zaman-dışı terazide)". Kasa kümesinde −0.0347 [−0.0715, +0.0044], n = 45: "ayırt edilemiyor". Aynı terazide model `@INF` ve Kaplan–Meier kurallarından ayırt edilemiyor (nokta farkları pozitif, yani model aleyhine). Ayrıntı `docs/SCORES_OOT.md` §6, §10, §11'dedir.

Kaynak dosyalar: `scores/scores_post_d1.json`; `registry/ipos.csv`; `GITLOG.txt`; `docs/SPEC_DEVIATIONS.md` H29, H30; `docs/SCORES_OOT.md` §6, §10, §11.

## 5.3 Kırılma akşamı modeli: `break_floor_v0`

### 5.3.1 Neden bu model? "Devam mı, dur mu?" analizi

Şartname yazılmadan önce sorulan soru "seri bozulunca ne olur, arz fiyatının altına düşer mi?" idi. Fable şartnamenin ilk bölümünü (§0) bir değer analizine ayırdı ve iki aday soruyu karşılaştırdı.

**Aday soru 1: "D10 kapanışı ≤ arz fiyatı".** Orkestratörün maruziyet tablosuna göre kırılma türü bu hedefi neredeyse ayırmıyor: taban kırılmasında 9/32 = 0.28, düşüşle kırılmada 7/27 = 0.26, yükselişle kırılmada 0/8. Mükemmel kalibre üç sınıflı bir tahminin Brier'i 0.174, tek oranın Brier'i 0.182'dir. İdeal kazanç yalnız −0.008'dir; aralık yarı genişliği ise ≈ 0.035'tir. Yani ölçülemeyecek kadar küçüktür. Ayrıca D10 hedefinin bir kısmı mekaniktir ve öğrenilmez, hesaplanır (5.4). Karar: **D10 için yeni model "dur"**.

**Aday soru 2: "ertesi seans taban kapanış".** Kırılma günü tabanda kapanan 35 arzın 19'unda ertesi gün de taban geldi (0.54). Taban üstünde bozulanlarda bu oran çok düşük. İki sınıflı ideal Brier ≈ 0.146, tek oran ≈ 0.197: ideal kazanç ≈ −0.05. Ürünün türetilmiş cevabı ise ters yönlüdür (5.3.7). Karar: **devam; birincil soru ertesi seans taban**.

Bu yüzden modelin adı `break_floor_v0`'dır: "kırılma akşamı, taban".

Kaynak dosyalar: `docs/specs_faz8/SPEC_BREAK_V0.md` §0, maruziyet tablosu; `docs/specs_faz8/KARARLAR.md` B1, C1.

### 5.3.2 Olay tanımı ve kapsam

**Kırılma akşamı E_b**, D_b'nin THB'si yayımlandıktan sonraki akşamdır (ölçülen 18:25–18:40). Model yalnız **b ∈ 1..9** için çağrılır, çünkü tahmin edilen seans D_{b+1}'dir ve D10'u aşmamalıdır.

| Durum | Davranış | H99 sayısı |
|---|---|---|
| L = 0 (b = 1; D1 tavan değil) | **Kapsamda** (KARARLAR C3) | 18 |
| 2 ≤ b ≤ 9 | kapsamda | 64 |
| b = 9 | F1 tanımlı, F2 tanımsız (`TARGET_UNDEFINED_F2`) | 4 |
| b = 10 | `NOT_APPLICABLE_B10` (D11 yok) | 3 |
| L = 10 | `NOT_APPLICABLE_NO_BREAK` | 14 |
| Tam gün durdurma | seans sayılmaz, D_h kayar | 0 |
| D_b alt limiti yok | RET `B_LIMIT_NA` | 0 |

H99'da b ≤ 9 olan **82 kırılma akşamı** vardır. b dağılımı (1..9): 18 / 11 / 4 / 13 / 12 / 8 / 6 / 6 / 4.

b = 1 akşamı ilginç bir kesişimdir. D1 tavan kapanmadıysa D1 sonrası model kapsam dışıdır; kırılma modeli ise kapsamdadır. İkisi aynı akşam birbirini dışlar ve tek akışta çalışır (KARARLAR B11).

Kaynak dosyalar: `docs/specs_faz8/SPEC_BREAK_V0.md` §1.2; `docs/specs_faz8/ekler/profil_kirilma.txt` §1.

### 5.3.3 Hedefler: F1 ve F2

```
y_F1 = 1[ Decimal(close(D_{b+1})) == Decimal(lower_limit(D_{b+1})) ]      birincil
y_F2 = 1[ D_{b+1} taban VE D_{b+2} taban ]                                  ikincil (b ≤ 8)
```

Etiket, tavan etiketinin aynasıdır: resmi THB kapanışı ile THM alt limitinin ham metin eşitliği. "%10" varsayımı etikete girmez. F1 = 0 ise F2 de 0'dır. Modelin çıktıları `p_floor_F1` ve `p_floor_F2` olasılıklarıdır.

F2'nin anlamına dikkat: kırılma günü tabansa bile F2 "≥ 3 ardışık taban" değildir. F2, kırılmadan **sonraki** iki güne bakar.

Kaynak dosyalar: `docs/specs_faz8/SPEC_BREAK_V0.md` §2; `models/break_floor_v0.json` (`target_definition`).

### 5.3.4 Özellikler: `b_floor` ve `b_turnover`

| Ad | Formül | Alan | Ön işleme |
|---|---|---|---|
| `b_floor` | 1[`KAPANIS FIYATI`_b == `ALT LIMIT FIYATI`_b] | THB kapanış, THM alt limit (D_b) | z-skor |
| `b_turnover` | ln(`TOPLAM ISLEM ADEDI`_b / `shares_offered`) | THB hacim (D_b); `registry/inputs/<T>.json` | [p05, p95] kırpma (ln ölçeğinde, Type-7) → z-skor |

**`b_floor` (taban kapanış).** Fiyat alt limitteyken satış emirleri kuyruk oluşturur. Kapanış tam limitteyse kuyruk gün sonunda tükenmemiştir. Ertesi sabah aynı satıcılar bir adım aşağıda yeniden kuyruk olur. Bu, tavan kilidinin aynasıdır. Literatür de aynı yönü gösterir: Bildik ve Gülay (2006) limitte kilitlenmenin limite dokunmaktan farklı olduğunu bulur. Çin verisinde tabanda kapanan günü ~%86 oranında aynı yönlü bir gün izler (özet düzeyi). Beklenen: β_floor > 0. H99'da kapanış ya tam alt limittedir ya da en az 5 adım üstündedir; "1–4 adım üstü" 0/64'tür. Bu yüzden "tabana yakın" diye ayrı bir kutuya gerek yoktur. 82 akşamın 35'inde `b_floor = 1`'dir (31 + b = 1'de 4).

**`b_turnover` (kırılma günü el değiştirmesi).** Tabanda kapanan günde hacmi alıcılar belirler, çünkü satıcı kuyruğu sınırsız gibidir. Yüksek hacim "kuyruğun büyük kısmı emildi", düşük hacim "kuyruk sürüyor" demektir. Beklenen β_turn < 0 ama düşük güvenle, çünkü karşı-mekanizma da var: yüksek hacim "çok satıcı var" demek olabilir. H99'da kırılma günü medyan el değiştirme arz edilen payın 1.63 katıdır (taban kırılmasında 1.04, taban üstünde 1.92). Bu, seri günlerinin ortalamasının 8.3 katıdır.

**Alınmayanlar.** b ve kalan gün sayısı, Z/B grubu, seri hacim şoku, açılış ya da AOF konumu, sözleşme sayısı, fiyat istikrarı ve listeleme öncesi özellikler (f1–f3). Listeleme öncesi özellikler bilinçli olarak alınmadı. Soru "kırılma günü ne söylüyor?"dur; ayrıca f3'süz arzlar (VEYAS gibi) kapsamda kalır. **VBTS** (Volatilite Bazlı Tedbir Sistemi) kademesi de alınmadı. VBTS, Borsa İstanbul'un aşırı oynaklıkta bir pay için kademeli tedbir (ör. kredili işlem yasağı) uygulamasıdır ve KAP'ta akşam ilan edilir. Araştırma notunda yalnız 3 vaka bulundu ve tedbir kriterleri kamuya açık değildir; bu yüzden v0'ın dışında kaldı. Etkileşim (b_floor × b_turnover) üçüncü parametre olurdu; olay bütçesi izin vermedi.

**Ret ve uyarılar.** `B_LIMIT_NA`, `B_VOLUME_INVALID`, `B_FIELD_INVALID`, `INPUT_SHARES_OFFERED` RET'tir. Gün boyu tabanda kilit (`EN YUKSEK == ALT LIMIT`) yalnız bilgi uyarısıdır (`WARN_B_FLOOR_LOCK_ALLDAY`; H99'da 8). `shares_offered`'ın kaynağı D_1'den önce yayımlanmamışsa tahmin yine üretilir ama satırın sınıfı RETRO olur.

Kaynak dosyalar: `docs/specs_faz8/SPEC_BREAK_V0.md` §3, §11; `docs/specs_faz8/ekler/profil_kirilma.txt` §3–§4; `borsai/predict_break.py` (`evaluate_break_day`).

### 5.3.5 Model: iki başlık, L2-lojistik, C ızgarası

Her başlık (F1 ve F2) ayrı bir L2 cezalı lojistik regresyondur:

```
logit P(y_h = 1) = α_h + β_h,floor · z_floor + β_h,turn · z_turn,     h ∈ {F1, F2}
```

Fit yolu Faz 7C'nin `fit.fit_fall_horizon` → `_fit_logit` yoludur:

- **C ızgarası:** (ZERO, 0.0001, 0.001, 0.01, 0.1, 1, 10, 100). C, ceza gücünün tersidir. ZERO "yalnız sabit terim", yani eğitim oranıdır.
- **Seçim:** iç arz-bırak (LOOCV) **Brier**. Her C için her eğitim arzı sırayla dışarıda bırakılır; kırpma sınırları, μ ve σ kalan arzlardan yeniden hesaplanır. En küçük ortalama Brier kazanır. Eşitlikte **küçük C** seçilir (`rank_C`; ZERO en küçüktür), yani yine temkinli olan.
- **Ön işleme başlık başına:** F1 82, F2 78 satırla kurulur. Bu yüzden iki başlığın kırpma sınırları ve μ/σ'sı biraz farklıdır (N3).
- **Bütçe:** başlık başına 3 serbest parametre vardır (2 β + sabit). F1'de 25 olay gerçekleşti: β başına ≈ 12, sabit dahil ≈ 8 olay. Şartname ≈ 22–24 olay ve β başına ≈ 11 bekliyordu. F2'de yalnız 11 olay vardır.

Donmuş nihai fit (`models/break_floor_v0.json`):

| | F1 (birincil) | F2 (ikincil) |
|---|---|---|
| Eğitim (arz / olay) | 82 / 25 | 78 / 11 |
| Seçilen C | 1.0 | 0.1 |
| Sabit α | −1.0006869 | −1.8948516 |
| β_floor (z ölçeğinde) | +0.9866556 | +0.2872180 |
| β_turn (z ölçeğinde) | +0.0628689 | −0.3079898 |
| `b_floor` μ / σ | 0.426829 / 0.494617 | 0.423077 / 0.494047 |
| `b_turnover` μ / σ | 0.039322 / 0.952342 | 0.031418 / 0.931137 |
| `b_turnover` p05 / p95 (ln) | −2.178886 / 1.057949 | −2.183673 / 1.061365 |
| İç LOOCV Brier (en iyi / ZERO) | 0.18407 / 0.21719 | 0.11863 / 0.12430 |

F1'in iç LOOCV tablosu: ZERO 0.21719, 0.0001 0.21705, 0.001 0.21583, 0.01 0.20665, 0.1 0.18724, **1.0 0.18407**, 10 0.18438, 100 0.18443.

**Ham ölçekte okuma** (kendi cebirsel türetmem; kırpma aralığı içinde geçerli):

```
F1:  logit p = −1.8547 + 1.9948 · b_floor + 0.0660 · ln(hacim_b / arz edilen pay)
```

Taban kapanış, ertesi gün taban oranlarını (odds) e^1.995 ≈ 7.4 kat artırır. El değiştirmenin F1'deki katsayısı ise neredeyse sıfırdır ve işareti beklentinin tersidir (+0.063). F2'de el değiştirme beklenen yönde, negatiftir.

Kaynak dosyalar: `models/break_floor_v0.json` (`horizons`, `preprocessing`); `borsai/fit.py` (`V1_6_C_GRID`, `_fit_logit`, `rank_C`); `docs/SPEC_DEVIATIONS.md` N1, N3, N4.

### 5.3.6 Sıfır modeli `@ZERO` ve `base_floor_by_type`

**`break_floor_v0@ZERO`** her başlık için eğitim oranını verir: C = ZERO ucunun kapalı biçimidir. Kesir tam sayılarla hesaplanır (`Fraction`):

```
@ZERO F1 = 25/82 = 0.3048780487804878
@ZERO F2 = 11/78 = 0.14102564102564102
```

Bu, D1 sonrası modeldeki λ = INF ucunun karşılığıdır: "özellikler hiçbir şey katmasaydı". Backtest'te `@ZERO` ayrı bir koşu değildir; her fold'un eğitim oranı ledger'ın `zero_F1` / `zero_F2` sütunlarına yazılır. Canlıda donmuş oran kullanılır ve kırılma günü alanlarını hiç okumaz (testli).

**`base_floor_by_type`** iki hücreli bir tablodur: eğitimde, test arzıyla aynı `b_floor` sınıfındaki F1 oranı. Donmuş değerler:

| `b_floor` | olay / n | oran |
|---|---|---|
| 0 (taban üstünde kırılma) | 6 / 47 | 0.1277 |
| 1 (tabanda kırılma) | 19 / 35 | 0.5429 |

Bu karşılaştırıcının görevi "lojistiğin iki hücreli tabloya ne kattığını" ölçmektir. Pratikte tek kattığı şey el değiştirmedir. Canlıda yalnız F1 için vardır.

Kaynak dosyalar: `models/break_floor_v0@ZERO.json`; `models/break_floor_v0.json` (`comparators`); `docs/specs_faz8/SPEC_BREAK_V0.md` §4.2, §5.2; `docs/SPEC_DEVIATIONS.md` N5, N6.

### 5.3.7 Asıl karşılaştırıcı: `PRODUCT_BREAK_FLOOR`

Birincil hücre, modeli **ürünün o akşam zaten gösterdiği cevaba** karşı ölçer. Ürünün "yarın taban mı?" diye bir çıktısı yoktur. Ama tavan yolu modelinin (`ceiling_path_v0`) "durum-2" görünümünden türetilebilir.

**Adım 1: hücreler.** Listeleme öncesi `ceiling_path_v0` geçmiş arzlardan bir "kırılma sonrası getiri" kütüphanesi kurar. Serisi t = L günde biten her eğitim arzı için, m = 1..10 − t gün sonraki getiri hesaplanır:

```
v = close(D_{t+m}) / baz − 1,    baz = P (t = 0) ya da close(D_t)
hücre (g, m):  g = Z (t = 0) ya da B (t ≥ 1)
```

Bir hücrede 10'dan az gözlem varsa komşu hücrelerle havuzlanır (N_MIN = 10).

**Adım 2: atomlar.** Seri t = L'de kırıldığında ürün D_h için şu "atomları" eşit ağırlıkla kullanır:

```
r = (close(D_L) / P) · (1 + v) − 1,     v ∈ hücre(g(L), h − L),   ağırlık 1/n
```

F1 için h = b + 1 = L + 2'dir, yani m = h − L = 2'dir: L ≥ 1 ise hücre (B, 2), L = 0 ise (Z, 2) kullanılır. L = 0'da ölçek yoktur; atom doğrudan v'dir.

**Adım 3: eşik ve olasılık.** D_{b+1}'de mümkün en düşük getiri tabandır: Lo(close_b)/P − 1.

```
eşik_F1     = Lo(close_b) / P − 1
P_ürün(F1)  = Σ { w : r ≤ eşik_F1 + 1e-12 }          (h = b + 1)
eşik_F2     = Lo(Lo(close_b)) / P − 1
P_ürün(F2)  = Σ { w : r ≤ eşik_F2 + 1e-12 }          (h = b + 2)
```

**Neden "ters yönlü"?** Ürün iki şeyi kullanmaz. (1) Kırılma gününün kapanışını kullanmaz; ölçek son tavan gününün kapanışıdır (close_L). (2) Kırılma türünü kullanmaz; taban, düşüş ve yükseliş kırılmaları aynı hücreyi alır. Tabanda bozulan arzda close_b ≈ 0.9·close_L'dir. Ertesi gün taban için atomun close_L'ye göre ≈ −%19 düşmesi gerekir: hücrede çift taban gibi. Taban üstünde bozulan arzda eşik daha gevşektir: ≈ −%10…−%15. Hücre aynı olduğu için ürün **taban üstünde bozulan arza daha yüksek** "yarın taban" olasılığı verir. Gerçekte durum tersidir.

Backtest ölçümleri bu öngörüyü doğruladı, hatta beklenenden uç çıktı:

| Sınıf (yakın dönem) | n | Ürün ortalaması | Gözlenen y_F1 | Model ortalaması |
|---|---|---|---|---|
| Tabanda kırılma | 28 | 0.115 | 0.536 | 0.450 |
| Taban üstünde kırılma | 41 | 0.568 | 0.122 | 0.251 |

**Eşik yuvarlaması (N20).** Taban kırılmalarında ürün neden 0.115 kadar düşük? Hücredeki çift taban getirileri başka arzların fiyat seviyelerinde ve başka adım yuvarlamalarıyla oluşmuştur. Yarıdan fazlası test arzının kesin eşiğinin "hemen üstünde" kalır ve sayılmaz. Hücrenin "çift tabana yakın" (v ≤ −0.185) payı ortalama 0.273 iken, kesin eşiğin saydığı pay 0.115'tir. Şartname bu sınır davranışını önceden not etmiş ve tanımı yine bağlayıcı tutmuştur (§5.1: "eşik tanımı yine de budur"). Fable bu duyarlılığı ayrıca ölçtü (5.6).

**Canlıda.** Ürün karşılaştırıcısı arzın listeleme öncesi birincil kaydındaki `ceiling_path_v0` çıktısını ve donmuş hücrelerini ister. Bugünkü 7 kayıt yalnız 16 Faz 1 modelini taşır; `ceiling_path_v0` sonradan (Faz 4) donduruldu. Bu yüzden bugün 7/7 `NOT_AVAILABLE`'dır ve o çiftler ürün hücrelerinden düşer (N31). Yeni arzların kayıtları 27 modeli taşıyacağı için sorun kendiliğinden kalkar.

Kaynak dosyalar: `docs/specs_faz8/SPEC_BREAK_V0.md` §0.1, §5.1; `borsai/predict_break.py` (`product_thresholds`, `product_atoms`, `product_from_cells`, `product_break_floor`); `borsai/predict_path.py` (`build_cells`, `mixture_atoms`, `conditional_after_break`); `docs/faz8/IMPL_RAPOR.md` §5; `docs/SPEC_DEVIATIONS.md` N7, N20, N31.

### 5.3.8 Birincil hücre ve önceden yazılmış beklenti

| Öncelik | Metrik | Karşılaştırılan | Fold kümesi |
|---|---|---|---|
| **Birincil** | F1 Brier | `PRODUCT_BREAK_FLOOR` | yakın dönem (ilk işlem ≥ 2024-01-01) |
| İlan edilmiş ikincil | F1 Brier | `@ZERO` | yakın dönem |
| İlan edilmiş ikincil | F2 Brier | ürün; `@ZERO` | yakın dönem |
| İlan edilmiş ikincil | F1 Brier | `base_floor_by_type` | yakın dönem |
| Bilgi | ürün − `@ZERO` (F1) | — | yakın dönem |
| Keşif | bütün fold'lar, 2023, b = 1 / 2 ≤ b ≤ 9, kalibrasyon, yıl | — | hüküm yok |

`@ZERO` hücresi bir güvenlik ayağıdır: karşılaştırıcı zayıf olduğu için ürünü geçmek kolaydır. Ürünü geçip tek oranı geçemeyen bir model öne çıkarılmaz.

**Önceden yazılmış beklenti** (2026-10-01, kod ve skor yokken):

| Hücre | Beklenen fark | Aralık | Aralık 0'ı |
|---|---|---|---|
| **F1 − ürün (birincil)** | −0.080 | [−0.140, −0.020] | dışlaması olası |
| F1 − `@ZERO` | −0.040 | [−0.080, 0.000] | dışlaması olası, garanti değil |
| F1 − `base_floor_by_type` | −0.005 | [−0.025, +0.015] | içerir |
| F2 − ürün | −0.050 | [−0.110, +0.010] | içerir ya da negatif dışlar |
| F2 − `@ZERO` | −0.030 | [−0.070, +0.010] | içerir |
| bilgi: ürün − `@ZERO` | +0.040 | [0.000, +0.090] | pozitif dışlar ya da içerir |

"Çok iyi" eşiği: birincil fark < −0.160 ya da birincil üst uç < −0.080 ya da F1 − `@ZERO` < −0.090. Ayrıca önceden yazıldı: β_floor > 0, β_turn < 0 (düşük güven), nihai C 0.1–1, ZERO payı ≤ %20, n 60–69 (F2 için 55–65), kalibrasyon farkı ≤ 0.06. Orkestratör backtest'ten önce bir maruziyet notu ekledi: taban üstü kırılmalarda gerçek oran 6/47 ≈ 0.128'dir, şartnamenin varsaydığı ≈ 0.08 değil. Aralıklar buna rağmen değiştirilmedi.

Kaynak dosyalar: `docs/specs_faz8/SPEC_BREAK_V0.md` §5.2, §6; `docs/specs_faz8/KARARLAR.md` (B7, B8, orkestratör notu).

### 5.3.9 Backtest: plan ve sonuçlar

**Plan** (`H99_BREAK_WALK_FORWARD_E_CUTOFF_B_LE_9_MIN10ROWS_5EV_5NE`):

- Test birimi b ≤ 9 olan her arzdır. Kesim T = D_b'nin tarihi (kırılma akşamı).
- Eğitim satırı j ancak etiket seansı T'den **kesin önce** ise girer (F1: D_{b_j+1} < T; F2: D_{b_j+2} < T).
- En az 10 satır, 5 olay, 5 olay-dışı gerekir; yoksa `INSUFFICIENT_TRAINING_HISTORY`.
- Ürün karşılaştırıcısının hücreleri test arzının **ilk işlem gününe** kesilir, çünkü ürün kaydı listeleme öncesi dondurulur.
- D_b'den sonraki satırlarda yükleyici yalnız {ticker, session_number, target_session_date, thb_raw_close, thm_raw_lower_limit} sütunlarını okur (erişim sayacı testi).

**Fold sayıları.** F1: 82 fold. 2023'ün 13 fold'unun hepsi yetersiz eğitimli. FIT_OK 69, hepsi yakın dönemde (2024: 27, 2025: 16, 2026: 26). Seçilen C: 0.1 → 32, 1.0 → 27, 0.01 → 7, ZERO → 3. F2: FIT_OK 52.

**Hücreler** (yakın dönem, F1 n = 69, 21 ay; F2 n = 52, 16 ay):

| Hücre | Model | Karş. | Fark | %95 aralık | iyi / kötü / eşit |
|---|---|---|---|---|---|
| **F1 − ürün (birincil)** | 0.1878 | 0.3781 | **−0.1904** | **[−0.2520, −0.1247]** | 48 / 21 / 0 |
| F1 − `@ZERO` | 0.1878 | 0.2158 | **−0.0281** | **[−0.0453, −0.0074]** | 49 / 17 / 3 |
| F1 − `base_floor_by_type` | 0.1878 | 0.1771 | +0.0106 | [−0.0047, +0.0282] | 17 / 52 / 0 |
| F2 − ürün | 0.0955 | 0.1527 | −0.0572 | [−0.0847, −0.0239] | 32 / 20 / 0 |
| F2 − `@ZERO` | 0.0955 | 0.0956 | −0.0001 | [−0.0131, +0.0179] | 38 / 14 / 0 |
| bilgi: ürün − `@ZERO` | 0.3781 | 0.2158 | +0.1623 | [+0.1087, +0.2139] | — |

**§6 satır satır:** 13 satırın 9'u tuttu, 4'ü tutmadı. Tutmayanlar: birincil (beklenenden **iyi**), bilgi satırı (ürün beklenenden **kötü**), β_turn işareti (+0.063; fold'ların 52/66'sında negatif) ve F2 n'i (52 < 55). Başarısızlık tanımlarından hiçbiri gerçekleşmedi. Birincil fark < −0.160 ve üst uç < −0.080 olduğu için **"çok iyi" iki ayaktan tetiklendi**; bu da Fable'ın bağımsız yeniden üretimini zorunlu kıldı.

**Kalibrasyon:** yakın dönem ortalama p_F1 0.3315, gözlenen 0.2899 (+0.042, ≤ 0.06 tuttu). Sınıf içinde ise model taban üstünde yüksek (+0.129), tabanda düşük (−0.086) kalır. Yani lojistik sınıf ayrımını yarım yapıyor. 2025 kohortunda fark +0.204'tür (n 16).

**Duyarlılıklar** (model değil, kayıt amaçlı):

| Varyant | F1 − ürün | F1 − `@ZERO` |
|---|---|---|
| yalnız `b_floor` | −0.1968 | −0.0345 [−0.0545, −0.0106] |
| yalnız `b_turnover` | −0.1567 | +0.0056 [−0.0094, +0.0296] |
| + Z/B grubu | −0.1801 | −0.0178 [−0.0314, −0.0000] |

Okuma açıktır: bilginin hepsi taban kapanışındadır. El değiştirme tek başına tek oranı geçemez. `b_floor`'a eklendiğinde kazancı biraz küçültür (−0.0345 → −0.0281). `base_floor_by_type` hücresi de aynı şeyi söyler: lojistik, iki hücreli oran tablosundan iyi değildir. Şartname gereği model yazıldığı gibi kaldı; bu sayılar bir sonraki sürüm (v1) tartışması içindir.

Kaynak dosyalar: `docs/faz8/IMPL_RAPOR.md` §4–§9; `docs/faz8/backtest/` (ledger'lar, MANIFEST, SHA256SUMS); `docs/MODELS.md` "Faz 8: kırılma akşamı".

### 5.3.10 Ön eleme, terfi ve öne çıkma

**"Ön eleme / tasarıma maruz" etiketi.** Hipotez ("kırılma türü sonraki günleri ayırır") H99'dan doğdu. Özellikler, H99'un tek değişkenli profilinden sonra yazıldı. Bu yüzden H99 backtest'i kanıt değildir; yalnız bir **ön eleme**dir. Rapor dili bunu zorunlu kılar: backtest'te bir hücre aralığı 0'ın altındaysa yalnız "backtest'te geçiyor (tasarıma maruz)" yazılır. Asıl sınav canlı sicildir. Eski dönem (2020–2023) bu model için hiçbir aşamada kullanılmaz (KARARLAR A2: "bize bugün lazım").

**Terfi yok.** Proje kuralına göre model değişikliği yeni model_id demektir ve eski model listeden kalkmaz. Bir model ötekini "terfi edip" yerinden etmez; modeller yan yana durur. `@ZERO` satırı her zaman görünür.

**Öne çıkma kuralı** (kartta hangi sayının büyük gösterileceği; JSON'da `promotion` alanı). Önceden yazıldı ve iki aşamalıdır:

1. **Aşama 1 — canlı n_scored < 30.** p_F1 ancak **k1** sağlanırsa öne çıkar: yakın dönem backtest'inde hem F1 − ürün hem F1 − `@ZERO` aralığının üst ucu < 0. Etiket zorunludur: **"ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = k"**. k1 yoksa model ikincil satıra iner ve başlık "basit kuraldan ayırt edilemiyor (backtest)" olur.
2. **Aşama 2 — canlı n_scored ≥ 30.** Yalnız canlı hücreler sayılır (**k2**): canlı F1 − ürün ve F1 − `@ZERO` aralıklarının üst uçları < 0. Backtest etiketi artık öne çıkarmaya katkı vermez.

Bugünkü durum: k1 sağlandı (−0.1247 < 0 ve −0.0074 < 0). Kart aşama 1'dedir; etiket "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0". Ayda ≈ 2.5 kırılma akşamı beklenir; aşama 2 için yaklaşık 12 ay gerekir.

Kaynak dosyalar: `docs/specs_faz8/SPEC_BREAK_V0.md` §8, §12; `docs/specs_faz8/KARARLAR.md` A2, A3, B12; `scores/scores_break.json` (`card.promotion`); `docs/SPEC_DEVIATIONS.md` N32.

### 5.3.11 Rejim uyarısı ve bant koruması

**`FON_KRIZI_2026`.** Eylül 2026'da bir portföy yönetim şirketinin bir para piyasası fonu dahil iki fonu geri ödeme temerrüdüne düştü, SPK yedi şirketin 130 fonunu tasfiyeye aldı (§2.6.4) ve BIST100 ay boyunca −%16.65 düştü. NETGL'in D1'i krizin ilk günlerine denk geldi. Eğitim kümesinde (2023-09…2026-08) böyle bir stres yoktur. Kural: D_1 ≥ 2026-09-16 olan her arz `regime_tags`'e `FON_KRIZI_2026` alır. Kartta şu metin görünür: "Bu arzın ilk seansları Eylül 2026 fon krizi penceresine düşüyor; eğitim kümesinde (2023-09…2026-08) böyle bir stres yok. Beklenti (önceden yazıldı): model tabanı az tahmin eder." Etiket model girdisi değildir, satırı n'den düşürmez ve ayrı bir kırılımda gösterilir. Bitiş tarihi açıktır; proje sahibi karar verene kadar sürer (KARARLAR C4).

**`BAND_RULE_MISMATCH`.** Yastık kuralı (5.4) ve ürün eşiği ±%10 bant ile adım tablosuna dayanır; model özellikleri dayanmaz. Her kırılma akşamında THM'den alt limit/referans oranı ölçülür. Oran [0.9, 0.9020] dışındaysa (üst limit için [1.098, 1.1]) uyarı verilir, yastık rozeti gizlenir ve satır `BAND_CHANGED` etiketi alır. Tahmin yine üretilir ve skorlanır. 21.09.2026 tarihli Pay Piyasası Prosedürü rev. 54'ün bant kuralını değiştirmediği ayrıca doğrulandı. Çekince: ±%10'un bütün pazarlarda geçerli olması dipnottaki duyurulara dayanır; o duyurular açılmadı.

Kaynak dosyalar: `models/break_floor_v0.json` (`regime_warning`, `band_rule`); `docs/specs_faz8/SPEC_BREAK_V0.md` §1.3, §6, §11; `docs/faz8/BANT_DOGRULAMA.md`; `docs/arastirma/TR_HALKA_ARZ_PIYASASI_20261001.md`.

### 5.3.12 NETGL'in kırılma akşamı: adım adım

NETGL'in makine kaydı (`registry/post_break/NETGL/machine_20261002T161730Z_c5a61ad0cf26.json`) bütün ara değerleri taşır. Hesabı bu değerlerden yeniden yaptım; sonuç kayıtla en son ondalığa kadar tutar.

**1. Seri.** D1 (2026-09-17) 28.06, D2 30.86, D3 33.94: üçü de üst limitte. D4 (2026-09-22) kapanış 30.56, üst limit 37.32. L = 3, b = 4, kırılma akşamı 2026-09-22.

**2. Ham alanlar (D_b = D4).**

| Alan | Değer |
|---|---|
| Kapanış | 30.56 |
| Alt limit | 30.56 |
| Referans | 33.94 |
| En yüksek / en düşük / açılış | 32 / 30.56 / 30.56 |
| İşlem adedi (hacim) | 9 071 008 |
| Sözleşme sayısı | 42 067 |
| Arz edilen pay (`registry/inputs/NETGL.json`) | 87 500 000 (kaynak 2026-09-13'te yayımlandı, D_1'den önce) |

Bant: 30.56 / 33.94 = 0.90041 ∈ [0.9, 0.9020]. Kural tutuyor.

**3. Özellikler.** Kapanış = alt limit → `b_floor = 1`. Oran = 9 071 008 / 87 500 000 = 0.103669; ln = **−2.26656**.

**4. Kırpma.** −2.26656, F1'in p05'i olan −2.17889'un altında. Değer −2.17889'a çekilir (F2'de −2.18367'ye). Kayıt `B_TURNOVER_CLIPPED_TO_TRAINING_P05_P95` uyarısını taşır. NETGL'in kırılma günü el değiştirmesi (arz edilen payın %10'u) eğitim kümesinin 5. yüzdeliğinin (≈ %11) altındadır; yani H99 kırılmalarının yaklaşık %95'inden düşüktür.

**5. z-skorlar.**

```
F1: z_floor = (1 − 0.426829) / 0.494617 = +1.15882
    z_turn  = (−2.178886 − 0.039322) / 0.952342 = −2.32921
F2: z_floor = (1 − 0.423077) / 0.494047 = +1.16775
    z_turn  = (−2.183673 − 0.031418) / 0.931137 = −2.37891
```

**6. Doğrusal öngörücü ve olasılık.**

```
F1: η = −1.00069 + 0.98666·(+1.15882) + 0.06287·(−2.32921)
      = −1.00069 + 1.14335 − 0.14644 = −0.00377
    p_F1 = sigmoid(−0.00377) = 0.49906   → kayıt: 0.4990578357497034  (≈ %50)

F2: η = −1.89485 + 0.28722·(+1.16775) + (−0.30799)·(−2.37891)
      = −1.89485 + 0.33540 + 0.73268 = −0.82677
    p_F2 = sigmoid(−0.82677) = 0.30433   → kayıt: 0.30432770420243327 (≈ %30)
```

**7. Okuma.** F1'de neredeyse bütün iş `b_floor`'dan gelir (+1.143). El değiştirme katkısı küçüktür (−0.146). F2'de ise düşük el değiştirme olasılığı belirgin biçimde artırır (+0.733): "kuyruk emilmedi, satış sürecek". Kırpma olmasaydı p_F1 0.4976, p_F2 0.3102 olurdu; kırpma etkisi küçüktür.

**8. Karşılaştırıcılar.** `@ZERO`: F1 0.3049, F2 0.1410. `base_floor_by_type` (sınıf 1): 0.5429. Ürün: `NOT_AVAILABLE`. Model, taban sınıfının ham oranından (0.543) biraz aşağıdadır; bunun nedeni F1'deki küçük pozitif el değiştirme katsayısı ve NETGL'in düşük el değiştirmesidir.

**9. Gerçekleşen** (bilgi; NETGL bu model için RETRO'dur). `docs/live/NETGL_D10_RAPOR.md`'ye göre D4…D10 kapanışlarının yedisi de alt limittedir: D5 27.52, D6 24.78, D7 22.32, D8 20.10, D9 18.09, D10 16.29. Yani y_F1 = 1 ve y_F2 = 1'dir. Kayıttaki `t_open` 2026-09-23T09:40:00+03:00'dır; D5'in açılış emir toplamasının başladığı andır.

Kaynak dosyalar: `registry/post_break/NETGL/machine_20261002T161730Z_c5a61ad0cf26.json`; `models/break_floor_v0.json`; `registry/inputs/NETGL.json`; `docs/live/NETGL_D10_RAPOR.md`.

## 5.4 Yapısal sıfır ve yastık aritmetiği

### 5.4.1 Fikir: yastık

Bir arz D1'den itibaren tavan yaptıkça fiyatı arz fiyatının üstüne çıkar. Bu farka **yastık** denir. Fiyat bir günde en çok bir taban kadar (≈ %10) düşebildiği için, yastığı silmek için gereken taban sayısı hesaplanabilir. Kalan gün sayısı buna yetmiyorsa D10 kapanışının arz fiyatının altında olması **mekanik olarak imkânsızdır**. Bu, öğrenilen bir şey değil, aritmetiktir. Bu yüzden projede model değil, kod olarak durur ve skorlanmaz.

Kaynak dosyalar: `docs/specs_faz8/SPEC_BREAK_V0.md` §0.2, §2.3–§2.4.

### 5.4.2 Yaklaşık kural: k_t ve r_t

Her akşam (t. seansın akşamı) iki sayı hesaplanır:

```
k_t = ln(P_t / P) / ln(1 / 0.9)     arz fiyatına olan uzaklık, "taban adımı" cinsinden
r_t = 10 − t                        D10'a kalan seans sayısı
k_t ≥ r_t  ⇒  D10'da arz altına inme olasılığı yapısal olarak sıfır
```

P_t t. günün kapanışı, P arz fiyatıdır. Sezgi: her taban fiyatı 0.9 ile çarpar. P_t'den P'ye inmek için 0.9^n · P_t ≤ P olmalıdır, yani n ≥ k_t. Kalan gün sayısı r_t, k_t'den küçükse yetecek kadar taban günü yoktur.

Kırılma akşamında t = b'dir. Araştırma notundaki tablo şu senaryoyu özetler: D1'den başlayan N günlük kesintisiz tavan serisi, ardından kalan 10 − N günün hepsi taban. Son sütun bu en kötü senaryodaki D10 fiyatıdır (1.1^N · 0.9^(10−N)):

| D1'den seri (N) | Yastık | Silmek için gereken taban | D10'da mümkün en düşük fiyat / P |
|---|---|---|---|
| 2 | +%21 | 1.8 | 0.52 |
| 3 | +%33 | 2.7 | 0.64 |
| 4 | +%46 | 3.6 | 0.78 |
| 5 | +%61 | 4.5 | 0.95 |
| 6 | +%77 | 5.4 | 1.16 (arz altı imkânsız) |
| 8 | +%114 | 7.2 | 1.74 (arz altı imkânsız) |

Kaba sonuç: D1'den 6 ya da daha uzun bir tavan serisinden sonra D10'da arz altı imkânsızdır.

Kaynak dosyalar: `docs/arastirma/TR_HALKA_ARZ_PIYASASI_20261001.md` ("Yastık aritmetiği D10 sorusunun yarısını mekanik olarak çözüyor").

### 5.4.3 Kesin kural: alt limit zinciri ve "10. günün en düşük mümkün kapanışı"

Yaklaşık kural adım yuvarlamasını yok sayar. Kod kesin olanı hesaplar (`predict_break.structural_zero_d10`):

```
min10 = Lo^(10 − b)(close_b)        alt limit işlevi Lo, 10 − b kez, kesin Decimal
min10 > P  ⇒  P(D10 ≤ arz) = 0 (yapısal)
```

**min10, 10. günün en düşük mümkün kapanışıdır**: kırılma gününden sonraki her seans tabanda kapansa bile fiyat bunun altına inemez. Alt limit adıma yukarı yuvarlandığı için zincir, nominal 0.9^(10−b) çarpımından biraz yüksek kalır.

H99'da 82 kırılma akşamında:

- 16 akşamda D10 ≤ arz mekanik olarak imkânsızdır. Hepsi b ≥ 7'dir (b = 7: 6, b = 8: 6, b = 9: 4).
- Yaklaşık kural (k_b ≥ r_b) ile kesin zincir 82/82 aynı hükmü verir.
- Mümkün olan 66 akşamın 8'inde arz altı ancak **kalan bütün günler taban** olursa mümkündür (min10/P ∈ (0.9, 1]).
- min10/P medyanı 0.638'dir.

Gösterim kuralı: rozet ancak bant kuralı tutuyorsa gösterilir (`BAND_RULE_MISMATCH` yoksa). Kart ya "D10 ≤ arz yapısal olarak imkânsız" rozetini ya da "k_b = …, kalan r_b = …" satırını gösterir. Rozet hiçbir zaman skorlanmaz.

Kaynak dosyalar: `borsai/predict_break.py` (`structural_zero_d10`, `structural_zero_badge`); `docs/specs_faz8/ekler/profil_kirilma.txt` §5; `docs/faz8/IMPL_RAPOR.md` §3; `docs/SPEC_DEVIATIONS.md` N9.

### 5.4.4 Örnekler: TKNKA, CITAS, NETGL

**TKNKA (yapısal sıfır).** Seri 7 gün sürdü, D8'de (2026-08-31) 157.1'den kapanışla bozuldu. Arz fiyatı 85.4.

```
k_b = ln(157.1 / 85.4) / ln(1/0.9) = 0.6095 / 0.1054 = 5.79      r_b = 10 − 8 = 2
Lo(157.1)  = ⌈141.39 / 0.10⌉ · 0.10 = 141.40
Lo(141.40) = ⌈127.26 / 0.10⌉ · 0.10 = 127.30 = min10
127.30 > 85.4  ⇒  imkânsız
```

Yaklaşık 6 taban gerekir ama yalnız 2 seans kalmıştır. Kayıttaki `structural_zero_D10` bloğu aynen bunu taşır: `min10 = "127.30"`, `impossible = true`, `k_b = 5.785`, `r_b = 2`.

**CITAS (sınırda).** b = 6, kapanış 112, P = 73.7, k_b = 3.97, r_b = 4. Zincir: 112 → 100.80 → 90.75 → 81.70 → **73.55**. min10 = 73.55 < 73.7 olduğundan arz altı mümkündür, ama ancak kalan dört günün dördü de taban olursa. Adım yuvarlamasının ne kadar önemli olabileceğini gösterir: fark yalnız 15 kuruştur.

**NETGL (mümkün ve gerçekleşti).** b = 4, kapanış 30.56, P = 25.52, k_b = 1.71, r_b = 6. Zincir: 30.56 → 27.52 → 24.78 → 22.32 → 20.10 → 18.09 → **16.29**. Kural "arz altı için kalan 6 seansta ≈ 2 taban gerekir" der. NETGL'de kalan altı seansın altısı da taban geldi ve D10 kapanışı tam olarak 16.29 oldu (`docs/live/NETGL_D10_RAPOR.md`). Yani 10. günün en düşük mümkün kapanışı birebir gerçekleşti.

Yedi kaydın tamamı (yastık değerleri makine kayıtlarından; gerçekleşen D10 `data/outcomes/<T>.csv`'den, yalnız bilgi):

| Arz | b | close_b | P | k_b | r_b | min10 | İmkânsız mı? | Gerçekleşen D10 |
|---|---|---|---|---|---|---|---|---|
| BKRGY | 1 | 11.64 | 12.93 | −1.00 | 9 | 4.54 | hayır | 7.77 |
| VEYAS | 1 | 135.9 | 136 | −0.01 | 9 | 52.85 | hayır | 136 |
| NETGL | 4 | 30.56 | 25.52 | 1.71 | 6 | 16.29 | hayır | 16.29 |
| INTET | 5 | 74.55 | 53.6 | 3.13 | 5 | 44.08 | hayır | 61.15 |
| CITAS | 6 | 112 | 73.7 | 3.97 | 4 | 73.55 | hayır (sınırda) | 128 |
| KPEKS | 6 | 136.1 | 94 | 3.51 | 4 | 89.40 | hayır | 95.2 |
| TKNKA | 8 | 157.1 | 85.4 | 5.79 | 2 | 127.30 | **evet** | 190 |

Negatif k_b, fiyatın kırılma günü zaten arz fiyatının altında olduğu demektir (BKRGY, VEYAS).

Kaynak dosyalar: `docs/specs_faz8/SPEC_BREAK_V0.md` §2.4, §0.2; `docs/specs_faz8/ekler/profil_kirilma.txt` §5; `borsai/predict_break.py` (`structural_zero_d10`, `structural_zero_badge`); `models/break_floor_v0.json` (`structural_zero_rule`); `docs/arastirma/TR_HALKA_ARZ_PIYASASI_20261001.md` ("Yastık aritmetiği"); `registry/post_break/*/machine_*.json`; `data/outcomes/*.csv`.

## 5.5 Makine kayıtları (`MACHINE_SEQUENCED`)

### 5.5.1 Neden insan kaydı yerine makine sırası?

Canlı terazinin dürüstlüğü şu soruya dayanır: "Bu tahmin, sonuç bilinmeden önce var mıydı?" Listeleme öncesi ve POST_D1 aşamalarında cevap bir **insan kaydıdır**: kayıt yazılır, push edilir, push kanıtı alınır. Bu yolun iki zayıflığı ölçüldü:

1. **Akşam yükü.** Her kırılma akşamı Claude'un sonuç güncellemesi, kayıt ve commit yapması; proje sahibinin de ertesi sabah 09:40'tan önce push ve kanıt alması gerekirdi. Ayda 2–3 akşam demektir. Bugünkü sicil bunun zor olduğunu gösterir: 7 listeleme öncesi kaydın hepsi geç yazıldı (LATE_RECORD) ve hiç POST_D1 kaydı yazılmadı.
2. **LATE_RECORD'ın açık kanalı.** Geç yazılan kayıtta, girdiyi toplayan kişinin sonucu biliyor olması ihtimali vardır.

Kırılma akşamında girdiyi toplayan biri yoktur. Bütün girdiler zaten repodadır: D_1..D_b'nin sha-pinli resmi bültenleri ve listeleme öncesi girdi dosyası (`registry/inputs/<T>.json`; yalnız `shares_offered` ve arz fiyatı). Bu dosyalar **tarih kuralıyla** seçilir. İnsan hiçbir değer girmez. Bu yüzden tahmin, skorlama anında dondurulmuş JSON'dan **deterministik** olarak üretilebilir. Kayıt ne zaman yazılırsa yazılsın aynı sayı çıkar.

Geriye tek bir kanıt kalır: modelin sonuçtan önce var olduğu. O da git DAG'ından okunur. Şartname bu yolu (a) "makine sıralı" diye seçti; gece insan kaydı (b) v0'da yoktur ama aynı model_id ile ileride eklenebilir (§9.1). Kalıp yeni değildir: eski kohortun POST_D1 kayıtları da (`registry/oot/post_d1/`) makine sıralı yazılmıştı.

Kalan kanallar ve kapatılışları:

- **Kod sonradan değişirse?** Kayıt `code` bloğunda `git_head`, `borsai_dirty`, `borsai_source_sha256` ve `predict_break_sha256` taşır. Skorlama, tahmini bugünkü kodla **bellekte yeniden üretir** ve kayıtla karşılaştırır. |Δ| > 1e-12 ya da durum farkı `ScoringError`'dur.
- **Seçim yanlılığı?** Skorlayıcı `ipos.csv`'deki bütün FROZEN arzları sayar. Kaydı yazılmayan arz "atlandı" olarak değil, bir payda durumu olarak görünür.

Kaynak dosyalar: `docs/specs_faz8/SPEC_BREAK_V0.md` §9.1; `docs/faz8/LIVE_RAPOR.md` §0; `docs/fable_faz5_audit/AUDIT.md` §6 (yedi listeleme öncesi kaydın LATE_RECORD olduğu).

### 5.5.2 Sınıf kuralı ve git DAG kanıtı

```
outcome_ingest_commit_break(a) = min( data/raw/bist/ altına tarihi > D_b(a) olan ilk THB/THM'yi ekleyen commit,
                                      data/outcomes/<a>.csv'ye h ≥ b + 1 dolu satırı ilk yazan commit )
model_prospective_break(m, a)  = is_ancestor(commit_frozen(m), outcome_ingest_commit_break(a))
                                 VE push_proof(commit_frozen(m)) var
inputs_pit_ok_break(a)         = shares_offered kaynağı D_1'den önce yayımlanmış
                                 VE kayıt bekçisi temiz VE her bülten sha'sı MANIFEST'e eşit

class = LIVE               prospektif VE insan kaydı T_open'dan önce push kanıtlı VE PIT   (v0'da üretici yok)
      = MACHINE_SEQUENCED  prospektif VE insan kaydı yok VE PIT
      = RETRO              aksi
```

Bülten terimi **pazar geneli**dir: herhangi bir arzın D_b'den sonraki tarihli bülteni repoya girdiği anda o akşamın "geleceği" repodadır. Sonuç commit'i henüz yoksa kontrol HEAD'e karşı yapılır.

Bu formül CLAUDE.md kural 1'e aynen eklendi: "Bir arz bu aşamanın modeli için ancak modelin JSON'u, D_b'den sonraki ilk bülteni ya da h ≥ b + 1 sonucunu repoya sokan commit'in atası ve push kanıtlı ise prospektiftir; bu satırlar `MACHINE_SEQUENCED` sınıfıyla ayrı ölçekte (`live_break`) skorlanır, LIVE ile toplanmaz…"

**Kritik ayrım.** Kayıt dosyasındaki `exposure_class = "MACHINE_SEQUENCED"` alanı kaydın **türünü** söyler: "bu kayıt makine tarafından üretildi". Satırın **sınıfı** ise skorlamada ayrıca hesaplanır. Bugünkü yedi kaydın türü MACHINE_SEQUENCED, sınıfı RETRO'dur.

Kaynak dosyalar: `docs/specs_faz8/SPEC_BREAK_V0.md` §9.3, §9.4; `CLAUDE.md` kural 1; `borsai/scoring.py` (`outcome_ingest_commit_after`, `model_prospective_break`, `record_live_break`); `borsai/predict_break.py` (`class_break`); `docs/SPEC_DEVIATIONS.md` N29, N30.

### 5.5.3 Akış: `python -m borsai.scoring --break`

Akşam iş yükü yoktur. Sonuçlar güncellendikten sonra, istenen herhangi bir zamanda tek komut yeter:

| Adım | Ne zaman | Kim | Ne |
|---|---|---|---|
| 1 | Her seans akşamı | Claude | `python -m borsai.outcomes update` → `data/raw/bist`, `data/outcomes` commit'i |
| 2 | Adım 1'den sonra, acele yok | Claude | `python -m borsai.scoring --break` → `registry/post_break`, `scores/scores_break.json`, `docs/SCORES_BREAK.md` commit'i |
| 3 | Sonraki push'la | Proje sahibi | `git push`; makine kaydı için ayrı push kanıtı **gerekmez** |

`--break` üç iş yapar (`main_break`):

1. `ensure_post_break_records`: FROZEN olan, kırılma akşamı (b ∈ 1..9) oluşmuş, D_1..D_b bültenleri pinli, girdisi ve takvimi olan her arz için eksik makine kaydını yazar.
2. `build_break_scores`: `scores/scores_break.json` (şema `borsai.scores_break/1`, ölçek `live_break`).
3. `render_break_doc`: yazılmış JSON'dan `docs/SCORES_BREAK.md`.

**Mükerrer kayıt yoktur.** Anahtar şu üçlüdür: INDEX_POST_BREAK sha'sı, D_1..D_b bülten sha'ları, girdi dosyası sha'sı. Kod sürümü anahtarda değildir; kod değişince yeni kayıt yazılmaz, yalnız bellekte parite yapılır. İkinci koşu 0 kayıt yazar; JSON'da yalnız `generated_at_utc` değişir. Dosya adı `machine_<UTC>_<kısa-sha>.json` biçimindedir ve içerik adreslidir (kısa sha, içeriğin hash'idir). Dosya `'xb'` kipiyle açılır: varsa üzerine yazılmaz. Kayıtlar append-only'dir, iptal edilmez.

Kaynak dosyalar: `docs/faz8/POST_BREAK_AKISI.md`; `borsai/scoring.py` (`main_break`, `ensure_post_break_records`); `borsai/freeze.py` (`write_post_break_machine_record`); `docs/SPEC_DEVIATIONS.md` N26, N27.

### 5.5.4 Kayıt dosyasının şeması

Şema `borsai.post_break_machine_record/1`:

| Blok | İçerik |
|---|---|
| üst düzey | `schema_version`, `record_type = "MACHINE"`, `record_stage = "POST_BREAK"`, `exposure_class`, `ticker`, `produced_at_utc` (bilgi, kanıt değil), `t_open` (bilgi) |
| `code` | `git_head`, `borsai_dirty`, `borsai_source_sha256`, `predict_break_sha256` |
| `inputs_ref` | girdi dosyası ve sha'sı, `shares_offered {value, source_published_at}`, `ipo_price_tl`, `inputs_pit_ok` |
| `streak` | `L`, `b`, `break_date`; h = 1..b her seans için tarih, THB/THM dosya ve sha, ham kapanış, ham üst limit, `ceiling_close` |
| `break_day` | D_b'nin 14 ham alanı (`fields_raw`), `b_floor`, `band_ratio` (alt/referans, üst/referans, `rule_ok`), `half_day`, `halt_flag`, uyarılar |
| `features` | `b_floor`, oran (Decimal metin), ln, başlık başına `clipped` ve `z` |
| `models_index`, `models` | INDEX_POST_BREAK sha'sı; her model için durum, `params_sha256`, `spec_sha256`, çıktı (F1/F2 `p_floor`, uyarılar) |
| `comparators` | `PRODUCT_BREAK_FLOOR {status, F1, F2, kaynak}`; `base_floor_by_type: null` |
| `structural_zero_D10` | `min10`, `P`, `impossible`, `k_b`, `r_b`, `band_rule_ok` |
| `summary` | model / tahmin / ret / kapsam dışı sayıları |

**Bekçi** (`registry.post_break_record_problems`). `streak.sessions` tam olarak h = 1..b olmalı ve son seans D_b olmalıdır. h > b'yi adlandıran hiçbir anahtar (`lower_limit_D…`, `floor_close_D…` gibi) ve hiçbir sonuç sözcüğü (`y_F1`, `realized_F1` …) bulunamaz. Hiçbir tarih D_b'den sonra olamaz. Hiçbir sha256, D_1..D_b dışındaki bir bültenin pinli sha'sı olamaz. Her bülten atfı MANIFEST'e eşit olmalıdır.

Kaynak dosyalar: `docs/specs_faz8/SPEC_BREAK_V0.md` §9.2; `registry/post_break/NETGL/machine_20261002T161730Z_c5a61ad0cf26.json`; `borsai/registry.py` (`post_break_record_problems`); `docs/SPEC_DEVIATIONS.md` N28.

### 5.5.5 Payda, ölçek ve dil

`scores_break.json`'da `ipos.csv`'deki her FROZEN arz için tek bir payda satırı vardır. İlk tutan durum yazılır: RETRO → STREAK_PENDING → STREAK_TARGET_UNAVAILABLE → NOT_SCORABLE_STREAK_NA → NOT_APPLICABLE_NO_BREAK → NOT_APPLICABLE_B10 → BULLETIN_NOT_PINNED → INPUTS_NOT_AVAILABLE → CALENDAR_NOT_AVAILABLE → RECORD. Satır sayısı sayaçların toplamına eşittir (özdeşlik testi).

`live_break` ölçeği LIVE ve MACHINE_SEQUENCED satırlarını içerir. Her hücre `n_live / n_machine` kırılımını gösterir. Hiçbir ölçekle (listeleme öncesi canlı, POST_D1, backtest, zaman-dışı) toplanmaz. Dil SPEC_SCORING §8'dir: n < 10 iken yalnız satır tablosu; 10 ≤ n < 30 iken "yetersiz örnek"; "geçiyor" yalnız n ≥ 30 ve aralık tamamen 0'ın altındaysa. Canlıda model ancak birincil **ve** `@ZERO` hücrelerinin ikisi de "geçiyor" ise geçer.

Kaynak dosyalar: `scores/scores_break.json` (`definitions`, `models[0].live_break.denominator`); `docs/SCORES_BREAK.md` §2; `docs/SPEC_DEVIATIONS.md` N30, N32.

### 5.5.6 Bugünkü yedi kayıt ve neden hepsi RETRO

Yedi kayıt 2026-10-02T16:17:30Z'de, `7ee0027` commit'inde ilk `--break` koşusuyla yazıldı (kod `71cf079`). b, D_b ve `b_floor` beklenen tabloyla birebir, p_F1 ve p_F2 bellekteki yeniden üretimle maks |Δ| = 0.0'dır.

| Arz | D_1 | L | b | D_b | `b_floor` | p_F1 | p_F2 | Sonuç commit'i | Sınıf |
|---|---|---|---|---|---|---|---|---|---|
| CITAS | 2026-08-18 | 5 | 6 | 2026-08-25 | 0 | 0.1383 | 0.0946 | `f1f9d44` | RETRO |
| TKNKA | 2026-08-20 | 7 | 8 | 2026-08-31 | 0 | 0.1382 | 0.0952 | `f1f9d44` | RETRO |
| VEYAS | 2026-08-20 | 0 | 1 | 2026-08-20 | 0 | 0.1376 | 0.0972 | `f1f9d44` | RETRO |
| KPEKS | 2026-08-21 | 5 | 6 | 2026-08-28 | 1 | 0.5389 | 0.1640 | `f1f9d44` | RETRO |
| INTET | 2026-09-01 | 4 | 5 | 2026-09-07 | 0 | 0.1418 | 0.0829 | `f1f9d44` | RETRO |
| BKRGY | 2026-09-02 | 0 | 1 | 2026-09-02 | 1 | 0.5433 | 0.1523 | `f1f9d44` | RETRO |
| NETGL | 2026-09-17 | 3 | 4 | 2026-09-22 | 1 | 0.4991 | 0.3043 | `c1eb7ae` | RETRO |

Bütün satırlarda `@ZERO` F1/F2 = 0.3049 / 0.1410, `inputs_pit_ok = true`, bekçi temiz, ürün `NOT_AVAILABLE`'dır. Yalnız NETGL `FON_KRIZI_2026` etiketi ve kırpma uyarısı taşır.

**DAG kanıtı.** Sıralama `GITLOG.txt`'ten ve skor dosyasındaki `class_evidence` alanından okunur:

| Commit | Zaman (+03:00) | Ne |
|---|---|---|
| `f1f9d44` | 2026-09-22 18:20 | ilk resmi sonuç commit'i: 6 arzın D_b sonrası bültenleri ve sonuçları (MANIFEST'e göre o gün 2026-08-06…2026-09-21 tarihli 59 bülten indirildi) |
| `c1eb7ae` | 2026-09-30 23:09 | NETGL D4–D10 bültenleri ve sonuçları (D_b = 2026-09-22'den sonraki ilk bülten) |
| `4d3c9a2` | 2026-10-02 16:21 | `break_floor_v0` ve `@ZERO` donduruldu; push kanıtı 2026-10-02T14:45:08Z |

Geçmiş doğrusaldır: `4d3c9a2` her iki sonuç commit'inin **torunudur**, atası değil. `model_prospective_break` bu yüzden yedi arzda da false'tur ve neden kodu `MODEL_FROZEN_AFTER_BREAK_OUTCOME`'dur. Kısacası, model kırılma akşamlarının hepsinden sonra yapıldı; bu sıralama en baştan belliydi (şartname §9.3: "bugünkü 7 arz → RETRO"). Bundan sonra listelenen ve kırılma akşamı `4d3c9a2`'den sonra gelen her arz, girdileri PIT ise kendiliğinden MACHINE_SEQUENCED olur.

**Bilgi: yedi akşamda ne oldu?** RETRO satırları `scores_break.json`'da gerçekleşen değer taşımaz. Aşağıdaki tablo benim türetmemdir ve hiçbir skora girmez. Resmi etiket THM alt limitinden gelir; burada THM yerine Lo(close_b) kullandım (H99'da bu ikisi 85/85 eşittir). n < 10 olduğu için ortalama ya da hüküm yazmıyorum; projenin dil kuralı da bunu yasaklar.

| Arz | `b_floor` | p_F1 | Lo(close_b) | close(D_{b+1}) | y_F1 (türetme) | y_F2 (türetme) |
|---|---|---|---|---|---|---|
| BKRGY | 1 | 0.543 | 10.48 | 10.48 | 1 | 0 |
| KPEKS | 1 | 0.539 | 122.50 | 122.5 | 1 | 1 |
| NETGL | 1 | 0.499 | 27.52 | 27.52 | 1 | 1 |
| CITAS | 0 | 0.138 | 100.80 | 117.6 | 0 | 0 |
| INTET | 0 | 0.142 | 67.10 | 68.2 | 0 | 0 |
| TKNKA | 0 | 0.138 | 141.40 | 172.8 | 0 | 0 |
| VEYAS | 0 | 0.138 | 122.40 | 135.9 | 0 | 0 |

Tabanda bozulan üç arzın üçünde ertesi gün de taban geldi; taban üstünde bozulan dördünde gelmedi. Bu, bir doğruluk iddiası değildir: model bu arzlardan sonra donduruldu ve yedi gözlem hiçbir şey kanıtlamaz.

Kaynak dosyalar: `docs/specs_faz8/SPEC_BREAK_V0.md` §9; `CLAUDE.md` kural 1; `docs/faz8/POST_BREAK_AKISI.md`, `docs/faz8/LIVE_RAPOR.md`; `docs/SCORES_BREAK.md`; `scores/scores_break.json` (`retro_info[].class_evidence`); `registry/post_break/*/machine_*.json`; `borsai/scoring.py` (`outcome_ingest_commit_after`, `model_prospective_break`, `ensure_post_break_records`, `main_break`); `borsai/freeze.py` (`build_post_break_machine_record`, `write_post_break_machine_record`); `borsai/registry.py` (`post_break_record_problems`); `docs/SPEC_DEVIATIONS.md` N26–N33; `GITLOG.txt`; `registry/push_proofs/4d3c9a26….json`.

## 5.6 Bağımsız denetimler: Fable ne buldu?

İki modelin dondurma yolunda da bağımsız bir yeniden üretim vardı. İkisi de "beklentiden çok iyi" eşiğini aştığı için şartname bu üretimi bir şarta bağladı: ledger'lar |Δ| ≤ 1e-9 ile eşleşmeden dondurma yok. İşi Fable yaptı: şartnameyi yazan, ama uygulamayı görmeden çalışan ayrı bir oturum. Fable her iki denetimde de `borsai` paketini **hiç import etmeyen** kendi betiğini yazdı. Betiğin `borsai` yüklemediği, `sys.modules` denetimiyle kanıtlandı.

### 5.6.1 Faz 5 denetimi: `post_d1_hazard_v0` → FREEZE_OK

**Yeniden üretim.** 87 fold'un durumu 87/87, seçilen λ 70/70 birebir tuttu. Bütün sayısal sütunlarda en büyük fark 1.5e-11'dir (en kötü sütun S_10). Nihai fit λ = 30 birebir; δ farkı 1.1e-16. §4'ün 28 hücresi basılı hassasiyette ve §5'in 18 etiketi birebir aynı. Fable bu sayıları kendi bağımsız float64 yoluyla üretti; Opus'un yolu kesin `Fraction`/`Decimal` kullanır. 1e-11 düzeyindeki fark bu iki yolun farkıdır.

**Bir "uyuşmazlık" ve nedeni.** MODELS.md iki fold'u "eşitlik" sayar (AGROT, MEGMT; λ = INF, model ≡ karşılaştırıcı). Fable'ın sayımında bunlar kazanç/kayıp çıktı. Neden: eşitlik "fark bit-eşit 0" demektir. Bu ancak aynı kod yolunda olur; bağımsız bir yeniden fit son bitte 1e-16 kadar farklıdır. Hüküm etkilenmez (K8; errata H26).

**Sızıntı yok.** Çalışma zamanı izi: D1 yükleyicisi 2..10. seanslarda yalnız {ticker, session_number, target_session_date} okur. `data/outcomes`, `data/raw/bist`, `scores` hiç açılmadı. Test arzının D1 alanı hiçbir fold'da ön işlemeye girmez. Her fold'da eğitim seansları kesimden önce biter.

**Mutasyon denetimi.** Mutasyon denetiminde koda bilerek küçük bir hata konur ve testlerin bunu yakalayıp yakalamadığına bakılır. Faz 5'te 18 mutasyon koşusunun 17'si kırmızı oldu (denetimin özeti bunları 12 mutasyon grubu olarak sayar: 12'nin 11'i; §6.15.5 ve §6.16 bu sayımı kullanır). Kırmızı olmayan tek mutasyon önemli bir bulguya dönüştü:

| # | Önem | Bulgu | Sonuç |
|---|---|---|---|
| K3 | önemli | `d1_lock`'ta Decimal yerine float eşitliği koyunca hiçbir test kırmızı olmadı ("eşdeğer mutant"). | `test_2`'ye "10.12" / "10.1200000000000000001" → 0 ve "10.12" / "10.120" → 1 çifti eklendi. |
| K4 | küçük | Bazı beklenti sabitleri yalnız MODELS.md bayt eşitliğiyle korunuyordu. | `test_15`'e sabitler eklendi. |
| K1, K2 | küçük | Ret kodlarının adı (öneksiz) ve şartnamede olmayan `D1_FIELD_INVALID`. | Errata H23, H24. |
| K6 | küçük | Şartnamenin sözde kodu `logit(hazard)` diyor; bit-eşitlik şartıyla çelişir. | Errata H25; kod zaten doğrudur. |
| K7 | küçük | "Model dosyaları sonuç commit'lerinin atası olmalı" kararının lafzı ilk dondurmada bekçiyi kırmızı yapardı. | CLAUDE.md kural 1'e POST_D1 cümlesi bu okumayla yazıldı. |
| K9 | bilgi | `path_conditional` hücreleri 2..10. seans kapanışlarını (kesimli) okur. | Errata H27; birincil çıktı etkilenmez. |

**Tanı: neden "bu kadar iyi"?** Fable dört şey buldu:

1. **Brier k = 2 kazancının tamamı kilitsiz arzlardandır.** 70 arzın 11'i kilitsizdir; farkın %100.8'i bunlardan gelir. Gözlenen D2 kırılma oranı kilitlilerde 0.034, kilitsizlerde **0.818**'dir. Model kilitsizlere ortalama 0.556 verir, karşılaştırıcı 0.154.
2. **Kazanç ayırt etmedendir, kalibrasyondan değil.** Murphy ayrıştırmasında model çözünürlüğü 0.094, karşılaştırıcınınki 0.013'tür. Kazancın ≈ %92'si ayırt etme payıdır. Etki tek bir yıla bağlı değildir.
3. **k = 10'daki hafif kötüleşme bir tasarım sonucudur.** δ bütün günlerde ortak olduğu için, D2–D3'te doğru olan "kilit = düşük risk" kayması D4–D10'a da taşınır. Gün grubu etkileşimi bunu giderirdi; ama bu yeni bir model_id'dir.
4. **Beklenti neden düşük kaldı?** Şartname sınıf hazard'larını kilitli 0.06–0.10, kilitsiz 0.36–0.62 varsaymıştı. Gerçekte 0.034 ve 0.818 çıktı. Fable'ın genel dersi: H99'da tavan mekaniği "ılımlı etki" varsayımlarından çok daha belirleyicidir. Sonuç görülmeden yazılan beklentiler etkinin gücünü sistematik olarak küçümsüyor. Aynı zamanda tasarım H99'a maruzdur; asıl kanıt prospektiftir.

Duyarlılık: yalnız `d1_lock` ile Brier k = 2 kazancı daha da büyüktür (−0.0561), ama k = 10 bozulması da büyür (+0.0171, aralık 0'ı pozitif dışlar). Yalnız `d1_turnover` k = 2 kazancının yarısını verir ve k = 10'u bozmaz.

Kaynak dosyalar: `docs/fable_faz5_audit/AUDIT.md` §0–§5 ve `ekler/`; `docs/MODELS.md` Faz 5 "Dondurma"; `docs/SPEC_DEVIATIONS.md` H23–H27.

### 5.6.2 Faz 8 denetimi: `break_floor_v0` → REPRO_OK

**Bit-eşit yeniden üretim.** Resmi ledger (82 satır × 47 sütun), üç duyarlılık ledger'ı ve iki nihai fit önizlemesi sıfırdan yeniden üretildi. 29 sayısal sütunda ve iç tablolarda en büyük fark **0.000e+00**'dır. Durumlar, seçilen C'ler, kimlik sha'ları ve Faz 4 hücre paritesi (87/87) birebir. Bit-eşitliğin nedeni ortak ortamdır (aynı scikit-learn 1.9.0 ve numpy 2.5.2, aynı satır sırası, aynı kesin ön işleme). Fable bunun bir "kopya" olmadığını göstermek için kendi Newton çözücüsünü de koştu: sklearn ile farkı p'de en çok 6.3e-9'dur.

**İlk koşudaki dört "uyuşmazlık".** Dördü de Fable'ın kendi tarafındaydı: bir sütunun iki başlıktan maksimum alınması, b = 9'da F2 eğitim kümesinin kurulmaması, yakınsamayan C = 10 adayının `null` skoru ve bir JSON biçim varsayımı. Opus'un kodunda ve şartnamede hata bulunmadı.

**N20 sağlamlığı (ürün eşiği).** Birincil farkın büyüklüğünün bir kısmının eşik yuvarlamasından gelip gelmediği ölçüldü:

| Ürün eşiği tanımı | Ürün Brier | Model − ürün | %95 aralık | Ürün ort.: taban / taban üstü |
|---|---|---|---|---|
| Kesin eşik (resmi) | 0.3781 | −0.1904 | [−0.2520, −0.1247] | 0.115 / 0.568 |
| Yarım adım tolerans | 0.3576 | −0.1698 | [−0.2281, −0.1086] | 0.172 / 0.568 |
| Bir adım tolerans | 0.3489 | −0.1611 | [−0.2193, −0.1013] | 0.199 / 0.569 |
| %1 göreli tolerans | 0.3426 | −0.1549 | [−0.2284, −0.0810] | 0.313 / 0.604 |
| Yuvarlamasız 0.9 | 0.3930 | −0.2052 | [−0.2665, −0.1375] | 0.053 / 0.566 |

Hüküm: "aralık 0'ın altında" beş tanımda da sağlamdır. Farkın ≈ 0.03–0.04'ü eşik yuvarlamasındandır. Asıl büyüklük, ürünün taban üstü kırılmalara her tanımda ≈ 0.57–0.60 vermesinden gelir (gözlenen 0.122). Fable'ın özeti: birincil hücre "model çok iyi" değil, "ürünün türetilmiş cevabı bu soruda zayıf" demektir. Modelin gerçek kanıtı `@ZERO` (−0.028, 0'ı dışlar) ve `base_floor_by_type` (+0.011, 0'ı içerir) hücreleridir. Yani lojistik, iki hücreli oran tablosuna bir şey eklemiyor; kazanç `b_floor` sınıf ayrımındadır.

Fable, DURKN, SERNT ve ATATR örneklerinde mekanizmayı atom atom gösterdi. Örneğin DURKN'da kesin eşik altında 0 atom vardır. Bir adım tolerans verilince altı atom eşiğin içine girer ve ürün 0'dan 0.20'ye çıkar. Bu altı atomun hepsi kaynağında gerçek bir çift tabandır; ama eşiğin 0.0005–0.0084 TL (bir adımdan az) üstünde kalmıştır.

**Sızıntı ve sıra.** Test arzının alanları üç fold'da bilerek değiştirildi; o fold'un fit'i, ön işlemesi, `@ZERO`'su ve ürünü bit-eşit kaldı, yalnız p değişti. 6 243 eğitim satırının hepsinde etiket seansı kesimden öncedir. Hücrelerin en son gözlemi her fold'da test arzının D1'inden öncedir. Koşu boyunca `data/outcomes`, `scores`, `registry`, `models` dosyası açılmadı. Şartname `7d78d43`'ten beri bayt-eşittir; değerlendirme kuralları sonuçtan önce (commit A) sabitlenmiş ve sonra değişmemiştir.

**"Aynı gün" kuralı (N2).** H99'da aynı gün listelenip etiketi kesimden önce olan tek çift KBORU ← SURGY'dir. O fold zaten yetersiz eğitimlidir. Kararın skorlara etkisi sıfırdır.

**Mutasyonlar.** 13 mutasyonun 13'ü kırmızı oldu. Örnekler: `b_floor`'u float eşitliğiyle hesaplamak; etiketi "en düşük == alt limit" yapmak; kesimi `<=` yapmak; ürün hücrelerini D1 yerine T'de kesmek; yapısal sıfırda 10 − b yerine 9 − b kullanmak; yakın dönem sınırını kaydırmak; `@ZERO`'ya test satırını katmak; "çok iyi" eşiğini değiştirmek.

**Kart için önerilen uyarılar** (MODELS.md'ye "bilgi" olarak girdi):

1. Birincil farkın büyüklüğü karşılaştırıcının zayıflığındandır; tek orana karşı kazanç küçüktür: −0.028 [−0.045, −0.007].
2. β_turn işareti beklentinin tersidir (+0.063); el değiştirme bilgi eklemiyor.
3. F2 − `@ZERO` ≈ 0: iki ardışık taban için model tek orandan ayırt edilemiyor.
4. Kalibrasyon sınıfa göre bozuk: taban üstünde model yüksek (+0.129), tabanda düşük (−0.086); 2025 kohortunda +0.204.
5. Rejim `FON_KRIZI_2026`: önceden yazılmış okuma "model tabanı az tahmin eder".
6. `BAND_RULE_MISMATCH` olunca yastık rozeti gizlenir.
7. Eski dönem terazisi yok; F2 n'i 52, beklentinin (55) altında.

Kaynak dosyalar: `docs/fable_faz8_audit/AUDIT.md` §0–§8 ve `ekler/`; `docs/MODELS.md` Faz 8 "Dondurma"; `docs/SPEC_DEVIATIONS.md` N24.

## 5.7 Özet: akılda kalacaklar

1. **İki model, iki akşam.** `post_d1_hazard_v0` D1 tavan kapanınca serinin sürüp sürmeyeceğini, `break_floor_v0` seri bozulunca ertesi gün(ler)in taban olup olmayacağını tahmin eder. Biri D1 tavan değilse kapsam dışıdır, öteki tam o akşam kapsamdadır.
2. **D1 sonrası modelin özü ofsettir.** Listeleme öncesi modelin doğrusal öngörücüsü değişmez; yalnız iki D1 özelliğinin katkısı (δ_lock = −0.328, δ_turn = +0.251, λ = 30) eklenir. λ = ∞'da model karşılaştırıcının kendisidir.
3. **D1 sonrası backtest: "yarın"da güçlü, bütün eğride ayırt edilemiyor.** Brier k = 2 −0.0512 [−0.1010, −0.0097]; birincil RPS_1 −0.0105 [−0.0264, +0.0058]. Kazancın kaynağı kilitsiz D1'lerdir.
4. **Kırılma modelinin özü taban kapanışıdır.** F1: α = −1.001, β_floor = +0.987, β_turn = +0.063 (z ölçeğinde), C = 1. El değiştirme neredeyse hiçbir şey katmaz.
5. **Kırılma backtest'i: ürüne karşı büyük, tek orana karşı küçük kazanç.** F1 − ürün −0.1904 [−0.2520, −0.1247], F1 − `@ZERO` −0.0281 [−0.0453, −0.0074], n = 69, 21 ay. Büyük fark, ürünün taban üstü kırılmalara ≈ 0.57 demesinden gelir.
6. **İkisi de tasarıma maruzdur.** H99 sonuçları yalnız ön elemedir; kart "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0" der. Asıl sınav canlıdır (kırılma modelinde n ≥ 30).
7. **D10 için model yok, aritmetik var.** min10 = Lo^(10−b)(close_b) > P ise D10 ≤ arz imkânsızdır (TKNKA). NETGL'de 10. günün en düşük mümkün kapanışı (16.29) birebir gerçekleşti.
8. **Makine sırası akşam yükünü sıfırlar.** Kırılma tahmini skorlama anında, yalnız pinli resmi dosyalardan üretilir. Prospektiflik git DAG'ından okunur. Kayıt türü MACHINE_SEQUENCED olabilir, ama satırın sınıfı ayrıca hesaplanır.
9. **Bugün iki modelin de canlı n'i sıfırdır.** D1 sonrası model (`7c18c0f`) yedi arzın D2+ sonuçlarını getiren `f1f9d44`'ten sonra; kırılma modeli (`4d3c9a2`) kırılma sonrası sonuçları getiren `f1f9d44` ve `c1eb7ae`'den sonra donduruldu. Yedi arzın hepsi iki model için de RETRO'dur. Repoya göre (son commit 2026-10-06) dondurmalardan beri yeni halka arz listelenmedi.
10. **Bağımsız denetimler** iki modeli de onayladı (FREEZE_OK, REPRO_OK). Denetimler sızıntı bulmadı. Bulunanlar test sertleştirmesi (Decimal eşitliği), şartname erratası ve yorum notlarıdır.

**Açık konular** (repoda karar bekleyen ya da sonraya bırakılanlar):

- f3'süz arzlar için PB tabanlı bir D1 sonrası varyant (`pb_post_d1_hazard_v0`) ayrı model_id olarak önerildi; henüz yok.
- D2 ve sonrası için POST_Dj güncellemeleri, canlı n ≥ 10 olmadan açılmayacak.
- D1 sonrası modelde gün grubu etkileşimi (k = 10 sorunu) ve kırılma modelinde el değiştirmesiz bir v1 tartışılabilir; ikisi de yeni model_id'dir.
- Kırılma akşamı için isteğe bağlı insan kaydı (LIVE yolu) formülde hazırdır; v0'da üreticisi yoktur.
- `FON_KRIZI_2026` uyarısının bitiş tarihi ve ±%10 bandın bütün pazarlara uygulandığını gösteren duyuruların doğrulanması açıktır.

Kaynak dosyalar: bu bölümün bütün kaynakları; özellikle `docs/MODELS.md` (Faz 5, Faz 8), `scores/scores_post_d1.json`, `scores/scores_break.json`, `models/post_d1_hazard_v0.json`, `models/break_floor_v0.json`, `models/break_floor_v0@ZERO.json`, `docs/specs_faz5/SPEC_POST_D1_V0.md` §13, `docs/specs_faz8/SPEC_BREAK_V0.md` §14, `docs/specs_faz8/KARARLAR.md` §C.

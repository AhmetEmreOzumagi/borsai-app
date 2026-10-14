# 1. Genel bakış: BorsAi bir bakışta

Bu bölüm kitabın kapısıdır. Önce BorsAi'nin ne olduğunu ve hangi soruları cevapladığını, sonra neden her şeyin "dürüst ölçüm" etrafında kurulduğunu anlatır. Ardından bir halka arzın verisinin resmî kaynaktan uygulama ekranına kadar izlediği yolu tek şemada gösterir ve bu yolu gerçek bir arz, NETGL, üzerinden baştan sona yürür. Bölüm, projenin kilit sayılarını tek tabloda toplayıp kitabın geri kalanının nasıl okunacağını söyleyerek biter.

Buradaki her sayı ya sonraki bölümlerden alındı ya da bu bölüm yazılırken repodaki dosyadan yeniden ölçüldü. Kaynak her alt bölümün sonunda yazılıdır. Ayrıntıyı tekrar etmek yerine hep ilgili bölüme yönlendiriyorum.

## 1.1 BorsAi nedir?

`CLAUDE.md`'nin ilk satırı projeyi tek cümleyle tanımlar: "Borsa İstanbul halka arzları için doğruluğu ölçülmüş tahmin modelleri ve onları gömülü çalıştıran bir masaüstü uygulaması." Cümlenin iki yarısı projenin iki büyük parçasıdır:

1. **Modeller ve ölçüm.** `borsai/` adlı Python paketi resmî veriyi okur, modelleri eğitir, dondurur, tahmin kaydı yazar ve tahminleri gerçekleşen sonuçlarla skorlar.
2. **Masaüstü uygulaması.** `app/` altındaki Tauri uygulaması aynı modelleri Rust'a taşınmış hâliyle, internete çıkmadan, yerel olarak çalıştırır. Tauri, arayüzü işletim sisteminin tarayıcı motorunda çizen ve arkasına Rust ile yazılmış bir program bağlayan bir masaüstü çatısıdır (Bölüm 7).

Cümledeki kilit sözcük "doğruluğu ölçülmüş"tür. Bir modelin iyi olduğu, tahminleri sonuç bilinmeden önce kaydedilip sonra gerçekleşenle karşılaştırılmadan söylenmez. Projenin kuralları, testleri ve iş akışı bu tek ilkeyi korumak için vardır (§1.3).

Proje bir kişinindir: bilgisayar mühendisliği 3. sınıf öğrencisi olan proje sahibi. İşi ise ayrı "eller" yapar. Bir claude.ai sohbeti orkestratördür: planı yönetir, görev dosyalarını yazar, raporları dosyalardan doğrular. Claude Code oturumları işi yapar: Opus kodu ve modelleri yazar, Sonnet mekanik ölçüm işlerini yapar, Fable şartname yazar ve bağımsız denetim yapar. Codex web'den veri toplar ama repoya yazmaz. `git push` yalnız proje sahibinin elindedir. Bu düzen ve gerekçesi §2.4'te anlatılıyor.

Repo kökünde şu klasörler vardır:

| Klasör | Ne içerir | Ayrıntı |
|---|---|---|
| `borsai/` | Python paketi: veri yükleme, özellikler, model eğitimi ve tahmini, backtest, kayıt, sonuç indirme, skorlama (39 dosya) | Bölüm 3–6 |
| `data/` | Resmî ham dosyalar (`data/raw/`), eğitim tabloları, canlı ve eski kohort sonuç dosyaları | Bölüm 3 |
| `models/` | Dondurulmuş model parametreleri (JSON) ve üç model dizini (`INDEX*.json`) | §4.1.3, §6.11.1 |
| `registry/` | Sicil: payda, girdi belgeleri, kaynak belgeler, tahmin kayıtları, makine kayıtları, push kanıtları, eski kohort | §3.9, §6.11 |
| `scores/` | Skor dosyaları: `scores.json`, `scores_post_d1.json`, `scores_break.json`, `scores_oot.json` | Bölüm 6 |
| `experiments/` | Deney günlüğü `log.jsonl` | §6.13 |
| `docs/` | Şartnameler, görev dosyaları (`docs/prompts/`), raporlar, denetimler, sapmalar defteri | Bölüm 2, 6 |
| `tests/` | pytest testleri ve bekçiler, altın referans dosyaları | §6.15 |
| `app/` | Masaüstü uygulaması: Rust arka uç, model portu, TypeScript arayüz, parite düzeneği | Bölüm 7–8 |
| `legacy/` | Eski repodan birebir kopya kod; değiştirilmez, port için referanstır | §2.2 |

Kaynak dosyalar: `CLAUDE.md`, repo kök dizini, `claude/HANDOFF.md` §3 (proje bilgi alanı).

### 1.1.1 Başlangıç sözlüğü

Kitap boyunca geçen temel terimler şunlardır. Daha uzun bir sözlük §2.0'dadır.

| Terim | Anlamı |
|---|---|
| Arz (halka arz) | Bir şirketin paylarının ilk kez borsada satışa sunulması. Kod adıyla anılır (ör. NETGL). |
| T, D1, D_h | T ilk işlem günüdür; D1 normalde aynı gündür. D_h, payın işlem gördüğü h'inci resmî seanstır (§3.4.6). |
| Tavan, taban | O günün üst ve alt fiyat limiti. Bant ±%10'dur. Kapanış üst limite tam eşitse gün "tavan"dır. |
| Seri uzunluğu L | D1'den başlayarak art arda kaç gün tavan kapanışı olduğu (0–10). |
| Kırılma günü b | Serinin bozulduğu gün, b = L + 1. "Kırılma akşamı" bu günün bülteninin çıktığı akşamdır. |
| THB, THM | Borsa İstanbul'un günlük resmî bültenleri. THB kapanış fiyatını ve işlem sayılarını, THM referans fiyatı ve limitleri verir. Sonuç verisi yalnız bunlardan gelir. |
| Talep katı (f3) | Talep toplamada arzın kaç kat talep gördüğü. Modellerin en güçlü girdisidir. |
| H99 | Eğitim kohortu: ilk işlem günü 2023-09-22 ile 2026-08-06 arasındaki 99 arz. |
| Dondurma | Modelin parametrelerinin JSON'a yazılıp commit ve push edilmesi. Donmuş model bir daha değişmez. |
| Kayıt | Bir arz için kayıtlı bütün modellerin tahminlerini, girdileri ve parametre özetleriyle (sha256) birlikte saklayan dosya. |
| Push kanıtı | Bir commit'in GitHub'da bulunduğunu GitHub sunucusunun saatiyle gösteren dosya. Yerel saat kanıt sayılmaz. |
| Sınıf | Bir arzın bir model için canlı sicildeki yeri: LIVE (kanıtlı canlı), LATE_RECORD (geç kayıt), RETRO (model sonuçtan sonra dondu; yalnız bilgi), MACHINE_SEQUENCED (makine kaydı; ayrı ölçek). |
| Terazi | Doğruluğun ölçüldüğü ayrı küme: backtest, canlı sicil, zaman-dışı eski kohort. Teraziler asla toplanmaz. |
| Basit kural | Modelin yenmesi gereken karşılaştırıcı: "her zaman tavan", eğitim medyanı, taban oranı, Kaplan–Meier (KM) tablosu gibi. |
| Birincil hücre | Bir model için sonuç görülmeden ilan edilmiş tek karşılaştırma (metrik + ufuk + karşılaştırıcı). Hüküm ona göre verilir. |
| "Geçiyor" | Model ile kural arasındaki farkın %95 aralığı tamamen modelin lehine. Aralık 0'ı içeriyorsa "ayırt edilemiyor". |
| Tasarıma maruz | Modelin tasarlandığı veride yapılmış ölçüm. Kanıt değil, ön elemedir. |

## 1.2 Hangi soruları cevaplıyor?

Bir halka arzın hayatında üç an vardır ve BorsAi her an için ayrı bir soru sorar. Her anın kendi model dizini, kendi kayıt türü ve kendi skor dosyası vardır.

| An | Soru | Bugünkü ana model | Kayıt kimin elinden, ne zaman | Ayrıntı |
|---|---|---|---|---|
| Listeleme öncesi | Kaç gün tavan yapar? Getirisi ne olur, arz fiyatının üstünde kalır mı? | `ceiling_hazard_v0` (tavan serisi), `v1_5_h99` (V1.5, getiri) | İnsan; ilk işlem gününden önce push edilir | Bölüm 4 |
| D1 akşamı | İlk gün tavan kapandı; yarın tavan bozulur mu? | `post_d1_hazard_v0` | İnsan; ikinci seansın 09:40'ından önce push edilir | §5.2 |
| Kırılma akşamı | Seri bozuldu; yarın da taban mı? | `break_floor_v0` | Makine; skorlama anında, insan değer girmez | §5.3–§5.5 |

Listeleme öncesi an kendi içinde ikiye ayrılır. **Talep toplama öncesi** (PB, "pre-bookbuilding") yalnız SPK bülteninde onaylanan planlanan yapı bilinir; talep katı henüz yoktur. Bu anın modelleri `pb_*` ailesidir (§4.5). **Talep toplama sonrası** ise talep katı (f3) açıklanmıştır ve asıl modeller çalışır.

Bu ana soruların yanında yardımcı çıktılar da vardır:

- **Tavan yolu** (`ceiling_path_v0`): seri olasılıklarını ±%10 bandın deterministik fiyat yoluyla birleştirip D_h getirisinin bütün dağılımını verir (§4.6).
- **Düşen arz** (`fall_d10_v0_*`): "D10'da arz fiyatının altında kapanır mı?" Kasa testinde öne çıkma kuralını geçemedi; bugün arşivdedir, yani listede kalır ama öne çıkmaz (§4.8).
- **Seri hesaplayıcı**: "Seri j gün sürdüyse yarın da tavan mı?" Yeni model gerektirmez; dondurulmuş eğriden P(L ≥ j+1 | L ≥ j) = S_{j+1}/S_j hesaplanır (§4.4.1, §8.16). Gün gün güncellenen ayrı bir model için şartname görevi bekliyor (§2.7.6).

Toplam 30 model donmuştur: listeleme öncesi dizinde 27, D1 sonrası dizinde 1, kırılma dizininde 2. Bunların 14'ü özellik kullanmaz: 8 basit kural ve bir modelin "özellik yok" ucu olan 6 satır (`@INF`, `@ZERO`). Neden bu kadar çok model olduğu §4.1.4'te anlatılıyor.

Uygulamanın sade görünümünde bir çıktı ancak önceden ilan edilmiş birincil hücresinin hükmü skor dosyasında "geçiyor" ise altın renkle öne çıkar. Bugünkü dosyalarla öne çıkanlar: `ceiling_hazard_v0`'ın tavan serisi eğrisi ve V1.5'in D5 getirisi. `break_floor_v0`'ın "yarın da taban" olasılığı (F1) "ön eleme" etiketiyle öne çıkar. `post_d1_hazard_v0` ve V1.5'in öbür çıktıları "≈" işaretiyle, vurgusuz durur (§8.11).

Kaynak dosyalar: `models/INDEX.json`, `models/INDEX_POST_D1.json`, `models/INDEX_POST_BREAK.json`, `docs/specs*/`, `app/src-tauri/src/commands/sade.rs` (`HEADLINE_OUTPUTS`).

## 1.3 Neden "dürüst ölçüm" merkezde?

Halka arz tahmini küçük veriyle yapılır. Eğitim kohortu 99 arzdır; olasılık modellerinde azınlık olayı bazen 10 tanedir. Küçük veride dört tuzak vardır (§6.1):

1. **Sızıntı.** Tahmin anında bilinemeyecek bir bilgi eğitime karışır; backtest olağanüstü çıkar, gerçek hayatta model çöker.
2. **Sonradan bilgelik.** Sonucu gördükten sonra modeli ya da eşiği değiştirip "zaten böyle düşünmüştük" demek.
3. **Çoklu karşılaştırma.** Onlarca hücreye bakılırsa bazıları şans eseri "geçiyor" çıkar.
4. **Küçük n yanılgısı.** Altı arzda kurala 5–1 üstün gelmek bir şey kanıtlamaz.

Üstelik H99'un sonuçları biliniyordu. Gün grupları, özellikler ve ızgaralar bu sonuçlar görülerek seçildi. Bu yüzden H99 üzerindeki her backtest **tasarıma maruzdur**: bir ön elemedir, kanıt değildir.

BorsAi'nin cevabı, bu tuzakları iyi niyete bırakmayıp kodla ve testle zorlamaktır. `CLAUDE.md` kurallarını kendisi "dürüst doğruluk için en az set; kodla zorlanır" diye tanıtır. Altı kural kısaca şudur (ayrıntı §6.2):

1. **Dondurma.** Resmî tahmin kaydı kayıtlı bütün modellerin çıktısını taşır ve ilk işlem gününden önce push edilir. Zaman kanıtı push'tur. Kayıt silinmez; hatalıysa iptal kaydı düşülür.
2. **Payda.** Kapsam başlangıcından sonra işlem gören her arz sicile girer; dondurulmadıysa nedeniyle "atlandı" satırı olur.
3. **Üç terazi.** Backtest, canlı sicil ve zaman-dışı eski kohort ayrı ölçülür, asla toplanmaz. Sınıf tarihlerden ve git geçmişinden hesaplanır; elle etiketlenmez.
4. **Deney günlüğü.** Her backtest koşusu kendiliğinden günlüğe yazılır; kaç şey denendiği görünür.
5. **Değişiklik = yeni model_id.** Model sessizce düzeltilmez; yanına yeni kimlik açılır, eskisi ve skorları listede kalır.
6. **Skorlama.** Sonuç yalnız resmî bültenlerden gelir; her model aynı arzlarda basit kurallarla eşleşik skorlanır; "geçiyor" ancak %95 aralığı 0'ı dışlarsa denir.

Kuralların yanında iki alışkanlık vardır. Birincisi **yazan el ile denetleyen elin ayrılmasıdır**: şartnameyi Fable yazar, kodu Opus yazar, sonucu Fable `borsai` paketini import etmeden sıfırdan yeniden üretir (§2.4.6). İkincisi **"ölçmeden aktarma yok"** ilkesidir: hiçbir sayı eski bir rapordan ya da hafızadan ölçülmeden alınmaz. Neden gerekli olduğunu küçük bir olay gösterir: 2 Ekim tarihli bir proje özeti V1.5'in D10 "arz üstü" olasılığını taban orana karşı "geçiyor" diye yazmıştı. `scores/scores.json`'daki hüküm ise "ayırt edilemiyor"dur: −0.0391 [−0.0756, +0.0023], n = 81 (§2.6.10).

Bu düzenin bugünkü dürüst sonucu da açıkça söylenmelidir:

- **Backtest'te** "kaç gün tavan", "D5 getiri" ve "yarın da taban mı" soruları basit kuralları geçiyor (§4.9, §5.3.9).
- **Zaman-dışı terazide** tavan modeli `ceiling_hazard_v0`, 2020–2023 arzlarında KM kuralını geçemiyor: açık kümede +0.069 [+0.001, +0.131] (§6.12.7).
- **Canlıda** kanıtlı ölçüm henüz yok. Sicildeki tek LIVE hücre, eski repodan gelen NETGL × V1.5 kaydıdır. Hüküm için en az 30 canlı arz gerekir (§6.8).

Proje sahibinin sözüyle: "Coin-flip model istemiyorum." Doğruluğu kanıtlanmamış model ana ekrana girmez; silinmez de, listede kalır.

Kaynak dosyalar: `CLAUDE.md`, `docs/specs/SPEC_SCORING.md`, `scores/scores.json`, `scores/scores_oot.json`, `claude/HANDOFF.md` §8.4 (proje bilgi alanı).

## 1.4 Uçtan uca boru hattı

Bir arzın verisi resmî kaynaktan uygulama ekranına kadar aşağıdaki yolu izler. Şemadaki her kutunun ayrıntısı parantezdeki bölümdedir.

```
Resmî kaynaklar (§3.2)
  KAP · SPK bülteni · BIST THB/THM · TÜİK TÜFE · BIST XU100
        │
        ▼
Veri katmanı (Bölüm 3)
  eğitim: data/training_table.csv (H99, 99 arz)
          data/training_table_v2.csv (170 arz)
  girdi:  registry/inputs/<T>.json (20 alan + kaynak + sha256)
        │
        ▼
Modeller (Bölüm 4–5, §2.4.3)
  şartname (Fable) → kod + backtest (Opus)
  → bağımsız yeniden üretim (Fable)
  → dondurma: models/<id>.json + models/INDEX*.json
        │
        ▼
Kayıt ve push kanıtı (§6.3, §6.11)   [ilk işlem gününden önce]
  python -m borsai.freeze      → registry/records/<T>/
  git push + borsai.push_proof → registry/push_proofs/<sha>.json
        │
        ▼
Sonuçların gelmesi (§3.10, §6.11.6)
  python -m borsai.outcomes update
    → data/raw/bist/ , data/outcomes/<T>.csv
  ├─ D1 akşamı: POST_D1 kaydı, insan, 2. seans 09:40'tan önce (§5.2)
  └─ kırılma akşamı: makine kaydı → registry/post_break/ (§5.5)
        │
        ▼
Skorlama (Bölüm 6)
  python -m borsai.scoring → scores/*.json
  üç terazi: backtest │ canlı │ zaman-dışı   (asla toplanmaz)
        │
        ▼
Uygulama (Bölüm 7–8)
  Rust: gömülü 27 + 1 model, Python'la parite
  TypeScript arayüz: sade ve ayrıntılı görünüm
```

Adımların kısa anlatımı:

| # | Adım | Ne olur | Ana dosyalar | Ayrıntı |
|---|---|---|---|---|
| 1 | Resmî kaynaklar | Bültenler, KAP ve SPK belgeleri, TÜFE ve XU100 indirilir; ham baytlar değiştirilmez, sha256 ile kilitlenir. | `data/raw/`, `registry/source_docs/` | §3.1–§3.2 |
| 2 | Girdi belgesi ve eğitim tabloları | Eğitim için H99 tablosu; her yeni arz için listeleme öncesi belgelerden 20 alanlık girdi belgesi. Her alan kaynağını, alıntısını ve yayın zamanını taşır. | `data/training_table*.csv`, `registry/inputs/` | §3.3, §3.8, §3.9 |
| 3 | Model eğitimi ve dondurma | Şartname sonuç görülmeden yazılır; kod ve walk-forward backtest gelir; beklentiden iyi sonuç bağımsız yeniden üretim ister; model ancak sonra dondurulur. | `docs/specs*/`, `models/` | §2.4.3, Bölüm 4–5, §6.5 |
| 4 | Kayıt ve push kanıtı | `freeze` dizindeki bütün modellerle kaydı yazar; proje sahibi push eder; `push_proof` GitHub'dan zaman kanıtı alır. | `registry/records/`, `registry/push_proofs/` | §6.3, §6.11 |
| 5 | Sonuçların gelmesi | Bülten indirmesi, commit'lenmemiş kayıt varken başlamaz (sıra bekçisi). Sonuçlar yalnız bültenlerden hesaplanır. | `data/raw/bist/`, `data/outcomes/` | §3.10, §6.11.6 |
| 6 | Skorlama | Sınıf git geçmişinden ve push kanıtlarından hesaplanır; eşleşik farklar, ay bloklu bootstrap ile %95 aralık, küçük n kuralları. | `scores/*.json`, `docs/SCORES*.md` | §6.6–§6.12 |
| 7 | Uygulama | Rust gömülü modelleri sha256 zinciriyle doğrular ve çalıştırır; arayüz hesap yapmaz, yalnız biçimlendirir ve çizer. | `app/` | Bölüm 7–8 |

İki ayrıntı şemayı anlamak için önemlidir. Birincisi, **sıra her şeydir**: bir modelin bir arz için "prospektif" sayılması, modeli ekleyen commit'in o arzın sonucunu ekleyen commit'in atası olmasına ve push kanıtına bağlıdır (§6.10.2). İkincisi, **uygulama resmî kayıt yazmaz**: tahmini Rust hesaplar, ama sicile giren kaydı her zaman repodaki Python (`borsai.freeze`) yazar; uygulama yalnız kendi sayısıyla karşılaştırır (§7.9.4).

Kaynak dosyalar: `borsai/freeze.py`, `borsai/push_proof.py`, `borsai/outcomes.py`, `borsai/scoring.py`, `app/src-tauri/build_embed.rs`, `docs/faz5/POST_D1_AKISI.md`, `docs/faz8/POST_BREAK_AKISI.md`.

## 1.5 Bir arzın yolculuğu: NETGL

NETGL, 17 Eylül 2026'da işlem görmeye başlayan bir halka arzdır. Projenin bütün düzeneği bu tek arzda görünür: resmî belgelerden girdi belgesi, eski repodaki tek kanıtlı canlı tahmin, yeni repoda geç yazılmış 16 modelli kayıt, üç gün tavan ve ardından yedi gün taban, ve bu yolun doğurduğu kırılma akşamı modeli. Aşağıdaki sayıların hepsi dosyalardan yeniden okundu.

### 1.5.1 Zaman çizelgesi

| Zaman (İstanbul) | Olay | Kaynak |
|---|---|---|
| 3 Eylül 20:18 | SPK Bülteni 2026/56: planlanan arz yapısı (sabit fiyat 25,52 TL) | `registry/source_docs/NETGL/MANIFEST.json` |
| 9–11 Eylül | Talep toplama | `registry/inputs/NETGL.json` |
| 13 Eylül 17:30 | KAP sonuç bildirimi: 87,5 milyon pay satıldı, talep 2,84 kat | aynı |
| 15 Eylül 18:10 | KAP: işlem görmeye başlama duyurusu, ilk işlem günü 17 Eylül | aynı |
| 16 Eylül 13:45 | Eski repoda V1.5 tahmini donduruldu; push kanıtı 14:32 (11:32:27 UTC) | `registry/legacy_frozen/NETGL_20260916_V1_5/` |
| 17 Eylül | D1: ilk işlem günü | `data/outcomes/NETGL.csv` |
| 22 Eylül 15:19 | Yeni repoda 16 modelli kayıt (`7cb49cf`; push kanıtı 14:06:05 UTC) | `registry/records/NETGL/` |
| 22 Eylül 18:20 | İlk resmî sonuçlar repoya girdi (`f1f9d44`; NETGL'in D1–D3'ü) | `GITLOG.txt` |
| 24 Eylül 16:36 | `post_d1_hazard_v0` donduruldu (`7c18c0f`) | `models/INDEX_POST_D1.json` |
| 30 Eylül 23:09 | D4–D10 sonuçları girdi (`c1eb7ae`) | `docs/live/NETGL_D10_RAPOR.md` |
| 2 Ekim 16:21 | `break_floor_v0` donduruldu (`4d3c9a2`) | `models/INDEX_POST_BREAK.json` |
| 2 Ekim 19:17 | Kırılma akşamı makine kaydı üretildi (`7ee0027` ile commit'lendi) | `registry/post_break/NETGL/` |

Kaynak dosyalar: tabloda anılanlar, `registry/push_proofs/`.

### 1.5.2 Girdi belgesi: 20 alan

Girdi belgesi (`registry/inputs/NETGL.json`) dört resmî kaynaktan doldurulan 20 alandan oluşur. Her dolu alan değerin yanında kaynak belgenin kimliğini, yayın zamanını, dosya yolunu, sha256'sını ve çoğu zaman belgeden birebir alıntıyı taşır. Bütün kaynaklar ilk işlem gününden önce yayımlanmıştır; denetim bunu her alan için ayrı yapar (§3.9.1).

| Grup | Alanlar ve NETGL değerleri | Kaynak |
|---|---|---|
| V1.5 alanları (9) | arz fiyatı 25,52 TL; satılan pay 87.500.000; arz büyüklüğü 2.233.000.000 TL; arz sonrası sermaye 312.500.000; sermaye artırımıyla satılan 62.500.000; ortak satışı 25.000.000; ek satış 0; talep katı 2,84; filtre durumu `NOT_SPECIFIED` | KAP sonuç bildirimi ve eki, KAP işlem başlama duyurusu, SPK bülteni |
| PB alanları (8) | planlanan fiyat 25,52; mevcut sermaye 250.000.000; yeni sermaye 312.500.000; bedelli 62.500.000; mevcut pay satışı 25.000.000; ek satış tavanı 0; taban arz 87.500.000; azami arz 87.500.000 | SPK Bülteni 2026/56 |
| Tarih alanları (3) | ilk işlem günü 2026-09-17; talep toplama 2026-09-09 – 2026-09-11 | KAP işlem başlama duyurusu |

Bu alanlardan modellerin kullandığı özellikler türetilir (§3.6):

- f1 = arz büyüklüğü 2,233 milyar TL (modelde doğal logaritması, 21,53);
- f2 = halka açıklık %28 (87,5 milyon / 312,5 milyon);
- f3 = talep katı 2,84;
- f4 = sermaye artırımı payı %71,43;
- f5 = 0 (f3 var);
- f6 = XU100'ün 20 seanslık getirisi −%9,24 (piyasa ilk işlem gününden önceki bir ayda düşmüştü);
- f1r = reel büyüklük, TÜFE'nin T − 2 ay kuralıyla 2025 fiyatlarına çevrilmiş 1,69 milyar TL.

Kaynak dosyalar: `registry/inputs/NETGL.json`, `registry/records/NETGL/20260922T121936Z_65a39d7392dd.json` (`market20` bloğu), `data/raw/tuik/tufe_genel_2025_100.csv`.

### 1.5.3 Kayıt: 16 model, 22 Eylül, geç kayıt

Yeni repo 21 Eylül'de kuruldu. Faz 1 modelleri 21–22 Eylül'de donduruldu ve 22 Eylül'de, o anki dizindeki 16 modelin hepsiyle NETGL'in kaydı yazıldı: V1.5, altı sabit kural, V1.6, market20, `pb_v0`, tavan modeli ve `@INF` ucu, PB tavan modeli ve `@INF` ucu, iki KM kuralı. 16 modelin 16'sı tahmin verdi, hiçbiri reddetmedi.

Kayıt NETGL'in ilk işlem gününden beş gün sonra yazıldığı için bu 16 model açısından **LATE_RECORD**'dur. Model parametreleri sonucu göremez, çünkü modeller sonuçlardan önce dondu. Ama kayıt ilk işlem gününden sonra yazıldı; bu sınıfın tek açık kanalı, girdiyi toplayan kişinin sonucu biliyor olabilmesidir. Bu yüzden satır etiketi görünür kalır ve kanıtlı canlı metriğe girmez (§6.10.2).

NETGL'in bir ayrıcalığı vardır. Eski repoda, 16 Eylül'de, ilk işlem gününden bir gün önce V1.5 ile bir tahmin yapılmış, commit edilmiş ve push edilmişti. Bu kayıt yeni repoya içeriği değiştirilmeden taşındı. Bu yüzden **NETGL × V1.5 hücresi LIVE'dır** ve bugün canlı sicildeki tek LIVE hücredir (§2.2.2, §6.10.4).

Kaynak dosyalar: `registry/records/NETGL/`, `registry/legacy_roles.json`, `scores/scores.json` (`live.rows`, `class_evidence`).

### 1.5.4 Tahminler

Kayıttaki başlıca tahminler (geç kayıttaki V1.5 değerleri, eski repodaki canlı tahminle aynıdır):

| Model | Çıktı | Tahmin |
|---|---|---|
| `ceiling_hazard_v0` | Beklenen seri E[L] | 3,28 gün (ekranda 3,3) |
| | Medyan seri ve en olası seri | 3 gün |
| | P(L ≥ 3) · P(L ≥ 5) · P(L = 10) | %61 · %27 · %4 |
| | İlk gün tavan olasılığı S_1 | %82 |
| `v1_5_h99` (V1.5) | D1 / D3 / D5 / D10 getirisi | +%7,7 / +%18,5 / +%25,5 / +%25,8 |
| | D5 fiyatı | 32,03 TL |
| | D10'da arz fiyatının üstünde kalma olasılığı | %60 |
| `v1_5_market20_v0` | D10 getirisi (negatif f6 yüzünden düşük) | +%14,4 |
| `pb_v0` | D5 getirisi (talep katı olmadan) | +%26,8 |
| `base_train_median` | D5 getirisi (basit kural) | +%37,4 |
| `base_km_expanding` | Seri olasılıkları (basit kural, bütün geçmiş) | P(L ≥ 3) %67 · P(L ≥ 5) %41 |

Tavan modelinin eğrisi şöyle okunur: büyüklük ortalamanın üstünde (seriyi kısaltan yönde), talep katı ortalamanın altında (yine kısaltan yönde), halka açıklık biraz yüksek (hafifçe uzatan yönde). Sonuçta her günün bozulma riski ortalama bir arza göre yüksek çıkar ve eğri KM kuralınınkinin altında kalır. Hesabın adım adım dökümü §4.4.8'dedir.

Bu kayıttan sonra dondurulan modeller (tavan yolu, v1 ailesi, düşüş modelleri) NETGL için RETRO'dur; kayıtta yer almazlar. Kitaptaki NETGL örneklerinde onların değerleri yalnız gösterim içindir. Örneğin tavan yolu modeli D5 için +%23,6 medyan, düşüş modelleri D10'da arz altına inme için %16–%19 olasılık verirdi (§4.6.4, §4.8.3).

Kaynak dosyalar: `registry/records/NETGL/20260922T121936Z_65a39d7392dd.json`, `registry/legacy_frozen/NETGL_20260916_V1_5/NETGL_20260916_V1_5_frozen_prediction_ledger.csv`.

### 1.5.5 Gerçekleşen

Resmî bültenlere göre NETGL'in on seansı:

| Gün | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Kapanış (TL) | 28,06 | 30,86 | 33,94 | 30,56 | 27,52 | 24,78 | 22,32 | 20,10 | 18,09 | 16,29 |
| Durum | tavan | tavan | tavan | taban | taban | taban | taban | taban | taban | taban |
| Arz fiyatına göre | +%9,95 | +%20,92 | +%32,99 | +%19,75 | +%7,84 | −%2,90 | −%12,54 | −%21,24 | −%29,11 | −%36,17 |

Okuma:

- **Seri üç gün sürdü:** L = 3. Tavan modelinin medyanı ve en olası değeri tam olarak buydu. D1 tavanı +%10 değil +%9,95'tir, çünkü üst limit fiyat adımına aşağı yuvarlanır: 25,52 × 1,1 = 28,072, limit 28,06 (§3.5.1).
- **Seri D4'te tabanda kırıldı:** b = 4. D4 kapanışı 30,56, o günün alt limitine (33,94 × 0,9'un adıma yuvarlanmış hâli) tam eşitti.
- **Kırılmadan sonra yedi gün taban geldi.** D5 getirisi +%7,8 oldu (V1.5'in tahmini +%25,5). D10 kapanışı 16,29 TL, getiri −%36,17; V1.5'in %60 dediği "arz üstünde kalma" gerçekleşmedi.
- **D10, mümkün olan en düşük değerde kapandı.** Kırılma günü kapanışından başlayarak kalan altı seansın hepsi taban olursa D10'un en düşük mümkün kapanışı 16,29'dur; NETGL tam olarak orada kapandı (§5.4.4).

Bu tek arz hiçbir modelin iyi ya da kötü olduğunu kanıtlamaz. Tek arzlık bir betimlemedir.

Kaynak dosyalar: `data/outcomes/NETGL.csv`, `docs/live/NETGL_D10_RAPOR.md`.

### 1.5.6 D1 akşamı: kayıt yok

NETGL D1'i tavanda, gün boyu kilitli kapattı. Bu, D1 sonrası modelin (`post_d1_hazard_v0`) tam kapsamıdır. Ama model 24 Eylül'de dondu; NETGL'in D2 sonucu ise 22 Eylül'de repoya girmişti. Model sonuçtan sonra dondurulduğu için NETGL bu model için RETRO'dur ve D1 sonrası kayıt hiç yazılmadı (§5.2.8).

Akışın provası geçici bir klon depoda yapıldı. Prova, D1'in kilitli olmasının riski düşürdüğünü, ortalamanın üstündeki el değiştirmenin ise artırdığını ve ikisinin neredeyse birbirini götürdüğünü gösterdi: "yarın bozulur" olasılığı 0,139 çıktı, listeleme öncesi modelin cevabı 0,137'ydi (§5.2.5).

Kaynak dosyalar: `docs/faz5/ekler/prova_netgl.txt`, `scores/scores_post_d1.json`.

### 1.5.7 Kırılma akşamı: makine kaydı

NETGL'in yolu yeni bir soru doğurdu: seri tabanda kapanarak bozulunca ne olur? Projenin hiçbir modeli serinin nasıl bozulduğunu kullanmıyordu. Faz 8'in kırılma akşamı modeli (`break_floor_v0`) doğrudan bu vakadan çıktı (§2.6.3, §2.3.13).

Model dondurulduktan sonra `python -m borsai.scoring --break` NETGL için bir **makine kaydı** yazdı. Bu kayıtta insan değer girmez: tahmin, donmuş model dosyasından, D1–D4 arasındaki sha-pinli bültenlerden ve girdi belgesindeki satılan pay sayısından deterministik olarak üretilir (§5.5).

| Kalem | Değer |
|---|---|
| Kırılma günü | b = 4 (22 Eylül), kapanış = alt limit, yani `b_floor = 1` |
| El değiştirme | işlem adedi / satılan pay = 0,104; logaritması −2,267. Eğitimin %5 sınırının altında olduğu için −2,179'a kırpıldı (uyarı kayıtta). |
| **Yarın (D5) da taban olasılığı (F1)** | **%50** (0,4991) |
| D5 ve D6 ikisi de taban olasılığı (F2) | %30 (0,3043) |
| Karşılaştırıcılar | bütün kırılmaların oranı (`@ZERO`) F1 %30, F2 %14; tabanda kırılanların eğitimdeki oranı %54 (model dosyasındaki karşılaştırıcı tablosundan); ürünün eski cevabı: yok (listeleme öncesi kayıt tavan yolu modelinden eskidir) |
| Yastık hesabı | D10'un en düşük mümkün kapanışı 16,29 < 25,52: arz altına inmek mümkün |
| Rejim etiketi | `FON_KRIZI_2026`: ilk seanslar Eylül 2026 fon krizi penceresine düşüyor (§2.6.4) |

Gerçekleşen: D5 ve D6'nın ikisi de taban. Yani F1 ve F2 olayları gerçekleşti. Ama model, kırılma akşamından sonra dondurulduğu için bu satır da RETRO'dur; hiçbir skora girmez (§5.5.6).

Kaynak dosyalar: `registry/post_break/NETGL/machine_20261002T161730Z_c5a61ad0cf26.json`, `models/break_floor_v0.json`, `scores/scores_break.json`.

### 1.5.8 Sınıflar ve skorlar

NETGL'in bugünkü sicil durumu:

| Model(ler) | Sınıf | Neden |
|---|---|---|
| `v1_5_h99` | LIVE | Eski repodaki kayıt D1'den önce push kanıtlı; model sonuçlardan önce dondu |
| Öbür 15 Faz 1 modeli (tavan modeli dahil) | LATE_RECORD | Modeller sonuçtan önce dondu, kayıt D1'den sonra yazıldı |
| Faz 4 ve sonrasının 11 listeleme öncesi modeli | RETRO | Sonuç repoya girdikten sonra donduruldular |
| `post_d1_hazard_v0` | RETRO | D2 sonucundan sonra dondu |
| `break_floor_v0`, `@ZERO` | RETRO | Kırılma sonrası sonuçlardan sonra dondu |

Canlı sicilde model başına en çok 7 arz var; n < 10 olduğu için hiçbir canlı metrik, ortalama ya da hüküm üretilmez, yalnız satır tablosu gösterilir (§6.8). Yine de skor formüllerinin ne yaptığını görmek için NETGL'in tek arzlık kayıplarını hesaplamak öğreticidir. Bunlar yalnız gösterimdir ve hiçbir skora girmez (küçük olan iyidir):

| Ölçü | Model | Karşılaştırıcı | Kaynak |
|---|---|---|---|
| Tavan serisi RPS | `ceiling_hazard_v0` 0.057 | KM, bütün geçmiş 0.097 · KM, son 10 arz 0.124 · `@INF` 0.095 | §4.4.8, §6.6.4 |
| D5 getirisi mutlak hata | V1.5 0.177 (17,7 puan) | eğitim medyanı 0.295 | §6.6.1 |
| D10 "arz üstü" Brier | V1.5 0.363 | taban oranı 0.500 · son-10 oranı 0.250 | §6.6.2 |
| Kırılma F1 Brier | `break_floor_v0` 0.251 | `@ZERO` 0.483 | bu bölüm için hesaplandı |

Tablo bir uyarı da taşır: aynı tek arzda V1.5 bir kurala karşı iyi, öbürüne karşı kötü görünür. Tek arzda bu tür sonuçlar gürültüdür; hüküm ancak n, fark ve %95 aralıkla birlikte verilebilir.

Kaynak dosyalar: `scores/scores.json`, `scores/scores_post_d1.json`, `scores/scores_break.json`, `docs/SCORES.md`.

### 1.5.9 NETGL uygulamada

Uygulamanın sade görünümünde NETGL iki ekranda görünür: Monitör ve Analiz (ikisi de repo modu ister). Analiz sayfasının iki parçası, seri hesaplayıcı ve kırılma kartı, ayrıca anılmaya değer:

- **Monitör.** Arz takip tablosundaki NETGL satırı: arza göre −%36,2; seri 3; listeleme öncesi tahmin "beklenen 3,3 / medyan 3" ve "5+ gün %27" (kapıdan geçtiği için altın); kırılma "4. gün taban"; ertesi gün taban %50; kayıt "geç kayıt, getiri canlı". Üstteki rejim şeridi fon krizi uyarısını gösterir (§8.12).
- **Analiz.** NETGL'in resmî sayfası. Fiyat koridoru on kapanışı, her günün üst limit çentiğini ve V1.5'in fiyat beklentisini çizer. Altında her günün işlem sayısı vardır (D1 17.885 sözleşme; en yüksek gün D9). Tavan sayıları yalnız dondurulmuş kayıttan okunur; model yeniden çalıştırılmaz (§8.15).
- **Seri hesaplayıcı.** Bültende gözlenen seri j = 3'tür. Model "yarın (D4) da tavan" için %67 der; altında gri satır, geçmiş arzların oranını verir: "3 gün tavan yapan 66 arzdan 53 tanesi 4. gün de tavan oldu" (%80). Model 3. günden sonra hep %67 der, çünkü günleri üç grupta ele alır; ekrandaki not bunu açıklar (§8.16, §2.6.11).
- **Kırılma kartı.** Analiz sayfasında "Kırılma akşamı: yarın da taban mı?" kartı: F1 %50, F2 %30, dört karşılaştırma çubuğu, özellik tablosu (kırpılan el değiştirme yıldızlı) ve yastık satırı. Kart yalnız makine kaydından ve skor dosyasından beslenir; katsayıları ancak model dosyasının sha256'sı kayıttakiyle eşitse gösterir (§8.15).

Kaynak dosyalar: `app/src/sade/render/monitor.ts`, `analiz.ts`, `calc.ts`; `app/tests/sade_render.test.ts`; `app/tests/fixtures/ui/`; `docs/app/UI_FIX_RAPOR.md`.

### 1.5.10 NETGL'in öğrettikleri

1. **Canlı kanıtın tek yolu zamanında dondurmaktır.** Aynı arzda aynı V1.5 sayıları, eski repoda bir gün önce push edildiği için LIVE, yeni repoda beş gün sonra yazıldığı için LATE_RECORD sayılır (§2.6.2).
2. **Mekanik olan öğrenilmez, hesaplanır.** D10'un en düşük mümkün kapanışı birebir gerçekleşti. Bu yüzden "D10'da arz altına düşer mi" sorusunun bir kısmı modelle değil, yastık aritmetiğiyle cevaplanır (§5.4).
3. **Rejim değişimi önceden yazılır.** NETGL'in D1'i fon krizinin ilk günlerine denk geldi. Proje bunu model girdisi yapmadı; uyarı etiketi koydu ve krizin modellere etkisini önceden yazdı: "model tabanı az tahmin eder" (§5.3.11).
4. **Bekçiler sınandı.** NETGL'in D4–D10 sonuçları girilirken üç bekçi test kırmızıya döndü ve oturum her seferinde durdu. Hiçbir test gevşetilmedi; kurallar genelleştirildi (§2.6.6).

## 1.6 Kilit sayılar

Aşağıdaki tablo kitapta en sık geçen sayıları ve kaynaklarını toplar. Değerler 6 Ekim 2026 itibarıyladır (HEAD `ee3796d`).

| Konu | Değer | Kaynak |
|---|---|---|
| Donmuş model | 27 + 1 + 2 = 30 (listeleme öncesi · D1 sonrası · kırılma akşamı) | `models/INDEX*.json`; §2.7.2, §6.11.1 |
| Uygulamaya gömülü model | 27 + 1 (kırılma modelleri gömülü değil) | §7.3, §7.4 |
| Eğitim kohortu H99 | 99 arz (2023-09-22 … 2026-08-06), tablo 99 satır × 31 sütun | `data/training_table.csv`; §3.3, §3.8.1 |
| Tavan modeli eğitimi | 97 arz (f3 dolu), 506 kişi-dönem satırı, 83 olay | §4.4.2 |
| Genişletilmiş eğitim tablosu (v2) | 170 satır × 39 sütun (H99 + eski kohort açık kümesi) | `data/training_table_v2.csv`; §3.8.3 |
| Backtest n | 87 (V1.5'in D5/D10 fold'ları ve tavan planı); V1.5'te 351 skorlanabilir fold (89/88/87/87) | §6.5.3, §4.3.6 |
| D1 sonrası backtest | n = 70 | §5.2.6 |
| Kırılma backtest'i | n = 69 (21 ay; yakın dönem) | §5.3.9 |
| Backtest birincil hükümleri | tavan modeli RPS −0.0569 / −0.0496 (iki KM kuralı) geçiyor; V1.5 D5 MAE −0.0839 geçiyor; kırılma F1 −0.1904 (ürüne karşı) ve −0.0281 (`@ZERO`'ya karşı) ön elemeyi geçiyor | §4.9, §5.3.9, §6.9.2 |
| Eski kohort (zaman-dışı) | 135 arz = 71 açık + 64 kasa; kasa bir kez açıldı (29 Eylül) | `registry/oot/cohort_pre_h99.csv`; §3.11, §6.12 |
| Canlı payda | 26 satır: 7 FROZEN arz + 19 kapsam dışı | `registry/ipos.csv`; §3.9.3 |
| Canlı sınıflar | LIVE hücre 1 (NETGL × V1.5); V1.5'te 6 skorlanan (1 LIVE + 5 geç kayıt) + 1 ret; tavan modelinde 6 geç kayıt; D1 sonrası ve kırılma sicillerinde 7/7 RETRO | `scores/*.json`; §6.10.4 |
| Kayıtlar | 7 listeleme öncesi kayıt (16'şar model), 7 kırılma makine kaydı, 0 D1 sonrası kayıt | `registry/`; §5.5.6 |
| Deney günlüğü | 2 146 satır (72 backtest, 19 duyarlılık, 1 koşullu, 2 054 keşif) | `experiments/log.jsonl`; §6.13 |
| Git geçmişi | 175 commit (21 Eylül – 6 Ekim 2026) | `GITLOG.txt`; §2.3.1 |
| Görev dosyası | 79 | `docs/prompts/`; §2.5 |
| Push kanıtı | 31 dosya (18 kanıt commit'i) | `registry/push_proofs/`; §2.4.5, §6.3.4 |
| Sapmalar defteri | 15 bölüm (A–O), yaklaşık 278 KB | `docs/SPEC_DEVIATIONS.md`; §6.14 |
| Python testleri | 952 test (son kabul, sıralı 18 dk 40 sn); 56 test dosyası | §2.7.1, §6.15 |
| Rust testleri | 169 `#[test]`; `test.sh` 164'ünü koşar | §7.12 |
| Arayüz testleri | vitest 376 test (24 dosya); Python parite testi 8; `gen_golden --check` 35 dosya, 0 fark | §8.25 |
| Altın vektör (Python ↔ Rust parite) | 13 102 satır, tolerans \|Δ\| ≤ 1e-9 | §7.11 |
| Rust komutu (arka uç ↔ arayüz) | 55 | §7.7 |
| Uygulama kabul kuralı | U1–U80 | §8.10 |
| Kod satırı (boş satır ve yorum dahil, `wc -l`) | `borsai/` 25 956 (39 dosya); `tests/` Python 19 240 (`reference/` hariç); Rust 25 027 (66 dosya); TypeScript `app/src` 12 642 (58 dosya) + `app/tests` 5 917; CSS 3 184 | bu bölüm için ölçüldü |
| Uygulama | `BorsAi.app` 8,4 MB; varsayılan pencere 1440 × 900; yalnız macOS arm64 | §2.7.5, §7.5 |
| Sade tasarım | 12 pano; tasarımla uygulama arasında 27 gerekçeli fark (F1–F27) | §8.24 |
| Bülten manifestleri | canlı: 73 zip (40 THB + 33 THM); eski kohort: 1 168 satır (zip'ler repo dışında) | §3.2.1 |

## 1.7 Kitabı nasıl okumalı?

### 1.7.1 Bölüm haritası

| Bölüm | Başlık | Ne anlatır |
|---|---|---|
| 2 | Tarihçe, çalışma biçimi ve bugünkü durum | Eski repodan yeni repoya geçiş; faz faz zaman çizelgesi; roller, görev dosyaları, push kanıtı akışı, bağımsız denetimler; dersler; bugünkü durum ve sıradaki adımlar; Python ortamı |
| 3 | Veri: kaynaklar, etiketler ve özellikler | Resmî kaynaklar ve indirme; H99; seans takvimleri; tavan, seri ve getiri etiketleri; f1–f6, f1r, pb1–pb4; ön işleme; eğitim tabloları; girdi belgesi; payda; sonuç dosyaları; pinler |
| 4 | Listeleme öncesi modeller | 27 girişlik dizin; basit kurallar; istatistik araç kutusu; V1.5, V1.6, market20; tavan serisi (hazard) modeli; PB modelleri; tavan yolu; v1 ailesi; düşen arz modelleri; sonuç tablosu |
| 5 | Listeleme sonrası modeller: D1 akşamı ve kırılma akşamı | `post_d1_hazard_v0` ve ofset fikri; `break_floor_v0`; yastık aritmetiği; makine kayıtları; Fable denetimleri |
| 6 | Ölçüm, skorlama ve dürüstlük kuralları | `CLAUDE.md` kuralları; sha256, git DAG, push kanıtı; walk-forward; metrikler; blok bootstrap; hüküm dili; birincil hücre; üç terazi ve sınıflar; dondurma ve kayıt akışı; zaman-dışı kohort ve kasa; deney günlüğü; sapmalar defteri; testler ve bekçiler |
| 7 | Uygulama I: Rust arka uç ve modellerin portu | Mimari; derleme ve gömme; açılış bütünlüğü; güvenlik ve yazma yolları; komut kataloğu; modellerin Rust portu ve sayı hassasiyeti; dondur ve D1 sonrası sihirbazları; parite; testler |
| 8 | Uygulama II: arayüz ve ekranlar | Ön ucun ilkeleri; iki görünüm; "ön uç hesap yapmaz"; biçimler ve SVG; metin kuralları; U-kuralları; Monitör, Giriş, Sonuç, Analiz, hesaplayıcı, Performans, Sicil ekranları; Safir tasarım sistemi; tasarımdan uygulamaya farklar; testler |
| 9 | Sözlük | Kitapta geçen 535 terim, kısaltma ve kod adı; Türk alfabesi sırasıyla, her maddede ilgili bölüm atfı |
| 10 | Dosya dizini: repoda ne nerede | Repodaki her klasör ve önemli dosya; ne işe yaradığı ve hangi bölümde anlatıldığı |

### 1.7.2 Ne merak ediyorsan nereye bakmalı?

| Soru | Nereye |
|---|---|
| Proje nasıl başladı, hangi sırayla ne yapıldı? | §2.2, §2.3 |
| Bir görev nasıl yazılır, kim ne yapar, push nasıl kanıtlanır? | §2.4, §6.3.4 |
| Bugün ne durumda, sırada ne var? | §2.7 |
| Veri nereden geliyor, nasıl kilitleniyor? | §3.1, §3.2, §3.12 |
| "Tavan", "seri", "getiri" tam olarak nasıl hesaplanıyor? | §3.4–§3.5 |
| Bir modelin girdileri ve özellikleri neler? | §3.6, §3.9.1 |
| "Kaç gün tavan?" modeli nasıl çalışır? | §4.4 |
| Getiri tahmini (V1.5) nasıl çalışır? | §4.3 |
| Hangi model gerçekten basit kuralları geçiyor? | §4.9, §6.9.2 |
| D1 akşamı ve kırılma akşamı modelleri ne yapar? | Bölüm 5 |
| Bir tahmin ne zaman "canlı" sayılır? | §6.10, §6.11 |
| %95 aralık nasıl hesaplanıyor, "geçiyor" ne demek? | §6.7, §6.8 |
| Geçmiş testte geleceğin sızmadığını ne garanti ediyor? | §6.5 |
| Eski kohort ve kasa nedir, neden bir kez açıldı? | §6.12 |
| Python ile Rust'ın aynı sayıyı verdiğini ne kanıtlıyor? | §7.8, §7.11 |
| Uygulama neden internete çıkmıyor, nereye yazıyor? | §7.5 |
| Ekrandaki bir sayı nereden geliyor, neden altın renkli? | §8.6, §8.11 |
| Seri hesaplayıcı neden 3. günden sonra hep aynı sayıyı veriyor? | §8.16, §2.6.11 |
| Tasarımdaki bir öğe uygulamada neden yok? | §8.24 |

### 1.7.3 Okuma notları

- **Sayıların kaynağı.** Her alt bölümün sonunda "Kaynak dosyalar" satırı vardır. Bazı bölümler yazılırken yeniden hesaplanan değerleri "[ölçüldü]" diye işaretler. Dosyada karşılığı bulunmayan yerler "belirsiz" diye yazılmıştır.
- **Sayı yazımı.** Bölümlerin bir kısmı fiyat ve yüzdeleri Türkçe yazımla (25,52 TL; %36,2), bir kısmı repodaki yazımla, ondalık noktayla (25.52; −0.0569) verir; ikisi aynı değeri gösterir. Skor farkları ve aralıklar çoğu yerde noktalı yazılır (−0.0569 [−0.0833, −0.0286]). Uygulama ekranları da ondalık nokta kullanır (§8.7).
- **Fark ve aralık.** Kitaptaki farklar "model − karşılaştırılan"dır. Kayıp ölçülerinde negatif fark modelin daha iyi olduğu demektir. Köşeli parantez %95 aralığıdır.
- **Tarih ve saat.** Saatler aksi yazılmadıkça İstanbul saatidir (+03:00); push kanıtlarının saati UTC'dir.
- **Yazılmayanlar.** Eski kohort kasasındaki arzların kodları ve resmî bülten dosyalarının tek tek adları hiçbir bölümde yazılmaz; yalnız ad kalıbı verilir. Bu, kasanın körlüğünü koruyan proje kuralıdır (§2.6.5, §6.12.3).
- **Bölümler bağımsız okunabilir.** Her bölüm kendi kavramlarını baştan tanımlar. Önce kuralları sonra modelleri görmek isteyen okur için 1 → 6 → 4 → 5 sırası akıcıdır; tarihçe (2) ve veri (3) gerektikçe açılabilir; uygulamayla ilgilenen okur doğrudan 7 ve 8'e geçebilir.

Kaynak dosyalar: bu kitabın 2–8. bölümleri.

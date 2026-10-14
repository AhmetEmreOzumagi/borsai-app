# 6. Ölçüm, skorlama ve dürüstlük kuralları

Bu bölüm BorsAi'nin en az görünen ama en çok emek verilmiş katmanını anlatır: bir modelin "iyi" olduğunu söylemeden önce neyin, nasıl ve hangi sırayla ölçüldüğünü. Model formülleri başka bölümlerin konusu (Bölüm 4 ve 5). Burada şu sorulara cevap arıyoruz:

- Bir tahmin ne zaman "gerçekten önceden yapılmış" sayılır, bunu kim ya da ne kanıtlar?
- Geçmiş veride test ederken geleceği yanlışlıkla görmemeyi nasıl garanti ederiz?
- "Model kuraldan iyi" cümlesini hangi sayılar, hangi aralık ve kaç arz destekler?
- Aynı veride çok şey denendiğinde şans eseri çıkan sonuçları nasıl ayıklarız?
- Bütün bunları kim denetler ve kural çiğnendiğinde ne kırmızıya döner?

Bölüm uzun. Her alt bölüm bir kavramı sıfırdan açıklar (sezgi, formül, repodan gerçek örnek) ve sonunda ilgili dosyaları listeler. Sayıların hepsi bu bölüm yazılırken repodaki dosyalardan okundu ya da Python ile yeniden hesaplandı; yeniden hesaplananlar "[ölçüldü]" diye işaretli. Emin olunamayan yerler "belirsiz" diye yazıldı.

Kısa bir uyarı: Repo anlık kopyasında git deposu yok, yalnız `GITLOG.txt` (175 commit) var. Bu yüzden git komutu gerektiren denetimler (ata/torun ilişkisi gibi) burada yeniden koşulamadı; onları koddan ve raporlardan aktarıyorum.

---

## 6.1 Neden bu kadar kural var?

Halka arz tahmini küçük veriyle çalışan bir iştir. Eğitim kümesi H99 dediğimiz 99 arzdır (2023-09-22 ile 2026-08-06 arası). Küçük veride dört tuzak var:

1. **Sızıntı (leakage):** Model eğitilirken, tahmin anında bilinemeyecek bir bilgi (gelecekteki fiyat, aynı gün listelenen başka bir arzın sonucu) eğitime karışır. Backtest olağanüstü iyi çıkar, gerçek hayatta model çöker.
2. **Sonradan bilgelik (hindsight):** Sonuçları gördükten sonra modeli, özelliği ya da eşiği değiştirip "önceden de böyle düşünmüştük" demek. İnsan bunu çoğu zaman fark etmeden yapar.
3. **Çoklu karşılaştırma:** 28 hücreye bakıp 15'inde "geçiyor" görmek etkileyicidir; ama hepsini aynı veride denediyseniz bazıları şans eseri geçer.
4. **Küçük n yanılgısı:** 6 arzda model kurala 5–1 üstün geldi diye model iyi değildir. Gürültü bu büyüklükte farkları kolayca üretir.

BorsAi'nin cevabı, bu tuzakları insanın iyi niyetine bırakmamak, kodla ve testle zorlamaktır. `CLAUDE.md`'nin ilk cümlesi bunu söyler: "dürüst doğruluk için en az set; kodla zorlanır". Bu bölümdeki her kuralın arkasında, çiğnendiğinde kırmızıya dönen bir test (bekçi) vardır.

Kaynak dosyalar: `CLAUDE.md`, `docs/specs/SPEC_SCORING.md`.

---

## 6.2 CLAUDE.md: kurallar madde madde

`CLAUDE.md` 6 numaralı kural, bir sıra kuralı ve birkaç genel ilkeden oluşur. Aşağıda her birini, neden var olduğunu ve kodda nerede zorlandığını açıklıyorum.

### Kural 1: Dondurma

> Resmi tahmin kaydı girdileri, kayıtlı TÜM modellerin çıktılarını ve her modelin parametre hash'ini birlikte içerir. İlk işlem gününden önce commit edilir ve uzak depoya push edilir; zaman kanıtı push'tur, yerel saat değil. Dondurulmuş kayıt silinmez; hatalıysa iptal kaydı düşülür.

**Ne demek:** Bir arz için tahmin yapıldığında, o an kayıtlı olan bütün modellerin tahmini tek bir JSON dosyasına yazılır. Dosyada girdiler, her modelin çıktısı ve her modelin parametre dosyasının sha256 parmak izi bulunur. Bu dosya GitHub'a gönderilir (push) ve GitHub'ın sunucu saati "bu dosya şu anda vardı" diye kanıt olur.

**Neden "TÜM modeller":** Yalnız iyi görünen modelin tahminini kaydedip ötekileri unutmak bir seçim yanlılığıdır. Hepsi birlikte kaydedilince sonradan "aslında şu model doğru söylemişti" denemez.

**Neden yerel saat değil:** Bilgisayarın saati elle değiştirilebilir, dosyanın içindeki tarih elle yazılabilir. GitHub'ın sunucu saatini kullanıcı değiştiremez.

**Neden silinmez:** Kötü çıkan bir tahmini silmek, kötü sonuçları sicilden temizlemek demektir. Hatalı kayıt kalır; üstüne açık bir "iptal kaydı" eklenir ve iptalin nedeni herkese görünür.

Kuralın devamı iki aşama tanımlar:
- **POST_D1 aşaması:** İlk işlem gününden (D1) sonra, D1 bilgisiyle güncellenen tahmin. Kaydın son teslim anı, D1'i izleyen ilk seans günü saat 09:40 (İstanbul). 09:40, Borsa İstanbul'da açılış emir toplamasının saatidir; ikinci günün fiyatı oluşmaya başlamadan önce kayıt kanıtlanmış olmalı.
- **POST_BREAK aşaması (kırılma akşamı):** Tavan serisi bozulduğu akşam yapılan tahmin. Bu aşamada insan değer girmez; tahmini makine, dondurulmuş model ve sha'sı sabitlenmiş resmi bültenlerden skorlama anında üretir ve `registry/post_break/` altına yalnız ekleme yaparak yazar. Bu satırlar `MACHINE_SEQUENCED` sınıfıyla ayrı bir ölçekte (`live_break`) skorlanır.

### Kural 2: Payda

> Başlangıçtan sonra işlem görmeye başlayan her arz sicile girer. Dondurulmadıysa nedeniyle birlikte "atlandı" satırı olur.

**Neden:** "Modelimiz kaydettiğimiz arzlarda çok iyi" cümlesi, hangi arzların kaydedilmediğini söylemezse anlamsızdır. Kolay arzları kaydedip zorları atlamak sonucu güzelleştirir. Payda dosyası `registry/ipos.csv` her arzı yazar; kayıt yoksa `SKIPPED` ve nedeni, kapsam dışıysa (varant, fon, bedelli kalan pay, kod değişikliği…) `OUT_OF_SCOPE` ve nedeni yazılır. Bugün dosyada 26 satır var: 7 `FROZEN` (CITAS, TKNKA, VEYAS, KPEKS, INTET, BKRGY, NETGL) ve 19 `OUT_OF_SCOPE` [ölçüldü].

### Kural 3: Üç terazi, asla toplanmaz

> backtest (retrospektif walk-forward), canlı (prospektif) ve zaman-dışı eski kohort (2023-09-22 öncesi arzlar; tahminler sonuç repoya girmeden push edilir). Bir arz bir model için ancak modelin JSON'u o arzın sonucu repoya girmeden önce dondurulduysa prospektiftir. Bu, tarihlerden hesaplanır; elle etiketlenmez.

"Terazi" burada bir doğruluk ölçüm ortamı demek. Üçü farklı türden kanıt üretir (§6.10'da ayrıntılı). Toplanırsa iyi kanıtla zayıf kanıt karışır. "Elle etiketlenmez" kısmı kritiktir: hiçbir dosyada "bu satır canlıdır" diye bir alan yoktur; sınıf her seferinde git geçmişinden ve push kanıtlarından yeniden hesaplanır.

### Kural 4: Deney günlüğü

> Her backtest koşusu (model_id, spec hash, veri hash, metrikler, zaman) append-only günlüğe otomatik yazılır.

**Neden:** Çoklu karşılaştırmayı görünür kılmak için. Kaç varyant denendiği bilinmezse, bir modelin "kazanması" yorumlanamaz. Günlük `experiments/log.jsonl`; ayrıntı §6.13.

### Kural 5: Değişiklik = yeni model_id

> özellik, ön işleme, ızgara, eğitim kesimi ya da veri sürümü değişirse yeni kimlik verilir. Eskisi ve skorları listede kalır.

**Neden:** Bir model kötü sonuç verdi diye "biraz düzeltip" aynı adla devam etmek, eski kötü skoru silmek demektir. Yeni kimlik, sicili sıfırdan başlatır; eskinin sicili görünür kalır. Örnek: tavan serisi modeli v0 dururken v1 ailesi (`ceiling_hazard_v1_clip`, `_real`, `_pooled`) ayrı kimliklerle eklendi.

İnce bir ayrım: Kod şartnameye uymuyorsa ve düzeltme modeli şartnameye *uydurmaksa*, model kimliği değişmez (çünkü modelin tanımı değişmiyor, uygulamadaki hata düzeltiliyor). Bu tür düzeltmeler `docs/SPEC_DEVIATIONS.md`'ye yazılır (§6.14).

### Kural 6: Skorlama

> sonuç yalnız resmi THB/THM'den gelir. Tanımlar ilk skorlamadan önce kodda yazılıdır. Her model basit kurallarla (her zaman tavan, eğitim medyanı, taban oranı, son-10 taban oranı) aynı arzlarda eşleşik skorlanır. Doğruluk fark + aralık + n ile raporlanır; "geçiyor" denebilmesi için aralığın 0'ı dışlaması gerekir.

Dört parçası var:
- **Resmi kaynak:** THB, Borsa İstanbul'un günlük fiyat bülteni; THM, günlük limit (taban/tavan) bülteni. İkincil sitelerden fiyat alınmaz.
- **Tanımlar önce:** Skor tanımı (`borsai/scoring.py`) sonuç verisi repoya girmeden commit edildi. Git geçmişinde bu görünür: `e469a93` ("outcome and scoring definitions in code before any post-listing outcome data"), sonuçları getiren `f1f9d44`'ün atasıdır.
- **Eşleşik karşılaştırma:** Model ham haliyle değil, aynı arzlarda basit bir kuralla yan yana skorlanır (§6.6).
- **Fark + aralık + n:** Tek bir "doğruluk yüzdesi" yoktur (§6.7, §6.8).

### Sıra kuralı

> 2026-08-19 sonrası THB/THM verisi ve 2026-08-06 sonrası listelenen arzların sonuçları, Faz 1 model JSON'ları dondurulmadan repoya alınmaz. Eski kohortun sonuç verisi, kohortun bütün listeleme öncesi tahmin kayıtları push edilmeden repoya alınmaz; kasadaki arzların sonuçları, doğrulanacak özellik önceden kaydedilip push edilmeden alınmaz.

Bu, "önce tahmin, sonra sonuç" ilkesinin depo düzeyindeki hali. Sonuç verisi repoya girdiği an, ondan sonra yazılan her şey (kod, model, rapor) o sonucu "görmüş" sayılır. Kod iki yerde zorlar: indirme anında (`outcomes.sequence_guard`) ve her test koşusunda (`scoring.sequence_violations`, `tests/test_outcome_guard.py`). Ayrıntı §6.11.

### Genel ilkeler

- **Veri yalnız resmi kaynaklardan** (KAP, SPK, Borsa İstanbul); ikincil kaynak etiketlenir.
- **git push, tag ve amend yalnız proje sahibi tarafından.** Zaman kanıtı push'a dayandığı için push'u yapan elin insan olması, otomasyonun kendi kendine "kanıt" üretmesini önler. `amend` yasağı, commit geçmişinin yeniden yazılmasını (dolayısıyla ata ilişkilerinin değişmesini) engeller.
- **`legacy/` değiştirilmez.** Eski repodan birebir kopyadır; `tests/test_guardrails.py` dosyaların hash'lerini `docs/PROVENANCE.md`'deki değerlerle karşılaştırır.
- **Testler: `.venv/bin/pytest -q`.**

Kaynak dosyalar: `CLAUDE.md`, `registry/ipos.csv`, `borsai/scoring.py` (`sequence_violations`), `borsai/outcomes.py` (`sequence_guard`), `tests/test_outcome_guard.py`, `tests/test_guardrails.py`.

---

## 6.3 Temel araçlar: sha256, kanonik JSON, git DAG ve push kanıtı

Kuralların hepsi dört teknik araca dayanır. Önce onları anlamak gerekir.

### 6.3.1 sha256: dosyanın parmak izi

**Sezgi:** sha256 bir "özet fonksiyonu"dur (hash). Herhangi uzunlukta bir bayt dizisini alır, 256 bitlik (64 onaltılık hane) bir değer üretir. İki önemli özelliği var:
- Aynı girdi her zaman aynı çıktıyı verir.
- Girdideki tek bir bit değişse çıktı tamamen değişir; ve verilen bir çıktıya uyan başka bir girdiyi bulmak pratikte imkânsızdır.

Bu yüzden bir dosyanın sha256'sını bir yere yazmak, o dosyayı "mühürlemek" demektir. Sonradan biri dosyayı değiştirirse hash tutmaz.

**Repodaki kullanımları:**
- `models/INDEX.json` her model dosyasının sha256'sını taşır. Kayıt yazıcı her modeli yüklerken hash'i yeniden hesaplar; tutmazsa durur (`freeze._index_models`: "parametre dosyası sha256 INDEX ile uyuşmuyor"). [ölçüldü: 27 + 1 + 2 model dosyasının hepsi dizindeki hash'le eşit]
- Her tahmin kaydı, kullandığı `INDEX.json`'un ve her modelin parametre dosyasının sha256'sını içerir (`params_sha256`).
- Resmi bülten zip'leri `data/raw/bist/MANIFEST.csv`'de URL, bayt sayısı ve sha256 ile pinlenir. Yerel dosya manifestle tutmazsa okuma durur.
- Girdi belgelerindeki her alan, kaynak PDF'in sha256'sını taşır (`source_sha256`).
- Tahmin kaydının dosya adı bile hash'tir: `20260922T121936Z_65a39d7392dd.json`'daki son 12 hane, dosya baytlarının sha256'sının başıdır ("içerik adresli" dosya adı).

**Pin** kelimesi bu bölümde çok geçecek: bir dosyanın beklenen hash'ini kodda ya da testte sabitlemek. Pinli dosya değişirse test kırmızı olur.

### 6.3.2 Kanonik JSON

Aynı bilgiyi taşıyan iki JSON metni anahtar sırası ya da boşluklar yüzünden farklı baytlar olabilir; o zaman hash'leri de farklı olur. `borsai/provenance.py` iki biçim tanımlar:
- `canonical_json`: anahtarlar sıralı, boşluksuz, UTF-8. Hash girdisi olarak kullanılır (ör. model şartnamesinin `spec_sha256`'sı).
- `pretty_json_bytes`: anahtarlar sıralı, 2 boşluk girinti, sonda satır sonu; float'lar Python'un en kısa gidiş-dönüş biçimiyle. Dosyaya yazılan her JSON bu biçimdedir.

Böylece aynı içerik her makinede aynı baytları, dolayısıyla aynı hash'i verir.

### 6.3.3 git DAG: ata ve torun

**Sezgi:** Git'te her commit, bir önceki commit'i (ebeveynini) işaret eder. Commit'ler oklarla birbirine bağlanır ve geriye doğru hiç döngü olmaz. Matematikte buna yönlü çevrimsiz çizge (DAG, directed acyclic graph) denir.

```
ff3eee6 ← 5fa849d ← d3fabad ← b09cab5 ← 1869da6 ← 7cb49cf ← 99aed71 ← e469a93 ← f1f9d44 ← …
(iskelet)  (Faz 1A)  (şartname) (Faz 1B)  (denetim)  (kayıtlar)  (kanıtlar)  (tanımlar)  (sonuçlar)
```

A commit'inden B commit'ine okları izleyerek (geriye doğru) gidilebiliyorsa A, B'nin **atası**dır, B de A'nın **torunu**. Bir commit kendisinin de atası sayılır. Komut: `git merge-base --is-ancestor A B` (çıkış kodu 0 ise ata).

**Neden saat yerine DAG:** Commit tarihleri elle ayarlanabilir. Ama B'yi A'nın torunu olarak yaratmak için A'nın içeriği B oluşturulurken *mevcut* olmalıdır. "Model dosyasını ekleyen commit, sonuç dosyasını ekleyen commit'in atası mı?" sorusu, saat kullanmadan "model sonuçtan önce mi vardı?" sorusunu cevaplar. `amend` ve geçmiş yeniden yazma yasağı bu ilişkiyi sabit tutar.

Kodda: `push_proof.is_ancestor` bu git komutunu çağırır; `scoring.Git` sınıfı sonuçları önbelleğe alır ve "bu dosyayı ilk ekleyen commit" (`added_commit`: `git log --diff-filter=A`) sorgusunu yapar.

DAG tek başına yetmez: Yerelde kurulan geçmiş GitHub'a gönderilmeden önce yeniden yazılabilir. "Bu commit şu anda gerçekten vardı" demek için dışarıdan bir tanık gerekir. O tanık push kanıtıdır.

### 6.3.4 Push kanıtı

**Yöntem:** `borsai/push_proof.py`, proje sahibi `git push` yaptıktan sonra çalıştırılır. GitHub'ın commit status API'sine (`POST /repos/{owner}/{repo}/statuses/{sha}`) "bu commit origin'de var" diye bir durum yazar. GitHub o sha'yı tanımıyorsa 404 döner; yani 201 (oluşturuldu) yanıtı, commit'in o anda uzak depoda bulunduğunun kanıtıdır. Yanıttaki `created_at` alanı GitHub sunucusunun saatidir.

Kanıt dosyası `registry/push_proofs/<40 haneli sha>.json` (şema `borsai.push_proof/1`):

| Alan | Anlamı |
|---|---|
| `proven_commit_sha` | Kanıtlanan commit |
| `repo_slug` | Depo (ör. `.../borsai`) |
| `method` | `GITHUB_COMMIT_STATUS_CREATED_AT` |
| `auth` | `gh` CLI ya da `GH_TOKEN` (token dosyaya yazılmaz) |
| `created_at` | GitHub'ın sunucu zamanı (UTC, `...Z`) |
| `github_status_id`, `context` | GitHub'ın verdiği kimlik ve bağlam (`borsai/push-proof`) |
| `github_response` | API yanıtının kendisi, olduğu gibi |
| `note` | "Kanıt, bu commit'i ve onun bütün atalarını kapsar." |

Kurallar:
- **Kapsama:** Bir commit'in kanıtı, onun bütün atalarını da kapsar (commit uzak depodaysa ataları da oradadır). Bir commit için geçerli zaman, kendisini ya da onu içeren bir torunu kanıtlayan **en erken** kanıtın `created_at`'idir (`earliest_proof`, `scoring.proof_time`).
- **Yeniden yazma yok:** Dosya varsa ağa çıkılmaz, dosya `xb` kipinde (yalnız yeni dosya) yazılır. Sonraki bir status ilk kanıtı değiştiremez.
- **Doğrulama:** `validate_proof` şemayı, 40 haneli sha'yı, `created_at` biçimini ve yanıt URL'sinin aynı commit'i gösterdiğini denetler.
- **Kimlik yoksa:** `MissingAuthError`; hiçbir dosya yazılmaz.

Repoda 31 kanıt dosyası var [ölçüldü]. İlki Faz 1A commit'i `5fa849d` için (`created_at` 2026-09-22T14:06:00Z), sonuncusu Faz 8 dondurması `4d3c9a2` için (2026-10-02T14:45:08Z). Bir örnek: `5fa849d` commit'inin yerel zamanı 2026-09-21 21:14 (+03:00), ama push kanıtı ertesi gün 14:06Z'de alındı. Hesapta geçerli olan ikincisidir: yerel commit zamanı hiçbir şeyi kanıtlamaz.

Eski repodan gelen NETGL dondurması da aynı yöntemle kanıtlıdır (`registry/legacy_frozen/NETGL_20260916_V1_5/push_proof.json`, `created_at` 2026-09-16T11:32:27Z; `context` farklı: `borsai/true-live-freeze-proof`). `tests/test_push_proof.py::test_same_method_as_legacy_netgl_proof` iki yöntemin aynı olduğunu sınar.

**GitHub Events API ve "30 gün sınırı" hakkında:** Görev metninde geçen bu iki kavram repo kodunda ve kanıt dosyalarında yok. Kanıt yöntemi Events API değil, commit status API'dir; dosyalarda geçen `events_url` yalnız GitHub yanıtının kullanıcı nesnesindeki standart bir bağlantıdır. "30 gün" ifadesi repoda yalnız SPK'nın fiyat istikrarı kuralı (halka arz sonrası en çok 30 gün) bağlamında geçiyor. Push kanıtı için bir süre sınırı kodda tanımlı değil; bu konuda başka bir kural varsa repo dışındadır (belirsiz).

Kaynak dosyalar: `borsai/provenance.py`, `borsai/push_proof.py`, `registry/push_proofs/`, `registry/legacy_frozen/NETGL_20260916_V1_5/push_proof.json`, `tests/test_push_proof.py`.

---

## 6.4 Ölçülen şey: sonuç tanımları (kısa)

Skorlamanın ne ölçtüğünü bilmeden metrikleri anlamak zor. Ayrıntı veri bölümünde (§3.4–§3.5); burada yalnız skorlamaya gereken tanımlar (`SPEC_SCORING §2–§3`):

```
D_h(a)   = arzın işlem gördüğü (sözleşme > 0 ve kapanış > 0) h'inci resmi seans
R_h      = kapanış(D_h) / arz fiyatı − 1          (getiri; h ∈ {1, 3, 5, 10})
Y_h      = 1[kapanış(D_h) > arz fiyatı]          (arz fiyatının üstünde mi?)
tavan_k  = 1[Decimal(kapanış(D_k)) == Decimal(üst limit(D_k))]   (o günün THM'sinden)
L        = D_1'den başlayan kesintisiz tavan sayısı (0..10)
S_k      = P(L ≥ k)  (tavan modellerinin çıktısı: "en az k gün tavan" olasılığı)
```

Önemli ayrıntılar:
- Yarım gün seans sayılır; tam gün durdurma sayılmaz (D_h kayar, `shifted_by_suspension`); 15 seansta D_10 oluşmazsa eksik ufuklar `TARGET_UNAVAILABLE` olur ve bütün modellerden aynı anda düşer.
- Tavan etiketi "%10 arttı mı" diye değil, kapanışın o günün resmi üst limitine Decimal (ondalık, yuvarlamasız) eşitliğiyle belirlenir. Sabit 1.10 oranı hiçbir yerde kullanılmaz; çünkü fiyat adımı yuvarlaması yüzünden gerçek oran H99'da 1.09604 ile 1.1 arasında değişiyor.
- Sayılar `Decimal(str)` ile ham metinden okunur, float'a girmez.

Canlı arzların sonuçları `data/outcomes/<TICKER>.csv`'de, satır başına bir seans (h, tarih, ham kapanış, ham limit, işlem sayısı, durdurma bayrakları, tavan etiketi, R_h, Y_h, iki bültenin sha256'sı, durum). Satır yalnız `PENDING` iken doldurulabilir; dolu satır değişecekse `OutcomeConflict` (resmi veri değişti) ile durulur.

Kaynak dosyalar: `docs/specs/SPEC_SCORING.md` §1–§3, `borsai/outcomes.py`, `data/outcomes/`.

---

## 6.5 Walk-forward backtest

### 6.5.1 Sezgi

Elimizde 99 geçmiş arz var. Bir modeli "geçmişte deneyerek" sınamak istiyoruz. En kötü yol: 99 arzın hepsiyle eğitip aynı 99 arzda hatayı ölçmek. Model bu arzları ezberleyebilir; hata yapay olarak küçük çıkar.

Daha iyi ama yine yanlış yol: arzları rastgele ikiye bölmek (eğitim/test). Sorun zamanda: 2025'te listelenen bir arzı, 2026'daki arzlarla eğitilmiş bir modelle tahmin etmek, 2025'te sahip olunmayan bilgiyi kullanmak demektir.

**Walk-forward** (ileriye yürüyen) backtest gerçek hayatı taklit eder: Her arz için, o arzın ilk işlem gününde *bilinebilecek* geçmiş arzlarla bir model eğitilir ve yalnız o arz tahmin edilir. Sonra bir sonraki arza geçilir; eğitim kümesi bir adım büyür. Her böyle "tek arzlık test" bir **fold**'dur.

```
zaman →   a1  a2  a3 … a11 a12 a13 …
fold(a12): eğitim = {hedefi a12'nin ilk işlem gününden önce kesinleşmiş arzlar}, test = a12
fold(a13): eğitim = {… a12 dahil, eğer a12'nin hedef günü a13'ten önceyse}, test = a13
```

### 6.5.2 Fold tanımı ve "kesin önce" kuralı

Kod: `borsai/backtest.py::plan_folds` (plan kimliği `H99_WALK_FORWARD_STRICT_PRIOR_DATE_MIN_TRAIN_10`). Her ufuk h ∈ {D1, D3, D5, D10} ve her test arzı k için:

```
tahmin tarihi  p(k)  = first_trading_date(k)
eğitim(k, h)        = { j : target_session_date(j, h) < p(k) }      (KESİN küçük)
durum               = SCORABLE  eğer |eğitim(k, h)| ≥ MIN_TRAIN_N = 10
                      INSUFFICIENT_TRAINING_HISTORY  aksi halde
```

Dikkat: Kural "j, k'dan önce listelendi" değil, "j'nin **h ufkundaki hedef seansı** k'nın ilk işlem gününden kesin önce" diyor. Neden? D10 hedefi için j'nin 10. işlem günü kapanışı gerekir. j, k'dan bir hafta önce listelendiyse, k'nın ilk günü geldiğinde j'nin D10 kapanışı henüz oluşmamıştır. O satırı eğitime koymak geleceği kullanmak olur. Bu yüzden aynı test arzı için D1 eğitim kümesi, D10 eğitim kümesinden büyüktür.

"Kesin küçük" (`<`, `≤` değil) de bilinçli: Aynı gün kapanan bir hedef, test arzının ilk işlem günü sabahı henüz bilinmez.

Kod bu kuralı yalnız uygulamakla kalmaz, sonradan da denetler. `plan_folds` her eğitim satırı için üç koşulu yeniden sınar ve biri bozulursa `BacktestStop` hatasıyla durur:
- `kendi kendini eğitme`: test arzı eğitim kümesinde olamaz;
- `aynı gün sızıntısı`: test arzıyla aynı gün listelenen arz eğitimde olamaz;
- `gelecek sızıntısı`: eğitim satırının hedef günü, kesim gününden (tahmin günü − 1) sonra olamaz.

Ledger'ın her satırı eğitim kümesinin kimliğini de taşır: `training_tickers_sha256` (eğitim arzlarının listesinin hash'i) ve `training_targets_sha256` (her eğitim arzının `ticker|hedef tarihi|R|Y` satırlarının hash'i). Böylece bağımsız bir denetçi, aynı fold'u kendi koduyla kurup hash'leri karşılaştırabilir.

### 6.5.3 MIN_TRAIN_N = 10 ve neden n = 87

10'dan az örnekle eğitilmiş bir modelin tahmini (ve onunla karşılaştırılan kuralın medyanı) anlamsız derecede oynaktır. Bu yüzden eğitim kümesi 10'dan küçük olan fold skorlanmaz. Sonuç: ilk birkaç arz hiçbir ufukta skorlanamaz; uzun ufuklarda (hedefi daha geç kesinleştiği için) daha fazla arz kaybedilir.

Bunu repodaki verilerden bağımsız olarak yeniden hesapladım (`data/training_table.csv` ve SESSIONS dosyasındaki `target_session_date` sütunuyla; `borsai` import edilmeden) [ölçüldü]:

| Ufuk | Skorlanabilir fold | Skorlanamayan | Son skorlanamayan arz (eğitim n) |
|---|---|---|---|
| D1 | 89 | 10 | BINHO, 2023-11-20 (9) |
| D3 | 88 | 11 | EKOS, 2023-11-21 (9) |
| D5 | **87** | 12 | AGROT, 2023-11-23 (9) |
| D10 | **87** | 12 | AGROT, 2023-11-23 (9) |
| Toplam | 351 | 45 | — |

Bu sayılar kodun belgelediği "351 skorlanabilir fold (89/88/87/87)" ile ve deney günlüğündeki ilk koşunun `folds_scorable` alanıyla (`{"D1": 89, "D3": 88, "D5": 87, "D10": 87}`) birebir aynı. D5 skorlanan fold'ları 23 farklı takvim ayına yayılıyor (2023-12…2026-08) [ölçüldü].

**Tavan modellerinde de n = 87, ama başka bir yoldan.** Tavan planı (`PLAN_CEILING`) yalnız talep katı (f3) dolu arzları kullanır: 99 arzın 97'si [ölçüldü]. Eğitim "kişi-dönem" satırlarıdır: her geçmiş arz için, serisi sürdüğü her gün bir satır ("o gün tavan bozuldu mu?") ve satır ancak seans tarihi test arzının ilk işlem gününden önceyse girer. Skorlanabilirlik üç koşul ister: en az 10 eğitim arzı, en az 5 olay (bozulma), en az 5 sağ kalım (bozulmama). Bağımsız hesabım: 97 arzın 87'si skorlanabilir, 10'u değil; skorlanan 87 fold 24 farklı aya yayılıyor [ölçüldü]. `scores.json`'da `ceiling_hazard_v0` birincil hücresinin `n = 87, n_blocks = 24` olması bununla tutarlı.

Dolayısıyla backtest tablolarında sık gördüğünüz n = 87, "99 arzdan ilk 12'si (D5/D10'da) ya da f3'süz 2 + yetersiz geçmişli 10 arz (tavan planında) düştükten sonra kalan" sayıdır. Rastlantı değildir; şartnameden ve veriden deterministik olarak çıkar.

### 6.5.4 Planlar

Her modelin bir planı vardır (şartnamesinde yazılı; `borsai/specs.py`). Planlar kesim gününü ve skorlanabilirlik koşulunu tanımlar:

| Plan | Kesim | Kullanan | Koşul |
|---|---|---|---|
| `PLAN_V15` | ilk işlem günü T | V1.5, V1.6, market20, basit kurallar | eğitim ≥ 10 |
| `PLAN_PB` | ilk talep toplama günü B | `pb_v0` | eğitim ≥ 10 (hedef < B) |
| `PLAN_CEILING` | T, f3 dolu 97 arz | `ceiling_hazard_v0`, KM kuralları | ≥ 10 arz, ≥ 5 olay, ≥ 5 sağ kalım |
| `PLAN_PB_CEILING` | B, 99 arz | `pb_ceiling_v0` | aynı |
| `PLAN_CEILING_PATH`, `PLAN_PB_CEILING_PATH` | T / B | tavan yolu modelleri | kaynak tavan ledger'ını aynen kullanır |
| `PLAN_POST_D1` | T, f3 dolu ve D1'de tavan kapanan arzlar (nihai eğitimde 81) | `post_d1_hazard_v0` | ≥ 10 arz, ≥ 5 olay, ≥ 5 sağ kalım |
| `PLAN_CEILING_POOLED` | T, H99 + eski kohort açık kümesi | `ceiling_hazard_v1_pooled` | — |
| `PLAN_FALL_*` | T | düşen arz modelleri | eğitim ≥ 10 |
| `PLAN_BREAK_H99` | kırılma günü | `break_floor_v0` | ≥ 10 satır, 5 olay, 5 olay-dışı |

PB modelleri talep toplama başlamadan tahmin yaptığı için kesimleri daha erkendir: eğitim satırının hedefi talep toplamanın ilk gününden (B) önce kesinleşmiş olmalıdır. Kod bunu da denetler (`talep toplama kesimi sızıntısı`).

Basit kurallar, karşılaştırıldıkları modelin planında ve **aynı eğitim kümesinden** koşar. Örneğin `base_train_median` D5 fold'unda, V1.5'in o fold'daki eğitim arzlarının D5 getirilerinin medyanını tahmin eder. Böylece model ile kural aynı bilgiyle yarışır.

### 6.5.5 Ledger ve altın dosyalar

Her koşu bir **fold ledger**'ı üretir: fold başına bir CSV satırı (kimlik, eğitim hash'leri, tahmin, gerçekleşen, model iç durumu: seçilen hiperparametre, iç çapraz doğrulama skor tablosu, uyarılar). Ledger'ın sha256'sı deney günlüğüne yazılır.

Resmi koşuların ledger'ları "altın" (golden) olarak `tests/reference/macos_golden*/` altında saklanır ve `SHA256SUMS`/`MANIFEST.json` ile pinlenir. Testler backtest'i yeniden koşup ledger'ın **bayt bayt** aynı çıktığını sınar (`test_acceptance_backtest.py::test_4`, `test_faz1b_backtest.py`, `test_faz7_golden.py` …). Bu, "bugünkü kod hâlâ dondurulan modeli üreten koddur" garantisidir. Skor tabloları (`docs/MODELS.md`, `scores.json`'un backtest blokları) yeni koşu yapmaz; hep bu altın ledger'lardan üretilir.

### 6.5.6 Sızıntı noktaları ve onları yakalayan testler

Sızıntı birden çok yerden girebilir. Repo her birini ayrı yakalamaya çalışıyor:

| Sızıntı noktası | Önlem | Test / denetim |
|---|---|---|
| Eğitimde gelecekteki hedef | `target_session_date < p(k)`, `BacktestStop` | `test_acceptance_backtest.py::test_1` (351/351 fold'un eğitim hash'i legacy ledger'la aynı) |
| Ön işleme (ortalama/varyans) test arzını görür | Standartlaştırma fold içinde, yalnız eğitimle | Fable denetimleri: test arzının alanı değiştirilince fit bit-eşit kalıyor |
| Hiperparametre seçimi test arzını görür | İç çapraz doğrulama (LOOCV) yalnız eğitim kümesinde | Ledger'daki iç skor tabloları bağımsız betikle yeniden üretildi |
| Tavan PP satırlarında kesim sonrası gün | `pp_rows(unit, cutoff)`; `max(seans) < T` assert'i | `CeilingFold.max_session_date`, Fable: 87/87 fold'da max < T |
| Aynı gün listelenen arz | açık assert | `aynı gün sızıntısı` |
| Özellikte gelecek veri (f6: piyasa endeksi) | `hisTs < ref_date` olan kayıtlar okunur; `S0 < ref_date ≤ D_1` | `tests/test_market20.py` (ref_date ve sonrasına saçma değer koyunca sonuç değişmiyor) |
| Etiket alanının tahmin koduna sızması | Etiket alanları yalnız yükleyicide | `test_faz8_break.py::test_14c` (AST taraması), `test_registry_carries_no_outcome_fields` |
| Kodun sonuç dizinlerini okuması | — | Fable `runtime_file_trace`: backtest çalışırken `data/outcomes/`, `scores/` altından 0 okuma |
| 2026-08-19 sonrası verinin eğitime girmesi | Eğitim tablosu sabit, pinli | `test_guardrails.py::test_no_data_after_sequence_cutoff`, `test_faz1b_guardrails.py` |

Kaynak dosyalar: `borsai/backtest.py` (`plan_folds`, `plan_folds_pb`, `plan_ceiling_folds`, `run_backtest`), `borsai/survival.py` (`pp_rows`), `borsai/specs.py` (PLAN_*), `data/training_table.csv`, `tests/reference/`, `tests/test_acceptance_backtest.py`, `tests/test_faz1b_backtest.py`.

---

## 6.6 Metrikler

BorsAi üç tür çıktı üretir ve her türün kendi hata ölçüsü vardır:

| Çıktı | Ne tahmin ediliyor | Birincil metrik | İkincil |
|---|---|---|---|
| `return` (R̂_h) | h. gün getirisi (sayı) | MAE | MedAE, yön isabeti |
| `p_up` (p̂_h) | P(kapanış > arz fiyatı) | Brier | log-kayıp, 0.5 eşikli isabet |
| `S` (S_1..S_10) | P(L ≥ k), tavan serisi dağılımı | RPS | k ∈ {1, 3, 5, 10} için Brier, kalibrasyon |
| `P_close_ceiling_k` | P(D_k'da tavan kapanış) | Brier | — |

Ufuklar ve çıktılar asla birleştirilmez. "Genel doğruluk" diye tek bir sayı üretilmez (`SPEC_SCORING §7`).

Hepsi **kayıp** (loss) olarak tanımlanır: küçük olan iyidir. Aşağıdaki örneklerde NETGL arzının gerçek kaydını kullanıyorum (`registry/records/NETGL/…_65a39d7392dd.json`; gerçekleşen değerler `data/outcomes/NETGL.csv`). NETGL'de R_D5 = 0.0784, Y_D10 = 0 (10. gün arz fiyatının altında kapandı), L = 3 [ölçüldü].

### 6.6.1 MAE (ortalama mutlak hata)

```
MAE = (1/n) Σ_i |R̂_i − R_i|
```

**Sezgi:** Tahminler ortalamada gerçekten kaç puan saptı? Getiriler kesir olarak tutulur; 0.030 = 3 puan (yüzde puanı).

**Örnek (tek arz, NETGL D5):**
- `v1_5_h99` tahmini R̂ = 0.2552 → |0.2552 − 0.0784| = **0.1768**
- `base_train_median` (eğitim medyanı) tahmini 0.3738 → |0.3738 − 0.0784| = **0.2955**
- Fark (model − kural) = 0.1768 − 0.2955 = **−0.1187** → bu arzda model 11.9 puan daha az yanıldı.

MAE'nin karşılaştırıldığı kurallar: `base_always_ceiling` (her gün tavan: R̂ = 1.1^h − 1, D5'te 0.61051), `base_train_median`, `base_train_mean`, `base_zero` (R̂ = 0).

**MedAE** (medyan mutlak hata) aykırı değerlere daha az duyarlıdır; ikincildir. Backtest günlüğünde ayrıca RMSE ve fiyat düzeyinde MAPE de hesaplanır (`metrics.regression_metrics`), ama hüküm hücrelerine girmez.

**Yön isabeti:** işaret(R̂) > 0 ile Y_h aynı mı? Skorda "kaçırma" olarak (`loss_dir_miss` = 1 − isabet) ve her zaman "her zaman tavan" kuralının yön isabetiyle yan yana gösterilir. İsabet oranı hiçbir yerde tek başına gösterilmez; yanıltıcıdır, çünkü arzların çoğu yukarı gittiği için "hep yukarı" demek bile yüksek isabet verir.

### 6.6.2 Brier skoru

```
Brier = (1/n) Σ_i (p̂_i − y_i)²        y_i ∈ {0, 1}
```

**Sezgi:** Olasılık tahmininin karesel hatası. "%90 yukarı" dediniz ve aşağı gittiyse (y = 0) kaybınız 0.81; "%50" dediyseniz 0.25. Brier hem *ayrım gücünü* (olanla olmayanı ayırma) hem *kalibrasyonu* (dediğiniz olasılıkların tutması) ödüllendirir. 0 mükemmel, 0.25 "hep %50 de" düzeyi, 1 tamamen yanlış ve emin.

**Örnek (NETGL D10, y = 0):**
- `v1_5_h99`: p̂ = 0.6023 → (0.6023 − 0)² = **0.3628**
- `base_rate` (eğitim kümesinde D10'da yukarı kapananların oranı): p̂ = 0.7071 → **0.4999**
- `base_last10_rate` (son 10 eğitim arzının oranı): p̂ = 0.5 → **0.25**
- Model − base_rate = −0.137 (model iyi); model − last10 = +0.113 (kural iyi). Tek arzda ikisi de bir şey kanıtlamaz; bu yüzden n ve aralık gerekir.

**Kırpma:** Olasılığı [0.01, 0.99]'a kırpma (`metrics.PROB_CLIP`) yalnız **backtest** tablolarında p_up Brier ve log-kayıp için uygulanır; Faz 1A'nın legacy benchmark'ı böyle tanımlandığı için korundu (SPEC_DEVIATIONS C7). **Canlı** skorlamada Brier kırpmasızdır (`scores.json` → `definitions.live_brier_clip = null`; E12). Tavan çıktılarının (S_k, P_close) Brier ve RPS'i her yerde kırpmasızdır. Aynı adlı metriğin iki terazide küçük bir tanım farkı taşıması bilinçli bir seçimdir; her hücre hangi teraziye ait olduğunu (`scale` alanı) taşıdığı için karışmaz.

### 6.6.3 Log-kayıp (log-loss)

```
LogLoss = −(1/n) Σ_i [ y_i·ln(p̂_i) + (1 − y_i)·ln(1 − p̂_i) ]
```

**Sezgi:** Gerçekleşen olaya verdiğiniz olasılığın negatif logaritması. Emin olup yanılmayı Brier'den çok daha sert cezalandırır: gerçekleşen olaya 0 olasılık verdiyseniz kayıp sonsuzdur.

**Örnek (NETGL D10, y = 0):** model −ln(1 − 0.6023) = **0.922**; base_rate −ln(0.2929) = **1.228**; "her zaman tavan" kuralı p̂ = 1 der, y = 0 için −ln(0) = ∞ olurdu.

Bu yüzden log-kayıpta olasılık kırpılır: canlıda p ∈ [1e-6, 1 − 1e-6] (`scoring.LOGLOSS_CLIP`; "her zaman tavan" kuralının kaybı −ln(1e-6) ≈ 13.8 olur), backtest'te [0.01, 0.99]. Log-kayıp ikincildir.

### 6.6.4 RPS (Ranked Probability Score)

Tavan modelleri tek bir olasılık değil, bütün bir dağılım verir: S_k = P(L ≥ k), k = 1..10 ("en az 1 gün tavan", "en az 2 gün"…). Gerçekleşen ise tek bir sayıdır: L. Bunları karşılaştırmak için:

```
RPS = (1/10) Σ_{k=1..10} ( S_k − 1[L ≥ k] )²
```

**Sezgi:** Her eşik k için "L en az k mı?" diye bir evet/hayır sorusu kurun, her birinin Brier'ini alın ve ortalayın. Bu, sıralı sonuçlar için doğru bir ölçüdür: L = 3 iken "4" diyen bir dağılım, "9" diyenden daha az cezalandırılır; çünkü eşiklerin çoğunda doğru tarafta olasılık verir.

Sınır durumları (`SPEC_SCORING §10-11`, `test_scoring.py::test_11_rps`): S tam olarak 1[L ≥ k] ise RPS = 0; "her zaman tavan" (S ≡ 1) ve L = 0 ise RPS = 1; L = 10 ise "her zaman tavan"ın RPS'i 0.

**Örnek (NETGL, L = 3; gösterge vektörü 1,1,1,0,0,0,0,0,0,0) [ölçüldü]:**

| k | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v0` S_k | .818 | .705 | .608 | .406 | .271 | .181 | .121 | .081 | .054 | .036 |
| terim (S_k − 1[L≥k])² | .033 | .087 | .153 | .165 | .074 | .033 | .015 | .007 | .003 | .001 |
| `base_km_expanding` S_k | .818 | .707 | .667 | .535 | .414 | .333 | .273 | .212 | .172 | .141 |
| terim | .033 | .086 | .111 | .287 | .172 | .111 | .074 | .045 | .030 | .020 |

RPS: `ceiling_hazard_v0` **0.057**, `base_km_expanding` **0.097**, `base_km_last10` 0.124, `ceiling_hazard_v0@INF` 0.095. Fark (model − KM genişleyen) = −0.040. Kaplan–Meier (KM) kuralları, geçmiş arzların seri uzunluklarının deneysel dağılımıdır (özellik kullanmaz); `@INF` aynı hazard kodunun özelliksiz (yalnız sabit terimli) sürümüdür.

### 6.6.5 Kalibrasyon

**Sezgi:** "%70" dediğiniz olaylar gerçekten aşağı yukarı %70 oranında oluyor mu? İyi ayırt eden ama sistematik olarak iyimser bir model kötü kalibre olabilir.

Repoda kalibrasyon bir hüküm değil, betimleyici bir satırdır: ortalama tahmin ile gözlenen oran yan yana yazılır. Backtest'te `compute_ceiling_metrics` ortalama S_1 ile gözlenen D1 tavan oranını raporlar; canlıda `live.descriptive` listesi ortalama S_k ile gözlenen P(L ≥ k)'yı verir (E13); kasa skorlarında düşen arz modelleri için "ort. P(D10 kapanışı ≤ arz) ve gözlenen oran" bilgi satırları var. Bağımsız denetimden bir gözlem örnek olsun: backtest'te tavan modelleri ve KM kuralları iyimser çıkmış (ort. S_1 0.866, gözlenen 0.816); nedeni tavan oranının yıllar içinde düşmesi ve walk-forward'ın doğal gecikmesi (`docs/fable_conformity_20260922/AUDIT.md` özet 9).

### 6.6.6 Eşleşik fark ve kazanç/kayıp/eşit sayımı

Modelin MAE'si 0.22 demek tek başına bir şey söylemez; zor bir dönemde her yöntem yüksek hata yapar. Bu yüzden BorsAi her modeli **aynı arzlarda** bir kuralla karşılaştırır ve her arz için fark alır:

```
d_i  = kayıp_model(i) − kayıp_kural(i)          (negatif = model iyi)
fark = (1/n) Σ d_i
```

"Eşleşik" (paired) olmanın iki faydası var: (1) Yalnız ikisinin de skorlandığı arzlar sayılır (model bir arzı reddettiyse o arz karşılaştırmadan düşer); (2) arzdan arza değişen zorluk farkta büyük ölçüde birbirini götürür, bu yüzden aralık daha dar çıkar.

Her hücre ayrıca üç sayım taşır:
- **kazanç** (`wins` / `model_better_n`): d_i < 0 olan arz sayısı,
- **kayıp** (`losses` / `rule_better_n`): d_i > 0,
- **eşit** (`ties`): d_i = 0 (tam eşitlik; ör. iki model aynı değeri verdiyse).

Örnek: `v1_5_h99` D5 MAE − medyan hücresinde 87 arzın 58'inde model, 29'unda kural daha az yanılmış, eşit 0 [ölçüldü]. Kazanç sayımı, ortalamanın birkaç uç arz tarafından mı sürüklendiğini görmeye yarar.

Kod: backtest için `metrics.paired_difference` (+ `report.paired`, `report_faz1b.paired`, `backtest.paired_ceiling`), canlı ve zaman-dışı için `scoring.paired_metric` (`PairedObs` nesneleri).

Kaynak dosyalar: `borsai/metrics.py`, `borsai/rules.py`, `borsai/scoring.py` (`loss_*`, `paired_metric`), `borsai/survival.py` (`rps`), `borsai/backtest.py` (`compute_metrics`, `compute_ceiling_metrics`), `docs/specs/SPEC_SCORING.md` §7.

---

## 6.7 Belirsizlik: blok bootstrap ve %95 aralık

### 6.7.1 Neden aralık?

87 arzda ortalama fark −0.084 çıktı. Başka bir 87 arzlık dönemde de aynısı çıkar mıydı? Ortalama fark rastlantıya bağlı bir sayıdır. **%95 güven aralığı**, "bu yöntemi tekrar tekrar uygulasaydık, gerçek farkı yakalayan aralıkların oranı yaklaşık %95 olurdu" anlamına gelen bir belirsizlik bandıdır. Aralık tamamen 0'ın altındaysa "model gerçekten iyi" demeye yeterli kanıt var sayılır; 0'ı içeriyorsa fark gürültüden ayırt edilemez.

### 6.7.2 Bootstrap

Aralığı formülle (ör. normal dağılım varsayımıyla) hesaplamak yerine **bootstrap** kullanılır: Elimizdeki örneğin "dünyayı temsil ettiğini" varsayıp ondan yerine koyarak (iadeli) yeni örnekler çekeriz ve her birinde ortalamayı hesaplarız. 4000 böyle ortalamanın dağılımı, gerçek ortalamanın ne kadar oynayabileceğini gösterir. %95 aralık, bu 4000 değerin en küçük %2.5'ini ve en büyük %2.5'ini kesip atınca kalan aralıktır.

### 6.7.3 Neden blok?

Sıradan bootstrap arzları tek tek bağımsız sayar. Ama arzlar bağımsız değil:
- **Pencereler çakışıyor:** Bir arzın 10 günlük penceresi ortalama 4 komşu arzınkiyle çakışıyor (şartnamenin ilk denetimden, AUDIT §2.5'ten aktardığı değer). Aynı haftanın piyasa havası hepsini birlikte etkiler.
- **Rejim değişiyor:** Tavan oranı ve getiriler yıldan yıla değişiyor.

Bağımlı gözlemleri bağımsızmış gibi saymak, "elimde 87 bağımsız kanıt var" yanılgısına, yani **fazla dar** aralığa yol açar. Çözüm: Birbirine bağlı gözlemleri birlikte çekmek. BorsAi'de blok = gerçekleşen ilk işlem gününün **takvim ayı** (`YYYY-MM`). Aynı ay listelenen arzlar hep birlikte çekilir ya da hiç çekilmez.

### 6.7.4 Algoritma

```
d   = eşleşik farklar (arz başına), blok = ilk işlem ayı
ids = farklı aylar (m tane)
4000 kez tekrarla:
    m ay çek (iadeli, her ay eşit olasılıkla)
    çekilen ayların BÜTÜN farklarını birleştir
    istatistik = birleşik listenin ortalaması
4000 istatistiği sırala
aralık = [ sıralı[100], sıralı[3899] ]          (0'dan sayan indeks)
```

**Neden 100 ve 3899?** 4000 değerin %2.5'i 100 değerdir. 0'dan sayan indekste 100. eleman, en küçük 100 değerden sonraki ilk değerdir (alt sınır). %97.5 noktası 3900'üncü değerdir; 0'dan sayan indeksi 3899'dur (üst sınır). Kod: `metrics.BOOTSTRAP_LO_INDEX = 100`, `BOOTSTRAP_HI_INDEX = 3899`.

**Tohum (seed) 20260921:** Rastgelelik sabit tohumla başlatılır; aynı girdi her koşuda aynı aralığı verir (`test_metrics.py`, `test_scoring.py::test_8a`). Her karşılaştırma kendi üreticisini sıfırdan kurar; sonuç çağrı sırasına bağlı değildir (`test_paired_difference_is_independent_of_call_order`).

**Koşullar:** n ≥ 10 ve en az 6 farklı blok (ay). Sağlanmazsa aralık **üretilmez** ("aralık için yetersiz").

### 6.7.5 İki uygulama: backtest ve canlı

Şartname (`SPEC_SCORING §8`) numpy `PCG64(20260921)` üreticisini ve yüzdelik [2.5, 97.5] hesabını yazıyordu. Uygulamada iki yol var:

| | Backtest hücreleri | Canlı ve zaman-dışı hücreler |
|---|---|---|
| Kod | `metrics.block_bootstrap_ci` | `scoring.block_bootstrap_ci` |
| Üretici | Python `random.Random(20260921)`, `rng.choices` | numpy `Generator(PCG64(20260921))`, `rng.choice` |
| Blok sırası | ilk görünüş sırası | sıralı |
| Aralık | sıralı[100], sıralı[3899] | `np.percentile(…, [2.5, 97.5])` |
| Gerekçe | Faz 1A'nın legacy benchmark'ıyla (AUDIT §1.2-c) aynı yöntem; MODELS.md tabloları kendi içinde karşılaştırılabilir kalsın | şartname §8 aynen |

Bu ayrım `docs/SPEC_DEVIATIONS.md` C7 ve E12'de belgelidir. `scores.json`'da her backtest hücresi `"bootstrap": "random.Random(20260921), ilk işlem ayı blokları, 4000 tekrar (SPEC_DEVIATIONS C7)"` notunu taşır; canlı tanımlar ise `definitions.bootstrap_live = {B: 4000, generator: "numpy PCG64", seed: 20260921, percentiles: [2.5, 97.5], block: "gerçekleşen D_1'in takvim ayı"}` bloğundadır. İki yöntem aynı terazide hiç karışmaz. Farklı rastgele sayı üreticileri farklı çekilişler yaptığı için uçlar biraz oynar, hüküm genelde değişmez: aşağıdaki örnek hücreye canlı yöntemi (numpy PCG64) uygulayınca aralık [−0.1360, −0.0286] çıkıyor, backtest yöntemiyle [−0.1343, −0.0321] [ölçüldü]. İkisi de tamamen 0'ın altında.

### 6.7.6 Örnek: `v1_5_h99`'un birincil hücresi

`v1_5_h99` D5 MAE − `base_train_median` hücresini altın ledger'lardan (`tests/reference/macos_golden/`) kendi betiğimle yeniden hesapladım (`borsai` import etmeden) [ölçüldü]:

| Değer | Benim hesabım | `scores.json` |
|---|---|---|
| n / blok | 87 / 23 | 87 / 23 |
| model MAE / kural MAE | 0.2220 / 0.3059 | 0.2220 / 0.3059 |
| fark | −0.08387 | −0.0839 |
| %95 aralık (blok, `random.Random`) | [−0.13432, −0.03211] | [−0.1343, −0.0321] |
| kazanç / kayıp / eşit | 58 / 29 / 0 | 58 / 29 / 0 |

Aralık tamamen 0'ın altında ve n ≥ 30 → hüküm **"geçiyor"**.

Karşılaştırma için aynı farkları blok kullanmadan (arz arz, iid) bootstrap'ledim: aralık [−0.1288, −0.0428], genişlik 0.086. Blok aralığının genişliği 0.102, yani yaklaşık %19 daha geniş [ölçüldü]. Bazı aylarda 7–12 arz birden var; blok yöntemi bu kümelenmeyi hesaba katıp aralığı genişletiyor. Bu örnekte hüküm değişmiyor, ama sınırdaki hücrelerde blok yöntemi yanlış bir "geçiyor"u önleyebilir.

Bir de kabul testi: `test_scoring.py::test_8b` canlı bootstrap kodunu (numpy) H99'un D1 MAE (V1.5 − medyan) farkına uygular ve ilk denetimdeki +0.0046 [+0.0015, +0.0079] değerini ±0.001 içinde yeniden üretmesini ister.

Kaynak dosyalar: `borsai/metrics.py` (`block_bootstrap_ci`, `paired_difference`), `borsai/scoring.py` (`block_bootstrap_ci`, `paired_metric`), `docs/specs/SPEC_SCORING.md` §8–§9, `docs/SPEC_DEVIATIONS.md` C7, E12, `tests/test_metrics.py`, `tests/test_scoring.py`.

---

## 6.8 Hüküm dili ve küçük n kuralları

Sayıların nasıl *söylendiği* de kurala bağlı. `scoring.verdict(n, ci)`:

```
n < 10                       → hüküm yok (null); YALNIZ satır tablosu
10 ≤ n < 30                  → "yetersiz örnek"  (metrik, fark ve varsa aralık gösterilir)
n ≥ 30 ve aralık yok         → "aralık için yetersiz"   (ör. 6'dan az ay)
n ≥ 30 ve üst uç < 0         → "geçiyor"
n ≥ 30 ve alt uç > 0         → "geçemiyor"
n ≥ 30 ve aralık 0'ı içerir  → "ayırt edilemiyor"
```

Ayrıntılar:
- **"Geçiyor" başka hiçbir koşulda kullanılmaz.** Noktasal fark tek başına hüküm değildir. `test_scoring.py::test_9e` kelime dağarcığının bu değerlerle sınırlı olduğunu, `test_9a` aralık 0'ı içerince metnin "ayırt edilemiyor" dediğini sınar.
- **n < 10'da metrik alanları boştur.** `paired_metric` n < 10 iken `model_value`, `rule_value`, `diff`, `ci95`, `wins`… alanlarını `null` yazar (`test_9b`). Canlı panelde yalnız arz arz tablo (arz, sınıf, tahmin, gerçekleşen, her kuralın tahmini) görünür; ortalama ve renk yoktur (`test_9c`, `test_scores_doc_has_no_live_verdict_or_average`).
- **10 ≤ n < 30**'da kazanan vurgusu yoktur; her zaman "yetersiz örnek" (E11).
- **Zaman-dışı terazide** hüküm terazinin adıyla birlikte yazılır: "geçiyor (zaman-dışı terazide)" (`scoring.OOT_V_PASS`), okuyucu bunu backtest ya da canlı başarısıyla karıştırmasın diye.
- Panel başlıkları sabittir: backtest "Geçmiş veri testi (retrospektif, tasarıma maruz)", canlı "Canlı sicil (prospektif, n = k; atlanan = s)". "Tasarıma maruz" ifadesi şunu hatırlatır: H99, modellerin tasarlandığı veridir; orada iyi olmak beklenir, kanıt değeri sınırlıdır.

Bugünkü durum: Canlı sicilde en çok 7 arz skorlandı. Bu yüzden `scores.json`'daki bütün canlı bloklarda `cells: []`; `docs/SCORES.md` "Canlı tarafta YALNIZ satır tablosu vardır: metrik, ortalama, fark, aralık ya da hüküm üretilmez" diyor [ölçüldü].

**Yakın dönem etiketleri (Faz 7 ve 7C).** Yeni model ailelerinde backtest'e ek bir hücre tanımlandı: yalnız ilk işlem günü ≥ 2024-01-01 olan fold'larda yeni model − eski model. Burada soru "yeni model eskisini bozuyor mu?" olduğu için dil farklıdır (`backtest.near_era_label`, sonuçlar görülmeden yazıldı):

```
alt uç > 0           → "bozuyor"
üst uç ≤ δ           → "tolerans içinde"     (δ = 0.010 RPS; düşen arz modellerinde 0.008 Brier)
aksi / aralık yok    → "belirsiz"
```

Örnek [ölçüldü, `scores.json` → `models[].backtest.near_era`]: `ceiling_hazard_v1_clip` −0.0011 [−0.0066, +0.0049] → "tolerans içinde"; `_real` +0.0104 [+0.0028, +0.0183] → "bozuyor"; `_pooled` +0.0289 [+0.0089, +0.0518] → "bozuyor" (n = 78, 22 ay).

Kaynak dosyalar: `borsai/scoring.py` (`verdict`, `V_*`, `MIN_N_*`, `OOT_V_PASS`), `borsai/backtest.py` (`near_era_label`, `near_era_label_fall`), `docs/SPEC_DEVIATIONS.md` E10–E11, `tests/test_scoring.py`.

---

## 6.9 Çoklu karşılaştırma, birincil hücre ve ön kayıt

### 6.9.1 Sorun

`v1_5_h99`'un backtest bloğunda 28 hücre var: 4 ufuk × (4 getiri kuralı + 3 olasılık kuralı). Bunların 15'i "geçiyor", 2'si "geçemiyor", 11'i "ayırt edilemiyor" [ölçüldü]. "Geçemiyor" olan ikisi D1'de medyana ve "her zaman tavan"a karşı: ilk gün kapanışı çoğu arzda tavan olduğu için iki kural da yaklaşık +0.10 der ve modelden az yanılır (çıkarım). Bütün modellerde backtest hücresi sayısı 293; bunlardan 168'i "geçiyor" [ölçüldü].

Her hücre %95 aralıkla değerlendirilse bile, gerçekte fark sıfır olan 20 hücreden yaklaşık biri şans eseri "geçiyor" der. Çok hücreye bakıp en iyisini seçmek, şansı başarı sanmaktır. Buna **çoklu karşılaştırma sorunu** (ya da "çatallanan yollar bahçesi") denir. Ayrıca hücreler bağımsız değildir; aynı arzlarda, birbirine benzeyen kurallara karşı ölçülürler.

### 6.9.2 Çözüm: önceden ilan edilmiş birincil hücre

Her model için, **sonuçlar görülmeden** tek bir hücre seçilir ve modelin "başarılı" sayılıp sayılmayacağına yalnız o hücre karar verir. Diğer bütün hücreler **"keşif"** etiketiyle gösterilir: bilgi verir, hüküm vermez. Birincil hücreler `scoring.PRIMARY_CELLS`'te (ve sonraki fazların ayrı sözlüklerinde) sabittir ve testlerle pinlidir:

| Model | Birincil hücre |
|---|---|
| `v1_5_h99` | D5 getiri MAE − `base_train_median` |
| `pb_v0` | D5 getiri MAE − `base_train_median` |
| `v1_5_market20_v0` | D5 getiri MAE − `v1_5_h99` |
| `v1_6_h99` | D10 getiri MAE − `v1_5_h99` |
| `ceiling_hazard_v0`, `pb_ceiling_v0` | S RPS − KM kuralları (`base_km_last10`, `base_km_expanding`; zaman-dışında yalnız `base_km_expanding`) |
| `ceiling_path_v0` | D5 getiri MAE − `base_train_median` |
| `ceiling_hazard_v1_*` (Faz 7) | S RPS − `base_km_expanding` |
| `fall_d10_v0_*` (Faz 7C) | D10 p_up Brier − `base_rate` |
| `post_d1_hazard_v0` | j = 1 koşullu RPS − `ceiling_hazard_v0` |
| `break_floor_v0` | F1 Brier − `PRODUCT_BREAK_FLOOR` (yakın dönem) |

Bazı modellerin karşılaştırılanı bir kural değil, öncül modeldir (ör. `v1_6_h99`'un sorusu "V1.5'ten iyi mi?"). Faz 7 ve 7C'de ayrıca önceden ilan edilmiş **"ikincil"** hücreler vardır; bunlar da önceden yazılıdır ama hüküm vermez.

Backtest birincil hücrelerinin bugünkü durumu (`scores.json`) [ölçüldü]:

| Model | Hücre | n (ay) | Fark | %95 aralık | K/K/E | Hüküm |
|---|---|---|---|---|---|---|
| `v1_5_h99` | D5 MAE − medyan | 87 (23) | −0.0839 | [−0.1343, −0.0321] | 58/29/0 | geçiyor |
| `v1_6_h99` | D10 MAE − v1.5 | 87 (23) | +0.0008 | [−0.0003, +0.0028] | 28/31/28 | ayırt edilemiyor |
| `v1_5_market20_v0` | D5 MAE − v1.5 | 87 (23) | −0.0008 | [−0.0178, +0.0137] | 40/47/0 | ayırt edilemiyor |
| `pb_v0` | D5 MAE − medyan | 87 (23) | −0.0355 | [−0.0775, +0.0102] | 56/31/0 | ayırt edilemiyor |
| `ceiling_hazard_v0` | RPS − KM genişleyen | 87 (24) | −0.0569 | [−0.0833, −0.0286] | 59/28/0 | geçiyor |
| `ceiling_hazard_v0` | RPS − KM son-10 | 87 (24) | −0.0496 | [−0.0751, −0.0219] | 52/35/0 | geçiyor |
| `pb_ceiling_v0` | RPS − KM genişleyen | 87 (23) | −0.0324 | [−0.0544, −0.0114] | 61/26/0 | geçiyor |
| `pb_ceiling_v0` | RPS − KM son-10 | 87 (23) | −0.0335 | [−0.0612, −0.0019] | 50/37/0 | geçiyor |
| `ceiling_path_v0` | D5 MAE − medyan | 85 (23) | −0.1158 | [−0.1611, −0.0738] | 63/22/0 | geçiyor |

(K/K/E: kazanç/kayıp/eşit.) Bunların hepsi "tasarıma maruz" backtest terazisindedir; asıl kanıt değeri zaman-dışı ve canlı teraziden gelir (§6.10, §6.12).

### 6.9.3 Ön kayıt (pre-registration)

Birincil hücre fikri daha genel bir ilkenin parçasıdır: **ön kayıt**. Bir model uygulanmadan önce şartnamesi (Fable'ın yazdığı `SPEC_*.md`) yazılır, commit edilir ve push edilir. Şartname modelin tanımını, fold planını, birincil hücreyi ve **önceden yazılmış beklentiyi** içerir (ör. "fark −0.005 ile −0.02 arasında olmalı"). Git geçmişinde bu desen sürekli tekrarlanır: `d3fabad` (Faz 1 şartnameleri) → `b09cab5` (uygulama); `52e1567` → `2d0c98e` (Faz 4); `c20c092` → `7ce0593` (Faz 5); `6a16c16` → `2a21a96` (Faz 7); `4fe4e51` → `3c93f9c` (Faz 7C); `7d78d43` → `fa623df` (Faz 8). Şartname commit'i uygulama commit'inin atasıdır ve push kanıtlıdır.

Beklentilerdeki sözel ifadeler ("çoğu", "≈ 0", "hafif kötü") yorum tartışması doğurmasın diye sayıya çevrilir: `report_faz1b.OPERATIONAL_RULES` (ör. MAE farkında "≈ 0" = |fark| belirli bir eşiğin altında; "ayırt edilemez" = aralık 0'ı içeriyor). Bu kurallar da sonuç görülmeden yazıldı ve MODELS.md'de basılı (SPEC_DEVIATIONS C8). Sonraki fazlarda rapor kodu şartnamenin beklenti tablosunu dosyadan **aynen** okur (`test_report.py::test_expectations_are_verbatim_quotes`).

### 6.9.4 "Beklentiden çok iyi" freni

Beklenti tutmadığında ne olur? İki yön de ilginçtir:
- **Beklentiden kötü:** Beklenti, modeli değiştirme gerekçesi değildir (CLAUDE.md kural 5); yalnız yeni bir model kimliği için bilgidir.
- **Beklentiden çok iyi:** Bu bir alarmdır. Gerçekçi olamayacak kadar iyi sonuç çoğu zaman sızıntıdan ya da hatadan gelir. Şartnameler bu durumda modelin, ilk uygulamayı görmemiş ayrı bir oturumda sıfırdan yeniden üretilmesini zorunlu kılar.

Gerçek örnek: Faz 4 tavan yolu modelinin birincil hücresi −0.1158 [−0.1611, −0.0738] çıktı; aralığın üst ucu şartnamedeki −0.060 eşiğinin altında kaldığı için "beklentiden çok iyi" kuralı tetiklendi. Commit `2d0c98e`'in başlığı bunu yazıyor: "NOT frozen (spec §6 better-than-expected check triggered, independent reproduction required)". Fable, `borsai`'yi import etmeyen bağımsız bir betikle 870 hücreyi yeniden üretti (maks |Δ| = 0), sızıntı aradı, bulamadı ve FREEZE_OK verdi; modeller ancak bundan sonra donduruldu (`a0df5b7`).

### 6.9.5 Varyant sayacı

Çoklu karşılaştırmayı tamamen yok etmek mümkün değil, ama görünür kılmak mümkün. Her model kartı `n_variants_same_data` taşır: deney günlüğünde **aynı veri sürümüyle** koşulmuş farklı (model_id, spec_sha256) çiftlerinin ve keşif satırlarının sayısı (SPEC_DEVIATIONS E16; duyarlılık satırları sayılmaz). `v1_5_h99`'un kartında bu sayı 23 (skorlar 2026-10-01'de üretildi); günlüğü bugün sayınca 24 çıkıyor, 24'üncü varyant 2026-10-02'deki Faz 8 resmi koşusu (`break_floor_v0`) [ölçüldü]. Anlamı: "Bu veri üzerinde şimdiye dek 23 farklı şey denendi; bu modelin başarısını bu bağlamda okuyun."

Kaynak dosyalar: `borsai/scoring.py` (`PRIMARY_CELLS`, `FAZ7_*`, `FAZ7C_*`, `_label`, `_n_variants_same_data`), `borsai/report_faz1b.py` (`OPERATIONAL_RULES`), `docs/specs*/`, `docs/MODELS.md`, `scores/scores.json`.

---

## 6.10 Üç terazi ve canlı sınıflar

### 6.10.1 Üç terazi

| Terazi | Ne | Kanıt gücü | Zayıf yanı |
|---|---|---|---|
| **Backtest** (retrospektif walk-forward) | H99'un 99 arzında, her fold'da yalnız geçmişle eğitilmiş modelin tahmini | En büyük n (≈ 87), hemen elde | Modeller bu veriye bakılarak tasarlandı ("tasarıma maruz"); seçim yanlılığı |
| **Canlı** (prospektif) | Model dondurulduktan *sonra* listelenen arzlar; tahmin sonuçtan önce push edildi | En dürüst kanıt | n çok küçük (bugün en çok 7), yavaş büyür (ayda birkaç arz) |
| **Zaman-dışı** (OOT, eski kohort) | 2020–2023 arasındaki 135 arz; donmuş modellerle tahmin edildi, tahminler sonuç repoya girmeden push edildi | Tasarıma maruz değil, n orta büyüklükte | Dönem eğitimden *önce*; kural rejimi farklı; kayıt anı D_1'den yıllar sonra |

**Neden asla toplanmazlar?** Her birinin farklı bir yanlılığı var. Backtest ile canlıyı toplarsanız 87 "tasarıma maruz" arz, 7 "gerçekten ileriye dönük" arzı boğar ve ortaya çıkan sayı aslında backtest sayısıdır ama "canlı dahil" etiketiyle sunulur. OOT ile canlıyı toplarsanız "gelecekte işe yarar mı" sorusu "geçmişin başka bir döneminde işe yarar mıydı" sorusuyla karışır. Her terazi kendi sorusuna cevap verir.

**Kodla zorlama:** Her gözlem (`PairedObs`) ve her blok bir `scale` alanı taşır. `scoring._one_scale` farklı ölçekli gözlemler aynı metrik hesabına girerse `ScaleMixError` fırlatır; aynı koşullu tabloda farklı j'ler (seri günleri) karışırsa da. `scoring.merge_scales` adlı fonksiyon, blokları birleştirmeye çalışan her çağrıyı **her durumda** reddeder; varlık nedeni, birleştirme girişiminin sessizce çalışmasını imkânsız kılmaktır (`test_scoring.py::test_9d_scales_never_combined`). Zamanla ölçek sayısı arttı ve hepsi aynı kurala tabi: `backtest`, `backtest_near_era`, `live`, `live_conditional` (j başına), `live_post_d1`, `live_break`, `OOT_PRE_H99`, `OOT_PRE_H99_POST_D1_MACHINE_SEQUENCED`. Dosyalar da ayrı: `scores.json`, `scores_post_d1.json`, `scores_break.json`, `scores_oot.json`.

### 6.10.2 Canlı sınıf formülü

Bir (model, arz) çiftinin canlı sicilde hangi sınıfa girdiği elle yazılmaz, her skorlamada yeniden hesaplanır (`SPEC_SCORING §5`, `scoring.pair_class`):

```
commit_frozen(m)          = models/<m>.json dosyasını EKLEYEN commit
outcome_ingest_commit(a)  = min( data/outcomes/<a>.csv'yi ekleyen commit,
                                 D_1(a)…D_10(a) tarihli herhangi bir THB/THM zip'ini ekleyen ilk commit )

model_prospective(m, a) = is_ancestor(commit_frozen(m), outcome_ingest_commit(a))
                          VE commit_frozen(m) için push kanıtı var
record_live(m, a)       = push_kanıtı(kaydı ekleyen commit).created_at [İstanbul tarihi] < D_1(a)
inputs_pit_ok(kayıt)    = her dolu girdi alanının kaynağı D_1'den önce yayımlanmış,
                          belge sha256'sı eşleşiyor; f6 için S0 < ref_date ≤ D_1

sınıf = LIVE         eğer model_prospective VE record_live
      = LATE_RECORD  eğer model_prospective VE değil record_live VE inputs_pit_ok
      = RETRO        aksi halde
```

Önemli incelikler:
- **Bülten neden "sonuç" sayılıyor?** Günlük THB bülteni o gün işlem gören *bütün* payları taşır. Bir tarihin zip'i repoya girdiği an, o gün işlem gören her arzın o günkü sonucu da girmiş sayılır. Bu yüzden `outcome_ingest_commit` yalnız arzın sonuç dosyasına değil, onun penceresindeki her bültene de bakar ve en erkenini alır.
- **Sonuç henüz commit edilmediyse** sınıf HEAD'e karşı denetlenir: sonuç commit'i HEAD'in torunu olacağından, HEAD'in her atası onun da atası olur (E15). Satırın `class_evidence.outcome_ingest_basis` alanı bunu yazar (`COMMITTED` ya da `UNCOMMITTED_CHECKED_AGAINST_HEAD`).
- **LATE_RECORD'ın anlamı:** Model sonuçtan önce donmuş (parametreler sonucu görmemiş), `predict` deterministik; ama kayıt D_1'den sonra yapılmış. Açık kalan tek kanal girdi toplayanın sonucu biliyor olması; bu yüzden `inputs_pit_ok` zorunlu ve satırın etiketi görünür. Canlı terazi = LIVE ∪ LATE_RECORD, ama her zaman `n_live / n_late` kırılımıyla.
- **RETRO** yalnız bilgi listesindedir (`retro_info`), hiçbir n'e girmez. H99'un 99 arzı her model için RETRO'dur.
- **Push kanıtı olmayan model** için hiçbir arz prospektif değildir.

Sınıflama kabul testleri geçici git depolarında beş senaryoyu kurar (`test_scoring.py::test_5a…5e`): (a) model → kayıt+kanıt → sonuç ⇒ LIVE; (b) model → sonuç, kayıt sonra ⇒ LATE_RECORD; (c) sonuç → model ⇒ RETRO; (d) push kanıtı yok ⇒ RETRO; (e) `inputs_pit_ok` yanlış ⇒ RETRO. `test_5i_no_hand_class_field_in_any_input` hiçbir girdi dosyasında elle yazılmış sınıf alanı olmadığını, `test_5j` `scores.json`'daki her sınıfın kanıtından yeniden hesaplandığını sınar.

### 6.10.3 Diğer satır türleri

| Tür | Anlamı | n'e girer mi? |
|---|---|---|
| `LEGACY_SELF_REPORTED` | Eski repodan gelen, zamanı yalnız kendi beyanına dayanan kayıt (push kanıtı yok). Model prospektifse bu sınıf, değilse RETRO; asla LIVE/LATE_RECORD değil (E8) | Hayır; ayrı alt satır, "+ self-reported" ikincil |
| Geçersiz kullanım (`invalid_use`) | f3'süz üç legacy V1.5 kaydı: model bugün o girdiyi RET ederdi | Hiçbir metriğe ve n'e girmez; gri gösterilir |
| `REFUSED` (uygulamada "RET") | Model girdiyi reddetti (ör. `F3_MISSING`: talep katı yok). Kayıt var, hücre "ret + neden" | `n_refused`; atlama değildir |
| `SKIPPED` | Arz için kayıt hiç yok (`NO_RECORD_BEFORE_LISTING`, `PUSH_PROOF_MISSING`, `INPUTS_NOT_AVAILABLE`) | `n_skipped` |
| `PENDING` | Kayıt var, sonuç henüz yok | `n_pending` |
| `TARGET_UNAVAILABLE` | 15 seansta hedef oluşmadı | `n_target_unavailable` |
| Ayrı model (`v1_5_full20`) | TKNKA'nın eski FULL20 kaydı başka bir eğitim kümesiyle; `v1_5_h99` sütununa yazılmaz | Kendi tek satırlık listesi, metrik yok |

Her canlı metrik yanında `n_scored / n_refused / n_skipped / n_target_unavailable` gösterilir (payda kuralı).

### 6.10.4 Bugünkü canlı sicil

`docs/SCORES.md` §2'den (skora giren son THB 2026-09-30) [ölçüldü]:

- 7 arz × 16 Faz 1 modeli: **LATE_RECORD**. Modeller (`5fa849d`, `b09cab5`) sonuçları getiren `f1f9d44`'ün atası ve push kanıtlı; ama tahmin kayıtları 2026-09-22'de yazıldı (`7cb49cf`, kanıt 14:06:05Z), yani bütün arzların ilk işlem gününden sonra.
- **NETGL × `v1_5_h99`: LIVE**, legacy kayıt `NETGL_20260916_V1_5` sayesinde: eski repo commit'i `5f70ace…`, push kanıtı 2026-09-16T11:32:27Z, D_1 = 2026-09-17. Bu, sicilin bugünkü tek LIVE hücresi.
- BKRGY ve INTET için `v1_5_h99`'un post-bookbuild legacy kayıtları `LEGACY_SELF_REPORTED`.
- VEYAS: f3 yok, dört f3'lü model (`v1_5_h99`, `v1_6_h99`, `v1_5_market20_v0`, `ceiling_hazard_v0`) `REFUSED` (`F3_MISSING`).
- Faz 4 sonrası donmuş 11 model × 7 arz = 77 çift **RETRO** (`retro_info`): bu modeller arzların sonucu repoya girdikten sonra donduruldu; kayıtları da yok.
- POST_D1 (`scores_post_d1.json`) ve kırılma akşamı (`scores_break.json`) sicillerinde 7'şer satırın hepsi RETRO, `n_scored = 0`.

Sonuç: `v1_5_h99` için n_rows 7, n_scored 6 (1 LIVE + 5 LATE), n_refused 1. n < 10 olduğu için hiçbir canlı hücre yok.

Kaynak dosyalar: `borsai/scoring.py` (`classify`, `pair_class`, `outcome_ingest_commit`, `ScaleMixError`, `merge_scales`, `live_block`), `borsai/registry.py` (`Candidate`), `scores/scores.json`, `scores/scores_post_d1.json`, `scores/scores_break.json`, `docs/SCORES.md`, `registry/legacy_roles.json`, `tests/test_scoring.py`.

---

## 6.11 Dondurma ve kayıt akışı

Bu bölüm bir tahminin "resmi" hale gelmesinin adımlarını anlatır.

### 6.11.1 Model dondurma

`python -m borsai.freeze --models <model_id> …` modeli H99 verisiyle nihai olarak fit eder ve `models/<model_id>.json` dosyasına yazar. Model dizinleri (indeksleri) üç ayrı dosyadır; çünkü her aşamanın kaydı yalnız kendi dizinindeki modelleri içerir:

| Dizin | Aşama | Bugünkü model sayısı | sha256 (ilk 16) |
|---|---|---|---|
| `models/INDEX.json` | listeleme öncesi | 27 | `7e636e8bf64b25d7` |
| `models/INDEX_POST_D1.json` | D1 sonrası | 1 (`post_d1_hazard_v0`) | `94ac36faffac6017` |
| `models/INDEX_POST_BREAK.json` | kırılma akşamı | 2 (`break_floor_v0`, `@ZERO`) | `899cf90c805d4531` |

[ölçüldü] Her dizin girdisi şunları taşır: `model_id`, `file`, `sha256` (parametre dosyasının), `algorithm`, `spec_sha256` (şartnamenin kanonik hash'i), `training_n`, `training_cutoff_date`, `training_tickers_sha256`, `data_version_sha256`, `frozen_at`, `frozen_at_basis`, `status: FROZEN`. POST_D1 girdisi ayrıca ebeveyn modeli (`parent_model_id = ceiling_hazard_v0`) ve onun sha'sını (`parent_sha256`) pinler.

Kurallar:
- **Üzerine yazma yok:** Kimlik dizinde ya da dosya diskte varsa `FreezeError("… zaten dondurulmuş; üzerine yazılmaz (yeni model_id gerekir)")`.
- **`frozen_at` kanıt değildir:** `frozen_at_basis` alanı bunu açıkça yazar: "LOCAL_CLOCK_SELF_REPORTED: zaman kanıtı bu dosyayı içeren commit'in push'udur".
- **Kod bağı:** Model JSON'u kodla aynı commit'e girdiği için commit hash'i JSON'a yazılamaz (bir commit kendi hash'ini içeremez). Bunun yerine JSON, `borsai/*.py` dosyalarının içerik hash'ini (`borsai_source_sha256`) taşır. Bağımsız denetim bu değerin HEAD'deki kod ağacının hash'ine eşit olduğunu doğruladı (`docs/fable_conformity_20260922/AUDIT.md` özet 7).
- **Ayrı dizinler karışmaz:** Listeleme öncesi ve POST_D1 modelleri aynı çağrıda dondurulamaz; POST_BREAK modelleri yalnız birlikte, kendi dizinine.

### 6.11.2 Tahmin kaydının içeriği

`python -m borsai.freeze registry/inputs/<TICKER>.json`, girdi belgesinden bir kayıt üretir: `registry/records/<TICKER>/<UTC-zaman>_<kısa-sha>.json` (şema `borsai.record/1`). NETGL kaydından gerçek alanlar [ölçüldü]:

| Alan | İçerik |
|---|---|
| `schema_version`, `record_type` | `borsai.record/1`, `PREDICTION` (ya da `CANCELLATION`) |
| `ticker` | `NETGL` |
| `recorded_at_utc`, `recorded_at_istanbul`, `recorded_at_basis` | Yerel saat + "zaman kanıtı bu kaydı içeren commit'in push kanıtıdır" notu |
| `code` | `git_head`, `borsai_dirty`, `borsai_source_sha256`, dosya başına `borsai_files_sha256` (23 dosya) |
| `input_sha256` ve `inputs` | Girdi belgesinin hash'i; `inputs.document` girdi belgesinin TAMAMI (her alan için değer, kaynak belge kimliği, alıntı, kaynak yolu, yayın zamanı, belge sha256'sı) |
| `model_inputs` | Modellere giden 19 düz alan (fiyat, pay sayıları, f3 = "2.84", f6 …) |
| `market20` | f6 piyasa özelliğinin hesabı: `S0_date`, `S20_date`, iki kapanış, `ref_date` ve kuralı, XU100 dosyası ve sha256'sı, takvim sha'sı |
| `models_index` | `INDEX.json` yolu, sha256'sı ve model kimlikleri listesi (o gün 16) |
| `models[]` | Her model için: `model_id`, `file`, `params_sha256`, `spec_sha256`, `algorithm`, `kind`, `status` (PREDICTED/REFUSED), `refusal` {code, field, reason}, `output` |
| `summary` | `n_models`, `n_predicted`, `n_refused`, `refusals` (ör. VEYAS: 4 × `F3_MISSING`) |
| `legacy_links`, `legacy_roles_sha256` | Eski repo kayıtlarına bağ ve rollerin hash'i |
| `tufe` | (INDEX'te TÜFE deflatörlü model varsa) kullanılan TÜFE ayı ve pinleri |

Örnek bir girdi alanı (NETGL f3):

```
"total_demand_multiple": {
  "value": "2.84",
  "quote": "toplamda 2,84 katı kadar talep",
  "source_id": "KAP_1662138_EK1",
  "source_published_at": "2026-09-13T17:30:28+03:00",
  "source_sha256": "bdf25f37…",
  "origin": "SOURCE_REPORTED"
}
```

Değer, alıntı, kaynak ve kaynağın sha'sı birlikte duruyor: denetçi PDF'i açıp hash'i doğrulayabilir, alıntıyı bulabilir, yayın anının D_1'den (2026-09-17) önce olduğunu görebilir.

Yazıcının kuralları (`freeze.write_record`, `build_record`):
- Girdi belgesi yapısal denetimden ve `inputs_pit_ok`'un girdi kısmından geçmezse kayıt **yazılmaz**.
- INDEX'teki **bütün** modeller çalıştırılır; reddeden modelin hücresi ret kodu ve nedeniyle yazılır. Bir model hata verirse (`ERROR`) kayıt yazılmaz.
- Dosya adı içerik adreslidir (bayt sha256'sının ilk 12 hanesi) ve dosya `xb` kipinde açılır: var olan dosya asla yeniden yazılmaz.
- Aynı arz için birden çok etkin kayıt olabilir (ör. talep toplama öncesi ve sonrası). Ama etkin bir kayıtla aynı `input_sha256` ve aynı INDEX sha'sını taşıyan ikinci kayıt `DUPLICATE_RECORD` ile reddedilir (E19).
- **Sınıf kayda yazılmaz.** Kayıt yalnız ne bilindiğini ve ne tahmin edildiğini söyler; ne zaman bilindiğini push kanıtı söyler.
- Yazıcı yalnız stdlib kullanır (`test_record_writer_is_stdlib_only`); masaüstü uygulamasının "dondur" düğmesi aynı Python fonksiyonunu çağırır.

Bir gözlem: Repodaki 7 kaydın hepsinde `code.borsai_dirty = true` [ölçüldü]. Yani kayıt anında `borsai/` altında commit'lenmemiş değişiklik ya da izlenmeyen dosya vardı (kayıtlar `7cb49cf` ile, Faz 2A kodunun kendisiyle birlikte commit edildi). Kural bunu yasaklamıyor; kod sürümünü bağlayan alan dosya başına hash'lerdir. Bunun bir sorun yaratıp yaratmadığı repodaki belgelerden net değil (belirsiz).

### 6.11.3 Hangi kayıt skorlanır? (birincil kayıt)

Bir (model, arz) için birden çok kayıt varsa, hangisinin skorlanacağı sonuç görülmeden şu kuralla belirlenir (`registry.select_primary`, `SPEC_SCORING §6`):

- **f3 isteyen modeller** (V1.5, V1.6, market20, tavan modelleri, v1 ve düşen arz modellerinin f3'lüleri): resmi f3 içeren kayıtlar arasında, D_1'den önce push kanıtlı **en son** kayıt (`LATEST_PUSH_PROVEN_BEFORE_D1`). Yoksa `inputs_pit_ok` olan en erken kayıt (`EARLIEST_LATE_RECORD`). Mantık: talep katı ancak talep toplama bitince belli olur; en güncel bilgiyle yapılmış ama yine D_1'den önce kanıtlanmış tahmin skorlanır.
- **PB modelleri ve kurallar:** **en erken** kayıt (`EARLIEST_RECORD`). PB modelleri talep toplama öncesi bilgilerle çalışır; kayıt talep toplama başladıktan sonra yapıldıysa `pb_after_bookbuild_start = 1` işareti konur, yine skorlanır.
- İki iz ayrı seçilir ve asla birleşmez: kanıtlı (`REGISTRY` + `GIT_PUSH`) birincil metriğe, `SELF_REPORTED` ikincil satıra.
- İptal edilmiş ve geçersiz kullanım kayıtları aday değildir.
- Dondurulmuş değer **asla yeniden hesaplanmaz**. JSON'dan yeniden üretilen değer yalnız parite denetimidir (beklenen |Δ| ≤ 1e-9), skora girmez (`test_freeze_records.py::test_committed_record_parity`).

**Eski repodan gelen (legacy) dondurmalar.** BorsAi'den önceki repoda yapılmış yedi V1.5 dondurması `registry/legacy_frozen/` altında **içerikleri değiştirilmeden** duruyor; rolleri ayrı bir dosyada, `registry/legacy_roles.json`'da (şema `borsai.legacy_roles/1`) bağlanır [ölçüldü]:

| Kayıt | Model | Rol | Zaman kanıtı | f3 |
|---|---|---|---|---|
| `NETGL_20260916_V1_5` | `v1_5_h99` | `PRIMARY` | `GIT_PUSH` (eski repo commit'i + GitHub status kanıtı) | 2.84 |
| `BKRGY_20260827_…POST_BOOKBUILD_PRE_LISTING` | `v1_5_h99` | `PRIMARY` | `SELF_REPORTED` | 1.77 |
| `INTET_20260831_…POST_BOOKBUILD_PRE_LISTING` | `v1_5_h99` | `PRIMARY` | `SELF_REPORTED` | 1.7 |
| `TKNKA_20260819_V1_5_FULL20` | `v1_5_full20` (ayrı model) | `PRIMARY_SEPARATE_MODEL` | `SELF_REPORTED` | 6.45 |
| `BKRGY_20260825_V1_5`, `…_R2`, `INTET_20260825_V1_5` | `v1_5_h99` | `INVALID_USE` | `SELF_REPORTED` | yok |

Her rol satırı `legacy_import = true`, `content_modified = false` ve dosya başına sha256 listesi taşır; sınıf burada da etiketlenmez. Legacy kayıtlar kural 1'in "bütün modeller birlikte" şartını sağlamaz (yalnız V1.5 içerirler); bu yüzden yalnız kendi model sütunlarında ve kendi izlerinde (kanıtlı ya da self-reported) kullanılırlar. `inputs_pit_ok` legacy kayıtlar için şöyle hesaplanır: eski paketteki V1.5 girdileri, resmi belgelerden toplanan `registry/inputs/<T>.json` değerleriyle Decimal-eşit ve o belgeler D_1'den önce yayımlanmış olmalı (E7). `tests/test_registry_inputs.py::test_inputs_agree_with_legacy_frozen_packets` bu eşitliği sınar.

### 6.11.4 İptal

`python -m borsai.freeze --cancel <kayıt.json> --reason "<neden>"` ayrı bir `CANCELLATION` kaydı yazar: iptal edilen dosyanın adı ve sha256'sı, neden, zaman, kod bloğu. İptal edilen dosya değişmez, yerinde kalır; yalnız skorlanmaz ve iptal nedeni görünür.

Kısıtlar: neden boş olamaz; yalnız etkin bir `PREDICTION` kaydı iptal edilebilir; ve **iptal, ilk işlem gününden itibaren yapılamaz** (İstanbul tarihi ≥ D_1 ise `FreezeError`). Neden? Sonucu görmeye başladıktan sonra kötü tahmini iptal etmek, sicili temizlemenin arka kapısı olurdu. POST_D1 kayıtları için sınır T_open'dır. Repoda bugün hiç iptal kaydı yok (`cancelled_records: []`) [ölçüldü].

### 6.11.5 POST_D1 ve POST_BREAK aşamaları

**POST_D1** (D1 akşamı güncellemesi): `freeze --post-d1 <TICKER>`, `registry/post_d1/<TICKER>/` altına kayıt yazar. Kayıt, temel kaydı (ceiling_hazard_v0'ın birincil listeleme öncesi kaydı), D_1 tarihli THB+THM'nin pinli sha256'ları ve ham alanlarını, `INDEX_POST_D1.json`'daki her modelin çıktısını ve karşılaştırıcıların koşullu kopyasını içerir. Zaman sınırı:

```
T_open(a) = D_1'i izleyen ilk resmi seans günü, 09:40:00+03:00
LIVE ⇔ push_kanıtı(kayıt commit'i).created_at < T_open     (an karşılaştırması, tarih değil)
```

Birincil POST_D1 kaydı: T_open'dan önce push kanıtlı **en erken** kayıt (`select_primary_post_d1`). Bekçi `registry.post_d1_record_problems`: kayıtta D_1 dışında hiçbir sonuç alanı (h ≥ 2 anahtarı, D_1 dışı bülten adı ya da sha'sı) olamaz; D_1 alanları yalnız `d1` bloğunda. POST_D1 modelinin prospektifliği için "model JSON'u, D_1'den sonraki ilk sonuç verisini repoya sokan commit'in atası" olmalı; ondan önce girmiş sonuçlar o model için RETRO'dur.

**POST_BREAK** (kırılma akşamı): İnsan kaydı yoktur. `python -m borsai.scoring --break` önce eksik makine kayıtlarını `registry/post_break/<T>/machine_<UTC>_<sha>.json` altına yazar: tahmin, dondurulmuş model JSON'u, D_b'ye kadarki sha-pinli resmi bültenler ve listeleme öncesi girdi dosyasından deterministik üretilir. Bekçi (`post_break_record_problems`): kayıtta D_b sonrası hiçbir bülten adı, sha'sı ya da h > b sonuç anahtarı yok. Sınıf `MACHINE_SEQUENCED`, ölçek `live_break`.

### 6.11.6 Sıra bekçileri

İki ayrı kapı var:

**1. İndirme kapısı — `outcomes.sequence_guard(market_date)`:** 2026-08-19 sonrası bir bülten ancak `INDEX.json` ve listelediği bütün model dosyaları, `INDEX_POST_D1.json` ve modelleri, `registry/records/` ve `registry/post_d1/` altındaki bütün kayıtlar **git'te izleniyor ve çalışma kopyasında değişmemişse** indirilir. Aksi halde `SequenceRuleError` ve hiçbir bayt indirilmez. Yani commit'lenmemiş bir tahmin kaydı dururken sonuç bülteni repoya giremez.

**2. Geçmiş denetimi — `scoring.sequence_violations()` (`test_outcome_guard.py::test_sequence_rule_outcomes_follow_models_and_records`):** Her test koşusunda bütün depo taranır. 2026-08-19 sonrası tarihli (ya da 2026-08-06 sonrası bir arzın işlem gününü kapsayan) her bülten zip'i ve her yeni arz sonuç dosyası için, onu ekleyen commit'in ataları:
- (a) Faz 1'in 16 model JSON'unu ekleyen commit'leri,
- (b) ilgili her FROZEN arzın ilk tahmin kaydını ekleyen commit'i

içermelidir. POST_D1 ve POST_BREAK modelleri için kural "sıralı olma"dır: hedef dosya ya modelden sonra (model atası) ya da modelden önce (o arz RETRO) girmiş olmalı; paralel daldan gelen hedef ihlaldir. Sonradan eklenen bir model sonuçtan sonra donarsa bekçi kırmızı olmaz; o model o arz için RETRO'ya düşer (bu, sınıflamanın işi).

Sentetik testler (`test_10`…`test_10h`) geçici depolarda yanlış sıraları kurar: sonuç modelden önce ⇒ kırmızı; doğru sıra ⇒ yeşil; sonuç kayıttan önce ⇒ kırmızı; commit'lenmemiş sonuç HEAD'e karşı; POST_D1/POST_BREAK modeli listelenmiş ama commit'lenmemiş ⇒ kırmızı; paralel dal ⇒ kırmızı.

### 6.11.7 Uçtan uca bir örnek: Faz 2'nin gerçek sırası

`GITLOG.txt` ve kanıt dosyalarından [ölçüldü]:

| Sıra | Commit | Yerel zaman (+03) | Ne | Push kanıtı (UTC) |
|---|---|---|---|---|
| 1 | `5fa849d` | 09-21 21:14 | Faz 1A modelleri donduruldu | 09-22 14:06:00 |
| 2 | `d3fabad` | 09-22 02:55 | Faz 1 şartnameleri | 14:06:01 |
| 3 | `b09cab5` | 09-22 13:10 | Faz 1B modelleri donduruldu | 14:06:03 |
| 4 | `1869da6` | 09-22 14:26 | Fable uygunluk denetimi | 14:06:04 |
| 5 | `7cb49cf` | 09-22 15:40 | 7 arzın tahmin kayıtları, payda | 14:06:05 |
| 6 | `99aed71` | 09-22 17:06 | 1–5'in push kanıt dosyaları | — |
| 7 | `e469a93` | 09-22 17:52 | Sonuç ve skor tanımları (veri yok) | 15:32:19 |
| 8 | `f1f9d44` | 09-22 18:20 | Resmi THB/THM sonuçları + ilk skorlama | 15:32:21 |

Kanıtların saniyeler arayla alınması, birden çok commit'in tek bir push'la gönderildiğini gösteriyor (çıkarım). Sıranın doğruluğu saatlerden değil DAG'dan gelir: 1, 3 ve 5, 8'in atasıdır; 7 de 8'in atasıdır ("tanımlar sonuçtan önce"). Kayıtlar (5) sonuçlardan (8) önce kanıtlı; ama D_1'lerden sonra, dolayısıyla LATE_RECORD.

Kaynak dosyalar: `borsai/freeze.py`, `borsai/registry.py` (`select_primary`, `select_primary_post_d1`, `t_open`, `post_d1_record_problems`, `post_break_record_problems`), `borsai/outcomes.py` (`sequence_guard`), `borsai/scoring.py` (`sequence_violations`), `models/INDEX*.json`, `registry/records/`, `registry/inputs/`, `registry/post_d1/`, `registry/post_break/`, `registry/legacy_frozen/`, `registry/legacy_roles.json`, `registry/push_proofs/`, `tests/test_freeze_records.py`, `tests/test_registry_inputs.py`, `tests/test_outcome_guard.py`, `tests/test_faz5_live.py`, `tests/test_faz8_live.py`.

---

## 6.12 Zaman-dışı kohort ve kasa

### 6.12.1 Neden?

Backtest tasarıma maruz, canlı n çok yavaş büyüyor. Arada bir kanıt kaynağı var: H99'dan *önce* listelenmiş arzlar. Bu arzların sonuçları geçmişte kaldı ama repoya hiç girmemişti; modeller onlara bakılarak kurulmadı. Eğer önce donmuş modellerle bu arzlar tahmin edilip push edilir, sonra sonuçları getirilirse, "tahmin sonuçtan önce" ilkesi korunmuş olur. Fark: dönem eğitimden öncedir ve kural rejimi farklıdır (ör. 2020'de günlük marj bazı pazarlarda %20, borsada satış yöntemi yaygın, eşit dağıtım kuralı 2023'te geldi). Bu yüzden bu terazi kendi adını taşır: **zaman-dışı (out-of-time, OOT)**.

### 6.12.2 Kohort

`registry/oot/cohort_pre_h99.csv` (append-only): ilk işlem günü 2020-01-01 … 2023-09-21 olan, halka arz sonucu Pay Piyasası'nda işlem görmeye başlayan bütün paylar. Kaynak: KAP'taki Borsa İstanbul "Payların İşlem Görmeye Başlaması" bildirimleri; SPK yıllık tabloları yalnız çapraz denetim. [ölçüldü]

| | Sayı |
|---|---|
| Satır | 136 (135 `MEMBER` + 1 `OUT_OF_SCOPE`: halka arzsız kotasyon) |
| Yıllara göre üye | 2020: 8, 2021: 52, 2022: 38, 2023: 37 |
| `OPEN` | 66 |
| `SEALED` (kasa) | 64 |
| `EXPOSED_ARCHIVE` | 4 (D_10'ları 2023-09-22 sonrasına düşen ve bültenleri arşivde fiziksel olarak bulunan arzlar) |
| `EXPOSED_CODEX` | 1 (girdi toplayan araç listeleme sonrası bir KAP başlığı görmüş) |
| Açık küme (kasa dışı) | 66 + 4 + 1 = **71** |

Girdiler yalnız listeleme öncesi resmi belgelerden (`registry/oot/inputs/<T>.json`, canlıdakiyle aynı şema); her alan kaynak kimliği, yayın zamanı ve sha256 taşır. Girdileri repo dışı bir araç çıkardı, Claude Code her değeri yeniden indirilen belgede birebir doğruladı (KARARLAR D7).

### 6.12.3 Kasa (vault)

**Sorun:** Eski kohortun bütün sonuçları açılırsa, sonradan yeni bir özellik (ör. "düşen arzları ayıran" bir değişken) arandığında hem keşif hem doğrulama aynı, görülmüş veride yapılır. Bu, çoklu karşılaştırmanın en sinsi biçimidir.

**Çözüm:** Kohortun yarısını **mühürlemek**. Kasa (SEALED) üyelerinin sonuçları, doğrulanacak özellik önceden yazılıp push edilene kadar hiçbir dosyaya, günlüğe ya da ekrana girmez.

Çekiliş (KARARLAR D2, şartname §9 seçenek K2):
- %50, ilk işlem **yılı içinde tabakalı** (her yıldan yarısı),
- tohum `numpy.random.Generator(PCG64(20260924))`, sıralama (`first_trading_date`, `ticker`),
- `EXPOSED_*` üyeler çekilişten önce çıkarılıp açık kümeye yazılır (zaten görülmüş olabilecek bir şey mühürlenemez),
- kasa listesi kohort dosyasıyla birlikte, girdi ve sonuç verisinden bağımsız olarak commit ve push edildi (`2e088c3`).

Bağımsız denetim çekilişi yalnız metinden yeniden üretti: 135/135 aynı (`docs/fable_faz6_audit/AUDIT.md`).

**Hijyen:** Kasa üyelerinin kodları hiçbir rapora, günlüğe ya da test çıktısına yazılmaz. Bekçi mesajları bile yalnız sayı verir ("kasa kodu (2 farklı)"), kod adı vermez. Bu bölümde de kasa üyelerinin adı geçmiyor.

### 6.12.4 Karantina: bültenler repoya ham girmez

Kohort penceresinde 135 üyenin 127'sinin 10 günlük penceresi başka bir üyeninkiyle çakışıyor (KARARLAR D6'daki orkestratör ölçümü). Rastgele %50 kasayla, açık bir arzın bülteni neredeyse her zaman bir kasa arzının sonucunu da taşır. Bu yüzden (KARARLAR D6):

1. Kohort penceresindeki THB/THM zip'leri **repoya girmez**; repo dışında bir karantina dizinine indirilir.
2. Deterministik ayıklama kodu yalnız **açık** üyelerin satırlarını (yalnız kendi D_1…D_10 tarihleri) okur. Repoya ayıklanmış satırlar (`data/outcomes_oot/<T>.csv`) ve her zip'in URL, sha256, bayt, Last-Modified ve indirme zamanı pinleri (`data/raw/bist/MANIFEST_OOT.csv`) girer.
3. Kasa kodları için satır okunursa ayıklama kodu hata verir.
4. Sonuç satırları `outcome_basis = MACHINE_EXTRACTED` etiketi taşır: makine bütün zip'i gördü, insan görmedi.
5. Sıra kapısı, ayıklanmış sonuçları ekleyen commit üzerine kurulur; zip indirmesinin kendisi de kapıya bağlıdır (`outcomes_oot.download_gate`): bütün S2 kayıtları commit'li ve push kanıtlı değilse karantina indirmesi başlamaz.

`test_no_cohort_window_bulletin_anywhere_in_repo` kohort penceresi tarihli hiçbir zip ya da iç CSV'nin repoda olmadığını sınar.

### 6.12.5 Adımlar ve sınıf

| Adım | İçerik | Commit |
|---|---|---|
| S0 | Şartname + proje sahibi kararları | `b8763fc`, `94ad4e8` |
| S1 | Üyelik, kasa, rejim etiketleri, girdiler, kaynak belgeler | `2e088c3` |
| S2 | 135 üye × 19 donmuş model, listeleme öncesi kayıtlar (`registry/oot/records/`) | `1dcceff` |
| S3 | Açık kümenin D_1 satırları (karantinadan makineyle) + `post_d1_hazard_v0` kayıtları | `9e1e992`, `7ade6a8` |
| S5 | Açık kümenin D_1…D_10 sonuç satırları | `77b54f7` |
| S6 | Skorlama (`scores_oot.json`, `SCORES_OOT.md`) | `cf60cea` |
| R1 | Faz 7/7C'nin 8 yeni modeli için ek kayıtlar (`--only-missing-models`) | `28aaa3b` |
| VA1/VA2/VB | Kasanın tek seferlik açılışı | `2f914dd`, `5a96e25`, `71b9071` |
| — | Kasa skorları | `ff49828` |

Sınıf formülü (`SPEC_OOT_PRE_H99_V0 §2`, KARARLAR D6-5, `scores_oot.json` → `definitions.class`):

```
oot_ingest_commit(a) = min( outcomes_oot/<a>.csv, raw/<a>.json ve d1_rows/<a>.json'u ekleyen commit,
                            tarihi [D_1(a), D_10(a)] olan bir THB/THM zip'ini ekleyen commit )
OOT_BLIND ⇔ model commit'i ve kayıt commit'i oot_ingest_commit'in atası
            VE modelin push kanıtı var
            VE push_kanıtı(kayıt) < push_kanıtı(oot_ingest_commit)
            VE kohortun HER üyesinin (o modeli içeren) kaydı oot_ingest_commit'in atası
aksi halde OOT_RETRO (yalnız bilgi)
```

Son koşul **kohort düzeyi kapı**dır: Bülten bütün payları taşıdığı için "arz başına sıra" yetmez. Faz 7'den sonra kapı **model başına** hale geldi: her model için, o modeli içeren birincil kayıt (en erken etkin kayıt) her üye için var ve önce kanıtlanmış olmalı (SPEC_DEVIATIONS L1).

Kayıt şeması `borsai.oot_record/1` canlıdakine benzer, ek olarak `record_stage = OOT_PRE_LISTING`, `scale = OOT_PRE_H99`, `cohort_file_sha256`, `cohort_row`, `regime_tags` ve `comparators` taşır. Karşılaştırıcılar **H99'da donmuş** kural değerleridir; yeniden eğitilmez. "Son 10 arz" kuralları için bu bilinçli bir uzlaşmadır: kohortta "T'den önceki son 10 arz"ın sonucu körlük altında bilinemez, bu yüzden H99'un son 10'u kullanılır ve satır `FROZEN_H99_LAST10_NOT_CHRONOLOGICAL` notunu taşır.

Rejim etiketleri (`regime_tags`): borsada satış, fiyat aralıklı talep toplama, fiyat adımı tablosu dönemi, günlük marj kuralı, açığa satış yasağı, tahsis rejimi, pazar. Bir model bir rejimde uygulanamıyorsa (ör. 0.10 marj sabitiyle çalışan modeller, marjın %10 olmadığı arzda) hücre "atlandı" değil `NOT_APPLICABLE_REGIME` + neden olur.

### 6.12.6 Kasanın açılışı

Kasa **bir kez** açılır. Ön koşul: doğrulanacak özellikler önceden kaydedilmiş olmalı. Kodda dört belge sabittir (`outcomes_oot.VAULT_OPENING_DOCS`): `docs/specs_faz7/SPEC_HAZARD_V1.md`, `docs/specs_faz7/KARARLAR.md`, `docs/specs_faz7_c/SPEC_C_V0.md`, `docs/specs_faz7_c/KARARLAR_C.md`. Kapı (`vault_gate_problems`), her belgenin HEAD'de, değişmemiş ve son değiştiren commit'inin push kanıtlı olmasını ister.

Açılış (`docs/faz7_vault/RAPOR.md`, `registry/oot/VAULT_OPEN.json`) [ölçüldü: işaret dosyası]:
- `MANIFEST_OOT.csv`'deki **914** zip (açılıştan önceki satırların tamamı; açılış adımlarıyla manifest 1.168 satıra çıktı, §3.2.1) yeniden indirildi; 914'ünün sha256'sı pinle eşit, uyuşmazlık 0. (Bir uyuşmazlık olsaydı `SourceChanged` ile hiçbir kasa dosyası yazılmazdı.)
- Kasa üyelerinin D_1 satırları ayıklandı (VA1), sonra kasa üyeleri için `post_d1_hazard_v0` kayıtları yazıldı (VA2), push kanıtı alındı, en son D_1…D_10 satırları geldi (VB).
- İşaret dosyası `VAULT_OPEN.json` (şema `borsai.vault_open/1`) en son yazılır; kasa kodu içermez; `n_sealed = 64`, `cohort.n_open = 71`, indirme kapısı sorunsuz, `opened_at_basis` yine "yerel saat; kanıt push'tur".
- Açılışta tek beklenmedik durum: karantinadaki bültenlerin yalnız biri (SPEC_DEVIATIONS M14'e göre 921'de 1) tarihi ISO dışı biçimde (`d.mm.yyyy`) taşıyordu; kod bütün-ya-hiç yazdığı için durdu, hiçbir şey yazılmadı; proje sahibi kararıyla ayrıştırıcı genişletildi (SPEC_DEVIATIONS M14).

Kasa bekçileri **iki kiplidir** (SPEC_DEVIATIONS M-E): işaret dosyası yokken kasa kodu hiçbir ayıklanmış dosyada geçemez; işaret varken kasa kodu yalnız üye başına kasa yollarında ve ortak skor çıktılarında, yalnız işaret commit'inde ya da sonrasında geçebilir. Kip elle bayrakla değil işaret dosyasının varlığıyla belirlenir.

Bağımsız denetçi Fable, kasa skorlarını **görmeden önce** kendi hesabını ve seçim kurallarını commit etti (`38d36e8`), sonra Opus'un dosyasıyla karşılaştırdı: 34 hücrenin hepsi birebir (`VAULT_SCORE_OK`).

### 6.12.7 Sonuçlar (özet)

`scores/scores_oot.json` (≈ 41 MB) üç ayrı anahtar ve üç D1-sonrası anahtar taşır; hiçbiri ötekine eklenmez [ölçüldü]:

| Anahtar | İçerik |
|---|---|
| `oot_pre_h99` | Açık küme (71 üye), 27 model (8 yeni model açık kümede `OOT_RETRO`: sonuçlar repoya girdikten sonra donduruldular) |
| `oot_pre_h99_sealed` | Kasa (64 üye), 27 model |
| `oot_pre_h99_all` | Açık + kasa (135), yalnız açık kümede de `OOT_BLIND` olan 19 eski model; 8 yeni model `excluded_models`'ta |
| `post_d1`, `post_d1_sealed`, `post_d1_all` | `post_d1_hazard_v0`, `MACHINE_SEQUENCED` |
| `retro_info` | 568 çift (8 yeni model × 71 açık üye), yalnız bilgi |

Birincil hücreler (fark = model − karşılaştırılan; negatif = model iyi; hüküm zaman-dışı terazide) [ölçüldü]:

| Model | Hücre | Açık küme | Kasa | Toplam |
|---|---|---|---|---|
| `v1_5_h99` | D5 MAE − medyan | −0.028 [−0.081, +0.023] n 68, ayırt edilemiyor | −0.012 [−0.071, +0.041] n 62, ayırt edilemiyor | −0.020 [−0.061, +0.017] n 130, ayırt edilemiyor |
| `v1_6_h99` | D10 MAE − v1.5 | +0.0004 [+0.0003, +0.0006], geçemiyor | +0.0004 [+0.0001, +0.0007], geçemiyor | +0.0004, geçemiyor |
| `v1_5_market20_v0` | D5 MAE − v1.5 | −0.002, ayırt edilemiyor | −0.006, ayırt edilemiyor | −0.004, ayırt edilemiyor |
| `pb_v0` | D5 MAE − medyan | −0.008, ayırt edilemiyor | +0.030, ayırt edilemiyor | +0.010, ayırt edilemiyor |
| `ceiling_hazard_v0` | RPS − KM genişleyen | +0.069 [+0.001, +0.131], **geçemiyor** | +0.073 [−0.001, +0.139], ayırt edilemiyor | +0.071 [+0.012, +0.126], **geçemiyor** |
| `pb_ceiling_v0` | RPS − KM genişleyen | +0.048, ayırt edilemiyor | +0.065, ayırt edilemiyor | +0.056 [+0.004, +0.109], geçemiyor |
| `ceiling_path_v0` | D5 MAE − medyan | −0.010, ayırt edilemiyor | +0.002, ayırt edilemiyor | −0.004, ayırt edilemiyor |
| `ceiling_hazard_v1_pooled` | RPS − KM genişleyen | (OOT_RETRO) | −0.040 [−0.067, −0.012] n 62, **geçiyor** | tanımsız |
| `ceiling_hazard_v1_real` | aynı | (OOT_RETRO) | −0.011, ayırt edilemiyor | tanımsız |
| `ceiling_hazard_v1_clip` | aynı | (OOT_RETRO) | +0.033, ayırt edilemiyor | tanımsız |
| `fall_d10_v0_pooled` | D10 Brier − taban oranı | (OOT_RETRO) | −0.045 [−0.092, −0.002] n 60, **geçiyor** | tanımsız |
| `fall_d10_v0_h99` | aynı | (OOT_RETRO) | −0.040 [−0.088, +0.004], ayırt edilemiyor | tanımsız |
| `post_d1_hazard_v0` | j = 1 koşullu RPS − v0 | −0.042 [−0.066, −0.020] n 59, geçiyor | −0.035 [−0.072, +0.004] n 45, ayırt edilemiyor | −0.039 [−0.060, −0.017] n 104, geçiyor |

Okuma notları:
- Backtest'te "geçiyor" olan `ceiling_hazard_v0`, zaman-dışı terazide KM tabanına karşı **geçemiyor** (açık küme ve toplam). Eski dönemde tavan dinamikleri farklıydı; backtest'teki kazanç bu döneme taşınmadı. Bu, terazileri ayrı tutmanın neden önemli olduğunun somut örneği.
- `v1_6_h99` her üç kümede çok küçük ama sistematik bir farkla V1.5'ten kötü; aralık 0'ı dışladığı için "geçemiyor".
- Kasada yalnız iki yeni aday geçiyor (`v1_pooled`, `fall_pooled`). Seçim kuralları (k1–k3) birden çok koşul istiyor; `v1_pooled` yakın dönem backtest hücresinde "bozuyor" etiketi aldığı için seçilmedi, uygulamada tavan kartı `ceiling_hazard_v0`'da kaldı; düşen arz kartı hiçbir modeli öne çıkarmıyor (`docs/faz7_vault/SKOR_RAPOR.md`).
- Önceden yazılmış beklentilerle karşılaştırma açık küme için `docs/faz6/S6_RAPOR.md` §4'te: `ceiling_hazard_v0` (+0.069, beklenti [−0.03, +0.03]) ve `pb_ceiling_v0` (+0.048, beklenti [−0.02, +0.04]) beklentiden kötü; `v1_5_h99`, `pb_v0` ve `post_d1_hazard_v0` beklentiden iyi; diğerleri aralık içinde. Rapor, beklentiden sapmanın modeli değiştirme gerekçesi olmadığını ayrıca yazıyor. Kasada hiçbir birincil hücre "beklentiden çok iyi" eşiğini aşmadı.

Kaynak dosyalar: `docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md`, `docs/specs_faz6/KARARLAR.md`, `docs/specs_faz6/FEASIBILITY.md`, `docs/faz6/`, `docs/faz7_oot/RAPOR.md`, `docs/faz7_vault/RAPOR.md`, `docs/faz7_vault/SKOR_RAPOR.md`, `registry/oot/` (`cohort_pre_h99.csv`, `records/`, `d1_rows/`, `post_d1/`, `inputs/`, `VAULT_OPEN.json`), `data/outcomes_oot/`, `data/raw/bist/MANIFEST_OOT.csv`, `borsai/outcomes_oot.py`, `borsai/scoring.py` (`class_oot`, `cohort_gate_ok`, `build_oot_scores`), `scores/scores_oot.json`, `docs/SCORES_OOT.md`, `tests/test_faz6_oot.py`, `tests/test_faz7_oot.py`, `tests/test_faz7_vault.py`.

---

## 6.13 Deney günlüğü (`experiments/log.jsonl`)

### 6.13.1 Ne ve neden

Kural 4'ün uygulaması. Her backtest koşusu, koşunun sonunda kendiliğinden günlüğe bir satır ekler (`backtest.run_backtest` → `append_log`). **Günlüğe yazmadan backtest koşturan bir yol yoktur**: `log_path` zorunlu argümandır. Dosya JSON Lines biçimindedir (satır başına bir JSON nesnesi, UTF-8, LF) ve **yalnız sonuna yazılır**: `append_log` dosyayı `"a"` kipinde açar, var olan satırları okumaz ve değiştirmez. Hatalı bir koşu da günlükte kalır.

Test paketi aynı `run_backtest` kodunu pytest'in geçici dizinindeki bir günlüğe yazarak koşar (`conftest.test_log_path`). Neden? Test koşuları yeni bir varyant denemez, dondurulmuş şartnameyi aynı veride doğrular; resmi günlüğe yazsalardı her test koşusu varyant sayacını şişirir ve repoyu kirletirdi.

### 6.13.2 İçerik [ölçüldü]

Bugün **2 146 satır** var; ilk satır 2026-09-21 20:58, son satır 2026-10-02 11:36.

| `kind` | Satır | Anlamı |
|---|---|---|
| `exploration` | 2 054 | Faz 7C düşen arz keşfinde denenen varyantlar (tek kaynak: `docs/specs_faz7_c/ekler/denenenler.csv`, `context = faz7c_exploration_import`) |
| `backtest` | 72 | Resmi walk-forward koşuları |
| `sensitivity` | 19 | Duyarlılık koşuları (çoğu Fable denetimlerinden; model değil, hiçbir tabloya girmez) |
| `conditional_eval` | 1 | Faz 4 koşullu RPS_j değerlendirmesi (keşif) |

Backtest satırlarının bağlamları: `faz1a_acceptance_run` 7, `faz1a_golden` 7, `faz1b_acceptance_run` 19, `faz1b_golden` 19, `faz4_acceptance_run` 3, `faz4_golden` 3, `faz5_golden` 1, `faz7_golden` 4, `faz7_golden_b1` 4, `faz7c_golden` 4, `official` 1 (Faz 8). Günlükte 49 farklı `model_id` geçiyor; iki veri sürümü var: H99 (`a0c7d082…`, 77 satır) ve eğitim tablosu v2 (`2ee8d51b…`, 2 069 satır; keşif satırlarının hepsi bu sürümde).

**Bir backtest satırının alanları** (`experiments/README.md`): `kind`, `context`, `model_id`, `spec_sha256` (şartnamenin kanonik hash'i), `plan_id`, `data_version_sha256`, `training_table_sha256`, `folds_total`, `folds_scorable`, `ledger_sha256`, `metrics` (ufuk başına n, MAE, medyan AE, Brier, isabet), `started_at`, `finished_at`, `git_commit`, `borsai_dirty`, `borsai_source_sha256`; doğrusal ve hazard modellerinde `runtime` (Python, scikit-learn, numpy… sürümleri); yeni modellerde `spec_document` ve `spec_document_sha256`; plan dışı koşularda `run_key` (ör. `base_train_median__pb`).

Örnek (ilk satırdan kısaltılmış):

```json
{"kind":"backtest","context":"faz1a_acceptance_run","model_id":"v1_5_h99",
 "plan_id":"H99_WALK_FORWARD_STRICT_PRIOR_DATE_MIN_TRAIN_10",
 "folds_total":396,"folds_scorable":{"D1":89,"D3":88,"D5":87,"D10":87},
 "metrics":{"D5":{"folds":87,"return":{"n":87,"mae":0.2220,"median_ae":0.1921},
                  "p_up":{"n":81,"brier":0.1614,"accuracy":0.8025}}, …},
 "ledger_sha256":"5c56da37…","git_commit":"ff3eee64…","borsai_dirty":true,
 "runtime":{"python":"3.12.14","scikit-learn":"1.9.0","numpy":"2.5.2", …}}
```

**Bir keşif satırı** model değildir ve dondurulmaz: `family`, `variant` (özellik, yöntem, hedef, alt küme, değer; ör. tek özellikli bir AUC denemesi), `variant_id` (`denenenler.csv#1`), kaynak dosyanın sha256'sı ve commit'i, "sonuçlar görüldükten sonra, H99 + açık küme" notu. Neden günlükte? Çünkü düşen arz ailesinin seçimi bu keşfe dayandı; 2 054 denemenin görünmesi, ailenin kasa sonucunu doğru bağlamda okumayı sağlar. Kart iki sayacı yan yana gösterir, toplamaz: `n_variants_same_data` ve aile keşif sayacı.

Günlüğün kullanım yerleri: model kartındaki varyant sayacı (§6.9.5); `docs/MODELS.md`'deki koşu sayıları; testlerde altın koşuların günlükte bulunması (`test_experiment_log.py::test_official_log_contains_golden_runs`), duyarlılık satırlarının hiçbir tabloya girmemesi (`test_sensitivity_lines_are_logged_but_enter_no_table`), bir `run_backtest` çağrısının tam bir satır eklemesi (`test_run_backtest_appends_exactly_one_line`).

Kaynak dosyalar: `experiments/log.jsonl`, `experiments/README.md`, `borsai/backtest.py` (`append_log`, `run_backtest`, `exploration_entries`, `import_exploration`), `borsai/scoring.py` (`_n_variants_same_data`, `family_exploration_card`), `tests/test_experiment_log.py`.

---

## 6.14 `docs/SPEC_DEVIATIONS.md`: sapmalar defteri

### 6.14.1 Ne işe yarar?

Şartnameler (`docs/specs*/`) commit edildikten sonra **değiştirilmez**. Ama hiçbir şartname her ayrıntıyı öngöremez: bir cümle iki türlü okunabilir, bir kural uygulanamaz çıkar, gerçek veri bir uç durum getirir. Bu durumlarda uygulayıcı kafasına göre karar verirse, "şartnameye uygun" iddiası boşa düşer. Çözüm: Her belirsizlik ve her çözümü tek bir deftere, gerekçesiyle yazılır. Standart satır biçimi:

| # | Şartname:bölüm | Belirsizlik | Seçilen yorum | Gerekçe |
|---|---|---|---|---|

Defterin iki işlevi var:
1. **Şeffaflık:** Denetçi (Fable) bir şeyin neden şartnameden farklı olduğunu buradan okur ve her maddeye "KABUL" ya da "bulgu" der.
2. **Model kimliği kararı:** Her madde, modelin davranışını değiştirip değiştirmediğini söyler. Değiştirmiyorsa (uygulama düzeltmesi, belirsizliğin giderilmesi) model kimliği aynı kalır; değiştiriyorsa yeni `model_id` gerekir (kural 5). Defterin başında bu yazıyor: "Hiçbir madde bir modelin davranışını ya da parametre sayısını değiştirmez".

Bazı maddeler **sonuç görüldükten sonra** yazılmak zorunda kaldı; bunlar açıkça işaretlenir. Örnek E20: canlı tamlık denetimi bir temerrüt pazarı kodunu tanımadığı için durdu; kural sonuç verisi görüldükten sonra yazıldı, ama yalnız payda denetimini etkiler, hiçbir sonuç, sınıf ya da skor tanımını değiştirmez. Bu açıklık, kuralın kendisinden daha önemlidir.

### 6.14.2 Bölümler [ölçüldü: 312 numaralı satır; D bölümü madde işaretli]

| Bölüm | Faz / görev | Madde | Konu |
|---|---|---|---|
| A | Faz 1B | 12 | Model tanımı ve hesap (çözücü toleransı, imputasyon yok, PB alanları) |
| B | Faz 1B | 7 | Kod yerleşimi ve arayüz (ret kodlarının biçimi, f6'nın yeri) |
| C | Faz 1B | 8 | Kurallar ve karşılaştırmalar (@INF ayrı kimlik, KM'nin 99 arzla dondurulması, **C7 bootstrap yöntemi**) |
| D | Faz 1B | — | Görev kurallarıyla ilgili notlar (eski testlerde zorunlu genelleştirmeler) |
| E | Faz 2B | 20 | Sonuç ve skorlama yorumları (15 seans penceresi, L tanımı, E10 "skorlanan arz", E11 hüküm dili, E12 canlı Brier kırpmasız, E16 varyant sayacı, E19 mükerrer kayıt) |
| F | Faz 4 | 17 | Tavan yolu modelleri, dondurma ve skor hücreleri |
| G | Faz 2C | 12 | Koşullu canlı skorlama (j başına ayrı ölçek) |
| H | Faz 5 | 47 | D1 sonrası model, dondurma ve canlı POST_D1 akışı |
| I | Faz 6 | 47 | Eski kohort altyapısı, S3/S5 ayıklama, S6 skorlama ve düzeltmeleri |
| J | Faz 7 | 31 | Tavan serisi v1 ve dondurması (J31: uygulama pinlerinin asgari yeniden pinlenmesi) |
| K | Faz 7C | 23 | Düşen arz modeli (K14: ufuk sırası denetimi düzeltmesi) |
| L | Faz 7 OOT | 12 | Ek kayıtlar, model başına kapı (L1), kasa skorlama kodu |
| M | Kasa | 24 | Tek seferlik açılış (M-A…M-L kararları, M14 ISO dışı tarih, M24 sonuç ilerlemesi pini) |
| N | Faz 8 | 33 | Kırılma akşamı modeli, dondurma, canlı POST_BREAK (N20 ürün eşiği bulgusu) |
| O | Faz 9 | 19 | Sade görünüm (uygulama arayüzü) |

### 6.14.3 Örnek kayıtlar

- **C7** (bootstrap yöntemi): Şartname numpy PCG64 diyordu; backtest tabloları Faz 1A'nın legacy benchmark'ıyla karşılaştırılabilir kalsın diye `random.Random(20260921)` ve [0.01, 0.99] kırpması korundu. Canlı skorlama şartnameye aynen uydu (E12). §6.7.5'teki tablo bu maddenin sonucudur.
- **E10** (n nedir?): Çok ufuklu bir modelde "skorlanan arz" en az bir hedefi gerçekleşmiş arzdır; hücreler yalnız `n_scored ≥ 10` ve hücrenin kendi n'i ≥ 10 iken üretilir. Aynı sayı hem gösterim kuralını hem uygulamanın bütünlük denetimini tanımlar.
- **K14** (aynı model_id ile düzeltme): Düşen arz modelinin stdlib tahmin kodu, JSON'daki ufukların *sırasını* denetliyordu; sıralı anahtarla yazılan dosya bu yüzden reddediliyordu. Denetim *küme* karşılaştırmasına çevrildi; model, backtest ve ledger'lar değişmedi; aynı kimlik.
- **M14** (kasa açılışında durma): Bir bültenin tarih alanı ISO değil `d.mm.yyyy` biçimindeydi; kod bütün-ya-hiç yazdığı için durdu. Proje sahibi kararıyla ayrıştırıcı, yalnız her satır bülten gününe denk geliyor ve sayısal alanlar kanonik biçimdeyse noktalı tarihi kabul edecek şekilde genişletildi.
- **M24** (içerik pini mi, bekçi mi?): Bir test, Faz 1 canlı bloklarının ilk skorlama anındaki halinde kalmasını istiyordu; yeni sonuç (NETGL D4–D10) girince kaçınılmaz olarak kırmızıya döndü. Karar: sonuçlar *ilerleyebilir* (PENDING → dolu), ama dondurulmuş alanlar, dolu ufuklar ve yeni arzlar yine kırmızı. Ayrıca bir düzeltme notu (`fd22be3`): ilk not testin kırmızılığının nedenini yanlış okumuştu; düzeltme de deftere yazıldı.
- **N20** (bulgu, değişiklik yok): Faz 8'in ürün karşılaştırıcısındaki eşik, fiyat adımı yuvarlaması yüzünden şartnamenin türetmesinden daha katı sayıyordu. Şartname aynen uygulandı (karşılaştırıcı değişirse yeni kimlik gerekirdi); sağlamlık analizi Fable denetimine bırakıldı, birincil hüküm toleranslı okumalarda da değişmedi.

Kaynak dosyalar: `docs/SPEC_DEVIATIONS.md`, `docs/specs*/`.

---

## 6.15 Test altyapısı ve bekçiler

### 6.15.1 Nasıl koşulur?

```
.venv/bin/pytest -q                          # sıralı (varsayılan; her görevin son kabul koşusu)
.venv/bin/pytest -q -n 6 --dist loadgroup    # paralel (ara koşular; pytest-xdist)
```

Son raporlara göre paket **952 test** toplar ve hepsi geçer: `docs/app/UI_FIX_RAPOR.md` (2026-10-06) paralel 952 geçti (9:49), sıralı 952 geçti (18:40); `docs/faz8/LIVE_RAPOR.md` sıralı 952 geçti (0:18:18). Bu çalışma ortamında pytest kurulu olmadığı ve repo kopyası git deposu olmadığı için sayıyı koşarak doğrulayamadım. Statik sayım: 56 test dosyasında 747 `def test_` fonksiyonu var; `@pytest.mark.parametrize` ile açılınca literal listelerden 827, isimli sabitlerle açılanlar (model ve arz listeleri) da eklenince yaklaşık 950 [ölçüldü, yaklaşık]; 952 ile tutarlı.

**Paralel koşu neden "loadgroup"?** Altyapı raporu (`docs/infra/TEST_SPEED_RAPOR.md`) bunu ölçtü: backtest testleri kendi içinde zaten 9 süreçlik bir havuz açıyor. Paralel işçiler bu havuzları aynı anda açarsa makine aşırı yüklenir; gruplamasız `-n auto` koşusu 44 dakika sürdü (sıralı 15–17 dk). `tests/conftest.py` her teste bir `xdist_group` işareti ekler: havuz açan testler (`backtest_results` fixture'ını kullananlar ve `POOL_MODULES` listesi) tek grupta (`backtest_pool`), diğerleri modül adına göre gruplanır. Aynı gruptaki testler tek işçide, sıralı koşudaki sırayla koşar. Sonuç: `-n 6 --dist loadgroup` ≈ 11 dk, sıralı ≈ 15–17 dk; paralel ve sıralı koşular düğüm düğüm aynı sonucu verdi (864/864, o tarihteki test sayısı). Ölçüm sırasında bir paralel-yük kararsızlığı (kasa testi) bulunup düzeltildi.

`conftest.py`'nin oturum fixture'ları: `dataset` (H99), `test_log_path` (geçici günlük), `backtest_results` (bütün modellerin backtest'i, oturumda bir kez), `frozen_models` (INDEX'teki donmuş JSON'lar).

### 6.15.2 Bekçi kavramı

Normal bir test "kod doğru hesaplıyor mu?" diye sorar. Bir **bekçi** (guard) "depo kurala uyuyor mu?" diye sorar: dosyaların sırası, hangi dosyanın nerede bulunabileceği, hangi kodun hangi metinde geçemeyeceği. Bekçiler gerçek repo üzerinde koşar; çoğu ayrıca geçici git depolarında kasıtlı olarak bozuk senaryolar kurup kırmızıya döndüklerini gösterir (bekçinin bekçisi).

### 6.15.3 Test türleri

| Tür | Ne korur | Örnekler |
|---|---|---|
| **Kabul testleri** | Şartnamenin numaralı kabul maddeleri | `test_acceptance_backtest.py` (H99 V1.5 benchmark'ını yeniden üretir: 351/351 fold kimliği, toleranslı tahminler, metrikler, bayt eşitliği), `test_outcomes.py` (SPEC_SCORING §10-1…4), `test_scoring.py` (§10-5…9, 11), `test_ceiling.py`, `test_pb.py`, `test_v1_6.py`, `test_market20.py` |
| **Altın / bayt eşitliği** | Bugünkü kod dondurulan modeli üreten kod mu? | `test_faz1b_backtest.py`, `test_faz5_golden.py`, `test_faz7_golden.py`, `test_faz7c_golden.py`, `test_faz8_golden.py` (ledger yeniden koşulup bayt bayt karşılaştırılır) |
| **Parite** | Donmuş JSON → stdlib tahmin = fit tarafı (numpy/sklearn) | `test_predict.py` (JSON ↔ sklearn), `test_faz7_frozen.py`, `test_faz7c_frozen.py`, `test_faz8_frozen.py`, `test_freeze_records.py::test_committed_record_parity` (kayıttaki değer = JSON'dan yeniden üretilen) |
| **Port ↔ legacy** | Yeni kod eski repo koduyla bit düzeyinde aynı mı? | `test_port_vs_legacy.py` (legacy değiştirilmeden import edilir; uç fold örnekleri: tek sınıf, yedek C, f3'süz test arzı, yakınsamayan D3 fold'u) |
| **Veri kabulü** | Eğitim tablosu ham kaynaklardan bağımsız olarak doğru mu? | `test_training_table.py` (üreticiyi import etmez, ham kaynakları kendisi okur), `test_xu100_update.py`, `test_faz7_table_v2.py`, `test_faz7_tufe.py`, `test_faz7_prospectus.py` |
| **Sıra bekçisi** | Sonuç ancak model ve kayıttan sonra | `test_outcome_guard.py` (aşağıda) |
| **Hijyen / kasa taraması** | Kasa kodu ve bülten adı hiçbir yerde yok | `test_outcome_guard.py::test_sealed_codes_absent_from_every_extracted_file`, `test_no_cohort_window_bulletin_anywhere_in_repo`, `test_cohort_codes_appear_in_data_only_as_outcomes`; `test_faz7_vault.py::test_new_task_files_carry_no_vault_code_or_bulletin_name`; `test_faz8_break.py::test_14_no_bulletin_names_or_sealed_codes_in_faz8_files` |
| **Değişmezlik pinleri** | Eski şartnameler, modeller, altınlar ve uygulama pinleri değişmedi | `test_guardrails.py`, `test_faz1b_guardrails.py`, `test_faz8_model.py::test_5c…`, `test_faz8_break.py::test_14b…`, `test_faz4_ceiling_path.py` |
| **Kayıt ve sicil** | Kayıt yazıcısı, payda, girdi belgeleri, push kanıtı | `test_freeze_records.py`, `test_registry_ipos.py`, `test_registry_inputs.py`, `test_push_proof.py`, `test_models.py` |
| **Günlük** | Kural 4 | `test_experiment_log.py` |
| **Rapor** | MODELS.md, beklentilerin aynen alıntısı | `test_report.py`, her fazın `*_golden.py`'si |

### 6.15.4 Öne çıkan bekçiler

**`tests/test_outcome_guard.py` (34 test)** — sıra kuralının ana bekçisi:
- `test_sequence_rule_outcomes_follow_models_and_records`: `sequence_violations() == []` (§6.11.6).
- `test_sequence_rule_covers_every_post_cutoff_bulletin_and_outcome`: bekçinin kapsamı eksiksiz mi? Bülten zip'leri yalnız `data/raw/bist/th[bm]/YYYY/` altında, sonuç dosyaları yalnız bilinen arzlar için.
- `test_text_mentions_of_post_cutoff_bulletins_follow_models`: 2026-08-19 sonrası bir bültene *metinde* atıf yapan dosya da sıra kuralına uyar (bir rapor sonucu, modelden önce anamaz).
- `test_new_ipos_appear_in_data_only_as_outcomes`: yeni arzların kodları `data/` altında yalnız sonuç dizinlerinde geçebilir; eğitim tablosuna sızamaz.
- `test_10…test_10h`: geçici depolarda bozuk sıra senaryoları.
- `test_registry_carries_no_outcome_fields`, `test_reference_files_hold_no_post_listing_outcomes`, `test_source_documents_predate_first_trading_day`: sicilde sonuç alanı adı (`close`, `R_D5`, `ceiling_streak_L` …) yok; kaynak belgeler ilk işlem gününden önce.
- POST_D1 / POST_BREAK bekçileri: kayıtlarda yalnız izinli günlerin alanları; h ≥ 2 sonucu, o seansın bültenini ekleyen commit'ten önce yazılamaz.
- Eski kohort bekçileri: `test_oot_records_hold_every_index_model_and_follow_model_commits` (G2), `test_oot_outcomes_follow_every_s2_record_and_its_push_proof` (G5′, model başına kapı ve kanıt sırası), kasa hijyeni (iki kipli), `test_cohort_file_is_append_only_in_history`, mutasyon testleri (`test_cohort_guard_t4_mutation`, `test_completeness_sealed_exception_two_mode_mutation`).

Bekçilerin hata mesajları kasa kodu basmaz: kodlar yerel değişkende tutulur, mesaj yalnız sayı taşır ("kasa kodu (2 farklı)").

**`test_scoring.py::test_5c_outcome_before_model_is_retro`:** sınıflama formülünün (c) senaryosu: geçici depoda önce sonuç, sonra model commit'lenir; sınıf RETRO olmalı.

**`test_faz8_model.py::test_5c_old_goldens_and_app_pins_unchanged`** (adı aynı olsa da başka bir test): Faz 8'in başlangıç commit'inden (`7d78d43`) bu yana `tests/reference` ve `models/` altında yalnız Faz 8'in eklediği üç dosyanın değiştiğini; tahmin kodlarının (`predict*.py`, `features.py`, `survival.py` …) ve backtest/metrik kodlarının hiç değişmediğini; `freeze.py`, `scoring.py`, `registry.py`'deki değişikliklerin yalnız adı belli görev commit'lerinden geldiğini; `specs.py`'ye yalnız ekleme yapıldığını; uygulamanın parite altınlarının (`app/parity/gen_golden.py --check`) farksız olduğunu git komutlarıyla sınar. Bu tür testlere repoda **pin** denir; bir görev bilerek pinli bir şeyi değiştirecekse, testteki pin satırı ayrı ve önceden onaylanmış bir commit'le güncellenir (K-PIN, K-PIN-L, K-PIN-UI, K-PIN-FIX etiketleri; SPEC_DEVIATIONS N25, N26, O). Commit başlıklarında "APPPIN" geçenler bu türdendir.

**`test_faz8_break.py::test_14b_old_specs_models_and_cutoff_unchanged`:** eski bütün şartname dizinleri (`docs/specs`, `specs_faz4` … `specs_faz7_c`) `7d78d43`'ten beri değişmemiş ve çalışma kopyasında temiz; `INDEX.json` ve `INDEX_POST_D1.json` bayt bayt aynı; `models`, `registry`, `data`, `scores`, `legacy`, `app` dizinlerinde commit'lenmemiş değişiklik yok; kırılma etiketlerinin tarihleri 2026-08-19 sınırını aşmıyor.

### 6.15.5 Mutasyon testi

Bir testin gerçekten koruduğunu nereden biliriz? Kodu bilerek bozarız ("mutant") ve testin kırmızıya döndüğünü görürüz. Kırmızıya dönmeyen mutant, testin bir boşluğu demektir. Fable denetimleri bunu sistematik yapar: Faz 6 altyapısında 16 mutasyonun 14'ü kırmızı (yeşil kalan ikisinden biri gerçek bir test boşluğuydu, öteki davranışı değiştirmeyen eşdeğer mutant; bir mutant da yalnız tesadüfen kırmızıydı; eksik testler `40db62c`'de eklendi); Faz 7C'de 16/16; Faz 8'de 13/13; Faz 5'te 12 mutasyon grubunun 11'i (alt koşularıyla 18'in 17'si; yeşil kalan, gerçekçi veride davranışı değiştirmeyen eşdeğer bir mutanttı ama yine ÖNEMLİ bulgu sayılıp teste bağlandı, §5.6.1). Bazı bekçi testleri mutasyonu kendi içinde taşır (`…_mutation` adlı testler).

### 6.15.6 Test dosyaları (66 girdi)

`tests/` altında 66 girdi var: 56 `test_*.py` dosyası, 9 yardımcı modül (`conftest.py`, `faz1b_support.py`, `faz5_support.py`, `faz5_live_support.py`, `faz6_support.py`, `faz7_support.py`, `faz7c_support.py`, `faz8_support.py`, `refcompare.py`) ve `reference/` dizini (altın ledger'lar, legacy benchmark çıktıları). `test_faz8_support.py` adı test dosyası gibi ama test içermez (görev kuralı yeni dosyaları `test_faz8_*` adıyla sınırladığı için).

| Dosya | Test | Koruduğu |
|---|---|---|
| `test_acceptance_backtest.py` | 16 | Faz 1A port kabulü: fold kimlikleri, toleranslı tahminler, metrikler, altın ledger bayt eşitliği |
| `test_ceiling.py` | 17 | `ceiling_hazard_v0`, `pb_ceiling_v0` kabul testleri (çözücü, RPS, ret) |
| `test_experiment_log.py` | 4 | Kural 4 |
| `test_faz1b_backtest.py` | 5 | Faz 1B altın ledger'ları, resmi günlük |
| `test_faz1b_guardrails.py` | 5 | Faz 1A altınları, `v1_5_h99` ve kural JSON'ları, şartnameler değişmedi; 08-19 sonrası veri yok |
| `test_faz1b_models.py` | 9 | Faz 1B donmuş modeller: INDEX, JSON yapısı, yeniden üretim, stdlib tahmin |
| `test_faz4_ceiling_path.py` | 26 | Tavan yolu kabul testleri, "beklentiden çok iyi" kararı, Faz 1 bloklarının değişmezliği |
| `test_faz5_frozen.py`, `_golden.py`, `_post_d1.py`, `_live.py` | 7, 8, 32, 41 | D1 sonrası model: dondurma, resmi koşu, kabul testleri, canlı akış (09:40 sınırı, sınıf senaryoları geçici depolarda) |
| `test_faz6_oot.py` | 54 | Eski kohort altyapısı: Takvim C, kohort doğrulayıcı, kasa çekilişi, rejim etiketleri, karantina ve indirme kapısı (sentetik zip, ağ yok), üçüncü terazi |
| `test_faz6_s6.py`, `_s6_fix.py` | 9, 12 | Zaman-dışı skorlama CLI'ı, SCORES_OOT.md, D1 etiketi kapısı, açık küme `retro_info` |
| `test_faz7_backtest.py`, `_model.py`, `_golden.py`, `_freeze.py`, `_frozen.py` | 10, 14, 15, 7, 9 | Tavan serisi v1: plan, model, resmi koşu, dondurma yolu, donmuş dosyalar |
| `test_faz7_table_v2.py`, `_tufe.py`, `_prospectus.py` | 11, 13, 8 | Eğitim tablosu v2, TÜFE dosyası ve T − 2 kuralı, izahname alanları |
| `test_faz7_oot.py` | 19 | Ek kayıtlar, model başına kapı, kasa skor kodu (sentetik SYN*/SYK* kodlarla) |
| `test_faz7_vault.py` | 17 | Kasa açılışı: dört belge kapısı, pinli yeniden indirme, işaret dosyası, iki kipli hijyen |
| `test_faz7c_*.py` (5 dosya) | 16, 8, 9, 12, 19 | Düşen arz modeli: backtest, dondurma, donmuş dosyalar, resmi koşu, model |
| `test_faz8_*.py` (6 dosya + destek) | 16, 7, 8, 7, 27, 16 | Kırılma akşamı modeli: tablo ve sızıntı, dondurma, resmi koşu, canlı POST_BREAK, model |
| `test_features.py` | 7 | f1–f5 özellik tanımları |
| `test_freeze_records.py` | 13 | Kayıt yazıcısı: bütün modeller, ret hücreleri, üzerine yazma reddi, mükerrer kayıt, iptal, PIT reddi, determinizm, stdlib, commit'li kayıtların tutarlılığı ve paritesi |
| `test_guardrails.py` | 3 | `legacy/` değişmedi; 08-19 sonrası veri yok |
| `test_market20.py` | 12 | f6 kabul testleri (gelecek veriye kör) |
| `test_metrics.py` | 4 | Backtest bootstrap'i, çağrı sırasından bağımsızlık, hüküm kuralı, kırpmanın yeri |
| `test_models.py` | 7 | INDEX ve donmuş dosyalar, eğitim blokları, kural değerleri, V1.5 yeniden fit, üzerine yazma reddi |
| `test_outcome_guard.py` | 34 | Sıra kuralı ve hijyen bekçileri (§6.15.4) |
| `test_outcomes.py` | 25 | Sonuç tanımları, indirici, manifest, ilan dışı kapanış, tamlık |
| `test_pb.py` | 10 | `pb_v0` kabul testleri |
| `test_port_vs_legacy.py` | 3 | Port ↔ legacy bit eşitliği |
| `test_predict.py` | 12 | JSON ↔ sklearn tahmin paritesi, uç vektörler, predict yalnız stdlib |
| `test_push_proof.py` | 8 | Kanıt biçimi, yeniden yazmama, kimliksiz atlama, ata kapsaması, commit'li kanıtların geçerliliği |
| `test_registry_inputs.py` | 11 | Girdi belgeleri, `inputs_pit_ok`, kaynak belge manifestleri, legacy rolleri |
| `test_registry_ipos.py` | 5 | Payda dosyası: şema, bilinen 7 arz, neden zorunluluğu, append-only, tamlık |
| `test_report.py` | 5 | MODELS.md ve beklentilerin aynen alıntısı |
| `test_scoring.py` | 34 | Sınıflama, birincil kayıt, payda, bootstrap, dil, RPS, `scores.json` şeması ve yeniden hesap eşitliği |
| `test_scoring_conditional.py` | 16 | Koşullu canlı skorlama (j başına, birleştirme yasağı) |
| `test_training_table.py` | 10 | Eğitim tablosunun bağımsız veri kabulü |
| `test_v1_6.py` | 9 | `v1_6_h99` kabul testleri |
| `test_xu100_update.py` | 6 | XU100 ve takvim uzatması |

(Sayılar `def test_` fonksiyon sayısıdır; parametrelerle açılınca toplam büyür.)

Uygulamanın kendi testleri ayrıdır (`app/scripts/test.sh`: Rust/cargo, TypeScript/vitest, parite betikleri, altın vektörler `gen_golden --check`); raporlarda pytest'in yanında birlikte verilir.

Kaynak dosyalar: `tests/`, `tests/conftest.py`, `docs/ENV.md`, `docs/infra/TEST_SPEED_RAPOR.md`, `docs/app/UI_FIX_RAPOR.md`, `docs/faz8/LIVE_RAPOR.md`, `pyproject.toml`.

---

## 6.16 Bağımsız denetimler (Fable)

Projenin çalışma biçiminde "yazan el ile denetleyen el ayrıdır". Şartnameleri Fable yazar, uygulamayı Opus (Claude Code) yapar, sonra Fable uygulamayı görmeden ya da yalnız okuyarak denetler. Denetimlerin ortak yöntemi:

- **Sıfırdan yeniden üretim:** Fable, `borsai` paketini **import etmeyen**, yalnız şartnameden yazılmış bir betikle aynı sayıları bağımsız olarak hesaplar. Betik sonunda `sys.modules` içinde `borsai` olmadığını assert eder. Eşik genelde |Δ| ≤ 1e-9; çoğu denetimde maks |Δ| = 0 çıktı.
- **Kör yeniden hesap:** Skor denetimlerinde Fable kendi hesabını Opus'un skor dosyalarını açmadan önce commit eder (Faz 1), sonra karşılaştırır (Faz 2). Sıra git'te görünür.
- **Sızıntı ve sıra denetimi**, **mutasyon koşusu**, **tam test koşusu**, **koruma ölçümü** (`registry/`, `data/`, `scores/`, `models/` ağaçlarının hash'i denetim öncesi ve sonrası aynı).
- İşaretler: **[ÖLÇTÜM]** ve **[ÇIKARIM]**; bulgu düzeyleri KRİTİK / ÖNEMLİ / KÜÇÜK.

| Dizin | Neyi denetledi | Hüküm ve ana bulgular |
|---|---|---|
| `docs/fable_conformity_20260922/` | Faz 1B'nin dokuz kimliği: beş model, iki `@INF` ucu ve iki KM kuralı (`b09cab5`), push öncesi | **PUSH_OK** (hepsi). Sızıntı yok (87/87 tavan fold'unda eğitim ve PP kümesi bağımsız kurguyla aynı, max seans < T). `ceiling_hazard_v0`'ın −0.05 RPS kazancı gerçek; şartnamedeki beklenti yanlış çapalanmıştı. 27 sapmanın hepsi KABUL; bir belgelenmemiş küçük sapma. Tahmin paritesi ≤ 1e-15. |
| `docs/fable_app_audit/` (+ `KAPANIS.md`) | Masaüstü uygulamasının SPEC_APP'e uygunluğu | İlk: **DÜZELTMEYLE UYGUN**; B1 KRİTİK (askıda sembolik bağla kişisel kaydın `registry/records/` altına yazılabilmesi), B2/B3 ÖNEMLİ (ekran mantığı testsiz, dondur ön koşulları yeniden denetlenmiyor). Uygulamanın skor hesaplamadığı ve iki teraziyi birleştirmediği doğrulandı. Kapanış: 10 bulgunun 10'u kapandı, **UYGUN**. |
| `docs/fable_faz4_audit/` | Tavan yolu modelleri ("beklentiden çok iyi" tetiklenmişti) | **FREEZE_OK** ×3. 870 hücre maks \|Δ\| = 0; §6'nın 36 satırı Δ = 0; sızıntı yok (backtest sırasında sonuç dizinlerinden 0 dosya okuma); kazancın kaynağı tanılandı; duyarlılık analizleri sonucu değiştirmedi. |
| `docs/fable_faz5_audit/` | `post_d1_hazard_v0` ve Faz 2C koşullu skorlama | **FREEZE_OK**; ledger maks \|Δ\| 1.5e-11; 12 mutasyonun 11'i kırmızı; Faz 2C koşullu satırları maks \|Δ\| = 0, **UYGUN**. |
| `docs/fable_faz6_audit/` | Eski kohort altyapısı, girdi örneklemi, kuru S2 koşusu | **S2_OK**. Kasa çekilişi 135/135, rejim etiketleri 135/135, Takvim C 1360/1360 satır; 15 üyelik örneklemde 296/296 alan doğru; 16 mutasyonun 14'ü kırmızı; iki ÖNEMLİ test kapsamı bulgusu (kod şartnameye uygun ama mutant yakalanmıyordu), `40db62c`'de kapatıldı. |
| `docs/fable_faz6_s6/` | Açık kümenin zaman-dışı skorları | Önce kör hesap (`aea4082`), sonra karşılaştırma: **S6_OK**; sınıf ve durum sayıları birebir (1349 OOT_BLIND / 0 RETRO). |
| `docs/fable_faz7_audit/` | Tavan serisi v1 ailesi | **FREEZE_OK** ×4; λ seçimleri 87/87 ve 97/97 birebir, maks \|Δ\| ≤ 4.3e-11; TÜFE dosyası resmi kaynaktan bağımsız doğrulandı; ÖNEMLİ bulgular B1–B4 (biri betimleyici sütun hatası, ikisi test eksiği, biri belgelenmemiş karar), hepsi aynı model kimliğiyle düzeltilebilir. |
| `docs/fable_faz7c_audit/` | Düşen arz modeli v0 ailesi | **FREEZE_OK** ×4; ledger'lar alan alan birebir (maks \|Δ\| = 0); 16/16 mutasyon kırmızı; kasa dosyalarına hiç dokunulmadı. |
| `docs/fable_faz7_vault/` | Kasa skorları ve seçim kuralları | Önce kör hesap ve seçim kuralları (`38d36e8`), sonra karşılaştırma: **VAULT_SCORE_OK**; 34 hücrenin hepsi birebir; skor tanımı değişmemiş. |
| `docs/fable_faz8_audit/` | Kırılma akşamı modeli | **REPRO_OK**; ledger, duyarlılıklar ve önizlemeler bit-eşit; N20 eşik bulgusunun sağlamlık analizi (toleranslı okumalarda birincil hüküm korunuyor); 13/13 mutasyon kırmızı. |

`CLAUDE.md`'nin andığı ilk denetim (`docs/fable_audit_20260921/AUDIT.md`, kodda sık geçen "AUDIT §1.2-c" atıflarının kaynağı) ve envanter (`docs/checkup_20260921/`) bu repo kopyasında yok; içerikleri yalnız atıflardan biliniyor (belirsiz).

Kaynak dosyalar: `docs/fable_*/AUDIT.md`, `docs/fable_app_audit/KAPANIS.md`, `docs/fable_faz6_s6/`, `docs/fable_faz7_vault/` (`recompute.py`, `BAGIMSIZ.json`, `karsilastir.py`).

---

## 6.17 Özet: bir tahminin yaşam döngüsü

Bütün kuralları tek bir akışta toplayalım. Yeni bir model ve yeni bir arz için:

1. **Şartname** (Fable) yazılır: model tanımı, fold planı, birincil hücre, önceden yazılmış beklenti. Commit + push + push kanıtı.
2. **Uygulama** (Opus): kod ve testler (commit A, sonuç yok), sonra resmi walk-forward koşusu (commit B). Her koşu deney günlüğüne bir satır yazar. Ledger'lar altın olarak pinlenir.
3. **Sapmalar** `SPEC_DEVIATIONS.md`'ye yazılır; davranışı değiştiren her şey yeni model kimliği ister.
4. **Bağımsız yeniden üretim** (Fable, `borsai` import etmeden). "Beklentiden çok iyi" tetiklendiyse zorunlu. Hüküm FREEZE_OK değilse dondurma yok.
5. **Dondurma:** `models/<id>.json` + `INDEX*.json` girdisi (sha256 pinleri). Commit + push + kanıt. Uygulama pinleri ayrı commit'te yeniden pinlenir.
6. **Kayıt:** Arz listelenmeden önce resmi belgelerden girdi belgesi (`registry/inputs/<T>.json`, her alan kaynak + yayın zamanı + sha256). `freeze` dizindeki bütün modellerle kaydı yazar. `ipos.csv`'ye satır. Commit + push + kanıt (D_1'den önce → LIVE adayı).
7. **Sonuç:** `sequence_guard` kayıtlar commit'li değilse bülten indirmez. Bültenler sha256 ile pinlenir, `data/outcomes/<T>.csv` yazılır. `sequence_violations` her test koşusunda sırayı denetler.
8. **Skorlama:** `python -m borsai.scoring`. Sınıf DAG + kanıt + tarihlerden hesaplanır; birincil kayıt kuralla seçilir; eşleşik farklar, blok bootstrap, n kuralları, hüküm dili. Çıktı `scores.json` + `SCORES.md`; uygulama yalnız gösterir, hesaplamaz.
9. **Raporlama:** Üç terazi ayrı panellerde; "geçiyor" yalnız n ≥ 30 ve aralık 0'ın altındaysa; birincil hücre dışındakiler "keşif".
10. **Hata olursa:** Kayıt silinmez; D_1'den önce iptal kaydı. Model yanlışsa yeni kimlik; eski kimlik ve sicili listede kalır.

Bu düzenin bedeli bürokrasidir; kazancı, bir sayının ne anlama geldiğini her zaman geriye doğru izleyebilmektir: hangi şartname, hangi kod, hangi veri, hangi sırayla, kim tarafından ve ne zaman kanıtlanarak.

Kaynak dosyalar: `CLAUDE.md`, `docs/specs/SPEC_SCORING.md`, `GITLOG.txt`.

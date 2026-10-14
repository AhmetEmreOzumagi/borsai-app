# 2. Tarihçe, çalışma biçimi ve bugünkü durum

Bu bölüm BorsAi'nin on altı günlük hikâyesini anlatır: 21 Eylül 2026'da yeni deponun iskeleti kuruldu, 6 Ekim 2026'da uygulamanın sunum öncesi düzeltmeleri bitti. Arada 175 commit, 79 görev dosyası, 30 donmuş model, üç ayrı doğruluk terazisi ve bir masaüstü uygulaması var. Amaç şu üç soruya dosyalara dayanarak cevap vermek:

1. Ne zaman ne yapıldı?
2. Hangi karar neden alındı?
3. Hangi ders çıkarıldı ve bugün nerede duruyoruz?

Bölümdeki her sayı repodaki bir dosyadan ya da proje bilgi alanındaki bir belgeden alındı; kaynağı her alt bölümün sonunda yazılı. Dosyada karşılığı bulunmayan yerler "belirsiz" diye işaretlendi. Model ayrıntıları (özellikler, ön işleme, formüller) ve kuralların uzun anlatımı başka bölümlerde (Bölüm 3–6); burada yalnız sürece etkileri anlatılıyor.

Kaynak dosyalar: `GITLOG.txt`, `docs/prompts/` (79 dosya), `models/INDEX.json`, `models/INDEX_POST_D1.json`, `models/INDEX_POST_BREAK.json`.

## 2.0 Okumadan önce: kısa sözlük

Aşağıdaki terimler bütün bölüm boyunca geçer.

| Terim | Anlamı |
|---|---|
| Arz | Borsa İstanbul'da halka arzla ilk kez işlem görmeye başlayan pay. |
| D1, D_h | Arzın ilk işlem günü (D1) ve D1'den itibaren işlem gördüğü h'inci resmi seans (D_h). Yarım gün sayılır, tam gün işlem durdurma sayılmaz. |
| Tavan / taban | Seans kapanışının o günün üst limitine (tavan) ya da alt limitine (taban) tam eşit olması. Bant ±%10'dur. |
| Seri uzunluğu L | D1'den başlayarak art arda kaç gün tavan kapanışı olduğu (0–10). |
| Kırılma günü b | Serinin bozulduğu gün, b = L + 1. "Kırılma akşamı" bu günün bülteninin yayımlandığı akşamdır. |
| THB / THM | Borsa İstanbul'un günlük resmi bültenleri. THB'den kapanış fiyatı ve işlem (sözleşme) sayısı, THM'den referans fiyat ile üst ve alt limit okunur. Sonuç verisi yalnız bunlardan gelir. |
| H99 | Eğitim kohortu: ilk işlem günü 2023-09-22…2026-08-06 arasında olan 99 arz. |
| Eski kohort | 2020-01-01…2023-09-21 arasında listelenen 135 arz. Açık küme (71) ve kasa (64) diye ikiye bölündü. |
| Kasa (SEALED) | Eski kohortun, sonuçları hiç görülmeden kapalı tutulan ve yalnız bir kez açılan yarısı. Üyelerinin kodları bu kitapta yazılmaz. |
| Dondurma | Bir modelin parametrelerinin JSON dosyasına yazılıp commit edilmesi ve push edilmesi. Donmuş model bir daha değişmez. |
| Kayıt | Bir arz için, kayıtlı bütün modellerin tahminlerini girdileri ve parametre hash'leriyle birlikte saklayan dosya (`registry/records/…`). |
| Push kanıtı | Bir commit'in GitHub'da bulunduğunu sunucu saatiyle gösteren dosya (`registry/push_proofs/<sha>.json`). Yerel saat kanıt sayılmaz. |
| LIVE / LATE_RECORD / RETRO | Bir arzın bir model için sınıfı. LIVE: model sonuçtan önce donmuş ve kayıt D1'den önce push edilmiş. LATE_RECORD: model önce donmuş ama kayıt D1'den sonra yazılmış. RETRO: model sonuçtan sonra donmuş; yalnız bilgi. |
| Terazi (ölçek) | Doğruluğun ölçüldüğü ayrı küme: backtest (geçmiş veri testi), canlı sicil ve zaman-dışı eski kohort. Teraziler asla toplanmaz. |
| Basit kural | Modelin yenmesi gereken karşılaştırıcı: "her zaman tavan", eğitim medyanı, taban oran, Kaplan–Meier (KM) oranı gibi. |
| Birincil hücre | Bir model için sonuç görülmeden önce ilan edilmiş tek karşılaştırma (metrik + ufuk + karşılaştırıcı). Hüküm bu hücreye göre verilir. |
| "Geçiyor" | Model ile kural arasındaki farkın %95 aralığı tamamen modelin lehine (0'ı dışlıyor). Aralık 0'ı içeriyorsa "ayırt edilemiyor". |
| Şartname (spec) | Bir modeli kodlanmadan önce bütünüyle tanımlayan belge: özellikler, model sınıfı, karşılaştırıcılar ve önceden yazılmış beklenti. |
| Orkestratör | Planı yöneten, görev dosyası yazan ve raporları doğrulayan sohbet (claude.ai proje sohbeti). |
| Opus, Sonnet, Fable | Claude Code oturumlarında kullanılan modeller. Opus kod yazar, Sonnet mekanik ölçüm yapar, Fable şartname yazar ve bağımsız denetim yapar. |

Kaynak dosyalar: `CLAUDE.md`, `docs/specs/SPEC_SCORING.md` §2, §3, §5, `docs/DATA.md`, `docs/specs_faz6/KARARLAR.md`, `claude/HANDOFF.md` §3 (proje bilgi alanı).

## 2.1 Projenin amacı ve öncelikleri

`CLAUDE.md`'nin ilk satırı amacı tek cümleyle verir: "Borsa İstanbul halka arzları için doğruluğu ölçülmüş tahmin modelleri ve onları gömülü çalıştıran bir masaüstü uygulaması." Proje sahibi bilgisayar mühendisliği 3. sınıf öğrencisidir. Öncelik sırası proje bilgi alanındaki strateji belgesinde şöyle yazılı:

1. Güncel yeni halka arzları en doğru tahmin eden, doğruluğu ölçülmüş modeller.
2. Bu modelleri gömülü ve yerel çalıştıran masaüstü uygulaması (Mac, sonra Windows).
3. Hocalara uygulama üzerinden sunum. Sunum Ekim'in ilk haftasında planlandı; `FAZ9_UI_FIX.md` (4 Ekim) "bu hafta hocalarına uygulamayı gösterecek" diyor.
4. Hukuk, SPK ve veri lisansı sonra.

Modellerin cevapladığı sorular, arzın hayatındaki üç ana göre dizilir:

| An | Soru | Bugünkü model |
|---|---|---|
| Listeleme öncesi | Kaç gün tavan yapar? | `ceiling_hazard_v0` |
| Listeleme öncesi | Getirisi ne olur, arz fiyatının üstünde kalır mı? | `v1_5_h99` (V1.5) |
| D1 akşamı | Yarın tavan bozulur mu? | `post_d1_hazard_v0` |
| Kırılma akşamı | Yarın da taban mı? | `break_floor_v0` |

Bu sorulara sonradan "Seri j gün sürdüyse yarın da tavan mı?" eklendi; 4 Ekim'de onun için yeni bir şartname görevi yazıldı (§2.7).

Projeyi bütün süreç boyunca yönlendiren ilkeler, proje sahibinin kendi sözleriyle dosyalarda geçer:

- **"Coin-flip model istemiyorum."** Doğruluğu kanıtlanmamış model ana ekrana girmez. Geçemeyen model silinmez, "araştırma arşivi"ne iner. Kaç fikir denendiği de saklanmaz.
- **Terfi yok, yan yana modeller.** Bir model başka birinin yerine geçmez; "öne çıkan" model önceden yazılmış bir kuralla seçilir (Faz 7 kararı K4).
- **Değişiklik = yeni model_id.** Özellik, ızgara, eğitim kesimi ya da veri sürümü değişirse yeni kimlik verilir; eskisi ve skorları listede kalır (`CLAUDE.md` kural 5).
- **Mekanik olan öğrenilmez, kodlanır.** Örneğin ±%10 bantta D1'den 6 ya da daha fazla tavandan sonra D10 kapanışının arz fiyatının altında olması aritmetik olarak imkânsızdır; model bu sıfırı öğrenmeye veri harcamaz.
- **Yazan el ile denetleyen el ayrıdır.** Şartnameyi Fable yazar, kodu Opus yazar, sonucu yine Fable sıfırdan yeniden üretir.

Kaynak dosyalar: `CLAUDE.md`, `claude/STRATEJI.md` §1–§2, `claude/HANDOFF.md` §2 (proje bilgi alanı), `docs/prompts/FAZ9_UI_FIX.md`, `docs/specs_faz7/KARARLAR.md` K4.

## 2.2 Eski repo (legacy) dönemi ve v2'ye geçiş

### 2.2.1 Eski repo neydi?

Yeni repodan önce proje `~/Desktop/Halka_Arz_Modeli` klasöründeki eski bir depoda yürüdü. Bu depo bugün arşivdir ve yalnız okunur. Yeni repoya oradan seçilmiş dosyalar kopyalandı; kopyalar `legacy/`, `data/raw/`, `registry/legacy_frozen/` ve `tests/reference/` altında durur. `docs/PROVENANCE.md` kopyalamayı dosya dosya belgeler:

- Kopya tarihi 2026-09-21. O an eski deponun HEAD'i `604e2187…`.
- Toplam 87 kopya: `data/raw` 11, `legacy` 21 istenen dosya + import kapanışından gelen 13 yardımcı modül, `registry/legacy_frozen` 29, `tests/reference` 13.
- 77 dosya bayt bayt aynı, 9 dosyada yalnız satır sonu değişti (CRLF→LF), 1 dosya türetildi.
- Türetilen dosya XU100 endeks serisidir. Dosyanın 9 684 kaydından ikisi 2026-08-19'dan sonrasına aitti (20 ve 21 Ağustos). Sıra kuralı yüzünden bu iki kayıt çıkarıldı; çıkarılan değerler hiçbir yere yazılmadı.
- 16 dosya bilerek kopyalanmadı ("Faz 2'de alınacak").

Eski deponun asıl modeli **V1.5** idi. `legacy/config/model_v1_5_spec.json` bunun ön kaydıdır (`BORSAI_V1_5_PREREG_20260814`). Dosyada V1'den V1.5'e beş öncülün zinciri var; hepsi 2026-08-14 tarihli. V1.5 her ufuk (D1, D3, D5, D10) için iki başlıklı küçük bir modeldir: getiri için Ridge regresyonu, "kapanış arz fiyatının üstünde mi" için L2 lojistik regresyon. Beş özellik kullanır: f1 arz büyüklüğü, f2 halka açıklık oranı, f3 toplam talep katı, f4 sermaye artırımı payı, f5 "f3 eksik" bayrağı. Eğitim kümesi H99'dur. Benchmark Windows'ta, Python 3.12.13 ile üretilmişti.

`legacy/` altındaki kod çalıştırılmak için değil, **port için referans** olarak durur. `CLAUDE.md` bunu açıkça söyler: "legacy/ eski repodan birebir kopyadır; değiştirilmez." İçerik üç gruptur:

| Grup | Ne var | Neden alındı |
|---|---|---|
| `legacy/scripts/modeling/` | V1.5 çekirdeği (`candidate_models.py`, `preprocessing.py`, `logistic_policy.py`, `fold_engine.py`, `metrics.py`, `baselines.py`), H99 benchmark koşucusu, talep toplama öncesi (PB) r6 modülleri, market20 onarım çekirdeği, canlı tahmin sözleşmesi | Yeni `borsai/` paketine taşınırken davranışın birebir korunduğunu sınamak (`tests/test_port_vs_legacy.py`) |
| `legacy/scripts/collect_historical99_bist_raw_v1.py` | THB/THM bültenlerini indirip ayrıştıran eski toplayıcı | Sütun eşlemesi ve URL kalıbı yeni `borsai/outcomes.py`'ye örnek oldu |
| `legacy/src/halka_arz_audit/` | Eski "true live" dondurma düzeni (`true_live_freeze.py`, `live_forecast_freeze.py`, `guards.py` …) | Import kapanışı gereği; referans |
| `legacy/artifacts/governance/` | `PRETRADE_EXTENSION_COLLECTION_SPEC` R6 (Markdown + JSON) | Eski veri toplama kurallarının kaydı |

Kaynak dosyalar: `docs/PROVENANCE.md` §Genel, §1, §2; `legacy/config/model_v1_5_spec.json`; `legacy/`; `docs/MODELS.md` (v1_5_h99 ayrıntısı); `CLAUDE.md`.

### 2.2.2 Eski "true live" dondurma düzeni

Eski depoda canlı tahminler `true_live_freeze.py` ile dondurulurdu. Modülün açıklaması bu düzenin ne kadar ağırlaştığını gösterir: bağımsız bir yeniden denetim (`PERSISTENCE_FINAL_GATE_FAIL`) TKNKA dondurmasının "yalnız harici bir dosya olarak FROZEN ilan edildiğini" bulmuş. Bunun üzerine dondurma, her çağrıda çok adımlı bir kapıya bağlanmış: paket şema denetimi, kanonik yol denetimi, bekleyen günlük kurtarma, "gerçek saate karşı" listeleme öncesi zaman penceresi, kayda ekleme, geri okuma… Zaman denetimi makinenin saatine ve kaydın kendi beyanına dayanıyordu.

Yeni repoya bu dondurmalardan yedi kayıt alındı. Hiçbirinin içeriği değiştirilmedi; `registry/legacy_roles.json` yalnız rollerini bağlar:

| Kayıt | Model | Rol | Zaman kanıtı | Not |
|---|---|---|---|---|
| NETGL, 16 Eylül | `v1_5_h99` | birincil | **git + push** (GitHub status `created_at` 2026-09-16T11:32:27Z; D1 = 17 Eylül) | Sicildeki tek gerçek LIVE tahmin |
| BKRGY, 27 Ağustos (talep sonrası) | `v1_5_h99` | birincil | kendi beyanı | f3 = 1.77 |
| INTET, 31 Ağustos (talep sonrası) | `v1_5_h99` | birincil | kendi beyanı | f3 = 1.7 |
| TKNKA, 19 Ağustos | `v1_5_full20` | ayrı model | kendi beyanı | 20 arzla eğitilmiş ayrı model; `v1_5_h99` sütununa yazılmaz |
| BKRGY, 25 Ağustos (iki sürüm) | `v1_5_h99` | geçersiz kullanım | kendi beyanı | f3 yok, f5 = 1; hiçbir metriğe girmez |
| INTET, 25 Ağustos | `v1_5_h99` | geçersiz kullanım | kendi beyanı | f3 yok; talep toplama öncesi |

"Kendi beyanı" (self-reported) kayıtlar ilk kez 6 Eylül'de git'e girmiş; yani tahmin zamanını kanıtlayan bağımsız bir iz yok. Bu yüzden yeni skorlama düzeninde ayrı bir alt satırda dururlar ve kanıtlı canlı metriğe girmezler. NETGL kaydı ise eski depoda commit edilip push edilmiş ve GitHub commit status API'siyle zamanlanmıştı. Yeni repodaki `borsai/push_proof.py` tam olarak bu yöntemi taşır.

Kaynak dosyalar: `legacy/src/halka_arz_audit/true_live_freeze.py` (baş açıklama), `registry/legacy_roles.json`, `registry/legacy_frozen/`, `docs/PROVENANCE.md` §3, `docs/specs/SPEC_SCORING.md` §6, `borsai/push_proof.py`.

### 2.2.3 Neden yeni repo (v2)?

Bu kopyada geçişin gerekçesini tek paragrafta söyleyen bir belge yok. Eski depodaki iki belge, Fable'ın 21 Eylül tarihli denetimi (`docs/fable_audit_20260921/AUDIT.md`) ile envanter (`docs/checkup_20260921/CHECKUP.md`), `CLAUDE.md`'de anılır ama bu kopyada yoktur. Geçişin nedenleri bu yüzden **belirsizdir**; aşağıdakiler dosyalardaki izlerden yapılmış çıkarımdır:

- **Yönetişim yükü.** `docs/DATA_NOTES.md` eski deponun veri hükümlerini özetlerken "yönetişim hükümleri (seviye sınıfları, terfi kapıları, tek kullanımlık yetkiler) bilerek dışarıda bırakıldı" der. Proje bilgi alanındaki HANDOFF, kaldırılan ve geri getirilmeyecek aygıtları sayar: okuma yasağı, eski karantina rejimi, Level A/B, N_A kapıları, terfi merdivenleri, `DECISION_LEDGER`, τ eşikleri, permütasyon testleri. `legacy/artifacts/governance/` altındaki toplama şartnamesi R1'den R6'ya altı revizyondan geçmiş, her biri ayrı bir git etiketiyle; son ikisi 12 Eylül tarihli.
- **Zaman kanıtı.** Eski kayıtların çoğu kendi beyanıyla zamanlanmıştı. Yeni düzende tek kanıt push'tur ve bu kural kodla zorlanır.
- **En az kural, kodla zorlanır.** `CLAUDE.md` kurallarını "dürüst doğruluk için en az set; kodla zorlanır" diye tanıtır. Yeni kural ölçütü HANDOFF'ta yazılıdır: "Bu, doğruluk rakamlarını dürüst tutmak için şart mı?"
- **Denetimin bulguları.** Yeni repodaki görev dosyaları 21 Eylül denetiminin bölümlerine sürekli atıf yapar. Örnekler: V1.5'in f5 katsayısının yalnız iki arzdan öğrenilmesi (§1.2-d), ızgaranın uçlara dayanması (§1.2-e), Windows ile macOS sayısal farkı (§1.2-b), blok bootstrap aralığı (§1.2-c), tavan için ayrık zamanlı hazard modeli önerisi (§3b), tahminin tek uygulamasının Rust'ta olması (§3e). `FAZ1_FABLE_MODEL_SPECS.md` "Senin denetimin … plana işlendi. Yeni repo hazır" diye başlar.

Sonuç olarak v2, eski deponun verisini ve V1.5'ini taşıyan, ama yönetişim aygıtlarını bırakıp yerine altı kodlu kural, push kanıtı ve "yazan el ≠ denetleyen el" düzenini koyan temiz bir başlangıçtır.

Kaynak dosyalar: `docs/PROVENANCE.md` §Genel, §1–§3, `legacy/config/model_v1_5_spec.json`, `legacy/src/halka_arz_audit/true_live_freeze.py` (baş açıklama), `legacy/artifacts/governance/BORSAI_PRETRADE_EXTENSION_COLLECTION_SPEC_20260912_R6/PRETRADE_EXTENSION_COLLECTION_SPEC.md`, `registry/legacy_roles.json`, `registry/legacy_frozen/`, `docs/DATA_NOTES.md`, `docs/prompts/FAZ1_FABLE_MODEL_SPECS.md`, `docs/prompts/FAZ1A_V1_5_PORT.md`, `claude/HANDOFF.md` §5, §12.

## 2.3 Faz faz zaman çizelgesi (21 Eylül – 6 Ekim 2026)

### 2.3.1 Genel tablo

Git geçmişinde 175 commit var. Her commit konusu `BORSAI_` önekiyle başlar ve fazı söyler (`BORSAI_FAZ5_FREEZE`, `BORSAI_APP_P2_B1` …). Aşağıdaki tablo commit'leri fazlara göre gruplar. Saatler İstanbul saatidir (+03:00).

| Faz | Tarih (ilk → son commit) | Commit | Amaç | Ana çıktı | Sonuç |
|---|---|---|---|---|---|
| 0 İskelet | 21 Eyl 19:55 | 1 | Yeni repo, ortam, veri anlık görüntüsü, kurallar | `CLAUDE.md`, `data/training_table.csv`, `docs/DATA*.md` | Temel hazır |
| 1 Çekirdek ve ilk modeller | 21 Eyl 21:14 → 22 Eyl 14:26 | 4 | V1.5 portu, basit kurallar, Fable şartnameleriyle 9 yeni model | `borsai/` çekirdeği, 16 donmuş model | Fable: hepsi PUSH_OK |
| 2 Sicil ve skorlama | 22 Eyl 15:40 → 24 Eyl 03:26 | 6 | Payda, girdiler, kayıtlar, resmi sonuçlar, ilk canlı skor, koşullu skor tanımları | `registry/`, `data/outcomes/`, `scores/scores.json` | 7 arz, n < 10: yalnız satır tablosu |
| 3 Masaüstü uygulaması | 22 Eyl 18:32 → 24 Eyl 01:34 | 16 | Tauri uygulaması, Rust tahmin portu, dondur sihirbazı, doğruluk paneli | `app/`, `docs/app/SPEC_APP*.md` | Fable denetimi: düzeltmeyle uygun → kapanışta UYGUN |
| 4 Tavan yolu | 22 Eyl 19:16 → 23 Eyl 01:07 | 4 | Seriden getiri dağılımına geçen üç model | `ceiling_path_v0`, `@INF`, `pb_ceiling_path_v0` | "Beklentiden çok iyi" → bağımsız yeniden üretim → FREEZE_OK |
| 5 D1 sonrası | 24 Eyl 02:58 → 20:12 | 9 | D1 akşamı bilgisiyle güncellenen model ve canlı POST_D1 aşaması | `post_d1_hazard_v0`, `models/INDEX_POST_D1.json` | Birincil hücre ayırt edilemiyor; Brier k = 2 geçiyor; donduruldu |
| 6 Eski kohort | 24 Eyl 17:22 → 25 Eyl 19:12 | 23 | 2020–2023 arzlarında sonuç görmeden zaman-dışı test | `registry/oot/`, `scores/scores_oot.json` | Tavan modeli eski dönemde KM'yi geçemiyor |
| 7 Tavan serisi v1 | 25 Eyl 19:51 → 27 Eyl 18:03 | 10 | v0'ın eski dönem zaafına üç düzeltme adayı; izahname alanları | `ceiling_hazard_v1_*` (4 kimlik) | İki aday yakın dönemi "bozuyor"; dördü de donduruldu |
| 7C Düşen arz | 27 Eyl 17:12 → 28 Eyl 21:58 | 12 | "Hangi arzlar ilk günlerde düşüyor?" | `fall_d10_v0_*` (4 kimlik), uygulama EK3 şartnamesi | Birincil "belirsiz"; dondu |
| 7 OOT ve kasa | 28 Eyl 23:30 → 29 Eyl 22:59 | 19 | Yeni modellerin eski kohort kayıtları, kasanın tek seferlik açılışı | kasa skorları | Hiçbir v1 ve düşüş adayı öne çıkma kuralını geçemedi |
| Ara: test hızı | 30 Eyl 17:36–17:38 | 2 | Paralel pytest | `pytest-xdist` | Sıralı ≈ 15 dk, paralel ≈ 11 dk |
| Ara: uygulama EK3 | 30 Eyl 21:09 → 1 Eki 21:10 | 24 | v1, D1 sonrası ve düşüş modellerinin Rust portu, yeni kartlar ve panel | P1, P2, P3/P4 | 27 + 1 model uygulamada Python'la tolerans içinde aynı (çoğu satır bit-eşit) |
| Ara: NETGL D10 | 30 Eyl 22:52 → 1 Eki 17:01 | 7 | NETGL'in D4–D10 resmi sonuçları | `docs/live/NETGL_D10_RAPOR.md` | L = 3, D4–D10 taban, D10 −%36,17 |
| 8 Kırılma akşamı | 1 Eki 22:29 → 2 Eki 19:51 | 12 | "Yarın da taban mı?" modeli ve makine sıralı canlı aşama | `break_floor_v0`, `models/INDEX_POST_BREAK.json` | Ürünü ve basit kuralı geçiyor; REPRO_OK; donduruldu |
| 9 Sade görünüm | 3 Eki 13:10 → 6 Eki 14:22 | 8 | Proje sahibinin onayladığı yeni arayüz ve altı düzeltme | `app/src/sade/` | Sunuma hazır |
| Push kanıtları | 22 Eyl 17:06 → 2 Eki 17:45 | 18 | Sıra iddiası taşıyan commit'lerin zaman kanıtı | `registry/push_proofs/` (31 dosya) | — |

Günlere göre commit sayısı da temponun resmini verir: 21 Eylül 2, 22 Eylül 17, 23 Eylül 10, 24 Eylül 20, 25 Eylül 26, 26 Eylül 5, 27 Eylül 13, 28 Eylül 7, 29 Eylül 20, 30 Eylül 11, 1 Ekim 25, 2 Ekim 11, 3 Ekim 5, 6 Ekim 3. En yoğun günler eski kohortun skorlandığı 25 Eylül ile uygulama portlarının ve NETGL sonuçlarının girdiği 1 Ekim'dir.

Donmuş model sayısı zamanla şöyle büyüdü:

| Tarih | Olay | `INDEX.json` | `INDEX_POST_D1.json` | `INDEX_POST_BREAK.json` |
|---|---|---|---|---|
| 21 Eyl | Faz 1A: V1.5 + 6 basit kural | 7 | — | — |
| 22 Eyl | Faz 1B: 9 yeni model | 16 | — | — |
| 22 Eyl | Faz 4: 3 tavan yolu modeli | 19 | — | — |
| 24 Eyl | Faz 5: D1 sonrası model | 19 | 1 | — |
| 27 Eyl | Faz 7: 4 v1 kimliği | 23 | 1 | — |
| 28 Eyl | Faz 7C: 4 düşüş kimliği | 27 | 1 | — |
| 2 Eki | Faz 8: kırılma modeli + kural satırı | 27 | 1 | 2 |

Kaynak dosyalar: `GITLOG.txt`, `models/INDEX.json`, `models/INDEX_POST_D1.json`, `models/INDEX_POST_BREAK.json`, `docs/MODELS.md`.

### 2.3.2 Faz 0 — İskelet (21 Eylül)

Tek commit (`ff3eee6`, "repo, environment, data snapshot, training table, rules"). Bu commit dört şey koydu:

- `CLAUDE.md`: altı kural ve sıra kuralı (§2.4.8).
- `.venv` ortamı ve sabit sürümlü bağımlılıklar (§2.8).
- Eski depodan kopyalanan ham veri ve `data/training_table.csv`: 99 satır, 31 sütun, değerler kaynaktaki metin hâliyle (`Decimal` ile okunur). İlk işlem tarihleri 2023-09-22…2026-08-06, sonuç seansları en geç 2026-08-19.
- Sıra kuralı yüzünden 2026-08-06 sonrası listelenen arzlar tabloya girmedi.

Bu commit aynı zamanda H99'un 99 arzının "sonuç giriş commit'i" sayılır. Bu yüzden H99 her model için RETRO'dur: bütün modeller bu sonuçları gördükten sonra yazıldı (SPEC_SCORING §5).

Kaynak dosyalar: `GITLOG.txt`, `docs/DATA.md`, `docs/specs/SPEC_SCORING.md` §1, §5.

### 2.3.3 Faz 1 — Çekirdek, V1.5 portu ve ilk yeni modeller (21–22 Eylül)

**Faz 1A** (`5fa849d`, 21 Eyl 21:14; Opus). `borsai/` paketi kuruldu: `features.py` (f1–f5'in tek tanımı), `preprocess.py`, `fit.py`, `predict.py`, `backtest.py`. V1.5 eski koddan taşındı ve Windows referansına karşı toleranslı kabul testinden geçti:

- 351 fold'un (ufuk × test arzı) eğitim kümesi hash'leri 351/351 eşit.
- Seçilen Ridge α 351/351, seçilen lojistik C 350/351 eşit.
- Ridge farkı en çok 2.72e-15, lojistik olasılık farkı en çok 3.06e-09.
- Beklenen tek sapma adıyla yazıldı: bir D3 fold'unda lojistik çözücü macOS'ta yakınsamıyor; eski kod da bu makinede aynısını yapıyor.

Testler geçince macOS'taki fold ledger'ları "altın referans" oldu; bundan sonraki regresyon testleri onlara karşı bayt bayt çalışır. Altı basit kural da aynı şemada model olarak donduruldu. Sonuç: 7 model.

**Faz 1 şartnameleri** (`d3fabad`, 22 Eyl 02:55; Fable). Aynı gece, aynı klasörde paralel çalışan bir Fable oturumu beş şartname yazdı: tavan modeli (`SPEC_CEILING_V0`), talep toplama öncesi model (`SPEC_PB_V0`), piyasa modeli (`SPEC_MARKET20_V0`), genişletilmiş ızgaralı V1.5 (`SPEC_V1_6`) ve skorlama tanımları (`SPEC_SCORING`). Her şartname sonuç görülmeden yazılmış bir beklenti taşır ve H99 sonuçlarının "tasarıma maruz" olduğunu açıkça yazar.

**Faz 1B** (`b09cab5`, 22 Eyl 13:10; Opus). Şartnameler koda döküldü, backtest'ten geçti ve donduruldu: `v1_6_h99`, `v1_5_market20_v0`, `pb_v0`, `ceiling_hazard_v0` ve `@INF` uç noktası, `pb_ceiling_v0` ve `@INF`, iki Kaplan–Meier kuralı (`base_km_expanding`, `base_km_last10`). Toplam 16 model.

**Fable uygunluk denetimi** (`1869da6`, 22 Eyl 14:26). Push'tan önce, şartnameyi yazan el kodu denetledi. Çünkü `ceiling_hazard_v0` beklentiden iyiydi: şartname RPS farkını −0.005 … −0.02 bekliyordu, gerçekleşen −0.0496 [−0.0751, −0.0219] oldu. Fable dört fold'u `borsai`'yi import etmeden sıfırdan yeniden üretti, sızıntı bulmadı ve beklentinin "yanlış çapalandığını" yazdı: f3 ile seri uzunluğu arasındaki ilişki güçlü (Spearman 0.55) ve kazanç dört yılda da aynı büyüklükte. Bütün modeller **PUSH_OK** aldı; `SPEC_DEVIATIONS.md`'deki 27 maddenin hepsi kabul edildi.

Backtest'te öne çıkanlar:

| Model | Birincil karşılaştırma | Fark [%95 aralık], n | Hüküm |
|---|---|---|---|
| `ceiling_hazard_v0` | RPS − `base_km_expanding` | −0.0569 [−0.0833, −0.0286], 87 | geçiyor |
| `v1_5_h99` | D5 getiri MAE − eğitim medyanı | −0.0839 [−0.1343, −0.0321], 87 | geçiyor |
| `pb_ceiling_v0` | RPS − `base_km_expanding` | −0.0324 [−0.0544, −0.0114], 87 | geçiyor |
| `pb_v0` | D5 MAE − eğitim medyanı | −0.0355 [−0.0775, +0.0102], 87 | ayırt edilemiyor |
| `v1_6_h99` | D10 MAE − V1.5 | +0.0008 [−0.0003, +0.0028], 87 | ayırt edilemiyor |
| `v1_5_market20_v0` | D5 MAE − V1.5 | −0.0008 [−0.0178, +0.0137], 87 | ayırt edilemiyor |

Faz 1'in asıl önemi zamanlamadır. `CLAUDE.md`'nin sıra kuralı, 2026-08-19 sonrası bülten verisinin ve 2026-08-06 sonrası arzların sonuçlarının, Faz 1 modelleri dondurulup push edilmeden repoya girmesini yasaklar. Böylece yeni arzlar bu modeller için gerçek prospektif örneklem olabildi.

Kaynak dosyalar: `docs/prompts/FAZ1A_V1_5_PORT.md`, `FAZ1_FABLE_MODEL_SPECS.md`, `FAZ1B_NEW_MODELS.md`, `FAZ1B_FABLE_CONFORMITY.md`; `docs/MODELS.md` (Port kabulü, Faz 1B); `docs/fable_conformity_20260922/AUDIT.md`; `docs/SCORES.md` §5; `docs/specs/`.

### 2.3.4 Faz 2 — Sicil, payda, resmi sonuçlar ve skorlama (22–24 Eylül)

**Faz 2A** (`7cb49cf`, 22 Eyl 15:40; Opus). Üç iş yapıldı:

1. Push kanıtı aracı `borsai/push_proof.py` yazıldı (eski depodaki yöntem: GitHub commit status API'si; zaman = sunucunun `created_at` değeri).
2. Payda dosyası `registry/ipos.csv` kuruldu. 2026-08-07'den bu yana işlem görmeye başlayan 7 arz `FROZEN` satırı aldı: CITAS, TKNKA, VEYAS, KPEKS, INTET, BKRGY, NETGL. Varant, sertifika, borsa yatırım fonu, bedelli kalan pay ve kod değişikliği gibi halka arz olmayan bildirimler `OUT_OF_SCOPE` diye nedenleriyle yazıldı.
3. 7 arzın listeleme öncesi girdileri resmi belgelerden toplandı (`registry/inputs/`, `registry/source_docs/`) ve 16 modelin hepsiyle kayıtları yazıldı (`registry/records/`). Bu görevde hiçbir sonuç verisi okunmadı.

**Faz 2B** iki commit'e bölündü ve bu bölünme bilinçliydi:

- **Commit A** (`e469a93`, 17:52): sonuç ve skor tanımları kodda; henüz hiçbir sonuç yok.
- **Commit B** (`f1f9d44`, 18:20): resmi THB/THM sonuçları ve ilk canlı skor.

A'nın B'nin atası olması, "tanımlar ilk skorlamadan önce kodda yazılıdır" kuralının (`CLAUDE.md` kural 6) git'teki kanıtıdır. Bu "A: kod, sonuçsuz → B: sonuçlar" kalıbı projenin geri kalanında her yeni skorlama işinde tekrarlandı.

İlk skorun beklenen tablosu da önceden yazılmıştı ve tuttu: 7 arzın hepsi Faz 1 modelleri için **LATE_RECORD** oldu, çünkü kayıtlar 22 Eylül'de, ilk işlem günlerinden sonra push edildi. Tek LIVE satır NETGL'in eski depodan gelen V1.5 kaydıydı. n = 7 < 10 olduğu için hiçbir metrik ya da hüküm üretilmedi; yalnız satır tablosu.

Görev sırasında iki pürüz çıktı:

- Tamlık denetimi bülten satırlarında açıklanamayan yeni bir kod buldu ve kural gereği durdu. Orkestratör ile proje sahibi kodun yeni bir arz değil, var olan bir payın temerrüt (buy-in) pazarı kodu olduğuna karar verdi. Ek görev (`FAZ2B_EK1_OYAKC.md`) yalnız o koda özel değil, genel bir kural ekletti: pazar ya da enstrüman tipi `BUYIN` ise sınıf `TEMERRUT_PAZARI`.
- 2A görev dosyasındaki "ikinci kayıt ancak iptalden sonra" cümlesi SPEC_SCORING §6 ile çelişiyordu; 2B görevinin 3. adımı bunu düzeltti.

**Faz 2C** (`18ca063` → `483f600`, 24 Eyl 03:06–03:26; Opus). Uygulama, "seri j gün sürdüyse" koşullu olasılığı zaten gösteriyordu, ama bunun canlı isabetini ölçen kod yoktu. Tanım Faz 4 şartnamesinde (§7) push kanıtlıydı. NETGL'in D4–D10'u henüz gelmediği için kodun şimdi girmesi, kuralın gereğiydi. Önce tanımlar ve testler (A), sonra bir sıra düzeltmesi (`097773d`), sonra koşullu bloklar (B) geldi. Her j için n < 10 olduğundan yine hücre üretilmedi.

Kaynak dosyalar: `docs/prompts/FAZ2A_REGISTRY_INPUTS.md`, `FAZ2B_OUTCOMES_SCORING.md`, `FAZ2B_EK1_OYAKC.md`, `FAZ2C_CONDITIONAL_SCORING.md`; `registry/ipos.csv`; `docs/SCORES.md` §1–§2, §6; `docs/SPEC_DEVIATIONS.md` E, G; `borsai/push_proof.py`.

### 2.3.5 Faz 3 — Masaüstü uygulaması (22–24 Eylül)

Faz 3 ve Faz 4'ün şartnameleri aynı commit'te push edildi (`52e1567`, 22 Eyl 18:32). Uygulama şartnamesi (`docs/app/SPEC_APP.md`, Fable, EK 1 dahil) mimariyi şöyle bağladı:

- **Tauri 2** masaüstü kabuğu, **Rust** arka uç, çerçevesiz sade **TypeScript** ön uç. Ağ erişimi yok.
- Tahminin **tek uygulaması Rust'ta** (`app/src-tauri/crates/borsai_predict`). Python'la eşliği altın vektörlerle sınanır: her model için en az 200 girdi, tolerans |Δ| ≤ 1e-9.
- **Ön uç hiç hesap yapmaz.** Bütün sayılar Rust komutlarından gelir. Bu, `no_frontend_math.test.ts` statik taramasıyla zorlanır: çarpma ve bölme yalnız biçimlendirme ve SVG koordinat dosyalarında serbesttir.
- Uygulama skor hesaplamaz; yalnız `scores.json`'u okur. Okuma "fail-closed"dur: bütünlük denetiminden geçmeyen dosya gösterilmez.
- Kişisel senaryo kayıtları sicile ve skora asla girmez.

Aşamalar sırayla geldi: S0 iskelet (`50c62da`), S1 Rust portu ve parite (`0b67f5d`), S2 girdi formu ve sonuç ekranı (`5606772`), EK 2 şartnamesi (Faz 4 modellerinin portu, `c89ff5a`), S3 resmi dondur sihirbazı ve sicil ekranı (`a41f183`), P1 tavan yolu portu (19/19 parite, `4c44bcc`), P2 gösterim (`510f890`), S4 doğruluk paneli (`0341bc6`), S5 dışa aktarma ve cila (`8fa0bf5`, 23 Eyl 12:24).

Bu sırada proje sahibi bir karar verdi (U52, 23 Eylül): kullanıcının "seri sürüyor" beyanı **yalnız etikettir**; hiçbir olasılığa ya da getiri hesabına girmez, resmi j'yi değiştirmez. Kod buna aykırıydı ve düzeltildi (`cf90da2`, `50e6af9`).

**Fable uygulama denetimi** (`70e1c52`, 23 Eyl 13:25). Asıl soru şuydu: uygulama resmi sicile, skora ya da kullanıcının resmi sanacağı bir sayıya yanlış bir şey sokabilir mi? Genel hüküm **DÜZELTMEYLE UYGUN**. Bağımsız parite örnekleminde 2 318 satırda 0 uyuşmazlık çıktı. Üç bulgu kapatılmadan gerçek dondurma yapılmaması istendi:

- **B1 (KRİTİK):** askıda bir sembolik bağ hedefi, kişisel kaydı `registry/` altına yazdırabiliyordu.
- **B2:** ekran mantığını sahte komut çağrısıyla sınayan test yoktu.
- **B3:** dondur düğmesi ön koşul denetimine bakmıyordu.

Düzeltme görevi (`db8e239`, 24 Eyl 00:39; Opus) bir kural koydu: her düzeltmeden önce onu yakalayan test yazılır ve düzeltme öncesi kırmızı olduğu gösterilir. Fable'ın kapanış denetimi (`303416c`) on bulgunun onunun kapandığını mutasyonla doğruladı ve hükmü **UYGUN**'a çevirdi. Kapanışta iki küçük yeni bulgu (C1, C2) açık kaldı; ikisi de değişmezleri etkilemiyor.

Kaynak dosyalar: `docs/prompts/FAZ3_*.md` (13 dosya), `docs/app/SPEC_APP.md`, `docs/app/SPEC_APP_EK2.md`, `app/README.md`, `docs/fable_app_audit/AUDIT.md`, `docs/fable_app_audit/KAPANIS.md`.

### 2.3.6 Faz 4 — Tavan yolu modelleri (22–23 Eylül)

Tavan modeli serinin uzunluğunu verir, getiriyi vermez. Faz 4'ün fikri, donmuş `ceiling_hazard_v0`'ın seri olasılıklarını ±%10 bandın deterministik limit yoluyla ve kırılma sonrası ampirik hücrelerle birleştirip D_h getirisinin dağılımını üretmekti. Yeni serbest parametre sayısı sıfırdı. Üç model yazıldı: `ceiling_path_v0`, sıfır modeli `ceiling_path_v0@INF` ve talep toplama öncesi sürüm `pb_ceiling_path_v0`.

Uygulama ve backtest (`2d0c98e`, 22 Eyl 19:16; Opus) önceden ilan edilen birincil hücrede şunu verdi: D5 getiri MAE'sinde eğitim medyanına karşı −0.1158 [−0.1611, −0.0738], n = 85. Bu, şartnamenin beklentisinden (−0.090 … −0.020) iyiydi. Şartnamenin §6'sındaki "beklentiden çok iyi" denetimi **10 koşulla tetiklendi**. Kural gereği modeller dondurulmadı ve commit mesajı bunu yazdı: "NOT frozen … independent reproduction required".

Fable, ilk uygulamayı görmeden ve `borsai`'yi import etmeden, yalnız şartnameden sıfırdan yeniden üretti (`2e2fd21`, 22:38). Üç ledger'ın 870 hücresinde en büyük fark **0** çıktı; §6'nın 36 satırı birebir aynıydı; sızıntı yoktu. Hüküm üç model için **FREEZE_OK**. Dondurma 30 dakika sonra yapıldı (`a0df5b7`, 23:08). Ertesi gece skor hücreleri `scores.json`'a eklendi (`0c3cb99`), çünkü uygulamanın doğruluk paneli yalnız o dosyayı okuyordu.

Bu üç model için 7 canlı arz RETRO'dur: kayıtları Faz 4'ten önce yazılmıştı.

Kaynak dosyalar: `docs/prompts/FAZ4_FABLE_CEILING_PATH_SPEC.md`, `FAZ4_CEILING_PATH_IMPL.md`, `FAZ4_FABLE_REPRO_AUDIT.md`, `FAZ4_FREEZE.md`, `FAZ4_SCORES_CELLS.md`; `docs/specs_faz4/SPEC_CEILING_PATH_V0.md`; `docs/MODELS.md` Faz 4; `docs/fable_faz4_audit/AUDIT.md`.

### 2.3.7 Faz 5 — D1 sonrası güncelleme (24 Eylül)

Soru: D1 tavan kapandıysa, D1'in bülten bilgisi (tavanda kilit, el değiştirme) "yarın tavan bozulur mu" tahminini iyileştirir mi? Fable'ın şartnamesi (`c20c092`, 02:58; push kanıtı 00:44:25 UTC) modeli şöyle kurdu: donmuş `ceiling_hazard_v0`'ın doğrusal öngörücüsü sabit bir ofset olarak kalır; D2–D10 hazard'ına iki D1 özelliği eklenir; ceza katsayısı λ iç çapraz doğrulamayla seçilir.

Opus önce kodu ve beklenti kurallarını sonuçsuz commit etti (A, `7ce0593`), sonra backtest'i koştu (B, `7d08169`):

- Birincil hücre: koşullu RPS'te `ceiling_hazard_v0`'a karşı −0.0105 [−0.0264, +0.0058], n = 70 → **ayırt edilemiyor**. Şartnamenin beklentisi tuttu.
- "Yarın" (k = 2) Brier'inde −0.0512 → **"beklentiden çok iyi" tetiklendi**.
- Nihai λ = 30; "D1 bilgisi bir şey eklemiyor" başarısızlık koşulu gerçekleşmedi. Proje sahibinin önceden verdiği karar gereği canlı POST_D1 akışı kurulacaktı.

Fable'ın sıfırdan yeniden üretimi (`fe8ed54`) 87 fold'da en büyük farkı 1.5e-11 buldu ve **FREEZE_OK** dedi. Model ayrı bir dizine donduruldu (`7c18c0f` → `models/INDEX_POST_D1.json`), çünkü bu aşamanın kaydı listeleme öncesi değil, D1 akşamı yazılır.

Aynı akşam canlı aşama kuruldu (`660cec1`, `8e3a623`). Kural `CLAUDE.md`'ye girdi: POST_D1 kaydının zaman sınırı D1'i izleyen ilk seans günü 09:40'tır (İstanbul) ve zaman kanıtı yine push'tur. Bu iş sırasında küçük bir kırılma yaşandı: Faz 5'te `predict_hazard.py` davranış değiştirmeden yeniden düzenlenmişti, ama uygulamanın altın MANIFEST'i dosyanın eski sha'sını pinliyordu. Uygulama test betiği kırmızıya döndü; bir Sonnet görevi (`FAZ5_LIVE_B_APPFIX.md`, `23b6479`) pini yeniden bağladı.

Kaynak dosyalar: `docs/prompts/FAZ5_*.md` (6 dosya); `docs/specs_faz5/SPEC_POST_D1_V0.md`; `docs/faz5/IMPL_RAPOR.md`, `FREEZE_RAPOR.md`, `LIVE_RAPOR.md`, `POST_D1_AKISI.md`; `docs/fable_faz5_audit/AUDIT.md`; `docs/MODELS.md` Faz 5.

### 2.3.8 Faz 6 — Eski kohort ve üçüncü terazi (24–25 Eylül)

Canlı sicil yavaş büyür: ayda birkaç arz. Faz 6'nın fikri, donmuş modelleri H99'dan **önceki** dönemde, yani 2020–2023 arzlarında, sonuçlara bakmadan test etmekti. Bu "zaman-dışı" test üçüncü bir terazi oldu.

Fable'ın fizibilite çalışması ve şartnamesi (`b8763fc`, 24 Eyl 17:22) evreni KAP'taki "Payların İşlem Görmeye Başlaması" bildirimlerinden çıkardı: 135 halka arz üyesi (2020: 8, 2021: 52, 2022: 38, 2023: 37) ve halka arzsız bir kotasyon (kapsam dışı). Proje sahibi aynı akşam sekiz kararı onayladı (`docs/specs_faz6/KARARLAR.md`, "sen onaylıyorsan ben de onaylıyorum", 19:58). En önemlileri:

- **D2, kasa:** kohortun %50'si, ilk işlem yılına göre tabakalı ve sabit tohumla (`PCG64(20260924)`) çekilir ve kapalı tutulur. Arşivde ya da toplama günlüğünde maruz kalmış 5 üye çekilişten önce açık kümeye alınır. Sonuç: açık küme 71, kasa 64.
- **D3, üç terazi:** `CLAUDE.md` kural 3 "üç terazi, asla toplanmaz" diye değişti; sıra kuralına eski kohort cümlesi eklendi.
- **D6, karantina:** Günlük bülten o gün işlem gören bütün payları taşır. Kohortta 135 üyenin 127'sinin on seanslık penceresi başka bir üyeninkiyle çakışıyordu. Yani açık kümenin bülteni hemen her zaman kasadan birinin sonucunu da taşır. Karar: bültenler repoya hiç girmez, repo dışında bir karantina klasörüne iner; repoya yalnız açık üyelerin ayıklanmış satırları ve zip'lerin sha pinleri girer. Kasa satırları hiçbir dosyaya yazılmaz; kod bunu testle zorlar.
- **D7, girdiler:** Codex + GPT-6 Astra (repo dışında, web açık) girdileri resmi belgelerden çıkarır; Claude Code her değeri yeniden indirilmiş belgede birebir doğrular.

Girdi toplama dört partide yapıldı (34 + 26 + 38 + 37 arz). Doğrulama görevi (`FAZ6_VERIFY_CODEX_INPUTS.md`, Opus, repo dışına yazdı) şunu raporladı: 135/135 dosya repo doğrulayıcısından geçiyor; f3 135'te 130'a çıktı; Codex'in 1 702 değerinin %98,4'ü birebir doğrulandı; rastgele 10 arzda 200/200 alan doğru.

Sonra adımlar sıkı bir sırayla ilerledi. Her adımın commit'i push edilip kanıtlanmadan bir sonraki başlamadı:

| Adım | Commit | Ne |
|---|---|---|
| A altyapı | `1d4913e` | kohort sicili, kasa çekilişi, rejim etiketleri, takvim C, bekçiler; kayıt ve sonuç yok |
| S1 | `2e088c3` | 135 üye, kasa, doğrulanmış girdiler |
| Fable denetimi | `af915b8` | **S2_OK**; kasa çekilişi metinden bağımsız 135/135 yeniden üretildi |
| S2 | `1dcceff` | 135 üye × 19 model tahmin kaydı, hiçbir bültenden önce |
| S3 | `9e1e992`, `7ade6a8` | açık kümenin D1 satırları; ardından D1 sonrası kayıtlar (makine sıralı) |
| S5 | `77b54f7` | açık kümenin D1–D10 sonuçları |
| Fable kör hesap | `aea4082` | Opus'un skorlarından önce bağımsız yeniden hesap |
| S6 | `cf60cea` | `scores/scores_oot.json`, `docs/SCORES_OOT.md` |
| Fable karşılaştırma | `e560699` | **S6_OK** |

Açık kümedeki sonuçlar (zaman-dışı terazi):

- Sekiz listeleme öncesi modelin altısı birincil hücresinde karşılaştırıcısından ayırt edilemiyor.
- `ceiling_hazard_v0`, KM kuralına karşı **geçemiyor**: +0.069 [+0.001, +0.131], n = 68. Model bu kohortta serileri olduğundan uzun görüyor.
- `post_d1_hazard_v0`, `ceiling_hazard_v0`'ın koşullu eğrisine karşı **geçiyor**: −0.042 [−0.066, −0.020], n = 59.

Kaynak dosyalar: `docs/prompts/FAZ6_*.md` (14 dosya); `docs/specs_faz6/FEASIBILITY.md`, `SPEC_OOT_PRE_H99_V0.md`, `KARARLAR.md`; `docs/faz6/INFRA_RAPOR.md`, `S2_RAPOR.md`, `S3_S5_RAPOR.md`, `S6_RAPOR.md`, `S6_FIX_RAPOR.md`; `docs/faz6/dogrulama/REPORT.md`; `docs/fable_faz6_audit/AUDIT.md`; `docs/fable_faz6_s6/AUDIT.md`.

### 2.3.9 Faz 7 — Tavan serisi v1 ve izahname alanları (25–27 Eylül)

Eski kohort testi `ceiling_hazard_v0`'ın bir zaafını gösterdi. Fable'ın tanısı (keşif etiketli) hatayı iki parçaya ayırdı: yaklaşık yarısı ekstrapolasyondu (eski arzlar nominal TL'de H99'dan çok küçüktü; 68 skorlanan arzın 40'ı eğitimin 5. yüzdeliğinin altındaydı), kalanı dönem farkıydı. Şartname (`6a16c16`, 25 Eyl 19:51; push kanıtı 18:09:45 UTC) bunun için iç içe üç aday yazdı:

- (a) `ceiling_hazard_v1_clip`: üç özellik eğitim aralığının 5. ve 95. yüzdeliklerine kırpılır.
- (b) `ceiling_hazard_v1_real`: arz büyüklüğü TÜİK TÜFE'siyle reel hâle getirilir (ay kuralı: ilk işlem ayı − 2).
- (c) `ceiling_hazard_v1_pooled`: H99'a eski kohortun açık kümesi eklenir (talep katı dolu 165 arz) ve cezasız bir dağıtım rejimi terimi konur; canlıda bu terim 0'dır.

Proje sahibi 25 Eylül 18:59'da orkestratöre yetki verdi ("planları kendin düzenle"); orkestratör açık soruları `docs/specs_faz7/KARARLAR.md`'de (K1–K5) kapattı. En önemlisi K1: kasa, "düşen arzlar" şartnamesi de push edilince **bir kez ve birlikte** açılacaktı.

Opus kodu, TÜFE serisini ve ikinci eğitim tablosunu (`data/training_table_v2.csv`) sonuçsuz commit etti (`2a21a96`), backtest'i ertesi gün koştu (`70b67d1`). Önceden ilan edilen "yakın dönem" hücresi (ilk işlem ≥ 2024-01-01, adayın `ceiling_hazard_v0`'a karşı RPS farkı) şunu verdi:

| Aday | Fark [%95 aralık], n = 78 | Etiket |
|---|---|---|
| `v1_clip` | −0.0011 [−0.0066, +0.0049] | tolerans içinde |
| `v1_real` | +0.0104 [+0.0028, +0.0183] | **bozuyor** |
| `v1_pooled` | +0.0289 [+0.0089, +0.0518] | **bozuyor** |

Yani eski arzları eğitime katmak bugünkü dönemi bozuyordu. Proje sahibinin sorusunun cevabı buydu. Fable'ın bağımsız yeniden üretimi (`eda9732`) en büyük farkı 4.3e-11 buldu ve dört kimliğe **FREEZE_OK** dedi. Etiketler dondurma kararına girmez (şartname §6.4); dördü de donduruldu (`66adbca`, 27 Eyl 17:39). INDEX 23 girişe çıktı. Uygulama bu dört kaydı bir sonraki uygulama görevine kadar "tanınmayan model" olarak yok saydı (`7133991`, SPEC_DEVIATIONS J31).

Paralelde bir veri işi yürüdü: eski kohortun 135 üyesi için izahnameden 7 aday alan (dağıtım yöntemi, fiyat istikrarı, satmama süreleri, sektör …). Codex dört partide çıkardı, Opus doğruladı (`FAZ7_VERIFY_PROSPECTUS.md`), Sonnet repoya aldı (`4e081d8`). Codex'in "OK" dediği 532 değerin 521'i (%97,9) birebir doğrulandı, 11'i düzeltildi.

Kaynak dosyalar: `docs/prompts/FAZ7_FABLE_HAZARD_V1_SPEC.md`, `FAZ7_HAZARD_V1_IMPL.md`, `FAZ7_FABLE_V1_REPRO_AUDIT.md`, `FAZ7_FREEZE.md`, `FAZ7_CODEX_PROSPECTUS_B1…B4.md`, `FAZ7_VERIFY_PROSPECTUS.md`, `FAZ7_PROSPECTUS_INTAKE.md`; `docs/specs_faz7/`; `docs/faz7/IMPL_RAPOR.md`, `FREEZE_RAPOR.md`, `docs/faz7/prospectus/REPORT.md`; `docs/fable_faz7_audit/AUDIT.md`; `docs/MODELS.md` Faz 7.

### 2.3.10 Faz 7C — Düşen arz modeli (27–28 Eylül)

Soru: "Hangi halka arzlar ilk on günde arz fiyatının altına düşüyor?" Fable önce bir keşif yaptı (`docs/specs_faz7_c/KESIF.md`): H99 ve açık küme, toplam 170 arz, 2 054 varyant denendi. Bulgu: düşenlerin ortak yanları ek satışın kullanılmış olması (19 arzın 12'si, %63; kullanılmayanlarda %20), düşük talep katı ve büyük reel arz büyüklüğü. Keşif açıkça "sonuçlar görüldükten sonra, 2 054 varyant denenerek" yazıldı ve bütün varyantlar deney günlüğüne `kind: exploration` satırı olarak girdi.

Şartname (`4fe4e51`) üç aday ve bir kural satırı tanımladı: `fall_d10_v0_h99`, `fall_d10_v0_pooled`, `fall_d10_v0_addsale` ve `fall_d10_v0_pooled@ZERO`. Kararlar `KARARLAR_C.md`'de (C1–C5) yazıldı; örneğin ek satış alanı boşsa model 0 varsaymaz, reddeder.

Uygulama (`3c93f9c` → `acaca2d`; Opus) ve Fable'ın yeniden üretimi (`80670cb`: en büyük fark 0, 16 mutasyonun 16'sı kırmızı, **FREEZE_OK**) sonrasında dört kimlik donduruldu (`ce569a8`, 28 Eyl 21:30). INDEX 27 girişe ulaştı. Birincil hücre ("eski arzları eğitime katmak bozar mı": `pooled − h99`, D10 Brier) −0.0058 [−0.0340, +0.0219], n = 75 → **belirsiz**.

Bu fazda uygulamanın üçüncü eki de yazıldı (`7be8394`, `docs/app/SPEC_APP_EK3.md`): v1 portu ve TÜFE tablosu, "kaç gün tavan" özet kartı, D1 sonrası satırı, zaman-dışı panel ve düşüş kartı.

Kaynak dosyalar: `docs/prompts/FAZ7_FABLE_C_SPEC.md`, `FAZ7_C_IMPL.md`, `FAZ7C_FABLE_REPRO_AUDIT.md`, `FAZ7C_FREEZE.md`, `FAZ7_FABLE_APP_EK3_SPEC.md`; `docs/specs_faz7_c/`; `docs/faz7c/`; `docs/fable_faz7c_audit/AUDIT.md`; `docs/MODELS.md` Faz 7C.

### 2.3.11 Faz 7 OOT ve kasanın açılışı (28–29 Eylül)

Kasa açılmadan önce yeni sekiz modelin (4 v1 + 4 düşüş) de eski kohort için tahmin kaydı olmalıydı. 135 ek kayıt yazıldı (`28aaa3b`, 29 Eyl 00:02): her biri tam 8 model, ilk kayıtla bayt-eşit girdiler, sonuç alanı yok. Bu sırada bir hijyen olayı yakalandı (§2.6). Skorlar 27 modelle yeniden üretildi (`cd22222`).

Kasa aynı gün, tek sefer açıldı:

| Adım | Commit | Ne |
|---|---|---|
| Kod | `1b2fe00`, `439a808` | açılış sürücüsü, iki kipli bekçiler; tarih biçimi düzeltmesi |
| VA1 | `2f914dd` (16:15) | bültenler pinlere karşı yeniden indirildi; kasanın 64 D1 satırı; `VAULT_OPEN.json` |
| VA2 | `5a96e25` | kasa üyeleri için D1 sonrası kayıtlar |
| VB | `71b9071` (19:47) | kasanın D1–D10 sonuçları |
| Fable kör hesap | `38d36e8` (21:05) | skorlardan önce bağımsız hesap ve seçim kuralları |
| Skor | `ff49828` (21:46) | kasa ve "açık + kasa" anahtarları |
| Fable karşılaştırma | `ca544cd` (22:59) | **VAULT_SCORE_OK**: 34 hücrenin hepsi birebir |

Kasanın sonuçları (zaman-dışı terazi):

- Tavan v1 adaylarından yalnız `v1_pooled` KM kuralını geçiyor: −0.040 [−0.067, −0.012], n = 62. Üç aday da kasada `ceiling_hazard_v0`'ı geçiyor.
- `ceiling_hazard_v0` kasada KM'den ayırt edilemiyor; açık + kasa toplamında (n = 130) geçemiyor: +0.071 [+0.012, +0.126].
- Düşüşte `fall_d10_v0_pooled` taban oranı geçiyor: −0.045 [−0.092, −0.002], n = 60. Ama hiçbir aday kasada V1.5'i geçemiyor.
- `post_d1_hazard_v0` kasada ayırt edilemiyor (−0.035 [−0.072, +0.004], n = 45); açık + kasa toplamında geçiyor (−0.039 [−0.060, −0.017], n = 104).

Önceden yazılmış seçim kurallarına göre sonuç: **hiçbir v1 adayı tavan kartında öne çıkamaz** (pooled'ın yakın dönem etiketi "bozuyor"), `ceiling_hazard_v0` birincil kalır; **hiçbir düşüş modeli öne çıkmaz**. Kasa bir kez açıldı ve harcandı.

Kaynak dosyalar: `docs/prompts/FAZ7_OOT_RECORDS.md`, `FAZ7_VAULT_OPEN.md`, `FAZ7_FABLE_VAULT_RECOMPUTE.md`, `FAZ7_VAULT_SCORE.md`; `docs/faz7_oot/RAPOR.md`; `docs/faz7_vault/RAPOR.md`, `SKOR_RAPOR.md`; `docs/fable_faz7_vault/AUDIT.md`.

### 2.3.12 Ara işler: test hızı, uygulama EK3 ve NETGL D10 (29 Eylül – 1 Ekim)

**Test hızı** (`f23df7a`, `a9ffa4a`, 30 Eylül; Sonnet). Tam `pytest` koşusu 20–30 dakikaya çıkmıştı ve her oturum bunu birkaç kez koşuyordu. `pytest-xdist` eklendi. Proje sahibinin kuralı açıktı: hız için hiçbir kontrol zayıflatılmaz, hiçbir test atlanmaz. Paralel koşu sıralıyla aynı 864 testi aynı sonuçla verdi. Varsayılan sıralı kaldı; her görevin son kabul koşusu sıralıdır.

**Uygulama EK3** (30 Eyl 21:09 → 1 Eki 21:10; Opus, üç görev):

- **P1:** v1 ailesinin Rust portu, TÜFE tablosu ve sonuç sayfasının başına "Tavan serisi — kaç gün tavan?" kartı. Proje sahibinin asıl isteği buydu: tahmin ilk bakışta görünsün.
- **P2:** `post_d1_hazard_v0`'ın Rust portu (238/238 parite; gerçek D1 verisiyle 71/71), D1 sonrası satırı ve D1 akşamı kayıt sihirbazı.
- **P3/P4:** düşüş ailesinin portu (635/635 satır bit-eşit), "Düşüş (D10)" kartı ve "Zaman-dışı test (eski kohort)" paneli. Kart, kasa sonucuna göre hiçbir modeli öne çıkarmıyor.

Bu üç görevden sonra 27 + 1 model uygulamada Python'la aynı sonucu veriyordu: altın vektörlerde fark \|Δ\| ≤ 1e-9, satırların çoğunda bit-eşit; bilinçli tek fark logaritma yoludur (§7.11).

**NETGL D4–D10** (`3b4d785` → `0d3e1ad`; Sonnet). NETGL'in D10'u 30 Eylül'dü. Görev resmi bültenleri indirdi ve sonuçları girdi: D1–D3 tavan, D4'ten D10'a yedi gün art arda taban; **D10 getirisi −%36,17**. Görev sırasında üç bekçi test kırmızıya döndü ve oturum her seferinde durdu (§2.6).

Kaynak dosyalar: `docs/prompts/INFRA_TEST_SPEED.md`, `FAZ7_APP_P1.md`, `FAZ7_APP_P2.md`, `FAZ7_APP_P3P4.md`, `LIVE_NETGL_D10.md`; `docs/infra/TEST_SPEED_RAPOR.md`; `docs/ENV.md`; `docs/app/p1/RAPOR.md`, `p2/RAPOR.md`, `p34/RAPOR.md`; `docs/live/NETGL_D10_RAPOR.md`.

### 2.3.13 Faz 8 — Kırılma akşamı (1–2 Ekim)

NETGL'in yolu yeni bir soru doğurdu: seri **tabanda kapanarak** bozulunca ne olur? Hiçbir model serinin nasıl bozulduğunu kullanmıyordu. Fable'ın görev dosyasına proje sahibinin iki kararı bağlayıcı olarak yazıldı:

- **"Bize bugün lazım"** (29 Eylül): eğitim yalnız güncel dönemle (H99) yapılır.
- **"Hiçbir modelimizin geçmişte başarılı olması gerekmez"** (1 Ekim): eski dönem testi yapılmaz. Kapı iki aşamalıdır: yakın dönem backtest'i yalnız ön elemedir, asıl sınav canlı sicildir.

Şartname (`7d78d43`, 1 Eki 22:29) önce "değer mi" sorusunu cevapladı. "D10 ≤ arz" hedefi için **dur** dedi (beklenen ideal kazanç ≈ −0.008, ayırt edilemez); onun yerine parametresiz bir yastık kuralı yeterliydi. Şartname birincil hedefi "ertesi seans taban kapanışı" olarak belirledi. Model iki özellikli küçük bir lojistikti: `b_floor` (kırılma günü kapanışı alt limitte mi) ve `b_turnover` (el değiştirme). Karşılaştırıcı, ürünün bugün verdiği cevaptı (`PRODUCT_BREAK_FLOOR`, tavan yolu modelinden türetilen olasılık). Aynı commit'e 1 Ekim tarihli piyasa araştırması da girdi (§2.6.9).

Sonra adımlar aynı kalıpla ilerledi: kararlar ve bant doğrulaması (`5d84e88`), sonuçsuz kod (`fa623df`), backtest (`df338c2`), rapor, Fable yeniden üretimi (`6d3f674`, **REPRO_OK**, en büyük fark 0, 13/13 mutasyon kırmızı), dondurma (`4d3c9a2`, 2 Eki 16:21 → `models/INDEX_POST_BREAK.json`), push kanıtı (`fd88be3`).

| Hücre (yakın dönem, n = 69, 21 ay) | Fark [%95 aralık] | Not |
|---|---|---|
| F1 Brier − ürünün cevabı (birincil) | −0.1904 [−0.2520, −0.1247] | "beklentiden çok iyi" tetiklendi |
| F1 Brier − sabit oran (`@ZERO`) | −0.0281 [−0.0453, −0.0074] | kazanç küçük ama aralık 0'ı dışlıyor |

Büyük farkın bir kısmı karşılaştırıcının zayıflığından gelir: ürün, taban üstünde bozulan arzlara ertesi gün ≈ 0.57 taban olasılığı veriyor, gözlenen 0.12. El değiştirme özelliğinin işareti beklentinin tersi çıktı (bilgi eklemiyor). Bu uyarılar karta yazıldı.

Canlı aşama da aynı gün kuruldu (`71cf079`, `7ee0027`). Burada yeni bir fikir uygulandı: **makine sıralı kayıt**. Kırılma akşamı insan kayıt yazmaz; `python -m borsai.scoring --break` tahmini, donmuş model JSON'undan ve sha-pinli bültenlerden skorlama anında deterministik üretir ve `registry/post_break/` altına yalnız ekleyerek yazar. Bu satırlar `MACHINE_SEQUENCED` sınıfıyla ayrı bir ölçekte (`live_break`) sayılır. `CLAUDE.md` kural 1'e bunun cümlesi aynen eklendi. Akşam işi sıfıra indi ve push kanıtı gerekmez. Bugünkü 7 arz bu model için RETRO'dur.

Kaynak dosyalar: `docs/prompts/FAZ8_FABLE_BREAK_SPEC.md`, `FAZ8_BREAK_IMPL.md`, `FAZ8_FABLE_REPRO_AUDIT.md`, `FAZ8_FREEZE.md`, `FAZ8_LIVE_BREAK.md`; `docs/specs_faz8/SPEC_BREAK_V0.md`, `KARARLAR.md`; `docs/faz8/IMPL_RAPOR.md`, `BANT_DOGRULAMA.md`, `FREEZE_RAPOR.md`, `LIVE_RAPOR.md`, `POST_BREAK_AKISI.md`; `docs/fable_faz8_audit/AUDIT.md`; `docs/MODELS.md` Faz 8.

### 2.3.14 Faz 9 — Sade görünüm ve sunum öncesi düzeltmeler (3–6 Ekim)

Yeni arayüz Claude Design kanvasında üretildi ve proje sahibi 3 Ekim'de onayladı ("Tamam yapalım bu arayüzü"). Tasarım 12 panodan oluşur (Monitör, Yeni arz girişi, Tahmin sonucu, Analiz, Model performansı, Sicil, iki sihirbaz, Kayıtlarım, Ayarlar ve Hakkında, stil rehberi, palet seçenekleri); uygulanan palet "Safir". `FAZ9_APP_UI.md` görevi (Opus) bunu "sade görünüm" olarak kurdu (`b48b29a` → `b045e71`, 3 Ekim). Kurallar:

- Eski arayüz silinmez; "Ayrıntılı görünüm" adıyla kodu ve testleriyle aynen kalır. Seçim Ayarlar'da.
- Bütün sayılar Rust'tan gelir. Yeni salt okuma komutları yazıldı: `monitor_view`, `arz_view`, `break_view`, `perf_view`, `headline_gate`.
- **Ana ekran kapısı veri-güdümlüdür:** bir çıktı ancak önceden ilan edilmiş birincil hücresinin hükmü dosyada "geçiyor" ise öne çıkar. Ön uçta elle liste yoktur.
- Proje sahibinin eski arayüzde bulamadığı "Seri j gün sürdüyse yarın ne olur?" hesaplayıcısı görünür yapıldı.

Proje sahibi yeni görünümü kullandı ve altı sorun buldu. `FAZ9_UI_FIX.md` (4 Ekim; Opus) yalnız bu altı maddeyi kapattı (`317304a` → `ee3796d`, 6 Ekim): Analiz'den arz listesine dönüş, Sicil künyesinin görünür olması, hesaplayıcıda "geçmiş arzlarda" karşılaştırması ve gün grubu notu, işlem sayısı çubukları, performans sayımlarının ayrılması ve pencere boyutu (1440 × 900). Son derleme `BorsAi.app` 8,4 MB.

Kaynak dosyalar: `docs/prompts/FAZ9_APP_UI.md`, `FAZ9_UI_FIX.md`; `docs/design/ui_v2/`; `docs/app/UI_V2_HARITA.md`, `UI_V2_RAPOR.md`, `UI_FIX_RAPOR.md`, `ui_fix_test_runs.txt`; `app/README.md`.

## 2.4 Çalışma biçimi

### 2.4.1 Roller

Proje bir kişinin projesidir, ama işi altı ayrı "el" yapar. Her elin ne yapıp ne yapmadığı yazılıdır.

| Rol | Ne yapar | Ne yapmaz |
|---|---|---|
| **Proje sahibi** | Oturumları başlatır, oturum bitince "bitti" der, push eder, onay verir, yeni arzları haber verir, arayüz tasarımını onaylar | — |
| **Orkestratör** (claude.ai proje sohbeti) | Planı yönetir; görev dosyalarını yazar (`docs/prompts/`); raporları diskten okuyup kilit sayıları kendisi yeniden hesaplar; kullanıcıya push bloğunu verir | Kod yazmaz, commit atmaz, push etmez. Git'i yalnız okuma komutlarıyla ve `GIT_OPTIONAL_LOCKS=0` önekiyle kullanır |
| **Claude Code / Opus** (önce "Opus 5", Faz 5'ten itibaren "Opus 5.5"; ayar Extra ya da yüksek) | Ana mühendis: kod, modelleme, backtest, dondurma, uygulama | Şartname yazmaz, kendi işini denetlemez |
| **Claude Code / Sonnet 5** (yüksek) | Mekanik işler: sonuç güncellemesi, test altyapısı, pin onarımı, veri alma, TÜFE ekleme | Model tasarlamaz |
| **Claude Code / Fable** (yüksek) | Şartname ve karar listesi yazar (önce "değer mi"), bağımsız yeniden üretim yapar, uygunluk ve sızıntı denetler | Uygulama kodu yazmaz; yazdığı şartnamenin kodunu yazan el olmaz |
| **Codex + GPT-6 Astra** (repo dışında) | Web ağırlıklı veri toplama: resmi belgelerden girdi ve izahname alanları | Repoya yazmaz; çıktısı her zaman Claude Code tarafından resmi belgede doğrulanır |

Bu dağılımın iki gerekçesi var. Birincisi, şartnameyi yazan elin kodu da yazması, şartnamenin koda göre "uydurulması" riskini doğurur. İkincisi, beklenenden iyi bir sonuç ya gerçek bir bulgudur ya da sızıntı veya hatadır; bunu ayırmanın yolu, ilk uygulamayı görmemiş bir elin sonucu sıfırdan yeniden üretmesidir.

Kullanıcının terminaline verilen komutlar için de kurallar var: macOS ve zsh; her blok `cd ~/Desktop/BorsAi` ile başlar ve yorum satırı içermez; regex, ünlem, dolar ya da ters tırnak içeren Python tek satırlıkları `python3 -c` ile değil, `/tmp`'ye yazılan bir heredoc ile verilir.

Kaynak dosyalar: proje talimatı (proje bilgi alanı: `claude/PROJE_TALIMATI.md`), `claude/HANDOFF.md` §3–§4, `docs/prompts/` (model satırları), `docs/prompts/FAZ6_CODEX_INPUTS_B1.md`.

### 2.4.2 Görev dosyası düzeni

Her iş repo içinde bir Markdown dosyası olarak yazılır: `docs/prompts/<FAZ>_<AD>.md`. Kullanıcı Claude Code'da yeni bir oturum açar, modeli ve akıl yürütme ayarını seçer ve tek cümle yazar:

> `docs/prompts/<DOSYA>.md dosyasını oku ve oradaki görevi uygula.`

Görev dosyası, oturumun sormadan çalışabileceği kadar eksiksiz olmalıdır. Zamanla oturmuş iskelet şudur:

| Bölüm | İçerik |
|---|---|
| Başlık | `TASK_ID` (ör. `BORSAI_FAZ8_FREEZE_20261002`); **model ve ayar en başta** (ör. "Model: Claude Code / Opus 5.5 · Extra"); klasör; ağ izni; git izni ("push/tag/amend yok") |
| Rol | Oturumun bu işteki kimliği ("şartnamesini yazarsın", "ana mühendissin", "veri bakımcısısın") |
| Bağlam | Ne değişti; **orkestratörün ölçtükleri** (tarih ve HEAD ile); tuzaklar; orkestratör veriye baktıysa **maruziyet beyanı** |
| Kararlar | Proje sahibinin bağlayıcı kararları ve görev kararları (`K-FRZ-1`, `K-UI-4`, `K-FIX-3` …) |
| Önceden onaylı pinler | Görevin bilerek kıracağı testler ve yerine gelecek genel kural (`K-PIN`) |
| İzinli izlenmeyen / Paralel | Çalışma ağacında bulunabilecek başka dosyalar; aynı anda çalışan oturumlar ve onların yolları |
| ÖNCE OKU | Okunacak dosyaların listesi, bölüm numaralarıyla |
| Adımlar | 0: taban (`git log`, `git status`, tam test); 0b: geçici klonda prova; sonra iş adımları |
| Beklenen sayılar | Orkestratörün önceden hesapladığı değerler; oturum bunları tutturmalı |
| Tek oturumda bitmezse | Nerede durulacağı |
| Kurallar | Yazılabilir ve salt okunur yollar; hijyen; **açık `git add` yolları** ve commit mesajı; `git add -A` yasak; `index.lock` hatasında beklemek |
| Teslim | Raporun içeriği (commit hash'leri, sayılar, sapmalar) |
| Kabul kapısı | `K1`…`K5` gibi denetlenebilir şartlar |

Dosyalar zamanla büyüdü. İlk görevler (`FAZ1A_V1_5_PORT.md`, 6,7 KB) birkaç paragraftı ve model satırı düz metindi ("Model: Opus 5, akıl yürütme yüksek"). Sonrakiler hem uzadı hem kalıplaştı: en büyüğü `FAZ7_VAULT_OPEN.md` (26 KB). 79 dosyanın toplamı yaklaşık 836 KB'tır. 2 Ekim'de proje sahibi, görev mesajlarında model ayarının her zaman en başta ve kalın yazılmasını istedi; `FAZ9_APP_UI.md`'den itibaren dosyalar `**Model: Claude Code / Opus 5.5 · Extra**` satırıyla açılır.

Ek dosyalar (`…_EK1.md`) ana görev sürerken çıkan bir durağın kararıdır. Örnekler: `FAZ2B_EK1_OYAKC.md` (tamlık durağı) ve `FAZ6_S3_S5_EXTRACT_EK1.md` (takvim C kapanışları için bülten kanıtı).

Kaynak dosyalar: `docs/prompts/*.md` (79 dosya), özellikle `FAZ8_FREEZE.md`, `FAZ8_LIVE_BREAK.md`, `FAZ9_APP_UI.md`; `claude/HANDOFF.md` §2, §6.

### 2.4.3 Bir modelin yolu

Faz 4'ten Faz 8'e her yeni model aynı yoldan geçti. Faz 8'in commit zinciri bu yolu adım adım gösterir:

| # | Adım | Kim | Faz 8 commit'i |
|---|---|---|---|
| 1 | Şartname ve kararlar; önce "değer mi" (§0) | Fable | `7d78d43` |
| 2 | Proje sahibi kararları (karar listesinin §C'si); dondurmadan önce commit ve push | orkestratör, proje sahibi | `5d84e88` |
| 3 | **A:** kod, testler, beklenti kuralları; gerçek veride sonuç yok | Opus | `fa623df` |
| 4 | **B:** resmi walk-forward backtest, altın ledger, `MODELS.md` bölümü; model **dondurulmaz** | Opus | `df338c2` |
| 5 | **R:** uygulama raporu | Opus | `c84ba64` |
| 6 | Sıfırdan bağımsız yeniden üretim, sızıntı denetimi, mutasyonlar | Fable | `6d3f674` |
| 7 | **K:** denetim notları ve dondurma kodu; **F1:** yalnız model dosyaları ve dizin; **F2:** testler ve notlar | Opus (ayrı oturum) | `74b851a`, `4d3c9a2`, `57dcd0c` |
| 8 | Push + kanıt | proje sahibi | `fd88be3` |
| 9 | Canlı aşama: önce kod (A), sonra çıktılar (B), sonra rapor (R) | Opus | `71cf079`, `7ee0027`, `5de4c27` |
| 10 | Uygulama portu ve kartı | Opus | (EK 5; henüz yok) |

Bu yolun dört dayanağı vardır:

- **Önceden yazılmış beklenti.** Şartname her hücre için beklenen fark aralığını ve "aralık 0'ı dışlar mı" cümlesini sonuç görülmeden yazar. Etiket kuralları (tuttu, tutmadı, daha iyi, daha kötü) A commit'inde koda girer (`OPERATIONAL_RULES_FAZ4` … `FAZ8`).
- **"Beklentiden çok iyi" eşiği.** Aşılırsa uygulama raporunda açıkça yazılır ve bağımsız yeniden üretim zorunludur.
- **A'nın B'nin atası olması.** Kuralların ve kodun sonuçtan önce yazıldığının git'teki kanıtı budur.
- **Dondurmanın ayrı oturumda yapılması.** Dondurulan JSON, Fable'ın denetlediği nihai fit önizlemesiyle `created_at`, `code_version` ve `runtime` dışında birebir aynı olmalıdır. Dondurma temiz ağaçta yapılır (`borsai_dirty = false`).

Kaynak dosyalar: `GITLOG.txt`, `docs/MODELS.md` (her fazın "Dondurma" alt bölümü), `docs/faz8/FREEZE_RAPOR.md`, `claude/HANDOFF.md` §6.

### 2.4.4 "Ölçmeden aktarma yok"

Proje talimatının kısa bir kuralı vardır: handoff'tan, eski rapordan ya da hafızadan gelen hiçbir öncül ölçülmeden kullanılmaz; bu, orkestratörün kendi sayıları için de geçerlidir. Bir rapor geldiğinde sorulacak soru "emri uyguladı mı" değil, "uygulanmış mı"dır. Kural dosyalarda birkaç biçimde görünür:

- **Görev dosyalarında "Orkestratörün ölçtükleri."** Örneğin `FAZ9_APP_UI.md` yedi ölçümle başlar (hangi testin hangi değişiklikte kırılacağı, hangi veri dosyalarının var olduğu …). `FAZ2C_CONDITIONAL_SCORING.md` beklenen sayıları verir ve ekler: "Bu beklentiyi kendin ölç; tutmazsa nedenini yaz."
- **"Beklenen sayılar" tablosu.** `FAZ8_LIVE_BREAK.md`'de orkestratör 7 arzın kırılma tahminini önceden yalnız standart kütüphaneyle hesapladı. Oturum aynı değerleri üretti; fark 0.0 çıktı (`docs/faz8/LIVE_RAPOR.md` §0).
- **Fable raporlarında [ÖLÇTÜM] / [ÇIKARIM] ayrımı.** Fable'ın Faz 5 denetimi: "MODELS.md'den ya da IMPL_RAPOR'dan alınan hiçbir sayı yeniden hesaplanmadan kullanılmadı."
- **Bu kitap.** Bu bölümdeki örneğin 7 canlı arzın medyan seri tahminleri ve kırılma olasılıkları, yazılırken kayıt dosyalarından yeniden hesaplandı.

Kural bozulduğunda ne olduğu da kayıtlıdır. Orkestratör sade görünüm görevinde işlem sayısı çubuklarını "veride yok" diye tasarımdan çıkarmıştı. Oysa `data/outcomes/<T>.csv`'de `trade_count_raw` sütunu vardı. Hata `FAZ9_UI_FIX.md`'de açıkça yazıldı ve düzeltildi (§2.6.10).

Kaynak dosyalar: proje talimatı (`claude/PROJE_TALIMATI.md`), `docs/prompts/FAZ9_APP_UI.md`, `FAZ2C_CONDITIONAL_SCORING.md`, `FAZ8_LIVE_BREAK.md`, `FAZ9_UI_FIX.md`; `docs/faz8/LIVE_RAPOR.md`; `docs/fable_faz5_audit/AUDIT.md`.

### 2.4.5 Push ve push kanıtı akışı

`CLAUDE.md` iki şeyi birlikte söyler: "git push, tag ve amend yalnız proje sahibi tarafından yapılır" ve "zaman kanıtı push'tur, yerel saat değil". Bu iki kural, projenin canlı doğruluk iddiasının belkemiğidir.

**Kanıt nasıl üretilir?** `borsai/push_proof.py` GitHub commit status API'sine bir durum yazar. GitHub bilmediği bir commit için 404 döndürür; başarılı yanıt, commit'in o anda uzak depoda bulunduğunun kanıtıdır. Zaman, yanıttaki `created_at` değeridir, yani GitHub sunucusunun saatidir. Kanıt `registry/push_proofs/<sha>.json` dosyasına yazılır. Bir commit'in geçerli zamanı, kendisinin ya da onu içeren bir torununun en erken kanıtıdır; dosya bir kez yazıldıktan sonra yeniden yazılmaz. Bugün 31 kanıt dosyası var.

**Hangi commit'ler kanıt ister?** Yalnız sıra iddiası taşıyanlar: tahmin kayıtları, D1 satırları, sonuç satırları, model dondurmaları, şartnameler (önceden kayıt). Kod, rapor, skor ve makine kaydı commit'leri düz push edilir. Git geçmişindeki 18 `BORSAI_PUSH_PROOFS` commit'i bu kanıtların kendisidir.

**Akış.** Oturum bitince orkestratör kullanıcıya bir blok verir. `docs/live/NETGL_D10_RAPOR.md` §8'deki gerçek örnek:

```
cd ~/Desktop/BorsAi
git push origin main
.venv/bin/python -m borsai.push_proof c1eb7ae
git add registry/push_proofs
git commit -m "BORSAI_PUSH_PROOFS: NETGL D4-D10 outcomes (c1eb7ae)" -- registry/push_proofs
git push origin main
git --no-pager log --oneline -3 origin/main
```

Orkestratör çıktıda `eski..yeni  main -> main` satırını görmeden işi tamam saymaz.

**Git kilidi.** Bir Claude Code oturumu commit atarken ne orkestratör ne kullanıcı git komutu çalıştırır. Orkestratör git'i yalnız okuma komutlarıyla ve her zaman `GIT_OPTIONAL_LOCKS=0` önekiyle çalıştırır; oturumlar `index.lock` hatasında bekleyip yeniden dener, kilidi silmez.

**Kanıt neden önemli?** Sınıf formülü (SPEC_SCORING §5) doğrudan kanıta bakar: model dondurma commit'i sonuç giriş commit'inin atası ve push kanıtlıysa model o arz için prospektiftir; kayıt D1'den önce push kanıtlıysa satır LIVE olur. Kanıtsız bir model commit'i için hiçbir arz prospektif değildir.

**Değişiklik.** 4 Ekim'de proje sahibi, her akşam bülteni çekip işleyecek bir botun kendi commit'ini push etmesine izin verdi (`FAZ10_FABLE_STREAK_SPEC.md`). "Yalnız sahibi push eder" kuralı botun veri commit'leri için gevşiyor; bot henüz kurulmadı (§2.7).

Kaynak dosyalar: `CLAUDE.md`, `borsai/push_proof.py`, `registry/push_proofs/`, `docs/specs/SPEC_SCORING.md` §5, `docs/live/NETGL_D10_RAPOR.md` §8, `docs/faz8/POST_BREAK_AKISI.md`, `docs/prompts/FAZ10_FABLE_STREAK_SPEC.md`, `claude/HANDOFF.md` §4.3–§4.4.

### 2.4.6 Fable'ın yeniden üretim kuralı ve bağımsız denetimler

**Kural.** Yeni bir modelin backtest sonucu, ilk uygulamayı görmemiş ayrı bir oturum (Fable) tarafından, yalnız şartnameden ve `borsai` paketini import etmeden sıfırdan yeniden üretilir. Eşik, ledger'ların her sayısal hücresinde |Δ| ≤ 1e-9'dur. Betik, sonunda `sys.modules` içinde `borsai` olmadığını denetler. Kural iki aşamada sertleşti:

- **Faz 4 ve 5:** yeniden üretim, şartnamenin "beklentiden çok iyi" eşiği aşıldığı için zorunlu oldu. Faz 4'te 10 koşul tetiklendi ve modeller yeniden üretimden önce dondurulmadı.
- **Faz 7'den itibaren:** `MODELS.md`'nin her bölümünde aynı cümle var: "Beklentiden çok iyi olsa da olmasa da sıradaki adım Fable'ın sıfırdan yeniden üretimidir."

Eski kohort ve kasada kural bir adım daha ileri gitti: **kör hesap.** Fable bağımsız hesabını, Opus'un skorlarını görmeden önce commit eder (Faz 6: `aea4082`; kasa: `38d36e8`), sonra iki sonucu karşılaştırır.

Denetimlerin hepsinde aynı ilke yazılıdır: **"Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir."**

| Klasör | Tarih | Denetlenen | Hüküm | Öne çıkan ölçüm |
|---|---|---|---|---|
| `docs/fable_conformity_20260922/` | 22 Eyl | Faz 1B'nin 9 modeli | hepsi **PUSH_OK** | 4 tavan fold'u sıfırdan; sızıntı yok; 27 sapma kabul |
| `docs/fable_faz4_audit/` | 22 Eyl | 3 tavan yolu modeli | **FREEZE_OK** | 870 hücrede maks \|Δ\| = 0 |
| `docs/fable_app_audit/AUDIT.md` | 23 Eyl | Uygulama (SPEC_APP, EK 2) | **DÜZELTMEYLE UYGUN** | 2 318 parite satırı, 0 uyuşmazlık; B1 kritik |
| `docs/fable_app_audit/KAPANIS.md` | 24 Eyl | Düzeltmeler | **UYGUN** | 10/10 bulgu kapandı, mutasyonla doğrulandı |
| `docs/fable_faz5_audit/` | 24 Eyl | `post_d1_hazard_v0` | **FREEZE_OK** | maks \|Δ\| = 1.5e-11; koşullu skorlama da uygun |
| `docs/fable_faz6_audit/` | 25 Eyl | Eski kohort altyapısı | **S2_OK** | kasa çekilişi 135/135; takvim 1 360/1 360 satır |
| `docs/fable_faz6_s6/` | 25 Eyl | Açık küme skorları (kör hesap) | **S6_OK** | sınıf ve hücre sayıları birebir |
| `docs/fable_faz7_audit/` | 26 Eyl | 4 v1 kimliği | **FREEZE_OK** | maks \|Δ\| = 4.3e-11 |
| `docs/fable_faz7c_audit/` | 27 Eyl | 4 düşüş kimliği | **FREEZE_OK** | maks \|Δ\| = 0; 16/16 mutasyon kırmızı |
| `docs/fable_faz7_vault/` | 29 Eyl | Kasa skorları (kör hesap) | **VAULT_SCORE_OK** | 34 hücrenin hepsi birebir |
| `docs/fable_faz8_audit/` | 2 Eki | `break_floor_v0` | **REPRO_OK** | maks \|Δ\| = 0; 13/13 mutasyon kırmızı |

Mutasyon testi şudur: koda bilerek küçük bir hata sokulur (ör. bir eşik değiştirilir) ve testlerin bunu yakalayıp yakalamadığına bakılır. Yakalanmayan mutasyon bir test açığıdır. Faz 6 denetiminde 16 mutasyonun 2'si yeşil kaldı, biri de yalnız tesadüfen kırmızıydı. İki "ÖNEMLİ" test kapsamı bulgusu yazıldı ve bülten indirmesinden önce kapatıldı (`40db62c`).

Kaynak dosyalar: yukarıdaki tablodaki klasörler; `docs/MODELS.md` (her fazın "Dondurma" notu); `docs/prompts/FAZ6_S2_RECORDS.md` (denetim kuralı cümlesi).

### 2.4.7 Bekçi testleri, önceden onay ve klonda prova

Projede çok sayıda **bekçi testi** vardır. Bunlar modelin doğruluğunu değil, sürecin dürüstlüğünü sınar: kasa kodu hiçbir dosyada yok mu, sonuç verisi tahminden önce girmiş mi, `registry/` altında sonuç alanı var mı, çalışma ağacı temiz mi, eski bir skor bloğu değişmiş mi. Tam test koşusu bugün 952 testtir.

Bu düzenin bir maliyeti var: canlı içeriği bir anın kopyasına kilitleyen testler, her canlı güncellemede kırılır. Oturumlar bekçi testine dokunan değişikliği yalnız proje sahibinin kendi mesajıyla kabul eder. Bu, aynı onay için tekrar tekrar durmak demekti ve proje sahibi bürokrasiden hoşlanmaz. Çözüm üç parçalı bir kalıp oldu:

1. **Önceden onaylı pin kuralı (K-PIN).** Görev dosyası, görevin bilerek kıracağı testleri ve yerine gelecek kuralı önceden yazar. Kural tek tek satır değil, genel bir ilişkidir ("dondurmadan önce | sonra tam olarak şu").
2. **Tek satırlık onay.** Kullanıcı başlatma cümlesine bir onay ekler, örneğin "Görev dosyasındaki önceden onaylı pin güncellemelerini (K-PIN-L) onaylıyorum."
3. **Klonda prova (adım 0b).** Oturum ana repoda bir şey commit'lemeden önce geçici bir `git clone --local` klonunda değişikliği dener ve kırılacak testlerin tam listesini çıkarır. Faz 8 dondurmasında 5 kırılmanın 5'i önceden görüldü.

Kalıcı çözümler sabit bir anı değil, bir ilişkiyi pinler. Örneğin M24 kuralı skor pinlerinde "sonuç ilerlemesine" izin verir: yalnız PENDING → dolu geçişi serbesttir; dondurulmuş alanlar, dolu ufuklar ve yeni arz kodları kırmızı kalır.

Test disiplini de sabittir: ara koşular paralel (`pytest -n 6 --dist loadgroup`, ≈ 10–12 dk), her görevin son kabul koşusu sıralı ve hiçbir test ayrılmadan (`pytest -q`, ≈ 18 dk); ayrıca `bash app/scripts/test.sh` (cargo, vitest, parite) ve `gen_golden --check`.

Kaynak dosyalar: `docs/prompts/FAZ8_FREEZE.md` (K-PIN), `FAZ8_LIVE_BREAK.md` (K-PIN-L), `FAZ9_UI_FIX.md` (K-PIN-FIX); `docs/live/NETGL_D10_RAPOR.md` §7; `docs/SPEC_DEVIATIONS.md` (M24, N19, N33); `docs/ENV.md`; `claude/HANDOFF.md` §4.6–§4.7.

### 2.4.8 CLAUDE.md'nin sürece etkisi

Kuralların kendisi Bölüm 6'da (§6.2) ayrıntılı anlatılıyor. Burada her kuralın iş akışında neyi değiştirdiği özetleniyor.

| Kural | Sürece etkisi |
|---|---|
| 1. Dondurma | Kayıt, kayıtlı **bütün** modellerin çıktılarını taşır ve ilk işlem gününden önce push edilmelidir. Bu yüzden her dondurmadan sonra push kanıtı alınır. Kural fazlarla genişledi: POST_D1 kaydı için D2 09:40 sınırı (Faz 5), POST_BREAK için makine sıralı kayıt cümlesi (Faz 8, `5d84e88`). |
| 2. Payda | Başlangıçtan sonra işlem gören her arz `registry/ipos.csv`'ye girer; dondurulmayan arz nedeniyle "atlandı" satırı olur. Bülten tamlık denetimi açıklanamayan her yeni kodda durur. |
| 3. Üç terazi | Her terazi ve ölçek kendi skor dosyasında: `scores.json` (backtest + canlı), `scores_post_d1.json`, `scores_oot.json`, `scores_break.json`. Kuralın metni Faz 6'da "iki terazi"den "üç terazi"ye değişti (KARARLAR D3). |
| 4. Deney günlüğü | Her backtest koşusu `experiments/log.jsonl`'a kendiliğinden bir satır ekler. Bugün 2 146 satır: 72 backtest, 19 duyarlılık, 1 koşullu değerlendirme ve Faz 7C keşfinin 2 054 varyantı. Uygulama kartları "kaç varyant denendi" sayacını buradan okur. |
| 5. Değişiklik = yeni model_id | Model düzeltilmez, yanına yeni kimlik yazılır (v0 → v1). Denetim kuralı bunun iki yönünü ayırır: kodu şartnameye uydurmak aynı kimlik, şartnameyi değiştirmek yeni kimlik. |
| 6. Skorlama | "A: tanımlar kodda, sonuç yok → B: sonuçlar" commit kalıbı; eşleşik basit kurallar; "geçiyor" yalnız aralık 0'ı dışlarsa; n < 10'da yalnız satır tablosu, 10 ≤ n < 30'da "yetersiz örnek". |
| Sıra kuralı | Faz 1 modelleri, yeni arzların sonuçlarından önce donduruldu. Eski kohortta bütün tahmin kayıtları hiçbir bültenden önce push edildi. Kasa, doğrulanacak özellikler önceden kaydedilip push edilmeden açılmadı. |
| Yalnız proje sahibi push eder | Push bloğu ve push çıktısının doğrulanması (§2.4.5). |
| `legacy/` değiştirilmez | Eski kod referans olarak kalır; port testleri ona karşı koşar. |

Şartnamenin belirsiz kaldığı her yerde uygulayıcı "en makul yorumu" seçer ve bunu `docs/SPEC_DEVIATIONS.md`'ye yazar. Dosya bugün 278 KB'tır ve fazlara göre 15 bölüme (A–O) ayrılır; her madde şartname bölümünü, belirsizliği, seçilen yorumu ve gerekçeyi taşır.

Kaynak dosyalar: `CLAUDE.md`, `docs/specs_faz6/KARARLAR.md` D3, `docs/specs_faz8/KARARLAR.md` §C, `experiments/log.jsonl`, `docs/SPEC_DEVIATIONS.md`, `scores/`.

## 2.5 Görev dosyaları kataloğu (79 dosya)

`docs/prompts/` altında 79 görev dosyası var. Model satırlarına göre dağılım:

| Rol ve model | Dosya | Tipik iş |
|---|---|---|
| Claude Code / Opus (5 → 5.5) | 41 | kod, backtest, dondurma, uygulama, veri doğrulama |
| Claude Code / Fable | 23 | şartname, karar listesi, bağımsız yeniden üretim, denetim |
| Codex + GPT-6 Astra | 8 | repo dışında resmi belgelerden veri toplama |
| Claude Code / Sonnet 5 | 5 | mekanik işler |
| Ek (ana görevin durak kararı) | 2 | `FAZ2B_EK1_OYAKC.md`, `FAZ6_S3_S5_EXTRACT_EK1.md` |

Aşağıdaki tablolar her dosyanın amacını tek satırda verir. "Model" sütunu dosyadaki model satırıdır.

**Faz 1–2**

| Dosya | Model | Amaç |
|---|---|---|
| `FAZ1A_V1_5_PORT.md` | Opus 5 · yüksek | `borsai/` çekirdeği, V1.5 portu, toleranslı kabul testi, basit kurallar |
| `FAZ1_FABLE_MODEL_SPECS.md` | Fable · yüksek | Beş şartname: tavan, PB, market20, V1.6, skorlama |
| `FAZ1B_NEW_MODELS.md` | Opus 5 · yüksek/Extra | Şartnameleri kodlamak, backtest, dondurmak |
| `FAZ1B_FABLE_CONFORMITY.md` | Fable · yüksek | Push öncesi uygunluk ve sızıntı denetimi |
| `FAZ2A_REGISTRY_INPUTS.md` | Opus 5 · yüksek/Extra | Push kanıtı aracı, payda, 7 arzın girdileri ve kayıtları |
| `FAZ2B_OUTCOMES_SCORING.md` | Opus 5 · Extra | Sonuç tanımları (A), resmi sonuçlar ve ilk canlı skor (B) |
| `FAZ2B_EK1_OYAKC.md` | ek | Temerrüt pazarı kodu için genel tamlık kuralı |
| `FAZ2C_CONDITIONAL_SCORING.md` | Opus · Extra | Koşullu ("seri j gün sürdüyse") canlı skorlama |

**Faz 3: uygulama**

| Dosya | Model | Amaç |
|---|---|---|
| `FAZ3_FABLE_APP_SPEC.md` | Fable · yüksek | Uygulama şartnamesi (SPEC_APP) |
| `FAZ3_FABLE_APP_SPEC_EK1.md` | Fable (ek) | Koşullu tavan güncellemesi özelliği |
| `FAZ3_APP_STAGE01.md` | Opus 5 · Extra | Aşama 0–1: iskelet, Rust portu, parite |
| `FAZ3_APP_STAGE2.md` | Opus 5 · Extra | Girdi formu, sonuç ekranı, senaryo modu |
| `FAZ3_FABLE_APP_SPEC_EK2.md` | Fable · yüksek | Faz 4 modellerinin uygulamaya eklenmesi (EK 2) |
| `FAZ3_APP_STAGE3.md` | Opus 5 · Extra | Resmi dondur sihirbazı, sicil ekranı |
| `FAZ3_APP_P1.md` | Opus 5 · Extra | Tavan yolu modellerinin Rust portu |
| `FAZ3_APP_P2.md` | Opus 5 · Extra | Tavan yolu gösterimi |
| `FAZ3_APP_STAGE4.md` | Opus 5 · Extra | Doğruluk paneli |
| `FAZ3_APP_STAGE5.md` | Opus 5 · Extra | Dışa aktarma, mod bandı, cila |
| `FAZ3_FABLE_APP_AUDIT.md` | Fable · yüksek | Uygulama uygunluk denetimi |
| `FAZ3_APP_AUDIT_FIX.md` | Opus 5 · Extra | B1–B8, B10, B12 düzeltmeleri, önce test |
| `FAZ3_FABLE_APP_AUDIT_CLOSE.md` | Fable · yüksek | Düzeltmelerin kapanış denetimi |

**Faz 4–5**

| Dosya | Model | Amaç |
|---|---|---|
| `FAZ4_FABLE_CEILING_PATH_SPEC.md` | Fable · yüksek | Tavan yolu şartnamesi |
| `FAZ4_CEILING_PATH_IMPL.md` | Opus 5 · Extra | Tavan yolu kodu ve backtest |
| `FAZ4_FABLE_REPRO_AUDIT.md` | Fable · yüksek | Sıfırdan yeniden üretim |
| `FAZ4_FREEZE.md` | Opus 5 · yüksek | Dondurma |
| `FAZ4_SCORES_CELLS.md` | Opus 5 · yüksek | Tavan yolu hücrelerini `scores.json`'a eklemek |
| `FAZ5_FABLE_POST_D1_SPEC.md` | Fable · yüksek | D1 sonrası model şartnamesi |
| `FAZ5_POST_D1_IMPL.md` | Opus 5.5 · Extra | Kod ve backtest |
| `FAZ5_FABLE_REPRO_AUDIT.md` | Fable · yüksek | Yeniden üretim ve Faz 2C denetimi |
| `FAZ5_FREEZE.md` | Opus 5.5 · yüksek | Dondurma (ayrı dizin) |
| `FAZ5_POST_D1_LIVE.md` | Opus 5.5 · Extra | Canlı POST_D1 aşaması (09:40 sınırı) |
| `FAZ5_LIVE_B_APPFIX.md` | Sonnet 5 · yüksek | Uygulama MANIFEST pininin yeniden bağlanması |

**Faz 6: eski kohort**

| Dosya | Model | Amaç |
|---|---|---|
| `FAZ6_FABLE_OLD_COHORT_SPEC.md` | Fable · yüksek | Fizibilite ve zaman-dışı test şartnamesi |
| `FAZ6_CODEX_INPUTS_B1…B4.md` | Codex + GPT-6 Astra | 135 arzın girdileri (34 + 26 + 38 + 37), sonuç körlüğü kuralıyla |
| `FAZ6_VERIFY_CODEX_INPUTS.md` | Opus 5.5 · yüksek | Codex değerlerinin resmi belgede doğrulanması (repo dışına) |
| `FAZ6_OOT_INFRA.md` | Opus 5.5 · Extra | Kohort altyapısı, kasa çekilişi, bekçiler |
| `FAZ6_FABLE_OOT_AUDIT.md` | Fable · yüksek | Altyapı denetimi, kuru S2 koşusu |
| `FAZ6_S2_RECORDS.md` | Opus 5.5 · yüksek | Denetim bulgularını kapatmak, 135 × 19 kayıt |
| `FAZ6_S3_S5_EXTRACT.md` | Opus 5.5 · Extra | Karantinaya indirme, D1 ve D1–D10 satırlarını ayıklama |
| `FAZ6_S3_S5_EXTRACT_EK1.md` | ek | Takvim C kapanışları için bülten kanıtı |
| `FAZ6_FABLE_S6_RECOMPUTE.md` | Fable · yüksek | Kör bağımsız hesap ve karşılaştırma |
| `FAZ6_S6_SCORING.md` | Opus 5.5 · yüksek | Zaman-dışı skorlar |
| `FAZ6_S6_FIX.md` | Opus 5.5 · yüksek (yeni oturum) | D1 sonrası bloğunu canlı tanıma uydurmak (B1–B3) |

**Faz 7 ve 7C**

| Dosya | Model | Amaç |
|---|---|---|
| `FAZ7_FABLE_HAZARD_V1_SPEC.md` | Fable · yüksek | Tavan serisi v1 şartnamesi |
| `FAZ7_HAZARD_V1_IMPL.md` | Opus 5.5 · Extra | v1 kodu, TÜFE, eğitim tablosu v2, backtest |
| `FAZ7_CODEX_PROSPECTUS_B1…B4.md` | Codex + GPT-6 Astra | 135 arz için izahnameden 7 alan |
| `FAZ7_VERIFY_PROSPECTUS.md` | Opus 5.5 · yüksek | İzahname alanlarının doğrulanması |
| `FAZ7_PROSPECTUS_INTAKE.md` | Sonnet 5 · yüksek | Doğrulanmış alanları repoya almak |
| `FAZ7_FABLE_V1_REPRO_AUDIT.md` | Fable · yüksek | v1 yeniden üretimi |
| `FAZ7_FREEZE.md` | Opus 5.5 · Extra | v1 dondurma, aylık TÜFE ekleme yolu |
| `FAZ7_FABLE_C_SPEC.md` | Fable · yüksek | Düşen arz keşfi ve şartnamesi |
| `FAZ7_C_IMPL.md` | Opus 5.5 · Extra | Düşüş modeli kodu ve backtest |
| `FAZ7_FABLE_APP_EK3_SPEC.md` | Fable · yüksek | Uygulama EK 3 şartnamesi |
| `FAZ7C_FABLE_REPRO_AUDIT.md` | Fable · yüksek | Düşüş modeli yeniden üretimi |
| `FAZ7C_FREEZE.md` | Opus 5.5 · Extra | Düşüş modeli dondurma |
| `FAZ7_OOT_RECORDS.md` | Opus 5.5 · Extra | 8 yeni modelin eski kohort kayıtları, model başına kapı |
| `FAZ7_VAULT_OPEN.md` | Opus 5.5 · Extra | Kasanın tek seferlik açılışı |
| `FAZ7_FABLE_VAULT_RECOMPUTE.md` | Fable · yüksek | Kasa için kör bağımsız hesap |
| `FAZ7_VAULT_SCORE.md` | Opus 5.5 · Extra | Kasa skorları ve seçim kuralları |

**Ara işler, Faz 8–10**

| Dosya | Model | Amaç |
|---|---|---|
| `INFRA_TEST_SPEED.md` | Sonnet 5 · yüksek | Paralel pytest, hiçbir kontrol zayıflatılmadan |
| `FAZ7_APP_P1.md` | Opus 5.5 · Extra | v1 portu, TÜFE tablosu, "kaç gün tavan" kartı |
| `LIVE_NETGL_D10.md` | Sonnet 5 · yüksek | NETGL D4–D10 resmi sonuçları |
| `FAZ7_APP_P2.md` | Opus 5.5 · Extra | D1 sonrası portu ve sihirbazı |
| `FAZ7_APP_P3P4.md` | Opus 5.5 · Extra | Düşüş portu, kart ve zaman-dışı panel |
| `FAZ8_FABLE_BREAK_SPEC.md` | Fable · yüksek | Kırılma akşamı şartnamesi ("değer mi" ile) |
| `FAZ8_BREAK_IMPL.md` | Opus 5.5 · Extra | Kod ve backtest |
| `FAZ8_FABLE_REPRO_AUDIT.md` | Fable · yüksek | Yeniden üretim, eşik sağlamlığı |
| `FAZ8_FREEZE.md` | Opus 5.5 · Extra | Üçüncü dizine dondurma |
| `FAZ8_LIVE_BREAK.md` | Opus 5.5 · Extra | Makine sıralı canlı aşama |
| `FAZ9_APP_UI.md` | Opus 5.5 · Extra | Sade görünüm |
| `FAZ9_UI_FIX.md` | Opus 5.5 · Extra | Sunum öncesi altı düzeltme |
| `TUFE_2026_09.md` | Sonnet 5 · yüksek | Eylül 2026 TÜFE satırı (bekliyor) |
| `FAZ10_FABLE_STREAK_SPEC.md` | Fable · yüksek | Seri içi gün gün tavan modeli şartnamesi (bekliyor) |

Kaynak dosyalar: `docs/prompts/*.md`.

## 2.6 Önemli dersler ve olaylar

### 2.6.1 Beklentiden iyi sonuç önce şüphe doğurur

Projede dört kez bir model, şartnamenin önceden yazdığı beklentiden belirgin biçimde iyi çıktı. Her seferinde ilk tepki sevinmek değil, sızıntı aramak oldu.

| Faz | Model | Beklenti | Gerçekleşen | Ne yapıldı | Sonuç |
|---|---|---|---|---|---|
| 1B | `ceiling_hazard_v0` | RPS farkı −0.005 … −0.02 | −0.0496 [−0.0751, −0.0219] | Push'tan önce Fable uygunluk denetimi; 4 fold sıfırdan | Sızıntı yok. Beklenti "yanlış çapalanmış"tı: f3'ün seri uzunluğuyla ilişkisi güçlü, kazanç dört yılda da aynı |
| 4 | `ceiling_path_v0` | D5 MAE farkı −0.090 … −0.020 | −0.1158 [−0.1611, −0.0738] | 10 koşul tetiklendi, dondurma durduruldu | 870 hücrede maks \|Δ\| = 0; FREEZE_OK |
| 5 | `post_d1_hazard_v0` | Brier k = 2 farkı > −0.040 | −0.0512 | Yeniden üretim şartı | maks \|Δ\| = 1.5e-11; FREEZE_OK |
| 8 | `break_floor_v0` | birincil −0.080 [−0.140, −0.020] | −0.1904 [−0.2520, −0.1247] | Yeniden üretim; eşik yuvarlamasının sağlamlık testi | REPRO_OK; farkın bir kısmı karşılaştırıcının zayıflığından |

Ders iki yönlüdür. Dört vakanın hiçbirinde sızıntı çıkmadı; yani "çok iyi" sonuçlar gerçek backtest sonuçlarıydı. Ama hepsi H99 üzerinde ve "tasarıma maruz"dur: özellikler ve gruplar aynı veri görülerek seçildi. Bu yüzden backtest yalnız ön elemedir; asıl sınav canlı sicildir.

Kaynak dosyalar: `docs/fable_conformity_20260922/AUDIT.md` §1.6, `docs/fable_faz4_audit/AUDIT.md`, `docs/fable_faz5_audit/AUDIT.md`, `docs/fable_faz8_audit/AUDIT.md`, `docs/MODELS.md`.

### 2.6.2 Geç kayıtlar: canlı kanıtın tek yolu zamanında dondurmaktır

Yeni repo kurulduğunda yedi arz zaten işlem görmeye başlamıştı (18 Ağustos – 17 Eylül). Faz 1 modelleri 22 Eylül'de dondu ve bu arzların kayıtları aynı gün yazıldı. Sonuç: **7 arzın hepsi Faz 1 modelleri için LATE_RECORD** (tek istisna: NETGL × `v1_5_h99` hücresi, eski depoda zamanında dondurulan kayıt sayesinde LIVE). Model parametreleri sonucu göremez (model, sonuç verisinden önce dondu), ama kayıt ilk işlem gününden sonra yazıldı. Bu sınıfın tek açık kanalı, girdileri toplayan kişinin sonucu biliyor olmasıdır; bu yüzden her girdinin kaynak belgesi ve yayın zamanı kayıtlıdır ve satır etiketi görünür kalır. Faz 4'ten sonraki bütün modeller bu yedi arz için RETRO'dur.

Bugün yeni repoda yazılmış kayıtlarda **gerçek LIVE tahmin sayısı 0**. Sicildeki tek LIVE satır, eski depodan gelen NETGL V1.5 kaydıdır. Strateji belgesindeki hesap: "canlıda kanıtlandı" diyebilmek için yaklaşık 30 canlı arz gerekir; her kaçırılan arz kayıp bir sınavdır. Yeni arz protokolünün ilk maddesi bu yüzden "ilk işlem gününden önce dondur, push et, kanıtla"dır.

Kaynak dosyalar: `docs/SCORES.md` §2–§3, `docs/specs/SPEC_SCORING.md` §5, `scores/scores.json`, `claude/STRATEJI.md` §4–§5, `claude/HANDOFF.md` §7.2.

### 2.6.3 NETGL vakası

NETGL (arz fiyatı 25,52 TL) 17 Eylül'de işlem görmeye başladı. Resmi bültenlere göre yolu şöyleydi:

| Gün | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Kapanış (TL) | 28,06 | 30,86 | 33,94 | 30,56 | 27,52 | 24,78 | 22,32 | 20,10 | 18,09 | 16,29 |
| Durum | tavan | tavan | tavan | taban | taban | taban | taban | taban | taban | taban |
| Arz fiyatına göre | +%9,95 | +%20,92 | +%32,99 | +%19,75 | +%7,84 | −%2,90 | −%12,54 | −%21,24 | −%29,11 | −%36,17 |

Modeller ne demişti?

- **V1.5** (eski depo, git + push, LIVE): D5 için +%25,5, D10 için +%25,8 getiri; D10'da arz fiyatının üstünde kalma olasılığı 0,60. Gerçekleşen D10 −%36,17. Basit kurallar da yanlış işaretliydi. Tek arz olduğu için hüküm yok.
- **`ceiling_hazard_v0`** (LATE_RECORD): medyan seri 3 gün, P(L ≥ 3) = 0,61, P(L ≥ 5) = 0,27. Gerçekleşen L = 3. Bu da tek arzlık bir betimlemedir.

Vakanın üç sonucu oldu:

1. **Yeni bir soru doğdu.** Hiçbir model serinin nasıl bozulduğunu kullanmıyordu. Faz 8'in kırılma akşamı modeli doğrudan bu vakadan çıktı.
2. **Rejim sorusu doğdu.** NETGL'in D1'i, Eylül 2026 fon krizinin başladığı günlere denk geliyordu (§2.6.4). Faz 8 görev dosyası NETGL'deki taban serisinin "temiz bir kırılma mekaniği örneği sayılmaması" gerektiğini yazdı.
3. **Bekçiler sınandı.** Sonuçlar girilirken üç bekçi test kırmızıya döndü ve oturum her seferinde durdu. Yeni temerrüt pazarı kodlarının üçü kasa üyelerinin kodlarıyla eşleşiyordu (halka arz değildi); bekçi iki kipli yapıldı (M23). İki skor pini sonuç ilerlemesi yüzünden kırıldı; yerine "yalnız PENDING → dolu serbest" ilişki kuralı kondu (M24). Raporda oturum kendi hatasını da yazdı: pinlerden birini başta "çalışma ağacı temizliği testi" sanmış, onayı yalnız diğeri için istemiş, sonra ikinci onayı ayrıca istemek zorunda kalmıştı.

Kaynak dosyalar: `docs/live/NETGL_D10_RAPOR.md`, `registry/legacy_frozen/true_live_v1_5_registry.csv`, `docs/prompts/FAZ8_FABLE_BREAK_SPEC.md`, `docs/SPEC_DEVIATIONS.md` M23–M24.

### 2.6.4 Eylül 2026 fon krizi rejimi

1 Ekim tarihli piyasa araştırması, eğitim verisinde karşılığı olmayan bir dönemi kayda geçirdi:

- 16 Eylül'de bir portföy yönetim şirketinin iki fonu geri ödeme temerrüdüne düştü. 17 Eylül'de SPK yedi şirketin 130 fonunu tasfiyeye aldı.
- BIST100 Eylül'de %16,65 düştü; zirveden kayıp %21,4.
- Eğitim kümesinde ilk on seansını böyle bir stresle geçiren arz yok ya da çok az.

Proje bunu bir **model girdisi** yapmadı. `FON_KRIZI_2026` bir uyarı etiketidir: D1 ≥ 2026-09-16 olan arzlarda kartta "olağan dışı piyasa" uyarısı çıkar. Bitiş tarihi açıktır; proje sahibi tarih verene kadar sürer (Faz 8 kararı C4). Etiket n'den düşülmez; yalnız kırılımı görünür. En önemlisi, rejimin canlı sonuçlara etkisi **önceden yazıldı**:

- Araştırma: "D10 düşüş modelleri arz altına inmeyi olduğundan düşük tahmin edecek; 'kaç gün tavan' modeli de seriyi olduğundan uzun görecek."
- Faz 8 şartnamesi: "model tabanı az tahmin eder."

Böylece canlı sicildeki hatalar, rejim değişimine hangi modelin dayandığını gösteren temiz bir kanıt olarak okunabilecek.

Kaynak dosyalar: `docs/arastirma/TR_HALKA_ARZ_PIYASASI_20261001.md` ("Eylül 2026 sonu"), `docs/specs_faz8/KARARLAR.md` B13 ve C4, `docs/MODELS.md` Faz 8 "Dondurma" (kart uyarısı 5).

### 2.6.5 Sonuç körlüğü ve kasa hijyeni

Eski kohort testinin değeri, tahminlerin sonuç görülmeden yapılmasına dayanır. Bunu korumak için alınan önlemler:

- **Karantina.** Bültenler repoya girmez; repo dışındaki `~/Desktop/BorsAi_quarantine` klasörüne iner. Repoya yalnız açık üyelerin ayıklanmış satırları ve zip pinleri girer.
- **Kod kapıları.** Ayıklama kodu bir kasa kodunun satırını okumaya kalkarsa hata verir. İndirme, bütün tahmin kayıtları commit'li ve push kanıtlı olmadan başlamaz.
- **Codex'e körlük kuralı.** Toplama görevleri haber sitelerini, forumları ve "kaç tavan yaptı" türü sayfaları açmayı yasaklar. İstemeden görülen listeleme sonrası bilgi `exposure_log`'a yazılır, değeri yazılmaz. Faz 6'da 5, Faz 7'de 8 satır yazıldı (KAP liste başlıkları; değer yok).
- **Okuma yasakları.** Özellik tasarlayan oturumlar maruziyet listelerini okumaz.
- **Hijyen taraması.** Repoya giren her metin, 64 kasa koduna karşı büyük/küçük harf duyarlı taranır; bülten dosya adı kalıbı da yazılmaz.

Kayda geçen olaylar:

- Fable'ın Faz 7C oturumu kohort dosyasının ilk üç satırını basarken 2 kasa kodu, orkestratör de bir denetim çıktısında 10 kasa kodu gördü. Hiçbir koda bağlı özellik ya da sonuç görülmedi; olay `KARARLAR_C.md`'ye yazıldı.
- Faz 7 OOT görevinde ilk yazım, ek kayıtlara ilk kayıttan `vault` alanını kopyaladı. 135 dosya commit'lenmeden silindi, kod düzeltildi, kayıtlar yeniden yazıldı.
- Kasa açılışında bir durak iletisi kural gereği bir kasa kodunu içeriyordu; kod hiçbir dosyaya yazılmadı.

Kaynak dosyalar: `docs/specs_faz6/KARARLAR.md` D2, D6, D7, Maruziyet kaydı; `docs/specs_faz7/KARARLAR.md` "Ek notlar"; `docs/specs_faz7_c/KARARLAR_C.md` "Hijyen olayları"; `docs/faz7_oot/RAPOR.md` §0; `docs/faz7_vault/RAPOR.md`; `docs/prompts/FAZ6_CODEX_INPUTS_B1.md`.

### 2.6.6 "DUR" kuralı işe yaradı

Görev dosyalarının çoğunda "beklenmeyen bir şey olursa DUR" maddesi var. Oturum durduğunda orkestratör ve proje sahibi karar verir; karar bir ek görev dosyasına ya da `SPEC_DEVIATIONS.md`'ye yazılır. Önemli duraklar:

| Durak | Ne oldu | Karar |
|---|---|---|
| Faz 2B tamlık | Bültende açıklanamayan yeni kod | Temerrüt pazarı; genel kural (`FAZ2B_EK1_OYAKC.md`) |
| Faz 6 takvim probu | Takvimde "kapalı" sayılan 5 günün (Şubat 2023 depreminin dört günü ve bir gün daha) bültenleri yayımlanmıştı | Takvim, bülten kanıtından kuruldu (`FAZ6_S3_S5_EXTRACT_EK1.md`): Şubat'taki dört gün "yayımlanmış ama işlem yok" sayıldı, kalan gün olağan seans çıktı |
| Faz 6 S6 | Eski kohortun D1 sonrası bloğu canlı tanımdan sapıyordu (B1–B3) | S6'yı koşan oturum değil, yeni bir oturum düzeltti (`1c2fb02`) |
| Kasa açılışı | Bir bültenin tarih alanı ISO biçiminde değildi | Proje sahibi kararıyla dar bir biçim kuralı (M14); başka biçimde yine DUR |
| NETGL D10 | Üç bekçi kırmızı | Yazılı onaylarla ilişki kuralları (M23, M24) |
| Faz 8 canlı | Taban koşusunda bir test, push kanıtı dosyası yüzünden kırmızıydı; ayrıca `registry/` altında sonuç alanını yasaklayan bekçi makine kaydının şemasıyla çelişiyordu | Test sabit bir commit aralığına bağlandı (N33); kayıt dizini kendi bekçisiyle hariç tutuldu |

Ders: durak bir aksaklık değil, sistemin çalıştığının işaretidir. Hiçbir durakta test gevşetilmedi; her seferinde kural genelleştirildi ve yazıldı.

Kaynak dosyalar: `docs/faz6/S3_S5_RAPOR.md` §3–§4, `docs/faz6/S6_RAPOR.md`, `docs/faz6/S6_FIX_RAPOR.md`, `docs/faz7_vault/RAPOR.md` §4, `docs/live/NETGL_D10_RAPOR.md` §7, `docs/faz8/LIVE_RAPOR.md`, `claude/HANDOFF.md` §4.6.

### 2.6.7 Uygulama tarafının dersleri

- **Değişmezler testle korunur.** Fable'ın uygulama denetimindeki kritik bulgu (sembolik bağ yoluyla `registry/` altına yazma) "pratik etkisi düşük" bir açıktı, ama bir değişmezi testsiz kırılabilir bırakıyordu. Düzeltme kuralı: önce açığı yakalayan test, onun kırmızı olduğunun kanıtı, sonra düzeltme.
- **Pinler davranış değişmese de kırılır.** Faz 5'te `predict_hazard.py` davranış değiştirmeden yeniden düzenlendi; uygulamanın altın MANIFEST'i eski sha'yı pinlediği için test betiği kırmızıya döndü. Model dizini her büyüdüğünde (19 → 23 → 27) uygulamaya ayrı bir "APPPIN" commit'i gerekti; uygulama yeni kayıtları bir sonraki port görevine kadar "tanınmayan" diye yok saydı (J31 kalıbı).
- **Ön uç hesap yapmaz.** Bütün sayılar Rust'tan gelir; bu, statik taramayla zorlanır. Sade görünümde de aynı kural sürdü: kırılma kartı yalnız makine kaydından ve skor dosyasından okunur.
- **Ana ekran veri-güdümlüdür.** Elle bir "gösterilecek modeller" listesi yoktur; kapı, skor dosyasındaki önceden ilan edilmiş hücrenin hükmüne bakar.

Kaynak dosyalar: `docs/fable_app_audit/AUDIT.md`, `KAPANIS.md`; `docs/prompts/FAZ3_APP_AUDIT_FIX.md`, `FAZ5_LIVE_B_APPFIX.md`; `GITLOG.txt` (APPPIN commit'leri); `app/README.md`; `docs/prompts/FAZ9_APP_UI.md` K-UI-3, K-UI-4.

### 2.6.8 "Eski arzları eğitime katmak bugünü bozar mı?"

Bu soru üç fazı boyunca izlendi ve cevabı proje sahibinin iki kararına dönüştü.

- **Faz 7:** Eski arzlarla eğitilen `v1_pooled` ve reel büyüklüklü `v1_real`, yakın dönemde `ceiling_hazard_v0`'dan kötü çıktı (önceden yazılı etiket: "bozuyor"). Buna karşılık kasada `v1_pooled`, KM kuralını geçen tek tavan adayıydı.
- **Faz 7C:** Düşüş modelinde `pooled − h99` farkı "belirsiz" çıktı.
- **Kasa:** Seçim kuralları (yakın dönem etiketi + kasa + V1.5'e karşı) hiçbir v1 ya da düşüş adayını öne çıkarmadı.

Kararlar:

1. **"Bize bugün lazım"** (29 Eylül): eğitim yalnız güncel dönemle yapılır.
2. **"Hiçbir modelimizin geçmişte başarılı olması gerekmez"** (1 Ekim): eski dönem testi kapı değil, bilgidir. Yeni modellerin kapısı yakın dönem backtest'i (ön eleme) ve canlı sicildir.

Faz 8'in kırılma modeli bu kararlarla yazılan ilk modeldir: eski kohort testi hiç yapılmadı.

Kaynak dosyalar: `docs/MODELS.md` Faz 7, Faz 7C; `docs/faz7_vault/SKOR_RAPOR.md` §9; `docs/specs_faz8/KARARLAR.md` §A; `docs/prompts/FAZ8_FABLE_BREAK_SPEC.md`.

### 2.6.9 Piyasa araştırmasının yeri

`docs/arastirma/TR_HALKA_ARZ_PIYASASI_20261001.md` 1 Ekim'de repoya girdi (Faz 8 şartnamesiyle aynı commit). Faz 8 görev dosyası onu "dış araştırma (orkestratör, 1 Ekim)" diye anar; metni kimin yazdığı dosyada belirtilmemiştir (belirsiz). Belgenin kuralı açıktır: her iddia [R] resmi/hakemli, [B] basın, [Ç] çıkarım ya da [P] proje ölçümü diye etiketlenir ve buradaki hiçbir sayı repo verisinde yeniden ölçülmeden modele girmez. Modele yarayan ana bulguları şunlardır:

- **Dört dalga:** 2023 çılgınlık, 2024 soğuma, 2025 duruş, 2026 rekor. Tavan serileri kısaldı ve 2026'da iki tepeli hâle geldi.
- **Yastık aritmetiği:** ±%10 bantta D1'den N günlük tavan, fiyatı arz fiyatının 1,1^N katına taşır. D10'da arz altına inmek için N ≤ 5 olmalıdır; N = 6 ve üstünde bu mekanik olarak imkânsızdır. Genel kural: arz fiyatına limit adımı cinsinden mesafe kalan seans sayısından büyük ya da eşitse olasılık yapısal olarak sıfırdır. Faz 8 bunu `D10_STRUCTURAL_ZERO` kuralı olarak kodladı.
- **Kilitlenme dokunmadan farklıdır:** kapanışta limitte kalmak, limite gün içinde değmekten güçlü bir işarettir.
- **VBTS** (volatilite bazlı tedbir sistemi) 1. kademesi tavan serisindeki arzlara yaklaşık 6.–9. seansta geliyor (üç vaka; zayıf kanıt).
- **Tek dağıtım kuralı kırılması** eğitim penceresinde 19.09.2024'tür.
- Borsa İstanbul'un 21.09.2026 tarihli prosedür revizyonu (rev. 54) araştırma anında kontrol edilememişti. Faz 8 dondurmasından önce doğrulandı: bant, yuvarlama ve ilk gün baz fiyat kuralı değişmemiş.

Kaynak dosyalar: `docs/arastirma/TR_HALKA_ARZ_PIYASASI_20261001.md`, `docs/prompts/FAZ8_FABLE_BREAK_SPEC.md`, `docs/faz8/BANT_DOGRULAMA.md`, `docs/specs_faz8/KARARLAR.md` B1, C5.

### 2.6.10 Orkestratörün kendi hataları

Proje talimatı "hata yaptığında açıkça söyle" der. Dosyalarda kayıtlı orkestratör hataları:

- **2A görev dosyası:** "ikinci kayıt ancak iptalden sonra" cümlesi skorlama şartnamesiyle çelişiyordu; 2B görevinde düzeltildi.
- **Faz 8 dondurma görevi:** önceden onaylı pin kuralı, dondurmadan sonra gelecek push kanıtı dosyasını hesaba katmadı; canlı görevin tabanında bir test kırmızıydı. Proje sahibinin kararıyla test sabit bir commit aralığına bağlandı (N33).
- **Faz 8 canlı görevi:** `registry/` altında sonuç alanını yasaklayan bekçi önceden ölçülmedi; oturum durdu.
- **Sade görünüm görevi:** işlem sayısı çubukları "veride yok" diye çıkarılmıştı; `trade_count_raw` sütunu vardı. `FAZ9_UI_FIX.md` "Bu yanlıştı" diye yazdı ve çubuklar eklendi.
- **Özet kaymaları.** 2 Ekim tarihli HANDOFF, V1.5'in D10 "arz üstü" olasılığını taban orana karşı "geçiyor" diye özetliyor. `scores/scores.json`'daki hüküm ise "ayırt edilemiyor"dur: −0.0391 [−0.0756, +0.0023]. Uygulama da bu hücreyi "fark net değil" diye gösterir. Ölçmeden aktarma kuralının neden var olduğuna küçük bir örnek.

Kaynak dosyalar: `docs/prompts/FAZ2B_OUTCOMES_SCORING.md` (Bağlam), `docs/prompts/FAZ9_UI_FIX.md` madde 4–5, `docs/SPEC_DEVIATIONS.md` N33, `scores/scores.json`, `claude/HANDOFF.md` §8.4, §9.

### 2.6.11 Gün grupları ve "3. günden sonra değişmeyen" olasılık

Proje sahibi sade görünümü kullanırken bir şey fark etti: "Seri j gün sürdüyse yarın ne olur?" hesaplayıcısında "yarın da tavan" olasılığı 3. günden sonra hiç değişmiyordu (NETGL'de j = 3…9 için hep %67, CITAS'ta hep %85). Bu bir hata değildi, modelin yapısıydı. `ceiling_hazard_v0` günleri üç gruba ayırır (1. gün; 2.–3. gün; 4.–10. gün) ve bir grubun içindeki her güne aynı devam olasılığını verir.

Çözüm iki adımda geldi:

1. **FAZ9_UI_FIX (hemen):** model değişmedi; ekranda açıklandı. Grup notu model dosyasındaki `day_groups`'tan okunur; yanına geçmiş arzların gün gün oranı (basit KM kuralı) konur. NETGL'de j = 3 ve j = 6'da model %67, geçmiş %80 ve %82.
2. **FAZ10 (sıradaki):** proje sahibi "hiç profesyonel durmuyor, modeli düzeltelim" dedi (4 Ekim) ve "seri sürerken her akşam güncellenen model" yolunu seçti (§2.7.7).

Kaynak dosyalar: `docs/prompts/FAZ9_UI_FIX.md` madde 3, `docs/app/UI_FIX_RAPOR.md` §0, `docs/prompts/FAZ10_FABLE_STREAK_SPEC.md`, `models/ceiling_hazard_v0.json`.

## 2.7 Bugünkü durum (6 Ekim 2026, HEAD `ee3796d`)

### 2.7.1 Depo

- HEAD `ee3796d` ("BORSAI_FAZ9_UI_FIX_R: final test runs", 6 Ekim 14:22). Git geçmişinde 175 commit.
- 31 push kanıtı dosyası; deney günlüğünde 2 146 satır.
- Testler (son kabul, `docs/app/ui_fix_test_runs.txt`): sıralı `pytest` 952 geçti (18 dk 40 sn); `test.sh` yeşil (cargo 164, vitest 24 dosya / 376 test, parite 8, `golden_unchanged` yeşil); `gen_golden --check` 35 dosya, 0 fark.

Kaynak dosyalar: `GITLOG.txt`, `registry/push_proofs/`, `experiments/log.jsonl`, `docs/app/ui_fix_test_runs.txt`.

### 2.7.2 Donmuş modeller: 27 + 1 + 2 = 30

| Dizin | Sayı | Modeller |
|---|---|---|
| `models/INDEX.json` (listeleme öncesi) | 27 | V1.5 ve 6 basit kural; `v1_6_h99`, `v1_5_market20_v0`, `pb_v0`; `ceiling_hazard_v0` ve `@INF`; `pb_ceiling_v0` ve `@INF`; iki KM kuralı; üç tavan yolu modeli; dört v1 kimliği; dört düşüş kimliği |
| `models/INDEX_POST_D1.json` (D1 akşamı) | 1 | `post_d1_hazard_v0` |
| `models/INDEX_POST_BREAK.json` (kırılma akşamı) | 2 | `break_floor_v0`, `break_floor_v0@ZERO` |

Kaynak dosyalar: `models/INDEX.json`, `models/INDEX_POST_D1.json`, `models/INDEX_POST_BREAK.json`.

### 2.7.3 Kanıt durumu (dürüst özet)

| Soru | Model | Backtest (H99, tasarıma maruz) | Eski kohort (açık / kasa) | Canlı |
|---|---|---|---|---|
| Kaç gün tavan? | `ceiling_hazard_v0` | **geçiyor**: RPS 0.150, KM kuralları 0.200–0.207 | açıkta geçemiyor; kasada ayırt edilemiyor; toplamda geçemiyor | LIVE 0; LATE 6 (bilgi) |
| D5 getiri | V1.5 | **geçiyor**: MAE 0.222, eğitim medyanı 0.306 | açık kümede ayırt edilemiyor | LIVE 1 (NETGL) |
| D10 arz üstü olasılığı | V1.5 | taban orana karşı ayırt edilemiyor | — | — |
| Yarın tavan bozulur mu? | `post_d1_hazard_v0` | birincil ayırt edilemiyor; "yarın" Brier'i backtest'te geçiyor | açıkta ve toplamda geçiyor; kasada ayırt edilemiyor | n = 0 (7 RETRO) |
| Yarın da taban mı? | `break_floor_v0` | **geçiyor**: ürüne karşı −0.190, sabit orana karşı −0.028 | test yapılmadı (karar) | n = 0 (7 RETRO) |
| D10'da düşer mi? | dört düşüş kimliği | birincil "belirsiz" | pooled kasada taban oranı geçiyor; hiçbiri V1.5'i geçemiyor | arşiv |
| v1 düzeltmeleri | clip / real / pooled | real ve pooled yakın dönemi bozuyor | pooled kasada KM'yi geçiyor | arşiv |

"Arşiv", modelin silindiği değil, ana ekranda öne çıkmadığı anlamına gelir; hepsi donmuş olarak listede kalır.

Kaynak dosyalar: `scores/scores.json`, `docs/SCORES.md` §5, `docs/MODELS.md`, `docs/faz6/S6_RAPOR.md`, `docs/faz7_vault/SKOR_RAPOR.md`, `scores/scores_break.json`, `scores/scores_post_d1.json`.

### 2.7.4 Canlı sicil

Skora giren en son bülten 2026-09-30'dur. Yedi arzın gerçekleşen yolu ve modellerin kayıtlı tahminleri:

| Arz | D1 | Gerçekleşen L | D10 getirisi | `ceiling_hazard_v0` medyan L | `break_floor_v0` ertesi gün taban olasılığı |
|---|---|---|---|---|---|
| CITAS | 2026-08-18 | 5 | +%73,7 | 5 | 0,14 |
| TKNKA | 2026-08-20 | 7 | +%122,5 | 5 | 0,14 |
| VEYAS | 2026-08-20 | 0 | %0,0 | RET (f3 yok) | 0,14 |
| KPEKS | 2026-08-21 | 5 | +%1,3 | 3 | 0,54 |
| INTET | 2026-09-01 | 4 | +%14,1 | 3 | 0,14 |
| BKRGY | 2026-09-02 | 0 | −%39,9 | 3 | 0,54 |
| NETGL | 2026-09-17 | 3 | −%36,2 | 3 | 0,50 |

Bu tablodaki tahminlerin hiçbiri kanıtlı canlı ölçüme girmez: tavan modeli için 6 satır LATE_RECORD'dur, kırılma modeli için 7 satırın hepsi RETRO'dur. Skor dosyalarındaki durum:

- `scores/scores.json`: model başına en çok 7 satır. `v1_5_h99` için n_live 1, n_late 5, ret 1. n < 10 olduğu için hiçbir canlı hücre ya da hüküm yok.
- `scores/scores_post_d1.json`: 7 arzın hepsi RETRO; `registry/post_d1/` henüz yok.
- `scores/scores_break.json` (`live_break`): 7 makine kaydı, hepsi RETRO; n = 0.

Kaynak dosyalar: `docs/SCORES.md` §1, `registry/records/*/`, `registry/post_break/*/`, `scores/`, `docs/faz8/LIVE_RAPOR.md`.

### 2.7.5 Uygulamanın durumu

- **Mimari:** Tauri 2 + Rust + çerçevesiz TypeScript; ağ yok; bugün yalnız macOS arm64. Son derleme `BorsAi.app` 8,4 MB.
- **Modeller:** 27 + 1 model gömülü ve Python'la tolerans içinde aynı (\|Δ\| ≤ 1e-9; çoğu satır bit-eşit, §7.11). Kırılma modelinin Rust portu ve üçüncü dizinin gömülmesi (EK 5) henüz yok; sade görünümdeki kırılma kartı bu yüzden yalnız makine kaydından ve skor dosyasından okur, senaryo modunda kırılma tahmini üretmez.
- **Görünümler:** Varsayılan "sade görünüm" (onaylı 12 pano, Safir paleti, IBM Plex yazı tipleri) ve kodu aynen duran "ayrıntılı görünüm".
- **Ana ekran:** kapı veri-güdümlüdür. Bugünkü dosyalarla `ceiling_hazard_v0` ve V1.5'in D5 getirisi öne çıkar; V1.5'in D10 olasılığı ve `post_d1_hazard_v0` "≈ fark net değil" işaretiyle durur; `break_floor_v0` skor dosyasındaki "ön eleme" etiketiyle gösterilir.
- **FAZ9_UI_FIX sonrası:** Analiz'den arz listesine dönüş, görünür Sicil künyesi, hesaplayıcıda geçmiş karşılaştırması ve gün grubu notu, işlem sayısı çubukları, ayrılmış performans sayımları, 1440 × 900 varsayılan pencere.

Kaynak dosyalar: `app/README.md`, `docs/app/UI_V2_RAPOR.md`, `docs/app/UI_FIX_RAPOR.md`, `docs/app/ui_fix_test_runs.txt`, `docs/prompts/FAZ9_APP_UI.md`.

### 2.7.6 Bekleyen görevler

İki görev dosyası bu kopyada var ama henüz commit'lenmedi. UI_FIX raporu ikisini de "izinli izlenmeyen, dokunulmadı" diye listeler.

**`docs/prompts/TUFE_2026_09.md`** (Sonnet 5 · yüksek). Eylül 2026 TÜFE satırının `data/raw/tuik/tufe_genel_2025_100.csv`'ye ilk gerçek aylık eklemesi. TÜFE dosyası bugün 2026-08'de bitiyor. TÜİK sunucusu komut satırı istemcilerine 403 döndüğü için tabloyu proje sahibi tarayıcıyla indirir. Ekleme önce geçici klonda prova edilir; araç tablonun eski aylarla birebir tuttuğunu denetler, tutmazsa hiçbir şeyi değiştirmeden durur. Neden önemli: reel büyüklük kullanan modeller (v1_real, v1_pooled, düşüş adayları) ilk işlem ayı − 2'nin TÜFE'sini ister; Kasım arzları Eylül TÜFE'sine ihtiyaç duyar.

**`docs/prompts/FAZ10_FABLE_STREAK_SPEC.md`** (Fable · yüksek). "Seri sürerken yarın da tavan mı?" sorusunun şartnamesi (`docs/specs_faz10/SPEC_STREAK_V0.md`). Bağlayıcı noktalar:

- Model her akşam o günün resmi bülten bilgisiyle (işlem sayısı, hacim, gün içi fiyatlar, tavanda kapanış) ertesi gün tavan olasılığını yeniden hesaplar.
- `ceiling_hazard_v0` ve onun 7 resmi kaydı değişmez; yeni model yan yana durur.
- Şartname önce "değer mi" sorusunu sayısal güç gerekçesiyle cevaplar. Orkestratörün maruziyet beyanına göre H99'da seri sürerken 409 risk satırı ve 67 olay var; ham veride 3. günden sonraki devam oranları %77–%82 arasında, yani neredeyse düz. Cevap "dur" ise geri dönüş yolu "her güne ayrı sabit"tir.
- Canlı aşama insan eli gerektirmeyen, makine sıralı bir akış olmalıdır.

Görevin 0. adımı HEAD'in `b045e71` olmasını bekliyor. Bugünkü HEAD `ee3796d` olduğu için başlatmadan önce bu satırın güncellenmesi gerekebilir (çıkarım).

Kaynak dosyalar: `docs/prompts/TUFE_2026_09.md`, `docs/prompts/FAZ10_FABLE_STREAK_SPEC.md`, `docs/app/UI_FIX_RAPOR.md` §1, `data/raw/tuik/tufe_genel_2025_100.csv`, `docs/faz7/FREEZE_RAPOR.md`.

### 2.7.7 Sıradaki adımlar

Repodaki görev dosyalarından ve proje bilgi alanındaki belgelerden çıkan sıra şöyledir. Proje bilgi alanındaki Ekim yol haritası kendi başında "ÖNERİ, ONAYLANMADI" der; proje sahibinin verdiği kararlar yalnız şunlardır: önce kapalı grup, bot push yapabilir, önce masaüstü.

1. **Yeni arz geldiğinde her şey durur.** Girdiler toplanır, 27 modelli kayıt ilk işlem gününden önce dondurulur, push edilir ve kanıtlanır. Bu, canlı kanıtın tek yoludur. İlk yeni arz, "yeni ticker" için önceden onaylı bir pin kuralı da isteyecek; bazı bekçiler yeni arz koduna kırmızı verir.
2. **Gün gün güncellenen tavan modeli.** Yol her zamanki gibidir: Fable şartnamesi (FAZ10), Opus uygulaması ve backtest'i, Fable'ın bağımsız yeniden üretimi, dondurma, uygulamaya taşıma, canlı sicil.
3. **Gece botu.** Her akşam resmi kaynakları okuyup sonuç satırlarını ve makine kayıtlarını yazacak, yeni arzı fark edip ilk işlem gününden önce donduracak ve kendi commit'ini push edecek. Yol haritası bunu "Ekim'in en değerli işi" sayar, çünkü yeni repoda yazılan kayıtlarda LIVE sayısı hâlâ 0'dır (tek LIVE hücre eski depodan gelen NETGL × V1.5 kaydıdır). En büyük bilinmeyen, bulut makinelerinin Borsa İstanbul ve KAP sitelerine erişip erişemeyeceğidir; ilk iş bir haftalık bağlantı yoklamasıdır.
4. **İmzalı veri paketi.** Kapalı gruptaki kullanıcıların repo kopyası olmayacak. Uygulama bugün çoğu ekranda yerel git reposunu okuyor. Önerilen çözüm, botun her gece yayımladığı imzalı bir paket: minisign (Ed25519) imzası, artan sıra numarası, dosya başına sha256. Kabul kapısı: aynı commit'te paket kipi ile repo kipi aynı ekranları birebir üretmeli.
5. **Yeni ekranlar.** Kırılma kartının Rust portu (EK 5); ölçekleri ayrı tutan bir canlı karne sayfası; "en çok benzeyen 5 geçmiş arz"; "neden bu tahmin" (katkılar); deterministik "kaç lot düşer" hesabı; yaklaşan arzlar takvimi.
6. **Windows derlemesi.** Mac'e özel iki nokta önce düzelir (`config.rs`'teki varsayılan Python yolu ve `borsai/tufe.py`'deki ekleme komutu).
7. **Takvim B'nin 2027 uzatması.** Resmi seans takvimi 2026-12-31'de bitiyor; Aralık başında uzatılmalı.
8. **Model geliştirme** yalnız "değer mi" kapısıyla: sıcak piyasa ve takvim yoğunluğu; KAP tahsisat verisi (yabancı ve yurt içi kurumsal pay, kişi başı lot).

Kaynak dosyalar: `docs/prompts/FAZ10_FABLE_STREAK_SPEC.md`, `docs/faz8/POST_BREAK_AKISI.md` §0, `claude/YOL_HARITASI_EKIM.md` (öneri durumunda), `claude/HANDOFF.md` §7, §11, `claude/STRATEJI.md` §4.

## 2.8 Python ortamı ve bağımlılıklar

**Yorumlayıcı ve ortam.** CPython 3.12.14, macOS arm64, `uv`'nin yönettiği kurulum. Sanal ortam repo içindeki `.venv/`'dir ve git'e girmez. Kurulum günü (21 Eylül) makinede `uv` ikilisi olmadığından ortam stdlib `venv` ve pip ile kuruldu:

```
~/.local/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
```

**Bağımlılıklar** `pyproject.toml`'da birebir sabittir (`requires-python = ">=3.12,<3.13"`):

| Tür | Paket ve sürüm |
|---|---|
| Çalışma zamanı | numpy 2.5.2, scikit-learn 1.9.0, scipy 1.18.0, joblib 1.5.3, threadpoolctl 3.6.0, narwhals 2.26.0 (scikit-learn'ün zorunlu bağımlılığı) |
| Geliştirme | pytest 9.1.1, pytest-xdist 3.8.0 (30 Eylül'deki test hızı işiyle eklendi) |

`requirements.lock`, kurulumdan sonraki `pip freeze` çıktısıdır: 13 satır, hash'siz, sürüm pinli düz liste (execnet, iniconfig, packaging, pluggy, Pygments dahil). Referans ortam `~/.borsai-venvs/v1_5-model-macos` aynı yorumlayıcıyı ve aynı altı çalışma zamanı paketini taşır.

**Çekirdeğin bağımlılık sınırı.** Tahmin kodu (`borsai/predict*.py`) **yalnız Python standart kütüphanesini** kullanır. Bu bir testle zorlanır: tahmin modüllerinin (`predict*.py` ve onların kullandığı `features.py`, `horizons.py`, `survival.py`) import kapanışı yalnız `{__future__, math, typing, decimal, dataclasses}` kümesine izin verir (`STDLIB_ALLOWED`; `tests/test_predict.py`, `test_faz1b_models.py`, `test_faz4_ceiling_path.py`, `test_faz5_post_d1.py`, `test_faz8_model.py`). Böylece aynı tahmin Rust'a birebir taşınabilir ve bağımlılıksız çalışır. Model **eğitimi** ise üçüncü taraf paket kullanır: `fit.py` numpy ve scikit-learn'ü (Ridge, LogisticRegression), `hazard.py` ve `post_d1.py` numpy'ı kullanır. Sonuç ve skor modüllerinin çoğu (`outcomes.py`, `registry.py`, `scoring.py`) standart kütüphaneyle yazılmıştır; numpy yalnız birkaç fonksiyonda yerel olarak import edilir. Sayılar ham metinden `Decimal` ile okunur; float'a çevrilip geri yazılmaz.

**Legacy'nin bağımlılıkları.** Eski V1.5 çekirdeği numpy, scipy, scikit-learn, joblib ve threadpoolctl kullanır ve çalışma zamanı sürümlerini kendisi denetler (`verify_runtime`). Bu yüzden yeni ortamın sürümleri eski referans ortamıyla aynı tutuldu.

**Sayısal tekrar üretilebilirlik.** H99 V1.5 benchmark'ı Windows'ta Python 3.12.13 ile üretilmişti. macOS'ta Ridge tahminleri en çok 2.7e-15, lojistik olasılıkları en çok 3.1e-9 farklı çıkıyor ve bir fold yakınsamıyor. Bu yüzden Faz 1 kabul testi "birebir" değil, toleranslı ve fold düzeyli yazıldı. macOS'taki ilk koşu sonraki bütün regresyonların bayt bayt altın referansı oldu. BLAS iş parçacığı ortam değişkenlerine bilerek dokunulmadı; bit-eşit altın testleri etkilenmesin.

**Testler.** `.venv/bin/pytest -q` sıralı koşar (varsayılan). Paralel koşu açık bayrakla çağrılır: `.venv/bin/pytest -q -n 6 --dist loadgroup`. Backtest havuzu açan testler tek bir grupta toplanır; aynı anda en çok bir havuz çalışır (gruplamasız 10 işçide süre 37–44 dakikaya çıkıyordu). Kural: ara koşular paralel, her görevin son kabul koşusu sıralı.

**Uygulama araç zinciri.** Rust (rustup, cargo), Node (nvm), Tauri CLI 2 ve Xcode komut satırı araçları. Uygulamanın `dependencies` listesi tam olarak iki pakettir (`@tauri-apps/api`, `@tauri-apps/plugin-dialog`); yazı tipleri ağ gerektirmesin diye `devDependencies`'ten paketlenir. CSP `default-src 'self'`'tir. Uygulama başkalarına dağıtılacaksa Apple imzası ve notarization, ondan önce de Borsa İstanbul veri lisansı sorusu gelir.

Kaynak dosyalar: `pyproject.toml`, `requirements.lock`, `docs/ENV.md`, `docs/infra/TEST_SPEED_RAPOR.md`, `borsai/*.py` (import satırları), `tests/test_faz1b_models.py`, `docs/MODELS.md` (Port kabulü), `docs/PROVENANCE.md` §2b, `docs/prompts/FAZ9_APP_UI.md` (K-UI-9), `claude/HANDOFF.md` §2.

## 2.9 Bölümün özeti

- BorsAi v2, eski deponun verisini ve V1.5'ini taşıyıp yönetişim aygıtlarını bırakan, altı kodlu kural ve push kanıtıyla işleyen yeni bir başlangıçtır (21 Eylül).
- On altı günde dokuz faz geçti: çekirdek ve ilk modeller, sicil ve skorlama, uygulama, tavan yolu, D1 sonrası, eski kohort ve kasa, v1 ve düşüş adayları, kırılma akşamı, sade görünüm.
- Bugün 30 model donmuş (27 + 1 + 2). Backtest'te "kaç gün tavan", "D5 getiri" ve "yarın da taban mı" soruları basit kuralları geçiyor; eski dönemde tavan modeli geçemiyor; canlıda kanıtlı ölçüm henüz yok.
- Çalışma biçimi, yazan el ile denetleyen elin ayrılmasına, önceden yazılmış beklentilere, "ölçmeden aktarma yok" ilkesine ve zaman kanıtı olarak push'a dayanır.
- En önemli ders: dürüst bir canlı karnenin tek yolu, her yeni arzı ilk işlem gününden önce dondurmaktır. Sıradaki işlerin hepsi (gece botu, gün gün tavan modeli, imzalı paket) bu hedefin etrafında dizilir.

Kaynak dosyalar: bu bölümün önceki alt bölümlerinde anılan dosyalar.

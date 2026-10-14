# TASK_ID: BORSAI_FAZ8_FABLE_BREAK_SPEC_20261001

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi.
- **Ağ:** yok.
- **Git:** yalnız okuma komutları ve her zaman `GIT_OPTIONAL_LOCKS=0` öneki. Sonda tek commit, yalnız kendi yollarınla. push/tag/amend yok.
- **Yazma:** YALNIZ `docs/specs_faz8/` (şartname, `KARARLAR.md`, `ekler/`) ve bu görev dosyası. Kod yok; profil betikleri `ekler/` altında olabilir.

## Rol
"Tavan bozulunca ne olur" sorusunun şartnamesini yazarsın: `docs/specs_faz8/SPEC_BREAK_V0.md`.

Yol her zamanki gibi:
1. şartname (sen);
2. Opus uygulama ve backtest;
3. Fable bağımsız yeniden üretim;
4. dondurma;
5. canlı sicil.

## Proje sahibinin kararları (bağlayıcı)
- **"Bize bugün lazım"** (29 Eylül). Eğitim yalnız güncel dönemle (H99, 2023-09 sonrası) yapılır; eski kohort eğitime girmez.
- **"Hiçbir modelimizin geçmişte (2020–23) başarılı olması gerekmez"** (1 Ekim). Eski dönem testi bu model için **yapılmaz**.
  - Kapı iki aşamalı: yakın dönem backtest'i (H99, tasarıma maruz) yalnız ön elemedir; asıl sınav canlı sicildir.
  - Uygulamada "öne çıkan" seçim kuralı bu iki ölçeğe göre **şimdi, önceden** yazılır.
- Değişiklik = yeni model_id. Terfi yok, yan yana modeller (CLAUDE.md).

## Bağlam
**Neden.** NETGL (ilk işlem 2026-09-17):
- D1–D3 tavan kapattı (L = 3). D4'te seri **tabanda kapanarak** bozuldu, D5–D10'un hepsi taban. D10 kapanışı arz fiyatının %36,2 altında (`docs/live/NETGL_D10_RAPOR.md`).
- Listeleme öncesi V1.5 D10 için +%25,8 demişti; bu, sicildeki tek gerçek LIVE tahmindi.
- Hiçbir modelimiz serinin **nasıl** bozulduğunu kullanmıyor:
  - `post_d1_hazard_v0` yalnız D1 tavan kapatan arzlarda ve yalnız D1 bilgisiyle çalışır;
  - tavan yolu (`ceiling_path_v0`) kırılma sonrasını ampirik hücrelerle verir;
  - V1.5 ve `fall_d10_v0` listeleme öncesidir.

**Orkestratörün keşfi — maruziyet beyanı.** Orkestratör bu görevi yazmadan önce H99'da şuna baktı:
- **Veri:** `..._bist_session_outcomes.csv` ve `..._d1_d3_d5_d10_targets.csv`.
- **Kırılma günü tanımı:** b = L + 1 (ilk tavan olmayan kapanış).
- **Kırılma türü:** `close == lower_limit` → taban; `close < reference_price` → düşüş; aksi → yükseliş/yatay.
- **Bulgular:**

  | Kırılma (L ≥ 1, L < 10) | n | sonrasında ≥ 2 ardışık taban | D10 ≤ arz fiyatı | ort. R10 |
  |---|---|---|---|---|
  | tabanda kapanış | 32 | 18 | 9 | +0.258 |
  | düşüşle, taban üstü | 27 | 2 | 7 | +0.421 |
  | yükseliş/yatay | 8 | 0 | 0 | +0.852 |

  - D1 tavan değil (L = 0, b = 1): 18 arzın 13'ünde D10 ≤ arz fiyatı. D1 tavan kapatan 81 arzda bu oran 16.
  - Seri hiç bozulmayan (L = 10): 14 arz.
  - Kırılma günü taban olan 35 arzın 19'unda ertesi gün de taban (bütün L'ler).

Bu sayılar **tasarıma maruzdur**: hipotez aynı veriden doğdu. H99 backtest'i bu yüzden yalnız ön elemedir. Bu tabloyu beklenti yazarken kullanabilirsin. **Bunun ötesinde özellik–sonuç ilişkisine bakma**; tek değişkenli profiller serbest. Şartnamenin başında bunu ve bu tabloyu maruziyet olarak beyan et.

**Mekanik ipuçları (orkestratör; karar senin).**
- Günlük fiyat marjı ±%10 ve D10'a kalan gün sayısı, D10'da arz fiyatının altına inmenin mümkün olup olmadığını sınırlar: kırılma kapanışı × 0.9^(10 − b) > arz fiyatı ise bu mekanik olarak imkânsızdır.
- Tabandaki kilit (satıcı fazlası), tavandaki kilidin aynası gibi ertesi güne taşınabilir.

**Dış araştırma (orkestratör, 1 Ekim; tam metin `docs/arastirma/TR_HALKA_ARZ_PIYASASI_20261001.md`).** Etiketleri: [R] resmî ya da hakemli, [B] basın, [Ç] çıkarım. Şartnameye girecek her sayı repoda yeniden ölçülür. İlgili bulgular:
- **Yastık aritmetiği** [Ç; bant kuralına dayanır]:
  - D1'den N ≥ 6 tavandan sonra D10'da arz altı mekanik olarak imkânsız.
  - Genel kural: k_t = ln(P_t / arz fiyatı) / ln(1/0.9) ve r_t = 10 − t. k_t ≥ r_t ise olasılık yapısal olarak 0'dır.

  Model bu sıfırı öğrenmeye veri harcamamalı.
- **Kilitlenme dokunmadan farklıdır** [R: Bildik & Gülay 2006, BIST]. Kapanışta limitte kalmak, limite yalnız dokunmaktan çok daha güçlü etki taşır. Çin'de tabanda kapanan günden sonraki gün ~%86 aynı yön [R, PLOS ONE 2015; özet düzeyi, doğrulanmalı]. Türkiye'de kırılma sonrasını ölçen hakemli çalışma yok.
- **VBTS 1. kademe** (açığa satış ve kredili işlem yasağı, bir ay) tavan serisindeki arzlara seans ~6–9 civarında geliyor [B; 3 vaka; kriterler gizli]. Tedbir KAP'ta akşam ilan edilir, yani t akşamı bilinir.
- **Tavana karşı satan yok:** mevcut ortaklar 180 gün satamaz; arz paylarında açığa satış fiilen yok [R]. Seriyi arz sahipleri ve ikincil alıcıların satışı bitirir.
- **Eğitim penceresindeki tek dağıtım kuralı kırılması** 19.09.2024'tür (i-SPK.128.23) [R]. ±%10 bant ve bireysele eşit dağıtım pencere boyunca sabit.
- **Eylül 2026 fon krizi** [B]:
  - 16–17 Eylül'de 130 fon tasfiyeye alındı; BIST100 Eylül'de −%16,65.
  - NETGL'nin D1'i (17 Eylül) krizin başladığı güne denk geliyor. NETGL'deki taban serisi kısmen piyasa genelindeki çöküşün sonucu olabilir; temiz bir "kırılma mekaniği" örneği sayılmamalı.
  - Eğitim kümesinde ilk on seansı böyle bir stresle çakışan arz yok ya da çok az.
  - Şartname, "rejim dışı" dönemde canlı sonuçların nasıl okunacağını ve kartta nasıl bir uyarı gösterileceğini önceden yazmalı; uyarı model girdisi olmaz.
- **Doğrulanmamış:** BIST Pay Piyasası Prosedürü 21.09.2026'da revize edildi (rev. 54); içeriği kontrol edilemedi. Şartname ±%10 bant ve ilk gün baz fiyat kuralını **açık varsayım** olarak yazsın. Orkestratör bunu dondurmadan önce doğrulatacak.

**Veri ve altyapı.**
- **H99 seans dosyası:** 990 satır = 99 × 10; açılış, en yüksek, en düşük, kapanış, hacim, AOF, işlem sayısı, referans, alt ve üst limit (ham ve düzeltilmiş).
- **Canlı `data/outcomes/<T>.csv`:** alt limit, açılış, en düşük ve hacim YOK. Kayıt akışı bunları bültenden okumalı; `post_d1` kaydının `d1.fields_raw` kalıbı buna örnektir (`borsai/freeze.py`, `borsai/predict_post_d1.py`).
- **POST_D1 aşaması bir emsaldir** (SPEC_POST_D1_V0 §7; `models/INDEX_POST_D1.json`; `registry.t_open`; push kanıtı; `scores/scores_post_d1.json`; uygulamada P2 sihirbazı).
  - Yeni aşama bunu **azami ölçüde yeniden kullanmalı**; mümkünse "D_j sonrası kayıt" genellemesi olarak.
  - Gereken altyapıyı ve onun maliyetini açıkça yaz.
- **Operasyon yükü:** ayda yaklaşık 3 arz, yani 2–3 kırılma akşamı. Her biri, ertesi seansın açılışından önce kayıt ve push ister. D1 akşamı akışı (P2 sihirbazı) zaten var; b = 1 durumunda aynı akşam iki kayıt mı, tek kayıt mı olacağını sen karar ver.
- **Canlı 7 arz** (`data/outcomes/`) tasarıma girmez; yeni model için RETRO olurlar. NETGL dahil.
- **Eski kohort, kasa ve OOT dosyaları:** `registry/oot/`, `data/outcomes_oot/` ve `scores/scores_oot.json` bu görevde **okunmaz**; gerekmiyor.

## Şartnamenin cevaplaması gerekenler
0. **Değer mi? (devam / dur önerisi, şartnamenin ilk bölümü).** Proje sahibi bu işin "iş olsun diye" yapılmasını istemiyor. Şartname önce şunu dürüstçe cevaplar:
   - **Ürün kırılma akşamı bugün ne söylüyor?** `ceiling_path_v0` kırılma sonrası hücreleri Z/B grupları ve m ile kurulu; kırılma türü bilgisini kullanmıyor (SPEC_CEILING_PATH_V0 §3).
   - **Yeni model ne kadar ekleyebilir?** Maruziyet tablosu ham veride iki şey söylüyor:
     - kırılma türü yakın günleri güçlü ayırıyor: tabanda bozulanların %56'sında ≥ 2 ardışık taban, taban üstünde bozulanlarda %7;
     - D10 ≤ arz oranını ise neredeyse ayırmıyor: 9/32 ve 7/27.
   - **Kazanç hangi hedefte ve ne büyüklükte beklenir?** Birincil hedefi buna göre seç. "D10 ≤ arz" yerine "sonraki günler taban mı / D10'a kadar kaç taban" daha güçlü olabilir; karar senin, gerekçesiyle.
   - **Bedeli nedir?** Uygulama oturumu, altyapı ve proje sahibinin akşam iş yükü.
   - **Sonuç:** "devam" ya da "dur" önerisi tek cümleyle. Beklenen kazanç ürünün bugünkü cevabından ayırt edilemeyecek kadar küçükse açıkça "dur" yaz ve gerekçesini ver. Şartnamenin geri kalanı yine yazılır, ama kısa tutulur.
1. **Olay ve kapsam.**
   - Kırılma akşamının tanımı (b = 1..?, D10'a yakın b'ler).
   - Durdurma, yarım gün, limit yok ve işlem yok hâlleri.
   - L = 0 (D1 tavan değil) kapsamda mı?
   - Seri hiç bozulmazsa ne olur?
2. **Hedef(ler) ve tek birincil.**
   - Öneri: birincil P(D10 kapanışı ≤ arz fiyatı | kırılma akşamı bilgisi). Proje sahibinin "düşer mi" sorusu budur.
   - İkincil: ertesi seans taban mı; D10 getirisi.
   - b'ye göre hedefin tanımsız olduğu hâller.
3. **Özellikler (≤ 3; mekanizmayla gerekçeli; sonuç görmeden).**
   - Tanım, bülten alanı, birim, dönüşüm, eşitlik ve tick kuralı (`close == lower_limit` ham mı düzeltilmiş mi), eksik hâller.
   - Listeleme öncesi özellik miras alınacak mı?
4. **Model sınıfı ve parametre bütçesi.**
   - Küçük L2 lojistik ya da daha basiti.
   - Sıfır modeli (kırılmalar arasındaki taban oran, `@ZERO`/`@INF` kalıbı) zorunlu.
   - Izgara ve iç CV SPEC_C_V0 ya da SPEC_CEILING_V0 kalıbında.
5. **Karşılaştırıcılar ve birincil hücre.**
   - **Asıl karşılaştırıcı, bugün ürünün kırılma akşamı verdiği cevaptır.** Ölç ve tanımla: `ceiling_path_v0`'ın gözlenen yol ile koşullu D10 p_up'ı ya da ürünün o akşam gösterdiği eşdeğer.
   - Ayrıca: kırılmalar arasındaki taban oran; listeleme öncesi `fall_d10_v0_h99` ve `v1_5_h99` p_up D10.
   - Birincil hücre tek; geri kalanı kural, ikincil ya da keşiftir.
6. **Önceden yazılmış beklenti** (SPEC_CEILING_PATH_V0 §6 kalıbı).
   - Her hücre için beklenen fark aralığı ve "aralık 0'ı dışlar mı".
   - Maruziyet tablosundan ve MODELS.md'deki karşılaştırıcı başarımından türetilir; hiçbir yeni skor hesaplanmaz.
   - "Beklentiden çok iyi" eşiği tanımlanır: aşılırsa Fable bağımsız yeniden üretimi zorunludur.
7. **Backtest planı.**
   - Walk-forward: eğitim satırının hedef seansı, test arzının kırılma akşamından kesin önce.
   - Fold alt sınırları; aylık blok bootstrap (SPEC_SCORING §8).
   - Yakın dönem hücresi: ilk işlem ≥ 2024-01-01, Faz 7 kalıbı.
   - Sızıntı noktaları ve testleri.
8. **Uygulama "öne çıkan" kuralı (önceden yazılı).**
   - Yalnız yakın dönem backtest'i ve canlı sicile dayanır.
   - Canlı n eşiği ve n < eşik iken ne gösterileceği tanımlanır.
   - Eski dönem kullanılmaz.
9. **Canlı kayıt aşaması (yeni ya da genelleştirilmiş).**
   - Ad, şema, dosya yolu, model dizini.
   - Girdi: kırılma gününün resmi bülten alanları, sha'larıyla.
   - Zaman sınırı: ertesi seans açılışı, `registry.t_open` kalıbı. Kanıt: push kanıtı.
   - LIVE/LATE/RETRO sınıf kuralı; ayrı skor dosyası ve ölçek (hiçbir ölçekle toplanmaz).
   - **Akşam yükü olmadan skorlama seçeneği.** Model tamamen resmi bülten alanları ve dondurulmuş parametrelerle deterministikse iki yol var:
     - **(a) Makine sıralı:** her kırılma akşamı kayıt + push istemeden, "model, sonuçlar repoya girmeden dondurulmuştu" kuralıyla (git DAG; eski kohorttaki `MACHINE_SEQUENCED` kalıbı) canlı ölçekte skorlamak.
     - **(b) Gece kaydı:** her kırılma akşamı kayıt + push (POST_D1 kalıbı).

     İkisini karşılaştır ve birini seç. Ölçüt: proje sahibinin akşam yükü ile kanıt gücü. Bugünkü 7 canlı kaydın hepsi geç yazıldığı için sayılmadı; akşam yükü bu yüzden gerçek bir risk.
   - CLAUDE.md kural 1'e eklenecek **önerilen metin** (proje sahibi onaylar; sen CLAUDE.md'ye dokunmazsın).
   - `borsai/` altında gereken değişikliklerin listesi ve tahmini oturum sayısı.
10. **Uygulama etkisi (kısa):** yeni kart ya da satır, ana hatlar (sonra EK 4).
11. **Ret ve uyarılar.**
12. **Maruziyet.** Orkestratör tablosu; `experiments/log.jsonl`'da H99'da kırılma sonrası ile ilgili denenmiş varyantlar; Faz 4 tavan yolu hücreleri; senin profillerin.
13. **Kabul testleri** (Opus için, kanıtlanabilir) ve **sözde kod**.
14. **Açık sorular** (proje sahibine, en çok 5; her birinde önerin).

Şartname kendi içinde karar verir; "Opus seçsin" bırakılmaz.

## ÖNCE OKU
- CLAUDE.md
- `docs/specs/SPEC_SCORING.md` (§2, §3 tavan etiketi, §5 sınıflar, §7–§8)
- `docs/specs_faz5/SPEC_POST_D1_V0.md` (tamamı: aşama, kayıt, zaman kanıtı, skor kalıbı) ve `docs/SPEC_DEVIATIONS.md` H bölümü
- `docs/specs_faz4/SPEC_CEILING_PATH_V0.md` (kırılma sonrası hücreler, koşullu görünüm, §6 beklenti kalıbı)
- `docs/specs_faz7_c/SPEC_C_V0.md` ve `KARARLAR_C.md` (düşüş hedefi, ızgara, yakın dönem hücresi, §5.5 kalıbı)
- `docs/specs_faz7/SPEC_HAZARD_V1.md` §5 (yakın dönem tanımı)
- `docs/MODELS.md` (Faz 4 tavan yolu, Faz 5 D1 sonrası, Faz 7C düşüş bölümleri)
- `docs/live/NETGL_D10_RAPOR.md`
- `docs/arastirma/TR_HALKA_ARZ_PIYASASI_20261001.md` (özellikle "Tavan bozulunca…", "Test edilebilir öneriler" C bölümü ve "Eylül 2026 sonu")
- `borsai/freeze.py` (post_d1), `borsai/predict_post_d1.py`, `borsai/predict_path.py`, `borsai/registry.py` (`t_open`), `borsai/outcomes.py`, `borsai/scoring.py` (post_d1 bölümü)
- `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv` ve `..._targets.csv`

## Adımlar
0. **Taban.**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3` = `origin/main`.
   - `GIT_OPTIONAL_LOCKS=0 git status --porcelain --untracked-files=all`: yalnız bu görev dosyası ve `docs/arastirma/TR_HALKA_ARZ_PIYASASI_20261001.md`. Başka bir şey varsa DUR.
1. Okuma.
2. **Tek değişkenli profiller** (`ekler/profil_*.txt`, betik `ekler/`):
   - b'nin dağılımı;
   - kırılma türlerinin sayımı;
   - kırılma günü alanlarının dağılımları.

   Sonuç sütunlarıyla birleştirme yok; maruziyet tablosu tek istisnadır ve zaten verilmiştir.
3. Şartname ve `KARARLAR.md`.
4. Commit.

## Kurallar
- `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `tests/`, `app/`, `docs/specs*` (faz8 hariç), `CLAUDE.md` salt okunur.
- Hiçbir model fit edilmez, hiçbir walk-forward skoru hesaplanmaz. Bunu şartnamenin başında beyan et.
- `docs/specs_faz8/` altına en çok ~1 MB.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma (bülten adlarını `th?YYYYMMDD` diye yaz).
- `git add -A` yok. Commit:
  ```
  git add docs/specs_faz8 docs/prompts/FAZ8_FABLE_BREAK_SPEC.md docs/arastirma/TR_HALKA_ARZ_PIYASASI_20261001.md
  git commit -m "BORSAI_FAZ8_SPEC: break-evening model spec with pre-registered expectations and live stage, before implementation; market research note" -- docs/specs_faz8 docs/prompts/FAZ8_FABLE_BREAK_SPEC.md docs/arastirma/TR_HALKA_ARZ_PIYASASI_20261001.md
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Rapor Türkçe.

## Teslim (rapor)
- Commit hash'i.
- 10 satırlık özet:
  - **"devam / dur" önerisi ve gerekçesi (ilk satır);**
  - olay ve kapsam, hedef, özellikler, model sınıfı, parametre bütçesi;
  - birincil hücre ve beklentisi;
  - öne çıkan kuralı;
  - canlı kayıt aşaması;
  - tahmini uygulama oturumu.
- Açık sorular ve önerilerin.

## Kabul kapısı
- **K0** §0 "değer mi" bölümü sayısal gerekçeyle "devam" ya da "dur" diyor.
- **K1** Şartname 1–14'ün hepsini cevaplıyor; hiçbir karar Opus'a bırakılmamış.
- **K2** Birincil hücre ürünün bugünkü kırılma akşamı cevabına karşı; beklenti sayısal ve aralıklı; "çok iyi" eşiği var.
- **K3** Maruziyet beyanı başta; eski kohort ve kasa dosyaları açılmadı; profiller tek değişkenli.
- **K4** Canlı aşamanın zaman kanıtı, sınıf kuralı ve CLAUDE.md öneri metni yazılı; öne çıkan kuralı yalnız yakın dönem ve canlıya dayanıyor.
- **K5** Commit yalnız `docs/specs_faz8/`, bu görev dosyası ve araştırma notu.

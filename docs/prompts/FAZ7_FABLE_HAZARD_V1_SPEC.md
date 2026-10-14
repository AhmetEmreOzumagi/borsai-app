# TASK_ID: BORSAI_FAZ7_FABLE_HAZARD_V1_SPEC_20260925

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi.
- **Ağ:** yalnız resmi kaynaklarda (TCMB EVDS, TÜİK, Borsa İstanbul) bir veri serisinin var olup olmadığını ve yayım zamanını görmek için. Veri indirilmez; indirme uygulama görevinin işidir.
- **Git:** yalnız okuma, her zaman `GIT_OPTIONAL_LOCKS=0`. Sonda tek commit, yalnız kendi yollarınla.
- **Yazma:** YALNIZ `docs/specs_faz7/` (şartname ve `ekler/`) ve bu görev dosyası. Kod yok (tanı betikleri `ekler/` altında olabilir). push/tag/amend yok.

## Bağlam (ölçüldü)
Eski kohort (2020-01-01…2023-09-21) açık kümesinin (71 arz) zaman-dışı skorları çıktı. `scores/scores_oot.json`, `docs/SCORES_OOT.md`, `docs/faz6/S6_RAPOR.md`; senin bağımsız denetimin `docs/fable_faz6_s6/AUDIT.md`, hüküm S6_OK. Birincil hücreler:

| Model | Fark [%95], n | Hüküm |
|---|---|---|
| `ceiling_hazard_v0` RPS − `base_km_expanding` | +0.069 [+0.001, +0.131], 68 | geçemiyor |
| `pb_ceiling_v0` RPS − `base_km_expanding` | +0.048 [−0.005, +0.100], 59 | ayırt edilemiyor |
| `post_d1_hazard_v0` koşullu RPS_1 − `ceiling_hazard_v0` koşullu | −0.042 [−0.066, −0.020], 59 | geçiyor (MACHINE_SEQUENCED) |
| V1.5, PB, tavan yolu (D5 MAE) | nokta −0.03…−0.01, aralıklar 0'ı içeriyor | ayırt edilemiyor |

Mekanizma notları (S6_RAPOR §9, AUDIT §5; keşif):
- `ceiling_hazard_v0` bu kohortta seriyi uzun görüyor. Ortalama S_k (model / KM / gözlenen): k = 5'te 0.665 / 0.414 / 0.529, k = 10'da 0.431 / 0.141 / 0.132. H99'da donmuş KM, k = 10'da gözlenene çok yakın.
- Yıl kırılımı: 2021 +0.148, 2022 +0.091, 2023 −0.037 (n 26 / 20 / 21). Ortalama L: 2021'de 3.4, 2022'de 3.3, 2023'te 7.2. Tahsis rejiminde PRE_20211111 +0.149 (22), THRESH100 +0.030 (31), EQUAL_DIST +0.032 (15).
- `ceiling_hazard_v0` = 3 paylaşılan katsayı (f1 = ln arz büyüklüğü, **nominal TL, kırpılmıyor**; f2; f3 [p05, p95] kırpılıyor) + 3 gün sabiti (SPEC_CEILING_V0 §4–§7). Beklenen işaret β_f1 > 0: büyük arz kısa seri. 2020–2022 arzları nominal TL'de eğitim aralığının çok altında; model ekstrapolasyonla uzun seri öngörüyor olabilir. Bu bir hipotezdir, test edilmedi.
- `post_d1_hazard_v0`'ın kazancı düzey düzeltmesi değil, yeniden sıralama. Hem o hem ana model k ≥ 7'de gözlenenin çok üstünde (k = 10: 0.47 / 0.49'a karşı 0.15).

**Veri kullanım kuralları (KARARLAR D4):**
- Açık küme (71 arz: 68'i f3'lü, 59'u PB girdili) skorlar yayımlandığı için artık yeni model kimliklerinin keşfine ve eğitimine girebilir: `registry/oot/inputs/<T>.json` + `data/outcomes_oot/<T>.csv`. Aynı şemalar; `borsai.features` aynı tanım.
- Kasa (64 arz) hiçbir keşfe ve eğitime girmez. Sonuçları repoda yok. Bir kez açılır (SPEC_OOT_PRE_H99_V0 §9).

**Proje sahibinin sorusu (bu şartnamenin cevaplaması gereken):** "2020–2021 piyasası bugünkünden farklıydı; eski arzları eğitime katmak bugünkü tahminleri bozmaz mı?" Bu, önceden yazılmış bir testle cevaplanmalı.

**Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.**

## Bu görevin amacı
`docs/specs_faz7/SPEC_HAZARD_V1.md`: tavan serisi modelinin v1 ailesi. Yol her zamanki gibi:
1. şartname (sen);
2. Opus uygulama (A kod ve kurallar, B backtest);
3. Fable yeniden üretim;
4. dondurma;
5. eski kohort kayıtları ve kasa;
6. canlı.

## Şartnamenin cevaplaması gerekenler
1. **Tanı (keşif, `ekler/`).** v0'ın açık kümedeki hatası nereden geliyor? İzinli: S2 kayıtlarındaki donmuş v0 tahminleri ile açık küme sonuçları; f1/f2/f3 kutularına, yıla ve rejim etiketine göre kalibrasyon; H99 ve açık kümede f1 dağılımları; dönem başına KM. Hepsi "keşif" etiketli. Yasak: aday model fit etmek ya da walk-forward skorlamak (o Opus'un, günlüğe yazılarak yapacağı iştir); kasa üyelerine herhangi bir amaçla bakmak.
2. **Aday model kimlikleri (en çok 3).** Her biri için mekanizma gerekçesi, parametre bütçesi (olay/parametre ≥ 10), eğitim kümesi ve ret kuralları. Değerlendirilmesi gereken seçenekler (seç, birleştir ya da gerekçeyle ele):
   - (a) **Sıfır yeni parametre:** f1 ve f2 eğitim aralığına kırpılır (f3 gibi). Yalnız ekstrapolasyon hipotezini sınar.
   - (b) **Dönemden bağımsız büyüklük:** reel (TÜFE ile), döviz cinsinden ya da göreli (ör. son N ayın arz büyüklüklerine göre). Her birinin resmi kaynağı, yayım gecikmesi ve listeleme anında bilinirliği (point-in-time) tanımlanır.
   - (c) **Havuzlanmış eğitim (H99 + açık küme)** ve bir rejim/düzey terimi (ör. eşit dağıtım öncesi/sonrası). Canlıda terim bugünkü rejime sabitlenir.
   
   PB karşılığı (`pb_ceiling_v1`) ve tavan yolu türevleri (sıfır parametreli eşleme) bu 3'ün içinde mi dışında mı, açıkça yaz. `post_d1_hazard_v1` bu şartnamenin dışında; ebeveyn değişirse ne gerekir, yalnız not.
3. **Önceden yazılmış testler ve birincil hücreler.** Her aday için:
   - (i) **Yakın dönem testi:** H99 walk-forward (2024–2026 fold'ları), v1 − v0, RPS; "eski veriyi eklemek yakın dönemi bozuyor mu" sorusu burada. Karar kuralı ve tolerans önceden yazılır (ör. aralığın üst sınırı ≤ +δ). H99 tasarıma maruzdur; bunu yaz.
   - (ii) **Kasa testi (64 arz, tek seferlik):** v1 − `base_km_expanding` ve v1 − `ceiling_hazard_v0`, RPS; ayrıca k = 10 Brier.
   - (iii) **Canlı:** SPEC_SCORING kalıbı.
   
   Açık küme bu adaylar için test değildir; havuzlanmış adaylarda eğitimdir, diğerlerinde tasarıma maruzdur. Açık kümede hesaplanan her sayı "keşif" diye etiketlenir.
4. **Önceden yazılmış beklenti** (SPEC_CEILING_PATH_V0 §6 kalıbı): her birincil hücre için yön ve aralık. Şu anki bilgin (açık küme sonuçları) açıkça beyan edilir; beklenti kasa ve canlı için yazılır.
5. **Kasa planı.**
   - Yeni kimliklerin 135 üyelik eski kohort kayıtları, kasa sonuçları çıkarılmadan önce commit ve push edilir.
   - Açık kümedeki satırları tanım gereği OOT_RETRO olur. Bunu yaz ve sınıf formülüyle uyumunu göster.
   - Kasa tek seferlik açılır. Önerim: açılış, "düşenler" (C) özellik şartnamesi de önceden kaydedildikten sonra, **birlikte** yapılır. Kabul, ret ya da alternatif; gerekçesiyle.
   - Kasa açılınca 19 donmuş modelin kasa sonuçları da ayrı anahtarla çıkar (`oot_pre_h99_sealed`).
6. **Uygulama (kısa).** Eğitim tablosu (`data/training_table_v2.csv`: H99 + açık küme; `training_table.csv` dokunulmaz), yeni INDEX girişleri, canlı kayıtlara etkisi (kayıt kendi aşamasının bütün modellerini içerir), uygulama listesi ve altın MANIFEST etkisi.
7. **Ret ve uyarılar** (f3 yok, aralık dışı, eksik resmi seri).
8. **Maruziyet beyanı.** Açık küme sonuçlarını gördün (S6 denetimi); H99'da denenmiş varyant sayısı (`experiments/log.jsonl`); bu şartnamenin tanı adımı.
9. **Kabul testleri** (Opus için, kanıtlanabilir) ve **sözde kod**.
10. **Açık sorular** (proje sahibine, en çok 5, her birine öneri).

Şartname kendi içinde karar verir; "Opus seçsin" bırakılmaz.

## Adımlar
0. **Taban.** `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3`, `git status --porcelain`. İzinli izlenmeyen: bu görev dosyası ve `docs/prompts/FAZ7_CODEX_PROSPECTUS_B1..B4.md` (repo dışında koşan Codex görevleri; dokunma). Başka bir şey varsa DUR.
1. **Okuma.** CLAUDE.md; docs/specs/SPEC_CEILING_V0.md, SPEC_PB_V0.md, SPEC_SCORING.md; docs/specs_faz4/SPEC_CEILING_PATH_V0.md; docs/specs_faz5/SPEC_POST_D1_V0.md; docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md (§3, §6, §8, §9) ve KARARLAR.md (D4, D6); docs/faz6/S6_RAPOR.md; docs/fable_faz6_s6/AUDIT.md; docs/MODELS.md; borsai/features.py, preprocess.py, hazard.py, survival.py, predict_hazard.py; experiments/log.jsonl.
2. **Tanı** (`ekler/tani_*.py`, `ekler/tani_*.txt`).
3. **Şartname.**
4. **Commit.**

## Kurallar
- `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `tests/`, `app/` ve öbür `docs/specs*` dizinleri salt okunur.
- Hiçbir model fit edilmez, hiçbir walk-forward skoru hesaplanmaz. Kasa üyelerinin hiçbir dosyasına bakılmaz. `docs/faz6/dogrulama/EXPOSURE.md` §3 okunmaz. Hangi kodun kasada olduğu yazılmaz.
- `docs/specs_faz7/` altına en çok ~1 MB.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit:
  ```
  git add docs/specs_faz7 docs/prompts/FAZ7_FABLE_HAZARD_V1_SPEC.md
  git commit -m "BORSAI_FAZ7_SPEC: ceiling hazard v1 family spec with pre-registered near-era, vault and live tests" -- docs/specs_faz7 docs/prompts/FAZ7_FABLE_HAZARD_V1_SPEC.md
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Rapor Türkçe.

## Teslim
- Commit hash'i.
- Şartnamenin başında 10 satırlık özet: tanı sonucu, adaylar, bütçe, birincil hücreler ve beklentiler, kasa planı.
- Açık sorular.

## Kabul kapısı
- **K1** 1–10 maddenin hepsi cevaplı; en çok 3 aday kimlik; hiçbir karar Opus'a bırakılmamış.
- **K2** Yakın dönem, kasa ve canlı testleri; birincil hücreler ve sayısal, aralıklı beklentiler önceden yazılı.
- **K3** Tanı yalnız açık küme ve H99 üzerinde; "keşif" etiketli; kasa hiç kullanılmadı; aday fit edilmedi.
- **K4** Commit yalnız `docs/specs_faz7/` ve bu görev dosyası.

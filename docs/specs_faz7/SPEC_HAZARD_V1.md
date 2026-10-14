# SPEC_HAZARD_V1 — tavan serisi modeli v1 ailesi (`ceiling_hazard_v1_clip`, `ceiling_hazard_v1_real`, `ceiling_hazard_v1_pooled`)

Görev: BORSAI_FAZ7_FABLE_HAZARD_V1_SPEC_20260925. Yazım: 2026-09-25, Fable. Uygulayıcı: Opus (A kod ve kurallar, B backtest); sonra Fable sıfırdan yeniden üretim; dondurma; eski kohort kayıtları ve kasa; canlı. Bu belge `docs/specs_faz7/` altındadır; `docs/specs*` (Faz 1–6) değişmemiştir. Kod yok; tanı betiği ve çıktısı `ekler/`.

**Beyan (K3).** Bu şartname yazılırken hiçbir model fit edilmedi, hiçbir walk-forward skoru hesaplanmadı, kasa (SEALED) üyelerinin hiçbir dosyası açılmadı, `docs/faz6/dogrulama/EXPOSURE.md` §3 okunmadı. Bakılanlar: (a) açık kümenin (71 arz) yayımlı zaman-dışı skorları (`scores/scores_oot.json`, `docs/SCORES_OOT.md`, `docs/faz6/S6_RAPOR.md`, `docs/fable_faz6_s6/AUDIT.md`); (b) S2 kayıtlarındaki donmuş `ceiling_hazard_v0` tahminleri ve açık küme sonuçları üzerinde bu görevin tanısı (`ekler/tani_v1.py` → `ekler/tani_v1_cikti.txt`; **hepsi "keşif"**); (c) H99 eğitim tablosu ve yayımlı v0/KM fold ledger'ları; (d) resmi kaynak sayfaları (`ekler/kaynak_kontrol_20260925.md`; veri indirilmedi). Maruziyetin tamamı §10'dadır.

İşaretler: **[ÖLÇTÜM]** = bu oturumda dosyadan/komuttan; **[KEŞİF]** = açık küme sonuçları görüldükten sonra hesaplanan sayı (hüküm değildir); **[ÇIKARIM]** = yorum; **[KARAR]** = bu şartnamenin bağlayıcı kararı. Görev metnindeki 10 madde → bölüm: 1→§1, 2→§2, 3→§5, 4→§6, 5→§7, 6→§8, 7→§9, 8→§10, 9→§11 + §12, 10→§13. Görev kuralı: "Opus seçsin" bırakılmamıştır; her seçim [KARAR] ile yazılıdır.

## Özet (10 satır)

1. **Tanı [KEŞİF]:** v0'ın açık kümedeki hatası iki parçadır. (i) **Ekstrapolasyon:** f1 nominal TL; 68 skorlanan arzın 28'i H99 eğitim minimumunun, 40'ı p05'inin altında (2021: 20/26, 2022: 15/20); z_f1 medyanı −1.97, en düşük −4.86; β_f1·z_f1 hazard logit'ini ortalama −0.85 kaydırıyor (2021–2022'de −1.1). Donmuş v0'da yalnız z_f1/z_f2 eğitim [p05, p95]'ine kırpılınca RPS 0.269 → 0.231 (KM 0.200): farkın **yaklaşık yarısı** ekstrapolasyon. (ii) **Dönem:** kırpılsa da 2021–2022'de S_10 tahmini 0.31–0.40, gözlenen 0.04–0.05; dönem KM'si (S_10 = 0.04/0.05) H99'dan (0.14) farklı; v0 yalnız 2023 üyelerinde KM'yi geçiyor. Tahsis rejimi: PRE_20211111 +0.149, THRESH100 +0.030, EQUAL_DIST +0.032.
2. **Üç aday, iç içe merdiven [KARAR]:** `ceiling_hazard_v1_clip` (a: f1, f2, f3 hepsi eğitim [p05, p95]'ine kırpılır; H99 eğitimi; sıfır yeni parametre) → `ceiling_hazard_v1_real` (b: f1 yerine **f1r = ln(büyüklük / TÜFE_{m−2})**, TÜİK TÜFE 2025=100; kırpma aynen; H99 eğitimi; sıfır yeni parametre) → `ceiling_hazard_v1_pooled` (c: f1r + havuzlanmış eğitim H99 + açık küme, 165 arz, ve **bir** rejim terimi r = 1[tahsis rejimi ≠ EQUAL_DIST_20230330], cezasız; canlıda r = 0). Kural satırı: `ceiling_hazard_v1_pooled@INF` (gün + rejim sabitleri). (a) ve (b)'nin @INF ucu `ceiling_hazard_v0@INF` ile bit-eşittir, ayrıca kaydedilmez.
3. **Bütçe:** (a), (b): 6 parametre / 83 olay = 13.8; (c): 7 parametre / 142 olay = 20.3 olay/parametre (≥ 10). Havuz: 880 kişi-dönem satırı.
4. **Deflatör [KARAR]:** TÜİK TÜFE genel endeksi (aylık, 2025=100, revizyonsuz; ay m'nin endeksi m+1'in 3. günü ~10:00'da yayımlanır, resmi sayfa `ekler/kaynak_kontrol_20260925.md`). Kural: T'nin ayı m ise **m−2** ayının endeksi (her zaman yayımlanmış; takvim dosyası gerekmez). USD (TCMB) ve XU100 deflatörleri gerekçeyle reddedildi (§3.2).
5. **Yakın dönem testi (i):** H99 walk-forward, ilk işlem ≥ 2024-01-01 olan **78 fold** (22 ay bloğu, 69 olay); hücre: v1 − v0 RPS (v0 altın ledger `976b4dcea981`). Karar: aralığın alt ucu > 0 → "eski veri/dönüşüm yakın dönemi **bozuyor**"; üst ucu ≤ **+0.010** → "tolerans içinde"; diğer → "belirsiz". Proje sahibinin sorusunun cevabı `v1_pooled`'ın bu hücresidir. H99 tasarıma maruzdur (§10).
6. **Kasa testi (ii; tek seferlik, n ≈ 60):** her aday için birincil hücre RPS − `base_km_expanding` (kayıttaki donmuş H99 KM); ilan edilmiş ikincil: RPS − `ceiling_hazard_v0`, k = 10 Brier (KM ve v0'a karşı), (c) için − `v1_pooled@INF`. **Canlı (iii):** SPEC_SCORING kalıbı, birincil RPS − `base_km_expanding`.
7. **Beklenti (kasa; fark, negatif = model iyi):** v0 − KM +0.08 [+0.02, +0.14]; clip − KM +0.035 [−0.02, +0.09], clip − v0 −0.04 [−0.07, −0.015]; real − KM −0.005 [−0.06, +0.05], real − v0 −0.08 [−0.13, −0.03]; pooled − KM **−0.03 [−0.07, +0.01]**, pooled − v0 −0.10 [−0.15, −0.05]. Yakın dönem v1 − v0: clip −0.003 [−0.010, +0.005]; real −0.004 [−0.015, +0.008]; pooled +0.002 [−0.010, +0.015] ("belirsiz" ya da "tolerans içinde"; "bozuyor" beklenmiyor). Tam tablo §6.
8. **Kasa planı [KARAR]:** yeni kimliklerin 135 üyelik kayıtları (üye başına yalnız yeni modelleri içeren ikinci kayıt) kasa açılmadan önce commit + push; açık kümedeki satırlar sınıf formülüyle **OOT_RETRO** (model commit'i S5 ingest commit'i `77b54f7`'nin atası değil); kasa, "düşenler" (C) özellik şartnamesi de push edildikten sonra **birlikte, tek seferde** açılır (kabul; gerekçe ve reddedilen alternatifler §7.4). Açılışta 19 eski model `oot_pre_h99_sealed` anahtarıyla da skorlanır.
9. **Uygulama seçim kuralı (önceden yazılı) [KARAR]:** kasa sonucundan sonra uygulamanın tavan sütununda birincil model, kasada KM'ye karşı "geçiyor", v0'a karşı aralığı 0'ın altında ve yakın dönemde "bozuyor" olmayan adaylar arasından kasa RPS noktası en düşük olandır; aday yoksa v0 kalır. Üç aday da sonuç ne olursa olsun dondurulur ve canlıda skorlanır.
10. Kapsam dışı: `pb_ceiling_v1` ve tavan yolu türevleri bu üç adayın **dışındadır** (§2.4); `post_d1_hazard_v1` ayrı şartname (§2.5). Uygulama etkisi: `data/training_table_v2.csv` (yeni), `borsai/tufe.py` (yeni), INDEX'e 4 giriş, altın MANIFEST yeniden üretimi (§8).

---

## 1. Tanı [KEŞİF] — v0'ın açık kümedeki hatası nereden geliyor?

Kaynak: `ekler/tani_v1.py` (yalnız okur; S2 kayıtlarındaki donmuş v0 tahminleri, kayıttaki donmuş KM karşılaştırıcısı, açık küme sonuçları, H99 tablosu, yayımlı ledger'lar; hiçbir üye kodu basılmaz) → `ekler/tani_v1_cikti.txt`. Bu bölümdeki her sayı **keşif**tir: önceden ilan edilmedi, sonuç görüldükten sonra hesaplandı, hüküm değildir; yalnız v1 tasarımının gerekçesidir.

### 1.1 Girdi aralığı (ekstrapolasyon hipotezi)

[ÖLÇTÜM `tani_v1_cikti.txt` §1] f1 = ln(nominal TL büyüklük). H99 eğitimi (97): medyan 21.06 (1 402 mn TL), p05 20.07 (521 mn), min 19.49 (291 mn). Açık küme (68 skorlanan): medyan 19.77 (386 mn); 2021 medyanı 19.28 (237 mn), 2022 19.38 (262 mn), 2023 20.59 (872 mn).

| | f1 < H99 min | f1 < H99 p05 | medyan z_f1 | min z_f1 |
|---|---|---|---|---|
| açık 68 | 28 | 40 | −1.97 | −4.86 |
| 2021 (26) | 15 | 20 | −2.66 | −4.24 |
| 2022 (20) | 10 | 15 | −2.52 | −3.49 |
| 2023 (21) | 2 | 4 | −0.83 | −3.82 |

Kayıttaki uyarılar: `OUT_OF_TRAINING_RANGE` f1 28, f3 10, f2 2; f3 kırpma 19 (p05 altı 3, p95 üstü 16). f2 aralık dışı yalnız 7 arzda p95 üstü. Ham f3 açık kümede belirgin yüksek (ort. 7.6, H99 3.7; 2021 ort. 8.1) — v0 f3'ü zaten kırpar; v1 bunu değiştirmez.

### 1.2 Doğrusal öngörücünün payları

[ÖLÇTÜM §2] β·z ortalaması (hazard logit'i; negatif = seri uzar): açık 68: f1 −0.852, f2 −0.083, f3 −0.292, toplam −1.227; 2021: −1.117 / −0.104 / −0.369; 2022: −1.051 / −0.085 / −0.069; 2023: −0.271 / −0.064 / −0.361. H99'da tanım gereği 0. **f1 payı tek başına 2021–2022'de hazard'ı e^−1.1 ≈ üçte bire indiriyor** [ÇIKARIM].

### 1.3 Kalibrasyon kutuları

[ÖLÇTÜM §3] Ortalama S_k (v0 / donmuş H99 KM / gözlenen), RPS farkı v0 − KM:

| kutu | n | S_5 | S_10 | RPS v0 | RPS KM | fark |
|---|---|---|---|---|---|---|
| z_f1 < −2 | 33 | 0.82 / 0.41 / 0.55 | 0.63 / 0.14 / 0.09 | 0.297 | 0.188 | **+0.109** |
| −2 ≤ z_f1 < −1 | 13 | 0.60 / 0.41 / 0.31 | 0.32 / 0.14 / 0.15 | 0.247 | 0.204 | +0.044 |
| −1 ≤ z_f1 < 0 | 13 | 0.53 / 0.41 / 0.38 | 0.26 / 0.14 / 0.00 | 0.190 | 0.176 | +0.014 |
| z_f1 ≥ 0 | 9 | 0.37 / 0.41 / 1.00 | 0.11 / 0.14 / 0.44 | 0.311 | 0.275 | +0.037 |
| 2021 | 26 | 0.74 / 0.41 / 0.42 | 0.53 / 0.14 / 0.04 | 0.326 | 0.178 | +0.148 |
| 2022 | 20 | 0.68 / 0.41 / 0.30 | 0.43 / 0.14 / 0.05 | 0.270 | 0.179 | +0.091 |
| 2023 | 21 | 0.54 / 0.41 / 0.86 | 0.29 / 0.14 / 0.33 | 0.206 | 0.242 | −0.037 |
| PRE_20211111 | 22 | 0.76 / 0.41 / 0.41 | 0.55 / 0.14 / 0.05 | 0.332 | 0.183 | +0.149 |
| THRESH100_20211111 | 31 | 0.71 / 0.41 / 0.48 | 0.47 / 0.14 / 0.10 | 0.233 | 0.203 | +0.030 |
| EQUAL_DIST_20230330 | 15 | 0.44 / 0.41 / 0.80 | 0.17 / 0.14 / 0.33 | 0.251 | 0.219 | +0.032 |

Yıl × f1 çaprazı (§3.7): 2021'de z_f1 < −1 olan 22 arzda fark +0.165 (2/20 kazanç); 2023'te z_f1 < −1 olan 5 arzda −0.229 (5/0). Yani düşük f1 **tek başına** hata kaynağı değil; 2021–2022 döneminde düşük f1'in anlamı farklı [ÇIKARIM].

### 1.4 Dönem başına Kaplan–Meier

[ÖLÇTÜM §4] S_1 / S_5 / S_10 / ort. L: açık 2021 0.77 / 0.42 / 0.04 / 3.4; 2022 0.85 / 0.30 / 0.05 / 3.3; 2023 1.00 / 0.86 / 0.33 / 7.2; H99 2023Q4 0.95 / 0.58 / 0.26 / 5.9; 2024 0.82 / 0.45 / 0.12 / 4.3; 2025 0.67 / 0.17 / 0.11 / 2.5; 2026 0.83 / 0.41 / 0.10 / 4.3. Donmuş H99 KM: 0.818 / 0.414 / 0.141. 2021–2022 kohortu S_10'da H99'un üçte biri; 2023 (her iki kaynakta) iki katı. H99'un kendi içinde de 2025 belirgin kısa.

### 1.5 Donmuş v0'ın girdi kırpma duyarlılığı (aday fit değil)

[ÖLÇTÜM §6] Parametreler değişmeden, yalnız z_f1 (ve z_f2) H99 [p05, p95] z-sınırlarına ([−1.55, +1.61]; [−1.95, +1.67]) kırpılınca RPS:

| küme | v0 | f1 kırpılı | f1+f2 kırpılı | f1 = eğitim ort. | KM |
|---|---|---|---|---|---|
| açık 68 | 0.269 | 0.233 | 0.231 | 0.189 | 0.200 |
| 2021 | 0.326 | 0.272 | 0.269 | 0.207 | 0.178 |
| 2022 | 0.270 | 0.215 | 0.214 | 0.154 | 0.179 |
| 2023 | 0.206 | 0.208 | 0.208 | 0.203 | 0.242 |

Okuma [ÇIKARIM]: kırpma açık kümede farkın yarısını kapatır (+0.069 → ≈ +0.031) ama 2021'de KM'yi hâlâ yenemez; f1'i tamamen etkisizleştirmek (z = 0) toplamda KM'yi geçer, 2021'de yine geçemez. Kalan pay dönemsel taban oranı farkıdır: ancak dönem bilgisi taşıyan eğitim ve rejim terimi kapatabilir → (c). Bu tablo (a)'nın prospektif skoru değildir: (a) yeniden fit eder ve kırpmayı eğitimde de uygular; sayılar yalnız mekanizmanın büyüklüğünü gösterir.

### 1.6 Tanı sonucu (bağlayıcı okuma)

- Hipotez "f1 nominal TL ekstrapolasyonu" **kısmen doğru**: hatanın ~yarısı.
- Kalan yarı **dönem etkisi**: 2020–2022 (özellikle eşit dağıtım öncesi) tavan serileri kısa; H99'un gün sabitleri bu döneme uymuyor.
- Buna göre v1 merdiveni: kırp (a) → reel büyüklük (b) → havuz + rejim (c). Her basamağın katkısı bir önceki basamağa karşı ikincil hücrede okunur (§5.4).

## 2. Aday model kimlikleri (3) [KARAR]

Ortak: `algorithm = discrete_time_hazard_logit_l2` (v0 ile aynı sınıf; §4), gün grupları g1 = {1}, g2 = {2, 3}, g3 = {4..10} aynen, pseudo-satırlar aynen (w = 0.5, z = 0, r = 0), λ ızgarası ve iç arz-bırak CV aynen, ret kuralları §9. Şartnamedeki herhangi bir şey değişirse yeni model_id (CLAUDE.md kural 5). Değişiklik olmayan her şey SPEC_CEILING_V0'dan **aynen** devralınır; aşağıda yalnız farklar.

| model_id | Eğitim kümesi | Özellikler (z-skor) | Kırpma [p05, p95] | Rejim terimi | Serbest parametre | Olay | Olay/param. |
|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | `H99_F3_PRESENT` (97; `training_table.csv`) | f1, f2, f3 | **f1, f2, f3** | yok | 3 β + 3 γ = 6 | 83 | 13.8 |
| `ceiling_hazard_v1_real` | `H99_F3_PRESENT` (97) | **f1r**, f2, f3 | f1r, f2, f3 | yok | 6 | 83 | 13.8 |
| `ceiling_hazard_v1_pooled` | `H99_F3_PRESENT ∪ OOT_OPEN_F3_PRESENT` (97 + 68 = 165; `training_table_v2.csv`) | f1r, f2, f3 | f1r, f2, f3 | **r** (cezasız δ) | 3 β + 3 γ + 1 δ = 7 | 142 | 20.3 |
| `ceiling_hazard_v1_pooled@INF` (kural satırı, aday değil) | aynı | yok | — | r | 3 γ + 1 δ (kapalı biçim) | 142 | — |

[ÖLÇTÜM `tani_v1_cikti.txt` §5] Havuz: 880 kişi-dönem satırı, 142 olay, 738 sağ kalım; grup olay/risk g1 25/165, g2 31/258, g3 86/457 (her grupta ≥ 15 olay). Açık f3'lü 68: 374 satır, 59 olay.

### 2.1 Mekanizma gerekçeleri [ÇIKARIM]

- **(a) `v1_clip`:** v0'ın tek bilinen zayıflığı (SPEC_CEILING_V0 §4 "f1 nominal TL") ve §1.1'deki aralık dışı kütle. Kırpma, eğitim desteği dışında doğrusal ekstrapolasyonu durdurur; f3'e zaten uygulanan kuralın f1 ve f2'ye genişletilmesidir. Yeni bilgi eklemez; yalnız ekstrapolasyon hipotezini sınar. H99 içinde p05/p95 dışı satır ≤ %10 olduğundan yakın dönem etkisi küçüktür.
- **(b) `v1_real`:** mekanizma "büyük arz → satıcı arzı bol → seri kısa" arz büyüklüğünün **dönemin alım gücüne göre** anlamlıdır; nominal TL 2020–2026'da 8–10 kat değişti. Reel büyüklük (TÜFE ile) dönemler arası aynı ölçeğe getirir; H99'da da (2023-09 → 2026-08 arasında ≈ 3× enflasyon) f1'i sıkılaştırır. Kırpma korunur ki (b) − (a) farkı yalnız deflasyonu ölçsün.
- **(c) `v1_pooled`:** §1.4–1.5: dönem taban oranı farkı kovaryatla kapanmıyor. Havuzlanmış eğitim β'yı 165 arzla ve daha geniş f1r/f3 desteğiyle kestirir; rejim terimi 2020–2023-03 satırlarının düzey farkını γ'ya bulaştırmadan emer. Canlıda r = 0: bugünkü rejimin sabiti γ'dır (H99 + eşit dağıtım sonrası 15 açık üye). Rejim terimi ikili seçildi (PRE ve THRESH ayrı iki kukla değil): §1.3'te THRESH ≈ EQUAL (+0.030 / +0.032) ama PRE +0.149 — üç düzeyli terim 1 parametre daha ister ve THRESH ile EQUAL'ı ayırt edecek olay yoktur; ikili terim "eşit dağıtım öncesi/sonrası" kural değişikliğine (i-SPK.128.21, 30/03/2023: borsa dışında bireysele eşit dağıtım) karşılık gelir ve canlıda 0'dır. **Eğitim sırasında r = 1 satırlarının 2021-11-11 öncesi/sonrası ayrımı yapılmaz.**
- Merdiven iç içedir: (b) = (a) + f1r; (c) = (b) + havuz + r. Her basamak bir öncekiyle aynı fold'larda karşılaştırılır (§5.4).

### 2.2 Değerlendirilip elenen seçenekler [KARAR]

| Seçenek | Karar | Gerekçe |
|---|---|---|
| Nominal f1 ile havuzlanmış eğitim | ret | Nominal büyüklük 2020–2026'da zamanla karışır; rejim kuklası düzeyi emer ama β_f1 dönemler arası farklı şeyler öğrenir; yorumlanamaz |
| Üç düzeyli tahsis rejimi (PRE / THRESH / EQUAL) | ret | +1 parametre; THRESH ≈ EQUAL (§1.3); bütçe |
| Yıl kuklaları | ret | Canlıda tanımsız; rejim kuralı tarihli ve yazılıdır |
| Gün sabitlerini döneme göre ayırmak (γ × r) | ret | +3 parametre; r = 1 kümesinde g2 olayı 14 |
| f1 için eğitim [min, max] kırpması (p05/p95 yerine) | ret | f3 ile tek kural; p05/p95 Type-7 kodda var |
| USD / XU100 deflatörü | ret | §3.2 |
| Son N ayın arzlarına göreli büyüklük | ret | 2020 üyeleri için 2019 arzları gerekir (repoda yok); 2020'de yılda 8 arz → ince pencere; yeni kaynak |
| `pb_ceiling_v1`, tavan yolu v1 | dışarıda | §2.4 |

### 2.3 Kimlik ve JSON alanları

Her model JSON'u SPEC_CEILING_V0 §12 alanlarını taşır; ek alanlar: `family: "ceiling_hazard_v1"`, `variant ∈ {clip, real, pooled}`, `preprocessing.winsor` üç sütun için, `deflator` (yalnız real/pooled: `{series: "TUIK_TUFE_GENEL_2025_100", month_rule: "T_MONTH_MINUS_2", file, file_sha256, unit: "2025 TL"}`), `regime` (yalnız pooled: `{column: "r_pre_equal", definition: "1[ALLOC_REGIME != EQUAL_DIST_20230330]", delta, penalized: false, live_value: 0}`), `training.set`, `training.table`, `training.cohort_counts {H99, OOT_OPEN}`, `spec_sha256` (bu dosya). `feature_ranges` f1r için 2025 TL biriminde.

### 2.4 PB karşılığı ve tavan yolu türevleri: bu üçün DIŞINDA [KARAR]

- `pb_ceiling_v1` bu şartnamede **tanımlanmaz**. Gerekçe: aday bütçesi 3'tür ve hata f3'lü ailededir (`pb_ceiling_v0` açık kümede "ayırt edilemiyor"); PB aynası "aynı kod, farklı özellik listesi"dir ve hangi dönüşümün işe yaradığı kasa testinden sonra bilinecektir. **Maliyet açıkça:** kasa tek seferlik olduğundan sonradan yazılacak `pb_ceiling_v1` kasada test edilemez; yalnız canlı teraziyle ölçülür. Alternatif (proje sahibi kararı, §13-2): `pb_ceiling_v1 = pooled`'ın PB aynası (pb1r = ln(planlanan büyüklük / TÜFE_{m−2}), pb2; r aynen; 99 + 71 = 170 arz, 147 olay, 6 parametre) kasadan önce 4. kimlik olarak dondurulur.
- Tavan yolu türevleri (`ceiling_path_v1*`): sıfır parametreli eşleme, dondurulmuş bir S JSON'unu ister (SPEC_CEILING_PATH_V0 §1); hangi v1'in S'i kullanılacağı seçim kuralından (§5.5) sonra bellidir. Bu şartnamenin dışında; ayrı, kısa şartname. Kasa testinde yer almaz (path'in birincil hücresi D5 MAE açık kümede "ayırt edilemiyor"; aciliyet yok).

### 2.5 `post_d1_hazard_v1` (yalnız not; bu şartnamenin dışında)

`post_d1_hazard_v0`, `ceiling_hazard_v0`'ın doğrusal öngörücüsünü sabit ofset alır ve δ (2) o ofsetin artığı üzerinde öğrenilmiştir; ebeveyn sha JSON'da pinlidir. Ebeveyn değişirse: yeni kimlik `post_d1_hazard_v1`, `parent_model_id` = seçim kuralıyla belirlenen v1, eğitim kümesi ebeveynin eğitim tablosunun L ≥ 1 alt kümesi (pooled ebeveynde 165 → ~143 arz), ofset ebeveynin f1r/r'li öngörücüsü, λ = INF ucu yine ebeveynin koşulluluğu. Kasa/canlı testleri SPEC_POST_D1_V0 §4 kalıbı. Ebeveyn v0 kalırsa hiçbir şey gerekmez.

## 3. Özellik ve veri tanımları

### 3.1 Kırpma (üç aday)

Eğitim kümesinden Type-7 doğrusal p05/p95 (kesin Fraction; `preprocess.quantile_type7`), **ham** değer üzerinde (f1/f1r için log ÖNCESİ TL değeri; z_vector'ün winsor → log sırası aynen), tahminde aynı sınırlarla kırpma. `Recipe` yeni alan `winsor: tuple[str, ...]` alır: CEILING_V1_CLIP = ("f1", "f2", "f3"), CEILING_V1_REAL = ("f1r", "f2", "f3"). Tahmin çıktısı: `clipped = True` herhangi bir sütun kırpıldıysa; `clipped_features: [...]`; uyarı kodu **`FEATURE_CLIPPED_TO_TRAINING_P05_P95`** (`feature`, `value`, `used`). v0'ın `F3_CLIPPED_TO_TRAINING_P05_P95` kodu v0'da aynen kalır.

### 3.2 f1r: reel arz büyüklüğü [KARAR]

```
size_TL       = ipo_size_tl (kaynakta bildirilmişse) ya da ipo_price_tl × shares_offered   # f1 ile TEK tanım (borsai.features)
m             = T'nin (ilk işlem günü, kayıttaki/tablodaki first_trading_date) yılı-ayı
tufe_month    = m − 2 ay                                                                     # ör. T = 2026-09-25 → 2026-07; T = 2026-10-01 → 2026-08
f1r_raw       = size_TL / (TUFE[tufe_month] / 100)                                            # birim: 2025 ortalama fiyatlarıyla TL
f1r           = ln(f1r_raw)   (ön işlemede, winsor'dan sonra; f1 ile aynı yol)
```

- **Seri:** TÜİK "Tüketici Fiyat Endeksi", genel endeks, aylık, **2025=100** (2026'da 2003=100'den taşındı; TÜİK'in zincirlenmiş uzun serisi, 1982'den itibaren). Resmi sayfa ve metaveri: `ekler/kaynak_kontrol_20260925.md` §1 (Ağustos 2026 bülteni 03 Eylül 2026 10:00; sıradaki 05 Ekim 2026; "veride revizyon uygulanmamaktadır"; yıllık yayım takvimi web sitesinde). Veri bu görevde indirilmedi; Opus indirir: `data/raw/tuik/tufe_genel_2025_100.csv` (sütunlar `month, index, release_date, bulletin_id, source_url, source_sha256`; kapsam 2019-11 … güncel; TÜİK veri portalındaki "Tüketici fiyat endeksi ve değişim oranları" tablosu; indirilen dosya sha256 ile pinlenir; PROVENANCE'a satır). Ay eklemek veri sürümünü değiştirmez (yalnız ek satır; eski satırlar bayt-eşit kalmalı, test); **temel yıl, zincirleme ya da bir eski satırın değişmesi = yeni veri sürümü = yeni model_id.**
- **Point-in-time:** ay m'nin endeksi m+1'in 3. günü (hafta sonuysa ilk iş günü) 10:00'da yayımlanır → m−2'nin endeksi en geç m−1'in ~5'inde yayımlanmıştır, T ise m ayındadır: **her T için yayımlanmış** (T ayın 1'i olsa bile). Kayıtta `tufe: {month, index, release_date, file_sha256, rule: "T_MONTH_MINUS_2"}` bloğu; `inputs_pit_ok` denetimi `release_date < T`'yi de sınar (bekçi). Deterministik gecikme (1–2 ay) log ölçeğinde önemsizdir (aylık enflasyon %2–5 → ≤ 0.10, σ_f1 = 0.71).
- **Backtest:** eğitim arzı j için kendi T_j'sinin m_j−2 endeksi (T_j < T_k olduğundan T_k'dan önce yayımlanmıştır; sızıntı yok). Fold içinde f1r ham değerleri değişmez; yalnız winsor/μ/σ fold'dan öğrenilir.
- **Reddedilen deflatörler [KARAR]:** USD/TRY (TCMB gösterge kur; `kurlar` XML arşivi 2020-01-02'den itibaren doğrulandı): kademeli devalüasyonlar (2021-12, 2023-06) yurtiçi alım gücünden bağımsız sıçramalar yapar, komşu haftalarda aynı arz farklı f1r alır; XU100 düzeyi (repoda, S0 kapanışı): hisse piyasası döngüsünü büyüklüğe karıştırır (2023 boğa dönemi arzları "küçük", 2025 düşüşü "büyük" görünür). TÜFE: hanehalkı alım gücü, aylık, pürüzsüz, revizyonsuz, resmi.
- **Bilinen sınır:** deflasyon medyanları hizalar (§1.1'de H99/2021 medyan oranı 5.9×; TÜFE'nin 2021 ortası → 2025 ortası oranı aynı mertebededir; kesin değer uygulamada ölçülür ve raporlanır) ama 2021–2022'nin kısa serilerini açıklamaz (§1.5). Bunun için (c).

### 3.3 Rejim terimi r (yalnız pooled) [KARAR]

`r = 1[alloc_regime(T) ∈ {PRE_20211111, THRESH100_20211111}]`, `alloc_regime` **tek tanım** `borsai.registry.ALLOC_REGIMES`'ten tarihle hesaplanır (`registry.alloc_regime(first_trading_date)` yardımcı fonksiyonu; elle etiket yok). Kohort dosyasındaki `ALLOC_REGIME` etiketiyle eşitliği test edilir (135/135). z-skorlanmaz; tasarım matrisinde γ bloğu gibi **cezasız** sütun. Canlıda ve H99 fold'larında T ≥ 2023-09-22 > 2023-03-30 → r = 0 (kodda assert). Eski kohort kayıtlarında (135 üye; kasa dahil) r kohort satırından. λ = INF: β ≡ 0, (γ, δ) pseudo-satırlı MLE'nin kendisi (Newton, 4 boyut; kapalı biçim yok — SPEC_CEILING_V0 §5'in "λ = INF: γ kapalı biçim" cümlesi bu modelde "λ = INF: β ≡ 0, (γ, δ) Newton" olur; @INF kuralı böyle üretilir).

### 3.4 Eğitim tablosu v2

`data/training_table_v2.csv` + `data/data_version_v2.json` (yeni; `training_table.csv` ve `data_version.json` **dokunulmaz**, bayt-eşit kalır — test). Satırlar: H99'un 99 satırı (değerler `training_table.csv`'den bayt-eşit kopya) + açık kümenin 71 üyesi (girdiler `registry/oot/inputs/<T>.json`'dan `registry.model_inputs` ile; sonuçlar `data/outcomes_oot/<T>.csv`'den SPEC_SCORING §3 tanımlarıyla; `borsai.outcomes_oot` kodu). Sıra (first_trading_date, ticker). Ek sütunlar: `cohort ∈ {H99, OOT_OPEN}`, `alloc_regime` (§3.3), `tufe_month`, `tufe_index` (izlenebilirlik; yüklemede `borsai.tufe` aramasıyla eşitlik assert), `sale_method`, `market`. Seans tarihleri: H99 için SESSIONS dosyası, açık üyeler için `data/outcomes_oot/<T>.csv` `session_date`. **Kasa üyesi hiçbir satır yoktur** (`test_cohort_codes_appear_in_data_only_as_outcomes` ve kasa bekçisi bu dosyayı da tarar). Builder `data/build_training_table_v2.py`; `data/build_training_table.py` dokunulmaz.

## 4. Model, amaç, çözücü, ızgara

SPEC_CEILING_V0 §5 aynen; tek fark tasarım matrisinde cezasız sütun kümesi: X = [G (3 gün grubu) | R (0 ya da 1 sütun, cezasız) | Z (β, ceza λ)]. `hazard.fit_rows` `unpenalized_cols` argümanı alır; `pen` vektörü buna göre. Newton başlangıcı: γ kapalı biçim (grup olay/risk), δ = 0, β = 0. Iç CV: arz-bırak; ön işleme (winsor, μ, σ) kalanlardan; r arz sabiti olduğundan yeniden kurulmaz. Yakınsamama kuralları aynen. `pb`/`v0` kodu bayt düzeyinde aynı çıktıyı vermeye devam eder (altın ledger'lar `976b4dcea981`, `90b610463de4` bayt-eşit — kabul testi 10).

Bütçe [ÖLÇTÜM §2 tablosu]: (a), (b) 13.8; (c) 20.3 olay/parametre. Walk-forward test kümesinde azınlıklar: H99 L < 1: 16, L ≥ 10: 11 (v0'dan; 87 fold); yakın dönem 78 fold'da olay 69.

## 5. Önceden yazılmış testler ve birincil hücreler [KARAR]

Her hücre: eşleşik fark (model − karşılaştırılan; negatif = model iyi), ay-blok bootstrap (blok = ilk işlem ayı; B = 4000; SPEC_SCORING §8 üretici/tohum; SPEC_DEVIATIONS C7 backtest'te), n ve kazanç/kayıp/eşit. Dil SPEC_SCORING §8: "geçiyor" yalnız n ≥ 30 ve aralık 0'ı dışlarsa. Üç terazi toplanmaz; zaman-dışı hükmü daima "(zaman-dışı terazide)" ekiyle.

### 5.1 (i) Yakın dönem testi — H99 walk-forward

- Planlar: `v1_clip`, `v1_real` → PLAN_CEILING aynen (kesim T, f3 dolu, ≥ 10 arz / 5 olay / 5 sağ kalım; 87 fold, v0 ile aynı ticker kümesi — test). `v1_pooled` → yeni plan `H99_PLUS_OOT_OPEN_CEILING_PP_WALK_FORWARD_T_CUTOFF_F3_PRESENT_MIN10IPO_5EV_5SV`: test arzları yine H99'un f3'lü 97'si; eğitim = `training_table_v2`'de seans tarihi < T olan bütün kişi-dönem satırları (açık üyelerin son seansı ≤ 2023-10-04 < ilk H99 fold'u 2023-11-21 → daima tam girer). Skorlanabilir fold sayısı 97'ye çıkar (beklenen; ölçülmedi); 87'nin tamamı dahildir (test).
- **Birincil hücre (her aday için bir tane):** `v1 − ceiling_hazard_v0`, RPS, **ilk işlem ≥ 2024-01-01 olan fold'lar** (78 fold, 22 ay bloğu [ÖLÇTÜM §7]); v0 değerleri altın ledger `tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv` (sha `976b4dcea981…`) satırlarından, fold ticker'ıyla eşleştirilerek (yeniden koşulmaz; ledger sha pinlenir).
- **Karar kuralı (önceden):** d = ortalama fark, [alt, üst] = %95 aralık.
  - alt > 0 → **"bozuyor"** (v1 yakın dönemde v0'dan kötü).
  - üst ≤ **+0.010** → **"tolerans içinde"** (eski veri / dönüşüm yakın dönemi bozmuyor).
  - diğer → **"belirsiz"**.
  - δ = 0.010 gerekçesi [ÖLÇTÜM §7]: v0'ın yakın dönemde KM'ye karşı kazancı yıl başına −0.035 … −0.077 (78 fold'da ≈ −0.056); δ bunun beşte biridir; fold başına v0 − KM farkının sd'si 0.12 → eşleşik v1 − v0 farkının SE'si ≈ 0.005–0.01, aralık genişliği δ'yı çözebilir.
- **Proje sahibinin sorusu** ("eski arzları eğitime katmak bugünkü tahminleri bozmaz mı?") tam olarak `v1_pooled`'ın bu hücresiyle cevaplanır: "bozuyor" / "tolerans içinde" / "belirsiz" sözcükleriyle. `v1_clip` ve `v1_real` hücreleri "dönüşüm yakın dönemi bozuyor mu" sorusunun cevabıdır.
- İkincil (ilan edilmiş): aynı 78 fold'da v1 − `base_km_expanding` (v0 planının KM ledger'ı), v1 − `ceiling_hazard_v0@INF`; k ∈ {1, 3, 5, 10} Brier; 2023 fold'ları (v0'da 9; pooled'da 19) **keşif**. Pooled planında KM kuralları havuzdan hesaplanır (`base_km_expanding__pooled`, `base_km_last10__pooled`) ve ayrı ledger satırı olur; keşif.
- **H99 tasarıma maruzdur:** v0'ın gün grupları H99 marjinallerine bakılarak seçildi (SPEC_CEILING_V0 §3); v1 bunları devralır; v0'ın H99 backtest sonucu yayımlıdır (MODELS.md) ve bu şartname yazılırken biliniyordu (§10). Kanıt değeri prospektif teraziden düşüktür.

### 5.2 (ii) Kasa testi — 64 arz, tek seferlik

Skorlama `python -m borsai.scoring --oot` `oot_pre_h99_sealed` anahtarıyla; sınıf `class_oot` formülüyle (§7.2); beklenen n: f3'lü kasa üyeleri ≈ 60 (kasada borsada satış 22 üye; açık kümede 27'sinden 3'ü f3'süzdü).

| Aday | **Birincil** | İlan edilmiş ikincil |
|---|---|---|
| `v1_clip` | RPS − `base_km_expanding` (kayıttaki donmuş H99 KM) | RPS − `ceiling_hazard_v0` (kasa S2 kaydı); Brier k = 10 − KM ve − v0; RPS − `ceiling_hazard_v0@INF` |
| `v1_real` | aynı | aynı + RPS − `v1_clip` (merdiven basamağı) |
| `v1_pooled` | aynı | aynı + RPS − `v1_real`, RPS − `v1_pooled@INF` (özelliklerin payı), Brier k = 10 − `v1_pooled@INF` |

Yıl ve rejim kırılımları (her biri n < 30) "yetersiz örnek" etiketiyle; diğer hücreler keşif. Kalibrasyon satırı: ort. S_5 ve S_10 ile gözlenen (bilgi; hüküm yok — proje sahibinin Faz 6 kararıyla uyumlu: kalibrasyon satırı yok ise yalnız raporda).

### 5.3 (iii) Canlı

SPEC_SCORING §5–§8 aynen. Birincil: RPS − `base_km_expanding` (kayıttaki kural değeri). İkincil: RPS − `ceiling_hazard_v0` (aynı kayıt; iki model de f3 ister → aynı ret kümesi), Brier k = 10. Sayaçlar `n_scored / n_refused / n_skipped / n_target_unavailable`, `n_live / n_late`. Birincil kayıt kuralı f3 isteyen modellerinki (D_1'den önce push kanıtlı **en son** kayıt). Hüküm n ≥ 30'da; 10 ≤ n < 30 "yetersiz örnek"; n < 10 satır tablosu.

### 5.4 Merdiven karşılaştırmaları (ikincil; üç terazide de aynı fold/arzlar)

`v1_clip − v0` (kırpmanın payı), `v1_real − v1_clip` (deflasyonun payı), `v1_pooled − v1_real` (havuz + rejimin payı). Yalnız bilgi; hüküm dili kullanılmaz ("… payı: fark [aralık]").

### 5.5 Uygulama birincil model seçim kuralı (önceden yazılı) [KARAR]

Kasa skorları yayımlandıktan sonra, tek seferde:
1. Aday **uygun** sayılır ancak: (k1) kasa birincil hücresi "geçiyor (zaman-dışı terazide)" (aralık tamamen 0'ın altında) VE (k2) kasada RPS − v0 aralığının üst ucu < 0 VE (k3) yakın dönem hücresi "bozuyor" değil.
2. Uygun adaylar arasında kasa RPS noktası en düşük olan uygulamanın tavan sütununda **birincil** olur; |Δ| < 0.002 eşitliğinde en basit (clip < real < pooled).
3. Uygun aday yoksa `ceiling_hazard_v0` birincil kalır.
4. Sonuç ne olursa olsun üç aday dondurulmuş kalır, canlıda skorlanır, MODELS.md'de listelenir; uygulama diğerlerini ikincil satırda gösterir. Bu kural kasa açılmadan önce push edilmiş olduğundan seçimin kendisi sonuca bakılarak değiştirilemez; kuralın değişmesi bu belgeyi değiştirir (yeni sürüm, gerekçeyle).

## 6. ÖNCEDEN YAZILMIŞ BEKLENTİ (SPEC_CEILING_PATH_V0 §6 kalıbı)

Bu bölüm 2026-09-25'te, bu modeller için hiçbir kod ve skor yokken yazıldı; sonradan değiştirilmez. **Beyan:** yazar açık kümenin 71 arzının zaman-dışı skorlarını (S6) ve §1'deki tanıyı görmüştür; kasa üyeleri açık kümeyle aynı yıl tabakalı çekilişten geldiği için (kasa: 2020: 4, 2021: 26, 2022: 18, 2023: 16; tahsis PRE 29 / THRESH 23 / EQUAL 12 [ÖLÇTÜM kohort dosyası, kod yok]) açık küme sayıları kasa beklentisinin temelidir; kasa açık kümeden biraz daha "eski" (PRE 29/64'e karşı 25/71). Aralıklar bu bilgiyle yazılmış, geniş tutulmuştur. Birim: RPS ve Brier farkı ham (kesir); negatif = model iyi.

### 6.1 Kasa (n ≈ 60; hüküm dili yalnız aralıkla)

| Hücre | Beklenen fark | Aralık | Aralık 0'ı | Gerekçe (kısa) |
|---|---|---|---|---|
| `ceiling_hazard_v0` − KM (kasada; açılışla gelir) | +0.08 | [+0.02, +0.14] | pozitif dışlaması olası | açık küme +0.069 [+0.001, +0.131]; kasada PRE payı yüksek |
| `v1_clip` − KM **(birincil)** | +0.035 | [−0.02, +0.09] | içerir | §1.5: kırpma farkın yarısını kapatır; refit β'yı az değiştirir |
| `v1_clip` − v0 | −0.04 | [−0.07, −0.015] | negatif dışlaması olası | eşleşik; 2021–2022 üyelerinde tutarlı kazanç |
| `v1_clip` Brier k=10 − KM | +0.10 | [+0.04, +0.16] | pozitif dışlar | S_10 hâlâ 0.3+ |
| `v1_real` − KM **(birincil)** | −0.005 | [−0.06, +0.05] | içerir | §1.5 "f1 = eğitim ort." sütunu 0.189 vs KM 0.200; deflasyon medyanları hizalar ama dağılım genişliği kalır |
| `v1_real` − v0 | −0.08 | [−0.13, −0.03] | negatif dışlaması olası | |
| `v1_real` − `v1_clip` | −0.04 | [−0.08, 0.00] | büyük olasılıkla içerir | deflasyonun payı |
| `v1_real` Brier k=10 − KM | +0.04 | [−0.01, +0.09] | içerir | |
| `v1_pooled` − KM **(birincil)** | **−0.03** | **[−0.07, +0.01]** | **büyük olasılıkla içerir** | rejim terimi 2020–2023-03 üyelerinde S'i kısaltır; özelliklerin ayrım payı v0'ın H99'daki −0.05'inin altında kalır |
| `v1_pooled` − v0 | −0.10 | [−0.15, −0.05] | negatif dışlar | |
| `v1_pooled` − `v1_real` | −0.03 | [−0.06, 0.00] | sınırda | havuz + rejimin payı |
| `v1_pooled` − `v1_pooled@INF` | −0.01 | [−0.04, +0.02] | içerir | 2021–2022 üyelerinde özellik ayrımı zayıf (§1.3: z_f1 < −2 kutusunda KM bile 0.188) |
| `v1_pooled` Brier k=10 − KM | 0.00 | [−0.03, +0.04] | içerir | |
| Kalibrasyon (bilgi) | pooled ort. S_5 − gözlenen | [−0.10, +0.10] | — | |

Hangi hücrede kazanç en olası: `v1_pooled − v0` ve `v1_real − v0` (eşleşik, büyük etki). En az olası: herhangi bir adayın KM'ye karşı "geçiyor" demesi (kasa 2021–2022 ağırlıklı; KM o dönemde güçlü).

### 6.2 Yakın dönem (78 fold; v1 − v0 RPS)

| Aday | Beklenen | Aralık | Beklenen etiket | Gerekçe |
|---|---|---|---|---|
| `v1_clip` | −0.003 | [−0.010, +0.005] | tolerans içinde | H99'da kırpılan satır ≤ %10; fold'larda çoğunlukla bit-yakın |
| `v1_real` | −0.004 | [−0.015, +0.008] | tolerans içinde ya da belirsiz | H99 içinde ≈ 3× enflasyon; f1r daha keskin ya da daha gürültülü; yön belirsiz |
| `v1_pooled` | +0.002 | [−0.010, +0.015] | **belirsiz** olası; "bozuyor" beklenmiyor | 68 eski arz β'yı çeker; γ bugünkü rejimden; iki etki zıt |
| `v1_pooled` − KM (ikincil) | −0.05 | [−0.08, −0.02] | — | v0'ın kazancı korunur |

### 6.3 Canlı (ilk n ≥ 30; ≈ 10–12 ay)

Her aday için v1 − v0: −0.005 [−0.02, +0.01] (ayırt edilemiyor); v1 − KM: −0.04 [−0.08, 0.00]. Canlı rejim EQUAL_DIST (r = 0) ve arzlar eğitim aralığında olduğundan üç adayın v0'dan canlıda ayrılması ilk 30 arzda beklenmez; canlı terazi bu ailede v0'a karşı **düşük çözünürlüklüdür**, asıl ayrım kasadadır.

### 6.4 Başarısızlık tanımları (aynı sözcüklerle)

- (a) **"v0'dan kötü":** kasada RPS − v0 aralığı tamamen 0'ın üstünde → aday listede kalır, kartı bunu yazar, uygulama birincili olamaz.
- (b) **"bozuyor":** yakın dönem hücresi alt > 0 → proje sahibine cevap "evet, bozuyor"; aday yine dondurulur, kural k3 ile birincil olamaz.
- (c) **"özellikler bilgi eklemiyor" (pooled):** kasada `v1_pooled − v1_pooled@INF` noktası ≥ 0 → kart bunu yazar.
- (d) **Kalibrasyon:** kasada |ort. S_5 − gözlenen P(L ≥ 5)| > 0.15 → "düzey kayması" notu.
- (e) **Beklentiden çok iyi:** kasa birincilinde fark < −0.10 ya da aralığın üst ucu < −0.06 → Fable'ın sıfırdan yeniden üretimi zaten dondurmadan önce yapılmıştır (yol adım 3); ek olarak kasa skorunun bağımsız yeniden hesabı (S6 denetimi kalıbı) uygulama birincili değişmeden önce zorunludur.
- Ara durum (aralık 0'ı içeriyor): "ayırt edilemiyor". **Her durumda üç aday bu şartnameyle dondurulur**; sonuca bakıp özellik/eşik/rejim tanımı değiştirmek = yeni model_id + günlük satırı.

## 7. Kasa planı [KARAR]

### 7.1 Sıra

1. Şartname (bu belge) commit + push (proje sahibi) + push kanıtı.
2. Opus A (kod, tablo v2, TÜFE dosyası, kurallar) → B (backtest, yakın dönem hücreleri, günlük) → Fable yeniden üretim (ledger'lar |Δ| ≤ 1e-9) → dondurma (INDEX'e 4 giriş) → push + kanıt.
3. **Eski kohort kayıtları (135 üye):** `python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv --only-missing-models`: üye başına **ikinci kayıt**, yalnız o üyenin hiçbir aktif kaydında bulunmayan INDEX modellerini içerir (`record_stage = OOT_PRE_LISTING`, `models_index` = yeni INDEX sha, `delta_of: <ilk kayıt dosya adı>`); girdiler ve `model_inputs` ilk kayıtla bayt-eşit (test), ek olarak `tufe` bloğu ve `alloc_regime`. Kasa üyeleri için yalnız listeleme öncesi girdiler okunur (S2'deki gibi); sonuç yok. Tek commit; push; kanıt. **Bu commit kasa sonuçlarından önce gelir ve kanıtı önce olmalıdır** (kapı, §7.3).
4. (C) "düşenler" özellik şartnamesi (ayrı görev) commit + push + kanıt.
5. **Kasa açılışı, tek seferde:** karantina zip'leri pinli sha ile yeniden indirilir; SEALED satırlar ayıklanır (`data/outcomes_oot/<T>.csv`, D6-4); tek commit; push; kanıt. Ardından `scoring --oot`: `oot_pre_h99_sealed` (19 eski + 3 yeni + 1 kural) ve `oot_pre_h99_all` (**yalnız** açık kümede OOT_BLIND olan 19 eski model; yeni modeller için "all" tanımsızdır çünkü açık satırları RETRO'dur — kod bunu birleştirmez, test).
6. Seçim kuralı (§5.5) uygulanır; MODELS.md ve uygulama güncellenir.

### 7.2 Açık küme satırları tanım gereği OOT_RETRO

`class_oot` (borsai/scoring.py, SPEC_OOT_PRE_H99_V0 §2 + KARARLAR D6-5):

```
blind = frozen_ok AND record_ok AND proof_ok AND cohort_gate_ok AND extra_ok
frozen_ok = commit_frozen(m) push kanıtlı VE is_ancestor(commit_frozen(m), oot_ingest_commit(a))
record_ok = is_ancestor(record_commit(m, a), oot_ingest_commit(a))
proof_ok  = push_proof(record_commit) < push_proof(oot_ingest_commit)
```

Açık üye a için `oot_ingest_commit(a)` = S5 commit'i **`77b54f7`** (2026-09-25; `data/outcomes_oot/<a>.csv`'yi ekleyen commit [ÖLÇTÜM `git log --diff-filter=A`]). Yeni bir v1 modelinin `commit_frozen` değeri bundan sonradır → `is_ancestor(commit_frozen, 77b54f7)` **yanlış** → `frozen_ok = False` → sınıf **OOT_RETRO**; `record_ok` de yanlıştır (kayıt commit'i de sonradır). Sonuç: v1 modelleri için 71 açık satır `retro_info` listesine düşer (`n_oot_retro = 71`, yalnız bilgi; hiçbir n'e girmez). Bu, formülün elle etiketsiz, tarihlerden hesabıyla uyumludur: açık küme v1 için eğitim (pooled) ya da tasarım kümesidir (clip, real), test değildir. Kasa üyesi s için `oot_ingest_commit(s)` adım 5'teki commit'tir; adım 2–3 ondan önce ve kanıtları önce olduğundan v1 satırları OOT_BLIND olur.

### 7.3 Kohort kapısının model başına genişletilmesi (kod notu)

Bugünkü `cohort_gate_ok`, kohortun her MEMBER'ının S2 kaydının ingest commit'inin atası olmasını ister. v1 için kapı **(model, üye)** başına olmalıdır: ingest anındaki INDEX'te bulunan her model m ve her MEMBER a için, m'yi içeren aktif bir kayıt ingest commit'inin atası ve kanıtı önce olmalı; yoksa kasa açılışı (indirme) başlamaz (`outcomes_oot.download_gate` de aynı kuralı çağırır). Birincil kayıt kuralı: **o modeli içeren en erken aktif kayıt** (SPEC_SCORING §6'nın "en erken kayıt" kuralıyla tutarlı; f3 isteyen modeller için canlıdaki "en son" kuralı eski kohortta anlamsızdır çünkü D_1 yıllar öncedir). SPEC_DEVIATIONS'a I-satırı.

### 7.4 Açılış zamanı: (C) ile birlikte — **KABUL**, gerekçesiyle

- Kasa, KARARLAR D2/D4 ve SPEC_OOT §9'a göre (C) sorusunun ("D1'de tavan yapmayan / arz altına düşen azınlığı ayıran listeleme öncesi özellik var mı?") doğrulama kümesi olarak çekildi; açılma koşulu (C) şartnamesinin push'udur. Kasayı yalnız v1 için şimdi açmak (C)'yi doğrulama kümesiz bırakır (canlı sicilde azınlık olayı ayda < 1; yıllar).
- **Reddedilen alternatif 1 — kasayı bölmek** (tohumlu ikinci çekilişle 32/32): v1 testi n ≈ 30'a düşer (hüküm eşiğinin tam sınırı; f3 retleriyle altına iner), (C) için azınlık olayı ≈ 6 → ikisi de hükümsüz.
- **Reddedilen alternatif 2 — önce v1, sonra (C) için yeni kasa**: yeni kasa ancak canlı sicilden kurulabilir (SPEC_OOT §9 son cümle); yıllar.
- **Kabul edilen: birlikte, tek seferde.** Maliyet: v1'in kasa hükmü (C) şartnamesinin yazılmasına kadar bekler. Bu bekleme v1'i durdurmaz: dondurma, canlı kayıtlar (adım 2'den itibaren her canlı kayıt v1'i içerir) ve yakın dönem testi hemen gerçekleşir; yalnız uygulama birincil seçimi (§5.5) kasayı bekler. Açılış ön koşulları: (i) v1 kayıtları (adım 3) push kanıtlı; (ii) (C) şartnamesi push kanıtlı; (iii) `oot_pre_h99_sealed`/`_all` kodu sentetik testte yeşil; (iv) model başına kapı (§7.3) yeşil.
- Kasa açılınca 19 eski modelin kasa sonuçları da `oot_pre_h99_sealed` ile çıkar; `oot_pre_h99_all` yalnız onlar için. Kasa sonuçları yayımlandıktan sonra SEALED küme, D4 gereği ancak doğrulaması yayımlanınca ve yalnız yeni kimliklerin (v2) eğitimine girebilir.

## 8. Uygulama (kısa)

| Parça | Değişiklik |
|---|---|
| `data/training_table_v2.csv`, `data/data_version_v2.json`, `data/build_training_table_v2.py` | §3.4; `training_table.csv` ve `data_version.json` bayt-eşit kalır (test) |
| `data/raw/tuik/tufe_genel_2025_100.csv` + PROVENANCE satırı | §3.2; sha pinli; ay ekleme = ek satır |
| `borsai/tufe.py` (yeni, stdlib) | `load()`, `month_for(T)`, `index_for(T)` → `{month, index, release_date, file_sha256}`; `release_date < T` bekçisi |
| `borsai/preprocess.py` | `Recipe.winsor` (varsayılan ("f3",) → v0/PB davranışı bayt-eşit); tarifler `CEILING_V1_CLIP`, `CEILING_V1_REAL` (f1r sütunu: ham = size/(index/100), log) |
| `borsai/hazard.py` | `fit_rows(..., unpenalized_cols)`; `TrainingResult` r'yi taşır; λ = INF'te (γ, δ) Newton |
| `borsai/specs.py` | `FAZ7_MODEL_IDS = (v1_clip, v1_real, v1_pooled, v1_pooled@INF)`; plan `PLAN_CEILING_POOLED`; `SPEC_DOCUMENTS_FAZ7` |
| `borsai/data.py` | `load_dataset_v2()` (aynı doğrulamalar + kohort sütunları + sessions iki kaynaktan) |
| `borsai/backtest.py` | pooled plan; v0 ledger'ından eşleşik yakın dönem hücresi; günlük satırı (`data_version_sha256` v2 için farklı → kart sayaçları ayrı) |
| `borsai/predict_hazard.py` | izinli özellik listeleri + `["f1r","f2","f3"]`; `regime` bloğu (canlıda `live_value`; OOT kayıtlarında `alloc_regime` girdisi); `tufe_index` girdisi; genel kırpma uyarısı (§3.1); v0/PB çıktıları bayt-eşit |
| `borsai/freeze.py` | `build_record`: `tufe` bloğu (market20 kalıbı) ve `model_inputs["tufe_index"]`, `["alloc_regime"]`; `--oot --only-missing-models` ikinci kayıt (§7.1-3) |
| `borsai/scoring.py` | model başına kohort kapısı (§7.3); "modeli içeren en erken aktif kayıt"; `oot_pre_h99_sealed` / `_all` (all yalnız BLIND açık satırı olan modeller); yakın dönem etiketleri ("bozuyor" / "tolerans içinde" / "belirsiz") `SCORES.md` backtest panelinde ayrı satır |
| `models/INDEX.json` | 4 giriş eklenir (sonuna); `INDEX_POST_D1.json` değişmez |
| Canlı kayıtlar | Dondurmadan sonraki her kayıt (kural 1) 4 yeni modeli otomatik içerir. Var olan 7 canlı kayıt (2026-08-18 … 09-17 arzları) v1'i içermez; bu arzlar v1 için formülle RETRO'dur (model commit'i sonuçlarından sonra) ve yalnız bilgi listesine düşer; v1 canlı n'i dondurma tarihinden sonra listelenen arzlarla başlar |
| `app/` | Rust `params.rs`/`hazard.rs`/`features.rs`: `f1r` (tufe girdisi), `regime` bloğu (r = live_value), genel kırpma bayrağı; `app/parity/gen_golden.py` `PINNED_MODEL_IDS` 19 → 23, `bit_equal_floor.json` 4 taban; **MANIFEST `predict_sources_sha256` değişir** (`predict_hazard.py`, `features.py`/`predict.py` değişirse) → altın vektörler yeniden üretilir, U46 için 16 eski dosya bayt-eşit kalır (yeni girdi satırları yalnız yeni modellere bağlanır; Faz 4 kalıbı); `gen_golden --check` adım 0'da yeşil olmalı (bilinen tuzak) |
| `docs/MODELS.md` | `report_faz7.py` (Faz 5 kalıbı); kartta yakın dönem etiketi ve "kasa: bekliyor" satırı |

## 9. Ret ve uyarılar

| Durum | Davranış (üç aday) |
|---|---|
| f3 boş | RET `REFUSED_F3_MISSING` (miras; PB aynası yok, §2.4) |
| f1/f2 hesaplanamıyor | etiketli RET (miras) |
| TÜFE ayı (m−2) dosyada yok (real, pooled) | RET `REFUSED_TUFE_MISSING:<YYYY-MM>`; dondurma/kayıt ön koşulu bunu önceden denetler (canlıda olmamalı) |
| TÜFE `release_date ≥ T` (real, pooled) | RET `REFUSED_TUFE_NOT_PIT` (bekçi; kural gereği olamaz) |
| TÜFE dosya sha JSON'dakiyle farklı | RET `REFUSED_TUFE_FILE_MISMATCH` (temel yıl/zincirleme değişimi; yeni veri sürümü gerekir) |
| Girdi p05 altı / p95 üstü (f1 ya da f1r, f2, f3) | kırpılır; `clipped = True`, `clipped_features`, uyarı `FEATURE_CLIPPED_TO_TRAINING_P05_P95` |
| Girdi eğitim min/max dışında | tahmin + `OUT_OF_TRAINING_RANGE` (kırpma sonrası da yazılır; bilgi) |
| Rejim (pooled): canlı | r = `live_value` (0); girdi istemez; kayıt `regime_value_used: 0` yazar |
| Rejim (pooled): eski kohort kaydı | r kohort satırından; `ALLOC_REGIME` etiketi yoksa RET `REFUSED_REGIME_UNKNOWN` |
| Eğitim tablosu v2'de kasa kodu | derleme/test hatası (bekçi), tahmin yolu değil |

Ret, kayıtta o model için "ret + neden"dir; arz sicilden düşmez (kural 2).

## 10. Maruziyet beyanı

1. **Açık küme sonuçları:** yazar S6 denetimini yaptı (`docs/fable_faz6_s6/AUDIT.md`), 71 açık arzın tahmin/sonuç çiftlerini gördü; §1'de bunlar üzerinde tanı hesapladı (kutu kalibrasyonu, dönem KM'si, donmuş v0 girdi kırpma duyarlılığı). Bu yüzden açık küme v1 için **test değildir**; havuzlanmış adayda eğitim, diğerlerinde tasarım kümesidir. Açık kümede hesaplanan her sayı "keşif" etiketlidir.
2. **Kasa:** hiçbir kasa üyesinin dosyası açılmadı; kasa hakkında yalnız kohort dosyasındaki vault/yıl/rejim sayımları kullanıldı (kod adı yazılmadı). `EXPOSURE.md` §3 okunmadı.
3. **H99:** v0'ın H99 backtest sonuçları yayımlıdır (RPS −0.050 [−0.072, −0.026] vs KM; MODELS.md) ve §5.1'in δ'sı bunlara bakılarak yazıldı; H99 tasarıma maruzdur (gün grupları). `experiments/log.jsonl` [ÖLÇTÜM]: 67 satır; tavan ailesinde H99'da denenmiş varyant: `ceiling_hazard_v0` (1 şartname, 2 koşu), `@INF`, `pb_ceiling_v0` (+@INF), `ceiling_path_v0` (+ @INF, PB, 5 duyarlılık), `post_d1_hazard_v0` (+ 2 duyarlılık). Hazard sınıfında **alternatif özellik/gruplama varyantı denenmemiştir**; v1 bu ailenin H99'daki ilk varyant kümesidir (3 + 1).
4. **Genel ön bilgi:** yazar 2020–2023 Türkiye halka arz dalgası hakkında genel bir izlenime sahiptir (SPEC_OOT §8'deki beyanla aynı); §6'nın aralıkları bunun ötesinde §1'in sayılarına dayanır ve bunu gizlemez.
5. **Ağ:** yalnız TÜİK veri portalı (TÜFE bülteni ve metaverisi) ve TCMB `kurlar` XML sayfaları okundu; veri indirilmedi (`ekler/kaynak_kontrol_20260925.md`).

## 11. Kabul testleri (Opus için, kanıtlanabilir)

1. **Tablo v2:** 170 satır; H99 99 satırının paylaşılan sütunları `training_table.csv` ile bayt-eşit; 71 açık üyenin L değeri `data/outcomes_oot` ile birebir (L dağılımı 71: {0: 9, 1: 11, 2: 5, 3: 4, 4: 3, 5: 8, 6: 5, 7: 6, 8: 5, 9: 6, 10: 9} [ÖLÇTÜM §9]); `alloc_regime` tek fonksiyondan ve kohort etiketiyle 135/135 eşit; hiçbir SEALED kod (bekçi genişletilir); `training_table.csv`, `data_version.json` sha değişmez.
2. **TÜFE dosyası:** aylar 2019-11'den güncele kesintisiz; 2025'in 12 ayının ortalaması 100.00 ± 0.05 (2025=100 temeli); her satırın `release_date` referans ayını izleyen ayın ≥ 3'ü; sha pinli; `month_for`: T = 2026-09-02 → 2026-07, 2026-09-25 → 2026-07, 2026-10-01 → 2026-08, 2020-01-06 → 2019-11; `release_date < T` bekçisi 170 satırın hepsinde tutar.
3. **PP sayımı:** H99 f3'lü 506 / 83 (v0 ile aynı); açık f3'lü 374 / 59; havuz 880 / 142; grup olay/risk 25/165, 31/258, 86/457.
4. **Kırpma:** `v1_clip` nihai fit'te winsor sınırları H99 97 arzın f1 (ham TL) / f2 / f3 Type-7 p05/p95'i; f1 = p05'in yarısı olan sentetik girdi ile f1 = p05 girdisi aynı z'yi verir; `clipped_features = ["f1"]`; uyarı kodu ve `used` alanı doğru.
5. **f1r:** büyüklük ve endeks aynı k katıyla çarpılınca f1r değişmez (|Δ| ≤ 1e-12); eğitimdeki her arz için `tufe_month` = T'nin m−2'si; v1_real'in 97 arzdaki f1r'leri `tufe.index_for` ile yeniden üretilir.
6. **Rejim:** `v1_pooled` λ = 1e9 ile fit → ‖β‖ ≤ 1e-6, δ'nın mutlak değeri > 1e-3 ve λ = INF (γ, δ) Newton çözümüne |Δ| ≤ 1e-6; canlı girdiyle r = 0; kohorttan PRE/THRESH üye için r = 1, EQUAL için 0; H99 fold'larında r = 0 assert'i.
7. **Fold planı:** `v1_clip`, `v1_real` ledger ticker kümesi = v0 ledger'ının 87'si; `v1_pooled` ledger'ı 87'nin hepsini içerir; yakın dönem alt kümesi üçünde de aynı 78 ticker (22 ay bloğu); sızıntı: her fold'da max(eğitim seans tarihi) < T (açık üyeler dahil).
8. **v0 karşılaştırıcısı:** ledger sha `976b4dcea981…` pinli; eşleşik fark v0 RPS'i ledger'daki S_1..S_10'dan hesaplanır ve v0'ın yayımlı 87-fold ortalaması 0.1503 yeniden üretilir (|Δ| ≤ 1e-9).
9. **Karar etiketi:** sentetik aralıklar: [+0.001, +0.02] → "bozuyor"; [−0.02, +0.009] → "tolerans içinde"; [−0.005, +0.02] → "belirsiz"; [+0.000, +0.02] → "belirsiz" (alt = 0 dışlamaz).
10. **Bayt-eşitlik:** v0, `@INF`, PB tavan altın ledger'ları ve 16 eski altın dosya bayt-eşit; `gen_golden --check` yeşil; Rust golden paritesi 23 model.
11. **JSON ↔ stdlib predict:** üç adayın eğitim arzlarında |Δ| ≤ 1e-12; `v1_clip@INF` ve `v1_real@INF` iç hesapları `ceiling_hazard_v0@INF` JSON'uyla bit-eşit (bu yüzden kayıtlı değil); `v1_pooled@INF` farklı ve kayıtlı.
12. **Eski kohort ikinci kayıt:** 135 üyede tam 4 modelli ikinci kayıt; girdiler ilk kayıtla bayt-eşit; skorlama (model, üye) için modeli içeren en erken aktif kaydı seçer; model başına kapı: bir üyenin ikinci kaydı eksikken indirme kapısı kırmızı.
13. **Sınıf:** geçici git deposunda: model commit'i ingest'ten sonra → OOT_RETRO (açık küme senaryosu, `n_oot_retro = 71`); model + kayıt + kanıt → ingest → OOT_BLIND (kasa senaryosu); `oot_pre_h99_all` yeni modeller için üretilmez (test).
14. **Günlük:** her koşu `experiments/log.jsonl`'a satır; `spec_sha256` = bu dosyanın sha256'sı; `data_version_sha256` pooled için v2.
15. **Bekçiler:** yeni dosyalarda kasa kodu ve bülten adı kalıbı yok; `registry/` sonuç alanı taşımaz (tufe bloğu sonuç değildir; alan adı bekçi listesine eklenir).

## 12. Sözde kod

```
# --- borsai/tufe.py (stdlib) ---
def month_for(T):                      # "YYYY-MM-DD" -> "YYYY-MM" (m − 2)
    y, m = int(T[:4]), int(T[5:7]); m -= 2
    if m <= 0: y, m = y - 1, m + 12
    return f"{y:04d}-{m:02d}"
def index_for(T, table):               # RET: TUFE_MISSING / TUFE_NOT_PIT
    row = table.get(month_for(T)) or refuse("REFUSED_TUFE_MISSING")
    if row.release_date >= T: refuse("REFUSED_TUFE_NOT_PIT")
    return {"month": row.month, "index": row.index, "release_date": row.release_date, "file_sha256": table.sha}

# --- özellikler (tahmin ve fit aynı yol) ---
raw = compute_features(...)            # f1 (TL), f2, f3  (tek tanım, değişmez)
if variant in (real, pooled): raw["f1r"] = raw["f1"] / (tufe.index / 100)
r = 0 if live else 1[alloc_regime(T) != "EQUAL_DIST_20230330"]          # yalnız pooled

# --- ön işleme (arz düzeyi; eğitimden öğrenilir) ---
for col in recipe.winsor: bounds[col] = type7_p05_p95(train_raw[col])   # ham; f1/f1r log öncesi
z[col] = (log if col in {f1, f1r} else id)(clip(x[col], bounds[col])) -> (· − μ)/σ     # σ ddof = 0

# --- fit ---
X = [G(3) | R(0/1 sütun, cezasız) | Z(β)];  J = −Σ w[e ln h + (1−e) ln(1−h)] + (λ/2)‖β‖²  (+ 6 pseudo-satır, z = 0, r = 0)
lambda = argmin_inner_loo(GRID); tie -> max λ; INF -> β ≡ 0, (γ, δ) Newton

# --- tahmin (stdlib) ---
eta_d = γ[g(d)] + δ·r + β·z;  h_d = sigmoid(eta_d);  S_k = Π_{d≤k}(1 − h_d);  P_L, P_close (v0 ile aynı)

# --- yakın dönem hücresi ---
folds = [f for f in ledger_v1 if f.T >= "2024-01-01" and f.status == FIT_OK]      # 78 bekleniyor
d = [rps(S_v1[f], L[f]) − rps(S_v0_ledger[f], L[f]) for f in folds]
lo, hi = block_bootstrap(d, blocks = month(T))
label = "bozuyor" if lo > 0 else "tolerans içinde" if hi <= 0.010 else "belirsiz"

# --- kasa sonrası seçim (§5.5) ---
ok = [c for c in (clip, real, pooled) if vault(c).vs_km.hi < 0 and vault(c).vs_v0.hi < 0 and near(c).label != "bozuyor"]
primary = min(ok, key = lambda c: (round(vault(c).rps_point, 3), ORDER[c])) if ok else "ceiling_hazard_v0"
```

## 13. Açık sorular (proje sahibine; en çok 5; her birine öneri)

1. **Kasa açılışı.** §7.4: (C) şartnamesiyle **birlikte** açılış. Öneri: kabul. Alternatif istenirse (yalnız v1 için hemen açmak) (C)'nin doğrulama kümesi kaybolur; bunu yazılı kabul etmek gerekir.
2. **`pb_ceiling_v1`.** §2.4: bu şartnamenin dışında; kasada test edilemeyecek. Öneri: dışında kalsın (canlı terazi). Kasa testi isteniyorsa 4. kimlik olarak `pooled`'ın PB aynası (§2.4'teki tanım) bu şartnameye tek satırla eklenir ve aday bütçesi 4 olur; karar bu belgenin push'undan **önce** verilmelidir.
3. **Deflatör.** Öneri: TÜİK TÜFE (§3.2). USD tercih edilirse `ceiling_hazard_v1_real_usd` ayrı kimlik olur (TCMB `kurlar` XML, S0 günü ForexBuying); XU100 önerilmez.
4. **Uygulama birincil seçim kuralı (§5.5).** Öneri: kabul; kasa sonucuna göre otomatik. Alternatif: v0 canlı n ≥ 30'a kadar birincil kalsın (o zaman uygulama kartı "kasada geçen aday: …" satırını yine gösterir).
5. **`post_d1_hazard_v1`.** Öneri: kasa seçimi bittikten sonra ayrı, kısa şartname (§2.5); ebeveyn v0 kalırsa yazılmaz. Alternatif: üç aday için de şimdi ofset modeli (3 ek kimlik) — bütçe ve kasa tek-seferliği nedeniyle önerilmez.

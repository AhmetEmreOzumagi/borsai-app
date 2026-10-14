# BORSAI_FAZ6_S6_SCORING_20260925 — eski kohortun açık kümesinde zaman-dışı skorlar (üçüncü terazi)

Uygulayıcı: Claude Code (Opus 5.5). Tarih: 2026-09-25. Ağ kullanılmadı. push, tag ve amend yapılmadı.

Adım 0–1 ve ilk adım 2 başka bir oturumda koşuldu. O oturum adım 2'de DUR dedi (B1–B3,
`docs/faz6/ekler/s6_denetim.txt` §1–§4). Bağımsız düzeltme (`1c2fb02`), belge düzeltmesi (`96f7d62`) ve buradan sonraki adımlar
(adım 2'nin yeniden koşusu, S6 commit'i, bu rapor) ikinci bir oturumda yapıldı. Bu raporda hiçbir üyenin kodu ya da üye başına değeri
yok; hangi kodun kasada olduğu yazılmadı. `docs/faz6/dogrulama/EXPOSURE.md` §3'ün listesi okunmadı; küme yalnız kodla sayıldı (T3).
`docs/fable_faz6_s6/` açılmadı.

## Proje sahibi için özet (T7)

Bu paragraftaki her sayı **zaman-dışı teraziye** aittir. Terazi 2020–2023 eski kohortunun açık kümesidir (71 arz); tahminler sonuç
repoya girmeden push edildi, dönemin kural rejimi bugünkünden farklı. Sonuçlar canlı sicil ya da geçmiş veri testiyle toplanmaz,
ortalaması alınmaz.

- Zaman-dışı terazide sekiz listeleme öncesi modelin altısı birincil hücresinde karşılaştırıcısından **ayırt edilemiyor**:
  `v1_5_h99`, `v1_5_market20_v0`, `pb_v0`, `pb_ceiling_v0`, `ceiling_path_v0`, `pb_ceiling_path_v0`.
- Zaman-dışı terazide `ceiling_hazard_v0`, KM tabanına (`base_km_expanding`) karşı **geçemiyor**: RPS farkı +0.069, aralık
  [+0.001, +0.131], n = 68. Toplu sayılara göre model bu kohortta tavan serilerini olduğundan uzun görüyor (§9).
- Zaman-dışı terazide `v1_6_h99`, `v1_5_h99`'a karşı **geçemiyor**. Fark D10 getiri MAE'sinde yalnız +0.0004 (0.04 puan); aralık 0'ı
  dışladığı için hüküm böyle, ama büyüklük önceden yazılan "≈ 0" beklentisinin içinde.
- Zaman-dışı terazinin ayrı, makine sıralı (MACHINE_SEQUENCED) D1 sonrası tablosunda `post_d1_hazard_v0`, `ceiling_hazard_v0`'ın
  koşullu eğrisine karşı **geçiyor (zaman-dışı terazide)**: RPS_1 farkı −0.042, aralık [−0.066, −0.020], n = 59. Aynı tabloda KM ve
  @INF kurallarına karşı ayırt edilemiyor.

## 1. Commit'ler

| Sıra | Commit | İçerik |
|---|---|---|
| C | `e79a4b7` | `BORSAI_FAZ6_S6_CODE`: T1 (`--oot`), T2 (`render_oot_doc`), T3 (`spk_corporate_action_members`), testleri; I39–I41 |
| FIX | `1c2fb02` | `BORSAI_FAZ6_S6_FIX` (bağımsız el): B1 post_d1 D1 etiketi kapısı, B2 yalnız açık küme `retro_info`, B3 path karşılaştırıcısı; I42–I45; `docs/faz6/S6_FIX_RAPOR.md` |
| RENDER | `96f7d62` | `BORSAI_FAZ6_S6_RENDER`: `SCORES_OOT.md` §6 yeni sayaçlar ve satır tanımı; proje sahibi kararları (kalibrasyon satırı yok; F1 denetiminin kapsamı kabul); I46, I47 |
| S6 | `cf60cea` | `BORSAI_FAZ6_S6`: yalnız `scores/scores_oot.json` ve `docs/SCORES_OOT.md` (CLI çıktısı, elle düzenlenmedi) |
| R | bu raporu ekleyen commit | `BORSAI_FAZ6_S6_REPORT`: bu rapor, `docs/faz6/ekler/s6_denetim.txt`, `docs/faz6/ekler/s6_test_runs.txt`. Hash: `git log -1 --format=%H -- docs/faz6/S6_RAPOR.md` |

Sıra: C → (adım 2 DUR) → FIX → RENDER → adım 2 → S6 → R. Skor tanımları (kayıp, eşleşme, sınıf, bootstrap, n kuralları) hiçbir
commit'te değişmedi. FIX kodu şartnameye uydurdu (aynı model_id), RENDER yalnız gösterimi değiştirdi.

## 2. T4: önceden yazılmış akıl-sağlığı denetimleri

Kaynak: yazılmış `scores/scores_oot.json` (`generated_at_utc` 2026-09-25T15:30:18Z; `code.git_head` `96f7d62`; `borsai_dirty` false).
Ayrıntı ve hücre değerleri `docs/faz6/ekler/s6_denetim.txt` "YENİDEN KOŞU" bölümünde. "PS": proje sahibinin DUR'dan sonra eklediği
post_d1 beklentisi.

| Denetim | Sonuç | Değer |
|---|---|---|
| `code.borsai_dirty = false` | TUTTU | HEAD `96f7d62` |
| 19 model; açık küme 71 | TUTTU | 19; `n_open` = `n_in_table` = 71 |
| her modelde 71 satır; `n_skipped` = `n_pending` = `n_oot_retro` = `n_target_unavailable` = 0 | TUTTU | 19/19 |
| REFUSED ve NOT_APPLICABLE_REGIME sayıları ve kodları orkestratör tablosuyla birebir; `n_scored` = PREDICTED | TUTTU | 19/19 |
| üst düzey `retro_info` boş | TUTTU | 0 |
| her satır OOT_BLIND, `record_proof_before_ingest_proof` ve `cohort_gate_ok` true | TUTTU | 1349 satır |
| post_d1 `n_oot_retro` = 0 | TUTTU | 0 |
| PS: post_d1 `n_scored` = 59 | TUTTU | 59 |
| PS: post_d1 `n_refused` + `n_not_applicable` = 12 | TUTTU | 3 + 9 |
| PS: `n_d1_label_na` = `n_undetermined` = `n_skipped` = `n_retro` = `n_oot_retro` = 0 | TUTTU | hepsi 0 |
| PS: satır + bütün payda sayaçları = 71 | TUTTU | 62 + 9 = 71 |
| `scores.json`, `scores_post_d1.json`, `SCORES.md` bayt-eşit | TUTTU | sha256 önce = sonra |
| kasa kodu `scores_oot.json` ve `SCORES_OOT.md`'de yok (gerçek repo bekçisi) | TUTTU | 1 passed |

İlk T4 metninde post_d1 için "satır ≤ 59" yazıyordu; bu, satırın skorlanan satır olduğu varsayımına dayanıyordu. Düzeltmeden sonra
(I42) D1'i tavan olan ret hücreli üye de canlıdaki gibi satırdır. Bu yüzden 62 satır = SCORED 59 + REFUSED 3 (F3_MISSING). D1'i tavan
kapanmayan 9 üye satır değildir, `n_not_applicable`'da sayılır. Bu 9, S3b'deki NOT_APPLICABLE kayıt sayısına eşit; F1 tutarlılık
denetimi 9'unda da gerçekleşen D1 etiketini 0 buldu.

## 3. Birincil hücreler (zaman-dışı terazi; önceden ilan edilmiş)

Fark = model − karşılaştırılan; negatif = model iyi. Getiri farkları kesir birimindedir (0.030 = 3 puan). Aralık: ay-blok bootstrap,
B = 4000, numpy PCG64 tohum 20260921, yüzdelik [2.5, 97.5].

| Model | Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç/kayıp/eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| `v1_5_h99` | return D5 MAE | `base_train_median` | 68 (28) | 0.2306 | 0.2588 | −0.0282 | [−0.0807, +0.0225] | 36 / 32 / 0 | ayırt edilemiyor |
| `v1_6_h99` | return D10 MAE | `v1_5_h99` | 68 (28) | 0.7472 | 0.7468 | +0.0004 | [+0.0003, +0.0006] | 13 / 40 / 15 | geçemiyor |
| `v1_5_market20_v0` | return D5 MAE | `v1_5_h99` | 68 (28) | 0.2288 | 0.2306 | −0.0018 | [−0.0112, +0.0059] | 20 / 17 / 31 | ayırt edilemiyor |
| `pb_v0` | return D5 MAE | `base_train_median` | 59 (28) | 0.2398 | 0.2480 | −0.0082 | [−0.0550, +0.0358] | 30 / 29 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v0` | S RPS | `base_km_expanding` | 68 (28) | 0.2689 | 0.2002 | +0.0686 | [+0.0011, +0.1313] | 25 / 43 / 0 | geçemiyor |
| `pb_ceiling_v0` | S RPS | `base_km_expanding` | 59 (28) | 0.2525 | 0.2049 | +0.0476 | [−0.0050, +0.0999] | 22 / 37 / 0 | ayırt edilemiyor |
| `ceiling_path_v0` | return D5 MAE | `base_train_median` | 67 (28) | 0.2491 | 0.2591 | −0.0101 | [−0.0688, +0.0466] | 35 / 32 / 0 | ayırt edilemiyor |
| `pb_ceiling_path_v0` | return D5 MAE | `base_train_median` | 58 (28) | 0.2393 | 0.2482 | −0.0089 | [−0.0590, +0.0396] | 27 / 31 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` (ayrı ölçek, MACHINE_SEQUENCED) | S_cond RPS, j = 1 | `ceiling_hazard_v0` koşullu | 59 (26) | 0.2548 | 0.2965 | −0.0418 | [−0.0664, −0.0201] | 35 / 24 / 0 | geçiyor (zaman-dışı terazide) |

Satır sayaçları (açık küme 71; hedef oluşmadı, bekleyen, atlanan ve OOT_RETRO her modelde 0):

| Model | skorlanan | ret (kod) | rejimle uygulanamaz |
|---|---|---|---|
| `v1_5_h99`, `v1_6_h99`, `v1_5_market20_v0`, `ceiling_hazard_v0` | 68 | 3 (F3_MISSING) | 0 |
| `ceiling_path_v0` | 67 | 3 (F3_MISSING) | 1 (TICK_TABLE_MISMATCH) |
| `pb_v0`, `pb_ceiling_v0` | 59 | 12 (PB_IDENTITY 6, PB_PRICE_RANGE 4, PB_FIELD_MISSING 2) | 0 |
| `pb_ceiling_path_v0` | 58 | 12 (aynı) | 1 (TICK_TABLE_MISMATCH) |
| diğer 11 model: altı `base_*` kuralı, iki KM kuralı, üç @INF | 71 | 0 | 0 |
| `post_d1_hazard_v0` (ayrı ölçek) | 59 (satır 62) | 3 (F3_MISSING) | — (D1 tavan değil 9, payda) |

## 4. T5: şartname §8 beklentisiyle karşılaştırma

Konum, gözlenen nokta tahmininin §8 aralığına göre yeri: "aralık içinde" / "altında: beklenenden iyi" / "üstünde: beklenenden
kötü". Nokta tahmini §8 aralığının altındaysa satır **beklentiden çok iyi** diye işaretlendi. Bu işaret bir "geçiyor" hükmü değildir;
bağımsız doğrulama paralel Fable görevinin işidir. Beklentiden sapma modeli değiştirme gerekçesi değildir (§8; CLAUDE.md kural 5).

| Model / hücre | §8 yön | §8 aralık (aynen) | Gözlenen fark [%95 aralık], n | Konum |
|---|---|---|---|---|
| `v1_5_h99` D5 MAE − medyan | belirsiz, hafif kötü | [−0.01, +0.04] puan | −0.0282 [−0.0807, +0.0225], 68 | **altında: beklenenden iyi — beklentiden çok iyi** (iki okumada da; aşağıya bakın) |
| `v1_6_h99` D10 MAE − `v1_5_h99` | ≈ 0 | [−0.01, +0.01] | +0.000415 [+0.000259, +0.000573], 68 | aralık içinde (hüküm "geçemiyor": aralık 0'ı dışlıyor ve pozitif) |
| `v1_5_market20_v0` D5 MAE − `v1_5_h99` | ≈ 0, hafif iyi | [−0.01, +0.005] | −0.0018 [−0.0112, +0.0059], 68 | aralık içinde |
| `pb_v0` D5 MAE − medyan | hafif kötü | [−0.005, +0.03] | −0.0082 [−0.0550, +0.0358], 59 | **altında: beklenenden iyi — beklentiden çok iyi** |
| `ceiling_hazard_v0` RPS − `base_km_expanding` | belirsiz | [−0.03, +0.03] | +0.0686 [+0.0011, +0.1313], 68 | **üstünde: beklenenden kötü**; §8 başarısızlık tanımı: "geçemiyor" |
| `pb_ceiling_v0` RPS − `base_km_expanding` | hafif kötü | [−0.02, +0.04] | +0.0476 [−0.0050, +0.0999], 59 | **üstünde: beklenenden kötü** |
| `ceiling_path_v0` birincil (D5 MAE − medyan) | ≈ `ceiling_hazard_v0` ile aynı işaret | [−0.03, +0.03] | −0.0101 [−0.0688, +0.0466], 67 | aralık içinde; işaret beklenenin tersi (`ceiling_hazard_v0` +0.0686; iki hücrenin metriği farklı) |
| `pb_ceiling_path_v0` birincil (D5 MAE − medyan) | hafif kötü | [−0.02, +0.04] | −0.0089 [−0.0590, +0.0396], 58 | aralık içinde |
| `post_d1_hazard_v0` j = 1 birincil | belirsiz, hafif iyi | [−0.03, +0.02] | −0.0418 [−0.0664, −0.0201], 59 | **altında: beklenenden iyi — beklentiden çok iyi**; MACHINE_SEQUENCED |

**"puan" belirsizliği.** Yalnız ilk satırın aralığı "puan" sözcüğünü taşıyor; SPEC_SCORING §7'de "0.030 = 3 puan".
- Okuma A: sayılar öbür satırlar gibi kesir biriminde. Aralık [−0.01, +0.04] kesir = [−1, +4] puan. Gözlenen −0.0282 (−2.82 puan)
  aralığın altında.
- Okuma B: sayılar puan biriminde. Aralık [−0.01, +0.04] puan = [−0.0001, +0.0004] kesir. Gözlenen yine aralığın altında.

İki okuma da aynı konumu verir. Nokta tahmini beklentiden iyi, ama aralık 0'ı içeriyor ve hüküm "ayırt edilemiyor".

**§8 başarısızlık tanımının yıl kuralı** ("yıl alt kümelerinde tersine dönüyorsa 'rejime bağlı' notu").
- `ceiling_hazard_v0` (geçemiyor): fark 2021'de +0.1476, 2022'de +0.0914, 2023'te −0.0368. 2023'te işaret dönüyor; ama o alt kümenin
  aralığı ([−0.1305, +0.0576]) 0'ı içeriyor ve n = 21 ("yetersiz örnek"). Not: **rejime bağlı (zayıf kanıt)**.
- `v1_6_h99` (geçemiyor): üç yılda da işaret pozitif (+0.0005, +0.0006, +0.0001). Dönüş yok.

## 5. T6: f6 penceresi 2023-04-24'ü kesen üye (EK1, I38)

S2 kaydındaki `market20` penceresi (S20…S0 tarihleri) 2023-04-24'ü kesen üye: **açık kümede 1**, kohortta 5 (S3_S5_RAPOR EK1 ile
aynı). Bu açık üye `v1_5_market20_v0`'ın skorlanan satırlarından biri. Hesap kod yazılmadan geçici bir betikle yapıldı. Betik tam
kümeyle dosyadaki hücreyi birebir yeniden üretti.

| `v1_5_market20_v0` D5 MAE − `v1_5_h99` (keşif, duyarlılık) | n (blok) | fark | %95 aralık | kazanç/kayıp/eşit | hüküm |
|---|---|---|---|---|---|
| tam açık küme (birincil, §3) | 68 (28) | −0.0018 | [−0.0112, +0.0059] | 20 / 17 / 31 | ayırt edilemiyor |
| o üye çıkarılınca | 67 (27) | −0.0013 | [−0.0105, +0.0067] | 19 / 17 / 31 | ayırt edilemiyor |

Hüküm değişmedi. Bu üyede f6, 20 XU100 gözlemi üzerinden hesaplanmış kabul edilir (I38); kayıt iptali ya da yeniden kayıt yok.

## 6. Kırılımlar ve keşif hücreleri (zaman-dışı terazi)

### 6.1 İlk işlem yılı (ikincil; birincil hücre)

2020'de n 1–4: metrik yok. Diğer yılların hepsi 10 ≤ n < 30: "yetersiz örnek"; hüküm yok, yalnız nokta ve aralık.

| Model | 2021 fark [aralık] (n) | 2022 fark [aralık] (n) | 2023 fark [aralık] (n) |
|---|---|---|---|
| `v1_5_h99` | −0.0309 [−0.1047, +0.0514] (26) | +0.0052 [−0.0901, +0.0854] (20) | −0.0470 [−0.1352, +0.0473] (21) |
| `v1_6_h99` | +0.0005 [+0.0002, +0.0007] (26) | +0.0006 [+0.0004, +0.0009] (20) | +0.0001 [−0.0000, +0.0002] (21) |
| `v1_5_market20_v0` | +0.0034 [−0.0038, +0.0125] (26) | +0.0048 [−0.0072, +0.0155] (20) | −0.0148 [−0.0387, +0.0034] (21) |
| `pb_v0` | −0.0333 [−0.1170, +0.0646] (19) | +0.0412 [−0.0377, +0.1198] (17) | +0.0185 [−0.0271, +0.0702] (19) |
| `ceiling_hazard_v0` | +0.1476 [+0.0416, +0.2521] (26) | +0.0914 [+0.0159, +0.1577] (20) | −0.0368 [−0.1305, +0.0576] (21) |
| `pb_ceiling_v0` | +0.1082 [+0.0110, +0.2050] (19) | +0.0970 [+0.0279, +0.1649] (17) | −0.0053 [−0.0578, +0.0485] (19) |
| `ceiling_path_v0` | −0.0028 [−0.0825, +0.0923] (26) | +0.0409 [−0.0535, +0.1202] (20) | −0.0594 [−0.1570, +0.0497] (20) |
| `pb_ceiling_path_v0` | −0.0238 [−0.1101, +0.0718] (19) | +0.0497 [−0.0436, +0.1359] (17) | +0.0007 [−0.0652, +0.0659] (18) |

### 6.2 Rejim alt kümeleri (keşif; birincil hücre)

Tam tablo `docs/SCORES_OOT.md` §4.2'de. Hükmü olan (n ≥ 30) alt kümeler:
- borsa dışı satış (n 34–44): hepsi "ayırt edilemiyor", yalnız `v1_6_h99` "geçemiyor" (+0.0004);
- `ALLOC_REGIME = THRESH100_20211111` (n 31): `v1_6_h99` "geçemiyor" (+0.0005), öbürleri "ayırt edilemiyor"; `pb_*`
  modellerinde bu alt küme n 25 ("yetersiz örnek").

Borsada satış (n 23–25), `PRE_20211111` (19–22) ve `EQUAL_DIST_20230330` (14–15) alt kümeleri "yetersiz örnek". Hazard
modellerinin nokta farkı en büyük `PRE_20211111`'de: `ceiling_hazard_v0` +0.1486, `pb_ceiling_v0` +0.0624.

### 6.3 Keşif hücreleri (önceden ilan edilmemiş; çoklu karşılaştırma)

Listeleme öncesi modellerde 476 keşif hücresi var: 295 "ayırt edilemiyor", 149 "geçiyor (zaman-dışı terazide)", 32 "geçemiyor". Bu
sayılar modellerin geçtiği iddiası değildir. "Geçiyor" hücrelerinin çoğu zayıf kurallara karşıdır: `base_zero`, `base_always_ceiling`,
`base_last10_rate` (donmuş H99 değeri, kronolojik değil). Tekrarlayan örüntüler:
- **D10 getiri MAE'si medyana ve ortalamaya karşı "geçemiyor".** `v1_5_h99`, `v1_6_h99`, `v1_5_market20_v0` ve `ceiling_path_v0`'da
  fark +0.246…+0.295; `pb_v0` ve `pb_ceiling_path_v0`'da ortalamaya karşı +0.21 ve +0.25.
- **Hazard modelleri k = 10'da KM ve @INF'e karşı "geçemiyor".** `ceiling_hazard_v0` S_10 Brier +0.18…+0.19; `pb_ceiling_v0`
  +0.14…+0.15.
  `ceiling_hazard_v0` RPS'te kendi @INF'ine karşı da "geçemiyor" (+0.0689).
- **`pb_v0` D5 MAE'de `v1_5_h99`'a karşı "geçemiyor"** (+0.0434, n 56).
- **`ceiling_path_v0` D5 MAE'de `v1_5_h99`'a karşı "geçemiyor"** (+0.0169, n 67).
- **post_d1 tablosu (ayrı ölçek).** Birincil hücreden başka 20 hücre var. `ceiling_hazard_v0`'a karşı S_cond k = 2 Brier "geçiyor"
  (−0.0152). KM, KM-last10 ve @INF'e karşı k = 10 Brier "geçemiyor" (+0.20). path_conditional ikincillerinde (B3'ten sonra üretildi)
  D5 ve D10 MAE "geçiyor" (−0.031, −0.109; kod etiketi "ikincil"); D3 MAE iki tarafta aynı (58 eşit).

## 7. n_spk_corporate_action_seen

Açık kümede **14**, kohortta 28 (`registry.N_SPK_CORPORATE_ACTION_ROW_SEEN`). Küme `EXPOSURE.md` §3'ten kodla okundu (T3). Hiçbir
yere basılmadı, yazılmadı; JSON'da üye başına bayrak yok.

## 8. Test sayıları

| Koşu | Sonuç |
|---|---|
| Adım 0 (HEAD `b3f9f6f`) | pytest 607; test.sh cargo 94 / npm 222 / parity 4 / golden YEŞİL |
| C öncesi | pytest 625 (607 + 18); test.sh yeşil |
| FIX | `tests/test_faz6_s6_fix.py` e79a4b7'de 12 failed, düzeltmeyle 12 passed; pytest 637; test.sh yeşil |
| RENDER | yeni render testi 1c2fb02'de kırmızı, düzeltmeyle yeşil; pytest 638; test.sh yeşil |
| S6 öncesi (skor dosyaları izlenmezken) | pytest 638; kırmızı temizlik bekçisi yok, deselect gerekmedi |
| S6 sonrası, deselect'siz | pytest 638 (7 dk 51 s); test.sh cargo 94 / 0, npm 222, parity 4, golden YEŞİL |

Saatler ve ayrıntı: `docs/faz6/ekler/s6_test_runs.txt`.

## 9. Model geliştirme için gözlemler (keşif)

Bu bölümdeki her şey "keşif" etiketlidir: önceden ilan edilmedi, sonuç görüldükten sonra yazıldı. Hiçbiri bugünkü modelleri
değiştirme gerekçesi değildir; yalnız yeni model kimliği için bilgidir (CLAUDE.md kural 5).

1. **`ceiling_hazard_v0` bu kohortta seri uzunluğunu fazla tahmin ediyor.** 68 skorlanan arzda ortalama S_k (model / KM /
   gözlenen P(L ≥ k)):
   - k = 1: 0.930 / 0.818 / 0.868
   - k = 2: 0.885 / 0.707 / 0.706
   - k = 5: 0.665 / 0.414 / 0.529
   - k = 10: 0.431 / 0.141 / 0.132

   KM k = 10'da gözlenene çok yakın; model üç kat yüksek. §8'deki gerekçeyle uyumlu: f1 nominal TL; 2020–2021 arzları eğitim
   aralığının çok altında, ekstrapolasyon riski var. Kovaryatsız @INF de modeli yeniyor (+0.0689).
2. **Farkın yıla bağlılığı.** Ortalama L 2021'de 3.4, 2022'de 3.3, 2023'te 7.2. Hazard modelleri kısa serili yıllarda (2021–2022)
   KM'den belirgin kötü, uzun serili 2023'te nokta olarak iyi. Kovaryatların dönemler arası anlamı kaymış olabilir. Yeni bir hazard
   modeli için dönem ya da taban oranı ayarı düşünülebilir (yeni model_id).
3. **`post_d1_hazard_v0`'ın `ceiling_hazard_v0`'a karşı kazancı**, büyük ölçüde ana modelin 1. maddedeki kaymasını D1 bilgisiyle
   düzeltmesinden geliyor olabilir. KM ve @INF'e karşı birincil ölçekte ayırt edilemiyor (+0.05), k = 10 Brier'de onlardan kötü.
   D1 bilgisinin tek başına değeri bu terazide gösterilmiş değil.
4. **D10 getiri tahminleri** medyan ve ortalama kurallarından belirgin kötü; D5'te fark yok. Uzun ufukta getiri ölçeği dönemler
   arasında taşınmıyor.
5. **`v1_6_h99` ile `v1_5_h99` pratikte aynı** (D10 MAE farkı 0.04 puan, 15 eşit). Izgara farkı bu terazide bilgi taşımıyor.
6. **`pb_v0`, D5 getiri MAE'sinde `v1_5_h99`'dan kötü** (+0.043, n 56; keşif hücresi). PB kimlik ve fiyat aralığı retleri açık
   kümenin 12/71'i.

# BORSAI_FAZ7_FABLE_VAULT_RECOMPUTE_20260929 — Faz 1: kör yeniden hesap (kasa, 64 üye)

Denetçi: Claude Code (Fable 5.1). Tarih: 2026-09-29 (İstanbul). Taban: HEAD `6287750` (`BORSAI_PUSH_PROOFS: Faz 7 vault outcome rows (71b9071)`; VB `71b9071` HEAD'in atası).

**Körlük beyanı.** Bu Faz 1 boyunca `scores/scores_oot.json`, `docs/SCORES_OOT.md`, `docs/faz7_vault/SKOR_RAPOR.md`, `docs/faz7_vault/ekler/skor_*` açılmadı, okunmadı, grep edilmedi; `borsai` import edilmedi (iki betik `python -I` ile koştu; çıktıda `borsai_imported: false`); `borsai/scoring.py` okunmadı. `docs/SPEC_DEVIATIONS.md` çalışma ağacından değil, yalnız HEAD'deki commit'li sürümünden `git show HEAD:…` ile okundu (I10–I13, I22, I23, L1, M1, M12). `docs/faz7_vault/RAPOR.md` de HEAD sürümünden okundu (sayı ve sıra bilgisi için). `tests/` okunmadı. `scores/scores.json` yalnız `models[].backtest.near_era` blokları için okundu. Çalışma ağacında bu görev sırasında Opus'un `docs/faz7_vault/ekler/skor_denetim.py` dosyası belirdi; açılmadı. Ağ yalnız 10 bülten zip'inin resmi URL'den `/tmp/borsai_fable_vault/`'a yeniden indirilmesi için kullanıldı; dizin sonra silindi. Karantinaya dokunulmadı. push, tag, amend yok. `BORSAI_FAZ7_VAULT_SCORE_REPORT` commit'i bu yazım sırasında repoda yok (`git log --all | grep -c VAULT_SCORE_REPORT` = 0).

Dosyalar: `recompute.py` (sınıf, durum, hücreler, seçim kuralları → `BAGIMSIZ.json`), `kaynak_denetimi.py` (adım 5 → `kaynak_denetimi_cikti.json`), bu özet. Bu özette üye başına değer tablosu ve kasa kodu yok; arz başına kayıp çiftleri `BAGIMSIZ.json` → `cells.*.*.pairs`.

## 0. Taban

HEAD `6287750`; `71b9071` atası. İzlenmeyen dosyalar: iki görev dosyası ve Opus'un izinli yolu. Repoda kohort penceresi tarihli izlenen zip 0. INDEX 27 model (19 eski + 4 v1 + 4 (C)), `INDEX_POST_D1` 1 model.

## 1. Sınıf (`class_oot`; SPEC_OOT §2 + I13 + L1, tarihlerden)

| Terim | Değer |
|---|---|
| 27 INDEX modeli için sonuç girişi (I10 + M1: min(outcomes csv, raw json, d1_rows, pencere zip'i)) | 64/64 üyede **`2f914dd`** (VA1; kanıt 2026-09-29T15:30:41Z) |
| `post_d1_hazard_v0` için sonuç girişi (d1_rows hariç; zip terimi (D_1, D_10]) | 64/64 üyede **`71b9071`** (VB; kanıt 2026-09-29T17:49:25Z) |
| Modeli içeren en erken etkin kayıt (L1/L2 + I12) | 19 eski model: ilk kayıt, 64/64 ekleyen commit `1dcceff` (kanıt 2026-09-24T22:39:24Z); 8 yeni model: delta kaydı, 64/64 `28aaa3b` (kanıt 2026-09-29T06:40:55Z); üye başına 2 kayıt, iptal 0 |
| POST_D1 kaydı | 64/64 tek kayıt, ekleyen commit `5a96e25` (kanıt 2026-09-29T15:30:43Z) |
| Model commit'leri ve kanıtları | 19 eski (5fa849d / b09cab5 / a0df5b7; 2026-09-22), v1 dörtlüsü `66adbca` (2026-09-27T15:30:42Z), (C) dörtlüsü `ce569a8` (2026-09-28T19:06:01Z), post_d1 `7c18c0f` (2026-09-24T14:13:55Z); 28/28 kanıtlı ve ilgili ingest'in atası |
| Kohort kapısı (L1: model başına, bütün 135 MEMBER; ata VE kanıt önce) | 27 model × 135 üye: modeli içeren kayıt commit'leri {`1dcceff`} ya da {`28aaa3b`}; ikisi de `2f914dd`'nin atası ve kanıtları önce → kapı açık; POST_D1 için kapı modeli `ceiling_hazard_v0` (L1), `71b9071`'e karşı açık |
| POST_D1 ek koşulları (I13) | 64/64: d1_rows kanonik sha = kayıt; D_1 THB/THM sha ve URL = MANIFEST_OOT pini = sonuç dosyası h=1; base_record = üyenin ilk etkin kaydı (yol + sha); d1_rows commit'i (`2f914dd`) ingest'in atası |
| DAG'da toplam sıra | 64/64 tam sıralı |
| Gerçekleşen D_1 = `first_trading_date` | 64/64 |

**Sayılar:**

| Küme | OOT_BLIND | OOT_RETRO |
|---|---|---|
| 27 INDEX modeli × 64 kasa üyesi | **1728** | 0 |
| `post_d1_hazard_v0` × 64 | **64** | 0 |
| Toplam | **1792** | 0 |

## 2. Satır durumları (kasa, 64 üye)

640 sonuç satırının hepsi `OK`; TARGET_UNAVAILABLE 0, NA_LIMIT 0, PENDING 0, SKIPPED 0. CSV `Y_h` sütunu ile `1[R_h > 0]` 256/256 eşit.

| Model | SCORED | REFUSED | NOT_APPLICABLE_REGIME |
|---|---|---|---|
| `v1_5_h99`, `v1_6_h99`, `v1_5_market20_v0`, `ceiling_hazard_v0`, `ceiling_hazard_v1_clip`, `_real`, `_pooled` | 62 | 2 | 0 |
| `pb_v0`, `pb_ceiling_v0` | 53 | 11 | 0 |
| `ceiling_path_v0` | 60 | 1 | 3 |
| `pb_ceiling_path_v0` | 51 | 10 | 3 |
| `base_always_ceiling`, `ceiling_hazard_v0@INF`, `pb_ceiling_v0@INF`, `ceiling_path_v0@INF`, `ceiling_hazard_v1_pooled@INF` | 63 | 0 | 1 |
| `fall_d10_v0_h99`, `fall_d10_v0_pooled` | 60 | 4 | 0 |
| `fall_d10_v0_addsale` | 62 | 2 | 0 |
| 7 kural + `fall_d10_v0_pooled@ZERO` | 64 | 0 | 0 |
| **Toplam 27 × 64 = 1728** | **1660** | **57** | **11** |

`post_d1_hazard_v0`: SCORED **45**, REFUSED **2** (`F3_MISSING`), NOT_APPLICABLE **17** (`D1_NOT_CEILING`; satır kapısı SPEC_POST_D1_V0: yalnız D1 tavan etiketi 1 olan üye satırdır). RAPOR §6'daki 45/2/17 ile aynı.

Bilgi: gerçekleşen seri L (64): 0: 17, 1: 3, 2: 7, 3: 5, 4: 7, 5: 4, 6: 5, 7: 3, 8: 2, 9: 2, 10: 9. Kasa yıl 2020: 4, 2021: 26, 2022: 18, 2023: 16; tahsis PRE 29 / THRESH 23 / EQUAL 12; borsada satış 22.

## 3. Hücreler (kasa; fark = model − karşılaştırılan, negatif = model iyi)

Blok = gerçekleşen D_1 ayı; aralık = ay-blok bootstrap (B = 4000, `numpy.random.Generator(PCG64(20260921))`, 2.5/97.5), koşul n ≥ 10 ve ≥ 6 blok; hüküm yalnız n ≥ 30. Kural değerleri üyenin ilk etkin kaydındaki `comparators` bloğundan (donmuş H99). K/Kb/E = kazanç/kayıp/eşit.

### 3.1 Eski 8 birincil hücre (SPEC_OOT §6)

| # | Hücre | n | blok | ort. fark | %95 aralık | K/Kb/E | hüküm |
|---|---|---|---|---|---|---|---|
| 1 | `v1_5_h99` D5 MAE − `base_train_median` | 62 | 27 | −0.011866 | [−0.070594, +0.041197] | 32/30/0 | ayırt edilemiyor |
| 2 | `v1_6_h99` D10 MAE − `v1_5_h99` | 62 | 27 | +0.000399 | [+0.000116, +0.000654] | 14/38/10 | geçemiyor |
| 3 | `v1_5_market20_v0` D5 MAE − `v1_5_h99` | 62 | 27 | −0.006065 | [−0.018567, +0.005637] | 23/14/25 | ayırt edilemiyor |
| 4 | `pb_v0` D5 MAE − `base_train_median` | 53 | 26 | +0.030277 | [−0.026276, +0.088253] | 24/29/0 | ayırt edilemiyor |
| 5 | `ceiling_hazard_v0` RPS − `base_km_expanding` | 62 | 27 | +0.072833 | [−0.000814, +0.138804] | 26/36/0 | ayırt edilemiyor |
| 6 | `pb_ceiling_v0` RPS − `base_km_expanding` | 53 | 26 | +0.065257 | [−0.004170, +0.132875] | 20/33/0 | ayırt edilemiyor |
| 7 | `ceiling_path_v0` D5 MAE − `base_train_median` | 60 | 27 | +0.001898 | [−0.070366, +0.068423] | 28/32/0 | ayırt edilemiyor |
| 8 | `pb_ceiling_path_v0` D5 MAE − `base_train_median` | 51 | 25 | +0.034617 | [−0.036567, +0.101817] | 21/30/0 | ayırt edilemiyor |

Hücre 5, SPEC_HAZARD_V1 §6.1'in ilk satırıdır (v0 − KM kasada).

### 3.2 v1 ailesi (SPEC_HAZARD_V1 §5.2, §5.4)

| Hücre | etiket | n | blok | ort. fark | %95 aralık | K/Kb/E | hüküm |
|---|---|---|---|---|---|---|---|
| `v1_clip` RPS − `base_km_expanding` | birincil | 62 | 27 | +0.033365 | [−0.026028, +0.088636] | 26/36/0 | ayırt edilemiyor |
| `v1_clip` RPS − `ceiling_hazard_v0` | k2 | 62 | 27 | −0.039467 | [−0.064041, −0.016132] | 42/20/0 | geçiyor (zaman-dışı) |
| `v1_clip` Brier k=10 − KM | ikincil | 62 | 27 | +0.069317 | [−0.015176, +0.146268] | 23/39/0 | ayırt edilemiyor |
| `v1_real` RPS − KM | birincil | 62 | 27 | −0.011037 | [−0.050031, +0.025901] | 39/23/0 | ayırt edilemiyor |
| `v1_real` RPS − v0 | k2 | 62 | 27 | −0.083870 | [−0.127917, −0.034728] | 47/15/0 | geçiyor (zaman-dışı) |
| `v1_real` Brier k=10 − KM | ikincil | 62 | 27 | +0.019196 | [−0.039680, +0.073335] | 33/29/0 | ayırt edilemiyor |
| `v1_pooled` RPS − KM | birincil | 62 | 27 | **−0.040009** | **[−0.067054, −0.012178]** | 42/20/0 | **geçiyor (zaman-dışı)** |
| `v1_pooled` RPS − v0 | k2 | 62 | 27 | −0.112842 | [−0.180783, −0.038056] | 42/20/0 | geçiyor (zaman-dışı) |
| `v1_pooled` Brier k=10 − KM | ikincil | 62 | 27 | −0.015301 | [−0.049241, +0.016062] | 47/15/0 | ayırt edilemiyor |
| `v1_real − v1_clip` (deflasyon payı) | merdiven | 62 | 27 | −0.044402 | [−0.073282, −0.011296] | 47/15/0 | — |
| `v1_pooled − v1_real` (havuz + rejim payı) | merdiven | 62 | 27 | −0.028972 | [−0.058823, +0.003735] | 37/25/0 | — |
| `v1_pooled − v1_pooled@INF` (özelliklerin payı) | merdiven | 62 | 27 | −0.035355 | [−0.062474, −0.007299] | 42/20/0 | — |

Kasa RPS noktaları (aynı 62 arz): v0 0.270112; KM 0.197279; clip 0.230644; real 0.186242; pooled 0.157270; pooled@INF 0.192625.

Kalibrasyon (bilgi; 62 arz; gözlenen P(L ≥ 5) = 0.371, P(L ≥ 10) = 0.129): ort. S_5 v0 0.643, clip 0.589, real 0.473, pooled 0.328; ort. S_10 v0 0.410, clip 0.331, real 0.222, pooled 0.123. §6.4-d (|ort. S_5 − gözlenen| > 0.15): clip 0.218 → "düzey kayması"; real 0.102, pooled 0.043 → yok (v0'da da 0.272).

### 3.3 (C) ailesi (SPEC_C_V0 §5.2, §5.4; hedef y4 = 1 − Y_D10, C1)

| Hücre | etiket | n | blok | ort. fark | %95 aralık | K/Kb/E | hüküm |
|---|---|---|---|---|---|---|---|
| `fall_h99` D10 Brier − `base_rate` | birincil | 60 | 27 | −0.039814 | [−0.087828, +0.004260] | 47/13/0 | ayırt edilemiyor |
| `fall_h99` D10 − `v1_5_h99` | k2 | 60 | 27 | −0.025037 | [−0.090590, +0.030224] | 12/48/0 | ayırt edilemiyor |
| `fall_h99` D5 − `base_rate` | ikincil | 60 | 27 | −0.024425 | [−0.062647, +0.010527] | 49/11/0 | ayırt edilemiyor |
| `fall_pooled` D10 − `base_rate` | birincil | 60 | 27 | **−0.045219** | **[−0.092270, −0.002029]** | 49/11/0 | **geçiyor (zaman-dışı)** |
| `fall_pooled` D10 − `v1_5_h99` | k2 | 60 | 27 | −0.030442 | [−0.100318, +0.031991] | 14/46/0 | ayırt edilemiyor |
| `fall_pooled` D5 − `base_rate` | ikincil | 60 | 27 | −0.034641 | [−0.075585, +0.001173] | 47/13/0 | ayırt edilemiyor |
| `fall_addsale` D10 − `base_rate` | birincil | 62 | 29 | −0.005823 | [−0.054065, +0.035836] | 47/15/0 | ayırt edilemiyor |
| `fall_addsale` D10 − `v1_5_h99` | k2 | 60 | 27 | +0.010376 | [−0.066664, +0.078031] | 13/47/0 | ayırt edilemiyor |
| `fall_addsale` D5 − `base_rate` | ikincil | 62 | 29 | −0.000088 | [−0.032770, +0.030381] | 47/15/0 | ayırt edilemiyor |
| `pooled − h99` (eski verinin payı) | merdiven | 60 | 27 | −0.005405 | [−0.027233, +0.018779] | 16/44/0 | — |
| `pooled − pooled@ZERO` (özelliklerin payı) | merdiven | 60 | 27 | −0.038367 | [−0.092211, +0.009868] | 46/14/0 | — |
| `v1_5_h99` D10 − `base_rate` | bilgi | 62 | 27 | −0.014377 | [−0.053339, +0.025684] | 51/11/0 | ayırt edilemiyor |

Kasa D10 Brier noktaları: h99 0.128822 (60), pooled 0.123417 (60), addsale 0.160141 (62; aynı 60'ta 0.164236), base_rate 0.168636 (60), v1_5 0.153859 (60). Olay: y4 12/60 (0.200; addsale kümesinde 12/62), y3 10/60.

Kalibrasyon (bilgi): ort. P(y4) h99 0.257, pooled 0.256, addsale 0.283, v1_5 0.104 (gözlenen 0.200; v1_5 kümesinde 13/62 = 0.210). §6.4-d eşiği (0.15) aşılmadı.

### 3.4 `post_d1_hazard_v0` (SPEC_POST_D1_V0 §4; j = 1 koşullu)

| Hücre | n | blok | ort. fark | %95 aralık | K/Kb/E | hüküm |
|---|---|---|---|---|---|---|
| koşullu RPS − `ceiling_hazard_v0` koşullu | 45 | 25 | −0.034665 | [−0.071489, +0.004372] | 19/26/0 | ayırt edilemiyor |

Karşılaştırıcı S_k/S_1 S2 kaydından yeniden hesaplandı; POST_D1 kaydındaki `comparators_conditional` ile 45/45 eşit (|Δ| ≤ 1e-12). M12 "beklentiden çok iyi" (fark < −0.08 ya da üst < −0.045): hayır.

## 4. Seçim kuralları (kendi sayılarımla)

**v1 (SPEC_HAZARD_V1 §5.5).** k1 = kasa birincil "geçiyor"; k2 = RPS − v0 üst ucu < 0; k3 = yakın dönem "bozuyor" değil (`scores.json` near_era: clip −0.0011 [−0.0066, +0.0049] "tolerans içinde"; real +0.0104 [+0.0028, +0.0183] "bozuyor"; pooled +0.0289 [+0.0089, +0.0518] "bozuyor").

| Aday | k1 | k2 | k3 | uygun |
|---|---|---|---|---|
| `v1_clip` | ✗ (ayırt edilemiyor) | ✓ | ✓ | ✗ |
| `v1_real` | ✗ (ayırt edilemiyor) | ✓ | ✗ (bozuyor) | ✗ |
| `v1_pooled` | ✓ (geçiyor) | ✓ | ✗ (bozuyor) | ✗ |

**Sonuç: uygun aday yok → `ceiling_hazard_v0` birincil kalır** (§5.5-3; K4: kart üç adayı yan yana gösterir). Eşitlik kuralı gerekmedi.

**(C) (SPEC_C_V0 §5.5).** k1 = kasa birincil "geçiyor"; k2 = D10 Brier − `v1_5_h99` üst ucu < 0; k3: pooled için yakın dönem `pooled − h99` "bozuyor" değil (−0.0058 [−0.0340, +0.0219] "belirsiz"); h99/addsale için yakın dönem − `base_rate` aralığı tamamen 0'ın üstünde değil (h99 [−0.0773, −0.0048]; addsale [−0.0301, +0.0161]).

| Aday | k1 | k2 | k3 | uygun |
|---|---|---|---|---|
| `fall_h99` | ✗ | ✗ | ✓ | ✗ |
| `fall_pooled` | ✓ (geçiyor) | ✗ (üst +0.032) | ✓ | ✗ |
| `fall_addsale` | ✗ | ✗ | ✓ | ✗ |

**Sonuç: "kasada geçen aday yok"** (§5.5-3; V1.5'in p_up sütunu olduğu gibi kalır; hiçbir aday öne çıkarılmaz).

Başarısızlık tanımları (§6.4 sözcükleriyle): v1 — (a) "v0'dan kötü" hiçbirinde; (b) "bozuyor": real, pooled; (c) "özellikler bilgi eklemiyor" (pooled − @INF ≥ 0): hayır (−0.035); (d) "düzey kayması": clip; (e) "beklentiden çok iyi" (birincil < −0.10 ya da üst < −0.06): hiçbirinde. (C) — (a) "taban orandan kötü": hiçbirinde; (b) "bozuyor": hayır; (c) "ek satış bilgi eklemiyor" (addsale − taban ≥ 0): hayır (−0.006); "özellikler bilgi eklemiyor" (pooled − @ZERO ≥ 0): hayır; (d) yok; (e) "beklentiden çok iyi" (< −0.08 ya da üst < −0.04): hiçbirinde.

**Sınıra yakın aralık uçları (Faz 2 için not; |uç| < 0.005):** `fall_pooled − base_rate` üst −0.0020 (k1'in dayandığı uç); `ceiling_hazard_v0 − KM` alt −0.0008; `fall_pooled` D5 − taban üst +0.0012; `fall_h99 − base_rate` üst +0.0043; `post_d1` üst +0.0044; `v1_pooled − v1_real` üst +0.0037. Farklı bir bootstrap çekiliş sırası bu uçları 0'ın öbür tarafına taşıyabilir; iki seçim kuralının sonucu bundan etkilenmez (pooled (C) adayı zaten k2'de düşer; v1 pooled k3'te düşer).

## 5. Kaynak denetimi (adım 5)

`random.Random(20260929).sample(MANIFEST_OOT veri satırı 915–1168 [254 satır], 10)`: 2020: 3, 2021: 5, 2022: 2; THB 6, THM 4. Her zip resmi URL'den `/tmp/borsai_fable_vault/`'a indirildi.

| Denetim | Sayı |
|---|---|
| indirilen / sha256 pinle eşit / bayt eşit | 10 / **10** / 10 |
| o tarihe düşen kasa üye-satırı (beklenen / bültende tek satır bulunan / TARIH = bülten günü = `session_date`) | 11 / **11** / 11 |
| karşılaştırılan ham alan (THB: `close_raw`, `trade_count_raw`; THM: `upper_limit_raw`, `reference_raw`) eşit / farklı | **22 / 0** |
| sonuç dosyasındaki `thb_sha256`/`thm_sha256` = MANIFEST pini | 11 / 11 |
| TARIH biçimi (bültenlerin bütün satırları; bağımsız çözümleme: ISO ya da d.mm.yyyy / dd.mm.yyyy) | 17 490 satır ISO; ISO dışı bülten 0; gün uyuşmazlığı 0 |
| geçici dizin silindi; `borsai` import | evet; hayır |

## 6. Tanım yorumları (belirsiz ya da iki okumalı yerler)

1. **Karşılaştırıcı kaynağı.** Yeni 8 modelin delta kaydında `comparators` bloğu boş; kural değerleri üyenin ilk etkin kaydından (S2) alındı. Kural 1 gereği bunlar donmuş H99 değerleridir; kayıtlar arasında `model_inputs` bayt-eşit olduğundan başka bir seçenek yoktur.
2. **Kapı.** L1'in model başına kapısı: ingest'teki INDEX'in her modeli × bütün 135 MEMBER için o modeli içeren en erken etkin kayıt ingest'in atası **ve** kanıtı önce. POST_D1 için kapı modeli `ceiling_hazard_v0` (L1 metni). Faz 6 S6 denetiminde yalnız ata terimi vardı; burada ikisi de var. Sonuç değişmez (kanıtlar 06:40:55Z ve 09-24T22:39:24Z < 15:30:41Z).
3. **Seçim kuralındaki "kasa RPS/Brier noktası".** Adayın kendi birincil hücre çiftlerindeki ortalama model kaybı. v1 adayları aynı 62 arzda; (C) adaylarında `addsale` 62, diğerleri 60 arzda. Ortak 60'taki değer bilgi olarak yanına yazıldı (addsale 0.164). Bu görevde uygun aday olmadığından nokta karşılaştırması sonucu etkilemedi.
4. **k3'ün h99/addsale okuması.** "Yakın dönem − `base_rate` hücresi tamamen 0'ın üstünde değil" = aralığın alt ucu ≤ 0. `scores.json`'daki near_era bloğunda bu iki adayın karşılaştırıcısı `base_rate`, pooled'ınki `fall_d10_v0_h99`; kod bunu böyle yazmış, şartnameyle uyumlu.
5. **Brier tanımı.** (C) modelleri `p_up` verir; hedef y4 = 1 − Y_D10 (C1). (p_up − Y_h)² ile ((1 − p_up) − y4)² sayısal olarak aynıdır; Y_h = 1[R_h > 0] (CSV `Y_h` ile 256/256 eşit). Kapanış = arz fiyatı durumu olay sayılır.
6. **Getiri nokta tahmini** kayıttaki `return` (kırpılmışsa kırpılmış; Faz 6 yorumu 1 aynen); tavan yolu `return` = karışım medyanı.
7. **Bootstrap** SPEC_SCORING §9 aynen (ids sıralı, `rng.choice(ids)`, `np.percentile` linear). Aynı girdiyle bit-eşit tekrar; farklı çekiliş sırası uçları oynatır (§4 notu).
8. **Hüküm dili.** "geçiyor / geçemiyor" yalnız n ≥ 30 ve aralık 0'ı dışlarsa, zaman-dışı satırda "(zaman-dışı terazide)" ekiyle; n < 30 "yetersiz örnek" (bu görevde hiçbir hücre n < 30 değil; post_d1 n = 45).
9. **Satır durumu ile sınıf ayrı** sayıldı; hücrelere yalnız OOT_BLIND ve iki tarafı PREDICTED çiftler girer. `post_d1`'in NOT_APPLICABLE (D1 tavan değil) durumu rejim uygulanamazlığı değildir; ayrı sayıldı. NOT_APPLICABLE_REGIME 11 hücre (1 üyede marj kuralı: 5 model; 3 üyede tavan yolu: 2 model).
10. **Kasa MANIFEST satırı sınırı.** 915. veri satırından itibaren (VAULT_OPEN.json `manifest_oot_before.n_rows = 914`; RAPOR §5 ve §B3: 914 → 946 → 1168). Kaynak denetimi yalnız kasa üyelerinin satırlarını aradı.
11. **Yıl ve rejim kırılımları** yalnız bilgi (her biri n < 30); `BAGIMSIZ.json` → `cells_summary.*.*.by_year`, `by_alloc_regime`.

## 7. Önceden yazılmış beklentiyle karşılaştırma (bilgi; hüküm değil)

v1 (§6.1): 13 hücrenin 13'ü beklenen aralık içinde (v0 − KM +0.073 [beklenen +0.08, aralık +0.02…+0.14]; clip − KM +0.033 [+0.035]; clip − v0 −0.039 [−0.04]; clip Brier10 +0.069 [+0.10]; real − KM −0.011 [−0.005]; real − v0 −0.084 [−0.08]; real − clip −0.044 [−0.04]; real Brier10 +0.019 [+0.04]; pooled − KM −0.040 [−0.03]; pooled − v0 −0.113 [−0.10]; pooled − real −0.029 [−0.03]; pooled − @INF −0.035 [−0.01; aralık −0.04…+0.02]; pooled Brier10 −0.015 [0.00]; kalibrasyon pooled S_5 − gözlenen −0.043 [−0.10…+0.10]). Şartnamenin "en az olası" dediği "bir adayın KM'ye karşı geçiyor demesi" pooled'da gerçekleşti (aralık üst ucu −0.012); beklenti aralığı 0'ı içeriyordu ama nokta beklentinin yanındadır.

(C) (§6.1): 12 hücrenin 11'i içinde; dışında kalan `addsale − v1_5_h99` +0.010 (beklenen −0.035 [−0.085, +0.010]; kötü yönde, sınırda). `pooled − base_rate` −0.045 (beklenen −0.030 [−0.070, +0.010]) aralığı 0'ı dışladı ("büyük olasılıkla içerir" denmişti). Kalibrasyon pooled +0.056 [−0.08…+0.08] içinde.

Eski 8 hücre (SPEC_OOT §8): 5 içinde (2, 3, 4, 7, 8); 1 (−0.012, beklenen −0.01…+0.04) hafifçe iyi yönde dışında; 5 (+0.073) ve 6 (+0.065) kötü yönde dışında (açık kümedekiyle aynı kalıp: +0.069 / +0.048). `post_d1`: SPEC_OOT §8 [−0.03, +0.02] dışında iyi yönde; M12 beklentisi −0.035 [−0.065, −0.005]: nokta −0.035 birebir, aralık 0'ı içeriyor (üst +0.004) → M12'nin "geçiyor olası ama kesin değil" notunun "kesin değil" tarafı.

Mekanizma yorumu Faz 2'de, Opus'un raporuyla birlikte. Ön not (sayı): `v1_pooled − v0` yıl kırılımı 2021 (26) −0.232, 2022 (18) −0.044, 2023 (16) +0.010; PRE_20211111 (27) −0.225. `fall_pooled − base_rate`: 2021 −0.066, 2022 −0.073, 2023 +0.011; EQUAL_DIST (12) +0.042.

## 8. Kabul (Faz 1)

- K1: bu commit Opus'un kasa skor çıktılarına bakılmadan atıldı (körlük beyanı; `BORSAI_FAZ7_VAULT_SCORE_REPORT` yok).
- K2: hücreler (8 + 13 + 12 + 1), sınıf (1792 BLIND / 0 RETRO), durum sayıları ve iki seçim kuralı bağımsız hesaplandı; kaynak denetimi 10/10 sha ve 22/22 alan, 11/11 satır eşit.

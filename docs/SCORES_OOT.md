# Zaman-dışı test: H99 öncesi kohort (2020–2023), tahminler sonuç repoya girmeden dondurulmuş (rejim farklı)

Bu sayfa `python -m borsai.scoring --oot` ile `scores/scores_oot.json`'dan üretilir; elle düzenlenmez. Tanımlar: `docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md` (§2 sınıf, §3 üçüncü terazi, §6 skorlama), `docs/specs_faz6/KARARLAR.md`, `docs/specs/SPEC_SCORING.md` §7–§8; yorum kararları `docs/SPEC_DEVIATIONS.md` bölüm I. Kod: `borsai/scoring.py`.

- **Üçüncü terazi (`OOT_PRE_H99`), asla toplanmaz.** Bu sayfadaki her sayı zaman-dışı teraziye aittir. Geçmiş veri testi (retrospektif) ve canlı sicil (prospektif) `docs/SCORES.md`'dedir; üç terazi arasında toplam ya da ortalama yoktur (CLAUDE.md kural 3).
- Kohort: ilk işlem günü 2020-01-01…2023-09-21 olan H99 öncesi arzlar. Tablolar yalnız açık kümedir (`oot_pre_h99`: OPEN ∪ EXPOSED_*). Kasadaki üyelerin sonucu repoda yoktur; skorlanmaz, kasa açılınca ayrı anahtarla raporlanır.
- Sınıf koddan hesaplanır, elle etiket yok: SPEC_OOT_PRE_H99_V0 §2 + KARARLAR D6-5: oot_ingest_commit(a) = min(data/outcomes_oot/<a>.csv, data/outcomes_oot/raw/<a>.json ve registry/oot/d1_rows/<a>.json'u ekleyen commit, tarihi [D_1(a), D_10(a)] olan herhangi bir THB/THM zip'ini ekleyen commit); OOT_BLIND = model commit'i ve kayıt commit'i onun atası VE modelin push kanıtı var VE push_kanıtı(kayıt) < push_kanıtı(oot_ingest_commit) VE kohortun HER MEMBER'ının S2 kaydı onun atası; aksi OOT_RETRO (yalnız bilgi). SPEC_HAZARD_V1 §7.2–§7.3 (model başına): kayıt = (model, üye) için modeli içeren en erken etkin kayıt; kohort kapısı = HER MEMBER için o modeli içeren kayıt ingest'in atası VE push kanıtı ingest'inkinden önce. OOT_RETRO çift hiçbir n'e girmez.
- Sonuç: resmi THB/THM'den makineyle ayıklanmış satırlar (`outcome_basis = MACHINE_EXTRACTED`). Karşılaştırılanlar: H99'da donmuş kural değerleri (kayıtta); last10: FROZEN_H99_LAST10_NOT_CHRONOLOGICAL.
- Fark = model − kural; negatif = model iyi. Aralık: ay-blok bootstrap (blok = gerçekleşen D_1'in takvim ayı), B = 4000, numpy PCG64 tohum 20260921, yüzdelik [2.5, 97.5]; koşul n ≥ 10 ve ≥ 6 blok.
- Dil (SPEC_SCORING §8): n < 10 → metrik yok; 10 ≤ n < 30 → "yetersiz örnek"; n ≥ 30 → aralık tamamen 0'ın altındaysa "geçiyor (zaman-dışı terazide)", tamamen üstündeyse "geçemiyor", 0'ı içeriyorsa "ayırt edilemiyor". Noktasal fark tek başına hüküm değildir.
- Üretim 2026-09-29T18:08:37Z; HEAD `38d36e812877bb101252eff417fb6299b448b22b`; borsai kaynak sha256 `f501510d12c3`; borsai kirli: hayır; kohort sha256 `7d05b334d739`.
- Üye başına satırlar (tahmin, gerçekleşen, kayıplar, sınıf kanıtı) yalnız `scores/scores_oot.json`'dadır; bu sayfada üye kodu yoktur.

## 1. Kohort sayaçları

| MEMBER | kapsam dışı | üyelik bekleyen | açık küme | kasa (SEALED) | EXPOSED_ARCHIVE | EXPOSED_CODEX | tabloya giren | SPK kurumsal işlem satırı görülen (tabloda / kohortta) |
|---|---|---|---|---|---|---|---|---|
| 135 | 1 | 0 | 71 | 64 | 4 | 1 | 71 | 14 / 28 |

## 2. Birincil hücreler (önceden ilan edilmiş, değişmez; SPEC_OOT_PRE_H99_V0 §6)

| Model | Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| `v1_5_h99` | return D5 MAE | `base_train_median` | 68 (28) | 0.2306 | 0.2588 | -0.0282 | [-0.0807, +0.0225] | 36 / 32 / 0 | ayırt edilemiyor |
| `v1_6_h99` | return D10 MAE | `v1_5_h99` | 68 (28) | 0.7472 | 0.7468 | +0.0004 | [+0.0003, +0.0006] | 13 / 40 / 15 | geçemiyor |
| `v1_5_market20_v0` | return D5 MAE | `v1_5_h99` | 68 (28) | 0.2288 | 0.2306 | -0.0018 | [-0.0112, +0.0059] | 20 / 17 / 31 | ayırt edilemiyor |
| `pb_v0` | return D5 MAE | `base_train_median` | 59 (28) | 0.2398 | 0.2480 | -0.0082 | [-0.0550, +0.0358] | 30 / 29 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v0` | S RPS | `base_km_expanding` | 68 (28) | 0.2689 | 0.2002 | +0.0686 | [+0.0011, +0.1313] | 25 / 43 / 0 | geçemiyor |
| `pb_ceiling_v0` | S RPS | `base_km_expanding` | 59 (28) | 0.2525 | 0.2049 | +0.0476 | [-0.0050, +0.0999] | 22 / 37 / 0 | ayırt edilemiyor |
| `ceiling_path_v0` | return D5 MAE | `base_train_median` | 67 (28) | 0.2491 | 0.2591 | -0.0101 | [-0.0688, +0.0466] | 35 / 32 / 0 | ayırt edilemiyor |
| `pb_ceiling_path_v0` | return D5 MAE | `base_train_median` | 58 (28) | 0.2393 | 0.2482 | -0.0089 | [-0.0590, +0.0396] | 27 / 31 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_clip` | S RPS | `base_km_expanding` | 0 | — | — | — | — | — | OOT_RETRO (71 çift; bu alt küme bu model için test değil) |
| `ceiling_hazard_v1_real` | S RPS | `base_km_expanding` | 0 | — | — | — | — | — | OOT_RETRO (71 çift; bu alt küme bu model için test değil) |
| `ceiling_hazard_v1_pooled` | S RPS | `base_km_expanding` | 0 | — | — | — | — | — | OOT_RETRO (71 çift; bu alt küme bu model için test değil) |
| `fall_d10_v0_h99` | p_up D10 Brier | `base_rate` | 0 | — | — | — | — | — | OOT_RETRO (71 çift; bu alt küme bu model için test değil) |
| `fall_d10_v0_pooled` | p_up D10 Brier | `base_rate` | 0 | — | — | — | — | — | OOT_RETRO (71 çift; bu alt küme bu model için test değil) |
| `fall_d10_v0_addsale` | p_up D10 Brier | `base_rate` | 0 | — | — | — | — | — | OOT_RETRO (71 çift; bu alt küme bu model için test değil) |

## 3. Satır sayaçları (model başına, açık küme)

| Model | tür | skorlanan | ret | rejimle uygulanamaz | hedef oluşmadı | bekleyen | atlanan (kayıt yok) | OOT_RETRO |
|---|---|---|---|---|---|---|---|---|
| `v1_5_h99` | linear | 68 | 3 | 0 | 0 | 0 | 0 | 0 |
| `base_always_ceiling` | rule | 71 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_train_median` | rule | 71 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_train_mean` | rule | 71 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_zero` | rule | 71 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_rate` | rule | 71 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_last10_rate` | rule | 71 | 0 | 0 | 0 | 0 | 0 | 0 |
| `v1_6_h99` | linear | 68 | 3 | 0 | 0 | 0 | 0 | 0 |
| `v1_5_market20_v0` | market20 | 68 | 3 | 0 | 0 | 0 | 0 | 0 |
| `pb_v0` | pb | 59 | 12 | 0 | 0 | 0 | 0 | 0 |
| `ceiling_hazard_v0` | hazard | 68 | 3 | 0 | 0 | 0 | 0 | 0 |
| `ceiling_hazard_v0@INF` | hazard | 71 | 0 | 0 | 0 | 0 | 0 | 0 |
| `pb_ceiling_v0` | hazard | 59 | 12 | 0 | 0 | 0 | 0 | 0 |
| `pb_ceiling_v0@INF` | hazard | 71 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_km_expanding` | km | 71 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_km_last10` | km | 71 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ceiling_path_v0` | ceiling_path | 67 | 3 | 1 | 0 | 0 | 0 | 0 |
| `ceiling_path_v0@INF` | ceiling_path | 71 | 0 | 0 | 0 | 0 | 0 | 0 |
| `pb_ceiling_path_v0` | ceiling_path | 58 | 12 | 1 | 0 | 0 | 0 | 0 |
| `ceiling_hazard_v1_clip` | hazard | 0 | 0 | 0 | 0 | 0 | 0 | 71 |
| `ceiling_hazard_v1_real` | hazard | 0 | 0 | 0 | 0 | 0 | 0 | 71 |
| `ceiling_hazard_v1_pooled` | hazard | 0 | 0 | 0 | 0 | 0 | 0 | 71 |
| `ceiling_hazard_v1_pooled@INF` | hazard | 0 | 0 | 0 | 0 | 0 | 0 | 71 |
| `fall_d10_v0_h99` | fall | 0 | 0 | 0 | 0 | 0 | 0 | 71 |
| `fall_d10_v0_pooled` | fall | 0 | 0 | 0 | 0 | 0 | 0 | 71 |
| `fall_d10_v0_addsale` | fall | 0 | 0 | 0 | 0 | 0 | 0 | 71 |
| `fall_d10_v0_pooled@ZERO` | fall | 0 | 0 | 0 | 0 | 0 | 0 | 71 |

## 4. Birincil hücrenin kırılımları

### 4.1 İlk işlem yılı (ikincil)

| Model | Alt küme | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm (ikincil) |
|---|---|---|---|---|---|---|---|---|---|
| `v1_5_h99` | 2020 | `base_train_median` | 1 (1) | — | — | — | — | — | metrik yok (n < 10) |
| `v1_5_h99` | 2021 | `base_train_median` | 26 (10) | 0.2263 | 0.2572 | -0.0309 | [-0.1047, +0.0514] | 13 / 13 / 0 | yetersiz örnek |
| `v1_5_h99` | 2022 | `base_train_median` | 20 (9) | 0.2904 | 0.2853 | +0.0052 | [-0.0901, +0.0854] | 9 / 11 / 0 | yetersiz örnek |
| `v1_5_h99` | 2023 | `base_train_median` | 21 (8) | 0.1899 | 0.2368 | -0.0470 | [-0.1352, +0.0473] | 13 / 8 / 0 | yetersiz örnek |
| `v1_6_h99` | 2020 | `v1_5_h99` | 1 (1) | — | — | — | — | — | metrik yok (n < 10) |
| `v1_6_h99` | 2021 | `v1_5_h99` | 26 (10) | 0.9027 | 0.9022 | +0.0005 | [+0.0002, +0.0007] | 4 / 13 / 9 | yetersiz örnek |
| `v1_6_h99` | 2022 | `v1_5_h99` | 20 (9) | 0.8039 | 0.8033 | +0.0006 | [+0.0004, +0.0009] | 2 / 16 / 2 | yetersiz örnek |
| `v1_6_h99` | 2023 | `v1_5_h99` | 21 (8) | 0.5138 | 0.5137 | +0.0001 | [-0.0000, +0.0002] | 7 / 11 / 3 | yetersiz örnek |
| `v1_5_market20_v0` | 2020 | `v1_5_h99` | 1 (1) | — | — | — | — | — | metrik yok (n < 10) |
| `v1_5_market20_v0` | 2021 | `v1_5_h99` | 26 (10) | 0.2297 | 0.2263 | +0.0034 | [-0.0038, +0.0125] | 4 / 6 / 16 | yetersiz örnek |
| `v1_5_market20_v0` | 2022 | `v1_5_h99` | 20 (9) | 0.2953 | 0.2904 | +0.0048 | [-0.0072, +0.0155] | 6 / 5 / 9 | yetersiz örnek |
| `v1_5_market20_v0` | 2023 | `v1_5_h99` | 21 (8) | 0.1751 | 0.1899 | -0.0148 | [-0.0387, +0.0034] | 10 / 6 / 5 | yetersiz örnek |
| `pb_v0` | 2020 | `base_train_median` | 4 (3) | — | — | — | — | — | metrik yok (n < 10) |
| `pb_v0` | 2021 | `base_train_median` | 19 (8) | 0.2035 | 0.2368 | -0.0333 | [-0.1170, +0.0646] | 11 / 8 / 0 | yetersiz örnek |
| `pb_v0` | 2022 | `base_train_median` | 17 (9) | 0.3180 | 0.2768 | +0.0412 | [-0.0377, +0.1198] | 7 / 10 / 0 | yetersiz örnek |
| `pb_v0` | 2023 | `base_train_median` | 19 (8) | 0.2555 | 0.2370 | +0.0185 | [-0.0271, +0.0702] | 8 / 11 / 0 | yetersiz örnek |
| `ceiling_hazard_v0` | 2020 | `base_km_expanding` | 1 (1) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v0` | 2021 | `base_km_expanding` | 26 (10) | 0.3259 | 0.1784 | +0.1476 | [+0.0416, +0.2521] | 5 / 21 / 0 | yetersiz örnek |
| `ceiling_hazard_v0` | 2022 | `base_km_expanding` | 20 (9) | 0.2703 | 0.1789 | +0.0914 | [+0.0159, +0.1577] | 6 / 14 / 0 | yetersiz örnek |
| `ceiling_hazard_v0` | 2023 | `base_km_expanding` | 21 (8) | 0.2057 | 0.2425 | -0.0368 | [-0.1305, +0.0576] | 13 / 8 / 0 | yetersiz örnek |
| `pb_ceiling_v0` | 2020 | `base_km_expanding` | 4 (3) | — | — | — | — | — | metrik yok (n < 10) |
| `pb_ceiling_v0` | 2021 | `base_km_expanding` | 19 (8) | 0.2805 | 0.1722 | +0.1082 | [+0.0110, +0.2050] | 5 / 14 / 0 | yetersiz örnek |
| `pb_ceiling_v0` | 2022 | `base_km_expanding` | 17 (9) | 0.2760 | 0.1789 | +0.0970 | [+0.0279, +0.1649] | 4 / 13 / 0 | yetersiz örnek |
| `pb_ceiling_v0` | 2023 | `base_km_expanding` | 19 (8) | 0.2370 | 0.2424 | -0.0053 | [-0.0578, +0.0485] | 9 / 10 / 0 | yetersiz örnek |
| `ceiling_path_v0` | 2020 | `base_train_median` | 1 (1) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_path_v0` | 2021 | `base_train_median` | 26 (10) | 0.2544 | 0.2572 | -0.0028 | [-0.0825, +0.0923] | 13 / 13 / 0 | yetersiz örnek |
| `ceiling_path_v0` | 2022 | `base_train_median` | 20 (9) | 0.3262 | 0.2853 | +0.0409 | [-0.0535, +0.1202] | 9 / 11 / 0 | yetersiz örnek |
| `ceiling_path_v0` | 2023 | `base_train_median` | 20 (8) | 0.1775 | 0.2369 | -0.0594 | [-0.1570, +0.0497] | 12 / 8 / 0 | yetersiz örnek |
| `pb_ceiling_path_v0` | 2020 | `base_train_median` | 4 (3) | — | — | — | — | — | metrik yok (n < 10) |
| `pb_ceiling_path_v0` | 2021 | `base_train_median` | 19 (8) | 0.2131 | 0.2368 | -0.0238 | [-0.1101, +0.0718] | 10 / 9 / 0 | yetersiz örnek |
| `pb_ceiling_path_v0` | 2022 | `base_train_median` | 17 (9) | 0.3265 | 0.2768 | +0.0497 | [-0.0436, +0.1359] | 6 / 11 / 0 | yetersiz örnek |
| `pb_ceiling_path_v0` | 2023 | `base_train_median` | 18 (8) | 0.2378 | 0.2371 | +0.0007 | [-0.0652, +0.0659] | 7 / 11 / 0 | yetersiz örnek |

### 4.2 Rejim alt kümeleri (keşif)

| Model | Alt küme | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm (keşif) |
|---|---|---|---|---|---|---|---|---|---|
| `v1_5_h99` | SALE_ON_EXCHANGE | `base_train_median` | 24 (12) | 0.2004 | 0.2455 | -0.0452 | [-0.1329, +0.0412] | 14 / 10 / 0 | yetersiz örnek |
| `v1_5_h99` | OFF_EXCHANGE | `base_train_median` | 44 (25) | 0.2472 | 0.2660 | -0.0189 | [-0.0822, +0.0423] | 22 / 22 / 0 | ayırt edilemiyor |
| `v1_5_h99` | ALLOC_REGIME=PRE_20211111 | `base_train_median` | 22 (10) | 0.2301 | 0.2525 | -0.0223 | [-0.0964, +0.0665] | 10 / 12 / 0 | yetersiz örnek |
| `v1_5_h99` | ALLOC_REGIME=THRESH100_20211111 | `base_train_median` | 31 (13) | 0.2174 | 0.2735 | -0.0562 | [-0.1405, +0.0319] | 19 / 12 / 0 | ayırt edilemiyor |
| `v1_5_h99` | ALLOC_REGIME=EQUAL_DIST_20230330 | `base_train_median` | 15 (6) | 0.2588 | 0.2376 | +0.0212 | [-0.0379, +0.0959] | 7 / 8 / 0 | yetersiz örnek |
| `v1_6_h99` | SALE_ON_EXCHANGE | `v1_5_h99` | 24 (12) | 0.7833 | 0.7828 | +0.0005 | [+0.0002, +0.0008] | 6 / 14 / 4 | yetersiz örnek |
| `v1_6_h99` | OFF_EXCHANGE | `v1_5_h99` | 44 (25) | 0.7276 | 0.7272 | +0.0004 | [+0.0002, +0.0005] | 7 / 26 / 11 | geçemiyor |
| `v1_6_h99` | ALLOC_REGIME=PRE_20211111 | `v1_5_h99` | 22 (10) | 0.8923 | 0.8919 | +0.0004 | [+0.0001, +0.0007] | 2 / 10 / 10 | yetersiz örnek |
| `v1_6_h99` | ALLOC_REGIME=THRESH100_20211111 | `v1_5_h99` | 31 (13) | 0.6976 | 0.6971 | +0.0005 | [+0.0003, +0.0008] | 6 / 20 / 5 | geçemiyor |
| `v1_6_h99` | ALLOC_REGIME=EQUAL_DIST_20230330 | `v1_5_h99` | 15 (6) | 0.6371 | 0.6369 | +0.0001 | [-0.0000, +0.0003] | 5 / 10 / 0 | yetersiz örnek |
| `v1_5_market20_v0` | SALE_ON_EXCHANGE | `v1_5_h99` | 24 (12) | 0.2049 | 0.2004 | +0.0046 | [-0.0047, +0.0159] | 5 / 7 / 12 | yetersiz örnek |
| `v1_5_market20_v0` | OFF_EXCHANGE | `v1_5_h99` | 44 (25) | 0.2418 | 0.2472 | -0.0053 | [-0.0169, +0.0062] | 15 / 10 / 19 | ayırt edilemiyor |
| `v1_5_market20_v0` | ALLOC_REGIME=PRE_20211111 | `v1_5_h99` | 22 (10) | 0.2311 | 0.2301 | +0.0010 | [-0.0035, +0.0035] | 3 / 5 / 14 | yetersiz örnek |
| `v1_5_market20_v0` | ALLOC_REGIME=THRESH100_20211111 | `v1_5_h99` | 31 (13) | 0.2225 | 0.2174 | +0.0051 | [-0.0046, +0.0149] | 8 / 7 / 16 | ayırt edilemiyor |
| `v1_5_market20_v0` | ALLOC_REGIME=EQUAL_DIST_20230330 | `v1_5_h99` | 15 (6) | 0.2385 | 0.2588 | -0.0203 | [-0.0529, +0.0046] | 9 / 5 / 1 | yetersiz örnek |
| `pb_v0` | SALE_ON_EXCHANGE | `base_train_median` | 25 (15) | 0.1936 | 0.2452 | -0.0515 | [-0.1250, +0.0210] | 15 / 10 / 0 | yetersiz örnek |
| `pb_v0` | OFF_EXCHANGE | `base_train_median` | 34 (23) | 0.2738 | 0.2501 | +0.0236 | [-0.0311, +0.0753] | 15 / 19 / 0 | ayırt edilemiyor |
| `pb_v0` | ALLOC_REGIME=PRE_20211111 | `base_train_median` | 19 (10) | 0.1824 | 0.2260 | -0.0435 | [-0.1507, +0.0607] | 11 / 8 / 0 | yetersiz örnek |
| `pb_v0` | ALLOC_REGIME=THRESH100_20211111 | `base_train_median` | 25 (13) | 0.2591 | 0.2710 | -0.0120 | [-0.0826, +0.0642] | 14 / 11 / 0 | yetersiz örnek |
| `pb_v0` | ALLOC_REGIME=EQUAL_DIST_20230330 | `base_train_median` | 15 (6) | 0.2804 | 0.2376 | +0.0428 | [+0.0071, +0.0936] | 5 / 10 / 0 | yetersiz örnek |
| `ceiling_hazard_v0` | SALE_ON_EXCHANGE | `base_km_expanding` | 24 (12) | 0.2590 | 0.1737 | +0.0852 | [+0.0043, +0.1614] | 7 / 17 / 0 | yetersiz örnek |
| `ceiling_hazard_v0` | OFF_EXCHANGE | `base_km_expanding` | 44 (25) | 0.2743 | 0.2147 | +0.0596 | [-0.0203, +0.1414] | 18 / 26 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v0` | ALLOC_REGIME=PRE_20211111 | `base_km_expanding` | 22 (10) | 0.3315 | 0.1829 | +0.1486 | [+0.0091, +0.2986] | 4 / 18 / 0 | yetersiz örnek |
| `ceiling_hazard_v0` | ALLOC_REGIME=THRESH100_20211111 | `base_km_expanding` | 31 (13) | 0.2328 | 0.2032 | +0.0296 | [-0.0681, +0.1152] | 14 / 17 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v0` | ALLOC_REGIME=EQUAL_DIST_20230330 | `base_km_expanding` | 15 (6) | 0.2515 | 0.2194 | +0.0320 | [-0.0166, +0.1000] | 7 / 8 / 0 | yetersiz örnek |
| `pb_ceiling_v0` | SALE_ON_EXCHANGE | `base_km_expanding` | 25 (15) | 0.2440 | 0.1886 | +0.0554 | [-0.0258, +0.1315] | 10 / 15 / 0 | yetersiz örnek |
| `pb_ceiling_v0` | OFF_EXCHANGE | `base_km_expanding` | 34 (23) | 0.2588 | 0.2169 | +0.0419 | [-0.0159, +0.1037] | 12 / 22 / 0 | ayırt edilemiyor |
| `pb_ceiling_v0` | ALLOC_REGIME=PRE_20211111 | `base_km_expanding` | 19 (10) | 0.2545 | 0.1922 | +0.0624 | [-0.0854, +0.2003] | 8 / 11 / 0 | yetersiz örnek |
| `pb_ceiling_v0` | ALLOC_REGIME=THRESH100_20211111 | `base_km_expanding` | 25 (13) | 0.2563 | 0.2059 | +0.0505 | [-0.0245, +0.1216] | 8 / 17 / 0 | yetersiz örnek |
| `pb_ceiling_v0` | ALLOC_REGIME=EQUAL_DIST_20230330 | `base_km_expanding` | 15 (6) | 0.2437 | 0.2194 | +0.0243 | [-0.0092, +0.0709] | 6 / 9 / 0 | yetersiz örnek |
| `ceiling_path_v0` | SALE_ON_EXCHANGE | `base_train_median` | 23 (12) | 0.2196 | 0.2459 | -0.0263 | [-0.1256, +0.0744] | 13 / 10 / 0 | yetersiz örnek |
| `ceiling_path_v0` | OFF_EXCHANGE | `base_train_median` | 44 (25) | 0.2645 | 0.2660 | -0.0016 | [-0.0760, +0.0683] | 22 / 22 / 0 | ayırt edilemiyor |
| `ceiling_path_v0` | ALLOC_REGIME=PRE_20211111 | `base_train_median` | 22 (10) | 0.2625 | 0.2525 | +0.0100 | [-0.0762, +0.1151] | 10 / 12 / 0 | yetersiz örnek |
| `ceiling_path_v0` | ALLOC_REGIME=THRESH100_20211111 | `base_train_median` | 31 (13) | 0.2375 | 0.2735 | -0.0360 | [-0.1310, +0.0574] | 19 / 12 / 0 | ayırt edilemiyor |
| `ceiling_path_v0` | ALLOC_REGIME=EQUAL_DIST_20230330 | `base_train_median` | 14 (6) | 0.2535 | 0.2378 | +0.0158 | [-0.0634, +0.1083] | 6 / 8 / 0 | yetersiz örnek |
| `pb_ceiling_path_v0` | SALE_ON_EXCHANGE | `base_train_median` | 24 (15) | 0.2120 | 0.2456 | -0.0335 | [-0.1191, +0.0462] | 13 / 11 / 0 | yetersiz örnek |
| `pb_ceiling_path_v0` | OFF_EXCHANGE | `base_train_median` | 34 (23) | 0.2586 | 0.2501 | +0.0084 | [-0.0545, +0.0711] | 14 / 20 / 0 | ayırt edilemiyor |
| `pb_ceiling_path_v0` | ALLOC_REGIME=PRE_20211111 | `base_train_median` | 19 (10) | 0.1862 | 0.2260 | -0.0398 | [-0.1533, +0.0676] | 11 / 8 / 0 | yetersiz örnek |
| `pb_ceiling_path_v0` | ALLOC_REGIME=THRESH100_20211111 | `base_train_median` | 25 (13) | 0.2580 | 0.2710 | -0.0131 | [-0.0930, +0.0723] | 12 / 13 / 0 | yetersiz örnek |
| `pb_ceiling_path_v0` | ALLOC_REGIME=EQUAL_DIST_20230330 | `base_train_median` | 14 (6) | 0.2781 | 0.2378 | +0.0403 | [-0.0119, +0.1021] | 4 / 10 / 0 | yetersiz örnek |
| `ceiling_hazard_v1_clip` | SALE_ON_EXCHANGE | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v1_clip` | OFF_EXCHANGE | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v1_clip` | ALLOC_REGIME=PRE_20211111 | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v1_clip` | ALLOC_REGIME=THRESH100_20211111 | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v1_clip` | ALLOC_REGIME=EQUAL_DIST_20230330 | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v1_real` | SALE_ON_EXCHANGE | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v1_real` | OFF_EXCHANGE | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v1_real` | ALLOC_REGIME=PRE_20211111 | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v1_real` | ALLOC_REGIME=THRESH100_20211111 | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v1_real` | ALLOC_REGIME=EQUAL_DIST_20230330 | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v1_pooled` | SALE_ON_EXCHANGE | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v1_pooled` | OFF_EXCHANGE | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v1_pooled` | ALLOC_REGIME=PRE_20211111 | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v1_pooled` | ALLOC_REGIME=THRESH100_20211111 | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `ceiling_hazard_v1_pooled` | ALLOC_REGIME=EQUAL_DIST_20230330 | `base_km_expanding` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_h99` | SALE_ON_EXCHANGE | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_h99` | OFF_EXCHANGE | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_h99` | ALLOC_REGIME=PRE_20211111 | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_h99` | ALLOC_REGIME=THRESH100_20211111 | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_h99` | ALLOC_REGIME=EQUAL_DIST_20230330 | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_pooled` | SALE_ON_EXCHANGE | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_pooled` | OFF_EXCHANGE | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_pooled` | ALLOC_REGIME=PRE_20211111 | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_pooled` | ALLOC_REGIME=THRESH100_20211111 | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_pooled` | ALLOC_REGIME=EQUAL_DIST_20230330 | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_addsale` | SALE_ON_EXCHANGE | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_addsale` | OFF_EXCHANGE | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_addsale` | ALLOC_REGIME=PRE_20211111 | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_addsale` | ALLOC_REGIME=THRESH100_20211111 | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |
| `fall_d10_v0_addsale` | ALLOC_REGIME=EQUAL_DIST_20230330 | `base_rate` | 0 (0) | — | — | — | — | — | metrik yok (n < 10) |

## 5. Keşif hücreleri (önceden ilan edilmemiş)

Canlı hücre tanımlarının aynısı (SPEC_OOT_PRE_H99_V0 §6, SPEC_DEVIATIONS I11); yalnız n ≥ 10 olanlar. Etiket "keşif": önceden ilan edilmediler ve çok sayıdalar (çoklu karşılaştırma); hüküm sözcüğü yalnız §8 dil kuralının çıktısıdır, bir modelin "geçtiği" iddiası değildir.

### `v1_5_h99` (keşif)

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| return D1 MAE | `base_always_ceiling` | 68 (28) | 0.0128 | 0.0096 | +0.0033 | [-0.0007, +0.0070] | 8 / 26 / 34 | ayırt edilemiyor |
| return D1 MAE | `base_train_median` | 68 (28) | 0.0128 | 0.0096 | +0.0033 | [-0.0007, +0.0070] | 8 / 26 / 34 | ayırt edilemiyor |
| return D1 MAE | `base_train_mean` | 68 (28) | 0.0128 | 0.0256 | -0.0128 | [-0.0161, -0.0092] | 56 / 12 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_zero` | 68 (28) | 0.0128 | 0.0905 | -0.0777 | [-0.0885, -0.0635] | 62 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 DirMiss | `base_always_ceiling` | 68 (28) | 0.0294 | 0.0294 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| return D3 MAE | `base_always_ceiling` | 68 (28) | 0.1090 | 0.1027 | +0.0063 | [-0.0155, +0.0287] | 13 / 16 / 39 | ayırt edilemiyor |
| return D3 MAE | `base_train_median` | 68 (28) | 0.1090 | 0.1020 | +0.0070 | [-0.0147, +0.0295] | 25 / 43 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_train_mean` | 68 (28) | 0.1090 | 0.1335 | -0.0245 | [-0.0508, +0.0017] | 40 / 28 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_zero` | 68 (28) | 0.1090 | 0.2396 | -0.1307 | [-0.1952, -0.0581] | 48 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 DirMiss | `base_always_ceiling` | 68 (28) | 0.1324 | 0.1324 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| return D5 MAE | `base_always_ceiling` | 68 (28) | 0.2306 | 0.2451 | -0.0144 | [-0.0711, +0.0445] | 21 / 15 / 32 | ayırt edilemiyor |
| return D5 MAE | `base_train_mean` | 68 (28) | 0.2306 | 0.2684 | -0.0378 | [-0.1010, +0.0241] | 36 / 32 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_zero` | 68 (28) | 0.2306 | 0.3797 | -0.1491 | [-0.2742, -0.0166] | 42 / 26 / 0 | geçiyor (zaman-dışı terazide) |
| return D5 DirMiss | `base_always_ceiling` | 68 (28) | 0.1618 | 0.1618 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| return D10 MAE | `base_always_ceiling` | 68 (28) | 0.7468 | 1.0428 | -0.2960 | [-0.4439, -0.1592] | 46 / 7 / 15 | geçiyor (zaman-dışı terazide) |
| return D10 MAE | `base_train_median` | 68 (28) | 0.7468 | 0.4927 | +0.2541 | [+0.0255, +0.4564] | 21 / 47 / 0 | geçemiyor |
| return D10 MAE | `base_train_mean` | 68 (28) | 0.7468 | 0.4779 | +0.2689 | [+0.0772, +0.4393] | 21 / 47 / 0 | geçemiyor |
| return D10 MAE | `base_zero` | 68 (28) | 0.7468 | 0.5748 | +0.1721 | [-0.0990, +0.4208] | 29 / 39 / 0 | ayırt edilemiyor |
| return D10 DirMiss | `base_always_ceiling` | 68 (28) | 0.1912 | 0.1912 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D1 Brier | `base_always_ceiling` | 68 (28) | 0.0287 | 0.0294 | -0.0007 | [-0.0057, +0.0026] | 2 / 66 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_always_ceiling` | 68 (28) | 0.1267 | 0.4063 | -0.2796 | [-0.7934, +0.0422] | 2 / 66 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_rate` | 68 (28) | 0.0287 | 0.0337 | -0.0050 | [-0.0084, +0.0002] | 63 / 5 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_rate` | 68 (28) | 0.1267 | 0.1708 | -0.0441 | [-0.0725, -0.0015] | 63 / 5 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_last10_rate` | 68 (28) | 0.0287 | 0.1659 | -0.1372 | [-0.1582, -0.1034] | 66 / 2 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_last10_rate` | 68 (28) | 0.1267 | 0.5228 | -0.3961 | [-0.4767, -0.2703] | 66 / 2 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 HitMiss | `base_rate` | 68 (28) | 0.0294 | 0.0294 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D3 Brier | `base_always_ceiling` | 68 (28) | 0.1245 | 0.1324 | -0.0078 | [-0.0234, +0.0041] | 9 / 59 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_always_ceiling` | 68 (28) | 0.6591 | 1.8285 | -1.1695 | [-2.1862, -0.4021] | 9 / 59 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `base_rate` | 68 (28) | 0.1245 | 0.1184 | +0.0061 | [-0.0193, +0.0379] | 55 / 13 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_rate` | 68 (28) | 0.6591 | 0.4034 | +0.2557 | [-0.0996, +0.8079] | 55 / 13 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_last10_rate` | 68 (28) | 0.1245 | 0.2500 | -0.1255 | [-0.2016, -0.0302] | 59 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_last10_rate` | 68 (28) | 0.6591 | 0.6931 | -0.0341 | [-0.4943, +0.6423] | 59 / 9 / 0 | ayırt edilemiyor |
| p_up D3 HitMiss | `base_rate` | 68 (28) | 0.1324 | 0.1324 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D5 Brier | `base_always_ceiling` | 68 (28) | 0.1496 | 0.1618 | -0.0121 | [-0.0390, +0.0080] | 11 / 57 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_always_ceiling` | 68 (28) | 0.7872 | 2.2349 | -1.4477 | [-2.6254, -0.5642] | 11 / 57 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_rate` | 68 (28) | 0.1496 | 0.1393 | +0.0104 | [-0.0189, +0.0456] | 54 / 14 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_rate` | 68 (28) | 0.7872 | 0.4540 | +0.3332 | [-0.0452, +0.8642] | 54 / 14 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 68 (28) | 0.1496 | 0.3276 | -0.1780 | [-0.2779, -0.0571] | 57 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 68 (28) | 0.7872 | 0.8507 | -0.0635 | [-0.5840, +0.6239] | 57 / 11 / 0 | ayırt edilemiyor |
| p_up D5 HitMiss | `base_rate` | 68 (28) | 0.1618 | 0.1618 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D10 Brier | `base_always_ceiling` | 68 (28) | 0.1791 | 0.1912 | -0.0121 | [-0.0558, +0.0221] | 13 / 55 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_always_ceiling` | 68 (28) | 0.8056 | 2.6412 | -1.8356 | [-3.1268, -0.7959] | 13 / 55 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `base_rate` | 68 (28) | 0.1791 | 0.1650 | +0.0141 | [-0.0293, +0.0630] | 51 / 17 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 68 (28) | 0.8056 | 0.5151 | +0.2905 | [-0.0712, +0.7432] | 51 / 17 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_last10_rate` | 68 (28) | 0.1791 | 0.2500 | -0.0709 | [-0.1520, +0.0212] | 53 / 15 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_last10_rate` | 68 (28) | 0.8056 | 0.6931 | +0.1124 | [-0.3240, +0.6499] | 53 / 15 / 0 | ayırt edilemiyor |
| p_up D10 HitMiss | `base_rate` | 68 (28) | 0.2206 | 0.1912 | +0.0294 | [+0.0000, +0.0725] | 0 / 2 / 66 | ayırt edilemiyor |

### `v1_6_h99` (keşif)

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| return D1 MAE | `v1_5_h99` | 68 (28) | 0.0128 | 0.0128 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| return D1 MAE | `base_always_ceiling` | 68 (28) | 0.0128 | 0.0096 | +0.0033 | [-0.0007, +0.0070] | 8 / 26 / 34 | ayırt edilemiyor |
| return D1 MAE | `base_train_median` | 68 (28) | 0.0128 | 0.0096 | +0.0033 | [-0.0007, +0.0070] | 8 / 26 / 34 | ayırt edilemiyor |
| return D1 MAE | `base_train_mean` | 68 (28) | 0.0128 | 0.0256 | -0.0128 | [-0.0161, -0.0092] | 56 / 12 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_zero` | 68 (28) | 0.0128 | 0.0905 | -0.0777 | [-0.0885, -0.0635] | 62 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 DirMiss | `base_always_ceiling` | 68 (28) | 0.0294 | 0.0294 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| return D3 MAE | `v1_5_h99` | 68 (28) | 0.1090 | 0.1090 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| return D3 MAE | `base_always_ceiling` | 68 (28) | 0.1090 | 0.1027 | +0.0063 | [-0.0155, +0.0287] | 13 / 16 / 39 | ayırt edilemiyor |
| return D3 MAE | `base_train_median` | 68 (28) | 0.1090 | 0.1020 | +0.0070 | [-0.0147, +0.0295] | 25 / 43 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_train_mean` | 68 (28) | 0.1090 | 0.1335 | -0.0245 | [-0.0508, +0.0017] | 40 / 28 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_zero` | 68 (28) | 0.1090 | 0.2396 | -0.1307 | [-0.1952, -0.0581] | 48 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 DirMiss | `base_always_ceiling` | 68 (28) | 0.1324 | 0.1324 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| return D5 MAE | `v1_5_h99` | 68 (28) | 0.2306 | 0.2306 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| return D5 MAE | `base_always_ceiling` | 68 (28) | 0.2306 | 0.2451 | -0.0144 | [-0.0711, +0.0445] | 21 / 15 / 32 | ayırt edilemiyor |
| return D5 MAE | `base_train_median` | 68 (28) | 0.2306 | 0.2588 | -0.0282 | [-0.0807, +0.0225] | 36 / 32 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_train_mean` | 68 (28) | 0.2306 | 0.2684 | -0.0378 | [-0.1010, +0.0241] | 36 / 32 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_zero` | 68 (28) | 0.2306 | 0.3797 | -0.1491 | [-0.2742, -0.0166] | 42 / 26 / 0 | geçiyor (zaman-dışı terazide) |
| return D5 DirMiss | `base_always_ceiling` | 68 (28) | 0.1618 | 0.1618 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| return D10 MAE | `base_always_ceiling` | 68 (28) | 0.7472 | 1.0428 | -0.2956 | [-0.4435, -0.1587] | 46 / 7 / 15 | geçiyor (zaman-dışı terazide) |
| return D10 MAE | `base_train_median` | 68 (28) | 0.7472 | 0.4927 | +0.2545 | [+0.0257, +0.4569] | 21 / 47 / 0 | geçemiyor |
| return D10 MAE | `base_train_mean` | 68 (28) | 0.7472 | 0.4779 | +0.2693 | [+0.0775, +0.4398] | 21 / 47 / 0 | geçemiyor |
| return D10 MAE | `base_zero` | 68 (28) | 0.7472 | 0.5748 | +0.1725 | [-0.0987, +0.4213] | 29 / 39 / 0 | ayırt edilemiyor |
| return D10 DirMiss | `base_always_ceiling` | 68 (28) | 0.1912 | 0.1912 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D1 Brier | `v1_5_h99` | 68 (28) | 0.0287 | 0.0287 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D1 LogLoss | `v1_5_h99` | 68 (28) | 0.1267 | 0.1267 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D1 Brier | `base_always_ceiling` | 68 (28) | 0.0287 | 0.0294 | -0.0007 | [-0.0057, +0.0026] | 2 / 66 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_always_ceiling` | 68 (28) | 0.1267 | 0.4063 | -0.2796 | [-0.7934, +0.0422] | 2 / 66 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_rate` | 68 (28) | 0.0287 | 0.0337 | -0.0050 | [-0.0084, +0.0002] | 63 / 5 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_rate` | 68 (28) | 0.1267 | 0.1708 | -0.0441 | [-0.0725, -0.0015] | 63 / 5 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_last10_rate` | 68 (28) | 0.0287 | 0.1659 | -0.1372 | [-0.1582, -0.1034] | 66 / 2 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_last10_rate` | 68 (28) | 0.1267 | 0.5228 | -0.3961 | [-0.4767, -0.2703] | 66 / 2 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 HitMiss | `base_rate` | 68 (28) | 0.0294 | 0.0294 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D3 Brier | `v1_5_h99` | 68 (28) | 0.1245 | 0.1245 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D3 LogLoss | `v1_5_h99` | 68 (28) | 0.6591 | 0.6591 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D3 Brier | `base_always_ceiling` | 68 (28) | 0.1245 | 0.1324 | -0.0078 | [-0.0234, +0.0041] | 9 / 59 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_always_ceiling` | 68 (28) | 0.6591 | 1.8285 | -1.1695 | [-2.1862, -0.4021] | 9 / 59 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `base_rate` | 68 (28) | 0.1245 | 0.1184 | +0.0061 | [-0.0193, +0.0379] | 55 / 13 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_rate` | 68 (28) | 0.6591 | 0.4034 | +0.2557 | [-0.0996, +0.8079] | 55 / 13 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_last10_rate` | 68 (28) | 0.1245 | 0.2500 | -0.1255 | [-0.2016, -0.0302] | 59 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_last10_rate` | 68 (28) | 0.6591 | 0.6931 | -0.0341 | [-0.4943, +0.6423] | 59 / 9 / 0 | ayırt edilemiyor |
| p_up D3 HitMiss | `base_rate` | 68 (28) | 0.1324 | 0.1324 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D5 Brier | `v1_5_h99` | 68 (28) | 0.1496 | 0.1496 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D5 LogLoss | `v1_5_h99` | 68 (28) | 0.7872 | 0.7872 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D5 Brier | `base_always_ceiling` | 68 (28) | 0.1496 | 0.1618 | -0.0121 | [-0.0390, +0.0080] | 11 / 57 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_always_ceiling` | 68 (28) | 0.7872 | 2.2349 | -1.4477 | [-2.6254, -0.5642] | 11 / 57 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_rate` | 68 (28) | 0.1496 | 0.1393 | +0.0104 | [-0.0189, +0.0456] | 54 / 14 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_rate` | 68 (28) | 0.7872 | 0.4540 | +0.3332 | [-0.0452, +0.8642] | 54 / 14 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 68 (28) | 0.1496 | 0.3276 | -0.1780 | [-0.2779, -0.0571] | 57 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 68 (28) | 0.7872 | 0.8507 | -0.0635 | [-0.5840, +0.6239] | 57 / 11 / 0 | ayırt edilemiyor |
| p_up D5 HitMiss | `base_rate` | 68 (28) | 0.1618 | 0.1618 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D10 Brier | `v1_5_h99` | 68 (28) | 0.1791 | 0.1791 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D10 LogLoss | `v1_5_h99` | 68 (28) | 0.8056 | 0.8056 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D10 Brier | `base_always_ceiling` | 68 (28) | 0.1791 | 0.1912 | -0.0121 | [-0.0558, +0.0221] | 13 / 55 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_always_ceiling` | 68 (28) | 0.8056 | 2.6412 | -1.8356 | [-3.1268, -0.7959] | 13 / 55 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `base_rate` | 68 (28) | 0.1791 | 0.1650 | +0.0141 | [-0.0293, +0.0630] | 51 / 17 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 68 (28) | 0.8056 | 0.5151 | +0.2905 | [-0.0712, +0.7432] | 51 / 17 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_last10_rate` | 68 (28) | 0.1791 | 0.2500 | -0.0709 | [-0.1520, +0.0212] | 53 / 15 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_last10_rate` | 68 (28) | 0.8056 | 0.6931 | +0.1124 | [-0.3240, +0.6499] | 53 / 15 / 0 | ayırt edilemiyor |
| p_up D10 HitMiss | `base_rate` | 68 (28) | 0.2206 | 0.1912 | +0.0294 | [+0.0000, +0.0725] | 0 / 2 / 66 | ayırt edilemiyor |

### `v1_5_market20_v0` (keşif)

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| return D1 MAE | `v1_5_h99` | 68 (28) | 0.0120 | 0.0128 | -0.0008 | [-0.0021, +0.0003] | 19 / 16 / 33 | ayırt edilemiyor |
| return D1 MAE | `base_always_ceiling` | 68 (28) | 0.0120 | 0.0096 | +0.0024 | [-0.0011, +0.0057] | 8 / 24 / 36 | ayırt edilemiyor |
| return D1 MAE | `base_train_median` | 68 (28) | 0.0120 | 0.0096 | +0.0024 | [-0.0011, +0.0057] | 8 / 24 / 36 | ayırt edilemiyor |
| return D1 MAE | `base_train_mean` | 68 (28) | 0.0120 | 0.0256 | -0.0136 | [-0.0164, -0.0104] | 58 / 10 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_zero` | 68 (28) | 0.0120 | 0.0905 | -0.0785 | [-0.0891, -0.0643] | 62 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 DirMiss | `base_always_ceiling` | 68 (28) | 0.0294 | 0.0294 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| return D3 MAE | `v1_5_h99` | 68 (28) | 0.1083 | 0.1090 | -0.0006 | [-0.0018, +0.0004] | 15 / 14 / 39 | ayırt edilemiyor |
| return D3 MAE | `base_always_ceiling` | 68 (28) | 0.1083 | 0.1027 | +0.0056 | [-0.0158, +0.0276] | 13 / 16 / 39 | ayırt edilemiyor |
| return D3 MAE | `base_train_median` | 68 (28) | 0.1083 | 0.1020 | +0.0064 | [-0.0150, +0.0285] | 24 / 44 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_train_mean` | 68 (28) | 0.1083 | 0.1335 | -0.0251 | [-0.0510, +0.0007] | 42 / 26 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_zero` | 68 (28) | 0.1083 | 0.2396 | -0.1313 | [-0.1958, -0.0588] | 48 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 DirMiss | `base_always_ceiling` | 68 (28) | 0.1324 | 0.1324 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| return D5 MAE | `base_always_ceiling` | 68 (28) | 0.2288 | 0.2451 | -0.0163 | [-0.0694, +0.0378] | 21 / 13 / 34 | ayırt edilemiyor |
| return D5 MAE | `base_train_median` | 68 (28) | 0.2288 | 0.2588 | -0.0300 | [-0.0809, +0.0180] | 35 / 33 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_train_mean` | 68 (28) | 0.2288 | 0.2684 | -0.0396 | [-0.1018, +0.0200] | 33 / 35 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_zero` | 68 (28) | 0.2288 | 0.3797 | -0.1509 | [-0.2782, -0.0191] | 42 / 26 / 0 | geçiyor (zaman-dışı terazide) |
| return D5 DirMiss | `base_always_ceiling` | 68 (28) | 0.1618 | 0.1618 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| return D10 MAE | `v1_5_h99` | 68 (28) | 0.7390 | 0.7468 | -0.0078 | [-0.0326, +0.0194] | 29 / 25 / 14 | ayırt edilemiyor |
| return D10 MAE | `base_always_ceiling` | 68 (28) | 0.7390 | 1.0428 | -0.3038 | [-0.4467, -0.1773] | 44 / 6 / 18 | geçiyor (zaman-dışı terazide) |
| return D10 MAE | `base_train_median` | 68 (28) | 0.7390 | 0.4927 | +0.2463 | [+0.0204, +0.4461] | 25 / 43 / 0 | geçemiyor |
| return D10 MAE | `base_train_mean` | 68 (28) | 0.7390 | 0.4779 | +0.2611 | [+0.0748, +0.4253] | 19 / 49 / 0 | geçemiyor |
| return D10 MAE | `base_zero` | 68 (28) | 0.7390 | 0.5748 | +0.1643 | [-0.1017, +0.4108] | 28 / 40 / 0 | ayırt edilemiyor |
| return D10 DirMiss | `base_always_ceiling` | 68 (28) | 0.1912 | 0.1912 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D1 Brier | `v1_5_h99` | 68 (28) | 0.0280 | 0.0287 | -0.0007 | [-0.0015, -0.0000] | 39 / 29 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `v1_5_h99` | 68 (28) | 0.1215 | 0.1267 | -0.0052 | [-0.0117, +0.0001] | 39 / 29 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_always_ceiling` | 68 (28) | 0.0280 | 0.0294 | -0.0014 | [-0.0068, +0.0020] | 2 / 66 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_always_ceiling` | 68 (28) | 0.1215 | 0.4063 | -0.2848 | [-0.8010, +0.0371] | 2 / 66 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_rate` | 68 (28) | 0.0280 | 0.0337 | -0.0057 | [-0.0088, -0.0006] | 65 / 3 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_rate` | 68 (28) | 0.1215 | 0.1708 | -0.0493 | [-0.0758, -0.0052] | 65 / 3 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_last10_rate` | 68 (28) | 0.0280 | 0.1659 | -0.1379 | [-0.1586, -0.1042] | 66 / 2 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_last10_rate` | 68 (28) | 0.1215 | 0.5228 | -0.4012 | [-0.4802, -0.2762] | 66 / 2 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 HitMiss | `base_rate` | 68 (28) | 0.0294 | 0.0294 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D3 Brier | `v1_5_h99` | 68 (28) | 0.1259 | 0.1245 | +0.0014 | [-0.0084, +0.0095] | 49 / 19 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `v1_5_h99` | 68 (28) | 0.7566 | 0.6591 | +0.0976 | [-0.0016, +0.2460] | 49 / 19 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_always_ceiling` | 68 (28) | 0.1259 | 0.1324 | -0.0065 | [-0.0286, +0.0110] | 9 / 59 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_always_ceiling` | 68 (28) | 0.7566 | 1.8285 | -1.0719 | [-2.0699, -0.3344] | 9 / 59 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `base_rate` | 68 (28) | 0.1259 | 0.1184 | +0.0075 | [-0.0204, +0.0417] | 56 / 12 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_rate` | 68 (28) | 0.7566 | 0.4034 | +0.3533 | [-0.0916, +1.0508] | 56 / 12 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_last10_rate` | 68 (28) | 0.1259 | 0.2500 | -0.1241 | [-0.1995, -0.0291] | 59 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_last10_rate` | 68 (28) | 0.7566 | 0.6931 | +0.0635 | [-0.4862, +0.8823] | 59 / 9 / 0 | ayırt edilemiyor |
| p_up D3 HitMiss | `base_rate` | 68 (28) | 0.1324 | 0.1324 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D5 Brier | `v1_5_h99` | 68 (28) | 0.1493 | 0.1496 | -0.0004 | [-0.0028, +0.0024] | 39 / 29 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `v1_5_h99` | 68 (28) | 0.7830 | 0.7872 | -0.0041 | [-0.0153, +0.0080] | 39 / 29 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_always_ceiling` | 68 (28) | 0.1493 | 0.1618 | -0.0125 | [-0.0387, +0.0066] | 11 / 57 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_always_ceiling` | 68 (28) | 0.7830 | 2.2349 | -1.4518 | [-2.6306, -0.5692] | 11 / 57 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_rate` | 68 (28) | 0.1493 | 0.1393 | +0.0100 | [-0.0194, +0.0453] | 54 / 14 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_rate` | 68 (28) | 0.7830 | 0.4540 | +0.3291 | [-0.0485, +0.8608] | 54 / 14 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 68 (28) | 0.1493 | 0.3276 | -0.1784 | [-0.2787, -0.0572] | 57 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 68 (28) | 0.7830 | 0.8507 | -0.0677 | [-0.5906, +0.6227] | 57 / 11 / 0 | ayırt edilemiyor |
| p_up D5 HitMiss | `base_rate` | 68 (28) | 0.1618 | 0.1618 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 68 | ayırt edilemiyor |
| p_up D10 Brier | `v1_5_h99` | 68 (28) | 0.1869 | 0.1791 | +0.0078 | [-0.0074, +0.0249] | 30 / 38 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `v1_5_h99` | 68 (28) | 0.8463 | 0.8056 | +0.0407 | [-0.0082, +0.0910] | 30 / 38 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_always_ceiling` | 68 (28) | 0.1869 | 0.1912 | -0.0042 | [-0.0557, +0.0421] | 13 / 55 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_always_ceiling` | 68 (28) | 0.8463 | 2.6412 | -1.7949 | [-3.0788, -0.7588] | 13 / 55 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `base_rate` | 68 (28) | 0.1869 | 0.1650 | +0.0219 | [-0.0275, +0.0750] | 50 / 18 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 68 (28) | 0.8463 | 0.5151 | +0.3312 | [-0.0455, +0.7924] | 50 / 18 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_last10_rate` | 68 (28) | 0.1869 | 0.2500 | -0.0631 | [-0.1458, +0.0312] | 53 / 15 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_last10_rate` | 68 (28) | 0.8463 | 0.6931 | +0.1531 | [-0.2935, +0.6893] | 53 / 15 / 0 | ayırt edilemiyor |
| p_up D10 HitMiss | `base_rate` | 68 (28) | 0.2206 | 0.1912 | +0.0294 | [-0.0303, +0.1077] | 1 / 3 / 64 | ayırt edilemiyor |

### `pb_v0` (keşif)

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| return D1 MAE | `v1_5_h99` | 56 (26) | 0.0111 | 0.0113 | -0.0002 | [-0.0028, +0.0024] | 17 / 14 / 25 | ayırt edilemiyor |
| return D1 MAE | `base_always_ceiling` | 59 (28) | 0.0105 | 0.0063 | +0.0042 | [+0.0006, +0.0083] | 4 / 16 / 39 | geçemiyor |
| return D1 MAE | `base_train_median` | 59 (28) | 0.0105 | 0.0063 | +0.0042 | [+0.0006, +0.0083] | 4 / 16 / 39 | geçemiyor |
| return D1 MAE | `base_train_mean` | 59 (28) | 0.0105 | 0.0247 | -0.0141 | [-0.0179, -0.0102] | 47 / 12 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_zero` | 59 (28) | 0.0105 | 0.0937 | -0.0831 | [-0.0933, -0.0699] | 55 / 4 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 DirMiss | `base_always_ceiling` | 59 (28) | 0.0169 | 0.0169 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 59 | ayırt edilemiyor |
| return D3 MAE | `v1_5_h99` | 56 (26) | 0.1045 | 0.0984 | +0.0061 | [-0.0043, +0.0175] | 10 / 20 / 26 | ayırt edilemiyor |
| return D3 MAE | `base_always_ceiling` | 59 (28) | 0.0993 | 0.0779 | +0.0214 | [+0.0015, +0.0435] | 7 / 18 / 34 | geçemiyor |
| return D3 MAE | `base_train_median` | 59 (28) | 0.0993 | 0.0772 | +0.0221 | [+0.0022, +0.0442] | 17 / 42 / 0 | geçemiyor |
| return D3 MAE | `base_train_mean` | 59 (28) | 0.0993 | 0.1317 | -0.0324 | [-0.0576, -0.0068] | 36 / 23 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_zero` | 59 (28) | 0.0993 | 0.2656 | -0.1662 | [-0.2257, -0.0980] | 44 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 DirMiss | `base_always_ceiling` | 59 (28) | 0.1017 | 0.1017 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 59 | ayırt edilemiyor |
| return D5 MAE | `v1_5_h99` | 56 (26) | 0.2524 | 0.2090 | +0.0434 | [+0.0257, +0.0641] | 9 / 27 / 20 | geçemiyor |
| return D5 MAE | `base_always_ceiling` | 59 (28) | 0.2398 | 0.1965 | +0.0433 | [-0.0100, +0.1019] | 12 / 17 / 30 | ayırt edilemiyor |
| return D5 MAE | `base_train_mean` | 59 (28) | 0.2398 | 0.2680 | -0.0282 | [-0.0834, +0.0254] | 30 / 29 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_zero` | 59 (28) | 0.2398 | 0.4234 | -0.1835 | [-0.2890, -0.0697] | 41 / 18 / 0 | geçiyor (zaman-dışı terazide) |
| return D5 DirMiss | `base_always_ceiling` | 59 (28) | 0.1017 | 0.1017 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 59 | ayırt edilemiyor |
| return D10 MAE | `v1_5_h99` | 56 (26) | 0.7432 | 0.7207 | +0.0224 | [-0.0519, +0.0977] | 22 / 33 / 1 | ayırt edilemiyor |
| return D10 MAE | `base_always_ceiling` | 59 (28) | 0.7188 | 0.9373 | -0.2185 | [-0.3443, -0.0874] | 45 / 11 / 3 | geçiyor (zaman-dışı terazide) |
| return D10 MAE | `base_train_median` | 59 (28) | 0.7188 | 0.5601 | +0.1587 | [-0.0642, +0.3656] | 27 / 32 / 0 | ayırt edilemiyor |
| return D10 MAE | `base_train_mean` | 59 (28) | 0.7188 | 0.5125 | +0.2063 | [+0.0308, +0.3722] | 18 / 41 / 0 | geçemiyor |
| return D10 MAE | `base_zero` | 59 (28) | 0.7188 | 0.6742 | +0.0446 | [-0.2158, +0.2939] | 29 / 30 / 0 | ayırt edilemiyor |
| return D10 DirMiss | `base_always_ceiling` | 59 (28) | 0.1356 | 0.1356 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 59 | ayırt edilemiyor |
| p_up D1 Brier | `v1_5_h99` | 56 (26) | 0.0190 | 0.0179 | +0.0011 | [+0.0002, +0.0021] | 19 / 37 / 0 | geçemiyor |
| p_up D1 LogLoss | `v1_5_h99` | 56 (26) | 0.0981 | 0.0875 | +0.0106 | [+0.0039, +0.0183] | 19 / 37 / 0 | geçemiyor |
| p_up D1 Brier | `base_always_ceiling` | 59 (28) | 0.0180 | 0.0169 | +0.0011 | [-0.0038, +0.0042] | 1 / 58 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_always_ceiling` | 59 (28) | 0.0937 | 0.2342 | -0.1405 | [-0.5737, +0.0552] | 1 / 58 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_rate` | 59 (28) | 0.0180 | 0.0237 | -0.0057 | [-0.0083, -0.0018] | 53 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_rate` | 59 (28) | 0.0937 | 0.1435 | -0.0499 | [-0.0698, -0.0211] | 53 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_last10_rate` | 59 (28) | 0.0180 | 0.1634 | -0.1454 | [-0.1581, -0.1184] | 58 / 1 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_last10_rate` | 59 (28) | 0.0937 | 0.5177 | -0.4240 | [-0.4741, -0.3264] | 58 / 1 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 HitMiss | `base_rate` | 59 (28) | 0.0169 | 0.0169 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 59 | ayırt edilemiyor |
| p_up D3 Brier | `v1_5_h99` | 56 (26) | 0.1037 | 0.1049 | -0.0012 | [-0.0096, +0.0055] | 10 / 46 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `v1_5_h99` | 56 (26) | 0.4026 | 0.6508 | -0.2482 | [-0.7356, +0.0327] | 10 / 46 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_always_ceiling` | 59 (28) | 0.0984 | 0.1017 | -0.0033 | [-0.0174, +0.0090] | 6 / 53 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_always_ceiling` | 59 (28) | 0.3827 | 1.4050 | -1.0223 | [-2.0219, -0.2600] | 6 / 53 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `base_rate` | 59 (28) | 0.0984 | 0.0995 | -0.0011 | [-0.0215, +0.0272] | 47 / 12 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_rate` | 59 (28) | 0.3827 | 0.3593 | +0.0234 | [-0.1102, +0.2355] | 47 / 12 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_last10_rate` | 59 (28) | 0.0984 | 0.2500 | -0.1516 | [-0.2150, -0.0665] | 53 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_last10_rate` | 59 (28) | 0.3827 | 0.6931 | -0.3104 | [-0.5464, +0.0258] | 53 / 6 / 0 | ayırt edilemiyor |
| p_up D3 HitMiss | `base_rate` | 59 (28) | 0.1017 | 0.1017 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 59 | ayırt edilemiyor |
| p_up D5 Brier | `v1_5_h99` | 56 (26) | 0.1049 | 0.1062 | -0.0013 | [-0.0120, +0.0073] | 11 / 45 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `v1_5_h99` | 56 (26) | 0.3966 | 0.6462 | -0.2496 | [-0.6960, +0.0402] | 11 / 45 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_always_ceiling` | 59 (28) | 0.0996 | 0.1017 | -0.0021 | [-0.0211, +0.0134] | 6 / 53 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_always_ceiling` | 59 (28) | 0.3774 | 1.4050 | -1.0276 | [-2.1443, -0.2177] | 6 / 53 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_rate` | 59 (28) | 0.0996 | 0.1059 | -0.0063 | [-0.0297, +0.0274] | 47 / 12 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_rate` | 59 (28) | 0.3774 | 0.3787 | -0.0013 | [-0.1300, +0.2030] | 47 / 12 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 59 (28) | 0.0996 | 0.3397 | -0.2401 | [-0.3187, -0.1302] | 53 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 59 (28) | 0.3774 | 0.8751 | -0.4977 | [-0.7445, -0.1314] | 53 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 HitMiss | `base_rate` | 59 (28) | 0.1017 | 0.1017 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 59 | ayırt edilemiyor |
| p_up D10 Brier | `v1_5_h99` | 56 (26) | 0.1387 | 0.1481 | -0.0094 | [-0.0248, +0.0062] | 15 / 41 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `v1_5_h99` | 56 (26) | 0.4723 | 0.7207 | -0.2483 | [-0.6050, +0.0127] | 15 / 41 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_always_ceiling` | 59 (28) | 0.1317 | 0.1356 | -0.0039 | [-0.0325, +0.0226] | 8 / 51 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_always_ceiling` | 59 (28) | 0.4501 | 1.8733 | -1.4232 | [-2.5509, -0.4699] | 8 / 51 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `base_rate` | 59 (28) | 0.1317 | 0.1420 | -0.0103 | [-0.0429, +0.0295] | 45 / 14 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 59 (28) | 0.4501 | 0.4661 | -0.0160 | [-0.1465, +0.1580] | 45 / 14 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_last10_rate` | 59 (28) | 0.1317 | 0.2500 | -0.1183 | [-0.1830, -0.0393] | 51 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_last10_rate` | 59 (28) | 0.4501 | 0.6931 | -0.2430 | [-0.4392, +0.0110] | 51 / 8 / 0 | ayırt edilemiyor |
| p_up D10 HitMiss | `base_rate` | 59 (28) | 0.1356 | 0.1356 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 59 | ayırt edilemiyor |

### `ceiling_hazard_v0` (keşif)

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| S RPS | `ceiling_hazard_v0@INF` | 68 (28) | 0.2689 | 0.1999 | +0.0689 | [+0.0019, +0.1305] | 25 / 43 / 0 | geçemiyor |
| S RPS | `base_km_last10` | 68 (28) | 0.2689 | 0.2649 | +0.0040 | [-0.0993, +0.1025] | 36 / 32 / 0 | ayırt edilemiyor |
| S RPS | `base_always_ceiling` | 68 (28) | 0.2689 | 0.5368 | -0.2679 | [-0.3608, -0.1777] | 57 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| S 1 Brier | `ceiling_hazard_v0@INF` | 68 (28) | 0.1071 | 0.1161 | -0.0091 | [-0.0197, +0.0043] | 57 / 11 / 0 | ayırt edilemiyor |
| S 1 Brier | `base_km_expanding` | 68 (28) | 0.1071 | 0.1173 | -0.0102 | [-0.0225, +0.0054] | 55 / 13 / 0 | ayırt edilemiyor |
| S 1 Brier | `base_km_last10` | 68 (28) | 0.1071 | 0.2500 | -0.1429 | [-0.2065, -0.0594] | 59 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| S 1 Brier | `base_always_ceiling` | 68 (28) | 0.1071 | 0.1324 | -0.0253 | [-0.0549, -0.0031] | 9 / 59 / 0 | geçiyor (zaman-dışı terazide) |
| S 3 Brier | `ceiling_hazard_v0@INF` | 68 (28) | 0.2847 | 0.2340 | +0.0508 | [-0.0057, +0.1105] | 42 / 26 / 0 | ayırt edilemiyor |
| S 3 Brier | `base_km_expanding` | 68 (28) | 0.2847 | 0.2337 | +0.0511 | [-0.0063, +0.1118] | 44 / 24 / 0 | ayırt edilemiyor |
| S 3 Brier | `base_km_last10` | 68 (28) | 0.2847 | 0.3300 | -0.0453 | [-0.1893, +0.1047] | 43 / 25 / 0 | ayırt edilemiyor |
| S 3 Brier | `base_always_ceiling` | 68 (28) | 0.2847 | 0.3676 | -0.0829 | [-0.1454, -0.0272] | 25 / 43 / 0 | geçiyor (zaman-dışı terazide) |
| S 5 Brier | `ceiling_hazard_v0@INF` | 68 (28) | 0.2741 | 0.2598 | +0.0143 | [-0.0765, +0.1028] | 38 / 30 / 0 | ayırt edilemiyor |
| S 5 Brier | `base_km_expanding` | 68 (28) | 0.2741 | 0.2624 | +0.0117 | [-0.0813, +0.1022] | 40 / 28 / 0 | ayırt edilemiyor |
| S 5 Brier | `base_km_last10` | 68 (28) | 0.2741 | 0.3545 | -0.0804 | [-0.2225, +0.0640] | 34 / 34 / 0 | ayırt edilemiyor |
| S 5 Brier | `base_always_ceiling` | 68 (28) | 0.2741 | 0.4706 | -0.1965 | [-0.3397, -0.0564] | 32 / 36 / 0 | geçiyor (zaman-dışı terazide) |
| S 10 Brier | `ceiling_hazard_v0@INF` | 68 (28) | 0.3025 | 0.1149 | +0.1876 | [+0.0985, +0.2762] | 17 / 51 / 0 | geçemiyor |
| S 10 Brier | `base_km_expanding` | 68 (28) | 0.3025 | 0.1149 | +0.1876 | [+0.0987, +0.2757] | 17 / 51 / 0 | geçemiyor |
| S 10 Brier | `base_km_last10` | 68 (28) | 0.3025 | 0.1203 | +0.1822 | [+0.0836, +0.2799] | 13 / 55 / 0 | geçemiyor |
| S 10 Brier | `base_always_ceiling` | 68 (28) | 0.3025 | 0.8676 | -0.5652 | [-0.6891, -0.4385] | 59 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `ceiling_hazard_v0@INF` | 68 (28) | 0.1071 | 0.1161 | -0.0091 | [-0.0197, +0.0043] | 57 / 11 / 0 | ayırt edilemiyor |
| P_close_ceiling 1 Brier | `base_km_expanding` | 68 (28) | 0.1071 | 0.1173 | -0.0102 | [-0.0225, +0.0054] | 55 / 13 / 0 | ayırt edilemiyor |
| P_close_ceiling 1 Brier | `base_km_last10` | 68 (28) | 0.1071 | 0.2500 | -0.1429 | [-0.2065, -0.0594] | 59 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `base_always_ceiling` | 68 (28) | 0.1071 | 0.1324 | -0.0253 | [-0.0549, -0.0031] | 9 / 59 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `v1_5_p_up_as_ceiling` | 68 (28) | 0.1071 | 0.1183 | -0.0112 | [-0.0261, +0.0006] | 15 / 53 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `ceiling_hazard_v0@INF` | 68 (28) | 0.2639 | 0.2189 | +0.0451 | [-0.0062, +0.1036] | 41 / 27 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `base_km_expanding` | 68 (28) | 0.2639 | 0.2189 | +0.0450 | [-0.0065, +0.1039] | 41 / 27 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `base_km_last10` | 68 (28) | 0.2639 | 0.3351 | -0.0711 | [-0.2074, +0.0777] | 46 / 22 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `base_always_ceiling` | 68 (28) | 0.2639 | 0.3235 | -0.0596 | [-0.1177, -0.0086] | 22 / 46 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 3 Brier | `v1_5_p_up_as_ceiling` | 68 (28) | 0.2639 | 0.3071 | -0.0432 | [-0.0861, -0.0057] | 22 / 46 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 5 Brier | `ceiling_hazard_v0@INF` | 68 (28) | 0.2711 | 0.2493 | +0.0217 | [-0.0512, +0.0987] | 39 / 29 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `base_km_expanding` | 68 (28) | 0.2711 | 0.2504 | +0.0207 | [-0.0542, +0.0997] | 41 / 27 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `base_km_last10` | 68 (28) | 0.2711 | 0.3003 | -0.0293 | [-0.1464, +0.0951] | 35 / 33 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `base_always_ceiling` | 68 (28) | 0.2711 | 0.4559 | -0.1848 | [-0.3075, -0.0681] | 31 / 37 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 5 Brier | `v1_5_p_up_as_ceiling` | 68 (28) | 0.2711 | 0.3973 | -0.1262 | [-0.2163, -0.0378] | 31 / 37 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 10 Brier | `ceiling_hazard_v0@INF` | 68 (28) | 0.3180 | 0.1665 | +0.1515 | [+0.0785, +0.2239] | 20 / 48 / 0 | geçemiyor |
| P_close_ceiling 10 Brier | `base_km_expanding` | 68 (28) | 0.3180 | 0.1665 | +0.1515 | [+0.0785, +0.2238] | 20 / 48 / 0 | geçemiyor |
| P_close_ceiling 10 Brier | `base_km_last10` | 68 (28) | 0.3180 | 0.1638 | +0.1543 | [+0.0736, +0.2345] | 15 / 53 / 0 | geçemiyor |
| P_close_ceiling 10 Brier | `base_always_ceiling` | 68 (28) | 0.3180 | 0.7941 | -0.4761 | [-0.6136, -0.3305] | 54 / 14 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 10 Brier | `v1_5_p_up_as_ceiling` | 68 (28) | 0.3180 | 0.6863 | -0.3682 | [-0.4702, -0.2545] | 54 / 14 / 0 | geçiyor (zaman-dışı terazide) |

### `pb_ceiling_v0` (keşif)

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| S RPS | `pb_ceiling_v0@INF` | 59 (28) | 0.2525 | 0.2052 | +0.0473 | [-0.0057, +0.0999] | 22 / 37 / 0 | ayırt edilemiyor |
| S RPS | `base_km_last10` | 59 (28) | 0.2525 | 0.2984 | -0.0459 | [-0.1343, +0.0416] | 36 / 23 / 0 | ayırt edilemiyor |
| S RPS | `base_always_ceiling` | 59 (28) | 0.2525 | 0.4729 | -0.2203 | [-0.3054, -0.1307] | 49 / 10 / 0 | geçiyor (zaman-dışı terazide) |
| S 1 Brier | `pb_ceiling_v0@INF` | 59 (28) | 0.0769 | 0.0876 | -0.0108 | [-0.0221, +0.0031] | 48 / 11 / 0 | ayırt edilemiyor |
| S 1 Brier | `base_km_expanding` | 59 (28) | 0.0769 | 0.0870 | -0.0101 | [-0.0211, +0.0034] | 48 / 11 / 0 | ayırt edilemiyor |
| S 1 Brier | `base_km_last10` | 59 (28) | 0.0769 | 0.2500 | -0.1731 | [-0.2264, -0.1039] | 54 / 5 / 0 | geçiyor (zaman-dışı terazide) |
| S 1 Brier | `base_always_ceiling` | 59 (28) | 0.0769 | 0.0847 | -0.0079 | [-0.0319, +0.0102] | 5 / 54 / 0 | ayırt edilemiyor |
| S 3 Brier | `pb_ceiling_v0@INF` | 59 (28) | 0.2313 | 0.2028 | +0.0285 | [-0.0200, +0.0804] | 37 / 22 / 0 | ayırt edilemiyor |
| S 3 Brier | `base_km_expanding` | 59 (28) | 0.2313 | 0.2015 | +0.0298 | [-0.0169, +0.0797] | 36 / 23 / 0 | ayırt edilemiyor |
| S 3 Brier | `base_km_last10` | 59 (28) | 0.2313 | 0.3648 | -0.1335 | [-0.2573, +0.0044] | 43 / 16 / 0 | ayırt edilemiyor |
| S 3 Brier | `base_always_ceiling` | 59 (28) | 0.2313 | 0.2712 | -0.0399 | [-0.0951, +0.0090] | 16 / 43 / 0 | ayırt edilemiyor |
| S 5 Brier | `pb_ceiling_v0@INF` | 59 (28) | 0.2884 | 0.2749 | +0.0136 | [-0.0608, +0.0860] | 28 / 31 / 0 | ayırt edilemiyor |
| S 5 Brier | `base_km_expanding` | 59 (28) | 0.2884 | 0.2763 | +0.0122 | [-0.0629, +0.0852] | 28 / 31 / 0 | ayırt edilemiyor |
| S 5 Brier | `base_km_last10` | 59 (28) | 0.2884 | 0.4022 | -0.1137 | [-0.2348, +0.0103] | 36 / 23 / 0 | ayırt edilemiyor |
| S 5 Brier | `base_always_ceiling` | 59 (28) | 0.2884 | 0.3898 | -0.1014 | [-0.2276, +0.0270] | 23 / 36 / 0 | ayırt edilemiyor |
| S 10 Brier | `pb_ceiling_v0@INF` | 59 (28) | 0.2760 | 0.1296 | +0.1464 | [+0.0657, +0.2311] | 9 / 50 / 0 | geçemiyor |
| S 10 Brier | `base_km_expanding` | 59 (28) | 0.2760 | 0.1294 | +0.1466 | [+0.0668, +0.2300] | 10 / 49 / 0 | geçemiyor |
| S 10 Brier | `base_km_last10` | 59 (28) | 0.2760 | 0.1381 | +0.1379 | [+0.0460, +0.2335] | 8 / 51 / 0 | geçemiyor |
| S 10 Brier | `base_always_ceiling` | 59 (28) | 0.2760 | 0.8475 | -0.5715 | [-0.7072, -0.4351] | 50 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `pb_ceiling_v0@INF` | 59 (28) | 0.0769 | 0.0876 | -0.0108 | [-0.0221, +0.0031] | 48 / 11 / 0 | ayırt edilemiyor |
| P_close_ceiling 1 Brier | `base_km_expanding` | 59 (28) | 0.0769 | 0.0870 | -0.0101 | [-0.0211, +0.0034] | 48 / 11 / 0 | ayırt edilemiyor |
| P_close_ceiling 1 Brier | `base_km_last10` | 59 (28) | 0.0769 | 0.2500 | -0.1731 | [-0.2264, -0.1039] | 54 / 5 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `base_always_ceiling` | 59 (28) | 0.0769 | 0.0847 | -0.0079 | [-0.0319, +0.0102] | 5 / 54 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `pb_ceiling_v0@INF` | 59 (28) | 0.2075 | 0.1905 | +0.0170 | [-0.0251, +0.0646] | 39 / 20 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `base_km_expanding` | 59 (28) | 0.2075 | 0.1888 | +0.0187 | [-0.0218, +0.0643] | 38 / 21 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `base_km_last10` | 59 (28) | 0.2075 | 0.3634 | -0.1559 | [-0.2668, -0.0297] | 45 / 14 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 3 Brier | `base_always_ceiling` | 59 (28) | 0.2075 | 0.2373 | -0.0298 | [-0.0806, +0.0158] | 14 / 45 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `pb_ceiling_v0@INF` | 59 (28) | 0.2720 | 0.2503 | +0.0217 | [-0.0394, +0.0843] | 29 / 30 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `base_km_expanding` | 59 (28) | 0.2720 | 0.2511 | +0.0209 | [-0.0406, +0.0841] | 29 / 30 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `base_km_last10` | 59 (28) | 0.2720 | 0.3310 | -0.0590 | [-0.1604, +0.0484] | 37 / 22 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `base_always_ceiling` | 59 (28) | 0.2720 | 0.3729 | -0.1009 | [-0.2058, +0.0036] | 22 / 37 / 0 | ayırt edilemiyor |
| P_close_ceiling 10 Brier | `pb_ceiling_v0@INF` | 59 (28) | 0.3072 | 0.1813 | +0.1259 | [+0.0569, +0.2017] | 12 / 47 / 0 | geçemiyor |
| P_close_ceiling 10 Brier | `base_km_expanding` | 59 (28) | 0.3072 | 0.1815 | +0.1257 | [+0.0580, +0.2007] | 13 / 46 / 0 | geçemiyor |
| P_close_ceiling 10 Brier | `base_km_last10` | 59 (28) | 0.3072 | 0.1832 | +0.1240 | [+0.0444, +0.2098] | 13 / 46 / 0 | geçemiyor |
| P_close_ceiling 10 Brier | `base_always_ceiling` | 59 (28) | 0.3072 | 0.7627 | -0.4555 | [-0.5908, -0.3025] | 45 / 14 / 0 | geçiyor (zaman-dışı terazide) |

### `ceiling_path_v0` (keşif)

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| return D1 MAE | `v1_5_h99` | 67 (28) | 0.0093 | 0.0128 | -0.0035 | [-0.0072, +0.0004] | 36 / 8 / 23 | ayırt edilemiyor |
| return D1 MAE | `ceiling_path_v0@INF` | 67 (28) | 0.0093 | 0.0093 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 67 | ayırt edilemiyor |
| return D1 MAE | `base_always_ceiling` | 67 (28) | 0.0093 | 0.0097 | -0.0004 | [-0.0006, -0.0002] | 26 / 0 / 41 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_train_median` | 67 (28) | 0.0093 | 0.0097 | -0.0004 | [-0.0006, -0.0002] | 26 / 0 / 41 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_train_mean` | 67 (28) | 0.0093 | 0.0257 | -0.0163 | [-0.0201, -0.0113] | 58 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_zero` | 67 (28) | 0.0093 | 0.0904 | -0.0810 | [-0.0935, -0.0642] | 59 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 DirMiss | `base_always_ceiling` | 67 (28) | 0.0299 | 0.0299 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 67 | ayırt edilemiyor |
| return D3 MAE | `v1_5_h99` | 67 (28) | 0.1027 | 0.1103 | -0.0076 | [-0.0307, +0.0141] | 53 / 13 / 1 | ayırt edilemiyor |
| return D3 MAE | `ceiling_path_v0@INF` | 67 (28) | 0.1027 | 0.1027 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 67 | ayırt edilemiyor |
| return D3 MAE | `base_always_ceiling` | 67 (28) | 0.1027 | 0.1042 | -0.0016 | [-0.0021, -0.0011] | 66 / 0 / 1 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_train_median` | 67 (28) | 0.1027 | 0.1035 | -0.0008 | [-0.0013, -0.0004] | 53 / 13 / 1 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_train_mean` | 67 (28) | 0.1027 | 0.1337 | -0.0310 | [-0.0636, +0.0029] | 42 / 25 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_zero` | 67 (28) | 0.1027 | 0.2383 | -0.1356 | [-0.2105, -0.0522] | 45 / 22 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 DirMiss | `base_always_ceiling` | 67 (28) | 0.1343 | 0.1343 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 67 | ayırt edilemiyor |
| return D5 MAE | `v1_5_h99` | 67 (28) | 0.2491 | 0.2322 | +0.0169 | [+0.0005, +0.0355] | 41 / 26 / 0 | geçemiyor |
| return D5 MAE | `ceiling_path_v0@INF` | 67 (28) | 0.2491 | 0.2609 | -0.0119 | [-0.0756, +0.0491] | 36 / 31 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_always_ceiling` | 67 (28) | 0.2491 | 0.2487 | +0.0003 | [-0.0485, +0.0556] | 59 / 8 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_train_mean` | 67 (28) | 0.2491 | 0.2680 | -0.0189 | [-0.0898, +0.0489] | 33 / 34 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_zero` | 67 (28) | 0.2491 | 0.3763 | -0.1272 | [-0.2598, +0.0092] | 41 / 26 / 0 | ayırt edilemiyor |
| return D5 DirMiss | `base_always_ceiling` | 67 (28) | 0.1642 | 0.1642 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 67 | ayırt edilemiyor |
| return D10 MAE | `v1_5_h99` | 67 (28) | 0.7633 | 0.7474 | +0.0159 | [-0.0496, +0.0746] | 34 / 33 / 0 | ayırt edilemiyor |
| return D10 MAE | `ceiling_path_v0@INF` | 67 (28) | 0.7633 | 0.4765 | +0.2868 | [+0.0556, +0.4766] | 23 / 44 / 0 | geçemiyor |
| return D10 MAE | `base_always_ceiling` | 67 (28) | 0.7633 | 1.0584 | -0.2951 | [-0.4800, -0.1278] | 61 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| return D10 MAE | `base_train_median` | 67 (28) | 0.7633 | 0.4801 | +0.2833 | [+0.0504, +0.4747] | 22 / 45 / 0 | geçemiyor |
| return D10 MAE | `base_train_mean` | 67 (28) | 0.7633 | 0.4683 | +0.2950 | [+0.0878, +0.4742] | 23 / 44 / 0 | geçemiyor |
| return D10 MAE | `base_zero` | 67 (28) | 0.7633 | 0.5596 | +0.2037 | [-0.0619, +0.4374] | 27 / 40 / 0 | ayırt edilemiyor |
| return D10 DirMiss | `base_always_ceiling` | 67 (28) | 0.1940 | 0.1940 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 67 | ayırt edilemiyor |
| p_up D1 Brier | `v1_5_h99` | 67 (28) | 0.0289 | 0.0291 | -0.0002 | [-0.0013, +0.0006] | 44 / 23 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `v1_5_h99` | 67 (28) | 0.1218 | 0.1279 | -0.0061 | [-0.0188, +0.0014] | 44 / 23 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `ceiling_path_v0@INF` | 67 (28) | 0.0289 | 0.0330 | -0.0041 | [-0.0068, -0.0005] | 59 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `ceiling_path_v0@INF` | 67 (28) | 0.1218 | 0.1660 | -0.0442 | [-0.0653, -0.0152] | 59 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_always_ceiling` | 67 (28) | 0.0289 | 0.0299 | -0.0010 | [-0.0068, +0.0031] | 2 / 65 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_always_ceiling` | 67 (28) | 0.1218 | 0.4124 | -0.2906 | [-0.8210, +0.0433] | 2 / 65 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_rate` | 67 (28) | 0.0289 | 0.0340 | -0.0051 | [-0.0082, -0.0008] | 61 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_rate` | 67 (28) | 0.1218 | 0.1717 | -0.0499 | [-0.0735, -0.0169] | 61 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_last10_rate` | 67 (28) | 0.0289 | 0.1660 | -0.1371 | [-0.1580, -0.1037] | 65 / 2 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_last10_rate` | 67 (28) | 0.1218 | 0.5229 | -0.4011 | [-0.4776, -0.2835] | 65 / 2 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 HitMiss | `base_rate` | 67 (28) | 0.0299 | 0.0299 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 67 | ayırt edilemiyor |
| p_up D3 Brier | `v1_5_h99` | 67 (28) | 0.1188 | 0.1264 | -0.0076 | [-0.0194, +0.0009] | 10 / 57 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `v1_5_h99` | 67 (28) | 0.4420 | 0.6687 | -0.2266 | [-0.5736, -0.0062] | 10 / 57 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `ceiling_path_v0@INF` | 67 (28) | 0.1188 | 0.1186 | +0.0001 | [-0.0182, +0.0247] | 55 / 12 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `ceiling_path_v0@INF` | 67 (28) | 0.4420 | 0.4030 | +0.0391 | [-0.0985, +0.2530] | 55 / 12 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_always_ceiling` | 67 (28) | 0.1188 | 0.1343 | -0.0156 | [-0.0410, +0.0037] | 9 / 58 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_always_ceiling` | 67 (28) | 0.4420 | 1.8558 | -1.4138 | [-2.5751, -0.4748] | 9 / 58 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `base_rate` | 67 (28) | 0.1188 | 0.1196 | -0.0008 | [-0.0206, +0.0253] | 54 / 13 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_rate` | 67 (28) | 0.4420 | 0.4062 | +0.0358 | [-0.1061, +0.2527] | 54 / 13 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_last10_rate` | 67 (28) | 0.1188 | 0.2500 | -0.1312 | [-0.2011, -0.0443] | 58 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_last10_rate` | 67 (28) | 0.4420 | 0.6931 | -0.2511 | [-0.5044, +0.0871] | 58 / 9 / 0 | ayırt edilemiyor |
| p_up D3 HitMiss | `base_rate` | 67 (28) | 0.1343 | 0.1343 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 67 | ayırt edilemiyor |
| p_up D5 Brier | `v1_5_h99` | 67 (28) | 0.1473 | 0.1519 | -0.0046 | [-0.0126, +0.0025] | 14 / 53 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `v1_5_h99` | 67 (28) | 0.5458 | 0.7986 | -0.2528 | [-0.5534, -0.0338] | 14 / 53 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `ceiling_path_v0@INF` | 67 (28) | 0.1473 | 0.1400 | +0.0074 | [-0.0178, +0.0378] | 52 / 15 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `ceiling_path_v0@INF` | 67 (28) | 0.5458 | 0.4552 | +0.0906 | [-0.0760, +0.3212] | 52 / 15 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_always_ceiling` | 67 (28) | 0.1473 | 0.1642 | -0.0169 | [-0.0488, +0.0072] | 11 / 56 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_always_ceiling` | 67 (28) | 0.5458 | 2.2682 | -1.7225 | [-3.0860, -0.6489] | 11 / 56 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_rate` | 67 (28) | 0.1473 | 0.1406 | +0.0067 | [-0.0193, +0.0383] | 53 / 14 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_rate` | 67 (28) | 0.5458 | 0.4570 | +0.0888 | [-0.0798, +0.3207] | 53 / 14 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 67 (28) | 0.1473 | 0.3272 | -0.1798 | [-0.2758, -0.0632] | 56 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 67 (28) | 0.5458 | 0.8497 | -0.3040 | [-0.6184, +0.0869] | 56 / 11 / 0 | ayırt edilemiyor |
| p_up D5 HitMiss | `base_rate` | 67 (28) | 0.1642 | 0.1642 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 67 | ayırt edilemiyor |
| p_up D10 Brier | `v1_5_h99` | 67 (28) | 0.1713 | 0.1817 | -0.0104 | [-0.0234, +0.0031] | 17 / 50 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `v1_5_h99` | 67 (28) | 0.5906 | 0.8170 | -0.2264 | [-0.4688, -0.0257] | 17 / 50 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `ceiling_path_v0@INF` | 67 (28) | 0.1713 | 0.1612 | +0.0101 | [-0.0215, +0.0463] | 47 / 20 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `ceiling_path_v0@INF` | 67 (28) | 0.5906 | 0.5054 | +0.0852 | [-0.0764, +0.2879] | 47 / 20 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_always_ceiling` | 67 (28) | 0.1713 | 0.1940 | -0.0227 | [-0.0643, +0.0117] | 13 / 54 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_always_ceiling` | 67 (28) | 0.5906 | 2.6806 | -2.0900 | [-3.4877, -0.9006] | 13 / 54 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `base_rate` | 67 (28) | 0.1713 | 0.1662 | +0.0051 | [-0.0305, +0.0457] | 51 / 16 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 67 (28) | 0.5906 | 0.5176 | +0.0730 | [-0.0994, +0.2895] | 51 / 16 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_last10_rate` | 67 (28) | 0.1713 | 0.2500 | -0.0787 | [-0.1539, +0.0073] | 54 / 13 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_last10_rate` | 67 (28) | 0.5906 | 0.6931 | -0.1025 | [-0.3548, +0.2020] | 54 / 13 / 0 | ayırt edilemiyor |
| p_up D10 HitMiss | `base_rate` | 67 (28) | 0.1940 | 0.1940 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 67 | ayırt edilemiyor |

### `ceiling_path_v0@INF` (keşif)

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| return D1 MAE | `base_always_ceiling` | 71 (30) | 0.0088 | 0.0092 | -0.0003 | [-0.0005, -0.0002] | 28 / 0 / 43 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_train_median` | 71 (30) | 0.0088 | 0.0092 | -0.0003 | [-0.0005, -0.0002] | 28 / 0 / 43 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_train_mean` | 71 (30) | 0.0088 | 0.0255 | -0.0167 | [-0.0203, -0.0121] | 62 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_zero` | 71 (30) | 0.0088 | 0.0909 | -0.0821 | [-0.0939, -0.0669] | 63 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 DirMiss | `base_always_ceiling` | 71 (30) | 0.0282 | 0.0282 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 71 | ayırt edilemiyor |
| return D3 MAE | `base_always_ceiling` | 71 (30) | 0.0969 | 0.0985 | -0.0016 | [-0.0021, -0.0011] | 70 / 0 / 1 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_train_median` | 71 (30) | 0.0969 | 0.0977 | -0.0008 | [-0.0013, -0.0004] | 57 / 13 / 1 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_train_mean` | 71 (30) | 0.0969 | 0.1328 | -0.0359 | [-0.0662, -0.0039] | 46 / 25 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_zero` | 71 (30) | 0.0969 | 0.2434 | -0.1465 | [-0.2184, -0.0678] | 49 / 22 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 DirMiss | `base_always_ceiling` | 71 (30) | 0.1268 | 0.1268 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 71 | ayırt edilemiyor |
| return D5 MAE | `base_always_ceiling` | 71 (30) | 0.2606 | 0.2350 | +0.0256 | [-0.0460, +0.0950] | 32 / 39 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_train_median` | 71 (30) | 0.2606 | 0.2576 | +0.0030 | [-0.0032, +0.0090] | 30 / 41 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_train_mean` | 71 (30) | 0.2606 | 0.2694 | -0.0088 | [-0.0189, +0.0014] | 43 / 28 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_zero` | 71 (30) | 0.2606 | 0.3892 | -0.1286 | [-0.2103, -0.0409] | 45 / 26 / 0 | geçiyor (zaman-dışı terazide) |
| return D5 DirMiss | `base_always_ceiling` | 71 (30) | 0.1549 | 0.1549 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 71 | ayırt edilemiyor |
| return D10 MAE | `base_always_ceiling` | 71 (30) | 0.5131 | 1.0100 | -0.4969 | [-0.7541, -0.2015] | 50 / 21 / 0 | geçiyor (zaman-dışı terazide) |
| return D10 MAE | `base_train_median` | 71 (30) | 0.5131 | 0.5176 | -0.0046 | [-0.0104, +0.0013] | 42 / 29 / 0 | ayırt edilemiyor |
| return D10 MAE | `base_train_mean` | 71 (30) | 0.5131 | 0.4939 | +0.0192 | [-0.0337, +0.0725] | 32 / 39 / 0 | ayırt edilemiyor |
| return D10 MAE | `base_zero` | 71 (30) | 0.5131 | 0.6066 | -0.0936 | [-0.1576, -0.0283] | 48 / 23 / 0 | geçiyor (zaman-dışı terazide) |
| return D10 DirMiss | `base_always_ceiling` | 71 (30) | 0.1831 | 0.1831 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 71 | ayırt edilemiyor |
| p_up D1 Brier | `base_always_ceiling` | 71 (30) | 0.0316 | 0.0282 | +0.0035 | [-0.0050, +0.0087] | 2 / 69 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_always_ceiling` | 71 (30) | 0.1622 | 0.3892 | -0.2270 | [-0.7506, +0.0982] | 2 / 69 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_rate` | 71 (30) | 0.0316 | 0.0327 | -0.0010 | [-0.0015, -0.0004] | 69 / 2 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_rate` | 71 (30) | 0.1622 | 0.1681 | -0.0059 | [-0.0083, -0.0020] | 69 / 2 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_last10_rate` | 71 (30) | 0.0316 | 0.1656 | -0.1340 | [-0.1513, -0.1062] | 69 / 2 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_last10_rate` | 71 (30) | 0.1622 | 0.5222 | -0.3601 | [-0.4126, -0.2754] | 69 / 2 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 HitMiss | `base_rate` | 71 (30) | 0.0282 | 0.0282 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 71 | ayırt edilemiyor |
| p_up D3 Brier | `base_always_ceiling` | 71 (30) | 0.1138 | 0.1268 | -0.0129 | [-0.0497, +0.0160] | 9 / 62 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_always_ceiling` | 71 (30) | 0.3916 | 1.7513 | -1.3596 | [-2.5976, -0.3846] | 9 / 62 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `base_rate` | 71 (30) | 0.1138 | 0.1149 | -0.0011 | [-0.0026, +0.0007] | 62 / 9 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_rate` | 71 (30) | 0.3916 | 0.3953 | -0.0037 | [-0.0085, +0.0024] | 62 / 9 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_last10_rate` | 71 (30) | 0.1138 | 0.2500 | -0.1362 | [-0.1864, -0.0724] | 62 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_last10_rate` | 71 (30) | 0.3916 | 0.6931 | -0.3015 | [-0.4201, -0.1509] | 62 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 HitMiss | `base_rate` | 71 (30) | 0.1268 | 0.1268 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 71 | ayırt edilemiyor |
| p_up D5 Brier | `base_always_ceiling` | 71 (30) | 0.1348 | 0.1549 | -0.0202 | [-0.0681, +0.0190] | 11 / 60 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_always_ceiling` | 71 (30) | 0.4434 | 2.1404 | -1.6970 | [-3.0840, -0.5689] | 11 / 60 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_rate` | 71 (30) | 0.1348 | 0.1355 | -0.0007 | [-0.0016, +0.0004] | 59 / 12 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_rate` | 71 (30) | 0.4434 | 0.4454 | -0.0020 | [-0.0046, +0.0012] | 59 / 12 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 71 (30) | 0.1348 | 0.3290 | -0.1942 | [-0.2629, -0.1093] | 60 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 71 (30) | 0.4434 | 0.8535 | -0.4101 | [-0.5611, -0.2228] | 60 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 HitMiss | `base_rate` | 71 (30) | 0.1549 | 0.1549 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 71 | ayırt edilemiyor |
| p_up D10 Brier | `base_always_ceiling` | 71 (30) | 0.1561 | 0.1831 | -0.0270 | [-0.0853, +0.0249] | 13 / 58 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_always_ceiling` | 71 (30) | 0.4942 | 2.5296 | -2.0354 | [-3.4546, -0.7775] | 13 / 58 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `base_rate` | 71 (30) | 0.1561 | 0.1616 | -0.0055 | [-0.0113, +0.0009] | 58 / 13 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 71 (30) | 0.4942 | 0.5080 | -0.0138 | [-0.0281, +0.0022] | 58 / 13 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_last10_rate` | 71 (30) | 0.1561 | 0.2500 | -0.0939 | [-0.1404, -0.0416] | 58 / 13 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_last10_rate` | 71 (30) | 0.4942 | 0.6931 | -0.1990 | [-0.2999, -0.0853] | 58 / 13 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 HitMiss | `base_rate` | 71 (30) | 0.1831 | 0.1831 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 71 | ayırt edilemiyor |

### `pb_ceiling_path_v0` (keşif)

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| return D1 MAE | `pb_v0` | 58 (28) | 0.0062 | 0.0107 | -0.0045 | [-0.0087, -0.0008] | 27 / 4 / 27 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_always_ceiling` | 58 (28) | 0.0062 | 0.0064 | -0.0003 | [-0.0005, -0.0001] | 20 / 0 / 38 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_train_median` | 58 (28) | 0.0062 | 0.0064 | -0.0003 | [-0.0005, -0.0001] | 20 / 0 / 38 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_train_mean` | 58 (28) | 0.0062 | 0.0247 | -0.0186 | [-0.0216, -0.0145] | 53 / 5 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_zero` | 58 (28) | 0.0062 | 0.0936 | -0.0874 | [-0.0982, -0.0729] | 54 / 4 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 DirMiss | `base_always_ceiling` | 58 (28) | 0.0172 | 0.0172 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 58 | ayırt edilemiyor |
| return D3 MAE | `pb_v0` | 58 (28) | 0.0777 | 0.1008 | -0.0231 | [-0.0462, -0.0031] | 51 / 6 / 1 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_always_ceiling` | 58 (28) | 0.0777 | 0.0792 | -0.0016 | [-0.0021, -0.0011] | 57 / 0 / 1 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_train_median` | 58 (28) | 0.0777 | 0.0785 | -0.0009 | [-0.0014, -0.0005] | 49 / 8 / 1 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_train_mean` | 58 (28) | 0.0777 | 0.1319 | -0.0542 | [-0.0831, -0.0225] | 42 / 16 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_zero` | 58 (28) | 0.0777 | 0.2644 | -0.1868 | [-0.2542, -0.1087] | 43 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 DirMiss | `base_always_ceiling` | 58 (28) | 0.1034 | 0.1034 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 58 | ayırt edilemiyor |
| return D5 MAE | `pb_v0` | 58 (28) | 0.2393 | 0.2417 | -0.0024 | [-0.0239, +0.0182] | 44 / 14 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_always_ceiling` | 58 (28) | 0.2393 | 0.1999 | +0.0394 | [-0.0003, +0.0855] | 49 / 9 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_train_mean` | 58 (28) | 0.2393 | 0.2675 | -0.0282 | [-0.0892, +0.0327] | 32 / 26 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_zero` | 58 (28) | 0.2393 | 0.4202 | -0.1808 | [-0.2951, -0.0584] | 40 / 18 / 0 | geçiyor (zaman-dışı terazide) |
| return D5 DirMiss | `base_always_ceiling` | 58 (28) | 0.1034 | 0.1034 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 58 | ayırt edilemiyor |
| return D10 MAE | `pb_v0` | 58 (28) | 0.7568 | 0.7181 | +0.0387 | [-0.0261, +0.1003] | 24 / 34 / 0 | ayırt edilemiyor |
| return D10 MAE | `base_always_ceiling` | 58 (28) | 0.7568 | 0.9534 | -0.1966 | [-0.3633, -0.0303] | 50 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| return D10 MAE | `base_train_median` | 58 (28) | 0.7568 | 0.5466 | +0.2102 | [-0.0134, +0.4144] | 19 / 39 / 0 | ayırt edilemiyor |
| return D10 MAE | `base_train_mean` | 58 (28) | 0.7568 | 0.5021 | +0.2547 | [+0.0632, +0.4306] | 20 / 38 / 0 | geçemiyor |
| return D10 MAE | `base_zero` | 58 (28) | 0.7568 | 0.6584 | +0.0984 | [-0.1590, +0.3384] | 30 / 28 / 0 | ayırt edilemiyor |
| return D10 DirMiss | `base_always_ceiling` | 58 (28) | 0.1379 | 0.1379 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 58 | ayırt edilemiyor |
| p_up D1 Brier | `pb_v0` | 58 (28) | 0.0184 | 0.0183 | +0.0001 | [-0.0005, +0.0006] | 10 / 48 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `pb_v0` | 58 (28) | 0.0962 | 0.0945 | +0.0016 | [-0.0035, +0.0049] | 10 / 48 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_always_ceiling` | 58 (28) | 0.0184 | 0.0172 | +0.0012 | [-0.0042, +0.0046] | 1 / 57 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_always_ceiling` | 58 (28) | 0.0962 | 0.2382 | -0.1420 | [-0.5831, +0.0589] | 1 / 57 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_rate` | 58 (28) | 0.0184 | 0.0240 | -0.0055 | [-0.0080, -0.0021] | 51 / 7 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_rate` | 58 (28) | 0.0962 | 0.1442 | -0.0480 | [-0.0660, -0.0235] | 51 / 7 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_last10_rate` | 58 (28) | 0.0184 | 0.1634 | -0.1450 | [-0.1578, -0.1181] | 57 / 1 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_last10_rate` | 58 (28) | 0.0962 | 0.5178 | -0.4216 | [-0.4703, -0.3273] | 57 / 1 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 HitMiss | `base_rate` | 58 (28) | 0.0172 | 0.0172 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 58 | ayırt edilemiyor |
| p_up D3 Brier | `pb_v0` | 58 (28) | 0.0982 | 0.1000 | -0.0019 | [-0.0062, +0.0016] | 9 / 49 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `pb_v0` | 58 (28) | 0.3608 | 0.3880 | -0.0271 | [-0.0929, +0.0143] | 9 / 49 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_always_ceiling` | 58 (28) | 0.0982 | 0.1034 | -0.0053 | [-0.0231, +0.0104] | 6 / 52 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_always_ceiling` | 58 (28) | 0.3608 | 1.4292 | -1.0684 | [-2.1321, -0.2663] | 6 / 52 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `base_rate` | 58 (28) | 0.0982 | 0.1006 | -0.0024 | [-0.0203, +0.0225] | 46 / 12 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_rate` | 58 (28) | 0.3608 | 0.3618 | -0.0010 | [-0.0978, +0.1450] | 46 / 12 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_last10_rate` | 58 (28) | 0.0982 | 0.2500 | -0.1518 | [-0.2135, -0.0699] | 52 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_last10_rate` | 58 (28) | 0.3608 | 0.6931 | -0.3323 | [-0.5295, -0.0567] | 52 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 HitMiss | `base_rate` | 58 (28) | 0.1034 | 0.1034 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 58 | ayırt edilemiyor |
| p_up D5 Brier | `pb_v0` | 58 (28) | 0.1006 | 0.1011 | -0.0005 | [-0.0049, +0.0029] | 6 / 52 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `pb_v0` | 58 (28) | 0.3663 | 0.3821 | -0.0158 | [-0.0682, +0.0167] | 6 / 52 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_always_ceiling` | 58 (28) | 0.1006 | 0.1034 | -0.0029 | [-0.0254, +0.0157] | 6 / 52 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_always_ceiling` | 58 (28) | 0.3663 | 1.4292 | -1.0629 | [-2.2248, -0.2120] | 6 / 52 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_rate` | 58 (28) | 0.1006 | 0.1069 | -0.0063 | [-0.0277, +0.0242] | 45 / 13 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_rate` | 58 (28) | 0.3663 | 0.3809 | -0.0146 | [-0.1155, +0.1384] | 45 / 13 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 58 (28) | 0.1006 | 0.3393 | -0.2387 | [-0.3155, -0.1322] | 52 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 58 (28) | 0.3663 | 0.8743 | -0.5081 | [-0.7263, -0.1930] | 52 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 HitMiss | `base_rate` | 58 (28) | 0.1034 | 0.1034 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 58 | ayırt edilemiyor |
| p_up D10 Brier | `pb_v0` | 58 (28) | 0.1306 | 0.1336 | -0.0030 | [-0.0069, +0.0007] | 16 / 42 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `pb_v0` | 58 (28) | 0.4400 | 0.4553 | -0.0152 | [-0.0425, +0.0073] | 16 / 42 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_always_ceiling` | 58 (28) | 0.1306 | 0.1379 | -0.0073 | [-0.0368, +0.0206] | 8 / 50 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_always_ceiling` | 58 (28) | 0.4400 | 1.9056 | -1.4655 | [-2.6227, -0.4787] | 8 / 50 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `base_rate` | 58 (28) | 0.1306 | 0.1429 | -0.0123 | [-0.0428, +0.0243] | 44 / 14 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 58 (28) | 0.4400 | 0.4682 | -0.0281 | [-0.1406, +0.1195] | 44 / 14 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_last10_rate` | 58 (28) | 0.1306 | 0.2500 | -0.1194 | [-0.1822, -0.0438] | 50 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_last10_rate` | 58 (28) | 0.4400 | 0.6931 | -0.2531 | [-0.4347, -0.0286] | 50 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 HitMiss | `base_rate` | 58 (28) | 0.1379 | 0.1379 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 58 | ayırt edilemiyor |

## 6. Zaman-dışı test, D1 sonrası (makine sıralı: makine bütün zip'i gördü, insan görmedi)

- **Ayrı ölçek** (`OOT_PRE_H99_POST_D1_MACHINE_SEQUENCED`): birincil tabloya (§2) girmez, §2–§5'teki hiçbir sayıyla toplanmaz (KARARLAR D5). Satırlar `exposure_class = MACHINE_SEQUENCED`: D_1 satırını makine ayıkladı; makine bütün zip'i gördü, insan görmedi.
- Satır: D1'i tavanda kapatan (resmi D1 tavan etiketi 1), D1 sonrası kaydı olan ve sınıfı OOT_BLIND olan her açık üye (ret dahil). D1'i tavan kapanmayan üye satır değildir, paydada "D1 tavan değil" olarak sayılır; D1 etiketi NA ya da bekleniyorsa da öyle (canlı blokla aynı kapı: SPEC_POST_D1_V0 §7.5; SPEC_DEVIATIONS I42). Açık küme = satır + payda sayaçları. Hedef D_2…D_10; D1 skorlanmaz. Birincil hücre SPEC_POST_D1_V0 §4: j = 1 koşullu RPS, `ceiling_hazard_v0`'ın koşullu eğrisi karşısında. §4'ün kalibrasyon satırları bu terazide üretilmez (SPEC_DEVIATIONS I46).

| Model | satır | skorlanan | ret | hedef oluşmadı | bekleyen | S_1 = 0 | D1 tavan değil | D1 etiketi NA | D1 bekleniyor | atlanan (S2 kaydı olan) | OOT_RETRO | açık küme |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `post_d1_hazard_v0` | 62 | 59 | 3 | 0 | 0 | 0 | 9 | 0 | 0 | 0 (0) | 0 | 71 |

| Model | Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| `post_d1_hazard_v0` | S_cond RPS | `ceiling_hazard_v0` | 59 (26) | 0.2548 | 0.2965 | -0.0418 | [-0.0664, -0.0201] | 35 / 24 / 0 | geçiyor (zaman-dışı terazide) |

Öbür hücreler, `post_d1_hazard_v0` (keşif; kod etiketi parantez içinde):

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| S_cond RPS (kural) | `ceiling_hazard_v0@INF` | 59 (26) | 0.2548 | 0.2041 | +0.0506 | [-0.0100, +0.1104] | 24 / 35 / 0 | ayırt edilemiyor |
| S_cond RPS (kural) | `base_km_expanding` | 59 (26) | 0.2548 | 0.2038 | +0.0509 | [-0.0094, +0.1108] | 25 / 34 / 0 | ayırt edilemiyor |
| S_cond RPS (kural) | `base_km_last10` | 59 (26) | 0.2548 | 0.2140 | +0.0408 | [-0.0357, +0.1140] | 26 / 33 / 0 | ayırt edilemiyor |
| S_cond RPS (kural) | `base_always_ceiling` | 59 (26) | 0.2548 | 0.5179 | -0.2631 | [-0.3573, -0.1747] | 50 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| S_cond 2 Brier (ikincil) | `ceiling_hazard_v0` | 59 (26) | 0.1649 | 0.1801 | -0.0152 | [-0.0274, -0.0045] | 47 / 12 / 0 | geçiyor (zaman-dışı terazide) |
| S_cond 2 Brier (ikincil) | `ceiling_hazard_v0@INF` | 59 (26) | 0.1649 | 0.1588 | +0.0060 | [-0.0093, +0.0241] | 45 / 14 / 0 | ayırt edilemiyor |
| S_cond 2 Brier (ikincil) | `base_km_expanding` | 59 (26) | 0.1649 | 0.1542 | +0.0106 | [-0.0085, +0.0345] | 48 / 11 / 0 | ayırt edilemiyor |
| S_cond 2 Brier (ikincil) | `base_km_last10` | 59 (26) | 0.1649 | 0.1519 | +0.0130 | [-0.0165, +0.0493] | 47 / 12 / 0 | ayırt edilemiyor |
| S_cond 2 Brier (ikincil) | `base_always_ceiling` | 59 (26) | 0.1649 | 0.1864 | -0.0216 | [-0.0400, -0.0052] | 11 / 48 / 0 | geçiyor (zaman-dışı terazide) |
| S_cond 10 Brier (ikincil) | `ceiling_hazard_v0` | 59 (26) | 0.3296 | 0.3442 | -0.0145 | [-0.0521, +0.0165] | 28 / 31 / 0 | ayırt edilemiyor |
| S_cond 10 Brier (ikincil) | `ceiling_hazard_v0@INF` | 59 (26) | 0.3296 | 0.1294 | +0.2002 | [+0.1019, +0.2967] | 17 / 42 / 0 | geçemiyor |
| S_cond 10 Brier (ikincil) | `base_km_expanding` | 59 (26) | 0.3296 | 0.1297 | +0.2000 | [+0.1023, +0.2956] | 17 / 42 / 0 | geçemiyor |
| S_cond 10 Brier (ikincil) | `base_km_last10` | 59 (26) | 0.3296 | 0.1305 | +0.1991 | [+0.0932, +0.3009] | 16 / 43 / 0 | geçemiyor |
| S_cond 10 Brier (ikincil) | `base_always_ceiling` | 59 (26) | 0.3296 | 0.8475 | -0.5178 | [-0.6504, -0.3815] | 50 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| return_cond D3 MAE (ikincil) | `ceiling_path_v0` | 58 (26) | 0.0700 | 0.0700 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 58 | ayırt edilemiyor |
| return_cond D5 MAE (ikincil) | `ceiling_path_v0` | 58 (26) | 0.1819 | 0.2131 | -0.0312 | [-0.0481, -0.0160] | 13 / 2 / 43 | geçiyor (zaman-dışı terazide) |
| return_cond D10 MAE (ikincil) | `ceiling_path_v0` | 58 (26) | 0.7011 | 0.8100 | -0.1089 | [-0.1778, -0.0396] | 23 / 9 / 26 | geçiyor (zaman-dışı terazide) |
| p_up_cond D3 Brier (ikincil) | `ceiling_path_v0` | 58 (26) | 0.0501 | 0.0514 | -0.0013 | [-0.0060, +0.0013] | 38 / 20 / 0 | ayırt edilemiyor |
| p_up_cond D5 Brier (ikincil) | `ceiling_path_v0` | 58 (26) | 0.0798 | 0.0868 | -0.0070 | [-0.0162, +0.0004] | 42 / 16 / 0 | ayırt edilemiyor |
| p_up_cond D10 Brier (ikincil) | `ceiling_path_v0` | 58 (26) | 0.1111 | 0.1212 | -0.0101 | [-0.0245, +0.0018] | 40 / 18 / 0 | ayırt edilemiyor |

## 7. OOT_RETRO (yalnız bilgi)

`retro_info`: 568 (model, arz) çifti; hiçbir n'e girmez. Kodlar ve sınıf kanıtı `scores/scores_oot.json`'dadır.

## 8. Zaman-dışı test, kasa (tek seferlik açılış): H99 öncesi kohortun SEALED üyeleri, tahminler sonuç repoya girmeden dondurulmuş

- Ayrı anahtar `oot_pre_h99_sealed`: yalnız kasadaki (SEALED) üyeler; açık küme tablolarıyla (§2–§5) ve toplamla (§9) toplanmaz. Kayıt kuralı: (model, üye) için modeli içeren en erken etkin kayıt (SPEC_HAZARD_V1 §7.3). Birincil hücreler önceden ilan edilmiştir: §6'daki 8 hücre, `ceiling_hazard_v1_*` için RPS − `base_km_expanding` (SPEC_HAZARD_V1 §5.2), `fall_d10_v0_*` için D10 Brier − `base_rate` (SPEC_C_V0 §5.2).

| MEMBER | açık küme | kasa (SEALED) | tabloya giren |
|---|---|---|---|
| 135 | 71 | 64 | 64 |

| Model | tür | skorlanan | ret | rejimle uygulanamaz | hedef oluşmadı | bekleyen | atlanan | OOT_RETRO |
|---|---|---|---|---|---|---|---|---|
| `v1_5_h99` | linear | 62 | 2 | 0 | 0 | 0 | 0 | 0 |
| `base_always_ceiling` | rule | 63 | 0 | 1 | 0 | 0 | 0 | 0 |
| `base_train_median` | rule | 64 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_train_mean` | rule | 64 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_zero` | rule | 64 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_rate` | rule | 64 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_last10_rate` | rule | 64 | 0 | 0 | 0 | 0 | 0 | 0 |
| `v1_6_h99` | linear | 62 | 2 | 0 | 0 | 0 | 0 | 0 |
| `v1_5_market20_v0` | market20 | 62 | 2 | 0 | 0 | 0 | 0 | 0 |
| `pb_v0` | pb | 53 | 11 | 0 | 0 | 0 | 0 | 0 |
| `ceiling_hazard_v0` | hazard | 62 | 2 | 0 | 0 | 0 | 0 | 0 |
| `ceiling_hazard_v0@INF` | hazard | 63 | 0 | 1 | 0 | 0 | 0 | 0 |
| `pb_ceiling_v0` | hazard | 53 | 11 | 0 | 0 | 0 | 0 | 0 |
| `pb_ceiling_v0@INF` | hazard | 63 | 0 | 1 | 0 | 0 | 0 | 0 |
| `base_km_expanding` | km | 64 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_km_last10` | km | 64 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ceiling_path_v0` | ceiling_path | 60 | 1 | 3 | 0 | 0 | 0 | 0 |
| `ceiling_path_v0@INF` | ceiling_path | 63 | 0 | 1 | 0 | 0 | 0 | 0 |
| `pb_ceiling_path_v0` | ceiling_path | 51 | 10 | 3 | 0 | 0 | 0 | 0 |
| `ceiling_hazard_v1_clip` | hazard | 62 | 2 | 0 | 0 | 0 | 0 | 0 |
| `ceiling_hazard_v1_real` | hazard | 62 | 2 | 0 | 0 | 0 | 0 | 0 |
| `ceiling_hazard_v1_pooled` | hazard | 62 | 2 | 0 | 0 | 0 | 0 | 0 |
| `ceiling_hazard_v1_pooled@INF` | hazard | 63 | 0 | 1 | 0 | 0 | 0 | 0 |
| `fall_d10_v0_h99` | fall | 60 | 4 | 0 | 0 | 0 | 0 | 0 |
| `fall_d10_v0_pooled` | fall | 60 | 4 | 0 | 0 | 0 | 0 | 0 |
| `fall_d10_v0_addsale` | fall | 62 | 2 | 0 | 0 | 0 | 0 | 0 |
| `fall_d10_v0_pooled@ZERO` | fall | 64 | 0 | 0 | 0 | 0 | 0 | 0 |

### 8.1 Birincil hücreler

| Model | Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| `v1_5_h99` | return D5 MAE | `base_train_median` | 62 (27) | 0.2463 | 0.2581 | -0.0119 | [-0.0706, +0.0412] | 32 / 30 / 0 | ayırt edilemiyor |
| `v1_6_h99` | return D10 MAE | `v1_5_h99` | 62 (27) | 0.6972 | 0.6968 | +0.0004 | [+0.0001, +0.0007] | 14 / 38 / 10 | geçemiyor |
| `v1_5_market20_v0` | return D5 MAE | `v1_5_h99` | 62 (27) | 0.2402 | 0.2463 | -0.0061 | [-0.0186, +0.0056] | 23 / 14 / 25 | ayırt edilemiyor |
| `pb_v0` | return D5 MAE | `base_train_median` | 53 (26) | 0.2858 | 0.2555 | +0.0303 | [-0.0263, +0.0883] | 24 / 29 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v0` | S RPS | `base_km_expanding` | 62 (27) | 0.2701 | 0.1973 | +0.0728 | [-0.0008, +0.1388] | 26 / 36 / 0 | ayırt edilemiyor |
| `pb_ceiling_v0` | S RPS | `base_km_expanding` | 53 (26) | 0.2659 | 0.2006 | +0.0653 | [-0.0042, +0.1329] | 20 / 33 / 0 | ayırt edilemiyor |
| `ceiling_path_v0` | return D5 MAE | `base_train_median` | 60 (27) | 0.2564 | 0.2545 | +0.0019 | [-0.0704, +0.0684] | 28 / 32 / 0 | ayırt edilemiyor |
| `pb_ceiling_path_v0` | return D5 MAE | `base_train_median` | 51 (25) | 0.2738 | 0.2391 | +0.0346 | [-0.0366, +0.1018] | 21 / 30 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_clip` | S RPS | `base_km_expanding` | 62 (27) | 0.2306 | 0.1973 | +0.0334 | [-0.0260, +0.0886] | 26 / 36 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_real` | S RPS | `base_km_expanding` | 62 (27) | 0.1862 | 0.1973 | -0.0110 | [-0.0500, +0.0259] | 39 / 23 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_pooled` | S RPS | `base_km_expanding` | 62 (27) | 0.1573 | 0.1973 | -0.0400 | [-0.0671, -0.0122] | 42 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| `fall_d10_v0_h99` | p_up D10 Brier | `base_rate` | 60 (27) | 0.1288 | 0.1686 | -0.0398 | [-0.0878, +0.0043] | 47 / 13 / 0 | ayırt edilemiyor |
| `fall_d10_v0_pooled` | p_up D10 Brier | `base_rate` | 60 (27) | 0.1234 | 0.1686 | -0.0452 | [-0.0923, -0.0020] | 49 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| `fall_d10_v0_addsale` | p_up D10 Brier | `base_rate` | 62 (29) | 0.1601 | 0.1660 | -0.0058 | [-0.0541, +0.0358] | 47 / 15 / 0 | ayırt edilemiyor |

### 8.2 İlan edilmiş ikinciller (ikincil; SPEC_HAZARD_V1 §5.2, SPEC_C_V0 §5.2)

| Model | Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | S RPS | `ceiling_hazard_v0` | 62 (27) | 0.2306 | 0.2701 | -0.0395 | [-0.0640, -0.0161] | 42 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_clip` | S RPS | `ceiling_hazard_v0@INF` | 62 (27) | 0.2306 | 0.1982 | +0.0325 | [-0.0258, +0.0865] | 27 / 35 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_clip` | S 10 Brier | `base_km_expanding` | 62 (27) | 0.1819 | 0.1125 | +0.0693 | [-0.0152, +0.1463] | 23 / 39 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_clip` | S 10 Brier | `ceiling_hazard_v0` | 62 (27) | 0.1819 | 0.2433 | -0.0615 | [-0.0939, -0.0271] | 42 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_real` | S RPS | `ceiling_hazard_v0` | 62 (27) | 0.1862 | 0.2701 | -0.0839 | [-0.1279, -0.0347] | 47 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_real` | S RPS | `ceiling_hazard_v0@INF` | 62 (27) | 0.1862 | 0.1982 | -0.0119 | [-0.0509, +0.0254] | 39 / 23 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_real` | S RPS | `ceiling_hazard_v1_clip` | 62 (27) | 0.1862 | 0.2306 | -0.0444 | [-0.0733, -0.0113] | 47 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_real` | S 10 Brier | `base_km_expanding` | 62 (27) | 0.1317 | 0.1125 | +0.0192 | [-0.0397, +0.0733] | 33 / 29 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_real` | S 10 Brier | `ceiling_hazard_v0` | 62 (27) | 0.1317 | 0.2433 | -0.1116 | [-0.1633, -0.0531] | 52 / 10 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_pooled` | S RPS | `ceiling_hazard_v0` | 62 (27) | 0.1573 | 0.2701 | -0.1128 | [-0.1808, -0.0381] | 42 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_pooled` | S RPS | `ceiling_hazard_v0@INF` | 62 (27) | 0.1573 | 0.1982 | -0.0409 | [-0.0692, -0.0117] | 40 / 22 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_pooled` | S RPS | `ceiling_hazard_v1_real` | 62 (27) | 0.1573 | 0.1862 | -0.0290 | [-0.0588, +0.0037] | 37 / 25 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_pooled` | S RPS | `ceiling_hazard_v1_pooled@INF` | 62 (27) | 0.1573 | 0.1926 | -0.0354 | [-0.0625, -0.0073] | 42 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_pooled` | S 10 Brier | `base_km_expanding` | 62 (27) | 0.0972 | 0.1125 | -0.0153 | [-0.0492, +0.0161] | 47 / 15 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_pooled` | S 10 Brier | `ceiling_hazard_v0` | 62 (27) | 0.0972 | 0.2433 | -0.1461 | [-0.2171, -0.0627] | 51 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_pooled` | S 10 Brier | `ceiling_hazard_v1_pooled@INF` | 62 (27) | 0.0972 | 0.1103 | -0.0130 | [-0.0516, +0.0217] | 46 / 16 / 0 | ayırt edilemiyor |
| `fall_d10_v0_h99` | p_up D5 Brier | `base_rate` | 60 (27) | 0.1175 | 0.1420 | -0.0244 | [-0.0626, +0.0105] | 49 / 11 / 0 | ayırt edilemiyor |
| `fall_d10_v0_h99` | p_up D5 Brier | `v1_5_h99` | 60 (27) | 0.1175 | 0.1300 | -0.0125 | [-0.0509, +0.0208] | 16 / 44 / 0 | ayırt edilemiyor |
| `fall_d10_v0_h99` | p_up D10 Brier | `base_last10_rate` | 60 (27) | 0.1288 | 0.2500 | -0.1212 | [-0.1695, -0.0773] | 48 / 12 / 0 | geçiyor (zaman-dışı terazide) |
| `fall_d10_v0_h99` | p_up D10 Brier | `v1_5_h99` | 60 (27) | 0.1288 | 0.1539 | -0.0250 | [-0.0906, +0.0302] | 12 / 48 / 0 | ayırt edilemiyor |
| `fall_d10_v0_h99` | p_up D10 Brier | `fall_d10_v0_addsale` | 60 (27) | 0.1288 | 0.1642 | -0.0354 | [-0.0813, +0.0063] | 46 / 14 / 0 | ayırt edilemiyor |
| `fall_d10_v0_pooled` | p_up D5 Brier | `base_rate` | 60 (27) | 0.1073 | 0.1420 | -0.0346 | [-0.0756, +0.0012] | 47 / 13 / 0 | ayırt edilemiyor |
| `fall_d10_v0_pooled` | p_up D5 Brier | `v1_5_h99` | 60 (27) | 0.1073 | 0.1300 | -0.0227 | [-0.0696, +0.0216] | 11 / 49 / 0 | ayırt edilemiyor |
| `fall_d10_v0_pooled` | p_up D10 Brier | `base_last10_rate` | 60 (27) | 0.1234 | 0.2500 | -0.1266 | [-0.1682, -0.0853] | 49 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| `fall_d10_v0_pooled` | p_up D10 Brier | `v1_5_h99` | 60 (27) | 0.1234 | 0.1539 | -0.0304 | [-0.1003, +0.0320] | 14 / 46 / 0 | ayırt edilemiyor |
| `fall_d10_v0_pooled` | p_up D10 Brier | `fall_d10_v0_addsale` | 60 (27) | 0.1234 | 0.1642 | -0.0408 | [-0.0723, -0.0114] | 45 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| `fall_d10_v0_pooled` | p_up D10 Brier | `fall_d10_v0_h99` | 60 (27) | 0.1234 | 0.1288 | -0.0054 | [-0.0272, +0.0188] | 16 / 44 / 0 | ayırt edilemiyor |
| `fall_d10_v0_pooled` | p_up D10 Brier | `fall_d10_v0_pooled@ZERO` | 60 (27) | 0.1234 | 0.1618 | -0.0384 | [-0.0922, +0.0099] | 46 / 14 / 0 | ayırt edilemiyor |
| `fall_d10_v0_addsale` | p_up D5 Brier | `base_rate` | 62 (29) | 0.1389 | 0.1390 | -0.0001 | [-0.0328, +0.0304] | 47 / 15 / 0 | ayırt edilemiyor |
| `fall_d10_v0_addsale` | p_up D5 Brier | `base_last10_rate` | 62 (29) | 0.1389 | 0.3277 | -0.1888 | [-0.2534, -0.1105] | 52 / 10 / 0 | geçiyor (zaman-dışı terazide) |
| `fall_d10_v0_addsale` | p_up D5 Brier | `v1_5_h99` | 60 (27) | 0.1429 | 0.1300 | +0.0128 | [-0.0311, +0.0553] | 13 / 47 / 0 | ayırt edilemiyor |
| `fall_d10_v0_addsale` | p_up D10 Brier | `base_last10_rate` | 62 (29) | 0.1601 | 0.2500 | -0.0899 | [-0.1316, -0.0498] | 47 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| `fall_d10_v0_addsale` | p_up D10 Brier | `v1_5_h99` | 60 (27) | 0.1642 | 0.1539 | +0.0104 | [-0.0667, +0.0780] | 13 / 47 / 0 | ayırt edilemiyor |

### 8.3 Bilgi (hüküm yok): kalibrasyon, ort. P(D10 kapanışı ≤ arz) ve gözlenen oran

| Model | n | ort. tahmin | gözlenen |
|---|---|---|---|
| `fall_d10_v0_h99` | 60 | 0.2568 | 0.2000 |
| `fall_d10_v0_pooled` | 60 | 0.2559 | 0.2000 |
| `fall_d10_v0_addsale` | 62 | 0.2829 | 0.1935 |

### 8.4 Keşif hücreleri (keşif; önceden ilan edilmemiş)

`v1_5_h99`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| return D1 MAE | `base_always_ceiling` | 62 (27) | 0.0293 | 0.0296 | -0.0003 | [-0.0039, +0.0036] | 14 / 24 / 24 | ayırt edilemiyor |
| return D1 MAE | `base_train_median` | 62 (27) | 0.0293 | 0.0296 | -0.0003 | [-0.0039, +0.0036] | 14 / 24 / 24 | ayırt edilemiyor |
| return D1 MAE | `base_train_mean` | 62 (27) | 0.0293 | 0.0394 | -0.0101 | [-0.0141, -0.0058] | 48 / 14 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_zero` | 62 (27) | 0.0293 | 0.0805 | -0.0512 | [-0.0736, -0.0279] | 47 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 DirMiss | `base_always_ceiling` | 62 (27) | 0.1613 | 0.1613 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| return D3 MAE | `base_always_ceiling` | 62 (27) | 0.1135 | 0.1342 | -0.0207 | [-0.0493, +0.0078] | 17 / 12 / 33 | ayırt edilemiyor |
| return D3 MAE | `base_train_median` | 62 (27) | 0.1135 | 0.1333 | -0.0198 | [-0.0484, +0.0086] | 22 / 40 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_train_mean` | 62 (27) | 0.1135 | 0.1488 | -0.0353 | [-0.0644, -0.0074] | 41 / 21 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_zero` | 62 (27) | 0.1135 | 0.2205 | -0.1070 | [-0.1912, -0.0233] | 38 / 24 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 DirMiss | `base_always_ceiling` | 62 (27) | 0.2097 | 0.2097 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| return D5 MAE | `base_always_ceiling` | 62 (27) | 0.2463 | 0.3118 | -0.0655 | [-0.1279, -0.0018] | 26 / 11 / 25 | geçiyor (zaman-dışı terazide) |
| return D5 MAE | `base_train_mean` | 62 (27) | 0.2463 | 0.2520 | -0.0057 | [-0.0797, +0.0602] | 31 / 31 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_zero` | 62 (27) | 0.2463 | 0.3283 | -0.0821 | [-0.2308, +0.0520] | 34 / 28 / 0 | ayırt edilemiyor |
| return D5 DirMiss | `base_always_ceiling` | 62 (27) | 0.1774 | 0.1774 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| return D10 MAE | `base_always_ceiling` | 62 (27) | 0.6968 | 1.1030 | -0.4062 | [-0.5858, -0.2024] | 45 / 7 / 10 | geçiyor (zaman-dışı terazide) |
| return D10 MAE | `base_train_median` | 62 (27) | 0.6968 | 0.4472 | +0.2496 | [+0.0062, +0.4682] | 21 / 41 / 0 | geçemiyor |
| return D10 MAE | `base_train_mean` | 62 (27) | 0.6968 | 0.4654 | +0.2314 | [+0.0302, +0.4198] | 24 / 38 / 0 | geçemiyor |
| return D10 MAE | `base_zero` | 62 (27) | 0.6968 | 0.5228 | +0.1740 | [-0.1169, +0.4278] | 22 / 40 / 0 | ayırt edilemiyor |
| return D10 DirMiss | `base_always_ceiling` | 62 (27) | 0.2258 | 0.2097 | +0.0161 | [+0.0000, +0.0517] | 0 / 1 / 61 | ayırt edilemiyor |
| p_up D1 Brier | `base_always_ceiling` | 62 (27) | 0.1446 | 0.1613 | -0.0166 | [-0.0310, -0.0033] | 10 / 52 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_always_ceiling` | 62 (27) | 0.5062 | 2.2283 | -1.7221 | [-2.8826, -0.6111] | 10 / 52 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_rate` | 62 (27) | 0.1446 | 0.1389 | +0.0057 | [-0.0035, +0.0162] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_rate` | 62 (27) | 0.5062 | 0.4591 | +0.0472 | [-0.0320, +0.1384] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_last10_rate` | 62 (27) | 0.1446 | 0.1923 | -0.0476 | [-0.1163, +0.0238] | 52 / 10 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_last10_rate` | 62 (27) | 0.5062 | 0.5762 | -0.0700 | [-0.3187, +0.1975] | 52 / 10 / 0 | ayırt edilemiyor |
| p_up D1 HitMiss | `base_rate` | 62 (27) | 0.1613 | 0.1613 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| p_up D3 Brier | `base_always_ceiling` | 62 (27) | 0.1764 | 0.2097 | -0.0333 | [-0.0611, -0.0100] | 13 / 49 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_always_ceiling` | 62 (27) | 0.7519 | 2.8968 | -2.1449 | [-3.4511, -0.9765] | 13 / 49 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `base_rate` | 62 (27) | 0.1764 | 0.1660 | +0.0104 | [-0.0211, +0.0472] | 48 / 14 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_rate` | 62 (27) | 0.7519 | 0.5145 | +0.2374 | [-0.0547, +0.5992] | 48 / 14 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_last10_rate` | 62 (27) | 0.1764 | 0.2500 | -0.0736 | [-0.1729, +0.0418] | 48 / 14 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_last10_rate` | 62 (27) | 0.7519 | 0.6931 | +0.0588 | [-0.3794, +0.5961] | 48 / 14 / 0 | ayırt edilemiyor |
| p_up D3 HitMiss | `base_rate` | 62 (27) | 0.2258 | 0.2097 | +0.0161 | [+0.0000, +0.0517] | 0 / 1 / 61 | ayırt edilemiyor |
| p_up D5 Brier | `base_always_ceiling` | 62 (27) | 0.1377 | 0.1774 | -0.0397 | [-0.0792, -0.0059] | 11 / 51 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_always_ceiling` | 62 (27) | 0.5017 | 2.4511 | -1.9494 | [-3.3185, -0.7913] | 11 / 51 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_rate` | 62 (27) | 0.1377 | 0.1479 | -0.0103 | [-0.0378, +0.0193] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_rate` | 62 (27) | 0.5017 | 0.4736 | +0.0281 | [-0.1433, +0.2295] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 62 (27) | 0.1377 | 0.3245 | -0.1868 | [-0.2850, -0.0703] | 51 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 62 (27) | 0.5017 | 0.8444 | -0.3426 | [-0.6643, +0.0450] | 51 / 11 / 0 | ayırt edilemiyor |
| p_up D5 HitMiss | `base_rate` | 62 (27) | 0.1935 | 0.1774 | +0.0161 | [+0.0000, +0.0517] | 0 / 1 / 61 | ayırt edilemiyor |
| p_up D10 Brier | `base_always_ceiling` | 62 (27) | 0.1583 | 0.2097 | -0.0514 | [-0.1024, -0.0103] | 13 / 49 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_always_ceiling` | 62 (27) | 0.5729 | 2.8968 | -2.3239 | [-3.5199, -1.1608] | 13 / 49 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `base_rate` | 62 (27) | 0.1583 | 0.1726 | -0.0144 | [-0.0533, +0.0257] | 51 / 11 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 62 (27) | 0.5729 | 0.5314 | +0.0415 | [-0.1618, +0.2798] | 51 / 11 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_last10_rate` | 62 (27) | 0.1583 | 0.2500 | -0.0917 | [-0.1644, -0.0148] | 48 / 14 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_last10_rate` | 62 (27) | 0.5729 | 0.6931 | -0.1203 | [-0.3917, +0.1982] | 48 / 14 / 0 | ayırt edilemiyor |
| p_up D10 HitMiss | `base_rate` | 62 (27) | 0.2258 | 0.2097 | +0.0161 | [-0.0392, +0.0678] | 1 / 2 / 59 | ayırt edilemiyor |

`v1_6_h99`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| return D1 MAE | `v1_5_h99` | 62 (27) | 0.0293 | 0.0293 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| return D1 MAE | `base_always_ceiling` | 62 (27) | 0.0293 | 0.0296 | -0.0003 | [-0.0039, +0.0036] | 14 / 24 / 24 | ayırt edilemiyor |
| return D1 MAE | `base_train_median` | 62 (27) | 0.0293 | 0.0296 | -0.0003 | [-0.0039, +0.0036] | 14 / 24 / 24 | ayırt edilemiyor |
| return D1 MAE | `base_train_mean` | 62 (27) | 0.0293 | 0.0394 | -0.0101 | [-0.0141, -0.0058] | 48 / 14 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_zero` | 62 (27) | 0.0293 | 0.0805 | -0.0512 | [-0.0736, -0.0279] | 47 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 DirMiss | `base_always_ceiling` | 62 (27) | 0.1613 | 0.1613 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| return D3 MAE | `v1_5_h99` | 62 (27) | 0.1135 | 0.1135 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| return D3 MAE | `base_always_ceiling` | 62 (27) | 0.1135 | 0.1342 | -0.0207 | [-0.0493, +0.0078] | 17 / 12 / 33 | ayırt edilemiyor |
| return D3 MAE | `base_train_median` | 62 (27) | 0.1135 | 0.1333 | -0.0198 | [-0.0484, +0.0086] | 22 / 40 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_train_mean` | 62 (27) | 0.1135 | 0.1488 | -0.0353 | [-0.0644, -0.0074] | 41 / 21 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_zero` | 62 (27) | 0.1135 | 0.2205 | -0.1070 | [-0.1912, -0.0233] | 38 / 24 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 DirMiss | `base_always_ceiling` | 62 (27) | 0.2097 | 0.2097 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| return D5 MAE | `v1_5_h99` | 62 (27) | 0.2463 | 0.2463 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| return D5 MAE | `base_always_ceiling` | 62 (27) | 0.2463 | 0.3118 | -0.0655 | [-0.1279, -0.0018] | 26 / 11 / 25 | geçiyor (zaman-dışı terazide) |
| return D5 MAE | `base_train_median` | 62 (27) | 0.2463 | 0.2581 | -0.0119 | [-0.0706, +0.0412] | 32 / 30 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_train_mean` | 62 (27) | 0.2463 | 0.2520 | -0.0057 | [-0.0797, +0.0602] | 31 / 31 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_zero` | 62 (27) | 0.2463 | 0.3283 | -0.0821 | [-0.2308, +0.0520] | 34 / 28 / 0 | ayırt edilemiyor |
| return D5 DirMiss | `base_always_ceiling` | 62 (27) | 0.1774 | 0.1774 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| return D10 MAE | `base_always_ceiling` | 62 (27) | 0.6972 | 1.1030 | -0.4058 | [-0.5855, -0.2022] | 45 / 7 / 10 | geçiyor (zaman-dışı terazide) |
| return D10 MAE | `base_train_median` | 62 (27) | 0.6972 | 0.4472 | +0.2500 | [+0.0063, +0.4687] | 21 / 41 / 0 | geçemiyor |
| return D10 MAE | `base_train_mean` | 62 (27) | 0.6972 | 0.4654 | +0.2318 | [+0.0304, +0.4204] | 24 / 38 / 0 | geçemiyor |
| return D10 MAE | `base_zero` | 62 (27) | 0.6972 | 0.5228 | +0.1744 | [-0.1168, +0.4283] | 22 / 40 / 0 | ayırt edilemiyor |
| return D10 DirMiss | `base_always_ceiling` | 62 (27) | 0.2258 | 0.2097 | +0.0161 | [+0.0000, +0.0517] | 0 / 1 / 61 | ayırt edilemiyor |
| p_up D1 Brier | `v1_5_h99` | 62 (27) | 0.1446 | 0.1446 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| p_up D1 LogLoss | `v1_5_h99` | 62 (27) | 0.5062 | 0.5062 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| p_up D1 Brier | `base_always_ceiling` | 62 (27) | 0.1446 | 0.1613 | -0.0166 | [-0.0310, -0.0033] | 10 / 52 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_always_ceiling` | 62 (27) | 0.5062 | 2.2283 | -1.7221 | [-2.8826, -0.6111] | 10 / 52 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_rate` | 62 (27) | 0.1446 | 0.1389 | +0.0057 | [-0.0035, +0.0162] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_rate` | 62 (27) | 0.5062 | 0.4591 | +0.0472 | [-0.0320, +0.1384] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_last10_rate` | 62 (27) | 0.1446 | 0.1923 | -0.0476 | [-0.1163, +0.0238] | 52 / 10 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_last10_rate` | 62 (27) | 0.5062 | 0.5762 | -0.0700 | [-0.3187, +0.1975] | 52 / 10 / 0 | ayırt edilemiyor |
| p_up D1 HitMiss | `base_rate` | 62 (27) | 0.1613 | 0.1613 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| p_up D3 Brier | `v1_5_h99` | 62 (27) | 0.1764 | 0.1764 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| p_up D3 LogLoss | `v1_5_h99` | 62 (27) | 0.7519 | 0.7519 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| p_up D3 Brier | `base_always_ceiling` | 62 (27) | 0.1764 | 0.2097 | -0.0333 | [-0.0611, -0.0100] | 13 / 49 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_always_ceiling` | 62 (27) | 0.7519 | 2.8968 | -2.1449 | [-3.4511, -0.9765] | 13 / 49 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `base_rate` | 62 (27) | 0.1764 | 0.1660 | +0.0104 | [-0.0211, +0.0472] | 48 / 14 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_rate` | 62 (27) | 0.7519 | 0.5145 | +0.2374 | [-0.0547, +0.5992] | 48 / 14 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_last10_rate` | 62 (27) | 0.1764 | 0.2500 | -0.0736 | [-0.1729, +0.0418] | 48 / 14 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_last10_rate` | 62 (27) | 0.7519 | 0.6931 | +0.0588 | [-0.3794, +0.5961] | 48 / 14 / 0 | ayırt edilemiyor |
| p_up D3 HitMiss | `base_rate` | 62 (27) | 0.2258 | 0.2097 | +0.0161 | [+0.0000, +0.0517] | 0 / 1 / 61 | ayırt edilemiyor |
| p_up D5 Brier | `v1_5_h99` | 62 (27) | 0.1377 | 0.1377 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| p_up D5 LogLoss | `v1_5_h99` | 62 (27) | 0.5017 | 0.5017 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| p_up D5 Brier | `base_always_ceiling` | 62 (27) | 0.1377 | 0.1774 | -0.0397 | [-0.0792, -0.0059] | 11 / 51 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_always_ceiling` | 62 (27) | 0.5017 | 2.4511 | -1.9494 | [-3.3185, -0.7913] | 11 / 51 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_rate` | 62 (27) | 0.1377 | 0.1479 | -0.0103 | [-0.0378, +0.0193] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_rate` | 62 (27) | 0.5017 | 0.4736 | +0.0281 | [-0.1433, +0.2295] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 62 (27) | 0.1377 | 0.3245 | -0.1868 | [-0.2850, -0.0703] | 51 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 62 (27) | 0.5017 | 0.8444 | -0.3426 | [-0.6643, +0.0450] | 51 / 11 / 0 | ayırt edilemiyor |
| p_up D5 HitMiss | `base_rate` | 62 (27) | 0.1935 | 0.1774 | +0.0161 | [+0.0000, +0.0517] | 0 / 1 / 61 | ayırt edilemiyor |
| p_up D10 Brier | `v1_5_h99` | 62 (27) | 0.1583 | 0.1583 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| p_up D10 LogLoss | `v1_5_h99` | 62 (27) | 0.5729 | 0.5729 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| p_up D10 Brier | `base_always_ceiling` | 62 (27) | 0.1583 | 0.2097 | -0.0514 | [-0.1024, -0.0103] | 13 / 49 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_always_ceiling` | 62 (27) | 0.5729 | 2.8968 | -2.3239 | [-3.5199, -1.1608] | 13 / 49 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `base_rate` | 62 (27) | 0.1583 | 0.1726 | -0.0144 | [-0.0533, +0.0257] | 51 / 11 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 62 (27) | 0.5729 | 0.5314 | +0.0415 | [-0.1618, +0.2798] | 51 / 11 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_last10_rate` | 62 (27) | 0.1583 | 0.2500 | -0.0917 | [-0.1644, -0.0148] | 48 / 14 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_last10_rate` | 62 (27) | 0.5729 | 0.6931 | -0.1203 | [-0.3917, +0.1982] | 48 / 14 / 0 | ayırt edilemiyor |
| p_up D10 HitMiss | `base_rate` | 62 (27) | 0.2258 | 0.2097 | +0.0161 | [-0.0392, +0.0678] | 1 / 2 / 59 | ayırt edilemiyor |

`v1_5_market20_v0`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| return D1 MAE | `v1_5_h99` | 62 (27) | 0.0287 | 0.0293 | -0.0006 | [-0.0019, +0.0007] | 23 / 15 / 24 | ayırt edilemiyor |
| return D1 MAE | `base_always_ceiling` | 62 (27) | 0.0287 | 0.0296 | -0.0009 | [-0.0039, +0.0023] | 15 / 22 / 25 | ayırt edilemiyor |
| return D1 MAE | `base_train_median` | 62 (27) | 0.0287 | 0.0296 | -0.0009 | [-0.0039, +0.0023] | 15 / 22 / 25 | ayırt edilemiyor |
| return D1 MAE | `base_train_mean` | 62 (27) | 0.0287 | 0.0394 | -0.0106 | [-0.0151, -0.0058] | 47 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_zero` | 62 (27) | 0.0287 | 0.0805 | -0.0518 | [-0.0747, -0.0279] | 46 / 16 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 DirMiss | `base_always_ceiling` | 62 (27) | 0.1613 | 0.1613 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| return D3 MAE | `v1_5_h99` | 62 (27) | 0.1125 | 0.1135 | -0.0010 | [-0.0023, +0.0003] | 20 / 10 / 32 | ayırt edilemiyor |
| return D3 MAE | `base_always_ceiling` | 62 (27) | 0.1125 | 0.1342 | -0.0217 | [-0.0503, +0.0061] | 18 / 12 / 32 | ayırt edilemiyor |
| return D3 MAE | `base_train_median` | 62 (27) | 0.1125 | 0.1333 | -0.0208 | [-0.0493, +0.0068] | 22 / 40 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_train_mean` | 62 (27) | 0.1125 | 0.1488 | -0.0363 | [-0.0659, -0.0078] | 42 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_zero` | 62 (27) | 0.1125 | 0.2205 | -0.1080 | [-0.1929, -0.0234] | 38 / 24 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 DirMiss | `base_always_ceiling` | 62 (27) | 0.2097 | 0.2097 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| return D5 MAE | `base_always_ceiling` | 62 (27) | 0.2402 | 0.3118 | -0.0716 | [-0.1311, -0.0140] | 23 / 9 / 30 | geçiyor (zaman-dışı terazide) |
| return D5 MAE | `base_train_median` | 62 (27) | 0.2402 | 0.2581 | -0.0179 | [-0.0822, +0.0410] | 32 / 30 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_train_mean` | 62 (27) | 0.2402 | 0.2520 | -0.0117 | [-0.0932, +0.0615] | 31 / 31 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_zero` | 62 (27) | 0.2402 | 0.3283 | -0.0881 | [-0.2441, +0.0519] | 35 / 27 / 0 | ayırt edilemiyor |
| return D5 DirMiss | `base_always_ceiling` | 62 (27) | 0.1774 | 0.1774 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| return D10 MAE | `v1_5_h99` | 62 (27) | 0.6885 | 0.6968 | -0.0083 | [-0.0352, +0.0195] | 31 / 22 / 9 | ayırt edilemiyor |
| return D10 MAE | `base_always_ceiling` | 62 (27) | 0.6885 | 1.1030 | -0.4145 | [-0.5866, -0.2281] | 43 / 5 / 14 | geçiyor (zaman-dışı terazide) |
| return D10 MAE | `base_train_median` | 62 (27) | 0.6885 | 0.4472 | +0.2413 | [-0.0182, +0.4725] | 22 / 40 / 0 | ayırt edilemiyor |
| return D10 MAE | `base_train_mean` | 62 (27) | 0.6885 | 0.4654 | +0.2231 | [+0.0106, +0.4190] | 23 / 39 / 0 | geçemiyor |
| return D10 MAE | `base_zero` | 62 (27) | 0.6885 | 0.5228 | +0.1657 | [-0.1400, +0.4362] | 22 / 40 / 0 | ayırt edilemiyor |
| return D10 DirMiss | `base_always_ceiling` | 62 (27) | 0.2258 | 0.2097 | +0.0161 | [+0.0000, +0.0517] | 0 / 1 / 61 | ayırt edilemiyor |
| p_up D1 Brier | `v1_5_h99` | 62 (27) | 0.1445 | 0.1446 | -0.0001 | [-0.0024, +0.0023] | 36 / 26 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `v1_5_h99` | 62 (27) | 0.5104 | 0.5062 | +0.0042 | [-0.0161, +0.0290] | 36 / 26 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_always_ceiling` | 62 (27) | 0.1445 | 0.1613 | -0.0168 | [-0.0314, -0.0029] | 10 / 52 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_always_ceiling` | 62 (27) | 0.5104 | 2.2283 | -1.7179 | [-2.8694, -0.6116] | 10 / 52 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_rate` | 62 (27) | 0.1445 | 0.1389 | +0.0056 | [-0.0044, +0.0167] | 49 / 13 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_rate` | 62 (27) | 0.5104 | 0.4591 | +0.0513 | [-0.0373, +0.1520] | 49 / 13 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_last10_rate` | 62 (27) | 0.1445 | 0.1923 | -0.0477 | [-0.1161, +0.0235] | 52 / 10 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_last10_rate` | 62 (27) | 0.5104 | 0.5762 | -0.0658 | [-0.3222, +0.2095] | 52 / 10 / 0 | ayırt edilemiyor |
| p_up D1 HitMiss | `base_rate` | 62 (27) | 0.1613 | 0.1613 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 62 | ayırt edilemiyor |
| p_up D3 Brier | `v1_5_h99` | 62 (27) | 0.1757 | 0.1764 | -0.0007 | [-0.0085, +0.0057] | 46 / 16 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `v1_5_h99` | 62 (27) | 0.8489 | 0.7519 | +0.0970 | [+0.0138, +0.2198] | 46 / 16 / 0 | geçemiyor |
| p_up D3 Brier | `base_always_ceiling` | 62 (27) | 0.1757 | 0.2097 | -0.0340 | [-0.0648, -0.0084] | 13 / 49 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_always_ceiling` | 62 (27) | 0.8489 | 2.8968 | -2.0479 | [-3.3469, -0.9270] | 13 / 49 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `base_rate` | 62 (27) | 0.1757 | 0.1660 | +0.0097 | [-0.0209, +0.0452] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_rate` | 62 (27) | 0.8489 | 0.5145 | +0.3344 | [-0.0251, +0.8062] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_last10_rate` | 62 (27) | 0.1757 | 0.2500 | -0.0743 | [-0.1712, +0.0383] | 48 / 14 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_last10_rate` | 62 (27) | 0.8489 | 0.6931 | +0.1558 | [-0.3483, +0.7786] | 48 / 14 / 0 | ayırt edilemiyor |
| p_up D3 HitMiss | `base_rate` | 62 (27) | 0.2258 | 0.2097 | +0.0161 | [+0.0000, +0.0517] | 0 / 1 / 61 | ayırt edilemiyor |
| p_up D5 Brier | `v1_5_h99` | 62 (27) | 0.1386 | 0.1377 | +0.0009 | [-0.0015, +0.0035] | 30 / 32 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `v1_5_h99` | 62 (27) | 0.5064 | 0.5017 | +0.0047 | [-0.0063, +0.0186] | 30 / 32 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_always_ceiling` | 62 (27) | 0.1386 | 0.1774 | -0.0389 | [-0.0776, -0.0055] | 11 / 51 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_always_ceiling` | 62 (27) | 0.5064 | 2.4511 | -1.9447 | [-3.3060, -0.7916] | 11 / 51 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_rate` | 62 (27) | 0.1386 | 0.1479 | -0.0094 | [-0.0386, +0.0219] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_rate` | 62 (27) | 0.5064 | 0.4736 | +0.0329 | [-0.1474, +0.2449] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 62 (27) | 0.1386 | 0.3245 | -0.1860 | [-0.2853, -0.0676] | 50 / 12 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 62 (27) | 0.5064 | 0.8444 | -0.3379 | [-0.6684, +0.0635] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D5 HitMiss | `base_rate` | 62 (27) | 0.1935 | 0.1774 | +0.0161 | [+0.0000, +0.0492] | 1 / 2 / 59 | ayırt edilemiyor |
| p_up D10 Brier | `v1_5_h99` | 62 (27) | 0.1585 | 0.1583 | +0.0002 | [-0.0099, +0.0094] | 29 / 33 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `v1_5_h99` | 62 (27) | 0.5830 | 0.5729 | +0.0101 | [-0.0306, +0.0446] | 29 / 33 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_always_ceiling` | 62 (27) | 0.1585 | 0.2097 | -0.0512 | [-0.1067, -0.0066] | 13 / 49 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_always_ceiling` | 62 (27) | 0.5830 | 2.8968 | -2.3138 | [-3.5212, -1.1360] | 13 / 49 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `base_rate` | 62 (27) | 0.1585 | 0.1726 | -0.0141 | [-0.0515, +0.0256] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 62 (27) | 0.5830 | 0.5314 | +0.0516 | [-0.1523, +0.2972] | 50 / 12 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_last10_rate` | 62 (27) | 0.1585 | 0.2500 | -0.0915 | [-0.1610, -0.0164] | 48 / 14 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_last10_rate` | 62 (27) | 0.5830 | 0.6931 | -0.1102 | [-0.3794, +0.2118] | 48 / 14 / 0 | ayırt edilemiyor |
| p_up D10 HitMiss | `base_rate` | 62 (27) | 0.2258 | 0.2097 | +0.0161 | [-0.0385, +0.0704] | 1 / 2 / 59 | ayırt edilemiyor |

`pb_v0`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| return D1 MAE | `v1_5_h99` | 51 (24) | 0.0234 | 0.0222 | +0.0012 | [-0.0006, +0.0032] | 16 / 18 / 17 | ayırt edilemiyor |
| return D1 MAE | `base_always_ceiling` | 52 (25) | 0.0230 | 0.0216 | +0.0014 | [-0.0020, +0.0047] | 6 / 14 / 32 | ayırt edilemiyor |
| return D1 MAE | `base_train_median` | 53 (26) | 0.0245 | 0.0231 | +0.0014 | [-0.0020, +0.0045] | 6 / 14 / 33 | ayırt edilemiyor |
| return D1 MAE | `base_train_mean` | 53 (26) | 0.0245 | 0.0349 | -0.0104 | [-0.0148, -0.0054] | 40 / 13 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_zero` | 53 (26) | 0.0245 | 0.0844 | -0.0600 | [-0.0797, -0.0373] | 42 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 DirMiss | `base_always_ceiling` | 52 (25) | 0.1154 | 0.1154 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 52 | ayırt edilemiyor |
| return D3 MAE | `v1_5_h99` | 51 (24) | 0.1193 | 0.1010 | +0.0184 | [+0.0095, +0.0286] | 8 / 22 / 21 | geçemiyor |
| return D3 MAE | `base_always_ceiling` | 52 (25) | 0.1171 | 0.1152 | +0.0019 | [-0.0273, +0.0268] | 8 / 14 / 30 | ayırt edilemiyor |
| return D3 MAE | `base_train_median` | 53 (26) | 0.1224 | 0.1198 | +0.0026 | [-0.0262, +0.0261] | 15 / 38 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_train_mean` | 53 (26) | 0.1224 | 0.1446 | -0.0222 | [-0.0543, +0.0097] | 33 / 20 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_zero` | 53 (26) | 0.1224 | 0.2388 | -0.1165 | [-0.2005, -0.0331] | 36 / 17 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 DirMiss | `base_always_ceiling` | 52 (25) | 0.1731 | 0.1731 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 52 | ayırt edilemiyor |
| return D5 MAE | `v1_5_h99` | 51 (24) | 0.2797 | 0.2292 | +0.0504 | [+0.0281, +0.0765] | 10 / 28 / 13 | geçemiyor |
| return D5 MAE | `base_always_ceiling` | 52 (25) | 0.2745 | 0.2848 | -0.0103 | [-0.0782, +0.0505] | 18 / 14 / 20 | ayırt edilemiyor |
| return D5 MAE | `base_train_mean` | 53 (26) | 0.2858 | 0.2541 | +0.0317 | [-0.0412, +0.1036] | 25 / 28 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_zero` | 53 (26) | 0.2858 | 0.3636 | -0.0778 | [-0.2188, +0.0601] | 30 / 23 / 0 | ayırt edilemiyor |
| return D5 DirMiss | `base_always_ceiling` | 52 (25) | 0.1538 | 0.1538 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 52 | ayırt edilemiyor |
| return D10 MAE | `v1_5_h99` | 51 (24) | 0.6769 | 0.6332 | +0.0437 | [-0.0509, +0.1364] | 23 / 28 / 0 | ayırt edilemiyor |
| return D10 MAE | `base_always_ceiling` | 52 (25) | 0.6644 | 1.0326 | -0.3681 | [-0.5944, -0.1498] | 41 / 8 / 3 | geçiyor (zaman-dışı terazide) |
| return D10 MAE | `base_train_median` | 53 (26) | 0.6530 | 0.4949 | +0.1582 | [-0.0779, +0.3846] | 21 / 32 / 0 | ayırt edilemiyor |
| return D10 MAE | `base_train_mean` | 53 (26) | 0.6530 | 0.4888 | +0.1642 | [-0.0312, +0.3501] | 20 / 33 / 0 | ayırt edilemiyor |
| return D10 MAE | `base_zero` | 53 (26) | 0.6530 | 0.5985 | +0.0545 | [-0.2258, +0.3186] | 26 / 27 / 0 | ayırt edilemiyor |
| return D10 DirMiss | `base_always_ceiling` | 52 (25) | 0.1731 | 0.1731 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 52 | ayırt edilemiyor |
| p_up D1 Brier | `v1_5_h99` | 51 (24) | 0.1063 | 0.1057 | +0.0006 | [-0.0014, +0.0025] | 19 / 32 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `v1_5_h99` | 51 (24) | 0.3782 | 0.3736 | +0.0046 | [-0.0237, +0.0269] | 19 / 32 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_always_ceiling` | 52 (25) | 0.1042 | 0.1154 | -0.0111 | [-0.0266, -0.0001] | 6 / 46 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_always_ceiling` | 52 (25) | 0.3711 | 1.5941 | -1.2230 | [-2.3770, -0.3296] | 6 / 46 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_rate` | 53 (26) | 0.1023 | 0.1005 | +0.0017 | [-0.0053, +0.0096] | 42 / 11 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_rate` | 53 (26) | 0.3642 | 0.3540 | +0.0103 | [-0.0468, +0.0736] | 42 / 11 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_last10_rate` | 53 (26) | 0.1023 | 0.1826 | -0.0804 | [-0.1342, -0.0132] | 47 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_last10_rate` | 53 (26) | 0.3642 | 0.5567 | -0.1925 | [-0.3879, +0.0401] | 47 / 6 / 0 | ayırt edilemiyor |
| p_up D1 HitMiss | `base_rate` | 53 (26) | 0.1132 | 0.1132 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 53 | ayırt edilemiyor |
| p_up D3 Brier | `v1_5_h99` | 51 (24) | 0.1511 | 0.1457 | +0.0053 | [-0.0060, +0.0179] | 6 / 45 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `v1_5_h99` | 51 (24) | 0.4984 | 0.6080 | -0.1097 | [-0.3260, +0.0674] | 6 / 45 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_always_ceiling` | 52 (25) | 0.1482 | 0.1731 | -0.0249 | [-0.0535, -0.0024] | 9 / 43 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_always_ceiling` | 52 (25) | 0.4889 | 2.3911 | -1.9023 | [-3.5085, -0.6422] | 9 / 43 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `base_rate` | 53 (26) | 0.1454 | 0.1415 | +0.0039 | [-0.0195, +0.0339] | 41 / 12 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_rate` | 53 (26) | 0.4798 | 0.4572 | +0.0226 | [-0.0967, +0.1756] | 41 / 12 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_last10_rate` | 53 (26) | 0.1454 | 0.2500 | -0.1046 | [-0.1946, +0.0099] | 44 / 9 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_last10_rate` | 53 (26) | 0.4798 | 0.6931 | -0.2134 | [-0.4836, +0.1326] | 44 / 9 / 0 | ayırt edilemiyor |
| p_up D3 HitMiss | `base_rate` | 53 (26) | 0.1698 | 0.1698 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 53 | ayırt edilemiyor |
| p_up D5 Brier | `v1_5_h99` | 51 (24) | 0.1353 | 0.1222 | +0.0132 | [-0.0026, +0.0302] | 6 / 45 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `v1_5_h99` | 51 (24) | 0.4430 | 0.4797 | -0.0367 | [-0.2111, +0.0948] | 6 / 45 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_always_ceiling` | 52 (25) | 0.1327 | 0.1538 | -0.0211 | [-0.0525, +0.0045] | 8 / 44 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_always_ceiling` | 52 (25) | 0.4346 | 2.1255 | -1.6908 | [-3.2083, -0.4661] | 8 / 44 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_rate` | 53 (26) | 0.1302 | 0.1332 | -0.0030 | [-0.0276, +0.0279] | 41 / 12 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_rate` | 53 (26) | 0.4267 | 0.4404 | -0.0138 | [-0.1183, +0.1191] | 41 / 12 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 53 (26) | 0.1302 | 0.3298 | -0.1996 | [-0.3016, -0.0703] | 45 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 53 (26) | 0.4267 | 0.8551 | -0.4284 | [-0.7010, -0.0816] | 45 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 HitMiss | `base_rate` | 53 (26) | 0.1509 | 0.1509 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 53 | ayırt edilemiyor |
| p_up D10 Brier | `v1_5_h99` | 51 (24) | 0.1449 | 0.1269 | +0.0180 | [-0.0021, +0.0410] | 6 / 45 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `v1_5_h99` | 51 (24) | 0.4565 | 0.4646 | -0.0082 | [-0.1777, +0.1285] | 6 / 45 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_always_ceiling` | 52 (25) | 0.1421 | 0.1731 | -0.0309 | [-0.0755, +0.0045] | 9 / 43 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_always_ceiling` | 52 (25) | 0.4480 | 2.3911 | -1.9431 | [-3.2718, -0.7954] | 9 / 43 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `base_rate` | 53 (26) | 0.1395 | 0.1561 | -0.0167 | [-0.0426, +0.0094] | 41 / 12 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 53 (26) | 0.4400 | 0.4963 | -0.0563 | [-0.1423, +0.0285] | 41 / 12 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_last10_rate` | 53 (26) | 0.1395 | 0.2500 | -0.1105 | [-0.1743, -0.0415] | 44 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_last10_rate` | 53 (26) | 0.4400 | 0.6931 | -0.2532 | [-0.4165, -0.0796] | 44 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 HitMiss | `base_rate` | 53 (26) | 0.1698 | 0.1698 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 53 | ayırt edilemiyor |

`ceiling_hazard_v0`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| S RPS | `ceiling_hazard_v0@INF` | 62 (27) | 0.2701 | 0.1982 | +0.0719 | [+0.0001, +0.1368] | 26 / 36 / 0 | geçemiyor |
| S RPS | `base_km_last10` | 62 (27) | 0.2701 | 0.2267 | +0.0435 | [-0.0767, +0.1457] | 24 / 38 / 0 | ayırt edilemiyor |
| S RPS | `base_always_ceiling` | 62 (27) | 0.2701 | 0.6145 | -0.3444 | [-0.4506, -0.2190] | 52 / 10 / 0 | geçiyor (zaman-dışı terazide) |
| S 1 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2051 | 0.2102 | -0.0052 | [-0.0321, +0.0214] | 50 / 12 / 0 | ayırt edilemiyor |
| S 1 Brier | `base_km_expanding` | 62 (27) | 0.2051 | 0.2075 | -0.0025 | [-0.0309, +0.0268] | 51 / 11 / 0 | ayırt edilemiyor |
| S 1 Brier | `base_km_last10` | 62 (27) | 0.2051 | 0.2500 | -0.0449 | [-0.1520, +0.0696] | 45 / 17 / 0 | ayırt edilemiyor |
| S 1 Brier | `base_always_ceiling` | 62 (27) | 0.2051 | 0.2742 | -0.0691 | [-0.1118, -0.0296] | 17 / 45 / 0 | geçiyor (zaman-dışı terazide) |
| S 3 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2779 | 0.2571 | +0.0208 | [-0.0432, +0.0832] | 42 / 20 / 0 | ayırt edilemiyor |
| S 3 Brier | `base_km_expanding` | 62 (27) | 0.2779 | 0.2563 | +0.0216 | [-0.0432, +0.0847] | 41 / 21 / 0 | ayırt edilemiyor |
| S 3 Brier | `base_km_last10` | 62 (27) | 0.2779 | 0.3056 | -0.0278 | [-0.2125, +0.1494] | 35 / 27 / 0 | ayırt edilemiyor |
| S 3 Brier | `base_always_ceiling` | 62 (27) | 0.2779 | 0.4355 | -0.1576 | [-0.2485, -0.0666] | 27 / 35 / 0 | geçiyor (zaman-dışı terazide) |
| S 5 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.3045 | 0.2364 | +0.0681 | [-0.0399, +0.1716] | 31 / 31 / 0 | ayırt edilemiyor |
| S 5 Brier | `base_km_expanding` | 62 (27) | 0.3045 | 0.2352 | +0.0693 | [-0.0424, +0.1756] | 32 / 30 / 0 | ayırt edilemiyor |
| S 5 Brier | `base_km_last10` | 62 (27) | 0.3045 | 0.2610 | +0.0436 | [-0.1327, +0.2028] | 28 / 34 / 0 | ayırt edilemiyor |
| S 5 Brier | `base_always_ceiling` | 62 (27) | 0.3045 | 0.6290 | -0.3245 | [-0.4511, -0.1759] | 39 / 23 / 0 | geçiyor (zaman-dışı terazide) |
| S 10 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2433 | 0.1125 | +0.1309 | [+0.0272, +0.2239] | 20 / 42 / 0 | geçemiyor |
| S 10 Brier | `base_km_expanding` | 62 (27) | 0.2433 | 0.1125 | +0.1308 | [+0.0276, +0.2233] | 20 / 42 / 0 | geçemiyor |
| S 10 Brier | `base_km_last10` | 62 (27) | 0.2433 | 0.1173 | +0.1260 | [+0.0058, +0.2293] | 17 / 45 / 0 | geçemiyor |
| S 10 Brier | `base_always_ceiling` | 62 (27) | 0.2433 | 0.8710 | -0.6276 | [-0.7578, -0.4599] | 54 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2051 | 0.2102 | -0.0052 | [-0.0321, +0.0214] | 50 / 12 / 0 | ayırt edilemiyor |
| P_close_ceiling 1 Brier | `base_km_expanding` | 62 (27) | 0.2051 | 0.2075 | -0.0025 | [-0.0309, +0.0268] | 51 / 11 / 0 | ayırt edilemiyor |
| P_close_ceiling 1 Brier | `base_km_last10` | 62 (27) | 0.2051 | 0.2500 | -0.0449 | [-0.1520, +0.0696] | 45 / 17 / 0 | ayırt edilemiyor |
| P_close_ceiling 1 Brier | `base_always_ceiling` | 62 (27) | 0.2051 | 0.2742 | -0.0691 | [-0.1118, -0.0296] | 17 / 45 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `v1_5_p_up_as_ceiling` | 62 (27) | 0.2051 | 0.2375 | -0.0324 | [-0.0527, -0.0132] | 19 / 43 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 3 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2794 | 0.2581 | +0.0213 | [-0.0419, +0.0830] | 42 / 20 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `base_km_expanding` | 62 (27) | 0.2794 | 0.2579 | +0.0215 | [-0.0420, +0.0834] | 42 / 20 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `base_km_last10` | 62 (27) | 0.2794 | 0.2982 | -0.0188 | [-0.1985, +0.1535] | 35 / 27 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `base_always_ceiling` | 62 (27) | 0.2794 | 0.4355 | -0.1561 | [-0.2461, -0.0662] | 27 / 35 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 3 Brier | `v1_5_p_up_as_ceiling` | 62 (27) | 0.2794 | 0.3609 | -0.0815 | [-0.1260, -0.0324] | 27 / 35 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 5 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.3167 | 0.2517 | +0.0650 | [-0.0253, +0.1556] | 33 / 29 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `base_km_expanding` | 62 (27) | 0.3167 | 0.2492 | +0.0675 | [-0.0246, +0.1613] | 34 / 28 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `base_km_last10` | 62 (27) | 0.3167 | 0.2483 | +0.0684 | [-0.0751, +0.2065] | 30 / 32 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `base_always_ceiling` | 62 (27) | 0.3167 | 0.5968 | -0.2801 | [-0.3934, -0.1583] | 37 / 25 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 5 Brier | `v1_5_p_up_as_ceiling` | 62 (27) | 0.3167 | 0.4902 | -0.1735 | [-0.2406, -0.0935] | 37 / 25 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 10 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2804 | 0.1760 | +0.1043 | [+0.0120, +0.1975] | 24 / 38 / 0 | geçemiyor |
| P_close_ceiling 10 Brier | `base_km_expanding` | 62 (27) | 0.2804 | 0.1760 | +0.1043 | [+0.0120, +0.1975] | 24 / 38 / 0 | geçemiyor |
| P_close_ceiling 10 Brier | `base_km_last10` | 62 (27) | 0.2804 | 0.1761 | +0.1043 | [-0.0044, +0.2106] | 21 / 41 / 0 | ayırt edilemiyor |
| P_close_ceiling 10 Brier | `base_always_ceiling` | 62 (27) | 0.2804 | 0.7742 | -0.4938 | [-0.6318, -0.3344] | 48 / 14 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 10 Brier | `v1_5_p_up_as_ceiling` | 62 (27) | 0.2804 | 0.6279 | -0.3475 | [-0.4473, -0.2288] | 48 / 14 / 0 | geçiyor (zaman-dışı terazide) |

`pb_ceiling_v0`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| S RPS | `pb_ceiling_v0@INF` | 52 (25) | 0.2654 | 0.2016 | +0.0638 | [-0.0092, +0.1310] | 20 / 32 / 0 | ayırt edilemiyor |
| S RPS | `base_km_last10` | 53 (26) | 0.2659 | 0.2469 | +0.0189 | [-0.0976, +0.1287] | 23 / 30 / 0 | ayırt edilemiyor |
| S RPS | `base_always_ceiling` | 52 (25) | 0.2654 | 0.5788 | -0.3135 | [-0.4334, -0.1815] | 41 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| S 1 Brier | `pb_ceiling_v0@INF` | 52 (25) | 0.1859 | 0.1796 | +0.0063 | [-0.0164, +0.0323] | 40 / 12 / 0 | ayırt edilemiyor |
| S 1 Brier | `base_km_expanding` | 53 (26) | 0.1824 | 0.1771 | +0.0053 | [-0.0166, +0.0305] | 40 / 13 / 0 | ayırt edilemiyor |
| S 1 Brier | `base_km_last10` | 53 (26) | 0.1824 | 0.2500 | -0.0676 | [-0.1659, +0.0421] | 41 / 12 / 0 | ayırt edilemiyor |
| S 1 Brier | `base_always_ceiling` | 52 (25) | 0.1859 | 0.2308 | -0.0448 | [-0.0852, -0.0105] | 12 / 40 / 0 | geçiyor (zaman-dışı terazide) |
| S 3 Brier | `pb_ceiling_v0@INF` | 52 (25) | 0.2881 | 0.2445 | +0.0436 | [-0.0274, +0.1150] | 32 / 20 / 0 | ayırt edilemiyor |
| S 3 Brier | `base_km_expanding` | 53 (26) | 0.2827 | 0.2432 | +0.0395 | [-0.0263, +0.1059] | 33 / 20 / 0 | ayırt edilemiyor |
| S 3 Brier | `base_km_last10` | 53 (26) | 0.2827 | 0.3198 | -0.0371 | [-0.2205, +0.1421] | 32 / 21 / 0 | ayırt edilemiyor |
| S 3 Brier | `base_always_ceiling` | 52 (25) | 0.2881 | 0.4038 | -0.1157 | [-0.2131, -0.0301] | 21 / 31 / 0 | geçiyor (zaman-dışı terazide) |
| S 5 Brier | `pb_ceiling_v0@INF` | 52 (25) | 0.3320 | 0.2378 | +0.0942 | [-0.0068, +0.1954] | 24 / 28 / 0 | ayırt edilemiyor |
| S 5 Brier | `base_km_expanding` | 53 (26) | 0.3259 | 0.2396 | +0.0863 | [-0.0139, +0.1878] | 25 / 28 / 0 | ayırt edilemiyor |
| S 5 Brier | `base_km_last10` | 53 (26) | 0.3259 | 0.2759 | +0.0500 | [-0.1167, +0.2105] | 21 / 32 / 0 | ayırt edilemiyor |
| S 5 Brier | `base_always_ceiling` | 52 (25) | 0.3320 | 0.6154 | -0.2834 | [-0.4265, -0.1349] | 32 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| S 10 Brier | `pb_ceiling_v0@INF` | 52 (25) | 0.2207 | 0.1446 | +0.0761 | [-0.0233, +0.1667] | 15 / 37 / 0 | ayırt edilemiyor |
| S 10 Brier | `base_km_expanding` | 53 (26) | 0.2292 | 0.1418 | +0.0874 | [-0.0077, +0.1758] | 16 / 37 / 0 | ayırt edilemiyor |
| S 10 Brier | `base_km_last10` | 53 (26) | 0.2292 | 0.1533 | +0.0759 | [-0.0384, +0.1796] | 11 / 42 / 0 | ayırt edilemiyor |
| S 10 Brier | `base_always_ceiling` | 52 (25) | 0.2207 | 0.8269 | -0.6062 | [-0.7697, -0.4165] | 43 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `pb_ceiling_v0@INF` | 52 (25) | 0.1859 | 0.1796 | +0.0063 | [-0.0164, +0.0323] | 40 / 12 / 0 | ayırt edilemiyor |
| P_close_ceiling 1 Brier | `base_km_expanding` | 53 (26) | 0.1824 | 0.1771 | +0.0053 | [-0.0166, +0.0305] | 40 / 13 / 0 | ayırt edilemiyor |
| P_close_ceiling 1 Brier | `base_km_last10` | 53 (26) | 0.1824 | 0.2500 | -0.0676 | [-0.1659, +0.0421] | 41 / 12 / 0 | ayırt edilemiyor |
| P_close_ceiling 1 Brier | `base_always_ceiling` | 52 (25) | 0.1859 | 0.2308 | -0.0448 | [-0.0852, -0.0105] | 12 / 40 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 3 Brier | `pb_ceiling_v0@INF` | 52 (25) | 0.2897 | 0.2455 | +0.0442 | [-0.0257, +0.1142] | 32 / 20 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `base_km_expanding` | 53 (26) | 0.2842 | 0.2442 | +0.0400 | [-0.0248, +0.1052] | 33 / 20 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `base_km_last10` | 53 (26) | 0.2842 | 0.3112 | -0.0269 | [-0.2063, +0.1483] | 32 / 21 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `base_always_ceiling` | 52 (25) | 0.2897 | 0.4038 | -0.1142 | [-0.2097, -0.0306] | 21 / 31 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 5 Brier | `pb_ceiling_v0@INF` | 52 (25) | 0.3288 | 0.2498 | +0.0790 | [-0.0011, +0.1616] | 26 / 26 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `base_km_expanding` | 53 (26) | 0.3227 | 0.2494 | +0.0732 | [-0.0065, +0.1569] | 27 / 26 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `base_km_last10` | 53 (26) | 0.3227 | 0.2597 | +0.0630 | [-0.0698, +0.1962] | 23 / 30 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `base_always_ceiling` | 52 (25) | 0.3288 | 0.5769 | -0.2481 | [-0.3760, -0.1202] | 30 / 22 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 10 Brier | `pb_ceiling_v0@INF` | 52 (25) | 0.2359 | 0.1875 | +0.0484 | [-0.0404, +0.1383] | 19 / 33 / 0 | ayırt edilemiyor |
| P_close_ceiling 10 Brier | `base_km_expanding` | 53 (26) | 0.2449 | 0.1854 | +0.0595 | [-0.0237, +0.1475] | 20 / 33 / 0 | ayırt edilemiyor |
| P_close_ceiling 10 Brier | `base_km_last10` | 53 (26) | 0.2449 | 0.1882 | +0.0567 | [-0.0434, +0.1594] | 15 / 38 / 0 | ayırt edilemiyor |
| P_close_ceiling 10 Brier | `base_always_ceiling` | 52 (25) | 0.2359 | 0.7500 | -0.5141 | [-0.6671, -0.3562] | 39 / 13 / 0 | geçiyor (zaman-dışı terazide) |

`ceiling_path_v0`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| return D1 MAE | `v1_5_h99` | 60 (27) | 0.0287 | 0.0288 | -0.0001 | [-0.0038, +0.0034] | 32 / 13 / 15 | ayırt edilemiyor |
| return D1 MAE | `ceiling_path_v0@INF` | 60 (27) | 0.0287 | 0.0287 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 60 | ayırt edilemiyor |
| return D1 MAE | `base_always_ceiling` | 60 (27) | 0.0287 | 0.0289 | -0.0002 | [-0.0004, -0.0001] | 20 / 0 / 40 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_train_median` | 60 (27) | 0.0287 | 0.0289 | -0.0002 | [-0.0004, -0.0001] | 20 / 0 / 40 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_train_mean` | 60 (27) | 0.0287 | 0.0390 | -0.0104 | [-0.0164, -0.0040] | 44 / 16 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_zero` | 60 (27) | 0.0287 | 0.0815 | -0.0528 | [-0.0770, -0.0274] | 45 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 DirMiss | `base_always_ceiling` | 60 (27) | 0.1667 | 0.1667 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 60 | ayırt edilemiyor |
| return D3 MAE | `v1_5_h99` | 60 (27) | 0.1229 | 0.1139 | +0.0090 | [-0.0144, +0.0299] | 42 / 16 / 2 | ayırt edilemiyor |
| return D3 MAE | `ceiling_path_v0@INF` | 60 (27) | 0.1229 | 0.1307 | -0.0078 | [-0.0251, +0.0000] | 2 / 0 / 58 | ayırt edilemiyor |
| return D3 MAE | `base_always_ceiling` | 60 (27) | 0.1229 | 0.1323 | -0.0094 | [-0.0267, -0.0012] | 58 / 0 / 2 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_train_median` | 60 (27) | 0.1229 | 0.1314 | -0.0086 | [-0.0257, -0.0005] | 47 / 12 / 1 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_train_mean` | 60 (27) | 0.1229 | 0.1474 | -0.0246 | [-0.0679, +0.0173] | 36 / 24 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_zero` | 60 (27) | 0.1229 | 0.2215 | -0.0987 | [-0.2008, +0.0006] | 37 / 23 / 0 | ayırt edilemiyor |
| return D3 DirMiss | `base_always_ceiling` | 60 (27) | 0.2000 | 0.2000 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 60 | ayırt edilemiyor |
| return D5 MAE | `v1_5_h99` | 60 (27) | 0.2564 | 0.2463 | +0.0100 | [-0.0103, +0.0292] | 40 / 20 / 0 | ayırt edilemiyor |
| return D5 MAE | `ceiling_path_v0@INF` | 60 (27) | 0.2564 | 0.2515 | +0.0049 | [-0.0741, +0.0762] | 29 / 31 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_always_ceiling` | 60 (27) | 0.2564 | 0.3098 | -0.0535 | [-0.1144, +0.0011] | 56 / 4 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_train_mean` | 60 (27) | 0.2564 | 0.2481 | +0.0083 | [-0.0822, +0.0874] | 28 / 32 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_zero` | 60 (27) | 0.2564 | 0.3270 | -0.0706 | [-0.2338, +0.0720] | 33 / 27 / 0 | ayırt edilemiyor |
| return D5 DirMiss | `base_always_ceiling` | 60 (27) | 0.1667 | 0.1667 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 60 | ayırt edilemiyor |
| return D10 MAE | `v1_5_h99` | 60 (27) | 0.7056 | 0.7085 | -0.0029 | [-0.0658, +0.0672] | 36 / 24 / 0 | ayırt edilemiyor |
| return D10 MAE | `ceiling_path_v0@INF` | 60 (27) | 0.7056 | 0.4453 | +0.2603 | [+0.0306, +0.4703] | 24 / 35 / 1 | geçemiyor |
| return D10 MAE | `base_always_ceiling` | 60 (27) | 0.7056 | 1.0968 | -0.3913 | [-0.6209, -0.1362] | 56 / 4 / 0 | geçiyor (zaman-dışı terazide) |
| return D10 MAE | `base_train_median` | 60 (27) | 0.7056 | 0.4468 | +0.2588 | [+0.0251, +0.4699] | 24 / 36 / 0 | geçemiyor |
| return D10 MAE | `base_train_mean` | 60 (27) | 0.7056 | 0.4656 | +0.2400 | [+0.0408, +0.4289] | 23 / 37 / 0 | geçemiyor |
| return D10 MAE | `base_zero` | 60 (27) | 0.7056 | 0.5249 | +0.1807 | [-0.0907, +0.4173] | 23 / 37 / 0 | ayırt edilemiyor |
| return D10 DirMiss | `base_always_ceiling` | 60 (27) | 0.2000 | 0.2000 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 60 | ayırt edilemiyor |
| p_up D1 Brier | `v1_5_h99` | 60 (27) | 0.1465 | 0.1492 | -0.0028 | [-0.0064, +0.0004] | 44 / 16 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `v1_5_h99` | 60 (27) | 0.5104 | 0.5204 | -0.0100 | [-0.0397, +0.0223] | 44 / 16 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `ceiling_path_v0@INF` | 60 (27) | 0.1465 | 0.1442 | +0.0022 | [-0.0063, +0.0122] | 48 / 12 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `ceiling_path_v0@INF` | 60 (27) | 0.5104 | 0.4767 | +0.0337 | [-0.0529, +0.1420] | 48 / 12 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_always_ceiling` | 60 (27) | 0.1465 | 0.1667 | -0.0202 | [-0.0375, -0.0041] | 10 / 50 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_always_ceiling` | 60 (27) | 0.5104 | 2.3026 | -1.7922 | [-2.9886, -0.6292] | 10 / 50 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_rate` | 60 (27) | 0.1465 | 0.1432 | +0.0033 | [-0.0061, +0.0144] | 49 / 11 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_rate` | 60 (27) | 0.5104 | 0.4708 | +0.0396 | [-0.0521, +0.1548] | 49 / 11 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_last10_rate` | 60 (27) | 0.1465 | 0.1933 | -0.0469 | [-0.1155, +0.0272] | 50 / 10 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_last10_rate` | 60 (27) | 0.5104 | 0.5784 | -0.0680 | [-0.3258, +0.2170] | 50 / 10 / 0 | ayırt edilemiyor |
| p_up D1 HitMiss | `base_rate` | 60 (27) | 0.1667 | 0.1667 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 60 | ayırt edilemiyor |
| p_up D3 Brier | `v1_5_h99` | 60 (27) | 0.1601 | 0.1736 | -0.0134 | [-0.0281, -0.0005] | 12 / 48 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `v1_5_h99` | 60 (27) | 0.5169 | 0.7553 | -0.2385 | [-0.4907, -0.0404] | 12 / 48 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `ceiling_path_v0@INF` | 60 (27) | 0.1601 | 0.1603 | -0.0002 | [-0.0205, +0.0233] | 46 / 14 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `ceiling_path_v0@INF` | 60 (27) | 0.5169 | 0.5014 | +0.0155 | [-0.0895, +0.1424] | 46 / 14 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_always_ceiling` | 60 (27) | 0.1601 | 0.2000 | -0.0399 | [-0.0743, -0.0114] | 12 / 48 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_always_ceiling` | 60 (27) | 0.5169 | 2.7631 | -2.2462 | [-3.7610, -0.9641] | 12 / 48 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `base_rate` | 60 (27) | 0.1601 | 0.1601 | +0.0001 | [-0.0215, +0.0253] | 46 / 14 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_rate` | 60 (27) | 0.5169 | 0.5006 | +0.0163 | [-0.0936, +0.1499] | 46 / 14 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_last10_rate` | 60 (27) | 0.1601 | 0.2500 | -0.0899 | [-0.1759, +0.0129] | 48 / 12 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_last10_rate` | 60 (27) | 0.5169 | 0.6931 | -0.1763 | [-0.4322, +0.1349] | 48 / 12 / 0 | ayırt edilemiyor |
| p_up D3 HitMiss | `base_rate` | 60 (27) | 0.2000 | 0.2000 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 60 | ayırt edilemiyor |
| p_up D5 Brier | `v1_5_h99` | 60 (27) | 0.1317 | 0.1374 | -0.0057 | [-0.0177, +0.0063] | 10 / 50 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `v1_5_h99` | 60 (27) | 0.4207 | 0.5050 | -0.0843 | [-0.2124, +0.0166] | 10 / 50 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `ceiling_path_v0@INF` | 60 (27) | 0.1317 | 0.1414 | -0.0097 | [-0.0292, +0.0122] | 47 / 13 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `ceiling_path_v0@INF` | 60 (27) | 0.4207 | 0.4584 | -0.0377 | [-0.1222, +0.0629] | 47 / 13 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_always_ceiling` | 60 (27) | 0.1317 | 0.1667 | -0.0350 | [-0.0736, -0.0035] | 10 / 50 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_always_ceiling` | 60 (27) | 0.4207 | 2.3026 | -1.8819 | [-3.3386, -0.7018] | 10 / 50 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_rate` | 60 (27) | 0.1317 | 0.1420 | -0.0103 | [-0.0304, +0.0125] | 46 / 14 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_rate` | 60 (27) | 0.4207 | 0.4601 | -0.0394 | [-0.1260, +0.0633] | 46 / 14 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 60 (27) | 0.1317 | 0.3267 | -0.1950 | [-0.2844, -0.0838] | 50 / 10 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 60 (27) | 0.4207 | 0.8487 | -0.4280 | [-0.6637, -0.1400] | 50 / 10 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 HitMiss | `base_rate` | 60 (27) | 0.1667 | 0.1667 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 60 | ayırt edilemiyor |
| p_up D10 Brier | `v1_5_h99` | 60 (27) | 0.1477 | 0.1587 | -0.0110 | [-0.0285, +0.0077] | 9 / 51 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `v1_5_h99` | 60 (27) | 0.4583 | 0.5785 | -0.1202 | [-0.2727, +0.0088] | 9 / 51 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `ceiling_path_v0@INF` | 60 (27) | 0.1477 | 0.1640 | -0.0163 | [-0.0387, +0.0074] | 45 / 15 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `ceiling_path_v0@INF` | 60 (27) | 0.4583 | 0.5114 | -0.0531 | [-0.1356, +0.0418] | 45 / 15 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_always_ceiling` | 60 (27) | 0.1477 | 0.2000 | -0.0523 | [-0.0983, -0.0117] | 12 / 48 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_always_ceiling` | 60 (27) | 0.4583 | 2.7631 | -2.3048 | [-3.5418, -1.1263] | 12 / 48 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `base_rate` | 60 (27) | 0.1477 | 0.1686 | -0.0209 | [-0.0463, +0.0071] | 46 / 14 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 60 (27) | 0.4583 | 0.5229 | -0.0646 | [-0.1563, +0.0419] | 46 / 14 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_last10_rate` | 60 (27) | 0.1477 | 0.2500 | -0.1023 | [-0.1638, -0.0364] | 48 / 12 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_last10_rate` | 60 (27) | 0.4583 | 0.6931 | -0.2348 | [-0.4008, -0.0537] | 48 / 12 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 HitMiss | `base_rate` | 60 (27) | 0.2000 | 0.2000 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 60 | ayırt edilemiyor |

`ceiling_path_v0@INF`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| return D1 MAE | `base_always_ceiling` | 63 (28) | 0.0289 | 0.0291 | -0.0003 | [-0.0005, -0.0001] | 21 / 0 / 42 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_train_median` | 63 (28) | 0.0289 | 0.0291 | -0.0003 | [-0.0005, -0.0001] | 21 / 0 / 42 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_train_mean` | 63 (28) | 0.0289 | 0.0391 | -0.0102 | [-0.0163, -0.0040] | 46 / 17 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_zero` | 63 (28) | 0.0289 | 0.0808 | -0.0519 | [-0.0761, -0.0272] | 47 / 16 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 DirMiss | `base_always_ceiling` | 63 (28) | 0.1587 | 0.1587 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 63 | ayırt edilemiyor |
| return D3 MAE | `base_always_ceiling` | 63 (28) | 0.1305 | 0.1321 | -0.0016 | [-0.0021, -0.0012] | 61 / 0 / 2 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_train_median` | 63 (28) | 0.1305 | 0.1313 | -0.0008 | [-0.0012, -0.0004] | 49 / 13 / 1 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_train_mean` | 63 (28) | 0.1305 | 0.1483 | -0.0178 | [-0.0630, +0.0231] | 36 / 27 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_zero` | 63 (28) | 0.1305 | 0.2222 | -0.0917 | [-0.1948, +0.0075] | 39 / 24 / 0 | ayırt edilemiyor |
| return D3 DirMiss | `base_always_ceiling` | 63 (28) | 0.2063 | 0.2063 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 63 | ayırt edilemiyor |
| return D5 MAE | `base_always_ceiling` | 63 (28) | 0.2552 | 0.3070 | -0.0518 | [-0.1297, +0.0429] | 38 / 25 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_train_median` | 63 (28) | 0.2552 | 0.2576 | -0.0024 | [-0.0093, +0.0059] | 35 / 28 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_train_mean` | 63 (28) | 0.2552 | 0.2525 | +0.0027 | [-0.0115, +0.0145] | 29 / 34 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_zero` | 63 (28) | 0.2552 | 0.3327 | -0.0774 | [-0.1809, +0.0225] | 38 / 25 / 0 | ayırt edilemiyor |
| return D5 DirMiss | `base_always_ceiling` | 63 (28) | 0.1746 | 0.1746 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 63 | ayırt edilemiyor |
| return D10 MAE | `base_always_ceiling` | 63 (28) | 0.4593 | 1.0859 | -0.6265 | [-0.9027, -0.2694] | 48 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| return D10 MAE | `base_train_median` | 63 (28) | 0.4593 | 0.4610 | -0.0017 | [-0.0088, +0.0046] | 34 / 29 / 0 | ayırt edilemiyor |
| return D10 MAE | `base_train_mean` | 63 (28) | 0.4593 | 0.4754 | -0.0160 | [-0.0670, +0.0435] | 35 / 28 / 0 | ayırt edilemiyor |
| return D10 MAE | `base_zero` | 63 (28) | 0.4593 | 0.5394 | -0.0800 | [-0.1482, -0.0154] | 42 / 21 / 0 | geçiyor (zaman-dışı terazide) |
| return D10 DirMiss | `base_always_ceiling` | 63 (28) | 0.2063 | 0.2063 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 63 | ayırt edilemiyor |
| p_up D1 Brier | `base_always_ceiling` | 63 (28) | 0.1378 | 0.1587 | -0.0209 | [-0.0405, -0.0031] | 10 / 53 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_always_ceiling` | 63 (28) | 0.4587 | 2.1929 | -1.7342 | [-2.9402, -0.6345] | 10 / 53 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_rate` | 63 (28) | 0.1378 | 0.1369 | +0.0009 | [-0.0005, +0.0025] | 53 / 10 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_rate` | 63 (28) | 0.4587 | 0.4535 | +0.0052 | [-0.0029, +0.0141] | 53 / 10 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_last10_rate` | 63 (28) | 0.1378 | 0.1917 | -0.0540 | [-0.1124, +0.0101] | 53 / 10 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_last10_rate` | 63 (28) | 0.4587 | 0.5752 | -0.1165 | [-0.2942, +0.0784] | 53 / 10 / 0 | ayırt edilemiyor |
| p_up D1 HitMiss | `base_rate` | 63 (28) | 0.1587 | 0.1587 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 63 | ayırt edilemiyor |
| p_up D3 Brier | `base_always_ceiling` | 63 (28) | 0.1643 | 0.2063 | -0.0420 | [-0.0867, -0.0024] | 13 / 50 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_always_ceiling` | 63 (28) | 0.5109 | 2.8508 | -2.3399 | [-3.8453, -1.0056] | 13 / 50 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `base_rate` | 63 (28) | 0.1643 | 0.1640 | +0.0004 | [-0.0017, +0.0026] | 50 / 13 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_rate` | 63 (28) | 0.5109 | 0.5097 | +0.0012 | [-0.0054, +0.0086] | 50 / 13 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_last10_rate` | 63 (28) | 0.1643 | 0.2500 | -0.0857 | [-0.1544, -0.0081] | 50 / 13 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_last10_rate` | 63 (28) | 0.5109 | 0.6931 | -0.1822 | [-0.3446, +0.0009] | 50 / 13 / 0 | ayırt edilemiyor |
| p_up D3 HitMiss | `base_rate` | 63 (28) | 0.2063 | 0.2063 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 63 | ayırt edilemiyor |
| p_up D5 Brier | `base_always_ceiling` | 63 (28) | 0.1459 | 0.1746 | -0.0287 | [-0.0780, +0.0146] | 11 / 52 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_always_ceiling` | 63 (28) | 0.4687 | 2.4122 | -1.9435 | [-3.3661, -0.7004] | 11 / 52 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_rate` | 63 (28) | 0.1459 | 0.1464 | -0.0005 | [-0.0015, +0.0007] | 52 / 11 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_rate` | 63 (28) | 0.4687 | 0.4701 | -0.0013 | [-0.0043, +0.0021] | 52 / 11 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 63 (28) | 0.1459 | 0.3251 | -0.1792 | [-0.2550, -0.0921] | 52 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 63 (28) | 0.4687 | 0.8455 | -0.3768 | [-0.5440, -0.1848] | 52 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 HitMiss | `base_rate` | 63 (28) | 0.1746 | 0.1746 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 63 | ayırt edilemiyor |
| p_up D10 Brier | `base_always_ceiling` | 63 (28) | 0.1670 | 0.2063 | -0.0393 | [-0.0933, +0.0109] | 13 / 50 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_always_ceiling` | 63 (28) | 0.5179 | 2.8508 | -2.3329 | [-3.6433, -1.1150] | 13 / 50 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `base_rate` | 63 (28) | 0.1670 | 0.1713 | -0.0042 | [-0.0099, +0.0018] | 50 / 13 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 63 (28) | 0.5179 | 0.5285 | -0.0105 | [-0.0245, +0.0045] | 50 / 13 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_last10_rate` | 63 (28) | 0.1670 | 0.2500 | -0.0830 | [-0.1280, -0.0345] | 50 / 13 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_last10_rate` | 63 (28) | 0.5179 | 0.6931 | -0.1752 | [-0.2732, -0.0699] | 50 / 13 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 HitMiss | `base_rate` | 63 (28) | 0.2063 | 0.2063 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 63 | ayırt edilemiyor |

`pb_ceiling_path_v0`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| return D1 MAE | `pb_v0` | 51 (25) | 0.0217 | 0.0232 | -0.0015 | [-0.0048, +0.0019] | 24 / 6 / 21 | ayırt edilemiyor |
| return D1 MAE | `base_always_ceiling` | 51 (25) | 0.0217 | 0.0221 | -0.0003 | [-0.0005, -0.0002] | 18 / 0 / 33 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_train_median` | 51 (25) | 0.0217 | 0.0221 | -0.0003 | [-0.0005, -0.0002] | 18 / 0 / 33 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_train_mean` | 51 (25) | 0.0217 | 0.0334 | -0.0117 | [-0.0176, -0.0052] | 39 / 12 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 MAE | `base_zero` | 51 (25) | 0.0217 | 0.0819 | -0.0601 | [-0.0827, -0.0347] | 40 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| return D1 DirMiss | `base_always_ceiling` | 51 (25) | 0.1176 | 0.1176 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 51 | ayırt edilemiyor |
| return D3 MAE | `pb_v0` | 51 (25) | 0.1157 | 0.1179 | -0.0022 | [-0.0270, +0.0274] | 41 / 8 / 2 | ayırt edilemiyor |
| return D3 MAE | `base_always_ceiling` | 51 (25) | 0.1157 | 0.1175 | -0.0017 | [-0.0024, -0.0012] | 49 / 0 / 2 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_train_median` | 51 (25) | 0.1157 | 0.1167 | -0.0009 | [-0.0014, -0.0005] | 40 / 10 / 1 | geçiyor (zaman-dışı terazide) |
| return D3 MAE | `base_train_mean` | 51 (25) | 0.1157 | 0.1377 | -0.0220 | [-0.0673, +0.0212] | 30 / 21 / 0 | ayırt edilemiyor |
| return D3 MAE | `base_zero` | 51 (25) | 0.1157 | 0.2275 | -0.1117 | [-0.2140, -0.0074] | 33 / 18 / 0 | geçiyor (zaman-dışı terazide) |
| return D3 DirMiss | `base_always_ceiling` | 51 (25) | 0.1765 | 0.1765 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 51 | ayırt edilemiyor |
| return D5 MAE | `pb_v0` | 51 (25) | 0.2738 | 0.2756 | -0.0019 | [-0.0255, +0.0202] | 34 / 17 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_always_ceiling` | 51 (25) | 0.2738 | 0.2903 | -0.0165 | [-0.0744, +0.0300] | 46 / 5 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_train_mean` | 51 (25) | 0.2738 | 0.2353 | +0.0385 | [-0.0512, +0.1191] | 23 / 28 / 0 | ayırt edilemiyor |
| return D5 MAE | `base_zero` | 51 (25) | 0.2738 | 0.3368 | -0.0630 | [-0.2238, +0.0922] | 28 / 23 / 0 | ayırt edilemiyor |
| return D5 DirMiss | `base_always_ceiling` | 51 (25) | 0.1569 | 0.1569 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 51 | ayırt edilemiyor |
| return D10 MAE | `pb_v0` | 51 (25) | 0.6883 | 0.6760 | +0.0123 | [-0.0507, +0.0771] | 24 / 27 / 0 | ayırt edilemiyor |
| return D10 MAE | `base_always_ceiling` | 51 (25) | 0.6883 | 1.0366 | -0.3483 | [-0.6202, -0.0815] | 45 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| return D10 MAE | `base_train_median` | 51 (25) | 0.6883 | 0.4765 | +0.2118 | [-0.0119, +0.4236] | 21 / 30 / 0 | ayırt edilemiyor |
| return D10 MAE | `base_train_mean` | 51 (25) | 0.6883 | 0.4790 | +0.2092 | [+0.0138, +0.3956] | 19 / 32 / 0 | geçemiyor |
| return D10 MAE | `base_zero` | 51 (25) | 0.6883 | 0.5745 | +0.1138 | [-0.1471, +0.3496] | 22 / 29 / 0 | ayırt edilemiyor |
| return D10 DirMiss | `base_always_ceiling` | 51 (25) | 0.1765 | 0.1765 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 51 | ayırt edilemiyor |
| p_up D1 Brier | `pb_v0` | 51 (25) | 0.1062 | 0.1062 | +0.0000 | [-0.0014, +0.0012] | 10 / 41 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `pb_v0` | 51 (25) | 0.3765 | 0.3770 | -0.0006 | [-0.0112, +0.0088] | 10 / 41 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_always_ceiling` | 51 (25) | 0.1062 | 0.1176 | -0.0114 | [-0.0272, +0.0001] | 6 / 45 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_always_ceiling` | 51 (25) | 0.3765 | 1.6254 | -1.2489 | [-2.4431, -0.3382] | 6 / 45 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 Brier | `base_rate` | 51 (25) | 0.1062 | 0.1041 | +0.0022 | [-0.0050, +0.0103] | 40 / 11 / 0 | ayırt edilemiyor |
| p_up D1 LogLoss | `base_rate` | 51 (25) | 0.3765 | 0.3637 | +0.0128 | [-0.0426, +0.0754] | 40 / 11 / 0 | ayırt edilemiyor |
| p_up D1 Brier | `base_last10_rate` | 51 (25) | 0.1062 | 0.1835 | -0.0773 | [-0.1318, -0.0067] | 45 / 6 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D1 LogLoss | `base_last10_rate` | 51 (25) | 0.3765 | 0.5585 | -0.1821 | [-0.3739, +0.0627] | 45 / 6 / 0 | ayırt edilemiyor |
| p_up D1 HitMiss | `base_rate` | 51 (25) | 0.1176 | 0.1176 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 51 | ayırt edilemiyor |
| p_up D3 Brier | `pb_v0` | 51 (25) | 0.1464 | 0.1508 | -0.0044 | [-0.0111, +0.0009] | 12 / 39 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `pb_v0` | 51 (25) | 0.4673 | 0.4958 | -0.0285 | [-0.0789, +0.0100] | 12 / 39 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_always_ceiling` | 51 (25) | 0.1464 | 0.1765 | -0.0301 | [-0.0639, -0.0027] | 9 / 42 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 LogLoss | `base_always_ceiling` | 51 (25) | 0.4673 | 2.4380 | -1.9708 | [-3.6304, -0.6518] | 9 / 42 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D3 Brier | `base_rate` | 51 (25) | 0.1464 | 0.1456 | +0.0008 | [-0.0183, +0.0250] | 39 / 12 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_rate` | 51 (25) | 0.4673 | 0.4668 | +0.0005 | [-0.0850, +0.1083] | 39 / 12 / 0 | ayırt edilemiyor |
| p_up D3 Brier | `base_last10_rate` | 51 (25) | 0.1464 | 0.2500 | -0.1036 | [-0.1905, +0.0059] | 42 / 9 / 0 | ayırt edilemiyor |
| p_up D3 LogLoss | `base_last10_rate` | 51 (25) | 0.4673 | 0.6931 | -0.2259 | [-0.4645, +0.0758] | 42 / 9 / 0 | ayırt edilemiyor |
| p_up D3 HitMiss | `base_rate` | 51 (25) | 0.1765 | 0.1765 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 51 | ayırt edilemiyor |
| p_up D5 Brier | `pb_v0` | 51 (25) | 0.1335 | 0.1349 | -0.0014 | [-0.0065, +0.0028] | 9 / 42 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `pb_v0` | 51 (25) | 0.4307 | 0.4399 | -0.0091 | [-0.0403, +0.0160] | 9 / 42 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_always_ceiling` | 51 (25) | 0.1335 | 0.1569 | -0.0234 | [-0.0584, +0.0060] | 8 / 43 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_always_ceiling` | 51 (25) | 0.4307 | 2.1671 | -1.7364 | [-3.3210, -0.4643] | 8 / 43 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_rate` | 51 (25) | 0.1335 | 0.1365 | -0.0031 | [-0.0245, +0.0241] | 38 / 13 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_rate` | 51 (25) | 0.4307 | 0.4478 | -0.0171 | [-0.1017, +0.0893] | 38 / 13 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 51 (25) | 0.1335 | 0.3286 | -0.1952 | [-0.2958, -0.0691] | 43 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 51 (25) | 0.4307 | 0.8527 | -0.4220 | [-0.6763, -0.1006] | 43 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 HitMiss | `base_rate` | 51 (25) | 0.1569 | 0.1569 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 51 | ayırt edilemiyor |
| p_up D10 Brier | `pb_v0` | 51 (25) | 0.1412 | 0.1441 | -0.0029 | [-0.0069, +0.0010] | 13 / 38 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `pb_v0` | 51 (25) | 0.4428 | 0.4523 | -0.0095 | [-0.0261, +0.0071] | 13 / 38 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_always_ceiling` | 51 (25) | 0.1412 | 0.1765 | -0.0352 | [-0.0816, +0.0022] | 9 / 42 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_always_ceiling` | 51 (25) | 0.4428 | 2.4380 | -1.9952 | [-3.3683, -0.8108] | 9 / 42 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 Brier | `base_rate` | 51 (25) | 0.1412 | 0.1589 | -0.0177 | [-0.0402, +0.0055] | 39 / 12 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 51 (25) | 0.4428 | 0.5021 | -0.0593 | [-0.1289, +0.0135] | 39 / 12 / 0 | ayırt edilemiyor |
| p_up D10 Brier | `base_last10_rate` | 51 (25) | 0.1412 | 0.2500 | -0.1088 | [-0.1688, -0.0418] | 42 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_last10_rate` | 51 (25) | 0.4428 | 0.6931 | -0.2503 | [-0.3990, -0.0873] | 42 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 HitMiss | `base_rate` | 51 (25) | 0.1765 | 0.1765 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 51 | ayırt edilemiyor |

`ceiling_hazard_v1_clip`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| S 1 Brier | `base_km_expanding` | 62 (27) | 0.2021 | 0.2075 | -0.0054 | [-0.0329, +0.0228] | 50 / 12 / 0 | ayırt edilemiyor |
| S 1 Brier | `ceiling_hazard_v0` | 62 (27) | 0.2021 | 0.2051 | -0.0029 | [-0.0086, +0.0010] | 21 / 41 / 0 | ayırt edilemiyor |
| S 1 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2021 | 0.2102 | -0.0081 | [-0.0342, +0.0175] | 50 / 12 / 0 | ayırt edilemiyor |
| S 3 Brier | `base_km_expanding` | 62 (27) | 0.2562 | 0.2563 | -0.0001 | [-0.0535, +0.0500] | 41 / 21 / 0 | ayırt edilemiyor |
| S 3 Brier | `ceiling_hazard_v0` | 62 (27) | 0.2562 | 0.2779 | -0.0217 | [-0.0457, -0.0021] | 33 / 29 / 0 | geçiyor (zaman-dışı terazide) |
| S 3 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2562 | 0.2571 | -0.0009 | [-0.0534, +0.0480] | 42 / 20 / 0 | ayırt edilemiyor |
| S 5 Brier | `base_km_expanding` | 62 (27) | 0.2544 | 0.2352 | +0.0192 | [-0.0718, +0.1094] | 32 / 30 / 0 | ayırt edilemiyor |
| S 5 Brier | `ceiling_hazard_v0` | 62 (27) | 0.2544 | 0.3045 | -0.0501 | [-0.0848, -0.0179] | 41 / 21 / 0 | geçiyor (zaman-dışı terazide) |
| S 5 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2544 | 0.2364 | +0.0180 | [-0.0693, +0.1061] | 33 / 29 / 0 | ayırt edilemiyor |
| S 10 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.1819 | 0.1125 | +0.0694 | [-0.0158, +0.1467] | 21 / 41 / 0 | ayırt edilemiyor |
| P_close_ceiling 1 Brier | `base_km_expanding` | 62 (27) | 0.2021 | 0.2075 | -0.0054 | [-0.0329, +0.0228] | 50 / 12 / 0 | ayırt edilemiyor |
| P_close_ceiling 1 Brier | `ceiling_hazard_v0` | 62 (27) | 0.2021 | 0.2051 | -0.0029 | [-0.0086, +0.0010] | 21 / 41 / 0 | ayırt edilemiyor |
| P_close_ceiling 1 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2021 | 0.2102 | -0.0081 | [-0.0342, +0.0175] | 50 / 12 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `base_km_expanding` | 62 (27) | 0.2579 | 0.2579 | +0.0000 | [-0.0520, +0.0487] | 41 / 21 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `ceiling_hazard_v0` | 62 (27) | 0.2579 | 0.2794 | -0.0215 | [-0.0452, -0.0021] | 33 / 29 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 3 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2579 | 0.2581 | -0.0002 | [-0.0522, +0.0481] | 42 / 20 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `base_km_expanding` | 62 (27) | 0.2769 | 0.2492 | +0.0277 | [-0.0510, +0.1097] | 34 / 28 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `ceiling_hazard_v0` | 62 (27) | 0.2769 | 0.3167 | -0.0398 | [-0.0630, -0.0166] | 39 / 23 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 5 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2769 | 0.2517 | +0.0252 | [-0.0508, +0.1053] | 35 / 27 / 0 | ayırt edilemiyor |
| P_close_ceiling 10 Brier | `base_km_expanding` | 62 (27) | 0.2417 | 0.1760 | +0.0656 | [-0.0052, +0.1400] | 23 / 39 / 0 | ayırt edilemiyor |
| P_close_ceiling 10 Brier | `ceiling_hazard_v0` | 62 (27) | 0.2417 | 0.2804 | -0.0387 | [-0.0761, +0.0010] | 40 / 22 / 0 | ayırt edilemiyor |
| P_close_ceiling 10 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2417 | 0.1760 | +0.0656 | [-0.0052, +0.1401] | 23 / 39 / 0 | ayırt edilemiyor |

`ceiling_hazard_v1_real`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| S 1 Brier | `base_km_expanding` | 62 (27) | 0.1730 | 0.2075 | -0.0345 | [-0.0559, -0.0158] | 55 / 7 / 0 | geçiyor (zaman-dışı terazide) |
| S 1 Brier | `ceiling_hazard_v0` | 62 (27) | 0.1730 | 0.2051 | -0.0320 | [-0.0535, -0.0107] | 18 / 44 / 0 | geçiyor (zaman-dışı terazide) |
| S 1 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.1730 | 0.2102 | -0.0372 | [-0.0594, -0.0177] | 52 / 10 / 0 | geçiyor (zaman-dışı terazide) |
| S 1 Brier | `ceiling_hazard_v1_clip` | 62 (27) | 0.1730 | 0.2021 | -0.0291 | [-0.0486, -0.0097] | 18 / 44 / 0 | geçiyor (zaman-dışı terazide) |
| S 3 Brier | `base_km_expanding` | 62 (27) | 0.2071 | 0.2563 | -0.0492 | [-0.0816, -0.0196] | 46 / 16 / 0 | geçiyor (zaman-dışı terazide) |
| S 3 Brier | `ceiling_hazard_v0` | 62 (27) | 0.2071 | 0.2779 | -0.0708 | [-0.1214, -0.0185] | 28 / 34 / 0 | geçiyor (zaman-dışı terazide) |
| S 3 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2071 | 0.2571 | -0.0500 | [-0.0823, -0.0202] | 46 / 16 / 0 | geçiyor (zaman-dışı terazide) |
| S 3 Brier | `ceiling_hazard_v1_clip` | 62 (27) | 0.2071 | 0.2562 | -0.0491 | [-0.0853, -0.0104] | 28 / 34 / 0 | geçiyor (zaman-dışı terazide) |
| S 5 Brier | `base_km_expanding` | 62 (27) | 0.2100 | 0.2352 | -0.0252 | [-0.0853, +0.0369] | 41 / 21 / 0 | ayırt edilemiyor |
| S 5 Brier | `ceiling_hazard_v0` | 62 (27) | 0.2100 | 0.3045 | -0.0945 | [-0.1592, -0.0265] | 37 / 25 / 0 | geçiyor (zaman-dışı terazide) |
| S 5 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2100 | 0.2364 | -0.0264 | [-0.0846, +0.0347] | 42 / 20 / 0 | ayırt edilemiyor |
| S 5 Brier | `ceiling_hazard_v1_clip` | 62 (27) | 0.2100 | 0.2544 | -0.0444 | [-0.0865, +0.0026] | 36 / 26 / 0 | ayırt edilemiyor |
| S 10 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.1317 | 0.1125 | +0.0193 | [-0.0401, +0.0736] | 33 / 29 / 0 | ayırt edilemiyor |
| S 10 Brier | `ceiling_hazard_v1_clip` | 62 (27) | 0.1317 | 0.1819 | -0.0501 | [-0.0845, -0.0157] | 51 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `base_km_expanding` | 62 (27) | 0.1730 | 0.2075 | -0.0345 | [-0.0559, -0.0158] | 55 / 7 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `ceiling_hazard_v0` | 62 (27) | 0.1730 | 0.2051 | -0.0320 | [-0.0535, -0.0107] | 18 / 44 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.1730 | 0.2102 | -0.0372 | [-0.0594, -0.0177] | 52 / 10 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `ceiling_hazard_v1_clip` | 62 (27) | 0.1730 | 0.2021 | -0.0291 | [-0.0486, -0.0097] | 18 / 44 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 3 Brier | `base_km_expanding` | 62 (27) | 0.2088 | 0.2579 | -0.0491 | [-0.0810, -0.0196] | 46 / 16 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 3 Brier | `ceiling_hazard_v0` | 62 (27) | 0.2088 | 0.2794 | -0.0706 | [-0.1207, -0.0190] | 28 / 34 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 3 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2088 | 0.2581 | -0.0494 | [-0.0812, -0.0198] | 46 / 16 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 3 Brier | `ceiling_hazard_v1_clip` | 62 (27) | 0.2088 | 0.2579 | -0.0491 | [-0.0850, -0.0108] | 28 / 34 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 5 Brier | `base_km_expanding` | 62 (27) | 0.2338 | 0.2492 | -0.0154 | [-0.0677, +0.0398] | 39 / 23 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `ceiling_hazard_v0` | 62 (27) | 0.2338 | 0.3167 | -0.0829 | [-0.1350, -0.0274] | 35 / 27 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 5 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.2338 | 0.2517 | -0.0179 | [-0.0682, +0.0366] | 40 / 22 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `ceiling_hazard_v1_clip` | 62 (27) | 0.2338 | 0.2769 | -0.0431 | [-0.0816, -0.0039] | 34 / 28 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 10 Brier | `base_km_expanding` | 62 (27) | 0.1932 | 0.1760 | +0.0171 | [-0.0289, +0.0653] | 31 / 31 / 0 | ayırt edilemiyor |
| P_close_ceiling 10 Brier | `ceiling_hazard_v0` | 62 (27) | 0.1932 | 0.2804 | -0.0872 | [-0.1460, -0.0241] | 46 / 16 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 10 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.1932 | 0.1760 | +0.0172 | [-0.0289, +0.0653] | 31 / 31 / 0 | ayırt edilemiyor |
| P_close_ceiling 10 Brier | `ceiling_hazard_v1_clip` | 62 (27) | 0.1932 | 0.2417 | -0.0485 | [-0.0818, -0.0169] | 45 / 17 / 0 | geçiyor (zaman-dışı terazide) |

`ceiling_hazard_v1_pooled`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| S 1 Brier | `base_km_expanding` | 62 (27) | 0.1589 | 0.2075 | -0.0487 | [-0.0727, -0.0246] | 45 / 17 / 0 | geçiyor (zaman-dışı terazide) |
| S 1 Brier | `ceiling_hazard_v0` | 62 (27) | 0.1589 | 0.2051 | -0.0462 | [-0.0922, -0.0019] | 15 / 47 / 0 | geçiyor (zaman-dışı terazide) |
| S 1 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.1589 | 0.2102 | -0.0513 | [-0.0784, -0.0238] | 42 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| S 1 Brier | `ceiling_hazard_v1_real` | 62 (27) | 0.1589 | 0.1730 | -0.0141 | [-0.0412, +0.0130] | 21 / 41 / 0 | ayırt edilemiyor |
| S 1 Brier | `ceiling_hazard_v1_pooled@INF` | 62 (27) | 0.1589 | 0.2091 | -0.0502 | [-0.0770, -0.0233] | 40 / 22 / 0 | geçiyor (zaman-dışı terazide) |
| S 3 Brier | `base_km_expanding` | 62 (27) | 0.1687 | 0.2563 | -0.0876 | [-0.1420, -0.0282] | 45 / 17 / 0 | geçiyor (zaman-dışı terazide) |
| S 3 Brier | `ceiling_hazard_v0` | 62 (27) | 0.1687 | 0.2779 | -0.1092 | [-0.2186, -0.0006] | 25 / 37 / 0 | geçiyor (zaman-dışı terazide) |
| S 3 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.1687 | 0.2571 | -0.0885 | [-0.1442, -0.0277] | 44 / 18 / 0 | geçiyor (zaman-dışı terazide) |
| S 3 Brier | `ceiling_hazard_v1_real` | 62 (27) | 0.1687 | 0.2071 | -0.0385 | [-0.0998, +0.0231] | 27 / 35 / 0 | ayırt edilemiyor |
| S 3 Brier | `ceiling_hazard_v1_pooled@INF` | 62 (27) | 0.1687 | 0.2456 | -0.0769 | [-0.1169, -0.0320] | 45 / 17 / 0 | geçiyor (zaman-dışı terazide) |
| S 5 Brier | `base_km_expanding` | 62 (27) | 0.1734 | 0.2352 | -0.0618 | [-0.1017, -0.0175] | 47 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| S 5 Brier | `ceiling_hazard_v0` | 62 (27) | 0.1734 | 0.3045 | -0.1311 | [-0.2375, -0.0166] | 36 / 26 / 0 | geçiyor (zaman-dışı terazide) |
| S 5 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.1734 | 0.2364 | -0.0630 | [-0.1033, -0.0182] | 47 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| S 5 Brier | `ceiling_hazard_v1_real` | 62 (27) | 0.1734 | 0.2100 | -0.0366 | [-0.0857, +0.0162] | 39 / 23 / 0 | ayırt edilemiyor |
| S 5 Brier | `ceiling_hazard_v1_pooled@INF` | 62 (27) | 0.1734 | 0.2260 | -0.0526 | [-0.0955, -0.0080] | 48 / 14 / 0 | geçiyor (zaman-dışı terazide) |
| S 10 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.0972 | 0.1125 | -0.0152 | [-0.0495, +0.0166] | 46 / 16 / 0 | ayırt edilemiyor |
| S 10 Brier | `ceiling_hazard_v1_real` | 62 (27) | 0.0972 | 0.1317 | -0.0345 | [-0.0624, -0.0019] | 51 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `base_km_expanding` | 62 (27) | 0.1589 | 0.2075 | -0.0487 | [-0.0727, -0.0246] | 45 / 17 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `ceiling_hazard_v0` | 62 (27) | 0.1589 | 0.2051 | -0.0462 | [-0.0922, -0.0019] | 15 / 47 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.1589 | 0.2102 | -0.0513 | [-0.0784, -0.0238] | 42 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 1 Brier | `ceiling_hazard_v1_real` | 62 (27) | 0.1589 | 0.1730 | -0.0141 | [-0.0412, +0.0130] | 21 / 41 / 0 | ayırt edilemiyor |
| P_close_ceiling 1 Brier | `ceiling_hazard_v1_pooled@INF` | 62 (27) | 0.1589 | 0.2091 | -0.0502 | [-0.0770, -0.0233] | 40 / 22 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 3 Brier | `base_km_expanding` | 62 (27) | 0.1709 | 0.2579 | -0.0869 | [-0.1376, -0.0321] | 46 / 16 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 3 Brier | `ceiling_hazard_v0` | 62 (27) | 0.1709 | 0.2794 | -0.1085 | [-0.2122, -0.0054] | 25 / 37 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 3 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.1709 | 0.2581 | -0.0872 | [-0.1382, -0.0318] | 46 / 16 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 3 Brier | `ceiling_hazard_v1_real` | 62 (27) | 0.1709 | 0.2088 | -0.0378 | [-0.0934, +0.0189] | 29 / 33 / 0 | ayırt edilemiyor |
| P_close_ceiling 3 Brier | `ceiling_hazard_v1_pooled@INF` | 62 (27) | 0.1709 | 0.2482 | -0.0772 | [-0.1168, -0.0335] | 45 / 17 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 5 Brier | `base_km_expanding` | 62 (27) | 0.1905 | 0.2492 | -0.0586 | [-0.0999, -0.0176] | 45 / 17 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 5 Brier | `ceiling_hazard_v0` | 62 (27) | 0.1905 | 0.3167 | -0.1262 | [-0.2257, -0.0260] | 35 / 27 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 5 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.1905 | 0.2517 | -0.0612 | [-0.1033, -0.0176] | 44 / 18 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 5 Brier | `ceiling_hazard_v1_real` | 62 (27) | 0.1905 | 0.2338 | -0.0433 | [-0.0949, +0.0074] | 37 / 25 / 0 | ayırt edilemiyor |
| P_close_ceiling 5 Brier | `ceiling_hazard_v1_pooled@INF` | 62 (27) | 0.1905 | 0.2375 | -0.0470 | [-0.0878, -0.0065] | 46 / 16 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 10 Brier | `base_km_expanding` | 62 (27) | 0.1633 | 0.1760 | -0.0128 | [-0.0486, +0.0268] | 43 / 19 / 0 | ayırt edilemiyor |
| P_close_ceiling 10 Brier | `ceiling_hazard_v0` | 62 (27) | 0.1633 | 0.2804 | -0.1171 | [-0.2043, -0.0224] | 48 / 14 / 0 | geçiyor (zaman-dışı terazide) |
| P_close_ceiling 10 Brier | `ceiling_hazard_v0@INF` | 62 (27) | 0.1633 | 0.1760 | -0.0128 | [-0.0486, +0.0268] | 43 / 19 / 0 | ayırt edilemiyor |
| P_close_ceiling 10 Brier | `ceiling_hazard_v1_real` | 62 (27) | 0.1633 | 0.1932 | -0.0299 | [-0.0617, +0.0050] | 49 / 13 / 0 | ayırt edilemiyor |
| P_close_ceiling 10 Brier | `ceiling_hazard_v1_pooled@INF` | 62 (27) | 0.1633 | 0.1732 | -0.0099 | [-0.0467, +0.0283] | 42 / 20 / 0 | ayırt edilemiyor |

`fall_d10_v0_h99`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| p_up D5 LogLoss | `base_rate` | 60 (27) | 0.3650 | 0.4601 | -0.0951 | [-0.2005, +0.0037] | 49 / 11 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `base_last10_rate` | 60 (27) | 0.1175 | 0.3267 | -0.2091 | [-0.2818, -0.1304] | 51 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 60 (27) | 0.3650 | 0.8487 | -0.4837 | [-0.6819, -0.2582] | 51 / 9 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `v1_5_h99` | 60 (27) | 0.3650 | 0.4861 | -0.1210 | [-0.2990, +0.0208] | 16 / 44 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `fall_d10_v0_addsale` | 60 (27) | 0.1175 | 0.1429 | -0.0253 | [-0.0629, +0.0148] | 48 / 12 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `fall_d10_v0_addsale` | 60 (27) | 0.3650 | 0.4525 | -0.0875 | [-0.1857, +0.0178] | 48 / 12 / 0 | ayırt edilemiyor |
| p_up D5 HitMiss | `base_rate` | 60 (27) | 0.1500 | 0.1667 | -0.0167 | [-0.1077, +0.0678] | 5 / 4 / 51 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 60 (27) | 0.3835 | 0.5229 | -0.1394 | [-0.2527, -0.0321] | 47 / 13 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_last10_rate` | 60 (27) | 0.3835 | 0.6931 | -0.3096 | [-0.4330, -0.1967] | 48 / 12 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `v1_5_h99` | 60 (27) | 0.3835 | 0.5679 | -0.1844 | [-0.4744, +0.0511] | 12 / 48 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `fall_d10_v0_addsale` | 60 (27) | 0.3835 | 0.5040 | -0.1205 | [-0.2259, -0.0228] | 46 / 14 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 HitMiss | `base_rate` | 60 (27) | 0.2000 | 0.2000 | +0.0000 | [-0.1071, +0.0952] | 7 / 7 / 46 | ayırt edilemiyor |

`fall_d10_v0_pooled`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| p_up D5 LogLoss | `base_rate` | 60 (27) | 0.3285 | 0.4601 | -0.1316 | [-0.2297, -0.0414] | 47 / 13 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `base_last10_rate` | 60 (27) | 0.1073 | 0.3267 | -0.2193 | [-0.2836, -0.1454] | 50 / 10 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `base_last10_rate` | 60 (27) | 0.3285 | 0.8487 | -0.5202 | [-0.6770, -0.3344] | 50 / 10 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `v1_5_h99` | 60 (27) | 0.3285 | 0.4861 | -0.1575 | [-0.4054, +0.0401] | 11 / 49 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `fall_d10_v0_addsale` | 60 (27) | 0.1073 | 0.1429 | -0.0356 | [-0.0618, -0.0109] | 45 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `fall_d10_v0_addsale` | 60 (27) | 0.3285 | 0.4525 | -0.1240 | [-0.1814, -0.0665] | 45 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 Brier | `fall_d10_v0_h99` | 60 (27) | 0.1073 | 0.1175 | -0.0102 | [-0.0371, +0.0150] | 11 / 49 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `fall_d10_v0_h99` | 60 (27) | 0.3285 | 0.3650 | -0.0365 | [-0.1187, +0.0387] | 11 / 49 / 0 | ayırt edilemiyor |
| p_up D5 Brier | `fall_d10_v0_pooled@ZERO` | 60 (27) | 0.1073 | 0.1391 | -0.0317 | [-0.0777, +0.0068] | 47 / 13 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `fall_d10_v0_pooled@ZERO` | 60 (27) | 0.3285 | 0.4512 | -0.1227 | [-0.2313, -0.0288] | 47 / 13 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 HitMiss | `base_rate` | 60 (27) | 0.2167 | 0.1667 | +0.0500 | [-0.0392, +0.1449] | 2 / 5 / 53 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 60 (27) | 0.3758 | 0.5229 | -0.1471 | [-0.2550, -0.0475] | 49 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `base_last10_rate` | 60 (27) | 0.3758 | 0.6931 | -0.3174 | [-0.4194, -0.2182] | 49 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `v1_5_h99` | 60 (27) | 0.3758 | 0.5679 | -0.1921 | [-0.4988, +0.0643] | 14 / 46 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `fall_d10_v0_addsale` | 60 (27) | 0.3758 | 0.5040 | -0.1283 | [-0.1994, -0.0619] | 45 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `fall_d10_v0_h99` | 60 (27) | 0.3758 | 0.3835 | -0.0077 | [-0.0608, +0.0486] | 16 / 44 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `fall_d10_v0_pooled@ZERO` | 60 (27) | 0.3758 | 0.5055 | -0.1297 | [-0.2544, -0.0189] | 46 / 14 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 HitMiss | `base_rate` | 60 (27) | 0.1833 | 0.2000 | -0.0167 | [-0.1321, +0.0862] | 6 / 5 / 49 | ayırt edilemiyor |

`fall_d10_v0_addsale`:

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| p_up D5 LogLoss | `base_rate` | 62 (29) | 0.4427 | 0.4534 | -0.0106 | [-0.0885, +0.0637] | 47 / 15 / 0 | ayırt edilemiyor |
| p_up D5 LogLoss | `base_last10_rate` | 62 (29) | 0.4427 | 0.8509 | -0.4082 | [-0.5632, -0.2206] | 52 / 10 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D5 LogLoss | `v1_5_h99` | 60 (27) | 0.4525 | 0.4861 | -0.0335 | [-0.2677, +0.1586] | 13 / 47 / 0 | ayırt edilemiyor |
| p_up D5 HitMiss | `base_rate` | 62 (29) | 0.2419 | 0.1613 | +0.0806 | [-0.0299, +0.1905] | 4 / 9 / 49 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_rate` | 62 (29) | 0.4947 | 0.5172 | -0.0225 | [-0.1258, +0.0664] | 47 / 15 / 0 | ayırt edilemiyor |
| p_up D10 LogLoss | `base_last10_rate` | 62 (29) | 0.4947 | 0.6931 | -0.1985 | [-0.2937, -0.1071] | 47 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| p_up D10 LogLoss | `v1_5_h99` | 60 (27) | 0.5040 | 0.5679 | -0.0639 | [-0.3811, +0.2007] | 13 / 47 / 0 | ayırt edilemiyor |
| p_up D10 HitMiss | `base_rate` | 62 (29) | 0.2419 | 0.1935 | +0.0484 | [-0.0938, +0.1724] | 5 / 8 / 49 | ayırt edilemiyor |

Kasa OOT_RETRO: 0 (model, arz) çifti; hiçbir n'e girmez.

## 9. Zaman-dışı test, toplam (açık küme + kasa): yalnız açık kümede de OOT_BLIND olan modeller; açık kümesi OOT_RETRO olan model için tanımsız

- Ayrı anahtar `oot_pre_h99_all`: açık küme + kasa, yalnız açık kümede OOT_BLIND olan modeller (SPEC_HAZARD_V1 §7.1-5). Açık küme satırları OOT_RETRO olan modeller birleştirilmez: `ceiling_hazard_v1_clip`, `ceiling_hazard_v1_real`, `ceiling_hazard_v1_pooled`, `ceiling_hazard_v1_pooled@INF`, `fall_d10_v0_h99`, `fall_d10_v0_pooled`, `fall_d10_v0_addsale`, `fall_d10_v0_pooled@ZERO`.

| MEMBER | açık küme | kasa (SEALED) | tabloya giren |
|---|---|---|---|
| 135 | 71 | 64 | 135 |

| Model | tür | skorlanan | ret | rejimle uygulanamaz | hedef oluşmadı | bekleyen | atlanan | OOT_RETRO |
|---|---|---|---|---|---|---|---|---|
| `v1_5_h99` | linear | 130 | 5 | 0 | 0 | 0 | 0 | 0 |
| `base_always_ceiling` | rule | 134 | 0 | 1 | 0 | 0 | 0 | 0 |
| `base_train_median` | rule | 135 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_train_mean` | rule | 135 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_zero` | rule | 135 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_rate` | rule | 135 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_last10_rate` | rule | 135 | 0 | 0 | 0 | 0 | 0 | 0 |
| `v1_6_h99` | linear | 130 | 5 | 0 | 0 | 0 | 0 | 0 |
| `v1_5_market20_v0` | market20 | 130 | 5 | 0 | 0 | 0 | 0 | 0 |
| `pb_v0` | pb | 112 | 23 | 0 | 0 | 0 | 0 | 0 |
| `ceiling_hazard_v0` | hazard | 130 | 5 | 0 | 0 | 0 | 0 | 0 |
| `ceiling_hazard_v0@INF` | hazard | 134 | 0 | 1 | 0 | 0 | 0 | 0 |
| `pb_ceiling_v0` | hazard | 112 | 23 | 0 | 0 | 0 | 0 | 0 |
| `pb_ceiling_v0@INF` | hazard | 134 | 0 | 1 | 0 | 0 | 0 | 0 |
| `base_km_expanding` | km | 135 | 0 | 0 | 0 | 0 | 0 | 0 |
| `base_km_last10` | km | 135 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ceiling_path_v0` | ceiling_path | 127 | 4 | 4 | 0 | 0 | 0 | 0 |
| `ceiling_path_v0@INF` | ceiling_path | 134 | 0 | 1 | 0 | 0 | 0 | 0 |
| `pb_ceiling_path_v0` | ceiling_path | 109 | 22 | 4 | 0 | 0 | 0 | 0 |

### 9.1 Birincil hücreler

| Model | Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| `v1_5_h99` | return D5 MAE | `base_train_median` | 130 (31) | 0.2381 | 0.2585 | -0.0204 | [-0.0613, +0.0166] | 68 / 62 / 0 | ayırt edilemiyor |
| `v1_6_h99` | return D10 MAE | `v1_5_h99` | 130 (31) | 0.7234 | 0.7230 | +0.0004 | [+0.0002, +0.0006] | 27 / 78 / 25 | geçemiyor |
| `v1_5_market20_v0` | return D5 MAE | `v1_5_h99` | 130 (31) | 0.2342 | 0.2381 | -0.0039 | [-0.0138, +0.0051] | 43 / 31 / 56 | ayırt edilemiyor |
| `pb_v0` | return D5 MAE | `base_train_median` | 112 (34) | 0.2616 | 0.2516 | +0.0100 | [-0.0323, +0.0475] | 54 / 58 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v0` | S RPS | `base_km_expanding` | 130 (31) | 0.2695 | 0.1988 | +0.0706 | [+0.0124, +0.1257] | 51 / 79 / 0 | geçemiyor |
| `pb_ceiling_v0` | S RPS | `base_km_expanding` | 112 (34) | 0.2588 | 0.2029 | +0.0560 | [+0.0042, +0.1090] | 42 / 70 / 0 | geçemiyor |
| `ceiling_path_v0` | return D5 MAE | `base_train_median` | 127 (31) | 0.2525 | 0.2569 | -0.0044 | [-0.0526, +0.0383] | 63 / 64 / 0 | ayırt edilemiyor |
| `pb_ceiling_path_v0` | return D5 MAE | `base_train_median` | 109 (33) | 0.2554 | 0.2440 | +0.0114 | [-0.0382, +0.0565] | 48 / 61 / 0 | ayırt edilemiyor |

## 10. Zaman-dışı test, D1 sonrası, kasa (tek seferlik açılış; makine sıralı: makine bütün zip'i gördü, insan görmedi)

- Ayrı anahtar `post_d1_sealed`, ayrı ölçek (`OOT_PRE_H99_POST_D1_MACHINE_SEQUENCED`): yalnız kasadaki (SEALED) üyeler; §6 (açık küme) ve §11 (toplam) ile toplanmaz. Formül, satır kapısı, birincil hücre ve payda sayaçları §6 ile aynı (SPEC_DEVIATIONS M-F); satırlar `exposure_class = MACHINE_SEQUENCED`.

| Model | satır | skorlanan | ret | hedef oluşmadı | bekleyen | S_1 = 0 | D1 tavan değil | D1 etiketi NA | D1 bekleniyor | atlanan (S2 kaydı olan) | OOT_RETRO | kasa |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `post_d1_hazard_v0` | 47 | 45 | 2 | 0 | 0 | 0 | 17 | 0 | 0 | 0 (0) | 0 | 64 |

| Model | Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| `post_d1_hazard_v0` | S_cond RPS | `ceiling_hazard_v0` | 45 (25) | 0.2582 | 0.2929 | -0.0347 | [-0.0715, +0.0044] | 19 / 26 / 0 | ayırt edilemiyor |

Öbür hücreler, `post_d1_hazard_v0` (keşif; kod etiketi parantez içinde):

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| S_cond RPS (kural) | `ceiling_hazard_v0@INF` | 45 (25) | 0.2582 | 0.1879 | +0.0703 | [-0.0124, +0.1596] | 19 / 26 / 0 | ayırt edilemiyor |
| S_cond RPS (kural) | `base_km_expanding` | 45 (25) | 0.2582 | 0.1883 | +0.0699 | [-0.0125, +0.1588] | 19 / 26 / 0 | ayırt edilemiyor |
| S_cond RPS (kural) | `base_km_last10` | 45 (25) | 0.2582 | 0.1984 | +0.0599 | [-0.0397, +0.1649] | 17 / 28 / 0 | ayırt edilemiyor |
| S_cond RPS (kural) | `base_always_ceiling` | 45 (25) | 0.2582 | 0.5210 | -0.2627 | [-0.3647, -0.1512] | 34 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| S_cond 2 Brier (ikincil) | `ceiling_hazard_v0` | 45 (25) | 0.0598 | 0.0654 | -0.0056 | [-0.0190, +0.0063] | 38 / 7 / 0 | ayırt edilemiyor |
| S_cond 2 Brier (ikincil) | `ceiling_hazard_v0@INF` | 45 (25) | 0.0598 | 0.0635 | -0.0037 | [-0.0110, +0.0058] | 40 / 5 / 0 | ayırt edilemiyor |
| S_cond 2 Brier (ikincil) | `base_km_expanding` | 45 (25) | 0.0598 | 0.0670 | -0.0072 | [-0.0151, +0.0032] | 41 / 4 / 0 | ayırt edilemiyor |
| S_cond 2 Brier (ikincil) | `base_km_last10` | 45 (25) | 0.0598 | 0.0800 | -0.0202 | [-0.0343, -0.0029] | 40 / 5 / 0 | geçiyor (zaman-dışı terazide) |
| S_cond 2 Brier (ikincil) | `base_always_ceiling` | 45 (25) | 0.0598 | 0.0667 | -0.0069 | [-0.0260, +0.0088] | 3 / 42 / 0 | ayırt edilemiyor |
| S_cond 10 Brier (ikincil) | `ceiling_hazard_v0` | 45 (25) | 0.2953 | 0.3160 | -0.0206 | [-0.0614, +0.0224] | 18 / 27 / 0 | ayırt edilemiyor |
| S_cond 10 Brier (ikincil) | `ceiling_hazard_v0@INF` | 45 (25) | 0.2953 | 0.1463 | +0.1490 | [+0.0154, +0.2813] | 15 / 30 / 0 | geçemiyor |
| S_cond 10 Brier (ikincil) | `base_km_expanding` | 45 (25) | 0.2953 | 0.1462 | +0.1491 | [+0.0175, +0.2798] | 15 / 30 / 0 | geçemiyor |
| S_cond 10 Brier (ikincil) | `base_km_last10` | 45 (25) | 0.2953 | 0.1498 | +0.1455 | [-0.0005, +0.2878] | 14 / 31 / 0 | ayırt edilemiyor |
| S_cond 10 Brier (ikincil) | `base_always_ceiling` | 45 (25) | 0.2953 | 0.8222 | -0.5269 | [-0.6784, -0.3515] | 37 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| return_cond D3 MAE (ikincil) | `ceiling_path_v0` | 44 (25) | 0.0519 | 0.0473 | +0.0046 | [+0.0000, +0.0160] | 0 / 1 / 43 | ayırt edilemiyor |
| return_cond D5 MAE (ikincil) | `ceiling_path_v0` | 44 (25) | 0.1740 | 0.1953 | -0.0212 | [-0.0493, +0.0090] | 7 / 3 / 34 | ayırt edilemiyor |
| return_cond D10 MAE (ikincil) | `ceiling_path_v0` | 44 (25) | 0.6829 | 0.7841 | -0.1011 | [-0.1844, -0.0096] | 13 / 10 / 21 | geçiyor (zaman-dışı terazide) |
| p_up_cond D3 Brier (ikincil) | `ceiling_path_v0` | 44 (25) | 0.0223 | 0.0229 | -0.0006 | [-0.0059, +0.0039] | 35 / 9 / 0 | ayırt edilemiyor |
| p_up_cond D5 Brier (ikincil) | `ceiling_path_v0` | 44 (25) | 0.0243 | 0.0240 | +0.0003 | [-0.0088, +0.0089] | 35 / 9 / 0 | ayırt edilemiyor |
| p_up_cond D10 Brier (ikincil) | `ceiling_path_v0` | 44 (25) | 0.0492 | 0.0479 | +0.0013 | [-0.0129, +0.0151] | 34 / 10 / 0 | ayırt edilemiyor |

## 11. Zaman-dışı test, D1 sonrası, toplam (açık küme + kasa; makine sıralı): yalnız açık kümede de OOT_BLIND olan POST_D1 modelleri

- Ayrı anahtar `post_d1_all`: açık küme + kasa, yalnız açık kümede OOT_BLIND olan POST_D1 modelleri; §6 ve §10 ile toplanmaz. Açık kümesi OOT_BLIND olmayan modeller birleştirilmez: yok.

| Model | satır | skorlanan | ret | hedef oluşmadı | bekleyen | S_1 = 0 | D1 tavan değil | D1 etiketi NA | D1 bekleniyor | atlanan (S2 kaydı olan) | OOT_RETRO | toplam |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `post_d1_hazard_v0` | 109 | 104 | 5 | 0 | 0 | 0 | 26 | 0 | 0 | 0 (0) | 0 | 135 |

| Model | Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| `post_d1_hazard_v0` | S_cond RPS | `ceiling_hazard_v0` | 104 (30) | 0.2563 | 0.2950 | -0.0387 | [-0.0604, -0.0173] | 54 / 50 / 0 | geçiyor (zaman-dışı terazide) |

Öbür hücreler, `post_d1_hazard_v0` (keşif; kod etiketi parantez içinde):

| Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| S_cond RPS (kural) | `ceiling_hazard_v0@INF` | 104 (30) | 0.2563 | 0.1971 | +0.0591 | [+0.0041, +0.1139] | 43 / 61 / 0 | geçemiyor |
| S_cond RPS (kural) | `base_km_expanding` | 104 (30) | 0.2563 | 0.1971 | +0.0591 | [+0.0041, +0.1135] | 44 / 60 / 0 | geçemiyor |
| S_cond RPS (kural) | `base_km_last10` | 104 (30) | 0.2563 | 0.2072 | +0.0490 | [-0.0187, +0.1163] | 43 / 61 / 0 | ayırt edilemiyor |
| S_cond RPS (kural) | `base_always_ceiling` | 104 (30) | 0.2563 | 0.5192 | -0.2630 | [-0.3416, -0.1744] | 84 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| S_cond 2 Brier (ikincil) | `ceiling_hazard_v0` | 104 (30) | 0.1194 | 0.1304 | -0.0110 | [-0.0212, -0.0024] | 85 / 19 / 0 | geçiyor (zaman-dışı terazide) |
| S_cond 2 Brier (ikincil) | `ceiling_hazard_v0@INF` | 104 (30) | 0.1194 | 0.1176 | +0.0018 | [-0.0066, +0.0119] | 85 / 19 / 0 | ayırt edilemiyor |
| S_cond 2 Brier (ikincil) | `base_km_expanding` | 104 (30) | 0.1194 | 0.1165 | +0.0029 | [-0.0081, +0.0167] | 89 / 15 / 0 | ayırt edilemiyor |
| S_cond 2 Brier (ikincil) | `base_km_last10` | 104 (30) | 0.1194 | 0.1208 | -0.0014 | [-0.0203, +0.0212] | 87 / 17 / 0 | ayırt edilemiyor |
| S_cond 2 Brier (ikincil) | `base_always_ceiling` | 104 (30) | 0.1194 | 0.1346 | -0.0152 | [-0.0305, -0.0025] | 14 / 90 / 0 | geçiyor (zaman-dışı terazide) |
| S_cond 10 Brier (ikincil) | `ceiling_hazard_v0` | 104 (30) | 0.3148 | 0.3320 | -0.0172 | [-0.0432, +0.0100] | 46 / 58 / 0 | ayırt edilemiyor |
| S_cond 10 Brier (ikincil) | `ceiling_hazard_v0@INF` | 104 (30) | 0.3148 | 0.1367 | +0.1781 | [+0.1010, +0.2614] | 32 / 72 / 0 | geçemiyor |
| S_cond 10 Brier (ikincil) | `base_km_expanding` | 104 (30) | 0.3148 | 0.1368 | +0.1780 | [+0.1017, +0.2600] | 32 / 72 / 0 | geçemiyor |
| S_cond 10 Brier (ikincil) | `base_km_last10` | 104 (30) | 0.3148 | 0.1389 | +0.1759 | [+0.0909, +0.2672] | 30 / 74 / 0 | geçemiyor |
| S_cond 10 Brier (ikincil) | `base_always_ceiling` | 104 (30) | 0.3148 | 0.8365 | -0.5217 | [-0.6393, -0.3794] | 87 / 17 / 0 | geçiyor (zaman-dışı terazide) |
| return_cond D3 MAE (ikincil) | `ceiling_path_v0` | 102 (30) | 0.0622 | 0.0602 | +0.0020 | [+0.0000, +0.0065] | 0 / 1 / 101 | ayırt edilemiyor |
| return_cond D5 MAE (ikincil) | `ceiling_path_v0` | 102 (30) | 0.1785 | 0.2054 | -0.0269 | [-0.0400, -0.0128] | 20 / 5 / 77 | geçiyor (zaman-dışı terazide) |
| return_cond D10 MAE (ikincil) | `ceiling_path_v0` | 102 (30) | 0.6932 | 0.7988 | -0.1055 | [-0.1638, -0.0474] | 36 / 19 / 47 | geçiyor (zaman-dışı terazide) |
| p_up_cond D3 Brier (ikincil) | `ceiling_path_v0` | 102 (30) | 0.0381 | 0.0391 | -0.0010 | [-0.0044, +0.0015] | 73 / 29 / 0 | ayırt edilemiyor |
| p_up_cond D5 Brier (ikincil) | `ceiling_path_v0` | 102 (30) | 0.0559 | 0.0597 | -0.0039 | [-0.0116, +0.0022] | 77 / 25 / 0 | ayırt edilemiyor |
| p_up_cond D10 Brier (ikincil) | `ceiling_path_v0` | 102 (30) | 0.0844 | 0.0896 | -0.0052 | [-0.0176, +0.0047] | 74 / 28 / 0 | ayırt edilemiyor |

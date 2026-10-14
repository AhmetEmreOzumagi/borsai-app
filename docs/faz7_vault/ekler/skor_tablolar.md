### Kasa birincil hücreleri

| Model | Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| `v1_5_h99` | return D5 MAE | `base_train_median` | 62 (27) | 0.2463 | 0.2581 | −0.0119 | [−0.0706, +0.0412] | 32 / 30 / 0 | ayırt edilemiyor |
| `v1_6_h99` | return D10 MAE | `v1_5_h99` | 62 (27) | 0.6972 | 0.6968 | +0.000399 | [+0.000116, +0.000654] | 14 / 38 / 10 | geçemiyor |
| `v1_5_market20_v0` | return D5 MAE | `v1_5_h99` | 62 (27) | 0.2402 | 0.2463 | −0.0061 | [−0.0186, +0.0056] | 23 / 14 / 25 | ayırt edilemiyor |
| `pb_v0` | return D5 MAE | `base_train_median` | 53 (26) | 0.2858 | 0.2555 | +0.0303 | [−0.0263, +0.0883] | 24 / 29 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v0` | S RPS | `base_km_expanding` | 62 (27) | 0.2701 | 0.1973 | +0.0728 | [−0.000814, +0.1388] | 26 / 36 / 0 | ayırt edilemiyor |
| `pb_ceiling_v0` | S RPS | `base_km_expanding` | 53 (26) | 0.2659 | 0.2006 | +0.0653 | [−0.0042, +0.1329] | 20 / 33 / 0 | ayırt edilemiyor |
| `ceiling_path_v0` | return D5 MAE | `base_train_median` | 60 (27) | 0.2564 | 0.2545 | +0.0019 | [−0.0704, +0.0684] | 28 / 32 / 0 | ayırt edilemiyor |
| `pb_ceiling_path_v0` | return D5 MAE | `base_train_median` | 51 (25) | 0.2738 | 0.2391 | +0.0346 | [−0.0366, +0.1018] | 21 / 30 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_clip` | S RPS | `base_km_expanding` | 62 (27) | 0.2306 | 0.1973 | +0.0334 | [−0.0260, +0.0886] | 26 / 36 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_real` | S RPS | `base_km_expanding` | 62 (27) | 0.1862 | 0.1973 | −0.0110 | [−0.0500, +0.0259] | 39 / 23 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_pooled` | S RPS | `base_km_expanding` | 62 (27) | 0.1573 | 0.1973 | −0.0400 | [−0.0671, −0.0122] | 42 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| `fall_d10_v0_h99` | p_up D10 Brier | `base_rate` | 60 (27) | 0.1288 | 0.1686 | −0.0398 | [−0.0878, +0.0043] | 47 / 13 / 0 | ayırt edilemiyor |
| `fall_d10_v0_pooled` | p_up D10 Brier | `base_rate` | 60 (27) | 0.1234 | 0.1686 | −0.0452 | [−0.0923, −0.0020] | 49 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| `fall_d10_v0_addsale` | p_up D10 Brier | `base_rate` | 62 (29) | 0.1601 | 0.1660 | −0.0058 | [−0.0541, +0.0358] | 47 / 15 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` | S_cond RPS, j = 1 (ayrı ölçek, MACHINE_SEQUENCED) | `ceiling_hazard_v0` | 45 (25) | 0.2582 | 0.2929 | −0.0347 | [−0.0715, +0.0044] | 19 / 26 / 0 | ayırt edilemiyor |

### Kasa satır sayaçları (64 üye; hedef oluşmadı, bekleyen, atlanan, OOT_RETRO her modelde 0)

| Model | skorlanan | ret (kod) | rejimle uygulanamaz |
|---|---|---|---|
| `v1_5_h99` | 62 | 2 (F3_MISSING 2) | 0 |
| `base_always_ceiling` (kural satırı) | 63 | 0 | 1 (MARGIN_NOT_10PCT 1) |
| `base_train_median` (kural satırı) | 64 | 0 | 0 |
| `base_train_mean` (kural satırı) | 64 | 0 | 0 |
| `base_zero` (kural satırı) | 64 | 0 | 0 |
| `base_rate` (kural satırı) | 64 | 0 | 0 |
| `base_last10_rate` (kural satırı) | 64 | 0 | 0 |
| `v1_6_h99` | 62 | 2 (F3_MISSING 2) | 0 |
| `v1_5_market20_v0` | 62 | 2 (F3_MISSING 2) | 0 |
| `pb_v0` | 53 | 11 (PB_IDENTITY 6, PB_PRICE_RANGE 5) | 0 |
| `ceiling_hazard_v0` | 62 | 2 (F3_MISSING 2) | 0 |
| `ceiling_hazard_v0@INF` (kural satırı) | 63 | 0 | 1 (MARGIN_NOT_10PCT 1) |
| `pb_ceiling_v0` | 53 | 11 (PB_IDENTITY 6, PB_PRICE_RANGE 5) | 0 |
| `pb_ceiling_v0@INF` (kural satırı) | 63 | 0 | 1 (MARGIN_NOT_10PCT 1) |
| `base_km_expanding` (kural satırı) | 64 | 0 | 0 |
| `base_km_last10` (kural satırı) | 64 | 0 | 0 |
| `ceiling_path_v0` | 60 | 1 (F3_MISSING 1) | 3 (MARGIN_NOT_10PCT 1, TICK_TABLE_MISMATCH 2) |
| `ceiling_path_v0@INF` (kural satırı) | 63 | 0 | 1 (MARGIN_NOT_10PCT 1) |
| `pb_ceiling_path_v0` | 51 | 10 (PB_IDENTITY 5, PB_PRICE_RANGE 5) | 3 (MARGIN_NOT_10PCT 1, TICK_TABLE_MISMATCH 2) |
| `ceiling_hazard_v1_clip` | 62 | 2 (F3_MISSING 2) | 0 |
| `ceiling_hazard_v1_real` | 62 | 2 (F3_MISSING 2) | 0 |
| `ceiling_hazard_v1_pooled` | 62 | 2 (F3_MISSING 2) | 0 |
| `ceiling_hazard_v1_pooled@INF` (kural satırı) | 63 | 0 | 1 (MARGIN_NOT_10PCT 1) |
| `fall_d10_v0_h99` | 60 | 4 (ADDITIONAL_SALE_MISSING 2, F3_MISSING 2) | 0 |
| `fall_d10_v0_pooled` | 60 | 4 (ADDITIONAL_SALE_MISSING 2, F3_MISSING 2) | 0 |
| `fall_d10_v0_addsale` | 62 | 2 (ADDITIONAL_SALE_MISSING 2) | 0 |
| `fall_d10_v0_pooled@ZERO` (kural satırı) | 64 | 0 | 0 |

### Kasa ilan edilmiş ikinciller

| Model | Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | S RPS | `ceiling_hazard_v0` | 62 (27) | 0.2306 | 0.2701 | −0.0395 | [−0.0640, −0.0161] | 42 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_clip` | S RPS | `ceiling_hazard_v0@INF` | 62 (27) | 0.2306 | 0.1982 | +0.0325 | [−0.0258, +0.0865] | 27 / 35 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_clip` | S 10 Brier | `base_km_expanding` | 62 (27) | 0.1819 | 0.1125 | +0.0693 | [−0.0152, +0.1463] | 23 / 39 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_clip` | S 10 Brier | `ceiling_hazard_v0` | 62 (27) | 0.1819 | 0.2433 | −0.0615 | [−0.0939, −0.0271] | 42 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_real` | S RPS | `ceiling_hazard_v0` | 62 (27) | 0.1862 | 0.2701 | −0.0839 | [−0.1279, −0.0347] | 47 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_real` | S RPS | `ceiling_hazard_v0@INF` | 62 (27) | 0.1862 | 0.1982 | −0.0119 | [−0.0509, +0.0254] | 39 / 23 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_real` | S RPS | `ceiling_hazard_v1_clip` | 62 (27) | 0.1862 | 0.2306 | −0.0444 | [−0.0733, −0.0113] | 47 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_real` | S 10 Brier | `base_km_expanding` | 62 (27) | 0.1317 | 0.1125 | +0.0192 | [−0.0397, +0.0733] | 33 / 29 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_real` | S 10 Brier | `ceiling_hazard_v0` | 62 (27) | 0.1317 | 0.2433 | −0.1116 | [−0.1633, −0.0531] | 52 / 10 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_pooled` | S RPS | `ceiling_hazard_v0` | 62 (27) | 0.1573 | 0.2701 | −0.1128 | [−0.1808, −0.0381] | 42 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_pooled` | S RPS | `ceiling_hazard_v0@INF` | 62 (27) | 0.1573 | 0.1982 | −0.0409 | [−0.0692, −0.0117] | 40 / 22 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_pooled` | S RPS | `ceiling_hazard_v1_real` | 62 (27) | 0.1573 | 0.1862 | −0.0290 | [−0.0588, +0.0037] | 37 / 25 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_pooled` | S RPS | `ceiling_hazard_v1_pooled@INF` | 62 (27) | 0.1573 | 0.1926 | −0.0354 | [−0.0625, −0.0073] | 42 / 20 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_pooled` | S 10 Brier | `base_km_expanding` | 62 (27) | 0.0972 | 0.1125 | −0.0153 | [−0.0492, +0.0161] | 47 / 15 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v1_pooled` | S 10 Brier | `ceiling_hazard_v0` | 62 (27) | 0.0972 | 0.2433 | −0.1461 | [−0.2171, −0.0627] | 51 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| `ceiling_hazard_v1_pooled` | S 10 Brier | `ceiling_hazard_v1_pooled@INF` | 62 (27) | 0.0972 | 0.1103 | −0.0130 | [−0.0516, +0.0217] | 46 / 16 / 0 | ayırt edilemiyor |
| `fall_d10_v0_h99` | p_up D5 Brier | `base_rate` | 60 (27) | 0.1175 | 0.1420 | −0.0244 | [−0.0626, +0.0105] | 49 / 11 / 0 | ayırt edilemiyor |
| `fall_d10_v0_h99` | p_up D5 Brier | `v1_5_h99` | 60 (27) | 0.1175 | 0.1300 | −0.0125 | [−0.0509, +0.0208] | 16 / 44 / 0 | ayırt edilemiyor |
| `fall_d10_v0_h99` | p_up D10 Brier | `base_last10_rate` | 60 (27) | 0.1288 | 0.2500 | −0.1212 | [−0.1695, −0.0773] | 48 / 12 / 0 | geçiyor (zaman-dışı terazide) |
| `fall_d10_v0_h99` | p_up D10 Brier | `v1_5_h99` | 60 (27) | 0.1288 | 0.1539 | −0.0250 | [−0.0906, +0.0302] | 12 / 48 / 0 | ayırt edilemiyor |
| `fall_d10_v0_h99` | p_up D10 Brier | `fall_d10_v0_addsale` | 60 (27) | 0.1288 | 0.1642 | −0.0354 | [−0.0813, +0.0063] | 46 / 14 / 0 | ayırt edilemiyor |
| `fall_d10_v0_pooled` | p_up D5 Brier | `base_rate` | 60 (27) | 0.1073 | 0.1420 | −0.0346 | [−0.0756, +0.0012] | 47 / 13 / 0 | ayırt edilemiyor |
| `fall_d10_v0_pooled` | p_up D5 Brier | `v1_5_h99` | 60 (27) | 0.1073 | 0.1300 | −0.0227 | [−0.0696, +0.0216] | 11 / 49 / 0 | ayırt edilemiyor |
| `fall_d10_v0_pooled` | p_up D10 Brier | `base_last10_rate` | 60 (27) | 0.1234 | 0.2500 | −0.1266 | [−0.1682, −0.0853] | 49 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| `fall_d10_v0_pooled` | p_up D10 Brier | `v1_5_h99` | 60 (27) | 0.1234 | 0.1539 | −0.0304 | [−0.1003, +0.0320] | 14 / 46 / 0 | ayırt edilemiyor |
| `fall_d10_v0_pooled` | p_up D10 Brier | `fall_d10_v0_addsale` | 60 (27) | 0.1234 | 0.1642 | −0.0408 | [−0.0723, −0.0114] | 45 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| `fall_d10_v0_pooled` | p_up D10 Brier | `fall_d10_v0_h99` | 60 (27) | 0.1234 | 0.1288 | −0.0054 | [−0.0272, +0.0188] | 16 / 44 / 0 | ayırt edilemiyor |
| `fall_d10_v0_pooled` | p_up D10 Brier | `fall_d10_v0_pooled@ZERO` | 60 (27) | 0.1234 | 0.1618 | −0.0384 | [−0.0922, +0.0099] | 46 / 14 / 0 | ayırt edilemiyor |
| `fall_d10_v0_addsale` | p_up D5 Brier | `base_rate` | 62 (29) | 0.1389 | 0.1390 | −0.000088 | [−0.0328, +0.0304] | 47 / 15 / 0 | ayırt edilemiyor |
| `fall_d10_v0_addsale` | p_up D5 Brier | `base_last10_rate` | 62 (29) | 0.1389 | 0.3277 | −0.1888 | [−0.2534, −0.1105] | 52 / 10 / 0 | geçiyor (zaman-dışı terazide) |
| `fall_d10_v0_addsale` | p_up D5 Brier | `v1_5_h99` | 60 (27) | 0.1429 | 0.1300 | +0.0128 | [−0.0311, +0.0553] | 13 / 47 / 0 | ayırt edilemiyor |
| `fall_d10_v0_addsale` | p_up D10 Brier | `base_last10_rate` | 62 (29) | 0.1601 | 0.2500 | −0.0899 | [−0.1316, −0.0498] | 47 / 15 / 0 | geçiyor (zaman-dışı terazide) |
| `fall_d10_v0_addsale` | p_up D10 Brier | `v1_5_h99` | 60 (27) | 0.1642 | 0.1539 | +0.0104 | [−0.0667, +0.0780] | 13 / 47 / 0 | ayırt edilemiyor |

### post_d1 kasa: öbür hücreler (kod etiketi parantezde)

| Model | Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| `post_d1_hazard_v0` | S_cond RPS (kural) | `ceiling_hazard_v0@INF` | 45 (25) | 0.2582 | 0.1879 | +0.0703 | [−0.0124, +0.1596] | 19 / 26 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` | S_cond RPS (kural) | `base_km_expanding` | 45 (25) | 0.2582 | 0.1883 | +0.0699 | [−0.0125, +0.1588] | 19 / 26 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` | S_cond RPS (kural) | `base_km_last10` | 45 (25) | 0.2582 | 0.1984 | +0.0599 | [−0.0397, +0.1649] | 17 / 28 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` | S_cond RPS (kural) | `base_always_ceiling` | 45 (25) | 0.2582 | 0.5210 | −0.2627 | [−0.3647, −0.1512] | 34 / 11 / 0 | geçiyor (zaman-dışı terazide) |
| `post_d1_hazard_v0` | S_cond 2 Brier (ikincil) | `ceiling_hazard_v0` | 45 (25) | 0.0598 | 0.0654 | −0.0056 | [−0.0190, +0.0063] | 38 / 7 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` | S_cond 2 Brier (ikincil) | `ceiling_hazard_v0@INF` | 45 (25) | 0.0598 | 0.0635 | −0.0037 | [−0.0110, +0.0058] | 40 / 5 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` | S_cond 2 Brier (ikincil) | `base_km_expanding` | 45 (25) | 0.0598 | 0.0670 | −0.0072 | [−0.0151, +0.0032] | 41 / 4 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` | S_cond 2 Brier (ikincil) | `base_km_last10` | 45 (25) | 0.0598 | 0.0800 | −0.0202 | [−0.0343, −0.0029] | 40 / 5 / 0 | geçiyor (zaman-dışı terazide) |
| `post_d1_hazard_v0` | S_cond 2 Brier (ikincil) | `base_always_ceiling` | 45 (25) | 0.0598 | 0.0667 | −0.0069 | [−0.0260, +0.0088] | 3 / 42 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` | S_cond 10 Brier (ikincil) | `ceiling_hazard_v0` | 45 (25) | 0.2953 | 0.3160 | −0.0206 | [−0.0614, +0.0224] | 18 / 27 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` | S_cond 10 Brier (ikincil) | `ceiling_hazard_v0@INF` | 45 (25) | 0.2953 | 0.1463 | +0.1490 | [+0.0154, +0.2813] | 15 / 30 / 0 | geçemiyor |
| `post_d1_hazard_v0` | S_cond 10 Brier (ikincil) | `base_km_expanding` | 45 (25) | 0.2953 | 0.1462 | +0.1491 | [+0.0175, +0.2798] | 15 / 30 / 0 | geçemiyor |
| `post_d1_hazard_v0` | S_cond 10 Brier (ikincil) | `base_km_last10` | 45 (25) | 0.2953 | 0.1498 | +0.1455 | [−0.000452, +0.2878] | 14 / 31 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` | S_cond 10 Brier (ikincil) | `base_always_ceiling` | 45 (25) | 0.2953 | 0.8222 | −0.5269 | [−0.6784, −0.3515] | 37 / 8 / 0 | geçiyor (zaman-dışı terazide) |
| `post_d1_hazard_v0` | return_cond D3 MAE (ikincil) | `ceiling_path_v0` | 44 (25) | 0.0519 | 0.0473 | +0.0046 | [+0.0000, +0.0160] | 0 / 1 / 43 | ayırt edilemiyor |
| `post_d1_hazard_v0` | return_cond D5 MAE (ikincil) | `ceiling_path_v0` | 44 (25) | 0.1740 | 0.1953 | −0.0212 | [−0.0493, +0.0090] | 7 / 3 / 34 | ayırt edilemiyor |
| `post_d1_hazard_v0` | return_cond D10 MAE (ikincil) | `ceiling_path_v0` | 44 (25) | 0.6829 | 0.7841 | −0.1011 | [−0.1844, −0.0096] | 13 / 10 / 21 | geçiyor (zaman-dışı terazide) |
| `post_d1_hazard_v0` | p_up_cond D3 Brier (ikincil) | `ceiling_path_v0` | 44 (25) | 0.0223 | 0.0229 | −0.000552 | [−0.0059, +0.0039] | 35 / 9 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` | p_up_cond D5 Brier (ikincil) | `ceiling_path_v0` | 44 (25) | 0.0243 | 0.0240 | +0.000274 | [−0.0088, +0.0089] | 35 / 9 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` | p_up_cond D10 Brier (ikincil) | `ceiling_path_v0` | 44 (25) | 0.0492 | 0.0479 | +0.0013 | [−0.0129, +0.0151] | 34 / 10 / 0 | ayırt edilemiyor |

### Toplam (açık + kasa) birincil hücreleri

| Model | Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| `v1_5_h99` | return D5 MAE | `base_train_median` | 130 (31) | 0.2381 | 0.2585 | −0.0204 | [−0.0613, +0.0166] | 68 / 62 / 0 | ayırt edilemiyor |
| `v1_6_h99` | return D10 MAE | `v1_5_h99` | 130 (31) | 0.7234 | 0.7230 | +0.000408 | [+0.000232, +0.000580] | 27 / 78 / 25 | geçemiyor |
| `v1_5_market20_v0` | return D5 MAE | `v1_5_h99` | 130 (31) | 0.2342 | 0.2381 | −0.0039 | [−0.0138, +0.0051] | 43 / 31 / 56 | ayırt edilemiyor |
| `pb_v0` | return D5 MAE | `base_train_median` | 112 (34) | 0.2616 | 0.2516 | +0.0100 | [−0.0323, +0.0475] | 54 / 58 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v0` | S RPS | `base_km_expanding` | 130 (31) | 0.2695 | 0.1988 | +0.0706 | [+0.0124, +0.1257] | 51 / 79 / 0 | geçemiyor |
| `pb_ceiling_v0` | S RPS | `base_km_expanding` | 112 (34) | 0.2588 | 0.2029 | +0.0560 | [+0.0042, +0.1090] | 42 / 70 / 0 | geçemiyor |
| `ceiling_path_v0` | return D5 MAE | `base_train_median` | 127 (31) | 0.2525 | 0.2569 | −0.0044 | [−0.0526, +0.0383] | 63 / 64 / 0 | ayırt edilemiyor |
| `pb_ceiling_path_v0` | return D5 MAE | `base_train_median` | 109 (33) | 0.2554 | 0.2440 | +0.0114 | [−0.0382, +0.0565] | 48 / 61 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` | S_cond RPS, j = 1 (post_d1_all) | `ceiling_hazard_v0` | 104 (30) | 0.2563 | 0.2950 | −0.0387 | [−0.0604, −0.0173] | 54 / 50 / 0 | geçiyor (zaman-dışı terazide) |

### Açık küme birincil hücreleri (Faz 6 ile aynı; yan yana okuma için)

| Model | Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| `v1_5_h99` | return D5 MAE | `base_train_median` | 68 (28) | 0.2306 | 0.2588 | −0.0282 | [−0.0807, +0.0225] | 36 / 32 / 0 | ayırt edilemiyor |
| `v1_6_h99` | return D10 MAE | `v1_5_h99` | 68 (28) | 0.7472 | 0.7468 | +0.000415 | [+0.000259, +0.000573] | 13 / 40 / 15 | geçemiyor |
| `v1_5_market20_v0` | return D5 MAE | `v1_5_h99` | 68 (28) | 0.2288 | 0.2306 | −0.0018 | [−0.0112, +0.0059] | 20 / 17 / 31 | ayırt edilemiyor |
| `pb_v0` | return D5 MAE | `base_train_median` | 59 (28) | 0.2398 | 0.2480 | −0.0082 | [−0.0550, +0.0358] | 30 / 29 / 0 | ayırt edilemiyor |
| `ceiling_hazard_v0` | S RPS | `base_km_expanding` | 68 (28) | 0.2689 | 0.2002 | +0.0686 | [+0.0011, +0.1313] | 25 / 43 / 0 | geçemiyor |
| `pb_ceiling_v0` | S RPS | `base_km_expanding` | 59 (28) | 0.2525 | 0.2049 | +0.0476 | [−0.0050, +0.0999] | 22 / 37 / 0 | ayırt edilemiyor |
| `ceiling_path_v0` | return D5 MAE | `base_train_median` | 67 (28) | 0.2491 | 0.2591 | −0.0101 | [−0.0688, +0.0466] | 35 / 32 / 0 | ayırt edilemiyor |
| `pb_ceiling_path_v0` | return D5 MAE | `base_train_median` | 58 (28) | 0.2393 | 0.2482 | −0.0089 | [−0.0590, +0.0396] | 27 / 31 / 0 | ayırt edilemiyor |
| `post_d1_hazard_v0` | S_cond RPS, j = 1 (post_d1) | `ceiling_hazard_v0` | 59 (26) | 0.2548 | 0.2965 | −0.0418 | [−0.0664, −0.0201] | 35 / 24 / 0 | geçiyor (zaman-dışı terazide) |

### Kasa, ilk işlem yılı (ikincil; birincil hücre)

| Model | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|
| `v1_5_h99` | metrik yok (2) | +0.0812 [+0.0115, +0.1409] (26; yetersiz örnek) | −0.0455 [−0.1279, +0.0414] (18; yetersiz örnek) | −0.0977 [−0.1676, −0.0252] (16; yetersiz örnek) |
| `v1_6_h99` | metrik yok (2) | +0.000821 [+0.000522, +0.0011] (26; yetersiz örnek) | +0.000087 [−0.000441, +0.000473] (18; yetersiz örnek) | +0.000040 [−0.000297, +0.000450] (16; yetersiz örnek) |
| `v1_5_market20_v0` | metrik yok (2) | +0.0044 [−0.0033, +0.0157] (26; yetersiz örnek) | +0.000015 [−0.0147, +0.0182] (18; yetersiz örnek) | −0.0306 [−0.0517, −0.000217] (16; yetersiz örnek) |
| `pb_v0` | metrik yok (2) | +0.1211 [+0.0267, +0.1814] (19; yetersiz örnek) | +0.0080 [−0.0828, +0.1177] (16; yetersiz örnek) | −0.0232 [−0.0884, +0.0614] (16; yetersiz örnek) |
| `ceiling_hazard_v0` | metrik yok (2) | +0.1662 [+0.0802, +0.2324] (26; yetersiz örnek) | +0.0220 [−0.1206, +0.1633] (18; yetersiz örnek) | −0.0373 [−0.0846, +0.0477] (16; yetersiz örnek) |
| `pb_ceiling_v0` | metrik yok (2) | +0.1803 [+0.0638, +0.2554] (19; yetersiz örnek) | +0.0376 [−0.0906, +0.1567] (16; yetersiz örnek) | −0.0214 [−0.0465, +0.0203] (16; yetersiz örnek) |
| `ceiling_path_v0` | metrik yok (2) | +0.1288 [+0.0525, +0.1912] (25; yetersiz örnek) | −0.0461 [−0.1386, +0.0554] (18; yetersiz örnek) | −0.1204 [−0.1991, −0.0318] (15; yetersiz örnek) |
| `pb_ceiling_path_v0` | metrik yok (1) | +0.1351 [+0.0461, +0.1930] (19; yetersiz örnek) | +0.0176 [−0.1101, +0.1515] (16; yetersiz örnek) | −0.0570 [−0.1284, +0.0484] (15; yetersiz örnek) |
| `ceiling_hazard_v1_clip` | metrik yok (2) | +0.0887 [+0.0156, +0.1557] (26; yetersiz örnek) | +0.0046 [−0.1204, +0.1263] (18; yetersiz örnek) | −0.0407 [−0.0918, +0.0431] (16; yetersiz örnek) |
| `ceiling_hazard_v1_real` | metrik yok (2) | −0.0011 [−0.0495, +0.0430] (26; yetersiz örnek) | −0.0220 [−0.1099, +0.0711] (18; yetersiz örnek) | −0.0249 [−0.0894, +0.0407] (16; yetersiz örnek) |
| `ceiling_hazard_v1_pooled` | metrik yok (2) | −0.0661 [−0.1067, −0.0275] (26; yetersiz örnek) | −0.0221 [−0.0756, +0.0501] (18; yetersiz örnek) | −0.0270 [−0.0677, +0.0155] (16; yetersiz örnek) |
| `fall_d10_v0_h99` | metrik yok (2) | −0.0498 [−0.1251, +0.0204] (25; yetersiz örnek) | −0.0682 [−0.1642, +0.0111] (17; yetersiz örnek) | +0.0069 [−0.0790, +0.0821] (16; yetersiz örnek) |
| `fall_d10_v0_pooled` | metrik yok (2) | −0.0657 [−0.1459, +0.0074] (25; yetersiz örnek) | −0.0730 [−0.1508, −0.0173] (17; yetersiz örnek) | +0.0112 [−0.0758, +0.0784] (16; yetersiz örnek) |
| `fall_d10_v0_addsale` | metrik yok (4) | −0.0300 [−0.1207, +0.0422] (25; yetersiz örnek) | −0.0139 [−0.0887, +0.0277] (17; yetersiz örnek) | +0.0075 [−0.0485, +0.0580] (16; yetersiz örnek) |

### Kasa, rejim alt kümeleri (keşif; birincil hücre)

| Model | borsada satış | borsa dışı | PRE_20211111 | THRESH100_20211111 | EQUAL_DIST_20230330 |
|---|---|---|---|---|---|
| `v1_5_h99` | +0.0372 [−0.0593, +0.1122] (20; yetersiz örnek) | −0.0352 [−0.0966, +0.0250] (42; ayırt edilemiyor) | +0.0577 [−0.0290, +0.1308] (27; yetersiz örnek) | −0.0389 [−0.1099, +0.0395] (23; yetersiz örnek) | −0.1168 [−0.1869, −0.0552] (12; yetersiz örnek) |
| `v1_6_h99` | +0.000526 [+0.000015, +0.000942] (20; yetersiz örnek) | +0.000339 [+0.000046, +0.000588] (42; geçemiyor) | +0.000803 [+0.000523, +0.0011] (27; yetersiz örnek) | +0.000107 [−0.000286, +0.000431] (23; yetersiz örnek) | +0.000052 [−0.000346, +0.000609] (12; yetersiz örnek) |
| `v1_5_market20_v0` | −0.0082 [−0.0257, +0.0077] (20; yetersiz örnek) | −0.0050 [−0.0176, +0.0070] (42; ayırt edilemiyor) | +0.000668 [−0.0031, +0.0058] (27; yetersiz örnek) | +0.0037 [−0.0108, +0.0206] (23; yetersiz örnek) | −0.0398 [−0.0642, −0.0026] (12; yetersiz örnek) |
| `pb_v0` | +0.0388 [−0.0839, +0.1402] (20; yetersiz örnek) | +0.0251 [−0.0355, +0.0821] (33; ayırt edilemiyor) | +0.0828 [−0.0334, +0.1559] (20; yetersiz örnek) | +0.0318 [−0.0439, +0.1197] (21; yetersiz örnek) | −0.0600 [−0.1252, +0.0113] (12; yetersiz örnek) |
| `ceiling_hazard_v0` | +0.1049 [−0.0061, +0.1922] (20; yetersiz örnek) | +0.0575 [−0.0234, +0.1375] (42; ayırt edilemiyor) | +0.1688 [+0.0859, +0.2358] (27; yetersiz örnek) | +0.0245 [−0.0907, +0.1436] (23; yetersiz örnek) | −0.0505 [−0.0826, −0.0090] (12; yetersiz örnek) |
| `pb_ceiling_v0` | +0.1076 [−0.0356, +0.2260] (20; yetersiz örnek) | +0.0396 [−0.0223, +0.0960] (33; ayırt edilemiyor) | +0.1493 [+0.0093, +0.2364] (20; yetersiz örnek) | +0.0432 [−0.0541, +0.1334] (21; yetersiz örnek) | −0.0361 [−0.0552, +0.0046] (12; yetersiz örnek) |
| `ceiling_path_v0` | +0.0624 [−0.0635, +0.1625] (20; yetersiz örnek) | −0.0284 [−0.1002, +0.0433] (40; ayırt edilemiyor) | +0.0971 [−0.000318, +0.1743] (26; yetersiz örnek) | −0.0262 [−0.1085, +0.0671] (23; yetersiz örnek) | −0.1644 [−0.2334, −0.1028] (11; yetersiz örnek) |
| `pb_ceiling_path_v0` | +0.0390 [−0.1008, +0.1547] (19; yetersiz örnek) | +0.0320 [−0.0404, +0.1000] (32; ayırt edilemiyor) | +0.1112 [+0.0061, +0.1783] (19; yetersiz örnek) | +0.0243 [−0.0807, +0.1324] (21; yetersiz örnek) | −0.0779 [−0.1400, +0.0512] (11; yetersiz örnek) |
| `ceiling_hazard_v1_clip` | +0.0139 [−0.0435, +0.0571] (20; yetersiz örnek) | +0.0426 [−0.0320, +0.1165] (42; ayırt edilemiyor) | +0.0937 [+0.0237, +0.1601] (27; yetersiz örnek) | +0.0056 [−0.0982, +0.1136] (23; yetersiz örnek) | −0.0492 [−0.0834, −0.0083] (12; yetersiz örnek) |
| `ceiling_hazard_v1_real` | −0.0097 [−0.0547, +0.0259] (20; yetersiz örnek) | −0.0117 [−0.0619, +0.0430] (42; ayırt edilemiyor) | +0.0058 [−0.0435, +0.0511] (27; yetersiz örnek) | −0.0241 [−0.0985, +0.0559] (23; yetersiz örnek) | −0.0240 [−0.0927, +0.0282] (12; yetersiz örnek) |
| `ceiling_hazard_v1_pooled` | −0.0322 [−0.0717, +0.0160] (20; yetersiz örnek) | −0.0437 [−0.0773, −0.0028] (42; geçiyor (zaman-dışı terazide)) | −0.0559 [−0.0951, −0.0177] (27; yetersiz örnek) | −0.0294 [−0.0768, +0.0288] (23; yetersiz örnek) | −0.0244 [−0.0622, +0.0018] (12; yetersiz örnek) |
| `fall_d10_v0_h99` | −0.0373 [−0.0797, +0.0140] (19; yetersiz örnek) | −0.0410 [−0.1072, +0.0231] (41; ayırt edilemiyor) | −0.0493 [−0.1192, +0.0134] (26; yetersiz örnek) | −0.0703 [−0.1416, −0.0059] (22; yetersiz örnek) | +0.0367 [−0.0714, +0.1216] (12; yetersiz örnek) |
| `fall_d10_v0_pooled` | −0.0436 [−0.0687, −0.0179] (19; yetersiz örnek) | −0.0460 [−0.1105, +0.0172] (41; ayırt edilemiyor) | −0.0613 [−0.1377, +0.0054] (26; yetersiz örnek) | −0.0736 [−0.1312, −0.0277] (22; yetersiz örnek) | +0.0417 [−0.0700, +0.1134] (12; yetersiz örnek) |
| `fall_d10_v0_addsale` | −0.0295 [−0.0485, −0.0122] (21; yetersiz örnek) | +0.0063 [−0.0601, +0.0755] (41; ayırt edilemiyor) | −0.0071 [−0.0948, +0.0751] (28; yetersiz örnek) | −0.0217 [−0.0788, +0.0151] (22; yetersiz örnek) | +0.0262 [−0.0485, +0.0844] (12; yetersiz örnek) |

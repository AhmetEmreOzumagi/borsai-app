# Modeller ve backtest sonuçları

Bu sayfa `python -m borsai.report` ile üretilir; elle düzenlenmez. Kaynaklar: `models/INDEX.json` ve model dosyaları, `tests/reference/macos_golden/` (Faz 1A) ve `tests/reference/macos_golden_faz1b/` (Faz 1B) altındaki fold ledger'ları (bu makinedeki resmi backtest), `experiments/log.jsonl`.

**Terazi:** buradaki bütün sayılar **backtest**tir (retrospektif walk-forward, H99, ilk işlem 2023-09-22…2026-08-06). Canlı (prospektif) skor ayrı tutulur ve henüz yoktur (n = 0). İki terazi toplanmaz (CLAUDE.md kural 3).

- Veri sürümü: `data/data_version.json` sha256 `a0c7d082dacdbde03f53d1c4af1ce9f7983f9946abc80062de570f4a1df1f977`.
- Eğitim kesimi (dondurulmuş modeller): en son hedef seansı 2026-08-19, n = 99 (`ceiling_hazard_v0` ve `ceiling_hazard_v0@INF`: f3'ü dolu 97 arz).
- Çalışma ortamı: Darwin 27.0.0 arm64 / CPython 3.12.14; joblib 1.5.3, numpy 2.5.2, python 3.12.14, scikit-learn 1.9.0, scipy 1.18.0, threadpoolctl 3.6.0.

## Kayıtlı modeller

| model_id | Ne yapar | Çıktı | Eğitim n | Kesim | Dosya sha256 (ilk 12) | Şartname sha256 (ilk 12) | Günlükteki koşu sayısı |
|---|---|---|---|---|---|---|---|
| `v1_5_h99` | V1.5 (BORSAI_V1_5_PREREG_20260814) portu: ufuk başına Ridge (getiri) ve L2-lojistik (P(kapanış > arz)), f1–f5, fold içi V1.3 ön işleme, iç LOOCV ile hiperparametre seçimi. | getiri, P(kapanış > arz) | 99 | 2026-08-19 | `bf809859f61e` | `a37ab09d4048` | 2 |
| `base_always_ceiling` | Her seans tavan: getiri = 1.1^h − 1; P(kapanış > arz) = 1. | getiri, P(kapanış > arz) | 0 | — | `0b27057479bd` | `ed1815f898c3` | 8 |
| `base_train_median` | Getiri = eğitimdeki R_h'lerin medyanı (legacy V1_BASE_MEDIAN). | getiri | 99 | 2026-08-19 | `56bb6c786717` | `842a14f52939` | 4 |
| `base_train_mean` | Getiri = eğitimdeki R_h'lerin ortalaması (legacy V1_BASE_MEAN). | getiri | 99 | 2026-08-19 | `8315d19ee941` | `f94c2e58d8a4` | 4 |
| `base_zero` | Getiri = 0 (legacy V1_BASE_ZERO). | getiri | 0 | — | `9d2f8f82a325` | `1ae0f539e663` | 4 |
| `base_rate` | P(kapanış > arz) = eğitimdeki Y_h ortalaması (legacy V1_BASE_RATE). | P(kapanış > arz) | 99 | 2026-08-19 | `eb91ae3d429e` | `d094ba111980` | 4 |
| `base_last10_rate` | P(kapanış > arz) = eğitim sırasındaki (first_trading_date, ticker) son 10 arzın Y_h ortalaması (AUDIT §3b). | P(kapanış > arz) | 99 | 2026-08-19 | `8b0a098d1ad6` | `ff7dfd4084a1` | 4 |
| `v1_6_h99` | V1.5 + genişletilmiş ızgara (SPEC_V1_6): Ridge α ∈ {0.001 … 10000, INF}, Logit C ∈ {ZERO, 0.0001 … 100}; INF/ZERO kapalı biçim sabit terim; aday başına yakınsamama. Özellikler, ön işleme ve fold planı V1.5 ile aynı. | getiri, P(kapanış > arz) | 99 | 2026-08-19 | `b40b7cb54cde` | `7e3dd5ffe816` | 2 |
| `v1_5_market20_v0` | V1.5 aynen + f6 = XU100(S0)/XU100(S20) − 1 (20 seanslık endeks getirisi, Takvim B, ref_date = T; SPEC_MARKET20_V0). f6 impute edilmez; hesaplanamıyorsa RET. | getiri, P(kapanış > arz) | 99 | 2026-08-19 | `9d6df5ece715` | `4163f65a2ba6` | 2 |
| `pb_v0` | Talep toplama öncesi model (SPEC_PB_V0): ufuk başına Ridge (getiri) ve L2-lojistik (P(kapanış > arz)), SPK onaylı planlanan yapıdan pb1–pb3, V1.6 ızgarası; bilgi kesimi ilk talep toplama günü B(k). | getiri, P(kapanış > arz) | 99 | 2026-08-19 | `97c3b287f90a` | `4eb55d4e6ce8` | 2 |
| `ceiling_hazard_v0` | Tavan serisi, ayrık zamanlı hazard (SPEC_CEILING_V0): 3 gün-grubu sabiti + f1 (ln arz büyüklüğü), f2 (halka açıklık), f3 (talep katı) katsayıları, L2 (λ iç arz-bırak CV ile). Çıktı S_k = P(seri ≥ k), k = 1..10. | tavan serisi S_k = P(L ≥ k), P(Dk tavan kapanışı) | 97 | 2026-08-19 | `caa4dc867a9f` | `18949ac747fd` | 2 |
| `ceiling_hazard_v0@INF` | ceiling_hazard_v0 ızgarasının uç noktası (λ = INF) kural olarak: yalnız 3 gün-grubu sabiti, özellik yok (SPEC_CEILING_V0 §10-4). Eğitim kümesi ve kesim modelinkiyle aynı. | tavan serisi S_k = P(L ≥ k), P(Dk tavan kapanışı) | 97 | 2026-08-19 | `c5ac8085fd76` | `db7a951f2578` | 2 |
| `pb_ceiling_v0` | Talep toplama öncesi tavan serisi (SPEC_PB_V0 §9): SPEC_CEILING_V0 hazard modeli, özellikler pb1, pb2 (2 katsayı + 3 gün sabiti), 99 arz, bilgi kesimi ilk talep toplama günü B(k). | tavan serisi S_k = P(L ≥ k), P(Dk tavan kapanışı) | 99 | 2026-08-19 | `7fb7a41e48ea` | `8acfd7079be6` | 2 |
| `pb_ceiling_v0@INF` | pb_ceiling_v0 ızgarasının uç noktası (λ = INF) kural olarak: yalnız 3 gün-grubu sabiti, özellik yok (SPEC_PB_V0 §9). Eğitim kümesi ve kesim modelinkiyle aynı. | tavan serisi S_k = P(L ≥ k), P(Dk tavan kapanışı) | 99 | 2026-08-19 | `6a5be1b952f5` | `b1a213bb68e2` | 2 |
| `base_km_expanding` | Tavan serisi Kaplan–Meier (SPEC_CEILING_V0 §10-1): S_k = Π_{d≤k}(1 − olay_d/risk_d), eğitimdeki tüm arzların kişi-dönem satırlarından; risk_d = 0 ise önceki günün hazard'ı. | tavan serisi S_k = P(L ≥ k), P(Dk tavan kapanışı) | 99 | 2026-08-19 | `8120c274de6f` | `ac6b402914cc` | 4 |
| `base_km_last10` | Tavan serisi son-10 Kaplan–Meier (SPEC_CEILING_V0 §10-2): her d için yalnız (j, d) satırı eğitimde bulunan son 10 arz (first_trading_date, ticker sırasıyla). | tavan serisi S_k = P(L ≥ k), P(Dk tavan kapanışı) | 99 | 2026-08-19 | `4bd27e6a5484` | `b457c4cfc188` | 4 |
| `ceiling_path_v0` | Tavan yolu (SPEC_CEILING_PATH_V0): dondurulmuş ceiling_hazard_v0'ın S_k'sı + deterministik limit yolu C_h + kırılma sonrası ampirik hücreler; R_h dağılımının medyanı, p_up ve kuantilleri, h = 1..10. Yeni serbest parametre 0. | getiri, P(kapanış > arz) | 99 | 2026-08-19 | `3e97e8788266` | `104f49c4c951` | 2 |
| `ceiling_path_v0@INF` | Tavan yolu sıfır modeli (MECHANICS_BASE; SPEC_CEILING_PATH_V0): ceiling_hazard_v0@INF'in yalnız gün-grubu sabitleri + aynı limit yolu ve hücreler; özellik yok. | getiri, P(kapanış > arz) | 99 | 2026-08-19 | `5e3692a82e25` | `9cc7f016db4b` | 2 |
| `pb_ceiling_path_v0` | Talep toplama öncesi tavan yolu (SPEC_CEILING_PATH_V0): dondurulmuş pb_ceiling_v0'ın S_k'sı + aynı limit yolu ve hücreler; backtest kesimi ilk talep toplama günü B(k); f3 istemez. | getiri, P(kapanış > arz) | 99 | 2026-08-19 | `3d1e2f41f5d0` | `b3f723fba37a` | 2 |
| `ceiling_hazard_v1_clip` | Tavan serisi v1 (a) kırpma (SPEC_HAZARD_V1): ceiling_hazard_v0 aynen, ama f1 (ham TL), f2, f3 üçü de eğitim Type-7 [p05, p95]'ine kırpılır; H99'un f3'lü 97 arzı; 3 gün sabiti + 3 katsayı. | tavan serisi S_k = P(L ≥ k), P(Dk tavan kapanışı) | 97 | 2026-08-19 | `f3a147535242` | `6103d3c9189c` | 2 |
| `ceiling_hazard_v1_real` | Tavan serisi v1 (b) reel büyüklük (SPEC_HAZARD_V1): f1 yerine f1r = ln(büyüklük / (TÜFE_{T−2} / 100)) (TÜİK TÜFE 2025=100); f1r, f2, f3 eğitim [p05, p95]'ine kırpılır; H99'un f3'lü 97 arzı; 3 gün sabiti + 3 katsayı. | tavan serisi S_k = P(L ≥ k), P(Dk tavan kapanışı) | 97 | 2026-08-19 | `d81dad3d60c1` | `fea051b61752` | 2 |
| `ceiling_hazard_v1_pooled` | Tavan serisi v1 (c) havuz (SPEC_HAZARD_V1): f1r, f2, f3 (kırpmalı) + cezasız rejim terimi r = 1[tahsis rejimi ≠ EQUAL_DIST_20230330]; eğitim H99 + eski kohortun açık kümesi (165 arz, training_table_v2); canlıda r = 0. | tavan serisi S_k = P(L ≥ k), P(Dk tavan kapanışı) | 165 | 2026-08-19 | `e03e71e0bb6e` | `2a088b0d86d7` | 2 |
| `ceiling_hazard_v1_pooled@INF` | ceiling_hazard_v1_pooled ızgarasının uç noktası (λ = INF) kural olarak: 3 gün-grubu sabiti + rejim sabiti δ, özellik yok (SPEC_HAZARD_V1 §2); (γ, δ) Newton. Eğitim kümesi ve kesim modelinkiyle aynı. | tavan serisi S_k = P(L ≥ k), P(Dk tavan kapanışı) | 165 | 2026-08-19 | `7d7c9d1ee5a6` | `f53ad4cf1ba9` | 2 |
| `fall_d10_v0_h99` | Düşen arz v0 (SPEC_C_V0): D10 ve D5'te P(kapanış > arz) için L2-lojistik (V1.6 C ızgarası, iç LOOCV Brier); özellikler f1r (TÜFE ile reel büyüklük), ln f3 (talep katı), ek satış bayrağı; H99'un f3 ve ek satış alanı dolu 94 arzı. Düşme olasılığı = 1 − p_up. | P(kapanış > arz) | 94 | 2026-08-19 | `b15eaa8cb1f7` | `e21c0a32bb98` | 1 |
| `fall_d10_v0_pooled` | Düşen arz v0 (SPEC_C_V0): h99 ile aynı özellikler ve model (f1r, ln f3, ek satış bayrağı; L2-lojistik, V1.6 C ızgarası); eğitim H99 + eski kohortun açık kümesi (161 arz, training_table_v2); rejim terimi yok. | P(kapanış > arz) | 161 | 2026-08-19 | `d2c5d5499611` | `1054f2c22147` | 1 |
| `fall_d10_v0_addsale` | Düşen arz v0 (SPEC_C_V0): yalnız ek satış bayrağı (1[additional_sale_shares > 0]) ile L2-lojistik (V1.6 C ızgarası); eğitim H99 + açık küme, ek satış alanı dolu 165 arz; f3 istemez. | P(kapanış > arz) | 165 | 2026-08-19 | `b95fc3ecee26` | `b0b04566f987` | 1 |
| `fall_d10_v0_pooled@ZERO` | fall_d10_v0_pooled ızgarasının uç noktası (C = ZERO) kural olarak: ufuk başına sabit p_up = eğitim oranı (kapalı biçim), özellik yok (SPEC_C_V0 §2). Eğitim kümesi, plan ve f3 filtre dışlaması modelinkiyle aynı. | P(kapanış > arz) | 161 | 2026-08-19 | `7c23b9236c0a` | `0c96245fb80f` | 1 |

"Günlükteki koşu sayısı": `experiments/log.jsonl`'daki backtest satırı sayısı, modelin koşulduğu bütün planlar dahil (bu belge üretildiği anda; plan başına sayılar Faz 1B bölümünün sonunda). Aynı veride bakılan her koşu sayılır (CLAUDE.md kural 4).

### v1_5_h99 ayrıntısı

- Girdiler f1–f5 (`borsai/features.py`): f1: arz büyüklüğü TL: kaynakta bildirilen ipo_size_tl, yoksa ipo_price_tl × shares_offered; ön işlemede doğal log; f2: shares_offered / post_ipo_share_capital × 100; 10 ondalık ROUND_HALF_UP; f3: total_demand_multiple (toplam talep katı); eksik ≠ 0; ön işlemede fold içi p05/p95 winsor; f4: capital_increase_shares / shares_offered × 100; 10 ondalık ROUND_HALF_UP; f5: 1 yalnız f3 eksikse, değilse 0.
- Ön işleme (`borsai/preprocess.py`, legacy V1.3): f3 fold içi p05/p95 winsor ve medyanla doldurma, f1 log, z-skor (ddof = 0). Dondurulmuş parametreler: f3 p05 = 1.14870997716, p95 = 8.332; f3 filtre modu `NOT_SPECIFIED` (eşitlik yok).
- Ridge (getiri) α ızgarası {0.1, 1, 10, 100}; L2-lojistik C ızgarası {0.01, 0.1, 1, 10}; iç LOOCV ile seçim (MAE / ham Brier).

| Ufuk | α (Ridge) | C (Logit) | Logit sınıfları (0 / 1) |
|---|---|---|---|
| D1 | 100 | 0.1 | 10 / 89 |
| D3 | 10 | 1 | 19 / 80 |
| D5 | 10 | 1 | 22 / 77 |
| D10 | 0.1 | 1 | 29 / 70 |

D1'de α = 100 ızgaranın üst ucu, D10'da α = 0.1 alt ucu (AUDIT §1.2-e). V1.5 referans olarak aynen korunur; ızgarası genişletilmiş bir sürüm ayrı model_id olur.

Tahmin kuralları (`borsai/predict.py`): f3 boşsa **RET** (f5 katsayısı yalnız ALBTN ve ENDAE'den öğrenildi, AUDIT §1.2-d); f1–f4 eğitim aralığı dışındaysa uyarı; f4 = 0 kabul + "eğitimde örneği yok" uyarısı; getiri fiziksel sınıra [0.9^h − 1, 1.1^h − 1] kırpılır ve işaretlenir.

## Backtest yöntemi

- H99 walk-forward, legacy benchmark'la aynı fold planı: eğitim satırı ancak hedef seansı test arzının ilk işlem gününden kesin önceyse girer; eğitim n'i < 10 olan fold skorlanmaz. Skorlanabilir fold: D1 89, D3 88, D5 87, D10 87 (toplam 351).
- Her fold'da model yalnız o fold'un eğitim satırlarıyla yeniden fit edilir; basit kurallar aynı fold'larda aynı eğitim hedeflerinden hesaplanır.
- Getiri: MAE (R_h uzayı). Olasılık: Brier; olasılık yalnız skorlamada [0.01, 0.99]'a kırpılır. Tahmin ham (kırpılmamış) haliyle skorlanır.
- **Eşleşik fark** = V1.5 − kural, aynı fold'larda; negatif = V1.5 daha iyi. Getiri karşılaştırması V1.5 Ridge'in fit edildiği fold'larda (351/351), olasılık karşılaştırması V1.5 Logit'in fit edildiği fold'larda (D1 80, D3 80, D5 81, D10 81; tek sınıflı eğitim fold'larında Logit fit edilmez).
- **%95 aralık:** ilk işlem ayına göre blok bootstrap (AUDIT §1.2-c yöntemi): aylar iadeli çekilir, çekilen ayların bütün farkları birleştirilip ortalaması alınır; 4000 tekrar; her karşılaştırma `random.Random(20260921)` ile ayrı başlar. Aralık, sıralı dağılımın 100. ve 3899. elemanıdır. Yöntem AUDIT'in tablosunu 12/12 hücrede aynen üretir (`tests/test_metrics.py`). Bu test ön kayıtlı değildir; AUDIT sonuçları gördükten sonra seçmiştir.
- **"Geçiyor" yalnız aralık 0'ı dışlıyorsa** denir. Aralık 0'ı içeriyorsa "ayırt edilemiyor".

## Eşleşik farklar: V1.5 − basit kural

### Getiri, MAE

| Ufuk | Kural | n (ay) | V1.5 | Kural | Fark | %95 aralık | V1.5 iyi / kural iyi / eşit | Hüküm |
|---|---|---|---|---|---|---|---|---|
| D1 | `base_always_ceiling` | 89 (24) | 0.0297 | 0.0251 | +0.0046 | [+0.0015, +0.0080] | 24 / 65 / 0 | **kural daha iyi** (aralık 0'ın üstünde) |
| D1 | `base_train_median` | 89 (24) | 0.0297 | 0.0251 | +0.0046 | [+0.0015, +0.0079] | 24 / 65 / 0 | **kural daha iyi** (aralık 0'ın üstünde) |
| D1 | `base_train_mean` | 89 (24) | 0.0297 | 0.0332 | -0.0035 | [-0.0060, -0.0011] | 52 / 37 / 0 | **V1.5 geçiyor** (aralık 0'ın altında) |
| D1 | `base_zero` | 89 (24) | 0.0297 | 0.0885 | -0.0588 | [-0.0765, -0.0426] | 73 / 16 / 0 | **V1.5 geçiyor** (aralık 0'ın altında) |
| D3 | `base_always_ceiling` | 88 (24) | 0.1201 | 0.1363 | -0.0163 | [-0.0531, +0.0185] | 37 / 51 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | `base_train_median` | 88 (24) | 0.1201 | 0.1357 | -0.0157 | [-0.0524, +0.0190] | 32 / 56 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | `base_train_mean` | 88 (24) | 0.1201 | 0.1555 | -0.0354 | [-0.0518, -0.0191] | 61 / 27 / 0 | **V1.5 geçiyor** (aralık 0'ın altında) |
| D3 | `base_zero` | 88 (24) | 0.1201 | 0.2385 | -0.1184 | [-0.1739, -0.0691] | 63 / 25 / 0 | **V1.5 geçiyor** (aralık 0'ın altında) |
| D5 | `base_always_ceiling` | 87 (23) | 0.2220 | 0.3332 | -0.1112 | [-0.1908, -0.0278] | 52 / 35 / 0 | **V1.5 geçiyor** (aralık 0'ın altında) |
| D5 | `base_train_median` | 87 (23) | 0.2220 | 0.3059 | -0.0839 | [-0.1343, -0.0321] | 58 / 29 / 0 | **V1.5 geçiyor** (aralık 0'ın altında) |
| D5 | `base_train_mean` | 87 (23) | 0.2220 | 0.2882 | -0.0662 | [-0.0950, -0.0397] | 62 / 25 / 0 | **V1.5 geçiyor** (aralık 0'ın altında) |
| D5 | `base_zero` | 87 (23) | 0.2220 | 0.3440 | -0.1220 | [-0.2136, -0.0421] | 53 / 34 / 0 | **V1.5 geçiyor** (aralık 0'ın altında) |
| D10 | `base_always_ceiling` | 87 (23) | 0.4477 | 1.1954 | -0.7477 | [-0.9355, -0.5384] | 72 / 15 / 0 | **V1.5 geçiyor** (aralık 0'ın altında) |
| D10 | `base_train_median` | 87 (23) | 0.4477 | 0.5640 | -0.1163 | [-0.1996, -0.0208] | 58 / 29 / 0 | **V1.5 geçiyor** (aralık 0'ın altında) |
| D10 | `base_train_mean` | 87 (23) | 0.4477 | 0.6011 | -0.1534 | [-0.2364, -0.0610] | 60 / 27 / 0 | **V1.5 geçiyor** (aralık 0'ın altında) |
| D10 | `base_zero` | 87 (23) | 0.4477 | 0.4976 | -0.0498 | [-0.2283, +0.1514] | 43 / 44 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |

### P(kapanış > arz), Brier

| Ufuk | Kural | n (ay) | V1.5 | Kural | Fark | %95 aralık | V1.5 iyi / kural iyi / eşit | Hüküm |
|---|---|---|---|---|---|---|---|---|
| D1 | `base_always_ceiling` | 80 (22) | 0.0943 | 0.1103 | -0.0160 | [-0.0461, +0.0105] | 8 / 71 / 1 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | `base_rate` | 80 (22) | 0.0943 | 0.1022 | -0.0078 | [-0.0286, +0.0115] | 41 / 39 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | `base_last10_rate` | 80 (22) | 0.0943 | 0.1065 | -0.0122 | [-0.0270, +0.0024] | 41 / 39 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | `base_always_ceiling` | 80 (23) | 0.1488 | 0.2206 | -0.0718 | [-0.1438, -0.0079] | 18 / 55 / 7 | **V1.5 geçiyor** (aralık 0'ın altında) |
| D3 | `base_rate` | 80 (23) | 0.1488 | 0.1847 | -0.0359 | [-0.0817, +0.0104] | 49 / 31 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | `base_last10_rate` | 80 (23) | 0.1488 | 0.1848 | -0.0360 | [-0.0817, +0.0124] | 49 / 26 / 5 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | `base_always_ceiling` | 81 (23) | 0.1614 | 0.2421 | -0.0806 | [-0.1573, -0.0085] | 20 / 56 / 5 | **V1.5 geçiyor** (aralık 0'ın altında) |
| D5 | `base_rate` | 81 (23) | 0.1614 | 0.1958 | -0.0343 | [-0.0773, +0.0106] | 52 / 29 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | `base_last10_rate` | 81 (23) | 0.1614 | 0.2014 | -0.0399 | [-0.0847, +0.0074] | 48 / 28 / 5 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | `base_always_ceiling` | 81 (23) | 0.1883 | 0.3026 | -0.1142 | [-0.1993, -0.0300] | 25 / 56 / 0 | **V1.5 geçiyor** (aralık 0'ın altında) |
| D10 | `base_rate` | 81 (23) | 0.1883 | 0.2274 | -0.0391 | [-0.0756, +0.0023] | 52 / 29 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | `base_last10_rate` | 81 (23) | 0.1883 | 0.2791 | -0.0908 | [-0.1527, -0.0287] | 46 / 35 / 0 | **V1.5 geçiyor** (aralık 0'ın altında) |

## Faz 1A modellerinin kendi skorlanabilir kümesindeki metrikler

Karşılaştırma için değil, bağlam için. Kurallar tüm skorlanabilir fold'larda, V1.5 yalnız fit edildiği fold'larda skorlanır; bu yüzden olasılık satırlarının n'i farklıdır. Karşılaştırma yukarıdaki eşleşik tablolardadır.

| Model | Ufuk | Getiri n | MAE | Medyan AE | RMSE | Olasılık n | Brier | İsabet | Log kaybı |
|---|---|---|---|---|---|---|---|---|---|
| `v1_5_h99` | D1 | 89 | 0.0297 | 0.0132 | 0.0520 | 80 | 0.0943 | 0.8875 | 0.3557 |
| `v1_5_h99` | D3 | 88 | 0.1201 | 0.0733 | 0.1635 | 80 | 0.1488 | 0.8000 | 0.4586 |
| `v1_5_h99` | D5 | 87 | 0.2220 | 0.1921 | 0.2806 | 81 | 0.1614 | 0.8025 | 0.4915 |
| `v1_5_h99` | D10 | 87 | 0.4477 | 0.3680 | 0.5703 | 81 | 0.1883 | 0.7284 | 0.5601 |
| `base_always_ceiling` | D1 | 89 | 0.0251 | 0.0000 | 0.0605 | 89 | 0.1102 | 0.8876 | 0.5264 |
| `base_always_ceiling` | D3 | 88 | 0.1363 | 0.0016 | 0.2313 | 88 | 0.2117 | 0.7841 | 1.0022 |
| `base_always_ceiling` | D5 | 87 | 0.3332 | 0.2938 | 0.4543 | 87 | 0.2479 | 0.7471 | 1.1720 |
| `base_always_ceiling` | D10 | 87 | 1.1954 | 1.4280 | 1.3367 | 87 | 0.3268 | 0.6667 | 1.5418 |
| `base_train_median` | D1 | 89 | 0.0251 | 0.0001 | 0.0605 | — | — | — | — |
| `base_train_median` | D3 | 88 | 0.1357 | 0.0009 | 0.2307 | — | — | — | — |
| `base_train_median` | D5 | 87 | 0.3059 | 0.2906 | 0.3924 | — | — | — | — |
| `base_train_median` | D10 | 87 | 0.5640 | 0.4773 | 0.6895 | — | — | — | — |
| `base_train_mean` | D1 | 89 | 0.0332 | 0.0185 | 0.0563 | — | — | — | — |
| `base_train_mean` | D3 | 88 | 0.1555 | 0.1133 | 0.1956 | — | — | — | — |
| `base_train_mean` | D5 | 87 | 0.2882 | 0.2782 | 0.3341 | — | — | — | — |
| `base_train_mean` | D10 | 87 | 0.6011 | 0.5478 | 0.6725 | — | — | — | — |
| `base_zero` | D1 | 89 | 0.0885 | 0.1000 | 0.0930 | — | — | — | — |
| `base_zero` | D3 | 88 | 0.2385 | 0.3294 | 0.2698 | — | — | — | — |
| `base_zero` | D5 | 87 | 0.3440 | 0.3167 | 0.4150 | — | — | — | — |
| `base_zero` | D10 | 87 | 0.4976 | 0.2471 | 0.7186 | — | — | — | — |
| `base_rate` | D1 | — | — | — | — | 89 | 0.1028 | 0.8876 | 0.3860 |
| `base_rate` | D3 | — | — | — | — | 88 | 0.1793 | 0.7841 | 0.5798 |
| `base_rate` | D5 | — | — | — | — | 87 | 0.2048 | 0.7471 | 0.6621 |
| `base_rate` | D10 | — | — | — | — | 87 | 0.2568 | 0.6667 | 0.8273 |
| `base_last10_rate` | D1 | — | — | — | — | 89 | 0.1068 | 0.8876 | 0.4244 |
| `base_last10_rate` | D3 | — | — | — | — | 88 | 0.1791 | 0.7841 | 0.5876 |
| `base_last10_rate` | D5 | — | — | — | — | 87 | 0.2100 | 0.7586 | 0.7136 |
| `base_last10_rate` | D10 | — | — | — | — | 87 | 0.3050 | 0.4943 | 1.0014 |

İsabet tek başına okunmaz: D1'de "her zaman yukarı" (ALWAYS_CEILING'in yönü) de 79/89 isabet eder.

## Port kabulü (Windows referansına karşı)

Legacy H99 benchmark'ı Windows'ta (Python 3.12.13) üretildi. Bu makinedeki port (fold düzeyi, `tests/test_acceptance_backtest.py`):

- Fold kurulumu: training_tickers_sha256 351/351 eşit.
- Seçilen α 351/351, seçilen C 350/351 eşit.
- Ridge: 220 fold'da son basamaklarda fark, maks |Δ| = 2.72e-15 (D5|ALBTN); tolerans 1e-12.
- Logit p: 57 fold'da fark, maks |Δ| = 3.06e-09 (D5|ORZAX); tolerans 1e-7.
- Adıyla beklenen tek sapma: D3|BETAE: MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE (Windows FIT_OK). Bu makinede iç LOOCV'de lbfgs yakınsamıyor; legacy kod da burada aynı sonucu veriyor (AUDIT §1.2-b). D3 Logit n'i 81 → 80.
- Aynı makinede port ile legacy kod (legacy/ import edilerek) geliştirme sırasında 351/351 fold'da bit düzeyinde aynı çıktı; test paketi uç durumları kapsayan 12 fold'u ve ön işlemeyi her koşuda yeniden karşılaştırır (`tests/test_port_vs_legacy.py`). Bu makinedeki ledger'lar bundan sonraki regresyonun altın referansıdır (bayt eşitliği).

## Notlar

- V1.5 Ridge backtest tahminlerinin 19/351'i fiziksel sınır [0.9^h − 1, 1.1^h − 1] dışında; backtest bunları kırpmadan skorlar (legacy ile aynı). `predict` çıktıyı kırpar ve işaretler.
- Backtest'te test arzı f3'süz olan 8 fold var (ALBTN ve ENDAE, her ufukta); V1.5 bunları f3 medyanı ve f5 = 1 ile tahmin etti ve skorlandı. `predict` aynı girdiyi reddeder.
- Olasılık karşılaştırmasında `base_always_ceiling`'in p_up'ı 1'dir; H99'da her eğitim fold'unda çoğunluk sınıfı 1 olduğundan legacy V1_BASE_MAJORITY ile aynı kuraldır.
- Gerçekleşen R_D1 fiyat adımı yüzünden 0.1'i çok az aşabilir (LILAK, BORLS; `docs/DATA.md`).
- Altın ledger sha256'ları: `base_always_ceiling_fold_ledger.csv` `2933c656feba`, `base_last10_rate_fold_ledger.csv` `1459e9ebd65f`, `base_rate_fold_ledger.csv` `898d2d849cc2`, `base_train_mean_fold_ledger.csv` `bbe8e29c998e`, `base_train_median_fold_ledger.csv` `abb8669fa5ac`, `base_zero_fold_ledger.csv` `4b0bd28cd6ea`, `v1_5_h99_fold_ledger.csv` `5c56da37bf7c`.

## Faz 1B: yeni modeller (Fable şartnameleri, docs/specs/)

**Terazi:** aşağıdaki her sayı **backtest**tir (retrospektif walk-forward, H99). Şartnamelerin hepsi bu sonuçların **tasarıma maruz** olduğunu yazar (özellik, gün grubu ve ızgaralar H99 görülerek seçildi; market20 ayrıca eski repoda görülmüştü); kanıt değeri düşüktür. Asıl ölçüm prospektiftir ve henüz yoktur (n = 0). "Geçiyor" yalnız aralık 0'ı dışlıyorsa yazılır.

Yöntem: eşleşik fark = model − karşılaştırılan, ikisinin de skorlandığı ortak fold'larda; %95 aralık yukarıdaki blok bootstrap (ilk işlem ayı blokları, 4000 tekrar, `random.Random(20260921)`). Getiri MAE; P(kapanış > arz) Brier (Faz 1A tablolarıyla aynı [0.01, 0.99] skorlama kırpması); tavan çıktıları RPS ve Brier (kırpmasız).

| Plan | Bilgi kesimi | Kural | Kullanan |
|---|---|---|---|
| `H99_WALK_FORWARD_STRICT_PRIOR_DATE_MIN_TRAIN_10` | T (ilk işlem günü) | hedef seansı < T; n ≥ 10 | V1.5, `v1_6_h99`, `v1_5_market20_v0`, Faz 1A kuralları |
| `H99_PB_WALK_FORWARD_BOOKBUILD_CUTOFF_MIN_TRAIN_10` | B (ilk talep toplama günü) | hedef seansı < B; n ≥ 10 | `pb_v0` ve 6 kural |
| `H99_CEILING_PP_WALK_FORWARD_T_CUTOFF_F3_PRESENT_MIN10IPO_5EV_5SV` | T | kişi-dönem satırı seansı < T; f3 dolu arzlar; ≥ 10 arz, ≥ 5 olay, ≥ 5 sağ kalım | `ceiling_hazard_v0`, @INF, KM kuralları, her zaman tavan |
| `H99_PB_CEILING_PP_WALK_FORWARD_B_CUTOFF_MIN10IPO_5EV_5SV` | B | aynı, 99 arz | `pb_ceiling_v0`, @INF, KM kuralları, her zaman tavan |

Beklenti tablolarındaki niteleyicilerin sayısal karşılığı (rapor kodunda sabit, sonuçlardan önce yazıldı):

- "çoğu / çoğunlukla / seçilir" = ilgili fold'ların > %50'si; "sık" = ≥ %25'i.
- "erken fold" = kronolojik ilk 20 skorlanabilir fold.
- Getiri MAE farkında "≈ 0" = |fark| < 0.002; "küçük değişim" = |fark| < 0.01.
- Brier/RPS farkında "≈ 0" = |fark| < 0.002; "hafif kötü" = 0 < fark < 0.01; "küçük kazanç" = −0.01 < fark ≤ +0.002.
- "~0.10" = |değer − 0.10| ≤ 0.005.
- "ayırt edilemez / aralık 0'ı içerir" = blok bootstrap %95 aralığı 0'ı içeriyor. "daha kötü ya da eşit" = aralık tamamen 0'ın altında değil (model anlamlı biçimde daha iyi değil).
- "en iyi KM kuralı" = `base_km_expanding` ve `base_km_last10`'dan eşleşik kümede ortalama RPS'i küçük olan.
- Çok parçalı beklentide her parça ayrı değerlendirilir; hepsi tutarsa "tuttu", hiçbiri tutmazsa "tutmadı", aksi halde "kısmen" ve tutmayan parça adıyla yazılır.

### `v1_6_h99` (SPEC_V1_6)

Plan: PLAN_V15 (351 fold, V1.5 ile aynı `training_tickers_sha256`). Izgara α ∈ {0.001 … 10000, INF}, C ∈ {ZERO, 0.0001 … 100}; aday başına yakınsamama.

Eşleşik fark: `v1_6_h99` − `v1_5_h99` (ikisinin de FIT_OK olduğu fold'lar):

| Ufuk | Çıktı | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| D1 | MAE | 89 (24) | 0.0297 | 0.0297 | -0.0000 | [-0.0002, +0.0001] | 6 / 7 / 76 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | Brier | 80 (22) | 0.0944 | 0.0943 | +0.0000 | [-0.0001, +0.0003] | 3 / 2 / 75 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | MAE | 88 (24) | 0.1201 | 0.1201 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 88 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | Brier | 80 (23) | 0.1488 | 0.1488 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 80 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | MAE | 87 (23) | 0.2222 | 0.2220 | +0.0001 | [+0.0000, +0.0005] | 4 / 4 / 79 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | Brier | 81 (23) | 0.1614 | 0.1614 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 81 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | MAE | 87 (23) | 0.4485 | 0.4477 | +0.0008 | [-0.0003, +0.0028] | 28 / 31 / 28 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | Brier | 81 (23) | 0.1883 | 0.1883 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 81 | ayırt edilemiyor (aralık 0'ı içeriyor) |

Getiri, MAE: model − basit kural

| Ufuk | Kural | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| D1 | `base_always_ceiling` | 89 (24) | 0.0297 | 0.0251 | +0.0046 | [+0.0015, +0.0078] | 24 / 65 / 0 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D1 | `base_train_median` | 89 (24) | 0.0297 | 0.0251 | +0.0046 | [+0.0015, +0.0078] | 24 / 65 / 0 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D1 | `base_train_mean` | 89 (24) | 0.0297 | 0.0332 | -0.0035 | [-0.0060, -0.0012] | 51 / 34 / 4 | **model geçiyor** (aralık 0'ın altında) |
| D1 | `base_zero` | 89 (24) | 0.0297 | 0.0885 | -0.0588 | [-0.0766, -0.0424] | 73 / 16 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | `base_always_ceiling` | 88 (24) | 0.1201 | 0.1363 | -0.0163 | [-0.0531, +0.0185] | 37 / 51 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | `base_train_median` | 88 (24) | 0.1201 | 0.1357 | -0.0157 | [-0.0524, +0.0190] | 32 / 56 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | `base_train_mean` | 88 (24) | 0.1201 | 0.1555 | -0.0354 | [-0.0518, -0.0191] | 61 / 27 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | `base_zero` | 88 (24) | 0.1201 | 0.2385 | -0.1184 | [-0.1739, -0.0691] | 63 / 25 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | `base_always_ceiling` | 87 (23) | 0.2222 | 0.3332 | -0.1110 | [-0.1907, -0.0277] | 52 / 35 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | `base_train_median` | 87 (23) | 0.2222 | 0.3059 | -0.0837 | [-0.1341, -0.0319] | 58 / 29 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | `base_train_mean` | 87 (23) | 0.2222 | 0.2882 | -0.0660 | [-0.0949, -0.0395] | 60 / 24 / 3 | **model geçiyor** (aralık 0'ın altında) |
| D5 | `base_zero` | 87 (23) | 0.2222 | 0.3440 | -0.1219 | [-0.2136, -0.0416] | 53 / 34 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | `base_always_ceiling` | 87 (23) | 0.4485 | 1.1954 | -0.7469 | [-0.9351, -0.5379] | 72 / 15 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | `base_train_median` | 87 (23) | 0.4485 | 0.5640 | -0.1155 | [-0.1990, -0.0198] | 57 / 30 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | `base_train_mean` | 87 (23) | 0.4485 | 0.6011 | -0.1526 | [-0.2362, -0.0592] | 59 / 27 / 1 | **model geçiyor** (aralık 0'ın altında) |
| D10 | `base_zero` | 87 (23) | 0.4485 | 0.4976 | -0.0490 | [-0.2284, +0.1539] | 43 / 44 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |

P(kapanış > arz), Brier (skorlamada [0.01, 0.99] kırpması): model − basit kural

| Ufuk | Kural | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| D1 | `base_always_ceiling` | 80 (22) | 0.0944 | 0.1103 | -0.0160 | [-0.0462, +0.0106] | 8 / 71 / 1 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | `base_rate` | 80 (22) | 0.0944 | 0.1022 | -0.0078 | [-0.0287, +0.0116] | 40 / 38 / 2 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | `base_last10_rate` | 80 (22) | 0.0944 | 0.1065 | -0.0122 | [-0.0270, +0.0025] | 41 / 39 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | `base_always_ceiling` | 81 (23) | 0.1469 | 0.2179 | -0.0709 | [-0.1405, -0.0079] | 18 / 55 / 8 | **model geçiyor** (aralık 0'ın altında) |
| D3 | `base_rate` | 81 (23) | 0.1469 | 0.1827 | -0.0357 | [-0.0802, +0.0104] | 50 / 31 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | `base_last10_rate` | 81 (23) | 0.1469 | 0.1825 | -0.0355 | [-0.0798, +0.0124] | 49 / 26 / 6 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | `base_always_ceiling` | 81 (23) | 0.1614 | 0.2421 | -0.0806 | [-0.1573, -0.0085] | 20 / 56 / 5 | **model geçiyor** (aralık 0'ın altında) |
| D5 | `base_rate` | 81 (23) | 0.1614 | 0.1958 | -0.0343 | [-0.0773, +0.0106] | 52 / 29 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | `base_last10_rate` | 81 (23) | 0.1614 | 0.2014 | -0.0399 | [-0.0847, +0.0074] | 48 / 28 / 5 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | `base_always_ceiling` | 81 (23) | 0.1883 | 0.3026 | -0.1142 | [-0.1993, -0.0300] | 25 / 56 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | `base_rate` | 81 (23) | 0.1883 | 0.2274 | -0.0391 | [-0.0756, +0.0023] | 52 / 29 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | `base_last10_rate` | 81 (23) | 0.1883 | 0.2791 | -0.0908 | [-0.1527, -0.0287] | 46 / 35 / 0 | **model geçiyor** (aralık 0'ın altında) |

Fit edilemeyen fold'lar — bu model: D1 logit MODEL_NOT_FIT_SINGLE_CLASS: 9; D3 logit MODEL_NOT_FIT_SINGLE_CLASS: 7; D5 logit MODEL_NOT_FIT_SINGLE_CLASS: 6; D10 logit MODEL_NOT_FIT_SINGLE_CLASS: 6. `v1_5_h99`: D1 logit MODEL_NOT_FIT_SINGLE_CLASS: 9; D3 logit MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE: 1; D3 logit MODEL_NOT_FIT_SINGLE_CLASS: 7; D5 logit MODEL_NOT_FIT_SINGLE_CLASS: 6; D10 logit MODEL_NOT_FIT_SINGLE_CLASS: 6.

Ridge α seçim dağılımı (fold sayısı; yalnız FIT_OK fold'lar). Kenar = sonlu uç değer(ler): 0.001, 10000.0.

| Ufuk | 0.001 | 0.01 | 0.1 | 1.0 | 10.0 | 100.0 | 1000.0 | 10000.0 | INF | n | en sık sonlu uç değerin payı |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 | 1 | 1 | 2 | 1 | 0 | 73 | 7 | 0 | 4 | 89 | %1 |
| D3 | 0 | 0 | 0 | 0 | 70 | 18 | 0 | 0 | 0 | 88 | %0 |
| D5 | 5 | 0 | 0 | 39 | 34 | 6 | 0 | 0 | 3 | 87 | %6 |
| D10 | 57 | 1 | 1 | 21 | 6 | 0 | 0 | 0 | 1 | 87 | %66 |

Logit C seçim dağılımı (fold sayısı; yalnız FIT_OK fold'lar). Kenar = sonlu uç değer(ler): 0.0001, 100.0.

| Ufuk | ZERO | 0.0001 | 0.001 | 0.01 | 0.1 | 1.0 | 10.0 | 100.0 | n | en sık sonlu uç değerin payı |
|---|---|---|---|---|---|---|---|---|---|---|
| D1 | 2 | 0 | 2 | 33 | 35 | 6 | 0 | 2 | 80 | %2 |
| D3 | 0 | 0 | 0 | 1 | 14 | 61 | 5 | 0 | 81 | %0 |
| D5 | 0 | 0 | 0 | 1 | 28 | 52 | 0 | 0 | 81 | %0 |
| D10 | 0 | 0 | 0 | 8 | 39 | 34 | 0 | 0 | 81 | %0 |

Aday başına yakınsamama: 2 (fold, C) adayı `CANDIDATE_NOT_CONVERGED`; nihai fit'te sıradaki adaya geçilen fold: 0. D3|BETAE: Logit FIT_OK, C = 1.0. D3 Logit FIT_OK n = 81.

Nihai fit (99 arz): D1 α = 100.0, C = 0.1; D3 α = 10.0, C = 1.0; D5 α = 10.0, C = 1.0; D10 α = 0.001, C = 1.0.

| Kaynak | Şartnamedeki beklenti (aynen) | Gerçekleşen (backtest) | Tuttu mu |
|---|---|---|---|
| SPEC_V1_6.md §8 | **D1 Ridge:** çoğu fold α ∈ {1000, 10000, INF} seçer; MAE 0.0297 ile 0.0332 arasına, yani V1.5'e eşit ya da **daha kötü** tarafa gider; medyana yenilgi sürer. | α ∈ {1000, 10000, INF}: %12 (89 fold); MAE 0.0297; medyana karşı +0.0046 [+0.0015, +0.0078] | kısmen (tutmayan: çoğu fold α ∈ {1000, 10000, INF}) |
| SPEC_V1_6.md §8 | **D3:** değişim ≈ 0 (V1.5 iç noktada: α = 10). | D3 ΔMAE +0.0000 [+0.0000, +0.0000] | tuttu |
| SPEC_V1_6.md §8 | **D5:** küçük değişim. | D5 ΔMAE +0.0001 [+0.0000, +0.0005] | tuttu |
| SPEC_V1_6.md §8 | **D10 Ridge:** α ∈ {0.001, 0.01} sık seçilir; MAE değişimi ±0.01 içinde, yönü belirsiz (aşırı uyum riski). | α ∈ {0.001, 0.01}: %67; D10 ΔMAE +0.0008 [-0.0003, +0.0028] | tuttu |
| SPEC_V1_6.md §8 | **Logit D1:** ZERO/0.0001/0.001 sık; Brier taban oranına yaklaşır (0.0943 → ~0.10). Diğer ufuklarda \|ΔBrier\| < 0.005. | C ∈ {ZERO, 0.0001, 0.001}: %5; D1 Brier 0.0944 (V1.5 0.0943); D3/D5/D10 ΔBrier +0.0000, +0.0000, +0.0000 | kısmen (tutmayan: ZERO/0.0001/0.001 sık; Brier ~0.10) |
| SPEC_V1_6.md §8 | Kenara yapışma: yeni ızgarada hiçbir ufukta tek bir uç değer fold'ların > %50'sinde seçilmemeli — INF/ZERO hariç (onlar "model yok" demektir ve meşru sonuçtur). | en sık sonlu uç değer payı: D1 ridge %1, D1 logit %2, D3 ridge %0, D3 logit %0, D5 ridge %6, D5 logit %0, D10 ridge %66, D10 logit %0 | tutmadı |

Prospektif ölçüt: Birincil: D10 MAE, `v1_5_h99`'a karşı (SPEC_V1_6 §8). Canlı n = 0: hüküm yok (SPEC_SCORING §8).

### `v1_5_market20_v0` (SPEC_MARKET20_V0)

Plan: PLAN_V15 (351 fold, V1.5 ile aynı eğitim kümeleri). f6 = XU100(S0)/XU100(S20) − 1, Takvim B, ref_date = T; 99/99 arzda hesaplandı, hiçbir satır düşmedi.

Eşleşik fark: `v1_5_market20_v0` − `v1_5_h99` (8 hücre):

| Ufuk | Çıktı | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| D1 | MAE | 89 (24) | 0.0296 | 0.0297 | -0.0001 | [-0.0007, +0.0006] | 51 / 38 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | Brier | 78 (22) | 0.0935 | 0.0960 | -0.0026 | [-0.0098, +0.0003] | 41 / 37 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | MAE | 88 (24) | 0.1200 | 0.1201 | -0.0000 | [-0.0025, +0.0019] | 43 / 45 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | Brier | 80 (23) | 0.1498 | 0.1488 | +0.0010 | [-0.0045, +0.0066] | 42 / 31 / 7 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | MAE | 87 (23) | 0.2212 | 0.2220 | -0.0008 | [-0.0178, +0.0137] | 40 / 47 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | Brier | 80 (23) | 0.1635 | 0.1616 | +0.0020 | [-0.0108, +0.0125] | 39 / 41 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | MAE | 87 (23) | 0.4468 | 0.4477 | -0.0009 | [-0.0528, +0.0429] | 46 / 41 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | Brier | 81 (23) | 0.1938 | 0.1883 | +0.0054 | [-0.0030, +0.0162] | 39 / 42 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |

Getiri, MAE: model − basit kural

| Ufuk | Kural | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| D1 | `base_always_ceiling` | 89 (24) | 0.0296 | 0.0251 | +0.0045 | [+0.0015, +0.0077] | 23 / 66 / 0 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D1 | `base_train_median` | 89 (24) | 0.0296 | 0.0251 | +0.0045 | [+0.0015, +0.0077] | 23 / 66 / 0 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D1 | `base_train_mean` | 89 (24) | 0.0296 | 0.0332 | -0.0036 | [-0.0061, -0.0011] | 52 / 37 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D1 | `base_zero` | 89 (24) | 0.0296 | 0.0885 | -0.0589 | [-0.0768, -0.0425] | 73 / 16 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | `base_always_ceiling` | 88 (24) | 0.1200 | 0.1363 | -0.0163 | [-0.0533, +0.0184] | 37 / 51 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | `base_train_median` | 88 (24) | 0.1200 | 0.1357 | -0.0157 | [-0.0525, +0.0190] | 34 / 54 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | `base_train_mean` | 88 (24) | 0.1200 | 0.1555 | -0.0354 | [-0.0520, -0.0197] | 60 / 28 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | `base_zero` | 88 (24) | 0.1200 | 0.2385 | -0.1185 | [-0.1744, -0.0689] | 63 / 25 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | `base_always_ceiling` | 87 (23) | 0.2212 | 0.3332 | -0.1120 | [-0.1854, -0.0344] | 52 / 35 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | `base_train_median` | 87 (23) | 0.2212 | 0.3059 | -0.0847 | [-0.1291, -0.0383] | 58 / 29 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | `base_train_mean` | 87 (23) | 0.2212 | 0.2882 | -0.0670 | [-0.0938, -0.0410] | 63 / 24 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | `base_zero` | 87 (23) | 0.2212 | 0.3440 | -0.1228 | [-0.2219, -0.0375] | 53 / 34 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | `base_always_ceiling` | 87 (23) | 0.4468 | 1.1954 | -0.7486 | [-0.9304, -0.5476] | 73 / 14 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | `base_train_median` | 87 (23) | 0.4468 | 0.5640 | -0.1172 | [-0.2139, -0.0193] | 60 / 27 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | `base_train_mean` | 87 (23) | 0.4468 | 0.6011 | -0.1543 | [-0.2380, -0.0645] | 62 / 25 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | `base_zero` | 87 (23) | 0.4468 | 0.4976 | -0.0508 | [-0.2396, +0.1541] | 39 / 48 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |

P(kapanış > arz), Brier (skorlamada [0.01, 0.99] kırpması): model − basit kural

| Ufuk | Kural | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| D1 | `base_always_ceiling` | 78 (22) | 0.0935 | 0.1132 | -0.0197 | [-0.0484, +0.0035] | 9 / 69 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | `base_rate` | 78 (22) | 0.0935 | 0.1046 | -0.0112 | [-0.0302, +0.0026] | 40 / 38 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | `base_last10_rate` | 78 (22) | 0.0935 | 0.1091 | -0.0157 | [-0.0294, -0.0029] | 42 / 36 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | `base_always_ceiling` | 81 (23) | 0.1479 | 0.2179 | -0.0700 | [-0.1379, -0.0074] | 17 / 52 / 12 | **model geçiyor** (aralık 0'ın altında) |
| D3 | `base_rate` | 81 (23) | 0.1479 | 0.1827 | -0.0348 | [-0.0780, +0.0103] | 56 / 25 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | `base_last10_rate` | 81 (23) | 0.1479 | 0.1825 | -0.0346 | [-0.0766, +0.0125] | 50 / 24 / 7 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | `base_always_ceiling` | 80 (23) | 0.1635 | 0.2329 | -0.0693 | [-0.1291, -0.0150] | 19 / 61 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | `base_rate` | 80 (23) | 0.1635 | 0.1898 | -0.0262 | [-0.0573, +0.0025] | 50 / 30 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | `base_last10_rate` | 80 (23) | 0.1635 | 0.1938 | -0.0302 | [-0.0611, +0.0015] | 47 / 33 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | `base_always_ceiling` | 81 (23) | 0.1938 | 0.3026 | -0.1088 | [-0.1949, -0.0265] | 25 / 56 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | `base_rate` | 81 (23) | 0.1938 | 0.2274 | -0.0337 | [-0.0731, +0.0075] | 54 / 27 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | `base_last10_rate` | 81 (23) | 0.1938 | 0.2791 | -0.0854 | [-0.1499, -0.0227] | 49 / 32 / 0 | **model geçiyor** (aralık 0'ın altında) |

Fit edilemeyen fold'lar — bu model: D1 logit MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE: 2; D1 logit MODEL_NOT_FIT_SINGLE_CLASS: 9; D3 logit MODEL_NOT_FIT_SINGLE_CLASS: 7; D5 logit MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE: 1; D5 logit MODEL_NOT_FIT_SINGLE_CLASS: 6; D10 logit MODEL_NOT_FIT_SINGLE_CLASS: 6. `v1_5_h99`: D1 logit MODEL_NOT_FIT_SINGLE_CLASS: 9; D3 logit MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE: 1; D3 logit MODEL_NOT_FIT_SINGLE_CLASS: 7; D5 logit MODEL_NOT_FIT_SINGLE_CLASS: 6; D10 logit MODEL_NOT_FIT_SINGLE_CLASS: 6.
V1.5 ile aynı yakınsamama politikası (fold düzeyi) geçerlidir; eşleşik Brier karşılaştırması iki modelin de fit edildiği fold'larda yapılır.

Nihai fit (99 arz) f6 katsayıları (z-skor ölçeğinde) ve f1–f5 katsayılarının ortalama mutlak değeri:

| Ufuk | Ridge β_f6 | Ridge: f1–f5 ort. mutlak β | Logit β_f6 | Logit: f1–f5 ort. mutlak β |
|---|---|---|---|---|
| D1 | +0.0033 | 0.0061 | +0.1636 | 0.2721 |
| D3 | +0.0035 | 0.0378 | -0.2559 | 0.9263 |
| D5 | +0.0259 | 0.0649 | +0.0748 | 0.6396 |
| D10 | +0.0630 | 0.1302 | -0.2561 | 0.5714 |

| Kaynak | Şartnamedeki beklenti (aynen) | Gerçekleşen (backtest) | Tuttu mu |
|---|---|---|---|
| SPEC_MARKET20_V0.md §9 | 8 hücrenin hepsinde V1.5'e karşı eşleşik fark aralığı 0'ı içerir; \|ΔMAE\| < 0.002, \|ΔBrier\| < 0.005. | 0'ı içeren aralık: 8/8; ΔMAE D1 -0.0001, D3 -0.0000, D5 -0.0008, D10 -0.0009; ΔBrier D1 -0.0026, D3 +0.0010, D5 +0.0020, D10 +0.0054 | kısmen (tutmayan: \|ΔBrier\| < 0.005) |
| SPEC_MARKET20_V0.md §9 | f6 katsayısının işareti pozitif (yükselen piyasa → daha yüksek getiri), büyüklüğü küçük. | Ridge β_f6 > 0: 4/4; \|β_f6\| < ort. \|β_f1..f5\|: 8/8 kafa | tuttu |

Prospektif ölçüt: Birincil: D5 MAE, `v1_5_h99`'a karşı (SPEC_MARKET20_V0 §9). Canlı n = 0: hüküm yok (SPEC_SCORING §8).

### `pb_v0` (SPEC_PB_V0)

Plan: PLAN_PB (kesim ilk talep toplama günü B(k)); skorlanabilir fold D1 87, D3 87, D5 87, D10 84. Kurallar aynı PB kesimiyle, aynı fold'larda. **D1 p_up bütçe üstüdür** (3 katsayı, 10 azınlık olayı; SPEC_PB_V0 §4).

Getiri, MAE: model − basit kural

| Ufuk | Kural | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| D1 | `base_always_ceiling` | 87 (23) | 0.0340 | 0.0257 | +0.0083 | [+0.0047, +0.0125] | 20 / 67 / 0 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D1 | `base_train_median` | 87 (23) | 0.0340 | 0.0257 | +0.0083 | [+0.0047, +0.0125] | 20 / 67 / 0 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D1 | `base_train_mean` | 87 (23) | 0.0340 | 0.0341 | -0.0001 | [-0.0017, +0.0016] | 35 / 38 / 14 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | `base_zero` | 87 (23) | 0.0340 | 0.0882 | -0.0543 | [-0.0715, -0.0383] | 71 / 16 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | `base_always_ceiling` | 87 (23) | 0.1444 | 0.1379 | +0.0065 | [-0.0263, +0.0412] | 36 / 51 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | `base_train_median` | 87 (23) | 0.1444 | 0.1373 | +0.0071 | [-0.0256, +0.0417] | 30 / 57 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | `base_train_mean` | 87 (23) | 0.1444 | 0.1582 | -0.0138 | [-0.0251, -0.0019] | 50 / 37 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | `base_zero` | 87 (23) | 0.1444 | 0.2374 | -0.0930 | [-0.1474, -0.0418] | 59 / 28 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | `base_always_ceiling` | 87 (23) | 0.2751 | 0.3332 | -0.0582 | [-0.1293, +0.0216] | 52 / 35 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | `base_train_median` | 87 (23) | 0.2751 | 0.3106 | -0.0355 | [-0.0775, +0.0102] | 56 / 31 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | `base_train_mean` | 87 (23) | 0.2751 | 0.2931 | -0.0181 | [-0.0367, +0.0004] | 47 / 34 / 6 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | `base_zero` | 87 (23) | 0.2751 | 0.3440 | -0.0690 | [-0.1606, +0.0147] | 51 / 36 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | `base_always_ceiling` | 84 (23) | 0.5178 | 1.1810 | -0.6632 | [-0.8403, -0.4704] | 66 / 18 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | `base_train_median` | 84 (23) | 0.5178 | 0.5656 | -0.0478 | [-0.1067, +0.0146] | 50 / 34 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | `base_train_mean` | 84 (23) | 0.5178 | 0.5917 | -0.0739 | [-0.1016, -0.0465] | 53 / 31 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | `base_zero` | 84 (23) | 0.5178 | 0.5093 | +0.0085 | [-0.1442, +0.1673] | 38 / 46 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |

P(kapanış > arz), Brier (skorlamada [0.01, 0.99] kırpması): model − basit kural

| Ufuk | Kural | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| D1 | `base_always_ceiling` | 80 (22) | 0.1000 | 0.1103 | -0.0104 | [-0.0257, +0.0037] | 9 / 71 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | `base_rate` | 80 (22) | 0.1000 | 0.1025 | -0.0025 | [-0.0080, +0.0018] | 23 / 19 / 38 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | `base_last10_rate` | 80 (22) | 0.1000 | 0.1088 | -0.0088 | [-0.0160, -0.0027] | 43 / 37 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | `base_always_ceiling` | 80 (22) | 0.1625 | 0.2083 | -0.0459 | [-0.0838, -0.0049] | 17 / 62 / 1 | **model geçiyor** (aralık 0'ın altında) |
| D3 | `base_rate` | 80 (22) | 0.1625 | 0.1753 | -0.0128 | [-0.0264, +0.0044] | 45 / 35 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | `base_last10_rate` | 80 (22) | 0.1625 | 0.1786 | -0.0162 | [-0.0385, +0.0147] | 43 / 37 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | `base_always_ceiling` | 80 (22) | 0.1741 | 0.2329 | -0.0587 | [-0.1090, -0.0027] | 19 / 61 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | `base_rate` | 80 (22) | 0.1741 | 0.1892 | -0.0151 | [-0.0292, +0.0033] | 46 / 34 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | `base_last10_rate` | 80 (22) | 0.1741 | 0.2024 | -0.0283 | [-0.0560, +0.0053] | 48 / 32 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | `base_always_ceiling` | 80 (22) | 0.2072 | 0.2941 | -0.0869 | [-0.1540, -0.0158] | 24 / 56 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | `base_rate` | 80 (22) | 0.2072 | 0.2218 | -0.0147 | [-0.0259, -0.0042] | 43 / 31 / 6 | **model geçiyor** (aralık 0'ın altında) |
| D10 | `base_last10_rate` | 80 (22) | 0.2072 | 0.2904 | -0.0832 | [-0.1302, -0.0378] | 46 / 34 / 0 | **model geçiyor** (aralık 0'ın altında) |

Fit edilemeyen fold'lar — bu model: D1 logit MODEL_NOT_FIT_SINGLE_CLASS: 7; D3 logit MODEL_NOT_FIT_SINGLE_CLASS: 7; D5 logit MODEL_NOT_FIT_SINGLE_CLASS: 7; D10 logit MODEL_NOT_FIT_SINGLE_CLASS: 4. `v1_5_h99`: D1 logit MODEL_NOT_FIT_SINGLE_CLASS: 9; D3 logit MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE: 1; D3 logit MODEL_NOT_FIT_SINGLE_CLASS: 7; D5 logit MODEL_NOT_FIT_SINGLE_CLASS: 6; D10 logit MODEL_NOT_FIT_SINGLE_CLASS: 6.

Bilgi amaçlı eşleşik karşılaştırma: `pb_v0` − `v1_5_h99`, aynı test arzı ve ufuk (eğitim kümeleri farklı: B(k) ve T(k) kesimleri); fark "talep katının değeri"dir (SPEC_PB_V0 §7):

| Ufuk | Çıktı | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| D1 | MAE | 87 (23) | 0.0340 | 0.0304 | +0.0036 | [+0.0013, +0.0060] | 34 / 53 / 0 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D1 | Brier | 80 (22) | 0.1000 | 0.0943 | +0.0056 | [-0.0103, +0.0215] | 24 / 56 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | MAE | 87 (23) | 0.1444 | 0.1215 | +0.0229 | [+0.0091, +0.0369] | 25 / 62 / 0 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D3 | Brier | 79 (22) | 0.1639 | 0.1394 | +0.0245 | [-0.0202, +0.0660] | 21 / 58 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | MAE | 87 (23) | 0.2751 | 0.2220 | +0.0530 | [+0.0337, +0.0726] | 25 / 62 / 0 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D5 | Brier | 80 (22) | 0.1741 | 0.1524 | +0.0217 | [-0.0217, +0.0580] | 23 / 57 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | MAE | 84 (23) | 0.5178 | 0.4298 | +0.0880 | [-0.0062, +0.1732] | 34 / 50 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | Brier | 80 (22) | 0.2072 | 0.1800 | +0.0272 | [-0.0161, +0.0623] | 23 / 57 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |

Ridge α seçim dağılımı (fold sayısı; yalnız FIT_OK fold'lar). Kenar = sonlu uç değer(ler): 0.001, 10000.0.

| Ufuk | 0.001 | 0.01 | 0.1 | 1.0 | 10.0 | 100.0 | 1000.0 | 10000.0 | INF | n | en sık sonlu uç değerin payı |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 | 0 | 0 | 4 | 3 | 14 | 50 | 2 | 0 | 14 | 87 | %0 |
| D3 | 6 | 0 | 0 | 9 | 64 | 8 | 0 | 0 | 0 | 87 | %7 |
| D5 | 54 | 0 | 2 | 2 | 17 | 6 | 0 | 0 | 6 | 87 | %62 |
| D10 | 9 | 3 | 0 | 35 | 30 | 7 | 0 | 0 | 0 | 84 | %11 |

Logit C seçim dağılımı (fold sayısı; yalnız FIT_OK fold'lar). Kenar = sonlu uç değer(ler): 0.0001, 100.0.

| Ufuk | ZERO | 0.0001 | 0.001 | 0.01 | 0.1 | 1.0 | 10.0 | 100.0 | n | en sık sonlu uç değerin payı |
|---|---|---|---|---|---|---|---|---|---|---|
| D1 | 38 | 0 | 1 | 7 | 34 | 0 | 0 | 0 | 80 | %0 |
| D3 | 0 | 0 | 0 | 0 | 66 | 14 | 0 | 0 | 80 | %0 |
| D5 | 0 | 0 | 0 | 0 | 80 | 0 | 0 | 0 | 80 | %0 |
| D10 | 6 | 0 | 1 | 9 | 64 | 0 | 0 | 0 | 80 | %0 |

Aday başına yakınsamama: 9 (fold, C) adayı `CANDIDATE_NOT_CONVERGED`; nihai fit'te sıradaki adaya geçilen fold: 0.

Nihai fit (99 arz): D1 α = 10.0, C = 0.1; D3 α = 1.0, C = 0.1; D5 α = 0.001, C = 0.1; D10 α = 0.001, C = 0.1.

| Kaynak | Şartnamedeki beklenti (aynen) | Gerçekleşen (backtest) | Tuttu mu |
|---|---|---|---|
| SPEC_PB_V0.md §8 | D1 MAE: `base_train_median`'a YENİK ya da eşit (V1.5 bile f3'le yeniliyor: +0.0046 [+0.0015, +0.0079], AUDIT §1.2-c). D1 p_up: taban oranından ayırt edilemez. | D1 MAE − medyan +0.0083 [+0.0047, +0.0125]; D1 Brier − taban oranı -0.0025 [-0.0080, +0.0018] | tuttu |
| SPEC_PB_V0.md §8 | D5/D10 MAE: medyana karşı noktasal küçük kazanç mümkün (V1.5'in −0.084 / −0.116'sının en çok üçte biri); aralık büyük olasılıkla 0'ı içerir. | D5 -0.0355 [-0.0775, +0.0102] (sınır −0.028); D10 -0.0478 [-0.1067, +0.0146] (sınır −0.0387) | kısmen (tutmayan: D5 kazanç ≤ üçte bir; D10 kazanç ≤ üçte bir) |
| SPEC_PB_V0.md §8 | V1.5'e karşı: her ufukta daha kötü ya da eşit. | aralığı tamamen 0'ın altında hücre: yok; noktasal: MAE D1 +0.0036, Brier D1 +0.0056, MAE D3 +0.0229, Brier D3 +0.0245, MAE D5 +0.0530, Brier D5 +0.0217, MAE D10 +0.0880, Brier D10 +0.0272 | tuttu |
| SPEC_PB_V0.md §8 | Seçilen α çoğunlukla ≥ 100; D1'de INF sık. | α ≥ 100 (INF dahil): %27; D1'de INF: %16 | tutmadı |
| SPEC_PB_V0.md §4 | D1'de beklenti "ZERO ya da C ≤ 0.001 seçilir, taban oranından ayırt edilemez" | D1 C ∈ {ZERO, 0.0001, 0.001}: %49; D1 Brier − taban oranı -0.0025 [-0.0080, +0.0018] | kısmen (tutmayan: ZERO ya da C ≤ 0.001 seçilir) |

Prospektif ölçüt: Birincil: D5 MAE, `base_train_median`'a karşı (SPEC_PB_V0 §8). Canlı n = 0: hüküm yok (SPEC_SCORING §8).

### `ceiling_hazard_v0` (SPEC_CEILING_V0)

Plan: PLAN_CEILING (kesim T, f3 dolu arzlar, ≥ 10 arz / ≥ 5 olay / ≥ 5 sağ kalım): 87 fold, ilki EKOS 2023-11-21. Test kümesinde L < 1: 16, L < 3: 31, L ≥ 5: 33, L ≥ 10: 11 (SPEC_CEILING_V0 §6: 16 / 31 / 33 / 11). Kurallar aynı fold'larda, aynı kişi-dönem eğitim kümesinden.

Birincil metrik RPS = (1/10) Σ_k (S_k − 1[L ≥ k])², kırpmasız; fark = model − kural:

| Kural | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v0@INF` | 87 (24) | 0.1503 | 0.2006 | -0.0503 | [-0.0724, -0.0263] | 58 / 29 / 0 | **model geçiyor** (aralık 0'ın altında) |
| `base_km_expanding` | 87 (24) | 0.1503 | 0.2072 | -0.0569 | [-0.0833, -0.0286] | 59 / 28 / 0 | **model geçiyor** (aralık 0'ın altında) |
| `base_km_last10` | 87 (24) | 0.1503 | 0.1999 | -0.0496 | [-0.0751, -0.0219] | 52 / 35 / 0 | **model geçiyor** (aralık 0'ın altında) |
| `base_always_ceiling` | 87 (24) | 0.1503 | 0.5966 | -0.4462 | [-0.5488, -0.3236] | 74 / 13 / 0 | **model geçiyor** (aralık 0'ın altında) |

Gün başına Brier (S_k, kırpmasız): model − en iyi KM kuralı (`base_km_last10`) ve model − `ceiling_hazard_v0@INF`:

| k | n | model | en iyi KM | fark | %95 aralık | model | @INF | fark | %95 aralık |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 87 | 0.1253 | 0.1524 | -0.0271 | [-0.0497, -0.0052] | 0.1253 | 0.1554 | -0.0301 | [-0.0479, -0.0142] |
| 2 | 87 | 0.1728 | 0.2378 | -0.0650 | [-0.1008, -0.0252] | 0.1728 | 0.2359 | -0.0631 | [-0.0963, -0.0361] |
| 3 | 87 | 0.1600 | 0.2539 | -0.0939 | [-0.1287, -0.0578] | 0.1600 | 0.2439 | -0.0839 | [-0.1200, -0.0545] |
| 4 | 87 | 0.1679 | 0.2556 | -0.0877 | [-0.1509, -0.0201] | 0.1679 | 0.2615 | -0.0935 | [-0.1318, -0.0556] |
| 5 | 87 | 0.1876 | 0.2602 | -0.0726 | [-0.1170, -0.0274] | 0.1876 | 0.2547 | -0.0672 | [-0.1005, -0.0303] |
| 6 | 87 | 0.1635 | 0.2216 | -0.0581 | [-0.0903, -0.0240] | 0.1635 | 0.2277 | -0.0642 | [-0.0926, -0.0337] |
| 7 | 87 | 0.1512 | 0.2059 | -0.0546 | [-0.0872, -0.0218] | 0.1512 | 0.2026 | -0.0514 | [-0.0781, -0.0189] |
| 8 | 87 | 0.1399 | 0.1602 | -0.0204 | [-0.0606, +0.0222] | 0.1399 | 0.1679 | -0.0280 | [-0.0608, +0.0099] |
| 9 | 87 | 0.1249 | 0.1354 | -0.0105 | [-0.0553, +0.0384] | 0.1249 | 0.1363 | -0.0114 | [-0.0485, +0.0327] |
| 10 | 87 | 0.1101 | 0.1155 | -0.0055 | [-0.0502, +0.0375] | 0.1101 | 0.1196 | -0.0096 | [-0.0479, +0.0294] |

Kalibrasyon (ortalama S_k ve gözlenen P(L ≥ k), aynı fold'lar):

| k | model ort. S_k | `base_km_expanding` | `base_km_last10` | gözlenen |
|---|---|---|---|---|
| 1 | 0.8655 | 0.8912 | 0.8460 | 0.8161 |
| 3 | 0.7041 | 0.7731 | 0.6912 | 0.6437 |
| 5 | 0.4342 | 0.5389 | 0.4349 | 0.3793 |
| 10 | 0.1874 | 0.2159 | 0.1578 | 0.1264 |

İkincil çıktı P(Dk'de tavan kapanışı), Brier (kırpmasız); fark = model − karşılaştırılan:

| k | Karşılaştırılan | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| 1 | `ceiling_hazard_v0@INF` | 87 (24) | 0.1253 | 0.1554 | -0.0301 | [-0.0479, -0.0142] | 58 / 29 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 1 | `base_km_expanding` | 87 (24) | 0.1253 | 0.1568 | -0.0316 | [-0.0503, -0.0150] | 52 / 35 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 1 | `base_km_last10` | 87 (24) | 0.1253 | 0.1524 | -0.0271 | [-0.0497, -0.0052] | 41 / 46 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 1 | `base_always_ceiling` | 87 (24) | 0.1253 | 0.1839 | -0.0586 | [-0.1015, -0.0192] | 16 / 71 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 1 | `v1_5_p_up_as_ceiling` | 78 (22) | 0.1294 | 0.1625 | -0.0332 | [-0.0648, -0.0031] | 25 / 53 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 3 | `ceiling_hazard_v0@INF` | 87 (24) | 0.1630 | 0.2458 | -0.0828 | [-0.1187, -0.0537] | 69 / 18 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 3 | `base_km_expanding` | 87 (24) | 0.1630 | 0.2513 | -0.0883 | [-0.1280, -0.0554] | 65 / 22 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 3 | `base_km_last10` | 87 (24) | 0.1630 | 0.2536 | -0.0906 | [-0.1254, -0.0552] | 61 / 26 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 3 | `base_always_ceiling` | 87 (24) | 0.1630 | 0.3563 | -0.1934 | [-0.3001, -0.0990] | 31 / 56 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 3 | `v1_5_p_up_as_ceiling` | 78 (23) | 0.1580 | 0.1870 | -0.0290 | [-0.0668, +0.0036] | 27 / 51 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| 5 | `ceiling_hazard_v0@INF` | 87 (24) | 0.2021 | 0.2647 | -0.0626 | [-0.1003, -0.0264] | 59 / 28 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 5 | `base_km_expanding` | 87 (24) | 0.2021 | 0.2756 | -0.0735 | [-0.1204, -0.0288] | 60 / 27 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 5 | `base_km_last10` | 87 (24) | 0.2021 | 0.2752 | -0.0731 | [-0.1157, -0.0389] | 56 / 31 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 5 | `base_always_ceiling` | 87 (24) | 0.2021 | 0.5402 | -0.3381 | [-0.4819, -0.1942] | 47 / 40 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 5 | `v1_5_p_up_as_ceiling` | 79 (23) | 0.1905 | 0.3079 | -0.1174 | [-0.1989, -0.0476] | 43 / 36 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 10 | `ceiling_hazard_v0@INF` | 87 (24) | 0.1673 | 0.1884 | -0.0211 | [-0.0553, +0.0135] | 56 / 31 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| 10 | `base_km_expanding` | 87 (24) | 0.1673 | 0.1884 | -0.0210 | [-0.0564, +0.0151] | 56 / 31 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| 10 | `base_km_last10` | 87 (24) | 0.1673 | 0.1920 | -0.0247 | [-0.0662, +0.0160] | 55 / 32 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| 10 | `base_always_ceiling` | 87 (24) | 0.1673 | 0.7586 | -0.5913 | [-0.7167, -0.4456] | 66 / 21 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 10 | `v1_5_p_up_as_ceiling` | 79 (23) | 0.1613 | 0.3842 | -0.2229 | [-0.3140, -0.1466] | 62 / 17 / 0 | **model geçiyor** (aralık 0'ın altında) |

Seçilen λ (fold sayısı): 0.1: 0, 1.0: 9, 3.0: 40, 10.0: 38, 30.0: 0, 100.0: 0, 300.0: 0, 1000.0: 0, INF: 0. İlk 20 fold'da INF: 0. Yakınsamayan λ adayı: 0; fold durumları: FIT_OK 87.

Nihai fit (97 arz, 506 risk-günü, 83 olay): λ = 10.0; γ = [-1.8095, -2.1470, -1.0071]; β_f1 = +0.4489, β_f2 = -0.1787, β_f3 = -0.5499. Yeniden-tavan oranları: r_a = (1 + 0.5)/(102 + 1) = 0.0146, r_b = (61 + 0.5)/(429 + 1) = 0.1430.

| Kaynak | Şartnamedeki beklenti (aynen) | Gerçekleşen (backtest) | Tuttu mu |
|---|---|---|---|
| SPEC_CEILING_V0.md §11 | Backtest RPS farkı (model − en iyi KM kuralı): −0.005 … −0.02; blok bootstrap %95 aralığı büyük olasılıkla 0'ı içerir (V1.5 Logit'in D1 Brier farkı −0.008 [−0.028, +0.011], AUDIT §1.2-c; çözünürlük ~0.02, AUDIT §3b). | en iyi KM `base_km_last10`: fark -0.0496 [-0.0751, -0.0219], n = 87 | tutmadı |
| SPEC_CEILING_V0.md §11 | En çok kazanç k = 3…5'te (azınlık 31–33); k = 1'de küçük; k = 10'da ≈ 0 ya da hafif kötü. | k'ya göre Brier farkı (en iyi KM): k1 -0.0271, k2 -0.0650, k3 -0.0939, k4 -0.0877, k5 -0.0726, k6 -0.0581, k7 -0.0546, k8 -0.0204, k9 -0.0105, k10 -0.0055; en çok kazanç k = 3 | kısmen (tutmayan: k = 1'de küçük; k = 10'da ≈ 0 ya da hafif kötü) |
| SPEC_CEILING_V0.md §11 | Seçilen λ çoğu fold'da 10–300; erken fold'larda INF sık. | λ ∈ {10, 30, 100, 300}: %44; ilk 20 fold'da INF: %0 | tutmadı |
| SPEC_CEILING_V0.md §11 | Nihai fit'te işaretler: β_f3 < 0, β_f1 > 0, β_f2 > 0. | β_f1 = +0.4489, β_f2 = -0.1787, β_f3 = -0.5499 | kısmen (tutmayan: β_f2 > 0) |
| SPEC_CEILING_V0.md §11 | (c) backtest'te model `@INF` kuralından noktasal olarak kötü → "özellikler bilgi eklemiyor" diye yazılır. | RPS model − @INF = -0.0503 [-0.0724, -0.0263]: model @INF'ten noktasal olarak kötü değil | başarısızlık (c) gerçekleşmedi |
| SPEC_CEILING_V0.md §11 | (b) \|ortalama S_1 − gözlenen D1 tavan oranı\| > 0.15 (kalibrasyon) | backtest: ort. S_1 0.8655, gözlenen D1 tavan oranı 0.8161, \|fark\| = 0.0494 | ölçüt prospektif; backtest'te aşılmadı |

Prospektif ölçüt: Birincil: RPS; `base_km_last10` **ve** `base_km_expanding`'e karşı (SPEC_CEILING_V0 §11). Canlı n = 0: hüküm yok (SPEC_SCORING §8).

### `pb_ceiling_v0` (SPEC_PB_V0 §9)

Plan: PLAN_PB_CEILING (kesim B(k), 99 arz, aynı skorlanabilirlik kuralı): **87 skorlanabilir fold** (şartname bu sayıyı ölçmedi; beklenen 84–89), ilki SKYMD 2023-12-06.

Birincil metrik RPS = (1/10) Σ_k (S_k − 1[L ≥ k])², kırpmasız; fark = model − kural:

| Kural | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|
| `pb_ceiling_v0@INF` | 87 (23) | 0.1821 | 0.2056 | -0.0235 | [-0.0367, -0.0083] | 57 / 30 / 0 | **model geçiyor** (aralık 0'ın altında) |
| `base_km_expanding` | 87 (23) | 0.1821 | 0.2144 | -0.0324 | [-0.0544, -0.0114] | 61 / 26 / 0 | **model geçiyor** (aralık 0'ın altında) |
| `base_km_last10` | 87 (23) | 0.1821 | 0.2156 | -0.0335 | [-0.0612, -0.0019] | 50 / 37 / 0 | **model geçiyor** (aralık 0'ın altında) |
| `base_always_ceiling` | 87 (23) | 0.1821 | 0.6195 | -0.4375 | [-0.5334, -0.3231] | 74 / 13 / 0 | **model geçiyor** (aralık 0'ın altında) |

Gün başına Brier (S_k, kırpmasız): model − en iyi KM kuralı (`base_km_expanding`) ve model − `pb_ceiling_v0@INF`:

| k | n | model | en iyi KM | fark | %95 aralık | model | @INF | fark | %95 aralık |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 87 | 0.1560 | 0.1746 | -0.0186 | [-0.0320, -0.0044] | 0.1560 | 0.1728 | -0.0168 | [-0.0294, -0.0031] |
| 2 | 87 | 0.2239 | 0.2476 | -0.0238 | [-0.0378, -0.0059] | 0.2239 | 0.2514 | -0.0276 | [-0.0436, -0.0080] |
| 3 | 87 | 0.2165 | 0.2652 | -0.0488 | [-0.0689, -0.0249] | 0.2165 | 0.2572 | -0.0408 | [-0.0568, -0.0225] |
| 4 | 87 | 0.2406 | 0.3004 | -0.0598 | [-0.1010, -0.0153] | 0.2406 | 0.2728 | -0.0322 | [-0.0557, -0.0046] |
| 5 | 87 | 0.2315 | 0.2820 | -0.0504 | [-0.0967, -0.0099] | 0.2315 | 0.2616 | -0.0301 | [-0.0560, -0.0019] |
| 6 | 87 | 0.1932 | 0.2453 | -0.0522 | [-0.0950, -0.0161] | 0.1932 | 0.2310 | -0.0379 | [-0.0620, -0.0146] |
| 7 | 87 | 0.1757 | 0.2086 | -0.0329 | [-0.0512, -0.0128] | 0.1757 | 0.2026 | -0.0268 | [-0.0453, -0.0047] |
| 8 | 87 | 0.1516 | 0.1703 | -0.0186 | [-0.0462, +0.0058] | 0.1516 | 0.1646 | -0.0129 | [-0.0290, +0.0052] |
| 9 | 87 | 0.1269 | 0.1366 | -0.0097 | [-0.0288, +0.0074] | 0.1269 | 0.1306 | -0.0037 | [-0.0194, +0.0113] |
| 10 | 87 | 0.1049 | 0.1137 | -0.0088 | [-0.0256, +0.0071] | 0.1049 | 0.1115 | -0.0066 | [-0.0208, +0.0080] |

Kalibrasyon (ortalama S_k ve gözlenen P(L ≥ k), aynı fold'lar):

| k | model ort. S_k | `base_km_expanding` | `base_km_last10` | gözlenen |
|---|---|---|---|---|
| 1 | 0.8565 | 0.8836 | 0.8379 | 0.7931 |
| 3 | 0.7050 | 0.7656 | 0.6909 | 0.6207 |
| 5 | 0.4420 | 0.5356 | 0.4374 | 0.3563 |
| 10 | 0.1623 | 0.2163 | 0.1621 | 0.1034 |

İkincil çıktı P(Dk'de tavan kapanışı), Brier (kırpmasız); fark = model − karşılaştırılan:

| k | Karşılaştırılan | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| 1 | `pb_ceiling_v0@INF` | 87 (23) | 0.1560 | 0.1728 | -0.0168 | [-0.0294, -0.0031] | 51 / 36 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 1 | `base_km_expanding` | 87 (23) | 0.1560 | 0.1746 | -0.0186 | [-0.0320, -0.0044] | 44 / 43 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 1 | `base_km_last10` | 87 (23) | 0.1560 | 0.1762 | -0.0202 | [-0.0401, +0.0019] | 40 / 47 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| 1 | `base_always_ceiling` | 87 (23) | 0.1560 | 0.2069 | -0.0509 | [-0.0915, -0.0087] | 18 / 69 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 3 | `pb_ceiling_v0@INF` | 87 (23) | 0.2180 | 0.2561 | -0.0380 | [-0.0544, -0.0199] | 54 / 33 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 3 | `base_km_expanding` | 87 (23) | 0.2180 | 0.2617 | -0.0437 | [-0.0626, -0.0228] | 52 / 35 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 3 | `base_km_last10` | 87 (23) | 0.2180 | 0.2741 | -0.0561 | [-0.0913, -0.0152] | 50 / 37 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 3 | `base_always_ceiling` | 87 (23) | 0.2180 | 0.3678 | -0.1498 | [-0.2411, -0.0597] | 32 / 55 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 5 | `pb_ceiling_v0@INF` | 87 (23) | 0.2401 | 0.2735 | -0.0334 | [-0.0628, -0.0063] | 57 / 30 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 5 | `base_km_expanding` | 87 (23) | 0.2401 | 0.2920 | -0.0519 | [-0.0993, -0.0118] | 58 / 29 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 5 | `base_km_last10` | 87 (23) | 0.2401 | 0.3042 | -0.0641 | [-0.1218, -0.0154] | 48 / 39 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 5 | `base_always_ceiling` | 87 (23) | 0.2401 | 0.5632 | -0.3231 | [-0.4540, -0.1943] | 49 / 38 / 0 | **model geçiyor** (aralık 0'ın altında) |
| 10 | `pb_ceiling_v0@INF` | 87 (23) | 0.1789 | 0.1830 | -0.0041 | [-0.0224, +0.0159] | 55 / 32 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| 10 | `base_km_expanding` | 87 (23) | 0.1789 | 0.1845 | -0.0057 | [-0.0271, +0.0156] | 56 / 31 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| 10 | `base_km_last10` | 87 (23) | 0.1789 | 0.1885 | -0.0096 | [-0.0336, +0.0145] | 45 / 42 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| 10 | `base_always_ceiling` | 87 (23) | 0.1789 | 0.7816 | -0.6028 | [-0.7338, -0.4569] | 68 / 19 / 0 | **model geçiyor** (aralık 0'ın altında) |

Seçilen λ (fold sayısı): 0.1: 0, 1.0: 1, 3.0: 23, 10.0: 62, 30.0: 1, 100.0: 0, 300.0: 0, 1000.0: 0, INF: 0. İlk 20 fold'da INF: 0. Yakınsamayan λ adayı: 0; fold durumları: FIT_OK 87.

Nihai fit (99 arz, 508 risk-günü, 85 olay): λ = 10.0; γ = [-1.5693, -2.1625, -1.1973]; β_pb1 = +0.4445, β_pb2 = -0.1462. Yeniden-tavan oranları: r_a = (2 + 0.5)/(108 + 1) = 0.0229, r_b = (61 + 0.5)/(441 + 1) = 0.1391.

Eşleşik RPS: `pb_ceiling_v0` − `ceiling_hazard_v0`, iki modelin de skorlandığı test arzları:

| Karşılaştırılan | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v0` | 85 (23) | 0.1817 | 0.1475 | +0.0342 | [+0.0180, +0.0515] | 28 / 57 / 0 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |

| Kaynak | Şartnamedeki beklenti (aynen) | Gerçekleşen (backtest) | Tuttu mu |
|---|---|---|---|
| SPEC_PB_V0.md §9 | Beklenti: RPS'te KM kurallarından ayırt edilemez; `ceiling_hazard_v0`'dan kötü ya da eşit. | RPS farkı: `base_km_expanding` -0.0324 [-0.0544, -0.0114]; `base_km_last10` -0.0335 [-0.0612, -0.0019]; `ceiling_hazard_v0`'a karşı +0.0342 [+0.0180, +0.0515] (n = 85) | kısmen (tutmayan: `base_km_expanding`'den ayırt edilemez; `base_km_last10`'dan ayırt edilemez) |

Prospektif ölçüt: Birincil: RPS; ölçüt SPEC_CEILING_V0 §11 ile aynı (SPEC_PB_V0 §9). Canlı n = 0: hüküm yok (SPEC_SCORING §8).

### Faz 1B koşuları ve deney günlüğü

| Koşu | Model | Plan | Fold | Ledger sha256 (ilk 12) | Günlükteki koşu sayısı |
|---|---|---|---|---|---|
| `v1_6_h99` | `v1_6_h99` | v15 | 351 | `94570b7d3b9e` | 2 |
| `v1_5_market20_v0` | `v1_5_market20_v0` | v15 | 351 | `552d8975fea1` | 2 |
| `pb_v0` | `pb_v0` | pb | 345 | `0f5c484eafbc` | 2 |
| `base_always_ceiling__pb` | `base_always_ceiling` | pb | 345 | `bd4c84a71dfb` | 2 |
| `base_train_median__pb` | `base_train_median` | pb | 345 | `9f76e3c251d9` | 2 |
| `base_train_mean__pb` | `base_train_mean` | pb | 345 | `9b85eb6a707e` | 2 |
| `base_zero__pb` | `base_zero` | pb | 345 | `3d500e1702a2` | 2 |
| `base_rate__pb` | `base_rate` | pb | 345 | `ba4466a50d18` | 2 |
| `base_last10_rate__pb` | `base_last10_rate` | pb | 345 | `a0b959fc28a8` | 2 |
| `ceiling_hazard_v0` | `ceiling_hazard_v0` | ceiling | 87 | `976b4dcea981` | 2 |
| `ceiling_hazard_v0@INF` | `ceiling_hazard_v0@INF` | ceiling | 87 | `90b610463de4` | 2 |
| `base_km_expanding` | `base_km_expanding` | ceiling | 87 | `ed1b8821a0c5` | 2 |
| `base_km_last10` | `base_km_last10` | ceiling | 87 | `6d605dd02b7c` | 2 |
| `base_always_ceiling__ceiling` | `base_always_ceiling` | ceiling | 87 | `f03bf949afa2` | 2 |
| `pb_ceiling_v0` | `pb_ceiling_v0` | pb_ceiling | 87 | `c92ce859ac67` | 2 |
| `pb_ceiling_v0@INF` | `pb_ceiling_v0@INF` | pb_ceiling | 87 | `cd7d7312777c` | 2 |
| `base_km_expanding__pb_ceiling` | `base_km_expanding` | pb_ceiling | 87 | `720cad51f85c` | 2 |
| `base_km_last10__pb_ceiling` | `base_km_last10` | pb_ceiling | 87 | `9ce48925224f` | 2 |
| `base_always_ceiling__pb_ceiling` | `base_always_ceiling` | pb_ceiling | 87 | `0fa306e3c7f0` | 2 |

"Günlükteki koşu sayısı": `experiments/log.jsonl`'da bu koşu anahtarının (model + plan) satır sayısı. Aynı veride bakılan her koşu sayılır (CLAUDE.md kural 4); bir koşunun ledger'ı altın ledger'la aynıysa sayı artsa da sonuç aynıdır.

## Faz 4: tavan yolu modelleri (Fable şartnamesi, docs/specs_faz4/)

**Terazi:** aşağıdaki her sayı **backtest**tir (retrospektif walk-forward, H99) ve **tasarıma maruzdur** (§10: grup ayrımı, N_MIN ve havuzlama sırası H99 kırılma sonrası ölçümleri görüldükten sonra seçildi); kanıt değeri düşüktür. Asıl ölçüm prospektiftir. 2026-08-06 sonrası listelenen ilk 7 arz (CITAS…NETGL) bu modeller için **RETRO**'dur; bu 7 arz için tavan yolu kaydı yazılmadı ve canlı sicilde bu modellerin satırı yoktur. "Geçiyor" yalnız aralık 0'ı dışlıyorsa yazılır.

Şartname: `docs/specs_faz4/SPEC_CEILING_PATH_V0.md` (sha256 `079836604724…`, commit 52e1567, uygulamadan önce push edildi). Üç model, yeni serbest parametre 0; seri bileşeni S_k dondurulmuş tavan modellerinden aynen (gömülü, sha'sı INDEX'le aynı).

| Plan | Model | S_k kaynağı (Faz 1B altın ledger'ı) | Hücre kesimi |
|---|---|---|---|
| `H99_CEILING_PATH_T_CUTOFF_REUSE_CEILING_LEDGER` | `ceiling_path_v0` | `ceiling_hazard_v0_fold_ledger.csv` (`976b4dcea981`) | T ilk işlem günü |
| `H99_CEILING_PATH_T_CUTOFF_REUSE_CEILING_LEDGER` | `ceiling_path_v0@INF` | `ceiling_hazard_v0@INF_fold_ledger.csv` (`90b610463de4`) | T ilk işlem günü |
| `H99_PB_CEILING_PATH_B_CUTOFF_REUSE_PB_CEILING_LEDGER` | `pb_ceiling_path_v0` | `pb_ceiling_v0_fold_ledger.csv` (`c92ce859ac67`) | B(k) ilk talep toplama günü |

Yöntem: fold kümesi ve sırası kaynak tavan ledger'ınınkidir; her fold'da S_1..S_10 ledger'dan okunur (yeniden fit yok), kırılma sonrası hücreler 99 arzdan yalnız seans tarihi < kesim olan gözlemlerle kurulur (§3). Tahmin = karışımın medyanı (MAE), p_up = P(R_h > 0) (Brier). Eşleşik fark = model − karşılaştırılan, iki tarafın da skorlandığı test arzları; %95 aralık blok bootstrap (ilk işlem ayı blokları, 4000 tekrar, `random.Random(20260921)`; SPEC_DEVIATIONS C7).

Etiket kuralları (sonuçlar görülmeden kodda sabitlendi, `borsai/report_faz4.py: OPERATIONAL_RULES_FAZ4`):

- Satırın beklenen fark aralığı [alt, üst] ("|fark| < x" için açık aralık (−x, x)); fark = model − karşılaştırılan, negatif = model iyi. Fark alt ucun altındaysa **daha iyi**, üst ucun üstündeyse **daha kötü**.
- Fark aralık içindeyse "Aralık 0'ı" ifadesinin kesin kısmına bakılır: "içerir" → %95 aralık 0'ı içermeli; "dışlar (negatif)" → aralığın üst ucu < 0; "içerir ya da pozitif dışlar" → üst uç ≥ 0; "dışlayabilir" / "dışlaması olası" → aralık 0'ı pozitif tarafta dışlamamalı (alt uç ≤ 0). Kesin kısım tutuyorsa **tuttu**, tutmuyorsa **tutmadı**.
- Olasılık ifadeleri ("büyük olasılıkla içerir", "dışlaması olası", "dışlayabilir") etiketi yalnız yukarıdaki kesin kısımlarıyla etkiler; ifadenin tamamının gerçekleşip gerçekleşmediği ayrı sütunda yazılır.
- Beklentiden çok iyi (§6): birincil hücrede fark < -0.120 ya da aralığın üst ucu < -0.060; ya da §6 tablosunun D3/D5/D10 ufuklu herhangi bir satırında (`@INF` ve PB satırları dahil) fark < alt uç − 0.03.
- D1 beraberlik cümlesi: `ceiling_path_v0` − `base_always_ceiling` D1 MAE'de fold başına fark bit-eşit 0 ya da |fark| < 0.001 olan fold'ların payı ≥ 80/87.
- Eşleşik küme: iki tarafın da skorlandığı test arzları (ticker ile). Karşılaştırılan ledger'lar Faz 1A/1B altınlarıdır (yeniden koşulmaz). Brier [0.01, 0.99] kırpmalı (Faz 1A tablolarıyla aynı), MAE kırpmasız.

### Birincil hücre

`ceiling_path_v0` − `base_train_median`, D5 getiri MAE (önceden ilan edilen tek birincil hücre): **fark -0.1158, %95 aralık [-0.1611, -0.0738], n = 85** (23 ay); model 0.1842, kural 0.3000; model iyi / kural iyi / eşit 63 / 22 / 0. Hüküm (backtest): **model geçiyor** (aralık 0'ın altında). §6 beklentisi −0.090 … −0.020 → **daha iyi**.

**Beklentiden çok iyi denetimi (§6):** **TETİKLENDİ** (10 koşul) — birincil aralığın üst ucu -0.0738 < -0.060; `ceiling_path_v0` D5 MAE − `ceiling_path_v0@INF`: fark -0.1033 < alt uç -0.050 − 0.03; `ceiling_path_v0` D10 MAE − `base_train_median`: fark -0.1746 < alt uç -0.100 − 0.03; `ceiling_path_v0` D10 MAE − `base_always_ceiling`: fark -0.7888 < alt uç -0.750 − 0.03; `ceiling_path_v0` D10 MAE − `v1_5_h99`: fark -0.0595 < alt uç -0.020 − 0.03; `ceiling_path_v0` D10 MAE − `ceiling_path_v0@INF`: fark -0.1327 < alt uç -0.050 − 0.03; `ceiling_path_v0` D10 Brier − `base_rate`: fark -0.0667 < alt uç -0.020 − 0.03; `ceiling_path_v0` D10 Brier − `base_last10_rate`: fark -0.1165 < alt uç -0.070 − 0.03; `ceiling_path_v0` D10 Brier − `v1_5_h99`: fark -0.0311 < alt uç +0.010 − 0.03; `ceiling_path_v0` D10 Brier − `ceiling_path_v0@INF`: fark -0.0522 < alt uç -0.010 − 0.03. §6 gereği modeller **dondurulmadı**; farklı elle sıfırdan yeniden üretim gerekir (aşağıda "Dondurma").

### §6 beklentisi ile gerçekleşen (satır satır)

| Model | Ufuk | Çıktı | Karşılaştırılan | Beklenen fark (§6, aynen) | Aralık 0'ı (§6, aynen) | Gerçekleşen fark | %95 aralık | n | Etiket | Aralık ifadesi gerçekleşti mi |
|---|---|---|---|---|---|---|---|---|---|---|
| `ceiling_path_v0` | D1 | MAE | `base_always_ceiling` | 0.000 … +0.005 | içerir (beraberlik) | +0.0002 | [-0.0002, +0.0010] | 87 | tuttu | evet |
| `ceiling_path_v0` | D1 | MAE | `base_train_median` | 0.000 … +0.005 | içerir | +0.0002 | [-0.0002, +0.0010] | 87 | tuttu | evet |
| `ceiling_path_v0` | D1 | MAE | `v1_5_h99` | −0.007 … −0.002 | dışlayabilir (negatif) | -0.0058 | [-0.0087, -0.0025] | 87 | tuttu | evet |
| `ceiling_path_v0` | D1 | MAE | sıfır model | \|fark\| < 0.001 | içerir | +0.0004 | [+0.0000, +0.0012] | 87 | tuttu | evet |
| `ceiling_path_v0` | D1 | Brier | `base_rate` | −0.005 … +0.005 | içerir | -0.0097 | [-0.0176, -0.0008] | 87 | daha iyi | hayır |
| `ceiling_path_v0` | D1 | Brier | `base_last10_rate` | −0.010 … +0.002 | içerir | -0.0167 | [-0.0264, -0.0079] | 87 | daha iyi | hayır |
| `ceiling_path_v0` | D1 | Brier | `v1_5_h99` | −0.002 … +0.010 | içerir | -0.0118 | [-0.0226, -0.0016] | 78 | daha iyi | hayır |
| `ceiling_path_v0` | D1 | Brier | sıfır model | \|fark\| < 0.003 | içerir | -0.0084 | [-0.0157, -0.0006] | 87 | daha iyi | hayır |
| `ceiling_path_v0` | D3 | MAE | `base_always_ceiling` | −0.020 … +0.005 | içerir | -0.0200 | [-0.0411, -0.0054] | 86 | tutmadı | hayır |
| `ceiling_path_v0` | D3 | MAE | `base_train_median` | −0.020 … +0.005 | içerir | -0.0194 | [-0.0404, -0.0049] | 86 | tutmadı | hayır |
| `ceiling_path_v0` | D3 | MAE | `v1_5_h99` | −0.010 … +0.020 | içerir | -0.0087 | [-0.0301, +0.0131] | 86 | tuttu | evet |
| `ceiling_path_v0` | D3 | MAE | sıfır model | −0.015 … 0.000 | içerir | -0.0188 | [-0.0397, -0.0044] | 87 | daha iyi | hayır |
| `ceiling_path_v0` | D3 | Brier | `base_rate` | −0.040 … −0.005 | büyük olasılıkla içerir | -0.0362 | [-0.0553, -0.0163] | 86 | tuttu | hayır |
| `ceiling_path_v0` | D3 | Brier | `base_last10_rate` | −0.040 … −0.005 | büyük olasılıkla içerir | -0.0386 | [-0.0628, -0.0113] | 86 | tuttu | hayır |
| `ceiling_path_v0` | D3 | Brier | `v1_5_h99` | −0.010 … +0.030 | içerir | -0.0085 | [-0.0332, +0.0154] | 78 | tuttu | evet |
| `ceiling_path_v0` | D3 | Brier | sıfır model | −0.025 … 0.000 | içerir | -0.0349 | [-0.0536, -0.0161] | 87 | daha iyi | hayır |
| `ceiling_path_v0` | D5 | MAE | `base_train_median` **(BİRİNCİL)** | −0.090 … −0.020 | dışlaması olası, garanti değil | -0.1158 | [-0.1611, -0.0738] | 85 | **daha iyi** | evet |
| `ceiling_path_v0` | D5 | MAE | `base_always_ceiling` | −0.110 … −0.040 | dışlaması olası | -0.1379 | [-0.2085, -0.0683] | 85 | daha iyi | evet |
| `ceiling_path_v0` | D5 | MAE | `v1_5_h99` | −0.020 … +0.050 | içerir | -0.0360 | [-0.0579, -0.0176] | 85 | daha iyi | hayır |
| `ceiling_path_v0` | D5 | MAE | sıfır model | −0.050 … −0.005 | içerir | -0.1033 | [-0.1462, -0.0628] | 87 | daha iyi | hayır |
| `ceiling_path_v0` | D5 | Brier | `base_rate` | −0.030 … 0.000 | içerir | -0.0452 | [-0.0704, -0.0168] | 85 | daha iyi | hayır |
| `ceiling_path_v0` | D5 | Brier | `base_last10_rate` | −0.035 … −0.005 | içerir | -0.0539 | [-0.0819, -0.0197] | 85 | daha iyi | hayır |
| `ceiling_path_v0` | D5 | Brier | `v1_5_h99` | 0.000 … +0.040 | içerir | -0.0166 | [-0.0414, +0.0052] | 79 | daha iyi | evet |
| `ceiling_path_v0` | D5 | Brier | sıfır model | −0.020 … +0.005 | içerir | -0.0407 | [-0.0631, -0.0159] | 87 | daha iyi | hayır |
| `ceiling_path_v0` | D10 | MAE | `base_train_median` | −0.100 … −0.010 | büyük olasılıkla içerir | -0.1746 | [-0.2756, -0.0709] | 85 | daha iyi | hayır |
| `ceiling_path_v0` | D10 | MAE | `base_always_ceiling` | −0.750 … −0.550 | dışlar (negatif) | -0.7888 | [-1.0102, -0.5617] | 85 | daha iyi | evet |
| `ceiling_path_v0` | D10 | MAE | `v1_5_h99` | −0.020 … +0.100 | içerir | -0.0595 | [-0.1447, +0.0157] | 85 | daha iyi | evet |
| `ceiling_path_v0` | D10 | MAE | sıfır model | −0.050 … +0.010 | içerir | -0.1327 | [-0.2152, -0.0538] | 87 | daha iyi | hayır |
| `ceiling_path_v0` | D10 | Brier | `base_rate` | −0.020 … +0.010 | içerir | -0.0667 | [-0.1070, -0.0298] | 85 | daha iyi | hayır |
| `ceiling_path_v0` | D10 | Brier | `base_last10_rate` | −0.070 … −0.020 | dışlayabilir | -0.1165 | [-0.1702, -0.0645] | 85 | daha iyi | evet |
| `ceiling_path_v0` | D10 | Brier | `v1_5_h99` | +0.010 … +0.060 | içerir ya da pozitif dışlar | -0.0311 | [-0.0695, +0.0032] | 79 | daha iyi | evet |
| `ceiling_path_v0` | D10 | Brier | sıfır model | −0.010 … +0.005 | içerir | -0.0522 | [-0.0830, -0.0241] | 87 | daha iyi | hayır |
| `ceiling_path_v0@INF` | D5 | MAE | `base_train_median` | −0.040 … +0.010 | içerir | -0.0101 | [-0.0221, -0.0026] | 85 | tutmadı | hayır |
| `ceiling_path_v0@INF` | D10 | MAE | `base_train_median` | −0.060 … +0.020 | içerir | -0.0366 | [-0.0887, +0.0048] | 85 | tuttu | evet |
| `pb_ceiling_path_v0` | D5 | MAE | `pb_v0` | −0.040 … +0.030 | içerir | -0.0124 | [-0.0391, +0.0162] | 87 | tuttu | evet |
| `pb_ceiling_path_v0` | D5 | MAE | `ceiling_path_v0` | +0.000 … +0.050 | içerir ya da pozitif dışlar | +0.0728 | [+0.0421, +0.1088] | 85 | daha kötü | evet |

Etiket sayıları: tuttu 10, tutmadı 3, daha iyi 22, daha kötü 1 (toplam 36).

D1 beraberlik cümlesi ("fold'ların ≥ 80/87'sinde fark bit-eşit 0 ya da |fark| < 0.001"): 87 eşleşik fold'un 52'inde fark bit-eşit 0, 84'inde bit-eşit 0 ya da |fark| < 0.001 → **tuttu**.

### Başarısızlık tanımları (§6)

- **(a) Yalnız mekanik** (ana − sıfır model, {D3, D5, D10} × {MAE, Brier}; altısının hepsinde aralık 0'ı içeriyor VE noktasal fark ≥ −0.005): D3 MAE -0.0188 [-0.0397, -0.0044]; D3 Brier -0.0349 [-0.0536, -0.0161]; D5 MAE -0.1033 [-0.1462, -0.0628]; D5 Brier -0.0407 [-0.0631, -0.0159]; D10 MAE -0.1327 [-0.2152, -0.0538]; D10 Brier -0.0522 [-0.0830, -0.0241] → gerçekleşmedi.
- **(b) Mekanik eşleme katmıyor** (sıfır model − `base_train_median`, D5 VE D10 MAE aralığı tamamen 0'ın üstünde): D5 -0.0101 [-0.0221, -0.0026]; D10 -0.0366 [-0.0887, +0.0048] → gerçekleşmedi.
- **(c) Eşleme hatası** (ana − `base_always_ceiling` D1 MAE aralığı tamamen 0'ın üstünde): +0.0002 [-0.0002, +0.0010] → gerçekleşmedi.
- **(d) Kalibrasyon** (|ortalama p_up_3 − gözlenen Y_3 oranı| > 0.15): ort. p_up_3 0.8307, gözlenen 0.8046, |fark| 0.0261, n = 87 → gerçekleşmedi.
- (e) Prospektif (n ≥ 30): birincil hücre aralığı 0'ı pozitif tarafta dışlıyor → "geçemiyor". Canlı n = 0; hüküm yok.

### `ceiling_path_v0`: bütün hücreler (§5; birincil dışındakiler keşif)

| Ufuk | Çıktı | Karşılaştırılan | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| D1 | MAE | `base_always_ceiling` | 87 (24) | 0.0225 | 0.0223 | +0.0002 | [-0.0002, +0.0010] | 33 / 2 / 52 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | MAE | `base_train_median` | 87 (24) | 0.0225 | 0.0223 | +0.0002 | [-0.0002, +0.0010] | 53 / 5 / 29 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | MAE | `v1_5_h99` | 87 (24) | 0.0225 | 0.0284 | -0.0058 | [-0.0087, -0.0025] | 71 / 16 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D1 | MAE | `ceiling_path_v0@INF` | 87 (24) | 0.0225 | 0.0222 | +0.0004 | [+0.0000, +0.0012] | 0 / 1 / 86 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | Brier | `base_rate` | 87 (24) | 0.0759 | 0.0855 | -0.0097 | [-0.0176, -0.0008] | 40 / 47 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D1 | Brier | `base_last10_rate` | 87 (24) | 0.0759 | 0.0926 | -0.0167 | [-0.0264, -0.0079] | 40 / 47 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D1 | Brier | `v1_5_h99` | 78 (22) | 0.0741 | 0.0860 | -0.0118 | [-0.0226, -0.0016] | 39 / 39 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D1 | Brier | `ceiling_path_v0@INF` | 87 (24) | 0.0759 | 0.0843 | -0.0084 | [-0.0157, -0.0006] | 50 / 37 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | MAE | `base_always_ceiling` | 86 (24) | 0.1091 | 0.1290 | -0.0200 | [-0.0411, -0.0054] | 79 / 4 / 3 | **model geçiyor** (aralık 0'ın altında) |
| D3 | MAE | `base_train_median` | 86 (24) | 0.1091 | 0.1284 | -0.0194 | [-0.0404, -0.0049] | 68 / 18 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | MAE | `v1_5_h99` | 86 (24) | 0.1091 | 0.1177 | -0.0087 | [-0.0301, +0.0131] | 58 / 28 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | MAE | `ceiling_path_v0@INF` | 87 (24) | 0.1078 | 0.1266 | -0.0188 | [-0.0397, -0.0044] | 11 / 4 / 72 | **model geçiyor** (aralık 0'ın altında) |
| D3 | Brier | `base_rate` | 86 (24) | 0.1315 | 0.1677 | -0.0362 | [-0.0553, -0.0163] | 54 / 32 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | Brier | `base_last10_rate` | 86 (24) | 0.1315 | 0.1701 | -0.0386 | [-0.0628, -0.0113] | 46 / 40 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | Brier | `v1_5_h99` | 78 (23) | 0.1337 | 0.1422 | -0.0085 | [-0.0332, +0.0154] | 25 / 53 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | Brier | `ceiling_path_v0@INF` | 87 (24) | 0.1300 | 0.1649 | -0.0349 | [-0.0536, -0.0161] | 57 / 30 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | MAE | `base_always_ceiling` | 85 (23) | 0.1842 | 0.3221 | -0.1379 | [-0.2085, -0.0683] | 74 / 11 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | MAE | `base_train_median` **(BİRİNCİL)** | 85 (23) | 0.1842 | 0.3000 | -0.1158 | [-0.1611, -0.0738] | 63 / 22 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | MAE | `v1_5_h99` | 85 (23) | 0.1842 | 0.2202 | -0.0360 | [-0.0579, -0.0176] | 58 / 27 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | MAE | `ceiling_path_v0@INF` | 87 (24) | 0.1800 | 0.2832 | -0.1033 | [-0.1462, -0.0628] | 47 / 17 / 23 | **model geçiyor** (aralık 0'ın altında) |
| D5 | Brier | `base_rate` | 85 (23) | 0.1495 | 0.1947 | -0.0452 | [-0.0704, -0.0168] | 57 / 28 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | Brier | `base_last10_rate` | 85 (23) | 0.1495 | 0.2034 | -0.0539 | [-0.0819, -0.0197] | 49 / 36 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | Brier | `v1_5_h99` | 79 (23) | 0.1389 | 0.1555 | -0.0166 | [-0.0414, +0.0052] | 32 / 47 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | Brier | `ceiling_path_v0@INF` | 87 (24) | 0.1462 | 0.1869 | -0.0407 | [-0.0631, -0.0159] | 59 / 28 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | MAE | `base_always_ceiling` | 85 (23) | 0.3921 | 1.1809 | -0.7888 | [-1.0102, -0.5617] | 73 / 12 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | MAE | `base_train_median` | 85 (23) | 0.3921 | 0.5668 | -0.1746 | [-0.2756, -0.0709] | 55 / 30 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | MAE | `v1_5_h99` | 85 (23) | 0.3921 | 0.4517 | -0.0595 | [-0.1447, +0.0157] | 49 / 36 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | MAE | `ceiling_path_v0@INF` | 87 (24) | 0.4095 | 0.5422 | -0.1327 | [-0.2152, -0.0538] | 54 / 33 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | Brier | `base_rate` | 85 (23) | 0.1841 | 0.2508 | -0.0667 | [-0.1070, -0.0298] | 60 / 25 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | Brier | `base_last10_rate` | 85 (23) | 0.1841 | 0.3006 | -0.1165 | [-0.1702, -0.0645] | 53 / 32 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | Brier | `v1_5_h99` | 79 (23) | 0.1555 | 0.1866 | -0.0311 | [-0.0695, +0.0032] | 47 / 32 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | Brier | `ceiling_path_v0@INF` | 87 (24) | 0.1801 | 0.2323 | -0.0522 | [-0.0830, -0.0241] | 60 / 27 / 0 | **model geçiyor** (aralık 0'ın altında) |

D10 dipnotu: bu ufuktaki kazanç **L = 10 arzlarında yoğunlaşıyor** (bağımsız denetim, `docs/fable_faz4_audit/AUDIT.md` §6-6: 2023'ün yedi fold'unda fark −0.48'e kadar iniyor; dört L = 10 arzı toplam farkın yaklaşık üçte birini veriyor). D10 keşif hücresidir, hüküm bundan etkilenmez.

Kendi skorlanabilir kümesinde (h = 2, 4, 6..9 yalnız bilgi; gerçekleşen R_h SESSIONS kapanışlarından):

| Ufuk | n | MAE | Medyan AE | Brier | ort. p_up | gözlenen Y oranı | yön isabeti | hep-yukarı isabeti | not |
|---|---|---|---|---|---|---|---|---|---|
| D1 | 87 | 0.0225 | 0.0000 | 0.0759 | 0.9177 | 0.9080 | 0.9080 | 0.9080 |  |
| D2 | 87 | 0.0594 | 0.0000 | 0.1309 | 0.8521 | 0.8161 | 0.8161 | 0.8161 | yalnız bilgi; kural yok |
| D3 | 87 | 0.1078 | 0.0000 | 0.1300 | 0.8307 | 0.8046 | 0.7931 | 0.8046 |  |
| D4 | 87 | 0.1350 | 0.0095 | 0.1516 | 0.7996 | 0.7586 | 0.7701 | 0.7586 | yalnız bilgi; kural yok |
| D5 | 87 | 0.1800 | 0.1233 | 0.1462 | 0.7916 | 0.7701 | 0.7701 | 0.7701 |  |
| D6 | 87 | 0.2366 | 0.2108 | 0.1595 | 0.7529 | 0.7356 | 0.7586 | 0.7356 | yalnız bilgi; kural yok |
| D7 | 87 | 0.2917 | 0.2834 | 0.1519 | 0.7581 | 0.7701 | 0.7701 | 0.7701 | yalnız bilgi; kural yok |
| D8 | 87 | 0.3393 | 0.2800 | 0.1868 | 0.7222 | 0.6897 | 0.7241 | 0.6897 | yalnız bilgi; kural yok |
| D9 | 87 | 0.3720 | 0.2986 | 0.1778 | 0.7131 | 0.6667 | 0.7816 | 0.6667 | yalnız bilgi; kural yok |
| D10 | 87 | 0.4095 | 0.3122 | 0.1801 | 0.7152 | 0.6897 | 0.7701 | 0.6897 |  |

87 fold (kaynak ledger'ınkiyle aynı küme ve sıra); fold durumları: OK 87. İlk fold EKOS (kesim 2023-11-21): Z = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], B = [6, 6, 5, 4, 3, 2, 0, 0, 0]. Havuzlanmış hücre kullanan (fold, ufuk): 513/870. Hücrede kesim ve sonrası tarihli seans olan fold: 0.

### `ceiling_path_v0@INF` (sıfır model, MECHANICS_BASE)

| Ufuk | Çıktı | Karşılaştırılan | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| D1 | MAE | `base_train_median` | 87 (24) | 0.0222 | 0.0223 | -0.0002 | [-0.0002, -0.0001] | 54 / 4 / 29 | **model geçiyor** (aralık 0'ın altında) |
| D1 | MAE | `base_always_ceiling` | 87 (24) | 0.0222 | 0.0223 | -0.0002 | [-0.0002, -0.0001] | 34 / 1 / 52 | **model geçiyor** (aralık 0'ın altında) |
| D1 | Brier | `base_rate` | 87 (24) | 0.0843 | 0.0855 | -0.0012 | [-0.0050, +0.0019] | 35 / 52 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | Brier | `base_last10_rate` | 87 (24) | 0.0843 | 0.0926 | -0.0083 | [-0.0180, -0.0009] | 44 / 43 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | MAE | `base_train_median` | 86 (24) | 0.1281 | 0.1284 | -0.0003 | [-0.0004, -0.0002] | 66 / 20 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | MAE | `base_always_ceiling` | 86 (24) | 0.1281 | 0.1290 | -0.0009 | [-0.0011, -0.0008] | 83 / 0 / 3 | **model geçiyor** (aralık 0'ın altında) |
| D3 | Brier | `base_rate` | 86 (24) | 0.1668 | 0.1677 | -0.0009 | [-0.0040, +0.0023] | 55 / 31 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | Brier | `base_last10_rate` | 86 (24) | 0.1668 | 0.1701 | -0.0033 | [-0.0205, +0.0196] | 50 / 36 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | MAE | `base_train_median` | 85 (23) | 0.2899 | 0.3000 | -0.0101 | [-0.0221, -0.0026] | 58 / 27 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | MAE | `base_always_ceiling` | 85 (23) | 0.2899 | 0.3221 | -0.0322 | [-0.0811, +0.0203] | 68 / 17 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | Brier | `base_rate` | 85 (23) | 0.1912 | 0.1947 | -0.0035 | [-0.0099, +0.0010] | 40 / 45 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | Brier | `base_last10_rate` | 85 (23) | 0.1912 | 0.2034 | -0.0122 | [-0.0323, +0.0152] | 46 / 39 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | MAE | `base_train_median` | 85 (23) | 0.5302 | 0.5668 | -0.0366 | [-0.0887, +0.0048] | 55 / 30 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | MAE | `base_always_ceiling` | 85 (23) | 0.5302 | 1.1809 | -0.6508 | [-0.8737, -0.4163] | 64 / 21 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | Brier | `base_rate` | 85 (23) | 0.2376 | 0.2508 | -0.0133 | [-0.0305, +0.0021] | 56 / 29 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | Brier | `base_last10_rate` | 85 (23) | 0.2376 | 0.3006 | -0.0630 | [-0.1022, -0.0240] | 47 / 38 / 0 | **model geçiyor** (aralık 0'ın altında) |

D10 dipnotu: bu ufuktaki kazanç **L = 10 arzlarında yoğunlaşıyor** (bağımsız denetim, `docs/fable_faz4_audit/AUDIT.md` §6-6: 2023'ün yedi fold'unda fark −0.48'e kadar iniyor; dört L = 10 arzı toplam farkın yaklaşık üçte birini veriyor). D10 keşif hücresidir, hüküm bundan etkilenmez.

| Ufuk | n | MAE | Medyan AE | Brier | ort. p_up | gözlenen Y oranı | yön isabeti | hep-yukarı isabeti | not |
|---|---|---|---|---|---|---|---|---|---|
| D1 | 87 | 0.0222 | 0.0000 | 0.0843 | 0.9260 | 0.9080 | 0.9080 | 0.9080 |  |
| D2 | 87 | 0.0687 | 0.0000 | 0.1593 | 0.8739 | 0.8161 | 0.8161 | 0.8161 | yalnız bilgi; kural yok |
| D3 | 87 | 0.1266 | 0.0000 | 0.1649 | 0.8569 | 0.8046 | 0.8046 | 0.8046 |  |
| D4 | 87 | 0.2142 | 0.0320 | 0.1944 | 0.8299 | 0.7586 | 0.7586 | 0.7586 | yalnız bilgi; kural yok |
| D5 | 87 | 0.2832 | 0.2596 | 0.1869 | 0.8238 | 0.7701 | 0.7701 | 0.7701 |  |
| D6 | 87 | 0.3505 | 0.3217 | 0.2055 | 0.7923 | 0.7356 | 0.7356 | 0.7356 | yalnız bilgi; kural yok |
| D7 | 87 | 0.4218 | 0.3717 | 0.1865 | 0.7974 | 0.7701 | 0.7701 | 0.7701 | yalnız bilgi; kural yok |
| D8 | 87 | 0.4721 | 0.4510 | 0.2387 | 0.7644 | 0.6897 | 0.6897 | 0.6897 | yalnız bilgi; kural yok |
| D9 | 87 | 0.5105 | 0.4998 | 0.2458 | 0.7553 | 0.6667 | 0.6667 | 0.6667 | yalnız bilgi; kural yok |
| D10 | 87 | 0.5422 | 0.4754 | 0.2323 | 0.7579 | 0.6897 | 0.6897 | 0.6897 |  |

### `pb_ceiling_path_v0` (PB varyantı; kesim B(k))

| Ufuk | Çıktı | Karşılaştırılan | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| D1 | MAE | `pb_v0` | 87 (23) | 0.0255 | 0.0340 | -0.0085 | [-0.0126, -0.0049] | 69 / 18 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D1 | MAE | `base_train_median` | 87 (23) | 0.0255 | 0.0257 | -0.0002 | [-0.0002, -0.0001] | 52 / 4 / 31 | **model geçiyor** (aralık 0'ın altında) |
| D1 | MAE | `base_always_ceiling` | 87 (23) | 0.0255 | 0.0257 | -0.0002 | [-0.0002, -0.0001] | 33 / 1 / 53 | **model geçiyor** (aralık 0'ın altında) |
| D1 | Brier | `pb_v0` | 80 (22) | 0.0963 | 0.1000 | -0.0037 | [-0.0088, +0.0012] | 31 / 49 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | Brier | `base_rate` | 87 (23) | 0.0982 | 0.1055 | -0.0073 | [-0.0144, +0.0004] | 32 / 55 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | Brier | `base_last10_rate` | 87 (23) | 0.0982 | 0.1113 | -0.0131 | [-0.0205, -0.0058] | 40 / 47 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | MAE | `pb_v0` | 87 (23) | 0.1275 | 0.1444 | -0.0169 | [-0.0474, +0.0137] | 58 / 29 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | MAE | `base_train_median` | 87 (23) | 0.1275 | 0.1373 | -0.0098 | [-0.0190, -0.0011] | 68 / 19 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | MAE | `base_always_ceiling` | 87 (23) | 0.1275 | 0.1379 | -0.0104 | [-0.0198, -0.0016] | 82 / 2 / 3 | **model geçiyor** (aralık 0'ın altında) |
| D3 | Brier | `pb_v0` | 80 (22) | 0.1579 | 0.1625 | -0.0046 | [-0.0158, +0.0048] | 29 / 51 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | Brier | `base_rate` | 87 (23) | 0.1642 | 0.1837 | -0.0195 | [-0.0322, -0.0059] | 50 / 37 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D3 | Brier | `base_last10_rate` | 87 (23) | 0.1642 | 0.1868 | -0.0226 | [-0.0421, +0.0034] | 43 / 44 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | MAE | `pb_v0` | 87 (23) | 0.2627 | 0.2751 | -0.0124 | [-0.0391, +0.0162] | 52 / 35 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | MAE | `base_train_median` | 87 (23) | 0.2627 | 0.3106 | -0.0479 | [-0.0838, -0.0113] | 54 / 33 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | MAE | `base_always_ceiling` | 87 (23) | 0.2627 | 0.3332 | -0.0705 | [-0.1287, -0.0049] | 66 / 21 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | Brier | `pb_v0` | 80 (22) | 0.1692 | 0.1741 | -0.0049 | [-0.0161, +0.0055] | 35 / 45 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | Brier | `base_rate` | 87 (23) | 0.1836 | 0.2078 | -0.0241 | [-0.0408, -0.0058] | 47 / 40 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | Brier | `base_last10_rate` | 87 (23) | 0.1836 | 0.2199 | -0.0363 | [-0.0643, -0.0027] | 49 / 38 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | MAE | `pb_v0` | 84 (23) | 0.4775 | 0.5178 | -0.0403 | [-0.1126, +0.0308] | 48 / 36 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | MAE | `base_train_median` | 84 (23) | 0.4775 | 0.5656 | -0.0881 | [-0.1543, -0.0303] | 56 / 28 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | MAE | `base_always_ceiling` | 84 (23) | 0.4775 | 1.1810 | -0.7035 | [-0.9290, -0.4537] | 64 / 20 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | Brier | `pb_v0` | 80 (22) | 0.1959 | 0.2072 | -0.0112 | [-0.0401, +0.0116] | 52 / 28 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | Brier | `base_rate` | 84 (23) | 0.2147 | 0.2463 | -0.0316 | [-0.0589, -0.0078] | 57 / 27 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | Brier | `base_last10_rate` | 84 (23) | 0.2147 | 0.3116 | -0.0969 | [-0.1440, -0.0548] | 49 / 35 / 0 | **model geçiyor** (aralık 0'ın altında) |

D10 dipnotu: bu ufuktaki kazanç **L = 10 arzlarında yoğunlaşıyor** (bağımsız denetim, `docs/fable_faz4_audit/AUDIT.md` §6-6: 2023'ün yedi fold'unda fark −0.48'e kadar iniyor; dört L = 10 arzı toplam farkın yaklaşık üçte birini veriyor). D10 keşif hücresidir, hüküm bundan etkilenmez.

Kurallar PB planının kendi koşularıdır (`…__pb`). Bilgi amaçlı (kesimleri farklı: B(k) ve T(k)), aynı test arzları:

| Ufuk | Çıktı | Karşılaştırılan | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|---|
| D1 | MAE | `ceiling_path_v0` | 85 (23) | 0.0227 | 0.0231 | -0.0004 | [-0.0012, +0.0000] | 1 / 0 / 84 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | MAE | `ceiling_path_v0@INF` | 85 (23) | 0.0227 | 0.0227 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 85 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D1 | Brier | `ceiling_path_v0` | 85 (23) | 0.0810 | 0.0776 | +0.0034 | [+0.0005, +0.0061] | 30 / 55 / 0 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D1 | Brier | `ceiling_path_v0@INF` | 85 (23) | 0.0810 | 0.0863 | -0.0052 | [-0.0117, +0.0013] | 42 / 43 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | MAE | `ceiling_path_v0` | 85 (23) | 0.1199 | 0.1103 | +0.0096 | [-0.0051, +0.0316] | 5 / 12 / 68 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | MAE | `ceiling_path_v0@INF` | 85 (23) | 0.1199 | 0.1296 | -0.0097 | [-0.0197, -0.0007] | 8 / 2 / 75 | **model geçiyor** (aralık 0'ın altında) |
| D3 | Brier | `ceiling_path_v0` | 85 (23) | 0.1532 | 0.1330 | +0.0202 | [+0.0067, +0.0337] | 28 / 57 / 0 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D3 | Brier | `ceiling_path_v0@INF` | 85 (23) | 0.1532 | 0.1687 | -0.0155 | [-0.0259, -0.0047] | 48 / 37 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D5 | MAE | `ceiling_path_v0` | 85 (23) | 0.2570 | 0.1842 | +0.0728 | [+0.0421, +0.1088] | 17 / 48 / 20 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D5 | MAE | `ceiling_path_v0@INF` | 85 (23) | 0.2570 | 0.2899 | -0.0329 | [-0.0692, +0.0051] | 36 / 25 / 24 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | Brier | `ceiling_path_v0` | 85 (23) | 0.1745 | 0.1495 | +0.0250 | [+0.0068, +0.0430] | 28 / 57 / 0 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D5 | Brier | `ceiling_path_v0@INF` | 85 (23) | 0.1745 | 0.1912 | -0.0167 | [-0.0302, -0.0029] | 50 / 35 / 0 | **model geçiyor** (aralık 0'ın altında) |
| D10 | MAE | `ceiling_path_v0` | 85 (23) | 0.4889 | 0.3921 | +0.0968 | [+0.0064, +0.1923] | 31 / 51 / 3 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D10 | MAE | `ceiling_path_v0@INF` | 85 (23) | 0.4889 | 0.5302 | -0.0413 | [-0.0711, -0.0078] | 48 / 36 / 1 | **model geçiyor** (aralık 0'ın altında) |
| D10 | Brier | `ceiling_path_v0` | 85 (23) | 0.2208 | 0.1841 | +0.0367 | [+0.0135, +0.0599] | 30 / 55 / 0 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D10 | Brier | `ceiling_path_v0@INF` | 85 (23) | 0.2208 | 0.2376 | -0.0168 | [-0.0335, +0.0000] | 50 / 35 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |

| Ufuk | n | MAE | Medyan AE | Brier | ort. p_up | gözlenen Y oranı | yön isabeti | hep-yukarı isabeti | not |
|---|---|---|---|---|---|---|---|---|---|
| D1 | 87 | 0.0255 | 0.0000 | 0.0982 | 0.9141 | 0.8851 | 0.8851 | 0.8851 |  |
| D2 | 87 | 0.0763 | 0.0000 | 0.1624 | 0.8518 | 0.7931 | 0.7931 | 0.7931 | yalnız bilgi; kural yok |
| D3 | 87 | 0.1275 | 0.0000 | 0.1642 | 0.8315 | 0.7816 | 0.7816 | 0.7816 |  |
| D4 | 87 | 0.1931 | 0.1790 | 0.1910 | 0.8006 | 0.7356 | 0.7356 | 0.7356 | yalnız bilgi; kural yok |
| D5 | 87 | 0.2627 | 0.2570 | 0.1836 | 0.7937 | 0.7471 | 0.7471 | 0.7471 |  |
| D6 | 87 | 0.3119 | 0.2979 | 0.2001 | 0.7564 | 0.7126 | 0.7126 | 0.7126 | yalnız bilgi; kural yok |
| D7 | 87 | 0.3650 | 0.3250 | 0.1852 | 0.7631 | 0.7471 | 0.7471 | 0.7471 | yalnız bilgi; kural yok |
| D8 | 87 | 0.4178 | 0.3575 | 0.2338 | 0.7253 | 0.6667 | 0.6667 | 0.6667 | yalnız bilgi; kural yok |
| D9 | 87 | 0.4582 | 0.3392 | 0.2369 | 0.7143 | 0.6437 | 0.6437 | 0.6437 | yalnız bilgi; kural yok |
| D10 | 87 | 0.4861 | 0.3479 | 0.2267 | 0.7171 | 0.6667 | 0.6667 | 0.6667 |  |

87 fold (kaynak ledger'ınkiyle aynı küme ve sıra); fold durumları: OK 87. İlk fold SKYMD (kesim 2023-11-30): Z = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], B = [6, 6, 5, 5, 3, 2, 0, 0, 0]. Havuzlanmış hücre kullanan (fold, ufuk): 516/870. Hücrede kesim ve sonrası tarihli seans olan fold: 0.

### Koşullu güncelleme (keşif): H99, j = 1..9

SPEC_CEILING_PATH_V0 §7: seri j. günde sürüyorken koşullu RPS_j = (1/(10 − j)) Σ_{k>j} (S_k/S_j − 1[L ≥ k])² ve koşullu Brier (k = j + 1 "yarın", k = 10 "sonuna kadar"); Faz 1B tavan ledger'larından (yeni model değil). **Keşif, tasarıma maruz; koşulsuz tablolarla toplanmaz, farklı j'ler birleştirilmez** (aynı arz birden çok j'de bulunur). Aralık n ≥ 10 ise.

`ceiling_hazard_v0` (koşu `ceiling_hazard_v0`); fark = model − kural, aynı fold'lar, L ≥ j olan arzlar:

| j | n | model RPS_j | − `ceiling_hazard_v0@INF` [%95] | − `base_km_expanding` [%95] | − `base_km_last10` [%95] | − `base_always_ceiling__ceiling` [%95] |
|---|---|---|---|---|---|---|
| 1 | 71 | 0.1706 | -0.0301 [-0.0592, -0.0004] | -0.0362 [-0.0687, -0.0031] | -0.0408 [-0.0735, -0.0073] | -0.3912 [-0.4904, -0.2744] |
| 2 | 60 | 0.1834 | -0.0094 [-0.0375, +0.0183] | -0.0202 [-0.0542, +0.0122] | -0.0185 [-0.0519, +0.0128] | -0.3582 [-0.4641, -0.2464] |
| 3 | 56 | 0.2155 | -0.0026 [-0.0361, +0.0311] | -0.0076 [-0.0427, +0.0270] | -0.0069 [-0.0490, +0.0326] | -0.3661 [-0.4900, -0.2365] |
| 4 | 43 | 0.2468 | +0.0171 [-0.0277, +0.0608] | +0.0146 [-0.0287, +0.0553] | -0.0022 [-0.0538, +0.0427] | -0.2842 [-0.4110, -0.1558] |
| 5 | 33 | 0.2284 | +0.0010 [-0.0540, +0.0490] | -0.0036 [-0.0557, +0.0422] | -0.0032 [-0.0612, +0.0475] | -0.2382 [-0.3649, -0.1280] |
| 6 | 26 | 0.2420 | +0.0208 [-0.0381, +0.0828] | +0.0136 [-0.0436, +0.0768] | +0.0080 [-0.0526, +0.0740] | -0.1618 [-0.2699, -0.0536] |
| 7 | 22 | 0.2659 | +0.0272 [-0.0321, +0.0921] | +0.0173 [-0.0495, +0.0872] | +0.0143 [-0.0573, +0.0942] | -0.1280 [-0.2258, -0.0191] |
| 8 | 16 | 0.1949 | +0.0173 [-0.0273, +0.0755] | +0.0049 [-0.0271, +0.0440] | -0.0049 [-0.0320, +0.0273] | -0.0551 [-0.1259, +0.0229] |
| 9 | 13 | 0.1295 | -0.0102 [-0.0467, +0.0316] | -0.0019 [-0.0413, +0.0513] | -0.0045 [-0.0460, +0.0538] | -0.0243 [-0.0917, +0.0402] |

| j | n | model Brier k = j+1 | − `ceiling_hazard_v0@INF` | − `base_km_expanding` | − `base_km_last10` | − `base_always_ceiling__ceiling` | model Brier k = 10 | − `ceiling_hazard_v0@INF` | − `base_km_expanding` | − `base_km_last10` | − `base_always_ceiling__ceiling` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 71 | 0.1277 | -0.0138 [-0.0303, -0.0005] | -0.0128 [-0.0237, -0.0023] | -0.0399 [-0.0607, -0.0203] | -0.0272 [-0.0545, -0.0037] | 0.1370 | -0.0043 [-0.0507, +0.0455] | -0.0034 [-0.0504, +0.0470] | -0.0023 [-0.0556, +0.0524] | -0.7080 [-0.8343, -0.5520] |
| 2 | 60 | 0.0557 | -0.0054 [-0.0195, +0.0078] | -0.0083 [-0.0322, +0.0106] | -0.0123 [-0.0357, +0.0079] | -0.0109 [-0.0368, +0.0092] | 0.1638 | +0.0067 [-0.0471, +0.0592] | +0.0050 [-0.0477, +0.0574] | +0.0045 [-0.0556, +0.0641] | -0.6529 [-0.7917, -0.4895] |
| 3 | 56 | 0.1739 | -0.0066 [-0.0305, +0.0179] | -0.0170 [-0.0553, +0.0161] | -0.0057 [-0.0553, +0.0468] | -0.0582 [-0.1098, -0.0117] | 0.1791 | +0.0097 [-0.0495, +0.0669] | +0.0121 [-0.0466, +0.0684] | +0.0099 [-0.0590, +0.0760] | -0.6244 [-0.7719, -0.4444] |
| 4 | 43 | 0.2053 | +0.0209 [+0.0016, +0.0406] | +0.0152 [-0.0085, +0.0381] | -0.0077 [-0.0432, +0.0256] | -0.0272 [-0.0742, +0.0141] | 0.2325 | +0.0279 [-0.0460, +0.1005] | +0.0335 [-0.0407, +0.1032] | +0.0229 [-0.0588, +0.0991] | -0.5116 [-0.6727, -0.3265] |
| 5 | 33 | 0.1508 | -0.0190 [-0.0766, +0.0170] | -0.0241 [-0.0828, +0.0136] | -0.0216 [-0.0712, +0.0162] | -0.0613 [-0.1608, +0.0079] | 0.2528 | +0.0203 [-0.0654, +0.0994] | +0.0252 [-0.0578, +0.1039] | +0.0247 [-0.0675, +0.1099] | -0.4139 [-0.5802, -0.2349] |
| 6 | 26 | 0.1261 | -0.0059 [-0.0449, +0.0256] | -0.0204 [-0.0575, +0.0174] | -0.0264 [-0.0677, +0.0149] | -0.0277 [-0.0960, +0.0226] | 0.2888 | +0.0357 [-0.0603, +0.1311] | +0.0396 [-0.0543, +0.1339] | +0.0326 [-0.0655, +0.1298] | -0.2882 [-0.4633, -0.0969] |
| 7 | 22 | 0.2201 | +0.0074 [-0.0304, +0.0492] | -0.0057 [-0.0526, +0.0481] | -0.0178 [-0.0745, +0.0549] | -0.0526 [-0.1084, +0.0023] | 0.2939 | +0.0346 [-0.0563, +0.1288] | +0.0362 [-0.0691, +0.1391] | +0.0299 [-0.0779, +0.1382] | -0.2061 [-0.3667, -0.0205] |
| 8 | 16 | 0.1627 | +0.0206 [-0.0058, +0.0588] | -0.0021 [-0.0190, +0.0146] | -0.0090 [-0.0348, +0.0117] | -0.0248 [-0.0854, +0.0247] | 0.2270 | +0.0140 [-0.0570, +0.0983] | +0.0119 [-0.0510, +0.0834] | -0.0008 [-0.0578, +0.0598] | -0.0855 [-0.1891, +0.0353] |
| 9 | 13 | 0.1295 | -0.0102 [-0.0467, +0.0316] | -0.0019 [-0.0413, +0.0513] | -0.0045 [-0.0460, +0.0538] | -0.0243 [-0.0917, +0.0402] | 0.1295 | -0.0102 [-0.0467, +0.0316] | -0.0019 [-0.0413, +0.0513] | -0.0045 [-0.0460, +0.0538] | -0.0243 [-0.0917, +0.0402] |

`pb_ceiling_v0` (koşu `pb_ceiling_v0`); fark = model − kural, aynı fold'lar, L ≥ j olan arzlar:

| j | n | model RPS_j | − `pb_ceiling_v0@INF` [%95] | − `base_km_expanding__pb_ceiling` [%95] | − `base_km_last10__pb_ceiling` [%95] | − `base_always_ceiling__pb_ceiling` [%95] |
|---|---|---|---|---|---|---|
| 1 | 69 | 0.1915 | -0.0109 [-0.0263, +0.0050] | -0.0184 [-0.0389, +0.0020] | -0.0278 [-0.0542, +0.0015] | -0.3866 [-0.4741, -0.2894] |
| 2 | 58 | 0.1914 | -0.0017 [-0.0161, +0.0111] | -0.0131 [-0.0305, +0.0028] | -0.0170 [-0.0435, +0.0096] | -0.3689 [-0.4660, -0.2685] |
| 3 | 54 | 0.2216 | +0.0029 [-0.0099, +0.0163] | -0.0021 [-0.0155, +0.0115] | -0.0053 [-0.0352, +0.0274] | -0.3816 [-0.4906, -0.2685] |
| 4 | 41 | 0.2228 | -0.0084 [-0.0300, +0.0157] | -0.0064 [-0.0288, +0.0212] | -0.0182 [-0.0517, +0.0154] | -0.3342 [-0.4565, -0.2076] |
| 5 | 31 | 0.2289 | -0.0025 [-0.0333, +0.0302] | -0.0029 [-0.0335, +0.0325] | -0.0033 [-0.0357, +0.0345] | -0.2679 [-0.3830, -0.1673] |
| 6 | 24 | 0.2526 | +0.0228 [+0.0024, +0.0559] | +0.0229 [-0.0056, +0.0692] | +0.0177 [-0.0104, +0.0635] | -0.1849 [-0.2683, -0.0967] |
| 7 | 20 | 0.2775 | +0.0220 [-0.0129, +0.0730] | +0.0077 [-0.0354, +0.0682] | +0.0029 [-0.0431, +0.0663] | -0.1558 [-0.2442, -0.0596] |
| 8 | 14 | 0.2086 | +0.0117 [-0.0247, +0.0612] | -0.0077 [-0.0611, +0.0486] | -0.0238 [-0.0992, +0.0492] | -0.0771 [-0.1809, +0.0194] |
| 9 | 11 | 0.1470 | -0.0124 [-0.0424, +0.0259] | -0.0111 [-0.0359, +0.0253] | -0.0142 [-0.0388, +0.0210] | -0.0348 [-0.1186, +0.0609] |

| j | n | model Brier k = j+1 | − `pb_ceiling_v0@INF` | − `base_km_expanding__pb_ceiling` | − `base_km_last10__pb_ceiling` | − `base_always_ceiling__pb_ceiling` | model Brier k = 10 | − `pb_ceiling_v0@INF` | − `base_km_expanding__pb_ceiling` | − `base_km_last10__pb_ceiling` | − `base_always_ceiling__pb_ceiling` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 69 | 0.1405 | -0.0049 [-0.0130, +0.0016] | -0.0041 [-0.0122, +0.0064] | -0.0293 [-0.0474, -0.0118] | -0.0189 [-0.0361, -0.0017] | 0.1307 | -0.0025 [-0.0198, +0.0170] | -0.0037 [-0.0212, +0.0160] | -0.0051 [-0.0293, +0.0210] | -0.7389 [-0.8474, -0.6117] |
| 2 | 58 | 0.0576 | -0.0054 [-0.0142, +0.0000] | -0.0086 [-0.0275, +0.0041] | -0.0135 [-0.0325, +0.0005] | -0.0114 [-0.0328, +0.0035] | 0.1507 | +0.0037 [-0.0148, +0.0231] | -0.0001 [-0.0172, +0.0191] | -0.0012 [-0.0263, +0.0258] | -0.6942 [-0.8171, -0.5617] |
| 3 | 54 | 0.1955 | +0.0080 [-0.0038, +0.0192] | -0.0046 [-0.0283, +0.0158] | -0.0023 [-0.0454, +0.0467] | -0.0453 [-0.0957, -0.0003] | 0.1646 | +0.0053 [-0.0150, +0.0285] | +0.0059 [-0.0140, +0.0296] | +0.0034 [-0.0252, +0.0352] | -0.6687 [-0.7993, -0.5194] |
| 4 | 41 | 0.1911 | -0.0014 [-0.0207, +0.0167] | -0.0084 [-0.0262, +0.0085] | -0.0253 [-0.0626, +0.0063] | -0.0528 [-0.1141, +0.0051] | 0.1926 | -0.0028 [-0.0315, +0.0357] | +0.0042 [-0.0279, +0.0455] | -0.0039 [-0.0369, +0.0354] | -0.5879 [-0.7407, -0.4135] |
| 5 | 31 | 0.1624 | -0.0164 [-0.0460, +0.0105] | -0.0199 [-0.0532, +0.0092] | -0.0183 [-0.0552, +0.0155] | -0.0634 [-0.1380, -0.0014] | 0.2317 | +0.0049 [-0.0353, +0.0552] | +0.0090 [-0.0322, +0.0638] | +0.0063 [-0.0366, +0.0636] | -0.4779 [-0.6372, -0.3283] |
| 6 | 24 | 0.1408 | +0.0004 [-0.0276, +0.0221] | -0.0081 [-0.0395, +0.0356] | -0.0134 [-0.0494, +0.0356] | -0.0258 [-0.0861, +0.0238] | 0.2809 | +0.0259 [-0.0226, +0.0851] | +0.0294 [-0.0219, +0.0983] | +0.0191 [-0.0335, +0.0888] | -0.3441 [-0.4984, -0.1809] |
| 7 | 20 | 0.2438 | +0.0118 [-0.0035, +0.0364] | -0.0008 [-0.0327, +0.0412] | -0.0113 [-0.0640, +0.0581] | -0.0562 [-0.0984, -0.0030] | 0.2899 | +0.0188 [-0.0416, +0.0999] | +0.0073 [-0.0631, +0.1014] | -0.0020 [-0.0724, +0.0917] | -0.2601 [-0.4074, -0.0876] |
| 8 | 14 | 0.1792 | +0.0181 [-0.0058, +0.0473] | -0.0083 [-0.0675, +0.0387] | -0.0220 [-0.1095, +0.0473] | -0.0351 [-0.1183, +0.0296] | 0.2380 | +0.0052 [-0.0515, +0.0792] | -0.0072 [-0.0675, +0.0686] | -0.0255 [-0.1026, +0.0627] | -0.1192 [-0.2624, +0.0288] |
| 9 | 11 | 0.1470 | -0.0124 [-0.0424, +0.0259] | -0.0111 [-0.0359, +0.0253] | -0.0142 [-0.0388, +0.0210] | -0.0348 [-0.1186, +0.0609] | 0.1470 | -0.0124 [-0.0424, +0.0259] | -0.0111 [-0.0359, +0.0253] | -0.0142 [-0.0388, +0.0210] | -0.0348 [-0.1186, +0.0609] |

### Dondurma

**Donduruldu — §6'nın istediği bağımsız yeniden üretimden sonra.** "Beklentiden çok iyi" denetimi tetiklendiği için dondurma, ilk uygulamayı görmeyen ayrı bir oturumun (Fable) yalnız şartnameden, `borsai` import etmeden yaptığı sıfırdan yeniden üretime bağlıydı. Sonuç (2026-09-22, `docs/fable_faz4_audit/AUDIT.md`): üç ledger'ın 870 (fold × ufuk) hücresinin hepsinde return, p_up, q10, q90 ve mean için **maks |Δ| = 0** (eşik 1e-9); §6'nın 36 satırında fark, aralık uçları ve n için **Δ = 0**; sızıntı yok (her fold'da hücredeki en son seans < kesim), S_k yeniden fit edilmemiş (870/870 kaynak ledger'la aynı); hüküm üç model için **FREEZE_OK**. Duyarlılık (N_MIN 5/20, tek grup, havuzsuz): birincil fark −0.112 … −0.122, aralık üst ucu −0.070 … −0.077 — hüküm değişmiyor; dondurulan model şartnamedeki v0'dır. Dondurma temiz ağaçta yapıldı (kayıtlarda `borsai_dirty` false); JSON'lar `models/` altına, kayıtları `models/INDEX.json`'un **sonuna** eklendi, ilk 16 kayıt değişmedi. Altın ledger'lar bayt olarak korundu (yeni sütun eklenmedi): denetlenen dosyalar bunlardır.

| model_id | Dosya sha256 (ilk 12) | Gömülü seri modeli | Seri sha256 (ilk 12) | Fiyat alanı | Hücre gözlemi | Z m = 1..10 | B m = 1..9 | Hücre kesimi |
|---|---|---|---|---|---|---|---|---|
| `ceiling_path_v0` | `3e97e8788266` | `ceiling_hazard_v0` | `caa4dc867a9f` | `ipo_price_tl` | 567 | [18, 18, 18, 18, 18, 18, 18, 18, 18, 18] | [67, 64, 60, 54, 48, 40, 28, 15, 11] | 2026-08-19 (99 arz) |
| `ceiling_path_v0@INF` | `5e3692a82e25` | `ceiling_hazard_v0@INF` | `c5ac8085fd76` | `ipo_price_tl` | 567 | [18, 18, 18, 18, 18, 18, 18, 18, 18, 18] | [67, 64, 60, 54, 48, 40, 28, 15, 11] | 2026-08-19 (99 arz) |
| `pb_ceiling_path_v0` | `3d1e2f41f5d0` | `pb_ceiling_v0` | `7fb7a41e48ea` | `ipo_price_try` | 567 | [18, 18, 18, 18, 18, 18, 18, 18, 18, 18] | [67, 64, 60, 54, 48, 40, 28, 15, 11] | 2026-08-19 (99 arz) |

Fiyat alanı: `pb_ceiling_path_v0` limit yolunu **planlanan** fiyattan kurar (PB girdisi `ipo_price_try`, SPK onaylı izahnamedeki fiyat), kesin arz fiyatından değil (SPEC_DEVIATIONS F4, F15); ana model ve sıfır model kesin arz fiyatını (`ipo_price_tl`) kullanır. Hücrelerin baz fiyatı üç modelde de eğitim arzlarının resmi kesin arz fiyatıdır. H99'da planlanan fiyat 99/99 arzda kesin fiyata eşitti; canlıda ayrışabilir.

### Faz 4 koşuları ve deney günlüğü

| Koşu | Plan | Fold | Ledger sha256 (ilk 12) | Günlükteki koşu sayısı |
|---|---|---|---|---|
| `ceiling_path_v0` | ceiling_path | 87 | `1f45365ee2d8` | 2 |
| `ceiling_path_v0@INF` | ceiling_path | 87 | `cf79a8330c79` | 2 |
| `pb_ceiling_path_v0` | pb_ceiling_path | 87 | `498676bb985e` | 2 |

Koşullu keşif (`kind: conditional_eval`) günlük satırı: 1.

Bu bölümün sayıları bağımsız olarak yeniden üretildi: 2026-09-22, ilk uygulamayı görmeyen ayrı oturum, maks |Δ| = 0; ayrıntı ve ham çıktılar `docs/fable_faz4_audit/`.

## Faz 8: kırılma akşamı (Fable şartnamesi, docs/specs_faz8/)

**Terazi ve ölçek:** aşağıdaki her sayı **backtest**tir (retrospektif walk-forward, H99'un 82 kırılma akşamı, `scale = backtest_break`) ve **tasarıma maruzdur** (hipotez "kırılma türü sonraki günleri ayırır" ve iki özellik H99'dan doğdu; SPEC_BREAK_V0 §12); H99 backtest'i yalnız ön elemedir. Ölçek: Brier (kırpmasız), F1 = ertesi işlem görmüş seansın kapanışı alt limitte (birincil), F2 = iki ardışık taban (ikincil). Modeller **henüz dondurulmadı** (Fable'ın sıfırdan yeniden üretiminden sonra ayrı görev; `models/INDEX_POST_BREAK.json`); canlı sicilde satırları yoktur. Canlı terazi (`live_break`, makine sıralı) ve eski dönem bu bölümde yoktur ve hiçbir tabloda toplanmaz.

Şartname: `docs/specs_faz8/SPEC_BREAK_V0.md` (sha256 `da98351c2b1b…`, commit 7d78d43, uygulamadan önce) ve bağlayıcı kararlar `docs/specs_faz8/KARARLAR.md` (sha256 `8d8bbc971b01…`; §C proje sahibi kararları C1–C5, 2026-10-01). Olay: b = L + 1 (ilk işlem görmüş tavan-dışı kapanış), kapsam b ∈ 1..9 (L = 0 dahil, C3); kırılma akşamı = D_b'nin THB yayımı. Model: başlık başına L2-lojistik (V1.6 C ızgarası, iç arz-bırak Brier; `fit.fit_fall_horizon`), özellikler `b_floor` (kapanış == alt limit, ham metin Decimal) ve `b_turnover` (ln(hacim / arz edilen pay), eğitim [p05, p95]'ine kırpma, z-skor). Kural satırı `break_floor_v0@ZERO` (fold'un eğitim oranı). D10 ≤ arz için model yok (C1); yastık kuralı `D10_STRUCTURAL_ZERO` kod, skorlanmaz. Bant varsayımı (±%10, içe yuvarlama, D1 baz fiyatı) rev. 54'e karşı doğrulandı (`docs/faz8/BANT_DOGRULAMA.md`). Uygulama yorumları SPEC_DEVIATIONS N.

Plan (§7.2): test birimi b ≤ 9 olan her arz; kesim T = D_b'nin tarihi; başlık h için eğitim satırı ancak hedef seansı (F1: D_{b+1}, F2: D_{b+2}) T'den kesin önce; ≥ 10 satır, ≥ 5 olay, ≥ 5 olay-dışı. Ürün karşılaştırıcısının hücreleri test arzının ilk işlem gününe kesimli (`build_cells(cutoff = D_1(k))`; ürünün listeleme öncesi kaydının karşılığı); Faz 4 ledger'ının 87 OK fold'unda hücre sayıları birebir.

Değerlendirme kuralları (sonuçlar görülmeden kodda sabitlendi, `borsai/specs.py: OPERATIONAL_RULES_FAZ8`, `FAZ8_RULES`, commit A):

- Birincil hücre (§5.2; tek): F1 Brier, `break_floor_v0 − PRODUCT_BREAK_FLOOR`, yakın dönem fold'ları (ilk işlem ≥ 2024-01-01). Brier kırpmasızdır (karşılaştırıcı tam 0/1 verebilir). Eşleşik küme: modelin F1 başlığı FIT_OK, karşılaştırılanın değeri var (ürün karşılaştırıcısında `POST_BREAK_INSUFFICIENT` ise çift düşer, sayılır), gerçekleşen y_F1 dolu; fark = model − karşılaştırılan (negatif = model iyi). %95 aralık SPEC_DEVIATIONS C7: ilk işlem ayı blokları, 4000 tekrar, `random.Random(20260921)`; n < 10 ya da < 6 ay ise aralık yok.
- İlan edilmiş ikinciller (aynı yakın dönem fold'ları): F1 − `break_floor_v0@ZERO` (fold'un eğitim oranı), F2 − `PRODUCT_BREAK_FLOOR`, F2 − `@ZERO`, F1 − `base_floor_by_type` (fold eğitiminde test arzının b_floor sınıfındaki F1 oranı; sınıf eğitimde yoksa çift düşer). Bilgi: `PRODUCT_BREAK_FLOOR − @ZERO` (F1, birincil hücrenin arzlarında). Keşif (hüküm yok): bütün fold'lar, 2023 fold'ları, b = 1 ve 2 ≤ b ≤ 9, b_floor sınıfına göre kalibrasyon, ilk işlem yılı. Aralık dili backtest'tir ("aralık 0'ın altında / üstünde / 0'ı içeriyor"); canlı hüküm sözcükleri kullanılmaz.
- §6 fark satırları (ilk altı satır): "Aralık" sütunu [alt, üst] kapalıdır; "Beklenen fark" (nokta) değerlendirilmez. Gerçekleşen fark alt ucun altındaysa **tutmadı (daha iyi)** (konum: altında — beklentiden çok iyi), üst ucun üstündeyse **tutmadı (daha kötü)** (konum: üstünde). Aralık içindeyse "Aralık 0'ı" ifadesinin kesin kısmına bakılır: "dışlaması olası" ve "dışlaması olası, garanti değil (alt uç ≤ 0)" → %95 aralığın alt ucu ≤ 0; "içerir" → alt ≤ 0 ≤ üst; "içerir ya da negatif dışlar" → alt uç ≤ 0; "pozitif dışlar ya da içerir (alt uç ≥ 0)" → üst uç ≥ 0 (sözcüklerden; parantezdeki "alt uç ≥ 0" sözcüklerle çeliştiği için hükme girmez, ayrı sütunda yazılır — SPEC_DEVIATIONS N). Kesin kısım tutuyorsa **tuttu**, tutmuyorsa **tutmadı (aralık)**; aralık yoksa **tutmadı (aralık yok)**. İfadenin tamamı ("dışlaması olası" → üst uç < 0; "içerir" → 0'ı içerir; "içerir ya da negatif dışlar" → alt uç ≤ 0; "pozitif dışlar ya da içerir" → üst uç ≥ 0) ayrı sütunda yazılır.
- Kalibrasyon satırı: yakın dönem F1 FIT_OK fold'larında (gerçekleşen y_F1 dolu) |ort(p_F1) − gözlenen y_F1 oranı| ≤ 0.06 → **tuttu**; aksi halde **tutmadı (model yüksek / model düşük)**.
- β_floor işareti (iki parça): nihai fit F1'de β_floor > 0; bütün F1 FIT_OK fold'larından C ≠ ZERO ve b_floor düşmemiş olanlarda β_floor > 0 payı ≥ %90 (düşen ve ZERO fold'ları paydada değil, ayrıca sayılır). İkisi tutarsa **tuttu**, hiçbiri tutmazsa **tutmadı**, aksi halde **kısmen** (tutmayan parça adıyla).
- β_turn işareti: nihai fit F1'de β_turn < 0 → **tuttu**; aksi halde **tutmadı** (> 0 ya da = 0 yönüyle). Fold payı bilgi olarak yazılır.
- Seçilen C (nihai fit F1): C ∈ [0.1, 1] → **tuttu**; C = ZERO → **tutmadı (ZERO)**; diğer → **tutmadı (daha küçük C / daha büyük C)**. Fold'lar: yakın dönem F1 FIT_OK fold'larında ZERO payı ≤ %20 → **tuttu**.
- n satırları: birincil hücrenin eşleşik n'i [60, 69] → **tuttu**; F2 satırı F2 − `PRODUCT_BREAK_FLOOR` hücresinin yakın dönem eşleşik n'i [55, 65] → **tuttu**; dışında **tutmadı (az / çok)**.
- Başarısızlık tanımları (§6, aynen): (a) yakın dönem F1 − `@ZERO` aralığı 0'ı içeriyor (alt ≤ 0 ≤ üst) ya da aralık yok → "basit kuraldan ayırt edilemiyor" (dondurulur, öne çıkarılmaz); (b) birincil aralığın alt ucu > 0 → "zarar veriyor" (kartta "ürünün cevabından kötü"); (c) nihai fit F1'de C = ZERO ya da yakın dönem F1 FIT_OK fold'larının ≥ %50'sinde ZERO → "özellikler bilgi eklemiyor"; (d) n ≥ 30 iken |ort(p_F1) − gözlenen| > 0.15 → "düzey kayması" notu.
- Ön eleme (k1, §8 aşama 1): birincil aralığın üst ucu < 0 VE F1 − `@ZERO` aralığının üst ucu < 0 → "backtest'te geçiyor (tasarıma maruz)"; kart bu durumda modeli "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = k" etiketiyle öne çıkarabilir. Aksi halde k1 sağlanmaz (tutmayan ayak adıyla yazılır). Eski dönem hiçbir aşamada kullanılmaz.
- Beklentiden çok iyi (§6): birincil fark < −0.160 ya da birincil aralığın üst ucu < −0.080 ya da F1 − `@ZERO` farkı < −0.090 → raporda açıkça yazılır; dondurma bu görevde yoktur. Tetiklense de tetiklenmese de sıradaki adım Fable'ın bu şartnameden bağımsız, sıfırdan yeniden üretimidir (ledger'lar |Δ| ≤ 1e-9).
- Kazanç/kayıp/eşitlik: arz başına Brier farkının işareti; fark bit-eşit 0 ise eşitlik; |fark| ≤ 1e-12 eşitlik sayısı ayrıca yazılır.
- Terazi: bu bölümdeki her sayı backtest'tir (H99 walk-forward, scale = backtest_break) ve tasarıma maruzdur (hipotez ve özellik seçimi H99'dan; SPEC_BREAK_V0 §12). Canlı terazi (`live_break`, makine sıralı) ve eski dönem bu bölümde yoktur; hiçbir tabloda toplanmaz.

### Kartlar

| model_id | Rol | Özellikler | Eğitim | Fold (FIT_OK: F1 / F2) | Birincil (yakın dönem) | Ön eleme (k1) | Canlı |
|---|---|---|---|---|---|---|---|
| `break_floor_v0` | model (tek) | b_floor, b_turnover | H99_BREAK_B_LE_9 (F1 82 / olay 25; F2 78 / olay 11) | 69 / 52 | -0.1904 [-0.2520, -0.1247], n = 69 | **sağlandı** | n = 0 (dondurulmadı) |
| `break_floor_v0@ZERO` | kural satırı (C = ZERO; aday değil) | — (sabit) | H99_BREAK_B_LE_9 (F1 82 / olay 25; F2 78 / olay 11) | ledger'ın zero_F1 / zero_F2 sütunları | — | — | n = 0 (dondurulmadı) |

### Birincil hücre ve `@ZERO` hücresi (yakın dönem, ilk işlem ≥ 2024-01-01)

| Hücre | Karşılaştırılan | n (ay) | model | karş. | fark | %95 aralık | model iyi / karş. iyi / eşit | aralık |
|---|---|---|---|---|---|---|---|---|
| F1 Brier **(BİRİNCİL)** | `PRODUCT_BREAK_FLOOR` | 69 (21) | 0.1878 | 0.3781 | -0.1904 | [-0.2520, -0.1247] | 48 / 21 / 0 (\|fark\| ≤ 1e-12: 0) | aralık 0'ın altında |
| F1 Brier **(ilan edilmiş ikincil)** | `break_floor_v0@ZERO` | 69 (21) | 0.1878 | 0.2158 | -0.0281 | [-0.0453, -0.0074] | 49 / 17 / 3 (\|fark\| ≤ 1e-12: 3) | aralık 0'ın altında |

Beklentiden çok iyi (§6): **tetiklendi — birincil fark < -0.160; birincil aralığın üst ucu < -0.080**. Her iki durumda da dondurma bu görevde yoktur; sıradaki adım Fable'ın bu şartnameden bağımsız, sıfırdan yeniden üretimidir.

Başarısızlık tanımları (§6): (a) basit kuraldan ayırt edilemiyor: **hayır**; (b) zarar veriyor (ürünün cevabından kötü): **hayır**; (c) özellikler bilgi eklemiyor: **hayır**; (d) düzey kayması: **hayır**. Ön eleme (k1, §8): **sağlandı**.

### İkincil ve bilgi hücreleri (aynı yakın dönem fold'ları)

| Başlık | Karşılaştırılan | Rol | n (ay) | model / sol | karş. | fark | %95 aralık | iyi / kötü / eşit | aralık |
|---|---|---|---|---|---|---|---|---|---|
| F2 | `PRODUCT_BREAK_FLOOR` | ilan edilmiş ikincil | 52 (16) | 0.0955 | 0.1527 | -0.0572 | [-0.0847, -0.0239] | 32 / 20 / 0 (\|fark\| ≤ 1e-12: 0) | aralık 0'ın altında |
| F2 | `break_floor_v0@ZERO` | ilan edilmiş ikincil | 52 (16) | 0.0955 | 0.0956 | -0.0001 | [-0.0131, +0.0179] | 38 / 14 / 0 (\|fark\| ≤ 1e-12: 0) | aralık 0'ı içeriyor |
| F1 | `base_floor_by_type` | ilan edilmiş ikincil (lojistiğin payı) | 69 (21) | 0.1878 | 0.1771 | +0.0106 | [-0.0047, +0.0282] | 17 / 52 / 0 (\|fark\| ≤ 1e-12: 0) | aralık 0'ı içeriyor |
| F1 | `PRODUCT_BREAK_FLOOR − @ZERO` | bilgi (ürün tek orandan kötü mü) | 69 (21) | 0.3781 | 0.2158 | +0.1623 | [+0.1087, +0.2139] | 22 / 47 / 0 (\|fark\| ≤ 1e-12: 0) | aralık 0'ın üstünde |

### §6 önceden yazılmış beklenti, satır satır

| Hücre (aynen) | Karşılaştırılan (aynen) | Beklenen (aynen) | Aralık (aynen) | Aralık 0'ı (aynen) | Gerçekleşen | %95 aralık | n | Konum (T6) | Hüküm | İfadenin tamamı |
|---|---|---|---|---|---|---|---|---|---|---|
| **F1 Brier (BİRİNCİL)** | `PRODUCT_BREAK_FLOOR` | **−0.080** | **[−0.140, −0.020]** | **dışlaması olası** | -0.1904 | [-0.2520, -0.1247] | 69 (21) | **altında — beklentiden çok iyi** | **tutmadı (daha iyi)** | üst uç < 0: evet |
| F1 Brier | `@ZERO` | −0.040 | [−0.080, 0.000] | dışlaması olası, garanti değil (alt uç ≤ 0) | -0.0281 | [-0.0453, -0.0074] | 69 (21) | **aralık içinde** | **tuttu** | üst uç < 0: evet |
| F1 Brier | `base_floor_by_type` | −0.005 | [−0.025, +0.015] | içerir | +0.0106 | [-0.0047, +0.0282] | 69 (21) | **aralık içinde** | **tuttu** | 0'ı içerir: evet |
| F2 Brier | `PRODUCT_BREAK_FLOOR` | −0.050 | [−0.110, +0.010] | içerir ya da negatif dışlar | -0.0572 | [-0.0847, -0.0239] | 52 (16) | **aralık içinde** | **tuttu** | alt uç ≤ 0: evet |
| F2 Brier | `@ZERO` | −0.030 | [−0.070, +0.010] | içerir | -0.0001 | [-0.0131, +0.0179] | 52 (16) | **aralık içinde** | **tuttu** | 0'ı içerir: evet |
| bilgi: `PRODUCT − @ZERO` (F1) | — | +0.040 | [0.000, +0.090] | pozitif dışlar ya da içerir (alt uç ≥ 0) | +0.1623 | [+0.1087, +0.2139] | 69 (21) | **üstünde** | **tutmadı (daha kötü)** | üst uç ≥ 0: evet; parantez (alt uç ≥ 0): evet |
| Kalibrasyon | ort(p_F1) − gözlenen F1 oranı | \|Δ\| ≤ 0.06 | — | — | +0.0417 (ort p 0.3315, gözlenen 0.2899) | — | 69 | — | **tuttu** | — |
| Katsayı işareti | β_floor (F1) | > 0; nihai fit ve ZERO olmayan fold'ların ≥ %90'ında | — | — | nihai +0.9867; fold'larda > 0: 66/66 (%100; düşen 0) | — | 66 | — | **tuttu** | — |
| Katsayı işareti | β_turn (F1) | < 0 (düşük güven) | — | — | nihai +0.0629; fold'larda < 0: 52/66 (%79; düşen 0) | — | 66 | — | **tutmadı (> 0)** | — |
| Seçilen C | nihai fit F1 | 0.1–1 en olası; ZERO olası değil | — | — | 1.0 | — | — | — | **tuttu** | — |
| Seçilen C | fold'lar F1 | ZERO payı ≤ %20 (yakın dönem FIT_OK fold'ları) | — | — | %4 | — | — | — | **tuttu** | — |
| n | F1 birincil eşleşik (yakın dönem) | 60–69 | — | — | 69 | — | — | — | **tuttu** | — |
| n | F2 (yakın dönem) | 55–65 | — | — | 52 | — | — | — | **tutmadı (az)** | — |

Hüküm sayıları: tuttu 9, tutmadı 4, kısmen 0 (toplam 13).

### Keşif (hüküm yok)

| Hücre | Fold kümesi | n (ay) | model / sol | karş. | fark | %95 aralık | iyi / kötü / eşit |
|---|---|---|---|---|---|---|---|
| F1 − `PRODUCT_BREAK_FLOOR` | 2023 fold'ları | 0 | — | — | — | — | — |
| F1 − `break_floor_v0@ZERO` | 2023 fold'ları | 0 | — | — | — | — | — |
| F2 − `PRODUCT_BREAK_FLOOR` | 2023 fold'ları | 0 | — | — | — | — | — |
| F2 − `break_floor_v0@ZERO` | 2023 fold'ları | 0 | — | — | — | — | — |
| F1 − `PRODUCT_BREAK_FLOOR` | bütün fold'lar | 69 (21) | 0.1878 | 0.3781 | -0.1904 | [-0.2520, -0.1247] | 48 / 21 / 0 (\|fark\| ≤ 1e-12: 0) |
| F1 − `break_floor_v0@ZERO` | bütün fold'lar | 69 (21) | 0.1878 | 0.2158 | -0.0281 | [-0.0453, -0.0074] | 49 / 17 / 3 (\|fark\| ≤ 1e-12: 3) |
| F2 − `PRODUCT_BREAK_FLOOR` | bütün fold'lar | 52 (16) | 0.0955 | 0.1527 | -0.0572 | [-0.0847, -0.0239] | 32 / 20 / 0 (\|fark\| ≤ 1e-12: 0) |
| F2 − `break_floor_v0@ZERO` | bütün fold'lar | 52 (16) | 0.0955 | 0.0956 | -0.0001 | [-0.0131, +0.0179] | 38 / 14 / 0 (\|fark\| ≤ 1e-12: 0) |
| F1 − `PRODUCT_BREAK_FLOOR` | b = 1 (L = 0), bütün yıllar | 17 (8) | 0.1984 | 0.3273 | -0.1288 | [-0.3000, +0.0393] | 9 / 8 / 0 (\|fark\| ≤ 1e-12: 0) |
| F1 − `break_floor_v0@ZERO` | b = 1 (L = 0), bütün yıllar | 17 (8) | 0.1984 | 0.2106 | -0.0122 | [-0.0457, +0.0117] | 13 / 4 / 0 (\|fark\| ≤ 1e-12: 0) |
| F1 − `PRODUCT_BREAK_FLOOR` | 2 ≤ b ≤ 9, bütün yıllar | 52 (19) | 0.1843 | 0.3948 | -0.2105 | [-0.2826, -0.1311] | 39 / 13 / 0 (\|fark\| ≤ 1e-12: 0) |
| F1 − `break_floor_v0@ZERO` | 2 ≤ b ≤ 9, bütün yıllar | 52 (19) | 0.1843 | 0.2176 | -0.0333 | [-0.0609, -0.0044] | 36 / 13 / 3 (\|fark\| ≤ 1e-12: 3) |

Kalibrasyon (F1, modelin FIT_OK fold'ları; ort p − gözlenen):

| Küme | n | ort p_F1 | gözlenen y_F1 | fark |
|---|---|---|---|---|
| yakın dönem | 69 | 0.3315 | 0.2899 | +0.0417 |
| 2023 | 0 | — | — | — |
| bütün | 69 | 0.3315 | 0.2899 | +0.0417 |
| bütün, b_floor = 1 | 28 | 0.4499 | 0.5357 | -0.0858 |
| bütün, b_floor = 0 | 41 | 0.2507 | 0.1220 | +0.1287 |
| ilk işlem yılı 2023 | 0 | — | — | — |
| ilk işlem yılı 2024 | 27 | 0.3553 | 0.3704 | -0.0151 |
| ilk işlem yılı 2025 | 16 | 0.3287 | 0.1250 | +0.2037 |
| ilk işlem yılı 2026 | 26 | 0.3086 | 0.3077 | +0.0009 |

### Fold özeti

- 82 fold (b ≤ 9; yakın dönem 69, 2023 13); F1 durumları: FIT_OK 69, INSUFFICIENT_TRAINING_HISTORY 13.
- F1: başlık durumları FIT_OK 69, INSUFFICIENT_TRAINING_HISTORY 13; FIT_OK 69 (yakın dönem 69, 21 ay, olay 20); seçilen C: ZERO: 3, 0.01: 7, 0.1: 32, 1.0: 27.
- F2: başlık durumları FIT_OK 52, INSUFFICIENT_TRAINING_HISTORY 26, TARGET_UNDEFINED_F2 4; FIT_OK 52 (yakın dönem 52, 16 ay, olay 5); seçilen C: 0.1: 43, 1.0: 9.
- Ürün karşılaştırıcısı `POST_BREAK_INSUFFICIENT`: 5 fold. Test arzının b_turnover'ı kırpılan fold (F1 ön işlemesi): 11. b_floor ya da b_turnover sıfır varyansla düşen fold (F1): 0.
- Yastık kuralı (`D10_STRUCTURAL_ZERO`, bilgi; skorlanmaz): D10 ≤ arz mekanik olarak imkânsız olan kırılma akşamı b = 7: 6, b = 8: 6, b = 9: 4 (toplam 16).

### Nihai fit önizlemesi (dondurulmadı)

Dondurmanın kullanacağı fonksiyonla (`borsai/post_break.py: final_fit`) bütün eğitim kümesinde (F1 82 arz, F2 78); `models/`'e yazılmadı, dosyalar `docs/faz8/backtest/` altında. Katsayılar z-skorlu kolonlarda, p_floor = P(taban) başlığınındır. numpy nihai model ile stdlib `predict_break` eğitim satırlarında |Δp| ≤ 1e-12 (§13-9).

| model_id | Başlık | C | sabit | katsayılar | arz / olay | kırpma [p05, p95] (ln) | parite maks \|Δp\| | dosya sha256 (ilk 12) |
|---|---|---|---|---|---|---|---|---|
| `break_floor_v0` | F1 | 1 | -1.0007 | b_floor +0.9867, b_turnover +0.0629 | 82 / 25 | [-2.17889, 1.05795] | 1.1e-16 | `eab46afb1b05` |
| `break_floor_v0` | F2 | 0.1 | -1.8949 | b_floor +0.2872, b_turnover -0.3080 | 78 / 11 | [-2.18367, 1.06136] | 5.6e-17 | `eab46afb1b05` |
| `break_floor_v0@ZERO` | F1 | ZERO (kural) | p = 0.304878 | — | 82 / 25 | — | 0.0e+00 | `d63f8f55b896` |
| `break_floor_v0@ZERO` | F2 | ZERO (kural) | p = 0.141026 | — | 78 / 11 | — | 0.0e+00 | `d63f8f55b896` |

Dondurulmuş karşılaştırıcı oranları (canlıda `@ZERO` ve `by_type` bunlardır): F1 eğitim oranı 0.3049, F2 0.1410; b_floor = 1 sınıfında 0.5429 (19/35), b_floor = 0 sınıfında 0.1277 (6/47).

Duyarlılıklar (§7.2: yalnız b_floor, yalnız b_turnover, + Z/B grubu): günlükte `kind: sensitivity` satırlarıdır; model değildir, bu belgeye, skora ve varyant sayacına girmez (test_experiment_log kuralı); sonuçları `docs/faz8/IMPL_RAPOR.md`'de.

### Faz 8 koşusu ve deney günlüğü

| Koşu | Plan | Fold | Ledger sha256 (ilk 12) | Günlükteki `kind: backtest` satırı | `kind: sensitivity` satırı |
|---|---|---|---|---|---|
| `break_floor_v0` (+ `break_floor_v0@ZERO` sütunları) | `H99_BREAK_WALK_FORWARD_E_CUTOFF_B_LE_9_MIN10ROWS_5EV_5NE` | 82 | `730a4e3cc75d` | 1 | 3 |

### Dondurma

**Donduruldu, bağımsız yeniden üretimden sonra.** İlk uygulamayı görmeyen ayrı bir oturum (Fable) şartnameden, `borsai` import etmeden sıfırdan yeniden üretti (2026-10-02, HEAD c84ba64): hüküm **REPRO_OK**; resmi ledger, üç duyarlılık ledger'ı ve iki nihai fit önizlemesi bit-eşit, maks |Δ| = 0.000e+00 (eşik 1e-9); Faz 4 hücre paritesi 87/87; 13/13 mutasyon kırmızı; sızıntı yok. Ayrıntı ve ham çıktılar `docs/fable_faz8_audit/`. Donmuş dosyalar yukarıdaki nihai fit önizlemelerinin aynısıdır (`created_at`, `code_version`, `runtime` dışında `==`); dondurma temiz ağaçta yapıldı (`borsai_dirty` false). Şartname belgesi donmuş JSON'larda `spec_document.sha256` = `da98351c2b1b…` (`docs/specs_faz8/SPEC_BREAK_V0.md`). Yukarıdaki 'dondurulmadı' ifadeleri backtest anının kaydıdır.

| model_id | Dosya | sha256 | Dondurma tarihi (yerel saat; kanıt push'tur) | Rol |
|---|---|---|---|---|
| `break_floor_v0` | `models/break_floor_v0.json` | `81f07e7810ca5b9513ebc577e14182798ea0b227f105df1551950d6ce40a3eab` | 2026-10-02 | model |
| `break_floor_v0@ZERO` | `models/break_floor_v0@ZERO.json` | `f460acc84717fb489eb81d96fce01ff44f4eb850b9fc66f0c50fb8858000bd3b` | 2026-10-02 | kural satırı ve karşılaştırıcı (`@ZERO`) |

- **Dizin:** `models/INDEX_POST_BREAK.json` ayrı dizindir (iki giriş, `FAZ8_MODEL_IDS` sırası); `models/INDEX.json` ve `models/INDEX_POST_D1.json` değişmedi. Listeleme öncesi kayıt ve POST_D1 kaydı bu modelleri okumaz (`freeze.run_model` → `PARAMS_INVALID`).
- **Öne çıkan durum** (§8 aşama 1): k1 sağlandı (birincil ve `@ZERO` aralıklarının üst uçları < 0). `break_floor_v0`'ın p_F1'i kartta öne çıkarılabilir; etiket aynen: "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0". `@ZERO` oranı ve ürün türevi yan yana.
- **Canlı:** makine sıralı (`MACHINE_SEQUENCED`), ölçek `live_break`; hiçbir ölçekle toplanmaz. Skorlama ve makine kayıt yazıcısı ayrı görevdir. Zaman kanıtı dondurma commit'inin push'udur. Bugünkü 7 arz bu model için RETRO'dur (§9.3).
- **Bilgi notları** (proje sahibi kararı, SPEC_DEVIATIONS N24; hücre tanımı değişmez):
  - (i) Ürün türevi kesin eşikle hesaplanır. Bir adım toleransla taban kırılmasında ürünün ortalaması 0.199 olur (kesin eşikte 0.115). Birincil fark −0.1611 [−0.2193, −0.1013]; aralık yine 0'ın altında.
  - (ii) Ürün taban üstü kırılmaya ≈ 0.57 der, gözlenen 0.12'dir. Birincil farkın büyüklüğü karşılaştırıcının zayıflığından gelir; tek orana karşı kazanç küçüktür: -0.0281 [-0.0453, -0.0074].
- **Kart uyarıları** (EK 5 kullanacak; AUDIT §8, kısaltılmış):
  1. birincil farkın büyüklüğü karşılaştırıcının zayıflığındandır (ürün taban üstü kırılmaya ≈ 0.57 der; eşik yuvarlaması ≈ 0.03 ekler); tek orana karşı kazanç küçük: −0.028 [−0.045, −0.007].
  2. β_turn işareti beklentinin tersi (+0.063); el değiştirme bilgi eklemiyor (duyarlılıklar, `by_type`).
  3. F2 − `@ZERO` ≈ 0: iki ardışık taban için model tek orandan ayırt edilemiyor.
  4. kalibrasyon sınıfa göre: taban üstü kırılmada model yüksek (+0.129), taban kırılmasında düşük (−0.086); 2025 kohortunda +0.204 (n 16).
  5. rejim `FON_KRIZI_2026` (D_1 ≥ 2026-09-16; bitiş açık, KARARLAR C4): önceden yazılı okuma "model tabanı az tahmin eder".
  6. `BAND_RULE_MISMATCH` olunca yastık rozeti gizli.
  7. eski dönem terazisi yok (proje sahibi kararı); n F2 52 < 55 beklentisi.

## Faz 7C: düşen arz modeli v0 (Fable şartnamesi, docs/specs_faz7_c/)

**Terazi ve ölçek:** aşağıdaki her sayı **backtest**tir (retrospektif walk-forward, H99 test arzları) ve **tasarıma maruzdur** (§10: özellikler H99'un ve eski kohortun açık kümesinin sonuçları görülerek, 2 054 varyant denenerek seçildi); kanıt değeri kasadan ve canlıdan düşüktür. Ölçek: p_up = P(D_h kapanışı > arz fiyatı) Brier'i (kırpmasız), D10 birincil, D5 ikincil; "düşme olasılığı" = 1 − p_up (Brier aynı). Adaylar **henüz dondurulmadı** (Fable'ın sıfırdan yeniden üretiminden sonra ayrı görev); canlı sicilde satırları yoktur. Kasa terazisi bekliyor (`ceiling_hazard_v1` ailesiyle birlikte, tek seferde).

Şartname: `docs/specs_faz7_c/SPEC_C_V0.md` (sha256 `d75c17cfec09…`, commit 4fe4e51, uygulamadan önce push kanıtlı) ve bağlayıcı kararlar `docs/specs_faz7_c/KARARLAR_C.md` (sha256 `2b60bec41924…`; çeliştiği yerde geçerli). Hedef y4 = 1 − Y_D10 (D10 kapanışı ≤ arz fiyatı; KARARLAR_C C1), ikincil y3 = 1 − Y_D5 (C3). Üç aday, her biri D5 ve D10 için ayrı L2-lojistik başlık (V1.6 C ızgarası, iç arz-bırak Brier; getiri başlığı yok): `fall_d10_v0_h99` — f1r (TÜFE ile reel büyüklük, `ceiling_hazard_v1_real` ile tek tanım), ln f3 (talep katı), ek satış bayrağı; H99'un 94 arzı (KARARLAR_C C2: bütçe 6.5 olay/parametre, kabul); `fall_d10_v0_pooled` — aynı özellikler, H99 + açık küme 161 arz, rejim terimi yok; `fall_d10_v0_addsale` — yalnız ek satış bayrağı, havuzun ek satış alanı dolu 165 arzı, f3 istemez. Kural satırı `fall_d10_v0_pooled@ZERO` (havuz oranı). Ek satış alanı boşsa RET (C4). Uygulama yorumları SPEC_DEVIATIONS K.

Planlar: PLAN_V15 kuralı (ufuk başına eğitim arzı ancak D_h seansı test arzının T'sinden kesin önce; eğitim n ≥ 10). Test arzları H99'dandır: `h99` ve `pooled` aynı 94 arz, `addsale` H99'un ek satış alanı dolu 95 arzı; havuz planlarında açık küme arzları eğitimde (son seansları 2023-10-04'ten önce). İmputasyonsuz tarifte f3'ü eğitim kümesinin filtre moduna açıkça zıt olan arz o kümede kullanılmaz (SPEC_DEVIATIONS J10 kuralı aynen, K); `@ZERO` modelinin planını kullanır. Karşılaştırıcılar Faz 1A altın ledger'larından, yeniden koşulmaz.

Etiket ve karşılaştırma kuralları (sonuçlar görülmeden kodda sabitlendi, `borsai/report_faz7c.py: OPERATIONAL_RULES_FAZ7C` ve `borsai/backtest.py: near_era_label_fall`, commit A):

- Birincil hücre (§5.1; tek): `fall_d10_v0_pooled − fall_d10_v0_h99`, D10 Brier, ilk işlem ≥ 2024-01-01 olan fold'lar. Brier p_up = P(kapanış > arz) ile ve kırpmasızdır (SPEC_SCORING §7; düşme olasılığı 1 − p_up ile aynı değer); iki ledger fold ticker'ıyla eşleşir, ikisinde de Logit FIT_OK olan fold'lar sayılır.
- Etiket (§5.1): %95 aralığın alt ucu > 0 → **bozuyor** (eski arzları eğitime katmak yakın dönemi bozuyor); üst ucu ≤ +0.008 → **tolerans içinde**; diğer → **belirsiz** (alt uç = 0 dışlamaz). Aralık SPEC_DEVIATIONS C7: ilk işlem ayı blokları, 4000 tekrar, `random.Random(20260921)`; n < 10 ya da < 6 ay ise aralık yok (`borsai/backtest.py: near_era_label_fall`, `paired_p_up`).
- §6.2 konumu (görev kararı T6): gerçekleşen fark noktası §6.2'nin beklenen aralığı [alt, üst] (kapalı) içindeyse **aralık içinde**, altındaysa **altında — beklentiden çok iyi**, üstündeyse **üstünde**. Beklentiden çok iyi olsa da olmasa da sıradaki adım Fable'ın sıfırdan yeniden üretimidir (ledger'lar |Δ| ≤ 1e-9).
- Kazanç/kayıp/eşitlik: fold başına Brier farkının işareti; fark bit-eşit 0 ise eşitlik; |fark| ≤ 1e-12 eşitlik sayısı ayrıca yazılır (bağımsız yeniden fit bit-eşit eşitlik üretmez).
- İkincil hücreler (§5.1, ilan edilmiş; aynı fold'lar): her aday − `base_rate` (D10 ve D5), her aday − `v1_5_h99` (D10; V1.5'in p_up başlığı), `pooled − pooled@ZERO` (D10). `base_rate` ve `v1_5_h99` Faz 1A altın ledger'larındandır (PLAN_V15, 99 arz; yeniden koşulmaz, sha pinli); `fall_d10_v0_h99@ZERO` ayrıca kaydedilmez (§2). D5'te − `v1_5_h99` ve `pooled − pooled@ZERO`, 2023 fold'ları ve bütün fold'lar keşiftir. Aralık dili backtest'tir ("aralık 0'ın altında / üstünde / 0'ı içeriyor"); SPEC_SCORING §8 hüküm sözcükleri kullanılmaz.
- Merdiven (§5.4; yalnız bilgi, hüküm dili yok): aynı yakın dönem D10 fold'larında `h99 − addsale` (f1r ve ln f3'ün payı), `pooled − h99` (eski verinin payı), `pooled − pooled@ZERO` (özelliklerin payı).
- Proje sahibinin sorusu ("eski arzları eğitime katmak bugünkü tahmini bozar mı?") birincil hücrenin etiketiyle cevaplanır (§6.4 (b)). H99 tasarıma maruzdur (§10): özellikler H99 ve açık kümenin sonuçları görülerek seçildi; kanıt değeri kasadan ve canlıdan düşüktür.
- Kasa (§5.2, tek seferlik; `ceiling_hazard_v1` ailesiyle birlikte) ve canlı (§5.3) teraziler bu bölümde yoktur. Uygulama kartı seçimi (§5.5) kasa sonucunu bekler; üç aday sonuç ne olursa olsun dondurulur ve listede kalır (KARARLAR K4).

### Kartlar

| model_id | Rol | Özellikler | Eğitim | Plan | Fold (Logit FIT_OK: D10 / D5) | Yakın dönem etiketi (birincil) | Kasa | Canlı | Varyant (aynı veri sürümü; `scores.json`) | Aile keşif sayacı (`scores.json`) |
|---|---|---|---|---|---|---|---|---|---|---|
| `fall_d10_v0_h99` | aday (merdivenin H99 basamağı; KARARLAR_C C2) | f1r, f3, add_sale | H99_F3_AS_PRESENT (94; D10 olay 26, D5 18) | fall_h99 | 76 / 76 | **belirsiz** (`pooled − h99`) | kasa: bekliyor | n = 0 (dondurulmadı) | 23 | 2054 |
| `fall_d10_v0_pooled` | aday (havuz) | f1r, f3, add_sale | H99_PLUS_OOT_OPEN_F3_AS_PRESENT (161; D10 olay 39, D5 29) | fall_pooled | 94 / 94 | **belirsiz** (`pooled − h99`) | kasa: bekliyor | n = 0 (dondurulmadı) | 2059 | 2054 |
| `fall_d10_v0_addsale` | aday (yalnız ek satış) | add_sale | H99_PLUS_OOT_OPEN_AS_PRESENT (165; D10 olay 40, D5 30) | fall_addsale | 95 / 95 | — | kasa: bekliyor | n = 0 (dondurulmadı) | 2059 | 2054 |
| `fall_d10_v0_pooled@ZERO` | kural satırı (C = ZERO; aday değil) | — (sabit) | H99_PLUS_OOT_OPEN_F3_AS_PRESENT (161; D10 olay 39, D5 29) | fall_pooled | 94 / 94 | — | kasa: bekliyor | n = 0 (dondurulmadı) | 2059 | 2054 |

Kart sayaçları `scores/scores.json`'dan (SCORES.md §5.2 ile aynı sayı): varyant sayacı aynı veri sürümündeki farklı backtest varyantları + keşif satırlarıdır; aile keşif sayacı günlükteki `kind: exploration` satırlarıdır (kaynak `docs/specs_faz7_c/ekler/denenenler.csv`, Fable Faz 7C denetimi F3); yan yana gösterilir, toplanmaz.

**Proje sahibinin sorusunun cevabı (yakın dönem, H99, tasarıma maruz):** `fall_d10_v0_pooled − fall_d10_v0_h99` (D10 Brier) = -0.0058 [-0.0340, +0.0219], n = 75 (22 ay) → **belirsiz**.

### Yakın dönem birincil hücresi (`pooled − h99`, D10 Brier, ilk işlem ≥ 2024-01-01) ve §6.2 konumu

| Hücre | n (ay) | pooled | h99 | fark | %95 aralık | pooled iyi / h99 iyi / eşit | Etiket | §6.2 beklenen (aynen) | §6.2 aralık (aynen) | §6.2 beklenen etiket (aynen) | Konum (T6) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `pooled − h99` **(BİRİNCİL)** | 75 (22) | 0.1624 | 0.1682 | -0.0058 | [-0.0340, +0.0219] | 33 / 42 / 0 (|fark| ≤ 1e-12: 0) | **belirsiz** | −0.002 | [−0.015, +0.012] | **"belirsiz"** ya da "tolerans içinde" | **aralık içinde** |

### İkincil hücreler (ilan edilmiş; aynı yakın dönem fold'ları) ve §6.2 konumu

| Aday | Karşılaştırılan | Ufuk | n (ay) | aday | karş. | fark | %95 aralık | aday iyi / karş. iyi / eşit | aralık | §6.2 satırı | §6.2 beklenen / aralık (aynen) | Konum (T6) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `fall_d10_v0_h99` | `base_rate` | D10 | 75 (22) | 0.1682 | 0.2116 | -0.0434 | [-0.0773, -0.0048] | 56 / 19 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın altında | `h99 − base_rate` (ikincil) | −0.025 [−0.055, +0.005] | **aralık içinde** |
| `fall_d10_v0_h99` | `base_rate` | D5 | 75 (22) | 0.1243 | 0.1648 | -0.0405 | [-0.0742, -0.0074] | 59 / 16 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın altında | — | — | — |
| `fall_d10_v0_h99` | `v1_5_h99` | D10 | 75 (22) | 0.1682 | 0.1737 | -0.0055 | [-0.0228, +0.0154] | 55 / 20 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor | her aday − `v1_5_h99` (ikincil) | +0.010 [−0.020, +0.040] | **aralık içinde** |
| `fall_d10_v0_pooled` | `base_rate` | D10 | 75 (22) | 0.1624 | 0.2116 | -0.0492 | [-0.0670, -0.0296] | 63 / 12 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın altında | `pooled − base_rate` (ikincil) | −0.025 [−0.055, +0.005] | **aralık içinde** |
| `fall_d10_v0_pooled` | `base_rate` | D5 | 75 (22) | 0.1340 | 0.1648 | -0.0308 | [-0.0495, -0.0170] | 62 / 13 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın altında | — | — | — |
| `fall_d10_v0_pooled` | `v1_5_h99` | D10 | 75 (22) | 0.1624 | 0.1737 | -0.0113 | [-0.0465, +0.0281] | 55 / 20 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor | her aday − `v1_5_h99` (ikincil) | +0.010 [−0.020, +0.040] | **aralık içinde** |
| `fall_d10_v0_addsale` | `base_rate` | D10 | 76 (22) | 0.2087 | 0.2153 | -0.0065 | [-0.0301, +0.0161] | 56 / 20 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor | `addsale − base_rate` (ikincil) | −0.005 [−0.020, +0.010] | **aralık içinde** |
| `fall_d10_v0_addsale` | `base_rate` | D5 | 76 (22) | 0.1699 | 0.1707 | -0.0008 | [-0.0186, +0.0153] | 60 / 16 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor | — | — | — |
| `fall_d10_v0_addsale` | `v1_5_h99` | D10 | 76 (22) | 0.2087 | 0.1782 | +0.0305 | [-0.0131, +0.0808] | 41 / 35 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor | her aday − `v1_5_h99` (ikincil) | +0.010 [−0.020, +0.040] | **aralık içinde** |
| `fall_d10_v0_pooled` | `fall_d10_v0_pooled@ZERO` | D10 | 75 (22) | 0.1624 | 0.2073 | -0.0449 | [-0.0629, -0.0262] | 61 / 14 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın altında | — | — | — |

Beklentiden çok iyi (T6: nokta §6.2 aralığının altında): yok. Her iki durumda da sıradaki adım Fable'ın bu şartnameden bağımsız, sıfırdan yeniden üretimidir.

### Merdiven (§5.4; yalnız pay, D10, aynı yakın dönem fold'ları)

- addsale → h99 (f1r ve ln f3'ün payı; eğitim kümeleri de farklı: H99 94 / havuz 165): `h99 − addsale` = -0.0341 [-0.0768, +0.0060], n = 75 (22 ay).
- h99 → pooled (eski verinin payı): `pooled − h99` = -0.0058 [-0.0340, +0.0219], n = 75 (22 ay).
- pooled@ZERO → pooled (özelliklerin payı): `pooled − pooled@ZERO` = -0.0449 [-0.0629, -0.0262], n = 75 (22 ay).

### Keşif (hüküm yok)

| Aday | Karşılaştırılan | Ufuk | Fold kümesi | n (ay) | aday | karş. | fark | %95 aralık | aday iyi / karş. iyi / eşit |
|---|---|---|---|---|---|---|---|---|---|
| `fall_d10_v0_h99` | `v1_5_h99` | D5 | yakın dönem | 75 (22) | 0.1243 | 0.1333 | -0.0089 | [-0.0245, +0.0068] | 57 / 18 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_pooled` | `v1_5_h99` | D5 | yakın dönem | 75 (22) | 0.1340 | 0.1333 | +0.0008 | [-0.0392, +0.0388] | 48 / 27 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_addsale` | `v1_5_h99` | D5 | yakın dönem | 76 (22) | 0.1699 | 0.1419 | +0.0280 | [-0.0197, +0.0795] | 30 / 46 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_pooled` | `fall_d10_v0_pooled@ZERO` | D5 | yakın dönem | 75 (22) | 0.1340 | 0.1623 | -0.0283 | [-0.0478, -0.0134] | 64 / 11 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_pooled` | `fall_d10_v0_h99` | D10 | 2023 fold'ları | 1 (1) | 0.6765 | 0.8599 | -0.1834 | — | 1 / 0 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_pooled` | `fall_d10_v0_h99` | D10 | bütün eşleşik fold'lar | 76 (23) | 0.1691 | 0.1773 | -0.0081 | [-0.0357, +0.0193] | 34 / 42 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_h99` | `base_rate` | D10 | 2023 fold'ları | 1 (1) | 0.8599 | 0.8622 | -0.0023 | — | 1 / 0 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_h99` | `base_rate` | D10 | bütün eşleşik fold'lar | 76 (23) | 0.1773 | 0.2201 | -0.0429 | [-0.0762, -0.0052] | 57 / 19 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_pooled` | `base_rate` | D10 | 2023 fold'ları | 7 (1) | 0.4730 | 0.6946 | -0.2216 | — | 5 / 2 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_pooled` | `base_rate` | D10 | bütün eşleşik fold'lar | 82 (23) | 0.1889 | 0.2528 | -0.0639 | [-0.0978, -0.0347] | 68 / 14 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_addsale` | `base_rate` | D10 | 2023 fold'ları | 7 (1) | 0.5131 | 0.6946 | -0.1815 | — | 5 / 2 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_addsale` | `base_rate` | D10 | bütün eşleşik fold'lar | 83 (23) | 0.2344 | 0.2557 | -0.0213 | [-0.0579, +0.0105] | 61 / 22 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_h99` | `v1_5_h99` | D10 | 2023 fold'ları | 1 (1) | 0.8599 | 0.8593 | +0.0006 | — | 0 / 1 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_h99` | `v1_5_h99` | D10 | bütün eşleşik fold'lar | 76 (23) | 0.1773 | 0.1827 | -0.0054 | [-0.0219, +0.0155] | 55 / 21 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_pooled` | `v1_5_h99` | D10 | 2023 fold'ları | 1 (1) | 0.6765 | 0.8593 | -0.1828 | — | 1 / 0 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_pooled` | `v1_5_h99` | D10 | bütün eşleşik fold'lar | 76 (23) | 0.1691 | 0.1827 | -0.0136 | [-0.0477, +0.0248] | 56 / 20 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_addsale` | `v1_5_h99` | D10 | 2023 fold'ları | 1 (1) | 0.8269 | 0.8593 | -0.0324 | — | 1 / 0 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_addsale` | `v1_5_h99` | D10 | bütün eşleşik fold'lar | 77 (23) | 0.2168 | 0.1870 | +0.0297 | [-0.0128, +0.0788] | 42 / 35 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_pooled` | `fall_d10_v0_pooled@ZERO` | D10 | 2023 fold'ları | 19 (4) | 0.2035 | 0.2071 | -0.0036 | — | 14 / 5 / 0 (|fark| ≤ 1e-12: 0) |
| `fall_d10_v0_pooled` | `fall_d10_v0_pooled@ZERO` | D10 | bütün eşleşik fold'lar | 94 (26) | 0.1707 | 0.2072 | -0.0366 | [-0.0551, -0.0185] | 75 / 19 / 0 (|fark| ≤ 1e-12: 0) |

### Fold özeti

- `fall_d10_v0_h99` — D10: 82 fold, FIT_OK 76, MODEL_NOT_FIT_SINGLE_CLASS 6; yakın dönem 75 FIT_OK fold (22 ay, olay 21); seçilen C (FIT_OK): 0.001: 3, 0.01: 10, 0.1: 3, 1.0: 59, 10.0: 1; f3 filtre dışlaması olan fold 0 (iç CV'de dışlama olan fold 0, skorlanmayan iç tutulan 0); test arzı kırpılan fold 28; ek satış sütunu sıfır varyansla düşen fold 0; eğitimdeki açık küme arzı 0…0. D5: 82 fold, FIT_OK 76, MODEL_NOT_FIT_SINGLE_CLASS 6; yakın dönem 75 FIT_OK fold (22 ay, olay 15); seçilen C (FIT_OK): 0.01: 8, 0.1: 3, 1.0: 49, 10.0: 16; f3 filtre dışlaması olan fold 0 (iç CV'de dışlama olan fold 0, skorlanmayan iç tutulan 0); test arzı kırpılan fold 24; ek satış sütunu sıfır varyansla düşen fold 0; eğitimdeki açık küme arzı 0…0.
- `fall_d10_v0_pooled` — D10: 94 fold, FIT_OK 94; yakın dönem 75 FIT_OK fold (22 ay, olay 21); seçilen C (FIT_OK): 1.0: 92, 10.0: 2; f3 filtre dışlaması olan fold 41 (iç CV'de dışlama olan fold 5, skorlanmayan iç tutulan 0); test arzı kırpılan fold 10; ek satış sütunu sıfır varyansla düşen fold 0; eğitimdeki açık küme arzı 60…67. D5: 94 fold, FIT_OK 94; yakın dönem 75 FIT_OK fold (22 ay, olay 15); seçilen C (FIT_OK): 0.1: 13, 1.0: 81; f3 filtre dışlaması olan fold 39 (iç CV'de dışlama olan fold 6, skorlanmayan iç tutulan 0); test arzı kırpılan fold 10; ek satış sütunu sıfır varyansla düşen fold 0; eğitimdeki açık küme arzı 62…67.
- `fall_d10_v0_addsale` — D10: 95 fold, FIT_OK 95; yakın dönem 76 FIT_OK fold (22 ay, olay 22); seçilen C (FIT_OK): 1.0: 95; f3 filtre dışlaması olan fold 0 (iç CV'de dışlama olan fold 0, skorlanmayan iç tutulan 0); test arzı kırpılan fold 0; ek satış sütunu sıfır varyansla düşen fold 0; eğitimdeki açık küme arzı 66…70. D5: 95 fold, FIT_OK 95; yakın dönem 76 FIT_OK fold (22 ay, olay 16); seçilen C (FIT_OK): 1.0: 93, 10.0: 2; f3 filtre dışlaması olan fold 0 (iç CV'de dışlama olan fold 0, skorlanmayan iç tutulan 0); test arzı kırpılan fold 0; ek satış sütunu sıfır varyansla düşen fold 0; eğitimdeki açık küme arzı 68…70.
- `fall_d10_v0_pooled@ZERO` — D10: 94 fold, FIT_OK 94; yakın dönem 75 FIT_OK fold (22 ay, olay 21); seçilen C (FIT_OK): ZERO: 94; f3 filtre dışlaması olan fold 41 (iç CV'de dışlama olan fold 0, skorlanmayan iç tutulan 0); test arzı kırpılan fold 0; eğitimdeki açık küme arzı 60…67. D5: 94 fold, FIT_OK 94; yakın dönem 75 FIT_OK fold (22 ay, olay 15); seçilen C (FIT_OK): ZERO: 94; f3 filtre dışlaması olan fold 39 (iç CV'de dışlama olan fold 0, skorlanmayan iç tutulan 0); test arzı kırpılan fold 0; eğitimdeki açık küme arzı 62…67.

### Nihai fit önizlemesi (dondurulmadı)

Dondurmanın kullanacağı fonksiyonla (`borsai/backtest.py: final_fit_fall`) bütün eğitim kümesinde; `models/`'e yazılmadı, dosyalar `tests/reference/macos_golden_faz7c/` altında (dondurma görevi bit-eşitliği `created_at`, `code_version` ve `runtime` dışında sınar). Katsayılar z-skorlu sütunlarda, p_up (P(kapanış > arz)) başlığınındır: pozitif katsayı düşme olasılığını azaltır.

| model_id | Ufuk | C | sabit | katsayılar | arz / olay | kırpma [p05, p95] (ham) | f3 filtre modu | dosya sha256 (ilk 12) |
|---|---|---|---|---|---|---|---|---|
| `fall_d10_v0_h99` | D5 | 1 | +2.4245 | f1r -1.0007, f3 +1.5284, add_sale -0.4451 | 94 / 18 | f1r [7.30435e+08, 6.11195e+09]; f3 [1.14774, 8.3635] | NOT_SPECIFIED | `a6c9e65eb567` |
| `fall_d10_v0_h99` | D10 | 1 | +1.4371 | f1r -0.8566, f3 +1.1093, add_sale -0.4207 | 94 / 26 | f1r [7.30435e+08, 6.11195e+09]; f3 [1.14774, 8.3635] | NOT_SPECIFIED | `a6c9e65eb567` |
| `fall_d10_v0_pooled` | D5 | 1 | +2.0526 | f1r -0.5850, f3 +0.9604, add_sale -0.8166 | 161 / 29 | f1r [5.71126e+08, 6.2468e+09]; f3 [1.15, 18.1] | NOT_SPECIFIED | `9e37a0fd3385` |
| `fall_d10_v0_pooled` | D10 | 1 | +1.4939 | f1r -0.5237, f3 +0.8520, add_sale -0.8028 | 161 / 39 | f1r [5.71126e+08, 6.2468e+09]; f3 [1.15, 18.1] | NOT_SPECIFIED | `9e37a0fd3385` |
| `fall_d10_v0_addsale` | D5 | 1 | +1.6113 | add_sale -0.6046 | 165 / 30 | — | — | `8c33da312573` |
| `fall_d10_v0_addsale` | D10 | 1 | +1.2082 | add_sale -0.6144 | 165 / 40 | — | — | `8c33da312573` |
| `fall_d10_v0_pooled@ZERO` | D5 | ZERO (kural) | p_up = 0.819876 | — | 161 / 29 | — | — | `883ab7b91329` |
| `fall_d10_v0_pooled@ZERO` | D10 | ZERO (kural) | p_up = 0.757764 | — | 161 / 39 | — | — | `883ab7b91329` |

### Faz 7C koşuları ve deney günlüğü

| Koşu | Plan | Fold (D10 + D5) | Ledger sha256 (ilk 12) | Günlükteki koşu sayısı |
|---|---|---|---|---|
| `fall_d10_v0_addsale` | fall_addsale | 190 | `6e93e4be713c` | 1 |
| `fall_d10_v0_h99` | fall_h99 | 164 | `01992680803f` | 1 |
| `fall_d10_v0_pooled` | fall_pooled | 188 | `e1c26cb68a26` | 1 |
| `fall_d10_v0_pooled@ZERO` | fall_pooled | 188 | `d08777b75c31` | 1 |

Keşif varyantları (§10; KARARLAR_C "Çokluk"): `docs/specs_faz7_c/ekler/denenenler.csv` (sha256 `25edc9a6e40c…`) günlükte 2054 `kind: exploration` satırı; veri sürümü v2 (`data/data_version_v2.json`), kart varyant sayacı bunları o sürümde sayar (SPEC_DEVIATIONS K). Model değildirler; dondurulmazlar.

V1.5 karşılaştırıcısının yeniden üretimi (§11-7): Faz 1A ledger'ından D10 Brier 0.1883 (81 fold; MODELS.md'deki 0.1883).

### Dondurma

**Donduruldu — bağımsız yeniden üretimden sonra.** İlk uygulamayı görmeyen ayrı bir oturum (Fable) şartnameden, `borsai` import etmeden sıfırdan yeniden üretti (2026-09-27, `docs/fable_faz7c_audit/AUDIT.md`, commit 80670cb): dört modelin sekiz ledger'ı alan alan birebir, p / sabit / katsayı / iç LOOCV tablosu **maks |Δ| = 0**; dört nihai fit önizlemesi ve bu bölümün hücreleri aynı; sızıntı yok; 16/16 mutasyon kırmızı; hüküm dördü için **FREEZE_OK**. Şartname gereği dört kimlik birlikte donduruldu (yakın dönem etiketi dondurma kararına girmez). Donmuş dosyalar yukarıdaki nihai fit önizlemelerinin aynısıdır (`created_at`, `code_version`, `runtime` dışında `==`); dondurma temiz ağaçta yapıldı (`borsai_dirty` false). Kayıtları `models/INDEX.json`'un **sonuna** eklendi, ilk 23 kayıt değişmedi; `models/INDEX_POST_D1.json` değişmedi. Şartname belgesi donmuş JSON'larda `spec.spec_document.sha256` = `d75c17cfec09…` (`docs/specs_faz7_c/SPEC_C_V0.md`). Ayrıntı ve ham çıktılar `docs/fable_faz7c_audit/`. Yukarıdaki "dondurulmadı" ifadeleri backtest anının kaydıdır.

| model_id | Dosya | sha256 | Dondurma (yerel saat; kanıt push'tur) | Rol |
|---|---|---|---|---|
| `fall_d10_v0_h99` | `models/fall_d10_v0_h99.json` | `b15eaa8cb1f76441088173e7582f636afe281855d924d23220d6ae076fe89beb` | 2026-09-28 | aday; kart seçimi (§5.5) kasa sonucunu bekler |
| `fall_d10_v0_pooled` | `models/fall_d10_v0_pooled.json` | `d2c5d549961173468486c159045c9d4361bd034e2a5c6bb5494aad68477f7c64` | 2026-09-28 | aday; kart seçimi (§5.5) kasa sonucunu bekler |
| `fall_d10_v0_addsale` | `models/fall_d10_v0_addsale.json` | `b95fc3ecee262f7b58441215d9c65ba682808c5a2cddd643f2e05f64640b8e09` | 2026-09-28 | aday; kart seçimi (§5.5) kasa sonucunu bekler |
| `fall_d10_v0_pooled@ZERO` | `models/fall_d10_v0_pooled@ZERO.json` | `7c23b9236c0a0ccc4192d8da58f0e1745fbd7443f1a6e78e2a056580fbfd8c3d` | 2026-09-28 | kural satırı (aday değil) |

- kasa: bekliyor (tavan serisi v1 ile birlikte tek seferde açılır) — SPEC_C_V0 §7.1. Eski kohortun (C) ek kayıtları (`--only-missing-models`, §7.1-3), model başına kapı (§7.3) ve `oot_pre_h99_sealed` kasa açılışından önce, sıradaki görevde (v1 ile birlikte).
- canlı n: dondurma commit'inden sonra listelenen arzlarla başlar; var olan 7 canlı kayıt (C) için RETRO (kayıtları (C) hücresi taşımaz; formülle). Zaman kanıtı dondurma commit'inin push'udur.
- Canlı kayıt girdileri (SPEC_DEVIATIONS K16): ek satış alanı V1.5 girdisidir, boşsa üç aday RET (KARARLAR_C C4); h99 ve pooled f3 ister (f3'süz RET, `registry.F3_MODELS`) ve T'nin ayı − 2'nin TÜFE'sini ister (ön koşul v1 ile ortak: ay dosyada yoksa kayıt yazılmaz); addsale f3 istemez, `@ZERO` girdi istemez.
- Uygulama birincili ve kart (§5.5, §9): seçim kasa sonucunu bekler; masaüstü uygulaması bu dört kaydı EK3'e kadar yok sayar (SPEC_DEVIATIONS K20). Skorlar bu görevde yeniden üretilmedi (K19); (C) skor hücreleri ve aile keşif sayacı (AUDIT F3) sıradaki skorlama görevinde.
- Denetim düzeltmeleri (aynı model_id): fold özetinin kural satırı (K17); bulgular F1–F9 SPEC_DEVIATIONS K3, K6, K9, K14, K16–K23.

## Faz 7: tavan serisi v1 (Fable şartnamesi, docs/specs_faz7/)

**Terazi ve ölçek:** aşağıdaki her sayı **backtest**tir (retrospektif walk-forward, H99 test arzları) ve **tasarıma maruzdur** (§10: gün grupları H99'dan, v0'ın H99 sonucu şartname yazılırken biliniyordu); kanıt değeri prospektif teraziden düşüktür. Ölçek koşulsuzdur (S_k, RPS; Faz 1B tavan tablolarıyla aynı ölçek, ama toplanmaz). Adaylar **henüz dondurulmadı** (Fable'ın sıfırdan yeniden üretiminden sonra ayrı görev); canlı sicilde satırları yoktur. Kasa terazisi bekliyor (KARARLAR K1: (C) şartnamesiyle birlikte, tek seferde).

Şartname: `docs/specs_faz7/SPEC_HAZARD_V1.md` (sha256 `25229cea8f6f…`, commit 6a16c16, push kanıtı 2026-09-25T18:09:45Z, uygulamadan önce) ve proje sahibi kararları `docs/specs_faz7/KARARLAR.md` (sha256 `eb6ac63cce3e…`; çeliştiği yerde bağlayıcı). Adaylar iç içe bir merdivendir: (a) `ceiling_hazard_v1_clip` — f1, f2, f3 eğitim [p05, p95]'ine kırpılır; (b) `ceiling_hazard_v1_real` — f1 yerine f1r = ln(büyüklük / (TÜFE_{T−2} / 100)), TÜİK TÜFE 2025=100; (c) `ceiling_hazard_v1_pooled` — f1r + H99 ve eski kohortun açık kümesi (165 arz) + cezasız rejim terimi r = 1[tahsis rejimi ≠ EQUAL_DIST_20230330] (canlıda 0). Kural satırı `ceiling_hazard_v1_pooled@INF` (gün + rejim sabitleri). `v1_clip@INF` ve `v1_real@INF` `ceiling_hazard_v0@INF` ile bit-eşittir, ayrıca kaydedilmez. Uygulama yorumları SPEC_DEVIATIONS J.

Planlar: `v1_clip` ve `v1_real` PLAN_CEILING'de (v0 ile aynı fold'lar ve ticker'lar); `v1_pooled` ve `@INF` PLAN_CEILING_POOLED'da (test arzları yine H99'un f3'lü 97'si; eğitim training_table_v2'nin seans tarihi < T olan bütün kişi-dönem satırları; bir eğitim kümesinde f3'ü filtre moduna açıkça zıt olan birim o kümede kullanılmaz — proje sahibi kararı, SPEC_DEVIATIONS J). Karşılaştırıcılar Faz 1B altın ledger'larından, yeniden koşulmaz.

Etiket ve karşılaştırma kuralları (sonuçlar görülmeden kodda sabitlendi, `borsai/report_faz7.py: OPERATIONAL_RULES_FAZ7` ve `borsai/backtest.py: near_era_label`, commit A):

- Birincil hücre (§5.1; her aday için bir tane): aday − `ceiling_hazard_v0`, RPS, ilk işlem ≥ 2024-01-01 olan fold'lar. v0 değerleri Faz 1B altın ledger'ından (`tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv`, sha256 `976b4dcea981…`; yeniden koşulmaz), fold ticker'ıyla eşleşir; iki tarafın da FIT_OK olduğu fold'lar sayılır.
- Etiket (§5.1): %95 aralığın alt ucu > 0 → **bozuyor** (aday yakın dönemde v0'dan kötü); üst ucu ≤ +0.010 → **tolerans içinde**; diğer → **belirsiz** (alt uç = 0 dışlamaz). Aralık SPEC_DEVIATIONS C7: ilk işlem ayı blokları, 4000 tekrar, `random.Random(20260921)`; RPS ve Brier kırpmasız (`borsai/backtest.py: near_era_label`, `paired_ceiling`).
- §6.2 konumu (görev kararı T6): gerçekleşen fark noktası §6.2'nin beklenen aralığı [alt, üst] (kapalı) içindeyse **aralık içinde**, altındaysa **altında — beklentiden çok iyi**, üstündeyse **üstünde**. Beklentiden çok iyi olsa da olmasa da sıradaki adım Fable'ın sıfırdan yeniden üretimidir (ledger'lar |Δ| ≤ 1e-9).
- Kazanç/kayıp/eşitlik: fold başına kayıp farkının işareti; fark bit-eşit 0 ise eşitlik (MODELS.md kuralı); |fark| ≤ 1e-12 eşitlik sayısı ayrıca yazılır (bağımsız yeniden fit bit-eşit eşitlik üretmez).
- İkincil hücreler (§5.1, ilan edilmiş): aynı fold'larda aday − `base_km_expanding` (v0 planının KM ledger'ı), aday − `ceiling_hazard_v0@INF`, Brier k ∈ {1, 3, 5, 10} (aday − v0). 2023 fold'ları ve havuz planının KM kuralları keşiftir.
- Merdiven (§5.4; yalnız bilgi, hüküm dili yok): aynı 78 fold'da `v1_clip − v0` (kırpmanın payı), `v1_real − v1_clip` (deflasyonun payı), `v1_pooled − v1_real` (havuz + rejimin payı).
- Proje sahibinin sorusu ("eski arzları eğitime katmak bugünkü tahminleri bozmaz mı?") `ceiling_hazard_v1_pooled`'ın birincil hücresinin etiketiyle cevaplanır; `v1_clip` ve `v1_real` hücreleri "dönüşüm yakın dönemi bozuyor mu" sorusunun cevabıdır. H99 tasarıma maruzdur (§10); kanıt değeri prospektif teraziden düşüktür.
- Kasa (§5.2, tek seferlik) ve canlı (§5.3) teraziler bu bölümde yoktur: kasa, (C) şartnamesiyle birlikte ve tek seferde açılır (KARARLAR K1); canlı n dondurmadan sonra listelenen arzlarla başlar. Uygulama birincil seçimi (§5.5, KARARLAR K4) kasa sonucunu bekler.

### Kartlar

| model_id | Basamak | Eğitim | Plan | Fold (FIT_OK) | Yakın dönem etiketi (birincil) | Kasa | Canlı | Varyant (aynı veri sürümü; `scores.json`) |
|---|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | (a) kırpma | H99_F3_PRESENT (97) | ceiling | 87 | **tolerans içinde** | kasa: bekliyor | n = 0 (dondurulmadı) | 23 |
| `ceiling_hazard_v1_real` | (b) reel büyüklük | H99_F3_PRESENT (97) | ceiling | 87 | **bozuyor** | kasa: bekliyor | n = 0 (dondurulmadı) | 23 |
| `ceiling_hazard_v1_pooled` | (c) havuz + rejim | H99_F3_PRESENT+OOT_OPEN_F3_PRESENT (165) | pooled | 97 | **bozuyor** | kasa: bekliyor | n = 0 (dondurulmadı) | 2059 |
| `ceiling_hazard_v1_pooled@INF` | kural satırı (λ = INF) | H99_F3_PRESENT+OOT_OPEN_F3_PRESENT (165) | pooled | 97 | bozuyor (kural satırı; aday değil) | kasa: bekliyor | n = 0 (dondurulmadı) | 2059 |

**Proje sahibinin sorusunun cevabı (yakın dönem, H99, tasarıma maruz):** `ceiling_hazard_v1_pooled` − v0 = +0.0289 [+0.0089, +0.0518], n = 78 (22 ay) → **bozuyor**.

### Yakın dönem birincil hücreleri (aday − `ceiling_hazard_v0`, RPS, ilk işlem ≥ 2024-01-01) ve §6.2 konumu

| Aday | n (ay) | aday | v0 | fark | %95 aralık | aday iyi / v0 iyi / eşit | Etiket | §6.2 beklenen (aynen) | §6.2 aralık (aynen) | §6.2 beklenen etiket (aynen) | Konum (T6) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v1_clip` **(BİRİNCİL)** | 78 (22) | 0.1427 | 0.1438 | -0.0011 | [-0.0066, +0.0049] | 46 / 32 / 0 (|fark| ≤ 1e-12: 0) | **tolerans içinde** | −0.003 | [−0.010, +0.005] | tolerans içinde | **aralık içinde** |
| `ceiling_hazard_v1_real` **(BİRİNCİL)** | 78 (22) | 0.1542 | 0.1438 | +0.0104 | [+0.0028, +0.0183] | 24 / 54 / 0 (|fark| ≤ 1e-12: 0) | **bozuyor** | −0.004 | [−0.015, +0.008] | tolerans içinde ya da belirsiz | **üstünde** |
| `ceiling_hazard_v1_pooled` **(BİRİNCİL)** | 78 (22) | 0.1728 | 0.1438 | +0.0289 | [+0.0089, +0.0518] | 25 / 53 / 0 (|fark| ≤ 1e-12: 0) | **bozuyor** | +0.002 | [−0.010, +0.015] | **belirsiz** olası; "bozuyor" beklenmiyor | **üstünde** |

§6.2'nin dördüncü satırı (ikincil): `ceiling_hazard_v1_pooled` − `base_km_expanding` = -0.0253 [-0.0386, -0.0099] (n = 78); §6.2 −0.05 [−0.08, −0.02] → **aralık içinde**.

Beklentiden çok iyi (T6: nokta §6.2 aralığının altında): yok. Her iki durumda da sıradaki adım Fable'ın bu şartnameden bağımsız, sıfırdan yeniden üretimidir.

Kural satırı `ceiling_hazard_v1_pooled@INF` − v0 (bilgi; aday değil): +0.0547 [+0.0287, +0.0806], n = 78.

### İkincil hücreler (ilan edilmiş; aynı yakın dönem fold'ları)

| Aday | Karşılaştırılan | Metrik | n (ay) | aday | karş. | fark | %95 aralık | aday iyi / karş. iyi / eşit | aralık |
|---|---|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | `base_km_expanding` | RPS | 78 (22) | 0.1427 | 0.1981 | -0.0554 | [-0.0826, -0.0283] | 52 / 26 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın altında |
| `ceiling_hazard_v1_clip` | `ceiling_hazard_v0@INF` | RPS | 78 (22) | 0.1427 | 0.1943 | -0.0516 | [-0.0765, -0.0265] | 54 / 24 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın altında |
| `ceiling_hazard_v1_clip` | `ceiling_hazard_v0` | Brier k = 1 | 78 (22) | 0.1289 | 0.1294 | -0.0004 | [-0.0023, +0.0016] | 49 / 29 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor |
| `ceiling_hazard_v1_clip` | `ceiling_hazard_v0` | Brier k = 3 | 78 (22) | 0.1500 | 0.1538 | -0.0038 | [-0.0142, +0.0037] | 53 / 25 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor |
| `ceiling_hazard_v1_clip` | `ceiling_hazard_v0` | Brier k = 5 | 78 (22) | 0.1804 | 0.1780 | +0.0024 | [-0.0087, +0.0177] | 56 / 22 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor |
| `ceiling_hazard_v1_clip` | `ceiling_hazard_v0` | Brier k = 10 | 78 (22) | 0.0932 | 0.0992 | -0.0060 | [-0.0222, +0.0049] | 49 / 29 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor |
| `ceiling_hazard_v1_real` | `base_km_expanding` | RPS | 78 (22) | 0.1542 | 0.1981 | -0.0439 | [-0.0692, -0.0170] | 47 / 31 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın altında |
| `ceiling_hazard_v1_real` | `ceiling_hazard_v0@INF` | RPS | 78 (22) | 0.1542 | 0.1943 | -0.0401 | [-0.0634, -0.0146] | 50 / 28 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın altında |
| `ceiling_hazard_v1_real` | `ceiling_hazard_v0` | Brier k = 1 | 78 (22) | 0.1343 | 0.1294 | +0.0049 | [-0.0003, +0.0104] | 57 / 21 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor |
| `ceiling_hazard_v1_real` | `ceiling_hazard_v0` | Brier k = 3 | 78 (22) | 0.1609 | 0.1538 | +0.0070 | [-0.0072, +0.0206] | 49 / 29 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor |
| `ceiling_hazard_v1_real` | `ceiling_hazard_v0` | Brier k = 5 | 78 (22) | 0.1907 | 0.1780 | +0.0127 | [-0.0015, +0.0272] | 31 / 47 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor |
| `ceiling_hazard_v1_real` | `ceiling_hazard_v0` | Brier k = 10 | 78 (22) | 0.1069 | 0.0992 | +0.0077 | [-0.0106, +0.0254] | 18 / 60 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor |
| `ceiling_hazard_v1_pooled` | `base_km_expanding` | RPS | 78 (22) | 0.1728 | 0.1981 | -0.0253 | [-0.0386, -0.0099] | 45 / 33 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın altında |
| `ceiling_hazard_v1_pooled` | `ceiling_hazard_v0@INF` | RPS | 78 (22) | 0.1728 | 0.1943 | -0.0216 | [-0.0347, -0.0062] | 44 / 34 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın altında |
| `ceiling_hazard_v1_pooled` | `ceiling_hazard_v0` | Brier k = 1 | 78 (22) | 0.1528 | 0.1294 | +0.0235 | [+0.0059, +0.0435] | 37 / 41 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın üstünde |
| `ceiling_hazard_v1_pooled` | `ceiling_hazard_v0` | Brier k = 3 | 78 (22) | 0.1998 | 0.1538 | +0.0459 | [+0.0169, +0.0854] | 21 / 57 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın üstünde |
| `ceiling_hazard_v1_pooled` | `ceiling_hazard_v0` | Brier k = 5 | 78 (22) | 0.2180 | 0.1780 | +0.0400 | [+0.0096, +0.0738] | 25 / 53 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın üstünde |
| `ceiling_hazard_v1_pooled` | `ceiling_hazard_v0` | Brier k = 10 | 78 (22) | 0.1047 | 0.0992 | +0.0056 | [-0.0199, +0.0327] | 17 / 61 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor |
| `ceiling_hazard_v1_pooled@INF` | `base_km_expanding` | RPS | 78 (22) | 0.1985 | 0.1981 | +0.0004 | [-0.0058, +0.0063] | 24 / 54 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor |
| `ceiling_hazard_v1_pooled@INF` | `ceiling_hazard_v0@INF` | RPS | 78 (22) | 0.1985 | 0.1943 | +0.0042 | [-0.0008, +0.0093] | 23 / 55 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor |
| `ceiling_hazard_v1_pooled@INF` | `ceiling_hazard_v0` | Brier k = 1 | 78 (22) | 0.1623 | 0.1294 | +0.0329 | [+0.0117, +0.0566] | 27 / 51 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın üstünde |
| `ceiling_hazard_v1_pooled@INF` | `ceiling_hazard_v0` | Brier k = 3 | 78 (22) | 0.2364 | 0.1538 | +0.0826 | [+0.0510, +0.1239] | 14 / 64 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın üstünde |
| `ceiling_hazard_v1_pooled@INF` | `ceiling_hazard_v0` | Brier k = 5 | 78 (22) | 0.2487 | 0.1780 | +0.0707 | [+0.0317, +0.1098] | 21 / 57 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ın üstünde |
| `ceiling_hazard_v1_pooled@INF` | `ceiling_hazard_v0` | Brier k = 10 | 78 (22) | 0.1161 | 0.0992 | +0.0169 | [-0.0242, +0.0555] | 25 / 53 / 0 (|fark| ≤ 1e-12: 0) | aralık 0'ı içeriyor |

### Merdiven (§5.4; yalnız pay, aynı yakın dönem fold'ları)

- kırpmanın payı (`v1_clip` − `ceiling_hazard_v0`): fark -0.0011 [-0.0066, +0.0049], n = 78 (22 ay).
- deflasyonun payı (`v1_real` − `v1_clip`): fark +0.0115 [+0.0045, +0.0190], n = 78 (22 ay).
- havuz + rejimin payı (`v1_pooled` − `v1_real`): fark +0.0185 [+0.0005, +0.0389], n = 78 (22 ay).

### Keşif (hüküm yok)

| Aday | Karşılaştırılan | Fold kümesi | n (ay) | aday | karş. | fark | %95 aralık | aday iyi / karş. iyi / eşit |
|---|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | `ceiling_hazard_v0` | 2023 fold'ları | 9 (2) | 0.1926 | 0.2066 | -0.0140 | — | 6 / 3 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_clip` | `ceiling_hazard_v0` | bütün eşleşik fold'lar | 87 (24) | 0.1479 | 0.1503 | -0.0024 | [-0.0079, +0.0036] | 52 / 35 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_real` | `ceiling_hazard_v0` | 2023 fold'ları | 9 (2) | 0.1944 | 0.2066 | -0.0122 | — | 6 / 3 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_real` | `ceiling_hazard_v0` | bütün eşleşik fold'lar | 87 (24) | 0.1584 | 0.1503 | +0.0081 | [+0.0006, +0.0159] | 30 / 57 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled` | `ceiling_hazard_v0` | 2023 fold'ları | 9 (2) | 0.2169 | 0.2066 | +0.0103 | — | 4 / 5 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled` | `ceiling_hazard_v0` | bütün eşleşik fold'lar | 87 (24) | 0.1773 | 0.1503 | +0.0270 | [+0.0076, +0.0486] | 29 / 58 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled@INF` | `ceiling_hazard_v0` | 2023 fold'ları | 9 (2) | 0.2351 | 0.2066 | +0.0285 | — | 5 / 4 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled@INF` | `ceiling_hazard_v0` | bütün eşleşik fold'lar | 87 (24) | 0.2023 | 0.1503 | +0.0520 | [+0.0268, +0.0761] | 31 / 56 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled` | `base_km_expanding__pooled` (havuz planı) | yakın dönem | 78 (22) | 0.1728 | 0.1929 | -0.0201 | [-0.0365, -0.0013] | 45 / 33 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled` | `base_km_expanding__pooled` (havuz planı) | bütün fold'lar | 97 (26) | 0.1729 | 0.1946 | -0.0217 | [-0.0395, -0.0021] | 53 / 44 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled` | `base_km_expanding__pooled` (havuz planı) | 2023 fold'ları | 19 (4) | 0.1737 | 0.2016 | -0.0280 | — | 8 / 11 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled` | `base_km_last10__pooled` (havuz planı) | yakın dönem | 78 (22) | 0.1728 | 0.1937 | -0.0210 | [-0.0527, +0.0151] | 38 / 40 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled` | `base_km_last10__pooled` (havuz planı) | bütün fold'lar | 97 (26) | 0.1729 | 0.1968 | -0.0238 | [-0.0502, +0.0073] | 50 / 47 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled` | `base_km_last10__pooled` (havuz planı) | 2023 fold'ları | 19 (4) | 0.1737 | 0.2092 | -0.0356 | — | 12 / 7 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled@INF` | `base_km_expanding__pooled` (havuz planı) | yakın dönem | 78 (22) | 0.1985 | 0.1929 | +0.0057 | [-0.0064, +0.0166] | 29 / 49 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled@INF` | `base_km_expanding__pooled` (havuz planı) | bütün fold'lar | 97 (26) | 0.1982 | 0.1946 | +0.0037 | [-0.0124, +0.0190] | 36 / 61 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled@INF` | `base_km_expanding__pooled` (havuz planı) | 2023 fold'ları | 19 (4) | 0.1971 | 0.2016 | -0.0046 | — | 7 / 12 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled@INF` | `base_km_last10__pooled` (havuz planı) | yakın dönem | 78 (22) | 0.1985 | 0.1937 | +0.0048 | [-0.0235, +0.0375] | 34 / 44 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled@INF` | `base_km_last10__pooled` (havuz planı) | bütün fold'lar | 97 (26) | 0.1982 | 0.1968 | +0.0015 | [-0.0224, +0.0287] | 42 / 55 / 0 (|fark| ≤ 1e-12: 0) |
| `ceiling_hazard_v1_pooled@INF` | `base_km_last10__pooled` (havuz planı) | 2023 fold'ları | 19 (4) | 0.1971 | 0.2092 | -0.0122 | — | 8 / 11 / 0 (|fark| ≤ 1e-12: 0) |

### Fold özeti

- `ceiling_hazard_v1_clip`: 87 fold, FIT_OK 87; yakın dönem 78 FIT_OK fold (22 ay); seçilen λ (FIT_OK): 0.1: 18, 1: 12, 3: 21, 10: 36; test arzı kırpılan fold (herhangi bir özellik, §3.1): 35 (f3 kırpılan: 20).
- `ceiling_hazard_v1_real`: 87 fold, FIT_OK 87; yakın dönem 78 FIT_OK fold (22 ay); seçilen λ (FIT_OK): 0.1: 20, 1: 10, 3: 21, 10: 36; test arzı kırpılan fold (herhangi bir özellik, §3.1): 36 (f3 kırpılan: 20).
- `ceiling_hazard_v1_pooled`: 97 fold, FIT_OK 97; yakın dönem 78 FIT_OK fold (22 ay); seçilen λ (FIT_OK): 10: 97; test arzı kırpılan fold (herhangi bir özellik, §3.1): 23 (f3 kırpılan: 7). δ (rejim) > 0 / < 0: 97 / 0. f3 filtre dışlaması olan fold: 44; eğitimdeki açık küme arzı sayıları [65, 68].
- `ceiling_hazard_v1_pooled@INF`: 97 fold, FIT_OK 97; yakın dönem 78 FIT_OK fold (22 ay); seçilen λ (FIT_OK): INF: 97; test arzı kırpılan fold (herhangi bir özellik, §3.1): 0. δ (rejim) > 0 / < 0: 97 / 0. f3 filtre dışlaması olan fold: 44; eğitimdeki açık küme arzı sayıları [65, 68].

### Nihai fit önizlemesi (dondurulmadı)

Dondurmanın kullanacağı fonksiyonla (`borsai/backtest.py: final_fit_v1`) bütün eğitim kümesinde; `models/`'e yazılmadı, dosyalar `tests/reference/macos_golden_faz7/` altında (dondurma görevi bit-eşitliği `created_at`, `code_version` ve `runtime` dışında sınar).

| model_id | λ | γ (g1, g2, g3) | β | δ (rejim) | arz / satır / olay | kırpma [p05, p95] (ham) | dosya sha256 (ilk 12) |
|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | 10 | -1.8191, -2.1417, -0.9953 | f1 +0.4634, f2 -0.1795, f3 -0.5611 | — | 97 / 506 / 83 | f1 [5.214e+08, 4.88799e+09]; f2 [11.1619, 35.1166]; f3 [1.14871, 8.332] | `18fdfb92d286` |
| `ceiling_hazard_v1_real` | 10 | -1.7659, -2.1292, -1.0813 | f1r +0.2645, f2 -0.2530, f3 -0.5267 | — | 97 / 506 / 83 | f1r [7.31271e+08, 6.09189e+09]; f2 [11.1619, 35.1166]; f3 [1.14871, 8.332] | `212a4075da6c` |
| `ceiling_hazard_v1_pooled` | 10 | -2.1155, -2.2445, -1.5441 | f1r +0.2265, f2 -0.1727, f3 -0.4959 | +0.9111 | 165 / 880 / 142 | f1r [5.65833e+08, 6.23722e+09]; f2 [15.0127, 37.543]; f3 [1.1616, 18.02] | `4fab0d630259` |
| `ceiling_hazard_v1_pooled@INF` | INF | -1.7832, -2.0499, -1.5279 | — | +0.2277 | 165 / 880 / 142 | — | `88c069584f72` |

### Faz 7 koşuları ve deney günlüğü

| Koşu | Plan | Fold | Ledger sha256 (ilk 12) | Günlükteki koşu sayısı |
|---|---|---|---|---|
| `base_km_expanding__pooled` | pooled | 97 | `cd77d9fec3d6` | — (`ceiling_hazard_v1_pooled` satırında) |
| `base_km_last10__pooled` | pooled | 97 | `e93ffc42a75e` | — (`ceiling_hazard_v1_pooled` satırında) |
| `ceiling_hazard_v1_clip` | ceiling | 87 | `22057c06f683` | 2 |
| `ceiling_hazard_v1_pooled` | pooled | 97 | `e165cafe26ee` | 2 |
| `ceiling_hazard_v1_pooled@INF` | pooled | 97 | `08cec307684d` | 2 |
| `ceiling_hazard_v1_real` | ceiling | 87 | `e97a67f4246e` | 2 |

v0 karşılaştırıcısının yeniden üretimi (§11-8): Faz 1B ledger'ından 87 fold ortalama RPS 0.1503 (MODELS.md'deki 0.1503).

### Dondurma

**Donduruldu — bağımsız yeniden üretimden sonra.** İlk uygulamayı görmeyen ayrı bir oturum (Fable) şartnameden, `borsai` import etmeden sıfırdan yeniden üretti (2026-09-26, `docs/fable_faz7_audit/AUDIT.md`, commit eda9732): altı ledger'da durum ve seçilen λ birebir, sayılarda **maks |Δ| = 4.3e-11** (eşik 1e-9); dört nihai fit önizlemesi ve bu bölümün 52 basılı hücresi aynı; sızıntı yok; hüküm dördü için **FREEZE_OK**. §6.4 gereği dört kimlik birlikte donduruldu (etiketler dondurma kararına girmez). Donmuş dosyalar yukarıdaki nihai fit önizlemelerinin aynısıdır (`created_at`, `code_version`, `runtime` dışında `==`); dondurma temiz ağaçta yapıldı (`borsai_dirty` false). Kayıtları `models/INDEX.json`'un **sonuna** eklendi, ilk 19 kayıt değişmedi; `models/INDEX_POST_D1.json` değişmedi. Ayrıntı ve ham çıktılar `docs/fable_faz7_audit/`. Yukarıdaki "dondurulmadı" ifadeleri backtest anının kaydıdır.

| model_id | Dosya | sha256 | Dondurma (yerel saat; kanıt push'tur) | Uygulama birincili |
|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | `models/ceiling_hazard_v1_clip.json` | `f3a147535242f8bde381ea68113f295f0a7dcdb5dd8a1046a3c1a55b0308241d` | 2026-09-27 | kasa sonucunu bekler |
| `ceiling_hazard_v1_real` | `models/ceiling_hazard_v1_real.json` | `d81dad3d60c18ba23298d0ca4c4e315b60cc665d34781ca52f06d001d21ba09d` | 2026-09-27 | §5.5 k3: olamaz |
| `ceiling_hazard_v1_pooled` | `models/ceiling_hazard_v1_pooled.json` | `e03e71e0bb6e7c65ceb9cdf0ee95b25334749362549428077ab670dd3f261402` | 2026-09-27 | §5.5 k3: olamaz |
| `ceiling_hazard_v1_pooled@INF` | `models/ceiling_hazard_v1_pooled@INF.json` | `7d7c9d1ee5a6a0c255fcf98103f872239439436a9e2da478601837d5eaf3f361` | 2026-09-27 | kural satırı |

- kasa: bekliyor ((C) şartnamesiyle birlikte açılır) — KARARLAR K1, §7.1. Eski kohortun dört modelli ikinci kayıtları (`--only-missing-models`, §7.1-3) ve model başına kapı (§7.3) kasa açılışından önce, sıradaki görevde.
- canlı n: dondurma commit'inden sonra listelenen arzlarla başlar; var olan 7 canlı kayıt v1 için RETRO (2026-08-18 … 09-17 arzları; kayıtları v1 hücresi taşımaz, model commit'i sonuçlarından sonra; formülle). Zaman kanıtı dondurma commit'inin push'udur.
- Uygulama birincili (§5.5): `ceiling_hazard_v1_real` ve `ceiling_hazard_v1_pooled` için §5.5 k3: uygulama birincili olamaz (yakın dönem etiketi "bozuyor"); `ceiling_hazard_v1_clip` için seçim kasa sonucunu bekler; `ceiling_hazard_v0` öne çıkarılmaya devam eder. Masaüstü uygulaması bu dört kaydı EK3'e kadar yok sayar (SPEC_DEVIATIONS J31).
- Canlı kayıt girdileri (SPEC_DEVIATIONS J26): real ve pooled T'nin ayı − 2'nin TÜFE'sini ister; o ay dosyada yoksa kayıt yazılmaz (aylık ekleme `docs/PROVENANCE.md` §11a; ilk gerçek ekleme Eylül 2026, Kasım arzları için); canlıda rejim r = 0.
- Denetim düzeltmesi (aynı model_id, J23): test arzı kırpma bayrağı herhangi bir sütunu sayar (§3.1); fold özetindeki 35 / 36 / 23 bu düzeltmeden sonradır. λ notu (J29): `v1_pooled`'ın λ = 10'u ızgaranın iç noktasıdır.

## Faz 5: D1 sonrası güncelleme (Fable şartnamesi, docs/specs_faz5/)

**Terazi ve ölçek:** aşağıdaki her sayı **backtest**tir (retrospektif walk-forward, H99) ve **tasarıma maruzdur** (§10); kanıt değeri düşüktür, asıl ölçüm prospektiftir. Bütün hücreler **koşullu ölçektedir** ("bugün D1 tavan kapandı", j = 1, `scale = backtest_conditional`): koşulsuz tablolarla (yukarıdaki Faz 1A/1B/4 bölümleri) **toplanmaz ve karşılaştırılmaz**. Model **dondurulmadı** (Fable'ın sıfırdan yeniden üretiminden sonra ayrı görev); canlı sicilde satırı yoktur. "Geçiyor" yalnız aralık 0'ı dışlıyorsa ve yalnız "backtest'te geçiyor (tasarıma maruz)" biçiminde yazılır.

Şartname: `docs/specs_faz5/SPEC_POST_D1_V0.md` (sha256 `a5b4675d8478…`, commit c20c092, push kanıtı 2026-09-24T00:44:25Z, uygulamadan önce). Model: dondurulmuş `ceiling_hazard_v0`'ın doğrusal öngörücüsü sabit ofset; d = 2..10 hazard'ına δ·u, u = z-skorlu (`d1_lock`, `d1_turnover`); h_1 ana modelden aynen; λ ∈ {0.1 … 1000, INF}, iç arz-bırak CV. λ = INF ucu karşılaştırıcının kendisidir.

Plan `H99_POST_D1_PP_WALK_FORWARD_T_CUTOFF_F3_PRESENT_L_GE_1_MIN10IPO_5EV_5SV`: fold kümesi ve sırası Faz 1B tavan ledger'ınınki (`976b4dcea981`); test arzı L ≥ 1 değilse `NOT_APPLICABLE`; ofset o fold'un yeniden koşulan `ceiling_hazard_v0` fit'i (γ, β, λ ve test hazard'ları ledger'la |Δ| ≤ 1e-9, aksi halde koşu durur); δ eğitim kümesi fold'un d ≥ 2 satırları, D1 ön işlemesi fold içinde. Karşılaştırıcı ve kurallar aynı fold'un Faz 1B ledger satırından (yeniden koşulmaz). Eşleşik fark = model − karşılaştırılan, iki tarafın da skorlandığı L ≥ 1 test arzları; %95 aralık blok bootstrap (ilk işlem ayı blokları, 4000 tekrar, `random.Random(20260921)`; SPEC_DEVIATIONS C7); koşullu RPS/Brier kırpmasız, p_up Brier [0.01, 0.99].

Etiket kuralları (sonuçlar görülmeden kodda sabitlendi, `borsai/report_faz5.py: OPERATIONAL_RULES_FAZ5`, commit A):

- Fark satırlarında (§5 tablosunun ilk 12 satırı) beklenen fark [alt, üst] kapalı aralıktır; "(nokta ≈ x)" bilgi amaçlıdır, değerlendirilmez. Fark = model − karşılaştırılan, negatif = model iyi. Fark alt ucun altındaysa **tutmadı (daha iyi)**, üst ucun üstündeyse **tutmadı (daha kötü)**.
- Fark aralık içindeyse "Aralık 0'ı" ifadesinin kesin kısmına bakılır: "içerir" → %95 aralık 0'ı içermeli; "dışlar" → aralığın üst ucu < 0; "içerir ya da negatif dışlar" → alt uç ≤ 0 (aralık 0'ı pozitif tarafta dışlamıyor); "dışlaması olası" / "dışlayabilir" / "dışlar (olası)" → alt uç ≤ 0; "büyük olasılıkla içerir" → kesin kısım yok. Kesin kısım tutuyorsa **tuttu**, tutmuyorsa **tutmadı (aralık)**. İfadenin tamamı (olasılık kısmı dahil: "dışlaması olası" → üst uç < 0; "büyük olasılıkla içerir" → 0'ı içerir) ayrı sütunda yazılır.
- Kalibrasyon satırı: |ort(h_2) − gözlenen D2 kırılma oranı| ≤ 0.05 → tuttu; h_2 = ledger'daki hazard_2, gözlenen = 1[L = 1] ortalaması, modelin FIT_OK fold'larında.
- λ nihai fit: seçilen λ ∈ [10, 100] → tuttu; λ = INF → tuttu ("INF olası" dendi); diğer λ → tutmadı (daha küçük / daha büyük).
- λ fold'lar (iki parça): "erken fold'larda INF" = kronolojik ilk 20 FIT_OK fold'un > %50'sinde INF; "fold'ların %20–50'sinde INF" = FIT_OK fold'larda INF payı [0.20, 0.50]. İkisi tutarsa tuttu, hiçbiri tutmazsa tutmadı, aksi halde kısmen (tutmayan parça adıyla).
- δ_lock işareti (iki parça): nihai fit'te δ_lock < 0; λ < INF olan FIT_OK fold'lardan d1_lock'un düşmediklerinde δ_lock < 0 payı ≥ %80 (düşen fold'lar paydada değil, ayrıca sayılır). Çok parça kuralı yukarıdaki gibi.
- δ_turn işareti: nihai fit'te δ_turn > 0 → tuttu; aksi halde tutmadı (< 0 ya da = 0 yönüyle).
- n (fold): birincil hücrenin eşleşik n'i [65, 71] → tuttu.
- Kazanç/kayıp/eşitlik: arz başına kayıp farkının işareti; fark bit-eşit 0 ise eşitlik (MODELS.md kuralı). Eşleşik küme: iki tarafın da skorlandığı (L ≥ 1) test arzları, ticker ile; karşılaştırılanın S_1 = 0 olduğu çift o hücreden düşer.
- Başarısızlık (a): birincil hücre aralığının alt ucu > 0. (b): nihai fit'te λ = INF ya da δ fit'i yapılan (FIT_OK) fold'ların ≥ %80'inde INF (INSUFFICIENT_TRAINING_HISTORY ve NOT_APPLICABLE paydada değil). (c): n ≥ 30 iken |ort(h_2) − gözlenen D2 kırılma oranı| > 0.1. (d): λ = INF fold'larında modelin S_cond'u aynı fold'un karşılaştırıcı S_cond'una bit-eşit değil ya da herhangi bir FIT_OK fold'da h_1 ana modelinkine (Faz 1B ledger'ı hazard_1) bit-eşit değil.
- Beklentiden çok iyi (§5): birincil fark < -0.040 ya da birincil aralığın üst ucu < -0.020 ya da Brier k = 2 farkı (`ceiling_hazard_v0` koşullu) < -0.040. Tetiklense de tetiklenmese de sıradaki adım Fable'ın sıfırdan yeniden üretimidir (ledger'lar |Δ| ≤ 1e-9).
- Canlı akış koşulu (proje sahibi kararı 3): (b) gerçekleşirse canlı POST_D1 akışı şimdi **kurulmaz**; λ sonlu ve (b) yoksa **kurulur**. Model her iki durumda da dondurulur (ayrı görev).
- "Kazanç en olası Brier k = 2'de" cümlesi: `ceiling_hazard_v0` koşullu karşısındaki dört hücreden (RPS_1, Brier k = 2, k = 3, k = 10) en negatif fark Brier k = 2'deyse tuttu.

### Birincil hücre

`post_d1_hazard_v0` − `ceiling_hazard_v0` koşullu, koşullu RPS_1 (k = 2..10; önceden ilan edilen tek birincil hücre): **fark -0.0105, %95 aralık [-0.0264, +0.0058], n = 70** (22 ay); model 0.1591, karşılaştırıcı 0.1695; model iyi / karşılaştırıcı iyi / eşit 38 / 30 / 2. Hüküm (backtest): ayırt edilemiyor (aralık 0'ı içeriyor). §5 beklentisi −0.020 … +0.003 → **tuttu**.

### Başarısızlık tanımları (§5) ve canlı akış koşulu

- **(a) D1 bilgisi zarar veriyor** (birincil aralık tamamen 0'ın üstünde): -0.0105 [-0.0264, +0.0058] → gerçekleşmedi.
- **(b) D1 bilgisi eklemiyor** (nihai fit'te λ = INF, ya da δ fit'i yapılan fold'ların ≥ %80'inde INF): nihai λ = 30; INF 2/70 FIT_OK fold (%3); paydada olmayanlar: INSUFFICIENT_TRAINING_HISTORY 1, NOT_APPLICABLE 16 → gerçekleşmedi.
- **(c) Kalibrasyon** (n ≥ 30 iken |ort(h_2) − gözlenen D2 kırılma oranı| > 0.10): ort(h_2) 0.1556, gözlenen 0.1571, |fark| 0.0015, n = 70 → gerçekleşmedi.
- **(d) Parite hatası** (INF ucu karşılaştırıcıya ya da h_1 ana modele bit-eşit değil): λ = INF fold'larında maks |S_cond − karşılaştırıcı S_cond| = 0.0 (2 fold); h_1 ≠ ana model: 0 fold → gerçekleşmedi.
- (e) Prospektif (n ≥ 30): birincil aralık 0'ı pozitif tarafta dışlıyor → "geçemiyor". Canlı n = 0; hüküm yok.

**Canlı akış koşulu (proje sahibi kararı 3): kurulur** — λ sonlu ve (b) yok; canlı POST_D1 akışı (dondurma ve Fable yeniden üretiminden sonra) kurulur.

**Beklentiden çok iyi denetimi (§5):** **TETİKLENDİ** (Brier k = 2 farkı -0.0512 < -0.040). Her iki durumda da sıradaki adım Fable'ın bu şartnameden bağımsız, sıfırdan yeniden üretimidir (ledger'lar |Δ| ≤ 1e-9).

### §5 beklentisi ile gerçekleşen (satır satır)

| Hücre | Karşılaştırılan | Beklenen (§5, aynen) | Aralık 0'ı (§5, aynen) | Gerçekleşen | %95 aralık | n | Etiket | Aralık ifadesi gerçekleşti mi |
|---|---|---|---|---|---|---|---|---|
| RPS_1 (BİRİNCİL) | `ceiling_hazard_v0` koşullu | −0.020 … +0.003 (nokta ≈ −0.008) | büyük olasılıkla içerir → "ayırt edilemiyor" | -0.0105 | [-0.0264, +0.0058] | 70 | **tuttu** | evet |
| RPS_1 | `ceiling_hazard_v0@INF` koşullu | −0.055 … −0.015 | dışlaması olası | -0.0417 | [-0.0806, -0.0009] | 70 | tuttu | evet |
| RPS_1 | `base_km_expanding` koşullu | −0.060 … −0.020 | dışlaması olası | -0.0481 | [-0.0892, -0.0050] | 70 | tuttu | evet |
| RPS_1 | `base_km_last10` koşullu | −0.065 … −0.025 | dışlaması olası | -0.0527 | [-0.0934, -0.0116] | 70 | tuttu | evet |
| RPS_1 | her-zaman-tavan | −0.42 … −0.36 | dışlar | -0.4108 | [-0.5150, -0.2902] | 70 | tuttu | evet |
| Brier k = 2 | `ceiling_hazard_v0` koşullu | −0.025 … 0.000 (nokta ≈ −0.010) | içerir ya da negatif dışlar; kazanç en olası bu hücrede | -0.0512 | [-0.1010, -0.0097] | 70 | tutmadı (daha iyi) | evet |
| Brier k = 2 | `@INF` koşullu | −0.040 … −0.010 | dışlayabilir | -0.0651 | [-0.1300, -0.0110] | 70 | tutmadı (daha iyi) | evet |
| Brier k = 2 | `base_km_last10` koşullu | −0.065 … −0.030 | dışlar (olası) | -0.0916 | [-0.1530, -0.0353] | 70 | tutmadı (daha iyi) | evet |
| Brier k = 10 | `ceiling_hazard_v0` koşullu | −0.006 … +0.006 | içerir | +0.0095 | [-0.0034, +0.0233] | 70 | tutmadı (daha kötü) | evet |
| Brier k = 3 (keşif) | `ceiling_hazard_v0` koşullu | −0.020 … +0.003 | içerir | -0.0342 | [-0.0745, +0.0042] | 70 | tutmadı (daha iyi) | evet |
| `path_conditional` h = 5 MAE | `ceiling_path_v0` koşullu (j = 1) | −0.015 … +0.005 | içerir | -0.0086 | [-0.0317, +0.0130] | 70 | tuttu | evet |
| `path_conditional` h = 3 p_up Brier | `ceiling_path_v0` koşullu | −0.015 … +0.005 | içerir | +0.0073 | [-0.0288, +0.0510] | 70 | tutmadı (daha kötü) | evet |
| Kalibrasyon | ort(h_2) − gözlenen D2 kırılma oranı | \|Δ\| ≤ 0.05 | — | ort(h_2) 0.1556 − gözlenen 0.1571 = -0.0015 (n = 70) | — |  | tuttu | — |
| λ | nihai fit | 10–100 en olası; INF olası | — | λ = 30.0 | — |  | tuttu | — |
| λ | fold'lar | erken fold'larda INF; fold'ların %20–50'sinde INF | — | INF 2/70 FIT_OK fold (%3); ilk 20 fold'da INF 2 (%10) | — |  | tutmadı | — |
| δ_lock işareti | nihai fit ve λ < INF fold'ları | < 0 (fold'ların ≥ %80'inde) | — | nihai δ_lock = -0.3279; λ < INF fold'larında < 0: 63/63 (d1_lock düşen: 5) | — |  | tuttu | — |
| δ_turn işareti | nihai fit | > 0 (düşük güven; ters çıkabilir) | — | nihai δ_turn = +0.2511; λ < INF fold'larında > 0 / < 0: 68 / 0 | — |  | tuttu | — |
| n (fold) | — | 65–71 | — | n = 70 | — |  | tuttu | — |

Etiket sayıları: tuttu 11, tutmadı 7, kısmen 0 (toplam 18).

"Hangi hücrede kazanç en olası: **Brier k = 2**" cümlesi (`ceiling_hazard_v0` koşullu karşısında fark): RPS_1 -0.0105, Brier k = 2 -0.0512, k = 3 -0.0342, k = 10 +0.0095 → **tuttu**.

### Bütün §4 hücreleri (koşullu ölçek, j = 1; birincil dışındakiler kural/ikincil/keşif)

| Metrik | Karşılaştırılan | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| RPS_1 (k = 2..10) | `ceiling_hazard_v0` koşullu (karşılaştırıcı) **(BİRİNCİL)** | 70 (22) | 0.1591 | 0.1695 | -0.0105 | [-0.0264, +0.0058] | 38 / 30 / 2 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| RPS_1 (k = 2..10) | `base_km_expanding` koşullu | 70 (22) | 0.1591 | 0.2072 | -0.0481 | [-0.0892, -0.0050] | 43 / 27 / 0 | **backtest'te geçiyor (tasarıma maruz)** |
| RPS_1 (k = 2..10) | `base_km_last10` koşullu | 70 (22) | 0.1591 | 0.2118 | -0.0527 | [-0.0934, -0.0116] | 41 / 29 / 0 | **backtest'te geçiyor (tasarıma maruz)** |
| RPS_1 (k = 2..10) | `ceiling_hazard_v0@INF` koşullu | 70 (22) | 0.1591 | 0.2007 | -0.0417 | [-0.0806, -0.0009] | 43 / 27 / 0 | **backtest'te geçiyor (tasarıma maruz)** |
| RPS_1 (k = 2..10) | `base_always_ceiling` (S_cond ≡ 1) | 70 (22) | 0.1591 | 0.5698 | -0.4108 | [-0.5150, -0.2902] | 59 / 11 / 0 | **backtest'te geçiyor (tasarıma maruz)** |
| Brier k = 2 | `ceiling_hazard_v0` koşullu (karşılaştırıcı) | 70 (22) | 0.0784 | 0.1296 | -0.0512 | [-0.1010, -0.0097] | 50 / 18 / 2 | **backtest'te geçiyor (tasarıma maruz)** |
| Brier k = 2 | `base_km_expanding` koşullu | 70 (22) | 0.0784 | 0.1426 | -0.0642 | [-0.1199, -0.0169] | 53 / 17 / 0 | **backtest'te geçiyor (tasarıma maruz)** |
| Brier k = 2 | `base_km_last10` koşullu | 70 (22) | 0.0784 | 0.1700 | -0.0916 | [-0.1530, -0.0353] | 42 / 28 / 0 | **backtest'te geçiyor (tasarıma maruz)** |
| Brier k = 2 | `ceiling_hazard_v0@INF` koşullu | 70 (22) | 0.0784 | 0.1435 | -0.0651 | [-0.1300, -0.0110] | 46 / 24 / 0 | **backtest'te geçiyor (tasarıma maruz)** |
| Brier k = 2 | `base_always_ceiling` (S_cond ≡ 1) | 70 (22) | 0.0784 | 0.1571 | -0.0787 | [-0.1557, -0.0129] | 11 / 59 / 0 | **backtest'te geçiyor (tasarıma maruz)** |
| Brier k = 10 | `ceiling_hazard_v0` koşullu (karşılaştırıcı) | 70 (22) | 0.1402 | 0.1307 | +0.0095 | [-0.0034, +0.0233] | 33 / 35 / 2 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| Brier k = 10 | `base_km_expanding` koşullu | 70 (22) | 0.1402 | 0.1361 | +0.0042 | [-0.0493, +0.0640] | 44 / 26 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| Brier k = 10 | `base_km_last10` koşullu | 70 (22) | 0.1402 | 0.1350 | +0.0053 | [-0.0535, +0.0683] | 42 / 28 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| Brier k = 10 | `ceiling_hazard_v0@INF` koşullu | 70 (22) | 0.1402 | 0.1364 | +0.0038 | [-0.0501, +0.0631] | 43 / 27 / 0 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| Brier k = 10 | `base_always_ceiling` (S_cond ≡ 1) | 70 (22) | 0.1402 | 0.8571 | -0.7169 | [-0.8385, -0.5693] | 60 / 10 / 0 | **backtest'te geçiyor (tasarıma maruz)** |

Kalibrasyon (ikincil; modelin FIT_OK fold'ları, L ≥ 1): ort(h_2) model 0.1556 / karşılaştırıcı 0.0916 / gözlenen D2 kırılma oranı 0.1571. k = 2: ort(S_cond) model 0.8444 / karşılaştırıcı 0.9084 / gözlenen 0.8429; k = 3: ort(S_cond) model 0.7595 / karşılaştırıcı 0.8316 / gözlenen 0.7857; k = 5: ort(S_cond) model 0.5024 / karşılaştırıcı 0.5309 / gözlenen 0.4571; k = 10: ort(S_cond) model 0.2495 / karşılaştırıcı 0.2358 / gözlenen 0.1429.

`path_conditional` (ikincil; `ceiling_path_v0` hücreleri ve limit yolu, S yerine bu modelin S'i; karşılaştırılan `ceiling_path_v0`'ın kendi j = 1 koşullu karışımı, aynı fold'un hücreleriyle). Fold durumları: OK 70 (NOT_PRODUCED skorlanmaz, TARGET_UNAVAILABLE değildir):

| Ufuk | Çıktı | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|---|
| D3 | koşullu medyan MAE | 70 (22) | 0.0456 | 0.0690 | -0.0234 | [-0.0495, +0.0000] | 8 / 2 / 60 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D3 | koşullu p_up Brier | 70 (22) | 0.0717 | 0.0643 | +0.0073 | [-0.0288, +0.0510] | 41 / 23 / 6 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | koşullu medyan MAE | 70 (22) | 0.1714 | 0.1800 | -0.0086 | [-0.0317, +0.0130] | 16 / 18 / 36 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D5 | koşullu p_up Brier | 70 (22) | 0.1051 | 0.1006 | +0.0044 | [-0.0311, +0.0461] | 45 / 23 / 2 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| D10 | koşullu medyan MAE | 70 (22) | 0.4992 | 0.4632 | +0.0361 | [+0.0002, +0.0767] | 24 / 32 / 14 | **karşılaştırılan daha iyi** (aralık 0'ın üstünde) |
| D10 | koşullu p_up Brier | 70 (22) | 0.1588 | 0.1625 | -0.0038 | [-0.0203, +0.0153] | 45 / 23 / 2 | ayırt edilemiyor (aralık 0'ı içeriyor) |

Keşif: koşullu Brier k = 3..9, `ceiling_hazard_v0` koşullu karşısında:

| k | n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |
|---|---|---|---|---|---|---|---|
| 3 | 70 (22) | 0.1123 | 0.1464 | -0.0342 | [-0.0745, +0.0042] | 46 / 22 / 2 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| 4 | 70 (22) | 0.1680 | 0.1913 | -0.0233 | [-0.0430, -0.0013] | 51 / 17 / 2 | **backtest'te geçiyor (tasarıma maruz)** |
| 5 | 70 (22) | 0.2129 | 0.2251 | -0.0122 | [-0.0253, +0.0053] | 47 / 21 / 2 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| 6 | 70 (22) | 0.2013 | 0.1989 | +0.0024 | [-0.0117, +0.0212] | 42 / 26 / 2 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| 7 | 70 (22) | 0.1844 | 0.1833 | +0.0010 | [-0.0129, +0.0171] | 40 / 28 / 2 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| 8 | 70 (22) | 0.1740 | 0.1698 | +0.0042 | [-0.0091, +0.0207] | 38 / 30 / 2 | ayırt edilemiyor (aralık 0'ı içeriyor) |
| 9 | 70 (22) | 0.1601 | 0.1508 | +0.0093 | [-0.0047, +0.0243] | 35 / 33 / 2 | ayırt edilemiyor (aralık 0'ı içeriyor) |

### Fold özeti

87 fold (Faz 1B tavan ledger'ıyla aynı küme ve sıra): FIT_OK 70, INSUFFICIENT_TRAINING_HISTORY 1, NOT_APPLICABLE 16, SURVIVAL_NOT_AVAILABLE 0, MODEL_NOT_FIT_DID_NOT_CONVERGE 0. Seçilen λ (FIT_OK fold sayısı): 3: 22, 10: 14, 30: 32, INF: 2. İlk 20 FIT_OK fold'da INF: 2. δ işaretleri (λ < INF, 68 fold): δ_lock < 0 63/63 (d1_lock düşen 5); δ_turn > 0 / < 0: 68 / 0.

T7 (λ = INF fold'ları): modelin S_cond'u ile aynı fold'un karşılaştırıcı S_cond'u arasındaki en büyük |Δ| = 0.0 (2 fold). T9 ((b)'nin paydası): δ fit'i yapılan FIT_OK fold 70; paydaya girmeyen INSUFFICIENT_TRAINING_HISTORY 1, NOT_APPLICABLE 16.

### Nihai fit önizlemesi (dondurulmadı)

81 arz (`H99_F3_PRESENT_L_GE_1`), δ eğitim kümesi 81 arz, 409 satır (d ≥ 2), 67 olay, 342 sağ kalım; kesim 2026-08-13. Ofset `models/ceiling_hazard_v0.json`'dan (`caa4dc867a9f`), `predict_hazard.linear_predictor` ile. **Seçilen λ = 30; δ_lock = -0.3278985872465678, δ_turn = 0.25106109793882575** (kolonlar ['d1_lock', 'd1_turnover'], düşen []); d1_turnover kırpma [-6.923783040059334, -0.6157622757273886]; çözücü 4 yineleme, maks |∇| 2.1316282072803006e-14. `models/`'e yazılmadı; dosya `tests/reference/macos_golden_faz5/post_d1_hazard_v0_final_fit_preview.json` (dondurma görevi bu önizlemeyle bit-eşitliği sınar).

| λ | iç CV skoru (satır başına log-kayıp) | durum |
|---|---|---|
| 0.1 | 0.39516214343262773 | SCORED |
| 1 | 0.3939017239475392 | SCORED |
| 3 | 0.39188784228193857 | SCORED |
| 10 | 0.3887083697617967 | SCORED |
| 30 | 0.38788300044658586 | SCORED |
| 100 | 0.39328404554217355 | SCORED |
| 300 | 0.40058366205586743 | SCORED |
| 1000 | 0.40530966208661073 | SCORED |
| INF | 0.4079193828377214 | SCORED |

### Faz 5 koşusu ve deney günlüğü

| Koşu | Plan | Fold | Ledger sha256 (ilk 12) | Günlükteki koşu sayısı |
|---|---|---|---|---|
| `post_d1_hazard_v0` | post_d1 | 87 | `579cf2ae4a35` | 1 |

### Dondurma

**Donduruldu — §5'in istediği bağımsız yeniden üretimden sonra.** "Beklentiden çok iyi" (Brier k = 2) tetiklendiği için dondurma, ilk uygulamayı görmeyen ayrı bir oturumun (Fable) yalnız şartnameden, `borsai` import etmeden yaptığı sıfırdan yeniden üretime bağlıydı. Sonuç (2026-09-24, `docs/fable_faz5_audit/AUDIT.md`): 87 fold'un durumu ve seçilen λ birebir, sayısal sütunlarda **maks |Δ| = 1.5e-11** (eşik 1e-9); nihai fit λ = 30 birebir; §4'ün 28 hücresi ve §5'in 18 etiketi aynı; sızıntı yok; hüküm **FREEZE_OK**. Ayrıntı ve ham çıktılar `docs/fable_faz5_audit/`. Dondurulan model şartnamedeki v0'dır ve yukarıdaki nihai fit önizlemesinin aynısıdır (`created_at`, `code_version`, `runtime` dışında `==`); dondurma temiz ağaçta yapıldı (`borsai_dirty` false). Yukarıdaki "dondurulmadı" ifadeleri backtest anının kaydıdır.

Donmuş dosya `models/post_d1_hazard_v0.json`, sha256 `3f7640267cd0f6b114ec88cf29e811587daa18c191866f9fa2d6910bc949e5dc`; kaydı ayrı dizinde, `models/INDEX_POST_D1.json` (aşama POST_D1, proje sahibi kararı 4). Ofset `ceiling_hazard_v0` (`caa4dc867a9f`); `models/INDEX.json` ve listeleme öncesi 19 model dosyası değişmedi. Canlı sicilde satırı canlı POST_D1 akışı kurulunca başlar; zaman kanıtı dondurma commit'inin push'udur.

k = 10 dipnotu: δ bütün d = 2..10'da ortak olduğundan kilit bilgisi D4–D10'a da taşınır; k = 10 hafif kötüleşir (`docs/fable_faz5_audit/AUDIT.md` §5-3); gün-grubu etkileşimi yeni model_id'dir.

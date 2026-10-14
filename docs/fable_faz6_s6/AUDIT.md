# BORSAI_FAZ6_FABLE_S6_RECOMPUTE_20260925 — Faz 2: bağımsız yeniden hesabın S6 skorlarıyla karşılaştırılması

Denetçi: Claude Code (Fable 5.1). Tarih: 2026-09-25 (İstanbul). Faz 1 commit'i `aea4082` (kör; Opus'un S6 çıktılarından önce). Faz 2'de okunanlar: `scores/scores_oot.json`, `docs/SCORES_OOT.md`, `docs/faz6/S6_RAPOR.md`, `docs/faz6/S6_FIX_RAPOR.md`, `docs/faz6/ekler/s6_denetim.txt`, SPEC_DEVIATIONS I39–I47, `git diff 3c82378..HEAD -- borsai/scoring.py tests/`. Ağ yok; push, tag, amend yok. Bu belgede üye kodu, kasa kodu ve bülten adı kalıbı yok; sayılar yalnız açık küme üzerindedir.

## Hüküm: **S6_OK**

KRİTİK ya da ÖNEMLİ bulgu yok. Üç KÜÇÜK/bilgi notu §5'te (tür: bilgi; ikisi rapor ifadesi, biri mekanizma).

## 1. Commit sırası ve körlük (K1)

| Sıra | Commit | İçerik |
|---|---|---|
| Fable Faz 1 | `aea4082` | kör yeniden hesap (`BORSAI_FAZ6_FABLE_S6_BLIND`) |
| Opus C | `e79a4b7` | `--oot` CLI, render, F5 ayrıştırıcısı |
| Opus FIX | `1c2fb02` | B1–B3 (post_d1 kapısı, açık küme `retro_info`, path karşılaştırıcısı) |
| Opus RENDER | `96f7d62` | SCORES_OOT.md §6 sayaçları |
| Opus S6 | `cf60cea` | `scores/scores_oot.json`, `docs/SCORES_OOT.md` |
| Opus R | `c0fecf5` | `S6_RAPOR.md`, ekler |

Fable'ın Faz 1 commit'i Opus'un bütün S6 commit'lerinden önce; S6 raporu `docs/fable_faz6_s6/`'nın açılmadığını yazıyor. `scores_oot.json`: `generated_at_utc` 2026-09-25T15:30:18Z, `code.git_head` `96f7d62`, `borsai_dirty` false.

## 2. Sınıf ve durum sayıları (birebir)

| Sayı | Fable (BAGIMSIZ.json) | Opus (scores_oot.json) | Eşit |
|---|---|---|---|
| Kohort sayaçları (MEMBER / kapsam dışı / açık / kasa / EXPOSED_ARCHIVE / EXPOSED_CODEX) | 135 / 1 / 71 / 64 / 4 / 1 | aynı | ✓ |
| 19 model × 71: OOT_BLIND / OOT_RETRO | 1349 / 0 | 1349 satır OOT_BLIND; `n_oot_retro` 0; üst düzey `retro_info` 0 | ✓ |
| 19 model durumları (SCORED / REFUSED / NOT_APPLICABLE_REGIME) toplam | 1296 / 51 / 2 | aynı, model başına 19/19 eşit | ✓ |
| `post_d1_hazard_v0`: BLIND / RETRO | 71 / 0 | 62 satır OOT_BLIND + 9 payda; `n_retro` 0 | ✓ |
| `post_d1_hazard_v0`: SCORED / REFUSED / D1 tavan değil | 59 / 3 / 9 | `n_scored` 59, `n_refused` 3, `n_not_applicable` 9; `n_d1_label_na` = `n_undetermined` = `n_skipped` = 0 | ✓ |
| TARGET_UNAVAILABLE / PENDING / SKIPPED | 0 / 0 / 0 | 0 / 0 / 0 | ✓ |

Fable'ın "NOT_APPLICABLE:D1_NOT_CEILING = 9" satır durumu, I42'den sonra Opus'ta satır değil payda sayacıdır (`n_not_applicable`); sayı aynı, yalnız sınıflandırma sunumu farklı. Fable'ın `n_spk_corporate_action_seen` sayacı yok (EXPOSURE §3 okunmadı); Opus 14 / 28.

## 3. Dokuz birincil hücre (toleranslar)

|Δ| değerleri Fable − Opus. Tolerans: n, blok ve ortalama fark 1e-9; aralık aynı üretici/tohum/blok sırasıyla 1e-9.

| # | Hücre | n (blok) | ort. fark | |Δ ort| | |Δ aralık| (alt, üst) | K/Kb/E eşit | hüküm (ikisi de) |
|---|---|---|---|---|---|---|---|
| 1 | `v1_5_h99` D5 MAE − `base_train_median` | 68 (28) | −0.028153 | 6.9e-18 | 0, 6.9e-18 | ✓ | ayırt edilemiyor |
| 2 | `v1_6_h99` D10 MAE − `v1_5_h99` | 68 (28) | +0.000415 | 0 | 0, 0 | ✓ | geçemiyor |
| 3 | `v1_5_market20_v0` D5 MAE − `v1_5_h99` | 68 (28) | −0.001832 | 0 | 0, 0 | ✓ | ayırt edilemiyor |
| 4 | `pb_v0` D5 MAE − `base_train_median` | 59 (28) | −0.008214 | 1.7e-18 | 0, 6.9e-18 | ✓ | ayırt edilemiyor |
| 5 | `ceiling_hazard_v0` RPS − `base_km_expanding` | 68 (28) | +0.068627 | 0 | 2.0e-18, 2.8e-17 | ✓ | geçemiyor |
| 6 | `pb_ceiling_v0` RPS − `base_km_expanding` | 59 (28) | +0.047639 | 0 | 2.6e-18, 0 | ✓ | ayırt edilemiyor |
| 7 | `ceiling_path_v0` D5 MAE − `base_train_median` | 67 (28) | −0.010073 | 0 | 0, 1.4e-17 | ✓ | ayırt edilemiyor |
| 8 | `pb_ceiling_path_v0` D5 MAE − `base_train_median` | 58 (28) | −0.008927 | 1.7e-18 | 6.9e-18, 0 | ✓ | ayırt edilemiyor |
| 9 | `post_d1_hazard_v0` j=1 koşullu RPS − `ceiling_hazard_v0` koşullu | 59 (26) | −0.041797 | 0 | 0, 3.5e-18 | ✓ | geçiyor (zaman-dışı terazide) |

Model ve karşılaştırıcı ortalama kayıpları da 6 haneye kadar eşit (ör. hücre 1: 0.230642 / 0.258795). Aralıklar bit düzeyinde aynı: aynı üretici, tohum ve sıralı blok kimlikleri; sıra kuralı farkı yok. Faz 1 özetinde işaretlenen yorum riskleri (kırpılmış `return`, `np.percentile` linear, `rng.choice(ids)`) Opus'un koduyla aynı çıktı.

Ek yeniden üretimler: S6_RAPOR §9.1'deki ortalama S_k tablosu (model / KM / gözlenen; k = 1, 2, 5, 10) ve yıl başına ortalama L (3.4 / 3.3 / 7.2) birebir; T6 duyarlılığı (f6 penceresi 2023-04-24'ü kesen 1 açık üye çıkarılınca n 67 (27), fark −0.001309, aralık [−0.010455, +0.006664], 19/17/31) birebir.

## 4. Öbür denetimler

- **Hüküm dili (`SCORES_OOT.md`).** "geçiyor" 157 kez, hepsi "geçiyor (zaman-dışı terazide)" biçiminde; çıplak "geçiyor" 0. "geçemiyor" 40, "ayırt edilemiyor" 324, "yetersiz örnek" 52 (10 ≤ n < 30 kırılımlar), "metrik yok" 9 (n < 10). Terazi adı başlıkta, girişte ve her "geçiyor"da. Birincil tablo (§2) ile keşif hücreleri (§5) ayrı; toplam/ortalama yok. ✓
- **S6_RAPOR §4 (şartname §8 beklentisi).** Dokuz hücrenin konumu Fable'ın Faz 1 özet §6 tablosuyla aynı: 1, 4, 9 beklenenden iyi ("beklentiden çok iyi" işareti), 5 ve 6 beklenenden kötü, 2, 3, 7, 8 aralık içinde. "puan" ikili okuması iki okumada da aynı konumu verir; doğru. §8 yıl kuralı için `ceiling_hazard_v0` 2023 dönüşü (−0.037, n 21, aralık 0'ı içerir) "rejime bağlı (zayıf kanıt)" doğru. ✓
- **Kod farkı (`3c82378..HEAD`, `borsai/scoring.py`, +349/−13).** Skor tanımı (kayıp, eşleşme, `class_oot`, bootstrap, n kuralları, `paired_metric`, `post_d1_row`) değişmedi. Değişenler: `--oot` CLI ve `main_oot`; `render_oot_doc` ve yardımcıları; `spk_corporate_action_members` (EXPOSURE §3'ü kodla okur, kümeyi yazmaz); `oot_post_d1_block` kapısı (I42: model düzeyi RETRO önce, D1 etiketi 0 → payda; `_oot_d1_label_agrees` tutarlılık bekçisi; I44: `path_params`); `build_oot_scores` `retro_info` süzgeci (I43). Hepsi kodu şartnameye uydurma ya da gösterim; aynı model_id. Bağımsız hesabın 9 hücreyi bit düzeyinde vermesi bunu doğruluyor. Test değişiklikleri: `test_faz6_oot.py`'de "dosya yok" assert'i "dosya değişmedi"ye çevrildi (S6'dan sonra dosya commit'li; gevşeme değil); `test_outcome_guard.py` kasa bekçisine iki skor dosyası eklendi (sıkılaşma). ✓
- **Kasa kodu.** Opus'un 9 yeni/değişen dosyası (`scores_oot.json`, `SCORES_OOT.md`, `S6_RAPOR.md`, `S6_FIX_RAPOR.md`, iki test dosyası, iki ek, görev dosyası) ve kod farkı: kasa kodu 0, bülten adı kalıbı 0. Fable'ın dosyaları: 0 / 0. ✓
- **F1 ek denetimi kapsamı (ret hücresi muaf) ve I46 (kalibrasyon satırı yok):** proje sahibi kararı; skor tanımı etkilenmez. Bilgi.

## 5. "Beklentiden çok iyi" üç hücrenin mekanizması (yalnız sayı; açık küme; keşif)

Kaynak: Fable'ın arz başına kayıp çiftleri (`BAGIMSIZ.json`) + kohort rejim etiketleri + gerçekleşen seri L. Gruplama sonuç görüldükten sonra yapıldı; hüküm değildir.

### 5.1 `v1_5_h99` D5 MAE − medyan (−0.028; §8 beklentisi [−0.01, +0.04])

| Gerçekleşen seri | n | ort. tahmin model / kural | gerçekleşen ort. | ort. fark | kazanç |
|---|---|---|---|---|---|
| L = 0 | 9 | 0.351 / 0.374 | 0.025 | −0.012 | 5 |
| L 1–4 | 23 | 0.516 / 0.374 | 0.119 | **+0.149** | 2 |
| L 5–9 | 27 | 0.549 / 0.374 | 0.608 | **−0.172** | 24 |
| L = 10 | 9 | 0.441 / 0.374 | 0.609 | −0.066 | 5 |

- D5 sonucu iki kümelidir: seri D5'e kadar sürdüyse getiri ≈ +0.61 (limit yolu), sürmediyse ort. 0.03–0.12. Açık kümede P(L ≥ 5) = 0.549; H99'da donmuş KM'nin S_5'i 0.414. Model bu kohortta ortalama 0.497 tahmin ediyor (kural 0.374); tahmin ortalaması gerçekleşen medyana (0.606) kuraldan daha yakın. Kazanç L ≥ 5 olan 36 arzdan (29 kazanç), kayıp L 1–4'ten (2 kazanç / 23) geliyor; en büyük 5 kazanç −1.18, en büyük 5 kayıp +1.18 (tek arz sürüklemiyor).
- Yıl: 2021 −0.031 (26), 2022 +0.005 (20), 2023 −0.047 (21); 2020 tek arz (−0.227). Tahsis rejimi: THRESH100 −0.056 (31) taşıyor, EQUAL_DIST +0.021 (15). Satış yöntemi ve pazar farkı küçük.
- Aynı terazide keşif hücresi: `v1_5_h99` D5 MAE − `base_always_ceiling` = −0.014 [−0.071, +0.045], 32 eşit → "her zaman tavan" kuralından ayırt edilemiyor; `ceiling_path_v0` − `base_always_ceiling` = +0.0003.
- **Okuma:** kazanç bir düzey etkisidir (kohortta D5 kilidi H99'dan sık; modelin nokta tahmini kilit atomuna medyan kuralından daha yakın), özellik ayrımı kanıtı değildir. Hüküm "ayırt edilemiyor" zaten bunu söylüyor.

### 5.2 `pb_v0` D5 MAE − medyan (−0.008; §8 beklentisi [−0.005, +0.03])

| Yıl | n | ort. fark | toplam fark |
|---|---|---|---|
| 2020 | 4 | **−0.226** | −0.904 |
| 2021 | 19 | −0.033 | −0.633 |
| 2022 | 17 | +0.041 | +0.701 |
| 2023 | 19 | +0.019 | +0.351 |

- Toplam fark −0.485; 2020'nin 4 arzı tek başına −0.904. **2020 hariç ortalama fark +0.0076 (n 55): §8 aralığının içinde.** 2020'nin 4 arzında L = 8, 9, 9, 9; model tahmini ort. 0.611, gerçekleşen ort. 0.605 (kayıp 0.005; kural 0.231). Bu dört arz `v1_5_h99` hücresinde yok (üçü f3 reddi; `v1_5_h99` 2020'de n 1).
- L grubu kalıbı 5.1 ile aynı: L 5–9 −0.142 (23/27 kazanç), L 1–4 +0.192 (1/18). Borsada satış −0.052 (25) / borsa dışı +0.024 (34); ANA −0.053 (26) / YILDIZ +0.027 (33).
- Keşif hücreleri: `pb_v0` − `v1_5_h99` +0.043 [+0.026, +0.064] "geçemiyor" (n 56); `pb_v0` − `base_always_ceiling` +0.043 [−0.010, +0.102].
- **Okuma:** "beklentiden çok iyi" işareti tanım gereği doğru, ama nokta tahminini §8 aralığının dışına taşıyan tek bir tabaka (2020, n 4, uzun serili, borsada satış/ANA) var. S6_RAPOR bunu belirtmiyor (§5 not 1).

### 5.3 `post_d1_hazard_v0` j = 1 koşullu RPS − `ceiling_hazard_v0` koşullu (−0.042; §8 beklentisi [−0.03, +0.02])

| Gerçekleşen seri | n | S_cond,2 model / ana | S_cond,5 | S_cond,10 | ort. fark | kazanç |
|---|---|---|---|---|---|---|
| L 1–4 | 23 | 0.925 / 0.957 | 0.602 / 0.721 | 0.318 / 0.438 | **−0.099** | 18 |
| L 5–9 | 27 | 0.971 / 0.963 | 0.814 / 0.780 | 0.610 / 0.560 | +0.007 | 9 |
| L = 10 | 9 | 0.943 / 0.927 | 0.673 / 0.622 | 0.419 / 0.381 | −0.044 | 8 |

59 arz ortalaması (k = 2 / 5 / 10): post_d1 0.949 / 0.710 / 0.467; ana model koşullu 0.955 / 0.733 / 0.485; KM koşullu 0.864 / 0.506 / 0.173; gözlenen P(L ≥ k | L ≥ 1) 0.814 / 0.610 / 0.153.

- Yıl: 2021 −0.046 (20), 2022 −0.041 (17), 2023 −0.041 (21); tahsis rejimlerinde −0.036…−0.055; pazarda −0.032 / −0.049. Tek dönem ya da tip taşımıyor. Borsa dışı −0.062 (36) / borsada satış −0.010 (23).
- Ortalama eğri düzeyi ana modelinkine çok yakın (fark ≤ 0.02); ikisi de k ≥ 7'de gözlenenin çok üstünde (k = 10: 0.47 ve 0.49'a karşı 0.15). Kazanç düzey düzeltmesi değil, **yeniden sıralama**: D1 özellikleri (kilit, el değiştirme) erken kırılanlarda (L 1–4) S_cond'u düşürüyor (k = 5'te 0.60'a karşı 0.72), uzun serilerde yükseltiyor. Bu yüzden ana modele karşı "geçiyor", KM ve @INF'e karşı (+0.05) ayırt edilemiyor, k = 10 Brier'de onlara karşı "geçemiyor" (+0.20).
- **Okuma:** S6_RAPOR §9.3 "kazanç büyük ölçüde ana modelin kaymasını D1 bilgisiyle düzeltmesinden geliyor olabilir" der. Sayılar bunun düzey düzeltmesi olmadığını, ayrım (sıralama) kazancı olduğunu gösteriyor; sonuç cümlesi ("D1 bilgisinin tek başına değeri KM'ye karşı gösterilmiş değil") olduğu gibi geçerli (§5 not 3).

## 6. Bulgular

| # | Düzey | Tür | Bulgu | Etki |
|---|---|---|---|---|
| 1 | KÜÇÜK | bilgi (rapor) | S6_RAPOR §4'te `pb_v0` "beklentiden çok iyi" işareti, tek tabakaya (2020, n 4) bağlı; 2020 hariç +0.0076, §8 aralığı içinde. Rapor bunu yazmıyor. | Hüküm değişmez ("ayırt edilemiyor"); işaretin yanına tabaka notu düşülmeli. |
| 2 | KÜÇÜK | bilgi (rapor) | S6_RAPOR §9.3'ün post_d1 mekanizma cümlesi ("kaymayı düzeltme") sayılarla uyuşmuyor: ortalama düzey aynı, kazanç yeniden sıralamadan. | Sonuç cümlesi geçerli; ifade düzeltilebilir. |
| 3 | bilgi | mekanizma | `v1_5_h99` D5 kazancı düzey etkisi (kohortta D5 kilidi H99'dan sık); "her zaman tavan" kuralından ayırt edilemiyor. S6_RAPOR bunu §9'da doğrudan yazmıyor (§9.1 hazard için benzerini yazıyor). | Model geliştirme bilgisi; hüküm etkilenmez. |

Kod ya da karar türünde bulgu yok.

## 7. Kabul kapısı

- **K1** ✓ Faz 1 commit'i `aea4082`, Opus'un S6 çıktılarından önce ve onlara bakılmadan.
- **K2** ✓ 9 hücre, sınıf ve durum sayıları bağımsız hesaplandı; kaynak denetimi 10/10 sha, 34/34 alan (Faz 1 özeti).
- **K3** ✓ Karşılaştırma toleranslarla yapıldı: sayılar birebir, 9 hücrede |Δ| ≤ 3e-17, hükümler aynı; hüküm **S6_OK**, bulgular §6.

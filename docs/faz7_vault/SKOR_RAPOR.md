# BORSAI_FAZ7_VAULT_SCORE_20260929 — kasa skorları (zaman-dışı terazi): birincil hücreler, önceden yazılmış beklentiler, seçim kuralları

Uygulayıcı: Claude Code (Opus 5.5). Tarih: 2026-09-29. Ağ kullanılmadı. push, tag ve amend yapılmadı.

- Bu raporda hiçbir üyenin kodu ve üye başına değer yok. Üye başına satırlar yalnız `scores/scores_oot.json`'dadır (ortak skor
  çıktısı; SPEC_DEVIATIONS M5 (a)).
- `docs/fable_faz7_vault/`'a dokunulmadı. Fable'ın paralel görevi `38d36e8` commit'ini bu görev sürerken ekledi; bu görevin tabanında
  vardır, içeriği okunmadı.
- **Uygulama ve MODELS.md değişmedi.** §9'daki seçim önerisi, Fable denetimi `VAULT_SCORE_OK` dedikten sonra uygulanır.

## Proje sahibi için özet (T8)

Bu bölümdeki her sayı **zaman-dışı teraziye** aittir. Kasa, 2020–2023 eski kohortunun bugüne kadar kapalı tutulan 64 arzıdır;
tahminler sonuç repoya girmeden push edildi. Bu sayılar geçmiş veri testiyle ya da canlı sicille toplanmaz, ortalamaları alınmaz.

**Tavan serisi (v1 adayları)**
- Kasada, zaman-dışı terazide v1 adaylarından yalnız `ceiling_hazard_v1_pooled` KM tabanını **geçiyor**: RPS farkı −0.040, aralık
  [−0.067, −0.012], n = 62.
- Kasada, zaman-dışı terazide `ceiling_hazard_v1_clip` (+0.033) ve `ceiling_hazard_v1_real` (−0.011) KM'den **ayırt edilemiyor**.
- Kasada, zaman-dışı terazide üç v1 adayı da `ceiling_hazard_v0`'ı geçiyor: clip −0.040, real −0.084, pooled −0.113.

**Tavan serisi (eski v0)**
- Kasada, zaman-dışı terazide `ceiling_hazard_v0` KM'den **ayırt edilemiyor**: +0.073, aralık [−0.001, +0.139].
- Açık küme ile kasanın toplamında (zaman-dışı terazi, n = 130) aynı model KM'ye karşı **geçemiyor**: +0.071 [+0.012, +0.126].

**Düşen arz ((C) adayları)**
- Kasada, zaman-dışı terazide `fall_d10_v0_pooled` taban oranı **geçiyor**: D10 Brier farkı −0.045 [−0.092, −0.002], n = 60.
- Kasada, zaman-dışı terazide `fall_d10_v0_h99` (−0.040) ve `fall_d10_v0_addsale` (−0.006) taban orandan **ayırt edilemiyor**.
- Kasada, zaman-dışı terazide üç (C) adayı da `v1_5_h99`'dan ayırt edilemiyor.

**D1 sonrası güncelleme**
- Zaman-dışı terazinin makine sıralı D1 sonrası tablosunda, kasada `post_d1_hazard_v0` `ceiling_hazard_v0`'dan **ayırt
  edilemiyor**: −0.035 [−0.072, +0.004], n = 45. Nokta tahmini beklentiyle (−0.035) aynı; satır sayısı beklenenden az olduğu için
  aralık 0'ı içeriyor.
- Zaman-dışı terazinin aynı tablosunda, açık küme + kasa toplamında `post_d1_hazard_v0` **geçiyor**: −0.039 [−0.060, −0.017], n = 104.

**Öbür eski modeller**
- Kasada, zaman-dışı terazide öbür yedi eski listeleme öncesi modelin altısı birincil hücresinde ayırt edilemiyor.
- Kasada, zaman-dışı terazide `v1_6_h99` `v1_5_h99`'a karşı çok küçük bir farkla **geçemiyor**: D10 MAE farkı +0.0004.

**Beklentiler.** Kasada, zaman-dışı terazide hiçbir birincil hücre "beklentiden çok iyi" eşiğini aşmadı. Kasada, zaman-dışı terazide v1, (C) ve
post_d1 birincillerinin hepsi önceden yazılmış aralığın içinde.

**Seçim önerisi (Fable denetimi bekleniyor).**
- Tavan serisi (SPEC_HAZARD_V1 §5.5): zaman-dışı terazinin kasa sayılarıyla ve kuralın k3 koşuluyla uygun aday yok; uygulamanın
  tavan kartında `ceiling_hazard_v0` birincil kalır.
  - `v1_pooled` zaman-dışı terazide k1'i ve k2'yi sağlıyor. k3'ü sağlamıyor: geçmiş veri terazisinin yakın dönem hücresinde
    etiketi "bozuyor".
  - `v1_real` de aynı etiket yüzünden uygun değil; ayrıca zaman-dışı terazide k1'i sağlamıyor.
  - `v1_clip` zaman-dışı terazide k1'i sağlamıyor.
- Düşen arz (SPEC_C_V0 §5.5): zaman-dışı terazide kasada geçen aday yok. `pooled` zaman-dışı terazide k1'i sağlıyor. Hiçbir aday
  zaman-dışı terazide k2'yi sağlamıyor, yani kasada `v1_5_h99`'a karşı aralığı tamamen 0'ın altında değil; bu yüzden, zaman-dışı terazinin sonucuna göre kart hiçbir
  (C) modelini öne çıkarmaz.

## 1. Commit'ler

| Sıra | Commit | İçerik |
|---|---|---|
| S | `ff49828` | `BORSAI_FAZ7_VAULT_SCORES`: yalnız `scores/scores_oot.json` ve `docs/SCORES_OOT.md` (CLI çıktısı, elle düzenlenmedi) |
| T | `8daeabe` | `BORSAI_FAZ7_VAULT_SCORES_TESTS`: T7, iki test sıkılaştırıldı (SPEC_DEVIATIONS M21); SPEC_DEVIATIONS M15–M22 |
| R | bu raporu ekleyen commit | `BORSAI_FAZ7_VAULT_SCORE_REPORT`: bu rapor, `ekler/skor_*`, görev dosyası. Hash: `git log -1 --format=%H -- docs/faz7_vault/SKOR_RAPOR.md` |

- Sıra S → T → R.
- Skor tanımı değişmedi: `git diff 439a808..HEAD -- borsai` boş.
- Skor komutu (T1) bir kez koşuldu: `.venv/bin/python -m borsai.scoring --oot`, HEAD `38d36e8`, borsai temiz, 1 dk 24 sn. Bayraksız
  `main()` koşulmadı.

## 2. T2: önceden yazılmış akıl-sağlığı denetimleri

- Kaynak: commit'ten önce yazılmış `scores/scores_oot.json`. Üretim zamanı 2026-09-29T18:08:37Z, `code.git_head` `38d36e8`,
  `borsai_dirty` false, borsai kaynak sha256 `f501510d12c3`.
- Betik: `ekler/skor_denetim.py` (yalnız okur). Çıktı: `ekler/skor_denetim.txt`.
- Karşılaştırılan Faz 6 dosyası `cf60cea`'daki `scores_oot.json`'dur.
- **23 denetimin 23'ü tuttu.**

| Denetim | Sonuç | Değer |
|---|---|---|
| code.borsai_dirty = false | TUTTU | git_head 38d36e8 |
| scores.json, scores_post_d1.json, SCORES.md bayt-eşit (sha256 önce = sonra) | TUTTU | scores.json 022a2f9904ba, scores_post_d1.json a27515108764, SCORES.md 5747dde1e238 |
| anahtarlar: oot_pre_h99, _sealed, _all, post_d1, post_d1_sealed, post_d1_all | TUTTU | oot_pre_h99, oot_pre_h99_all, oot_pre_h99_sealed, post_d1, post_d1_all, post_d1_sealed |
| sealed: 27 model (INDEX sırası) | TUTTU | 27 |
| sealed: kohort sayaçları n_sealed = n_in_table = 64 | TUTTU | n_sealed 64, n_in_table 64, n_member 135 |
| sealed: retro_info boş | TUTTU | 0 |
| sealed: her modelde 64 satır, hepsi SEALED | TUTTU | 27/27; toplam satır 1728 |
| sealed: n_oot_retro = n_skipped = n_pending = n_target_unavailable = 0 | TUTTU | 27/27 |
| sealed: PREDICTED, REFUSED (kod) ve NOT_APPLICABLE_REGIME (ret alanı) orkestratör tablosuyla birebir; n_scored = PREDICTED | TUTTU | 27/27 |
| sealed: her satır OOT_BLIND; kayıt S2 (19 eski) / ek kayıt 28aaa3b (8 yeni); ingest VA1 2f914dd; kayıt kanıtı < ingest kanıtı; kohort kapısı doğru | TUTTU | 1728/1728 satır; S2 2026-09-24T22:39:24Z, ek 2026-09-29T06:40:55Z, VA1 2026-09-29T15:30:41Z |
| all: tam olarak 19 eski model | TUTTU | 19 |
| all: yeni 8 model excluded_models'ta, nedeniyle (açık OOT_BLIND 0, açık OOT_RETRO 71) | TUTTU | 8 |
| all: her eski modelde n = açık n + kasa n (sayaçlar, satırlar, hücre n'leri) | TUTTU | 19/19 |
| all: kohort sayaçları n_in_table = 135 | TUTTU | 135 |
| açık: 19 eski modelin blokları Faz 6 commit'li dosyasıyla (cf60cea) aynı (hücreler, satırlar, sayaçlar) | TUTTU | 19/19 |
| açık: kohort sayaçları Faz 6 ile aynı | TUTTU | n_open 71, n_in_table 71 |
| açık: yeni 8 modelde n_oot_retro = 71, skorlanan satır 0 | TUTTU | 8/8 |
| açık: üst düzey retro_info yalnız yeni 8 modelin açık çiftleri (8 × 71) | TUTTU | 568 çift; Faz 6: 0 |
| post_d1 (açık) commit'li dosyadakiyle aynı | TUTTU | satır 62, skorlanan 59 |
| post_d1_sealed: 47 satır (45 skorlanan + 2 ret), n_not_applicable = 17, n_oot_retro = 0, diğer payda sayaçları 0 | TUTTU | satır 47, skorlanan 45, ret 2, NA 17, OOT_RETRO 0 |
| post_d1_sealed: ret kodları F3_MISSING × 2 | TUTTU | {'F3_MISSING': 2} |
| post_d1_sealed: her satır OOT_BLIND, MACHINE_SEQUENCED; kayıt VA2, ingest VB; kayıt kanıtı < ingest kanıtı | TUTTU | 47/47; VA2 2026-09-29T15:30:43Z, VB 2026-09-29T17:49:25Z |
| post_d1_all = açık + kasa (sayaçlar, satırlar; birincil n = 59 + 45) | TUTTU | satır 109, skorlanan 104, NA 26, birincil n 104 |

Kayıt kanıtları: ilk kayıtlar (S2 `1dcceff`) 2026-09-24T22:39:24Z, ek kayıtlar (`28aaa3b`) 2026-09-29T06:40:55Z. Kasa ingest'i
listeleme öncesi modeller için VA1 `2f914dd` (15:30:41Z), `post_d1_hazard_v0` için VB `71b9071` (17:49:25Z; VA2 `5a96e25`
kaydının kanıtı 15:30:43Z).

## 3. Kasa birincil hücreleri (zaman-dışı terazi; önceden ilan edilmiş)

**Okuma kuralları**
- Fark = model − karşılaştırılan; negatif = model iyi.
- Getiri farkları kesir birimindedir (0.030 = 3 puan).
- Aralık: ay-blok bootstrap, B = 4000, numpy PCG64 tohum 20260921, yüzdelik [2.5, 97.5].
- Hüküm dili SPEC_SCORING §8'dir. "Geçiyor" yalnız n ≥ 30 ve aralık tamamen 0'ın altındaysa kullanılır, daima "(zaman-dışı
  terazide)" ekiyle.

**Birincil hücrelerin kaynağı**
- Eski 8 model: SPEC_OOT_PRE_H99_V0 §6 (`OOT_PRIMARY_CELLS`).
- v1 adayları: SPEC_HAZARD_V1 §5.2.
- (C) adayları: SPEC_C_V0 §5.2.
- post_d1: `OOT_POST_D1_PRIMARY` (ayrı ölçek).

**Kural satırları.** Kasadaki 27 modelin 13'ü kural satırıdır: altı `base_*` kuralı, iki KM kuralı, dört `@INF` ve
`fall_d10_v0_pooled@ZERO`. Kural satırlarının birincil hücresi yoktur; yalnız sayaçları aşağıdadır.

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

Kasa POST_D1 sayaçları (`post_d1_sealed`): 47 satır = 45 skorlanan + 2 ret (`F3_MISSING`). D1'i tavan olmayan 17 üye satır değildir,
paydada sayılır (`n_not_applicable`). OOT_RETRO, atlanan, bekleyen, hedef oluşmadı, D1 etiketi NA ve D1 bekleniyor sayaçlarının
hepsi 0. M12'nin satır beklentisi (n ≈ 50–54) VA2'deki 45 PREDICTED'dan büyüktü; bu fark D_1 bilgisidir, modelin girdisidir
(RAPOR §B6).

## 4. İlan edilmiş ikinciller (kasa; "ikincil")

Bu tablo v1 §5.2 ve (C) §5.2'nin ilan ettiği hücreleri gösterir (kod etiketi "ikincil").

**Merdiven hücreleri yalnız bilgidir.** `v1_real − v1_clip`, `v1_pooled − v1_real`, `pooled − h99` ve `h99 − addsale` için
SPEC_HAZARD_V1 §5.4 ve SPEC_C_V0 §5.4 hüküm dili kullanmaz; okunuşu "… payı: fark [aralık]"tır. Tablonun hüküm sütunu bu satırlarda
yalnız §8 dil kuralının mekanik çıktısıdır.

Diğer bütün hücreler keşiftir (`docs/SCORES_OOT.md` §8.4).

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

post_d1 kasa bloğunun öbür hücreleri. Kaynak SPEC_POST_D1_V0 §4; kod etiketi "kural" ya da "ikincil"; ölçek ayrıdır.

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

## 5. Toplam (açık küme + kasa) birincilleri: 19 eski model ve post_d1

- `oot_pre_h99_all` ve `post_d1_all` ayrı anahtarlardır. Açık küme ve kasa bloklarıyla toplanmazlar; üç terazinin hiçbiriyle
  birleştirilmezler.
- Yeni 8 model toplamda **tanımsızdır**: açık küme satırları OOT_RETRO'dur (`excluded_models`).
- Karşılaştırma için açık küme satırları da aşağıdadır; Faz 6 ile bayt-eşittirler.

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

## 6. T3: önceden yazılmış beklentilerle karşılaştırma

- "Konum", gözlenen nokta tahmininin beklenen aralığa göre yeridir (S6 kalıbı). Üç değer alır: "aralık içinde", "altında:
  beklenenden iyi", "üstünde: beklenenden kötü".
- Beklenen fark ve aralık, şartnamedeki metnin aynısıdır.
- Beklentiden sapma modeli değiştirme gerekçesi değildir (CLAUDE.md kural 5).

**SPEC_HAZARD_V1 §6.1**

| Hücre | Beklenen fark | Beklenen aralık (aynen) | Gözlenen fark [%95 aralık], n | Konum |
|---|---|---|---|---|
| `ceiling_hazard_v0` − KM (kasada) | +0.08 | [+0.02, +0.14] | +0.0728 [−0.000814, +0.1388], 62 | aralık içinde |
| `v1_clip` − KM **(birincil)** | +0.035 | [−0.02, +0.09] | +0.0334 [−0.0260, +0.0886], 62 | aralık içinde |
| `v1_clip` − v0 | −0.04 | [−0.07, −0.015] | −0.0395 [−0.0640, −0.0161], 62 | aralık içinde |
| `v1_clip` Brier k=10 − KM | +0.10 | [+0.04, +0.16] | +0.0693 [−0.0152, +0.1463], 62 | aralık içinde |
| `v1_real` − KM **(birincil)** | −0.005 | [−0.06, +0.05] | −0.0110 [−0.0500, +0.0259], 62 | aralık içinde |
| `v1_real` − v0 | −0.08 | [−0.13, −0.03] | −0.0839 [−0.1279, −0.0347], 62 | aralık içinde |
| `v1_real` − `v1_clip` | −0.04 | [−0.08, 0.00] | −0.0444 [−0.0733, −0.0113], 62 | aralık içinde |
| `v1_real` Brier k=10 − KM | +0.04 | [−0.01, +0.09] | +0.0192 [−0.0397, +0.0733], 62 | aralık içinde |
| `v1_pooled` − KM **(birincil)** | −0.03 | [−0.07, +0.01] | −0.0400 [−0.0671, −0.0122], 62 | aralık içinde |
| `v1_pooled` − v0 | −0.10 | [−0.15, −0.05] | −0.1128 [−0.1808, −0.0381], 62 | aralık içinde |
| `v1_pooled` − `v1_real` | −0.03 | [−0.06, 0.00] | −0.0290 [−0.0588, +0.0037], 62 | aralık içinde |
| `v1_pooled` − `v1_pooled@INF` | −0.01 | [−0.04, +0.02] | −0.0354 [−0.0625, −0.0073], 62 | aralık içinde |
| `v1_pooled` Brier k=10 − KM | 0.00 | [−0.03, +0.04] | −0.0153 [−0.0492, +0.0161], 62 | aralık içinde |

**SPEC_C_V0 §6.1**

| Hücre | Beklenen fark | Beklenen aralık (aynen) | Gözlenen fark [%95 aralık], n | Konum |
|---|---|---|---|---|
| `v1_5_h99` − `base_rate` D10 (bilgi) | +0.010 | [−0.030, +0.050] | −0.0144 [−0.0533, +0.0257], 62 | aralık içinde |
| `fall_d10_v0_h99` − `base_rate` **(birincil)** | −0.020 | [−0.060, +0.020] | −0.0398 [−0.0878, +0.0043], 60 | aralık içinde |
| `fall_d10_v0_h99` − `v1_5_h99` | −0.030 | [−0.080, +0.010] | −0.0250 [−0.0906, +0.0302], 60 | aralık içinde |
| `fall_d10_v0_pooled` − `base_rate` **(birincil)** | −0.030 | [−0.070, +0.010] | −0.0452 [−0.0923, −0.0020], 60 | aralık içinde |
| `fall_d10_v0_pooled` − `pooled@ZERO` | −0.020 | [−0.060, +0.020] | −0.0384 [−0.0922, +0.0099], 60 | aralık içinde |
| `fall_d10_v0_pooled` − `fall_d10_v0_h99` | −0.010 | [−0.035, +0.015] | −0.0054 [−0.0272, +0.0188], 60 | aralık içinde |
| `fall_d10_v0_addsale` − `base_rate` **(birincil)** | −0.025 | [−0.060, +0.010] | −0.0058 [−0.0541, +0.0358], 62 | aralık içinde |
| `fall_d10_v0_addsale` − `v1_5_h99` | −0.035 | [−0.085, +0.010] | +0.0104 [−0.0667, +0.0780], 60 | üstünde: beklenenden kötü |
| D5 (ikincil) `fall_d10_v0_h99` − `base_rate` | −0.015 | [−0.050, +0.020] | −0.0244 [−0.0626, +0.0105], 60 | aralık içinde |
| D5 (ikincil) `fall_d10_v0_pooled` − `base_rate` | −0.015 | [−0.050, +0.020] | −0.0346 [−0.0756, +0.0012], 60 | aralık içinde |
| D5 (ikincil) `fall_d10_v0_addsale` − `base_rate` | −0.015 | [−0.050, +0.020] | −0.000088 [−0.0328, +0.0304], 62 | aralık içinde |

**SPEC_DEVIATIONS M12**

| Hücre | Beklenen fark | Beklenen aralık (aynen) | Gözlenen fark [%95 aralık], n | Konum |
|---|---|---|---|---|
| `post_d1_hazard_v0` j = 1 koşullu RPS − `ceiling_hazard_v0` (kasa) | −0.035 | [−0.065, −0.005] | −0.0347 [−0.0715, +0.0044], 45 | aralık içinde |

**SPEC_OOT_PRE_H99_V0 §8 (açık küme için yazıldı; kasa için aynı beklenti okunur)**

| Hücre | Beklenen fark | Beklenen aralık (aynen) | Gözlenen fark [%95 aralık], n | Konum |
|---|---|---|---|---|
| `v1_5_h99` D5 MAE − medyan | belirsiz, hafif kötü | [−0.01, +0.04] puan | −0.0119 [−0.0706, +0.0412], 62 | altında: beklenenden iyi · okuma B (puan = 0.01): [−0.0001, +0.0004] → altında: beklenenden iyi |
| `v1_6_h99` D10 MAE − `v1_5_h99` | ≈ 0 | [−0.01, +0.01] | +0.000399 [+0.000116, +0.000654], 62 | aralık içinde |
| `v1_5_market20_v0` D5 MAE − `v1_5_h99` | ≈ 0, hafif iyi | [−0.01, +0.005] | −0.0061 [−0.0186, +0.0056], 62 | aralık içinde |
| `pb_v0` D5 MAE − medyan | hafif kötü | [−0.005, +0.03] | +0.0303 [−0.0263, +0.0883], 53 | üstünde: beklenenden kötü |
| `ceiling_hazard_v0` RPS − `base_km_expanding` | belirsiz | [−0.03, +0.03] | +0.0728 [−0.000814, +0.1388], 62 | üstünde: beklenenden kötü |
| `pb_ceiling_v0` RPS − `base_km_expanding` | hafif kötü | [−0.02, +0.04] | +0.0653 [−0.0042, +0.1329], 53 | üstünde: beklenenden kötü |
| `ceiling_path_v0` birincil (D5 MAE − medyan) | ≈ `ceiling_hazard_v0` ile aynı işaret | [−0.03, +0.03] | +0.0019 [−0.0704, +0.0684], 60 | aralık içinde |
| `pb_ceiling_path_v0` birincil (D5 MAE − medyan) | hafif kötü | [−0.02, +0.04] | +0.0346 [−0.0366, +0.1018], 51 | aralık içinde |

**Kalibrasyon (bilgi satırları)**

- v1_pooled ort. S_5 − gözlenen = −0.0430 (beklenen [−0.10, +0.10]) → aralık içinde
- fall pooled ort. P(y4) − gözlenen = +0.0559 (beklenen [−0.08, +0.08]) → aralık içinde

**Dört okuma notu**
- **§8 kasaya uygulanıyor.** SPEC_OOT_PRE_H99_V0 §8 açık küme için yazıldı; kasa için aynı beklenti okunur (görev T3).
- **`ceiling_hazard_v0 − KM` hücresinin iki beklentisi var.** SPEC_HAZARD_V1 §6.1 kasa için +0.08 [+0.02, +0.14] yazdı; gözlenen
  aralığın içinde. §8'in açık küme beklentisi [−0.03, +0.03] idi; gözlenen onun üstünde.
- **"puan" belirsizliği.** §8'in ilk satırındaki "puan" iki okumayla yazıldı (S6 kalıbı). Okuma A: sayılar kesir. Okuma B: 1 puan =
  0.01 kesir. İki okuma aynı konumu verir.
- **Kalibrasyon.** v1 satırı raporda, dosyadaki kasa satırlarından hesaplandı (M17). (C) satırı dosyadaki bilgi satırından
  alındı.

## 7. T4: "beklentiden çok iyi" işaretleri

Eşikler şartnamelerin sözcükleriyle alındı. Karşılaştırılan sayılar birincil hücrenin noktası ve %95 aralığının üst ucudur.

| Birincil hücre (kasa) | Eşik | Fark | Üst uç | İşaret |
|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | fark < −0.10 ya da üst uç < −0.06 | +0.0334 | +0.0886 | yok |
| `ceiling_hazard_v1_real` | fark < −0.10 ya da üst uç < −0.06 | −0.0110 | +0.0259 | yok |
| `ceiling_hazard_v1_pooled` | fark < −0.10 ya da üst uç < −0.06 | −0.0400 | −0.0122 | yok |
| `fall_d10_v0_h99` | fark < −0.08 ya da üst uç < −0.04 | −0.0398 | +0.0043 | yok |
| `fall_d10_v0_pooled` | fark < −0.08 ya da üst uç < −0.04 | −0.0452 | −0.0020 | yok |
| `fall_d10_v0_addsale` | fark < −0.08 ya da üst uç < −0.04 | −0.0058 | +0.0358 | yok |
| `post_d1_hazard_v0` (M12) | fark < −0.08 ya da üst uç < −0.045 | −0.0347 | +0.0044 | yok |

**İşaret yok.** Bağımsız yeniden hesap paralel Fable görevidir. Seçim, Fable `VAULT_SCORE_OK` demeden uygulanmaz.

## 8. T5: başarısızlık tanımları (her aday için)

"Tuttu": tanımdaki başarısızlık gerçekleşti. "Tutmadı": gerçekleşmedi. (b) sütunu `scores/scores.json` `models[].backtest.near_era`
bloğundan okunur; bu değer geçmiş veri terazisine aittir ve kasa sayılarıyla toplanmaz.

**SPEC_HAZARD_V1 §6.4**

| Aday | (a) "v0'dan kötü": kasada RPS − v0 aralığı tamamen > 0 | (b) "bozuyor": yakın dönem alt > 0 (geçmiş veri terazisi) | (c) "özellikler bilgi eklemiyor": `v1_pooled − v1_pooled@INF` noktası ≥ 0 | (d) kalibrasyon: \|ort. S_5 − gözlenen P(L ≥ 5)\| > 0.15 |
|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | −0.0395 [−0.0640, −0.0161] → tutmadı | −0.0011 [−0.0066, +0.0049], etiket "tolerans içinde" → tutmadı | tanımsız (yalnız pooled) | \|0.5890 − 0.3710\| = 0.2180 → **tuttu**: "düzey kayması" notu |
| `ceiling_hazard_v1_real` | −0.0839 [−0.1279, −0.0347] → tutmadı | +0.0104 [+0.0028, +0.0183], etiket "bozuyor" → **tuttu** | tanımsız (yalnız pooled) | \|0.4726 − 0.3710\| = 0.1017 → tutmadı |
| `ceiling_hazard_v1_pooled` | −0.1128 [−0.1808, −0.0381] → tutmadı | +0.0289 [+0.0089, +0.0518], etiket "bozuyor" → **tuttu** | −0.0354 → tutmadı | \|0.3279 − 0.3710\| = 0.0430 → tutmadı |

**SPEC_C_V0 §6.4**

| Aday | (a) "taban orandan kötü": birincil aralık tamamen > 0 | (b) "bozuyor": yakın dönem `pooled − h99` alt > 0 (geçmiş veri terazisi) | (c) "ek satış bilgi eklemiyor" (addsale − `base_rate` noktası ≥ 0) / "özellikler bilgi eklemiyor" (pooled − `pooled@ZERO` noktası ≥ 0) | (d) kalibrasyon: \|ort. P(y4) − gözlenen oran\| > 0.15 |
|---|---|---|---|---|
| `fall_d10_v0_h99` | −0.0398 [−0.0878, +0.0043] → tutmadı | tanımsız (yalnız pooled) | tanımsız (addsale ve pooled) | \|0.2568 − 0.2000\| = 0.0568 → tutmadı |
| `fall_d10_v0_pooled` | −0.0452 [−0.0923, −0.0020] → tutmadı | −0.0058 [−0.0340, +0.0219], etiket "belirsiz" → tutmadı | özellikler: −0.0384 → tutmadı | \|0.2559 − 0.2000\| = 0.0559 → tutmadı |
| `fall_d10_v0_addsale` | −0.0058 [−0.0541, +0.0358] → tutmadı | tanımsız (yalnız pooled) | ek satış: −0.0058 → tutmadı | \|0.2829 − 0.1935\| = 0.0893 → tutmadı |

## 9. Seçim önerisi (Fable denetimi bekleniyor) — T6

Bu bölüm yalnız dosyadaki sayıları kullanır; yeni hesap yoktur.
- Zaman-dışı terazi: `scores/scores_oot.json` `oot_pre_h99_sealed`.
- Geçmiş veri terazisi (yalnız k3): `scores/scores.json` `models[].backtest.near_era`.

Uygulamaya ve MODELS.md'ye dokunulmadı.

### 9.1 SPEC_HAZARD_V1 §5.5 (tavan serisi kartında birincil)

Kuralın koşulları:
- **k1:** kasa birincil hücresi "geçiyor (zaman-dışı terazide)".
- **k2:** kasada RPS − `ceiling_hazard_v0` aralığının üst ucu < 0.
- **k3:** yakın dönem hücresi "bozuyor" değil.

Eşitlik kuralı |Δ| < 0.002'dir; sıra clip < real < pooled.

| Aday | k1: kasa birincil (RPS − KM) | k2: kasada RPS − v0 | k3: yakın dönem (geçmiş veri terazisi) | kasa RPS noktası | sonuç |
|---|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | +0.0334 [−0.0260, +0.0886], n 62: ayırt edilemiyor → **hayır** | −0.0395 [−0.0640, −0.0161]: üst uç < 0 → **evet** | −0.0011 [−0.0066, +0.0049], "tolerans içinde" → **evet** | 0.2306 | uygun değil |
| `ceiling_hazard_v1_real` | −0.0110 [−0.0500, +0.0259], n 62: ayırt edilemiyor → **hayır** | −0.0839 [−0.1279, −0.0347]: üst uç < 0 → **evet** | +0.0104 [+0.0028, +0.0183], "bozuyor" → **hayır** | 0.1862 | uygun değil |
| `ceiling_hazard_v1_pooled` | −0.0400 [−0.0671, −0.0122], n 62: geçiyor (zaman-dışı terazide) → **evet** | −0.1128 [−0.1808, −0.0381]: üst uç < 0 → **evet** | +0.0289 [+0.0089, +0.0518], "bozuyor" → **hayır** | 0.1573 | uygun değil |

**Öneri: uygun aday yok. Uygulamanın tavan kartında `ceiling_hazard_v0` birincil kalır.**

KARARLAR K4 gereği:
- Kart `ceiling_hazard_v0`'ı öne çıkarır.
- Kasada geçen ve geçemeyen adayları bir satırda yazar: kasada KM'yi geçen `v1_pooled`; ayırt edilemeyen `v1_clip` ve `v1_real`.
- Üç aday dondurulmuş kalır ve canlıda skorlanır.

### 9.2 SPEC_C_V0 §5.5 ("düşüş" kartında öne çıkarma)

Kuralın koşulları:
- **k1:** kasa birincil hücresi "geçiyor (zaman-dışı terazide)".
- **k2:** kasada D10 Brier − `v1_5_h99` aralığının üst ucu < 0.
- **k3:** `pooled` için yakın dönem hücresi "bozuyor" değil; `h99` ve `addsale` için yakın dönem − `base_rate` hücresi tamamen 0'ın
  üstünde değil.

Eşitlik sırası addsale < h99 < pooled.

| Aday | k1: kasa birincil (D10 Brier − `base_rate`) | k2: kasada D10 Brier − `v1_5_h99` | k3: yakın dönem (geçmiş veri terazisi) | kasa D10 Brier noktası | sonuç |
|---|---|---|---|---|---|
| `fall_d10_v0_h99` | −0.0398 [−0.0878, +0.0043], n 60: ayırt edilemiyor → **hayır** | −0.0250 [−0.0906, +0.0302]: üst uç ≥ 0 → **hayır** | − `base_rate` −0.0434 [−0.0773, −0.0048]: tamamen 0'ın üstünde değil → **evet** | 0.1288 | uygun değil |
| `fall_d10_v0_pooled` | −0.0452 [−0.0923, −0.0020], n 60: geçiyor (zaman-dışı terazide) → **evet** | −0.0304 [−0.1003, +0.0320]: üst uç ≥ 0 → **hayır** | `pooled − h99` −0.0058 [−0.0340, +0.0219], "belirsiz" → **evet** | 0.1234 | uygun değil |
| `fall_d10_v0_addsale` | −0.0058 [−0.0541, +0.0358], n 62: ayırt edilemiyor → **hayır** | +0.0104 [−0.0667, +0.0780]: üst uç ≥ 0 → **hayır** | − `base_rate` −0.0065 [−0.0301, +0.0161]: tamamen 0'ın üstünde değil → **evet** | 0.1601 | uygun değil |

**Öneri: kasada geçen aday yok.** Kart hiçbir (C) modelini öne çıkarmaz ve "kasada geçen aday yok" yazar. V1.5'in p_up sütunu olduğu
gibi kalır. KARARLAR_C / K4 gereği hiçbir model listeden kalkmaz.

## 10. Kırılımlar (kasa; birincil hücre)

- İlk işlem yılı ikincil satırdır; rejim alt kümeleri keşiftir.
- 10 ≤ n < 30: "yetersiz örnek". Hüküm yok; yalnız nokta ve aralık gösterilir.
- n < 10: metrik yok.
- Kasanın 2020 tabakası 4 üyedir.

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

n ≥ 30 olan rejim alt kümesi yalnız "borsa dışı satış"tır (n 32–42). Bu alt kümede:
- `ceiling_hazard_v1_pooled` "geçiyor (zaman-dışı terazide)", −0.044 [−0.077, −0.003].
- `v1_6_h99` "geçemiyor", +0.0003.
- Öbür modeller "ayırt edilemiyor".

Bu satırlar keşiftir.

## 11. Kalibrasyon bilgi satırları (hüküm yok)

- Kaynak: kasadaki OOT_BLIND ve skorlanan satırlar. Her model kendi skorlanan satırlarında ölçülür; bu yüzden n modelden modele
  değişir (ret ve rejimle uygulanamaz satırlar).
- Tavan ailesi: ort. S_k ve gözlenen P(L ≥ k). Rapor içi hesaptır (M17); dosyada v1 için kalibrasyon satırı yoktur (L7, I46).
- (C): dosyadaki bilgi satırı. Değerler ort. P(D10 kapanışı ≤ arz) ve gözlenen orandır.

| Model | n | ort. S_5 | gözlenen P(L ≥ 5) | fark | ort. S_10 | gözlenen P(L ≥ 10) | fark |
|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v0` | 62 | 0.6434 | 0.3710 | +0.2725 | 0.4096 | 0.1290 | +0.2805 |
| `ceiling_hazard_v1_clip` | 62 | 0.5890 | 0.3710 | +0.2180 | 0.3307 | 0.1290 | +0.2017 |
| `ceiling_hazard_v1_real` | 62 | 0.4726 | 0.3710 | +0.1017 | 0.2215 | 0.1290 | +0.0925 |
| `ceiling_hazard_v1_pooled` | 62 | 0.3279 | 0.3710 | −0.0430 | 0.1234 | 0.1290 | −0.0057 |
| `ceiling_hazard_v1_pooled@INF` | 63 | 0.3923 | 0.3810 | +0.0114 | 0.1241 | 0.1429 | −0.0188 |
| `base_km_expanding` | 64 | 0.4141 | 0.3906 | +0.0235 | 0.1414 | 0.1406 | +0.000789 |

| Model | n | ort. P(D10 kapanışı ≤ arz) | gözlenen oran | fark |
|---|---|---|---|---|
| `fall_d10_v0_h99` | 60 | 0.2568 | 0.2000 | +0.0568 |
| `fall_d10_v0_pooled` | 60 | 0.2559 | 0.2000 | +0.0559 |
| `fall_d10_v0_addsale` | 62 | 0.2829 | 0.1935 | +0.0893 |

## 12. Test sayıları (`ekler/skor_test_runs.txt`)

| Koşu | Sonuç |
|---|---|
| Adım 0: taban (HEAD `6287750`; koşu sırasında Fable `38d36e8`'i ekledi) | pytest 864 geçti (14 dk 25 sn); `test.sh` yeşil (cargo 94, vitest 222/222, parity 4, golden YEŞİL); `gen_golden --check` 25 dosya, fark 0 |
| Skor sonrası, dosyalar commit'siz, deselect'siz | 860 geçti, 4 kırmızı: iki temizlik bekçisi ve iki içerik testi. Görev kuralı gereği DUR; proje sahibi kararı M21 |
| S öncesi, dört test adıyla deselect | 860 geçti, 4 deselect (15 dk 55 sn) |
| S (`ff49828`) sonrası, deselect'siz | 862 geçti, 2 kırmızı: tam olarak iki içerik testi (18 dk 46 sn). `test.sh` yeşil (cargo 94, vitest 222/222, parity 4, golden YEŞİL); `gen_golden --check` 25, fark 0 |
| T hazırlığı: repo dışı kopya, S'nin commit'li durumuna karşı | sıkılaştırılmış iki test geçti. Dört mutasyonun dördü kırmızı: kasa hücre farkına 1e-12, `definitions`'a anahtar, `code.borsai_source_sha256`, belge sonuna satır sonu |
| T öncesi hedefli (`test_faz7_vault`, `test_faz7_oot`, `test_outcome_guard`) | 64 geçti (5 dk 25 sn) |
| T (`8daeabe`) sonrası, deselect'siz | pytest 864 geçti (19 dk 59 sn). `test.sh` yeşil (cargo 94, vitest 222/222, parity 4, golden YEŞİL); `gen_golden --check` 25, fark 0 |

## 13. Model geliştirme için gözlemler (keşif)

Bu bölüm keşiftir; hiçbir modelin geçtiği iddiası değildir.

**Kasa artık kullanıldı.** Bir sonraki fikir yeni model_id ister ve yalnız canlı teraziyle ölçülebilir. İkinci bir kasa yoktur
(SPEC_OOT_PRE_H99_V0 §9).

**Tavan serisi**
1. **Düzey kayması tavan ailesinin ana hatasıdır.** Kasada ort. S_5 − gözlenen P(L ≥ 5):
   - `ceiling_hazard_v0` +0.27, `v1_clip` +0.22, `v1_real` +0.10 → hepsi uzun seri bekliyor.
   - `v1_pooled` −0.04 ve `base_km_expanding` +0.02 → düzeyleri gözlenene yakın.
   - `v1_pooled`'ın kasadaki kazancının bir kısmı rejim teriminin taşıdığı düzeydir.
   - Özellikler de katkı veriyor: `v1_pooled − v1_pooled@INF` −0.035 [−0.063, −0.007].
   - Aynı model geçmiş veri terazisinin yakın döneminde "bozuyor" (+0.029). Bugünkü rejimde havuzun β'ları yakın dönemi kötüleştiriyor.
2. **Aday fikir.** Eski dönemin düzeyini yalnız rejim sabitine bırakan, β'ları yalnız H99'dan öğrenen bir model (yeni model_id).
   Yalnız canlıda ölçülebilir; canlı dönem tek rejim olduğundan ayrımı düşük olur (SPEC_HAZARD_V1 §6.3).
3. **Yıl örüntüsü açık kümedekiyle aynı.** v0 ailesinin (`ceiling_hazard_v0`, `pb_ceiling_v0`, `ceiling_path_v0`,
   `pb_ceiling_path_v0`, `v1_clip`) farkı 2021'de büyük ve pozitif, 2023'te negatif; alt kümeler yetersiz örnektir. Rejim alt
   kümelerinde de aynı yön var: `PRE_20211111`'de pozitif, `EQUAL_DIST_20230330`'da negatif. `v1_pooled`'da üç yılda da nokta
   negatif.

**Düşen arz**

4. **`fall_d10_v0_pooled` ile `v1_5_h99` karşılaştırması.**
   - Ortalama farkı −0.030 ama kazanç/kayıp 14/46: V1.5 üyelerin çoğunda daha iyi. (C) modeli az sayıda üyede, büyük olasılıkla
     düşen arzlarda, çok daha iyi.
   - Bu, iki çıktının birlikte kullanılabileceğini düşündürür. Örnek: V1.5 p_up'ı ek satış bayrağıyla düzelten bir model (yeni
     model_id).
   - Kasada olay sayısı 12'dir (60 üyede gözlenen oran 0.20). Güç düşük.
5. **(C) adayları düşme oranını biraz yüksek veriyor.** Tahmin 0.26–0.28, gözlenen 0.19–0.20 (fark +0.056…+0.089). Bu, §6.4 (d)
   eşiğinin (0.15) altındadır.

**D1 sonrası**

6. **`post_d1_hazard_v0` k = 10 Brier'de kurallara karşı geçemiyor.** KM ve @INF'e karşı +0.149. Aynı örüntü açık kümede de
   vardı (+0.20). D1 sonrası model uzun serileri kasada da fazla bekliyor. Birincil hücre (j = 1 koşullu RPS) bundan
   etkilenmiyor.

## 14. Kabul kapısı

- **K1: tuttu.**
  - Taban yeşil: pytest 864, `test.sh` yeşil.
  - VB kanıtı (2026-09-29T17:49:25Z), VA2 kanıtından (15:30:43Z) sonra.
  - `s2_gate_problems` ve `vault_s3_gate_problems` ikisi de 0.
- **K2: tuttu.**
  - T2'nin 23 denetiminin 23'ü commit'ten önce tuttu.
  - Kasa satırlarında `n_oot_retro` 0 (27 modelde ve `post_d1_sealed`'da).
  - `scores.json`, `scores_post_d1.json` ve `SCORES.md` sha256 olarak aynı.
- **K3: tuttu.**
  - `scores_oot.json` ve `SCORES_OOT.md` S'de (`ff49828`) commit'li.
  - T3–T6 bu raporda (§6–§9).
  - `git diff 439a808..HEAD -- borsai` boş.
- **K4: tuttu, bir kayıtla.**
  - Sıra S → T → R; push yok.
  - Commit'lerde yalnız izinli yollar: S'de iki skor dosyası; T'de iki test dosyası ve SPEC_DEVIATIONS; R'de `docs/faz7_vault/` ve görev dosyası.
  - Kayıt: S ile T arasında iki içerik testi kırmızıydı. Bu, proje sahibinin kararıyla ve adıyla oldu (SPEC_DEVIATIONS M21).

Push yapılmadı. Push ve push kanıtı proje sahibinindir.

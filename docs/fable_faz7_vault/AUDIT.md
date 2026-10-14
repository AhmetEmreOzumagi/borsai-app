# BORSAI_FAZ7_FABLE_VAULT_RECOMPUTE_20260929 — Faz 2: bağımsız kasa hesabı ile kasa skorlarının karşılaştırması

Denetçi: Claude Code (Fable 5.1). Tarih: 2026-09-29 (İstanbul). Taban: HEAD `3cfd010` (`BORSAI_FAZ7_VAULT_SCORE_REPORT`); Faz 1 körlük commit'im `38d36e8` bunun atası; Opus'un skor koşusu `38d36e8` üzerinde yapıldı (`scores_oot.json` → `code.git_head`).

**Sıra kanıtı (K1).** Faz 1 (`38d36e8`, 21:05) Opus'un S (`ff49828`), T (`8daeabe`) ve R (`3cfd010`) commit'lerinden öncedir; Faz 1 boyunca skor dosyaları açılmadı (`faz1_ozet.md` körlük beyanı). Bu Faz 2'de okunanlar: `scores/scores_oot.json`, `docs/SCORES_OOT.md`, `docs/faz7_vault/SKOR_RAPOR.md`, `docs/faz7_vault/ekler/skor_tablolar.md`, `ekler/skor_test_runs.txt`, `git diff 439a808..HEAD -- borsai tests docs/SPEC_DEVIATIONS.md`. `borsai` yine import edilmedi (`karsilastir.py`, `python -I`). Karantinaya dokunulmadı; ağ yok; push, tag, amend yok.

Dosyalar: `karsilastir.py` (BAGIMSIZ.json ↔ scores_oot.json) → `karsilastir_cikti.json`; bu rapor.

## Hüküm

**`VAULT_SCORE_OK`.** Kasanın sınıf ve durum sayıları, Faz 1'de hesaplanan 34 hücrenin hepsi (n, blok, ortalama fark, %95 aralık, kazanç/kayıp/eşit, model ve kural değeri, hüküm), yıl kırılımları, `oot_pre_h99_all` kuralı ve iki seçim kuralının sonucu Opus'un dosyasıyla **birebir** aynı. Skor tanımı değişmedi (`borsai/` farkı boş). Bulgular yalnız bilgi düzeyinde (§6).

## 1. Sınıf ve durum sayıları

| Karşılaştırma | Opus (`oot_pre_h99_sealed`, `post_d1_sealed`) | Bağımsız | Sonuç |
|---|---|---|---|
| 27 INDEX modeli × 64 satır, sınıf | 1728 OOT_BLIND, 0 RETRO (`n_oot_retro` 27/27 = 0) | 1728 / 0 | birebir |
| 27 model, durum (`n_scored / n_refused / n_not_applicable_regime`) | 1660 / 57 / 11; `n_pending = n_skipped = n_target_unavailable = 0` | 1660 / 57 / 11 | model başına 27/27 birebir |
| `post_d1_hazard_v0` kasa | 47 satır: 45 skorlanan + 2 ret; `n_not_applicable` 17; OOT_RETRO 0; satırlar OOT_BLIND, MACHINE_SEQUENCED | 45 / 2 / 17; 64/64 OOT_BLIND | birebir |
| Sonuç girişi ve kanıtlar | VA1 `2f914dd` (15:30:41Z) listeleme öncesi; VB `71b9071` (17:49:25Z) post_d1; kayıtlar `1dcceff` / `28aaa3b` / `5a96e25` | aynı | birebir |

## 2. Hücreler (Faz 1'in 34 hücresi)

Eşleştirme anahtarı (metric, horizon_or_k, output, rule_id). Toleranslar: sayımlar birebir; fark ve aralık |Δ| ≤ 1e-9.

| Grup | Hücre sayısı | BİREBİR | KÜÇÜK | ÖNEMLİ |
|---|---|---|---|---|
| Eski 8 birincil (SPEC_OOT §6) | 8 | 8 | 0 | 0 |
| v1 (SPEC_HAZARD_V1 §5.2/§5.4; v0 − KM dahil) | 13 | 13 | 0 | 0 |
| (C) (SPEC_C_V0 §5.2/§5.4; `v1_5_h99 − base_rate` bilgi dahil) | 12 | 12 | 0 | 0 |
| `post_d1_hazard_v0` j = 1 birincil | 1 | 1 | 0 | 0 |
| **Toplam** | **34** | **34** | 0 | 0 |

En büyük |Δ|: ortalama fark 4.2e-17, aralık uçları 2.8e-17 (kayan nokta toplama sırası). Hüküm metinleri aynı (Opus dosyada "geçiyor", belgede "geçiyor (zaman-dışı terazide)"). Aralıklar aynı üretici, tohum ve blok sırasıyla bit-eşit çıktı; Faz 1'de not edilen sıfıra yakın uçlar (`fall_pooled − base_rate` üst −0.0020, `v0 − KM` alt −0.0008, `post_d1` üst +0.0044) Opus'ta da aynı değerlerde. Kalibrasyon satırları (v1: ort. S_5/S_10; (C): ort. P(y4)) SKOR_RAPOR §11 ve SCORES_OOT §8.3 ile 1e-4 hassasiyetinde aynı (0.6434/0.5890/0.4726/0.3279; 0.2568/0.2559/0.2829).

Yıl kırılımları: 14 birincil hücrenin 56 yıl satırı (n ve fark) birebir; n < 10 (2020) satırlarında iki tarafta da metrik yok.

## 3. `oot_pre_h99_all` ve `post_d1_all`

- `oot_pre_h99_all` tam olarak 19 eski modeli içeriyor (INDEX sırası); 8 yeni model `excluded_models`'ta, her biri açık kümede 0 BLIND / 71 RETRO gerekçesiyle. `n_in_table` 135.
- 19/19 modelde sayaçlar (`n_scored`, `n_refused`, `n_not_applicable_regime`, `n_oot_retro`), satır sayıları ve her hücrenin n'i = açık + kasa (hücre bazında eşleştirildi).
- `post_d1_all`: 109 = 62 + 47 satır, 104 = 59 + 45 skorlanan, 26 = 9 + 17 NA; `excluded_models` boş.
- Toplam bloğun fark ve aralıkları bu görevde bağımsız hesaplanmadı (Faz 1 kapsamı kasa); yalnız n kuralı denetlendi.

## 4. Hüküm dili

- Kasa dosyasındaki 650 hücrenin hüküm sözcükleri {geçiyor 228, geçemiyor 19, ayırt edilemiyor 403}; "geçiyor" ancak n ≥ 30 ve üst uç < 0, "geçemiyor" ancak n ≥ 30 ve alt uç > 0 iken: **0 ihlal**. Kasada n < 30 hücre yok; yıl/rejim kırılımları "yetersiz örnek" ya da "metrik yok".
- Belge §8'de her "geçiyor" "(zaman-dışı terazide)" ekiyle (228/228); T8 özetindeki her cümle terazi adını taşıyor; k3 cümlesinde geçmiş veri terazisinin adı ayrıca var, toplama yok.
- Bilgi (§6-1): "geçemiyor" belgede eksiz (19 hücre; ör. `v1_6_h99`).

## 5. SKOR_RAPOR denetimi (T3–T6)

- **T3 (beklenti karşılaştırması):** v1 §6.1 13/13 "aralık içinde"; (C) §6.1 11/12 içinde, `addsale − v1_5_h99` +0.0104 "üstünde" (beklenen [−0.085, +0.010]); M12 post_d1 içinde; SPEC_OOT §8 kasaya uygulanmış (M17): 1 altında, 3 üstünde, 4 içinde. Hepsi kendi Faz 1 okumamla aynı; tek fark kendi özetimde `pb_v0` (+0.030277) satırını "sınırda içinde" yazmam: doğrusu Opus'unki ("üstünde", 0.030277 > 0.03). `ceiling_hazard_v0 − KM` için iki beklenti (v1 §6.1 ve SPEC_OOT §8) ayrı ayrı yazılmış; doğru.
- **T4 ("beklentiden çok iyi"):** 7 birincilde işaret yok; eşikler şartname sözcükleriyle (v1 −0.10/−0.06; (C) −0.08/−0.04; post_d1 −0.08/−0.045). Benimkiyle aynı. Bu yüzden mekanizma açıklaması zorunlu değil; bilgi notu §6-4.
- **T5 (başarısızlık tanımları):** v1: (a) hiçbirinde; (b) real ve pooled "bozuyor"; (c) pooled −0.0354 → tutmadı; (d) clip 0.2180 → "düzey kayması". (C): (a)–(d) hiçbirinde. Benimkiyle aynı; "tanımsız" işaretleri (M19) doğru.
- **T6 (seçim kuralları):** v1 → uygun aday yok, `ceiling_hazard_v0` birincil kalır (clip k1 ✗; real k1 ✗ k3 ✗; pooled k1 ✓ k2 ✓ k3 ✗). (C) → "kasada geçen aday yok" (h99 k1 ✗ k2 ✗; pooled k1 ✓ k2 ✗; addsale k1 ✗ k2 ✗). **İki kuralın sonucu Faz 1'deki sonucumla aynı**; k1–k3 değerleri aday aday aynı; eşitlik kuralı iki tarafta da kullanılmadı (M20: metindeki |Δ| < 0.002, sözde koddaki `round(…, 3)` değil — Faz 1'de ben de metni uyguladım).

## 6. Bulgular

Kritik ya da önemli bulgu yok. Bilgi düzeyinde:

1. **KÜÇÜK / bilgi — "geçemiyor" eksiz.** SPEC_HAZARD_V1 §5 ve SPEC_C_V0 §5 zaman-dışı hükmünün daima "(zaman-dışı terazide)" ekiyle yazılmasını ister; belge ve rapor tablolarında ek yalnız "geçiyor"a uygulanıyor, "geçemiyor" (19 hücre) eksiz. Faz 6'dan gelen render davranışı (`borsai/` farkı boş; S6 denetiminde de böyleydi), hüküm değişmiyor; T8 cümleleri terazi adını taşıyor. İstenirse ayrı bir render düzeltmesi (skor tanımı değişmez).
2. **bilgi — testler.** `tests/` farkı yalnız T7 sıkılaştırması: `test_real_scores_oot_in_memory_run_equals_committed_file` (kasa açık kipte bellek koşusu = commit'li dosya, tam eşitlik, yalnız `code.git_head` için ata bağıntısı) ve `test_committed_oot_doc_unchanged_by_new_renderer` (dört kasa anahtarı var; bayt eşitliği). İkisi de eskisinden katı; S ile T arasındaki kırmızı pencere proje sahibi kararıyla ve adıyla kayıtlı (SPEC_DEVIATIONS M21). Opus T sonrası tam pytest 864 geçti; bu denetimde test koşulmadı (tanım farkı yok).
3. **bilgi — seçim noktası.** (C) adayının "kasa D10 Brier noktası" adayın kendi skorlanan kümesinde (addsale 62 arz, 0.1601; ortak 60'ta 0.1642). İki okumada da sıralama ve sonuç değişmez; uygun aday yok.
4. **bilgi — kazancın mekanizması (yalnız sayı; hüküm değil).** "Beklentiden çok iyi" hücre olmadığından zorunlu değil; kasada "geçiyor" çıkan iki birincil için: `v1_pooled − KM` yıl: 2021 (26) −0.066, 2022 (18) −0.022, 2023 (16) −0.027; rejim: PRE −0.056, THRESH −0.029, EQUAL −0.024 — kazanç üç yıla ve üç rejime yayılı. `v1_pooled − v0` ise 2021'de −0.232, 2023'te +0.010 (PRE −0.225, EQUAL +0.026): v0'a karşı fark eski rejimin düzey kaymasıdır (v0 ort. S_5 0.643, gözlenen 0.371). `fall_pooled − base_rate`: 2021 −0.066, 2022 −0.073, **2023 +0.011**; PRE −0.061, THRESH −0.074, **EQUAL +0.042** (12 üye). (C) kazancı 2023-03 öncesi rejimlerden geliyor; bugünkü rejim alt kümesinde işaret pozitif (n = 12, yetersiz örnek). SKOR_RAPOR §13'ün okumasıyla uyumlu.
5. **bilgi — sıfıra yakın uçlar.** `fall_pooled − base_rate` üst ucu −0.0020 (k1'in dayandığı uç), `v0 − KM` alt ucu −0.0008, `post_d1` üst +0.0044: bit-eşit yeniden üretildi; farklı bir bootstrap uygulaması bu hükümleri oynatabilirdi ama seçim sonuçlarını değiştirmezdi (pooled (C) k2'de, v1 pooled k3'te düşer).

## 7. Kabul kapısı

- **K1** ✓ Faz 1 commit'i (`38d36e8`) Opus'un S/T/R commit'lerinden önce ve skor dosyalarına bakılmadan.
- **K2** ✓ Faz 1: hücreler, sınıf/durum ve iki seçim kuralı bağımsız; kaynak denetimi 10/10 sha, 11/11 satır, 22/22 alan.
- **K3** ✓ Faz 2: 34/34 hücre |Δ| ≤ 1e-9 (gerçekte ≤ 4.2e-17), sayılar birebir, `oot_pre_h99_all` kuralı, hüküm dili, T3–T6 ve seçim kuralı sonuçları denetlendi; hüküm `VAULT_SCORE_OK`.

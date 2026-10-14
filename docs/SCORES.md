# Skorlar: canlı sicil ve backtest

Bu sayfa `python -m borsai.scoring` ile `scores/scores.json`'dan üretilir; elle düzenlenmez. Tanımlar: `docs/specs/SPEC_SCORING.md`; kod: `borsai/outcomes.py` (sonuç), `borsai/scoring.py` (sınıf, birincil kayıt, metrik).

- Skora giren en son THB: **2026-09-30**. Sonuç yalnız resmi BIST THB/THM'den (`data/raw/bist/`, `data/outcomes/`).
- Kod: HEAD `cf5019ceaea9251153c75ba25a6b727a6d965a12` (üretim anı); borsai kaynak sha256 `f501510d12c3`.
- **İki terazi asla toplanmaz.** Canlı sicil (prospektif) ile geçmiş veri testi (retrospektif walk-forward, H99) ayrı bölümlerdedir; aralarında ortalama ya da toplam yoktur (CLAUDE.md kural 3).
- **Küçük n (SPEC_SCORING §8):** modellerin canlı skorlanan arz sayısı en çok n = 7 < 10. Canlı tarafta YALNIZ satır tablosu vardır: metrik, ortalama, fark, aralık ya da hüküm üretilmez.

## 1. Sonuçlar (arz × ufuk)

D_h = payın işlem gördüğü h'inci resmi seans (yarım gün sayılır, tam gün durdurma sayılmaz). Tavan = kapanış = o seansın THM üst limiti (Decimal eşitliği). R_h = kapanış / arz fiyatı − 1; Y_h = 1[kapanış > arz fiyatı]. PENDING = seans henüz oluşmadı.

| Arz | Arz fiyatı | D_1 (THB) | D_1 (duyuru) | D_3 | D_5 | D_10 | R_D1 | R_D3 | R_D5 | R_D10 | Y 1/3/5/10 | Tavan D1…D10 | L | Satır durumu |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CITAS | 73.7 | 2026-08-18 | 2026-08-18 | 2026-08-20 | 2026-08-24 | 2026-08-31 | 0.0997 | 0.3304 | 0.6079 | 0.7368 | 1/1/1/1 | 1111100110 | 5 | OK 10 |
| TKNKA | 85.4 | 2026-08-20 | 2026-08-20 | 2026-08-24 | 2026-08-26 | 2026-09-02 | 0.0995 | 0.3290 | 0.6066 | 1.2248 | 1/1/1/1 | 1111111011 | 7 | OK 10 |
| VEYAS | 136 | 2026-08-20 | 2026-08-20 | 2026-08-24 | 2026-08-26 | 2026-09-02 | -0.0007 | 0.0985 | 0.0147 | 0.0000 | 0/1/1/0 | 0010000000 | 0 | OK 10 |
| KPEKS | 94 | 2026-08-21 | 2026-08-21 | 2026-08-25 | 2026-08-27 | 2026-09-03 | 0.1000 | 0.3298 | 0.6085 | 0.0128 | 1/1/1/1 | 1111100000 | 5 | OK 10 |
| INTET | 53.6 | 2026-09-01 | 2026-09-01 | 2026-09-03 | 2026-09-07 | 2026-09-14 | 0.0998 | 0.3293 | 0.3909 | 0.1409 | 1/1/1/1 | 1111000000 | 4 | OK 10 |
| BKRGY | 12.93 | 2026-09-02 | 2026-09-02 | 2026-09-04 | 2026-09-08 | 2026-09-15 | -0.0998 | -0.2583 | -0.3155 | -0.3991 | 0/0/0/0 | 0000000000 | 0 | OK 10 |
| NETGL | 25.52 | 2026-09-17 | 2026-09-17 | 2026-09-21 | 2026-09-23 | 2026-09-30 | 0.0995 | 0.3299 | 0.0784 | -0.3617 | 1/1/1/0 | 1110000000 | 3 | OK 10 |

Tavan sütunu: 1 = tavan kapanışı, 0 = değil, ? = NA (üst limit yok), · = PENDING. Satır durumu: 10 ufuk satırının `data/outcomes/<T>.csv` durumları.

Yarım gün / gün içi durdurma / tam gün durdurma kayması: yok.

## 2. Sınıf ve birincil kayıt (arz × model)

Sınıf koddan hesaplanır (SPEC_SCORING §5): model JSON'unu ekleyen commit sonuç commit'inin atası mı ve push kanıtı var mı; kaydın push kanıtı D_1'den önce mi; inputs_pit_ok. Birincil kayıt §6 kuralıyla (`registry.select_primary`). Sonuç dosyaları henüz commit edilmemişken üretilen skorda sınıf HEAD'e karşı denetlenir (`class_evidence`).

| Model | CITAS | TKNKA | VEYAS | KPEKS | INTET | BKRGY | NETGL |
|---|---|---|---|---|---|---|---|
| `v1_5_h99` | LATE_RECORD | LATE_RECORD | LATE_RECORD (ret) | LATE_RECORD | LATE_RECORD; + LEGACY_SELF_REPORTED `INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING` | LATE_RECORD; + LEGACY_SELF_REPORTED `BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING` | LIVE legacy `NETGL_20260916_V1_5` |
| `base_always_ceiling` | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `base_train_median` | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `base_train_mean` | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `base_zero` | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `base_rate` | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `base_last10_rate` | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `v1_6_h99` | LATE_RECORD | LATE_RECORD | LATE_RECORD (ret) | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `v1_5_market20_v0` | LATE_RECORD | LATE_RECORD | LATE_RECORD (ret) | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `pb_v0` | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `ceiling_hazard_v0` | LATE_RECORD | LATE_RECORD | LATE_RECORD (ret) | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `ceiling_hazard_v0@INF` | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `pb_ceiling_v0` | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `pb_ceiling_v0@INF` | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `base_km_expanding` | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `base_km_last10` | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD | LATE_RECORD |
| `ceiling_path_v0` | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO |
| `ceiling_path_v0@INF` | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO |
| `pb_ceiling_path_v0` | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO |
| `ceiling_hazard_v1_clip` | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO |
| `ceiling_hazard_v1_real` | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO |
| `ceiling_hazard_v1_pooled` | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO |
| `ceiling_hazard_v1_pooled@INF` | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO |
| `fall_d10_v0_h99` | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO |
| `fall_d10_v0_pooled` | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO |
| `fall_d10_v0_addsale` | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO |
| `fall_d10_v0_pooled@ZERO` | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO | RETRO |

Sicil kayıtları (kayıt → ekleyen commit, push kanıtı):

- BKRGY: `20260922T121936Z_459846d44a17.json` → `7cb49cf`, kanıt 2026-09-22T14:06:05Z
- CITAS: `20260922T121935Z_6356b36ec865.json` → `7cb49cf`, kanıt 2026-09-22T14:06:05Z
- INTET: `20260922T121935Z_6dccd49888dc.json` → `7cb49cf`, kanıt 2026-09-22T14:06:05Z
- KPEKS: `20260922T121935Z_4ef4794c6b2b.json` → `7cb49cf`, kanıt 2026-09-22T14:06:05Z
- NETGL: `20260922T121936Z_65a39d7392dd.json` → `7cb49cf`, kanıt 2026-09-22T14:06:05Z
- TKNKA: `20260922T121935Z_653e87af9823.json` → `7cb49cf`, kanıt 2026-09-22T14:06:05Z
- VEYAS: `20260922T121935Z_0f4695ad423c.json` → `7cb49cf`, kanıt 2026-09-22T14:06:05Z
- BKRGY: legacy `BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING` → LEGACY_SELF_REPORTED; kanıt yok (yalnız beyan)
- INTET: legacy `INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING` → LEGACY_SELF_REPORTED; kanıt yok (yalnız beyan)
- NETGL: legacy `NETGL_20260916_V1_5` → LIVE; kanıt 2026-09-16T11:32:27Z

## 3. `v1_5_h99` — Canlı sicil (prospektif, n = 6; atlanan = 0)

n_live = 1 (LIVE), n_late = 5 (LATE_RECORD); ret = 1; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Ufuk | Sınıf | Kayıt | model R̂ | model p̂ | `base_always_ceiling` R̂ | `base_train_median` R̂ | `base_train_mean` R̂ | `base_zero` R̂ | `base_always_ceiling` p̂ | `base_rate` p̂ | `base_last10_rate` p̂ | R | Y | Durum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CITAS | D1 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.0866 | 0.941 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 1.000 | 0.899 | 0.600 | 0.0997 | 1 | OK |
| CITAS | D3 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.3082 | 0.990 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 1.000 | 0.808 | 0.500 | 0.3304 | 1 | OK |
| CITAS | D5 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.4860 | 0.986 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 1.000 | 0.778 | 0.400 | 0.6079 | 1 | OK |
| CITAS | D10 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.8833 | 0.965 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 1.000 | 0.707 | 0.500 | 0.7368 | 1 | OK |
| TKNKA | D1 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.0856 | 0.938 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 1.000 | 0.899 | 0.600 | 0.0995 | 1 | OK |
| TKNKA | D3 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.2827 | 0.981 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 1.000 | 0.808 | 0.500 | 0.3290 | 1 | OK |
| TKNKA | D5 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.4293 | 0.971 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 1.000 | 0.778 | 0.400 | 0.6066 | 1 | OK |
| TKNKA | D10 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.6865 | 0.918 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 1.000 | 0.707 | 0.500 | 1.2248 | 1 | OK |
| VEYAS | D1 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | ret (F3_MISSING) | ret (F3_MISSING) | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 1.000 | 0.899 | 0.600 | -0.0007 | 0 | REFUSED |
| VEYAS | D3 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | ret (F3_MISSING) | ret (F3_MISSING) | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 1.000 | 0.808 | 0.500 | 0.0985 | 1 | REFUSED |
| VEYAS | D5 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | ret (F3_MISSING) | ret (F3_MISSING) | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 1.000 | 0.778 | 0.400 | 0.0147 | 1 | REFUSED |
| VEYAS | D10 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | ret (F3_MISSING) | ret (F3_MISSING) | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 1.000 | 0.707 | 0.500 | 0.0000 | 0 | REFUSED |
| KPEKS | D1 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.0655 | 0.883 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 1.000 | 0.899 | 0.600 | 0.1000 | 1 | OK |
| KPEKS | D3 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.1560 | 0.782 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 1.000 | 0.808 | 0.500 | 0.3298 | 1 | OK |
| KPEKS | D5 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.2041 | 0.768 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 1.000 | 0.778 | 0.400 | 0.6085 | 1 | OK |
| KPEKS | D10 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.2167 | 0.665 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 1.000 | 0.707 | 0.500 | 0.0128 | 1 | OK |
| INTET | D1 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.0694 | 0.888 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 1.000 | 0.899 | 0.600 | 0.0998 | 1 | OK |
| INTET | D3 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.1362 | 0.697 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 1.000 | 0.808 | 0.500 | 0.3293 | 1 | OK |
| INTET | D5 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.1752 | 0.628 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 1.000 | 0.778 | 0.400 | 0.3909 | 1 | OK |
| INTET | D10 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.1166 | 0.470 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 1.000 | 0.707 | 0.500 | 0.1409 | 1 | OK |
| BKRGY | D1 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.0661 | 0.886 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 1.000 | 0.899 | 0.600 | -0.0998 | 0 | OK |
| BKRGY | D3 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.1433 | 0.698 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 1.000 | 0.808 | 0.500 | -0.2583 | 0 | OK |
| BKRGY | D5 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.1683 | 0.668 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 1.000 | 0.778 | 0.400 | -0.3155 | 0 | OK |
| BKRGY | D10 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.0637 | 0.494 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 1.000 | 0.707 | 0.500 | -0.3991 | 0 | OK |
| NETGL | D1 | LIVE | `NETGL_20260916_V1_5` | 0.0770 | 0.913 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 1.000 | 0.899 | 0.600 | 0.0995 | 1 | OK |
| NETGL | D3 | LIVE | `NETGL_20260916_V1_5` | 0.1847 | 0.857 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 1.000 | 0.808 | 0.500 | 0.3299 | 1 | OK |
| NETGL | D5 | LIVE | `NETGL_20260916_V1_5` | 0.2552 | 0.797 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 1.000 | 0.778 | 0.400 | 0.0784 | 1 | OK |
| NETGL | D10 | LIVE | `NETGL_20260916_V1_5` | 0.2583 | 0.602 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 1.000 | 0.707 | 0.500 | -0.3617 | 0 | OK |

Self-reported (ikincil; kanıtlı n'e girmez):

| Arz | Ufuk | Sınıf | Kayıt | model R̂ | model p̂ | `base_always_ceiling` R̂ | `base_train_median` R̂ | `base_train_mean` R̂ | `base_zero` R̂ | `base_always_ceiling` p̂ | `base_rate` p̂ | `base_last10_rate` p̂ | R | Y | Durum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| INTET | D1 | LEGACY_SELF_REPORTED | `INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING` | 0.0694 | 0.888 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 1.000 | 0.899 | 0.600 | 0.0998 | 1 | OK |
| INTET | D3 | LEGACY_SELF_REPORTED | `INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING` | 0.1362 | 0.697 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 1.000 | 0.808 | 0.500 | 0.3293 | 1 | OK |
| INTET | D5 | LEGACY_SELF_REPORTED | `INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING` | 0.1752 | 0.628 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 1.000 | 0.778 | 0.400 | 0.3909 | 1 | OK |
| INTET | D10 | LEGACY_SELF_REPORTED | `INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING` | 0.1166 | 0.470 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 1.000 | 0.707 | 0.500 | 0.1409 | 1 | OK |
| BKRGY | D1 | LEGACY_SELF_REPORTED | `BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING` | 0.0661 | 0.886 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 1.000 | 0.899 | 0.600 | -0.0998 | 0 | OK |
| BKRGY | D3 | LEGACY_SELF_REPORTED | `BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING` | 0.1433 | 0.698 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 1.000 | 0.808 | 0.500 | -0.2583 | 0 | OK |
| BKRGY | D5 | LEGACY_SELF_REPORTED | `BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING` | 0.1683 | 0.668 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 1.000 | 0.778 | 0.400 | -0.3155 | 0 | OK |
| BKRGY | D10 | LEGACY_SELF_REPORTED | `BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING` | 0.0637 | 0.494 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 1.000 | 0.707 | 0.500 | -0.3991 | 0 | OK |


## 3. `base_always_ceiling` — Canlı sicil (prospektif, n = 7; atlanan = 0)

n_live = 0 (LIVE), n_late = 7 (LATE_RECORD); ret = 0; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Ufuk | Sınıf | Kayıt | model R̂ | model p̂ | R | Y | Durum |
|---|---|---|---|---|---|---|---|---|
| CITAS | D1 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.1000 | 1.000 | 0.0997 | 1 | OK |
| CITAS | D3 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.3310 | 1.000 | 0.3304 | 1 | OK |
| CITAS | D5 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.6105 | 1.000 | 0.6079 | 1 | OK |
| CITAS | D10 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 1.5937 | 1.000 | 0.7368 | 1 | OK |
| TKNKA | D1 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.1000 | 1.000 | 0.0995 | 1 | OK |
| TKNKA | D3 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.3310 | 1.000 | 0.3290 | 1 | OK |
| TKNKA | D5 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.6105 | 1.000 | 0.6066 | 1 | OK |
| TKNKA | D10 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 1.5937 | 1.000 | 1.2248 | 1 | OK |
| VEYAS | D1 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.1000 | 1.000 | -0.0007 | 0 | OK |
| VEYAS | D3 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.3310 | 1.000 | 0.0985 | 1 | OK |
| VEYAS | D5 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.6105 | 1.000 | 0.0147 | 1 | OK |
| VEYAS | D10 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 1.5937 | 1.000 | 0.0000 | 0 | OK |
| KPEKS | D1 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.1000 | 1.000 | 0.1000 | 1 | OK |
| KPEKS | D3 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.3310 | 1.000 | 0.3298 | 1 | OK |
| KPEKS | D5 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.6105 | 1.000 | 0.6085 | 1 | OK |
| KPEKS | D10 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 1.5937 | 1.000 | 0.0128 | 1 | OK |
| INTET | D1 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.1000 | 1.000 | 0.0998 | 1 | OK |
| INTET | D3 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.3310 | 1.000 | 0.3293 | 1 | OK |
| INTET | D5 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.6105 | 1.000 | 0.3909 | 1 | OK |
| INTET | D10 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 1.5937 | 1.000 | 0.1409 | 1 | OK |
| BKRGY | D1 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.1000 | 1.000 | -0.0998 | 0 | OK |
| BKRGY | D3 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.3310 | 1.000 | -0.2583 | 0 | OK |
| BKRGY | D5 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.6105 | 1.000 | -0.3155 | 0 | OK |
| BKRGY | D10 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 1.5937 | 1.000 | -0.3991 | 0 | OK |
| NETGL | D1 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.1000 | 1.000 | 0.0995 | 1 | OK |
| NETGL | D3 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.3310 | 1.000 | 0.3299 | 1 | OK |
| NETGL | D5 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.6105 | 1.000 | 0.0784 | 1 | OK |
| NETGL | D10 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 1.5937 | 1.000 | -0.3617 | 0 | OK |


## 3. `base_train_median` — Canlı sicil (prospektif, n = 7; atlanan = 0)

n_live = 0 (LIVE), n_late = 7 (LATE_RECORD); ret = 0; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Ufuk | Sınıf | Kayıt | model R̂ | model p̂ | R | Y | Durum |
|---|---|---|---|---|---|---|---|---|
| CITAS | D1 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.1000 | — | 0.0997 | 1 | OK |
| CITAS | D3 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.3297 | — | 0.3304 | 1 | OK |
| CITAS | D5 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.3738 | — | 0.6079 | 1 | OK |
| CITAS | D10 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.2471 | — | 0.7368 | 1 | OK |
| TKNKA | D1 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.1000 | — | 0.0995 | 1 | OK |
| TKNKA | D3 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.3297 | — | 0.3290 | 1 | OK |
| TKNKA | D5 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.3738 | — | 0.6066 | 1 | OK |
| TKNKA | D10 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.2471 | — | 1.2248 | 1 | OK |
| VEYAS | D1 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.1000 | — | -0.0007 | 0 | OK |
| VEYAS | D3 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.3297 | — | 0.0985 | 1 | OK |
| VEYAS | D5 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.3738 | — | 0.0147 | 1 | OK |
| VEYAS | D10 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.2471 | — | 0.0000 | 0 | OK |
| KPEKS | D1 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.1000 | — | 0.1000 | 1 | OK |
| KPEKS | D3 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.3297 | — | 0.3298 | 1 | OK |
| KPEKS | D5 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.3738 | — | 0.6085 | 1 | OK |
| KPEKS | D10 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.2471 | — | 0.0128 | 1 | OK |
| INTET | D1 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.1000 | — | 0.0998 | 1 | OK |
| INTET | D3 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.3297 | — | 0.3293 | 1 | OK |
| INTET | D5 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.3738 | — | 0.3909 | 1 | OK |
| INTET | D10 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.2471 | — | 0.1409 | 1 | OK |
| BKRGY | D1 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.1000 | — | -0.0998 | 0 | OK |
| BKRGY | D3 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.3297 | — | -0.2583 | 0 | OK |
| BKRGY | D5 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.3738 | — | -0.3155 | 0 | OK |
| BKRGY | D10 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.2471 | — | -0.3991 | 0 | OK |
| NETGL | D1 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.1000 | — | 0.0995 | 1 | OK |
| NETGL | D3 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.3297 | — | 0.3299 | 1 | OK |
| NETGL | D5 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.3738 | — | 0.0784 | 1 | OK |
| NETGL | D10 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.2471 | — | -0.3617 | 0 | OK |


## 3. `base_train_mean` — Canlı sicil (prospektif, n = 7; atlanan = 0)

n_live = 0 (LIVE), n_late = 7 (LATE_RECORD); ret = 0; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Ufuk | Sınıf | Kayıt | model R̂ | model p̂ | R | Y | Durum |
|---|---|---|---|---|---|---|---|---|
| CITAS | D1 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.0774 | — | 0.0997 | 1 | OK |
| CITAS | D3 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.2097 | — | 0.3304 | 1 | OK |
| CITAS | D5 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.3121 | — | 0.6079 | 1 | OK |
| CITAS | D10 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.4725 | — | 0.7368 | 1 | OK |
| TKNKA | D1 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.0774 | — | 0.0995 | 1 | OK |
| TKNKA | D3 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.2097 | — | 0.3290 | 1 | OK |
| TKNKA | D5 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.3121 | — | 0.6066 | 1 | OK |
| TKNKA | D10 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.4725 | — | 1.2248 | 1 | OK |
| VEYAS | D1 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.0774 | — | -0.0007 | 0 | OK |
| VEYAS | D3 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.2097 | — | 0.0985 | 1 | OK |
| VEYAS | D5 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.3121 | — | 0.0147 | 1 | OK |
| VEYAS | D10 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.4725 | — | 0.0000 | 0 | OK |
| KPEKS | D1 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.0774 | — | 0.1000 | 1 | OK |
| KPEKS | D3 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.2097 | — | 0.3298 | 1 | OK |
| KPEKS | D5 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.3121 | — | 0.6085 | 1 | OK |
| KPEKS | D10 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.4725 | — | 0.0128 | 1 | OK |
| INTET | D1 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.0774 | — | 0.0998 | 1 | OK |
| INTET | D3 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.2097 | — | 0.3293 | 1 | OK |
| INTET | D5 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.3121 | — | 0.3909 | 1 | OK |
| INTET | D10 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.4725 | — | 0.1409 | 1 | OK |
| BKRGY | D1 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.0774 | — | -0.0998 | 0 | OK |
| BKRGY | D3 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.2097 | — | -0.2583 | 0 | OK |
| BKRGY | D5 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.3121 | — | -0.3155 | 0 | OK |
| BKRGY | D10 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.4725 | — | -0.3991 | 0 | OK |
| NETGL | D1 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.0774 | — | 0.0995 | 1 | OK |
| NETGL | D3 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.2097 | — | 0.3299 | 1 | OK |
| NETGL | D5 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.3121 | — | 0.0784 | 1 | OK |
| NETGL | D10 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.4725 | — | -0.3617 | 0 | OK |


## 3. `base_zero` — Canlı sicil (prospektif, n = 7; atlanan = 0)

n_live = 0 (LIVE), n_late = 7 (LATE_RECORD); ret = 0; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Ufuk | Sınıf | Kayıt | model R̂ | model p̂ | R | Y | Durum |
|---|---|---|---|---|---|---|---|---|
| CITAS | D1 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.0000 | — | 0.0997 | 1 | OK |
| CITAS | D3 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.0000 | — | 0.3304 | 1 | OK |
| CITAS | D5 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.0000 | — | 0.6079 | 1 | OK |
| CITAS | D10 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.0000 | — | 0.7368 | 1 | OK |
| TKNKA | D1 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.0000 | — | 0.0995 | 1 | OK |
| TKNKA | D3 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.0000 | — | 0.3290 | 1 | OK |
| TKNKA | D5 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.0000 | — | 0.6066 | 1 | OK |
| TKNKA | D10 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.0000 | — | 1.2248 | 1 | OK |
| VEYAS | D1 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.0000 | — | -0.0007 | 0 | OK |
| VEYAS | D3 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.0000 | — | 0.0985 | 1 | OK |
| VEYAS | D5 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.0000 | — | 0.0147 | 1 | OK |
| VEYAS | D10 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.0000 | — | 0.0000 | 0 | OK |
| KPEKS | D1 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.0000 | — | 0.1000 | 1 | OK |
| KPEKS | D3 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.0000 | — | 0.3298 | 1 | OK |
| KPEKS | D5 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.0000 | — | 0.6085 | 1 | OK |
| KPEKS | D10 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.0000 | — | 0.0128 | 1 | OK |
| INTET | D1 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.0000 | — | 0.0998 | 1 | OK |
| INTET | D3 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.0000 | — | 0.3293 | 1 | OK |
| INTET | D5 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.0000 | — | 0.3909 | 1 | OK |
| INTET | D10 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.0000 | — | 0.1409 | 1 | OK |
| BKRGY | D1 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.0000 | — | -0.0998 | 0 | OK |
| BKRGY | D3 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.0000 | — | -0.2583 | 0 | OK |
| BKRGY | D5 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.0000 | — | -0.3155 | 0 | OK |
| BKRGY | D10 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.0000 | — | -0.3991 | 0 | OK |
| NETGL | D1 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.0000 | — | 0.0995 | 1 | OK |
| NETGL | D3 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.0000 | — | 0.3299 | 1 | OK |
| NETGL | D5 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.0000 | — | 0.0784 | 1 | OK |
| NETGL | D10 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.0000 | — | -0.3617 | 0 | OK |


## 3. `base_rate` — Canlı sicil (prospektif, n = 7; atlanan = 0)

n_live = 0 (LIVE), n_late = 7 (LATE_RECORD); ret = 0; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Ufuk | Sınıf | Kayıt | model R̂ | model p̂ | R | Y | Durum |
|---|---|---|---|---|---|---|---|---|
| CITAS | D1 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | — | 0.899 | 0.0997 | 1 | OK |
| CITAS | D3 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | — | 0.808 | 0.3304 | 1 | OK |
| CITAS | D5 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | — | 0.778 | 0.6079 | 1 | OK |
| CITAS | D10 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | — | 0.707 | 0.7368 | 1 | OK |
| TKNKA | D1 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | — | 0.899 | 0.0995 | 1 | OK |
| TKNKA | D3 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | — | 0.808 | 0.3290 | 1 | OK |
| TKNKA | D5 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | — | 0.778 | 0.6066 | 1 | OK |
| TKNKA | D10 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | — | 0.707 | 1.2248 | 1 | OK |
| VEYAS | D1 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | — | 0.899 | -0.0007 | 0 | OK |
| VEYAS | D3 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | — | 0.808 | 0.0985 | 1 | OK |
| VEYAS | D5 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | — | 0.778 | 0.0147 | 1 | OK |
| VEYAS | D10 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | — | 0.707 | 0.0000 | 0 | OK |
| KPEKS | D1 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | — | 0.899 | 0.1000 | 1 | OK |
| KPEKS | D3 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | — | 0.808 | 0.3298 | 1 | OK |
| KPEKS | D5 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | — | 0.778 | 0.6085 | 1 | OK |
| KPEKS | D10 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | — | 0.707 | 0.0128 | 1 | OK |
| INTET | D1 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | — | 0.899 | 0.0998 | 1 | OK |
| INTET | D3 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | — | 0.808 | 0.3293 | 1 | OK |
| INTET | D5 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | — | 0.778 | 0.3909 | 1 | OK |
| INTET | D10 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | — | 0.707 | 0.1409 | 1 | OK |
| BKRGY | D1 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | — | 0.899 | -0.0998 | 0 | OK |
| BKRGY | D3 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | — | 0.808 | -0.2583 | 0 | OK |
| BKRGY | D5 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | — | 0.778 | -0.3155 | 0 | OK |
| BKRGY | D10 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | — | 0.707 | -0.3991 | 0 | OK |
| NETGL | D1 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | — | 0.899 | 0.0995 | 1 | OK |
| NETGL | D3 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | — | 0.808 | 0.3299 | 1 | OK |
| NETGL | D5 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | — | 0.778 | 0.0784 | 1 | OK |
| NETGL | D10 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | — | 0.707 | -0.3617 | 0 | OK |


## 3. `base_last10_rate` — Canlı sicil (prospektif, n = 7; atlanan = 0)

n_live = 0 (LIVE), n_late = 7 (LATE_RECORD); ret = 0; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Ufuk | Sınıf | Kayıt | model R̂ | model p̂ | R | Y | Durum |
|---|---|---|---|---|---|---|---|---|
| CITAS | D1 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | — | 0.600 | 0.0997 | 1 | OK |
| CITAS | D3 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | — | 0.500 | 0.3304 | 1 | OK |
| CITAS | D5 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | — | 0.400 | 0.6079 | 1 | OK |
| CITAS | D10 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | — | 0.500 | 0.7368 | 1 | OK |
| TKNKA | D1 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | — | 0.600 | 0.0995 | 1 | OK |
| TKNKA | D3 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | — | 0.500 | 0.3290 | 1 | OK |
| TKNKA | D5 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | — | 0.400 | 0.6066 | 1 | OK |
| TKNKA | D10 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | — | 0.500 | 1.2248 | 1 | OK |
| VEYAS | D1 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | — | 0.600 | -0.0007 | 0 | OK |
| VEYAS | D3 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | — | 0.500 | 0.0985 | 1 | OK |
| VEYAS | D5 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | — | 0.400 | 0.0147 | 1 | OK |
| VEYAS | D10 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | — | 0.500 | 0.0000 | 0 | OK |
| KPEKS | D1 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | — | 0.600 | 0.1000 | 1 | OK |
| KPEKS | D3 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | — | 0.500 | 0.3298 | 1 | OK |
| KPEKS | D5 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | — | 0.400 | 0.6085 | 1 | OK |
| KPEKS | D10 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | — | 0.500 | 0.0128 | 1 | OK |
| INTET | D1 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | — | 0.600 | 0.0998 | 1 | OK |
| INTET | D3 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | — | 0.500 | 0.3293 | 1 | OK |
| INTET | D5 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | — | 0.400 | 0.3909 | 1 | OK |
| INTET | D10 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | — | 0.500 | 0.1409 | 1 | OK |
| BKRGY | D1 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | — | 0.600 | -0.0998 | 0 | OK |
| BKRGY | D3 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | — | 0.500 | -0.2583 | 0 | OK |
| BKRGY | D5 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | — | 0.400 | -0.3155 | 0 | OK |
| BKRGY | D10 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | — | 0.500 | -0.3991 | 0 | OK |
| NETGL | D1 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | — | 0.600 | 0.0995 | 1 | OK |
| NETGL | D3 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | — | 0.500 | 0.3299 | 1 | OK |
| NETGL | D5 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | — | 0.400 | 0.0784 | 1 | OK |
| NETGL | D10 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | — | 0.500 | -0.3617 | 0 | OK |


## 3. `v1_6_h99` — Canlı sicil (prospektif, n = 6; atlanan = 0)

n_live = 0 (LIVE), n_late = 6 (LATE_RECORD); ret = 1; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Ufuk | Sınıf | Kayıt | model R̂ | model p̂ | `v1_5_h99` R̂ | `base_always_ceiling` R̂ | `base_train_median` R̂ | `base_train_mean` R̂ | `base_zero` R̂ | `v1_5_h99` p̂ | `base_always_ceiling` p̂ | `base_rate` p̂ | `base_last10_rate` p̂ | R | Y | Durum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CITAS | D1 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.0866 | 0.941 | 0.0866 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.941 | 1.000 | 0.899 | 0.600 | 0.0997 | 1 | OK |
| CITAS | D3 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.3082 | 0.990 | 0.3082 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.990 | 1.000 | 0.808 | 0.500 | 0.3304 | 1 | OK |
| CITAS | D5 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.4860 | 0.986 | 0.4860 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.986 | 1.000 | 0.778 | 0.400 | 0.6079 | 1 | OK |
| CITAS | D10 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.8836 | 0.965 | 0.8833 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.965 | 1.000 | 0.707 | 0.500 | 0.7368 | 1 | OK |
| TKNKA | D1 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.0856 | 0.938 | 0.0856 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.938 | 1.000 | 0.899 | 0.600 | 0.0995 | 1 | OK |
| TKNKA | D3 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.2827 | 0.981 | 0.2827 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.981 | 1.000 | 0.808 | 0.500 | 0.3290 | 1 | OK |
| TKNKA | D5 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.4293 | 0.971 | 0.4293 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.971 | 1.000 | 0.778 | 0.400 | 0.6066 | 1 | OK |
| TKNKA | D10 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.6865 | 0.918 | 0.6865 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.918 | 1.000 | 0.707 | 0.500 | 1.2248 | 1 | OK |
| VEYAS | D1 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | ret (F3_MISSING) | ret (F3_MISSING) | ret | 0.1000 | 0.1000 | 0.0774 | 0.0000 | ret | 1.000 | 0.899 | 0.600 | -0.0007 | 0 | REFUSED |
| VEYAS | D3 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | ret (F3_MISSING) | ret (F3_MISSING) | ret | 0.3310 | 0.3297 | 0.2097 | 0.0000 | ret | 1.000 | 0.808 | 0.500 | 0.0985 | 1 | REFUSED |
| VEYAS | D5 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | ret (F3_MISSING) | ret (F3_MISSING) | ret | 0.6105 | 0.3738 | 0.3121 | 0.0000 | ret | 1.000 | 0.778 | 0.400 | 0.0147 | 1 | REFUSED |
| VEYAS | D10 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | ret (F3_MISSING) | ret (F3_MISSING) | ret | 1.5937 | 0.2471 | 0.4725 | 0.0000 | ret | 1.000 | 0.707 | 0.500 | 0.0000 | 0 | REFUSED |
| KPEKS | D1 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.0655 | 0.883 | 0.0655 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.883 | 1.000 | 0.899 | 0.600 | 0.1000 | 1 | OK |
| KPEKS | D3 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.1560 | 0.782 | 0.1560 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.782 | 1.000 | 0.808 | 0.500 | 0.3298 | 1 | OK |
| KPEKS | D5 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.2041 | 0.768 | 0.2041 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.768 | 1.000 | 0.778 | 0.400 | 0.6085 | 1 | OK |
| KPEKS | D10 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.2163 | 0.665 | 0.2167 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.665 | 1.000 | 0.707 | 0.500 | 0.0128 | 1 | OK |
| INTET | D1 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.0694 | 0.888 | 0.0694 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.888 | 1.000 | 0.899 | 0.600 | 0.0998 | 1 | OK |
| INTET | D3 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.1362 | 0.697 | 0.1362 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.697 | 1.000 | 0.808 | 0.500 | 0.3293 | 1 | OK |
| INTET | D5 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.1752 | 0.628 | 0.1752 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.628 | 1.000 | 0.778 | 0.400 | 0.3909 | 1 | OK |
| INTET | D10 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.1161 | 0.470 | 0.1166 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.470 | 1.000 | 0.707 | 0.500 | 0.1409 | 1 | OK |
| BKRGY | D1 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.0661 | 0.886 | 0.0661 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.886 | 1.000 | 0.899 | 0.600 | -0.0998 | 0 | OK |
| BKRGY | D3 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.1433 | 0.698 | 0.1433 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.698 | 1.000 | 0.808 | 0.500 | -0.2583 | 0 | OK |
| BKRGY | D5 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.1683 | 0.668 | 0.1683 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.668 | 1.000 | 0.778 | 0.400 | -0.3155 | 0 | OK |
| BKRGY | D10 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.0630 | 0.494 | 0.0637 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.494 | 1.000 | 0.707 | 0.500 | -0.3991 | 0 | OK |
| NETGL | D1 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.0770 | 0.913 | 0.0770 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.913 | 1.000 | 0.899 | 0.600 | 0.0995 | 1 | OK |
| NETGL | D3 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.1847 | 0.857 | 0.1847 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.857 | 1.000 | 0.808 | 0.500 | 0.3299 | 1 | OK |
| NETGL | D5 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.2552 | 0.797 | 0.2552 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.797 | 1.000 | 0.778 | 0.400 | 0.0784 | 1 | OK |
| NETGL | D10 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.2579 | 0.602 | 0.2583 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.602 | 1.000 | 0.707 | 0.500 | -0.3617 | 0 | OK |


## 3. `v1_5_market20_v0` — Canlı sicil (prospektif, n = 6; atlanan = 0)

n_live = 0 (LIVE), n_late = 6 (LATE_RECORD); ret = 1; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Ufuk | Sınıf | Kayıt | model R̂ | model p̂ | `v1_5_h99` R̂ | `base_always_ceiling` R̂ | `base_train_median` R̂ | `base_train_mean` R̂ | `base_zero` R̂ | `v1_5_h99` p̂ | `base_always_ceiling` p̂ | `base_rate` p̂ | `base_last10_rate` p̂ | R | Y | Durum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CITAS | D1 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.0857 | 0.939 | 0.0866 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.941 | 1.000 | 0.899 | 0.600 | 0.0997 | 1 | OK |
| CITAS | D3 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.3073 | 0.998 | 0.3082 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.990 | 1.000 | 0.808 | 0.500 | 0.3304 | 1 | OK |
| CITAS | D5 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.4948 | 0.985 | 0.4860 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.986 | 1.000 | 0.778 | 0.400 | 0.6079 | 1 | OK |
| CITAS | D10 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.8672 | 0.969 | 0.8833 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.965 | 1.000 | 0.707 | 0.500 | 0.7368 | 1 | OK |
| TKNKA | D1 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.0857 | 0.939 | 0.0856 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.938 | 1.000 | 0.899 | 0.600 | 0.0995 | 1 | OK |
| TKNKA | D3 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.2827 | 0.994 | 0.2827 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.981 | 1.000 | 0.808 | 0.500 | 0.3290 | 1 | OK |
| TKNKA | D5 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.4370 | 0.971 | 0.4293 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.971 | 1.000 | 0.778 | 0.400 | 0.6066 | 1 | OK |
| TKNKA | D10 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.6879 | 0.922 | 0.6865 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.918 | 1.000 | 0.707 | 0.500 | 1.2248 | 1 | OK |
| VEYAS | D1 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | ret (F3_MISSING) | ret (F3_MISSING) | ret | 0.1000 | 0.1000 | 0.0774 | 0.0000 | ret | 1.000 | 0.899 | 0.600 | -0.0007 | 0 | REFUSED |
| VEYAS | D3 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | ret (F3_MISSING) | ret (F3_MISSING) | ret | 0.3310 | 0.3297 | 0.2097 | 0.0000 | ret | 1.000 | 0.808 | 0.500 | 0.0985 | 1 | REFUSED |
| VEYAS | D5 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | ret (F3_MISSING) | ret (F3_MISSING) | ret | 0.6105 | 0.3738 | 0.3121 | 0.0000 | ret | 1.000 | 0.778 | 0.400 | 0.0147 | 1 | REFUSED |
| VEYAS | D10 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | ret (F3_MISSING) | ret (F3_MISSING) | ret | 1.5937 | 0.2471 | 0.4725 | 0.0000 | ret | 1.000 | 0.707 | 0.500 | 0.0000 | 0 | REFUSED |
| KPEKS | D1 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.0663 | 0.888 | 0.0655 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.883 | 1.000 | 0.899 | 0.600 | 0.1000 | 1 | OK |
| KPEKS | D3 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.1573 | 0.806 | 0.1560 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.782 | 1.000 | 0.808 | 0.500 | 0.3298 | 1 | OK |
| KPEKS | D5 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.2039 | 0.772 | 0.2041 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.768 | 1.000 | 0.778 | 0.400 | 0.6085 | 1 | OK |
| KPEKS | D10 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.2413 | 0.649 | 0.2167 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.665 | 1.000 | 0.707 | 0.500 | 0.0128 | 1 | OK |
| INTET | D1 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.0722 | 0.903 | 0.0694 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.888 | 1.000 | 0.899 | 0.600 | 0.0998 | 1 | OK |
| INTET | D3 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.1393 | 0.620 | 0.1362 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.697 | 1.000 | 0.808 | 0.500 | 0.3293 | 1 | OK |
| INTET | D5 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.1850 | 0.644 | 0.1752 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.628 | 1.000 | 0.778 | 0.400 | 0.3909 | 1 | OK |
| INTET | D10 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.1722 | 0.417 | 0.1166 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.470 | 1.000 | 0.707 | 0.500 | 0.1409 | 1 | OK |
| BKRGY | D1 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.0677 | 0.895 | 0.0661 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.886 | 1.000 | 0.899 | 0.600 | -0.0998 | 0 | OK |
| BKRGY | D3 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.1454 | 0.649 | 0.1433 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.698 | 1.000 | 0.808 | 0.500 | -0.2583 | 0 | OK |
| BKRGY | D5 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.1677 | 0.678 | 0.1683 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.668 | 1.000 | 0.778 | 0.400 | -0.3155 | 0 | OK |
| BKRGY | D10 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.1041 | 0.461 | 0.0637 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.494 | 1.000 | 0.707 | 0.500 | -0.3991 | 0 | OK |
| NETGL | D1 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.0710 | 0.888 | 0.0770 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.913 | 1.000 | 0.899 | 0.600 | 0.0995 | 1 | OK |
| NETGL | D3 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.1782 | 0.919 | 0.1847 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.857 | 1.000 | 0.808 | 0.500 | 0.3299 | 1 | OK |
| NETGL | D5 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.1995 | 0.774 | 0.2552 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.797 | 1.000 | 0.778 | 0.400 | 0.0784 | 1 | OK |
| NETGL | D10 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.1436 | 0.714 | 0.2583 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.602 | 1.000 | 0.707 | 0.500 | -0.3617 | 0 | OK |


## 3. `pb_v0` — Canlı sicil (prospektif, n = 7; atlanan = 0)

n_live = 0 (LIVE), n_late = 7 (LATE_RECORD); ret = 0; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Ufuk | Sınıf | Kayıt | model R̂ | model p̂ | `v1_5_h99` R̂ | `base_always_ceiling` R̂ | `base_train_median` R̂ | `base_train_mean` R̂ | `base_zero` R̂ | `v1_5_h99` p̂ | `base_always_ceiling` p̂ | `base_rate` p̂ | `base_last10_rate` p̂ | R | Y | Durum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CITAS | D1 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.0623 | 0.874 | 0.0866 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.941 | 1.000 | 0.899 | 0.600 | 0.0997 | 1 | OK |
| CITAS | D3 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.1460 | 0.736 | 0.3082 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.990 | 1.000 | 0.808 | 0.500 | 0.3304 | 1 | OK |
| CITAS | D5 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.1967 | 0.704 | 0.4860 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.986 | 1.000 | 0.778 | 0.400 | 0.6079 | 1 | OK |
| CITAS | D10 | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.2480 | 0.625 | 0.8833 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.965 | 1.000 | 0.707 | 0.500 | 0.7368 | 1 | OK |
| TKNKA | D1 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.0658 | 0.881 | 0.0856 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.938 | 1.000 | 0.899 | 0.600 | 0.0995 | 1 | OK |
| TKNKA | D3 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.1632 | 0.769 | 0.2827 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.981 | 1.000 | 0.808 | 0.500 | 0.3290 | 1 | OK |
| TKNKA | D5 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.2178 | 0.736 | 0.4293 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.971 | 1.000 | 0.778 | 0.400 | 0.6066 | 1 | OK |
| TKNKA | D10 | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.2472 | 0.639 | 0.6865 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.918 | 1.000 | 0.707 | 0.500 | 1.2248 | 1 | OK |
| VEYAS | D1 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.0353 | 0.717 | ret | 0.1000 | 0.1000 | 0.0774 | 0.0000 | ret | 1.000 | 0.899 | 0.600 | -0.0007 | 0 | OK |
| VEYAS | D3 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | -0.0024 | 0.424 | ret | 0.3310 | 0.3297 | 0.2097 | 0.0000 | ret | 1.000 | 0.808 | 0.500 | 0.0985 | 1 | OK |
| VEYAS | D5 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | -0.0268 | 0.402 | ret | 0.6105 | 0.3738 | 0.3121 | 0.0000 | ret | 1.000 | 0.778 | 0.400 | 0.0147 | 1 | OK |
| VEYAS | D10 | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | -0.1352 | 0.370 | ret | 1.5937 | 0.2471 | 0.4725 | 0.0000 | ret | 1.000 | 0.707 | 0.500 | 0.0000 | 0 | OK |
| KPEKS | D1 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.0620 | 0.891 | 0.0655 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.883 | 1.000 | 0.899 | 0.600 | 0.1000 | 1 | OK |
| KPEKS | D3 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.1602 | 0.759 | 0.1560 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.782 | 1.000 | 0.808 | 0.500 | 0.3298 | 1 | OK |
| KPEKS | D5 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.2039 | 0.732 | 0.2041 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.768 | 1.000 | 0.778 | 0.400 | 0.6085 | 1 | OK |
| KPEKS | D10 | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.2500 | 0.654 | 0.2167 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.665 | 1.000 | 0.707 | 0.500 | 0.0128 | 1 | OK |
| INTET | D1 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.0714 | 0.892 | 0.0694 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.888 | 1.000 | 0.899 | 0.600 | 0.0998 | 1 | OK |
| INTET | D3 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.1834 | 0.799 | 0.1362 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.697 | 1.000 | 0.808 | 0.500 | 0.3293 | 1 | OK |
| INTET | D5 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.2609 | 0.765 | 0.1752 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.628 | 1.000 | 0.778 | 0.400 | 0.3909 | 1 | OK |
| INTET | D10 | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.3473 | 0.674 | 0.1166 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.470 | 1.000 | 0.707 | 0.500 | 0.1409 | 1 | OK |
| BKRGY | D1 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.0670 | 0.902 | 0.0661 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.886 | 1.000 | 0.899 | 0.600 | -0.0998 | 0 | OK |
| BKRGY | D3 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.1860 | 0.802 | 0.1433 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.698 | 1.000 | 0.808 | 0.500 | -0.2583 | 0 | OK |
| BKRGY | D5 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.2382 | 0.775 | 0.1683 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.668 | 1.000 | 0.778 | 0.400 | -0.3155 | 0 | OK |
| BKRGY | D10 | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.2727 | 0.681 | 0.0637 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.494 | 1.000 | 0.707 | 0.500 | -0.3991 | 0 | OK |
| NETGL | D1 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.0730 | 0.892 | 0.0770 | 0.1000 | 0.1000 | 0.0774 | 0.0000 | 0.913 | 1.000 | 0.899 | 0.600 | 0.0995 | 1 | OK |
| NETGL | D3 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.1896 | 0.810 | 0.1847 | 0.3310 | 0.3297 | 0.2097 | 0.0000 | 0.857 | 1.000 | 0.808 | 0.500 | 0.3299 | 1 | OK |
| NETGL | D5 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.2680 | 0.775 | 0.2552 | 0.6105 | 0.3738 | 0.3121 | 0.0000 | 0.797 | 1.000 | 0.778 | 0.400 | 0.0784 | 1 | OK |
| NETGL | D10 | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.3335 | 0.673 | 0.2583 | 1.5937 | 0.2471 | 0.4725 | 0.0000 | 0.602 | 1.000 | 0.707 | 0.500 | -0.3617 | 0 | OK |


## 3. `ceiling_hazard_v0` — Canlı sicil (prospektif, n = 6; atlanan = 0)

n_live = 0 (LIVE), n_late = 6 (LATE_RECORD); ret = 1; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Sınıf | Kayıt | model S_1/S_3/S_5/S_10 | `ceiling_hazard_v0@INF` S_1/3/5/10 | `base_km_expanding` S_1/3/5/10 | `base_km_last10` S_1/3/5/10 | `base_always_ceiling` S_1/3/5/10 | model P_close 1/3/5/10 | `v1_5_p_up_as_ceiling` 1/3/5/10 | L | tavan 1/3/5/10 | Durum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.924 / 0.825 / 0.591 / 0.256 | 0.832 / 0.671 / 0.426 / 0.137 | 0.818 / 0.667 / 0.414 / 0.141 | 0.500 / 0.320 / 0.205 / 0.059 | 1.000 / 1.000 / 1.000 / 1.000 | 0.924 / 0.828 / 0.649 / 0.362 | 0.941 / 0.990 / 0.986 / 0.965 | 5 | 1 / 1 / 1 / 0 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.906 / 0.786 / 0.519 / 0.184 | 0.832 / 0.671 / 0.426 / 0.137 | 0.818 / 0.667 / 0.414 / 0.141 | 0.500 / 0.320 / 0.205 / 0.059 | 1.000 / 1.000 / 1.000 / 1.000 | 0.906 / 0.789 / 0.588 / 0.301 | 0.938 / 0.981 / 0.971 / 0.918 | 7 | 1 / 1 / 1 / 1 | SCORED |
| VEYAS | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | ret (F3_MISSING) | 0.832 / 0.671 / 0.426 / 0.137 | 0.818 / 0.667 / 0.414 / 0.141 | 0.500 / 0.320 / 0.205 / 0.059 | 1.000 / 1.000 / 1.000 / 1.000 | ret | ret | 0 | 0 / 1 / 0 / 0 | REFUSED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.784 / 0.547 / 0.210 / 0.019 | 0.832 / 0.671 / 0.426 / 0.137 | 0.818 / 0.667 / 0.414 / 0.141 | 0.500 / 0.320 / 0.205 / 0.059 | 1.000 / 1.000 / 1.000 / 1.000 | 0.784 / 0.554 / 0.323 / 0.159 | 0.883 / 0.782 / 0.768 / 0.665 | 5 | 1 / 1 / 1 / 0 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.758 / 0.502 / 0.171 / 0.012 | 0.832 / 0.671 / 0.426 / 0.137 | 0.818 / 0.667 / 0.414 / 0.141 | 0.500 / 0.320 / 0.205 / 0.059 | 1.000 / 1.000 / 1.000 / 1.000 | 0.758 / 0.510 / 0.290 / 0.153 | 0.888 / 0.697 / 0.628 / 0.470 | 4 | 1 / 1 / 0 / 0 | SCORED |
| BKRGY | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.760 / 0.507 / 0.175 / 0.012 | 0.832 / 0.671 / 0.426 / 0.137 | 0.818 / 0.667 / 0.414 / 0.141 | 0.500 / 0.320 / 0.205 / 0.059 | 1.000 / 1.000 / 1.000 / 1.000 | 0.760 / 0.514 / 0.293 / 0.153 | 0.886 / 0.698 / 0.668 / 0.494 | 0 | 0 / 0 / 0 / 0 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.818 / 0.608 / 0.271 / 0.036 | 0.832 / 0.671 / 0.426 / 0.137 | 0.818 / 0.667 / 0.414 / 0.141 | 0.500 / 0.320 / 0.205 / 0.059 | 1.000 / 1.000 / 1.000 / 1.000 | 0.818 / 0.614 / 0.375 / 0.174 | 0.913 / 0.857 / 0.797 / 0.602 | 3 | 1 / 1 / 0 / 0 | SCORED |


## 3. `ceiling_hazard_v0@INF` — Canlı sicil (prospektif, n = 7; atlanan = 0)

n_live = 0 (LIVE), n_late = 7 (LATE_RECORD); ret = 0; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Sınıf | Kayıt | model S_1/S_3/S_5/S_10 | model P_close 1/3/5/10 | L | tavan 1/3/5/10 | Durum |
|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.832 / 0.671 / 0.426 / 0.137 | 0.832 / 0.675 / 0.508 / 0.261 | 5 | 1 / 1 / 1 / 0 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.832 / 0.671 / 0.426 / 0.137 | 0.832 / 0.675 / 0.508 / 0.261 | 7 | 1 / 1 / 1 / 1 | SCORED |
| VEYAS | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.832 / 0.671 / 0.426 / 0.137 | 0.832 / 0.675 / 0.508 / 0.261 | 0 | 0 / 1 / 0 / 0 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.832 / 0.671 / 0.426 / 0.137 | 0.832 / 0.675 / 0.508 / 0.261 | 5 | 1 / 1 / 1 / 0 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.832 / 0.671 / 0.426 / 0.137 | 0.832 / 0.675 / 0.508 / 0.261 | 4 | 1 / 1 / 0 / 0 | SCORED |
| BKRGY | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.832 / 0.671 / 0.426 / 0.137 | 0.832 / 0.675 / 0.508 / 0.261 | 0 | 0 / 0 / 0 / 0 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.832 / 0.671 / 0.426 / 0.137 | 0.832 / 0.675 / 0.508 / 0.261 | 3 | 1 / 1 / 0 / 0 | SCORED |


## 3. `pb_ceiling_v0` — Canlı sicil (prospektif, n = 7; atlanan = 0)

n_live = 0 (LIVE), n_late = 7 (LATE_RECORD); ret = 0; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Sınıf | Kayıt | model S_1/S_3/S_5/S_10 | `pb_ceiling_v0@INF` S_1/3/5/10 | `base_km_expanding` S_1/3/5/10 | `base_km_last10` S_1/3/5/10 | `base_always_ceiling` S_1/3/5/10 | model P_close 1/3/5/10 | L | tavan 1/3/5/10 | Durum |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.759 / 0.550 / 0.258 / 0.039 | 0.815 / 0.657 / 0.418 / 0.135 | 0.818 / 0.667 / 0.414 / 0.141 | 0.500 / 0.320 / 0.205 / 0.059 | 1.000 / 1.000 / 1.000 / 1.000 | 0.759 / 0.560 / 0.361 / 0.173 | 5 | 1 / 1 / 1 / 0 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.779 / 0.582 / 0.292 / 0.052 | 0.815 / 0.657 / 0.418 / 0.135 | 0.818 / 0.667 / 0.414 / 0.141 | 0.500 / 0.320 / 0.205 / 0.059 | 1.000 / 1.000 / 1.000 / 1.000 | 0.779 / 0.591 / 0.390 / 0.184 | 7 | 1 / 1 / 1 / 1 | SCORED |
| VEYAS | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.551 / 0.262 / 0.055 / 0.001 | 0.815 / 0.657 / 0.418 / 0.135 | 0.818 / 0.667 / 0.414 / 0.141 | 0.500 / 0.320 / 0.205 / 0.059 | 1.000 / 1.000 / 1.000 / 1.000 | 0.551 / 0.279 / 0.187 / 0.140 | 0 | 0 / 1 / 0 / 0 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.773 / 0.573 / 0.282 / 0.048 | 0.815 / 0.657 / 0.418 / 0.135 | 0.818 / 0.667 / 0.414 / 0.141 | 0.500 / 0.320 / 0.205 / 0.059 | 1.000 / 1.000 / 1.000 / 1.000 | 0.773 / 0.583 / 0.382 / 0.180 | 5 | 1 / 1 / 1 / 0 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.802 / 0.620 / 0.336 / 0.072 | 0.815 / 0.657 / 0.418 / 0.135 | 0.818 / 0.667 / 0.414 / 0.141 | 0.500 / 0.320 / 0.205 / 0.059 | 1.000 / 1.000 / 1.000 / 1.000 | 0.802 / 0.629 / 0.428 / 0.201 | 4 | 1 / 1 / 0 / 0 | SCORED |
| BKRGY | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.801 / 0.619 / 0.334 / 0.072 | 0.815 / 0.657 / 0.418 / 0.135 | 0.818 / 0.667 / 0.414 / 0.141 | 0.500 / 0.320 / 0.205 / 0.059 | 1.000 / 1.000 / 1.000 / 1.000 | 0.801 / 0.628 / 0.427 / 0.201 | 0 | 0 / 0 / 0 / 0 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.808 / 0.631 / 0.349 / 0.079 | 0.815 / 0.657 / 0.418 / 0.135 | 0.818 / 0.667 / 0.414 / 0.141 | 0.500 / 0.320 / 0.205 / 0.059 | 1.000 / 1.000 / 1.000 / 1.000 | 0.808 / 0.640 / 0.440 / 0.207 | 3 | 1 / 1 / 0 / 0 | SCORED |


## 3. `pb_ceiling_v0@INF` — Canlı sicil (prospektif, n = 7; atlanan = 0)

n_live = 0 (LIVE), n_late = 7 (LATE_RECORD); ret = 0; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Sınıf | Kayıt | model S_1/S_3/S_5/S_10 | model P_close 1/3/5/10 | L | tavan 1/3/5/10 | Durum |
|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.815 / 0.657 / 0.418 / 0.135 | 0.815 / 0.665 / 0.499 / 0.255 | 5 | 1 / 1 / 1 / 0 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.815 / 0.657 / 0.418 / 0.135 | 0.815 / 0.665 / 0.499 / 0.255 | 7 | 1 / 1 / 1 / 1 | SCORED |
| VEYAS | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.815 / 0.657 / 0.418 / 0.135 | 0.815 / 0.665 / 0.499 / 0.255 | 0 | 0 / 1 / 0 / 0 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.815 / 0.657 / 0.418 / 0.135 | 0.815 / 0.665 / 0.499 / 0.255 | 5 | 1 / 1 / 1 / 0 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.815 / 0.657 / 0.418 / 0.135 | 0.815 / 0.665 / 0.499 / 0.255 | 4 | 1 / 1 / 0 / 0 | SCORED |
| BKRGY | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.815 / 0.657 / 0.418 / 0.135 | 0.815 / 0.665 / 0.499 / 0.255 | 0 | 0 / 0 / 0 / 0 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.815 / 0.657 / 0.418 / 0.135 | 0.815 / 0.665 / 0.499 / 0.255 | 3 | 1 / 1 / 0 / 0 | SCORED |


## 3. `base_km_expanding` — Canlı sicil (prospektif, n = 7; atlanan = 0)

n_live = 0 (LIVE), n_late = 7 (LATE_RECORD); ret = 0; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Sınıf | Kayıt | model S_1/S_3/S_5/S_10 | model P_close 1/3/5/10 | L | tavan 1/3/5/10 | Durum |
|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.818 / 0.667 / 0.414 / 0.141 | 0.818 / 0.674 / 0.496 / 0.261 | 5 | 1 / 1 / 1 / 0 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.818 / 0.667 / 0.414 / 0.141 | 0.818 / 0.674 / 0.496 / 0.261 | 7 | 1 / 1 / 1 / 1 | SCORED |
| VEYAS | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.818 / 0.667 / 0.414 / 0.141 | 0.818 / 0.674 / 0.496 / 0.261 | 0 | 0 / 1 / 0 / 0 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.818 / 0.667 / 0.414 / 0.141 | 0.818 / 0.674 / 0.496 / 0.261 | 5 | 1 / 1 / 1 / 0 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.818 / 0.667 / 0.414 / 0.141 | 0.818 / 0.674 / 0.496 / 0.261 | 4 | 1 / 1 / 0 / 0 | SCORED |
| BKRGY | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.818 / 0.667 / 0.414 / 0.141 | 0.818 / 0.674 / 0.496 / 0.261 | 0 | 0 / 0 / 0 / 0 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.818 / 0.667 / 0.414 / 0.141 | 0.818 / 0.674 / 0.496 / 0.261 | 3 | 1 / 1 / 0 / 0 | SCORED |


## 3. `base_km_last10` — Canlı sicil (prospektif, n = 7; atlanan = 0)

n_live = 0 (LIVE), n_late = 7 (LATE_RECORD); ret = 0; hedef oluşmadı = 0; bekleyen = 0 (skorlanan ama bazı ufukları bekleyen: 0). n < 10: metrik yok, yalnız satırlar.

| Arz | Sınıf | Kayıt | model S_1/S_3/S_5/S_10 | model P_close 1/3/5/10 | L | tavan 1/3/5/10 | Durum |
|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 0.500 / 0.320 / 0.205 / 0.059 | 0.500 / 0.336 / 0.315 / 0.190 | 5 | 1 / 1 / 1 / 0 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 0.500 / 0.320 / 0.205 / 0.059 | 0.500 / 0.336 / 0.315 / 0.190 | 7 | 1 / 1 / 1 / 1 | SCORED |
| VEYAS | LATE_RECORD | `20260922T121935Z_0f4695ad423c.json` | 0.500 / 0.320 / 0.205 / 0.059 | 0.500 / 0.336 / 0.315 / 0.190 | 0 | 0 / 1 / 0 / 0 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 0.500 / 0.320 / 0.205 / 0.059 | 0.500 / 0.336 / 0.315 / 0.190 | 5 | 1 / 1 / 1 / 0 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 0.500 / 0.320 / 0.205 / 0.059 | 0.500 / 0.336 / 0.315 / 0.190 | 4 | 1 / 1 / 0 / 0 | SCORED |
| BKRGY | LATE_RECORD | `20260922T121936Z_459846d44a17.json` | 0.500 / 0.320 / 0.205 / 0.059 | 0.500 / 0.336 / 0.315 / 0.190 | 0 | 0 / 0 / 0 / 0 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 0.500 / 0.320 / 0.205 / 0.059 | 0.500 / 0.336 / 0.315 / 0.190 | 3 | 1 / 1 / 0 / 0 | SCORED |


## 4. Ayrı modeller, geçersiz kullanım, atlananlar, RETRO

### `v1_5_full20` (INDEX'te değil; tek satırlık kendi listesi)

| Arz | Sınıf | Kayıt | R̂ D1/D3/D5/D10 | p̂ D1/D3/D5/D10 | R D1/D3/D5/D10 | Durum |
|---|---|---|---|---|---|---|
| TKNKA | LEGACY_SELF_REPORTED | `TKNKA_20260819_V1_5_FULL20` | 0.0704 / 0.2403 / 0.3875 / 0.6558 | 0.845 / 0.933 / 0.905 / 0.793 | 0.0995 / 0.3290 / 0.6066 / 1.2248 | SCORED |

AYRI model (n = 20/20/20/19 eğitim); v1_5_h99 sütununa yazılmaz; metrik yok (SPEC_SCORING §6).

### Geçersiz kullanım (gri; hiçbir metriğe ve n'e girmez)

| Model | Arz | Kayıt | R̂ D1/D3/D5/D10 | Not |
|---|---|---|---|---|
| `v1_5_h99` | INTET | `INTET_20260825_V1_5` | 0.0155 / -0.0942 / -0.1492 / -0.2055 | f3'süz; model bugün RET eder (SPEC_SCORING §6: geçersiz kullanım, hiçbir metriğe ve n'e girmez) |
| `v1_5_h99` | BKRGY | `BKRGY_20260825_V1_5` | 0.0120 / -0.0895 / -0.1603 / -0.2681 | f3'süz; model bugün RET eder (SPEC_SCORING §6: geçersiz kullanım, hiçbir metriğe ve n'e girmez) |
| `v1_5_h99` | BKRGY | `BKRGY_20260825_V1_5_R2` | 0.0120 / -0.0895 / -0.1603 / -0.2681 | f3'süz; model bugün RET eder (SPEC_SCORING §6: geçersiz kullanım, hiçbir metriğe ve n'e girmez) |

İptal edilmiş kayıt: 0.

### Payda (`registry/ipos.csv`)

Kapsam içi atlanan (SKIPPED) arz: 0. Kapsam dışı (OUT_OF_SCOPE) satırlar:

| Satır | KAP | Durum ve neden |
|---|---|---|
| BEWEN | KAP_1641554 | OUT_OF_SCOPE: OTHER:HALKA_ARZ_ERTELENDI_ISLEM_GORMEDI |
| GRYAT | KAP_1644127 | OUT_OF_SCOPE: OTHER:VARANT_SERTIFIKA |
| SEKFK | KAP_1645133 | OUT_OF_SCOPE: OTHER:BEDELLI_KALAN_PAYLAR |
| BNPPI | KAP_1648967 | OUT_OF_SCOPE: OTHER:VARANT_SERTIFIKA |
| AKMEN | KAP_1651948 | OUT_OF_SCOPE: OTHER:VARANT_SERTIFIKA |
| KRTEK | KAP_1652041 | OUT_OF_SCOPE: OTHER:BEDELLI_KALAN_PAYLAR |
| GSIPD | KAP_1652496 | OUT_OF_SCOPE: OTHER:VARANT_SERTIFIKA |
| CVKMD | KAP_1653572 | OUT_OF_SCOPE: OTHER:BEDELLI_KALAN_PAYLAR |
| ISMEN | KAP_1654788 | OUT_OF_SCOPE: OTHER:VARANT_SERTIFIKA |
| INFO | KAP_1655287 | OUT_OF_SCOPE: OTHER:VARANT_SERTIFIKA |
| MARKA | KAP_1656124 | OUT_OF_SCOPE: OTHER:KOD_DEGISIKLIGI |
| ISP+ISX30 | KAP_1659130 | OUT_OF_SCOPE: OTHER:FON_BYF |
| ALVES | KAP_1660522 | OUT_OF_SCOPE: OTHER:PAZAR_DEGISIKLIGI |
| ISMDL+ISP | KAP_1662048 | OUT_OF_SCOPE: OTHER:FON_BYF |
| ZPMDK+ZPMDL | KAP_1662050 | OUT_OF_SCOPE: OTHER:FON_BYF |
| AKMEN | KAP_1662855 | OUT_OF_SCOPE: OTHER:VARANT_SERTIFIKA |
| BNPPI | KAP_1662856 | OUT_OF_SCOPE: OTHER:VARANT_SERTIFIKA |
| GRYAT | KAP_1664625 | OUT_OF_SCOPE: OTHER:VARANT_SERTIFIKA |
| GSIPD | KAP_1665181 | OUT_OF_SCOPE: OTHER:VARANT_SERTIFIKA |

RETRO (yalnız bilgi, hiçbir teraziye girmez): 77 (model, arz) çifti: `ceiling_path_v0`/CITAS, `ceiling_path_v0`/TKNKA, `ceiling_path_v0`/VEYAS, `ceiling_path_v0`/KPEKS, `ceiling_path_v0`/INTET, `ceiling_path_v0`/BKRGY, `ceiling_path_v0`/NETGL, `ceiling_path_v0@INF`/CITAS, `ceiling_path_v0@INF`/TKNKA, `ceiling_path_v0@INF`/VEYAS, `ceiling_path_v0@INF`/KPEKS, `ceiling_path_v0@INF`/INTET, `ceiling_path_v0@INF`/BKRGY, `ceiling_path_v0@INF`/NETGL, `pb_ceiling_path_v0`/CITAS, `pb_ceiling_path_v0`/TKNKA, `pb_ceiling_path_v0`/VEYAS, `pb_ceiling_path_v0`/KPEKS, `pb_ceiling_path_v0`/INTET, `pb_ceiling_path_v0`/BKRGY, `pb_ceiling_path_v0`/NETGL, `ceiling_hazard_v1_clip`/CITAS, `ceiling_hazard_v1_clip`/TKNKA, `ceiling_hazard_v1_clip`/VEYAS, `ceiling_hazard_v1_clip`/KPEKS, `ceiling_hazard_v1_clip`/INTET, `ceiling_hazard_v1_clip`/BKRGY, `ceiling_hazard_v1_clip`/NETGL, `ceiling_hazard_v1_real`/CITAS, `ceiling_hazard_v1_real`/TKNKA, `ceiling_hazard_v1_real`/VEYAS, `ceiling_hazard_v1_real`/KPEKS, `ceiling_hazard_v1_real`/INTET, `ceiling_hazard_v1_real`/BKRGY, `ceiling_hazard_v1_real`/NETGL, `ceiling_hazard_v1_pooled`/CITAS, `ceiling_hazard_v1_pooled`/TKNKA, `ceiling_hazard_v1_pooled`/VEYAS, `ceiling_hazard_v1_pooled`/KPEKS, `ceiling_hazard_v1_pooled`/INTET, `ceiling_hazard_v1_pooled`/BKRGY, `ceiling_hazard_v1_pooled`/NETGL, `ceiling_hazard_v1_pooled@INF`/CITAS, `ceiling_hazard_v1_pooled@INF`/TKNKA, `ceiling_hazard_v1_pooled@INF`/VEYAS, `ceiling_hazard_v1_pooled@INF`/KPEKS, `ceiling_hazard_v1_pooled@INF`/INTET, `ceiling_hazard_v1_pooled@INF`/BKRGY, `ceiling_hazard_v1_pooled@INF`/NETGL, `fall_d10_v0_h99`/CITAS, `fall_d10_v0_h99`/TKNKA, `fall_d10_v0_h99`/VEYAS, `fall_d10_v0_h99`/KPEKS, `fall_d10_v0_h99`/INTET, `fall_d10_v0_h99`/BKRGY, `fall_d10_v0_h99`/NETGL, `fall_d10_v0_pooled`/CITAS, `fall_d10_v0_pooled`/TKNKA, `fall_d10_v0_pooled`/VEYAS, `fall_d10_v0_pooled`/KPEKS, `fall_d10_v0_pooled`/INTET, `fall_d10_v0_pooled`/BKRGY, `fall_d10_v0_pooled`/NETGL, `fall_d10_v0_addsale`/CITAS, `fall_d10_v0_addsale`/TKNKA, `fall_d10_v0_addsale`/VEYAS, `fall_d10_v0_addsale`/KPEKS, `fall_d10_v0_addsale`/INTET, `fall_d10_v0_addsale`/BKRGY, `fall_d10_v0_addsale`/NETGL, `fall_d10_v0_pooled@ZERO`/CITAS, `fall_d10_v0_pooled@ZERO`/TKNKA, `fall_d10_v0_pooled@ZERO`/VEYAS, `fall_d10_v0_pooled@ZERO`/KPEKS, `fall_d10_v0_pooled@ZERO`/INTET, `fall_d10_v0_pooled@ZERO`/BKRGY, `fall_d10_v0_pooled@ZERO`/NETGL.

## 5. Geçmiş veri testi (retrospektif, tasarıma maruz): önceden ilan edilen birincil hücreler

Canlı sicilden AYRI terazi. Kaynak: fold ledger'ları; tam tablolar `docs/MODELS.md`'de (aralık `random.Random`, SPEC_DEVIATIONS C7). Bütün backtest hücreleri `scores/scores.json` → `models[].backtest.cells`.

| Model | Hücre | Karşılaştırılan | n (ay) | model | karşılaştırılan | fark | %95 aralık | hüküm (§8) |
|---|---|---|---|---|---|---|---|---|
| `v1_5_h99` | return D5 MAE | `base_train_median` | 87 (23) | 0.2220 | 0.3059 | -0.0839 | [-0.1343, -0.0321] | geçiyor |
| `v1_6_h99` | return D10 MAE | `v1_5_h99` | 87 (23) | 0.4485 | 0.4477 | +0.0008 | [-0.0003, +0.0028] | ayırt edilemiyor |
| `v1_5_market20_v0` | return D5 MAE | `v1_5_h99` | 87 (23) | 0.2212 | 0.2220 | -0.0008 | [-0.0178, +0.0137] | ayırt edilemiyor |
| `pb_v0` | return D5 MAE | `base_train_median` | 87 (23) | 0.2751 | 0.3106 | -0.0355 | [-0.0775, +0.0102] | ayırt edilemiyor |
| `ceiling_hazard_v0` | S RPS | `base_km_expanding` | 87 (24) | 0.1503 | 0.2072 | -0.0569 | [-0.0833, -0.0286] | geçiyor |
| `ceiling_hazard_v0` | S RPS | `base_km_last10` | 87 (24) | 0.1503 | 0.1999 | -0.0496 | [-0.0751, -0.0219] | geçiyor |
| `pb_ceiling_v0` | S RPS | `base_km_expanding` | 87 (23) | 0.1821 | 0.2144 | -0.0324 | [-0.0544, -0.0114] | geçiyor |
| `pb_ceiling_v0` | S RPS | `base_km_last10` | 87 (23) | 0.1821 | 0.2156 | -0.0335 | [-0.0612, -0.0019] | geçiyor |
| `ceiling_path_v0` | return D5 MAE | `base_train_median` | 85 (23) | 0.1842 | 0.3000 | -0.1158 | [-0.1611, -0.0738] | geçiyor |
| (C) yakın dönem: `fall_d10_v0_pooled` | p_up D10 Brier (ilk işlem ≥ 2024-01-01) | `fall_d10_v0_h99` | 75 (22) | 0.1624 | 0.1682 | -0.0058 | [-0.0340, +0.0219] | belirsiz (§5.1 etiketi, δ = +0.008) |

### 5.1 Yakın dönem blokları (backtest, H99, ilk işlem ≥ 2024-01-01; `models[].backtest.near_era`)

Etiket kuralı önceden yazılı (SPEC_HAZARD_V1 §5.1, SPEC_C_V0 §5.1): %95 aralığın alt ucu > 0 → bozuyor; üst ucu ≤ tolerans → tolerans içinde; diğer → belirsiz. (C)'de birincil hücreyi yalnız `fall_d10_v0_pooled` taşır; öteki (C) satırları §5.5 k3'ün "yakın dönem − `base_rate`" hücresidir. Hüküm sözcüğü değil etikettir.

| Model | Karşılaştırılan | Metrik | n (ay) | fark | %95 aralık | tolerans | Etiket |
|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v1_clip` | `ceiling_hazard_v0` | RPS | 78 (22) | -0.0011 | [-0.0066, +0.0049] | +0.010 | tolerans içinde |
| `ceiling_hazard_v1_real` | `ceiling_hazard_v0` | RPS | 78 (22) | +0.0104 | [+0.0028, +0.0183] | +0.010 | bozuyor |
| `ceiling_hazard_v1_pooled` | `ceiling_hazard_v0` | RPS | 78 (22) | +0.0289 | [+0.0089, +0.0518] | +0.010 | bozuyor |
| `ceiling_hazard_v1_pooled@INF` | `ceiling_hazard_v0` | RPS | 78 (22) | +0.0547 | [+0.0287, +0.0806] | +0.010 | bozuyor |
| `fall_d10_v0_h99` | `base_rate` | D10 Brier | 75 (22) | -0.0434 | [-0.0773, -0.0048] | +0.008 | tolerans içinde |
| `fall_d10_v0_pooled` | `fall_d10_v0_h99` | D10 Brier | 75 (22) | -0.0058 | [-0.0340, +0.0219] | +0.008 | belirsiz |
| `fall_d10_v0_addsale` | `base_rate` | D10 Brier | 76 (22) | -0.0065 | [-0.0301, +0.0161] | +0.008 | belirsiz |
| `fall_d10_v0_pooled@ZERO` | `base_rate` | D10 Brier | 75 (22) | -0.0043 | [-0.0162, +0.0080] | +0.008 | tolerans içinde |

### 5.2 (C) kart sayaçları: varyant sayacı ve aile keşif sayacı (yan yana, toplanmaz)

Aile keşif sayacı: `experiments/log.jsonl`'daki `kind: exploration` satırları (kaynak `docs/specs_faz7_c/ekler/denenenler.csv`, sha256 `25edc9a6e40c…`; SPEC_C_V0 §10, KARARLAR_C "Çokluk"). Varyant sayacı: aynı veri sürümündeki farklı backtest varyantları + keşif satırları (kart `n_variants_same_data`, değişmedi).

| Model | Varyant (aynı veri sürümü) | Aile keşif sayacı |
|---|---|---|
| `fall_d10_v0_h99` | 23 | 2054 |
| `fall_d10_v0_pooled` | 2059 | 2054 |
| `fall_d10_v0_addsale` | 2059 | 2054 |
| `fall_d10_v0_pooled@ZERO` | 2059 | 2054 |

## 6. Koşullu tavan skorları (canlı, j başına; SPEC_CEILING_PATH_V0 §7)

Seri j. günde sürüyorken (D_1..D_j resmi THM'de tavan) dondurulmuş kaydın S vektöründen P(L ≥ k | L ≥ j) = S_k / S_j. Skorlanan çift (arz, j): L ≥ j biliniyor ve D_{j+1}..D_10 sonuçlarının hepsi girmiş; eksik ufuk bütün modellerde aynı anda düşer. Sınıf, dayandığı kaydın sınıfıdır (j'ye göre yeniden sınıflanmaz). Metrikler `borsai/predict_path.py`'nin ortak fonksiyonlarından (`conditional_rps`, `conditional_brier`, `conditional`); yorum kararları `docs/SPEC_DEVIATIONS.md` bölüm G.

- **Farklı j'ler ve koşulsuz tablolar toplanmaz**: aynı arz birden çok j'de bulunur (bağımlı). Bu bölüm canlı sicilden (§3) ve geçmiş veri testinden (§5) ayrı bir ölçektir (`live_conditional`).
- **j başına n < 10: metrik hesaplanmaz**; yalnız satır tablosu (tahmin ve gerçekleşen). 10 ≤ n < 30: "yetersiz örnek". Bugün en büyük n = 5: hiçbir j'de koşullu hücre ya da hüküm yoktur. Satır kayıpları (RPS_j, Brier) `scores/scores.json` → `models[].conditional.by_j[].rows`.

### `ceiling_hazard_v0`

Karşılaştırılanlar, S_k / S_j: `ceiling_hazard_v0@INF`, `base_km_expanding`, `base_km_last10`, `base_always_ceiling`. Önceden ilan edilen birincil hücre (j başına ayrı): RPS_j, `base_km_last10` / `base_km_expanding` karşısında.

| j | skorlanan (LIVE / LATE) | ret | bekleyen | hedef oluşmadı | S_j = 0 | atlanan | RETRO | kayıt yok | L ≥ j henüz belirsiz | hücre |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 2 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 3 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 4 | 4 (0 / 4) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 5 | 3 (0 / 3) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 6 | 1 (0 / 1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 7 | 1 (0 / 1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 8 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 9 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |

j = 1 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_2/S_1 · S_10/S_1 | `ceiling_hazard_v0@INF` | `base_km_expanding` | `base_km_last10` | `base_always_ceiling` | Durum |
|---|---|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.945 · 0.277 | 0.898 · 0.165 | 0.864 · 0.173 | 0.800 · 0.117 | 1.000 · 1.000 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.931 · 0.203 | 0.898 · 0.165 | 0.864 · 0.173 | 0.800 · 0.117 | 1.000 · 1.000 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.836 · 0.024 | 0.898 · 0.165 | 0.864 · 0.173 | 0.800 · 0.117 | 1.000 · 1.000 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.814 · 0.015 | 0.898 · 0.165 | 0.864 · 0.173 | 0.800 · 0.117 | 1.000 · 1.000 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.863 · 0.044 | 0.898 · 0.165 | 0.864 · 0.173 | 0.800 · 0.117 | 1.000 · 1.000 | SCORED |

j = 2 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_3/S_2 · S_10/S_2 | `ceiling_hazard_v0@INF` | `base_km_expanding` | `base_km_last10` | `base_always_ceiling` | Durum |
|---|---|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.945 · 0.293 | 0.898 · 0.184 | 0.943 · 0.200 | 0.800 · 0.147 | 1.000 · 1.000 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.931 · 0.218 | 0.898 · 0.184 | 0.943 · 0.200 | 0.800 · 0.147 | 1.000 · 1.000 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.836 · 0.029 | 0.898 · 0.184 | 0.943 · 0.200 | 0.800 · 0.147 | 1.000 · 1.000 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.814 · 0.019 | 0.898 · 0.184 | 0.943 · 0.200 | 0.800 · 0.147 | 1.000 · 1.000 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.863 · 0.051 | 0.898 · 0.184 | 0.943 · 0.200 | 0.800 · 0.147 | 1.000 · 1.000 | SCORED |

j = 3 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_4/S_3 · S_10/S_3 | `ceiling_hazard_v0@INF` | `base_km_expanding` | `base_km_last10` | `base_always_ceiling` | Durum |
|---|---|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.846 · 0.310 | 0.797 · 0.205 | 0.803 · 0.212 | 0.800 · 0.184 | 1.000 · 1.000 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.813 · 0.234 | 0.797 · 0.205 | 0.803 · 0.212 | 0.800 · 0.184 | 1.000 · 1.000 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.619 · 0.035 | 0.797 · 0.205 | 0.803 · 0.212 | 0.800 · 0.184 | 1.000 · 1.000 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.584 · 0.023 | 0.797 · 0.205 | 0.803 · 0.212 | 0.800 · 0.184 | 1.000 · 1.000 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.668 · 0.059 | 0.797 · 0.205 | 0.803 · 0.212 | 0.800 · 0.184 | 1.000 · 1.000 | SCORED |

j = 4 (skorlanan n = 4):

| Arz | Sınıf | Kayıt | L | model S_5/S_4 · S_10/S_4 | `ceiling_hazard_v0@INF` | `base_km_expanding` | `base_km_last10` | `base_always_ceiling` | Durum |
|---|---|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.846 · 0.366 | 0.797 · 0.257 | 0.774 · 0.264 | 0.800 · 0.229 | 1.000 · 1.000 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.813 · 0.288 | 0.797 · 0.257 | 0.774 · 0.264 | 0.800 · 0.229 | 1.000 · 1.000 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.619 · 0.056 | 0.797 · 0.257 | 0.774 · 0.264 | 0.800 · 0.229 | 1.000 · 1.000 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.584 · 0.040 | 0.797 · 0.257 | 0.774 · 0.264 | 0.800 · 0.229 | 1.000 · 1.000 | SCORED |

j = 5 (skorlanan n = 3):

| Arz | Sınıf | Kayıt | L | model S_6/S_5 · S_10/S_5 | `ceiling_hazard_v0@INF` | `base_km_expanding` | `base_km_last10` | `base_always_ceiling` | Durum |
|---|---|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.846 · 0.433 | 0.797 · 0.322 | 0.805 · 0.341 | 0.800 · 0.287 | 1.000 · 1.000 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.813 · 0.354 | 0.797 · 0.322 | 0.805 · 0.341 | 0.800 · 0.287 | 1.000 · 1.000 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.619 · 0.091 | 0.797 · 0.322 | 0.805 · 0.341 | 0.800 · 0.287 | 1.000 · 1.000 | SCORED |

j = 6 (skorlanan n = 1):

| Arz | Sınıf | Kayıt | L | model S_7/S_6 · S_10/S_6 | `ceiling_hazard_v0@INF` | `base_km_expanding` | `base_km_last10` | `base_always_ceiling` | Durum |
|---|---|---|---|---|---|---|---|---|---|
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.813 · 0.436 | 0.797 · 0.404 | 0.818 · 0.424 | 0.800 · 0.358 | 1.000 · 1.000 | SCORED |

j = 7 (skorlanan n = 1):

| Arz | Sınıf | Kayıt | L | model S_8/S_7 · S_10/S_7 | `ceiling_hazard_v0@INF` | `base_km_expanding` | `base_km_last10` | `base_always_ceiling` | Durum |
|---|---|---|---|---|---|---|---|---|---|
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.813 · 0.536 | 0.797 · 0.507 | 0.778 · 0.519 | 0.800 · 0.448 | 1.000 · 1.000 | SCORED |

### `ceiling_hazard_v0@INF`

Karşılaştırılanlar, S_k / S_j: yok (yalnız satır; koşulsuz blokta da karşılaştırıcısı yok).

| j | skorlanan (LIVE / LATE) | ret | bekleyen | hedef oluşmadı | S_j = 0 | atlanan | RETRO | kayıt yok | L ≥ j henüz belirsiz | hücre |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 2 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 3 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 4 | 4 (0 / 4) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 5 | 3 (0 / 3) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 6 | 1 (0 / 1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 7 | 1 (0 / 1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 8 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 9 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |

j = 1 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_2/S_1 · S_10/S_1 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.898 · 0.165 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.898 · 0.165 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.898 · 0.165 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.898 · 0.165 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.898 · 0.165 | SCORED |

j = 2 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_3/S_2 · S_10/S_2 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.898 · 0.184 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.898 · 0.184 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.898 · 0.184 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.898 · 0.184 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.898 · 0.184 | SCORED |

j = 3 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_4/S_3 · S_10/S_3 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.797 · 0.205 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.797 · 0.205 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.797 · 0.205 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.797 · 0.205 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.797 · 0.205 | SCORED |

j = 4 (skorlanan n = 4):

| Arz | Sınıf | Kayıt | L | model S_5/S_4 · S_10/S_4 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.797 · 0.257 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.797 · 0.257 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.797 · 0.257 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.797 · 0.257 | SCORED |

j = 5 (skorlanan n = 3):

| Arz | Sınıf | Kayıt | L | model S_6/S_5 · S_10/S_5 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.797 · 0.322 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.797 · 0.322 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.797 · 0.322 | SCORED |

j = 6 (skorlanan n = 1):

| Arz | Sınıf | Kayıt | L | model S_7/S_6 · S_10/S_6 | Durum |
|---|---|---|---|---|---|
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.797 · 0.404 | SCORED |

j = 7 (skorlanan n = 1):

| Arz | Sınıf | Kayıt | L | model S_8/S_7 · S_10/S_7 | Durum |
|---|---|---|---|---|---|
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.797 · 0.507 | SCORED |

### `pb_ceiling_v0`

Karşılaştırılanlar, S_k / S_j: `pb_ceiling_v0@INF`, `base_km_expanding`, `base_km_last10`, `base_always_ceiling`. Önceden ilan edilen birincil hücre (j başına ayrı): RPS_j, `base_km_last10` / `base_km_expanding` karşısında.

| j | skorlanan (LIVE / LATE) | ret | bekleyen | hedef oluşmadı | S_j = 0 | atlanan | RETRO | kayıt yok | L ≥ j henüz belirsiz | hücre |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 2 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 3 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 4 | 4 (0 / 4) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 5 | 3 (0 / 3) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 6 | 1 (0 / 1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 7 | 1 (0 / 1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 8 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 9 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |

j = 1 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_2/S_1 · S_10/S_1 | `pb_ceiling_v0@INF` | `base_km_expanding` | `base_km_last10` | `base_always_ceiling` | Durum |
|---|---|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.851 · 0.051 | 0.898 · 0.165 | 0.864 · 0.173 | 0.800 · 0.117 | 1.000 · 1.000 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.864 · 0.067 | 0.898 · 0.165 | 0.864 · 0.173 | 0.800 · 0.117 | 1.000 · 1.000 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.861 · 0.062 | 0.898 · 0.165 | 0.864 · 0.173 | 0.800 · 0.117 | 1.000 · 1.000 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.880 · 0.090 | 0.898 · 0.165 | 0.864 · 0.173 | 0.800 · 0.117 | 1.000 · 1.000 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.884 · 0.098 | 0.898 · 0.165 | 0.864 · 0.173 | 0.800 · 0.117 | 1.000 · 1.000 | SCORED |

j = 2 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_3/S_2 · S_10/S_2 | `pb_ceiling_v0@INF` | `base_km_expanding` | `base_km_last10` | `base_always_ceiling` | Durum |
|---|---|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.851 · 0.060 | 0.898 · 0.184 | 0.943 · 0.200 | 0.800 · 0.147 | 1.000 · 1.000 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.864 · 0.077 | 0.898 · 0.184 | 0.943 · 0.200 | 0.800 · 0.147 | 1.000 · 1.000 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.861 · 0.072 | 0.898 · 0.184 | 0.943 · 0.200 | 0.800 · 0.147 | 1.000 · 1.000 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.880 · 0.103 | 0.898 · 0.184 | 0.943 · 0.200 | 0.800 · 0.147 | 1.000 · 1.000 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.884 · 0.111 | 0.898 · 0.184 | 0.943 · 0.200 | 0.800 · 0.147 | 1.000 · 1.000 | SCORED |

j = 3 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_4/S_3 · S_10/S_3 | `pb_ceiling_v0@INF` | `base_km_expanding` | `base_km_last10` | `base_always_ceiling` | Durum |
|---|---|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.685 · 0.071 | 0.797 · 0.205 | 0.803 · 0.212 | 0.800 · 0.184 | 1.000 · 1.000 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.708 · 0.089 | 0.797 · 0.205 | 0.803 · 0.212 | 0.800 · 0.184 | 1.000 · 1.000 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.702 · 0.084 | 0.797 · 0.205 | 0.803 · 0.212 | 0.800 · 0.184 | 1.000 · 1.000 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.736 · 0.117 | 0.797 · 0.205 | 0.803 · 0.212 | 0.800 · 0.184 | 1.000 · 1.000 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.744 · 0.126 | 0.797 · 0.205 | 0.803 · 0.212 | 0.800 · 0.184 | 1.000 · 1.000 | SCORED |

j = 4 (skorlanan n = 4):

| Arz | Sınıf | Kayıt | L | model S_5/S_4 · S_10/S_4 | `pb_ceiling_v0@INF` | `base_km_expanding` | `base_km_last10` | `base_always_ceiling` | Durum |
|---|---|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.685 · 0.103 | 0.797 · 0.257 | 0.774 · 0.264 | 0.800 · 0.229 | 1.000 · 1.000 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.708 · 0.126 | 0.797 · 0.257 | 0.774 · 0.264 | 0.800 · 0.229 | 1.000 · 1.000 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.702 · 0.119 | 0.797 · 0.257 | 0.774 · 0.264 | 0.800 · 0.229 | 1.000 · 1.000 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.736 · 0.159 | 0.797 · 0.257 | 0.774 · 0.264 | 0.800 · 0.229 | 1.000 · 1.000 | SCORED |

j = 5 (skorlanan n = 3):

| Arz | Sınıf | Kayıt | L | model S_6/S_5 · S_10/S_5 | `pb_ceiling_v0@INF` | `base_km_expanding` | `base_km_last10` | `base_always_ceiling` | Durum |
|---|---|---|---|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.685 · 0.151 | 0.797 · 0.322 | 0.805 · 0.341 | 0.800 · 0.287 | 1.000 · 1.000 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.708 · 0.178 | 0.797 · 0.322 | 0.805 · 0.341 | 0.800 · 0.287 | 1.000 · 1.000 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.702 · 0.170 | 0.797 · 0.322 | 0.805 · 0.341 | 0.800 · 0.287 | 1.000 · 1.000 | SCORED |

j = 6 (skorlanan n = 1):

| Arz | Sınıf | Kayıt | L | model S_7/S_6 · S_10/S_6 | `pb_ceiling_v0@INF` | `base_km_expanding` | `base_km_last10` | `base_always_ceiling` | Durum |
|---|---|---|---|---|---|---|---|---|---|
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.708 · 0.252 | 0.797 · 0.404 | 0.818 · 0.424 | 0.800 · 0.358 | 1.000 · 1.000 | SCORED |

j = 7 (skorlanan n = 1):

| Arz | Sınıf | Kayıt | L | model S_8/S_7 · S_10/S_7 | `pb_ceiling_v0@INF` | `base_km_expanding` | `base_km_last10` | `base_always_ceiling` | Durum |
|---|---|---|---|---|---|---|---|---|---|
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.708 · 0.355 | 0.797 · 0.507 | 0.778 · 0.519 | 0.800 · 0.448 | 1.000 · 1.000 | SCORED |

### `pb_ceiling_v0@INF`

Karşılaştırılanlar, S_k / S_j: yok (yalnız satır; koşulsuz blokta da karşılaştırıcısı yok).

| j | skorlanan (LIVE / LATE) | ret | bekleyen | hedef oluşmadı | S_j = 0 | atlanan | RETRO | kayıt yok | L ≥ j henüz belirsiz | hücre |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 2 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 3 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 4 | 4 (0 / 4) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 5 | 3 (0 / 3) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 6 | 1 (0 / 1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 7 | 1 (0 / 1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 8 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 9 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |

j = 1 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_2/S_1 · S_10/S_1 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.898 · 0.165 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.898 · 0.165 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.898 · 0.165 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.898 · 0.165 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.898 · 0.165 | SCORED |

j = 2 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_3/S_2 · S_10/S_2 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.898 · 0.184 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.898 · 0.184 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.898 · 0.184 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.898 · 0.184 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.898 · 0.184 | SCORED |

j = 3 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_4/S_3 · S_10/S_3 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.797 · 0.205 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.797 · 0.205 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.797 · 0.205 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.797 · 0.205 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.797 · 0.205 | SCORED |

j = 4 (skorlanan n = 4):

| Arz | Sınıf | Kayıt | L | model S_5/S_4 · S_10/S_4 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.797 · 0.257 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.797 · 0.257 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.797 · 0.257 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.797 · 0.257 | SCORED |

j = 5 (skorlanan n = 3):

| Arz | Sınıf | Kayıt | L | model S_6/S_5 · S_10/S_5 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.797 · 0.322 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.797 · 0.322 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.797 · 0.322 | SCORED |

j = 6 (skorlanan n = 1):

| Arz | Sınıf | Kayıt | L | model S_7/S_6 · S_10/S_6 | Durum |
|---|---|---|---|---|---|
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.797 · 0.404 | SCORED |

j = 7 (skorlanan n = 1):

| Arz | Sınıf | Kayıt | L | model S_8/S_7 · S_10/S_7 | Durum |
|---|---|---|---|---|---|
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.797 · 0.507 | SCORED |

### `base_km_expanding`

Karşılaştırılanlar, S_k / S_j: yok (yalnız satır; koşulsuz blokta da karşılaştırıcısı yok).

| j | skorlanan (LIVE / LATE) | ret | bekleyen | hedef oluşmadı | S_j = 0 | atlanan | RETRO | kayıt yok | L ≥ j henüz belirsiz | hücre |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 2 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 3 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 4 | 4 (0 / 4) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 5 | 3 (0 / 3) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 6 | 1 (0 / 1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 7 | 1 (0 / 1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 8 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 9 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |

j = 1 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_2/S_1 · S_10/S_1 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.864 · 0.173 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.864 · 0.173 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.864 · 0.173 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.864 · 0.173 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.864 · 0.173 | SCORED |

j = 2 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_3/S_2 · S_10/S_2 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.943 · 0.200 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.943 · 0.200 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.943 · 0.200 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.943 · 0.200 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.943 · 0.200 | SCORED |

j = 3 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_4/S_3 · S_10/S_3 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.803 · 0.212 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.803 · 0.212 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.803 · 0.212 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.803 · 0.212 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.803 · 0.212 | SCORED |

j = 4 (skorlanan n = 4):

| Arz | Sınıf | Kayıt | L | model S_5/S_4 · S_10/S_4 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.774 · 0.264 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.774 · 0.264 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.774 · 0.264 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.774 · 0.264 | SCORED |

j = 5 (skorlanan n = 3):

| Arz | Sınıf | Kayıt | L | model S_6/S_5 · S_10/S_5 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.805 · 0.341 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.805 · 0.341 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.805 · 0.341 | SCORED |

j = 6 (skorlanan n = 1):

| Arz | Sınıf | Kayıt | L | model S_7/S_6 · S_10/S_6 | Durum |
|---|---|---|---|---|---|
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.818 · 0.424 | SCORED |

j = 7 (skorlanan n = 1):

| Arz | Sınıf | Kayıt | L | model S_8/S_7 · S_10/S_7 | Durum |
|---|---|---|---|---|---|
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.778 · 0.519 | SCORED |

### `base_km_last10`

Karşılaştırılanlar, S_k / S_j: yok (yalnız satır; koşulsuz blokta da karşılaştırıcısı yok).

| j | skorlanan (LIVE / LATE) | ret | bekleyen | hedef oluşmadı | S_j = 0 | atlanan | RETRO | kayıt yok | L ≥ j henüz belirsiz | hücre |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 2 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 3 | 5 (0 / 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 4 | 4 (0 / 4) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 5 | 3 (0 / 3) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 6 | 1 (0 / 1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 7 | 1 (0 / 1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 8 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 9 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |

j = 1 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_2/S_1 · S_10/S_1 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.800 · 0.117 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.800 · 0.117 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.800 · 0.117 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.800 · 0.117 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.800 · 0.117 | SCORED |

j = 2 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_3/S_2 · S_10/S_2 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.800 · 0.147 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.800 · 0.147 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.800 · 0.147 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.800 · 0.147 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.800 · 0.147 | SCORED |

j = 3 (skorlanan n = 5):

| Arz | Sınıf | Kayıt | L | model S_4/S_3 · S_10/S_3 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.800 · 0.184 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.800 · 0.184 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.800 · 0.184 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.800 · 0.184 | SCORED |
| NETGL | LATE_RECORD | `20260922T121936Z_65a39d7392dd.json` | 3 | 0.800 · 0.184 | SCORED |

j = 4 (skorlanan n = 4):

| Arz | Sınıf | Kayıt | L | model S_5/S_4 · S_10/S_4 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.800 · 0.229 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.800 · 0.229 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.800 · 0.229 | SCORED |
| INTET | LATE_RECORD | `20260922T121935Z_6dccd49888dc.json` | 4 | 0.800 · 0.229 | SCORED |

j = 5 (skorlanan n = 3):

| Arz | Sınıf | Kayıt | L | model S_6/S_5 · S_10/S_5 | Durum |
|---|---|---|---|---|---|
| CITAS | LATE_RECORD | `20260922T121935Z_6356b36ec865.json` | 5 | 0.800 · 0.287 | SCORED |
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.800 · 0.287 | SCORED |
| KPEKS | LATE_RECORD | `20260922T121935Z_4ef4794c6b2b.json` | 5 | 0.800 · 0.287 | SCORED |

j = 6 (skorlanan n = 1):

| Arz | Sınıf | Kayıt | L | model S_7/S_6 · S_10/S_6 | Durum |
|---|---|---|---|---|---|
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.800 · 0.358 | SCORED |

j = 7 (skorlanan n = 1):

| Arz | Sınıf | Kayıt | L | model S_8/S_7 · S_10/S_7 | Durum |
|---|---|---|---|---|---|
| TKNKA | LATE_RECORD | `20260922T121935Z_653e87af9823.json` | 7 | 0.800 · 0.448 | SCORED |

### `ceiling_path_v0`

Karşılaştırılanlar, S_k / S_j: `ceiling_hazard_v0@INF`, `base_km_expanding`, `base_km_last10`, `base_always_ceiling`. Önceden ilan edilen birincil hücre (j başına ayrı): RPS_j, `base_km_last10` / `base_km_expanding` karşısında. Getiri/p_up ikincilleri (h ∈ {3, 5, 10}, h > j): koşullu `ceiling_path_v0@INF`; koşulsuz referans `base_train_median`, `base_rate`.

| j | skorlanan (LIVE / LATE) | ret | bekleyen | hedef oluşmadı | S_j = 0 | atlanan | RETRO | kayıt yok | L ≥ j henüz belirsiz | hücre |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 2 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 3 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 4 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | — (n < 10) |
| 5 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | — (n < 10) |
| 6 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | — (n < 10) |
| 7 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | — (n < 10) |
| 8 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 9 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |

### `ceiling_path_v0@INF`

Karşılaştırılanlar, S_k / S_j: `base_km_expanding`, `base_km_last10`, `base_always_ceiling`. Önceden ilan edilen birincil hücre (j başına ayrı): RPS_j, `base_km_last10` / `base_km_expanding` karşısında. Getiri/p_up ikincilleri (h ∈ {3, 5, 10}, h > j): koşullu —; koşulsuz referans `base_train_median`, `base_rate`.

| j | skorlanan (LIVE / LATE) | ret | bekleyen | hedef oluşmadı | S_j = 0 | atlanan | RETRO | kayıt yok | L ≥ j henüz belirsiz | hücre |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 2 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 3 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 4 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | — (n < 10) |
| 5 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | — (n < 10) |
| 6 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | — (n < 10) |
| 7 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | — (n < 10) |
| 8 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 9 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |

### `pb_ceiling_path_v0`

Karşılaştırılanlar, S_k / S_j: `pb_ceiling_v0@INF`, `base_km_expanding`, `base_km_last10`, `base_always_ceiling`. Önceden ilan edilen birincil hücre (j başına ayrı): RPS_j, `base_km_last10` / `base_km_expanding` karşısında. Getiri/p_up ikincilleri (h ∈ {3, 5, 10}, h > j): koşullu `ceiling_path_v0@INF`; koşulsuz referans `base_train_median`, `base_rate`.

| j | skorlanan (LIVE / LATE) | ret | bekleyen | hedef oluşmadı | S_j = 0 | atlanan | RETRO | kayıt yok | L ≥ j henüz belirsiz | hücre |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 2 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 3 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 4 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | — (n < 10) |
| 5 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | — (n < 10) |
| 6 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | — (n < 10) |
| 7 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | — (n < 10) |
| 8 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 9 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |

### `ceiling_hazard_v1_clip`

Karşılaştırılanlar, S_k / S_j: yok (yalnız satır; koşulsuz blokta da karşılaştırıcısı yok).

| j | skorlanan (LIVE / LATE) | ret | bekleyen | hedef oluşmadı | S_j = 0 | atlanan | RETRO | kayıt yok | L ≥ j henüz belirsiz | hücre |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 2 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 3 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 4 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | — (n < 10) |
| 5 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | — (n < 10) |
| 6 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | — (n < 10) |
| 7 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | — (n < 10) |
| 8 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 9 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |

### `ceiling_hazard_v1_real`

Karşılaştırılanlar, S_k / S_j: yok (yalnız satır; koşulsuz blokta da karşılaştırıcısı yok).

| j | skorlanan (LIVE / LATE) | ret | bekleyen | hedef oluşmadı | S_j = 0 | atlanan | RETRO | kayıt yok | L ≥ j henüz belirsiz | hücre |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 2 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 3 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 4 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | — (n < 10) |
| 5 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | — (n < 10) |
| 6 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | — (n < 10) |
| 7 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | — (n < 10) |
| 8 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 9 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |

### `ceiling_hazard_v1_pooled`

Karşılaştırılanlar, S_k / S_j: yok (yalnız satır; koşulsuz blokta da karşılaştırıcısı yok).

| j | skorlanan (LIVE / LATE) | ret | bekleyen | hedef oluşmadı | S_j = 0 | atlanan | RETRO | kayıt yok | L ≥ j henüz belirsiz | hücre |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 2 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 3 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 4 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | — (n < 10) |
| 5 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | — (n < 10) |
| 6 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | — (n < 10) |
| 7 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | — (n < 10) |
| 8 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 9 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |

### `ceiling_hazard_v1_pooled@INF`

Karşılaştırılanlar, S_k / S_j: yok (yalnız satır; koşulsuz blokta da karşılaştırıcısı yok).

| j | skorlanan (LIVE / LATE) | ret | bekleyen | hedef oluşmadı | S_j = 0 | atlanan | RETRO | kayıt yok | L ≥ j henüz belirsiz | hücre |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 2 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 3 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | — (n < 10) |
| 4 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | — (n < 10) |
| 5 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | — (n < 10) |
| 6 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | — (n < 10) |
| 7 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | — (n < 10) |
| 8 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |
| 9 | 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — (n < 10) |

## 7. D1 sonrası güncelleme (canlı POST_D1, j = 1; SPEC_POST_D1_V0 §7)

Kaynak `scores/scores_post_d1.json` (şema `borsai.scores_post_d1/1`). D1'i resmi THM üst limitinde kapatan arzda D_1 bülteninden yazılan POST_D1 kaydının (`registry/post_d1/`) S vektöründen S_k / S_1, k = 2..10; D1 hedefi skorlanmaz. Sınıf tarihlerden: model dosyası D_1'den sonraki ilk sonuç verisinin atası ve push kanıtlı mı; kaydın push kanıtı T_open'dan (D_1'i izleyen ilk resmi seans 09:40:00+03:00) önce mi; inputs_pit_ok_post_d1. Yorum kararları `docs/SPEC_DEVIATIONS.md` H28–H47.

- **Ayrı ölçek** (`live_post_d1`): koşulsuz canlı sicil (§3), koşullu bloklar (§6) ve geçmiş veri testi (§5) ile toplanmaz.
- **n < 10: metrik hesaplanmaz**, yalnız satır tablosu; 10 ≤ n < 30: "yetersiz örnek".

### `post_d1_hazard_v0`

Kart: eğitim n = 81; δ eğitim arzlarının son seans tarihi 2026-08-13 (kesim değil; şartname eğitim kesimi 2026-08-19); param sha `3f764026`; aynı veri sürümünde denenen varyant 23. Önceden ilan edilen birincil hücre: RPS_1, `ceiling_hazard_v0` koşullu karşısında. Karşılaştırılanlar: `ceiling_hazard_v0`, `ceiling_hazard_v0@INF`, `base_km_expanding`, `base_km_last10`, `base_always_ceiling`; path ikincili `ceiling_path_v0`.

| skorlanan (LIVE / LATE) | ret | atlanan | kapsam dışı (D1 tavan değil) | D1 etiketi NA | hedef oluşmadı | bekleyen | S_1 = 0 | RETRO | D1 bekleniyor | hücre |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 (0 / 0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | — (n < 10) |

Payda (`registry/ipos.csv`'de FROZEN her arz, §7.5):

| Arz | D_1 | D1 tavan | Aşama durumu | Kayıt | Sınıf |
|---|---|---|---|---|---|
| CITAS | 2026-08-18 | 1 | RETRO | — | — |
| TKNKA | 2026-08-20 | 1 | RETRO | — | — |
| VEYAS | 2026-08-20 | 0 | RETRO | — | — |
| KPEKS | 2026-08-21 | 1 | RETRO | — | — |
| INTET | 2026-09-01 | 1 | RETRO | — | — |
| BKRGY | 2026-09-02 | 0 | RETRO | — | — |
| NETGL | 2026-09-17 | 1 | RETRO | — | — |

RETRO (yalnız bilgi, hiçbir n'e girmez): 7 (model, arz) çifti: `post_d1_hazard_v0`/CITAS, `post_d1_hazard_v0`/TKNKA, `post_d1_hazard_v0`/VEYAS, `post_d1_hazard_v0`/KPEKS, `post_d1_hazard_v0`/INTET, `post_d1_hazard_v0`/BKRGY, `post_d1_hazard_v0`/NETGL.

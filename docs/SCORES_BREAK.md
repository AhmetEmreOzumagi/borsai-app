# Kırılma akşamı sicili (canlı, makine sıralı; ölçek `live_break`)

Bu sayfa `python -m borsai.scoring --break` ile `scores/scores_break.json`'dan üretilir; elle düzenlenmez. Tanımlar: `docs/specs_faz8/SPEC_BREAK_V0.md` (§2 hedefler, §5 karşılaştırıcılar, §8 öne çıkan kuralı, §9 canlı aşama `POST_BREAK`), `docs/specs/SPEC_SCORING.md` §7–§8; yorum kararları `docs/SPEC_DEVIATIONS.md` bölüm N. Kod: `borsai/scoring.py` (skor), `borsai/freeze.py` (makine kaydı), `borsai/registry.py` (kayıt bekçisi).

- **Dördüncü ölçek (`live_break`), asla toplanmaz.** Geçmiş veri testi (backtest, `docs/MODELS.md` Faz 8), canlı listeleme öncesi ve POST_D1 sicili (`docs/SCORES.md`) ve zaman-dışı terazi (`docs/SCORES_OOT.md`) ayrıdır; aralarında toplam ya da ortalama yoktur (CLAUDE.md kural 3).
- **Makine sıralı kayıt:** tahmin, donmuş model JSON'u, D_1..D_b'nin sha-pinli resmi bültenleri ve listeleme öncesi girdi dosyasından skorlama anında deterministik üretilir ve `registry/post_break/` altına append-only yazılır; insan değer girmez.
- Sınıf koddan hesaplanır, elle etiket yok: SPEC_BREAK_V0 §9.3: MACHINE_SEQUENCED = model_prospective_break VE insan kaydı yok VE inputs_pit_ok_break; LIVE = model_prospective_break VE push kanıtlı insan kaydı < T_open VE inputs_pit_ok_break (v0'da insan kaydı üreticisi yok); RETRO aksi. model_prospective_break = commit_frozen(m) atası outcome_ingest_commit_after(D_b, h ≥ b + 1) (tarihi > D_b ilk THB/THM ya da h ≥ b + 1 dolu satırı ilk yazan commit) VE modelin push kanıtı var. inputs_pit_ok_break = girdi dosyası PIT (shares_offered < D_1) VE kayıt bekçisi temiz VE D_1..D_b bülten sha'ları MANIFEST'e ve dosyaya eşit. RETRO arz hiçbir n'e girmez (yalnız §6 bilgi tablosu).
- Hedefler: F1 = `close(D_{b+1}) == lower_limit(D_{b+1})`, F2 = `F1 and close(D_{b+2}) == lower_limit(D_{b+2})`; Decimal(kapanış) == Decimal(alt limit), resmi THB kapanışı ve pinli THM alt limiti; F1 = 0 ise F2 = 0; b = 9'da F2 tanımsız.
- Fark = model − karşılaştırılan; negatif = model iyi; Brier kırpmasız. Aralık: ay-blok bootstrap (blok = gerçekleşen D_1'in takvim ayı), B = 4000, numpy PCG64 tohum 20260921, yüzdelik [2.5, 97.5]; koşul n ≥ 10 ve ≥ 6 blok.
- Dil (SPEC_SCORING §8, SPEC_BREAK_V0 §6 e): n < 10 → yalnız satır tablosu; 10 ≤ n < 30 → "yetersiz örnek"; "geçiyor" yalnız n ≥ 30 ve aralık tamamen 0'ın altındaysa; tamamen üstündeyse "geçemiyor", 0'ı içeriyorsa "ayırt edilemiyor". Model ancak birincil ve `@ZERO` hücrelerinin ikisi de "geçiyor" ise canlıda geçer.
- Üretim 2026-10-02T16:17:54Z; HEAD `71cf0791d53d3b48e5914f760fa075a7626c6a15`; borsai kaynak sha256 `3dcef9955cf8`; borsai kirli: hayır; INDEX_POST_BREAK sha256 `899cf90c805d`.

## 1. Kart: `break_floor_v0` (kural satırı `break_floor_v0@ZERO`)

| Alan | Değer |
|---|---|
| Dondurma | 2026-10-02T16:21:00+03:00 (yerel saat, kanıt değil); commit `4d3c9a26be65`; push kanıtı 2026-10-02T14:45:08Z |
| Eğitim | F1 n = 82, F2 n = 78; etiketlerin son seansı 2026-08-10; şartname kesimi 2026-08-19; parametre sha256 `81f07e78` |
| Donmuş karşılaştırıcılar | `@ZERO` F1 0.3049, F2 0.1410; kırılma türü oranı (F1) b_floor = 0: 0.1277, b_floor = 1: 0.5429 |
| Öne çıkan durum (§8 aşama 1) | öne çıkar; etiket: "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0" |
| Backtest bilgi satırı (backtest_break, first_trading_date >= 2024-01-01; toplanmaz) | F1 − ürün -0.1904 [-0.2520, -0.1247] n 69; F1 − `@ZERO` -0.0281 [-0.0453, -0.0074] n 69; "backtest'te geçiyor (tasarıma maruz)" |
| Rejim uyarısı | `FON_KRIZI_2026` (D_1 ≥ 2026-09-16, bitiş açık); model girdisi değil, n'den düşülmez |
| Varyant sayacı (aynı veri) | 24 model varyantı / 1 koşu |

## 2. Payda (ipos.csv'de FROZEN her arz; ilk tutan durum)

| Durum | Anlam | Arz |
|---|---|---|
| `RETRO` | RETRO (model bu arz için prospektif değil; yalnız bilgi) | 7 |
| `STREAK_PENDING` | seri sürüyor / kırılma günü bekleniyor | 0 |
| `STREAK_TARGET_UNAVAILABLE` | seri bozulmadan 15 seans sınırı doldu | 0 |
| `NOT_SCORABLE_STREAK_NA` | seride üst limit NA (L belirsiz) | 0 |
| `NOT_APPLICABLE_NO_BREAK` | L = 10 (kırılma yok) | 0 |
| `NOT_APPLICABLE_B10` | b = 10 (D_{b+1} yok) | 0 |
| `BULLETIN_NOT_PINNED` | D_1..D_b bülteni pinli değil | 0 |
| `INPUTS_NOT_AVAILABLE` | girdi dosyası yok | 0 |
| `CALENDAR_NOT_AVAILABLE` | takvim yok (T_open hesaplanamıyor) | 0 |
| `RECORD` | satır (makine kaydı; sınıf) | 0 |

Özdeşlik: payda 7 = aşama sayaçları + satır (0); satırlar: skorlanan 0 (makine sıralı 0 / LIVE 0), ret 0, hedef bekleniyor 0, hedef oluşmadı 0, etiket NA 0.

| Arz | D_1 | seri | L | b | D_b | durum | sınıf | makine kaydı |
|---|---|---|---|---|---|---|---|---|
| CITAS | 2026-08-18 | `BREAK` | 5 | 6 | 2026-08-25 | `RETRO` | RETRO | machine_20261002T161730Z_af6ce6567cc6.json |
| TKNKA | 2026-08-20 | `BREAK` | 7 | 8 | 2026-08-31 | `RETRO` | RETRO | machine_20261002T161730Z_130557515e13.json |
| VEYAS | 2026-08-20 | `BREAK` | 0 | 1 | 2026-08-20 | `RETRO` | RETRO | machine_20261002T161730Z_b4d19ca74cdc.json |
| KPEKS | 2026-08-21 | `BREAK` | 5 | 6 | 2026-08-28 | `RETRO` | RETRO | machine_20261002T161730Z_1510442bfbdf.json |
| INTET | 2026-09-01 | `BREAK` | 4 | 5 | 2026-09-07 | `RETRO` | RETRO | machine_20261002T161730Z_82475cb4213b.json |
| BKRGY | 2026-09-02 | `BREAK` | 0 | 1 | 2026-09-02 | `RETRO` | RETRO | machine_20261002T161730Z_0ffe802ead07.json |
| NETGL | 2026-09-17 | `BREAK` | 3 | 4 | 2026-09-22 | `RETRO` | RETRO | machine_20261002T161730Z_c5a61ad0cf26.json |

## 3. Satır tablosu (canlı satırlar; n_scored < 10 iken yalnız bu tablo)

Canlı satır yok (bütün arzlar ya RETRO ya da payda durumunda).

## 4. Hücreler (§5.2; satır başına eşleşik)

n_scored = 0 < 10: hücre yok, hüküm yok (yalnız satır tablosu).

## 5. Kalibrasyon ve rejim kırılımı (betimsel; aralık ve hüküm yok)

n_scored = 0 < 10: yok.

## 6. RETRO bilgi satırları (hiçbir n'e girmez)

| Arz | D_1 | L | b | D_b | b_floor | p_F1 | p_F2 | `@ZERO` F1 / F2 | tür oranı | ürün | rejim | uyarılar | makine kaydı | neden |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CITAS | 2026-08-18 | 5 | 6 | 2026-08-25 | 0 | 0.1383 | 0.0946 | 0.3049 / 0.1410 | 0.1277 | NOT_AVAILABLE | — | — | machine_20261002T161730Z_af6ce6567cc6.json | MODEL_FROZEN_AFTER_BREAK_OUTCOME |
| TKNKA | 2026-08-20 | 7 | 8 | 2026-08-31 | 0 | 0.1382 | 0.0952 | 0.3049 / 0.1410 | 0.1277 | NOT_AVAILABLE | — | — | machine_20261002T161730Z_130557515e13.json | MODEL_FROZEN_AFTER_BREAK_OUTCOME |
| VEYAS | 2026-08-20 | 0 | 1 | 2026-08-20 | 0 | 0.1376 | 0.0972 | 0.3049 / 0.1410 | 0.1277 | NOT_AVAILABLE | — | — | machine_20261002T161730Z_b4d19ca74cdc.json | MODEL_FROZEN_AFTER_BREAK_OUTCOME |
| KPEKS | 2026-08-21 | 5 | 6 | 2026-08-28 | 1 | 0.5389 | 0.1640 | 0.3049 / 0.1410 | 0.5429 | NOT_AVAILABLE | — | — | machine_20261002T161730Z_1510442bfbdf.json | MODEL_FROZEN_AFTER_BREAK_OUTCOME |
| INTET | 2026-09-01 | 4 | 5 | 2026-09-07 | 0 | 0.1418 | 0.0829 | 0.3049 / 0.1410 | 0.1277 | NOT_AVAILABLE | — | — | machine_20261002T161730Z_82475cb4213b.json | MODEL_FROZEN_AFTER_BREAK_OUTCOME |
| BKRGY | 2026-09-02 | 0 | 1 | 2026-09-02 | 1 | 0.5433 | 0.1523 | 0.3049 / 0.1410 | 0.5429 | NOT_AVAILABLE | — | — | machine_20261002T161730Z_0ffe802ead07.json | MODEL_FROZEN_AFTER_BREAK_OUTCOME |
| NETGL | 2026-09-17 | 3 | 4 | 2026-09-22 | 1 | 0.4991 | 0.3043 | 0.3049 / 0.1410 | 0.5429 | NOT_AVAILABLE | FON_KRIZI_2026 | B_TURNOVER_CLIPPED_TO_TRAINING_P05_P95 | machine_20261002T161730Z_c5a61ad0cf26.json | MODEL_FROZEN_AFTER_BREAK_OUTCOME |

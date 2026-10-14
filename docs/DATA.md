# Eğitim tablosu: `data/training_table.csv`

- Her arz için bir satır; toplam 99 satır ve 31 sütun.
- Sıra: `first_trading_date` artan, sonra `ticker` artan.
- Biçim: UTF-8, BOM yok, LF.
- Üretici: `data/build_training_table.py`. Sürüm ve hash'ler: `data/data_version.json`. Kabul testi: `tests/test_training_table.py`.

## Kurallar

- **Değerler kaynaktaki metin haliyle** alınır. float'a çevrilip geri yazılmaz; `Decimal("…")` ile okunmalıdır. Örnek: `R_D3` 50 basamaklı kesirli bir değerdir, `ipo_price_tl` ise `76.6` gibi yazılır.
- **Eksik değer boş hücredir.** Kaynaktaki karşılığı `DATA_NOT_FOUND`'dur. Yalnız iki sütunda eksik var: `total_demand_multiple` (2) ve `additional_sale_shares` (4).
- **Üretici yalnız kopyalar ve denetler.** Bir kaynak tutarsızlığında (ticker kümesi, ilk işlem tarihi, hedef ile seans kapanışı, kesin kesir) durur; değer düzeltmez.
- **Kapsam.** İlk işlem tarihleri 2023-09-22…2026-08-06. Sonuç seansları 2026-08-19'a kadar. 2026-08-06 sonrası listelenen arzlar tabloda yok (sıra kuralı).

Kaynak kısaltmaları (hepsi `data/raw/` altında):
- `MASTER` = `HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv`
- `PROV` = `HISTORICAL99_FROZEN_COHORT_V1_canonical_provenance.csv`
- `READY` = `HISTORICAL99_FROZEN_COHORT_V1_canonical_feature_readiness.csv`
- `TARGETS` = `HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv`
- `SESSIONS` = `HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv`

## Sütunlar

### Kimlik

| Sütun | Tanım | Kaynak | Eksik |
|---|---|---|---|
| `ticker` | BIST işlem kodu | `MASTER.ticker` | 0 |
| `first_trading_date` | İlk işlem günü (D1), YYYY-MM-DD | `MASTER.first_trading_date`. READY ve SESSIONS'ın 1. seans tarihiyle eşitliği denetlenir | 0 |
| `point_in_time_status` | Girdi değerlerinin arz anında bilindiği kanıtlı mı? `PASS` = 20 (FULL20). `UNKNOWN` = 79: eğitimde kullanılır, ama bu satırlar için point-in-time kanıtı yok (proje sahibinin kararı 3) | `PROV.point_in_time_status`. READY ile eşitliği denetlenir | 0 |

### Ham girdiler

| Sütun | Tanım | Kaynak | Eksik |
|---|---|---|---|
| `ipo_price_tl` | Halka arz fiyatı, TL/pay | `MASTER.ipo_price` | 0 |
| `shares_offered` | Satılan toplam pay. 6 arzda kullanılan ek satışı içerir (bkz. `DATA_NOTES.md` §4) | `MASTER.shares_offered` | 0 |
| `post_ipo_share_capital` | Arz sonrası çıkarılmış sermaye, pay adedi | `MASTER.post_ipo_share_capital` | 0 |
| `capital_increase_shares` | Sermaye artırımıyla satılan pay | `MASTER.capital_increase_shares` | 0 |
| `existing_share_sale_shares` | Ortak satışıyla satılan pay | `MASTER.existing_share_sale` | 0 |
| `total_demand_multiple` | Toplam talep katı (V1.5'te f3). Tanımı satırdan satıra değişir (bkz. `DATA_NOTES.md` §5) | `MASTER.total_demand_multiple`. `READY.f3_total_demand_multiple` ile eşit | 2 (ALBTN, ENDAE) |
| `total_demand_multiple_origin` | f3'ün kökeni: `SOURCE_REPORTED` 71, `CALCULATED_FROM_SOURCE_TOTALS` 16, `CALCULATED_FROM_PRIMARY_TOTALS` 8, `SOURCE_REPORTED_APPROX` 2, `DATA_NOT_FOUND` 1 (ALBTN), `LEGITIMATE_SOURCE_MISSING` 1 (ENDAE) | `MASTER.total_demand_multiple_origin` | 0 (etiket) |
| `total_demand_filter_status` | Talebin filtrelenip filtrelenmediği: `NOT_SPECIFIED` 59, `UNFILTERED` 36, `NOT_APPLICABLE` 2 (f3 yok), `SOURCE_SEQUENCE_AMBIGUOUS` 1, `FILTERED_ACCEPTED_AFTER_DUPLICATE_SCREEN` 1. V1.5 ön işlemesi bu alanı altıncı girdi olarak alır (AUDIT §1.2-j) | `MASTER.total_demand_filter_status` | 0 (etiket) |
| `additional_sale_shares` | Kullanılan ek satış payı. 95 dolu değerin 89'u sıfır, 6'sı pozitif. Özellik olarak bilgi içeriği 6 satırdır | `MASTER.additional_sale_shares` | 4 (KARCL, MASFN, ALBTN, METEN) |

Denetimde doğrulanan kimlik: `shares_offered = capital_increase_shares + existing_share_sale_shares` 93 arzda tutar. Kalan 6 arzda eşitlik ek satışla tamamlanır: `shares_offered = capital_increase_shares + existing_share_sale_shares + additional_sale_shares`.

### Hedefler

h ∈ {1, 3, 5, 10}.

| Sütun | Tanım | Kaynak | Eksik |
|---|---|---|---|
| `R_Dh` | Getiri: resmi THB kapanışı(D_h) / arz fiyatı − 1, kaynak metniyle. Kaynaktaki kesin kesirle (`target_return_exact_numerator/denominator`) eşitliği üreticide denetlenir | `TARGETS.target_return` (horizon = Dh) | 0 |
| `Y_Dh` | 1 ise kapanış(D_h) > arz fiyatı, değilse 0 | `TARGETS.above_ipo_flag` | 0 |

`Y = 1` sayıları: D1 89, D3 80, D5 77, D10 70.

D_h, ilk işlem gününden itibaren h'inci resmi BIST Pay Piyasası seansıdır:
- Resmi tam kapanış günleri sayılmaz.
- Yarım gün bir seans sayılır. H99'da 6 yarım gün seansı var: EKDMR D3, MCARD D7, LXGYO D8, GENKM D10, SVGYO D10, ENTRA D4.
- 990 seansın hepsinde işlem durumu `ACTIVE_NOT_SUSPENDED`, yani işlem durdurma yok.

Takvim: `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv`.

### Tavan

| Sütun | Tanım | Kaynak | Eksik |
|---|---|---|---|
| `ceiling_close_Dk` (k = 1..10) | 1 ise o seansın resmi kapanışı o seansın resmi üst limitine **Decimal olarak eşit**, değilse 0 | `SESSIONS.close` (THB kapanış fiyatı) ve `SESSIONS.upper_limit` (THM üst limit). İkisi de ham THB/THM metniyle 990/990 aynı | 0 |
| `ceiling_streak_L` | 1. seanstan başlayan kesintisiz tavan kapanışı sayısı (0–10). İlk 0'da durur; sonraki tavanlar sayılmaz | `ceiling_close_D1..D10`'dan | 0 |

Her seansta tavan kapanışı sayısı (D1…D10): 81, 70, 67, 54, 48, 46, 39, 30, 26, 25.

Seri dağılımı: 0:18, 1:11, 2:4, 3:13, 4:12, 5:8, 6:6, 7:6, 8:4, 9:3, 10:14. Seri ≥ 1/3/5/10 sayıları: 81/66/41/14.

**Tanım neden böyle, fiyat adımı notu:**
- Tavan, "getiri ≥ %10" diye tanımlanmaz. Üst limit, referans fiyatın %10 üstünün fiyat adımına yuvarlanmış halidir.
- 990 seansta üst limit / referans oranı 1.09604…1.1 aralığında.
- 4 arzda D1 referans fiyatı arz fiyatından bir adım farklı: LILAK 37.4 / 37.39, ARTMS 25.36 / 25.35, AVPGY 55.1 / 55.08, BORLS 25.3 / 25.29.
- Bu yüzden D1'de tavan kapatan 81 arzın yalnız 50'sinde `R_D1` tam 0.1. Diğerlerinde 0.1'in biraz altında (ör. DMRGD 0.0996) ya da üstünde (LILAK 0.10029, BORLS 0.10004).
- Etiket her zaman o seansın THM üst limitinden okunur. Kural değişirse etiket THM'yi izler, sabit bir oran kırılmaz (AUDIT §3b).

## Kaynak dosyalar ve hash'ler

`data/data_version.json` şunları listeler:
- tablonun sha256'sı;
- kullanılan beş kaynak dosyanın sha256'sı;
- üreticinin sha256'sı.

`data/raw/` altındaki her dosyanın eski yolu ve dönüşümü `docs/PROVENANCE.md`'dedir. Kanonik CSV'ler CRLF'den LF'ye çevrildi; UTF-8 BOM korundu, okurken `utf-8-sig` kullanın.

Tabloda olmayan ama `data/raw/` altında duranlar:
- `…_membership.csv`: 100'lük hedef evren, 99 üye ve 1 boşluk, `DEFERRED_RECONCILIATION`.
- `…_field_provenance.csv`: seans alanı başına kaynak.
- Oturum takvimi.
- PB kanıt CSV'si (99): talep toplama öncesi planlanan arz yapısı.
- Takvim B (910 seans) ve XU100 kapanışları: f6_market20 için.

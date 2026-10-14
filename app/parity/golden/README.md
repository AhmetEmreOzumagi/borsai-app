# Altın vektörler (SPEC_APP §1.3)

Üretici: `app/parity/gen_golden.py` (repo `.venv`, seed 20260922). Elle düzenlenmez.

```bash
.venv/bin/python app/parity/gen_golden.py          # üret
.venv/bin/python app/parity/gen_golden.py --check  # diskteki dosyalarla bayt bayt karşılaştır
```

## Dosyalar

| Dosya | İçerik |
|---|---|
| `<model_id>.jsonl` (19) | `models/INDEX.json`'un ilk 19 modeli; eski 16 modelde 392 satır (`v1_5_market20_v0`: 395; 3 satır yalnız çekirdek yol), üç tavan yolu modelinde 468 satır (392 ortak + 76 yalnız-onlara-bağlı fiyat/eşik satırı) |
| `<model_id>.conditional.jsonl` (3) | Tavan yolu koşullu karışımı (SPEC_CEILING_PATH_V0 §7): model başına 40 taban satır × (10 durum-1 + 3 sapma + 10 durum-2) vektör; ilk satırda 5 ön koşul ihlali |
| `_patched_params.jsonl` | Test içi yamalı parametrelerle 31 satır: ilk 19 (bkz. U46) `F3_FILTER_STATUS_CONFLICT`, `PARAMS_INVALID`, `SCHEMA_UNSUPPORTED`, f3 imputasyonu, market20 ret sırası; son 12 satır tavan yolu (yetersiz gözlem, havuzlama, kırpılmış havuz, `N_MIN`/`margin`/`price_field`/`survival_model_id`/`gamma`/hücre anahtarı/şema) |
| `MANIFEST.json` | seed, INDEX sha256, model kümesi, satır sayıları (`rows`, `conditional_rows`), portun tanımı olan 8 Python dosyasının sha256'sı, kapsama muafiyetleri |

**U46 (SPEC_APP EK 2 §3.5):** Aşama P1'de 16 eski `.jsonl` dosyası ve `_patched_params.jsonl`'ın ilk 19
satırı `0b67f5d` ile BAYT-EŞİTTİR; `dec_cases.json`'ın eski bölümleri de aynıdır. Denetim:
`bash app/tests/golden_unchanged.sh`. Yeni girdi satırları yalnız üç tavan yolu modeline `only` ile
bağlanır; yeni yamalı satırlar dosyanın sonuna eklenir.

Satır biçimi (bir satır bir JSON nesnesi, anahtarlar sıralı):

```json
{"case_id": "v1_5_h99/0137", "model_id": "v1_5_h99", "params_sha256": "bf80…",
 "inputs": {…model_inputs düz sözlüğü, metin değerler…},
 "extra": {"f6_market20": "…" | sayı | null, "f6_market20_refusal": null | "STALE_S0"},
 "entry": "core",                     // yalnız predict.predict doğrudan çağrılan satırlarda
 "params_patch": [[["yol", …], değer]], // yalnız _patched_params.jsonl
 "expected": {"output": {…Python çıktısı…}} | {"error": {"code": "PARAMS_INVALID"}} | {"exception": "ValueError"},
 "conditional": [ {j, S_cond[10], P_L_cond[11], p_break_next} | null, … j = 0..10 ],  // tavan modelleri
 "tags": ["edge:…", "refused:INPUT_MISSING:ipo_price_tl", "clipped:D1:UPPER", …]}
```

- Çağrı girdisi `{**inputs, **extra}`; dağıtım `borsai/freeze.py: model_kind`/`run_model` ile aynı (`entry = core`: `borsai/predict.py: predict`).
- Sonlu olmayan binary64 metin olarak yazılır: `"NaN"`, `"Infinity"`, `"-Infinity"` (Rust aynı biçimi üretir).
- `expected.exception`: Python'un etiketsiz istisna fırlattığı girdiler (f1 binary64'te 0'a düşer → `math.log(0.0)` ValueError; 28 haneli bağlamda `decimal.Overflow`). Rust bu satırlarda `DOMAIN_ERROR` döner.
- `conditional`: SPEC_APP §3g; Python'da `S[k-1]/S_j`, `P_L[l]/S_j`, `1 − S[j]/S_j` (S_0 = 1), j ≥ 10 ya da S_j = 0 → `null`. Yalnız hazard/km türlerinde; tavan yolu koşullu güncellemesi ayrı dosyadadır.

Tavan yolu koşullu dosyasının satır biçimi:

```json
{"case_id": "ceiling_path_v0/cond/0007", "base_case_id": "ceiling_path_v0/0012",
 "model_id": "ceiling_path_v0", "params_sha256": "…",
 "output": {…taban satırın expected.output'u aynen (koşullu hesabın girdisi: kayıttaki çıktı)…},
 "streak_ongoing": [{"j": 0..9, "closes": ["C_1", …, "C_j"], "expected": {"output": {…}} | {"exception": "ValueError"}}],
 "streak_ongoing_mismatch": [{"j": 1|3|5, "closes": [… son eleman C_j'nin bir adım altı], "expected": …}],
 "after_break": [{"t": 0..9, "closes": ["C_1", …, "C_t", "<baz × 0.95, 2 ondalık HALF_UP>"], "expected": …}],
 "invalid": [{"case": "streak:j=10" | …, "fn": "conditional" | "conditional_after_break", "output": {…}?, "expected": {"exception": "ValueError"}}]}
```

- `closes` limit yolunun kendi değerleridir (sapma satırları hariç): `limit_path_mismatch = 0`.
- `after_break` kırılma günü kapanışı: t = 0'da `P × 0.95`, t ≥ 1'de `C_t × 0.95` (2 ondalığa HALF_UP).
- Python `ValueError` (ön koşul ihlali) → Rust `CONDITIONAL_INVALID`.
- j = 0 vektörü koşulsuz `D{h}` ile bit-eşittir (`return, p_up, q10, q50, q90, mean, n_atoms`).

## Girdi planı (471 durum; 76'sı yalnız tavan yolu modellerinde)

- 99 H99 satırı: `data/training_table.csv`'den yalnız girdi sütunları, H99 master'dan yalnız `ipo_size_tl`, PB kanıt CSV'sinden yalnız 8 PB alanı; f6 rastgele (seed).
- 7 sicil girdisi: `registry/inputs/*.json` (`borsai.registry.model_inputs`), f6 kaydın `model_inputs`'ından.
- 80 rastgele geçerli girdi: fiyat 1–500 TL, pay 1e6–5e8, sermaye pay × (2…12), sermaye artırımı payı 0–%100, f3 0.3–60 (log-düzgün), `ipo_size_tl` bazen verilmiş bazen boş, değerlerin bir kısmı JSON sayı (Python `repr` yolu), planlanan PB yapısı ID-A/B/C'yi sağlar, ek satış tavanı bazen > 0.
- 207 uç ve ret satırı (NETGL girdileri tabanlı; 3'ü yalnız `v1_5_market20_v0` çekirdek yolu): her `INPUT_*` kodu (her zorunlu alan için ayrı `INPUT_MISSING`; `"12,5"`, `"abc"`, `"inf"`, `"nan"`, bool, liste; `""` ve `"DATA_NOT_FOUND"` eksik sayılır), Decimal sözdizimi (Unicode boşluk/rakam, alt çizgi, üs sınırları), `"1e400"` (sonlu ama binary64'e taşan), `F3_MISSING`, filtre durumları, `F4_ZERO`, her özellik için alt/üst `OUT_OF_TRAINING_RANGE`, `_pct` yuvarlama sınırları, bütün `MARKET20_<NEDEN>` kodları, f6 sayı değil / aralık dışı / sonsuz, `FEATURE_NOT_PROVIDED` (çekirdek yol), PB'nin 8 alanı, fiyat aralığı (`-`, `–`, `—`), 9 PB özdeşlik/aralık adı, 200 haneli kesinlik (`precision`), pb4 > 0, kurallar için yalnız fiyat.
- 76 tavan yolu satırı (`only = ceiling_path_v0, ceiling_path_v0@INF, pb_ceiling_path_v0`; `ipo_price_tl` ve `ipo_price_try` aynı değere çekilir, PB özdeşlikleri korunur): 21 fiyat adımı sınırı, 16 üst limit adım geçişi, 11 snap (HALF_UP), 15 üs biçimi (`1E2`, `1e400`, `1e-400`, "1"+61 sıfır, uzun kesirli fiyatlar → `Inexact`), 9 f3 merdiveni (S_h eşiği), 4 PB fiyat biçimi.
- Kırpma araması: 21 tekli + ikili uç aday (f1 → ∞ / → 0, f2 = 100, f6 ±∞, pb1 uçları …); her (model, ufuk, yön) için ilk ulaşan aday satır olarak eklenir (2 yeni satır; diğer hedefleri uç satırlar zaten karşılar, etiketleri birleştirilir).

## Kapsama (U3, `cargo test -p borsai_predict --test coverage`)

Her T-2 ret kodu ve uyarı kodu ≥ 2 satırda. Sayım `expected`'tan yapılır; tablo `target/golden_coverage.json`'a yazılır.

| Kod | Satır | Kod | Satır |
|---|---|---|---|
| INPUT_MISSING | 128 | MARKET20_NOT_PROVIDED | 18 (+1 yamalı) |
| INPUT_NOT_NUMERIC | 107 | MARKET20_NOT_NUMERIC | 4 |
| INPUT_NOT_POSITIVE | 54 | MARKET20_CALENDAR_NOT_COVERING | 2 |
| INPUT_NEGATIVE | 10 | MARKET20_INSUFFICIENT_HISTORY | 2 |
| DIVISION_BY_ZERO | 20 | MARKET20_XU100_CLOSE_MISSING | 2 |
| INPUT_INCONSISTENT | 20 | MARKET20_STALE_S0 | 6 |
| F3_MISSING | 36 | MARKET20_PREDICTION_TOO_EARLY | 3 |
| F3_FILTER_STATUS_CONFLICT | 0 (+3 yamalı) | MARKET20_XU100_INTEGRITY | 2 |
| FEATURE_NOT_PROVIDED | 2 | PB_FIELD_MISSING | 84 |
| OUT_OF_TRAINING_RANGE | 1195 | PB_IDENTITY | 108 |
| F4_ZERO_NO_TRAINING_EXAMPLE | 56 | PB_PRICE_RANGE | 22 |
| F3_WINSORIZED | 198 | PB4_ADDITIONAL_SALE_CEILING | 99 |
| F3_CLIPPED_TO_TRAINING_P05_P95 | 145 | RETURN_CLIPPED_TO_PHYSICAL_BOUND | 393 |

Tavan yolu kapsaması (U44, `path_coverage` → `target/golden_coverage_path.json`):

| Ölçüt | `ceiling_path_v0` | `@INF` | `pb_ceiling_path_v0` |
|---|---|---|---|
| `IPO_PRICE_NOT_ON_TICK_GRID` | 90 | 91 | 79 |
| `expected.exception` (Inexact/Overflow/ValueError) | 6 | 3 | 3 |
| snap = P / snap ≠ P | 276 / 129 | 320 / 132 | 304 / 89 |
| `ipo_price_tl` reddi (`@INF` fiyat yolu) | 13 | 13 | — (PB alanı) |
| koşullu j = 0..9 ve t = 0..9 | 40'ar | 40'ar | 40'ar |

Yamalı satırlarda: 20 `POST_BREAK_INSUFFICIENT` hücresi, 34 `pooled` hücre, 8 kırpılmış havuz değeri
(dondurulmuş hücrelerde havuzlama ve kırpma HİÇ tetiklenmez: her hücre ≥ 11 gözlem).

`RETURN_CLIPPED_TO_PHYSICAL_BOUND`: getiri başlığı sabit olmayan 4 modelin (`v1_5_h99`, `v1_6_h99`,
`v1_5_market20_v0`, `pb_v0`) 4 ufkunun hepsinde UPPER ve LOWER en az birer satırda; ulaşılamayan ufuk
yok. Bütün modellerde f1/pb1 katsayısı her ufukta negatif: f1 → ∞ LOWER, f1 → 0 (log çok negatif) UPPER.
Kural modellerinin getirileri sabittir ve sınır içindedir (kırpma tanım gereği yok).

Muafiyetler (`MANIFEST.json: coverage_exemptions`):
- `OUT_OF_TRAINING_RANGE` f4 üst: f4 ≤ 100 (`INPUT_INCONSISTENT`), eğitim üst sınırı 100.
- `OUT_OF_TRAINING_RANGE` pb3 üst: pb3 > 100 `PB3_RANGE` ile reddedilir, eğitim üst sınırı 100.
- `S_H_THRESHOLD` (`ceiling_path_v0@INF`): sıfır modelin özelliği yoktur, S sabittir; S_h eşiğinin
  iki yanı aynı dosyada bulunamaz (ana ve PB modellerinde f3 merdiveniyle her ikisi de ≥ 5 satır).
- `POST_BREAK_POOLING`: dondurulmuş hücrelerde havuzlama tetiklenmez (her hücre ≥ 11); havuzlama,
  yetersizlik ve kırpma yalnız `_patched_params.jsonl`'ın tavan yolu satırlarıyla sınanır.
- `F3_FILTER_STATUS_CONFLICT`: kayıtlı modellerde `f3_filter_mode = NOT_SPECIFIED`; ret yolu yalnız
  yamalı parametreyle (`_patched_params.jsonl`, 3 satır) sınanır. Kayıtlı modellerde FILTERED/UNFILTERED
  girdisi "ret yok" satırı olarak yer alır.

## Ulaşılamayan / Python'da tanımsız yollar

- PB'de `int / int` taşması (OverflowError) ulaşılamaz: 200 haneli kesin bağlam `pb4`'ü ≤ 10^201 ile sınırlar.
- Python'un etiketsiz istisnaları (12 satır: 8 ValueError, 4 decimal.Overflow) altın vektörde
  `expected.exception` olarak durur; Rust `DOMAIN_ERROR` döner. Bu girdiler Python'da kayıt da üretmez.

## Faz 7 `ceiling_hazard_v1` (SPEC_APP EK 3 §4, Aşama P1)

Model kümesi 23: INDEX'in son dört kaydı (`ceiling_hazard_v1_clip`, `_real`, `_pooled`, `_pooled@INF`) eklendi. Eski
19 dosya (16'sı `0b67f5d`, üç tavan yolu dosyası ve koşullu dosyaları `7133991` ile) BAYT-EŞİT; yamalı dosyanın ilk
31 satırı aynı (U55, `golden_unchanged.sh`). v1 dosyaları 616 satır: ortak 392 satır (TÜFE anahtarı yok → real ve
pooled `TUFE_MISSING`, clip ve @INF tahmin) + yalnız v1'e bağlı 224 satır (`only = V1_IDS`):

- H99 + TÜFE (99): H99 girdileri + `tufe_index = tufe.index_for(ilk işlem günü)` (T'nin ayı − 2).
- Eski kohort açık kümesi + TÜFE + rejim (71): `registry/oot/cohort_pre_h99.csv`'nin YALNIZ `vault != SEALED`
  üyeleri (`_assert_open` bekçisi), girdiler `registry/oot/inputs/<üye>.json` → `registry.model_inputs` (ticker yok),
  `alloc_regime` kohort satırının `ALLOC_REGIME` etiketi. `case_id` kodsuz: `<model>/oot/<sıra>`. r = 1 (PRE/THRESH)
  56 üye, r = 0 (EQUAL_DIST) 15 üye.
- Canlı sicil + TÜFE (7), uç durumlar (47): her v1 kırpma sütununda p05 / 2 ve 2 · p95, f1r'nin TÜFE ile kırpılması,
  iki sütun birden, `tufe_index` biçimleri ve retleri, `tufe_refusal` kodları, `alloc_regime` etiketleri, f3 boş + TÜFE.

Yamalı satırlar 31 → 43 (EK 3 §4.3; silme yerine null / boş sözlük / sütunsuz kopya: aynı ret yolu). Kapsama (U54,
`cargo test -p borsai_predict --test coverage v1_coverage` → `target/golden_coverage_v1.json`): `TUFE_MISSING` her
girdi yolunda ≥ 2, `TUFE_NOT_PIT` 2, `TUFE_FILE_MISMATCH` 2, `REGIME_UNKNOWN` pooled 4 / @INF 4, `regime_source`
LIVE_VALUE 665 / ALLOC_REGIME_INPUT 145, `regime_value_used = 1` 113 satır, her sütunda alt/üst kırpma ≥ 2, iki ve
daha çok sütunlu `clipped_features` 109 satır; @INF'te `clipped` ve `clipped_features` her satırda null. Hijyen:
`test_gen_golden.py::test_no_sealed_code_in_golden` (kasa kodu hiçbir dosyada yok; açık küme satırlarında kod yok).

# Rust ↔ Python parite (SPEC_APP §1.2–§1.3)

`predict`'in uygulamadaki tek gerçeklemesi `src-tauri/crates/borsai_predict`'tir; tanım Python'dakidir
(`borsai/predict.py`, `predict_hazard.py`, `predict_pb.py`, `predict_market20.py`, `predict_path.py`,
`features.py`, `horizons.py`, `survival.py`). Parite Python'un ürettiği altın vektörlerle sınanır.

| Dosya | Görev |
|---|---|
| `gen_golden.py` | Altın vektör ve `dec_cases.json` üreticisi (repo `.venv`, yalnız okur, yalnız stdlib predict yolu) |
| `test_gen_golden.py` | U1 Python tarafı: numpy/scikit-learn import edilmez; `--check` bayt bayt; ≥ 200 satır |
| `golden/` | 23 model × ≥ 200 satır (tavan yolu ≥ 450, Faz 7 v1 ≥ 600) + üç `.conditional.jsonl` + `_patched_params.jsonl` + `MANIFEST.json` (bkz. `golden/README.md`) |
| `tufe_cases.json` | TÜFE tablosu okuma/denetim durumları (EK 3 §3.5, U56; `gen_golden.py --tufe-cases`) |
| `dec_cases.json` | U4 + U47 birim durumları (Decimal ayrıştırma, `_pct`, 28 hane çarpma, `float(Decimal)`, `sum()`, `int/int`, 200 hane kesin bağlam, pb1 ln, `limit_path`: 60 hane kesin bağlam + fiyat adımı tablosu) |
| `incidents/` | Dondur akışında parite uyuşmazlığı kayıtları (aşama 3; şimdilik boş) |
| `bit_equal_floor.json` | Model başına bit-eşit altın satır tabanı: `golden_parity` her modelde `bit_equal_rows ≥ taban` sınar (tolerans içi sessiz sürüklenme; FAZ3_APP_AUDIT B10). Tabanı olmayan model kırmızıdır; yeni model eklenince taban bilerek yazılır |

```bash
# repo kökünden
.venv/bin/python app/parity/gen_golden.py            # yeniden üret (Python predict değişirse)
.venv/bin/python app/parity/gen_golden.py --check    # diskteki dosyalar güncel mi
.venv/bin/pytest -q app/parity/test_gen_golden.py    # U1 (Python)
source app/scripts/env.sh && cd app/src-tauri
cargo test -p borsai_predict --test golden           # U1, U2, U37, U42, U43, U45 -> target/parity_report.json
cargo test -p borsai_predict --test coverage         # U3, U44 -> target/golden_coverage{,_path}.json
cargo test -p borsai_predict --test dec_semantics    # U4, U47
BORSAI_REPO=$(cd ../.. && pwd) cargo test -p borsai_predict --test records_parity   # U6 (+ EK 2 §3.7)
cd ../.. && bash app/tests/golden_unchanged.sh        # U46 + U55: eski 19 altın dosya bayt-eşit
```

`golden` testi ayrıca `MANIFEST.json: predict_sources_sha256`'yı diskteki Python dosyalarıyla karşılaştırır:
Python predict tanımı değişirse test kırmızıdır; altın vektörler yeniden üretilir ve Rust uyumlanır
(tolerans gevşetilmez).

## Sayısal kararlar (SPEC_APP §1.3 tablosu) ve Rust'taki karşılıkları

| Konu | Rust |
|---|---|
| Girdi ayrıştırma | `dec::parse`: CPython 3.12 `_decimal` + libmpdec birebir: `str.strip()` boşluk kümesi, alt çizgilerin atılması, Unicode ondalık rakamlar (Unicode 15.0 tablosu), `inf`/`nan`/`sNaN`, `MAX_EMAX`/`MIN_ETINY` üs sınırları. Değer kesin: `Dec` = BigUint katsayı × 10^i64 üs |
| f1 = pay × fiyat | `dec::mul_round(…, 28)` HALF_EVEN; bağlam taşması (Emax 999999) Python'da `decimal.Overflow` → Rust `DOMAIN_ERROR` |
| f2, f4 (`_pct`) | `dec::pct`: 28 hanede bölüm HALF_EVEN, ×100 (kesin), 10 ondalığa HALF_UP |
| Decimal → binary64 | ondalık metin → `str::parse::<f64>()` (doğru yuvarlama) |
| pb2, pb3, pb4 | `dec::ratio_to_f64`: < 2^53 ise IEEE bölme, değilse BigInt 55 bit + yapışkan bit, HALF_EVEN, alt-normal dahil |
| pb1 | kesin çarpım → binary64 → `f64::ln`; değer binary64 normal aralığı dışındaysa (taşma/alt-normal) ln(m) + E·ln 10 |
| `sum(c·z) + b` | `sum::py_sum`: CPython 3.12 Neumaier (başlangıç tamsayı 0) |
| min/max | `py_min`/`py_max`: Python `min`/`max` (NaN sırası korunur) |
| exp, log | `f64::exp`, `f64::ln` (Apple libm); `math.log(x ≤ 0)` Python'da ValueError → Rust `DOMAIN_ERROR` |
| Fiziksel sınırlar | kesin metinler: D1 ±0.1, D3 [−0.271, 0.331], D5 [−0.40951, 0.61051], D10 [−0.6513215599, 1.5937424601] |
| JSON sayıları | `serde_json` `float_roundtrip` (doğru yuvarlanmış ayrıştırma) + `preserve_order` |
| Limit yolu C_h (kesin, prec 60) | `dec::div_exact` (libmpdec üs kuralı: sonuç üssü `exp(a) − exp(b)`'den küçük/eşit, katsayı tamsayı olan en büyük üs), `dec::mul_ctx`, `dec::ctx_round` (kesin kısalma; kalan ≠ 0 → Python `Inexact` → `DOMAIN_ERROR`), `dec::to_integral` (FLOOR/HALF_UP, `exp ≥ 0` ise üs korunur) |
| `str(Decimal)` metinleri | `dec::py_str`: CPython `to_sci_string` (`1E+2`, `1E-7`, `0.000001`, `1.0`, `0.00`) — `limit_path` alanları BİREBİR sınanır |
| C/P oranları | `path::ratio` / `ratio_minus_one`: 60 haneye HALF_EVEN, sonra bir kez binary64 (Python `_RATIO`; çift yuvarlama aynen, kesin rasyonelden kısayol YOK) |
| Karışım (tavan yolu) | atomlar Python ekleme sırasıyla; `sort_by` kararlı; kümülatif toplam düz `+=`; `p_up`/`mean` `sum::py_sum`; kuantil eşiği `q − 1e-12` her çağrıda hesaplanır |
| Fiziksel sınırlar (hücre kırpma) | `path::physical_bounds(m)`: m = 1..10 için `(0.9^m − 1, 1.1^m − 1)` kesin metinleri |

## Faz 7C düşen arz ailesi: referans kilidi (SPEC_APP EK 3 §8, U76; P4 adım 0, 2026-10-01)

Referans: `borsai/predict_fall.py` (sha256 `MANIFEST.json: predict_sources_sha256`), `borsai/freeze.py: model_kind`, dondurulmuş
dört JSON (`fall_d10_v0_h99`, `_pooled`, `_addsale`, `_pooled@ZERO`; INDEX 27 giriş, `7e636e8b…`). EK 3 §8 Python referansı yokken
yazılmıştı; çelişkide **Python kazanır** (Rust bir porttur, EK 3 değişmez). Ölçülen farklar:

| # | Konu | EK 3 §8 | Python (Rust bunu izler) |
|---|---|---|---|
| 1 | Tür adı ve ayrım | `Kind::Fall`; `family == "fall_d10_v0"` → Fall, `RIDGE_LOGIT`'ten önce | `freeze.model_kind`: `algorithm == "l2_logit_v1_6_grid"` → `"fall"` (`family` değil). `family` silinmiş dosya yine `fall` türündedir ve `_check_params` `PARAMS_INVALID` verir (EK 3: "Linear'a düşer") |
| 2 | Ret sırası | compute_features → F3 → add_sale → TÜFE | compute_features (yalnız f3'lü modelde) → `F3_MISSING` → `F3_FILTER_STATUS_CONFLICT` → TÜFE (`TUFE_*`, alan `tufe_index`) → ek satış (`ADDITIONAL_SALE_MISSING` / `INPUT_NEGATIVE` / `INPUT_NOT_NUMERIC`, alan `additional_sale_shares`). Ek satış reddinde `f1r_raw` ve `tufe_index_used` o ana kadar dolu kalır |
| 3 | `F3_MISSING` koşulu | V1.5 kuralı (`input_policy.f3_missing == REFUSE`) | f3 boşsa politikaya bakılmadan ret; filtre çelişkisi yalnız `f3_filter_status_conflict == REFUSE` iken |
| 4 | Kırpma uyarı kodu | `F3_WINSORIZED` ya da `FEATURE_CLIPPED_TO_TRAINING_P05_P95` | `FEATURE_CLIPPED_TO_TRAINING_P05_P95` (f1r ve f3; alanlar `feature`, `value`, `used`); `F3_WINSORIZED` yok |
| 5 | Çıktı anahtarları | `LinearOutput` `{model_id, D10, D5, warnings, refused}` | `{model_id, D5, D10, warnings, refused, clipped, clipped_features, f1r_raw, tufe_index_used, add_sale_used}` (bu sırayla); ufuk sırası `FALL_HORIZONS` = D5, D10 (dosya sırası D10, D5 değil); ufuk hücresi V1.5 biçimi, getiri alanları null |
| 6 | `direction` | `p_up ≥ 0.5 ? UP : DOWN` | `UP` ancak `p > 0.5` (V1.5 kuralı) |
| 7 | `@ZERO` biçimi | `variant` "pooled", `features []` ya da sabit başlık | `variant = "pooled@ZERO"`, `features []`, `preprocessing null`, `deflator` yok, iki `constant` başlık (`value` = eğitim oranı); hiçbir girdi okunmaz, hiçbir koşulda ret yok; ek alanların hepsi null |
| 8 | `addsale` girdileri | — | yalnız `additional_sale_shares` okunur (`compute_features` çağrılmaz: fiyat/pay/f3/TÜFE gerekmez); `clipped false`, `clipped_features []` |
| 9 | Sabit başlık değeri | V1.5 `parse_head` (bool = 1.0) | `predict_fall._check_params`: `bool` sabit değer `PARAMS_INVALID` |
| 10 | Parametre denetimi | `parse_linear` kalıbı + `family`, `deflator`, winsor/log kümeleri | ayrıca ufuk kümesi tam `{D5, D10}`, her ufukta `return` null, özellik listesi ∈ {`[]`, `[f1r, f3, add_sale]`, `[add_sale]`}, ön işleme kolonları ⊆ özellikler |
| 11 | Ek satış ayrıştırma | yok / null / "" / DATA_NOT_FOUND → ret | `features.parse_decimal(required=False)`: ayrıca boşluk → `ADDITIONAL_SALE_MISSING`; bool, `inf`, `nan`, sayı değil → `INPUT_NOT_NUMERIC`; `-0` → 0 |

Rust: `params::{Kind::Fall, parse_fall}`, `fall::{predict_fall, additional_sale_flag}`, `output::FallOut` (`LinearOutput.fall`); birim
testleri `tests/fall_semantics.rs`, sayısal parite `golden/fall_d10_v0_*.jsonl`.

# SPEC_APP EK 2 — Faz 4 tavan-yolu modelleri uygulamada

Görev: BORSAI_FAZ3_FABLE_APP_SPEC_EK2_20260922. Yazan: Fable, 2026-09-22. Uygulayıcı: Opus (Claude Code), yalnız `app/` altında. Bu ek `docs/app/SPEC_APP.md`'ye (bundan sonra SPEC_APP) bölüm numaralarıyla atıf yapar; SPEC_APP'in metni değişmemiştir. Çelişkide üst belgeler (`CLAUDE.md`, `docs/specs/SPEC_SCORING.md`, `docs/specs_faz4/SPEC_CEILING_PATH_V0.md`, bundan sonra SPEC_PATH) kazanır; SPEC_APP ile bu ek çelişirse bu ek kazanır (SPEC_APP §8-3 bu eki önceden işaret etti).

İşaretler SPEC_APP'teki gibi: **[ÖLÇTÜM]** = bu oturumda dosyadan/komuttan; **[ÇIKARIM]** = yorum; **[KARAR]** = bağlayıcı karar, tek cümle gerekçeyle.

## Özet (10 satır)

1. Üç model (`ceiling_path_v0`, `ceiling_path_v0@INF`, `pb_ceiling_path_v0`; tür `ceiling_path`, `borsai/freeze.py: model_kind`) Rust `borsai_predict`'e port edilir; tanım `borsai/predict_path.py`'dir, Rust bir porttur. `PINNED_MODEL_IDS` 16 → 19, sıra INDEX sırası.
2. Seri bileşeni gömülü `survival_model` kopyasından, mevcut `hazard::predict_hazard` ile hesaplanır; açılışta kopyanın INDEX'teki seri modeliyle sha ve yapı eşitliği denetlenir (U41, bütünlük yolu).
3. Limit yolu C_h kesin ondalıkla: mevcut `dec.rs`'ye üç işlev eklenir — kesin bölmenin libmpdec üs kuralı, `to_integral_value` (FLOOR/HALF_UP) ve Python `str(Decimal)` metin biçimi. Oranlar Python'daki gibi 60 haneye yuvarlanıp bir kez binary64'e çevrilir (çift yuvarlama aynen).
4. Karışım binary64: atomlar Python ekleme sırasıyla, kararlı sıralama, kümülatif toplam düz `+=`, `p_up`/`mean` CPython `sum()` (Neumaier), kuantil eşiği `q − 1e-12`.
5. Ret ve uyarı kodları birebir: seri modelinin retleri aynen geçer; `@INF`'te fiyat reddi `INPUT_MISSING`/`INPUT_NOT_NUMERIC`/`INPUT_NOT_POSITIVE` (`ipo_price_tl`); yeni uyarı `IPO_PRICE_NOT_ON_TICK_GRID` (metin alanları `field`, `value`, `snapped`, `tick`); durumlar `OK`/`POST_BREAK_INSUFFICIENT`/`REALIZED`.
6. Altın vektörler: `gen_golden.py` 19 modele çıkar; 16 eski `.jsonl` dosyası **bayt-eşit kalır** (yeni girdiler yalnız üç yeni modele `only` ile bağlanır); üç yeni dosya ≥ 450 satır; koşullu karışım için ayrı `<model_id>.conditional.jsonl` (j = 0..9 ve kırılma t = 0..9). Toleranslar §3.3'te sayısal.
7. Gösterim: Grup A'ya üç sütun (D1/D3/D5/D10 medyan getiri, p_up, %10–%90); yeni **Grup C** "tavan yolu: getiri dağılımı h = 1..10" (tablo + yelpaze SVG + C_h); "getiri (koşullu)" sekmesi durum 1 (seri j gün sürüyor) ve durum 2 (t'de kırıldı) ile dolar; resmi görünümde yalnız kayıttaki çıktı (U38 ilkesi).
8. `scores.json`: `kind = "ceiling_path"` blokları getiri/p_up modeli gibi okunur; bugün backtest hücreleri boş ve `primary_cell` null [ÖLÇTÜM] — uygulama bunu "hücre yok" diye gösterir, doldurmaz; `retro_info` 21 satır (3 model × 7 arz); ileride gelecek `models[].conditional` bloğu için okuyucu şeması §5'te.
9. Yeni U-testleri U41–U51; hepsi `cargo test`/vitest/betik ile kanıtlanabilir. Aşama: yeni **Aşama P** (P1 port + parite, P2 gösterim), aşama 3'ten sonra; aşama 3'ün parite adımı port gelince kendiliğinden 19/19 der. Tahmin: 4 oturum.
10. Önceden yazılmış beklenti (§7): 19/19 model, maks |Δ| < 1e-12 (izin 1e-9), VEYAS girdileriyle yalnız `ceiling_path_v0` RET (`F3_MISSING`), sonuç ekranı 5 RET + 14 dolu.

---

## 0. Bağlam [ÖLÇTÜM, bu oturum]

- `models/INDEX.json`: 19 kayıt; son üçü `CEILING_PATH_MIXTURE_EQ_V0`, dondurma `2026-09-22T22:44:42+03:00` (a0df5b7). INDEX sha256 `1bc33791336482…`.
- `app/src-tauri/build_embed.rs: PINNED_MODEL_IDS` 16 kayıt; INDEX'in fazlası `ignored_model_ids` olarak "Hakkında"ya düşüyor. `borsai_predict` `Kind` enum'unda `ceiling_path` yok; `params::model_kind` bu algoritmayı `Rule` sayar → `parse_linear` → `PARAMS_INVALID` ("horizons.D2: bilinmeyen ufuk" yolu). Yani bugün bu üç dosya gömülse açılış `INTEGRITY_FAILED` olur; port şart.
- `app/parity/golden/MANIFEST.json`: çalışma ağacında değiştirilmiş (paralel aşama 3 oturumu); `models_index_sha256` artık 19 modelli INDEX'in sha'sı, `model_ids` hâlâ 16, `n_cases` 395, `predict_sources_sha256` 7 dosya (`predict_path.py` yok).
- `registry/records/*`: 7 arzın kayıtları 16 modelli (`models_index.sha256` `a448a5cce6e9…`); hiçbir kayıt Faz 4 çıktısı içermiyor. Yeni kayıtlar `borsai.freeze` ile 19 model içerecek.
- `scores/scores.json` (`borsai.scores/1`): 19 model bloğu; üç Faz 4 bloğunda `kind = "ceiling_path"`, `backtest.cells = []`, `primary_cell = null`, `live.n_rows = 0`; `retro_info` 21 öğe, hepsi Faz 4 modelleri, `record_id = null`, `class_evidence.basis` "MODEL_FROZEN_AFTER_OUTCOME_NO_RECORD…". Üst düzeyde ayrıca `separate_models`, `definitions`, `outcomes` anahtarları var (SPEC_APP §2.3 listesinde yok; bilinmeyen anahtar yok sayılır).
- `borsai/scoring.py`: `prediction_of_cell` `ceiling_path` için D1/D3/D5/D10 `return`/`p_up` okuyor (satır 343); `comparators` bu türü doğrusal model gibi ele alıyor (`RETURN_RULES` + `PROB_RULES`, `v1_5_h99` yok); `backtest_cells` ve `PRIMARY_CELLS`'te `ceiling_path` dalı YOK → hücreler boş (ön koşul görevi Ö1, §8).
- Üç model JSON'unun üst düzey anahtarları aynı: `algorithm, code_version, created_at, description, feature_definitions, feature_ranges, features, horizons, input_policy, limit_path, model_id, post_break, quantile_rule, schema_version, spec, spec_sha256, survival_model, survival_model_id, survival_model_sha256, survival_training, training`. `post_break.cells` üçünde bayt-aynı (hücre JSON'unun kanonik sha'sı `278589d27864ad46…`); `cell_n` Z 1..10 = 18, B 1..9 = 67, 64, 60, 54, 48, 40, 28, 15, 11; `n_obs` 567; `cutoff_date` = `max_session_date` = 2026-08-19. `limit_path.price_field`: ana ve sıfır modelde `ipo_price_tl`, PB'de `ipo_price_try`. `features`: `["f1","f2","f3"]` / `[]` / `["pb1","pb2"]` (gömülü seri modelininkiyle aynı).
- `survival_model` kopyaları: üçünde `json.loads(dosya) == params["survival_model"]` ve `survival_model_sha256` = INDEX sha'sı (`caa4dc867a9f…`, `c5ac8085fd76…`, `7fb7a41e48ea…`) [ÖLÇTÜM]; `tests/test_faz4_ceiling_path.py:195-196` de aynı denetimi yapıyor.
- `data/outcomes/<T>.csv` başlığı (yalnız başlık okundu): `h, session_date, close_raw, upper_limit_raw, reference_raw, trade_count_raw, halt_flag, half_day, shifted_by_suspension, ceiling_close, R_h, Y_h, ipo_price, thb_sha256, thm_sha256, status`. `borsai/outcomes.py:476` `close_raw`'ı `Decimal(close_raw)` ile okuyor → koşullu karışımın gözlenen kapanışı bu sütundur ve Decimal-ayrıştırılabilir metindir.
- `predict_path.predict`'in H99 girdileriyle (yalnız girdi sütunları) koşusu: 97 tahmin, 2 RET (f3 yok); snap ≠ P yalnız BORLS, AVPGY, ARTMS, LILAK; h = 1..10 için `return == limit_path_return` sayısı = `S_h ≥ 0.5` sayısı = 97, 84, 77, 49, 33, 21, 16, 11, 10, 5 (SPEC_PATH §4 tutarlılığı, port testi için sabit). Dondurulmuş hücrelerle hiçbir hücre havuzlanmaz: `n_atoms` h = 1..10 için her arzda `19, 86, 150, 210, 264, 312, 352, 380, 395, 406`.

---

## 1. §2.1 eki: `ceiling_path` model JSON'u

Rust'ın okuduğu alanlar (Python `predict_path._check_params` + `predict` ile aynı; başka alan okunmaz, bilinmeyen alan yok sayılır):

| Alan | Tür | Rust'ta kullanım | Denetim (`PARAMS_INVALID` nedeni, Python metniyle) |
|---|---|---|---|
| `schema_version` | metin | | `borsai.model/1` değilse `SCHEMA_UNSUPPORTED` |
| `algorithm` | metin | tür seçimi (`Kind::CeilingPath`) | `CEILING_PATH_MIXTURE_EQ_V0` değilse "tavan yolu modeli değil" |
| `model_id` | metin | çıktı `model_id` | |
| `survival_model` | nesne | seri bileşeni: `params::parse_hazard` + `hazard::predict_hazard` aynen | sözlük değilse, `model_id ≠ survival_model_id` ise ya da `algorithm ≠ discrete_time_hazard_logit_l2` ise "gömülü seri modeli yok ya da kimliği tutmuyor"; ardından `parse_hazard`'ın kendi denetimleri (ör. `gamma/beta boyutu tutmuyor`) |
| `survival_model_id` | metin | yukarıdaki eşleme; U41 | |
| `survival_model_sha256` | metin | yalnız U41 (açılış bütünlüğü) | Python `_check_params` bakmaz; Rust tahmin yolunda da bakmaz |
| `limit_path.margin` | metin `"0.10"` | sabit `1 + 0.10`, `1 − 0.10` | `margin`, `tick_table`, `upper_rounding`, `d1_base` dördü birden şartname sabitlerine JSON-eşit değilse "limit yolu sabitleri şartnameyle aynı değil"; `lower_rounding`, `rule_source` OKUNMAZ |
| `limit_path.tick_table` | `[{below, tick}]` × 8 | adım tablosu (metinler kesin Decimal'e) | JSON-eşitlik: `below` `"20","50","100","250","500","1000","2500",null`; `tick` `"0.01","0.02","0.05","0.10","0.25","0.50","1.00","2.50"` |
| `limit_path.upper_rounding` | `"FLOOR_TO_TICK_AT_LIMIT_LEVEL"` | | aynı |
| `limit_path.d1_base` | `"HALF_UP_TO_TICK"` | | aynı |
| `limit_path.price_field` | `"ipo_price_tl"` \| `"ipo_price_try"` | hangi girdi alanı ayrıştırılır | ikisinden biri değilse aynı hata |
| `post_break.N_MIN` | 10 | havuzlama eşiği | 10 değilse "kırılma sonrası sabitleri şartnameyle aynı değil" |
| `post_break.groups` | `["Z","B"]` | | listeye eşit değilse aynı hata |
| `post_break.cells` | `{"Z": {"1"…"10": [[G, ticker]…]}, "B": {"1"…"9": …}}` | hücre gözlemleri (G binary64, ticker metin) | anahtar kümeleri tam Z 1..10 / B 1..9 değilse "hücre anahtarları Z 1..10 / B 1..9 değil"; fazla/eksik anahtar hata; hücre listesi boş olabilir |
| `horizons` | `D1..D10` | OKUNMAZ (parse_linear ÇAĞRILMAZ) | |
| diğer (`features`, `feature_ranges`, `quantile_rule`, `spec`, `training`, `survival_training`, `cell_n`, …) | | okunmaz | |

**[KARAR] `check_params` sırası Python'unkiyle aynı** (schema → algorithm → survival_model → limit_path → post_break); gerekçe: yamalı-parametre altın satırlarında ilk hata kodu ve U33'te hata nedeni Python'la aynı olsun.

**[KARAR] U41 — gömülü seri modeli bütünlüğü (açılış, `models::verify`):** her `ceiling_path` modeli için (a) `survival_model_sha256` INDEX'te `model_id == survival_model_id` olan kaydın `sha256`'sına eşit, (b) o kayıt gömülü model kümesinde var, (c) `survival_model` JSON değeri o gömülü dosyanın ayrıştırılmış değerine yapısal olarak eşit (`serde_json::Value` eşitliği; dosya baytları `pretty_json_bytes` ile aynı üreticiden çıktığından sayı gösterimleri de aynıdır [ÖLÇTÜM: `json.loads` eşitliği Python'da geçiyor]). Tek uyuşmazlık → `INTEGRITY_FAILED`, `reason_code = "SURVIVAL_MODEL_MISMATCH"`. Gerekçe: SPEC_PATH §1 "S_k dondurulmuş modelin çıktısına bit-eşittir" güvencesi kopyanın bozulmamasına dayanır ve bunu tahmin anında değil açılışta, sha ile denetlemek SPEC_APP §1.4'ün fail-closed ilkesidir.

**Girdi sözleşmesi:** `predict(params, inputs)` aynı düz girdi sözlüğünü alır (`borsai.registry.model_inputs` + f6 alanları); f6 okunmaz. Çıktı yapısı §2.7.

---

## 2. Rust portu

### 2.1 Modül ve türler

- `crates/borsai_predict/src/path.rs` (yeni): `limit_path`, `cells`, `pool`, `mixture`, `summarize`, `predict_path`, `conditional`, `conditional_after_break`. `params.rs`: `Kind::CeilingPath` (`as_str = "ceiling_path"`), `PathParams { model_id, survival: HazardParams, survival_raw: Value, price_field, cells: BTreeMap<(Group, u8), Vec<(f64, String)>> }`, `parse_path`, `check_params` dalı. `output.rs`: `Output::Path(PathOutput)`. `lib.rs: predict` dağıtımı `Kind::CeilingPath => parse_path → path::predict_path`.
- `model_kind`: `algorithm == "CEILING_PATH_MIXTURE_EQ_V0"` denetimi `HAZARD_ALGORITHM`'den sonra, `KM_ALGORITHMS`'den önce (Python `freeze.model_kind` sırası; sonuç aynı çünkü kümeler ayrık).
- Sabitler metin olarak (`dec::parse` ile bir kez): `MARGIN = "0.10"`, `TICK_TABLE` (8 çift), `QUANTILE_EPS = 1e-12`, `N_MIN = 10`, `DAYS = 10`, `M_MAX = {Z: 10, B: 9}`.

### 2.2 Decimal: `dec.rs` yeterli mi? [ÖLÇTÜM]

Var olan ve yeniden kullanılan: `parse` (Python `Decimal(str)`), `Dec { neg, coeff, exp }`, `cmp/eq` (değer eşitliği; `Decimal("27.5") == Decimal("27.50")` gibi), `to_f64` (doğru yuvarlanmış), `round_sig` (HALF_EVEN/HALF_UP), `div_round(a, b, prec)` (doğru yuvarlanmış bölüm), `mul_round`, `add_exact/mul_exact/check_exact` (prec + Inexact), `quantize`.

Eksik olan üç şey ve kararları:

1. **Kesin bölmede libmpdec üs kuralı** (`y / adım`, `P / adım`). Python'da `_EXACT` bağlamı (prec 60, Inexact tuzağı) ile `y / s` her zaman kesindir (adımlar yalnız 2 ve 5 çarpanlı) ama sonucun **üssü** metne yansır. **[KARAR] `dec::div_exact(a, b, prec) -> Result<Dec, Inexact>`:** kesin değer v = a/b; `ideal = exp(a) − exp(b)`; sonuç üssü `e` = `ideal`'den küçük ya da eşit, `v·10^(−e)` tamsayı olan EN BÜYÜK e (v = 0 için `e = ideal`); katsayı `v·10^(−e)`; kesin değilse (kalan ≠ 0) `Inexact`. Gerekçe: ölçülen Python davranışı (aşağıdaki tablo) yalnız bu kuralla bit-eşit metin verir. Ölçümler: `30.2500/0.02 → 1512.50 (exp −2)`, `1E+2/0.10 → 1E+3`, `100/0.10 → 1.0E+3 (katsayı 10, exp 2)`, `1/0.25 → 4`, `0/0.10 → 0E+2`, `110.0/0.10 → 1.10E+3 (exp 1)`.
2. **Bağlam yuvarlaması (prec 60) kesin işlemlerde:** çarpma (`b × 1.10`, `q × adım`) ve bölme sonucu 60 haneyi aşarsa libmpdec 60 haneye yuvarlar: atılan haneler sıfırsa sonuç kesindir ama **gösterim** 60 haneli katsayı + yükseltilmiş üs olur ("1"+61 sıfır fiyatında snap `1.00000000000000000000000000000000000000000000000000000000000E+61` [ÖLÇTÜM]); atılan hanelerden biri sıfır değilse `decimal.Inexact` fırlar (Python etiketsiz istisna → Rust `DOMAIN_ERROR`; "25." + 70 hane fiyatta ölçüldü). **[KARAR]** `dec::ctx_round(x, 60) -> Result<Dec, Inexact>`: `ndigits(coeff) > 60` ise `round_drop` ile kes; kalan ≠ 0 → `Inexact`; kalan = 0 → katsayı kısalır, üs artar (sondaki sıfırlar ATILMAZ). Bu işlev `mul` ve `div_exact` sonuçlarına, `to_integral` sonucuna uygulanır. Gerekçe: `str(C)` alanlarının birebirliği (§3.3) buna bağlı.
3. **`to_integral_value(rounding)` ve Python `str(Decimal)`.** **[KARAR] `dec::to_integral(x, mode)`:** `exp ≥ 0` ise değişmez (üs korunur: `1E+3` → `1E+3`), `exp < 0` ise `quantize(x, 0, mode)` (FLOOR için: büyüklük üzerinde kes, negatifte ROUND_FLOOR = sıfırdan uzağa; fiyatlar pozitif olduğundan yalnız pozitif dal ölçülür). **[KARAR] `dec::py_str(x) -> String`** CPython `Decimal.__str__` (bilimsel olmayan `to_sci_string`): `d` = katsayı haneleri, `e` = üs, `left = e + len(d)`; `e ≤ 0 ve left > −6` ise `dot = left` (düz gösterim), değilse `dot = 1` (bilimsel); `dot ≤ 0` → `"0." + "0"×(−dot) + d`; `dot ≥ len(d)` → `d + "0"×(dot − len(d))`; aksi hâlde `d[:dot] + "." + d[dot:]`; `left ≠ dot` ise sonuna `"E" + ("+" | "−") + |left − dot|`; negatifse başa `"-"`. Ölçümler: `1E2 → "1E+2"`, `0.0000001 → "1E-7"`, `0.000001 → "0.000001"`, `10 → "10"`, `1.0 → "1.0"`, `0E-2 → "0.00"`, `25.520 → "25.520"`, `1e400 → "1E+400"`.

Çarpma kesin: `Dec { neg, coeff: a·b, exp: exp_a + exp_b }` sonra `ctx_round(…, 60)`; `1.0E+2 × 0.10 = 10.0 (exp −1)`, `1E+3 × 1.00 = 1.00E+3 (exp 1)` [ÖLÇTÜM].

**Oranlar (`ratio`, `ratio_minus_one`, `physical_bounds`, `rho_max` yok):** Python `_RATIO` bağlamı (prec 60, Inexact tuzağı YOK): `float(a / b)` ve `float(a / b − 1)`. **[KARAR]** Rust: `q = div_round(a, b, 60)` (HALF_EVEN, 60 hane); `ratio = q.to_f64()`; `ratio_minus_one = add_exact(q, −1, 60)?.to_f64()` (çıkarma 60 hanede kesindir: C/P < 6 olduğundan hane konumları değişmez; `add_exact` Inexact verirse `DOMAIN_ERROR`, beklenmez). Kesin rasyonelden doğrudan binary64'e KISAYOL YASAK: Python 60 haneye yuvarlayıp sonra binary64'e çevirir (çift yuvarlama); 20 000 rastgele (C, P) çiftinde fark 0 ölçüldü ama kural Python'unkidir, kısa yol parite kanıtı değildir. `physical_bounds(m)` metin sabitleri (`(0.9^m − 1, 1.1^m − 1)` kesin Decimal'den `float`, [ÖLÇTÜM]):

| m | alt | üst |
|---|---|---|
| 1 | −0.1 | 0.1 |
| 2 | −0.19 | 0.21 |
| 3 | −0.271 | 0.331 |
| 4 | −0.3439 | 0.4641 |
| 5 | −0.40951 | 0.61051 |
| 6 | −0.468559 | 0.771561 |
| 7 | −0.5217031 | 0.9487171 |
| 8 | −0.56953279 | 1.14358881 |
| 9 | −0.612579511 | 1.357947691 |
| 10 | −0.6513215599 | 1.5937424601 |

### 2.3 Limit yolu (`predict_path.limit_path`, SPEC_PATH §2)

```
tick(x)   : tablo sırasıyla ilk (lim None ya da x < lim) satırın adımı  (dec::cmp)
U(b)      : y = ctx_round(b × 1.10); s = tick(y); q = div_exact(y, s)?; q = to_integral(q, FLOOR); ctx_round(q × s)
snap(P)   : s = tick(P); q = div_exact(P, s)?; q = to_integral(q, HALF_UP); ctx_round(q × s)
limit_path: b = snap(P); C_k = U(C_{k−1}) (C_0 yerine b), k = 1..10; rho_k = ratio_minus_one(C_k, P); scale_k = ratio(C_k, P)
```
`Inexact` → `PredictError::domain` (Python etiketsiz istisna). Çıktı metinleri `py_str`: `ipo_price = py_str(P)`, `snapped_ipo_price = py_str(snap)`, `tick = tick(P)` tablo metni, `C[k] = py_str(C_k)`. Uyarı koşulu `!dec::eq(snap, P)` (değer eşitliği; `136` ↔ `136.0` uyarı VERMEZ [ÖLÇTÜM VEYAS]).

Ölçülen biçimler (port testi U47'nin `dec_cases.json: limit_path` bölümü; üretici Python'dan yazar):

| Girdi metni | `ipo_price` | `snapped` | `tick` | C_1 | C_2 | C_10 | uyarı |
|---|---|---|---|---|---|---|---|
| `25.52` | 25.52 | 25.52 | 0.02 | 28.06 | 30.86 | 66.05 | — |
| `25.5` | 25.5 | 25.50 | 0.02 | 28.04 | 30.84 | 66.00 | — |
| `25.520` | 25.520 | 25.52 | 0.02 | 28.06 | 30.86 | 66.05 | — |
| `100` | 100 | 100 | 0.10 | 110.00 | 121.00 | 259.00 | — |
| `1E2` | 1E+2 | 1.0E+2 | 0.10 | 110.0 | 121.00 | 259.00 | — |
| `1E3` | 1E+3 | 1.00E+3 | 1.00 | 1100.0 | 1210.00 | 2590.00 | — |
| `25.29` | 25.29 | 25.30 | 0.02 | 27.82 | 30.60 | 65.50 | NOT_ON_TICK_GRID |
| `19.999` | 19.999 | 20.00 | 0.01 | 22.00 | 24.20 | 51.80 | NOT_ON_TICK_GRID |
| `45.45` | 45.45 | 45.46 | 0.02 | 50.00 | 55.00 | 117.80 | NOT_ON_TICK_GRID |
| `18.19` | 18.19 | 18.19 | 0.01 | 20.00 | 22.00 | 47.12 | — |
| `0.014` | 0.014 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 | NOT_ON_TICK_GRID (ρ_1 = −0.2857…) |
| `1e-400` | 1E-400 | 0.00 | 0.01 | 0.00 | 0.00 | 0.00 | NOT_ON_TICK_GRID (ρ_h = −1.0) |
| `1e400` | 1E+400 | 1.000E+400 | 2.50 | 1.10000E+400 | 1.2100000E+400 | 2.59374246010000000000000E+400 | — |
| `999999999` | 999999999 | 1000000000.00 | 2.50 | 1100000000.00 | 1210000000.00 | 2593742457.50 | NOT_ON_TICK_GRID |
| `25.` + 70×`5` | — | — | — | — | — | — | `decimal.Inexact` → `DOMAIN_ERROR` |

Adım sınırları (U47): `tick(19.999) = 0.01`, `tick(20) = 0.02`, `tick(49.99) = 0.02`, `tick(50) = 0.05`, `tick(2500) = 2.50`; `18.19 → C_1 = 20.00` (adım, yuvarlanacak değerin KENDİ seviyesinden: 20.009 → adım 0.02 → 20.00), `18.2 → 20.02`, `9.09 → 9.99`, `9.10 → 10.01`.

### 2.4 Hücreler ve havuzlama (SPEC_PATH §3)

- Hücre değerleri JSON'dan `serde_json` `float_roundtrip` ile (Python `json.load` da doğru yuvarlar → bit-eşit). Sıra dosya sırası (artan; yeniden sıralanmaz).
- `ladder(g, m)`: `[[(g,m)], [(diğer,m)]]` + d = 1..9 için `mm ∈ (m−d, m+d)` sırasıyla, her adım `[(Z,mm), (B,mm)]`; geçersiz hücreler (Z m ∉ 1..10, B m ∉ 1..9) adımdan ATILIR, adım boş kalabilir (Python `ladder` ile aynı; `sources` listesi yalnız geçerli anahtarları içerir). Ölçüm: `ladder(B,1)` ilk 4 adım `[(B,1)], [(Z,1)], [], [(Z,2),(B,2)]`; `ladder(Z,10)` `[(Z,10)], [], [(Z,9),(B,9)], [], [(Z,8),(B,8)]`.
- `pool`: adım adım topla; **adım sonunda** `n ≥ N_MIN` ise dur; `sources` bakılan bütün hücreler (boşlar dahil); `values[i] = py_min(py_max(v, lo), hi)` (`sum::py_min/py_max`, Python `min(max(v, lo), hi)` sırası); `n_clipped` sayımı; `sufficient = n ≥ N_MIN`; `pooled = len(sources) > 1`. Ölçümler (yamalı hücrelerle, U44 satırlarının beklenenleri): (B,9) 3 gözleme indirilince `n = 21, sources = [(B,9),(Z,9)], pooled`; her şey boş + (Z,1) 5 gözlem iken `pool(B,1)` → `n = 5, sufficient = False, len(sources) = 19`; (B,2)'ye −0.25 ve +0.30 eklenmiş yamada `pool(B,1)` → `n = 10, sources = [(B,1),(Z,1),(Z,2),(B,2)], n_clipped = 8, min/max = −0.1/0.1`.
- Dondurulmuş dosyalarda havuzlama ve kırpma HİÇ tetiklenmez (her hücre ≥ 11) → bu yollar yalnız yamalı parametrelerle sınanır (§3.2).

### 2.5 Karışım ve kuantil (SPEC_PATH §4)

```
mixture_atoms(limit_atom, parts, cells, h):
  atoms = [limit_atom] (varsa)
  for (t, weight, scale) in parts (t artan):          # koşulsuz: t = 0..h−1, weight = P_L[t], scale = None (t=0) | scale[t−1]
      pc = pool(cells, g(t), h − t); used.push(pc)
      if !pc.sufficient: return (atoms, used, false)   # o ana kadarki atomlar döner; n_atoms = 0 yazılır
      w = weight / (pc.n as f64)
      atoms += [ (if scale None { v } else { scale * (1.0 + v) - 1.0 }, w) for v in pc.values ]   # işlem sırası aynen
summarize(atoms):
  ordered = atoms.clone(); ordered.sort_by(r partial_cmp)   # KARARLI sıralama (Rust sort_by kararlıdır); eşit r'de ekleme sırası
  q(p): cum = 0.0; for (r, w) in ordered { cum += w; if cum >= p - 1e-12 { return r } }; ordered.last().r
  return = q(0.5); q10 = q(0.1); q50 = q(0.5); q90 = q(0.9)
  p_up = py_sum(w for (r, w) in ordered if r > 0.0);  mean = py_sum(r * w for (r, w) in ordered)
```
**[KARAR]** kümülatif toplam `cum` düz `+=` (Python `q()` içindeki döngü), `p_up`/`mean` `sum::py_sum` (Python `sum()`); gerekçe: iki yol farklı yuvarlar ve bit-eşitlik ancak aynı yolla sağlanır. `p − 1e-12` her çağrıda binary64 ile hesaplanır (`0.5 - 1e-12`), sabitleştirilmez. NaN atom oluşamaz (v sonlu, scale sonlu; P → 0 durumunda `scale = 0.0`). `S_h`, `P_L` seri modelinin çıktısından aynen (`hazard::predict_hazard` → `survival`, `p_streak`).

### 2.6 `predict_path` akışı (`predict_path.predict`)

1. `parse_path` (denetimler §1).
2. `surv = predict_hazard(&p.survival, inputs)`; çıktı iskeleti: `model_id, refused: None, warnings: surv.warnings, clipped: surv.clipped, hazard/S/P_L/P_close_ceiling: surv…, limit_path: None, D1..D10: None`.
3. `surv.refused` doluysa → `refused` kopyalanır, dönülür (diğer alanlar None; `warnings` surv'ünki).
4. Fiyat: `price_field == "ipo_price_try"` ise `pb_features` yolunun `parse_pb_decimal` portu (`PB_FIELD_MISSING` / `PB_PRICE_RANGE`; `≤ 0` → `PB_IDENTITY`/`VALUE_POSITIVE`), değilse `features::parse_decimal` portu (`INPUT_MISSING`, `INPUT_NOT_NUMERIC`; `≤ 0` → `INPUT_NOT_POSITIVE`), `field` = alan adı. Ret → `refused` yazılır ve `hazard, S, P_L, P_close_ceiling, clipped` **None'a çekilir**, `warnings` olduğu gibi kalır (Python `out.update(...)` davranışı) [ÖLÇTÜM: `@INF` + `ipo_price_tl = None/"abc"/"0"/"-1"/""` → `INPUT_MISSING`/`INPUT_NOT_NUMERIC`/`INPUT_NOT_POSITIVE`/`INPUT_NOT_POSITIVE`/`INPUT_MISSING`, `warnings = []`, `S = None`]. Ana ve PB modellerinde bu dal ulaşılamaz (fiyat özellik hesabında zaten ayrıştırıldı) ama port edilir.
5. `limit_path`; `Inexact` → `DOMAIN_ERROR`. `snap ≠ P` (değer) → `IPO_PRICE_NOT_ON_TICK_GRID` uyarısı: `{code, message, field: <price_field>, value: py_str(P), snapped: py_str(snap), tick: <tablo metni>}` (Python `_warn(..., field=field, value=str(P), snapped=…, tick=…)` [ÖLÇTÜM]; `feature` anahtarı YOK).
6. `limit_path` çıktısı `{ipo_price, snapped_ipo_price, tick, C[10], rho[10]}`; h = 1..10 için `horizon_prediction`.

Python'un etiketsiz istisnaları (`ValueError` özellik yolunda, `decimal.Inexact` limit yolunda, `decimal.Overflow`) → `DOMAIN_ERROR` (mevcut kural; altın satırda `expected.exception`).

### 2.7 Çıktı yapısı (`Output::Path`, `to_json` anahtar sırası Python sözlüğüyle aynı)

```
{"model_id", "refused", "warnings", "clipped", "hazard", "S", "P_L", "P_close_ceiling",
 "limit_path": null | {"ipo_price": str, "snapped_ipo_price": str, "tick": str, "C": [str×10], "rho": [f64×10]},
 "D1".."D10": null | {"return", "p_up", "mean", "q10", "q50", "q90": f64|null,
                     "limit_path_return": f64, "S_h": f64, "p_limit_path": f64, "n_atoms": int,
                     "post_break": {"cells": [{"group": "Z"|"B", "m": int, "n": int, "pooled": bool, "sources": [[g, m]…]}…],
                                    "status": "OK" | "POST_BREAK_INSUFFICIENT"}}}
```
`POST_BREAK_INSUFFICIENT`'ta `return/p_up/mean/q10/q50/q90 = null`, `n_atoms = 0`, `limit_path_return/S_h/p_limit_path` dolu, `cells` o ana kadar bakılan hücreler [ÖLÇTÜM]. `warnings[i]` mevcut `Warning` yapısına `field`, `snapped`, `tick` (metin) ve metin `value` eklenir: **[KARAR]** `Warning.value` türü `Option<Value>`'ya genişletilmez; `Warning`'e `text_fields: Vec<(String, String)>` eklenir ve `to_json` bunları aynen basar; gerekçe: mevcut altın vektörlerin sayısal `value` alanı ve `cmp_warnings` değişmeden kalır.

`RunResult.kind` `"ceiling_path"`; `predict_all` sırası INDEX sırası (19).

### 2.8 Koşullu güncelleme (`conditional`, `conditional_after_break`; SPEC_PATH §7)

İmza: `path::conditional(params: &PathParams, record_output: &Value, j: usize, observed_closes: &[&str]) -> Result<Value, PredictError>` ve `conditional_after_break(…, t, closes)`. **[KARAR] Girdi kayıttaki çıktı JSON'udur, Rust'ın kendi `PathOutput`'u değil;** `P = parse(limit_path.ipo_price)`, `C = parse(limit_path.C[k])`, `rho = limit_path.rho[k]`, `S = output.S` kayıttan okunur; limit yolu YENİDEN HESAPLANMAZ. Gerekçe: resmi görünüm dondurulmuş değerden hesaplamak zorundadır (SPEC_APP §3g, U38) ve Python `_record_path` de böyle yapar.

- Ön koşullar (Python `ValueError`): `refused` dolu ya da `limit_path`/`S` null → `PredictError("CONDITIONAL_INVALID", …)`; durum 1: `0 ≤ j ≤ 9`, `len(closes) ≥ j`; durum 2: `0 ≤ t ≤ 9`, `len(closes) ≥ t + 1`; `S_j ≤ 0` → aynı hata (Python `conditional_weights` `ValueError`). Altın satırlarda `expected.exception = "ValueError"` ↔ Rust bu kod.
- `conditional_weights(S, j)`: `S0 = [1.0] + S`; `s_cond[k] = S0[k] / S0[j]` (k = j+1..10); `pl_cond[t] = (S0[t] − S0[t+1]) / S0[j]` (t = j..9); `pl_cond[10] = S0[10] / S0[j]`. j = 0'da `S0[0] = 1.0` ile bölme → koşulsuzla bit-eşit (test).
- Durum 1: `obs[t] = parse(closes[t])` (Python `Decimal(str(close))`; `close_raw` metni); `scale[t] = ratio(t ≤ j ? obs[t−1] : C[t−1], P)` t = 1..10; `limit_path_mismatch = any(!eq(obs[t−1], C[t−1]), t = 1..j)` (Decimal değer eşitliği). h ≤ j → `{"status": "REALIZED", "realized_return": ratio_minus_one(obs[h−1], P)}`; h > j → `parts = [(t, pl_cond[t], t == 0 ? None : scale[t−1]) for t in j..h−1]`, `mixture_atoms((rho[h−1], s_cond[h]), parts, cells, h)`, hücre `{"status", …_horizon alanları, limit_path_return = rho[h−1], S_h = s_cond[h]}`. Üst alanlar: `state = "STREAK_ONGOING"`, `j`, `S_j` (j = 0 → 1.0, değilse `S[j−1]`), `S_cond` (`{"k": v}` metin anahtarlı), `P_L_cond`, `limit_path_mismatch` (0/1 tamsayı).
- Durum 2: `scale = t == 0 ? None : ratio(obs[t−1], P)`; `limit_path_mismatch` t'ye kadar; h ≤ len(obs) → REALIZED; h > len(obs) → `mixture_atoms(None, [(t, 1.0, scale)], cells, h)`, `limit_path_return = S_h = p_limit_path = null`. Üst alanlar: `state = "AFTER_BREAK"`, `t`, `note = "kırılma sonrası, D_{t}'ye koşullu"` (metin birebir; Türkçe ek Python'daki gibi sabit `'ye`), `limit_path_mismatch`.
- Ölçüm (NETGL girdisi, ana model): `conditional(j = 3, closes = C[:3])` → `mismatch 0`, `D3 = {REALIZED, 0.3299373040752351}`, `D5.return = 0.4300646010495506`, `D5.p_up = 1.0`, `D5.n_atoms = 132`, hücreler `[(B,2,64), (B,1,67)]`; closes `["28.06","30.86","33.90"]` → `mismatch 1`, `D3.realized_return = 0.3283699059561129`; `conditional_after_break(t = 3, closes = C[:3] + ["31.00"])` → `D4 REALIZED 0.21473354231974923`, `D5.return = 0.1564672209349871`, `n_atoms 64`; `t = 0, closes = ["24.00"]` → `D3.return = −0.06217162872154115`, `p_up 0.2222222222222222`, `n_atoms 18`.

### 2.9 Ret ve uyarı kodlarının birebirliği (T-2 eki)

| Kod / durum | Kaynak | `field` / alan | Arayüz metni (tr.ts) |
|---|---|---|---|
| `F3_MISSING` (miras) | gömülü `ceiling_hazard_v0` | `total_demand_multiple` | mevcut metin + "tavan yolu tahmini `pb_ceiling_path_v0` ve sıfır model sütunlarındadır" |
| `PB_FIELD_MISSING`, `PB_IDENTITY`, `PB_PRICE_RANGE` (miras) | gömülü `pb_ceiling_v0` | mevcut | mevcut |
| `INPUT_MISSING`, `INPUT_NOT_NUMERIC`, `INPUT_NOT_POSITIVE` | `predict_path._price` (yalnız `@INF`'te ulaşılır) | `ipo_price_tl` | mevcut; ek cümle: "arz fiyatı limit yolu için gerekli (SPEC_DEVIATIONS F2)" |
| uyarı `IPO_PRICE_NOT_ON_TICK_GRID` | `predict_path` | `field` (`ipo_price_tl` \| `ipo_price_try`), `value`, `snapped`, `tick` | "arz fiyatı {value} fiyat adımı ızgarasında değil (adım {tick}); D1 baz fiyatı {snapped} alındı" |
| uyarı `OUT_OF_TRAINING_RANGE`, `F3_CLIPPED_TO_TRAINING_P05_P95`, `PB4_ADDITIONAL_SALE_CEILING` (miras) | seri modeli | mevcut | mevcut |
| durum `POST_BREAK_INSUFFICIENT` | `D{h}.post_break.status` | — | "kırılma sonrası hücrelerde yeterli gözlem yok (n < 10): S ve P(L) var, getiri/p_up/kuantil yok" |
| durum `REALIZED` | koşullu `D{h}.status` | — | "gerçekleşti: {realized_return}" |
| `CONDITIONAL_INVALID` | Rust (Python `ValueError`) | — | "koşullu güncelleme bu kayıttan yapılamaz: {neden}" |
| `SURVIVAL_MODEL_MISMATCH` | U41 bütünlük | model_id | INTEGRITY bandı: "gömülü seri modeli kopyası INDEX ile uyuşmuyor: {model_id}" |
| `DOMAIN_ERROR` (mevcut) | limit yolu `Inexact` dahil | — | mevcut |

Bütün kod ve durum metinleri `tr.ts`'te anahtar olarak bulunmalı (U8 kümesi genişler: vitest `codes_have_text`).

---

## 3. Parite ve altın vektörler

### 3.1 `gen_golden.py` genişlemesi

- `PINNED_MODEL_IDS` 16 → 19 (INDEX'in ilk 19 kaydı, aynı sırayla; `load_models` 19'u denetler). `PREDICT_SOURCES` + `borsai/predict_path.py` (8 dosya; `golden` testi `predict_sources_unchanged` 8 sha denetler).
- `model_kind`: `algorithm == pth.ALGORITHM → "ceiling_path"` (freeze.py a0df5b7 ile aynı sıra); `call`: `"ceiling_path" → pth.predict`.
- `clip_cases` hedefleri: **[KARAR]** `r.get("kind") == "ridge"` (şu anki `!= "constant"` yerine); gerekçe: `mixture_median` başlığında `return_clipped` yoktur, aksi hâlde 60 anlamsız muafiyet üretilir; 16 modelde ridge ↔ "constant değil" eşdeğer olduğundan mevcut satırlar değişmez.
- `derived_tags`: `IPO_PRICE_NOT_ON_TICK_GRID` için anahtar `w.get("feature") or w.get("horizon") or w.get("field")`; `D{h}.post_break.status` için `status:D{h}:POST_BREAK_INSUFFICIENT` ve `pooled:D{h}` etiketleri (yalnız `ceiling_path`); bu değişiklikler 16 modelin satırlarını etkilemez (o çıktılarda alan yok).
- **[KARAR] Yeni girdi satırları yalnız üç yeni modele `only=(…)` ile bağlanır;** gerekçe: 16 eski `.jsonl` bayt-eşit kalmalı (U46) ve bu satırlar yalnız limit yolunu sınar. Liste (`edge_specs` sonuna, `only=PATH_IDS`; her biri NETGL tabanı üzerine `ipo_price_tl` ve `ipo_price_try` AYNI değere çekilerek, PB özdeşlikleri korunur):
  - adım sınırları: `19.99, 19.999, 20, 20.01, 49.98, 49.99, 50, 50.05, 99.95, 99.99, 100, 100.10, 249.90, 250, 499.75, 500, 999.50, 1000, 2499, 2500, 2502.50` (21)
  - üst limit adım geçişi: `18.18, 18.19, 18.2, 18.21, 45.45, 45.46, 9.09, 9.10, 9.11, 90.90, 90.95, 227.20, 227.30, 454.50, 909.00, 2272.50` (16)
  - snap (HALF_UP): `25.29, 25.295, 25.30, 55.08, 37.39, 12345.678, 0.014, 0.009, 0.005, 0.015, 999999999` (11)
  - üs biçimleri: `1E2, 1E3, 1E+1, 2552e-2, +25.52E0, 25.520, 100.00, 1e+60, 1e400, 1e-5, 1e-400, "1"+61 sıfır, "25."+70×"5"` (13; son ikisi istisna/uzun gösterim)
  - S_h eşiği: f3 ∈ `{0.3, 0.5, 1.0, 1.1487, 3.5, 8.332, 14.6, 20, 60}` × fiyat 25.52 (9; ana modelde S_1..S_10 merdiveni, `return == rho` geçişleri)
  - PB fiyat biçimleri (yalnız `pb_ceiling_path_v0` etkisi, diğer ikisi aynı satırı `ipo_price_tl`'den koşar): `ipo_price_try ∈ {"25.29", "1E2", "25.520", "10-12"}` (4)
  - Toplam ≥ 74 yeni satır; anahtar tekrarları (`Case.key`) birleştirilir. Beklenen dosya boyu: 392 + ≥ 70 → **≥ 460 satır/model**.
- Mevcut 392 satırın hepsi üç yeni modelde de koşar (V1.5 uç girdileri, PB uçları, 99 H99, 7 sicil, 80 rastgele); `only=("v1_5_market20_v0",)` olan 3 satır hariç.

### 3.2 Yamalı parametreler (`_patched_params.jsonl` eki, `only` gerekmez)

| Etiket | Model | Yama | Beklenen |
|---|---|---|---|
| `path:insufficient` | `ceiling_path_v0` | `post_break.cells` hepsi boş, `Z.1` ilk 5 gözlem | D1..D10 `POST_BREAK_INSUFFICIENT`, `n_atoms 0`, `S` dolu [ÖLÇTÜM] |
| `path:insufficient:inf` | `ceiling_path_v0@INF` | aynı | aynı |
| `path:pooled` | `ceiling_path_v0` | `B.9` ilk 3, `B.8` ilk 4 gözlem | D9/D10 hücrelerinde `pooled: true`, `sources [[B,9],[Z,9]]`, n 21 |
| `path:pooled:pb` | `pb_ceiling_path_v0` | aynı | aynı |
| `path:clipped_pool` | `ceiling_path_v0` | `B.1` ilk 2, `Z.1` boş, `Z.2` boş, `B.2` = `[[-0.25,"XX"],[0.30,"YY"]] + ilk 6` | D2'de hücre (B,1): n 10, kırpılmış (değerler [−0.1, 0.1] içinde) |
| `path:params:n_min` | `ceiling_path_v0` | `post_break.N_MIN = 9` | `PARAMS_INVALID` |
| `path:params:margin` | `ceiling_path_v0@INF` | `limit_path.margin = "0.20"` | `PARAMS_INVALID` |
| `path:params:price_field` | `pb_ceiling_path_v0` | `limit_path.price_field = "ipo_price"` | `PARAMS_INVALID` |
| `path:params:survival_id` | `ceiling_path_v0` | `survival_model_id = "x"` | `PARAMS_INVALID` |
| `path:params:survival_gamma` | `ceiling_path_v0` | `survival_model.gamma = [0.1]` | `PARAMS_INVALID` (gamma/beta) |
| `path:params:cells_key` | `ceiling_path_v0` | `post_break.cells.B.9` silinir | `PARAMS_INVALID` |
| `path:schema` | `ceiling_path_v0@INF` | `schema_version = "borsai.model/2"` | `SCHEMA_UNSUPPORTED` |

Hepsi Python'da bu oturumda ölçüldü (§2.4, §2.6). Toplam yamalı satır 19 → 31.

### 3.3 Karşılaştırma kuralları (tests/common `cmp_output` eki; ÖNCEDEN yazılmış toleranslar)

`cmp_output`, çıktıda `limit_path` anahtarı varsa `ceiling_path` dalına girer:

| Alan | Kural | Beklenti |
|---|---|---|
| `model_id`, `clipped`, `refused.code`, `refused.field` | birebir | |
| `warnings` | (kod, `feature`\|`horizon`\|`field`) çok kümesi; `message` hariç anahtar kümeleri eşit; sayısal `value/used/train_min/train_max` \|Δ\| ≤ 1e-9; **metin** `value/snapped/tick/field` birebir | |
| `hazard[]`, `S[]`, `P_L[]`, `P_close_ceiling[]` | \|Δ\| ≤ 1e-9 | bit-eşit (aynı `predict_hazard` kodu) |
| `limit_path.ipo_price`, `snapped_ipo_price`, `tick`, `C[k]` | **metin birebir** | |
| `limit_path.rho[k]` | \|Δ\| ≤ 1e-9 | bit-eşit (60 hane → binary64 aynı yol) |
| `D{h}.return, q10, q50, q90, mean, p_up, limit_path_return, S_h, p_limit_path` | \|Δ\| ≤ 1e-9; null ↔ null | maks \|Δ\| < 1e-12; `return/q*` atom değeri olduğundan bit-eşit |
| `D{h}.n_atoms` | birebir tamsayı | |
| `D{h}.post_break` | JSON birebir (`cells` listesi sırası dahil, `status`) | |
| Koşullu: `state, j, t, note, limit_path_mismatch` | birebir | |
| Koşullu: `S_j`, `S_cond{}`, `P_L_cond{}` | \|Δ\| ≤ **1e-12** (U37 ile aynı) | bit-eşit (tek bölme) |
| Koşullu: `D{h}` OK hücreleri | yukarıdaki D-kuralları | |
| Koşullu: `REALIZED.realized_return` | \|Δ\| ≤ 1e-9 | bit-eşit |
| `expected.error.code` / `expected.exception` | mevcut kural (`DOMAIN_ERROR`; koşulluda `CONDITIONAL_INVALID`) | |

Rapor: `target/parity_report.json` model başına satır/maks \|Δ\|/bit-eşit oranı 19 model; koşullu bölümde `ceiling_path` için ayrı sayaç (`vectors`, `after_break_vectors`, `max_abs_delta`).

### 3.4 Koşullu karışım altın dosyası (U43)

**[KARAR]** `golden/<model_id>.conditional.jsonl` ayrı dosya, model başına 40 taban satır (7 sicil + seed 20260922 ile seçilen 33 H99 satırı; RET edenler atlanıp sıradaki alınır); satır biçimi:
```json
{"case_id": "ceiling_path_v0/cond/0007", "base_case_id": "ceiling_path_v0/0012", "model_id": …, "params_sha256": …,
 "output": {…taban satırın expected.output'u aynen…},
 "streak_ongoing": [{"j": 0, "closes": ["28.06", …], "expected": {…conditional çıktısı…} | {"exception": "ValueError"}} … j = 0..9],
 "streak_ongoing_mismatch": [{"j": 1|3|5, "closes": [C_t'nin bir adım altı …], "expected": …}],
 "after_break": [{"t": 0..9, "closes": [C_1..C_t, C_t × 0.95 (2 ondalığa HALF_UP) ], "expected": …}]}
```
Gerekçe: koşullu vektörleri ana dosyaya gömmek dosyayı 10 kat büyütür; 40 × 23 = 920 vektör/model üç durumu ve j/t'nin tamamını kapsar (dosya ≤ 1.5 MB). Rust testi `output`'u JSON olarak `path::conditional`'a verir (kayıt yolu ile aynı). Beklentiler: j = 0 vektörü koşulsuz `D{h}` ile bit-eşit (`return, p_up, q10, q50, q90, mean, n_atoms`); `mismatch` satırlarında `limit_path_mismatch = 1` ve h ≤ j hücreleri `REALIZED`; `after_break` t = 0'da `n_atoms = 18` (Z,h), t ≥ 1'de `n_atoms = n(B, h − t)`.

### 3.5 `PINNED_MODEL_IDS` 16 → 19 ve "16" sabitleri

- `build_embed.rs: PINNED_MODEL_IDS: [&str; 19]` (son üç: `ceiling_path_v0`, `ceiling_path_v0@INF`, `pb_ceiling_path_v0`); `ignored_model_ids` boş kalır ama mekanizma korunur (SPEC_APP §8-2). **[KARAR] sıra kuralı: INDEX sırası, ek her zaman sona;** gerekçe: `verify` ORDER_MISMATCH denetimi ve `predict_all` sütun sırası INDEX'e bağlıdır.
- Değişecek sabitler [ÖLÇTÜM]: `tests/build_embed.rs: plan_pins_first_16_index_entries` (ad ve 19), `tests/integrity.rs` `EMBEDDED_MODELS.len() == 16` → 19 (iki yerde), `crates/borsai_predict/tests/golden.rs` `golden_files_present` (16 → 19; `index_entries(16)` → 19), `golden_parity` (`stats.len() == 16`, `models_passing == 16` → 19), `conditional_parity` (6 kalır: hazard/km; `ceiling_path` ayrı test `conditional_path_parity`), `records_parity` (bkz. §3.7), `app/parity/test_gen_golden.py` (PINNED 19), `README`/`golden/README.md` metinleri, TS `Kind` birliği (`"ceiling_path"`), `KIND_TEXT`. Aşama 3'ün "desteklenen küme gömülü veriden" kuralı (FAZ3_APP_STAGE3 değişen 1) burada da geçerlidir: parite ve ekran kodunda 16/19 sabiti YOK.
- **U46 — 16 altın dosya bayt-eşit:** `for f in 16 model: cmp app/parity/golden/<f>.jsonl <(git show 0b67f5d:app/parity/golden/<f>.jsonl)`; `_patched_params.jsonl`'ın ilk 19 satırı bayt-eşit (yeni satırlar sona eklenir). `MANIFEST.json` değişir (`model_ids` 19, `rows` 19 anahtar, `n_cases`, `patched_rows`, `predict_sources_sha256` 8 dosya, `models_index_sha256` = `1bc33791…`, yeni `conditional_rows`). `dec_cases.json`'a `limit_path` bölümü eklenir (bkz. §2.3 tablosu; metinler Python'dan yazılır) — bu dosyanın mevcut bölümleri bayt-eşit kalır.

### 3.6 Kapsama (U44, `coverage.rs` eki)

Ek sayımlar (yalnız `ceiling_path` dosyalarında): uyarı `IPO_PRICE_NOT_ON_TICK_GRID` ≥ 2 satır (her üç modelde); `@INF` dosyasında `INPUT_MISSING/INPUT_NOT_NUMERIC/INPUT_NOT_POSITIVE` alanı `ipo_price_tl` ≥ 2 (mevcut `missing:`/`not_positive:` satırlarından gelir); `expected.exception` ≥ 2 (`Inexact` ve `ValueError`); `status:POST_BREAK_INSUFFICIENT` ≥ 2 ve `pooled` ≥ 2 ve kırpılmış havuz ≥ 1 **yalnız yamalı satırlarda** (MANIFEST `coverage_exemptions`: "dondurulmuş hücrelerde havuzlama tetiklenmez: her hücre ≥ 11"); `S_h ≥ 0.5` ve `< 0.5` satırları h = 1, 3, 5, 10'un her birinde ≥ 5'er (ana modelde f3 merdiveniyle); `snap ≠ P` ≥ 2, `snap = P` ≥ 2; koşullu dosyada j = 0..9 ve t = 0..9 her biri ≥ 40.

### 3.7 Resmi kayıt paritesi (U6 eki) ve aşama 3 bağlantısı

- `records_parity`: kayıttaki her model hücresi için Rust'ta tür biliniyorsa karşılaştırılır (19'un hepsi); kayıtta olup INDEX'te olmayan ya da INDEX'te olup kayıtta olmayan model "kapsam dışı" DEĞİL, "kayıt sürümü farklı" olarak sayılır ve raporlanır. Mevcut 7 kayıt 16 modelli → 7 × 16 hücre karşılaştırılır, 3 model "kayıtta yok" (uyuşmazlık değil). Yeni kayıtlar (19) → 19 hücre.
- Aşama 3 (FAZ3_APP_STAGE3 değişen 1): parite adımı desteklenen kümeyi gömülü veriden okur; port gelince ekran metni kendiliğinden `parite: 19/19 desteklenen model, |Δ|max = …` olur ve "uygulamada henüz olmayan" listesi boşalır. Ek kural: kayıt sürümü 16 modelli eski kayıtsa `kayıt INDEX'ten eski: 3 model kayıtta yok` satırı (incident değil). Karşılaştırma kuralları §3.3.

---

## 4. Gösterim (SPEC_APP §3b ve §3g eki)

### 4.1 Grup A'da Faz 4 sütunları (D1/D3/D5/D10)

- Grup A sütun sırası **[KARAR]**: doğrusal/PB/market20 modelleri → `ceiling_path` modelleri (INDEX sırası) → basit kurallar; gerekçe: `ceiling_path` skorlamada getiri/p_up modelidir (`scoring.comparators`), kurallar yine sağda kalır. `isGroupB` değişmez (hazard/km); `ceiling_path` Grup B'de GÖRÜNMEZ: S vektörü gömülü seri modeliyle bit-eşittir (U45) ve iki kez çizilmesi bilgi katmaz; sütun başlığında "S: `<survival_model_id>` ile aynı" notu.
- Hücre içeriği (h ∈ {D1, D3, D5, D10}): **medyan getiri %** (1 ondalık, işaretli) + rozet `medyan`; altında **%10–%90** küçük gri (`q10`–`q90`, 1 ondalık); `p_up` yüzde 0 ondalık ve yön oku (`p_up ≥ 0.5 → ↑`, aksi `↓`; görüntüleme kuralı, çıktıda `direction` yoktur); `S_h` yüzde (tooltip "P(limit yolu D{h}'e kadar)"); fiyat satırı **[KARAR]**: `return == limit_path_return` (bit-eşit) ise `C_h TL` metni (kayıt/çıktıdaki `limit_path.C[h−1]` dizesi, rozet `limit yolu`), değilse `≈ P × (1 + medyan)` Rust `path_display` komutundan (görüntüleme türevi, gri, tooltip "kayıtta yoktur"); gerekçe: limit atomu tam kapanış fiyatıdır ve fiyat adımı yuvarlaması içerir, medyan ise atomlar arasında seçilmiş bir getiridir, TL karşılığı yaklaşıktır. Kırpma işareti yok (`return_clipped` yoktur). `POST_BREAK_INSUFFICIENT` hücresi: `—` + tooltip T-2 metni. Tooltip ham değerler `pyRepr` ile (`return, p_up, mean, q10, q90, S_h, n_atoms`).
- "backtest tipik hata" satırı: `scores.json`'da hücre yoksa satır yok (bugün yok, §5).
- RET bloğu Grup A'daki gibi (VEYAS: `ceiling_path_v0` `RET · F3_MISSING`).
- Senaryo modu: aynı; filigran ve tooltip SPEC_APP §3c.

### 4.2 Grup C — "Tavan yolu: getiri dağılımı (h = 1..10)"

Grup B'nin altında, yalnız INDEX'te `ceiling_path` modeli varken (yoksa bölüm yok). Model seçici Grup C sütunlarını da kapsar. İçerik, seçili `ceiling_path` modelleri için:
- **Tablo** satır h = 1..10, sütun model: `medyan % · [q10, q90] · p_up % · S_h % · C_h TL · n_atoms`; hücre `title` ham değerler. `POST_BREAK_INSUFFICIENT` satırı gri.
- **Yelpaze grafiği (SVG, ön uçta ≤ 80 satır)**: x = h, y = getiri; her model için q10–q90 bandı (yarı saydam), q50 çizgisi, `rho_h` (limit yolu) kesikli; renk `colorOf(model_id)`. U25 uyarınca ön uç yalnız piksel koordinatı hesaplar.
- **Limit yolu satırı**: `ipo_price`, `snapped_ipo_price` (farklıysa sarı `IPO_PRICE_NOT_ON_TICK_GRID` metni), `tick`, `C_1..C_10` (metin aynen). SPEC_APP §3b'deki "≈ arz × 1.1^k" bilgi satırı Grup B'de kalır; Grup C'de kesin C_h vardır ve ikisi yan yana durabilir ("Grup B: yaklaşık; Grup C: fiyat adımı kuralıyla kesin").
- **Hücre notu** (katlanır): h başına `post_break.cells` (`group, m, n, pooled, sources`) — "kırılma sonrası hücre: H99'un 99 arzından, kesim 2026-08-19, N_MIN = 10".
- Rejim uyarısı ve DISCLAIMER SPEC_APP §3b/§4.

### 4.3 "Getiri (koşullu)" sekmesi (§3g eki)

Koşullu bölümde mevcut sekme (`COND.tabReturn`); `returnNone` metni yalnız INDEX'te `ceiling_path` modeli yokken kalır. Doluyken:
- **Durum seçimi** şeritten (Rust `streak_view`): `broken = false` → **durum 1**, `j` = seçilen j (resmi gözlenen ya da varsayımsal; kullanıcı beyanı j'ye girmez, SPEC_APP §3g ve U52); `broken = true` ve seçilen j = gözlenen → **durum 2**, `t = j_observed`. Varsayımsal j (seçilen ≠ gözlenen) durum 1'dir ve "varsayımsal j" etiketi taşır; kırılmış seride varsayımsal j > t seçilirse "seri D{t+1}'de bozuldu; varsayımsal j için durum 1 hesaplandı" uyarısı.
- **Gözlenen kapanış kaynağı [KARAR]:** durum 1'de `closes[t] = data/outcomes/<T>.csv` `close_raw` (h = 1..j; `status = OK` satırları); durum 2'de h = 1..t+1. Resmi j'de h = 1..j satırlarının hepsi `status = OK`'tir; varsayım gerekmez. Eksik kapanış yerine **`C_t` (limit yolu) varsayımı** yalnız varsayımsal j > resmi j seçildiğinde kullanılır ve satır "kapanış varsayımı: limit yolu (varsayımsal j)" etiketi alır. **Kullanıcı beyanı hiçbir koşulda bu hesaba girmez [KARAR, proje sahibi 2026-09-23]:** beyan resmi verinin önündeyse kart boş kalır ve "resmi kapanış bekleniyor" yazar (SPEC_APP §3g, U52). Durum 2'de `close(D_{t+1})` dosyada yoksa durum 2 **hesaplanmaz**, "kırılma günü kapanışı dosyada yok; kırılma sonrası dağılım için resmi kapanış gerekir" yazılır. Gerekçe: durum 1'de t ≤ j kapanışları yalnız `scale` ve `mismatch` için gerekir ve limit yolu varsayımı SPEC_PATH §7'nin t > j için zaten kullandığı değerdir; durum 2'de ise gözlenen kapanış dağılımın ölçeğidir, uydurulmaz. Rust komutu `path_conditional(model_id, source, j_or_t, state)` kapanışları KENDİSİ okur (ön uç okumaz), hangi h'lerin dosyadan hangilerinin varsayım olduğunu döner.
- **Gösterim:** h = 1..10 satırı: `REALIZED` satırlarında gerçekleşen getiri % (+ kaynak `session_date`), diğerlerinde medyan/[q10,q90]/p_up/S_h (koşullu)/n_atoms; üstte `S_j`, `P(L = t | L ≥ j)` çubukları (durum 1); durum 2'de "kırılma sonrası, D_t'ye koşullu (SPEC_PATH §7-2); D_{t+2}… gözlemleri koşullanmaz" notu (`note` alanı aynen). Yelpaze grafiği h > j (ya da h > t+1) için.
- **`limit_path_mismatch = 1`:** sarı kutu "gözlenen kapanış limit yolundan sapıyor: D{t} gözlenen {close} / C_{t} {C}" (ilk sapan t), SPEC_PATH §2 açık soru 1'e atıf; hesap yine gösterilir. Bu bayrak da kayda ya da dosyaya yazılmaz.
- **Resmi görünüm (U38 ilkesi) [KARAR]:** arz sayfasında koşullu getiri YALNIZ dondurulmuş kaydın `models[<path model>].output` alanından (`limit_path`, `S`, `D*`) ve gömülü `params.post_break.cells`'ten hesaplanır; `predict_all` çağrılmaz (komut çağrı sayacı 0, U49); hücreler gömülü parametreden okunduğu için kayıttaki `params_sha256` gömülü sha ile eşit olmalı, değilse "kayıt farklı parametreyle yazılmış (sha …); koşullu getiri hesaplanamaz" (model yeniden çalıştırılmaz). Kayıt 16 modelliyse "bu kayıt Faz 4 modellerini içermiyor (kayıt INDEX'ten eski)". Kaynak satırı: "kaynak: kayıt <dosya>, params sha <ilk 8>".
- **Senaryo modunda** senaryo çıktısından; filigran §3c. Kişisel kayıtta (`borsai.app_scenario/1`) `outputs.<path model>` zaten saklanır; ek alan yok.

### 4.4 Sicil ekranı, model kartı, metinler

- Sicil kayıt sayfası: kayıttaki `ceiling_path` hücreleri Grup A/C ile aynı render (kayıt değerleri; U38); FAZ3_APP_STAGE3 değişen 5'teki "bu modelin gösterimi Faz 4 portuyla gelecek" metni portla kalkar.
- Model kartı: `KIND_TEXT.ceiling_path = "tavan yolu (S_k + limit yolu + kırılma sonrası hücreler)"`; "ne yapar" `description`; ek satır "seri modeli: `<survival_model_id>` (sha ilk 8)"; birincil hücre `scores.json`'dan (bugün null → "—; SPEC_CEILING_PATH_V0 §5: D5 getiri MAE, `base_train_median`" bilgi notu, değer uydurulmaz).
- U7 güncellemesi: f3 boş girdi → **5 RET** (`v1_5_h99`, `v1_6_h99`, `v1_5_market20_v0`, `ceiling_hazard_v0`, `ceiling_path_v0`) + **14 dolu** sütun.

---

## 5. §2.3 eki: `scores.json`'da Faz 4 modelleri

- `models[].kind = "ceiling_path"`: uygulama bloğu getiri/p_up modeli gibi okur (`backtest.cells` `output ∈ {return, p_up}`, `live.rows[].prediction.D{h}.{return, p_up}`); ek alan yok. `primary_cell` null ise kart "—" (uydurma yok).
- **Bugünkü durum [ÖLÇTÜM]:** `backtest.cells = []` ve `live.n_rows = 0`; panelde "bu model için backtest hücresi yok (scores.json üretmedi)" ve canlı bölümde "n = 0" hâli (SPEC_APP §3d "canlı kayıt henüz skorlanmadı"). Neden ön koşul görevi Ö1'dir; uygulama beklemez.
- `retro_info[]`: `{model_id, ticker, record_id: null, inputs_pit_problems, class_evidence{basis, d1, model_frozen_at, model_params_sha256, outcome_ingest_commit, …}}` — 21 satır; RETRO bölümünde model başına gruplanır: "`ceiling_path_v0` — CITAS, TKNKA, VEYAS, KPEKS, … (7): model sonuçtan sonra donduruldu, kayıt yok" (`basis` metni tooltip). Hiçbir n'e girmez (U26).
- Üst düzey `separate_models`, `definitions`, `outcomes`: yok sayılır (şema "alan eklenebilir").
- **İleride `models[].conditional` (SPEC_PATH §7, Faz 2C) — okuyucu sözleşmesi [KARAR]:**
  ```json
  {"schema_version": "borsai.scores_conditional/1", "title": "Koşullu tavan skorları (canlı, j başına)",
   "scale": "live_conditional",
   "by_j": [{"j": 1, "n_scored": 0, "n_refused": 0, "n_skipped": 0, "n_target_unavailable": 0, "n_live": 0, "n_late": 0,
             "rows": [{"ticker", "class", "record_id", "L", "S_cond": {...}, "rps_cond", "brier_next", "brier_10", "status"}],
             "cells": [{"output": "S_cond"|"p_up_cond"|"return_cond", "horizon_or_k", "metric": "RPS"|"Brier"|"MAE",
                        "model_value", "rule_id", "rule_value", "diff", "ci95", "n", "wins", "losses", "ties", "verdict"}]}]}
  ```
  Uygulama: blok yoksa "henüz koşullu skor yok"; `schema_version` bu değer değilse "desteklenmeyen koşullu skor bloğu (sürüm X)" ve blok gösterilmez; her `by_j` öğesi kendi `n_scored`'uyla SPEC_APP §3d küçük-n kurallarına (n < 10 satır tablosu; 10–29 "yetersiz örnek"; ≥ 30 hüküm) ve §2.3 bütünlük denetimine (n < 10 iken `cells` boş; `n_live + n_late = n_scored`) girer; j'ler ve koşulsuz tablo asla toplanmaz (U22 taraması genişler). Gerekçe: SPEC_APP §2.3 bloğu "isteğe bağlı" bırakmıştı; Python henüz üretmediğinden şekli burada sabitlemek uygulamayı ikinci kez değiştirmekten korur (açık soru 4).

---

## 6. Aşama, U-testleri ve oturum tahmini

**[KARAR] Yeni Aşama P (Faz 4 portu), aşama 3'ten sonra:** P1 = port + parite (U41–U47), P2 = gösterim (U48–U50); U51 aşama 4 (doğruluk paneli) ile birlikte. Gerekçe: aşama 3'ün parite adımı ve sicil ekranı port olmadan "uygulamada henüz yok" diyerek yeşil kalır, P1 bittiğinde aynı kod 19/19 der; P2 aşama 4 ile paralel yürüyebilir.

| # | Test | Yöntem | Kanıt |
|---|---|---|---|
| U41 | Gömülü seri modeli bütünlüğü: üç `ceiling_path` modelinde `survival_model_sha256` = INDEX sha (`caa4dc86…`, `c5ac8085…`, `7fb7a41e…`) ve `survival_model` = gömülü dosyanın JSON değeri; kopyanın bir sayısı değiştirilmiş test-içi kopya → `INTEGRITY_FAILED / SURVIVAL_MODEL_MISMATCH`; INDEX'ten seri modeli çıkarılmış kopya → aynı | `cargo test --test integrity survival_model_integrity` | çıktı |
| U42 | Altın parite 19/19: üç yeni dosya ≥ 450 satır; §3.3 kuralları; `parity_report.json` `models_passing = 19`, maks \|Δ\| ≤ 1e-9; `predict_sources_unchanged` 8 dosya | `cargo test -p borsai_predict --test golden` | rapor |
| U43 | Koşullu karışım paritesi: `<model>.conditional.jsonl` 3 × 40 taban satır × (10 + 3 + 10) vektör; `S_cond/P_L_cond/S_j` ≤ 1e-12, D-hücreleri ≤ 1e-9; j = 0 koşulsuzla bit-eşit; `mismatch` satırlarında bayrak 1; istisna satırları `CONDITIONAL_INVALID` | `cargo test -p borsai_predict --test golden conditional_path_parity` | rapor koşullu bölümü |
| U44 | Kapsama (§3.6) | `cargo test -p borsai_predict --test coverage` | `golden_coverage.json` |
| U45 | S bit-eşitliği: her altın satırda `ceiling_path_v0.S` = aynı girdiyle `ceiling_hazard_v0.S` (bit), `@INF` ↔ `ceiling_hazard_v0@INF`, PB ↔ `pb_ceiling_v0`; ret kodları ve alanları da birebir (`F3_MISSING` dahil) | `cargo test -p borsai_predict --test golden survival_passthrough` | çıktı |
| U46 | 16 altın dosya ve `_patched_params.jsonl` ilk 19 satırı `0b67f5d` ile bayt-eşit; `dec_cases.json` eski bölümleri bayt-eşit | `bash app/tests/golden_unchanged.sh` (`git show 0b67f5d:…` ile `cmp`) | betik çıktısı |
| U47 | Decimal ek anlamı: `div_exact` üs kuralı (§2.2 ölçümleri), `to_integral` üs koruması, `py_str` (`1E+2`, `1E-7`, `0.000001`, `1.0`, `0.00`, `1.00000…E+61`), `ctx_round` (kesin kısalma vs `Inexact`), limit yolu tablosu (§2.3, 14 satır) — beklenenler `gen_golden.py --dec-cases` ile Python'dan | `cargo test -p borsai_predict --test dec_semantics limit_path` | çıktı |
| U48 | Grup A üç sütun + Grup C render: fixture `runs_veyas.json` (Rust gerçek çıktısı, 19 model: 5 RET + 14 dolu), `runs_netgl.json`; Grup C tablosu 10 satır, yelpaze SVG q10/q50/q90/rho 4 seri, C_h metinleri aynen; fiyat kuralı (`return == rho` → C_h + "limit yolu", değilse "≈"); `POST_BREAK_INSUFFICIENT` fixture (yamalı) `—`; ön uçta hesap yok taraması genişler (yalnız SVG piksel) | vitest + `cargo test --test stage2` fixture üretimi + ekran görüntüsü | ikisi |
| U49 | "Getiri (koşullu)" sekmesi: fixture'lar `streak_all10` (durum 1, j = 3 seçili), `streak_broken` (durum 2, t = 2), `streak_pending` + beyan (kart boş, "resmi kapanış bekleniyor"; U52), mismatch (kapanış C_t'den sapan sentetik CSV); resmi görünümde kayıt-dışı kaynak yok: `predict_all` sayaç 0, kayıt `output.S` kasten `0.5^k` yapılmış test kaydında ekrandaki `S_cond` `0.5^(k−j)`; 16 modelli kayıtta "kayıt Faz 4 modellerini içermiyor" | vitest + `cargo test --test stage3 official_conditional_return_uses_record_only` + `e2e_personal_isolation.sh` (dosyalara yazılmadı) | çıktı |
| U50 | Kayıt paritesi 19: geçici klonda `freeze` ile yazılan kayıt 19 model içerir, parite ekran satırı `19/19`; eski 7 kayıt `16/16 + 3 kayıtta yok`; `records_parity` maks \|Δ\| ≤ 1e-9 | `e2e_freeze_tmp_repo.sh` + `BORSAI_REPO=… cargo test --test records_parity` | betik çıktısı |
| U51 | Doğruluk paneli: `kind = ceiling_path` bloğu; boş backtest → "hücre yok" metni; `retro_info` model başına gruplu, n'e girmez; `conditional` yok → "henüz koşullu skor yok"; sentetik `conditional` bloğu (`docs/app/ekler_ek2/scores_conditional_sentetik.json` — bu ekte yazılmadı, uygulayıcı §5 şemasıyla üretir, `synthetic: true`) j = 1 (n = 4) satır tablosu, j = 3 (n = 12) "yetersiz örnek"; yanlış sürüm → mesaj | vitest | çıktı |

**Oturum tahmini (Opus):** P1 2 oturum (dec eki + `path.rs` + params/output 1; gen_golden + testler + kapsama 1), P2 1.5 oturum (Grup A/C + koşullu sekme 1; sicil/kart/metinler 0.5), U51 aşama 4 içinde +0.5. **Toplam ≈ 4 oturum.** Mevcut 16 dosya bayt-eşit kalmazsa nedenini raporda gerekçelendirmek zorunludur (U46); beklenen neden yoktur.

Uygulayıcı kuralları SPEC_APP §7 ile aynı: yalnız `app/`; Python salt okunur; tolerans gevşetilmez; parite tutmuyorsa Rust düzeltilir; Python'da eksik bulunursa Ö-görevi olarak raporlanır, düzeltilmez.

---

## 7. ÖNCEDEN YAZILMIŞ BEKLENTİ

Yazım 2026-09-22, port kodu yokken; sayılar Python `predict_path` koşusundan (girdi verisi; sonuç verisi okunmadı).

- **Parite:** 19/19 model geçer; üç yeni modelde maks \|Δ\| < 1e-12 (izin 1e-9); `limit_path.rho`, `D*.return/q10/q50/q90`, `S` bit-eşit; `p_up/mean` bit-eşit (py_sum); bit-eşit satır oranı hazard modellerinin oranından düşük değil (sigmoid/exp libm payı aynı). Koşullu: `S_cond` maks \|Δ\| = 0.
- **Altın satır sayıları:** 16 eski dosya 392 (`v1_5_market20_v0` 395), değişmez; üç yeni dosya ≥ 460'ar (392 + ≥ 70 uç); yamalı 31; koşullu 3 × 40 satır (920 vektör/model).
- **Dondurulmuş hücrelerle** her tahminde `n_atoms = [19, 86, 150, 210, 264, 312, 352, 380, 395, 406]`, hiçbir hücre `pooled`, hiçbir satır `POST_BREAK_INSUFFICIENT` (yamalı hariç).
- **VEYAS girdileri (`registry/inputs/VEYAS.json`, f3 boş, fiyat 136):**
  - `ceiling_path_v0` → **RET** `F3_MISSING` / `total_demand_multiple` (miras; `S` null).
  - `ceiling_path_v0@INF` → tahmin, uyarı yok; `limit_path`: `ipo_price "136"`, `snapped "136.0"` (Decimal-eşit, uyarı YOK), `tick "0.10"`, `C = 149.60, 164.50, 180.90, 198.90, 218.70, 240.50, 264.50, 290.75, 319.75, 351.50`; `D1 return 0.1, p_up 0.9064625850340136`; `D3 0.3301470588235294 / 0.8173697881702022`; `D5 0.3521329606222654 / 0.7839846747553669`; `D10 0.2700421819022305 / 0.7369266602370846`; `S = 0.8316, 0.7468, 0.6707, 0.5347, 0.4263, …` (4 ondalık); `return == rho` h = 1..4'te, h ≥ 5'te değil.
  - `pb_ceiling_path_v0` → tahmin; uyarılar `OUT_OF_TRAINING_RANGE` (`pb1 = 22.9026 > 22.6439`) ve `PB4_ADDITIONAL_SALE_CEILING` (`pb4 = 19.23`); `ipo_price "136.00"`; `D1 0.1 / 0.7507200510340583`; `D3 0.03840682788051209 / 0.5467949148405984`; `D5 0.0 / 0.4913412249290071`; `D10 −0.005041297340854123 / 0.46010491627739736`; `S_1 = 0.5513`.
  - Sonuç ekranı: **5 RET + 14 dolu**; Grup C'de 2 sütun (`@INF`, PB) ve `ceiling_path_v0` RET bloğu.
- **NETGL girdileri (ana model):** `C = 28.06, 30.86, 33.94, 37.32, 41.04, 45.14, 49.64, 54.60, 60.05, 66.05`; `return` h = 1..10: `0.09953, 0.20925, 0.32994, 0.23339, 0.23606, 0.1886, 0.17608, 0.16842, 0.12787, 0.13238` (5 ondalık); `S_1..S_3 ≥ 0.5`, `S_4 = 0.4062 < 0.5` → medyan h = 4'ten itibaren limit atomundan ayrılır.
- **Aşama 3 ekranı** port sonrası: `parite: 19/19 desteklenen model`; eski 7 kayıt: `16/16 + kayıtta yok: 3`.

---

## 8. Ön koşul görevleri (Python tarafı; bu ekte DÜZELTİLMEDİ)

| # | Ne | Neden | Dosya |
|---|---|---|---|
| Ö1 | `scoring.backtest_cells` ve `PRIMARY_CELLS`'e `ceiling_path` dalı (SPEC_PATH §5 tablosu: getiri MAE → `base_always_ceiling`, `base_train_median`, `v1_5_h99`, sıfır model; p_up Brier → `base_rate`, `base_last10_rate`, `v1_5_h99`, sıfır model; birincil D5 MAE–`base_train_median`; PB için `pb_v0` ve `__pb` kuralları) | `scores.json`'da üç modelin backtest hücreleri boş ve `primary_cell` null [ÖLÇTÜM]; uygulama kartı ve "backtest tipik hata" satırı bu yüzden "—" gösterir; MODELS.md'de tablolar var, `scores.json`'a taşınmamış | `borsai/scoring.py` (`backtest_cells`, `PRIMARY_CELLS`), `scores/scores.json` yeniden üretim, `docs/SCORES.md` |
| Ö2 | `models[].conditional` üreticisi (SPEC_PATH §7 canlı tanımı; Faz 2C) — §5'teki okuyucu şemasıyla | Bugün blok yok; uygulama "henüz yok" gösterir; şema uyuşmazsa uygulama ikinci kez değişir | `borsai/scoring.py`, `docs/specs/SPEC_SCORING.md` eki |
| Ö3 | `scoring.comparators` `ceiling_path` için `v1_5_h99`'u içermiyor (`LINEAR_VS_V15` listesinde değil); SPEC_PATH §5 canlıda da V1.5 karşılaştırması ister | canlı hücreler (n ≥ 10 olunca) şartnamedeki karşılaştırmaların bir kısmını üretmeyecek | `borsai/scoring.py: LINEAR_VS_V15 / comparators` |

Uygulama tarafında ön koşul yoktur: `predict_path.py` referans işlevlerinin hepsi (`predict, limit_path, mixture_atoms, summarize, conditional, conditional_after_break, conditional_weights, pool, ladder`) mevcut ve stdlib; `freeze.build_record` 19 modeli yazıyor; `close_raw` Decimal-ayrıştırılabilir.

---

## 9. Açık sorular (proje sahibine; en çok 5)

| # | Soru | Önerim |
|---|---|---|
| 1 | Grup A'da Faz 4 fiyat hücresi: medyan limit atomuysa kesin `C_h`, değilse `≈ P × (1 + medyan)` (görüntüleme türevi) mi; yoksa fiyat hiç gösterilmesin mi? | Öneri §4.1'deki gibi; "≈" gri ve tooltip'li. Fiyat adımı kesinliği yalnız limit yolunda anlamlıdır. |
| 2 | Faz 4 modelleri Grup B'de (S eğrisi) de görünsün mü? | Hayır: S bit-eşit kopyadır (U45); sütun başlığında "S: ceiling_hazard_v0 ile aynı" notu yeter. |
| 3 | Koşullu getiri sekmesinde gözlenen kapanış dosyada yokken (yalnız beyan) durum 1 için `C_t` varsayımı kabul mü? Durum 2 beyanla hesaplanmaz. | **Proje sahibi kararı (2026-09-23): Hayır.** Beyan hiçbir koşulda getiri ya da olasılık hesabına girmez; yalnız "seri sürüyor" etiketiyle görünür. Koşullu getiri kartı resmi kapanış gelene kadar "resmi kapanış bekleniyor" uyarısıyla boş kalır. SPEC_APP §3g ve U52. Diğer dört soruda öneri onaylandı. |
| 4 | `models[].conditional` şemasını (§5) Faz 2C bu şekilde mi üretsin? | Evet; `schema_version = borsai.scores_conditional/1`, j başına ayrı `n`, SPEC_SCORING §8 küçük-n dili aynen. |
| 5 | Aşama P, aşama 4'ten (doğruluk paneli) önce mi? | P1 aşama 3 commit'inden hemen sonra (parite 19/19 ve yeni kayıtlar için gerekli); P2 aşama 4 ile paralel yürüyebilir. |

---

## 10. Maruziyet (bu oturum)

**Gördüm:** SPEC_APP tamamı; SPEC_PATH tamamı; `borsai/predict_path.py`, `survival.py`, `freeze.py`, `predict_hazard.py` (baş ve kuyruk), `features.py` (parse işlevleri), `scoring.py` (ilgili işlevler), `outcomes.py` (yalnız sütun/durum sabitleri ve `close_raw` ayrıştırma satırı); `models/INDEX.json`; üç Faz 4 JSON'unun üst düzey anahtarları, `limit_path`, `post_break` sayımları, `survival_model` anahtarları (hücre değerlerinin ilk 3'ü ekranda göründü); `app/parity/gen_golden.py`, `golden/MANIFEST.json`, `README`'ler, `build_embed.rs`, `borsai_predict` kaynakları ve testleri, `commands/{models,predict,ceiling,scores}.rs`, `state.rs`, `types.ts`, `render/{results,ceiling}.ts`, `screens/results.ts`, `tr.ts` (koşullu bölümü), `tests/{build_embed,integrity,stage2}.rs`; `scores/scores.json` (üç Faz 4 bloğu, `retro_info`, bir V1.5 ve bir tavan bloğunun hücre/satır örneği — bu satırlar 7 arzın gerçekleşen değerlerini içeriyordu; yalnız şema için bakıldı, hiçbir değer bu belgeye alınmadı); `registry/inputs/VEYAS.json` ve `NETGL.json` girdi değerleri; kayıtların model sayısı ve ret özeti; `data/outcomes/*.csv` yalnız başlık satırı; `tests/test_outcome_guard.py` ve `test_faz1b_guardrails.py` (bekçi kalıpları); `docs/prompts/FAZ3_*` görev dosyaları.

**Koştum:** `predict_path.predict` (H99 girdi sütunları, VEYAS, NETGL, sentetik fiyatlar), `conditional`/`conditional_after_break` (NETGL, sentetik kapanışlar), `pool`/`ladder` (yamalı hücreler), Decimal üs/metin ölçümleri. Model fit edilmedi, backtest koşulmadı, `data/outcomes` değerleri okunmadı.

**Görmedim:** `docs/fable_faz4_audit/`, `docs/MODELS.md` (yalnız üç satır grep), `experiments/log.jsonl`, `tests/test_faz4_ceiling_path.py` (yalnız `survival_model` satırları grep), `app/src/i18n/tr.ts`'in geri kalanı, `commands/{scenario,inputs_doc,config,form,market20,git}.rs`.

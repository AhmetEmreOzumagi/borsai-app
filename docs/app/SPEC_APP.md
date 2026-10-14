# SPEC_APP — BorsAi masaüstü uygulaması şartnamesi (Faz 3)

Görev: BORSAI_FAZ3_FABLE_APP_SPEC_20260922. Yazan: Fable. Uygulayıcı: Opus (Claude Code), `app/` altında. Bu belge uygulayıcının sormadan kodlayabileceği kadar kesin olmak zorundadır; her karar gerekçelidir, her kabul testi kanıtlanabilirdir.

## Özet (11 satır; EK 1 ile bir satır eklendi)

1. Tauri 2 + Rust arka uç + sade TypeScript (Vite, çerçeve yok). Ağ erişimi yok. Yalnız macOS arm64, kişisel kullanım; imza ertelenir.
2. `predict`'in uygulamadaki TEK gerçeklemesi Rust'tadır (`app/src-tauri/crates/borsai_predict`, Tauri'siz saf crate). Tanım Python'dakidir (`borsai/predict*.py`); Rust bir porttur. Parite: Python'un ürettiği altın vektörler (model başına ≥ 200 girdi, uçlar ve ret yolları dahil) `cargo test` ile |Δ| ≤ 1e-9; ret ve uyarı kodları birebir.
3. Model JSON'ları ve `models/INDEX.json` derlemeye gömülür (salt okunur); açılışta her dosyanın sha256'sı INDEX ile doğrulanır, uyuşmazlıkta tahmin kapalıdır.
4. Resmi sicilin tek yazıcısı Python `borsai.freeze` olarak kalır; uygulama girdi belgesini (`registry/inputs/<T>.json`) yazar, `python -m borsai.freeze` çağırır, çıkan kaydı kendi tahminiyle parite denetiminden geçirir ve commit + push + push kanıtı talimatını gösterir. Resmi sicil repodadır; uygulama verisinde asla değildir.
5. Uygulama skor hesaplamaz. Doğruluk paneli yalnız `scores/scores.json`'u (`borsai.scores/1`) gösterir; SPEC_SCORING §7–§8 gösterim kurallarının her biri bir kabul testine bağlıdır (§5, tablo T-1).
6. Koşullu tavan güncellemesi (EK 1, §3g): "seri j gün sürdü" bilgisiyle P(L ≥ k | L ≥ j) = S_k / S_j; resmi görünümde DONDURULMUŞ kaydın S vektöründen, senaryoda senaryo çıktısından; model yeniden çalıştırılmaz. Gözlenen seri birincil olarak `data/outcomes/<T>.csv`'den, ikincil olarak "kullanıcı beyanı" etiketiyle elle; beyan yalnız şeritte etiket olarak görünür, hiçbir olasılık ya da getiri hesabına, skora ve sicile girmez (proje sahibi kararı 2026-09-23, U52).
7. Senaryo modu (kullanıcının kendi sayıları) ve kişisel kayıtlar uygulama verisindedir (`borsai.app_scenario/1`); sicile ve skora hiçbir yoldan giremez; bu bir testle gösterilir (U27–U30).
8. f6 (XU100 20 seans getirisi): uygulama ağa çıkmaz. Senaryoda f6 ya "repo modu"nda Python `borsai.market20` ile pinli dosyalardan hesaplanır ya da kullanıcı elle girer (etiketli); resmi kayıtta f6'yı her zaman `borsai.freeze` hesaplar.
9. Dil Türkçe; "tahmin" ve "olasılık" sözcükleri; tek satırlık "yatırım tavsiyesi değildir" yer tutucusu her ekranda.
10. Aşamalar: (0) kurulum → (1) predict + parite → (2) ekranlar → (3) dondur akışı → (4) doğruluk paneli → (5) kişisel kayıtlar. Her aşamanın kabul kapısı §7'de.
11. Model davranışını değiştiren hiçbir şey yoktur: f3 yokken tahmin uydurulmaz, kırpma ve ret kuralları Python'dakidir.

İşaretler: **[ÖLÇTÜM]** = bu oturumda dosyadan/komuttan; **[ÇIKARIM]** = yorum; **[KARAR]** = bu şartnamenin bağlayıcı kararı.

Bağlayıcı üst belgeler: `CLAUDE.md` (6 kural + sıra kuralı), `docs/specs/SPEC_SCORING.md` §7–§9, `docs/specs/SPEC_CEILING_V0.md`, `SPEC_PB_V0.md`, `SPEC_MARKET20_V0.md`, `SPEC_V1_6.md`, `docs/SPEC_DEVIATIONS.md` (B2, B3, B7, C1–C5). Çelişkide üst belge kazanır; bu belge yalnız uygulamayı tanımlar.

---

## 1. Mimari

### 1.1 Katmanlar

```
┌──────────────────────────── Tauri 2 penceresi (WebView) ────────────────────────────┐
│  Ön uç: TypeScript (Vite, vanilla). Ekranlar §3. Hiç hesap yapmaz;                     │
│  invoke() ile Rust komutlarını çağırır; sayı biçimlendirme ve SVG çizimi ön uçta.       │
└──────────────────────────────────────────────────────────────────────────────────────┘
        │ tauri::command (JSON)
┌──────────────────────────── Rust arka uç (src-tauri) ───────────────────────────────┐
│  commands/: config · models · predict · scenario · inputs_doc · freeze · scores · git  │
│  crates/borsai_predict: SAF predict (Tauri'siz; serde_json + num-bigint/num-rational)  │
│  Gömülü: models/*.json + INDEX.json (build.rs), isteğe bağlı scores.json anlık kopyası │
└──────────────────────────────────────────────────────────────────────────────────────┘
        │ std::process::Command (yalnız "repo modu"nda, ağ yok)
┌──────────────────────────── Python (repo içi .venv) ────────────────────────────────┐
│  python -m borsai.freeze  (resmi kayıt yazıcı, TEK)                                   │
│  python -c "... borsai.market20 ..."  (f6, pinli dosyalardan)                          │
│  python -c "... borsai.registry.inputs_pit_problems ..."  (girdi belgesi denetimi)     │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**[KARAR] Tauri 2.** Gerekçe: WebView'lü küçük ikili, Rust arka uç `cargo test` ile WebView'süz sınanabilir (AUDIT §3e), dosya ve süreç erişimi Rust'ta kalır. Ön uçta çerçeve yok: ekranlar form + tablo + iki basit SVG'dir; React/Svelte bağımlılığı bakım yükü ekler, kazanç yoktur. Grafik kütüphanesi yok: S_k eğrisi ve P(L = l) çubukları ön uçta ≤ 60 satırlık SVG üreticisiyle çizilir.

Tauri eklentileri: yalnız `tauri-plugin-dialog` (dosya seçici). Dosya G/Ç ve süreç çalıştırma Rust komutlarında (`std::fs`, `std::process`); `fs`/`shell` eklentileri kullanılmaz (yetenek yüzeyi küçük kalsın). Ön uç bağımlılıkları: `@tauri-apps/api`, `@tauri-apps/plugin-dialog`, geliştirme için `vite`, `typescript`, `vitest`.

### 1.2 `predict`'in tek gerçeklemesi: Rust [KARAR]

Seçenekler ve karar:

| Seçenek | Artı | Eksi | Karar |
|---|---|---|---|
| **Rust port** (`borsai_predict` crate) | Tek ikili, bağımlılık yok, `cargo test` ile parite, ileride ürünleşmeye uygun, WebView'süz test | İkinci gerçekleme: Python ile ayrışma riski (AUDIT §3e) | **SEÇİLDİ.** Ayrışma, Python'un ürettiği altın vektörlerle her `cargo test`'te sınanır (§1.3) |
| Python sidecar (PyInstaller/py2app ile gömülü CPython + `borsai/`) | Parite sorunu sıfır (aynı kod) | ~30–40 MB ek ikili, imzasız sidecar Gatekeeper'a takılır, `ROOT`/git bağımlı modüller uygulama paketinde anlamsız, ürünleşmede dağıtım ve güncelleme yükü | Reddedildi; ama **resmi kayıt yazıcı** için repo içi Python zaten çağrılıyor (§3e), bu "sidecar" değildir |
| WASM (Rust→wasm ya da Pyodide) | Tarayıcıda da çalışır | Pyodide ≥ 10 MB ve stdlib Decimal'i yavaş; Rust→wasm, Rust portunun üstüne ikinci derleme hedefi; masaüstünde gereksiz | Reddedildi; ileride web sürümü istenirse aynı Rust crate wasm'a derlenir (crate'i `no_std` uyumlu tutmak gerekmez, `wasm32-unknown-unknown` yeterli) |

Rust crate'in sınırı: Python'daki `borsai/predict.py`, `predict_hazard.py`, `predict_pb.py`, `predict_market20.py`, `features.py` (compute_features, compute_pb_features), `horizons.py`, `survival.py` (survival, p_streak, p_close, sigmoid) fonksiyonlarının birebir portu. **Port ETMEZ:** fit, backtest, market20 (f6 hesabı), registry, freeze, scoring. f6 hazır değer olarak gelir (SPEC_MARKET20_V0 §10 rol ayrımı; SPEC_DEVIATIONS B2).

Model türü ayrımı `borsai/freeze.py: model_kind` ile aynı [ÖLÇTÜM `freeze.py:119-133`]:

```
algorithm == "discrete_time_hazard_logit_l2"           -> hazard   (predict_hazard.predict)
algorithm in {"KM_EXPANDING", "KM_LAST10"}             -> km       (predict_hazard.predict; girdi okumaz)
algorithm == "V1_5_RIDGE_LOGIT" and "f6" in features   -> market20 (predict_market20.predict)
algorithm == "V1_5_RIDGE_LOGIT" and features pb*       -> pb       (predict_pb.predict)
algorithm == "V1_5_RIDGE_LOGIT"                        -> linear   (predict.predict)
else                                                   -> rule     (predict.predict; features boş, sabit kafalar)
```

Rust çıktı yapıları Python sözlükleriyle alan alan aynıdır (serde ile aynı anahtar adları): linear/pb/market20/rule için `{model_id, D1, D3, D5, D10: {return, return_unclipped, return_clipped, price, p_up, direction} | null, warnings[], refused | null, features? (pb), f6_market20? (market20)}`; hazard/km için `{model_id, hazard[10], S[10], P_L[11], P_close_ceiling[10], clipped, warnings[], refused | null}`. `warnings[i] = {code, message, ...ek alanlar}`; `refused = {code, field, reason}`. Rust `message` metnini Türkçe kendi üretir; parite `message`'ı karşılaştırmaz (§1.3).

### 1.3 Python ile parite yöntemi

**Altın vektörler.** `app/parity/gen_golden.py` (Python, repo `.venv` ile koşar; `borsai` paketini import eder; yalnız stdlib predict yolunu çağırır) her kayıtlı model için `app/parity/golden/<model_id>.jsonl` üretir. Satır biçimi:

```json
{"case_id": "v1_5_h99/0137", "model_id": "v1_5_h99", "params_sha256": "bf80…", "inputs": {...ham metin girdiler...},
 "extra": {"f6_market20": "-0.0924…" | null, "f6_market20_refusal": null | "STALE_S0"},
 "expected": {...Python çıktısı, alan alan...}, "tags": ["f3_missing"]}
```

Girdi üretim planı (model başına ≥ 200 satır; sayı `gen_golden.py`'de sabit, seed 20260922):
- 99 H99 eğitim satırı (`data/training_table.csv`'den yalnız GİRDİ sütunları; sonuç sütunları okunmaz) + 7 sicil girdisi (`registry/inputs/*.json`, `borsai.registry.model_inputs` ile).
- ≥ 60 rastgele geçerli girdi: fiyat 1–500 TL, pay 1e6–5e8, sermaye pay×(2…12), sermaye artırımı payı 0–%100, f3 0.3–60 (kırpma her iki yönde), ipo_size_tl bazen verilmiş bazen boş.
- Uç ve ret yolları (her biri en az 2 satır): her `INPUT_*` kodu (`INPUT_MISSING` her zorunlu alan için ayrı; `INPUT_NOT_NUMERIC` ("12,5", "abc", "inf", "nan"; not: "" ve "DATA_NOT_FOUND" eksik sayılır → `INPUT_MISSING`; "1e400" Python Decimal'de sonludur, ret değildir ve altın vektörde "sonlu ama binary64'e taşan" satır olarak yer alır); `INPUT_NOT_POSITIVE` fiyat/pay/sermaye/f3 ≤ 0; `INPUT_NEGATIVE`; `DIVISION_BY_ZERO` pay = 0 ve sermaye = 0; `INPUT_INCONSISTENT` iki yönü), `F3_MISSING`, `F3_FILTER_STATUS_CONFLICT` (yalnız f3_filter_mode açık olan bir model varsa; şu an yok → satır "beklenen: ret yok" olarak yine yazılır), `F4_ZERO_NO_TRAINING_EXAMPLE`, her özellik için `OUT_OF_TRAINING_RANGE` (alt ve üst), `F3_WINSORIZED` / `F3_CLIPPED_TO_TRAINING_P05_P95`, her ufuk için `RETURN_CLIPPED_TO_PHYSICAL_BOUND` UPPER ve LOWER (uç f3 ve f1 değerleriyle; Ridge katsayıları küçük olduğundan D1'de kırpma zor tetiklenir — üretici kırpma hedefine ulaşana kadar f3'ü artırır/azaltır ve ulaşamıyorsa bunu `golden/README.md`'ye yazar).
- market20: f6 ∈ eğitim aralığı içi/dışı, f6 = None ve her `MARKET20_<NEDEN>` kodu, f6 sayı değil.
- PB: 8 alanın her biri boş, "10-12"/"10–12"/"10—12" fiyat aralığı, ID-A/B/C ihlalleri, BASE/POST/VALUE_POSITIVE, PB2/PB3/PB4_RANGE, pb4 > 0, aralık dışı pb1/pb2/pb3, çok haneli girdiler (`precision` yolu).
- KM ve @INF: girdi yok; 1 satır yeterli ama 200 sayısı için girdiler değişik verilir (çıktı sabit kalmalı, bu da testtir).
- Kurallar (`base_*`): fiyat yok / ≤ 0 → ret; fiyat dolu → sabit çıktılar.

**Karşılaştırma (`cargo test -p borsai_predict --test golden`).** Her satır için Rust `predict` çağrılır ve:
- `refused`: `code` ve `field` birebir eşit (ikisi de null ya da ikisi de aynı). Ret varsa çıktı alanlarının hepsi null (Python'daki gibi).
- `warnings`: `(code, feature|horizon)` çok kümesi eşit; sıra karşılaştırılmaz; `message` karşılaştırılmaz; `value/used/train_min/train_max` sayısal alanları |Δ| ≤ 1e-9.
- Her sayısal çıktı (`return`, `return_unclipped`, `price`, `p_up`, `hazard[i]`, `S[k]`, `P_L[l]`, `P_close_ceiling[k]`, `f6_market20`, `features.pb*`): **|Δ| ≤ 1e-9** (mutlak). null ↔ null.
- `direction`, `return_clipped`, `clipped`: birebir.
- Ek istatistik: test, model başına maks |Δ| ve bit-eşit satır oranını `target/parity_report.json`'a yazar; rapor §7 kabul kapısında alıntılanır.

**Sayısal alan kararları [KARAR]** (Python davranışı [ÖLÇTÜM `borsai/features.py`, `predict.py`; bu oturumda .venv'de doğrulandı]):

| Konu | Python | Rust'ta nasıl | Beklenen Δ |
|---|---|---|---|
| Girdi ayrıştırma | `Decimal(str(value).strip())`; boş/None/`DATA_NOT_FOUND` eksik; sonlu değilse `INPUT_NOT_NUMERIC` | Metinden kesin rasyonel (`num-rational::BigRational`); aynı eksiklik ve sonluluk kuralları; `Decimal` sözdizimi (öncü `+`/`-`, `E` üs, `1e400` → sonsuz değil, Python'da `Decimal('1e400')` sonludur, kabul) | 0 |
| f1 = pay × fiyat (size verilmemişse) | 28 anlamlı hane, ROUND_HALF_EVEN bağlamı | Kesin çarpım; 28 anlamlı haneyi aşarsa HALF_EVEN yuvarla (`dec::round_sig(x, 28)`) | 0 |
| f2, f4 (`_pct`) | 28 hanede `num/den`, ×100, 10 ondalığa ROUND_HALF_UP, sondaki sıfırlar atılır | `q = round_sig(num/den, 28, HALF_EVEN)`; `raw = q × 100` (kesin); `round_places(raw, 10, HALF_UP)` | 0 |
| Decimal → binary64 | `float(Decimal)` doğru yuvarlanmış | Ondalık metne yaz → `str::parse::<f64>()` (Rust std doğru yuvarlar). `to_f64()` benzeri kısa yollar YASAK | 0 |
| pb2, pb3, pb4 | `int / int` (doğru yuvarlanmış) | Pay ve payda `< 2^53` ise `n as f64 / d as f64` (IEEE bölme doğru yuvarlar → bit-eşit); değilse BigInt ile 55+ bitlik bölüm + kalanla HALF_EVEN | 0 |
| pb1 | 60 haneli `Decimal.ln()` → float | Kesin çarpım → binary64 (doğru yuvarlanmış) → `f64::ln` | ≤ 5e-15 (ln argümanının 1 ulp'si ve libm) |
| Doğrusal terim `sum(c·z) + b` | CPython 3.12 `sum()` **Neumaier telafili** toplama [ÖLÇTÜM: `sum([1e16, 1.0, -1e16]) == 1.0`] | Aynı algoritma (aşağıda) | 0 |
| `exp`, `log` | C libm (`math.exp`, `math.log`) | `f64::exp`, `f64::ln` → aynı makinede Apple libm | 0 beklenir; garanti yok, tolerans içinde |
| Fiziksel sınırlar | `float(Decimal("0.9")**h − 1)` | Sabitler metinden parse: D1 [−0.1, 0.1], D3 [−0.271, 0.331], D5 [−0.40951, 0.61051], D10 [−0.6513215599, 1.5937424601] [ÖLÇTÜM] | 0 |
| Ufuk sırası | JSON anahtar sırası (dosya `sort_keys` ile yazılmış: D1, D10, D3, D5) | `serde_json` `preserve_order` özelliği ile aynı sıra; uyarı listesi sırası da böyle oluşur (parite sırayı zaten karşılaştırmaz) | — |

CPython `sum()` float yolu (birebir port edilecek; `bltinmodule.c`):
```
f = 0.0; c = 0.0
for x in items:
    t = f + x
    if |f| >= |x|: c += (f - t) + x
    else:          c += (x - t) + f
    f = t
if c != 0 and c sonlu: f += c
return f
```
Hazard'daki `lin = sum(beta[c]·z[c])` ve `head_values`'daki `sum(...) + intercept` bu fonksiyonla; `survival` (ardışık çarpım), `p_streak` (çıkarma), `p_close` doğrudan ifadeyle.

**Tolerans neden 1e-9:** SPEC_SCORING §6 parite denetimi ve AUDIT §3e aynı sayıyı verir; JSON'daki μ, σ, p05/p95 binary64 olduğundan 1e-12'lik Python↔sklearn paritesinden daha gevşek olmak zorunda değildir, ama libm/toplama farkları için pay bırakılır. Rapor maks |Δ|'yı yazar; beklenti < 1e-12.

### 1.4 Gömme ve doğrulama

- `build.rs`: `models/INDEX.json`'u okur, listedeki her dosyayı `OUT_DIR/embedded.rs` içine `include_str!` ile gömer (INDEX'te olmayan dosya gömülmez; INDEX'te olup diskte olmayan dosya derlemeyi kırar). `scores/scores.json` varsa aynı yolla gömülür, yoksa `None`. Derleme anındaki `git rev-parse HEAD` ve `git status --porcelain -- models scores` çıktısı `build_info` olarak gömülür (uygulama "Hakkında" ekranında görünür).
- Açılışta (`models::verify`): her gömülü dosyanın sha256'sı INDEX'teki `sha256` ile ve INDEX'in kendi sha256'sı `build_info.index_sha256` ile karşılaştırılır. Tek uyuşmazlıkta durum `INTEGRITY_FAILED`: tahmin komutları hata döner, arayüz kırmızı bant gösterir ("Gömülü model dosyası INDEX ile uyuşmuyor: <model_id>"). Kısmi çalışma yok.
- Her tahmin çıktısı (senaryo ve resmi) `params_sha256` taşır; arayüzde model kartında ilk 8 hane görünür (SPEC_SCORING §8).

---

## 2. Veri sözleşmeleri

| Belge | Şema | Kaynak | Uygulamada |
|---|---|---|---|
| Model parametreleri | `borsai.model/1` | `models/<file>` (INDEX üzerinden) | Gömülü, salt okunur, sha doğrulamalı (§1.4) |
| Model dizini | `borsai.model_index/1` | `models/INDEX.json` | Gömülü; model listesi buradan (yeni model = yeniden derleme, §8) |
| Girdi belgesi | `borsai.inputs/1` | `registry/inputs/<T>.json` | Uygulama YAZAR (dondur akışı) ve OKUR (resmi kaydı gösterirken) |
| Tahmin kaydı | `borsai.record/1` | `registry/records/<T>/<UTC>_<sha12>.json` | Yalnız OKUR (Python yazar) |
| İptal kaydı | `borsai.record/1`, `record_type = CANCELLATION` | aynı dizin | Yalnız OKUR; iptali Python'a yaptırır |
| Skorlar | `borsai.scores/1` | `scores/scores.json` | Yalnız OKUR (repo yolu ya da gömülü anlık kopya) |
| Payda | CSV, `registry/ipos.csv` | | Yalnız OKUR (atlanan sayısı, listeleme) |
| Push kanıtı | `borsai.push_proof/1` | `registry/push_proofs/<sha>.json` | Yalnız OKUR (kayıt için "zaman kanıtı var/yok" göstergesi) |
| Gözlenen sonuç (tavan şeridi) | CSV, `data/outcomes/<T>.csv` (Faz 2B üretir; sütunlar FAZ2B adım 1: `session_date, …, ceiling_close, …, status`) | Faz 2B | Yalnız OKUR (§3g); uygulama bu dizine hiçbir zaman yazmaz |
| Kişisel kayıt | `borsai.app_scenario/1` | uygulama verisi (§2.4) | Uygulama yazar/siler/dışa aktarır |
| Uygulama ayarı | `borsai.app_config/1` | uygulama verisi `config.json` | repo_root, python_path, scores_source |

### 2.1 Model JSON'ları (gömülü, salt okunur)

Okunan alanlar (Python predict'in okuduklarıyla aynı): `schema_version`, `model_id`, `algorithm`, `features`, `horizons.{D1,D3,D5,D10}.{return,p_up}` (`kind` ∈ constant | ridge | logit; `value` | `coef[]`, `columns[]`, `intercept`), `preprocessing.{columns, medians, winsor.f3.{p05,p95}, log_transform, mean, std, f3_filter_mode}`, `input_policy.{f3_missing, f3_filter_status_conflict}`, `feature_ranges.<f>.{min,max}`, hazard için `gamma[3]`, `beta{}`, `day_groups`, `reclose_rates.{r_a,r_b}`, KM için `survival.hazard[10]`. Başka alan okunmaz; bilinmeyen alan yok sayılır. `_check_params` denetimleri (`PARAMS_INVALID`, `SCHEMA_UNSUPPORTED`) Rust'ta da vardır ve gömülü dosyalarda derleme testinde koşar (U33): açılışta PARAMS_INVALID çıkması `INTEGRITY_FAILED` sayılır.

### 2.2 Girdi belgesi (`borsai.inputs/1`)

Yapı [ÖLÇTÜM `borsai/registry.py:132-202`, `registry/inputs/NETGL.json`, `VEYAS.json`]:
- Üst düzey: `schema_version`, `ticker`, `company`, `stage`, `collected_at` (ISO, +03:00), `collected_at_basis = "LOCAL_CLOCK_SELF_REPORTED"`, `collection_rules[]`, `first_trading_date_source`, `fields{}`, `sources{}`.
- `fields`: 20 alan, hepsi bulunmak ZORUNDA (`INPUT_FIELDS` = 9 V1.5 + 8 PB + 3 tarih). Dolu alan: `value` (**metin**), `source_id`, `source_document`, `source_published_at` (ISO + saat dilimi), `source_sha256`, `source_path`, `quote`; isteğe bağlı `cross_checks[]`, `locator`; f3 için `origin ∈ {SOURCE_REPORTED, SOURCE_REPORTED_APPROX, CALCULATED_FROM_SOURCE_TOTALS, CALCULATED_FROM_PRIMARY_TOTALS}`; filtre durumu `∈ {NOT_SPECIFIED, UNFILTERED, FILTERED}`. Boş alan: `value: null`, `missing_reason` (zorunlu), isteğe bağlı `checked_sources[]`, `evidence[]`.
- `sources[source_id] = {kind ∈ {KAP_NOTIFICATION_PDF, KAP_ATTACHMENT_PDF, SPK_BULLETIN}, document_id, published_at, sha256, path}`; alanın `source_published_at/sha256/path` değerleri kaynak tablosuyla birebir aynı olmalı.
- `stage ∈ {PRE_BOOKBUILD, POST_BOOKBUILD_PRE_LISTING}` [KARAR; mevcut kayıtlarda ikincisi kullanılıyor].

Uygulama belgeyi yazarken Rust'ta yapısal denetimi (`validate_inputs` portu) yapar, ardından **yetkili denetim** olarak Python'u çağırır (§3e adım 4). İki denetim de geçmeden dondur düğmesi açılmaz.

### 2.3 Skorlar (`borsai.scores/1`, yalnız okunur)

Şema FAZ2B görev dosyası adım 2'dekidir; alan eklenebilir, kaldırılamaz. Uygulamanın okuduğu alanlar: `schema_version`, `generated_at_utc`, `as_of_session`, `code`, `inputs.models_index_sha256`, `models[].{model_id, kind, card{training_n, training_cutoff, params_sha256_8, n_variants_same_data}, primary_cell, backtest{title, cells[]}, live{title, n_live, n_late, n_scored, n_refused, n_skipped, n_target_unavailable, n_pending, rows[], cells[], self_reported_rows[]}}`, `skipped[]`, `retro_info[]`. Hücre: `{output, horizon_or_k, metric, model_value, rule_id, rule_value, diff, ci95 | null, n, wins, losses, ties, verdict}`; `verdict ∈ {"geçiyor", "geçemiyor", "ayırt edilemiyor", "yetersiz örnek", "aralık için yetersiz", null}`. Koşullu skorlar (EK 1) ayrı, isteğe bağlı blokta gelir: `models[].conditional` (tanım Faz 4 şartnamesi §7, `docs/specs_faz4/`); uygulama bu bloğu koşulsuz tablodan ayrı bir bölümde gösterir, yoksa "henüz koşullu skor yok" yazar (§3g).

Kaynak seçimi (`scores_source`): `REPO` (= `<repo_root>/scores/scores.json`, varsayılan repo modunda) ya da `EMBEDDED` (derlemeye gömülü anlık kopya). Panelin başlığında hangisi olduğu, `generated_at_utc`, `as_of_session` ve dosya sha256'sının ilk 12 hanesi yazılır. `inputs.models_index_sha256` gömülü INDEX sha'sından farklıysa sarı uyarı: "skorlar farklı bir model dizini için üretilmiş".

**Bütünlük denetimi (fail-closed):** uygulama dosyayı olduğu gibi gösterir ama SPEC_SCORING §8 ile çelişen içeriği reddeder (U24): `live.n_scored < 10` iken `live.cells` boş değilse; `verdict = "geçiyor"/"geçemiyor"` iken `n < 30` ya da `ci95` null ya da `ci95` 0'ı içeriyorsa; `verdict = "ayırt edilemiyor"` iken `ci95` 0'ı dışlıyorsa; `n_live + n_late ≠ n_scored` ise. Bu durumda panel yerine "scores.json şartname kuralına aykırı: <kural>" gösterilir. Uygulama hiçbir hücreyi kendisi hesaplamaz, düzeltmez, doldurmaz.

### 2.4 Kişisel kayıtlar (`borsai.app_scenario/1`)

Yol: `<app_data_dir>/scenarios/<ULID>.json`; macOS'ta `~/Library/Application Support/<identifier>/` (Tauri `app_data_dir`). `identifier = "tr.borsai.app"` [KARAR].

```json
{"schema_version": "borsai.app_scenario/1", "official": false, "scenario_id": "<ULID>", "title": "…",
 "created_at_local": "2026-10-01T10:00:00+03:00", "app_version": "0.1.0", "build_git_head": "…",
 "stage": "PRE_BOOKBUILD" | "POST_BOOKBUILD_PRE_LISTING", "ticker_label": "serbest metin (isteğe bağlı)",
 "inputs": {…model_inputs düz sözlüğü, metin değerler…},
 "f6": {"value": "…" | null, "refusal": null | "…", "origin": "REPO_PYTHON" | "MANUAL" | "NONE", "S0_date": …, "S20_date": …, "xu100_sha256": …},
 "models_index_sha256": "…", "outputs": {"<model_id>": {"params_sha256": "…", "output": {…}}}}
```
Kurallar: `record_type` anahtarı YOKTUR (Python `active_records` yalnız `record_type == PREDICTION` sayar; bu dosya kazara sicil dizinine düşse bile skorlanamaz); `schema_version` sicilinkinden farklıdır; `official: false` sabittir. Dosya yalnız uygulama verisine yazılır; hedef yol `repo_root` altındaysa yazma reddedilir (U27). Silinebilir; dışa aktarma kullanıcı seçtiği yola aynı içeriği kopyalar (repo altına dışa aktarma da reddedilir).

### 2.5 Şema sürümleri: uyumsuzlukta davranış [KARAR]

| Belge | Desteklenen | Uyumsuzsa |
|---|---|---|
| model / model_index | tam `borsai.model/1`, `borsai.model_index/1` | `INTEGRITY_FAILED`: tahmin kapalı, bant mesajı; derleme testi (U33) zaten kırmızı |
| inputs | `borsai.inputs/1` | Uygulama başka sürüm YAZMAZ; okurken farklı sürüm → "desteklenmeyen girdi belgesi sürümü" ve kayıt görüntüleme kapalı |
| record | `borsai.record/1` | Kayıt listede "okunamıyor (sürüm X)" satırı olarak durur; içerik gösterilmez |
| scores | `borsai.scores/1` | Doğruluk paneli kapalı, mesaj: "scores.json sürümü X; uygulama 1'i destekler. Uygulamayı güncelleyin." Kısmi gösterim yok |
| app_scenario | `borsai.app_scenario/1` | Dosya listede "eski sürüm" etiketiyle; açılmaz, silinebilir, dışa aktarılabilir |
| app_config | `borsai.app_config/1` | Varsayılanlara dön, eski dosyayı `config.json.bak` olarak sakla |

Sürüm karşılaştırması tam metin eşitliğidir; "1.x" tahmini yapılmaz.

---

## 3. Ekranlar ve akışlar

Genel çerçeve: sol gezinme (Girdi · Sonuç · Doğruluk · Sicil · Kişisel kayıtlar · Ayarlar · Hakkında). Üstte **mod bandı**: `SENARYO` (turuncu, "Bu tahmin sicile girmez") ya da `RESMİ KAYIT` (mavi, kayıt dosya adı ve zaman kanıtı durumu). Altta sabit tek satır: `Bu uygulama yatırım tavsiyesi değildir; çıktılar istatistiksel tahmin ve olasılıklardır.` (§4). Repo modu göstergesi: Ayarlar'da `repo_root` doğrulanmışsa yeşil "Repo modu: <yol>", değilse gri "Bağımsız mod (dondur ve doğruluk paneli repo ister)".

Boş ve hata hâlleri her ekranda üç sınıftır: **boş** (veri yok; ne yapılacağı yazılı), **kapalı** (ön koşul yok: repo modu, bütünlük, sürüm), **hata** (işlem başarısız; ham stderr açılır kutuda). Hiçbir ekran sessizce boş kalmaz.

### 3a. Girdi formu

**Aşama seçici:** `Talep toplama ÖNCESİ (PB)` / `Talep toplama SONRASI, listeleme öncesi`. Aşama, hangi alanların zorunlu olduğunu ve boş alanların `missing_reason` ön metnini belirler; hiçbir model davranışını değiştirmez (f3 boşsa f3 isteyen modeller her aşamada RET eder).

**Alan listesi.** Birim: pay adetleri nominal 1 TL pay (adet = TL nominal); fiyatlar TL; oranlar sayı. Değerler metin olarak saklanır (binlik ayırıcı yok, ondalık nokta; form virgülü noktaya çevirir ve bunu gösterir). "Kaynak ipucu" resmi belgenin adıdır; ikincil kaynak yasaktır (CLAUDE.md).

| # | Alan (`fields.<ad>`) | Tanım | Kaynak ipucu | PB | Sonrası | Kullanan |
|---|---|---|---|---|---|---|
| 1 | `ipo_price_tl` | Resmi kesin halka arz fiyatı, TL | KAP "Halka Arz Sonuçları" (aracı kurum bildirimi) "HALKA ARZ FİYATI"; çapraz: BIST "Payların İşlem Görmeye Başlaması" baz fiyat | isteğe bağlı (sabit fiyatlı arzda SPK bülteni fiyatı; fiyat aralıklıysa boş) | zorunlu | V1.5 ailesi, kurallar (fiyat çıktısı), tavan modeli |
| 2 | `shares_offered` | Satışa sunulan (dağıtılan) toplam pay adedi; ek satış KULLANILDIYSA dahil (DATA_NOTES §4: 6 arzda böyle; form bunu `additional_sale_shares` ile açık yazar) | KAP "Halka Arz Sonuçları" "SATIŞA SUNULAN PAY ADEDİ" | boş (`missing_reason`: "nihai dağıtım yok") | zorunlu | f1 (size yoksa), f2, f4 |
| 3 | `post_ipo_share_capital` | Arz sonrası ödenmiş sermaye (pay adedi) | BIST "Payların İşlem Görmeye Başlaması" ("sermayesini temsil eden … payları"); çapraz SPK bülteni "Yeni Sermaye" | isteğe bağlı (SPK bülteni planlanan) | zorunlu | f2 |
| 4 | `capital_increase_shares` | Sermaye artırımı yoluyla satılan pay adedi | Sonuç bildirimi ayrımı basmıyorsa SPK bülteni "Bedelli" sütunu; taşıma ancak DATA_NOTES §2'nin üç koşuluyla (form onay kutusu + `locator`) | isteğe bağlı | zorunlu | f4 |
| 5 | `existing_share_sale_shares` | Ortak satışı yoluyla dağıtılan pay adedi | KAP sonuç eki | boş | zorunlu (belgede yoksa boş + neden) | yalnız tutarlılık denetimi (2 = 4 + 5 [+ ek satış]) |
| 6 | `additional_sale_shares` | Kullanılan ek satış pay adedi (0 olabilir) | KAP sonuç eki; SPK bülteni "Ek Pay Satışı" '-' ise 0 | boş | zorunlu (0 dahil) | tutarlılık denetimi |
| 7 | `total_demand_multiple` | **f3, toplam talep katı** — tanım §3a.1 | KAP "Halka Arz Sonuçları" eki ("toplamda X katı talep") | boş (`missing_reason`: "talep toplama yapılmadı") | zorunlu değil ama boşsa f3 isteyen 4 model RET | f3 |
| 8 | `total_demand_filter_status` | f3'ün filtre durumu: belge "mükerrer talepler ayıklanmış/filtrelenmiş" diyorsa `FILTERED`, "filtrelenmemiş" diyorsa `UNFILTERED`, ifade yoksa `NOT_SPECIFIED` | aynı belge | boş | f3 doluysa zorunlu | f3 filtre çakışması denetimi |
| 9 | `ipo_size_tl` | Kaynakta bildirilen halka arz büyüklüğü, TL (f1 kaynağı; verilmezse f1 = fiyat × pay) | KAP sonuç bildirimi "HALKA ARZ BÜYÜKLÜĞÜ (TL)" | boş | isteğe bağlı | f1 |
| 10 | `ipo_price_try` | SPK onaylı **planlanan** fiyat (tek değer; aralık ise "10-12" biçiminde metin → PB modelleri `PB_PRICE_RANGE` ile RET) | SPK haftalık bülteni A.1 "İlk Halka Arzlar" tablosu "Satış Fiyatı" | zorunlu | zorunlu | pb1 |
| 11 | `planned_pre_ipo_capital` | Mevcut sermaye | SPK bülteni tablosu "Mevcut Sermaye" | zorunlu | zorunlu | ID-A |
| 12 | `planned_post_ipo_capital` | Yeni sermaye | "Yeni Sermaye" | zorunlu | zorunlu | pb2, ID-A |
| 13 | `planned_capital_increase_shares` | Bedelli (sermaye artırımı) | "Bedelli" | zorunlu | zorunlu | pb3, ID-A/B |
| 14 | `planned_existing_share_sale` | Mevcut pay satışı ('-' = 0) | "Mevcut Pay Satışı" | zorunlu | zorunlu | ID-B |
| 15 | `planned_base_offer_shares` | Taban arz = 13 + 14 (H99 PB tanımı; belgede açıkça yazan toplamla çapraz denetim) | tablo + KAP sonuç eki toplamı | zorunlu | zorunlu | pb1, pb2, pb3, ID-B/C |
| 16 | `planned_additional_sale_ceiling` | Ek pay satışı tavanı ('-' = 0) | "Ek Pay Satışı" | zorunlu | zorunlu | pb4 (uyarı), ID-C |
| 17 | `planned_max_offer_shares` | Azami arz = 15 + 16 | türetilmiş ama tabloya yazılır; form 15 + 16'yı önerir, kullanıcı onaylar | zorunlu | zorunlu | ID-C |
| 18 | `first_trading_date` | İlk işlem günü T (ISO) | BIST "Payların İşlem Görmeye Başlaması" bildirimi | boş ya da beklenen tarih | zorunlu | f6 kural 5, dondur "ilk işlem gününden önce" uyarısı, iptal sınırı |
| 19 | `bookbuilding_start` | İlk talep toplama günü B | BIST bildirimi "Halka Arz Tarihi"; SPK bülteni | zorunlu (varsa) | zorunlu | `pb_after_bookbuild_start` (SPEC_SCORING §6) |
| 20 | `bookbuilding_end` | Son talep toplama günü | aynı | isteğe bağlı | zorunlu | bilgi |
| — | `f6_market20` (belgeye YAZILMAZ) | XU100 20 seans getirisi; §3a.2 | pinli XU100 + takvim (repo) | senaryo | senaryo | `v1_5_market20_v0` |

Form denetimleri (anında, Rust `validate_inputs` portu + özellik ön denetimi): sayı biçimi; 2 ≥ 4, 2 ≤ 3, 4 ≥ 0; `2 = 4 + 5 + 6` tutmuyorsa sarı uyarı (RET değil; DATA_NOTES §4); PB özdeşlikleri ID-A/B/C (tutmuyorsa kırmızı: PB modelleri RET edecek, dondurulabilir ama görünür). Uyarılar alanın yanında, kod adıyla.

Her dolu alanın yanında **kaynak kutusu**: kaynak seçici (`sources` tablosundan), `quote` (belgeden aynen alıntı, zorunlu), `locator` (isteğe bağlı), `cross_checks` ekle. Kaynak tablosu ekranın altında: belge ekle → dosya seçici (PDF) → uygulama sha256 hesaplar, `kind`, `document_id`, `published_at` (kullanıcı belgeden okur; KAP bildirim PDF başlığındaki "KAP'ta yayınlanma tarihi ve saati") girilir; dosya dondur akışında `registry/source_docs/<T>/` altına kopyalanır (§3e). Senaryo modunda kaynak kutuları isteğe bağlıdır ve gri "senaryo: kaynak gerekmez" etiketi taşır.

**Durumlar:** boş form (aşama seçilmemiş → alanlar kapalı); doldurma; "Tahmin et" (senaryo) düğmesi her zaman açık (RET'ler sonuç ekranında görünür); "Resmi kayıt için hazırla" yalnız repo modunda ve zorunlu alan + kaynak kutuları tamamsa açık. Hata: dosya okunamadı, sha hesaplanamadı (mesaj + yeniden dene).

#### 3a.1 f3'ün tam tanımı [KARAR; DATA_NOTES §5'teki karışıklığa uygulama tarafı cevabı]

`total_demand_multiple` = **toplam talep / taban arz**, burada:
- pay (numerator): resmi sonuç belgesinde bildirilen **toplam talep** (tüm yatırımcı grupları, ek satış öncesi/sonrası ayrımı belgede neyse o; belge "mükerrer/filtrelenmiş" demiyorsa filtre durumu `NOT_SPECIFIED`);
- payda: **satışa sunulan taban pay adedi** (ek satış tavanı HARİÇ, `planned_base_offer_shares` ile aynı büyüklük). Belge ek satış dahil paydayla kat veriyorsa `locator`'a "payda ek satış dahil" yazılır, değer yine belgedeki gibi alınır (dönüştürme yok).
- Köken sırası: (1) belge katı açıkça yazıyorsa `SOURCE_REPORTED` (metin "yaklaşık/~" diyorsa `SOURCE_REPORTED_APPROX`); (2) belge katı yazmıyor ama toplam talep adedini ve taban arzı açıkça veriyorsa form `talep / taban` bölmesini önerir, kullanıcı onaylarsa `CALCULATED_FROM_SOURCE_TOTALS` ve `quote` iki sayıyı da içerir; (3) talep dağıtıma eşit basılmış, planlanandan az satılmış ya da yalnız grup bazlı talepler varsa **f3 boş**, `missing_reason` yazılır (VEYAS kararıyla aynı; kat türetilmez). `CALCULATED_FROM_PRIMARY_TOTALS` yalnız izahname/fiyat tespit raporundaki toplamlardan hesaplanan legacy vakalar içindir; uygulama bu kökeni üretmez.
- Uygulama f3'ü asla başka bir alandan türetmez, ortalama almaz, yuvarlamaz. Tanım metni formda alanın yanında görünür; `collection_rules` dizisine aynen yazılır.
Bu tanım H99'daki çoğunluk uygulamasıyla (SOURCE_REPORTED 71/97 [ÖLÇTÜM DATA_NOTES §5]) uyumludur; proje sahibinin onayı açık soru 1'dedir.

#### 3a.2 XU100 f6: ağ yok [KARAR]

- Uygulama hiçbir koşulda ağa çıkmaz (Tauri `http` eklentisi yok; Rust'ta `reqwest`/`ureq` bağımlılığı yok; U34 bunu `Cargo.lock` ve `package-lock.json` taramasıyla sınar).
- **Repo modunda** senaryo f6'sı Python'dan alınır (pinli XU100 dosyası ve takvim B + uzatması; SPEC_MARKET20_V0 §2–§4, `borsai/market20.py: load_live_sources`). Komut (Rust `std::process::Command`, cwd = repo_root, ağ yok):
  ```
  <python> -c "import json,sys; from borsai import market20 as m; cal,recs,sha=m.load_live_sources(); t=sys.argv[2] or None; r=m.market20(sys.argv[1],cal,recs,xu100_sha256=sha,live=bool(t),first_trading_date=t); print(json.dumps(r.as_record()))" <ref_date> <first_trading_date|"">
  ```
  `ref_date` = bugünün Europe/Istanbul tarihi (uygulama UTC+3 sabit alır; Türkiye'de yaz saati yok). T boşsa `live=False` ile yalnız pencere hesaplanır ve arayüz "T bilinmiyor; kural 5 denetlenemedi" yazar. Çıktıdaki `refusal` doluysa `v1_5_market20_v0` o kodla RET eder ve arayüz nedenini açıklar (`STALE_S0`: "pinli XU100 dosyası bayat; SPEC_MARKET20_V0 §4 prosedürüyle Python tarafında güncellenmeli"; `CALENDAR_NOT_COVERING`: "takvim uzatması bitti"). Uygulama XU100 indirmez, güncellemez.
- **Bağımsız modda** ya da kullanıcı isterse: `f6` elle girilir; kutunun yanında "elle girildi (senaryo)" etiketi ve S0/S20 tarihleri boş. Boş bırakılırsa `MARKET20_NOT_PROVIDED` ile RET.
- Resmi kayıtta f6'yı `borsai.freeze` kendisi hesaplar (`market20_for_record`); formdaki değer belgeye yazılmaz ve kayda etkisi yoktur; form bunu açıkça söyler.

### 3b. Sonuç ekranı

Girdi formundan "Tahmin et" ile gelinir; Rust `predict_all` bütün INDEX modellerini aynı girdiyle çalıştırır (16 sütun). Üstte mod bandı (§3). Sağ üstte **model seçici**: her model için onay kutusu (varsayılan: hepsi açık); gizleme yalnız görünümü etkiler, kişisel kayıtta ve resmi kayıtta bütün modeller vardır (kural 1). Sütun grupları:

**Grup A — getiri ve olasılık (10 model):** `v1_5_h99`, `v1_6_h99`, `v1_5_market20_v0`, `pb_v0`, `base_always_ceiling`, `base_train_median`, `base_train_mean`, `base_zero`, `base_rate`, `base_last10_rate`. Satırlar D1, D3, D5, D10; her hücrede:
- getiri **%** (1 ondalık, işaretli: `+%7.7`) ve **fiyat** TL (2 ondalık: `27.48 TL`); fiyat = arz fiyatı × (1 + kırpılmış getiri) — Python `price` alanı, yeniden hesaplanmaz;
- kırpıldıysa hücre işareti `⌐` ve tooltip "fiziksel sınıra kırpıldı; ham değer +%12.3" (`return_unclipped`);
- `p_up` = **P(kapanış > arz)** yüzde, 0 ondalık (`%91`); yön `↑/↓` (`direction`, yalnız p_up varsa);
- kural sütunlarında olmayan çıktı (`base_train_median` p_up yok, `base_rate` getiri yok) "—";
- `base_always_ceiling` fiyatı "yaklaşık" etiketiyle (fiyat adımı yuvarlaması yok; AUDIT §3e).
- Nokta tahminin altında düz metin: "backtest tipik hata (n = 89): MAE 3.0 puan" — değer `scores.json`'daki modelin o ufuktaki MAE hücresinden (`model_value`), dosya yoksa satır yok. "Tahmin aralığı" sözü hiçbir yerde kullanılmaz (AUDIT §3d).

**Grup B — tavan serisi (7 sütun):** `ceiling_hazard_v0`, `ceiling_hazard_v0@INF`, `pb_ceiling_v0`, `pb_ceiling_v0@INF`, `base_km_expanding`, `base_km_last10`, `her zaman tavan` (S_k ≡ 1, tanım gereği; SPEC_DEVIATIONS C4; model çıktısı değil, sabit satır, gri). Öğeler:
- **S_k tablosu ve eğrisi:** k = 1..10, `S[k]` yüzde 0 ondalık; SVG çizgi grafiği (x = k, y = S_k, 0–1), seçili modeller üst üste, renk = sütun rengi. Eksen başlığı: "P(seri ≥ k gün)".
- **P(L = k):** l = 0..10 çubuk grafiği (`P_L`), başlık "Tavan k'ıncı günden sonra bozulur: P(L = k)"; l = 0 "hiç tavan yok", l = 10 "10 gün boyunca tavan (sağdan sansürlü)". Toplamın 1 olduğu tooltip'te.
- **Beklenen L** = Σ_l l·P_L[l] (1 ondalık, "gün"); **medyan L** = en küçük l ile Σ_{j≤l} P_L[j] ≥ 0.5. İkisi de görüntüleme türevidir; hücre tooltip'i formülü yazar; kayıtlara YAZILMAZ (model çıktısı değildir).
- **P_close_ceiling[k]:** k = 1..10, "P(Dk'de tavan kapanışı)" başlığı ve "ikincil, türetilmiş (SPEC_CEILING_V0 §8)" notu.
- Bilgi satırı (SPEC_CEILING_V0 §8'in izin verdiği tek eşleme): "seri k gün sürerse kapanış ≈ arz fiyatı × 1.1^k (fiyat adımı yuvarlaması nedeniyle yaklaşık)"; k = 1, 3, 5, 10 için TL değerleri, "≈" ile.
- Hazard'lar `hazard[d]` katlanabilir satırda.

**Ret hücreleri:** ret eden model sütununda bütün hücreler yerine tek blok: `RET · <kod>` + alan + Türkçe neden (tablo T-2, §3b.1). Sütun kaybolmaz, sayı gösterilmez. f3 boşken 4 model RET, PB sütunları dolu — bu SPEC_PB_V0 §8-8'in istediği görünümdür.

**Uyarılar:** sütun başlığı altında sarı rozet sayısı; tıklayınca liste. Kodlar ve metinleri T-2. Kırpma uyarısı ayrıca hücreye işlenir. Uyarı hiçbir hücreyi gizlemez.

**Model kartı** (her sütun başlığında, tıklayınca): `model_id`, "ne yapar" (INDEX/`description`), eğitim n ve kesim tarihi, `params_sha256` ilk 8, `experiments/log.jsonl`'daki aynı veri sürümünde denenen varyant sayısı (`scores.json card.n_variants_same_data`; dosya yoksa "—"), önceden ilan edilmiş birincil hücre, prospektif hüküm durumu ("canlı n = k: hüküm yok" ya da scores verdict'i).

**Rejim uyarısı** (sonuç ve doğruluk ekranlarında, gri kutu, sabit metin): "Modeller 2023-09-22…2026-08-06 arasında listelenen 99 arzla eğitildi (kesim 2026-08-19). D1 tavan oranı yıllara göre %95 → %82 → %67 → %83 değişti (AUDIT §2.4); bugünkü rejim eğitim dönemine benzemeyebilir. Girdi eğitim aralığı dışındaysa sütun uyarı taşır."

Durumlar: boş (girdi yok → "Girdi formuna gidin"); bütünlük hatası (§1.4 → tahmin yok); kısmi (bazı modeller RET → normal görünüm). Senaryo çıktısı "Kişisel kayıt olarak sakla" düğmesiyle §3f'ye; resmi hazırlık "Dondur akışına geç" ile §3e'ye.

#### 3b.1 Ret ve uyarı kodları (T-2; Python sabitleriyle birebir [ÖLÇTÜM])

| Kod | Kaynak | `field` | Arayüz metni (Türkçe) |
|---|---|---|---|
| `INPUT_MISSING` | features | alan adı | "<alan> boş; bu model bu alansız tahmin vermez" |
| `INPUT_NOT_NUMERIC` | features | alan | "<alan> sayı değil" |
| `INPUT_NOT_POSITIVE` | features | alan | "<alan> pozitif olmalı" |
| `INPUT_NEGATIVE` | features | capital_increase_shares | "sermaye artırımı payı negatif olamaz" |
| `DIVISION_BY_ZERO` | features | shares_offered / post_ipo_share_capital | "payda sıfır" |
| `INPUT_INCONSISTENT` | features | capital_increase_shares / shares_offered | "sermaye artırımı payı satılan paydan büyük" / "satılan pay arz sonrası sermayeden büyük" |
| `F3_MISSING` | predict, predict_hazard | total_demand_multiple | "Toplam talep katı (f3) yok; bu model f3'süz tahmin vermez. f3'süz tahmin PB sütunlarındadır." |
| `F3_FILTER_STATUS_CONFLICT` | predict | total_demand_filter_status | "f3 filtre durumu eğitimdekiyle çelişiyor" |
| `FEATURE_NOT_PROVIDED` | predict | özellik | "<özellik> verilmedi; impute edilmez" (çekirdek yolu; uygulamada market20 sarmalayıcısı önce yakalar) |
| `MARKET20_NOT_PROVIDED`, `MARKET20_NOT_NUMERIC`, `MARKET20_CALENDAR_NOT_COVERING`, `MARKET20_INSUFFICIENT_HISTORY`, `MARKET20_XU100_CLOSE_MISSING`, `MARKET20_STALE_S0`, `MARKET20_PREDICTION_TOO_EARLY`, `MARKET20_XU100_INTEGRITY` | predict_market20 | f6_market20 | "f6 (20 seanslık XU100 getirisi) yok: <neden>; bu model f6'sız tahmin vermez" + nedenin açıklaması (§3a.2) |
| `PB_FIELD_MISSING` | features (PB) | alan / `precision` | "<alan> boş ya da ayrıştırılamıyor (PB)" |
| `PB_IDENTITY` | features (PB) | `ID-A`, `ID-B`, `ID-C`, `BASE_POSITIVE`, `POST_POSITIVE`, `VALUE_POSITIVE`, `PB2_RANGE`, `PB3_RANGE`, `PB4_RANGE` | "planlanan yapı özdeşliği tutmuyor: <ad>" (ID-A: yeni = mevcut + bedelli; ID-B: taban = bedelli + mevcut pay satışı; ID-C: azami = taban + ek satış) |
| `PB_PRICE_RANGE` | features (PB) | ipo_price_try | "fiyat tek değer değil (aralık); PB modeli aralıkla tahmin vermez" |
| uyarı `OUT_OF_TRAINING_RANGE` | hepsi | `feature`, `value`, `train_min`, `train_max` | "<özellik> = v eğitim aralığı [min, max] dışında; tahmin dışdeğerlemedir" |
| uyarı `F4_ZERO_NO_TRAINING_EXAMPLE` | predict | f4 | "sermaye artırımı yok (f4 = 0): eğitimde örneği yok" |
| uyarı `F3_WINSORIZED` | predict | f3, `used` | "f3 eğitim p05/p95 sınırına kırpıldı: kullanılan <used>" |
| uyarı `F3_CLIPPED_TO_TRAINING_P05_P95` | predict_hazard | f3, `used` | aynı metin; ayrıca `clipped = true` |
| uyarı `RETURN_CLIPPED_TO_PHYSICAL_BOUND` | predict | `horizon`, `value`, `used` | "<ufuk> getirisi fiziksel sınıra kırpıldı" |
| uyarı `PB4_ADDITIONAL_SALE_CEILING` | predict_pb, predict_hazard | pb4 | "ek satış tavanı var (pb4 = v); eğitimde 7 örnek" |

Parametre dosyası hataları (`PARAMS_INVALID`, `SCHEMA_UNSUPPORTED`) kullanıcı hatası değildir; §1.4 bütünlük yolu.

### 3c. Senaryo modu

- Varsayılan moddur. Kullanıcı istediği sayıyı girer; kaynak kutuları zorunlu değildir.
- Görsel ayrım: turuncu mod bandı, sütun başlıklarında "SENARYO" filigranı, dışa aktarılan dosyada `official: false`. Sonuç ekranındaki her sayı bir tooltip'te "senaryo tahmini; sicile ve doğruluk hesabına girmez" der.
- Sicile giremez: yazma yolu yalnız `<app_data_dir>/scenarios/` (§2.4, U27–U30). Uygulamada senaryodan resmi kayda giden tek yol "Resmi kayıt için hazırla"dır; bu yol girdileri kopyalar ama kaynak kutuları tamamlanmadan ve repo modu olmadan dondur düğmesini açmaz.
- Kaydedilen senaryolar sonuç ekranına geri yüklenebilir; yüklenen senaryo, gömülü INDEX sha'sından farklı bir sha ile kaydedildiyse sarı "bu senaryo farklı bir model kümesiyle üretildi; yeniden hesaplamak için Tahmin et" uyarısı taşır (eski çıktı olduğu gibi gösterilir, üzerine yazılmaz).

### 3d. Doğruluk paneli (SPEC_SCORING §8 birebir)

Veri: `scores.json` (§2.3). Panel iki BAĞIMSIZ bölümden oluşur; aralarında hiçbir toplam, ortalama ya da birleşik hüküm yoktur (U22).

**Bölüm 1 — "Geçmiş veri testi (retrospektif, tasarıma maruz)"** (başlık `backtest.title`'dan aynen; arka plan lacivert-gri). Model başına açılır kart; içinde hücre tablosu:

| Çıktı | Ufuk/k | Metrik | Model | Kural (`rule_id`) | Fark | %95 aralık | n | kazanç / kayıp / eşit | Hüküm |
|---|---|---|---|---|---|---|---|---|---|

- Birim: getiri hataları **puan** (0.030 → "3.0 puan"); Brier/RPS 4 ondalık.
- Hüküm sütunu `verdict` metnini aynen basar; `null` → "—". Renk: yalnız `verdict ∈ {geçiyor, geçemiyor}` iken (yeşil/kırmızı); "ayırt edilemiyor" ve diğerleri gri.
- **Birincil hücre** (`primary_cell` ile eşleşen satır) kalın çerçeve ve "birincil (önceden ilan)" rozeti; diğer satırlar "keşif" rozeti.
- İsabet oranı (`metric = accuracy`) satırı ancak aynı satırda kuralın isabeti varsa gösterilir; `rule_value` null ise satır gizlenir ve "isabet oranı tek başına gösterilmez" notu düşülür (U20).
- Kalibrasyon ve gün başına Brier hücreleri (tavan modelleri) aynı tabloda `output = S_k`, `horizon_or_k = k`.

**Bölüm 2 — "Canlı sicil (prospektif, n = k; atlanan = s)"** (başlık: `live.title` + `n = {n_scored}; atlanan = {n_skipped}`; arka plan kehribar). Alt başlık: "n_live = a (LIVE), n_late = b (LATE_RECORD); ret = r; hedef oluşmadı = u; bekleyen = p". Ardından n'e göre ÜÇ hâl (U16–U18):

| `n_scored` | Gösterilen |
|---|---|
| **n < 10** | YALNIZ satır tablosu: arz · D1 · sınıf (LIVE/LATE_RECORD) · kayıt · tahmin · gerçekleşen · her kuralın tahmini · durum. Hiçbir metrik, ortalama, hüküm, renk yok. `live.cells` boş olmalı (değilse §2.3 bütünlük hatası). Üstte: "n < 10: metrik hesaplanmaz, yalnız satırlar (SPEC_SCORING §8)". |
| **10 ≤ n < 30** | Satır tablosu + hücre tablosu; her hücre satırında **"yetersiz örnek"** rozeti (verdict metni zaten budur; ek olarak panel başlığında da); `ci95` null olan satırda "aralık için yetersiz"; kazanan vurgusu ve renk YOK. |
| **n ≥ 30** | Tam tablo; verdict renkleri açık; "geçiyor"/"geçemiyor" yalnız `ci95` 0'ı dışlıyorsa (dosya böyle üretmiş olmalı; §2.3 denetimi). |

- `self_reported_rows` ayrı alt tablo: "Legacy, yalnız beyanla zamanlanmış (LEGACY_SELF_REPORTED) — ikincil". Birincil canlı sayılara girmez; kendi n'i ayrı yazılır.
- `retro_info` ayrı, katlanır, gri "RETRO (bilgi amaçlı; hiçbir teraziye girmez)".
- `skipped` listesi: ticker, durum, `skip_reason`.
- Zaman kanıtı sütunu: kayıt için `registry/push_proofs/` altında kanıt varsa "git+push <created_at>" yoksa "zaman kanıtı yok" (satır sınıfını uygulama HESAPLAMAZ; `class` alanı scores.json'dandır).
- "Geçiyor" sözcüğü panelde yalnız `verdict` metninden gelir; arayüz metinlerinde başka yerde geçmez (U19: kaynak kodunda `geçiyor` dizesi yalnız verdict eşleme tablosunda ve bu kuralın açıklamasında bulunur).
- Model kartı ve rejim uyarısı §3b'deki gibi panelin üstünde.

Durumlar: dosya yok → "scores.json bulunamadı (Faz 2B henüz koşmadı ya da yol yanlış)"; sürüm uyumsuz → §2.5; bütünlük hatası → §2.3; `n_scored = 0` → yalnız başlık ve "canlı kayıt henüz skorlanmadı".

### 3e. Resmi "dondur" akışı

**[KARAR] Kayıt yazıcı Python `borsai.freeze` olarak kalır.** Gerekçe: kayıt repoya bağlı kanıt taşır (git HEAD, `borsai/` kaynak ağacı sha'sı, pinli XU100/takvim sha'ları ve f6, legacy roller, INDEX sha denetimi, `DUPLICATE_RECORD` ve iptal kuralları; `freeze.py:204-248`); bunları Rust'ta ikinci kez yazmak "iki yazıcı" riski ve Faz 2B ile eşzamanlı değişen kuralları takip yükü demektir. Uygulamanın katkısı: doğru girdi belgesini üretmek, süreci tek düğmede toplamak, çıkan kaydı kendi tahminiyle parite denetiminden geçirmek ve sonraki adımları (commit, push, kanıt) tam komutlarla göstermek. Push, tag, amend uygulama tarafından YAPILMAZ (CLAUDE.md: yalnız proje sahibi).

Akış (ekran: "Resmi kayıt" sihirbazı, 6 adım; her adımın çıktısı ekranda kalır):

1. **Ön koşullar:** repo modu; `git` var; `<repo>/models/INDEX.json` sha'sı gömülü INDEX sha'sına eşit (değilse DUR: "uygulama farklı bir model kümesiyle derlenmiş; yeniden derleyin"); `GIT_OPTIONAL_LOCKS=0 git status --porcelain -- registry` çıktısı gösterilir (kirli olabilir, yalnız bilgi).
2. **Kaynak belgeler:** seçilen PDF'ler `<repo>/registry/source_docs/<T>/` altına kopyalanır (var olan aynı adlı dosya ancak sha eşitse kabul; farklıysa DUR), sha256 ölçülür, `MANIFEST.json` var olan biçimde (NETGL'deki alanlar [ÖLÇTÜM]) yazılır/eklenir (var olan giriş değiştirilmez).
3. **Girdi belgesi:** `registry/inputs/<T>.json` üretilir (`pretty_json_bytes` biçimi: sıralı anahtar, 2 boşluk, sonda LF). Dosya varsa fark gösterilir ve kullanıcı onaylar (aynı arzın ikinci aşaması: önce PB, sonra talep katlı; açık soru 3).
4. **Denetim (yetkili):** `<python> -c "import json,sys; from borsai import registry as r; d,_=r.load_inputs(sys.argv[1]); print(json.dumps(r.inputs_pit_problems(d)))" registry/inputs/<T>.json` → boş liste değilse DUR, sorunlar listelenir.
5. **"İlk işlem gününden önce" uyarısı:** T doluysa ve bugün (Istanbul) ≥ T ise kırmızı: "Bu kayıt ilk işlem gününden sonra yazılıyor; SPEC_SCORING §5'e göre en iyi hâlde LATE_RECORD olur, LIVE olamaz." T boşsa sarı: "T bilinmiyor; kayıt yine yazılır, f6 kural 5 denetlenemez." Kullanıcı "yine de dondur" der.
6. **Dondur:** `<python> -m borsai.freeze registry/inputs/<T>.json` (cwd = repo_root; stdout = kayıt yolu). Başarıda uygulama kaydı okur, her modelin hücresini Rust `predict_all` çıktısıyla (aynı girdi + kayıttaki `market20.f6/refusal`) §1.3 kurallarıyla karşılaştırır; sonuç "parite: 16/16 model |Δ|max = …" ya da kırmızı "PARİTE UYUŞMAZLIĞI: <model> <alan> Δ = …" (kayıt yine geçerlidir; uygulama sayısı değil kayıt esastır; uyuşmazlık `app/parity/incidents/<UTC>.json`'a yazılır ve raporlanır). Hata çıkışında stderr aynen gösterilir; `DUPLICATE_RECORD` ve "iptal edilmemiş kayıt var" (2B öncesi kural) mesajları Türkçe açıklanır.

Sonra ekran **"Şimdi yapılacaklar"** (kopyalanabilir komut blokları; uygulama çalıştırmaz):
```bash
cd <repo_root>
git add registry/inputs/<T>.json registry/source_docs/<T>/ registry/records/<T>/<dosya>.json
git commit -m "BORSAI_RECORD_<T>: prediction record before first trading day"
git push origin main
.venv/bin/python -m borsai.push_proof $(git rev-parse HEAD)
git add registry/push_proofs/ && git commit -m "BORSAI_PUSH_PROOF: <sha>" && git push origin main
```
ve metin: "Zaman kanıtı push'tur, yerel saat değil (CLAUDE.md kural 1). Kanıt `created_at` tarihi T'den önceyse kayıt LIVE adayıdır." Kayıt listesinde (Sicil ekranı) her kayıt için `registry/push_proofs/` taranır: kaydı ekleyen commit'i uygulama bilemez (commit henüz atılmamış olabilir); bu yüzden gösterge "kanıt dosyası var: <sha> <created_at>" ya da "push kanıtı bulunamadı" düzeyindedir, sınıf hesaplamaz.

**Aynı arza ikinci kayıt:** önce PB (talep toplama öncesi) kaydı, sonra talep katlı kayıt. Faz 2B düzeltmesinden (FAZ2B adım 3) sonra `freeze` bunu kabul eder; öncesinde "iptal edilmemiş kayıt var" hatası verir. Uygulama bu hatayı "Faz 2B düzeltmesi henüz yok: ikinci kayıt için önce iptal gerekir ya da kod güncellenmeli" diye açıklar; kendisi iptal ETMEZ. Hangi kaydın skorlanacağına SPEC_SCORING §6 karar verir; uygulama sicil ekranında ikisini de listeler ve "birincil kayıt seçimi skorlamada yapılır" yazar.

**İptal akışı:** Sicil ekranında etkin kayıt → "İptal kaydı düş" → neden metni (boş olamaz) → `<python> -m borsai.freeze --cancel registry/records/<T>/<dosya>.json --reason "<neden>"`. Python T'den itibaren iptali reddeder (`freeze.py:303`); uygulama aynı kuralı önceden gösterir ama son söz Python'undur. İptal edilen dosya silinmez; listede üstü çizili + neden + zaman.

**Resmi sicil repoda kalır:** uygulama verisinde sicilin kopyası tutulmaz; "Sicil" ekranı her açılışta `<repo>/registry/records/**` okur. Kişisel kayıtlar oraya yazılamaz (U27).

### 3f. Kişisel kayıtlar

Liste: başlık, oluşturma zamanı, aşama, uygulama sürümü, model kümesi sha (ilk 8), "gömülü kümeyle aynı mı" rozeti. İşlemler: aç (sonuç ekranına yükle), sil (onay; geri alınamaz; dosya silinir), dışa aktar (dosya seçici; repo altı reddedilir), tümünü dışa aktar (tek JSON dizisi). Boş hâl: "Henüz kişisel kayıt yok; sonuç ekranında 'Kişisel kayıt olarak sakla'". Hata: dosya okunamıyor → satır "okunamıyor" ve sil seçeneği. Panelin üstünde sabit: "Kişisel kayıtlar sicile ve doğruluk hesabına girmez."

---

### 3g. Koşullu tavan güncellemesi (EK 1)

**Tanım.** Tavan modelleri S_k = P(L ≥ k), k = 1..10 verir; S_0 = 1. Seri j gün sürdüyse (gözlenen j ardışık tavan kapanışı, seri henüz bozulmamış):

```
P(L ≥ k | L ≥ j) = S_k / S_j                       k > j
P(L = k | L ≥ j) = P_L[k] / S_j = (S_k − S_{k+1}) / S_j   k ≥ j, S_11 := 0
"yarın bozulur"   = P(L = j | L ≥ j) = 1 − S_{j+1} / S_j
tanımsız          : S_j = 0 ya da j ≥ 10   → "—"
j = 0             : koşulsuz S_k (S_0 = 1)
```
Beklenen kalan gün ve koşullu medyan L, koşullu P_L'den §3b'deki formüllerle (görüntüleme türevi). Hesap Rust `borsai_predict::survival::conditional(S, j)` fonksiyonundadır (saf; `S_k / S_j` tek bölme, ek işlem yok); ön uç hesaplamaz.

**Veri kaynağı: gözlenen seri j [KARAR].**
- **Birincil:** repo modunda `<repo_root>/data/outcomes/<T>.csv` (Faz 2B üretir; etiket resmi THM'den, SPEC_SCORING §3). Satırlar h = 1..10 sırasıyla okunur; j = baştan itibaren `status = OK` ve `ceiling_close = 1` olan ardışık satır sayısı; ilk `ceiling_close = 0` (status OK) seriyi bozar → L = j gerçekleşmiştir, koşullu eğri yerine "seri D{j+1}'de bozuldu; gerçekleşen L = j" gösterilir; ilk `PENDING` satırda durulur (j o ana kadarki sayı); `NA_LIMIT` ya da `TARGET_UNAVAILABLE` satırında durulur ve şerit o günü "etiket yok" gösterir, koşullu eğri j ile yine hesaplanır ama "etiketsiz gün var" uyarısı taşır. Dosya yoksa "gözlenen seri yok (Faz 2B henüz üretmedi)". Gerekçe: tek resmi kaynak; uygulama THB/THM indirmez, etiket üretmez.
- **İkincil:** kullanıcı beyanı [KARAR, proje sahibi 2026-09-23]: şeritte bir güne tıklayarak yalnız "seri sürüyor" (o gün tavan kapandı) işaretlenebilir; başka beyan türü yoktur. Beyan **yalnız etikettir**: şeritte turuncu çerçeve ve "seri sürüyor (kullanıcı beyanı)" yazısı.
  - Beyan hiçbir koşulda olasılık ya da getiri hesabına girmez. Resmi j'yi değiştirmez. Koşullu eğri, "yarın bozulma olasılığı", koşullu beklenen/medyan L ve koşullu getiri (EK 2 §4.3) yalnız resmi veriden hesaplanır.
  - Beyan resmi verinin önündeyse (beyanlı gün dosyada yok ya da `PENDING`): koşullu olasılık bölümü ve koşullu getiri kartı **boş kalır** ve "resmi kapanış bekleniyor" uyarısı gösterir. Resmi kapanış dosyaya girince beyan etiketi kalkar, hesap resmi veriyle yapılır.
  - Dosyadaki resmi değerle çelişen beyan gösterilmez; yerine "beyan resmi veriyle çelişiyor; resmi değer esas" uyarısı çıkar.
  - Gerekçe: beyanla üretilmiş bir sayı ekran görüntüsünde ya da aylar sonra bakıldığında modelin çıktısından ayırt edilemez; resmi kapanış zaten aynı akşam belli olur.
  - Beyan yalnız uygulama belleğinde ve (kullanıcı saklarsa) kişisel kayıt dosyasında `observed_streak_user` alanında tutulur; `data/outcomes/`, `registry/` ve `scores` hiçbir yoldan yazılmaz (U39, U52).

**Ekran ("Arz sayfası" — sicil ekranından bir arz seçilince ve sonuç ekranının tavan grubunda):**
- **Gün gün şeridi** D1..D10: durumlar `tavan` (yeşil), `tavan değil` (kırmızı), `bekliyor` (gri), `etiket yok` (çizgili), `beyan` (turuncu çerçeve, "seri sürüyor (kullanıcı beyanı)"; yalnız etiket). Altında kaynak satırı: "kaynak: data/outcomes/<T>.csv (as-of <son session_date>)"; beyanlı gün varsa ek satır "D<k>: kullanıcı beyanı, hesaba katılmadı".
- **j seçici:** varsayılan resmi j (dosyadan; beyan bu değeri değiştirmez); kullanıcı 0..9 arasında kaydırabilir ("j = 3 ise…" senaryosu; seçilen j gözlenenden farklıysa "varsayımsal j" etiketi).
- **Koşullu eğri:** seçilen j için bütün tavan modellerinin (hazard ve km türleri + "her zaman tavan" sabiti) `P(L ≥ k | L ≥ j)` eğrileri yan yana, aynı SVG'de; tablo k = j+1..10; ayrıca "yarın bozulma olasılığı" ve koşullu beklenen/medyan L. Basit kuralların koşullu değeri aynı formülle kendi S vektörlerinden ("koşullu KM"). Tanımsız hücreler "—".
- **Resmi sicil görünümünde** S vektörleri yalnız dondurulmuş kayıttaki `models[].output.S`'ten okunur (kayıt `record_type = PREDICTION`, iptal edilmemiş; birden çok kayıt varsa her biri ayrı sekme). Model yeniden çalıştırılmaz, girdi değiştirilmez; ekran "kaynak: kayıt <dosya adı>, params sha <ilk 8>" yazar (U38).
- **Senaryo modunda** S vektörleri senaryo çıktısından; mod bandı ve "senaryo" filigranı §3c'deki gibi.
- **İleride (Faz 4) tavan-yolu modelleri** L ≥ j koşulunda D_h getiri dağılımı ve p_up verecek (`docs/specs_faz4/`). Bu şartname yalnız yeri ayırır: koşullu bölümde "getiri (koşullu)" sekmesi, INDEX'te o türde model yoksa "henüz yok" gösterir. Çıktı şeması Faz 4 şartnamesiyle gelince §2.1'e eklenir ve altın vektörler genişletilir.

**Doğruluk gösterimi:** `scores.json`'daki `models[].conditional` bloğu (Faz 4 §7) doğruluk panelinde **üçüncü, ayrı** bölümde ("Koşullu tavan skorları") gösterilir; §8 küçük-n ve hüküm kuralları o bloğun kendi n'iyle aynen uygulanır; koşulsuz tabloyla hiçbir satırda toplanmaz; blok yoksa "henüz koşullu skor yok".

## 4. Dil ve üslup

- Arayüz Türkçe; kod ve JSON anahtarları İngilizce (sözleşmelerle aynı). Metinler tek dosyada (`app/src/i18n/tr.ts`), kod içinde serbest metin yok (U21 tarama).
- Sözcükler: "tahmin", "olasılık", "P(kapanış > arz)", "tavan serisi", "basit kural", "fark", "%95 aralık", "ayırt edilemiyor". Yasak: "kesin", "garanti", "kazandırır", "al/sat", "hedef fiyat", "sinyal", "doğruluk %<sayı>" tek başına.
- Sayı biçimi: getiri 1 ondalık yüzde, fiyat 2 ondalık TL, olasılık 0 ondalık yüzde, metrik 4 ondalık, hata "puan"; tooltip'te ham binary64 (Python repr ile aynı, `format!("{:?}")`).
- Yer tutucu (her ekranın altında, sabit dize `DISCLAIMER`): `Bu uygulama yatırım tavsiyesi değildir; çıktılar istatistiksel tahmin ve olasılıklardır.` Hukuki metin değildir; ürünleşmeden önce §8-1'deki çerçeveyle değiştirilecektir.

## 5. Kabul testleri (U1…U40)

Her test **otomatik** (`cargo test`, `npm test` = vitest, `bash app/tests/*.sh`) ya da **elle kanıtlanabilir** (ekran görüntüsü + dosya çıktısı raporda). Kanıt biçimi her satırda.

### 5.1 Parite (Rust ↔ Python)

| # | Test | Yöntem | Kanıt |
|---|---|---|---|
| U1 | Her kayıtlı model için `app/parity/golden/<model_id>.jsonl` var ve ≥ 200 satır; `gen_golden.py` yalnız stdlib predict yolunu import eder (`numpy`/`sklearn` import edilirse test kırmızı; `tests/test_predict.py` yöntemi: alt süreçte `sys.modules` taraması) | `cargo test golden_files_present`; Python tarafı `app/parity/test_gen_golden.py` (pytest, repo `.venv`) | test çıktısı |
| U2 | Bütün satırlarda §1.3 karşılaştırması geçer: sayısal \|Δ\| ≤ 1e-9, ret kodu+alan birebir, uyarı (kod, özellik/ufuk) çok kümesi birebir, `direction`/`return_clipped`/`clipped` birebir | `cargo test -p borsai_predict --test golden` | `target/parity_report.json`: model başına satır sayısı, maks \|Δ\|, bit-eşit oranı |
| U3 | Uç yollar kapsanmış: her T-2 ret kodu ve her uyarı kodu altın vektörlerde ≥ 2 satırda geçiyor; `RETURN_CLIPPED_TO_PHYSICAL_BOUND` her ufukta UPPER ve LOWER en az birer kez (ulaşılamayan ufuk `golden/README.md`'de gerekçeli) | `cargo test golden_coverage` (etiket sayımı) | kapsama tablosu |
| U4 | Sayısal kararlar: `_pct` yuvarlama sınırı satırları (ör. 1/3, 2/3, 5/1e11, 28+ haneli girdiler), `float(Decimal)` doğru yuvarlama, Neumaier toplama (`[1e16, 1, −1e16]` → 1.0), PB `n/d` `< 2^53` ve üstü yolları | `cargo test dec_semantics` (birim testleri, beklenenler Python'dan `gen_golden.py --dec-cases` ile üretilir) | çıktı |
| U5 | Gömülü INDEX'teki her model `predict_all` sonucunda tam bir sütun üretir (16/16), sıra INDEX sırası, `params_sha256` INDEX ile eşit | `cargo test predict_all_covers_index` | çıktı |
| U6 | Resmi kayıtla parite: `registry/records/**` altındaki her PREDICTION kaydı için, kayıttaki `model_inputs` (f6 dahil) ile Rust çıktısı kaydın `models[].output` alanlarına §1.3 kurallarıyla eşit (7 arz × 16 model) | `cargo test records_parity` (repo yolu `BORSAI_REPO` ortam değişkeninden; yoksa test atlanır ve bunu yazar) | çıktı; rapor |

### 5.2 Ret ve uyarı kodları

| # | Test | Yöntem | Kanıt |
|---|---|---|---|
| U7 | f3 boş girdi: `v1_5_h99`, `v1_6_h99`, `v1_5_market20_v0`, `ceiling_hazard_v0` → `F3_MISSING`/`total_demand_multiple`; PB modelleri, KM ve kurallar tahmin verir; sonuç ekranında 4 RET bloğu ve 12 dolu sütun | `cargo test` (kod) + vitest (render) + elle ekran görüntüsü | ikisi de |
| U8 | Her T-2 kodu için arayüz metni var (`tr.ts` anahtar kümesi = kod kümesi; eksik anahtar derlemede hata) | vitest `codes_have_text` | çıktı |
| U9 | f6 yok/bayat: `MARKET20_NOT_PROVIDED` ve `MARKET20_STALE_S0` senaryoları sonuç ekranında neden açıklamasıyla; diğer 15 model etkilenmez | cargo + vitest | çıktı |
| U10 | Kırpma: getirisi sınır dışına çıkan girdi hücrede `⌐` işareti + ham değer tooltip'i; `return` sınırda, `return_unclipped` ham | cargo (altın) + vitest (render) | çıktı |
| U11 | Uyarılar hiçbir hücreyi gizlemez: `OUT_OF_TRAINING_RANGE` + `F4_ZERO` + `PB4` aynı anda olan girdi → 16 sütun da dolu, rozet sayıları doğru | vitest | çıktı |
| U12 | Parametre dosyası bozuk (test-içi kopyada `coef` uzunluğu değiştirilmiş) → `PARAMS_INVALID`, uygulama `INTEGRITY_FAILED`; tahmin komutu hata döner | cargo `integrity_fail_closed` | çıktı |

### 5.3 Gösterim kuralları (SPEC_SCORING §7–§8) — K2 eşlemesi, tablo T-1

Fixture'lar: `docs/app/ekler/scores_n7_sentetik.json`, `scores_n12_sentetik.json`, `scores_n35_sentetik.json` (kurgusal SNTxx arzları; `synthetic: true`; uygulayıcı bunları `app/tests/fixtures/` altına kopyalar ve Faz 2B'nin gerçek şeması çıkınca alan adlarını günceller — kurallar değişmez). Render fonksiyonları saf TS'dir (`renderAccuracy(scores): HtmlString`), vitest DOM'suz metin/`jsdom` ile sınar.

| # | §8 kuralı | Test | Yöntem |
|---|---|---|---|
| U13 | Backtest başlığı aynen "Geçmiş veri testi (retrospektif, tasarıma maruz)"; canlı başlık "Canlı sicil (prospektif, n = k; atlanan = s)" ve n_live/n_late alt satırı | vitest: başlık dizeleri birebir; n = 7, atlanan = 1 için "n = 7; atlanan = 1" | çıktı |
| U14 | İki terazi ayrı renk sınıfı (`.panel-backtest`, `.panel-live`) ve aralarında toplam/ortalama içeren hiçbir öğe yok; TS'de iki listeyi birleştiren fonksiyon yok | vitest: DOM'da her iki sınıf; `grep -R "concat\|\.\.\.backtest.*live"` tarzı statik denetim testi + koddaki tek birleştirme noktası olmadığının `lint` kuralı | çıktı |
| U15 | Her metrik satırı: model değeri · kural adı · kural değeri · fark · aralık · n · kazanç/kayıp/eşit; getiri hataları "puan" birimiyle (0.0046 → "0.5 puan") | vitest n35 fixture | çıktı |
| U16 | **n < 10 → yalnız satır tablosu:** n7 fixture ile çıktı satır tablosunu içerir (7 satır: arz, D1, sınıf, tahmin, gerçekleşen, kuralların tahmini), hiçbir `<td class="metric">` yok, "yetersiz örnek"/"geçiyor"/"ayırt" dizeleri yok, renk sınıfı yok; "n < 10: metrik hesaplanmaz" notu var | vitest + elle ekran görüntüsü | ikisi |
| U17 | **10 ≤ n < 30 → "yetersiz örnek":** n12 fixture ile hücreler var, her satırda "yetersiz örnek" rozeti, `ci95 null` satırında "aralık için yetersiz", kazanan renk sınıfı (`.win`/`.lose`) YOK | vitest | çıktı |
| U18 | **n ≥ 30:** n35 fixture ile "geçiyor" (aralık [−0.009, −0.001]), "geçemiyor" ([0.001, 0.005]), "ayırt edilemiyor" ([−0.006, 0.004]) satırları doğru renkte; metinler `verdict` alanından | vitest | çıktı |
| U19 | **"Geçiyor" başka koşulda yok:** kaynak ağacında "geçiyor" dizesi yalnız `tr.ts`'deki verdict eşlemesinde; n7 ve n12 render çıktısında hiç yok; n35'te yalnız verdict'i öyle olan satırlarda | vitest + `grep -R` testi | çıktı |
| U20 | **İsabet oranı tek başına yok:** `metric = accuracy` satırı yalnız `rule_value` doluyken; fixture'daki `rule_value` null yapılmış kopyada satır gizlenir ve not düşülür | vitest | çıktı |
| U21 | **Model kartı:** model_id, eğitim n, kesim, sha ilk 8 (`bf809859`), varyant sayısı (2) kartta; yasak sözcük listesi (§4) `tr.ts`'de geçmez | vitest | çıktı |
| U22 | **Birincil hücre vurgusu:** `primary_cell` (D5 MAE vs median) satırı `.primary` sınıfı ve "birincil (önceden ilan)" rozeti; diğer satırlar "keşif" | vitest | çıktı |
| U23 | **Rejim uyarısı** sonuç ve doğruluk ekranında sabit metinle var | vitest | çıktı |
| U24 | **Fail-closed bütünlük:** n7 fixture'ına elle `live.cells` eklenmiş kopya → panel yerine hata; n12'de `verdict: "geçiyor"` yapılmış kopya → hata; n35'te ci95 0'ı içerirken "geçiyor" → hata; `n_live + n_late ≠ n_scored` → hata | vitest | çıktı |
| U25 | **Uygulama skor hesaplamaz:** TS ve Rust kaynaklarında `bootstrap`, `percentile`, `mean(` … gibi metrik hesap fonksiyonu yok (beyaz liste: beklenen/medyan L, yüzde biçimlendirme); scores.json'dan gelen her sayı DOM'da olduğu gibi (biçimlendirilmiş) — vitest fixture'daki her `model_value` metnini DOM'da bulur | vitest + statik tarama | çıktı |
| U26 | **Legacy self-reported ikincil ve RETRO ayrı:** fixture'a `self_reported_rows` ve `retro_info` eklenince ayrı bölümlerde ve canlı n'e girmeden gösterilir | vitest | çıktı |

### 5.4 Dondur akışı uçtan uca (geçici repo) ve kişisel kayıt izolasyonu — K4

Betik `app/tests/e2e_freeze_tmp_repo.sh` (bash + repo `.venv` Python'u; ağ yok):

| # | Test | Yöntem | Kanıt |
|---|---|---|---|
| U27 | **Kişisel kayıt sicile giremez (yol):** `save_scenario`/`export_scenario` hedefi `repo_root` altındaysa (kanonik yol, sembolik bağ çözülmüş) `SCENARIO_PATH_INSIDE_REPO` hatası; `app_data_dir` repo altına ayarlanamaz (ayar reddedilir) | `cargo test scenario_path_guard` | çıktı |
| U28 | **Kişisel kayıt sicile giremez (izleme):** betik: geçici klon `git clone --local <repo> $TMP`; uygulama komutları (`tauri` CLI'siz, `cargo test --test e2e` ile aynı Rust komut fonksiyonları) 3 senaryo kaydeder ve 1'ini dışa aktarır; ardından `$TMP/registry` ağacının sha listesi (öncesi/sonrası) birebir aynı ve `GIT_OPTIONAL_LOCKS=0 git -C $TMP status --porcelain -- registry` boş; asıl repoda da aynı | betik | çıktı |
| U29 | **Kişisel kayıt skorlanamaz (şema):** bir senaryo dosyası kasten `$TMP/registry/records/SNT01/` altına kopyalanır; `python -c "from borsai import freeze as f; print(len(f.active_records('SNT01', ...)))"` → 0 (record_type yok); test sonra dosyayı siler | betik | çıktı |
| U30 | **Dondur uçtan uca:** `$TMP`'de kurgusal arz `SNTA1` (T = bugün + 5, B = bugün − 3, kaynak belgeler = betiğin ürettiği 3 küçük PDF, `published_at` = dün): adım 2–6 çalışır; `$TMP/registry/inputs/SNTA1.json` `validate_inputs` boş liste; `inputs_pit_problems` boş; `freeze` bir kayıt yazar (`$TMP/registry/records/SNTA1/<UTC>_<sha12>.json`), kayıt 16 model içerir, dosya adı içerik sha'sıyla tutarlı; Rust parite 16/16; kayıt `git status`'ta untracked görünür (commit uygulama tarafından atılmaz); uygulama verisinde kayıt kopyası YOK; sonra `--cancel` ile iptal kaydı düşer ve `active_records` 0 olur; iptal nedeni boşsa hata | betik + `cargo test e2e` | betik çıktısı |
| U31 | **T geçmişse uyarı:** T = dün ile adım 5 kırmızı uyarı; `--cancel` Python tarafından reddedilir ve uygulama hatayı aynen gösterir | betik | çıktı |
| U32 | **Push kanıtı komutu gösterimi:** adım 6 sonrası ekrandaki komut bloğu `git rev-parse HEAD` ve `python -m borsai.push_proof` içerir; uygulama `git push`/`commit` ÇALIŞTIRMAZ (Rust'ta `Command::new("git")` argümanları beyaz liste: `rev-parse`, `status`, `log`, `ls-files`; test argüman beyaz listesini sınar) | `cargo test git_readonly_whitelist` | çıktı |

### 5.5 Bütünlük, şema, çevrimdışılık

| # | Test | Yöntem |
|---|---|---|
| U33 | Gömülü her model dosyası sha256 = INDEX; INDEX sha = build_info; `_check_params` hepsinde geçer; INDEX'te olup diskte olmayan dosya derlemeyi kırar | `cargo test embedded_integrity` + `build.rs` |
| U34 | Ağ bağımlılığı yok: `Cargo.lock`'ta `reqwest`, `ureq`, `hyper`, `tauri-plugin-http` yok; `package-lock.json`'da `axios`/`node-fetch` yok; `tauri.conf.json` CSP `connect-src 'self' ipc: http://ipc.localhost` dışına izin vermez | `cargo test no_network_deps` + vitest |
| U35 | Şema uyumsuzluğu: `schema_version` değiştirilmiş scores/inputs/record/scenario kopyaları §2.5 tablosundaki davranışı verir (kısmi gösterim yok) | vitest + cargo |
| U36 | Senaryo yükleme: farklı `models_index_sha256` ile kaydedilmiş senaryo sarı uyarıyla açılır, çıktı üzerine yazılmaz | vitest |

### 5.6 Koşullu tavan güncellemesi (EK 1)

| # | Test | Yöntem | Kanıt |
|---|---|---|---|
| U37 | **Parite:** her hazard/km altın satırı için j = 0..9 koşullu vektörleri (`S_k/S_j`, `P_L[k]/S_j`, `1 − S_{j+1}/S_j`) Python'da `gen_golden.py`'nin aynı ifadelerle ürettiği beklenenlere \|Δ\| ≤ **1e-12**; j = 0'da koşulsuz S ile bit-eşit; S_j = 0 ve j ≥ 10 → tanımsız (`null`) | `cargo test conditional_parity` | `parity_report.json` koşullu bölümü |
| U38 | **Resmi görünüm yalnız dondurulmuş S kullanır:** test kaydı, `models[].output.S` değerleri kayıttaki `model_inputs`'tan Rust `predict_all`'ın üreteceğinden kasten farklı (örn. hepsi 0.5^k) bir kayıtla render edilir; ekrandaki koşullu değerler kayıttaki S'ten (0.5^(k−j)) çıkar, Rust tahmini çağrılmaz (komut çağrı sayacı 0) | vitest + `cargo test official_view_uses_record_only` | çıktı |
| U39 | **Kullanıcı beyanı hiçbir skora ve sicile girmez:** geçici klonda şerit beyanı girilir, senaryo saklanır, resmi kayıt görüntülenir; ardından `$TMP/data/outcomes`, `$TMP/registry`, `$TMP/scores` ağaçlarının sha listesi öncesiyle aynı; beyan yalnız `<app_data_dir>/scenarios/*.json` içinde `observed_streak_user` alanında; `scores.json` okuyucu bu alanı hiçbir yerde okumaz (statik tarama: `observed_streak_user` yalnız scenario modülünde geçer) | `e2e_personal_isolation.sh` + vitest | çıktı |
| U40 | **Şerit ve tanımsızlık:** sentetik `data/outcomes/SNTA1.csv` (kurgusal; 3 OK-tavan, 1 PENDING) → j = 3, şerit yeşil×3 + gri; 2 tavan + 1 tavan değil → "seri D3'te bozuldu; L = 2", koşullu eğri yok; NA_LIMIT satırı → "etiket yok" + uyarı; j = 10 ya da S_j = 0 → "—"; gözlenen j ile seçilen j farklıysa "varsayımsal j" etiketi | vitest | çıktı |
| U52 | **Beyandan türetilmiş sayı arayüzde yok** [KARAR, proje sahibi 2026-09-23]: fixture kurgusal `data/outcomes/SNTB1.csv` (D1–D2 OK-tavan, D3 `PENDING`; resmi j = 2) + beyan "D3 seri sürüyor" (beyanlı j = 3). <br>(1) Test, beyanlı j = 3 ile çıkacak değer kümesini aynı Rust fonksiyonlarından üretir ve arayüzün biçimlendiricisiyle metne çevirir: tavan modellerinde S_k/S_3 (k = 4..10), 1 − S_4/S_3, koşullu beklenen ve medyan L; Faz 4 modellerinde (port geldiyse) h = 4..10 koşullu medyan, p_up, q10, q90. Küme boş olamaz. Aynı ekranda başka bir kaynaktan da üretilen metinler kümeden çıkarılır ve listelenir. <br>(2) Render edilen DOM'un tamamında (metin düğümleri, `title`/`aria-label`/`data-*` öznitelikleri, SVG `<text>`/`<title>`, ipuçları) bu metinlerin HİÇBİRİ geçmez. Üç görünümde sınanır: resmi sicil, sonuç ekranı, senaryo. <br>(3) Koşullu olasılık bölümünde ve koşullu getiri kartında "resmi kapanış bekleniyor" yazar ve sayı hücresi yoktur. Şeritte D3 turuncu çerçeve ve "seri sürüyor (kullanıcı beyanı)". <br>(4) Pozitif kontrol: aynı fixture'da D3 `OK`-tavan yapılınca (resmi j = 3) aynı küme ekranda görünür. Arama gerçekten sayı bulabiliyor. <br>(5) Statik: koşullu hesap yapan Rust komutlarının (`conditional`, `streak_view`, `path_conditional`) imzasında beyan parametresi yoktur (`cargo test conditional_commands_take_no_declaration`). `observed_streak_user` ve ön uçtaki beyan durumu yalnız şerit etiketi render'ında ve senaryo kayıt modülünde geçer. <br>(6) Şeritte beyan seçeneği yalnız "seri sürüyor"dur. | vitest + `cargo test` | çıktı |

## 6. Kurulum ve çalıştırma (macOS arm64, kişisel)

[ÖLÇTÜM 2026-09-22] `rustc`, `cargo`, `node`, `npm`, `brew`, `uv` yok; Xcode CLT `/Library/Developer/CommandLineTools` var; `git` `/usr/bin/git`; repo `.venv` CPython 3.12.14.

Claude Code'un çalıştıracağı komutlar (yönetici parolası gerekmez; hepsi kullanıcı diziniyle sınırlı):

```bash
# 1. Rust (rustup, kararlı araç zinciri; Tauri 2 için ≥ 1.77.2)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal
source "$HOME/.cargo/env"
rustc --version && cargo --version

# 2. Node LTS (brew yok → nvm; alternatif: nodejs.org .pkg, yönetici ister)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"
nvm install 22 && nvm use 22
node --version && npm --version

# 3. Tauri iskeleti (app/ altında; app/.gitkeep kaldırılır)
cd ~/Desktop/BorsAi
rm app/.gitkeep
npm create tauri-app@latest app -- --template vanilla-ts --manager npm --identifier tr.borsai.app --yes
cd app && npm install
npm install @tauri-apps/plugin-dialog && cd src-tauri && cargo add tauri-plugin-dialog && cd ..
npm install -D vitest jsdom

# 4. Geliştirme ve derleme
npm run tauri dev                 # canlı geliştirme
npm run tauri build               # app/src-tauri/target/release/bundle/macos/BorsAi.app (+ .dmg)
cd src-tauri && cargo test --workspace   # predict paritesi dahil
cd .. && npm test                 # vitest: gösterim kuralları
bash tests/e2e_freeze_tmp_repo.sh # dondur akışı (geçici klon)
```
`create-tauri-app` bayrak adları CTA sürümüne göre değişebilir; etkileşimli sihirbaz da kabul (seçimler: vanilla, TypeScript, npm). Ağ yalnız kurulum adımlarında (rustup, nvm, npm registry, crates.io) kullanılır; uygulamanın kendisi ağa çıkmaz.

**Dizin düzeni (`app/`):**
```
app/
  package.json  tsconfig.json  vite.config.ts  index.html
  src/
    main.ts                 gezinme, mod bandı, DISCLAIMER
    types.ts                Rust komut sözleşmeleri (serde ile aynı alan adları)
    i18n/tr.ts              bütün arayüz metinleri, T-2 kod → metin
    screens/{inputs,results,accuracy,registry,scenarios,settings,about}.ts
    render/{accuracy.ts, results.ts, svg.ts, format.ts}   saf fonksiyonlar (vitest hedefi)
  src-tauri/
    Cargo.toml (workspace: ".", "crates/borsai_predict")  tauri.conf.json  build.rs
    capabilities/default.json   (core:default, dialog:default; başka izin yok)
    src/{main.rs, lib.rs, state.rs, commands/{config,models,predict,scenario,inputs_doc,freeze,scores,git}.rs, python.rs, embedded.rs(build.rs üretir)}
    crates/borsai_predict/
      Cargo.toml (serde, serde_json[preserve_order], num-bigint, num-rational, num-traits)
      src/{lib.rs, dec.rs, sum.rs, features.rs, pb_features.rs, horizons.rs, linear.rs, hazard.rs, market20.rs, survival.rs, params.rs, error.rs}
      tests/{golden.rs, dec_semantics.rs, coverage.rs, records_parity.rs}
  parity/
    gen_golden.py  test_gen_golden.py  README.md  golden/<model_id>.jsonl (16 dosya, commit edilir)  incidents/ (boş, .gitkeep)
  tests/
    fixtures/scores_n{7,12,35}.json   display.test.ts   codes.test.ts   e2e_freeze_tmp_repo.sh   e2e_personal_isolation.sh
```

**Rust ↔ TS komut sözleşmesi (`#[tauri::command]`):** `app_info()`, `get_config()`, `set_config(cfg)`, `validate_repo(path)`, `predict_all(inputs, f6)`, `market20_via_python(ref_date, t)`, `save_scenario(doc)`, `list_scenarios()`, `load_scenario(id)`, `delete_scenario(id)`, `export_scenario(id, target)`, `write_inputs_document(doc, files)`, `check_inputs_document(rel_path)`, `freeze_record(rel_path)`, `cancel_record(rel_path, reason)`, `list_official_records()`, `read_record(rel_path)`, `load_scores(source)`, `git_status_registry()`. Hepsi `Result<T, AppError>`; `AppError = {code, message, detail?}`; ön uç `code`'u `tr.ts`'ten çevirir.

**macOS imzası:** kişisel kullanımda ertelenir. `tauri.conf.json` → `bundle.macOS.signingIdentity: "-"` (ad-hoc) ya da null; yerel derlenen `.app` karantina bayrağı taşımadığından Gatekeeper'a takılmaz. Dağıtım gündeme gelirse Developer ID + notarization ve §8-1.

**Uygulama verisi:** `~/Library/Application Support/tr.borsai.app/{config.json, scenarios/}`. Ayarlar ekranı `repo_root` ve `python_path` (varsayılan `<repo_root>/.venv/bin/python`) alır; doğrulama: `models/INDEX.json` var ve sha gömülüyle eşit, `python -c "import borsai"` başarılı, `git rev-parse HEAD` başarılı, pinli XU100 son tarihi ve takvim son günü (bilgi).

## 7. Aşamalar ve kabul kapıları

| Aşama | Teslim | Kabul kapısı | Tahmini iş |
|---|---|---|---|
| 0 Kurulum | §6 komutları; iskelet; `cargo test`/`npm test` boş geçer; `app/.gitkeep` kalkar | araç sürümleri raporda; `npm run tauri dev` pencere açar | 0.5 gün (1 oturum) |
| 1 predict + parite | `borsai_predict` crate; `gen_golden.py` + 16 altın dosya; U1–U6, U12, U33, U34 | U2 raporunda 16/16 model, maks \|Δ\| ≤ 1e-9 (beklenti < 1e-12); U6 7 kayıt × 16 model geçer | 2–3 gün (2–3 oturum) |
| 2 Ekranlar | Girdi formu, sonuç ekranı, senaryo modu, ayarlar, hakkında; f6 repo/elle; koşullu tavan şeridi ve eğrisi (§3g); U7–U11, U36, U37, U40 | U7 ekran görüntüsü (VEYAS girdileriyle 4 RET + 12 dolu); form denetimleri; SVG'ler | 3–4 gün (3–4 oturum) |
| 3 Dondur akışı | Kaynak belge kopyalama + MANIFEST, girdi belgesi yazıcı, Python denetim/freeze/cancel çağrıları, parite denetimi, komut bloğu; sicil ekranı ve arz sayfası (dondurulmuş S'ten koşullu görünüm); U27–U32, U38, U39 | `e2e_freeze_tmp_repo.sh` yeşil; asıl repoda `git status -- registry` değişmemiş | 1.5–2 gün (2 oturum) |
| 4 Doğruluk paneli | `scores.json` okuyucu (repo/gömülü), §3d render, bütünlük denetimi; koşullu skor bloğu (ayrı bölüm); U13–U26, U35 | vitest yeşil; n7/n12/n35 ekran görüntüleri; gerçek `scores/scores.json` (Faz 2B) ile n = 7 satır tablosu | 2 gün (2 oturum) |
| 5 Kişisel kayıtlar + cila | liste/sil/dışa aktar; rejim uyarısı; model kartı; DISCLAIMER; U21, U23, U28–U29 | tam koşu: `cargo test --workspace`, `npm test`, iki betik | 1 gün (1 oturum) |

Toplam: ~10–13 iş günü; Claude Code ile 11–13 oturum. Sonra Fable uygunluk denetimi (bu şartnameye karşı; K1–K4 ve U-tablosu).

Uygulayıcı kuralları: `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `docs/specs/`, `tests/` DEĞİŞMEZ (Faz 2B paralel; Faz 1 bekçileri). Uygulama kodu yalnız `app/`. Repo kökünde `.gitignore`'a `app/node_modules`, `app/src-tauri/target`, `app/dist` eklenmesi gerekir; bu tek satırlık değişiklik proje sahibine bırakılır (açık soru 5) ya da `app/.gitignore` ile çözülür (tercih: `app/.gitignore`, kök dosyaya dokunulmaz).

## 8. Açık konular (karar değil)

1. **BIST veri lisansı ve SPK çerçevesi (dağıtımdan önce).** Uygulama THB/THM verisinin kendisini gömmez; gömdüğü şey bu veriden türetilmiş model parametreleri, H99 eğitim aralıkları ve `scores.json` (arz başına gerçekleşen getiri/tavan etiketi içerir). Bu türev verinin üçüncü kişilere dağıtımı Borsa İstanbul veri lisansı açısından sorulmamıştır (AUDIT §2.10: repoda kanıt yok). Ayrıca çıktılar "tahmin/olasılık" dilinde de olsa ücretli ürün, SPK'nın yatırım danışmanlığı ve yatırım tavsiyesi düzenlemelerine dokunabilir; tek satırlık yer tutucu hukuki metin değildir. Kişisel kullanımda ikisi de ertelenir; dağıtım kararı öncesi hukuki görüş alınır.
2. **Yeni model_id'ler ve yeniden eğitim.** Model kümesi derleme anında INDEX'ten okunur; yeni bir model dondurulup INDEX'e girince uygulama yeniden derlenir (`build.rs` otomatik gömer), Rust'ta yeni bir `algorithm` ya da özellik listesi gerekiyorsa `borsai_predict` genişletilir ve altın vektörleri yeniden üretilir (`gen_golden.py` INDEX'i okur). Yeniden eğitim = yeni `model_id` (kural 5); eski model listede ve uygulamada kalır, kullanıcı gizleyebilir. Uygulama sürümü ile gömülü INDEX sha'sı "Hakkında"da görünür; kayıtlar hangi INDEX sha'sıyla üretildiğini taşır, bu yüzden eski kayıtlar eski kümeyle okunabilir kalır (çıktı üzerine yazılmaz).
3. **Faz 4 tavan-yolu modelleri.** `docs/specs_faz4/` şartnamesi yeni çıktı türleri (L ≥ j koşulunda D_h getiri dağılımı, p_up) tanımlayacak; uygulama bunları yalnız INDEX'te o türde model ve `scores.json`'da ilgili blok varken gösterir; şema bu belgeye §2.1/§2.3 eklemesiyle girer, altın vektörler genişletilir. Şimdilik yalnız yer ayrılmıştır (§3g).
4. **`scores.json` tazeliği.** Skorlar Python tarafında üretilir; uygulama gömülü kopyanın tarihini ve repo kopyasını ayrı gösterir. Otomatik güncelleme yok; "Faz 2B skorlamasını çalıştır" düğmesi bu şartnamede YOK (ağ ve sonuç verisi Python görevidir).

## Açık sorular (proje sahibine)

| # | Soru | Önerim |
|---|---|---|
| 1 | **f3 tanımı** (§3a.1): payda "taban arz, ek satış hariç"; köken sırası SOURCE_REPORTED → CALCULATED_FROM_SOURCE_TOTALS → boş; talep dağıtıma eşit basılmışsa türetme yok. Bu tanım kabul mü? | Kabul; H99 çoğunluğuyla uyumlu ve VEYAS kararıyla tutarlı. Onaylanınca `collection_rules`'a aynen girer; değişirse yalnız form metni değişir, model değişmez. |
| 2 | **Senaryo f6'sı**: repo modunda Python `borsai.market20` çağrısı + elle giriş (etiketli). Uygulama hiçbir koşulda XU100 indirmesin mi? | Evet, indirmesin. XU100 güncellemesi SPEC_MARKET20_V0 §4 prosedürüyle Python tarafında kalsın; uygulama bayatlığı `STALE_S0` ile açıkça göstersin. |
| 3 | **Aynı arza iki aşama için girdi dosyası adı**: `registry/inputs/<T>.json` üzerine yazılsın (her kayıt belgenin tamamını gömdüğü ve git geçmişi tuttuğu için bilgi kaybı yok) mı, yoksa `<T>.PB.json` ve `<T>.json` ayrı mı? | Ayrı dosya: `registry/inputs/<T>.PB.json` (talep öncesi) ve `<T>.json` (talep sonrası). `freeze` herhangi bir yolu kabul ediyor (`write_record(inputs_path)`); Faz 2B testleri `inputs/<T>.json` adını varsayıyorsa 2B ile uyumlanır. |
| 4 | **Bağımsız mod** (repo olmadan yalnız senaryo) istenen bir hedef mi? Ürünleşme yolu buysa Rust port kararı doğru; değilse aynı karar yine geçerli ama "bağımsız mod" ekranı sadeleşebilir. | Evet, korunsun: ileride ücretli ürün hedefi bunu gerektirir; maliyeti küçük (yalnız "repo yok" kapalı hâlleri). |
| 5 | **Kök `.gitignore`** için `app/node_modules`, `app/src-tauri/target`, `app/dist` satırları proje sahibi tarafından mı eklensin, yoksa `app/.gitignore` yeterli mi? | `app/.gitignore` yeterli; kök dosyaya dokunulmasın (uygulayıcı yalnız `app/` altına yazar). |

## Ekler

- `docs/app/ekler/scores_n7_sentetik.json`, `scores_n12_sentetik.json`, `scores_n35_sentetik.json`: U16–U26 için kurgusal fixture'lar (`borsai.scores/1`; SNTxx arzları gerçek değildir; backtest hücreleri `docs/MODELS.md`'deki `v1_5_h99` değerlerinin kopyasıdır; canlı satırlardaki sayılar rastgeledir).

Kaynak dosyalar [ÖLÇTÜM, bu oturum]: `borsai/predict.py`, `predict_hazard.py`, `predict_pb.py`, `predict_market20.py`, `features.py`, `horizons.py`, `survival.py`, `freeze.py`, `registry.py`, `market20.py`, `provenance.py`; `models/INDEX.json` ve 3 model JSON'u; `registry/inputs/NETGL.json`, `VEYAS.json`; `registry/records/NETGL/*.json`; `registry/source_docs/NETGL/MANIFEST.json`; `docs/specs/*`; `docs/MODELS.md`, `DATA_NOTES.md`, `ENV.md`, `SPEC_DEVIATIONS.md`; `docs/prompts/FAZ2B_OUTCOMES_SCORING.md`, `FAZ3_FABLE_APP_SPEC_EK1.md`; `tests/test_outcome_guard.py`, `test_faz1b_guardrails.py`, `test_freeze_records.py`, `test_predict.py`; eski repo `docs/fable_audit_20260921/AUDIT.md` §3d–§3e, §2.10.

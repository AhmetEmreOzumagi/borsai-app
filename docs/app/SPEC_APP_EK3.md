# SPEC_APP EK 3 — birikmiş model ve gösterim işleri uygulamada (ceiling hazard v1, TÜFE, Tavan serisi kartı, D1 sonrası, zaman-dışı panel, düşen arz kartı)

Görev: BORSAI_FAZ7_FABLE_APP_EK3_SPEC_20260927. Yazan: Fable, 2026-09-27. Uygulayıcı: Opus (Claude Code), yalnız `app/` altında, aşamalı (P1–P4). Bu ek `docs/app/SPEC_APP.md`'ye (SPEC_APP) ve `docs/app/SPEC_APP_EK2.md`'ye (EK 2) bölüm numaralarıyla atıf yapar; ikisinin metni değişmemiştir. Çelişkide üst belgeler (`CLAUDE.md`, `docs/specs/SPEC_SCORING.md`, `docs/specs_faz7/SPEC_HAZARD_V1.md` + `KARARLAR.md`, `docs/specs_faz5/SPEC_POST_D1_V0.md`, `docs/specs_faz7_c/SPEC_C_V0.md` + `KARARLAR_C.md`, `docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md`) kazanır; SPEC_APP ya da EK 2 ile bu ek çelişirse bu ek kazanır.

İşaretler: **[ÖLÇTÜM]** = bu oturumda dosyadan/komuttan (HEAD `f89e41a`, çalışma ağacında yalnız üç izlenmeyen belge); **[ÇIKARIM]** = yorum; **[KARAR]** = bağlayıcı karar, tek cümle gerekçeyle. Görev metnindeki 11 madde → bölüm: 1→§1, 2→§2, 3→§3, 4→§4, 5→§5, 6→§6, 7→§7, 8→§8, 9→§9, 10→§11, 11→§13. Kod yazılmadı; uygulama yolları salt okunur ölçüldü.

## Özet (12 satır)

1. Dört aşama, birbirinden bağımsız commit'lenebilir: **P1** = A (ceiling hazard v1 Rust portu + TÜFE tablosu) + D ("Tavan serisi" özet kartı); **P2** = B (D1 sonrası: `predict_post_d1` portu, "D1 sonrası" satırı, kayıt akışı); **P3** = E (Doğruluk sekmesinde "Zaman-dışı test (eski kohort)" paneli); **P4** = C (`fall_d10_v0` portu + "Düşüş (D10)" kartı; ancak (C) dondurulup INDEX'e girince).
2. v1 Rust portu `Kind::Hazard` içinde kalır (Python `freeze.model_kind` v1'i "hazard" sayar); `HazardParams` bir `v1: Option<V1Params>` bloğu alır (variant, üç sütunlu winsor, `deflator` pini, `regime {delta, live_value}`). f1r = f1 / (TÜFE / 100) **iki Decimal işlemi** 60 hanede (ilki kesin, ikincisi HALF_EVEN), sonra binary64 ve `f64::ln`; η_d = (γ_{g(d)} + δ·r) + β·z sırasıyla.
3. Yeni ret kodları birebir: `TUFE_MISSING`, `TUFE_NOT_PIT`, `TUFE_FILE_MISMATCH` (alan `tufe_index`), `REGIME_UNKNOWN` (alan `alloc_regime`); yeni uyarı `FEATURE_CLIPPED_TO_TRAINING_P05_P95`; yeni çıktı alanları `clipped_features`, `f1r_raw`, `tufe_index_used`, `regime_value_used`, `regime_source`. Toleranslar §2.7'de önceden yazılı; beklenti bit-eşit.
4. TÜFE: `data/raw/tuik/tufe_genel_2025_100.csv` derlemeye gömülür (Rust `tufe.rs`: `month_for`, `index_for` = m − 2 ve `release_date < T`, önek pini denetimi). Repo modunda repodaki dosya her tahminde yeniden okunur (yeni ay yeniden derleme istemez); bağımsız modda gömülü tablo (yeni ay = yeniden derleme; ekran bunu söyler). Ay eksikse real/pooled RET `TUFE_MISSING` ve dondur sihirbazı `TUFE_MONTH` engeliyle durur (Python `TufeMissing` kayıt yazmaz). Kayıtlı tahminlerde yalnız `model_inputs.tufe_index` / `tufe_refusal`.
5. Altın vektörler: `PINNED_MODEL_IDS` 19 → 23 (INDEX sırası; P2'de ayrı `PINNED_POST_D1_MODEL_IDS = ["post_d1_hazard_v0"]`; P4'te 27). U46 korunur: 16 eski dosya bayt-eşit, yeni girdi satırları yalnız yeni modellere `only` ile bağlanır. Kasa (SEALED) üyesinin hiçbir girdisi altın vektörlere girmez; açık küme girdileri `vault != SEALED` süzgeciyle ve kodsuz `case_id` ile girer.
6. "Tavan serisi" özet kartı Sonuç sayfasının başına gelir: öne çıkan model (kasa açılana kadar `ceiling_hazard_v0`, SPEC_HAZARD_V1 §5.5 ve KARARLAR K4), beklenen/medyan seri, P(≥ 3), P(≥ 5), P(10), en olası bozulma günü, j > 0'da koşullu satır; adaylar yan yana yakın dönem etiketiyle ("tolerans içinde" / "bozuyor" / "belirsiz"), "kasa: bekliyor", canlı n. Grup B tablosu ve eğrisi katlanır ayrıntı olur. Terazi dili aynen, üç renk, toplanmaz.
7. Öne çıkarma kuralı Rust'ta tek fonksiyondur (`featured_ceiling`): kasa bloğu (`oot_pre_h99_sealed`) yokken v0; varken §5.5 k1–k3 yalnız dosyadaki `verdict`, `ci95` ve yakın dönem etiketinden okunur (skor hesaplanmaz). Yakın dönem etiketi `scores.json`'daki yeni `near_era` bloğundan gelir (Ö1; blok yoksa "—").
8. D1 sonrası: `post_d1_hazard_v0.json` ve `INDEX_POST_D1.json` gömülür, parent/path sha'ları açılışta INDEX ile denetlenir; Rust `post_d1::predict_post_d1` (ofset = mevcut hazard doğrusal öngörücüsü; refactor `hazard::linear`); koşullu sekmede "D1 sonrası (post_d1_hazard_v0)" satırı yalnız resmi j ≥ 1 ve `registry/post_d1/<T>/` etkin kaydı varken, S yalnız kayıttan (U38 kalıbı); "D1 sonrası kayıt" sihirbazı: komut bloğu (bülten indirme Python'da) + `python -m borsai.freeze --post-d1` çağrısı + parite + commit/push/kanıt komutları + `T_open` metni.
9. Zaman-dışı panel: `scores/scores_oot.json` (`borsai.scores_oot/1`) üçüncü, ayrı renkli bölüm; hüküm metni "(zaman-dışı terazide)" ekiyle; `open != true` satır çizilmez (fail-closed); `oot_pre_h99_sealed` yokken "kasa: kapalı"; RETRO yalnız bilgi; D1 sonrası zaman-dışı alt bloğu ayrı ölçek.
10. (C): `Kind::Fall` (`family = "fall_d10_v0"`), V1.5 lojistik yolunun f1r + ln f3 + `add_sale` ile portu, `@ZERO` sabit başlık; "Düşüş (D10)" kartı SPEC_C_V0 §9 metinleriyle; öne çıkarma §5.5 (C) sürümü. Python referansı henüz yok: §8 şartnameden yazıldı ve **"referans: (C) dondurmasından sonra doğrulanır"** işaretlidir; P4 adım 0 "referans kilidi"dir.
11. Yeni U-testleri U53–U80; oturum tahmini P1 ≈ 5, P2 ≈ 2.5, P3 ≈ 1.5, P4 ≈ 3 (toplam ≈ 12). Önceden yazılmış beklenti §11: 23/23 parite, dört v1 dosyasında maks |Δ| < 1e-12, VEYAS girdileriyle 8 RET + 15 dolu.
12. Python tarafı ön koşulları (bu ekte DÜZELTİLMEDİ, §12): Ö1 `scores.json`'a `near_era` bloğu; Ö2 23 modelli `scores.json`; Ö3 (C) predict referansı ve `model_kind` adı; Ö4 `scores_oot.json`'a `oot_pre_h99_sealed`/`_all` (kasa açılışıyla).

---

## 0. Bağlam [ÖLÇTÜM, bu oturum]

- `models/INDEX.json` 23 giriş, sha256 `53265dd5d324…`; son dört giriş `ceiling_hazard_v1_clip` (`f3a14753…`), `_real` (`d81dad3d…`), `_pooled` (`e03e71e0…`), `_pooled@INF` (`7d7c9d1e…`). `INDEX_POST_D1.json` tek giriş `post_d1_hazard_v0` (`3f764026…`, `parent_sha256` = `ceiling_hazard_v0` sha `caa4dc86…`, `stage POST_D1`).
- `app/src-tauri/build_embed.rs: PINNED_MODEL_IDS: [&str; 19]`; `plan_embedding` fazlasını `ignored_model_ids`'e düşürür; `tests/build_embed.rs` yok sayılan listenin tam dört v1 kimliği olmasını bekler (J31). `commands/parity.rs: compare_record` INDEX'te olup gömülü olmayan modelleri `unsupported` listesine yazar (uyuşmazlık değil); `commands/registry.rs: record_row` bunları `unsupported_models` olarak listeler.
- `crates/borsai_predict`: `Kind` = hazard | km | ceiling_path | market20 | pb | linear | rule; `params::parse_hazard` özellik listesini `[] | [f1,f2,f3] | [pb1,pb2]` ile sınırlar (v1'in `[f1r,f2,f3]`'ü PARAMS_INVALID olurdu); `hazard::predict_hazard` yalnız f3 kırpar ve doğrusal öngörücüyü dışarı vermez; `output::HazardOutput` 8 alan; `Warning` sayısal `value/used/train_min/train_max` + metin `text_fields`; `dec.rs` `div_exact`, `div_round`, `to_f64`, `py_str`, `ln_to_f64` var; `survival::conditional(S, j)` var.
- v1 JSON'ları [ÖLÇTÜM]: `clip`: `features [f1,f2,f3]`, `preprocessing.winsor` üç sütun (f1 ham TL: p05 521 400 000, p95 4 887 992 000), `log_transform [f1]`, `regime` yok, `deflator` yok. `real`: `features [f1r,f2,f3]`, `deflator {series, month_rule T_MONTH_MINUS_2, file, file_sha256 3d61cbcf…, through_month 2026-08, unit, definition, append_rule, source}`, `regime` yok, `log_transform [f1r]`. `pooled`: real + `regime {column r_pre_equal, definition, delta 0.9111035924105239, penalized false, live_value 0, h99_value 0, pseudo_row_value 0, z_scored false, alloc_regime}`, winsor f1r p05 565 832 560.98 / p95 6 237 217 020.46. `pooled@INF`: `features []`, `preprocessing null`, `beta {}`, `deflator` YOK, `regime` VAR, `gamma` 3 değer. Hepsinde `family = "ceiling_hazard_v1"`, `variant`, `pseudo_rows {r 0, weight 0.5, z 0}`, `horizons` D1/D3/D5/D10 null başlıklar.
- `borsai/predict_hazard.py` [ÖLÇTÜM]: `_check_params` v1 dalı; `_linear_v1` sırası (compute_features → F3_MISSING → TÜFE → aralık uyarıları → kırpma → z → rejim → η); `_tufe_input` ret kuralları; `real_size` 60 haneli bağlam; `_V1_OUTPUT_KEYS` sırası; `REGIME_R = {PRE_20211111: 1, THRESH100_20211111: 1, EQUAL_DIST_20230330: 0}`. `borsai/tufe.py`: `month_for`, `index_for` (`release_date < T`), `prefix_sha256(through_month)`, `verify_pin`, `APPEND_COMMAND`. `borsai/specs.py: TUFE_PIN = {through_month 2026-08, prefix_sha256 3d61cbcf…}` (= bugünkü tam dosya sha'sı). CSV 82 veri satırı (2019-11 … 2026-08), sütunlar `month,index,release_date,bulletin_id,source_url,source_sha256`, LF, süreklilik denetimli.
- `borsai/predict_post_d1.py` [ÖLÇTÜM]: `predict_post_d1(params, parent, inputs, d1, *, path_params=None)`; `evaluate_d1` sırası ve kodları (H8/H9/H23/H24: öneksiz `D1_LIMIT_NA`, `D1_VOLUME_INVALID`, `D1_FIELD_INVALID`, `INPUT_SHARES_OFFERED`; kapsam dışı `not_applicable {code D1_NOT_CEILING}`; `D1_NOT_TRADED` PredictError); `curves` → `conditional_j1 {S_cond {"2".."10"}, p_break_next = 1.0 − S_cond[2], P_L_cond {"1".."10"}}`; `d1_features` alanları; `path_conditional` yalnız `path_params` verilince ve kaynak çıktı reddedilmemişse. `registry/post_d1/` bugün yok (H30); `scores/scores_post_d1.json` var (`models[].conditional_j1`, `n_retro 7`, hücre yok).
- `scores/scores_oot.json` [ÖLÇTÜM]: üst anahtarlar `schema_version borsai.scores_oot/1, scale OOT_PRE_H99, generated_at_utc, code, cohort_sha256, definitions, oot_pre_h99, post_d1, retro_info`. `oot_pre_h99`: `title, scale, n_member 135, n_open 71, n_sealed 64, n_out_of_scope 1, n_exposed_archive 4, n_exposed_codex 1, n_in_table 71, n_pending_membership 0, n_spk_corporate_action_seen 14 / _cohort_total 28, models[19]`. Model bloğu: `model_id, kind, scale, subset "oot_pre_h99", primary_cell, cells[], by_year[], by_regime[], rows[71], n_scored, n_refused, n_skipped, n_target_unavailable, n_pending, n_not_applicable_regime, n_oot_retro`. Hücre alanları SPEC_APP §2.3 + `label ∈ {birincil, keşif, ikincil}`, `subset`, `n_blocks`, `scale`, `n_live/n_late` (0). Satır: `ticker, d1, year, open (true), vault, class, class_evidence, status, cell_status, prediction, realized, rules, targets, regime_tags, record_id, listed_first_trading_date`. `post_d1.models[0]`: `scale OOT_PRE_H99_POST_D1_MACHINE_SEQUENCED`, `exposure_class`, `cells`, `rows`, sayaçlar, `retro_info`. `oot_pre_h99_sealed`/`_all` anahtarları YOK (kasa kapalı). `docs/SCORES_OOT.md` hükümleri "geçiyor (zaman-dışı terazide)" ekiyle yazar; sayfada üye kodu yoktur.
- `scores/scores.json` kartı: `card {training_n, training_cutoff, params_sha256_8, n_variants_same_data 20, n_runs_same_data}`; yakın dönem bloğu YOK (J30: skorlar yeniden üretilmedi). Yakın dönem etiketleri yalnız `docs/MODELS.md` Faz 7 bölümünde ve `experiments/log.jsonl` `near_era` alanında: clip **tolerans içinde** (−0.0011 [−0.0066, +0.0049]), real **bozuyor** (+0.0104 [+0.0028, +0.0183]), pooled **bozuyor** (+0.0289 [+0.0089, +0.0518]), n = 78 (22 ay).
- Ön uç: `render/results.ts` (Grup A/B/C, `isGroupB`, `groupB`), `render/ceiling.ts` (`renderConditional`, `renderStrip`, `condCurve`), `render/accuracy.ts` (`panel-backtest`, `panel-live`, `conditional`, `retroSection`), `render/card.ts` (`CardVM`, tek kart), `i18n/tr.ts` (`CODE_TEXT` 30 kod, `RESULTS`, `CEILING`, `COND`, `CARD`, `KIND_TEXT`, `VERDICT`, `ACCURACY.scalesNote` "İki terazi bağımsızdır…", `FREEZE.blockerText`). `commands/ceiling.rs: CeilingDisplay {j, rows[] {model_id, constant, S, P_L, expected_l, median_l, cond {S_cond, P_L_cond, p_break_next, expected_l, expected_remaining, median_l}}, price_hint}`. `commands/scores.rs` yalnız `scores.json`'u okur ve §2.3 bütünlük denetimini yapar. `commands/freeze.rs: preflight_in` engelleri `REPO_DIR · GIT_HEAD · INDEX_SHA · BORSAI_IMPORT`.
- Kayıtlar: 7 canlı kayıt 16 modelli, `model_inputs`'ta `tufe_index` yok; `tufe` bloğu yok. Dondurma sonrası yazılan her kayıt 23 model + `tufe` bloğu + `model_inputs.tufe_index/tufe_refusal` taşır (FREEZE_RAPOR §4, J26).
- "19" sabitleri [ÖLÇTÜM]: `tests/build_embed.rs` (ad ve 19), `tests/integrity.rs` (üç yerde), `crates/…/tests/golden.rs` (`golden_files_present`, `golden_parity` 19/19), `app/parity/test_gen_golden.py` (≥ 19), `tests/golden_unchanged.sh` (`OLD_MODELS` 16, `NEW_MODELS` 3), `bit_equal_floor.json` 19 taban.

---

## 1. Aşamalar ve sıra [KARAR]

Sıra P1 → P2 → P3 → P4; her aşama kendi commit'iyle biter ve tek başına yeşildir (`bash app/scripts/test.sh`). P3 P2'den bağımsızdır (P2 gecikirse P3 öne alınabilir). P4 yalnız (C) INDEX'e girdikten sonra başlar; öncesinde `build_embed` (C) kayıtlarını `ignored_model_ids`'e düşürür ve testler bunu bekler (J31 kalıbı). Gerekçe: A ve D aynı veri yolunu (v1 çıktıları) kullanır; B ayrı dizin ve ayrı akıştır; E yalnız okuyucu; C'nin referansı henüz yoktur.

| Aşama | İçerik | Dokunulan dosyalar (yalnız `app/`) | U-testleri | Altın vektör ekleri | Oturum |
|---|---|---|---|---|---|
| **P1** | A: v1 portu + TÜFE; D: Tavan serisi kartı; pinler 23 | `build_embed.rs` (PINNED 23, TÜFE gömme), `build.rs`, `src/embedded.rs`; crate: `params.rs` (V1Params), `hazard.rs` (`linear`, v1 dalı), `tufe.rs` (yeni), `error.rs` (kodlar), `output.rs` (v1 alanları, `Warning.bool_fields`), `lib.rs`; `commands/{models,predict,ceiling,freeze,parity,scores,config}.rs` (TÜFE kaynağı, `TUFE_MONTH` engeli, `featured_ceiling`, `near_era` okuyucu); `src/render/{results,ceiling,card}.ts`, `src/render/summary.ts` (yeni), `screens/results.ts`, `screens/settings.ts`, `types.ts`, `i18n/tr.ts`, `styles.css`; `parity/gen_golden.py`, `golden/*` (4 yeni + MANIFEST + patched), `bit_equal_floor.json`, `test_gen_golden.py`; testler `tests/{build_embed,integrity,stage2,stage3}.rs`, `crates/…/tests/{golden,coverage,dec_semantics,records_parity}.rs`, `app/tests/{results,ceiling,codes,summary}.test.ts`, `golden_unchanged.sh`, UI fikstürleri | U53–U63 | 4 dosya (≥ 600 satır/model), `_patched_params.jsonl` +12, `dec_cases.json` `real_size` bölümü, `tufe_cases.json` (yeni) | ≈ 5 |
| **P2** | B: post_d1 portu, gömme, "D1 sonrası" satırı, kayıt sihirbazı | `build_embed.rs` (ikinci dizin), crate `post_d1.rs` (yeni), `params.rs` (`Kind::PostD1`), `output.rs`; `commands/{models,post_d1,registry,ceiling,path,parity}.rs`; `render/{ceiling,registry,post_d1}.ts`, `screens/{results,registry}.ts`, `tr.ts`; `gen_golden.py` (`PINNED_POST_D1_MODEL_IDS`, sentetik D1 blokları), `golden/post_d1_hazard_v0.jsonl`; testler | U64–U70 | 1 dosya (≥ 220 satır), patched +8 | ≈ 2.5 |
| **P3** | E: zaman-dışı panel | `build_embed.rs` (`scores_oot.json` anlık kopya), `commands/scores_oot.rs` (yeni), `render/accuracy_oot.ts` (yeni), `render/accuracy.ts` (üç terazi notu), `screens/accuracy.ts`, `types.ts`, `tr.ts`, `styles.css` (`.panel-oot`), fikstürler `app/tests/fixtures/scores_oot/*` (sentetik), `app/tests/accuracy_oot.test.ts` | U71–U75 | — | ≈ 1.5 |
| **P4** | C: fall portu, "Düşüş (D10)" kartı, pinler 27 | `build_embed.rs` (PINNED 27), crate `fall.rs` (yeni), `params.rs` (`Kind::Fall`), `error.rs`, `output.rs`; `commands/{models,predict,parity,scores}.rs` (`featured_fall`); `render/{results,summary}.ts`, `tr.ts`; `gen_golden.py` (27, `FALL_IDS`), 4 altın dosya, `bit_equal_floor.json` +4; testler | U76–U80 | 4 dosya (≥ 560 satır/model), patched +10 | ≈ 3 |

Uygulayıcı kuralları SPEC_APP §7 ve EK 2 §6 ile aynı: yalnız `app/`; Python, `models/`, `scores/`, `registry/`, `data/` salt okunur; tolerans gevşetilmez; parite tutmuyorsa Rust düzeltilir; Python'da eksik bulunursa Ö-görevi olarak raporlanır (§12), düzeltilmez. Her aşamanın adım 0'ı: `gen_golden --check` yeşil, `bash app/scripts/test.sh` yeşil (bilinen tuzak: MANIFEST index sha; `docs/faz7/FREEZE_RAPOR.md` §9).

---

## 2. A — `ceiling_hazard_v1` ailesinin Rust portu

### 2.1 Tür ve dağıtım [KARAR]

- v1 modelleri `Kind::Hazard`'da kalır: Python `freeze.model_kind` `algorithm == discrete_time_hazard_logit_l2` → "hazard"; `RunResult.kind` `"hazard"`; ön uç `isGroupB` değişmez. Gerekçe: kayıt ve skor dosyaları bu türü yazar; yeni bir `kind` değeri okuyucuları kırar.
- `params::parse_hazard` genişler; `HazardParams`'a `pub v1: Option<V1Params>` eklenir:

```
V1Params { variant: String,                       // "clip" | "real" | "pooled"
           deflator: Option<DeflatorPin>,         // yalnız "f1r" in features
           regime: Option<Regime> }               // yalnız pooled ve pooled@INF
DeflatorPin { through_month: String, prefix_sha256: String }   // JSON deflator.through_month, deflator.file_sha256
Regime { delta: f64, live_value: u8 }             // JSON regime.delta, regime.live_value
```

### 2.2 Parametre denetimi (`_check_params` v1 dalının birebir karşılığı; sıra Python'daki gibi)

| Adım | Koşul | `PARAMS_INVALID` metni (Python) |
|---|---|---|
| 1 | `schema_version` | `SCHEMA_UNSUPPORTED` (mevcut) |
| 2 | KM ise `survival.S` 10 değer (mevcut) | mevcut |
| 3 | `algorithm == discrete_time_hazard_logit_l2` | "tavan modeli değil" |
| 4 | `v1 = params.family == "ceiling_hazard_v1"`. İzinli özellik listeleri: v1 → `[]`, `[f1,f2,f3]`, `[f1r,f2,f3]`; v1 değil → `[]`, `[f1,f2,f3]`, `[pb1,pb2]` | "desteklenmeyen özellik listesi …" |
| 5 | v1 ve `features` boş değil: `set(preprocessing.winsor) == set(features)` | "v1: kırpma sınırları üç özelliğin hepsi için değil" |
| 6 | v1 ve `"f1r" in features`: `deflator` sözlük | "v1: f1r var ama deflator bloğu yok" |
| 7 | v1 ve `regime` null değil: `delta` sayı (bool değil), `penalized == false`, `live_value ∈ {0, 1}` | "v1: regime bloğu geçersiz (delta, penalized, live_value)" |
| 8–11 | `day_groups`, `gamma` 3 / `set(beta) == set(features)`, ön işleme kolonları ⊆ features (features boş değilse), `reclose_rates` | mevcut metinler |

Rust okur: `deflator.through_month`, `deflator.file_sha256` (pin; §3), `regime.delta`, `regime.live_value`, `variant`. Başka v1 alanı (`pseudo_rows`, `lambda`, `training`, `spec`, `feature_definitions`, `code_version`, `runtime`, `h99_value`, `pseudo_row_value`, `z_scored`, `column`, `definition`, `alloc_regime`) OKUNMAZ. `preprocessing` null ise (`pooled@INF`) `prep = None`; features boş olduğundan adım 5 ve 11 atlanır [ÖLÇTÜM `_check_params`]. Not: Python `live_value not in (0, 1)` `True/False`'u da kabul eder; Rust `Value::Bool` için de kabul eder (aynı davranış; gömülü dosyalarda tamsayı 0).

### 2.3 Akış (`_linear_v1` birebir; `hazard::linear(p, inputs) -> LinOut`)

`LinOut { refused, warnings, clipped: Option<bool>, clipped_features: Option<Vec<String>>, f1r_raw: Option<f64>, tufe_index_used: Option<String>, regime_value_used: Option<u8>, regime_source: Option<&'static str>, z: Vec<(String, f64)>, lin: f64, eta: [f64; 10] }`. v0/PB/KM yolu bugünkü `predict_hazard`'ın gövdesidir, yalnız `linear`'a taşınır (bit-eşit; U46 ve mevcut altınlar bunu sınar). v1 yolu:

1. `features` boş değilse `compute_features(inputs)`; `FeatureFail::Refuse` → `refused` (mevcut); `Domain` → `DOMAIN_ERROR`. `f3 == None` → `F3_MISSING` / `total_demand_multiple` (metin v0 ile aynı).
2. `"f1r" in features` ise TÜFE girdisi (`_tufe_input`):
   - `inputs["tufe_refusal"]` var ve `null` değil → kod = değer ∈ {`TUFE_MISSING`, `TUFE_NOT_PIT`, `TUFE_FILE_MISMATCH`} ise o, değilse `TUFE_MISSING`; **RET**, alan `tufe_index`.
   - `inputs["tufe_index"]` yok / `null` / boş-kırpılmış metin / bool → `TUFE_MISSING`. Metin `dec::parse` ile Decimal'e çevrilemiyorsa → **`TUFE_MISSING`** (`INPUT_NOT_NUMERIC` DEĞİL). Sonlu değil ya da ≤ 0 → `TUFE_MISSING`. JSON sayı → `features::number_text` (Python `repr(float)` / `str(int)`).
   - `f1r_dec = real_size(f1, idx)`: `q = dec::div_exact(idx, 100, 60)` (her zaman kesin: 100'e bölme üs kaydırmasıdır; `Inexact` gelirse `DOMAIN_ERROR`, beklenmez); `f1r_dec = dec::div_round(f1, q, 60)` (HALF_EVEN, 60 anlamlı hane; Python `_REAL_CTX` tek yuvarlama). `values["f1r"] = f1r_dec.to_f64()` (doğru yuvarlanmış). `f1r_raw = values["f1r"]`; `tufe_index_used = dec::py_str(idx)` (girdi metninin Decimal ayrıştırılmış hâli: `"134.75"` → `"134.75"`, `"134.750"` → `"134.750"`, `"1.3475E2"` → `"134.75"`).
   - Değilse (`clip`) `values = {f1, f2, f3}` binary64 (mevcut yol).
3. `range_warnings` **ham** değerlerle (`feature_ranges` dosya sırası; f1r 2025 TL biriminde).
4. Kırpma, `prep.columns` sırasıyla: `w = winsor[col]` varsa ve `!(p05 ≤ x ≤ p95)` → `used = py_min(py_max(x, p05), p95)`, `clipped_features.push(col)`, uyarı `FEATURE_CLIPPED_TO_TRAINING_P05_P95 {feature: col, value: x, used}`. `clipped = !clipped_features.is_empty()`. (v0'ın `F3_CLIPPED_TO_TRAINING_P05_P95` kodu v0'da aynen kalır; v1'de f3 için de yeni kod.)
5. `z = z_vector(prep, values)` (mevcut: winsor → ln → z; f1r `log_transform`'da).
6. `features` boşsa (pooled@INF) 1–5 atlanır; `clipped = None`, `clipped_features = None`, `z = []`.
7. Rejim (`regime` bloğu varsa; @INF dahil): `inputs` sözlüğünde **`alloc_regime` anahtarı varsa** (değeri `null` olsa bile) etiket → r: `PRE_20211111 → 1`, `THRESH100_20211111 → 1`, `EQUAL_DIST_20230330 → 0`; başka her değer (`null`, `""`, bilinmeyen metin, sayı) → **RET `REGIME_UNKNOWN`**, alan `alloc_regime`. Anahtar yoksa `r = live_value`, `regime_source = "LIVE_VALUE"`; varsa `"ALLOC_REGIME_INPUT"`. `regime_value_used = r`. `dr = delta * (r as f64)`.
8. `lin = py_sum(beta[c] * z[c] for c in prep.columns)` (boş → 0.0). `eta[d] = (gamma[g(d)] + dr) + lin` (rejim varsa; ikili toplama sırası aynen) ya da `gamma[g(d)] + lin` (rejim yoksa).

Ret anında `LinOut`'un o ana kadar dolan alanları korunur (Python `out` sözlüğü): `TUFE_*` reddinde `clipped = None`, `clipped_features = None`, `f1r_raw`/`tufe_index_used` yok, `warnings` boş; `REGIME_UNKNOWN` reddinde `clipped`, `clipped_features`, `f1r_raw`, `tufe_index_used` ve aralık/kırpma uyarıları dolu, `regime_*` yok. `predict_hazard` = `linear` + `sigmoid(eta)` + `curves`.

### 2.4 Çıktı (`HazardOutput` eki; `to_json` anahtar sırası Python `_V1_OUTPUT_KEYS` sırası)

Mevcut 8 anahtardan (`model_id, hazard, S, P_L, P_close_ceiling, clipped, warnings, refused`) sonra **yalnız v1 ailesinde ve yalnız `LinOut`'ta dolu olanlar**: `clipped_features` (liste | null), `f1r_raw` (f64), `tufe_index_used` (metin), `regime_value_used` (0 | 1 tamsayı), `regime_source` (metin). v0/PB/KM çıktıları bayt-eşit kalır (anahtar eklenmez). `clipped_features` v1'de her zaman yazılır (features boşken `null`; `TUFE_*` reddinde `null`); `f1r_raw`/`tufe_index_used` yalnız TÜFE girdisi geçerliyken; `regime_*` yalnız rejim adımı geçilmişse.

`Warning`'e `bool_fields: Vec<(String, bool)>` eklenir (P2'nin `WARN_D1_LOCK_INCONSISTENT` alanları için; P1'de boş kalır). `to_json` sırası: `code, message, text_fields…, bool_fields…, feature, horizon, value, used, train_min, train_max` (Python `_warn(code, message, **extra)` ek alanları çağrı sırasıyla yazar; parite sırayı karşılaştırmaz).

### 2.5 Ret ve uyarı kodlarının birebirliği (T-2 eki)

| Kod | Tür | `field` / alanlar | Arayüz metni (`tr.ts`) |
|---|---|---|---|
| `TUFE_MISSING` | RET | `tufe_index` | "TÜFE endeksi (T'nin ayı − 2) yok; bu model deflatörsüz tahmin vermez, imputasyon yok. {neden}" — neden: `T_UNKNOWN` → "ilk işlem günü girilmedi; ay belirlenemez"; ay eksik → "TÜFE {ay} tabloda yok; ay eklenince görünür ({kaynak})"; sayı değil / ≤ 0 → "TÜFE endeksi sayı değil ya da pozitif değil" |
| `TUFE_NOT_PIT` | RET | `tufe_index` | "TÜFE {ay} yayımı ({yayım günü}) ilk işlem gününden önce değil (bekçi; kural gereği olamaz)" |
| `TUFE_FILE_MISMATCH` | RET | `tufe_index` | "TÜFE tablosunun önek pini modelin pinine uymuyor (eski satır, temel yıl ya da zincirleme değişmiş): yeni veri sürümü gerekir" |
| `REGIME_UNKNOWN` | RET | `alloc_regime` | "tahsis rejimi etiketi bilinmiyor; eski kohort kaydı kohort satırındaki ALLOC_REGIME'i verir (canlı kayıtta bu anahtar olmaz)" |
| `F3_MISSING`, `INPUT_*`, `DIVISION_BY_ZERO` (miras) | RET | mevcut | mevcut; F3 metnine ek cümle yok |
| uyarı `FEATURE_CLIPPED_TO_TRAINING_P05_P95` | uyarı | `feature`, `value`, `used` | "{feature} eğitim p05/p95 sınırına kırpıldı: kullanılan {used}" |
| uyarı `OUT_OF_TRAINING_RANGE` (miras) | uyarı | mevcut | mevcut (f1r için birim notu: "2025 TL") |

`ModelCode` birliği ve `CODE_TEXT` dört kod + bir uyarıyla genişler (U8 `codes_have_text`).

### 2.6 `regime_source` ve rejim girdisinin kaynağı [KARAR]

Uygulama `alloc_regime` anahtarını **hiçbir zaman kendisi üretmez**: senaryo ve canlı tahminde girdi sözlüğünde anahtar yoktur (r = `live_value` = 0; Python J6 ile aynı); anahtar yalnız eski kohort kayıtlarının `model_inputs`'unda gelir ve kayıt paritesinde olduğu gibi Rust'a verilir. Gerekçe: canlı rejim EQUAL_DIST'tir ve etiket kohort dosyasının işidir (SPEC_HAZARD_V1 §3.3, §9). Girdi formunda rejim alanı YOKTUR.

### 2.7 Karşılaştırma toleransları (tests/common `cmp_output` eki; ÖNCEDEN yazılı)

| Alan | Kural | Beklenti |
|---|---|---|
| `hazard[]`, `S[]`, `P_L[]`, `P_close_ceiling[]` | \|Δ\| ≤ 1e-9 (mevcut) | bit-eşit (aynı toplama sırası, aynı libm) |
| `clipped` | birebir (null ↔ null) | |
| `clipped_features` | liste birebir (sıra dahil: `prep.columns` sırası); null ↔ null; anahtar var/yok birebir | |
| `f1r_raw` | \|Δ\| ≤ 1e-9 · max(1, \|beklenen\|) (göreli; değer 1e8–1e10 mertebesinde) | bit-eşit (iki taraf da doğru yuvarlanmış dönüşüm) |
| `tufe_index_used` | metin birebir | |
| `regime_value_used` | tamsayı birebir | |
| `regime_source` | metin birebir | |
| `warnings` | (kod, `feature`) çok kümesi; sayısal `value/used` \|Δ\| ≤ 1e-9; `message` hariç anahtar kümeleri eşit | |
| `refused.code`, `refused.field` | birebir | |
| anahtar kümesi | v1 çıktısında Python'da bulunan her anahtar Rust'ta da bulunur ve tersi (özellikle `f1r_raw`/`regime_*`'nin ret durumundaki yokluğu) | |

Rapor `target/parity_report.json` 23 model; `bit_equal_floor.json`'a 4 taban ilk yeşil koşunun değeriyle yazılır (kural: taban bilinçli yazılır; beklenti §11).

---

## 3. TÜFE tablosu uygulamada

### 3.1 Kaynak seçimi [KARAR]

| Mod | Kaynak | Ne zaman okunur | Yeni ay nasıl görünür |
|---|---|---|---|
| **Repo modu** (varsayılan) | `<repo_root>/data/raw/tuik/tufe_genel_2025_100.csv` | **her tahminde** (dosya küçük; bayat kopya tutulmaz) | `build_tufe_csv.py --append-month` ile dosyaya satır eklenir (Python tarafı, PROVENANCE §11a); uygulama yeniden derlenmez, sonraki "Tahmin et" yeni ayı görür |
| **Bağımsız mod** | derlemeye gömülü kopya (`build.rs`: `TUFE_CSV: &str = include_str!(…)`; derleme anındaki repo dosyası) | açılışta bir kez | yalnız yeniden derlemeyle; Ayarlar ve Hakkında ekranı "TÜFE tablosu {son ay}'a kadar gömülü (derleme {git_head})" yazar |

Gerekçe: Python kayıt yolu dosyayı her seferinde okur (`tufe.load()`); repo modunda aynı davranış pariteyi korur ve aylık eklemeyi derlemeden ayırır; bağımsız modda başka kaynak yoktur ve uygulama ağa çıkmaz (kullanıcı dosyası seçeneği açık soru 3).

### 3.2 Rust `tufe.rs` (crate içinde, saf)

Python `borsai/tufe.py`'nin portu; yalnız okuma ve denetim:

```
parse(raw: &str) -> Result<TufeTable, TufeError>      // sütunlar birebir; LF; ay sürekliliği (2019-11'den, boşluksuz);
                                                         // index pozitif Decimal (kırpılmamış metin); release_date ay+1'in ≥ 3'ü;
                                                         // bulletin_id rakam, source_sha256 64 hex, source_url https://
month_for(T: &str) -> String                             // yıl-ay − 2; "2026-09-25" → "2026-07", "2026-10-01" → "2026-08", "2020-01-06" → "2019-11"
index_for(T, &table) -> Result<TufeRow, TufeRefusal>     // ay yok → TUFE_MISSING{month}; !(release_date < T) → TUFE_NOT_PIT{month}
prefix_sha256(&table, through_month) -> Result<String, TufeRefusal>   // başlık + through_month satırına kadar (dahil) baytların sha256; ay yoksa TUFE_FILE_MISMATCH
verify_pin(&table, &DeflatorPin) -> Result<(), TufeRefusal>           // prefix_sha256 != pin → TUFE_FILE_MISMATCH
```

`TufeError` (biçim/süreklilik) Python'da istisnadır (kayıt yazılmaz); uygulamada: tablo **geçersiz** sayılır, deflatörlü modellere `tufe_refusal = TUFE_FILE_MISMATCH` verilir ve Ayarlar/Hakkında'da kırmızı satır ("TÜFE tablosu ayrıştırılamadı: {neden}"); öteki modeller etkilenmez (bütünlük bandı DEĞİL; gerekçe: TÜFE dosyası model dosyası değildir, INDEX ile pinlenmez; fail-closed yalnız deflatörlü hücrelerde). `dec::parse` ile endeks metni; tarih karşılaştırması ISO metin sırası (`release_date < T`, Python ile aynı).

### 3.3 Tahminde TÜFE girdisinin hazırlanması (`commands/predict.rs`, `tufe_for_inputs`) [KARAR]

Python'da `predict_hazard` saftır; `freeze.tufe_for_record` girdiyi hazırlar (J5, J26). Uygulamada aynı ayrım: `predict_all` çağrılmadan önce Rust `tufe_for_inputs(T: Option<&str>, table: &TufeStatus, pins: &[DeflatorPin]) -> TufeInputs { tufe_index: Option<String>, tufe_refusal: Option<String>, info: TufeInfo }` girdi sözlüğüne `tufe_index` ya da `tufe_refusal` **ancak INDEX'te deflatörlü model varsa** ekler (yoksa anahtar yok; kayıt biçimi ve eski altınlar aynen). Kurallar (`freeze.tufe_for_record` sırası):

1. T (`first_trading_date` form alanı; senaryoda da bu alan) boş → `tufe_refusal = TUFE_MISSING`, `reason = T_UNKNOWN`.
2. Tablo geçersiz (§3.2) → `TUFE_FILE_MISMATCH`.
3. `index_for(T)`: ay yok → `TUFE_MISSING` (ay adı ve `APPEND_COMMAND` metni `info`'da; §3.4); yayım T'den önce değil → `TUFE_NOT_PIT`.
4. Her deflatörlü modelin pini `verify_pin` → tutmayan varsa `TUFE_FILE_MISMATCH` (Python: tek ret kodu bütün deflatörlü hücreler için).
5. Aksi hâlde `tufe_index = row.index` (kaynak metni, kırpılmamış).

`TufeInfo {source: EMBEDDED|REPO, path, file_sha256, through_month (son ay), month, index, release_date, bulletin_id, refusal, reason}` sonuç ekranında Grup B'nin (ve Tavan serisi kartının) altında tek satır: "TÜFE: {ay} = {endeks} (yayım {gün}; kaynak {repo dosyası | gömülü}; pin ✓)" ya da ret nedeni. Senaryo modunda kullanıcı TÜFE değerini **elle giremez** (imputasyon yok; SPEC_HAZARD_V1 §9); T'yi değiştirerek ay değiştirir.

### 3.4 Ay eksikse [KARAR]

- **Senaryo/sonuç ekranı:** real ve pooled sütunları `RET · TUFE_MISSING` bloğu; blok metni "TÜFE {YYYY-MM} tabloda yok. Bülten yayımlanınca (m + 1'in 3'ü 10:00) Python tarafında eklenir:" + kopyalanabilir komut (Python `tufe.APPEND_COMMAND` metni birebir, Rust'ta sabit `TUFE_APPEND_COMMAND`; vitest U57 metni Python kaynağıyla karşılaştırır). clip ve @INF etkilenmez (clip TÜFE istemez; @INF deflatörsüz).
- **Dondur sihirbazı (SPEC_APP §3e adım 1):** yeni engel kodu **`TUFE_MONTH`**: repo modunda INDEX'te deflatörlü model varsa ve `index_for(T)` `TUFE_MISSING` verirse ön koşullar DUR (Python `freeze.TufeMissing` kayıt yazmaz; uygulama Python'u çağırmadan aynı sonucu gösterir). Metin: "TÜFE {ay} dosyada yok; kayıt yazılamaz. Önce ayı ekleyin:" + komut. `TUFE_NOT_PIT` ve `TUFE_FILE_MISMATCH` engel DEĞİLDİR (Python kaydı yazar, hücreler RET; sihirbaz sarı bilgi satırı). T boş → engel değil (mevcut sarı uyarı; Python `T_UNKNOWN` reddi yazar).
- Parite adımı (`compare_record`): kayıttaki `model_inputs.tufe_index` / `tufe_refusal` Rust'a **olduğu gibi** verilir; uygulama TÜFE'yi yeniden aramaz (U38 ilkesi; kayıt esastır).

### 3.5 Gömme ve pin (`build_embed.rs`, `models::verify`)

- `plan_embedding` `data/raw/tuik/tufe_genel_2025_100.csv` yolunu da plana koyar; dosya yoksa derleme kırılır (INDEX'te deflatörlü model varken) — deflatörlü model yoksa `TUFE_CSV: Option<&str> = None`.
- Açılışta (`models::verify` sonrası, ayrı adım `tufe::status`): gömülü tablo `parse`, her deflatörlü modelin pini `verify_pin`. Sonuç `TufeStatus { valid, source, through_month, file_sha256, pin_ok: Vec<(model_id, bool)> }` `AppInfo`'ya eklenir (Hakkında ekranı). Pin tutmuyorsa bütünlük bandı YOK; ilgili modeller `TUFE_FILE_MISMATCH` ile reddeder (§3.2 gerekçesi). Repo modunda `TufeStatus` her tahminde repodaki dosyadan yeniden kurulur; Ayarlar ekranındaki repo doğrulaması "TÜFE son ay {ay}, pin ✓/✗" satırı ekler.
- `tufe_cases.json` (yeni; `gen_golden.py --tufe-cases` üretir): `month_for` 8 örnek (§3.2 + yıl sınırları `2026-01-15 → 2025-11`, `2026-02-01 → 2025-12`), `index_for` (var olan ay; eksik ay; `release_date == T` → `TUFE_NOT_PIT`; `release_date = T − 1 gün` → geçer), `prefix_sha256` gerçek dosyada `2026-08` ve `2019-11` için (Python `tufe.prefix_sha256`), sentetik satır eklenmiş kopyada pinin tuttuğu ve bir eski satırın değiştiği kopyada tutmadığı; `parse` retleri (CRLF, eksik ay, üç ondalık haneli bozuk endeks, yayım günü 2'si). Rust `cargo test -p borsai_predict --test tufe_semantics` (U56).

---

## 4. Altın vektörler ve pinler

### 4.1 `PINNED_MODEL_IDS` 19 → 23 (P1), + `PINNED_POST_D1_MODEL_IDS` (P2), → 27 (P4) [KARAR]

- `build_embed.rs`: `PINNED_MODEL_IDS: [&str; 23]` = INDEX'in ilk 23 kaydı sırasıyla (son dört: `ceiling_hazard_v1_clip`, `_real`, `_pooled`, `_pooled@INF`); sıra kuralı EK 2 §3.5 aynen (INDEX sırası, ek sona). `ignored_model_ids` boşalır; `tests/build_embed.rs` beklentisi "boş" olur (P4'e kadar (C) INDEX'e girerse yeniden "tam dört (C) kimliği"; J31 kalıbı).
- P2: ikinci dizin `models/INDEX_POST_D1.json` (`INDEX_POST_D1_SCHEMA = borsai.model_index/1`) ve `PINNED_POST_D1_MODEL_IDS: [&str; 1] = ["post_d1_hazard_v0"]`; `EMBEDDED_POST_D1_MODELS`, `BUILD_INFO.index_post_d1_sha256`. Açılış denetimi (`models::verify_post_d1`): dosya sha = INDEX_POST_D1 `sha256`; INDEX_POST_D1 girişinin `parent_sha256` = INDEX'teki `ceiling_hazard_v0.sha256` = gömülü dosyanın sha'sı; JSON `parent.sha256` aynı; `path_secondary.sha256` = INDEX'teki `ceiling_path_v0.sha256`; `check_params(post, parent, path)` geçer. Tek uyuşmazlık → `INTEGRITY_FAILED / POST_D1_PARENT_MISMATCH` (U41 kalıbı; gerekçe: ofset bit-eşitliği parent kopyasının bozulmamasına dayanır).
- P4: `PINNED_MODEL_IDS: [&str; 27]` (son dört: `fall_d10_v0_h99`, `_pooled`, `_addsale`, `_pooled@ZERO`; sıra INDEX'ten okunur, adlar SPEC_C_V0 §2).
- "19" sabitleri (§0 listesi) INDEX'ten sayılır ya da 23/27'ye çekilir; `integrity.rs`'te `EMBEDDED_MODELS.len() == PINNED_MODEL_IDS.len()`. `records_parity`: eski 7 kayıt "16/16 + kayıtta yok: 7"; dondurma sonrası kayıtlar 23/23 (kayıttaki `model_inputs.tufe_index`/`tufe_refusal` Rust'a aynen geçer).

### 4.2 `gen_golden.py` genişlemesi (P1)

- `PINNED_MODEL_IDS` 23; `V1_IDS = (clip, real, pooled, pooled@INF)`; `DEFLATOR_IDS = (real, pooled)`. `PREDICT_SOURCES` + `borsai/tufe.py` (9 dosya; `predict_sources_unchanged` 9 sha; `predict_hazard.py` sha zaten K'da yeniden pinlendi).
- **[KARAR] Mevcut 392 satır (395 market20) dört yeni modelde de koşar, girdileri değişmeden:** `tufe_index` anahtarı olmadığından real/pooled bu satırlarda `TUFE_MISSING` ret eder (geçerli kapsama: ret yolu), clip ve @INF tahmin verir. Gerekçe: eski 16 dosyanın `inputs` alanı değişemez (U46); TÜFE'li satırlar yalnız yeni modellere bağlanır.
- **Yeni girdi satırları, `only=V1_IDS`** (Faz 4 kalıbı; `edge_specs` sonuna `v1_specs(add)`):
  - **H99 + TÜFE (99):** `data/training_table.csv`'den yalnız girdi sütunları (mevcut `h99_cases`) + `first_trading_date` → `tufe_index = tufe.index_for(T, table).index` (metin); f3'süz 2 arz `F3_MISSING` (TÜFE'den önce). Etiket `h99_tufe:<i>`.
  - **Açık küme + TÜFE + rejim (71):** `registry/oot/cohort_pre_h99.csv` yalnız `vault != SEALED` satırlar (`_assert_open` bekçisi: SEALED satır istenirse `SystemExit`; kod yazılmaz, basılmaz); girdiler `registry/oot/inputs/<T>.json` → `registry.model_inputs`; `tufe_index` üyenin T'sinden; `alloc_regime` = satırın `ALLOC_REGIME` etiketi. `case_id` = `ceiling_hazard_v1_pooled/oot/0007` biçiminde **kodsuz** (sıra numarası); `inputs` sözlüğünde ticker yok (`model_inputs` ticker taşımaz [ÖLÇTÜM]). Bu satırlar pooled'da r = 1 yolunu (PRE/THRESH üyeler) ve r = 0'ı (EQUAL) sınar; MANIFEST `oot_open_rows: 71`, `oot_sealed_rows_excluded_by_guard: true`. Test `test_gen_golden.py::test_no_sealed_code_in_golden` (kohortun SEALED kodlarını tek tek aramaz; kasa kodlarının kümesini sha ile karşılaştıran Faz 6 bekçi yardımcısını çağırır).
  - **Canlı (7 sicil + TÜFE):** `registry/inputs/*.json` + `tufe_index` (T'den; VEYAS T = 2026-09 → 2026-07); anahtarsız (r = 0).
  - **Uç durumlar (her biri ≥ 2 satır):** her v1 winsor sütunu için `p05 / 2` ve `2 · p95` (f1 için `ipo_size_tl` ile, f1r için `ipo_size_tl` ve `tufe_index` ile; f2/f3 mevcut kalıp) → `FEATURE_CLIPPED` + `OUT_OF_TRAINING_RANGE`; `tufe_index` ∈ {yok, `null`, `""`, `"  "`, `"abc"`, `"0"`, `"-1"`, `"inf"`, `"nan"`, `true`} (hepsi `TUFE_MISSING`); `tufe_index` biçimleri `"134.75"`, `"134.750"`, `"1.3475E2"`, `"134,75"` (ret), sayı `134.75` (JSON number → `repr`); `tufe_refusal` ∈ {`TUFE_NOT_PIT`, `TUFE_FILE_MISMATCH`, `TUFE_MISSING`, `"BOGUS"` (→ `TUFE_MISSING`)} `tufe_index` doluyken; `alloc_regime` ∈ {`PRE_20211111`, `THRESH100_20211111`, `EQUAL_DIST_20230330`, `null`, `""`, `"UNKNOWN"`, `1`} (son dördü `REGIME_UNKNOWN`; @INF dahil); f3 boş + `tufe_index` var (F3 önce); f1 için kırpma ve TÜFE birlikte (f1r kırpılır, f1 aralık dışı olmaz).
  - Toplam ≥ 99 + 71 + 7 + 40 = 217 yeni satır → **≥ 600 satır/model** (392 + 217; anahtar tekrarları birleşir).
- `derived_tags`: `FEATURE_CLIPPED_TO_TRAINING_P05_P95` için `feature` anahtarı; `regime:<r>` ve `regime_source:<src>`; `tufe:<code>`; bu etiketler 19 eski modelin çıktısında oluşmaz.
- `dec_cases.json`'a `real_size` bölümü (eski bölümler bayt-eşit): (`size_tl`, `tufe_index`) çiftleri → `f1r_dec` metni (`str(Decimal)`) ve `float`: `("2233000000", "134.75")`, `("2233000000", "13.736052")`, `("521400000", "1E2")`, `("1", "3")` (60 haneli periyodik), `("12345678901234567890123456789", "7")`, `("2233000000", "134.750")`, k-katı değişmezliği (`("4466000000", "269.5")` aynı float). Rust `dec_semantics real_size` (U56).
- `bit_equal_floor.json`: 4 yeni taban ilk yeşil koşunun `bit_equal_rows`'u; 19 eski taban değişmez.
- MANIFEST: `model_ids` 23, `rows` 23 anahtar, `n_cases`, `patched_rows` 31 → 43, `predict_sources_sha256` 9 dosya, `models_index_sha256` `53265dd5…`, yeni `tufe_prefix_sha256` (`TUFE_PIN`), `oot_open_rows`. `coverage_exemptions` ekleri: `REGIME_UNKNOWN` yalnız `pooled`/`pooled@INF` dosyalarında; `TUFE_*` yalnız real/pooled; `FEATURE_CLIPPED` f1 yalnız clip, f1r yalnız real/pooled; @INF'te kırpma yok (özellik yok).

### 4.3 Yamalı parametreler (`_patched_params.jsonl` eki, ilk 31 satır bayt-eşit)

| Etiket | Model | Yama | Beklenen |
|---|---|---|---|
| `v1:features:pb` | `ceiling_hazard_v1_clip` | `features = ["pb1","pb2"]` (+ beta anahtarları) | `PARAMS_INVALID` ("desteklenmeyen özellik listesi") |
| `v1:winsor:missing_f2` | `clip` | `preprocessing.winsor.f2` silinir | `PARAMS_INVALID` (kırpma sınırları üç özellik için değil) |
| `v1:deflator:missing` | `real` | `deflator` silinir | `PARAMS_INVALID` |
| `v1:regime:penalized` | `pooled` | `regime.penalized = true` | `PARAMS_INVALID` |
| `v1:regime:live_value` | `pooled@INF` | `regime.live_value = 2` | `PARAMS_INVALID` |
| `v1:regime:delta_bool` | `pooled` | `regime.delta = true` | `PARAMS_INVALID` |
| `v1:regime:live_value_1` | `pooled@INF` | `regime.live_value = 1` | tahmin; anahtarsız girdiyle `regime_value_used = 1` (η'ya δ eklenir) |
| `v1:features:f1r_no_family` | `real` | `family` silinir | `PARAMS_INVALID` (v1 olmayan dalda `[f1r,f2,f3]` yasak) |
| `v1:gamma:2` | `clip` | `gamma = [0.1, 0.2]` | `PARAMS_INVALID` |
| `v1:schema` | `pooled` | `schema_version = borsai.model/2` | `SCHEMA_UNSUPPORTED` |
| `v1:reclose:missing` | `real` | `reclose_rates` silinir | `PARAMS_INVALID` |
| `v1:winsor:tight_f3` | `clip` | `winsor.f3 = {p05: 2.83, p95: 2.85}` (NETGL f3 = 2.84 içeride) | tahmin; `clipped false`, `clipped_features []` |

Hepsi Python'da ölçülür (`gen_golden` üretirken); toplam yamalı 43.

### 4.4 Parite ve "desteklenmiyor" durumunun kalkması

- `compare_record`: gömülü küme 23 olunca v1 hücreleri karşılaştırılır; `unsupported` yalnız INDEX'te olup gömülü olmayan modeller için kalır (P4'e kadar (C) INDEX'e girerse onlar). Sicil ekranı metni "uygulamada henüz olmayan: {n}" kendiliğinden boşalır (aşama 3 kuralı: desteklenen küme gömülü veriden).
- `records_parity` (U6): dondurma sonrası yazılan ilk canlı kayıt 23 hücre; `tufe_index` metni kayıttan; `tufe` bloğu okunmaz (bilgi olarak sicil ekranında gösterilir: ay, endeks, yayım, pin durumu).
- `build_embed` beklentisi: `ignored_model_ids == []` (P1–P3); (C) dondurulup INDEX'e girerse P4'e kadar `== [4 (C) kimliği]`; P4 sonrası `[]`.

---

## 5. D — "Tavan serisi" özet kartı (Sonuç sayfasının başı)

### 5.1 Yer ve ilişki [KARAR]

Sonuç ekranında mod bandının ve rejim uyarısının hemen altında, **Grup A'dan önce**, tam genişlikte tek kart (`<section class="summary summary-ceiling">`). Grup B (S_k tablosu, eğri, P(L = k) çubukları, P_close, hazard'lar) yerinde kalır ama **katlanır** (`<details>`; varsayılan kapalı; başlık "Ayrıntı: Grup B — tavan serisi tabloları ve eğrileri"). Kart özet, Grup B ayrıntıdır; kart Grup B'den başka bir sayı üretmez: bütün değerler Rust `ceiling_display` satırlarından (`CeilingRow`, `CondView`) ve `scores.json` / `scores_oot.json` okuyucularından gelir (U25). Masaüstü genişliği (≥ 1100 px) hedeflenir; mobil düzen yok. Gerekçe: proje sahibinin isteği "kaç gün tavan" tahmininin ilk bakışta görünmesi; sayfa yoğunluğu Grup B'nin katlanmasıyla düşer, bilgi kaybolmaz.

### 5.2 İçerik (her satır bir veri kaynağına bağlı)

`ceiling_display` genişler: `CeilingRow`'a `mode_l: usize` (en olası l: `argmax_l P_L[l]`, l = 0..10; eşitlikte en küçük l; görüntüleme türevi, kayda yazılmaz) ve `CondView`'a `mode_l` (koşullu `P_L_cond` üzerinde, l ≥ j) eklenir; `S[2], S[4], S[9]` doğrudan okunur (P(≥ 3), P(≥ 5), P(10)). Yeni Rust komutu **`ceiling_summary(runs, j, ipo_price_tl, official) -> CeilingSummary`** yalnız derler (kendi hesap yapmaz: `ceiling_display_value` + `featured_ceiling` + `near_era`/`oot` okuyucuları):

```
CeilingSummary {
  featured: { model_id, params_sha256, reason: "VAULT_CLOSED_V0_DEFAULT" | "RULE_5_5" | "RULE_5_5_NONE_ELIGIBLE_V0" },
  j, j_source: "OFFICIAL" | "HYPOTHETICAL" | "NONE",
  rows: [ { model_id, role: "FEATURED" | "CANDIDATE" | "RULE" | "CONSTANT",
            refused: null | {code, field}, expected_l, median_l, mode_l, p_ge3, p_ge5, p_10,
            cond: null | { p_break_next, expected_remaining, median_l, mode_l, s_cond_3, s_cond_5, s_cond_10 },
            near_era: null | { label, diff, ci95, n, n_blocks, comparator, subset },     // scores.json models[].backtest.near_era (Ö1)
            vault: { status: "CLOSED" | "OPEN", verdict: null | string, diff, ci95, n },  // scores_oot.json oot_pre_h99_sealed (yoksa CLOSED)
            live: { n_scored: null | int, verdict: null | string } } ],
  tufe: TufeInfo | null }
```

Kart satırları (üstten alta):

1. **Başlık satırı:** "Tavan serisi — kaç gün tavan?" · mod rozeti (SENARYO turuncu / RESMİ KAYIT mavi; resmi görünümde kaynak "kayıt {dosya}, params sha {ilk 8}") · "öne çıkan: `{model_id}` ({neden metni})".
2. **Öne çıkan modelin özeti (büyük yazı):** "Beklenen seri **{expected_l:.1f} gün** · medyan **{median_l} gün**" — tooltip formüller (CEILING.expectedLTip/medianLTip).
3. **Olasılıklar:** "P(en az 3 gün) **%{S_3}** · P(en az 5 gün) **%{S_5}** · P(10 gün) **%{S_10}**" (0 ondalık; tooltip ham binary64).
4. **En olası bozulma günü:** `mode_l = 0` → "D1'de tavan kapanışı yok (P = %{P_L[0]})"; 1 ≤ `mode_l` ≤ 9 → "D{mode_l+1} (seri {mode_l} gün; P = %{P_L[mode_l]})"; `mode_l = 10` → "10 gün boyunca tavan (sağdan sansürlü; P = %{P_L[10]})".
5. **Koşullu satır (yalnız j > 0):** "Seri {j} gün sürdü ({j_source: gözlenen | varsayımsal}) → yarın bozulma **%{p_break_next}** · beklenen kalan **{expected_remaining:.1f} gün** · P(≥ 5 | ≥ j) %{s_cond_5} · P(10 | ≥ j) %{s_cond_10}"; tanımsızsa (S_j = 0, j ≥ 10) "—" ve COND.undefinedAll metni. j = 0'da satır yok. Kullanıcı beyanı bu satıra hiçbir koşulda girmez; beyan resmi verinin önündeyse satır "resmi kapanış bekleniyor" (U52).
6. **Adaylar tablosu (yan yana, toplanmaz):** satır sırası: öne çıkan (★) → v1 adayları INDEX sırasıyla (`clip`, `real`, `pooled`) → kural satırları (`pooled@INF`, `ceiling_hazard_v0@INF`, `base_km_expanding`, `base_km_last10`) → `her zaman tavan` (gri, sabit). PB modelleri (`pb_ceiling_v0`, `@INF`) f3 boşken listede; f3 doluyken katlanır ("PB aynası: f3'süz tahmin"). Sütunlar: model · beklenen · medyan · P(≥3) · P(≥5) · P(10) · [j>0: yarın bozulma] · **yakın dönem (geçmiş veri testi)** · **zaman-dışı (kasa)** · **canlı sicil**. Üç terazi sütunu üç renk sınıfıyla (`.scale-backtest` lacivert-gri, `.scale-oot` yeşil-gri, `.scale-live` kehribar) ve başlık altında tek satır: "üç terazi ayrıdır; toplanmaz". RET eden model satırı sayılar yerine `RET · {kod}` (sütun kaybolmaz).
7. **Terazi sütunlarının metinleri:**
   - yakın dönem: `near_era.label` aynen ("tolerans içinde" / "bozuyor" / "belirsiz") + tooltip "{comparator}'a karşı fark {diff} [{ci95}], n = {n} ({n_blocks} ay); backtest, tasarıma maruz"; blok yoksa "—" ve tooltip "scores.json'da yakın dönem bloğu yok (Ö1)"; v0 ve kurallar için "—" (tanım gereği).
   - zaman-dışı: `vault.status == CLOSED` → "kasa: bekliyor"; OPEN → dosyadaki `verdict` + " (zaman-dışı terazide)" (yalnız geçiyor/geçemiyor'da ek; "yetersiz örnek"/"ayırt edilemiyor" ekle yazılır: "ayırt edilemiyor (zaman-dışı terazide)").
   - canlı: `live.n_scored < 10` → "n = {n}: hüküm yok"; ≥ 10 → dosyadaki verdict; `scores.json` yoksa "—".
8. **TÜFE satırı** (§3.3 `TufeInfo`; yalnız INDEX'te deflatörlü model varsa).
9. **Alt satır:** "Ayrıntı: Grup B tablosu ve eğrisi ▾" bağlantısı (details'ı açar) · sabit `DISCLAIMER` (SPEC_APP §4 metni aynen; kart kendi kopyasını taşımaz, ekranın altındaki tek satır yeter — kartın içinde ek bir "yatırım tavsiyesi değildir" satırı YOK, iki kez yazmak sadeleşmeye aykırıdır) · senaryo filigranı `SENARYO` sütun başlıklarında (RESULTS.watermark; resmi görünümde yok).

Sözcükler: "tahmin", "olasılık", "tavan serisi", "basit kural", "fark", "%95 aralık", "ayırt edilemiyor"; yasak liste SPEC_APP §4 aynen ("kesin", "garanti", "kazandırır", "al/sat", "hedef fiyat", "sinyal", tek başına "doğruluk %"). "Geçiyor" yalnız dosyadaki `verdict`'ten (U19).

### 5.3 Öne çıkarma kuralı (`featured_ceiling`; SPEC_HAZARD_V1 §5.5 + KARARLAR K4) [KARAR]

```
fn featured_ceiling(scores: Option<&ScoresDoc>, oot: Option<&ScoresOotDoc>) -> Featured
  sealed = oot?.oot_pre_h99_sealed                                   // yoksa → ("ceiling_hazard_v0", VAULT_CLOSED_V0_DEFAULT)
  for c in [clip, real, pooled] (INDEX'te varsa):
      k1 = sealed.cell(c, primary: S RPS vs base_km_expanding).verdict == "geçiyor"        // dosyadaki metin; aralık 0'ın altında demektir
      k2 = sealed.cell(c, S RPS vs ceiling_hazard_v0).ci95[1] < 0
      k3 = scores.near_era(c).label != "bozuyor"                                              // blok yoksa k3 = false (uygun sayılmaz)
      eligible if k1 && k2 && k3; key = (round(model_value, 3), order[c])   // order clip < real < pooled
  featured = min(eligible) else ("ceiling_hazard_v0", RULE_5_5_NONE_ELIGIBLE_V0)
```

Uygulama hiçbir skor hesaplamaz: yalnız dosyadaki `verdict`, `ci95`, `model_value` ve etiketleri karşılaştırır (U25 beyaz listesine `featured_ceiling` eklenir; test: fonksiyon `bootstrap`/`mean` çağırmaz). Kural K4 gereği hiçbir model listeden kalkmaz; öne çıkan yalnız kartın ilk satırıdır. `MODELS.md`'deki insan kararıyla uyum Python tarafının testidir (§12 Ö5). Kasa açılıp `oot_pre_h99_sealed` yazılmadan sonuç `VAULT_CLOSED_V0_DEFAULT`'tur; bugünkü etiketlerle (real ve pooled "bozuyor") kasa açıldıktan sonra yalnız `clip` uygun olabilir [ÇIKARIM].

### 5.4 Tel kafes (metin; masaüstü ≥ 1100 px; senaryo modu, j = 2 gözlenmiş varsayımsal örnek — sayılar biçim içindir, ölçüm değildir)

```
┌ Tavan serisi — kaç gün tavan?                                  SENARYO · öne çıkan: ceiling_hazard_v0 (kasa kapalı; §5.5 v0) ┐
│                                                                                                                              │
│   Beklenen seri  4.1 gün      Medyan  3 gün        En olası bozulma günü: D4 (seri 3 gün; P = %21)                           │
│   P(en az 3 gün) %62   ·   P(en az 5 gün) %41   ·   P(10 gün) %14                                                           │
│   Seri 2 gün sürdü (gözlenen) → yarın bozulma %19 · beklenen kalan 2.6 gün · P(≥ 5 | ≥ 2) %55 · P(10 | ≥ 2) %19              │
│                                                                                                                              │
│   model                      beklenen  medyan  P≥3   P≥5   P10   yarın   yakın dönem (backtest)   zaman-dışı (kasa)   canlı │
│   ★ ceiling_hazard_v0         4.1       3      %62   %41   %14   %19     —                        kasa: bekliyor       n = 7: hüküm yok │
│     ceiling_hazard_v1_clip    4.0       3      %60   %39   %13   %20     tolerans içinde          kasa: bekliyor       n = 0: hüküm yok │
│     ceiling_hazard_v1_real    3.6       3      %55   %33   %10   %23     bozuyor                  kasa: bekliyor       n = 0: hüküm yok │
│     ceiling_hazard_v1_pooled  3.2       2      %49   %27    %7   %27     bozuyor                  kasa: bekliyor       n = 0: hüküm yok │
│     kural · v1_pooled@INF     3.4       3      %52   %30    %8   %25     —                        kasa: bekliyor       n = 0: hüküm yok │
│     kural · v0@INF            3.9       3      %58   %38   %12   %21     —                        kasa: bekliyor       n = 7: hüküm yok │
│     kural · KM genişleyen     3.9       3      %58   %41   %14   %22     —                        kasa: bekliyor       n = 7: hüküm yok │
│     kural · KM son 10         3.4       3      %51   %31   %10   %26     —                        kasa: bekliyor       n = 7: hüküm yok │
│     her zaman tavan          10.0      10     %100  %100  %100    %0     —                        —                    —     │
│   ▸ PB aynası (f3'süz tahmin): pb_ceiling_v0, pb_ceiling_v0@INF                                                              │
│   üç terazi ayrıdır; toplanmaz · yakın dönem: H99, ilk işlem ≥ 2024-01-01, n = 78 (22 ay), tasarıma maruz                    │
│   TÜFE: 2026-07 = 132.31 (yayım 2026-08-03; kaynak repo dosyası; pin ✓)                                                     │
│   ▸ Ayrıntı: Grup B — S_k tablosu ve eğrisi, P(L = k), P_close, hazard                                                       │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Resmi sicil görünümünde (arz sayfası) aynı kart, S vektörleri yalnız dondurulmuş kayıttan (U38); başlık "RESMİ KAYIT · kaynak: kayıt {dosya}, params sha {ilk 8}"; kayıt 16/19 modelliyse v1 satırları "kayıt bu modeli içermiyor (kayıt INDEX'ten eski)".

### 5.5 `scores.json` yakın dönem bloğu — okuyucu sözleşmesi (Ö1) [KARAR]

```
models[].backtest.near_era = { "schema_version": "borsai.near_era/1", "scale": "backtest_near_era",
   "label": "tolerans içinde" | "bozuyor" | "belirsiz", "comparator": "ceiling_hazard_v0", "metric": "RPS",
   "subset": "first_trading_date >= 2024-01-01", "diff": f64, "ci95": [lo, hi], "n": int, "n_blocks": int,
   "tolerance": 0.010, "source": "experiments/log.jsonl near_era; backtest.near_era_cell" }
```

Uygulama: blok yoksa "—"; `schema_version` farklıysa "desteklenmeyen yakın dönem bloğu (sürüm X)" ve k3 = false; `label` üç değer dışında ise fail-closed (kart yerine bütünlük hatası, SPEC_APP §2.3 kalıbı). Gerekçe: etiket yalnız Python'un yazdığı dosyadan gelir; uygulama `experiments/log.jsonl` okumaz (kural 4'ün günlüğü skor dosyası değildir) ve etiketi kendisi türetmez.

---

## 6. B — D1 sonrası (`post_d1_hazard_v0`)

SPEC_POST_D1_V0 §8 ve §11-16'nın "EK 3 gerekir" maddeleri; ret kodları errata H23/H24 (öneksiz), ofset H25 (`linear_predictor`), kayıt akışı H28–H47.

### 6.1 Gömme ve tür

- İkinci dizin ve pin §4.1. `Kind::PostD1` (`as_str = "post_d1"`; Python `freeze.model_kind` → "post_d1" [ÖLÇTÜM]); `model_kind`: `algorithm == "discrete_time_hazard_offset_logit_l2"` denetimi `HAZARD_ALGORITHM`'den sonra. `predict_all` (listeleme öncesi) bu türü **çalıştırmaz** (Python `run_model` de ERROR verir); ayrı komut `predict_post_d1`.
- `params::parse_post_d1(p, parent, path) -> PostD1Params` = Python `check_params` birebir sırada: schema → `algorithm`/`stage` → `parent.model_id`/`parent.algorithm` → kopya `gamma`/`beta`/`preprocessing_id` JSON-eşitliği → miras `feature_ranges` (parent'ın her anahtarı için eşit) → `updated_days == [2..10]` → `delta` anahtar kümesi `{d1_lock, d1_turnover}` ve sonlu → `d1_preprocessing.columns` sıralı alt küme → düşen kolonun `delta == 0.0` → `clip.d1_turnover.p05 ≤ p95` sonlu → aktif kolonların `mean`/`std` (std > 0) → `path_params` varsa `algorithm`, `model_id == ceiling_path_v0`, `path_secondary.model_id`, `survival_model_sha256 == parent.sha256`. Metinler Python'daki gibi (yamalı satırlar ilk hatayı sınar).

### 6.2 `post_d1::predict_post_d1(params, parent: &HazardParams, inputs, d1: &Value, path: Option<&PathParams>) -> PostD1Output`

1. `base = hazard::linear(parent, inputs)` (§2.3 refactor; v0 yolu). Çıktı iskeleti: `{model_id, stage: "POST_D1", refused: null, not_applicable: null, warnings: base.warnings, clipped: base.clipped, hazard/S/P_L/P_close_ceiling/conditional_j1/path_conditional/d1_features: null}`. `base.refused` → `refused`, dön.
2. `evaluate_d1(d1, inputs["shares_offered"])` sırası (H9): `f = d1.fields_raw` (yoksa boş sözlük); `raw(name)` = `parse_decimal(f[name], required=false)`; ret → `None`. `close`, `trade_count` None/≤ 0 → **`PredictError(D1_NOT_TRADED)`** (`run_model` → `status ERROR`, `refusal.code = D1_NOT_TRADED`); `upper_limit` None/≤ 0 → RET `D1_LIMIT_NA` / `upper_limit`; `!dec::eq(close, upper)` → `not_applicable {code: D1_NOT_CEILING}` (ret değil; `refused null`); `volume` None/≤ 0 → RET `D1_VOLUME_INVALID` / `volume`; `low`, `open`, `high` sırasıyla None/≤ 0 → RET `D1_FIELD_INVALID` / `<ad>`; `shares_offered` `parse_decimal(required)` reddi ya da ≤ 0 → RET `INPUT_SHARES_OFFERED` / `shares_offered` (ana model önce reddettiği için bu dal yalnız `evaluate_d1` birim testinde ulaşılır; kapsama muafiyeti). `lock = dec::eq(low, upper)`; `consistency = {open_at_U, high_at_U, close_at_U}` (Decimal değer eşitliği); `lock && !all` → `WARN_D1_LOCK_INCONSISTENT` (**`bool_fields`** üç anahtar, bu sırayla); `d1.half_day` truthy tamsayı → `WARN_D1_HALF_DAY`; `d1.halt_flag` → `WARN_D1_INTRADAY_HALT`; `special_trade_volume` > 0 → `WARN_D1_SPECIAL_TRADES` (`text_fields`: `special_trade_volume = py_str(special)`, `volume = py_str(volume)`). `ratio`: `dec::div_exact(volume, shares, 60)` kesinse o (üs kuralı), değilse `dec::div_round(volume, shares, 60)` (HALF_EVEN, 60 hane); `turnover_ln = dec::ln_to_f64(ratio)` (pb1 kuralı: kesin → binary64 → `f64::ln`; Python 60 haneli `Decimal.ln()` → `float`; beklenen \|Δ\| ≤ 5e-15, EK 1 tablosu).
3. `warnings += values.warnings`; `OUT_OF_TRAINING_RANGE` `d1_lock`, `d1_turnover` sırasıyla (`feature_ranges` anahtarı varsa; ham değer, kırpma öncesi); `d1_transform`: `used = py_min(py_max(raw, p05), p95)`, `u[c] = (x[c] − mean[c]) / std[c]` `columns` sırasıyla; kırpıldıysa `D1_TURNOVER_CLIPPED_TO_TRAINING_P05_P95 {feature: d1_turnover, value, used}`.
4. `shift = py_sum(delta[c] * u[c] for c in columns)`; `hazard[0] = sigmoid(eta[0])`; `hazard[d−1] = sigmoid(eta[d−1] + shift)` d = 2..10 (δ = 0'da özel dal yok; `+ 0.0` bit-eşit, H2). `S = survival`, `P_L = p_streak`, `P_close = p_close(S, parent.r_a, parent.r_b)`.
5. `conditional_j1`: mevcut `survival::conditional(S, 1)` → `S_cond` **metin anahtarlı sözlük** `{"2": S[1]/S[0], …, "10"}`, `p_break_next = 1.0 − S_cond["2"]` (H10; `conditional.p_break_next` ile aynı ifade: `1.0 − s[1]/s[0]`), `P_L_cond` `{"1": …, "10"}` (`p_l_cond[l]`, l ≥ 1). Bit-eşitlik: Python `conditional_weights` `(S0[t] − S0[t+1]) / S0[1]` = Rust `p_streak(s)[t] / s[0]` (aynı ifadeler; U37 zaten sınar).
6. `d1_features = {d1_lock: int, d1_turnover_ratio: py_str(ratio), d1_turnover_ln, clipped: bool, d1_turnover_used, z: {columns…}, ceiling_close_D1: 1, lock_consistency: {…bool}}`.
7. `path` verilmişse: `po = path::predict_path(path, inputs)`; `po.refused` ya da `limit_path` yoksa `null`; değilse `path::conditional(path, {po.to_json() with "S": S}, 1, [d1.fields_raw.close metni])` (mevcut komut; kayıt yolu gibi JSON alır).

Çıktı `to_json` anahtar sırası Python sözlüğü: `model_id, stage, refused, not_applicable, warnings, clipped, hazard, S, P_L, P_close_ceiling, conditional_j1, path_conditional, d1_features`. `RunResult.kind = "post_d1"`; `status`: `refused` → REFUSED; `not_applicable` → **`NOT_APPLICABLE`** (yeni durum; Python `run_post_d1_model` `refusal = out["refused"] or out["not_applicable"]`); aksi PREDICTED.

### 6.3 Ret ve durum kodları (T-2 eki; H23 öneksiz)

| Kod | Tür | `field` | Arayüz metni |
|---|---|---|---|
| `D1_NOT_TRADED` | hata (kayıt yazılmaz) | — | "D_1 işlem görmemiş (sözleşme sayısı ya da kapanış yok / ≤ 0): D_1 henüz oluşmadı; POST_D1 kaydı yazılamaz" |
| `D1_LIMIT_NA` | RET | `upper_limit` | "D_1 THM üst limiti yok ya da ≤ 0 (tavan etiketi NA)" |
| `D1_NOT_CEILING` | kapsam dışı (`not_applicable`) | — | "D1 tavanda kapanmadı: D1 sonrası model bu arzda tanımlı değil (ret değil; kırılma sonrası görünüm için tavan yolu sekmesi)" |
| `D1_VOLUME_INVALID` | RET | `volume` | "TOPLAM ISLEM ADEDI boş/≤ 0 iken sözleşme sayısı > 0 (veri tutarsızlığı; bülten satırı elle incelenir)" |
| `D1_FIELD_INVALID` | RET | `low` \| `open` \| `high` | "D_1 THB {alan} alanı yok ya da ≤ 0 (veri tutarsızlığı)" |
| `INPUT_SHARES_OFFERED` | RET | `shares_offered` | "arz edilen pay yok / sayı değil / ≤ 0 (el değiştirme paydası)" |
| `F3_MISSING`, `INPUT_*` (miras) | RET | mevcut | mevcut |
| uyarı `WARN_D1_HALF_DAY` | uyarı | — | "D1 yarım gün: el değiştirme kısa seansta ölçüldü (eğitimde örnek yok)" |
| uyarı `WARN_D1_INTRADAY_HALT` | uyarı | — | "D1'de gün içi geçici durdurma (eğitimde örnek yok)" |
| uyarı `WARN_D1_SPECIAL_TRADES` | uyarı | `special_trade_volume`, `volume` (metin) | "özel işlem bildirimi hacmi {special_trade_volume} > 0; hacim düzeltilmedi (resmi toplam {volume})" |
| uyarı `WARN_D1_LOCK_INCONSISTENT` | uyarı | `open_at_U`, `high_at_U`, `close_at_U` (bool) | "en düşük = üst limit ama açılış/en yüksek/kapanış üst limite eşit değil; bülten satırı elle incelenmeli" |
| uyarı `D1_TURNOVER_CLIPPED_TO_TRAINING_P05_P95` | uyarı | `d1_turnover`, `value`, `used` | "el değiştirme ln(hacim/pay) eğitim p05/p95 sınırına kırpıldı: kullanılan {used}" |
| `POST_D1_PARENT_MISMATCH` | bütünlük | model_id | INTEGRITY bandı: "D1 sonrası modelin ebeveyn/tavan yolu kopyası INDEX ile uyuşmuyor" |

Karşılaştırma (tests/common `cmp_output`, çıktıda `stage == "POST_D1"` dalı): `refused`/`not_applicable` `code`+`field` birebir; `d1_features.d1_turnover_ratio` metin birebir; `d1_turnover_ln`, `d1_turnover_used`, `z.*` \|Δ\| ≤ 1e-9; `hazard/S/P_L/P_close` \|Δ\| ≤ 1e-9 (beklenti: `ln` payı ≤ 5e-15 → hazard'da ≤ 1e-15); `conditional_j1.S_cond/P_L_cond` sözlük anahtar kümesi birebir, değerler ≤ 1e-12; `p_break_next` ≤ 1e-12; `path_conditional` EK 2 §3.3 koşullu kuralları; `d1_features.lock_consistency`/`d1_lock`/`clipped`/`ceiling_close_D1` birebir; uyarılar (kod, `feature`) çok kümesi + `bool_fields`/`text_fields` birebir.

### 6.4 Altın vektörler (`golden/post_d1_hazard_v0.jsonl`, ≥ 220 satır) [KARAR]

- Sonuç dosyası okunmaz; **D1 blokları sentetiktir** (seed 20260922, `gen_golden.py: synth_d1(rng, price)`): `upper_limit` = `snap(price) × 1.10` fiyat adımına FLOOR (EK 2 limit yolu ile aynı metin; Python `predict_path.limit_path`'in `C_1`'i), kapanış = üst limit (P = 0.85) ya da altında; kilitli (low = upper, P = 0.8) ya da `low = upper − adım`; `open`/`high` = upper (kilitliyken 1 satırda tutarsız); `volume` ∈ [shares × 1e-4, shares × 0.6] (log-tekdüze); `trade_count` ∈ [1, 50 000]; `half_day`/`halt_flag` 0 (her biri 2 satırda 1); `special_trade_volume` 0 (2 satırda > 0). Gerekçe: gerçek D1 alanları sonuç verisidir (`data/outcomes`, SESSIONS), `gen_golden` bunları okumaz; parite girdinin gerçekliğine değil aritmetiğe bağlıdır.
- Satırlar: 99 H99 + 7 sicil + 80 rastgele (mevcut girdi tabanları) × sentetik D1; uçlar (≥ 2'şer): `D1_NOT_TRADED` (`trade_count` "0"/boş; `close` boş) → `expected.error.code`; `D1_LIMIT_NA`; `D1_NOT_CEILING` (kapanış ≠ limit); `D1_VOLUME_INVALID`; `D1_FIELD_INVALID` × 3 alan; kilit tutarsız; yarım gün; durdurma; özel işlem; `d1_turnover` p05 altı ve p95 üstü (kırpma + aralık dışı); `F3_MISSING` (VEYAS tabanı); `path_params` verilmiş (varsayılan) ve verilmemiş (2 satır, `path_conditional: null`); ana model uyarıları (f1 aralık dışı) ile birlikte.
- `expected` = `predict_post_d1(params, parent, inputs, d1, path_params=ceiling_path_v0)` çıktısı; satır `"d1": {...}` ve `"path_params": true|false` alanlarını taşır. Yamalı (`_patched_params.jsonl`, +8): `parent.gamma[0]` değişik → `PARAMS_INVALID`; `delta` eksik anahtar; `updated_days = [2..9]`; `d1_preprocessing.columns = [d1_turnover, d1_lock]` (sıra); `clip.p05 > p95`; `stage = "PRE"`; `path_secondary.model_id = "x"` (path verilince); `schema_version` → `SCHEMA_UNSUPPORTED`.
- `PINNED_POST_D1_MODEL_IDS = ("post_d1_hazard_v0",)`; MANIFEST `post_d1_rows`, `models_index_post_d1_sha256`; `bit_equal_floor.json` 1 taban (ilk koşu); U46: eski dosyalar bayt-eşit (bu satırlar yalnız post_d1 dosyasında).

### 6.5 Gösterim: koşullu sekmede "D1 sonrası" satırı [KARAR]

- **Resmi sicil görünümü (arz sayfası):** `registry/post_d1/<T>/*.json` (şema `borsai.post_d1_record/1`, `record_type = PREDICTION`, iptal edilmemiş) okunur (`commands/post_d1.rs: post_d1_records(ticker)`). Etkin kayıt yoksa satır yok, şeritin altında gri "D1 sonrası kayıt yok". Varsa **en erken** etkin kayıt (recorded_at_utc) varsayılan, diğerleri sekme; etiket "birincil POST_D1 kaydı seçimi skorlamada yapılır (T_open ve push kanıtı)"; her kayıt için push kanıtı göstergesi mevcut kalıpla ("kanıt dosyası var: {sha} {created_at}" / "push kanıtı bulunamadı").
- Satır adı "D1 sonrası (post_d1_hazard_v0)"; `S` yalnız kaydın `models[post_d1_hazard_v0].output.S`'inden (`status PREDICTED`); koşullu sekmedeki tablo ve eğriye **ek satır** (renk `colorOf`), `S_cond`, "yarın bozulma", koşullu beklenen/medyan aynı Rust `ceiling_display` ile (j seçici aynı; `S_cond[k]/S_cond[j]` = `S_k/S_j`). **Yalnız j ≥ 1** (resmi ya da varsayımsal); j = 0'da satır gizli ve not "D1 sonrası model j ≥ 1'de tanımlı". Kayıttaki hücre `REFUSED` → satır `RET · {kod}`; `NOT_APPLICABLE` → "D1 tavanda kapanmadı: model tanımlı değil". Kaynak satırı: "kaynak: registry/post_d1/{T}/{dosya}, params sha {ilk 8}; D_1 {session_date}; bültenler sha {thb ilk 8} / {thm ilk 8}". `path_conditional` doluysa "Getiri (koşullu)" sekmesinde ek kart "D1 sonrası S ile tavan yolu (ikincil)" (`PathConditional` JSON'u kayıttan; hesap yok).
- **Tavan serisi kartında (§5):** resmi görünümde etkin POST_D1 kaydı varsa ve j ≥ 1 ise adaylar tablosuna "D1 sonrası (post_d1_hazard_v0)" satırı (rol `POST_D1`), koşullu sütunlar dolu, koşulsuz sütunlar (beklenen, P≥3 …) yine S'ten (bilgi; `S_1` ana modelden).
- **Senaryo modunda** satır yok ("senaryoda D1 bülteni yok; D1 sonrası tahmin yalnız resmi kayıttan"). Kullanıcı D1 alanlarını elle girmez (açık soru 5).
- **Doğruluk paneli:** `scores/scores_post_d1.json` (`borsai.scores_post_d1/1`; `models[].conditional_j1 {rows, cells, denominator, descriptive, n_*}`) `accuracy.ts`'te var olan koşullu blok okuyucusuyla ("Koşullu skorlar" bölümü, ölçek `live_post_d1`), kart alanları H43 adlarıyla (`training_last_session_date` + anlam metni, `spec_training_cutoff`; "kesim" sözcüğü yazılmaz). Bugün `n_retro 7`, hücre yok → yalnız `retro_info` (n'e girmez). `scores_post_d1.json` gömülmez (repo modu; yoksa "dosya yok").

### 6.6 "D1 sonrası kayıt" sihirbazı (Sicil ekranı; yalnız repo modu) [KARAR]

Kayıt yazıcı Python'dur (`borsai.freeze --post-d1`); bülten indirme Python'dur (`borsai.outcomes update`); uygulama ağa çıkmaz, bülten okumaz, etiket üretmez. Adımlar (her adımın çıktısı ekranda kalır):

1. **Ön koşullar** (`post_d1_preflight`): repo modu; git; `models/INDEX_POST_D1.json` sha = gömülü; `models/INDEX.json` sha = gömülü; arzın `registry/records/<T>/` altında etkin, `ceiling_hazard_v0` hücresi PREDICTED bir kaydı var (yoksa DUR: "listeleme öncesi kayıt yok → SKIPPED_POST_D1: NO_PRE_LISTING_RECORD"); `data/outcomes/<T>.csv` var ve h = 1 satırı `OK` ise D_1 gösterilir; değilse "D_1 henüz repoda değil: adım 2'yi çalıştırın". `T_open` Python'dan: `<python> -c "from borsai import registry as r, outcomes as o; import sys; print(r.t_open(sys.argv[1], o.load_calendar()).isoformat())" <D_1>` (repo modu, ağ yok); hata → `CALENDAR_NOT_AVAILABLE` metni. Kalan süre (yerel saat, yalnız bilgi: "yerel saat kanıt değildir; sınır push kanıtının created_at'idir").
2. **Bülten ve sonuç güncellemesi — yalnız komut bloğu** (uygulama çalıştırmaz; ağ):
   ```bash
   cd <repo_root>
   .venv/bin/python -m borsai.outcomes update --through <D_1>
   git add data/ && git commit -m "BORSAI_OUTCOMES_<D_1>: bulletins and outcomes through D_1"
   ```
   "Çalıştırdım, yeniden denetle" düğmesi adım 1'i yeniler (h = 1 OK olmalı; `sequence_guard` gereği commit edilmiş olmalı: `GIT_OPTIONAL_LOCKS=0 git status --porcelain -- data registry/post_d1` boşsa yeşil, değilse sarı "commit bekliyor: freeze durabilir").
3. **Kayıt:** `<python> -m borsai.freeze --post-d1 <TICKER>` (cwd repo; stdout kayıt yolu; stderr aynen). Başarıda uygulama kaydı okur ve **parite**: `predict_post_d1` Rust'ta kaydın `base_record` girdileriyle (kaydın `models_index`'i gömülüyle eşit; f1–f3 girdileri kayıttaki base_record dosyasının `model_inputs`'undan okunur — girdi belgesi değil, H36) ve kaydın `d1` bloğuyla (`fields_raw`, `half_day`, `halt_flag`) koşulur; `models[post_d1_hazard_v0].output` ile §6.3 kuralları; sonuç "parite: 1/1" ya da kırmızı uyuşmazlık (`app/parity/incidents/`). `comparators_conditional` kopyaları Rust `survival::conditional(S, 1)` ile \|Δ\| ≤ 1e-12 denetlenir (bilgi). `D1_NOT_TRADED`/`CALENDAR_NOT_AVAILABLE`/`NoBaseRecord` Python hataları Türkçe açıklanır.
4. **Şimdi yapılacaklar** (komut bloğu; uygulama çalıştırmaz):
   ```bash
   cd <repo_root>
   git add registry/post_d1/<TICKER>/
   git commit -m "BORSAI_POST_D1_<TICKER>: post-D1 record before T_open"
   git push origin main
   .venv/bin/python -m borsai.push_proof $(git rev-parse HEAD)
   git add registry/push_proofs/ && git commit -m "BORSAI_PUSH_PROOF: <sha>" && git push origin main
   ```
   Metin: "Zaman kanıtı push'tur (CLAUDE.md kural 1). Kanıtın created_at'i {T_open}'dan (D2_cal 09:40 Europe/Istanbul) önceyse kayıt LIVE adayıdır; sonra LATE_RECORD. Sınıf skorlamada tarihlerden hesaplanır."
- İptal: "İptal kaydı düş" → `<python> -m borsai.freeze --cancel-post-d1 <dosya> --reason "…"` (CLI adı Python'da doğrulanır; yoksa Ö-görevi). `T_open` sonrası iptal Python tarafından reddedilir; uygulama aynen gösterir.
- `Command::new("git")` beyaz listesi değişmez (`rev-parse`, `status`, `log`, `ls-files`); U32 testi genişler.

---

## 7. E — Doğruluk sekmesinde "Zaman-dışı test (eski kohort)" paneli

### 7.1 Kaynak ve okuyucu (`commands/scores_oot.rs`)

- Dosya `scores/scores_oot.json` (`borsai.scores_oot/1`); kaynak seçimi `scores.json` ile aynı (`REPO` = `<repo_root>/scores/scores_oot.json`; `EMBEDDED` = derlemeye gömülü anlık kopya, `build.rs` varsa gömer `SCORES_OOT_JSON: Option<&str>`). Panel başlığı: kaynak, `generated_at_utc`, `code.git_head` ilk 12, `cohort_sha256` ilk 12, dosya sha ilk 12.
- Okunan alanlar: `schema_version`, `scale`, `definitions.class` (metin, tooltip), `oot_pre_h99 {title, n_member, n_open, n_sealed, n_out_of_scope, n_pending_membership, n_exposed_archive, n_exposed_codex, n_in_table, n_spk_corporate_action_seen(_cohort_total), models[]}`, `post_d1 {title, scale, models[]}`, `retro_info[]`, ileride `oot_pre_h99_sealed`, `oot_pre_h99_all` (aynı model bloğu şeması; `subset` alanı sırasıyla `oot_pre_h99_sealed`, `oot_pre_h99_all`). Model bloğu: `model_id, kind, scale, subset, primary_cell, cells[], by_year[], by_regime[], rows[], n_scored, n_refused, n_skipped, n_target_unavailable, n_pending, n_not_applicable_regime, n_oot_retro`. Bilinmeyen anahtar yok sayılır.
- **Fail-closed bütünlük** (`check_integrity_oot`, SPEC_APP §2.3 kalıbı; panel yerine "scores_oot.json şartname kuralına aykırı: {kural}"): `schema_version` ≠ `borsai.scores_oot/1` → sürüm mesajı (§2.5 satırı: "uygulama 1'i destekler"); her model bloğunda `n_scored < 10` iken `cells` boş değil (`OOT_CELLS_BELOW_MIN_N`); her hücrede (`cells`, `by_year`, `by_regime`) `verdict ∈ {geçiyor, geçemiyor}` iken `n < 30` ya da `ci95` null ya da 0'ı içeriyor (`VERDICT_WITHOUT_INTERVAL`); `verdict == ayırt edilemiyor` iken `ci95` 0'ı dışlıyor; `n_live + n_late ≠ 0` (zaman-dışı satırlarda canlı sınıf olamaz; `OOT_LIVE_COUNTS_NONZERO`); **her `rows[]` öğesinde `open == true` değil** → **`OOT_ROW_NOT_OPEN`** (kod adı ya da kimlik basılmaz; yalnız sayı: "{n} satır açık küme değil"); `retro_info[]`'daki bir `ticker` aynı dosyanın `open == true` bir satırında geçmiyorsa o ticker **çizilmez** (yalnız sayı) — kural: uygulama SEALED kodu hiçbir yoldan göstermez, dosya yanlışlıkla taşısa bile. Uygulama hiçbir hücreyi hesaplamaz, düzeltmez, doldurmaz.

### 7.2 Yerleşim [KARAR]

Doğruluk ekranı üç **bağımsız** üst bölüm olur (sırasıyla): (1) mevcut model blokları (içlerinde "Geçmiş veri testi (retrospektif, tasarıma maruz)" ve "Canlı sicil (prospektif, n = k; atlanan = s)"), (2) mevcut RETRO/atlanan/ayrı modeller, (3) **yeni** `<section class="panel-oot">` "Zaman-dışı test (eski kohort)". Üçüncü bölüm kendi model seçicisini, kendi kaynak satırını ve kendi RETRO listesini taşır; model bloklarının içine gömülmez. Gerekçe: dosya ayrı, model kümesi ayrı (bugün 19; kasa açılınca 27), ölçek ayrı; "asla toplanmaz" görünür kalır. `ACCURACY.scalesNote` üç teraziyi sayar: "Üç terazi bağımsızdır: geçmiş veri testi (retrospektif, tasarıma maruz), zaman-dışı test (eski kohort) ve canlı sicil (prospektif) hiçbir yerde toplanmaz, ortalanmaz, tek hükümde birleşmez." Renk: `.panel-oot` yeşil-gri (lacivert-gri backtest, kehribar canlı ile ayrışır; U14 statik taraması üç listeyi birleştiren fonksiyon olmadığını sınar).

Bölüm 3 içeriği:

1. **Başlık:** dosyanın `oot_pre_h99.title`'ı aynen ("Zaman-dışı test: H99 öncesi kohort (2020–2023), tahminler sonuç repoya girmeden dondurulmuş (rejim farklı)"); alt satır kohort sayaçları: "MEMBER {n_member} · açık küme {n_open} · kasa (SEALED) {n_sealed} · kapsam dışı {n_out_of_scope} · EXPOSED {n_exposed_archive} + {n_exposed_codex} · tabloya giren {n_in_table}"; **kasa satırı**: `oot_pre_h99_sealed` yoksa "kasa: kapalı — SEALED üyelerin sonucu repoda yok; skor yok ((C) şartnamesiyle birlikte açılır)"; varsa "kasa: açıldı — {generated_at_utc}".
2. **Sınıf tanımı** (katlanır): `definitions.class` metni aynen; not "sınıf tarihlerden hesaplanır, elle etiket yok; OOT_RETRO çift hiçbir n'e girmez".
3. **Model blokları** (`<details class="model-block-oot">`, model seçicisiyle): kart (`CardVM` aynı; `sha` gömülü model sha'sı, `shaCompare` yok — dosya sha taşımaz; `liveN`/`liveVerdict` null → "—"); **birincil hücre** (`label == birincil`, `.primary` rozeti "birincil (önceden ilan)"), diğer `cells` ("keşif"); tablo sütunları SPEC_APP §3d T-1 aynen + `n (blok)` = `n ({n_blocks})`; **hüküm sütunu**: dosyadaki `verdict` + `verdict ∈ {geçiyor, geçemiyor, ayırt edilemiyor}` iken sabit ek **" (zaman-dışı terazide)"** (`VERDICT_OOT_SUFFIX`; "yetersiz örnek" ve null ekle yazılmaz); renk yalnız geçiyor/geçemiyor'da. **Kırılımlar** (katlanır): `by_year` ("İlk işlem yılı — ikincil") ve `by_regime` ("Tahsis rejimi — keşif"); n < 10 satırlar "metrik yok (n < 10)" (dosyadaki null'lar), 10 ≤ n < 30 "yetersiz örnek" rozeti; renk yok. **Sayaçlar:** "skorlanan {n_scored} · ret {n_refused} · rejimle uygulanamaz {n_not_applicable_regime} · hedef oluşmadı {n_target_unavailable} · bekleyen {n_pending} · atlanan {n_skipped} · OOT_RETRO {n_oot_retro} (yalnız bilgi)". **Satır tablosu** (katlanır; yalnız `open == true`): arz · D1 · yıl · rejim etiketi · sınıf (`OOT_BLIND`) · durum · tahmin (`prediction` özeti: hazard için `S_1, S_5, S_10`; getiri için `D5 return/p_up`) · gerçekleşen (`realized` özeti) · kayıt (`record_id`) — biçimlendirme SPEC_APP §3d `rowTable` kalıbı, `class_evidence` tooltip.
4. **Kasa alt bölümleri** (yalnız varsa): "Kasa (SEALED; tek seferlik, H99 öncesi kohort)" → `oot_pre_h99_sealed.models` aynı blok render'ıyla, ayrı model seçicisi; "Açık ∪ kasa (yalnız açık kümede OOT_BLIND olan modeller)" → `oot_pre_h99_all`. Üç alt küme arasında toplam yok; her blok kendi `subset` etiketini taşır.
5. **D1 sonrası zaman-dışı** (`post_d1`): ayrı alt bölüm, başlık dosyadan aynen ("… makine sıralı: makine bütün zip'i gördü, insan görmedi"), `exposure_class` rozeti, hücreler aynı kurallarla; sayaçlar `n_rows, n_scored, n_refused, n_not_applicable, n_d1_label_na, n_no_record, n_oot_retro`; not "ayrı ölçek (`OOT_PRE_H99_POST_D1_MACHINE_SEQUENCED`); birincil tabloya girmez".
6. **OOT_RETRO (yalnız bilgi)**: `retro_info` model başına gruplu ("{model} — {n} çift; {açık satırda geçen ticker'lar}"), `class_evidence.basis` tooltip; v1 (ve ileride (C)) için 71 açık satır burada görünür (SPEC_HAZARD_V1 §7.2). Hiçbir n'e girmez.
7. **Tavan serisi ve Düşüş kartlarına terazi satırı** (§5.2-7, §8.4): kasa hücresi bu okuyucudan gelir.

### 7.3 Boş ve hata hâlleri

Dosya yok → "scores_oot.json bulunamadı (Faz 6 S6 henüz koşmadı ya da yol yanlış)"; bağımsız modda gömülü kopya yoksa "zaman-dışı skorlar repo modu ister"; sürüm uyumsuz → §2.5; bütünlük → §7.1; `models` boş → "zaman-dışı skor yok". `inputs`/INDEX sha uyuşmazlığı: dosya `models_index_sha256` taşımaz [ÖLÇTÜM]; model kartı `params_sha256_8` alanı da yoktur → sha karşılaştırması yapılmaz, kartta "dosya sha taşımıyor" notu.

---

## 8. C — `fall_d10_v0` ailesinin portu ve "Düşüş (D10)" kartı (P4; (C) dondurulunca)

**Referans notu:** Bu bölüm `docs/specs_faz7_c/SPEC_C_V0.md` §2.3, §3, §8, §9 ve `KARARLAR_C.md`'den yazıldı; Python referansı (`borsai/predict_fall.py` ya da `predict.py` eki) bu oturumda yoktur (paralel Opus oturumu yazıyor). **Referans: (C) dondurmasından sonra doğrulanır.** P4 adım 0 = **referans kilidi**: uygulayıcı donmuş dört JSON'un üst düzey anahtarlarını, Python `freeze.model_kind`'ın (C) için verdiği adı, predict fonksiyonunun çıktı anahtarlarını ve ret kod sabitlerini ölçer; bu bölümle çelişen her nokta raporda "referans farkı" satırı olur ve **Python kazanır** (Rust bir porttur); bu belge değişmez, sapma `docs/SPEC_DEVIATIONS.md`'ye değil rapora yazılır (app/ dışına yazılmaz).

### 8.1 Tür ve JSON alanları (SPEC_C_V0 §2.3)

- `Kind::Fall` (`as_str = "fall"`; Python adı referans kilidinde doğrulanır; farklıysa Rust metni Python'a uyar). `model_kind`: `family == "fall_d10_v0"` → Fall (algorithm `l2_logit_v1_6_grid` [SPEC_C §2]; `V1_5_RIDGE_LOGIT` olsaydı `Kind::Linear`'a düşerdi — bu yüzden `family` denetimi `RIDGE_LOGIT_ALGORITHM`'den ÖNCE).
- Okunan alanlar: `schema_version`, `model_id`, `family`, `variant ∈ {h99, pooled, addsale}` (`@ZERO` kural satırı: `variant` "pooled", `features []` ya da başlıklar `constant`; referans kilidi), `features` ⊆ `{f1r, f3, add_sale}` (h99/pooled: `[f1r, f3, add_sale]`; addsale: `[add_sale]`; @ZERO: `[]`), `horizons.{D5, D10}.p_up {kind: logit | constant, columns, coef, intercept | value}` (`return` başlığı YOK → çıktı `return: null`), `preprocessing {columns, winsor.{f1r, f3}.{p05, p95}, log_transform [f1r, f3], mean, std, f3_filter_mode}`, `input_policy {f3_missing, additional_sale_missing, f3_filter_status_conflict}`, `feature_ranges`, `deflator` (§2.1 pini; f1r varsa zorunlu), `target_definition` (yalnız kart metni). `parse_fall` denetimleri `parse_linear` kalıbı + `family`, `deflator` (f1r varsa), winsor anahtar kümesi `== {f1r, f3} ∩ features`, `log_transform == [f1r, f3] ∩ features`.

### 8.2 Akış (`fall::predict_fall`; V1.5 `predict_core` kalıbı, yeni özellikler)

1. `compute_features(inputs)` (f1, f2, f3, f4; retler miras). `f3` istenen varyantta (`h99`, `pooled`) `f3 == None` → `F3_MISSING` / `total_demand_multiple`; f3 filtre durumu V1.5 kuralı (`f3_filter_mode` açıkken çelişki → `F3_FILTER_STATUS_CONFLICT` / `total_demand_filter_status`; SPEC_C'nin `REFUSED_F3_FILTER_CONFLICT` sabiti bugün `"F3_FILTER_STATUS_CONFLICT"` değerini taşır [ÖLÇTÜM `predict.py:40`]).
2. `add_sale` (özellik listesindeyse): `additional_sale_flag(inputs["additional_sale_shares"])`: yok / `null` / `""` / `DATA_NOT_FOUND` → RET **`ADDITIONAL_SALE_MISSING`** / `additional_sale_shares` (KARARLAR C4; kod B3 biçimi öneksiz [ÇIKARIM, J5/H23 kalıbı]); sayı değil → `INPUT_NOT_NUMERIC`; `< 0` → `INPUT_NEGATIVE` / `additional_sale_shares`; `> 0` → 1.0, `== 0` → 0.0.
3. `f1r` (özellik listesindeyse): §2.3 adım 2 aynen (`tufe_index`/`tufe_refusal`; `real_size`; `TUFE_*` retleri, alan `tufe_index`).
4. Sıra (referans kilidinde doğrulanır): compute_features → F3 → add_sale → TÜFE → aralık uyarıları → z. Ham değerler `values = {f1r, f3, add_sale}`; `range_warnings` ham değerlerle (f1r 2025 TL, f3 ham, add_sale {0, 1}).
5. `z_vector(prep, values)`: f1r ve f3 winsor → **ln** → z (f3 için yeni: V1.5'te ham winsor'lu f3 idi; SPEC_C §3.2); add_sale yalnız z. Kırpma uyarısı: kodu referans kilidinde okunur — adaylar `F3_WINSORIZED` (V1.5 kalıbı, yalnız f3) ve `FEATURE_CLIPPED_TO_TRAINING_P05_P95` (v1 kalıbı; f1r için tek seçenek [ÇIKARIM]); Rust Python'un yazdığını üretir, `tr.ts` iki kodu da tanır.
6. Başlıklar: her `horizons` anahtarı (dosya sırası: `D10`, `D5`) için `p_up = sigmoid(py_sum(coef·z) + intercept)` (`head_values` kalıbı: `sum(...) + intercept`), `direction = p_up ≥ 0.5 ? "UP" : "DOWN"` (V1.5 kuralı; referans kilidi), `return/return_unclipped/return_clipped/price = null`. `@ZERO`: `constant` başlık → `p_up = value`.
7. Çıktı `LinearOutput` biçimi (`{model_id, D10, D5, warnings, refused}`; anahtar kümesi `horizons`'tan); `RunResult.kind = "fall"`.

Ret/uyarı T-2 eki: `ADDITIONAL_SALE_MISSING` — "ek satış alanı boş → bu model tahmin vermez (0 varsayılmaz; KARARLAR C4)"; `INPUT_NEGATIVE` / `additional_sale_shares` — "ek satış payı negatif olamaz"; `F3_MISSING` metnine (C) için ek yok; `TUFE_*` §2.5.

### 8.3 Altın vektörler (P4)

- `PINNED_MODEL_IDS` 27 (INDEX sırası); `FALL_IDS` dört kimlik; `PREDICT_SOURCES` + (C) predict dosyası. Mevcut 392 satır dört yeni modelde koşar (BASE `additional_sale_shares = "0"` → add_sale 0; `tufe_index` yok → h99/pooled `TUFE_MISSING`, addsale ve @ZERO tahmin verir).
- Yeni satırlar `only=FALL_IDS`: H99 99 + `tufe_index` (ek satış alanı `training_table.csv` girdi sütunundan; boş 4 arz → `ADDITIONAL_SALE_MISSING`); açık 71 + `tufe_index` (§4.2 bekçisiyle; `alloc_regime` verilmez — (C)'de rejim yok, verilse de okunmaz); 7 sicil + `tufe_index`; uçlar: `additional_sale_shares` ∈ {yok, `null`, `""`, `"DATA_NOT_FOUND"`, `"abc"`, `"-1"`, `"0"`, `"0.0"`, `"35000000"`, `"1e400"`}; f3 p05 altı/p95 üstü (ln sonrası z); f1r kırpma; filtre çelişkisi (yamalı `f3_filter_mode = FILTERED` + `UNFILTERED` girdi); `@ZERO` değişik girdilerle sabit çıktı. ≥ 560 satır/model. Yamalı +10 (`family` silinir → Linear'a düşer ve `PARAMS_INVALID`/farklı yol: referans kilidi; `deflator` eksik; winsor eksik; `horizons.D1` ekli → `PARAMS_INVALID`; `schema`).
- Toleranslar: `p_up` \|Δ\| ≤ 1e-9 (beklenti bit-eşit; `py_sum` + `sigmoid`), `direction` birebir, `return*`/`price` null ↔ null, ret ve uyarı kuralları §2.7.

### 8.4 "Düşüş (D10)" kartı (SPEC_C_V0 §9 metinleri aynen) [KARAR]

Yer: Sonuç sayfasında Tavan serisi kartının hemen altında, aynı genişlikte ikinci özet kart (`summary summary-fall`); Grup A'daki V1.5 `p_up` sütunu olduğu gibi kalır. Yalnız INDEX'te `fall` türü model varken çizilir. İçerik:

1. Başlık "Düşüş (D10) — arz fiyatının altına düşme olasılığı" · mod rozeti · "öne çıkan: {model_id | kasada geçen aday yok}".
2. Öne çıkan (varsa) için büyük satır: "**P(D10 kapanışı ≤ arz fiyatı) = %k**" (= 1 − p_up, 0 ondalık) · altında "P(kapanış > arz) = %(100 − k)" · D5 satırı aynı biçimde (ikincil, KARARLAR C3).
3. Adaylar tablosu: `fall_d10_v0_addsale`, `_h99`, `_pooled` (SPEC_C §5.5 basitlik sırası), kural `pooled@ZERO` ("basit kural: havuz oranı"), karşılaştırıcı satırları `base_rate` ve `v1_5_h99` (Grup A'daki p_up'tan, "karşılaştırıcı" rozeti). Sütunlar: model · P(D10 ≤ arz) · P(D5 ≤ arz) · yakın dönem (backtest; `near_era` bloğu (C) için `comparator = fall_d10_v0_h99`, metrik Brier, `tolerance 0.008`; yalnız `pooled`'da etiket, h99/addsale için `− base_rate` hücresinin "tamamen 0'ın üstünde" bilgisi → "taban orandan kötü" / "—") · zaman-dışı (kasa) · canlı. RET satırları `RET · {kod}` ("ek satış alanı boş → bu model tahmin vermez" / "talep katı yok → …").
4. Kart alt satırları: model kartı bağlantısı (model_id, "ne yapar" INDEX açıklaması, eğitim n ve kesim, sha ilk 8, varyant sayısı — `card.n_variants_same_data`, `exploration` satırlarını sayar [SPEC_C §9]; birincil hücre "D10 Brier − taban oran"); üç terazi notu; TÜFE satırı §3.3.
5. Öne çıkarma `featured_fall` (SPEC_C_V0 §5.5): `oot_pre_h99_sealed` yokken `None` → "kasa: bekliyor"; varken k1 (birincil `p_up D10 Brier vs base_rate` verdict "geçiyor"), k2 (`vs v1_5_h99` `ci95[1] < 0`), k3 (`pooled` için near_era ≠ "bozuyor"; h99/addsale için yakın dönem `− base_rate` hücresi `ci95[0] > 0` değil — bu hücre `scores.json` `backtest.cells`'ten okunur), `min(round(model_value, 3), order addsale < h99 < pooled)`; uygun yoksa "kasada geçen aday yok" (V1.5 sütunu olduğu gibi). K4: hiçbir model listeden kalkmaz.

Sözcükler yalnız izinli liste (SPEC_APP §4); "düşer" fiili değil "düşme olasılığı" adı; "sinyal", "al/sat" yok.

---

## 9. Metinler (`app/src/i18n/tr.ts`; kod içinde serbest metin yok, U21 taraması)

Öncelik: proje sahibinin gördüğü ekranın sadeleşmesi — kartlar özet verir, Grup B/C ve satır tabloları katlanır. Yeni anahtarlar (kısa, Türkçe; değerler §5–§8'deki metinler):

| Blok | Anahtar | Metin |
|---|---|---|
| `CODE_TEXT` (+ `ModelCode`) | `TUFE_MISSING`, `TUFE_NOT_PIT`, `TUFE_FILE_MISMATCH`, `REGIME_UNKNOWN`, `FEATURE_CLIPPED_TO_TRAINING_P05_P95` | §2.5 |
| `CODE_TEXT` (P2) | `D1_NOT_TRADED`, `D1_LIMIT_NA`, `D1_NOT_CEILING`, `D1_VOLUME_INVALID`, `D1_FIELD_INVALID`, `INPUT_SHARES_OFFERED`, `WARN_D1_HALF_DAY`, `WARN_D1_INTRADAY_HALT`, `WARN_D1_SPECIAL_TRADES`, `WARN_D1_LOCK_INCONSISTENT`, `D1_TURNOVER_CLIPPED_TO_TRAINING_P05_P95` | §6.3 |
| `CODE_TEXT` (P4) | `ADDITIONAL_SALE_MISSING` | §8.2 |
| `KIND_TEXT` | `post_d1: "D1 sonrası güncelleme (ofset + D1 kilit ve el değiştirme)"`, `fall: "düşen arz (D5/D10 arz altı kapanış olasılığı)"` | |
| `SUMMARY` (yeni) | `ceilingTitle: "Tavan serisi — kaç gün tavan?"`, `featured: (m, why) => \`öne çıkan: ${m} (${why})\``, `featuredWhy: {VAULT_CLOSED_V0_DEFAULT: "kasa kapalı; SPEC_HAZARD_V1 §5.5 uyarınca v0", RULE_5_5: "kasa sonucu, §5.5", RULE_5_5_NONE_ELIGIBLE_V0: "kasada uygun aday yok; v0"}`, `expected: (d) => \`Beklenen seri ${d} gün\``, `median: (d) => \`medyan ${d} gün\``, `pGe: (k, p) => \`P(en az ${k} gün) ${p}\``, `p10: (p) => \`P(10 gün) ${p}\``, `modeNone: (p) => \`D1'de tavan kapanışı yok (P = ${p})\``, `modeDay: (d, l, p) => \`D${d} (seri ${l} gün; P = ${p})\``, `modeCensored: (p) => \`10 gün boyunca tavan (sağdan sansürlü; P = ${p})\``, `condLine: (j, src, pb, rem, s5, s10) => …`, `jObserved: "gözlenen"`, `jHypothetical: "varsayımsal"`, `colNearEra: "yakın dönem (geçmiş veri testi)"`, `colVault: "zaman-dışı (kasa)"`, `colLive: "canlı sicil"`, `vaultClosed: "kasa: bekliyor"`, `vaultOpen: "kasa: açıldı"`, `nearEraNone: "—"`, `nearEraTip: (cmp, d, ci, n, nb) => …`, `nearEraMissing: "scores.json'da yakın dönem bloğu yok"`, `scalesLine: "üç terazi ayrıdır; toplanmaz"`, `nearEraFoot: "yakın dönem: H99, ilk işlem ≥ 2024-01-01, tasarıma maruz"`, `detailGroupB: "Ayrıntı: Grup B — S_k tablosu ve eğrisi, P(L = k), P_close, hazard"`, `pbMirror: "PB aynası (f3'süz tahmin)"`, `roleRule: "kural"`, `recordWithoutModel: "kayıt bu modeli içermiyor (kayıt INDEX'ten eski)"`, `officialPending: COND.officialPending` (aynı dize) |
| `SUMMARY` (P4) | `fallTitle: "Düşüş (D10) — arz fiyatının altına düşme olasılığı"`, `pFall: (h, k) => \`P(D${h} kapanışı ≤ arz fiyatı) = ${k}\``, `pUpLine: (k) => \`P(kapanış > arz) = ${k}\``, `fallNone: "kasada geçen aday yok"`, `fallRule: "basit kural: havuz oranı"`, `comparator: "karşılaştırıcı"`, `fallWhat: "ek satış, reel büyüklük ve talep katından D10'da arz altı kapanış olasılığı"` (INDEX `description` yoksa yedek), `fallPrimary: "D10 Brier − taban oran"` |
| `TUFE` (yeni) | `line: (m, idx, rel, src, pin) => \`TÜFE: ${m} = ${idx} (yayım ${rel}; kaynak ${src}; pin ${pin})\``, `sourceText: {REPO: "repo dosyası", EMBEDDED: "gömülü tablo"}`, `pinOk: "✓"`, `pinBad: "✗ (TUFE_FILE_MISMATCH)"`, `missingMonth: (m) => \`TÜFE ${m} tabloda yok. Bülten yayımlanınca (m + 1'in 3'ü 10:00) Python tarafında eklenir:\``, `appendCommand: "<Python tufe.APPEND_COMMAND metni birebir>"`, `embeddedThrough: (m, head) => \`TÜFE tablosu ${m}'a kadar gömülü (derleme ${head}); yeni ay için yeniden derleme ya da repo modu\``, `invalid: (why) => \`TÜFE tablosu ayrıştırılamadı: ${why}\``, `tUnknown: "ilk işlem günü girilmedi; TÜFE ayı belirlenemez"`, `noManual: "TÜFE elle girilmez (imputasyon yok); ay ilk işlem gününden türetilir"` |
| `FREEZE.blockerText` | `TUFE_MONTH: "TÜFE (T'nin ayı − 2) dosyada yok; kayıt yazılamaz. Önce ayı ekleyin (komut aşağıda)."` | §3.4 |
| `COND` (P2) | `postD1Row: "D1 sonrası (post_d1_hazard_v0)"`, `postD1None: "D1 sonrası kayıt yok"`, `postD1Scenario: "senaryoda D1 bülteni yok; D1 sonrası tahmin yalnız resmi kayıttan"`, `postD1J0: "D1 sonrası model j ≥ 1'de tanımlı"`, `postD1Source: (f, sha, d1, thb, thm) => …`, `postD1Primary: "birincil POST_D1 kaydı seçimi skorlamada yapılır (T_open ve push kanıtı)"`, `postD1NotApplicable: "D1 tavanda kapanmadı: model tanımlı değil"`, `postD1PathCard: "D1 sonrası S ile tavan yolu (ikincil)"` |
| `POST_D1` (yeni; sihirbaz) | `title: "D1 sonrası kayıt sihirbazı"`, `intro`, `steps: ["Ön koşullar", "Bülten ve sonuç güncellemesi (Python; komut)", "Kayıt (Python freeze --post-d1)", "Şimdi yapılacaklar"]`, `tOpen: (t) => \`T_open = ${t} (D2_cal 09:40 Europe/Istanbul)\``, `tOpenNote: "yerel saat kanıt değildir; sınır push kanıtının created_at'idir"`, `noBaseRecord: "listeleme öncesi kayıt yok → SKIPPED_POST_D1: NO_PRE_LISTING_RECORD"`, `d1Pending: "D_1 henüz repoda değil: adım 2'yi çalıştırın"`, `recheck: "Çalıştırdım, yeniden denetle"`, `uncommitted: "commit bekliyor: freeze durabilir (sequence_guard)"`, `parity: (ok, n, d) => …`, `calendarNA: "takvim D_1'i kapsamıyor (CALENDAR_NOT_AVAILABLE); kayıt yazılamaz"`, `liveNote: (t) => \`Kanıtın created_at'i ${t}'dan önceyse kayıt LIVE adayıdır; sonra LATE_RECORD. Sınıf skorlamada tarihlerden hesaplanır.\`` |
| `ACCURACY` (P3) | `scalesNote` (üç terazi metni, §7.2), `oot: {title (dosyadan), counters: (…) => …, vaultClosed: "kasa: kapalı — SEALED üyelerin sonucu repoda yok; skor yok ((C) şartnamesiyle birlikte açılır)", vaultOpen: (t) => …, classDef: "Sınıf tanımı", byYear: "İlk işlem yılı — ikincil", byRegime: "Tahsis rejimi — keşif", sealedTitle: "Kasa (SEALED; tek seferlik, H99 öncesi kohort)", allTitle: "Açık ∪ kasa (yalnız açık kümede OOT_BLIND olan modeller)", postD1Title (dosyadan), postD1Note: "ayrı ölçek; birincil tabloya girmez", retroTitle: "OOT_RETRO (yalnız bilgi; hiçbir n'e girmez)", noFile: "scores_oot.json bulunamadı (Faz 6 S6 henüz koşmadı ya da yol yanlış)", repoOnly: "zaman-dışı skorlar repo modu ister", noShaNote: "dosya params sha taşımıyor", integrityRule: {OOT_CELLS_BELOW_MIN_N, OOT_LIVE_COUNTS_NONZERO, OOT_ROW_NOT_OPEN: (n) => \`${n} satır açık küme değil (SEALED gösterilmez)\`}}`, `VERDICT_OOT_SUFFIX = " (zaman-dışı terazide)"` |
| `SETTINGS` | `tufeLine: (m, pin) => \`TÜFE son ay ${m}, pin ${pin}\`` |
| `ABOUT` | `tufeEmbedded: (m, sha) => …`, `postD1Index: (sha) => \`INDEX_POST_D1 sha256 ${sha}\`` |

Kurallar: "geçiyor" dizesi kaynakta yalnız `VERDICT` eşlemesinde ve U19 açıklamasında (yeni metinlerde yok; `VERDICT_OOT_SUFFIX` "geçiyor" içermez); yasak sözcükler yok; `thb`/`thm` + tarih kalıbı hiçbir metinde yok (bülten sha'ları "bültenler sha …" diye gösterilir).

---

## 10. Kabul testleri (U53–U80; hepsi `cargo test` / vitest / betik)

### 10.1 P1 — v1 portu, TÜFE, kart

| # | Test | Yöntem | Kanıt |
|---|---|---|---|
| U53 | **Parite 23/23:** dört v1 dosyası ≥ 600 satır; §2.7 kuralları; `parity_report.json` `models_passing = 23`, maks \|Δ\| ≤ 1e-9; `predict_sources_unchanged` 9 dosya; `bit_equal_floor` 23 taban | `cargo test -p borsai_predict --test golden` | rapor |
| U54 | **Kapsama:** `TUFE_MISSING` ≥ 10 satır (real, pooled; girdi yok/boş/sayı değil/≤ 0 ve `tufe_refusal` yolları ayrı ayrı ≥ 2), `TUFE_NOT_PIT` ≥ 2, `TUFE_FILE_MISMATCH` ≥ 2, `REGIME_UNKNOWN` ≥ 4 (pooled ve @INF'te ≥ 2), `regime_source` her iki değer ≥ 10, `regime_value_used = 1` ≥ 20 (açık küme PRE/THRESH), `FEATURE_CLIPPED` her sütun için alt ve üst ≥ 2 (f1 yalnız clip, f1r yalnız real/pooled), `clipped_features` ≥ 2 sütunlu ≥ 2 satır, `F3_MISSING` ≥ 2 (dört modelde), @INF'te `clipped null` bütün satırlar | `cargo test -p borsai_predict --test coverage` | `golden_coverage.json` |
| U55 | **U46 korunur:** 16 eski altın dosya `0b67f5d` ile, 3 tavan yolu dosyası ve koşullu dosyalar `7133991` ile bayt-eşit; `_patched_params.jsonl` ilk 31 satır bayt-eşit; `dec_cases.json` eski bölümleri bayt-eşit; MANIFEST ve 4 yeni dosya değişir (bilgi) | `bash app/tests/golden_unchanged.sh` (`OLD_MODELS` 19, `NEW_MODELS` 4; taban commit'leri betikte) | betik çıktısı |
| U56 | **Decimal ve TÜFE anlamı:** `real_size` `dec_cases` bölümü (metin ve float birebir), k-katı değişmezliği Δ = 0; `tufe_cases.json`: `month_for` 8, `index_for` retleri, `prefix_sha256` gerçek dosyada iki ay, ek satırla pin tutar / değişen eski satırla `TUFE_FILE_MISMATCH`, `parse` retleri | `cargo test -p borsai_predict --test dec_semantics real_size` + `--test tufe_semantics` | çıktı |
| U57 | **TÜFE kaynak ve engel:** geçici klonda (a) repo dosyasından `index_for` → real/pooled tahmin verir; (b) dosyaya 2026-09 satırı eklenmiş kopyada T = 2026-11-10 ile ay bulunur (yeniden derleme yok); (c) 2026-09 yokken T = 2026-11-10 → iki model `RET TUFE_MISSING`, blok metni `APPEND_COMMAND` ile (vitest metni `borsai/tufe.py`'deki dizeyle karşılaştırır); dondur sihirbazı `TUFE_MONTH` engeli ve Python çağrılmaz (sayaç 0); (d) T boş → `T_UNKNOWN` reddi, engel değil; (e) bir eski satır değiştirilmiş kopya → `TUFE_FILE_MISMATCH` (engel değil; sarı satır); (f) bağımsız modda gömülü tablo ve Hakkında satırı | `cargo test --test stage3 tufe_source_and_blocker` + vitest | çıktı |
| U58 | **Bütünlük 23:** gömülü 23 dosya sha = INDEX; `check_params` hepsinde geçer (v1 dalı); v1 JSON'unun `winsor.f2` silinmiş test-içi kopyası → `INTEGRITY_FAILED`; `ignored_model_ids == []` | `cargo test --test integrity` + `--test build_embed` | çıktı |
| U59 | **Kayıt paritesi:** eski 7 kayıt "16/16 + kayıtta yok: 7" (unsupported boş); geçici klonda `freeze` ile yazılan kayıt 23 model, `tufe` bloğu, `model_inputs.tufe_index`; Rust parite 23/23 (`tufe_index` kayıttan) | `e2e_freeze_tmp_repo.sh` + `BORSAI_REPO=… cargo test --test records_parity` | betik çıktısı |
| U60 | **Tavan serisi kartı render:** fixture `runs_netgl.json` (23 model; Rust gerçek çıktısı), `runs_veyas.json` (f3 boş: 8 RET + 15 dolu; kartta `pb_ceiling_v0` satırları açık), `scores_near_era.json` (sentetik `near_era` blokları: clip "tolerans içinde", real/pooled "bozuyor"), `scores_oot.json` fixture kasa kapalı; DOM'da: öne çıkan `ceiling_hazard_v0` ve neden `VAULT_CLOSED_V0_DEFAULT`; beklenen/medyan/P≥3/P≥5/P10 değerleri `ceiling_display` fixture'ındaki `S[2], S[4], S[9]`, `expected_l`, `median_l` biçimlendirilmiş hâliyle birebir; `mode_l` üç dal (0, orta, 10) üç sentetik S vektörüyle; j = 0'da koşullu satır yok, j = 2'de var; üç terazi sütunu üç sınıf; "kasa: bekliyor"; canlı "n = 7: hüküm yok"; Grup B `<details>` kapalı; ön uçta hesap yok taraması (`summary.ts` yalnız biçimlendirir; `no_frontend_math.test.ts` genişler) | vitest `summary.test.ts` + `cargo test --test stage2 ceiling_summary_fixtures` + ekran görüntüsü | ikisi |
| U61 | **Öne çıkarma kuralı:** `featured_ceiling` birim testleri: kasa bloğu yok → v0/`VAULT_CLOSED_V0_DEFAULT`; sentetik `oot_pre_h99_sealed` ile (a) clip k1–k3 sağlar → clip; (b) real ve pooled `verdict geçiyor` ama near_era "bozuyor" → uygun değil; (c) iki uygun aday `model_value` 0.1801 / 0.1809 → düşük olan, 0.1804 / 0.1806 (yuvarlanınca eşit) → basit olan; (d) `near_era` bloğu yok → k3 = false; (e) `k2` `ci95[1] = 0.0` → uygun değil; fonksiyon `bootstrap`/`mean` çağırmaz (statik) | `cargo test featured_ceiling` | çıktı |
| U62 | **Resmi görünümde yalnız kayıt:** test kaydı `output.S` kasten `0.5^k` yapılmış 23 modelli kayıtla kart ve koşullu satırlar `0.5^(k−j)` verir, `predict_all` sayacı 0; 16 modelli kayıtta v1 satırları "kayıt bu modeli içermiyor"; beyan resmi verinin önündeyse koşullu satır "resmi kapanış bekleniyor" (U52 kümesi karta genişler: beyanlı j ile üretilen hiçbir metin DOM'da yok) | vitest + `cargo test --test stage3 official_summary_uses_record_only` | çıktı |
| U63 | **U7 güncellemesi:** VEYAS girdileriyle sonuç ekranı **8 RET** (`v1_5_h99`, `v1_6_h99`, `v1_5_market20_v0`, `ceiling_hazard_v0`, `ceiling_path_v0`, `ceiling_hazard_v1_clip`, `_real`, `_pooled`; hepsi `F3_MISSING`) + **15 dolu** (`pooled@INF` dahil); NETGL girdileriyle T = 2026-09-17 → `tufe_index` 2026-07 = 132.31, real/pooled dolu | `cargo test --test stage2 u7_veyas` + ekran görüntüsü | ikisi |

### 10.2 P2 — D1 sonrası

| # | Test | Yöntem | Kanıt |
|---|---|---|---|
| U64 | **Parite post_d1:** `golden/post_d1_hazard_v0.jsonl` ≥ 220 satır; §6.3 kuralları; `S_cond`/`P_L_cond`/`p_break_next` ≤ 1e-12; `d1_turnover_ratio` metin birebir; yamalı 8 satır ilk hata kodu; `bit_equal_floor` tabanı | `cargo test -p borsai_predict --test golden post_d1_parity` | rapor |
| U65 | **INF ve h_1 paritesi (Rust içi):** `delta = {0.0, 0.0}` yamasıyla `S` ve `conditional_j1` `ceiling_hazard_v0`'ın `survival::conditional(S, 1)` çıktısına **bit-eşit** (H2); `hazard[0]` ana modelle bit-eşit; `evaluate_d1` kilit eşitliği `"10.12"/"10.120"` → 1, `"10.12"/"10.1200000000000000001"` → 0 (K3 çifti) | `cargo test -p borsai_predict post_d1_inf_and_lock` | çıktı |
| U66 | **Kapsama:** her `D1_*` reddi ≥ 2 (`D1_FIELD_INVALID` üç alan), `D1_NOT_CEILING` ≥ 5, `D1_NOT_TRADED` (`expected.error`) ≥ 2, her `WARN_D1_*` ≥ 2, `D1_TURNOVER_CLIPPED` alt/üst ≥ 2, `OUT_OF_TRAINING_RANGE` `d1_turnover` ≥ 2, `path_conditional` null (path verilmemiş) ≥ 2 ve dolu ≥ 100; `INPUT_SHARES_OFFERED` muafiyet (ana model önce reddeder; birim test) | `--test coverage` | `golden_coverage.json` |
| U67 | **Bütünlük ikinci dizin:** gömülü `post_d1_hazard_v0.json` sha = INDEX_POST_D1; parent/path sha zinciri; `parent.gamma[0]` bozulmuş test-içi kopya → `INTEGRITY_FAILED / POST_D1_PARENT_MISMATCH`; `predict_all` bu türü çalıştırmaz (23 sütun) | `cargo test --test integrity post_d1_integrity` | çıktı |
| U68 | **"D1 sonrası" satırı:** fixture'lar: sentetik `registry/post_d1/SNTA1/…json` (şema §7.4 birebir; PREDICTED; `models[].output.S` kasten `0.6^k`), iptal edilmiş ikinci kayıt, `NOT_APPLICABLE` hücreli üçüncü arz; j = 0 → satır yok + not; j = 2 → satır `0.6^(k−2)`; RET/NOT_APPLICABLE metinleri; senaryoda satır yok; kaynak satırı; iki etkin kayıt → sekmeler ve "birincil seçim skorlamada" etiketi; beyan resmi verinin önündeyse satır yok (U52) | vitest `post_d1.test.ts` + `cargo test --test stage3 post_d1_records_reader` | çıktı |
| U69 | **Sihirbaz uçtan uca (geçici klon):** kurgusal arz `SNTA1` için listeleme öncesi kayıt + sentetik D_1 sonuç satırı (h = 1 OK; `data/outcomes/SNTA1.csv` betik yazar; gerçek bülten yok — `freeze --post-d1` yerel bülten sha denetimi için betik sentetik zip ve MANIFEST satırı üretir, `tests/faz5_live_support.py` kalıbı) → adım 1 T_open Python'dan (takvim), adım 3 `freeze --post-d1` kayıt yazar, Rust parite 1/1, `comparators_conditional` \|Δ\| ≤ 1e-12; kayıt `git status`'ta untracked; uygulama `git commit/push` çalıştırmaz (beyaz liste testi); listeleme öncesi kayıt yokken adım 1 DUR; `T_open` sonrası iptal Python reddi aynen | `app/tests/e2e_post_d1_tmp_repo.sh` + `cargo test --test e2e post_d1_flow` | betik çıktısı |
| U70 | **Doğruluk paneli post_d1:** gerçek `scores/scores_post_d1.json` ile "Koşullu skorlar" bölümü: hücre yok, `retro_info` 7 satır n'e girmez, kart H43 alanları ("kesim" sözcüğü yok); sentetik n = 12 ve n = 35 kopyalarında küçük-n kuralları | vitest | çıktı |

### 10.3 P3 — Zaman-dışı panel

| # | Test | Yöntem | Kanıt |
|---|---|---|---|
| U71 | **Üç terazi ayrı:** DOM'da `.panel-backtest`, `.panel-live`, `.panel-oot` üç sınıf; üçünü birleştiren fonksiyon yok (statik tarama genişler); `scalesNote` üç teraziyi sayar; zaman-dışı bölüm model bloklarının içinde değil | vitest `accuracy_oot.test.ts` | çıktı |
| U72 | **Hüküm eki ve renk:** sentetik `scores_oot_n35.json` ("geçiyor" [−0.05, −0.01], "geçemiyor" [+0.001, +0.13], "ayırt edilemiyor" [−0.006, +0.004]) → metinler `verdict + " (zaman-dışı terazide)"`, renk yalnız ilk ikisinde; `by_year` n = 26 → "yetersiz örnek" ve renk yok; n = 1 → "metrik yok (n < 10)"; "geçiyor" dizesi kaynakta yalnız `VERDICT` eşlemesinde (U19 taraması `VERDICT_OOT_SUFFIX`'i kapsar) | vitest | çıktı |
| U73 | **Fail-closed ve hijyen:** `n_scored = 8` iken `cells` dolu → hata; `verdict geçiyor` ve `n = 20` → hata; `n_live = 1` → hata; bir satırda `open: false` → panel yerine `OOT_ROW_NOT_OPEN` ve DOM'da o satırın `ticker`'ı HİÇBİR yerde yok; `retro_info`'da açık satırda geçmeyen ticker → çizilmez (sayı var); şema sürümü 2 → sürüm mesajı | vitest + `cargo test scores_oot_integrity` | çıktı |
| U74 | **Kasa alt bölümleri:** `oot_pre_h99_sealed` ve `_all` içeren sentetik dosya → iki ek alt bölüm, "kasa: açıldı", her blok kendi `subset` etiketiyle, aralarında toplam yok; yokken "kasa: kapalı" | vitest | çıktı |
| U75 | **Gerçek dosya ile render:** `scores/scores_oot.json` (repo) → 19 model bloğu, birincil hücreler `docs/SCORES_OOT.md` §2'deki 8 satırla aynı değer metinleri (biçimlendirme farkı hariç; `SCORES_OOT.md` 4 ondalık), `post_d1` alt bölümü 1 model; DOM'da yalnız `open: true` satırların ticker'ları; tavan serisi kartında "kasa: bekliyor" | vitest `accuracy_oot.test.ts real file` + ekran görüntüsü | ikisi |

### 10.4 P4 — (C)

| # | Test | Yöntem | Kanıt |
|---|---|---|---|
| U76 | **Referans kilidi raporu:** P4 adım 0 ölçümleri (`model_kind` adı, çıktı anahtarları, ret sabitleri, kırpma uyarı kodu, `@ZERO` biçimi) `app/parity/README.md`'ye yazılır; §8 ile fark listesi (boş olabilir) | rapor | metin |
| U77 | **Parite 27/27:** dört (C) dosyası ≥ 560 satır; `p_up` ≤ 1e-9 (beklenti bit-eşit); `direction` birebir; `return*` null; yamalı 10; `bit_equal_floor` 27 | `--test golden` | rapor |
| U78 | **Kapsama:** `ADDITIONAL_SALE_MISSING` ≥ 6 (yok/null/boş/DATA_NOT_FOUND), `INPUT_NEGATIVE` (`additional_sale_shares`) ≥ 2, `add_sale = 1` ≥ 20 (açık küme 13 + H99 6 + uç), `F3_MISSING` yalnız h99/pooled, `TUFE_*` yalnız h99/pooled, f3 ln-winsor alt/üst ≥ 2, `@ZERO` sabit çıktı ≥ 200 satırda bit-eşit | `--test coverage` | `golden_coverage.json` |
| U79 | **Düşüş kartı:** fixture `runs_netgl_27.json`; öne çıkan yok → "kasada geçen aday yok"; P(D10 ≤ arz) = 1 − p_up biçimlendirilmiş (0 ondalık) ve `p_up` satırı; adaylar sırası addsale, h99, pooled, @ZERO, karşılaştırıcılar `base_rate`, `v1_5_h99`; RET metinleri; `featured_fall` birim testleri (§8.4 k1–k3, eşitlik, uygun yok) | vitest `summary.test.ts fall` + `cargo test featured_fall` | çıktı |
| U80 | **U46/U55 genişlemesi:** 23 eski altın dosya bayt-eşit (taban P1 commit'i), `_patched_params.jsonl` ilk 51 satır; `ignored_model_ids == []`; kayıt paritesi 27/27 (geçici klon) | `golden_unchanged.sh` + `records_parity` | betik çıktısı |

Uygulayıcı her aşamada `bash app/scripts/test.sh` tam yeşil raporlar; U46 zinciri (U55 → U80) her aşamada koşar.

---

## 11. ÖNCEDEN YAZILMIŞ BEKLENTİ

Yazım 2026-09-27, port kodu yokken; sayılar Python kaynaklarından ve dondurulmuş JSON'lardan çıkarımdır, koşulmadı.

- **P1 parite:** 23/23 model geçer; dört v1 dosyasında maks |Δ| < 1e-12 (izin 1e-9); `hazard/S/P_L/P_close` bit-eşit satır oranı v0'ınkinden düşük değil; `f1r_raw` bit-eşit (iki doğru yuvarlanmış dönüşüm); `tufe_index_used` metin birebir 100 %. Eski 19 dosya bayt-eşit, `_patched_params.jsonl` ilk 31 satır bayt-eşit. Satır sayıları: clip/real/pooled/@INF her biri ≈ 392 + 217 = ~609. Mevcut 392 satırda real ve pooled 390'ında `TUFE_MISSING` (2 satır `F3_MISSING` önce), clip ve @INF tahmin verir; @INF'te bütün satırlarda `clipped null`, `clipped_features null`, `regime_value_used 0`, `regime_source LIVE_VALUE`.
- **VEYAS girdileri (f3 boş, T 2026-09):** `ceiling_hazard_v1_clip/real/pooled` → RET `F3_MISSING` (TÜFE'den önce); `pooled@INF` → tahmin, `S` sabit eğri (γ = [−1.7832, −2.0499, −1.5279], δ·0 = 0): `S_1 = sigmoid(−γ_1) = 1 − 0.1440 = 0.856`, `S_10 ≈ 0.856 · 0.886² · 0.822⁷ ≈ 0.17` (4 ondalık koşuda ölçülür). Sonuç ekranı **8 RET + 15 dolu**.
- **NETGL girdileri (f3 2.84, `ipo_size_tl` 2 233 000 000, T 2026-09-17 → TÜFE 2026-07 = 132.31):** `f1r_raw = 2233000000 / 1.3231 = 1 687 703 424.08…` (2025 TL; koşuda ölçülür); real ve pooled winsor içinde (p05 566 mn – p95 6 237 mn), kırpma yok; `regime_value_used 0`; clip'te f1 = 2 233 mn winsor [521 mn, 4 888 mn] içinde, kırpma yok; f3 = 2.84 üç modelde içeride → `clipped false`, `clipped_features []`.
- **P1 kart:** öne çıkan `ceiling_hazard_v0` (`VAULT_CLOSED_V0_DEFAULT`); `near_era` bloğu `scores.json`'da yokken sütun "—" (Ö1 gelince clip "tolerans içinde", real/pooled "bozuyor"); "kasa: bekliyor"; canlı v0 "n = 7: hüküm yok", v1 "n = 0: hüküm yok".
- **P2:** post_d1 dosyası ≈ 230 satır; `S`/`S_cond` maks |Δ| < 1e-13 (`ln` payı ≤ 5e-15 → hazard'a ≤ 1e-15); bit-eşit oranı v0'dan düşük (ln yolu); `d1_turnover_ratio` metni 100 % birebir; sentetik D1 satırlarının ≈ %85'i `D1_NOT_CEILING` değil, ≈ %12'si `D1_NOT_CEILING`. Gerçek `registry/post_d1/` boş → satır yok; `scores_post_d1.json` hücre yok.
- **P3:** gerçek dosya 19 blok, 8 birincil hücre `SCORES_OOT.md` §2 ile aynı; hiçbir `OOT_ROW_NOT_OPEN`; `post_d1` alt bloğunda 1 model, n = 59 birincil "geçiyor (zaman-dışı terazide)".
- **P4:** referans kilidinde en olası farklar: `model_kind` adı ("fall" ya da "fall_d10"), kırpma uyarı kodu, `@ZERO`'nun `features []` + `constant` başlık biçimi, `direction` alanının varlığı. Parite 27/27, `p_up` bit-eşit. NETGL girdileriyle (`additional_sale_shares` "0") add_sale 0; VEYAS'ta h99/pooled `F3_MISSING`, addsale tahmin verir.
- **Test sayıları:** cargo +≈ 30, vitest +≈ 45, `test_gen_golden.py` +≈ 6; `test.sh` süresi +≈ 30 %.
- **Riskli noktalar:** (1) `real_size` çift işlemin Decimal üs/yuvarlama davranışı (`div_exact` sonra `div_round`); Python'la `dec_cases` üzerinden ilk günde sınanır. (2) `alloc_regime` anahtarının `null` değeriyle `REGIME_UNKNOWN` (anahtar var/yok ayrımı serde `Map`'te korunur). (3) `bool_fields`'ın `Warning.to_json` sırası. (4) `ln_to_f64` ile Python 60 haneli `ln` farkı: pariteyi değil bit-eşit oranını etkiler. (5) `scores.json`'da `near_era` yokken kartın yarım görünmesi: kabul edilen geçici durum (Ö1). (6) Açık küme girdilerinin altın vektörlere alınmasında kohort dosyasının SEALED süzgeci: `_assert_open` ve `test_no_sealed_code_in_golden` zorunlu. (7) (C) referansının bu belgeden sapması: referans kilidi. (8) Sihirbaz U69 için sentetik bülten zip'i ve MANIFEST satırı üretmek Python bekçilerine (sha eşitliği) takılabilir; `tests/faz5_live_support.py` kalıbı izlenir.

---

## 12. Ön koşul görevleri (Python tarafı; bu ekte DÜZELTİLMEDİ; uygulama beklemez)

| # | Ne | Neden | Dosya |
|---|---|---|---|
| Ö1 | `scores.json`'a `models[].backtest.near_era` bloğu (§5.5 şeması; `backtest.near_era_cell` çıktısı ve `near_era_label`; (C) için `comparator fall_d10_v0_h99`, `tolerance 0.008`) | Tavan serisi ve Düşüş kartlarının yakın dönem sütunu ve §5.5 k3 buna bağlı; bugün etiket yalnız MODELS.md/günlükte | `borsai/scoring.py`, `scores/scores.json` yeniden üretim (J30 istisnası düşer) |
| Ö2 | 23 modelli `scores.json` (4 v1 kartı, `retro_info` 28 satır, `models_index_sha256` 53265dd5…) | Kart `n_variants` ve canlı n satırları; bugün J30 ile eski | aynı |
| Ö3 | (C) predict referansı: stdlib fonksiyon, `freeze.model_kind` adı, ret sabitleri (`ADDITIONAL_SALE_MISSING` B3 biçimi), kırpma uyarı kodu, `@ZERO` JSON biçimi; `gen_golden.PREDICT_SOURCES`'a giren dosya adı | §8 referans kilidi | `borsai/predict*.py`, `models/INDEX.json` (dondurma) |
| Ö4 | `scores_oot.json`'a `oot_pre_h99_sealed` / `oot_pre_h99_all` (kasa açılışı; SPEC_HAZARD_V1 §7.1-5) ve `generated_at_utc`'nin kasa açılış tarihi; satırlarda `open` alanı kasa üyeleri için de doğru | §5.3 / §8.4 seçim kuralı ve §7.2 kasa alt bölümleri | `borsai/scoring.py` |
| Ö5 | `featured_ceiling` / `featured_fall` sonucunu `MODELS.md`'deki insan kararıyla karşılaştıran Python testi (kasa açılınca) | Uygulama kuralı veri-güdümlü uygular; iki yolun ayrışması sessiz kalmamalı | `tests/` |
| Ö6 | `freeze --cancel-post-d1` CLI adı (varsa) ve `registry.t_open` tek satırlık çağrının kararlılığı (uygulama bunları çağırır) | §6.6 adım 1 ve iptal | `borsai/freeze.py`, `registry.py` |

---

## 13. Açık sorular (proje sahibine; orkestratör cevaplar; en çok 5)

| # | Soru | Önerim |
|---|---|---|
| 1 | **Öne çıkarma seçimi** (§5.3, §8.4): uygulama §5.5 kuralını dosyadaki verdict/aralık/etiketten kendisi mi uygulasın, yoksa proje sahibi kasa sonrası tek bir dosyaya (`models/APP_FEATURED.json` gibi) elle mi yazsın? | Veri-güdümlü (bu ek): kural önceden yazılıdır, uygulama skor hesaplamaz, yalnız okur; Ö5 testi insan kararıyla uyumu sınar. Elle dosya, "sonuca bakıp seçmek" görüntüsü verir. |
| 2 | **Yakın dönem etiketinin kaynağı**: `scores.json` `near_era` bloğu (Ö1) kabul mü? Blok gelmeden kart sütunu "—" gösterir. | Kabul; sıradaki skorlama görevi 23 modelli `scores.json`'u yazarken bloğu ekler (aynı commit). Alternatif (uygulamanın `experiments/log.jsonl` okuması) reddedilir: günlük skor dosyası değildir. |
| 3 | **Bağımsız modda TÜFE**: yalnız gömülü tablo (yeni ay = yeniden derleme) yeterli mi, yoksa Ayarlar'da kullanıcı seçimli CSV (aynı biçim, aynı pin denetimi) istenir mi? | P1'de yalnız gömülü + repo; kişisel kullanımda repo modu varsayılandır, yeniden derleme aylık ekleme ile aynı gün yapılabilir. CSV seçici ürünleşme gündeme gelirse tek ayar satırıyla eklenir (`tufe_source = FILE`). |
| 4 | **D1 sonrası kayıt sihirbazı** `freeze --post-d1`'i uygulama mı çalıştırsın (mevcut dondur kalıbı; parite denetimi için), yoksa bütün akış yalnız komut bloğu olsun mu? | Uygulama çalıştırır (§6.6 adım 3); bülten indirme ve commit/push yalnız komut. Gerekçe: kaydın Rust paritesi ancak uygulama kaydı okuyunca anında görünür; Python yine tek yazıcıdır. |
| 5 | **Senaryo modunda D1 alanlarını elle girip** "kilitli olsaydı / el değiştirme x olsaydı" tahmini görmek isteniyor mu? | Hayır (bu ek): v0 yalnız resmi bültenle tanımlı; elle girilen D1 alanı, beyan gibi, ekran görüntüsünde model çıktısından ayrılamaz (U52 gerekçesi). İstenirse ayrı ek, senaryo filigranı ve "D1 girdisi kullanıcı beyanı" etiketiyle. |

---

## 14. Maruziyet (bu oturum)

**Gördüm:** SPEC_APP tamamı; EK 2 tamamı; SPEC_HAZARD_V1 tamamı; SPEC_POST_D1_V0 tamamı; SPEC_C_V0 tamamı + KARARLAR_C; `docs/faz7/IMPL_RAPOR.md` §14, `docs/fable_faz7_audit/AUDIT.md` §8–§9, `docs/faz7/FREEZE_RAPOR.md` tamamı; SPEC_DEVIATIONS H ve J tamamı; `docs/SCORES_OOT.md` §0–§4 başı, §6–§7 (açık küme sayıları; üye kodu yok); `docs/MODELS.md` Faz 7 bölümü (grep); `borsai/predict_hazard.py`, `tufe.py`, `predict_post_d1.py` tamamı; `freeze.py` (docstring, `v1_record_inputs`, post_d1 fonksiyon adları), `scoring.py` (oot bölümü grep), `registry.py`/`outcomes.py`/`predict.py`/`predict_path.py` (ilgili fonksiyonlar grep), `specs.py` `TUFE_PIN`; `models/INDEX.json`, `INDEX_POST_D1.json`, dört v1 JSON'unun ve `post_d1_hazard_v0.json`'un üst düzey alanları (deflator, regime, preprocessing, input_policy); `data/raw/tuik/tufe_genel_2025_100.csv` ilk 4 ve son 3 satırı, `build_tufe_csv.py` argümanları; `scores/scores.json` (kart ve blok anahtarları), `scores_oot.json` (yapı; **satır örneği yalnız `ticker`/`record_id` maskelenmiş olarak** — bir açık üyenin d1 tarihi ve ret kodu göründü, üye kodu görülmedi), `scores_post_d1.json` (yapı, `retro_info` ilk öğesi CITAS d1); 7 canlı kaydın model ve girdi anahtarları; `app/` Rust ve TS kaynakları (§0 listesi), testler ve fikstür adları, `golden/MANIFEST.json`, `bit_equal_floor.json`, `test.sh`, `golden_unchanged.sh`.

**Koşmadım:** hiçbir predict, fit ya da skor; hiçbir Rust derlemesi. Veri sürümü, `data/outcomes*`, kohort dosyası, kasa üyelerine ait hiçbir dosya okunmadı; SEALED kod görülmedi. Ağ yok. Yazılan tek dosya bu belge (+ görev dosyası commit'i).

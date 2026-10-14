# Kitap denetimi 4 — Ajan B: test sayıları, U-haritası, şartname boşlukları, komut kaydı

Repo: /Users/ahmet/Desktop/BorsAi, HEAD ee3796d (salt okuma; testler koşulmadı, kaynak sayıldı).
Denetlenen kılavuz bölümleri: `docs/fable_kitap_audit/kitap/07_uygulama_rust.md` §7.7, §7.12, §7.13; `08_uygulama_arayuz.md` §8.10, §8.25.
Etiketler: [ÖLÇTÜM] = kaynak/grep ile sayıldı; [ÇIKARIM] = ölçümden çıkarılan yorum. Sınıf: [P] = kılavuz/belge hatası, [K] = kod/belge tutarsızlığı, [B] = bilgi/doğrulama.

## 1. Bulgular

| # | Sınıf | Önem | Yer | Beklenen | Bulunan |
|---|---|---|---|---|---|
| B1 | [B] | — | 07 §7.7; `app/src-tauri/src/lib.rs:49-105` | 55 komut | [ÖLÇTÜM] `generate_handler!` 55 giriş; `#[tauri::command]` 55 fn (18 dosya); kümeler birebir. Kılavuz doğru. |
| B2 | [K] | düşük | `lib.rs:68`, `commands/freeze.rs:335` | her kayıtlı komut ön uçtan çağrılır | [ÖLÇTÜM] `freeze_todo` kayıtlı ama `app/src/**/*.ts` içinde `invoke("freeze_todo")` yok; Rust testlerinde de adı geçmiyor (stage3 `todo_block_shape` iç fonksiyon `todo_commands`'ı sınar). Ölü IPC yüzeyi; §7.7 bunu işaretlemiyor. |
| B3 | [B] | — | 07 §7.12 | 169 `#[test]`, 13 `#[ignore]` (8+5), test.sh 164 | [ÖLÇTÜM] 169 `#[test]` (37 dosya); `#[ignore` 15 grep vuruşu, 2'si `//!` yorum (records_parity.rs:3, e2e.rs:7) → 13 gerçek; 8 BORSAI_REPO (stage2 1, stage3 4, records_parity 3) + 5 e2e; 169 − 5 = 164. Dağılım tablosunun 16 satırı sayımla birebir (§2a). Kılavuz doğru. |
| B4 | [P] | düşük | 07 §7.12 "5'i geçici klon ister" | — | [ÖLÇTÜM] e2e'nin 5'inden 2'si (`prepare_screens`, `prepare_screens_p2`) ek olarak `BORSAI_E2E_SCREENS=1` ister ve `screens.sh` / `screens_p2.sh` ile koşar (test.sh yorumu "yalnız geliştirme"). Eksik ayrıntı, yanlış değil. |
| B5 | [B] | — | 08 §8.25 | vitest 376 = 355 `it(` + döngü | [ÖLÇTÜM] 24 dosya, 355 literal `it(`; `.each` yok; döngü: `results.test.ts:116` (+1), `stage5.test.ts:81` (`cases` 10 → +9), `stage5.test.ts:207` (`neutralOrOfficial` 7 → +6), `u52_declaration.test.ts:401` (`mutations` 6 → +5) = +21 → 376. `ui_fix_test_runs.txt` adım 2/5 "24 dosya, 376 test" ✓ (adım 0 taban b045e71: 365; UI_FIX_A +11). §8.25 dosya-başı tablo 24/24 doğru. |
| B6 | [P] | orta | 07 §7.13 son satır (`--include-ignored` statik koruması "belirsiz") | kapanış C2 koruma testi | [ÖLÇTÜM] `grep -rn include-ignored app/src-tauri/tests app/tests app/src-tauri/src app/parity tests` → 0 (yalnız `#[ignore = "…"]` metinleri ve test.sh). Koruma testi **yok**; "belirsiz" → "yok". |
| B7 | [P] | düşük | 07 §7.13 README satırı | eski satırlar | [ÖLÇTÜM] `app/README.md:199` "19 gömülü model", `:205` "`streak_view(ticker?, userDays)`" eskimiş (api.ts `streakView: (ticker: string | null)`, MANIFEST `model_ids` 27). Kılavuz doğru; README "Bilinen sapmalar" bu eskimeyi listelemiyor. |
| B8 | [P] | orta | 07 §7.13 kaynak listesi `app/parity/README.md`; 08 §8.10 | parity belgeleri güncel sayı | [ÖLÇTÜM] `app/parity/README.md:11` "23 model × ≥ 200 satır", `:27` "eski 19 altın dosya"; `golden/README.md:14` "`<model_id>.jsonl` (19) … ilk 19 model", `:17` "8 Python dosyasının sha256'sı". MANIFEST.json: `model_ids` 27, `rows` 27, `predict_sources_sha256` 11, `fall_model_ids` 4, `post_d1_model_ids` 1. Kılavuz bu eskimeyi listelemiyor. |
| B9 | [P] | düşük | 07 §7.13 "--cancel-post-d1 vs --cancel" | sapma | [ÖLÇTÜM] `borsai/freeze.py:1588` tek bayrak `--cancel` ("listeleme öncesi ya da POST_D1"); EK3 §6.6/Ö6 "CLI adı Python'da doğrulanır; yoksa Ö-görevi". [ÇIKARIM] Sapma değil, Ö6'nın kapanışı; kılavuz satırı buna göre yazılmalı. |
| B10 | [P] | düşük | 08 §8.10 U76–U80 özeti: U79 "kasada geçen aday yok" | şartname metni | [ÖLÇTÜM] Uygulama `SUMMARY.fallVaultClosed` / "öne çıkan yok — kasa sonrası kural (§5.5): uygun aday yok"; sapma `docs/app/p34/RAPOR.md §8-1` (K-P4-1) kayıtlı; `summary.test.ts` U79 uygulanan metni sınar. Kılavuz şartname metnini tekrar ediyor; §7.13 bu kayıtlı sapmayı listelemiyor. |
| B11 | [B] | — | 07 §7.13 Cargo.lock | reqwest/hyper var | [ÖLÇTÜM] `Cargo.lock` `name = "reqwest"`/`"hyper"` 2 vuruş; `no_network.rs:27` `--filter-platform aarch64-apple-darwin`; README "Bilinen sapmalar" 1. Doğru. |
| B12 | [B] | — | 07 §7.13 Dec vs BigRational | — | [ÖLÇTÜM] `SPEC_APP.md:107,569` BigRational; README madde 2 `Dec`; Cargo.toml'larda num-rational yok. Doğru. |
| B13 | [K] | düşük | `app/README.md` "Bilinen sapmalar" (11 madde) | app sapmaları tek yerde | [ÖLÇTÜM] §7.13'teki stderr sınıflaması, dışa aktarma bağ aşırı reddi, `--cancel`, fall portu 11 fark, U79 metni, K-P4-1/2 burada yok; `docs/fable_app_audit`, `app/parity/README.md`, `p34/RAPOR.md §8`'e dağınık. `docs/SPEC_DEVIATIONS.md` yalnız Python tarafı (A–K), app satırı yok. |
| B14 | [B] | — | U62 "predict_all sayacı 0" | Rust tarafında sayaç | [ÖLÇTÜM] `stage3.rs official_summary_uses_record_only` sayaç kullanmaz (0.5^k kayıt değerleri + `official_view_uses_record_only` tahminle çakışmama); "0 çağrı" `sade_invoke.test.ts:136,170,241` ve `screens_invoke.test.ts`'te. covered-but-weak. |
| B15 | [B] | — | U-haritası | 80 U | [ÖLÇTÜM] Üç şartnamede 80 `\| Un \|` satırı (U1–U40+U52 SPEC_APP §5; U41–U51 EK2 §6; U53–U80 EK3 §10); çakışan numara yok. Test ağacında numarası geçmeyen tek U: **U76** (belge gereği; `app/parity/README.md:57`). |

## 2. Sayı tabloları

### 2a. Rust `#[test]` / `#[ignore]` [ÖLÇTÜM]

| Dosya (app/src-tauri/…) | test | ignore | ignore fn → ortam |
|---|---|---|---|
| crates/borsai_predict/src/{dec 5, path 5, post_d1 3, tufe 2, fall 1, sum 1, survival 1} | 18 | 0 | |
| crates/…/tests/golden.rs | 9 | 0 | |
| crates/…/tests/coverage.rs | 5 | 0 | |
| crates/…/tests/dec_semantics.rs | 12 | 0 | |
| crates/…/tests/{tufe 4, v1 5, fall 7, post_d1 2}_semantics.rs | 18 | 0 | |
| crates/…/tests/records_parity.rs | 3 | 3 | `records_parity`, `post_d1_oot_open`, `fall_oot_open` → BORSAI_REPO |
| src/{json_out 2, clock 1, commands/{registry 1, predict 1, parity 1, ceiling 1, freeze 1, inputs_doc 2, path 2, scenario 2, fall 1, form 3, post_d1 2}} | 20 | 0 | |
| tests/build_embed.rs | 7 | 0 | |
| tests/integrity.rs | 6 | 0 | |
| tests/no_network.rs | 1 | 0 | |
| tests/stage2.rs | 20 | 1 | `market20_via_python_repo` → BORSAI_REPO |
| tests/stage3.rs | 23 | 4 | `inputs_doc_bytes_match_python`, `preflight_real_repo`, `wizard_fixtures`, `post_d1_preflight_real_repo` → BORSAI_REPO |
| tests/stage4.rs | 6 | 0 | |
| tests/oot_panel.rs | 2 | 0 | |
| tests/sade.rs | 13 | 0 | |
| tests/e2e.rs | 6 | 5 | `freeze_flow`, `personal_isolation`, `post_d1_flow` → BORSAI_E2E_REPO/DATA/PYTHON; `prepare_screens`, `prepare_screens_p2` → + BORSAI_E2E_SCREENS=1 |
| **Toplam** | **169** | **13** | test.sh: 169 − 5 = **164** |

`app/scripts/test.sh`: `--include-ignored --exact --skip freeze_flow --skip prepare_screens --skip personal_isolation --skip post_d1_flow --skip prepare_screens_p2` → 5 isim birebir. `ui_fix_test_runs.txt` adım 2/5 "cargo 164 passed / 0 failed" ✓.

### 2b. vitest [ÖLÇTÜM]

| Dosya (app/tests/) | literal `it(` | döngü | toplam |
|---|---|---|---|
| sade_render 46 · accuracy 43 · summary 32 · path 23 · freeze 20 · accuracy_oot 18 · post_d1 17 · registry 13 · post_d1_wizard 12 · ceiling 12 · sade_svg_format 11 · no_frontend_math 10 · sade_invoke 8 · screens_invoke 7 · sade_static 6 · scenario 4 · inputs 4 · codes 4 · no_network 3 · format 2 · disclaimer 2 | — | 0 | aynen |
| results.test.ts | 17 | +1 (`:116`) | 18 |
| stage5.test.ts | 20 | +15 (`:81` 10 hâl; `:207` 7 hâl) | 35 |
| u52_declaration.test.ts | 21 | +5 (`:401` 6 mutasyon) | 26 |
| **Toplam (24 dosya)** | **355** | **+21** | **376** |

## 3. U-haritası

Tür: cargo / vitest / betik / belge. Durum: covered (yıldızlı 15 U'da gövde açılıp iddia doğrulandı), by-content, weak.

| U | Gereksinim | Test | Tür | Durum |
|---|---|---|---|---|
| U1 | altın ≥ 200 satır; gen_golden stdlib | golden.rs::golden_files_present; parity/test_gen_golden.py | cargo+py | covered |
| U2 | Δ ≤ 1e-9, kod/uyarı birebir | golden.rs::golden_parity | cargo | covered |
| U3 | her kod ≥ 2 satır | coverage.rs | cargo | covered |
| U4 | Decimal/float/Neumaier | dec_semantics.rs; gen_golden.py | cargo | covered |
| U5 | predict_all INDEX'i kapsar | integrity.rs::predict_all_covers_index | cargo | covered |
| U6 | resmi kayıt paritesi | records_parity.rs::records_parity (ignore) | cargo | covered |
| U7* | f3 boş: RET + dolu | stage2.rs::u7_veyas_four_refusals (10 RET F3_MISSING/total_demand_multiple, 17 PREDICTED, fixture); results.test.ts "U7" (10 ret/17 dolu/27 başlık; RET bloğu sayı göstermez) | cargo+vitest | covered |
| U8 | her koda metin | codes.test.ts "codes_have_text (U8)" | vitest | covered |
| U9 | f6 yok/bayat | stage2::u9_f6_missing_and_stale; results "U9" | cargo+vitest | covered |
| U10 | kırpma ⌐ | stage2::u10_clipping; results "U10" | cargo+vitest | covered |
| U11 | uyarılar gizlemez | stage2::u11_warnings_do_not_hide; results "U11" | cargo+vitest | covered |
| U12 | bozuk params → INTEGRITY_FAILED | integrity.rs::integrity_fail_closed | cargo | covered |
| U13–U18 | başlık, iki terazi, metrik satırı, n<10 / 10≤n<30 / n≥30 | accuracy.test.ts "U13".."U18" | vitest | covered |
| U19* | "geçiyor" yalnız tr.ts ve verdict'ten | accuracy "U19" (TS ağacında yalnız tr.ts 1 vuruş; Rust yalnız scores.rs `VERDICT_PASS`; panelde her 'geçiyor' `td.verdict`'ten, n12'de yok); sade_static; sade_render | vitest | covered |
| U20–U23 | isabet tek başına yok; kart+yasak sözcük; birincil hücre; rejim | accuracy "U20".."U23"; stage5; results | vitest | covered |
| U24* | fail-closed 6 ihlal | accuracy "U24" (bad_live_cells, bad_descriptive, bad_self_cells, bad_split, bad_verdict_small_n, bad_verdict_ci_zero → `.integrity-error[data-rule]`, panel/cell-row yok); stage4 | vitest+cargo | covered |
| U25* | skor hesabı yok | accuracy "U25" (her model/rule değeri biçimlendirilmiş DOM'da; render/accuracy.ts'te bootstrap/percentile/mean/sum/reduce/Math./** yok); no_frontend_math; sade_static; summary | vitest | covered |
| U26 | self-reported/RETRO ayrı | accuracy "U26" | vitest | covered |
| U27* | kişisel kayıt repoya yazılamaz | stage2::scenario_path_guard (repo altı, symlink appdata, export, askıda bağ/`..` 5 vaka → SCENARIO_PATH_INSIDE_REPO); ::config_reset_and_data_dir_guard (DATA_DIR_INSIDE_REPO) | cargo | covered (bağ aşırı reddi §7.13) |
| U28–U31 | izleme, şema, dondur e2e, T geçmiş | e2e.rs::freeze_flow; e2e_freeze_tmp_repo.sh; freeze.test.ts "U30" | betik+vitest | covered |
| U32* | komut bloğu; app git yazmaz | freeze.test.ts "U32" (rev-parse HEAD, `-m borsai.push_proof`, yorum yok, commit `--`); stage2::git_readonly_whitelist (commit/push/add/tag/-c/reset/checkout → GIT_NOT_ALLOWED; `Command::new("git")` yalnız git.rs; git.rs:9 rev-parse/status/log/ls-files); stage3 todo_block_shape | vitest+cargo | covered |
| U33 | gömülü sha = INDEX | integrity::embedded_integrity; build_embed | cargo | covered |
| U34* | ağ yok | no_network.rs::no_network_deps (darwin grafiğinde 4 paket yok; lock'ta ureq/plugin-http yok; package-lock axios/node-fetch/plugin-http yok; CSP connect-src+default-src; capabilities 2 izin); no_network.test.ts 3 it; sade_static | cargo+vitest | covered (bilinçli sapma: lock'ta reqwest/hyper) |
| U35 | şema uyumsuzluğu | accuracy "U35"; stage2; stage4 | vitest+cargo | covered |
| U36 | farklı INDEX senaryo | scenario.test.ts "U36"; stage2::u36_scenario_other_index | vitest+cargo | covered |
| U37 | koşullu parite 1e-12 | golden.rs::conditional_parity | cargo | covered |
| U38* | resmi görünüm yalnız S | stage3::official_view_uses_record_only (S=0.5^k ≠ tahmin; s_cond=0.5^(k−j); k≤j None); registry.test.ts "U38" (%50/%25, data-j=3); sade_invoke (`predict_all` 0); screens_invoke | cargo+vitest | covered |
| U39 | beyan skora/sicile girmez | e2e::personal_isolation; ::observed_streak_user_only_in_scenario_module; e2e_personal_isolation.sh | betik+cargo | covered |
| U40 | şerit/tanımsız | ceiling.test.ts "U40"; stage2::u40_streak_and_undefined | vitest+cargo | covered |
| U41 | seri modeli bütünlüğü | integrity::survival_model_integrity | cargo | covered |
| U42–U45 | parite 19/19, koşullu karışım, kapsama, S bit-eşit | golden.rs (golden_files_present, conditional_path_parity, survival_passthrough*); coverage::path_ids | cargo | covered |
| U46 | eski altın bayt-eşit | golden_unchanged.sh | betik | covered |
| U47 | Decimal ek anlamı | dec_semantics::dec_semantics_limit_path | cargo | covered |
| U48–U49 | Grup A/C; "Getiri (koşullu)" | path.test.ts "U48"×2, "U49"×2; stage3 path_record | vitest+cargo | covered |
| U50 | kayıt paritesi 19 | e2e::freeze_flow | betik | covered |
| U51 | ceiling_path bloğu | accuracy "U51" | vitest | covered |
| U52* | beyandan sayı yok | u52_declaration "U52-1/2/4" (3 görünüm DECL_D3 ile; `allText` = metin+title/aria/data-*+SVG text/title; forbidden ≥10; U52-4 pozitif kontrol); "U52-5" (api satırlarında beyan yok; `streakView(ticker)` tek argüman); "U52-6"; 6 mutasyon; stage2::conditional_commands_take_no_declaration; e2e personal_isolation; summary/post_d1/path "U52 karta genişler" | vitest+cargo+betik | covered |
| U53–U56 | parite 23, TÜFE kapsama, U46 korunur, real_size/TÜFE anlamı | golden_parity; coverage::tufe_path; golden_unchanged.sh; dec_semantics_real_size; tufe_semantics::cases | cargo+betik | covered |
| U57* | TÜFE kaynak/engel | stage3::tufe_source_and_blocker ((a) repo 132.31 pin_ok; (c) ay yok → TUFE_MISSING real/pooled, clip/@INF etkilenmez, append komutu, blocker TUFE_MONTH, FREEZE_PREFLIGHT_BLOCKED, freeze_calls()==0; (b) satır eklenince 136.5, derleme yok); freeze.test.ts "U57" | cargo+vitest | covered |
| U58–U59 | bütünlük 23; kayıt paritesi | integrity::v1_params_integrity; records_parity; stage3 parity_counts_only_supported_models | cargo | covered |
| U60 | kart render | summary "U60"×3; stage2 ceiling_summary_fixtures | vitest+cargo | covered |
| U61* | öne çıkarma kuralı | stage2::featured_ceiling_rules (kasa yok → v0 VAULT_CLOSED_V0_DEFAULT; clip RULE_5_5; pooled "bozuyor" k3 false; yuvarlama eşitliği; yakın dönem yok; ci95[1]=0; gerçek dosya NONE_ELIGIBLE_V0 + k1/k2/k3 tablosu) | cargo | covered |
| U62* | kart yalnız kayıttan | stage3::official_summary_uses_record_only (p_ge3 0.125, p_10 0.5^10, cond, tufe RECORD; 16 modelli kayıtta v1 in_record=false); summary "U62"; predict_all 0 → sade_invoke/screens_invoke | cargo+vitest | covered-but-weak (B14) |
| U63 | U7 güncel sayılar | stage2 u7; integrity; results | cargo+vitest | covered |
| U64–U67 | post_d1 parite, INF/h1, kapsama, ikinci dizin | golden::post_d1_parity; post_d1_semantics.rs; coverage::post_d1_coverage; integrity::post_d1_integrity | cargo | covered |
| U68 | "D1 sonrası" satırı | post_d1.test.ts "U68"; stage3 post_d1_records_reader | vitest+cargo | covered |
| U69* | sihirbaz e2e | e2e::post_d1_flow (engeller NO_PRE_LISTING_RECORD+D1_PENDING, Python çağrılmaz; sentetik D_1 → ok, UNCOMMITTED, T_open 09:40+03:00, commit sonrası ok); e2e_post_d1_tmp_repo.sh; post_d1_wizard.test.ts "U69"×2 (12 it; iptal `--cancel`; git'e yazan komut yok); stage3 post_d1_wizard_fixtures | betik+cargo+vitest | covered |
| U70 | panel post_d1 | post_d1 "U70"; stage4 scores_post_d1_reader | vitest+cargo | covered |
| U71–U72 | üç terazi; hüküm eki | accuracy_oot "U71", "U72" | vitest | covered |
| U73* | fail-closed + kasa kodu görünmez | accuracy_oot "U73 + K-P3-1" (satırlar yalnız oot_pre_h99; kasa/toplam/post_d1 bloklarında [data-ticker] yok; SNTS1/SNTP1/SNTX1/SNTZ9 0; RETRO yalnız açık kodla; ihlallerde data-rule, blok yok, "1 satır açık küme değil"); oot_panel.rs::panel_view_rows_only_in_open_block | vitest+cargo | covered |
| U74–U75 | kasa alt bölümleri; gerçek dosya | accuracy_oot "U74", "U75"; oot_panel::panel_view_real_file | vitest+cargo | covered |
| U76 | referans kilidi raporu | app/parity/README.md:57 | belge | by-content |
| U77–U78 | parite 27; kapsama add_sale | golden::fall_parity; coverage::add_sale_path | cargo | covered |
| U79* | Düşüş kartı | summary "U79"×2 (VAULT_CLOSED → `fallVaultClosed`; aday sırası addsale/h99/pooled/@ZERO + base_rate/v1_5_h99; P(D10≤arz)=pctInt(pct_fall) Rust'tan, tooltip p_up/p_fall; üç terazi; h99 ★); stage2::featured_fall_rules | vitest+cargo | covered; metin sapması kayıtlı (p34 §8-1; B10) |
| U80 | U46/U55 genişlemesi | golden_unchanged.sh; build_embed; e2e freeze_flow | betik+cargo | covered |

NOT COVERED: yok. by-content: U76. weak: U62.

## 4. Şartname boşlukları / farklı uygulananlar

| # | Madde | Kod | Kayıt |
|---|---|---|---|
| G1 | SPEC_APP §1.3 BigRational | `Dec` | README "Bilinen sapmalar" 2; kılavuz §7.13 |
| G2 | U34 lock'ta reqwest yok | lock'ta var (mobil), test darwin grafiği | README 1; no_network.rs; kılavuz |
| G3 | EK3 §8 fall portu | Python `predict_fall.py` kazanır (11 fark) | app/parity/README.md; kılavuz |
| G4 | EK3 §6.6 `--cancel-post-d1` | `--cancel` (freeze.py:1588 tek bayrak; Ö6) | kılavuz "sapma" (B9: kapanış); README'de yok |
| G5 | U27 export hedef bağı | bağsa her durumda ret | kılavuz (C1); README'de yok |
| G6 | Python hata sınıflaması | stderr metni | kılavuz (B11); README'de yok |
| G7 | EK3 U79 "kasada geçen aday yok" | "öne çıkan yok — kasa sonrası kural (§5.5): uygun aday yok" | p34/RAPOR.md §8-1; kılavuz §8.10 şartname metnini tekrar ediyor |
| G8 | EK3 §8.4-5 k3 kaynağı backtest.cells | scores.json `near_era` bloğu | p34 §8-2 |
| G9 | EK3 §8.4-3 yalnız pooled etiketi | dört (C) modelinde etiket (K-P4-2) | p34 §8-3 |
| G10 | EK3 §8.4 kart yalnız Sonuç | arz sayfasında da (U62 kalıbı) | p34 §8-5 |
| G11 | EK3 §7.2 hüküm eki yalnız "geçiyor" | "ayırt edilemiyor"a da; model `info` panelde yok | p34 §8-9 |
| G12 | UI_V2_HARITA F1–F24 | 24 tasarım farkı; F5 (işlem adedi çubukları) UI_FIX_A 317304a ile sonradan eklendi | HARITA tablosu; UI_V2_RAPOR §11 (EK5 portu, F14, sihirbaz etkin adım, pencere 1200×800); UI_FIX_RAPOR "sapma yok" |
| G13 | Kapanış C2 `--include-ignored` koruması | yok | kılavuz "belirsiz" (B6) |
| G14 | README `predict_all` 19 model, `streak_view(ticker?, userDays)` | 27 model, `streakView(ticker)` | kılavuz §7.13; README düzeltilmemiş |
| G15 | parity README "23 model"/"eski 19"; golden README "(19)"/"8 Python dosyası" | MANIFEST 27 model, 11 kaynak | kayıtsız (B8) |
| G16 | `freeze_todo` | kayıtlı, çağrılmıyor | kayıtsız (B2) |
| G17 | K-UI-14/15 | testlerde K-UI-1..13 (K-UI-6 biçim içerikle) | [ÇIKARIM] süreç kuralı |

## 5. Komut denetimi [ÖLÇTÜM]

- `lib.rs:49-105` `generate_handler![…]`: 55 giriş (benzersiz 55).
- `#[tauri::command]`: 55 fn — ceiling 4, config 4, form 1, freeze 5, inputs_doc 4, market20 1, models 1, path 3, post_d1 6, predict 1, registry 3, sade 4, sade_break 1, scenario 6, scores 3, scores_oot 2, snapshot 4, source_docs 2 (fall/git/parity/mod: 0).
- Kayıtlı olup fn'si olmayan: yok. Fn olup kayıtsız: yok.
- `invoke("…")`: `api.ts` 44 benzersiz + `sade/api.ts` 6 (kesişim yok) = 50; `dev/demo.ts` 4 dev_* ; `dev/dialog-demo.ts` get_config. Var olmayan ada invoke: yok. Çağrılmayan tek kayıtlı komut: `freeze_todo`.

## 6. Denetlenmeyenler

- Testler koşulmadı; "passed" sayıları `docs/app/ui_fix_test_runs.txt`'ten.
- Yıldızlı 15 U'nun gövdesi okundu; diğer 65 U yalnız ad/numara/grep bağlamıyla eşlendi.
- `app/tests/fixtures/**` içeriği açılmadı; registry/oot SEALED listeleri hiç okunmadı.
- HARITA F1–F24'ün her birinin bugünkü koddaki durumu tek tek kontrol edilmedi (yalnız F5 commit konusundan).
- `app/scripts/screens*.sh`, `docs/fable_app_audit/{AUDIT,KAPANIS}.md` açılmadı; kılavuzun C1/C2/B9/B11 atıfları doğrulanmadı.
- `cargo metadata` çıktısı ve `package-lock.json` doğrudan okunmadı (yalnız testin ne sınadığı).

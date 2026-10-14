FAZ9_WINDOWS: A 63d953d (+A2 fc69fec, A3 0cd882f) · B ac1d5e0 · C e688f96 (+C2 d57e2b3, C3 e9f06d8) · R (bu commit) · CI yeşil https://github.com/AhmetEmreOzumagi/borsai/actions/runs/38406430116

# BORSAI_FAZ9_WINDOWS_20261013 — Windows derlemesi, CI ve sunum öncesi ekran metni düzeltmeleri: teslim raporu

Görev `docs/prompts/FAZ9_WINDOWS.md`. Önceden onaylı pin K-PIN-WIN (proje sahibi başlatma cümlesinde onayladı); adım D'de
orkestratör kararı K-WIN-5 (Windows libm farkı) proje sahibi aracılığıyla geldi. Push, tag, amend yok (CI koşuları için push'u
proje sahibi yaptı). Bu görevde hiçbir model, skor ya da hüküm değişmedi: `git diff --stat 2f01a28 -- borsai models scores
registry data` boş; `app/parity` farkı boş; `build.rs`/`build_embed.rs` farkı boş.

**TABAN** `2f01a28` = origin/main; ağaçta yalnız izinli izlenmeyenler (`docs/prompts/FAZ9_WINDOWS.md` commit A'ya girdi;
`FAZ10_FABLE_STREAK_SPEC.md` ve `TUFE_2026_09.md`'ye dokunulmadı).

## 1. Commit'ler

| Adım | Hash | Konu |
|---|---|---|
| A | `63d953d` | `BORSAI_FAZ9_WINDOWS_A: Windows portability (default_python, verbatim path prefix, unix-only symlink/shell tests), NSIS bundle target, K-PIN-WIN test_5c` |
| B | `ac1d5e0` | `BORSAI_FAZ9_WINDOWS_B: screen text fixes (not-primary return cell, monitor strip label, SUM identity warning) and screenshots` |
| C | `e688f96` | `BORSAI_FAZ9_WINDOWS_C: GitHub Actions workflow (test-windows, build-windows, build-macos) and README` |
| A2 | `fc69fec` | `BORSAI_FAZ9_WINDOWS_A2: e2e static scan path separator on Windows (CI run 38387284223)` |
| C2 | `d57e2b3` | `BORSAI_FAZ9_WINDOWS_C2: workflow cargo fetch --locked, cargo test --no-fail-fast, npm test after a red cargo step` |
| A3 | `0cd882f` | `BORSAI_FAZ9_WINDOWS_A3: K-WIN-5 Windows libm last-digit differences in fixture, post_d1 row and golden floor tests (CI run 38390530487)` |
| C3 | `e9f06d8` | `BORSAI_FAZ9_WINDOWS_C3: workflow info step dumping Windows numeric differences (K-WIN-5 evidence)` |
| R | (bu commit) | `BORSAI_FAZ9_WINDOWS_R: final test runs` |

Her commit'ten sonra `test_5c` ve `test_14b` tek başına yeşil (temiz `app/` ağacı). C2 ve C3 görevin K-CI-1 iş akışına eklerdir:
C2 proje sahibinin isteğiyle (`--no-fail-fast`) ve U34 için (`cargo fetch --locked`), C3 K-WIN-5'in kanıt adımı (işi kırmızı yapmaz).

## 2. Windows tuzakları (K-WIN-3)

Windows makinesi yok; ölçüm kod okuması, Mac'te koşu ve CI'daki Windows koşularıdır (üç koşu, §5). Mac'te Windows hedefi için
`cargo check` yapılamadı: `rustup target add x86_64-pc-windows-msvc` static.rust-lang.org'dan indirme ister (görevin ağ izni
yalnız crates.io/npm) ve `tauri-build` Windows hedefinde kaynak derleyici ister.

| # | Tuzak | Ölçüm | Değişiklik | Koruyan test |
|---|---|---|---|---|
| 1 | `canonicalize` → `\\?\C:\…` | Görevin saydığı yerler doğrulandı: `config.rs` (`resolve_path` sonundaki `canonicalize`, `validate_repo_value`'daki repo `canonicalize` + `PYTHON_IMPORT` `starts_with`), `freeze.rs:87, 181-182`. **Ek (aynı sınıf):** (a) `resolve_path` `Component::Prefix`'i `/` köke çeviriyordu: Windows'ta sürücü harfi düşer (D: üzerindeki repo ile C: üzerindeki veri dizini karışabilir; UNC hiç tutmaz); (b) `post_d1.rs:471, 629-631` aynı kalıp; (c) `git.rs` `-C`'ye giden yol (testlerin `repo_dir()`'i `canonicalize` eder). **CI'da ölçüldü:** `is_within_verbatim_prefix_windows` üç koşuda da yeşil; runner'da `temp_dir().canonicalize()` `\\?\` ile başlıyor. | `config.rs`: `plain_path` (Windows'ta verbatim disk/UNC önekini düz yazıma çevirir; başka sistemde kimlik) + `canonical` (= `canonicalize` + `plain_path`); `resolve_path` öneki korur, kök = son önekin kökü, sonuç `plain_path`; `validate_repo_value`/`build_repo_root` `canonical`, Python'un bastığı yol `plain_path`. `freeze.rs`, `post_d1.rs`: iki taraf aynı biçim. `git.rs`: `-C` `plain_path`. Unix'te davranış bayt bayt aynı. Yeni bağımlılık yok (`dunce::simplified` 260 karakterden uzun yolda öneki bırakır, iki taraf farklı biçime düşebilirdi). | `config.rs`: `strip_verbatim_prefix_forms` (her sistem), `default_python_per_os`, `is_within_verbatim_prefix_windows` (`#[cfg(windows)]`: `\\?\C:\a\b` ⊂ `C:\a`, ters yön, `c:`, `\\?\C:\ab` ⊄ `C:\a`, `D:\a\b` ⊄ `C:\a`, gerçek `temp_dir`). `stage2::scenario_path_guard`'ın bağsız kısmı Windows'ta koşar ve yeşil. |
| 2 | Sembolik bağ testleri | `stage2.rs` (`scenario_path_guard`: 7 `std::os::unix::fs::symlink`) ve `e2e.rs` (`freeze_flow`: 4) Windows'ta **derlenmezdi bile**. `config.rs`/`scenario.rs`'te bağ oluşturan test yok (yalnız `symlink_metadata` okuması). | `scenario_path_guard`: bağlı iki blok `#[cfg(unix)] { … }` (+ `file_listing`); bağsız yol bekçisi iddiaları her sistemde. `freeze_flow` (repo modu + bağ; `#[ignore]`) `#[cfg(unix)]`. | Unix'te aynı iddialar aynı sırayla (zayıflama yok). |
| 3 | Sabit `/tmp` ve `.venv/bin/python` | `stage3.rs:584` (`todo_block_shape`), `:1506` (`post_d1_todo_block_shape`): saf dizeler. `:822` (`wizard_fixtures`): `freeze_result.json` fikstürünün belirlenimci dizesi; test `#[ignore]` (repo modu). | `:584`, `:1506`: kök `temp_dir().join("borsai_x")`, Python `default_python(&root)` (K-WIN-1), beklenen `PY_REL` (`.venv/bin/python` / Windows `.venv\Scripts\python.exe`), "cd" satırı kökten. `:822` **bilerek değişmedi** (`temp_dir` fikstürü makineye bağlardı; dosya sistemine dokunmaz, Windows'ta aynı dizeyi üretir). Öbür geçişler (`:93, 621, 744, 1495`, `:1644`) `#[ignore]` ya da `#[cfg(unix)]`. | Unix'te beklenen dizeler bayt bayt aynı; Windows'ta iki test yeşil. |
| 4 | İzin bitleri | Uygulama çıktısının `mode`'unu denetleyen test yok. `PermissionsExt` + `#!/bin/sh` sahte Python kullanan üç testten `freeze_refuses_when_preflight_blocked` `cfg`'siz idi (Windows'ta derlenmezdi). | `freeze_refuses_when_preflight_blocked` `#[cfg(unix)]` (kardeşleri `tufe_source_and_blocker`, `post_d1_wizard_fixtures` gibi). | Unix'te aynen. |
| 5 | Repo-göreli dize yollar | JSON yolları `format!("registry/…")`, `data/outcomes/{t}.csv`, `app/parity/incidents/…` ile `/`; `rel_of` `\\`→`/`; OS yoluna `Path::join`. CI'da bütün `rel_path` fikstür alanları birebir tuttu. | Yok. Yeni kodda sabit Mac yolu ya da kabuğa özel sözdizimi yok. | Fikstür karşılaştırmaları (`stage2/stage3/sade.rs`). |
| 6 | `build.rs` git | `build_embed.rs: git_command`; hata → `"UNKNOWN"`, derleme durmaz; CI `fetch-depth: 0`. `build.rs` repo kökünü `canonicalize` eder: Windows'ta `git -C \\?\D:\…` gider. Windows derlemesi CI'da tamamlandı (`build-windows` yeşil); BUILD_INFO'nun HEAD'i loglarda görünmez. | Yok (`build.rs` yazılabilir değil). | — (ilk Windows açılışında "Hakkında"da derleme HEAD'i `e9f06d8…` mi, `UNKNOWN` mu bakılmalı). |

Ek Windows bulguları (altı maddenin dışında):

- **vitest ayırıcı (adım 0b, onaylı):** `no_frontend_math.test.ts` (U25), `sade_static.test.ts` (U19/U21), `u52_declaration.test.ts`
  (U52) göreli yolu `/`'li izin listeleriyle karşılaştırıyordu; Windows'ta `render\format.ts`. Yalnız `rel` yardımcısı ayırıcıyı
  `/`'ye çevirir; macOS'ta özdeş. Proje sahibine soruldu, "Uygula". CI'da vitest 377/377.
- **CI 1. koşu (A2):** `tests/e2e.rs` `observed_streak_user_only_in_scenario_module` (ignore'suz statik tarama) kaynak yolunu
  `strip_prefix(...).display()` ile kurup `"commands/scenario.rs"` ile karşılaştırıyordu (Windows'ta `commands\scenario.rs`). Yalnız
  ayırıcı. Proje sahibinin isteğiyle bütün Rust test dosyaları aynı tuzak için tarandı: başka vaka yok (`stage2.rs:529`,
  `stage3.rs:1642-1644` `#[cfg(unix)]`; `/REPO` fikstürleri `#[cfg(unix)]` testten; `scores_oot_panel_real.json`'daki mutlak yol
  karşılaştırılmaz; öbür `path` alanları `format!` ile `/`'li ya da `"FIXTURE"`). cargo ilk kırmızı ikilide durduğu için C2.
- **U34 `no_network.rs` (C2, öngörülen):** `cargo metadata --locked --offline --filter-platform aarch64-apple-darwin` Windows
  runner'ında macOS paketleri önbellekte olmadığından düşerdi. Test değişmedi; iş akışına `cargo fetch --locked`. 2. ve 3. koşuda
  yeşil.
- **CI 2. koşu: Windows libm farkı (A3, K-WIN-5).** 7 kırmızı, hepsi sayısal: `stage2` `u40_streak_and_undefined`,
  `u7_veyas_four_refusals`; `stage3` `official_conditional_return_uses_record_only`, `registry_view_synthetic`,
  `u52_record_fixtures` (fikstürler); `stage3::official_summary_post_d1_row` (`0.6f64.powi(3)` Windows'ta `0.21599999999999997`,
  kayıttaki S `0.216`); `golden_parity` B10 bit-eşit tabanı. Uygulama:
  - `stage2`/`stage3` fikstür yardımcıları: macOS'ta bayt karşılaştırması aynen; öbür sistemlerde `tests/fixture_cmp` JSON'u
    ayrıştırır: yapı, anahtarlar ve sıraları, metinler, mantıksal değerler, null ve tamsayılar birebir; kayan noktalı sayılar
    |Δ| ≤ 1e-9; tolerans içi farklar `target/tmp/fixture_numeric/`'e dökülür. Yeni `fixture_cmp_rules` (her sistemde): tolerans içi
    kabul; tolerans dışı, metin, tamsayı, null, uzunluk, anahtar, anahtar sırası, kayan/tamsayı türü, bozuk JSON KIRMIZI.
    `sade.rs`, `oot_panel.rs`, `stage4.rs` fikstür karşılaştırmaları Windows'ta zaten yeşildi; değiştirilmedi.
  - `official_summary_post_d1_row`: beklenen S `powi` yerine kayda yazılan değerin kendisi (`powers06()`); macOS'ta iddia aynı.
  - `golden_parity`: B10 tabanı yalnız macOS'ta; Windows'ta model başına tablo basılır. `app/parity/` değişmedi.
  - **Doğrulama (3. koşu, C3 bilgi adımı):** Windows'ta yeniden üretilen fikstürlerin depodakinden farkı (karşılaştırılmayan, skor
    bağlı fikstürler hariç): **9 dosya, her birinde tek satır, tek alan**: `price_hint[3].price` (arz fiyatı × `1.1f64.powi(10)`),
    NETGL `66.19230758175205` → `66.19230758175206` (|Δ| 1.42e-14; `ceiling_netgl_j0/j2/j3`, `record_ceiling_j0/j3`,
    `record_ceiling_path_j3`, `record_ceiling_u52_j2/j3`) ve VEYAS `352.74897457360026` → `352.7489745736003` (|Δ| 5.68e-14;
    `ceiling_veyas_j0`). Yol ya da metin farkı yok; S vektörleri birebir. Ekranda fiyat 2 ondalıkla gösterildiği için görünür
    fark yok (66.19 TL, 352.75 TL). Karşılaştırıcının dökümü aynı farkları listeledi.
  - **Golden, Windows (2. ve 3. koşu, birebir aynı):** model başına bit-eşit satır / satır, maks |Δ|: `v1_5_h99` 390/392 1.11e-16;
    `v1_6_h99` 390/392 1.11e-16; `v1_5_market20_v0` 392/395 5.55e-17; `pb_v0` 389/392 1.14e-13; `ceiling_hazard_v0` 391/392
    1.11e-16; `pb_ceiling_v0` 387/392 1.14e-13; `ceiling_path_v0` 467/468 1.11e-16; `pb_ceiling_path_v0` 461/468 1.14e-13;
    `ceiling_hazard_v1_clip` 608/616 2.78e-16; `ceiling_hazard_v1_real` 614/616 2.78e-16; `ceiling_hazard_v1_pooled` 614/616
    2.22e-16; `fall_d10_v0_pooled` 634/635 5.55e-17; öbür 15 model bütün satırlarda bit-eşit. macOS tabanından eksik: 13 modelde
    1–8 satır. 27/27 model, bütün satırlar 1e-9 içinde.
- **Test ikilisi manifest riski: gerçekleşmedi.** Üç koşuda da bütün test ikilileri açıldı; `STATUS_ENTRYPOINT_NOT_FOUND` yok.
- **`app/dist` olmadan `cargo test`:** test profili `devUrl`'yi kullanır; CI test işi `npm run build` istemedi.
- **Önceden var olan uyarı (değişmedi):** Tauri, `identifier` `tr.borsai.app`'in `.app` ile bitmesine uyarı verir (Mac ve Windows
  derlemesinde).
- **Repo modu Windows'ta (K-WIN-4):** hedef değil, denenmedi. Bilinen engeller: `borsai/tufe.py:48` `APPEND_COMMAND`
  `.venv/bin/python` ile başlar (dokunulmadı), e2e betikleri bash'tir, komut bloklarındaki `$(git rev-parse HEAD)` kabuk
  sözdizimidir. README "repo modu macOS/Linux" der.

## 3. Değişen dosyalar ve neden

| Dosya | Adım | Neden |
|---|---|---|
| `app/src-tauri/src/commands/config.rs` | A | K-WIN-1 `default_python`; tuzak 1 (`plain_path`, `canonical`, `strip_verbatim_prefix`, `resolve_path` öneki); birim testleri |
| `app/src-tauri/src/commands/freeze.rs`, `post_d1.rs` | A | tuzak 1 |
| `app/src-tauri/src/commands/git.rs` | A | tuzak 1 (`-C` düz yol) |
| `app/src-tauri/tauri.conf.json` | A | K-WIN-2: `targets` + `nsis`; `bundle.windows.nsis` = `installMode: currentUser`, `languages: ["Turkish", "English"]`, `displayLanguageSelector: true`; imza yok, `msi` yok; `icon.ico` zaten listede |
| `app/src-tauri/tests/stage2.rs`, `stage3.rs`, `e2e.rs` | A, A2, A3 | tuzak 2–4; A2 ayırıcı; A3 K-WIN-5 |
| `app/src-tauri/tests/fixture_cmp/mod.rs` (yeni) | A3 | K-WIN-5 macOS dışı fikstür karşılaştırıcısı |
| `app/src-tauri/crates/borsai_predict/tests/golden.rs` | A3 | K-WIN-5: B10 yalnız macOS |
| `app/src/i18n/tr.ts` | A, B | A: K-WIN-1 metinleri; B: K-TXT-1..3 |
| `app/tests/no_frontend_math.test.ts`, `sade_static.test.ts`, `u52_declaration.test.ts` | A | vitest ayırıcı (onaylı) |
| `tests/test_faz8_model.py` | A | K-PIN-WIN: `APP_TASKS` sonuna `("BORSAI_FAZ9_WINDOWS_", "BORSAI_FAZ9_WINDOWS_R:")` |
| `docs/prompts/FAZ9_WINDOWS.md` | A | görev dosyası |
| `app/src/sade/render/common.ts`, `sonuc.ts`, `analiz.ts`, `giris.ts`, `app/src/sade/sade.css` | B | K-TXT-1..3 |
| `app/tests/sade_render.test.ts` | B | K-TXT pinleri |
| `app/src/dev/demo.ts` | B | görüntü koşusu `winSteps` (yalnız geliştirme) |
| `app/docs/screens/v2/win_01..04_*.png` | B | yeni ekran görüntüleri |
| `.github/workflows/build.yml` | C, C2, C3 | K-CI-1; C2 `cargo fetch --locked`, `--no-fail-fast`, `npm test` `if: !cancelled()`; C3 bilgi adımı |
| `README.md` | C | K-CI-2 |
| `app/README.md` | C | Windows/CI bölümü, "yalnız macOS arm64" cümlesi, kapı satırı K-TXT-1'e göre |
| `docs/app/WINDOWS_RAPOR.md`, `docs/app/windows_test_runs.txt` | R | bu rapor ve test günlüğü |

**K-WIN-1 seçimi:** metin işletim sisteminden bağımsız: `SETTINGS.python` "Python yolu (boşsa <repo_root> içindeki .venv
Python'u)", sade Ayarlar `pythonPlaceholder` "boşsa repo içindeki .venv Python'u". Rust'tan varsayılan yolu göstermek yeni bir
komut alanı isterdi; gerek görülmedi.

**Eklenen bağımlılık:** yok (`Cargo.toml`, `Cargo.lock`, `package.json`, `package-lock.json` değişmedi).

**Yapılmayan (bilerek):** `build.rs`/`build_embed.rs`, `app/scripts/*` (yazılabilir değil; görüntüler `screens_v2.sh`'nin
komutlarıyla aynı kalıpta, `VITE_BORSAI_DEMO_WIN=1` eklenerek elle koşturuldu), `borsai/tufe.py`.

## 4. K-TXT-1..3: önce / sonra

| | Önce | Sonra | Görüntü |
|---|---|---|---|
| K-TXT-1 (Tahmin sonucu ve Analiz getiri tablosu, öne çıkmayan D1/D3/D10 "Geçmiş test") | `≈ fark net değil` | `· birincil değil` (`SADE.notPrimaryMark` + `SADE.notPrimaryText`); satırda hüküm sözcüğü yok; dosyadaki keşif hükmü gösterilmez. D5: "birincil: ✓ geçiyor" (aynen). Değer hücrelerindeki gri `≈` ve `approxTip` aynen. `approxText: "fark net değil"` perf sayım cümlesi için aynen (`:615` testi değişmedi). | `app/docs/screens/v2/win_01_sonuc_birincil_degil.png`, `win_04_analiz_birincil_degil.png` |
| K-TXT-2 (Monitör veri şeridi) | "Üretimdeki model 4 — kendi sorusunda öne çıkan" | "Üretimdeki model 4 — kendi sorusunda ölçülen" (perf ekranının `stripProdSub`'ı); sayı `PRODUCTION_MODELS.len()` aynen | `win_02_monitor_serit.png` |
| K-TXT-3 (Yeni arz girişi, Denetim paneli) | Not: "Tutmayan bir özdeşlik bu alanı kullanan modelleri durdurur; satır kırmızı görünür." SUM tutmazsa kırmızı "× tutmuyor" | Not: "ID-A, ID-B, ID-C tutmazsa PB modelleri durur; SUM tutmazsa yalnız uyarıdır, model durmaz." SUM tutmazsa `⚠ tutmuyor (uyarı)` (`.mark-warn`, kehribar). ID-A/B/C aynen kırmızı. | `win_03_giris_sum_uyari.png` (NETGL; görüntü için ek satış alanı 12 500 000 yazıldı, kayıt yazılmadı) |

Görüntü koşusu: `VITE_BORSAI_DEMO=1 VITE_BORSAI_DEMO_V2=1 VITE_BORSAI_DEMO_WIN=1 npm run tauri dev -- --features snapshot`,
uygulama verisi geçici dizinde, 1440 × 900, `sips -Z 1440`; koşu öncesi/sonrası `registry/` ve `data/` sha listesi aynı (2 246
dosya). Bu görüntüler macOS'tan alındı.

**U-kuralı sapması: yok.** SPEC_APP §3a (satır 244) "2 = 4 + 5 + 6 tutmuyorsa sarı uyarı (RET değil); ID-A/B/C kırmızı" der;
K-TXT-3 kodu şartnameye uydurur. U19 ve U22 etkilenmez. Orkestratöre not: tasarım belgesi `docs/design/ui_v2/README.md:88`
hâlâ "≈ fark net değil işaretiyle durur" der (SPEC_APP/EK değil; bu görevde yazılabilir değil).

**Değişen testler (K-PIN-WIN ve K-WIN-5):**
- vitest `sade_render.test.ts`: "öne çıkan altın; öne çıkmayan aynı değer + ≈" (`notPrimaryLabel`); "getiri tablosu: … öbür
  ufuklar · birincil değil (hüküm sözcüğü yok)" (eski `:394`); Analiz "getiri paneli" (+`notPrimaryRows`); Monitör ilk testi
  (+şerit alt etiketi); Giriş ID-A testi (+`.mark-fail`); yeni "K-TXT-3: SUM tutmazsa uyarı…". `:615` değişmedi.
- vitest ayırıcı: üç tarama dosyasında yalnız `rel`.
- cargo: `config.rs` 3 yeni birim testi (1'i yalnız Windows); `stage2::scenario_path_guard` (cfg blokları);
  `stage3::{todo_block_shape, post_d1_todo_block_shape}`; `stage3::freeze_refuses_when_preflight_blocked` ve `e2e::freeze_flow`
  `#[cfg(unix)]`; A2 `e2e::observed_streak_user_only_in_scenario_module` (ayırıcı); A3 `stage2`/`stage3` fikstür yardımcıları,
  yeni `stage2::fixture_cmp_rules`, `stage3::official_summary_post_d1_row`, `golden::golden_parity` (B10 yalnız macOS).
- pytest: `tests/test_faz8_model.py` `APP_TASKS` satırı (test_5c'nin kendisi değişmedi).
- Bekçi testleri (kasa, sıra, hijyen, temizlik, `test_faz7_vault`, `test_outcome_guard`, `test_scoring`), `app/parity/` ve
  `golden_unchanged` değişmedi. macOS'ta bütün bit-eşitlik iddiaları aynen.

Adım 0b (geçici `git clone --local` klonunda prova; adım C sonunda silindi): A + B taslağıyla Mac'te kırılan testler yalnız
vitest `sade_render.test.ts`'teki iki K-TXT-1 pini; cargo'da kırılan yok. Liste K-PIN-WIN genel kuralına uydu.

## 5. CI

İş akışı `.github/workflows/build.yml` (YAML Ruby `YAML.safe_load` ile ayrıştırıldı; actionlint yok; yapı denetimi betiği
her değişiklikten sonra 0 hata).

| Koşu | HEAD | test-windows | build-windows | build-macos |
|---|---|---|---|---|
| [38387284223](https://github.com/AhmetEmreOzumagi/borsai/actions/runs/38387284223) | `e688f96` | KIRMIZI 6 dk 20 sn (e2e ayırıcı → A2; sonraki ikililer koşmadı) | koşmadı | YEŞİL 3 dk 39 sn, `BorsAi-macos-e688f96` 3 551 606 bayt |
| [38390530487](https://github.com/AhmetEmreOzumagi/borsai/actions/runs/38390530487) | `d57e2b3` | KIRMIZI 10 dk 36 sn: cargo 149 / 7 kırmızı (sayısal) / 12 ignored; vitest 377 → A3 | koşmadı | YEŞİL 2 dk 45 sn, `BorsAi-macos-d57e2b3` 3 551 593 bayt |
| [38406430116](https://github.com/AhmetEmreOzumagi/borsai/actions/runs/38406430116) | `e9f06d8` | **YEŞİL 11 dk 05 sn**: cargo **157 passed / 0 failed / 12 ignored**; vitest **24 dosya, 377 passed**; bilgi adımı §2 | **YEŞİL 12 dk 50 sn**: `BorsAi_0.1.0_x64-setup.exe` → artefakt `BorsAi-windows-e9f06d8` (zip 2 835 390 bayt) | **YEŞİL 2 dk 22 sn**: `BorsAi_0.1.0_aarch64.dmg` → artefakt `BorsAi-macos-e9f06d8` (zip 3 551 572 bayt) |

Son koşu 2026-10-13 13:37–14:01 UTC. İki artefakt indirilebilir (Actions koşu sayfası, "Artifacts").

**Gerçek Windows açılışı bu oturumda doğrulanmadı.** Proje sahibi ya da bir Windows kullanıcısı kurup üç ekrana bakacak (Tahmin
sonucu getiri tablosu "· birincil değil", Monitör şeridi "kendi sorusunda ölçülen", Yeni arz girişi SUM uyarısı); ayrıca
"Hakkında"da derleme HEAD'i (tuzak 6) ve kişisel kaydı Belgeler'e dışa aktarma (yol bekçisi, tuzak 1).

Mac yerel derleme (adım A gereği; `npm run tauri build`, HEAD `e688f96`): `nsis` hedefi Mac'te sessizce atlandı, hata yok;
`BorsAi.app` + `BorsAi_0.1.0_aarch64.dmg` (3 562 647 bayt, sha256 `0c5cd45a86f9…`); `borsai-app` sha256 `1373d7f15cdf…`.

## 6. Test sayıları

| Takım | Taban (`2f01a28`) | Son |
|---|---|---|
| pytest | 952 (paralel `-n 6`) | 952 passed in 1194.41s (sıralı, ayrılan yok) |
| cargo Mac (`test.sh`, include-ignored, 5 e2e atlanır) | 164 | 167 passed / 0 failed (+2 `config.rs`, +1 `fixture_cmp_rules`) |
| cargo Mac (yalın, CI gibi) | — | 159 + 13 ignored |
| cargo Windows (CI) | — | 157 + 12 ignored (Mac yalından: üç `#[cfg(unix)]` test ve `freeze_flow` çıkar, Windows birim testi girer) |
| vitest | 376 (24 dosya) | 377 (24 dosya) (Windows'ta da 377) |
| parity (`app/parity/test_gen_golden.py`) | 8 | 8 passed |
| `golden_unchanged.sh` | YEŞİL | YEŞİL |
| `gen_golden --check` | 35/0 | 35/0 |

Ara koşular (her commit öncesi `test.sh` + paralel pytest, `test_14b` yalnız commit öncesi ayrıldı) ve bütün komutlar:
`docs/app/windows_test_runs.txt`.

## 7. Hijyen sayımları

SEALED kasa kodları (`registry/oot/cohort_pre_h99.csv`, 64 kod; sözcük sınırıyla, büyük/küçük harf duyarlı) ve bülten adı
kalıbı `th[bm]` + 8 hane; kodlar yazılmadı, yalnız sayıldı:

- `README.md`, `.github/workflows/build.yml`, `app/README.md`, `docs/prompts/FAZ9_WINDOWS.md`, bu rapor, test günlüğü: kasa kodu
  0, bülten adı 0 (6 dosya).
- Dört ekran görüntüsü (macOS Vision OCR metni): kasa kodu 0, bülten adı 0; görüntülerde yalnız takipteki 7 arz. OCR'da
  `win_01`/`win_04` getiri tablolarında "geçemiyor", "ayırt edilemiyor", "fark net değil" 0.

## 8. Yapılmayanlar ve açık sorular

1. **Repo modu Windows'ta** hedef değil ve denenmedi (§2). Gerekirse ayrı görev: `tufe.py` `APPEND_COMMAND`, bash e2e betikleri,
   komut bloklarındaki kabuk sözdizimi.
2. **`--include-ignored` koruma testi (AUDIT_4 bulgu 9):** yapılmadı. CI'da Windows `cargo test` ignore'luları ignore bırakır;
   `test.sh`'nin atlama listesini sınayan statik test hâlâ yok.
3. **Sürüm etiketi ve release:** iş akışı `v*` etiketiyle de koşar ama release oluşturmaz; karar proje sahibinin. Paketler
   imzasız (macOS ad-hoc, Windows imzasız; SmartScreen ve Gatekeeper uyarıları README'de).
4. **Tuzak 6:** `build.rs` yazılabilir değildi; Windows'ta "Hakkında" `UNKNOWN` gösterirse `build.rs`'te `canonicalize` sonrası
   öneki soymak için onay gerekir.
5. **K-WIN-5'in kapsamı:** toleranslı karşılaştırma yalnız `stage2`/`stage3` fikstür yardımcılarında; `sade.rs`, `oot_panel.rs`,
   `stage4.rs` Windows'ta bayt bayt tuttu. Gelecekte bu dosyaların fikstürüne `powi`/`exp`/`ln` türevi bir sayı girerse aynı
   karşılaştırıcı oraya da bağlanmalı.
6. Actions sürümleri `@v4` (checkout, setup-node, upload-artifact), `Swatinem/rust-cache@v2`, `dtolnay/rust-toolchain@stable`.
   Özel depoda dakikalar Windows ×2, macOS ×10 çarpanlı; `build-macos` her koşuda paralel çalışır. C3 bilgi adımı test-windows'a
   ≈ 1.5 dk ekler; gerekirse sonra kaldırılabilir.

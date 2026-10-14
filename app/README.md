# BorsAi masaüstü uygulaması (`app/`)

Şartname: [`docs/app/SPEC_APP.md`](../docs/app/SPEC_APP.md) (Fable, EK 1 dahil; bağlayıcı).
Tauri 2 + Rust arka uç + sade TypeScript (Vite, çerçeve yok). Ağ erişimi yok; macOS arm64 ve Windows x64 (aşağıda).

Bu sürümde tamamlanan aşamalar (SPEC_APP §7):
- **Aşama 0 (kurulum ve iskelet):** araç zinciri, Tauri iskeleti, `build.rs` ile model gömme.
- **Aşama 1 (predict + parite):** `src-tauri/crates/borsai_predict` (saf Rust portu), açılış bütünlük
  denetimi, `predict_all` komutu, Python altın vektörleri ve parite testleri (`parity/README.md`).
- **Aşama 2 (ekranlar):** girdi formu (§3a; anında Rust denetimi, sicil girdi belgesinden salt okuma
  kopyası), sonuç ekranı (§3b; grup A/B, RET blokları, uyarı rozetleri, model kartı, backtest tipik
  hata satırı), senaryo modu ve kişisel kayıt sakla/listele/aç/sil (§3c, §3f'nin bir kısmı), f6 repo
  modu (Python `borsai.market20`) / elle / boş (§3a.2), koşullu tavan şeridi ve eğrisi (§3g, EK 1),
  Ayarlar ve Hakkında. Ekran görüntüleri: [`docs/screens/`](docs/screens/README.md).
- **Aşama 3 (dondur akışı):** resmi kayıt sihirbazı (§3e; 6 adım, "Şimdi yapılacaklar" komut bloğu,
  iptal akışı), kaynak belge kopyalama + `MANIFEST.json`, girdi belgesi yazıcı (Python
  `pretty_json_bytes` ile **bayt-eşit**), Rust `validate_inputs` portu, yetkili Python denetimi,
  `borsai.freeze` çağrısı ve kaydın parite denetimi, sicil ekranı ve arz sayfası (§3g resmi görünüm:
  koşullu değerler yalnız dondurulmuş kayıttaki `models[].output.S`'ten), kişisel kayıt dışa aktarma.
- **Aşama P (Faz 4 tavan yolu portu, EK 2):** P1 `path.rs` portu ve 19/19 altın parite; P2 gösterim
  (Grup A sütunları, Grup C getiri dağılımı, "Getiri (koşullu)" sekmesi, sicil ve model kartı).
- **Aşama 4 (doğruluk paneli):** `scores.json` okuyucu (repo/gömülü; §2.3), §2.5 sürüm davranışı ve
  **fail-closed** bütünlük denetimi (`scores_view`), §3d paneli: iki BAĞIMSIZ terazi (geçmiş veri testi
  ve canlı sicil), küçük-n üç hâli (n < 10 satır tablosu, 10 ≤ n < 30 "yetersiz örnek", n ≥ 30 hüküm),
  birincil hücre rozeti, self-reported / RETRO / atlanan / geçersiz kullanım / iptal edilen / ayrı
  modeller bölümleri ve EK 2 §5 koşullu skor bloğu. Hüküm metni her zaman dosyadaki `verdict` alanıdır.

Ön uç hiç hesap yapmaz: bütün sayılar Rust komutlarından gelir (`predict_all`, `ceiling_display`,
`streak_view`, `check_form`, `score_hints`, `scores_view`); TS yalnız biçimlendirir ve SVG çizer. Bu,
`tests/no_frontend_math.test.ts` statik taramasıyla zorlanır (çarpma/bölme yalnız `render/format.ts`
yüzde biçimlendirmesinde ve `render/svg.ts` piksel koordinatında).

## Sade görünüm (UI v2; FAZ9_APP_UI)

Varsayılan görünüm **sade görünüm**dür (onaylı tasarım `docs/design/ui_v2/`, Safir paleti; öğe ↔ veri haritası
`docs/app/UI_V2_HARITA.md`, teslim raporu `docs/app/UI_V2_RAPOR.md`). Eski arayüz silinmedi: **Ayrıntılı görünüm** adıyla kodu ve
testleriyle aynen durur. Seçim Ayarlar'dadır (`config.json` → `ui_view`: `SADE` | `AYRINTILI`; alan yoksa `SADE`, eski config
dosyaları aynen okunur). Her sade ekranda "Ayrıntılı görünüm" bağlantısı karşılık gelen eski ekranı açar; ayrıntılı görünümün sol
gezinmesinin sonundaki "Sade görünüme dön" geri getirir. İkisi de seçimi kalıcı yazar (`set_ui_view`).

| Sade ekran | Rust komutları | Eski karşılığı |
|---|---|---|
| Monitör | `monitor_view`, `headline_gate`, `perf_view` | — (yeni) |
| Yeni arz girişi | `check_form`, `list_input_documents`, `read_input_document`, `market20_via_python`, `predict_all` | Girdi |
| Tahmin sonucu (hesaplayıcı) | `ceiling_display`, `ceiling_summary`, `headline_gate`, `perf_view`, `save_scenario` | Sonuç |
| Analiz (hesaplayıcı, kırılma kartı) | `arz_view`, `break_view`, `arz_streak`, `record_summary`, `record_ceiling`, `post_d1_view` | Sicil → arz sayfası |
| Model performansı | `perf_view`, `headline_gate` | Doğruluk |
| Sicil | `registry_view`, `monitor_view`, `break_view`, `post_d1_records`, `read_record_json` | Sicil |
| Kayıtlarım | kişisel kayıt komutları | Kişisel kayıtlar |
| Ayarlar ve Hakkında | `get_config`, `set_config`, `validate_repo`, `set_ui_view`, `app_info` | Ayarlar, Hakkında |
| Sihirbazlar | eski `screens/registry.ts` aynen, sade kabukta | Dondur, D1 sonrası |

- **Kod:** `src/sade/` (kabuk `app.ts`, saf render `render/*.ts`, ekran bağlayıcıları `screens/*.ts`, `sade.css`, `fonts.ts`).
  `src/screens/*.ts` ve `src/render/*.ts` mevcut dosyaları değişmedi; `render/svg.ts` (koordinat fonksiyonları) ve
  `render/format.ts` (biçimleyiciler) yalnız ekleme. Metinler `i18n/tr.ts`'te yeni dışa aktarımlar (`SADE`, `SADE_NAV`,
  `VERDICT_PLAIN`, `VERDICT_MARK`). Rust: `src-tauri/src/commands/sade.rs`, `sade_break.rs`.
- **Hesap yok:** bütün sayılar Rust komutlarından; ön uç yalnız biçimler ve SVG koordinatı hesaplar (`no_frontend_math` taraması
  `src/sade/**`'ı da kapsar). Yeni komutlar skor ya da metrik hesaplamaz: okur, eşler, sayar, sıralar.
- **Ana ekran kapısı (`headline_gate`):** bir çıktı ancak dosyada önceden ilan edilmiş birincil hücresinin `verdict`'i "geçiyor"
  ise altın renkte öne çıkar; değilse aynı değer gri ve "≈" işaretiyle durur; getiri tablosunda o satırın "Geçmiş test" hücresi
  "· birincil değil" yazar, keşif hükmü gösterilmez (FAZ9_WINDOWS K-TXT-1). Kırılma modeli için
  `scores_break.json` `promotion`. Hüküm hücresi her yerde dosyadaki `verdict`'tir; sade açıklama ayrı satırdır.
- **Seri hesaplayıcı** ("Seri j gün sürdüyse yarın ne olur?"): j = 0–9; senaryoda `ceiling_display(S, j)`, resmi görünümde
  `record_summary(T, file, j, jObserved)` + `record_ceiling(T, file, j)`, gözlenen j `arz_streak`'ten (`streak_view` ile aynı okuyucu,
  veri kökünden), "Gözlenene dön". Kullanıcı beyanı şeridi (U52) yalnız ayrıntılı görünümde.
- **Kırılma kartı** yalnız makine kaydından ve `scores_break.json`'dan; katsayılar `models/break_floor_v0.json`'dan, dosyanın sha'sı
  makine kaydındaki `params_sha256` ile eşitken (değilse kart kapanır). Senaryo modunda kırılma tahmini yok (EK 5 portu ayrı görev).
- **Bağımsız mod:** Yeni arz girişi, Tahmin sonucu, Kayıtlarım ve Ayarlar çalışır. Kişisel modda sicil gömülü anlık görüntüdür
  (FAZ9_SNAPSHOT): Monitör, Analiz (kırılma kartı dahil), Sicil ve Model performansı derlemeye gömülü salt okunur kopyadan okur
  (`registry/ipos.csv`, `registry/{records,inputs,post_break,push_proofs}/**`, kayıtlı arzların `data/outcomes/<T>.csv`'si,
  `scores/scores_{break,post_d1}.json`, `models/break_floor_v0.json`). Açılışta `<app_data_dir>/snapshot/<derleme sha7>/` altına
  aynı göreli yollarla yazılır ve manifestle (yol → sha256 → bayt; `BUILD_INFO`) doğrulanır; her okumada yeniden doğrulanır, hiç
  yazılmaz; tutmazsa `SNAPSHOT_INTEGRITY_FAILED` ve ekranlar kapalı. Anlık görüntüde git çağrılmaz (kayıt kanıtı ve `git status`
  derleme anınınki). Monitör "Veri: gömülü anlık görüntü · derleme <sha7> · son sonuç <tarih>" der; yeni arz ve sonuç için yeni
  paket gerekir. Dondurma, D1 sonrası kayıt ve iptal repo modu ister.
- **Yazı tipleri:** IBM Plex Sans / Sans Condensed / Mono, `@fontsource/*` 5.3.0 (devDependencies, OFL-1.1; yalnız latin ve
  latin-ext). Vite pakete gömer; ağ yok (CSP ve `dependencies` aynen).
- **Hareket:** yalnız CSS, `prefers-reduced-motion`'da yok; sayı sayma animasyonu yok.
- **Ekran görüntüleri:** `bash app/scripts/screens_v2.sh` (yalnız geliştirme; asıl repo salt okunur, uygulama verisi geçici dizinde) →
  `app/docs/screens/v2/*.png`. Eski `app/docs/screens/*.png` ve eski görüntü betikleri değişmedi (eski demo koşusunda görünüm ayrıntılıdır).
- **Testler:** `src-tauri/tests/sade.rs` (gerçek repo dosyaları, görevdeki beklenen sayılar; `BORSAI_UPDATE_UI_FIXTURES=1` ile
  `tests/fixtures/ui/sade_*.json` yeniden yazılır), `tests/sade_render.test.ts`, `sade_svg_format.test.ts`, `sade_invoke.test.ts`
  (sahte `invoke` ile komut ve argümanlar), `sade_static.test.ts`.
- **Sunum öncesi düzeltmeler (FAZ9_UI_FIX; rapor `docs/app/UI_FIX_RAPOR.md`):** üst bardaki "Analiz" sekmesi ve "Tüm arzlar"
  her zaman takipteki arzların listesini açar (kod, şirket, ilk işlem günü; en yeni üstte); arz açıkken yol "Analiz › T" ve arz
  değiştirici. Sicil'de satır ya da "Aç" künyeyi yeniden çizer ve künye görünür alanın dışındaysa sayfa ona kayar
  (`prefers-reduced-motion` → anında). Hesaplayıcıda "Yarın da tavan"ın yanında "Geçmiş arzlarda" (basit kural `base_km_expanding`,
  aynı kaydın/koşunun S'i; S_{j+1}/S_j ve S × n sayımı Rust'ta: `ceiling_display` / `record_ceiling` çıktısındaki `calc`) ve modelin
  gün grupları notu (`day_groups` model dosyasından, Rust okur). Analiz'de koridorun altında işlem sayısı çubukları (`DayRow.trade_count_raw`
  aynen, `trade_count_rel` 0–1 Rust'tan; `svg.ts` piksele çevirir, `format.ts` binlik ayırıcı). Model performansı sayımları dosyadaki
  verdict'e göre ayrı (`PerfCounts`: pass / undecided / fail / other / no_verdict). Pencere 1440 × 900 ortada, en küçük 1024 × 680; çalışma
  alanı küçükse büyütülmüş açılır (`lib.rs` `setup`). Görüntü koşusunda `dev_window_size` (yalnız `--features snapshot`).

## Windows (FAZ9_WINDOWS; rapor `docs/app/WINDOWS_RAPOR.md`)

Windows x64 paketi (NSIS `.exe`, kullanıcı başına kurulum, Türkçe/İngilizce, imzasız) yerel makinede değil GitHub Actions'ta derlenir:
`.github/workflows/build.yml` (`workflow_dispatch` ya da `v*` etiketi) önce `windows-latest`'te `cargo test --workspace` + `npm test`, sonra
`npm run tauri build`; artefaktlar `BorsAi-windows-<sha7>` ve `BorsAi-macos-<sha7>`. Windows'ta hedef bağımsız (kişisel) moddur; repo modu macOS/Linux içindir.

## Araç zinciri

2026-09-22'de kuruldu, `sudo` yok. Kabuk profillerine (`~/.zshrc` vb.) dokunulmadı; araçları
yüklemek için `source app/scripts/env.sh`.

| Araç | Sürüm | Yer |
|---|---|---|
| rustup | 1.29.1 | `~/.cargo`, `~/.rustup` (`--profile minimal`, kararlı zincir) |
| rustc / cargo | 1.98.1 / 1.98.1 (aarch64-apple-darwin) | |
| nvm | 0.40.3 | `~/.nvm` (`PROFILE=/dev/null` ile) |
| Node / npm | 22.23.2 (LTS) / 10.9.8 | `nvm alias default 22` |
| Tauri CLI (`@tauri-apps/cli`) | 2.11.5 | `app/node_modules` |
| `tauri` crate / `tauri-build` | 2.11.6 / 2.6.3 | `Cargo.lock` |
| `tauri-plugin-dialog` (crate / npm) | 2.7.3 / 2.7.3 | |
| `@tauri-apps/api` | 2.11.1 | |
| Vite / TypeScript / Vitest / jsdom | 8.3.0 / 6.0.3 / 5.0.1 / 30.1.1 | |
| Xcode CLT | `/Library/Developer/CommandLineTools`, Apple clang 21.0.0 | önceden kurulu |

Kilit dosyaları commit edilir: `app/package-lock.json`, `app/src-tauri/Cargo.lock`.

## Komutlar

```bash
bash app/scripts/dev.sh      # = source app/scripts/env.sh && cd app && npm run tauri dev
bash app/scripts/test.sh     # cargo test --workspace (BORSAI_REPO ile) + npm test (tsc + vitest) + pytest app/parity
bash app/tests/e2e_freeze_tmp_repo.sh       # U28-U32: dondur akışı, GEÇİCİ KLONDA (asıl repo salt okuma)
bash app/tests/e2e_personal_isolation.sh    # U39: kişisel kayıt ve kullanıcı beyanı izolasyonu
bash app/scripts/screens.sh  # yalnız geliştirme: docs/screens/*.png'yi yeniden üretir (aşağıda)
```

İlk açılışta uygulama "Bağımsız mod"dadır. Repo modu için Ayarlar → "öneriyi kullan" (derleme anındaki
repo kökü) → Kaydet; doğrulama: `models/INDEX.json` sha'sı gömülüyle eşit, `git rev-parse HEAD`,
`.venv/bin/python -c "import borsai"` (repo içinden), uygulama verisi repo dışında.

Elle:

```bash
source app/scripts/env.sh
cd app
npm ci                          # ilk kez
npm run tauri dev               # geliştirme penceresi
npm run tauri build -- --bundles app    # src-tauri/target/release/bundle/macos/BorsAi.app, ad-hoc imza
ditto src-tauri/target/release/bundle/macos/BorsAi.app /Applications/BorsAi.app
(cd src-tauri && cargo test --workspace)
npm test
```

`--bundles app` yalnız `.app` üretir. Mac'te `.dmg` adımı `bundle_dmg.sh` hatasıyla düşebilir;
`.app` yeterlidir (kişisel kullanım, imza ad-hoc). `/Applications`'a kopyalamayı kullanıcı yapar.

`app/.gitignore`: `node_modules/`, `src-tauri/target/`, `dist/`. Kök `.gitignore`'a dokunulmadı
(SPEC_APP açık soru 5).

## Model gömme (`src-tauri/build.rs`, SPEC_APP §1.4)

- `build_embed.rs`'deki `PINNED_MODEL_IDS`: `models/INDEX.json`'un ilk 19 kaydı, açıkça sabit (son üç
  kayıt Faz 4 tavan-yolu modelleri; Aşama P1, SPEC_APP EK 2 §3.5). `build.rs` bu 19 kaydın INDEX'in ilk
  19 kaydıyla sırasıyla aynı olduğunu denetler; INDEX'e sonradan eklenen kayıtlar gömülmez ve
  "Hakkında"da "gömülmeyen" diye listelenir (bugün bu liste boş). Sıra kuralı: INDEX sırası, ek sona.
- Açılış bütünlüğü (U41): her `ceiling_path` modelinin gömülü `survival_model` kopyası, INDEX'teki seri
  modelinin sha256'sı ve gömülü dosyanın ayrıştırılmış değeriyle denetlenir; uyuşmazlık
  `INTEGRITY_FAILED / SURVIVAL_MODEL_MISMATCH`.
- Her model dosyası `include_str!` ile gömülür; INDEX'te olup diskte olmayan dosya derlemeyi kırar.
  `scores/scores.json` varsa gömülür.
- `build_info`: derleme anındaki `git rev-parse HEAD` ve `git status --porcelain -- models scores`.
  git yalnız okuma alt komutlarıyla (`rev-parse`, `status`) ve `GIT_OPTIONAL_LOCKS=0` ile çağrılır
  (paralel commit sırasında `index.lock` bırakmamak için); tek çağrı noktası `build_embed.rs: git_command`.

## Dizin düzeni

SPEC_APP §6'daki düzen. Bu aşamada dolu olanlar:

```
app/
  package.json  package-lock.json  tsconfig.json  vite.config.ts  index.html
  scripts/{env.sh, dev.sh, test.sh, screens.sh}
  src/{main.ts, api.ts, dom.ts, state.ts, types.ts, styles.css, vite-env.d.ts, i18n/tr.ts, dev/demo.ts}
  src/render/{format.ts, svg.ts, codes.ts, colors.ts, results.ts, ceiling.ts, inputs.ts,
              registry.ts, freeze.ts, accuracy.ts}                         saf render (vitest hedefi)
  src/screens/{ctx.ts, inputs.ts, results.ts, accuracy.ts, scenarios.ts, settings.ts, about.ts,
               registry.ts}
  src-tauri/
    Cargo.toml (workspace: ".", "crates/borsai_predict")  Cargo.lock  tauri.conf.json
    build.rs  build_embed.rs  capabilities/default.json  icons/
    src/{main.rs, lib.rs, state.rs, embedded.rs, clock.rs, python.rs, json_out.rs,
         commands/{mod.rs, models.rs, predict.rs, config.rs, git.rs, form.rs, inputs_doc.rs, market20.rs,
                   ceiling.rs, path.rs, scenario.rs, scores.rs, snapshot.rs, source_docs.rs, freeze.rs,
                   parity.rs, registry.rs}}
    tests/{build_embed.rs, integrity.rs, no_network.rs, stage2.rs, stage3.rs, stage4.rs, e2e.rs}
    crates/borsai_predict/
      src/{lib.rs, dec.rs, sum.rs, features.rs, pb_features.rs, horizons.rs, linear.rs, hazard.rs,
           market20.rs, survival.rs, params.rs, error.rs, output.rs}
      tests/{golden.rs, coverage.rs, dec_semantics.rs, records_parity.rs, common/mod.rs}
  parity/{gen_golden.py, test_gen_golden.py, README.md, dec_cases.json, golden/, incidents/}
  tests/{disclaimer.test.ts, no_network.test.ts, codes.test.ts, results.test.ts, ceiling.test.ts,
         scenario.test.ts, inputs.test.ts, format.test.ts, no_frontend_math.test.ts,
         registry.test.ts, freeze.test.ts, path.test.ts, u52_declaration.test.ts,
         accuracy.test.ts, helpers.ts}
  tests/{e2e_freeze_tmp_repo.sh, e2e_personal_isolation.sh}   geçici klona karşı uçtan uca
  tests/fixtures/ui/*.json        Rust komutlarının gerçek çıktısı (stage2.rs üretir ve güncelliğini sınar)
  tests/fixtures/outcomes/<durum>/SNTA1.csv   sentetik gözlenen seri (U40)
  tests/fixtures/scores/*.json    sentetik scores.json'lar (SPEC_APP §5.3; README'si yanında)
  docs/screens/*.png              ekran görüntüleri
```

## Tauri komutları

Hepsi `Result<T, AppError>`; `AppError = {code, message, detail?}` (ön uç `code`'u `tr.ts`'ten çevirir).

| Komut | Ne yapar |
|---|---|
| `app_info()` | sürüm, derleme git HEAD/durumu, INDEX sha256, gömülü/gömülmeyen modeller (açıklama, eğitim n/kesim), bütünlük |
| `predict_all(inputs, f6?)` | 19 gömülü model, INDEX sırasıyla; `borsai.freeze.run_model` alanları + `model_id`, `params_sha256`; bütünlük bozuksa `INTEGRITY_FAILED` |
| `get_config()`, `set_config(cfg)`, `validate_repo(path, pythonPath)` | `borsai.app_config/1` (`<app_data_dir>/config.json`); sürüm uyumsuzsa `config.json.bak` + varsayılan; uygulama verisi repo altına düşerse `DATA_DIR_INSIDE_REPO` |
| `check_form(stage, fields)` | §3a anında denetimleri: virgül→nokta, sayı biçimi, 2 ≥ 4, 2 ≤ 3, 4 ≥ 0, 2 = 4+5+6 (sarı), ID-A/B/C (kırmızı), aşamaya göre zorunlular, 13+14 ve 15+16 önerisi (kesin ondalık) |
| `list_input_documents()`, `read_input_document(ticker)` | repo modunda `registry/inputs/<T>.json` salt okuma (senaryoya kopya) |
| `market20_via_python(refDate?, t?)` | repo modunda §3a.2'deki Python komutu, cwd = repo, `PYTHONDONTWRITEBYTECODE=1`; ref_date = bugün (Istanbul, UTC+3) |
| `ceiling_display(models, j, ipoPriceTl?)` | S_k'dan P_L, beklenen/medyan L; `survival::conditional(S, j)`; "her zaman tavan" sabit satırı; 1.1^k fiyat eşlemesi |
| `streak_view(ticker?, userDays)` | `data/outcomes/<T>.csv` salt okuma + kullanıcı beyanı → gün gün şerit, gözlenen j, bozulma, etiketsiz gün |
| `arz_streak(ticker)` | Analiz'in gözlenen serisi: `streak_view` ile aynı okuyucu, veri kökünden (repo ya da kişisel modda gömülü anlık görüntü) |
| `save_scenario(req)`, `list_scenarios()`, `load_scenario(id)`, `delete_scenario(id)` | `borsai.app_scenario/1`, `<app_data_dir>/scenarios/<ULID>.json`; çıktılar kayıt anında Rust'ta üretilir; `record_type` yok, `official: false`; repo altı `SCENARIO_PATH_INSIDE_REPO` |
| `score_hints()` | `scores.json` (repo ya da gömülü) → model kartı alanları ve backtest MAE `model_value` (aynen; hesap yok) |
| `scores_view()` | Doğruluk paneli (§3d): kaynak (REPO/EMBEDDED), `generated_at_utc`, `as_of_session`, sha ilk 12, INDEX uyuşmazlığı, §2.5 sürüm denetimi ve §2.3 **fail-closed** bütünlük denetimi; belge olduğu gibi aktarılır (hücre hesaplanmaz, düzeltilmez, doldurulmaz) |
| `dev_snapshot(name)`, `dev_snapshot_done()`, `dev_scores_fixture(name)` | YALNIZ `--features snapshot`: ekran görüntüsü ve doğruluk panelinin sentetik skor dosyasına bağlanması (aksi hâlde `SNAPSHOT_UNAVAILABLE`) |
| `export_scenario(id, target)` | kişisel kaydı seçilen yola kopyalar; hedef repo altındaysa `SCENARIO_PATH_INSIDE_REPO` (U27), gömülü anlık görüntü altındaysa `SCENARIO_PATH_INSIDE_SNAPSHOT` |
| `freeze_preflight(t?)` | §3e adım 1: git HEAD, repo `models/INDEX.json` sha'sı = gömülü sha, `borsai.__file__` repo altında, `git status --porcelain -- registry`; T uyarı düzeyi (`RED`/`YELLOW`/`NONE`) |
| `copy_source_docs(ticker, docs)`, `read_source_manifest(ticker)` | §3e adım 2: belgeleri `registry/source_docs/<T>/` altına kopyalar, `MANIFEST.json`'a ekler; var olan dosya/giriş DEĞİŞMEZ, farklı sha → `SOURCE_DOC_CONFLICT` |
| `preview_inputs_doc(req)`, `write_inputs_doc(req, confirm)` | §3e adım 3: `registry/inputs/<T>[.PB].json` (`pretty_json_bytes` biçimi), Rust `validate_inputs`, var olan dosyayla fark ve onay |
| `inputs_pit_check(relPath)` | §3e adım 4: yetkili denetim, `borsai.registry.inputs_pit_problems` (Python) |
| `freeze_record(relPath)` | §3e adım 6: `python -m borsai.freeze`; kaydı okur, gömülü modellerle parite karşılaştırması yapar, komut bloğunu üretir |
| `cancel_record(relPath, reason)` | `python -m borsai.freeze --cancel … --reason …`; neden boş olamaz, T kuralını Python uygular |
| `registry_view()` | Sicil: `registry/records/**`, iptal bağları, `registry/ipos.csv`, `registry/push_proofs/`, git izleme (salt okuma); kişisel modda gömülü anlık görüntüden, git bilgisi derleme anınınki |
| `record_ceiling(ticker, file, j)`, `read_record_json(ticker, file)` | Arz sayfası: S vektörleri YALNIZ kayıttan; desteklenmeyen modeller adıyla listelenir (U38) |

git yalnız `commands/git.rs`'ten, beyaz liste `rev-parse`, `status`, `log`, `ls-files` ve `GIT_OPTIONAL_LOCKS=0`
ile çağrılır (U32 `git_readonly_whitelist`).

## Yalnız geliştirme bayrakları

- `BORSAI_DATA_DIR=<dizin>` (yalnız debug derleme): uygulama verisini başka dizine yönlendirir.
- `BORSAI_SCORES_FIXTURES=<dizin>` + `--features snapshot`: `dev_scores_fixture(name)` doğruluk panelini
  o dizindeki sentetik `<name>.json`'a bağlar (ekran görüntüsü koşusu; dosyalar salt okunur ve
  `synthetic: true` taşır, panel başlığında kaynak `FIXTURE` yazar).
- `cargo`/`tauri dev` özelliği `snapshot` + `BORSAI_SNAPSHOT_DIR` + `VITE_BORSAI_DEMO=1`: `src/dev/demo.ts`
  gerçek düğmelere tıklayarak ekran görüntüsü koşusunu yapar (`scripts/screens.sh`). objc2 paketleri
  `Cargo.lock`'ta zaten vardı (wry); varsayılan derlemeye girmez, üretim ön ucunda ölü koddur.

## Bilinen sapmalar

- `Cargo.lock`'ta `reqwest`/`hyper` var: Tauri 2 bunları yalnız Android/iOS hedefi için bildirir; macOS
  derlemesine girmez. U34 bu yüzden `cargo metadata --filter-platform aarch64-apple-darwin` ile sınanır
  (`src-tauri/tests/no_network.rs`).
- Kesin aritmetik `num-rational::BigRational` yerine `Dec` (BigUint katsayı × 10^i64 üs) ile: değer yine
  kesin rasyonel; `Decimal`'in 10^±10^18'e varan üslerini açmadan temsil eder (`num-rational` bağımlılığı yok).
- Python'un etiketsiz istisna fırlattığı girdilerde (ör. f1 binary64'te 0'a düşer → `math.log(0.0)`)
  Rust `DOMAIN_ERROR` döner.
- Kişisel kayıttaki `outputs[<model_id>]` şartnamedeki `{params_sha256, output}`'a ek olarak `kind`,
  `status`, `refusal` taşır (sonuç ekranı aynı render ile açsın diye); `input_dates` (T, B, son gün) ek
  alandır. Alan kaldırılmadı.
- "Tahmin et" aşama seçilene kadar kapalıdır (boş formda alanlar kapalı; senaryo belgesi aşama ister);
  aşama seçildikten sonra her zaman açıktır.
- Fixture'lar: vitest render testleri elle yazılmış sayı kullanmaz; `src-tauri/tests/stage2.rs` ve
  `stage3.rs` Rust komutlarını çalıştırıp `tests/fixtures/ui/*.json`'u karşılaştırır
  (`BORSAI_UPDATE_UI_FIXTURES=1` ile yeniden yazar). `score_hints.json` repo'daki `scores.json` ile
  değiştiği için yalnız varlığı sınanır. Doğruluk panelinin görünüm fixture'ı
  `tests/fixtures/ui/scores_views.json`'dur (`stage4.rs`): yalnız başlık alanlarını ve §2.3/§2.5
  kararlarını taşır, belgeyi `doc_file` ile `tests/fixtures/scores/` altındaki dosyaya bağlar.
- Parite uyuşmazlığı olayı `<repo_root>/app/parity/incidents/<UTC>.json`'a yazılır (şartnamedeki yol);
  uygulama repo altında yalnız `app/`, `registry/inputs/` ve `registry/source_docs/` yollarına yazar.
- Sihirbazda alan DEĞERLERİ sonuç ekranından gelir ve düzenlenemez: kayda giren değer, tahmin edilen
  değerdir. Kullanıcı yalnız kaynak belgeyi, alıntıyı ve boş alanların gerekçesini girer.
- `registry/inputs/*.json` sicilde elle yazıldığı için anahtar sırası `sort_keys` değildir; yazıcı
  bayt-eşitliği Python'un AYNI belge için ürettiği baytlarla sınanır (`stage3.rs`).
- U28'deki "3 senaryo kaydet + 1'ini dışa aktar" `e2e_freeze_tmp_repo.sh` içinde `export_scenario`
  ile koşar; repo altına dışa aktarma reddi de aynı yerde sınanır.

# FAZ9_WINDOWS — Windows derlemesi, CI ve sunum öncesi ekran metni düzeltmeleri

**Model: Claude Code / Opus · Extra**

- **TASK_ID:** `BORSAI_FAZ9_WINDOWS_20261013`
- **Klasör:** repo kökü `~/Desktop/BorsAi`
- **Ağ:** yalnız paket kayıtları (crates.io, npm). BIST, KAP, SPK, TÜİK'e istek yok. GitHub Actions'ı bu oturum çalıştırmaz; iş akışı dosyasını yazar, koşuyu proje sahibi başlatır.
- **Commit konusu öneki:** `BORSAI_FAZ9_WINDOWS_` (A, B, C, R; aşağıda).
- **Denetim kuralı (aynen):** Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir. Bu görevde hiçbir model, skor ya da hüküm değişmez.

## Rol

Uygulamanın ana mühendisisin. Proje sahibi uygulamayı yakında kapalı bir deneme grubuna verecek ve grubun çoğu Windows kullanıyor. Senin makinen Mac; Windows makinesi yok. Bu yüzden Windows derlemesini GitHub Actions yapacak, sen kodu taşınabilir hâle getirip iş akışını yazacaksın. Ayrıca dört bağımsız denetimin (`docs/fable_kitap_audit/AUDIT_4_UYGULAMA.md`) ekranda yanıltıcı bulduğu üç metni düzelteceksin. Görev bu kadardır; başka iyileştirme yapma, bulduğunu rapora yaz.

## Bağlam ve orkestratörün ölçtükleri (2026-10-13, HEAD = origin/main = `2f01a28`, `docs/` dışı ağaç temiz)

- **Kod büyük ölçüde taşınabilir.** `app/src-tauri/src` ve `app/src` altında `cfg(target_os)`, `osascript`, `/usr/bin`, `/opt/homebrew`, kabuk çağrısı yok. Dış süreç yalnız iki yerde: `commands/git.rs` (`Command::new("git")`, alt komut beyaz listesi) ve `python.rs` (`Command::new(python)`). İkisi de yalnız **repo modunda** çağrılır. Kişisel mod (deneme grubunun kullanacağı mod) Python ve git istemez; 27 + 1 model Rust'ta hesaplanır.
- **Mac'e özel tek yer:** `commands/config.rs:120` `default_python` = `repo/.venv/bin/python`. Windows'ta `.venv\Scripts\python.exe` olmalı. `app/src/i18n/tr.ts:796` ve `:2061` metinleri de `.venv/bin/python` der.
- **`borsai/tufe.py:48` `APPEND_COMMAND`** `.venv/bin/python` ile başlar. **Bu dosyaya dokunma** (`borsai/` değişikliği kasa testini kırmızı yapar ve bu görevin işi değildir). Repo modu Windows'ta bu görevin hedefi değildir; README öyle yazar.
- **Bundle:** `app/src-tauri/tauri.conf.json` `targets: ["app", "dmg"]`, `macOS.signingIdentity: "-"` (ad-hoc). Windows hedefi yok.
- **CI yok:** `.github/` dizini yok.
- **README yok:** repo kökünde `README.md` yok; yalnız `app/README.md` var.
- **Satır sonları güvende:** `.gitattributes` `* text=auto eol=lf`; Windows'ta checkout edilen `models/*.json` ve `scores/*.json` LF kalır, gömülü sha'lar tutar. Bunu yine de iş akışında `git config --global core.autocrlf false` ile çifte emniyete al.
- **Sürümler:** tauri 2.11.6 (Cargo.lock), `@tauri-apps/cli` 2.11.5, vite 8, vitest 5, typescript 6, Node 22 (`app/scripts/env.sh`), `rust-version = "1.77.2"`.
- **Test tabanı (`ee3796d`, `docs/app/ui_fix_test_runs.txt`):** pytest **952**; `bash app/scripts/test.sh` yeşil: cargo **164**, vitest **376** (24 dosya), parity 8, golden_unchanged; `gen_golden --check` **35/0**. Denetimlerden sonra `app/` değişmedi; taban aynıdır (adım 0'da ölç).
- **Ölçülmüş Windows tuzakları** (adım A'da tek tek bak, rapora yaz):
  1. `std::fs::canonicalize` Windows'ta `\\?\C:\...` (verbatim) öneki döndürür. `config.rs:188, 214`, `freeze.rs:87, 181-182`'de canonicalize edilmiş yol ile edilmemiş yol `starts_with` ile karşılaştırılıyor; Windows'ta bu yanlış `false` verebilir (U27 yol bekçisi, `SCENARIO_PATH_INSIDE_REPO`, `DATA_DIR_OUTSIDE_REPO`). İki tarafı da aynı biçime getir (`dunce::canonicalize` ya da öneki soyan küçük bir yardımcı); unix davranışı bayt bayt aynı kalsın.
  2. Sembolik bağ testleri (`config.rs`, `scenario.rs`, `tests/stage2.rs`, `tests/e2e.rs`) Windows'ta ayrıcalık ister (`ERROR_PRIVILEGE_NOT_HELD`). Bu testler Windows'ta `#[cfg(unix)]` ile dışarıda kalır ya da bağ oluşturulamazsa açıkça "SKIPPED (symlink privilege)" yazıp geçer; **unix'te hiçbir test zayıflamaz**.
  3. `tests/stage3.rs:584, 822`'de sabit `/tmp/...` yolları ve `.venv/bin/python` metni var. Sabit yollar `std::env::temp_dir()` ile; `.venv/bin/python` içeren beklentiler `cfg` ile ikiye ayrılır.
  4. Dosya izin bitleri (`mode`) denetleyen testler varsa unix'e kilitle.
  5. Repo-göreli dize yollar (`registry/source_docs/{ticker}/...`) `/` ile kalır (JSON sözleşmesi); yalnız OS yoluna çevrilirken `Path::join` kullanılır. Yeni kodda sabit Mac yolu ya da kabuğa özel sözdizimi yok (proje kuralı).
  6. `build.rs` `git rev-parse HEAD` ve `git status` çağırır; CI'da `actions/checkout` `fetch-depth: 0` ile. Git yoksa "UNKNOWN" yazar, derleme durmaz.
- **Ekran metni bulguları (AUDIT_4, kendim doğruladım):**
  1. **Bulgu 1 (KRİTİK):** `app/src/sade/render/sonuc.ts:120` ve `analiz.ts:214` `approxLabel()`; `tr.ts:1470` `approxText: "fark net değil"`. Öne çıkmayan her ufukta "≈ fark net değil" yazıyor. Oysa `scores/scores.json` `v1_5_h99` return D1 × `base_train_median`: **geçemiyor**, +0.0046 [+0.0015, +0.0079], n 89. "Fark net değil" dosyada "ayırt edilemiyor" demektir (perf sayım cümlesi onu doğru kullanıyor); öne çıkmayan hücre için yanlış sözcük.
  2. **Bulgu 2 (ORTA):** Monitör veri şeridi "Üretimdeki model 4 — kendi sorusunda öne çıkan". `commands/sade.rs:1413` `n_production: PRODUCTION_MODELS.len()` (sabit 4); `app/tests/fixtures/ui/sade_gate.json`'da öne çıkan 3 (`post_d1_hazard_v0` featured = false). Performans ekranı aynı sayıya "kendi sorusunda ölçülen" diyor (doğru).
  3. **Bulgu 7 (ORTA):** Giriş ekranı `identityNote` (`tr.ts:1639`) "tutmayan özdeşlik modelleri durdurur; satır kırmızı"; SUM satırı kırmızı "× tutmuyor" (`sade/render/giris.ts:140-141`). Oysa `commands/form.rs:225` `SHARES_SUM_MISMATCH` **warn**; hiçbir model durmaz. ID-A/B/C için durdurma doğru.

## Kararlar

### A. Taşınabilirlik ve Windows paketi
- **K-WIN-1 · `default_python`.** `cfg(windows)` → `repo\.venv\Scripts\python.exe`; diğer → `repo/.venv/bin/python`. `tr.ts`'teki iki metin "boşsa repo içindeki .venv Python'u" gibi işletim sisteminden bağımsız yazılır ya da Rust'tan gelen varsayılan yol gösterilir. Hangisini seçtiğini rapora yaz.
- **K-WIN-2 · Bundle.** `targets: ["app", "dmg", "nsis"]`. `bundle.windows.nsis`: `installMode: "currentUser"` (yönetici istemez), diller `["Turkish", "English"]`, `displayLanguageSelector: true`. İmza yok. `icon.ico` zaten var. `msi` ekleme (WiX, gereksiz).
- **K-WIN-3 · Windows tuzakları** yukarıdaki altı madde. Her biri için: ölçtün mü, değişiklik gerekti mi, hangi test koruyor. Verbatim önek için Windows'a özgü bir birim testi yaz (`#[cfg(windows)]`): `\\?\C:\a\b` ile `C:\a` için `is_within` doğru.
- **K-WIN-4 · Repo modu Windows'ta hedef değil.** Kişisel mod hedeftir. Repo modu Windows'ta çalışırsa not düş, çalışmıyorsa README "repo modu macOS/Linux" der. `tufe.py` ve `borsai/` altına dokunulmaz.

### B. Ekran metni (yalnız metin ve sınıf; model, skor, kapı mantığı değişmez)
- **K-TXT-1 · Öne çıkmayan ufuk.** Getiri tablosunda (Tahmin sonucu ve Analiz) öne çıkmayan satırın "Geçmiş test" hücresi **"birincil değil"** yazar (işaret `·` ya da `—`, `≈` değil). İpucu metni (`approxTip`) kalır. Dosyadaki keşif hükmü ("geçemiyor" dahil) **gösterilmez**; U-kuralları "hüküm sözcüğü yalnız birincil hücre için" diyorsa buna uygun kalır. `approxText: "fark net değil"` perf sayım cümlesinde "ayırt edilemiyor" için **aynen kalır**; yeni bir anahtar ekle (`notPrimaryText`), eskisini yeniden adlandırma.
- **K-TXT-2 · Monitör şeridi.** Alt etiket "kendi sorusunda ölçülen" olur (perf ekranıyla aynı). Sayı `PRODUCTION_MODELS.len()` kalır (üretimdeki model sayısı doğru 4'tür; yanlış olan etiketti).
- **K-TXT-3 · Giriş özdeşlik notu.** Not: "ID-A, ID-B, ID-C tutmazsa PB modelleri durur; SUM tutmazsa yalnız uyarıdır, model durmaz." SUM satırı tutmadığında işaret ve sınıf uyarı (sarı/nötr), "× tutmuyor" kırmızı değil. ID-A/B/C davranışı aynen.
- Bu üç değişiklik `SPEC_APP`/EK'lerdeki bir U-kuralının metniyle çelişiyorsa kuralı değiştirme; `docs/app/UI_FIX_RAPOR.md`'nin yanına yazacağın raporda "sapma" olarak kaydet ve orkestratöre bırak.

### C. CI ve README
- **K-CI-1 · İş akışı** `.github/workflows/build.yml`:
  - Tetik: `workflow_dispatch` ve `v*` etiketleri. Push'ta koşmaz (dakika harcamasın).
  - İş `test-windows` (`windows-latest`): `actions/checkout` (`fetch-depth: 0`), `core.autocrlf false`, Rust stable (`dtolnay/rust-toolchain@stable`), Node 22 (`actions/setup-node`), `Swatinem/rust-cache`, `npm ci`, `cargo test --workspace` (ignore'lular ignore kalır; `--include-ignored` **yok**, çünkü `.venv` ve `BORSAI_REPO` yok), `npm test`.
  - İş `build-windows` (`windows-latest`, `test-windows`'a bağlı): `npm run tauri build` (ya da `npx tauri build`), çıktı `src-tauri/target/release/bundle/nsis/*.exe` → `actions/upload-artifact` adı `BorsAi-windows-<sha7>`.
  - İş `build-macos` (`macos-latest`): aynı kurulum, `tauri build` → `bundle/dmg/*.dmg` → artefakt `BorsAi-macos-<sha7>`.
  - `timeout-minutes` her işte 45. Release oluşturma **yok** (proje sahibi karar verir). Secret yok.
  - İş akışı dosyasını `actionlint` benzeri bir araç yoksa en azından YAML olarak ayrıştırıp doğrula.
- **K-CI-2 · README.md (repo kökü).** Kısa, Türkçe:
  1. ne olduğu (iki cümle, "olasılık üretir, al-sat sinyali değildir");
  2. dürüst durum (backtest geçiyor, canlı sicil yeni başlıyor; `docs/SCORES.md`'ye bağ);
  3. kurulum: macOS (dmg, imzasız: sağ tık → Aç), Windows (nsis .exe, SmartScreen "Ek bilgi → Yine de çalıştır"), kişisel modda Python/git gerekmez;
  4. geliştirici kurulumu bir paragraf (`app/README.md`'ye bağ);
  5. proje kuralları için `CLAUDE.md`'ye bağ.
  Kasa kodu, bülten adı kalıbı, kişisel bilgi yok (adım R'de tara).

## Önceden onaylı pin güncellemesi (K-PIN-WIN)
Proje sahibi başlatma cümlesinde onaylar. Genel kural: **bu görevin kendi değişikliklerinin birebir yansıması olan pinler güncellenir; başka hiçbir pin değişmez.**
- `tests/test_faz8_model.py` `APP_TASKS` demetine `("BORSAI_FAZ9_WINDOWS_", "BORSAI_FAZ9_WINDOWS_R:")` eklenir (sona). `test_5c`'nin kendisi değişmez; `app/parity/` hiç değişmez.
- `app/tests/sade_render.test.ts:394` ("öbür ufuklar ≈ fark net değil") ve K-TXT-2/3'ün metnini pinleyen vitest/cargo testleri yeni metne güncellenir. `:615` perf sayım cümlesi testi **değişmez**.
- Windows tuzakları için `cfg` ile ayrılan Rust testleri (yukarıda 2–4).
- Bekçi testlerine (kasa, sıra, hijyen, temizlik, `test_faz7_vault`, `test_outcome_guard`, `test_scoring`) dokunulmaz. `borsai/`, `models/`, `scores/`, `registry/`, `data/` değişmez.

## İzinli izlenmeyenler (adım 0)
`docs/prompts/FAZ10_FABLE_STREAK_SPEC.md`, `docs/prompts/TUFE_2026_09.md`, `docs/prompts/FAZ9_WINDOWS.md` (bu dosya). Başka izlenmeyen varsa dur ve yaz.

## ÖNCE OKU
- `CLAUDE.md`
- `docs/prompts/FAZ9_UI_FIX.md` (kalıp, K-PIN-FIX, kabul biçimi) ve `docs/app/UI_FIX_RAPOR.md`
- `docs/fable_kitap_audit/AUDIT_4_UYGULAMA.md` bulgu 1, 2, 7 ve "Proje sahibine açık sorular" (cevaplar: 1 → "birincil değil"; 2 → bu görevde değil; 3 → bu görevde değil)
- `docs/app/SPEC_APP.md` §1.1 (repo modu), §4 (biçim), U-kuralları tablosu; `docs/app/SPEC_APP_EK3.md` Python'a düşülen yerler
- `app/README.md`, `app/scripts/test.sh`, `app/scripts/env.sh`
- `app/src-tauri/src/commands/config.rs` (tamamı), `python.rs`, `commands/freeze.rs:80-190`, `commands/form.rs:200-240`, `commands/sade.rs:1380-1420`
- `app/src/sade/render/sonuc.ts`, `analiz.ts`, `giris.ts`, `monitor.ts`; `app/src/i18n/tr.ts` ilgili anahtarlar
- `tests/test_faz8_model.py:30-40, 140-170`

## Adımlar

**0. Taban.** `GIT_OPTIONAL_LOCKS=0`; HEAD `2f01a28`, `git status --porcelain --untracked-files=all` yalnız izinli izlenmeyenler. `source app/scripts/env.sh`. Tabanı ölç ve kaydet: `.venv/bin/pytest -q -n 6 --dist loadgroup` (952 bekleniyor), `bash app/scripts/test.sh` (164 / 376), `.venv/bin/python -m app.parity.gen_golden --check` ya da repodaki karşılığı (35/0). Sayılar tutmuyorsa dur, yaz.

**0b. Geçici klonda prova.** `/tmp/borsai_win_<tarih>/` altına `git clone` (ana repoya dokunmadan). Orada A ve B değişikliklerinin taslağını uygula, `cargo test` + `npm test` koş ve **kırılan testlerin tam listesini** çıkar. Liste K-PIN-WIN'in genel kuralına uymayan bir test içeriyorsa dur ve orkestratöre yaz. Klon sonunda silinir.

**A. Taşınabilirlik ve paket** (commit `BORSAI_FAZ9_WINDOWS_A: …`). K-WIN-1..4 ve K-PIN-WIN'in Rust/Python kısmı (`APP_TASKS`). Mac'te `cargo test --workspace` yeşil, `npm test` yeşil, `tauri build` dmg üretir (yerel doğrulama; Windows derlemesi CI'da). `tauri.conf.json`'daki yeni `nsis` bloğunu `npx tauri build --help` / şema ile doğrula; Mac'te nsis hedefi atlanır, hata vermemeli (gerekirse `--bundles dmg` ile derle ve raporda yaz).

**B. Ekran metni** (commit `BORSAI_FAZ9_WINDOWS_B: …`). K-TXT-1..3 ve ilgili test güncellemeleri. Her üç ekranın yeni hâli için `app/docs/screens/v2/` altına ekran görüntüsü (`screens_v2.sh` kalıbı; dosya adı `win_01_sonuc_birincil_degil.png` gibi). Görüntülerde kasa kodu ya da bülten adı olmaz.

**C. CI ve README** (commit `BORSAI_FAZ9_WINDOWS_C: …`). `.github/workflows/build.yml`, `README.md`. YAML ayrıştır. `app/README.md`'ye Windows derlemesinin CI'da yapıldığına dair üç satır.

**→ BURADA DUR.** Orkestratöre teslim raporunun taslağını ver (aşağıdaki başlıklar, CI satırları boş). Proje sahibi push eder ve Actions'ı `workflow_dispatch` ile çalıştırır; sonucu (koşu URL'si, iş süreleri, artefakt adları ve boyutları) aynı pencereye yapıştırır.

**D. CI sonucu ve kapanış** (commit `BORSAI_FAZ9_WINDOWS_R: final test runs`). CI çıktısını rapora işle. Kırmızı iş varsa düzelt (yeni A2/C2 commit'i, aynı önek), proje sahibi yeniden push eder ve koşturur; yeşil olana dek. Son kabul: sıralı `.venv/bin/pytest -q` (ayrılan yok), `bash app/scripts/test.sh`, `gen_golden --check`; çıktılar `docs/app/windows_test_runs.txt`.

## Tek oturumda bitmezse
Adım sınırında dur, commit atma (yarım iş commit'lenmez), yarım kalan adımı ve kırılan test listesini rapora yaz. Proje sahibi aynı pencerede "devam et" der.

## Kurallar
- **Yazılabilir:** `app/src-tauri/src/**`, `app/src-tauri/tests/**`, `app/src-tauri/tauri.conf.json`, `app/src-tauri/Cargo.toml` ve `Cargo.lock` (yalnız yeni bağımlılık gerekirse, ör. `dunce`; gerekçesi rapora), `app/src/**`, `app/tests/**`, `app/docs/screens/v2/**`, `app/README.md`, `app/package.json`/`package-lock.json` (yalnız gerekirse), `.github/workflows/build.yml`, `README.md`, `tests/test_faz8_model.py` (yalnız `APP_TASKS`), `docs/app/WINDOWS_RAPOR.md`, `docs/app/windows_test_runs.txt`, `docs/prompts/FAZ9_WINDOWS.md` (bu dosya, commit A ile).
- **Salt okunur:** `borsai/`, `models/`, `scores/`, `registry/`, `data/`, `experiments/`, `legacy/`, `app/parity/`, `docs/specs*`, `CLAUDE.md`, öteki testler.
- Ağ yalnız paket kurulumu için. Testlerde ağ yok (`no_network` testleri yeşil kalır).
- `git add` yalnız yukarıdaki yollarla, açık yol listesiyle; `git add -A` yok. push, tag, amend yok.
- Windows kuralı: yeni kodda sabit Mac yolu ya da kabuğa özel sözdizimi yok.
- Hijyen: README, rapor ve ekran görüntülerinde kasa kodu (`registry/oot/cohort_pre_h99.csv` SEALED, 64 kod) ve `th[bm]`+8 hane kalıbı 0; sayımı rapora yaz, kodları yazma.

## Teslim (`docs/app/WINDOWS_RAPOR.md`)
1. İlk satır: `FAZ9_WINDOWS: A <sha> · B <sha> · C <sha> · R <sha> · CI <yeşil/kırmızı> <koşu URL'si>`
2. Windows tuzakları tablosu (6 satır: ölçüm, değişiklik, koruyan test).
3. Değişen dosyalar ve neden; eklenen bağımlılıklar.
4. K-TXT-1..3 öncesi/sonrası metin ve ekran görüntüsü yolları; U-kuralı sapması varsa.
5. CI: her işin süresi, Windows'ta koşan cargo/vitest sayıları, artefakt adları ve boyutları. **Gerçek Windows açılışı bu oturumda doğrulanmadı** cümlesi aynen; proje sahibi ya da bir Windows kullanıcısı açıp üç ekrana bakacak.
6. Test sayıları: taban ve son (pytest, cargo Mac, cargo Windows, vitest, parity, golden).
7. Hijyen sayımları.
8. Yapılmayanlar ve açık sorular (repo modu Windows'ta; `--include-ignored` koruma testi AUDIT_4 bulgu 9; sürüm etiketi ve release kararı).

## Kabul kapısı
- `test_5c` yeşil; `app/parity` diff boş; `git status -- app` R'den sonra boş.
- Sıralı pytest ayrılan test olmadan yeşil (≥ 952); `bash app/scripts/test.sh` yeşil; `gen_golden --check` 35/0.
- CI: `test-windows`, `build-windows`, `build-macos` yeşil; iki artefakt indirilebilir.
- Üç ekran görüntüsünde yeni metinler görünür; hiçbir hüküm sözcüğü öne çıkmayan satırda yok.
- `borsai/`, `models/`, `scores/`, `registry/`, `data/` diff boş (`git diff --stat 2f01a28 -- borsai models scores registry data` boş).
- Hijyen 0/0.

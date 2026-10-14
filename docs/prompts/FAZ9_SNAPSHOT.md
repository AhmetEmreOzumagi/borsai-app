# FAZ9_SNAPSHOT — Kişisel modda gömülü sicil anlık görüntüsü (Monitör, Analiz, Sicil, Performans dolu)

**Model: Claude Code / Opus · Extra**

- **TASK_ID:** `BORSAI_FAZ9_SNAPSHOT_20261013`
- **Klasör:** repo kökü `~/Desktop/BorsAi`
- **Ağ:** yalnız paket kayıtları. CI koşusunu proje sahibi başlatır.
- **Commit konusu öneki:** `BORSAI_FAZ9_SNAPSHOT_` (A, B, R; aşağıda).
- **Denetim kuralı (aynen):** Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir. Bu görevde hiçbir model, skor, sınıf ya da hüküm değişmez; yalnız verinin uygulamaya nasıl ulaştığı değişir.

## Rol

Uygulamanın ana mühendisisin. Proje sahibi Windows paketini (`BorsAi_0.1.0_x64-setup.exe`, CI koşusu 38406430116) gerçek bir Windows'ta açtı: uygulama çalışıyor, ama Monitör ve Analiz boş. Neden: Windows'ta repo yok, uygulama kişisel modda; Monitör/Analiz/Sicil/kırılma kartı `require_repo` ile repodan okuyor. Deneme grubu için bu ekranlar projenin kendisidir. Görev: resmi sicilin **salt okunur bir anlık görüntüsünü** modeller gibi uygulamaya gömmek ve kişisel modda bu dört ekranı o görüntüden doldurmak. Dondurma, D1 sonrası kayıt, sonuç yazma gibi her yazma işi repo modunda kalır. Başka iyileştirme yapma, bulduğunu rapora yaz.

## Orkestratörün ölçtükleri (2026-10-13, HEAD = origin/main = `e5a4d0f` + izlenmeyen `e6c2e07` envanter commit'i; ağaç temiz)

- **Bugün gömülü olanlar** (`app/src-tauri/build_embed.rs` `EmbedPlan`): `models/INDEX.json` + 27 model + `INDEX_POST_D1.json` + 1 model; TÜFE tablosu; `scores/scores.json` (`scores_path`); süzülmüş `scores_oot.json` (`scores_oot_path`, `filter_scores_oot`). Üretilen kod `OUT_DIR/embedded.rs`, tipler `src/embedded.rs`.
- **Repodan okunup gömülü olmayanlar** (sade görünümün okuduğu yollar, `sade.rs`, `sade_break.rs`, `registry.rs`):
  - `registry/ipos.csv` (8 KB; `registry.rs:318`)
  - `registry/records/<T>/*.json` (7 arz, 336 KB; `registry.rs:400-406, 525`)
  - `registry/inputs/` (112 KB; `sade.rs:672`)
  - `registry/post_break/<T>/machine_*.json` (56 KB; `sade.rs:391-405`)
  - `data/outcomes/*.csv` (8 dosya, 636 KB; `sade.rs:128, 208`)
  - `scores/scores_break.json` (28 KB; `sade.rs:482`), `scores/scores_post_d1.json` (16 KB; `sade.rs:544-546`)
  - Sicil künyesindeki "push kanıtı var" `registry/push_proofs/` okuyorsa (31 dosya) o da; ölç.
  Toplam ≈ 1,2 MB. Paket 2,85 MB → ≈ 4 MB.
- **`require_repo` kullanan sade komutları:** `sade.rs:899` (`monitor_view`), `sade.rs:962` (`arz_view`), `sade_break.rs:288` (`break_view`); `registry.rs` 3 yer (Sicil). Diğerleri (`freeze.rs` 5, `post_d1.rs` 6, `inputs_doc.rs` 4, `source_docs.rs` 2, `ceiling/market20/path` 1'er) **yazma ya da repo'ya özgü** işlerdir; dokunulmaz.
- Görünüm fonksiyonları zaten `repo: &Path` alıyor (`monitor_view_in`, `arz_view_in`, `break_view_in`, `scores_break_in`). Bu, soyutlama yazmadan "anlık görüntü dizini"ni aynı fonksiyonlara vermeye izin verir.
- `BUILD_INFO.git_status_models_scores` (`build.rs:19`) derleme anında yalnız `models` ve `scores` kirliliğine bakıyor.
- Kişisel mod yalıtım testi `app/tests/e2e_personal_isolation.sh` (U39): beyan ve kişisel kayıt yalnız `<app_data_dir>/scenarios/`'ta; `data/outcomes`, `registry`, `scores` ağaçları değişmez.
- Test tabanı (`e5a4d0f`, `docs/app/windows_test_runs.txt`): pytest **952** (sıralı); `test.sh`: cargo **167**, vitest **377**, parity 8, golden_unchanged; `gen_golden --check` 35/0. CI 3 iş yeşil.
- `APP_TASKS` bugün üç satır; sonuncusu `("BORSAI_FAZ9_WINDOWS_", "BORSAI_FAZ9_WINDOWS_R:")`.

## Kararlar

- **K-SNAP-1 · Ne gömülür.** Yukarıdaki liste: `registry/ipos.csv`, `registry/records/**`, `registry/inputs/**`, `registry/post_break/**`, `registry/push_proofs/**` (yalnız Sicil künyesi okuyorsa), `data/outcomes/*.csv`, `scores/scores_break.json`, `scores/scores_post_d1.json`. Ham bülten, PDF, `source_docs`, `registry/oot/**` **gömülmez**. Gömülen kümenin manifesti (`yol → sha256 → bayt`) ve derleme HEAD'i `BUILD_INFO`'ya eklenir; `git_status` denetimi bu yolları da kapsar (kirli ağaçtan derlenirse `BUILD_INFO` söyler).
- **K-SNAP-2 · Nasıl kullanılır.** Kişisel modda (repo doğrulanmamışken) uygulama açılışta gömülü anlık görüntüyü `<app_data_dir>/snapshot/<build_sha7>/` altına **aynı göreli yollarla** yazar (varsa sha'larını doğrular, tutmazsa siler ve yeniden yazar; doğrulanamıyorsa `SNAPSHOT_INTEGRITY_FAILED` ve dört ekran boş kalır, fail-closed). Salt okunur ekranlar (`monitor_view`, `arz_view`, `break_view`, Sicil görünümleri) repo yoksa bu dizini `repo` parametresi olarak alır. Yazma komutları (`freeze`, `post_d1`, `inputs_doc`, `source_docs`, senaryo dışı her şey) **asla** anlık görüntüye yazmaz; `require_repo` onlarda aynen kalır. Anlık görüntü dizini `is_within` yol bekçisinde "repo kökü" sayılmaz ve kişisel kayıtlar oraya yazılamaz.
- **K-SNAP-3 · Ekran dürüstlüğü.** Kişisel modda Monitör veri şeridi "Veri: gömülü anlık görüntü · derleme <sha7> · son sonuç <tarih>" der (Rust'tan gelir; tarih `data/outcomes` içindeki en geç seans). Sicil künyesinde kaynak "gömülü anlık görüntü" yazar. Dondur/kaydet düğmeleri kişisel modda bugünkü gibi repo modu ister. Repo modunda hiçbir ekran metni değişmez.
- **K-SNAP-4 · Yalıtım.** `e2e_personal_isolation.sh` genişler: kişisel modda dört ekran açılıp beyan girildikten sonra anlık görüntü dizinindeki dosyaların sha'ları değişmemiş olmalı; `scenarios/` dışına hiçbir yazma olmamalı.
- **K-SNAP-5 · Windows kuralı:** yeni kodda sabit yol ya da kabuk sözdizimi yok; `Path::join`; verbatim önek yardımcısı (`config.rs`) kullanılır.

## Önceden onaylı pin güncellemesi (K-PIN-SNAP)
Proje sahibi başlatma cümlesinde onaylar. Genel kural: **bu görevin kendi değişikliklerinin birebir yansıması olan pinler güncellenir; başka hiçbir pin değişmez.**
- `tests/test_faz8_model.py` `APP_TASKS` sonuna `("BORSAI_FAZ9_SNAPSHOT_", "BORSAI_FAZ9_SNAPSHOT_R:")`.
- `app/src-tauri/tests/build_embed.rs` plan pinleri (yeni anlık görüntü girdileri), `tests/integrity.rs` (anlık görüntü manifest sha'ları, bir bayt mutasyonu → `SNAPSHOT_INTEGRITY_FAILED`), `e2e.rs`/`stage*.rs` içinde kişisel modda boş görünüm bekleyen iddialar (varsa; listesi 0b'de çıkar).
- Bekçi testlerine (kasa, sıra, hijyen, temizlik, `test_faz7_vault`, `test_outcome_guard`, `test_scoring`) dokunulmaz. `borsai/`, `models/`, `scores/`, `registry/`, `data/`, `app/parity/` değişmez.

## İzinli izlenmeyenler (adım 0)
`docs/prompts/FAZ10_FABLE_STREAK_SPEC.md`, `docs/prompts/TUFE_2026_09.md`, `docs/prompts/FAZ9_SNAPSHOT.md` (bu dosya). `docs/public_mirror/**` ve `docs/prompts/FAZ9_PUBLIC_INVENTORY.md` commit'li (`e6c2e07`), izlenmeyen değil.

## ÖNCE OKU
- `CLAUDE.md`; `docs/prompts/FAZ9_WINDOWS.md` ve `docs/app/WINDOWS_RAPOR.md` (kalıp, K-PIN, CI akışı, Windows tuzakları)
- `docs/app/SPEC_APP.md` §1.1 (modlar), §2 (ayar), §5.4 (U39 kişisel yalıtım), U-kuralları; `SPEC_APP_EK3.md` §3 (bağımsız mod, gömme)
- `app/src-tauri/build.rs`, `build_embed.rs` (tamamı), `src/embedded.rs`, `src/state.rs`, `src/commands/config.rs` (`is_within`, `resolve_path`), `src/lib.rs` (app_data_dir)
- `src/commands/sade.rs` 120–220, 380–560, 660–700, 840–980; `sade_break.rs` 170–300; `registry.rs` 300–530
- `app/tests/e2e_personal_isolation.sh`, `app/src-tauri/tests/integrity.rs`, `tests/build_embed.rs`
- `app/src/sade/render/monitor.ts`, `sicil.ts`; `app/src/i18n/tr.ts` ilgili anahtarlar

## Adımlar

**0. Taban.** `GIT_OPTIONAL_LOCKS=0`; HEAD `e6c2e07`; izlenmeyenler yalnız izinli üçü. `source app/scripts/env.sh`. Tabanı ölç: `.venv/bin/pytest -q -n 6 --dist loadgroup` (952), `bash app/scripts/test.sh` (167 / 377), `gen_golden --check` (35/0). Sicil künyesinin `push_proofs` okuyup okumadığını ölç (K-SNAP-1 listesine girer mi).

**0b. Geçici klonda prova.** `/tmp/borsai_snap_<tarih>/` klonunda A+B taslağı; `cargo test`, `npm test`, `e2e_personal_isolation.sh` koş; kırılan testlerin tam listesi. K-PIN-SNAP dışında kırılan varsa dur, yaz. Klon sonunda silinir.

**A. Gömme ve bütünlük** (commit `BORSAI_FAZ9_SNAPSHOT_A: …`). `EmbedPlan`'a anlık görüntü girdileri ve manifest; `embedded.rs` tipleri; `BUILD_INFO` genişlemesi; açılışta yazma + sha doğrulama + fail-closed; `integrity.rs` ve `build_embed.rs` testleri; `APP_TASKS`. Mac'te `cargo test`, `npm test` yeşil; `tauri build` dmg boyutunu rapora yaz.

**B. Görünümler ve ekran** (commit `BORSAI_FAZ9_SNAPSHOT_B: …`). `monitor_view`, `arz_view`, `break_view`, Sicil komutlarında repo yoksa anlık görüntü dizini; K-SNAP-3 metinleri; `e2e_personal_isolation.sh` genişlemesi; vitest/cargo pinleri. **Kişisel modda** dört ekranın görüntüsü `app/docs/screens/v2/snap_01..04_*.png` (`screens_v2.sh` kalıbı; repo ayarı boşken çekilir). Görüntülerde kasa kodu ya da bülten adı olmaz (OCR ile say).

**→ BURADA DUR.** Teslim raporunun taslağı; proje sahibi push eder, `gh workflow run build.yml --ref main` çalıştırır, koşu numarasını yazar.

**C. CI sonucu ve kapanış** (commit `BORSAI_FAZ9_SNAPSHOT_R: final test runs`). CI'ı rapora işle (süreler, artefakt adları ve boyutları; Windows'ta cargo/vitest sayıları). Kırmızı varsa A2/B2 ile düzelt, yeniden push ve koşu. Son kabul: sıralı `.venv/bin/pytest -q` (ayrılan yok), `bash app/scripts/test.sh`, `gen_golden --check`, `bash app/tests/e2e_personal_isolation.sh`; çıktılar `docs/app/snapshot_test_runs.txt`.

## Tek oturumda bitmezse
Adım sınırında dur, commit atma, kırılan test listesini rapora yaz. "devam et" ile aynı pencerede sürer.

## Kurallar
- **Yazılabilir:** `app/src-tauri/build.rs`, `build_embed.rs`, `src/**`, `tests/**`, `app/src/**`, `app/tests/**`, `app/docs/screens/v2/**`, `app/README.md`, `README.md` (yalnız "kişisel modda sicil gömülü anlık görüntüdür" cümlesi), `tests/test_faz8_model.py` (yalnız `APP_TASKS`), `docs/app/SNAPSHOT_RAPOR.md`, `docs/app/snapshot_test_runs.txt`, `docs/prompts/FAZ9_SNAPSHOT.md`. `.github/workflows/build.yml` yalnız gerekiyorsa (gerekmemeli).
- **Salt okunur:** `borsai/`, `models/`, `scores/`, `registry/`, `data/`, `experiments/`, `legacy/`, `app/parity/`, `docs/specs*`, `docs/public_mirror/`, `CLAUDE.md`, öteki testler.
- Anlık görüntüye hiçbir koşulda yazılmaz (yalnız açılışta üretilir ve doğrulanır). Senaryo kayıtları `scenarios/` dışına çıkmaz.
- `git add` açık yol listesiyle; push, tag, amend yok.
- Hijyen: rapor, görüntüler ve test günlüğünde kasa kodu 0, `th[bm]`+8 hane 0; sayımı rapora yaz.

## Teslim (`docs/app/SNAPSHOT_RAPOR.md`)
1. İlk satır: `FAZ9_SNAPSHOT: A <sha> · B <sha> · R <sha> · CI <yeşil/kırmızı> <URL> · paket mac <MB> win <MB>`
2. Gömülen dosyalar tablosu (yol kalıbı, sayı, bayt, manifest sha'sı).
3. Kişisel modda hangi komutların anlık görüntüyü kullandığı; `require_repo`'su aynen kalanların listesi.
4. Bütünlük: bir bayt mutasyonu sonucu; `BUILD_INFO` kirli ağaç davranışı.
5. Yalıtım: genişletilmiş e2e çıktısı.
6. Dört ekran görüntüsü yolu; repo modunda metinlerin değişmediğinin kanıtı (fikstür farkı boş).
7. Test sayıları (taban ve son); CI.
8. Hijyen; yapılmayanlar ve açık sorular (ör. anlık görüntünün ne zaman yenileneceği: her yeni arz/sonuçta CI paketi).

## Kabul kapısı
- `test_5c` yeşil; `app/parity` diff boş; R'den sonra `git status -- app` boş.
- Sıralı pytest ≥ 952 yeşil; `test.sh` yeşil; `gen_golden --check` 35/0; `e2e_personal_isolation.sh` YEŞİL.
- CI üç iş yeşil, iki artefakt.
- Kişisel mod görüntülerinde Monitör'de 7 arz ve K-SNAP-3 şeridi görünür; repo modu fikstürleri değişmemiş.
- `borsai models scores registry data app/parity` diff boş. Hijyen 0/0.

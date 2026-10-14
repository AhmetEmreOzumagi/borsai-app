# TASK_ID: BORSAI_FAZ3_APP_AUDIT_FIX_20260923

Model: Opus 5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ: yalnız npm/crates (gerekirse). push/tag/amend yok.

## Bağlam
- Fable uygulama denetimi `70e1c52`: `docs/fable_app_audit/AUDIT.md`. Genel hüküm **DÜZELTMEYLE UYGUN**.
- Orkestratör B1, B2, B3'ü koddan doğruladı:
  - B1: `commands/config.rs:101-119` `is_within` askıda sembolik bağda en yakın var olan ataya düşüyor; `scenario.rs` `std::fs::write` bağı izliyor.
  - B2: `tests/u52_declaration.test.ts:319-331` yalnız `api.` geçen satırları tarıyor; `screens/results.ts:81` satırı taranmıyor.
  - B3: `render/freeze.ts:236` `ready` preflight'a bakmıyor; `commands/freeze.rs` `freeze_in` preflight'ı yeniden denetlemiyor.
- Bu görev denetimin düzeltme tariflerini uygular. Tarifler `AUDIT.md` bulgu tablosunda, dosya:satır düzeyinde; önce onları oku.
- Kural: her düzeltmeden ÖNCE onu yakalayan test yazılır ve düzeltme öncesi KIRMIZI olduğu gösterilir (çıktısı rapora). Sonra düzeltme, sonra yeşil.

## Kapsam
**Zorunlu (gerçek arz dondurmasından önce):**
- **B1** KRİTİK: askıda sembolik bağ hedefi kişisel kaydı `registry/` altına yazdırıyor.
  - `check_export_target`: hedef sembolik bağsa reddet (`symlink_metadata`; hedefi çözüp yeniden denetle ya da doğrudan `SCENARIO_PATH_INSIDE_REPO`).
  - Yazım `OpenOptions::new().write(true).create_new(true)` ile. Hedef dosya zaten varsa üzerine yazma davranışı bugün nasılsa korunur. Var olan normal dosyanın üzerine yazmak gerekiyorsa önce `symlink_metadata` ile bağ olmadığı kanıtlanır; bu kararı rapora yaz.
  - Tekli ve toplu dışa aktarma aynı yol. `save_scenario` ve `scenarios_dir` da aynı bağ denetiminden geçer.
  - `is_within`'e sözcüksel `..` normalizasyonu.
  - Testler:
    - `tests/stage2.rs::scenario_path_guard` ve `export_all_scenarios_in`: askıda dosya bağı, dizin bağı, var olmayan ara dizinli `..`.
    - `tests/e2e.rs::freeze_flow` U28 bölümü: aynı hedefler; `registry/` sha listesi değişmez.
- **B3** ÖNEMLİ: dondurma preflight'sız açılıyor.
  - `freeze_in` başında `preflight_in(repo, embedded_index_sha, t)`. `ok` değilse yeni kod `FREEZE_PREFLIGHT_BLOCKED` ile dön; Python çağrılmaz, `app/parity/incidents/` altına dosya yazılmaz.
  - Ön uçta `ready`'ye `preflight?.ok === true` eklenir.
  - Testler:
    - `tests/stage3.rs::freeze_refuses_when_preflight_blocked`: sahte gömülü sha → hata; `registry/records` ve `app/parity/incidents` değişmez.
    - `tests/freeze.test.ts`: preflight yok ya da `ok: false` → düğme kapalı.
  - Yeni hata kodunun metni `tr.ts`'e girer. `tests/codes.test.ts` `SPEC_APP.md` §3b.1 tablosunu okur ve şartnameye dokunamazsın. Kod T-2 tablosuna değil hata metinlerine aitse orada kalır. Test yine de kırılırsa kök nedeni raporla ve DUR.
- **B2** ÖNEMLİ: ekran mantığı sahte `invoke` ile hiç sınanmıyor.
  - Yeni `tests/screens_invoke.test.ts`: `vi.mock("@tauri-apps/api/core")` ile `invoke` çağrılarını yakala.
  - `screens/results.ts` (`derive`, `pathConditional`) ve `screens/registry.ts` (`loadRecord`) akışları, `tests/fixtures/outcomes/sntb1/` (resmi j = 2) + D3 beyanıyla koşturulur.
  - Beklenen: `ceiling_display`, `path_conditional`, `record_ceiling` çağrılarının j argümanı resmi j (2). `streak_view` tek argümanlı. Sicil akışında `predict_all` çağrı sayısı 0 (gerçek sayaç).
  - Statik tarama veri akışına çevrilir: `screens/*.ts` içinde `declared` / `declDropped` yalnız beyan işleyicisinde, senaryo kaydetmede ve `resetView`'da geçebilir. Başka her satır kırmızıdır.
  - Denetimin (e2) mutasyonu (`screens/results.ts:81`'de `j`'ye beyan sayısı eklemek) düzeltmeden sonra KIRMIZI olmalı. Klonda ya da geçici değişiklikle göster, geri al, çıktıyı rapora yaz.

**Aynı oturumda (küçük):**
- **B4:** `app/docs/screens/README.md:32` satırı görüntüyle eşleşsin: dört model `F3_MISSING`, `v1_5_market20_v0` `MARKET20_XU100_CLOSE_MISSING` (repo modu f6).
- **B5:** Ortam değişkeni isteyen testler yalın `cargo test`'te "ok" görünmesin. Tercih `#[ignore = "<ne ister, hangi betik koşar>"]`.
  - `test.sh` `BORSAI_REPO` isteyenleri `--include-ignored` ile koşar. İki e2e betiği kendi testlerini `--ignored` ile koşar.
  - Sonuç: `test.sh` + iki betik birlikte her testi gerçekten koşar. Hiçbir test env yok diye `return` ile yeşil dönmez.
  - Raporda, yalın `cargo test`'te "ignored" sayısı ve hangi testler olduğu.
- **B6:** `tests/stage2.rs::input_document_read_only`'ye `schema_version: "borsai.inputs/0"` → `INPUTS_SCHEMA_UNSUPPORTED`.
- **B7:** `tests/e2e_freeze_tmp_repo.sh` adım 4'e ekle: SNTA1 dizinindeki iptal kaydının iptal ettiği dosya Python `active_records`'ta yok, ve `len == 1`. İptal kaydını betik dosyadan bulur; e2e'nin yazdığı yapıya bak.
- **B8:** `commands/path.rs:286-290` OUTPUT kaynağında `params_sha256` zorunlu (`None` → `INVALID_ARGUMENT`). `stage3.rs::official_conditional_return_uses_record_only`'ye hata satırı.
- **B10:** Tolerans içi sessiz sürüklenme. `app/parity/bit_equal_floor.json`: model başına bugünkü `bit_equal_rows` (şu anki `target/parity_report.json`'dan, model_id → sayı).
  - `golden.rs::golden_parity` her model için `bit_equal_rows ≥ taban` sınar. Tabanı olmayan model kırmızıdır: yeni model eklenince taban bilerek yazılır.
  - Denetimin (a) mutasyonu (altın vektörde son hane) artık `golden_parity`'de KIRMIZI olmalı; göster.
  - U46 (`golden_unchanged.sh`) ve `test_gen_golden.py --check` yeşil kalır: altın dosyalara dokunma.
- **B12:** Push kanıtı yoksa gösterge metni: "bu kaydı ekleyen commit için kanıt dosyası yok; torun commit kanıtı skorlamada değerlendirilir". Bant da aynı dizeyi kullanır (A5-3). Git beyaz listesi DEĞİŞMEZ.

**Yapılmayacak:**
- B9: kabul; şartname notu proje sahibinde.
- B11: Python görevi, sonra.
- `identifier`: denetim "kalsın" dedi; karar proje sahibinde, dokunma.
- Ekran görüntülerini yeniden üretme. Metni değişen ekran varsa README'de yalnız not düş.

ÖNCE OKU:
- CLAUDE.md
- docs/fable_app_audit/AUDIT.md: bulgu tablosu, adım 3 ve adım 5
- docs/fable_app_audit/ekler/: `yol_bekcisi_sonda.txt`, `audit_probe.rs`, `mutate.sh`, `mutasyon_ciktilari.txt`
- docs/app/SPEC_APP.md §2.4, §3e, §5.4 (U27–U32), §5.6 U52
- İlgili app/ kodu ve testleri

## Adımlar
0. Taban:
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3`, `git status --porcelain`
   - İzinli izlenmeyen dosya yalnız `docs/prompts/FAZ3_APP_AUDIT_FIX.md`. Başka bir şey varsa DUR.
1. B1 → B3 → B2 sırayla: her biri için önce test ve kırmızı çıktı, sonra düzeltme, sonra yeşil.
2. Küçükler: B4, B5, B6, B7, B8, B10, B12.
3. Mutasyon yeniden koşusu, geçici klonda (`git clone --local` + ayrı `CARGO_TARGET_DIR`; Fable'ın `ekler/mutate.sh`'ı kalıp):
   - (a) ve (e2) artık KIRMIZI
   - askıda bağ sondası artık `Err`
   - denetimin öteki 9 mutasyonu hâlâ kırmızı

   Çıktılar rapora. Klon `/tmp` altında kalır, asıl `app/`'e yazılmaz.
4. Tam koşu: `bash app/scripts/test.sh`, `bash app/tests/e2e_freeze_tmp_repo.sh`, `bash app/tests/e2e_personal_isolation.sh`, `.venv/bin/pytest -q`. Hepsi yeşil.
5. Derleme: `source app/scripts/env.sh && cd app && npm run tauri build -- --bundles app`. `/Applications`'a kopyalama.
6. Commit.

Bu görev tek oturumda bitmezse:
- B1 + B3 bitmiş ve yeşil bir noktada commit at. Mesaja `(partial)` ekle.
- Kalanları raporda listele.

## Kurallar
- YALNIZ `app/` altına yaz. Tek istisna bu görev dosyası.
- `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `docs/`, `tests/` salt okunur.
- Altın dosyalar (`app/parity/golden/`) değişmez.
- Kişinin gerçek uygulama verisine yazma, oradaki dosyaları açma.
- Dondur akışını asıl repoda çalıştırma; yalnız testlerin geçici klonunda.
- Mevcut testleri gevşetme. Tutmayan test varsa kök nedeni bul; gerekirse DUR.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit:
  ```
  git add app docs/prompts/FAZ3_APP_AUDIT_FIX.md
  git commit -m "<mesaj>" -- app docs/prompts/FAZ3_APP_AUDIT_FIX.md
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Mesaj: `BORSAI_FAZ3_AUDIT_FIX: symlink-safe personal record export, freeze requires preflight, screen-level invoke tests and audit small fixes (B1-B8, B10, B12)`
- Rapor Türkçe.

## Teslim (rapor)
- Commit hash'i ve `git show --stat` özeti.
- Her bulgu (B1–B8, B10, B12) için:
  - değişen dosya:satır
  - yeni ya da genişleyen test
  - düzeltme öncesi kırmızı çıktı (son satırlar) ve sonrası yeşil
- Mutasyon yeniden koşusu tablosu: mutasyon · test · kırmızı mı.
- B5: yalın `cargo test`'te ignored testlerin listesi; `test.sh` + betiklerde hepsinin koştuğunun kanıtı.
- Test sayıları ve süreleri, önce/sonra: cargo, vitest, iki e2e, pytest.
- Derleme sonucu.
- Sapmalar ve kalan işler.

## Kabul kapısı
- K1 B1: askıda dosya bağı, dizin bağı ve `..` hedefleri tekli, toplu ve kaydetmede reddediliyor. Sonda `Err` veriyor; `registry/` sha listesi değişmiyor.
- K2 B3: preflight `ok` değilken dondurma hem Rust'ta hem ön uçta kapalı. Python çağrılmıyor, olay dosyası yazılmıyor.
- K3 B2: sahte `invoke` testi yeşil; (e2) mutasyonu kırmızı. Denetimin öteki mutasyonları hâlâ kırmızı; (a) artık kırmızı (B10).
- K4 Tam koşu yeşil; yalın `cargo test`'te env yüzünden "ok" dönen test yok.
- K5 Commit yalnız `app/` ve bu görev dosyası; altın dosyalar ve `identifier` değişmemiş.

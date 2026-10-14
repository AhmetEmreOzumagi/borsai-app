# FAZ9_PUBLIC_MIRROR — Herkese açık ayna repo (`AhmetEmreOzumagi/borsai-app`), README, lisans, sürüm CI'ı

**Model: Claude Code / Opus · Extra**

- **TASK_ID:** `BORSAI_FAZ9_PUBLIC_MIRROR_20261013`
- **Klasör:** repo kökü `~/Desktop/BorsAi` (özel repo, kaynak). Ayna ağacı **repo dışında** `~/Desktop/BorsAi_public/` altına üretilir.
- **Ağ:** yalnız paket kayıtları. GitHub'da repo oluşturma, push, etiket ve Release **proje sahibinin** işidir; sen komut bloklarını yazarsın.
- **Commit konusu öneki (özel repoda):** `BORSAI_FAZ9_PUBLIC_MIRROR_` (A, B, R).
- **Denetim kuralı (aynen):** Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir. Bu görevde model, skor, hüküm değişmez.

## Rol

Uygulamanın ana mühendisisin. Proje sahibi projeyi herkese açmak istiyor: kodu ve belgeleri okunabilsin, Mac ve Windows kurulum paketleri GitHub Releases'ten indirilebilsin, README profesyonel olsun. Özel repo (`AhmetEmreOzumagi/borsai`) özel kalır: push kanıtlarının ve zaman damgalarının taşıyıcısıdır; geçmişi yeniden yazılmaz. Herkese açık repo **tek commit'lik yeni geçmişli bir ayna**dır; özel repodaki sha'ya atıf yapar. Envanter ve ölçümler Fable tarafından yapıldı: `docs/public_mirror/INVENTORY.md`, `MIRROR_MANIFEST.txt`, `ekler/`. Sen uygularsın.

## Proje sahibi ve orkestratör kararları (13 Ekim; INVENTORY §7 sorularına cevaplar)

| Soru | Karar |
|---|---|
| 1, 3 — türetilmiş veri, skorlar | **GİRER**: `data/raw/*.csv`, `data/raw/*.json`, `data/raw/xu100/**`, `data/outcomes/**`, `data/outcomes_oot/**`, `data/training_table*.csv`, `data/data_version*.json`, `scores/*.json`, `app/parity/golden/**`, `tests/reference/**`, `experiments/log.jsonl`. Gerekçe: uygulama paketleri bu veriyi zaten gömülü dağıtıyor. `DATA_NOTICE.md` kaynakları ve "resmi bülten ve belgeler yeniden dağıtılmaz" cümlesini yazar; hukuki görüş alınmadığını saklamaz. |
| 2 — PDF olmayan resmi belgeler | TÜİK (`data/raw/tuik/**`) **GİRER** (açık veri). `docs/specs_faz6/ekler/spk_tablolar/*.xlsx` **GİRMEZ** (PDF kararıyla tutarlı; türetilmiş CSV'ler kalır). |
| 4 — sicil | **GİRER** olduğu gibi: `registry/records`, `registry/oot/**` (source_docs hariç), `registry/post_break`, `registry/inputs`, `registry/ipos.csv`, `registry/legacy_frozen`, `registry/legacy_roles.json`. "Dondurulmuş kayıt silinmez" aynada da geçerli. |
| 5 — kimlik | Ayna commit yazarı: `Ahmet Emre Özümağı <AhmetEmreOzumagi@users.noreply.github.com>` (proje sahibi GitHub'da "keep my email private" ayarını açar; ID'li biçim gerekiyorsa README'de değil, komut bloğunda yazılır). `registry/push_proofs/**` **olduğu gibi GİRER** (kullanıcı adı zaten repo sahibi). |
| 6 — kasa kodları | Aynada olduğu gibi (kasa harcandı). ORTAK hijyen kuralı yalnız **yeni yazılan** README/notlar için sürer: README, DATA_NOTICE, CHANGELOG, iş akışında kasa kodu 0, bülten adı kalıbı 0. |
| 7 — manifestler | **GİRER**: `registry/source_docs/*/MANIFEST.json`, `registry/source_docs/_ENUMERATION/ENUMERATION.json`, `registry/oot/source_docs/*/MANIFEST.json`, `registry/oot/source_docs_faz7/**` (yalnız JSON), `data/raw/bist/MANIFEST.csv`, `MANIFEST_OOT.csv`. PDF ve zip **GİRMEZ**. |
| 8 — doğrulama günlükleri | `docs/faz6/dogrulama/_tools/logs/**` **GİRMEZ** (şirket adresleri); `REPORT.md` yeter. |
| 9 — üçüncü şahıs adları | Olduğu gibi (kamuya açık belgelerden). |
| 10 — `legacy/` | **GİRER**. |
| 11 — ikonlar | Proje sahibi hatırlamıyor. **Ölç:** `app/src-tauri/icons/*` sha'larını Tauri CLI şablon ikonlarıyla (node_modules'daki `@tauri-apps/cli` ya da `tauri icon` varsayılan çıktısı) karşılaştır; git geçmişinde ikonları ekleyen commit'i ve varsa kaynak dosyayı bul. Şablonsa README'de "ikon Tauri şablonudur" notu; özelse kod lisansı kapsar. Sonucu rapora yaz. |
| 12 — lisans | **Apache-2.0** kökte `LICENSE`; `NOTICE` dosyası (telif satırı + "veri için DATA_NOTICE.md"). `app/` için ayrı kopya gerekmez; `app/package.json` ve `Cargo.toml` `license = "Apache-2.0"`. |
| 13 — geçmiş | **Tek commit** yeni geçmiş. README "Kaynak ve kanıt" bölümü: özel repo sha (`<HEAD>`), `registry/push_proofs/` açıklaması, "zaman kanıtı özel repodadır" cümlesi. |
| 14 — güncelleme | Elle, betikle: `scripts/mirror/build_mirror.py` (özel repoda) ayna ağacını manifestten yeniden üretir; proje sahibi `borsai-app`'te yeni bir commit atar. CI aynada: `v*` etiketinde Release. |
| 15 — SPK cümlesi | README ve uygulama metnindeki "yatırım tavsiyesi değildir" cümlesine INVENTORY §5.3'teki aday eklenir (kısa, Türkçe + İngilizce). Hukuki görüş sonra; README bunu "hukuki görüş alınmamıştır" diye söyler. |
| Repo adı | **`AhmetEmreOzumagi/borsai-app`** (public). `borsai` özel kalır. |

## Orkestratörün ölçtükleri (2026-10-13, HEAD = origin/main = `459d8fc`, ağaç temiz; izlenmeyen yalnız `FAZ10_FABLE_STREAK_SPEC.md`, `TUFE_2026_09.md` ve bu dosya)
- Envanter: GİRER 1 340 / 66,3 MB; GİRMEZ 909 / 225,7 MB; KARAR 1 512 / 157,5 MB. Yukarıdaki kararlarla ayna ≈ GİRER + KARAR − (xlsx 5, logs 11, PDF/zip) ≈ **~2 800 dosya, ~220 MB**; 100 MB üstü dosya yok; en büyük `scores/scores_oot.json` 41,3 MB (GitHub 50 MB uyarısı altında; `.gitattributes` LFS gerekmez).
- GİRMEZ yollar silinmiş klonda: uygulama kişisel modda çalışır; pytest 960'ta 79 kırmızı + 16 hata (69'u doğrudan GİRMEZ yolu, 24'ü dolaylı); cargo 2 kırmızı (`inputs_doc_bytes_roundtrip`, `inputs_doc_bytes_match_python`: NETGL manifesti ister → manifestler GİRER kararıyla yeşile döner); vitest 377/377 (bugün 384); `golden_unchanged.sh` yeşil. Liste: `docs/public_mirror/ekler/kirmizi_testler.txt`.
- CI (`.github/workflows/build.yml`): `workflow_dispatch` + `v*` etiketi; test-windows, build-windows, build-macos; release yok; secret yok. Aynada Release eklenir.
- Lisanslar: npm GPL/AGPL 0; cargo MPL-2.0 5 (Tauri zinciri; uyumlu), GPL 0; Python hepsi izinli. Kökte LICENSE yok.
- Ekran görüntüleri: `app/docs/screens/v2/*.png` (Monitör, Analiz, hesaplayıcı, performans, sicil, `win_01..04`, `snap_01..04`); README bunlardan 3–4 tanesini kullanır.
- Kurulu paketler: `BorsAi_0.1.0_x64-setup.exe` (NSIS, imzasız; SmartScreen), `BorsAi_0.1.0_aarch64.dmg` (ad-hoc imza; "sağ tık → Aç"). Snapshot gömülü; kişisel modda 7 arz görünür.
- Test tabanı (`459d8fc`): pytest 952 (sıralı), cargo 176, vitest 384, parity 8, golden_unchanged, `gen_golden --check` 35/0, `e2e_personal_isolation.sh` yeşil.
- `APP_TASKS` dört satır; bu görev `app/` altında yalnız `package.json` (`license` alanı) ve `Cargo.toml` (`license`) değiştirirse **o da `app/`'a dokunmaktır** → K-PIN: `("BORSAI_FAZ9_PUBLIC_MIRROR_", "BORSAI_FAZ9_PUBLIC_MIRROR_R:")` eklenir.

## Kararlar (uygulama)

- **K-MIR-1 · Ayna üretimi betikle.** `scripts/mirror/build_mirror.py` (yalnız stdlib): girdi `scripts/mirror/MIRROR_MANIFEST.txt` (Fable'ın manifestinin kararlar uygulanmış nihai hâli; GİRER/GİRMEZ, KARAR kalmaz), çıktı `~/Desktop/BorsAi_public/` (önce boşaltır). Dosyalar bayt bayt kopyalanır; hiçbir dosyanın içeriği düzenlenmez. Ayrıca ayna üstüne `scripts/mirror/overlay/**` kopyalanır (README, LICENSE, NOTICE, DATA_NOTICE, CHANGELOG, CONTRIBUTING, iş akışı, `.gitattributes`, `.gitignore`). Betik sonunda özet basar: dosya sayısı, MB, GİRMEZ kalıplarına uyan 0 dosya (doğrulama), 100 MB üstü 0, `.pdf`/`.zip` 0 (TÜİK `.xls` ve `docs` görselleri hariç ikili dosya listesi), kasa kodu ve bülten kalıbı yalnız overlay dosyalarında sayılır (0 olmalı).
- **K-MIR-2 · README (overlay, Türkçe; başta kısa İngilizce özet paragrafı).** Bölümler: başlık + tek cümle + rozetler (CI durumu, sürüm, lisans); 3–4 ekran görüntüsü; **Ne yapar** (üç an, olasılık, al-sat değil); **Kurulum** (macOS dmg: imzasız, "sağ tık → Aç"; Windows exe: SmartScreen "Ek bilgi → Yine de çalıştır"; kişisel mod, Python/git gerekmez; gömülü anlık görüntü ve "son sonuç" tarihi); **Dürüst durum** (backtest geçiyor; canlı sicil n küçük; sayılar `docs/SCORES.md`'den, ölçülerek yazılır); **Nasıl çalışır** (veri → modeller → üç terazi → kapı → uygulama; `docs/` bağlantıları); **Yeniden üretim** (ham bülten ve belgeler yok; kaynak URL kalıpları `docs/DATA.md`; hangi testlerin atlandığı ve neden, sayıyla); **Geliştirme** (`app/README.md`, test komutları, CI); **Kaynak ve kanıt** (özel repo, push kanıtları, sha); **Lisans ve veri** (Apache-2.0; DATA_NOTICE); **Uyarı** (yatırım tavsiyesi değildir + K-15 cümlesi, hukuki görüş alınmadı); **İletişim**. Sayılar ölçülür (`scores/*.json`, test sayıları, dosya sayıları); abartı yok; "canlıda kanıtlandı" yok. Markdown GitHub'da düzgün görünür; görsel yolları göreli.
- **K-MIR-3 · Aynada testler.** Ham bülten/PDF isteyen pytest'ler **açıkça atlanır**: `tests/conftest.py`'ye `requires_raw_sources` fixture/işaretleyicisi: `data/raw/bist/*.zip` ya da `registry/**/source_docs/**/*.pdf` yoksa `pytest.skip("ham bülten ve resmi belgeler herkese açık aynada yeniden dağıtılmaz")`. Yalnız `ekler/kirmizi_testler.txt`'teki testler işaretlenir; **iddialar değişmez**; özel repoda dosyalar var olduğundan hiçbiri atlanmaz (ölç: özel repoda sıralı pytest yine 952 passed, 0 skipped). `tests/test_registry_ipos.py` toplama hatası da aynı mekanizmayla. Cargo: manifestler girdiği için 2 test yeşil olmalı; ölç. Ayna ağacında koş: `pytest` (passed/skipped sayıları), `cargo test --workspace`, `npm test`, `gen_golden --check`; README'ye yaz.
- **K-MIR-4 · Ayna CI (overlay `.github/workflows/build.yml`).** Özel repodakinin kopyası + `v*` etiketinde `softprops/action-gh-release` (ya da `gh release create`) ile dmg ve exe'nin Release'e eklenmesi; `permissions: contents: write` yalnız release işinde; `workflow_dispatch` korunur; secret yok (`GITHUB_TOKEN` yeter). Test işi aynada `cargo test --workspace` + `npm test` + `pytest -q` (Python kurulumu: `actions/setup-python` 3.12 + `pip install -r requirements.lock`; `requires_raw_sources` atlamalarıyla yeşil olmalı). YAML ayrıştırılır.
- **K-MIR-5 · Sürüm.** `tauri.conf.json`, `Cargo.toml`, `package.json` sürümü `0.1.0` kalır; ayna etiketi `v0.1.0`; `CHANGELOG.md` tek girdi.
- **K-MIR-6 · Özel repoda ne değişir.** Yalnız: `scripts/mirror/**` (betik, nihai manifest, overlay), `tests/conftest.py` (+ işaretler), `app/package.json` ve `app/src-tauri/Cargo.toml` `license` alanları, `LICENSE`/`NOTICE`/`DATA_NOTICE.md` kökte de (özel repo da lisanslı olsun), `README.md` kökte (overlay README'nin özel repo için kısa sürümü ya da aynısı), `tests/test_faz8_model.py` `APP_TASKS`, `docs/app/PUBLIC_MIRROR_RAPOR.md`, `docs/prompts/FAZ9_PUBLIC_MIRROR.md`. `borsai/`, `models/`, `scores/`, `registry/`, `data/`, `app/parity/`, `app/src/**`, `app/src-tauri/src/**` **değişmez**.
- **K-MIR-7 · Windows kuralı** (betik yolları `pathlib`).

## Önceden onaylı pin güncellemesi (K-PIN-MIRROR)
Genel kural: bu görevin kendi değişikliklerinin birebir yansıması olan pinler güncellenir; başka hiçbir pin değişmez. `APP_TASKS` satırı; `requires_raw_sources` işaretleri (yalnız atlama koşulu, iddia değişmez); `package.json`/`Cargo.toml` `license` alanını pinleyen test varsa. Bekçi testlerine dokunulmaz.

## İzinli izlenmeyenler (adım 0)
`docs/prompts/FAZ10_FABLE_STREAK_SPEC.md`, `docs/prompts/TUFE_2026_09.md`, `docs/prompts/FAZ9_PUBLIC_MIRROR.md`.

## ÖNCE OKU
- `docs/public_mirror/INVENTORY.md` (tamamı), `MIRROR_MANIFEST.txt`, `ekler/kirmizi_testler.txt`, `ekler/envanter.csv` (sınıflama)
- `CLAUDE.md`, `README.md`, `app/README.md`, `docs/DATA.md`, `docs/SCORES.md`, `docs/MODELS.md`
- `.github/workflows/build.yml`, `.gitattributes`, `.gitignore`, `app/.gitignore`
- `docs/prompts/FAZ9_WINDOWS.md`, `FAZ9_SNAPSHOT.md` (kalıp, K-PIN, CI akışı), `docs/app/SNAPSHOT_RAPOR.md`
- `tests/conftest.py` (varsa), `tests/test_faz8_model.py:30-40`
- `app/docs/screens/v2/` listesi

## Adımlar

**0. Taban.** HEAD `459d8fc`; izlenmeyenler izinli; `source app/scripts/env.sh`; taban: paralel pytest 952, `test.sh` 176/384, `gen_golden --check` 35/0. İkon ölçümü (soru 11).

**A. Betik, manifest, overlay** (commit `BORSAI_FAZ9_PUBLIC_MIRROR_A: …`). `scripts/mirror/build_mirror.py`, nihai `MIRROR_MANIFEST.txt`, overlay dosyaları (README taslağı dahil), kök `LICENSE`/`NOTICE`/`DATA_NOTICE.md`, `license` alanları, `APP_TASKS`. Betiği çalıştır: `~/Desktop/BorsAi_public/` üretilir; özet rapora.

**B. Aynada test ve README'nin sayıları** (commit `BORSAI_FAZ9_PUBLIC_MIRROR_B: …`). `tests/conftest.py` işaretleri; özel repoda sıralı pytest 952 passed / 0 skipped (ölç). Ayna ağacında: `python -m venv` + `pip install -r requirements.lock` (ya da özel reponun `.venv`'ini ayna köküne işaret ederek), `pytest -q` → passed/skipped; `cd app && npm ci && npm test`; `cd app/src-tauri && cargo test --workspace`; `gen_golden --check`. Sonuçlar README'nin "Yeniden üretim" bölümüne ve rapora. README son hâli; görseller yerinde; ayna kökünde `git init` **yapma** (proje sahibi yapar).

**→ BURADA DUR.** Teslim raporu taslağı + proje sahibine komut bloğu (aşağıda; sha ve sayıları doldur). Proje sahibi aynayı GitHub'a koyar, etiketi atar, CI Release'i üretir; koşu numarasını yazar.

**C. Kapanış** (commit `BORSAI_FAZ9_PUBLIC_MIRROR_R: final test runs`). Ayna CI sonucunu ve Release varlıklarını (ad, boyut) rapora; özel repoda son kabul: sıralı pytest (ayrılan yok), `test.sh`, `gen_golden --check`; `docs/app/public_mirror_test_runs.txt`.

### Proje sahibine verilecek komut bloğu (B sonunda doldur)
```
cd ~/Desktop/BorsAi_public
git init -b main
git config user.name "Ahmet Emre Özümağı"
git config user.email "AhmetEmreOzumagi@users.noreply.github.com"
git add -A
git commit -m "BorsAi v0.1.0: public mirror of AhmetEmreOzumagi/borsai@<sha7> (code, models, scores, registry, docs; raw bulletins and official documents not redistributed)"
gh repo create AhmetEmreOzumagi/borsai-app --public --source=. --remote=origin --description "Borsa İstanbul halka arzları için tahmin ve ölçüm sistemi" --push
git tag v0.1.0
git push origin v0.1.0
gh run list --repo AhmetEmreOzumagi/borsai-app --limit 1
```
Not: `gh repo create --push` önce main'i push eder; etiket push'u Release iş akışını tetikler. Proje sahibi GitHub ayarlarından "Keep my email addresses private" açık olmalı (push reddi olursa komut bloğuna `<id>+` öneki eklenir).

## Kurallar
- **Yazılabilir (özel repo):** K-MIR-6 listesi. **Salt okunur:** `borsai/`, `models/`, `scores/`, `registry/`, `data/`, `experiments/`, `legacy/`, `app/parity/`, `app/src/**`, `app/src-tauri/src/**`, `docs/specs*`, `docs/public_mirror/`, `CLAUDE.md`.
- Ayna ağacı `~/Desktop/BorsAi_public/` repo dışıdır; orada git komutu çalıştırma (`git init` dahil).
- Hiçbir veri ya da kaynak dosyanın içeriği değiştirilmez; yalnız kopyalanır ya da dışarıda bırakılır.
- Hijyen: overlay dosyaları, rapor ve README'de kasa kodu 0, bülten kalıbı 0; sayım rapora.
- `git add` açık yol listesiyle; push, tag, amend yok (özel repoda da).

## Teslim (`docs/app/PUBLIC_MIRROR_RAPOR.md`)
1. İlk satır: `FAZ9_PUBLIC_MIRROR: A <sha> · B <sha> · R <sha> · ayna <dosya>, <MB> · ayna testleri pytest <p>/<s skip> cargo <n> vitest <n> · Release <v0.1.0 URL ya da bekliyor>`
2. Nihai manifest özeti (GİRER/GİRMEZ tablo; GİRMEZ'in kalıp düzeyinde listesi).
3. İkon ölçümü sonucu.
4. Atlanan testlerin sayısı ve gerekçe metni; özel repoda 0 skip kanıtı.
5. README'deki her sayının kaynağı (dosya/komut).
6. Lisans dağılımı özeti ve `LICENSE`/`NOTICE`/`DATA_NOTICE` içerik özeti.
7. Ayna CI ve Release (R'de).
8. Hijyen; yapılmayanlar ve açık sorular (hukuki görüş; ayna güncelleme ritmi).

## Kabul kapısı
- Özel repo: `test_5c` yeşil; sıralı pytest ≥ 952 passed, **0 skipped**; `test.sh` yeşil; `gen_golden --check` 35/0; korunan dizinler diff boş; R'den sonra `git status -- app` boş.
- Ayna: `build_mirror.py` özeti GİRMEZ kalıbı 0, `.pdf`/`.zip` 0, 100 MB üstü 0; ayna pytest kırmızı 0 (skip sayısı rapora), cargo 0 kırmızı, vitest 384, `gen_golden --check` 35/0.
- README: görseller görünür, bağlantılar kırık değil (göreli yollar aynada var), sayılar ölçülü, "canlıda kanıtlandı" ifadesi yok, uyarı bölümü var.
- Hijyen 0/0.

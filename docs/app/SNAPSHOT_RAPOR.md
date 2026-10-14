FAZ9_SNAPSHOT: A 526b84f · B 4a945dd (+B2 73e76fa) · R (bu commit) · CI yeşil https://github.com/AhmetEmreOzumagi/borsai/actions/runs/38438091552 · paket mac 3,70 MB win 2,90 MB

# BORSAI_FAZ9_SNAPSHOT_20261013 — Kişisel modda gömülü sicil anlık görüntüsü: teslim raporu

Görev `docs/prompts/FAZ9_SNAPSHOT.md`. Önceden onaylı pin K-PIN-SNAP (proje sahibi başlatma cümlesinde onayladı). A, B ve
orkestratör kararıyla B2 commit'lendi; proje sahibi `73e76fa`'yı push etti ve CI'ı koşturdu (38438091552, üç iş yeşil). R bu
raporu ve son kabul koşularını (`docs/app/snapshot_test_runs.txt`) ekler. Paket boyutları: mac = yerel `tauri build` dmg'si
(B2, 3 695 153 bayt; CI artefaktı zip 3 678 663 bayt), win = CI artefaktı `BorsAi-windows-73e76fa` (zip 2 895 768 bayt; içindeki
NSIS kurulum dosyası indirilmedi).
Hiçbir model, skor, sınıf ya da hüküm değişmedi; `borsai/ models/ scores/ registry/ data/ app/parity/` farkı boş
(`git diff --stat e6c2e07 -- borsai models scores registry data app/parity` → boş).

## 1. Özet

Windows paketinde (repo yok, kişisel mod) Monitör, Analiz ve Sicil boştu. Artık resmi sicilin derleme anındaki salt okunur
kopyası ikiliye gömülü (63 dosya, 627 365 bayt). Kişisel modda açılışta `<app_data_dir>/snapshot/<derleme sha7>/` altına
repo içi göreli yollarla yazılır, manifestle doğrulanır ve Monitör, Analiz (kırılma kartı dahil), Sicil ve Model performansı
aynı görünüm fonksiyonlarıyla bu dizinden okur. Her okuma dizini yeniden doğrular; tutmazsa `SNAPSHOT_INTEGRITY_FAILED` ve
ekranlar kapanır (fail-closed). Yazma işleri (dondurma, D1 sonrası kayıt, iptal, girdi belgesi, kaynak belge) repo modunda
kalır. Repo modunda çıktı ve ekran metni değişmedi (UI fikstürleri yeniden üretildi, fark boş).

| Commit | Konu |
|---|---|
| A `526b84f` | Gömme ve bütünlük: `SNAPSHOT_SPEC`, manifest ve git bilgisi `BUILD_INFO`'da; açılışta yazma + sha doğrulama + fail-closed (`registry_snapshot.rs`, `AppState::read_root`); `build_embed.rs`/`integrity.rs` testleri; `APP_TASKS` |
| B `4a945dd` | Görünümler ve ekran: salt okunur komutlar veri köküne bağlandı; K-SNAP-3 metinleri; `e2e_personal_isolation.sh` 2b adımı; vitest/cargo testleri; `snap_01..04` görüntüleri; README cümlesi |
| B2 `73e76fa` | Orkestratör kararı: `data/outcomes/COMPLETENESS.csv` gömülü kümeden çıktı (hiçbir ekran okumuyor, kasa kodu taşıyor); `data/outcomes` kapsamı `PerRecord("csv")`: yalnız kayıtlı 7 arzın `<T>.csv`'si; manifest, `build_embed` testleri, vitest künye sabitleri ve `app/README.md` dosya listesi buna göre |

## 2. Gömülen dosyalar (K-SNAP-1)

`build_embed.rs` `SNAPSHOT_SPEC` (yol bileşenleri `Path::join` ile; gizli adlar atlanır, sembolik bağ ve taşınabilir olmayan
ad derlemeyi kırar; yoksa gömülmez). `data/outcomes/` kapsamı `PerRecord("csv")`: `registry/records/` altında kayıt dizini olan
her arz için `<T>.csv` (B2). `HEAD = 73e76fa`'da (anlık görüntü yolları temiz):

| Yol kalıbı | Dosya | Bayt |
|---|---|---|
| `registry/ipos.csv` | 1 | 6 804 |
| `registry/records/<T>/*.json` | 7 | 330 346 |
| `registry/inputs/<T>.json` | 7 | 105 225 |
| `registry/post_break/<T>/machine_*.json` | 7 | 44 389 |
| `registry/push_proofs/<sha>.json` | 31 | 69 192 |
| `data/outcomes/<T>.csv` (kayıtlı arzlar) | 7 | 15 485 |
| `scores/scores_break.json` | 1 | 25 168 |
| `scores/scores_post_d1.json` | 1 | 12 310 |
| `models/break_floor_v0.json` | 1 | 18 446 |
| **toplam** | **63** | **627 365** |

- Manifest (`BUILD_INFO.snapshot_manifest`, satır başına `yol\tsha256\tbayt`, yol sırasıyla) sha256'sı:
  `dbc19f10daa5e557fbecb142e12ede8dda33e886460773ce191f70d5ce882751` (B2; B'deki 64 dosyalık manifest
  `d24c8180…` idi). Aynı metin anlık görüntü dizininin kökünde `SNAPSHOT_MANIFEST.tsv` olarak durur.
- `BUILD_INFO` ekleri: `snapshot_manifest`, `snapshot_manifest_sha256`, `git_status_snapshot` (`git status --porcelain --
  <SNAPSHOT_SPEC yolları>`); derleme HEAD'i zaten `git_head`. Ayrıca `SNAPSHOT_RECORD_COMMITS`: izlenen her tahmin kaydını
  ekleyen commit (7 kayıt; derleme anında `git ls-files` + `git log --diff-filter=A`). build.rs git beyaz listesi bu yüzden
  `rev-parse, status` → `rev-parse, status, ls-files, log` (hepsi salt okuma; K-PIN-SNAP `build_embed.rs` pini).
- **Listeye eklenen (orkestratör listesinde yoktu):** `models/break_floor_v0.json`. Kırılma kartı katsayıları yalnız bu dosyanın
  sha'sı makine kaydındaki `params_sha256` ile eşitken gösterir (`sade_break::break_view_in`); dosya olmadan kart
  `NO_MODEL_FILE` ile kapalı kalırdı. 18 KB.
- **Ölçüm (görevdeki "ölç"):** Sicil künyesi `registry/push_proofs/` okuyor (`registry::read_proofs`; "push kanıtı var" ve
  Sicil şeridindeki kanıt sayısı). 31 dosya gömüldü. Kaydı ekleyen commit repo modunda `git log`'dan gelir; anlık görüntüde
  git çağrılmaz, derleme anının bilgisi okunur (`registry_snapshot::frozen_git`), bu yüzden künyede "push kanıtı var
  22.09.2026 14:06 UTC · kaydı ekleyen commit …" kişisel modda da dolu.
- Gömülmeyenler: ham bülten, PDF, `registry/source_docs/`, `registry/oot/**`, `registry/legacy_frozen/`, `data/raw/` ve (B2)
  `data/outcomes/COMPLETENESS.csv` (618 945 bayt; tamlık listesi, hiçbir ekran okumuyor, kasa kodu taşıyor); kaydı olmayan arzın
  sonuç dosyası da girmez (`plan_snapshot_pins_spec_and_mirrors_repo`, `plan_snapshot_scope_rules` sınar). `registry/post_d1/`
  bugün repoda yok (bkz. §8).
- Paket (`tauri build --bundles app,dmg`): macOS dmg önceki 3 562 647 bayt → A 3 753 772 → B 3 761 237 → B2 3 695 153 bayt;
  ikili 8 720 512 → B 10 025 264 → B2 9 414 320 bayt. CI artefaktları (zip): Windows 2 835 390 (`e9f06d8`) → 2 895 768
  (`73e76fa`), macOS 3 551 572 → 3 678 663 bayt.

## 3. Kişisel modda hangi komutlar anlık görüntüyü kullanır

Tek karar noktası `AppState::read_root()`: doğrulanmış repo varsa repo kökü, yoksa doğrulanmış anlık görüntü dizini (bu
oturumda ilk kez gerekiyorsa üretilir; her çağrıda yeniden doğrulanır, yazılmaz). Görünüm fonksiyonları (`*_in(repo: &Path)`)
değişmedi; yalnız onlara verilen kök değişti.

| Ekran | Komut | Not |
|---|---|---|
| Monitör | `monitor_view`, `headline_gate`, `perf_view` | `load()`: D1 sonrası ve kırılma skorları veri kökünden; `scores.json` ve `scores_oot` zaten gömülüydü |
| Analiz | `arz_view`, `break_view`, **`arz_streak` (yeni)**, `record_summary`, `record_ceiling` | `post_d1_view` yalnız D1 sonrası kaydı varsa çağrılır (yok) |
| Sicil | `registry_view`, `monitor_view`, `break_view`, `read_record_json` | `post_d1_records` repo ister; hata yakalanır, "D1 sonrası, yok" (bugün doğru) |
| Model performansı | `perf_view`, `headline_gate` | D1 sonrası ve kırılma bölümleri dolu; "repo modu ister" notu yerine kaynak satırı |

**Orkestratör ölçümünden sapmalar (K-SNAP-2 ilkesine göre; bulguyu yazıyorum):**

1. `ceiling.rs`'teki `require_repo` (`record_summary`) "yazma ya da repo'ya özgü" grubundaydı; oysa Analiz'in kayıt kartını
   (hesaplayıcı) dolduran salt okuma komutudur. Repo istese Analiz kişisel modda hata kutusu gösterirdi. Veri köküne
   bağlandı; repo modunda davranış aynı (D1 sonrası skorları repo modunda eskisi gibi `scores_post_d1_value`'dan).
2. `streak_view` hem Analiz'in hem kişisel **Tahmin sonucu** ekranının gözlenen serisidir. Onu anlık görüntüye bağlamak kişisel
   moddaki Sonuç ekranının metnini değiştirirdi (her arz için `NO_REPO` → `MISSING`, anlık görüntüdeki 7 arzda resmi j ve U52
   beyan etkileşimi). Bu yüzden `streak_view` aynen kaldı; Analiz yeni salt okuma komutu `arz_streak(ticker)`'ı çağırır
   (`streak_view_in` ile aynı okuyucu, veri kökünden; repo modunda çıktı birebir aynı). Vitest'te Analiz'in komut pini
   `streak_view` → `arz_streak` (2 iddia; bu görevin değişikliğinin yansıması).
3. Sicil görünümü git'e bağlıydı (izlenen kayıt, kaydı ekleyen commit, `git status`). Anlık görüntü dizini git deposu değil
   (ve uygulama verisi bir üst git deposunun içindeyse yanlış depo okunurdu); anlık görüntüde git hiç çağrılmaz, derleme anının
   bilgisi kullanılır. `frozen_git` yalnız kökteki `SNAPSHOT_MANIFEST.tsv` gömülü manifestle bayt bayt aynıyken devreye girer;
   repo kökünde `None` (test: `snapshot_mode_views_equal_repo_views`).
4. K-SNAP-3 metinlerine ek olarak Sicil giriş cümlesi kişisel modda "…paketin derlendiği andaki sicilin gömülü, salt okunur
   kopyasından okur…" der (eski cümle "bu ekran her açılışta repodan okur" kişisel modda yanlış olurdu). Repo modunda aynen.

**`require_repo`'su aynen kalanlar** (yazma ya da repo'ya özgü; anlık görüntüyü hiç görmez): `freeze.rs` 5
(`freeze_preflight`, `inputs_pit_check`, `freeze_record`, `cancel_record`, `freeze_todo`), `post_d1.rs` 6 (`post_d1_records`,
`post_d1_view`, `post_d1_preflight`, `post_d1_freeze`, `post_d1_cancel`, `post_d1_todo`), `inputs_doc.rs` 4
(`list_input_documents`, `read_input_document`, `preview_inputs_doc`, `write_inputs_doc`), `source_docs.rs` 2
(`copy_source_docs`, `read_source_manifest`), `market20.rs` 1 (`market20_via_python`), `path.rs` 1 (`path_conditional`, kayıt
kaynağı; yalnız ayrıntılı görünüm). `state.repo()` ile repo'ya bakan ve değişmeyenler: `streak_view`, `path` resmi kapanışlar,
`predict_all` (Python yolu), `score_hints`/`scores_view`/`scores_post_d1_view`/`scores_oot_view` (ayrıntılı doğruluk paneli;
REPO/EMBEDDED seçimi aynen). Ayrıntılı (eski) Sicil ekranı kişisel modda eskisi gibi "repo modu" kapısında.

**Yol bekçisi (K-SNAP-2):** `<app_data_dir>/snapshot/` korunan kökler listesine (repo kökleri) girmez; kişisel kayıt kaydetme ve
dışa aktarma hedefi onun altındaysa ayrı kodla reddedilir (`SCENARIO_PATH_INSIDE_SNAPSHOT`). Anlık görüntü üretimi hedef bir
korunan kökün (repo) altına düşüyorsa hiçbir şey yazmaz (`SNAPSHOT_INTEGRITY_FAILED`). Anlık görüntü dizinini repo kökü olarak
Ayarlar'a vermek repo modu açmaz (`models/INDEX.json` yok).

## 4. Bütünlük

- **Açılış:** `registry_snapshot::prepare` = gömülü kopyayı manifestle doğrula (`verify_embedded`: manifest sha = `BUILD_INFO`,
  her dosyanın yolu/sha256/baytı manifest satırıyla) → dizin varsa ağaç birebir mi (`verify_tree`: beklenen dosyalar ve üst
  dizinleri dışında hiçbir şey yok, bağ yok, sha'lar tutar) → tutmazsa sil, `<sha7>.tmp<pid>`'e yaz, doğrula, yerine taşı →
  yine tutmazsa `SNAPSHOT_INTEGRITY_FAILED`. Üretim yalnız açılışta (kişisel moddaysa; `lib.rs` `prepare_snapshot`) ya da oturum
  içinde kişisel moda geçildikten sonraki ilk okumada, bir kez.
- **Okuma:** her `read_root` dizini yeniden doğrular, yazmaz; tutmazsa `SNAPSHOT_INTEGRITY_FAILED`.
- **Bir bayt mutasyonu** (`tests/integrity.rs::snapshot_one_byte_mutation_fails_closed`): (a) gömülü kopyada bir kayıt
  dosyasının ilk baytı değişmiş test-içi kopya → `verify_embedded` `SNAPSHOT_INTEGRITY_FAILED` (mesaj dosyayı adlandırır);
  manifest sha'sı yanlış → aynı; (b) yazılmış dizinde aynı bayt değişince `read_root`, `monitor_view`, `registry_view` →
  `SNAPSHOT_INTEGRITY_FAILED`, aynı oturumda dosya yeniden yazılmaz; yeni açılış dizini silip doğrusunu yazar; (c) fazla boş arz
  dizini ve fazla dosya → aynı, yeni açılışta silinir; (d) manifestle uyuşmayan kopya hiç kullanılmaz; (e) uygulama verisi
  korunan bir kökün altındaysa hiçbir şey yazılmaz. Ön uçta `FAILED` künyesi dört ekranı kapatır, bütünlük kutusu ve kodu
  görünür, hiçbir okuma komutu çağrılmaz (vitest).
- **Kirli ağaçtan derleme:** prova klonunda `registry/ipos.csv`'ye bir bayt eklenip derlendi (sonda testi; klon silindi):
  `BUILD_INFO.git_status_snapshot = " M registry/ipos.csv\n"`, eski `git_status_models_scores = ""` (bunu görmezdi),
  `build_dirty = true`, manifest satırı yeni baytları taşır (`registry/ipos.csv … 6805`). Künye `build_dirty` iken Monitör
  şeridi "· derlemede commit bekleyen değişiklik vardı" ekler, Sicil şeridinde kaynak kırmızıdır. Git yoksa `UNKNOWN`
  (kirli sayılmaz, bilinmez). CI temiz checkout'tan derler.

## 5. Yalıtım (K-SNAP-4)

`bash app/tests/e2e_personal_isolation.sh` (B üzerinde, ana repo) — yeni adım 2b ve sonu:

```
=== 2b. kişisel mod: gömülü sicil anlık görüntüsü (K-SNAP-4) ===
test personal_snapshot_isolation ... E2E| K-SNAP-4 anlık görüntü: 63 dosya, 627365 bayt, derleme 4a945dd, son sonuç Some("2026-09-30"), durum READY
E2E| K-SNAP-4 ekranlar: Monitör 7 arz, Sicil 7 arz / 31 kanıt, Performans 6 satır, kapı 12 çıktı; 46 okuma komutu
E2E| K-SNAP-4 anlık görüntü: 64 dosyanın sha'sı aynı; değişen yalnız ["scenarios/<ULID>.json"]
E2E| K-SNAP-4 repo git status -- registry data scores: "" (öncesiyle aynı)
anlık görüntü dizini: <app_data_dir>/snapshot/4a945dd
uygulama verisi: yalnız snapshot/ ve scenarios/ (1 kişisel kayıt)
anlık görüntü: manifestteki 63 dosyanın sha256'sı diskteki dosyayla aynı (shasum); fazla dosya yok
anlık görüntüde observed_streak_user: YOK
...
asıl repo registry/ sha listesi öncesiyle BİREBİR AYNI (1865 dosya)
asıl repo git status --porcelain -- registry data scores: BOŞ
=== e2e_personal_isolation: YEŞİL ===
```

(B2 çalışma ağacında, commit'ten hemen önce koştu; derleme sha'sı o anki HEAD `4a945dd`.) `personal_snapshot_isolation` ortam
istemez (geçici uygulama verisi), `test.sh` ve CI'da da koşar: kişisel modda açılış → Monitör, Sicil, her arz için Analiz
(arz, seri, kırılma kartı, kayıt kartı, koşullu görünüm, ham kayıt), Performans ve kapı → beyanlı kişisel kayıt → anlık
görüntüye tekli ve toplu dışa aktarma `SCENARIO_PATH_INSIDE_SNAPSHOT` ile reddedilir.

## 6. Ekran görüntüleri ve repo modu kanıtı

Kişisel modda (B'de çekildi; B2 yalnız gömülü kümeden okunmayan bir dosyayı çıkardı, ekran içeriği aynı; repo ayarı boş, yeni uygulama verisi; `screens_v2.sh` kalıbı: `BORSAI_DATA_DIR=<geçici> BORSAI_SNAPSHOT_DIR=<geçici>
VITE_BORSAI_DEMO=1 VITE_BORSAI_DEMO_V2=1 VITE_BORSAI_DEMO_SNAP=1 npm run tauri dev -- --features snapshot`, sonra `sips -Z 1440`;
`app/scripts/` bu görevde yazılabilir olmadığı için betik eklenmedi, adımlar `src/dev/demo.ts` `snapSteps`):

- `app/docs/screens/v2/snap_01_monitor.png` — "Bağımsız mod", veri şeridi "Veri: gömülü anlık görüntü · derleme 526b84f · son
  sonuç 30.09.2026", 7 arz.
- `app/docs/screens/v2/snap_02_analiz_netgl.png` — NETGL, gözlenen j = 3, kayıt kartı, kırılma akşamı.
- `app/docs/screens/v2/snap_03_sicil.png` — kaynak şeridi, künyede kaynak satırı, push kanıtı ve ekleyen commit.
- `app/docs/screens/v2/snap_04_model_performansi.png` — kaynak satırı; D1 sonrası ve kırılma bölümleri dolu.

Koşu sonunda asıl repo `registry/` ve `data/` sha listesi öncesiyle aynı (2246 dosya); uygulama verisinde yalnız `snapshot/`.

**Repo modunda metin değişmedi:** (1) `BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test sade --test stage3 -- --include-ignored`
B koduyla bütün UI fikstürlerini yeniden yazdı (97 dosya, 19:23) ve `git diff -- app/tests/fixtures` **0 satır**: repo modu
JSON çıktıları bayt bayt aynı (yeni alanlar repo modunda serileştirilmez). (2) vitest "repo modu: şerit ve künye metinleri
aynen" (Monitör'de kaynak satırı yok, Sicil şeridinde "temiz", eski giriş cümlesi, Performans'ta kaynak yok). (3) cargo
`snapshot_mode_views_equal_repo_views`: kişisel moddaki Monitör, Sicil, 7 arzın Analiz/kırılma/seri/kayıt kartı/koşullu
görünüm/ham kayıt ve Performans çıktıları repo modundakilerle aynı (yalnız `repo_root`, künye ve derleme anının `git status`'u
ayrı).

## 7. Test sayıları ve CI

| Takım | Taban (`e6c2e07`) | B / B2 (ara koşular) | Son (`73e76fa`) |
|---|---|---|---|
| pytest | 952 (paralel, 12:41) | B: 951 + 1 kırmızı yalnız commit öncesi (`test_14b`: commit'lenmemiş `app/`); commit sonrası `test_14b` + `test_5c` yeşil. B2 commit sonrası paralel: 952 passed (12:02), ayrılan yok | 952 passed in 1062.49s (0:17:42), sıralı, ayrılan yok |
| cargo Mac (`test.sh`) | 167 | 176 (+9: 2 `registry_snapshot` birim, 3 `build_embed`, 2 `integrity`, 1 `sade`, 1 `e2e`); B2 aynı | 176 passed / 0 failed |
| cargo Windows (CI, yalın) | 157 + 12 ignored (`e9f06d8`) | — | 166 passed / 0 failed / 12 ignored (+9, hepsi yeşil) |
| vitest | 377 (24 dosya) | 384 (+7); B2 aynı | 384 (24 dosya); Windows'ta da 384 |
| parity / golden_unchanged | 8 / YEŞİL | 8 / YEŞİL | 8 passed / YEŞİL |
| `gen_golden --check` | 35/0 | 35/0 (A ve B2'de ölçüldü) | 35/0 |
| `e2e_personal_isolation.sh` | — | YEŞİL (B ve B2) | YEŞİL (anlık görüntü 63 dosya, derleme `73e76fa`) |

0b provası (`/tmp/borsai_snap_20261013/`, sonunda silindi): A+B taslağıyla kırılan testlerin tam listesi —
`tests/build_embed.rs::git_calls_are_lock_free_and_read_only` (git beyaz liste pini) ve `app/tests/sade_invoke.test.ts`'te Analiz
komut pini iki iddia (`streak_view` → `arz_streak`). `e2e.rs`/`stage*.rs`'te kişisel modda boş görünüm bekleyen iddia yok
(`sade_invoke.test.ts`'teki "bağımsız mod: … repo modu gerekli" iddiası anlık görüntüsüz yapılandırmayla aynen geçer). Başka
kırılan yok; bekçi testlerine dokunulmadı.

CI: koşu [38438091552](https://github.com/AhmetEmreOzumagi/borsai/actions/runs/38438091552) (`73e76fa`, `workflow_dispatch`),
2026-10-13 17:22–17:37 UTC, üç iş yeşil:

| İş | Süre | Sonuç |
|---|---|---|
| `test-windows` | 9 dk 59 sn | cargo `--no-fail-fast` 166 passed / 0 failed / 12 ignored; yeni anlık görüntü testlerinin hepsi Windows'ta yeşil (`plan_snapshot_*`, `snapshot_git_facts_match_embedded`, `snapshot_manifest_integrity`, `snapshot_one_byte_mutation_fails_closed`, `snapshot_mode_views_equal_repo_views`, `personal_snapshot_isolation`, iki birim testi); vitest 24 dosya, 384 passed; bilgi adımı yalnız bilinen K-WIN-5 farkını gösterdi (9 fikstürde `price_hint` 1.1^k son hanesi, \|Δ\| ≤ 5.7e-14), `golden_parity` 1 passed |
| `build-windows` | 4 dk 43 sn | `BorsAi_0.1.0_x64-setup.exe` → artefakt `BorsAi-windows-73e76fa` (zip 2 895 768 bayt) |
| `build-macos` | 2 dk 44 sn | `BorsAi_0.1.0_aarch64.dmg` → artefakt `BorsAi-macos-73e76fa` (zip 3 678 663 bayt) |

Uyarılar yalnız GitHub'ın "Node.js 20 deprecated" bilgilendirmesi (eylem sürümleri; iş akışı değişmedi). **Gerçek Windows
açılışı bu oturumda doğrulanmadı**; proje sahibi ya da bir Windows kullanıcısı `BorsAi-windows-73e76fa`'yı kurup repo ayarı boşken
Monitör'de 7 arzı ve "Veri: gömülü anlık görüntü · derleme 73e76fa · son sonuç 30.09.2026" şeridini görmeli. Mac'te gerçek Tauri
açılışı (debug, ekran koşusu) anlık görüntüyü yazdı ve dört ekranı doldurdu.

## 8. Hijyen, yapılmayanlar ve açık sorular

**Hijyen** (SEALED kasa kodları `registry/oot/cohort_pre_h99.csv`, 64 kod, sözcük sınırıyla; bülten adı `th[bm]` + 8 hane;
kodlar yazılmadı, sayıldı): bu rapor, `docs/app/snapshot_test_runs.txt`, `docs/prompts/FAZ9_SNAPSHOT.md`, `README.md`,
`app/README.md`: kasa kodu 0, bülten adı 0 (5 dosya);
dört ekran görüntüsü (macOS Vision OCR metni): kasa kodu 0, bülten adı 0; görüntülerde yalnız takipteki 7 arz.
**Gömülen veride** (bilgi; görev hijyen kuralı rapor/görüntü/günlük içindir): B'de `registry/ipos.csv`'de 1 (kapsam dışı bir
bedelli kalan pay satırının kodu) ve `data/outcomes/COMPLETENESS.csv`'de 10 (temerrüt pazarı kodları ve bir birincil piyasa
satırı) kasa kodu geçişi vardı; bunlar kasanın sonuç verisi değil, var olan payların işlem kodlarıdır ve hiçbir ekranda görünmez.
Orkestratör kararıyla `COMPLETENESS.csv` B2'de çıktı: gömülü 63 dosyada kasa kodu geçişi **1** (`registry/ipos.csv`; payda
sayımları için okunur, satır `OUT_OF_SCOPE`, ekranda kod gösterilmez). Makine kayıtlarında 62 bülten adı (`streak.sessions`)
var; görünüm onları döndürmez (hijyen kuralı, `sade_break.rs`).

**Yapılmayanlar ve açık sorular**
1. **Yenileme:** anlık görüntü derleme anınındır; her yeni arz, sonuç ya da makine kaydı yeni bir CI paketi ister (Monitör
   derlemeyi ve son sonuç tarihini yazar). Otomatik tetik yok (iş akışı push'ta koşmaz).
2. **Eski dizinler:** `<app_data_dir>/snapshot/<eski sha7>/` silinmez (her biri ≈ 0,63 MB). Açılışta temizlensin mi?
3. **`COMPLETENESS.csv`:** kapandı (orkestratör kararı, B2 `73e76fa`): gömülü kümeden çıktı; `data/outcomes/` yalnız kayıtlı
   arzların `<T>.csv`'si. Kalan tek kasa kodu geçişi `registry/ipos.csv`'nin `OUT_OF_SCOPE` satırında (Monitör/Sicil payda
   sayımı bu dosyadan; satır ekranda kodla gösterilmez). İstenirse ayrı karar.
4. **`registry/post_d1/`:** bugün yok, gömülmedi. D1 sonrası kayıtlar gelince kişisel modda görünmeleri için spec'e eklenmeli
   ve `post_d1.rs`'in git bilgisi (izleme, ekleyen commit) de dondurulmalı (bu görevde `post_d1.rs` dokunulmaz).
5. **Kişisel Tahmin sonucu ekranı** anlık görüntüyü görmez (`streak_view` aynen); takipteki bir arzın girdileri kişisel modda
   girilirse resmi seri gösterilmez. İstenirse ayrı karar (U52 beyan etkileşimi).
6. Ayrıntılı (eski) görünümün Sicil ve doğruluk paneli kişisel modda repo ister (kapsam dışı).
7. Monitör tablosunun son sütunu 1440 px'te iç kaydırmada kalıyor; repo modu görüntülerinde de aynı (önceden var).

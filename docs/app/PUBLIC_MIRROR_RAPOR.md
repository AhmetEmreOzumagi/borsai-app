FAZ9_PUBLIC_MIRROR: A 76c0463 · B (bu commit) · R bekliyor · ayna 3 151 dosya, 226,5 MB · ayna testleri pytest 782/154 skip cargo 167 (+1 atlandı) vitest 384 · Release bekliyor

# BORSAI_FAZ9_PUBLIC_MIRROR_20261013 — Herkese açık ayna (`AhmetEmreOzumagi/borsai-app`): teslim raporu (B taslağı)

Görev `docs/prompts/FAZ9_PUBLIC_MIRROR.md`. Önceden onaylı pin K-PIN-MIRROR (proje sahibi başlatma cümlesinde onayladı).
Görev sırasında iki karar proje sahibine soruldu ve cevaplandı (§0). Hiçbir model, skor, sınıf ya da hüküm değişmedi;
`borsai/ models/ scores/ registry/ data/ experiments/ legacy/ app/parity/ app/src/ app/src-tauri/src/` farkı boş.
Ayna ağacı `~/Desktop/BorsAi_public/` B commit'inden üretildi; orada git komutu çalıştırılmadı. Push, etiket, Release ve ayna
reposunun oluşturulması proje sahibinindir (§9 komut bloğu).

## 0. Görev sırasında alınan kararlar (proje sahibi, 2026-10-13)

Envanterin test probu (`docs/public_mirror/INVENTORY.md` §3.2) tam geçmişli bir klonda yapılmıştı. Aynanın gerçek hâli (karar 13:
tek commit'lik yeni geçmiş) scratchpad'deki bir provada taklit edildi: kararlarla süzülmüş ağaç + `git init` + tek commit.

| Takım | Tam geçmişli klon, GİRMEZ yok (envanter) | Tek commit'lik ayna provası (bu görev, işaretsiz) |
|---|---|---|
| pytest | 79 kırmızı + 16 hata | 109 kırmızı + 50 hata |
| cargo (CI komutu) | 2 kırmızı (NETGL manifesti) | 1 kırmızı: `sade.rs::snapshot_mode_views_equal_repo_views` |
| vitest | 377/377 | 384/384 |

Ek kırmızıların hepsi özel repo geçmişini istiyordu (`git show <eski sha>`, push kanıtı için `merge-base`, commit ataları);
aralarında bekçi testleri var. Cargo kırmızısı bir ürün bulgusudur: aynadan derlenen pakette Sicil künyesindeki "kaydı ekleyen
commit" ayna commit'i olur ve yedi kaydın hepsinde "kaydı ekleyen commit için kanıt dosyası yok" yazar. K-MIR-3 yalnız
listedeki testlere işaret, K-MIR-6 uygulama kodu ve `app/src-tauri/tests` değişikliğine izin vermediğinden soruldu:

1. **İkinci atlama koşulu (`requires_git_history`)** — onaylandı. Özel repo geçmişi yoksa (ilk commit `ff3eee6` bulunamazsa)
   geçmiş isteyen testler gerekçesiyle atlanır; yalnız işaret eklenir (bekçi testleri dahil), iddialar değişmez.
2. **Release paketleri özel repo CI'ından, elle yükleme** — onaylandı. Ayna CI'ı test eder ve paketleri yalnız doğrulama
   artefaktı olarak üretir; Release oluşturmaz. O tek Rust testi yalnız ayna iş akışında `--skip` ile atlanır (gerekçe iş akışında
   yazılı). Kaydı ekleyen commit'i dosyadan gömecek uygulama değişikliği ayrı bir görev olarak önerildi (§8).

## 1. Commit'ler

| Commit | Konu |
|---|---|
| A `76c0463` | `scripts/mirror/build_mirror.py` (yalnız stdlib), nihai `MIRROR_MANIFEST.txt`, overlay (README taslağı, CI, CHANGELOG, CONTRIBUTING, `.gitattributes`, `.gitignore`), kökte `LICENSE`/`NOTICE`/`DATA_NOTICE.md`, `app/package.json` ve `app/src-tauri/Cargo.toml` `license = "Apache-2.0"`, `APP_TASKS` satırı, görev dosyası |
| B (bu commit) | `tests/conftest.py`: `requires_raw_sources`, `requires_git_history`; 30 test dosyasında 135 işaret satırı (+ `test_outcome_guard.py`'de `import pytest`, `test_faz7_vault.py`'de modül düzeyinde atlama); betik düzeltmesi (blob okuma, aşağıda); README'nin son hâli ve ölçülmüş sayıları; özel repo README'si; bu rapor |
| R | CI ve Release sonuçları, son kabul koşuları, `docs/app/public_mirror_test_runs.txt` |

Betik düzeltmesi (B): A'daki betik dosyaları çalışma ağacından okuyup blob sha'sıyla karşılaştırıyordu. Temiz kipte beş CSV'de
durdu: çalışma kopyaları CRLF, commit'teki blob LF (`eol=lf` normalleştirmesi; `git status` temiz gösterir). Durması doğru
davranıştı (fail-closed). B'de içerik `git cat-file --batch` ile HEAD blob'larından okunur ve her blob'un sha'sı yeniden
hesaplanır; ayna böylece commit'in baytlarını taşır. Kirli kip (`--allow-dirty`, yalnız prova) gerçekten değişmiş ya da
izlenmeyen dosyaları çalışma ağacından alır ve README'ye `<sha>+kirli` yazar.

## 2. Nihai manifest (`scripts/mirror/MIRROR_MANIFEST.txt`)

Sınıflama: HEAD'deki her dosya için önce GİRMEZ kalıpları (öncelikli), sonra GİRER. Hiçbir kurala uymayan dosya ya da hiçbir
dosyaya uymayan kural betiği durdurur (KARAR kalmadı; yeni bir dosya türü açık karar ister). Sayılar test edilen ayna
kopyasından (B, 3 150 dosya; bu rapor dosyası +1).

| GİRER kalıbı | Dosya | MB | GİRER kalıbı | Dosya | MB |
|---|---:|---:|---|---:|---:|
| kök (10 dosya: CLAUDE.md, README.md, LICENSE, NOTICE, DATA_NOTICE.md, pyproject.toml, requirements.lock, .gitattributes, .gitignore, iş akışı) | 10 | 0,0 | `registry/ipos.csv`, `legacy_roles.json` | 2 | 0,0 |
| `app/**` | 423 | 84,6 | `registry/records/**` | 7 | 0,3 |
| `docs/**` | 836 | 39,6 | `registry/post_break/**` | 7 | 0,0 |
| `scores/*.json` | 4 | 42,7 | `registry/inputs/**` | 7 | 0,1 |
| `tests/**` | 140 | 14,5 | `registry/legacy_frozen/**` | 29 | 0,2 |
| `borsai/**` | 39 | 1,5 | `registry/push_proofs/**` | 31 | 0,1 |
| `models/**` | 34 | 0,5 | `registry/source_docs/*/MANIFEST.json` + `_ENUMERATION/ENUMERATION.json` | 8 | 0,0 |
| `legacy/**` | 34 | 0,9 | `registry/oot/records/**` | 270 | 17,4 |
| `experiments/**` | 2 | 2,1 | `registry/oot/post_d1/**` | 135 | 3,4 |
| `scripts/**` | 11 | 0,1 | `registry/oot/inputs/**` | 135 | 2,5 |
| `data/*.py`, `training_table*.csv`, `data_version*.json` | 6 | 0,1 | `registry/oot/candidate_features/**` | 135 | 1,4 |
| `data/outcomes/**` | 8 | 0,6 | `registry/oot/candidate_features_faz7/**` | 136 | 2,2 |
| `data/outcomes_oot/**` | 270 | 1,4 | `registry/oot/d1_rows/**` | 135 | 0,2 |
| `data/raw/*.csv`, `*.json`, `xu100/**` | 15 | 8,1 | `registry/oot/source_docs/*/MANIFEST.json` | 135 | 0,3 |
| `data/raw/tuik/**` | 5 | 0,1 | `registry/oot/source_docs_faz7/**/*.json` | 135 | 1,3 |
| `data/raw/bist/MANIFEST.csv`, `MANIFEST_OOT.csv` | 2 | 0,3 | `registry/oot/cohort_pre_h99.csv`, `VAULT_OPEN.json` | 2 | 0,0 |

GİRMEZ (kalıp düzeyinde; 645 dosya, 225,3 MB):

| GİRMEZ kalıbı | Dosya | MB | Gerekçe |
|---|---:|---:|---|
| `**/*.pdf` | 555 | 208,3 | KAP/SPK PDF'leri (`registry/source_docs`, `registry/oot/source_docs`); soru 7 |
| `**/*.zip` | 73 | 15,4 | BIST THB/THM bülten zip'leri (`data/raw/bist`); soru 7 |
| `registry/source_docs/_ENUMERATION/kap_byCriteria_*.json` | 1 | 0,0 | KAP API yanıtı (bildirim listesi); manifest değil, soru 7 listesinde yok → **benim kararım: dışarıda** (§8) |
| `docs/specs_faz6/ekler/spk_tablolar/*.xlsx` | 5 | 0,1 | SPK yıllık tabloları; soru 2 |
| `docs/faz6/dogrulama/_tools/logs/**` | 11 | 1,4 | şirket adresli doğrulama günlükleri; soru 8 |

Overlay (`scripts/mirror/overlay/`, 9 dosya): README.md, CHANGELOG.md, CONTRIBUTING.md, `.github/workflows/build.yml`,
`.gitattributes` (özel repodaki kural aynen + linguist işaretleri), `.gitignore`, LICENSE, NOTICE, DATA_NOTICE.md. Yerine
geçtiği GİRER dosyalar: README.md, iş akışı, `.gitattributes`, `.gitignore`, LICENSE, NOTICE, DATA_NOTICE.md (son üçü özel repo
kökündekilerle bayt-eşit olmak zorunda; betik denetler). Yer tutucular: yalnız `@@KAYNAK_SHA@@`, `@@KAYNAK_SHA7@@`.

Betik özeti (test edilen B kopyası): GİRMEZ kalıbına uyan 0, `.pdf`/`.zip` 0, 100 MB üstü 0, 50 MB üstü 0 (en büyük
`scores/scores_oot.json` 41,3 MB), sembolik bağ 0, overlay kasa kodu 0, bülten adı 0. İkili dosya 138; TÜİK `.xls` ve
`docs`/`app/docs` görselleri dışında kalan liste yalnız 16 ikon (`app/src-tauri/icons/*`). Süre < 1 sn.

## 3. İkon ölçümü (soru 11)

- `app/src-tauri/icons/` 16 dosya, tek commit'te geldi: `50c62da` (BORSAI_FAZ3_S0, Tauri iskeleti); repoda kaynak dosya yok.
- Karşılaştırma: kurulu `@tauri-apps/cli` 2.11.5 ile geçici dizinde `tauri init` (şablonu üretir) ve şablon `icon.png`'den
  `tauri icon`. Sonuç: **`icon.ico` şablonla bayt-eşit** (sha256 `e38ca88e1d54…`). Öteki 15 dosya bayt olarak farklı; PNG'ler
  palet kipinde (renk türü 3), şablonunkiler RGBA (renk türü 6). Piksel karşılaştırması (stdlib PNG çözücü, alfa çarpımlı):
  aynı boyut, ortalama |Δ| 3,2–7,5 / 255, piksellerin %84–98'i |Δ| ≤ 16 içinde; görsel olarak aynı Tauri logosu (iki halka).
  `tauri icon` çıktısı da bayt-eşit değil. [ÇIKARIM] İkonlar Tauri şablon ikonunun sıkıştırılmış (paletli) bir sürümüdür; büyük
  olasılıkla iskelet kurulurken `create-tauri-app` şablonundan geldi.
- Sonuç: **ikon Tauri şablonudur**. README ("Lisans ve veri") ve NOTICE bunu yazar (tauri-cli MIT ya da Apache-2.0).
  Açık soru: herkese açık sürümde projeye özgü bir ikon (§8).

## 4. Atlanan testler

Mekanizma `tests/conftest.py`: `raw_sources_present()` = `data/raw/bist/**.zip` ve `registry/**/source_docs/**/*.pdf` var;
`git_history_present()` = özel reponun ilk commit'i (`ff3eee6…`) bu depoda var. İşaretli bir test, koşulu sağlanmıyorsa
toplamada gerekçeli `skip` alır. Gerekçe metinleri:

- `requires_raw_sources`: "ham bülten ve resmi belgeler herkese açık aynada yeniden dağıtılmaz"
- `requires_git_history`: "zaman kanıtı ve commit geçmişi özel repodadır; herkese açık ayna tek commit'tir"

Seçim ölçümle yapıldı (scratchpad provaları, sonra silinecek): (a) tam geçmişli klon + nihai dosya kümesi (PDF/zip/xlsx/günlük/
KAP API yanıtı `git rm`) → 77 kırmızı; bunlardan 76'sı envanter listesindeydi (`requires_raw_sources`), 1'i (`test_14b`) provanın
silme commit'inin yan etkisiydi; (b) tek commit'lik ayna → 154 kırmızı test kimliği; (b) − (a) = 77 test + `test_faz7_vault.py`
modülü → `requires_git_history`. Envanter listesinin 90 kimliğinden 12'si manifestler girdiği için aynada yeşil (işaretlenmedi):
`test_registry_ipos.py` (toplama hatası kalktı, 6 test), `test_faz7_prospectus.py` 4, `test_outcome_guard.py` 6,
`test_faz6_oot.py::test_real_listing_source_matches_pinned_document`; 1'i geçmiş (`test_faz8_live.py::test_real_seven_machine_records_…`),
1'i vault modülünde.

| Dosya | raw | geçmiş | Dosya | raw | geçmiş |
|---|---:|---:|---|---:|---:|
| `test_faz1b_guardrails.py` | 0 | 3 | `test_faz7c_golden.py` | 0 | 5 |
| `test_faz4_ceiling_path.py` | 1 | 3 | `test_faz7c_model.py` | 0 | 2 |
| `test_faz5_frozen.py` | 0 | 1 | `test_faz8_break.py` | 0 | 1 |
| `test_faz5_live.py` | 14 | 5 | `test_faz8_frozen.py` | 1 | 2 |
| `test_faz5_post_d1.py` | 1 | 4 | `test_faz8_golden.py` | 0 | 1 |
| `test_faz6_oot.py` | 2 | 0 | `test_faz8_live.py` | 6 | 3 |
| `test_faz7_freeze.py` | 5 | 0 | `test_faz8_model.py` | 0 | 1 |
| `test_faz7_frozen.py` | 1 | 3 | `test_freeze_records.py` | 8 | 0 |
| `test_faz7_golden.py` | 0 | 4 | `test_models.py` | 0 | 1 |
| `test_faz7_oot.py` | 0 | 11 | `test_outcome_guard.py` | 1 | 5 |
| `test_faz7_table_v2.py` | 1 | 0 | `test_outcomes.py` | 5 | 0 |
| `test_faz7_vault.py` | 0 | modül (17) | `test_push_proof.py` | 0 | 5 |
| `test_faz7c_backtest.py` | 0 | 1 | `test_registry_inputs.py` | 3 | 0 |
| `test_faz7c_freeze.py` | 3 | 0 | `test_scoring.py` | 3 | 11 |
| `test_faz7c_frozen.py` | 1 | 3 | `test_scoring_conditional.py` | 2 | 2 |

Fonksiyon olarak 58 + 77 işaret (parametreli olanlarla 76 + 77 test kimliği). Değişen satırlar yalnız eklemedir: 135
dekoratör, `test_outcome_guard.py`'de `import pytest` (dosya pytest'i içe aktarmıyordu), `test_faz7_vault.py`'de modül
düzeyinde atlama (`REAL_MARKER` içe aktarmada gerçek deponun kasa işaretini push kanıtıyla doğrular; geçmiş yoksa modül
toplanamaz). İddia değişikliği 0.

| Ölçüm | Sonuç |
|---|---|
| Özel repo, sıralı `.venv/bin/pytest -q -rs` (B ağacı) | **952 passed, 0 skipped** (26 dk 44 sn) |
| Ayna (B, tek commit), `pytest -q -n 6 --dist loadgroup -rfEs` | **782 passed, 154 skipped, 0 kırmızı** (76 ham kaynak + 77 geçmiş + 1 modül = 17 test) |
| Ayna, CI komutu `cargo test --workspace --no-fail-fast -- --exact --skip snapshot_mode_views_equal_repo_views` | **167 passed, 0 failed, 13 ignored, 1 atlandı**; NETGL manifesti girdiği için envanterin 2 kırmızısı yeşil (biri `#[ignore]`) |
| Ayna, `npm ci && npm test` | **24 dosya, 384 test**; `npm ci` kilit dosyasına dokunmadı (`license` alanı eklenmiş `package.json` ile) |
| Ayna, `gen_golden.py --check` / `test_gen_golden.py` | **35/0** / 8 passed |
| Özel repo, `bash app/scripts/test.sh` (A değişiklikleriyle) | cargo 176, vitest 384, parite 8, golden_unchanged YEŞİL |

## 5. README'deki sayıların kaynağı

| README'deki sayı | Kaynak |
|---|---|
| Geçmiş veri testi birincil hücreleri (n, fark, aralık, hüküm) | `scores/scores.json` → `models[].backtest.cells` (`label == "birincil"`); `docs/SCORES.md` §5 ile aynı |
| 99 arz, 2023-09-22…2026-08-06 | `docs/DATA.md` (eğitim tablosu kapsamı) |
| Zaman-dışı açık küme 71, kasa 64, birincil hücreler | `scores/scores_oot.json` → `oot_pre_h99`, `oot_pre_h99_sealed`, `oot_pre_h99_all` (`models[].cells`, birincil) |
| Canlı 7 arz, 18.08–17.09.2026, en çok n = 7, LIVE satır 1 | `scores/scores.json` → `models[].live` (`n_scored`, `n_live`, `n_late`), `outcomes`; `registry/ipos.csv` (FROZEN 7) |
| D1 sonrası ve kırılma: canlı satır 0 | `scores_post_d1.json` (RETRO 7), `scores_break.json` → `live_break.n_retro = 7`, `n_scored = 0` |
| Modeller 27 / 1 / 2 | `models/INDEX.json`, `INDEX_POST_D1.json`, `INDEX_POST_BREAK.json` (`models` uzunluğu) |
| Son sonuç 30.09.2026 | `scores/scores.json` `as_of_session`; Monitör görüntüsü |
| Test sonuçları ve atlama sayıları | §4 tablo (bu görevin koşuları) |
| Kaynak commit | `build_mirror.py` yer tutucusu (`@@KAYNAK_SHA@@`) |

Abartı denetimi: "canlıda kanıtlandı" ya da eşdeğeri yok; geçmiş veri testi "ileriye dönük doğruluğun kanıtı değildir" ile,
eski kohortta `ceiling_hazard_v0`'ın geçemediği özetle birlikte yazılı. Görseller göreli (`app/docs/screens/v2/`): 4 görüntü
(Monitör, Analiz, hesaplayıcı, model performansı); README'de 36 göreli bağlantı, kırık 0 (aynada ölçüldü).

## 6. Lisans

- Bağımlılık dağılımı (INVENTORY §4.5, değişmedi): npm 82 paket (GPL/AGPL/LGPL 0; MPL-2.0 2; OFL-1.1 3 yazı tipi), cargo
  macOS çözümü 258 paket (GPL/AGPL 0; MPL-2.0 5: `cssparser`, `cssparser-macros`, `dtoa-short`, `option-ext`, `selectors`),
  Python 14 paket (hepsi izinli). Apache-2.0 bunların hepsiyle uyumlu.
- `npm audit` (aynada, `npm ci` sonrası): üretim bağımlılıkları 0 açık; geliştirme zincirinde 1 yüksek önemde uyarı
  (`source-map-js` ≤ 1.2.1, GHSA-68fv-2mgg-jv7q, olay döngüsü DoS; Vite derleme aracı, pakete girmez). Düzeltilmedi (§8).
- `LICENSE`: Apache License 2.0 tam metni, 11 358 bayt, sha256 `cfc7749b96f6…` (apache.org `LICENSE-2.0.txt` ile aynı değer;
  ağ yok, metin yerel cargo önbelleğindeki iki bağımsız crate'in aynı baytlı kopyasından alındı).
- `NOTICE`: telif satırı (Copyright 2026 Ahmet Emre Özümağı), kodun Apache-2.0 olduğu, veri için `DATA_NOTICE.md`, Apache-2.0'ın
  kaynak kurumlar üzerinde hak tanımadığı, ikonun Tauri şablonu olduğu (TR + EN).
- `DATA_NOTICE.md`: İngilizce özet; kaynak tablosu (BIST THB/THM ve URL kalıbı, XU100, tatil tabloları, KAP, SPK, TÜİK, GitHub
  status API) ve depodaki karşılıkları; "Resmi bültenler ve belgeler yeniden dağıtılmaz" ve aynada olmayanların listesi; koşullar
  (Apache-2.0 yalnız kod; veri dosyalarına ayrı lisans verilmez, kaynak değerler kurumların koşullarına tabi; "Hukuki görüş
  alınmamıştır"; itiraz olursa kapsam yeniden değerlendirilir; garanti yok; yatırım tavsiyesi değil).
- `app/package.json` `"license": "Apache-2.0"`, `app/src-tauri/Cargo.toml` `license = "Apache-2.0"`. `app/` için ayrı kopya yok.

## 7. Ayna CI ve Release

Ayna iş akışı (`scripts/mirror/overlay/.github/workflows/build.yml`; Ruby Psych ile ayrıştırıldı): `workflow_dispatch` + `v*`;
`permissions: contents: read`, secret yok, yazma izni yok. İşler: `test-windows` (özel repodakinin kopyası; cargo adımında tek
`--skip`), `test-python` (macos-latest, setup-python 3.12, `pip install -r requirements.lock`, `pytest -q -rs`, parite),
`build-windows` (`needs: test-windows`), `build-macos`. Release işi yok (karar 2): paketler özel repo CI'ında aynı kaynak
commit'ten derlenir ve proje sahibi `gh release create` ile yükler.

R'de doldurulacak: ayna CI koşusu (süreler, iş sonuçları, Windows cargo/vitest sayıları, macOS pytest sayıları), özel repo CI
koşusu ve Release varlıkları (ad, boyut, sha256).

## 8. Hijyen, yapılmayanlar, açık sorular

- Hijyen (kasa kodu / `th[bm]` + 8 hane): overlay 9 dosya, aynadaki işlenmiş overlay 8 dosya, özel README, LICENSE, NOTICE,
  DATA_NOTICE, manifest, betik, conftest, görev dosyası ve test dosyalarına eklenen satırlar: **0 / 0**. Kasa kodları yalnız
  bellekte (betik, `registry/oot/cohort_pre_h99.csv`'den okur); ekrana basılan yollar maskeli.
- Korunan dizinler: `git diff 459d8fc -- borsai models scores registry data experiments legacy app/parity app/src app/src-tauri/src` boş.
- **Yapılmadı (K-MIR-6):** K-15 SPK cümlesi uygulama metnine eklenmedi (`app/src/**` yazılamaz); README ve DATA_NOTICE'ta var.
  Uygulama metni ve `disclaimer.test.ts` ayrı görev.
- **Önerilen ayrı görev:** kaydı ekleyen commit ve push kanıtı eşlemesini derlemede git'ten değil sicildeki bir dosyadan gömmek;
  böylece aynadan derlenen paket de Sicil kanıtını doğru gösterir ve ayna CI'ındaki `--skip` kalkar.
- Benim kararım: `registry/source_docs/_ENUMERATION/kap_byCriteria_*.json` (KAP API yanıtı) dışarıda. Hiçbir test istemiyor
  (aynada yeşil); karar proje sahibinin.
- Açık sorular: hukuki görüş (BIST/KAP/SPK veri koşulları; DATA_NOTICE ve README "alınmamıştır" der); ayna güncelleme ritmi
  (öneri: her yeni sürüm etiketinde betikle yeni bir commit); herkese açık sürüm için projeye özgü ikon; `source-map-js`
  güncellemesi (geliştirme bağımlılığı); test-python işinin macOS CI'ında süresi ve sayısal yeniden üretilebilirliği ilk koşuda
  görülecek.

## 9. Proje sahibine komut bloğu

R'de son hâli; B sonunda verilen blok proje sahibine iletilen mesajdadır.

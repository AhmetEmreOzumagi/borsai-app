# BorsAi uygulaması uygunluk denetimi (SPEC_APP, EK 2 ve aşama görev kararlarına karşı)

Görev: BORSAI_FAZ3_FABLE_APP_AUDIT_20260923. Denetleyen: Fable. Taban: HEAD `8fa0bf5` (BORSAI_FAZ3_S5), ağaç temiz (tek izinli izlenmeyen dosya: bu görevin dosyası). Tarih: 2026-09-23. İşaretler: **[ÖLÇTÜM]** bu oturumda komut/dosyadan, **[ÇIKARIM]** yorum.

Denetimin asıl sorusu: uygulama resmi sicile, skora ya da kullanıcının resmi sanacağı bir sayıya yanlış bir şey sokabilir mi?

## Genel hüküm: **DÜZELTMEYLE UYGUN**

Uygulama gerçek arz dondurmasında kullanılabilir; önce B1 ve B3 (dondur akışı ve kişisel kayıt izolasyonu) kapatılmalı, B2 aynı düzeltme turunda önerilir. Hiçbir bulgu resmi kayda ya da `scores.json`'a yanlış bir SAYI sokmaz: kayıt yazıcı Python'dur, uygulama skor hesaplamaz, resmi görünüm yalnız kayıttan okur; bunlar hem kodda hem testte hem de mutasyonla doğrulandı. B1 bir değişmezin (kişisel kayıt `registry/` altına düşemez) testsiz kırılabilen bir yoludur; dosya sicile düşse de skorlanamaz (`record_type` yok, U29), yani yanlış sayı üretmez ama şartname yasağını çiğner.

## Özet (10 satır)

1. **[ÖLÇTÜM]** Tam koşu yeşil: cargo 95 test / 16 ikili, vitest 207 test / 15 dosya, `test_gen_golden` 4, U46 betiği; iki e2e betiği; pytest 432 test (921 s). Asıl repo `git status` ve `registry/`, `data/`, `scores/` sha listeleri koşu öncesiyle birebir aynı.
2. **[ÖLÇTÜM]** U1–U52 ve A5-1…A5-7 için 59 satır: 52 EVET, 7 KISMEN, 0 HAYIR. Hiçbir test boş ya da kendini doğrulayan değil; U28'deki `let _ = scen_before` kusuru aşama 5'te gerçekten kapanmış (`tests/e2e.rs:363` karşılaştırıyor).
3. **[ÖLÇTÜM]** 11 mutasyon (istenen 9 + iki varyant): 9'u kırmızı. Kırmızı olmayan iki mutasyon: (a) altın vektörde son hane (|Δ| = 6.7e-16, 1e-9 toleransının altında; U1 bayt denetimi kırmızı) ve (e2) beyanlı j'nin api satırından bir satır önce türetilmesi (U52-5 statik taraması yalnız `api.` geçen satırlara bakıyor) → B2.
4. **[ÖLÇTÜM]** Bağımsız parite örneklemi: 122 yeni girdi × 19 model = 2318 satır, `gen_golden.py` kullanılmadı; 0 uyuşmazlık, maks |Δ| = 1.14e-13, 2315/2318 bit-eşit. 7 resmi kayıt × 16 model = 112 hücre bit-eşit (maks |Δ| = 0); 3 Faz 4 modeli her kayıtta "kayıtta yok" (uyuşmazlık değil).
5. **[ÖLÇTÜM]** Kişisel kayıt yol bekçisi: büyük/küçük harf, sembolik bağlı dizin, `..` ve repo altına ayarlanmış uygulama verisi reddediliyor; **askıda sembolik bağ (dosya) hedefi bekçiyi geçiyor** ve dosya `registry/records/` altına yazılıyor → B1 (KRİTİK, tanım gereği).
6. **[ÖLÇTÜM]** Dondur sihirbazının 6. adım düğmesi yalnız adım 3–5'i şart koşuyor; adım 1'in DUR'ları (`INDEX_SHA`, `BORSAI_IMPORT`) `freeze_record` komutunda yeniden denetlenmiyor → B3 (ÖNEMLİ). Python `borsai.freeze` girdi denetimini (adım 4) kendisi tekrarlıyor; kayıt her koşulda Python'un ve repo INDEX'inindir.
7. **[ÖLÇTÜM]** Uygulama skor hesaplamıyor (TS ve Rust taramaları boş), iki terazi hiçbir öğede birleşmiyor, "geçiyor" dizesi yalnız `tr.ts` verdict eşlemesinde ve `scores.rs` denetim sabitinde, n < 10'da hiçbir metrik/hüküm yok (Rust fail-closed + TS satır-tablo dalı).
8. **[ÖLÇTÜM]** Beyan yalnız etiket: Rust koşullu komutlarının imzasında beyan yok, render beyan resmi verinin önündeyken bölümü ve getiri kartını boş bırakıyor; DOM taramalı U52 testi pozitif kontrollü. Açık: ekran mantığı (`screens/*.ts`) hiçbir testte sahte `invoke` ile sınanmıyor (B2).
9. **[ÖLÇTÜM]** 8 ekran görüntüsü şartnameyle uyumlu; tek uyuşmazlık README satırı: `04` görüntüsünde `v1_5_market20_v0` RET kodu `MARKET20_XU100_CLOSE_MISSING`, README "F3_MISSING" diyor (B4).
10. **[ÇIKARIM]** identifier `tr.borsai.app` kalsın: Tauri uyarısı ("ends with `.app` … conflicts with the application bundle extension") bu kişisel, ad-hoc imzalı derlemede gerçek bir soruna yol açmıyor; uygulama bu kimlikle kuruldu, LaunchServices'e kaydoldu ve WebView çalıştı; taşınacak veri bugün yok (`Application Support/tr.borsai.app` henüz oluşmamış).

## Bulgu tablosu

| # | Önem | Alan | Kanıt | Düzeltme tarifi |
|---|---|---|---|---|
| B1 | **KRİTİK** (tanım gereği: değişmez testsiz kırılabilir; pratik etki düşük, dosya skorlanamaz) | U27 kişisel kayıt izolasyonu | `ekler/yol_bekcisi_sonda.txt`: `export[symlink_file] -> Ok("OK"); repo'da dosya oluştu mu: true`. Neden: `app/src-tauri/src/commands/config.rs:101-119` `is_within` hedef yolu `canonicalize` ile çözer; askıda sembolik bağ çözülemeyince en yakın var olan ataya (repo dışı) düşer ve `false` döner; `commands/scenario.rs:303` (`std::fs::write(target, …)`) ve `:346` bağı izleyip repo içine yazar. | `scenario.rs::check_export_target` (286–296): `std::fs::symlink_metadata(target)` bağsa `read_link` ile hedefi çözüp yeniden denetle ya da doğrudan `SCENARIO_PATH_INSIDE_REPO`/`INVALID_ARGUMENT` ile reddet; yazımı `std::fs::write` yerine `OpenOptions::new().write(true).create_new(true)` ile yap (O_EXCL bağ varsa EEXIST verir; iki yol da tekli+toplu dışa aktarmada). `is_within`'e `..` içeren var olmayan yollar için sözcüksel normalizasyon ekle (sonda: `dotdot_nonexistent_mid -> false`, yazma OS'ta ENOENT ile düşüyor, bugün zararsız). Test: `tests/stage2.rs::scenario_path_guard`'a askıda bağ ve dizin bağı hedefi (tekli ve `export_all_scenarios_in`); `tests/e2e.rs::freeze_flow` U28 bölümüne aynı iki hedef; beklenen: ret ve `registry/` sha listesi değişmez. Düzeltme öncesi bu testler kırmızı olmalı. |
| B2 | ÖNEMLİ | U52-5 (ön uç), U38/U49 ekran mantığı | Mutasyon (e2) yeşil: `screens/results.ts:81` `const j = (… ?? 0) + store.view.declared.filter((x) => x).length` ile `npm test` (tsc + 207 vitest) geçiyor (`ekler/mutasyon_ciktilari.txt`). `tests/u52_declaration.test.ts:319-331` yalnız `api.` geçen satırlarda beyan sözcüğü arıyor; `screens/results.ts` ve `screens/registry.ts` izinli listede; hiçbir test `screens/*.ts`'yi sahte `invoke` ile koşturmuyor. Mutasyon (e1) (aynı ifade doğrudan api satırında) kırmızı. | (1) `tests/screens_invoke.test.ts` (yeni): `vi.mock("@tauri-apps/api/core")` ile `invoke` yakala; `screens/results.ts` `derive()` ve `screens/registry.ts` `loadRecord()`'u SNTB1 fixture'ı (resmi j = 2) + D3 beyanı ile koştur; `ceiling_display`, `path_conditional`, `record_ceiling` çağrılarının `j`/`jOrT` argümanı resmi j'ye eşit, `streak_view` tek argümanlı, `predict_all` sicil ekranında 0 çağrı (U49 "sayaç 0" gerçek sayaçla). (2) Statik taramayı veri akışına çevir: `screens/*.ts` içinde `declared` yalnız `data-action="declare"` işleyicisi, `save()` ve `resetView` çağrılarında; `j`/`jSelected` türetilen satırlarda yasak. Mutasyon (e2) düzeltme sonrası kırmızı olmalı. |
| B3 | ÖNEMLİ | §3e dondur akışı ön koşulları | `app/src/render/freeze.ts:236` `ready = pit boş && acknowledged && written` — adım 1 (`preflight`) koşulmadan da "Dondur" açılır; `commands/freeze.rs:212-238` `freeze_in` `INDEX_SHA`/`BORSAI_IMPORT` engelleyicilerini yeniden denetlemez. Sonuç: gömülü INDEX repo'dan eskiyse kayıt yine Python'un ve repo INDEX'inin (doğru), ama parite bloğu uyuşmazlık/"kayıtta yok" gösterir ve `app/parity/incidents/` altına sahte olay dosyası yazılır (`parity.rs:342-358`). Python adım 4'ü kendisi tekrarlar (`borsai/freeze.py:219-221`), o kapı sağlam. | `freeze_in` başında `preflight_in(repo, embedded_index_sha, t)` koş; `!ok` ise `FREEZE_PREFLIGHT_BLOCKED` (yeni kod, `tr.ts` `ERROR_TEXT`'e metin) ile dön, Python çağrılmasın. Ön uçta `ready`'ye `preflight?.ok === true` ekle. Test: `tests/stage3.rs` (yeni `freeze_refuses_when_preflight_blocked`): `embedded_index_sha = "0"*64` ile `freeze_in` → hata, `registry/records` değişmedi, `app/parity/incidents` boş; `tests/freeze.test.ts`: preflight yokken düğme kapalı. |
| B4 | KÜÇÜK | Ekran README iddiası | `app/docs/screens/README.md:32` `04` için "5 RET bloğu (F3_MISSING: … v1_5_market20_v0 …)"; görüntüde `v1_5_market20_v0` bloğu `RET · MARKET20_XU100_CLOSE_MISSING` (repo modu f6, çekim günü penceresinde kapanış eksik; market20 sarmalayıcısı f3'ten önce reddeder, Python'la aynı). U7'nin market20 kanıtı test tarafında (`stage2.rs::u7_veyas_four_refusals`) doğru. | README satırını görüntüyle eşle ("dört model F3_MISSING, market20 f6 reddi") ya da görüntüyü elle f6 ile yeniden al. |
| B5 | KÜÇÜK | Ortam yoksa sessizce geçen testler | `crates/borsai_predict/tests/records_parity.rs:37-41`, `tests/e2e.rs:198-201, 437-440, 524-531`, `tests/stage3.rs:110-113, 582-586, 609-612`, `tests/stage2.rs:509-512`: env yoksa `return` ile **ok**. `test.sh` ve betikler env'i veriyor (tam koşuda hepsi koştu **[ÖLÇTÜM]**), yalın `cargo test` yeşil görünür. | Env yoksa `panic!` (varsayılan) ve açık `BORSAI_SKIP_REPO_TESTS=1` ile atla; ya da `#[ignore]` + `test.sh`'ta `-- --include-ignored`. |
| B6 | KÜÇÜK | U35 girdi belgesi sürümü | `commands/inputs_doc.rs:205-208` `INPUTS_SCHEMA_UNSUPPORTED` yolu var; `tests/stage2.rs::input_document_read_only` sürüm uyumsuzluğunu sınamıyor (scores/record/scenario sınanıyor). | `input_document_read_only`'ye geçici repoda `schema_version: "borsai.inputs/0"` belgesiyle `read_input_document_in` → `INPUTS_SCHEMA_UNSUPPORTED`, kayıt görüntüleme kapalı (vitest: `render/inputs` prefill hata kutusu). |
| B7 | KÜÇÜK | U30 iptal sonrası `active_records` | `app/tests/e2e_freeze_tmp_repo.sh` adım 4 yalnız `len(recs)` yazdırır; `tests/e2e.rs:283-288` iptal sonrası uygulama görünümüyle `n_active == 1` sınar (PB kaydı etkin kalır). Python'un `active_records`'u iptal edilen dosyayı listelemiyor mu, doğrudan sınanmıyor. | Betik adım 4'e `assert len(recs) == 1 and iptal edilen dosya adı not in recs` ekle (betik zaten iptal dosya adını bilmiyor; `cargo test` çıktısından yakalanır ya da e2e.rs Python'u `-c` ile çağırıp sınar). |
| B8 | KÜÇÜK | `path_conditional` OUTPUT kaynağı sha varsayılanı | `commands/path.rs:286-290`: `params_sha256` verilmezse gömülü sha kabul edilir; ön uç her zaman `run.params_sha256` gönderir (`screens/results.ts:58-64`), bugün etkisi yok. | Alanı zorunlu yap (`None` → `INVALID_ARGUMENT`); `stage3.rs::official_conditional_return_uses_record_only`'ye `source_output(…, None)` → hata satırı. |
| B9 | KÜÇÜK | U34 sapması | `Cargo.lock`'ta `reqwest`/`hyper` var (Tauri 2 mobil hedefleri); `tests/no_network.rs:3-7` bunu belgeleyip macOS'a çözülmüş grafiği (`cargo metadata --filter-platform aarch64-apple-darwin`) sınıyor; `ureq`/`tauri-plugin-http` yok. Şartname metniyle ("Cargo.lock'ta yok") çelişir, güvenlik açısından eşdeğer. | Kabul; SPEC_APP U34 satırına "macOS'a çözülmüş grafik" notu (belge güncellemesi proje sahibinde). |
| B10 | KÜÇÜK | U2 toleransı ve sessiz sürüklenme | Mutasyon (a): son hane değişimi (|Δ| = 6.7e-16) `golden_parity` yeşil, bit-eşit 392 → 391; yalnız `test_gen_golden.py::test_golden_files_are_reproducible` (bayt denetimi) kırmızı. 1e-8'lik değişim `golden_parity` kırmızı (a3). Tolerans şartname gereği 1e-9; bit-eşitlik yalnız rapor. | `golden.rs::golden_parity`'ye taban: `bit_equal_rows ≥ MANIFEST'e yazılacak bit_equal_floor` (bugün 7671/7679) — tolerans içindeki sessiz sürüklenmeyi yakalar; MANIFEST'e `bit_equal_floor` alanı `gen_golden.py` tarafından yazılır. |
| B11 | KÜÇÜK | Python hata sınıflandırması metinle | `commands/freeze.rs:147-156` `classify` stderr'de `"DUPLICATE_RECORD"` ve `"iptal ilk işlem gününden"` alt dizelerini arar; e2e ikisini de sınıyor **[ÖLÇTÜM]**. Python mesajı değişirse kod `PYTHON_FAILED`'e düşer (ham stderr yine görünür; güvenli yön). | `borsai.freeze` CLI'sına makine okunur çıkış (`stderr` son satırı `CODE=DUPLICATE_RECORD` gibi) eklenmesi Python görevi (Ö-görevi); uygulama tarafı değişmez. |
| B12 | KÜÇÜK | Push kanıtı göstergesi | `commands/registry.rs:302-307` kanıtı yalnız kaydı ekleyen commit'in sha'sıyla eşler; SPEC_SCORING §5 torun commit kanıtını da sayar. Bugünkü 7 kayıt için ekleyen commit'lerin kanıtı var (`15` görüntüsü ve `registry/push_proofs/` **[ÖLÇTÜM]**), yön "bulunamadı" (tutucu), sınıf hesaplanmıyor. | Gösterge metnini "bu commit için kanıt dosyası yok; torun commit kanıtı Faz 2B'de değerlendirilir" yap ya da `git merge-base --is-ancestor` ile (beyaz listeye eklenir) torun kanıtını "kanıt (torun): …" diye göster. |

Aşağıdaki adımlar 1–7 sırayla; her ölçüm `ekler/` altındaki dosyaya bağlıdır.

## Adım 0. Taban [ÖLÇTÜM]

```
8fa0bf5 BORSAI_FAZ3_S5: export-all personal records, per-screen mode band …
0341bc6 BORSAI_FAZ3_S4 …   510f890 BORSAI_FAZ3_P2 …
git status --porcelain: ?? docs/prompts/FAZ3_FABLE_APP_AUDIT.md
```

Okunanlar: CLAUDE.md; SPEC_APP.md tamamı; SPEC_APP_EK2.md tamamı; SPEC_SCORING §5–§9; SPEC_CEILING_PATH_V0 §5, §7; FAZ3_APP_STAGE3/P1/P2/STAGE4/STAGE5 görev dosyaları; FAZ3_FABLE_APP_SPEC K1–K4; `app/` altındaki bütün Rust (`src-tauri/src/**`, `crates/borsai_predict/src/**`, `tests/**`), TS (`src/**`, `tests/**`) ve betikler. Kod yeniden üretimde kaynak olarak kullanılmadı; yalnız denetlendi.

## Adım 1. Tam koşu [ÖLÇTÜM] (`ekler/test_runs.txt`)

| Koşu | Sonuç | Süre |
|---|---|---|
| `bash app/scripts/test.sh` | cargo: 16 ikili, 95 geçti / 0 kaldı; vitest: 15 dosya, 207 test; `test_gen_golden.py` 4; `golden_unchanged.sh` YEŞİL | 82 s |
| `bash app/tests/e2e_freeze_tmp_repo.sh` | YEŞİL; PB kaydı 19 model `parite: 19/19, |Δ|max = 0`; ikinci kayıt 19/19; `DUPLICATE_RECORD`; iptal; U31 kırmızı uyarı + Python iptal reddi; eski 7 kayıt `16/16 · kayıt INDEX'ten eski: 3`; U28 sha listesi aynı | 7 s |
| `bash app/tests/e2e_personal_isolation.sh` | YEŞİL; `data/outcomes` 8, `registry` 95, `scores` 1 dosya sha aynı; beyan alanı yalnız uygulama verisinde | 5 s |
| `.venv/bin/pytest -q` | 432 geçti | 921 s |

Asıl repoda koşu öncesi/sonrası: `git status --porcelain` aynı (`?? docs/prompts/FAZ3_FABLE_APP_AUDIT.md`); `registry/` (95), `data/` (84), `scores/` (1) dosya sha256 listeleri `diff` boş. Parite raporu (`ekler/parity_report_full_run.json`): 19/19 model, 7679 satır, maks |Δ| 1.137e-13, bit-eşit 7671 (0.99896); koşullu (6 tavan modeli) Δ = 0; tavan yolu koşullu 3 × (520 + 400) vektör Δ = 0; yamalı 31/31.

## Adım 2. U-tablosu

Sütunlar: şartname cümlesi (kısa) · test dosyası:fonksiyon · gerçekten bunu sınıyor mu · sonuç. Dosya yolları `app/` köküne göre; `crate/` = `src-tauri/crates/borsai_predict/`.

| U | Şartname (kısa) | Test | Sınıyor mu | Sonuç |
|---|---|---|---|---|
| U1 | Her model için altın dosya ≥ 200 satır; üretici yalnız stdlib | `crate/tests/golden.rs::golden_files_present`; `parity/test_gen_golden.py::test_generator_imports_only_stdlib_predict_path`, `::test_every_pinned_model_has_at_least_200_rows`, `::test_golden_files_are_reproducible` | EVET: alt süreçte `sys.modules` taraması, satır sayısı, `--check` bayt bayt | yeşil |
| U2 | Bütün satırlarda §1.3 karşılaştırması, \|Δ\| ≤ 1e-9 | `golden.rs::golden_parity` (+ `::comparator_detects_mismatch` karşılaştırıcının kendisini sınar: 1e-8, ret kodu/alanı, uyarı, yön, NaN, hata türü) | EVET; rapor `target/parity_report.json` | yeşil; 19/19, maks 1.14e-13; mutasyon (b1)(b2)(a3) kırmızı, (a) son hane tolerans altı (B10) |
| U3 | Her T-2 kodu ≥ 2 satır; kırpma her ufukta UPPER/LOWER | `crate/tests/coverage.rs::golden_coverage` | EVET: sayım `expected`'tan, muafiyetler MANIFEST'te gerekçeli (f4/pb3 üst, F3_FILTER yamalı) | yeşil |
| U4 | `_pct`, `float(Decimal)`, Neumaier, `n/d` | `crate/tests/dec_semantics.rs::dec_semantics_{parse,pct,mul28,to_float,fsum,int_ratio,exact200,pb1_ln}` | EVET; beklenenler Python'dan `dec_cases.json` | yeşil |
| U5 | `predict_all` INDEX'in her modeli için sütun, sıra, sha | `tests/integrity.rs::predict_all_covers_index` | EVET (19/19, sha eşit, f3 boşta 5 RET) | yeşil |
| U6 | 7 resmi kayıt × modeller parite | `crate/tests/records_parity.rs::records_parity` | EVET (BORSAI_REPO ile; env yoksa sessiz ok → B5) | yeşil; 7 × 16 = 112 hücre bit-eşit |
| U7 | f3 boş → RET kümesi, PB dolu | `tests/stage2.rs::u7_veyas_four_refusals`; `tests/results.test.ts` "U7"; `integrity.rs::predict_all_covers_index` | EVET (5 RET + 14 dolu, EK 2 güncel) | yeşil; ekran B4 |
| U8 | Her kod için metin | `tests/codes.test.ts` codes_have_text | EVET: `tr.ts` küme = Rust sabitleri + şartname T-2 | yeşil |
| U9 | f6 yok/bayat: yalnız market20 RET | `stage2.rs::u9_f6_missing_and_stale`; `results.test.ts` "U9" | EVET (diğer 18 çıktı birebir eşit) | yeşil |
| U10 | Kırpma işareti ve ham değer | `stage2.rs::u10_clipping`; `results.test.ts` "U10" | EVET | yeşil |
| U11 | Uyarılar hücre gizlemez | `stage2.rs::u11_warnings_do_not_hide`; `results.test.ts` "U11" | EVET (19 dolu, rozet = uyarı sayısı) | yeşil |
| U12 | Bozuk parametre → INTEGRITY_FAILED | `integrity.rs::integrity_fail_closed` | EVET (coef kısaltma, sha, INDEX sha, şema) | yeşil |
| U13 | Başlıklar ve n alt satırı | `tests/accuracy.test.ts` "U13" | EVET | yeşil |
| U14 | İki terazi ayrı, toplanmaz | `accuracy.test.ts` "U14" | EVET DOM'da (`.panel-backtest`/`.panel-live` iç içe değil, `data-scale`); statik kısım sezgisel regex | yeşil |
| U15 | Metrik satırı alanları, puan birimi | `accuracy.test.ts` "U15" | EVET | yeşil |
| U16 | n < 10 yalnız satır tablosu | `accuracy.test.ts` "U16"; Rust `stage4.rs::integrity_is_fail_closed` (`LIVE_CELLS_BELOW_MIN_N`) | EVET (iki katman) | yeşil; mutasyon (c) kırmızı |
| U17 | 10 ≤ n < 30 yetersiz örnek | `accuracy.test.ts` "U17" | EVET (rozet, `ci95` null, `.win/.lose` yok) | yeşil |
| U18 | n ≥ 30 hüküm ve renk | `accuracy.test.ts` "U18" | EVET (metin `verdict`'ten) | yeşil; mutasyon (d) kırmızı (Rust) |
| U19 | "geçiyor" yalnız verdict eşlemesinde | `accuracy.test.ts` "U19" (TS + Rust kaynak taraması + DOM sayımı); `results.test.ts` kart | EVET | yeşil |
| U20 | İsabet oranı tek başına yok | `accuracy.test.ts` "U20" | EVET | yeşil |
| U21 | Model kartı alanları; yasak sözcük yok | `accuracy.test.ts` "U21"; `stage5.test.ts` A5-5; `no_frontend_math.test.ts` "§4 yasak sözcükleri" | EVET | yeşil |
| U22 | Birincil hücre vurgusu | `accuracy.test.ts` "U22"; koşullu için "U51" | EVET | yeşil |
| U23 | Rejim uyarısı sabit metin | `accuracy.test.ts` "U23"; `results.test.ts`; `stage5.test.ts` A5-7 | EVET | yeşil |
| U24 | Fail-closed bütünlük (4 kural) | `stage4.rs::integrity_is_fail_closed` (11 ihlal); `accuracy.test.ts` "U24" (6 ihlalde panel yok) | EVET | yeşil; (c)(d) kırmızı |
| U25 | Uygulama skor hesaplamaz | `accuracy.test.ts` "U25" (her `model_value`/`rule_value` DOM'da); `no_frontend_math.test.ts` (TS işleç ve Rust fonksiyon taraması) | EVET | yeşil |
| U26 | Self-reported ve RETRO ayrı | `accuracy.test.ts` "U26" | EVET | yeşil |
| U27 | Kişisel kayıt yolu repo altına olamaz | `stage2.rs::scenario_path_guard`, `::config_reset_and_data_dir_guard`; `src/commands/scenario.rs::tests::export_all_scenarios_array_and_guard` | KISMEN: kanonik yol, dizin sembolik bağı, ayar reddi sınanıyor; askıda dosya bağı ve `..` sınanmıyor (B1) | yeşil; mutasyon (g) kırmızı |
| U28 | Kişisel kayıt işlemleri registry sha'sını değiştirmez | `tests/e2e.rs::freeze_flow` (U28 bölümü, `scen_before` karşılaştırılıyor :363) + betik adım 6 | EVET (aşama 5 düzeltmesi doğrulandı) | yeşil |
| U29 | Senaryo dosyası sicile düşse de skorlanamaz | `e2e_freeze_tmp_repo.sh` adım 4 (`active_records`) | EVET | yeşil |
| U30 | Dondur uçtan uca | `e2e.rs::freeze_flow` | KISMEN: 19 model, sha'lı dosya adı, parite 19/19, kopya yok, izlenmiyor, iptal, boş neden reddi sınanıyor; "iptal sonrası `active_records`" Python'la doğrudan sınanmıyor (B7) | yeşil |
| U31 | T geçmişse kırmızı; iptal Python'ca reddedilir | `e2e.rs::freeze_flow` (`t_level RED`, `FREEZE_CANCEL_AFTER_T`) | EVET | yeşil |
| U32 | Komut bloğu; uygulama git yazmaz | `stage2.rs::git_readonly_whitelist`; `stage3.rs::todo_block_shape`; `tests/build_embed.rs::git_calls_are_lock_free_and_read_only`, `::build_rs_runs_git_only_through_the_whitelist`; `freeze.test.ts` "U32" | EVET | yeşil; (f) kırmızı |
| U33 | Gömülü sha = INDEX; `_check_params`; eksik dosya derlemeyi kırar | `integrity.rs::embedded_integrity`; `build_embed.rs::missing_model_file_breaks_the_build` | EVET | yeşil |
| U34 | Ağ bağımlılığı yok | `tests/no_network.rs::no_network_deps`; `no_network.test.ts` | KISMEN (B9: Cargo.lock'ta mobil `reqwest`/`hyper`; platform grafiği temiz, CSP ve yetenekler sınanıyor) | yeşil |
| U35 | Şema uyumsuzluğu §2.5 | scores: `stage4.rs::unsupported_schema_version_closes_panel`, `accuracy.test.ts` "U35"; record: `stage3.rs::registry_view_synthetic`, `registry.test.ts`; scenario: `stage2.rs::u36_scenario_other_index`, `scenario.test.ts`; inputs: — | KISMEN (B6) | yeşil |
| U36 | Farklı INDEX ile senaryo sarı uyarı, çıktı aynen | `stage2.rs::u36_scenario_other_index`; `scenario.test.ts` | EVET | yeşil |
| U37 | Koşullu parite ≤ 1e-12, j = 0 bit-eşit | `golden.rs::conditional_parity` | EVET (6 model, Δ = 0) | yeşil |
| U38 | Resmi görünüm yalnız kayıttaki S | `stage3.rs::official_view_uses_record_only`, `::registry_view_real_repo_readonly`; `registry.test.ts` "U38" ve statik çağrı kümesi | EVET; "sayaç 0" statik çağrı kümesiyle (B2 gerçek sayaç önerir) | yeşil; (i) kırmızı |
| U39 | Beyan hiçbir skora/sicile girmez | `e2e_personal_isolation.sh` + `e2e.rs::personal_isolation`, `::observed_streak_user_only_in_scenario_module` | EVET | yeşil |
| U40 | Şerit ve tanımsızlık | `stage2.rs::u40_streak_and_undefined`; `ceiling.test.ts` | EVET | yeşil |
| U41 | Gömülü seri modeli bütünlüğü | `integrity.rs::survival_model_integrity` | EVET (sayı bozma ve INDEX'ten çıkarma → `SURVIVAL_MODEL_MISMATCH`) | yeşil |
| U42 | 19/19 parite, ≥ 450 satır, 8 kaynak sha | `golden.rs::golden_files_present`, `::golden_parity`, `::predict_sources_unchanged` | EVET | yeşil |
| U43 | Koşullu karışım paritesi | `golden.rs::conditional_path_parity` | EVET (40 taban × 13 + 10 vektör, 5 ihlal, 120 sapma bayrağı, j = 0 bit-eşit) | yeşil |
| U44 | Tavan yolu kapsaması | `coverage.rs::path_coverage` | EVET | yeşil |
| U45 | S bit-eşit kopya | `golden.rs::survival_passthrough_bit_equal` | EVET | yeşil |
| U46 | 16 eski altın dosya bayt-eşit | `tests/golden_unchanged.sh` (test.sh içinde) | EVET (`git show 0b67f5d` ile `cmp`) | yeşil |
| U47 | Decimal ek anlamı ve limit yolu tablosu | `dec_semantics.rs::dec_semantics_exact_context`, `::tick_and_bounds`, `::limit_path` | EVET (≥ 14 satır, metin birebir) | yeşil |
| U48 | Grup A/C render | `tests/path.test.ts` "U48"; fixture üreticileri `stage2.rs::u7_veyas_four_refusals`, `::path_post_break_insufficient_fixture` | EVET | yeşil |
| U49 | Getiri (koşullu) sekmesi; resmi görünüm kayıttan | `path.test.ts` "U49"; `stage3.rs::official_conditional_return_uses_record_only`; `registry.test.ts` statik; `e2e_personal_isolation.sh` | EVET (B2 sayaç notu) | yeşil |
| U50 | Kayıt paritesi 19 / eski 16 + 3 | `e2e.rs::freeze_flow`; `records_parity.rs` | EVET | yeşil |
| U51 | Faz 4 blokları; koşullu skor bloğu | `accuracy.test.ts` "U51"; `stage4.rs::integrity_is_fail_closed` (koşullu kurallar) | EVET | yeşil |
| U52 | Beyandan türetilmiş sayı arayüzde yok (6 madde) | `tests/u52_declaration.test.ts` (1–4 DOM taraması pozitif kontrollü, 6 tek seçenek, 2 şema, 5 ön uç statik); `stage2.rs::conditional_commands_take_no_declaration` (5 Rust); `stage3.rs::u52_record_fixtures` | KISMEN: 1–4, 6 ve Rust 5 EVET; ön uç 5 satır-yerel tarama (B2) | yeşil; (e1) kırmızı, (e2) yeşil |
| A5-1 | Bant tablosu sınıf/metin | `stage5.test.ts` A5-1 | EVET (10 hâl + repo göstergesi) | yeşil; (h) kırmızı |
| A5-2 | SENARYO yalnız senaryo ekranlarında | `stage5.test.ts` A5-2 | EVET | yeşil |
| A5-3 | Bant zaman kanıtı = sayfadaki dize | `stage5.test.ts` A5-3 | EVET (`proofLine` iki yerde) | yeşil |
| A5-4 | Çift ayraç yok; payda iki alt tablo | `stage5.test.ts` A5-4 (gerçek `scores.json`) | EVET | yeşil |
| A5-5 | Tek kart fonksiyonu, aynı alan sırası | `stage5.test.ts` A5-5 | EVET | yeşil |
| A5-6 | Tümünü dışa aktar | `scenario.rs::tests::export_all_scenarios_array_and_guard`; `e2e.rs::freeze_flow` | EVET | yeşil |
| A5-7 | Rejim metni veriyle eşleşir | `stage5.test.ts` A5-7 (hesap testte) | EVET | yeşil |

Ayrı hüküm, K1–K4 (`docs/prompts/FAZ3_FABLE_APP_SPEC.md` 142–145; şartname yazım görevinin kapıları):
- K1 (yalnız `docs/app/` altında yeni dosya): şartname commit'leri `52e1567`, `c89ff5a`, `cf90da2` yalnız `docs/app/` ve kendi görev dosyaları (`docs/prompts/FAZ3_FABLE_APP_SPEC*.md`) **[ÖLÇTÜM `git show --stat`]** → sağlandı.
- K2 (SPEC_SCORING §8'in her gösterim kuralı bir kabul testine bağlı): §8 satırları ↔ U13, U14, U16, U17, U18, U19, U20, U21; hepsi yukarıda EVET → sağlandı.
- K3 (parite yöntemi ve toleransı sayısal): §1.3 (1e-9), §5.6 U37 (1e-12), EK 2 §3.3 → sağlandı ve testlerde aynı sayılar (`common/mod.rs::TOL`, `TOL_CONDITIONAL`).
- K4 (resmi sicil repoda; kişisel kayıt giremez, testle gösterilir): U27/U28/U29 var, ama B1 yolu testsiz → **KISMEN**; B1 kapanınca sağlanır.

## Adım 3. Mutasyon denetimi [ÖLÇTÜM] (`ekler/mutasyon_ciktilari.txt`, sürücü `ekler/mutate.sh`)

Klon: `git clone --local` → `/tmp/borsai_app_audit/clone`; `node_modules` ve `.venv` asıl repodan sembolik bağ; `CARGO_TARGET_DIR=/tmp/borsai_app_audit/target`; klon derlemesi (`cargo test --workspace --no-run --offline`) **209 s**. Her mutasyon uygulandı → test koştu → `git checkout --` ile geri alındı; klon sonunda temiz.

| Mutasyon | Uygulanan değişiklik | Test | Kırmızı mı |
|---|---|---|---|
| (a) altın son hane | `v1_5_h99.jsonl` satır 0 `D5.p_up` `…0418 → …0411` (\|Δ\| = 6.7e-16) | `golden_parity` | **HAYIR** (tolerans 1e-9; bit-eşit 392 → 391 raporda) — B10 |
| (a2) aynı mutasyon, U1 bayt denetimi | aynı | `test_gen_golden.py::test_golden_files_are_reproducible` | EVET (`--check` bayt farkı) |
| (a3) 1e-8 basamağı | `D5.p_up += 1e-8` | `golden_parity` | EVET (`1 uyuşmazlık … \|Δ\| = 1.0e-8`) |
| (b1) kırpma sınırı | `horizons.rs` D3 üst `"0.331" → "0.332"` | `golden_parity` | EVET (288 uyuşmazlık: `D3.return`, `D3.price`, `RETURN_CLIPPED…used`) |
| (b2) ridge katsayısı okunuşu | `linear.rs::linear_term` `coef.iter()` → `coef.iter().rev()` | `golden_parity` | EVET (21 691 uyuşmazlık) |
| (c) `n7.json` n = 7 iken `live.cells` dolu | n35'ten 1 hücre kopyalandı | `cargo test --test stage4` / `vitest accuracy.test.ts` | EVET / EVET (Rust: `header_fields_and_index_mismatch`, `integrity_is_fail_closed`, `ui_view_fixtures`; vitest: U25 "her model_value DOM'da" — U16 kendisi yeşil kaldı, TS n < 10 dalı hücreyi zaten çizmez; asıl kapı Rust) |
| (d) `n35.json` "geçiyor" iken ci95 ∋ 0 | `base_train_mean` D1 `ci95 → [-0.009, 0.001]` | `stage4` / `vitest accuracy.test.ts` | EVET / EVET (Rust: `integrity_is_fail_closed`, `ui_view_fixtures`; vitest: U18 aralık metni — TS hükmü dosyadan basar, ihlali Rust yakalar) |
| (e1) beyanlı j api satırında | `screens/results.ts` `api.pathConditional(…, jOrT + store.view.declared.filter(…).length, …)` | `vitest u52_declaration.test.ts` | EVET (U52-5 "api çağrılarında beyan alanı yok") |
| (e2) beyanlı j bir satır önce | `screens/results.ts:81` `const j = (…) + store.view.declared.filter((x) => x).length` | `npm test` (tsc + 207 vitest) | **HAYIR** — B2 |
| (f) git beyaz listesine `commit` | `git.rs` `[&str; 5]` | `stage2 git_readonly_whitelist` | EVET |
| (g) senaryo yol bekçisi kaldırıldı | `scenario.rs` `scenarios_dir` ve `check_export_target` koşulu `false &&` | `stage2 scenario_path_guard` / `--lib export_all_scenarios_array_and_guard` / `e2e_freeze_tmp_repo.sh` | EVET / EVET / EVET (`e2e.rs:337` repo altına dışa aktarma reddi) |
| (h) bant: Sicil listesi `mode-scenario` | `shell.ts::registryBand` liste dalı | `vitest stage5.test.ts` | EVET (A5-1 ve A5-2) |
| (i) resmi görünümde `predict_all` | `screens/registry.ts::loadRecord` içine `api.predictAll(…)` | `vitest registry.test.ts` | EVET (iki statik test) |

## Adım 4. Bağımsız parite örneklemi [ÖLÇTÜM]

Üretici: `ekler/gen_sample.py` (kendi betiğim; `gen_golden.py` import edilmedi, kullanılmadı; seed 20260923; cwd = klon, `borsai` klondan yüklendi; yasak modül yüklenmedi). Karşılaştırıcı: `ekler/audit_sample.rs` klon crate'ine geçici test olarak kopyalandı, `common::run_row` + `cmp_expected` (§1.3 kuralları, tolerans 1e-9). Asıl `app/`'e yazılmadı.

- Girdi: **122** durum (70 rastgele geçerli + 46 uç + 6 f6 ucu) × **19 model** = **2318 satır**; altın dosyalardaki hiçbir (girdi, ek) çiftiyle çakışmadığı doğrulandı.
- Uçlar: f3 yok (2), PB alanı eksik/tümü eksik, fiyat aralığı (`-`, `–`), ID-A/ID-C ihlali, f3 eğitim aralığı dışı (alt/üst) ve winsor sınırı, f1 → ∞ / → 0 (kırpma), `1e400`, fiyat 0/negatif/`abc`/`12,5`/`inf`/`nan`/boş/`DATA_NOT_FOUND`, pay 0, sermaye 0, negatif ve tutarsız artırım, f4 = 0, pb4 > 0, üs biçimi, adım sınırları (`20`, `19.999`), HALF_UP snap (`25.295`), `2502.50`, 70 haneli fiyat (`Inexact`), `1e-400`, Unicode boşluk, alt çizgili rakam, FILTERED/UNFILTERED, 28 haneli f3, 40 haneli büyüklük, 1/3'lü `_pct`, f6 `abc`/`1e400`/`-inf`/`0`/ret öncelikleri.
- Sonuç (`ekler/parity_sample_report.json`): **0 uyuşmazlık**, maks |Δ| **1.137e-13**, bit-eşit 2315/2318 (bit-eşit olmayan tek satır `pb_v0`, `pb_ceiling_v0`, `pb_ceiling_path_v0`'da; pb1 `ln` yolu, §1.3 payı içinde). Satır türleri örneği (`ceiling_path_v0`): 93 tahmin, 12 `F3_MISSING`, 4 `INPUT_INCONSISTENT`, 4 `INPUT_NOT_NUMERIC`, 3 `INPUT_MISSING`, 2 `INPUT_NOT_POSITIVE`, 2 `DIVISION_BY_ZERO`, 1 `INPUT_NEGATIVE`, 1 `Inexact`; `v1_5_h99`: 31 satırda kırpma + 59'da eğitim aralığı dışı uyarısı.
- Resmi kayıtlar (`records_parity`, `BORSAI_REPO` = asıl repo, salt okuma): **7 kayıt × 16 model = 112 hücre**, 112 bit-eşit, maks |Δ| = 0; her kayıtta 3 Faz 4 modeli "kayıtta yok" (uyuşmazlık değil, EK 2 §3.7). Tam koşudaki e2e: yeni kayıt 19/19, |Δ|max = 0.

## Adım 5. Değişmezler

| Değişmez | Hüküm | Kanıt |
|---|---|---|
| Uygulama skor hesaplamaz | SAĞLANIYOR | `grep -rnE "bootstrap\|percentile\|quantile\|\bmean\(\|\.reduce\(\|\bsum\("` `src/` (tr.ts hariç) boş; Rust `src-tauri/src` için `fn (mean\|brier\|rps\|mae\|accuracy)` boş **[ÖLÇTÜM]**. Panelin her sayısı `scores_view` `doc`'undan; `scores.rs:159-175` belge olduğu gibi aktarılır; TS yalnız biçimlendirir (`render/format.ts`), satır sayar (G2). `card.ts` prospektif durum n < 10 → sabit metin, ≥ 10 → yalnız `verdict`. |
| İki terazi birleşmez; koşullu koşulsuzla birleşmez | SAĞLANIYOR | `render/accuracy.ts` `backtestSection`/`liveSection` ayrı `<section>`; `conditional()` j başına ayrı blok, kendi n'i; `scales-note`; vitest U14/U51 DOM ve regex; Rust `check_conditional` j başına. |
| "geçiyor" yalnız `verdict`; n < 10'da metrik/hüküm yok | SAĞLANIYOR | Kaynakta dize yalnız `tr.ts:956` (`VERDICT.pass`) ve `scores.rs:128` (denetim sabiti) **[ÖLÇTÜM]**; `accuracy.ts:303-306` n < 10 yalnız `rowTable`; Rust `LIVE_CELLS_BELOW_MIN_N`/`LIVE_DESCRIPTIVE_BELOW_MIN_N` fail-closed; kart `prospectiveText`. |
| Beyan kuralı (U52 ve genel ilke) | SAĞLANIYOR (render ve Rust); test açığı B2 | Rust: `ceiling.rs::streak_view_in`, `path.rs::path_conditional_value` imzasında beyan yok (`stage2.rs::conditional_commands_take_no_declaration`); `render/ceiling.ts:281-292` beyan resmi verinin önündeyse (`AHEAD`) koşullu bölüm ve getiri kartı yalnız "resmi kapanış bekleniyor"; çelişkide `CONFLICT` uyarısı; Sicil arz sayfası aynı render'ı kullanır (`render/registry.ts:172-175`); bant beyandan etkilenmez (`bandFor` yalnız ekran/hâl). Senaryo değeri resmi ekranda: `record_ceiling` yalnız kayıttan (U38); `path_conditional` RECORD kaynağı yalnız kayıt + gömülü hücreler + resmi kapanış; varsayımsal j etiketli; `approx_price`/`price_hint`/beklenen L görüntüleme türevi olarak etiketli (şartname §3b, EK 2 §4.1). Elle f6 yalnız senaryoda; resmi kayıtta f6'yı Python hesaplar (`freeze.py:225-228`). |
| Dondur: yalnız `freeze` yazar; commit/push yok | SAĞLANIYOR; B3 | Kayıt yazımı yalnız `python -m borsai.freeze` (`freeze.rs:214`); uygulamanın repo altına yazdığı yollar `registry/inputs/<T>[.PB].json`, `registry/source_docs/<T>/`, `app/parity/incidents/` (grep `fs::write` **[ÖLÇTÜM]**); `Command::new("git")` yalnız `git.rs` beyaz listeyle (`rev-parse`, `status`, `log`, `ls-files`), `build_embed.rs` (`rev-parse`, `status`); mutasyon (f) kırmızı; komut bloğu yalnız metin (U32). |
| Kişisel kayıt `registry/` altına düşemez | **KIRILABİLİR** (B1) | Sonda (`ekler/yol_bekcisi_sonda.txt`): büyük/küçük harf → ret (`canonicalize` disk yazımına çevirir); dizin sembolik bağı → ret; `..` var olan → ret, var olmayan ara dizinle → bekçi `false` ama OS `ENOENT` (yazılmadı); `app_data_dir` repo altına: `set_config` `DATA_DIR_INSIDE_REPO`, `scenarios_dir` sembolik/harf varyantlarında ret; **askıda dosya bağı → yazıldı**. `BORSAI_DATA_DIR` yalnız debug derlemede (`lib.rs:19-22`). |
| Resmi görünüm yalnız kayıttan; INDEX'ten eski kayıtta uydurma yok | SAĞLANIYOR | `registry.rs::record_ceiling_in` S'ler `models[].output.S`'ten, `path_models` boşsa "Faz 4 modelleri yok" (`16b` görüntüsü); `parity.rs` `missing_in_record` uyuşmazlık değil, olay dosyası yok; `path.rs` RECORD'da sha ≠ gömülü → hesap yok; mutasyon (i) kırmızı; `stage3.rs::official_view_uses_record_only` (0.5^k). |
| `scores.json` fail-closed; sürüm uyumsuzluğunda kısmi gösterim yok | SAĞLANIYOR | `scores.rs::scores_view_from` sürüm ≠ 1 → `doc: None`; ihlalde `doc: None`; TS `renderAccuracy` yalnız hata kutusu; mutasyon (c)(d) Rust kırmızı; `stage4.rs` 11 ihlal + gerçek dosya geçiyor. |
| Bant kuralı G1 | SAĞLANIYOR | `render/shell.ts::bandFor` tek saf fonksiyon; `main.ts` yalnız çağırır; A5-1/A5-2; mutasyon (h) kırmızı; görüntüler `15`, `16`, `22` mavi, `25`, `25c`, `26` gri, `04`, `11b` turuncu **[ÖLÇTÜM]**. |

## Adım 6. Ekran kontrolü [ÖLÇTÜM]

| Görüntü | Gördüğüm | Şartname / README ile |
|---|---|---|
| `04_sonuc_veyas_grup_a` | Turuncu SENARYO bandı; Grup A'da 19 sütun, `v1_5_h99`, `v1_6_h99`, `ceiling_hazard_v0`, `ceiling_path_v0` `RET · F3_MISSING`; `v1_5_market20_v0` `RET · MARKET20_XU100_CLOSE_MISSING`; tavan yolu sütunlarında medyan rozeti, %10–%90, p_up, S_h, `149.60 TL limit yolu`; PB `pb_ceiling_path_v0` D1 +%10.0, D3 +%3.8, D5 %0.0, D10 −%0.5 (EK 2 §7 beklentisiyle aynı) | Şartname (§3b, EK 2 §4.1) uyumlu; README satırı **uyuşmuyor** (B4) |
| `11b_kisisel_kayitlar_tumunu_disa_aktar` | Turuncu bant; "Tümü dışa aktarıldı: …/appdata/borsai_kisisel_kayitlar.json · 1 kayıt"; tablo 1 kayıt, gömülü kümeyle aynı | Uyumlu (G4) |
| `15_arz_sayfasi_netgl` | Mavi `RESMİ KAYIT · 20260922T121936Z_65a39d7392dd.json · kanıt dosyası var: 7cb49cf5d2f9 …`; künye (16 model, INDEX sha ilk 12, T = 2026-09-17); "git'te izleniyor · kaydı ekleyen commit …"; kaynak satırı params sha'larıyla; "bu kayıt Faz 4 modellerini içermiyor"; şerit D1–D3 tavan | Uyumlu (§3e, §3g, G1, EK 2 §4.4) |
| `16_arz_sayfasi_netgl_kosullu` | j = 3 (gözlenen), P(L ≥ k \| L ≥ 3) eğrisi 6 model + her zaman tavan, tablo k = 4..10 | Uyumlu (U38) |
| `22_dondur_adim6_kayit_ve_parite` | Bant `RESMİ KAYIT · hazırlanıyor · Dondur gerçek repoya yazar`, repo göstergesi geçici klon; "Kayıt yazıldı: registry/records/SNTC3/…"; 19 model; `parite: 19/19 desteklenen model, \|Δ\|max = 0`; komut bloğu `git add … / git commit -m … -- <aynı yollar> / git push / push_proof $(git rev-parse HEAD)`; "Uygulama bu komutları çalıştırmaz" | Uyumlu (U30/U32/U50, STAGE3 değişen 4) |
| `25_dogruluk_gercek_dosya` | Gri `DOĞRULUK · scores.json'dan salt okuma…`; `v1_5_h99` özeti "n = 6; atlanan = 0"; kart (19 varyant, birincil D5 MAE `base_train_median`, "canlı n = 6: hüküm yok"); backtest tablosu hükümler `verdict`'ten (geçemiyor/geçiyor/ayırt edilemiyor), birincil satır çerçeveli | Uyumlu (§3d, G3) |
| `25c_dogruluk_retro_atlanan` | RETRO 3 model × 7 arz; "FROZEN olmayan payda satırları (19)": SKIPPED (0) "yok", OUT_OF_SCOPE (19) tablo, altta atlanan notu | Uyumlu (G2) |
| `26_dogruluk_n7_satir_tablosu` | Canlı n = 7: yalnız satır tablosu (8 satır: 7 skorlanan + 1 RET), metrik/hüküm/renk yok, "n < 10: metrik hesaplanmaz"; geçersiz kullanım katlanır, iptal edilen kayıt, "henüz koşullu skor yok" | Uyumlu (U16) |

## Adım 7. identifier önerisi (HANDOFF açık karar 3)

**Öneri: `tr.borsai.app` kalsın.** [ÇIKARIM; kanıtlar ÖLÇTÜM]

- Uyarının tam metni (`@tauri-apps/cli` 2.11.5 ikilisinden `strings`): `The bundle identifier "<id>" set in \`tauri.conf.json > identifier\` ends with \`.app\`. This is not recommended because it conflicts with the application bundle extension on macOS.` Uyarı bir tavsiyedir; derlemeyi durdurmaz.
- Gerçek bir sorun yaratıp yaratmadığı: `/Applications/BorsAi.app` `CFBundleIdentifier = tr.borsai.app`, ad-hoc imzalı (`codesign -dv`), LaunchServices'e kayıtlı (`lsregister -dump`); `~/Library/WebKit/tr.borsai.app` ve `~/Library/Caches/tr.borsai.app` dizinleri var (yalnız varlıkları bakıldı) → uygulama bu kimlikle açılmış ve WKWebView çalışmış; `app/docs/screens/*.png` aynı kimlikli geliştirme derlemesinden. Kimliğin macOS'ta dokunduğu yerler: Info.plist kimliği, `app_data_dir` yolu (`~/Library/Application Support/tr.borsai.app`), WebKit/Caches dizin adları. Hiçbirinde `.app` soneki bir çakışma üretmedi; uyarı tauri-bundler'ın `.app` paket uzantısı adlandırmasıyla ilgili kozmetik bir tavsiyedir. Dağıtım (notarization, App Store) gündeme gelirse yeniden değerlendirilir; kişisel kullanımda değiştirmenin faydası yok.
- Değişirse taşıma tarifi: `~/Library/Application Support/tr.borsai.app` **bugün yok** (ayar ya da kişisel kayıt yazılmamış) → taşınacak dosya sıfır. İleride varsa: uygulamayı kapat → `ditto "~/Library/Application Support/tr.borsai.app" "~/Library/Application Support/<yeni-id>"` (yalnız `config.json` ve `scenarios/*.json`; kişisel kayıt dosyaları kimlik taşımaz, olduğu gibi geçerli kalır) → `tauri.conf.json` `identifier` değiştir → `npm run tauri build -- --bundles app` → `/Applications`'a kopyala → eski `Application Support`, `WebKit`, `Caches` dizinlerini sil. Resmi sicil repoda olduğundan (uygulama verisinde kopya yok) taşımadan etkilenmez; `set_config` `DATA_DIR_INSIDE_REPO` bekçisi yeni yolda aynen çalışır.

## Ekler (`docs/fable_app_audit/ekler/`, toplam ≈ 80 KB)

- `test_runs.txt` — tam koşu ölçümleri (sayılar, süreler, son satırlar, sha eşitliği).
- `mutasyon_ciktilari.txt` — 11 mutasyonun komut çıktıları; `mutate.sh` — sürücü.
- `parity_report_full_run.json` — tam koşudaki `target/parity_report.json`; `golden_coverage_path.json`.
- `parity_sample_report.json`, `gen_sample.py`, `audit_sample.rs` — bağımsız örneklem raporu, üretici ve karşılaştırıcı.
- `audit_probe.rs`, `yol_bekcisi_sonda.txt` — yol bekçisi sondaları ve çıktısı.

Geçici işler `/tmp/borsai_app_audit/` altında (klon, ayrı `target`, örneklem 6.6 MB, mutasyon günlükleri); asıl repoda `app/`, `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `tests/` değişmedi; kişinin gerçek uygulama verisine yazılmadı ve oradaki dosyalar açılmadı.

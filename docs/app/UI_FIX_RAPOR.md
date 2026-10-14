# BORSAI_FAZ9_UI_FIX_20261004 — sade görünüm düzeltmeleri (sunum öncesi): teslim raporu

Görev `docs/prompts/FAZ9_UI_FIX.md`. Proje sahibinin bulduğu altı sorun (2026-10-04) K-FIX-1…6 ile kapatıldı; sınırlar K-FIX-7.
Önceden onaylı pin K-PIN-FIX (proje sahibi başlatma cümlesinde onayladı). Push, tag, amend yok. Şartnameden sapma yok →
`docs/SPEC_DEVIATIONS.md`'ye "P" bölümü eklenmedi.

## 0. Kısa sonuç

- **Analiz'e dönüş (K-FIX-1):** üst bardaki "Analiz" sekmesi ve arz sayfasındaki "Tüm arzlar" her zaman takipteki arzların
  tablosunu açar (kod, şirket, ilk işlem günü; en yeni üstte). Arz açıkken yol "Analiz › NETGL" ve bir arz değiştirici var.
- **Sicil künyesi (K-FIX-2):** satır ya da "Aç" künyeyi seçilen arzla yeniden çizer; künye görünür alanın dışındaysa sayfa
  yumuşakça künyeye kayar (`prefers-reduced-motion` → anında). 1200 px pencerede künye tablonun yanında kalıyor (görüntü `v2_07b`).
- **Hesaplayıcı (K-FIX-3):** "Yarın da tavan"ın yanında gri "Geçmiş arzlarda" (basit kural `base_km_expanding`, aynı kaydın /
  koşunun S'i; S_{j+1} / S_j ve "66 arzdan 53 tanesi" sayımı Rust'ta) ve modelin gün grupları notu (model dosyasındaki
  `day_groups`'tan; sabit metin yok). NETGL j = 3 ve j = 6: model %67 ikisinde de; geçmiş %80 ve %82.
- **İşlem sayısı çubukları (K-FIX-4):** koridorun altında D1–D10; sayı `trade_count_raw` aynen (binlik ayırıcıyla), yükseklik
  Rust'ın 0–1 oranından. NETGL D1 17.885, D2 28.445; en büyük gün D9 241.603.
- **Performans sayımları (K-FIX-5):** "3 satırda model daha iyi · 1 satırda fark net değil · 2 satır hükümsüz"; `PerfCounts`
  beş ayrı alan (pass / undecided / fail / other / no_verdict), toplanmaz.
- **Pencere (K-FIX-6):** 1440 × 900 ortada; çalışma alanı küçükse büyütülmüş; en küçük 1024 × 680; bu genişlikte hiçbir sade
  ekranda yatay kaydırma yok (görüntü koşusunda her ekran için denetlenir).
- Değişmeyenler: `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `legacy/`, `docs/specs*`, `CLAUDE.md`,
  `experiments/log.jsonl`, `app/parity/`, `app/src/screens/*`, `app/src/render/*` (yalnız `svg.ts` ve `format.ts` eklemeleri),
  ayrıntılı görünüm, eski `app/docs/screens/*.png`.

## 1. Commit'ler (push yok)

| Commit | Hash | Konu |
|---|---|---|
| A | `317304a` | `BORSAI_FAZ9_UI_FIX_A: analysis back nav, registry card scroll, calculator history row and day-group note, trade-count bars, perf counts split, window size, K-PIN-FIX test_5c` |
| C | `b2a861b` | `BORSAI_FAZ9_UI_FIX_C: screenshots and report` |
| R | (son koşu sayılarını ekleyen commit) | `BORSAI_FAZ9_UI_FIX_R: final test runs` |

**TABAN** `b045e71` = origin/main (`git diff --stat b045e71 HEAD` boş); ağaçta yalnız izinli izlenmeyenler
(`docs/prompts/FAZ9_UI_FIX.md`, `docs/prompts/TUFE_2026_09.md`, `docs/prompts/FAZ10_FABLE_STREAK_SPEC.md`; son ikisine dokunulmadı).

## 2. Adım 1: K-PIN-FIX (a) provası (geçici `git clone --local` klonu)

Klon scratch dizininde; `.venv` ve `app/node_modules` bağları klonun `.git/info/exclude`'unda. Yeni `_app_ui_commits_only`
(APP_TASKS listesi) klona kondu; yalnız `test_5c` koşuldu:

| Durum | Sonuç | Kırmızıysa iddia |
|---|---|---|
| (i) temiz | **yeşil** | — |
| (ii) commit'siz `app/README.md` değişikliği | **yeşil** | — |
| (iii) `BORSAI_FAZ9_UI_FIX_A:` konulu `app/` commit'i | **yeşil** | — |
| (iv) `BORSAI_PROVA_X:` konulu `app/` commit'i | **kırmızı** | konu öneki (`startswith(prefixes)`) |
| (v) commit'siz `app/parity/README.md` değişikliği | **kırmızı** | `git diff --quiet 7d78d43 -- app/parity` → "app/parity" |
| (vi) `BORSAI_FAZ9_UI_FIX_C:` commit'inden sonra commit'siz `app/` | **kırmızı** | `git status --porcelain -- app` → " M app/README.md" |
| (vi-b) C sonrası temiz | **yeşil** | — |

Not: ilk koşuda (iv) için kullanılan `git reset --hard` klondaki commit'siz test dosyasını da geri aldığı için (v)–(vi) eski
fonksiyonla koşmuştu; klon A commit'ine döndürülüp yama yeniden uygulandı ve (iii)–(vi-b) yukarıdaki gibi yeniden ölçüldü.
Asıl repoda bu adımda commit yok.

## 3. Madde madde

| # | Ne yapıldı | Dosya / komut | Görüntü |
|---|---|---|---|
| K-FIX-1 | Üst bardaki "Analiz" sekmesi ve "Tüm arzlar" (`data-go="analiz"`) kabukta `sade.ticker`'ı boşaltır; arz yalnız `openAnalysis` ile açılır (arama, Monitör, Sicil, liste satırı, değiştirici). Liste `renderAnalizPick(rows)`: tablo (kod + şirket, ilk işlem günü, "Aç"), `monitor_view` satırlarından, en yeni D1 üstte (eşitlikte kod sırası). Arz açıkken yol "Analiz › T", "Tüm arzlar" düğmesi ve `<select data-role="arz-switch">` (Monitör arzları). Analiz ekranı arz yoluyla açılsa da `monitor_view`'ı yükler (değiştirici için). | `app/src/sade/app.ts`, `screens/analiz.ts`, `render/analiz.ts` (`crumb`, `renderAnalizPick`, `PickRow`), `tr.ts` `SADE.analiz` | `v2_05a_analiz_listesi`, `v2_05_analiz_netgl`, `v2_05f_analiz_bkrgy_degistirici` |
| K-FIX-2 | `sicil-select` (satır ve "Aç") → `loadTicker` → `paint` → `revealCard`: künye `.sicil-card` görünür alanın tamamen içindeyse dokunmaz; değilse `scrollIntoView({block:"start", behavior})`, `prefers-reduced-motion` → `auto`; CSS `scroll-margin-top: 72px` üst barı açıkta bırakır. Tablo `.s-scroll` sarmalına alındı (dar pencerede panel içinde kayar); 1200 px'te künye tablonun yanında kaldı. | `app/src/sade/screens/sicil.ts` (`revealCard`), `render/sicil.ts`, `sade.css` | `v2_07b_sicil_1200_bkrgy` (1200 × 800 pencere, BKRGY seçili), `v2_07_sicil` |
| K-FIX-3 | Rust: `CeilingDisplay.calc: Option<CalcView>` (`skip_serializing_if`; saf `ceiling_display_value`'da yok, eski sözleşme aynen). `calc_view_value(rows, j, models)`: `history` (kural `base_km_expanding` satırının `cond.S_cond[j]` = S_{j+1}/S_j; `s_cond` eğri için; `training.n` model dosyasından; S_j × n ve S_{j+1} × n 1e-9 içinde tam sayıysa `n_at_j`, `n_next`, değilse null) ve `day_groups` (display satırlarından dosyasında `day_groups` olan modeller, anahtar sırasıyla). `attach_calc` komut katmanında: `ceiling_display` (artık `state` alır) ve `record_ceiling`. Ön uç: "Geçmiş arzlarda (basit kural, eğitimdeki tüm arzlar)" gri (`.rule-text`), sayım cümlesi yalnız Rust verdiyse; not yalnız öne çıkan modelin gün grubu varsa, metin gruplardan ("1. gün · 2–3. gün · 4–10. gün", "3. günden sonra" = sondan ikinci grubun son günü); eğride kuralın koşullu eğrisi ince gri kesikli (`calcCurve`, `svg.ts` ekleme). Altın yalnız model. | `app/src-tauri/src/commands/ceiling.rs` (`CalcView`, `CalcHistory`, `DayGroups`, `calc_view_value`, `attach_calc`, `CALC_RULE_ID`, `CALC_COUNT_TOL`), `registry.rs` (`record_ceiling`), `app/src/types.ts` (ekleme), `sade/render/calc.ts`, `render/sonuc.ts`, `render/analiz.ts`, `render/svg.ts` (`calcCurve`), `tr.ts` `SADE.calc` | `v2_05b_analiz_hesaplayici_gozlenen_j3` (model %67, geçmiş %80, "3 gün tavan yapan 66 arzdan 53 tanesi…"), `v2_05b2_analiz_hesaplayici_j6` (model %67, geçmiş %82, "33 arzdan 27"), `v2_04_sonuc_j3` (senaryo) |
| K-FIX-4 | `DayRow.trade_count_raw` (metin aynen, yalnız `status = OK`) ve `trade_count_rel` (gün / on günün en büyüğü; sütun ya da sayı yoksa null). Koridorun altında "İşlem sayısı" satırı: her gün `tradeBar(rel)` (`svg.ts` piksel) + `countTr(raw)` (`format.ts`, tr-TR binlik ayırıcı); değer yoksa çubuk yok, tire. `docs/design/ui_v2/README.md` §3 satırı düzeltildi. | `app/src-tauri/src/commands/sade.rs` (`DayRow`, `read_days`), `sade/types.ts`, `render/analiz.ts` (`corridor`), `render/svg.ts` (`tradeBar`), `render/format.ts` (`countTr`), `sade.css` | `v2_05e_analiz_islem_sayisi` (17.885, 28.445, …, 241.603 tam yükseklik) |
| K-FIX-5 | `PerfCounts { n_rows, n_pass, n_undecided, n_fail, n_other, n_no_verdict }` (`VERDICT_UNDECIDED`, `VERDICT_FAIL` sabitleri); `SADE.perf.stripRowsSub(counts)` parçaları " · " ile birleştirir, sıfır olan parça yazılmaz ("x satırda kural daha iyi", "x satır yetersiz örnek" ayrı). Hüküm hücresi yine dosyadaki `verdict` (U19). Bugün: 6 / 3 / 1 / 0 / 0 / 2. | `sade.rs` (`PerfCounts`, `perf_view_value`), `sade/types.ts` (`PerfCounts`), `render/perf.ts`, `tr.ts` `SADE.perf.stripRowsSub` | `v2_06_model_performansi` |
| K-FIX-6 | `tauri.conf.json`: 1440 × 900, `center: true`, min 1024 × 680. `lib.rs` `setup`: `current_monitor().work_area()` mantıksal boyutu `DEFAULT_WINDOW`'dan küçükse `maximize()`. Sabitler `DEFAULT_WINDOW`, `MIN_WINDOW` cargo testiyle conf'a bağlı. Görüntü koşusu için `dev_window_size(w, h)` (yalnız `--features snapshot`); demo 1024 × 680'de Monitör, Analiz (liste ve NETGL), Model performansı, Sicil, Kayıtlarım, Giriş ekranlarında `scrollWidth ≤ clientWidth` ister, aşarsa koşu hata verir (`zz_demo_error`). Bu koşuda aşan ekran yok. | `app/src-tauri/tauri.conf.json`, `src/lib.rs`, `src/commands/snapshot.rs`, `app/src/dev/demo.ts`, `sade.css` (Sicil/pick tablosu `.s-scroll`) | `v2_13_analiz_1024` (1024 × 680), bütün v2 görüntüleri 1440 × 900 pencerede |

## 4. `SADE` içinde değişen dizeler (eski → yeni)

| Anahtar | Eski | Yeni |
|---|---|---|
| `analiz.pickNote` | "Monitörden ya da kod aramasından bir arz seçin." | "Takipteki arzlar, en yeni ilk işlem günü üstte. Bir satıra tıkla ya da üst bardan kod ara." |
| `perf.stripRowsSub` | `(p, o, nv) => "${p} satırda model daha iyi, ${o} satırda değil, ${nv} satır hükümsüz"` | `(counts) =>` "x satırda model daha iyi" · "x satırda fark net değil" · "x satırda kural daha iyi" · "x satır hükümsüz" · "x satır yetersiz örnek" (" · " ile; sıfır olan parça yazılmaz) |

Yeni dizeler (ekleme): `analiz.allIpos` "Tüm arzlar", `switchIpo` "Başka arz", `colIpo` "Arz", `colD1` "İlk işlem günü", `open` "Aç",
`tradeTitle` "İşlem sayısı", `tradeSub`; `calc.historyLabel` "Geçmiş arzlarda", `historySub` "basit kural, eğitimdeki tüm arzlar",
`historyCount(j, nAt, nNext, d)` ("j gün tavan yapan nAt arzdan nNext tanesi d. gün de tavan oldu." / j = 0: "Eğitimdeki nAt arzdan
nNext tanesi ilk gün tavan oldu."), `groupWord`, `groupOne`, `groupRange`, `groupsNote(n, groups, last)` (görevdeki önerilen
metin), `legendRule` "basit kural, seçilen güne koşullu". `SADE` dışında `tr.ts`'te silinen ya da değişen satır yok
(`git diff b045e71 -U0 -- app/src/i18n/tr.ts | grep '^-'`: yalnız `pickNote` ve `stripRowsSub`).

## 5. Değişen test fonksiyonları

| Test | K-PIN-FIX | Gerekçe (tek satır) |
|---|---|---|
| `tests/test_faz8_model.py::_app_ui_commits_only` (+ sabit `APP_TASKS`; `APP_UI_PREFIX`, `APP_UI_LAST_APP_SUBJECT` kalktı; `test_5c` içindeki çağrı yorumu) | (a) | görev listesi: app/'a dokunan her commit listedeki öneklerden biriyle başlar; commit'siz app/ yalnız son görevin kapanış konusu log'da yokken; app/parity aynen |
| `src-tauri/tests/sade.rs::perf_view_real_files` | (b) | `n_other_verdict` → `(n_rows, n_pass, n_undecided, n_fail, n_other, n_no_verdict) = (6, 3, 1, 0, 0, 2)` ve toplam = n_rows |
| `sade.rs::calculator_netgl_expected_numbers` | (b) | kayıt ve senaryo display'ine `attach_calc` (fixture'lar komut çıktısıyla aynı); iddialar aynen |
| `sade.rs::arz_view_real_repo` | (b) | işlem sayısı metinleri ve oranları eklendi (D9 = 1, D1 = 17885 / 241603) |
| yeni `sade.rs::calculator_history_and_day_groups_expected_numbers` | — | görevdeki beklenen tablo: NETGL/CITAS "yarın da tavan" yüzdeleri j = 0..9, geçmiş oranları ±5e-5 ve yüzdeleri, S × 99 sayımları, day_groups; kural yoksa / tam sayı değilse / S_j = 0 dalları; saf display'de `calc` yok |
| yeni `sade.rs::read_days_trade_counts_optional`, `window_config_k_fix_6` | — | sütun yoksa null, OK olmayan gün okunmaz; conf = lib sabitleri |
| `app/tests/sade_render.test.ts`: "senaryo j = 0…", "senaryo j = 3…", "resmi görünüm…", "tanımsız j…" | (b) | `CalcVM.calc` parametresi; j = 0 geçmiş %82 (99/81), j = 3 %80 (66/53), kural eğrisi ve açıklaması |
| `sade_render.test.ts`: Analiz `vm()` (`tickers`), "arz seçilmemişken…" | (b) | liste tablo oldu (kod, şirket, D1; en yeni üstte; boş not) |
| yeni `sade_render.test.ts`: "j = 6…", "ek yoksa…", "yol 'Analiz › NETGL'…", "işlem sayısı…", "hesaplayıcı resmi görünümde geçmiş…", "sayım cümlesi…" | — | K-FIX-1, 3, 4, 5 render iddiaları |
| yeni `sade_svg_format.test.ts`: "işlem sayısı binlik ayırıcıyla", "işlem sayısı çubuğu…", "hesaplayıcı eğrisi + kural eğrisi…" | — | `countTr`, `tradeBar`, `calcCurve` yalnız biçim / koordinat |
| `sade_invoke.test.ts`: `beforeEach` sıfırlaması (sicil alanları); yeni "Analiz sekmesi her zaman listeyi açar…", "Sicil: 'Aç'…" | (b) | gerçek tıklamalarla liste / yol / değiştirici ve künye kayması (scrollIntoView sahte; reduced-motion dalı; görünürken kaymaz) |
| fixture'lar `app/tests/fixtures/ui/sade_*.json` | (b) | `BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test sade` ile gerçek dosyalardan yeniden üretildi: `sade_arz_netgl`, `sade_monitor` (DayRow alanları), `sade_perf` (sayımlar), `sade_ceiling_netgl_j0/j3`, `sade_record_ceiling_netgl_j0/j3` (`calc`), yeni `sade_record_ceiling_netgl_j6` |

U13–U26, U34, parite (`app/parity/`), `golden_unchanged` ve `no_frontend_math` değişmedi (yeşil). Bekçiler ayrılmadı: `test_14b`
yalnız commit öncesi ara koşudan ayrıldı; commit A'dan hemen sonra `test_5c` ve `test_14b` tek başına yeşil (2 passed).

## 6. Test sayıları

| Aşama | pytest | `test.sh` | `gen_golden --check` |
|---|---|---|---|
| Taban (`b045e71`), paralel `-n 6 --dist loadgroup` | **952 passed** (9:49) | yeşil: cargo 161 / 0, vitest 365 (24 dosya), parity 8, golden_unchanged yeşil | 35 / 0 |
| A öncesi, paralel, `test_14b` ayrıldı | **951 passed**, 1 deselected (10:44) | yeşil: cargo **164** (161 + 3 yeni), vitest **376** (365 + 11 yeni), parity 8, golden yeşil | 35 / 0 |
| A sonrası (`317304a`, temiz ağaç): `test_5c` + `test_14b` tek başına | 2 passed | — | — |
| Son kabul (HEAD `b2a861b` = C, temiz ağaç), **sıralı, ayrılan yok** | **952 passed** (18:40; derleme ve test.sh ile eşzamanlı koştu) | yeşil: cargo **164 / 0** (161 + 3 yeni), vitest **376** (24 dosya; 365 + 11 yeni), parity **8**, golden_unchanged yeşil | **35 / 0** |

Beklenen sayılar cargo testlerinde birebir (oranlar ±5e-5, yüzdeler tam): `calculator_history_and_day_groups_expected_numbers`,
`perf_view_real_files`, `arz_view_real_repo`, `calculator_netgl_expected_numbers`.

## 7. `.app` derlemesi

- Komut: `source app/scripts/env.sh && cd app && npm run tauri build -- --bundles app` (HEAD `b2a861b` = C, temiz ağaç; derleme
  izlenen hiçbir dosyayı değiştirmedi: `git status --porcelain` yalnız izinli izlenmeyenler).
- Çıktı: `app/src-tauri/target/release/bundle/macos/BorsAi.app` (8.4 MB; ad-hoc imza, noter onayı yok).
- `Contents/MacOS/borsai-app` sha256: `81a7d329e9661917b07272b4bfcaf92a32abf44ca6ff64600d828da60eef6860`.
- Paketin bütün dosyalarının sha listesinin sha256'sı: `194278b0b6e0620d6b8d23011fc1acc9979686472960b5cda959e00cc207ff24`.
- Ön uç paketinde 18 yerel woff2 (IBM Plex); CSS'te uzak URL yok (vitest).
- Kurulum proje sahibinde: `ditto app/src-tauri/target/release/bundle/macos/BorsAi.app /Applications/BorsAi.app`.

## 8. Hijyen taraması

Yeni ve değişen her dosya (`git diff --name-only b045e71` + izlenmeyenler; görev dosyaları hariç) `registry/oot/cohort_pre_h99.csv`'deki
64 SEALED koduna karşı büyük/küçük harf duyarlı ve sözcük sınırıyla, ayrıca bülten adı kalıbına (`th[bm]` + 8 hane) karşı tarandı
(kodlar yazdırılmadan): A öncesi 36 metin dosyası, **0 bulgu**; C öncesi (görüntüler ve rapor dahil) 64 dosya (38 metin, 26 görüntü ikili), **0 bulgu**. Yeni Rust çıktıları (`calc`, `trade_count_*`)
bülten adı ve eğitim arz listesi taşımaz (cargo: `no_bulletin_names`, `calc` metninde "tickers" yok).

## 10. Görüntüler (`app/docs/screens/v2/`, gerçek uygulama, `bash app/scripts/screens_v2.sh`)

Gerçek uygulama (Tauri, `--features snapshot`), asıl repo salt okunur (betik sonunda `registry/` ve `data/` sha listeleri
öncesiyle aynı); uygulama verisi geçici dizinde. Pencere 1440 × 900 (K-FIX-6; görüntüler 1440 px), Sicil görüntüsü 1200 × 800,
`v2_13` 1024 × 680. Demo koşusu 1024 × 680'de yatay kaydırma denetimini geçti (`zz_demo_error.png` yok). Eski
`app/docs/screens/*.png` değişmedi; eski v2 görüntüleri yeni pencere boyutuyla yenilendi.

| Dosya | İçerik (bu görevle ilgili) |
|---|---|
| `v2_05a_analiz_listesi.png` (yeni) | Analiz sekmesi: takipteki arzların tablosu (kod, şirket, ilk işlem günü; en yeni üstte) |
| `v2_05_analiz_netgl.png` | Analiz NETGL: yol "Analiz › NETGL", "Tüm arzlar", "Başka arz" değiştiricisi |
| `v2_05e_analiz_islem_sayisi.png` (yeni) | Fiyat koridorunun altında işlem sayısı çubukları (17.885, 28.445, …, 241.603) |
| `v2_05b_analiz_hesaplayici_gozlenen_j3.png` | Hesaplayıcı j = 3: model %67, geçmiş arzlarda %80 (66 arzdan 53), gün grupları notu, kural eğrisi |
| `v2_05b2_analiz_hesaplayici_j6.png` (yeni) | Hesaplayıcı j = 6: model %67, geçmiş arzlarda %82 (33 arzdan 27) |
| `v2_05f_analiz_bkrgy_degistirici.png` (yeni) | Değiştiriciyle BKRGY açıldı (yol "Analiz › BKRGY") |
| `v2_04_sonuc_j3.png` | Tahmin sonucu (senaryo) j = 3: aynı satır ve not |
| `v2_06_model_performansi.png` | "3 satırda model daha iyi · 1 satırda fark net değil · 2 satır hükümsüz" |
| `v2_07b_sicil_1200_bkrgy.png` (yeni) | Sicil, 1200 × 800 pencere, BKRGY seçili; künye görünür alanda (tablonun yanında) |
| `v2_13_analiz_1024.png` (yeni) | Analiz NETGL 1024 × 680: yatay kaydırma yok (üst bar iki satıra kırılır) |
| öbür `v2_*.png` | FAZ9_APP_UI görüntüleri, 1440 × 900 pencereyle yenilendi (içerik aynı) |

## 9. Bulduğum ama yapmadığım şeyler (kapsam dışı)

- 1024 px genişlikte üst bar iki satıra kırılıyor ("Yeni arz gir" ve dişli ikinci satırda); yatay kaydırma yok. Daha sıkı bir üst
  bar yerleşimi ayrı iş.
- j ≥ 5'te "En az 5 gün sürme" okuması tire gösterir (k ≤ j koşullu değer tanımsız; var olan davranış).
- Gün gün değişen tavan modeli (day_groups yerine) ayrı görev (görev metni).
- Sicil künyesi 1200 px'te artık tablonun yanında (tablo `.s-scroll` sarmalında); kayma yolu yalnız daha dar pencerelerde ve
  künyenin alta indiği durumlarda devreye girer (vitest'te sahte yerleşimle sınandı).
- `ceiling_display` komutu `state` almaya başladı (gömülü model dosyaları için); ayrıntılı görünümün çağrısı ve argümanları
  değişmedi, `calc` alanını yok sayar.

## Kabul kapısı

| Koşul | Durum |
|---|---|
| Son sıralı pytest yeşil, ayrılan yok | ✓ 952 passed |
| `test.sh` yeşil | ✓ cargo 164, vitest 376, parity 8, golden_unchanged |
| `gen_golden --check` 35/0 | ✓ |
| `git diff b045e71 -- app/src/screens app/src/render`: yalnız `render/svg.ts` ve `render/format.ts` eklemeleri, silinen satır yok | ✓ (2 dosya, 64 ekleme, 0 silme) |
| `tr.ts`'te silinen ya da değişen satırların hepsi `SADE` içinde | ✓ (`analiz.pickNote`, `perf.stripRowsSub`) |
| `git diff b045e71 --stat -- borsai models registry data scores legacy docs/specs* CLAUDE.md experiments app/parity` boş | ✓ |
| Beklenen sayılar cargo testlerinde birebir (oranlar ±5e-5, yüzdeler tam) | ✓ `calculator_history_and_day_groups_expected_numbers`, `perf_view_real_files`, `arz_view_real_repo` |
| Altı maddenin her biri görüntüde | ✓ §10 |
| Hijyen temiz | ✓ 0 bulgu |

# BORSAI_FAZ9_APP_UI_20261003 — sade görünüm: teslim raporu

Görev `docs/prompts/FAZ9_APP_UI.md` (Opus 5.5). Onaylı tasarım `docs/design/ui_v2/`; öğe ↔ veri haritası `docs/app/UI_V2_HARITA.md`
(kod yazılmadan önce, commit D); sapmalar `docs/SPEC_DEVIATIONS.md` §O (O1–O19). Push, tag, amend yok.

## 0. Kısa sonuç

- Uygulamanın varsayılan görünümü artık **sade görünüm**dür. Eski arayüz **Ayrıntılı görünüm** adıyla kodu ve testleriyle aynen durur.
  Seçim Ayarlar'da; geçiş iki yönde çalışır (`ui_view` config alanı, geriye uyumlu).
- 12 panonun uygulama karşılıkları yapıldı (Stil ve Palet sade.css'in belirteçleri): Monitör, Yeni arz girişi, Tahmin sonucu, Analiz,
  Model performansı, Sicil, Kayıtlarım, Ayarlar ve Hakkında, sihirbaz kabuğu (dondur ve D1 sonrası). K-UI-15 sırasında yetişmeyen ekran yok.
- Proje sahibinin aradığı **"Seri j gün sürdüyse yarın ne olur?"** hesaplayıcısı hem Tahmin sonucunda (senaryo) hem Analiz'de (resmi
  görünüm, bültende gözlenen j ve "Gözlenene dön") görünür. Yalnız var olan Rust komutları; yeni hesap yok. NETGL'de görevdeki beklenen
  sayıları verir (cargo testi, vitest ve görüntü `v2_04`, `v2_05b`).
- Bütün sayılar Rust'tan. Yeni salt okuma komutları: `monitor_view`, `arz_view`, `break_view`, `perf_view`, `headline_gate`
  (+ `set_ui_view`). Ana ekran kapısı veri-güdümlü; bugünkü dosyalarla K-UI-4 beklentisiyle birebir (§5).
- Değişmeyenler: `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `legacy/`, `docs/specs*`, `CLAUDE.md`, `experiments/log.jsonl`,
  `app/src/screens/*`, `app/src/render/*` (yalnız `svg.ts` ve `format.ts`'e ekleme), `app/parity/`, eski `app/docs/screens/*.png`.

## 1. Commit'ler (push yok)

| Commit | Hash | Konu |
|---|---|---|
| D | `b48b29aea9f62f5d68eb602ac1f0d47dd6235d1e` | `BORSAI_FAZ9_APP_UI_D: design assets, task file, mapping` |
| A | `62cc4e3c9b8bbbd553c0b99114f2435058fde52f` | `BORSAI_FAZ9_APP_UI_A: read-only view commands, ui_view config, K-PIN-UI test_5c` |
| B | `a2f94fd6181fd79204a012eb18174f60ac880532` | `BORSAI_FAZ9_APP_UI_B: sade view screens, fonts, styles, tests` |
| C | `89477d61109edf786b2d8741ad3652587572c902` | `BORSAI_FAZ9_APP_UI_C: screenshots, docs, deviations O` |
| R | (son koşu sayılarını ekleyen commit) | `BORSAI_FAZ9_APP_UI_R: final test runs` |

## 2. Taban (adım 0) ve prova (adım 0b)

**Taban** `5de4c27` = origin/main; ağaçta yalnız izinli izlenmeyenler (`docs/prompts/FAZ9_APP_UI.md`, `docs/design/ui_v2/**`).

| Ölçüm | Sonuç |
|---|---|
| Paralel pytest (`-n 6 --dist loadgroup`) | **952 passed** (8:44) |
| `bash app/scripts/test.sh` | yeşil: cargo 151 / 0, vitest 305 (20 dosya), parity 8, golden_unchanged yeşil |
| `gen_golden --check` | 35 / 0 |

**Prova** (geçici `git clone --local` klonu; `.venv` ve `app/node_modules` bağları klonun `.git/info/exclude`'unda): `app/README.md`'ye
zararsız bir satır, konusu `BORSAI_FAZ9_APP_UI_PROVA:` olan commit'le; ayrıca commit'lenmemiş `app/scripts/dev.sh` satırı.

| Ölçüm | Sonuç |
|---|---|
| Paralel pytest | 950 passed, **2 failed**: `tests/test_faz8_break.py::test_14b_old_specs_models_and_cutoff_unchanged` (commit'siz `app/scripts/dev.sh`: `git status --porcelain -- … app` boş değil) ve `tests/test_faz8_model.py::test_5c_old_goldens_and_app_pins_unchanged` (`git diff --name-only 7d78d43 -- tests/reference app models` listesinde commit'li `app/README.md` ve commit'siz `app/scripts/dev.sh`) |
| `test.sh` (klon, ayrı `CARGO_TARGET_DIR`) | yeşil: cargo 151, vitest 305 |

Beklenenle aynı (test_5c commit'li ve commit'siz, test_14b commit'siz) → DUR yok. Asıl repoda bu adımda commit yok.

## 3. Ekran ekran: ne yapıldı, hangi komut, hangi alan

Ortak: üst bar (marka, beş sekme, kod arama, mod göstergesi, veri tarihi, yerel saat, "Yeni arz gir", Ayarlar dişlisi); her ekranın
altında `DISCLAIMER` ve sürüm. Mod göstergesi eski bandın `render/shell.ts: bandFor` fonksiyonundan (aynı kaynak, K-UI-12). Bütün metin
`tr.ts`'te (`SADE`, `SADE_NAV`, `VERDICT_PLAIN`, `VERDICT_MARK`; var olan dizeler değişmedi).

| Ekran | Rust komutları | Okunan alanlar | Not |
|---|---|---|---|
| **Monitör** | `monitor_view`, `headline_gate`, `perf_view` | `registry/ipos.csv` (FROZEN satırlar), girdi belgesi `ipo_price_tl` / `shares_offered`, etkin kaydın `ceiling_hazard_v0.output.S` (beklenen/medyan L `ceiling_display_value`; P(≥5) = S[4]) ve `v1_5_h99.output.Dh`, `data/outcomes/<T>.csv` (`close_raw`, `upper_limit_raw`, `ceiling_close`, `R_h`), makine kaydı (`streak.b`, `streak.L`, `break_day.b_floor`, F1/F2 `p_floor`, `structural_zero_D10.impossible`, uyarı kodları), `scores.json` canlı satırları (`class`, `status`, `record_source`, kanıt zamanı), `scores_break.json` (`live_break.denominator[].class`, `card.regime_warning`) | Sayımlar Rust'ta: 7 arz; seride 0; D10'da arz altında 2 / 7 (NETGL `R_10` = −0.36168, BKRGY); tabanda kırılma 3 / 7 (BKRGY b = 1, KPEKS b = 6, NETGL b = 4); TKNKA "D10'da arz altına inemez"; kayıt sütunu model başına (NETGL "geç kayıt / getiri canlı"). Olay akışı dosyalardan; aynı gün aynı tür kayıt olayları tek satır. Rejim şeridi `FON_KRIZI_2026`. |
| **Yeni arz girişi** | `check_form`, `list_input_documents`, `read_input_document`, `market20_via_python`, `predict_all` | form durumu (`store.form`, eski Girdi ekranıyla ortak) | SPK bülteni (8), KAP sonuçları (8), BIST duyuruları (4) grupları; okunur tekrar (`312.5 milyon pay`, `17 Eylül 2026`); özdeşlik durumları yalnız Rust notlarından (`PB_IDENTITY`, `SHARES_SUM_MISMATCH`); f6 Hesapla / Elle gir / Boş bırak; ret nedeni `MARKET20_REASON_TEXT`. |
| **Tahmin sonucu** | `ceiling_display(S, 0 \| j)`, `ceiling_summary(runs, 0, null, t)`, `headline_gate`, `perf_view`, `save_scenario` | `predict_all` çıktısı (ya da kişisel kayıttaki çıktı, yeniden hesaplanmaz) | Manşet yalnız öne çıkan çıktılardan; P(L = l) çubukları; model / basit kural tablosu; geçmiş test iki değer + dosyadaki hüküm; hesaplayıcı (senaryo); getiri tablosu (D5 öne çıkan, öbürleri ≈); rejim uyarısı; dayanaklar; kişisel kayıt (beyansız istek). |
| **Analiz** | `arz_view`, `break_view`, `streak_view`, `record_summary(T, file, j, jObserved)`, `record_ceiling(T, file, j)`, `post_d1_view` (kayıt varsa), `headline_gate` | `arz_view`: zaman çizelgesi, koridor, kayıttaki `P_close_ceiling` ve V1.5 `price`, getiri satırları (`R_h` metni), günlük; `break_view`: makine kaydı, kart, sha denetimli katsayılar | j varsayılanı gözlenen j (NETGL 3); "Gözlenene dön"; `predict_all` çağrılmaz (U38; vitest). Kırılma kartı: F1 %50, F2 %30, taban kırılması sınıf oranı %54, `@ZERO` %30, ürün yok; özellik tablosu (30.56 = 30.56; −2.1789* kırpıldı, ham −2.2666; katsayılar +0.9867, +0.0629, sabit −1.0007, C = 1); D10 yapısal sıfır satırı; ön eleme etiketi; sınıf geçmişe dönük. |
| **Model performansı** | `perf_view`, `headline_gate` | `scores.json` birincil hücreler + `v1_5_h99` p_up D10 / `base_rate`; `scores_break.json` `card.backtest_info`; `scores_oot.json` `_all` blokları; canlı sayaçlar | Altı satır (§7'deki tablo); hüküm dosyadaki verdict + sade açıklama; okuma rehberi (nokta, çizgi, sıfır) aynen; aralık çizimi `svg.ts: intervalBar`; üç terazi ayrı; canlı ilerleme (n / 30); canlı satırlar (7 arz). Bağımsız modda gömülü scores.json ile ilk dört satır. |
| **Sicil** | `registry_view`, `monitor_view`, `break_view`, `post_d1_records`, `read_record_json` | kayıt satırları (dosya, kayıt zamanı, push kanıtı, ekleyen commit, girdi sha, INDEX sha, git HEAD), sayımlar | Künye sekmeleri (listeleme öncesi / kırılma akşamı / D1 sonrası); "D1 sonrası kayıt sihirbazı", "İptal kaydı düş" (eski kayıt sayfası) ve "Yeni resmi kayıt" sade kabukta eski ekranı açar. |
| **Kayıtlarım** | `list_scenarios`, `load_scenario`, `export_scenario`, `export_all_scenarios`, `delete_scenario` | — | Gerçek liste; örnek satır yok. |
| **Ayarlar ve Hakkında** | `get_config`, `set_config`, `validate_repo`, `set_ui_view`, `app_info` | — | Görünüm seçimi (Sade / Ayrıntılı). |
| **Sihirbaz kabuğu** | eski `screens/registry.ts` (`freeze_*`, `post_d1_*`) | — | Adım listesi + "Akılda tut"; eski ekran `.s-legacy` altında koyu temalı. |

## 4. Tasarım ↔ uygulama farkları (K-UI-7)

| # | Öğe (pano) | Neden | Ne yapıldı |
|---|---|---|---|
| F1 | "Ortalama seri 3,43 / modelin ortalaması 3,67" (Monitör) | ortalama (U25) | "Tavan serisinde" sayımı |
| F2 | "model hatası %25 daha düşük" (Sonuç, Model performansı) | oran (U25) | model ve kural değeri yan yana + dosyadaki hüküm |
| F3 | Monitör özetinde "en güçlü seyir TKNKA" | seçim ölçütü | yok |
| F4 | "BIST kapalı" göstergesi | takvim durumu dosyadan değil | yok; veri tarihi kalır |
| F5 | Analiz işlem adedi çubukları | sonuç dosyasında hacim yok | yok |
| F6 | Kalibrasyon grafiği ve D1 sonrası geçmiş test satırları (−0.0512, −0.0105) | skor dosyalarında yok | yok |
| F7 | Sayı sayma animasyonu | ön uç aritmetiği | yok; yalnız CSS hareket |
| F8 | Rejim şeridindeki piyasa sayıları (130 fon, BIST100 −%16,65) | dosyada yok | metin tr.ts + `start_d1` |
| F9 | "üçünde ertesi gün de taban", "kırılmadan sonra 7 seans taban", kırılma kartı "Gerçekleşen: taban, taban" | outcomes'ta alt limit yok; etiket yalnız skor satırında (RETRO'da yok) | yok |
| F10 | Monitör "Canlı sicil 0/30" tek sayı | modeller arası toplam terazileri karıştırır (V1.5 canlı n = 1) | model başına canlı n (Üretimdeki modeller, Model performansı) |
| F11 | "Üretimdeki model 4/30; 26'sı ölçüt", "Donmuş model ve kural 30", "Keşif varyantı 2.054" | toplam ve günlük sayımı uygulamada yok | "4" kalır |
| F12 | Monitör süzgeci "Kırılma akşamı 0" | "bugün kırılma akşamı" dosyalardan belirlenemez | "Tümü" ve "Seride" |
| F13 | Giriş: "Taban arzın bileşimi" yüzdeleri, ilerleme çubuğu, grup "8/8" sayaçları | oran ve ön uç sayacı | eksik zorunlu alan listesi |
| F14 | Giriş: "Modellerin göreceği değerler" (f1..f6, pb1..pb4) | tahminden önce özellik veren Rust komutu yok | yok (öneri: ayrı Rust komutu) |
| F15 | Giriş: tarihin haftanın günü | tarih hesabı | gün-ay-yıl okunur tekrar |
| F16 | Analiz koridorunda ±%10 bant mumları | alt limit yok | kapanış çizgisi, tavan/değil işaretleri, üst limit çentiği, arz çizgisi, model beklentisi, kırılma çizgisi |
| F17 | Analiz gerçekleşen satırında "taban" | alt limit yok | "tavan değil" |
| F18 | Günlükte "KAP arz adedi sabitlendi", işlem adedi (lot) | MANIFEST ve hacim okunmuyor | yok |
| F19 | Aralık yöntemi kutusu ("Blok … 4.000 tekrar") | alan adı U25 taramasında yasaklı sözcük | yok (ayrıntılı görünümde) |
| F20 | Araştırma arşivi | metinler skor dosyasında yok | ayrıntılı görünüme bağlantı |
| F21 | Olay akışında "Sistem: canlı skorlama açıldı" | git log gerekir | yok |
| F22 | Sihirbaz adım göstergesinde etkin adım | eski render dosyaları değişmez | adım listesi var, etkin işaret yok |
| F23 | Hakkında "Kırılma akşamı modelleri 2 899cf90c" | modeller gömülü değil (EK 5 portu ayrı) | yok |
| F24 | Kayıtlarım örnek satırı | örnek | gerçek liste |
| F25 | Sayı biçimi (`0,499`, `3,28`, `+%25,52`) | SPEC_APP §4 + format.ts | `%50`, `3.3`, `+%25.5` |
| F26 | Giriş "Piyasa: −%9,24, 16.09 / 19.08 kapanışları" | "Hesapla" bugünü referans alır (§3a.2); pinli XU100 bugüne yetişmediği için Python `XU100_CLOSE_MISSING` | ret nedeni metniyle gösterilir; davranış değişmedi (O17) |
| F27 | Sonuç ve Analiz'de D1 sonrası satırı (`post_d1_view`) | bugün D1 sonrası kayıt yok | not ("D1 sonrası model bu arz için kayıtlı değil" / senaryoda bülten yok) |

## 5. `headline_gate`'in bugünkü çıktısı (`app/tests/fixtures/ui/sade_gate.json`, gerçek dosyalar)

| Çıktı | Dosya | Durum | Birincil mi | Birincil hücre (ölçü · kurallar) | Dosyadaki verdict'ler | Öne çıkan | Etiket | Canlı n |
|---|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v0` S | scores.json | OK | evet | RPS · base_km_last10, base_km_expanding | geçiyor, geçiyor | **evet** | — | 0 |
| `v1_5_h99` return D1 | scores.json | OK | hayır | MAE · base_train_median | — | **hayır** | — | 1 |
| `v1_5_h99` return D3 | scores.json | OK | hayır | MAE · base_train_median | — | **hayır** | — | 1 |
| `v1_5_h99` return D5 | scores.json | OK | evet | MAE · base_train_median | geçiyor | **evet** | — | 1 |
| `v1_5_h99` return D10 | scores.json | OK | hayır | MAE · base_train_median | — | **hayır** | — | 1 |
| `v1_5_h99` p_up D1, D3, D5, D10 | scores.json | OK | hayır | MAE · base_train_median | — | **hayır** | — | 1 |
| `post_d1_hazard_v0` S_cond | scores_post_d1.json | OK | evet | RPS · ceiling_hazard_v0 | — (n = 0, hücre yok) | **hayır** | — | 0 |
| `break_floor_v0` p_floor F1 | scores_break.json | OK | evet | Brier · PRODUCT_BREAK_FLOOR | (hüküm alanı yok; `promotion.promoted` = true) | **evet** | ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0 | 0 |
| `break_floor_v0` p_floor F2 | scores_break.json | OK | hayır | Brier · PRODUCT_BREAK_FLOOR | — | **hayır** | (aynı) | 0 |

K-UI-4 beklentisiyle karşılaştırma: ceiling_hazard_v0 öne çıkar ✓; V1.5 D5 getirisi öne çıkar, D10 arz üstü olasılığı ≈ ✓;
post_d1_hazard_v0 ≈ (birincil RPS hücresi) ✓; break_floor_v0 `promotion` ne diyorsa o, etiket aynen ✓. Mutasyon (cargo): ceiling'in bir
birincil satırı "ayırt edilemiyor" yapılınca ya da satır silinince öne çıkmaz.

## 6. Değişen test fonksiyonları

| Test | K-PIN-UI | Gerekçe (tek satır) |
|---|---|---|
| `tests/test_faz8_model.py::test_5c_old_goldens_and_app_pins_unchanged` (+ yardımcı `_app_ui_commits_only`, sabitler `APP_UI_PREFIX`, `APP_UI_LAST_APP_SUBJECT`) | (a) | `app` diff yol listesinden çıktı; yerine `app/parity/` 7d78d43'ten beri değişmemiş ve app/'a dokunan her commit `BORSAI_FAZ9_APP_UI_` konulu, commit'siz app/ yalnız C'den önce; `tests/reference` ve `models` iddiaları aynen |

(b) kapsamında güncellenen vitest/cargo iddiası **yok**: var olan 305 vitest ve 151 cargo testi değişmeden yeşil kaldı.

K-PIN-UI (a) mutasyonları (prova klonu, yalnız `test_5c`): taban yeşil; C öncesi commit'siz app/ yeşil; yabancı konulu app/ commit'i
**kırmızı**; FAZ9 konulu `app/parity/README.md` değişikliği **kırmızı**; `BORSAI_FAZ9_APP_UI_C:` sonrası commit'siz app/ **kırmızı**, temiz yeşil.

Yeni testler: `app/src-tauri/tests/sade.rs` (10: ui_view geriye uyum; NETGL hesaplayıcı beklenen sayıları resmi ve senaryo yolunda;
headline_gate gerçek dosyalar + mutasyon; monitor_view; arz_view; break_view gerçek dosyalar + sha uyuşmazlığı / dosya yok / kayıt yok;
perf_view gerçek dosyalar + yalnız gömülü), `app/tests/sade_render.test.ts` (40), `sade_svg_format.test.ts` (8), `sade_invoke.test.ts`
(6), `sade_static.test.ts` (6).

**Beklenen sayı notu (O9):** görevdeki "beklenen L ≈ 3.2813" ve "P(10 | ≥3) ≈ 0.0592" 4 ondalığa yuvarlanmış S_k'lardan türetilmiş; tam
değerler 3.28115 ve 0.059132 (Python ile aynı). Cargo testi ikisini görev değerine ±3e-4 ve tam değere ±5e-5 ile sınar; öbür beklenen
sayılar ±5e-5 içinde birebir (S₁…S₁₀; medyan 3; P(L = 3) 0.2022, D4; j = 0 yarın tavan 0.8176; j = 3 bozulma 0.3324, kalan 1.890,
P(≥5 | ≥3) 0.4458; base_km_last10 S ve beklenen L 2.2127; monitör sayımları; F1/F2 p_floor; canlı sınıflar; performans satırları; kırılma
backtest satırları ve karşılaştırıcılar).

## 7. Test sayıları

| Aşama | pytest | `test.sh` | `gen_golden` |
|---|---|---|---|
| Taban (5de4c27), paralel | 952 passed (8:44) | yeşil: cargo 151, vitest 305, parity 8 | 35 / 0 |
| Prova (klon), paralel | 950 passed, 2 failed (beklenen) (10:12) | yeşil | — |
| A öncesi, paralel, `test_14b` ayrıldı | 951 passed, 1 deselected (10:37) | yeşil: cargo 161, vitest 305, parity 8 | 35 / 0 |
| A sonrası (temiz ağaç): `test_5c` + `test_14b` tek başına | 2 passed | — | — |
| B öncesi, paralel, `test_14b` ayrıldı | 951 passed, 1 deselected (10:42) | yeşil: cargo 161, vitest 365 (24 dosya), parity 8 | 35 / 0 |
| (ilk son kabul denemesi: sıralı pytest %96'da kırmızısız ilerlerken aracın arka plan süre sınırında durduruldu; `nohup` ile baştan koşuldu) | — | — | — |
| Son kabul (HEAD `89477d6` = C, temiz ağaç), **sıralı, ayrılan yok** | **952 passed** (16:52) | yeşil (0:59): cargo **161 / 0** (151 + 10 yeni), vitest **365** (24 dosya; 305 + 60 yeni), parity **8**, golden_unchanged yeşil | **35 / 0** |

Model performansı satırları (`scores.json`, dosyadaki verdict aynen; uygulamada `perf_view` → Model performansı):

| Model | Ölçü | Kural | Fark | %95 aralık | n | Kazanç / kayıp / eşit | Hüküm |
|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v0` | RPS | `base_km_last10` | −0.04956 | [−0.07515, −0.02186] | 87 | 52 / 35 / 0 | geçiyor |
| `ceiling_hazard_v0` | RPS | `base_km_expanding` | −0.05686 | [−0.08326, −0.02865] | 87 | 59 / 28 / 0 | geçiyor |
| `v1_5_h99` | D5 MAE | `base_train_median` | −0.08387 | [−0.13432, −0.03211] | 87 | 58 / 29 / 0 | geçiyor |
| `v1_5_h99` | D10 Brier | `base_rate` | −0.03910 | [−0.07562, +0.00234] | 81 | 52 / 29 / 0 | ayırt edilemiyor |
| `break_floor_v0` | F1 Brier | ürün | −0.19038 | [−0.25203, −0.12470] | 69 (21 ay) | — | (hüküm alanı yok) |
| `break_floor_v0` | F1 Brier | `@ZERO` | −0.02808 | [−0.04528, −0.00740] | 69 (21 ay) | — | (hüküm alanı yok) |

## 8. `.app` derlemesi

- Komut: `source app/scripts/env.sh && cd app && npm run tauri build -- --bundles app` (HEAD `89477d6` = C, temiz ağaç; 2:02; derleme
  izlenen hiçbir dosyayı değiştirmedi).
- Çıktı: `app/src-tauri/target/release/bundle/macos/BorsAi.app` (8.4 MB; ad-hoc imza, noter onayı yok).
- `Contents/MacOS/borsai-app` sha256: `208ae193a283551ffb1c2d3c373d5820cca28d90cce15e777e527770470106de`.
- Paketin bütün dosyalarının sha listesinin sha256'sı: `5217bc91f70d634ee6617c0bce899c063f4b838ebc3747e2c5c68f5f3521beea`.
- Ön uç paketinde 18 yerel woff2 (IBM Plex; latin + latin-ext) var; CSS'te uzak URL yok.
- Kurulum proje sahibinde: `ditto app/src-tauri/target/release/bundle/macos/BorsAi.app /Applications/BorsAi.app`.

## 9. Hijyen taraması

Yeni ve değişen her dosya (D: 29, A: 7, B: 56, C: görüntüler dahil) `registry/oot/cohort_pre_h99.csv`'deki 64 SEALED koduna karşı büyük/küçük
harf duyarlı, sözcük sınırıyla ve bülten adı kalıbına (`th[bm]` + 8 hane) karşı tarandı (kodlar yazdırılmadan): **0 bulgu**. Yeni Rust
görünümleri bülten dosya adlarını ve eğitim arz listelerini döndürmez; cargo testleri `monitor_view`, `arz_view` ve `break_view`
çıktılarında bülten adı kalıbı olmadığını sınar.

## 10. Görüntüler (`app/docs/screens/v2/`, gerçek uygulama, `bash app/scripts/screens_v2.sh`)

Gerçek uygulama (Tauri, `--features snapshot`), asıl repo salt okunur (betik sonunda `registry/` ve `data/` sha listeleri öncesiyle
aynı); uygulama verisi geçici dizinde. Pencere 1200 × 800 (görüntüler 1440 px). Eski `app/docs/screens/*.png` değişmedi.

| Dosya | İçerik |
|---|---|
| `v2_00_bagimsiz_mod_monitor.png` | Bağımsız mod: Monitör "repo modu gerekli" |
| `v2_01_monitor.png`, `v2_01b_monitor_olay_akisi.png` | Monitör: rejim şeridi, özet, veri şeridi, arz takip tablosu, seçili arz, üretimdeki modeller, olay akışı |
| `v2_02_giris_netgl_talep_sonrasi.png`, `v2_02b_giris_kap_bist_piyasa.png` | Yeni arz girişi, NETGL talep sonrası (sicil belgesinden), denetim, piyasa |
| `v2_03_sonuc_j0.png` | Tahmin sonucu, hesaplayıcı j = 0 (yarın tavan %82) |
| `v2_04_sonuc_j3.png`, `v2_04b_sonuc_getiri_dayanaklar.png` | Tahmin sonucu, hesaplayıcı j = 3 (bozulma %33, kalan 1.9, %45, %6); getiri tablosu, dayanaklar, kişisel kayıt |
| `v2_05_analiz_netgl.png` … `v2_05d_analiz_gunluk.png` | Analiz NETGL: başlık, zaman çizelgesi, koridor, kaç gün tavan; hesaplayıcı gözlenen j = 3 (D4'te bozuldu, L = 3); kırılma kartı ve getiri; günlük |
| `v2_06_model_performansi.png`, `v2_06b_model_performansi_terazi_canli.png` | Model performansı: fark satırları, okuma rehberi; üç terazi, canlı sicil |
| `v2_07_sicil.png` | Sicil |
| `v2_08_kayitlarim.png` | Kayıtlarım (demo kaydı, geçici uygulama verisinde) |
| `v2_09_sihirbaz_adim1_on_kosullar.png` | Dondur sihirbazı adım 1 (yalnız ön koşul denetimi; yazma yok) sade kabukta |
| `v2_10_ayarlar_hakkinda.png` | Ayarlar ve Hakkında, görünüm seçimi |
| `v2_11_ayrintili_gorunume_gecis.png` | Ayarlar'dan ayrıntılı görünüme geçiş (eski arayüz, "Sade görünüme dön") |
| `v2_12_sade_gorunume_donus.png` | Sade görünüme dönüş |

## Kabul kapısı

| Koşul | Durum |
|---|---|
| Son sıralı pytest yeşil, ayrılan yok | ✓ 952 passed |
| `test.sh` yeşil (cargo, vitest — U19, U21, U25, U34 dahil —, parity, golden_unchanged) | ✓ |
| `gen_golden --check` 35/0 | ✓ |
| `git diff 5de4c27 -- app/src/screens app/src/render` yalnız `svg.ts` ve `format.ts` eklemeleri; `tr.ts`'te silinen/değişen satır yok | ✓ (277 ekleme, 0 silme; tr.ts 0 silme) |
| `git diff 5de4c27 --stat -- borsai models registry data scores legacy docs/specs* CLAUDE.md experiments` boş | ✓ |
| Sade görünüm varsayılan; Ayarlar'dan ayrıntılı görünüme geçiş ve dönüş (görüntüler) | ✓ `v2_10`, `v2_11`, `v2_12` |
| Hesaplayıcı NETGL'de beklenen sayılar (cargo testi ve görüntü) | ✓ `calculator_netgl_expected_numbers`; `v2_03`, `v2_04`, `v2_05b` |
| Hijyen temiz | ✓ 0 bulgu |

## 11. Açık kalanlar

- K-UI-15 sırasına göre yetişmeyen ekran yok.
- **EK 5 portu** (kırılma modelinin Rust portu, üçüncü dizin gömme, altın vektörler; senaryo modunda kırılma tahmini) ayrı görev.
- F14: tahminden önce model özelliklerini (f1..f6, pb1..pb4) veren bir Rust komutu yazılırsa Girişteki "Modellerin göreceği değerler"
  çizilebilir.
- Sihirbazların tam yeniden çizimi (etkin adım göstergesi dahil) bu görevde zorunlu değildi; eski ekran sade kabukta.
- Pencere varsayılanı 1200 × 800 (`tauri.conf.json` değişmedi); tasarım 1440 genişlikte. Dar pencerede Monitör'ün yan sütunu alta iner.

## Yazı tipi lisansı (K-UI-9)

IBM Plex Sans, IBM Plex Sans Condensed ve IBM Plex Mono: SIL Open Font License 1.1 (`@fontsource/*` 5.3.0 paketlerinin `license`
alanı ve LICENSE dosyaları). Yalnız devDependencies; Vite font dosyalarını uygulama paketine gömer; çalışma zamanında ağ yok.

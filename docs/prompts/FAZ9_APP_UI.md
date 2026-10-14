# FAZ9_APP_UI — Sade görünüm (onaylı yeni arayüz)

**Model: Claude Code / Opus 5.5 · Extra**

- **TASK_ID:** `BORSAI_FAZ9_APP_UI_20261003`
- **Klasör:** repo kökü `~/Desktop/BorsAi`
- **Ağ:** yalnız npm kayıt deposu, yalnız K-UI-9'daki üç yazı tipi paketi için. Başka ağ yok.
- **Commit konusu öneki:** `BORSAI_FAZ9_APP_UI_` (D, A, B, C, R; aşağıda).

## Rol

Uygulamanın ana mühendisisin. Proje sahibinin onayladığı yeni arayüzü ("sade görünüm") mevcut uygulamanın üstüne kuracaksın. Eski arayüz silinmez; **Ayrıntılı görünüm** olarak kodu ve testleriyle aynen kalır. Gelecek hafta proje sahibi hocalarına uygulamayı gösterecek: öncelik, sunumda görünecek ekranların doğru ve sağlam çalışması.

## Bağlam

**Tasarım:** `docs/design/ui_v2/` (önce `README.md`; panolar `boards/*.dc.html`, görüntüler `png/*.png`). 12 pano: Monitör, Yeni arz girişi, Tahmin sonucu, Analiz, Model performansı, Sicil, Resmi kayıt sihirbazı, D1 sonrası kayıt, Kayıtlarım, Ayarlar ve Hakkında, Stil rehberi, Palet seçenekleri. Uygulanacak palet: Safir.

**Proje sahibinin özel isteği:** eski arayüzdeki "seri j gün sürdüyse yarın ne olur" hesabını (varsayımsal j) bulamadı. Sade görünümde bu, **Tahmin sonucu**nda ve **Analiz**'de görünür bir hesaplayıcıdır (tasarımda "Seri j gün sürdüyse yarın ne olur?"). Var olan Rust komutlarıyla (`ceiling_display`, `ceiling_summary`, `record_summary`, `streak_view`) yapılır; yeni hesap yazılmaz.

**Orkestratörün ölçtükleri (2026-10-03, HEAD = origin/main = `5de4c27`, ağaç temiz):**

1. **`tests/test_faz8_model.py::test_5c_old_goldens_and_app_pins_unchanged`** `git diff --name-only 7d78d43 -- tests/reference app models` çıktısının yalnız üç dondurma dosyası olmasını ister. **`app/` altındaki her değişiklik bu testi kırar.** Önceden onaylı kural: K-PIN-UI (a).
2. **`tests/test_faz8_break.py::test_14b_...`** `git status --porcelain -- … app` boş ister: temizlik bekçisidir. Commit'lenmemiş `app/` değişikliğinde kırmızıdır. Kalıp: commit öncesi ara koşudan ayrılır, commit'ten sonra ayrılmadan koşar.
3. **`app/tests/no_frontend_math.test.ts`:** TS'de `* / %` yalnız `render/format.ts` ve `render/svg.ts`'te. `mean(`, `.reduce(`, `**`, `Math.pow` vb. her yerde yasak. Türkçe serbest metin yalnız `i18n/tr.ts`'te.
4. **`app/tests/no_network.test.ts` (U34):** `package.json` `dependencies` tam olarak `["@tauri-apps/api", "@tauri-apps/plugin-dialog"]`. CSP `default-src 'self'`. Yazı tipleri bu yüzden `devDependencies`'ten paketlenir (K-UI-9).
5. **SPEC_APP §4:** yasak sözcükler ("kesin", "garanti", "kazandırır", "al/sat", "hedef fiyat", "sinyal", tek başına "doğruluk %…"); sayı biçimleri (getiri 1 ondalık yüzde, fiyat 2 ondalık TL, olasılık 0 ondalık yüzde, metrik 4 ondalık); her ekranda `DISCLAIMER`.
6. **U19:** "geçiyor" dizesi yalnız `tr.ts`'deki verdict eşlemesinde. Panelde basılan hüküm metni dosyadaki `verdict` alanının kendisidir.
7. **Veri kaynakları (hepsi var, hepsi salt okunur):**
   - `registry/records/<T>/*.json`: listeleme öncesi kayıtlar (7 arz, 16 model). `models[].output.S`, `P_L` ve V1.5 getirileri.
   - `registry/post_break/<T>/machine_*.json`: 7 makine kaydı. `streak`, `break_day.b_floor`, `features` (z ve clipped), `models[0].output.F1/F2.p_floor`, `structural_zero_D10.impossible`, `warnings`.
   - `data/outcomes/<T>.csv`: `h`, `session_date`, `close_raw`, `upper_limit_raw`, `ceiling_close`, `R_h` (yalnız h = 1, 3, 5, 10 satırlarında dolu).
   - `scores/scores.json`: `models[].backtest.cells[]` (`diff`, `ci95`, `n`, `wins`, `losses`, `ties`, `model_value`, `rule_value`, `verdict`), `primary_cell`, `live.rows[]` (`class`, `status`).
   - `scores/scores_break.json`: `models[].card.backtest_info` (F1_product, F1_zero), `comparators_frozen`, `promotion`, `live_break`.
   - `scores/scores_post_d1.json` ve `scores/scores_oot.json`: var olan okuyucular.
   - `models/break_floor_v0.json`: katsayılar. Okunurken sha, makine kaydındaki `params_sha256` ile karşılaştırılır; tutmazsa kart kapanır.
8. **D1 sonrası modelin geçmiş test hücreleri** (MODELS.md'deki −0.0512 ve −0.0105) **hiçbir skor dosyasında yok.** Kırılma modelinin kalibrasyon grupları da yok. Bunlar çizilmez (K-UI-7).
9. **EK 5'in Rust portu bu görevde YOK.** Kırılma kartı yalnız makine kaydından ve `scores_break.json`'dan okunur; senaryo modunda kırılma tahmini üretilmez. Üçüncü dizin gömme, altın vektörler ve port ayrı görevdir.

## Kararlar

- **K-UI-1 · İki görünüm.** `SADE` (varsayılan) ve `AYRINTILI` (eski arayüz, aynen). Seçim Ayarlar'da. `AppConfig`'e geriye uyumlu `ui_view` alanı eklenir: yoksa `SADE`; eski config dosyaları okunur. Her sade ekranda "Ayrıntılı görünüm" bağlantısı karşılık gelen eski ekrana gider.
- **K-UI-2 · Eski kod değişmez.** `app/src/screens/*.ts` ve `app/src/render/*.ts` mevcut dosyaları değişmez. İki istisna var, ikisi de yalnız ekleme: `render/svg.ts` (yeni koordinat fonksiyonları) ve `render/format.ts` (yeni biçimleyiciler). `main.ts` kabuğu görünüme göre yönlendirir. Yeni TS kodu `app/src/sade/` altına (ekranlar, saf render fonksiyonları, `sade.css`). Metinler `i18n/tr.ts`'e yeni bir dışa aktarım olarak eklenir; var olan dizeler değişmez.
- **K-UI-3 · Bütün sayılar Rust'tan.** Gereken yeni salt okuma komutları (adlar önerilir; sen netleştir):
  - `monitor_view`: arz listesi, kapanış dizisi, D10 getirisi `R_h`'den, seri, kırılma günü ve türü, kayıttan beklenen ve medyan seri ile P(≥5), makine kaydından ertesi gün taban, sınıflar `scores.json` canlı satırlarından, özet **sayımları**.
  - `arz_view(ticker)`: zaman çizelgesi, koridor, günlük.
  - `break_view(ticker)`: makine kaydı, `scores_break.json` kartı, sha denetimli katsayılar.
  - `perf_view`: model ile kural farkı satırları, üç terazi özeti, canlı satırlar; yalnız skor dosyalarından.
  - `headline_gate` (K-UI-4).

  Hiçbiri skor ya da metrik hesaplamaz (U25). Okur, eşler, sayar, sıralar. Var olan komutlar yeniden kullanılır.
- **K-UI-4 · Ana ekran kapısı veri-güdümlü.** Bir model çıktısı "öne çıkan" olarak ancak önceden ilan edilmiş birincil hücresinin `verdict`'i `geçiyor` ise görünür. Aksi hâlde yalnız ilgili panelde "≈ fark net değil" işaretiyle ve öne çıkmadan durur. Ön uçta elle liste yok. Bugünkü dosyalarla beklenen:
  - `ceiling_hazard_v0` öne çıkar;
  - `v1_5_h99` D5 getirisi öne çıkar, D10 arz üstü olasılığı ≈ işaretli;
  - `post_d1_hazard_v0` ≈ işaretli (birincil RPS hücresi);
  - `break_floor_v0`: `scores_break.json` `promotion` / `backtest_info.k1` ne diyorsa o. Etiket "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = k".
- **K-UI-5 · Hüküm metni.** Hüküm hücresi dosyadaki `verdict`'tir (U19). Sade dil açıklaması (ör. "aralığın tamamı sıfırın altında: model ortalamada daha az hata yaptı") `tr.ts`'te verdict'e bağlı ayrı bir dizedir. Tasarımdaki "Model daha iyi / Fark net değil" etiketleri bu açıklama satırına dönüşür. Model performansındaki okuma rehberi (nokta, çizgi, sıfır) aynen gelir.
- **K-UI-6 · Biçim.** SPEC_APP §4 ve var olan `format.ts` kuralları geçerlidir. Tasarımdaki yazımlar (`0,499`, `+%25,52`) biçim örneği değildir.
- **K-UI-7 · Tasarımda olup dosyada olmayan ya da ön uçta hesap isteyen öğe çizilmez.** Rapordaki "tasarım ↔ uygulama farkları" tablosuna yazılır. Orkestratörün bildikleri `docs/design/ui_v2/README.md` "Tasarımdan uygulamaya geçerken" §3'te. Bulduğun başkalarını ekle.
- **K-UI-8 · Hesaplayıcı.**
  - j düğmeleri 0–9.
  - Senaryoda değerler `ceiling_summary(runs, j, null, t)` ya da `ceiling_display`'den gelir.
  - Resmi görünümde `record_summary(ticker, file, j, jObserved)`; `jObserved` `streak_view`'den gelir; "Gözlenene dön" düğmesi var.
  - Yarın bozulma, beklenen kalan gün, koşullu medyan, P(≥ 5 | ≥ j) ve P(10 | ≥ j) Rust alanlarıdır.
  - Eğri koordinatı `render/svg.ts`'te çizilir.
  - Kullanıcı beyan şeridi (U52) sade görünümde yok; ayrıntılı görünümde aynen var.
  - D1 sonrası satırı: kayıt varsa `post_d1_view`, yoksa tasarımdaki not.
- **K-UI-9 · Yazı tipleri.** `@fontsource/ibm-plex-sans`, `@fontsource/ibm-plex-sans-condensed`, `@fontsource/ibm-plex-mono` **devDependencies** olur (OFL). Vite paketler, ağ gerekmez. `package-lock.json` commit'lenir. U34 aynen yeşil kalır. Lisans notu raporda.
- **K-UI-10 · Hareket.** Yalnız CSS (çizgi çizilmesi, çubuk büyümesi, belirme). `prefers-reduced-motion` desteklenir. Sayı sayma animasyonu yok (U25).
- **K-UI-11 · Sihirbazlar.** Dondur ve D1 sonrası akışlarının mantığı, komutları ve metinleri aynen kalır. Sade görünümde var olan sihirbaz ekranı yeni kabuğun içinde, yeni CSS kapsamıyla (`.sade` kökü altında var olan sınıflar) gösterilir. Tasarımdaki adım göstergesi kabuğa eklenebilir, ama eski render dosyaları değişmez. Tam yeniden çizim bu görevde zorunlu değil.
- **K-UI-12 · Mod göstergesi ve uyarılar.** Üst barda ekrana göre mod göstergesi var. Eski bant metinleri (`TR.modeScenario` vb.) korunur, ikisi aynı kaynaktan gelir. Her sade ekranın altında `DISCLAIMER` var. Rejim uyarısı `FON_KRIZI_2026` kuralıyla (C4; D_1 ≥ 2026-09-16) ilgili arzlarda ve Monitör'de görünür; metin `tr.ts`'te.
- **K-UI-13 · Bağımsız mod.** Repo yokken Yeni arz girişi, Tahmin sonucu, Kayıtlarım ve Ayarlar çalışır. Monitör, Analiz, Sicil ve Model performansı "repo modu gerekli" boş durumu ve Ayarlar bağlantısını gösterir (gömülü skorla çalışan kısımlar çalışabilir).
- **K-UI-14 · Windows.** Yeni kodda sabit Mac yolu ya da kabuğa özel sözdizimi yok.
- **K-UI-15 · Öncelik.** Sıra: Monitör → Yeni arz girişi → Tahmin sonucu (hesaplayıcı) → Analiz (hesaplayıcı + kırılma kartı) → Model performansı → Sicil → Kayıtlarım → Ayarlar ve Hakkında → sihirbaz kabuğu. Zaman yetmezse sona kalanlar ayrıntılı görünüme bağlanır ve raporlanır.

## Önceden onaylı pin güncellemeleri (K-PIN-UI)

Proje sahibi başlatma cümlesinde onaylar. Bunların dışında hiçbir test gevşetilmez.

- **(a)** `tests/test_faz8_model.py::test_5c_old_goldens_and_app_pins_unchanged`: `app` yol listesinden çıkar. Yerine iki iddia gelir:
  1. `app/parity/` `7d78d43`'ten beri değişmemiş (boş diff; `gen_golden --check` zaten koşuyor);
  2. `7d78d43..HEAD` arasında `app/`'a dokunan her commit'in konusu `BORSAI_FAZ9_APP_UI_` ile başlıyor, ve commit'lenmemiş `app/` değişikliği yalnız bu görevin commit'lerinden önceki ara koşularda var (var olan `_task_commits_ref` kalıbı).

  `tests/reference` ve `models` iddiaları aynen kalır.
- **(b)** Vitest ve cargo'da yalnız şunlar güncellenebilir:
  - kabuk ve gezinme iddiaları (`main.ts` yönlendirmesi, NAV);
  - `AppConfig` şemasına `ui_view` eklenmesinin kırdığı iddialar.

  U13–U26, U34, parite, `golden_unchanged`, `no_frontend_math` (izin listesi aynen; yeni dosyaları da tarar) ve var olan ekran render testleri **değişmez**. Değişen her test fonksiyonu rapora listelenir.
- **(c)** Python kodu (`borsai/`), `models/`, `registry/`, `data/`, `scores/`, `legacy/`, `docs/specs*`, `CLAUDE.md` ve `experiments/log.jsonl` **değişmez**.

**Bekçiler asla ayrılmaz** (kasa, sıra, hijyen, `test_outcome_guard`, `test_scoring` içerik pinleri). Temizlik bekçisi `test_14b` yalnız commit öncesi ara koşulardan ayrılır.

## İzinli izlenmeyenler (adım 0)

`docs/prompts/FAZ9_APP_UI.md` ve `docs/design/ui_v2/**`. Bunları orkestratör koydu; ilk commit'e (D) girerler.

## ÖNCE OKU

1. `docs/design/ui_v2/README.md`, sonra `png/*.png` (hepsi), sonra gerektikçe `boards/*.dc.html`.
2. `docs/app/SPEC_APP.md` §1.1, §3, §4, §5.3, §5.5, §5.6.
3. `app/README.md`, `app/src/main.ts`, `app/src/state.ts`, `app/src/api.ts`, `app/src/render/shell.ts`, `app/src/render/summary.ts`, `app/src/render/ceiling.ts`, `app/src/i18n/tr.ts` (`COND`, `SUMMARY`, `RESULTS`, `ACCURACY`).
4. `app/tests/no_frontend_math.test.ts`, `app/tests/no_network.test.ts`, `app/tests/helpers.ts`, `app/scripts/test.sh`, `app/scripts/screens.sh`, `app/src/dev/demo.ts`.
5. `tests/test_faz8_model.py` (`test_5c`, `_task_commits_ref`), `tests/test_faz8_break.py::test_14b…`.
6. `docs/faz8/LIVE_RAPOR.md` (makine kaydı alanları), `docs/SCORES_BREAK.md`.
7. `docs/SPEC_DEVIATIONS.md` son bölüm (N): yeni bölüm aynı biçimde "O" olur.

## Adımlar

**0. Taban.**
- `git status --porcelain --untracked-files=all` yalnız izinli izlenmeyenleri gösterir.
- HEAD = origin/main.
- Ara paralel pytest (`.venv/bin/pytest -q -n 6 --dist loadgroup`) yeşil, 952.
- `bash app/scripts/test.sh` yeşil.
- `gen_golden --check` 35/0.

Kırmızı varsa DUR, raporla.

**0b. Geçici klonda prova.**
- `git clone --local` ile bir klon aç.
- `app/` altında zararsız bir değişikliği konusu `BORSAI_FAZ9_APP_UI_PROVA:` olan bir commit'le yap. Bir de commit'lenmemiş `app/` değişikliği bırak.
- Klonda pytest (paralel) ve `test.sh` koş. Kırılan testlerin **tam listesini** çıkar.
- Beklenen: `test_5c` (commit'li ve commit'siz) ve `test_14b` (commit'siz).

Liste farklıysa DUR, raporla. Asıl repoda bu adımda hiçbir şey commit'lenmez.

**1. Haritalama (kod yok).** `docs/app/UI_V2_HARITA.md` yaz. Her pano için:

| Öğe | Veri kaynağı (komut, dosya alanı) | SPEC kuralı | Durum (çizilir / çizilmez + neden) |
|---|---|---|---|

Yeni Rust komutlarının imzaları, `headline_gate` kuralının bugünkü dosyalarla çıktısı (K-UI-4 beklenenleriyle karşılaştır) ve "tasarım ↔ uygulama farkları" ilk listesi.

**Commit D:** `BORSAI_FAZ9_APP_UI_D: design assets, task file, mapping`
```
git add docs/prompts/FAZ9_APP_UI.md docs/design/ui_v2 docs/app/UI_V2_HARITA.md
```

**2. Rust (A).**
- Yeni salt okuma komutları, `AppConfig.ui_view`, K-PIN-UI (a) test değişikliği.
- Cargo testleri gerçek repo dosyalarıyla, aşağıdaki **beklenen sayılar**la.
- Ara paralel pytest: `test_14b` ayrılır.
- **Commit A:** `BORSAI_FAZ9_APP_UI_A: read-only view commands, ui_view config, K-PIN-UI test_5c`. `git add` yalnız `app/src-tauri/` altındaki dokunduğun yollar ve `tests/test_faz8_model.py`.
- Commit'ten hemen sonra `test_5c` ve `test_14b` tek başına yeşil.

**3. TS (B).**
- Sade kabuk ve ekranlar (`app/src/sade/`), `tr.ts` eklemeleri, `render/svg.ts` ve `render/format.ts` eklemeleri, yazı tipleri, `sade.css`.
- Vitest: her yeni saf render fonksiyonu için metin ve yapı testleri. Gerçek dosyalardan üretilmiş fixture'larla.
- U19, U21, U25 ve U34 taramaları yeni dosyaları da kapsar.
- **Commit B:** `BORSAI_FAZ9_APP_UI_B: sade view screens, fonts, styles, tests`. `git add` yalnız `app/src/`, `app/tests/`, `app/package.json`, `app/package-lock.json` ve `app/index.html` (dokunduysan).

**4. Görüntüler ve belgeler (C).**
- `app/scripts/screens.sh` kalıbıyla sade görünüm demo koşusu. Çıktı `app/docs/screens/v2/*.png`; eski `app/docs/screens/*.png` **değişmez**.
- En az şu görüntüler:
  - Monitör;
  - Yeni arz girişi (NETGL, talep sonrası);
  - Tahmin sonucu j = 0 ve j = 3;
  - Analiz NETGL (hesaplayıcı gözlenen j = 3);
  - Model performansı;
  - Sicil;
  - Kayıtlarım;
  - Ayarlar;
  - bir sihirbaz adımı;
  - ayrıntılı görünüme geçiş.
- `app/README.md`'ye sade görünüm bölümü.
- `docs/SPEC_DEVIATIONS.md`'ye "O. Sade görünüm (BORSAI_FAZ9_APP_UI_20261003)" bölümü (K-UI-1 … K-UI-15 ve K-PIN-UI satırları).
- `docs/app/UI_V2_RAPOR.md` (teslim, aşağıda).

**Commit C:** `BORSAI_FAZ9_APP_UI_C: screenshots, docs, deviations O`

**5. Derleme.** `npm run tauri build -- --bundles app`. `.app` sha'sını rapora yaz. Kurulumu proje sahibi yapar (`ditto … /Applications/BorsAi.app`); sen kurma.

**6. Son kabul.**
- Sıralı `.venv/bin/pytest -q`, **ayrılan test yok**.
- `bash app/scripts/test.sh`, `gen_golden --check`.
- Sayıları rapora yaz. **Commit R:** `BORSAI_FAZ9_APP_UI_R: final test runs`.

## Beklenen sayılar (orkestratör dosyalardan hesapladı; cargo testleri bunlarla)

**NETGL, `ceiling_hazard_v0`, kayıt `registry/records/NETGL/20260922T121936Z_65a39d7392dd.json`:**
- S₁…S₁₀ = 0.8176, 0.7053, 0.6084, 0.4062, 0.2712, 0.1811, 0.1209, 0.0807, 0.0539, 0.0360 (4 ondalık).
- Beklenen L ≈ 3.2813, medyan 3; P(L = l)'nin tepesi l = 3 (≈ 0.2022), yani D4'te bozulma.
- j = 0: yarın tavan ≈ 0.8176.
- j = 3: yarın bozulma ≈ 0.3324, beklenen kalan ≈ 1.890, P(≥5 | ≥3) ≈ 0.4458, P(10 | ≥3) ≈ 0.0592.
- Gözlenen j = 3: seri D4'te bozuldu, L = 3.

**Basit kural `base_km_last10` aynı kayıtta:** S = 0.5, 0.4, 0.32, 0.256, 0.2048, … ; beklenen L ≈ 2.2127.

**Monitör sayımları:**
- 7 arz; seride 0.
- D10'da arz altında 2: NETGL `R_10` ≈ −0.3617, BKRGY.
- Tabanda kırılma 3: BKRGY b = 1, KPEKS b = 6, NETGL b = 4.

**Makine kayıtları, F1 `p_floor` (ertesi gün taban):**

| Arz | F1 p_floor | Not |
|---|---|---|
| BKRGY | 0.5433 | |
| KPEKS | 0.5389 | |
| NETGL | 0.4991 | F2 0.3043; `b_turnover` kırpıldı uyarısı |
| INTET | 0.1418 | |
| CITAS | 0.1383 | |
| TKNKA | 0.1382 | `structural_zero_D10.impossible` = true → "D10'da arz altına inemez" rozeti |
| VEYAS | 0.1376 | |

**Canlı sınıflar (`scores.json`):**
- `ceiling_hazard_v0`: LATE_RECORD 6, ret 1 (VEYAS), LIVE 0.
- `v1_5_h99`: LIVE 1 (NETGL; eski repodan 16.09 kaydı, kayıt kanıtı 2026-09-16T11:32:27Z), LATE_RECORD 5, ret 1 (VEYAS).
- Monitör'ün kayıt sütunu bu yüzden model başına yazılır: NETGL'de "geç kayıt; getiri canlı".

**Model performansı satırları** (`scores.json` backtest hücreleri; dosyada `verdict` aynen):

| Model | Ölçü | Kural | Fark | %95 aralık | n | Kazanç / kayıp / eşit | Hüküm |
|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v0` | RPS | `base_km_last10` | −0.04956 | [−0.07515, −0.02186] | 87 | 52 / 35 / 0 | geçiyor |
| `ceiling_hazard_v0` | RPS | `base_km_expanding` | −0.05686 | [−0.08326, −0.02865] | 87 | 59 / 28 / 0 | geçiyor |
| `v1_5_h99` | D5 MAE | `base_train_median` | −0.08387 | [−0.13432, −0.03211] | 87 | 58 / 29 / 0 | geçiyor |
| `v1_5_h99` | D10 Brier | `base_rate` | −0.03910 | [−0.07562, +0.00234] | 81 | 52 / 29 / 0 | ayırt edilemiyor |

**Kırılma (`scores_break.json` `backtest_info`):**
- F1 − ürün −0.19038 [−0.25203, −0.12470], n 69 (21 ay);
- F1 − `@ZERO` −0.02808 [−0.04528, −0.00740].
- `comparators_frozen.by_type_F1`: taban kırılması 0.5429, taban üstü 0.1277; `zero.F1` 0.3049.

## Tek oturumda bitmezse

Commit sınırlarında (D, A, B, C) dur. Raporun "nerede kaldım" bölümünü yaz. Commit'lenmemiş iş bırakma.

## Kurallar

- push, tag ve amend yok (proje sahibi yapar).
- Her commit'te açık `git add` yolları; `git add -A` ya da `.` yok.
- Yazılabilir: `app/` (K-UI-2 sınırlarıyla), `tests/test_faz8_model.py` (yalnız K-PIN-UI (a)), `docs/app/`, `docs/design/ui_v2/` (yalnız commit D'de, içerik aynen), `docs/SPEC_DEVIATIONS.md` (yalnız ekleme), `app/README.md`.
- Salt okunur: geri kalan her şey (K-PIN-UI (c)).
- **Hijyen:** yeni ve değişen her dosyayı `registry/oot/cohort_pre_h99.csv`'deki SEALED kodlarına karşı büyük/küçük harf duyarlı tara. Bülten adı kalıbı (`th[bm]` + 8 hane) yok. Sonucu rapora yaz.
- Belirsizlikte: kural şartnamede ya da bu dosyada yazılıysa uygula; yazılı değilse ve sonucu etkiliyorsa DUR, seçenekli soru sor.

## Teslim (`docs/app/UI_V2_RAPOR.md`)

1. Commit listesi (sha, konu).
2. Adım 0b'nin kırılan test listesi (beklenenle karşılaştırma).
3. Ekran ekran ne yapıldı; hangi Rust komutu, hangi dosya alanı.
4. **Tasarım ↔ uygulama farkları** tablosu (K-UI-7): öğe, neden, ne yapıldı.
5. `headline_gate`'in bugünkü çıktısı.
6. Değişen test fonksiyonları (K-PIN-UI (a), (b)), her biri tek satır gerekçeyle.
7. Test sayıları: pytest (sıralı, ayrılan yok), cargo, vitest, parity, `golden_unchanged`, `gen_golden`.
8. `.app` sha'sı ve derleme komutu.
9. Hijyen taraması sonucu.
10. Görüntü listesi (`app/docs/screens/v2/`).
11. Açık kalanlar (K-UI-15 sırasına göre yetişmeyenler; EK 5 portu ayrı görev).

## Kabul kapısı

- Son sıralı pytest yeşil, **ayrılan yok**.
- `test.sh` yeşil: cargo, vitest (U19, U21, U25 ve U34 dahil), parity, `golden_unchanged`.
- `gen_golden --check` 35/0.
- Eski render ve ekran dosyaları değişmedi: `git diff 5de4c27 -- app/src/screens app/src/render` yalnız `render/svg.ts` ve `render/format.ts` eklemeleri. `tr.ts`'te silinen ya da değişen satır yok.
- `git diff 5de4c27 --stat -- borsai models registry data scores legacy docs/specs* CLAUDE.md experiments` boş.
- Sade görünüm varsayılan; Ayarlar'dan ayrıntılı görünüme geçiş ve geri dönüş çalışıyor (görüntülerde).
- Hesaplayıcı NETGL'de beklenen sayıları veriyor (cargo testi ve görüntü).
- Hijyen temiz.

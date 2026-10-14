# 8. Uygulama II: arayüz ve ekranlar

Bu bölüm BorsAi masaüstü uygulamasının **ön ucunu** anlatır. Ön uç (frontend), pencerenin içinde gördüğün her şeydir: düğmeler, tablolar, grafikler, metinler. Arkasında Rust ile yazılmış bir **arka uç** (backend) çalışır; modeller orada koşar, dosyalar orada okunur. Bu bölüm arka ucu yalnız ön ucun ondan ne istediği kadarıyla anlatır.

Okurken iki soruyu aklında tut: "Bu sayı nereden geliyor?" ve "Bu ekran neden böyle?". Uygulamanın neredeyse bütün tasarım kararları bu iki sorunun cevabıdır. Kısa cevap şudur: **sayılar Rust'tan ya da repodaki dosyalardan gelir; ön uç yalnız biçimlendirir ve çizer.** Ekranlar da projenin dürüstlük kurallarını (dondurma, üç terazi, küçük örnekte hüküm vermeme) görünür kılacak biçimde kurulmuştur.

Bölümde anılan örnek sayılar (ör. "yarın da tavan %82") test dosyalarına gömülmüş beklenen değerlerdir ya da teslim raporlarından alınmıştır. Hangisi olduğu yanlarında yazar. Bu oturumda uygulama derlenmedi, testler koşulmadı; kod ve belgeler okunarak yazıldı.

---

## 8.1 Büyük resim: ön uç ne yapar, ne yapmaz

### Katmanlar

Uygulama **Tauri 2** ile kurulmuştur. Tauri, bir web sayfasını işletim sisteminin kendi tarayıcı motorunda (macOS'ta WKWebView) gösteren ve bu sayfaya Rust ile yazılmış bir arka uç bağlayan bir çatıdır. Electron'a benzer ama çok daha küçüktür: tarayıcıyı pakete gömmez, sistemdekini kullanır.

```
┌─ Pencere (WebView) ─────────────────────────────────────────────┐
│ Ön uç: TypeScript, Vite ile paketlenir, çerçeve (framework) yok  │
│  - Rust komutlarını invoke() ile çağırır                          │
│  - gelen sayıları biçimlendirir (format.ts)                       │
│  - grafikleri elle SVG olarak çizer (svg.ts)                      │
└───────────────┬──────────────────────────────────────────────────┘
                │ tauri::command (JSON)
┌───────────────▼─ Rust arka uç (src-tauri) ───────────────────────┐
│ modeller (gömülü), predict, dosya okuma, skor dosyası okuyucuları │
└───────────────┬──────────────────────────────────────────────────┘
                │ yalnız repo modunda, ağ yok
┌───────────────▼─ Python (repo içi .venv) ────────────────────────┐
│ borsai.freeze (resmi kayıt yazıcı), borsai.market20 (XU100 f6)    │
└──────────────────────────────────────────────────────────────────┘
```

**TypeScript** (TS), JavaScript'e tür denetimi ekleyen dildir; derleyici (`tsc`) tür hatalarını yakalar, sonra düz JavaScript üretilir. **Vite**, kaynak dosyaları tek pakete toplayan ve geliştirme sırasında sayfayı canlı yenileyen araçtır.

### Neden çerçeve yok?

React, Svelte gibi çerçeveler kullanılmadı. Şartnamenin gerekçesi: ekranlar "form + tablo + birkaç basit SVG"dir; çerçeve bakım yükü ve bağımlılık getirir, kazancı yoktur. Bunun pratik sonucu şu kalıptır:

1. **Saf render fonksiyonu**: bir "görünüm modeli" (VM, view model) nesnesi alır, HTML metni döndürür. Örnek: `renderMonitor(vm): string`. Bu fonksiyon hiçbir yan etki yapmaz; aynı girdi her zaman aynı HTML'i verir. Bu yüzden test edilmesi kolaydır.
2. **Ekran bağlayıcısı (`mount`)**: Rust komutlarını çağırır, sonucu bellekteki durum nesnesine yazar, render fonksiyonunu çağırıp `main.innerHTML = …` ile ekrana basar ve tıklama olaylarını dinler.
3. **Olay delegasyonu**: her düğmeye ayrı dinleyici bağlanmaz. Düğmelerde `data-action="…"` gibi öznitelikler vardır; ekranın kök elemanındaki tek `onclick` hangi düğmeye basıldığını `closest("[data-action]")` ile bulur.

Bu kalıpta durum değişince ekranın ilgili kısmı baştan çizilir ("repaint"). Kullanıcı yazarken odağın kaybolmaması için Yeni arz girişi ekranı odaktaki alanı ve imleç konumunu çizimden önce kaydedip sonra geri yükler.

### Ön ucun yapmadıkları

- **Hesap yapmaz.** Olasılık, ortalama, oran, fark üretmez (§8.6).
- **Ağa çıkmaz.** İnternet isteği yoktur; bağımlılıklar ve güvenlik politikası bunu sınar (§8.10, U34).
- **Dosya yazmaz.** Bütün dosya işlemleri Rust komutlarındadır. Ön uç yalnız dosya seçici penceresini açar (`@tauri-apps/plugin-dialog`).
- **git'e yazmaz.** Commit ve push komutları ekranda kopyalanabilir metin olarak durur; uygulama onları çalıştırmaz.

### Dizin düzeni

| Yol | Ne |
|---|---|
| `app/index.html` | Tek HTML sayfası; `#app` kökü, eski `styles.css`, `main.ts` |
| `app/src/main.ts` | Açılış ve görünüm yönlendirmesi (SADE / AYRINTILI) |
| `app/src/api.ts` | Rust komutlarının tipli sarmalayıcıları |
| `app/src/state.ts` | Bellekteki uygulama durumu (`store`) |
| `app/src/types.ts` | Rust çıktılarının TS tipleri (alan adları serde ile aynı) |
| `app/src/dom.ts` | `esc`, `el`, hata kutusu |
| `app/src/i18n/tr.ts` | Bütün arayüz metinleri |
| `app/src/render/*.ts` | Eski (ayrıntılı) görünümün saf render fonksiyonları; `format.ts` ve `svg.ts` iki görünümün ortak araçları |
| `app/src/screens/*.ts` | Eski görünümün ekran bağlayıcıları |
| `app/src/sade/` | Sade görünüm: kabuk `app.ts`, `api.ts`, `state.ts`, `types.ts`, `fonts.ts`, `sade.css`, `render/*.ts`, `screens/*.ts` |
| `app/src/dev/` | Yalnız geliştirme: ekran görüntüsü koşusu (`demo.ts`, `dialog-demo.ts`) |
| `app/tests/` | vitest testleri, fixture'lar, uçtan uca bash betikleri |
| `app/scripts/` | `dev.sh`, `test.sh`, `env.sh`, `screens*.sh` |

Kaynak dosyalar: `docs/app/SPEC_APP.md` §1.1, §6; `app/README.md`; `app/index.html`; `app/package.json`; `app/vite.config.ts`.

---

## 8.2 Açılış, iki görünüm ve yönlendirme

### İki görünüm

Uygulamanın iki arayüzü vardır:

- **Sade görünüm** (`SADE`, varsayılan): 3 Ekim 2026'da onaylanan yeni tasarım. Koyu zemin, az sayıda öne çıkan sayı, bir "Monitör" ana ekranı, seri hesaplayıcı.
- **Ayrıntılı görünüm** (`AYRINTILI`): uygulamanın ilk arayüzü. Bütün modeller, bütün hücreler, bütün kurallar yan yana. Açık renkli, sol gezinmeli.

Seçim `config.json` dosyasındaki `ui_view` alanında durur. Alan yoksa Rust `SADE` sayar; böylece görünüm alanı eklenmeden önce yazılmış eski ayar dosyaları da sorunsuz okunur ("geriye uyumlu").

### `main.ts` adım adım

1. Sayfa yüklenince (`DOMContentLoaded`) `#app` köküne "Yükleniyor…" yazılır.
2. Üç Rust komutu **paralel** çağrılır: `app_info` (sürüm, gömülü modeller, bütünlük), `get_config` (ayarlar ve repo durumu), `score_hints` (skor dosyasından model kartı ipuçları). Biri hata verirse sonucu `null` olur; uygulama yine açılır.
3. Sonuçlar `store.info`, `store.config`, `store.hints` alanlarına yazılır.
4. Sade görünümdeysek ve repo modu açıksa `loadMonitor()` bir kez çağrılır; üst bardaki "Veri" tarihi buradan gelir.
5. `render()` çağrılır: `isSade()` doğruysa `mountSade(root, sadeHost)`, değilse `unmountSade` ve `renderDetailed`.

`isSade()` yalnız `config.ui_view !== "AYRINTILI"` kontrolüdür. Bir istisna var: eski ekran görüntüsü koşusu (`VITE_BORSAI_DEMO=1`, `VITE_BORSAI_DEMO_V2` yok) her zaman ayrıntılı görünümü sürer, çünkü o koşunun adımları eski düğmelere tıklar.

### Görünüm değiştirme

`setView(view)` Rust'ın `set_ui_view` komutunu çağırır; komut `config.json`'a yalnız bu alanı yazar ve güncel ayarı döndürür. Yazılamazsa (ör. uygulama verisi dizini yok) seçim yalnız bu oturum için bellekte değişir.

Geçişin üç yolu vardır:

- Sade ekranlardaki "Ayrıntılı görünüm" bağlantıları (`data-detailed="<eski ekran>"`): kalıcı olarak ayrıntılıya geçer ve karşılık gelen eski ekranı açar.
- Ayarlar'daki "Görünüm" seçimi (iki radyo düğmesi).
- Ayrıntılı görünümün sol gezinmesinin sonundaki "Sade görünüme dön" düğmesi.

### Ayrıntılı görünümün kabuğu

`renderDetailed` üç parça çizer: üstte **mod bandı** (§8.11), solda yedi düğmeli gezinme (Girdi, Sonuç, Doğruluk, Sicil, Kişisel kayıtlar, Ayarlar, Hakkında) ve "Sade görünüme dön", altta sabit `DISCLAIMER` satırı. Seçili ekranın `mount` fonksiyonu ortadaki `<main>`'e bağlanır.

### Sade görünümün kabuğu (`sade/app.ts`)

`render()` her ekran değişiminde kabuğu baştan kurar: üst bar (`renderTopBar`), ekran alanı (`<main class="s-screen">`), alt bilgi (`renderFooter`). Sonra `sade.screen` değerine göre dokuz ekrandan birinin `mount`'u çağrılır: `monitor`, `giris`, `sonuc`, `analiz`, `perf`, `sicil`, `kayitlarim`, `ayarlar`, `sihirbaz`.

Kabuk düzeyindeki olaylar tek yerde yakalanır:

| Öznitelik / olay | Ne yapar |
|---|---|
| `data-go="<ekran>"` | Sade ekrana geçer. `analiz` ise önce seçili arzı boşaltır; böylece "Analiz" sekmesi hep listeyi açar (K-FIX-1). |
| `data-detailed="<eski ekran>"` | Ayrıntılı görünüme geçer. `registry` ise ve bir arz açıksa, eski sicil ekranı o arzın kayıt sayfasıyla açılır. |
| Arama kutusunda Enter | Kod büyük harfe çevrilir (`toLocaleUpperCase("tr")`, Türkçe İ/ı kuralıyla). Monitör satırlarında yoksa "…: takipteki arzlarda yok" yazar; varsa Analiz'de o arzı açar. |
| 30 saniyelik zamanlayıcı | Üst bardaki yerel saati yeniler (yalnız gösterim). |

`unmountSade` ayrıntılıya geçerken kök sınıfı ve dinleyicileri kaldırır, saati durdurur.

### İki dünya arasındaki eşleme

Sihirbazlar ve iptal sayfası gibi bazı ekranlar sade görünümde yeniden yazılmadı; eski ekranın kendisi sade kabuğun içinde açılır. Eski ekranlar `navigate("inputs")` gibi eski kimliklerle gezinir. İki eşleme fonksiyonu bunu çevirir:

| Eski ekran (`ScreenId`) | Sade ekran (`sadeScreenOf`) |
|---|---|
| `inputs` (Girdi) | `giris` |
| `results` (Sonuç) | `sonuc` |
| `scenarios` (Kişisel kayıtlar) | `kayitlarim` |
| `settings`, `about` | `ayarlar` |
| `accuracy` (Doğruluk) | `perf` |
| `registry` (Sicil) | sicil listesindeyse `sicil`, kayıt sayfası ya da sihirbazdaysa `sihirbaz` |

Ters yön (`legacyScreenOf`) mod göstergesi içindir (§8.11).

Kaynak dosyalar: `app/src/main.ts`; `app/src/sade/app.ts`; `app/src/sade/ctx.ts`; `app/src/sade/api.ts` (`setUiView`); `docs/prompts/FAZ9_APP_UI.md` K-UI-1; `docs/app/UI_V2_HARITA.md` (`set_ui_view`, `AppConfig.ui_view`).

---

## 8.3 Durum yönetimi

**Durum** (state), ekranın o anki hâlini belirleyen verilerdir: hangi aşama seçili, son tahminin çıktıları, hesaplayıcıda hangi gün seçili. BorsAi'de durum iki düz JavaScript nesnesinde tutulur; Redux gibi bir kütüphane yoktur.

### Kalıcı olan yalnız Rust'ın yazdığıdır

Uygulama kapatılınca bellekteki her şey gider. Kalıcı olan yalnız Rust'ın uygulama verisi dizinine yazdığı iki şeydir: `config.json` (ayarlar, görünüm seçimi) ve `scenarios/*.json` (kişisel kayıtlar). Resmi sicil uygulama verisinde değil, repodadır ve her açılışta yeniden okunur.

### `store` (`state.ts`)

İki görünümün ortak durumu:

| Alan | İçerik |
|---|---|
| `info`, `config`, `hints` | Açılışta okunan `app_info`, `get_config`, `score_hints` |
| `form` (`FormState`) | Girdi formu: aşama, 20 alanın metin değerleri, arz etiketi, son `check_form` sonucu, sicilden doldurma listesi, f6 modu ve değeri, meşgul/hata |
| `results` (`ResultsState`) | Son tahmin: bütün modellerin çıktıları (`runs`), girdiler, tarihler, aşama, f6 bloğu, kaynak (`FORM` ya da `SCENARIO`), açılan kişisel kaydın başlığı, saklanınca kayıt kimliği |
| `view` (`ViewState`) | Eski sonuç ekranının görünümü: gizlenen modeller, açık kart, seçili j, sekme ve kullanıcı beyanı (`declared`, on gün için doğru/yanlış) |
| `accuracy` | Eski doğruluk panelinin verisi ve açık blokları |
| `registry` | Eski sicil ekranı: `list` / `record` / `wizard` / `post_d1` hâli, seçili arz ve kayıt, kayıttan gelen tavan görünümü |
| `freeze`, `postD1Wizard` | İki sihirbazın taslakları |

Birkaç yardımcı fonksiyon da buradadır:

- `resultsFromScenario`: kişisel kayıttaki çıktıları olduğu gibi `ResultsState`'e çevirir. **Yeniden hesaplamaz** (U36): kayıt farklı bir model kümesiyle üretildiyse bile eski çıktı gösterilir.
- `resetView`: yeni tahminde görünümü sıfırlar; kayıttan gelen beyanlardan yalnız `"CEILING"` ("seri sürüyor") türünü kabul eder, ötekileri atar ve bunu not eder (U52-2).
- `scenarioRequestWithoutDeclaration`: sade görünümün kişisel kayıt isteği; beyan alanı her zaman `null`.

### `sade` (`sade/state.ts`)

Yalnız sade görünümün durumu: açık ekran, Analiz'in arzı, Monitör/kapı/performans verileri ve hataları, Monitör'de seçili satır ve süzgeç (`ALL` / `STREAK`), Analiz'in verileri ve hesaplayıcı j'si (`arzJ`; `null` = bültende gözlenen j), Tahmin sonucunun j'si (`sonucJ`, varsayılan 0), Sicil'in seçili arzı ve sekmesi, arama mesajı.

Sade ekranlar Monitör verisini paylaşır: Analiz'in arz değiştiricisi ve Sicil'in sayımları `sade.monitor`'dan okunur; yoksa önce `loadMonitor()` çağrılır. Ayarlar kaydedilince (repo değişmiş olabilir) bu önbellekler boşaltılır.

Kaynak dosyalar: `app/src/state.ts`; `app/src/sade/state.ts`; `app/src/sade/screens/ayarlar.ts`; `docs/app/SPEC_APP.md` §2.4, §3c.

---

## 8.4 Rust'a köprü: `api.ts`, `types.ts`, `dom.ts`

### Komut çağrısı

Ön uç Rust'a `invoke(komutAdı, argümanlar)` ile ulaşır. Rust tarafında her komut `#[tauri::command]` ile işaretli bir fonksiyondur ve `Result<T, AppError>` döndürür. Tauri argüman adlarını JavaScript'in `camelCase` biçiminden Rust'ın `snake_case` biçimine çevirir; bu yüzden TS'te `ipoPriceTl`, Rust'ta `ipo_price_tl` yazılır.

`api.ts` her komutu tipli bir fonksiyona sarar. Örnek:

```ts
ceilingDisplay: (models, j, ipoPriceTl) =>
  invoke<CeilingDisplay>("ceiling_display", { models, j, ipoPriceTl }),
```

Sade görünümün yeni komutları ayrı dosyadadır (`sade/api.ts`): `monitor_view`, `arz_view`, `break_view`, `perf_view`, `headline_gate`, `set_ui_view`.

Komutların kabaca grupları:

| Grup | Komutlar |
|---|---|
| Uygulama ve ayar | `app_info`, `get_config`, `set_config`, `validate_repo`, `set_ui_view` |
| Girdi ve tahmin | `check_form`, `list_input_documents`, `read_input_document`, `market20_via_python`, `predict_all` |
| Tavan serisi | `ceiling_display`, `ceiling_summary`, `record_summary`, `record_ceiling`, `streak_view` |
| Tavan yolu (Faz 4) | `path_display`, `path_params`, `path_conditional` |
| Kişisel kayıt | `save_scenario`, `list_scenarios`, `load_scenario`, `delete_scenario`, `export_scenario`, `export_all_scenarios` |
| Skorlar | `score_hints`, `scores_view`, `scores_post_d1_view`, `scores_oot_view`, `scores_oot_model` |
| Sicil ve dondurma | `registry_view`, `read_record_json`, `freeze_preflight`, `copy_source_docs`, `read_source_manifest`, `preview_inputs_doc`, `write_inputs_doc`, `inputs_pit_check`, `freeze_record`, `cancel_record` |
| D1 sonrası | `post_d1_records`, `post_d1_view`, `post_d1_preflight`, `post_d1_freeze`, `post_d1_cancel`, `post_d1_todo` |
| Sade görünüm | `monitor_view`, `arz_view`, `break_view`, `perf_view`, `headline_gate` |

Dikkat çekici bir ayrıntı: `ceiling_summary`, `record_summary` ve `streak_view` imzalarında **kullanıcı beyanı parametresi yoktur**. Bu bilinçli bir sınırdır (U52-5): beyan Rust'a hiçbir yoldan gidemez, dolayısıyla hiçbir hesaba giremez.

### Tipler (`types.ts`)

`types.ts` Rust çıktılarının TS karşılığıdır; alan adları Rust'taki `serde` adlarıyla birebir aynıdır. Örnek: bir modelin tek çalıştırması

```ts
interface ModelRun {
  model_id: string; params_sha256: string; kind: Kind;
  status: "PREDICTED" | "REFUSED" | "ERROR";
  refusal: Refusal | null; output: ModelOutput | null;
}
```

İlginç bir tip `Num = number | string`'dir. JSON standardında sonsuz ve NaN (sayı değil) yoktur; Rust bunları `"NaN"`, `"Infinity"`, `"-Infinity"` metni olarak gönderir. Ayrıca skor dosyasındaki gerçekleşen getiriler tam ondalık **metin** olarak gelir. `format.ts`'teki `toNum` ikisini de okur.

### Hata kutusu ve kaçış (`dom.ts`)

Rust bir hata döndürünce `invoke` reddedilir. `asAppError` gelen şeyi `{code, message, detail?}` biçimine getirir. `renderError` kodun Türkçe karşılığını `ERROR_TEXT`'ten bulur, kodu yanında yazar ve ham çıktıyı katlanır bir "Ham çıktı" kutusuna koyar. Böylece hata hiçbir ekranda sessizce kaybolmaz (şartname §3: "boş, kapalı, hata" üç hâli).

`esc` fonksiyonu HTML'e giren her metni kaçırır (`&`, `<`, `>`, `"`, `'`). Metinler `innerHTML` ile basıldığı için bu zorunludur: bir arz adında `<` olsa bile sayfa bozulmaz, betik çalışmaz.

Kaynak dosyalar: `app/src/api.ts`; `app/src/sade/api.ts`; `app/src/types.ts`; `app/src/sade/types.ts`; `app/src/dom.ts`; `app/README.md` "Tauri komutları".

---

## 8.5 Bağımsız mod ve repo modu

Uygulama iki modda çalışır:

- **Repo modu**: Ayarlar'da bir repo klasörü bağlanmış ve doğrulanmıştır. Uygulama sicili, sonuç dosyalarını (`data/outcomes/<T>.csv`), skor dosyalarını ve TÜFE tablosunu doğrudan repodan okur; resmi kayıt için Python'u çağırabilir.
- **Bağımsız mod**: repo yoktur. Modeller derlemeye gömülü olduğundan tahmin yine çalışır; skorlar ve TÜFE için derleme anındaki gömülü kopyalar kullanılır.

Repo doğrulaması (`validate_repo`) şu satırları denetler: repo dizini var mı; uygulama verisi repo dışında mı (içindeyse `DATA_DIR_INSIDE_REPO`, çünkü kişisel kayıt sicile karışmamalı); repodaki `models/INDEX.json`'un sha256'sı gömülü INDEX'inkine eşit mi; `git rev-parse HEAD` çalışıyor mu; `python -c "import borsai"` repo içinden yükleniyor mu. Bilgi satırları: `data/outcomes` dizini, pinli XU100 ve takvimin son günü, TÜFE tablosunun son ayı ve pini.

Ekranların iki moddaki durumu:

| Ekran | Repo modu | Bağımsız mod |
|---|---|---|
| Monitör, Analiz, Sicil (sade) | çalışır | "Bu ekran repo modu ister" boş durumu ve "Ayarlara git" düğmesi; hiçbir komut çağrılmaz |
| Yeni arz girişi | çalışır; sicilden doldurma ve f6 "Hesapla" açık | çalışır; sicilden doldurma, "Hesapla" ve "Resmi kayıt için hazırla" kapalı |
| Tahmin sonucu, Kayıtlarım, Ayarlar | çalışır | çalışır |
| Model performansı | bütün bölümler | gömülü `scores.json` ile geçmiş test satırları; D1 sonrası, kırılma ve zaman-dışı bölümleri için not |
| Ayrıntılı: Sicil, dondur, D1 sonrası | çalışır | kapalı (repo ister) |

Görev metni (K-UI-13) Model performansını da "repo modu gerekli" listesine koymuştu ama "gömülü skorla çalışan kısımlar çalışabilir" diye izin vermişti; uygulama bu izni kullandı.

Üst barda repo modu kapalıyken küçük bir "Bağımsız mod" etiketi görünür. Ayrıntılı görünümde mod bandının sağında "Repo modu: \<yol\>" ya da "Bağımsız mod (dondur ve doğruluk paneli repo ister)" yazar.

Kaynak dosyalar: `app/src/i18n/tr.ts` (`SETTINGS.checkText`, `SADE.repoRequired*`); `app/src/sade/render/common.ts` (`renderRepoRequired`); `app/tests/sade_invoke.test.ts` ("bağımsız mod" testi); `docs/app/UI_V2_HARITA.md` "Bağımsız mod"; `docs/prompts/FAZ9_APP_UI.md` K-UI-13; `docs/app/SPEC_APP.md` §6.

---

## 8.6 "Ön uç hesap yapmaz" kuralı

### Ne demek?

Ekrandaki her sayı ya bir Rust komutunun çıktısıdır ya da repodaki bir dosyadan (kayıt, sonuç dosyası, skor dosyası) olduğu gibi okunmuştur. TypeScript kodu bir sayıdan başka bir **anlamlı** sayı üretmez: olasılık toplamaz, ortalama almaz, iki değeri bölüp oran çıkarmaz, "1 − p" yazmaz.

İzin verilen dört işlem vardır:

1. **Biçimlendirme**: 0.914'ü "%91" yazmak için 100 ile çarpmak gösterim ölçeğidir, yeni bilgi değildir. Bu çarpma yalnız `render/format.ts`'te bulunur.
2. **Piksel koordinatı**: bir olasılığı 250 piksellik eksende konumlandırmak için ölçeklemek. Yalnız `render/svg.ts`'te.
3. **Karşılaştırma ve seçme**: `x < 0` ise kırmızı yaz, listeden `model_id === "base_km_last10"` olan satırı bul, tarihleri metin olarak sırala.
4. **Metin işlemi**: tarih metnini "17.09.2026" biçimine çevirmek, bir değerin "-" ile başlayıp başlamadığına bakmak.

"Beklenen seri", "medyan", "en olası gün", koşullu olasılıklar, Monitör'deki sayımlar ("D10'da arz altında 2 / 7"), performans ekranındaki "3 satırda model daha iyi" sayımı... bunların hepsi Rust'ta üretilir. Rust da bunları skor hesaplamadan üretir: modelin dondurulmuş çıktısından türeyen gösterim değerleridir (ör. beklenen L = Σ l·P(L = l)) ya da dosyadaki satırların sayımıdır.

### Neden?

- **Tek gerçekleme.** Modelin tanımı Python'dadır; Rust onun birebir portudur ve her `cargo test`'te Python'un ürettiği "altın vektörlerle" |Δ| ≤ 1e-9 içinde karşılaştırılır. Ön uçta üçüncü bir hesap yolu olsaydı onun doğruluğunu sınayan bir parite olmazdı.
- **Ekran görüntüsü dürüstlüğü.** Bir sayı ekranda göründüyse, aylar sonra bile hangi komuttan, hangi dosyadan geldiği söylenebilmelidir. Kullanıcı beyanının hiçbir sayıya girmemesi kuralı (U52) da aynı düşüncedir.
- **Skorun tek kaynağı.** Doğruluk hükmü yalnız Python'un ürettiği skor dosyasından gelir (U25). Uygulama bir hücreyi "düzeltse" ya da eksik bir hücreyi "doldursa", şartnamenin küçük-n ve aralık kuralları atlatılabilirdi.
- **Test edilebilirlik.** Render fonksiyonları saf ve hesapsız olunca testler yalnız "Rust'ın verdiği değer doğru biçimde basıldı mı?" sorusunu sorar.

### Nasıl sınanıyor: `no_frontend_math.test.ts`

Bu test kaynak kodu okuyup düzenli ifadelerle (regex) tarar. Önce `split` adlı küçük bir ayrıştırıcı her dosyayı **kod** ve **metin sabitleri** olarak ikiye ayırır: yorumlar atılır, tırnak içindeki metinler ayrı listeye gider, şablon metinlerinin `${…}` içi koda geri döner. Böylece bir yorumdaki "a / b" ya da bir Türkçe cümledeki "/" yanlış alarm vermez. Testin ilk maddesi bu ayrıştırıcının kendisini sınar.

Taramalar:

| # | Ne yasak | Nerede |
|---|---|---|
| 1 | `bootstrap`, `percentile`, `quantile`, `mean(`, `median(`, `average`, `stdev`/`variance`, `.reduce(`, `sum(`, `Math.exp/log/pow/sqrt`, `**` (üs) | bütün `src/**/*.ts` |
| 2 | `*`, `/`, `%` işleçleri | `render/format.ts` ve `render/svg.ts` dışındaki her dosya (import satırları hariç) |
| 3 | `approx_price`, `c_text`, `limit_path_return` alanlarına atama; `q10/q50/q90` ile aritmetik | tavan yolu değerleri yalnız okunur (`types.ts` hariç) |
| 4 | `polygon`, `fill-opacity` | yelpaze grafiğinin bandı yalnız `svg.ts`'te çizilir |
| 5 | `S[…] /` | koşullu olasılık (S_k / S_j) ön uçta bölünmez |
| 6 | `1 - …p_up`, `100 - …`, `p_up` ile aritmetik | düşüş olasılığı (1 − p_up) yalnız Rust'ta |
| 7 | Rust'ta `bootstrap`, `percentile`, `quantile`, `fn mean/brier/rps/mae/accuracy` | `src-tauri/src/**/*.rs` |
| 8 | Türkçe karakter içeren metin sabiti | `i18n/tr.ts` dışında |
| 9 | Yasak sözcükler | `tr.ts` içinde (§8.9) |

Sade görünüm daha da sıkıdır. `sade_static.test.ts`, `src/sade/**` altındaki **hiçbir** dosyada `*`, `/`, `%` bulunmamasını ister (format/svg istisnası burada yok), ayrıca `**`, `.reduce(`, `Math.exp/log/pow/sqrt`, `requestAnimationFrame`, `.animate(` arar. Bu yüzden sade kodda bir çubuğun genişliği bile `fillPct(değer, en_büyük)` çağrısıyla `svg.ts`'e bırakılır.

Doğruluk panelinin testi (U25) öbür yönden de bakar: sentetik skor dosyasındaki her `model_value` ve `rule_value` biçimlendirilmiş hâliyle DOM'da (sayfanın belge ağacında) aranır ve bulunmalıdır. Yani ekran dosyadaki sayıyı göstermek zorundadır, kendi sayısını değil.

### Sınırlar (dürüst not)

Bu tarama bir regex taramasıdır; anlamı kanıtlamaz. Örneğin `Math.max` ve `Math.min` yasak listede değildir ve sade kodda kullanılır: Tahmin sonucundaki getiri çubuklarının en uzununu bulmak için (`Math.max(...|getiri|)`), Model performansında aralık ekseninin uçlarını seçmek için. Bunlar ölçek seçimidir, ekrana yazılan bir sayı üretmez; ama kuralın "ruhuna" uyup uymadığına tarama değil, kod incelemesi karar verir. Taramayı tamamlayan ikinci önlem, render testlerinin elle yazılmış sayı kullanmamasıdır: fixture'lar Rust komutlarının gerçek çıktısıdır (§8.25).

Kaynak dosyalar: `app/tests/no_frontend_math.test.ts`; `app/tests/sade_static.test.ts`; `app/tests/helpers.ts` (`split`); `app/tests/accuracy.test.ts` (U25); `docs/app/SPEC_APP.md` §1.1, U25; `docs/app/UI_V2_HARITA.md` "Genel kurallar".

---

## 8.7 Sayı biçimleri (`render/format.ts`)

Bütün biçimlendirme tek dosyadadır. Kurallar şartnamenin §4'ünden gelir ve iki görünümde aynıdır. Tasarım panolarındaki `0,499`, `+%25,52` gibi virgüllü yazımlar **biçim örneği değildir**; uygulama nokta kullanır (fark F25).

### Ana biçimler

| Fonksiyon | Ne için | Kural | Örnek (test) |
|---|---|---|---|
| `pctSigned1` | getiri | işaretli yüzde, 1 ondalık; yuvarlanınca 0.0 çıkarsa işaretsiz `%0.0` | 0.077 → `+%7.7`; −0.0321 → `-%3.2`; −0.00001 → `%0.0` |
| `pct0` | olasılık | yüzde, 0 ondalık | 0.914 → `%91` |
| `pctInt` | Rust'ın yuvarladığı tamsayı yüzde (düşüş kartı) | yalnız `%` eklenir | 16 → `%16` |
| `tl2` | fiyat | 2 ondalık + " TL" | 27.4812 → `27.48 TL` |
| `price2` | tablo hücresindeki fiyat | 2 ondalık, birim başlıkta | `25.52` |
| `points1` | getiri hatası (MAE) | ×100, 1 ondalık + " puan" | 0.030 → `3.0 puan`; 0.0046 → `0.5 puan` |
| `points1Bare` | aralık uçları | aynı, birimsiz | `[-0.9, -0.1] puan` |
| `metric4` | Brier, RPS, isabet | 4 ondalık | `0.1573` |
| `signed4` | katsayı | işaretli 4 ondalık | `+0.9867`, `-1.0007` |
| `fixed1` | gün sayısı (beklenen seri) | 1 ondalık | 3.2811 → `3.3` |
| `short` | uyarı metnindeki özellik değeri | en çok 6 anlamlı hane | |
| `pyRepr` | ipucundaki ham değer | Python `repr(float)` ile aynı | 1e-5 → `1e-05`; 1 → `1.0`; 100 → `100.0` |
| `sha8`, `sha12` | özet (hash) önekleri | ilk 8 / 12 karakter | |

Değer yoksa ya da sayıya çevrilemiyorsa `DASH` (`—`) basılır. `"NaN"` gibi sonlu olmayan metinler olduğu gibi gösterilir; gizlenmez.

**Puan** nedir? Getiri tahmininin hatası (MAE, ortalama mutlak hata) getiriyle aynı birimdedir: 0.030 hata, getiri ekseninde 3 yüzde puanı demektir. "%3" yazmak "göreli %3" diye yanlış okunabileceği için "3.0 puan" yazılır. Brier ve RPS ise birimsiz olasılık hatalarıdır; 4 ondalıkla yazılır.

### Türkçe yazım kuralları

- **Yüzde işareti sayının önünde**: Türkçede doğru yazım `%91`'dir, `91%` değil. İşaretli getiride işaret en başa gelir: `+%7.7`.
- **Ondalık ayırıcı nokta**: Türkçe yazımda ondalık virgüldür, ama şartname noktayı seçmiştir (tablolar Python çıktıları ve kayıt dosyalarıyla aynı görünsün diye). Bu bir uzlaşmadır; F25 bunu açıkça kaydeder.
- **Binlik ayırıcı yalnız sayımlarda**: `countTr` işlem sayısını tr-TR yerel ayarıyla (`Intl.NumberFormat`) yazar: 17885 → `17.885`. Buradaki nokta binlik ayırıcıdır. İşlem sayısı tamsayı olduğu için ondalık noktayla karışmaz, ama aynı ekranda `25.52` (fiyat) ve `17.885` (sayım) bulunabilir; okurken bağlama bakmak gerekir.
- **Tarih**: `dateTr` ISO tarihini gün.ay.yıl yazar: `2026-09-17` → `17.09.2026`; tarih-saat için `22.09.2026 15:19`, saat UTC ise sonuna ` UTC`. `readableDate` okunur tekrar içindir: `17 Eylül 2026` (ay adları `tr.ts`'ten).
- **Büyük sayıların okunur tekrarı**: `readableCount` 312500000 → `312.5 milyon` (birimler bin / milyon / milyar `tr.ts`'ten; en çok 3 ondalık, sondaki sıfırlar atılır).
- **Saat**: `clockTr` yerel saati `03.10.2026 13:20` biçiminde yazar.
- **Ek uyumu**: Türkçe ekler sayıya göre değişir ("D4'te", "D6'da", "D2'de"). `tr.ts`'teki `LOCATIVE` tablosu 1–11 için doğru eki tutar; "seri D4'te bozuldu" gibi metinler buradan kurulur.

Kaynak dosyalar: `app/src/render/format.ts`; `app/tests/format.test.ts`; `app/tests/sade_svg_format.test.ts`; `app/src/i18n/tr.ts` (`LOCATIVE`, `SADE.months`, `SADE.units`); `docs/app/SPEC_APP.md` §4.

---

## 8.8 Grafikler: elle SVG (`render/svg.ts`)

Grafik kütüphanesi yoktur. **SVG** (Scalable Vector Graphics), tarayıcının doğrudan çizdiği, metin olarak yazılan bir vektör grafik biçimidir: `<line x1=… y1=…/>`, `<path d="M10,20 L30,40"/>`, `<rect …/>`. `svg.ts`'teki fonksiyonlar bu metni üretir.

Hepsinde aynı iki dönüşüm vardır: değer → piksel.

```
sx(x) = sol_boşluk + (x − x_min) / (x_max − x_min) × iç_genişlik
sy(y) = üst_boşluk + (1 − y) × iç_yükseklik          (y ∈ [0, 1], olasılık ekseni)
```

SVG'de y ekseni aşağı doğru büyür; `1 − y` bu yüzden vardır. Değer yoksa (`null` ya da sonlu değil) çizgi o noktada kesilir; boşluk uydurulmaz.

| Fonksiyon | Görünüm | Ne çizer |
|---|---|---|
| `lineChart`, `barChart`, `fanChart`, `legend` | ayrıntılı | S_k eğrileri, P(L = k) çubukları, tavan yolu getiri yelpazesi (q10–q90 bandı, q50 çizgisi, limit yolu kesikli) |
| `fillPct`, `progressPct` | sade | CSS genişliği (`"37.5%"`); 0–100'e kırpılır |
| `sparkline` | sade | Monitör'deki 10 seanslık "kıvılcım" çizgisi; arz fiyatı referans çizgisi |
| `distBars` | sade | P(L = l), l = 0..10: 11 çubuk, en olası vurgulu, gerçekleşen l halkalı; yükseklik en büyük çubuğa göre |
| `survivalCurve`, `calcCurve` | sade | hesaplayıcı eğrisi: koşulsuz S_k, seçilen j'ye koşullu eğri, (calcCurve'de) kuralın koşullu eğrisi; geçmiş günler gölgeli, yarın noktası |
| `corridorChart` | sade | Analiz fiyat koridoru |
| `intervalBar`, `intervalTicks` | sade | Model performansında sıfır çizgisi, %95 aralık çizgisi, fark noktası |
| `returnDots` | sade | Analiz getiri noktaları: tahmin halka, gerçekleşen dolu |
| `tradeBar` | sade | işlem sayısı çubuğu; yükseklik Rust'ın 0–1 oranından |

Fiyat koridorunun y ekseni verinin en küçük ve en büyük değerine oturur ve iki yandan %8 pay bırakılır; bu da piksel hesabıdır. Sade grafiklerdeki `draw`, `grow`, `growx`, `fade` sınıfları açılış hareketini tetikler (§8.23).

Kaynak dosyalar: `app/src/render/svg.ts`; `app/tests/sade_svg_format.test.ts`; `docs/app/SPEC_APP.md` §1.1; `docs/app/SPEC_APP_EK2.md` §4.2.

---

## 8.9 Metin kuralları: `i18n/tr.ts`

### Tek kaynak

Arayüzdeki her Türkçe sözcük `app/src/i18n/tr.ts` dosyasındadır (yaklaşık 2100 satır). Başka bir dosyada Türkçe karakter (ç, ğ, ı, ö, ş, ü) içeren bir metin sabiti bulunursa `no_frontend_math` testi kırmızı olur. Neden tek dosya? Yasak sözcük ve "geçiyor" denetimleri tek yerde yapılabilsin; metin değişikliği kodu değiştirmesin; ileride başka dil eklenebilsin.

Dosya dışa aktarımlara (export) bölünmüştür. Başlıcaları:

| Dışa aktarım | Ne |
|---|---|
| `DISCLAIMER` | sabit yer tutucu uyarı |
| `NAV`, `ScreenId` | eski görünümün yedi ekranı |
| `ModelCode`, `CODE_TEXT`, `PB_IDENTITY_NAMES`, `MARKET20_REASON_TEXT` | model ret ve uyarı kodlarının Türkçe metinleri (T-2 tablosu) |
| `ERROR_TEXT` | uygulama hata kodları |
| `STAGES`, `FIELDS`, `F3_DEFINITION`, `FORM_NOTE_TEXT`, `INPUTS`, `F6` | girdi formu |
| `TR` | mod bandı ve genel |
| `RESULTS`, `PATH`, `CEILING`, `COND`, `CARD`, `KIND_TEXT`, `SUMMARY`, `TUFE` | eski sonuç ekranı ve kartlar |
| `REGISTRY`, `FREEZE`, `POST_D1`, `SOURCE_KIND_TEXT` | sicil ve sihirbazlar |
| `VERDICT`, `VERDICT_OOT_SUFFIX`, `ACCURACY` | hüküm eşlemesi ve doğruluk paneli |
| `SADE_NAV`, `SadeScreenId`, `VERDICT_PLAIN`, `VERDICT_MARK`, `SADE` | sade görünüm |

Metinlerin çoğu düz dize değil, küçük fonksiyonlardır: `SADE.calc.dayJ(j, d, p)` → "Seri 3 gün sürdüyse yarın (D4) da tavan olasılığı %67." Sayıları biçimlendirici verir, `tr.ts` yalnız kalıbı tutar.

Sade görünüm eklendiğinde kural şuydu (K-UI-2): `tr.ts`'e yalnız yeni dışa aktarım eklenir, var olan dizeler değişmez. Sunum öncesi düzeltmede (FAZ9_UI_FIX) yalnız `SADE` içindeki iki dize değişti: `analiz.pickNote` ve `perf.stripRowsSub`.

### DISCLAIMER

```
Bu uygulama yatırım tavsiyesi değildir; çıktılar istatistiksel tahmin ve olasılıklardır.
```

Bu dize her ekranın altında durur: ayrıntılı görünümde sabit alt satır, sade görünümde alt bilginin solu. `disclaimer.test.ts` dizeyi harfi harfine sınar. Şartname bunun hukuki metin olmadığını, ürünleşmeden önce hukuki görüşle değiştirileceğini yazar (§4, §8-1). Tavan serisi kartı kendi kopyasını taşımaz; iki kez yazmak sadeleşmeye aykırı sayılmıştır.

### "geçiyor" yalnız hüküm eşlemesinde (U19)

Projenin altıncı kuralı der ki: bir model ancak basit kurala karşı farkın %95 aralığı 0'ı dışlıyorsa "geçiyor" denebilir. Uygulama bu hükmü kendisi vermez; Python'un ürettiği skor dosyasındaki `verdict` alanını basar. Bu sözcüğün başka bir yerden sızmaması için:

- `tr.ts`'te `VERDICT = { pass: "geçiyor", fail: "geçemiyor", undecided: "ayırt edilemiyor", insufficient: "yetersiz örnek", noInterval: "aralık için yetersiz" }` tek eşlemedir. Bu dizeler ekrana basılmak için değil, **renk sınıfı seçmek** için karşılaştırılır; basılan metin dosyadaki alanın kendisidir.
- Test bütün `src/**/*.ts` metin sabitlerinde "geçiyor"u arar: `tr.ts`'te tam **bir** kez, başka hiçbir dosyada sıfır kez geçmelidir.
- Rust kaynağında yalnız `commands/scores.rs` içindeki `pub const VERDICT_PASS: &str = "geçiyor";` satırına izin verilir.
- Render testinde sayfadaki her "geçiyor" bir hüküm hücresinden (`td.verdict[data-verdict]`) gelmelidir; küçük örneklem (n = 12) panelinde hiç geçmemelidir.

Zaman-dışı terazinin eki `VERDICT_OOT_SUFFIX = " (zaman-dışı terazide)"` "geçiyor" içermez; böylece "geçiyor (zaman-dışı terazide)" metni de yalnız dosyadaki verdict + sabit ekten oluşur.

Sade görünüm iki yardımcı ekler, ikisi de verdict'e **anahtar** olarak bağlıdır:

- `VERDICT_PLAIN`: hüküm hücresinin altındaki sade açıklama. "geçiyor" → "Model daha iyi: aralığın tamamı sıfırın altında, model ortalamada daha az hata yaptı." Hüküm hücresinin yerine geçmez; ayrı satırdır (K-UI-5).
- `VERDICT_MARK`: işaretler. ✓ (geçiyor), × (geçemiyor), ≈ (ayırt edilemiyor).

### Yasak sözcükler (U21)

Şartname §4: "kesin", "garanti", "kazandırır", "al/sat", "hedef fiyat", "sinyal" ve tek başına "doğruluk %\<sayı\>" kullanılmaz. Test `tr.ts`'in tamamını küçük harfe çevirip (`toLocaleLowerCase("tr")`) bu sözcükleri arar ve "doğruluk %" ardından rakam kalıbını reddeder. İzinli sözlük: "tahmin", "olasılık", "P(kapanış > arz)", "tavan serisi", "basit kural", "fark", "%95 aralık", "ayırt edilemiyor". Düşüş kartı da "düşer" fiilini değil, "düşme olasılığı" adını kullanır.

Gerekçe: Bu uygulama bir tahmin ve ölçüm aracıdır. "Kesin" ya da "sinyal" gibi sözcükler kullanıcıyı çıktıyı bir alım-satım önerisi gibi okumaya iter; SPK'nın yatırım danışmanlığı çerçevesine de dokunabilir.

### Kodların metinleri (U8)

`ModelCode` bir TS birlik tipidir (union type): modelin döndürebileceği her ret ve uyarı kodu (`INPUT_MISSING`, `F3_MISSING`, `TUFE_MISSING`, `D1_NOT_CEILING`…) burada sayılır. `CODE_TEXT: Record<ModelCode, …>` her koda bir metin fonksiyonu bağlar; bir kod eksikse `tsc` derlemeyi kırar. `codes.test.ts` ayrıca Rust'ın `error.rs` dosyasındaki kod sabitlerini ve şartnamenin T-2 tablosunu okuyup kümelerin uyuştuğunu sınar. Tanınmayan bir kod gelirse ekranda "tanımsız kod: …" yazar; sessizce boş kalmaz.

Kaynak dosyalar: `app/src/i18n/tr.ts`; `app/tests/disclaimer.test.ts`; `app/tests/accuracy.test.ts` (U19 bölümü); `app/tests/no_frontend_math.test.ts` (son iki madde); `app/tests/codes.test.ts`; `app/src/render/codes.ts`; `docs/app/SPEC_APP.md` §3d, §4, U8, U19, U21; `docs/app/UI_FIX_RAPOR.md` §4.

---

## 8.10 U-kuralları: kabul testlerinin haritası

### U nedir?

Şartname (SPEC_APP) ve iki eki, uygulamanın "bitti" sayılması için geçmesi gereken testleri **U1, U2, …** diye numaralar ("U", uygulama kabul testi demektir). Her U satırı üç şey söyler: ne sınanacak, nasıl sınanacak (`cargo test`, vitest ya da bash betiği) ve kanıt ne olacak (test çıktısı, rapor dosyası, ekran görüntüsü). U'lar şartnameye yazıldıktan sonra kod yazılır; böylece "testi koda göre ayarlamak" zorlaşır.

Numaralar üç belgeye dağılmıştır: SPEC_APP §5 (U1–U40 ve sonradan eklenen U52), EK 2 §6 (U41–U51, Faz 4 tavan yolu modelleri), EK 3 §10 (U53–U80, tavan hazard v1, TÜFE, D1 sonrası, zaman-dışı panel, düşüş kartı). Toplam 80 numara vardır; aşağıda gruplanmış hâlleri ve ön ucu doğrudan ilgilendirenlerin ayrıntısı var.

### Gruplar

| Aralık | Konu | Ön ucu ilgilendiren özü |
|---|---|---|
| U1–U6 | Rust ↔ Python paritesi | Altın vektörler (model başına ≥ 200 girdi), \|Δ\| ≤ 1e-9, resmi kayıtlarla parite. Ön uç değil, Rust testi. |
| U7–U12 | Ret ve uyarı kodları | f3 boşken ret eden modeller ret bloğu gösterir, ötekiler dolu (U7); her kodun Türkçe metni var (U8); kırpılan hücrede `⌐` (U10); uyarılar hiçbir hücreyi gizlemez (U11); bozuk parametre dosyası tahmini kapatır (U12). |
| U13–U26 | Doğruluk paneli gösterimi (SPEC_SCORING §7–§8) | Başlıklar (U13), iki terazi ayrı (U14), metrik satırı alanları ve "puan" (U15), küçük-n üç hâli (U16–U18), "geçiyor" (U19), isabet oranı tek başına yok (U20), model kartı ve yasak sözcükler (U21), birincil hücre (U22), rejim uyarısı (U23), fail-closed (U24), hesap yok (U25), RETRO ayrı (U26). |
| U27–U32 | Dondurma ve kişisel kayıt yalıtımı | Kişisel kayıt repoya yazılamaz (U27–U29), dondurma uçtan uca geçici klonda (U30), ilk işlem günü geçmişse kırmızı uyarı (U31), uygulama git'e yazmaz (U32). |
| U33–U36 | Bütünlük, ağ, şema, senaryo yükleme | Gömülü dosya sha'ları (U33), ağ yok (U34), şema sürümü uyuşmazlığında kısmi gösterim yok (U35), eski kümeyle saklanmış senaryo sarı uyarıyla ve üzerine yazılmadan açılır (U36). |
| U37–U40, U52 | Koşullu tavan güncellemesi | Koşullu değerlerin paritesi 1e-12 (U37), resmi görünüm yalnız dondurulmuş S'i kullanır (U38), kullanıcı beyanı hiçbir skora ve sicile girmez (U39), şerit ve tanımsız durumlar (U40), beyandan türetilmiş hiçbir sayı arayüzde yok (U52). |
| U41–U51 | Faz 4 tavan yolu modelleri | Port, parite 19/19, Grup A ve Grup C render (U48), "Getiri (koşullu)" sekmesi (U49), doğruluk panelinde tavan yolu blokları (U51). |
| U53–U63 | Tavan hazard v1, TÜFE, "Tavan serisi" kartı | Parite 23/23, TÜFE kaynağı ve "ay eksik" engeli (U57), kart render (U60), öne çıkarma kuralı (U61), resmi görünümde yalnız kayıt (U62), U7'nin güncel sayıları (U63). |
| U64–U70 | D1 sonrası güncelleme | Parite, bütünlük, "D1 sonrası" satırı (U68), sihirbaz uçtan uca (U69), doğruluk panelinde D1 sonrası skorlar (U70). |
| U71–U75 | Zaman-dışı panel | Üç terazi ayrı (U71), hüküm eki ve renk (U72), fail-closed ve kasa kodlarının hiç gösterilmemesi (U73), kasa alt bölümleri (U74), gerçek dosyayla render (U75). |
| U76–U80 | Düşen arz (D10) ailesi | Referans kilidi, parite 27/27, "Düşüş (D10)" kartı (U79). |

U7'nin hikâyesi model kümesinin büyümesini de gösterir: f3'süz bir arz girdisiyle sonuç ekranı ilk şartnamede **4 ret + 12 dolu** sütun (16 model), EK 2'de **5 + 14** (19 model), EK 3'te **8 + 15** (23 model), P4 portundan sonra commit mesajına göre **10 + 17** (27 model) göstermelidir. Her yeni model, eski sayıyı bilerek değiştiren bir test güncellemesiyle girmiştir.

### Ön uç için en önemli kurallar

**U14 ve U71: terazi ayrımı.** Projenin üçüncü kuralı backtest (geçmiş veri testi), canlı sicil ve zaman-dışı eski kohortun "asla toplanmayacağını" söyler. Ayrıntılı görünümde bunlar üç ayrı renk sınıfıyla (`.panel-backtest` lacivert-gri, `.panel-live` kehribar, `.panel-oot` yeşil-gri) ayrı bölümlerdir; test DOM'da üç sınıfın birbirinin içine girmediğini ve kaynakta üç listeyi birleştiren bir fonksiyon olmadığını sınar. Sade görünümde aynı ilke "Üç ayrı sınav" tablosudur (§8.17).

**U16–U18: küçük örnek.** Canlı sicilde skorlanan arz sayısı (n) 10'dan küçükse yalnız satır tablosu görünür, hiçbir metrik, renk ya da hüküm yoktur. 10 ≤ n < 30 iken metrikler görünür ama her satırda "yetersiz örnek" rozeti vardır ve kazanan rengi yoktur. n ≥ 30'da renkler açılır. Eşikler (`MIN_N_METRIC = 10`, `MIN_N_VERDICT = 30`) skor dosyasının kendi tanımlarıyla aynıdır; uygulama bunları sayıları değerlendirmek için değil, hangi düzenin çizileceğini seçmek için kullanır.

**U24: fail-closed.** "Fail-closed" (hata durumunda kapalı), şüpheli durumda kısmi göstermek yerine hiç göstermemek demektir. Skor dosyası şartnameyle çelişirse (ör. n < 10 iken canlı hücre üretilmiş; n < 30 iken "geçiyor" denmiş; aralık 0'ı içerirken "geçiyor" denmiş; n_live + n_late ≠ n_scored) panel kapanır ve yerine "scores.json şartname kuralına aykırı: \<kural\>" yazar. Uygulama dosyayı düzeltmez.

**U25: hesap yok.** §8.6.

**U27: kişisel kayıt repoya yazılamaz.** Kişisel kayıt ve dışa aktarma hedefi repo klasörünün altındaysa Rust `SCENARIO_PATH_INSIDE_REPO` hatası verir; sembolik bağlar çözülerek denetlenir. Ön uç hedefi yalnız dosya seçiciden alır, kendisi denetlemez.

**U32: git yalnız okunur.** Rust'ta `git` yalnız `rev-parse`, `status`, `log`, `ls-files` alt komutlarıyla çağrılabilir; commit/push komutları ekranda kopyalanacak metindir.

**U34: ağ yok.** Dört katmanda sınanır:

1. `package.json`'un çalışma zamanı bağımlılıkları yalnız `@tauri-apps/api` ve `@tauri-apps/plugin-dialog`'dur. `package-lock.json`'da `axios`, `node-fetch`, `@tauri-apps/plugin-http` yoktur.
2. `Cargo.lock` taraması: `reqwest`, `ureq`, `hyper`, `tauri-plugin-http` macOS hedefinde derlenmez. (Kilit dosyasında `reqwest`/`hyper` adları geçer, çünkü Tauri bunları yalnız Android/iOS için bildirir; test bu yüzden `cargo metadata --filter-platform aarch64-apple-darwin` ile bakar.)
3. **CSP** (Content Security Policy, içerik güvenlik politikası): tarayıcı motoruna "bu sayfa nereden kaynak yükleyebilir, nereye bağlanabilir" diyen kural dizisidir. `tauri.conf.json`'daki politika `default-src 'self'; connect-src 'self' ipc: http://ipc.localhost; img-src 'self' data:; style-src 'self' 'unsafe-inline'`'tır. `connect-src` yalnız uygulamanın kendisine ve Tauri'nin iç iletişim kanalına (IPC) izin verir; bir `fetch("https://…")` motor tarafından engellenir. Test bu iki yönergenin varlığını sınar.
4. Tauri yetenekleri (`capabilities/default.json`) yalnız `core:default` ve `dialog:default`'tur; dosya sistemi, kabuk ve HTTP eklentileri yoktur.

Sade görünümün yazı tipleri de bu kurala uyar: `@fontsource` paketleri yalnız geliştirme bağımlılığıdır, Vite yazı tipi dosyalarını pakete gömer; `sade.css`'te ve `index.html`'de `http(s)://` ya da `@import` bulunmaz (`sade_static.test.ts`).

**U38 ve U62: resmi görünüm yalnız kayıttan.** Bir arzın resmi sayfasında (sade Analiz, ayrıntılı arz sayfası) tavan olasılıkları dondurulmuş kayıttaki `models[].output.S` vektöründen gelir; model yeniden çalıştırılmaz. Test bunu ustaca sınar: kayıttaki S kasten 0.5^k yapılır (modelin asla üretmeyeceği bir eğri); ekrandaki koşullu değerler 0.5^(k−j) çıkmalı ve `predict_all` hiç çağrılmamalıdır.

**U52: beyandan sayı yok.** Ayrıntılı görünümde kullanıcı bir güne tıklayıp "seri sürüyor" beyanı girebilir (resmi kapanış henüz dosyada yokken). Proje sahibinin 23 Eylül 2026 kararıyla bu beyan **yalnız etikettir**: şeritte turuncu çerçeve olarak görünür, hiçbir olasılığa girmez. Test, beyanlı j ile çıkacak bütün sayıları aynı Rust fonksiyonlarıyla üretip biçimlendirir, sonra ekranın tamamında (metin, `title`, `data-*`, SVG metinleri) bunlardan **hiçbirinin** geçmediğini arar. Pozitif kontrol olarak aynı gün resmen tavan yapılınca aynı sayıların göründüğü de sınanır; yani arama gerçekten sayı bulabilmektedir. Sade görünümde beyan şeridi hiç yoktur (K-UI-8).

Kaynak dosyalar: `docs/app/SPEC_APP.md` §5; `docs/app/SPEC_APP_EK2.md` §6; `docs/app/SPEC_APP_EK3.md` §10; `app/tests/no_network.test.ts`; `app/src-tauri/tauri.conf.json`; `app/src-tauri/capabilities/default.json`; `app/tests/u52_declaration.test.ts`; `app/tests/accuracy.test.ts`; `app/tests/accuracy_oot.test.ts`; `app/README.md` "Bilinen sapmalar"; `GITLOG.txt` (P34_C3 commit'i).

---

## 8.11 Sade görünüm: ortak kabuk ve ortak parçalar

### Üst bar

Soldan sağa: marka ("BorsAi"), beş sekme (Monitör, Analiz, Model performansı, Sicil, Kayıtlarım), kod arama kutusu, mod göstergesi, bağımsız moddaysa "Bağımsız mod" etiketi, veri tarihi ("Veri 03.10.2026" gibi; Monitör'ün `data_date` alanı, sonuç dosyalarındaki en geç seans günü) ve yerel saat, birincil mavi "Yeni arz gir" düğmesi ve Ayarlar dişlisi. Bar sayfa kayarken üstte kalır (`position: sticky`). Yeni arz girişi, Tahmin sonucu ve Ayarlar sekme değildir; sihirbaz açıkken "Sicil" sekmesi vurgulu kalır.

### Mod göstergesi

Eski görünümün mod bandıyla **aynı fonksiyondan** gelir (`render/shell.ts: bandFor`). Sade ekran önce eski karşılığına çevrilir (`legacyScreenOf`), sonra aynı tablo uygulanır (K-UI-12):

| Sade ekran | Gösterge | Açıklama (ipucunda) |
|---|---|---|
| Yeni arz girişi, Tahmin sonucu, Kayıtlarım | SENARYO | Bu tahmin sicile girmez |
| Analiz, Sicil | RESMİ KAYIT | sicil (salt okuma) |
| Sihirbaz | RESMİ KAYIT | "hazırlanıyor · Dondur gerçek repoya yazar", D1 sonrası sihirbazı ya da kayıt sayfası metni |
| Model performansı | DOĞRULUK | scores.json'dan salt okuma; uygulama skor hesaplamaz |
| Monitör, Ayarlar | (yok) | |

Metin `tr.ts`'te büyük harfle tanımlıdır ("SENARYO"); sade CSS onu küçük harfe çevirip ilk harfi büyütür ("Senaryo", "Resmi kayıt"). Sade görünümde gösterge zeminsiz küçük bir haptır: senaryo açık mavi, resmi kayıt yeşil, nötr gri çerçeveli. Eski görünümde aynı bilgi tam genişlikte bir banttır ve zemini senaryoda turuncu, resmi kayıtta mavi, nötrde gridir.

### Alt bilgi

Her sade ekranın altında solda `DISCLAIMER`, sağda "BorsAi \<sürüm\>" ve "Hakkında" bağlantısı vardır (`renderFooter`).

### Rejim şeridi

2026 Eylül'ünde piyasada eğitim döneminde görülmemiş bir stres dönemi başladı; proje bunu `FON_KRIZI_2026` rejim etiketiyle işaretler (D1 ≥ 2026-09-16). Şerit koyu kahverengi zeminde turuncu yazıyla ("Fon krizi rejimi" rozeti + "… tarihinde ve sonrasında listelenen arzların ilk seansları eğitim döneminde görülmemiş bir stres penceresine düşüyor…") çizilir. Başlangıç tarihi `scores_break.json`'daki `card.regime_warning`'den gelir; şerit yalnız en az bir arz bu etiketi taşıyorsa görünür (Monitör'de ve o arzın Analiz sayfasında). Tasarımdaki "130 fon tasfiyesi", "BIST100 −%16,65" gibi sayılar dosyalarda olmadığı için çıkarıldı (F8).

### Ana ekran kapısı (`headline_gate`)

Sade görünümün en önemli kuralıdır. Altın renk **yalnız bizim modelimizin çıktısıdır** ve bir çıktı ancak hak ettiyse altın görünür. Hak etmek şudur (K-UI-4): çıktının önceden ilan edilmiş **birincil hücresi** (model dondurulmadan önce "bu modeli şu ölçüde, şu kurala karşı değerlendirin" diye yazılan tek hücre) skor dosyasında "geçiyor" hükmü almış olmalıdır. Birden çok kurala karşı birincil satırlar varsa hepsi "geçiyor" olmalıdır.

Kararı Rust verir. `sade.rs`'teki `HEADLINE_OUTPUTS` sabiti ana ekranların gösterdiği 12 çıktıyı listeler:

| Model | Çıktı | Soru | Skor dosyası |
|---|---|---|---|
| `ceiling_hazard_v0` | S (tavan serisi dağılımı) | Kaç gün tavan | `scores.json` |
| `v1_5_h99` | return D1, D3, D5, D10 | Getiri | `scores.json` |
| `v1_5_h99` | p_up D1, D3, D5, D10 | Arz üstünde mi | `scores.json` |
| `post_d1_hazard_v0` | S_cond | Yarın tavan bozulur mu | `scores_post_d1.json` |
| `break_floor_v0` | p_floor F1, F2 | Yarın da taban mı | `scores_break.json` |

Kırılma modelinin skor dosyasında hüküm alanı yoktur; onun için kapı `card.promotion.promoted` alanına bakar ve etiketi aynen gösterir ("ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = k").

Teslim raporundaki (3 Ekim 2026) gerçek dosyalarla kapının çıktısı: `ceiling_hazard_v0` S öne çıkar (iki birincil satır, ikisi de "geçiyor"); `v1_5_h99` D5 getirisi öne çıkar; öbür getiri ve arz-üstü olasılıkları öne çıkmaz; `post_d1_hazard_v0` öne çıkmaz (n = 0, hücre yok); `break_floor_v0` F1 ön elemeyle öne çıkar, F2 çıkmaz.

Ön uçta bu karar `common.ts: gated(e, değerHtml)` ile uygulanır: öne çıkan değer altın sınıfıyla ve "Önceden ilan edilmiş birincil hücresinin dosyadaki hükmüyle öne çıkar" ipucuyla, öne çıkmayan değer gri, yanında "≈" işaretiyle ve "…dosyada geçmediği için öne çıkmaz" ipucuyla basılır. Değer gizlenmez, yalnız vurgulanmaz.

### Hüküm hücresi

`verdictCell(v)`: işaret (✓ / × / ≈) + dosyadaki `verdict` metni aynen, `data-verdict` özniteliğiyle. Renk sınıfı yalnız "geçiyor" (yeşil) ve "geçemiyor" (kırmızı) için; ötekiler gri. Altına `verdictPlain(v)` sade açıklamayı koyar. Zaman-dışı hücresi (`ootVerdictCell`) aynı hücreye " (zaman-dışı terazide)" ekini ekler; dar panellerde ek ipucuna taşınır.

### Sınıf metinleri

Her resmi kaydın, skorlamada tarihlerden hesaplanan bir **sınıfı** vardır. Ön uç bunu hesaplamaz, dosyadan okur ve Türkçeleştirir:

| Kod | Ekranda | Anlamı |
|---|---|---|
| `LIVE` | canlı | Kayıt ilk işlem gününden önce push kanıtlı; canlı sicil sayısına girer (yeşil çerçeve) |
| `LATE_RECORD` | geç kayıt | Kayıt ilk işlem gününden sonra; canlı sayılmaz |
| `RETRO` | geçmişe dönük | Model sonuç repoya girdikten sonra donduruldu; hiçbir teraziye girmez |
| `MACHINE_SEQUENCED` | makine sıralı | Kırılma akşamı makine kaydı; ayrı ölçek |
| `REFUSED` | ret | Model bu girdiyle tahmin vermedi |
| `SKIPPED` | atlandı | Dondurulmadı; payda satırı olarak durur |
| `PENDING` | bekliyor | Sonuç henüz yok |

Model başına soru adları da sabittir: `ceiling_hazard_v0` → "Kaç gün tavan", `v1_5_h99` → "Getiri", `post_d1_hazard_v0` → "Yarın tavan bozulur mu", `break_floor_v0` → "Yarın da taban mı".

### Basit kural adları

Karşılaştırma kuralları sade dilde adlandırılır: `base_km_last10` "son 10 arzın tablosu", `base_km_expanding` "bütün geçmişin tablosu", `base_train_median` "eğitim medyanı", `base_rate` "taban oranı", `@ZERO` "bütün kırılmaların oranı", `PRODUCT_BREAK_FLOOR` "ürünün eski cevabı". **KM** (Kaplan–Meier), geçmiş arzlarda serinin her gün sürme oranından kurulan model içermeyen bir tablodur; "basit kural" budur.

Kaynak dosyalar: `app/src/sade/render/shell.ts`; `app/src/sade/render/common.ts`; `app/src/render/shell.ts`; `app/src-tauri/src/commands/sade.rs` (`HEADLINE_OUTPUTS`, `PRODUCTION_MODELS`); `app/src/i18n/tr.ts` (`SADE`, `TR`); `docs/app/UI_V2_HARITA.md`; `docs/app/UI_V2_RAPOR.md` §5; `app/tests/sade_render.test.ts` (kabuk ve kapı testleri).

---

## 8.12 Monitör

Monitör sade görünümün ana ekranıdır: "Takipteki arzlar şu an ne durumda?" sorusuna tek bakışta cevap verir. Eski arayüzde karşılığı yoktur; sicil, sonuç dosyaları ve skorlardan derlenir. Repo modu ister.

### Veri

Üç komut paralel çağrılır: `monitor_view` (arz satırları, sayımlar, olaylar), `headline_gate` (altın / ≈ kararı) ve `perf_view` (üretimdeki modeller). `monitor_view` şunları okur: `registry/ipos.csv` (dondurulmuş satırlar), her arzın girdi belgesinden yalnız arz fiyatı ve arz adedi, etkin listeleme öncesi kaydındaki `ceiling_hazard_v0.output.S` ve `v1_5_h99` getirileri, `data/outcomes/<T>.csv` (kapanış, üst limit, tavan bayrağı, getiri metni `R_h`), kırılma akşamı makine kaydı, skor dosyalarının canlı satırları (sınıflar) ve push kanıtı dosyaları. Beklenen ve medyan seri, kayıttaki S'ten eski ekranların kullandığı **aynı** Rust yoluyla (`ceiling::row`) türetilir.

### Ekranın parçaları (yukarıdan aşağı)

1. **Rejim şeridi** (§8.11).
2. **Özet cümlesi**: "7 arz takipte. Şu an tavan serisinde olan yok." + D10'da arz fiyatının altında kapatanların kodları. Sayılar `counts`'tan.
3. **Veri şeridi** (beş okuma, dikey çizgilerle ayrılmış; kart değildir):

| Okuma | Kaynak alan | Not |
|---|---|---|
| Takipteki arz | `n_ipos`; altında ilk ve son D1 | |
| Tavan serisinde | `n_in_streak` | "bugünkü bültene göre" |
| D10'da arz altında | `n_d10_below / n_d10_known` | sıfırdan büyükse kırmızı; altında kodlar |
| Tabanda kırılma | `n_break_floor / n_break_known` | seri taban kapanışıyla bozuldu |
| Üretimdeki model | `perf_view.n_production` (altın) | kendi sorusunda öne çıkan |

4. **Arz takip tablosu** (en yeni ilk işlem günü üstte):

| Sütun | Kaynak | Biçim / renk |
|---|---|---|
| Arz (kod + şirket) | `ticker`, `company` | |
| İlk işlem | `first_trading_date` | `dateTr` |
| Arz fiyatı | `ipo_price` (metin) | `price2` |
| D10 | `d10_close` (metin) | `price2` |
| Arza göre | `r10` (metin, `R_10`) | `pctSigned1`; `r10_below` doğruysa kırmızı, yanlışsa yeşil |
| 10 seans | `days[].close_raw` | kıvılcım çizgisi; arz fiyatı referans; D10 arz altıysa kırmızı, üstüyse yeşil |
| Seri | `streak.realized_l` yoksa `j_observed` | gerçekleşen ya da süren seri uzunluğu |
| Listeleme öncesi tahmin: Beklenen / medyan | `ceiling.expected_l`, `median_l` | kapıdan geçtiyse altın, değilse ≈ |
| Listeleme öncesi tahmin: 5+ gün | `ceiling.p_ge5` (= S_5) | `pct0`; aynı kapı |
| Kırılma | `break_info.b`, `b_floor` | "4. gün taban" (kırmızı) ya da "4. gün taban üstü" |
| Kırılma akşamı: Ertesi gün taban | `break_info.p_floor_f1` | `pct0`, kırılma modelinin kapısı; altında sınıf; yapısal sıfırsa "D10'da arz altına inemez" rozeti |
| Kayıt | `classes[]` | tavan modelinin sınıfı; getiri modelininki farklıysa ikinci satır ("getiri canlı") |

Kayıt yoksa "kayıt yok", model ret ettiyse "girdi eksik (KOD)" yazar. Tablonun altındaki not "geç kayıt"ın ne demek olduğunu ve sınıfın tarihlerden hesaplandığını açıklar.

"Yapısal sıfır" ilginç bir rozet: kırılma günündeki kapanıştan sonra kalan günlerin hepsi taban (−%10) olsa bile 10. gün kapanışı arz fiyatının üstünde kalıyorsa, o arz D10'da arz fiyatının altına **matematiksel olarak** inemez. Rust bunu makine kaydındaki `structural_zero_D10.impossible` alanından okur.

5. **Süzgeç**: "Tümü 7" / "Seride 0". Seride olanlar `streak.in_streak` alanıyla seçilir (karşılaştırma, hesap değil).
6. **Seçili arz paneli** (sağda): son kapanış (büyük), arza göre getiri, büyük kıvılcım, "Seri, model medyanı ve gerçek", kırılma akşamı ertesi gün taban olasılığı, "D5 getiri, tahmin ve gerçek" ve "Analizi aç" düğmesi.
7. **Üretimdeki modeller** (zeminde, ince çizgiyle): dört model için geçmiş test hükmü (kırılma modelinde ön eleme etiketi), eski dönem (zaman-dışı) hükmü, canlı n. Not: "Üç sınav ayrı tutulur, toplanmaz."
8. **Olay akışı**: tarih · kaynak · metin. Olaylar yalnız dosyalardan gelir: listeleme öncesi kayıt yazıldı (aynı gün aynı tür kayıtlar tek satırda birleşir), ardışık tavan günleri ve kapanışları, kırılma günü ve türü, D10 kapanışı ve getirisi, makine kaydı, model donduruldu (push kanıtı zamanıyla), rejim başladı.

### Etkileşim

Satıra tıklamak seçili arz panelini değiştirir; süzgeç tabloyu daraltır; "Analizi aç" ve üst bardaki kod araması Analiz'i açar.

### Çizilmeyenler

Tasarımda olup uygulamada olmayanlar: "Ortalama seri 3,43 / modelin ortalaması 3,67" (ortalama; F1), "en güçlü seyir" (seçim ölçütü; F3), "BIST kapalı" (takvim durumu dosyadan değil; F4), "Canlı sicil 0/30" tek sayısı (modeller arası toplam terazileri karıştırır; F10), "4/30 üretimdeki model" kesrinin paydası (F11), "Kırılma akşamı" süzgeci ("bugün kırılma akşamında mıyız" dosyalardan belirlenemez; F12), "Sistem: canlı skorlama açıldı" olayı (git günlüğü gerekir; F21).

Teslim raporundaki ve testteki (`sade_render.test.ts`) beklenen sayılar: 7 arz; seride 0; D10'da arz altında 2 / 7; tabanda kırılma 3 / 7; üretimde 4. Örnek satır (NETGL): arza göre −%36.2, seri 3, beklenen 3.3 / 3 ve 5+ gün %27 (altın), "4. gün taban", ertesi gün taban %50, kayıt "geç kayıt, getiri canlı".

Kaynak dosyalar: `app/src/sade/render/monitor.ts`; `app/src/sade/screens/monitor.ts`; `app/src/sade/types.ts` (`MonitorView`, `MonitorRow`, `MonitorCounts`, `EventItem`); `docs/app/UI_V2_HARITA.md` pano 1; `docs/app/UI_V2_RAPOR.md` §3–§4; `app/tests/sade_render.test.ts` ("Monitör").

---

## 8.13 Yeni arz girişi

Yeni bir halka arzın belgelerden okunan değerlerini yazıp tahmin aldığın ekrandır. Eski "Girdi" ekranıyla **aynı form durumunu** (`store.form`) ve aynı Rust komutlarını kullanır; yalnız düzen değişmiştir. Bu yüzden bir görünümde yazılan değer öbüründe de görünür.

### Üst panel

- **Aşama**: "Talep toplama öncesi" (`PRE_BOOKBUILD`) ya da "Talep toplama sonrası" (`POST_BOOKBUILD_PRE_LISTING`). Aşama seçilmeden alanlar kapalıdır. Aşama yalnız hangi alanların zorunlu olduğunu belirler; hiçbir modelin davranışını değiştirmez.
- **Arz kodu**: serbest etiket; yazarken Türkçe kurala göre büyük harfe çevrilir.
- **Sicildeki girdi belgesinden doldur** (repo modunda): `list_input_documents` sicildeki `registry/inputs/<T>.json` belgelerini listeler; "Doldur" `read_input_document` ile değerleri ve boş alanların gerekçelerini forma **kopyalar**. Belge değişmez; forma gelen değerler senaryodur.

### Alan grupları

Alanlar belgelerin yayımlanma sırasıyla üç gruba ayrılmıştır. Bu düzen kullanıcının elindeki belgeye göre doldurmasını kolaylaştırır:

| Grup | Belge | Alanlar |
|---|---|---|
| SPK bülteni (8) | İlk halka arzlar tablosu; talep toplamadan önce | planlanan fiyat, mevcut sermaye, yeni sermaye, bedelli, mevcut pay satışı, ek pay satışı tavanı, taban arz, azami arz |
| KAP halka arz sonuçları (8) | Aracı kurumun dağıtım bildirimi; talep toplamadan sonra | halka arz fiyatı, sermaye artırımıyla satılan, satışa sunulan pay, ortak satışıyla dağıtılan, kullanılan ek satış, halka arz büyüklüğü, toplam talep katı (f3), talepte mükerrer ayıklama |
| BIST duyuruları (4) | Payların işlem görmeye başlaması | ilk işlem günü, talep toplama başlangıcı ve bitişi, arz sonrası ödenmiş sermaye |

Talep öncesi aşamada KAP grubunun üstünde "bu aşamada boş kalan alanlar beklenir" notu çıkar.

### Bir alanın anatomisi

Her alan şu parçalardan oluşur: etiket (+ "isteğe bağlı" ya da "bu aşamada boş" etiketi); sağa hizalı değer kutusu ve birim eki (TL, pay, kat); altında **okunur tekrar** ve geçerlilik işareti ✓; denetim notları; Rust'ın önerisi ("öneri: 312500000 · uygula"); sicil belgesinde boşsa gerekçesi ("belgede boş: …").

Okunur tekrar yalnız biçimlendirmedir: `312500000` → "312.5 milyon pay", `2026-09-17` → "17 Eylül 2026", fiyat → "25.52 TL". Tasarımda tarihin yanında haftanın günü de vardı ("Perşembe"); bu bir tarih hesabı olduğu için çizilmedi (F15).

### Anında denetim: `check_form`

Her tuş vuruşunda 180 ms beklenir (debounce: art arda tuşlarda yalnız sonuncusundan sonra çalışma) ve Rust `check_form(aşama, alanlar)` çağrılır. Dönen sonuç:

- `normalized`: virgülü noktaya çevrilmiş, ayrıştırılmış değerler;
- `requirements`: aşamaya göre her alanın durumu (zorunlu / isteğe bağlı / boş beklenir);
- `notes`: alan başına kodlu notlar (`level`: error / warn / info), ör. `REQUIRED_EMPTY`, `PB_IDENTITY`, `SHARES_SUM_MISMATCH`;
- `suggestions`: kesin ondalıkla hesaplanmış öneriler (taban arz = bedelli + mevcut pay satışı; azami arz = taban + ek satış tavanı);
- `model_inputs`: modellere gidecek düz girdi sözlüğü.

Notların metinleri `FORM_NOTE_TEXT`'ten gelir. Hata içeren alanın kenarı kırmızı, uyarı içeren sarı olur.

### Denetim paneli (sağda)

- **Eksik zorunlu alanlar**: `REQUIRED_EMPTY` notu taşıyan alanların adları; yoksa "✓ Eksik zorunlu alan yok."
- **Özdeşlikler**: dört satır.

| Kimlik | Özdeşlik |
|---|---|
| ID-A | Yeni sermaye = mevcut + bedelli |
| ID-B | Taban arz = bedelli + mevcut pay satışı |
| ID-C | Azami arz = taban + ek satış tavanı |
| SUM | Satışa sunulan = artırım + ortak + ek satış |

Her satırın durumu ("✓ tutuyor" / "× tutmuyor") **yalnız Rust'ın notundan** okunur; ön uç toplama yapmaz. Bütün alanlar doluysa altına iki taraf okunur biçimde yazılır ("toplam = parça + parça", her biri `readableCount` ile), ama eşitliği ön uç denetlemez. Tutmayan PB özdeşliği (ID-A/B/C) PB modellerini durdurur. SUM tutmazsa satır yine "× tutmuyor" der ama hiçbir model durmaz; şartnameye göre bu yalnız sarı bir uyarıdır (ret değil).

### Piyasa (f6)

`v1_5_market20_v0` modeli XU100 endeksinin ilk işlem gününden önceki 20 seanslık getirisini (f6) kullanır. Üç seçenek:

- **Hesapla** (repo modu): `market20_via_python` repo içindeki Python'u (`borsai.market20`) pinli XU100 dosyasıyla çalıştırır. Sonuç büyük yazıyla (negatifse kırmızı, değilse yeşil; işaret metnin "-" ile başlamasından anlaşılır) ve S0/S20 tarihleri ile kapanışlarıyla gösterilir. Python ret ederse nedeni `MARKET20_REASON_TEXT`'ten yazılır (ör. pinli dosya bayat).
- **Elle gir**: değer senaryo olarak yazılır.
- **Boş bırak**: model `MARKET20_NOT_PROVIDED` ile ret eder.

Not: "Uygulama ağa çıkmaz; resmi kayıtta bu değeri dondurma adımı kendisi hesaplar." Teslim raporuna göre "Hesapla" bugünü referans aldığından ve pinli XU100 dosyası bugüne yetişmediğinden ekran bir ret nedeni gösterebilir (F26).

### f3 tanımı

"Toplam talep katı nasıl yazılır?" katlanır kutusu şartnamedeki tanımı aynen verir: toplam talep / taban arz (ek satış hariç); belgede kat yazıyorsa o, yazmıyorsa iki toplam açıkça verilmişse bölme önerilir, aksi hâlde boş bırakılır.

### "Tahmin et"

1. f6 "Hesapla" modundaysa ve ilk işlem günü değiştiyse f6 yeniden hesaplanır.
2. `check_form` son kez çağrılır.
3. `predict_all(model_inputs, f6, T)`: gömülü bütün modeller aynı girdiyle çalışır. T'den TÜFE ayı (T'nin ayı − 2) Rust'ta türetilir; TÜFE elle girilmez.
4. Sonuç `store.results`'a yazılır, görünüm sıfırlanır, Tahmin sonucu açılır.

"Resmi kayıt için hazırla" yalnız repo modunda ve bir tahmin yapılmışsa açıktır; dondurma sihirbazını açar (§8.21). Kayda giren değerler tahmin ekranındaki değerlerin aynısıdır.

### Çizilmeyenler

"Taban arzın bileşimi bedelli %71,4 / ortak %28,6" (oran), ilerleme çubuğu ve grup başına "8/8" sayaçları (F13); "Modellerin göreceği değerler" (f1..f6, pb1..pb4): tahminden önce özellikleri veren bir Rust komutu olmadığı için çizilmedi (F14; rapor böyle bir komut önerir).

Kaynak dosyalar: `app/src/sade/render/giris.ts`; `app/src/sade/screens/giris.ts`; `app/src/i18n/tr.ts` (`SADE.giris`, `SADE.fieldLabel`, `FORM_NOTE_TEXT`, `F3_DEFINITION`, `F6`, `MARKET20_REASON_TEXT`); `docs/app/SPEC_APP.md` §3a, §3a.1, §3a.2; `docs/app/UI_V2_HARITA.md` pano 2.

---

## 8.14 Tahmin sonucu

"Tahmin et"ten sonra açılan ekrandır. Bir **senaryodur**: sicile ve doğruluk hesabına girmez. Üst bardaki "Senaryo" göstergesi ve başlığın altındaki cümle bunu her an hatırlatır.

### Veri

Ekran açılınca dört istek paralel gider:

- `ceiling_summary(runs, 0, null, T)`: "Tavan serisi" özetinin satırları (öne çıkan model, adaylar, kurallar, TÜFE bilgisi). Rust bunu `ceiling_display` satırlarından, skor dosyası okuyucularından ve öne çıkarma kuralından (`featured_ceiling`) derler.
- `ceiling_display(S vektörleri, 0, arz fiyatı)`: tavan modellerinin (Grup B: hazard ve KM türleri) S vektörlerinden P(L = l) dağılımı, beklenen ve medyan seri, en olası l.
- `headline_gate` ve `perf_view` (daha önce yüklenmediyse).

Hesaplayıcıda j değişince yalnız `ceiling_display(S, j)` yeniden çağrılır (§8.16).

Birkaç terim: **L** serinin uzunluğudur, yani arzın ilk günden itibaren kaç gün üst üste tavan (günlük üst limit, +%10) kapattığı; 0..10. **S_k = P(L ≥ k)** serinin en az k gün sürme olasılığıdır (S_0 = 1). **P(L = l)** serinin tam l gün sürme olasılığıdır; P(L = l) = S_l − S_{l+1}. Bu dönüşümler Rust'tadır.

Kişisel kayıttan açılan bir tahminde `runs` kayıttaki çıktılardır; model yeniden çalıştırılmaz.

### Ekranın parçaları

**Başlık bölümü.** Yol "Yeni arz girişi / Tahmin sonucu"; başlık "\<KOD\> için tahmin" (kod boşsa "Senaryo tahmini"); alt cümle "\<aşama\>, formdaki değerlerle. Bu bir senaryodur: sicile ve doğruluk hesabına girmez." Sağda "Girdileri düzenle" (kişisel kayıttan açıldıysa değerleri forma kopyalar) ve "Resmi kayıt için hazırla" (repo modunda).

**Manşet cümlesi.** Yalnız kapıdan geçen çıktılardan kurulur (K-UI-4): öne çıkan tavan modeli öne çıkıyorsa "Model bu arz için ortalama 3.3 gün tavan bekliyor. En olası yol 3 gün tavan, 4. gün bozulma."; V1.5 D5 getirisi öne çıkıyorsa " 5. gün getirisi tahmini +%25.5." eklenir. (Sayılar örnek arzın test beklentisidir.) Hiçbiri öne çıkmıyorsa manşet yoktur. "En olası yol" Rust'ın `mode_l` (P(L = l)'nin en büyük olduğu l) ve `mode_break_day` (= mode_l + 1) alanlarıdır.

**"Kaç gün tavan?" paneli.**

- Sağ üstte öne çıkan modelin kimliği (altın, mono yazı).
- Büyük sayı: beklenen seri (`expected_l`, 1 ondalık; kapıdan geçtiyse altın) + "gün bekleniyor, medyan 3".
- **P(L = l) çubukları**: l = 0..10 için 11 çubuk; en olası l altın, öbürleri soluk altın; yükseklik en büyük çubuğa göre. Altında not: "Çubuk k: serinin tam k gün sürme olasılığı. 0: ilk gün tavan yok; 10: on gün boyunca tavan."
- Küçük tablo: "Model" satırı (altın) ve "Basit kural, son 10 arz" satırı (gri; `base_km_last10`) için Beklenen, Medyan, 3+ gün, 5+ gün, 10 gün. 3+ gün = S_3, 5+ gün = S_5, 10 gün = S_10.
- Geçmiş test satırı: "Geçmiş testte hata puanı (RPS): model …, basit kural … (n = …). Hüküm: ✓ geçiyor" ve altında sade açıklama. Değerler `perf_view`'ın bu model ile `base_km_last10` satırından aynen gelir. **RPS** (Ranked Probability Score), sıralı sonuçlar (0, 1, 2… gün) için olasılık dağılımının hatasıdır; küçük olan iyidir.

Tasarımdaki "Geçmiş testte model bu kurala göre hatasını yaklaşık %25 azalttı" cümlesi bir oran hesabı olduğu için çizilmedi; yerine iki değer yan yana ve dosyadaki hüküm durur (F2).

Model bu girdiyle ret ettiyse (ör. f3 yoksa `F3_MISSING`) panelde "… bu girdiyle tahmin vermedi (KOD)." yazar.

**Seri hesaplayıcı.** Panelin yanında; §8.16.

**Getiri tahmini paneli** (`v1_5_h99`):

| Sütun | Kaynak | Not |
|---|---|---|
| Gün | D1, D3, D5, D10 | öne çıkan satır vurgulu |
| Tahmin | `output.Dh.return` | yatay çubuk (genişlik: mutlak getiri / en büyük mutlak getiri, `fillPct`) + `pctSigned1`; kapı |
| Fiyat | `output.Dh.price` | Rust'ın verdiği arz fiyatı × (1 + kırpılmış getiri); ön uç çarpmaz |
| Arz üstü olasılığı | `output.Dh.p_up` = P(kapanış > arz) | `pct0`; kendi kapısı (bugün hep ≈) |
| Geçmiş test | kapı | öne çıkansa "birincil: ✓ geçiyor", değilse "≈ fark net değil" |

Altında `score_hints`'ten: "Geçmiş testte 5. gün tahmininin tipik hatası X puan (ortalama mutlak, n = N)." Şartname "tahmin aralığı" sözünü yasaklar (nokta tahminin etrafında güven aralığı varmış izlenimi vermesin diye); tipik hata cümlesi bu yüzden geçmiş testin ortalama mutlak hatasıdır, aralık değildir.

**Rejim uyarısı paneli.** Sabit metin (U23): modellerin 2023-09-22…2026-08-06 arasında listelenen 99 arzla eğitildiği, D1 tavan oranının yıllara göre değiştiği ve bugünkü rejimin eğitim dönemine benzemeyebileceği.

**"Bu tahminin dayanakları".** Dört satır: uyarı sayısı (öne çıkan tavan modeli ve V1.5'in uyarıları; ayrıntısı ayrıntılı görünümde), TÜFE (reel büyüklük için kullanılan ay ve endeks ya da ret kodu; `ceiling_summary.tufe`), XU100 20 seans (f6 değeri ya da ret nedeni), girdi kaynağı (form ya da kişisel kayıt başlığı). Altında "Ayrıntılı görünüm: bütün modeller ve basit kurallar" bağlantısı.

**"Kişisel kayıt olarak sakla".** Yalnız formdan gelen tahminde görünür. Başlık varsayılanı "\<KOD\>, \<aşama\>". "Sakla" `save_scenario`'yu beyansız bir istekle çağırır; Rust kaydı uygulama verisine yazar ve kimliği döner ("Saklandı: \<kimlik\>"). Not: "Yalnız bu bilgisayarda, uygulama verisine yazılır."

### Boş ve hata hâlleri

Tahmin yoksa "Henüz tahmin yok. Yeni arz girişinde 'Tahmin et'e basın." ve "Yeni arz gir" düğmesi. Gömülü model bütünlüğü bozuksa (açılışta bir modelin sha256'sı INDEX'le tutmamışsa) yalnız kırmızı bant: "Gömülü model dosyası INDEX ile uyuşmuyor; tahmin kapalı." Komut hataları ekranın altında hata kutusunda.

Kaynak dosyalar: `app/src/sade/render/sonuc.ts`; `app/src/sade/screens/sonuc.ts`; `app/src/i18n/tr.ts` (`SADE.sonuc`, `RESULTS.regime`); `docs/app/UI_V2_HARITA.md` pano 3; `app/tests/sade_render.test.ts` ("Tahmin sonucu"); `app/tests/sade_invoke.test.ts`.

---

## 8.15 Analiz

Bir arzın **resmi** sayfasıdır: listeleme öncesi dondurulmuş kayıt, bültenlerden gelen gerçekleşen kapanışlar, kırılma akşamı makine kaydı ve getiriler tek sayfada. Eski görünümde karşılığı Sicil → arz sayfasıdır. Repo modu ister.

### Liste ve yol

Üst bardaki "Analiz" sekmesi her zaman **takipteki arzların listesini** açar (K-FIX-1): kod + şirket, ilk işlem günü ve "Aç"; en yeni ilk işlem günü üstte (ISO tarih metinleri `localeCompare` ile sıralanır, eşitlikte kod sırası). Satır, "Aç", üst bardaki kod araması ya da Monitör'deki "Analizi aç" bir arzı açar.

Arz açıkken yol "Analiz › KOD" olarak görünür; yanında "Tüm arzlar" düğmesi (listeye döner) ve "Başka arz" açılır listesi (arz değiştirici; Monitör satırlarından) durur. Bu düzen, ilk sürümde Analiz'den listeye dönüş yolu olmadığı için sunum öncesi eklendi.

### Veri

Açılışta paralel: `arz_view(T)` (başlık, zaman çizelgesi, koridor, getiriler, günlük), `break_view(T)` (kırılma kartı; yoksa `null`), `streak_view(T)` (bültende gözlenen seri), `headline_gate`, gerekiyorsa `monitor_view`. Sonra seçili j ile `record_summary(T, dosya, j, jGözlenen)` ve `record_ceiling(T, dosya, j)`; arzın D1 sonrası kaydı varsa `post_d1_view(T, j, null)`.

j'nin varsayılanı **bültende gözlenen j**'dir (`streak_view.j_observed`). Burada `predict_all` hiç çağrılmaz: bütün tavan sayıları dondurulmuş kayıttaki S'ten gelir (U38). `sade_invoke.test.ts` bunu çağrı listesine bakarak sınar.

### Başlık

Büyük kod ve şirket adı; sağda altı okuma: Arz fiyatı, D10 kapanış, Arza göre (kırmızı/yeşil), İlk işlem, Tavan serisi ("3 gün"), Arz adedi (okunur, "87.5 milyon"). Altında üç model için sınıf satırları (soru adı + sınıf; örnek arzda "Kaç gün tavan: geç kayıt", "Getiri: canlı") ve arz rejim etiketini taşıyorsa "Fon krizi rejimi" rozeti. (Örnek değerler test beklentisinden.)

### Zaman çizelgesi

Dört adım, soldan sağa:

1. **Listelemeden önce**: kaydın yazıldığı zaman (İstanbul) ve sınıfı; "Beklenen seri X gün" (+ D5 getirisi, yalnız öne çıkıyorsa). Kayıt yoksa "listeleme öncesi kayıt yok"; model ret ettiyse "girdi eksik (KOD)".
2. **İlk gün akşamı** (D1 tarihi): "n D1 sonrası kayıt" ya da "Kayıt yazılmadı".
3. **Kırılma akşamı** (kırılma tarihi): "b. gün tabanda / taban üstünde kapandı" ve "Yarın da taban olasılığı %p" (kapılı). Kırılma yoksa "kırılma kaydı yok".
4. **D10**: "L gün tavan; arza göre r".

### Fiyat koridoru

On seansın fiyat grafiği (`corridorChart`):

- x ekseni: "arz", D1…D10; y ekseni TL.
- Arz fiyatı yatay kesikli gri çizgi ("arz 25.52" etiketiyle) ve x = 0'da nokta.
- Kapanış çizgisi (beyaz), arz fiyatından başlar. Her kapanışta kare işaret: tavan kapanışıysa yeşil, değilse kırmızı, bilinmiyorsa gri.
- Günün üst limiti: yeşil, yarı saydam kısa yatay çentik. Kapanış bu limite eşitse o gün tavandır; işaretin rengi dosyadaki `ceiling_close` bayrağından gelir, ön uç karşılaştırmaz.
- Getiri modelinin beklentisi: kayıttaki `v1_5_h99` fiyatları (D1, D3, D5, D10) altın kesikli çizgi ve eşkenar dörtgen işaretler.
- Kırılma günü: dikey kesikli çizgi, "4. gün kırılma" etiketi; son kapanışın değeri altında yazılı.

Altında üç gün-şeridi:

- "Model: o gün tavan kapanış olasılığı (listeleme öncesi)": kayıttaki `P_close_ceiling[h]` (`pct0`, tavan modelinin kapısıyla). Bu, serinin o güne kadar sürüp o gün de tavan kapatma olasılığıdır; şartnamede "ikincil, türetilmiş" çıktı diye geçer.
- "Gerçekleşen kapanış": tavan / tavan değil / bekliyor (`ceiling_close` = 1 / 0 / yok).
- **İşlem sayısı** (FAZ9_UI_FIX ile eklendi): her gün için küçük gri çubuk ve altında bültendeki toplam sözleşme sayısı (`trade_count_raw` metni, `countTr` ile binlik ayırıcılı). Çubuk yüksekliği Rust'ın verdiği `trade_count_rel` oranıdır (o gün / on günün en büyüğü); ön uç bölmez. Sayı yoksa çubuk çizilmez, tire yazılır. Test beklentisi (örnek arz): D1 17.885, D2 28.445, en büyük gün D9 tam yükseklik.

Tasarımda her gün için ±%10 bant mumları vardı; sonuç dosyasında günün alt limiti olmadığı için yalnız üst limit çentiği çizilir (F16) ve tavan olmayan kapanış "taban" değil "tavan değil" diye yazılır (F17).

### "Kaç gün tavan?" (kayıttan)

Tahmin sonucundaki panelin aynısı, ama S kayıttan (`record_ceiling.display`). Seri bozulduysa gerçekleşen L çubuğu yeşil halkayla işaretlenir ("Gerçekleşen seri işaretli"). Model ve basit kural satırları `record_summary`'den.

### Seri hesaplayıcı (resmi görünüm)

§8.16. Fark: bültende gözlenen seri kutusu ve "Gözlenene dön" düğmesi vardır; D1 sonrası satırı kayıttan gelir.

### Kırılma kartı: "Kırılma akşamı: yarın da taban mı?"

**Kırılma**, tavan serisinin bozulduğu gündür. O akşam (b. gün) `break_floor_v0` modeli ertesi gün (b + 1) taban (−%10) kapanış olasılığını verir. Bu tahmin insan eliyle değil, makine tarafından sıralı üretilir ve `registry/post_break/` altına yazılır. Kart yalnız bu makine kaydından ve `scores_break.json`'dan beslenir; senaryo modunda kırılma tahmini yoktur (Rust portu ayrı bir görevdir).

Kartın içeriği:

- Büyük sayı: "(b+1). gün taban olasılığı" (F1, kapılı); yanında "(b+1). ve (b+2). gün taban" (F2).
- Dört yatay çubuk, karşılaştırma için: Model (altın) · "Tabanda kırılanların oranı" ya da "Taban üstü kırılanların oranı" (kırılma türüne göre geçmiş oran) · "Bütün kırılmaların oranı" (`@ZERO`, özelliksiz model) · "Ürünün eski cevabı" (yoksa "yok"). Çubuklar 0–1 ölçeğindedir.
- Özellik tablosu (Ham değer, Girdi, z, Katsayı): "Kapanış alt limitte" (kapanış ile alt limit metinleri "=" ya da "≠" ile), "ln(işlem adedi / arz adedi)" (kırpıldıysa yıldızlı), "Sabit (C = …)". **z**, değerin eğitim ortalamasından kaç standart sapma uzak olduğudur. Katkı (katsayı × z) hesaplanmaz; yalnız katsayı gösterilir.
- Not: kırpma varsa "* ham X, eğitimin %5'lik sınırına kırpıldı. Eğitim: n kırılma akşamı; ertesi gün taban olan: e."
- Yapısal sıfır: "10. günün en düşük mümkün kapanışı X (altı ardışık taban), arz fiyatı P." ve gerekiyorsa "Bu arz D10'da arz fiyatının altına inemez" rozeti.
- Ön eleme etiketi (`card.promotion_label` aynen), geçmiş testteki kırılma akşamı sayısı ve "Bu arz için sınıf: …".

**Güvenlik kilidi**: katsayılar `models/break_floor_v0.json`'dan okunur, ama yalnız dosyanın sha256'sı makine kaydındaki `params_sha256` ile eşitse. Değilse kart kapanır: "Kırılma kartı kapalı: katsayı dosyasının sha'sı makine kaydındakiyle tutmuyor." Kayıt yoksa "Bu arz için kırılma akşamı makine kaydı yok."

Teslim raporundaki örnek arz değerleri: F1 %50, F2 %30 (≈), taban kırılması sınıf oranı %54, `@ZERO` %30, ürün yok; katsayılar +0.9867, +0.0629, sabit −1.0007, C = 1; turnover girdisi −2.1789* (ham −2.2666). Tasarımdaki "Gerçekleşen: taban, taban" satırı çizilmedi: o etiket yalnız skor satırında vardır, sonuç dosyasında alt limit yoktur (F9).

### Getiri: tahmin ve gerçekleşen

Nokta grafiği (`returnDots`): her ufuk (D1, D3, D5, D10) için tahmin altın halka, gerçekleşen dolu beyaz nokta, ikisi arasında ince çizgi, sıfır çizgisi kesikli. Tablo: Gün · Tahmin (kapılı) · Arz üstü olasılığı (kapılı) · Gerçek (`R_h` metni; negatifse kırmızı) · Geçmiş test (birincil ✓ ya da ≈). Not: "Halkalı nokta tahmin, dolu nokta gerçekleşen. Sınıf: …"

### Kayıt ve kanıt günlüğü

`arz_view.log`: bu arzın olayları (kayıt, seri günleri, kırılma, D10, makine kaydı), Monitör'ün olay akışıyla aynı biçimde. KAP belgesinin sabitlenmesi ve işlem adedi (lot) satırları çizilmez (F18). En altta "Sicilde gör" ve "Ayrıntılı görünüm" (eski arz sayfası; kullanıcı beyanı şeridi ve iptal oradadır) bağlantıları.

Kaynak dosyalar: `app/src/sade/render/analiz.ts`; `app/src/sade/screens/analiz.ts`; `app/src/sade/types.ts` (`ArzView`, `BreakView`, `DayRow`); `app/src/render/svg.ts` (`corridorChart`, `tradeBar`, `returnDots`); `docs/app/UI_V2_HARITA.md` pano 4; `docs/app/UI_V2_RAPOR.md` §3; `docs/app/UI_FIX_RAPOR.md` K-FIX-1, K-FIX-4; `app/tests/sade_render.test.ts` ("Analiz").

---

## 8.16 Seri hesaplayıcı: "Seri j gün sürdüyse yarın ne olur?"

Proje sahibinin en çok istediği araçtır ve iki ekranda aynı bileşenle çizilir (`sade/render/calc.ts`): Tahmin sonucunda senaryo modunda, Analiz'de resmi görünümde.

### Soru ve formül

Bir arz j gün üst üste tavan yaptı. Yarın da tavan yapma olasılığı nedir? Listeleme öncesi model zaten S_k = P(L ≥ k) eğrisini vermiştir. Koşullu olasılık tanımından:

```
P(L ≥ k | L ≥ j) = S_k / S_j            (k > j)
yarın da tavan    = P(L ≥ j+1 | L ≥ j) = S_{j+1} / S_j
yarın bozulma     = 1 − S_{j+1} / S_j
tanımsız          : S_j = 0 ya da j ≥ 10  → "—"
```

Model **yeniden çalıştırılmaz**; yalnız elde zaten olan eğri yeniden ölçeklenir. Bu bölme Rust'taki `survival::conditional(S, j)` fonksiyonundadır ve Python'la 1e-12 içinde eşleştiği test edilir (U37). Ön uç yalnız j'yi seçer ve sonucu basar.

### Parçalar

1. **Başlık ve kimlik**: "Seri j gün sürdüyse yarın ne olur?" ve sağda öne çıkan modelin kimliği (altın). Alt satır senaryoda "Gün sayısını seç; yarının tavan ve bozulma olasılığı Rust'tan gelir.", resmi görünümde "Bültendeki seriyle ya da kendi seçtiğin günle".
2. **j düğmeleri** 0–9 ve "resmi" / "varsayımsal" etiketi. Senaryoda j her zaman varsayımsaldır. Resmi görünümde seçilen j bültende gözlenen j'ye eşitse "resmi", değilse "varsayımsal"; gözlenen j'nin düğmesi ayrıca işaretlidir.
3. **Bültende gözlenen seri kutusu** (yalnız resmi görünüm): "Bültende gözlenen: 3 gün" + durum ("seri sürüyor" ya da "seri D4'te bozuldu; gerçekleşen L = 3") + on günün dosyadaki durumları (tavan / tavan değil / bekliyor / etiket yok). j gözlenenden farklıysa "Gözlenene dön" düğmesi. Veri `streak_view`'den; Rust `data/outcomes/<T>.csv`'yi okur, baştan itibaren ardışık tavan günlerini sayar, ilk "bekliyor" satırında durur.
4. **Gün şeridi** D1–D10: j'ye kadar olan günler yeşil "tavan", j+1 altın kesikli çerçeveli "yarın", sonrası tire.
5. **Giriş cümlesi**: j = 0'da "Listeleme günü: D1'de tavan olasılığı %82."; j > 0'da "Seri 3 gün sürdüyse yarın (D4) da tavan olasılığı %67."
6. **Dört okuma** (hepsi Rust'ın `cond` alanlarından, öne çıkan modelin kapısıyla altın ya da ≈):

| Okuma | Alan | Anlamı |
|---|---|---|
| Yarın da tavan (+ "bozulma %p") | `cond.S_cond[j]`, `cond.p_break_next` | P(L ≥ j+1 \| L ≥ j) ve tümleyeni |
| Beklenen kalan gün (+ "koşullu medyan seri m gün") | `cond.expected_remaining`, `cond.median_l` | serinin j'den sonra kaç gün daha sürmesinin beklenen değeri; koşullu dağılımın medyanı |
| En az 5 gün sürme | `cond.S_cond[4]` | P(L ≥ 5 \| L ≥ j) |
| 10 gün boyunca tavan | `cond.S_cond[9]` | P(L ≥ 10 \| L ≥ j) |

`S_cond` dizisinin indisi k − 1'dir: `S_cond[j]` k = j + 1'e karşılık gelir. k ≤ j için koşullu değer tanımsız sayılır ve tire basılır; bu yüzden j ≥ 5'te "En az 5 gün sürme" tire gösterir (UI_FIX raporunda bilinen davranış olarak not edilmiş). `cond` hiç yoksa (S_j = 0 ya da j ≥ 10) okumaların yerine "Bu j'de koşullu değerler tanımsız" yazar.

7. **"Geçmiş arzlarda"** (FAZ9_UI_FIX ile eklendi): "Yarın da tavan"ın altında gri. Basit kural `base_km_expanding`'in aynı j'deki S_{j+1}/S_j değeri; aynı kaydın ya da koşunun içinden okunur. Bu kural bütün eğitim arzlarının (H99, n = 99) gün gün sürme oranlarıdır ve sansürsüz olduğu için S_j × n tam sayıdır. Rust bunu 1e-9 toleransla denetler; tam sayıysa bir sayım cümlesi de verir: "3 gün tavan yapan 66 arzdan 53 tanesi 4. gün de tavan oldu." (j = 0'da "Eğitimdeki 99 arzdan 81 tanesi ilk gün tavan oldu."). Tam sayı değilse yalnız oran yazar. Renk gridir: altın yalnız modelin çıktısıdır.
8. **Gün grupları notu**: `ceiling_hazard_v0` bir **kesikli zaman hazard** modelidir: her gün için "dün tavansa bugün de tavan olma" olasılığını modeller, ama günleri gruplara ayırır. Model dosyasındaki `day_groups` bugün `{g1: [1], g2: [2, 3], g3: [4…10]}`'dur. Aynı gruptaki günler aynı devam olasılığını paylaştığı için 3. günden sonra "yarın da tavan" değişmez. Not bu grupları dosyadan okur (sabit metin değildir): "Model günleri üç grupta ele alır: 1. gün · 2–3. gün · 4–10. gün. Aynı gruptaki her gün için aynı devam olasılığını kullanır; bu yüzden 3. günden sonra 'yarın da tavan' değişmez. 'Geçmiş arzlarda' oranı her gün için ayrı hesaplanır." Not, bir kullanıcının "j = 3 ile j = 6'da model neden aynı sayıyı veriyor?" sorusuna cevaptır.
9. **D1 sonrası satırı**: senaryoda "Senaryoda D1 bülteni yok; D1 sonrası güncelleme yalnız resmi kayıtta çalışır."; resmi görünümde kayıt varsa "D1 sonrası model (post_d1_hazard_v0) yarın bozulma: %p", yoksa "… bu arz için kayıtlı değil." (bugünkü durum; F27). D1 sonrası model j ≥ 1'de tanımlıdır.
10. **Eğri** (`calcCurve`): x = k (0..10), y = olasılık. Koşulsuz S_k gri kesikli; seçilen j'ye koşullu eğri altın, j'de 1'den başlar; kuralın koşullu eğrisi ince gri noktalı; 0..j arası gölgeli ("geçmiş günler"); yarının noktası altın daire. Altında formül: "P(L ≥ k | L ≥ j) = S_k / S_j. Model yeniden çalıştırılmaz."

### Örnek arzda test beklentileri

`sade_render.test.ts` ve Rust testi `calculator_netgl_expected_numbers` aynı arzın gerçek kaydıyla şu sayıları sınar:

| j | Yarın da tavan (model) | Bozulma | Diğer | Geçmiş arzlarda |
|---|---|---|---|---|
| 0 | %82 (S_1 = 0.8176) | %18 | | %82 (99 arzdan 81) |
| 3 | %67 | %33 | kalan 1.9 gün, koşullu medyan 4, P(≥5 \| ≥3) %45, P(10 \| ≥3) %6 | %80 (66 arzdan 53) |
| 6 | %67 | | | %82 (33 arzdan 27) |

Raporun dürüst notu (O9): görev metnindeki "beklenen L ≈ 3.2813" ve "P(10 | ≥3) ≈ 0.0592" dört ondalığa yuvarlanmış S'lerden türetilmişti; tam değerler 3.28115 ve 0.059132'dir. Test ikisini de uygun toleransla sınar.

### Kullanıcı beyanı yok

Ayrıntılı görünümde şeride tıklayıp "seri sürüyor" beyanı girilebilir (§8.22). Sade görünümde bu şerit hiç yoktur (K-UI-8); kişisel kayıt isteğinde beyan alanı her zaman boştur. Resmi j yalnız bültenden gelir.

Kaynak dosyalar: `app/src/sade/render/calc.ts`; `app/src/render/svg.ts` (`calcCurve`, `survivalCurve`); `app/src/types.ts` (`CeilingRow`, `CondView`, `CalcView`, `CalcHistory`, `DayGroups`); `app/src/i18n/tr.ts` (`SADE.calc`, `COND`); `models/ceiling_hazard_v0.json` (`day_groups`); `docs/app/SPEC_APP.md` §3g; `docs/app/UI_FIX_RAPOR.md` K-FIX-3, §9; `docs/app/UI_V2_RAPOR.md` §6 (O9); `app/tests/sade_render.test.ts` ("seri hesaplayıcı").

---

## 8.17 Model performansı

"Modeller işe yarıyor mu?" sorusunun sade ekranıdır. Eski görünümde karşılığı Doğruluk panelidir. Tek ilke: **her model kendi sorusunda, o soruya basit bir kuralla verilen cevaba karşı ölçülür** ve sayılar yalnız skor dosyalarından gelir.

### Veri

`perf_view` ve `headline_gate`. `perf_view` dört skor dosyasını okur: `scores/scores.json` (listeleme öncesi modeller), `scores_post_d1.json`, `scores_break.json`, `scores_oot.json`. Hangi satırların gösterileceği Rust'taki sabit listededir: ana ekran çıktılarının birincil hücreleri + birincil olmayan bir karşılaştırma (V1.5'in D10 arz üstü olasılığı taban orana karşı, dosyada "keşif" etiketli) + kırılma modelinin iki geçmiş test satırı. Bağımsız modda gömülü `scores.json` ile ilk dört satır görünür ve "D1 sonrası, kırılma akşamı ve zaman-dışı bölümler repo modu ister." notu düşer.

Skor dosyası şartnameyle çelişirse ekranın tamamı kapanır: "scores.json şartname kuralına aykırı (KURAL); panel kapalı." (U24'ün sade karşılığı).

### Veri şeridi

| Okuma | Kaynak | Bugünkü değer (rapor) |
|---|---|---|
| Üretimde | `n_production` (altın) | 4 |
| Karşılaştırma | `counts.n_rows` + sayım cümlesi | 6; "3 satırda model daha iyi · 1 satırda fark net değil · 2 satır hükümsüz" |
| Hüküm eşiği | `min_n_verdict`, `min_n_metric` | 30; "n ≥ 30 hüküm, n < 10 yalnız satır" |

Sayım cümlesinin parçaları Rust'ın `PerfCounts` yapısındaki **ayrı** alanlardan gelir (`n_pass`, `n_undecided`, `n_fail`, `n_other`, `n_no_verdict`); sıfır olan parça yazılmaz. İlk sürüm "ayırt edilemiyor" ile "geçemiyor"u aynı kovaya koyuyordu ("… satırda değil"); proje sahibi bunun yanıltıcı olduğunu fark etti ve düzeltildi (K-FIX-5).

### "Model, basit kuraldan daha iyi mi?" tablosu

Her satır bir karşılaştırmadır. Sütunlar:

| Sütun | İçerik | Kaynak |
|---|---|---|
| Soru ve karşılaştırma | "Kaç gün tavan ile son 10 arzın tablosu, RPS" + etiket (birincil / keşif) + `model_id · rule_id` | `question`, `rule_id`, `metric`, `label` |
| Hata puanı | iki yatay çubuk: model (altın) ve kural (gri), genişlikler ikisinin büyüğüne göre; yanlarında değerler | `model_value`, `rule_value` |
| 0 = fark yok | aralık çizimi: sıfır çizgisi, %95 aralık çizgisi, fark noktası | `diff`, `ci95` |
| Fark ve %95 aralık | fark ve aralık metni | `diff`, `ci95` |
| Model daha iyi olan arz | "kazanç / n" ve altında "kazanç · kayıp · eşit"; kırılma satırlarında "n = 69 (21 ay)" | `wins`, `losses`, `ties`, `n`, `n_months` |
| Hüküm | dosyadaki verdict + sade açıklama; kırılma satırlarında "hüküm alanı yok" + ön eleme etiketi | `verdict`, kapı |

**Fark** = model hatası − kural hatası. Hata ölçülerinde küçük olan iyidir; bu yüzden negatif fark modelin daha az hata yaptığı anlamına gelir. Değerler ölçüye göre biçimlenir: MAE puan (−0.08387 → "-8.4 puan"), RPS ve Brier 4 ondalık.

Aralık çizimlerinin hepsi aynı yatay ölçeği paylaşır. Ölçeğin uçları satırlardaki farkların ve aralık uçlarının en küçüğü ile en büyüğüdür (sıfır her zaman içeride kalır); bu bir eksen seçimidir. Aralık çizgisi hüküm "geçiyor" ise yeşil, değilse gridir; hüküm alanı olmayan kırılma satırında kapıdan geçtiyse (ön eleme) yine yeşildir.

Tablonun üstünde okuma rehberi aynen tasarımdaki gibidir (K-UI-5):

- "← model daha az hata yaptı · 0 = fark yok · kural daha iyi →"
- "Nokta ortalama farktır: model hatası eksi kural hatası. Sıfırın solundaysa model ortalamada daha az hata yapmış."
- "Çizgi %95 aralıktır: arzlar ilk işlem ayına göre bloklar hâlinde yeniden örneklendi; farkların %95'i bu çizginin üstüne düştü."
- "Çizginin tamamı sıfırın solunda ise fark tesadüf sayılmaz: model geçer. Çizgi sıfırı kesiyorsa fark tesadüf olabilir: 'fark net değil'."

Altta ölçülerin sözlüğü: **RPS** kaç gün sorusundaki olasılık dağılımının hatası; **MAE** getiri tahmininin ortalama mutlak sapması; **Brier** evet/hayır olasılığının karesel hatası. Ve kritik bir uyarı: "Geçmiş test tasarıma maruzdur, yalnız ön elemedir; asıl sınav canlı sicildir." **Tasarıma maruz**, modeli kuran kişinin bu verileri tasarım sırasında görmüş olması demektir; geçmiş testin sonucu bu yüzden iyimser olabilir.

Teslim raporundaki (3 Ekim 2026) altı satır:

| Model | Ölçü | Kural | Fark | %95 aralık | n | Kazanç / kayıp / eşit | Hüküm |
|---|---|---|---|---|---|---|---|
| `ceiling_hazard_v0` | RPS | `base_km_last10` | −0.04956 | [−0.07515, −0.02186] | 87 | 52 / 35 / 0 | geçiyor |
| `ceiling_hazard_v0` | RPS | `base_km_expanding` | −0.05686 | [−0.08326, −0.02865] | 87 | 59 / 28 / 0 | geçiyor |
| `v1_5_h99` | D5 MAE | `base_train_median` | −0.08387 | [−0.13432, −0.03211] | 87 | 58 / 29 / 0 | geçiyor |
| `v1_5_h99` | D10 Brier | `base_rate` | −0.03910 | [−0.07562, +0.00234] | 81 | 52 / 29 / 0 | ayırt edilemiyor |
| `break_floor_v0` | F1 Brier | ürün | −0.19038 | [−0.25203, −0.12470] | 69 (21 ay) | — | hüküm alanı yok |
| `break_floor_v0` | F1 Brier | `@ZERO` | −0.02808 | [−0.04528, −0.00740] | 69 (21 ay) | — | hüküm alanı yok |

Dördüncü satır ana ekran kapısının neden V1.5'in D10 arz üstü olasılığını öne çıkarmadığını gösterir: aralık sıfırı kesiyor.

### Üç ayrı sınav

Tablo: Model (soru + kimlik) · Geçmiş test (dosyadaki hükümler; kırılma modelinde ön eleme) · Eski dönem (zaman-dışı) (eski kohort bloğunun birincil hücre hükmü + " (zaman-dışı terazide)" + "n arz"; yoksa "test yok") · Canlı sicil ("a sayılan, b geç kayıt" + varsa "n geçmişe dönük"). Başlığın sağında altın renkte "Asıl sınav canlı sicil". Alt başlık: "Geçmiş test, eski dönem ve canlı sicil ayrı tutulur, asla toplanmaz."

**Eski dönem** (zaman-dışı, OOT: out-of-time) teste girmeyen eski bir kohorttur: H99 eğitim kümesinden önce (2020–2023) listelenmiş arzlar, tahminleri sonuçları repoya girmeden dondurulmuş.

### Canlı sicil ilerlemesi

Dört aşama için yatay çubuk: listeleme öncesi (kaç gün tavan), listeleme öncesi (D5 getiri), ilk gün akşamı (yarın tavan bozulur mu), kırılma akşamı (yarın da taban mı). Çubuk sayılan canlı arz sayısının hüküm eşiğine oranıdır ("1 / 30"); oranı `progressPct` (svg.ts) çizer. Not: "Her aşama 30 sayılan arzda değerlendirilir; geç ve geçmişe dönük kayıt sayılmaz."

### Canlı sicil satırları

Her arz için: Arz, İlk işlem; "Kaç gün tavan" grubu (Sınıf, Beklenen, Gerçek); "5. gün getirisi" grubu (Sınıf, Tahmin, Gerçek); İlk gün akşamı sınıfı; Kırılma akşamı sınıfı. Beklenen L kayıttaki S'ten Rust'ta, gerçekleşen L sonuç dosyasından gelir; getiri tahmini kayıttan, gerçekleşen getiri skor dosyasındaki ondalık metinden. Canlı sınıflı hücre yeşil çerçeveli. Not: "Sınıf push kanıtının tarihinden hesaplanır: ilk işlem gününden önce push'lanan kayıt canlıdır. D1 sonrası ve kırılma akşamı modelleri bu arzlardan sonra donduruldu; onlarda sayılan arz yok."

### Çizilmeyenler

Kalibrasyon grafiği ve D1 sonrası geçmiş test satırları (skor dosyalarında yok; F6); "Donmuş model ve kural 30", "Keşif varyantı 2.054" (toplam ve deney günlüğü sayımı; F11); aralık yöntemi kutusu (dosyadaki alan adı ön uç taramasında yasaklı bir sözcük içerdiği için; F19); araştırma arşivi (metinleri skor dosyasında yok; F20, yerine ayrıntılı görünüme bağlantı). En altta "Ayrıntılı görünüm: bütün modeller, hücreler ve zaman-dışı panel" bağlantısı.

Kaynak dosyalar: `app/src/sade/render/perf.ts`; `app/src/sade/screens/perf.ts`; `app/src/render/accuracy.ts` (`value`, `ciText`); `app/src-tauri/src/commands/sade.rs` (`PERF_EXTRA_CELLS`, `PRODUCTION_MODELS`, `PerfCounts`); `docs/app/UI_V2_RAPOR.md` §7; `docs/app/UI_FIX_RAPOR.md` K-FIX-5; `app/tests/sade_render.test.ts` ("Model performansı").

---

## 8.18 Sicil

Resmi kayıtların listesi ve künyesi. Giriş cümlesi kuralı özetler: "Resmi kayıtlar repoda kalır. Bu ekran her açılışta repodan okur; uygulama sicile yazmaz, commit ve push atmaz."

### Veri

`registry_view` (kayıtlar, iptal bağları, payda dosyası `registry/ipos.csv`, push kanıtları, git durumu), `monitor_view` (sayımlar, makine kayıtları, sınıflar) ve seçili arz için `break_view` ile `post_d1_records`. Ham kayıt istenirse `read_record_json`.

### Veri şeridi

Altı okuma: **Payda** ("n satır"; "a kayıtlı, b kapsam dışı"), Listeleme öncesi kayıt (etkin tahmin kaydı sayısı), D1 sonrası kayıt, Kırılma akşamı kaydı (makine kaydı), Zaman kanıtı dosyası (`registry/push_proofs` altındaki dosya sayısı), Repo durumu (`registry/` ve `data/` için `git status` boşsa yeşil "temiz", değilse kırmızı "commit bekleyen değişiklik var").

**Payda** projenin ikinci kuralıdır: başlangıçtan sonra işlem görmeye başlayan her arz sicile girer; dondurulmadıysa nedeniyle "atlandı" satırı olur. Böylece "yalnız iyi tahminleri göstermek" mümkün olmaz.

### Kayıtlı arzlar tablosu

Arz (kod + şirket), İlk işlem günü, Listeleme öncesi ("✓ n kayıt" ya da "yok"), D1 sonrası, Kırılma akşamı ("makine kaydı" ya da "yok"), "Aç". En yeni ilk işlem günü üstte. Altında "Kapsam dışı n satır — hiçbir sayıma girmez."

### Kayıt künyesi

Sağdaki panel seçili arzın künyesidir; üç sekme:

- **Listeleme öncesi** (tarih): Kayıt dosyası; Kayıt zamanı ("Yerel saat beyandır; zaman kanıtı push'tur."); Zaman kanıtı ("✓ push kanıtı var \<tarih\>" ya da "kaydı ekleyen commit için kanıt dosyası yok", altında kaydı ekleyen commit'in ilk 12 hanesi); Sınıf (model başına); Girdi belgesi (yol + sha'nın ilk 12 hanesi); Model kümesi ("n model" + kayıt anındaki INDEX sha256); Kayıt anındaki git HEAD.
- **Kırılma akşamı** (tarih): dosya, üretim zamanı (UTC), sınıf, yarın da taban olasılığı.
- **D1 sonrası**: varsa kayıt dosyaları, zamanları ve türleri; yoksa "Bu arz için D1 sonrası kayıt yok."

Altta üç düğme: "D1 sonrası kayıt sihirbazı", "Ham kayıt (JSON)" (kaydın tamamı girintili JSON olarak panelin altında açılır) ve "İptal kaydı düş". İptal ve D1 sonrası sihirbazı eski ekranlardır, sade kabuğun içinde açılır (§8.21). Not: "İptal ve iptal kuralı ayrıntılı kayıt sayfasındadır; son söz Python'undur. Aynı arzın birden çok kaydı ayrı sekmelerdedir; birincil kayıt seçimi skorlamada yapılır." Başlıktaki "Analizi aç" arzın Analiz sayfasına, sağ üstteki birincil "Yeni resmi kayıt" düğmesi dondurma sihirbazına gider.

**Neden "yerel saat beyandır"?** Bilgisayarın saati değiştirilebilir. Projenin ilk kuralına göre bir tahminin ilk işlem gününden önce yazıldığının kanıtı uzak depoya yapılan **push**'tur; push kanıtı dosyası GitHub'ın kaydettiği zamanı taşır.

### Künyeye kayma

Pencere darken künye tablonun altına iner. Bir satıra tıklanınca künye yeniden çizilir; künye görünür alanın tamamen içinde değilse sayfa yumuşakça künyenin başına kayar (`scrollIntoView`). Kullanıcı işletim sisteminde "hareketi azalt" seçtiyse kayma anında olur. CSS'teki `scroll-margin-top: 72px` künye başlığının yapışkan üst barın altında kalmamasını sağlar. Bu davranış sunum öncesi eklendi (K-FIX-2); 1200 piksel genişlikte künye tablonun yanında kalır.

Kaynak dosyalar: `app/src/sade/render/sicil.ts`; `app/src/sade/screens/sicil.ts` (`revealCard`); `app/src/i18n/tr.ts` (`SADE.sicil`); `docs/app/UI_V2_HARITA.md` pano 6; `docs/app/UI_FIX_RAPOR.md` K-FIX-2; `app/tests/sade_invoke.test.ts` ("Sicil: 'Aç'…").

---

## 8.19 Kayıtlarım

Kişisel kayıtlar (senaryolar) listesi. "Sakladığın senaryo tahminleri. Yalnız bu bilgisayarda durur; sicile ve doğruluk hesabına girmez."

- **Liste** (`list_scenarios`): Başlık, Oluşturma zamanı, Aşama, Model kümesi ("✓ güncel kümeyle aynı" ya da "eski küme"), İşlemler.
- **Aç** (`load_scenario`): kayıttaki çıktılar olduğu gibi Tahmin sonucuna yüklenir; yeniden hesaplanmaz (U36). Eski kümeyle üretilmiş bir kaydı yeniden hesaplamak için kullanıcı "Girdileri düzenle" ile değerleri forma kopyalayıp yeniden tahmin eder. Dosya okunamıyorsa "Aç" görünmez.
- **Dışa aktar** (`export_scenario`): işletim sisteminin kaydetme penceresi açılır; hedef repo klasörünün altındaysa Rust reddeder (U27). "Tümünü dışa aktar" (`export_all_scenarios`) bütün kayıtları tek JSON dizisine yazar ve kaç kaydın aktarıldığını, kaçının okunamadığını bildirir.
- **Sil** (`delete_scenario`): önce bir onay penceresi (`ask`) açılır; silme geri alınamaz.
- **Boş durum**: "Henüz saklanan senaryo yok" ve nasıl ekleneceğinin açıklaması, "Yeni arz gir" düğmesi.

Bir kişisel kayıt dosyasının (`borsai.app_scenario/1`) bilerek `record_type` alanı yoktur ve `official: false` taşır. Bu dosya yanlışlıkla sicil dizinine kopyalansa bile Python'un sicil okuyucusu onu tahmin kaydı saymaz (U29).

Tasarımdaki örnek satır çizilmedi; uygulama gerçek kayıtları listeler (F24).

Kaynak dosyalar: `app/src/sade/render/kayitlarim.ts`; `app/src/sade/screens/kayitlarim.ts`; `app/src/state.ts` (`openScenarioIntoStore`); `docs/app/SPEC_APP.md` §2.4, §3f.

---

## 8.20 Ayarlar ve Hakkında

İki sütunlu ekran.

**Sol sütun: ayarlar.**

- **Repo klasörü**: metin kutusu, "Klasör seç" (işletim sisteminin klasör seçici penceresi) ve derleme anındaki repo yolu öneriliyorsa "Öneriyi kullan".
- **Python yolu**: boşsa repo içindeki `.venv/bin/python`.
- **Skor dosyalarının kaynağı**: "Repodaki dosya" (`scores/scores.json`) ya da "Uygulamaya gömülü kopya".
- Düğmeler: **Kaydet** (`set_config`), **Doğrula** (`validate_repo`), **Repoyu kaldır** (repo yolunu silip kaydeder; bağımsız moda döner).
- Doğrulama listesi: her denetim için ✓ (geçti), × (zorunlu ve kaldı) ya da i (bilgi), ayrıntı metniyle; başlıkta "Repo modu açık / kapalı".
- Uygulama verisi dizininin yolu.

Kaydedince ayar ve skor ipuçları yeniden okunur; Monitör, kapı, performans ve Analiz önbellekleri boşaltılır (repo değişmiş olabilir); üst bar yenilenir.

**Sağ sütun: görünüm ve Hakkında.**

- **Görünüm**: iki radyo düğmesi. "Sade görünüm: Monitör, analiz ve hesaplayıcı (varsayılan)" ve "Ayrıntılı görünüm: Bütün modeller, hücreler ve kurallar (eski arayüz, aynen)". Seçim anında kabuğa iletilir ve `set_ui_view` ile kalıcı yazılır. Bu seçim tasarımda yoktu; görev gereği eklendi.
- **Hakkında** (`app_info`): uygulama sürümü; model bütünlüğü ("✓ tamam" ya da "× bozuk: tahmin kapalı"); listeleme öncesi model sayısı ve gömülü INDEX sha256'sının ilk 12 hanesi; D1 sonrası model sayısı ve ikinci dizinin sha'sı; gömülü skor kopyası var/yok; gömülü TÜFE tablosunun son ayı; "Uygulama verisi: kullanıcı klasöründe, repo dışında". Altta "Gömülü modellerin tam listesi ve parametre özetleri (ayrıntılı görünüm)" bağlantısı.

Tasarımdaki "Kırılma akşamı modelleri 2" satırı çizilmedi: kırılma modeli uygulamaya gömülü değildir (F23).

Kaynak dosyalar: `app/src/sade/render/ayarlar.ts`; `app/src/sade/screens/ayarlar.ts`; `app/src/i18n/tr.ts` (`SADE.ayarlar`, `SETTINGS.checkText`); `docs/app/UI_V2_HARITA.md` pano 10.

---

## 8.21 Sihirbaz kabuğu

Resmi kayıt (dondurma) ve D1 sonrası kayıt sihirbazları **yeniden yazılmadı**. Görev kuralı (K-UI-11) açıktı: bu akışların mantığı, komutları ve metinleri aynen kalır, çünkü sicile kayıt düşen tek yoldur ve uzun testlerle sınanmıştır. Sade görünümde eski ekran (`screens/registry.ts`) yeni bir çerçevenin içinde açılır:

- Üstte yol: "Sicile dön · Sicil / Yeni resmi kayıt" (ya da "Sicil / D1 sonrası kayıt", "Sicil / Kayıt sayfası").
- **Adım listesi**: dondurmada altı adım (Ön koşullar · Kaynak belgeler · Girdi belgesi · Denetim (yetkili, Python) · İlk işlem günü uyarısı · Dondur), D1 sonrasında dört adım (Ön koşullar · Bülten ve sonuç güncellemesi (Python; komut) · Kayıt (Python freeze --post-d1) · Şimdi yapılacaklar). Numaralı yuvarlaklarla çizilir.
- Ortada eski ekranın kendisi, `.s-legacy` kökünün altında; sade CSS eski sınıfları koyu temaya uyarlar.
- Sağda dondurmada "Akılda tut" paneli: "Zaman kanıtı push'tur, yerel saat değil. Push ilk işlem gününden önceyse kayıt canlı adayıdır." · "Kayda giren değerler tahmin ekranındaki değerlerin aynısıdır." · "İptal, ilk işlem gününden önce yapılabilir; sonrasında Python reddeder."

Eski ekran `ctx.legacy` bağlamıyla bağlanır; onun `navigate` çağrıları sade ekranlara çevrilir (§8.2). Eski ekran kendi içinde listeye dönerse (ör. "Sicile dön"), çerçeve bunu fark edip sade Sicil'e geçer.

Tasarımdaki adım göstergesinde **etkin adım** vurgulanıyordu; eski render dosyaları değiştirilemediği ve etkin adım bilgisi dışarıdan okunamadığı için bu işaret çizilmedi (F22).

Sihirbazların içeriği §8.22'de anlatılıyor.

Kaynak dosyalar: `app/src/sade/screens/sihirbaz.ts`; `app/src/screens/registry.ts`; `app/src/i18n/tr.ts` (`FREEZE.steps`, `POST_D1.steps`, `SADE.wizard`); `docs/prompts/FAZ9_APP_UI.md` K-UI-11.

---

## 8.22 Eski ayrıntılı görünüm

### Neden hâlâ var?

Sade görünüm yazılırken proje sahibinin kararı şuydu: eski arayüz silinmez, "Ayrıntılı görünüm" adıyla kodu ve testleriyle **aynen** kalır (K-UI-1, K-UI-2). Bunun dört nedeni var:

1. **Tam şeffaflık.** Sade görünüm yalnız dört üretim modelini ve kapıdan geçen çıktıları öne çıkarır. Ayrıntılı görünüm gömülü bütün modelleri (27), bütün basit kuralları, bütün uyarıları ve bütün skor hücrelerini gösterir. Bir modelin neden öne çıkmadığını merak eden kişi oraya bakar.
2. **Yalnız orada olan işlevler.** Kullanıcı beyanı şeridi (U52), tavan yolu modellerinin Grup C tablosu ve "Getiri (koşullu)" sekmesi, model kartları ve uyarı listeleri, zaman-dışı panelin kasa alt bölümleri ve yıl/rejim kırılımları, D1 sonrası skor bölümü, kayıt iptal formu, gömülü modellerin tam listesi.
3. **Sınanmış kod.** U1–U80 testlerinin büyük kısmı bu ekranların render fonksiyonlarını sınar. Dondurma ve D1 sonrası sihirbazları sicile yazan tek yoldur; yeniden yazmak gereksiz risk olurdu.
4. **Sıfır riskli geçiş.** Teslim raporları, sade görünüm ve düzeltme görevlerinin `screens/` ve `render/` altındaki eski dosyalara yalnız `svg.ts` ve `format.ts` eklemeleri yaptığını, silinen satır olmadığını `git diff` ile gösterir. `sade_static.test.ts` de eski dosyaların sade koda bağlanmadığını sınar.

### Kabuk

Açık renkli tema, sistem yazı tipi. Üstte **mod bandı**: SENARYO (turuncu, "Bu tahmin sicile girmez"), RESMİ KAYIT (mavi; sicil listesinde "sicil (salt okuma)", kayıt sayfasında kayıt dosyası ve push kanıtı satırı, sihirbazda "hazırlanıyor · Dondur gerçek repoya yazar"), DOĞRULUK (gri, "scores.json'dan salt okuma; uygulama skor hesaplamaz"); sağda repo modu göstergesi. Solda yedi ekranlık gezinme, altta DISCLAIMER. Her model sabit bir renge sahiptir (`colors.ts`); sütun başlığı ve eğri aynı rengi kullanır.

### Girdi

Aşama seçici; 20 alanlık tablo (# · Alan · Kaynak ipucu · Bu aşamada · Değer · Denetim). "Kaynak ipucu" her alanın hangi resmi belgeden okunacağını yazar (ör. KAP "Halka Arz Sonuçları"). f6 bölümü (Python ile hesapla / elle gir / boş bırak; S0, S20, XU100 dosya sha'sı, ret nedeni). Sicil belgesinden senaryoya kopyalama, f3 tanımı, "Tahmin et" ve "Resmi kayıt için hazırla". Birim notu: pay adetleri nominal 1 TL pay; binlik ayırıcı yok, ondalık nokta (virgül noktaya çevrilir ve gösterilir).

### Sonuç

Yukarıdan aşağı:

1. **"Tavan serisi — kaç gün tavan?" kartı** (EK 3 §5): öne çıkan model ve nedeni; büyük satırda beklenen seri ve medyan; P(en az 3 gün), P(en az 5 gün), P(10 gün); en olası bozulma günü; j > 0'da koşullu satır; **adaylar tablosu** (öne çıkan ★, v1 adayları, kural satırları, PB aynası, "her zaman tavan" sabiti) ve üç terazi sütunu: yakın dönem (geçmiş veri testi), zaman-dışı (kasa), canlı sicil. Üç sütunun üç ayrı rengi vardır ve altında "üç terazi ayrıdır; toplanmaz" yazar. TÜFE satırı ("TÜFE: 2026-07 = 132.31 (yayım …; kaynak repo dosyası; pin ✓)" gibi) ve skor kaynakları.
   **Öne çıkarma kuralı** (`featured_ceiling`, Rust): kasa (eski kohortun mühürlü yarısı) açılmadan önce `ceiling_hazard_v0`; açıldıktan sonra bir v1 adayı ancak (k1) kasadaki birincil hücresi "geçiyor", (k2) v0'a karşı aralığın üst ucu 0'ın altında ve (k3) yakın dönem etiketi "bozuyor" değilse uygun olur. P1 raporuna göre gerçek dosyalarla sonuç `RULE_5_5_NONE_ELIGIBLE_V0`'dır: uygun v1 adayı yok, öne çıkan v0 kalır. Uygulama yalnız dosyadaki hüküm, aralık ve etiketleri karşılaştırır.
2. **"Düşüş (D10)" kartı**: arz fiyatının altına düşme olasılığı, P(D10 kapanışı ≤ arz fiyatı) = 1 − p_up (Rust'ta hesaplanır, ön uç çıkarma yapmaz). P34 raporundaki gerçek dosyalarla öne çıkan aday yoktur ("kasa sonrası kural: uygun aday yok").
3. **Grup A — getiri ve olasılık**: model başına bir sütun, satırlar D1, D3, D5, D10. Hücrede işaretli getiri yüzdesi, fiyat (TL), `p_up` yüzdesi ve yön oku (↑/↓). Fiziksel sınıra kırpılan getiride `⌐` işareti ve ham değeri gösteren ipucu. "Her zaman tavan" kuralının fiyatı "≈ … yaklaşık" etiketli (fiyat adımı yuvarlaması yok). Ret eden sütunda bütün hücreler yerine tek blok: `RET · KOD` + alan + Türkçe neden; sütun kaybolmaz. Sütun başlığında "kart" düğmesi ve uyarı rozeti ("⚠ 2"); senaryoda başlıklarda "SENARYO" filigranı. Altında "backtest tipik hata (n = …): MAE … puan".
4. **Grup B — tavan serisi** (katlanır, varsayılan kapalı): S_k tablosu ve eğrisi (bütün tavan modelleri üst üste), P(L = k) çubukları, P(Dk'de tavan kapanışı), hazard değerleri, "seri k gün sürerse kapanış ≈ arz × 1.1^k" bilgi satırı.
5. **Grup C — tavan yolu getiri dağılımı** (h = 1..10): medyan, %10–%90 aralığı, p_up, S_h, limit yolu fiyatı C_h, atom sayısı; yelpaze grafiği (q10–q90 bandı, q50 çizgisi, limit yolu kesikli).
6. **Koşullu bölüm**: iki sekme. "Tavan serisi (koşullu)": gün gün şerit (tavan yeşil, tavan değil kırmızı, bekliyor gri, etiket yok çizgili, kullanıcı beyanı turuncu çerçeve), j seçici (gözlenen ya da varsayımsal), koşullu eğri ve tablo, D1 sonrası satırı. "Getiri (koşullu)": tavan yolu modellerinin koşullu getiri kartları.
7. Model seçici (gizleme yalnız görünümü etkiler; kayıtta bütün modeller vardır), rejim uyarısı, kişisel kayıt saklama, "Dondur akışına geç".

**Kullanıcı beyanı** yalnız bu ekranda ve eski arz sayfasında vardır. Şeritte bir güne tıklamak "seri sürüyor" beyanını açar/kapatır. Beyan resmi verinin önündeyse koşullu bölüm boş kalır ve "resmi kapanış bekleniyor" yazar; resmi veriyle çelişirse gösterilmez ve "beyan resmi veriyle çelişiyor; resmi değer esas" uyarısı çıkar; resmi kapanış gelince etiket kalkar.

### Doğruluk

Kaynak satırı (repo dosyası ya da gömülü kopya, üretim zamanı, as-of seans, sha'nın ilk 12 hanesi) ve gerekirse sarı "skorlar farklı bir model dizini için üretilmiş" uyarısı. Sonra model başına açılır bloklar; her blokta model kartı ve iki **bağımsız** bölüm:

- **"Geçmiş veri testi (retrospektif, tasarıma maruz)"** (lacivert-gri): hücre tablosu (çıktı, ufuk, metrik, model, kural, fark, %95 aralık, n, kazanç/kayıp/eşit, hüküm). Birincil hücre kalın çerçeve ve "birincil (önceden ilan)" rozeti; ötekiler "keşif". Getiri hataları puan, Brier/RPS 4 ondalık. İsabet oranı satırı yalnız kuralın isabeti de varsa görünür (U20).
- **"Canlı sicil (prospektif, n = k; atlanan = s)"** (kehribar): küçük-n üç hâli (n < 10 yalnız satır tablosu; 10–29 "yetersiz örnek"; ≥ 30 renkli hüküm).

Ayrıca koşullu skorlar, beyana dayalı eski kayıtlar ("ikincil"), RETRO (katlanır, gri, "hiçbir teraziye girmez"), atlananlar, D1 sonrası skorlar ve üçüncü bağımsız bölüm **"Zaman-dışı test (eski kohort)"** (yeşil-gri; `.panel-oot`). Zaman-dışı panelde hüküm metnine " (zaman-dışı terazide)" eklenir; satır tablosu yalnız açık küme bloğunda vardır ve Rust yalnız `open == true` satırları gönderir. Kasaya (SEALED) ait bir arz kodu, dosya yanlışlıkla taşısa bile, ekranın hiçbir yerinde gösterilmez; böyle bir satır gelirse panel kapanır ve yalnız sayı yazılır (`OOT_ROW_NOT_OPEN`, U73).

### Sicil

- **Liste**: kayıtlı arzlar, kayıt sayıları, push kanıtı durumu.
- **Arz sayfası**: aynı arzın birden çok kaydı ayrı sekmelerde; kayıt dosyası ve zaman kanıtı satırı ("kanıt dosyası var: \<sha\> \<zaman\>" ya da "push kanıtı bulunamadı"); "Tavan serisi" kartı ve koşullu bölüm **yalnız dondurulmuş kayıttan** (U38; kaynak satırı "kaynak: kayıt \<dosya\>, params sha \<ilk 8\>"); kayıtta olmayan yeni modeller "kayıt bu modeli içermiyor (kayıt INDEX'ten eski)"; ham JSON; iptal formu (neden boş olamaz; T'den sonra Python reddeder).
- **Dondurma sihirbazı** (altı adım): (1) ön koşullar: repo, git, repodaki INDEX sha'sı = gömülü sha, `borsai` repo altından yükleniyor, TÜFE ayı var; (2) kaynak PDF'lerin `registry/source_docs/<T>/` altına kopyalanması ve MANIFEST; (3) girdi belgesinin önizlenmesi ve yazılması (alan değerleri sonuç ekranından gelir, düzenlenemez; kullanıcı yalnız kaynak belgeyi, alıntıyı ve boş alan gerekçesini girer); (4) Python'un yetkili denetimi; (5) ilk işlem günü uyarısı (geçtiyse kırmızı: en iyi hâlde geç kayıt olur); (6) `python -m borsai.freeze`, ardından uygulamanın kendi tahminiyle **parite** karşılaştırması ("parite: n/n desteklenen model, |Δ|max = …") ve kopyalanabilir "Şimdi yapılacaklar" komut bloğu (git add, commit, push, push kanıtı). Uygulama bu komutları çalıştırmaz.
- **D1 sonrası kayıt sihirbazı** (dört adım): ön koşullar ve T_open (D1'i izleyen ilk seans 09:40), bülten güncellemesi için komut bloğu, `freeze --post-d1` ve parite, "Şimdi yapılacaklar".

### Kişisel kayıtlar, Ayarlar, Hakkında

Sade karşılıklarıyla aynı komutlar. Hakkında ayrıca derleme anındaki git HEAD ve `models/`/`scores/` durumunu, gömülü modellerin tam tablosunu (tür, params sha'nın ilk 8 hanesi), INDEX'te olup gömülmeyen modelleri ve ikinci dizinin (D1 sonrası) sha'sını gösterir.

Kaynak dosyalar: `app/src/main.ts` (`renderDetailed`); `app/src/screens/*.ts`; `app/src/render/{results,ceiling,summary,accuracy,accuracy_oot,registry,freeze,post_d1,inputs,card,colors,shell}.ts`; `app/src/styles.css`; `docs/app/SPEC_APP.md` §3; `docs/app/SPEC_APP_EK2.md` §4; `docs/app/SPEC_APP_EK3.md` §5–§8; `docs/app/p1/RAPOR.md` §4; `docs/app/p34/RAPOR.md` §4–§5.

---

## 8.23 Tasarım sistemi: Safir

### Renkler

Onaylı palet **Safir**'dir (Palet panosundaki üç seçenekten biri; öbürleri Grafit ve Gece moru, uygulanmadı). Koyu lacivert zemin üzerinde parlak metin. Bütün değerler `sade.css`'in başında `.sade` kökünde CSS değişkenleri olarak tanımlıdır; ayrıntılı görünüm (`styles.css`) bunlardan etkilenmez.

| Rol | Değer | CSS değişkeni | Anlam |
|---|---|---|---|
| Zemin | `#0A0F1A` | `--bg` | sayfa |
| Üst bar | `#0D1423` | `--bar` | |
| Pano | `#131C2F`, kenar `#22304A`, köşe 10 px, üstte ince iç ışık | `--panel`, `--panel-border` | birincil içerik |
| Kuyu | `#0D1423`, giriş kenarı `#2E3F61` | `--well`, `--input-border` | giriş alanı, segment zemini |
| Satır çizgisi | `#1A2539`; seçili satır `#16284A` + solda 3 px `#5B9BFF` | `--row-line`, `--row-sel`, `--sel-bar` | |
| Metin | birincil `#F4F7FC`, ikincil `#B7C3D7`, not ve eksen `#8C9AB3` | `--text`, `--text-2`, `--text-3` | |
| Eylem | `#2F6FEB` (birincil düğme); bağlantı, etkin sekme, odak halkası `#5B9BFF` | `--action`, `--accent` | |
| **Model çıktısı** | `#FFB648` (altın) | `--gold` | yalnız bizim modelimizin çıktısı |
| Yukarı / tavan / geçti | `#1ECB8A`; yazı `#5FE4B0`; zemin yeşilin %17'si | `--up`, `--up-text`, `--up-bg` | |
| Aşağı / taban | `#FF5D6E`; yazı `#FF9AA5`; zemin kırmızının %15'i | `--down`, `--down-text`, `--down-bg` | |
| Basit kural | `#8C9BB6`; ince çizgi `#50607D` | `--rule`, `--rule-line` | karşılaştırma |
| Rejim uyarısı | zemin `#1D140E`, kenar `#47301C`, yazı `#FFC38F`; rozet `#FF8A3D` üstüne `#1F0E05` | `--regime-*` | |

İki bağlayıcı kural:

1. **Altın yalnız modelimizin çıktısıdır.** Basit kural ve gerçekleşen değer asla altın olmaz. Bu yüzden hesaplayıcıdaki "Geçmiş arzlarda" satırı gri, P(L = l) çubuklarında en olası çubuk altın, koridorda gerçekleşen kapanış çizgisi beyaz, model beklentisi altın kesiklidir. Kapıdan geçmeyen model çıktısı da altın değil gridir (§8.11).
2. **Renk tek başına bilgi taşımaz.** Her renkli değerin yanında bir sözcük ya da işaret vardır: ✓ (geçti), × (kaldı), ≈ (fark net değil), ◐ (kısmen); "tavan" / "tavan değil" yazıları; "geç kayıt" metni. Renk körlüğü olan biri ya da siyah-beyaz bir çıktı da aynı bilgiyi okur.

Grafik renkleri bu sözlükten türer: P(L = l) çubukları soluk altın, en olası çubuk altın, gerçekleşen l yeşil halka; hesaplayıcıda koşulsuz eğri gri kesikli, koşullu eğri altın, kural eğrisi gri noktalı; koridorda tavan kapanışı yeşil kare, tavan değil kırmızı kare, üst limit yeşil çentik, arz çizgisi gri kesikli; aralık çizimi geçiyorsa yeşil, değilse gri; işlem sayısı çubukları gri.

### Yazı tipleri

| Yazı tipi | Kullanım |
|---|---|
| **IBM Plex Sans** (400/500/600/700) | arayüz metni |
| **IBM Plex Sans Condensed** (400/500/600) | tablolar, ana sayılar, tarihler; eşit genişlikli rakamlar (`font-variant-numeric: tabular-nums`) alt alta sayıların hizalanmasını sağlar |
| **IBM Plex Mono** (400/500) | yalnız model kimlikleri, dosya adları, sha önekleri |

Ölçek: sayfa başlığı 26 px kalın; pano başlığı 16 px yarı kalın + 13 px alt satır; tablo 13–14 px; not 12 px; ana sayılar 28–40 px Condensed. Etiketler cümle düzenindedir; BÜYÜK HARF yalnız hisse kodlarında.

Yazı tipleri `@fontsource` paketlerinden gelir (sürüm 5.3.0, lisans SIL Open Font License 1.1). `sade/fonts.ts` 18 CSS dosyasını içe aktarır: üç ailenin kullanılan kalınlıkları için `latin` ve `latin-ext` alt kümeleri. Türkçe harfler (ğ, ş, ı, İ) `latin-ext`'tedir; bu yüzden ikisi birlikte gerekir. Paketler yalnız geliştirme bağımlılığıdır; Vite derlemede yazı tipi dosyalarını (woff2) uygulama paketine koyar, çalışma zamanında ağdan hiçbir şey indirilmez. Teslim raporu pakette 18 yerel woff2 dosyası olduğunu yazar. `sade_static.test.ts` 18 içe aktarmanın hepsinin `@fontsource/` ile başladığını, dosyaların yerelde var olduğunu ve lisans alanının OFL-1.1 olduğunu sınar.

### Hareket

Tek bir **açılış anı** vardır; yalnız CSS ile:

| Sınıf | Hareket | Süre |
|---|---|---|
| `draw` | çizgi soldan sağa çizilir (`stroke-dashoffset` 1 → 0) | 1.6 s |
| `grow` | çubuk tabandan büyür (`scaleY` 0 → 1) | 0.9 s; P(L = l) çubukları 0.3 s'den başlayarak 0.05 s arayla sırayla |
| `growx` | yatay çubuk soldan uzar | 1.1 s |
| `fade` | nokta en son belirir | 0.7 s, 0.9 s gecikme |

Paneller kaymaz. Kullanıcının işletim sisteminde "hareketi azalt" ayarı açıksa (`@media (prefers-reduced-motion: reduce)`) bütün bu animasyonlar kapanır ve öğeler son hâlleriyle çizilir; Sicil'deki künyeye kayma da anında olur. JavaScript animasyonu (`requestAnimationFrame`, `.animate(`) sade kodda test ile yasaktır.

Tasarımda sayıların sıfırdan sayarak büyüdüğü bir **sayaç animasyonu** vardı. Uygulamada yoktur: ara değerleri üretmek ön uçta aritmetik ister (U25; F7).

### Yerleşim ve pencere

Pencere 1440 × 900 piksel açılır, ortalanır; en küçük boyut 1024 × 680'dir. Ekranın çalışma alanı daha küçükse pencere büyütülmüş açılır (K-FIX-6). Paneller esnek satırlar hâlinde dizilir; dar pencerede Monitör'ün yan sütunu ve Sicil künyesi alta iner, geniş tablolar kendi kutularında yatay kayar (`.s-scroll`). Ekran görüntüsü koşusu 1024 × 680'de her sade ekranda sayfanın yatay kaymadığını denetler. 760 pikselin altı için ek bir kural takımı vardır. 1024 genişlikte üst bar iki satıra kırılır; rapor bunu "ayrı iş" olarak not eder.

Ayrıntılı görünüm açık renkli kalır (açık gri zemin; senaryo turuncu `#E8740C`, resmi mavi `#1F5FBF`, nötr gri; terazi renkleri lacivert-gri, yeşil-gri, kehribar).

Kaynak dosyalar: `docs/design/ui_v2/README.md` "Belirteçler", "Yazı", "Hareket"; `docs/design/ui_v2/boards/Palet.dc.html`, `Stil.dc.html`; `app/src/sade/sade.css`; `app/src/sade/fonts.ts`; `app/src/styles.css`; `app/src-tauri/tauri.conf.json`; `app/tests/sade_static.test.ts`; `docs/app/UI_V2_RAPOR.md` "Yazı tipi lisansı"; `docs/app/UI_FIX_RAPOR.md` K-FIX-6.

---

## 8.24 Tasarımdan uygulamaya: süreç ve farklar

### Süreç

1. **Tasarım kanvası.** Sade görünüm Claude Design kanvasında 12 pano olarak çizildi. Repoya kopyası `docs/design/ui_v2/`'dedir: `boards/*.dc.html` (panoların kaynağı; "Design Component" biçimi, satır içi stiller, `{{ … }}` delikleri; çalıştırma ortamı repoda yok, bu yüzden yalnız referans olarak okunur), `boards/canvas.json` (pano sırası, başlıklar, boyutlar; hepsi 1440 px genişlik) ve `png/` (panoların durağan görüntüleri; yedek yazı tipiyle çizildiği için satır kırılmaları uygulamadan farklı olabilir; bu kopyada `png/` boştur).
2. **Onay.** Proje sahibi 3 Ekim 2026'da onayladı ("Tamam yapalım bu arayüzü").
3. **Orkestratör ölçümü.** Panolardaki sayıların hangisinin bir dosyada karşılığı olduğu, hangisinin ön uçta hesap istediği önceden ölçüldü; sonuç tasarım README'sinin "Tasarımdan uygulamaya geçerken (bağlayıcı)" bölümüne yazıldı: panolardaki sayılar **örnektir**; biçimler şartnameye uyar; ön uç hesap yapmaz; ana ekran kapısı veri-güdümlüdür.
4. **Görev dosyası** (`docs/prompts/FAZ9_APP_UI.md`): K-UI-1…K-UI-15 kuralları (iki görünüm, eski kod değişmez, bütün sayılar Rust'tan, kapı, hüküm metni, biçim, çizilemeyen öğeler, hesaplayıcı, yazı tipleri, hareket, sihirbazlar, mod göstergesi, bağımsız mod, Windows uyumu, öncelik sırası).
5. **Harita önce.** Kod yazılmadan önce `docs/app/UI_V2_HARITA.md` yazıldı: her panonun her öğesi için veri kaynağı (Rust komutu ve dosya alanı), şartname kuralı ve durumu ("çizilir" / "çizilmez"). Commit sırası D (tasarım, görev, harita) → A (salt okuma Rust komutları) → B (sade ekranlar, yazı tipleri, stiller, testler) → C (ekran görüntüleri, belgeler) → R (son test koşuları).
6. **Düzeltme turu.** Proje sahibi 4 Ekim'de altı sorun buldu; `FAZ9_UI_FIX` görevi bunları K-FIX-1…6 ile kapattı: Analiz'e dönüş ve arz değiştirici, Sicil künyesine kayma, hesaplayıcıya "Geçmiş arzlarda" ve gün grupları notu, işlem sayısı çubukları, performans sayımlarının ayrılması, pencere boyutu.

### Panolar

| Pano | Başlık | Uygulamadaki karşılık |
|---|---|---|
| `Main` | Monitör | §8.12 |
| `Giris` (+ talep öncesi hâli) | Yeni arz girişi | §8.13 |
| `Sonuc` | Tahmin sonucu | §8.14, §8.16 |
| `Arz` | Analiz (arz sayfası) | §8.15, §8.16 |
| `Dogruluk` | Model performansı | §8.17 |
| `Sicil` | Sicil | §8.18 |
| `Dondur` | Resmi kayıt sihirbazı | §8.21 (eski ekran, yeni çerçeve) |
| `D1Sonrasi` | D1 sonrası kayıt | §8.21 |
| `Kayitlarim` | Kayıtlarım | §8.19 |
| `Ayarlar` | Ayarlar ve Hakkında | §8.20 |
| `Stil` | Stil rehberi | `sade.css` belirteçleri |
| `Palet` | Palet seçenekleri | uygulanan: Safir |

### Tasarım ↔ uygulama farkları (F1–F27)

Her fark bir nedene bağlıdır; çoğunun nedeni "ön uç hesap yapmaz" ya da "bu bilgi hiçbir dosyada yok"tur. Liste teslim raporundaki son numaralandırmadır (haritadaki ilk taslakta numaralar biraz farklıydı).

| # | Öğe (pano) | Neden | Ne yapıldı |
|---|---|---|---|
| F1 | "Ortalama seri 3,43 / modelin ortalaması 3,67" (Monitör) | ortalama (U25) | "Tavan serisinde" sayımı |
| F2 | "model hatası %25 daha düşük" (Sonuç, Model performansı) | oran | iki değer yan yana + dosyadaki hüküm |
| F3 | "en güçlü seyir" (Monitör) | seçim ölçütü tasarıma ait | yok |
| F4 | "BIST kapalı" göstergesi | takvim durumu dosyadan değil | yok; veri tarihi kalır |
| F5 | Analiz işlem adedi çubukları | ilk raporda "sonuç dosyasında hacim yok" gerekçesi | sonra kapandı: işlem sayısı (`trade_count_raw`) sonuç dosyasında var, FAZ9_UI_FIX ile çizildi |
| F6 | Kalibrasyon grafiği, D1 sonrası geçmiş test satırları | skor dosyalarında yok | yok |
| F7 | Sayı sayma animasyonu | ön uç aritmetiği | yalnız CSS hareket |
| F8 | Rejim şeridindeki piyasa sayıları | dosyada yok | metin `tr.ts` + başlangıç tarihi |
| F9 | "ertesi gün de taban", "7 seans taban", "Gerçekleşen: taban, taban" | sonuç dosyasında alt limit yok; etiket yalnız skor satırında | yok |
| F10 | "Canlı sicil 0/30" tek sayı | modeller arası toplam terazileri karıştırır | model başına canlı n |
| F11 | "4/30", "30 model", "2.054 varyant" | toplam ve deney günlüğü sayımı | "4" kalır |
| F12 | "Kırılma akşamı" süzgeci | "bugün kırılma akşamı" dosyalardan belirlenemez | "Tümü" ve "Seride" |
| F13 | Giriş: bileşim yüzdeleri, ilerleme çubuğu, "8/8" | oran ve sayaç | eksik zorunlu alan listesi |
| F14 | Giriş: "Modellerin göreceği değerler" | tahminden önce özellik veren Rust komutu yok | yok (öneri: yeni komut) |
| F15 | Giriş: haftanın günü | tarih hesabı | gün-ay-yıl |
| F16 | Koridorda ±%10 bant mumları | alt limit yok | kapanış, tavan/değil, üst limit, arz, model, kırılma |
| F17 | Gerçekleşende "taban" yazımı | alt limit yok | "tavan değil" |
| F18 | Günlükte KAP belge sabitleme, işlem adedi (lot) | MANIFEST ve hacim okunmuyor | yok |
| F19 | Aralık yöntemi kutusu | alan adı taramada yasaklı sözcük | yok (ayrıntılıda) |
| F20 | Araştırma arşivi | metinler skor dosyasında yok | ayrıntılıya bağlantı |
| F21 | "Sistem: canlı skorlama açıldı" olayı | git günlüğü gerekir | yok |
| F22 | Sihirbazda etkin adım | eski render dosyaları değişmez | adım listesi var, etkin işaret yok |
| F23 | Hakkında "Kırılma akşamı modelleri 2" | modeller gömülü değil | yok |
| F24 | Kayıtlarım örnek satırı | örnek | gerçek liste |
| F25 | Virgüllü sayı yazımı | şartname §4 | `%50`, `3.3`, `+%25.5` |
| F26 | Giriş "Piyasa: −%9,24" | "Hesapla" bugünü referans alır; pinli XU100 bugüne yetişmiyor | ret nedeni metniyle gösterilir |
| F27 | D1 sonrası satırı | bugün D1 sonrası kayıt yok | not |

Bu tablo bir başarısızlık listesi değildir. Tasarım "ne güzel görünür" sorusuna, harita ve fark listesi "bunu dürüstçe gösterebilir miyiz" sorusuna cevap verir. F5 ilginç bir örnektir: ilk turda "hacim dosyada yok" denmişti; proje sahibi işlem sayısını istedi, sonuç dosyasında `trade_count_raw` sütunu bulundu ve çubuklar eklendi. Yani fark listesi de ölçülerek güncellenir.

Kaynak dosyalar: `docs/design/ui_v2/README.md`; `docs/design/ui_v2/boards/canvas.json`; `docs/prompts/FAZ9_APP_UI.md`; `docs/prompts/FAZ9_UI_FIX.md`; `docs/app/UI_V2_HARITA.md`; `docs/app/UI_V2_RAPOR.md` §1, §4; `docs/app/UI_FIX_RAPOR.md` §0, §3; `GITLOG.txt`.

---

## 8.25 Testler ve ekran görüntüleri

### Katmanlar

`bash app/scripts/test.sh` dört şeyi sırayla koşar: Rust testleri (`cargo test --workspace`, repo yolu `BORSAI_REPO` ile; geçici klon isteyen beş uçtan uca test hariç), ön uç testleri (`npm test` = `tsc --noEmit` + `vitest run`), Python parite testleri (`app/parity/test_gen_golden.py`) ve eski altın dosyaların bayt-eşitliği (`golden_unchanged.sh`). Ortam isteyen bir Rust testi listeye eklenmezse ortamsız koşar ve kırmızı olur; betik bunu bilerek böyle kurar ("fail-closed").

Son teslim raporundaki (FAZ9_UI_FIX; son kabul koşusu HEAD `b2a861b`'de yapıldı, çıktıları bugünkü HEAD `ee3796d` commit'iyle repoya girdi) sayılar: **vitest 376 test (24 dosya)**, cargo 164, parite 8, `golden_unchanged` yeşil, `gen_golden --check` 35/0; repo genelinde pytest 952. Sade görünümden önce vitest 305'ti; sade görünüm 60 test ekledi (365), düzeltme turu 11 test daha (376). Bu oturumda testler koşulmadı (kopyada `node_modules` yok); sayılar rapordan. Kaynak metinde 355 `it(` çağrısı sayılıyor; fark, döngüyle üretilen testlerden gelir (ör. `results.test.ts`'te her ret kodu için, `stage5.test.ts`'te her ekran hâli için ayrı test).

### vitest dosyaları

**vitest**, Vite ile çalışan bir JavaScript test çatısıdır. Varsayılan ortam `node`'dur; DOM gereken dosyalar başlarındaki `// @vitest-environment jsdom` satırıyla **jsdom** (Node içinde çalışan sahte tarayıcı belgesi) kullanır.

| Dosya | `it(` | Ne sınar |
|---|---|---|
| `sade_render.test.ts` | 46 | sade ekranların render çıktısı; Monitör sayımları, hesaplayıcı sayıları, kapı, hüküm hücresi, Analiz, performans, Sicil, Kayıtlarım, Ayarlar, Giriş |
| `accuracy.test.ts` | 43 | doğruluk paneli: U13–U26 |
| `summary.test.ts` | 32 | Tavan serisi ve Düşüş kartları (U60–U62, U79) |
| `path.test.ts` | 23 | tavan yolu gösterimi (U48–U49) |
| `u52_declaration.test.ts` | 21 | kullanıcı beyanı (U52) |
| `stage5.test.ts`, `freeze.test.ts` | 20 + 20 | mod bandı, model kartı; dondurma sihirbazı |
| `accuracy_oot.test.ts` | 18 | zaman-dışı panel (U71–U75) |
| `results.test.ts`, `post_d1.test.ts` | 17 + 17 | sonuç ekranı (U7, U9–U11); D1 sonrası satırı (U68, U70) |
| `registry.test.ts`, `post_d1_wizard.test.ts`, `ceiling.test.ts` | 13 + 12 + 12 | sicil, D1 sonrası sihirbazı, şerit (U40) |
| `sade_svg_format.test.ts` | 11 | yeni biçimleyiciler ve SVG koordinatları |
| `no_frontend_math.test.ts` | 10 | §8.6 |
| `sade_invoke.test.ts` | 8 | sade ekranların komut çağrıları |
| `screens_invoke.test.ts` | 7 | eski ekranların komut çağrıları |
| `sade_static.test.ts` | 6 | sade dosyalarda hesap yok, yazı tipleri yerel, hareket CSS'te |
| `scenario`, `inputs`, `codes`, `no_network`, `format`, `disclaimer` | 4 + 4 + 4 + 3 + 2 + 2 | kişisel kayıt, form, U8, U34, biçimler, DISCLAIMER |

### İki önemli test tekniği

**Sahte `invoke`.** `sade_invoke.test.ts` Tauri'nin `invoke` fonksiyonunu `vi.mock` ile sahtesiyle değiştirir: her çağrının adı ve argümanları bir listeye yazılır, cevap fixture'dan döner. Sonra **gerçek** `mountSade` çağrılır ve gerçek düğmelere tıklanır. Böylece şunlar sınanır: Analiz açılınca j varsayılanı gözlenen j = 3'tür ve `record_summary`'ye `jObserved = 3` gider; `predict_all` hiç çağrılmaz (U38); j düğmesi Tahmin sonucunda yalnız `ceiling_display`'i yeniden çağırır; kişisel kayıt isteğinde beyan alanı boştur; bağımsız modda Monitör, Analiz ve Sicil hiçbir komut çağırmaz.

**Rust'ın ürettiği fixture'lar.** Render testleri elle yazılmış sayı kullanmaz. `app/tests/fixtures/ui/` altındaki 97 JSON dosyası Rust komutlarının gerçek repo dosyalarıyla ürettiği çıktılardır (örn. `sade_monitor.json`, `sade_record_ceiling_netgl_j3.json`, `sade_gate.json`). Rust testleri (`stage2.rs`, `stage3.rs`, `sade.rs`) bu dosyaların güncel olduğunu sınar ve `BORSAI_UPDATE_UI_FIXTURES=1` ile yeniden yazar. Skor kuralları için `fixtures/scores/` altındaki dosyalar ise bilerek **sentetiktir** (`synthetic: true`; n = 7, 12, 35 senaryoları ve kurala aykırı kopyalar); kurgusal arzlarla küçük-n ve fail-closed dallarını sınar. Gözlenen seri durumları için `fixtures/outcomes/` altında kurgusal arzlarla sentetik sonuç dosyaları vardır (bekliyor, bozuldu, etiket yok, on gün tavan).

### Uçtan uca betikler

`e2e_freeze_tmp_repo.sh` (U28–U32: dondurma akışı geçici klonda), `e2e_personal_isolation.sh` (U39: kişisel kayıt ve beyan hiçbir repo dosyasını değiştirmez), `e2e_post_d1_tmp_repo.sh` (U69). Hepsi asıl repoyu salt okur; değişikliği `git clone --local` ile açılan geçici klonda yapar ve öncesi/sonrası sha listelerini karşılaştırır.

### Ekran görüntüleri

Görüntüler elle değil, uygulamanın kendisi tarafından üretilir. Yöntem:

1. Betik (`scripts/screens_v2.sh` sade, `screens.sh` eski, `screens_p2.sh`, `screens_p34.sh` ek aşamalar) uygulamayı `npm run tauri dev -- --features snapshot` ile ve `VITE_BORSAI_DEMO=1` (sade için ayrıca `VITE_BORSAI_DEMO_V2=1`) ortam değişkenleriyle açar.
2. `src/dev/demo.ts` bir kullanıcı gibi davranır: yalnız gerçek düğmelere tıklar, alanları doldurur ve her adımda Rust'ın `dev_snapshot` komutuyla pencerenin görüntüsünü alır. Bu kod yalnız geliştirme derlemesinde ve bu bayrakla yüklenir; üretimde ölü koddur.
3. Dosya seçici yerel bir pencere olduğundan demo ona tıklayamaz; yalnız bu koşuda `vite.config.ts` dialog modülünü `src/dev/dialog-demo.ts` ile değiştirir. Hedef geçici uygulama verisidir; yol bekçisi yine Rust'ta çalışır.
4. Uygulama verisi geçici bir dizindedir (`BORSAI_DATA_DIR`); asıl repo salt okunur. Betik sonunda `registry/` ve `data/` ağaçlarının sha listesinin öncekiyle aynı olduğunu denetler; değilse kırmızı biter.
5. Sade koşusu 1024 × 680 pencerede her ekranda `scrollWidth ≤ clientWidth` (yatay kayma yok) ister; aşan olursa `zz_demo_error.png` üretip hata verir.
6. Görüntüler `sips` ile 1440 px genişliğe getirilip `app/docs/screens/v2/` altına yazılır.

Teslim raporlarındaki sade görüntüler: `v2_00` (bağımsız mod Monitör), `v2_01` (Monitör ve olay akışı), `v2_02` (Giriş), `v2_03`/`v2_04` (Tahmin sonucu j = 0, j = 3, getiri ve dayanaklar), `v2_05…` (Analiz: liste, başlık, koridor, hesaplayıcı j = 3 ve j = 6, işlem sayısı, kırılma kartı, günlük, arz değiştirici), `v2_06` (Model performansı), `v2_07` (Sicil; 1200 px'te künye), `v2_08` (Kayıtlarım), `v2_09` (dondurma sihirbazı 1. adım), `v2_10`–`v2_12` (Ayarlar, ayrıntılıya geçiş ve dönüş), `v2_13` (Analiz 1024 × 680). Bu repo kopyasında `app/docs/screens/` altında yalnız `README.md` vardır; görüntü dosyaları kopyaya alınmamış (belirsiz: asıl repoda olup olmadıkları burada ölçülemedi).

### Hijyen taraması

Her teslimden önce yeni ve değişen bütün dosyalar (görüntüler dahil) eski kohort kasasındaki 64 mühürlü arz koduna (büyük/küçük harf duyarlı, sözcük sınırıyla) ve bülten dosya adı kalıbına karşı taranır; kodlar taranırken yazdırılmaz. Rapor "0 bulgu" yazar. Rust testleri de yeni görünüm komutlarının çıktısında bülten dosya adı ve eğitim arz listesi bulunmadığını sınar.

Kaynak dosyalar: `app/scripts/test.sh`; `app/vite.config.ts`; `app/tests/*.test.ts`; `app/tests/helpers.ts`; `app/tests/fixtures/{ui,scores,outcomes}/`; `app/scripts/screens_v2.sh`, `screens.sh`; `app/src/dev/demo.ts`, `dialog-demo.ts`; `docs/app/UI_V2_RAPOR.md` §7–§10; `docs/app/UI_FIX_RAPOR.md` §5–§10; `app/README.md`.

---

## 8.26 Bölüm özeti

- Ön uç düz TypeScript'tir; çerçeve yok. Saf render fonksiyonları HTML metni üretir, ekran bağlayıcıları Rust komutlarını çağırır ve olayları dinler. Durum iki düz nesnededir; kalıcı olan yalnız Rust'ın yazdığı ayar ve kişisel kayıt dosyalarıdır.
- İki görünüm vardır: varsayılan **sade** (Safir paleti, Monitör, hesaplayıcı) ve **ayrıntılı** (eski arayüz, bütün modeller). Seçim `config.json`'daki `ui_view`'dadır; iki yönde geçilir.
- **Ön uç hesap yapmaz.** Çarpma ve bölme yalnız `format.ts` (gösterim ölçeği) ve `svg.ts` (piksel) içindedir; sade kodda hiç yoktur. Bu, kaynak kodu tarayan testlerle zorlanır.
- Sayı biçimleri tek dosyadadır: olasılık `%91`, getiri `+%7.7`, fiyat `27.48 TL`, metrik 4 ondalık, getiri hatası "puan"; ondalık ayırıcı noktadır.
- Bütün metinler `tr.ts`'tedir. "geçiyor" yalnız hüküm eşlemesinde bulunur ve ekrandaki her "geçiyor" dosyadaki `verdict`'ten gelir; yasak sözcükler test edilir; DISCLAIMER her ekranın altındadır.
- Sade görünümde altın renk yalnız **kapıdan geçen** model çıktısıdır: önceden ilan edilmiş birincil hücresi dosyada "geçiyor" olmayan çıktı gri ve "≈" ile durur.
- Resmi görünümde (Analiz) bütün tavan sayıları dondurulmuş kayıttan gelir; model yeniden çalıştırılmaz. Kullanıcı beyanı hiçbir sayıya girmez.
- Tasarım onaylandıktan sonra her öğe bir veri kaynağına bağlandı; bağlanamayan ya da hesap isteyen 27 öğe gerekçesiyle çizilmedi ya da değiştirildi.

Kaynak dosyalar: bu bölümün bütün alt bölümlerinde anılanlar; özet için `app/README.md` ve `docs/app/UI_V2_RAPOR.md` §0.

# 7. Uygulama I: Rust arka uç ve modellerin portu

Bu bölüm, BorsAi masaüstü uygulamasının ekranın arkasında kalan yarısını anlatır: `app/src-tauri` altındaki Rust kodu, modellerin Rust'a taşınmış hâli (`borsai_predict` crate'i) ve bu taşımanın Python'la aynı sayıyı verdiğini kanıtlayan parite düzeneği. Ön ucun (TypeScript ekranları) ayrıntısı bir sonraki bölümün (Bölüm 8) konusudur; burada ön uç yalnız "komut çağıran ve gelen sayıyı biçimlendiren taraf" olarak görünür.

Bölümü okurken akılda tutulacak üç cümle:

1. **Uygulama sayı üretir ama resmî kayıt yazmaz.** Tahminleri Rust hesaplar; resmî sicile giren kaydı her zaman repodaki Python (`borsai.freeze`) yazar.
2. **Rust, Python'un kopyasıdır, rakibi değildir.** Bir modelin tanımı Python'dadır; Rust portu her test koşusunda Python'un ürettiği "doğru cevaplarla" (altın vektörler) sınanır.
3. **Şüphede kapalı kal (fail-closed).** Gömülü bir dosyanın sha256'sı tutmazsa, skor dosyası kurala aykırıysa ya da ön koşul eksikse uygulama yarım çalışmaz; hata gösterir.

Kod parçaları kısaltılmıştır; tam hâli için her alt bölümün sonundaki dosyalara bakın. Sayılar, aksi yazılmadıkça, bu bölüm yazılırken repo anlık kopyasından okunmuştur.

---

## 7.1 Önce kavramlar

Bu alt bölüm, bölümün geri kalanında sık geçen terimleri sıfırdan tanımlar. Bildiğiniz terimleri atlayabilirsiniz.

### Tauri ve webview

**Tauri**, masaüstü uygulaması yazmak için bir çatıdır (framework). Arayüz HTML, CSS ve JavaScript/TypeScript ile yazılır; bu arayüzü işletim sisteminin kendi **webview**'i çizer. Webview, bir uygulamanın içine gömülebilen tarayıcı motorudur: macOS'ta WKWebView, Windows'ta WebView2, Linux'ta WebKitGTK. Electron gibi çatılar Chromium'u uygulamayla birlikte paketler; Tauri paketlemez, bu yüzden ikili dosya küçük kalır. Uygulamanın "beyni" ise derlenmiş bir **Rust** programıdır. BorsAi Tauri'nin 2. ana sürümünü kullanır (`Cargo.lock`'ta `tauri 2.11.6`).

### Rust, crate, workspace

**Rust**, belleği çöp toplayıcı olmadan güvenli yöneten, derlenen bir dildir. Bu bölümde sık göreceğiniz iki tür vardır: `Option<T>` (değer var: `Some(x)`, yok: `None`) ve `Result<T, E>` (başarı: `Ok(x)`, hata: `Err(e)`). Rust'ta istisna (exception) yoktur; hata dönüş değeriyle taşınır. `?` işleci "hata ise hemen geri dön" demektir.

**Crate**, Rust'ın derleme birimidir: bir kütüphane ya da çalıştırılabilir program. **Cargo** Rust'ın paket yöneticisi ve derleme aracıdır. `Cargo.toml` bir crate'in bildirimidir (adı, bağımlılıkları; `"2"` yazımı "2.x sürümlerinden uyumlu olan" demektir); `Cargo.lock` ise bağımlılıkların çözülmüş tam sürümlerini ve sağlama toplamlarını tutar, böylece her derleme aynı kütüphane sürümleriyle yapılır. **Workspace**, birden çok crate'i tek bir `Cargo.lock` altında toplayan çatıdır. BorsAi'de workspace iki üyelidir: uygulamanın kendisi (`borsai-app`, `app/src-tauri`) ve modellerin saf portu (`borsai_predict`, `app/src-tauri/crates/borsai_predict`). "Saf" burada Tauri'ye, dosya sistemine ve ağa bağımlı olmayan demektir; bu crate yalnız sayı hesaplar ve pencere açmadan `cargo test` ile sınanabilir.

### serde ve JSON

**serde**, Rust'ta veri yapılarını başka biçimlere çevirme (serialize) ve geri okuma (deserialize) çatısıdır. `#[derive(Serialize, Deserialize)]` yazılan bir `struct` otomatik olarak JSON'a dönüşebilir. **serde_json** bu işin JSON tarafıdır. BorsAi iki özellik açar:

- `preserve_order`: JSON nesnelerindeki anahtar sırası korunur. Model dosyalarındaki ufuk sırası (`D1, D10, D3, D5`) ve dolayısıyla uyarı sırası buna bağlıdır.
- `float_roundtrip`: metindeki ondalık sayı, en yakın 64 bitlik kayan nokta sayısına doğru yuvarlanarak okunur. Python'un `json.load`'ı da doğru yuvarlar; bu sayede iki taraf aynı model katsayısını aynı bitlerle okur.

### IPC, komut, `invoke`

**IPC** (inter-process communication), iki yazılım parçası arasında mesajlaşmadır. Tauri'de ön uç (webview içindeki TypeScript) ile arka uç (Rust) ayrı dünyalardır; aralarındaki köprü **komut**tur. Rust'ta bir fonksiyonun üstüne `#[tauri::command]` yazılır ve `tauri::generate_handler![...]` listesine eklenir. Ön uç onu adıyla çağırır:

```ts
// app/src/api.ts
predictAll: (inputs, f6, t) => invoke<ModelRun[]>("predict_all", { inputs, f6, t }),
```

Argümanlar JSON olarak Rust'a gider, serde ile Rust türlerine çevrilir; dönüş değeri yine JSON olarak geri gelir. Rust tarafı `Ok(x)` dönerse TypeScript'teki `Promise` çözülür, `Err(e)` dönerse reddedilir. Tauri, JavaScript'teki camelCase argüman adlarını (`relPath`) Rust'taki snake_case parametrelere (`rel_path`) kendisi eşler.

### State (paylaşılan durum)

Komutların ortak bir duruma ihtiyacı vardır: hangi modeller doğrulandı, ayar dosyası ne diyor, repo nerede. Tauri'de `Builder::manage(x)` ile bir değer uygulamaya bağlanır ve her komut onu `tauri::State<'_, AppState>` parametresiyle alır. BorsAi'de bu değer `AppState`'tir (§7.2).

### CSP ve capabilities

**CSP** (Content Security Policy), webview'e "hangi kaynaktan betik, stil, resim yükleyebilirsin; hangi adrese bağlanabilirsin" kurallarını veren bir güvenlik başlığıdır. Kötü niyetli ya da yanlışlıkla eklenmiş bir betik dış bir sunucuya veri gönderemesin diye kullanılır.

**Capabilities** (yetenekler), Tauri 2'nin izin sistemidir: bir pencerenin Tauri çekirdeğinin ve eklentilerin hangi komutlarını çağırabileceğini listeler. Dosya sistemi, kabuk (shell), HTTP gibi eklentiler burada izin verilmedikçe ön uçtan kullanılamaz.

### build.rs ve gömme (embed)

**build.rs**, Cargo'nun asıl derlemeden önce çalıştırdığı küçük bir Rust programıdır. Kod üretmek, dosya okumak, bir koşul tutmazsa derlemeyi kırmak için kullanılır. Ürettiği dosyalar `OUT_DIR` adlı geçici derleme dizinine yazılır.

**Gömme**, bir dosyanın içeriğini derleme anında programın içine sabit olarak koymaktır. Rust'ta `include_str!("yol")` makrosu bunu yapar: dosya metni ikilinin bir parçası olur, çalışma anında diskte o dosyanın bulunması gerekmez. BorsAi model JSON'larını, model dizinini (`INDEX.json`), TÜFE tablosunu ve skor dosyalarının anlık kopyalarını böyle gömer.

### sha256

**sha256**, herhangi bir bayt dizisinden 256 bitlik (64 onaltılık hane) bir "parmak izi" üreten kriptografik özet fonksiyonudur. Tek bir bayt değişse sonuç tamamen değişir; iki farklı dosyanın aynı özete sahip olması pratikte imkânsızdır. BorsAi'de sha256 bir zincir gibi kullanılır: `INDEX.json` her model dosyasının sha256'sını yazar, uygulama açılışta gömülü dosyaların sha256'sını hesaplayıp karşılaştırır; tahmin kaydı da hangi parametre dosyasıyla üretildiğini `params_sha256` alanıyla taşır.

### Kayan nokta (f64) ve Decimal

Bilgisayarın olağan ondalık sayısı **f64**'tür (IEEE 754 binary64, "çift duyarlıklı kayan nokta"). 64 bitin 53'ü anlamlı haneye ayrılır; bu yaklaşık 15–17 ondalık hane demektir. Taban 2 olduğu için 0.1 gibi sayılar tam temsil edilemez, her işlem en yakın temsil edilebilir sayıya yuvarlanır. Sonuç: `0.1 + 0.2 != 0.3`, ve toplama sırası değişince son hane değişebilir.

**Decimal** (Python'un `decimal` modülü) taban 10'da kesin sayıdır: `Decimal("25.52")` gerçekten 2552 × 10⁻² değeridir. İşlemler bir **bağlam** (context) içinde yapılır: kaç anlamlı hane tutulacağı (precision) ve nasıl yuvarlanacağı. **ROUND_HALF_EVEN** (bankacı yuvarlaması) tam yarıda çift olana yuvarlar (2.5 → 2, 3.5 → 4); **ROUND_HALF_UP** tam yarıda sıfırdan uzağa (2.5 → 3). BorsAi'nin Python modelleri girdileri ve bazı özellikleri Decimal ile hesaplar, sonra f64'e çevirip katsayılarla çarpar. Rust'ta aynı bitleri elde etmek için **Python'un hangi adımı hangi duyarlıkta yaptığını birebir taklit etmek** gerekir; §7.8.1 bunu anlatır.

### Neumaier toplaması

Kayan noktada çok sayıda terimi toplarken küçük terimler büyüklerin yanında kaybolabilir. **Telafili toplama** (Kahan ve onun geliştirilmiş hâli **Neumaier**), her adımda kaybolan parçayı ayrı bir değişkende biriktirir ve sonda ekler. CPython 3.12'nin yerleşik `sum()` fonksiyonu kayan nokta toplamada Neumaier yöntemini kullanır: `sum([1e16, 1.0, -1e16]) == 1.0`, düz bir döngü 0.0 verirdi. Rust portu aynı algoritmayı yazar (§7.8.1).

### Parite, altın vektör, bit eşitliği

**Parite**, iki ayrı gerçeklemenin (burada Python ve Rust) aynı girdide aynı çıktıyı vermesidir. **Altın vektör** (golden vector), referans gerçeklemenin (Python) ürettiği ve dosyaya dondurulmuş girdi–beklenen çıktı çiftleridir; Rust testi bu dosyayı okuyup her satırı yeniden hesaplar. **Bit eşitliği**, iki f64'ün 64 bitinin aynı olmasıdır (`x.to_bits() == y.to_bits()`); "|Δ| ≤ 1e-9" toleransından daha sıkıdır. BorsAi'de kabul ölçütü toleranstır; bit eşitliği ayrıca sayılır ve model başına bir tabanın altına düşmemesi istenir (§7.11).

### Repo modu ve bağımsız mod

Uygulama iki modda çalışır:

- **Bağımsız mod:** ayarlarda repo yolu yok ya da doğrulanmamış. Uygulama yalnız derlemeye gömülü verilerle çalışır: 27 model, TÜFE tablosu, `scores.json` anlık kopyası, `scores_oot.json`'un satırsız süzülmüş kopyası. Tahmin, senaryo, kişisel kayıt ve (gömülü) doğruluk paneli çalışır; sicil, resmî kayıt, D1 sonrası, f6'nın Python'dan alınması ve sade görünümün izleme ekranları çalışmaz.
- **Repo modu:** ayarlardaki repo kökü doğrulanmış (§7.6). TÜFE tablosu her tahminde repodan okunur, skorlar (ayar `REPO` ise) repodan okunur, Python çağrıları yapılabilir.

Kaynak dosyalar: `app/src-tauri/Cargo.toml`, `app/src-tauri/Cargo.lock`, `app/src/api.ts`, `docs/app/SPEC_APP.md` §1.

---

## 7.2 Mimari: üç katman ve bir köprü

```
┌──────────── Tauri penceresi (webview) ─────────────┐
│ TypeScript ön uç: form, tablo, SVG.                 │
│ Hesap yapmaz; invoke("komut", {…}) çağırır.         │
└─────────────────────────┬───────────────────────────┘
                          │ IPC (JSON)
┌─────────────────────────▼───────────────────────────┐
│ Rust arka uç: app/src-tauri/src                      │
│  lib.rs (55 komut) · state.rs · commands/*.rs        │
│  embedded.rs (derlemeye gömülü dosyalar)             │
│  crates/borsai_predict (saf model portu)             │
└──────────┬──────────────────────────┬────────────────┘
           │ std::fs (salt okuma +     │ std::process::Command
           │ izinli yazma yolları)     │ (yalnız repo modunda)
┌──────────▼──────────┐   ┌───────────▼──────────────────┐
│ Repo dosyaları       │   │ git (salt okuma alt komutları)│
│ models/, registry/,  │   │ <repo>/.venv Python:          │
│ data/, scores/       │   │  borsai.freeze, market20, …   │
└──────────────────────┘   └───────────────────────────────┘
```

### Ön uç hiç hesap yapmaz

Ön uç bir sayı göstermek istediğinde onu bir komuttan alır. Beklenen seri uzunluğu, koşullu olasılık, düşüş yüzdesi, "fiyat ≈ P × (1 + medyan)" gibi görüntüleme türevleri bile Rust'ta hesaplanır. Bu kural `app/tests/no_frontend_math.test.ts` taramasıyla zorlanır: TypeScript'te çarpma ve bölme yalnız yüzde biçimlendirmesinde ve SVG piksel koordinatında geçebilir. Gerekçe: bir sayının tek bir yerde üretilmesi onu test etmeyi ve Python'la karşılaştırmayı mümkün kılar.

### Açılış sırası

```rust
// app/src-tauri/src/lib.rs (kısaltılmış)
tauri::Builder::default()
    .plugin(tauri_plugin_dialog::init())               // yalnız dosya seçici
    .manage(state::AppState::from_embedded())           // 1) gömülü modelleri doğrula
    .setup(|app| {
        let dir = app.path().app_data_dir()?;            // 2) uygulama verisi dizini
        app.state::<AppState>().attach_data_dir(&dir);   // 3) config.json + repo doğrulaması
        /* 4) çalışma alanı küçükse pencere büyütülür */ Ok(())
    })
    .invoke_handler(tauri::generate_handler![ /* 55 komut */ ])
    .run(tauri::generate_context!())
```

1. `AppState::from_embedded()` gömülü 27 + 1 modeli doğrular (`verify_embedded`, §7.4). Sonuç `Result` olarak saklanır: doğrulama başarısızsa uygulama yine açılır ama bütün tahmin komutları `INTEGRITY_FAILED` döner.
2. Uygulama verisi dizini Tauri'den alınır. Yalnız hata ayıklama (debug) derlemesinde `BORSAI_DATA_DIR` ortam değişkeni bunu başka dizine yönlendirebilir (ekran görüntüsü koşuları gerçek veriye yazmasın diye).
3. `attach_data_dir` ayar dosyasını okur; ayarda repo kökü varsa hızlı repo doğrulaması yapar (Python import denetimi dahil).
4. Pencere ayarları (§7.5).

### `AppState`

```rust
pub struct AppState {
    pub models: Result<Arc<VerifiedModels>, IntegrityError>,  // açılışta bir kez
    pub runtime: Mutex<Runtime>,                              // değişebilen kısım
}
pub struct Runtime {
    pub data_dir: Option<PathBuf>,
    pub config: AppConfig,
    pub config_note: Option<String>,    // CONFIG_RESET
    pub repo: Option<RepoCheck>,        // son repo doğrulaması
    pub scores_fixture: Option<PathBuf>,// yalnız ekran görüntüsü koşusu
}
```

`Arc` (atomik referans sayımlı paylaşım) doğrulanmış model kümesini kopyalamadan paylaştırır; `Mutex` (karşılıklı dışlama kilidi) ayarın iki komut tarafından aynı anda değiştirilmesini önler. Yardımcı yöntemler:

- `repo()` doğrulanmış repo bağlamını (`RepoCtx { root, python }`) ya da `None` döner.
- `require_repo()` repo modu değilse `REPO_MODE_REQUIRED` hatası döner; repo isteyen her komut ilk satırında bunu çağırır.
- `protected_roots()` kişisel kayıt yazımında korunacak kökleri verir: ayardaki repo (doğrulanmamış olsa bile) ve derleme anındaki repo.

### Hata modeli

Bütün komutlar `Result<T, AppError>` döner:

```rust
pub struct AppError { pub code: String, pub message: String, pub detail: Option<String> }
```

`code` makine okunur sabittir (`REPO_MODE_REQUIRED`, `INTEGRITY_FAILED`, `FREEZE_PREFLIGHT_BLOCKED` …); ön uç bunu `app/src/i18n/tr.ts`'teki Türkçe metne çevirir. `message` geliştirici içindir; `detail` ham çıktıdır (örneğin Python'un stderr'i aynen). Böylece Rust kodunda kullanıcıya gösterilecek serbest metin birikmez, metinler tek dosyada kalır.

### Eşzamanlı (sync) ve eşzamansız (async) komutlar

Tauri'de `async` işaretli olmayan komutlar ana iş parçacığında koşar; uzun süren bir iş (Python çağırmak gibi) pencereyi dondurabilir. Bu yüzden Python çağıran komutlar `async fn` olarak yazılmıştır: `set_config`, `validate_repo`, `market20_via_python`, `freeze_preflight`, `inputs_pit_check`, `freeze_record`, `cancel_record`, `post_d1_preflight`, `post_d1_freeze`, `post_d1_cancel`. Hesap ve dosya okuma komutları eşzamanlıdır (sicil görünümü gibi bazıları kısa `git ls-files`/`git log` çağrıları da yapar).

Kaynak dosyalar: `app/src-tauri/src/main.rs`, `lib.rs`, `state.rs`, `commands/mod.rs`, `app/README.md`.

---

## 7.3 Derleme: bağımlılıklar, `build.rs` ve gömme

### Bağımlılık listesi

| Crate | Kimin | Sürüm (`Cargo.lock`) | Ne için |
|---|---|---|---|
| `tauri` | uygulama | 2.11.6 | çatı (pencere, IPC, state) |
| `tauri-build` | derleme | 2.6.3 | `tauri.conf.json`'u derlemeye bağlar |
| `tauri-plugin-dialog` | uygulama | 2.7.3 | dosya seçici (tek eklenti) |
| `serde` | ikisi | 1.0.229 | dönüştürme çatısı |
| `serde_json` | ikisi | 1.0.151 | JSON (`preserve_order`, `float_roundtrip`) |
| `sha2` | ikisi | 0.10.9 | sha256 |
| `num-bigint` | crate | 0.4.8 | sınırsız büyüklükte tamsayı (Decimal katsayısı) |
| `num-integer`, `num-traits` | crate | 0.1.47, 0.2.19 | `gcd`, `div_rem`, sıfır/bir sabitleri |
| `objc2*`, `block2` | uygulama, yalnız macOS, isteğe bağlı | 0.6 / 0.3 | yalnız `snapshot` özelliği (ekran görüntüsü) |

Bilerek **olmayanlar**: HTTP istemcisi (`reqwest`, `ureq`, `hyper`), `tauri-plugin-http`, `fs` ve `shell` eklentileri, `num-rational`. `Cargo.lock`'ta toplam 447 paket kaydı vardır; çoğu Tauri'nin dolaylı bağımlılığıdır. `reqwest` ve `hyper` `Cargo.lock`'ta görünür, çünkü Tauri bunları Android/iOS hedefleri için bildirir; macOS derlemesine girmedikleri `cargo metadata --filter-platform aarch64-apple-darwin` ile sınanır (§7.12, `no_network.rs`).

`Cargo.toml`'daki başka ayarlar:

- `[lib] crate-type = ["staticlib", "cdylib", "rlib"]`: uygulama kodu bir kütüphane (`borsai_app_lib`) olarak derlenir; `main.rs` yalnız `borsai_app_lib::run()` çağırır. Testler bu kütüphaneyi doğrudan kullanır.
- `[features] snapshot`: yalnız geliştirmede ekran görüntüsü almak için macOS WKWebView bağlamaları; varsayılan derlemeye girmez.
- `[profile.release]`: `lto = true` (bütün programı birlikte iyileştir), `codegen-units = 1`, `opt-level = 3`, `panic = "abort"`, `strip = true`.
- `rust-version = "1.77.2"`: Tauri 2'nin istediği en düşük Rust sürümü.

### `build.rs` ne yapar

`build.rs` kısadır; işin çoğu `build_embed.rs`'tedir (aynı dosya testlerde de kullanılsın diye `include!` ile alınır). Adımlar:

1. Repo kökünü bulur (`app/src-tauri/../..`).
2. `plan_embedding`: `models/INDEX.json`'u okur.
   - `schema_version` `borsai.model_index/1` olmalı.
   - INDEX'in **ilk 27 kaydı**, koddaki sabit listeyle (`PINNED_MODEL_IDS`) **sırasıyla** aynı olmalı. Liste: 16 eski model (V1.5, altı sabit kural, V1.6, market20, PB, tavan v0 ve `@INF`, PB tavan ve `@INF`, iki KM kuralı), 3 tavan yolu modeli, 4 `ceiling_hazard_v1` modeli, 4 `fall_d10_v0` modeli. Kural: yeni model INDEX'in sonuna eklenir.
   - Her kaydın `file` adı düz bir ad olmalı (`/`, `\` yok, `.` ile başlamaz) ve dosya diskte bulunmalı.
   - INDEX'te 27'den fazla kayıt varsa fazlası gömülmez, `ignored_model_ids` olarak listelenir (bugün boş).
   - Gömülen modellerden biri **deflatörlü** ise (özelliklerinde `f1r` ve sözlük biçiminde `deflator` bloğu var) `data/raw/tuik/tufe_genel_2025_100.csv` de gömülür; dosya yoksa derleme kırılır. Bugün dört deflatörlü model vardır: `ceiling_hazard_v1_real`, `ceiling_hazard_v1_pooled`, `fall_d10_v0_h99`, `fall_d10_v0_pooled`.
   - `scores/scores.json` ve `scores/scores_oot.json` varsa plana girer.
3. `plan_post_d1`: ikinci dizin `models/INDEX_POST_D1.json`. Kayıtları sabit listeyle (`["post_d1_hazard_v0"]`) **tam olarak** aynı olmalı: fazlası da eksiği de derlemeyi kırar.
4. git'ten iki bilgi okunur: `git rev-parse HEAD` ve `git status --porcelain -- models scores`. git yalnız salt okuma alt komutlarıyla (`rev-parse`, `status`) ve `GIT_OPTIONAL_LOCKS=0` ortam değişkeniyle çağrılır. Bu değişken, paralel bir commit sırasında git'in `index.lock` dosyası bırakmasını önler. git yoksa ya da repo değilse değer `"UNKNOWN"` olur.
5. `scores_oot.json` **süzülür** (aşağıda) ve `OUT_DIR/scores_oot_embedded.json`'a yazılır.
6. `OUT_DIR/embedded.rs` üretilir.
7. `cargo:rerun-if-changed` satırları: `models/`, `scores/`, TÜFE dosyası ve git'in `HEAD`/`refs` dosyaları değişirse `build.rs` yeniden koşar.
8. Son olarak `tauri_build::build()`.

### Üretilen `embedded.rs`

```rust
// OUT_DIR/embedded.rs (build.rs üretir; şekil)
pub const INDEX_JSON: &str = include_str!(".../models/INDEX.json");
pub const EMBEDDED_MODELS: &[EmbeddedModel] = &[
    EmbeddedModel { model_id: "v1_5_h99", file: "v1_5_h99.json", json: include_str!(".../models/v1_5_h99.json") },
    /* … 27 kayıt … */
];
pub const INDEX_POST_D1_JSON: &str = include_str!(".../models/INDEX_POST_D1.json");
pub const EMBEDDED_POST_D1_MODELS: &[EmbeddedModel] = &[ /* post_d1_hazard_v0 */ ];
pub const SCORES_JSON: Option<&str> = Some(include_str!(".../scores/scores.json"));
pub const SCORES_OOT_JSON: Option<&str> = Some(include_str!(".../OUT_DIR/scores_oot_embedded.json"));
pub const TUFE_CSV: Option<&str> = Some(include_str!(".../tufe_genel_2025_100.csv"));
pub const BUILD_INFO: BuildInfo = BuildInfo { git_head: "…", git_status_models_scores: "…",
    index_sha256: "…", index_post_d1_sha256: "…", ignored_index_models: &[] };
```

`src/embedded.rs` yalnız türleri tanımlar ve bu dosyayı `include!(concat!(env!("OUT_DIR"), "/embedded.rs"))` ile içeri alır. `BUILD_INFO.index_sha256`, `build.rs`'in okuduğu INDEX baytlarının sha256'sıdır; açılış doğrulaması (§7.4) gömülü INDEX metnini bununla karşılaştırır.

### `scores_oot.json` süzgeci

`scores/scores_oot.json` eski kohortun zaman-dışı skorlarıdır ve repo anlık kopyasında 41 288 743 bayttır (≈ 41 MB). İçinde arz kodu taşıyan satırlar da vardır. Bağımsız modda bu dosyanın tamamını gömmek hem boyut hem kasa hijyeni açısından istenmez. `filter_scores_oot` **hesap yapmaz, yalnız süzer**: üst düzeyde `schema_version`, `generated_at_utc`, `code`, `cohort_sha256`, `definitions` kalır; altı alt küme bloğunun (`oot_pre_h99`, `oot_pre_h99_sealed`, `oot_pre_h99_all`, `post_d1`, `post_d1_sealed`, `post_d1_all`) başlık ve sayaçları aynen kalır; `models[]` öğelerinden yalnız `rows` ve `retro_info` atılır; üst düzey `retro_info` gömülmez. Sonuna `embedded_copy: {source_sha256, rows_embedded: false, note}` eklenir. P1 raporuna göre gömülü kopya 744 206 bayttır.

### Derlemeyi bilerek kıran durumlar

| Durum | Neden kırılır |
|---|---|
| INDEX'in ilk 27 kaydı sabit listeden farklı (sıra ya da küme) | uygulamanın hangi modelleri desteklediği koddadır; sessizce değişemez |
| INDEX'te olup diskte olmayan model dosyası | eksik dosyayla çalışan uygulama olmaz |
| `INDEX_POST_D1.json` kayıtları sabit listeden farklı | ikinci dizin tek modelle dondurulmuştur |
| Deflatörlü model varken TÜFE tablosu yok | bağımsız modda deflatörün tek kaynağı gömülü tablodur |
| Dosya adı yol parçası içeriyor | `include_str!` yolu `models/` dışına kaçmasın |

Bu kurallar `app/src-tauri/tests/build_embed.rs`'teki yedi testle sınanır (§7.12).

Kaynak dosyalar: `app/src-tauri/Cargo.toml`, `Cargo.lock`, `build.rs`, `build_embed.rs`, `src/embedded.rs`, `tests/build_embed.rs`, `docs/app/p1/RAPOR.md`.

---

## 7.4 Açılış bütünlüğü: sha256 zinciri

Uygulama her açılışta, hiçbir komut çalışmadan önce, gömülü model kümesini doğrular (`commands/models.rs: verify_embedded`). Amaç: ikilinin içindeki model dosyası ile INDEX'in "bu dosya budur" dediği şey birebir aynı olsun; tek uyuşmazlıkta hiçbir model tahmin vermesin.

### Birinci dizin (`verify`)

Sırayla:

1. Gömülü `INDEX_JSON` metninin sha256'sı = `BUILD_INFO.index_sha256`. Değilse `INDEX_SHA_MISMATCH`.
2. INDEX ayrıştırılır, sürümü `borsai.model_index/1` olmalı. Değilse `INDEX_INVALID`.
3. Her gömülü model için, INDEX sırasıyla:
   - INDEX'in i. kaydının `model_id` ve `file` alanı gömülü kayıtla aynı (`ORDER_MISMATCH`, `MODEL_NOT_IN_INDEX`).
   - Gömülü JSON baytlarının sha256'sı = INDEX kaydındaki `sha256` (`MODEL_SHA_MISMATCH`).
   - JSON ayrıştırılır ve **parametre denetiminden** geçer: `borsai_predict::check_params`, Python'daki `_check_params`'ın birebir portudur (model türüne göre gerekli alanlar, boyutlar, kolon eşleşmeleri). Python'un yalnız kullanırken `KeyError` verdiği eksik alanlar da burada `PARAMS_INVALID` sayılır. Hata `PARAMS_INVALID` ya da `SCHEMA_UNSUPPORTED`.
4. **Seri modeli kopyası denetimi (U41):** üç tavan yolu modelinin her biri, kendi içinde bir tavan serisi modelinin tam kopyasını taşır (`survival_model`). Bu kopyanın (a) `survival_model_sha256` alanı INDEX'teki o modelin sha256'sına eşit, (b) o model gömülü kümede ve dosya sha'sı aynı, (c) kopyanın JSON değeri gömülü dosyanın ayrıştırılmış değerine yapısal olarak eşit olmalı. Değilse `SURVIVAL_MODEL_MISMATCH`.

### İkinci dizin (`verify_post_d1`)

D1 sonrası model (`post_d1_hazard_v0`) bir **ofset modelidir**: ana tavan modelinin (`ceiling_hazard_v0`) doğrusal öngörücüsünü aynen kullanır ve üstüne D1 bilgisiyle bir kayma ekler (§7.8.8). Ana modelin parametreleri değişirse bu modelin anlamı bozulur. Bu yüzden zincir ayrıca denetlenir:

- `INDEX_POST_D1.json` sha256'sı = `BUILD_INFO.index_post_d1_sha256`; kayıt sayısı ve sırası gömülüyle aynı; dosya sha256'sı dizindekiyle aynı.
- Ebeveyn: dizin kaydının `parent_sha256` = INDEX'teki `ceiling_hazard_v0` sha'sı = gömülü dosyanın sha'sı = modelin JSON'undaki `parent.sha256`; `parent.model_id` aynı.
- İkincil tavan yolu: JSON'daki `path_secondary.sha256` = gömülü `ceiling_path_v0` dosyasının sha'sı.
- `parse_post_d1(post, parent, path)` ve ebeveyn ile tavan yolunun kendi parametre denetimleri geçmeli.

Herhangi bir uyuşmazlık `POST_D1_PARENT_MISMATCH` olur. Repo anlık kopyasında bu değerler tutarlıdır: ikinci dizindeki `parent_sha256` ile INDEX'teki `ceiling_hazard_v0` sha'sı aynı (`caa4dc86…`), INDEX sha256'sı `7e636e8b…`, ikinci dizinin sha256'sı `94ac36fa…`; INDEX'teki 27 dosyanın hepsinin sha256'sı diskteki dosyalarla eşleşiyor (bu bölüm için Python ile yeniden hesaplandı).

### Uyuşmazlıkta ne olur

`IntegrityError { model_id, reason_code, message }`, `AppState.models`'e `Err` olarak yazılır. Tahmin yapan her komut ilk iş `state.models.as_ref().map_err(|e| e.to_app_error())?` çağırır; sonuç `INTEGRITY_FAILED` kodlu hata ve ekranda kırmızı bant ("Gömülü model dosyası INDEX ile uyuşmuyor: \<model\> (\<neden\>)"). Kısmi çalışma yoktur: 27 modelden biri bozuksa öteki 26'sı da çalışmaz. Gerekçe: kullanıcı ekranda gördüğü sütunun hangi parametreyle üretildiğinden emin olamıyorsa hiçbir sütuna güvenemez.

`app_info` komutu doğrulama sonucunu, derleme bilgisini (git HEAD, `git status`), gömülü ve gömülmeyen model listesini, her modelin açıklamasını, INDEX'teki eğitim n'ini ve kesim tarihini, gömülü TÜFE tablosunun son ayını ve pin durumunu "Hakkında" ekranına verir.

Kaynak dosyalar: `app/src-tauri/src/commands/models.rs`, `crates/borsai_predict/src/params.rs` (`check_params`), `tests/integrity.rs`.

---

## 7.5 Pencere, güvenlik ve yazma yolları

### `tauri.conf.json`

| Alan | Değer | Anlamı |
|---|---|---|
| `identifier` | `tr.borsai.app` | uygulama kimliği; uygulama verisi dizininin adı |
| `build.devUrl` | `http://localhost:1420` | geliştirmede Vite sunucusu (sabit port) |
| `build.frontendDist` | `../dist` | sürüm derlemesinde gömülen ön uç |
| `app.withGlobalTauri` | `false` | `window.__TAURI__` enjekte edilmez; ön uç `@tauri-apps/api`'yi modül olarak alır |
| pencere | 1440 × 900, `center: true`, en küçük 1024 × 680 | aşağıda |
| `security.csp` | aşağıda | |
| `bundle.targets` | `app`, `dmg` | yalnız macOS paketleri |
| `bundle.macOS.signingIdentity` | `"-"` | ad-hoc imza (kişisel kullanım) |

**Pencere.** Varsayılan 1440 × 900 mantıksal piksel, ekranın ortasında; en küçük 1024 × 680 (bu boyutta hiçbir sade ekranda yatay kaydırma çıkmaması hedeflenmiştir). `lib.rs`'teki `setup` adımı monitörün çalışma alanını okur; 1440 × 900'den küçükse pencereyi büyütülmüş (maximize) açar. Aynı sayılar `lib.rs`'te `DEFAULT_WINDOW = (1440.0, 900.0)` ve `MIN_WINDOW = (1024.0, 680.0)` sabitleridir; bir cargo testi (`tests/sade.rs::window_config_k_fix_6`) `tauri.conf.json` ile bu sabitlerin eşitliğini sınar, biri ötekinden habersiz değiştirilemez.

### CSP, yönerge yönerge

```
default-src 'self'; connect-src 'self' ipc: http://ipc.localhost; img-src 'self' data:; style-src 'self' 'unsafe-inline'
```

- `default-src 'self'`: başka bir yönergeyle izin verilmeyen her şey (betik dahil) yalnız uygulamanın kendi kaynağından yüklenebilir. Dış bir CDN'den betik yüklenemez.
- `connect-src 'self' ipc: http://ipc.localhost`: ağ bağlantısı (fetch, XHR, WebSocket) yalnız uygulamanın kendisine ve Tauri'nin IPC kanalına. `ipc:` macOS/Linux'taki özel protokoldür; `http://ipc.localhost` Windows'ta WebView2'nin IPC adresidir. Dış bir sunucuya istek atılamaz.
- `img-src 'self' data:`: resimler yalnız uygulamadan ya da `data:` URI'lerinden.
- `style-src 'self' 'unsafe-inline'`: stiller uygulamadan; satır içi stile izin vardır (SVG çizimi ve dinamik stil için). Satır içi **betiğe** izin yoktur.

### Capabilities

`capabilities/default.json` ana pencereye yalnız iki izin verir: `core:default` (Tauri çekirdeğinin varsayılan güvenli komutları) ve `dialog:default` (dosya seçici). `fs`, `shell`, `http` eklentileri yüklenmemiştir; dosya okuma/yazma ve süreç çalıştırma yalnız Rust komutlarının içinde, kodla denetlenen yollarda yapılır. Uygulamanın kendi komutları (`generate_handler!` listesi) bu dosyada ayrıca listelenmez.

### Ağ yok

SPEC_APP §3a.2'nin kararı: uygulama hiçbir koşulda ağa çıkmaz. Bu dört katmanda sağlanır: (1) bağımlılıklarda HTTP istemcisi yok, (2) HTTP eklentisi yok, (3) CSP dış bağlantıyı yasaklar, (4) Python çağrıları yalnız ağ gerektirmeyen işler içindir (pinli XU100 dosyası ve takvimden f6 hesabı, kayıt yazımı). Bülten indirmek gibi ağ isteyen işler yalnız kopyalanabilir **komut metni** olarak gösterilir; kullanıcı kendi terminalinde çalıştırır.

### git: salt okuma beyaz listesi

Uygulamanın çalışma anında git çağırdığı tek yer `commands/git.rs`'tir (derleme tarafında `build_embed.rs`). Beyaz liste: `rev-parse`, `status`, `log`, `ls-files`. İlk argüman listede değilse `GIT_NOT_ALLOWED`; `-c` ya da `--exec-path` gibi seçeneklerle başlatmak da reddedilir, çünkü ilk argüman alt komut olmak zorundadır. Her çağrı `GIT_OPTIONAL_LOCKS=0` taşır. Uygulama `add`, `commit`, `push`, `tag` **çalıştırmaz**; bu komutlar yalnız ekranda metin olarak gösterilir (U32 testi).

Kullanım yerleri: repo doğrulaması ve ön koşullar (`rev-parse HEAD`), sicil ve D1 sonrası dizinlerinin durumu (`status --porcelain -- registry`; `-- data registry/post_d1`), kayıt dosyalarının izlenip izlenmediği (`ls-files`) ve dosyayı ekleyen commit (`log --diff-filter=A --format=%H -1 -- <yol>`; push kanıtını eşlemek için).

### Python: yalnız repo modunda ve ağsız

`python.rs` tek bir yardımcı içerir:

```rust
Command::new(python).current_dir(repo)
    .env("PYTHONDONTWRITEBYTECODE", "1")   // repo ağacına __pycache__ bile yazılmaz
    .env("PYTHONNOUSERSITE", "1")          // kullanıcı site-packages'ı karışmaz
    .args(args)
```

Çıkış kodu 0 değilse `PYTHON_FAILED` (stderr `detail`'de aynen); yorumlayıcı bulunamazsa `PYTHON_NOT_FOUND`. Python'un hangi işler için çağrıldığı §7.9.4'teki tabloda toplanmıştır.

### Uygulama nereye yazar

| Yer | Ne | Kim yazar |
|---|---|---|
| `<app_data_dir>/config.json` | ayar (`borsai.app_config/1`) | Rust; geçici dosya + `rename` (yarım dosya kalmaz) |
| `<app_data_dir>/scenarios/<ULID>.json` | kişisel kayıt (`borsai.app_scenario/1`) | Rust; `create_new` (var olanın üzerine yazmaz) |
| kullanıcının seçtiği dışa aktarma yolu | kişisel kaydın kopyası | Rust; repo altıysa ret |
| `<repo>/registry/inputs/<T>.json`, `<T>.PB.json` | girdi belgesi | Rust (Python'la bayt-eşit biçimde), fark onayıyla |
| `<repo>/registry/source_docs/<T>/` + `MANIFEST.json` | kaynak PDF kopyaları | Rust; var olan giriş değiştirilmez |
| `<repo>/app/parity/incidents/<UTC>.json` | parite uyuşmazlığı olayı | Rust; yalnız uyuşmazlıkta |
| `<repo>/registry/records/<T>/…` | resmî tahmin ve iptal kaydı | **Python** (`borsai.freeze`), uygulamanın çağrısıyla |
| `<repo>/registry/post_d1/<T>/…` | D1 sonrası kayıt ve iptali | **Python** (`borsai.freeze --post-d1`, `--cancel`) |

Uygulama `data/outcomes/`, `scores/`, `models/` ve eski kohort dizinine (`registry/oot/`) hiç yazmaz; eski kohort dizinini hiçbir komutta okumaz da.

### Yol bekçileri

Dışarıdan gelen her yol ve kod parçası denetlenir:

- `valid_ticker`: arz kodu 2–12 karakter, yalnız büyük harf ve rakam. Yol parçası olarak güvenlidir.
- `safe_rel` (dondur): göreli yol, istenen önekle başlar (`registry/inputs/`, `registry/records/`), `..` içermez, `/` ile başlamaz, `.json` ile biter, yalnız harf, rakam ve `._-/@` karakterlerinden oluşur. `safe_post_rel` D1 sonrası kayıtlar için aynı işi `registry/post_d1/<T>/<dosya>.json` kalıbıyla yapar.
- `resolve_path` + `guard_outside` (kişisel kayıt, U27): kişisel kaydın repo altına düşmemesi bir değişmezdir. Rust'ın `canonicalize`'ı tek başına yetmez; askıda (hedefi olmayan) bir sembolik bağ ya da var olmayan ara dizinli `..` en yakın var olan ataya düşer ve bağın gösterdiği yeri görmez. `resolve_path` yolu bileşen bileşen yürür, her sembolik bağı `read_link` ile izler (en çok 40 halka), `..`'ı o ana kadar çözülmüş fiziksel yoldan atar. Fable denetiminin tek KRİTİK bulgusu (B1: askıda bağ üzerinden kişisel kayıt `registry/records/` altına yazılabiliyordu) bu düzeltmeyle kapandı.
- `write_export`: dışa aktarma hedefi hiçbir koşulda bağ izlemez. Hedef yoksa `create_new` (O_EXCL; arada biri bağ koyarsa "dosya var" hatası); hedef normal dosyaysa aynı dizinde geçici dosyaya yazılıp `rename` edilir; hedefin kendisi bağsa reddedilir (nereyi gösterirse göstersin; kapanış denetiminin C1 notu: güvenli yönde aşırı ret).
- Uygulama verisi dizini repo altına düşerse (`DATA_DIR_INSIDE_REPO`) ayar kaydedilmez.

### Windows uyumu notları

Şartname hedefi açıkça **yalnız macOS arm64**'tür (SPEC_APP özet madde 1); Windows'ta derlenip sınanmış bir sürüm belgelenmemiştir. Kodda Windows'a dönük izler ve olası sorunlar (sorun olanlar ölçülmedi, çıkarımdır):

- Var olanlar: `main.rs`'teki `windows_subsystem = "windows"` (sürüm derlemesinde ek konsol penceresi açılmaz), CSP'deki `http://ipc.localhost`, simge listesindeki `icon.ico`, yol metinlerinde `\` → `/` dönüşümü (`rel_of`), kökteki `.gitattributes`'ın `* text=auto eol=lf` kuralı (model JSON'ları ve TÜFE tablosu Windows'ta da LF ile çekilir; CRLF olsaydı sha256'lar ve TÜFE ayrıştırması bozulurdu).
- Olası sorunlar [çıkarım]: varsayılan Python yolu `.venv/bin/python`'dır (Windows sanal ortamında `.venv\Scripts\python.exe`; Ayarlar'dan elle verilebilir); `resolve_path` sürücü önekini (`C:`) köke çevirir, Windows yollarında yanlış sonuç verebilir; "Şimdi yapılacaklar" bloklarındaki `$(git rev-parse HEAD)` bash/zsh sözdizimidir (PowerShell'de alt ifade olarak çalışır, cmd.exe'de çalışmaz); `bundle.targets` yalnız macOS paketleridir; ağ yokluğu testi yalnız `aarch64-apple-darwin` grafiğini tarar; ekran görüntüsü özelliği yalnız macOS'tadır.

Kaynak dosyalar: `app/src-tauri/tauri.conf.json`, `capabilities/default.json`, `src/lib.rs`, `src/python.rs`, `src/commands/git.rs`, `src/commands/config.rs` (`resolve_path`), `src/commands/scenario.rs`, `src/commands/freeze.rs` (`safe_rel`), `tests/no_network.rs`, `docs/fable_app_audit/AUDIT.md`, `KAPANIS.md`, kökteki `.gitattributes`.

---

## 7.6 Ayar dosyası, görünüm seçimi ve repo modu doğrulaması

### `config.json`

Konum: Tauri'nin `app_data_dir()`'i + `config.json`. macOS'ta bu `~/Library/Application Support/tr.borsai.app/config.json`'dur (SPEC_APP §2.4). Şema:

```rust
pub struct AppConfig {
    pub schema_version: String,      // "borsai.app_config/1"
    pub repo_root: Option<String>,
    pub python_path: Option<String>, // boşsa <repo>/.venv/bin/python
    pub scores_source: String,       // "REPO" | "EMBEDDED"
    #[serde(default = "default_ui_view")]
    pub ui_view: String,             // "SADE" (varsayılan) | "AYRINTILI"
}
```

- **Okuma (`load_config`)**: dosya yoksa varsayılan. Ayrıştırılamıyorsa, sürümü farklıysa ya da `scores_source` geçersizse dosya `config.json.bak` adıyla saklanır, varsayılana dönülür ve `CONFIG_RESET` notu düşülür (SPEC_APP §2.5). `ui_view` sonradan eklenmiş, geriye uyumlu bir alandır: yoksa `SADE`; tanınmayan bir değer ayarı sıfırlamaz, yalnız görünümü `SADE`'ye döndürür.
- **Yazma (`save_config`)**: önce `config.json.tmp`, sonra `rename`. Yarıda kesilen bir yazım eski dosyayı bozmaz.
- **`set_config(cfg)`**: sürüm, `scores_source` ve `ui_view` değerleri denetlenir (`INVALID_ARGUMENT`); boşluklar kırpılır; repo verilmişse hızlı doğrulama koşar. Uygulama verisi dizini repo altına düşüyorsa `DATA_DIR_INSIDE_REPO` ile ret. Öteki denetimler başarısızsa ayar **yine kaydedilir**, yalnız repo modu kapalı kalır ve gerekçeler ekranda görünür.
- **`set_ui_view(view)`**: yalnız görünüm seçimini değiştirir, repo doğrulamasını yeniden koşmaz. Sade görünüm (UI v2) varsayılandır; ayrıntılı görünüm eski arayüzdür ve kodu, testleriyle aynen durur.

### Repo modu doğrulaması (`validate_repo_value`)

| Denetim | Zorunlu mu | Ne bakar |
|---|---|---|
| `REPO_DIR` | evet | yol var ve dizin (kanonik hâli) |
| `DATA_DIR_OUTSIDE_REPO` | evet | uygulama verisi repo altında değil (`resolve_path` ile) |
| `INDEX_SHA` | evet | `<repo>/models/INDEX.json` sha256'sı = gömülü INDEX sha'sı |
| `GIT_HEAD` | evet | `git rev-parse HEAD` başarılı |
| `PYTHON_IMPORT` | evet | `python -c "import borsai, os; print(os.path.realpath(borsai.__file__))"` başarılı **ve** basılan yol repo altında (başka bir yerdeki `borsai` paketine sızma yok) |
| `OUTCOMES_DIR` | hayır (bilgi) | `data/outcomes/` var |
| `TUFE_TABLE` | hayır (bilgi) | repo TÜFE tablosunun son ayı ve dört deflatör pininin tutup tutmadığı |
| `MARKET20_SOURCES` | hayır (yalnız derin doğrulama) | `borsai.market20.load_live_sources()`: XU100 son günü, takvim son günü, XU100 dosya sha'sı |

Repo modu = zorunlu denetimlerin hepsi geçti. Ayarlar ekranındaki "Doğrula" düğmesi (`validate_repo` komutu) derin doğrulamayı kaydetmeden yapar; açılışta ve `set_config`'te hızlı doğrulama (market20 kaynakları hariç) koşar.

`INDEX_SHA` denetimi önemlidir: uygulamaya gömülü modeller ile repodaki modeller farklıysa (uygulama eski derlenmiş), uygulamanın tahmini ile Python'un yazacağı kayıt farklı modellerden gelir. Bu durumda repo modu açılmaz; dondur akışı da aynı denetimi ayrıca yapar (§7.9.4).

Kaynak dosyalar: `app/src-tauri/src/commands/config.rs`, `src/state.rs`, `docs/app/SPEC_APP.md` §2.4–§2.5, `docs/app/UI_V2_RAPOR.md`.

---

## 7.7 Komut kataloğu

`lib.rs`'teki `generate_handler!` listesinde **55 komut** vardır. Aşağıdaki tablolar onları işlevine göre gruplar. "Mod" sütunu: **her ikisi** = bağımsız ve repo modunda çalışır; **repo** = `require_repo()` çağırır, bağımsız modda `REPO_MODE_REQUIRED` döner. Argüman adları Rust'taki hâlleridir (ön uç camelCase gönderir).

### Uygulama, ayar, form, tahmin

| Komut | Girdi | Çıktı | Okur / çağırır | Ne hesaplar | Mod |
|---|---|---|---|---|---|
| `app_info` | — | `AppInfo` | gömülü INDEX, modeller, TÜFE | sürüm, git HEAD, sha'lar, bütünlük, model kartları, TÜFE pin durumu | her ikisi |
| `get_config` | — | `ConfigView` | bellekteki ayar | ayar + repo denetimi + önerilen repo kökü | her ikisi |
| `set_config` | `cfg: AppConfig` | `ConfigView` | `config.json`, repo, git, Python | biçim denetimi, hızlı repo doğrulaması, yazım | her ikisi |
| `validate_repo` | `path`, `python_path?` | `RepoCheck` | repo, git, Python (market20 kaynakları dahil) | derin doğrulama, kaydetmez | her ikisi |
| `set_ui_view` | `view` | `ConfigView` | `config.json` | yalnız `ui_view` | her ikisi |
| `check_form` | `stage?`, `fields` | `FormCheck` | — | §7.9.1 | her ikisi |
| `predict_all` | `inputs`, `f6?`, `t?` | `ModelRun[]` (27) | gömülü modeller, TÜFE (repo ya da gömülü) | 27 modelin tahmini | her ikisi |
| `market20_via_python` | `ref_date?`, `t?` | `Market20View` | Python `borsai.market20` | f6 (XU100 20 seans getirisi) | repo |

### Girdi belgesi ve kaynak belgeler (dondur adım 2–3)

| Komut | Girdi | Çıktı | Okur / yazar | Ne yapar | Mod |
|---|---|---|---|---|---|
| `list_input_documents` | — | arz kodları | `registry/inputs/*.json` | listeler (`.PB.json` adları kod kuralına uymadığı için listeye girmez) | repo |
| `read_input_document` | `ticker` | `InputDocument` | `registry/inputs/<T>.json` | salt okuma; sürüm farklıysa `INPUTS_SCHEMA_UNSUPPORTED` | repo |
| `preview_inputs_doc` | `req` | `InputsDocPreview` | MANIFEST, var olan belge | belgeyi kurar, Rust `validate_inputs`, satır farkı, sha256; yazmaz | repo |
| `write_inputs_doc` | `req`, `confirm` | `InputsDocPreview` | yazar: `registry/inputs/<T>[.PB].json` | sorun varsa ret; dosya farklıysa onay ister (`INPUTS_DOC_EXISTS`) | repo |
| `copy_source_docs` | `ticker`, `docs` | `SourceDocsView` | yazar: `registry/source_docs/<T>/`, `MANIFEST.json` | önce hepsini okur ve çakışma arar, sonra yazar; farklı sha → `SOURCE_DOC_CONFLICT` | repo |
| `read_source_manifest` | `ticker` | MANIFEST JSON | `registry/source_docs/<T>/MANIFEST.json` | salt okuma | repo |

### Resmî kayıt (dondur) ve sicil

| Komut | Girdi | Çıktı | Okur / çağırır | Ne yapar | Mod |
|---|---|---|---|---|---|
| `freeze_preflight` | `t?` | `Preflight` | git, repo INDEX, Python, TÜFE | adım 1 ön koşulları ve engeller | repo |
| `inputs_pit_check` | `rel_path` | sorun listesi | Python `registry.inputs_pit_problems` | adım 4 yetkili denetim | repo |
| `freeze_record` | `rel_path` | `FreezeResult` | Python `borsai.freeze`, kayıt, gömülü modeller | ön koşulları yeniden denetler, kaydı yazdırır, parite | repo |
| `cancel_record` | `rel_path`, `reason` | `CancelResult` | Python `borsai.freeze --cancel` | iptal kaydı | repo |
| `freeze_todo` | `ticker`, iki yol | komut satırları | — | "Şimdi yapılacaklar" metni | repo |
| `registry_view` | — | `RegistryView` | `registry/records/**`, `ipos.csv`, `push_proofs/`, git | sicil listesi, iptal bağları, push kanıtı göstergesi | repo |
| `record_ceiling` | `ticker`, `file`, `j` | `RecordCeiling` | kayıt dosyası | arz sayfası: S yalnız kayıttan + hesaplayıcı eki | repo |
| `read_record_json` | `ticker`, `file` | kayıt JSON | kayıt dosyası | ham kayıt | repo |

### Tavan serisi, tavan yolu, özet kartlar

| Komut | Girdi | Çıktı | Okur | Ne hesaplar | Mod |
|---|---|---|---|---|---|
| `ceiling_display` | `models: [{model_id, S}]`, `j`, `ipo_price_tl?` | `CeilingDisplay` | gömülü model dosyaları (yalnız hesaplayıcı eki için) | P_L, beklenen/medyan/en olası L, koşullu değerler, "her zaman tavan" satırı, 1.1^k fiyat ipucu | her ikisi |
| `streak_view` | `ticker?` | `StreakView` | `data/outcomes/<T>.csv` | gün gün şerit ve resmî j | her ikisi (dosya yalnız repo modunda okunur) |
| `ceiling_summary` | `runs`, `j`, `j_observed?`, `t?` | `CeilingSummary` | `scores.json`, `scores_oot.json`, TÜFE | "Tavan serisi — kaç gün tavan?" kartı + "Düşüş (D10)" kartı | her ikisi |
| `record_summary` | `ticker`, `file`, `j`, `j_observed?` | `CeilingSummary` | kayıt + skor dosyaları + D1 sonrası kayıt | aynı kart, değerler yalnız kayıttan | repo |
| `path_display` | `models: [{model_id, output}]` | `PathDisplayRow[]` | — | limit atomuysa kayıttaki `C_h` metni, değilse P × (1 + medyan) | her ikisi |
| `path_conditional` | `model_id`, `source`, `j_or_t`, `state_name` | `PathConditional` | kayıt ya da verilen çıktı, `data/outcomes` | koşullu getiri dağılımı (seri sürüyor / kırıldı) | her ikisi (kayıt kaynağı repo ister) |
| `path_params` | — | `PathParamsInfo[]` | gömülü tavan yolu modelleri | hücre bilgisi (n, kesim) | her ikisi |

### D1 sonrası

| Komut | Girdi | Çıktı | Ne yapar | Mod |
|---|---|---|---|---|
| `post_d1_records` | `ticker` | kayıt satırları | `registry/post_d1/<T>/` listesi, iptal bağları, push kanıtı | repo |
| `post_d1_view` | `ticker`, `j`, `file?` | `PostD1View` | kaydın S'inden koşullu satır (yalnız j ≥ 1) | repo |
| `post_d1_preflight` | `ticker` | `PostD1Preflight` | sihirbaz adım 1 (§7.10) | repo |
| `post_d1_freeze` | `ticker` | `PostD1FreezeResult` | Python `freeze --post-d1`, parite | repo |
| `post_d1_cancel` | `rel_path`, `reason` | `PostD1CancelResult` | Python `freeze --cancel` | repo |
| `post_d1_todo` | `kind`, `ticker`, `through?` | komut satırları | adım 2 (`OUTCOMES`) ya da 4 (`RECORD`) metni | repo |

### Kişisel kayıtlar (senaryo)

| Komut | Girdi | Çıktı | Ne yapar |
|---|---|---|---|
| `save_scenario` | `req` | özet | çıktıları **Rust `predict_all` ile yeniden üretir** (ön uçtan sayı almaz), `scenarios/<ULID>.json` yazar |
| `list_scenarios` | — | özetler | `OK` / `OLD_VERSION` / `UNREADABLE`, "gömülü kümeyle aynı mı" |
| `load_scenario` | `id` | kayıt | çıktıyı olduğu gibi döner; INDEX sha farklıysa bayrak, yeniden hesap yok |
| `delete_scenario` | `id` | — | dosyayı siler |
| `export_scenario` | `id`, `target` | yol | repo altına ret, bağ izlemeyen yazım |
| `export_all_scenarios` | `target` | sayaçlar | tek JSON dizisi; okunamayanlar sayılır |

Hepsi her iki modda çalışır. Kişisel kayıtta `record_type` anahtarı yoktur ve `official: false` sabittir; dosya bir şekilde sicil dizinine düşse bile Python'un `active_records`'u onu saymaz. ULID, 48 bit milisaniye + 80 bit rastgele değerin Crockford base32 ile yazılmış 26 karakterlik kimliğidir; zamana göre sıralanabilir.

### Skorlar ve sade görünüm

| Komut | Okur | Ne yapar | Mod |
|---|---|---|---|
| `score_hints` | `scores.json` (repo ya da gömülü) | model kartı alanları, backtest MAE hücreleri, canlı n | her ikisi |
| `scores_view` | `scores.json` | doğruluk paneli; sürüm ve **fail-closed** bütünlük denetimi | her ikisi |
| `scores_post_d1_view` | `scores/scores_post_d1.json` | gömülmez; `NO_REPO` / `NO_FILE` / `REPO` | repo dosyası |
| `scores_oot_view`, `scores_oot_model` | `scores_oot.json` (repo, önbellekli; ya da süzülmüş gömülü) | zaman-dışı panel; satırlar yalnız açık kümede | her ikisi |
| `monitor_view` | sicil, `data/outcomes`, makine kayıtları, skor dosyaları, git | izlenen arzlar, sayaçlar, olay akışı | repo |
| `arz_view` | aynı + kayıt | tek arzın görünümü (P_close_ceiling kayıttan) | repo |
| `perf_view` | skor dosyaları | birincil hücreler, hüküm sayımları | her ikisi |
| `headline_gate` | skor dosyaları | hangi çıktı ana ekranda "öne çıkar" | her ikisi |
| `break_view` | `registry/post_break/<T>/machine_*.json`, `scores_break.json`, `models/break_floor_v0.json` | kırılma akşamı kartı; katsayılar yalnız sha eşitse | repo |

### Yalnız geliştirme

`dev_snapshot`, `dev_scores_fixture`, `dev_snapshot_done`, `dev_window_size`: `--features snapshot` ve `BORSAI_SNAPSHOT_DIR` olmadan hepsi `SNAPSHOT_UNAVAILABLE` döner. Kayıtlıdırlar ama üretimde iş yapmazlar.

### Modüllerden notlar

Tabloların kısa bıraktığı birkaç ayrıntı:

- **`ceiling.rs`** görüntüleme türevlerini hesaplar ve hiçbirini kayda yazmaz: beklenen L = Σ l·P_L[l]; medyan L = Σ_{i≤l} P_L[i] ≥ 0.5 olan en küçük l; en olası L = en büyük P_L[l] (eşitlikte küçük l). Koşullu değerler yalnız `survival::conditional`'dan gelir (§7.8.5). **Hesaplayıcı eki** (`attach_calc`, FAZ9_UI_FIX K-FIX-3): basit kuralın (`base_km_expanding`) seçilen j'deki koşullu değeri S_{j+1}/S_j ve kural dosyasındaki eğitim n'i ile "j gün tavan yapan n arzdan m tanesi" sayımları; sayımlar ancak S_j·n ve S_{j+1}·n 1e-9 içinde tamsayıysa verilir. Gün grupları model dosyasındaki `day_groups`'tan okunur, ekranda sabit "4–10" yazılmaz.
- **Gözlenen seri ve beyan (U52).** Resmî j yalnız `data/outcomes/<T>.csv`'den gelir: h = 1'den başlayarak `status = OK` ve `ceiling_close = 1` olan ardışık günler sayılır; `ceiling_close = 0` seriyi bozar, `NA_LIMIT`/`TARGET_UNAVAILABLE` "etiket yok" olarak durdurur, `PENDING` ya da eksik satır durdurur. Kullanıcının "seri sürüyor" beyanı bu modülün **hiçbir fonksiyon imzasında yoktur**; yalnız ön uçta etiket ve kişisel kayıtta `observed_streak_user` alanı olarak yaşar. Test, Rust komutlarının imzalarını tarayarak bunu sınar.
- **Kart sırası ve öne çıkarma.** `ceiling_summary` satır sırası: öne çıkan model → v1 adayları → v0 → kurallar (`@INF` ve KM) → PB aynası → "her zaman tavan". Öne çıkan, `scores::featured_ceiling` ile **dosyadaki alanların karşılaştırılmasıyla** seçilir: kasa bloğu yoksa `ceiling_hazard_v0`; varsa her aday için k1 = kasa birincil hücresi "geçiyor", k2 = v0'a karşı aralığın üst ucu < 0, k3 = yakın dönem etiketi "bozuyor" değil; uygunlar arasından `round(model_value, 3)` en küçük olan (eşitlikte basit olan), uygun yoksa v0. Hiçbir model listeden çıkarılmaz. Düşüş kartı (`commands/fall.rs`) aynı kalıbı `featured_fall` ile izler; P(düşüş) = 1 − p_up ve gösterim yüzdeleri k = round(100·(1 − p_up)), 100 − k burada hesaplanır.
- **Resmî görünümde model yeniden çalıştırılmaz (U38).** `record_ceiling`, `record_summary`, `post_d1_view` ve kayıt kaynaklı `path_conditional` S vektörlerini ve çıktıları **yalnız dondurulmuş kayıttan** okur. `path_conditional` ayrıca kayıttaki `params_sha256` gömülü sha'dan farklıysa hesap yapmaz (`PATH_PARAMS_SHA_MISMATCH`); eldeki çıktıdan hesaplarken sha zorunludur (denetim bulgusu B8 düzeltmesi).
- **Skor dosyaları "olduğu gibi" aktarılır.** `scores.rs` hiçbir hücreyi hesaplamaz, düzeltmez, doldurmaz. Bütünlük denetimi fail-closed'dur: canlı n < 10 iken hücre varsa, "geçiyor/geçemiyor" hükmü n < 30 ya da 0'ı içeren/eksik aralıkla verilmişse, "ayırt edilemiyor" 0'ı dışlayan aralıkla verilmişse, `n_live + n_late ≠ n_scored` ise panel yerine ihlal gösterilir. `scores_oot.rs` aynı kuralları zaman-dışı dosyaya uygular; büyük repo dosyasını bir kez ayrıştırıp (yol, boyut, değişme zamanı aynı kaldıkça) önbellekte tutar ve satırlardan yalnız açık küme bloğunun `open == true` satırlarını özetleyerek saklar. Kasa (SEALED) üyelerinin kodları panelde, test fikstürlerinde ve hata metinlerinde hiç görünmez.
- **Sade görünüm komutları** (`sade.rs`, `sade_break.rs`) yalnız okur, eşler, sayar ve sıralar. "Öne çıkan" kararı yalnız `headline_gate`'te ve yalnız dosyada önceden ilan edilmiş birincil hücrenin `verdict`'inden verilir. `break_view` kırılma modelini (`break_floor_v0`) **çalıştırmaz**: olasılıkları makine kaydından okur; katsayıları ancak `models/break_floor_v0.json` dosyasının sha256'sı makine kaydındaki `params_sha256`'ya eşitse döner, değilse kart kapanır (`SHA_MISMATCH`). Bu model 27'lik gömülü kümede değildir. Bülten dosya adları ve eğitim arz listeleri hiçbir görünümde dönmez.

Kaynak dosyalar: `app/src-tauri/src/lib.rs`, `src/commands/*.rs` (hepsi), `app/src/api.ts`, `docs/app/UI_FIX_RAPOR.md`, `docs/app/SPEC_APP_EK3.md` §5, §7.

---

## 7.8 `borsai_predict`: modellerin Rust portu

`borsai_predict` crate'i Python'daki `borsai/predict.py`, `predict_hazard.py`, `predict_pb.py`, `predict_market20.py`, `predict_path.py`, `predict_fall.py`, `predict_post_d1.py`, `features.py`, `horizons.py`, `survival.py` ve `tufe.py`'nin okuma/denetim kısmının portudur. **Port edilmeyenler:** model eğitimi (fit), backtest, f6 hesabı (market20), sicil, kayıt yazımı, skorlama. f6 hazır değer olarak gelir.

| Dosya | İçerik |
|---|---|
| `dec.rs` | Python `decimal`'ın kullanılan kısmı: ayrıştırma, bağlamlar, yuvarlama, `str()` |
| `sum.rs` | CPython `sum()` (Neumaier), `min`/`max` |
| `features.rs`, `pb_features.rs` | f1–f4, pb1–pb4 |
| `linear.rs` | V1.5 ailesi, kurallar, PB |
| `market20.rs` | f6'lı V1.5 sarmalayıcısı |
| `hazard.rs` | tavan serisi (v0, PB, `@INF`, KM, v1) |
| `survival.rs` | S, P_L, P_close, sigmoid, koşullu |
| `path.rs` | tavan yolu karışımı ve koşullu güncellemesi |
| `fall.rs` | düşen arz |
| `post_d1.rs` | D1 sonrası güncelleme |
| `tufe.rs` | TÜFE tablosu, ay kuralı, önek pini |
| `horizons.rs` | ufuklar ve fiziksel getiri sınırları |
| `params.rs` | parametre okuma ve denetimi, model türü |
| `output.rs`, `error.rs` | çıktı yapıları, ret/uyarı kodları |

### 7.8.1 Sayı hassasiyeti: Python'u adım adım taklit etmek

Bir tahminin bit bit aynı çıkması için yalnız formül değil, **her ara adımın sayı türü ve yuvarlaması** aynı olmalıdır. Python modelleri üç farklı sayı dünyası kullanır ve Rust her birini ayrı taklit eder.

**(a) Kesin ondalık: `Dec`.** Rust'ın standart kütüphanesinde Decimal yoktur. Port kendi türünü yazar:

```rust
pub struct Dec { pub neg: bool, pub coeff: BigUint, pub exp: i64 }   // (-1)^neg × coeff × 10^exp
```

`BigUint` sınırsız büyüklükte doğal sayıdır (`num-bigint`); böylece `Decimal("1e400")` gibi f64'e sığmayan değerler de kesin tutulur. Şartname başta `num-rational::BigRational` (kesir) önermişti; uygulama bunun yerine bu türü seçti, çünkü Decimal'in üssünü açmadan temsil eder ve `str(Decimal)` metnini birebir üretmeyi kolaylaştırır (README "Bilinen sapmalar").

`dec.rs`'teki işlemler, hangi Python adımını taklit ettikleriyle:

| Rust | Python karşılığı | Nerede kullanılır |
|---|---|---|
| `parse(s)` | `Decimal(str(value).strip())` (CPython 3.12 + libmpdec) | her girdi |
| `mul_round(a, b, 28)` | 28 anlamlı hane, ROUND_HALF_EVEN çarpma | f1 = pay × fiyat |
| `pct(num, den)` | `_pct`: 28 hanede bölme, ×100, 10 ondalığa ROUND_HALF_UP | f2, f4 |
| `add_exact`, `mul_exact` (prec 200) | `_EXACT_CONTEXT`, Inexact tuzağı | PB özdeşlikleri, pb1'in çarpımı |
| `div_exact`, `mul_ctx`, `ctx_round`, `to_integral` (prec 60) | `predict_path._EXACT` (kesin bağlam) | tavan yolunun limit fiyatları |
| `div_round(a, b, 60)` | 60 hane HALF_EVEN bölme | oranlar, f1r, D1 el değiştirme oranı |
| `py_str(x)` | `str(Decimal)` | çıktıdaki metin alanları |
| `to_f64()` | `float(Decimal)` | Decimal → f64 |
| `ratio_to_f64(n, d)` | `int / int` | pb2, pb3, pb4 |
| `ln_to_f64(x)` | `float(Decimal.ln())` (yaklaşık) | pb1, D1 el değiştirme ln'i |

Bazı ayrıntılar neden önemli:

- **Ayrıştırma Python kadar hoşgörülü ve onun kadar katı olmalı.** `Decimal(" +.5e-3 ")` geçerlidir, `"1_000"` geçerlidir (alt çizgiler atılır), `"１２"` (tam genişlikli rakamlar) geçerlidir, `"12,5"` geçersizdir, `"inf"` ve `"nan"` Decimal üretir ama sonlu değildir. Bunun için `dec.rs` CPython 3.12'den üretilmiş iki Unicode tablosu taşır: `str.isspace()`'in doğru olduğu 29 karakter ve ondalık rakam bloklarının 68 başlangıcı. Ayrıca libmpdec'in üs sınırları (`MAX_EMAX`, `MIN_ETINY`) uygulanır. Ret kodu da Python'unkiyle aynı olmalıdır: boş ya da `"DATA_NOT_FOUND"` → `INPUT_MISSING`; `"12,5"`, `"abc"`, `"inf"`, bool, liste → `INPUT_NOT_NUMERIC`.
- **Decimal → f64 kısayolsuz.** `to_f64`, kesin değeri `"<katsayı>e<üs>"` metnine yazar ve Rust'ın `str::parse::<f64>()`'ine verir; bu ayrıştırıcı doğru yuvarlar (en yakın f64, eşitlikte çift). Python'un `float(Decimal)`'ı da doğru yuvarladığı için sonuç bit-eşittir. Şartname "elle hesaplayan kısa yollar yasak" der.
- **`int / int`.** Python'da iki tamsayının bölümü doğru yuvarlanmış f64'tür. `ratio_to_f64`, pay ve payda 2^53'ten küçükse doğrudan IEEE bölmesi yapar (iki sayı f64'e kayıpsız sığar, bölme doğru yuvarlar); değilse BigInt ile 55 bitlik bir bölüm ve "yapışkan bit" (kalanın sıfır olup olmadığı) hesaplayıp HALF_EVEN yuvarlar, alt-normal sayıları da doğru üretir.
- **Çift yuvarlama da taklit edilir.** Tavan yolundaki C/P oranı Python'da önce 60 haneye, sonra f64'e yuvarlanır. Kesin kesirden doğrudan f64'e gitmek "daha doğru" olurdu ama Python'un yaptığı bu değildir. 20 000 rastgele çiftte fark ölçülmemiş olsa da kural Python'unkidir (EK 2 §2.2: "kısa yol parite kanıtı değildir").
- **Kesin bağlamda üs de önemlidir.** Python `Decimal("100") / Decimal("0.10")` için `1.0E+3` yazar, `Decimal("1E+2") / Decimal("0.10")` için `1E+3`. Değer aynı, metin farklı. Limit fiyatları kayıtta metin olarak saklandığı için `div_exact` libmpdec'in üs kuralını uygular: sonuç üssü `exp(a) − exp(b)`'den küçük ya da eşit, katsayıyı tamsayı yapan en büyük üs. Kesin bölme ancak paydanın (ortak bölen atıldıktan sonra) yalnız 2 ve 5 çarpanı varsa mümkündür; değilse `Inexact`, Python'daki etiketsiz istisnanın karşılığı olarak `DOMAIN_ERROR`.
- **`ln`'de bilinçli küçük fark.** Python pb1'i 60 haneli `Decimal.ln()` ile hesaplayıp f64'e çevirir. Rust kesin değeri önce f64'e yuvarlar, sonra `f64::ln` alır. Beklenen fark ≤ 5e-15'tir (ln argümanının bir ulp'si ve matematik kütüphanesi); altın vektörlerde PB satırlarının birkaçı bu yüzden bit-eşit değildir (§7.11). Değer f64'ün normal aralığı dışındaysa ln(m·10^E) = ln(m) + E·ln 10 yedek yolu kullanılır.

**(b) Kayan nokta: f64.** Özellikler f64'e çevrildikten sonraki her şey (z-skoru, doğrusal terim, sigmoid, çarpımlar) f64'tür. Rust'ın `f64::exp` ve `f64::ln`'i aynı makinede Python'un `math.exp`/`math.log`'uyla aynı sistem kütüphanesini (macOS'ta Apple libm) çağırır; şartname bunu "0 beklenir, garanti yok, tolerans içinde" diye yazar.

**(c) Toplama: CPython `sum()`.**

```rust
// crates/borsai_predict/src/sum.rs
pub fn py_sum<I: IntoIterator<Item = f64>>(items: I) -> f64 {
    let mut it = items.into_iter();
    let mut f = match it.next() { None => return 0.0, Some(x) => 0.0 + x };
    let mut c = 0.0f64;                       // kaybolan parçaların toplamı
    for x in it {
        let t = f + x;
        if f.abs() >= x.abs() { c += (f - t) + x; } else { c += (x - t) + f; }
        f = t;
    }
    if c != 0.0 && c.is_finite() { f += c; }
    f
}
```

Doğrusal terim `Σ c·z + b` Python'da `sum(c*z for …) + intercept` biçimindedir: önce Neumaier toplamı, **sonra** sabit eklenir. Rust aynı sırayı izler (`linear_term`). Tavan yolu karışımında ise kümülatif olasılık Python'da düz `+=` döngüsüyle toplanır; Rust orada da düz `+=` kullanır. İki yol farklı yuvarlar; bit eşitliği ancak aynı yolla gelir. `py_max(a, b)` ve `py_min(a, b)` da Python'un NaN davranışını korur: `max(a, b)`, `b > a` değilse `a`'yı döner.

**(d) Fiziksel getiri sınırları.** Günlük fiyat limiti ±%10 olduğu için h günde getiri [0.9^h − 1, 1.1^h − 1] aralığındadır. Python bu sınırları Decimal'le kesin hesaplayıp bir kez f64'e çevirir; Rust aynı kesin değerlerin metnini ayrıştırır: D1 [−0.1, 0.1], D3 [−0.271, 0.331], D5 [−0.40951, 0.61051], D10 [−0.6513215599, 1.5937424601] (tavan yolunda m = 1..10'un tamamı).

**(e) JSON yazımı: `json_out.rs`.** Uygulamanın repoya yazdığı belgeler (girdi belgesi, kaynak MANIFEST'i, olay dosyası) Python'un `pretty_json_bytes`'ıyla **bayt-eşit** olmalıdır: sıralı anahtarlar, 2 boşluk girinti, sonda LF, `ensure_ascii=False`, sayılar Python `repr(float)` biçiminde (`1e-05`, `1e+16`, `0.1`). serde_json'un güzel yazıcısı bu kurala uymadığı için yazıcı elle yazılmıştır; sonlu olmayan sayı yazmayı reddeder.

Kaynak dosyalar: `app/src-tauri/crates/borsai_predict/src/dec.rs`, `sum.rs`, `horizons.rs`, `app/src-tauri/src/json_out.rs`, `app/parity/README.md` (sayısal kararlar tablosu), `docs/app/SPEC_APP.md` §1.3, `SPEC_APP_EK2.md` §2.2.

### 7.8.2 Model türleri ve dağıtım

Bir parametre dosyasının hangi koda gideceği `params::model_kind`'da, Python `freeze.model_kind` ile aynı kuralla belirlenir:

| `algorithm` | Ek koşul | Tür | Rust fonksiyonu | Modeller |
|---|---|---|---|---|
| `discrete_time_hazard_logit_l2` | — | `hazard` | `hazard::predict_hazard` | `ceiling_hazard_v0`, `@INF`, `pb_ceiling_v0`, `@INF`, `ceiling_hazard_v1_*` (4) |
| `discrete_time_hazard_offset_logit_l2` | — | `post_d1` | `post_d1::run_post_d1` (ayrı giriş) | `post_d1_hazard_v0` |
| `l2_logit_v1_6_grid` | — | `fall` | `fall::predict_fall` | `fall_d10_v0_*` (4) |
| `CEILING_PATH_MIXTURE_EQ_V0` | — | `ceiling_path` | `path::predict_path` | `ceiling_path_v0`, `@INF`, `pb_ceiling_path_v0` |
| `KM_EXPANDING`, `KM_LAST10` | — | `km` | `hazard::predict_hazard` | `base_km_expanding`, `base_km_last10` |
| `V1_5_RIDGE_LOGIT` | özelliklerde `f6` | `market20` | `market20::predict_market20` | `v1_5_market20_v0` |
| `V1_5_RIDGE_LOGIT` | özellik `pb…` | `pb` | `linear::predict_pb` | `pb_v0` |
| `V1_5_RIDGE_LOGIT` | — | `linear` | `linear::predict_core` | `v1_5_h99`, `v1_6_h99` |
| başka her şey | — | `rule` | `linear::predict_core` | `base_*` sabit kurallar (6) |

`run_model` her modelin sonucunu `{kind, status, refusal, output}` olarak paketler: tahmin verdiyse `PREDICTED`, model kendi kuralıyla reddettiyse `REFUSED` (çıktı yine döner, ret alanıyla), parametre hatası ya da Python'un etiketsiz istisnasına karşılık gelen durumda `ERROR` (çıktı yok). `predict_all` 27 modeli INDEX sırasıyla aynı girdiyle koşar; her satıra `model_id` ve `params_sha256` eklenir. D1 sonrası model bu döngüde **çalışmaz** (Python'da da `run_model` ERROR verir); onun girişi ayrıdır.

Kaynak dosyalar: `crates/borsai_predict/src/params.rs` (`model_kind`, `check_params`), `lib.rs` (`predict`, `run_model`, `predict_all`), `docs/app/SPEC_APP.md` §1.2.

### 7.8.3 Özellikler

**V1.5 özellikleri (`features::compute_features`)**, kesin ondalıkla:

```
f1 = ipo_size_tl                         (verilmişse, > 0)
   = shares_offered × ipo_price_tl       (verilmemişse; 28 hane HALF_EVEN)
f2 = _pct(shares_offered, post_ipo_share_capital)   satılan payın arz sonrası sermayeye oranı (%)
f3 = total_demand_multiple               toplam talep katı (isteğe bağlı, > 0)
f4 = _pct(capital_increase_shares, shares_offered)  satılan payın ne kadarı sermaye artırımı (%)
f5 = 1[f3 yok]                           (yalnız z-vektöründe; "f3 eksik" göstergesi)
_pct(a, b) = HALF_UP_10( HALF_EVEN_28(a / b) × 100 )
```

Ret sırası Python'daki gibidir: fiyat (eksik / sayı değil / ≤ 0), satılan pay (0 ise `DIVISION_BY_ZERO`), arz sonrası sermaye, sermaye artırımı payı (negatifse `INPUT_NEGATIVE`, satılandan büyükse `INPUT_INCONSISTENT`), satılan > sermaye (`INPUT_INCONSISTENT`), f3 ≤ 0, büyüklük. f1'in 28 hanelik çarpımı taşarsa (Python `decimal.Overflow`) sonuç `DOMAIN_ERROR`'dur: Python o girdide kayıt üretmez, Rust da tahmin üretmez.

**f1r (gerçek büyüklük, `hazard::real_size`)**: f1'in 2025 fiyatlarıyla ifadesi.

```
q   = TÜFE / 100                 (kesin; yalnız üs kayar)
f1r = HALF_EVEN_60( f1 / q )     → bir kez f64
```

TÜFE değeri ilk işlem gününün ayından iki ay önceki aydır (§7.8.9).

**PB özellikleri (`pb_features::compute_pb_features`)**, talep toplama öncesi (planlanan yapı) için:

```
değer = ipo_price_try × planned_base_offer_shares      (200 hane, kesin olmak zorunda)
pb1 = ln(değer)
pb2 = taban / arz_sonrası_sermaye × 100
pb3 = sermaye_artırımı / taban × 100
pb4 = ek_satış_tavanı / taban × 100       (modelde değil; > 0 ise uyarı)
Özdeşlikler: ID-A  arz_sonrası = arz_öncesi + sermaye_artırımı
             ID-B  taban = sermaye_artırımı + mevcut_pay_satışı
             ID-C  azami = taban + ek_satış_tavanı
```

Fiyat "10-12", "10–12" ya da "10—12" gibi bir aralıksa `PB_PRICE_RANGE` ile ret (PB modeli aralıkla tahmin vermez). Sekiz alandan biri eksik ya da 200 hanede kesin değilse `PB_FIELD_MISSING`; özdeşlik ya da aralık tutmazsa `PB_IDENTITY` (alanı ihlalin adıdır: `ID-A`, `PB2_RANGE` …). Oranlar kesin kesirden `ratio_to_f64` ile tek yuvarlamayla f64'e iner.

Kaynak dosyalar: `crates/borsai_predict/src/features.rs`, `pb_features.rs`, `hazard.rs` (`real_size`, `div_ctx`).

### 7.8.4 Doğrusal aile: V1.5, V1.6, kurallar, PB, market20

```
x_c  = özellik değeri (yoksa eğitim medyanı; f5 = 1[f3 yok])
x_c  = min(max(x_c, p05_c), p95_c)        (yalnız kırpma tanımlı kolonlarda; "winsor")
x_c  = ln(x_c)                             (yalnız log kolonlarında; x ≤ 0 → DOMAIN_ERROR)
z_c  = (x_c − μ_c) / σ_c                   (σ = 0 → DOMAIN_ERROR)

ret_h  = Neumaier(Σ coef_{h,c}·z_c) + b_h          ("ridge" başlığı; ya da sabit)
p_up_h = sigmoid(Neumaier(Σ coef'·z) + b')          ("logit" başlığı; ya da sabit)
ret_h  ← [0.9^h − 1, 1.1^h − 1] aralığına kırpılır   (kırpıldıysa RETURN_CLIPPED uyarısı)
fiyat_h = P × (1 + ret_h)
yön_h   = "UP" ancak p_up_h > 0.5
sigmoid(x) = 1/(1+e^(−x))  (x ≥ 0) ;  e^x/(1+e^x)  (x < 0)   — taşmasız biçim
```

Uyarılar hücreyi gizlemez, yanına eklenir: `OUT_OF_TRAINING_RANGE` (ham değer eğitim aralığı dışında; tahmin dışdeğerlemedir), `F4_ZERO_NO_TRAINING_EXAMPLE`, `F3_WINSORIZED`, `RETURN_CLIPPED_TO_PHYSICAL_BOUND`. f3 yoksa ve modelin politikası `REFUSE` ise `F3_MISSING`; f3'ün filtre durumu eğitimdeki modla çelişiyorsa ve politika `REFUSE` ise `F3_FILTER_STATUS_CONFLICT` (bugün hiçbir kayıtlı modelde filtre modu açık değildir; bu yol yalnız yamalı parametrelerle sınanır). Bir kolonun değeri yoksa ve medyanı da yoksa `FEATURE_NOT_PROVIDED`: imputasyon yapılmaz.

**Kurallar** (`base_*`) özelliksizdir: yalnız fiyatı okur, başlıkları sabittir. **PB modeli** z'yi pb1–pb3'ten kurar ve fiyatı `ipo_price_try`'dan alır. **market20** önce f6'ya bakar (Python'daki sırayla, parametre denetiminden de önce): f6 sayı değilse `MARKET20_NOT_NUMERIC`; yoksa gelen neden kodu (`STALE_S0`, `CALENDAR_NOT_COVERING`, `INSUFFICIENT_HISTORY`, `XU100_CLOSE_MISSING`, `PREDICTION_TOO_EARLY`, `XU100_INTEGRITY`, bilinmiyorsa `NOT_PROVIDED`) `MARKET20_` önekiyle ret; varsa V1.5 çekirdeği f6'yı ek özellik olarak alır.

Kaynak dosyalar: `crates/borsai_predict/src/linear.rs`, `market20.rs`, `survival.rs` (`sigmoid`), `horizons.rs`.

### 7.8.5 Tavan serisi: hazard, KM ve v1 ailesi

Soru: arz ilk günden itibaren kaç gün üst üste tavan kapatacak? L ∈ {0, 1, …, 10} seri uzunluğudur. Model günlük "bozulma tehlikesi" (hazard) h_d'yi verir: d. güne kadar tavan sürdüyse d. gün tavanın bozulma olasılığı.

```
g(d)  = 0 (d = 1), 1 (d = 2, 3), 2 (d = 4..10)            gün grupları (dosyadaki day_groups)
η_d   = γ_{g(d)} + Σ_c β_c·z_c                             v0 / PB
η_d   = (γ_{g(d)} + δ·r) + Σ_c β_c·z_c                     v1 pooled (rejim terimiyle)
h_d   = sigmoid(η_d)
S_k   = Π_{d ≤ k} (1 − h_d)                                P(L ≥ k), soldan sağa çarpım
P_L[0] = 1 − S_1 ;  P_L[l] = S_l − S_{l+1} (1 ≤ l ≤ 9) ;  P_L[10] = S_10
P_close[1] = S_1 ;  P_close[k] = S_k + (1 − S_k)·r_k,  r_k = r_a (k ≤ 4), r_b (k ≥ 5)
```

P_close, "k. gün tavan kapanışı" olasılığıdır: seri sürüyorsa tavan, bozulduysa bile yeniden tavana dönme olasılığı (`reclose_rates`) eklenir.

- **v0** (`ceiling_hazard_v0`): özellikler f1, f2, f3; f3 zorunlu (yoksa `F3_MISSING`, "f3'süz tavan tahmini PB modelinden gelir"). f3 eğitim p05/p95 dışındaysa kırpılır ve `F3_CLIPPED_TO_TRAINING_P05_P95` uyarısı, `clipped: true`.
- **PB** (`pb_ceiling_v0`): pb1, pb2.
- **`@INF`**: özelliksiz; η_d = γ_{g(d)}. Girdi okumaz, her arza aynı eğriyi verir (basit karşılaştırma kuralı).
- **KM** (`base_km_*`): Kaplan–Meier tablosu; tehlikeler dosyadaki `survival.hazard`'dan, girdi okunmaz.
- **v1 ailesi** (`ceiling_hazard_v1_clip`, `_real`, `_pooled`, `_pooled@INF`): türü yine `hazard`'dır (kayıt okuyucuları kırılmasın diye); farkı JSON'daki `family` alanından anlaşılır. v0'dan farklı olarak ailenin bütün özellikli modelleri yalnız f3'ü değil **her** özelliği eğitim p05/p95'ine kırpar (`FEATURE_CLIPPED_TO_TRAINING_P05_P95`). `clip` f1, f2, f3 kullanır; `real` ve `pooled` f1 yerine f1r kullanır; TÜFE girdisi gerekir (`tufe_input`: `tufe_refusal` doluysa o kodla, `tufe_index` eksik/sayı değil/≤ 0 ise `TUFE_MISSING` ile ret; `INPUT_NOT_NUMERIC` değil). `pooled` ve `pooled@INF` tahsis rejimi terimi taşır: girdide `alloc_regime` anahtarı **varsa** etiket r'ye çevrilir (`PRE_20211111` ve `THRESH100_20211111` → 1, `EQUAL_DIST_20230330` → 0, başka her şey `REGIME_UNKNOWN`); anahtar yoksa canlı değer (`live_value`) kullanılır. Uygulama bu anahtarı hiçbir zaman kendisi üretmez; yalnız eski kohort kayıtlarının girdisinde gelir. Ek çıktı alanları: `clipped_features`, `f1r_raw`, `tufe_index_used`, `regime_value_used`, `regime_source`.

**Koşullu güncelleme (`survival::conditional`).** "Seri j gün sürdü" bilgisiyle, modeli yeniden çalıştırmadan:

```
P(L ≥ k | L ≥ j) = S_k / S_j          (k > j; S_0 = 1)
P(L = l | L ≥ j) = P_L[l] / S_j       (l ≥ j)
"yarın bozulur"  = 1 − S_{j+1} / S_j
j ≥ 10 ya da S_j = 0 → tanımsız ("—")
```

Her hücre tek bir bölmedir; j = 0 koşulsuz eğrinin kendisidir (testte bit-eşitliği sınanır).

Kaynak dosyalar: `crates/borsai_predict/src/hazard.rs`, `survival.rs`, `params.rs` (`parse_hazard`, `parse_v1`), `docs/app/SPEC_APP_EK3.md` §2.

### 7.8.6 Tavan yolu (`path.rs`)

Soru: ilk 10 günün her birinde getiri dağılımı ne? Model iki parçalıdır: seri sürdükçe fiyat **limit yolunu** izler; seri bozulduktan sonraki getiriler ise geçmiş arzlardan toplanmış **hücrelerden** gelir.

**Limit yolu**, kesin ondalıkla (60 hane, Inexact tuzaklı):

```
adım(x)  : fiyat adımı tablosu  x < 20 → 0.01 ; < 50 → 0.02 ; < 100 → 0.05 ; < 250 → 0.10 ;
           < 500 → 0.25 ; < 1000 → 0.50 ; < 2500 → 1.00 ; aksi → 2.50
snap(P)  = HALF_UP( P / adım(P) ) × adım(P)            D1 baz fiyatı
U(b)     = FLOOR( y / adım(y) ) × adım(y),  y = b × 1.10   üst limit (adım y'nin kendi seviyesinden)
C_0 = snap(P) ;  C_k = U(C_{k−1}) ;  ρ_k = C_k / P − 1 ;  ölçek_k = C_k / P
```

Arz fiyatı adım ızgarasında değilse `IPO_PRICE_NOT_ON_TICK_GRID` uyarısı (metin alanlarıyla: alan, değer, oturtulan fiyat, adım). Örnek ölçümler `path.rs` testlerinde: 25.52 TL → C_1 = 28.06, C_10 = 66.05; 18.19 → C_1 = 20.00 (18.19 × 1.1 = 20.009, adım 20'nin üstünde 0.02 olduğu için 20.00'ye iner).

**Hücreler ve havuzlama.** Seri uzunluğu L = t ise (t = 0: seri hiç başlamadı, grup Z; 1 ≤ t ≤ 9: seri t gün sürüp bozuldu, grup B), h. günün getirisi t. günün kapanışına (t = 0'da arz fiyatına, t ≥ 1'de limit fiyatı C_t'ye) göre m = h − t gün sonraki getiriyi tutan hücre (g, m)'den gelir. Hücreler geçmiş arzların gözlemleridir ve model dosyasında (`post_break.cells`) dondurulmuştur. Bir hücrede 10'dan az gözlem varsa "merdiven" kuralıyla komşu hücreler eklenir: önce kendi hücresi, sonra öbür grubun aynı m'si, sonra d = 1..9 için m − d ve m + d (her adımda Z sonra B); adım sonunda n ≥ 10 olunca durulur. Toplanan değerler hedef m'nin fiziksel sınırına kırpılır. (Dondurulmuş hücrelerin hepsinde ≥ 11 gözlem olduğundan bugün havuzlama hiç tetiklenmez; bu yollar yalnız yamalı parametrelerle sınanır.)

**Karışım ve özet.** h. gün için atomlar (değer, ağırlık):

```
limit atomu:     (ρ_h, S_h)                              seri h gün sürdü
her t = 0..h−1:  hücre(g(t), h − t)'nin n değerinden her v için
                 değer = v (t = 0)  ya da  ölçek_t·(1 + v) − 1 (t ≥ 1),  ağırlık = P_L[t] / n
sıralama: değere göre artan, KARARLI (eşitlikte ekleme sırası)
Q(q)  = kümülatif ağırlık ≥ q − 1e-12 olan ilk atomun değeri   (düz += ile)
return = Q(0.5) ;  q10, q50, q90 ;  p_up = Neumaier(Σ w, r > 0) ;  mean = Neumaier(Σ r·w)
```

Bir hücre yetersiz kalırsa o ufuk `POST_BREAK_INSUFFICIENT` olur ve özet alanları boştur. Tavan yolu modelinin S'i, gömülü seri modelinin (örneğin `ceiling_hazard_v0`) aynı girdiyle ürettiği S'in bit-eşit kopyasıdır (U45 testi).

**Koşullu tavan yolu** (`path::conditional`, `conditional_after_break`): "seri j gün sürüyor" durumunda ağırlıklar koşullu P_L'den, ölçekler gözlenen kapanışlardan (j'ye kadar) ve limit yolundan gelir; "seri t. günde kırıldı" durumunda yalnız gözlenen kırılma günü kapanışının ölçeğiyle hücre karışımı. Girdi, dondurulmuş kayıttaki çıktıdır; limit yolu **yeniden hesaplanmaz**. Gözlenen kapanış limit yolundan farklıysa `limit_path_mismatch = 1`.

Kaynak dosyalar: `crates/borsai_predict/src/path.rs`, `params.rs` (`parse_path`), `docs/app/SPEC_APP_EK2.md` §2.3–§2.8.

### 7.8.7 Düşen arz (`fall.rs`)

Soru: D5 ve D10'da kapanış arz fiyatının altında mı? Model p_up = P(kapanış > arz fiyatı) verir; ekran "düşme olasılığı"nı 1 − p_up olarak gösterir.

```
özellikler: f1r, f3, add_sale = 1[ek satış payı > 0]     (h99, pooled)
            add_sale                                       (addsale)
            yok                                            (pooled@ZERO: sabit oran)
f1r ve f3: kırp (p05/p95) → ln → z ;  add_sale: z
p_up_h = sigmoid(Σ coef·z + b),  h ∈ {D5, D10} (çıktı bu sırayla)
```

Ret sırası Python'unkidir (EK 3 §8'in önerisinden farklı; çelişkide Python kazanır, `app/parity/README.md`'deki 11 maddelik "referans kilidi" tablosu): özellik retleri → `F3_MISSING` → filtre çelişkisi → TÜFE → ek satış (`ADDITIONAL_SALE_MISSING`: boş alan 0 sayılmaz; negatif `INPUT_NEGATIVE`; sayı değil `INPUT_NOT_NUMERIC`). `@ZERO` hiçbir girdi okumaz ve hiçbir koşulda reddetmez; `addsale` yalnız ek satış alanını okur.

Kaynak dosyalar: `crates/borsai_predict/src/fall.rs`, `params.rs` (`parse_fall`), `app/parity/README.md` (referans kilidi), `docs/app/SPEC_APP_EK3.md` §8.

### 7.8.8 D1 sonrası (`post_d1.rs`)

Soru: ilk gün tavanda kapandı; seri yarın bozulur mu? `post_d1_hazard_v0` ana modelin (`ceiling_hazard_v0`) doğrusal öngörücüsünü **ofset** olarak kullanır, yeniden eğitmez:

```
η_d (taban)  = ceiling_hazard_v0'ın η_d'si (hazard::linear; aynı kod)
d1_lock      = 1[D1 en düşük = üst limit]                 (gün boyu kilitli mi)
d1_turnover  = ln(hacim / arz edilen pay)                  (60 hane oran → f64 ln), p05/p95'e kırpılır
u_c          = (x_c − μ_c) / σ_c
h_1          = sigmoid(η_1)                                (ana modelden aynen)
h_d          = sigmoid(η_d + Σ_c δ_c·u_c),  d = 2..10
```

D1 bülten satırı (`fields_raw`) `evaluate_d1`'de Python sırasıyla denetlenir: kapanış ya da sözleşme sayısı yok/≤ 0 → `D1_NOT_TRADED` (hata; kayıt yazılmaz); üst limit yok → `D1_LIMIT_NA`; kapanış ≠ üst limit → **kapsam dışı** `D1_NOT_CEILING` (ret değil, durum `NOT_APPLICABLE`); hacim yok → `D1_VOLUME_INVALID`; en düşük/açılış/en yüksek yok → `D1_FIELD_INVALID`. Uyarılar: kilit tutarsız (en düşük = limit ama açılış/en yüksek/kapanış değil), yarım gün, gün içi durdurma, özel işlem hacmi > 0, el değiştirme kırpıldı. Çıktıda ayrıca j = 1 koşullu görünümü (`conditional_j1`) ve tavan yolunun bu modelin S'iyle koşullu hâli (`path_conditional`) bulunur. Ret kodları önek taşımaz (errata H23).

Kaynak dosyalar: `crates/borsai_predict/src/post_d1.rs`, `params.rs` (`parse_post_d1`), `docs/app/SPEC_APP_EK3.md` §6.2–§6.3.

### 7.8.9 TÜFE tablosu (`tufe.rs`)

`data/raw/tuik/tufe_genel_2025_100.csv`: TÜİK genel TÜFE (2025 = 100), sütunlar `month, index, release_date, bulletin_id, source_url, source_sha256`. Repo anlık kopyasında ilk ay 2019-11, son ay 2026-08 (134.75, yayım 2026-09-03).

- **Ay kuralı:** `month_for(T)` = T'nin ayı − 2 (`"2026-09-25"` → `"2026-07"`, `"2020-01-06"` → `"2019-11"`). İki ay geri gidilir, çünkü bir ayın TÜFE'si izleyen ayın başında yayımlanır; ilk işlem gününde elde olan en yeni veri budur.
- **`parse`:** dosya UTF-8, satır sonu LF, sütunlar birebir, aylar 2019-11'den boşluksuz artar, endeks pozitif ve kırpılmamış Decimal metni, yayım günü izleyen ayın ≥ 3. günü, bülten kimliği rakam, sha 64 hex, adres `https://`. İhlal → tablo geçersiz (değer düzeltilmez).
- **`index_for(T)`:** ay yoksa `TUFE_MISSING`; yayım günü T'den önce değilse `TUFE_NOT_PIT` (point-in-time bekçisi: tahmin anında bilinmeyen veri kullanılmasın).
- **Önek pini:** deflatörlü her model, eğitildiği andaki dosyanın `through_month` satırına kadarki baytlarının sha256'sını taşır. `verify_pin`, bugünkü dosyanın aynı önekinin sha'sını hesaplar. Yeni ay **eklemek** pini bozmaz; eski bir satırı, temel yılı ya da zincirlemeyi değiştirmek bozar → `TUFE_FILE_MISMATCH`. Repo anlık kopyasında pin ayı 2026-08'dir.
- **Ekleme komutu:** ay eksikse ekranda Python'un `tufe.APPEND_COMMAND` metni birebir gösterilir (yorumlayıcı repo modunda ayardaki Python'la değiştirilir); uygulama bu komutu çalıştırmaz.

TÜFE girdisinin tahmine nasıl girdiği §7.9.2'dedir.

Kaynak dosyalar: `crates/borsai_predict/src/tufe.rs`, `data/raw/tuik/tufe_genel_2025_100.csv`, `docs/app/SPEC_APP_EK3.md` §3.

### 7.8.10 Çıktı ve hata yapısı

- `Refusal { code, field, reason }`: etiketli ret. `code` ve `field` Python sabitleriyle birebirdir; `reason` Rust'ın kendi Türkçe metnidir ve parite karşılaştırmasına girmez.
- `PredictError { code, message }`: `PARAMS_INVALID`, `SCHEMA_UNSUPPORTED`, `DOMAIN_ERROR` (Python'un etiketsiz istisnasının karşılığı: `math.log(0.0)`, `decimal.Overflow`, `Inexact`), `D1_NOT_TRADED`.
- `Warning`: kod, mesaj ve Python `_warn(**extra)` sırasıyla ek alanlar (metin alanları, mantıksal alanlar, `feature`, `horizon`, `value`, `used`, `train_min`, `train_max`).
- `Output` dört biçimdedir (`Linear`, `Hazard`, `Path`, `PostD1`); `to_json` anahtar sırası Python sözlüğüyle aynıdır. JSON'da sonlu olmayan f64 metin olarak yazılır: `"NaN"`, `"Infinity"`, `"-Infinity"` (altın vektörler de böyle yazar).

Kaynak dosyalar: `crates/borsai_predict/src/output.rs`, `error.rs`, `lib.rs` (`RunResult`, `ModelRun`).

---

## 7.9 Uçtan uca: formdan ekrana, ekrandan sicile

Bu alt bölüm parçaları birleştirir: kullanıcı formu doldurduğu andan, tahminin ekranda görünmesine ve resmî kaydın yazılmasına kadar hangi komutun ne yaptığını sırasıyla izler.

### 7.9.1 Form ve anında denetim: `check_form`

Ön uç her alan değişiminde `check_form(stage, fields)` çağırır. `stage` iki değerden biridir: `PRE_BOOKBUILD` (talep toplama öncesi; yalnız planlanan yapı ve fiyat aralığı bilinir) ya da `POST_BOOKBUILD_PRE_LISTING` (talep toplandı, işlem başlamadı). `fields` formun 20 alanı ve f6 alanıdır. Komut model çalıştırmaz; yalnız girdiyi denetler. Bütün aritmetik kesin ondalıkla (`Dec`) yapılır.

1. **Biçim.** Sayı alanlarında baştaki ve sondaki boşluk kırpılır; metinde **tek virgül var ve nokta yoksa** virgül noktaya çevrilir (`"25,52"` → `"25.52"`, gri `COMMA_CONVERTED` notu). Binlik ayırıcı kabul edilmez. Tarihler katı ISO olmalı (`YYYY-MM-DD`, artık yıl dahil geçerli takvim günü; değilse `DATE_NOT_ISO`). Filtre durumu `NOT_SPECIFIED`, `UNFILTERED`, `FILTERED`'dan biri olmalı. Sayı, Python `Decimal` kurallarıyla ayrıştırılamıyorsa `INPUT_NOT_NUMERIC`; PB fiyatı aralıksa `PB_PRICE_RANGE`.
2. **Tutarlılık (kırmızı).** Fiyat, satılan pay, arz sonrası sermaye, talep katı ve büyüklük > 0; sermaye artırımı payı ≥ 0 ve ≤ satılan pay; satılan pay ≤ arz sonrası sermaye. PB özdeşlikleri ID-A, ID-B, ID-C tutmazsa `PB_IDENTITY` ve beklenen değer.
3. **Uyarı (sarı).** Satılan pay = sermaye artırımı + mevcut pay satışı + ek satış (kesin toplam) tutmazsa `SHARES_SUM_MISMATCH` ve toplam; talep katı var ama filtre durumu boşsa `FILTER_STATUS_REQUIRED`.
4. **Öneri.** ID-B ve ID-C toplamları (planlanan taban pay ve azami pay) formda önerilir; kullanıcı onaylarsa uygulanır. ID-A yalnız denetlenir.
5. **Aşamaya göre zorunluluk.** Her alan için `REQUIRED`, `OPTIONAL`, `EMPTY` (o aşamada bilinmez, boş kalmalı) ya da `REQUIRED_IF_F3`; zorunlu ama boş alana gri `REQUIRED_EMPTY` notu.

Dönen `FormCheck` normalize edilmiş metinleri, notları (error / warn / info), önerileri, zorunluluk tablosunu ve `predict_all`'a gidecek **17 model girdisini** (9 V1.5 alanı + 8 PB alanı, boşlar `null`) içerir. Önemli ilke: formdaki kırmızı not bir RET değildir; RET'i yalnız model verir. Form aynı kuralları erken gösterir ki kullanıcı neden sütunların boş kaldığını tahminden önce görsün.

Kaynak dosyalar: `app/src-tauri/src/commands/form.rs`, `src/clock.rs` (`is_iso_date`), `crates/borsai_predict/src/features.rs`, `pb_features.rs`, `docs/app/SPEC_APP.md` §3a.

### 7.9.2 Tahmin: `predict_all`

Ön uç "Tahmin et" dediğinde `predict_all(inputs, f6, t)` çağrılır. `t`, formdaki ilk işlem günüdür (T).

**f6'nın kaynağı.** V1.5 market20 modeli f6'yı (XU100'ün 20 seanslık getirisi) ister ama uygulama f6'yı hesaplamaz:

- Repo modunda ön uç önce `market20_via_python(ref_date, t)` çağırır. Rust, şartnamedeki Python tek satırlığını birebir koşar: `borsai.market20.load_live_sources()` ile pinli XU100 dosyasını ve takvimi okur, `market20(...)` ile f6'yı ya da neden kodunu hesaplar ve JSON basar. `ref_date` verilmezse bugünün İstanbul tarihi kullanılır; saat dilimi sabit UTC+3'tür (Türkiye 2016'dan beri yaz saati uygulamıyor; `clock.rs` takvim hesabını standart kütüphaneyle, Howard Hinnant'ın `civil_from_days` algoritmasıyla yapar). T boşsa `t_unknown = true` ve Python canlı kural denetimini yapmaz. Çıktının `f6` ve `refusal` alanları metin ya da null olmalı; değilse `MARKET20_OUTPUT_INVALID`.
- Bağımsız modda kullanıcı f6'yı elle girer (etiketli) ya da boş bırakır; boşsa model `MARKET20_NOT_PROVIDED` ile reddeder.

**TÜFE'nin hazırlanması.** Python'da `predict_hazard` saftır; TÜFE girdisini kayıt yazıcısı (`freeze.tufe_for_record`) hazırlar. Uygulama aynı ayrımı korur: `predict_all` modelleri çağırmadan önce `tufe_for_inputs` girdi sözlüğüne iki anahtar ekler, `tufe_index` ve `tufe_refusal`. Bu ekleme yalnız gömülü kümede deflatörlü model varsa yapılır (bugün dört tane var). Kurallar `freeze.tufe_for_record` sırasıyladır:

1. T boş → `tufe_refusal = TUFE_MISSING` (neden `T_UNKNOWN`).
2. Tablo geçersiz (ayrıştırılamadı) → `TUFE_FILE_MISMATCH`.
3. `index_for(T)`: ay yoksa `TUFE_MISSING` (ekranda ay adı ve ekleme komutu); yayım T'den önce değilse `TUFE_NOT_PIT`.
4. Deflatörlü modellerden birinin önek pini tutmuyorsa `TUFE_FILE_MISMATCH`.
5. Aksi hâlde `tufe_index` = tablodaki endeks metni.

Tablo repo modunda **her tahminde** repodaki dosyadan yeniden okunur (yeni ay eklenince uygulamayı yeniden derlemek gerekmez); bağımsız modda gömülü kopya kullanılır. Kullanıcı TÜFE değerini elle giremez: imputasyon yoktur, ay yalnız T'den türetilir. Örnek (birim testinden): T = 2026-09-17 → ay 2026-07 → endeks 132.31, pin tutuyor.

**Koşu.** `with_f6` girdiye `f6_market20` ve `f6_market20_refusal` anahtarlarını ekler; `borsai_predict::predict_all` 27 modeli INDEX sırasıyla koşar. Her satır `{model_id, params_sha256, kind, status, refusal, output}`'tur. Aynı girdi sözlüğü 27 modele gider; her model yalnız kendi alanlarını okur.

Kaynak dosyalar: `app/src-tauri/src/commands/predict.rs`, `market20.rs`, `src/clock.rs`, `crates/borsai_predict/src/lib.rs`, `tufe.rs`, `docs/app/SPEC_APP.md` §3a.2, `SPEC_APP_EK3.md` §3.3.

### 7.9.3 Ekrana giden türevler

Tahmin satırları ön uca döndükten sonra ekran birkaç komutla daha beslenir; hiçbiri modeli yeniden çalıştırmaz:

- `ceiling_summary(runs, j, j_observed, t)`: "Tavan serisi — kaç gün tavan?" kartı. Her satırın değerleri `ceiling_display`'in aynı satır hesabından gelir (P(L ≥ 3) = S_3, P(L ≥ 5) = S_5, P(L = 10) = S_10, beklenen/medyan/en olası L, j > 0 ise koşullu sütunlar). Terazi sütunları (yakın dönem, kasa, canlı) skor dosyalarından okunur. Aynı yanıtın `fall` alanı "Düşüş (D10)" kartıdır. `t` yalnız kartın TÜFE satırı içindir.
- `ceiling_display(models, j, ipo_price_tl)`: Grup B (tavan serisi) eğrileri ve tablosu; ek olarak "seri k gün sürerse kapanış ≈ arz fiyatı × 1.1^k" fiyat ipucu (k = 1, 3, 5, 10) ve hesaplayıcı eki.
- `path_display(models)`: Grup C (tavan yolu) fiyat satırı. Medyan getiri limit atomuna eşitse (bit-eşit) kayıttaki `C_h` metni aynen gösterilir; değilse P × (1 + medyan) burada hesaplanır.
- `streak_view(ticker)`: repo modunda arzın gözlenen serisi ve resmî j.
- `score_hints()`: model kartı alanları ve "backtest tipik hata" satırı, skor dosyasından aynen.

**Senaryo olarak saklama.** `save_scenario` ön uçtan **sayı almaz**: girdileri ve f6'yı alır, `predict_all`'ı Rust'ta yeniden koşar ve çıktıları dosyaya yazar. Böylece kişisel kayıttaki sayı, ekranda görülenle aynı kaynaktan gelir ve ön uçtaki bir hata kayda sızmaz. Yüklenen senaryo yeniden hesaplanmaz; gömülü INDEX sha'sı farklıysa yalnız bayrak gösterilir (U36).

Kaynak dosyalar: `app/src-tauri/src/commands/ceiling.rs`, `fall.rs`, `path.rs`, `scores.rs`, `scenario.rs`.

### 7.9.4 Resmî kayıt: "dondur" sihirbazı

Resmî kayıt, ilk işlem gününden önce yazılan ve sonra skorlanan tahmindir. Kayıt yazıcısı Python `borsai.freeze`'dir; uygulamanın işi doğru girdi belgesini üretmek, süreci tek ekranda toplamak, çıkan kaydı kendi tahminiyle karşılaştırmak ve sonraki git adımlarını göstermektir. Altı adım:

1. **Ön koşullar (`freeze_preflight`).** `git rev-parse HEAD` başarılı (`GIT_HEAD`); repodaki `models/INDEX.json` sha'sı gömülüyle aynı (`INDEX_SHA`); `borsai.__file__` repo altında (`BORSAI_IMPORT`); deflatörlü model varsa repodaki TÜFE tablosunda T'nin ayı var (`TUFE_MONTH`; Python bu durumda kayıt yazmaz). Bilgi satırları: `git status --porcelain -- registry` (kirli olabilir), T düzeyi (`RED`: bugün ≥ T, kayıt en iyi hâlde geç kayıt olur; `YELLOW`: T bilinmiyor), TÜFE'nin `NOT_PIT`/`FILE_MISMATCH` durumları (engel değil; Python kaydı yazar, ilgili hücreler RET olur).
2. **Kaynak belgeler (`copy_source_docs`).** Seçilen PDF'ler `registry/source_docs/<T>/` altına kopyalanır, sha256'ları ölçülür, `MANIFEST.json` güncellenir. Önce bütün dosyalar okunup çakışma aranır: aynı adlı dosya farklı sha'daysa (`SOURCE_DOC_CONFLICT`) **hiçbir şey yazılmaz**. Var olan MANIFEST girişi değiştirilmez.
3. **Girdi belgesi (`preview_inputs_doc` → `write_inputs_doc`).** `borsai.inputs/1` belgesi kurulur: alan değerleri sonuç ekranındaki (tahmin edilen) değerlerdir ve düzenlenemez; kullanıcı yalnız kaynak, alıntı ve boş alan gerekçesi girer. Dosya adı aşamaya göre `registry/inputs/<T>.PB.json` ya da `<T>.json`. Rust `validate_inputs` (Python `registry.py`'nin yapısal denetiminin portu; sorun metinleri birebir) koşar; sorun varsa yazılmaz. Dosya varsa satır farkı gösterilir ve onay istenir. Baytlar Python'un `pretty_json_bytes`'ıyla aynıdır (`json_out.rs`).
4. **Yetkili denetim (`inputs_pit_check`).** Python `registry.inputs_pit_problems` çağrılır; liste boş değilse durulur. Rust denetimi yardımcıdır, son söz Python'undur.
5. **İlk işlem günü uyarısı.** Ön uçta; adım 1'in T düzeyi kullanılır.
6. **Dondur (`freeze_record`).**
   - Ön koşullar **yeniden** denetlenir (Fable denetimi B3: düğme ön koşulsuz açılabiliyordu). Engel varsa `FREEZE_PREFLIGHT_BLOCKED`; Python çağrılmaz, kayıt ve olay dosyası yazılmaz.
   - `python -m borsai.freeze registry/inputs/<T>.json` koşar; stdout'un son satırı kayıt yolu.
   - Kayıt okunur (`borsai.record/1`) ve **parite** yapılır (`parity::compare_record`): kayıttaki her hücre için model gömülü değilse "desteklenmiyor" listesine yazılır (uyuşmazlık değil); `params_sha256` gömülüyle aynı olmalı; model kaydın kendi `model_inputs`'u ile (f6 ve TÜFE alanları kayıttaki gibi; uygulama TÜFE'yi yeniden aramaz) Rust'ta yeniden koşulur; durum aynı olmalı; çıktılar §7.11'deki kurallarla karşılaştırılır. Uygulamada olup kayıtta olmayan model de uyuşmazlık değildir (kayıt INDEX'ten eskidir).
   - Uyuşmazlık varsa `app/parity/incidents/<UTC>.json` yazılır (`borsai.app_parity_incident/1`: kayıt yolu, uygulama sürümü, derleme HEAD'i, INDEX sha'sı, rapor). **Kayıt yine geçerlidir**; uygulamanın sayısı değil kayıt esastır. Repo anlık kopyasında `incidents/` dizininde yalnız `.gitkeep` vardır; yani bu kopyada kayıtlı bir uyuşmazlık olayı yoktur.
   - Python hataları stderr metninden sınıflanır: `DUPLICATE_RECORD` → `FREEZE_DUPLICATE_RECORD`, "iptal ilk işlem gününden" → `FREEZE_CANCEL_AFTER_T`; tanınmayan hata ham stderr'le `PYTHON_FAILED` kalır (denetim notu B11: metne bağlı sınıflama, güvenli yönde).
   - "Şimdi yapılacaklar" komut bloğu üretilir; uygulama bunları **çalıştırmaz**:

```bash
cd <repo_root>
git add registry/inputs/<T>.json registry/source_docs/<T>/ registry/records/<T>/<dosya>.json
git commit -m "BORSAI_RECORD_<T>: prediction record before first trading day" -- <aynı yollar>
git push origin main
.venv/bin/python -m borsai.push_proof $(git rev-parse HEAD)
git add registry/push_proofs/
git commit -m "BORSAI_PUSH_PROOF: $(git rev-parse HEAD)" -- registry/push_proofs/
git push origin main
```

Yorum satırı yoktur; her `commit` `--` ile yalnız ilgili yollara sınırlanır (başka değişiklik yanlışlıkla kayda girmesin). Zaman kanıtı yerel saat değil push'tur; push kanıtının oluşturulma zamanı T'den önceyse kayıt "canlı" adayıdır. Sınıf (LIVE / LATE_RECORD / RETRO) uygulamada hesaplanmaz, skorlamada tarihlerden hesaplanır.

**İptal (`cancel_record`).** `python -m borsai.freeze --cancel registry/records/<T>/<dosya>.json --reason "<neden>"`. Neden boş olamaz. Python T'den itibaren iptali reddeder; uygulama kuralı önceden gösterir ama son söz Python'undur. İptal edilen dosya silinmez; sicilde iptal bağıyla gösterilir.

Kaynak dosyalar: `app/src-tauri/src/commands/freeze.rs`, `parity.rs`, `inputs_doc.rs`, `source_docs.rs`, `src/json_out.rs`, `docs/app/SPEC_APP.md` §3e, `docs/fable_app_audit/AUDIT.md` (B3, B11).

### Python'a düşülen yerlerin tamamı

| Rust yeri | Python çağrısı | Amaç |
|---|---|---|
| `config::validate_repo_value` | `-c "import borsai, os; print(os.path.realpath(borsai.__file__))"` | repo modu: `borsai` repo içinden mi geliyor |
| aynı, derin doğrulama | `-c` `market20.load_live_sources()` | XU100 ve takvim son günleri, XU100 sha'sı |
| `market20::market20_value` | `-c` `market20.market20(...)` `<ref_date> <T>` | senaryonun f6'sı |
| `freeze::preflight_at`, `post_d1::post_d1_preflight_at` | `-c` `borsai.__file__` | ön koşul `BORSAI_IMPORT` |
| `freeze::inputs_pit_in` | `-c` `registry.inputs_pit_problems(...)` `<yol>` | yetkili girdi denetimi |
| `freeze::freeze_in` | `-m borsai.freeze <girdi belgesi>` | resmî kayıt |
| `freeze::cancel_in`, `post_d1::post_d1_cancel_in` | `-m borsai.freeze --cancel <kayıt> --reason <neden>` | iptal kaydı |
| `post_d1::post_d1_preflight_at` | `-c` `registry.t_open(D_1, outcomes.load_calendar())` | T_open (D2 takvim günü 09:40) |
| `post_d1::post_d1_freeze_in` | `-m borsai.freeze --post-d1 <T>` | D1 sonrası kayıt (stdout: `path`, `T_open`, `note`) |

Başka hiçbir yerde süreç çalıştırılmaz (`Command::new` yalnız `python.rs` ve `git.rs`'te geçer).

Kaynak dosyalar: `app/src-tauri/src/python.rs`, `src/commands/config.rs`, `market20.rs`, `freeze.rs`, `post_d1.rs`.

---

## 7.10 D1 sonrası kayıt sihirbazı

İlk işlem günü (D_1) tavanda kapandıktan sonra, ikinci işlem günü açılmadan önce (T_open = D2 takvim günü 09:40, İstanbul) `post_d1_hazard_v0` ile ikinci bir resmî kayıt yazılabilir. Akış dondur sihirbazının kalıbını izler; uygulama ağa çıkmaz, bülten okumaz, etiket üretmez.

1. **Ön koşullar (`post_d1_preflight`).** Engeller: `GIT_HEAD`; `INDEX_SHA` ve `INDEX_POST_D1_SHA` (iki dizin de gömülüyle aynı); `BORSAI_IMPORT`; `NO_PRE_LISTING_RECORD` (arzın sicilde iptal edilmemiş ve `ceiling_hazard_v0` hücresi tahmin vermiş bir listeleme öncesi kaydı yoksa); `D1_PENDING` (`data/outcomes/<T>.csv`'de h = 1 satırı `OK` ya da `NA_LIMIT` ve tarihli değilse); `CALENDAR_NOT_AVAILABLE` (Python T_open'ı hesaplayamazsa). Uyarılar: `UNCOMMITTED` (`git status --porcelain -- data registry/post_d1` boş değil; Python'un sıra bekçisi durabilir), `T_OPEN_PASSED` (yerel saate göre T_open geçmiş; yerel saat kanıt değildir, yalnız bilgidir).
2. **Bülten ve sonuç güncellemesi — yalnız komut metni** (ağ gerektirir):

```bash
cd <repo_root>
.venv/bin/python -m borsai.outcomes update --through <D_1>
git add data/
git commit -m "BORSAI_OUTCOMES_<D_1>: bulletins and outcomes through D_1" -- data/
```

3. **Kayıt (`post_d1_freeze`).** Ön koşullar yeniden denetlenir; `python -m borsai.freeze --post-d1 <T>` koşar ve JSON basar (`path`, `T_open`, `note`). Kayıt (`borsai.post_d1_record/1`) okunur ve parite yapılır (`compare_post_d1_record`): model, **base kaydın** `model_inputs`'u (girdi belgesi değil; errata H36) ve kaydın `d1` bloğuyla (`fields_raw`, `half_day`, `halt_flag`) Rust'ta yeniden koşulur; ikincil tavan yolu ancak base kayıtta `ceiling_path_v0` tahmin vermişse verilir. Ek olarak base kayıt dosyasının sha256'sı kayıttakiyle aynı olmalı, ve karşılaştırıcıların `comparators_conditional` kopyaları Rust `survival::conditional(S, 1)` ile |Δ| ≤ 1e-12 denetlenir (bilgi). Python hataları stderr'den sınıflanır (`POST_D1_DUPLICATE_RECORD`, `POST_D1_CALENDAR_NOT_AVAILABLE`, `POST_D1_NO_BASE_RECORD`, `POST_D1_NOT_TRADED`, `POST_D1_CANCEL_AFTER_T_OPEN`).
4. **Şimdi yapılacaklar** (çalıştırılmaz): `git add registry/post_d1/<T>/`, `git commit -m "BORSAI_POST_D1_<T>: post-D1 record before T_open" -- registry/post_d1/<T>/`, push, push kanıtı ve onun commit/push'u. Push kanıtı T_open'dan önceyse kayıt canlı adayıdır.

**İptal (`post_d1_cancel`).** Uygulama `python -m borsai.freeze --cancel <kayıt> --reason "…"` komutunu kendisi çalıştırır ve kalan commit/push satırlarını gösterir (iptal satırı tekrar edilmez). T_open'dan sonra Python reddeder. Not: EK 3 §6.6 iptal için `--cancel-post-d1` adını önermişti ("CLI adı Python'da doğrulanır"); uygulanan kod ortak `--cancel` bayrağını kullanır.

**Görüntüleme.** `post_d1_view` yalnız `registry/post_d1/<T>/` dizinini okur (eski kohortun D1 sonrası kayıtları hiçbir komutta okunmaz). Varsayılan, en erken etkin kayıttır. Durumlar: `NO_RECORD`, `J0` (j = 0'da satır gizli; model j ≥ 1'de tanımlı), `PREDICTED`, `REFUSED`, `NOT_APPLICABLE` (D1 tavanda kapanmadı), `NO_CELL`. S yalnız kayıttan okunur ve aynı `ceiling_display` yolundan geçer. Resmî karttaki "D1 sonrası" satırı da (`add_post_d1_row`) yalnız bu görünümden beslenir.

P2 raporuna göre geçici bir klonda uçtan uca koşu (U69) yeşildir: parite 1/1, karşılaştırıcı |Δ| 0, kayıt izlenmeyen dosya olarak kaldı, uygulamanın commit sayısı değişmedi, T_open sonrası iptal Python tarafından reddedildi.

Kaynak dosyalar: `app/src-tauri/src/commands/post_d1.rs`, `parity.rs` (`compare_post_d1_record`, `check_comparators_conditional`), `ceiling.rs` (`outcome_day1_in`, `add_post_d1_row`), `docs/app/SPEC_APP_EK3.md` §6.5–§6.6, `docs/app/p2/RAPOR.md`.

---

## 7.11 Parite: Python ile Rust'ın aynı sayıyı verdiğinin kanıtı

İki gerçekleme her zaman ayrışma riski taşır: biri değişir, öbürü unutulur; ya da ikisi "aynı formülü" farklı yuvarlar. Şartnamenin cevabı (SPEC_APP §1.2–§1.3): tanım Python'dadır, Rust bir porttur, ve port **Python'un kendi ürettiği** cevaplarla sınanır. Düzenek dört parçadır.

### Üretici: `app/parity/gen_golden.py`

- Repo `.venv`'iyle, repo kökünden koşar ve yalnız `app/parity/` altına yazar. Yalnız standart kütüphaneli predict yolunu import eder; numpy ve scikit-learn yüklenmez (U1; `test_gen_golden.py` bunu alt süreçte `sys.modules` taramasıyla sınar).
- Rastgelelik sabit tohumla: `SEED = 20260922`. `--check` bayrağı dosyaları yeniden üretip diskteki baytlarla karşılaştırır.
- Okuduğu veri: model dosyaları; eğitim tablosunun yalnız **girdi** sütunları; PB kanıt dosyasından yalnız sekiz PB alanı; sicildeki girdi belgeleri; kayıtlardan yalnız f6 alanları; TÜFE tablosu; eski kohortun **yalnız açık küme** üyelerinin girdi belgeleri (kasa satırları `_assert_open` bekçisiyle dışlanır, kod basılmaz). Sonuç dosyaları (`data/outcomes*`) **okunmaz**: altın vektörler aritmetiği sınar, gerçekleşen değerleri değil.
- Girdi planı (taban, model başına): 99 eğitim satırı, 7 sicil girdisi, 80 rastgele geçerli girdi ve 207 uç/ret satırı (her ret kodu, Decimal sözdizimi uçları: Unicode boşluk ve rakamlar, alt çizgi, üs sınırları, `"1e400"`; her özelliğin alt/üst aralık dışı; `_pct` yuvarlama sınırları; bütün market20 nedenleri; dokuz PB özdeşlik/aralık adı …). Yeni model aileleri kendi satırlarını `only` etiketiyle ekler: tavan yolu +76 satır (fiyat adımı sınırları, snap, üs biçimleri), v1 ailesi +224 satır (TÜFE ve rejim uçları, açık kohort), düşen arz aynı kalıpla. D1 sonrası modelin D1 blokları **sentetiktir** (`synth_d1`, ayrı rastgele akış: eski satırlar değişmesin diye).
- Her satır: `case_id`, `model_id`, `params_sha256`, `inputs`, `extra` (f6), `expected` ve etiketler. `expected` üç biçimden biridir: `output` (Python çıktısı), `error.code` (Python `PredictError`), `exception` (Python'un etiketsiz istisnası: Rust burada `DOMAIN_ERROR` döner).
- Ayrıca: `_patched_params.jsonl` (test içinde parametresi bilerek bozulmuş satırlar: `PARAMS_INVALID`, `SCHEMA_UNSUPPORTED`, havuzlama, yetersiz hücre …; dondurulmuş dosyalarda hiç tetiklenmeyen yollar böyle sınanır), üç `*.conditional.jsonl` (tavan yolu koşullu karışımı), `dec_cases.json` (sayısal birim durumları) ve `tufe_cases.json`.
- `MANIFEST.json`: tohum, INDEX ve ikinci dizin sha'ları, model listesi, satır sayıları, kapsama muafiyetleri ve **portun tanımı olan 11 Python dosyasının sha256'sı** (`predict_sources_sha256`).

Repo anlık kopyasındaki satır sayıları:

| Dosya grubu | Satır |
|---|---|
| 15 eski model × 392 + `v1_5_market20_v0` 395 | 6 275 |
| 3 tavan yolu modeli × 468 | 1 404 |
| 4 `ceiling_hazard_v1` modeli × 616 | 2 464 |
| 4 `fall_d10_v0` modeli × 635 | 2 540 |
| `post_d1_hazard_v0` | 238 |
| `_patched_params.jsonl` | 61 |
| 3 koşullu dosya × 40 taban satır | 120 |
| **Toplam** (`golden/*.jsonl`) | **13 102** |

`dec_cases.json`'un bölümleri: `parse` 59, `pct` 16, `mul28` 8, `to_float` 20, `fsum` 29, `int_ratio` 15, `exact200` 16, `pb1_ln` 8, `real_size` 10 durum ve `limit_path` (fiyat adımı tablosu ve kesin bağlam ölçümleri). `tufe_cases.json`: `month_for` 8, `index_for` 24, `index_for_guard` 3, `parse` 15 ret, `prefix` 12, ekleme komutu metni.

### Rust testi: `cargo test -p borsai_predict --test golden`

Her satırda Rust `predict` çağrılır ve sonuç şu kurallarla karşılaştırılır:

| Alan | Kural |
|---|---|
| `refused.code`, `refused.field` | birebir (ikisi de null ya da ikisi de aynı) |
| sayısal çıktılar (`return`, `price`, `p_up`, `hazard[]`, `S[]`, `P_L[]` …) | mutlak \|Δ\| ≤ 1e-9; null ↔ null |
| `direction`, `return_clipped`, `clipped`, `clipped_features`, `regime_*`, `add_sale_used` | birebir |
| metin alanları (`limit_path.C`, `snapped_ipo_price`, `tick`, `tufe_index_used`, `d1_turnover_ratio`) | birebir (Decimal üs biçimi dahil) |
| `f1r_raw` | göreli: \|Δ\| ≤ 1e-9 · max(1, \|beklenen\|) (değer 10⁸–10¹⁰ mertebesinde) |
| koşullu değerler (`S_cond`, `P_L_cond`, `p_break_next`) | \|Δ\| ≤ 1e-12 |
| `warnings` | (kod, özellik/ufuk) çok kümesi eşit; `message` karşılaştırılmaz; sayısal ek alanlar ≤ 1e-9, metin/mantıksal ek alanlar birebir |
| anahtar kümesi | Python çıktısındaki her anahtar Rust'ta da var, tersi de |

Test ayrıca model başına geçen satır, bit-eşit satır ve en büyük |Δ|'yı `target/parity_report.json`'a yazar. İki ek koruma vardır:

- **`predict_sources_unchanged`**: MANIFEST'teki 11 Python dosyasının sha256'sı diskteki dosyalarla aynı olmalı. Biri Python modelini değiştirirse test kırmızıdır; altın vektörler yeniden üretilir ve Rust uyumlanır. Tolerans gevşetilmez.
- **Bit-eşitlik tabanı (`app/parity/bit_equal_floor.json`)**: her model için bit-eşit satır sayısı bir tabanın altına düşemez. Tabanı olmayan yeni model kırmızıdır; taban bilinçli yazılır. Gerekçe (Fable denetimi B10): altın vektörde son haneyi değiştiren bir mutasyon (|Δ| = 6.7e-16) 1e-9 toleransını geçiyordu; taban bu "sessiz sürüklenmeyi" yakalar. Repo anlık kopyasındaki tabanlar 28 model için toplam 12 879 satırdır: modellerin çoğunda bütün satırlar bit-eşittir; istisnalar `pb_v0` (390/392), `pb_ceiling_v0` (390/392), `pb_ceiling_path_v0` (464/468) ve `post_d1_hazard_v0`'dır (204/238). Dördünün ortak nedeni ln yoludur (§7.8.1): Python 60 haneli `Decimal.ln()` kullanır, Rust kesin değeri f64'e yuvarlayıp `f64::ln` alır. Raporlara göre en büyük farklar 1.14e-13 (eski PB satırları) ve 1.78e-15 (D1 sonrası) — ikisi de toleransın çok altında.

Öteki crate testleri: `coverage` (her ret ve uyarı kodu altın vektörde en az iki satırda; her getiri ufkunda alt ve üst kırpma; muafiyetler MANIFEST'te gerekçeli), `dec_semantics` (`dec_cases.json`; pb1 ln için ≤ 5e-15), `tufe_semantics`, `v1_semantics`, `fall_semantics`, `post_d1_semantics` (Python sırasının ve kodlarının birim düzeyinde sınanması).

### Eski dosyalar dokunulmaz: `golden_unchanged.sh`

Yeni model eklemek eski altın satırları değiştirmemelidir; değiştirirse portun eski davranışı fark edilmeden kaymış olabilir. Betik, git'ten salt okunur biçimde dört taban commit'i (`0b67f5d`, `7133991`, `d01daa4`, `0041dc9`) okuyup eski `.jsonl` dosyalarının, yamalı dosyanın ilk N satırının ve `dec_cases.json`'un eski bölümlerinin **bayt bayt** aynı kaldığını denetler. Yeni satırlar yalnız sona eklenir.

### Gerçek kayıtlarla parite

- `records_parity` (U6): sicildeki her tahmin kaydı için kayıttaki `model_inputs` ile Rust çıktısı kaydın çıktısına eşit (kayıt INDEX'ten eskiyse eksik modeller "kayıtta yok" sayılır, uyuşmazlık değildir). Raporlara göre eski 7 kayıt × 16 model hücresi bit-eşittir.
- `post_d1_oot_open` (K-P2-4): eski kohortun kasa dışı D1 sonrası kayıtları **71/71** (59 tahmin, 9 kapsam dışı, 3 ret), en büyük |Δ| 8.88e-16.
- `fall_oot_open` (K-P4-3): açık kohort kayıtlarında 284 düşen arz hücresi **284/284**, hepsi bit-eşit.
- Kasa (SEALED) dizinleri bu testlerde açılmaz; çıktıda yalnız sayılar basılır.

Bu üç test asıl repoyu ister (`BORSAI_REPO` ortam değişkeni) ve `#[ignore]` işaretlidir: yalın `cargo test`'te "ignored" görünür, `test.sh` `--include-ignored` ile koşar. Ortam yoksa test **kırmızı** olur, sessizce "ok" dönmez (denetim bulgusu B5'in düzeltmesi).

### Bağımsız denetim

Fable'ın uygulama denetimi (19 modellik aşamada) üreticiyi kullanmadan 122 yeni girdi × 19 model = 2 318 satırlık bağımsız örneklem kurdu: 0 uyuşmazlık, en büyük |Δ| 1.14e-13, 2 315/2 318 bit-eşit. Aynı denetim 11 mutasyondan 9'unun testlerde kırmızıya düştüğünü ölçtü; yeşil kalan ikisi (tolerans altı son hane değişimi ve ön uçtaki bir beyan türetimi) sonraki düzeltme turunda testlere bağlandı ve kapanış denetiminde kırmızıya düştü.

Kaynak dosyalar: `app/parity/README.md`, `gen_golden.py`, `test_gen_golden.py`, `golden/README.md`, `golden/MANIFEST.json`, `bit_equal_floor.json`, `dec_cases.json`, `tufe_cases.json`, `incidents/`, `app/tests/golden_unchanged.sh`, `crates/borsai_predict/tests/*.rs`, `src/commands/parity.rs`, `docs/fable_app_audit/AUDIT.md`, `KAPANIS.md`, `docs/app/p1/RAPOR.md`, `p2/RAPOR.md`, `p34/RAPOR.md`.

---

## 7.12 Testler: "cargo 164" neyi sınıyor

### Sayının kökeni

`app/src-tauri` altında (crate dahil) **169** `#[test]` fonksiyonu vardır (bu bölüm için kaynak dosyalarda sayıldı). Bunlardan 13'ü `#[ignore]` işaretlidir: 8'i asıl repoyu (`BORSAI_REPO`) ister, 5'i geçici bir git klonu ister. `app/scripts/test.sh` şunu koşar:

```bash
(cd src-tauri && BORSAI_REPO="$REPO" cargo test --workspace -- --include-ignored \
  --exact --skip freeze_flow --skip prepare_screens --skip personal_isolation --skip post_d1_flow --skip prepare_screens_p2)
npm test                                                  # tsc + vitest
(cd "$REPO" && .venv/bin/pytest -q app/parity/test_gen_golden.py)   # 8 Python testi
bash tests/golden_unchanged.sh
```

Yani 169 − 5 (geçici klon isteyen e2e testleri) = **164** cargo testi koşar; son kabul raporundaki "cargo 164 / 0" budur (`docs/app/UI_FIX_RAPOR.md`; aynı raporda vitest 376, Python parite 8). Atlanan beş test kendi betikleriyle koşar: `tests/e2e_freeze_tmp_repo.sh`, `e2e_personal_isolation.sh`, `e2e_post_d1_tmp_repo.sh` (asıl repoya hiçbir şey yazılmaz; `git clone --local` ile geçici klon). Yeni bir ortam isteyen test atlama listesine girmezse env'siz koşar ve kırmızı olur (fail-closed).

**Not:** Bu bölüm yazılırken testler yeniden koşulamadı (yazım ortamından crates.io'ya erişim yoktu); sayılar kaynak koddan sayıldı, sonuçlar raporlardan alındı.

### Dağılım

| Yer | Test sayısı | Ne sınar |
|---|---|---|
| crate kaynak içi (`dec`, `path`, `post_d1`, `tufe`, `fall`, `sum`, `survival`) | 18 | Decimal ayrıştırma ve üs kuralları, `py_str`, `ratio_to_f64`; fiyat adımı sınırları ve ölçülmüş limit yolları; merdiven sırası, havuzlama ve kırpma; kuantil kuralı; D1 değerlendirme sırası; Neumaier; koşullu j = 0 = koşulsuz |
| crate `tests/golden.rs` | 9 | altın dosyalar, kaynak sha'ları, 27 model paritesi + bit-eşitlik tabanı, D1 sonrası, düşen arz, koşullu karışım, seri kopyasının bit-eşitliği, karşılaştırıcının kendisinin uyuşmazlığı yakaladığı |
| crate `tests/coverage.rs` | 5 | ret/uyarı kodu kapsaması (genel, tavan yolu, v1, D1 sonrası, düşen arz) |
| crate `tests/dec_semantics.rs` | 12 | `dec_cases.json`'un her bölümü |
| crate `tufe_`, `v1_`, `fall_`, `post_d1_semantics` | 18 | Python sırası ve kodları |
| crate `tests/records_parity.rs` | 3 (ignore) | gerçek kayıtlarla parite |
| uygulama kaynak içi (`form`, `json_out`, `clock`, `freeze`, `parity`, `predict` …) | 20 | virgül/tutarlılık/özdeşlik notları, Python baytlı JSON, İstanbul tarihi, yol bekçisi, parite karşılaştırıcısı, TÜFE kural sırası |
| `tests/build_embed.rs` | 7 | 27 kayıt pini, TÜFE yalnız deflatörle, eksik dosya derlemeyi kırar, fazla INDEX kaydı listelenir, git kilitsiz ve beyaz listeli, ikinci dizin pini |
| `tests/integrity.rs` | 6 | gömülü sha = INDEX, bozuk kopya → `INTEGRITY_FAILED` (fail-closed), `predict_all` 27 sütun, seri kopyası, D1 sonrası zinciri |
| `tests/no_network.rs` | 1 | macOS grafiğinde ağ paketi yok; `Cargo.lock`, `Cargo.toml`, `package-lock.json` taraması; CSP `connect-src`; yetenekler yalnız iki izin |
| `tests/stage2.rs` | 20 | ret blokları, f6 yok/bayat, kırpma, uyarılar hücre gizlemez, şerit, beyanın komutlara girmemesi, senaryo yol bekçisi, git beyaz listesi, ayar sıfırlama, öne çıkarma kuralları, kart fikstürleri |
| `tests/stage3.rs` | 23 | girdi belgesi baytları Python'la aynı, `validate_inputs` portu, kaynak belge kopyalama, parite sayımı, sicil, ön koşul engelinde Python'un çağrılmaması, resmî görünümün yalnız kayıttan okuması, TÜFE engeli, D1 sonrası okuyucu ve sihirbaz |
| `tests/stage4.rs` | 6 | `scores.json` fail-closed bütünlük, sürüm uyumsuzluğu, başlık alanları |
| `tests/oot_panel.rs` | 2 | zaman-dışı panel: satırlar yalnız açık kümede, gerçek dosya |
| `tests/sade.rs` | 13 | `ui_view` geriye uyumu, hesaplayıcı beklenen sayıları, ana ekran kapısı, monitör ve arz görünümü (gerçek repo), işlem sayısı çubukları, pencere sabitleri = `tauri.conf.json`, kırılma kartı ve sha uyuşmazlığında kapanma, performans görünümü |
| `tests/e2e.rs` | 6 (5 ignore) | geçici klonda dondur akışı, kişisel kayıt izolasyonu, beyanın yalnız senaryo modülünde olması, D1 sonrası akış, ekran görüntüsü hazırlığı |

Birçok entegrasyon testi ayrıca **ön uç fikstürlerini** üretir: `BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test stage2` (ya da `stage3`, `stage4`, `sade`, `oot_panel`) Rust komutlarının gerçek çıktısını `app/tests/fixtures/ui/*.json`'a yazar; normal koşuda fikstürün güncel olduğu sınanır. Böylece vitest render testleri elle yazılmış sayı kullanmaz.

Kaynak dosyalar: `app/scripts/test.sh`, `app/src-tauri/tests/*.rs`, `crates/borsai_predict/tests/*.rs`, kaynak içi `#[cfg(test)]` modülleri, `app/tests/*.sh`, `docs/app/UI_FIX_RAPOR.md`, `docs/app/ui_fix_test_runs.txt`.

---

## 7.13 Şartnameden sapmalar, açık notlar ve belirsizlikler

| Konu | Şartname / belge | Kod | Durum |
|---|---|---|---|
| Kesin aritmetik türü | SPEC_APP §1.3: `num-rational::BigRational` | `Dec` (BigUint × 10^üs) | bilinçli; README'de |
| `Cargo.lock`'ta ağ paketi | U34: "Cargo.lock'ta yok" | `reqwest`/`hyper` var (yalnız mobil hedef) | kabul (denetim B9); test macOS grafiğinde |
| Düşen arz portu | EK 3 §8 önerisi | Python `predict_fall.py` (11 fark) | çelişkide Python kazanır; `app/parity/README.md` tablosu |
| D1 sonrası iptal bayrağı | EK 3 §6.6: `--cancel-post-d1` (doğrulanacak) | `--cancel` | kod ortak bayrağı kullanır |
| Python hata sınıflaması | — | stderr metnine bağlı | güvenli yön (denetim B11; Python'a makine okunur kod eklenmesi önerilmiş) |
| Dışa aktarmada hedef bağ | U27 | hedefin kendisi bağsa her durumda ret | aşırı ret, güvenli yön (kapanış C1) |
| `app/README.md` | — | bazı satırlar eski aşamadan kalma ("19 gömülü model", `streak_view(ticker?, userDays)`) | **belirsiz/eskimiş**: güncel kod 27 model ve beyansız `streak_view(ticker)` |
| Windows | hedef değil | §7.5 notları | ölçülmedi |
| `test.sh`'taki `--include-ignored` | kapanış C2: bayrağı koruyan test önerilmişti | bayrak ve atlama listesi betikte; ayrı statik koruma testi bu anlık kopyada bulunamadı | **belirsiz** |

Kaynak dosyalar: `app/README.md` ("Bilinen sapmalar"), `docs/app/SPEC_APP.md`, `SPEC_APP_EK3.md`, `app/parity/README.md`, `docs/fable_app_audit/AUDIT.md`, `KAPANIS.md`.

---

## 7.14 Akılda kalacaklar

- Arka uç üç katmanlıdır: ön uç (hesap yapmaz) → 55 Rust komutu → saf model crate'i; repo modunda ayrıca salt okuma git ve repo içi Python.
- Derleme 27 modeli, D1 sonrası modeli, TÜFE tablosunu ve skor anlık kopyalarını ikiliye gömer; sabit listeye uymayan INDEX derlemeyi kırar. Açılışta sha256 zinciri doğrulanır; tek uyuşmazlık bütün tahmini kapatır.
- Modellerin Rust portu Python'un yalnız formüllerini değil **sayı türlerini ve yuvarlama sırasını** da taklit eder: 28, 60 ve 200 haneli Decimal bağlamları, doğru yuvarlanmış dönüşümler, CPython `sum()`'ın Neumaier toplaması.
- Parite, Python'un ürettiği 13 102 satırlık altın vektörle, 1e-9 toleransla ve model başına bit-eşitlik tabanıyla sınanır; Python tanımı değişirse test kırmızıdır. Bilinçli tek fark ln yoludur (en çok 1.14e-13).
- Resmî kaydı her zaman Python yazar; uygulama kaydı okur, kendi hesabıyla karşılaştırır, uyuşmazlığı olay dosyasına yazar ve git komutlarını yalnız metin olarak gösterir.
- Ağ yoktur; git yalnız okur; kişisel kayıt repo altına düşemez; resmî görünümde model yeniden çalıştırılmaz.
- `test.sh`, 169 Rust testinin 164'ünü koşar; geri kalan beşi geçici klon betikleriyle koşar.

Kaynak dosyalar: bu bölümün 7.1–7.13 alt bölümlerinde listelenenler.

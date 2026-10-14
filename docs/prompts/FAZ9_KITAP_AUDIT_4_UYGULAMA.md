# FAZ9_KITAP_AUDIT_4_UYGULAMA — Masaüstü uygulamasının bağımsız denetimi

**Model: Claude Code / Fable · yüksek**

- **TASK_ID:** `BORSAI_FAZ9_KITAP_AUDIT_4_20261008`
- **Klasör:** repo kökü `~/Desktop/BorsAi`. Ağ yok.
- **Ortak kurallar:** önce `docs/prompts/FAZ9_KITAP_AUDIT_ORTAK.md`'yi oku. Bu görevde `<n>` = 4, `<AD>` = UYGULAMA.
- **Rapor:** `docs/fable_kitap_audit/AUDIT_4_UYGULAMA.md`. Ekler `docs/fable_kitap_audit/ekler/4/` altına.
- **Araç zinciri:** `source app/scripts/env.sh`.

## Kapsam

- `kitap/07_uygulama_rust.md`'nin tamamı.
- `kitap/08_uygulama_arayuz.md`'nin tamamı.

Asıl sorular:
- **Uygulama, Python'daki dondurulmuş modellerle her girdide aynı sayıyı veriyor mu?**
- **Ekranda yazan metin, gösterilen sayının ne olduğunu doğru anlatıyor mu?**

Proje sahibi uygulamayı yakında hocalarına sunacak. Ekranda yanlış ya da yanıltıcı bir şey varsa önce onu bul.

## ÖNCE OKU

- CLAUDE.md
- `docs/fable_kitap_audit/README.md`
- `kitap/07_uygulama_rust.md` ve `kitap/08_uygulama_arayuz.md`
- Uygulama şartnameleri ve raporları:
  - `docs/app/SPEC_APP.md`, `SPEC_APP_EK2.md`, `SPEC_APP_EK3.md`
  - `docs/app/UI_V2_HARITA.md`, `UI_V2_RAPOR.md`, `UI_FIX_RAPOR.md`
- Parite: `app/parity/README.md`, `gen_golden.py`, `golden/`
- Kod:
  - `app/src-tauri/` (`build.rs`, `build_embed.rs`, `tauri.conf.json`, `capabilities/`, `src/`)
  - `app/src-tauri/crates/borsai_predict/`
  - `app/src/` (`api.ts`, `state.ts`, `render/`, `i18n/tr.ts`, `sade/`, `screens/`)
- Önceki uygulama denetimi (yeniden yapma; iddia olarak kullan): `docs/fable_app_audit/AUDIT.md` ve `KAPANIS.md`

## Adım 0

`FAZ9_KITAP_AUDIT_1_VERI.md`'nin Adım 0'ıyla aynı: HEAD, fark listesi ve izlenmeyen dosyalar. Koruma ölçümü → `ekler/4/koruma_once.txt`.

Derleme ve test gerektiren her şey **klonda** yapılır, asıl repodaki `app/` altında hiçbir dosya oluşmaz:
- klon: `git clone --local . /tmp/borsai_kitap_audit_4/clone`;
- `.venv` ve `app/node_modules` bağları klonun `.git/info/exclude`'unda;
- `CARGO_TARGET_DIR=/tmp/borsai_kitap_audit_4/target`.

Sonda `git status --porcelain -- app` boş olmalı.

## Adımlar

Sıra önem sırasıdır. Her adım bitince raporu güncelle.

**1. Yeni girdilerle bağımsız parite (§7.8, §7.11).**
- 35 altın vektör var. Bunlar uygulamadaki bütün modelleri ve ret yollarını kapsıyor mu?
- Ayrıca kendi girdilerini üret: H99 aralıklarında en az 200 rastgele geçerli girdi ve uç durumlar:
  - f3 eksik;
  - f6 reddi;
  - sınır değerleri;
  - TÜFE ayı yok;
  - yarım gün.
- Her girdiyi Python `predict*` fonksiyonlarından ve Rust `borsai_predict`'ten geçir. Rust tarafı için klonda geçici bir test ikilisi yazabilirsin.
- Her model ve her çıktı alanı için maks |Δ| ölç. Şartnamedeki pariteyle (bit-eşit ya da tolerans) karşılaştır.
- Uygulama hangi modelleri hesaplıyor, hangilerini yalnız kayıttan okuyor? `break_floor_v0` uygulamada nasıl yer alıyor? `borsai_predict`'te kırılma modülü yok; uygulama bu modelin sayısını nereden alıyor?

**2. Ekrandaki metin, sayının anlamını doğru anlatıyor mu? (bölüm 8)** Her sade ekranda (§8.12–§8.20) gösterilen her sayı için şu zinciri kur:
- Rust komutu;
- model çıktısının hangi alanı;
- `render/format.ts`'deki biçim;
- `i18n/tr.ts`'deki etiket.

Etiketin söylediği şeyle sayının matematiksel tanımı aynı mı? Özellikle:
- **Seri hesaplayıcı (§8.16):**
  - "Seri j gün sürdüyse yarın da tavan" olasılığı h_{j+1} mi, S_{j+1}/S_j mi? (İkisi eşit olmalı; göster.)
  - j ≥ 3'te sabit kalması g3 grubundan mı geliyor?
  - UI_FIX'te eklenen gün grubu notu bunu doğru söylüyor mu?
  - Beklenen seri uzunluğu ΣS_k mı?
- **Hüküm kelimeleri** (geçiyor / ayırt edilemiyor / geçemiyor): ekranda gösterilen hükümler `scores*.json` ile tutuyor mu? Aralık 0'ı içerirken "geçiyor" yazan bir yer var mı?
- **Üç terazi:** ekranda backtest, canlı ve OOT sayıları hiçbir yerde toplanmıyor ya da karıştırılmıyor mu? Canlı n = 0 olan bir modelde ekran canlı başarı izlenimi veriyor mu?
- **Yuvarlama:** yüzde ve ondalık yuvarlaması (yarıya yuvarlama kuralı) şartnameyle aynı mı? 0,665 gibi sınır değerleri bir test girdisiyle göster.
- **Renk dili:** altın renk yalnız model çıktısında mı?

**3. "Ön uç hesap yapmaz" kuralı (§8.6).** `app/src/` altındaki TypeScript'te model çıktıları üzerinde aritmetik var mı (`Math.*`, `*`, `/`, `+`, `-`, toplama, ortalama)? Biçimleme ile hesabı ayır. Kuralı zorlayan test neyi tarıyor, neyi kaçırıyor?

**4. Grafikler (§8.8).**
- SVG grafiklerde eksen, ölçek ve veri eşlemesi doğru mu?
- Yanıltıcı ölçek var mı (sıfırdan başlamayan çubuk gibi)?
- Bir grafiğin verisini Rust çıktısından elle yeniden çiz ve karşılaştır.

**5. Açılış bütünlüğü, gömme ve güvenlik (§7.3–§7.6).**
- `build.rs` ve `build_embed.rs` hangi dosyaları gömüyor? Gömülü sha'lar HEAD'deki dosyalarla tutuyor mu?
- Klonda gömülü bir dosyanın bir baytını değiştir: uygulama açılışta reddediyor mu (ilgili cargo testi)?
- `tauri.conf.json` CSP'sini ve `capabilities/`'ı oku. Ağa çıkış mümkün mü? Hangi yollara yazılabiliyor?
- `src-tauri/src/python.rs` ne yapıyor? Uygulama Python çalıştırıyor mu, hangi durumda, hangi güvenceyle?

**6. Kayıt yazma (§7.9, §7.10).** Uygulamanın dondurma ya da kayıt akışı, Python'un `freeze`'iyle aynı girdiden aynı kanonik JSON'u ve aynı hash'leri mi üretiyor? Klonda geçici bir registry ile göster. CLAUDE.md kural 1'e (bütün modeller, parametre hash'leri) uyuyor mu?

**7. Monitör ve veri akışı (§8.12).** Yeni bir arz eklenince monitöre nasıl geliyor? Hangi dosyaya bağlı? Proje sahibi bunu sordu; kılavuzdaki cevap doğru mu?

**8. Testler ve şartname uyumu (§7.12, §8.10, §8.25).**
- U-kurallarının her biri için bir test var mı?
- cargo ve vitest test sayılarını yalnız listeleme ile ölç, tam koşu yapma.
- SPEC_APP, EK2, EK3 ve UI_V2_HARITA'da uygulanmamış ya da kayıtsız sapmış bir gereksinim var mı?

## Commit

```
git add docs/prompts/FAZ9_KITAP_AUDIT_4_UYGULAMA.md docs/fable_kitap_audit/AUDIT_4_UYGULAMA.md docs/fable_kitap_audit/ekler/4
git commit -m "BORSAI_FAZ9_KITAP_AUDIT_4: independent audit of the desktop app against the project guide" -- docs/prompts/FAZ9_KITAP_AUDIT_4_UYGULAMA.md docs/fable_kitap_audit/AUDIT_4_UYGULAMA.md docs/fable_kitap_audit/ekler/4
```

## Kabul kapısı

- **K1:** En az 200 yeni girdide Python–Rust paritesi model model ölçüldü.
- **K2:** Her sade ekranda her sayı için etiket ↔ tanım zinciri kuruldu. Yanıltıcı metinler listelendi.
- **K3:** "Ön uç hesap yapmaz", gömme bütünlüğü ve kayıt yazma iddiaları kanıtla.
- **K4:** Koruma eşit, `git status --porcelain -- app` boş, hijyen sayımları 0, commit yalnız izinli yollarda.

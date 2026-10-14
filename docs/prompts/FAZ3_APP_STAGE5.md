# TASK_ID: BORSAI_FAZ3_APP_STAGE5_20260923

Model: Opus 5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ: yalnız npm/crates (gerekirse). push/tag/amend yok.

## Bağlam
- Uygulama aşama 0–4 ve Aşama P (P1, P2) tamam. Son commit `0341bc6` (aşama 4). HEAD = origin/main, ağaç temiz [orkestratör ölçtü].
- Bu görev `docs/app/SPEC_APP.md` §7'nin son satırı: **aşama 5, kişisel kayıtlar + cila**. İşin çoğu aşama 2–4'te yapıldı. Bu görev eksikleri kapatır, bir şartname uyumsuzluğunu düzeltir ve uygulamayı Fable uygunluk denetimine hazırlar.
- Zaten var olan (yeniden yazma; yalnız doğrula ve gerekirse genişlet):
  - Kişisel kayıt listesi, aç, sil (onaylı), tekli dışa aktar: `src/screens/scenarios.ts`, `src-tauri/src/commands/scenario.rs`
  - U27 yol bekçisi (`SCENARIO_PATH_INSIDE_REPO`), U28 (`src-tauri/tests/e2e.rs`), U29 (`tests/e2e_freeze_tmp_repo.sh`)
  - Rejim uyarısı sonuç ve doğruluk ekranında (U23), DISCLAIMER altbilgisi (`tests/disclaimer.test.ts`), U21 model kartı testi

### Orkestratörün bulduğu kusurlar (ölçüldü; bağlayıcı)
1. **Mod bandı her ekranda "SENARYO".** `src/main.ts` `band()` her zaman `mode-band mode-scenario` ve `TR.modeScenario` üretiyor, hangi ekranda olunduğuna bakmıyor. Resmi sicil arz sayfası (`app/docs/screens/15_*`, `16*`), dondur sihirbazı (`17–24`) ve doğruluk paneli (`25*–30`) "SENARYO · Bu tahmin sicile girmez" bandıyla görünüyor.
   - Kök neden durum sızıntısı değil, statik kabuk.
   - SPEC_APP §3 genel çerçeve iki bant tanımlar: `SENARYO` (turuncu) ya da `RESMİ KAYIT` (mavi, kayıt dosya adı ve zaman kanıtı durumu).
   - `src/styles.css`'te `.mode-official` sınıfı tanımlı ama hiç kullanılmıyor.
2. **Doğruluk panelinde model başlığında çift ayraç.** `src/render/accuracy.ts:334-335` `ACCURACY.liveHead("", …)` boş başlıkla çağrılıyor. Çıktı: "v1_5_h99 · V1.5 ailesi (Ridge + lojistik) · · n = 6; atlanan = 0".
3. **"Atlanan arzlar (payda; 19)" yanıltıcı.** Gerçek `scores.json`'da `skipped[]` 19 satırın hepsi `OUT_OF_SCOPE`, `SKIPPED` 0. Model başlıkları doğru olarak "atlanan = 0" diyor (dosyadaki `n_skipped` yalnız SKIPPED sayar, `borsai/scoring.py:947`). Aynı panelde "atlanan 19" ile "atlanan = 0" yan yana duruyor.
4. **İki ayrı model kartı.** `render/results.ts` `renderCard` ve `render/accuracy.ts` `card` ayrı kodlar ve alan kümeleri farklı. Sonuç ekranındakinde seri modeli ve prospektif durum var, doğruluk panelindekinde yok.
5. **README derleme satırı.** `app/README.md:74` `npm run tauri build` ve "(+ .dmg)" diyor. Mac'te `.dmg` adımı `bundle_dmg.sh` hatasıyla düşüyor, `.app` yine üretiliyor.
6. **Rejim metni n'siz.** Yıllık D1 tavan oranları doğru [orkestratör `data/training_table.csv`'den ölçtü: 2023 18/19 = 0.947, 2024 27/33 = 0.818, 2025 12/18 = 0.667, 2026 24/29 = 0.828]. Ama metinde n yok, 2023'ün yalnız Eylül–Aralık olduğu yazmıyor ve kaynak "AUDIT §2.4" (eski repo).

### Görev kararları (bu görevde bağlayıcı; SPEC_APP §3'ün uygulanışı)
**G1 · Bant kuralı.**
- Bant tek bir saf fonksiyondan üretilir (öneri: `src/render/shell.ts` içinde `bandFor(screen, view)`); `main.ts` yalnız çağırır.
- Ekran içi geçişlerde bant yeniden üretilir: sicil listesi → arz sayfası → kayıt sekmesi → sihirbaz.

| Ekran / hâl | Sınıf | Metin |
|---|---|---|
| Girdi, Sonuç, Kişisel kayıtlar | `.mode-scenario` (turuncu) | bugünkü: "SENARYO · Bu tahmin sicile girmez" |
| Sicil · liste | `.mode-official` (mavi) | "RESMİ KAYIT · sicil (salt okuma)" |
| Sicil · arz sayfası, kayıt seçili | `.mode-official` | "RESMİ KAYIT · <kayıt dosya adı> · <zaman kanıtı göstergesi>" |
| Sicil · arz sayfası, kayıt yok | `.mode-official` | "RESMİ KAYIT · <T> · kayıt yok" |
| Sicil · dondur sihirbazı | `.mode-official` | "RESMİ KAYIT · hazırlanıyor · Dondur gerçek repoya yazar" |
| Doğruluk | `.mode-neutral` (gri, yeni) | "DOĞRULUK · scores.json'dan salt okuma; uygulama skor hesaplamaz" |
| Ayarlar, Hakkında | `.mode-neutral` | mod sözcüğü yok |

- Zaman kanıtı göstergesi, sayfadaki push kanıtı göstergesiyle aynı veriden gelir ve aynı dizedir. Yeni hesap yok, sınıf (LIVE/LATE) hesaplanmaz.
- Sağdaki repo modu göstergesi her bantta aynen kalır. `INTEGRITY_FAILED` bandı (§2.5) varsa önceliği korunur.
- Arz sayfasındaki kullanıcı beyanı bandı değiştirmez. Beyan yalnız şeritte etikettir (U52).
- Metinler `tr.ts`'e girer (U21 taraması).

**G2 · Payda bölümü (doğruluk paneli).**
- Başlık: "FROZEN olmayan payda satırları (<satır sayısı>)".
- Satırlar `status`'a göre iki alt tabloya ayrılır: SKIPPED ve OUT_OF_SCOPE. Her alt başlıkta kendi satır sayısı; boş alt tablo "yok" yazar.
- Altta sabit not: "Canlı 'atlanan' yalnız SKIPPED satırlarını sayar (değer scores.json'daki n_skipped). OUT_OF_SCOPE satırlar kapsam dışıdır; hiçbir n'e girmez."
- Satır saymak dışında hesap yok (U25).

**G3 · Model kartı tek fonksiyon.**
- İki ekran aynı render fonksiyonunu kullanır (öneri: `src/render/card.ts`).
- Alan kümesi ve sırası iki ekranda aynı: ne yapar · tür · (tavan yolunda) seri modeli · eğitim n / kesim · params sha256 ilk 8 · varyant sayısı · birincil hücre · prospektif durum.
- Prospektif durum `n < 10` iken bugünkü `CARD.liveNoVerdict` metnidir. `n ≥ 10` iken yalnız dosyadaki `verdict`'ten gelir.
- Sonuç ekranında sha çalıştırılan modelin `params_sha256`'sından gelir, doğruluk panelinde `scores.json` `card.params_sha256_8`'den. İkisi de biliniyorsa ve ilk 8 hane farklıysa kartta sarı uyarı: "skorlar bu parametrelerle üretilmemiş". Bu bir sha karşılaştırmasıdır, metrik değildir.

**G4 · Tümünü dışa aktar (§3f).**
- Rust komutu `export_all_scenarios(target)`. Çıktı tek JSON dizisi: okunabilen her kişisel kayıt (OK ve OLD_VERSION), dosyadaki JSON değeriyle, `scenario_id` sırasıyla. Okunamayanlar diziye girmez; sonuç mesajında sayılır.
- Hedef repo altındaysa `SCENARIO_PATH_INSIDE_REPO`. Tekli dışa aktarmanın bekçisi kullanılır, ikinci bir yol denetimi yazılmaz.
- Liste boşken düğme kapalıdır.

**G5 · Rejim metni.**
- Sabit metin olarak kalır; ön uçta hesap yok.
- Yıllara n eklenir: "%95 (18/19; 2023 Eyl–Ara) → %82 (27/33) → %67 (12/18) → %83 (24/29)". Kaynak etiketi `data/training_table.csv` olur.
- Test, `data/training_table.csv`'yi okuyup yıllık oran ve n'leri kendisi hesaplar ve metindekilerle karşılaştırır. Testte hesap serbesttir, `src/`'de değildir.

**G6 · identifier.** `tauri.conf.json` `identifier = "tr.borsai.app"` DEĞİŞMEZ. Yalnız raporla:
- (a) derleme çıktısındaki Tauri uyarısının tam metni
- (b) `app_data_dir`'in gerçek yolu
- (c) orada kaç kişisel kayıt dosyası var (yalnız `ls | wc -l`; dosyaları açma, kopyalama, değiştirme)
- (d) kimlik değişirse ne olur ve taşıma için ne gerekir (tek paragraf)

Karar proje sahibine kalır.

ÖNCE OKU:
- CLAUDE.md
- docs/app/SPEC_APP.md: §2.4, §2.5, §3 genel çerçeve (satır 208–212), §3c, §3e (sicil göstergesi, iptal), §3f, §4, §5.3 U21–U25, §5.4 U27–U29, §7
- docs/app/SPEC_APP_EK2.md: model kartı ve seri modeli satırı
- app/ kodu: `src/main.ts`, `src/screens/ctx.ts`, `src/screens/scenarios.ts`, `src/screens/registry.ts`, `src/render/registry.ts`, `src/render/accuracy.ts`, `src/render/results.ts`, `src/styles.css`, `src/i18n/tr.ts`, `src-tauri/src/commands/scenario.rs`, `src-tauri/tests/e2e.rs`, `tests/*.test.ts`, `scripts/screens.sh`, `src/dev/demo.ts`, `docs/screens/README.md`, `README.md`
- scores/scores.json (gerçek dosya; salt okunur)

## Adımlar
0. Taban:
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3`, `git status --porcelain`
   - İzinli izlenmeyen dosya yalnız `docs/prompts/FAZ3_APP_STAGE5.md`. Başka bir şey varsa DUR.
   - Taban koşusu: `bash app/scripts/test.sh` ve `.venv/bin/pytest -q`. Sayıları ve süreleri not et; bunlar raporun "önce" sütunu.
1. **G1 bant.** Saf fonksiyon, `main.ts` bağlantısı, `.mode-neutral` stili. Testler:
   - A5-1: tablodaki her hâl için sınıf ve metin birebir.
   - A5-2: Doğruluk, Sicil (dört hâl), Ayarlar, Hakkında render'ında `TR.modeScenario` ve `TR.modeScenarioNote` hiç geçmez. Girdi, Sonuç, Kişisel kayıtlarda geçer.
   - A5-3: arz sayfasında bant metnindeki zaman kanıtı dizesi, sayfadaki göstergeyle aynı dizedir (fixture kayıtla).
2. **G2, çift ayraç, G3.** Testler:
   - A5-4: model özetinde "· ·" yok; gerçek `scores.json` ile render'da SKIPPED alt tablosu "yok", OUT_OF_SCOPE 19 satır.
   - A5-5: iki ekranın kartı aynı fonksiyondan, aynı alan sırasıyla. U21 iki ekranda da geçer. sha uyuşmazlığı fixture'ında sarı uyarı çıkar.
3. **G4 tümünü dışa aktar.** Rust komutu, ön uç düğmesi, sonuç mesajı. Testler:
   - A5-6 (cargo): dizi uzunluğu = okunabilen dosya sayısı; her öğede `official: false` var ve `record_type` yok; okunamayan dosya atlanıp sayılır; repo altı hedef reddedilir.
   - `src-tauri/tests/e2e.rs` U28 bölümüne eklenir: tümünü dışa aktarma da asıl ve geçici `registry/` sha listesini değiştirmez; repo altına tümünü dışa aktarma reddedilir.
4. **G5 rejim metni.** A5-7: metin testi, veri dosyasından hesapla karşılaştırma.
5. **README.** `app/README.md` derleme bölümü:
   ```
   npm run tauri build -- --bundles app
   ditto src-tauri/target/release/bundle/macos/BorsAi.app /Applications/BorsAi.app
   ```
   `.dmg` notu: "Mac'te .dmg adımı bundle_dmg.sh hatasıyla düşebilir; .app yeterlidir." `docs/screens/README.md`'deki "Senaryo modu (turuncu bant)" satırı G1'e göre güncellenir.
6. **Ekran görüntüleri.** `bash app/scripts/screens.sh` ile hepsini yeniden üret. Pencere koşu boyunca öndedir, bitene kadar bekle.
   - Yeni görüntüler: kişisel kayıtlar listesinde "tümünü dışa aktar" sonucu; Ayarlar ekranı nötr bantla.
   - README tablosuna yeni satırları ekle.
   - Betik sonunda "asıl repo registry/ sha listesi öncesiyle aynı" satırı çıkmalı.
7. **Tam koşu:** `bash app/scripts/test.sh`, `bash app/tests/e2e_freeze_tmp_repo.sh`, `bash app/tests/e2e_personal_isolation.sh`, `.venv/bin/pytest -q`. Hepsi yeşil.
8. **Derleme doğrulaması:** `source app/scripts/env.sh && cd app && npm run tauri build -- --bundles app`.
   - `.app`'in üretildiğini, `.dmg` adımına girilmediğini ve G6(a) uyarı metnini raporla.
   - `/Applications`'a KOPYALAMA; bunu kullanıcı yapar.
   - Komut hata verirse tam hata metnini yaz ve README'ye çalışan biçimi koy.
9. **G6 raporu** (dosyaya dokunmadan).
10. Commit.

Bu aşama tek oturumda bitmezse:
- Yeşil ve tutarlı bir ara noktada commit at. Mesaja `(partial)` ekle.
- Kalanları raporda listele.

## Kurallar
- YALNIZ `app/` altına yaz. Tek istisna bu görev dosyası.
- `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `docs/`, `tests/` salt okunur.
- Kişinin gerçek uygulama verisine (`~/Library/Application Support/tr.borsai.app/`) yazma. Oradaki dosyaları açma; yalnız G6(c) için say.
- Ön uçta hesap yok (U25). İki terazi hiçbir yerde toplanmaz (U14). "geçiyor" dizesi yalnız `tr.ts` verdict eşlemesinde (U19).
- Mevcut testleri gevşetme. Tutmayan test varsa kök nedeni bul; gerekirse DUR ve raporla.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit:
  ```
  git add app docs/prompts/FAZ3_APP_STAGE5.md
  git commit -m "<mesaj>" -- app docs/prompts/FAZ3_APP_STAGE5.md
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Mesaj: `BORSAI_FAZ3_S5: export-all personal records, per-screen mode band (scenario/official/neutral), single model card and accuracy panel polish (SPEC_APP stage 5)`
- Rapor Türkçe.

## Teslim (rapor)
- Commit hash'i ve `git show --stat` özeti.
- Kusur 1–6 ve G1–G6 için ne yapıldı, hangi dosyada; her biri için test adı.
- A5-1…A5-7 tablosu ve U21, U23, U27, U28, U29 sonucu.
- Test sayıları ve süreleri, önce/sonra: cargo, npm (vitest), iki e2e betiği, pytest.
- Derleme sonucu: komut, süre, `.app` yolu, `.dmg` adımı, Tauri uyarı metni.
- G6 raporu (a)–(d).
- Ekran görüntüsü yolları (yeni ve yeniden üretilen); `screens.sh`'ın son iki satırı.
- Görev kapsamı dışında fark ettiğin cila notları (yapmadan, liste olarak).
- Sapmalar ve kalan işler.

## Kabul kapısı
- K1 G1: A5-1…A5-3 yeşil. Yeniden üretilen `15`, `16`, `17–24`, `25–30` görüntülerinde turuncu SENARYO bandı yok; `02–12`'de var; `01` ve `13` nötr bantlı.
- K2 G4: A5-6 ve genişletilmiş U28 yeşil; U27 bekçisi tek kod yolu.
- K3 Doğruluk paneli: çift ayraç yok; payda bölümü iki alt tablo; U25 taraması yeşil (yeni hesap yok).
- K4 G3 tek kart fonksiyonu; U21 iki ekranda. G5 metni veriyle eşleşiyor.
- K5 Tam koşu yeşil (test.sh, iki e2e, pytest); `npm run tauri build -- --bundles app` `.app` üretiyor.
- K6 Commit yalnız `app/` ve bu görev dosyası; `identifier` değişmemiş; gerçek uygulama verisine yazılmamış.

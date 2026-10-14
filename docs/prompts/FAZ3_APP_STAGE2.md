# TASK_ID: BORSAI_FAZ3_APP_STAGE2_20260922

Model: Opus 5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ: yalnız npm/crates (gerekirse). push/tag/amend yok.

## Bağlam
- Aşama 0 (50c62da) ve aşama 1 (0b67f5d) tamam.
  - `borsai_predict` 16/16 modelde Python ile eşleşiyor; maks |Δ| 1.1e-13.
  - Koşullu parite U37 geçiyor.
- Bu görev `docs/app/SPEC_APP.md` §7'deki **aşama 2: Ekranlar**. Kapsam:
  - girdi formu (§3a)
  - sonuç ekranı (§3b)
  - senaryo modu (§3c)
  - ayarlar ve hakkında
  - f6 repo modu / elle giriş
  - koşullu tavan şeridi ve eğrisi (§3g, EK 1)
  - U-testleri: U7–U11, U36, U40 (U37 zaten yeşil)
- Model kümesi hâlâ sabit 16 model (`PINNED_MODEL_IDS`).
  - Faz 4 `ceiling_path` modelleri dondurulunca ayrı bir görevle eklenecek.
  - §3g'deki "getiri (koşullu)" sekmesi şimdilik "henüz yok" gösterir.
- Paralel oturum: Fable, Faz 4 denetimi. Yalnız `docs/fable_faz4_audit/` altına yazıyor, commit atmıyor.

ÖNCE OKU:
- CLAUDE.md
- docs/app/SPEC_APP.md: §1, §2, §3a–§3c, §3g, §4, §5 (U7–U11, U36, U40), §7
- app/README.md
- app/ kodu

## Adımlar
1. Ekranlar ve Rust komutları (§3a–§3c, §3g): şartnamedeki alanlar, durumlar, boş ve hata hâlleri.
   - Ön uç hesap yapmaz. Bütün sayılar Rust komutlarından gelir. Koşullu değerler `borsai_predict::survival::conditional`'dan.
2. f6: repo modunda Python `borsai.market20` çağrısı (salt okuma, §1.1); ya da elle giriş, etiketli. Ağ yok.
3. Senaryo kaydetme ve yükleme: `borsai.app_scenario/1`, uygulama verisinde. U36: farklı INDEX sha'sıyla kaydedilmiş senaryo.
4. §3g şeridi:
   - Gözlenen seri `data/outcomes/<T>.csv`'den okunur, salt okuma.
   - Kullanıcı beyanı yalnız uygulama verisinde tutulur.
   - U40 sentetik fixture'larla.
5. Testler: `bash app/scripts/test.sh` tam koşu yeşil.
6. Ekran görüntüleri: `npm run tauri dev` ile VEYAS girdileri (U7: 4 RET + 12 dolu) ve bir senaryo. `app/docs/screens/` altına.
7. Commit. Mesaj: `BORSAI_FAZ3_S2: input form, results, scenario mode and conditional ceiling strip (SPEC_APP stage 2)`

Bu aşama tek oturumda bitmezse:
- Yeşil ve tutarlı bir ara noktada commit at. Mesaja `(partial)` ekle.
- Kalanları raporda listele.

## Kurallar
- YALNIZ `app/` altına yaz. Tek istisna bu görev dosyası.
- Commit:
  ```
  git add app docs/prompts/FAZ3_APP_STAGE2.md
  git commit -m "<mesaj>" -- app docs/prompts/FAZ3_APP_STAGE2.md
  ```
  - `git add -A` yok.
  - `index.lock` hatasında 10 saniye bekle ve yeniden dene; kilidi silme.
- `data/`, `registry/`, `scores/` yalnız okunur. Uygulama hiçbir koşulda bunlara yazmaz. U39 ruhu burada da geçerli.
- Model davranışı Python'daki gibidir: f3 yokken tahmin uydurulmaz, kırpma ve ret kuralları aynı.
- Arayüz Türkçe; SPEC_APP §4 dil kuralları.
- Rapor Türkçe.

## Teslim (rapor)
- Commit hash'i ve `git show --stat` özeti.
- U-testleri tablosu.
- Ekran görüntülerinin yolları.
- Proje sahibinin uygulamayı açması için komut: `bash app/scripts/dev.sh`.
- Kalan işler.
- Sapmalar.

## Kabul kapısı
- K1 U7–U11, U36, U40 yeşil; aşama 0–1 testleri yeşil kalıyor.
- K2 Ön uçta hesap yok (U25 statik tarama kalıbıyla denetle).
- K3 Commit yalnız `app/` ve bu görev dosyası.

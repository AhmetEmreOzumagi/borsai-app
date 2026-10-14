# TASK_ID: BORSAI_FAZ7_FABLE_APP_EK3_SPEC_20260927

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi. Ağ yok. push/tag/amend yok.

## Rol
**SPEC_APP EK 3**'ü yazarsın: `docs/app/SPEC_APP_EK3.md`. Birikmiş bütün model ve gösterim işlerini uygulamaya taşıyan ek şartname. Uygulayıcı Opus olacak (ayrı görev, aşamalı). Belge, sormadan kodlanabilecek kadar kesin olmalı. EK 2'nin kalıbı: Rust portu, parite ve altın vektörler, gösterim, U-testleri, önceden yazılmış beklenti.

## Bağlam
- **Uygulama bugün (`ecd8973` sonrası):**
  - `models/INDEX.json` 23 giriş.
  - Uygulama ilk 19'u gömüyor; son 4'ü (`ceiling_hazard_v1_clip`, `_real`, `_pooled`, `_pooled@INF`) `ignored_model_ids`.
  - Kayıt karşılaştırmasında v1 hücreleri "desteklenmiyor" sayılıyor (`docs/faz7/FREEZE_RAPOR.md` "Uygulama etkisi"; SPEC_DEVIATIONS J31).
- **Birikmiş işler (hepsi bu ekte):**
  - **A. `ceiling_hazard_v1` ailesi (dondu, `66adbca`):**
    - Rust portu: f1r (TÜFE ile reel büyüklük), genel kırpma, rejim bloğu, yeni ret kodları.
    - TÜFE tablosunun uygulamaya gömülmesi ve aylık ekleme.
    - Altın vektörler 19 → 23.
    - Kaynak: `docs/specs_faz7/SPEC_HAZARD_V1.md` §3, §8, §9; `docs/faz7/IMPL_RAPOR.md` §14; `docs/fable_faz7_audit/AUDIT.md` §8.
  - **B. `post_d1_hazard_v0` (dondu, `models/INDEX_POST_D1.json`):** SPEC_POST_D1_V0 "EK 3 gerekir" diyor:
    - "D1 sonrası" satırı koşullu sekmede;
    - D1 sonrası kayıt akışı (komut bloğu; uygulama bülten indirmez);
    - Rust `predict_post_d1`, altın vektörler.
  - **C. `fall_d10_v0` ailesi ("düşen arz", şartname `docs/specs_faz7_c/SPEC_C_V0.md` + `KARARLAR_C.md`):**
    - henüz dondurulmadı; kodu paralel bir Opus oturumunda yazılıyor;
    - Rust portu, "Düşüş (D10)" kartı (SPEC_C_V0 §9; oradaki "EK4" bu eke katıldı);
    - uygulaması (C) dondurulunca açılan ayrı aşama olur.
  - **D. Proje sahibinin isteği: "kaç gün tavan" tahmini daha görünür olsun.** Bugün tavan serisi Sonuç sayfasının ortasında (Grup B) tablo ve eğri olarak duruyor; sayfa yoğun. Sonuç sayfasının başında bir **"Tavan serisi" özet kartı** tasarla. İçeriği:
    - öne çıkan modelin beklenen ve medyan seri uzunluğu;
    - P(en az 3 gün), P(en az 5 gün), P(10 gün);
    - en olası bozulma günü;
    - "yarın bozulur mu" (koşullu, j > 0'da);
    - yan yana adaylar ve etiketleri.
    
    Öne çıkarma kuralı SPEC_HAZARD_V1 §5.5 ve KARARLAR K4: kasa açılana kadar `ceiling_hazard_v0` öne çıkar, v1 adayları yakın dönem etiketiyle ("tolerans içinde" / "bozuyor") ve "kasa: bekliyor" satırıyla yanında.
  - **E. Doğruluk sekmesinde "Zaman-dışı (eski kohort)" paneli:**
    - kaynaklar `scores/scores_oot.json`, `docs/SCORES_OOT.md`;
    - üçüncü terazi, asla toplanmaz;
    - kasa açılınca `oot_pre_h99_sealed` satırları için yer.
- **Terazi dili (aynen):**
  - "Geçmiş veri testi (retrospektif, tasarıma maruz)";
  - "Zaman-dışı test (eski kohort)";
  - "Canlı sicil (prospektif)".
  
  Ayrı renk, toplanmaz. "Geçiyor" yalnız SPEC_SCORING §8 koşuluyla. Yasak sözcükler SPEC_APP §4 aynen.
- **Hijyen:** kasa (SEALED) üyelerinin dosyası açılmaz; `scores_oot.json` yalnız açık küme satırlarını taşır. Hangi kodun kasada olduğu yazılmaz. Altın vektörlere kasa üyelerinin girdileri girmez.

## Paralel
Bir Opus oturumu `docs/prompts/FAZ7_C_IMPL.md`'yi koşuyor: `borsai/`, `tests/`, `docs/faz7c/`, `docs/MODELS.md`, `docs/SPEC_DEVIATIONS.md`, `experiments/`. Onun dosyalarına dokunma. Senin commit'in yalnız `docs/app/SPEC_APP_EK3.md` (+ gerekirse `docs/app/ekler/ek3_*`) ve bu görev dosyası. (C) için Python referansı henüz yoksa şartnameden (SPEC_C_V0 §2.3, §3, §8, §9) yaz ve "referans: (C) dondurmasından sonra doğrulanır" diye işaretle.

ÖNCE OKU:
- CLAUDE.md
- docs/app/SPEC_APP.md (tamamı), docs/app/SPEC_APP_EK2.md (kalıp)
- docs/specs_faz7/SPEC_HAZARD_V1.md §3, §8, §9; docs/faz7/IMPL_RAPOR.md §14; docs/fable_faz7_audit/AUDIT.md §8; docs/faz7/FREEZE_RAPOR.md; docs/SPEC_DEVIATIONS.md J (J23–J31)
- docs/specs_faz5/SPEC_POST_D1_V0.md (EK 3 ile ilgili bütün satırlar), docs/SPEC_DEVIATIONS.md H
- docs/specs_faz7_c/SPEC_C_V0.md §2.3, §3, §8, §9; KARARLAR_C.md
- borsai/predict_hazard.py, tufe.py, predict_post_d1.py, freeze.py (kayda ne yazıldığı), scoring.py (Faz 7 ve oot blokları)
- models/INDEX.json, INDEX_POST_D1.json; `models/ceiling_hazard_v1_pooled.json` ve `models/post_d1_hazard_v0.json`'ın üst düzey anahtarları
- data/raw/tuik/tufe_genel_2025_100.csv (yapı), borsai/specs.py `TUFE_PIN`, data/raw/tuik/build_tufe_csv.py (`--append-month`)
- app/parity/gen_golden.py, app/parity/golden/MANIFEST.json, app/src-tauri/build_embed.rs, app/src-tauri/crates/borsai_predict/src/ (özellikle `params.rs`, `hazard.rs`, `features.rs`, `dec.rs`, `output.rs`), app/src-tauri/src/commands/ (freeze, parity, models), app/src/ (Sonuç ve Doğruluk ekranları, i18n/tr.ts)
- scores/scores_oot.json yapısı, docs/SCORES_OOT.md

## Belge neyi karara bağlamalı
1. **Aşamalar ve sıra.** Önerilen sıra:
   - P1 = A + D (v1 portu ve Tavan serisi kartı);
   - P2 = B (D1 sonrası);
   - P3 = E (zaman-dışı panel);
   - P4 = C ((C) portu ve Düşüş kartı; (C) dondurulunca).
   
   Her aşama için dokunulacak dosyalar, U-testleri, altın vektör ekleri ve oturum tahmini. Aşamalar birbirinden bağımsız commit'lenebilmeli.
2. **v1 Rust portu (A).**
   - Params şeması: `family`, `variant`, `features`, `preprocessing.winsor` üç sütun, `log`, `deflator`, `regime`.
   - f1r aritmetiği: Decimal 60 hane, ROUND_HALF_EVEN, iki işlem sırası Python ile aynı; sonra binary64 ve ln.
   - η toplama sırası; genel kırpma bayrağı ve uyarısı; yeni çıktı alanları; ret kodlarının birebirliği.
   - Karşılaştırma toleransları önceden yazılı (EK 2 §3.3 kalıbı).
3. **TÜFE uygulamada.**
   - Bağımsız modda gömülü tablo (önek pini denetimiyle; `tufe.index_for` karşılığı: m − 2 ve `release_date < T`).
   - Repo modunda repodaki dosya.
   - Uygulama yeniden derlenmeden yeni ay nasıl görünür? Kullanıcıya ne söylenir? Ay eksikse arayüz ne yapar ("TÜFE ayı yok → real/pooled RET; kayıt ön koşulu durur")?
   - Kayıtlı tahminlerde `model_inputs.tufe_index` kullanılır.
4. **Altın vektörler.**
   - `PINNED_MODEL_IDS` 19 → 23 (A), post_d1 (B), sonra 27 (C).
   - `bit_equal_floor.json` tabanları.
   - U46: 16 eski dosya bayt-eşit kalır; yeni girdi satırları yalnız yeni modellere bağlanır (Faz 4 kalıbı).
   - Önerilen girdi satırları: H99 + `tufe_index`, açık küme + `alloc_regime`, canlı (anahtarsız), uç durumlar.
   - Kasa girdisi yok.
   - Parite ve "desteklenmiyor" durumunun kalkması; `build_embed` `ignored_model_ids` beklentisi.
5. **"Tavan serisi" özet kartı (D).**
   - Yer, içerik, sözcükler, öne çıkarma kuralı, adayların sırası ve etiketleri, terazi satırları.
   - Koşullu (j) durumda nasıl değiştiği.
   - Mobil olmayan masaüstü genişliği; mevcut Grup B tablosuyla ilişki (kart özet, tablo ayrıntı).
   - Bir ekran taslağı: metin tel kafes yeterli.
   - "Yatırım tavsiyesi değildir" ve senaryo filigranı aynen.
6. **D1 sonrası (B):** SPEC_POST_D1_V0'ın EK 3 maddeleri aynen. Resmi j yalnız gözlenen seri dosyasından; D1 sonrası kayıt akışının komut bloğu; gösterim kuralları.
7. **Zaman-dışı panel (E):**
   - hangi hücreler; hüküm dili "(zaman-dışı terazide)";
   - n ve blok sayıları; RETRO satırlarının bilgi olarak gösterimi;
   - kasa açılınca eklenecek satırların yeri; kasa açılmadan "kasa: kapalı".
8. **(C) portu ve Düşüş kartı (C):**
   - SPEC_C_V0 §2.3 JSON alanları, ek satış bayrağı, ln f3 ve f1r, `@ZERO` sabit başlık, retler;
   - SPEC_C_V0 §9 metinleri;
   - §5.5 kart seçim kuralı (kasa sonrası; öncesinde "kasa: bekliyor").
9. **Metinler:** `i18n/tr.ts` için yeni anahtarlar, Türkçe ve kısa. Proje sahibinin gördüğü ekranın sadeleşmesi öncelikli: yeni kartlar özet verir, ayrıntı katlanır.
10. **ÖNCEDEN YAZILMIŞ BEKLENTİ:** aşama başına oturum sayısı, beklenen test sayısı artışı, riskli noktalar.
11. **Açık sorular** (en çok 5, her birine önerin; proje sahibi adına orkestratör cevaplar).

## Kurallar
- Yazılabilir: yalnız `docs/app/SPEC_APP_EK3.md`, `docs/app/ekler/ek3_*` ve bu görev dosyası. Geri kalan her şey salt okunur. Kod yazılmaz.
- Ölçtüğün her şeyi [ÖLÇTÜM], çıkarımı [ÇIKARIM], kararı [KARAR] diye işaretle (EK 2 kalıbı).
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- Türkçe.
- `git add -A` yok. Commit:
  ```
  git add docs/app/SPEC_APP_EK3.md docs/app/ekler docs/prompts/FAZ7_FABLE_APP_EK3_SPEC.md
  git commit -m "BORSAI_APP_EK3_SPEC: app addendum 3 (ceiling hazard v1 port and CPI table, ceiling-streak summary card, post-D1 row and flow, out-of-time panel, falling-IPO card)" -- docs/app/SPEC_APP_EK3.md docs/app/ekler docs/prompts/FAZ7_FABLE_APP_EK3_SPEC.md
  ```
  `docs/app/ekler`'de değişiklik yoksa o yolu çıkar. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.

## Teslim (rapor)
- Commit hash'i.
- Aşama tablosu (dosyalar, U-testleri, altın vektör ekleri, oturum tahmini).
- Tavan serisi kartının tel kafesi.
- Açık sorular.

## Kabul kapısı
- **K1** A–E'nin her biri kodlanabilir kesinlikte (şema, aritmetik, ret kodları, toleranslar, metinler).
- **K2** Altın vektör planı U46'yı koruyor; kasa girdisi yok.
- **K3** Tavan serisi kartı proje sahibinin isteğini karşılıyor ve terazi dilini koruyor.
- **K4** Commit yalnız izinli yollarda.

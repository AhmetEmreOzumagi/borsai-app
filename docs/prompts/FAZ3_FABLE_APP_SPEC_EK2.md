# TASK_ID: BORSAI_FAZ3_FABLE_APP_SPEC_EK2_20260922

Model: Fable · yüksek. Klasör: ~/Desktop/BorsAi. Ağ gerekmez. push/tag/amend yok.

## Bağlam
- Faz 4'ün üç modeli dondu (a0df5b7): `ceiling_path_v0`, `ceiling_path_v0@INF`, `pb_ceiling_path_v0`. `models/INDEX.json` 19 model.
- Uygulama (`app/`) ilk 16 modeli gömüyor.
  - `app/src-tauri/build_embed.rs` içinde `PINNED_MODEL_IDS` var; son 3 model `ignored_model_ids` olarak atlanıyor.
  - Rust `borsai_predict` bu türü (`predict_path`) bilmiyor.
- SPEC_APP bu anı önceden işaretledi:
  - §8-3: "şema bu belgeye §2.1/§2.3 eklemesiyle girer, altın vektörler genişletilir"
  - §3g: "getiri (koşullu)" sekmesi için yer ayrıldı
- Bu görev o eki yazar: **SPEC_APP EK 2 — Faz 4 tavan-yolu modelleri uygulamada.**
  - Uygulayıcı Opus olacak (ayrı görev). Belge, sormadan kodlanabilecek kadar kesin olmalı.
- Python referansı hazır, yeni model tanımı yok:
  - `borsai/predict_path.py` (`predict`, `limit_path`, `mixture_atoms`, `summarize`, `conditional`, `conditional_after_break`, `conditional_weights`)
  - `docs/specs_faz4/SPEC_CEILING_PATH_V0.md` §4 ve §7
- Paralel oturum: Opus, `app/` altında aşama 3'ü (dondur akışı) kodluyor. O görevin parite adımı "desteklenen model" kümesini gömülü veriden okuyacak; port gelince 19/19 olmalı. Kendi görev dosyası `docs/prompts/FAZ3_APP_STAGE3.md`.

ÖNCE OKU:
- CLAUDE.md
- docs/app/SPEC_APP.md (tamamı; özellikle §1.2–§1.4, §2.1, §2.3, §3b, §3g, §5.1, §5.6, §7, §8)
- docs/specs_faz4/SPEC_CEILING_PATH_V0.md (tamamı)
- borsai/predict_path.py, borsai/survival.py, borsai/freeze.py (kayda ne yazıldığı), borsai/scoring.py (Faz 4 modelleri nasıl görünüyor)
- models/INDEX.json; `models/ceiling_path_v0.json`'ın üst düzey anahtarları (dosya büyük, parça parça oku)
- app/parity/gen_golden.py, app/parity/golden/MANIFEST.json, app/src-tauri/build_embed.rs, app/src-tauri/crates/borsai_predict/src/ (özellikle `dec.rs`, `survival.rs`, `output.rs`, `lib.rs`)
- scores/scores.json'da üç yeni modelin blokları ve `retro_info`
- data/outcomes/ dosyalarının YALNIZ başlık satırı (sütun adları; §7 koşullu karışımı gözlenen kapanışı kullanır)

## Belge neyi karara bağlamalı
1. **§2.1 eki:** Rust'ın okuyacağı model JSON alanları. `survival_model` gömülü kopyası ve sha denetimi (INDEX'teki seri modeli sha'sıyla ilişki). Bilinmeyen alan kuralı.
2. **Rust portu:**
   - Decimal gerektiren kısım: fiyat adımı tablosu, `FLOOR_TO_TICK_AT_LIMIT_LEVEL`, `HALF_UP_TO_TICK`, `C` dizisi metin olarak. Mevcut `dec.rs` yeterli mi, [ÖLÇTÜM] ile.
   - Atom sırası ve kuantil kuralının bit-eşitliği.
   - binary64 adımları.
   - Ret ve uyarı kodlarının birebirliği (`F3_MISSING` mirası, `POST_BREAK_INSUFFICIENT`).
3. **Parite ve altın vektörler:**
   - `gen_golden.py`'nin 19 modele genişlemesi. Model başına ≥ 200 girdi: fiyat adımı sınırları, S_h ≥ 0.5 / < 0.5 geçişleri, havuzlama merdiveni, f3 yok, PB varyantı.
   - Koşullu karışım için j = 0..9 ve kırılma sonrası t durumları. Referans `predict_path.conditional` / `conditional_after_break`.
   - Tolerans ÖNCEDEN yazılır: hangi alan bit-eşit, hangisi |Δ| ≤ 1e-9, metin alanları birebir.
   - `PINNED_MODEL_IDS` 16 → 19 ve sıra kuralı. Altın dosyaları mevcut 16 modelde bayt olarak değişmemeli (ya da değişecekse neden).
4. **Gösterim (§3b ve §3g eki):**
   - Sonuç ekranında h = 1..10 için medyan, %10–%90, p_up, S_h, limit yolu fiyatı.
   - D1/D3/D5/D10 sütunlarının diğer modellerle yan yana nasıl duracağı. Senaryo modu.
   - "getiri (koşullu)" sekmesi: durum 1 (seri j gün sürüyor) ve durum 2 (t'de kırıldı). Gözlenen kapanış kaynağı. `limit_path_mismatch` gösterimi.
   - Resmi görünümde yalnız kayıttaki değerler kullanılır (U38 ile aynı ilke).
5. **§2.3 eki:** `scores.json`'da Faz 4 modellerinin nasıl okunacağı (RETRO, `retro_info`) ve ileride gelecek `models[].conditional` bloğu.
6. **Aşama ve kabul testleri:**
   - Yeni U-testleri (U41…), kanıtlanabilir.
   - Hangi aşamaya girdiği ve tahmini oturum sayısı.
   - Aşama 3'ün parite adımıyla bağlantısı (port sonrası 19/19).
7. **Önceden yazılmış beklenti:**
   - parite toleransları
   - altın satır sayısı
   - VEYAS girdileriyle hangi Faz 4 modelinin RET edeceği (şimdi yaz; uygulayıcı rapor ederken karşılaştırır)

İşaretler SPEC_APP'teki gibi: [ÖLÇTÜM], [ÇIKARIM], [KARAR]. Her [KARAR] tek cümle gerekçe taşır.

## Kurallar
- YALNIZ yaz: `docs/app/SPEC_APP_EK2.md` ve gerekirse `docs/app/ekler_ek2/`.
- `docs/app/SPEC_APP.md`'yi DEĞİŞTİRME. Paralel oturum onu okuyor. Ek, bölüm numaralarıyla ona atıf yapar.
- `app/`, `borsai/`, `models/`, `registry/`, `data/`, `scores/`, `docs/specs/`, `docs/specs_faz4/`, `tests/` salt okunur.
- Model fit etme. Backtest koşma. Sonuç verisinden yalnız sütun adlarını oku.
- Python'da bir eksik bulursan (örneğin referans fonksiyon yok ya da kayıtta gereken alan yok) kendin düzeltme. Belgeye "ön koşul görevi" olarak yaz: ne, neden, hangi dosya.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma (`tests/test_outcome_guard.py`).
- Commit öncesi: `.venv/bin/pytest -q tests/test_outcome_guard.py tests/test_faz1b_guardrails.py` yeşil.
- Commit (paralel oturum var, yalnız kendi yolların):
  ```
  git add docs/app/SPEC_APP_EK2.md docs/prompts/FAZ3_FABLE_APP_SPEC_EK2.md
  git commit -m "<mesaj>" -- docs/app/SPEC_APP_EK2.md docs/prompts/FAZ3_FABLE_APP_SPEC_EK2.md
  ```
  - `ekler_ek2/` yazdıysan iki satıra da ekle.
  - `git add -A` yok.
  - `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Mesaj: `BORSAI_FAZ3_EK2: SPEC_APP addendum for Faz 4 ceiling path models (fields, Rust port, parity, display)`
- Rapor Türkçe.

## Teslim (rapor)
- Commit hash'i ve `git show --stat`.
- Belgenin 10 satırlık özeti.
- [KARAR] listesi.
- Ön koşul görevleri (varsa).
- Açık sorular (en çok 5), her birine önerinle.
- Uygulayıcı için tahmini oturum sayısı.

## Kabul kapısı
- K1 Yukarıdaki 7 başlığın her biri karara bağlanmış; tolerans ve beklentiler sayısal.
- K2 Her U-testi bir komut ya da dosyayla kanıtlanabilir.
- K3 SPEC_APP.md ve salt okunur dizinler değişmemiş. Commit yalnız izinli yollar.
- K4 İki bekçi testi yeşil.

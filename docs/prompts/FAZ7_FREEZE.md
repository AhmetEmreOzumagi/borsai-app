# TASK_ID: BORSAI_FAZ7_FREEZE_20260927

Model: Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ gerekmez. push/tag/amend yok.

## Bağlam
- `ceiling_hazard_v1` ailesi uygulandı ve backtest edildi, dondurulmadı:
  - A `2a21a96`, B `70b67d1`, R `f5d7609`;
  - görev `docs/prompts/FAZ7_HAZARD_V1_IMPL.md`, rapor `docs/faz7/IMPL_RAPOR.md` (özellikle §14 "Dondurma görevi için notlar").
- Fable'ın bağımsız yeniden üretimi ve denetimi: `docs/fable_faz7_audit/AUDIT.md` (`eda9732`). Hüküm dört model için de **FREEZE_OK**:
  - ledger'lar durum ve λ'da birebir, sayılarda maks |Δ| 4.3e-11;
  - sızıntı yok; 21 mutasyonun 19'u kırmızı.
- Yakın dönem etiketleri: clip "tolerans içinde", real ve pooled "bozuyor". Şartname §6.4 gereği **dördü de dondurulur**: `ceiling_hazard_v1_clip`, `_real`, `_pooled`, `_pooled@INF`. real ve pooled §5.5 k3 ile uygulama birincili olamaz.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Bu görevde model davranışı değişmez. Denetim bulguları B1–B3 ve B7 aynı model_id sınıfındadır.
- Bu görev, sonuçları gören uygulayıcıdan farklı bir oturumdur (bağımsız el).

### Orkestratör kararları (proje sahibi adına, bağlayıcı)
- **B4 (J10 dışlaması):** kural değişmez; davranışı SPEC_DEVIATIONS J10'a belgelenir. Etkisi +0.0289 → +0.0279; kuralın değişmesi yeni kimlik olurdu ve fayda yok.
- **MODELS.md Faz 7 dondurma notu için `report_faz7.py` değişikliği onaylı.** Faz 5 kalıbı: var olan bölümlerin geri kalanı değişmez.
- **Skorlar yeniden üretilmez.** `scores/`, `docs/SCORES.md` değişmez; J16 istisnaları geçerli kalır.
- **Eski kohort ikinci kayıtları (`--only-missing-models`), model başına kapı ve `oot_pre_h99_sealed/_all` bu görevde YOK;** sıradaki görev yapacak. B7 bekçisi bu görevde `build_record`'a girer.
- **Uygulama (Rust) bu görevde YOK;** `app/` salt okunur. Ayrı görev (EK3) v1 desteğini ve "Tavan serisi" kartını ekleyecek.

### Bilinen iki tuzak
- **Sıra bekçisi:** `scoring.sequence_violations` INDEX'teki her model dosyasının commit'li olmasını ister. Model dosyaları commit edilmeden tam test sıra bekçisinde KIRMIZIdır; bu doğru davranıştır. Bu yüzden F1 yalnız model dosyaları + INDEX'tir ve tam test F1'den sonra koşar (Faz 5 kalıbı).
- **`borsai_dirty`:** `code_version()` yalnız `borsai/`'yi izler. Kod değişiklikleri (K commit'i) dondurmadan ÖNCE ayrı commit'te olmalı; dondurma temiz ağaçta koşar (IMPL_RAPOR §14).

### Paralel
- Bir Fable oturumu `docs/prompts/FAZ7_FABLE_C_SPEC.md`'yi koşuyor. Yalnız `docs/specs_faz7_c/` altına ve kendi görev dosyasına yazar, kendi yollarıyla commit atar.
- Bunlar izinli izlenmeyen sayılır: onlara dokunma, commit'lerine alma. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.

ÖNCE OKU:
- CLAUDE.md
- docs/fable_faz7_audit/AUDIT.md (§0, §4, §5, §7, §8)
- docs/faz7/IMPL_RAPOR.md (§9, §10, §14)
- docs/specs_faz7/SPEC_HAZARD_V1.md §3.1–§3.3, §7.1, §8, §9, §11
- docs/SPEC_DEVIATIONS.md J
- docs/prompts/FAZ5_FREEZE.md (kalıp)
- borsai/freeze.py (`freeze`, `build_record`, `main`), borsai/backtest.py (`final_fit_v1`), borsai/hazard.py (`TrainingResult.predict`), borsai/tufe.py, borsai/predict_hazard.py, borsai/report_faz7.py, borsai/specs.py (`FAZ7_MODEL_IDS`, `TUFE_PIN`)
- data/raw/tuik/build_tufe_csv.py, docs/PROVENANCE.md §11
- tests/test_faz7_*.py, tests/faz7_support.py, tests/test_experiment_log.py
- app/src-tauri/build_embed.rs (INDEX'te sabit listenin dışındaki kayıtlar `ignored_model_ids`), app/src-tauri/src/commands/freeze.rs ve parity.rs (`compare_record`): yalnız OKU.

## Adımlar
0. **Taban**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -4`: HEAD `eda9732` ya da torunu. `git status --porcelain`.
   - İzinli izlenmeyen: bu görev dosyası, `docs/prompts/FAZ7_FABLE_C_SPEC.md`, `docs/specs_faz7_c/**`. Başka bir şey varsa DUR.
   - Tam `.venv/bin/pytest -q`, `bash app/scripts/test.sh`, `gen_golden --check` (25/0). Kırmızı varsa DUR.
   - Sayılar `docs/faz7/ekler/freeze_test_runs.txt`'ye.

1. **K: kod ve belge düzeltmeleri** (model davranışı değişmez)
   - **K1 · B1:** `hazard.TrainingResult.predict`'te `clipped = bool(clipped_features)` (şartname §3.1: herhangi bir sütun).
     - Faz 7 altın ledger'larını yeniden üret. **Yalnız `test_clipped` sütunu değişmeli.** Kanıt: dosya başına sütun sütun karşılaştırma; diğer bütün sütunlar metin olarak aynı. Karşılaştırmayı `docs/fable_faz7_audit/ekler/repro_ledgers/` ile de yap.
     - Beklenen herhangi-sütun sayıları: clip 35, real 36, pooled 23.
     - MANIFEST ve SHA256SUMS yenilenir.
     - Günlük: eski satırlar değişmez. Yeni satır gerekiyorsa sona eklenir, `context` B1'i söyler. `faz7_variants` sayımı değişmemeli (test).
     - MODELS.md Faz 7 fold özeti yeniden render edilir: 35/36/23; yalnız f3 sayısı (20/20/7) ayrıca yazılabilir.
     - Nihai fit önizlemeleri değişmemeli (B1 onlara dokunmaz); değişirse DUR.
   - **K2 · B2:** `test_faz7_tufe.py`'ye `release_date == T → TUFE_NOT_PIT` sentetik satırı. Önce mutasyon c2'nin (`release_date ≤ T` kabul) bu testte kırmızı olduğunu göster (geçici değişiklik, geri al), sonra ekle.
   - **K3 · B3:**
     - `assert bt.NEAR_ERA_TOLERANCE == 0.010` (ya da sabitin adı neyse);
     - sentinel `[−0.02, +0.012] → belirsiz`;
     - `OPERATIONAL_RULES_FAZ7` metnindeki eşik sabitten üretilir. Render edilen MODELS.md metni bayt-eşit kalmalı.
     - Mutasyon j'nin (eşik +0.015) artık kırmızı olduğunu göster.
   - **K4 · dondurma kodu:**
     - `freeze.py` v1 kimliklerini `backtest.final_fit_v1`'e yönlendirir. Kod yolu aynı kalır; fonksiyon taşınırsa önizlemelerle bit-eşitlik testi zaten var.
     - `build_record`:
       - `tufe` bloğu (market20 kalıbı) ve `model_inputs["tufe_index"]` (`tufe.index_for(T)`, `release_date < T` bekçisi dahil);
       - `model_inputs["alloc_regime"]` **yalnız** `record_stage == OOT_PRE_LISTING` kayıtlarında (canlıda anahtar yok → r = `live_value` = 0; J6).
     - **Kayıt ön koşulu (şartname §9):** canlı kayıtta TÜFE ayı (m − 2) dosyada yoksa kayıt YAZILMADAN durur. Hata, eksik ayı ve aylık ekleme komutunu söyler. Sentetik test.
     - **B7 bekçisi:** `OOT_PRE_LISTING` kaydında rejimli model varken `alloc_regime` yoksa kayıt yazılmaz. Sentetik test.
   - **K5 · TÜFE aylık ekleme yolu:**
     - `build_tufe_csv.py` (ya da `borsai.tufe`) yeni bir ayı dosyanın sonuna bir satır olarak ekleyen, belgelenmiş bir komut sunmalı. Girdiler: bülten sayısı ve yayım tarihi, indirilen tablonun url/sha'sı.
     - Eski satırlar bayt-eşit kalır; önek pini (`TUFE_PIN`) tutar.
     - Var olan yol yeterliyse yalnız belgele ve sentetik testle göster; değilse ekle.
     - **Bu görevde gerçek ay EKLENMEZ, ağ yok.** Komut PROVENANCE §11'e ve rapora yazılır. İlk gerçek ekleme Eylül 2026 TÜFE'si olacak; Kasım'da listelenecek arzlar için gerekli.
   - **K6 · belgeler (SPEC_DEVIATIONS J; şartname değişmez):**
     - J10'a B4: filtre modunun 2023-09…2025-01 arasında UNFILTERED ↔ NOT_SPECIFIED salınımı, dışlamalı 44 fold (25'i yakın dönemde), nihai fit'te dışlama yok, etki +0.0289 → +0.0279, orkestratör kararı "kural değişmez".
     - B5: ikincil Brier hücrelerinin karşılaştırıcısı v0.
     - B6: J16'nın test listesine beşinci test.
     - B8: λ = 10 ızgaranın iç noktası; IMPL görev metnindeki "üst uç" ifadesi yanlıştı.
     - B9: bilgi notu.
     - Yeni satırlar J23+ olarak.
   - **K7:** `experiments/log.jsonl`'a Fable'ın 4 duyarlılık satırı (`docs/fable_faz7_audit/ekler/sensitivity_runs.jsonl`, `kind: sensitivity`, model değil). Faz 5 kalıbı; `test_experiment_log.py` bu türü zaten kabul ediyor olmalı.
   - Tam pytest + test.sh + `gen_golden --check` yeşil → **commit K**.

2. **F1: dondurma** (temiz ağaç, `borsai_dirty = false`)
   - `.venv/bin/python -m borsai.freeze --models ceiling_hazard_v1_clip ceiling_hazard_v1_real ceiling_hazard_v1_pooled ceiling_hazard_v1_pooled@INF`
   - Beklenen:
     - 4 yeni model JSON'u;
     - `models/INDEX.json` sonuna 4 giriş (`FAZ7_MODEL_IDS` sırası); ilk 19 giriş metin olarak aynı;
     - 19 eski model dosyası, `post_d1_hazard_v0.json` ve `INDEX_POST_D1.json` bayt-eşit;
     - `spec_document_sha256` = `25229cea8f6f…` (tam değer şartname dosyasının sha'sı).
   - Donmuş JSON ↔ `tests/reference/macos_golden_faz7/<model>_final_fit_preview.json`: `created_at`, `code_version`, `runtime` dışında `==`. Değilse DONDURMA DOSYALARINI COMMIT ETME, DUR ve raporla.
   - Hızlı kontrol: `.venv/bin/pytest -q tests/test_faz7_golden.py tests/test_faz7_model.py` yeşil.
   - **Commit F1** (yalnız 4 model dosyası + INDEX.json).

3. **Tam test F1'den sonra.** Yeşil olmalı: `test_outcome_guard.py` (sıra bekçisi), `test_models.py`, Faz 1B/4/5 bekçileri. Kırmızıysa DUR ve raporla; F1'i geri alma, amend yapma.

4. **F2: donmuş model testleri ve belgeler**
   - Donmuş JSON'larla `predict_hazard` (stdlib), her modelin eğitim arzlarında numpy nihai fit'e |Δ| ≤ 1e-12. Ayrıca şunlar sınanır:
     - `@INF` (özelliksiz);
     - rejim yolu: canlı r = 0, OOT girdisiyle r = etiket;
     - TÜFE yolu: `tufe_index` ile real ve pooled.
     - INDEX şeması, 23 giriş, sha'lar; `INDEX_POST_D1.json` değişmedi.
   - **Uygulama etkisi (yalnız ölç, `app/` değişmez):**
     - `bash app/scripts/test.sh` yeşil mi? Beklenen: `build_embed` 4 kaydı `ignored_model_ids`'e alır.
     - `gen_golden --check` 25/0.
     - Uygulamanın "dondur" akışı yeni INDEX'le ne yapar? Kaynakta ölç ve raporla:
       - gömülü INDEX sha'sı, uygulama yeniden derlenmeden `INDEX_SHA` ön koşulunda durur;
       - yeniden derlenince `compare_record` v1 modellerini içeren bir kaydı nasıl karşılaştırır.
     - Bu, EK3 görevinin girdisidir. Çözmeye çalışma.
   - **MODELS.md** (`python -m borsai.report`; onaylı `report_faz7.py` değişikliği). Faz 7 bölümüne dondurma notu:
     - tarih ve donmuş dosya sha'ları;
     - bağımsız yeniden üretim 2026-09-26, maks |Δ| 4.3e-11, `docs/fable_faz7_audit/`;
     - "kasa: bekliyor ((C) şartnamesiyle birlikte açılır)";
     - "canlı n: dondurma commit'inden sonra listelenen arzlarla başlar; var olan 7 canlı kayıt v1 için RETRO";
     - real ve pooled için "§5.5 k3: uygulama birincili olamaz".
     
     Bölümlerin geri kalanı değişmez.
   - `docs/faz7/FREEZE_RAPOR.md` (rapor, aşağıda).
   - Tam pytest + test.sh yeşil → **commit F2**.

5. **Rapor.**

## Kurallar
- **DEĞİŞMEZ:**
  - `models/INDEX.json`'un ilk 19 girişi, 19 eski model dosyası, `post_d1_hazard_v0.json`, `INDEX_POST_D1.json`;
  - `docs/specs*`, `docs/fable_faz7_audit/`, `registry/`, `scores/`, `docs/SCORES.md`, `app/`, `legacy/`, `CLAUDE.md`;
  - `data/` (yalnız `data/raw/tuik/build_tufe_csv.py` K5 için değişebilir; TÜFE CSV'si ve xls bayt-eşit);
  - `tests/reference/` altındaki Faz 7 dışı dosyalar.
- **Yazılabilir:**
  - `borsai/` (K1, K3, K4, K5);
  - `tests/` (yeni testler; `tests/reference/macos_golden_faz7/` yalnız K1);
  - `experiments/log.jsonl` (yalnız ekleme), `docs/MODELS.md`, `docs/SPEC_DEVIATIONS.md` (J'ye ekleme), `docs/PROVENANCE.md` (§11'e ekleme);
  - `docs/faz7/`, bu görev dosyası;
  - F1'de `models/` (4 dosya + INDEX.json).
- Model davranışı şartnamedekidir. Dondurmada bir uyuşmazlık bulursan dondurma dosyalarını commit etme, DUR.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma. Hangi kodun kasada olduğu yazılmaz.
- `git add -A` yok. Commit'ler:
  ```
  git add borsai tests experiments/log.jsonl docs/MODELS.md docs/SPEC_DEVIATIONS.md docs/PROVENANCE.md data/raw/tuik/build_tufe_csv.py docs/faz7 docs/prompts/FAZ7_FREEZE.md
  git commit -m "BORSAI_FAZ7_FREEZE_K: audit fixes (clipped flag, TUFE and tolerance tests), freeze and record code for ceiling hazard v1, TUFE monthly append path, errata" -- borsai tests experiments/log.jsonl docs/MODELS.md docs/SPEC_DEVIATIONS.md docs/PROVENANCE.md data/raw/tuik/build_tufe_csv.py docs/faz7 docs/prompts/FAZ7_FREEZE.md
  git add models/ceiling_hazard_v1_clip.json models/ceiling_hazard_v1_real.json models/ceiling_hazard_v1_pooled.json "models/ceiling_hazard_v1_pooled@INF.json" models/INDEX.json
  git commit -m "BORSAI_FAZ7_FREEZE: ceiling hazard v1 family frozen into models/INDEX.json after independent reproduction (Fable FREEZE_OK)" -- models/ceiling_hazard_v1_clip.json models/ceiling_hazard_v1_real.json models/ceiling_hazard_v1_pooled.json "models/ceiling_hazard_v1_pooled@INF.json" models/INDEX.json
  git add tests docs/MODELS.md borsai/report_faz7.py docs/faz7
  git commit -m "BORSAI_FAZ7_FREEZE_B: frozen-model tests, MODELS.md freeze note, freeze report" -- tests docs/MODELS.md borsai/report_faz7.py docs/faz7
  ```
  Model dosya adları `freeze`'in yazdığı adlardır. Farklıysa gerçek adları kullan ve raporda belirt. Değişmeyen bir yol pathspec'te hata verirse o yolu çıkar. `report_faz7.py` değişikliği K'da yapıldıysa F2'de o yol çıkar.
- Push yok. Rapor Türkçe.

## Tek oturumda bitmezse
K yeşil ve commit'liyse orada dur. F1 ancak temiz ağaçta ve önizleme eşitliğiyle atılır.

## Teslim (rapor)
Raporu sohbete ve `docs/faz7/FREEZE_RAPOR.md`'ye yaz (F2'ye girer).
- K, F1, F2 hash'leri ve `git show --stat`; sıra K → F1 → F2.
- K1: sütun karşılaştırması (yalnız `test_clipped` değişti), yeni ledger sha'ları, 35/36/23.
- K2/K3 mutasyonlarının kırmızı gösterimi.
- K4/K5: yeni ön koşullar ve komut; aylık TÜFE ekleme komutunun tam metni.
- Donmuş 4 modelin sha256'sı, INDEX'e eklenen 4 giriş, önizleme ↔ donmuş JSON karşılaştırması (hangi alanlar farklı).
- Bayt-eşitlikler: ilk 19 giriş, eski model dosyaları, `INDEX_POST_D1`.
- Test sayıları: taban, K öncesi, F1 sonrası, F2 öncesi (sayı, süre); `gen_golden --check`; test.sh.
- Uygulama etkisi ölçümü (EK3 için).
- Sapmalar.

## Kabul kapısı
- **K1** Denetim düzeltmeleri: B1 (yalnız `test_clipped` değişti), B2, B3 (mutasyonlar kırmızı), B7 bekçisi; J errata yazılı; duyarlılık satırları günlükte.
- **K2** Dört model dondu. JSON'lar önizlemeyle (üç alan dışında) `==`; INDEX 23 giriş, ilk 19 değişmedi.
- **K3** Canlı kayıt yolu TÜFE bloğunu yazıyor ve eksik ayda kayıttan önce duruyor; aylık ekleme komutu belgeli ve testli.
- **K4** F1 sonrası ve F2 öncesi tam test yeşil; test.sh ve `gen_golden --check` yeşil. Commit'ler yalnız izinli yollarda; push yok.

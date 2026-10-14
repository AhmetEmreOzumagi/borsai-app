# TASK_ID: BORSAI_FAZ7C_FREEZE_20260928

Model: Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ gerekmez. push/tag/amend yok.

## Bağlam
- `fall_d10_v0` ailesi ("düşen arz") uygulandı ve backtest edildi, dondurulmadı:
  - A `3c93f9c`, A2 `1239e45`, A3 `77d0ee5`, B `acaca2d`, R `197a741`;
  - görev `docs/prompts/FAZ7_C_IMPL.md`, rapor `docs/faz7c/IMPL_RAPOR.md` (§11 dondurma notları).
- Fable'ın bağımsız yeniden üretimi ve denetimi: `docs/fable_faz7c_audit/AUDIT.md` (`80670cb`). Dört model için de **FREEZE_OK**:
  - ledger'lar alan alan birebir (maks |Δ| = 0);
  - 16/16 mutasyon kırmızı; sızıntı yok;
  - A2/A3 skor koduna dokunmuyor;
  - bulgular F1–F9, hepsi KÜÇÜK.
- Yakın dönem: birincil `pooled − h99` "belirsiz". Şartname gereği **dördü de dondurulur**: `fall_d10_v0_h99`, `fall_d10_v0_pooled`, `fall_d10_v0_addsale`, `fall_d10_v0_pooled@ZERO`.
- **Kalıp: `docs/prompts/FAZ7_FREEZE.md` ve `docs/faz7/FREEZE_RAPOR.md`.** Aynı sıra (K → F1 → APPPIN → F2), aynı iki tuzak:
  - sıra bekçisi: tam test F1'den sonra;
  - `borsai_dirty`: kod commit'i dondurmadan önce.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Bu görevde model davranışı değişmez.
- Bu görev, sonuçları gören uygulayıcıdan farklı bir oturumdur.

### Orkestratör kararları (proje sahibi adına, bağlayıcı)
- **APPPIN önceden onaylı (J31 kalıbı).** F1'den sonra ayrı bir commit'te yalnız şunlar güncellenir:
  - `app/parity/golden/MANIFEST.json`'daki `models_index_sha256`;
  - `app/tests/fixtures/ui/preflight_*.json`'daki INDEX sha'ları;
  - `app/src-tauri/tests/build_embed.rs`'deki `ignored_model_ids` beklentisi (4 v1 + 4 (C), INDEX sırasıyla).
  
  Rust mantığı değişmez. Başka bir `app/` dosyası değişmesi gerekirse DUR.
- **`report_faz7c.py` değişikliği onaylı:** F5 düzeltmesi ve dondurma notu.
- **Skorlar yeniden üretilmez.** `scores/`, `docs/SCORES.md` değişmez; J30 kalıbındaki istisna 8 yeni kartı kapsayacak şekilde, aynı koşullarla genişletilebilir. Skorların yeniden üretimi, yakın dönem bloğu ve F3 (K10 aile keşif sayacı) sıradaki görevde.
- **Eski kohort ek kayıtları, model başına kapı ve `oot_pre_h99_sealed/_all` bu görevde YOK;** sıradaki görevde, v1 ve (C) için birlikte.
- **Uygulama Rust desteği bu görevde YOK;** EK3 aşamaları.

### Paralel
Yok.

ÖNCE OKU:
- CLAUDE.md
- docs/fable_faz7c_audit/AUDIT.md (§0, §3, §7, §8)
- docs/faz7c/IMPL_RAPOR.md (§8, §11, §12)
- docs/specs_faz7_c/SPEC_C_V0.md §2.3, §7.1, §8, §9, §11; KARARLAR_C.md
- docs/SPEC_DEVIATIONS.md K ve J30, J31
- docs/prompts/FAZ7_FREEZE.md ve docs/faz7/FREEZE_RAPOR.md (kalıp)
- borsai/freeze.py (`freeze`, `model_kind`, `build_record`), borsai/backtest.py (`final_fit_fall`), borsai/predict_fall.py, borsai/registry.py (`F3_MODELS`), borsai/report_faz7c.py
- tests/test_faz7_frozen.py, tests/test_faz7c_*.py, tests/faz7_support.py, tests/faz7c_support.py, tests/test_models.py
- app/src-tauri/tests/build_embed.rs, app/parity/golden/MANIFEST.json (yalnız oku; APPPIN'e kadar)

## Adımlar
0. **Taban**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -4`: HEAD `80670cb` ya da torunu. `git status --porcelain`.
   - İzinli izlenmeyen: bu görev dosyası. Başka bir şey varsa DUR.
   - Tam `.venv/bin/pytest -q`, `bash app/scripts/test.sh`, `gen_golden --check` (25/0). Kırmızı varsa DUR.
   - Sayılar `docs/faz7c/ekler/freeze_test_runs.txt`'ye.

1. **K: kod ve belge düzeltmeleri** (model davranışı değişmez)
   - **K1 · dondurma yönlendirmesi:**
     - `freeze.model_kind` için "fall" dalı; `freeze` dört kimliği `backtest.final_fit_fall`'a yönlendirir (kod yolu aynı);
     - `registry.F3_MODELS`'e f3 isteyen `fall_d10_v0_h99` ve `fall_d10_v0_pooled`.
     - `build_record` (C) modelleri için gerekli girdileri zaten yazıyor mu? `additional_sale_shares`, `tufe_index`, ret yolları. Sentetik testle göster.
     - Canlı kayıtta TÜFE ön koşulu v1 ile ortak (tekrar yazılmaz).
   - **K2 · F5:** `report_faz7c.fold_summary` kural satırında (`@ZERO`) "ek satış sütunu düşen fold" alanını yazmaz. MODELS.md yeniden render; başka satır değişmez (farkı göster).
   - **K3 · F9:** küçük semantik testler:
     - eğitim satırlarında yüksek f3 → daha yüksek p_up (işaret);
     - bir fold'da test arzının girdileri değişince fit bit-eşit (Fable 2-i kalıbı).
     
     İkisinin de ilgili mutasyonda kırmızı olduğunu göster.
   - **K4 · belgeler (SPEC_DEVIATIONS K'ya ekleme; şartname değişmez):**
     - F1: K3'e ölçülen simetri farkı (addsale D5 |Δp| 8.7e-9; eşik Y_h fit'inde tanımlı).
     - F2 notu.
     - F4: K6 duyarlılığı, bilgi.
     - F6: parite testleri yazılmış JSON'dan koşar; kalıp notu.
     - F7: K6 bağlayıcı proje sahibi kararıdır.
     - Yeni satırlar K16+ olarak.
   - **K5:** Fable'ın duyarlılık satırlarını (`docs/fable_faz7c_audit/ekler/sensitivity_runs.jsonl`, `kind: sensitivity`) günlüğe ekle (yalnız ekleme).
   - **K6 · INDEX 27 hazırlığı:** "19/23 model" varsayan testler hem 23 hem 27 girişle geçecek şekilde uyarlanır. Önce dondurmayı geçici bir klonda dene (FAZ7_FREEZE kalıbı) ve F1 sonrası kırılacak testleri önceden gör.
   - Tam pytest + test.sh + `gen_golden --check` yeşil → **commit K**.

2. **F1: dondurma** (temiz ağaç, `borsai_dirty = false`)
   - `.venv/bin/python -m borsai.freeze --models fall_d10_v0_h99 fall_d10_v0_pooled fall_d10_v0_addsale fall_d10_v0_pooled@ZERO`
   - Beklenen:
     - 4 yeni model JSON'u;
     - `models/INDEX.json` sonuna 4 giriş (`FAZ7C_MODEL_IDS` sırası); ilk 23 giriş metin olarak aynı;
     - 23 eski model dosyası, `post_d1_hazard_v0.json` ve `INDEX_POST_D1.json` bayt-eşit;
     - şartname belge sha'sı SPEC_C_V0.md'nin sha'sı.
   - Donmuş JSON ↔ `tests/reference/macos_golden_faz7c/<model>_final_fit_preview.json`: `created_at`, `code_version`, `runtime` dışında `==`. Değilse DONDURMA DOSYALARINI COMMIT ETME, DUR ve raporla.
   - Hızlı kontrol: `.venv/bin/pytest -q tests/test_faz7c_golden.py tests/test_faz7c_model.py tests/test_models.py`.
   - **Commit F1** (yalnız 4 model dosyası + INDEX.json).

3. **Tam test F1'den sonra.** Yeşil olmalı. Kırmızıysa DUR ve raporla; F1'i geri alma, amend yapma.

4. **APPPIN** (önceden onaylı; yalnız yukarıdaki dosyalar ve satırlar)
   - Pin öncesi ve sonrası: `gen_golden --check`, `bash app/scripts/test.sh` (cargo `--no-fail-fast` sayıları dahil).
   - **Commit APPPIN.**

5. **F2: donmuş model testleri ve belgeler**
   - Donmuş JSON'larla `predict_fall` (stdlib), her modelin eğitim arzlarında numpy/sklearn nihai fit'e |Δ| ≤ 1e-12. Ayrıca şunlar sınanır:
     - `@ZERO` sabit (Fraction);
     - ret yolları (f3 boş, ek satış boş, TÜFE eksik/PIT değil, filtre uyuşmazlığı).
     - INDEX şeması, 27 giriş, sha'lar.
   - **MODELS.md Faz 7C dondurma notu** (`report_faz7c.py`):
     - tarih ve donmuş dosya sha'ları;
     - bağımsız yeniden üretim 2026-09-27, maks |Δ| = 0, `docs/fable_faz7c_audit/`;
     - "kasa: bekliyor (tavan serisi v1 ile birlikte tek seferde açılır)";
     - "canlı n: dondurma commit'inden sonra listelenen arzlarla başlar".
   - `docs/faz7c/FREEZE_RAPOR.md`.
   - Tam pytest + test.sh + `gen_golden --check` yeşil → **commit F2**.

6. **Rapor.**

## Kurallar
- **DEĞİŞMEZ:**
  - `models/INDEX.json`'un ilk 23 girişi ve 23 eski model dosyası, `post_d1_hazard_v0.json`, `INDEX_POST_D1.json`;
  - `docs/specs*`, `docs/fable_faz7c_audit/`, `docs/app/`, `registry/`, `scores/`, `docs/SCORES.md`, `data/`, `legacy/`, `CLAUDE.md`;
  - `app/` (APPPIN dışında);
  - `tests/reference/` altındaki Faz 7C dışı dosyalar.
- **Yazılabilir:**
  - `borsai/` (K1, K2, K3);
  - `tests/`;
  - `experiments/log.jsonl` (yalnız ekleme), `docs/MODELS.md`, `docs/SPEC_DEVIATIONS.md` (K'ya ekleme);
  - `docs/faz7c/`, bu görev dosyası;
  - F1'de `models/` (4 dosya + INDEX.json);
  - APPPIN'de yukarıdaki üç tür `app/` dosyası.
- Model davranışı şartnamedekidir. Dondurmada uyuşmazlık bulursan dondurma dosyalarını commit etme, DUR.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma. Hangi kodun kasada olduğu yazılmaz.
- Oturum içinde proje sahibine karar sorman gerekirse soruyu ve seçenekleri açıkça yaz. Proje sahibi orkestratöre danışarak cevaplayacak.
- `git add -A` yok. Commit'ler:
  ```
  git add borsai tests experiments/log.jsonl docs/MODELS.md docs/SPEC_DEVIATIONS.md docs/faz7c docs/prompts/FAZ7C_FREEZE.md
  git commit -m "BORSAI_FAZ7C_FREEZE_K: audit notes and tests (F1-F9), freeze routing for the falling-IPO family, fold-summary render fix, tests ready for a 27-entry index" -- borsai tests experiments/log.jsonl docs/MODELS.md docs/SPEC_DEVIATIONS.md docs/faz7c docs/prompts/FAZ7C_FREEZE.md
  git add models/fall_d10_v0_h99.json models/fall_d10_v0_pooled.json models/fall_d10_v0_addsale.json "models/fall_d10_v0_pooled@ZERO.json" models/INDEX.json
  git commit -m "BORSAI_FAZ7C_FREEZE: falling-IPO model v0 family frozen into models/INDEX.json after independent reproduction (Fable FREEZE_OK)" -- models/fall_d10_v0_h99.json models/fall_d10_v0_pooled.json models/fall_d10_v0_addsale.json "models/fall_d10_v0_pooled@ZERO.json" models/INDEX.json
  git add app/parity/golden/MANIFEST.json app/tests/fixtures/ui app/src-tauri/tests/build_embed.rs
  git commit -m "BORSAI_FAZ7C_FREEZE_APPPIN: re-pin the app to the 27-entry models/INDEX.json and expect the eight Faz 7 and 7C models as ignored; no Rust logic change (orchestrator decision, J31 pattern)" -- app/parity/golden/MANIFEST.json app/tests/fixtures/ui app/src-tauri/tests/build_embed.rs
  git add tests docs/MODELS.md borsai/report_faz7c.py docs/faz7c
  git commit -m "BORSAI_FAZ7C_FREEZE_B: frozen-model tests, MODELS.md freeze note, freeze report" -- tests docs/MODELS.md borsai/report_faz7c.py docs/faz7c
  ```
  Model dosya adları `freeze`'in yazdığı adlardır; farklıysa gerçek adları kullan ve raporda belirt. Değişmeyen bir yol pathspec'te hata verirse o yolu çıkar. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Push yok. Rapor Türkçe.

## Tek oturumda bitmezse
K yeşil ve commit'liyse orada dur. F1 ancak temiz ağaçta ve önizleme eşitliğiyle atılır.

## Teslim (rapor)
Raporu sohbete ve `docs/faz7c/FREEZE_RAPOR.md`'ye yaz (F2'ye girer).
- K, F1, APPPIN, F2 hash'leri ve sıra.
- F1–F9'un her biri için ne yapıldı.
- Donmuş 4 modelin sha256'sı, INDEX'e eklenen 4 giriş, önizleme ↔ donmuş JSON karşılaştırması.
- Bayt-eşitlikler.
- Test sayıları: taban, K öncesi, F1 sonrası, APPPIN öncesi/sonrası, F2 öncesi.
- Sapmalar.
- Push'tan sonra proje sahibinin koşacağı kanıt komutu (F1 commit'i).

## Kabul kapısı
- **K1** Dört model dondu. JSON'lar önizlemeyle (üç alan dışında) `==`; INDEX 27 giriş, ilk 23 değişmedi.
- **K2** F1–F9 işlendi (kod, test ya da belge); F5 render düzeltmesi yalnız o satırı değiştirdi.
- **K3** F1 sonrası ve F2 öncesi tam test yeşil; APPPIN sonrası test.sh ve `gen_golden --check` yeşil.
- **K4** Commit'ler yalnız izinli yollarda; push yok.

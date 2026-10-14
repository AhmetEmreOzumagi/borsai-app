# TASK_ID: BORSAI_FAZ5_FREEZE_20260924

Model: Opus 5.5 · yüksek. Klasör: ~/Desktop/BorsAi. Ağ gerekmez. push/tag/amend yok.

## Bağlam
- `post_d1_hazard_v0` uygulandı ve backtest edildi (`7ce0593` A, `7d08169` B), dondurulmadı: §5 "beklentiden çok iyi" Brier k = 2'de tetiklenmişti.
- Fable bağımsız yeniden üretim ve denetim: `docs/fable_faz5_audit/AUDIT.md` (`fe8ed54`). Hüküm **FREEZE_OK**:
  - 87 fold: durum ve λ birebir, sayısal sütunlar maks |Δ| 1.5e-11 (orkestratör Fable'ın ledger'ını altınla ayrıca karşılaştırdı: 2660 sayı, maks 1.53e-11, durum/λ/n uyuşmazlığı 0).
  - Nihai fit önizlemesi: λ = 30 birebir, δ maks |Δ| 1.1e-16. §4'ün 28 hücresi ve §5'in 18 etiketi aynı.
  - Canlı akış koşulu **teyit: kurulur** (nihai λ = 30, INF 2/70).
  - Sızıntı yok; 18 Faz 5 mutasyonunun 17'si kırmızı (tek yeşil: eşdeğer mutant, bulgu K3).
- Proje sahibi kararı 4: POST_D1 modelleri `models/INDEX_POST_D1.json`'da; `models/INDEX.json` ve listeleme öncesi kayıtlar DEĞİŞMEZ; uygulama bu dosyayı EK 3'e kadar okumaz.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** (Bu görevde model davranışı değişmez.)
- Bu görev yalnız dondurma ve denetimin bıraktığı küçük işler. Canlı POST_D1 akışı ayrı görev.

### Orkestratörün bulduğu nokta (kodda ölçüldü)
`scoring.sequence_violations` (commit A) `INDEX_POST_D1.json`'daki her model dosyasının commit'li olmasını ister; `tests/test_outcome_guard.py::test_sequence_rule_outcomes_follow_models_and_records` gerçek repoyu tarar. Yani dondurma dosyaları commit edilmeden tam test koşusu bu bekçide KIRMIZI olur; bu doğru davranıştır (commit'siz model varken yeni bülten inmemeli). Bu yüzden iki commit: F1 yalnız model dosyaları, F2 geri kalanı; tam test F1'den sonra.

### Paralel
- Orkestratör bu oturum sürerken `docs/prompts/FAZ5_POST_D1_LIVE.md` dosyasını yazabilir.
- Aynı anda bir Fable oturumu `docs/prompts/FAZ6_FABLE_OLD_COHORT_SPEC.md` görevini koşar; YALNIZ `docs/specs_faz6/` altına ve kendi görev dosyasına yazar, en sonda yalnız kendi yollarıyla commit atar.
- Bunlar izinli izlenmeyen sayılır; onlara dokunma, commit'lerine alma. `index.lock` hatasında bekle ve yeniden dene.

ÖNCE OKU:
- CLAUDE.md
- docs/fable_faz5_audit/AUDIT.md (§0, §4, §7)
- docs/specs_faz5/SPEC_POST_D1_V0.md §3.5, §6.2
- docs/SPEC_DEVIATIONS.md H bölümü; docs/faz5/IMPL_RAPOR.md §7
- borsai/freeze.py (`freeze`, `freeze_post_d1`), borsai/post_d1.py (nihai fit), borsai/specs.py (`POST_D1_MODEL_SPECS`)
- tests/test_faz5_post_d1.py (`test_2_…`, `test_15_…`), tests/test_faz5_golden.py, tests/test_experiment_log.py
- docs/prompts/FAZ4_FREEZE.md (kalıp)

## Adımlar
0. **Taban**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3` (beklenen HEAD `fe8ed54` ya da torunu), `git status --porcelain`.
   - İzinli izlenmeyen: `docs/prompts/FAZ5_FREEZE.md`, `docs/prompts/FAZ5_POST_D1_LIVE.md`, `docs/prompts/FAZ6_FABLE_OLD_COHORT_SPEC.md`, `docs/specs_faz6/**`. Başka bir şey varsa DUR.
   - `.venv/bin/pytest -q` tam koşu (sayı, süre). Kırmızı varsa DUR.
   - Altın MANIFEST'in `borsai_source_sha256`'sı (`5804e5cd…`) HEAD'in `borsai/` kaynak sha'sına eşit mi? (`7ce0593`'ten beri `borsai/` değişmedi olmalı.) Eşit değilse DUR ve farkı raporla.
1. **Dondurma** (temiz `borsai/`, `borsai_dirty = false`):
   - `.venv/bin/python -m borsai.freeze --models post_d1_hazard_v0`
   - Beklenen: yeni `models/post_d1_hazard_v0.json` ve `models/INDEX_POST_D1.json` (şema `borsai.model_index/1`, tek kayıt). `models/INDEX.json` ve mevcut 19 model dosyası bayt-eşit.
   - Ön koşullar kodda: `ceiling_hazard_v0.json` ve `ceiling_path_v0.json` sha'ları `INDEX.json` ile eşit; JSON'daki parent ve `path_secondary` sha pinleri dosya sha'larıyla eşit; `spec_document_sha256` = `a5b4675d…`.
   - Donmuş JSON ↔ `tests/reference/macos_golden_faz5/post_d1_hazard_v0_final_fit_preview.json`: `created_at`, `code_version`, `runtime` dışında `==`. Değilse DONDURMA DOSYALARINI COMMIT ETME, DUR ve raporla.
   - Hızlı kontrol: `.venv/bin/pytest -q tests/test_faz5_post_d1.py tests/test_faz5_golden.py` yeşil.
   - **Commit F1** (yalnız iki model dosyası).
2. **Tam test** F1'den sonra: yeşil olmalı (özellikle `test_outcome_guard.py`, `test_models.py`, `test_faz1b_guardrails.py`, Faz 4 bekçileri). Kırmızıysa DUR ve raporla; F1'i geri alma, amend yapma.
3. **Denetimin bıraktığı işler** (AUDIT §4, §7; hepsi aynı model_id):
   - K3: `test_2`'ye binary64'te ayırt edilemeyen ama Decimal'de farklı çift: "10.12" vs "10.1200000000000000001" → 0; "10.12" vs "10.120" → 1. Önce testin float mutasyonunda kırmızı olduğunu göster (geçici değişiklikle; geri al), sonra ekle.
   - K4: `test_15`'e `LAMBDA_FINAL_LIKELY`, `LAMBDA_FOLD_INF_SHARE`, `N_FOLDS_RANGE`, `LOCK_SIGN_SHARE` sabitlerinin şartname §5 değerleriyle eşitliği.
   - Donmuş model testleri: `models/post_d1_hazard_v0.json` ile `predict_post_d1` 81 eğitim arzında numpy nihai fit'e |Δ| ≤ 1e-12, h_1 ve λ = INF ucu bit-eşit (var olan test altyapısını kullan); `INDEX_POST_D1.json` şeması, tek kayıt, sha'lar; `INDEX.json` 72a000f ile bayt-eşit.
   - `experiments/log.jsonl`'a Fable'ın 2 duyarlılık satırı (`docs/fable_faz5_audit/ekler/sensitivity_runs.jsonl`, `kind: sensitivity`, model değil). Faz 4 kalıbı; `test_experiment_log.py` bu türü zaten kabul ediyorsa değiştirme.
   - `docs/SPEC_DEVIATIONS.md` H bölümüne errata satırları (şartname değişmez, v0 kimliği değişmez): K1 (§9 kod adları öneksiz, B3), K2 (`D1_FIELD_INVALID`), K6 (§12 sözde kodu `eta = linear_predictor(parent, inputs)` olmalı), K8 (eşitlik sayımı yalnız aynı kod yolunda bit-eşit farkla), K9 (§6.1-7 (i) yalnız D1 yükleyicisi için; path hücreleri SPEC_CEILING_PATH_V0 §8'e göre kesimli okur).
   - `docs/MODELS.md` yeniden üretilir (`python -m borsai.report`). Faz 5 bölümünün sonuna: bağımsız yeniden üretim 2026-09-24, maks |Δ| 1.5e-11, `docs/fable_faz5_audit/`; donmuş model sha'sı; k = 10 dipnotu: "δ bütün d = 2..10'da ortak olduğundan kilit bilgisi D4–D10'a da taşınır; k = 10 hafif kötüleşir (AUDIT §5-3); gün-grubu etkileşimi yeni model_id'dir." Mevcut bölümlerin geri kalanı değişmez.
   - K5 ve K7 bu görevde YOK (canlı akış görevi).
4. **Skorlar yeniden üretilmez.** `scores/scores.json` ve `docs/SCORES.md` değişmez (H22 istisnası geçerli kalır; canlı akış görevi yeniden üretecek).
5. Tam test yeşil → **Commit F2**.
6. Rapor.

## Kurallar
- DEĞİŞMEZ: `models/INDEX.json` ve 19 model dosyası; `docs/specs*`; `docs/fable_faz5_audit/`; `tests/reference/` altındaki mevcut dosyalar (altın faz5 MANIFEST dahil); `registry/`, `data/`, `scores/`, `docs/SCORES.md`, `app/`, `legacy/`, `CLAUDE.md`; `borsai/` (davranış değişikliği yok; gerekirse DUR).
- Model davranışı şartnamedekidir. Dondurmada bir uyuşmazlık bulursan dondurma dosyalarını commit etme, DUR.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit'ler:
  ```
  git add models/post_d1_hazard_v0.json models/INDEX_POST_D1.json
  git commit -m "BORSAI_FAZ5_FREEZE: post_d1_hazard_v0 frozen into models/INDEX_POST_D1.json after independent reproduction (Fable FREEZE_OK)" -- models/post_d1_hazard_v0.json models/INDEX_POST_D1.json
  git add tests experiments/log.jsonl docs/MODELS.md docs/SPEC_DEVIATIONS.md docs/faz5 docs/prompts/FAZ5_FREEZE.md
  git commit -m "BORSAI_FAZ5_FREEZE_B: frozen-model tests, audit test hardening (K3, K4), sensitivity log lines, errata notes, MODELS.md" -- tests experiments/log.jsonl docs/MODELS.md docs/SPEC_DEVIATIONS.md docs/faz5 docs/prompts/FAZ5_FREEZE.md
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Push yok. Rapor Türkçe.

## Teslim (rapor)
Raporu sohbete ve `docs/faz5/FREEZE_RAPOR.md`'ye yaz (F2'ye girer).
- F1 ve F2 hash'leri, `git show --stat`; F1'in F2'nin atası olduğu.
- Donmuş modelin sha256'sı, `INDEX_POST_D1.json` içeriği, parent/path/spec sha pinleri.
- Önizleme ↔ donmuş JSON karşılaştırması (hangi alanlar farklı).
- `INDEX.json` ve 19 model dosyasının bayt-eşitliği.
- Test sayıları: taban, F1 sonrası, F2 öncesi (sayı, süre).
- K3 mutasyonunun kırmızı gösterimi.
- Sapmalar.

## Kabul kapısı
- K1 `post_d1_hazard_v0` dondu; JSON önizlemeyle (üç alan dışında) `==`; `INDEX_POST_D1.json` tek kayıt ve doğru sha.
- K2 `INDEX.json`, 19 model dosyası, `scores/`, `registry/`, `data/`, `app/`, `borsai/` değişmedi.
- K3 K3/K4 testleri eklendi; duyarlılık satırları günlükte; errata H'de; MODELS.md güncel.
- K4 F1 sonrası ve F2 öncesi tam test yeşil; F1, F2'nin atası; commit'ler yalnız izinli yollarda; push yok.

# BORSAI_FAZ8_FREEZE_20261002 — `break_floor_v0` ve `break_floor_v0@ZERO` dondurması: rapor

Görev `docs/prompts/FAZ8_FREEZE.md` (Opus 5.5; sonuçları gören uygulayıcıdan ayrı oturum). Ağ yok; push, tag, amend yok. Bağlayıcı
metinler `docs/specs_faz8/SPEC_BREAK_V0.md` (sha256 `da98351c2b1b…`) ve `docs/specs_faz8/KARARLAR.md` (sha256 `8d8bbc971b01…`);
denetim `docs/fable_faz8_audit/AUDIT.md` (`6d3f674`: **REPRO_OK**). **Model davranışı değişmedi**: dondurma kodu yazıldı, model kodu
(`post_break.py`, `predict_break.py`) ve şartname değişmedi; donmuş JSON'lar nihai fit önizlemelerinin aynısıdır.

## 0. Kısa sonuç

- İki kimlik donduruldu: `break_floor_v0` (model) ve `break_floor_v0@ZERO` (kural satırı ve karşılaştırıcı), yeni ayrı dizin
  `models/INDEX_POST_BREAK.json`'a. `models/INDEX.json`, `models/INDEX_POST_D1.json` ve 28 model dosyası bayt-eşit.
- Donmuş JSON'lar önizlemelerle `created_at`, `code_version`, `runtime` dışında `==` (gerçekte yalnız `created_at` ve `code_version`
  farklı; `runtime` de aynı). Dondurma temiz ağaçta; `code_version.git_commit` = K, `borsai_dirty` false.
- Kod (K): `freeze_post_break`, `post_break_index_entry`, `model_kind → post_break` dalı (ortak algoritma adından önce), `run_model`
  reddi, `specs._spec_of` / `specs.model_kind` (yalnız ekleme). Var olan 28 modelin türü değişmedi.
- Prova (geçici klon) yalnız yönlendirmeyle bağlamdaki beş K-PIN testini kırmızı verdi (başka kırmızı yok); bütün K ve F2 ile
  klonda hepsi yeşil. Ana depoda K-PIN dışında hiçbir pin değişmedi; uygulama (`app/`) değişmedi, APPPIN adımı yok.
- MODELS.md'de yalnız Faz 8 bölümünün sonuna "### Dondurma" notu eklendi (REPRO_OK, N20 bilgi notları, kart uyarıları).
- Proje sahibine bu görevde soru sorulmadı.

## 1. Commit'ler (sıra K → F1 → F2)

| Commit | Hash | Üst | İçerik |
|---|---|---|---|
| K | `74b851a5be6ad6b4746ac96a7745d2ee0c9d95f3` | `6d3f674` | `borsai/freeze.py`, `borsai/specs.py` (yalnız ekleme), yeni `tests/test_faz8_freeze.py`, `tests/faz8_support.py` (`frozen_post_break_files`), beş K-PIN testi, SPEC_DEVIATIONS N21–N25, `docs/faz8/freeze_test_runs.txt`, görev dosyası — 12 dosya, +649 / −13 |
| F1 | `4d3c9a26be65ee4b3b8f204945f36cdae7eedd5a` | `74b851a` | yalnız `models/INDEX_POST_BREAK.json`, `models/break_floor_v0.json`, `models/break_floor_v0@ZERO.json` — 3 dosya, +1137 |
| F2 | (bu raporu içeren commit) | `4d3c9a2` | yeni `tests/test_faz8_frozen.py`, `borsai/report_faz8.py` (dondurma notu), `docs/MODELS.md`, SPEC_DEVIATIONS (F2 satırı), `docs/faz8/` |

K, F1'in atası; F1, F2'nin atası (doğrusal). `git show --stat`:

```
commit 74b851a5be6ad6b4746ac96a7745d2ee0c9d95f3
parent 6d3f6741ae1beffb26625229e18768665ece61d2
BORSAI_FAZ8_FREEZE_K: freeze routing for the break-evening model (freeze_post_break into models/INDEX_POST_BREAK.json; post_break kind checked before the shared logit algorithm name; run_model refuses…

 borsai/freeze.py               |  70 +++++++++++-
 borsai/specs.py                |   9 ++
 docs/SPEC_DEVIATIONS.md        |  14 +++
 docs/faz8/freeze_test_runs.txt |  46 ++++++++
 docs/prompts/FAZ8_FREEZE.md    | 249 +++++++++++++++++++++++++++++++++++++++++
 tests/faz8_support.py          |  26 +++++
 tests/test_faz5_frozen.py      |   4 +-
 tests/test_faz5_post_d1.py     |   9 +-
 tests/test_faz8_break.py       |   3 +-
 tests/test_faz8_freeze.py      | 195 ++++++++++++++++++++++++++++++++
 tests/test_faz8_golden.py      |   6 +-
 tests/test_faz8_model.py       |  31 ++++-
 12 files changed, 649 insertions(+), 13 deletions(-)
```

```
commit 4d3c9a26be65ee4b3b8f204945f36cdae7eedd5a
parent 74b851a5be6ad6b4746ac96a7745d2ee0c9d95f3
BORSAI_FAZ8_FREEZE: break_floor_v0 and break_floor_v0@ZERO frozen into models/INDEX_POST_BREAK.json after independent reproduction (Fable REPRO_OK)

 models/INDEX_POST_BREAK.json    |  43 +++
 models/break_floor_v0.json      | 635 ++++++++++++++++++++++++++++++++++++++++
 models/break_floor_v0@ZERO.json | 459 +++++++++++++++++++++++++++++
 3 files changed, 1137 insertions(+)
```

Dosya adları `freeze`'in yazdığı, görev metnindeki adlardır.

## 2. Prova (adım 0b; geçici klon, ayrıntı `docs/faz8/freeze_test_runs.txt`)

- **Yalnız yönlendirme** (K-FRZ-1..3) → klonda commit → dondurma → commit: tam paralel pytest **901 passed, 5 failed**. Beşi de (i)
  K-PIN türü (dondurma öncesi durumu sabitleyen iddialar): `test_faz8_break::test_14b`, `test_faz8_model::test_5c`,
  `test_faz5_frozen::test_pre_listing_index_and_models_byte_identical`, `test_faz8_golden::test_b7`, `test_faz5_post_d1::test_14`.
  (ii) kod hatası: yok. (iii) başka: yok. `test.sh` ve `gen_golden --check` yeşil (uygulama yalnız INDEX.json ve INDEX_POST_D1.json'u
  okur). Var olan 28 modelin `freeze.model_kind` / `specs.model_kind` türü yönlendirmeden önce ve sonra aynı (28/28).
- **Bütün K** (yeni dal, 6d3f674'ten) → commit → dondurma → commit: **913 passed** (0 failed). **F2** (commit'siz): 920 passed, 1 failed
  — tek kırmızı `test_faz7_vault::test_real_scores_oot_in_memory_run_equals_committed_file` (`/code/borsai_dirty`: commit'siz
  `borsai/report_faz8.py`; tanımı gereği), F2 commit'inden sonra tek başına yeşil. `test.sh`, `gen_golden --check` yeşil. Yeni
  testlerin 8 mutasyonu 8/8 kırmızı. Klon ve cargo hedef dizini silindi.

## 3. K · kod

- **K-FRZ-1 (N21):** komut var olan bayrak: `python -m borsai.freeze --models break_floor_v0 break_floor_v0@ZERO`; `--post-break` yok.
- **K-FRZ-2 (N22):** `freeze.freeze` herhangi bir POST_BREAK kimliği görünce `freeze_post_break`'e verir; o yalnız
  `FAZ8_MODEL_IDS`'i (sırasıyla) kabul eder; kimlik üç dizinden birinde ya da diskte varsa hiçbir şey yazılmadan `FreezeError`;
  `post_break.final_fit(m, dataset)[0]` → `models/<id>.json`; giriş `post_break_index_entry` (`index_entry` alanları, `training_n` =
  `n_F1`, + `stage`, `training_n_F2`, `training_tickers_sha256_F2`, `sessions_file_sha256`); INDEX.json ve INDEX_POST_D1.json'a yazılmaz.
- **K-FRZ-3 (N23):** `freeze.model_kind`: `stage == POST_BREAK` ve `family == break_floor_v0` → `post_break` (algoritma denetiminden
  önce; ortak ad `l2_logit_v1_6_grid`); `run_model`: `post_break` → ERROR + `PARAMS_INVALID`. `specs._spec_of` ve `specs.model_kind`
  aynı dal (yalnız ekleme; `git diff 6d3f674 -- borsai/specs.py`'de silinen satır yok).
- `registry.py`, `scoring.py`, `outcomes.py`, `predict_break.py`, `post_break.py` değişmedi (K-FRZ-6). Günlüğe satır eklenmedi (K-FRZ-5).
- Yeni testler `tests/test_faz8_freeze.py` (7): iki dosya + INDEX_POST_BREAK yazılır, öteki dizinler bayt-eşit; dizin girişi alanları
  (ve `index_entry`'nin kırılma JSON'unda KeyError vermesi); ikinci çağrı / tek kimlik / ters sıra / karışık çağrı / başka dizinde ya
  da diskte var → ret, hiçbir şey yazılmaz; CLI `--models` iki kimliği `freeze`'e verir, `--post-break` reddedilir; `model_kind`
  (önizleme → `post_break`; aşama ya da aile tutmazsa dal çalışmaz); 28 modelin türü sabit sözlükle; `run_model` → PARAMS_INVALID.

## 4. K-PIN (önceden onaylı; SPEC_DEVIATIONS N25)

Yardımcı `tests/faz8_support.frozen_post_break_files()`: dondurmadan önce `[]`, sonra üç dosya adı (dizin şeması, giriş sırası,
dosya adları ve sha'lar doğrulanır; başka durum durur). Eski bayt-eşitlik ayakları aynen.

| Test | İddia | Önce | Sonra |
|---|---|---|---|
| `test_faz8_model.py::test_5c_old_goldens_and_app_pins_unchanged` | `git diff 7d78d43 -- tests/reference app models`; `freeze.py` değişmedi | boş; `freeze.py` 7d78d43 ile aynı | yalnız eklenen üç models/ dosyası (diff-filter=A da aynı); `freeze.py` 7d78d43..6d3f674 aynı, sonrası yalnız konusu `BORSAI_FAZ8_FREEZE_K:` olan tek commit (çalışma ağacı ona eşit); `specs.py` aynı K kuralı + yalnız ekleme sürer |
| `test_faz8_break.py::test_14b_old_specs_models_and_cutoff_unchanged` | INDEX_POST_BREAK yok | dosya yok | `frozen_post_break_files()` (yok ya da doğrulanmış üç dosya); INDEX.json/INDEX_POST_D1 bayt-eşitliği ve `git status` temizliği aynen |
| `test_faz8_golden.py::test_b7_old_outputs_unchanged` | `git diff 5d84e88 -- … models …` boş | boş | yalnız eklenen üç models/ dosyası (diff-filter=A da aynı) |
| `test_faz5_post_d1.py::test_14_models_goldens_and_read_only_paths_unchanged` | models/ JSON sayısı ve eklenen küme | 22 + Faz 7/7C dosyaları | + üç Faz 8 dosyası (sayı ve `--diff-filter=A` kümesi); `pre` 20 dosyanın bayt-eşitliği aynen |
| `test_faz5_frozen.py::test_pre_listing_index_and_models_byte_identical` | diskteki models/ JSON listesi | INDEX + INDEX_POST_D1 + POST_D1 + INDEX girişleri | + `frozen_post_break_files()` |

Kapsam dışı bekçiler (`test_outcome_guard`, `test_faz7_vault`, `test_scoring` içerik pinleri, sıra/kasa/hijyen, N19 istisnası)
hiçbir koşuda kırmızı olmadı; dokunulmadı.

## 5. F1 · dondurma

`.venv/bin/python -m borsai.freeze --models break_floor_v0 break_floor_v0@ZERO` (HEAD `74b851a`, `git status` boş; 2 s).

| model_id | sha256 | frozen_at (yerel) | spec_sha256 (ilk 12) |
|---|---|---|---|
| `break_floor_v0` | `81f07e7810ca5b9513ebc577e14182798ea0b227f105df1551950d6ce40a3eab` | 2026-10-02T16:21:00+03:00 | `8ada9ccf77dc` |
| `break_floor_v0@ZERO` | `f460acc84717fb489eb81d96fce01ff44f4eb850b9fc66f0c50fb8858000bd3b` | 2026-10-02T16:21:01+03:00 | `73d719f01240` |

`models/INDEX_POST_BREAK.json` (sha256 `899cf90c805d45313e187e2297f9207229d119f57c1ca56b009ace24ff8e8c5e`; şema `borsai.model_index/1`;
iki giriş, `FAZ8_MODEL_IDS` sırası). Her giriş: algorithm `l2_logit_v1_6_grid`, file, sha256 (yukarıda), schema_version
`borsai.model/1`, spec_sha256, `training_n` 82, `training_cutoff_date` 2026-08-10, `training_tickers_sha256` `a6b9557400eb…` (F1 kümesi),
data_version_sha256 `a0c7d082dacd…` (H99), frozen_at, frozen_at_basis, status FROZEN, `stage` POST_BREAK, `training_n_F2` 78,
`training_tickers_sha256_F2` `fc59946f7a2a…`, `sessions_file_sha256` `eca620d3a5e8…`.

**Önizleme ↔ donmuş JSON:** ikisinde de farklı alanlar yalnız `created_at` (önizleme 2026-10-02T11:36:14+03:00, donmuş 16:21:00 /
16:21:01) ve `code_version` (önizleme `fa623df`; donmuş `git_commit` `74b851a5…` = K, `borsai_dirty` false, `borsai_source_sha256`
`ec8ca3f85bb1…` = K'nın borsai/ ağacı, testli). `runtime` dahil öteki her alan `==`. Uyuşmazlık yok.

Beklenen sayılar tablosu (görev metni) birebir: `break_floor_v0` F1 C 1.0, sabit −1.0006869243500793, b_floor +0.9866556408087268,
b_turnover +0.06286893543556789; F2 C 0.1, sabit −1.89485164203132, +0.28721801132023284 / −0.3079897535288709; eğitim 82 / 25 ve
78 / 11; `@ZERO` 0.3048780487804878 (25/82) ve 0.14102564102564102 (11/78); `by_type_F1` 19/35 = 0.5428571428571428, 6/47 =
0.1276595744680851 (Fraction'la bit-eşit, testli); `training.cutoff_date` 2026-08-10.

Commit öncesi hızlı kontrol (`test_faz8_freeze/golden/model/break`): 43 passed, 3 failed — üçü de commit'siz `models/`'ten
(`test_b7`, `test_5c`: `git diff` izlenmeyen dosyayı görmez; `test_14b`: `git status` `??`); F1 commit'inden sonra 3 passed.

## 6. Bayt-eşitlikler

- `models/INDEX.json` sha256 `7e636e8bf64b…` (27 giriş), `models/INDEX_POST_D1.json` `94ac36faffac…`, 28 model dosyası ve
  `models/.gitkeep`: 6d3f674 ile 31/31 bayt-eşit (`tests/test_faz8_frozen.py` sınar).
- `scores/`, `docs/SCORES.md`, `registry/`, `data/`, `app/`, `legacy/`, `CLAUDE.md`, `experiments/log.jsonl` (2146 satır),
  `docs/specs*` (KARARLAR dahil), `docs/fable_faz8_audit/`, `docs/faz8/backtest/`, `tests/reference/`: değişmedi
  (`git diff --name-only 6d3f674 -- …` boş; §8).

## 7. F2 · MODELS.md ve donmuş-model testleri

- `borsai/report_faz8.py`: `_frozen_section` (yalnız INDEX_POST_BREAK iki kimliği listeleyince ve resmi dizinle), `frozen_entries`,
  `card_warnings`, `REPRO` sözlüğü (değer → AUDIT bölümü), `PROMOTION_LABEL`. `@ZERO` hücresi ledger'dan.
- `docs/MODELS.md` diff: yalnız Faz 8 bölümünün sonunda (`### Faz 8 koşusu ve deney günlüğü` tablosundan sonra, Faz 7C başlığından
  önce) **+24 satır, −0**: "### Dondurma" başlığı; REPRO paragrafı; iki satırlı dosya tablosu; Dizin / Öne çıkan durum / Canlı
  maddeleri; iki bilgi notu (N20); yedi kart uyarısı. `### Nihai fit önizlemesi (dondurulmadı)` ve öteki başlıklar yerinde; başka bayt
  yok.
- `tests/test_faz8_frozen.py` (8): dizin ve bayt-eşitlikler; donmuş ↔ önizleme, K = F1'in üstü, temiz kod, F1 yalnız üç dosya;
  yeniden dondurma reddi; stdlib ↔ numpy (82 / 78 satır, |Δp| ≤ 1e-12) ve beklenen katsayılar; `@ZERO` / `by_type` Fraction; b = 9
  (dört H99 arzı: F2 yok, `TARGET_UNDEFINED_F2`), b = 10 (`B10`), L = 10 (`NO_BREAK`); tür + `run_model` + listeleme öncesi kayıt
  yalnız INDEX.json'un 27 modeli (`test_faz7c_frozen::test_live_record_with_the_real_index_carries_four_fall_cells` de 27'yi sınar);
  MODELS.md notu (sha'lar, REPRO değerlerinin AUDIT bölümünde birebir geçmesi, k1 etiketi, yedi uyarı).

## 8. Test sayıları ve süreleri (ayrıntı `docs/faz8/freeze_test_runs.txt`)

| Aşama | pytest | `test.sh` | `gen_golden --check` |
|---|---|---|---|
| Taban (6d3f674), paralel | 906 passed, 569.2 s | yeşil, 69 s (cargo 151 / 0, npm 305, parity 8, golden_unchanged) | 35 / 0 |
| Prova: yalnız yönlendirme + F1 (klon), paralel | 901 passed, 5 failed (K-PIN), 645.2 s | yeşil, 88 s | 35 / 0 |
| Prova: bütün K + F1 (klon), paralel | 913 passed, 696.0 s | — | — |
| Prova: + F2 commit'siz (klon), paralel | 920 passed, 1 failed (kasa bellek testi, `borsai_dirty`; commit sonrası 1 passed), 711.5 s | yeşil | 35 / 0 |
| K öncesi (commit'siz K), paralel | 912 passed (+1 ayrılan), 693.2 s | yeşil, 56 s | 35 / 0 |
| K sonrası, ayrılan test + K testleri | 9 passed, 98.8 s | — | — |
| F1 sonrası (HEAD 4d3c9a2), paralel | **913 passed**, 669.9 s | yeşil, 56 s (cargo 151 / 0, npm 305, parity 8) | 35 / 0 |
| F2 öncesi (HEAD 4d3c9a2 + F2 commit'siz), **sıralı** | **920 passed, 1 deselected**, 970.3 s (0:16:10) | yeşil, 40 s (cargo 151 / 0, npm 305, parity 8, golden_unchanged) | 35 / 0 |

Sayılar: 906 taban + 7 (`test_faz8_freeze.py`) + 8 (`test_faz8_frozen.py`) = 921. Ayrılan test
(`test_faz7_vault.py::test_real_scores_oot_in_memory_run_equals_committed_file`) commit'siz `borsai/` ile `borsai_dirty` farkından
tanımı gereği kırmızıdır; her commit'ten (K, F2) hemen sonra tek başına koşulur (K sonrası yeşil; F2 sonrası sonuç sohbet raporunda).

## 9. Sapmalar (SPEC_DEVIATIONS N21–N25)

| # | Konu |
|---|---|
| N21 | K-FRZ-1: komut `--models` (şartnamedeki `--post-break` yerine); tek dondurma yolu |
| N22 | K-FRZ-2: `freeze_post_break`, `post_break_index_entry` (`training_n` = `n_F1`; `index_entry` değişmedi); `training_cutoff_date` 2026-08-10 ile şartnamedeki 2026-08-19 iki ayrı alan |
| N23 | K-FRZ-3: ortak algoritma adı; `post_break` dalı aşama/aileyle ve algoritmadan önce; `run_model` reddi; `specs` yalnız ekleme; 28 tür aynı |
| N24 | K-FRZ-4: Fable §9 cevapları (proje sahibi kararı 2026-10-02): N20 notları MODELS.md'ye bilgi; b = 9'da F2 yok (testli); bant duyuruları dondurmayı bekletmez (N15 çekincesi açık) |
| N25 | K-PIN: beş test, tek yardımcı, kural (a)/(b) |

Ek notlar:
- Commit öncesi koşularda `test_faz7_vault::test_real_scores_oot_in_memory_run_equals_committed_file` ayrıldı (commit'siz `borsai/`
  ile `borsai_dirty` farkı tanımı gereği kırmızıdır; Faz 8 A kalıbı) ve her commit'ten sonra tek başına koşuldu (yeşil).
- `models/.gitkeep` izli: "models/ 30 dosya" sayımı JSON dosyalarıdır (31 izli dosya).
- Hijyen: yeni dosyalarda bülten adı kalıbı ve kasa kodu yok (`test_faz8_break::test_14` yeni test dosyalarını ve `docs/faz8/`'i tarar).

## 10. Push'tan sonra proje sahibinin koşacağı kanıt komutu

Zaman kanıtı push'tur: dalı (K `74b851a`, F1 `4d3c9a2` ve F2) push ettikten sonra

```
.venv/bin/python -m borsai.push_proof 4d3c9a2
```

Bu model için bir arz ancak dondurma commit'i (F1) o arzın D_b'sinden sonraki ilk bülteni ya da h ≥ b + 1 sonucunu repoya sokan
commit'in atasıysa ve push kanıtlıysa prospektiftir (§9.3); bugünkü 7 arz RETRO'dur.

## 11. Sıradaki görevler için notlar

- **S görevi (canlı skorlama, makine sıralı kayıt):** `sequence_violations`'a INDEX_POST_BREAK (model dosyaları H5 kuralıyla),
  makine kayıt yazıcısı (`registry/post_break/`), `record_problems_through`, `outcome_ingest_commit_after`, `scores_break.json`.
  `outcomes.sequence_guard` bugün INDEX_POST_BREAK'i ayrıca listelemez; ama `models/` korunan dizin olduğundan commit'siz dosya
  bülten indirmeyi zaten durdurur. Skorlama `freeze.model_kind`'i kullanır: donmuş kırılma JSON'u artık `post_break` döner (S görevi
  bu türü kendi yoluna almalı; listeleme öncesi skorlamaya girmez çünkü INDEX.json'da değildir).
- **EK 5 (uygulama):** `build_embed` yalnız INDEX.json ve INDEX_POST_D1.json okur; INDEX_POST_BREAK EK 5'te eklenecek. Kart metni
  MODELS.md dondurma notundaki iki bilgi notu ve yedi uyarıdan (`report_faz8.card_warnings`); etiket `PROMOTION_LABEL`; canlı n
  skorlama görevinden.
- K-PIN yardımcısı `frozen_post_break_files()` bundan sonraki dondurma görevlerinde `frozen_tail_ids` gibi genişletilebilir.

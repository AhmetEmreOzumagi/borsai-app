# TASK_ID: BORSAI_FAZ8_FREEZE_20261002

Model: Claude Code / Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ gerekmez. push/tag/amend yok.

**Rol:** kırılma akşamı modelini (`break_floor_v0`) ve kural satırını (`break_floor_v0@ZERO`) SPEC_BREAK_V0 §7.3'e göre dondurmak. Dondurma kodu henüz yok; bu görev onu yazar, dondurur ve belgeler. Model davranışı değişmez.

## Bağlam
- Sıra: şartname `7d78d43` → K `5d84e88` → A `fa623df` → B `df338c2` → R `c84ba64` → Fable denetimi `6d3f674`. Denetimin hükmü **REPRO_OK** (`docs/fable_faz8_audit/AUDIT.md`):
  - ledger, üç duyarlılık ve iki önizleme bit-eşit (maks |Δ| = 0);
  - 13/13 mutasyon kırmızı; sızıntı yok; dondurma önerisi §8.
- Hücreler: birincil F1 − ürün −0.1904 [−0.2520, −0.1247]; F1 − `@ZERO` −0.0281 [−0.0453, −0.0074]; n 69, 21 ay; k1 sağlandı.
- Dondurma kodu yok (IMPL_RAPOR §13, N1). `freeze_post_break`, `model_kind → post_break` dalı ve `models/INDEX_POST_BREAK.json` bu görevde yazılır.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Bu görevde model davranışı değişmez.
- Bu oturum, sonuçları gören uygulayıcıdan farklı bir oturumdur.

### Orkestratörün ölçtükleri (2 Ekim, `6d3f674`; dosya okuyarak, test koşmadan)
1. **Taban.** HEAD = origin/main = `6d3f674`, ağaç temiz.
   - `models/` 30 dosya: `INDEX.json` 27 giriş (sha256 `7e636e8b…`), `INDEX_POST_D1.json` 1 giriş (`94ac36fa…`), 28 model dosyası. `INDEX_POST_BREAK.json` yok.
   - Günlük 2146 satır. pytest 906 (AUDIT §5), `gen_golden --check` 35/0, `test.sh` yeşil (cargo 151, vitest 305, parity 8).
2. **Kod.** `git diff fa623df 6d3f674 -- borsai` boş: önizlemeleri üreten kod bugünkü kod.
3. **Önizlemeler.**
   - `docs/faz8/backtest/break_floor_v0_final_fit_preview.json` (sha `eab46afb…`) ve `…@ZERO_final_fit_preview.json` (`d63f8f55…`).
   - `code_version` = {git_commit `fa623df`, borsai_dirty false, borsai_source_sha256 `0e13b6be…`}.
   - `post_break.final_fit(model_id, dataset)` önizlemeyi üretir. `test_faz8_golden::test_b5` aynı yolu `created_at`, `code_version`, `runtime` dışında `==` ile sınar.
4. **Tuzak 1: algoritma adı çakışıyor.** `predict_break.ALGORITHM == predict_fall.FALL_ALGORITHM == "l2_logit_v1_6_grid"`.
   - `freeze.model_kind(params)` algoritmaya bakar. Donmuş kırılma JSON'u için bugün **`"fall"`** döner.
   - `scoring` bu fonksiyonu kullanır (satır ~1205, 2226, 2516, 2643, 3347).
   - `specs.model_kind(model_id)` → `_spec_of` Faz 8 kimliklerini bilmez (KeyError).
5. **Tuzak 2: `freeze.index_entry` `params["training"]["n"]` okur.** Kırılma JSON'unun `training`'inde `n` yok (`n_F1`, `n_F2` var) → KeyError.
6. **Tuzak 3: dondurma öncesi durumu sabitleyen testler** (okuyarak buldum; tam liste adım 0b'deki provadan çıkar):
   - K'de (`freeze.py` değişince): `tests/test_faz8_model.py::test_5c_old_goldens_and_app_pins_unchanged`. Bu test `borsai/freeze.py`'nin `7d78d43`'ten beri değişmemesini ister; `specs.py` için yalnız ekleme şartı da burada.
   - F1'de (`models/`'e 3 dosya eklenince):
     - yine `test_5c` (`git diff 7d78d43 -- … models` boş);
     - `tests/test_faz8_break.py::test_14b_old_specs_models_and_cutoff_unchanged` (`INDEX_POST_BREAK.json` yok);
     - `tests/test_faz8_golden.py::test_b7_old_outputs_unchanged` (`git diff 5d84e88 -- … models` boş);
     - `tests/test_faz5_post_d1.py::test_14_models_goldens_and_read_only_paths_unchanged` (models/ dosya sayısı ve eklenen dosya kümesi);
     - `tests/test_faz5_frozen.py::test_pre_listing_index_and_models_byte_identical` (models/ dosya listesi).
7. **Uygulama.**
   - `build_embed` yalnız `INDEX.json` ve `INDEX_POST_D1.json` okur (`plan_embedding`, `plan_post_d1`). models/'e eklenen dosyalar gömmeyi değiştirmez.
   - İki dizin değişmediği için `app/parity/golden/MANIFEST.json` pinleri de değişmez. **APPPIN adımı yok.**
8. **MODELS.md.**
   - `report.py` Faz 8 kancası `render_faz8`'i çağırır.
   - `test_b6`, MODELS.md'nin `report.render()` ile eşitliğini ve bölüm başlıklarını sınar. `### Nihai fit önizlemesi (dondurulmadı)` başlığı yerinde kalmalı.
   - Kalıp: `report_faz5._frozen_section` ve `report_faz7c._frozen_section`.
9. **Hijyen.** `test_faz8_break::test_14` şunları tarar: `docs/faz8/**` (.md/.txt/.csv/.json), `tests/test_faz8_*.py`, `borsai/report_faz8.py`. Yeni dosyalar da taranır.

## Kararlar (orkestratör, proje sahibi adına; bağlayıcı)
- **K-FRZ-1 · Komut.** Dondurma var olan bayrakla yapılır: `python -m borsai.freeze --models break_floor_v0 break_floor_v0@ZERO`.
  - `freeze()` POST_BREAK kimliklerini `freeze_post_break`'e yönlendirir (`freeze_post_d1` kalıbı).
  - Şartname §7.3'teki `--post-break` bayrağı eklenmez; tek dondurma yolu kalır. Bu yalnız komut adıdır, model davranışı değildir; SPEC_DEVIATIONS N'ye yazılır.
- **K-FRZ-2 · `freeze_post_break(model_ids, dataset, *, models_dir)`.**
  - İki kimlik yalnız birlikte ve `FAZ8_MODEL_IDS` sırasıyla dondurulur. Tek kimlik, başka sıra ya da başka modellerle karışık çağrı `FreezeError` verir.
  - Kimlik üç dizinin herhangi birinde ya da diskte varsa `FreezeError` (üzerine yazılmaz).
  - `params = post_break.final_fit(m, dataset)[0]` → `models/<id>.json` (`pretty_json_bytes`).
  - `models/INDEX_POST_BREAK.json` yeni dosyadır (`borsai.model_index/1`). `INDEX.json` ve `INDEX_POST_D1.json`'a hiçbir zaman yazılmaz (testli).
  - Dizin girişi: `index_entry` alanları; `training_n` = `n_F1`. Ek alanlar: `stage`, `training_n_F2`, `training_tickers_sha256_F2`, `sessions_file_sha256`.
  - `index_entry`'nin kendisi değişmez; ayrı bir yardımcı yazılır.
- **K-FRZ-3 · Tür dalları.**
  - `freeze.model_kind`: `stage == predict_break.STAGE` (ve `family`) ise `"post_break"`. Bu denetim algoritma denetiminden **önce** gelir.
  - `run_model`: `post_break` modeli listeleme öncesi kayıtta çalışmaz; `post_d1` gibi `PARAMS_INVALID` döner.
  - `specs._spec_of` `POST_BREAK_MODEL_SPECS`'i tanır. `specs.model_kind` fall denetiminden önce `"post_break"` döner.
  - `specs.py`'ye **yalnız ekleme** yapılır; silinen satır olmaz (`test_5c` bunu sınamayı sürdürür).
  - Var olan 28 modelin iki fonksiyondaki türü değişmez. Türler provada ölçülür ve testte sabit sözlük olarak yazılır.
- **K-FRZ-4 · Fable §9 cevapları** (proje sahibi ve orkestratör kabul etti, 2026-10-02):
  1. N20 notları MODELS.md'nin Faz 8 dondurma notuna **bilgi** olarak girer (AUDIT §2d). Hücre tanımı değişmez; kart metni EK 5'te yazılır.
  2. b = 9'da F2 yazılmaz. Kod değişmez; donmuş JSON'la test edilir.
  3. Bant duyuruları dondurmayı bekletmez. N15 çekincesi açık kalır; canlıda koruma `BAND_RULE_MISMATCH`'tir.

  Üçü SPEC_DEVIATIONS N'ye proje sahibi kararı olarak yazılır. **`docs/specs_faz8/KARARLAR.md` değişmez** (sha'sı `specs.py`'de ve model JSON'unda pinli).
- **K-FRZ-5 · Günlük.** Dondurma backtest değildir; `experiments/log.jsonl`'a satır eklenmez. Fable'ın N20 alternatif eşik tablosu (AUDIT §2b) karşılaştırıcının sağlamlık denetimidir, model varyantı değildir; kaydı AUDIT'tedir.
- **K-FRZ-6 · Kapsam dışı** (S görevi, şartname §9.6):
  - `sequence_violations`'a INDEX_POST_BREAK eklenmesi;
  - makine kayıt yazıcısı, `record_problems_through`, `outcome_ingest_commit_after`;
  - `scores_break.json` ve `registry/post_break/`.

  `borsai/registry.py`, `scoring.py`, `outcomes.py`, `predict_break.py` ve `post_break.py` bu görevde değişmez.
- **K-FRZ-7 · Skorlar.** Skorlar yeniden üretilmez; `scores/` ve `docs/SCORES.md` değişmez. N19 istisnası aynen geçerlidir.
- **K-FRZ-8 · Uygulama.** `app/` değişmez. `test.sh` F1'den sonra kırmızıysa DUR.

## Önceden onaylı pin güncellemeleri (K-PIN)
Proje sahibi bunları başlatma cümlesinde onaylar.

**Kural.** Dondurma öncesi durumu sabitleyen iddialar iki durumu kabul edecek biçimde güncellenir:
- (a) Dondurmadan önce: bugünkü hali aynen.
- (b) Dondurmadan sonra yalnız şu:
  - `models/`'e tam olarak 3 dosya eklenmiş: `INDEX_POST_BREAK.json`, `break_floor_v0.json`, `break_floor_v0@ZERO.json`;
  - INDEX_POST_BREAK tam olarak `FAZ8_MODEL_IDS`'i listeler ve sha'lar dosyalarla eşittir;
  - `borsai/freeze.py` ve `borsai/specs.py`'deki fark yalnız bu görevin K commit'inden gelir; `specs.py`'de yine silinen satır yoktur.

**Kalıp.**
- `tests/faz8_support.py`'ye tek bir yardımcı eklenir: `frozen_post_break_files()`. Dondurmadan önce `[]`, sonra üç dosya adını döndürür ve dizin içeriğini doğrular (`faz7_support.frozen_tail_ids` kalıbı). Testler bu yardımcıyı kullanır.
- Eski bayt-eşitlik ayakları aynen kalır, gevşetilmez: INDEX.json, INDEX_POST_D1.json, 28 model dosyası, eski altınlar, specs belgeleri, registry/data/scores/app.

**Kapsam.** Bağlam 6'daki beş test ile adım 0b provasında bulunan **aynı türden** testler.

**Kapsam dışı; kırmızı olursa DUR ve raporla:** `test_outcome_guard`, `test_faz7_vault`, `test_scoring` içerik pinleri, sıra/kasa/hijyen bekçileri, N19 istisnası ve herhangi bir mantık değişikliği.

## İzinli izlenmeyen
Yalnız bu görev dosyası (`docs/prompts/FAZ8_FREEZE.md`). Başka bir şey varsa DUR.

## Paralel
Yok.

## ÖNCE OKU
- `CLAUDE.md`
- `docs/fable_faz8_audit/AUDIT.md` (§0, §2, §8, §9)
- `docs/faz8/IMPL_RAPOR.md` (§7, §11, §13)
- `docs/specs_faz8/SPEC_BREAK_V0.md` §4.4, §7.3, §8, §9.2, §13; `docs/specs_faz8/KARARLAR.md` §C
- `docs/SPEC_DEVIATIONS.md` N
- `docs/prompts/FAZ7C_FREEZE.md` ve `docs/faz7c/FREEZE_RAPOR.md` (kalıp: prova → K → F1 → F2)
- `borsai/freeze.py`: `freeze`, `freeze_post_d1`, `index_entry`, `model_kind`, `run_model`, `main`
- `borsai/specs.py`: `_spec_of`, `model_kind`, Faz 8 bloğu
- `borsai/post_break.py`: `final_fit`, `build_params`, `parity_rows`
- `borsai/predict_break.py`: `check_params`, `predict_break`
- `borsai/report_faz8.py`; `report_faz5.py` ve `report_faz7c.py` (`_frozen_section`)
- `tests/test_faz8_*.py`, `tests/faz8_support.py`, `tests/faz7_support.py` (`frozen_tail_ids`), `tests/test_faz5_frozen.py`, `tests/test_faz7c_frozen.py`, `tests/test_faz7c_freeze.py`

## Adımlar
0. **Taban**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3`: HEAD `6d3f674` (ya da yalnız push kanıtı commit'i içeren torunu).
   - `git status --porcelain --untracked-files=all`: yalnız bu görev dosyası görünmeli.
   - Paralel pytest (`.venv/bin/pytest -q -n 6 --dist loadgroup`), `bash app/scripts/test.sh` ve `.venv/bin/python app/parity/gen_golden.py --check` koş. Beklenen: 906 passed; test.sh yeşil; 35/0. Kırmızı varsa DUR.
   - Sayıları (komut, sayı, süre) `docs/faz8/freeze_test_runs.txt`'ye yaz.

0b. **Prova** (geçici klon; repo dışında, oturumun geçici dizininde; `.venv` sembolik bağla; FAZ7C kalıbı)
   - Klonda yalnız K-FRZ-2/3 yönlendirmesini uygula → klonda dondur → klonda commit at → tam paralel pytest ve `test.sh` koş. Kırmızıları listele.
   - Her kırmızıyı sınıfla:
     - (i) K-PIN türü (önceden onaylı);
     - (ii) kod hatası: model davranışı değişmeden düzelt;
     - (iii) başka bir şey: DUR, ana repoda hiçbir şey commit etmeden raporla.
   - Aynı klonda bütün K'yi, F2 testlerini ve notu uygula; hepsini yeşil gör.
   - Klonu sonda sil. Özeti `docs/faz8/freeze_test_runs.txt`'ye yaz.

1. **K: kod, testler, belgeler** (model davranışı değişmez)
   - K-FRZ-1..3'ün kodu: `borsai/freeze.py`, `borsai/specs.py`. Windows: sabit yol yok, `Path` kullan.
   - Yeni K testleri (`tests/test_faz8_freeze.py`). Sentetik `models_dir` kullan; `final_fit` gerekiyorsa monkeypatch'le önizlemeyi döndür. Sınanacaklar:
     - iki dosya ve INDEX_POST_BREAK yazılıyor; INDEX.json ile INDEX_POST_D1 bayt-eşit kalıyor;
     - ikinci çağrı reddediliyor; tek kimlikli ya da karışık çağrı reddediliyor;
     - dizin girişinin alanları doğru;
     - `model_kind`: önizleme JSON'u → `post_break`; 28 donmuş dosyanın türü değişmemiş;
     - `run_model` → `PARAMS_INVALID`;
     - CLI `--models break_floor_v0 break_floor_v0@ZERO` iki kimliği `freeze`'e veriyor (`test_faz7c_freeze` kalıbı).
   - K-PIN güncellemeleri (provada bulunanlar dahil).
   - SPEC_DEVIATIONS N'ye ekleme (N21'den başlayarak): K-FRZ-1 (komut adı), K-FRZ-2 (dizin girişi; `index_entry`'nin `n`'i), K-FRZ-3 (algoritma adı çakışması ve yeni dal), K-FRZ-4 (Fable §9 cevapları; proje sahibi kararı 2026-10-02), K-PIN (hangi testler, hangi kural).
   - Paralel pytest, `test.sh` ve `gen_golden --check` yeşilse **commit K**.

2. **F1: dondurma** (temiz ağaçta; `borsai_dirty = false`)
   - `git status --porcelain --untracked-files=all` boş olmalı.
   - `.venv/bin/python -m borsai.freeze --models break_floor_v0 break_floor_v0@ZERO`
   - Beklenen:
     - Tam olarak 3 yeni dosya: `models/break_floor_v0.json`, `models/break_floor_v0@ZERO.json`, `models/INDEX_POST_BREAK.json`. Dizinde 2 giriş, `FAZ8_MODEL_IDS` sırasıyla, sha'lar dosyalarla eşit, `stage` POST_BREAK.
     - `INDEX.json` (`7e636e8b…`), `INDEX_POST_D1.json` (`94ac36fa…`) ve 28 model dosyası bayt-eşit.
     - Donmuş JSON önizlemeyle `created_at`, `code_version`, `runtime` dışında `==`. `code_version.git_commit` = K, `borsai_dirty` false.
     - Aşağıdaki "Beklenen sayılar" tablosu.
   - Uyuşmazlık varsa DONDURMA DOSYALARINI COMMIT ETME, DUR ve raporla.
   - Hızlı kontrol: `.venv/bin/pytest -q tests/test_faz8_freeze.py tests/test_faz8_golden.py tests/test_faz8_model.py tests/test_faz8_break.py`. Commit'siz `models/` yüzünden `git status` kırmızıları beklenir (Faz 7C'de 3 tane çıkmıştı); başka kırmızı varsa DUR.
   - **Commit F1** (yalnız bu 3 dosya).

3. **Tam test, F1'den sonra.** Paralel pytest (tam küme), `test.sh` ve `gen_golden --check` yeşil olmalı. Kırmızıysa DUR; F1'i geri alma, amend yapma.

4. **F2: donmuş model testleri ve belgeler**
   - Yeni `tests/test_faz8_frozen.py`. Sınanacaklar:
     - INDEX_POST_BREAK: şema, 2 giriş, sha'lar, alanlar. INDEX.json, INDEX_POST_D1 ve 28 model dosyası `6d3f674` ile bayt-eşit.
     - Donmuş JSON önizlemeye eşit (3 alan dışında). `code_version.git_commit`, `models/break_floor_v0.json`'ı ekleyen commit'in üstüdür; `borsai_dirty` false; `pb.check_params` geçer.
     - stdlib `predict_break` donmuş JSON'la 82 (F2'de 78) eğitim satırında numpy nihai fit'ten en çok 1e-12 sapar (|Δp| ≤ 1e-12; `parity_rows`).
     - `@ZERO` F1 = 25/82, F2 = 11/78; `by_type_F1` 19/35 ve 6/47. Fraction'la bit-eşit.
     - b = 9'da F2 yok (`TARGET_UNDEFINED_F2`), F1 dolu. b = 10 ve L = 10 kapsam dışı (K-FRZ-4/2).
     - `model_kind` → `post_break`; `run_model` → `PARAMS_INVALID`. Listeleme öncesi kayıt yolu hâlâ yalnız INDEX.json'un 27 modelini çalıştırır (var olan bir test bunu sınıyorsa ona atıf yeter).
     - MODELS.md dondurma notu: sha'lar dosyalarla eşit; REPRO sabitleri AUDIT.md metninde birebir geçiyor.
   - `borsai/report_faz8.py` → `_frozen_section`. Bu bölüm yalnız INDEX_POST_BREAK iki kimliği listeleyince yazılır, Faz 8 bölümünün **sonuna**, `### Dondurma` başlığıyla. İçerik:
     - **Donduruldu, bağımsız yeniden üretimden sonra:** REPRO_OK 2026-10-02; maks |Δ| 0 (eşik 1e-9); Faz 4 hücre paritesi 87/87; 13/13 mutasyon kırmızı; `docs/fable_faz8_audit/`. Donmuş dosyalar önizlemenin aynısıdır; dondurma temiz ağaçta yapıldı. Son cümle: "Yukarıdaki 'dondurulmadı' ifadeleri backtest anının kaydıdır."
     - **Tablo:** model_id | dosya | sha256 | dondurma tarihi (yerel saat; kanıt push'tur) | rol. Roller: `break_floor_v0` model; `@ZERO` kural satırı ve karşılaştırıcı.
     - **Dizin:** `models/INDEX_POST_BREAK.json` ayrı dizindir; INDEX.json ve INDEX_POST_D1 değişmedi.
     - **Öne çıkan durum** (§8 aşama 1): k1 sağlandı. Etiket aynen: "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0".
     - **Canlı:** makine sıralı, ölçek `live_break`. Skorlama ve makine kayıt yazıcısı ayrı görevdir. Zaman kanıtı dondurma commit'inin push'udur. Bugünkü 7 arz bu model için RETRO'dur (§9.3).
     - **Bilgi notları** (K-FRZ-4/1; hücre tanımı değişmez):
       - (i) Ürün türevi kesin eşikle hesaplanır. Bir adım toleransla taban kırılmasında ürünün ortalaması 0.199 olur (kesin eşikte 0.115). Birincil fark −0.1611 [−0.2193, −0.1013]; aralık yine 0'ın altında.
       - (ii) Ürün taban üstü kırılmaya ≈ 0.57 der, gözlenen 0.12'dir. Birincil farkın büyüklüğü karşılaştırıcının zayıflığından gelir; tek orana karşı kazanç küçüktür: −0.0281 [−0.0453, −0.0074].
     - **Kart uyarıları** (EK 5 kullanacak): AUDIT §8 "Gösterilecek uyarılar" 1–7, kısaltarak, sayılar aynen.
     - Sayılar sabit sözlükte tutulur (REPRO; kaynağı AUDIT bölüm numarasıyla). Test, bunların AUDIT.md'de birebir geçtiğini sınar. `@ZERO` hücresi ledger'dan zaten hesaplanıyorsa oradan alınır.
   - `.venv/bin/python -m borsai.report` → `docs/MODELS.md`. Fark yalnız Faz 8 bölümünün sonundaki not olmalı; diff rapora girer.
   - `docs/faz8/FREEZE_RAPOR.md`.
   - **Sıralı** tam pytest (`.venv/bin/pytest -q`), `test.sh` ve `gen_golden --check` yeşilse **commit F2**.

5. **Rapor.**

## Beklenen sayılar (önizlemelerden ölçüldü)
| | F1 | F2 |
|---|---|---|
| `break_floor_v0` C | 1.0 | 0.1 |
| sabit | −1.0006869243500793 | −1.89485164203132 |
| katsayı b_floor / b_turnover | +0.9866556408087268 / +0.06286893543556789 | +0.28721801132023284 / −0.3079897535288709 |
| eğitim n / olay | 82 / 25 | 78 / 11 |
| `@ZERO` p | 0.3048780487804878 (25/82) | 0.14102564102564102 (11/78) |

- `by_type_F1`: sınıf 1 → 19/35 = 0.5428571428571428; sınıf 0 → 6/47 = 0.1276595744680851.
- `training.cutoff_date` 2026-08-10. Bu, etiketlerin son seansıdır. `specs` sözlüğündeki 2026-08-19 ise veri kesimidir; iki ayrı alan, ikisi de doğru.
- `spec_sha256`: `8ada9ccf…` (model) / `73d719f0…` (@ZERO). Şartname belgesi `da98351c…`, KARARLAR `8d8bbc97…`.
- pytest: taban 906. K, F1 ve F2'de 906 + yeni testler; sayıyı raporla.

## Tek oturumda bitmezse
- K yeşil ve commit'liyse orada durulabilir.
- F1 yalnız temiz ağaçta ve önizleme eşitliği sağlanınca atılır. F1 commit'liyse ve F1 sonrası tam test yeşilse orada da durulabilir: push ve kanıt F1'le yapılabilir, F2 ertesi gün.
- Aynı pencerede "devam" ile sürer.

## Kurallar
- **DEĞİŞMEZ:**
  - `models/INDEX.json`, `models/INDEX_POST_D1.json` ve 28 model dosyası;
  - `docs/specs*` (`docs/specs_faz8/KARARLAR.md` dahil), `docs/fable_faz8_audit/`, `docs/faz8/backtest/`, `tests/reference/`;
  - `registry/`, `data/`, `scores/`, `docs/SCORES.md`, `app/`, `legacy/`, `CLAUDE.md`, `experiments/log.jsonl`;
  - `borsai/` içinde `freeze.py`, `specs.py` (K) ve `report_faz8.py` (F2) dışındaki her şey.
- **Yazılabilir:**
  - K'de: `borsai/freeze.py`, `borsai/specs.py` (yalnız ekleme), `tests/`, `docs/SPEC_DEVIATIONS.md` (N'ye ekleme), `docs/faz8/` (`backtest/` hariç), bu görev dosyası.
  - F1'de: yalnız üç `models/` dosyası.
  - F2'de: `tests/`, `borsai/report_faz8.py`, `docs/MODELS.md`, `docs/SPEC_DEVIATIONS.md`, `docs/faz8/` (`backtest/` hariç).
- Model davranışı şartnamedekidir. Dondurmada uyuşmazlık bulursan dondurma dosyalarını commit etme, DUR.
- Metinlere `thb`/`thm` + 8 haneli tarih kalıbı ve kasa üyesi kodu yazılmaz (`test_faz8_break::test_14` yeni dosyaları da tarar).
- Windows: yeni kodda sabit Mac yolu ya da kabuğa özel sözdizimi olmaz.
- Proje sahibine karar sorman gerekirse soruyu ve seçenekleri açıkça yaz. Proje sahibi orkestratöre danışarak cevaplayacak.
- `git add -A` yok. Commit'ler:
  ```
  git add borsai/freeze.py borsai/specs.py tests docs/SPEC_DEVIATIONS.md docs/faz8 docs/prompts/FAZ8_FREEZE.md
  git commit -m "BORSAI_FAZ8_FREEZE_K: freeze routing for the break-evening model (freeze_post_break into models/INDEX_POST_BREAK.json; post_break kind checked before the shared logit algorithm name; run_model refuses it), freeze tests, pre-approved post-freeze pin updates (K-PIN), SPEC_DEVIATIONS N21+" -- borsai/freeze.py borsai/specs.py tests docs/SPEC_DEVIATIONS.md docs/faz8 docs/prompts/FAZ8_FREEZE.md
  git add models/break_floor_v0.json "models/break_floor_v0@ZERO.json" models/INDEX_POST_BREAK.json
  git commit -m "BORSAI_FAZ8_FREEZE: break_floor_v0 and break_floor_v0@ZERO frozen into models/INDEX_POST_BREAK.json after independent reproduction (Fable REPRO_OK)" -- models/break_floor_v0.json "models/break_floor_v0@ZERO.json" models/INDEX_POST_BREAK.json
  git add tests borsai/report_faz8.py docs/MODELS.md docs/SPEC_DEVIATIONS.md docs/faz8
  git commit -m "BORSAI_FAZ8_FREEZE_B: frozen-model tests, MODELS.md Faz 8 freeze note (REPRO_OK, N20 info notes, card warnings), freeze report" -- tests borsai/report_faz8.py docs/MODELS.md docs/SPEC_DEVIATIONS.md docs/faz8
  ```
  Dosya adları `freeze`'in yazdığı adlardır; farklıysa gerçek adları kullan ve raporda belirt. Değişmeyen bir yol pathspec'te hata verirse o yolu çıkar. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Push yok. Rapor Türkçe.

## Teslim (rapor)
Raporu sohbete ve `docs/faz8/FREEZE_RAPOR.md`'ye yaz (F2'ye girer):
- K, F1, F2 hash'leri ve sıra (K F1'in atası, F1 F2'nin atası); `git show --stat`.
- Prova: yalnız yönlendirmeyle çıkan kırmızı liste ve sınıflaması; bütün K'yle sonuç.
- K-PIN: her test için tek satır (hangi iddia, önce/sonra).
- Donmuş iki dosyanın sha256'sı, INDEX_POST_BREAK içeriği, önizleme ↔ donmuş JSON karşılaştırması (hangi alanlar farklı).
- Bayt-eşitlikler (INDEX.json, INDEX_POST_D1, 28 dosya).
- MODELS.md diff özeti.
- Test sayıları ve süreleri: taban, K öncesi, F1 sonrası, F2 öncesi; `test.sh` ve `gen_golden`.
- Sapmalar (N21+).
- Push'tan sonra proje sahibinin koşacağı kanıt komutu (F1 commit'i için).

## Kabul kapısı
- **K1** İki kimlik dondu. JSON'lar önizlemeyle (3 alan dışında) `==`. INDEX_POST_BREAK 2 giriş ve sha'ları doğru. `borsai_dirty` false.
- **K2** INDEX.json, INDEX_POST_D1, 28 model dosyası, `scores/`, `registry/`, `data/`, `app/`, günlük, `docs/specs*` ve KARARLAR değişmedi.
- **K3** Donmuş kırılma JSON'unun türü `post_break`; listeleme öncesi kayıtta çalışmıyor; var olan 28 modelin türü değişmedi.
- **K4** F1 sonrası ve F2 öncesi (sıralı) tam test yeşil; `test.sh` ve `gen_golden` yeşil. Pin değişiklikleri yalnız K-PIN kuralıyla yapıldı.
- **K5** MODELS.md dondurma notu yazıldı; Fable §9 cevapları SPEC_DEVIATIONS'ta. Commit'ler yalnız izinli yollarda; push yok.

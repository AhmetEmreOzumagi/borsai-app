# TASK_ID: BORSAI_FAZ8_LIVE_BREAK_20261002

Model: Claude Code / Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ gerekmez (bültenler yerelde pinli). push/tag/amend yok.

**Rol:** kırılma akşamı modelinin canlı aşamasını (`POST_BREAK`, makine sıralı) kurmak. Bu görevde yazılacaklar:
- makine kayıt yazıcısı;
- kayıt bekçisi;
- sınıf kanıtları;
- `scores/scores_break.json` (ölçek `live_break`) ve belgesi;
- sıra bekçisine yeni dizin.

Şartname SPEC_BREAK_V0 §9, kabul testleri §13-11, 12, 13. Model ve skor tanımı değişmez.

## Bağlam
- Model donmuş ve zaman kanıtlı:
  - `break_floor_v0` ve `break_floor_v0@ZERO` → `models/INDEX_POST_BREAK.json`;
  - commit `4d3c9a2`; push kanıtı `registry/push_proofs/4d3c9a26….json` (GitHub `2026-10-02T14:45:08Z`, kanıt commit'i `fd88be3`);
  - dondurma raporu `docs/faz8/FREEZE_RAPOR.md`.
- Dondurma görevinde kapsam dışı bırakılanlar şimdi yazılıyor (FAZ8_FREEZE K-FRZ-6): sıra bekçisine INDEX_POST_BREAK, makine kayıt yazıcısı, kayıt bekçisi, sonuç-giriş commit'i, `scores_break.json`.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Bu görevde model davranışı değişmez.

### Orkestratörün ölçtükleri (2 Ekim, `fd88be3`; dosya okuyarak, test koşmadan)
1. **Taban.** HEAD = origin/main = `fd88be3`, ağaç temiz.
   - pytest 921: son sıralı koşu 920 passed + 1 ayrılan kasa testi, o test commit sonrası tek başına yeşil.
   - `gen_golden --check` 35/0; `test.sh` yeşil (cargo 151, vitest 305, parity 8).
2. **Kalıplar (scoring.py ve freeze.py'de).**
   - POST_D1 sınıfı: `outcome_ingest_commit_post_d1`, `model_prospective_post_d1`, `class_post_d1`, `post_d1_block`, `build_post_d1_scores`.
   - Eski kohort makine kaydı: `freeze.build_oot_post_d1_record` / `write_oot_post_d1_record` (`EXPOSURE_MACHINE_SEQUENCED`).
   - Ayrı dosya + ayrı belge + bayrak: `scoring.main_oot` (`--oot` → `scores_oot.json` + `SCORES_OOT.md`; SPEC_DEVIATIONS I39).
   - Mükerrer kayıt reddi: `freeze.write_record` (aynı girdi sha'sı + INDEX sha'sı → DUPLICATE).
3. **Bekçiler.**
   - `registry.post_d1_record_problems` bütün `session_date` değerlerinin tam olarak D_1 olmasını ister; `tests/test_outcome_guard.py` onu çağırır.
   - `scoring.sequence_violations` INDEX.json Faz 1 modellerini ve INDEX_POST_D1'i bağlar; INDEX_POST_BREAK'i bilmez.
4. **Bayraksız `scoring.main()`.** `tests/test_faz6_s6.py::test_main_dispatches_oot_flag_and_bare_main_is_unchanged` çağrı listesini sabitler (`build_scores, build_post_d1_scores, write_scores, write_post_d1_scores, write_doc`).
5. **Uygulama.** `build_embed` yalnız `scores.json` ve `scores_oot.json`'u adla gömer; yeni skor dosyası uygulamayı etkilemez → `app/` değişmez.
6. **Girdiler.** `outcomes.ThbRow` D_b alanlarının hepsini taşır (open, high, low, volume, turnover, aof, special_volume, special_turnover); `ThmRow.lower` var → `outcomes.py` değişmez.
   - `data/outcomes/<T>.csv` alt limit taşımaz; etiket için D_{b+1}/D_{b+2} alt limiti pinli THM'den okunur.
   - `data/raw/bist/` 2026-08-17…2026-09-30 bültenleri MANIFEST'te (73 satır); 7 arzın D_1..D_{b+2} günleri bu aralıkta.
7. **Listeleme öncesi kayıtlar.** 7 arzın `registry/records/<T>/` kaydı yalnız 16 Faz 1 modelini taşır, `ceiling_path_v0` çıktısı yok → `PRODUCT_BREAK_FLOOR` bu 7 arzda **NOT_AVAILABLE** (§5.1 "kayıt yoksa NOT_AVAILABLE"). İleride gelecek arzların kaydı 27 modeli taşır.
8. **Bu görevin kıracağı koruma testleri** (okuyarak buldum; tam liste adım 0b provasından çıkar):
   - `tests/test_faz8_model.py::test_5c_old_goldens_and_app_pins_unchanged`: `scoring`, `registry` 7d78d43'ten beri değişmemiş; `_freeze_k_ref`: `freeze.py` yalnız `BORSAI_FAZ8_FREEZE_K:` commit'inden.
   - `tests/test_faz8_golden.py::test_b7_old_outputs_unchanged`: `git diff 5d84e88 -- … registry … scores` (ve models) yalnız dondurma dosyaları.
9. **Beklenen sayılar.** 7 arz için kırılma alanlarını ve tahmini, donmuş JSON ve stdlib `predict_break` ile kendim hesapladım.
   - Girdiler: D_b'nin pinli THB/THM bülteninden `fields_raw` = {open, high, low, close, volume, trade_count, reference_price, upper_limit, lower_limit, special_trade_volume}; `half_day`/`halt_flag` sonuç CSV'sinden; `shares_offered` = `registry/inputs/<T>.json` `fields.shares_offered`.
   - Sonuçlar "Beklenen sayılar" tablosunda.
   - **Orkestratör maruziyeti:** bu 7 arzın D_{b+1} kapanışlarına baktım. 7'si de RETRO'dur (model sonuçlardan sonra donduruldu); hiçbir canlı n'e girmez.

## Kararlar (orkestratör, proje sahibi adına; bağlayıcı)
- **K-LB-1 · Komut ve dosyalar.** `python -m borsai.scoring --break` (`main_break`; `main_oot` kalıbı) sırayla şunları yapar:
  - (i) eksik makine kayıtlarını yazar (K-LB-3);
  - (ii) `scores/scores_break.json`'ı yazar (şema `borsai.scores_break/1`);
  - (iii) yazılmış JSON'dan `docs/SCORES_BREAK.md`'yi üretir.

  Bayraksız `main()` **değişmez** (test_faz6_s6 yeşil kalır). `scores.json`, `scores_post_d1.json`, `scores_oot.json`, `docs/SCORES.md` ve `docs/SCORES_OOT.md`'ye dokunulmaz.

  Şartname §9.6'daki "docs/SCORES.md §8" yerine ayrı belge yazılır. Gerekçe: SCORES.md, scores.json'la birlikte üretiliyor; onu yeniden yazmak scores.json'ı yeniden üretmek demek (Faz 8 varyant sayacı +1, N19 istisnası), bu da bu görevin kapsamı dışında. Kalıp I39. SPEC_DEVIATIONS N'ye yazılır.
- **K-LB-2 · Kayıt yeri ve şeması** (şartname §9.2 aynen):
  - Yol `registry/post_break/<T>/machine_<UTC>_<kısa-sha>.json`; şema `borsai.post_break_machine_record/1`; append-only; `exposure_class = MACHINE_SEQUENCED`.
  - Yazıcı `freeze.write_post_break_machine_record(ticker, …)` (ve `build_…`); yol sabiti `registry.POST_BREAK_DIR`.
  - Kayıt **sınıf taşımaz**; sınıf skorlamada hesaplanır.
  - Bugünkü 7 arz RETRO olduğu halde kayıtları yazılır (bilgi satırları onlardan okunur; §13-12).
- **K-LB-3 · Mükerrer kayıt yok.** INDEX_POST_BREAK sha'sı, D_1..D_b bülten sha'ları ve girdi dosyası sha'sı aynı olan bir kayıt varsa yeni kayıt yazılmaz (`write_record` kalıbı).
  - Kod değişince yeni kayıt yazılmaz. Parite denetimi bellekte yapılır: skorlama birincil kaydın tahminini yeniden üretir ve kayıtla karşılaştırır; |Δ| > 1e-12 ise `ScoringError`.
  - Şartname §9.3 "sonrakiler parite denetimi" ile amaç aynı, dosya kirliliği yok; SPEC_DEVIATIONS N'ye yazılır.
  - İkinci `--break` koşusu 0 yeni kayıt yazar (testli).
- **K-LB-4 · Kayıt bekçisi.** Yeni `registry.post_break_record_problems(rec, manifest)` (D_b kaydın kendisinden):
  - h > b sonuç anahtarı yok;
  - bülten atıfları ve sha'lar yalnız D_1..D_b günlerinin pinli değerleri; D_b sonrası hiçbir bültenin adı ya da sha'sı yok;
  - `streak.sessions` h = 1..b, tarihler takvim sırasında.

  Ortak yardımcılar (`_walk`, `_H_KEY`, `_BULLETIN_NAME`, `_SHA`) kullanılır. **`post_d1_record_problems` değişmez** (şartnamedeki genelleştirme yerine ayrı fonksiyon; bekçinin POST_D1 davranışı bit-eşit kalır). SPEC_DEVIATIONS N.
- **K-LB-5 · Sonuç-giriş commit'i.** Yeni `scoring.outcome_ingest_commit_after(git, ticker, day, h_min)`: min(tarihi > `day` olan ilk THB/THM'yi ekleyen commit, `data/outcomes/<T>.csv`'ye h ≥ `h_min` için OK/NA_LIMIT satırını ilk yazan commit).
  - Kırılma için `day = D_b`, `h_min = b + 1`.
  - **`outcome_ingest_commit_post_d1` değişmez.** §13-11(f) testi: 7 gerçek arzda ve sentetik depoda `outcome_ingest_commit_after(day = D_1, h_min = 2)` == `outcome_ingest_commit_post_d1` (bit-eşit commit).
- **K-LB-6 · Sınıf.** `predict_break.class_break` (saf formül, N12) + git kanıtları:
  - `model_prospective` = `commit_frozen(m)` ingest commit'inin atası VE push kanıtı var;
  - `record_live` v0'da hep False (insan kaydı üreticisi yok);
  - `inputs_pit_ok` = `registry.inputs_pit_problems(inputs)` boş VE bekçi temiz VE bülten sha'ları MANIFEST'e ve dosyaya eşit.

  Ölçek `live_break`; satırlar MACHINE_SEQUENCED ∪ LIVE; RETRO yalnız `retro_info`'ya gider. `ScaleMixError`: başka ölçekle birleştirme reddedilir (`merge_scales`).
- **K-LB-7 · Karşılaştırıcılar (canlı).**
  - `@ZERO` = donmuş `@ZERO` JSON'unun oranı;
  - `base_floor_by_type` = donmuş `comparators.by_type_F1` sınıf oranı;
  - `PRODUCT_BREAK_FLOOR` = arzın birincil listeleme öncesi kaydındaki `ceiling_path_v0` (yoksa `@INF`) çıktısı ve dondurulmuş hücreleriyle `predict_break.product_break_floor`; kayıtta yoksa `NOT_AVAILABLE` (bugün 7/7).

  Hücreler §5.2 (birincil F1 − ürün; F1 − `@ZERO`; F2 ikisi; F1 − by_type), satır başına eşleşik; karşılaştırıcısı olmayan çift o hücreden düşer.
- **K-LB-8 · Payda ve küçük n** (§9.3 aynen):
  - Payda sırası: RETRO → STREAK_PENDING → NOT_SCORABLE_STREAK_NA → NOT_APPLICABLE_NO_BREAK → NOT_APPLICABLE_B10 → BULLETIN_NOT_PINNED → INPUTS_NOT_AVAILABLE → CALENDAR_NOT_AVAILABLE → satır.
  - Sayaçlar ve özdeşlik testi.
  - n < 10: yalnız satır tablosu; 10 ≤ n < 30: "yetersiz örnek"; "geçiyor" yalnız n ≥ 30 ve aralık 0'ı dışlarsa.
  - Rejim kırılımı (`FON_KRIZI_2026`) ve kalibrasyon `descriptive`.
- **K-LB-9 · Sıra bekçisi (K-GUARD).** `scoring.sequence_violations`'a INDEX_POST_BREAK model dosyaları POST_D1 dalıyla **aynı kuralla** eklenir (yalnız ekleme). `tests/test_outcome_guard.py`'ye yalnız **yeni** testler eklenir; var olan bekçi testlerinin hiçbir satırı değişmez.
- **K-LB-10 · Kanıt.** Bu görevin commit'leri sıra iddiası taşımaz (makine kaydının sınıfı yazılma zamanına bağlı değil) → push kanıtı gerekmez, düz push.

## Önceden onaylı pin güncellemeleri (K-PIN-L)
Proje sahibi başlatma cümlesinde onaylar. Kural FAZ8_FREEZE K-PIN'in devamıdır:
- **`test_5c`:** `scoring.py`, `registry.py`, `freeze.py` farkı yalnız konusu `BORSAI_FAZ8_FREEZE_K:` ya da `BORSAI_FAZ8_LIVE_A:` ile başlayan commit'lerden gelebilir (`_freeze_k_ref` genelleştirilir). `specs.py` bu görevde değişmez; değişmesi gerekirse yalnız ekleme olur, silme yasağı sürer.
- **`test_b7`:** `registry` ve `scores` için fark yalnız **eklenen** dosyalar olabilir: `registry/post_break/**` ve `scores/scores_break.json` (diff-filter=A); başka hiçbir dosya değişmez. Dondurma dosyaları ayağı aynen kalır.
- **Kapsam:** bu iki test ve adım 0b provasında bulunan **aynı türden** iddialar ("dosya değişmedi" / "dizin farkı boş").
- **Kapsam dışı; kırmızı olursa DUR:**
  - var olan `test_outcome_guard` satırları, `test_faz7_vault`, `test_scoring` içerik pinleri, N19 istisnası;
  - kasa/sıra/hijyen bekçilerinin mevcut iddiaları;
  - herhangi bir mantık değişikliği.

## İzinli izlenmeyen
Yalnız bu görev dosyası (`docs/prompts/FAZ8_LIVE_BREAK.md`). Başka bir şey varsa DUR.

## Paralel
Yok (repoda başka oturum koşmaz).

## ÖNCE OKU
- `CLAUDE.md` (kural 1'in POST_BREAK cümlesi)
- `docs/specs_faz8/SPEC_BREAK_V0.md` §5, §8, §9, §11, §13 (11–13 ve sözde kodun "canlı" bölümü)
- `docs/faz8/IMPL_RAPOR.md` §13; `docs/faz8/FREEZE_RAPOR.md`; `docs/fable_faz8_audit/AUDIT.md` §8
- `docs/SPEC_DEVIATIONS.md` H (POST_D1), I39, N
- `borsai/scoring.py`: `outcome_ingest_commit_post_d1` … `build_post_d1_scores`, `main_oot`, `main`, `sequence_violations`, `merge_scales`, `ScaleMixError`, `model_evidence`, `proof_time`
- `borsai/freeze.py`: `build_oot_post_d1_record`, `write_oot_post_d1_record`, `write_record`, `_write_new`, `record_filename`, `INDEX_POST_BREAK_NAME`
- `borsai/registry.py`: `post_d1_record_problems`, `t_open`, `inputs_pit_problems`
- `borsai/predict_break.py` (tamamı); `borsai/outcomes.py`: `local_bulletin`, `ThbRow`, `ThmRow`, `read_manifest`
- `tests/test_outcome_guard.py`, `tests/test_faz5_live.py` (POST_D1 sınıf testleri), `tests/test_faz6_s6.py` (main ve belge kalıbı), `tests/test_faz8_*.py`, `tests/faz8_support.py`
- `docs/faz5/POST_D1_AKISI.md` (akış belgesi kalıbı)

## Adımlar
0. **Taban**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3`: HEAD `fd88be3`. `git status --porcelain --untracked-files=all`: yalnız bu görev dosyası.
   - Paralel pytest, `bash app/scripts/test.sh`, `gen_golden --check`. Beklenen: 921 passed (kasa testi `test_real_scores_oot_in_memory_run_equals_committed_file` temiz ağaçta yeşil olmalı); test.sh yeşil; 35/0. Kırmızı varsa DUR.
   - Sayılar `docs/faz8/live_test_runs.txt`'ye.

0b. **Prova** (geçici klon; repo dışında; `.venv` bağlı; FAZ8_FREEZE kalıbı)
   - Klonda A'nın kodunu yaz, commit et, `--break`'i koş, çıktıları commit et, tam paralel pytest ve `test.sh` koş.
   - Kırmızıları sınıfla: (i) K-PIN-L türü; (ii) kod hatası (düzelt); (iii) başka → DUR, ana repoda hiçbir şey commit etmeden raporla.
   - Klonu sonda sil. Özeti `live_test_runs.txt`'ye yaz.

1. **A: kod ve sentetik testler** (gerçek çıktı yok: `registry/post_break/` ve `scores_break.json` repoda oluşmaz)
   - K-LB-1..9 kodu: `borsai/scoring.py`, `borsai/freeze.py`, `borsai/registry.py`. Windows: `Path`, sabit yol yok.
   - Yeni `tests/test_faz8_live.py`. Sentetik depo ve sentetik bültenlerle (`faz5_live_support` / `faz6_support` kalıpları) sınanacaklar:
     - **§13-11 sınıf:**
       - (a) model → D_b bülteni → D_{b+1} bülteni ⇒ MACHINE_SEQUENCED;
       - (b) D_{b+1} bülteni modelden önce ⇒ RETRO;
       - (c) push kanıtı yok ⇒ RETRO;
       - (d) `shares_offered` PIT değil ⇒ RETRO;
       - (e) LIVE formülü (saf);
       - (f) K-LB-5 paritesi;
       - (g) bekçi: h > b anahtarı, D_b sonrası bülten adı ya da sha'sı → kırmızı. Mutasyon: bekçi kapatılınca test kırmızı.
     - **§13-12:** payda özdeşliği; STREAK_PENDING (seri sürüyor), NO_BREAK (L = 10), B10, BULLETIN_NOT_PINNED, INPUTS_NOT_AVAILABLE dalları; b = 9 → F2 yok.
     - **§13-13:** `live_break` hücresini başka ölçekle birleştirmek `ScaleMixError` verir; "geçiyor" yalnız n ≥ 30 ve aralık 0'ı dışlarsa (sentetik skor satırları); "ön eleme" etiketi.
     - **K-LB-3:** ikinci yazım 0 kayıt; kayıt p'si bozulunca `ScoringError`.
     - **Kayıt şeması:** alanlar, `exposure_class`, `models_index` sha'sı; `@ZERO` kırılma alanlarını okumaz.
     - **K-LB-9:** sıra bekçisinde POST_BREAK dalı. Sentetik: paralel dalda model → ihlal; önce/sonra → temiz. Bu testler `tests/test_outcome_guard.py`'ye yalnız ekleme olarak yazılır.
   - K-PIN-L güncellemeleri.
   - SPEC_DEVIATIONS N'ye ekleme (N26'dan başlayarak): K-LB-1 (ayrı belge), K-LB-3 (mükerrer yok, bellekte parite), K-LB-4 (ayrı bekçi), K-LB-5 (yeni fonksiyon, post_d1 değişmedi), K-LB-7 (ürün NOT_AVAILABLE nedeni), K-PIN-L.
   - Kasa testi hariç paralel pytest; `test.sh`; `gen_golden` → **commit A**. Hemen ardından kasa testini tek başına koş (yeşil olmalı).

2. **B: gerçek koşu** (HEAD = A, ağaç temiz)
   - `.venv/bin/python -m borsai.scoring --break`
   - Beklenen:
     - `registry/post_break/<T>/` altında tam olarak 7 kayıt (arz başına bir);
     - `scores/scores_break.json`;
     - `docs/SCORES_BREAK.md`;
     - başka hiçbir dosya değişmez (`git status` ile göster).
   - Değerler "Beklenen sayılar" tablosuyla karşılaştırılır (|Δp| ≤ 1e-12; b, D_b, b_floor birebir). Fark varsa çıktıları COMMIT ETME, DUR ve farkın nedenini raporla.
   - Komutu ikinci kez koş: 0 yeni kayıt; `scores_break.json` yalnız `generated_at_utc` ve `code` alanlarında farklı olabilir (göster).
   - Gerçek dosya testleri (`tests/test_faz8_live.py`'ye ek):
     - 7 kayıt bekçiden temiz geçiyor;
     - 7/7 RETRO, `n_scored` 0;
     - payda özdeşliği;
     - NETGL satırı b = 4, `b_floor` = 1, `FON_KRIZI_2026`;
     - ürün NOT_AVAILABLE 7/7;
     - `SCORES_BREAK.md` = yazılmış JSON'un render'ı.
   - `docs/faz8/POST_BREAK_AKISI.md` (kısa, `POST_D1_AKISI.md` kalıbı): yeni arzda kırılma akşamından sonra hangi komut, ne zaman, ne commit'lenir. Akşam iş yükü yok; `outcomes update` sonrası `--break`. Push kanıtı gerekmez.
   - Paralel pytest, `test.sh`, `gen_golden` → **commit B**.

3. **Son kabul** (B commit'inden sonra, **deselect'siz, sıralı**): `.venv/bin/pytest -q`, `test.sh`, `gen_golden --check`. Kırmızıysa DUR; amend yok.

4. **R: rapor.** `docs/faz8/LIVE_RAPOR.md` ve `live_test_runs.txt` → **commit R**.

## Beklenen sayılar (orkestratör; donmuş JSON + stdlib `predict_break`; bütün arzlar RETRO)
| Arz | D_1 | L | b | D_b | b_floor | p_F1 | p_F2 | Not |
|---|---|---|---|---|---|---|---|---|
| CITAS | 2026-08-18 | 5 | 6 | 2026-08-25 | 0 | 0.13833264286466687 | 0.09464223345801025 | |
| TKNKA | 2026-08-20 | 7 | 8 | 2026-08-31 | 0 | 0.13817491254287276 | 0.09521214961923939 | |
| VEYAS | 2026-08-20 | 0 | 1 | 2026-08-20 | 0 | 0.1376436522563838 | 0.09715847417357594 | |
| KPEKS | 2026-08-21 | 5 | 6 | 2026-08-28 | 1 | 0.5389117003850694 | 0.16401056260438845 | |
| INTET | 2026-09-01 | 4 | 5 | 2026-09-07 | 0 | 0.14182539930275256 | 0.08290496022647753 | |
| BKRGY | 2026-09-02 | 0 | 1 | 2026-09-02 | 1 | 0.5432679533511754 | 0.15231130173471372 | |
| NETGL | 2026-09-17 | 3 | 4 | 2026-09-22 | 1 | 0.4990578357497034 | 0.30432770420243327 | `FON_KRIZI_2026`; `B_TURNOVER_CLIPPED_TO_TRAINING_P05_P95` |

- `@ZERO`: F1 0.3048780487804878, F2 0.14102564102564102. `by_type_F1`: sınıf 0 → 0.1276595744680851, sınıf 1 → 0.5428571428571428.
- Sınıf 7/7 RETRO (model `4d3c9a2`, bütün sonuçlardan sonra donduruldu). `n_scored` = `n_machine` = `n_live` = 0; `retro_info` 7; payda 7 satır, hepsi RETRO.
- Ürün 7/7 NOT_AVAILABLE (Bağlam 7).
- pytest: taban 921; A, B ve son kabulde 921 + yeni testler (sayıyı raporla).

## Tek oturumda bitmezse
- A yeşil ve commit'liyse orada durulabilir. B ancak HEAD = A ve temiz ağaçta koşulur.
- Aynı pencerede "devam" ile sürer.

## Kurallar
- **DEĞİŞMEZ:**
  - `models/`;
  - `scores/scores.json`, `scores_post_d1.json`, `scores_oot.json`, `docs/SCORES.md`, `docs/SCORES_OOT.md`, `docs/MODELS.md`;
  - `registry/` (`post_break/` hariç), `data/`, `app/`, `legacy/`, `CLAUDE.md`, `experiments/log.jsonl`;
  - `docs/specs*`, `docs/fable_faz8_audit/`, `docs/faz8/backtest/`, `tests/reference/`;
  - `borsai/` içinde `scoring.py`, `freeze.py`, `registry.py` dışındaki her şey (`predict_break.py`, `post_break.py`, `outcomes.py`, `specs.py` dahil).
- **Yazılabilir:**
  - A'da: `borsai/scoring.py`, `borsai/freeze.py`, `borsai/registry.py`, `tests/`, `docs/SPEC_DEVIATIONS.md` (N'ye ekleme), `docs/faz8/` (`backtest/` hariç), bu görev dosyası.
  - B'de: `registry/post_break/**`, `scores/scores_break.json`, `docs/SCORES_BREAK.md`, `tests/`, `docs/faz8/`.
  - R'de: `docs/faz8/`.
- Model ve skor tanımı şartnamedekidir. Uyuşmazlık bulursan çıktıları commit etme, DUR.
- Belgelere ve raporlara `thb`/`thm` + 8 haneli tarih kalıbı ve kasa üyesi kodu yazılmaz. Makine kayıtları bülten atfı taşır (POST_D1 kaydı kalıbı; bekçi denetler); bu kural kayıtlar için değildir.
- Kasa testi (`test_real_scores_oot_in_memory_run_equals_committed_file`) commit'siz `borsai/` ile tanımı gereği kırmızıdır. Bu yüzden yalnız A öncesi koşudan ayrılır, A commit'inden hemen sonra tek başına koşulur, son kabulde ayrılmaz. Başka hiçbir bekçi ayrılmaz.
- Proje sahibine karar sorman gerekirse soruyu ve seçenekleri açıkça yaz. Proje sahibi orkestratöre danışarak cevaplayacak.
- `git add -A` yok. Commit'ler:
  ```
  git add borsai/scoring.py borsai/freeze.py borsai/registry.py tests docs/SPEC_DEVIATIONS.md docs/faz8 docs/prompts/FAZ8_LIVE_BREAK.md
  git commit -m "BORSAI_FAZ8_LIVE_A: POST_BREAK live stage code before outputs (machine record writer and guard, outcome_ingest_commit_after, class_break evidence, scores_break.json builder and SCORES_BREAK.md via scoring --break, sequence guard for INDEX_POST_BREAK), synthetic tests (spec 13-11..13), pre-approved pin updates (K-PIN-L), SPEC_DEVIATIONS N26+" -- borsai/scoring.py borsai/freeze.py borsai/registry.py tests docs/SPEC_DEVIATIONS.md docs/faz8 docs/prompts/FAZ8_LIVE_BREAK.md
  git add registry/post_break scores/scores_break.json docs/SCORES_BREAK.md tests docs/faz8
  git commit -m "BORSAI_FAZ8_LIVE_B: first scoring --break run (7 machine records, all RETRO; scores/scores_break.json live_break n_scored 0; docs/SCORES_BREAK.md), real-file tests, POST_BREAK flow note" -- registry/post_break scores/scores_break.json docs/SCORES_BREAK.md tests docs/faz8
  git add docs/faz8
  git commit -m "BORSAI_FAZ8_LIVE_REPORT: live-stage report and test runs" -- docs/faz8
  ```
  Değişmeyen bir yol pathspec'te hata verirse o yolu çıkar. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Push yok. Rapor Türkçe.

## Teslim (rapor)
Raporu sohbete ve `docs/faz8/LIVE_RAPOR.md`'ye yaz:
- A, B, R hash'leri ve sıra; `git show --stat`.
- Prova: kırmızı liste ve sınıflaması.
- K-PIN-L: her test için tek satır (hangi iddia, önce/sonra).
- 7 makine kaydı: dosya adı, sha256, b, D_b, b_floor, p_F1, p_F2, uyarılar; beklenen tabloyla fark.
- `scores_break.json` özeti (sayaçlar, payda, `retro_info`); ikinci koşunun farkı.
- Test sayıları: taban, A öncesi, A sonrası kasa testi, B öncesi, son kabul (sayı, süre); `test.sh` ve `gen_golden`.
- Sapmalar (N26+).
- Yeni arz geldiğinde kırılma akşamı için tek satırlık komut.

## Kabul kapısı
- **K1** `--break` 7 kaydı yazdı; değerler beklenen tabloyla |Δp| ≤ 1e-12, b/D_b/b_floor birebir; ikinci koşu 0 kayıt.
- **K2** 7/7 RETRO, `n_scored` 0, payda özdeşliği tutuyor; NETGL b = 4, `b_floor` = 1.
- **K3** §13-11 (a)–(g), §13-12, §13-13 testleri var ve yeşil; bekçi mutasyonu kırmızı. `post_d1_record_problems` ve `outcome_ingest_commit_post_d1` değişmedi (diff boş).
- **K4** Bayraksız `main()` aynı. `scores.json`, `scores_post_d1.json`, `SCORES.md`, `models/`, `app/` değişmedi.
- **K5** Son kabul (deselect'siz, sıralı) yeşil; `test.sh` ve `gen_golden` yeşil. Pin değişiklikleri yalnız K-PIN-L ve K-GUARD kuralıyla yapıldı. Commit'ler izinli yollarda; push yok.

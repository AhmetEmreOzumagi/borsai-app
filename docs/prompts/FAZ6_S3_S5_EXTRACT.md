# TASK_ID: BORSAI_FAZ6_S3_S5_EXTRACT_20260925

Model: Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi. **Ağ: yalnız `www.borsaistanbul.com` THB/THM bülten URL'leri (`outcomes.source_url`; HEAD probu + zip indirme), yalnız karantinaya** (`~/Desktop/BorsAi_quarantine`, repo dışı). Başka site yok. push/tag/amend yok.

**İki bölüm:** A (S3: D_1 satırları + post_d1 kayıtları) ve B (S5: D_1…D_10 satırları). Arada proje sahibi push + push kanıtı yapar. **Bölüm A bitince oturum biter, beklemez.** Bölüm B, proje sahibi aynı cümleyle yeni oturum açınca başlar; adım 0 hangi bölümde olunduğunu diskten ölçer:
- C commit'i (`BORSAI_FAZ6_S3_CODE`) yoksa → Bölüm A.
- RA commit'i (`BORSAI_FAZ6_S3_REPORT`) var ve S3a/S3b'nin push kanıtları repoda → Bölüm B.
- RA var ama kanıt yok → DUR; rapordaki push bloğunu proje sahibine hatırlat.
- Arada bir yerdeyse → "Tek oturumda bitmezse" bölümü.

## Bağlam
- S2: 135 × 19 kayıt `1dcceff`, push kanıtı 2026-09-24T22:39:24Z (`f57ce50`). Proje sahibinin terminalinde `s2_gate_problems() == []`.
- Altyapı `1d4913e` + denetim düzeltmesi `40db62c`: karantina, indirme kapısı, ayıklayıcı (`borsai/outcomes_oot.py`), `freeze --oot-post-d1`, bekçiler. Hiçbiri gerçek veriyle çağrılmadı.
- **KARARLAR D6** (bağlayıcı; şartnamenin S3/S5 ve G5'inin yerine):
  - Kohort penceresinin bültenleri repoya girmez.
  - Yalnız açık kümenin (OPEN ∪ EXPOSED_*, 71 üye) `<T>.E` satırları, yalnız o üyenin D_1…D_10'u makineyle ayıklanır.
  - SEALED (64 üye) satırları hiçbir dosyaya, günlüğe ya da ekrana yazılmaz.
  - Repoya satırlar + zip pinleri (`MANIFEST_OOT.csv`) girer; `outcome_basis = MACHINE_EXTRACTED`.
- **D5:** post_d1 kayıtları `MACHINE_SEQUENCED`, ayrı alt tablo.
- **Sınıf formülü** (`scoring.class_oot`; SPEC_DEVIATIONS I10, I13):
  - Listeleme öncesi modeller için sonuç girişi = `d1_rows/<T>.json`'u ya da `outcomes_oot`'u ekleyen ilk commit.
  - `post_d1_hazard_v0` için = D_1 sonrası sonuç (d1_rows hariç; o modelin girdisi).
  - Kaydın push kanıtı, sonuç commit'inin kanıtından ÖNCE olmalı. Değilse OOT_RETRO.
  - Bu yüzden sıra zorunlu: **C → S3a (d1_rows) → S3b (post_d1 kayıtları) → push + kanıt → S5 → push + kanıt.**
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Bu görev hiçbir modeli, şartnameyi, girdiyi ya da S2 kaydını değiştirmez.
- **Sonuç hijyeni:**
  - Rapora, ekrana ve eklere yalnız SAYI yazılır (dosya, durum, eşleşme sayıları).
  - Hiçbir üyenin fiyat, getiri, limit ya da tavan değeri yazılmaz; bir üyenin satırı ekrana basılmaz.
  - Hangi kodun SEALED olduğu yazılmaz. Bir bekçi testi kırmızı olur ve çıktısında bir kod görünürse o çıktı rapora yapıştırılmaz.
  - `docs/faz6/dogrulama/EXPOSURE.md` §3 okunmaz.

## Orkestratörün ölçtükleri (2026-09-25 ~02:00)
- HEAD = origin/main = `f57ce50`, ağaç temiz. pytest tabanı 598 (S2_RAPOR §4).
- Kohort 135 MEMBER; açık küme 71, SEALED 64. Açık kümede f3'süz 3 üye (INFRA_RAPOR §6: f3 modelleri açık kümede 68/71).
- Açık kümenin 71 ilk işlem günü 68 farklı tarihe düşüyor. Takvim C ile ilk 10 seans yaklaşık 447 farklı tarih; 4 üyenin penceresi 2023-09-22 sonrasına (H99 takvimine) taşıyor. Beklenen indirme: S3 ≈ 140 zip, toplam ≈ 900 zip.
- `extract_d1_rows` var olan `d1_rows/<T>.json`'da `FileExistsError` verir (F6 kalıntısı). `fetch_quarantine`, `append_manifest_oot` ve `write_outcome_oot` yeniden koşuya dayanıklı.
- `outcomes.download_bytes` indirmeler arasında beklemiyor (yalnız hatadan sonra geri çekiliyor).
- `outcomes_oot`'un CLI'si yok.
- `freeze --oot-post-d1 <T>` tek arz içindir. f3'süz arzda kayıt REFUSED durumuyla yazılır (hata vermez). D1 tavan değilse NOT_APPLICABLE.
- Uygulamanın altın MANIFEST'i yalnız `predict*`, `features`, `horizons`, `survival` kaynaklarını pinler; bu görevin dokunduğu dosyalar onun dışında.

## Görev kararları (SPEC_DEVIATIONS bölüm I'ye I28… olarak yazılır)
- **T1 (F6 kalıntısı):** `extract_d1_rows` yeniden koşuya dayanıklı olur. Dosya varsa ve baytları yeni belgeyle aynıysa atlar (`UNCHANGED`); farklıysa `OotOutcomeError` (DUR). Önce kırmızı test.
- **T2: CLI** `python -m borsai.outcomes_oot {probe|s3|s3-post-d1|s5}`.
  - Seçenekler: `--pace SANİYE` (varsayılan 0.5; yalnız gerçek ağ indirmesinden önce bekler, karantinadan okuma beklemez) ve `--quarantine YOL`.
  - Çıktı yalnız sayılar (JSON). Ayıklama davranışı değişmez.
  - `probe`: `download_gate` + `check_xu100_gap_closures`. Çıktı: 5 tarih ve sonuç.
  - `s3`: `extract_d1_rows`. Çıktı: yazılan / aynı / toplam, D_1 ≠ first_trading_date sayısı.
  - `s3-post-d1`: `registry/oot/d1_rows/*.json`'daki her dosya için `freeze.write_oot_post_d1_record`. `DuplicateRecord` → "zaten var" (sayılır). Başka her `FreezeError` → DUR. Çıktı: yazılan / zaten var, PREDICTED / REFUSED / NOT_APPLICABLE sayıları, ret ve uygulanamazlık kodlarının sayıları.
  - `s5`: önce `s3_gate_problems()` (T3). Boş değilse hiçbir bülten indirilmez (`GateError`). Sonra `extract_open_members`. Çıktı: action sayıları, `n_sessions` dağılımı, `sealed_not_opened`.
- **T3: S5 kapısı** `s3_gate_problems(root, proofs)`. Her açık üye için:
  - `d1_rows/<T>.json` izleniyor, değişmemiş, onu ekleyen commit'in push kanıtı var, `d1_rows_problems == []`;
  - `registry/oot/post_d1/<T>/` altında etkin bir kayıt var, izleniyor, değişmemiş, push kanıtlı.
  - Neden: post_d1 kaydı D_2+ sonuçtan önce push kanıtlı değilse `class_oot` onu OOT_RETRO sayar ve post_d1'in eski kohort testi kaybolur.
  - Testler: eksik kanıt → sorun listelenir; tam → `[]`. Mutasyon: kanıt denetimi ya da post_d1 denetimi kaldırılınca test kırmızı. `s5`'in kapıyı çağırdığı da test edilir (kapı sorun dönerse `extract_open_members` çağrılmaz).
- **T4:** post_d1 kaydı, d1_rows'u olan HER açık üye için yazılır (REFUSED ve NOT_APPLICABLE dahil; hiçbiri atlanmaz). Canlıdaki "f3 yoksa kayıt yok" burada uygulanmaz: payda tam kalır, skorlama yalnız SCORED satırı kullanır.
- **T5: Bağımsız ham alan denetimi.** `borsai` import etmeyen bir betik (repo dışında çalışır, ör. `/tmp/borsai_s3s5/`) karantinadaki zip'leri doğrudan açar ve yalnız açık küme kodlarının satırlarına bakar; SEALED kodları hiç aramaz. Karşılaştırır:
  - d1_rows `fields_raw` (14 alan) ↔ D_1 zip satırı;
  - S5 CSV'lerinde `close_raw`, `upper_limit_raw`, `reference_raw`, `trade_count_raw` ↔ ilgili seansın zip satırı;
  - `thb_sha256` / `thm_sha256` ↔ karantina dosyası ↔ `MANIFEST_OOT.csv`;
  - `ceiling_close` ↔ (kapanış == üst limit, Decimal);
  - h ∈ {1, 3, 5, 10} için `R_h` ↔ kapanış / arz fiyatı − 1 (|Δ| ≤ 1e-12).
  
  Çıktı yalnız sayılar. Betik (değer içermez) ve sayı çıktısı `docs/faz6/ekler/s3_s5_bagimsiz*.{py,txt}` olarak kopyalanır.
- **T6: Ağ ve veri hatası kuralları.**
  - `probe`'da 5 tarihten birinin THB'si yayımlanmışsa (`CalendarConflict`) DUR. İndirme yok; Takvim C yeni dosya sürümüyle düzeltilir (ayrı görev).
  - HEAD 200 ya da 404 dışında bir kod dönerse DUR. GET ile deneme yok. Rapora yalnız durum kodu, Content-Type ve Content-Length.
  - Takvimde seans olan bir gün için bülten 404 (`NotPublished`) → DUR, tarihi yaz (takvimde eksik kapanış olabilir).
  - Bir kod ilk işlem gününden sonra 15 seansta görünmezse (`OotOutcomeError`) → DUR, açık üyenin kodunu ve nedeni yaz.
  - Geçici ağ hatası (3 deneme sonrası): komutu yeniden koş; karantina önbellektir.
  - Karantinada manifest satırı olmayan bir zip kalırsa (yarıda kesilmiş yazma): o tek dosyayı `~/Desktop/BorsAi_quarantine/_orphans/`'a taşı, yeniden koş, rapora yaz.

## Paralel
Bu görev koşarken başka oturum yok. Proje sahibi bu sırada git komutu çalıştırmaz.

## İzinli izlenmeyen
- Bölüm A başında yalnız `docs/prompts/FAZ6_S3_S5_EXTRACT.md`.
- Bölüm B başında hiçbiri (ağaç temiz).
- Başka bir şey varsa DUR.

ÖNCE OKU: CLAUDE.md; docs/specs_faz6/KARARLAR.md (D5, D6); docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md (§1 D_1 kuralı, §2); docs/SPEC_DEVIATIONS.md bölüm I (I10, I13, I15–I17, I22, I23, I25); docs/faz6/INFRA_RAPOR.md §9; docs/faz6/S2_RAPOR.md §5–§7; docs/fable_faz6_audit/AUDIT.md §8, §10; borsai/outcomes_oot.py (tamamı); borsai/freeze.py (`build_oot_post_d1_record`, `write_oot_post_d1_record`, `run_post_d1_model`); borsai/scoring.py (`oot_ingest_commit`, `cohort_gate_ok`, `class_oot`, `oot_post_d1_block`); tests/test_faz6_oot.py; tests/test_outcome_guard.py (eski kohort bölümü).

## Bölüm A (S3)
0. **Taban.**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3` → HEAD `f57ce50`. `git status --porcelain` → yalnız görev dosyası.
   - `.venv/bin/python -c "from borsai import outcomes_oot as oo; print(oo.s2_gate_problems())"` → `[]`.
   - Karantina dizini yok ya da boş olmalı. Doluysa dosya ve MANIFEST satır sayısını rapora yaz; her dosyanın sha'sı manifestle eşleşmeli, değilse DUR.
   - Tam `.venv/bin/pytest -q` (598 geçti), `bash app/scripts/test.sh` (yeşil), `app/parity/gen_golden.py --check` (S2 görevindeki gibi; fark yok). Sayılar `docs/faz6/ekler/s3_s5_test_runs.txt`'ye.
1. **Kod (commit C).** T1, T2, T3 ve testleri `tests/test_faz6_oot.py`'ye (sentetik, ağ yok).
   - T1 testi önce kırmızı gösterilir.
   - T3 mutasyon gösterimi: çıktı `docs/faz6/ekler/s3_s5_mutasyon.txt`.
   - SPEC_DEVIATIONS I28… (T1–T6).
   - Tam pytest + test.sh yeşil → **commit C**.
2. **Prob (ilk ağ işi):** `.venv/bin/python -m borsai.outcomes_oot probe`. 5 tarihin hepsi yayımlanmamış olmalı; değilse T6 → DUR.
3. **S3a:** `.venv/bin/python -m borsai.outcomes_oot s3`. Beklenen:

   | Denetim | Beklenen |
   |---|---|
   | `registry/oot/d1_rows/*.json` | 71 dosya, hepsi açık küme üyesi; SEALED 0 |
   | her dosya | `d1_rows_problems == []`, `exposure_class = MACHINE_SEQUENCED`, `session_h = 1` |
   | `data/raw/bist/MANIFEST_OOT.csv` | satır = 2 × (farklı D_1 tarihi sayısı); her sha karantina dosyasıyla eşit |
   | D_1 | her üyede D_1 ≥ first_trading_date; D_1 ≠ first_trading_date sayısı rapora |
   | T5 (d1_rows) | 71 × 14 alan zip satırıyla eşit; 0 fark |
   | sızıntı | SEALED kodların hiçbiri yeni dosyalarda yok (`test_sealed_codes_absent_from_every_extracted_file` yeşil) |

   Tutmazsa commit etme, DUR.
   - **Temizlik yolu.** Yalnız bu yeni dosyalar yüzünden kırmızı olan temizlik bekçileri deselect edilir. Beklenen dört test: `test_faz4_ceiling_path.py::test_new_models_are_retro_with_no_record_and_no_metric`, `test_faz5_post_d1.py::test_14_models_goldens_and_read_only_paths_unchanged`, `test_scoring.py::test_faz4_scores_json_existing_blocks_unchanged`, `test_guardrails.py::test_legacy_and_data_have_no_working_tree_changes`.
   - Deselect'li tam koşu yeşil → **commit S3a** (yalnız `registry/oot/d1_rows` + `data/raw/bist/MANIFEST_OOT.csv`) → deselect'siz tam koşu yeşil.
   - Başka bir kırmızı varsa DUR. Eski kohort bekçileri (`test_oot_*`, `test_sealed_*`, `test_no_cohort_window_*`, `test_cohort_*`) asla deselect edilmez, gevşetilmez.
4. **S3b:** `.venv/bin/python -m borsai.outcomes_oot s3-post-d1`. Beklenen:
   - `registry/oot/post_d1/<T>/` altında 71 kayıt; her biri `borsai.oot_post_d1_record/1`, `MACHINE_SEQUENCED`, `code.git_head` = S3a, `borsai_dirty = false`.
   - `d1_rows.sha256` dosyanın kanonik sha'sına eşit; `base_record` o üyenin S2 kaydı.
   - f3 eksikliğiyle REFUSED olan kayıtların üye kümesi = S2 kaydında `ceiling_hazard_v0` hücresi REFUSED olan açık üyeler (3), birebir.
   - PREDICTED / REFUSED / NOT_APPLICABLE sayıları rapora.
   - Aynı temizlik yolu → **commit S3b** (yalnız `registry/oot/post_d1`) → deselect'siz tam koşu + test.sh yeşil.
5. **Rapor** `docs/faz6/S3_S5_RAPOR.md` Bölüm A (commit RA): C, S3a, S3b hash'leri; prob sonucu; S3 tablosu; post_d1 durum sayıları; T5 sayıları; test sayıları; mutasyon; proje sahibi için aşağıdaki push bloğu (hash'ler doldurulmuş). **Oturum burada biter; S5'e geçme.**

   ```
   cd ~/Desktop/BorsAi
   git push origin main
   .venv/bin/python -m borsai.push_proof <S3a> <S3b>
   git add registry/push_proofs
   git commit -m "BORSAI_PUSH_PROOFS: Faz 6 S3 d1_rows (<S3a>) and post_d1 records (<S3b>)" -- registry/push_proofs
   git push origin main
   git --no-pager log --oneline -3 origin/main
   ```

## Bölüm B (S5)
0. **Taban.**
   - Ağaç temiz. HEAD, RA'nın ve S3 kanıt commit'inin torunu. `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -1 origin/main` = HEAD.
   - `.venv/bin/python -c "from borsai import outcomes_oot as oo; print(oo.s2_gate_problems(), oo.s3_gate_problems())"` → `[] []`. Değilse DUR; S5'e başlama.
   - Tam pytest + test.sh yeşil (sayılar ek dosyaya).
1. **S5:** `.venv/bin/python -m borsai.outcomes_oot s5`. Beklenen:

   | Denetim | Beklenen |
   |---|---|
   | `data/outcomes_oot/<T>.csv` | 71 dosya; her biri 10 satır (h = 1…10); `outcome_basis` hep `MACHINE_EXTRACTED`; `PENDING` 0 |
   | `data/outcomes_oot/raw/<T>.json` | 71; D_10'dan sonra okunmuş seans yok; okunan − çözümlenen seans farkı olan üye sayısı rapora |
   | D_1 tutarlılığı | 71/71 CSV'nin h = 1 seansı = d1_rows D_1'i; D_1 thb/thm sha'ları d1_rows ve MANIFEST_OOT ile eşit |
   | `MANIFEST_OOT.csv` | S3a'daki satırlar bayt olarak aynı ve başta (yalnız ekleme); toplam = 2 × okunan farklı seans; her sha karantinayla eşit |
   | durumlar | 10 seansı olmayan üye sayısı; `TARGET_UNAVAILABLE` ve `NA_LIMIT` satır sayıları rapora (değer yok) |
   | T5 (S5) | bütün satırlarda ham alanlar zip'le eşit; `ceiling_close` ve `R_h` yeniden hesapla eşit; 0 fark |
   | sızıntı | SEALED kod hiçbir yeni dosyada yok; `sealed_not_opened` = 64 |

   Tutmazsa commit etme, DUR. Aynı temizlik yolu → **commit S5** (yalnız `data/outcomes_oot` + `data/raw/bist/MANIFEST_OOT.csv`) → deselect'siz tam pytest + test.sh yeşil.
2. **Rapor** Bölüm B (commit RB): S5 hash'i, tablo sayıları, T5, test sayıları, S6 için notlar ve push bloğu:

   ```
   cd ~/Desktop/BorsAi
   git push origin main
   .venv/bin/python -m borsai.push_proof <S5>
   git add registry/push_proofs
   git commit -m "BORSAI_PUSH_PROOFS: Faz 6 S5 outcome rows (<S5>)" -- registry/push_proofs
   git push origin main
   git --no-pager log --oneline -3 origin/main
   ```
   `scores/` yazılmaz, `scoring.main()` ve `build_oot_scores` bu görevde ÇALIŞTIRILMAZ (S6 ayrı görev).

## Tek oturumda bitmezse
Her komut yeniden koşulabilir: karantina önbellektir; `s3` aynı dosyayı atlar; `s3-post-d1` var olan kaydı "zaten var" sayar; `s5` UNCHANGED yazar. Commit'lenmiş adımı tekrarlama. Nerede kalındığını `git log` ve dosya sayılarıyla ölç. C commit'liyse ve S3 yarımsa, `s3`'ten devam et.

## Kurallar
- **Yazılabilir:**
  - `borsai/outcomes_oot.py` (yalnız T1–T3), `tests/test_faz6_oot.py`, `docs/SPEC_DEVIATIONS.md` (I28…);
  - yalnız CLI ile: `registry/oot/d1_rows/`, `registry/oot/post_d1/`, `data/outcomes_oot/`, `data/raw/bist/MANIFEST_OOT.csv`;
  - `docs/faz6/S3_S5_RAPOR.md`, `docs/faz6/ekler/s3_s5_*`, karantina dizini (repo dışı), bu görev dosyası.
- **Salt okunur:** `models/`, `registry/` (yukarıdaki iki dizin dışı), `data/` (yukarıdakiler dışı), `scores/`, `app/`, `docs/specs*`, `CLAUDE.md`, `legacy/`, diğer `borsai/` dosyaları, `tests/test_outcome_guard.py`.
- Karantinadaki zip'ler ya da iç CSV'leri repoya kopyalanmaz, repo içinde açılmaz. Kohort penceresinden hiçbir bülten dosyası repoda olmaz.
- Ayıklanmış dosyalar ve kayıtlar elle düzenlenmez; hata varsa commit'ten önce DUR.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit'ler:
  ```
  git add borsai/outcomes_oot.py tests/test_faz6_oot.py docs/SPEC_DEVIATIONS.md docs/faz6/ekler/s3_s5_mutasyon.txt docs/prompts/FAZ6_S3_S5_EXTRACT.md
  git commit -m "BORSAI_FAZ6_S3_CODE: idempotent d1_rows extraction (F6), outcomes_oot CLI with pacing, S5 gate on pushed S3 outputs" -- borsai/outcomes_oot.py tests/test_faz6_oot.py docs/SPEC_DEVIATIONS.md docs/faz6/ekler/s3_s5_mutasyon.txt docs/prompts/FAZ6_S3_S5_EXTRACT.md
  git add registry/oot/d1_rows data/raw/bist/MANIFEST_OOT.csv
  git commit -m "BORSAI_FAZ6_S3: D_1 rows of the open set, machine-extracted from quarantined bulletins, with zip pins" -- registry/oot/d1_rows data/raw/bist/MANIFEST_OOT.csv
  git add registry/oot/post_d1
  git commit -m "BORSAI_FAZ6_S3_POST_D1: post_d1_hazard_v0 out-of-time records (MACHINE_SEQUENCED), before any D_2+ row" -- registry/oot/post_d1
  git add docs/faz6/S3_S5_RAPOR.md docs/faz6/ekler
  git commit -m "BORSAI_FAZ6_S3_REPORT: S3 counts and checks" -- docs/faz6/S3_S5_RAPOR.md docs/faz6/ekler
  git add data/outcomes_oot data/raw/bist/MANIFEST_OOT.csv
  git commit -m "BORSAI_FAZ6_S5: D_1..D_10 outcome rows of the open set (MACHINE_EXTRACTED) with zip pins" -- data/outcomes_oot data/raw/bist/MANIFEST_OOT.csv
  git add docs/faz6/S3_S5_RAPOR.md docs/faz6/ekler
  git commit -m "BORSAI_FAZ6_S5_REPORT: S5 counts and checks" -- docs/faz6/S3_S5_RAPOR.md docs/faz6/ekler
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Rapor Türkçe.

## Kabul kapısı
- **KA1** T1 (önce kırmızı), T2, T3 (mutasyonla) testli; C sonrası tam pytest + test.sh yeşil.
- **KA2** Prob: 5 tarih yayımlanmamış.
- **KA3** S3a: 71 d1_rows, MANIFEST pinleri, T5 0 fark. S3b: 71 post_d1 kaydı, f3 REFUSED kümesi birebir. Sıra C → S3a → S3b → RA. push yok.
- **KB1** S5'ten önce `s3_gate_problems() == []` (S3 kanıtları repoda).
- **KB2** S5 tablosu birebir; T5 0 fark; SEALED 0.
- **KB3** S5 commit'i yalnız izinli yollar; deselect'siz tam pytest + test.sh yeşil; push yok.

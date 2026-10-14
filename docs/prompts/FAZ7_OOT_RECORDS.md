# TASK_ID: BORSAI_FAZ7_OOT_RECORDS_20260928

Model: Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ yok. push/tag/amend yok.

## Rol
Kasa açılışından önceki son Python işi. Dört parça:
1. **Model başına kohort kapısı ve kasa skorlama kodu** (sentetik testlerle; gerçek kasa verisi YOK).
2. **Eski kohortun ek kayıtları:** 135 üyenin her biri için yeni 8 modeli (4 tavan serisi v1 + 4 düşen arz) içeren ikinci kayıt.
3. **Skorların yeniden üretimi:** 27 modelli `scores.json`, yakın dönem blokları ve (C) kartlarında aile keşif sayacı.
4. Rapor.

Bundan sonra proje sahibi push eder ve kayıt commit'inin zaman kanıtını alır. Kasa ancak bu kanıttan sonra, ayrı bir görevde, tek seferde açılır.

## Bağlam
- **Donmuş yeni modeller:**
  - `ceiling_hazard_v1_clip/_real/_pooled/_pooled@INF`: `66adbca`, kanıt 2026-09-27T15:30:42Z.
  - `fall_d10_v0_h99/_pooled/_addsale/_pooled@ZERO`: `ce569a8`, kanıt proje sahibinin son push'unda.
  - `models/INDEX.json` 27 giriş.
- **Şartnameler (bağlayıcı):**
  - `docs/specs_faz7/SPEC_HAZARD_V1.md` §7.1 adım 3–5, §7.2, §7.3, §11-10, 11, 12;
  - `docs/specs_faz7_c/SPEC_C_V0.md` §5.2, §7, §11-10; KARARLAR, KARARLAR_C;
  - `docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md` §2 (`class_oot`), §6; KARARLAR D6.
- **Uygulama sözleşmesi:** `docs/app/SPEC_APP_EK3.md` §5.5 (Ö1: `models[].backtest.near_era` şeması) ve §12 (Ö2).
- **Denetim önerisi (Fable, `docs/fable_faz7c_audit/AUDIT.md` F3 ve §3 K10):** keşifte denenen 2 054 varyantın 1 912'si H99 sonuçlarını kullandı. (C) kartlarında ayrı bir **aile keşif sayacı** gösterilir. Orkestratör kabul etti.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Bu görevde hiçbir model davranışı değişmez.
- **Hijyen (sert):**
  - Kasa üyeleri için yalnız listeleme öncesi girdiler okunur (`registry/oot/inputs/<T>.json`, kohort satırının rejim etiketi); sonuç yok, karantina yok, ağ yok.
  - Hangi kodun kasada olduğu hiçbir dosyaya, çıktıya, test adına ya da rapora yazılmaz ve ekrana basılmaz. Kasa denetimleri yalnız sayı basar. Kohort dosyası yalnız betikle okunur; satırı basılmaz.
  - `EXPOSURE.md` dosyaları ve Codex `exposure_log`'ları okunmaz.

## Orkestratör kararları (proje sahibi adına, bağlayıcı)
- **Birincil kayıt kuralı (eski kohort):** o modeli içeren en erken aktif kayıt (SPEC_HAZARD_V1 §7.3).
- **Ek kayıtlar tek koşuda ve tek commit'te:** 8 yeni modelin hepsi; `delta_of` ilk kaydı gösterir.
- **`oot_pre_h99_all` yalnız 19 eski model için;** yeni 8 model için tanımsızdır ve kod bunu birleştirmez (test).
- **Aile keşif sayacı:** üç (C) adayının ve kural satırının kartında `n_exploration_family` (değer: günlükteki `kind: exploration` satır sayısı, bugün 2 054; kaynak `denenenler.csv` sha'sı). Var olan `n_variants_same_data` sayacı değişmez; ikisi yan yana gösterilir. MODELS.md Faz 7C kartı ve SCORES.md aynı sayıyı yazar.
- **Yakın dönem blokları (Ö1):** EK3 §5.5 şeması aynen.
  - v1 için: comparator `ceiling_hazard_v0`, metric RPS, tolerance 0.010.
  - (C) için: comparator `fall_d10_v0_h99`, metric D10 Brier, tolerance 0.008; yalnız `fall_d10_v0_pooled` birincil hücreyi taşır. `h99` ve `addsale` için şartname §5.5 k3'ün "yakın dönem − `base_rate`" hücresi aynı şemada, `comparator: "base_rate"` ile.
  - Değerler altın ledger'lardan ve günlükteki `near_era` satırlarından; bayt-eşit (test).
- **Uygulama pinleri:** skor dosyası değişince `app/` altında yalnız skor sha'sı ya da skor içeriği pinleyen fikstür/test kırmızı olursa, J31 kalıbında asgari yeniden pin **önceden onaylıdır** (ayrı commit, yalnız sha/fikstür satırları). Rust'ın yeni skor dosyasını ayrıştıramaması gibi bir mantık sorunu çıkarsa DUR ve raporla; Rust'a dokunma.
- **`scores_oot.json` bu görevde değişmez** (kasa açılışı görevi yeniden üretecek). Değişmesi gerekirse DUR.

ÖNCE OKU:
- CLAUDE.md
- yukarıdaki şartname bölümleri; docs/faz6/S2_RAPOR.md ve docs/prompts/FAZ6_OOT_INFRA.md (ilk kayıtların nasıl yazıldığı)
- docs/faz7/FREEZE_RAPOR.md, docs/faz7c/FREEZE_RAPOR.md, docs/faz7c/IMPL_RAPOR.md §11
- docs/SPEC_DEVIATIONS.md I (eski kohort), J, K
- borsai/freeze.py (`build_oot_record`, `--oot`, B7 bekçisi), borsai/registry.py, borsai/scoring.py (`class_oot`, `cohort_gate_ok`, oot anahtarları, J30/K19 istisnaları), borsai/outcomes_oot.py (`download_gate`), borsai/backtest.py (`near_era_cell`, `near_era_cell_fall`, etiketler), borsai/report.py, report_faz7.py, report_faz7c.py
- tests/test_faz6_oot.py, tests/test_faz6_s6.py, tests/test_outcome_guard.py, tests/faz7_support.py, tests/faz7c_support.py

## Adımlar
0. **Taban.**
   - HEAD, proje sahibinin kanıt commit'i ya da `fdb15c6`'nın torunu. İzinli izlenmeyen: bu görev dosyası.
   - Tam `.venv/bin/pytest -q`, `bash app/scripts/test.sh`, `gen_golden --check`.
   - Sayılar `docs/faz7_oot/ekler/test_runs.txt`'ye.
1. **Kod (commit C):**
   - **Model başına kapı** (§7.3): ingest anındaki INDEX'teki her model m ve her MEMBER a için, m'yi içeren aktif bir kayıt ingest commit'inin atası olmalı ve push kanıtı ingest kanıtından önce olmalı.
     - `outcomes_oot.download_gate` aynı kuralı çağırır; kapı kapalıysa indirme başlamaz.
     - Sentetik geçici git deposunda testler: bir üyenin ikinci kaydı eksikken kapı kırmızı; kanıt sonrayken kırmızı; hepsi tamamken yeşil.
   - **`freeze --oot <kohort> --only-missing-models`:** üye başına yalnız o üyenin hiçbir aktif kaydında bulunmayan INDEX modellerini içeren kayıt.
     - `record_stage = OOT_PRE_LISTING`, `models_index` = yeni INDEX sha, `delta_of` = ilk kayıt dosya adı.
     - Girdiler ve `model_inputs` ilk kayıtla bayt-eşit (test), ek olarak `tufe` bloğu ve rejimli modeller için `alloc_regime`.
     - Retler (f3 boş, ek satış boş, TÜFE) model başına "ret + neden"; üye sicilden düşmez.
     - Zaten tam olan üyede kayıt yazılmaz (idempotent; test).
   - **Kasa skorlama kodu:** `scoring --oot`'a `oot_pre_h99_sealed` ve `oot_pre_h99_all` anahtarları.
     - Birincil hücreler: v1 §5.2, (C) §5.2.
     - "Modeli içeren en erken aktif kayıt" kuralı.
     - Yeni modellerin açık küme satırları formülle OOT_RETRO (`n_oot_retro = 71`).
     - Sentetik kasa senaryosunda OOT_BLIND (geçici depo).
     - Gerçek veriyle kasa skoru bu görevde ÜRETİLMEZ.
   - **`scores.json` kod ekleri:** `models[].backtest.near_era` (EK3 §5.5) ve (C) kartlarında `n_exploration_family`.
   - Tam pytest yeşil → **commit C**.
2. **Ek kayıtlar (commit R1):**
   - Temiz ağaçta `.venv/bin/python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv --only-missing-models`.
   - Beklenen: 135 yeni kayıt dosyası, her biri tam 8 modeli içerir. İlk 135 kayıt bayt-eşit; açık/kasa ayrımı hiçbir yere yazılmaz.
   - Denetim (yalnız sayı): model başına ret sayıları. Kasa ve açık küme için ayrı ayrı sayı basılabilir, kod basılmaz.
   - Tam pytest yeşil → **commit R1** (yalnız `registry/oot/records/` altındaki yeni dosyalar).
3. **Skorlar (commit S):**
   - `python -m borsai.scoring` (canlı ve post_d1): 27 modelli `scores.json`, `scores_post_d1.json`, `docs/SCORES.md`.
   - J16/J30/K19 istisnaları kendiliğinden devre dışı kalmalı; kalan sabitleri gözden geçir.
   - `scores_oot.json` değişmez.
   - MODELS.md yeniden render (Faz 7/7C kartlarında sayaçlar); var olan bölümlerin başka satırı değişmez.
   - Uygulama: test.sh ve `gen_golden --check`. Gerekirse önceden onaylı asgari pin (ayrı commit **APPPIN_S**).
   - Tam pytest yeşil → **commit S**.
4. **Rapor** `docs/faz7_oot/RAPOR.md` (commit R):
   - hash'ler;
   - kapı ve kasa skorlama kodunun testleri;
   - 135 ek kaydın özeti (sayılar);
   - yeniden üretilen skorların farkı (19 eski kartta ne değişti: yalnız sayaçlar ve INDEX sha olmalı);
   - near_era blokları (dört v1 + dört (C));
   - uygulama etkisi;
   - kasa açılışı görevi için ön koşullar listesi:
     - R1'in push kanıtı;
     - kapının gerçek depoda bu kanıtla yeşile döndüğünü doğrulayacak komut;
     - SPEC_HAZARD_V1 §7.1-5 ve SPEC_C_V0 §7.1-5 adımları.

## Tek oturumda bitmezse
C yeşil ve commit'liyse orada dur. R1 ancak temiz ağaçta atılır ve yeniden koşulabilir (idempotent).

## Kurallar
- **Yazılabilir:**
  - `borsai/`, `tests/`;
  - `registry/oot/records/` (yalnız yeni ek kayıt dosyaları);
  - `scores/scores.json`, `scores/scores_post_d1.json`, `docs/SCORES.md`, `docs/MODELS.md`;
  - `docs/SPEC_DEVIATIONS.md` (yeni bölüm L), `docs/faz7_oot/`, bu görev dosyası;
  - `app/` yalnız önceden onaylı pin satırları.
- **Salt okunur:** `models/`, `data/`, `scores/scores_oot.json`, `docs/specs*`, `docs/app/`, `legacy/`, `CLAUDE.md`, var olan kayıt dosyaları.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- Oturum içinde proje sahibine karar sorman gerekirse soruyu ve seçenekleri açıkça yaz. Proje sahibi orkestratöre danışarak cevaplayacak.
- `git add -A` yok. Commit'ler:
  ```
  git add borsai tests docs/SPEC_DEVIATIONS.md docs/faz7_oot docs/prompts/FAZ7_OOT_RECORDS.md
  git commit -m "BORSAI_FAZ7_OOT_C: per-model cohort gate, sealed and all out-of-time scoring keys (synthetic tests only), only-missing-models records, near-era blocks and family exploration counter" -- borsai tests docs/SPEC_DEVIATIONS.md docs/faz7_oot docs/prompts/FAZ7_OOT_RECORDS.md
  git add registry/oot/records
  git commit -m "BORSAI_FAZ7_OOT_RECORDS: second pre-listing records for the 135 pre-H99 members with the eight Faz 7 and 7C models (no outcomes)" -- registry/oot/records
  git add scores/scores.json scores/scores_post_d1.json docs/SCORES.md docs/MODELS.md
  git commit -m "BORSAI_FAZ7_SCORES: live scores regenerated with 27 models, near-era blocks and family exploration counter" -- scores/scores.json scores/scores_post_d1.json docs/SCORES.md docs/MODELS.md
  git add docs/faz7_oot
  git commit -m "BORSAI_FAZ7_OOT_REPORT: report and vault-opening prerequisites" -- docs/faz7_oot
  ```
  APPPIN_S gerekirse S'den sonra, yalnız pin dosyalarıyla. Değişmeyen bir yol pathspec'te hata verirse o yolu çıkar. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Push yok. Rapor Türkçe.

## Kabul kapısı
- **K1** Kapı ve kasa skorlama kodu sentetik testlerde doğru; `oot_pre_h99_all` yeni modelleri birleştirmiyor.
- **K2** 135 ek kayıt: her biri 8 model; girdiler ilk kayıtla bayt-eşit; sonuç alanı yok; kasa kodu hiçbir yeni metinde yok.
- **K3** 27 modelli skorlar üretildi. 19 eski modelin skor hücreleri değişmedi (yalnız sayaçlar ve INDEX sha). near_era blokları altın ledger'larla eşit. Aile keşif sayacı (C) kartlarında.
- **K4** Tam pytest, test.sh ve `gen_golden --check` yeşil. Commit'ler yalnız izinli yollarda; push yok.

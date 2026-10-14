# TASK_ID: BORSAI_FAZ7_VAULT_OPEN_20260929

Model: Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi. **Ağ: yalnız `www.borsaistanbul.com` THB/THM bülten URL'leri (`outcomes.source_url`; HEAD probu + zip indirme), yalnız karantinaya** (`~/Desktop/BorsAi_quarantine`, repo dışı). Başka site yok. push/tag/amend yok.

**Kasa açılışı. Tek seferlik ve geri alınamaz.** 64 SEALED üyenin sonuç satırları repoya girer. İki bölüm var: A (kod + kasa açılışı + D_1 satırları + post_d1 kayıtları) ve B (D_1…D_10 satırları). Arada proje sahibi push eder ve push kanıtı alır.

**Bölüm A bitince oturum biter, beklemez.** Bölüm B, proje sahibi aynı cümleyle yeni oturum açınca başlar. Adım 0 hangi bölümde olunduğunu diskten ölçer:
- C commit'i (`BORSAI_FAZ7_VAULT_CODE`) yoksa → Bölüm A.
- RA commit'i (`BORSAI_FAZ7_VAULT_A_REPORT`) var ve VA1/VA2'nin push kanıtları repoda → Bölüm B.
- RA var ama kanıt yok → DUR; rapordaki push bloğunu proje sahibine hatırlat.
- Arada bir yerdeyse → "Tek oturumda bitmezse".

Skorlama bu görevde YOK. `scoring --oot` ayrı görevdir (`FAZ7_VAULT_SCORE`); ancak VB'nin push kanıtından sonra koşar.

## Bağlam
- **Kasa:** kohortun 64 SEALED üyesi (2020: 4, 2021: 26, 2022: 18, 2023: 16). Açık küme (71) Faz 6'da skorlandı.
  - Açık kümenin yolu: S3a (d1_rows) → S3b (post_d1 kayıtları) → push + kanıt → S5 (D_1…D_10).
  - Kalıp: `docs/prompts/FAZ6_S3_S5_EXTRACT.md`, rapor `docs/faz6/S3_S5_RAPOR.md`. **Bu görev o yolun kasa karşılığıdır.**
- **Bağlayıcı metinler:**
  - `docs/specs_faz6/KARARLAR.md` D4, D5, D6. D6-4: "Kasa açıldığında zip'ler yeniden indirilir, pinlenmiş sha ile eşleşmesi zorunludur; sonra SEALED satırları ayıklanır."
  - `docs/specs_faz7/SPEC_HAZARD_V1.md` §7.1-5, §7.3, §7.4; `docs/specs_faz7_c/SPEC_C_V0.md` §7; `docs/specs_faz7/KARARLAR.md`; `docs/specs_faz7_c/KARARLAR_C.md`.
  - `docs/faz7_oot/RAPOR.md` §9: kasa görevinin ön koşulları ve eksik parçalar.
- **Sınıf formülü** (`scoring.class_oot`; SPEC_DEVIATIONS I10, I13, L1):
  - Listeleme öncesi modellerde sonuç girişi = `d1_rows/<T>.json`'u ya da `outcomes_oot`'u ekleyen ilk commit. Kasa için bu **VA1** olur.
  - `post_d1_hazard_v0` için sonuç girişi = D_1 sonrası sonuç (d1_rows hariç, o modelin girdisidir). Kasa için bu **VB** olur.
  - Kaydın push kanıtı, sonuç commit'inin kanıtından ÖNCE olmalı; değilse OOT_RETRO.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Bu görev hiçbir modeli, şartnameyi, girdiyi ya da kaydı değiştirmez.

## Orkestratörün ölçtükleri (2026-09-29 ~10:00)
- HEAD = origin/main = `1d659da`, ağaç temiz.
- `models/INDEX.json` 27, `INDEX_POST_D1.json` 1. `registry/push_proofs` 26 dosya. `registry/oot/records` 270 kayıt (135 ilk + 135 ek). `data/outcomes_oot` 71 csv. `data/raw/bist/MANIFEST_OOT.csv` 914 satır + başlık.
- **Ön koşulların push kanıtları** (kanıt, commit'i ve bütün atalarını kapsar; en erken kapsayan kanıt):

  | Belge / commit | Ekleyen commit | En erken kanıt |
  |---|---|---|
  | `docs/specs_faz7/SPEC_HAZARD_V1.md` | `6a16c16` | 2026-09-25T18:09:45Z |
  | `docs/specs_faz7/KARARLAR.md` | `2a21a96` | 2026-09-27T15:30:42Z |
  | `docs/specs_faz7_c/SPEC_C_V0.md` | `4fe4e51` | 2026-09-27T15:30:42Z |
  | `docs/specs_faz7_c/KARARLAR_C.md` | `3c93f9c` | 2026-09-28T19:06:01Z |
  | 135 ek kayıt | `28aaa3b` | 2026-09-29T06:40:55Z |

- Proje sahibinin terminalinde `s2_gate_problems()` → 0 (29 Eylül 09:40).
- **Kodun bugünkü hali:**
  - `outcomes_oot.open_vault` iskelet. Tek bir özellik şartnamesinin kanıtını denetliyor, `download_gate`'i çağırıyor, MANIFEST_OOT'un her satırını **temposuz** yeniden indirip sha'yı karşılaştırıyor ve SEALED kümesini dönüyor. Kasa üyelerini ayıklayan sürücü yok.
  - `extract_d1_rows`, `extract_open_members`, `s3_post_d1` ve `s3_gate_problems` yalnız açık küme içindir. `s3_post_d1` açık küme dışı ad görünce DUR der.
  - `resolve_member(..., unsealed=…)` ve `assert_extractable` kasa kodunu yalnız `unsealed` ile açar.
  - `scoring.oot_post_d1_block` yalnız açık üyeleri dolaşır.
  - `OotContext.vault_opened()` "bir SEALED üyenin sonuç dosyası repoda" demektir. `oot_vault_blocks` yalnız INDEX modelleri için `oot_pre_h99_sealed` ve `oot_pre_h99_all` üretir.
- **Kasa bekçileri kasanın kapalı olduğunu varsayar:**
  - `test_sealed_codes_absent_from_every_extracted_file`: ayıklanmış dosyalar, `registry/oot/post_d1`, MANIFEST_OOT, `scores_oot.json`, `SCORES_OOT.md`.
  - `cohort_code_problems` / T4: kasa kodu `data/`'nın hiçbir yerinde olamaz.
  - `test_cohort_guard_t4_mutation`: `outcomes_oot`'taki kasa kodu kırmızı.
  - Gerçek depoda 71 sayısını pinleyen başka testler olabilir.
- **Açık kümede post_d1** (`scores_oot.json` `post_d1`): 62 satır, 59 skorlandı, 3 ret (f3), 9 uygulanamaz (D1 tavan değil). Birincil hücre: koşullu RPS − `ceiling_hazard_v0`, −0.0418 [−0.0664, −0.0201] → geçiyor (makine sıralı).
- R1 raporu: kasada f3'süz üye 2.

## Proje sahibi ve orkestratör kararları (bağlayıcı; SPEC_DEVIATIONS'ta L'den sonraki yeni bölüme M1… olarak yazılır)

**M-A. İki adımlı açılış, D_1 dahil.** Proje sahibi kararı, 2026-09-29 ~10:05: `post_d1_hazard_v0` kasada da kör test edilecek.
- Sıra: **C → VA1** (kasa açılışı: yeniden indirme + D_1 satırları + işaret dosyası) **→ VA2** (post_d1 kayıtları) **→ RA → push + kanıt → VB** (D_1…D_10) **→ RB → push + kanıt.**
- Şartnamelerdeki "tek commit" lafzı yerine: kasa **bir kez** açılır, sonuç satırları iki commit'te girer (Faz 6 S3/S5 kalıbı). Kasa açıldıktan sonra hiçbir model, şartname, eşik ya da skor tanımı değişmez.

**M-B. Açılış kapısı.** Sürücü başlamadan önce yukarıdaki dört belgenin (SPEC_HAZARD_V1, KARARLAR, SPEC_C_V0, KARARLAR_C) commit'li, çalışma kopyasında değişmemiş ve push kanıtlı olduğunu denetler. `open_vault` bir liste alacak biçimde genelleştirilebilir. Buna ek olarak `download_gate()` (model başına) açık olmalıdır. Biri eksikse hiçbir zip indirilmez.

**M-C. Yeniden indirme (D6-4).**
- Bölüm A'da `open_vault` **bir kez** koşar: MANIFEST_OOT'un 914 satırı tempolu (`--pace`) yeniden indirilir ve hepsinin sha'sı pinle eşit olmalıdır. Tek bir uyuşmazlık (`SourceChanged`) → DUR; hiçbir kasa dosyası yazılmaz. Rapora yalnız sayı yazılır.
- Kasa ayıklamasında okunan **her zip**, o koşuda resmi kaynaktan indirilmiş baytlardır (`fetch_vault`).
  - Karantinada kopyası varsa sha'ları eşit olmalı.
  - MANIFEST_OOT'ta pini varsa eşit olmalı.
  - Takvim kanıt dosyasında THB pini varsa eşit olmalı.
  - Herhangi bir uyuşmazlık → DUR.
  - Karantinada yoksa indirilen dosya karantinaya ve karantina manifestine yazılır.
  - Testler: üç uyuşmazlık türünün her biri kırmızı; eşitlik yeşil.

**M-D. İşaret dosyası `registry/oot/VAULT_OPEN.json`.**
- `vault-d1` komutu bunu en son yazar (bütün indirme ve ayıklamadan sonra). VA1 commit'ine girer.
- İçerik:
  - şema;
  - açılış zamanı (İstanbul);
  - M-B'deki dört belgenin yolu, ekleyen commit'i ve kanıt zamanı;
  - `download_gate` sonucu;
  - açılıştan önce MANIFEST_OOT'un sha'sı;
  - yeniden indirilen ve eşleşen zip sayıları;
  - `n_sealed = 64`;
  - `code.git_head`.
- **Kasa kodu içermez** (test).
- Yeniden koşuda: dosya varsa ve içeriği zaman alanları dışında aynıysa dokunulmaz; farklıysa DUR.

**M-E. Kasa açıldıktan sonra hijyen bekçileri (iki kip).** Kasa durumu elle bayrakla değil, **commit'li işaret dosyasıyla** belirlenir.
- **İşaret yokken:** bütün kasa bekçileri bugünkü gibi katıdır. Bugünkü iddialar aynen kalır; gevşetilmez.
- **İşaret commit'liyken:**
  - (a) Kasa kodları yalnız şu yollarda bulunabilir:
    - `registry/oot/d1_rows/<T>.json`
    - `registry/oot/post_d1/<T>/…`
    - `data/outcomes_oot/<T>.csv`
    - `data/outcomes_oot/raw/<T>.json`
    - `scores/scores_oot.json`, `docs/SCORES_OOT.md`
    - zaten izinli olan kayıt, girdi ve kaynak belge dizinleri.
  - (b) Bu yollardaki her kasa dosyası, işaret dosyasını ekleyen commit'te ya da onun torununda eklenmiş olmalıdır.
  - (c) `data/`'nın geri kalanında kasa kodu yine yasaktır. Buna `data/training_table_v2.csv` de dahildir; COMPLETENESS istisnası aynen kalır. Gerekçe D4: kasa satırları doğrulaması yayımlanana kadar hiçbir eğitim ya da keşif tablosuna girmez; sonra da yalnız yeni bir tablo sürümüyle ve yeni kimlikle girer.
  - (d) `assert_extractable` kasa kodunu yalnız iki durumda açar: `open_vault` sonucu verilmişse (Bölüm A) ya da işaret commit'li ve push kanıtlıysa (Bölüm B).
- **Mutasyon testleri:** işaret yokken kasa dosyası → kırmızı; işaretten önceki bir commit'te eklenmiş kasa dosyası → kırmızı; izinli yol dışında kasa kodu → kırmızı; v2'de kasa kodu → kırmızı.
- Bekçi iletileri kod adı taşımaz, yalnız sayı taşır (bugünkü gibi).

**M-F. post_d1 kasa skorlama kodu.** C commit'inde yazılır, yalnız sentetik testlerle; gerçek veriyle skor üretilmez.
- `scores_oot.json`'a kasa açılınca iki anahtar eklenir:
  - `post_d1_sealed`: kasa satırları; MACHINE_SEQUENCED; `post_d1` ile aynı formül, satır kapısı ve hücreler.
  - `post_d1_all`: açık + kasa; yalnız açık kümede OOT_BLIND olan POST_D1 modelleri için (`all_eligible` kalıbı).
- `post_d1` (açık küme) bayt olarak aynı kalır.
- Üç anahtar birbirine ve başka hiçbir tabloya eklenmez. `SCORES_OOT.md`'ye ayrı bölümler eklenir.
- Kasa kapalıyken bu anahtarlar ve bölümler yoktur (test). Bugünkü `scores_oot.json`'u yeniden üreten bellek koşusu, kasa kapalıyken commit'li dosyayla aynı olmalıdır (test).

**M-G. Kayıt kapsamı.** Kasa d1_rows'u olan HER üye için post_d1 kaydı yazılır; REFUSED ve NOT_APPLICABLE dahil (Faz 6 T4).

**M-H. CLI** `python -m borsai.outcomes_oot`'a üç komut eklenir. Adlar öneridir; değiştirirsen rapora yaz. Çıktı yalnız sayıdır (JSON).
- `vault-d1`: M-B kapısı → `check_calendar_closures` → `open_vault` (M-C) → 64 kasa üyesinin yalnız D_1'e kadar ayıklanması → `registry/oot/d1_rows/<T>.json` + MANIFEST_OOT pinleri → işaret dosyası (M-D).
- `vault-post-d1`: kasa d1_rows'u olan her üye için `freeze.write_oot_post_d1_record` (`s3-post-d1` kalıbı; işaret yoksa DUR).
- `vault-s5`: B kapısı (M-I) → kasa üyelerinin D_1…D_10 ayıklanması → `data/outcomes_oot/<T>.csv` + `raw/<T>.json` + MANIFEST_OOT pinleri.
- Kasa kapalıyken ve işaret yokken `vault-post-d1` ile `vault-s5` hiçbir zip açmaz (test).

**M-I. B kapısı** (`vault_s3_gate_problems`; `s3_gate_problems`'ın kasa karşılığı). `vault-s5` ancak şunların hepsi sağlanınca bülten açar:
- `s2_gate_problems()` boş;
- M-B'deki belgeler kanıtlı;
- işaret dosyası commit'li, değişmemiş ve push kanıtlı;
- her kasa üyesinin d1_rows dosyası ve skorlamanın seçeceği post_d1 kaydı commit'li, değişmemiş ve push kanıtlı; kayıt d1_rows'un kanonik sha'sını taşıyor.

Mutasyon: kanıt denetimi ya da post_d1 denetimi kaldırılınca test kırmızı.

**M-J. Bağımsız ham alan denetimi** (Faz 6 T5 kalıbı).
- Betik `borsai` import etmez, repo dışında çalışır (ör. `/tmp/borsai_vault/`). Karantinadaki zip'leri doğrudan açar ve yalnız kasa kodlarının satırlarına bakar.
- Karşılaştırmalar:
  - d1_rows `fields_raw` (14 alan) ↔ D_1 zip satırı;
  - B'de `close_raw`, `upper_limit_raw`, `reference_raw`, `trade_count_raw` ↔ zip satırı;
  - sha'lar ↔ karantina ↔ MANIFEST_OOT;
  - `ceiling_close` ↔ (kapanış == üst limit, Decimal);
  - h ∈ {1, 3, 5, 10} için `R_h` ↔ kapanış / arz fiyatı − 1 (|Δ| ≤ 1e-12).
- Çıktı yalnız sayı. Betik ve çıktısı `docs/faz7_vault/ekler/bagimsiz_*.{py,txt}` olarak kopyalanır.

**M-K. Ağ ve veri hatası kuralları** (Faz 6 T6 aynen).
- Takvimde seans olan bir gün için bülten 404 → DUR, tarihi yaz.
- HEAD 200 ya da 404 dışı bir kod dönerse DUR; GET denenmez.
- Bir kod ilk işlem gününden sonra 15 seansta görünmezse DUR. Proje sahibine kodu ve nedeni yazabilirsin; kasa artık açılıyor.
- Geçici ağ hatası (3 deneme sonrası): komutu yeniden koş; karantina önbellektir.
- Manifest satırı olmayan yarım zip → `~/Desktop/BorsAi_quarantine/_orphans/`'a taşı, yeniden koş, rapora yaz.

**M-L. Önceden yazılmış beklenti: post_d1 kasada.** Kasa sonucu repoda yokken yazıldı; C commit'iyle kaydolur.
- Satır sayısı: ~56 üyede D1 tavan beklenir; 2 ret (f3) → n ≈ 50–54.
- Birincil hücre: koşullu RPS − `ceiling_hazard_v0`. Beklenen **−0.035**, aralık **[−0.065, −0.005]**. "Geçiyor (zaman-dışı, makine sıralı)" olası ama kesin değil; açık kümede aralığın üst ucu −0.020 idi.
- "Beklentiden çok iyi": fark < −0.08 ya da aralığın üst ucu < −0.045. Bu durumda VAULT_SCORE'da bağımsız yeniden hesap zorunludur.
- v1 ve (C) beklentileri şartnamelerde (§6.1); bu görev onlara dokunmaz.

## Hijyen
- Rapora, ekrana ve eklere yalnız SAYI yazılır: dosya, durum ve eşleşme sayıları. Hiçbir üyenin fiyat, getiri, limit ya da tavan değeri yazılmaz; bir üyenin satırı ekrana basılmaz.
- Kasa kodlarını listeleyen metin yazılmaz. DUR iletisi dışında kod adı geçmez. Kohort dosyası yalnız betikle okunur; satırı basılmaz.
- Bir bekçi kırmızı olur ve çıktısında bir kod görünürse o çıktı rapora yapıştırılmaz.
- `EXPOSURE.md` dosyaları ve Codex `exposure_log`'ları okunmaz.
- `scoring --oot`, `build_oot_scores` ve kasa satırlarından herhangi bir metrik bu görevde hesaplanmaz; bellekte bile.

## Paralel
Bu görev koşarken başka oturum yok. Proje sahibi bu sırada git komutu çalıştırmaz.

## İzinli izlenmeyen
- Bölüm A başında yalnız `docs/prompts/FAZ7_VAULT_OPEN.md`.
- Bölüm B başında hiçbiri (ağaç temiz).
- Başka bir şey varsa DUR.

## ÖNCE OKU
- CLAUDE.md
- `docs/specs_faz6/KARARLAR.md` (D4, D5, D6); `docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md` §1 (D_1 kuralı), §2, §9
- `docs/specs_faz7/SPEC_HAZARD_V1.md` §5.2, §6.1, §7; `docs/specs_faz7_c/SPEC_C_V0.md` §5.2, §6.1, §7; iki KARARLAR belgesi
- `docs/SPEC_DEVIATIONS.md` bölüm I (I10, I13, I28–I38) ve L
- `docs/prompts/FAZ6_S3_S5_EXTRACT.md` (kalıp); `docs/faz6/S3_S5_RAPOR.md`; `docs/faz7_oot/RAPOR.md` §2, §8, §9
- `borsai/outcomes_oot.py` (tamamı)
- `borsai/freeze.py`: `build_oot_post_d1_record`, `write_oot_post_d1_record`, `oot_primary_of`
- `borsai/scoring.py`: `OotContext` (`vault_opened`, `realized`), `oot_ingest_commit`, `cohort_gate_ok`, `class_oot`, `oot_post_d1_block`, `oot_vault_blocks`, `all_eligible`, `build_oot_scores`, `_render_oot_vault`
- `tests/test_faz6_oot.py`, `tests/test_faz7_oot.py`, `tests/test_outcome_guard.py`, `tests/faz6_support.py`, `tests/faz7_support.py`

## Bölüm A
0. **Taban.**
   - `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3` → HEAD `1d659da` (ya da torunu, aradaki commit'ler yalnız push kanıtı). `git status --porcelain` → yalnız bu görev dosyası.
   - `.venv/bin/python -c "from borsai import outcomes_oot as oo; print(len(oo.s2_gate_problems()))"` → `0`. Değilse DUR.
   - Karantina: dosya sayısı ve manifest satır sayısı rapora yazılır. Her dosyanın sha'sı manifestle eşleşmeli; değilse DUR. Zip içi açılmaz.
   - Tam `.venv/bin/pytest -q` (beklenen 848 geçti), `bash app/scripts/test.sh` (yeşil), `.venv/bin/python app/parity/gen_golden.py --check` (25/0). Sayılar `docs/faz7_vault/ekler/test_runs.txt`'ye.
1. **Kod (commit C).** M-B…M-I ve testleri. Hepsi sentetik; ağ yok; gerçek kasa verisi yok. Sentetik kasa senaryosu `tests/faz6_support.py` ve `tests/faz7_support.py` kalıplarıyla kurulur (SYK* kodlar).
   - Kasa kapalıyken ve işaret yokken bugünkü bütün iddialar aynen geçer. Var olan hiçbir bekçi gevşetilmez; yeni kip eklenir.
   - **Prova (geçici klon, ağ yok).** `git clone` ile `/tmp`'ye kopyala. Klonda kasa üyeleri için sentetik değerli d1_rows, post_d1, `outcomes_oot` ve ham dosyalar ile işaret dosyası yaz. Kodlar kohort dosyasından betikle alınır ve basılmaz. Klonda commit et, tam pytest koş.
     - Kırmızı olan testler "kasa kapalı" varsayımı taşıyanlardır (ör. gerçek depoda 71'i sayanlar). Bunları işarete bağlı iki kipli yap: kapalı kipte iddia aynen, açık kipte kasa sayısıyla.
     - Listeyi rapora yaz (test adı, eski iddia → yeni iddia).
     - Provadan sonra klonu sil.
   - SPEC_DEVIATIONS M1… (M-A…M-L ve verdiğin yorum kararları).
   - Tam pytest + test.sh + `gen_golden --check` yeşil → **commit C**.
2. **Prob (ilk ağ işi):** `.venv/bin/python -m borsai.outcomes_oot probe` → kapı OPEN, mod EVIDENCE, çelişki yok. Değilse M-K → DUR.
3. **VA1:** `.venv/bin/python -m borsai.outcomes_oot vault-d1`. Beklenen:

   | Denetim | Beklenen |
   |---|---|
   | M-B kapısı | dört belge kanıtlı; `download_gate` açık |
   | `open_vault` | 914 zip yeniden indirildi, 914 sha eşit, 0 uyuşmazlık |
   | `registry/oot/d1_rows/*.json` | 135 dosya: 71 açık (bayt-eşit, dokunulmadı) + 64 kasa (yeni) |
   | yeni her dosya | `d1_rows_problems == []`, `exposure_class = MACHINE_SEQUENCED`, `session_h = 1`, D_1 ≥ first_trading_date. D_1 ≠ first_trading_date olanların sayısı rapora. |
   | `MANIFEST_OOT.csv` | ilk 915 satır (başlık + 914) bayt-eşit; yalnız ekleme. Yeni satır = 2 × (pinli olmayan yeni D_1 tarihi sayısı). Her yeni sha = karantina = taze indirme. |
   | `registry/oot/VAULT_OPEN.json` | M-D şeması; kasa kodu 0; `n_sealed = 64` |
   | M-J (d1_rows) | 64 × 14 alan zip satırıyla eşit; 0 fark |
   | bekçiler | açık kipte yeşil (M-E) |

   Tutmazsa commit etme, DUR.
   - **Temizlik yolu:** yalnız bu görevin commit edilmemiş yeni dosyaları yüzünden kırmızı olan temizlik bekçileri deselect edilir. Faz 6 S3'te dört testti; bugünkü listeyi rapora yaz. Deselect'li tam koşu yeşil → **commit VA1** → deselect'siz tam koşu yeşil.
   - Eski kohort bekçileri (`test_oot_*`, `test_sealed_*`, `test_no_cohort_window_*`, `test_cohort_*` ve M-E'nin yenileri) asla deselect edilmez. Başka bir kırmızı varsa DUR.
4. **VA2:** `.venv/bin/python -m borsai.outcomes_oot vault-post-d1`. Beklenen:
   - `registry/oot/post_d1/<T>/` altında 64 yeni kasa kaydı; açık kümenin 71 kaydı bayt-eşit.
   - Her yeni kayıt: `borsai.oot_post_d1_record/1`, `MACHINE_SEQUENCED`, `code.git_head` = VA1, `borsai_dirty = false`. `d1_rows.sha256` kanonik sha'ya eşit; `base_record` o üyenin S2 kaydı.
   - f3 eksikliğiyle REFUSED olan kayıtların kümesi = S2 kaydında `ceiling_hazard_v0` hücresi REFUSED olan kasa üyeleri, birebir (beklenen 2).
   - PREDICTED / REFUSED / NOT_APPLICABLE sayıları ve ret kodları rapora.
   - Aynı temizlik yolu → **commit VA2** (yalnız `registry/oot/post_d1`) → deselect'siz tam pytest + test.sh yeşil.
5. **Rapor** `docs/faz7_vault/RAPOR.md` Bölüm A (commit RA). İçerik:
   - C, VA1, VA2 hash'leri;
   - taban ve karantina sayıları; prob sonucu; `open_vault` sayıları;
   - VA1 ve VA2 tabloları; M-J sayıları;
   - prova listesi; mutasyon gösterimleri (`docs/faz7_vault/ekler/mutasyon.txt`);
   - test sayıları;
   - proje sahibi için push bloğu (hash'ler doldurulmuş):

   ```
   cd ~/Desktop/BorsAi
   git push origin main
   .venv/bin/python -m borsai.push_proof <VA1> <VA2>
   git add registry/push_proofs
   git commit -m "BORSAI_PUSH_PROOFS: Faz 7 vault D_1 rows (<VA1>) and post_d1 records (<VA2>)" -- registry/push_proofs
   git push origin main
   git --no-pager log --oneline -3 origin/main
   ```
   **Oturum burada biter; B'ye geçme.**

## Bölüm B
0. **Taban.**
   - Ağaç temiz. HEAD, RA'nın ve VA kanıt commit'inin torunu. `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -1 origin/main` = HEAD.
   - `.venv/bin/python -c "from borsai import outcomes_oot as oo; print(len(oo.s2_gate_problems()), len(oo.vault_s3_gate_problems()))"` → `0 0` (komut adı C'de ne olduysa). Değilse DUR.
   - VA1 ve VA2 kanıtlarının `created_at`'i R1 kanıtından (2026-09-29T06:40:55Z) sonra olmalı; rapora yaz.
   - Tam pytest + test.sh yeşil; sayılar ek dosyaya.
1. **VB:** `.venv/bin/python -m borsai.outcomes_oot vault-s5`. Beklenen:

   | Denetim | Beklenen |
   |---|---|
   | `data/outcomes_oot/<T>.csv` | 135 dosya: 71 açık bayt-eşit + 64 kasa. Her yeni dosya 10 satır (h = 1…10), `outcome_basis` hep `MACHINE_EXTRACTED`, `PENDING` 0. |
   | `data/outcomes_oot/raw/<T>.json` | 135 (64 yeni). D_10'dan sonra okunmuş seans yok. Okunan − çözümlenen seans farkı olan üye sayısı rapora. |
   | D_1 tutarlılığı | 64/64 CSV'nin h = 1 seansı = d1_rows D_1'i; D_1 thb/thm sha'ları d1_rows ve MANIFEST_OOT ile eşit |
   | `MANIFEST_OOT.csv` | VA1 sonrası satırlar bayt-eşit ve başta; yalnız ekleme; her sha = karantina = taze indirme |
   | durumlar | 10 seansı olmayan üye sayısı; `TARGET_UNAVAILABLE` ve `NA_LIMIT` satır sayıları (değer yok) |
   | M-J (S5) | bütün yeni satırlarda ham alanlar zip'le eşit; `ceiling_close` ve `R_h` yeniden hesapla eşit; 0 fark |
   | bekçiler | açık kipte yeşil; G5′ (sonuç dosyaları kayıtların ve kanıtlarının torunu) yeşil |

   Tutmazsa commit etme, DUR. Aynı temizlik yolu → **commit VB** (yalnız `data/outcomes_oot` + `data/raw/bist/MANIFEST_OOT.csv`) → deselect'siz tam pytest + test.sh + `gen_golden --check` yeşil.
2. **Rapor** Bölüm B (commit RB): VB hash'i, tablo sayıları, M-J, test sayıları, VAULT_SCORE için notlar ve push bloğu:

   ```
   cd ~/Desktop/BorsAi
   git push origin main
   .venv/bin/python -m borsai.push_proof <VB>
   git add registry/push_proofs
   git commit -m "BORSAI_PUSH_PROOFS: Faz 7 vault outcome rows (<VB>)" -- registry/push_proofs
   git push origin main
   git --no-pager log --oneline -3 origin/main
   ```
   `scores/` yazılmaz; `scoring` hiçbir kipte çalıştırılmaz.

## Tek oturumda bitmezse
- Her komut yeniden koşulabilir olmalı (test). Karantina önbellektir. `vault-d1` var olan aynı d1_rows'u UNCHANGED sayar ve işaret için M-D kuralını uygular. `vault-post-d1` var olan kaydı "zaten var" sayar. `vault-s5` UNCHANGED yazar.
- Yeniden koşuda `open_vault` yeniden indirmesi tekrarlanabilir; zararı yok.
- Commit'lenmiş adımı tekrarlama. Nerede kalındığını `git log` ve dosya sayılarıyla ölç.

## Kurallar
- **Yazılabilir:**
  - `borsai/outcomes_oot.py`, `borsai/scoring.py` (yalnız M-F ve kasa kipi), `borsai/freeze.py` (yalnız kasa üyelerine post_d1 kaydı izni gerekiyorsa);
  - `tests/` (yeni testler; M-E iki kip; prova listesindeki iki kipli testler);
  - `docs/SPEC_DEVIATIONS.md` (yeni bölüm M);
  - yalnız CLI ile: `registry/oot/d1_rows/`, `registry/oot/post_d1/`, `registry/oot/VAULT_OPEN.json`, `data/outcomes_oot/`, `data/raw/bist/MANIFEST_OOT.csv`;
  - `docs/faz7_vault/`, karantina dizini (repo dışı), bu görev dosyası.
- **Salt okunur:** `models/`, `registry/` (yukarıdakiler dışı), `data/` (yukarıdakiler dışı), `scores/`, `app/`, `docs/specs*`, `docs/app/`, `CLAUDE.md`, `legacy/`, var olan kayıt, d1_rows, post_d1 ve sonuç dosyaları.
- test.sh kırmızı olursa `app/`'e dokunma; DUR ve raporla.
- Karantinadaki zip'ler ya da iç CSV'leri repoya kopyalanmaz, repo içinde açılmaz. Kohort penceresinden hiçbir bülten dosyası repoda olmaz.
- Ayıklanmış dosyalar ve kayıtlar elle düzenlenmez; hata varsa commit'ten önce DUR.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- Oturum içinde proje sahibine karar sorman gerekirse soruyu ve seçenekleri açıkça yaz. Proje sahibi orkestratöre danışarak cevaplayacak.
- `git add -A` yok. Commit'ler:
  ```
  git add borsai tests docs/SPEC_DEVIATIONS.md docs/faz7_vault docs/prompts/FAZ7_VAULT_OPEN.md
  git commit -m "BORSAI_FAZ7_VAULT_CODE: vault opening driver (re-download against pins, sealed D_1 rows, post_d1 records, D_1..D_10 rows), vault marker and part-B gate, post_d1 sealed and all scoring keys (synthetic tests only), two-mode hygiene guards" -- borsai tests docs/SPEC_DEVIATIONS.md docs/faz7_vault docs/prompts/FAZ7_VAULT_OPEN.md
  git add registry/oot/d1_rows registry/oot/VAULT_OPEN.json data/raw/bist/MANIFEST_OOT.csv
  git commit -m "BORSAI_FAZ7_VAULT_D1: vault opened once; D_1 rows of the 64 sealed members from re-downloaded bulletins, zip pins and vault marker" -- registry/oot/d1_rows registry/oot/VAULT_OPEN.json data/raw/bist/MANIFEST_OOT.csv
  git add registry/oot/post_d1
  git commit -m "BORSAI_FAZ7_VAULT_POST_D1: post_d1_hazard_v0 records for the sealed members (MACHINE_SEQUENCED), before any D_2+ row" -- registry/oot/post_d1
  git add docs/faz7_vault
  git commit -m "BORSAI_FAZ7_VAULT_A_REPORT: vault opening part A counts and checks" -- docs/faz7_vault
  git add data/outcomes_oot data/raw/bist/MANIFEST_OOT.csv
  git commit -m "BORSAI_FAZ7_VAULT_S5: D_1..D_10 outcome rows of the 64 sealed members (MACHINE_EXTRACTED) with zip pins" -- data/outcomes_oot data/raw/bist/MANIFEST_OOT.csv
  git add docs/faz7_vault
  git commit -m "BORSAI_FAZ7_VAULT_B_REPORT: vault opening part B counts and checks" -- docs/faz7_vault
  ```
  Değişmeyen bir yol pathspec'te hata verirse o yolu çıkar. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Push yok. Rapor Türkçe.

## Kabul kapısı
- **KA1** M-B…M-I testli; M-C, M-E ve M-I mutasyonla gösterildi. Kasa kapalıyken bugünkü bütün iddialar aynen geçiyor. Prova listesi rapor edildi. C sonrası tam pytest + test.sh + `gen_golden --check` yeşil.
- **KA2** Prob temiz. `open_vault`: 914/914 sha eşit. VA1 tablosu birebir; M-J 0 fark; işaret dosyasında kod yok.
- **KA3** VA2: 64 kasa kaydı; f3 REFUSED kümesi birebir. Sıra C → VA1 → VA2 → RA. push yok.
- **KB1** VB'den önce B kapısı boş; VA kanıtları R1 kanıtından sonra.
- **KB2** VB tablosu birebir; M-J 0 fark; açık kümenin dosyaları bayt-eşit.
- **KB3** VB commit'i yalnız izinli yollarda; deselect'siz tam pytest + test.sh + `gen_golden --check` yeşil; skorlama çalıştırılmadı; push yok.

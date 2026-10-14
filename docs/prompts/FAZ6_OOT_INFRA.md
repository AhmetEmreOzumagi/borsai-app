# TASK_ID: BORSAI_FAZ6_OOT_INFRA_20260924

Model: Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi (+ okuma: `~/Desktop/BorsAi_codex/verified/`). **Ağ gerekmez ve KULLANILMAZ** (bu görevde hiçbir bülten ya da belge indirilmez). push/tag/amend yok.

## Bağlam
- Faz 6 = H99 öncesi 135 arzlık eski kohortun (2020-01-01…2023-09-21) dürüst protokolle projeye alınması. İki amaç var:
  - (A) Donmuş modellerin zaman-dışı testi.
  - (C) Azınlık sınıfı ("düşenler") için ileride keşif ve doğrulama.
- Şartname: `docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md` (`b8763fc`), fizibilite `docs/specs_faz6/FEASIBILITY.md`. **Proje sahibi kararları `docs/specs_faz6/KARARLAR.md` D1–D8 bağlayıcıdır; şartnameyle çeliştiği yerde KARARLAR geçerlidir.** En önemli fark D6: kohort penceresindeki THB/THM zip'leri repoya ham girmez. Karantinaya indirilir, yalnız OPEN üyelerin satırları kodla ayıklanır; repoya ayıklanmış satırlar ve zip pinleri girer. Bu, şartnamenin §2 S3/S5/G5 "zip commit" tasarımının yerine geçer.
- Girdiler hazır ve doğrulanmış (repo dışında): `~/Desktop/BorsAi_codex/verified/registry/oot/{inputs,source_docs,candidate_features}/` (135 ticker). Doğrulama raporu `verified/REPORT.md`. Ölçümler:
  - 135/135 dosya `validate_inputs` ve `inputs_pit_problems`'ten geçiyor.
  - f3 130/135; PB modellerinin girdisi 112 arzda tam.
  - Codex'in girdi değerlerinin %98,4'ü birebir doğrulandı.
- **Bu görev yalnız altyapı + kohort + girdi içe aktarımı.** Tahmin kaydı (S2), bülten indirme ve ayıklama (S3/S5) ve skorlama (S6) YOK. Onlar push ve bağımsız denetimden sonra ayrı görevler.
- **Ders (bu hafta yaşandı):** `borsai/`'deki bir değişiklik uygulamanın altın MANIFEST pinini kırdı ve fark edilmedi. Bu görevde tam `pytest` ile birlikte `bash app/scripts/test.sh` de her commit öncesi koşar.

### Proje sahibi kuralları (aynen)
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** (Bu görev hiçbir modeli değiştirmez.)
- Sonuç körlüğü: kohort üyelerinin listeleme sonrası hiçbir fiyat, getiri, tavan ya da hacim bilgisine bakılmaz. `verified/EXPOSURE.md` §3'teki ticker listesi okunmaz (KARARLAR D8-1); yalnız sayıları kullanılabilir.

## İzinli izlenmeyen (adım 0'da bunlar dışında bir şey varsa DUR)
`docs/prompts/FAZ6_CODEX_INPUTS_B1.md`, `…_B2.md`, `…_B3.md`, `…_B4.md`, `docs/prompts/FAZ6_VERIFY_CODEX_INPUTS.md`, `docs/prompts/FAZ6_OOT_INFRA.md`, `docs/specs_faz6/KARARLAR.md`.

ÖNCE OKU:
- CLAUDE.md
- docs/specs_faz6/KARARLAR.md (tamamı), SPEC_OOT_PRE_H99_V0.md (tamamı), FEASIBILITY.md §2–§4, §7; ekler/takvim_2020_2023.md, ekler/kurallar_arastirma.md (§1, §3, §6, §7, §10)
- ~/Desktop/BorsAi_codex/verified/REPORT.md (EXPOSURE.md §3 HARİÇ)
- docs/specs/SPEC_SCORING.md (§2, §3, §5, §6), docs/specs/SPEC_MARKET20_V0.md (§3, §4)
- docs/SPEC_DEVIATIONS.md (C, E, H)
- borsai/: registry.py, freeze.py (listeleme öncesi `build_record`, POST_D1 kayıt yazıcısı), outcomes.py (bülten ayrıştırma, `sequence_guard`, D_h), market20.py, predict_path.py (fiyat adımı, limit yolu), scoring.py (sınıf, `ScaleMixError`, POST_D1 bölümü), push_proof.py
- tests/test_outcome_guard.py, tests/test_faz5_live.py (geçici git deposu kalıpları)

## Adımlar
0. **Taban:** `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3` (HEAD `8e3a623` ya da torunu), `git status --porcelain`. Tam `.venv/bin/pytest -q` ve `bash app/scripts/test.sh` (sayı, süre). Kırmızı varsa DUR.
1. **Commit S0b: kararlar ve girdi toplama görevleri (kod yazmadan önce).** `docs/specs_faz6/KARARLAR.md` + beş `docs/prompts/FAZ6_*` görev dosyası (bu görev dosyası hariç).
2. **Tanım eşlemesi:** şartname §1–§7, §10 ve KARARLAR D1–D8'in her maddesi → dosya:fonksiyon, `docs/faz6/OOT_TANIM_ESLEME.md`. Boşluk ya da iki okumalı yer: lafza göre karar, `docs/SPEC_DEVIATIONS.md`'ye yeni "I. Faz 6" bölümü. Bilinen üç karar:
   - (i) **Skor çıktısı ayrı dosyada** `scores/scores_oot.json` (şema `borsai.scores_oot/1`), `scores.json`'a üst anahtar EKLENMEZ. Neden: uygulama `scores.json`'u gömer; POST_D1'deki L1 kararıyla aynı gerekçe. Bu, şartname §3'teki "`scores.json`'da ayrı üst anahtar" cümlesinden sapmadır.
   - (ii) `vault` ve `regime_tags` yalnız `cohort_pre_h99.csv`'de tutulur (tek kaynak); girdi dosyalarına kopyalanmaz; doğrulanmış girdi dosyaları bayt-eşit alınır.
   - (iii) `vault` değer kümesi `{OPEN, SEALED, EXPOSED_ARCHIVE, EXPOSED_CODEX}` (KARARLAR D2).
3. **Kod (commit A), sonuçsuz ve ağsız:**
   - `registry.py`:
     - `OOT_DIR = registry/oot`; `cohort_pre_h99.csv` okuyucu ve doğrulayıcı (şartname §1 sütunları, durumlar, append-only, `CANCELLED` kuralı).
     - Kasa çekilişi (KARARLAR D2): `numpy.random.Generator(PCG64(20260924))`, ilk işlem yılı tabakası, sıralama (`first_trading_date`, `ticker`), maruz kodlar çekilişten önce çıkarılıp OPEN yazılır. Tohumdan deterministik; test.
     - `regime_tags` hesaplayıcı (şartname §7 tablosu; yalnız kural tarihleri, arz belgeleri ve arz fiyatından):
       - `SALE_ON_EXCHANGE`, `PRICE_RANGE_BOOKBUILD`
       - `TICK_TABLE_EPOCH` + `TICK_TABLE_MISMATCH` (C_1..C_10'u dönem tablosuyla ve JSON tablosuyla ayrı hesapla, farklıysa etiket)
       - `MARGIN_RULE`, `SHORT_SELL_BAN`, `ALLOC_REGIME`, `MARKET`, `EXPOSED_*`
       
       Kaynak kural tarihleri kodda sabit ve kaynak notlu.
   - **Takvim C:** `data/raw/pay_calendar_c_20200101_20230921.csv`. Kaynaklar: BIST tatil tabloları (FEASIBILITY ve `ekler/takvim_2020_2023.md` kaynakları; PDF'ler repoda değilse sha ve URL'leriyle not et, İNDİRME) ve pinli XU100 serisinin gün kümesi. Sütunlar B uzatmasıyla aynı. Yarım günler ve 2023-02-09…14 deprem kapanışı. Test: hafta içi XU100 boşlukları = resmi kapanışlar. `market20` eski kohort için bu takvimi kullanır (`ref_date = first_trading_date`, SPEC_MARKET20 §4-e).
   - **`freeze.py --oot`** (şartname §5, `borsai.oot_record/1`), yalnız yazıcı ve testleri; gerçek kayıt YAZILMAZ:
     - `models/INDEX.json`'daki 19 modelin hepsi. Durumlar: PREDICTED, REFUSED, `NOT_APPLICABLE_REGIME` (+neden).
     - `comparators` donmuş H99 değerleri ve `comparator_note`.
     - `cohort_file_sha256`, `inputs_sha256`, `regime_tags`, `vault`, `code`.
     - Dizin `registry/oot/records/<T>/`. Tek toplu koşu CLI'si.
     - Ön koşul: kohort dosyası ve bütün girdiler commit'li (temiz ağaç).
   - **Karantina ve ayıklama (KARARLAR D6)**, yalnız kod ve sentetik zip'lerle test; indirme YOK:
     - `borsai/outcomes_oot.py`: karantina dizini repo dışında ve yapılandırılabilir (varsayılan `~/Desktop/BorsAi_quarantine`).
     - İndirme kapısı: kohortun bütün MEMBER S2 kayıtları commit'li VE push kanıtlı değilse indirme başlamaz.
     - Ayıklayıcı yalnız OPEN (OPEN + EXPOSED_*) kodların `<T>.E` satırlarını ve yalnız o üyenin D_1…D_10 tarihlerini okur. SEALED kod istenirse hata verir.
     - Çıktılar: `data/outcomes_oot/<T>.csv` (`OUTCOME_COLUMNS` anlamı aynen) ve `data/raw/bist/MANIFEST_OOT.csv` (tarih, tür, URL, sha256, bayt, Last-Modified, indirme zamanı). `outcome_basis = MACHINE_EXTRACTED`.
     - D_1 kuralı şartname §1 (KAP bildirim tarihinden önce olmayan, sözleşme > 0 ilk resmi seans).
     - Kasa açılışı fonksiyonu: yeniden indir, sha pinine eşit değilse hata. Yalnız iskelet ve test; çağrılmaz.
   - **post_d1 eski kohort (S3), yalnız kod ve sentetik test:** yalnız D_1 satırı ayıklanır → `registry/oot/d1_rows/<T>.json`; `post_d1_hazard_v0` kaydı `registry/oot/post_d1/<T>/` (`exposure_class = MACHINE_SEQUENCED`); `models/INDEX_POST_D1.json`'dan.
   - **`scoring.py`:**
     - Ölçek `OOT_PRE_H99`. `ScaleMixError` backtest, canlı, POST_D1 ve OOT'u karıştıran her çağrıyı reddeder.
     - `class_oot` (şartname §2 sözde kodu; `oot_ingest_commit` = `data/outcomes_oot/<T>.csv`'yi ekleyen ilk commit).
     - Birincil hücreler şartname §6; sayaçlar şartname §6 + `n_exposed_codex`, `n_spk_corporate_action_seen`.
     - Çıktı karar (i). Gerçek skor üretilmez (sonuç yok); sentetik test.
   - **Bekçiler (`tests/test_outcome_guard.py` ve yeni `tests/test_faz6_oot.py`):**
     - G1: `registry/oot/` sonuç alanı taşımaz; `d1_rows` ve `post_d1` yalnız D_1.
     - G2: kayıt bütün INDEX modellerini içerir; kayıt commit'i model commit'lerinin torunu.
     - G5′: `data/outcomes_oot/` ekleyen commit, kohortun bütün S2 kayıt commit'lerinin torunu ve S2 kanıtı önce; SEALED kod `data/outcomes_oot/`'ta ya da herhangi bir ayıklanmış dosyada yok.
     - G6: ölçek karışımı.
     - Kohort penceresi tarihli hiçbir THB/THM zip'i repoda yok (herhangi bir dizinde).
     - `test_new_ipos_appear_in_data_only_as_outcomes` kalıbı kohort kodları için genişler.
   - **CLAUDE.md:** KARARLAR D3'teki iki metin AYNEN (kural 3 ilk cümlesi değişir, sıra kuralına ek cümle).
   - Tam pytest + `bash app/scripts/test.sh` yeşil → **commit A**.
4. **Commit B (S1: kohort + girdiler):**
   - `registry/oot/cohort_pre_h99.csv`: 135 MEMBER + GMTAS `OUT_OF_SCOPE`. Kaynak `docs/specs_faz6/ekler/evren_listesi.csv`. Çekilişle `vault`, hesaplayıcıyla `regime_tags`, `added_at`.
   - `registry/oot/{inputs,source_docs,candidate_features}/`: `~/Desktop/BorsAi_codex/verified/registry/oot/` altından bayt-eşit kopya. Kopya sonrası sha karşılaştırması raporda.
   - `docs/faz6/dogrulama/`: `REPORT.md`, `EXPOSURE.md`, `coverage.csv`, `verification_log.jsonl`, `_tools/` (KARARLAR D8-5).
   - Denetim: 135/135 `validate_inputs` ve `inputs_pit_problems(root=repo)` boş; kohort doğrulayıcısı temiz. Kasa dağılımı yıl × {OPEN, SEALED, EXPOSED_*} tablosu raporda (hangi kodun SEALED olduğu yazılmaz, yalnız sayılar).
   - Tam pytest + test.sh yeşil → **commit B**.
5. **Rapor** `docs/faz6/INFRA_RAPOR.md` (commit B'ye girer).

**Temizlik bekçileri hakkında (orkestratör ölçtü):** bazı mevcut testler `registry/`, `data/`, `models/` çalışma ağacının temiz olmasını ister: `tests/test_faz4_ceiling_path.py` (~691), `tests/test_faz5_post_d1.py` (~909), `tests/test_scoring.py` (~631). Commit A'nın takvim C dosyası ve commit B'nin `registry/oot/` dosyaları commit edilmeden önce bu testler **yalnız bu görevin kendi yeni dosyaları yüzünden** kırmızı olur; bu beklenir.
- Sıra: önce bu üç temizlik testi `--deselect` edilerek tam koşu yeşil → commit → sonra deselect'siz tam koşu + test.sh yeşil.
- Deselect'siz koşu kırmızıysa düzeltme commit'i at (amend yok).
- Bu testleri gevşetme. Başka bir nedenle kırmızıysa DUR.

Tek oturumda bitmezse: S0b ve yeşil olan en son commit'te dur; kalanı raporda yaz.

## Kurallar
- Yazılabilir: `borsai/` (yukarıdaki dosyalar + yeni `outcomes_oot.py`), `tests/`, `CLAUDE.md` (yalnız D3 metinleri), `docs/SPEC_DEVIATIONS.md` (yalnız I bölümü), `docs/faz6/`, `data/raw/pay_calendar_c_20200101_20230921.csv`, `registry/oot/` (yalnız commit B), bu görev dosyası ve S0b dosyaları.
- Salt okunur: `models/`, `registry/` (oot dışı), `data/` (takvim C dışı), `scores/`, `docs/SCORES.md`, `docs/specs*` (KARARLAR hariç; o S0b'de olduğu gibi commit edilir), `app/`, `legacy/`, `experiments/`, `tests/reference/` mevcut dosyalar.
- Mevcut listeleme öncesi ve POST_D1 akışlarının davranışı değişmez; mevcut testler yeşil kalır. `scores.json` değişmez.
- Ağ yok; hiçbir THB/THM indirilmez; kohort üyelerinin listeleme sonrası verisine bakılmaz.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- Testi gevşetme; kök nedeni bul; gerekirse DUR.
- `git add -A` yok. Commit'ler:
  ```
  git add docs/specs_faz6/KARARLAR.md docs/prompts/FAZ6_CODEX_INPUTS_B1.md docs/prompts/FAZ6_CODEX_INPUTS_B2.md docs/prompts/FAZ6_CODEX_INPUTS_B3.md docs/prompts/FAZ6_CODEX_INPUTS_B4.md docs/prompts/FAZ6_VERIFY_CODEX_INPUTS.md
  git commit -m "BORSAI_FAZ6_S0B: owner decisions (vault 50%, 2020 start, three scales, quarantine extraction) and input collection task files" -- docs/specs_faz6/KARARLAR.md docs/prompts/FAZ6_CODEX_INPUTS_B1.md docs/prompts/FAZ6_CODEX_INPUTS_B2.md docs/prompts/FAZ6_CODEX_INPUTS_B3.md docs/prompts/FAZ6_CODEX_INPUTS_B4.md docs/prompts/FAZ6_VERIFY_CODEX_INPUTS.md
  git add borsai tests CLAUDE.md docs/SPEC_DEVIATIONS.md docs/faz6/OOT_TANIM_ESLEME.md data/raw/pay_calendar_c_20200101_20230921.csv docs/prompts/FAZ6_OOT_INFRA.md
  git commit -m "BORSAI_FAZ6_A: out-of-time cohort infrastructure (registry/oot, vault draw, regime tags, calendar C, --oot writer, quarantine extraction, third scale, guards), no records, no outcomes" -- borsai tests CLAUDE.md docs/SPEC_DEVIATIONS.md docs/faz6/OOT_TANIM_ESLEME.md data/raw/pay_calendar_c_20200101_20230921.csv docs/prompts/FAZ6_OOT_INFRA.md
  git add registry/oot docs/faz6
  git commit -m "BORSAI_FAZ6_S1: pre-H99 cohort membership, vault and regime tags; verified pre-listing inputs and source documents (135 members)" -- registry/oot docs/faz6
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Rapor Türkçe.

## Teslim (rapor)
- Üç commit hash'i, `git show --stat`, sıra.
- Tanım eşleme ve I kararları.
- Test sayıları (taban, A, B): pytest ve test.sh.
- Kasa dağılımı (yıl × küme, yalnız sayılar); regime_tags dağılımı; `TICK_TABLE_MISMATCH` ve `MARGIN_NOT_10PCT` olan arz sayısı.
- Model başına girdisi tam arz sayısı (OPEN kümede ve toplamda): f3 isteyen 5 model, PB modelleri, kurallar.
- İçe aktarım sha denetimi; repo boyut artışı.
- Sonraki görevler için notlar: S2 toplu kayıt, bağımsız denetim, S3/S5 indirme ve ayıklama, S6 skorlama.

## Kabul kapısı
- K1 S0b, A'nın atası; A, B'nin atası; commit'ler yalnız izinli yollarda; push yok.
- K2 Hiçbir kayıt, bülten ya da sonuç dosyası yok (`registry/oot/records`, `d1_rows`, `post_d1`, `data/outcomes_oot` boş; kohort penceresi tarihli zip yok).
- K3 Kasa çekilişi deterministik ve testli; maruz kodlar OPEN.
- K4 135/135 girdi doğrulayıcıdan geçiyor; bayt-eşit içe aktarım.
- K5 CLAUDE.md'de yalnız D3 metinleri; tam pytest ve test.sh yeşil.

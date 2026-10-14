# TASK_ID: BORSAI_FAZ5_POST_D1_LIVE_20260924

Model: Opus 5.5 · Extra. Klasör: ~/Desktop/BorsAi. Ağ gerekmez (bülten indirme testleri yerel sabitlerle). push/tag/amend yok.

## Bağlam
- `post_d1_hazard_v0` donduruldu: `7c18c0f` (F1: `models/post_d1_hazard_v0.json`, sha `3f764026…`; `models/INDEX_POST_D1.json`), `dd7a8cd` (F2: testler, errata, MODELS.md). Fable bağımsız yeniden üretim FREEZE_OK (`docs/fable_faz5_audit/AUDIT.md`). Proje sahibi push eder ve F1 için push kanıtı alır.
- **Canlı akış koşulu gerçekleşti:** nihai λ = 30, INF 2/70 fold → şartname §5 (b) yok → proje sahibi kararı 3 gereği canlı POST_D1 akışı **şimdi kurulur**. Fable teyit etti.
- Bağlayıcı tanım: `docs/specs_faz5/SPEC_POST_D1_V0.md` **§7** (yeni kayıt aşaması `POST_D1`, zaman sınırı, sınıf, kayıt şeması, payda) ve §7.6 (kod ana hatları), §9, §11-13 ve §11-14'ün `registry/post_d1/` kısmı. Şartname DEĞİŞMEZ.
- Bu görev bir sonraki arzda şunu mümkün kılmalı: D1 akşamı resmi bülten yayımlanınca `POST_D1` kaydı yazılır, **D2 09:40'tan önce** push edilir ve push kanıtı alınır; D2..D10 sonuçları gelince skorlanır.
- Uygulama (`app/`) bu görevde değişmez; POST_D1'i EK 3'te okuyacak.

### Proje sahibi kararları (bağlayıcı; aynen)
1. §13 kararları: (1) POST_D1 zaman sınırı **D1'i izleyen ilk resmi seans günü 09:40:00 Europe/Istanbul**; (2) `pb_post_d1_hazard_v0` sonra, ayrı model_id; (3) D1 tavan kapatmayanlar v0'da kapsam dışı; (4) POST_Dj (j ≥ 2) canlı n ≥ 10 olmadan açılmaz; (5) `path_conditional` v0'da kalır, ikincil, birincil hücreyi etkilemez.
2. **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.**
3. POST_D1 modelleri ayrı dizinde: `models/INDEX_POST_D1.json`. `models/INDEX.json` ve listeleme öncesi kayıtlar değişmez. POST_D1 kaydının `models_index` alanı bu dosyayı gösterir; parent (`ceiling_hazard_v0`) sha'sı `INDEX.json` ile denetlenir. Sıra bekçisi ve skorlama iki dizini birlikte okur. Uygulama ikinci dizini EK 3'te okur; o zamana kadar uygulama 19 modelle aynen çalışır.
4. **CLAUDE.md kural 1'in sonuna bu commit'te AYNEN eklenecek cümle** (proje sahibi onayı 2026-09-24; son cümle Fable bulgusu K7 üzerine onaylandı):
   > Her kayıt kendi aşamasının dizinindeki tüm modelleri içerir (listeleme öncesi: models/INDEX.json; POST_D1: models/INDEX_POST_D1.json). POST_D1 kaydının zaman sınırı D1'i izleyen ilk seans günü 09:40 (Europe/Istanbul), zaman kanıtı push kanıtıdır. Bir POST_D1 modeli, kendisinden sonra repoya giren her sonuç commit'inin atasıdır; ondan önce girmiş sonuçlar o model için RETRO'dur.

### Paralel çalışma
- Codex (repo dışında) eski kohort girdilerini topluyor; repoya yazmaz.
- Orkestratör bu oturum sürerken `docs/prompts/FAZ6_*.md` ve `docs/specs_faz6/KARARLAR.md` dosyalarını yazabilir. Bunlar izinli izlenmeyen sayılır; onlara dokunma, commit'ine alma.
- `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.

## Görev kararları (Fable denetimi bunları şartname sayar; `docs/SPEC_DEVIATIONS.md` H bölümüne devam numarasıyla yaz)
- **L1 Skor çıktısı ayrı dosyada.** POST_D1 skorlaması `scores/scores_post_d1.json`'a (şema `borsai.scores_post_d1/1`) ve `docs/SCORES.md`'ye yeni bir bölüm olarak yazılır. `scores/scores.json`'un yapısına POST_D1 bloğu EKLENMEZ (uygulama onu gömer ve bütünlüğünü denetler; karar 3). Koşullu j = 1 satır şeması Faz 2C'ninkiyle aynı alan adlarını kullanır (EK 3 okuyacak).
- **L2 Payda.** `registry/ipos.csv`'nin şeması ve mevcut satırları değişmez. §7.5'in POST_D1 aşaması satırları skorlamada `ipos.csv` + `registry/post_d1/` + D1 etiketlerinden hesaplanır ve `scores_post_d1.json`'a yazılır (`n_scored / n_refused / n_skipped / n_not_applicable / n_target_unavailable / n_live / n_late`, `retro_info`).
- **L3 Bugünkü 7 arz** (CITAS, VEYAS, TKNKA, KPEKS, INTET, BKRGY, NETGL) bu model için RETRO'dur: yalnız `retro_info`. Onlar için gerçek `registry/post_d1/` kaydı YAZILMAZ.
- **L4 Uçtan uca prova (geçici klonda, repoya yazmadan):** NETGL'in pinli D1 bülteni ve birincil listeleme öncesi kaydıyla `freeze --post-d1 NETGL` akışı koşulur (zaman enjeksiyonuyla). Denetimler: kayıt şeması §7.4 birebir; model çıktısı doğrudan `predict_post_d1` ile `==`; `comparators_conditional` kopyası Faz 2C `scores.json` j = 1 NETGL satırıyla |Δ| ≤ 1e-12; sınıf RETRO; bekçiler yeşil. Çıktı `docs/faz5/ekler/prova_netgl.txt`.
- **L5 Bülten sütunları.** `THB_COLUMNS` eki §7.6 listesi + `OZEL ISLEM BILDIRIMI ISLEM ADEDI` / `…ISLEM HACMI` (Fable bulgusu H19). Adları repodaki pinli 2026 THB başlığıyla birebir doğrula. `OUTCOME_COLUMNS` değişmez. Regresyon: mevcut pinli bültenlerden `data/outcomes/*.csv` yeniden üretilince bayt-eşit (ağsız; yalnız yerel dosyalar).
- **L6 Zaman.** `t_open` = resmi takvimde (`official_sessions`, ilan dışı kapanışlar düşülmüş) D_1'den sonraki ilk seans + `09:40:00+03:00` sabiti; yerel saat kullanılmaz. Takvim 2026-12-31'de bitiyor: takvim dışı D_1 için tahmin yerine etiketli hata (`CALENDAR_NOT_AVAILABLE`); tahmin etme.
- **L7 Sıra bekçisi.** `sequence_guard`, `registry/post_d1/` altında commit edilmemiş dosya varken bülten indirmeyi durdurur (§7.4 son madde). `tests/test_outcome_guard.py`: `registry/post_d1/` altında yalnız `d1` bloğunda ve yalnız D_1 tarihli alanlar; h ≥ 2 anahtarı ya da D_1 dışı bülten sha'sı → kırmızı; `data/outcomes` h ≥ 2 OK satırı ilgili bülten commit'inden önce olamaz.
- **L8 Donmuş JSON etiketi.** `models/post_d1_hazard_v0.json` ve `INDEX_POST_D1.json`'daki `training.cutoff_date` / `training_cutoff_date` = 2026-08-13, δ eğitim arzlarının 10 seansının en geç tarihidir (`post_d1.py` 793); şartnamenin kesimi (2026-08-19) ya da δ satırlarının en geç seansı (2026-08-05, KARCL d = 4; Fable ölçtü) değildir. Model sayılarını etkilemez; donmuş dosya DEĞİŞMEZ. Anlamını H'ye yaz; okuyucular (kayıt, EK 3) bu alanı "kesim" diye göstermesin.
- **L9 K5 kapanışı.** Skor yeniden üretiminde kart sayacı `n_variants_same_data` 20 olur; H22 test istisnası (`scores_json_is_pre_faz5`) kendiliğinden devre dışı kalmalı. Bunu gösteren test.
- **L10 Akış belgesi.** `docs/faz5/POST_D1_AKISI.md`: D1 akşamı yapılacaklar komut düzeyinde (kim, ne zaman, hangi komut, son tarih `T_open`), başarısızlık hâlleri (D1 tavan değil, D1 işlem görmedi, üst limit yok, `base_record` yok, T_open geçti) ve her birinde ne olacağı. Orkestratör bir sonraki arzın görevini bundan yazacak.

ÖNCE OKU:
- CLAUDE.md
- docs/specs_faz5/SPEC_POST_D1_V0.md (§1.3, §2, §7 tamamı, §9, §11-13, §11-14, §12 canlı sınıf)
- docs/specs/SPEC_SCORING.md (§2, §3, §5, §6, §8, §9)
- docs/SPEC_DEVIATIONS.md (E, G, H)
- docs/fable_faz5_audit/AUDIT.md §4, §7
- borsai/: outcomes.py (`THB_COLUMNS`, `REQUIRED`, `ThbRow`, `update`, `sequence_guard`, MANIFEST), registry.py (`select_primary`, `Candidate`), freeze.py (`build_record`, `write_record`, `cancel_record`, `freeze_post_d1`, `model_kind`, `run_model`), predict_post_d1.py, push_proof.py (`earliest_proof`), scoring.py (`pair_class`, `outcome_ingest_commit`, `_need_names`, koşullu j blokları, `build_scores`, `render_doc`, `sequence_violations`)
- tests/test_outcome_guard.py, tests/test_scoring.py, tests/test_scoring_conditional.py, tests/test_freeze_records.py, tests/test_push_proof.py (geçici git deposu ve kanıt taklidi kalıpları)

## Adımlar
0. **Taban:** `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -4`, `git status --porcelain`. İzinli izlenmeyen: `docs/prompts/FAZ5_POST_D1_LIVE.md`, `docs/prompts/FAZ6_*.md`, `docs/specs_faz6/KARARLAR.md`. Başka bir şey varsa DUR. `.venv/bin/pytest -q` tam koşu (sayı, süre); kırmızı varsa DUR.
1. **Tanım eşlemesi (kod yazmadan):** §7'nin her cümlesi → dosya:fonksiyon tablosu `docs/faz5/LIVE_TANIM_ESLEME.md`. Boşluk ya da iki okumalı yer: lafza göre karar, H'ye yaz.
2. **Uygulama (commit A):** §7.6 ana hatları + L1–L10:
   - `outcomes.py`: sütun eki (L5); `update` D_1 bültenlerini indirir, `data/outcomes/<T>.csv` h = 1 OK, h ≥ 2 PENDING; `sequence_guard` (L7).
   - `registry.py`: `POST_D1_DIR`, `t_open` (L6), `select_primary_post_d1`, `DUPLICATE_RECORD`, iptal yalnız `T_open`'dan önce.
   - `freeze.py`: `build_post_d1_record`, `write_post_d1_record`, CLI `--post-d1 <TICKER>` (ve iptal); `base_record` seçimi SPEC_SCORING §6 (`ceiling_hazard_v0` birincil kaydı); f1–f3 o kaydın `model_inputs`'undan; `INDEX_POST_D1.json`'daki her model; `comparators_conditional` kayıttan kopya; uygun `base_record` yoksa kayıt yazılmaz.
   - `scoring.py`: `outcome_ingest_commit_post_d1`, `model_prospective_post_d1`, `inputs_pit_ok_post_d1`, `class_post_d1`; `_need_names("post_d1")` = k = 2..10 (+ `path_conditional` varsa h ∈ {3, 5, 10}); D1 hedefi hiçbir zaman skorlanmaz; birincil hücre koşullu RPS_1 vs `ceiling_hazard_v0` koşullu; n kuralları SPEC_SCORING §8; `ScaleMixError` (`live_post_d1` ölçeği hiçbir şeyle birleşmez); çıktı L1–L2.
   - `CLAUDE.md` kural 1 cümlesi (karar 4) AYNEN.
   - Testler: §11-13 (a)–(j) geçici git depolarında (push kanıtı taklidi, zaman enjeksiyonu, sistem saatine dokunmadan); §11-14 `registry/post_d1/` bekçisi; L4 prova; L5 regresyonu; L6 takvim sınırı; L9.
   - `docs/faz5/POST_D1_AKISI.md` (L10), SPEC_DEVIATIONS H satırları.
   - Tam pytest yeşil → `docs/faz5/ekler/live_test_runs.txt` → **commit A**.
3. **Skor yeniden üretimi (commit B):** `python -m borsai.scoring` (outcomes güncellemesi YAPMA; veri `as_of_session` 2026-09-21'de kalır).
   - `scores/scores.json` farkı YALNIZ `generated_at_utc`, `code` ve kartlardaki `n_variants_same_data` (19 → 20) olabilir; başka bir alan değiştiyse DUR, B'yi atma, nedenini raporla.
   - `scores/scores_post_d1.json` yeni: 7 arz `retro_info`, sayaçlar 0, hücre yok.
   - `docs/SCORES.md` POST_D1 bölümü.
   - Tam pytest yeşil. Uygulama testleri: `bash app/scripts/test.sh`. Kırmızıysa `app/`'e DOKUNMA; B'yi atma, kök nedeni raporla.
   - Yeşilse **commit B**, sonra uygulamayı yeniden derle (gömülü `scores.json` güncellensin): `source app/scripts/env.sh && cd app && npm run tauri build -- --bundles app`. `/Applications`'a kopyalama.
4. Rapor.

Tek oturumda bitmezse: A yeşil ve commit'liyse orada dur, B'yi raporda bırak. A bitmediyse yalnız yeşil kısmı `BORSAI_FAZ5_LIVE_A (partial): …` ile commit et.

## Kurallar
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** Model davranışı değişmez: `predict_post_d1`, `post_d1.py` fit kodu ve donmuş JSON'lar dokunulmaz.
- Yazılabilir: `borsai/` (yukarıdaki dosyalar), `tests/`, `CLAUDE.md` (yalnız karar 4 cümlesi), `docs/SPEC_DEVIATIONS.md` (yalnız H eki), `docs/faz5/`, `scores/`, `docs/SCORES.md` (commit B), bu görev dosyası.
- Salt okunur: `models/` (hepsi), `registry/` (mevcut bütün dosyalar; `registry/post_d1/` gerçek repoda BOŞ kalır), `data/`, `docs/specs*`, `docs/app/`, `docs/fable_*`, `app/`, `legacy/`, `experiments/`, `tests/reference/` altındaki mevcut dosyalar.
- Listeleme öncesi kayıtların yazımı (`build_record`) ve mevcut 19 modelin skor blokları davranış olarak değişmez; mevcut testler yeşil kalır.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- Testi gevşetme; kök nedeni bul; gerekirse DUR.
- `git add -A` yok. Commit'ler:
  ```
  git add borsai tests CLAUDE.md docs/SPEC_DEVIATIONS.md docs/faz5 docs/prompts/FAZ5_POST_D1_LIVE.md
  git commit -m "BORSAI_FAZ5_LIVE_A: live POST_D1 record stage, 09:40 time bound, class and scoring definitions in code, guards (SPEC_POST_D1_V0 §7), no score data" -- borsai tests CLAUDE.md docs/SPEC_DEVIATIONS.md docs/faz5 docs/prompts/FAZ5_POST_D1_LIVE.md
  git add scores docs/SCORES.md docs/faz5/LIVE_RAPOR.md
  git commit -m "BORSAI_FAZ5_LIVE_B: scores regenerated (variant counter 20, separate scores_post_d1.json with retro_info only)" -- scores docs/SCORES.md docs/faz5/LIVE_RAPOR.md
  ```
- Rapor Türkçe.

## Teslim (rapor)
Raporu sohbete ve `docs/faz5/LIVE_RAPOR.md`'ye yaz (A'ya girer; B sonuçlarını B commit'inden önce "B" başlığıyla ekle, B'ye de girer).
- Commit hash'leri, `git show --stat`, A'nın B'nin atası olduğu.
- Tanım eşleme tablosu, H kararları.
- §11-13 (a)–(j) ve diğer testlerin sonuçları; test sayıları (taban, A, B).
- L4 prova çıktısı özeti; L5 regresyonu.
- `scores.json` fark özeti (hangi anahtarlar); `scores_post_d1.json` özeti.
- `bash app/scripts/test.sh` ve derleme sonucu (yeni `.app`'in `borsai-app` sha256'sı).
- `POST_D1_AKISI.md`'nin kısa özeti.
- Sapmalar, açık noktalar (EK 3 için notlar dahil).

## Kabul kapısı
- K1 §11-13 (a)–(j), `registry/post_d1/` bekçisi, L4–L9 testleri ve tam pytest yeşil.
- K2 `models/`, mevcut `registry/` dosyaları, `data/`, `app/` kaynakları, `docs/specs*` değişmedi; `registry/post_d1/` gerçek repoda boş.
- K3 CLAUDE.md'de yalnız karar 4 cümlesi eklendi, metin birebir.
- K4 `scores.json` farkı yalnız izinli alanlar; `scores_post_d1.json` ayrı; uygulama testleri yeşil; `.app` yeniden derlendi.
- K5 A, B'nin atası; commit'ler yalnız izinli yollarda; push yok.

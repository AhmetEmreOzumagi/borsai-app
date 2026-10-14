# TASK_ID: BORSAI_FAZ2B_OUTCOMES_SCORING_20260922

Model: Opus 5 · Extra. Çalışma klasörü ~/Desktop/BorsAi (ek dizin gerekmez; eski toplayıcı `legacy/` altında). Ağ: yalnız borsaistanbul.com (THB/THM zip'leri, resmi takvim/duyuru). push/tag/amend yok.

## Bağlam

- Faz 1 modelleri dondurulup push edildi: 5fa849d (v1_5_h99 + basit kurallar), b09cab5 (diğer 9 model).
- Faz 2A push edildi (`1869da6..7cb49cf`). İçinde `registry/ipos.csv`, `registry/inputs/` ve 7 arz × 16 model tahmin kaydı (`registry/records/`) var.
- Push kanıtları (`registry/push_proofs/`) bu görevden hemen önce proje sahibi tarafından commit edilip push edildi.
- Bu görev resmi sonuç verisini getirir ve ilk canlı skoru üretir. İki commit atılır:
  - **Commit A:** tanımlar ve kod. Sonuç verisi yok.
  - **Commit B:** sonuç verisi ve skorlar.
  - A, B'nin atası olur. Böylece tanımların sonuçtan önce kodda yazıldığı git'ten görülür (CLAUDE.md kural 6, SPEC_SCORING Özet 1).
- Beklenen durum. Bunlar yalnız beklentidir; kod her şeyi tarihlerden ve DAG'dan hesaplar, hiçbir şey elle yazılmaz:
  - 7 arzın tamamı Faz 1 modelleri için LATE_RECORD olur, çünkü kayıtların push'u ilk işlem gününden sonra yapıldı.
  - NETGL'de `v1_5_h99` legacy git+push kaydı LIVE olur.
  - BKRGY ve INTET'te `v1_5_h99` self-reported ikincil satırda görünür.
  - TKNKA'nın `v1_5_full20` modeli ayrı bir listede durur.
  - n = 7 < 10 olduğundan yalnız satır tablosu üretilir; metrik üretilmez (SPEC_SCORING §8).
- NETGL'nin ilk işlem günü 2026-09-17. D10'u henüz oluşmamış olabilir; oluşmayan ufuklar PENDING kalır.
- 2A görev dosyasında bir hata vardı: "ikinci kayıt ancak iptalden sonra" kuralı SPEC_SCORING §6 ile çelişiyor. Adım 3'te bu düzeltilir.

ÖNCE OKU:
- CLAUDE.md
- docs/specs/SPEC_SCORING.md (tamamı, bağlayıcı)
- docs/SPEC_DEVIATIONS.md (özellikle C7)
- docs/prompts/FAZ2A_REGISTRY_INPUTS.md
- borsai/registry.py, freeze.py, push_proof.py, metrics.py, survival.py
- registry/legacy_roles.json
- tests/test_outcome_guard.py, tests/test_faz1b_guardrails.py, tests/test_guardrails.py
- legacy/scripts/collect_historical99_bist_raw_v1.py:
  - THB/THM sütunları :170-185
  - `source_url` :324
  - `parse_archive_bytes` :403
  - `build_session_record` :563
- data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv (H99 ham alanları ve her zip'in sha256'sı)
- Takvimler:
  - data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv
  - data/raw/pay_calendar_b_extension_20260820_20261231.csv

## Adımlar

### 0. Başlangıç ölçümü
- `git log --oneline -3` ve `git status --porcelain` çalıştır. HEAD'de 7cb49cf'nin üstünde push kanıtı commit'i olmalı ve `registry/push_proofs/` içinde 5fa849d, b09cab5 ve 7cb49cf'nin kanıtları bulunmalı. Değilse DUR ve raporla.
- `.venv/bin/pytest -q` ile tam koşu yap; test sayısını ve süreyi yaz. Kırmızı test varsa DUR ve raporla.
- Tam koşu uzun sürebilir. Geliştirirken yalnız ilgili testleri koş; tam koşuyu her commit'ten önce yap.

### COMMIT A: tanımlar (sonuç verisi YOK)

Commit A atılana kadar yasaklar:
- 2026-08-17'den sonraki hiçbir THB/THM dosyası indirilmez, açılmaz, okunmaz.
- 2026-08-06'dan sonra listelenen arzların fiyatına hiçbir kaynaktan bakılmaz.

**1. `borsai/outcomes.py`**
- **İndirici.** Kaynak kalıbı SPEC_SCORING §1'de. Legacy toplayıcıdaki `source_url` ve `parse_archive_bytes`'ı porta taşı; `legacy/` değişmez.
  - Ham zip baytları olduğu gibi `data/raw/bist/thb/YYYY/thbYYYYMMDD1.zip` ve `data/raw/bist/thm/YYYY/thmYYYYMMDD1.zip` altına yazılır.
  - Manifest: `data/raw/bist/MANIFEST.csv` (date, kind, url, sha256, bytes, internal_filename, downloaded_at).
  - Var olan dosya yeniden yazılmaz.
- **Ayrıştırıcı.** Değerler ham metinden `Decimal(str)` ile alınır; float'a hiç girmez.
- **Kaynak sınaması.**
  - 2026-08-17 THB ve THM zip'lerini indir. sha256'ları SESSIONS dosyasındaki `thb_sha256`/`thm_sha256` ile birebir aynı olmalı.
  - Bu iki zip commit A'ya girer. 2026-08-17'de işlem gören post-08-06 arz yok; CITAS'ın D1'i 08-18.
  - sha tutmazsa DUR: kaynak değişmiş olabilir. Testi gevşetme.
- **`resolve_sessions` ve `ceiling_label`.** SPEC_SCORING §2, §3 ve §9'daki sözde kod. Takvim: H99 takvimi ile 2A uzatmasının birleşimi.
  - D_1 = THB'de payın traded olduğu ilk resmi seans.
  - Kayıttaki ilk işlem tarihiyle farklıysa fark raporlanır.
- **Sonuç dosyası:** arz başına tek dosya, `data/outcomes/<TICKER>.csv` (SPEC_SCORING §1).
  - Satırlar h = 1..10. Sütunlar: session_date, close_raw, upper_limit_raw, reference_raw, trade_count_raw, halt_flag, half_day, shifted_by_suspension, ceiling_close, thb_sha256, thm_sha256, status.
  - R_h ve Y_h yalnız h ∈ {1, 3, 5, 10} satırlarında doldurulur.
  - status ∈ {OK, PENDING, TARGET_UNAVAILABLE, NA_LIMIT}.
  - ipo_price `registry/inputs/<TICKER>.json`'dan alınır.
- **Komut:** `python -m borsai.outcomes update [--through YYYY-MM-DD]`.
  - Eksik seansların zip'lerini indirir ve `ipos.csv`'deki kapsam içi her arzın sonuç dosyasını üretir.
  - Yeniden koşuda yalnız PENDING satırları dolar. Dolu bir satır değişecekse komut hata verir; bu, resmi verinin değiştiği anlamına gelir.
- **Tamlık denetimi (SPEC_SCORING §4).**
  - Pencere boyunca Pay Piyasası THB'sinde ilk kez görünen işlem kodlarını listele.
  - `ipos.csv`'de olmayan her kod için neden yaz: kod değişikliği, pazar değişikliği, fon, varant ya da yeni arz.
  - Yeni bir halka arz çıkarsa DUR ve raporla. `ipos.csv` satırı proje sahibinin onayıyla eklenir.

**2. `borsai/scoring.py`**
- **`classify(m, a)`.** SPEC_SCORING §5 formülü: git DAG (`git merge-base --is-ancestor`), `registry/push_proofs` ve `inputs_pit_ok`. Elle sınıf alanı yoktur.
- **Birincil kayıt.** `registry.select_primary` (2A) ve `legacy_roles.json` kullanılır. İptal edilmiş kayıt skorlanmaz.
- **Metrikler ve aralıklar.**
  - Metrikler SPEC_SCORING §7'ye göre.
  - Bootstrap §8'e göre: numpy `PCG64(20260921)`, 4000 tekrar. Aralık ancak n ≥ 10 ve en az 6 blok varsa üretilir.
  - Backtest'teki `random.Random` uygulamasına dokunma (C7).
- **Küçük n.** n < 10 → yalnız satır tablosu; metrik alanları `null` (§8).
- **Komut:** `python -m borsai.scoring`. Çıktılar: `scores/scores.json` ve `docs/SCORES.md`.
- **İki terazi** ayrı bloklarda durur. Hiçbir alan ikisini birleştirmez ya da ortalamasını almaz.
- **`scores/scores.json` şeması** (`schema_version: "borsai.scores/1"`; masaüstü uygulaması bunu okuyacak):
  ```
  { schema_version, generated_at_utc,
    as_of_session,                      skora giren en son THB tarihi
    code: {git_head, borsai_source_sha256},
    inputs: {outcomes_sha256, records_sha256, models_index_sha256},
    models: [ {
      model_id, kind,
      card: {training_n, training_cutoff, params_sha256_8, n_variants_same_data},
      primary_cell,                     SPEC_SCORING §7'de önceden ilan edilen hücre
      backtest: {title: "Geçmiş veri testi (retrospektif, tasarıma maruz)",
                 cells: [ {output, horizon_or_k, metric, model_value, rule_id, rule_value,
                           diff, ci95, n, wins, losses, ties, verdict} ]},
      live: {title: "Canlı sicil (prospektif)",
             n_live, n_late, n_scored, n_refused, n_skipped, n_target_unavailable, n_pending,
             rows: [ {ticker, d1, class, record_id, prediction, rules, realized, status} ],
             cells: [],                 yalnız n ≥ 10 olduğunda doldurulur
             self_reported_rows: [ ... ]} } ],
    skipped: [ ipos.csv'deki SKIPPED ve OUT_OF_SCOPE satırları ],
    retro_info: [ RETRO sınıfındaki (model, arz) çiftleri, yalnız bilgi ] }
  ```
  - `verdict` ∈ {"geçiyor", "geçemiyor", "ayırt edilemiyor", "yetersiz örnek", "aralık için yetersiz", null}. Seçim yalnız §8 kurallarıyla yapılır.
  - Backtest hücreleri var olan fold ledger'larından alınır; yeniden fit yapılmaz. Değerler `docs/MODELS.md`'dekilerle aynı olmalı ve bunu bir test sınamalı.
  - Şemaya alan eklenebilir, alan kaldırılamaz. Eklenen alanları raporla.

**3. `borsai/freeze.py` düzeltmesi**
- "İkinci kayıt ancak iptalden sonra" kuralı kaldırılır. Aynı arz için birden çok etkin kayıt olabilir (önce talep öncesi PB kaydı, sonra talep katlı kayıt). Hangisinin skorlandığına SPEC_SCORING §6 karar verir.
- Korunacaklar:
  - Dosya asla yeniden yazılmaz.
  - Aynı `input_sha256` ve aynı models_index sha'sıyla ikinci kayıt reddedilir (`DUPLICATE_RECORD`).
  - İptal yalnız D_1'den önce yapılabilir.
- İlgili testleri güncelle.

**4. Bekçi testleri (sıra kuralı)**
- `tests/test_outcome_guard.py` bugün "hiç sonuç yok" diye denetliyor. "Sonuç ancak sırayla" denetlemesine dönüştür:
  - 2026-08-19 sonrası tarihli her THB/THM dosyası ve post-08-06 her arzın `data/outcomes/<T>.csv` dosyası için, o dosyayı ekleyen commit'in ataları şunları içermeli:
    - (a) `models/INDEX.json`'daki şimdiki 16 model JSON'unu ekleyen commit'ler,
    - (b) o arzın `registry/records` kaydını ekleyen commit.
  - Commit edilmemiş sonuç dosyası için aynı koşul HEAD'e karşı denetlenir.
- Bundan sonra eklenecek bir model sonuçtan sonra dondurulursa test kırmızı olmaz; o model o arz için RETRO'ya düşer (bu, sınıflamanın işi).
- `tests/test_guardrails.py` ve `tests/test_faz1b_guardrails.py` eğitim verisini ve model girdilerini korur. Değişmezler ve yeşil kalmalılar.
- SPEC_SCORING §10'daki kabul testlerinin 1–11 hepsi yazılır.

**5. Commit A**
- Tam koşu yeşil olduktan sonra commit at.
- Mesaj: `BORSAI_FAZ2B_A: outcome and scoring definitions in code before any post-listing outcome data (SPEC_SCORING)`
- Yollar (açık `git add`):
  - `borsai/`
  - `tests/`
  - `data/raw/bist/` (yalnız 2026-08-17 zip'leri ve MANIFEST.csv)
  - `docs/PROVENANCE.md`
  - `docs/SPEC_DEVIATIONS.md` (yeni satır varsa)
  - `docs/prompts/FAZ2B_OUTCOMES_SCORING.md`

### COMMIT B: sonuç verisi ve ilk canlı skor

6. `python -m borsai.outcomes update` çalıştır: 2026-08-18'den erişilebilen son THB'ye kadar. Bugünün bülteni henüz yayımlanmadıysa bir önceki seansta dur.
7. Tamlık denetimini çalıştır.
8. `python -m borsai.scoring` çalıştır.
9. Tam koşu yeşil olduktan sonra commit at.
   - Mesaj: `BORSAI_FAZ2B_B: official THB/THM outcomes for post-2026-08-06 IPOs and first live scoring (n < 10: row table only)`
   - Yollar: `data/raw/bist/`, `data/outcomes/`, `scores/`, `docs/SCORES.md`, `docs/PROVENANCE.md`

## Kurallar
- Şu yollar DEĞİŞMEZ:
  - `models/`, `tests/reference/`, `legacy/`, `docs/specs/`
  - `registry/` altındaki her şey (`ipos.csv` dahil)
  - `data/training_table.csv`
  - `data/raw/` altındaki mevcut dosyalar
- Dondurulmuş hiçbir değer yeniden hesaplanıp yerine yazılmaz. Model JSON'undan yeniden tahmin yalnız parite denetimidir (|Δ| ≤ 1e-9) ve skora girmez.
- Commit A'dan sonra tanımlar değişmez. Commit B sırasında bir tanım hatası bulursan DUR ve raporla; B'yi atma.
- Testi gevşetme. Kök nedeni bul; gerekirse DUR.
- `docs/app/` ve `docs/prompts/FAZ3_*` başka bir oturuma ait (paralel çalışan Fable). Onlara dokunma, commit'e ekleme.
- `git add -A` YOK; yalnız yukarıda sayılan yollar.
- Rapor Türkçe.

## Teslim (rapor)
- İki commit'in hash'i ve `git show --stat` özetleri; A'nın B'nin atası olduğunu gösteren `git merge-base --is-ancestor` çıktısı.
- Başlangıç ve son tam test koşusu: test sayısı ve süre.
- H99 kabul testi: 990 seans, 396 hedef, 990 tavan etiketi, 99 L; toplamlar 81/67/48/25 ve 81/66/41/14.
- 2026-08-17 zip'lerinin sha eşleşmesi.
- İndirilen seans aralığı, dosya sayısı, toplam boyut ve takvimle uyuşmazlıklar (ör. UNANNOUNCED_CLOSURE).
- Tamlık denetimi listesi.
- Arz × ufuk tablosu: D_1 (kayıttaki tarihle karşılaştırmalı), D_h tarihleri, R_h, Y_h, tavan etiketleri, L, durum (PENDING dahil).
- Arz × model sınıf tablosu (LIVE / LATE_RECORD / RETRO / legacy) ve seçilen birincil kayıt.
- `docs/SCORES.md`'deki satır tablosu.
- Sapmalar, belirsizlikler ve verdiğin kararlar.

## Kabul kapısı
- K1 A, B'nin atası. A'da 2026-08-17 sonrası THB/THM ve post-08-06 arz sonucu yok (git'ten kanıt).
- K2 SPEC_SCORING §10 kabul testleri 1–11 yeşil; H99 yeniden üretimi birebir.
- K3 Sınıf ve birincil kayıt koddan hesaplanıyor; şemada elle sınıf alanı yok.
- K4 n < 10 olduğu için hiçbir canlı metrik, ortalama ya da "geçiyor" ifadesi yok.
- K5 `models/`, `tests/reference/`, `legacy/`, `docs/specs/` ve `registry/` değişmedi.
- K6 push, tag, amend yok.

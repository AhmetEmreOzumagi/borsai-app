# 10. Dosya dizini: repoda ne nerede

Bu bölüm, kitabın dayandığı repo kopyasındaki klasörleri ve önemli dosyaları tek tek gösterir. Kopyanın HEAD'i `ee3796d`'dir (6 Ekim 2026). Tablolardaki "Yol" sütunu repo köküne göre verilir. "Bölüm" sütunu dosyanın en ayrıntılı anlatıldığı yeri gösterir; "—" o dosyanın kitapta ayrıca anlatılmadığı anlamına gelir.

Okuma notları:

- **Yer tutucular.** `<T>` bir arz kodunu (ör. NETGL) gösterir. `<zaman>` `20260922T121936Z` biçiminde bir UTC damgasıdır. `<kısa-sha>` dosya baytlarının sha256'sının ilk 12 hanesidir (içerik adresli ad, §6.11.2).
- **Bu kopyada olmayanlar.** PDF, zip, xls, png ve woff2 gibi ikili dosyalar kitabın kopyasına alınmadı. Bunlar "bu kopyada yok, gerçek repoda var" diye işaretlidir. Repo dışında duran dosyalar ayrıca belirtilir.
- **Toplu yazılanlar.** Eski kohortta dosya adı arz kodu taşıyan dosyalar (`data/outcomes_oot/`, `registry/oot/` alt klasörleri, `docs/faz6/dogrulama/_tools/decisions/`) tek tek listelenmez, yalnız sayıları verilir. Resmî bülten zip'lerinin adları da yazılmaz. Bu, kasanın körlüğünü koruyan proje kuralıdır (§6.12.3).
- **Görev dosyaları.** `docs/prompts/` altındaki 79 görev dosyası burada tek satırla geçer; kataloğu §2.5'tedir.

## Kök dizin

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `CLAUDE.md` | Projenin bağlayıcı kuralları: dondurma, payda, üç terazi, deney günlüğü, değişiklik = yeni `model_id`, skorlama ve sıra kuralı. Her Claude Code oturumu işe bunu okuyarak başlar. | §6.2, §2.4.8 |
| `pyproject.toml` | `borsai` paketinin tanımı (sürüm 0.0.0, Python ≥ 3.12 ve < 3.13). Çalışma bağımlılıkları birebir pinlidir: numpy 2.5.2, scikit-learn 1.9.0, scipy 1.18.0, joblib 1.5.3, threadpoolctl 3.6.0, narwhals 2.26.0. Geliştirme eki pytest 9.1.1 ve pytest-xdist 3.8.0'dır. pytest ayarı da buradadır (`testpaths = tests`). | §2.8 |
| `requirements.lock` | Sanal ortamın 13 satırlık tam sürüm listesi; doğrudan ve dolaylı bütün paketler. | §2.8 |
| `.gitattributes` | Bütün metin dosyalarını LF satır sonuyla tutar (`* text=auto eol=lf`) ve ikili türleri işaretler. CRLF'ye dönen bir JSON'un sha256'sı bozulacağı için vardır. | §7.5 |
| `.gitignore` | `.venv/`, `__pycache__/`, `.DS_Store`, `.pytest_cache/` ve `*.pyc` git'e girmez. | §2.8 |
| `.claude/` | Claude Code'un yerel ayar klasörü; bu kopyada boş. | — |
| `GITLOG.txt` | Git geçmişinin dökümü: 175 satır, her satır kısa sha, tarih ve commit konusu, en eskiden en yeniye. Kopyada `.git` olmadığı için kitap tarihleri buradan okur. Kopya hazırlanırken eklendi (dosya sahibi ve tarihi diğerlerinden farklı); gerçek repoda izlenen bir dosya olup olmadığı belirsiz. | §2.3.1 |
| `.DS_Store` | macOS Finder'ın gizli klasör ayar dosyası; git'e girmez. | — |

Klasörler: `borsai/` (Python paketi), `data/` (veri), `models/` (donmuş modeller), `registry/` (sicil), `scores/` (skor dosyaları), `experiments/` (deney günlüğü), `legacy/` (eski repodan kopya), `tests/` (Python testleri), `docs/` (belgeler), `app/` (masaüstü uygulaması).

## borsai/

Projenin Python paketi: 39 modül, yaklaşık 26 bin satır. `predict*` modülleri yalnız standart kitaplıkla yazılır; fit ve backtest modülleri numpy ve scikit-learn kullanır. Komut satırından çağrılan modüller `python -m borsai.<modül>` biçiminde koşar.

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `borsai/__init__.py` | Paketin tanıtımı ve modül haritası; kod içermez. | §2.8 |
| `borsai/backtest.py` | Walk-forward backtest motoru ve planları (`PLAN_V15` ve şartnamelerdeki diğer planlar). Fold'ları kurar, her fold'da modeli yeniden fit eder, ledger yazar. Her koşu sonunda deney günlüğüne kendisi satır ekler. CLI. | §6.5, §6.13 |
| `borsai/ceiling_path.py` | Tavan yolu modellerinin verisi, backtest'i, dondurulması ve koşullu (keşif) değerlendirmesi. Tahmin matematiği `predict_path.py`'dedir. | §4.6 |
| `borsai/data.py` | Eğitim tablolarını yükler ve `data_version*.json`'daki sha256 ile doğrular (`load_dataset`). Seans tarihleri ve PB girdileri de buradan okunur. | §3.8.2, §3.8.3 |
| `borsai/features.py` | f1–f5 ve pb1–pb4 özelliklerinin tek tanımı; kesin ondalık (`decimal`) aritmetiği. | §3.6.1, §3.6.4 |
| `borsai/fit.py` | Model fit'i: V1.5 ailesinin Ridge ve L2-lojistik ızgaraları, iç LOOCV ve eşitlik kuralları; eski repodaki `candidate_models.py`'nin portu. | §4.2, §4.3 |
| `borsai/freeze.py` | Dondurma: modelleri `models/` altına, tahmin kayıtlarını `registry/records/` altına yazar. İptal, POST_D1, eski kohort ve kırılma akşamı kayıtları da buradadır. CLI (`--post-d1`, `--cancel`, `--oot`, `--only-missing-models` vb.). | §6.11 |
| `borsai/hazard.py` | Ayrık zamanlı tehlike modelinin fit'i: `ceiling_hazard_v0`, `pb_ceiling_v0`, Faz 7 `ceiling_hazard_v1_*` ve `@INF` uçları. | §4.4.5, §4.7 |
| `borsai/horizons.py` | Ufuklar (D1, D3, D5, D10) ve fiziksel getiri sınırı R_h ∈ [0,9^h − 1; 1,1^h − 1]. | §3.5.3 |
| `borsai/market20.py` | f6: XU100'ün 20 seanslık getirisi ve takvim sonu denetimi. | §3.6.2 |
| `borsai/metrics.py` | Skor tanımları (MAE, Brier, log-kayıp, RPS) ve eşleşik fark aralığı; eski repodaki `metrics.py` ile birebir. | §6.6, §6.7 |
| `borsai/outcomes.py` | Resmî sonuç verisi: THB ve THM bültenlerinden `data/outcomes/<T>.csv` üretir; indirme, sıra kuralı ve tamlık denetimi. CLI (`fetch`, `update --through`, `completeness`). | §3.2.1, §3.10 |
| `borsai/outcomes_oot.py` | Eski kohortun sonuç verisi: repo dışı karantinada indirme ve ayıklama, kasaya hijyen. CLI (`--pace`, `--quarantine`). | §3.11, §6.12.4 |
| `borsai/post_break.py` | Kırılma akşamı modeli `break_floor_v0`: kırılma tablosu, walk-forward, karşılaştırıcılar ve nihai fit önizlemesi. CLI (`--official`). | §5.3 |
| `borsai/post_d1.py` | D1 sonrası model `post_d1_hazard_v0`: D1 verisi, fit, walk-forward ve nihai fit önizlemesi. CLI. | §5.2 |
| `borsai/predict.py` | V1.5 ailesi ve basit kurallar için saf tahmin (yalnız stdlib). Bir test numpy ve scikit-learn'ün yüklenmediğini ayrı süreçte sınar. | §4.3.5 |
| `borsai/predict_break.py` | Kırılma akşamı tahmini, yastık kuralı ve ürün karşılaştırıcısı (`PRODUCT_BREAK_FLOOR`). | §5.3, §5.4 |
| `borsai/predict_fall.py` | Düşen arz modelleri `fall_d10_v0_*` için tahmin. | §4.8 |
| `borsai/predict_hazard.py` | Tavan serisi tahmini: hazard modelleri, `@INF` uçları ve Kaplan–Meier kuralları; S_k ve P_L çıktıları. | §4.4, §4.7 |
| `borsai/predict_market20.py` | `v1_5_market20_v0` tahmini; f6'yı hesaplamaz, hazır değeri alır. | §4.3.8 |
| `borsai/predict_path.py` | Tavan yolu modellerinin tahmini: limit yolu atomu ve karışım dağılımı. | §4.6 |
| `borsai/predict_pb.py` | `pb_v0` tahmini (talep toplama öncesi planlanan yapıdan). | §4.5 |
| `borsai/predict_post_d1.py` | `post_d1_hazard_v0` tahmini: dondurulmuş tavan modelinin öngörücüsüne D1 ofseti eklenir. | §5.2 |
| `borsai/preprocess.py` | Fold içi ön işleme: eski V1.3'ün 11 adımlık tarifinin bit düzeyinde portu. | §3.7 |
| `borsai/provenance.py` | sha256, kanonik JSON, git ve zaman damgası yardımcıları. | §6.3 |
| `borsai/push_proof.py` | Push kanıtı yazar: GitHub commit status API'sine durum gönderir, sunucunun `created_at`'ını dosyaya yazar. CLI. | §6.3.4 |
| `borsai/registry.py` | Sicil: payda (`ipos.csv`), girdi belgeleri, eski kayıt rolleri ve birincil kayıt seçimi; `inputs_pit_ok` denetimi. | §3.9, §6.11.3 |
| `borsai/report.py` | `docs/MODELS.md` üreticisi (Faz 1A bölümü); altın ledger'lardan okur, yeniden backtest koşmaz. CLI. | §6.5.5 |
| `borsai/report_faz1b.py` | `MODELS.md`'nin Faz 1B bölümü ve şartname beklentileri. | §6.9.3 |
| `borsai/report_faz4.py` | `MODELS.md`'nin Faz 4 (tavan yolu) bölümü. | §4.6.6 |
| `borsai/report_faz5.py` | `MODELS.md`'nin Faz 5 (D1 sonrası) bölümü. | §5.2.6 |
| `borsai/report_faz7.py` | `MODELS.md`'nin Faz 7 (tavan serisi v1) bölümü. | §4.7 |
| `borsai/report_faz7c.py` | `MODELS.md`'nin Faz 7C (düşen arz) bölümü. | §4.8.4 |
| `borsai/report_faz8.py` | `MODELS.md`'nin Faz 8 (kırılma akşamı) bölümü. | §5.3.9 |
| `borsai/rules.py` | Basit kurallar: eğitim hedeflerinden sabit tahmin (ortalama, medyan, oran, son-10). | §4.1.5 |
| `borsai/scoring.py` | Skorlama: sınıf, birincil kayıt, eşleşik metrikler, bootstrap aralıkları ve küçük-n dili. `scores/*.json` ve `docs/SCORES*.md`'yi üretir. CLI (`--oot`, `--break`). En büyük modüldür (4 764 satır). | §6.8, §6.10 |
| `borsai/specs.py` | Kayıtlı model şartnameleri ve backtest planları; `spec_sha256` buradan hesaplanır. | §3.8.4, §6.5.4 |
| `borsai/survival.py` | Tavan serisi için ortak tanımlar: kişi-dönem satırları ve S_k / P_L dönüşümleri. | §4.4.1, §4.4.2 |
| `borsai/tufe.py` | TÜİK TÜFE endeksini (2025=100) okur ve T − 2 ay kuralını uygular (f1r için). | §3.6.3 |

## data/

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `data/training_table.csv` | Eğitim tablosu v1: H99'un 99 arzı, 31 sütun. | §3.8.1 |
| `data/training_table_v2.csv` | Eğitim tablosu v2: 170 satır (H99 + eski kohortun açık kümesi), 39 sütun; kasa satırı yok. | §3.8.3 |
| `data/build_training_table.py` | v1 tablosunu `data/raw/` kanonik dosyalarından üreten betik. | §3.8.1 |
| `data/build_training_table_v2.py` | v2 tablosunu üreten betik. | §3.8.3 |
| `data/data_version.json` | v1 tablosunun kimliği: sha256, satır ve sütun sayıları, kaynak dosyaların hash'leri, sonuçların son seansı (2026-08-19). | §3.8.1, §3.12 |
| `data/data_version_v2.json` | v2 tablosunun kimliği; kohortlar, TÜFE ve eski kohort girdi ve sonuç kaynakları dahil. | §3.8.3, §3.12 |

### data/raw/

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_membership.csv` | H99 üyelik listesi. | §3.3.2 |
| `data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv` | H99'un işlem öncesi alanları (MASTER). | §3.3.2 |
| `data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_provenance.csv` | H99 kaynak kimlikleri (PROV). | §3.3.2 |
| `data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_feature_readiness.csv` | f1–f5 ham değerleri (READY). | §3.3.2 |
| `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv` | H99'un D1–D10 bülten alanları (SESSIONS). | §3.3.2 |
| `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv` | H99'un getiri hedefleri (TARGETS). | §3.3.2 |
| `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_field_provenance.csv` | Alan alan kaynak kayıtları (4,4 MB). | §3.3.2 |
| `data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv` | Takvim A: H99 dönemi Pay Piyasası seans takvimi. | §3.4.2 |
| `data/raw/PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv` | Talep toplama öncesi (PB) alanların nokta-zamanında kanıtı. | §3.3.2, §3.6.4 |
| `data/raw/v2_market20_official_pay_calendar_evidence_r4.csv` | Takvim B: market20 için resmî seans takvimi kanıtı. | §3.4.3 |
| `data/raw/pay_calendar_b_extension_20260820_20261231.csv` | Takvim B'nin 2026 sonuna kadar uzatması. | §3.4.3 |
| `data/raw/pay_calendar_c_20200101_20230921.csv` | Takvim C: eski kohort dönemi (2020–2023) seans takvimi. | §3.4.4 |
| `data/raw/pay_calendar_c_bulletin_evidence_20200101_20230921.csv` | Takvim C'nin bülten kanıtı. | §3.4.4 |
| `data/raw/official_bist_xu100_graphic_pinned_through_20260819.json` | 2026-08-19'a kadar pinli XU100 grafik verisi. | §3.2.5 |
| `data/raw/xu100/xu100_graphic_20260922.json` | 22 Eylül 2026'da alınan XU100 grafik verisi (uzatma). | §3.2.5, §3.6.2 |
| `data/raw/bist/MANIFEST.csv` | Canlı bülten zip'lerinin pin dosyası: 73 satır (40 THB, 33 THM); tarih, tür, URL, sha256, bayt, indirme ve yayın zamanı. | §3.2.1 |
| `data/raw/bist/MANIFEST_OOT.csv` | Eski kohort bültenlerinin pin dosyası: 1 168 satır (584 THB, 584 THM). Zip'lerin kendisi repo dışındaki karantinadadır. | §3.2.1, §6.12.4 |
| `data/raw/bist/thb/2026/` | Canlı THB zip'leri (40 dosya); bu kopyada yok, gerçek repoda var. | §3.2.1 |
| `data/raw/bist/thm/2026/` | Canlı THM zip'leri (33 dosya); bu kopyada yok, gerçek repoda var. | §3.2.1 |
| `data/raw/tuik/tufe_genel_2025_100.csv` | TÜFE genel endeksi (2025=100), ay başına bir satır ve yayın tarihi. | §3.2.4, §3.6.3 |
| `data/raw/tuik/tufe_bultenleri.csv` | TÜFE bültenlerinin yayın tarihleri. | §3.2.4 |
| `data/raw/tuik/build_tufe_csv.py` | TÜİK tablosundan `tufe_genel_2025_100.csv`'yi üreten betik. | §3.6.3 |
| `data/raw/tuik/tufe_degisim_oranlari_bulten_58290.source.json` | TÜİK tablosunun kaynak künyesi (URL, sha256, bayt, bülten). | §3.2.4 |
| `data/raw/tuik/tufe_degisim_oranlari_bulten_58290.xls` | TÜİK'in ham tablosu; bu kopyada yok, gerçek repoda var. | §3.2.4 |

### data/outcomes/ ve data/outcomes_oot/

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `data/outcomes/<T>.csv` | Yedi canlı arzın gün gün resmî sonucu (BKRGY, CITAS, INTET, KPEKS, NETGL, TKNKA, VEYAS): seans, kapanış, üst limit, referans, işlem sayısı, tavan etiketi, R_h, Y_h, bülten sha'ları ve durum. | §3.10.1 |
| `data/outcomes/COMPLETENESS.csv` | Tamlık denetimi: bültenlerde ilk kez görünen her kod ve sınıflaması (6 413 satır). | §3.10.3 |
| `data/outcomes_oot/` | Eski kohortun ayıklanmış sonuç dosyaları: 135 CSV, arz başına bir dosya. | §3.11 |
| `data/outcomes_oot/raw/` | Ayıklamanın ara çıktısı: 135 JSON (`borsai.oot_raw_rows/1`). | §3.11 |

## models/

Donmuş modellerin parametre dosyaları (`borsai.model/1`) ve üç dizin. Bir dosya bir kez yazılır; değişiklik yeni `model_id` ister.

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `models/INDEX.json` | Listeleme öncesi dizin: 27 giriş. Her girişte `model_id`, dosya, sha256, `spec_sha256`, `data_version_sha256`, eğitim kesimi ve n, `training_tickers_sha256`, `frozen_at` ve dayanağı. Uygulamaya gömülür. | §4.1.3, §6.11.1 |
| `models/INDEX_POST_D1.json` | D1 sonrası dizin: 1 giriş (`post_d1_hazard_v0`). Uygulamaya gömülür. | §5.2, §7.4 |
| `models/INDEX_POST_BREAK.json` | Kırılma akşamı dizini: 2 giriş (`break_floor_v0`, `@ZERO`). Gömülmez. | §5.3 |
| `models/.gitkeep` | Boş klasörü git'te tutmak için. | — |
| `models/base_always_ceiling.json` | Kural: her seans tavan. | §4.1.5 |
| `models/base_km_expanding.json` | Kural: genişleyen Kaplan–Meier tavan serisi eğrisi. | §4.1.5 |
| `models/base_km_last10.json` | Kural: son 10 arzın Kaplan–Meier eğrisi. | §4.1.5 |
| `models/base_last10_rate.json` | Kural: son 10 arzın yön oranı. | §4.1.5 |
| `models/base_rate.json` | Kural: eğitimdeki yön oranı (taban oranı). | §4.1.5 |
| `models/base_train_mean.json` | Kural: eğitim getirilerinin ortalaması. | §4.1.5 |
| `models/base_train_median.json` | Kural: eğitim getirilerinin medyanı. | §4.1.5 |
| `models/base_zero.json` | Kural: getiri her ufukta 0. | §4.1.5 |
| `models/v1_5_h99.json` | V1.5 getiri ve p_up modeli (H99 ile fit). | §4.3 |
| `models/v1_6_h99.json` | V1.6: genişletilmiş ızgaralı V1.5. | §4.3.7 |
| `models/v1_5_market20_v0.json` | V1.5 + f6 (market20). | §4.3.8 |
| `models/pb_v0.json` | Talep toplama öncesi getiri ve p_up modeli. | §4.5.3 |
| `models/ceiling_hazard_v0.json` | Tavan serisi (hazard) modeli. | §4.4 |
| `models/ceiling_hazard_v0@INF.json` | Aynı modelin özelliksiz ucu (λ = ∞). | §4.4.9 |
| `models/pb_ceiling_v0.json` | Talep toplama öncesi tavan serisi modeli. | §4.5.4 |
| `models/pb_ceiling_v0@INF.json` | PB tavan modelinin özelliksiz ucu. | §4.5.4 |
| `models/ceiling_path_v0.json` | Tavan yolu modeli. | §4.6 |
| `models/ceiling_path_v0@INF.json` | Tavan yolu modelinin özelliksiz ucu. | §4.6 |
| `models/pb_ceiling_path_v0.json` | Talep toplama öncesi tavan yolu modeli. | §4.6 |
| `models/ceiling_hazard_v1_clip.json` | Tavan serisi v1, kırpılmış büyüklük. | §4.7.2 |
| `models/ceiling_hazard_v1_real.json` | Tavan serisi v1, reel büyüklük (f1r). | §4.7.2 |
| `models/ceiling_hazard_v1_pooled.json` | Tavan serisi v1, H99 + açık küme havuzu. | §4.7.2 |
| `models/ceiling_hazard_v1_pooled@INF.json` | Havuz modelinin özelliksiz ucu (kural satırı). | §4.7.2 |
| `models/fall_d10_v0_h99.json` | Düşen arz modeli, yalnız H99. | §4.8.3 |
| `models/fall_d10_v0_pooled.json` | Düşen arz modeli, havuz. | §4.8.3 |
| `models/fall_d10_v0_addsale.json` | Düşen arz modeli, ek satış bayrağıyla. | §4.8.3 |
| `models/fall_d10_v0_pooled@ZERO.json` | Düşen arz kural satırı (eğitim oranı). | §4.8.3 |
| `models/post_d1_hazard_v0.json` | D1 sonrası güncelleme modeli. | §5.2.4 |
| `models/break_floor_v0.json` | Kırılma akşamı modeli (F1 ve F2 başlıkları). | §5.3.5 |
| `models/break_floor_v0@ZERO.json` | Kırılma akşamı kural satırı. | §5.3.6 |

Toplam 30 model dosyası: dizinlerdeki 27 + 1 + 2 girişle birebir.

## registry/

Tahmin sicili: payda, girdiler, kaynak belgeler, kayıtlar ve kanıtlar. Kayıt dosyaları bir kez yazılır (`xb` kipi); düzeltme yeni dosya ya da iptal kaydıyla yapılır.

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `registry/ipos.csv` | Canlı payda: 26 satır (7 `FROZEN` + 19 kapsam dışı). Sütunlar: `ticker`, `company`, `first_trading_date`, `listing_source_id`, `status`, `skip_reason`, `note`, `added_at`. Yalnız sona ekleme yapılır. | §3.9.3 |
| `registry/legacy_roles.json` | Eski repodan gelen kayıtların rolleri (`borsai.legacy_roles/1`): hangisinin birincil sayılacağı. | §6.11.3 |
| `registry/inputs/<T>.json` | Yedi canlı arzın girdi belgesi (`borsai.inputs/1`): 20 alan, her alanın kaynağı ve toplanma zamanı. | §3.9.1 |
| `registry/source_docs/<T>/MANIFEST.json` | Yedi arzın kaynak belge manifesti (`borsai.source_docs/1`): belge kimliği, türü, sha256 ve yayın zamanı. PDF'ler bu kopyada yok, gerçek repoda var. | §3.9.2 |
| `registry/source_docs/_ENUMERATION/ENUMERATION.json` | Paydanın tamlık taraması (`borsai.ipo_enumeration/1`): KAP ve SPK sorguları, ertelenen arzlar, sonuç. | §3.2.2, §3.9.2 |
| `registry/source_docs/_ENUMERATION/kap_byCriteria_subject_paylarin_islem_gormeye_baslamasi_20260801_20260922.json` | Taramanın KAP'tan gelen ham yanıtı. | §3.2.2 |
| `registry/records/<T>/<zaman>_<kısa-sha>.json` | Listeleme öncesi tahmin kayıtları (`borsai.record/1`): 7 arz, birer kayıt, her biri 16 modelin çıktısı. Alanlar: girdiler, `model_inputs`, `models[]` (`model_id`, dosya, `params_sha256`, `spec_sha256`, çıktı ya da ret), `models_index`, kayıt zamanı ve dayanağı, özet. Sınıf kayda yazılmaz. | §6.11.2 |
| `registry/post_break/<T>/machine_<zaman>_<kısa-sha>.json` | Kırılma akşamı makine kayıtları (`borsai.post_break_machine_record/1`): 7 dosya. Kırılma günü, seri, özellikler, karşılaştırıcılar, yapısal sıfır ve `exposure_class` taşır. | §5.5.4 |
| `registry/push_proofs/<sha>.json` | Push kanıtları (`borsai.push_proof/1`): 31 dosya, adı kanıtlanan commit'in tam sha'sı. Alanlar: `proven_commit_sha`, `created_at` (GitHub sunucu saati), `context`, `github_status_id`, `method`. | §6.3.4 |
| `registry/legacy_frozen/` | Eski repodaki "true live" dondurmalarının kopyası: 7 klasör (BKRGY ×3, INTET ×2, NETGL, TKNKA) ve `true_live_v1_5_registry.csv`, toplam 29 dosya. NETGL klasöründe eski push kanıtı (`push_proof.json`) vardır. | §2.2.2, §6.11.3 |
| `registry/post_d1/` | D1 sonrası kayıtların klasörü; henüz kayıt yazılmadığı için bu kopyada yok. | §5.2.8 |

### registry/oot/

Eski kohortun (135 arz) sicili. Dosya adları arz kodu taşıdığı için yalnız sayılar verilir.

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `registry/oot/cohort_pre_h99.csv` | Kohort dosyası: 136 satır (135 üye + 1 kapsam dışı). Her satırda tarih, satış yöntemi, pazar, yıl, durum, kasa etiketi ve rejim etiketleri. Kasa üyelerinin kodları bu kitapta hiçbir yere yazılmaz. | §6.12.2, §3.11 |
| `registry/oot/VAULT_OPEN.json` | Kasanın 29 Eylül 2026'da açıldığını gösteren işaret dosyası; kasa kodu içermez. | §6.12.6 |
| `registry/oot/inputs/` | 135 girdi belgesi (`borsai.inputs/1`). | §6.12.2 |
| `registry/oot/records/` | 135 klasör, her birinde 2 kayıt; toplam 270 dosya (`borsai.oot_record/1`). | §6.12.5 |
| `registry/oot/post_d1/` | 135 klasör, birer D1 sonrası makine kaydı (`borsai.oot_post_d1_record/1`). | §6.12.5 |
| `registry/oot/d1_rows/` | 135 dosya: her arzın D1 satırı (`borsai.oot_d1_row/1`). | §6.12.5 |
| `registry/oot/candidate_features/` | 135 dosya: Faz 6'da toplanan aday alanlar (`borsai.oot_candidate_features/1`); model girdisi değildir. | §2.3.8 |
| `registry/oot/candidate_features_faz7/` | 135 dosya + `SHA256SUMS`: Faz 7'de izahnamelerden toplanan yedi alan. | §2.3.9 |
| `registry/oot/source_docs/` | 135 klasör, birer `MANIFEST.json`; 523 PDF bu kopyada yok, gerçek repoda var. | §6.12.2 |
| `registry/oot/source_docs_faz7/` | 135 klasör, birer `MANIFEST.json`. Manifestler 1 284 izahname ve ek belgesini URL ve sha256'sıyla listeler; PDF'ler (3,19 GB) repoya hiç alınmadı. | §2.3.9 |

## scores/

`borsai.scoring`'in çıktıları. Uygulama bunları okur, hiçbir sayıyı yeniden hesaplamaz.

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `scores/scores.json` | Canlı sicil ve backtest skorları (`borsai.scores/1`, 1,3 MB): model başına canlı satırlar, koşullu satırlar, retro bilgi listesi ve backtest hücreleri. | §6.10.4 |
| `scores/scores_post_d1.json` | D1 sonrası sicili (`borsai.scores_post_d1/1`). | §5.2.8 |
| `scores/scores_break.json` | Kırılma akşamı sicili (`borsai.scores_break/1`, ölçek `live_break`). | §5.5.3 |
| `scores/scores_oot.json` | Zaman-dışı terazi (`borsai.scores_oot/1`, 41 MB): açık küme, kasa ve hepsi blokları ile D1 sonrası blokları. Uygulamaya süzülmüş kopyası gömülür. | §6.12.7, §7.3 |

## experiments/

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `experiments/README.md` | Deney günlüğünün biçimi ve kuralları. | §6.13.2 |
| `experiments/log.jsonl` | Deney günlüğü: 2 146 satır, her backtest, duyarlılık ve keşif koşusu için bir JSON satırı. Silinmez, düzeltilmez. | §6.13 |

## legacy/

Eski repodan (Halka_Arz_Modeli) değiştirilmeden alınan 34 dosya. Port'un bit düzeyinde aynı sonucu verdiğini sınayan testler bunları içe aktarır; bekçi testi bu klasörün değişmediğini denetler.

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `legacy/artifacts/governance/BORSAI_PRETRADE_EXTENSION_COLLECTION_SPEC_20260912_R6/` | Talep toplama öncesi alanların toplama şartnamesi (`.md` ve `.json`). | §2.2.1, §4.5 |
| `legacy/config/model_v1_5_spec.json` | V1.5'in eski repodaki şartnamesi. | §4.3.1 |
| `legacy/scripts/collect_historical99_bist_raw_v1.py` | H99 bültenlerini toplayan eski betik; indirme adresi kaynağı. | §3.2.1 |
| `legacy/scripts/modeling/` | V1.5 çekirdeği (`candidate_models.py`, `preprocessing.py`, `logistic_policy.py`, `fold_engine.py`, `metrics.py`, `baselines.py`, `feature_assembly.py`, `target_extraction.py`, `common.py`), H99 benchmark koşucusu, canlı dondurma betikleri ve market20 onarımı. | §2.2.1, §4.3 |
| `legacy/scripts/modeling/prebookbuild_v1_r6/` | Talep toplama öncesi PB çekirdeği (`pb_core4.py`, `chronology.py`, `identity_gate.py`, `targets.py`). | §4.5 |
| `legacy/scripts/validation/validate_batch.py` | Eski toplu doğrulama betiği. | §2.2.1 |
| `legacy/src/halka_arz_audit/` | Eski denetim paketi: değerlendirme, donmuş tahminler, bekçiler, envanter, canlı tahmin ve dondurma, OOXML okuyucu. | §2.2.1 |

## tests/

Python testleri: 56 `test_*.py` dosyası ve 9 yardımcı. Son kabulde 952 test geçti. Ayrıntılı tablo §6.15.6'dadır.

### Yardımcılar

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `tests/conftest.py` | Ortak fixture'lar; resmi backtest koşularının (`run_all`) paylaşımı. | §6.15.1 |
| `tests/refcompare.py` | Windows referans ledger'larıyla karşılaştırma yardımcıları. | §6.15.6 |
| `tests/faz1b_support.py` | Faz 1B testlerinin ortak yardımcıları. | §6.15.6 |
| `tests/faz5_support.py` | Faz 5 yardımcıları ve refactor öncesi anlık görüntü. | §6.15.6 |
| `tests/faz5_live_support.py` | Canlı POST_D1 akışının geçici klonda provası. | §6.15.6 |
| `tests/faz6_support.py` | Faz 6 sentetik girdi, kohort, geçici git deposu ve sentetik bülten zip'leri. | §6.15.6 |
| `tests/faz7_support.py` | Faz 7 sentetik veri kümesi ve varyant sayacı istisnası. | §6.15.6 |
| `tests/faz7c_support.py` | Faz 7C sentetik düşen arz verisi ve varyant sayacı istisnası. | §6.15.6 |
| `tests/faz8_support.py` | Faz 8 için var olan testlerin sınırlı istisnası. | §6.15.6 |

### Test dosyaları

| Yol | Ne sınar | Bölüm |
|---|---|---|
| `tests/test_acceptance_backtest.py` | Faz 1A kabul 1–4: port, H99 benchmark'ını 351 fold'da yeniden üretir. | §4.3.6 |
| `tests/test_training_table.py` | Eğitim tablosunun veri kabul testi; ham kaynaklardan bağımsız sayım. | §3.8.1 |
| `tests/test_features.py` | f1–f5 tanımı ve f3 filtre modu. | §3.6.1 |
| `tests/test_port_vs_legacy.py` | Port ile eski kodun aynı makinede bit eşitliği. | §3.7 |
| `tests/test_predict.py` | Tahmin paritesi (JSON ↔ sklearn), `training_tickers_sha256` ve "predict yalnız stdlib". | §4.3.5 |
| `tests/test_models.py` | Donmuş modeller ve `models/INDEX.json`. | §6.11.1 |
| `tests/test_metrics.py` | Eşleşik fark aralığı ve metrik yardımcıları. | §6.7 |
| `tests/test_experiment_log.py` | Her backtest koşusunun günlüğe kendiliğinden yazılması. | §6.13 |
| `tests/test_guardrails.py` | `legacy/` değişmedi; 2026-08-19 sonrası veri yok. | §6.15.4 |
| `tests/test_report.py` | `docs/MODELS.md` ve şartname beklentilerinin aynen alıntılanması. | §6.9.3 |
| `tests/test_ceiling.py` | `ceiling_hazard_v0` ve `pb_ceiling_v0` kabul testleri. | §4.4 |
| `tests/test_pb.py` | `pb_v0` kabul testleri. | §4.5 |
| `tests/test_v1_6.py` | `v1_6_h99` kabul testleri. | §4.3.7 |
| `tests/test_market20.py` | `v1_5_market20_v0` ve f6 kabul testleri. | §4.3.8 |
| `tests/test_xu100_update.py` | XU100 ve takvim uzatmasının eski kayıtlarla örtüşmesi. | §3.2.5 |
| `tests/test_faz1b_backtest.py` | Faz 1B koşularının altın ledger'larla bayt eşitliği. | §6.5.5 |
| `tests/test_faz1b_guardrails.py` | Faz 1A dosyaları ve şartnameler değişmedi. | §6.15.4 |
| `tests/test_faz1b_models.py` | Faz 1B donmuş modelleri: INDEX, yapı, yeniden üretim. | §6.11.1 |
| `tests/test_outcomes.py` | Sonuç ayıklama: yarım gün, durdurma, tavan etiketi, indirici ve manifest. | §3.10 |
| `tests/test_outcome_guard.py` | Sıra bekçisi: sonuç ancak kayıttan sonra repoya girer. | §6.11.6 |
| `tests/test_registry_ipos.py` | Payda dosyası: şema, bilinen 7 arz, yalnız sona ekleme, tamlık. | §3.9.3 |
| `tests/test_registry_inputs.py` | Girdi belgeleri, `inputs_pit_ok`, kaynak belgeler ve eski roller. | §3.9.1 |
| `tests/test_freeze_records.py` | Kayıt yazıcı: bütün modeller kayıtta, ret hücreleri, üzerine yazma reddi, iptal. | §6.11.2 |
| `tests/test_push_proof.py` | Push kanıtı biçimi, yeniden yazmama, torun commit kapsaması; ağa çıkmaz. | §6.3.4 |
| `tests/test_scoring.py` | Sınıflama, birincil kayıt, payda, bootstrap, hüküm dili ve RPS. | §6.8, §6.10 |
| `tests/test_scoring_conditional.py` | Koşullu canlı skorlama. | §4.6.5 |
| `tests/test_faz4_ceiling_path.py` | Tavan yolu kabul testleri ve "beklentiden çok iyi" dondurma kararı. | §4.6.6 |
| `tests/test_faz5_post_d1.py` | `post_d1_hazard_v0` kabul testleri. | §5.2 |
| `tests/test_faz5_golden.py` | Faz 5 resmi koşusu ve altın ledger. | §5.2.6 |
| `tests/test_faz5_frozen.py` | Faz 5 dondurması ve `INDEX_POST_D1.json`. | §5.2.4 |
| `tests/test_faz5_live.py` | Canlı POST_D1 akışı, geçici git depolarında. | §5.2.7 |
| `tests/test_faz6_oot.py` | Eski kohort altyapısı: Takvim C, kohort, kasa çekilişi, rejim etiketleri, `freeze --oot`. | §6.12 |
| `tests/test_faz6_s6.py` | `scoring --oot` ve `SCORES_OOT.md`. | §6.12.5 |
| `tests/test_faz6_s6_fix.py` | Eski kohort D1 sonrası bloğu ve kasa hijyeni. | §6.12.5 |
| `tests/test_faz7_table_v2.py` | Eğitim tablosu v2 ve tahsis rejimi; kasa dosyaları okunmaz. | §3.8.3, §3.6.5 |
| `tests/test_faz7_tufe.py` | TÜFE dosyası ve T − 2 kuralı. | §3.6.3 |
| `tests/test_faz7_model.py` | Faz 7 model kodu (sentetik veriyle). | §4.7 |
| `tests/test_faz7_backtest.py` | Faz 7 backtest altyapısı. | §4.7.4 |
| `tests/test_faz7_golden.py` | Faz 7 resmi koşuları ve altın ledger'lar. | §4.7 |
| `tests/test_faz7_freeze.py` | Faz 7 dondurma yolu. | §4.7.3 |
| `tests/test_faz7_frozen.py` | Faz 7 dondurması `models/`'de. | §4.7.3 |
| `tests/test_faz7_oot.py` | Eski kohort ek kayıtları, kohort kapısı ve kasa skorlama kodu. | §6.12.5 |
| `tests/test_faz7_prospectus.py` | İzahname alanları bekçisi. | §2.3.9 |
| `tests/test_faz7_vault.py` | Kasanın tek seferlik açılışı ve iki kipli kasa bekçisi. | §6.12.6 |
| `tests/test_faz7c_model.py` | Faz 7C model kodu. | §4.8 |
| `tests/test_faz7c_backtest.py` | Faz 7C backtest altyapısı ve kurallar. | §4.8 |
| `tests/test_faz7c_golden.py` | Faz 7C resmi koşuları ve keşif satırları. | §4.8.4 |
| `tests/test_faz7c_freeze.py` | Faz 7C dondurma yolu. | §4.8.3 |
| `tests/test_faz7c_frozen.py` | Faz 7C dondurması `models/`'de. | §4.8.3 |
| `tests/test_faz8_break.py` | Kırılma tablosu, özellikler, sızıntı, plan, yastık kuralı ve hijyen. | §5.3, §5.4 |
| `tests/test_faz8_model.py` | Kırılma modeli fit yolu, ürün karşılaştırıcısı ve stdlib paritesi. | §5.3.5 |
| `tests/test_faz8_golden.py` | Faz 8 resmi koşusu. | §5.3.9 |
| `tests/test_faz8_freeze.py` | Faz 8 dondurma yolu. | §5.3 |
| `tests/test_faz8_frozen.py` | Faz 8 dondurması ve `INDEX_POST_BREAK.json`. | §5.3 |
| `tests/test_faz8_live.py` | `POST_BREAK` aşaması: makine sıralı sınıf, geçici git depolarında. | §5.5 |
| `tests/test_faz8_support.py` | Adı `test_` ile başlasa da test içermez: sentetik kırılma tabloları. | §6.15.6 |

### tests/reference/

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `tests/reference/macos_golden/` | Faz 1A altın ledger'ları: V1.5 ve 6 basit kural, `MANIFEST.json`, `SHA256SUMS` (9 dosya). | §6.5.5 |
| `tests/reference/macos_golden_faz1b/` | Faz 1B altın ledger'ları (21 dosya). | §6.5.5 |
| `tests/reference/macos_golden_faz4/` | Faz 4 tavan yolu ledger'ları (5 dosya). | §4.6.6 |
| `tests/reference/macos_golden_faz5/` | Faz 5 ledger'ı ve nihai fit önizlemesi (4 dosya). | §5.2.6 |
| `tests/reference/macos_golden_faz7/` | Faz 7 ledger'ları ve fit önizlemeleri (12 dosya). | §4.7 |
| `tests/reference/macos_golden_faz7c/` | Faz 7C ledger'ları ve fit önizlemeleri (10 dosya). | §4.8 |
| `tests/reference/v1_5_benchmark/` | Eski repodaki Windows H99 V1.5 benchmark'ı (3 CSV). | §4.3.6 |
| `tests/reference/baseline_benchmark/` | Eski repodaki basit kural benchmark'ı (2 CSV). | §4.3.6 |
| `tests/reference/v1_5_macos_runtime_replay_20260911/` | V1.5'in macOS'ta yeniden koşusu (5 dosya). | §2.2.1 |
| `tests/reference/faz5_pre_refactor/predict_hazard_snapshot.json` | Faz 5 refactor'undan önceki tahmin anlık görüntüsü. | §5.2 |
| `tests/reference/A_v1_5_probe_cikti.json` | V1.5 prob çıktısı (referans). | — |
| `tests/reference/q3a_macos_yeniden_kosu_cikti.json` | macOS yeniden koşu çıktısı (referans). | — |
| `tests/reference/netgl_input_contract.json` | NETGL'in eski girdi sözleşmesi. | §2.2.2 |

## docs/

### Üst düzey belgeler

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `docs/DATA.md` | Eğitim tablosunun sütun sütun tanımı ve kaynakları. | §3.3.2, §3.8.1 |
| `docs/DATA_NOTES.md` | Eski repodaki veri anlamı hükümlerinin özeti (f2 formülü gibi tuzaklar). | §3.3.3 |
| `docs/ENV.md` | Python ve uygulama ortamı, sürümler ve pinler. | §2.8, §3.12 |
| `docs/PROVENANCE.md` | Eski repodan kopyalanan her dosyanın kökeni ve referans ledger'lar. | §2.2, §3.2.2 |
| `docs/MODELS.md` | Modeller ve backtest sonuçları (198 KB); `borsai.report*` ile üretilir, elle düzenlenmez. | §4.9, §6.5.5 |
| `docs/SCORES.md` | Canlı sicil ve backtest skorlarının okunur hâli; `scores.json`'dan üretilir. | §6.10.4 |
| `docs/SCORES_BREAK.md` | Kırılma akşamı sicili. | §5.5.3 |
| `docs/SCORES_OOT.md` | Zaman-dışı terazinin okunur hâli. | §6.12.7 |
| `docs/SPEC_DEVIATIONS.md` | Sapmalar defteri: şartnameden her sapma ve yorum, A–O bölümleri (278 515 bayt). | §6.14 |
| `docs/prompts/` | 79 görev dosyası; katalog §2.5. | §2.4.2, §2.5 |

### Şartnameler

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `docs/specs/SPEC_SCORING.md` | Skorlama şartnamesi: sonuç tanımları, sınıf, birincil kayıt, metrikler, kabul testleri. | §6.4, §6.10 |
| `docs/specs/SPEC_CEILING_V0.md` | `ceiling_hazard_v0` şartnamesi. | §4.4 |
| `docs/specs/SPEC_PB_V0.md` | PB modelleri şartnamesi. | §4.5 |
| `docs/specs/SPEC_MARKET20_V0.md` | market20 şartnamesi. | §4.3.8 |
| `docs/specs/SPEC_V1_6.md` | V1.6 şartnamesi. | §4.3.7 |
| `docs/specs/ekler/` | Fable'ın ölçüm betikleri ve çıktıları (m1 hazard, m2 PB ve market fold'ları, m3 market penceresi). | §4.4, §4.5 |
| `docs/specs_faz4/SPEC_CEILING_PATH_V0.md` | Tavan yolu şartnamesi; ekte Borsa İstanbul kural metni ve m4 ölçümü. | §4.6 |
| `docs/specs_faz5/SPEC_POST_D1_V0.md` | D1 sonrası model şartnamesi; ekte kural metni ve D1 profili. | §5.2 |
| `docs/specs_faz6/SPEC_OOT_PRE_H99_V0.md` | Eski kohort ve üçüncü terazi şartnamesi. | §6.12 |
| `docs/specs_faz6/FEASIBILITY.md` | Eski kohortun yapılabilirlik incelemesi. | §2.3.8 |
| `docs/specs_faz6/KARARLAR.md` | Faz 6 kararları (D1–D8). | §2.3.8 |
| `docs/specs_faz6/ekler/` | Evren listesi, KAP sorgu günlükleri, SPK bülten dizini, kural araştırması, Takvim C notu, arşiv taramaları, örnek denetim. | §2.3.8, §3.4.4 |
| `docs/specs_faz7/SPEC_HAZARD_V1.md` | Tavan serisi v1 şartnamesi. | §4.7 |
| `docs/specs_faz7/KARARLAR.md` | Faz 7 kararları (ör. K3: TÜFE'nin T − 2 ay kuralı). | §4.7, §3.6.3 |
| `docs/specs_faz7/ekler/` | Kaynak kontrolü ve tanı betiği. | §4.7 |
| `docs/specs_faz7_c/SPEC_C_V0.md` | Düşen arz modeli şartnamesi. | §4.8 |
| `docs/specs_faz7_c/KARARLAR_C.md` | Faz 7C kararları. | §4.8 |
| `docs/specs_faz7_c/KESIF.md` | Düşen arz keşfi: ne denendi, ne bulundu. | §4.8.2 |
| `docs/specs_faz7_c/ekler/` | Keşif betiği ve çıktısı, denenenler listesi (`denenenler.csv`), kasa sayımı. | §4.8.2, §6.13.2 |
| `docs/specs_faz8/SPEC_BREAK_V0.md` | Kırılma akşamı şartnamesi. | §5.3 |
| `docs/specs_faz8/KARARLAR.md` | Faz 8 kararları (C1–C5). | §5.3 |
| `docs/specs_faz8/ekler/` | Kırılma profili betiği ve çıktısı. | §5.3.1 |

### Uygulama ve tasarım belgeleri

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `docs/app/SPEC_APP.md` | Masaüstü uygulamasının ana şartnamesi (EK 1 dahil). | §7, §8 |
| `docs/app/SPEC_APP_EK2.md` | Ek 2: tavan yolu modelleri uygulamada. | §7.8.6, §8.8 |
| `docs/app/SPEC_APP_EK3.md` | Ek 3: v1, D1 sonrası, zaman-dışı panel ve düşüş kartı. | §7.7, §7.10 |
| `docs/app/UI_FIX_RAPOR.md`, `docs/app/ui_fix_test_runs.txt` | Sunum öncesi arayüz düzeltmelerinin raporu ve test koşuları. | §2.3.14, §7.12 |
| `docs/app/UI_V2_HARITA.md` | Sade görünüm tasarımının uygulamaya haritası. | §8.24 |
| `docs/app/UI_V2_RAPOR.md`, `docs/app/ui_v2_test_runs.txt` | Sade görünüm görevinin raporu ve test koşuları. | §2.3.14, §8.25 |
| `docs/app/p1/`, `docs/app/p2/`, `docs/app/p34/` | EK 3 parçalarının (P1, P2, P3–P4) raporları ve test koşuları. | §2.3.12, §7.10 |
| `docs/app/ekler/` | Sentetik `scores` dosyaları (n = 7, 12, 35). | §8.25 |
| `docs/design/ui_v2/README.md` | Onaylı sade tasarımın açıklaması. | §8.24 |
| `docs/design/ui_v2/boards/` | 12 pano (`Arz`, `Ayarlar`, `D1Sonrasi`, `Dogruluk`, `Dondur`, `Giris`, `Kayitlarim`, `Main`, `Palet`, `Sicil`, `Sonuc`, `Stil`, `.dc.html`) ve `canvas.json`. | §8.24 |
| `docs/design/ui_v2/png/` | Panoların durağan görüntüleri; bu kopyada yok, gerçek repoda var. | §8.24 |

### Fable denetimleri

Her denetim klasöründe bir `AUDIT.md` ve `ekler/` vardır. Ekler bağımsız yeniden üretim betikleri ve ledger'ları, mutasyon betikleri ve çıktıları, koruma önce/sonra kayıtları, sıra kanıtları ve test çıktılarıdır.

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `docs/fable_conformity_20260922/` | Faz 1 uygunluk denetimi: bağımsız yeniden üretim ve tahmin paritesi. | §2.3.3, §6.16 |
| `docs/fable_faz4_audit/` | Tavan yolu modellerinin denetimi ve duyarlılık koşuları. | §2.3.6, §4.6.6 |
| `docs/fable_faz5_audit/` | `post_d1_hazard_v0` denetimi (FREEZE_OK). | §5.6.1 |
| `docs/fable_faz6_audit/` | Eski kohort altyapısının denetimi; kasa ve rejim için bağımsız betikler. | §2.3.8, §6.16 |
| `docs/fable_faz6_s6/` | Zaman-dışı skorlamanın denetimi (`BAGIMSIZ.json`, `recompute.py`, kaynak denetimi). | §6.16 |
| `docs/fable_faz7_audit/` | Tavan serisi v1 denetimi. | §2.3.9, §6.16 |
| `docs/fable_faz7_vault/` | Kasa açılışının bağımsız karşılaştırması (`karsilastir.py`). | §2.3.11, §6.16 |
| `docs/fable_faz7c_audit/` | Düşen arz modeli denetimi. | §2.3.10, §6.16 |
| `docs/fable_faz8_audit/` | Kırılma modeli denetimi (REPRO_OK), sızıntı ve hijyen betikleri. | §5.6.2 |
| `docs/fable_app_audit/` | Uygulama denetimi ve kapanışı (`AUDIT.md`, `KAPANIS.md`), parite örneklemi ve mutasyonlar. | §2.4.6, §2.6.7 |

### Faz raporları

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `docs/faz5/` | Faz 5 raporları: uygulama, dondurma, canlı akış, tanım eşlemeleri ve `POST_D1_AKISI.md`; ekte NETGL provası. | §5.2.7 |
| `docs/faz6/` | Faz 6 raporları: altyapı (`INFRA_RAPOR.md`), S2, S3–S5, S6 ve düzeltmesi, tanım eşlemesi; ekte bağımsız betikler ve mutasyonlar. | §2.3.8 |
| `docs/faz6/dogrulama/` | Eski kohort girdilerinin doğrulama paketi: `REPORT.md`, `EXPOSURE.md`, kapsama ve sha tabloları, doğrulama günlüğü. | §2.3.8 |
| `docs/faz6/dogrulama/_tools/` | Doğrulamanın betikleri (`scripts/`), günlükleri (`logs/`) ve arz başına karar dosyaları (`decisions/`, 135 dosya). | §2.3.8 |
| `docs/faz7/` | Faz 7 uygulama ve dondurma raporları; ekte beklenen sayıların ölçümü. | §2.3.9 |
| `docs/faz7/prospectus/` | İzahname alanlarının toplanma paketi (40 dosya): `README.md`, `REPORT.md`, `EXPOSURE.md`, betikler ve günlükler. | §2.3.9 |
| `docs/faz7_oot/` | Eski kohort ek kayıtlarının raporu. | §2.3.11, §6.12.7 |
| `docs/faz7_vault/` | Kasa açılışı ve kasa skorlarının raporları (`RAPOR.md`, `SKOR_RAPOR.md`). | §6.12.6, §6.12.7 |
| `docs/faz7c/` | Faz 7C uygulama ve dondurma raporları. | §2.3.10 |
| `docs/faz8/` | Faz 8 raporları: uygulama, dondurma, canlı, `POST_BREAK_AKISI.md` ve bant doğrulaması (`BANT_DOGRULAMA.md`). | §5.3, §5.5 |
| `docs/faz8/backtest/` | Kırılma modelinin resmi koşusu: fold ledger'ı, üç duyarlılık ledger'ı, iki nihai fit önizlemesi, `MANIFEST.json`, `SHA256SUMS`. | §5.3.9 |
| `docs/infra/TEST_SPEED_RAPOR.md` | Test hızlandırma raporu (pytest-xdist). | §2.3.12, §6.15.1 |
| `docs/live/NETGL_D10_RAPOR.md` | NETGL'in D10'a kadar canlı seyri. | §2.3.12, §5.3.12 |
| `docs/arastirma/TR_HALKA_ARZ_PIYASASI_20261001.md` | Türkiye halka arz piyasası araştırması (rejim ve fon krizi bağlamı). | §2.6.9 |

## app/

Masaüstü uygulaması: Tauri 2, Rust arka uç ve çerçevesiz TypeScript ön uç. Yalnız macOS arm64; ağ erişimi yok.

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `app/README.md` | Uygulamanın kurulumu, mimarisi ve komutları. | §7.2, §8.1 |
| `app/package.json`, `app/package-lock.json` | npm bağımlılıkları (`@tauri-apps/api`, `plugin-dialog`; geliştirmede `@fontsource` ×3, Tauri CLI, jsdom, TypeScript, Vite, vitest) ve betikler (`dev`, `build`, `test`). | §8.1 |
| `app/index.html` | Ön ucun tek HTML sayfası. | §8.1 |
| `app/vite.config.ts` | Vite ayarı; ekran görüntüsü koşusunda dosya seçiciyi taklitle değiştirir. | §8.25 |
| `app/tsconfig.json` | TypeScript derleyici ayarı. | — |
| `app/.gitignore` | `node_modules/`, `src-tauri/target/` ve `dist/` git'e girmez. | — |
| `app/dist/` | Vite derleme çıktısı; git'e girmez. Kopyada `index.html`, bir JS ve bir CSS dosyası var; CSS'in andığı 18 woff2 yazı tipi dosyası bu kopyada yok. | — |

### app/src/ (ön uç)

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `app/src/main.ts` | Kabuk: görünüme göre yönlendirir (Sade varsayılan, Ayrıntılı eski arayüz). | §8.2 |
| `app/src/state.ts` | Ayrıntılı görünümün bellek durumu (`store`). | §8.3 |
| `app/src/api.ts` | Rust komutlarının tipli sarmalayıcıları. | §8.4 |
| `app/src/types.ts` | Rust komut sözleşmelerinin TypeScript tipleri. | §8.4 |
| `app/src/dom.ts` | Küçük DOM yardımcıları; metin HTML'e `esc` ile girer. | §8.4 |
| `app/src/vite-env.d.ts` | Vite tip bildirimi. | — |
| `app/src/styles.css` | Ayrıntılı görünümün stilleri. | §8.22, §8.23 |
| `app/src/i18n/tr.ts` | Bütün arayüz metinleri (2 106 satır); yasak sözcükler burada geçmez. | §8.9 |
| `app/src/render/format.ts` | Sayı biçimlendirme; hesap yapmaz. | §8.7 |
| `app/src/render/svg.ts` | Elle yazılmış SVG grafikler; aritmetiği yalnız piksel koordinatıdır. | §8.8 |
| `app/src/render/shell.ts` | Mod bandı (`bandFor`); sade mod göstergesi de buradan beslenir. | §8.11, §8.22 |
| `app/src/render/codes.ts` | Ret ve uyarı kodlarının Türkçe metne çevrilmesi. | §8.9 |
| `app/src/render/colors.ts` | Model başına sabit renk. | §8.22 |
| `app/src/render/card.ts` | Model kartı; sonuç ekranı ve doğruluk paneli aynı fonksiyonu kullanır. | §8.22 |
| `app/src/render/accuracy.ts`, `accuracy_oot.ts` | Doğruluk paneli ve zaman-dışı panel (saf render). | §8.22 |
| `app/src/render/ceiling.ts`, `summary.ts` | Koşullu tavan güncellemesi ve "kaç gün tavan?" özet kartı. | §8.22 |
| `app/src/render/inputs.ts`, `results.ts` | Girdi formu ve sonuç ekranı. | §8.22 |
| `app/src/render/freeze.ts`, `post_d1.ts`, `registry.ts` | Dondur sihirbazı, D1 sonrası bloğu ve sihirbazı, sicil ve arz sayfası. | §8.22, §7.9.4, §7.10 |
| `app/src/screens/` | Ayrıntılı görünümün ekranları: `about`, `accuracy`, `ctx`, `inputs`, `registry`, `results`, `scenarios`, `settings`. | §8.22 |
| `app/src/sade/app.ts` | Sade görünümün kabuğu: üst bar, ekran, alt bilgi. | §8.2, §8.11 |
| `app/src/sade/state.ts` | Sade görünümün bellek durumu. | §8.3 |
| `app/src/sade/api.ts`, `types.ts` | Sade görünümün yeni salt okuma komutları ve çıktı tipleri. | §8.4 |
| `app/src/sade/ctx.ts` | Sade ekranların kabuğa erişimi. | §8.2 |
| `app/src/sade/fonts.ts` | IBM Plex yazı tiplerinin yerel paketlerden yüklenmesi; ağ yok. | §8.23 |
| `app/src/sade/sade.css` | Safir tasarım sisteminin stilleri. | §8.23 |
| `app/src/sade/render/monitor.ts` · `screens/monitor.ts` | Monitör. | §8.12 |
| `app/src/sade/render/giris.ts` · `screens/giris.ts` | Yeni arz girişi. | §8.13 |
| `app/src/sade/render/sonuc.ts` · `screens/sonuc.ts` | Tahmin sonucu. | §8.14 |
| `app/src/sade/render/analiz.ts` · `screens/analiz.ts` | Analiz (arz sayfası). | §8.15 |
| `app/src/sade/render/calc.ts` | Seri hesaplayıcı. | §8.16 |
| `app/src/sade/render/perf.ts` · `screens/perf.ts` | Model performansı. | §8.17 |
| `app/src/sade/render/sicil.ts` · `screens/sicil.ts` | Sicil. | §8.18 |
| `app/src/sade/render/kayitlarim.ts` · `screens/kayitlarim.ts` | Kayıtlarım. | §8.19 |
| `app/src/sade/render/ayarlar.ts` · `screens/ayarlar.ts` | Ayarlar ve Hakkında. | §8.20 |
| `app/src/sade/screens/sihirbaz.ts` | Sihirbaz kabuğu: eski dondur ve D1 sonrası sihirbazlarını sade kabukta açar. | §8.21 |
| `app/src/sade/render/common.ts`, `shell.ts` | Sade görünümün ortak parçaları ve üst barı. | §8.11 |
| `app/src/dev/demo.ts`, `dialog-demo.ts` | Yalnız geliştirme: ekran görüntüsü koşusu ve dosya seçici taklidi; üretimde ölü kod. | §8.25 |

### app/src-tauri/ (Rust arka uç)

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `app/src-tauri/Cargo.toml` | `borsai-app` paketi ve workspace (`.` + `crates/borsai_predict`); Tauri 2, serde, serde_json bağımlılıkları; `snapshot` özelliği. | §7.3 |
| `app/src-tauri/Cargo.lock` | Rust bağımlılıklarının kilitli sürümleri. | §7.3 |
| `app/src-tauri/build.rs` | Derlemede modelleri ve INDEX'leri gömer, sonra `tauri-build`'i çağırır. | §7.3 |
| `app/src-tauri/build_embed.rs` | `build.rs` ile testlerin ortak gömme kodu: model kümesi, sha zinciri, TÜFE tablosu, süzülmüş zaman-dışı skorlar. | §7.3 |
| `app/src-tauri/tauri.conf.json` | Pencere (1440 × 900), CSP ve paket ayarları. | §7.5 |
| `app/src-tauri/capabilities/default.json` | İzinler: yalnız `core:default` ve `dialog:default`; dosya, kabuk ve HTTP eklentisi yok. | §7.5 |
| `app/src-tauri/icons/` | Uygulama simgeleri (`icon.icns`, `icon.ico`). | — |
| `app/src-tauri/gen/schemas/` | Tauri'nin ürettiği izin şemaları; git'e girmez. | — |
| `app/src-tauri/.gitignore` | `/target/` ve `/gen/schemas` git'e girmez. | — |
| `app/src-tauri/src/main.rs` | Giriş noktası (6 satır). | §7.2 |
| `app/src-tauri/src/lib.rs` | Uygulamanın kurulumu: açılış doğrulaması, durum ve komut listesi (`generate_handler!`). | §7.2, §7.7 |
| `app/src-tauri/src/state.rs` | `AppState`: doğrulanmış gömülü model kümesi ve çalışma ayarları. | §7.2, §7.6 |
| `app/src-tauri/src/embedded.rs` | Gömülü dosyaların tipleri; içeriği `build.rs` üretir. | §7.3 |
| `app/src-tauri/src/json_out.rs` | Python'un `pretty_json_bytes`'ıyla bayt-eşit JSON yazıcı. | §7.9.4 |
| `app/src-tauri/src/python.rs` | Repo içi Python çağrısı; yalnız repo modunda, ağsız, bytecode yazmadan. | §7.5 |
| `app/src-tauri/src/clock.rs` | İstanbul saati (UTC+3 sabit) ve tarih hesabı. | §7.9.2 |

### app/src-tauri/src/commands/

55 Tauri komutu bu dosyalara dağılır. Ayrıntılı katalog §7.7'dedir.

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `commands/mod.rs` | Komut modüllerinin listesi; her komut `Result<T, AppError>` döner. | §7.7 |
| `commands/models.rs` | Gömülü model kümesinin açılış doğrulaması ve derleme bilgisi (`app_info`). | §7.4 |
| `commands/config.rs` | Ayar dosyası ve repo modu doğrulaması (`get_config`, `set_config`, `validate_repo`, `set_ui_view`). | §7.6 |
| `commands/form.rs` | Girdi formunun anında denetimi (`check_form`). | §7.9.1 |
| `commands/predict.rs` | Bütün gömülü modellerle tahmin (`predict_all`). | §7.9.2 |
| `commands/market20.rs` | f6'yı repo modunda Python'dan alır (`market20_via_python`). | §7.7 |
| `commands/ceiling.rs` | Tavan serisi görüntüleri ve koşullu güncelleme (`ceiling_display`, `streak_view`, `ceiling_summary`, `record_summary`). | §7.9.3 |
| `commands/path.rs` | Tavan yolu görüntüleri ve koşullu getiri (`path_display`, `path_conditional`, `path_params`). | §7.8.6, §7.9.3 |
| `commands/fall.rs` | Düşüş kartının derlenmesi (yardımcı, komut yok). | §7.8.7 |
| `commands/inputs_doc.rs` | Girdi belgesini okur ve yazar (`list_input_documents`, `read_input_document`, `preview_inputs_doc`, `write_inputs_doc`). | §7.9.4 |
| `commands/source_docs.rs` | Kaynak belgeleri sicile kopyalar (`copy_source_docs`, `read_source_manifest`). | §7.9.4 |
| `commands/freeze.rs` | Resmî dondur akışı (`freeze_preflight`, `inputs_pit_check`, `freeze_record`, `cancel_record`, `freeze_todo`); kaydı Python yazar. | §7.9.4 |
| `commands/parity.rs` | Dondurulmuş kaydın Rust ile parite denetimi (yardımcı, komut yok). | §7.9.4 |
| `commands/git.rs` | Salt okuma git çağrıları için beyaz liste (komut yok). | §7.5 |
| `commands/post_d1.rs` | D1 sonrası kayıtlar ve sihirbazı (6 komut). | §7.10 |
| `commands/registry.rs` | Sicil ekranı ve arz sayfası (`registry_view`, `record_ceiling`, `read_record_json`). | §7.7 |
| `commands/scenario.rs` | Kişisel kayıtlar (6 komut); yalnız uygulama verisine yazar. | §7.7 |
| `commands/scores.rs` | `scores.json` okuyucusu (`score_hints`, `scores_view`, `scores_post_d1_view`). | §7.7 |
| `commands/scores_oot.rs` | Zaman-dışı skor okuyucusu (`scores_oot_view`, `scores_oot_model`). | §7.7 |
| `commands/sade.rs` | Sade görünüm komutları (`monitor_view`, `arz_view`, `headline_gate`, `perf_view`). | §7.7, §8.11 |
| `commands/sade_break.rs` | Sade görünümün kırılma kartı (`break_view`). | §7.7, §8.15 |
| `commands/snapshot.rs` | Yalnız geliştirme: ekran görüntüsü (4 komut); `snapshot` özelliği olmadan çalışmaz. | §7.7, §8.25 |

### app/src-tauri/crates/borsai_predict/

Modellerin Rust portu; Tauri'den bağımsız, saf crate.

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `crates/borsai_predict/Cargo.toml` | Crate tanımı. | §7.8 |
| `src/lib.rs` | `predict`'in uygulamadaki tek gerçeklemesi; model türüne göre dağıtım. | §7.8.2 |
| `src/params.rs` | Model parametre dosyasının okunması ve Python'la aynı sırada denetimi. | §7.8.2 |
| `src/dec.rs` | Python `decimal` davranışının gereken kadarı (BigUint tabanlı `Dec`). | §7.8.1 |
| `src/sum.rs` | CPython `sum()`'ının Neumaier telafili toplaması. | §7.8.1 |
| `src/features.rs` | f1–f4 özellikleri. | §7.8.3 |
| `src/pb_features.rs` | pb1–pb4 özellikleri. | §7.8.3 |
| `src/horizons.rs` | Ufuklar ve fiziksel getiri sınırı. | §7.8.4 |
| `src/linear.rs` | V1.5 ailesi, kurallar ve PB modeli. | §7.8.4 |
| `src/market20.rs` | `v1_5_market20_v0`. | §7.8.4 |
| `src/hazard.rs` | Tavan serisi: hazard, KM ve v1 ailesi. | §7.8.5 |
| `src/survival.rs` | Tavan serisi eğrileri ve koşullu güncelleme. | §7.8.5 |
| `src/path.rs` | Tavan yolu modelleri. | §7.8.6 |
| `src/fall.rs` | Düşen arz ailesi. | §7.8.7 |
| `src/post_d1.rs` | D1 sonrası model. | §7.8.8 |
| `src/tufe.rs` | TÜFE tablosunun okunması ve denetimi. | §7.8.9 |
| `src/output.rs` | Tahmin çıktılarının Python sözlükleriyle aynı yapısı. | §7.8.10 |
| `src/error.rs` | Hata ve ret türleri; kodlar Python'la birebir. | §7.8.10 |
| `tests/golden.rs` | Rust ↔ Python paritesi: altın vektörlerin hepsi. | §7.11 |
| `tests/records_parity.rs` | Resmî kayıtlarla parite (asıl repo gerekir). | §7.11 |
| `tests/coverage.rs` | Uç yolların kapsamı: her ret ve uyarı kodu en az iki satırda. | §7.12 |
| `tests/dec_semantics.rs`, `tufe_semantics.rs` | Sayısal alan kararları ve TÜFE okuma; beklenenler Python'dan. | §7.12 |
| `tests/fall_semantics.rs`, `post_d1_semantics.rs`, `v1_semantics.rs` | Model ailelerinin anlam birim testleri. | §7.12 |
| `tests/common/mod.rs` | Parite testlerinin ortak kodu. | §7.11 |

### app/src-tauri/tests/

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `tests/build_embed.rs` | Gömme planı ve git kuralları. | §7.12 |
| `tests/integrity.rs` | Gömülü model kümesinin bütünlüğü; tek uyuşmazlıkta kapanma. | §7.4, §7.12 |
| `tests/no_network.rs` | Ağ bağımlılığı yok. | §7.5 |
| `tests/stage2.rs`, `stage3.rs`, `stage4.rs` | Aşama 2–4 kabul testleri; vitest fixture'larını gerçek komut çıktısından üretir. | §7.12, §8.25 |
| `tests/oot_panel.rs` | Zaman-dışı panelin Rust tarafı. | §7.12 |
| `tests/sade.rs` | Sade görünüm komutları, gerçek repo dosyalarıyla. | §7.12 |
| `tests/e2e.rs` | Uçtan uca dondur akışı ve kişisel kayıt izolasyonu; yalnız geçici klonda. | §7.12 |

### app/parity/

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `app/parity/README.md` | Parite kuralları ve karşılaştırma toleransları. | §7.11 |
| `app/parity/gen_golden.py` | Altın vektör üreticisi: Python tahminlerini `golden/*.jsonl`'a yazar; `--check` ile fark arar. | §7.11 |
| `app/parity/test_gen_golden.py` | Üreticinin Python testleri. | §7.11 |
| `app/parity/golden/` | Altın vektörler: 28 model `.jsonl`, 3 `.conditional.jsonl`, `_patched_params.jsonl`, `MANIFEST.json`, `README.md`; toplam 13 102 satır. | §7.11 |
| `app/parity/bit_equal_floor.json` | Bit-eşitlik tabanı: oranın düşemeyeceği alt sınırlar. | §7.11 |
| `app/parity/dec_cases.json` | Decimal anlam testlerinin Python'dan alınan beklenenleri. | §7.11 |
| `app/parity/tufe_cases.json` | TÜFE okuma testlerinin beklenenleri. | §7.11 |
| `app/parity/incidents/` | Parite olay dosyalarının yeri; şimdilik yalnız `.gitkeep`. | §7.9.4 |

### app/tests/ (ön uç testleri)

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `app/tests/*.test.ts` | 24 vitest dosyası, 376 test. | §8.25 |
| `app/tests/no_frontend_math.test.ts` | "Ön uç hesap yapmaz" statik taraması. | §8.6 |
| `app/tests/u52_declaration.test.ts`, `decl_flow.ts` | Kullanıcı beyanından türetilmiş sayının arayüzde olmadığını sınar; `decl_flow.ts` AST ile veri akışı taraması. | §8.16, §8.25 |
| `app/tests/sade_render.test.ts`, `sade_invoke.test.ts`, `sade_static.test.ts`, `sade_svg_format.test.ts` | Sade görünümün render, komut çağrısı, statik ve biçim testleri. | §8.25 |
| `app/tests/helpers.ts` | Test yardımcıları; fixture yolları. | §8.25 |
| `app/tests/fixtures/ui/` | 97 JSON: Rust komutlarının gerçek çıktısından üretilmiş görünüm fixture'ları. | §8.25 |
| `app/tests/fixtures/scores/` | 11 sentetik skor dosyası ve README. | §8.25 |
| `app/tests/fixtures/outcomes/` | Kurgusal SNTA1 ve SNTB1 arzlarının 6 sentetik sonuç dosyası ve README. | §8.25 |
| `app/tests/e2e_freeze_tmp_repo.sh` | Dondur akışı uçtan uca, geçici klonda. | §7.12, §8.25 |
| `app/tests/e2e_post_d1_tmp_repo.sh` | D1 sonrası sihirbazı uçtan uca, geçici klonda. | §7.12, §8.25 |
| `app/tests/e2e_personal_isolation.sh` | Kişisel kayıt ve kullanıcı beyanı izolasyonu. | §8.25 |
| `app/tests/golden_unchanged.sh` | Eski altın dosyaların bayt-eşit kaldığını denetler. | §7.11 |

### app/scripts/ ve app/docs/

| Yol | Ne işe yarar | Bölüm |
|---|---|---|
| `app/scripts/env.sh` | Rust ve Node araç zincirini kabuğa yükler. | §8.1 |
| `app/scripts/dev.sh` | Uygulamayı geliştirme modunda açar. | §8.1 |
| `app/scripts/test.sh` | Bütün uygulama testleri: vitest, cargo (164 test) ve ortam isteyen Rust testleri. | §7.12, §8.25 |
| `app/scripts/screens.sh`, `screens_p2.sh`, `screens_p34.sh`, `screens_v2.sh` | Ekran görüntüsü koşuları (yalnız geliştirme). | §8.25 |
| `app/docs/screens/README.md` | Ekran görüntülerinin listesi ve nasıl üretildiği. | §8.25 |
| `app/docs/screens/*.png`, `app/docs/screens/v2/` | Ekran görüntüleri (README 37 png anar); bu kopyada yok, gerçek repoda var. | §8.25 |

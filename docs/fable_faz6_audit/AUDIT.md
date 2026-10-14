# BORSAI_FAZ6_FABLE_OOT_AUDIT_20260925 — Eski kohort altyapısının uygunluk denetimi, girdi örneklemi, kuru S2 koşusu, mutasyon denetimi

Denetleyen: Fable (şartnamenin yazarı; uygulamayı Opus yaptı). Denetlenen: `94ad4e8` (S0b kararlar) → `1d4913e` (A altyapı) → `2e088c3` (S1 üyelik + girdiler) → HEAD `cec77dc` (push kanıtları). Tarih: 2026-09-25 (İstanbul; sistem saati 2026-09-24T21:27Z'de başladı). Çalışma ağacında yalnız görev dosyası ve bu dizin izlenmeyen.

Sınırlar: ağ yalnız (a) dört BIST tatil tablosu PDF'i ve (b) beş pinli KAP/SPK belgesinin yeniden indirilmesi için kullanıldı; **hiçbir THB/THM bülteni istenmedi, HEAD bile atılmadı.** Git yalnız okuma (`GIT_OPTIONAL_LOCKS=0`); mutasyon ve kuru koşu `/tmp/borsai_faz6_audit/clone` (`git clone --local`). Kohort üyelerinin listeleme sonrası hiçbir fiyat, getiri, tavan ya da hacim bilgisine bakılmadı; `docs/faz6/dogrulama/EXPOSURE.md` §3 okunmadı; hangi kodun SEALED olduğu bu raporda yazılmaz. Korunan ağaçlar (`registry/`, `data/`, `scores/`, `models/`) önce/sonra aynı: `ekler/koruma_once.txt` = `ekler/koruma_sonra.txt`.

İşaretler: **[ÖLÇTÜM]** bu oturumda betik/komutla; **[ÇIKARIM]** yorum. Bağımsız betikler (`kasa_bagimsiz.py`, `rejim_bagimsiz.py`, `takvim_c_denetim.py`, `orneklem_denetim.py`) `borsai` import etmez (her biri sonda `sys.modules` denetimini basar: "borsai sys.modules içinde mi: False"); yalnız `features_karsilastirma.py`, `s2_kuru_kosu_analiz.py`, `mut_d_probe.py` ve mutasyon/test koşuları repo kodunu çağırır.

## 0. Hüküm

**S2_OK.** Altyapı ve girdiler S2'yi (135 üye × 19 model, kalıcı tahmin kayıtları) yazmaya hazırdır. Gerekçe:

| Konu | Sonuç | Dayanak |
|---|---|---|
| Kod ↔ şartname + KARARLAR | D1–D8 ve I1–I27'nin hepsi uygun ya da kabul edilebilir, belgelenmiş sapma; model davranışını değiştiren hiçbir madde yok | §1 |
| Kasa (I4, D2) | Yalnız metinden bağımsız yeniden üretim **135/135**; on alternatif okumanın yalnız eşdeğeri (`choice(dizi)`) aynı sonucu veriyor | §2 |
| Rejim etiketleri | Kural tarihlerinden bağımsız yeniden hesap **135/135**, sayılar INFRA_RAPOR §5 ile aynı | §3 |
| Takvim C (I15) | Resmi siteden indirilen 4 PDF'in sha256'sı pinlerle 4/4 eşit; PDF metninden ayrıştırılan tam/yarım gün kümeleri ile **1360/1360 satır** uyuşuyor; seans kümesi = XU100 gün kümesi (930) | §4 |
| Girdi örneklemi (15 üye, 296 dolu alan) | sha 296/296, yayın < ilk işlem 296/296, değer belgede 285/285 (alıntılı alanlar), taşıma kuralı 21/21, türetilmiş 21/21; 5 belge yeniden indirildi, sha 5/5 eşit; `borsai.features` 15/15 beklenenle eşit | §6 |
| Kuru S2 (klon) | 135 kayıt × 19 model = 2565 hücre; durum sayıları INFRA_RAPOR §6 ile aynı; 5 kaydın 95 hücresi doğrudan `predict` çağrısına bit-eşit; şema §5 tam | §7 |
| Mutasyonlar | 16 mutasyonun 14'ü kırmızı; **(b) ve (i2) yeşil** → bulgu F1 (ÖNEMLİ) ve F3 (KÜÇÜK, eşdeğer mutant); (d) kırmızı ama tesadüfi → bulgu F2 (ÖNEMLİ) | §8 |
| Tam test | pytest **594 geçti** (325 s); `bash app/scripts/test.sh` yeşil | §9 |

Bulgular (§10): KRİTİK yok. ÖNEMLİ 2 (ikisi de test kapsamı: kod şartnameye uygun, mutant yakalanmıyor; S2'yi engellemez, S3/S5'ten önce kapatılmalı). KÜÇÜK 7. Hiçbiri model_id'yi etkilemez.

S2 için uygulama notu (INFRA_RAPOR §9 ile aynı): temiz ağaçta `python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv`; yalnız `registry/oot/records/` commit'i; push; `push_proof`. Commit öncesi `test_faz4_ceiling_path.py::test_new_models_are_retro_with_no_record_and_no_metric` (registry kirli) beklenen kırmızıdır; commit sonrası deselect'siz koşu.

## 1. Uygunluk: kod ↔ şartname (`b8763fc`) + KARARLAR (`94ad4e8`) [ÖLÇTÜM: kod okuması + testler + §2–§8 ölçümleri]

Hüküm sözlüğü: **uygun** = lafza uyar; **sapma/kabul** = lafızdan ayrılır, davranışı değiştirmez ya da KARARLAR/görev kararıyla gerekçelidir; **sapma/bulgu** = §10'da bulgu.

### 1.1 Şartname bölümleri

| Madde | Kod | Hüküm |
|---|---|---|
| §1 üyelik: pencere 2020-01-01…2023-09-21, 135 MEMBER + GMTAS `OUT_OF_SCOPE`, payda dosyası sütunları, append-only, CANCELLED | `registry.COHORT_START/END`, `validate_cohort`, `append_cohort`, `cohort_append_only_problems`; S1 dosyası koddan birebir yeniden üretiliyor (`test_real_cohort_validates_and_reproduces_from_code`) | uygun (I5 iptal kuralı kabul) |
| §1 gerçekleşen D_1 = KAP tarihinden önce olmayan, sözleşme > 0 ilk resmi seans | `outcomes_oot.resolve_member` → `outcomes.resolve_sessions(start = first_trading_date)`; 15 seans sınırı ilk görünüşten; hiç görünmezse DUR | uygun (I17) |
| §1 girdisi olmayan üye SKIPPED: INPUTS_NOT_AVAILABLE | `freeze.build_oot_records` (`skipped`), `scoring.oot_model_rows` (`ROW_SKIPPED`) | uygun (bugün 135/135 girdi var) |
| §2 S1 G1: `registry/oot/` sonuç alanı taşımaz; kaynak yayını < ilk işlem günü; belge sha | `registry.oot_outcome_key_problems`, `inputs_pit_problems`; testler; örneklemde 296/296 (§6) | uygun (mutasyon h kırmızı) |
| §2 S2 G2: kayıt bütün INDEX modellerini içerir; model commit'lerinin torunu; yeniden yazılmaz | `build_oot_record` (her INDEX modeli, ret hücreleri dahil), `_write_new('xb')`, içerik adresli ad; bekçi `test_oot_records_hold_every_index_model_and_follow_model_commits` | uygun (mutasyon l kırmızı) |
| §2 S3 G3: `d1_rows` yalnız `<T>.E`, yalnız D_1; zip sha pini; kohort düzeyi kapı | `extract_d1_rows`, `d1_row_doc`, `d1_rows_problems` (tek tanım `registry.post_d1_record_problems`), `download_gate` | uygun (I22) |
| §2 S5/G5 (zip repoya girer) → **KARARLAR D6 yerine geçer** | zip repoya girmez; karantina; yalnız açık küme ayıklanır; MANIFEST_OOT pinleri; bekçiler | uygun D6 ile (aşağıda) |
| §2 `oot_ingest_commit` | `scoring.oot_ingest_commit`: min(outcomes csv, ham kopya, d1_rows, [D_1..D_10] seans tarihli zip) | sapma/kabul (I10: terimler genişletildi, yön muhafazakâr) + KÜÇÜK not F4 (zip terimi takvim aralığı yerine gerçekleşen seans tarihleri; D6 bekçisiyle boş) |
| §2 `class_oot` sözde kodu | `scoring.class_oot`: model commit'i atası VE model push kanıtı var VE kayıt commit'i atası VE kanıt(kayıt) < kanıt(sonuç) VE kohort kapısı (**bütün MEMBER**) VE ek koşul; sonuç commit'siz → HEAD'e karşı DAG, kanıt sırası gösterilemez → OOT_RETRO | uygun (I13; D6-5 şartnameye üstün; mutasyon k, i kırmızı) |
| §2 post_d1 ek koşulu (d1_rows sha, zip pini, S3 commit'i atası) | `oot_post_d1_block`: `extra_ok` = d1_rows sha kayıttakiyle, D_1 = kayıttaki, MANIFEST_OOT pini eşit; ingest terimi D_1 sonrası | uygun (I23) |
| §2 var olan bekçilerle uyum | `test_registry_carries_no_outcome_fields` iki eski kohort dizinini kendi (daha sıkı) bekçisine bırakır; 8 yeni bekçi | uygun (I25) |
| §3 üçüncü ölçek `OOT_PRE_H99`; `ScaleMixError`; `scores.json` üst anahtarı; uygulama paneli | `SCALE_OOT` metin sabiti, `_one_scale`/`merge_scales` değişmedi (test: 5 ölçekle karışım reddi, mutasyon j kırmızı); **ayrı dosya** `scores/scores_oot.json`; panel sonraki görev | sapma/kabul (I1 ayrı dosya, I24 Enum yerine sabit); panel açık iş |
| §4 girdiler; `regime_tags`/`vault` girdi dosyasında | Girdiler bayt-eşit alındı; etiket ve kasa **yalnız** kohort dosyasında; kayıt ikisini satırdan kopyalar | sapma/kabul (I2) |
| §4 f6: XU100 pinli seri + Takvim C, `ref_date = first_trading_date` | `market20.oot_market20`, `load_oot_sources` (seans = XU100 günü denetimi) | uygun (I20; 135/135 ret yok) |
| §4 tavan yolu: dönem adım tablosu, farklıysa uygulanamaz | `registry.tick_table_mismatch`, `limit_path_with` (JSON tablosuyla `predict_path.limit_path`'e 2000 fiyatta eşit) | uygun (I7; §3) |
| §4 D1 alanları (post_d1) | S3 kalıbı | uygun |
| §5 kayıt şeması ve alanları | `borsai.oot_record/1`, `OOT_PRE_LISTING`, `OOT_PRE_H99`, `cohort_file_sha256`, `inputs_sha256`, `models_index{path,sha256}`, `models[]{model_id, params_sha256, status ∈ {PREDICTED, REFUSED, NOT_APPLICABLE_REGIME}, refusal, output}`, `comparators`, `regime_tags`, `recorded_at_utc`, `code{git_head, borsai_source_sha256}` (+I19 ek alanlar) | uygun (§7 kuru koşu) |
| §5 last10 kuralları donmuş H99 + `comparator_note` | `COMPARATOR_NOTE_LAST10 = FROZEN_H99_LAST10_NOT_CHRONOLOGICAL`, diğerleri `FROZEN_H99` | uygun (135/135) |
| §5 tek toplu koşu; sonradan eklenen üye | `write_oot_records` önce bellekte hepsi, sonra yazım; yinelenen kayıt atlanır | uygun (I12, I26) |
| §6 tanımlar, metrikler, aralık | `outcomes.outcome_rows`'un kendisi (+`outcome_basis`); `paired_metric`, blok bootstrap aynı | uygun |
| §6 birincil hücreler | `OOT_PRIMARY_CELLS`: v1_5 D5 MAE/medyan; v1_6 D10 MAE/v1_5; market20 D5 MAE/v1_5; pb_v0 D5 MAE/medyan; hazard ve pb_ceiling RPS/**yalnız** km_expanding; iki yol modeli SPEC_CEILING_PATH_V0 §5 (D5 MAE/medyan); post_d1 SPEC_POST_D1 §4 | uygun (I11) |
| §6 n kuralları, sayaçlar, kasa açılınca ayrı anahtarlar | açık küme birincil; yıl ve rejim kırılımları ikincil/keşif; sayaçlar tam (+`n_exposed_codex`, `n_pending`, `n_skipped`); `_sealed`/`_all` S6'da | uygun; S6 açık iş |
| §7 rejim tablosu | `compute_regime_tags`, `regime_not_applicable` | uygun (I6–I9, I18, I21; §3 135/135) |
| §8 beklenti | kod dışı | — |
| §9 kasa K2, açılma koşulu | `draw_vault` (I4); `open_vault` iskeleti (özellik şartnamesi commit'li + kanıtlı; yeniden indirme + sha eşitliği) | uygun (§2) |
| §10 yerleşim | `outcomes_oot.py` ayrı modül (şartname `outcomes.py` içinde diyordu); `Scale` sabit | sapma/kabul (yerleşim) |

### 1.2 KARARLAR D1–D8

| Karar | Hüküm | Kanıt |
|---|---|---|
| D1 2020-01-01; 135 üye + GMTAS | uygun | kohort dosyası; evren listesi sayıları 8/52/38/37 |
| D2 kasa %50, yıl tabakalı, PCG64(20260924), (ftd, ticker); maruz kodlar önce çıkarılır; liste commit + push | uygun | §2: 135/135; S1 commit'i `2e088c3`'ün push kanıtı `2026-09-24T21:18:56Z` |
| D3 CLAUDE.md metinleri | uygun, **birebir** | betik: iki alıntı da CLAUDE.md'de aynen; `git diff 7f1b3d7 HEAD -- CLAUDE.md` yalnız bu iki satır |
| D4 eğitimde kullanım | kod dışı; SEALED hiçbir dosyaya ayıklanmaz | `test_sealed_codes_absent_from_every_extracted_file`; `training_table.csv` dokunulmadı |
| D5 post_d1 `MACHINE_SEQUENCED` ayrı alt tablo; `n_exposed_*` görünür | uygun | `oot_post_d1_block`, `cohort_counters` |
| D6-1 zip repoya girmez, karantina | uygun | `quarantine_dir` repo içini reddeder; bekçi (mutasyon m kırmızı) |
| D6-2 yalnız OPEN satırları; `data/outcomes_oot/<T>.csv`, ham kopya, MANIFEST_OOT | uygun (bulgu F2: D_10'da durma testsiz) | `extract_open_members`, `extract_code_row` |
| D6-3 SEALED satırı hiçbir yere yazılmaz; istenirse bülten açılmadan hata | uygun | `assert_extractable` `fetch`'ten önce (mutasyon c kırmızı) |
| D6-4 açılışta yeniden indirme + sha | uygun (iskelet) | `open_vault` |
| D6-5 sıra kapısı: sonuç commit'i bütün S2 kayıtlarının torunu; S2 kanıtı önce; indirme kapıya bağlı | uygun (bulgu F1: kapının SEALED kapsamı testsiz) | `download_gate`/`s2_gate_problems` (bütün MEMBER), `cohort_gate_ok`, `class_oot`; mutasyon a, i, k kırmızı |
| D6-6 `outcome_basis = MACHINE_EXTRACTED` | uygun | sütun + okuyucu reddi |
| D7 Codex çıkarır, doğrulayıcı doğrular; aday özellikler ayrı | uygun | bayt-eşit içe aktarım (test), `candidate_features/` 135 dosya, §6 örneklem |
| D8-1 SPK kurumsal işlem satırı maruziyeti sayılır; üyeler kasaya girebilir | kısmen: sayaç `null`, kohort toplamı 28; üye başına etiket S6'ya ertelendi | I14; bulgu F5 (karar) |
| D8-2 fiyat/pay için BIST listeleme bildirimi birincil | uygun | örneklemde 15/15 `ipo_price_tl`, `shares_offered` BIST bildiriminden |
| D8-3 SPK bülteni gün sonu üst sınırı | uygun | örneklemde 15/15 `T23:59:59+03:00`; hepsi talep toplama başlangıcından önce (`pit_pb.ok`) |
| D8-4 FILTERED alan düzeyi işaret | uygun | MIATK, VBTYZ örneklemde FILTERED; model farkı görmez |
| D8-5 repoya alınacaklar | uygun | `registry/oot/{inputs,source_docs,candidate_features}`, `docs/faz6/dogrulama/` |

### 1.3 SPEC_DEVIATIONS I1–I27

| # | Hüküm | Not |
|---|---|---|
| I1 ayrı skor dosyası | sapma/kabul | uygulama `scores.json`'u gömer; `scores.json` bayt-eşit dokunulmamış (`git diff 7f1b3d7 HEAD -- scores app models` boş) |
| I2 vault/regime_tags yalnız kohort dosyasında | sapma/kabul | tek kaynak; girdiler bayt-eşit (test) |
| I3 EXPOSED_CODEX değeri, açık küme = OPEN ∪ EXPOSED_* | uygun | D2 lafzı ("kasaya giremez") |
| I4 kasa algoritması | uygun | §2 bağımsız 135/135; aşağı yuvarlama kasayı hiçbir tabakada yarının üstüne çıkarmaz |
| I5 CANCELLED | uygun | lafız + canlı payda kalıbı |
| I6 MARGIN: 6 model | uygun | kuru koşuda 1 üye × 6 hücre |
| I7 R3: yalnız iki yol modeli | uygun | 3 üye; §3 not: kural "yol farklı", "fiyat ≥ 100" değil (4 üye ≥ 100 TL, biri aynı yolu veriyor) |
| I8 ALLOC talep toplama başlangıcı | uygun | D_1 okumasıyla 4 üye farklı (bağımsız hesapla aynı) |
| I9 iki açığa satış bayrağı | uygun | 134 / 32 |
| I10 ingest terimleri | sapma/kabul | muhafazakâr; F4 notu |
| I11 birincil hücreler | uygun | |
| I12 en erken etkin kayıt | uygun | önceden ilan |
| I13 model kanıtı; MEMBER kapısı; commit'siz → RETRO | uygun | 19 modelin hepsinin push kanıtı var (en geç 2026-09-22T20:17:10Z) |
| I14 SPK sayacı null | sapma/karar | F5 |
| I15 Takvim C: tablo + 5 XU100-boşluk günü; S5 HEAD probu | uygun | §4: 5 gün bağımsız olarak da tabloda yok |
| I16 sütunlar, ham kopya, MANIFEST_OOT | uygun | |
| I17 D_1 kuralı | uygun | |
| I18 maruziyet sınıf adları; EXPOSED_ARCHIVE takvimden | uygun | bağımsız hesap D2 listesiyle aynı |
| I19 ek kayıt alanları | uygun | sınıf/sonuç alanı yok (test) |
| I20 en yeni pinli XU100 | uygun | kayıtta `xu100_graphic_20260922.json` |
| I21 MARGIN_NOT_10PCT yalnız Yıldız/Ana | uygun | kohortta ALT/GİP üyesi yok |
| I22 S3 okuma/atıf | uygun | |
| I23 POST_D1 şema, zaman sınırı yok | uygun | |
| I24 ölçek sabitleri | sapma/kabul | davranış aynı |
| I25 bekçi istisnası | uygun (daha sıkı) | |
| I26 ön koşul | uygun | mutasyonsuz kuru koşu temiz klonda geçti; testte kirli ağaç reddi |
| I27 SEALED üyeler S2 kaydı alır | uygun | 135/135 kayıt |

### 1.4 POST_D1 ve listeleme öncesi akışlar değişmedi mi? [ÖLÇTÜM]

`git diff 7f1b3d7 HEAD -- borsai tests/test_outcome_guard.py` içindeki **silinen** satırlar yalnız: `freeze.py` CLI'daki `_is_post_d1` yardımcısının `_record_stage` ile değiştirilmesi (iptal komutu üç kayıt türünü aşamaya göre yönlendirir; POST_D1 ve listeleme öncesi için davranış aynı) ve `test_outcome_guard.py`'de I25 istisna satırı + docstring. `predict*.py`, `features.py`, `survival.py`, `horizons.py`, model JSON'ları, `scores/`, `app/`, `models/`, `legacy/`, `experiments/` diff'i boş. Uygulamanın altın MANIFEST pini yeşil (§9).

## 2. Kasa çekilişi, bağımsız yeniden üretim (I4, D2) [ÖLÇTÜM `ekler/kasa_bagimsiz.py`]

Yalnız KARARLAR D2 ve I4 metninden; numpy 2.5.2; `borsai` yüklenmedi.

| Okuma | Eşleşme | Kasa n |
|---|---|---|
| **Ana okuma**: tek `Generator(PCG64(20260924))`, yıllar artan, tabaka içi (first_trading_date, ticker), `choice(n, n//2, replace=False)`, maruz 5 kod önce çıkarılır | **135/135** | 64 |
| `choice(ticker_dizisi, n//2, replace=False)` | 135/135 (eşdeğer çağrı) | 64 |
| `permutation(n)[:n//2]` | 65/135 | 64 |
| `shuffle(liste)[:n//2]` | 65/135 | 64 |
| `choice(..., shuffle=False)` | 73/135 | 64 |
| tek sayıda yukarı yuvarlama | 101/135 | 66 |
| her yıl için yeni üreteç | 71/135 | 64 |
| tabaka içi sıra yalnız ticker | 69/135 | 64 |
| yıllar azalan | 71/135 | 64 |
| maruz kodlar çekilişe girip sonra üzerine yazılır | 106/135 | 65 |
| tabakasız tek çekiliş | 72/135 | 65 |

Yıl × küme (dosyadan): 2020 4/4, 2021 26/26, 2022 19+1 maruz/18, 2023 17+4 maruz/16 → açık 71, kasa 64 (INFRA_RAPOR §4 ile aynı). Kural ihlali yok; değişiklik önerilmez. [ÇIKARIM] "Aynı sonucu veren başka makul okuma" yalnız numpy'nin dizi biçimli `choice` çağrısıdır (aynı indeks yolu); belirsizlik bırakan her öteki okuma farklı kasa verir, bu yüzden I4'ün yazılı olması gereklidir ve yazılıdır.

## 3. Rejim etiketleri, bağımsız yeniden hesap (§7) [ÖLÇTÜM `ekler/rejim_bagimsiz.py`]

Girdiler: evren listesi (pazar, KAP satış yöntemi), girdi belgeleri (`ipo_price_tl`, `ipo_price_try`, `bookbuilding_start`), pinli XU100 serisinin gün kümesi (Takvim C **kullanılmadı**), donmuş tavan yolu JSON'unun adım tablosu (veri), kural tarihleri `kurallar_arastirma.md` §1/§3/§6–7/§10, limit yolu SPEC_CEILING_PATH_V0 §2 lafzından yeniden yazıldı. **135/135 `regime_tags` dizisi birebir eşit.**

| Etiket | Bağımsız | INFRA §5 |
|---|---|---|
| TICK_TABLE_EPOCH=T2015 | 135 | 135 |
| TICK_TABLE_MISMATCH | 3 | 3 |
| MARGIN_RULE PRE/POST | 1 / 134 | 1 / 134 |
| MARGIN_NOT_10PCT | 1 | 1 |
| SALE_ON_EXCHANGE | 49 | 49 |
| PRICE_RANGE_BOOKBUILD | 9 | 9 |
| SHORT_SELL_BAN / …2020_END_NOT_FOUND | 32 / 134 | 32 / 134 |
| ALLOC PRE / THRESH100 / EQUAL_DIST | 54 / 54 / 27 | 54 / 54 / 27 |
| MARKET YILDIZ / ANA | 84 / 51 | 84 / 51 |
| EXPOSED_ARCHIVE / EXPOSED_CODEX | 4 / 1 | 4 / 1 |

Ek ölçümler: EXPOSED_ARCHIVE = takvim D_10 ≥ 2023-09-22 olan üyeler (XU100 gün kümesiyle) = D2 listesi (4 kod) ✓. I8: ALLOC D_1'e göre okunsaydı 4 üye değişirdi ✓. I7 sınırı: arz fiyatı ≥ 100 TL olan 4 üye var, 3'ü uyumsuz; dördüncüde (108,6 TL) T2015 ve JSON tabloları 250 TL seviyesini geçerken aynı taban yuvarlamasını verdiği için C_1..C_10 aynı çıkıyor — kural "fiyat ≥ 100" değil "yol farklı" (§7 R3 lafzı) ve kod buna uyuyor. [ÇIKARIM] `SHORT_SELL_BAN_2020_END_NOT_FOUND`'un 134 üyeyi kapsaması bayrağı alt küme olarak bilgisiz kılar; I9'un gerekçesi (bilinmeyen bitiş) doğru, keşif satırı olarak yorumlanmamalı.

## 4. Takvim C (I15) [ÖLÇTÜM `ekler/takvim_c_denetim.py`]

- Dört tatil tablosu resmi URL'lerden indirildi; sha256 `ekler/takvim_2020_2023.md` pinleriyle **4/4 eşit** (2020 a71e242b…, 2021 9a2b21f0…, 2022 fe1e6fe6…, 2023 696bc0f5…). PDF'ler repoya konmadı.
- PDF metni (macOS PDFKit) kural tabanlı ayrıştırıldı: bir tarih son geçtiği "seans yapılmayacaktır" parçasında ise tam kapanış, son "yarım gün seans yapılacaktır" parçasında ise yarım gün; takas cümleleri atlanır. Sonuç: 2020 tam 15 / yarım 2; 2021 tam 14 / yarım 3; 2022 tam 11 / yarım 2; 2023 tam 14 / yarım 2. Yarım günler eklerdeki tabloyla 4/4 eşit; tam kapanış kümeleri `market20.HOLIDAY_TABLES_2020_2023` ile aynı (ör. 2020-05-23 Cumartesi "Arife" tam kapanış, 2020-08-30 Pazar tam kapanış, 2023-10-28 Cumartesi tabloda "yarım gün" yazsa da işlem bilgisi "seans yapılmayacaktır" → tam kapanış; Takvim C aralığı dışında).
- **Satır satır: 1360/1360 uyuşma** (`full_closure`, `half_day`, `counts_as_official_session`, `is_weekend`, `weekday_name`, `source_year`, `source_pdf`, `source_pdf_sha256`, `source_locator`, `verification_status`). Seans 930 = XU100 kapanışı olan gün 930 (252/249/252/177). Hafta içi XU100 boşluğu 42 = tablonun hafta içi tam kapanışları (37) ∪ tabloda olmayan 5 gün {2023-02-09, 02-10, 02-13, 02-14, 04-24}; bu 5 gün bağımsız ayrıştırmada da tabloda yok. 9 yarım günün hepsinde XU100 kapanışı var.
- [ÇIKARIM] Beş kapanışın tek kanıtı XU100 boşluğu olmaya devam ediyor; kodun S5'ten önce THB HEAD probu (`check_xu100_gap_closures`, yayımlanmışsa DUR) doğru savunmadır ve testlidir. Bu denetimde prob **koşulmadı** (bülten HEAD'i yasak).

## 5. CLAUDE.md, skor/uygulama dokunulmazlığı [ÖLÇTÜM]

- KARARLAR D3'ün iki alıntısı CLAUDE.md'de birebir; kural 3'ün kalan cümleleri aynen; sıra kuralı satırına ek cümle aynen (§1.2).
- `git diff 7f1b3d7 HEAD --stat -- scores app models legacy experiments docs/SCORES.md docs/MODELS.md` boş.
- Push kanıtları: şartname `b8763fc` 2026-09-24T19:26:21Z; A `1d4913e` 21:18:55Z (S0b `94ad4e8`'i kapsar); S1 `2e088c3` 21:18:56Z. Sıra: şartname → kararlar → altyapı → üyelik/girdiler; hepsi bugünkü HEAD'in atası.

## 6. Girdi örneklem denetimi [ÖLÇTÜM `ekler/orneklem_denetim.py`, `features_karsilastirma.py`, `yeniden_indirme_out.txt`]

Seçim: `random.Random(20260925)`, yıllar artan sırayla, her yılda `sorted(ticker)` listesinden `rng.sample(k)` (2020: 2, 2021: 5, 2022: 4, 2023: 4) → ARZUM, FADE; BOBET, KZBGY, MIATK, ORCAY, VBTYZ; HUNER, OBASE, SEGYO, TERA; A1CAP, ATAKP, FORTE, SOKE. Kaynak: 15 üyenin `registry/oot/source_docs/<T>/` altındaki pinli belgeleri (58 belge: 16 KAP bildirimi, 15 SPK bülteni, 27 KAP eki; 13'ü yalnız OCR katmanlı). Metin: macOS PDFKit; OCR belgelerde Apple Vision (`ekler/pdfocr.swift`), doğrulayıcıdan bağımsız araç.

| ticker | ilk işlem | dolu | boş | sha OK | yayın<ilk işlem | alıntı EXACT | alıntı gevşek | alıntı FAIL | alıntısız | değer belgede | değer YOK | taşıma OK/FAIL | türetilmiş OK/FAIL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ARZUM | 2020-12-24 | 19 | 1 | 19 | 19 | 7 | 10 | 0 | 2 | 17 | 0 | 2/0 | 2/0 |
| FADE | 2020-08-06 | 17 | 3 | 17 | 17 | 7 | 10 | 0 | 0 | 17 | 0 | 2/0 | 2/0 |
| BOBET | 2021-06-03 | 20 | 0 | 20 | 20 | 8 | 10 | 0 | 2 | 18 | 0 | 2/0 | 3/0 |
| KZBGY | 2021-08-12 | 20 | 0 | 20 | 20 | 8 | 10 | 0 | 2 | 18 | 0 | 2/0 | 2/0 |
| MIATK | 2021-11-22 | 20 | 0 | 20 | 20 | 11 | 9 | 0 | 0 | 20 | 0 | 1/0 | 2/0 |
| ORCAY | 2021-09-02 | 20 | 0 | 20 | 20 | 11 | 9 | 0 | 0 | 20 | 0 | 1/0 | 0/0 |
| VBTYZ | 2021-07-12 | 20 | 0 | 20 | 20 | 12 | 8 | 0 | 0 | 20 | 0 | 0/0 | 2/0 |
| HUNER | 2022-02-21 | 20 | 0 | 20 | 20 | 12 | 8 | 0 | 0 | 20 | 0 | 0/0 | 2/0 |
| OBASE | 2022-08-03 | 20 | 0 | 20 | 20 | 10 | 10 | 0 | 0 | 20 | 0 | 2/0 | 2/0 |
| SEGYO | 2022-06-07 | 20 | 0 | 20 | 20 | 11 | 9 | 0 | 0 | 20 | 0 | 1/0 | 0/0 |
| TERA | 2022-12-22 | 20 | 0 | 20 | 20 | 8 | 10 | 0 | 2 | 18 | 0 | 1/0 | 2/0 |
| A1CAP | 2023-06-15 | 20 | 0 | 20 | 20 | 10 | 9 | 0 | 1 | 19 | 0 | 2/0 | 0/0 |
| ATAKP | 2023-07-27 | 20 | 0 | 20 | 20 | 9 | 10 | 0 | 1 | 19 | 0 | 2/0 | 2/0 |
| FORTE | 2023-06-14 | 20 | 0 | 20 | 20 | 11 | 9 | 0 | 0 | 20 | 0 | 1/0 | 0/0 |
| SOKE | 2023-01-12 | 20 | 0 | 20 | 20 | 8 | 10 | 1 | 1 | 19 | 0 | 2/0 | 0/0 |
| **toplam** | | **296** | 4 | **296** | **296** | 143 | 141 | 1 | 11 | **285** | **0** | **21/0** | **21/0** |

Okuma anahtarı ve notlar:
- **sha OK**: alanın `source_sha256`'sı = dosyanın sha256'sı = MANIFEST satırı (296/296). **yayın < ilk işlem**: alanın `source_published_at`'ının İstanbul tarihi < `first_trading_date` ve MANIFEST ile aynı (296/296).
- **alıntı**: EXACT 143 = alıntı belge metninde birebir; gevşek 141 = 1 boşluksuz eşleşme + 140 sözcük/sayı eşleşmesi (hepsi %100 token; SPK A.1 satırlarında PDFKit sütunları karıştırdığı, OCR belgelerde iki OCR motorunun satır kırdığı için); FAIL 1 = SOKE `post_ipo_share_capital` (PDFKit "386.500.000"ı "386.5" veriyor; sayfa görüntüsünde "386.500.000 TL" açıkça yazılı → değer doğru, araç artefaktı, bulgu F7); alıntısız 11 = 7 `total_demand_filter_status = NOT_SPECIFIED` (6'sında belgede "filtre" sözcüğü yok; TERA'da yalnız grup katları için "filtrelenmemiş" geçiyor, doğrulayıcının notu bunu söylüyor: bulgu F8, kabul) + 4 hesaplanmış f3 (pay/payda alıntılarıyla ayrıca denetlendi, aşağıda).
- **değer belgede 285/285**: 227 alanda değer alıntının içinde (Türkçe sayı ve tarih yazımları: "2,4", "18.000.000", "06/08/2020", "29-30/07/2020"); 41 alanda değer 0 ve kaynak SPK hücresinde "-" ya da "tamamının satışı gerçekleşmiştir" beyanı (`zero_from_statement`); 17 alanda değer SPK satırından türetilmiş toplam (taban = Bedelli + Mevcut Pay Satışı; azami = taban + Ek Pay Satışı) ve üç PB özdeşliği (A/B/C) 15/15 üyede tutuyor.
- **DATA_NOTES §2 taşıma** 21/21: (a) "tamamının satışı" alıntısı kaynak belgede bulundu, (b) satılan = planlanan taban özdeşliği aritmetik olarak tutuyor, (c) ek satış '-' ya da belgede yazılı; ayrıca 15/15 üyede satılan pay = artırım + ortak satışı + ek satış.
- **DATA_NOTES §5 f3**: 15 üyede 4 `CALCULATED_FROM_SOURCE_TOTALS` (ARZUM, BOBET, KZBGY, TERA): pay/payda alıntıları belgede, `pay/payda` ROUND_HALF_UP 10 ondalık yeniden hesabı 4/4 değere eşit; paydalar belgedeki nihai gerçekleşen arz nominali (TERA'da ek satış dahil 16.500.000, `denominator_includes_additional_sale = true`); 9 `SOURCE_REPORTED`, 1 `SOURCE_REPORTED_APPROX` (A1CAP), 1 boş (FADE, borsada satış). Filtre durumu: FILTERED 2 (MIATK, VBTYZ; alıntıda "filtre edilmiş"), UNFILTERED ve NOT_SPECIFIED alan düzeyinde işaretli.
- **Görsel denetim** (sayfa görüntüleri, `ekler/pdfpage.swift`): ARZUM SPK 2020/75 A.1 satırı (32.210.000 / 32.210.000 / - / - / 13.306.475 / 1.995.971 / 15,50-17) = girdi; TERA SPK 2022/69 (37.500.000 / 52.500.000 / 15.000.000 / - / - / 1.500.000 / 10,00) = girdi; SOKE BIST bildirimi (77.500.000; 7,5; 12/01/2023; 04-05-06/01/2023; sermaye 386.500.000) = girdi; KZBGY sonuç belgesi (60.000.000 nominal, 15,80 TL, 948.000.000 TL; talep toplamı 60.000.000 → f3 = 1) = girdi.
- **Yeniden indirme 5/5 sha eşit** (2026-09-24T21:36Z): FADE, BOBET, HUNER BIST/aracı kurum KAP bildirimleri (`api/BildirimPdf`), ARZUM SPK 2020/75, A1CAP SPK 2023/29.
- **`borsai.features`**: 15/15 üyede `compute_features` (f1–f5) ve `compute_pb_features` (pb1–pb3) çıktıları Decimal/Fraction ile bağımsız hesaplanan değerlere eşit (ARZUM PB `PB_PRICE_RANGE` reddi, KZBGY `PB_IDENTITY:PB3_RANGE` reddi beklenen; FADE f3 yok → f5 = 1).

[ÇIKARIM] Doğrulayıcı raporunun "%98,4 birebir, 200/200" iddiası bu bağımsız örneklemle çelişmiyor: 296 dolu alanın hiçbirinde belgeyle uyuşmazlık bulunmadı.

## 7. Kuru S2 koşusu (klon) [ÖLÇTÜM `ekler/s2_kuru_kosu_analiz.py`]

`/tmp/borsai_faz6_audit/clone` (HEAD `cec77dc`, temiz): `.venv/bin/python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv` → 5,8 s; **135 kayıt yazıldı, 0 atlandı, 0 yinelenen**; `cohort_file_sha256` dosyayla eşit; kayıt `code.git_head = cec77dc…`, `borsai_dirty = false`, `recorded_at_utc = 2026-09-24T21:30:50Z`. Kayıtlar gerçek repoya yazılmadı (klondan da taşındı; §11).

| Model | PREDICTED / REFUSED / NA (135) | Açık küme PREDICTED (71) | Ret kodları | NA kodları |
|---|---|---|---|---|
| v1_5_h99, v1_6_h99, v1_5_market20_v0, ceiling_hazard_v0 | 130 / 5 / 0 | 68 | F3_MISSING 5 | — |
| ceiling_path_v0 | 127 / 4 / 4 | 67 | F3_MISSING 4 | TICK_TABLE_MISMATCH 3, MARGIN_NOT_10PCT 1 |
| pb_v0, pb_ceiling_v0 | 112 / 23 / 0 | 59 | PB_IDENTITY 12, PB_PRICE_RANGE 9, PB_FIELD_MISSING 2 | — |
| pb_ceiling_path_v0 | 109 / 22 / 4 | 58 | PB_IDENTITY 11, PB_PRICE_RANGE 9, PB_FIELD_MISSING 2 | TICK_TABLE_MISMATCH 3, MARGIN_NOT_10PCT 1 |
| base_always_ceiling, ceiling_hazard_v0@INF, pb_ceiling_v0@INF, ceiling_path_v0@INF | 134 / 0 / 1 | 71 | — | MARGIN_NOT_10PCT 1 |
| 7 kural (median, mean, zero, rate, last10_rate, km_expanding, km_last10) | 135 / 0 / 0 | 71 | — | — |

- INFRA_RAPOR §6 ile aynı: f3 isteyen 5 model 130 (açık 68), PB 112 (açık 59), kural/@INF 135 (71); ret kodları 5 / 12+9+2. NA hücreleri: 4 üyede; her kayıtta `registry.regime_not_applicable(regime_tags)` ile ve bağımsız kuralla (MARGIN → 6 model, TICK → 2 yol modeli) **135/135 eşleşme**; hücrede modelin kendi `model_status` ve çıktısı görünür kalıyor (I6).
- **Bit-eşitlik**: `random.Random(20260925).sample` ile 5 kayıt (CVKMD, DNISI, KZBGY, QUAGR, UNLU): 95 hücrenin çıktısı, kaydın `model_inputs`'u ile doğrudan `predict_hazard/predict_path/predict_pb/predict_market20/predict.predict` çağrısına **95/95 `==`** (ve kanonik JSON eşit); `params_sha256` dosya ve INDEX ile eşit.
- **Karşılaştırıcılar**: 8 kural 135/135 kayıtta; `comparator_note` last10 iki kuralda `FROZEN_H99_LAST10_NOT_CHRONOLOGICAL`, diğer altısında `FROZEN_H99`; çıktı/durum/sha kuralın kendi hücresiyle aynı. km_expanding, km_last10, last10_rate, rate çıktısı 135 kayıtta tek değer (donmuş H99); median/mean/zero/always_ceiling 107 farklı değer (çıktı arz fiyatına bağlı fiyat düzeyi içeriyor; 107 farklı fiyat) — donmuş oran, arza göre ölçeklenmiş.
- **Şema §5**: 13 zorunlu alan + I19 ek alanları var; `models_index {path, sha256, model_ids}` 19 kimlik; `market20` bloğu Takvim C, `ref_date = first_trading_date`, ret yok; `vault` ve `regime_tags` kohort satırından; sonuç anahtarı yok; dosya adı içerik adresli; `inputs_sha256` dosyayla eşit 135/135.

## 8. Mutasyon denetimi [ÖLÇTÜM `ekler/mutate.sh`, `ekler/mutasyon_ciktilari.txt`, `ekler/mut_d_probe.py`]

Klon HEAD `cec77dc`; her mutasyon uygulandı, test(ler) koştu, geri alındı; sonda klon temiz (0 değişiklik). Bülten adları çıktılarda maskeli.

| # | Mutasyon | Test(ler) | Kırmızı mı |
|---|---|---|---|
| a | indirme kapısı push kanıtını aramaz | gate testi | **evet** |
| b | kapı SEALED üyelerin S2 kaydını aramaz | gate, class_oot kapı, ayıklayıcı, d1_rows, G5′ bekçisi (5 test) | **HAYIR** (5/5 yeşil) → F1 |
| c | ayıklayıcı SEALED kodu kabul eder | ayıklayıcı testi | **evet** |
| d | ayıklayıcı D_10'da durmaz (D_11+ okur) | 5 test | evet ama **tesadüfi**: 3 kırmızı + 1 error yalnız sentetik piyasa dosyası bittiği için (`NotPublished`); sonda: 60 seanslık piyasada mutant 61. seansı istiyor, hiçbir test "yalnız D_1…D_10" koşulunu doğrudan denetlemiyor → F2 |
| e | kasa tohumu 20260925 | sha kilidi, evren sayıları, gerçek kohort yeniden üretimi | **evet** (2/3; evren sayıları testi doğal olarak yeşil) |
| e2 | tabaka (yıl) sırası tersine | sha kilidi, gerçek kohort | **evet** (2/2) |
| f | marj kural tarihi 2020-03-14 | kural tarihi testi, gerçek kohort | **evet** (birim testi; gerçek kohort testi yeşil: sınır gününde üye yok, bilgi F9) |
| g | TICK eşiği: yalnız C_1..C_5 karşılaştırılır | 250 eşiği testi, gerçek kohort | **evet** (2/2) |
| g2 | T2015 tablosuna 250 kademesi eklenir | aynı | **evet** (2/2) |
| h | G1: girdi dosyasına `close` anahtarı | G1 bekçisi, bayt-eşit import | **evet** (2/2) |
| i | kohort kapısı hep açık (`cohort_gate_ok` → True) | class_oot kapı testi, DAG/kanıt testi | **evet** (1/2) |
| i2 | kayıt-atası koşulu kaldırılır (`record_ok = True`) | 3 class_oot/skor testi | **HAYIR** (3/3 yeşil) → F3: eşdeğer mutant (kohort kapısı üyenin kendi kaydını da kapsar) |
| j | `_one_scale` ve `merge_scales` OOT karışımını kabul eder | ölçek karışımı testi | **evet** |
| k | `class_oot` kanıt sırasını yok sayar | DAG/kanıt testi | **evet** |
| l | `freeze --oot` ilk modeli atlar | batch testi, gerçek kuru koşu, gate | **evet** (3/3) |
| m | kohort penceresi tarihli zip repoya konur | pencere bekçisi | **evet** |

Toplam 16 mutasyon (görevin 13'ü + e2, g2, i2): 14 kırmızı, 2 yeşil; (d) tesadüfi kırmızı.

## 9. Tam test [ÖLÇTÜM `ekler/test_runs.txt`]

Gerçek repoda (HEAD `cec77dc`, çalışma ağacında yalnız görev dosyası izlenmeyen; denetim dizini henüz yazılmamıştı): `.venv/bin/pytest -q -p no:cacheprovider` → **594 geçti, 0 kırmızı, 325 s** (INFRA_RAPOR §3'te teslim mesajına bırakılan sayı; beklenen 594 ile aynı). `bash app/scripts/test.sh` → yeşil (npm 222, parity 4, altın dosyalar bayt-eşit, `golden_unchanged: YEŞİL`); cargo bölümü ikinci koşuda tam yakalandı (aynı ekte).

## 10. Bulgular

Tür: **kod düzeltmesi** (test dahil; şartname değişmez, aynı model_id) / **girdi düzeltmesi** (iptal satırıyla) / **karar**. Hiçbir bulgu modelin davranışını değiştirmez.

| # | Önem | Tür | Bulgu | Öneri |
|---|---|---|---|---|
| F1 | **ÖNEMLİ** | kod (test) | D6-5 kapısı kodda bütün MEMBER'ları kapsıyor ama hiçbir test SEALED bir üyenin S2 kaydı eksikken kapının kapalı kalmasını denetlemiyor (mutasyon b: 5 test yeşil). Kapının SEALED kapsamı, tek pencere-içi bültenin bütün kohortun kaydını beklemesi kuralının özüdür. | `test_faz6_oot.py`'ye: SEALED üyenin kayıt dosyası silinince ve commit'lenmemişken `download_gate` `GateError`; `cohort_gate_ok` SEALED üyenin kaydı sonuç commit'inin atası değilken kapalı. S3'ten önce eklenmeli; S2'yi engellemez. |
| F2 | **ÖNEMLİ** | kod (test, isteğe bağlı savunma) | D6-2 "yalnız o üyenin D_1…D_10" koşulunu doğrudan denetleyen test yok: `resolve_member` D_10'da durmayan mutant, testlerde yalnız sentetik piyasa bittiği için kırmızı; uzun piyasada (sonda) D_11+ bültenlerini istemeye devam ediyor (gerçek koşuda: gereksiz bülten indirme ve ham kopyaya D_10 sonrası satır). | Test: uzun sentetik piyasada `fetch` çağrıları ≤ D_10, `raw_copies` seans sayısı = çözümlenen seans sayısı ≤ 10. İsteğe bağlı: `raw_copies`/`extract_open_members`'ta `len(sessions) ≤ N_SESSIONS` savunması. S5'ten önce. |
| F3 | KÜÇÜK | kod (test) | `class_oot`'un "kayıt commit'i sonuç commit'inin atası" terimi tek başına testsiz (mutasyon i2 yeşil); eşdeğer mutant: kohort kapısı (bütün MEMBER kayıtları ata) bu koşulu kapsıyor. | Düşük öncelik; F1 testine tek assert olarak eklenebilir. |
| F4 | KÜÇÜK | kod | `oot_ingest_commit` zip terimi §2'deki "tarihi ∈ [D_1, D_10]" yerine gerçekleşen 10 seans tarihini tarıyor (aradaki durdurma günü zip'i sayılmaz). D6 sonrası zip repoya girmediğinden ve bekçi (mutasyon m) her pencere zip'ini reddettiğinden fiilen boş terim. | Değişiklik gerekmez; istenirse takvim günleri üzerinden tarama. |
| F5 | KÜÇÜK | karar | D8-1 üye başına `exposure_class = SPK_CORPORATE_ACTION_ROW_SEEN` ister; kod sayaç için liste bekliyor (`null`), kohort toplamı 28 sabit. | S6 görevinde EXPOSURE.md §3'ü insan görmeden makineyle okuyup üye kümesini kodla üretme (I14'ün planı); sabit 28'i o kümeden türetme. |
| F6 | KÜÇÜK | karar (S3 görevi) | `s2_gate_problems` `registry/oot` altında hiçbir izlenmeyen dosya istemiyor; S3 `registry/oot/d1_rows/` yazdığından, yarım kalan bir S3 koşusu yeniden başlatılınca kapı kapanır ve `_write_new('xb')` var olan dosyayı reddeder. | S3 tek koşuda ve commit'le bitirilmeli; ya da kapının kirlilik denetiminden `d1_rows`/`post_d1` dışlanmalı (bekçileri ayrı). |
| F7 | KÜÇÜK | bilgi | PDFKit metin katmanı SOKE BIST bildiriminde "386.500.000"ı "386.5" olarak veriyor; girdi değeri doğru (görüntüden). Araç artefaktı; doğrulayıcı pdfplumber kullanmış. | İşlem yok. Metin katmanı karşılaştırmalarında iki araç kullanmak yararlı. |
| F8 | KÜÇÜK | bilgi | TERA `total_demand_filter_status = NOT_SPECIFIED`, belge yalnız grup katları için "filtrelenmemiş" diyor; doğrulayıcı notu bunu açıkça yazıyor (REPORT §10 AZTEK ile aynı yaklaşım). DATA_NOTES §5 gereği alan düzeyinde işaretli; model farkı görmez. | İşlem yok. |
| F9 | KÜÇÜK | bilgi | Marj kural tarihinin bir gün kayması gerçek kohort testinde görünmez (sınır gününde üye yok); birim testi yakalıyor (mutasyon f). | İşlem yok. |

Notlar (bulgu değil): (1) `freeze.main` iptal komutu dağıtımı `_record_stage` ile yeniden yazıldı; POST_D1/listeleme öncesi davranışı aynı. (2) `oot_breakdowns` ALLOC değerleriyle keşif alt kümeleri üretiyor; `SHORT_SELL_BAN_2020_END_NOT_FOUND` (134 üye) alt küme olarak anlamsız, keşif tablosunda kullanılmıyor. (3) Kasa açılınca `oot_pre_h99_sealed`/`_all` ve uygulama paneli S6 ve sonrası; bu görevin kapsamı dışında. (4) `test_no_cohort_window_bulletin_anywhere_in_repo` 2023-12-31'e kadar hiçbir zip'i kabul etmiyor; EXPOSED_ARCHIVE üyelerinin D_2…D_10 bültenleri (≥ 2023-09-22) yalnız eski repo arşivinde, bu repoda yok → tutarlı.

## 11. Kabul kapısı

- **K1** ✓ §1 tablosu D1–D8 ve I1–I27'nin hepsini kapsar; kasa 135/135 ve rejim etiketleri 135/135 bağımsız yeniden üretildi (`borsai` import edilmeden; alt süreç `sys.modules` çıktıları eklerde).
- **K2** ✓ 15 üyenin 296 dolu girdi alanı pinli belgede bulundu (sha 296, yayın 296, değer 285/285 alıntılı alan; 41 yapısal sıfır ve 17 türetilmiş toplam ayrıca sınıflandırıldı; tek uyuşmazlık adayı SOKE araç artefaktı, görüntüyle kapatıldı); 5 belge yeniden indirildi, sha 5/5 eşit.
- **K3** ✓ Kuru S2: 135 × 19 = 2565 hücre; durum sayıları INFRA_RAPOR §6 ile aynı; 5 kayıtta 95/95 hücre bit-eşit.
- **K4** ✓ 16 mutasyon (≥ 13), her birinin çıktısı `ekler/mutasyon_ciktilari.txt`; kırmızı olmayan (b), (i2) ve tesadüfi kırmızı (d) bulgu.
- **K5** ✓ Hiçbir bülten istenmedi (HEAD dahil); ağ yalnız 4 tatil PDF'i + 5 KAP/SPK belgesi; commit yalnız `docs/fable_faz6_audit/` ve görev dosyası; korunan ağaçlar önce/sonra eşit (`ekler/koruma_once.txt`, `ekler/koruma_sonra.txt`). Klondaki kuru koşu kayıtları `/tmp/borsai_faz6_audit/s2_records/`'a taşındı, klon temiz.

## Ekler (`ekler/`)

| Dosya | İçerik |
|---|---|
| `koruma_once.txt`, `koruma_sonra.txt` | HEAD, `git status`, korunan dört ağacın commit sha'ları ve çalışma ağacı dosya sha özetleri |
| `kasa_bagimsiz.py`, `_out.txt` | §2 |
| `rejim_bagimsiz.py`, `_out.txt` | §3 |
| `takvim_c_denetim.py`, `_out.txt` | §4 (PDF'ler indirilip sha karşılaştırıldı; repoya konmadı) |
| `orneklem_denetim.py`, `_out.txt` | §6 (alan alan ayrıntı, 15 üye) |
| `features_karsilastirma.py`, `_out.txt` | §6 `borsai.features` |
| `yeniden_indirme_out.txt` | §6 5 belge |
| `pdftext.swift`, `pdfocr.swift`, `pdfpage.swift` | macOS PDFKit metin, Vision OCR, sayfa görüntüsü araçları (`swiftc -O`) |
| `s2_kuru_kosu_analiz.py`, `_out.txt` | §7 |
| `mutate.sh`, `mutasyon_ciktilari.txt`, `mut_d_probe.py` | §8 |
| `test_runs.txt` | §9 |
| `SHA256SUMS` | eklerin sha256'ları |

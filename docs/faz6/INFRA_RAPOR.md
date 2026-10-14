# BORSAI_FAZ6_OOT_INFRA_20260924 — Rapor

Uygulayıcı: Claude Code (Opus 5.5). Tarih: 2026-09-24 (İstanbul). Ağ kullanılmadı. Hiçbir bülten indirilmedi. Kohort üyelerinin listeleme sonrası hiçbir fiyat, getiri, tavan ya da hacim bilgisine bakılmadı. `verified/EXPOSURE.md` §3'ün ticker listesi okunmadı; dosya bayt olarak kopyalandı. push, tag ve amend yapılmadı.

## 0. Özet

- Üç commit sırayla atıldı: S0b `94ad4e8` → A `1d4913e` → B (bu raporu içeren commit). Her biri bir öncekinin torunu. Yalnız izinli yollara dokunuldu.
- A: eski kohort altyapısı. İçinde kohort dosyası şeması ve doğrulayıcısı, kasa çekilişi, rejim etiketleri, Takvim C, `freeze --oot` yazıcısı, karantina + indirme kapısı + ayıklayıcı, S3 kodu, üçüncü terazi `OOT_PRE_H99`, `class_oot` ve bekçiler var. Gerçek kayıt, sonuç ya da skor üretilmedi.
- B (S1): `registry/oot/cohort_pre_h99.csv` (135 MEMBER + GMTAS `OUT_OF_SCOPE`), doğrulanmış girdiler ve kaynak belgeler, `docs/faz6/dogrulama/`.
  - 1109 dosyanın 1108'i kaynağıyla bayt-eşit.
  - Tek istisna `docs/faz6/dogrulama/coverage.csv`: depo kuralı `.gitattributes` `eol=lf` yüzünden CRLF→LF, dönüşüm kayıtlı (§6).
  - `registry/oot/` altındaki her dosya bayt-eşit.
- Denetim: 135/135 girdi `validate_inputs` ve `inputs_pit_problems(root=repo)` ile temiz. Kohort doğrulayıcısı temiz. Kohort dosyası koddan birebir yeniden üretiliyor (vault ve regime_tags dahil).
- Testler (taban → A → B):
  - pytest: 545 → 590 (+4 atlanan: S1'i bekleyen gerçek kohort testleri) → B commit öncesi 591 + 3 deselect (§3).
  - `bash app/scripts/test.sh` her adımda yeşil: cargo 94, npm 222, parity 4, golden değişmedi.

## 1. Commit'ler

| Sıra | Commit | Konu | `git show --stat` özeti |
|---|---|---|---|
| 1 | `94ad4e8` | BORSAI_FAZ6_S0B | 6 dosya: `docs/specs_faz6/KARARLAR.md`, `docs/prompts/FAZ6_CODEX_INPUTS_B1..B4.md`, `docs/prompts/FAZ6_VERIFY_CODEX_INPUTS.md` |
| 2 | `1d4913e` | BORSAI_FAZ6_A | 13 dosya, +4626 / −9: `borsai/{freeze,market20,registry,scoring}.py`, yeni `borsai/outcomes_oot.py`, `data/raw/pay_calendar_c_20200101_20230921.csv`, `CLAUDE.md` (+2/−2), `docs/SPEC_DEVIATIONS.md` (I bölümü), `docs/faz6/OOT_TANIM_ESLEME.md`, `docs/prompts/FAZ6_OOT_INFRA.md`, `tests/{test_faz6_oot,faz6_support,test_outcome_guard}.py` |
| 3 | B (bu commit) | BORSAI_FAZ6_S1 | 1112 dosya: `registry/oot/cohort_pre_h99.csv`, `registry/oot/{inputs (135), source_docs (135 dizin + MANIFEST), candidate_features (135)}`, `docs/faz6/dogrulama/` (REPORT, EXPOSURE, coverage, verification_log, `_tools/`, `import_sha256.csv`), bu rapor |

Sıra: `git merge-base --is-ancestor 94ad4e8 1d4913e` ve `1d4913e` → B doğru. Commit'ler yalnız görev metnindeki pathspec'lerle atıldı. `git add -A` kullanılmadı.

## 2. Tanım eşlemesi ve I kararları

Tam tablo `docs/faz6/OOT_TANIM_ESLEME.md`'de: şartname §1–§7, §10 ve KARARLAR D1–D8'in her maddesi için dosya:fonksiyon ve test. Yorumlar `docs/SPEC_DEVIATIONS.md` bölüm I'de (I1–I27). Öne çıkanlar:

- **I1:** Skor çıktısı ayrı dosyada: `scores/scores_oot.json` (`borsai.scores_oot/1`). `scores.json` değişmez. `scoring.main()` bu dosyayı yazmaz.
- **I2:** `vault` ve `regime_tags` yalnız kohort dosyasında. Girdiler bayt-eşit alındı.
- **I3:** Kasa değer kümesi {OPEN, SEALED, EXPOSED_ARCHIVE, EXPOSED_CODEX}. Açık küme OPEN ∪ EXPOSED_*.
- **I4:** Kasa çekilişi tek PCG64(20260924) ile yapılır. Yıllar artan sırada, tabaka içi sıra (first_trading_date, ticker). Her tabakada `n // 2` üye SEALED olur (tek sayıda aşağı yuvarlanır).
- **I6/I7:** NOT_APPLICABLE_REGIME:
  - MARGIN (üç `@INF`, her-zaman-tavan ve iki yol modeli).
  - R3 (yalnız `ceiling_path_v0` ve `pb_ceiling_path_v0`).
  - Hücrede modelin kendi durumu ve çıktısı görünür kalır.
- **I8:** ALLOC_REGIME talep toplama başlangıcına göre belirlenir. D_1'e göre okunsaydı 4 üyede farklı çıkardı.
- **I9:** 2020 açığa satış yasağının bitişi bulunamadı. Bu yüzden ayrı bayrak var: `SHORT_SELL_BAN_2020_END_NOT_FOUND`.
- **I10/I13:** `oot_ingest_commit` ham kopyayı ve D_1 satırı dosyasını da sayar. Kohort kapısı bütün MEMBER'ları kapsar (D6-5). Model push kanıtı da aranır. Sonuç commit edilmemişse `OOT_RETRO`.
- **I14:** `n_spk_corporate_action_seen` için üye listesi okunmadı. Sayaç liste verilene kadar `null`, kohort toplamı 28.
- **I15:** Takvim C'nin tabloda olmayan beş kapanışı (Şubat 2023 deprem günleri ve 2023-04-24) yalnız XU100 boşluğuna dayanıyor. S5'te bülten indirilmeden önce THB HEAD probuyla denetlenir.

CLAUDE.md'de yalnız KARARLAR D3'teki iki metin değişti, aynen (`git show 1d4913e -- CLAUDE.md`):

- kural 3'ün ilk cümlesi,
- sıra kuralı satırına eklenen cümle.

## 3. Testler

| Aşama | pytest | `bash app/scripts/test.sh` |
|---|---|---|
| Taban (HEAD `7f1b3d7`) | 545 geçti, 0 kırmızı (295 sn) | yeşil (32 sn): cargo 94, npm 222, parity 4, golden değişmedi |
| A, commit öncesi (temizlik testleri deselect) | 586 geçti, 4 atlandı, 4 deselect | yeşil (aynı sayılar) |
| A, commit sonrası (deselect'siz) | **590 geçti, 4 atlandı**, 0 kırmızı (334 sn) | yeşil (aynı sayılar) |
| B, commit öncesi (görevin üç temizlik testi deselect) | **591 geçti, 0 atlandı, 3 deselect** (342 sn): S1 ile 4 gerçek kohort testi açıldı | yeşil (aynı sayılar) |
| B, commit sonrası (deselect'siz) | teslim mesajında (beklenen 594 geçti) | teslim mesajında |

**Deselect edilen temizlik testleri.** Görevin saydığı üç test:

- `test_faz4_ceiling_path.py::test_new_models_are_retro_with_no_record_and_no_metric`
- `test_faz5_post_d1.py::test_14_models_goldens_and_read_only_paths_unchanged`
- `test_scoring.py::test_faz4_scores_json_existing_blocks_unchanged`

A'nın ilk commit öncesi koşusunda aynı nedenle kırmızı olan dördüncü bir test çıktı: `test_guardrails.py::test_legacy_and_data_have_no_working_tree_changes` (`data/` altında commit'lenmemiş dosya: bu görevin Takvim C dosyası). Başka bir kırmızı yoktu. Bu test de A'nın commit öncesi koşusunda deselect edildi. A commit'lendikten sonraki deselect'siz koşuda dördü de yeşil. B'nin commit öncesi koşusunda yalnız görevdeki üç test deselect edildi (Takvim C artık commit'li).

Yeni testler: `tests/test_faz6_oot.py` (41; 4'ü S1 sonrası gerçek kohortla koşar) ve `tests/test_outcome_guard.py`'ye 8 bekçi. Gerçek kohort testleri S1 öncesinde atlanır. `test_s1_files_present_after_s1_commit` sessiz atlamayı engeller: HEAD geçmişinde S1 commit'i varsa dosyalar olmak zorundadır.

§3 notu: B'nin commit sonrası koşusu bu rapor commit'lendikten sonra yapılır. Sayısı görev teslim mesajındadır. B test eklemez; beklenen 594 = 590 + S1'de açılan 4.

## 4. Kasa dağılımı (yıl × küme; yalnız sayılar)

| Yıl | Üye | OPEN | EXPOSED_ARCHIVE | EXPOSED_CODEX | Açık küme | SEALED |
|---|---|---|---|---|---|---|
| 2020 | 8 | 4 | 0 | 0 | 4 | 4 |
| 2021 | 52 | 26 | 0 | 0 | 26 | 26 |
| 2022 | 38 | 19 | 0 | 1 | 20 | 18 |
| 2023 | 37 | 17 | 4 | 0 | 21 | 16 |
| **Toplam** | **135** | **66** | **4** | **1** | **71** | **64** |

Çekiliş tohumdan deterministik ve testli. Algoritma sentetik girdiyle sha kilidinde. Evren listesi üzerindeki sayılar ve kohort dosyasının koddan yeniden üretimi de testte. Maruz beş kod açık kümede. EXPOSED_ARCHIVE kümesi takvimden bağımsız olarak da hesaplandı (takvim D_10 ≥ 2023-09-22): KARARLAR D2'deki dört kodla aynı.

## 5. regime_tags dağılımı (135 üye; kasa kırılımı verilmez)

| Etiket | Üye |
|---|---|
| `TICK_TABLE_EPOCH=T2015` | 135 (kohortun tamamı) |
| `TICK_TABLE_MISMATCH` | **3** (arz fiyatı ≥ 100 TL; limit yolu 250 TL seviyesini geçiyor) |
| `MARGIN_RULE=PRE_20200313` / `POST_20200313` | 1 / 134 |
| `MARGIN_NOT_10PCT` | **1** |
| `SALE_ON_EXCHANGE` | 49 |
| `PRICE_RANGE_BOOKBUILD` | 9 |
| `SHORT_SELL_BAN` (06/02/2023'ten) | 32 |
| `SHORT_SELL_BAN_2020_END_NOT_FOUND` | 134 |
| `ALLOC_REGIME=PRE_20211111` / `THRESH100_20211111` / `EQUAL_DIST_20230330` | 54 / 54 / 27 |
| `MARKET=YILDIZ` / `ANA` | 84 / 51 |
| `EXPOSED_ARCHIVE` / `EXPOSED_CODEX` | 4 / 1 |

Rejim yüzünden NOT_APPLICABLE_REGIME hücreleri (135 üyede, kuru koşu):

- `ceiling_path_v0` ve `pb_ceiling_path_v0`: 4'er (3 fiyat adımı, 1 marj).
- `base_always_ceiling`, `ceiling_hazard_v0@INF`, `pb_ceiling_v0@INF`, `ceiling_path_v0@INF`: 1'er (marj).

## 6. Model başına girdisi tam arz sayısı

Kaynak: bu koddaki S2 yolunun bellekteki kuru koşusu (`test_real_dry_run_builds_every_member_without_writing` ile aynı; kayıt yazılmadı). "Girdisi tam" = model girdi reddi vermiyor (rejimle uygulanamayan hücre ayrı sayılır).

| Model grubu | Açık küme (71) | Toplam (135) | Ret kodları (toplam) |
|---|---|---|---|
| f3 isteyen 5 model (`v1_5_h99`, `v1_6_h99`, `v1_5_market20_v0`, `ceiling_hazard_v0`, `ceiling_path_v0`) | 68 | 130 | `F3_MISSING` 5 |
| PB modelleri (`pb_v0`, `pb_ceiling_v0`, `pb_ceiling_path_v0`) | 59 | 112 | `PB_IDENTITY` 12, `PB_PRICE_RANGE` 9, `PB_FIELD_MISSING` 2 |
| Kurallar ve `@INF` modelleri (8 kural, 3 `@INF`) | 71 | 135 | yok |

`v1_5_market20_v0`'ın f6'sı 135 üyenin hepsinde üretiliyor. Takvim C ve XU100 kullanılıyor, `ref_date = first_trading_date`. Ret yok.

## 7. İçe aktarım sha denetimi ve repo boyutu

- Kaynak: `~/Desktop/BorsAi_codex/verified/`. `cp -Rp` ile kopyalandı. Kaynak ve hedef dosya kümeleri birebir aynı (eksik ya da fazla dosya yok).
- Liste: `docs/faz6/dogrulama/import_sha256.csv`. 1109 satır; sütunlar path, sha256 (repodaki bayt), bytes, source_sha256, source_bytes, transform. Test her satırı dosyayla karşılaştırır: `test_real_inputs_validate_and_are_byte_equal_imports`.
- Bayt-eşit: 1108 dosya, bunların hepsi `registry/oot/` altında: inputs 135, candidate_features 135, source_docs 523 belge + 135 MANIFEST. Geri kalanlar `docs/faz6/dogrulama/` altında.
- Dönüşüm: yalnız `docs/faz6/dogrulama/coverage.csv`. CRLF→LF, 5266 satır sonu; yalnız CR yoktu. Her LF CRLF yapılınca kaynak baytları geri gelir. Neden: depo `.gitattributes` `* text=auto eol=lf` (bu görevde yazılamaz). Girdi dosyası değil, doğrulama belgesi.
- `_tools/` 2,7 MB ve D8-5'teki 10 MB sınırının altında olduğu için `_tools/logs` dahil alındı.
- Boyut:
  - çalışma ağacı: `registry/oot` 200 MB, `docs/faz6/dogrulama` 6 MB;
  - git nesneleri: sahnelemede +156 MB (sıkıştırılmış loose nesne; `git count-objects` 876 KB → 160 024 KB). PDF'ler ikili olduğundan sıkıştırma kazancı az.
- Yasak kalıp denetimi: içe aktarılan metin dosyalarında bülten adı kalıbı yok. JSON anahtarlarında sonuç alanı adı yok (G1 testi). Bülten zip'i yok.

## 8. Sapmalar, olaylar, kararlar

1. **Takvim C kaynağı.** Tatil tablosu PDF'leri repoda değil. Bu görevde indirilmedi. Şartname görevinin yerel kopyaları kullanıldı: `/private/tmp/borsai_faz6/bist_tatil/`, sha256'ları ekteki dört pinle birebir aynı. Bunlardan elle döküldü; döküm kodda sabit (`market20.HOLIDAY_TABLES_2020_2023`), dosya o sabitlerden üretiliyor. Denetim sonuçları:
   - Hafta içi XU100 boşlukları (42) = kapanışlar.
   - Yıllık seans sayıları XU100 gün sayılarına eşit: 252/249/252/177.
   - Takvim B ile tek fark 5 XU100-boşluk günü.
   - 2023-04-24'ün resmi kaynağı yok; S5'te probla denetlenecek (I15).
2. **Dördüncü temizlik testi** (§3). Aynı neden (bu görevin commit'lenmemiş kendi dosyası), gevşetilmedi. A'dan sonra yeşil.
3. **coverage.csv satır sonu** (§7).
4. **Kasa yuvarlaması** (I4). Tek sayılı tabakalarda (2022: 37 aday, 2023: 33 aday) kasa aşağı yuvarlandı: 18 ve 16. Böylece kasa hiçbir tabakada yarıyı aşmaz.
5. Bu görevde bir modelin davranışı değişmedi. Şu dosyalara dokunulmadı: model JSON'ları, `predict*.py`, `features.py`, `survival.py`, `horizons.py`. Uygulamanın altın MANIFEST pini yeşil kaldı. `scores/`, `docs/SCORES.md`, `app/`, `legacy/`, `experiments/` dokunulmadı.

## 9. Sonraki görevler için notlar

**S2 (toplu kayıt).**
- Komut: `.venv/bin/python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv`, temiz ağaçta, bu görevin commit'lerinden (ve push kanıtlarından) sonra koşulur. Ön koşul denetimi kodda. Bütün kayıtlar önce bellekte kurulur; bir hata olursa hiçbiri yazılmaz.
- 135 × 19 hücre; kuru koşu yaklaşık 4 sn.
- Tek commit (yalnız `registry/oot/records/`), sonra push ve `python -m borsai.push_proof <sha>` (proje sahibi).
- Uyarı: bu commit'ten önce `registry/` temiz olmayacağından `test_faz4_ceiling_path.py::test_new_models_are_retro_with_no_record_and_no_metric` kırmızı olur (bu görevdeki gibi deselect → commit → deselect'siz koşu).

**Bağımsız denetim (S2'den önce önerilir).**
- `class_oot` (I13) ve kohort kapısının D6-5 okuması.
- ALLOC (I8) ve açığa satış (I9) okumaları.
- Takvim C dökümünün PDF'lerle ikinci kez karşılaştırılması.
- Kasa algoritmasının (I4) şartname §9 ile uyumu.
- `n_spk_corporate_action_seen` için üye listesinin makineyle okunma yolu (I14).

**S3/S5 (indirme ve ayıklama).**
- `outcomes_oot.extract_d1_rows` ve `extract_open_members`; karantina varsayılanı `~/Desktop/BorsAi_quarantine` (`BORSAI_QUARANTINE_DIR`).
- İlk iş: kapı (`download_gate`) bütün MEMBER S2 kayıtları commit'li ve push kanıtlı olmadan açılmaz. İkinci iş: beş XU100-boşluk günü için THB HEAD probu; yayımlanmışsa DUR, Takvim C yeni dosya sürümüyle düzeltilir.
- SEALED kodlar bülten açılmadan reddedilir.
- S3 çıktıları: `registry/oot/d1_rows/<T>.json`, `MANIFEST_OOT.csv` pinleri, `freeze --oot-post-d1 <T>`. Commit + push kanıtı, sonra S5.
- S5 çıktıları: `data/outcomes_oot/<T>.csv` + `raw/<T>.json` + `MANIFEST_OOT.csv`. Commit + push kanıtı.
- Bekçiler (G1, G3, G5′, SEALED yokluğu, pencere zip yasağı) gerçek repoda o anda devreye girer.
- Canlı temizlik testleri `data/` ve `registry/` temizliği ister (bkz. §3).

**S6 (skorlama).**
- `scoring.build_oot_scores` → `write_oot_scores`. `main()`'e bağlanması ve `docs/SCORES.md` bölümü o görevde.
- Kasa açılınca `oot_pre_h99_sealed` / `_all` ayrı anahtar olur (`outcomes_oot.open_vault` iskelet, çağrılmadı).
- Uygulama üçüncü paneli (şartname §3) ayrı görev.

## 10. Kabul kapısı

- **K1** ✓ S0b `94ad4e8` → A `1d4913e` → B; yalnız izinli yollar; push yok.
- **K2** ✓ Aşağıdakiler yok ya da boş: `registry/oot/records`, `d1_rows`, `post_d1`, `data/outcomes_oot`, `data/raw/bist/MANIFEST_OOT.csv`. Kohort penceresi tarihli zip yok (bekçi `test_no_cohort_window_bulletin_anywhere_in_repo`).
- **K3** ✓ Kasa çekilişi deterministik ve testli; maruz 5 kod açık kümede (EXPOSED_*).
- **K4** ✓ 135/135 girdi doğrulayıcıdan ve belge sha denetiminden geçiyor. `registry/oot/` içe aktarımı bayt-eşit. Tek dönüşüm `docs/` altındaki bir doğrulama belgesinde, kayıtlı.
- **K5** ✓ CLAUDE.md'de yalnız D3 metinleri. Tam pytest ve test.sh A sonrası yeşil; B sayıları teslim mesajında.

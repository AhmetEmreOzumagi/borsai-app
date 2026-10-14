# BORSAI_FAZ6_S3_S5_EXTRACT_20260925 — eski kohort S3: D_1 satırları ve POST_D1 kayıtları (Bölüm A), EK1 (Takvim C kanıtı) ve S5: D_1…D_10 satırları (Bölüm B)

Uygulayıcı: Claude Code (Opus 5.5). Tarih: 2026-09-25 (İstanbul; ağ işleri 13:37–14:57 arası).

Ağ yalnız `www.borsaistanbul.com` THB/THM bülten URL'lerine gitti: HEAD probları ve zip indirmesi. İndirilen zip'ler yalnız karantinaya yazıldı (`~/Desktop/BorsAi_quarantine`, repo dışında).

Bu raporda yalnız sayılar var. Hiçbir üyenin fiyatı, getirisi, limiti ya da satırı yazılmadı; hangi kodun kasada olduğu yazılmadı. `docs/faz6/dogrulama/EXPOSURE.md` §3 okunmadı. push, tag ve amend yapılmadı. Bölüm A yazılırken Bölüm B (S5) başlamamıştı; Bölüm B, proje sahibinin push kanıtından sonra koşuldu ve raporun sonundadır.

## 1. Commit'ler

| Sıra | Commit | İçerik |
|---|---|---|
| C | `1c0803e` | `BORSAI_FAZ6_S3_CODE`: T1, T2, T3 ve testleri, SPEC_DEVIATIONS I28–I33, `docs/faz6/ekler/s3_s5_mutasyon.txt`, görev dosyası |
| E1 | `5975cd8` | `BORSAI_FAZ6_CAL_C_EVIDENCE_CODE`: EK1 kodu (K2, K3, K4, K5) ve testleri, SPEC_DEVIATIONS I34–I38, `docs/faz6/ekler/s3_s5_mutasyon_ek1.txt`, EK1 dosyası |
| E2 | `ae42f85` | `BORSAI_FAZ6_CAL_C_EVIDENCE`: yalnız `data/raw/pay_calendar_c_bulletin_evidence_20200101_20230921.csv` (42 satır) |
| S3a | `9e1e992` | `BORSAI_FAZ6_S3`: yalnız `registry/oot/d1_rows/` (71 dosya) ve `data/raw/bist/MANIFEST_OOT.csv`, toplam 72 dosya |
| S3b | `7ade6a8` | `BORSAI_FAZ6_S3_POST_D1`: yalnız `registry/oot/post_d1/` (71 dosya) |
| RA | bu raporu ekleyen commit | `BORSAI_FAZ6_S3_REPORT`: bu rapor ve `docs/faz6/ekler/s3_s5_*` ekleri. Bir commit kendi hash'ini içeremez; `git log -1 --format=%H -- docs/faz6/S3_S5_RAPOR.md` ile okunur. |

Sıra: C → (prob DUR) → E1 → E2 → prob → S3a → S3b → RA.

Taban: HEAD `f57ce50`; çalışma ağacında yalnız görev dosyası izlenmiyordu. `s2_gate_problems() == []`; karantina dizini yoktu.

## 2. Kod (commit C): T1, T2, T3

Hiçbir model, şartname, girdi ya da S2 kaydı değişmedi. Ayıklama tanımları da değişmedi. Kod değişikliği yalnız `borsai/outcomes_oot.py` içinde.

| Karar | Uygulama | Test (`tests/test_faz6_oot.py`) |
|---|---|---|
| T1 (F6 kalıntısı) | `d1_row_action`: dosya yoksa CREATED, aynı baytlarsa UNCHANGED, farklıysa DUR (hiçbir şey yazılmadan). `extract_d1_rows` written / unchanged / D_1 ≠ ilk işlem günü listelerini döner. | `test_extract_d1_rows_is_rerun_safe_unchanged_or_stop`. **Önce kırmızı**: kod HEAD halindeyken `FileExistsError` verdi. |
| T2 (CLI) | `python -m borsai.outcomes_oot {probe\|calendar-evidence\|s3\|s3-post-d1\|s5}`; `--pace` (0,5 s, yalnız gerçek indirmeden önce), `--quarantine`. HEAD yalnız 200/404 kabul eder; başka kod DUR. Çıktı yalnız sayı (JSON); hata `durum: DUR`, çıkış 2. | `test_cli_commands_print_numbers_only_pace_downloads_and_rerun`, `test_cli_stops_on_closed_gate_head_codes_published_gap_day_and_unpublished_session` |
| T3 (S5 kapısı) | `s3_gate_problems`: her açık üye için d1_rows ve skorlamanın seçeceği POST_D1 kaydı HEAD'de, değişmemiş, push kanıtlı olmalı. d1_rows bekçisi HEAD'deki MANIFEST_OOT'a karşı koşar; kayıt dosyanın kanonik sha'sını taşımalı. `s5` önce kapıyı çağırır. | `test_s3_gate_requires_committed_unchanged_pushed_d1_rows_and_post_d1`, `test_cli_s5_calls_s3_gate_before_any_extraction` |

Mutasyon (`docs/faz6/ekler/s3_s5_mutasyon.txt`): 10 mutasyonun 10'u kırmızı, mutasyonsuz koşu 5/5 yeşil.
- (p) kanıt denetimi kaldırılınca T3 testi kırmızı.
- (q) POST_D1 denetimi kaldırılınca T3 testi kırmızı.
- (s) `s5` kapıyı çağırmayınca T3 ve CLI testleri kırmızı.
- Diğerleri: bayt denetimi, eski 'xb' davranışı, yalnız kayıt kanıtı, sha bağı, kirlilik, tempo ve karantina önbelleği.

## 3. İlk prob: DUR (T6)

2026-09-25 13:37'de (İstanbul) prob `CalendarConflict` ile durdu: Takvim C'nin 5 XU100-boşluk kapanışının beşinde de THB zip'i yayımlanmıştı. Kural gereği hiçbir zip indirilmedi.

Yumuşak-404 olmadığını yalnız HEAD ile ayrıca doğruladım:
- hafta sonu ve gelecek tarih: 404, `text/html`, 8558 B;
- bilinen yayımlanmış bir 2026 bülteni: 200, `application/zip`;
- komşu olağan seanslar: 95–107 KB.

| Gün | HEAD | Content-Type | Content-Length |
|---|---|---|---|
| 2023-02-09 | 200 | application/zip | 30615 |
| 2023-02-10 | 200 | application/zip | 30614 |
| 2023-02-13 | 200 | application/zip | 30612 |
| 2023-02-14 | 200 | application/zip | 30611 |
| 2023-04-24 | 200 | application/zip | 107104 |

Oturum burada durdu ve proje sahibine bildirildi. Orkestratör EK1'i yazdı.

## 4. EK1: Takvim C kapanışları için bülten kanıtı

**Kök neden.** Prob "bülten yayımlanmışsa o gün seanstır" varsayıyordu. Doğru ölçüt, o gün işlem yapılıp yapılmadığıdır. Takvim C dosyası ve `market20` sabitleri (f6'nın takvimi, S2 kayıtları onunla dondu) değişmedi (K1). Sonuç takvimi ayrıldı: Takvim C ∪ `TRADING_SESSION` günleri (K2; SPEC_DEVIATIONS I34–I38).

**E1 (`5975cd8`):**
- `calendar-evidence` komutu (önce kapı, sonra 42 kapanışın her biri için HEAD; 200 günlerinin zip'i karantinaya).
- K4 karar kuralı tek fonksiyonda (`evidence_decision`).
- Sonuç takvimi (`load_calendar_oot`) ve her kapanışı kanıta karşı denetleyen prob (`check_calendar_closures`; `probe`, `s3` ve `s5` aynı fonksiyonu çağırır).
- 4 yeni test; 2 test yeni davranışa uyarlandı.
- Mutasyon (`docs/faz6/ekler/s3_s5_mutasyon_ek1.txt`): 13 mutasyonun 13'ü kırmızı, mutasyonsuz 6/6 yeşil. Görevin istediği üçü de dahil: eşik 50 → 1 (e01), `TRADING_SESSION` takvime eklenmez (e05), prob kanıtı atlar (e06).

**E2 (`ae42f85`), 42 satır:**

| Kaynak | NOT_PUBLISHED | PUBLISHED_NO_TRADING | TRADING_SESSION | Toplam |
|---|---|---|---|---|
| HOLIDAY_TABLE | 37 | 0 | 0 | 37 |
| XU100_GAP | 0 | 4 | 1 | 5 |
| **Toplam** | **37** | **4** | **1** | **42** |

DUR durumu yok (1–49 işlemli satır yok; HEAD yalnız 200/404). Beş XU100-boşluk günü (piyasa toplamları, üye satırı yok):

| Gün | Karar | Pay satırı | İşlemli pay satırı |
|---|---|---|---|
| 2023-02-09 | PUBLISHED_NO_TRADING | 495 | 0 |
| 2023-02-10 | PUBLISHED_NO_TRADING | 495 | 0 |
| 2023-02-13 | PUBLISHED_NO_TRADING | 495 | 0 |
| 2023-02-14 | PUBLISHED_NO_TRADING | 495 | 0 |
| 2023-04-24 | TRADING_SESSION | 501 | 496 |

- **`TRADING_SESSION` günleri:** yalnız **2023-04-24**; sonuç takviminde artık seans. Şubat günleri kapalı kalır.
- **K6 (yalnız takvimden ve S2 kayıtlarındaki f6 pencere tarihlerinden; kod yok):**

| Gün | f6 penceresini kesen (açık / toplam) | D_1…D_10 takvim penceresini kesen (açık / toplam) |
|---|---|---|
| 2023-04-24 (TRADING_SESSION) | 1 / 5 | 2 / 3 |
| Şubat günleri (PUBLISHED_NO_TRADING; takvim değişmedi) | 1 / 1 | 0 / 1 |

- Hiçbir üyenin ilk işlem günü bu 5 güne düşmüyor. Sayılar orkestratörün ölçümüyle aynı.
- Kayıt iptali ve yeniden kayıt yok. 2023-04-24'ü kesen 5 üyede f6, 20 XU100 gözlemi üzerinden hesaplanmış olur (I38); S6'da bilgi olarak sayılır.
- Kohortun rejim etiketleri yeni sonuç takvimiyle birebir yeniden üretiliyor (`test_real_cohort_validates_and_reproduces_from_code` yeşil).

**İkinci prob (E2 sonrası):** `mode = EVIDENCE`, 42 kapanış denetlendi, HEAD 200: 5 / 404: 37, kanıtla tam tutarlı. Sonuç: yeşil.

## 5. S3a (`9e1e992`)

Komut: `.venv/bin/python -m borsai.outcomes_oot s3`. Sonuç: yazılan 71, aynı 0, toplam 71; ağdan indirilen 136 zip; 42 HEAD (200: 5, 404: 37).

| Denetim | Beklenen | Ölçülen |
|---|---|---|
| `registry/oot/d1_rows/*.json` | 71 dosya, hepsi açık küme üyesi; SEALED 0 | 71; 71 açık küme üyesi; SEALED 0 |
| her dosya | `d1_rows_problems == []`, `exposure_class = MACHINE_SEQUENCED`, `session_h = 1` | 71/71, 71/71, 71/71 |
| `data/raw/bist/MANIFEST_OOT.csv` | satır = 2 × farklı D_1 tarihi; her sha karantinayla eşit | 136 satır = 2 × 68; anahtarlar tam D_1 × {thb, thm}; sha 136/136 eşit |
| D_1 | her üyede D_1 ≥ first_trading_date; D_1 ≠ first_trading_date sayısı | 71/71; **D_1 ≠ first_trading_date: 0** |
| T5 (d1_rows) | 71 × 14 alan zip satırıyla eşit; 0 fark | 994 alan eşit; 0 fark (§7) |
| sızıntı | `test_sealed_codes_absent_from_every_extracted_file` yeşil | yeşil; ayrıca `test_oot_d1_rows_and_post_d1_records_carry_only_d1`, `test_no_cohort_window_bulletin_anywhere_in_repo`, `test_oot_outcomes_follow_every_s2_record_and_its_push_proof`, `test_oot_registry_carries_no_outcome_fields`, `test_cohort_codes_appear_in_data_only_as_outcomes` yeşil |

**Karantina:**
- 141 zip: S3'ün 136 zip'i ve kanıtın 5 zip'i. Her zip'in karantina manifestinde satırı var ve sha'sı eşit.
- Manifest satırı olmayan (yarıda kesilmiş) zip yok; `_orphans/` kullanılmadı.
- Kohort penceresinden repoda hiçbir zip ya da iç CSV yok.

## 6. S3b (`7ade6a8`)

Komut: `.venv/bin/python -m borsai.outcomes_oot s3-post-d1`, HEAD = S3a iken, `borsai/` temizken. Sonuç: 71 yazıldı, 0 zaten var.

| Denetim | Ölçülen |
|---|---|
| `registry/oot/post_d1/<T>/` | 71 dizin, hepsi açık küme üyesi, her birinde tek kayıt, dosya adı içerik adresli |
| şema, sınıf, ölçek | 71/71 `borsai.oot_post_d1_record/1`, `MACHINE_SEQUENCED`, `record_stage = OOT_POST_D1`, `scale = OOT_PRE_H99` |
| `code` | 71/71 `git_head = 9e1e992` (S3a), `borsai_dirty = false` |
| `d1_rows.sha256` | 71/71 dosyanın kanonik sha'sına eşit |
| `base_record` | 71/71 o üyenin S2 kaydı (yol + sha256) |
| bekçi | 71/71 `post_d1_record_problems == []` (MANIFEST_OOT'a karşı) |
| f3 REFUSED kümesi | 3; S2 kaydında `ceiling_hazard_v0` hücresi REFUSED olan açık üyelerle **birebir aynı** (3) |

**Durum sayıları** (`post_d1_hazard_v0`, 71 hücre; T4: hiçbiri atlanmadı):

| PREDICTED | REFUSED | NOT_APPLICABLE | Toplam |
|---|---|---|---|
| 59 | 3 (`F3_MISSING`) | 9 (`D1_NOT_CEILING`) | 71 |

## 7. T5: bağımsız ham alan denetimi

Betik `docs/faz6/ekler/s3_s5_bagimsiz.py`, çıktısı `docs/faz6/ekler/s3_s5_bagimsiz_s3.txt`.
- `borsai` import edilmedi (`python -I`, `cwd=/`; çıktıda `borsai_import_edildi: false`).
- Karantina zip'leri doğrudan açıldı ve yalnız açık küme kodlarının satırlarına bakıldı.
- Sonuç takvimi K7'ye göre kuruldu: Takvim C ∪ kanıttaki `TRADING_SESSION` günleri.

| Denetim | Sayı |
|---|---|
| d1_rows dosyası / açık küme | 71 / 71 |
| karşılaştırılan ham alan (`fields_raw` ↔ D_1 zip satırı) | 994 = 71 × 14 |
| sha: d1_rows ↔ karantina zip ↔ MANIFEST_OOT ↔ karantina manifesti; url, bayt, iç ad | hepsi eşit |
| `ceiling_close_D1` (Decimal kapanış == üst limit), `lock_consistency`, `halt_flag` | hepsi eşit |
| D_1 kuralı ([ilk işlem günü, D_1) seanslarında işlem yok; D_1'de işlem var) | 71/71 |
| MANIFEST_OOT = 2 × farklı D_1 (68) | 136 |
| kanıt dosyası: kapsam 42 = Takvim C'nin hafta içi kapanışları; 200 günlerinde zip sha/bayt; sayıların yeniden sayımı; K4 kararı | hepsi eşit (37 / 4 / 1) |
| **denetim geçen / fark** | **2543 / 0** (33 denetim türü, 136 zip okundu) |

Betik değer içermez; bülten dosya adını tarihten kendisi kurar (metinde ad kalıbı yok). Sentetik depoda iki kez denendi: temiz veride 0 fark; kasıtlı bozulmada (bir kapanış, bir `aof` alanı) fark yakaladı.

## 8. Test sayıları (`docs/faz6/ekler/s3_s5_test_runs.txt`)

| Koşu | pytest | test.sh |
|---|---|---|
| Taban (`f57ce50`) | 598 geçti | yeşil (cargo 94, npm 222, parity 4, golden YEŞİL); `gen_golden --check` 25/0 |
| C öncesi | 603 geçti | yeşil |
| E1 öncesi | 607 geçti | yeşil |
| E2 öncesi (3 temizlik bekçisi deselect) | 604 geçti, 3 deselect | — |
| E2 sonrası | 607 geçti | — |
| S3a öncesi (4 temizlik bekçisi deselect) | 603 geçti, 4 deselect | — |
| S3a sonrası | 607 geçti | — |
| S3b öncesi (3 temizlik bekçisi deselect) | 604 geçti, 3 deselect | — |
| S3b sonrası | 607 geçti | yeşil (cargo 94, npm 222, parity 4, golden YEŞİL) |

Deselect edilen testler yalnız temizlik bekçileriydi; her birinin kırmızısı yalnız o adımın commit'lenmemiş yeni dosyasından geliyordu (ek dosyada adları var). Eski kohort bekçileri (`test_oot_*`, `test_sealed_*`, `test_no_cohort_window_*`, `test_cohort_*`) hiçbir koşuda deselect edilmedi, gevşetilmedi.

## 9. Kapı durumu (ölçüm, S3b commit'inden sonra)

- `s2_gate_problems()`: `[]`.
- `s3_gate_problems()`: 142 sorun (71 d1_rows + 71 POST_D1 kaydı), hepsi "push kanıtı yok". Başka sorun yok (commit'siz, değişmiş, bekçi, sha bağı, açık küme dışı ad).

S5 kapısı, proje sahibi push edip kanıtı ekleyene kadar kapalı.

## 10. Proje sahibi için: push ve push kanıtı

E1 ve E2 (ve C) aynı push'la gider. Kanıt S3a ve S3b içindir.

```
cd ~/Desktop/BorsAi
git push origin main
.venv/bin/python -m borsai.push_proof 9e1e992 7ade6a8
git add registry/push_proofs
git commit -m "BORSAI_PUSH_PROOFS: Faz 6 S3 d1_rows (9e1e992) and post_d1 records (7ade6a8)" -- registry/push_proofs
git push origin main
git --no-pager log --oneline -3 origin/main
```

- S3b'nin kanıtının `created_at`'i S5 sonuç commit'inin kanıtından önce olmalı. `class_oot` bu sırayı ister; aksi halde post_d1 OOT_RETRO sayılır.
- Kanıtlar `registry/push_proofs/` altındadır. `registry/oot` ve S3 çıktı dizinlerinin kirlilik denetimlerini etkilemez.

## 11. Bölüm B (S5) için notlar

- **Adım 0:** `s2_gate_problems(), s3_gate_problems()` → `[] []` olmalı; bu, S3 kanıtlarının repoda olduğunu gösterir. `s5` komutu bu kapıyı kendisi de çağırır.
- **Takvim ve prob:**
  - Sonuç takvimi 2023-04-24'ü seans sayıyor. Penceresi o günü kesen 2 açık üyenin D_h sayımı bu güne göre yapılır; T5 betiği aynı takvimi kullanır.
  - Her `s5` koşusu önce 42 HEAD probu atar (kip `EVIDENCE`).
- **Karantina ve tekrar:**
  - Karantina 141 zip ile önbellekte; S5 yalnız eksikleri indirir.
  - Yarım kalan S5 yeniden koşulabilir: MANIFEST_OOT'a eklenen commit'siz satırlar S5 kapısını kapatmaz; pinler HEAD'deki sürümden denetlenir.
- **T5 (S5 kipi):** `python -I docs/faz6/ekler/s3_s5_bagimsiz.py --stage s5 --root ~/Desktop/BorsAi --quarantine ~/Desktop/BorsAi_quarantine --s3a 9e1e992`. S3a'daki MANIFEST_OOT satırlarının yeni dosyanın başında bayt olarak durduğunu bu `--s3a` ile denetler. Bu kip sentetik depoda iki kez denendi: temiz veride 0 fark, bozulmada fark yakaladı.
- **Temizlik yolu:** S5 `data/` yazdığından büyük olasılıkla `test_guardrails::test_legacy_and_data_have_no_working_tree_changes`, `test_faz5_post_d1::test_14…` ve `test_scoring::test_faz4_scores_json…` kırmızı olur (bu görevde E2 adımında olduğu gibi).
- **Tam pytest süresi:** bu makinede 7–10 dakika (607 test); Bash'in 10 dakikalık sınırına yakın, arka planda koşulmalı.

## 12. Kabul kapısı

- **KA1** ✓ T1 önce kırmızıydı (`FileExistsError`). T2 ve T3 testli; T3 mutasyonla kırmızı gösterildi (10/10). EK1'in her yeni kuralı mutasyonla kırmızı gösterildi (13/13). C sonrası (ve E1 sonrası) tam pytest ve test.sh yeşil.
- **KA2** ✓ İlk prob kuralı doğru işledi (DUR). EK1'den sonra prob yeşil: 42 kapanış kanıtla tutarlı. 2023-04-24 `TRADING_SESSION`; 4 Şubat günü `PUBLISHED_NO_TRADING` (kapalı kalır); 37 tatil günü `NOT_PUBLISHED`.
- **KA3** ✓ S3a: 71 d1_rows, MANIFEST_OOT pinleri (136), T5 0 fark. S3b: 71 POST_D1 kaydı; f3 REFUSED kümesi birebir (3). Sıra C → E1 → E2 → S3a → S3b → RA. push yok.

---

# Bölüm B (S5): D_1…D_10 satırları

Tarih: 2026-09-25 (İstanbul; ağ işi 16:14–16:24). Bölüm A'daki hijyen kuralları aynen geçerlidir: raporda yalnız sayı var, SEALED kod yok, EXPOSURE §3 okunmadı. push, tag ve amend yapılmadı. `scores/` yazılmadı; `scoring.main()` ve `build_oot_scores` çalıştırılmadı.

## B1. Commit'ler

| Sıra | Commit | İçerik |
|---|---|---|
| Kanıt (proje sahibi) | `3c82378` | S3a ve S3b push kanıtları: `9e1e992` 2026-09-25T13:05:56Z, `7ade6a8` 2026-09-25T13:05:58Z |
| S5 | `77b54f7` | `BORSAI_FAZ6_S5`: yalnız `data/outcomes_oot/` (71 CSV + 71 ham kopya) ve `data/raw/bist/MANIFEST_OOT.csv`; toplam 143 dosya |
| RB | bu bölümü ekleyen commit | `BORSAI_FAZ6_S5_REPORT`: bu rapor ve `docs/faz6/ekler/s3_s5_*` ekleri |

## B2. Adım 0 (taban)

- Ağaç temizdi. HEAD = `origin/main` = `3c82378`; RA'nın (`6c979b4`) ve S3 kanıt commit'inin torunu.
- `s2_gate_problems(), s3_gate_problems()` → `[] []`.
- Tam pytest **607 geçti**. `test.sh` yeşil: cargo 94, npm 222, parity 4, golden YEŞİL. `gen_golden --check`: 25 dosya, fark yok.
- Karantinada 141 zip vardı.

## B3. S5

Komut: `.venv/bin/python -m borsai.outcomes_oot s5`. Sırayla: S5 kapısı (boş), indirme kapısı, 42 HEAD'lik takvim probu (kip `EVIDENCE`; 200: 5, 404: 37).

Sonuç: 71 üye ayıklandı, hepsi `CREATED`; `n_sessions` 71 üyede 10; ağdan 777 zip indirildi; `sealed_not_opened` = **64**.

| Denetim | Beklenen | Ölçülen |
|---|---|---|
| `data/outcomes_oot/<T>.csv` | 71 dosya; her biri 10 satır (h = 1…10); `outcome_basis` hep `MACHINE_EXTRACTED`; `PENDING` 0 | 71 dosya, hepsi açık küme üyesi (SEALED 0); 71/71 on satır; 71/71 `MACHINE_EXTRACTED`; `PENDING` 0 |
| `data/outcomes_oot/raw/<T>.json` | 71; D_10'dan sonra okunmuş seans yok; okunan − çözümlenen seans farkı olan üye sayısı | 71 (CSV kümesiyle aynı); 71/71 D_10'dan sonra okuma yok; **fark olan üye: 1** (penceresinde işlemsiz bir gün var, `shifted_by_suspension` > 0) |
| D_1 tutarlılığı | 71/71 CSV'nin h = 1 seansı = d1_rows D_1; D_1 thb/thm sha'ları d1_rows ve MANIFEST_OOT ile eşit | 71/71; 71/71 |
| `MANIFEST_OOT.csv` | S3a satırları bayt olarak aynı ve başta; toplam = 2 × okunan farklı seans; her sha karantinayla eşit | S3a'nın 136 satırı bayt-eşit önek; toplam **914** = 2 × **457**, anahtarlar tam okunan seans × {thb, thm}; sha 914/914 eşit; her satırın bülten sha'sı MANIFEST_OOT'ta (71/71 dosya) |
| durumlar | 10 seansı olmayan üye; `TARGET_UNAVAILABLE` ve `NA_LIMIT` satır sayıları | 10 seansı olmayan üye **0**; 710 satırın hepsi `OK`; `TARGET_UNAVAILABLE` **0**, `NA_LIMIT` **0** |
| T5 (S5) | bütün satırlarda ham alanlar zip'le eşit; `ceiling_close` ve `R_h` yeniden hesapla eşit; 0 fark | 2840 ham alan (710 × 4) ve 284 R_h (71 × 4) eşit; 10996 denetimde **0 fark** (§B4) |
| sızıntı | SEALED kod hiçbir yeni dosyada yok; `sealed_not_opened` = 64 | 143 yeni dosyanın 0'ında SEALED kod (ad ya da içerik); `sealed_not_opened` = 64; `test_sealed_codes_absent_from_every_extracted_file` ve bütün eski kohort bekçileri yeşil (82/82) |

Takvim (EK1):
- D_1…D_10'u 2023-04-24'ü içeren açık üye **2**; bu, yalnız takvimden yapılan ölçümle (§4) aynı.
- Şubat kapanış günlerinden birini içeren pencere 0.

Karantina:
- 918 zip = MANIFEST_OOT'un 914 zip'i + kanıtın 4 Şubat THB'si; 2023-04-24 THB'si hem kanıtta hem S5'te.
- Her zip'in karantina manifestinde satırı var ve sha'sı eşit; manifest satırı olmayan zip yok, `_orphans/` kullanılmadı.
- Kohort penceresinden repoda hiçbir zip ya da iç CSV yok.

## B4. T5 (S5 kipi)

Komut (`cwd=/`, `python -I`): `docs/faz6/ekler/s3_s5_bagimsiz.py --stage s5 --root ~/Desktop/BorsAi --quarantine ~/Desktop/BorsAi_quarantine --s3a 9e1e992`. Çıktı `docs/faz6/ekler/s3_s5_bagimsiz_s5.txt`; betik Bölüm A'da commit'lenen dosyanın kendisi (değişmedi).

| Denetim | Sayı |
|---|---|
| sonuç dosyası / ham kopya / satır | 71 / 71 / 710 (hepsi `OK`) |
| `close_raw`, `trade_count_raw`, `upper_limit_raw`, `reference_raw` ↔ ilgili seansın zip satırı | 2840 eşit |
| `halt_flag`, `ceiling_close` (Decimal kapanış == üst limit), `status` yeniden hesap | hepsi eşit |
| `R_h` ↔ kapanış / arz fiyatı − 1 (\|Δ\| ≤ 1e-12), `Y_h` = 1[R > 0], h ∈ {1, 3, 5, 10} | 284 eşit |
| `thb_sha256` / `thm_sha256` ↔ zip ↔ MANIFEST_OOT ↔ karantina manifesti | hepsi eşit |
| ham kopya satırları ↔ zip; D_h çözümü (ilk görünüş, işlem gören ilk 10 seans) yeniden kuruldu; okunan seanslar ardışık sonuç takvimi seansları | 71/71 |
| MANIFEST_OOT: S3a öneki; 914 = 2 × 457 | eşit |
| kanıt dosyası (42 satır; 37 / 4 / 1) | eşit |
| **denetim geçen / fark** | **10996 / 0** (36 denetim türü, 914 zip okundu); `borsai_import_edildi: false` |

## B5. Test sayıları (`docs/faz6/ekler/s3_s5_test_runs.txt`)

| Koşu | pytest | test.sh |
|---|---|---|
| Taban B (`3c82378`) | 607 geçti | yeşil (cargo 94, npm 222, parity 4, golden YEŞİL) |
| S5 öncesi: 3 temizlik bekçisi kırmızı, yalnız commit'lenmemiş `data/` yüzünden (`test_guardrails::test_legacy_and_data…`, `test_faz5_post_d1::test_14…`, `test_scoring::test_faz4_scores_json…`); üçü deselect | 604 geçti, 3 deselect | — |
| S5 sonrası, deselect'siz | 607 geçti | yeşil (cargo 94, npm 222, parity 4, golden YEŞİL) |

## B6. S6 (skorlama) için notlar

- **Sonuç girişi (I10).**
  - Listeleme öncesi 19 model için `oot_ingest_commit` = `min(d1_rows, outcomes_oot, raw)` = **S3a `9e1e992`**, çünkü D_1 satırı dosyası bu modeller için sonuçtur.
  - Kayıt sırası: S2 kanıtı (2026-09-24T22:39:24Z) < S3a kanıtı (2026-09-25T13:05:56Z).
  - `post_d1_hazard_v0` için giriş, D_1 sonrası sonuçtur (d1_rows hariç): **S5 `77b54f7`**. Kayıt kanıtı (S3b 13:05:58Z) S5'in kanıtından önce olmalı; aşağıdaki push bloğu bunu sağlar.
- **Payda.**
  - Açık küme 71; 710 sonuç satırının hepsi `OK`, `TARGET_UNAVAILABLE` 0.
  - POST_D1: 59 PREDICTED, 3 REFUSED (`F3_MISSING`), 9 NOT_APPLICABLE (`D1_NOT_CEILING`).
- **Takvim.** `OotContext.calendar()` artık sonuç takvimini (2023-04-24 seans) kullanır. 2023-04-24'ü kesen f6 penceresi 5 üyede (açık 1) var; bu f6, 20 XU100 gözlemi üzerinden hesaplanmış kabul edilir ve bilgi olarak sayılır (I38).
- **Açık kalanlar.** F5 (üye başına `SPK_CORPORATE_ACTION_ROW_SEEN`, EXPOSURE §3 makineyle okunarak) ve `scores/scores_oot.json` → `main()` bağlantısı S6 görevinde. Kasa açılışı (`open_vault`) ayrı görev.
- **Karantina.** Kasa açılışında MANIFEST_OOT'taki 914 zip yeniden indirilip pinlere karşı denetlenecek. Karantina (918 zip) şimdilik silinmemeli; önbellek olarak yeniden indirmeyi azaltır.

## B7. Proje sahibi için: push ve push kanıtı

```
cd ~/Desktop/BorsAi
git push origin main
.venv/bin/python -m borsai.push_proof 77b54f7
git add registry/push_proofs
git commit -m "BORSAI_PUSH_PROOFS: Faz 6 S5 outcome rows (77b54f7)" -- registry/push_proofs
git push origin main
git --no-pager log --oneline -3 origin/main
```

S5'in kanıtı `created_at`, S3b'nin kanıtından (13:05:58Z) sonra olacak; bu sıra, post_d1'in eski kohort testi için gereklidir.

## B8. Kabul kapısı

- **KB1** ✓ S5'ten önce `s3_gate_problems() == []` (S3 kanıtları `3c82378`'de). `s5` komutu kapıyı kendisi de çağırdı.
- **KB2** ✓ S5 tablosu birebir tuttu (71 dosya × 10 satır, `MACHINE_EXTRACTED`, `PENDING` 0; D_1 71/71; MANIFEST_OOT önek + 914 = 2 × 457; 10 seansı olmayan üye 0; `TARGET_UNAVAILABLE` 0, `NA_LIMIT` 0). T5 0 fark; SEALED 0; `sealed_not_opened` 64.
- **KB3** ✓ S5 commit'i yalnız izinli yollar (143 dosya). Deselect'siz tam pytest ve test.sh yeşil. push yok.

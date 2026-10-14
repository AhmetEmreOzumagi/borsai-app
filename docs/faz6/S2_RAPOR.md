# BORSAI_FAZ6_S2_RECORDS_20260925 — Fable bulgularının kapatılması ve eski kohort S2 tahmin kayıtları

Uygulayıcı: Claude Code (Opus 5.5). Tarih: 2026-09-25 (İstanbul; sistem saati kayıt anında 2026-09-24T22:13Z). Ağ kullanılmadı. Hiçbir bülten istenmedi. Kohort üyelerinin listeleme sonrası hiçbir verisine bakılmadı. `docs/faz6/dogrulama/EXPOSURE.md` §3 okunmadı. Hangi kodun kasada olduğu bu raporda yazılmaz. push, tag ve amend yapılmadı.

## 1. Commit'ler

| Sıra | Commit | İçerik |
|---|---|---|
| C | `40db62c` | `BORSAI_FAZ6_AUDIT_FIX`: F1, F2, F3 testleri; F2 savunması; F6 kapı düzeltmesi; mutasyon çıktısı `docs/faz6/ekler/s2_bulgu_kapatma.txt`; görev dosyası |
| S2 | `1dcceff` | `BORSAI_FAZ6_S2`: yalnız `registry/oot/records/` (135 dosya, başka yol yok) |
| R | bu raporu ekleyen commit | `BORSAI_FAZ6_S2_REPORT`: yalnız `docs/faz6/S2_RAPOR.md`. Bir commit kendi hash'ini içeremez; `git log -1 --format=%H -- docs/faz6/S2_RAPOR.md` ile okunur. |

Taban: HEAD `af915b8`, çalışma ağacında yalnız görev dosyası izlenmiyordu. Taban koşusu: pytest **594 geçti**, `bash app/scripts/test.sh` yeşil, `gen_golden.py --check` 25 dosyada fark yok.

## 2. Bulguların kapatılması (commit C)

Hiçbir model, şartname, girdi ya da kayıt değişmedi. Kod değişikliği yalnız `borsai/outcomes_oot.py` içinde. Görev bunu yalnız F2 savunması ve F6 için izin veriyordu.

| Bulgu | Test (`tests/test_faz6_oot.py`) | Kod |
|---|---|---|
| **F1 (a)** | `test_download_gate_covers_sealed_members`. Açık üye tamam; yalnız kasadaki üyenin kaydı (i) commit'le silinmiş, (ii) commit'lenmemiş ya da (iii) commit'li ama kanıtsız. Üç durumda da `GateError`, ve sorun listesi yalnız o üyeyi gösteriyor. Kanıt eklenince kapı açılıyor. | yok |
| **F1 (b)** | `test_cohort_gate_covers_sealed_members_and_record_ancestor_term`. Açık üyenin sonuç commit'i, kasadaki üyenin S2 kaydından önce giriyor. Sonuç: `cohort_gate_ok = (False, [kasadaki üye])`. Açık üye `OOT_RETRO`, oysa model, kayıt ve kanıt sırası terimlerinin hepsi tamam. Kasadaki kayıt ata olunca kapı açılıyor ve üye `OOT_BLIND` oluyor. | yok |
| **F3** | Aynı testte tek assert. Kayıt, HEAD geçmişinde olmayan bir yan dalda; kapı açık, model ve kanıt sırası tamam. Bu durumda `class_oot(..., record_commit=yan_dal)` → `("OOT_RETRO", record_before_ingest=False)`. Sınıfı yalnız kayıt-atası terimi belirliyor. | yok |
| **F2** | `test_extraction_never_requests_a_bulletin_after_d10`. Piyasa 40 seans; kod her gün işlemde ve D_10'dan sonra da sürüyor. D_10'dan sonraki bir seansın bülteni istendiği anda `fetch` ve indirici testi doğrudan düşürüyor (`pytest.fail`); piyasanın bitmesi beklenmiyor. Denetlenen yollar `resolve_member`, `raw_copies` ve `extract_open_members`. Çağrı sayısı 2 × 10. Ham kopyadaki seans sayısı çözümlenen seans sayısına eşit, ≤ 10. Savunma üç durumda sınandı: D_10 sonrası okunmuş, 10'dan fazla seans çözümlenmiş, `extract_open_members` içinde D_10 sonrası okunmuş. Üçünde de hata veriyor ve hiçbir çıktı yazılmıyor. | `assert_window_bound(ext)`: çözümlenen seans ≤ `N_SESSIONS`; pencere dolduysa D_10'dan sonra hiçbir bülten okunmamış olmalı. `raw_copies` içinde ve `extract_open_members` içinde, yazmadan önce çağrılıyor. |
| **F6** | `test_download_gate_ignores_s3_outputs_only`. `registry/oot/d1_rows/` ve `registry/oot/post_d1/` altındaki izlenmeyen dosyalar kapıyı kapatmıyor; o dizinlerin bekçisi (`d1_rows_problems`) ayrı çalışıyor ve boş belgeyi hâlâ reddediyor. Aşağıdaki kirlilik ise kapıyı kapatıyor: benzer adlı yollar (`d1_rows_x.json`, `post_d1x/`), `inputs/`, kök dosya ve değiştirilmiş girdi. | `S2_GATE_DIRT_EXCLUDED = ("registry/oot/d1_rows", "registry/oot/post_d1")`. `git status` pathspec'inde `:(exclude)` ile dışlanıyor. |

### Mutasyon gösterimi (`docs/faz6/ekler/s2_bulgu_kapatma.txt`)

Klon: `git clone --local` ile alındı, üstüne commit'lenmemiş fark uygulandı. Her mutasyondan sonra yeni 4 test koştu, sonra mutasyon yedekten geri alındı. Her kırmızı, testin kendi assert'inden geliyor; sentetik verinin bitmesinden gelen tesadüfi kırmızı yok.

| Mutasyon | Kırmızı test | Düşen assert |
|---|---|---|
| Fable (b): `s2_gate_problems` SEALED'i atlar | F1a | `[] == ['SYNB: S2 kaydı yok']` |
| (b′): (b)'nin skor tarafındaki eşi; `cohort_gate_ok` SEALED'i atlar | F1b | `(True, []) == (False, ['SYNZ'])` |
| Fable (i): kohort kapısı hep açık | F1b | aynı |
| Fable (i2): `record_ok = True` | F1b (F3 assert'i) | `('OOT_BLIND', True) == ('OOT_RETRO', False)` |
| Fable (d): durma koşulu `N_SESSIONS + 1` | F2 | D_10'dan (2021-03-12) sonraki seansın bülteni istendi: 2021-03-15 |
| (d′): `assert_window_bound` boş | F2 | `DID NOT RAISE OotOutcomeError` |
| (f6): dışlama kaldırılır | F6 | S3 çıktıları "temiz değil" sayılıyor |
| (f6b): dışlama fazla geniş (`inputs/`, benzer adlar) | F6 | `d1_rows_x.json` kirliliği görülmüyor |
| mutasyonsuz | — | 4/4 yeşil |

(b) yalnız indirme kapısını değiştirir, bu yüzden F1b'yi etkilemez. F1b için skor tarafındaki eşi (b′) ve Fable'ın (i) mutasyonu gösterildi.

## 3. S2 kayıtları (commit S2)

Komut: `.venv/bin/python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv`. Ağaç, commit C'den hemen sonra temizdi. Koşu 4,2 s sürdü. Çıktı: **135 yazıldı, 0 atlandı, 0 yinelenen**. `cohort_file_sha256 = 7d05b334…60a7`.

Denetim betiği her maddeyi yeniden hesapladı (repo dışında, scratchpad):

| Denetim | Sonuç |
|---|---|
| Dosya sayısı | 135; her MEMBER'a tam bir kayıt |
| Şema | 135/135 `schema_version = borsai.oot_record/1`, `record_type = PREDICTION`, `record_stage = OOT_PRE_LISTING`, `scale = OOT_PRE_H99` |
| Model | Her kayıtta INDEX'teki 19 model, aynı sırada; toplam 2565 hücre |
| `cohort_file_sha256` | 135/135 kohort dosyasının sha256'sına eşit |
| `inputs_sha256` | 135/135 `registry/oot/inputs/<T>.json` sha256'sına eşit |
| `models_index.sha256` | 135/135 `models/INDEX.json` sha256'sına eşit (`1bc33791…8779`); `model_ids` INDEX ile aynı |
| `params_sha256` | Her hücrede model dosyasının ve INDEX'in sha256'sına eşit |
| `code` | 135/135 `git_head = 40db62c` (commit C), `borsai_dirty = false` |
| Diğer | Dosya adı içerik adresli; sonuç anahtarı yok; `vault` ve `regime_tags` kohort satırından |
| `recorded_at_utc` | 2026-09-24T22:13:06Z … 22:13:10Z. Bu yerel saattir; zaman kanıtı push'tur (§6). |
| Kasa | OPEN (açık küme) **71**, SEALED **64** |

### Durum sayıları (135 üye; AUDIT §7 ile birebir, 19/19 model)

| Model | PREDICTED / REFUSED / NOT_APPLICABLE_REGIME |
|---|---|
| `v1_5_h99`, `v1_6_h99`, `v1_5_market20_v0`, `ceiling_hazard_v0` | 130 / 5 / 0 |
| `ceiling_path_v0` | 127 / 4 / 4 |
| `pb_v0`, `pb_ceiling_v0` | 112 / 23 / 0 |
| `pb_ceiling_path_v0` | 109 / 22 / 4 |
| `base_always_ceiling`, `ceiling_hazard_v0@INF`, `pb_ceiling_v0@INF`, `ceiling_path_v0@INF` | 134 / 0 / 1 |
| 7 kural (`base_train_median`, `base_train_mean`, `base_zero`, `base_rate`, `base_last10_rate`, `base_km_expanding`, `base_km_last10`) | 135 / 0 / 0 |
| **Toplam (2565 hücre)** | **2461 / 92 / 12** |

### Bit-eşitlik

5 kayıt `random.Random(20260925).sample` ile seçildi: CVKMD, DNISI, KZBGY, QUAGR, UNLU. Bu, Fable'ın kuru koşusundaki kümeyle aynı. Her hücre, kaydın `model_inputs`'u ile doğrudan `predict` / `predict_hazard` / `predict_path` / `predict_pb` / `predict_market20` çağrısına karşılaştırıldı. Sonuç: **95/95 hücre `==`**, kanonik JSON da eşit.

## 4. Test sayıları

| Koşu | pytest | test.sh |
|---|---|---|
| Taban (`af915b8`) | 594 geçti | yeşil |
| C öncesi (değişiklikler ağaçta) | **598 geçti** (594 + 4 yeni) | yeşil (cargo 94, npm 222, parity 4, `golden_unchanged` YEŞİL) |
| S2 öncesi, kayıtlar izlenmiyor | 595 geçti, 3 kırmızı. Üçü de temizlik bekçisi ve yalnız `?? registry/oot/records/` yüzünden kırmızı: `test_faz4_ceiling_path.py::test_new_models_are_retro_with_no_record_and_no_metric`, `test_faz5_post_d1.py::test_14_models_goldens_and_read_only_paths_unchanged`, `test_scoring.py::test_faz4_scores_json_existing_blocks_unchanged` | — |
| Aynı, üçü deselect | **595 geçti, 3 deselect** | — |
| S2 sonrası, deselect'siz | **598 geçti** | yeşil (cargo 94, npm 222, parity 4, `golden_unchanged` YEŞİL) |

## 5. Kapı durumu (ölçüm, S2 commit'inden sonra)

`outcomes_oot.s2_gate_problems()` 135 sorun veriyor; hepsi "push kanıtı yok". Kapı, proje sahibi push edip kanıtı ekleyene kadar kapalı. Başka sorun (kayıt eksik, commit'siz, model eksik, kirlilik) yok.

## 6. Proje sahibi için: push ve push kanıtı

```
git push origin main
.venv/bin/python -m borsai.push_proof 40db62c 1dcceff
git add registry/push_proofs
git commit -m "BORSAI_PUSH_PROOFS: Faz 6 audit fix (40db62c) and S2 records (1dcceff)" -- registry/push_proofs
git push origin main
.venv/bin/python -c "from borsai import outcomes_oot as oo; print(oo.s2_gate_problems())"   # [] beklenir
```

- S2 commit'inin (`1dcceff`) kanıtı, kohortun herhangi bir bülteni indirilmeden önce alınmalı. Kanıtın `created_at`'i, sonuç commit'inin kanıtından önce olmalı (`class_oot` kanıt sırası).
- Kanıt dosyaları `registry/push_proofs/` altında durur, `registry/oot` altında değil. Bu nedenle kanıt commit'i kapının kirlilik denetimini etkilemez.

## 7. S3/S5 için notlar

- **Adım 0:** Önce `s2_gate_problems() == []` olmalı. Bu, push kanıtının repoda olduğunu doğrular. Sonra `gen_golden.py --check` ve tam test koşulur.
- **F6 kalıntısı:** Kapı artık yarım kalan bir S3'ü engellemiyor. Ama `extract_d1_rows`, var olan `d1_rows/<T>.json` için `_write_new('xb')` ile hâlâ `FileExistsError` verir. S3 görevi iki yoldan birini seçmeli: ya tek koşuda bitmeli, ya da "dosya var ve içerik aynıysa atla, farklıysa DUR" kuralını kendi kapsamında eklemeli. Bu görev yalnız kapıyı düzeltti; `extract_d1_rows` davranışı değişmedi.
- **F2 savunması:** `extract_open_members` bir üyede pencere aşımı görürse o üyede durur ve o üyeye hiçbir dosya yazmaz. Önceki üyelerin çıktıları yazılmış olabilir. Bu bir DUR durumudur: kod düzeltilir, aynı model_id.
- **F4, F5, F7–F9** değişmedi. F5 (üye başına `exposure_class`, sabit 28) S6'ya kaldı. F4 fiilen boş terimdir.
- **Beş XU100-boşluk günü:** HEAD probu S3'ün ilk ağ işidir. Yayımlanmış bir gün çıkarsa DUR.
- **Canlı temizlik bekçileri:** S3/S5 commit'lerinden önce aynı üçlü, `data/` yazılınca da `test_guardrails.py::test_legacy_and_data_have_no_working_tree_changes` kırmızı olur. Yol: deselect → commit → deselect'siz koşu.

## 8. Kabul kapısı

- **K1** ✓ F1 (a, b), F2 ve F3 testleri eklendi. Fable'ın (b), (d), (i2) mutasyonları ve (b′), (i), (d′), (f6), (f6b) yeni testleri doğrudan assert'le kırmızı yaptı; geri alınınca 4/4 yeşil. F6 düzeltildi ve testlendi. Tam pytest 598 ve test.sh yeşil.
- **K2** ✓ 135 kayıt × 19 model = 2565 hücre. Durum sayıları AUDIT §7 ile 19/19 model birebir. 5 kayıtta 95/95 hücre bit-eşit.
- **K3** ✓ Sıra C `40db62c` → S2 `1dcceff` → R. S2 commit'i yalnız `registry/oot/records/` (135 dosya). push yok.
- **K4** ✓ Hiçbir bülten ya da sonuç dosyası yok: ağ kullanılmadı, `data/` değişmedi.

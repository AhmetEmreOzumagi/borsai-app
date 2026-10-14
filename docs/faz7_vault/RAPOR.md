# BORSAI_FAZ7_VAULT_OPEN_20260929 — kasanın tek seferlik açılışı: Bölüm A (kod, açılış, kasa D_1 satırları, kasa POST_D1 kayıtları)

Uygulayıcı: Claude Code (Opus 5.5). Tarih: 2026-09-29 (İstanbul; ağ işleri 13:13–15:44 arası).

Ağ yalnız `www.borsaistanbul.com` THB/THM bülten URL'lerine gitti (HEAD probları ve zip indirmesi); indirilen zip'ler yalnız karantinaya yazıldı (`~/Desktop/BorsAi_quarantine`, repo dışında). Bu raporda yalnız sayılar var: hiçbir üyenin fiyatı, getirisi, limiti ya da satırı yazılmadı; kasa kodu listelenmedi. `EXPOSURE.md` dosyaları ve Codex `exposure_log`'ları okunmadı. Skorlama çalıştırılmadı (`scoring --oot`, `build_oot_scores` gerçek kasa verisiyle hiç çağrılmadı; kasa satırlarından bellekte bile metrik hesaplanmadı). push, tag ve amend yapılmadı.

## 1. Commit'ler

| Sıra | Commit | İçerik |
|---|---|---|
| C | `1b2fe00` | `BORSAI_FAZ7_VAULT_CODE`: M-B…M-I kodu ve sentetik testleri, SPEC_DEVIATIONS M1–M13, görev dosyası, `ekler/test_runs.txt` |
| C2 | `439a808` | `BORSAI_FAZ7_VAULT_CODE2`: TARIH biçimi düzeltmesi (proje sahibi kararı; SPEC_DEVIATIONS M14), testi, güçlendirilmiş B kapısı testi |
| VA1 | `2f914dd` | `BORSAI_FAZ7_VAULT_D1`: yalnız `registry/oot/d1_rows/` (64 yeni kasa dosyası), `registry/oot/VAULT_OPEN.json`, `data/raw/bist/MANIFEST_OOT.csv` |
| VA2 | `5a96e25` | `BORSAI_FAZ7_VAULT_POST_D1`: yalnız `registry/oot/post_d1/` (64 yeni kasa kaydı) |
| RA | bu raporu ekleyen commit | `BORSAI_FAZ7_VAULT_A_REPORT`: bu rapor ve `docs/faz7_vault/ekler/` (bir commit kendi hash'ini içeremez; `git log -1 --format=%H -- docs/faz7_vault/RAPOR.md`) |

Sıra: C → prob → ilk `vault-d1` (DUR, §4) → C2 → `vault-d1` → VA1 → `vault-post-d1` → VA2 → RA. Görevdeki C → VA1 → VA2 → RA sırasına proje sahibinin kararıyla C2 eklendi (SPEC_DEVIATIONS M14).

## 2. Taban (adım 0)

- HEAD = `origin/main` = `1d659da`; çalışma ağacında yalnız görev dosyası izlenmiyordu.
- `len(oo.s2_gate_problems())` → **0**.
- Karantina: **918 zip, manifest 918 satır**; her dosyanın sha256'sı manifestle eşit; manifest satırı olup dosyası olmayan 0; `_orphans/` yok. Zip içleri açılmadı.
- Tam pytest **848 geçti**; `test.sh` yeşil (cargo 94, vitest 222/222, parity 4, golden_unchanged YEŞİL); `gen_golden --check` 25 dosya, fark 0 (`ekler/test_runs.txt`).

## 3. Kod (C ve C2)

Hiçbir model, şartname, eşik, skor tanımı, girdi ya da kayıt değişmedi. Kod `borsai/outcomes_oot.py` ve `borsai/scoring.py`'de (yalnız M-F); `freeze.py` değişmedi (kasa üyesinin POST_D1 kaydı bugünkü yazıcıyla yazılır).

| Karar | Uygulama | Test (`tests/test_faz7_vault.py`, sentetik) |
|---|---|---|
| M-A | Komutlar `vault-d1` → `vault-post-d1` → (kanıt) → `vault-s5`; kasa bir kez açılır (yeniden indirme VA1'de) | uçtan uca sentetik zaman çizelgesi |
| M-B | `VAULT_OPENING_DOCS` (dört belge); `vault_docs_evidence`: HEAD'de, değişmemiş, son değiştiren commit'i kanıtlı; `vault_gate_problems` = belgeler + `download_gate`; `open_vault(feature_specs=…)` genelleşti (eski `feature_spec` aynen) | `test_vault_gate_requires_four_committed_unchanged_pushed_documents_and_download_gate`: kanıtsız / değişmiş / commit'siz belge ve kapalı indirme kapısında hiçbir HEAD ve zip yok |
| M-C | `open_vault`: HEAD'deki MANIFEST_OOT'un her pini tempolu yeniden indirilir, sha eşit değilse `SourceChanged` (hiçbir kasa dosyası yazılmaz); `VaultFetcher`: her zip o koşuda indirilir; karantina kopyası, MANIFEST_OOT pini ve Takvim C kanıt pini ile eşit olmalı; karantinada yoksa yazılır | `test_open_vault_redownloads_every_pin_and_stops_on_one_mismatch`, `test_vault_fetcher_equal_green_and_each_mismatch_kind_red` (üç uyuşmazlık türü ayrı ayrı kırmızı; eşitlik yeşil) |
| M-D | `registry/oot/VAULT_OPEN.json` (şema `borsai.vault_open/1`), en son yazılır; kasa kodu yok; yeniden koşuda zaman alanları dışında aynıysa dokunulmaz, farklıysa DUR; indirme kapısının kirlilik denetimi işareti saymaz | `test_vault_d1_writes_sealed_d1_rows_pins_and_marker_and_is_rerun_safe`, `test_vault_d1_writes_nothing_when_a_later_member_stops` |
| M-E | İki kip (`vault_marker_state`, `vault_hygiene_problems`; `cohort_code_problems(..., vault_open)`); açılış yetkisi `VaultUnsealed` (yalnız `open_vault` ve `vault_marker_unsealed`) | `test_vault_hygiene_guard_two_modes_and_mutations`, `test_cohort_code_guard_two_modes`, `test_sealed_rows_open_only_with_open_vault_result_or_pushed_marker` |
| M-F | `post_d1_sealed`, `post_d1_all` (yalnız kasa açılınca); `post_d1` açık blok aynı; SCORES_OOT.md §10–§11 | `test_post_d1_vault_keys_only_after_vault_opens_and_open_block_unchanged`; gerçek depo: `test_real_scores_oot_in_memory_run_equals_committed_file_while_vault_closed` |
| M-G, M-H | `vault-post-d1` kasa d1_rows'u olan her üyeye kayıt (REFUSED, NOT_APPLICABLE dahil), işaret commit'siz ise DUR; komutlar yalnız sayı basar | `test_vault_post_d1_needs_committed_marker_and_covers_every_sealed_member`, `test_vault_post_d1_and_s5_open_no_zip_without_marker` |
| M-I | `vault_s3_gate_problems` (iletiler yalnız sayı); `vault-s5` önce kapıyı çağırır; D_1 ve D_1 sha'ları d1_rows'la aynı değilse DUR | `test_vault_s3_gate_requires_pushed_marker_d1_rows_and_post_d1_then_vault_s5`, `test_vault_s5_stops_before_writing_when_d1_differs_from_d1_rows` |
| M14 (C2) | TARIH: ISO ya da d.mm.yyyy / dd.mm.yyyy; noktalı bültende her satır bülten gününe çevrilmeli ve sayısal alanlar kanonik biçimde, aksi DUR; ISO yolu aynen | `test_tarih_dotted_formats_accepted_iso_path_unchanged_and_other_formats_stop` |
| hijyen | yeni metinlerde kasa kodu ve bülten adı kalıbı yok | `test_new_task_files_carry_no_vault_code_or_bulletin_name` |

### 3.1 Prova (geçici klon; SPEC_DEVIATIONS M13)

C'nin kodu commit'li bir geçici klonda, 64 gerçek kasa üyesi için **sentetik değerli** d1_rows, POST_D1 kayıtları, sonuç ve ham kopya dosyaları ve işaret dosyası yazıldı (kodlar kohort dosyasından betikle; hiçbiri basılmadı; test çıktısı kasa kodu maskesinden geçti; ağ yok). Klon provadan sonra silindi.

| Durum | Tam pytest | Kırmızı olanlar |
|---|---|---|
| VA1 commit'siz | 857 geçti, 6 kırmızı | yalnız temizlik bekçileri: `test_faz4_ceiling_path::test_new_models_are_retro_with_no_record_and_no_metric`, `test_faz5_post_d1::test_14_models_goldens_and_read_only_paths_unchanged`, `test_faz7c_golden::test_models_dir_registry_scores_unchanged`, `test_faz7c_model::test_tables_and_data_versions_unchanged`, `test_guardrails::test_legacy_and_data_have_no_working_tree_changes`, `test_scoring::test_faz4_scores_json_existing_blocks_unchanged` |
| VA1 → VA2 → kanıt → VB → kanıt commit'li | 862 geçti, 1 kırmızı | `test_faz7c_model::test_kesif_guard_stops_on_closed_code` |

İki kipli yapılan testler (eski iddia → yeni iddia):

| Test | Kapalı kip (eski iddia, aynen) | Açık kip (yeni iddia) |
|---|---|---|
| `test_faz7c_model::test_kesif_guard_stops_on_closed_code` | keşif aracı yüklenir, açık küme 71, kapalı kodda durur | kasa sonuç dosyaları repodayken (135 dosya, işaret var) araç yüklenirken durur ve yalnız sayıyı yazar |
| `test_outcome_guard::test_sealed_codes_absent_from_every_extracted_file` | ayıklanmış dosyalarda, POST_D1'de, MANIFEST_OOT'ta, skor dosyalarında kasa kodu yok | `vault_hygiene_problems == []` (M-E a, b) |
| `test_outcome_guard::test_cohort_codes_appear_in_data_only_as_outcomes` | data/'nın hiçbir yerinde kasa kodu yok | yalnız üyenin kendi sonuç dosyalarında kendi kodu; v2 ve başka her yerde yine yasak |

Provadan önce yapılan iki uyarlama: `test_faz6_oot::test_extractor_reads_only_open_codes_and_never_opens_sealed` ve `test_faz7_oot::_vault_ingest` kasa kodunu düz kümeyle değil `VaultUnsealed` yetkisiyle açar (düz kümenin reddedildiği ayrıca iddia edildi).

### 3.2 Mutasyonlar (`ekler/mutasyon.txt`)

18 mutasyonun 18'i kırmızı (her birinin kırmızı nedeni hedef iddia). Görevin istediği M-I mutasyonları (kanıt denetimi: m14, m16; POST_D1 denetimi: m15) C'nin testiyle kırmızıydı. M-C'nin üç uyuşmazlık denetimi (m01–m03), "o koşuda indir" kuralı (m04) ve pin karşılaştırması (m05); M-E'nin kapalı kip (m08), commit sırası (m09), kendi kodu (m10), izinli yol (m11), yetki (m12) ve data/ bekçisi (m13) denetimleri kırmızı. **Bir açık ve kapanışı:** m17 (`vault-s5`'in B kapısını çağırmaması) C'nin testinde yeşil kaldı; o testte işaret kanıtsızdı ve ikinci savunma (`vault_marker_unsealed`) aynı durumu kapatıyordu. C2'de test "işaret kanıtlı, POST_D1 kaydı kanıtsız" durumunu ekledi; m17 artık kırmızı.

## 4. Prob ve ilk `vault-d1` (DUR)

- **Prob** (13:12 civarı): kapı OPEN, kip EVIDENCE, 42 kapanış denetlendi (HEAD 200: 5, 404: 37; 200'ler `application/zip`, 404'ler `text/html`), çelişki yok. Ağdan indirme 0.
- **İlk `vault-d1`** (C ile, 13:13–13:35): M-B kapısı açık; prob temiz; `open_vault` uyuşmazlıksız bitti (uyuşmazlık olsaydı ayıklamaya geçilmezdi). Kasa D_1 ayıklamasında DUR: bir THB bülteninin `TARIH` alanı ISO değil, `d.mm.yyyy`. Kod bütün-ya-hiç yazdığı için **repoya hiçbir şey yazılmadı** (değişiklik 0, işaret dosyası yok); karantinaya 3 zip girdi (manifestli, sha eşit).
- Ölçüm (yalnız sayı): karantinadaki 921 bültenin 1'i ISO dışı TARIH'li; başlığı komşu bültenlerle aynı (56 sütun); ilgili sayısal sütunlardaki 5 451 843 değerin hepsi aynı biçimde (rakam ve tek noktalı ondalık; sözleşme sayısı tam sayı; boş); kasada penceresi 2020-08-06 öncesine düşen üye 2.
- Proje sahibi kararı (C2, beş ekle): kabul edilen biçimler yalnız ISO, `d.mm.yyyy`, `dd.mm.yyyy`; çevrilen tarih bülten günüyle birebir; aynı bültende sayısal biçim denetimi (farklıysa DUR); ISO yolu değişmez (test); bağımsız betik tarihi kendi çözümler; rapora ISO dışı bülten sayısı ve günleri (§5.2).

## 5. VA1 (`vault-d1`, C2 ile; 15:29–15:44)

Komut çıktısı (yalnız sayı): kapı OPEN; belge 4; yeniden indirme 914 / eşit 914 / uyuşmayan 0; kasa üyesi ayıklandı 64, yazıldı 64, aynı 0; D_1 ≠ ilk işlem günü 0; önceden pinli olmayan yeni D_1 tarihi 16; MANIFEST_OOT'a eklenen satır 32 (toplam 946); işaret CREATED; `n_sealed` 64; ağdan indirme 946 (914 yeniden indirme + 32); kasa ayıklamasında okunan farklı zip 122 (96 okuma aynı koşunun yeniden indirmesinden, 32 yeni indirme; karantinaya yeni yazılan 29); ISO dışı TARIH'li bülten 1; takvim probu 200: 5, 404: 37.

| Denetim | Beklenen | Ölçülen |
|---|---|---|
| M-B kapısı | dört belge kanıtlı; `download_gate` açık | 4/4 belge HEAD'de, değişmemiş, kanıtlı (en erken kanıtlar: SPEC_HAZARD_V1 `6a16c16` 2026-09-25T18:09:45Z; KARARLAR `2a21a96` ve SPEC_C_V0 `4fe4e51` 2026-09-27T15:30:42Z; KARARLAR_C `3c93f9c` 2026-09-28T19:06:01Z); indirme kapısı 0 sorun |
| `open_vault` | 914 zip yeniden indirildi, 914 sha eşit, 0 uyuşmazlık | 914 / 914 / 0 |
| `registry/oot/d1_rows/*.json` | 135: 71 açık (bayt-eşit, dokunulmadı) + 64 kasa | 135 = 71 + 64; 71 açık dosya HEAD'le bayt-eşit ve `git status`'ta değişmemiş |
| yeni her dosya | `d1_rows_problems == []`, MACHINE_SEQUENCED, `session_h = 1`, D_1 ≥ ilk işlem günü | 64/64, 64/64, 64/64, 64/64; **D_1 ≠ ilk işlem günü: 0** |
| `MANIFEST_OOT.csv` | ilk 915 satır bayt-eşit; yalnız ekleme; yeni satır = 2 × pinli olmayan yeni D_1 | HEAD'deki 915 satır bayt olarak önek; 946 − 914 = 32 = 2 × 16; yeni anahtarlar tam 16 tarih × {thb, thm}; 32/32 sha = karantina dosyası = karantina manifesti (taze indirmeyle eşitlik koşu içinde `VaultFetcher`'da denetlendi) |
| `registry/oot/VAULT_OPEN.json` | M-D şeması; kasa kodu 0; `n_sealed = 64` | şema sorunu 0; kasa kodu 0; bülten adı kalıbı 0; `n_sealed` 64; `manifest_oot_before` 914 satır ve HEAD sha'sı; `code.git_head` = C2, `borsai_dirty` false |
| M-J (d1_rows) | 64 × 14 alan zip satırıyla eşit; 0 fark | 896 = 64 × 14 alan eşit; **2512 denetim, 0 fark** (35 denetim türü, 122 zip); `borsai` import edilmedi |
| bekçiler | açık kipte yeşil (M-E) | `vault_hygiene_problems() == []`; eski kohort bekçileri deselect edilmeden yeşil (§7) |
| açık küme dosyaları | dokunulmadı | `git status --porcelain` açık kümenin 71 d1_rows'u ve `data/outcomes_oot/` için boş |

M-J betiği `docs/faz7_vault/ekler/bagimsiz_kasa.py` (repo dışındaki geçici dizinden kopyalandı; değer içermez), çıktısı `ekler/bagimsiz_kasa_d1.txt`. Komut (`cwd=/`): `python -I bagimsiz_kasa.py --stage d1 --root ~/Desktop/BorsAi --quarantine ~/Desktop/BorsAi_quarantine --base 439a808`. Betik sentetik depoda denendi: temiz veride 0 fark; kasıtlı bozulmada (bir `aof` alanı, bir kapanış) fark yakaladı; noktalı TARIH'li bir bülten içeren sentetik senaryoda 0 fark ve 1 ISO dışı bülten.

### 5.1 `git status` (VA1'den önce; kod adları yerine yol kalıbı)

```
?? registry/oot/VAULT_OPEN.json
?? registry/oot/d1_rows/<T>.json      (64 dosya; hepsi kasa üyesi)
 M data/raw/bist/MANIFEST_OOT.csv      (yalnız ekleme)
?? docs/faz7_vault/ekler/mutasyon.txt
```

### 5.2 ISO dışı TARIH'li bültenler (M14; değer yok)

- VA1'de okunan zip'lerde: **1** bülten — **2020-06-04 THB**. Bağımsız betik de aynı sayıyı ve günü buldu; o bültende bütün satırların günü tutuyor ve sayısal alanlar kanonik biçimde (fark 0).
- Hijyen notu: bu gün, VA1'de bir kasa üyesinin D_1 okuma kümesindedir; proje sahibinin isteğiyle yazıldı.

## 6. VA2 (`vault-post-d1`)

Komut: `.venv/bin/python -m borsai.outcomes_oot vault-post-d1`; HEAD = VA1 (`2f914dd`), `borsai/`, `registry/`, `data/` temiz. Çıktı: d1_rows (kasa) 64, yazılan 64, zaten var 0; bu komut hiçbir zip açmaz.

| Denetim | Beklenen | Ölçülen |
|---|---|---|
| `registry/oot/post_d1/<T>/` | 64 yeni kasa kaydı; açık kümenin 71 kaydı bayt-eşit | 135 dizin = 71 açık + 64 kasa; kasa üyesi başına tam 1 kayıt; açık kümenin 71 kaydı izleniyor ve `git status`'ta değişmemiş |
| şema, sınıf, ölçek | `borsai.oot_post_d1_record/1`, `MACHINE_SEQUENCED` | 64/64 (`record_stage = OOT_POST_D1`, `scale = OOT_PRE_H99`); dosya adları içerik adresli |
| `code` | `git_head` = VA1, `borsai_dirty = false` | 64/64 `2f914dd`, 64/64 false |
| `d1_rows.sha256` | d1_rows'un kanonik sha'sı | 64/64 |
| `base_record` | üyenin S2 kaydı | 64/64 (yol ve sha256) |
| bekçi | `post_d1_record_problems == []` (MANIFEST_OOT'a karşı) | 64/64 |
| f3 REFUSED kümesi | S2'de `ceiling_hazard_v0` hücresi REFUSED olan kasa üyeleri, birebir (beklenen 2) | 2 = 2, **birebir aynı** |
| hijyen bekçisi | açık kipte yeşil | `vault_hygiene_problems() == []` |

**Durum sayıları** (`post_d1_hazard_v0`, 64 hücre; M-G: hiçbiri atlanmadı):

| PREDICTED | REFUSED | NOT_APPLICABLE | Toplam |
|---|---|---|---|
| 45 | 2 (`F3_MISSING`) | 17 (`D1_NOT_CEILING`) | 64 |

Temizlik yolu: VA2'den önce yalnız commit'lenmemiş `registry/oot/post_d1/` yüzünden kırmızı olan 5 temizlik bekçisi (VA1 listesinden `test_guardrails` hariç; data/ değişmedi) deselect edildi; eski kohort bekçileri hiçbir koşuda deselect edilmedi.

## 7. Test sayıları (`ekler/test_runs.txt`)

| Koşu | pytest | test.sh / gen_golden |
|---|---|---|
| Taban (`1d659da`) | 848 geçti | yeşil (cargo 94, vitest 222/222, parity 4, golden YEŞİL); 25/0 |
| C öncesi | 863 geçti | yeşil (aynı sayılar); 25/0 |
| Prova, VA1 commit'siz (klon) | 857 geçti, 6 kırmızı (temizlik) | — |
| Prova, VB sonrası (klon) | 862 geçti, 1 kırmızı (iki kipli yapıldı) | — |
| C2 öncesi | 864 geçti (+ güçlendirilen dosya tek başına 16 geçti) | yeşil (aynı sayılar); 25/0 |
| VA1 öncesi (6 temizlik bekçisi deselect) | 858 geçti, 6 deselect | — |
| VA1 sonrası, deselect'siz | 864 geçti | — |
| VA2 öncesi (5 temizlik bekçisi deselect) | 859 geçti, 5 deselect | — |
| VA2 sonrası, deselect'siz | 864 geçti (25 dk 17 sn) | yeşil (cargo 94, vitest 222/222, parity 4, golden YEŞİL); 25/0 |

Deselect edilen testler yalnız temizlik bekçileriydi; her birinin kırmızısı yalnız o adımın commit'lenmemiş yeni dosyasından geliyordu:
- VA1 (6): `test_faz4_ceiling_path::test_new_models_are_retro_with_no_record_and_no_metric`, `test_faz5_post_d1::test_14_models_goldens_and_read_only_paths_unchanged`, `test_faz7c_golden::test_models_dir_registry_scores_unchanged`, `test_faz7c_model::test_tables_and_data_versions_unchanged`, `test_guardrails::test_legacy_and_data_have_no_working_tree_changes`, `test_scoring::test_faz4_scores_json_existing_blocks_unchanged` (Faz 6 S3'teki dörde ek olarak Faz 7C'nin iki temizlik testi).
- VA2 (5): aynı liste, `test_guardrails` hariç (data/ değişmedi; bu beş test tek başına koşulup ölçüldü).
Eski kohort bekçileri (`test_oot_*`, `test_sealed_*`, `test_no_cohort_window_*`, `test_cohort_*`) ve M-E'nin yeni bekçileri hiçbir koşuda deselect edilmedi; VA1 ve VA2'den önce açık kipte yeşildi.

### 7.1 Kapı durumu (VA2'den sonra; ölçüm)

- `len(s2_gate_problems())` → 0.
- `vault_s3_gate_problems()` → 3 sorun, hepsi push kanıtı: işaret dosyası; kasa d1_rows (64 üye); kasa POST_D1 kaydı (64 üye). Başka sorun yok (commit'siz, değişmiş, bekçi, sha bağı, kohort dışı ad). `vault-s5` kapısı proje sahibi push edip kanıtı ekleyene kadar kapalı.

## 8. Hijyen ve maruziyet

- Kohort dosyası yalnız betikle okundu; satırı basılmadı. Kasa üyelerinin bültenlerinden yalnız `<T>.E` satırları makineyle okundu; hiçbir satır, fiyat ya da limit ekrana, günlüğe ya da rapora yazılmadı. Ölçümler toplam sayıdır.
- İlk `vault-d1`'in DUR iletisi (§4) kural gereği bir kasa kodunu içeriyordu ("DUR iletisi dışında kod adı geçmez"); bu kod hiçbir dosyaya yazılmadı. Prova ve bekçi çıktıları kasa kodu maskesinden geçirildi; maskesiz junit dosyaları okunmadan silindi.
- Yeni metinlerde (rapor, ekler, SPEC_DEVIATIONS M, testler, işaret dosyası) kasa kodu ve bülten adı kalıbı yok (`test_new_task_files_carry_no_vault_code_or_bulletin_name`).
- Kohort penceresinden repoda hiçbir zip ya da iç CSV yok; zip'ler repo içinde açılmadı.

## 9. Proje sahibi için: push ve push kanıtı

```
cd ~/Desktop/BorsAi
git push origin main
.venv/bin/python -m borsai.push_proof 2f914dd 5a96e25
git add registry/push_proofs
git commit -m "BORSAI_PUSH_PROOFS: Faz 7 vault D_1 rows (2f914dd) and post_d1 records (5a96e25)" -- registry/push_proofs
git push origin main
git --no-pager log --oneline -3 origin/main
```

- VA1 ve VA2'nin kanıtlarının `created_at`'i R1 kanıtından (2026-09-29T06:40:55Z) sonra olacak; VA2'nin kanıtı VB'nin kanıtından önce olmalıdır (`post_d1_hazard_v0`'ın kasada kör testi için; I13).
- Bölüm B, aynı görev cümlesiyle yeni oturumda başlar; adım 0 `s2_gate_problems()` ve `vault_s3_gate_problems()`'in ikisinin de 0 olduğunu ölçer.

## 10. Bölüm B için notlar

- Karantina (§2'deki 918 + ilk koşunun 3 + VA1'in 29 = 950 zip) önbellektir; `vault-s5` yine her zip'i o koşuda indirip karantina, MANIFEST_OOT ve kanıt pinleriyle karşılaştırır.
- Kasada penceresi 2020-08-06 öncesine düşen 2 üyenin D_2…D_10 bültenleri henüz indirilmedi; ISO dışı TARIH'li başka bülten çıkarsa M14 kuralı uygulanır (sayısal biçim farklıysa DUR).
- VB'nin temizlik yolunda provadaki listeye benzer bekçiler kırmızı olabilir (data/ yazılır); `test_kesif_guard_stops_on_closed_code` VB'den sonra açık kipine geçer.
- VAULT_SCORE (ayrı görev): M-L beklentisi SPEC_DEVIATIONS M12'de; "beklentiden çok iyi" durumunda bağımsız yeniden hesap zorunlu.

## 11. Kabul kapısı (Bölüm A)

- **KA1** ✓ M-B…M-I testli (sentetik, `tests/test_faz7_vault.py`); M-C, M-E ve M-I mutasyonla kırmızı gösterildi (18/18; m17 C2 testiyle). Kasa kapalıyken bugünkü bütün iddialar aynen geçti (C öncesi 863). Prova listesi §3.1'de. C sonrası (ve C2 sonrası) tam pytest + test.sh + `gen_golden --check` yeşil.
- **KA2** ✓ Prob temiz (42 kapanış; 200: 5, 404: 37). `open_vault`: 914/914 sha eşit, 0 uyuşmazlık. VA1 tablosu birebir; M-J 0 fark (2512 denetim); işaret dosyasında kod yok. İlk `vault-d1` DUR'u (TARIH biçimi) proje sahibinin kararıyla C2'de çözüldü; o koşu repoya hiçbir şey yazmadı.
- **KA3** ✓ VA2: 64 kasa kaydı; f3 REFUSED kümesi birebir (2). Sıra C → C2 → VA1 → VA2 → RA (C2 proje sahibi kararı). push yok.

---

# Bölüm B: kasa üyelerinin D_1…D_10 satırları (VB)

Tarih: 2026-09-29 (İstanbul; ağ işi 19:00–19:14). Bölüm A'daki hijyen kuralları aynen geçerlidir: raporda yalnız sayı var, kasa kodu listelenmedi, hiçbir üyenin fiyatı, getirisi, limiti ya da satırı yazılmadı; `EXPOSURE.md` dosyaları ve Codex `exposure_log`'ları okunmadı. Ağ yalnız `www.borsaistanbul.com` THB/THM bülten URL'lerine gitti (42 HEAD probu ve zip indirmesi); zip'ler yalnız karantinaya yazıldı. push, tag ve amend yapılmadı. `scores/` yazılmadı; skorlama hiçbir kipte çalıştırılmadı (`scoring --oot` ve `build_oot_scores` çağrılmadı; kasa satırlarından bellekte bile metrik hesaplanmadı).

## B1. Commit'ler

| Sıra | Commit | İçerik |
|---|---|---|
| Kanıt (proje sahibi) | `93c672b` | VA1 ve VA2 push kanıtları: `2f914dd` 2026-09-29T15:30:41Z, `5a96e25` 2026-09-29T15:30:43Z |
| VB | `71b9071` | `BORSAI_FAZ7_VAULT_S5`: yalnız `data/outcomes_oot/` (64 CSV + 64 ham kopya, hepsi yeni) ve `data/raw/bist/MANIFEST_OOT.csv` (yalnız ekleme); toplam 129 dosya |
| RB | bu bölümü ekleyen commit | `BORSAI_FAZ7_VAULT_B_REPORT`: bu bölüm, `ekler/bagimsiz_kasa_s5.txt`, `ekler/test_runs.txt`'nin Bölüm B satırları |

Sıra: RA → kanıt → VB → RB. VB'den önce ve sonra ağaçta başka değişiklik yoktu; VB commit'inin 129 dosyasının hepsi izinli iki yolda.

## B2. Adım 0 (taban)

- Ağaç temizdi (izlenmeyen dosya yok). HEAD = `origin/main` = `93c672b` (VA kanıt commit'i; RA `9e9f5ac`'nin torunu).
- `len(s2_gate_problems()), len(vault_s3_gate_problems())` → **0 0**.
- Kanıt sırası: VA1 (15:30:41Z) ve VA2 (15:30:43Z) kanıtları R1 kanıtından (`28aaa3b`, 2026-09-29T06:40:55Z) sonra ✓.
- Karantina: **950 zip, manifest 950 satır**, 950/950 sha256 manifestle eşit; `_orphans/` yok. Zip içleri açılmadı.
- Tam pytest **864 geçti** (27 dk 29 sn); `test.sh` yeşil (cargo 94, vitest 222/222, parity 4, golden_unchanged YEŞİL); `gen_golden --check` 25 dosya, fark 0 (`ekler/test_runs.txt`).
- M-J betiğinin s5 aşaması VB'den önce açık kümede denendi (betiğin repo dışındaki geçici bir kopyasında üye kümesi yalnız açık küme yapılarak; Faz 6 S5 dosyaları): 71 üye, 710 satır, **12 436 denetim, 0 fark**. Kopya repoya girmedi; commit'li betik değişmedi.

## B3. VB (`vault-s5`)

Komut: `.venv/bin/python -m borsai.outcomes_oot vault-s5` (19:00:52–19:14:25). Sırayla: B kapısı (`vault_s3_gate_problems`: 0 sorun), yetki (`vault_marker_unsealed`: işaret HEAD'de, değişmemiş, kanıtlı, şemadan geçiyor), takvim probu (kip EVIDENCE; 42 HEAD: 200: 5, 404: 37; çelişki yok), 64 kasa üyesinin D_1…D_10 ayıklanması (`VaultFetcher`), savunmalar (pencere ≤ D_10; D_1 ve D_1 bülten sha'ları d1_rows'la aynı), bütün üyeler hazır olunca yazım.

Komut çıktısı (yalnız sayı): ayıklanan 64, hepsi `CREATED`; `n_sessions` 64 üyede 10; okunan > çözümlenen 1 üye; satır durumu `OK` 640; MANIFEST_OOT'a eklenen 222 satır; ağdan indirme 832; okunan farklı zip 832 (= 2 × 416 seans); karantinaya yeni yazılan 222; ISO dışı TARIH'li bülten 4 (§B3.1).

M-C (`VaultFetcher`): okunan 832 zip'in 832'si bu koşuda resmi kaynaktan indirildi (karantinadan okuma 0). 610'unun karantinada kopyası vardı: 610/610 karantina kopyası ve karantina manifestiyle, 610/610 VB öncesi MANIFEST_OOT pinleriyle sha256-eşit; 1 THB ayrıca Takvim C bülten kanıtındaki pinle eşit. Kalan 222 karantinada yoktu; karantinaya ve karantina manifestine yazıldı. Uyuşmazlık 0 (olsaydı DUR; hiçbir sonuç dosyası yazılmazdı).

| Denetim | Beklenen | Ölçülen |
|---|---|---|
| `data/outcomes_oot/<T>.csv` | 135 dosya: 71 açık bayt-eşit + 64 kasa. Her yeni dosya 10 satır (h = 1…10), `outcome_basis` hep `MACHINE_EXTRACTED`, `PENDING` 0 | 135 = 71 açık + 64 kasa; kohort dışı ad 0; açık kümenin 71 CSV'si ve 71 ham kopyası (142 dosya) `93c672b` ile bayt-eşit ve `git status`'ta değişmemiş; 64/64 on satır, h = 1…10; 64/64 `MACHINE_EXTRACTED`; `PENDING` 0 |
| `data/outcomes_oot/raw/<T>.json` | 135 (64 yeni). D_10'dan sonra okunmuş seans yok. Okunan − çözümlenen seans farkı olan üye sayısı | 135 (CSV kümesiyle aynı; 64 yeni); 64/64 D_10'dan sonra okuma yok; **fark olan üye: 1** |
| D_1 tutarlılığı | 64/64 CSV'nin h = 1 seansı = d1_rows D_1; D_1 thb/thm sha'ları d1_rows ve MANIFEST_OOT ile eşit | 64/64; 64/64 d1_rows; 64/64 MANIFEST_OOT |
| `MANIFEST_OOT.csv` | VA1 sonrası satırlar bayt-eşit ve başta; yalnız ekleme; her sha = karantina = taze indirme | `93c672b`'deki başlık + 946 satır bayt olarak önek; 946 → **1168** (+222); yeni anahtarlar tam olarak kasanın okunan 416 seansından önceden pinsiz olanlar × {thb, thm}; anahtar tekrarı yok; 222/222 yeni sha = karantina dosyası = karantina manifesti; taze indirmeyle eşitlik koşu içinde `VaultFetcher`'da (832/832) |
| durumlar | 10 seansı olmayan üye sayısı; `TARGET_UNAVAILABLE` ve `NA_LIMIT` satır sayıları | 10 seansı olmayan üye **0**; 640 satırın 640'ı `OK`; `TARGET_UNAVAILABLE` **0**; `NA_LIMIT` **0** |
| M-J (S5) | bütün yeni satırlarda ham alanlar zip'le eşit; `ceiling_close` ve `R_h` yeniden hesapla eşit; 0 fark | 2560 ham alan (640 × 4) ve 256 `R_h` (64 × 4) eşit; **11 361 denetim, 0 fark** (§B4) |
| bekçiler | açık kipte yeşil; G5′ yeşil | `vault_hygiene_problems() == []` (VB commit'ten önce ve sonra); eski kohort bekçileri, M-E bekçileri ve G5′ (`test_oot_outcomes_follow_every_s2_record_and_its_push_proof`) hiçbir koşuda deselect edilmeden yeşil (§B5) |

Karantina: 950 → **1172 zip**; manifest 1172 satır; 1172/1172 sha256 eşit; `_orphans/` kullanılmadı. Kohort penceresinden repoda hiçbir zip ya da iç CSV yok; zip'ler repo içinde açılmadı.

### B3.1 ISO dışı TARIH'li bültenler (M14; değer yok)

- VB'de okunan 832 zip'in **4**'ü: **2020-06-04 THB, 2020-06-05 THB, 2020-06-08 THB, 2020-06-09 THB**. İlki VA1'de de okunmuştu (§5.2). Dördünde de her satır bülten gününe çevrildi ve ilgili sayısal alanlar kanonik biçimdeydi (aksi DUR olurdu). Bağımsız betik (tarihi kendi çözümler) aynı sayıyı ve günleri buldu; o denetimlerde fark 0.
- Hijyen notu: bu günler kasa üyelerinin okuma kümesindedir; M14'teki proje sahibi kararı ("rapora ISO dışı bülten sayısı ve günleri") gereği yazıldı.

## B4. M-J (S5 kipi)

Komut (`cwd=/`, `python -I`): `bagimsiz_kasa.py --stage s5 --root ~/Desktop/BorsAi --quarantine ~/Desktop/BorsAi_quarantine --base 93c672b` (VB'den önceki HEAD). Betik Bölüm A'da commit'lenen `docs/faz7_vault/ekler/bagimsiz_kasa.py`'nin repo dışındaki bayt-eşit kopyası (değişmedi). Çıktı `ekler/bagimsiz_kasa_s5.txt`.

| Denetim | Sayı |
|---|---|
| sonuç dosyası / ham kopya / kasa satırı | 135 / 135 / 640 (hepsi `OK`) |
| `close_raw`, `trade_count_raw`, `upper_limit_raw`, `reference_raw` ↔ ilgili seansın zip satırı | 2560 eşit |
| `halt_flag`, `ceiling_close` (Decimal kapanış == üst limit), `status`, `ipo_price` (girdi) yeniden hesap | hepsi eşit |
| `R_h` ↔ kapanış / arz fiyatı − 1 (\|Δ\| ≤ 1e-12), `Y_h` = 1[R > 0], h ∈ {1, 3, 5, 10} | 256 eşit |
| `thb_sha256` / `thm_sha256` ↔ zip ↔ MANIFEST_OOT; h = 1 sha'ları ↔ d1_rows | hepsi eşit |
| ham kopya satırları ↔ zip; D_h çözümü (ilk görünüş, işlem gören ilk 10 seans) yeniden kuruldu; okunan seanslar ardışık sonuç takvimi seansları; D_10'dan sonra okuma yok; h = 1 = d1_rows D_1 | 64/64 |
| açık kümenin sonuç ve ham kopya dosyaları `93c672b` ile bayt-eşit | 142/142 |
| MANIFEST_OOT: `93c672b` öneki; yeni satırlar = okunan kasa seanslarının pinsiz olanları; her sha = karantina dosyası = karantina manifesti | eşit (1168 satır, 222 yeni) |
| TARIH (bağımsız çözümleme): kod satırının günü; ISO dışı bültende bütün satırların günü ve sayısal biçim | eşit; ISO dışı 4 bülten |
| **denetim geçen / fark** | **11 361 / 0** (36 denetim türü, 832 zip okundu); `borsai_import_edildi: false` |

## B5. Test sayıları (`ekler/test_runs.txt`)

| Koşu | pytest | test.sh / gen_golden |
|---|---|---|
| Taban B (`93c672b`) | 864 geçti (27 dk 29 sn) | yeşil (cargo 94, vitest 222/222, parity 4, golden YEŞİL); 25/0 |
| VB öncesi (4 temizlik bekçisi deselect) | 860 geçti, 4 deselect (31 dk 45 sn) | — |
| VB sonrası (`71b9071`), deselect'siz | 864 geçti (19 dk 33 sn) | yeşil (cargo 94, vitest 222/222, parity 4, golden YEŞİL); 25/0 |

Temizlik yolu: VB'den sonra, commit'ten önce Bölüm A'nın altı temizlik bekçisi tek başına koşuldu: **4 kırmızı, 2 yeşil**. Dördünün kırmızısı yalnız `git status`'taki commit'lenmemiş VB dosyalarındandı (`M data/raw/bist/MANIFEST_OOT.csv` ve `data/outcomes_oot/` altında 128 izlenmeyen dosya; çıktı kasa kodu maskesinden geçti):
- `test_faz5_post_d1::test_14_models_goldens_and_read_only_paths_unchanged`
- `test_faz7c_model::test_tables_and_data_versions_unchanged`
- `test_guardrails::test_legacy_and_data_have_no_working_tree_changes`
- `test_scoring::test_faz4_scores_json_existing_blocks_unchanged`

Yeşil kalan ikisi (`test_faz4_ceiling_path::test_new_models_are_retro_with_no_record_and_no_metric`, `test_faz7c_golden::test_models_dir_registry_scores_unchanged`) `registry/`'ye bakar; VB `registry/`'ye yazmadı. Eski kohort bekçileri (`test_oot_*`, `test_sealed_*`, `test_no_cohort_window_*`, `test_cohort_*`), M-E'nin bekçileri ve G5′ hiçbir koşuda deselect edilmedi. `test_faz7c_model::test_kesif_guard_stops_on_closed_code` VB'den sonra açık kipte (işaret var, 135 dosya) yeşil.

## B6. VAULT_SCORE için notlar

- **Sonuç girişi (I10, M1).**
  - Listeleme öncesi modeller için kasa ingest'i **VA1 `2f914dd`** (kanıt 2026-09-29T15:30:41Z; d1_rows bu modeller için sonuçtur). Kasa üyelerinin kayıt kanıtları bundan önce: ilk kayıtlar (S2) 2026-09-24T22:39:24Z, ek kayıtlar (`28aaa3b`) 2026-09-29T06:40:55Z. Sınıf `scoring.class_oot` ile tarihlerden hesaplanır; elle etiket yok.
  - `post_d1_hazard_v0` için kasa ingest'i **VB `71b9071`**. Kasa POST_D1 kayıtlarının kanıtı (VA2, 15:30:43Z) VB'nin kanıtından önce olmalı; aşağıdaki push bloğu bunu sağlar (VB'nin kanıtı ondan sonra alınır).
- **Payda.** Kasa 64 üye; 640 sonuç satırının hepsi `OK`, `TARGET_UNAVAILABLE` 0. Kasa POST_D1 (VA2): 45 PREDICTED, 2 REFUSED (`F3_MISSING`), 17 NOT_APPLICABLE (`D1_NOT_CEILING`). M-L'nin satır sayısı beklentisi (n ≈ 50–54) VA2'deki 45 PREDICTED'den büyüktü; bu fark D_1 bilgisidir (modelin girdisi), sonuç değil. Satır kapısı skorlamada uygulanır.
- **Beklenti.** M-L, SPEC_DEVIATIONS M12'de (birincil hücre beklentisi −0.035, aralık [−0.065, −0.005]); "beklentiden çok iyi" (fark < −0.08 ya da aralığın üst ucu < −0.045) → bağımsız yeniden hesap zorunlu.
- **Kasa kipi.** Kasa sonuç dosyaları artık repoda: `OotContext.vault_opened()` doğru olur; `scoring --oot` kasa ve toplam bloklarını (`oot_pre_h99_sealed`/`_all`, `post_d1_sealed`/`post_d1_all`) ve SCORES_OOT.md §10–§11'i üretecek. Commit'li `scores/scores_oot.json` Faz 6 S6'dan (19 model) kalmıştır (M6 yorumu).
- **Karantina.** 1172 zip önbellektir; bağımsız yeniden hesap için silinmemeli.
- **D4.** Kasa satırları hiçbir eğitim ya da keşif tablosuna girmedi; `data/`'nın geri kalanında (v2 dahil) kasa kodu yok (`cohort_code_problems` açık kipte yeşil).

## B7. Proje sahibi için: push ve push kanıtı

```
cd ~/Desktop/BorsAi
git push origin main
.venv/bin/python -m borsai.push_proof 71b9071
git add registry/push_proofs
git commit -m "BORSAI_PUSH_PROOFS: Faz 7 vault outcome rows (71b9071)" -- registry/push_proofs
git push origin main
git --no-pager log --oneline -3 origin/main
```

VB'nin kanıtının `created_at`'i VA2'nin kanıtından (15:30:43Z) sonra olacak; bu sıra `post_d1_hazard_v0`'ın kasada kör testi için gereklidir (I13). `FAZ7_VAULT_SCORE` bu kanıttan sonra koşar.

## B8. Kabul kapısı (Bölüm B)

- **KB1** ✓ VB'den önce `s2_gate_problems()` ve `vault_s3_gate_problems()` boş (0 0); `vault-s5` kapıyı kendisi de çağırdı. VA1 ve VA2 kanıtları (15:30:41Z, 15:30:43Z) R1 kanıtından (06:40:55Z) sonra.
- **KB2** ✓ VB tablosu birebir tuttu (135 = 71 + 64; 64 × 10 satır, `MACHINE_EXTRACTED`, `PENDING` 0; D_1 64/64; MANIFEST_OOT önek + 222; 10 seansı olmayan üye 0; `TARGET_UNAVAILABLE` 0, `NA_LIMIT` 0). M-J 0 fark (11 361 denetim). Açık kümenin 142 dosyası bayt-eşit.
- **KB3** ✓ VB commit'i yalnız izinli yollarda (129 dosya). Deselect'siz tam pytest (864 geçti) + `test.sh` (yeşil) + `gen_golden --check` (25/0) yeşil. Skorlama çalıştırılmadı; `scores/` yazılmadı; push yok.

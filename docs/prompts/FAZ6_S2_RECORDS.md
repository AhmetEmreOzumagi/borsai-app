# TASK_ID: BORSAI_FAZ6_S2_RECORDS_20260925

Model: Opus 5.5 · yüksek. Klasör: ~/Desktop/BorsAi. **Ağ gerekmez ve KULLANILMAZ** (bülten yok). push/tag/amend yok.

## Bağlam
- Eski kohort altyapısı ve girdiler: `1d4913e` (A), `2e088c3` (S1, push kanıtı 2026-09-24T21:18:56Z). Rapor `docs/faz6/INFRA_RAPOR.md`.
- Fable denetimi `af915b8` (`docs/fable_faz6_audit/AUDIT.md`), hüküm **S2_OK**:
  - Kasa ve rejim etiketleri bağımsız olarak 135/135 yeniden üretildi.
  - Takvim C resmi PDF'lerle 1360/1360 satır uyuşuyor.
  - 15 üyelik girdi örnekleminde 296/296 alan doğru.
  - Kuru S2: 135 × 19 = 2565 hücre, durum sayıları raporla aynı, 95/95 hücre bit-eşit.
  - Tam pytest 594 geçti; test.sh yeşil.
- Denetimin iki ÖNEMLİ bulgusu **test kapsamıyla** ilgili; kod şartnameye uygun. S2'yi engellemiyor ama S3/S5'ten (bülten indirme) önce kapatılmaları şart. Bu görev önce onları kapatır, sonra S2'yi yazar.
- **Denetim bir uygulama hatası ya da sızıntı bulursa kodu şartnameye uydurmak aynı model_id'dir; şartnameyi değiştirmek yeni model_id'dir.** (Bu görev hiçbir modeli değiştirmez.)
- Sonuç körlüğü: kohort üyelerinin listeleme sonrası hiçbir verisine bakılmaz; `docs/faz6/dogrulama/EXPOSURE.md` §3 okunmaz; raporda hangi kodun SEALED olduğu yazılmaz.

## İzinli izlenmeyen
Yalnız `docs/prompts/FAZ6_S2_RECORDS.md`. Başka bir şey varsa DUR.

ÖNCE OKU: CLAUDE.md; docs/fable_faz6_audit/AUDIT.md (§0, §7, §8, §10); docs/faz6/INFRA_RAPOR.md (§6, §9); docs/specs_faz6/KARARLAR.md (D2, D6); borsai/outcomes_oot.py (`s2_gate_problems`, `download_gate`, `resolve_member`, `raw_copies`, `extract_open_members`); borsai/freeze.py (`build_oot_records`, `write_oot_records`); tests/test_faz6_oot.py.

## Adımlar
0. **Taban:** `GIT_OPTIONAL_LOCKS=0 git --no-pager log --oneline -3` (HEAD `af915b8` ya da torunu), `git status --porcelain`. Tam `.venv/bin/pytest -q` ve `bash app/scripts/test.sh` (beklenen 594 geçti, test.sh yeşil).
1. **Bulgu kapatma (commit C):**
   - **F1:** `tests/test_faz6_oot.py`'ye iki test.
     - (a) Sentetik kohortta SEALED bir üyenin S2 kaydı yok ya da commit'lenmemişken `download_gate` `GateError` verir.
     - (b) `cohort_gate_ok`, SEALED bir üyenin kaydı sonuç commit'inin atası değilken kapalıdır.
     - F3'ü de kapsayan tek assert ekle: kayıt-atası terimi tek başına bozulunca kırmızı.
   - **F2:** uzun sentetik piyasada (≥ 30 seans) iki assert: `resolve_member` / `raw_copies` / `extract_open_members` hiçbir zaman D_10'dan sonraki seansın bültenini istemez (`fetch` çağrı sayacı), ham kopyanın seans sayısı = çözümlenen seans sayısı ≤ 10. Savunma olarak `raw_copies` ve `extract_open_members` içine `len(sessions) ≤ outcomes.N_SESSIONS` denetimi (aşılırsa hata).
   - Her yeni test için mutasyon gösterimi: Fable'ın mutasyonu (b), (d), (i2) geçici olarak uygulanınca yeni test KIRMIZI, geri alınınca yeşil. Çıktı `docs/faz6/ekler/s2_bulgu_kapatma.txt`.
   - F6 (S3 yeniden başlatma): `s2_gate_problems`'in kirlilik denetiminden `registry/oot/d1_rows/` ve `registry/oot/post_d1/` dışlanır; o dizinlerin bekçileri ayrı ve değişmez. Test.
   - Tam pytest + test.sh yeşil → **commit C**.
2. **S2 (commit S2):**
   - Temiz ağaçta: `.venv/bin/python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv`.
   - Beklenen: `registry/oot/records/<T>/…json`, 135 MEMBER, her kayıtta 19 model. Durum sayıları (PREDICTED / REFUSED / NOT_APPLICABLE_REGIME, 135 üyede) **AUDIT §7 tablosuyla birebir**:
     - v1_5_h99, v1_6_h99, v1_5_market20_v0, ceiling_hazard_v0: 130 / 5 / 0
     - ceiling_path_v0: 127 / 4 / 4
     - pb_v0, pb_ceiling_v0: 112 / 23 / 0
     - pb_ceiling_path_v0: 109 / 22 / 4
     - base_always_ceiling ve üç `@INF`: 134 / 0 / 1
     - 7 kural: 135 / 0 / 0
     
     Tutmazsa kayıtları commit ETME, DUR.
   - Denetim: 135/135 kayıt `borsai.oot_record/1` şemasında; `cohort_file_sha256` ve `inputs_sha256` dosyalarla eşit; `models_index.sha256` = `models/INDEX.json` sha'sı; 5 rastgele kayıtta (tohum 20260925) bütün hücreler doğrudan `predict` çağrısına bit-eşit.
   - Commit öncesi yalnız `test_faz4_ceiling_path.py::test_new_models_are_retro_with_no_record_and_no_metric` ve diğer temizlik bekçileri, yalnız bu yeni kayıtlar yüzünden kırmızıysa: deselect'li tam koşu yeşil → **commit S2** (yalnız `registry/oot/records/`) → deselect'siz tam koşu + test.sh yeşil. Değilse DUR (amend yok).
3. **Rapor** `docs/faz6/S2_RAPOR.md` (commit S2'den sonra, ayrı küçük commit R). İçerik:
   - C, S2 ve R hash'leri.
   - Kayıt ve durum sayıları (yalnız toplamlar; kasa kırılımı yalnız OPEN/SEALED sayısı).
   - Bit-eşitlik denetimi.
   - Test sayıları.
   - Mutasyon gösterimi.
   - Proje sahibine push ve push kanıtı komutları.
   - Bir sonraki adım olan S3/S5 için notlar.

Tek oturumda bitmezse: C yeşil ve commit'liyse orada dur.

## Kurallar
- Yazılabilir: `borsai/outcomes_oot.py` (yalnız F2 savunması ve F6), `tests/`, `registry/oot/records/` (yalnız S2 CLI'siyle), `docs/faz6/`, bu görev dosyası.
- Salt okunur: `models/`, `registry/` (records dışı), `data/`, `scores/`, `app/`, `docs/specs*`, `CLAUDE.md`, diğer `borsai/` dosyaları.
- Kayıtlar elle düzenlenmez, yeniden yazılmaz; hata varsa commit'lenmeden önce DUR.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.
- `git add -A` yok. Commit'ler:
  ```
  git add borsai/outcomes_oot.py tests docs/faz6/ekler/s2_bulgu_kapatma.txt docs/prompts/FAZ6_S2_RECORDS.md
  git commit -m "BORSAI_FAZ6_AUDIT_FIX: tests for SEALED S2 gate coverage and D1..D10 bulletin bound (Fable F1, F2, F3), S3 restart gate (F6)" -- borsai/outcomes_oot.py tests docs/faz6/ekler/s2_bulgu_kapatma.txt docs/prompts/FAZ6_S2_RECORDS.md
  git add registry/oot/records
  git commit -m "BORSAI_FAZ6_S2: out-of-time prediction records, 135 members x 19 frozen models, before any cohort bulletin" -- registry/oot/records
  git add docs/faz6/S2_RAPOR.md
  git commit -m "BORSAI_FAZ6_S2_REPORT: S2 record counts and checks" -- docs/faz6/S2_RAPOR.md
  ```
  `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
- Rapor Türkçe.

## Kabul kapısı
- K1 F1, F2, F3 testleri eklendi ve mutasyonla kırmızı gösterildi; F6 düzeltildi; tam pytest + test.sh yeşil.
- K2 135 kayıt × 19 model; durum sayıları beklenenle birebir; 5 kayıt bit-eşit.
- K3 C → S2 → R sırası; S2 commit'i yalnız `registry/oot/records/`; push yok.
- K4 Hiçbir bülten ya da sonuç dosyası yok.

# TASK_ID: BORSAI_FAZ7_PROSPECTUS_INTAKE_20260926

Model: Sonnet 5 · yüksek.
- **Klasörler:** repo `~/Desktop/BorsAi`. Kaynak `~/Desktop/BorsAi_codex/verified_faz7/`, salt okunur.
- **Ağ:** yok.
- **Git:** push/tag/amend yok.

## Rol
Eski kohortun 135 üyesi için doğrulanmış izahname alanlarını repoya alırsın. Bunlar 7 listeleme öncesi alan:
- `distribution_method`
- `price_stability_planned`
- `price_stability_days`
- `issuer_lockup_days`
- `shareholder_lockup_days`
- `sector`
- `participation_index_eligible`

Doğrulama bitti (`verified_faz7/REPORT.md`). Senin işin kopyalamak, pinlemek, bekçi testi yazmak ve commit etmek. Değer değiştirmezsin.

## Paralel
Bir Fable oturumu `docs/prompts/FAZ7_FABLE_V1_REPRO_AUDIT.md`'yi koşuyor ve yalnız `docs/fable_faz7_audit/`'e yazıyor. O dizine ve görev dosyasına dokunma, commit'ine koyma.

## Hijyen
- 135 üye tek dizinde durur. OPEN / SEALED ayrımı hiçbir yeni dosyaya, dizin adına, çıktıya ya da rapora yazılmaz ve ekrana basılmaz.
- Kasa üyelerinin sonuçlarına hiçbir yerde bakılmaz. `docs/faz6/dogrulama/EXPOSURE.md` §3 okunmaz.
- `verified_faz7/EXPOSURE.md` okunmaz: yalnız bayt-eşit kopyalanır ve sha'lanır.
- Metinlerde `thb`/`thm` + 8 haneli tarih kalıbı yazma.

ÖNCE OKU: CLAUDE.md; `verified_faz7/REPORT.md`; `docs/prompts/FAZ7_VERIFY_PROSPECTUS.md`; Faz 6 kalıbı için `registry/oot/candidate_features/` ve `registry/oot/source_docs/*/MANIFEST.json` birer örnek, `tests/test_outcome_guard.py` (`test_registry_carries_no_outcome_fields`, `test_source_documents_predate_first_trading_day`), `borsai/registry.py` (`load_inputs`, `istanbul_date`, OOT girdi dizini).

## Adımlar
0. **Taban.** `git status --porcelain`. İzinli izlenmeyen/değişmiş yollar:
   - bu görev dosyası;
   - `docs/prompts/FAZ7_CODEX_PROSPECTUS_B1..B4.md`, `docs/prompts/FAZ7_VERIFY_PROSPECTUS.md`;
   - Fable'ın yolları (`docs/fable_faz7_audit/`, `docs/prompts/FAZ7_FABLE_V1_REPRO_AUDIT.md`).
   
   Başka bir şey varsa DUR.
1. **Kopyala (bayt-eşit):**

   | Kaynak (`verified_faz7/`) | Hedef |
   |---|---|
   | `candidate_features_faz7/<T>.json` (135) | `registry/oot/candidate_features_faz7/<T>.json` |
   | `source_docs/<T>/MANIFEST.json` (135; PDF'ler KOPYALANMAZ) | `registry/oot/source_docs_faz7/<T>/MANIFEST.json` |
   | `REPORT.md`, `coverage.csv`, `verification_log.jsonl`, `EXPOSURE.md` | `docs/faz7/prospectus/` |
   | `_tools/scripts/*.py` ve `*.md` (`__pycache__` hariç) | `docs/faz7/prospectus/scripts/` |
   | `_tools/logs/`: `verifier_interventions.jsonl`, `sha_compare.json`, `sample10.txt`, `recheck_log.jsonl`, `audit_result.json`, `tables.md` | `docs/faz7/prospectus/logs/` |

2. **Pin dosyası:** `registry/oot/candidate_features_faz7/SHA256SUMS` (sha256sum biçimi). İçinde:
   - 135 özellik dosyası;
   - 135 kaynak MANIFEST'i (yol `../source_docs_faz7/<T>/MANIFEST.json`);
   - `docs/faz7/prospectus/` altındaki her dosya (göreli yolla).
3. **`docs/faz7/prospectus/README.md`** (kısa, Türkçe):
   - ne olduğu, kaynak, doğrulayıcı;
   - PDF'lerin repoda olmadığı ve MANIFEST'teki URL + sha256 ile yeniden indirilip eşlenebileceği;
   - alan tanımları için REPORT §3'e gönderme;
   - şu cümle aynen: "(C) özelliklerini tasarlayan oturum `EXPOSURE.md`'yi okumaz; keşif yalnız H99 ve açık kümede yapılır, kasa üyelerinin özellik dosyaları keşifte açılmaz."
4. **Bekçi testi `tests/test_faz7_prospectus.py`** (gerçek repo; `borsai` import edebilir):
   - (a) Özellik dosyası adları = `docs/specs_faz6/ekler/evren_listesi.csv`'deki 135 MEMBER = `registry/oot/inputs/*.json` adları. Kaynak MANIFEST dizinleri aynı 135.
   - (b) Her dosyada 7 alan var. `status` ∈ {VERIFIED, CORRECTED, FILLED, MISSING}. MISSING ↔ `value` boş.
   - (c) Alan başına durum sayıları REPORT §1 tablosuyla birebir (sabit olarak yazılır):

     | Alan | VERIFIED | CORRECTED | FILLED | MISSING |
     |---|---|---|---|---|
     | `distribution_method` | 80 | 5 | 50 | 0 |
     | `price_stability_planned` | 99 | 0 | 36 | 0 |
     | `price_stability_days` | 93 | 0 | 42 | 0 |
     | `issuer_lockup_days` | 73 | 3 | 59 | 0 |
     | `shareholder_lockup_days` | 80 | 3 | 52 | 0 |
     | `sector` | 89 | 0 | 46 | 0 |
     | `participation_index_eligible` | 7 | 0 | 24 | 104 |

   - (d) Dolu her alan için:
     - alanın `source_id`'si o üyenin kaynak MANIFEST'inin `documents` listesinde var;
     - alanın `source_sha256`'sı MANIFEST'teki `sha256` ile aynı;
     - `published_at` (Europe/Istanbul tarihi) `registry/oot/inputs/<T>.json`'daki ilk işlem gününden önce.
   - (e) `SHA256SUMS` bütün satırlarda tutuyor. Dizinde listede olmayan dosya yok.
   - (f) Yeni dosyalarda `test_registry_carries_no_outcome_fields`'ın `OUTCOME_KEYS` anahtarlarından hiçbiri yok. Bu, var olan bekçiyle de sınanır; burada doğrudan yeni dizinler için tekrarlanır.
   - (g) Mutasyon gösterimi (geçici kopyada, repo dosyası değişmez):
     - bir dosyada bir kaynağın yayım zamanı ilk işlem gününe çekilince (d) kırmızı;
     - bir özellik dosyasında tek bayt değişince (e) kırmızı.
     
     Çıktı `docs/faz7/prospectus/intake_mutation.txt`.
5. **PROVENANCE:** `docs/PROVENANCE.md`'nin sonuna yalnız ekleme olarak yeni bölüm "Faz 7: izahname alanları (135 eski kohort üyesi)". İçeriği:
   - kaynak dizin, doğrulayıcı görevi, tarih;
   - dosya sayıları ve toplam bayt;
   - `SHA256SUMS`'ın sha'sı;
   - PDF'lerin repo dışında olduğu;
   - REPORT §8'deki açık tanım noktası (`shareholder_lockup_days` toplama kuralı, `components`'ten yeniden hesaplanabilir).
6. **Testler:**
   - Önce `.venv/bin/pytest -q tests/test_faz7_prospectus.py tests/test_outcome_guard.py`.
   - Sonra tam `.venv/bin/pytest -q`.
   - Temizlik bekçileri (`registry` ya da `data` için `git status` boş olmalı diyenler) yalnız bu görevin commit edilmemiş yeni yolları yüzünden kırmızıysa: deselect → commit → deselect'siz tam koşu. Başka bir kırmızı varsa DUR.
   - Var olan bir test `registry/oot/` alt dizinlerini sabit bir listeyle sayıyor ve yeni dizin yüzünden kırmızıysa DUR ve raporla. O testi gevşetme.
   - Sayılar ve süreler `docs/faz7/prospectus/intake_test_runs.txt`'ye.
7. **Commit:**
   ```
   git add registry/oot/candidate_features_faz7 registry/oot/source_docs_faz7 docs/faz7/prospectus tests/test_faz7_prospectus.py docs/PROVENANCE.md docs/prompts/FAZ7_PROSPECTUS_INTAKE.md docs/prompts/FAZ7_CODEX_PROSPECTUS_B1.md docs/prompts/FAZ7_CODEX_PROSPECTUS_B2.md docs/prompts/FAZ7_CODEX_PROSPECTUS_B3.md docs/prompts/FAZ7_CODEX_PROSPECTUS_B4.md docs/prompts/FAZ7_VERIFY_PROSPECTUS.md
   git commit -m "BORSAI_FAZ7_PROSPECTUS: verified prospectus fields for the 135 pre-H99 members (7 fields, source manifests, verification report)" -- registry/oot/candidate_features_faz7 registry/oot/source_docs_faz7 docs/faz7/prospectus tests/test_faz7_prospectus.py docs/PROVENANCE.md docs/prompts/FAZ7_PROSPECTUS_INTAKE.md docs/prompts/FAZ7_CODEX_PROSPECTUS_B1.md docs/prompts/FAZ7_CODEX_PROSPECTUS_B2.md docs/prompts/FAZ7_CODEX_PROSPECTUS_B3.md docs/prompts/FAZ7_CODEX_PROSPECTUS_B4.md docs/prompts/FAZ7_VERIFY_PROSPECTUS.md
   ```
   `git add -A` yok. `index.lock` hatasında 10 saniye bekle, yeniden dene; kilidi silme.
8. Commit'ten sonra deselect'siz tam `.venv/bin/pytest -q`. Sonucu `intake_test_runs.txt`'ye ekleme; dosya commit'lendi. Raporda ver.

## Dokunulmayacaklar
`borsai/`, `models/`, `scores/`, `data/`, `app/`, `docs/specs*`, `registry/` (yeni iki dizin hariç), `tests/` (yeni test dosyası hariç), `experiments/`, `docs/MODELS.md`, `docs/fable_faz7_audit/`, `~/Desktop/BorsAi_codex/` (salt okunur).

## Teslim raporu
- Commit hash'i ve `git show --stat` özeti.
- Kopyalanan dosya sayıları ve baytlar; `SHA256SUMS`'ın sha'sı.
- Test sayıları: hedefli, deselect'li ve deselect'siz tam koşu (commit sonrası).
- Mutasyon çıktısı.
- DUR olduysa neden.

## Kabul kapısı
- **K1** 135 + 135 dosya kaynağıyla bayt-eşit; PDF yok; OPEN/SEALED ayrımı hiçbir yerde yazılı değil.
- **K2** `test_faz7_prospectus.py` (a)–(f) yeşil; (g) mutasyonları kırmızı gösterildi.
- **K3** Commit sonrası tam pytest yeşil. Yalnız izinli yollar commit'lendi.

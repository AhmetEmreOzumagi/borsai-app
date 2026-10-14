# Faz 7: izahname alanları (eski kohortun 135 üyesi)

Eski kohortun (2020-01-01…2023-09-21 arası listelenen, `docs/specs_faz6/ekler/evren_listesi.csv`'deki 135 MEMBER) listeleme öncesi 7 izahname alanı, resmi belgelerden doğrulanmış ve doldurulmuş hâliyle:
`distribution_method`, `price_stability_planned`, `price_stability_days`, `issuer_lockup_days`, `shareholder_lockup_days`, `sector`, `participation_index_eligible`.

## Kaynak ve doğrulayıcı
- İlk çıkarım: Codex + GPT-6 Astra (görevler `docs/prompts/FAZ7_CODEX_PROSPECTUS_B1..B4.md`).
- Doğrulama ve doldurma: Claude Code (Opus 5.5), görev `docs/prompts/FAZ7_VERIFY_PROSPECTUS.md` (BORSAI_FAZ7_VERIFY_PROSPECTUS_20260925). Çıktı `~/Desktop/BorsAi_codex/verified_faz7/` altında üretildi.
- Repoya alım: `docs/prompts/FAZ7_PROSPECTUS_INTAKE.md`. Bu görevde hiçbir değer değiştirilmedi; dosyalar bayt-eşit kopyadır.

## Yerleşim
| Yol | İçerik |
|---|---|
| `registry/oot/candidate_features_faz7/<T>.json` | 135 özellik dosyası (7 alan, alan başına durum, kaynak, sayfa, alıntı) |
| `registry/oot/candidate_features_faz7/SHA256SUMS` | Bu görevin bütün dosyalarının sha256 pini (sha256sum biçimi) |
| `registry/oot/source_docs_faz7/<T>/MANIFEST.json` | 135 kaynak belge listesi (URL, KAP bildirimi, yayın zamanı, sha256, bayt, sayfa, metin katmanı) |
| `docs/faz7/prospectus/REPORT.md` | Doğrulama raporu (kapsama, Codex doğruluk oranı, eşleme kuralları, boşluklar) |
| `docs/faz7/prospectus/coverage.csv`, `verification_log.jsonl` | Ticker × alan durumu; karar günlüğü |
| `docs/faz7/prospectus/EXPOSURE.md` | Maruziyet kaydı (bayt-eşit kopya) |
| `docs/faz7/prospectus/scripts/`, `logs/` | Doğrulayıcının betikleri ve kayıtları, olduğu gibi |
| `docs/faz7/prospectus/intake_mutation.txt`, `intake_test_runs.txt` | Bekçi mutasyon gösterimi; alım görevinin test koşuları |

Satır sonu: `coverage.csv` kaynakta CRLF'ydi. Depo `.gitattributes` (`* text=auto eol=lf`) commit'te LF'ye çevireceği için pin taze klonda tutsun diye dosya baştan LF'ye çevrildi (yalnız satır sonu; kaynak sha256 `47fc7b6b9889d2a3f3604fe513a5cfb0d4299c28ecde727d8c9f83532bdd8831`, bu kopya `94cccfd34c8133c5ee84e1fbaf04338f84b68b57eb69963eeaa8722825a38661`). Diğer bütün dosyalar kaynakla bayt-eşittir.

## PDF'ler repoda değil
İzahname ve ek PDF'leri (1.284 belge, 3,19 GB) repoya alınmadı. Her belgenin resmi URL'si ve sha256'sı MANIFEST'te (`documents[].url`, `sha256`, `bytes`); belge yeniden indirilip sha256 ile eşlenebilir. Özellik dosyalarındaki `source_file` yolları doğrulayıcının çalışma ağacına görelidir (`source_docs/<T>/…`); bu ağaç repoda yoktur, eşleme `source_id` ile MANIFEST üzerinden yapılır.

## Alan tanımları
Değer biçimi, kategori eşleme kuralları, süre dönüşümü ve `shareholder_lockup_days` toplama kuralı için `REPORT.md` §3'e bakın. Toplama kuralı `components` listesinden yeniden hesaplanabilir (§8).

## Bekçi
`tests/test_faz7_prospectus.py`: dosya kümeleri 135 MEMBER ile aynı; 7 alan ve durum; alan başına durum sayıları REPORT §1 ile birebir; her dolu alanın kaynağı MANIFEST'te, sha256'sı eşit ve yayın zamanı ilk işlem gününden önce; `SHA256SUMS` tutuyor ve dizinde pinsiz dosya yok; sonuç alanı yok.

(C) özelliklerini tasarlayan oturum `EXPOSURE.md`'yi okumaz; keşif yalnız H99 ve açık kümede yapılır, kasa üyelerinin özellik dosyaları keşifte açılmaz.

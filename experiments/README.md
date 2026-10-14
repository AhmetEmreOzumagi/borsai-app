# Deney günlüğü

`log.jsonl`: her backtest koşusu için bir satır (CLAUDE.md kural 4). Satırı `borsai/backtest.py` (`run_backtest`) koşunun sonunda kendisi ekler; günlüğe yazmadan backtest koşturan bir yol yoktur.

- Biçim: satır başına bir JSON nesnesi, UTF-8, LF.
- Alanlar: `model_id`, `spec_sha256`, `data_version_sha256`, `training_table_sha256`, `plan_id`, `folds_scorable`, `ledger_sha256` (fold ledger CSV'sinin sha256'sı), `metrics` (ufuk başına n, MAE, medyan AE, Brier, isabet), `started_at`, `finished_at`, `git_commit`, `borsai_dirty`, `borsai_source_sha256`, `context`; V1.5 için ayrıca `runtime`.
- Append-only: satırlar düzeltilmez ve silinmez. Hatalı bir koşu da günlükte kalır.
- Resmi koşu: `.venv/bin/python -m borsai.backtest` (varsayılan: bütün kayıtlı modeller).

Test paketi (`.venv/bin/pytest`) aynı `run_backtest` kodunu pytest'in geçici dizinindeki bir günlüğe yazarak koşar ve o günlüğe yazıldığını sınar. Neden: test koşuları dondurulmuş şartnameyi aynı veride kodu doğrulamak için yeniden çalıştırır, yeni bir varyant denemez; resmi günlüğe yazsalardı her test koşusu repoyu kirletirdi.

Faz 1A'daki koşular:
- `faz1a_acceptance_run`: port kabul testlerinden (1-3) önceki ilk tam koşu.
- `faz1a_golden`: kabul testleri geçtikten sonra `tests/reference/macos_golden/` altın ledger'larını üreten koşu. `docs/MODELS.md` bu ledger'lardan üretilir.

Faz 1B'deki koşular (`borsai.backtest.FAZ1B_RUNS`: yeni dokuz modelin kendi planındaki koşuları ve karşılaştırıldıkları basit kuralların PB ve tavan planlarındaki koşuları, 19 koşu; plan dışı koşuların satırında `run_key` vardır, ör. `base_train_median__pb`):
- `faz1b_acceptance_run`: kod ve testler tamamlandıktan sonraki ilk tam koşu; rapor bu koşunun ledger'larıyla yazıldı.
- `faz1b_golden`: kod son haline geldikten sonra `tests/reference/macos_golden_faz1b/` altın ledger'larını üreten koşu (`python -m borsai.backtest --suite faz1b --context faz1b_golden --write-golden`). `docs/MODELS.md` bunlardan üretilir.
- Yeni modellerin satırlarında ayrıca `spec_document` ve `spec_document_sha256` (docs/specs/ altındaki şartname dosyasının sha256'sı) bulunur.

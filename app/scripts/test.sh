#!/usr/bin/env bash
# Bütün uygulama testleri: bash app/scripts/test.sh
set -euo pipefail
cd "$(dirname "$0")/.."
. scripts/env.sh
if [ ! -d node_modules ]; then npm ci; fi
REPO="$(cd .. && pwd)"
# Ortam isteyen Rust testleri #[ignore]'dır: yalın `cargo test`'te "ignored" görünür, env yok diye
# sessizce "ok" dönmez. BORSAI_REPO isteyenler burada --include-ignored ile koşar; geçici klon isteyen
# beş e2e testi burada atlanır (adı birebir) ve betiklerde --ignored ile koşar:
#   freeze_flow, prepare_screens → tests/e2e_freeze_tmp_repo.sh · personal_isolation → tests/e2e_personal_isolation.sh
#   · post_d1_flow → tests/e2e_post_d1_tmp_repo.sh (EK 3 U69) · prepare_screens_p2 → scripts/screens_p2.sh (yalnız geliştirme)
# Yeni bir ortam isteyen test bu listeye girmezse burada env'siz koşar ve KIRMIZI olur (fail-closed).
(cd src-tauri && BORSAI_REPO="$REPO" cargo test --workspace -- --include-ignored \
  --exact --skip freeze_flow --skip prepare_screens --skip personal_isolation --skip post_d1_flow --skip prepare_screens_p2)
npm test
(cd "$REPO" && .venv/bin/pytest -q app/parity/test_gen_golden.py)
bash tests/golden_unchanged.sh

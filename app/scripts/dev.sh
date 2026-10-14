#!/usr/bin/env bash
# Uygulamayı geliştirme modunda açar: bash app/scripts/dev.sh
set -euo pipefail
cd "$(dirname "$0")/.."
. scripts/env.sh
if [ ! -d node_modules ]; then npm ci; fi
exec npm run tauri dev

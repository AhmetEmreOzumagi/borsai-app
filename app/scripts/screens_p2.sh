#!/usr/bin/env bash
# YALNIZ GELİŞTİRME: EK 3 P2 ekran görüntüleri (D1 sonrası sihirbazı ve satırı): bash app/scripts/screens_p2.sh [hedef_dizin]
# Varsayılan hedef docs/app/p2/ekran. Akış YALNIZ GEÇİCİ KLONDA koşar: betik `git clone --local` ile klon açar,
# `prepare_screens_p2` (e2e.rs) kurgusal SNTA1'in listeleme öncesi kaydını ve sentetik D_1 bültenleri + sonuç satırını
# klonda yazıp commit'ler; `npm run tauri dev -- --features snapshot` + VITE_BORSAI_DEMO_P2=1 demo'su repo kökünü klona
# çevirir, sihirbazla D1 sonrası kaydını (Python freeze --post-d1) klonda yazar ve görüntü alır. Uygulama verisi geçici
# dizindedir. Asıl repo'nun registry/ ve data/ ağaçları değişmez; betik sonunda bunu denetler.
set -euo pipefail
cd "$(dirname "$0")/.."
. scripts/env.sh
if [ ! -d node_modules ]; then npm ci; fi
REPO="$(cd .. && pwd)"
OUT="${1:-$REPO/docs/app/p2/ekran}"
TMP="$(mktemp -d)"
mkdir -p "$TMP/appdata" "$TMP/shots" "$OUT"
tree_shas() { (cd "$REPO" && find registry data -type f | LC_ALL=C sort | xargs shasum -a 256); }
tree_shas >"$TMP/before.txt"

CLONE="$TMP/clone"
git clone --local --quiet "$REPO" "$CLONE"
(cd src-tauri && BORSAI_E2E_REPO="$CLONE" BORSAI_E2E_DATA="$TMP/e2edata" BORSAI_E2E_PYTHON="$REPO/.venv/bin/python" \
  BORSAI_E2E_SCREENS=1 cargo test --test e2e prepare_screens_p2 -- --ignored --exact --nocapture)

BORSAI_DATA_DIR="$TMP/appdata" BORSAI_SNAPSHOT_DIR="$TMP/shots" VITE_BORSAI_DEMO=1 VITE_BORSAI_DEMO_P2=1 \
  VITE_BORSAI_DEMO_REPO="$CLONE" VITE_BORSAI_DEMO_PYTHON="$REPO/.venv/bin/python" \
  npm run tauri dev -- --features snapshot >"$TMP/dev.log" 2>&1 || true
if [ -f "$TMP/shots/zz_demo_error.png" ]; then
  echo "demo hata verdi: $TMP/shots/zz_demo_error.png ($TMP/dev.log)" >&2
  exit 1
fi
n=0
for f in "$TMP"/shots/*.png; do
  sips -Z 1200 "$f" --out "$OUT/$(basename "$f")" >/dev/null
  n=$((n + 1))
done
echo "klon: yazılan D1 sonrası kayıtları"
(cd "$CLONE" && GIT_OPTIONAL_LOCKS=0 git status --porcelain -- registry/post_d1)
tree_shas >"$TMP/after.txt"
if ! diff -u "$TMP/before.txt" "$TMP/after.txt"; then
  echo "KIRMIZI: asıl repo registry/ ya da data/ ağacı değişti (akış yalnız klonda koşmalıydı)" >&2
  exit 1
fi
echo "asıl repo registry/ ve data/ sha listesi öncesiyle aynı"
echo "$n görüntü: $OUT (ham: $TMP/shots)"

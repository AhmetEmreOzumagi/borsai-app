#!/usr/bin/env bash
# YALNIZ GELİŞTİRME: app/docs/screens/*.png'yi yeniden üretir: bash app/scripts/screens.sh
# `npm run tauri dev -- --features snapshot` + VITE_BORSAI_DEMO=1: src/dev/demo.ts gerçek düğmelere
# tıklar (repo modu, VEYAS girdileri, NETGL senaryosu, sicil ekranı, dondur sihirbazı), her adımda
# WKWebView görüntüsü alır, sonunda uygulamayı kapatır. Uygulama verisi geçici dizindedir
# (BORSAI_DATA_DIR); sahibinin gerçek uygulama verisine ve repo'nun data/ registry/ scores/
# dizinlerine yazılmaz. Pencere koşu boyunca öndedir.
#
# Doğruluk paneli (§3d) önce asıl repo'nun scores/scores.json'unu okur (salt okuma), sonra
# BORSAI_SCORES_FIXTURES altındaki sentetik dosyalara geçer (dev_scores_fixture; yalnız bu koşuda).
#
# DONDUR SİHİRBAZI YALNIZ GEÇİCİ KLONDA koşar: betik `git clone --local` ile bir klon açar, kurgusal
# SNTC3 kaynak belgelerini oraya kopyalar ve demo ikinci yarıda repo kökünü o klona çevirir. Asıl
# repo'nun registry/ ağacı değişmez; betik sonunda bunu denetler.
set -euo pipefail
cd "$(dirname "$0")/.."
. scripts/env.sh
if [ ! -d node_modules ]; then npm ci; fi
REPO="$(cd .. && pwd)"
TMP="$(mktemp -d)"
mkdir -p "$TMP/appdata" "$TMP/shots" docs/screens
reg_shas() { (cd "$REPO" && find registry -type f | LC_ALL=C sort | xargs shasum -a 256); }
reg_shas >"$TMP/reg_before.txt"

CLONE="$TMP/clone"
git clone --local --quiet "$REPO" "$CLONE"
(cd src-tauri && BORSAI_E2E_REPO="$CLONE" BORSAI_E2E_DATA="$TMP/e2edata" BORSAI_E2E_PYTHON="$REPO/.venv/bin/python" \
  BORSAI_E2E_SCREENS=1 cargo test --test e2e prepare_screens -- --ignored --exact --nocapture)

BORSAI_DATA_DIR="$TMP/appdata" BORSAI_SNAPSHOT_DIR="$TMP/shots" VITE_BORSAI_DEMO=1 \
  BORSAI_SCORES_FIXTURES="$(pwd)/tests/fixtures/scores" \
  VITE_BORSAI_DEMO_REPO="$CLONE" VITE_BORSAI_DEMO_PYTHON="$REPO/.venv/bin/python" \
  npm run tauri dev -- --features snapshot >"$TMP/dev.log" 2>&1 || true
if [ -f "$TMP/shots/zz_demo_error.png" ]; then
  echo "demo hata verdi: $TMP/shots/zz_demo_error.png ($TMP/dev.log)" >&2
  exit 1
fi
n=0
for f in "$TMP"/shots/*.png; do
  sips -Z 1200 "$f" --out "docs/screens/$(basename "$f")" >/dev/null
  n=$((n + 1))
done
reg_shas >"$TMP/reg_after.txt"
if ! diff -u "$TMP/reg_before.txt" "$TMP/reg_after.txt"; then
  echo "KIRMIZI: asıl repo registry/ ağacı değişti (sihirbaz yalnız klonda koşmalıydı)" >&2
  exit 1
fi
echo "asıl repo registry/ sha listesi öncesiyle aynı"
echo "$n görüntü: app/docs/screens/ (ham: $TMP/shots)"

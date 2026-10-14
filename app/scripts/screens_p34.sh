#!/usr/bin/env bash
# YALNIZ GELİŞTİRME: EK 3 P3/P4 ekran görüntüleri: bash app/scripts/screens_p34.sh [çıktı dizini]
# `npm run tauri dev -- --features snapshot` + VITE_BORSAI_DEMO=1 VITE_BORSAI_DEMO_P34=1: src/dev/demo.ts (p34Steps) repo
# modunda NETGL ve VEYAS girdileriyle "Düşüş (D10)" kartını, NETGL arz sayfasını ve Doğruluk sekmesindeki zaman-dışı paneli
# (açık küme, kasa, toplam, D1 sonrası, OOT_RETRO) görüntüler. Asıl repo SALT OKUNUR: uygulama verisi geçici dizindedir
# (BORSAI_DATA_DIR); betik sonunda registry/ ve data/ sha listelerinin değişmediğini denetler. Panel yalnız açık küme kodlarını
# gösterir (K-P3-1). Pencere koşu boyunca öndedir.
set -euo pipefail
cd "$(dirname "$0")/.."
. scripts/env.sh
if [ ! -d node_modules ]; then npm ci; fi
REPO="$(cd .. && pwd)"
OUT="${1:-$REPO/docs/app/p34/ekran}"
TMP="$(mktemp -d)"
mkdir -p "$TMP/appdata" "$TMP/shots" "$OUT"
shas() { (cd "$REPO" && find registry data -type f | LC_ALL=C sort | xargs shasum -a 256); }
shas >"$TMP/before.txt"
BORSAI_DATA_DIR="$TMP/appdata" BORSAI_SNAPSHOT_DIR="$TMP/shots" VITE_BORSAI_DEMO=1 VITE_BORSAI_DEMO_P34=1 \
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
shas >"$TMP/after.txt"
if ! diff -u "$TMP/before.txt" "$TMP/after.txt"; then
  echo "KIRMIZI: asıl repo registry/ ya da data/ ağacı değişti" >&2
  exit 1
fi
echo "asıl repo registry/ ve data/ sha listesi öncesiyle aynı"
echo "$n görüntü: $OUT (ham: $TMP/shots)"

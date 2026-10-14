#!/usr/bin/env bash
# YALNIZ GELİŞTİRME: sade görünüm (FAZ9_APP_UI) ekran görüntüleri: bash app/scripts/screens_v2.sh [çıktı dizini]
# `npm run tauri dev -- --features snapshot` + VITE_BORSAI_DEMO=1 VITE_BORSAI_DEMO_V2=1: src/dev/demo.ts (v2Steps) gerçek
# düğmelere tıklar: bağımsız mod boş durumu, repo modu (öneri), Monitör, Yeni arz girişi (NETGL, talep sonrası), Tahmin sonucu
# j = 0 ve j = 3, kişisel kayıt, Kayıtlarım, Analiz NETGL (gözlenen j = 3, kırılma kartı), Model performansı, Sicil, dondur
# sihirbazının 1. adımı (yalnız ön koşul denetimi) ve Ayrıntılı görünüme geçiş/dönüş. Asıl repo SALT OKUNUR: uygulama verisi
# geçici dizindedir (BORSAI_DATA_DIR); betik sonunda registry/ ve data/ sha listelerinin değişmediğini denetler. Eski
# app/docs/screens/*.png'ye dokunmaz. Pencere koşu boyunca öndedir.
set -euo pipefail
cd "$(dirname "$0")/.."
. scripts/env.sh
if [ ! -d node_modules ]; then npm ci; fi
REPO="$(cd .. && pwd)"
OUT="${1:-docs/screens/v2}"
TMP="$(mktemp -d)"
mkdir -p "$TMP/appdata" "$TMP/shots" "$OUT"
shas() { (cd "$REPO" && find registry data -type f | LC_ALL=C sort | xargs shasum -a 256); }
shas >"$TMP/before.txt"
BORSAI_DATA_DIR="$TMP/appdata" BORSAI_SNAPSHOT_DIR="$TMP/shots" VITE_BORSAI_DEMO=1 VITE_BORSAI_DEMO_V2=1 \
  npm run tauri dev -- --features snapshot >"$TMP/dev.log" 2>&1 || true
if [ -f "$TMP/shots/zz_demo_error.png" ]; then
  echo "demo hata verdi: $TMP/shots/zz_demo_error.png ($TMP/dev.log)" >&2
  exit 1
fi
n=0
for f in "$TMP"/shots/*.png; do
  sips -Z 1440 "$f" --out "$OUT/$(basename "$f")" >/dev/null
  n=$((n + 1))
done
shas >"$TMP/after.txt"
if ! diff -u "$TMP/before.txt" "$TMP/after.txt"; then
  echo "KIRMIZI: asıl repo registry/ ya da data/ ağacı değişti" >&2
  exit 1
fi
echo "asıl repo registry/ ve data/ sha listesi öncesiyle aynı"
echo "$n görüntü: $OUT (ham: $TMP/shots)"

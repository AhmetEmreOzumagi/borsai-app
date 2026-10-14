#!/usr/bin/env bash
# Kişisel kayıt ve kullanıcı beyanı izolasyonu (SPEC_APP §5.4 U39).
#
#   bash app/tests/e2e_personal_isolation.sh
#
# Geçici klonda: şeride beyan girilir, kişisel kayıt saklanır, resmi kayıt görüntülenir. Ardından
# `data/outcomes`, `registry` ve `scores` ağaçlarının sha listeleri öncesiyle karşılaştırılır; beyan
# yalnız `<app_data_dir>/scenarios/*.json` içindedir. Statik tarama: `observed_streak_user` skor,
# sicil ve dondur okuyucularında hiç geçmez. Ağ yok.
# FAZ9_SNAPSHOT K-SNAP-4 (adım 2b): kişisel modda (repo ayarı boş) gömülü sicil anlık görüntüsü açılışta
# `<app_data_dir>/snapshot/<sha7>/` altına yazılır; dört ekran ve kırılma kartı açılır, beyanlı kişisel kayıt
# saklanır; anlık görüntü dosyalarının sha'ları değişmez, `scenarios/` dışına yazma olmaz, anlık görüntüye
# kişisel kayıt yazılamaz. Betik manifesti bağımsız olarak da (shasum) doğrular.
set -euo pipefail
cd "$(dirname "$0")/.."
. scripts/env.sh
REPO="$(cd .. && pwd)"
PY="$REPO/.venv/bin/python"

reg_shas() { (cd "$REPO" && find registry -type f | LC_ALL=C sort | xargs shasum -a 256); }

TMP="$(mktemp -d)"
CLONE="$TMP/repo"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

echo "=== 0. asıl repo registry sha listesi (öncesi) ==="
reg_shas >"$TMP/reg_before.txt"
echo "$(wc -l <"$TMP/reg_before.txt" | tr -d ' ') dosya"

echo "=== 1. geçici klon ==="
git clone --local --quiet "$REPO" "$CLONE"
(cd "$CLONE" && "$PY" -c 'import borsai, os, sys
p = os.path.realpath(borsai.__file__)
print("borsai.__file__ =", p)
sys.exit(0 if p.startswith(os.path.realpath(sys.argv[1])) else 1)' "$CLONE")

echo "=== 2. beyan + kişisel kayıt + resmi kayıt görüntüleme ==="
(cd src-tauri && BORSAI_E2E_REPO="$CLONE" BORSAI_E2E_DATA="$TMP/appdata" BORSAI_E2E_PYTHON="$PY" \
  cargo test --test e2e personal_isolation -- --ignored --exact --nocapture --test-threads=1)

echo "=== 2b. kişisel mod: gömülü sicil anlık görüntüsü (K-SNAP-4) ==="
SNAPDATA="$TMP/appdata_snap"
(cd src-tauri && BORSAI_E2E_SNAP_DATA="$SNAPDATA" \
  cargo test --test e2e personal_snapshot_isolation -- --exact --nocapture --test-threads=1)
SNAPDIR="$(find "$SNAPDATA/snapshot" -mindepth 1 -maxdepth 1 -type d)"
if [ "$(echo "$SNAPDIR" | wc -l | tr -d ' ')" != "1" ] || [ ! -f "$SNAPDIR/SNAPSHOT_MANIFEST.tsv" ]; then
  echo "KIRMIZI: anlık görüntü dizini tek değil ya da manifest yok: $SNAPDIR" >&2
  exit 1
fi
echo "anlık görüntü dizini: <app_data_dir>/snapshot/$(basename "$SNAPDIR")"
OUTSIDE="$(cd "$SNAPDATA" && find . -type f ! -path './snapshot/*' ! -path './scenarios/*')"
if [ -n "$OUTSIDE" ]; then
  echo "KIRMIZI: uygulama verisinde snapshot/ ve scenarios/ dışında dosya: $OUTSIDE" >&2
  exit 1
fi
echo "uygulama verisi: yalnız snapshot/ ve scenarios/ ($(cd "$SNAPDATA" && find scenarios -type f | wc -l | tr -d ' ') kişisel kayıt)"
# manifest bağımsız doğrulama: her satırın sha256'sı diskteki dosyayla aynı; dosya kümesi = manifest + manifestin kendisi
BAD=0
while IFS="$(printf '\t')" read -r REL SHA BYTES; do
  GOT="$(shasum -a 256 "$SNAPDIR/$REL" | cut -d' ' -f1)"
  [ "$GOT" = "$SHA" ] || { echo "KIRMIZI: $REL sha uyuşmuyor" >&2; BAD=1; }
done <"$SNAPDIR/SNAPSHOT_MANIFEST.tsv"
NMAN="$(wc -l <"$SNAPDIR/SNAPSHOT_MANIFEST.tsv" | tr -d ' ')"
NDISK="$(find "$SNAPDIR" -type f | wc -l | tr -d ' ')"
[ "$NDISK" = "$((NMAN + 1))" ] || { echo "KIRMIZI: diskte $NDISK dosya, manifest $NMAN satır" >&2; BAD=1; }
[ "$BAD" = "0" ] || exit 1
echo "anlık görüntü: manifestteki $NMAN dosyanın sha256'sı diskteki dosyayla aynı (shasum); fazla dosya yok"
if grep -rl observed_streak_user "$SNAPDIR" >/dev/null 2>&1; then
  echo "KIRMIZI: beyan alanı anlık görüntüde" >&2
  exit 1
fi
echo "anlık görüntüde observed_streak_user: YOK"

echo "=== 3. geçici klon: sonuç, sicil ve skor ağaçları değişmedi ==="
DIRTY="$(cd "$CLONE" && GIT_OPTIONAL_LOCKS=0 git status --porcelain -- data registry scores)"
if [ -n "$DIRTY" ]; then
  echo "KIRMIZI: geçici klonda data/ registry/ scores/ değişti:" >&2
  echo "$DIRTY" >&2
  exit 1
fi
echo "geçici klon git status --porcelain -- data registry scores: BOŞ"

echo "=== 4. beyan yalnız uygulama verisinde ==="
HITS="$(grep -rl observed_streak_user "$CLONE/registry" "$CLONE/data" "$CLONE/scores" 2>/dev/null || true)"
if [ -n "$HITS" ]; then
  echo "KIRMIZI: beyan alanı repo ağacında: $HITS" >&2
  exit 1
fi
echo "registry/ data/ scores/ içinde observed_streak_user: YOK"
grep -l observed_streak_user "$TMP"/appdata/scenarios/*.json | sed "s|$TMP|<app_data_dir>|"

echo "=== 5. statik tarama: observed_streak_user'ı kim okuyor ==="
MAP="$(cd "$REPO" && grep -rl observed_streak_user app/src app/src-tauri/src | LC_ALL=C sort)"
echo "$MAP"
# Beyan yalnız senaryo (kişisel kayıt) yolunda geçebilir: Rust'ta tek modül, ön uçta senaryo taşıyan
# sözleşme/durum/ekran dosyaları. Tarama bu kümenin ALT KÜMESİ olmalı.
ALLOWED="app/src-tauri/src/commands/scenario.rs
app/src/api.ts
app/src/screens/results.ts
app/src/screens/scenarios.ts
app/src/state.ts
app/src/types.ts"
EXTRA="$(comm -23 <(echo "$MAP") <(echo "$ALLOWED" | LC_ALL=C sort))"
if [ -n "$EXTRA" ]; then
  echo "KIRMIZI: beyan alanı beklenmeyen bir modülde geçiyor (skor/sicil/dondur okuyucuları bu alanı okumaz):" >&2
  echo "$EXTRA" >&2
  exit 1
fi
for f in app/src-tauri/src/commands/scores.rs app/src-tauri/src/commands/registry.rs app/src-tauri/src/commands/freeze.rs app/src-tauri/src/commands/parity.rs; do
  if grep -q observed_streak_user "$REPO/$f"; then
    echo "KIRMIZI: $f beyan alanını okuyor" >&2
    exit 1
  fi
done
echo "scores / registry / freeze / parity okuyucuları beyan alanını okumuyor"

echo "=== 6. ASIL REPO denetimi ==="
reg_shas >"$TMP/reg_after.txt"
if ! diff -u "$TMP/reg_before.txt" "$TMP/reg_after.txt"; then
  echo "KIRMIZI: asıl repo registry/ ağacı değişti" >&2
  exit 1
fi
echo "asıl repo registry/ sha listesi öncesiyle BİREBİR AYNI ($(wc -l <"$TMP/reg_after.txt" | tr -d ' ') dosya)"
STATUS="$(cd "$REPO" && GIT_OPTIONAL_LOCKS=0 git status --porcelain -- registry data scores)"
if [ -n "$STATUS" ]; then
  echo "KIRMIZI: asıl repo git status --porcelain -- registry data scores boş değil:" >&2
  echo "$STATUS" >&2
  exit 1
fi
echo "asıl repo git status --porcelain -- registry data scores: BOŞ"
echo "=== e2e_personal_isolation: YEŞİL ==="

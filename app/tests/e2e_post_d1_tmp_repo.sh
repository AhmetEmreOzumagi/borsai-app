#!/usr/bin/env bash
# D1 sonrası kayıt sihirbazı uçtan uca (SPEC_APP EK 3 §6.6, §10.2 U69).
#
#   bash app/tests/e2e_post_d1_tmp_repo.sh
#
# Akış GEÇİCİ BİR KLONA karşı koşar (`git clone --local`): asıl repo'nun registry/ ve data/ ağaçlarına hiçbir şey yazılmaz ve
# betik bunu kendisi denetler. Kurgusal arz SNTA1: listeleme öncesi kayıt (mevcut dondur akışı), sentetik D_1 bültenleri
# (THB + THM zip, MANIFEST satırı) ve sonuç satırı (h = 1 OK) yalnız klonda; ardından uygulamanın ön koşul, Python
# `freeze --post-d1` çağrısı, Rust paritesi, komut blokları ve iptal yolları. Ağ yok.
set -euo pipefail
cd "$(dirname "$0")/.."
. scripts/env.sh
REPO="$(cd .. && pwd)"
PY="$REPO/.venv/bin/python"

tree_shas() { (cd "$REPO" && find registry data -type f | LC_ALL=C sort | xargs shasum -a 256); }

TMP="$(mktemp -d)"
CLONE="$TMP/repo"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

echo "=== 0. asıl repo registry/ ve data/ sha listesi (öncesi) ==="
tree_shas >"$TMP/before.txt"
echo "$(wc -l <"$TMP/before.txt" | tr -d ' ') dosya"

echo "=== 1. geçici klon ==="
git clone --local --quiet "$REPO" "$CLONE"

echo "=== 2. PYTHONPATH sızıntısı denetimi ==="
if ! (cd "$CLONE" && "$PY" -c 'import borsai, os, sys
p = os.path.realpath(borsai.__file__)
print("borsai.__file__ =", p)
sys.exit(0 if p.startswith(os.path.realpath(sys.argv[1])) else 1)' "$CLONE"); then
  echo "DUR: borsai geçici klon altından yüklenmiyor" >&2
  exit 1
fi

echo "=== 3. U69: uygulama komutları (tauri CLI'siz; aynı Rust komut fonksiyonları) ==="
(cd src-tauri && BORSAI_E2E_REPO="$CLONE" BORSAI_E2E_DATA="$TMP/appdata" BORSAI_E2E_PYTHON="$PY" \
  cargo test --test e2e post_d1_flow -- --ignored --exact --nocapture --test-threads=1)

echo "=== 4. geçici klon: yazılan dosyalar (git status) ==="
(cd "$CLONE" && GIT_OPTIONAL_LOCKS=0 git status --porcelain -- registry data)

echo "=== 5. ASIL REPO denetimi ==="
tree_shas >"$TMP/after.txt"
if ! diff -u "$TMP/before.txt" "$TMP/after.txt"; then
  echo "KIRMIZI: asıl repo registry/ ya da data/ ağacı değişti" >&2
  exit 1
fi
echo "asıl repo registry/ ve data/ sha listesi öncesiyle BİREBİR AYNI ($(wc -l <"$TMP/after.txt" | tr -d ' ') dosya)"
STATUS="$(cd "$REPO" && GIT_OPTIONAL_LOCKS=0 git status --porcelain -- registry data)"
if [ -n "$STATUS" ]; then
  echo "KIRMIZI: asıl repo git status --porcelain -- registry data boş değil:" >&2
  echo "$STATUS" >&2
  exit 1
fi
echo "asıl repo GIT_OPTIONAL_LOCKS=0 git status --porcelain -- registry data: BOŞ"
echo "=== e2e_post_d1_tmp_repo: YEŞİL ==="

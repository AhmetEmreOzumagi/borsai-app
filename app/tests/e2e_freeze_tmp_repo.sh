#!/usr/bin/env bash
# Dondur akışı uçtan uca (SPEC_APP §5.4: U28, U29, U30, U31, U32).
#
#   bash app/tests/e2e_freeze_tmp_repo.sh
#
# Akış GEÇİCİ BİR KLONA karşı koşar (`git clone --local`): asıl repo'nun registry/ ağacına hiçbir şey
# yazılmaz ve betik bunu kendisi denetler. Her Python çağrısında cwd = klon; ilk `freeze`'den ÖNCE
# `borsai.__file__`'in klon altında olduğu doğrulanır (PYTHONPATH sızıntısı asıl repoya kayıt yazdırır).
# Ağ yok.
set -euo pipefail
cd "$(dirname "$0")/.."
. scripts/env.sh
REPO="$(cd .. && pwd)"
PY="$REPO/.venv/bin/python"
REF="${BORSAI_REG_BEFORE:-/tmp/reg_before.txt}"

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
echo "klon: $CLONE"

echo "=== 2. PYTHONPATH sızıntısı denetimi (ilk freeze'den ÖNCE) ==="
if ! (cd "$CLONE" && "$PY" -c 'import borsai, os, sys
p = os.path.realpath(borsai.__file__)
print("borsai.__file__ =", p)
sys.exit(0 if p.startswith(os.path.realpath(sys.argv[1])) else 1)' "$CLONE"); then
  echo "DUR: borsai geçici klon altından yüklenmiyor; kayıt asıl repoya yazılabilirdi." >&2
  exit 1
fi

echo "=== 3. uygulama komutları (tauri CLI'siz; aynı Rust komut fonksiyonları) ==="
(cd src-tauri && BORSAI_E2E_REPO="$CLONE" BORSAI_E2E_DATA="$TMP/appdata" BORSAI_E2E_PYTHON="$PY" \
  cargo test --test e2e freeze_flow -- --ignored --exact --nocapture --test-threads=1)

echo "=== 4. U29: kişisel kayıt sicile düşse bile skorlanamaz (record_type yok); U30: iptal sonrası active_records ==="
SCEN="$(ls "$TMP"/appdata/scenarios/*.json | head -1)"
cp "$SCEN" "$CLONE/registry/records/SNTA1/kisisel_kayit.json"
# İptal kaydı dosyadan bulunur (e2e iki tahmin kaydı + bir iptal kaydı yazar); iptal ettiği dosya
# Python active_records'ta YOK ve etkin kayıt tam 1 (PB kaydı).
(cd "$CLONE" && "$PY" -c 'import json, pathlib
from borsai import freeze as f
recs = [p.name for p, _ in f.active_records("SNTA1")]
assert "kisisel_kayit.json" not in recs, recs
print("U29 active_records(SNTA1) =", len(recs), recs)
print("U29 kişisel kayıt dosyası sayılmadı: record_type yok")
docs = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(pathlib.Path("registry/records/SNTA1").glob("*.json"))}
canc = [(n, d["cancels"]["file"]) for n, d in docs.items() if d.get("record_type") == "CANCELLATION"]
assert len(canc) == 1, ("tek iptal kaydı bekleniyor", canc)
name, cancelled = canc[0]
assert cancelled in docs and docs[cancelled].get("record_type") == "PREDICTION", (cancelled, sorted(docs))
assert cancelled not in recs, ("iptal edilen kayıt active_records içinde", cancelled, recs)
assert len(recs) == 1, ("etkin kayıt sayısı 1 olmalı", recs)
print("U30 iptal kaydı", name, "->", cancelled, "; active_records içinde değil; etkin kayıt =", len(recs), recs)')
rm "$CLONE/registry/records/SNTA1/kisisel_kayit.json"

echo "=== 4b. ekran görüntüsü hazırlığı (prepare_screens; #[ignore], yalnız geçici klonda) ==="
(cd src-tauri && BORSAI_E2E_REPO="$CLONE" BORSAI_E2E_DATA="$TMP/appdata_screens" BORSAI_E2E_PYTHON="$PY" \
  BORSAI_E2E_SCREENS=1 cargo test --test e2e prepare_screens -- --ignored --exact --nocapture)

echo "=== 5. geçici klon: yazılan sicil dosyaları ==="
(cd "$CLONE" && GIT_OPTIONAL_LOCKS=0 git status --porcelain -- registry)

echo "=== 6. ASIL REPO denetimi ==="
reg_shas >"$TMP/reg_after.txt"
if ! diff -u "$TMP/reg_before.txt" "$TMP/reg_after.txt"; then
  echo "KIRMIZI: asıl repo registry/ ağacı değişti" >&2
  exit 1
fi
echo "asıl repo registry/ sha listesi öncesiyle BİREBİR AYNI ($(wc -l <"$TMP/reg_after.txt" | tr -d ' ') dosya)"
if [ -f "$REF" ]; then
  if diff -u "$REF" "$TMP/reg_after.txt" >/dev/null; then
    echo "görev başındaki taban listeyle ($REF) de aynı"
  else
    echo "KIRMIZI: $REF ile ayrışıyor" >&2
    diff -u "$REF" "$TMP/reg_after.txt" >&2 || true
    exit 1
  fi
fi
STATUS="$(cd "$REPO" && GIT_OPTIONAL_LOCKS=0 git status --porcelain -- registry)"
if [ -n "$STATUS" ]; then
  echo "KIRMIZI: asıl repo git status --porcelain -- registry boş değil:" >&2
  echo "$STATUS" >&2
  exit 1
fi
echo "asıl repo GIT_OPTIONAL_LOCKS=0 git status --porcelain -- registry: BOŞ"
echo "=== e2e_freeze_tmp_repo: YEŞİL ==="

#!/usr/bin/env bash
# U46 (SPEC_APP EK 2 §3.5) + U55 (EK 3 §10.1) + EK 3 P2 (§6.4) + U80 (EK 3 §10.4, P4): eski altın dosyalar BAYT-EŞİT kalır.
#
#   bash app/tests/golden_unchanged.sh
#
# Tabanlar: 0b67f5d (BORSAI_FAZ3_S1, altın vektörlerin ilk hâli) ve 7133991 (EK 2 P1 sonrası son pin: üç tavan
# yolu dosyası, koşullu dosyaları ve 31 satırlık yamalı dosya). Denetlenenler:
#   1. 16 eski `golden/<model_id>.jsonl` dosyası 0b67f5d ile bayt bayt aynı,
#   2. üç tavan yolu dosyası ve üç koşullu dosya 7133991 ile bayt bayt aynı,
#   3. `golden/_patched_params.jsonl`'ın İLK 19 satırı 0b67f5d ile, İLK 31 satırı 7133991 ile bayt-eşit,
#   4. `parity/dec_cases.json`'ın eski bölümleri (0b67f5d'nin 9 bölümü ve 7133991'in `limit_path`'i) bayt-eşit,
#   5. (EK 3 P2) dört v1 dosyası d01daa4 (P1 A2) ile bayt bayt aynı; `_patched_params.jsonl`'ın İLK 43 satırı d01daa4 ile
#      bayt-eşit (D1 sonrası yamalı satırlar yalnız sona eklenir); `dec_cases.json` d01daa4 bölümleri aynı,
#   6. (EK 3 P4, U80) mevcut bütün altın `.jsonl` dosyaları (23 model + 3 koşullu + `post_d1_hazard_v0`) 0041dc9 (P2 B2) ile
#      bayt bayt aynı; `_patched_params.jsonl`'ın İLK 51 satırı 0041dc9 ile bayt-eşit ((C) yamalı satırları yalnız sona
#      eklenir); `dec_cases.json` 0041dc9 bölümleri aynı,
#   7. MANIFEST.json ve dört (C) dosyası DEĞİŞİR (beklenen; yalnız bilgi olarak yazdırılır).
# Ağ yok, yazma yok.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$(cd .. && pwd)"
BASE="${BORSAI_GOLDEN_BASE:-0b67f5d}"
BASE2="${BORSAI_GOLDEN_BASE2:-7133991}"
BASE3="${BORSAI_GOLDEN_BASE3:-d01daa4}"
BASE4="${BORSAI_GOLDEN_BASE4:-0041dc9}"
PY="$REPO/.venv/bin/python"

OLD_MODELS=(
  v1_5_h99 base_always_ceiling base_train_median base_train_mean base_zero base_rate base_last10_rate
  v1_6_h99 v1_5_market20_v0 pb_v0 ceiling_hazard_v0 'ceiling_hazard_v0@INF' pb_ceiling_v0 'pb_ceiling_v0@INF'
  base_km_expanding base_km_last10
)
PATH_MODELS=(ceiling_path_v0 'ceiling_path_v0@INF' pb_ceiling_path_v0)
V1_MODELS=(ceiling_hazard_v1_clip ceiling_hazard_v1_real ceiling_hazard_v1_pooled 'ceiling_hazard_v1_pooled@INF')
NEW_MODELS=(fall_d10_v0_h99 fall_d10_v0_pooled fall_d10_v0_addsale 'fall_d10_v0_pooled@ZERO')
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "=== 1. 16 eski altın dosya bayt-eşit (taban $BASE) ==="
fail=0
for m in "${OLD_MODELS[@]}"; do
  rel="app/parity/golden/$m.jsonl"
  if ! (cd "$REPO" && GIT_OPTIONAL_LOCKS=0 git show "$BASE:$rel") >"$TMP/old" 2>/dev/null; then
    echo "KIRMIZI: $rel tabanda yok" >&2
    fail=1
    continue
  fi
  if cmp -s "$TMP/old" "$REPO/$rel"; then
    printf 'OK   %-26s %s satır\n' "$m" "$(wc -l <"$REPO/$rel" | tr -d ' ')"
  else
    echo "KIRMIZI: $rel bayt-eşit DEĞİL" >&2
    fail=1
  fi
done

echo "=== 1b. üç tavan yolu dosyası ve koşullu dosyaları bayt-eşit (taban $BASE2) ==="
for m in "${PATH_MODELS[@]}"; do
  for suffix in jsonl conditional.jsonl; do
    rel="app/parity/golden/$m.$suffix"
    if ! (cd "$REPO" && GIT_OPTIONAL_LOCKS=0 git show "$BASE2:$rel") >"$TMP/old" 2>/dev/null; then
      echo "KIRMIZI: $rel tabanda ($BASE2) yok" >&2
      fail=1
      continue
    fi
    if cmp -s "$TMP/old" "$REPO/$rel"; then
      printf 'OK   %-40s %s satır\n' "$m.$suffix" "$(wc -l <"$REPO/$rel" | tr -d ' ')"
    else
      echo "KIRMIZI: $rel bayt-eşit DEĞİL" >&2
      fail=1
    fi
  done
done

echo "=== 1c. dört v1 dosyası bayt-eşit (taban $BASE3) ==="
for m in "${V1_MODELS[@]}"; do
  rel="app/parity/golden/$m.jsonl"
  if ! (cd "$REPO" && GIT_OPTIONAL_LOCKS=0 git show "$BASE3:$rel") >"$TMP/old" 2>/dev/null; then
    echo "KIRMIZI: $rel tabanda ($BASE3) yok" >&2
    fail=1
    continue
  fi
  if cmp -s "$TMP/old" "$REPO/$rel"; then
    printf 'OK   %-32s %s satır\n' "$m" "$(wc -l <"$REPO/$rel" | tr -d ' ')"
  else
    echo "KIRMIZI: $rel bayt-eşit DEĞİL" >&2
    fail=1
  fi
done

echo "=== 1d. (P4) mevcut bütün altın dosyalar bayt-eşit (taban $BASE4: 23 model + 3 koşullu + D1 sonrası) ==="
for rel in $(cd "$REPO" && GIT_OPTIONAL_LOCKS=0 git ls-tree --name-only "$BASE4" -- app/parity/golden/ | grep '\.jsonl$' | grep -v '_patched_params'); do
  (cd "$REPO" && GIT_OPTIONAL_LOCKS=0 git show "$BASE4:$rel") >"$TMP/old"
  if cmp -s "$TMP/old" "$REPO/$rel"; then
    printf 'OK   %-46s %s satır\n' "${rel#app/parity/golden/}" "$(wc -l <"$REPO/$rel" | tr -d ' ')"
  else
    echo "KIRMIZI: $rel bayt-eşit DEĞİL ($BASE4)" >&2
    fail=1
  fi
done
n4="$(cd "$REPO" && GIT_OPTIONAL_LOCKS=0 git ls-tree --name-only "$BASE4" -- app/parity/golden/ | grep '\.jsonl$' | grep -vc '_patched_params')"
if [ "$n4" -ne 27 ]; then echo "KIRMIZI: $BASE4 tabanında 27 altın .jsonl beklenirdi, $n4" >&2; fail=1; fi

echo "=== 2. _patched_params.jsonl ilk satırları bayt-eşit ($BASE: 19, $BASE2: 31, $BASE3: 43, $BASE4: 51) ==="
for b in "$BASE" "$BASE2" "$BASE3" "$BASE4"; do
  (cd "$REPO" && GIT_OPTIONAL_LOCKS=0 git show "$b:app/parity/golden/_patched_params.jsonl") >"$TMP/old_patched"
  OLD_N="$(wc -l <"$TMP/old_patched" | tr -d ' ')"
  head -n "$OLD_N" "$REPO/app/parity/golden/_patched_params.jsonl" >"$TMP/new_head"
  if cmp -s "$TMP/old_patched" "$TMP/new_head"; then
    echo "OK   ilk $OLD_N satır $b ile aynı; bugün $(wc -l <"$REPO/app/parity/golden/_patched_params.jsonl" | tr -d ' ') satır"
  else
    echo "KIRMIZI: _patched_params.jsonl ilk $OLD_N satırı ($b) değişti" >&2
    fail=1
  fi
done

echo "=== 3. dec_cases.json eski bölümleri bayt-eşit ==="
for b in "$BASE" "$BASE2" "$BASE3" "$BASE4"; do
(cd "$REPO" && GIT_OPTIONAL_LOCKS=0 git show "$b:app/parity/dec_cases.json") >"$TMP/old_dec.json"
if ! "$PY" - "$TMP/old_dec.json" "$REPO/app/parity/dec_cases.json" <<'PYEOF'
import json, sys

old = json.load(open(sys.argv[1], encoding="utf-8"))
new = json.load(open(sys.argv[2], encoding="utf-8"))
dumps = lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True, indent=1)  # noqa: E731
bad = [k for k in old if dumps(old[k]) != dumps(new.get(k))]
added = sorted(set(new) - set(old))
print(f"OK   {len(old)} eski bölüm aynı; yeni bölüm: {added}" if not bad else f"KIRMIZI: değişen bölümler {bad}")
sys.exit(1 if bad else 0)
PYEOF
then
  fail=1
fi
done

echo "=== 4. beklenen değişiklikler (bilgi) ==="
echo "MANIFEST.json: $( (cd "$REPO" && GIT_OPTIONAL_LOCKS=0 git diff --stat "$BASE4" -- app/parity/golden/MANIFEST.json | tail -1) )"
for m in "${NEW_MODELS[@]}"; do
  printf '  yeni %-30s %s satır\n' "$m" "$(wc -l <"$REPO/app/parity/golden/$m.jsonl" | tr -d ' ')"
done

if [ "$fail" -ne 0 ]; then
  echo "=== golden_unchanged: KIRMIZI ===" >&2
  exit 1
fi
echo "=== golden_unchanged: YEŞİL (U46, U55, U80; EK 3 P2, P4) ==="

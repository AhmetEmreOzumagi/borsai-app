#!/usr/bin/env bash
# Faz 2C koşullu skorlama mutasyonları (adım 4); aynı klon ve aynı sürücü kalıbı (mutate.sh).
set -u
C=/tmp/borsai_faz5_audit/clone
LOGD=/tmp/borsai_faz5_audit/mut
mkdir -p "$LOGD"
PY="$C/.venv/bin/python"
SUM="$LOGD/summary_faz2c.txt"; : > "$SUM"
cd "$C"
run() { local name=$1; shift; local start=$(date +%s)
  ( cd "$C" && "$PY" -m pytest -q -p no:cacheprovider --no-header "$@" ) > "$LOGD/$name.log" 2>&1; local rc=$?
  local end=$(date +%s); local tail=$(grep -E 'passed|failed|error' "$LOGD/$name.log" | tail -1)
  echo "$name rc=$rc dur=$((end-start))s :: $* :: $tail" >> "$SUM"; }
revert() { (cd "$C" && GIT_OPTIONAL_LOCKS=0 git checkout -q -- "$@" && GIT_OPTIONAL_LOCKS=0 git status --porcelain -- "$@"); }
edit() { "$PY" - "$C/$1"; }
TC=tests/test_scoring_conditional.py

# (m1) n < 10 iken hücre üretimi
edit borsai/scoring.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='        if len(obs) < MIN_N_METRIC:\n            continue\n        cell = {"output": output'
new='        if not obs:\n            continue\n        cell = {"output": output'
old2='            "cells": conditional_cells(model_id, j, scored) if len(scored) >= MIN_N_METRIC else [],'
new2='            "cells": conditional_cells(model_id, j, scored),'
assert old in s and old2 in s; open(p,"w",encoding="utf-8").write(s.replace(old,new).replace(old2,new2)); print("MUT(m1) uygulandı")
PYEOF
run m1_cells_below_ten "$TC::test_t1_small_n_rules_per_j" "$TC::test_real_no_conditional_cell_or_verdict_below_ten"
revert borsai/scoring.py

# (m2) sınıf mirası kırılır (koşullu satır sınıfı her zaman LIVE)
edit borsai/scoring.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    row: dict[str, Any] = {"ticker": unit["ticker"], "d1": unit["d1"], "class": unit["class"], "record_id": unit["record_id"],'
new='    row: dict[str, Any] = {"ticker": unit["ticker"], "d1": unit["d1"], "class": CLASS_LIVE, "record_id": unit["record_id"],'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(m2) uygulandı")
PYEOF
run m2_class_not_inherited "$TC::test_t3_class_is_inherited_per_j" "$TC::test_real_blocks_only_for_s_kinds_and_ek2_integrity"
revert borsai/scoring.py

# (m3) L < j arz paydaya girer
edit borsai/scoring.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    if 0 in labels:\n        return NOT_MEMBER\n    return MEMBER if all(x == 1 for x in labels) else UNDETERMINED'
new='    if 0 in labels:\n        return MEMBER\n    return MEMBER if all(x == 1 for x in labels) else UNDETERMINED'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(m3) uygulandı")
PYEOF
run m3_L_below_j_in_denominator "$TC::test_t5_arz_with_L_below_j_is_not_in_the_denominator" "$TC::test_real_blocks_only_for_s_kinds_and_ek2_integrity"
revert borsai/scoring.py

# (m4) PENDING hedef tek modelde SCORED sayılır (eksik ufuk bütün modellerde aynı anda düşmez)
edit borsai/scoring.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    target, L, reason = conditional_target(realized, j)\n    scored = target == ROW_SCORED'
new=('    target, L, reason = conditional_target(realized, j)\n'
     '    if model_id == "ceiling_hazard_v0" and target == ROW_PENDING:\n'
     '        target, L, reason = ROW_SCORED, _l_at_least(realized), None\n'
     '    scored = target == ROW_SCORED')
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(m4) uygulandı")
PYEOF
run m4_pending_not_simultaneous "$TC::test_t4_missing_horizon_drops_pair_for_all_models_at_once" "$TC::test_real_pair_status_is_the_same_for_every_model"
revert borsai/scoring.py

# (m5) S_j = 0 tanımsız çift skorlanır (en büyük kayıp yerine 0 atanır)
edit borsai/scoring.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    try:\n        s_cond, _ = pth.conditional_weights(S, j)\n    except ValueError:\n        return None'
new='    try:\n        s_cond, _ = pth.conditional_weights(S, j)\n    except ValueError:\n        s_cond = {k: 0.0 for k in range(j + 1, sv.DAYS + 1)}'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(m5) uygulandı")
PYEOF
run m5_undefined_scored "$TC::test_t5b_zero_S_j_is_undefined_not_scored"
revert borsai/scoring.py

echo "=== klon durumu ===" >> "$SUM"
(cd "$C" && GIT_OPTIONAL_LOCKS=0 git status --porcelain | grep -v '^?? .venv') >> "$SUM"
echo DONE_FAZ2C >> "$SUM"

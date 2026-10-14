#!/usr/bin/env bash
# Mutasyon sürücüsü (BORSAI_FAZ7C_FABLE_REPRO_AUDIT adım 3): her mutasyon klonda ayrı uygulanır, ilgili test(ler) koşar, sonuç (rc)
# kaydedilir, geri alınır. Klon: git clone --local -> /tmp/borsai_faz7c_audit/clone (HEAD 197a741); .venv sembolik bağ.
# Kod adı basılmaz: (n) mutasyonunda kasa kodu bellekte seçilir, dosyaya yazılır, hiçbir çıktıya yazılmaz.
set -u
C=/tmp/borsai_faz7c_audit/clone
LOGD=/tmp/borsai_faz7c_audit/mut
mkdir -p "$LOGD"
[ -e "$C/.venv" ] || ln -s /Users/ahmet/Desktop/BorsAi/.venv "$C/.venv"
PY="$C/.venv/bin/python"
SUM="$LOGD/summary_efp.txt"; : > "$SUM"
cd "$C"
echo "klon HEAD: $(GIT_OPTIONAL_LOCKS=0 git rev-parse --short HEAD); borsai kaynağı: $($PY -c 'import borsai,os; print(os.path.dirname(borsai.__file__))')" >> "$SUM"
run() { # run <ad> <pytest hedefleri...>
  local name=$1; shift
  local start=$(date +%s)
  ( cd "$C" && "$PY" -m pytest -q -p no:cacheprovider --no-header "$@" ) > "$LOGD/$name.log" 2>&1; local rc=$?
  local end=$(date +%s)
  local tail=$(grep -E '^(FAILED|ERROR)|[0-9]+ (passed|failed|error)' "$LOGD/$name.log" | tail -1)
  echo "$name rc=$rc dur=$((end-start))s :: $* :: $tail" >> "$SUM"
}
revert() { (cd "$C" && GIT_OPTIONAL_LOCKS=0 git checkout -q -- "$@" && GIT_OPTIONAL_LOCKS=0 git status --porcelain -- "$@"); }
edit() { "$PY" - "$C/$1"; }

TM=tests/test_faz7c_model.py
TB=tests/test_faz7c_backtest.py
TG=tests/test_faz7c_golden.py
TT=tests/test_faz7_tufe.py
GOLDEN="$TG::test_backtest_byte_identical_to_faz7c_golden"
PREV_H99="$TG::test_final_fit_preview_reproducible_and_stdlib_parity[fall_d10_v0_h99]"
PREV_ZERO="$TG::test_final_fit_preview_reproducible_and_stdlib_parity[fall_d10_v0_pooled@ZERO]"

# (e) D5 fold'unda D10 kesimi (K6 tersi: seçenek B) — çapa plan_fall_folds'a özgü (aynı satır PLAN_V15'te de var; ilk koşuda mutasyon uygulanmadı, düzeltildi)
edit borsai/backtest.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='        for test in tests:\n            pdate = by[test].first_trading_date\n            cutoff = _cutoff(pdate)\n            training = tuple(t for t in ordered if by[t].targets[h].session_date < pdate)\n'
new='        for test in tests:\n            pdate = by[test].first_trading_date\n            cutoff = _cutoff(pdate)\n            training = tuple(t for t in ordered if by[t].targets["D10"].session_date < pdate)\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(e) uygulandı")
PYEOF
run e_d5_fold_uses_d10_cut "$TB::test_fold_plans_test_sets_near_era_and_no_leakage" "$GOLDEN"
revert borsai/backtest.py

# (f) eğitim kesimi < yerine <=
edit borsai/backtest.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='        for test in tests:\n            pdate = by[test].first_trading_date\n            cutoff = _cutoff(pdate)\n            training = tuple(t for t in ordered if by[t].targets[h].session_date < pdate)\n'
new='        for test in tests:\n            pdate = by[test].first_trading_date\n            cutoff = _cutoff(pdate)\n            training = tuple(t for t in ordered if by[t].targets[h].session_date <= pdate)\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(f) uygulandı")
PYEOF
run f_cutoff_le "$TB::test_fold_plans_test_sets_near_era_and_no_leakage" "$TG::test_ledger_fold_sets_statuses_and_leakage" "$GOLDEN"
revert borsai/backtest.py

# (p) etiket yönü ters (K3): başlıklar y = 1 − Y_h ile fit edilir ve olasılık p_up diye yazılır (backtest ve nihai fit)
edit borsai/backtest.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='"order": list(f.training), "raw": {t: raw[t] for t in f.training}, "Y": {t: by[t].targets[f.horizon].Y for t in f.training},'
new='"order": list(f.training), "raw": {t: raw[t] for t in f.training}, "Y": {t: 1 - by[t].targets[f.horizon].Y for t in f.training},'
assert s.count(old)==1; s=s.replace(old,new)
old2='        hf = fitmod.fit_fall_horizon([r.ticker for r in rows], raw, {r.ticker: r.targets[h].Y for r in rows}, status,'
new2='        hf = fitmod.fit_fall_horizon([r.ticker for r in rows], raw, {r.ticker: 1 - r.targets[h].Y for r in rows}, status,'
assert s.count(old2)==1; s=s.replace(old2,new2)
open(p,"w",encoding="utf-8").write(s); print("MUT(p) uygulandı")
PYEOF
run p_label_direction_flipped "$GOLDEN" "$PREV_H99"
revert borsai/backtest.py

echo "=== klon durumu (mutasyonlar geri alındı) ===" >> "$SUM"
(cd "$C" && GIT_OPTIONAL_LOCKS=0 git status --porcelain | grep -v '^?? .venv') >> "$SUM"
echo DONE_FAZ7C_EFP >> "$SUM"

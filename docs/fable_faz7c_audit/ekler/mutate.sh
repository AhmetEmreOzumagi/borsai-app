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
SUM="$LOGD/summary.txt"; : > "$SUM"
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

# (0) mutasyonsuz taban: hedef testlerin yeşil olduğu gösterilir
run 0_taban_yesil "$TM::test_additional_sale_flag_values" "$TM::test_additional_sale_flag_refusals" "$TM::test_additional_sale_flag_counts_on_real_tables" \
  "$TM::test_training_sets_counts_match_spec_and_measured_numbers" "$TM::test_winsor_bounds_type7_and_log_after_winsor" "$TM::test_zero_rule_is_training_rate_bit_equal_fraction" \
  "$TB::test_fold_plans_test_sets_near_era_and_no_leakage" "$TB::test_comparator_ledgers_pinned_and_v15_d10_brier_reproduced" "$TB::test_near_era_tolerance_constant" \
  "$TB::test_near_era_sentinel_intervals" "$TB::test_near_era_rule_text_from_constant" "$TB::test_exploration_entries_and_counter" \
  "$TG::test_near_era_primary_cell_and_label" "$TG::test_ledger_fold_sets_statuses_and_leakage" "$TT::test_month_for_examples" tests/test_v1_6.py::test_5_ties_choose_inf_and_zero \
  tests/test_outcome_guard.py::test_cohort_codes_appear_in_data_only_as_outcomes "$PREV_H99" "$GOLDEN"

# (a) ek satış boşken 0 kabul
edit borsai/predict_fall.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    if parsed is None:\n        raise FeatureError(ADDITIONAL_SALE_MISSING, ADDITIONAL_SALE_FIELD,'
new='    if parsed is None:\n        return 0\n        raise FeatureError(ADDITIONAL_SALE_MISSING, ADDITIONAL_SALE_FIELD,'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(a) uygulandı")
PYEOF
run a_addsale_missing_as_zero "$TM::test_additional_sale_flag_refusals" "$TM::test_additional_sale_flag_counts_on_real_tables" "$TM::test_predict_refusal_paths"
revert borsai/predict_fall.py

# (b) bayrak ≥ 0 ile (0 → 1)
edit borsai/predict_fall.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    return 1 if parsed > 0 else 0\n'; new='    return 1 if parsed >= 0 else 0\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(b) uygulandı")
PYEOF
run b_flag_ge_zero "$TM::test_additional_sale_flag_values" "$TM::test_additional_sale_flag_counts_on_real_tables"
revert borsai/predict_fall.py

# (c) f3 (ve f1r) log'u kırpmadan önce: log özellikleri için sınırlar log uzayında Type-7, sonra exp (kırpma ln ölçeğinde)
edit borsai/preprocess.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='            ordered = sorted(raw_vals.values())\n            lo = quantile_type7(ordered, WINSOR_P05)\n            hi = quantile_type7(ordered, WINSOR_P95)\n'
new=('            ordered = sorted(raw_vals.values())\n'
     '            if fid in recipe.log:\n'
     '                _l = sorted(Fraction((Decimal(v.numerator) / Decimal(v.denominator)).ln()) for v in ordered)\n'
     '                _q = lambda pp_: Fraction((Decimal(quantile_type7(_l, pp_).numerator) / Decimal(quantile_type7(_l, pp_).denominator)).exp())\n'
     '                lo, hi = _q(WINSOR_P05), _q(WINSOR_P95)\n'
     '            else:\n'
     '                lo = quantile_type7(ordered, WINSOR_P05)\n'
     '                hi = quantile_type7(ordered, WINSOR_P95)\n')
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(c) uygulandı")
PYEOF
run c_log_before_clip "$TM::test_winsor_bounds_type7_and_log_after_winsor" "$PREV_H99"
revert borsai/preprocess.py

# (d) kırpma sınırları (ve z istatistikleri) test arzını da içerir
edit borsai/fit.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='        final = pp.fit_preprocessing({t: raw[t] for t in used}, {t: filter_status.get(t) for t in used}, recipe=recipe)\n        if test_raw is not None and not final.insufficient_feature_variation:'
new='        final = pp.fit_preprocessing({**{t: raw[t] for t in used}, **({"__test__": test_raw} if test_raw is not None else {})}, {t: filter_status.get(t) for t in used}, recipe=recipe)\n        if test_raw is not None and not final.insufficient_feature_variation:'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(d) uygulandı")
PYEOF
run d_clip_bounds_include_test_ipo "$GOLDEN"
revert borsai/fit.py

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

# (g) f1r T − 1 ayı
edit borsai/tufe.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    m -= LAG_MONTHS\n'; new='    m -= 1\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(g) uygulandı")
PYEOF
run g_tufe_month_T_minus_1 "$TT::test_month_for_examples" "$TT::test_index_for_is_pit_on_all_170_rows" "$PREV_H99"
revert borsai/tufe.py

# (h) yakın dönem eşiği 0.008 yerine 0.015
edit borsai/backtest.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='NEAR_ERA_TOLERANCE_FALL = 0.008'; new='NEAR_ERA_TOLERANCE_FALL = 0.015'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(h) uygulandı")
PYEOF
run h_tolerance_0_015 "$TB::test_near_era_tolerance_constant" "$TB::test_near_era_sentinel_intervals" "$TB::test_near_era_rule_text_from_constant" "$TG::test_models_md_faz7c_section"
revert borsai/backtest.py

# (i) yakın dönem sınırı 2023-12-01
edit borsai/backtest.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='NEAR_ERA_START = "2024-01-01"'; new='NEAR_ERA_START = "2023-12-01"'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(i) uygulandı")
PYEOF
run i_near_era_start_2023_12_01 "$TB::test_fold_plans_test_sets_near_era_and_no_leakage" "$TG::test_ledger_fold_sets_statuses_and_leakage" "$TG::test_near_era_primary_cell_and_label"
revert borsai/backtest.py

# (j) @ZERO 94 satırdan (yalnız H99) hesaplanır
edit borsai/backtest.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    rows = fall_training_rows(spec, dataset, add_sale, check=official)\n    if len(rows) != spec["training"]["n"] or dataset.data_version_sha256 != spec["training"]["data_version_sha256"]:'
new='    rows = fall_training_rows(spec, dataset, add_sale, check=official)\n    if "parent_model_id" in spec:\n        rows = [r for r in rows if (getattr(r, "cohort", "H99") or "H99") == "H99"]\n    if len(rows) not in (spec["training"]["n"], 94) or dataset.data_version_sha256 != spec["training"]["data_version_sha256"]:'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(j) uygulandı")
PYEOF
run j_zero_from_94_rows "$TM::test_zero_rule_is_training_rate_bit_equal_fraction" "$PREV_ZERO"
revert borsai/backtest.py

# (k) C eşitliğinde büyük C (şartname: bit-eşit eşitlikte en küçük C, ZERO en küçük; mutasyon kuralı tersine çevirir)
edit borsai/fit.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    return [e.hyperparameter for e in sorted(scored, key=lambda e: (e.score, e.hyperparameter))]\n'
new='    return [e.hyperparameter for e in sorted(scored, key=lambda e: (e.score, -e.hyperparameter))]\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(k) uygulandı")
PYEOF
run k_tie_to_largest_C tests/test_v1_6.py::test_5_ties_choose_inf_and_zero "$TM::test_fit_path_is_v1_6_logit_without_ridge"
revert borsai/fit.py

# (l) base_rate ledger sha pini atlanır
edit borsai/backtest.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    if sha256_bytes(raw) != ref["sha256"]:\n        raise BacktestStop(f"{ref[\'path\']}: sha256'
new='    if False and sha256_bytes(raw) != ref["sha256"]:\n        raise BacktestStop(f"{ref[\'path\']}: sha256'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(l) uygulandı")
PYEOF
run l_base_rate_pin_skipped "$TB::test_comparator_ledgers_pinned_and_v15_d10_brier_reproduced"
revert borsai/backtest.py

# (m) keşif satırı sayısı 2 053
edit borsai/specs.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='"n": 2054,'; new='"n": 2053,'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(m) uygulandı")
PYEOF
run m_exploration_count_2053 "$TB::test_exploration_entries_and_counter"
revert borsai/specs.py

# (n) data/ altına bir kasa kodu eklenir: kod bellekte seçilir, yazılmaz (v2'ye satır eklenir)
"$PY" - <<'PYEOF'
import json, glob
from pathlib import Path
C = Path("/tmp/borsai_faz7c_audit/clone")
sealed = sorted(json.load(open(p))["ticker"] for p in glob.glob(str(C / "registry/oot/records/*/*.json")) if json.load(open(p)).get("vault") == "SEALED")
v2 = C / "data/training_table_v2.csv"
v2.write_bytes(v2.read_bytes() + f"{sealed[11]},2021-06-01,PASS,10,1000000,5000000,500000,500000,3.5,,UNFILTERED,0,0.1,0.1,0.1,0.1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,1,,OOT_OPEN,ON_EXCHANGE,ANA,PRE_20211111,2021-05-20,2021-04,20.1\n".encode())
print("MUT(n) uygulandı: v2'ye bir kasa kodu satırı eklendi (kod yazdırılmadı)")
PYEOF
run n_vault_code_in_data tests/test_outcome_guard.py::test_cohort_codes_appear_in_data_only_as_outcomes "$TM::test_no_sealed_code_in_training_tables_or_new_files" "$TM::test_tables_and_data_versions_unchanged"
revert data/training_table_v2.csv

# (o) bootstrap tohumu
edit borsai/metrics.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='BOOTSTRAP_SEED = 20260921'; new='BOOTSTRAP_SEED = 20260922'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(o) uygulandı")
PYEOF
run o_bootstrap_seed "$TG::test_near_era_primary_cell_and_label" "$TG::test_models_md_faz7c_section"
revert borsai/metrics.py

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
echo DONE_FAZ7C >> "$SUM"

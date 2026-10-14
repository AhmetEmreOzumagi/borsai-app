#!/usr/bin/env bash
# Mutasyon sürücüsü (BORSAI_FAZ7_FABLE_V1_REPRO_AUDIT adım 3): her mutasyon klonda ayrı uygulanır, ilgili test(ler) koşar,
# sonuç (rc) kaydedilir, geri alınır. Klon: git clone --local -> /tmp/borsai_faz7_audit/clone (HEAD f5d7609); .venv sembolik bağ.
# Kod adı basılmaz: (m) mutasyonunda kasa kodu bellekte seçilir, dosyaya yazılır, hiçbir çıktıya yazılmaz.
set -u
C=/tmp/borsai_faz7_audit/clone
LOGD=/tmp/borsai_faz7_audit/mut
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
  local tail=$(grep -E '^(FAILED|ERROR)|[0-9]+ (passed|failed)' "$LOGD/$name.log" | tail -1)
  echo "$name rc=$rc dur=$((end-start))s :: $* :: $tail" >> "$SUM"
}
runcmd() { # runcmd <ad> <komut...>  (pytest dışı bekçi, ör. gen_golden --check)
  local name=$1; shift
  local start=$(date +%s)
  ( cd "$C" && "$@" ) > "$LOGD/$name.log" 2>&1; local rc=$?
  local end=$(date +%s)
  echo "$name rc=$rc dur=$((end-start))s :: $* :: $(tail -1 "$LOGD/$name.log")" >> "$SUM"
}
revert() { (cd "$C" && GIT_OPTIONAL_LOCKS=0 git checkout -q -- "$@" && GIT_OPTIONAL_LOCKS=0 git status --porcelain -- "$@"); }
edit() { "$PY" - "$C/$1"; }

TM=tests/test_faz7_model.py
TB=tests/test_faz7_backtest.py
TG=tests/test_faz7_golden.py
TT=tests/test_faz7_tufe.py
TC=tests/test_ceiling.py
GOLDEN="$TG::test_backtest_byte_identical_to_faz7_golden"

# (a) kırpma sınırları test arzını da içerir
edit borsai/backtest.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='        "units": [units[t] for t in f.training], "raw": {t: raw[t] for t in f.training},\n        "status": {t: status[t] for t in f.training}, "cutoff": f.cutoff_date, "features": features, "recipe": recipe,\n        "grid": grid, "test_raw": raw[f.test_ticker], "test_status": status[f.test_ticker],\n        "regime":'
new='        "units": [units[t] for t in f.training], "raw": {**{t: raw[t] for t in f.training}, f.test_ticker: raw[f.test_ticker]},\n        "status": {t: status[t] for t in f.training}, "cutoff": f.cutoff_date, "features": features, "recipe": recipe,\n        "grid": grid, "test_raw": raw[f.test_ticker], "test_status": status[f.test_ticker],\n        "regime":'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(a) backtest uygulandı")
PYEOF
edit borsai/hazard.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    prepared = _prepare(tickers, raw, status, features, recipe)\n    g, Z, e = _arrays(rows, prepared.z, prepared.columns)'
new='    prepared = _prepare(list(raw), {**raw, **{t: raw[t] for t in tickers}}, status, features, recipe)\n    g, Z, e = _arrays(rows, prepared.z, prepared.columns)'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(a) hazard uygulandı")
PYEOF
run a_clip_bounds_include_test_ipo "$GOLDEN"
revert borsai/backtest.py borsai/hazard.py

# (b) kırpma ham değer yerine ln ölçeğinde (log özellikleri için sınırlar log uzayında Type-7, sonra exp)
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
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(b) uygulandı")
PYEOF
run b_clip_on_log_scale "$TM::test_winsor_bounds_are_training_type7_p05_p95_of_raw_values" "$GOLDEN"
revert borsai/preprocess.py

# (c1) f1r T − 1 ayını kullanır
edit borsai/tufe.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    m -= LAG_MONTHS\n'; new='    m -= 1\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(c1) uygulandı")
PYEOF
run c1_tufe_month_T_minus_1 "$TT::test_month_for_examples" "$TT::test_index_for_is_pit_on_all_170_rows" "$TG::test_tufe_month_and_index_in_ledgers"
revert borsai/tufe.py

# (c2) release_date ≤ T kabul edilir (bekçi yalnız > T'de reddeder)
edit borsai/tufe.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    if not row.release_date < T:\n'; new='    if row.release_date > T:\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(c2) uygulandı")
PYEOF
run c2_release_date_le_T_accepted "$TT::test_refusals_missing_not_pit_and_file_mismatch" "$TT::test_index_for_is_pit_on_all_170_rows" "$TM::test_tufe_refusals_in_predict" "$TT"
revert borsai/tufe.py

# (d1) γ cezalandırılır
edit borsai/hazard.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    pen = np.concatenate([np.zeros(n_free), np.full(p, lam)])\n'; new='    pen = np.full(n_free + p, lam)\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(d1) uygulandı")
PYEOF
run d1_gamma_penalized "$TC::test_6_gamma_is_not_penalized" "$TM::test_regime_lambda_1e9_equals_inf_newton_and_beta_vanishes"
revert borsai/hazard.py

# (d2) δ cezalandırılır (γ değil)
edit borsai/hazard.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    pen = np.concatenate([np.zeros(n_free), np.full(p, lam)])\n'; new='    pen = np.concatenate([np.zeros(N_GROUPS), np.full(n_free - N_GROUPS + p, lam)])\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(d2) uygulandı")
PYEOF
run d2_delta_penalized "$TM::test_regime_lambda_1e9_equals_inf_newton_and_beta_vanishes" "$TG::test_regime_fit_lambda_1e9_matches_inf_on_real_data"
revert borsai/hazard.py

# (e) λ eşitliğinde küçük λ
edit borsai/hazard.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    return max(lam for lam, s in scored if s == best)\n'; new='    return min(lam for lam, s in scored if s == best)\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(e) uygulandı")
PYEOF
run e_tie_to_smallest_lambda "$TC::test_7_tie_goes_to_largest_lambda_and_inf_is_in_grid"
revert borsai/hazard.py

# (f) eğitim kesimi < yerine <=
edit borsai/survival.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='        if cutoff is not None and unit.session_dates[d - 1] >= cutoff:\n'; new='        if cutoff is not None and unit.session_dates[d - 1] > cutoff:\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(f) uygulandı")
PYEOF
run f_cutoff_le "$TB::test_fold_plans_same_tickers_near_era_78_and_no_leakage" "$TC::test_3_censoring_three_sessions_before_cutoff" "$GOLDEN"
revert borsai/survival.py

# (g1) canlı tahminde r = 1
edit borsai/predict_hazard.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='            r, source = regime["live_value"], REGIME_SOURCE_LIVE\n'; new='            r, source = 1, REGIME_SOURCE_LIVE\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(g1) uygulandı")
PYEOF
run g1_live_r_equals_1 "$TM::test_regime_values_live_and_oot_inputs" "$TG::test_pooled_at_inf_differs_from_v0_at_inf"
revert borsai/predict_hazard.py

# (g2) test tahmininde r = 1 (backtest)
edit borsai/backtest.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='        "test_regime": regime[f.test_ticker] if regime is not None else None, "r_columns": r_columns,\n'
new='        "test_regime": {REGIME_COLUMN: 1.0} if regime is not None else None, "r_columns": r_columns,\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(g2) uygulandı")
PYEOF
run g2_test_r_equals_1 "$TB::test_log_entries_and_ledgers_synthetic" "$GOLDEN"
revert borsai/backtest.py

# (h) J10 dışlaması kapatılır
edit borsai/hazard.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    return tuple(t for t in present if pp.opposite_explicit_status(status.get(t), mode))\n'; new='    return ()\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(h) uygulandı")
PYEOF
run h_j10_exclusion_off "$TM::test_f3_filter_exclusion_rule" "$TB::test_pooled_plan_filter_exclusion_matches_independent_mode" "$GOLDEN"
revert borsai/hazard.py

# (i) yakın dönem sınırı 2023-12-01
edit borsai/backtest.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='NEAR_ERA_START = "2024-01-01"'; new='NEAR_ERA_START = "2023-12-01"'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(i) uygulandı")
PYEOF
run i_near_era_start_2023_12_01 "$TB::test_fold_plans_same_tickers_near_era_78_and_no_leakage" "$TB::test_near_era_cell_of_v0_against_itself" "$TG::test_near_era_cells_labels_and_v0_comparator"
revert borsai/backtest.py

# (j) etiket eşiği +0.015
edit borsai/backtest.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='NEAR_ERA_TOLERANCE = 0.010'; new='NEAR_ERA_TOLERANCE = 0.015'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(j) uygulandı")
PYEOF
run j_tolerance_0_015 "$TB::test_near_era_label_rule_synthetic" "$TG::test_near_era_cells_labels_and_v0_comparator" "$TG::test_models_md_faz7_section" tests/test_report.py
revert borsai/backtest.py

# (k1) v0 karşılaştırıcı ledger'ının sha pini atlanır
edit borsai/backtest.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    if sha256_bytes(raw) != ref["sha256"]:\n        raise BacktestStop(f"{ref[\'path\']}: sha256'
new='    if False and sha256_bytes(raw) != ref["sha256"]:\n        raise BacktestStop(f"{ref[\'path\']}: sha256'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(k1) uygulandı")
PYEOF
run k1_v0_ledger_pin_skipped "$TB::test_v0_comparator_ledger_pinned_and_mean_rps_reproduced"
revert borsai/backtest.py

# (k2) v0 yerine başka bir ledger (tutarlı pinle: @INF ledger'ı ve onun sha'sı)
edit borsai/backtest.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old=('    "ceiling_hazard_v0": {"path": "tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv",\n'
     '                          "sha256": "976b4dcea9819160bf863873a0a3e3a639942bdfeec6f9229e015047c904665b"},\n')
new=('    "ceiling_hazard_v0": {"path": "tests/reference/macos_golden_faz1b/ceiling_hazard_v0@INF_fold_ledger.csv",\n'
     '                          "sha256": "90b610463de417c702cfae8032957aa4745aefcb4814a2745459da90bddb2f93"},\n')
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(k2) uygulandı")
PYEOF
run k2_v0_comparator_is_other_ledger "$TB::test_v0_comparator_ledger_pinned_and_mean_rps_reproduced" "$TG::test_near_era_cells_labels_and_v0_comparator" "$TG::test_manifest_and_sha256sums"
revert borsai/backtest.py

# (l) predict_hazard'da v0 çıktısını değiştiren küçük değişiklik (T2 bekçisi: gen_golden --check; Faz 1B parite testi)
edit borsai/predict_hazard.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    out.update(z=z, lin=lin, eta=[gamma[sv.GROUP_OF_DAY[d]] + lin for d in range(1, sv.DAYS + 1)])\n    return out\n\n\ndef _tufe_input'
new='    out.update(z=z, lin=lin, eta=[gamma[sv.GROUP_OF_DAY[d]] + lin * (1.0 + 1e-7) for d in range(1, sv.DAYS + 1)])\n    return out\n\n\ndef _tufe_input'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(l) uygulandı")
PYEOF
runcmd l_v0_predict_changed_gen_golden_check "$PY" app/parity/gen_golden.py --check
run l_v0_predict_changed_pytest "$TC::test_8_json_matches_numpy_final_model"
revert borsai/predict_hazard.py

# (m) data/ altına bir kasa kodu eklenir (T4): kod bellekte seçilir, yazılmaz
"$PY" - <<'PYEOF'
import json, glob
from pathlib import Path
C = Path("/tmp/borsai_faz7_audit/clone")
sealed = sorted(json.load(open(p))["ticker"] for p in glob.glob(str(C / "registry/oot/records/*/*.json")) if json.load(open(p)).get("vault") == "SEALED")
v2 = C / "data/training_table_v2.csv"
v2.write_bytes(v2.read_bytes() + f"{sealed[7]},2021-06-01,PASS,10,1000000,5000000,500000,500000,3.5,,UNFILTERED,0,0.1,0.1,0.1,0.1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,1,,OOT_OPEN,ON_EXCHANGE,ANA,PRE_20211111,2021-05-20,2021-04,20.1\n".encode())
print("MUT(m) uygulandı: v2'ye bir kasa kodu satırı eklendi (kod yazdırılmadı)")
PYEOF
run m_vault_code_in_data tests/test_outcome_guard.py::test_cohort_codes_appear_in_data_only_as_outcomes
revert data/training_table_v2.csv

# (n) TÜFE dosyasında eski bir satırın değeri değişir (önek pini)
edit data/raw/tuik/tufe_genel_2025_100.csv <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='2019-11,13.736052,'; new='2019-11,13.736053,'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(n) uygulandı")
PYEOF
run n_tufe_old_row_changed "$TT::test_file_sha_pinned_in_specs_and_provenance" "$TT::test_index_for_is_pit_on_all_170_rows" "$TT::test_builder_reproduces_csv_from_pinned_xls"
revert data/raw/tuik/tufe_genel_2025_100.csv

# (o1) bootstrap tohumu
edit borsai/metrics.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='BOOTSTRAP_SEED = 20260921'; new='BOOTSTRAP_SEED = 20260922'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(o1) uygulandı")
PYEOF
run o1_bootstrap_seed "$TG::test_near_era_cells_labels_and_v0_comparator"
revert borsai/metrics.py

# (o2) ay bloğu anahtarı YYYY-MM -> YYYY
edit borsai/backtest.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='        months.append(t[:7])\n        a.append(la)'; new='        months.append(t[:4])\n        a.append(la)'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(o2) uygulandı")
PYEOF
run o2_block_key_year "$TB::test_near_era_cell_of_v0_against_itself" "$TG::test_near_era_cells_labels_and_v0_comparator"
revert borsai/backtest.py

echo "=== klon durumu (mutasyonlar geri alındı) ===" >> "$SUM"
(cd "$C" && GIT_OPTIONAL_LOCKS=0 git status --porcelain | grep -v '^?? .venv') >> "$SUM"
echo DONE_FAZ7 >> "$SUM"

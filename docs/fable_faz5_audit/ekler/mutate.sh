#!/usr/bin/env bash
# Mutasyon sürücüsü (BORSAI_FAZ5_FABLE_REPRO_AUDIT adım 3 ve 4): her mutasyon klonda uygulanır, ilgili test(ler) koşar,
# sonuç (rc) kaydedilir, geri alınır. Klon: git clone --local -> /tmp/borsai_faz5_audit/clone; .venv sembolik bağ.
set -u
C=/tmp/borsai_faz5_audit/clone
LOGD=/tmp/borsai_faz5_audit/mut
mkdir -p "$LOGD"
[ -e "$C/.venv" ] || ln -s /Users/ahmet/Desktop/BorsAi/.venv "$C/.venv"
PY="$C/.venv/bin/python"
SUM="$LOGD/summary.txt"; : > "$SUM"
cd "$C"
echo "borsai kaynağı: $($PY -c 'import borsai,os; print(os.path.dirname(borsai.__file__))')" >> "$SUM"
run() { # run <ad> <pytest hedefleri...>
  local name=$1; shift
  local start=$(date +%s)
  ( cd "$C" && "$PY" -m pytest -q -p no:cacheprovider --no-header "$@" ) > "$LOGD/$name.log" 2>&1; local rc=$?
  local end=$(date +%s)
  local tail=$(grep -E '^(FAILED|ERROR|[0-9]+ (passed|failed))|passed|failed' "$LOGD/$name.log" | tail -1)
  echo "$name rc=$rc dur=$((end-start))s :: $* :: $tail" >> "$SUM"
}
revert() { (cd "$C" && GIT_OPTIONAL_LOCKS=0 git checkout -q -- "$@" && GIT_OPTIONAL_LOCKS=0 git status --porcelain -- "$@"); }
edit() { # edit <dosya> <python replace betiği (stdin)>
  "$PY" - "$C/$1" ; }

T5=tests/test_faz5_post_d1.py
TG=tests/test_faz5_golden.py

# (a1) tahmin yolu: ofset logit(sigmoid(η)) gidiş-dönüşüyle
edit borsai/predict_post_d1.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    hazards = updated_hazards(base["eta"], params["delta"], u, prep["columns"])'
new='    hazards = updated_hazards([math.log(h / (1.0 - h)) for h in (sv.sigmoid(e) for e in base["eta"])], params["delta"], u, prep["columns"])'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(a1) uygulandı")
PYEOF
run a1_logit_roundtrip_predict "$T5::test_5_t2_inf_endpoint_bit_equal" "$T5::test_10_numpy_final_model_vs_stdlib_predict_fixed_delta"
revert borsai/predict_post_d1.py

# (a2) fold ofseti: logit(hazard) gidiş-dönüşüyle (eğitim ve test η)
edit borsai/post_d1.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    eta = {t: res.fit.linear_predictors(res.prepared.z[t]) for t in tickers}'
new='    eta = {t: [math.log(h / (1.0 - h)) for h in res.fit.hazards(res.prepared.z[t])] for t in tickers}'
old2='    eta_test = res.fit.linear_predictors(z_test)'
new2='    eta_test = [math.log(h / (1.0 - h)) for h in res.fit.hazards(z_test)]'
assert old in s and old2 in s; open(p,"w",encoding="utf-8").write(s.replace(old,new).replace(old2,new2)); print("MUT(a2) uygulandı")
PYEOF
run a2_logit_roundtrip_fold "$T5::test_t2_t7_pipeline_inf_ledger_equals_comparator" "$TG::test_backtest_byte_identical_to_faz5_golden"
revert borsai/post_d1.py

# (b) δ = 0 için erken dönüş dalı
edit borsai/predict_post_d1.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    hazards = updated_hazards(base["eta"], params["delta"], u, prep["columns"])'
new=('    if all(v == 0.0 for v in params["delta"].values()):\n'
     '        out.update(curves([sv.sigmoid(e) for e in base["eta"]], parent["reclose_rates"]))\n'
     '        return out\n' + old)
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(b) uygulandı")
PYEOF
run b_zero_delta_branch "$T5::test_5b_no_special_branch_for_zero_delta" "$T5::test_5_t2_inf_endpoint_bit_equal"
revert borsai/predict_post_d1.py

# (c) test arzının D1 özelliği fold ön işleme istatistiklerine katılır
edit borsai/post_d1.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    ds = delta_set_of(res, payload["feats"])'
new=old+'\n    ds.feats["__TEST__"] = dict(payload["test_feats"])'
old2='    prep = fit_d1_prep({t: ds.feats[t] for t in ds.tickers})\n    U, o, e = arrays(ds, ds.tickers, prep)\n    fit = fit_delta(U, o, e, selected, prep.columns)'
new2='    prep = fit_d1_prep(ds.feats)\n    U, o, e = arrays(ds, ds.tickers, prep)\n    fit = fit_delta(U, o, e, selected, prep.columns)'
old3='        out.update(status=None, feats_used=ds.feats, prep=fit_d1_prep(ds.feats).params())'
assert old in s and old2 in s and old3 in s
open(p,"w",encoding="utf-8").write(s.replace(old,new).replace(old2,new2)); print("MUT(c) uygulandı")
PYEOF
run c_test_ipo_in_prep "$T5::test_8b_test_ipo_d1_fields_do_not_touch_training" "$TG::test_backtest_byte_identical_to_faz5_golden"
revert borsai/post_d1.py

# (d) SESSIONS yükleyicisi 2. seansın hacmini okur
edit borsai/post_d1.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='            if k != 1:\n                continue'
new='            if k != 1:\n                _ = r["thb_raw_volume"]\n                continue'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(d) uygulandı")
PYEOF
run d_loader_reads_session2_volume "$T5::test_8_sessions_loader_whitelist"
revert borsai/post_d1.py

# (e) λ eşitliğinde küçük λ
edit borsai/hazard.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    return max(lam for lam, s in scored if s == best)'
new='    return min(lam for lam, s in scored if s == best)'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(e) uygulandı")
PYEOF
run e_tie_to_smallest_lambda "$T5::test_7_selection_ties_to_largest_and_drops_nonconverged"
revert borsai/hazard.py

# (f) eğitim kesimi < yerine <=
edit borsai/survival.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='        if cutoff is not None and unit.session_dates[d - 1] >= cutoff:'
new='        if cutoff is not None and unit.session_dates[d - 1] > cutoff:'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(f) uygulandı")
PYEOF
run f_cutoff_le "$T5::test_4_fold_set_and_leakage_dates" "$TG::test_backtest_byte_identical_to_faz5_golden"
revert borsai/survival.py

# (g1) d1_lock düzeltilmiş low/upper_limit sütunlarından
edit borsai/post_d1.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='"low": "thb_raw_low",'; new='"low": "low",'
old2='"upper_limit": "thm_raw_upper_limit"}'; new2='"upper_limit": "upper_limit"}'
assert old in s and old2 in s; open(p,"w",encoding="utf-8").write(s.replace(old,new).replace(old2,new2)); print("MUT(g1) uygulandı")
PYEOF
run g1_lock_from_corrected_columns "$T5::test_8_sessions_loader_whitelist" "$T5::test_2_feature_definitions"
revert borsai/post_d1.py

# (g2) d1_lock float karşılaştırmasıyla
edit borsai/predict_post_d1.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    lock = int(prices["low"] == upper)'
new='    lock = int(float(prices["low"]) == float(upper))'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(g2) uygulandı")
PYEOF
run g2_lock_float_compare "$T5::test_2_feature_definitions" "$T5::test_9_refusals_warnings_scope" "$TG::test_backtest_byte_identical_to_faz5_golden"
revert borsai/predict_post_d1.py

# (h) h_1 de δ ile güncellenir
edit borsai/predict_post_d1.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    return [sv.sigmoid(eta[0])] + [sv.sigmoid(eta[d - 1] + shift) for d in UPDATED_DAYS]'
new='    return [sv.sigmoid(eta[0] + shift)] + [sv.sigmoid(eta[d - 1] + shift) for d in UPDATED_DAYS]'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(h) uygulandı")
PYEOF
run h_h1_updated "$T5::test_5_t2_inf_endpoint_bit_equal" "$T5::test_10_numpy_final_model_vs_stdlib_predict_fixed_delta" "$TG::test_backtest_byte_identical_to_faz5_golden"
revert borsai/predict_post_d1.py

# (i1) sequence_guard INDEX_POST_D1.json'u yok sayar
edit borsai/outcomes.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    if post_index.exists():\n        paths += ["models/INDEX_POST_D1.json"]'
new='    if False and post_index.exists():\n        paths += ["models/INDEX_POST_D1.json"]'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(i1) uygulandı")
PYEOF
run i1_sequence_guard_ignores_post_index "$T5::test_t4_sequence_guard_reads_post_d1_index"
revert borsai/outcomes.py

# (i2) sequence_violations INDEX_POST_D1.json'u yok sayar
edit borsai/scoring.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='''    post_commits = ({e["model_id"]: git.added_commit(f"models/{e['file']}")
                     for e in json.loads(post_path.read_text(encoding="utf-8"))["models"]} if post_path.exists() else {})'''
new='    post_commits = {}'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(i2) uygulandı")
PYEOF
run i2_sequence_violations_ignore_post_index tests/test_outcome_guard.py::test_10e_post_d1_model_listed_but_not_committed_is_red tests/test_outcome_guard.py::test_10f_post_d1_model_then_outcome_is_green_parallel_branch_is_red
revert borsai/scoring.py

# (j) freeze_post_d1 modeli INDEX.json'a da ekler
edit borsai/freeze.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    post_path.write_bytes(pretty_json_bytes(post_index))\n    return post_index'
new=('    post_path.write_bytes(pretty_json_bytes(post_index))\n'
     '    index["models"].append(post_index["models"][-1])\n'
     '    (models_dir / "INDEX.json").write_bytes(pretty_json_bytes(index))\n'
     '    return post_index')
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(j) uygulandı")
PYEOF
run j_freeze_writes_index_json "$T5::test_t4_freeze_post_d1_writes_only_the_separate_index"
revert borsai/freeze.py

# (k1) §5 fark satırı sınırı 0.001 kaydırılır (parse_range)
edit borsai/report_faz5.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    lo, hi = (float(p.strip()) for p in t.split("…"))'
new='    lo, hi = (float(p.strip()) + 0.001 for p in t.split("…"))'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(k1) uygulandı")
PYEOF
run k1_expectation_bound_shift "$T5::test_15_expectation_rows_verbatim_and_rules"
revert borsai/report_faz5.py

# (k2) "çok iyi" eşiği −0.040 → −0.060
edit borsai/report_faz5.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='TOO_GOOD_BRIER2_DIFF = -0.040'; new='TOO_GOOD_BRIER2_DIFF = -0.060'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(k2) uygulandı")
PYEOF
run k2_too_good_threshold "$T5::test_15_expectation_rows_verbatim_and_rules" "$TG::test_models_md_faz5_section"
revert borsai/report_faz5.py

# (k3) λ nihai fit "olası" aralığı (10, 100) → (10, 29): λ = 30 etiketi döner; yalnız MODELS.md eşitliği yakalar mı?
edit borsai/report_faz5.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='LAMBDA_FINAL_LIKELY = (10.0, 100.0)'; new='LAMBDA_FINAL_LIKELY = (10.0, 29.0)'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(k3) uygulandı")
PYEOF
run k3_lambda_final_range "$T5::test_15_expectation_rows_verbatim_and_rules" "$TG::test_models_md_faz5_section" tests/test_report.py::test_models_md_is_up_to_date
revert borsai/report_faz5.py

# (l1) bootstrap tohumu
edit borsai/metrics.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='BOOTSTRAP_SEED = 20260921'; new='BOOTSTRAP_SEED = 20260922'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(l1) uygulandı")
PYEOF
run l1_bootstrap_seed "$T5::test_t6_comparator_reproduces_models_md_j1"
revert borsai/metrics.py

# (l2) ay bloğu anahtarı YYYY-MM -> YYYY (koşullu gözlemler)
edit borsai/report_faz5.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='block=r["first_trading_date"][:7]'; assert s.count(old)==2
open(p,"w",encoding="utf-8").write(s.replace(old,'block=r["first_trading_date"][:4]')); print("MUT(l2) uygulandı")
PYEOF
run l2_block_key_year "$T5::test_t6_comparator_reproduces_models_md_j1"
revert borsai/report_faz5.py

echo "=== klon durumu ===" >> "$SUM"
(cd "$C" && GIT_OPTIONAL_LOCKS=0 git status --porcelain | grep -v '^?? .venv') >> "$SUM"
echo DONE_FAZ5 >> "$SUM"

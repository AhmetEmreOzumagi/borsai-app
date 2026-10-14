#!/usr/bin/env bash
# Mutasyon sürücüsü (BORSAI_FAZ8_FABLE_REPRO_AUDIT adım 4): her mutasyon klonda ayrı uygulanır, ilgili test(ler) koşar, rc kaydedilir,
# geri alınır. Klon: git clone --local -> /tmp/borsai_faz8_audit/clone (HEAD c84ba64); .venv sembolik bağ. Depoya yazılmaz.
set -u
C=/tmp/borsai_faz8_audit/clone
LOGD=/tmp/borsai_faz8_audit/mut
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

TB=tests/test_faz8_break.py
TM=tests/test_faz8_model.py
TG=tests/test_faz8_golden.py
TV=tests/test_faz7_vault.py
GOLDEN="$TG::test_b4_ledger_reproduces_bit_exact"
MD="$TG::test_b6_models_md_faz8_section"

# (0) mutasyonsuz taban: hedef testlerin yeşil olduğu gösterilir
run 0_taban_yesil "$TB::test_2_b_floor_is_raw_text_decimal_equality" "$TB::test_3_loader_whitelist_access_counter" "$TB::test_4_plan_counts_and_cutoffs" \
  "$TB::test_4b_same_day_rule_synthetic" "$TB::test_7_structural_zero_on_h99" "$TB::test_7b_structural_zero_boundary_and_rounding" \
  "$TB::test_1b_streak_matches_table_and_snapshot_dates" "$TB::test_2b_turnover_quantiles_match_profile_section_4" \
  "$TM::test_5b_zero_rate_is_exact_fraction" "$TM::test_10_too_good_triggers" "$TM::test_15c_ledger_columns_fixed_and_report_renders_synthetic" \
  "$TG::test_b3_ledger_structure_and_plan" "$GOLDEN" "$MD" "$TV::test_scores_oot_code_rule_mutations"

# (a) b_floor float eşitliğiyle
edit borsai/predict_break.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    floor = int(close == lower)\n'; new='    floor = int(float(close) == float(lower))\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(a) uygulandı")
PYEOF
run a_b_floor_float_equality "$TB::test_2_b_floor_is_raw_text_decimal_equality"
revert borsai/predict_break.py

# (b) etiket "en düşük == alt limit" (dokunma) ile
edit borsai/post_break.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    return int(_dec(row[LABEL_COLUMNS["close"]]) == lo)\n'; new='    return int(_dec(row["thb_raw_low"]) == lo)\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(b) uygulandı")
PYEOF
run b_label_low_touch "$TB::test_3_loader_whitelist_access_counter" "$TG::test_b3_ledger_structure_and_plan" "$GOLDEN"
revert borsai/post_break.py

# (c) eğitim kesimi <=
edit borsai/post_break.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='                if y is None or d is None or not d < T:\n'; new='                if y is None or d is None or not d <= T:\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(c) uygulandı")
PYEOF
run c_cutoff_le "$TB::test_4_plan_counts_and_cutoffs" "$TB::test_4b_same_day_rule_synthetic" "$GOLDEN"
revert borsai/post_break.py

# (d) hücre kesimi D_1 yerine T
edit borsai/post_break.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='        cells, info = cache.get(u.first_trading_date)\n'; new='        cells, info = cache.get(f.break_date)\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(d) uygulandı")
PYEOF
run d_cells_cutoff_T "$GOLDEN" "$TM::test_15c_ledger_columns_fixed_and_report_renders_synthetic"
revert borsai/post_break.py

# (e) beyaz liste dışı sütun okuma (D_{b+1} satırında thb_raw_low)
edit borsai/post_break.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='            y1 = _label(s[b + 1])\n'; new='            y1 = _label(s[b + 1])\n            _leak = s[b + 1]["thb_raw_low"]\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(e) uygulandı")
PYEOF
run e_whitelist_extra_column "$TB::test_3_loader_whitelist_access_counter"
revert borsai/post_break.py

# (f) yapısal sıfırda 10 − b yerine 9 − b
edit borsai/predict_break.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    for _ in range(DAYS - b):\n        x = pth.lower_limit(x)\n'; new='    for _ in range(DAYS - 1 - b):\n        x = pth.lower_limit(x)\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(f) uygulandı")
PYEOF
run f_structural_zero_9_minus_b "$TB::test_7_structural_zero_on_h99" "$TB::test_7b_structural_zero_boundary_and_rounding" "$TG::test_b3_ledger_structure_and_plan"
revert borsai/predict_break.py

# (g) ürün eşiği bir adım kaydırılmış
edit borsai/predict_break.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    lo1 = pth.lower_limit(cb)\n    return pth.ratio_minus_one(lo1, P), pth.ratio_minus_one(pth.lower_limit(lo1), P)\n'
new='    lo1 = pth.lower_limit(cb)\n    lo1 = lo1 + pth.tick(lo1)\n    return pth.ratio_minus_one(lo1, P), pth.ratio_minus_one(pth.lower_limit(lo1), P)\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(g) uygulandı")
PYEOF
run g_product_threshold_one_tick "$GOLDEN" "$MD"
revert borsai/predict_break.py

# (h) yakın dönem sınırı 2023-12-01
edit borsai/specs.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='FAZ8_NEAR_ERA_START = "2024-01-01"\n'; new='FAZ8_NEAR_ERA_START = "2023-12-01"\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(h) uygulandı")
PYEOF
run h_near_era_2023_12_01 "$TB::test_4_plan_counts_and_cutoffs" "$TG::test_b3_ledger_structure_and_plan" "$MD"
revert borsai/specs.py

# (i) @ZERO test satırını içerir
edit borsai/post_break.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='"zero_F1": train_rate(ys1),'; new='"zero_F1": train_rate(ys1 + [table.labels[f.ticker].y1]),'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(i) uygulandı")
PYEOF
run i_zero_includes_test_row "$TM::test_5b_zero_rate_is_exact_fraction" "$TG::test_b3_ledger_structure_and_plan" "$GOLDEN"
revert borsai/post_break.py

# (j) el değiştirmede pay yerine sermaye
edit borsai/post_break.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='row.inputs["ipo_price_tl"], row.inputs["shares_offered"], L, b, status,'; new='row.inputs["ipo_price_tl"], row.inputs["post_ipo_share_capital"], L, b, status,'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(j) uygulandı")
PYEOF
run j_turnover_capital_instead_of_shares "$TB::test_1b_streak_matches_table_and_snapshot_dates" "$TB::test_2b_turnover_quantiles_match_profile_section_4" "$GOLDEN"
revert borsai/post_break.py

# (k) kırpma sınırları (ve z istatistikleri) test arzını içerir (ortak fit yolu fit.py)
edit borsai/fit.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='        final = pp.fit_preprocessing({t: raw[t] for t in used}, {t: filter_status.get(t) for t in used}, recipe=recipe)\n        if test_raw is not None and not final.insufficient_feature_variation:'
new='        final = pp.fit_preprocessing({**{t: raw[t] for t in used}, **({"__test__": test_raw} if test_raw is not None else {})}, {t: filter_status.get(t) for t in used}, recipe=recipe)\n        if test_raw is not None and not final.insufficient_feature_variation:'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(k) uygulandı")
PYEOF
run k_clip_bounds_include_test_ipo "$GOLDEN"
revert borsai/fit.py

# (l) §6 "çok iyi" eşiği −0.16 yerine −0.20
edit borsai/specs.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    "too_good_primary_diff": -0.160,\n'; new='    "too_good_primary_diff": -0.200,\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(l) uygulandı")
PYEOF
run l_too_good_threshold_0_20 "$TM::test_10_too_good_triggers" "$MD"
revert borsai/specs.py

# (m) N19 kasa kod-sha bekçisi gevşetilmiş (kaynak hash'i denetimi kapalı): mutasyon testi yakalamalı
edit tests/test_faz7_vault.py <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    if committed["code"]["borsai_source_sha256"] != fs7.borsai_tree_sha256_at(last):\n        probs.append("borsai_source_sha256")\n'
new='    if False and committed["code"]["borsai_source_sha256"] != fs7.borsai_tree_sha256_at(last):\n        probs.append("borsai_source_sha256")\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(m) uygulandı")
PYEOF
run m_vault_guard_source_sha_disabled "$TV::test_scores_oot_code_rule_mutations"
revert tests/test_faz7_vault.py

echo "klon temiz mi (git status --porcelain, .venv dışında): $(cd "$C" && GIT_OPTIONAL_LOCKS=0 git status --porcelain | grep -v '^?? .venv' | wc -l | tr -d ' ') satır" >> "$SUM"
cat "$SUM"

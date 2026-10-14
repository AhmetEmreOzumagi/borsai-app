#!/usr/bin/env bash
# Mutasyon sürücüsü (BORSAI_FAZ6_FABLE_OOT_AUDIT adım 4): her mutasyon klonda uygulanır, ilgili test(ler) koşar, rc kaydedilir,
# geri alınır. Klon: git clone --local -> /tmp/borsai_faz6_audit/clone; .venv sembolik bağ. Çıktılar: $LOGD/<ad>.log, summary.txt.
# Not: bülten dosya adı kalıbı metinde yazılmaz; (m) için ad parçalardan kurulur ve günlükler maskelenir.
set -u
C=/tmp/borsai_faz6_audit/clone
LOGD=/tmp/borsai_faz6_audit/mut
mkdir -p "$LOGD"
[ -e "$C/.venv" ] || ln -s /Users/ahmet/Desktop/BorsAi/.venv "$C/.venv"
PY="$C/.venv/bin/python"
SUM="$LOGD/summary.txt"; : > "$SUM"
cd "$C"
export GIT_OPTIONAL_LOCKS=0
echo "borsai kaynağı: $($PY -c 'import borsai,os; print(os.path.dirname(borsai.__file__))')" >> "$SUM"
echo "HEAD: $(git rev-parse HEAD)" >> "$SUM"
MASK='s/th([bm])(20[0-9]{6})/th\1_[tarih-maskeli]/g'
run() { # run <ad> <pytest hedefleri...>
  local name=$1; shift
  local start=$(date +%s)
  ( cd "$C" && "$PY" -m pytest -q -p no:cacheprovider --no-header "$@" ) 2>&1 | sed -E "$MASK" > "$LOGD/$name.log"; local rc=${PIPESTATUS[0]}
  local end=$(date +%s)
  local tail=$(grep -E '^(FAILED|ERROR|[0-9]+ (passed|failed))|passed|failed' "$LOGD/$name.log" | tail -1)
  echo "$name rc=$rc dur=$((end-start))s :: $* :: $tail" >> "$SUM"
}
revert() { (cd "$C" && git checkout -q -- "$@" && git clean -fdq -- "$@" && git status --porcelain -- "$@"); }
edit() { "$PY" - "$C/$1"; }   # edit <dosya> <python replace betiği (stdin)>

T6=tests/test_faz6_oot.py
TG=tests/test_outcome_guard.py
OO=borsai/outcomes_oot.py
RG=borsai/registry.py
SC=borsai/scoring.py
FZ=borsai/freeze.py

# (a) indirme kapısı push kanıtını aramaz
edit $OO <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='            if sc.proof_time(git, git.added_commit(rel), proofs) is None:\n                problems.append(f"{rel}: push kanıtı yok")'
new='            if False:\n                problems.append(f"{rel}: push kanıtı yok")'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(a) uygulandı")
PYEOF
run a_gate_no_proof "$T6::test_download_gate_requires_committed_and_pushed_s2_records"
revert $OO

# (b) kapı SEALED üyelerin S2 kaydını aramaz
edit $OO <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    for r in reg.cohort_members(rows):\n        recs = fz.active_records(r["ticker"], root / "registry" / "oot" / "records")'
new='    for r in reg.cohort_members(rows):\n        if not reg.is_open(r["vault"]):\n            continue\n        recs = fz.active_records(r["ticker"], root / "registry" / "oot" / "records")'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(b) uygulandı")
PYEOF
run b_gate_skips_sealed "$T6::test_download_gate_requires_committed_and_pushed_s2_records" "$T6::test_class_oot_cohort_gate_and_outcome_before_record" "$T6::test_extractor_reads_only_open_codes_and_never_opens_sealed" "$T6::test_d1_rows_and_oot_post_d1_record" "$TG::test_oot_outcomes_follow_every_s2_record_and_its_push_proof"
revert $OO

# (c) ayıklayıcı SEALED kodu kabul eder
edit $OO <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    if not reg.is_open(v) and ticker not in set(unsealed):\n        raise SealedAccessError('
new='    if False:\n        raise SealedAccessError('
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(c) uygulandı")
PYEOF
run c_extractor_accepts_sealed "$T6::test_extractor_reads_only_open_codes_and_never_opens_sealed"
revert $OO

# (d) ayıklayıcı D_11 satırını da alır (durma koşulu D_10'da durmaz; okuma 15 seans sınırına kadar sürer)
edit $OO <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='        if (d1_only and res.sessions) or len(res.sessions) == oc.N_SESSIONS or res.exhausted:'
new='        if (d1_only and res.sessions) or len(res.sessions) == oc.N_SESSIONS + 1 or res.exhausted:'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(d) uygulandı")
PYEOF
run d_extractor_reads_d11 "$T6::test_extractor_reads_only_open_codes_and_never_opens_sealed" "$T6::test_extracted_rows_equal_outcomes_definitions" "$T6::test_d1_rows_and_oot_post_d1_record" "$T6::test_build_oot_scores_synthetic" "$T6::test_oot_post_d1_block_machine_sequenced_rows"
revert $OO

# (e) kasa tohumu değişir; (e2) tabaka (yıl) sırası değişir
edit $RG <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='VAULT_SEED = 20260924'; new='VAULT_SEED = 20260925'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(e) uygulandı")
PYEOF
run e_vault_seed "$T6::test_vault_draw_is_deterministic_stratified_and_exposed_stay_open" "$T6::test_vault_draw_on_universe_counts" "$T6::test_real_cohort_validates_and_reproduces_from_code"
revert $RG
edit $RG <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    for year in sorted(strata):\n        tickers = strata[year]'; new='    for year in sorted(strata, reverse=True):\n        tickers = strata[year]'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(e2) uygulandı")
PYEOF
run e2_vault_year_order "$T6::test_vault_draw_is_deterministic_stratified_and_exposed_stay_open" "$T6::test_real_cohort_validates_and_reproduces_from_code"
revert $RG

# (f) marj kural tarihi bir gün kayar
edit $RG <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='MARGIN_CHANGE = "2020-03-13"'; new='MARGIN_CHANGE = "2020-03-14"'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(f) uygulandı")
PYEOF
run f_margin_date_shift "$T6::test_regime_tags_follow_rule_dates" "$T6::test_real_cohort_validates_and_reproduces_from_code"
revert $RG

# (g) TICK_TABLE_MISMATCH eşiği bozulur: yalnız C_1..C_5 karşılaştırılır; (g2) T2015 tablosuna 250 kademesi eklenir
edit $RG <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    return limit_path_with(price, table) != limit_path_with(price, TICK_TABLE)'
new='    return limit_path_with(price, table)[1][:5] != limit_path_with(price, TICK_TABLE)[1][:5]'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(g) uygulandı")
PYEOF
run g_tick_threshold_c5 "$T6::test_tick_table_mismatch_only_where_path_reaches_250" "$T6::test_real_cohort_validates_and_reproduces_from_code"
revert $RG
edit $RG <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='(("20", "0.01"), ("50", "0.02"), ("100", "0.05"), (None, "0.10"))'
new='(("20", "0.01"), ("50", "0.02"), ("100", "0.05"), ("250", "0.10"), (None, "0.25"))'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(g2) uygulandı")
PYEOF
run g2_t2015_table_250_tier "$T6::test_tick_table_mismatch_only_where_path_reaches_250" "$T6::test_real_cohort_validates_and_reproduces_from_code"
revert $RG

# (h) G1: registry/oot/inputs'a sonuç alanı eklenir (klondaki gerçek girdi dosyası)
edit registry/oot/inputs/FADE.json <<'PYEOF'
import sys, json; p=sys.argv[1]; d=json.load(open(p,encoding="utf-8")); d["close"]="9.99"
json.dump(d, open(p,"w",encoding="utf-8"), ensure_ascii=False, indent=1); print("MUT(h) uygulandı")
PYEOF
run h_g1_outcome_key_in_inputs "$TG::test_oot_registry_carries_no_outcome_fields" "$T6::test_real_inputs_validate_and_are_byte_equal_imports"
revert registry/oot/inputs/FADE.json

# (i) data/outcomes_oot commit'i S2 atası olmadan kabul edilir (kohort kapısı hep açık); (i2) kayıt-atası koşulu kaldırılır
edit $SC <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    return not missing, missing\n'; new='    return True, []\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(i) uygulandı")
PYEOF
run i_cohort_gate_always_open "$T6::test_class_oot_cohort_gate_and_outcome_before_record" "$T6::test_class_oot_requires_dag_order_and_proof_order"
revert $SC
edit $SC <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    record_ok = rc is not None and git.is_ancestor(rc, target)\n'; new='    record_ok = True\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(i2) uygulandı")
PYEOF
run i2_record_ancestor_ignored "$T6::test_class_oot_requires_dag_order_and_proof_order" "$T6::test_class_oot_cohort_gate_and_outcome_before_record" "$T6::test_build_oot_scores_synthetic"
revert $SC

# (j) ScaleMixError OOT ile backtest/canlı karışımını kabul eder (_one_scale ve merge_scales)
edit $SC <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    scales = {o.scale for o in obs}\n    if len(scales) > 1:\n        raise ScaleMixError(f"iki terazi birleştirilemez: {sorted(scales)}")'
new='    scales = {o.scale for o in obs}\n    if len(scales) > 1 and SCALE_OOT not in scales:\n        raise ScaleMixError(f"iki terazi birleştirilemez: {sorted(scales)}")\n    if SCALE_OOT in scales:\n        scales = {SCALE_OOT}'
assert s.count(old)==1; s=s.replace(old,new)
old2='    scales = {b.get("scale") for b in blocks}\n    if len(scales) > 1:'
new2='    scales = {b.get("scale") for b in blocks}\n    if SCALE_OOT in scales:\n        return None\n    if len(scales) > 1:'
assert s.count(old2)==1; open(p,"w",encoding="utf-8").write(s.replace(old2,new2)); print("MUT(j) uygulandı")
PYEOF
run j_scale_mix_accepts_oot "$T6::test_scale_mixing_with_oot_is_rejected"
revert $SC

# (k) class_oot kanıt sırasını yok sayar
edit $SC <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    proof_ok = rec_proof is not None and ing_proof is not None and rec_proof < ing_proof\n'; new='    proof_ok = True\n'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(k) uygulandı")
PYEOF
run k_class_oot_ignores_proof_order "$T6::test_class_oot_requires_dag_order_and_proof_order"
revert $SC

# (l) freeze --oot bir modeli atlar
edit $FZ <<'PYEOF'
import sys; p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old='    cells = [_oot_cell(e, p, sha, inputs, na.get(e["model_id"])) for e, p, sha in models]'
new='    cells = [_oot_cell(e, p, sha, inputs, na.get(e["model_id"])) for e, p, sha in models[1:]]'
assert s.count(old)==1; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(l) uygulandı")
PYEOF
run l_freeze_oot_skips_model "$T6::test_oot_batch_one_record_per_member_with_every_model" "$T6::test_real_dry_run_builds_every_member_without_writing" "$T6::test_download_gate_requires_committed_and_pushed_s2_records"
revert $FZ

# (m) kohort penceresi tarihli bir zip repoya konur (ad parçalardan; metinde kalıp yok)
K1="th""b"; D1="2021""0301"; ZIPD="$C/data/raw/bist/$K1/2021"; ZIPF="$ZIPD/${K1}${D1}1.zip"
mkdir -p "$ZIPD"; printf 'PK\x05\x06%s' "$(printf '\0%.0s' {1..18})" > "$ZIPF"; echo "MUT(m) uygulandı: $(echo "$ZIPF" | sed -E "$MASK")" >> "$SUM"
run m_cohort_window_zip_in_repo "$TG::test_no_cohort_window_bulletin_anywhere_in_repo"
rm -f "$ZIPF"; rmdir "$ZIPD" 2>/dev/null; rmdir "$C/data/raw/bist/$K1" 2>/dev/null

echo "son durum: $(git status --porcelain | grep -v '^?? .venv$' | wc -l | tr -d ' ') değişiklik (0 beklenir)" >> "$SUM"
cat "$SUM"

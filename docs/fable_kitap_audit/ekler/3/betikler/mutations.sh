#!/bin/zsh
# Adım 1: CLAUDE.md kurallarını bozan mutasyonlar, klonda. Her mutasyon commit'lenir, hedef testler koşulur, sonra sıfırlanır.
set -u
export GIT_OPTIONAL_LOCKS=0
C=/tmp/borsai_kitap_audit_3/clone
OUT=/tmp/borsai_kitap_audit_3/mut_out
mkdir -p $OUT
cd $C
BASE=$(git rev-parse HEAD)
PY=$C/.venv/bin/python
run_tests() { # name, tests...
  local name=$1; shift
  echo "### $name :: $*" > $OUT/$name.txt
  git add -A . >/dev/null 2>&1; git -c user.name=audit -c user.email=a@b commit -q -m "MUTATION $name" --allow-empty >/dev/null 2>&1
  git status --porcelain --untracked-files=all | head -5 >> $OUT/$name.txt
  perl -e 'alarm 1500; exec @ARGV' $PY -m pytest -q -p no:cacheprovider -o addopts="" --no-header "$@" >> $OUT/$name.txt 2>&1
  echo "exit=$?" >> $OUT/$name.txt
  tail -n 3 $OUT/$name.txt | sed 's/^/    /'
  git reset -q --hard $BASE; git clean -fdq
}
echo "BASE $BASE"
# baseline sanity (no mutation): a few quick tests should be green
run_tests m0_baseline tests/test_guardrails.py tests/test_registry_ipos.py tests/test_experiment_log.py tests/test_push_proof.py "tests/test_scoring.py::test_9d_scales_never_combined" "tests/test_scoring.py::test_9e_verdict_vocabulary"

# (a) bir kayıttan bir model çıkarılmış
$PY - <<'EOF'
import json,pathlib
p=sorted(pathlib.Path('registry/records/CITAS').glob('*.json'))[0]
d=json.loads(p.read_text()); d['models']=d['models'][:-1]; d['summary']['n_models']-=1; d['summary']['n_predicted']-=1
p.write_text(json.dumps(d,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
EOF
run_tests m_a_record_missing_model "tests/test_freeze_records.py::test_committed_record_consistency" "tests/test_scoring.py::test_committed_scores_json_matches_recomputation"

# (b) kayıtta parametre hash'i yanlış
$PY - <<'EOF'
import json,pathlib
p=sorted(pathlib.Path('registry/records/NETGL').glob('*.json'))[0]
d=json.loads(p.read_text()); d['models'][0]['params_sha256']='0'*64
p.write_text(json.dumps(d,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
EOF
run_tests m_b_record_wrong_param_hash "tests/test_freeze_records.py::test_committed_record_consistency" "tests/test_scoring.py::test_committed_scores_json_matches_recomputation"

# (c) push kanıtı olmayan kayıt LIVE sayılmaya çalışılıyor
sed -i '' 's/    live = istanbul_before(cand.push_created_at, d1)/    live = True/' borsai/scoring.py
grep -n "live = True" borsai/scoring.py | head -2
run_tests m_c_no_proof_live "tests/test_scoring.py" -k "test_5"
sed -i '' 's/    live = istanbul_before(cand.push_created_at, d1)/    live = True/' borsai/scoring.py
run_tests m_c2_no_proof_live_scores "tests/test_scoring.py::test_committed_scores_json_matches_recomputation"

# (d) iki terazi aynı metrikte toplanıyor
$PY - <<'EOF'
import pathlib
p=pathlib.Path('borsai/scoring.py'); s=p.read_text()
s=s.replace('''    if len(scales) > 1:
        raise ScaleMixError(f"iki terazi birleştirilemez: {sorted(scales)}")
    js = {o.j for o in obs}''','''    js = {o.j for o in obs}''')
p.write_text(s)
EOF
run_tests m_d_scale_mix "tests/test_scoring.py::test_9d_scales_never_combined" tests/test_scoring_conditional.py "tests/test_faz8_live.py::test_13_13_scale_mix_is_refused" "tests/test_faz5_live.py::test_scale_mix_post_d1"

# (e) parametresi değişmiş model aynı model_id ile
$PY - <<'EOF'
import json,pathlib
p=pathlib.Path('models/v1_5_h99.json'); d=json.loads(p.read_text())
d['horizons']['D5']['return']['coef'][0]+=0.001
p.write_text(json.dumps(d,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
EOF
run_tests m_e_param_changed_same_id tests/test_models.py "tests/test_faz1b_guardrails.py::test_faz1a_model_files_and_index_entries_unchanged" "tests/test_freeze_records.py::test_committed_record_consistency"

# (f) legacy/ içinde bir bayt değişmiş
f=$(git ls-files legacy | grep '\.py$' | head -1); printf '\n' >> "$f"; echo "mutated $f"
run_tests m_f_legacy_byte tests/test_guardrails.py

# (g) resmi olmayan kaynaktan bir sonuç satırı (NETGL h=5 kapanış değişti)
$PY - <<'EOF'
import pathlib
p=pathlib.Path('data/outcomes/NETGL.csv'); s=p.read_text().splitlines()
for i,l in enumerate(s):
    if l.startswith('5,'):
        parts=l.split(','); parts[2]='27.50'; s[i]=','.join(parts)
p.write_text("\n".join(s)+"\n")
EOF
run_tests m_g_unofficial_outcome "tests/test_faz5_live.py::test_l5_outcomes_regenerate_byte_equal" "tests/test_faz8_live.py::test_real_scores_break_seven_rows_match_recomputation" "tests/test_scoring.py::test_committed_scores_json_matches_recomputation"

# (g2) sonuç satırının bülten sha'sı MANIFEST'ten farklı
$PY - <<'EOF'
import pathlib
p=pathlib.Path('data/outcomes/NETGL.csv'); s=p.read_text().splitlines()
for i,l in enumerate(s):
    if l.startswith('5,'):
        parts=l.split(','); parts[13]='0'*64; s[i]=','.join(parts)
p.write_text("\n".join(s)+"\n")
EOF
run_tests m_g2_outcome_sha_mismatch "tests/test_faz5_live.py::test_l5_outcomes_regenerate_byte_equal" "tests/test_outcome_guard.py::test_outcome_rows_h_ge_2_follow_bulletin_commits" "tests/test_faz8_live.py::test_real_seven_machine_records_match_expected_and_pass_guard"

# (h) bir dondurulmuş kayıt silinmiş
git rm -q registry/records/CITAS/*.json
run_tests m_h_record_deleted "tests/test_freeze_records.py::test_each_frozen_ipo_has_an_active_record_and_no_duplicates" "tests/test_outcome_guard.py::test_sequence_rule_outcomes_follow_models_and_records" "tests/test_scoring.py::test_committed_scores_json_matches_recomputation"

# (i) deney günlüğünden bir satır silinmiş (Faz 8 resmi koşu)
$PY - <<'EOF'
import pathlib,json
p=pathlib.Path('experiments/log.jsonl'); lines=p.read_text().splitlines()
keep=[l for l in lines if not (json.loads(l).get('kind')=='backtest' and json.loads(l).get('context')=='official')]
assert len(keep)==len(lines)-1
p.write_text("\n".join(keep)+"\n")
EOF
run_tests m_i_log_line_deleted tests/test_experiment_log.py "tests/test_faz8_golden.py::test_b7_old_outputs_unchanged"

# (j) payda: ipos.csv'den bir FROZEN satır silinmiş
$PY - <<'EOF'
import pathlib
p=pathlib.Path('registry/ipos.csv'); lines=p.read_text().splitlines()
p.write_text("\n".join(l for l in lines if not l.startswith('NETGL,'))+"\n")
EOF
run_tests m_j_ipos_row_deleted tests/test_registry_ipos.py "tests/test_scoring.py::test_7_denominator"

# (k) sıra bekçisi devre dışı
$PY - <<'EOF'
import pathlib
p=pathlib.Path('borsai/scoring.py'); s=p.read_text()
s=s.replace('''    head = git.head()
    out: list[str] = []
    for rel, relevant in targets:''','''    head = git.head()
    out: list[str] = []
    targets = []
    for rel, relevant in targets:''')
p.write_text(s)
EOF
run_tests m_k_sequence_guard_disabled tests/test_outcome_guard.py -k "test_10"

# (l) hüküm dili gevşetilmiş: "geçiyor" aralık yerine noktasal farkla
$PY - <<'EOF'
import pathlib
p=pathlib.Path('borsai/scoring.py'); s=p.read_text()
s=s.replace('''    lo, hi = ci
    if hi < 0:
        return V_PASS''','''    lo, hi = ci
    if (lo + hi) / 2 < 0:
        return V_PASS''')
p.write_text(s)
EOF
run_tests m_l_verdict_loosened "tests/test_scoring.py::test_9a_interval_including_zero_says_indistinguishable" "tests/test_scoring.py::test_9e_verdict_vocabulary" "tests/test_scoring.py::test_backtest_primary_cells_and_verdicts" tests/test_metrics.py

# (m) push kanıtı dosyası sahte: created_at iki alanda da öne alınmış (iç tutarlı)
$PY - <<'EOF'
import json,pathlib
p=pathlib.Path('registry/push_proofs/7cb49cf5d2f9b3bfb1c2c0ca1d437fa5f313089d.json'); d=json.loads(p.read_text())
d['created_at']='2026-08-01T10:00:00Z'; d['github_response']['created_at']='2026-08-01T10:00:00Z'; d['github_response']['updated_at']='2026-08-01T10:00:00Z'
p.write_text(json.dumps(d,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
EOF
run_tests m_m_forged_proof_consistent tests/test_push_proof.py "tests/test_scoring.py::test_committed_scores_json_matches_recomputation"

# (n) model JSON'u INDEX'ten çıkarılmış (kayıtlı model sessizce listeden düşürülmüş)
$PY - <<'EOF'
import json,pathlib
p=pathlib.Path('models/INDEX.json'); d=json.loads(p.read_text()); d['models']=[m for m in d['models'] if m['model_id']!='v1_6_h99']
p.write_text(json.dumps(d,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
EOF
run_tests m_n_model_removed_from_index tests/test_models.py "tests/test_freeze_records.py::test_committed_record_consistency"
echo DONE

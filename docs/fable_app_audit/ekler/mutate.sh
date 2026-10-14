#!/usr/bin/env bash
# Mutasyon sürücüsü (FAZ3_FABLE_APP_AUDIT adım 3): her mutasyon klonda uygulanır, ilgili test koşar, geri alınır.
set -u
C=/tmp/borsai_app_audit/clone
L=/tmp/borsai_app_audit/mut
mkdir -p "$L"
cd "$C" && source app/scripts/env.sh
export CARGO_TARGET_DIR=/tmp/borsai_app_audit/target
[ -e "$C/.venv" ] || ln -s /Users/ahmet/Desktop/BorsAi/.venv "$C/.venv"
SUM="$L/summary.txt"; : > "$SUM"
PY=/Users/ahmet/Desktop/BorsAi/.venv/bin/python
run() { # run <name> <cmd...> ; logs rc
  local name=$1; shift
  local start=$(date +%s)
  ( cd "$C" && "$@" ) > "$L/$name.log" 2>&1; local rc=$?
  local end=$(date +%s)
  echo "$name rc=$rc dur=$((end-start))s :: $*" >> "$SUM"
}
revert() { (cd "$C" && GIT_OPTIONAL_LOCKS=0 git checkout -q -- "$@" && GIT_OPTIONAL_LOCKS=0 git status --porcelain -- "$@") ; }
cargo_t() { (cd "$C/app/src-tauri" && cargo test --offline "$@"); }
vitest_t() { (cd "$C/app" && npx vitest run "$@"); }

# (a) altın vektörde tek sayının son hanesi
$PY - <<'PYEOF'
import json
p="/tmp/borsai_app_audit/clone/app/parity/golden/v1_5_h99.jsonl"
lines=open(p,encoding="utf-8").read().split("\n")
for i,l in enumerate(lines):
    if not l: continue
    r=json.loads(l); o=r.get("expected",{}).get("output") or {}
    d5=(o.get("D5") or {})
    v=d5.get("p_up")
    if isinstance(v,float):
        s=repr(v); last=s[-1]
        new=s[:-1]+("1" if last!="1" else "2")
        d5["p_up"]=float(new); r["expected"]["output"]["D5"]=d5
        lines[i]=json.dumps(r,ensure_ascii=False,sort_keys=True)
        print(f"MUT(a) satır {i} case {r['case_id']} D5.p_up {s} -> {new} (|Δ|={abs(float(new)-v):e})")
        break
open(p,"w",encoding="utf-8").write("\n".join(lines))
PYEOF
run a_golden_digit cargo_t -p borsai_predict --test golden golden_parity
revert app/parity/golden/v1_5_h99.jsonl

# (b1) kırpma sınırı D3 üst 0.331 -> 0.332
sed -i '' 's/"D3" => ("-0.271", "0.331")/"D3" => ("-0.271", "0.332")/' app/src-tauri/crates/borsai_predict/src/horizons.rs
grep -n '0.332' app/src-tauri/crates/borsai_predict/src/horizons.rs >> "$SUM"
run b1_clip_bound cargo_t -p borsai_predict --test golden golden_parity
revert app/src-tauri/crates/borsai_predict/src/horizons.rs

# (b2) ridge katsayısı okunuşu: katsayılar ters sırayla eşlenir
sed -i '' 's/py_sum(coef.iter().zip(z.iter()).map(|(c, v)| c \* v)) + intercept/py_sum(coef.iter().rev().zip(z.iter()).map(|(c, v)| c * v)) + intercept/' app/src-tauri/crates/borsai_predict/src/linear.rs
grep -n 'coef.iter().rev()' app/src-tauri/crates/borsai_predict/src/linear.rs >> "$SUM"
run b2_ridge_coef_order cargo_t -p borsai_predict --test golden golden_parity
revert app/src-tauri/crates/borsai_predict/src/linear.rs

# (c) scores fixture n7: n = 7 iken live.cells dolu
$PY - <<'PYEOF'
import json
b="/tmp/borsai_app_audit/clone/app/tests/fixtures/scores/"
n7=json.load(open(b+"n7.json",encoding="utf-8")); n35=json.load(open(b+"n35.json",encoding="utf-8"))
n7["models"][0]["live"]["cells"]=n35["models"][0]["live"]["cells"][:1]
json.dump(n7,open(b+"n7.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)
print("MUT(c) n7 live.n_scored =",n7["models"][0]["live"]["n_scored"],"live.cells =",len(n7["models"][0]["live"]["cells"]))
PYEOF
run c_n7_cells_rust cargo_t --test stage4
run c_n7_cells_vitest vitest_t tests/accuracy.test.ts
revert app/tests/fixtures/scores/n7.json

# (d) n35: verdict geçiyor iken ci95 0'ı içeriyor
$PY - <<'PYEOF'
import json
b="/tmp/borsai_app_audit/clone/app/tests/fixtures/scores/"
d=json.load(open(b+"n35.json",encoding="utf-8"))
for c in d["models"][0]["live"]["cells"]:
    if c["verdict"]=="geçiyor":
        print("MUT(d) n35 hücre",c["rule_id"],c["horizon_or_k"],"ci95",c["ci95"],"-> [-0.009, 0.001]"); c["ci95"]=[-0.009,0.001]; break
json.dump(d,open(b+"n35.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)
PYEOF
run d_n35_verdict_ci0_rust cargo_t --test stage4
run d_n35_verdict_ci0_vitest vitest_t tests/accuracy.test.ts
revert app/tests/fixtures/scores/n35.json

# (e1) ön uç: beyanlı j doğrudan api çağrı satırında
$PY - <<'PYEOF'
p="/tmp/borsai_app_audit/clone/app/src/screens/results.ts"; s=open(p,encoding="utf-8").read()
old="await api.pathConditional(run.model_id, source, jOrT, stateName)"
new="await api.pathConditional(run.model_id, source, jOrT + store.view.declared.filter((x) => x).length, stateName)"
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(e1) uygulandı")
PYEOF
run e1_declared_in_api_line vitest_t tests/u52_declaration.test.ts
revert app/src/screens/results.ts

# (e2) ön uç: beyanlı j bir satır yukarıda türetilir, api satırı temiz
$PY - <<'PYEOF'
p="/tmp/borsai_app_audit/clone/app/src/screens/results.ts"; s=open(p,encoding="utf-8").read()
old="const j = store.view.jSelected ?? streak.j_observed ?? 0;"
new="const j = (store.view.jSelected ?? streak.j_observed ?? 0) + store.view.declared.filter((x) => x).length;"
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(e2) uygulandı")
PYEOF
run e2_declared_one_line_above_npm_test bash -c 'cd app && npm test'
revert app/src/screens/results.ts

# (f) git beyaz listesine commit
sed -i '' 's/pub const GIT_READONLY_SUBCOMMANDS: \[&str; 4\] = \["rev-parse", "status", "log", "ls-files"\];/pub const GIT_READONLY_SUBCOMMANDS: [\&str; 5] = ["rev-parse", "status", "log", "ls-files", "commit"];/' app/src-tauri/src/commands/git.rs
grep -n 'GIT_READONLY_SUBCOMMANDS' app/src-tauri/src/commands/git.rs | head -1 >> "$SUM"
run f_git_commit_whitelist cargo_t --test stage2 git_readonly_whitelist
revert app/src-tauri/src/commands/git.rs

# (g) senaryo yol bekçisi kaldırılır (tekli ve toplu dışa aktarma + scenarios_dir)
$PY - <<'PYEOF'
p="/tmp/borsai_app_audit/clone/app/src-tauri/src/commands/scenario.rs"; s=open(p,encoding="utf-8").read()
a="        if is_within(&dir, root) {"; b="        if is_within(target, root) {"
assert a in s and b in s
s=s.replace(a,"        if false && is_within(&dir, root) {").replace(b,"        if false && is_within(target, root) {")
open(p,"w",encoding="utf-8").write(s); print("MUT(g) uygulandı")
PYEOF
run g_guard_removed_stage2 cargo_t --test stage2 scenario_path_guard
run g_guard_removed_unit cargo_t --lib export_all_scenarios_array_and_guard
run g_guard_removed_e2e bash app/tests/e2e_freeze_tmp_repo.sh
revert app/src-tauri/src/commands/scenario.rs

# (h) bant: Sicil listesi SENARYO döndürür
$PY - <<'PYEOF'
p="/tmp/borsai_app_audit/clone/app/src/render/shell.ts"; s=open(p,encoding="utf-8").read()
old='  return { cls: "mode-official", head, note: TR.modeOfficialList };'
new='  return { cls: "mode-scenario", head: TR.modeScenario, note: TR.modeScenarioNote };'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(h) uygulandı")
PYEOF
run h_band_registry_scenario vitest_t tests/stage5.test.ts
revert app/src/render/shell.ts

# (i) resmi görünümde predict_all çağrısı
$PY - <<'PYEOF'
p="/tmp/borsai_app_audit/clone/app/src/screens/registry.ts"; s=open(p,encoding="utf-8").read()
old="    s.streak = await api.streakView(t.ticker);\n"
new="    s.streak = await api.streakView(t.ticker);\n    await api.predictAll({}, { value: null, refusal: null });\n"
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(i) uygulandı")
PYEOF
run i_official_predict_all vitest_t tests/registry.test.ts
revert app/src/screens/registry.ts

echo "=== klon durumu ===" >> "$SUM"
(cd "$C" && GIT_OPTIONAL_LOCKS=0 git status --porcelain) >> "$SUM"
echo DONE >> "$SUM"

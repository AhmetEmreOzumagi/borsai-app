#!/usr/bin/env bash
# Mutasyon sürücüsü (FAZ3_FABLE_APP_AUDIT_CLOSE adım 3): denetimin 11 mutasyonu + 6 yeni (j–o) + 1 varyant (j2).
# Klon /tmp/borsai_app_audit_close/clone (git clone --local, HEAD db8e239), ayrı CARGO_TARGET_DIR.
# Her mutasyon: uygula → ilgili test → `git checkout --` ile geri al. Kalıp: ekler/mutate.sh (Fable, 2026-09-23).
set -u
C=/tmp/borsai_app_audit_close/clone
L=/tmp/borsai_app_audit_close/mut
mkdir -p "$L"
cd "$C" && source app/scripts/env.sh
export CARGO_TARGET_DIR=/tmp/borsai_app_audit_close/target
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

# ============================================================ denetimin 11 mutasyonu (a … i)
# (a) altın vektörde tek sayının son hanesi
$PY - <<'PYEOF'
import json
p="/tmp/borsai_app_audit_close/clone/app/parity/golden/v1_5_h99.jsonl"
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
run a_golden_digit cargo_t -p borsai_predict --test golden golden_parity -- --nocapture
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
b="/tmp/borsai_app_audit_close/clone/app/tests/fixtures/scores/"
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
b="/tmp/borsai_app_audit_close/clone/app/tests/fixtures/scores/"
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
p="/tmp/borsai_app_audit_close/clone/app/src/screens/results.ts"; s=open(p,encoding="utf-8").read()
old="await api.pathConditional(run.model_id, source, jOrT, stateName)"
new="await api.pathConditional(run.model_id, source, jOrT + store.view.declared.filter((x) => x).length, stateName)"
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(e1) uygulandı")
PYEOF
run e1_declared_in_api_line vitest_t tests/u52_declaration.test.ts
revert app/src/screens/results.ts

# (e2) ön uç: beyanlı j bir satır yukarıda türetilir, api satırı temiz
$PY - <<'PYEOF'
p="/tmp/borsai_app_audit_close/clone/app/src/screens/results.ts"; s=open(p,encoding="utf-8").read()
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

# (g) senaryo yol bekçisi kaldırılır (guard_outside koşulu; kaydetme + tekli + toplu aynı bekçi)
$PY - <<'PYEOF'
p="/tmp/borsai_app_audit_close/clone/app/src-tauri/src/commands/scenario.rs"; s=open(p,encoding="utf-8").read()
a="        if is_within(p, root) {"
assert s.count(a)==1, s.count(a)
s=s.replace(a,"        if false && is_within(p, root) {")
open(p,"w",encoding="utf-8").write(s); print("MUT(g) uygulandı (guard_outside)")
PYEOF
run g_guard_removed_stage2 cargo_t --test stage2 scenario_path_guard
run g_guard_removed_unit cargo_t --lib export_all_scenarios_array_and_guard
run g_guard_removed_e2e bash app/tests/e2e_freeze_tmp_repo.sh
revert app/src-tauri/src/commands/scenario.rs

# (h) bant: Sicil listesi SENARYO döndürür
$PY - <<'PYEOF'
p="/tmp/borsai_app_audit_close/clone/app/src/render/shell.ts"; s=open(p,encoding="utf-8").read()
old='  return { cls: "mode-official", head, note: TR.modeOfficialList };'
new='  return { cls: "mode-scenario", head: TR.modeScenario, note: TR.modeScenarioNote };'
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(h) uygulandı")
PYEOF
run h_band_registry_scenario vitest_t tests/stage5.test.ts
revert app/src/render/shell.ts

# (i) resmi görünümde predict_all çağrısı
$PY - <<'PYEOF'
p="/tmp/borsai_app_audit_close/clone/app/src/screens/registry.ts"; s=open(p,encoding="utf-8").read()
old="    s.streak = await api.streakView(t.ticker);\n"
new="    s.streak = await api.streakView(t.ticker);\n    await api.predictAll({}, { value: null, refusal: null });\n"
assert old in s; open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(i) uygulandı")
PYEOF
run i_official_predict_all vitest_t tests/registry.test.ts
run i_official_predict_all_invoke vitest_t tests/screens_invoke.test.ts
revert app/src/screens/registry.ts

# ============================================================ yeni mutasyonlar (j … o)
# (j) B1 geri alınır: check_export_target'taki bağ reddi kalkar, resolve_path eski canonicalize davranışına döner
$PY - <<'PYEOF'
p="/tmp/borsai_app_audit_close/clone/app/src-tauri/src/commands/config.rs"; s=open(p,encoding="utf-8").read()
i=s.index("/// Sembolik bağ sınırı"); j=s.index("const PY_IMPORT")
old_canon='''/// MUT(j): eski canonicalize davranışı (askıda bağda en yakın var olan ataya düşer).
pub fn resolve_path(p: &Path) -> PathBuf {
    let mut cur = p.to_path_buf();
    let mut rest: Vec<std::ffi::OsString> = Vec::new();
    loop {
        if let Ok(c) = cur.canonicalize() {
            return rest.into_iter().rev().fold(c, |acc, part| acc.join(part));
        }
        match (cur.file_name().map(|s| s.to_os_string()), cur.parent()) {
            (Some(name), Some(parent)) => {
                rest.push(name);
                cur = parent.to_path_buf();
            }
            _ => return p.to_path_buf(),
        }
    }
}

'''
s=s[:i]+old_canon+s[j:]
open(p,"w",encoding="utf-8").write(s)
q="/tmp/borsai_app_audit_close/clone/app/src-tauri/src/commands/scenario.rs"; t=open(q,encoding="utf-8").read()
blk='''    if std::fs::symlink_metadata(target).is_ok_and(|m| m.file_type().is_symlink()) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("{} sembolik bağ; dışa aktarma bağı izlemez", target.display())));
    }
'''
assert t.count(blk)==1
open(q,"w",encoding="utf-8").write(t.replace(blk,""))
print("MUT(j) uygulandı: resolve_path eski canonicalize, check_export_target bağ reddi yok (write_export duruyor)")
PYEOF
run j_b1_reverted_stage2 cargo_t --test stage2 scenario_path_guard -- --nocapture
run j_b1_reverted_e2e bash app/tests/e2e_freeze_tmp_repo.sh
# (j2) varyant: (j) + write_export yerine eski std::fs::write (düzeltme öncesi tam hâl)
$PY - <<'PYEOF'
q="/tmp/borsai_app_audit_close/clone/app/src-tauri/src/commands/scenario.rs"; t=open(q,encoding="utf-8").read()
a='    write_export(target, &bytes, "senaryo dışa aktarılamadı")?;'
b='    write_export(target, pretty(&Value::Array(docs)).as_bytes(), "kişisel kayıtlar dışa aktarılamadı")?;'
assert a in t and b in t
t=t.replace(a,'    std::fs::write(target, &bytes).map_err(|e| io_error("senaryo dışa aktarılamadı", e))?;')
t=t.replace(b,'    std::fs::write(target, pretty(&Value::Array(docs)).as_bytes()).map_err(|e| io_error("kişisel kayıtlar dışa aktarılamadı", e))?;')
open(q,"w",encoding="utf-8").write(t); print("MUT(j2) uygulandı: + std::fs::write")
PYEOF
run j2_b1_fully_reverted_stage2 cargo_t --test stage2 scenario_path_guard -- --nocapture
revert app/src-tauri/src/commands/config.rs app/src-tauri/src/commands/scenario.rs

# (k) freeze_in'deki preflight denetimi kaldırılır
$PY - <<'PYEOF'
p="/tmp/borsai_app_audit_close/clone/app/src-tauri/src/commands/freeze.rs"; s=open(p,encoding="utf-8").read()
blk='''    if !pre.ok {
        return Err(AppError::new(FREEZE_PREFLIGHT_BLOCKED, format!("ön koşullar sağlanmıyor: {}", pre.blockers.join(", ")))
            .with_detail(serde_json::to_string_pretty(&pre).unwrap_or_default()));
    }
'''
assert s.count(blk)==1
open(p,"w",encoding="utf-8").write(s.replace(blk,"    let _ = pre; // MUT(k)\n")); print("MUT(k) uygulandı")
PYEOF
run k_freeze_no_preflight cargo_t --test stage3 freeze_refuses_when_preflight_blocked -- --nocapture
revert app/src-tauri/src/commands/freeze.rs

# (l) render/freeze.ts ready'den preflight?.ok kaldırılır
$PY - <<'PYEOF'
p="/tmp/borsai_app_audit_close/clone/app/src/render/freeze.ts"; s=open(p,encoding="utf-8").read()
old="const ready = vm.preflight?.ok === true && vm.pit !== null"
assert s.count(old)==1
open(p,"w",encoding="utf-8").write(s.replace(old,"const ready = vm.pit !== null")); print("MUT(l) uygulandı")
PYEOF
run l_freeze_ts_ready_no_preflight vitest_t tests/freeze.test.ts
revert app/src/render/freeze.ts

# (m) path.rs OUTPUT kaynağında None → gömülü sha geri
$PY - <<'PYEOF'
p="/tmp/borsai_app_audit_close/clone/app/src-tauri/src/commands/path.rs"; s=open(p,encoding="utf-8").read()
old='''        SOURCE_OUTPUT => match &source.params_sha256 {
            Some(sha) => (source.output.clone().unwrap_or(Value::Null), sha.clone(), None),
            None => return Err(AppError::new(INVALID_ARGUMENT, "çıktı kaynağı params_sha256 ister")),
        },
'''
new='''        SOURCE_OUTPUT => (
            source.output.clone().unwrap_or(Value::Null),
            source.params_sha256.clone().unwrap_or_else(|| embedded_sha.to_string()),
            None,
        ),
'''
assert s.count(old)==1
open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("MUT(m) uygulandı")
PYEOF
run m_path_output_sha_default cargo_t --test stage3 official_conditional_return_uses_record_only
revert app/src-tauri/src/commands/path.rs

# (n) bit_equal_floor.json'dan bir model silinir
$PY - <<'PYEOF'
import json
p="/tmp/borsai_app_audit_close/clone/app/parity/bit_equal_floor.json"
d=json.load(open(p,encoding="utf-8")); v=d["bit_equal_rows"].pop("v1_5_h99")
json.dump(d,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=2); print("MUT(n) v1_5_h99 tabanı silindi (idi:",v,")")
PYEOF
run n_floor_model_removed cargo_t -p borsai_predict --test golden golden_parity
revert app/parity/bit_equal_floor.json

# (o) test.sh'tan --include-ignored kaldırılır → env isteyen testler koşmaz; bunu hangi kontrol yakalıyor?
$PY - <<'PYEOF'
p="/tmp/borsai_app_audit_close/clone/app/scripts/test.sh"; s=open(p,encoding="utf-8").read()
old='''(cd src-tauri && BORSAI_REPO="$REPO" cargo test --workspace -- --include-ignored \\
  --exact --skip freeze_flow --skip prepare_screens --skip personal_isolation)
'''
assert s.count(old)==1, s
open(p,"w",encoding="utf-8").write(s.replace(old,'(cd src-tauri && BORSAI_REPO="$REPO" cargo test --workspace)\n')); print("MUT(o) uygulandı")
PYEOF
run o_test_sh_no_include_ignored bash app/scripts/test.sh
revert app/scripts/test.sh

echo "=== klon durumu ===" >> "$SUM"
(cd "$C" && GIT_OPTIONAL_LOCKS=0 git status --porcelain) >> "$SUM"
echo DONE >> "$SUM"

"""K3 (F9): denetimin d ve p mutasyonları (docs/fable_faz7c_audit/ekler/mutate.sh çapaları aynen) yeni semantik testlerde kırmızı mı?
Her mutasyon yedekten geri alınır; borsai/ ağacının sha'sı önce/sonra aynı olmalı."""
import hashlib, pathlib, shutil, subprocess, sys
ROOT = pathlib.Path.cwd()
PY = str(ROOT / ".venv/bin/python")
T = "tests/test_faz7c_freeze.py"
SIGN = [f"{T}::test_f9_high_f3_in_training_gives_higher_p_up"]
INV = [f"{T}::test_f9_fold_fit_is_bit_equal_when_test_ipo_inputs_change"]

def tree():
    sys.path.insert(0, str(ROOT))
    from borsai.provenance import source_tree_sha256
    return source_tree_sha256(ROOT / "borsai")["tree_sha256"]

def run(name, targets):
    r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-header", *targets], cwd=ROOT, capture_output=True, text=True)
    last = [l for l in r.stdout.splitlines() if l.strip()][-1]
    fails = [l for l in r.stdout.splitlines() if l.startswith("FAILED")]
    print(f"{name}: rc={r.returncode} :: {last}")
    for f in fails:
        print("   ", f.split(" - ")[0])

MUTS = {
 "d_clip_bounds_include_test_ipo": ("borsai/fit.py", [(
  '        final = pp.fit_preprocessing({t: raw[t] for t in used}, {t: filter_status.get(t) for t in used}, recipe=recipe)\n        if test_raw is not None and not final.insufficient_feature_variation:',
  '        final = pp.fit_preprocessing({**{t: raw[t] for t in used}, **({"__test__": test_raw} if test_raw is not None else {})}, {t: filter_status.get(t) for t in used}, recipe=recipe)\n        if test_raw is not None and not final.insufficient_feature_variation:')], INV + SIGN),
 "p_label_direction_flipped": ("borsai/backtest.py", [(
  '"order": list(f.training), "raw": {t: raw[t] for t in f.training}, "Y": {t: by[t].targets[f.horizon].Y for t in f.training},',
  '"order": list(f.training), "raw": {t: raw[t] for t in f.training}, "Y": {t: 1 - by[t].targets[f.horizon].Y for t in f.training},'), (
  '        hf = fitmod.fit_fall_horizon([r.ticker for r in rows], raw, {r.ticker: r.targets[h].Y for r in rows}, status,',
  '        hf = fitmod.fit_fall_horizon([r.ticker for r in rows], raw, {r.ticker: 1 - r.targets[h].Y for r in rows}, status,')], SIGN + INV),
 "p1_backtest_fold_only": ("borsai/backtest.py", [(
  '"order": list(f.training), "raw": {t: raw[t] for t in f.training}, "Y": {t: by[t].targets[f.horizon].Y for t in f.training},',
  '"order": list(f.training), "raw": {t: raw[t] for t in f.training}, "Y": {t: 1 - by[t].targets[f.horizon].Y for t in f.training},')], SIGN),
 "p2_final_fit_only": ("borsai/backtest.py", [(
  '        hf = fitmod.fit_fall_horizon([r.ticker for r in rows], raw, {r.ticker: r.targets[h].Y for r in rows}, status,',
  '        hf = fitmod.fit_fall_horizon([r.ticker for r in rows], raw, {r.ticker: 1 - r.targets[h].Y for r in rows}, status,')], SIGN),
}
before = tree()
print(f"borsai/ ağacı önce: {before}")
run("0_mutasyonsuz", SIGN + INV)
for name, (path, reps, targets) in MUTS.items():
    p = ROOT / path
    bak = pathlib.Path(sys.argv[1]) / (p.name + ".bak")
    shutil.copyfile(p, bak)
    s = p.read_text(encoding="utf-8")
    for old, new in reps:
        assert s.count(old) == 1, (name, old[:60])
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")
    try:
        run(name, targets)
    finally:
        shutil.copyfile(bak, p)
    assert hashlib.sha256(p.read_bytes()).hexdigest() == hashlib.sha256(bak.read_bytes()).hexdigest()
after = tree()
print(f"borsai/ ağacı sonra: {after} ({'aynı' if after == before else 'FARKLI'})")

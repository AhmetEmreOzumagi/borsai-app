"""Adım 8: experiments/log.jsonl satırlarının spec/veri/ledger hash'leri (borsai import edilmez)."""
from __future__ import annotations
import sys, json
from pathlib import Path
from collections import Counter
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa

lines = [json.loads(l) for l in (ROOT / "experiments/log.jsonl").read_text(encoding="utf-8").splitlines()]
print("lines", len(lines), Counter(l.get("kind") for l in lines))
bt = [l for l in lines if l.get("kind") == "backtest"]
print("backtest contexts", Counter(l["context"] for l in bt))
print("distinct model_id in log:", len({l.get("model_id") for l in lines if l.get("model_id")}))
tt_sha = sha256_file(ROOT / "data/training_table.csv"); tt2_sha = sha256_file(ROOT / "data/training_table_v2.csv")
dv = load_json(ROOT / "data/data_version.json"); dv2 = load_json(ROOT / "data/data_version_v2.json")
dv_sha = sha256_file(ROOT / "data/data_version.json"); dv2_sha = sha256_file(ROOT / "data/data_version_v2.json")
print("data_version.json sha", dv_sha[:12], "v2", dv2_sha[:12], "| training_table sha", tt_sha[:12], "v2", tt2_sha[:12])
print("data_version_sha256 values in log:", Counter(l.get("data_version_sha256", "")[:12] for l in lines))
print("training_table_sha256 values in backtest lines:", Counter(l.get("training_table_sha256", "")[:12] for l in bt))
# ledger sha: find by name in golden dirs
ledgers = {}
for d in (ROOT / "tests/reference").glob("macos_golden*"):
    for f in d.glob("*.csv"):
        ledgers.setdefault(sha256_file(f), []).append(f.relative_to(ROOT).as_posix())
for f in (ROOT / "docs/faz8/backtest").glob("*.csv"):
    ledgers.setdefault(sha256_file(f), []).append(f.relative_to(ROOT).as_posix())
found = 0; missing = []
for l in bt:
    s = l.get("ledger_sha256")
    if s in ledgers: found += 1
    else: missing.append((l["context"], l["model_id"], l.get("run_key")))
print(f"backtest ledger_sha256 found among golden/docs ledgers: {found}/{len(bt)}; missing: {len(missing)}")
print("  missing by context:", Counter(m[0] for m in missing))
# spec document sha
ok = bad = 0; nodoc = 0
for l in lines:
    sd = l.get("spec_document"); ss = l.get("spec_document_sha256")
    if not sd: nodoc += 1; continue
    if sha256_file(ROOT / sd) == ss: ok += 1
    else: bad += 1; print("  spec doc sha mismatch:", sd, l.get("kind"), l.get("model_id"))
print(f"spec_document_sha256 == file at HEAD: ok {ok}, bad {bad}, lines without spec_document {nodoc}")
# decisions doc
ok = bad = 0
for l in lines:
    sd = l.get("decisions_document"); ss = l.get("decisions_document_sha256")
    if not sd: continue
    if sha256_file(ROOT / sd) == ss: ok += 1
    else: bad += 1; print("  decisions doc sha mismatch:", sd, l.get("context"))
print(f"decisions_document_sha256 ok {ok} bad {bad}")
# sensitivity lines
sens = [l for l in lines if l.get("kind") == "sensitivity"]
print("sensitivity contexts:", Counter(l.get("context") for l in sens))
# variants same data per data version (E16): distinct (model_id, spec_sha256) backtest + exploration
for dv_s in {l.get("data_version_sha256") for l in lines if l.get("data_version_sha256")}:
    pairs = {(l["model_id"], l["spec_sha256"]) for l in lines if l.get("kind") == "backtest" and l.get("data_version_sha256") == dv_s}
    expl = sum(1 for l in lines if l.get("kind") == "exploration" and l.get("data_version_sha256") == dv_s)
    print(f"data version {dv_s[:12]}: backtest (model,spec) pairs {len(pairs)} + exploration {expl} = {len(pairs)+expl}")
sc = load_json(ROOT / "scores/scores.json")
print("scores.json card n_variants_same_data:", Counter(m["card"].get("n_variants_same_data") for m in sc["models"]))
# git append-only check
import subprocess, os
e = dict(os.environ); e["GIT_OPTIONAL_LOCKS"] = "0"
out = subprocess.run(["git", "-C", str(ROOT), "log", "--format=%h", "--numstat", "--", "experiments/log.jsonl"], check=True, capture_output=True, text=True, env=e).stdout.split()
dels = [x for i, x in enumerate(out) if i > 0 and out[i-1].isdigit() and x.isdigit()]
print("log.jsonl numstat (added, deleted) pairs:", [(out[i], out[i+1]) for i in range(len(out)-1) if out[i].isdigit() and out[i+1].isdigit()][:20])
# each historical version is a prefix of the next
hist = subprocess.run(["git", "-C", str(ROOT), "log", "--reverse", "--format=%H", "--", "experiments/log.jsonl"], check=True, capture_output=True, text=True, env=e).stdout.split()
prev = b""; prefix_ok = True
for c in hist:
    cur = subprocess.run(["git", "-C", str(ROOT), "show", f"{c}:experiments/log.jsonl"], check=True, capture_output=True, env=e).stdout
    if not cur.startswith(prev): prefix_ok = False; print("  NOT prefix at", c[:7])
    prev = cur
print("every committed log version is a byte-prefix of the next:", prefix_ok, "| current file equals HEAD version:", prev == (ROOT / "experiments/log.jsonl").read_bytes())

import json, hashlib, sys
from pathlib import Path
ROOT = Path('/Users/ahmet/Desktop/BorsAi')
def canon(v): return hashlib.sha256(json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",",":"), allow_nan=False).encode()).hexdigest()
idx = json.load(open(ROOT/'models/INDEX.json'))
print("schema:", idx.get("schema_version"), "n_models:", len(idx["models"]))
bad = 0
for e in idx["models"]:
    p = ROOT/'models'/e["file"]
    fb = p.read_bytes()
    d = json.loads(fb)
    file_sha = hashlib.sha256(fb).hexdigest()
    spec_sha = canon(d["spec"])
    ok_file = file_sha == e["sha256"]
    ok_spec = spec_sha == d["spec_sha256"] == e["spec_sha256"]
    ok_id = d["model_id"] == e["model_id"]
    doc = d["spec"].get("spec_document")
    doc_ok = "n/a"
    if doc:
        dp = ROOT/doc["path"]
        if dp.exists():
            doc_ok = hashlib.sha256(dp.read_bytes()).hexdigest() == doc["sha256"]
        else:
            doc_ok = "MISSING:"+doc["path"]
    tr = d.get("training", {})
    print(f"{e['model_id']:32s} file={ok_file} spec={ok_spec} id={ok_id} doc={doc_ok} n={e['training_n']}/{tr.get('n')} alg={e['algorithm']} cutoff={e['training_cutoff_date']} frozen={e['frozen_at'][:10]} status={e['status']}")
    if not (ok_file and ok_spec and ok_id and doc_ok in (True,"n/a")): bad += 1
print("BAD:", bad)

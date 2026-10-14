"""Adım 7: eski kohort — sayılar, sıra kuralı, açık küme birincil hücreleri (borsai import edilmez; kod adı basılmaz)."""
from __future__ import annotations
import sys, json, math
from decimal import Decimal
from pathlib import Path
from collections import Counter
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa

coh = read_csv(ROOT / "registry/oot/cohort_pre_h99.csv")
members = [r for r in coh if r["status"] == "MEMBER"]
open_set = [r for r in members if r["vault"] in ("OPEN", "EXPOSED_ARCHIVE", "EXPOSED_CODEX")]
sealed = [r for r in members if r["vault"] == "SEALED"]
print("members", len(members), "open set", len(open_set), "sealed", len(sealed), Counter(r["vault"] for r in members))
proofs = load_proofs()
# per-member: first record commit & proof; ingest commit & proof
def recs(t):
    d = ROOT / "registry/oot/records" / t
    out = []
    for p in sorted(d.glob("*.json")):
        r = load_json(p); out.append((p, r))
    return out
def ingest(t):
    paths = [f"data/outcomes_oot/{t}.csv", f"data/outcomes_oot/raw/{t}.json", f"registry/oot/d1_rows/{t}.json"]
    return earliest(added_commit(p) for p in paths)
stats = Counter(); ingest_commits = Counter(); rec_commits = Counter()
model_commits = {e["model_id"]: added_commit(f"models/{e['file']}") for e in load_json(ROOT / "models/INDEX.json")["models"]}
old19 = [e["model_id"] for e in load_json(ROOT / "models/INDEX.json")["models"][:19]]
new8 = [e["model_id"] for e in load_json(ROOT / "models/INDEX.json")["models"][19:]]
blind_new8_open = blind_new8_sealed = 0
for r in members:
    t = r["ticker"]; rr = recs(t)
    first = next((p for p, x in rr if not x.get("record_scope")), None); delta = next((p for p, x in rr if x.get("record_scope") == "ONLY_MISSING_MODELS"), None)
    ic = ingest(t); ip = proof_time(ic, proofs)
    fc = added_commit(first.relative_to(ROOT).as_posix()); fp = proof_time(fc, proofs)
    dc = added_commit(delta.relative_to(ROOT).as_posix()); dp = proof_time(dc, proofs)
    ingest_commits[ic[:7]] += 1; rec_commits[(fc[:7], dc[:7])] += 1
    ok_first = is_ancestor(fc, ic) and fp is not None and ip is not None and fp < ip and all(is_ancestor(model_commits[m], ic) for m in old19)
    stats["first_ok" if ok_first else "first_BAD"] += 1
    ok_delta = is_ancestor(dc, ic) and dp is not None and ip is not None and dp < ip and all(is_ancestor(model_commits[m], ic) for m in new8)
    if r["vault"] == "SEALED":
        blind_new8_sealed += ok_delta
    else:
        blind_new8_open += ok_delta
print("ingest commits:", dict(ingest_commits)); print("(first,delta) record commits:", dict(rec_commits)); print(dict(stats))
print(f"new-8-model records before ingest (OOT_BLIND eligible): open {blind_new8_open}/{len(open_set)}, sealed {blind_new8_sealed}/{len(sealed)}")
# cohort-level gate: all members' first records are ancestors of every ingest
gate_ok = all(is_ancestor(added_commit(next(p for p, x in recs(r["ticker"]) if not x.get("record_scope")).relative_to(ROOT).as_posix()), ingest(r2["ticker"])) for r2 in open_set for r in members[:5])
print("cohort gate spot check (5 members x all open ingests):", gate_ok)
pt = {c: proof_time(c, proofs) for c in ("1dcceff58c4399958cd12dd536cc467889070371", "28aaa3bd5ddae7ddde52e207558ddc984c9aedf6", "77b54f785fd03480dbb7cc9573eedce0d3cd0c57", "9e1e992328a552e416aa4e5165d6d19a0a828029", "2f914dd76117babbc52f5b8853e43a891f3a53f8", "71b9071e894563d079a8182f91f48ba84a9bd0f9", "7ade6a8df18dc7a4ef031a9cb9de7e3332edcc57", "5a96e25ae43051b7a599b54a42477d0a265408f7")}
print("proof times:", {k[:7]: v for k, v in pt.items()})
# ---- open-set primary cells from records + outcomes (numpy PCG64 bootstrap)
def np_ci(d, blocks):
    if len(d) < 10 or len(set(blocks)) < 6: return None
    rng = np.random.Generator(np.random.PCG64(20260921)); ids = sorted(set(blocks))
    by = {b: [x for x, bb in zip(d, blocks) if bb == b] for b in ids}
    stats_ = []
    for _ in range(4000):
        s = [x for b in rng.choice(ids, size=len(ids), replace=True) for x in by[str(b)]]
        stats_.append(sum(s) / len(s))
    lo, hi = np.percentile(stats_, [2.5, 97.5]); return [float(lo), float(hi)]
oot = load_json(ROOT / "scores/scores_oot.json")
def outcome(t):
    p = ROOT / "data/outcomes_oot" / f"{t}.csv"
    return read_csv(p) if p.exists() else None
def first_record(t):
    return next(x for p, x in recs(t) if not x.get("record_scope"))
def paired(mid, subset, loss):
    d, mo, a, b = [], [], [], []
    for r in subset:
        t = r["ticker"]; rec = first_record(t); out = outcome(t)
        if out is None: continue
        cell = next(c for c in rec["models"] if c["model_id"] == mid)
        la_lb = loss(cell, rec, out)
        if la_lb is None: continue
        la, lb = la_lb; a.append(la); b.append(lb); d.append(la - lb); mo.append(out[0]["session_date"][:7])
    n = len(d); ci = np_ci(d, mo)
    return dict(n=n, n_blocks=len(set(mo)), model=sum(a)/n, rule=sum(b)/n, diff=sum(d)/n, ci=ci, wins=sum(x<0 for x in d), losses=sum(x>0 for x in d))
def loss_mae_d5(cell, rec, out):
    if cell["status"] != "PREDICTED": return None
    row5 = next((x for x in out if x["h"] == "5"), None)
    if row5 is None or row5["status"] != "OK": return None
    R = float(Decimal(row5["R_h"])); pm = cell["output"]["D5"]["return"]; pr = rec["comparators"]["base_train_median"]["output"]["D5"]["return"]
    return abs(pm - R), abs(pr - R)
def loss_rps(cell, rec, out):
    if cell["status"] != "PREDICTED": return None
    labs = [x["ceiling_close"] for x in out[:10]]
    if len(labs) < 10 or any(x not in ("0", "1") for x in labs): return None
    L = 0
    for x in labs:
        if x == "1": L += 1
        else: break
    S = cell["output"]["S"]; Sk = rec["comparators"]["base_km_expanding"]["output"]["S"]
    rps = lambda S_: sum((S_[k-1] - (1.0 if L >= k else 0.0)) ** 2 for k in range(1, 11)) / 10
    return rps(S), rps(Sk)
def oot_cell(key, mid):
    b = oot[key]; m = next(x for x in b["models"] if x["model_id"] == mid)
    return next(({k: c[k] for k in ("diff", "ci95", "n", "n_blocks", "wins", "losses", "verdict")} for c in m["cells"] if c.get("label") == "birincil"), None)
for mid, loss in (("v1_5_h99", loss_mae_d5), ("ceiling_hazard_v0", loss_rps), ("pb_v0", loss_mae_d5)):
    for key, subset in (("oot_pre_h99", open_set), ("oot_pre_h99_sealed", sealed)):
        mine = paired(mid, subset, loss); print(key, mid, "mine:", json.dumps({k: (round(v, 6) if isinstance(v, float) else v) for k, v in mine.items()}))
        print("   scores_oot:", json.dumps(oot_cell(key, mid)))
# regime NA count check for base_always etc skipped. Verify n_scored for v1_5 open = 68 (3 refused)
m = next(x for x in oot["oot_pre_h99"]["models"] if x["model_id"] == "v1_5_h99")
print("scores_oot v1_5_h99 open counters:", {k: m[k] for k in m if k.startswith("n_")})
# vault marker
vo = load_json(ROOT / "registry/oot/VAULT_OPEN.json"); print("VAULT_OPEN:", {k: vo[k] for k in vo if k in ("n_sealed", "redownload", "cohort", "manifest_oot_before")})
print("MANIFEST_OOT rows:", len(read_csv(ROOT / "data/raw/bist/MANIFEST_OOT.csv")))

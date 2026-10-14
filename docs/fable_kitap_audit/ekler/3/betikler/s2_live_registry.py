"""Adım 2: canlı sicili sıfırdan yeniden üret (SPEC_SCORING §5–§6; borsai import edilmez)."""
from __future__ import annotations
import json, sys
from decimal import Decimal
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa

F3_MODELS = {"v1_5_h99", "v1_6_h99", "v1_5_market20_v0", "ceiling_hazard_v0", "ceiling_path_v0",
             "ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled",
             "fall_d10_v0_h99", "fall_d10_v0_pooled"}
INPUT_FIELDS = ("ipo_price_tl", "shares_offered", "ipo_size_tl", "post_ipo_share_capital", "capital_increase_shares",
                "existing_share_sale_shares", "additional_sale_shares", "total_demand_multiple", "total_demand_filter_status",
                "first_trading_date", "bookbuilding_start", "bookbuilding_end", "ipo_price_try", "planned_pre_ipo_capital",
                "planned_post_ipo_capital", "planned_capital_increase_shares", "planned_existing_share_sale",
                "planned_additional_sale_ceiling", "planned_base_offer_shares", "planned_max_offer_shares")

proofs = load_proofs()
index = load_json(ROOT / "models/INDEX.json")
models = {e["model_id"]: e for e in index["models"]}
ipos = read_csv(ROOT / "registry/ipos.csv")
frozen = [r for r in ipos if r["status"] == "FROZEN"]
legacy = load_json(ROOT / "registry/legacy_roles.json")
scores = load_json(ROOT / "scores/scores.json")
HEAD = head()

def inputs_pit_problems(doc, d1):
    probs = []
    f = doc["fields"]
    for name in INPUT_FIELDS:
        x = f.get(name) or {}
        if x.get("value") is None or not x.get("source_published_at"):
            continue
        if not istanbul_date(x["source_published_at"]) < d1:
            probs.append(f"{name}: pub not before D1")
        sp = x.get("source_path")
        if sp:
            p = ROOT / sp
            if not p.exists():
                probs.append(f"{name}: doc missing")
            elif sha256_file(p) != x["source_sha256"]:
                probs.append(f"{name}: doc sha mismatch")
    return probs

def record_pit_problems(rec, d1):
    probs = inputs_pit_problems(rec["inputs"]["document"], d1)
    m = rec.get("market20") or {}
    if m.get("f6") is not None and not (m["S0_date"] < m["ref_date"] <= d1):
        probs.append("f6 window")
    return probs

def model_evidence(mid):
    rel = f"models/{models[mid]['file']}"
    c = added_commit(rel)
    return c, proof_time(c, proofs)

def realized(ticker):
    p = ROOT / "data/outcomes" / f"{ticker}.csv"
    rows = read_csv(p) if p.exists() else []
    d1 = rows[0]["session_date"] if rows else None
    dates = [r["session_date"] for r in rows if r["status"] in ("OK", "NA_LIMIT")]
    return d1, dates, rows

def outcome_ingest_commit(ticker, dates):
    paths = [f"data/outcomes/{ticker}.csv"]
    for d in dates:
        for kind in ("thb", "thm"):
            paths.append(f"data/raw/bist/{kind}/{d[:4]}/{kind}{d.replace('-', '')}1.zip")
    return earliest(added_commit(p) for p in paths)

def legacy_packet_values(entry):
    pk = next((p for p in entry["files"] if p.endswith("_pretrade_evidence_packet.csv")), None)
    if pk is None:
        return None
    return {r["field"]: r["normalized_value"] for r in read_csv(ROOT / pk)}

LEGACY_MAP = {"ipo_price_tl": "ipo_price_tl", "shares_offered_final": "shares_offered",
              "capital_increase_shares": "capital_increase_shares", "post_ipo_share_capital": "post_ipo_share_capital",
              "f3": "total_demand_multiple"}

def legacy_pit_ok(entry, doc, d1):
    vals = legacy_packet_values(entry)
    if vals is None or doc is None:
        return False
    for a, b in LEGACY_MAP.items():
        va, vb = vals.get(a), doc["fields"][b]["value"]
        try:
            if va is None or vb is None or Decimal(str(va)) != Decimal(str(vb)):
                return False
        except Exception:
            return False
    return not inputs_pit_problems(doc, d1)

def candidates(ticker, mid, d1):
    out = []
    rdir = ROOT / "registry/records" / ticker
    recs = [(p, load_json(p)) for p in sorted(rdir.glob("*.json"))] if rdir.exists() else []
    cancelled = {r["cancels"]["file"] for _, r in recs if r.get("record_type") == "CANCELLATION"}
    for p, rec in recs:
        if rec.get("record_type") != "PREDICTION":
            continue
        cell = next((c for c in rec["models"] if c["model_id"] == mid), None)
        if cell is None:
            continue
        rel = p.relative_to(ROOT).as_posix()
        c = added_commit(rel)
        pit = record_pit_problems(rec, d1)
        out.append(dict(record_id=p.name, track="REGISTRY", has_f3=rec["inputs"]["document"]["fields"]["total_demand_multiple"]["value"] is not None,
                        recorded_at=rec["recorded_at_utc"], push=proof_time(c, proofs), pit_ok=not pit, pit=pit,
                        cancelled=p.name in cancelled, invalid=False, cell=cell, commit=c,
                        bookbuilding_start=rec["inputs"]["document"]["fields"]["bookbuilding_start"]["value"]))
    doc_path = ROOT / "registry/inputs" / f"{ticker}.json"
    doc = load_json(doc_path) if doc_path.exists() else None
    for e in legacy["records"]:
        if e["ticker"] != ticker or e["model_id"] != mid:
            continue
        push = None
        if e["time_proof"] == "GIT_PUSH":
            pr = load_json(ROOT / e["push_proof_file"])
            assert pr["created_at"] == e["push_proof_created_at"]
            assert str(pr["url"]).endswith("/statuses/" + e["old_repo_commit"])
            push = pr["created_at"]
        out.append(dict(record_id=e["record"], track="GIT_PUSH" if e["time_proof"] == "GIT_PUSH" else "SELF_REPORTED",
                        has_f3=bool(e["has_official_f3"]), recorded_at=e.get("prediction_timestamp_self_reported") or "",
                        push=push, pit_ok=legacy_pit_ok(e, doc, d1), pit=[], cancelled=False,
                        invalid=e["role"] == "INVALID_USE", cell=None, commit=e.get("old_repo_commit"), bookbuilding_start=None))
    return out

def proven_before(c, d1):
    return c["push"] is not None and istanbul_date(c["push"]) < d1

def select_primary(mid, cands, d1):
    pool = [c for c in cands if not c["cancelled"] and not c["invalid"]]
    res = {}
    for track_name, tracks in (("proven", ("REGISTRY", "GIT_PUSH")), ("self_reported", ("SELF_REPORTED",))):
        cs = [c for c in pool if c["track"] in tracks]
        choice, rule = None, None
        if mid in F3_MODELS:
            cs = [c for c in cs if c["has_f3"]]
            live = [c for c in cs if proven_before(c, d1)]
            if live:
                choice = max(live, key=lambda c: (c["push"], c["recorded_at"])); rule = "LATEST_PUSH_PROVEN_BEFORE_D1"
            else:
                late = [c for c in cs if c["pit_ok"]]
                if late:
                    choice = min(late, key=lambda c: (c["push"] or "9999", c["recorded_at"])); rule = "EARLIEST_LATE_RECORD"
        elif cs:
            choice = min(cs, key=lambda c: (c["push"] or "9999", c["recorded_at"])); rule = "EARLIEST_RECORD"
        res[track_name] = (choice, rule or "NO_ELIGIBLE_RECORD")
    return res

def classify(prospective, live, pit_ok):
    if prospective and live:
        return "LIVE"
    if prospective and pit_ok:
        return "LATE_RECORD"
    return "RETRO"

report = {"models": {}, "retro_pairs": [], "mismatch": []}
score_models = {m["model_id"]: m for m in scores["models"]}
score_retro = {(r["model_id"], r["ticker"]): r for r in scores["retro_info"]}
my_retro = set()
n_checks = 0
for mid in models:
    mc, mp = model_evidence(mid)
    rows = {}
    for ipo in frozen:
        t = ipo["ticker"]
        d1, dates, _ = realized(t)
        d1 = d1 or ipo["first_trading_date"]
        oc = outcome_ingest_commit(t, dates)
        target = oc or HEAD
        prospective = mc is not None and mp is not None and is_ancestor(mc, target)
        cands = candidates(t, mid, d1)
        sel = select_primary(mid, cands, d1)
        choice, rule = sel["proven"]
        if choice is None:
            refused = sorted([c for c in cands if c["track"] == "REGISTRY" and not c["cancelled"] and c["cell"]["status"] == "REFUSED"],
                             key=lambda c: c["recorded_at"])
            if refused:
                choice, rule = refused[0], "REFUSED_IN_EARLIEST_RECORD"
            else:
                if not prospective:
                    my_retro.add((mid, t))
                    rows[t] = dict(klass="RETRO", record=None, basis="NO_RECORD")
                else:
                    rows[t] = dict(klass="PROSPECTIVE_NO_RECORD", record=None)
                continue
        live = proven_before(choice, d1) if choice["push"] else False
        if choice["track"] == "SELF_REPORTED":
            klass = "LEGACY_SELF_REPORTED" if prospective else "RETRO"
        else:
            klass = classify(prospective, live, choice["pit_ok"])
        status = "REFUSED" if (choice["cell"] is not None and choice["cell"]["status"] == "REFUSED") else "SCORED"
        rows[t] = dict(klass=klass, record=choice["record_id"], rule=rule, status=status, pit=choice["pit"],
                       model_commit=mc, model_push=mp, outcome_commit=oc, record_push=choice["push"], live=live)
        if klass == "RETRO":
            my_retro.add((mid, t))
        # self-reported track
        sc, _ = sel["self_reported"]
        if sc is not None:
            rows[t]["self_reported"] = dict(record=sc["record_id"], klass="LEGACY_SELF_REPORTED" if prospective else "RETRO")
    report["models"][mid] = dict(model_commit=mc, model_push=mp, rows=rows)
    # compare with scores.json
    sm = score_models.get(mid)
    if sm is None:
        report["mismatch"].append(f"{mid}: not in scores.json"); continue
    live = sm["live"]
    sc_rows = {r["ticker"]: r for r in live["rows"]}
    for t, r in rows.items():
        n_checks += 1
        if r["klass"] in ("LIVE", "LATE_RECORD"):
            s = sc_rows.get(t)
            if s is None or s["class"] != r["klass"] or s["record_id"] != r["record"] or s["status"] != r["status"]:
                report["mismatch"].append(f"{mid}/{t}: mine {r['klass']}/{r['record']}/{r['status']} vs scores {None if s is None else (s['class'], s['record_id'], s['status'])}")
        elif r["klass"] == "RETRO":
            if (mid, t) not in score_retro:
                report["mismatch"].append(f"{mid}/{t}: mine RETRO but not in retro_info")
            elif t in sc_rows:
                report["mismatch"].append(f"{mid}/{t}: mine RETRO but scores has live row")
        else:
            report["mismatch"].append(f"{mid}/{t}: unexpected {r['klass']}")
    for t in sc_rows:
        if t not in rows or rows[t]["klass"] not in ("LIVE", "LATE_RECORD"):
            report["mismatch"].append(f"{mid}/{t}: scores has live row, mine {rows.get(t)}")
    # self reported rows
    srs = {r["ticker"]: r for r in live.get("self_reported_rows", [])}
    mine_sr = {t: r["self_reported"] for t, r in rows.items() if r.get("self_reported")}
    if set(srs) != set(mine_sr):
        report["mismatch"].append(f"{mid}: self_reported rows differ: scores {sorted(srs)} mine {sorted(mine_sr)}")
    # counters
    my_scored = [r for r in rows.values() if r["klass"] in ("LIVE", "LATE_RECORD") and r.get("status") == "SCORED"]
    my_live = sum(r["klass"] == "LIVE" for r in my_scored); my_late = sum(r["klass"] == "LATE_RECORD" for r in my_scored)
    my_ref = sum(r["klass"] in ("LIVE", "LATE_RECORD") and r.get("status") == "REFUSED" for r in rows.values())
    cnt = dict(n_scored=len(my_scored), n_live=my_live, n_late=my_late, n_refused=my_ref,
               n_rows=sum(r["klass"] in ("LIVE", "LATE_RECORD") for r in rows.values()))
    sc_cnt = {k: live[k] for k in cnt}
    if cnt != sc_cnt:
        report["mismatch"].append(f"{mid}: counters mine {cnt} vs scores {sc_cnt}")
    report["models"][mid]["counters"] = cnt

retro_in_scores = set(score_retro)
if my_retro != retro_in_scores:
    report["mismatch"].append(f"retro_info set differs: only mine {sorted(my_retro - retro_in_scores)}; only scores {sorted(retro_in_scores - my_retro)}")

print("pairs checked:", n_checks, "retro pairs:", len(my_retro), "mismatches:", len(report["mismatch"]))
for m in report["mismatch"]:
    print("  MISMATCH:", m)
# summary of classes
from collections import Counter
cls = Counter()
for mid, m in report["models"].items():
    for t, r in m["rows"].items():
        cls[(r["klass"])] += 1
print("class totals over 27x7:", dict(cls))
# detail of key pairs
for mid in ("v1_5_h99",):
    for t, r in report["models"][mid]["rows"].items():
        print(mid, t, r["klass"], r.get("rule"), r.get("record"), "model_commit", (r.get("model_commit") or "")[:7], "model_push", r.get("model_push"),
              "outcome_commit", (r.get("outcome_commit") or "")[:7], "record_push", r.get("record_push"), "pit", r.get("pit"))
# LIVE pairs
lives = [(mid, t, r) for mid, m in report["models"].items() for t, r in m["rows"].items() if r["klass"] == "LIVE"]
print("LIVE pairs:", [(a, b) for a, b, _ in lives])
# push proofs stats
print("proof files:", len(proofs), "earliest:", min(p["created_at"] for p in proofs), "latest:", max(p["created_at"] for p in proofs))
print("HEAD proven?", proof_time(HEAD, proofs))
# -------- Rule 1 second sentence: every record carries every model of its stage INDEX with param hashes
def index_at(commit, name):
    import subprocess
    raw = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:models/{name}"], check=True, capture_output=True).stdout
    return json.loads(raw), sha256_bytes(raw)
problems = []
checked = 0
for p in sorted((ROOT / "registry/records").glob("*/*.json")):
    rec = load_json(p); c = added_commit(p.relative_to(ROOT).as_posix())
    idx, sha = index_at(c, "INDEX.json")
    checked += 1
    if rec["models_index"]["sha256"] != sha: problems.append(f"{p.name}: index sha != INDEX at record commit")
    ids = [e["model_id"] for e in idx["models"]]
    if [m["model_id"] for m in rec["models"]] != ids: problems.append(f"{p.name}: model list != INDEX list")
    for m in rec["models"]:
        e = next(x for x in idx["models"] if x["model_id"] == m["model_id"])
        if m["params_sha256"] != e["sha256"]: problems.append(f"{p.name}/{m['model_id']}: params sha != INDEX")
        # and current file sha unchanged
        if sha256_file(ROOT / "models" / e["file"]) != e["sha256"]: problems.append(f"{p.name}/{m['model_id']}: model file changed since")
for p in sorted((ROOT / "registry/post_break").glob("*/*.json")):
    rec = load_json(p); c = added_commit(p.relative_to(ROOT).as_posix())
    idx, sha = index_at(c, "INDEX_POST_BREAK.json"); checked += 1
    if rec["models_index"]["sha256"] != sha: problems.append(f"{p.name}: index sha mismatch")
    if [m["model_id"] for m in rec["models"]] != [e["model_id"] for e in idx["models"]]: problems.append(f"{p.name}: model list")
    for m in rec["models"]:
        e = next(x for x in idx["models"] if x["model_id"] == m["model_id"])
        if m["params_sha256"] != e["sha256"]: problems.append(f"{p.name}/{m['model_id']}: params sha")
# OOT records (first and delta) — kodlar basılmaz
first_ok = delta_ok = 0; oot_problems = 0
for p in sorted((ROOT / "registry/oot/records").glob("*/*.json")):
    rec = load_json(p); c = added_commit(p.relative_to(ROOT).as_posix()); idx, sha = index_at(c, "INDEX.json"); checked += 1
    ids = [e["model_id"] for e in idx["models"]]
    mine = [m["model_id"] for m in rec["models"]]
    ok = rec["models_index"]["sha256"] == sha
    if rec.get("record_scope") == "ONLY_MISSING_MODELS":
        prev_ids = ids[:19]
        ok = ok and mine == [i for i in ids if i not in prev_ids]
    else:
        ok = ok and mine == ids
    ok = ok and all(m["params_sha256"] == next(x["sha256"] for x in idx["models"] if x["model_id"] == m["model_id"]) for m in rec["models"])
    if ok:
        if rec.get("record_scope"): delta_ok += 1
        else: first_ok += 1
    else:
        oot_problems += 1
for p in sorted((ROOT / "registry/oot/post_d1").glob("*/*.json")):
    rec = load_json(p); c = added_commit(p.relative_to(ROOT).as_posix()); idx, sha = index_at(c, "INDEX_POST_D1.json"); checked += 1
    ok = rec["models_index"]["sha256"] == sha and [m["model_id"] for m in rec["models"]] == [e["model_id"] for e in idx["models"]]
    ok = ok and all(m["params_sha256"] == next(x["sha256"] for x in idx["models"] if x["model_id"] == m["model_id"]) for m in rec["models"])
    if not ok: oot_problems += 1
print(f"rule-1 index coverage: records checked {checked}; live records problems {len(problems)}; oot first ok {first_ok}, delta ok {delta_ok}, oot problems {oot_problems}")
for x in problems: print("  ", x)
json.dump(report, open(Path(__file__).parent / "s2_out.json", "w"), ensure_ascii=False, indent=1, default=str)

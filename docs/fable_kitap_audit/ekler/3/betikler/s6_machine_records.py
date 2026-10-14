"""Adım 6: registry/post_break/ makine kayıtlarını sıfırdan üret ve sınıfları hesapla (borsai import edilmez)."""
from __future__ import annotations
import sys, json, math
from decimal import Decimal, localcontext
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa

params = load_json(ROOT / "models/break_floor_v0.json")
zero = load_json(ROOT / "models/break_floor_v0@ZERO.json")
idx = load_json(ROOT / "models/INDEX_POST_BREAK.json")
idx_sha = sha256_file(ROOT / "models/INDEX_POST_BREAK.json")
manifest = {(r["date"], r["kind"]): r for r in read_csv(ROOT / "data/raw/bist/MANIFEST.csv")}
proofs = load_proofs()
scores_break = load_json(ROOT / "scores/scores_break.json")
retro = {r["ticker"]: r for r in scores_break["retro_info"]}
model_commit = added_commit("models/break_floor_v0.json")
model_push = proof_time(model_commit, proofs)
print("model commit", model_commit[:7], "push", model_push)
HEAD = head()
THB = {"open": "ACILIS FIYATI", "high": "EN YUKSEK FIYAT", "low": "EN DUSUK FIYAT", "close": "KAPANIS FIYATI",
       "volume": "TOPLAM ISLEM ADEDI", "turnover": "TOPLAM ISLEM HACMI", "aof": "A.O.F", "trade_count": "TOPLAM SOZLESME SAYISI",
       "halt": "GECICI DURDURMA", "special_trade_volume": "OZEL ISLEM BILDIRIMI ISLEM ADEDI", "special_trade_turnover": "OZEL ISLEM BILDIRIMI ISLEM HACMI"}
THM = {"reference_price": "REFERANS FIYATI", "upper_limit": "UST LIMIT FIYATI", "lower_limit": "ALT LIMIT FIYATI"}

def head_p(hp, prep, feats):
    if hp["kind"] == "constant":
        return float(hp["value"]), None, False
    z = []
    w = prep["winsor"]["b_turnover"]
    clipped = not (w["p05"] <= feats["b_turnover"] <= w["p95"])
    for col in prep["columns"]:
        x = feats[col]
        if col in prep["winsor"]:
            x = min(max(x, prep["winsor"][col]["p05"]), prep["winsor"][col]["p95"])
        z.append((x - prep["mean"][col]) / prep["std"][col])
    return sigmoid(sum(c * v for c, v in zip(hp["coef"], z)) + hp["intercept"]), z, clipped

def ingest_after(ticker, day, h_min):
    commits = []
    # bulletins dated > day anywhere under data/raw/bist
    import subprocess, os
    e = dict(os.environ); e["GIT_OPTIONAL_LOCKS"] = "0"
    out = subprocess.run(["git", "-C", str(ROOT), "log", "--diff-filter=A", "--format=@%H", "--name-only", "--", "data/raw/bist"],
                         check=True, capture_output=True, text=True, env=e).stdout.splitlines()
    added = {}; c = None
    for line in out:
        if line.startswith("@"): c = line[1:]
        elif line.strip(): added[line.strip()] = c
    for rel, c in added.items():
        name = Path(rel).name
        if name.startswith(("thb", "thm")) and name.endswith("1.zip"):
            d = name[3:11]; d = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            if d > day: commits.append(c)
    rel = f"data/outcomes/{ticker}.csv"
    hist = git("log", "--reverse", "--format=%H", "--", rel).splitlines()
    for c in hist:
        try:
            txt = git("show", f"{c}:{rel}")
        except Exception:
            continue
        import csv, io
        rows = list(csv.DictReader(io.StringIO(txt)))
        if any(int(r["h"]) >= h_min and r["status"] in ("OK", "NA_LIMIT") for r in rows):
            commits.append(c); break
    return earliest(commits)

results = []
maxd = 0.0
for p in sorted((ROOT / "registry/post_break").glob("*/*.json")):
    rec = load_json(p); t = rec["ticker"]
    rows = read_csv(ROOT / "data/outcomes" / f"{t}.csv")
    # streak from outcomes
    Lc = 0; b = None
    for r in rows:
        assert r["status"] in ("OK", "NA_LIMIT"), r["status"]
        if r["ceiling_close"] == "0": b = Lc + 1; break
        Lc += 1
    assert b is not None and 1 <= b <= 9
    d1 = rows[0]["session_date"]; db = rows[b - 1]["session_date"]
    # D_1..D_b bulletins: sha check vs MANIFEST and record
    sessions = []
    for h in range(1, b + 1):
        day = rows[h - 1]["session_date"]
        for kind in ("thb", "thm"):
            sha, hdr, data = read_bulletin(day, kind)
            assert manifest[(day, kind)]["sha256"] == sha, (t, h, kind)
            assert rows[h - 1][f"{kind}_sha256"] == sha
            assert rec["streak"]["sessions"][h - 1][kind]["sha256"] == sha
            if kind == "thb":
                row = data[f"{t}.E"]; assert row["KAPANIS FIYATI"] == rows[h - 1]["close_raw"]
                thb_row = row
            else:
                lim = data[f"{t}.E"]; assert lim["UST LIMIT FIYATI"] == rows[h - 1]["upper_limit_raw"]
                thm_row = lim
        assert rec["streak"]["sessions"][h - 1]["date"] == day
    # break day fields
    _, _, thb = read_bulletin(db, "thb"); _, _, thm = read_bulletin(db, "thm")
    tr, tl = thb[f"{t}.E"], thm[f"{t}.E"]
    fields = {k: tr[v] for k, v in THB.items()} | {k: tl[v] for k, v in THM.items()}
    assert fields == rec["break_day"]["fields_raw"], (t, {k: (fields[k], rec["break_day"]["fields_raw"].get(k)) for k in fields if fields[k] != rec["break_day"]["fields_raw"].get(k)})
    inputs = load_json(ROOT / "registry/inputs" / f"{t}.json")
    shares = Decimal(inputs["fields"]["shares_offered"]["value"]); price = Decimal(inputs["fields"]["ipo_price_tl"]["value"])
    so_pub = inputs["fields"]["shares_offered"]["source_published_at"]
    pit = istanbul_date(so_pub) < d1
    close = Decimal(fields["close"]); lower = Decimal(fields["lower_limit"]); vol = Decimal(fields["volume"]); ref = Decimal(fields["reference_price"]); up = Decimal(fields["upper_limit"])
    b_floor = int(close == lower)
    with localcontext(CTX60):
        ratio = vol / shares; ln = float(ratio.ln()); rl = lower / ref; ru = up / ref
    band_ok = Decimal("0.9") <= rl <= Decimal("0.9020") and Decimal("1.098") <= ru <= Decimal("1.1")
    feats = {"b_floor": float(b_floor), "b_turnover": ln}
    mine = {}
    for h in ("F1", "F2"):
        if h == "F2" and b > 8: mine[h] = None; continue
        pF, z, clipped = head_p(params["horizons"][h]["p_floor"], params["preprocessing"][h], feats)
        mine[h] = pF
    recm = {m["model_id"]: m for m in rec["models"]}
    pr = recm["break_floor_v0"]["output"]
    d1_ = abs(mine["F1"] - pr["F1"]["p_floor"]); d2_ = abs(mine["F2"] - pr["F2"]["p_floor"]) if mine["F2"] is not None else 0.0
    maxd = max(maxd, d1_, d2_)
    zF1 = recm["break_floor_v0@ZERO"]["output"]["F1"]["p_floor"]; zF2 = recm["break_floor_v0@ZERO"]["output"]["F2"]["p_floor"]
    from fractions import Fraction
    assert zF1 == float(Fraction(25, 82)) and zF2 == float(Fraction(11, 78))
    # structural zero
    x = close
    for _ in range(10 - b): x = lower_limit(x)
    with localcontext(CTX60):
        k_b = float((close / price).ln() / (Decimal(1) / Decimal("0.9")).ln())
    sz = rec["structural_zero_D10"]
    assert str(x) == sz["min10"] and (x > price) == sz["impossible"] and sz["r_b"] == 10 - b and abs(k_b - sz["k_b"]) < 1e-12, (t, str(x), sz)
    # record-level checks
    assert rec["streak"]["L"] == Lc and rec["streak"]["b"] == b and rec["break_day"]["b_floor"] == b_floor
    assert rec["features"]["b_turnover_ratio"] == str(ratio) and rec["features"]["b_turnover_ln"] == ln
    assert rec["inputs_ref"]["inputs_pit_ok"] == pit and rec["inputs_ref"]["sha256"] == sha256_file(ROOT / "registry/inputs" / f"{t}.json")
    assert rec["models_index"]["sha256"] == idx_sha
    assert rec["break_day"]["band_ratio"]["rule_ok"] == band_ok
    # file name content-addressed
    assert p.name.split("_")[2][:12] == sha256_bytes(p.read_bytes())[:12]
    # class
    oc = ingest_after(t, db, b + 1)
    prospective = model_commit is not None and model_push is not None and is_ancestor(model_commit, oc or HEAD)
    klass = ("LIVE" if False else "MACHINE_SEQUENCED") if (prospective and pit) else "RETRO"
    sc = retro.get(t)
    ev = sc["class_evidence"] if sc else None
    agree = sc is not None and ev["outcome_ingest_commit"] == oc and ev["model_prospective"] == prospective
    results.append(dict(ticker=t, L=Lc, b=b, D_b=db, b_floor=b_floor, p_F1=mine["F1"], p_F2=mine["F2"], rec_F1=pr["F1"]["p_floor"],
                        rec_F2=pr["F2"]["p_floor"] if pr["F2"] else None, dF1=d1_, dF2=d2_, clipped=clipped, min10=str(x), impossible=x > price,
                        k_b=round(k_b, 4), ingest=oc[:7] if oc else None, prospective=prospective, klass=klass, scores_agree=agree,
                        pit=pit, band_ok=band_ok))
for r in results:
    print(json.dumps(r, ensure_ascii=False))
print("max |Δ p| over 7 records:", maxd)
print("all scores_break class_evidence agree:", all(r["scores_agree"] for r in results), "classes:", [r["klass"] for r in results])
# ancestry sanity
print("model 4d3c9a2 ancestor of f1f9d44?", is_ancestor(model_commit, "f1f9d444132e89f0377b026b76d775a82685c649"), "; of c1eb7ae?", is_ancestor(model_commit, "c1eb7aeb0bbdb7bea937d71f93751fd859671207"))
json.dump(results, open(Path(__file__).parent / "s6_out.json", "w"), indent=1, default=str)

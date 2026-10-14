"""Python ↔ Rust çıktı karşılaştırması (SPEC_APP §1.3 kuralları): ret kodu+alan birebir; sayılar |Δ| ≤ 1e-9
(f1r_raw göreli; koşullu değerler ≤ 1e-12); metin/mantıksal birebir; anahtar kümeleri eşit; uyarılar
(kod, feature/horizon) çok kümesi + sayısal ek alanlar; `message`/`reason` karşılaştırılmaz."""
from __future__ import annotations

import json
import math
import struct
import sys
from collections import defaultdict
from pathlib import Path

OUT = Path(sys.argv[1])
TOL = 1e-9
TOL_COND = 1e-12


def bits(x: float) -> int:
    return struct.unpack("<Q", struct.pack("<d", x))[0]


def isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


class Cmp:
    def __init__(self):
        self.max_abs = defaultdict(float)   # (model, field) -> max |Δ|
        self.bit_rows = defaultdict(int)
        self.rows = defaultdict(int)
        self.fail = []
        self.tol_hits = defaultdict(int)    # (model, field) -> rows with 0 < |Δ| ≤ tol
        self.cur = None
        self.cur_bit = True

    def num(self, a, b, path, model):
        field = (path.split("/")[1] if "/" in path else path) or "?"
        key = (model, field)
        if isinstance(a, str) or isinstance(b, str):  # NaN/Infinity metinleri
            if a != b:
                self.fail.append((self.cur, model, path, a, b))
            return
        d = abs(a - b)
        if bits(float(a)) != bits(float(b)):
            self.cur_bit = False
        self.max_abs[key] = max(self.max_abs[key], d)
        tol = TOL
        if "cond" in path or "conditional" in path:
            tol = TOL_COND
        if field == "f1r_raw" or path.endswith("f1r_raw"):
            tol = TOL * max(1.0, abs(b))
        if d > tol or math.isnan(d):
            self.fail.append((self.cur, model, path, a, b))
        elif d > 0:
            self.tol_hits[key] += 1

    def warnings(self, a, b, path, model):
        def key(w):
            return (w.get("code"), w.get("feature"), w.get("horizon"))
        ka = sorted(key(w) for w in a)
        kb = sorted(key(w) for w in b)
        if ka != kb:
            self.fail.append((self.cur, model, path, ka, kb))
            return
        for wa in a:
            wb = next(w for w in b if key(w) == key(wa))
            for k, v in wa.items():
                if k == "message":
                    continue
                if k not in wb:
                    self.fail.append((self.cur, model, f"{path}/{k}", v, "<missing>"))
                    continue
                self.cmp(v, wb[k], f"{path}/{k}", model)
            for k in wb:
                if k != "message" and k not in wa:
                    self.fail.append((self.cur, model, f"{path}/{k}", "<missing>", wb[k]))

    def cmp(self, a, b, path, model):
        if isinstance(a, dict) and isinstance(b, dict):
            if set(a) != set(b):
                self.fail.append((self.cur, model, path, sorted(set(a) - set(b)), sorted(set(b) - set(a))))
            for k in a:
                if k in b:
                    if k == "warnings":
                        self.warnings(a[k], b[k], f"{path}/{k}", model)
                    elif k in ("reason", "message"):
                        continue
                    else:
                        self.cmp(a[k], b[k], f"{path}/{k}", model)
            return
        if isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                self.fail.append((self.cur, model, path, len(a), len(b)))
                return
            for i, (x, y) in enumerate(zip(a, b)):
                self.cmp(x, y, f"{path}[{i}]", model)
            return
        if a is None or b is None:
            if a is not b:
                self.fail.append((self.cur, model, path, a, b))
            return
        if isnum(a) or isnum(b):
            if isnum(a) and isnum(b):
                self.num(a, b, path, model)
            else:
                self.fail.append((self.cur, model, path, a, b))
            return
        if a != b:
            self.fail.append((self.cur, model, path, a, b))

    def run(self, py: dict, rs: dict, model: str):
        self.cur_bit = True
        self.rows[model] += 1
        ps, rs_s = py["status"], rs["status"]
        if ps == "EXCEPTION":
            ok = rs_s == "ERROR" and rs["refusal"]["code"] == "DOMAIN_ERROR"
            if not ok:
                self.fail.append((self.cur, model, "status", f"EXCEPTION:{py['refusal']['code']}", f"{rs_s}:{rs.get('refusal')}"))
            else:
                self.bit_rows[model] += 1
            return
        if ps != rs_s:
            self.fail.append((self.cur, model, "status", ps, rs_s))
            return
        if py.get("kind") != rs.get("kind"):
            self.fail.append((self.cur, model, "kind", py.get("kind"), rs.get("kind")))
        pr, rr = py.get("refusal"), rs.get("refusal")
        if (pr is None) != (rr is None):
            self.fail.append((self.cur, model, "refusal", pr, rr))
        elif pr is not None:
            if pr.get("code") != rr.get("code") or pr.get("field") != rr.get("field"):
                self.fail.append((self.cur, model, "refusal", (pr.get("code"), pr.get("field")), (rr.get("code"), rr.get("field"))))
        po, ro = py.get("output"), rs.get("output")
        if (po is None) != (ro is None):
            self.fail.append((self.cur, model, "output", po is None, ro is None))
        elif po is not None:
            self.cmp(po, ro, "", model)
        if self.cur_bit:
            self.bit_rows[model] += 1


def load(p):
    return {json.loads(l)["case_id"]: json.loads(l) for l in open(p, encoding="utf-8")}


c = Cmp()
py = load(OUT / "py_out.jsonl")
rs = load(OUT / "rust_out.jsonl")
assert set(py) == set(rs)
for cid in py:
    c.cur = cid
    for m in py[cid]["runs"]:
        c.run(py[cid]["runs"][m], rs[cid]["runs"][m], m)
pyp = load(OUT / "py_post_out.jsonl")
rsp = load(OUT / "rust_post_out.jsonl")
assert set(pyp) == set(rsp)
for cid in pyp:
    c.cur = cid
    c.run(pyp[cid]["post"], rsp[cid]["post"], "post_d1_hazard_v0")

# özet
models = sorted(c.rows, key=lambda m: (m != "post_d1_hazard_v0", m))
lines = ["| model | satır | bit-eşit | maks \\|Δ\\| (alan) | tolerans-içi fark olan satır-alan | uyuşmazlık |", "|---|---|---|---|---|---|"]
tot_fail = defaultdict(int)
for f in c.fail:
    tot_fail[f[1]] += 1
for m in models:
    fields = [(k[1], v) for k, v in c.max_abs.items() if k[0] == m]
    mx = max(fields, key=lambda x: x[1]) if fields else ("—", 0.0)
    hits = sum(v for k, v in c.tol_hits.items() if k[0] == m)
    lines.append(f"| {m} | {c.rows[m]} | {c.bit_rows[m]} | {mx[1]:.3e} ({mx[0]}) | {hits} | {tot_fail[m]} |")
summary = "\n".join(lines)
print(summary)
print(f"\nTOPLAM satır {sum(c.rows.values())}, bit-eşit {sum(c.bit_rows.values())}, uyuşmazlık {len(c.fail)}")
# durum dağılımı
from collections import Counter
st = Counter()
for cid in py:
    for m, r in py[cid]["runs"].items():
        st[(m, r["status"], (r.get("refusal") or {}).get("code"))] += 1
(OUT / "summary.md").write_text(summary + f"\n\nTOPLAM satır {sum(c.rows.values())}, bit-eşit {sum(c.bit_rows.values())}, uyuşmazlık {len(c.fail)}\n", encoding="utf-8")
(OUT / "failures.json").write_text(json.dumps([list(map(str, f)) for f in c.fail[:200]], ensure_ascii=False, indent=1), encoding="utf-8")
(OUT / "status_counts.json").write_text(json.dumps([[k[0], k[1], k[2], v] for k, v in sorted(st.items())], ensure_ascii=False, indent=0), encoding="utf-8")
(OUT / "max_abs.json").write_text(json.dumps({f"{k[0]}/{k[1]}": v for k, v in sorted(c.max_abs.items())}, indent=1), encoding="utf-8")
for f in c.fail[:30]:
    print("FAIL", f)

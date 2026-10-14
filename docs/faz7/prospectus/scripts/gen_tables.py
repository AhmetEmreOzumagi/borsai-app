"""REPORT.md için sayısal tablolar (markdown) -> logs/tables.md"""
import collections
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import FIELDS, MEMBERS, T, V, codex_all  # noqa: E402

CX = codex_all()


def main():
    cov = list(csv.DictReader(open(V / "coverage.csv", encoding="utf-8")))
    vlog = [json.loads(x) for x in open(V / "verification_log.jsonl", encoding="utf-8")]
    p1 = [r for r in vlog if r["pass"] == 1]
    L = ["## Alan başına kapsama (önce = Codex OK; sonra = doğrulanmış dolu)", "",
         "| Alan | Codex OK (önce) | Sonra (dolu) | VERIFIED | CORRECTED | FILLED | MISSING | Codex UNVERIFIABLE |",
         "|---|---|---|---|---|---|---|---|"]
    tot = collections.Counter()
    for k in FIELDS:
        c = collections.Counter(r[k] for r in cov)
        before = sum(1 for m in MEMBERS if CX[m["ticker"]]["fields"].get(k, {}).get("status") == "OK")
        unv = sum(1 for r in p1 if r["field"] == k and r["codex_outcome"] == "UNVERIFIABLE")
        after = c["VERIFIED"] + c["CORRECTED"] + c["FILLED"]
        L.append(f"| `{k}` | {before} | {after} | {c['VERIFIED']} | {c['CORRECTED']} | {c['FILLED']} | {c['MISSING']} | {unv} |")
        tot.update(c)
        tot["before"] += before
        tot["unv"] += unv
    L.append(f"| **toplam (945 hücre)** | {tot['before']} | {tot['VERIFIED'] + tot['CORRECTED'] + tot['FILLED']} | "
             f"{tot['VERIFIED']} | {tot['CORRECTED']} | {tot['FILLED']} | {tot['MISSING']} | {tot['unv']} |")
    L += ["", "## Codex doğruluk oranı (Codex'in OK verdiği değerler)", "",
          "| Alan | Codex OK | VERIFIED | CORRECTED | UNVERIFIABLE | doğruluk (VERIFIED/OK) |", "|---|---|---|---|---|---|"]
    g = collections.Counter()
    for k in FIELDS:
        c = collections.Counter(r["codex_outcome"] for r in p1 if r["field"] == k and r["codex_status"] == "OK")
        n = sum(c.values())
        g.update(c)
        L.append(f"| `{k}` | {n} | {c['VERIFIED']} | {c['CORRECTED']} | {c['UNVERIFIABLE']} | "
                 f"{(100 * c['VERIFIED'] / n if n else 0):.1f}% |")
    n = sum(g.values())
    L.append(f"| **toplam** | {n} | {g['VERIFIED']} | {g['CORRECTED']} | {g['UNVERIFIABLE']} | {100 * g['VERIFIED'] / n:.1f}% |")
    # parti bazında
    L += ["", "Parti bazında (VERIFIED / CORRECTED / UNVERIFIABLE):", ""]
    for b in ("B1", "B2", "B3", "B4"):
        ts = {m["ticker"] for m in MEMBERS if CX[m["ticker"]]["_batch"] == b}
        c = collections.Counter(r["codex_outcome"] for r in p1 if r["ticker"] in ts and r["codex_status"] == "OK")
        L.append(f"- {b} ({len(ts)} arz): {c['VERIFIED']} / {c['CORRECTED']} / {c['UNVERIFIABLE']}")
    # değer dağılımları (bilgi amaçlı; ilişki analizi değil)
    L += ["", "## Değer dağılımı (yalnız biçim kontrolü için)", ""]
    for k in FIELDS:
        vals = collections.Counter()
        for m in MEMBERS:
            d = json.loads((V / "candidate_features_faz7" / f"{m['ticker']}.json").read_text())
            v = d["fields"][k]["value"]
            vals[v if k != "sector" else ("dolu" if v else None)] += 1
        L.append(f"- `{k}`: " + ", ".join(f"{json.dumps(a, ensure_ascii=False)}: {b}" for a, b in vals.most_common(12)))
    (T / "logs" / "tables.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()

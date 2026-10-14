"""coverage.csv, verification_log.jsonl ve rapor için sayımlar (report_stats.json)."""
import collections
import csv
import datetime as dt
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from blib import EV, W, codex_all  # noqa: E402

OUT = Path.home() / "Desktop/BorsAi_codex/verified"
REG = OUT / "registry/oot"
CX = codex_all()
V15 = ["ipo_price_tl", "shares_offered", "post_ipo_share_capital", "capital_increase_shares", "existing_share_sale_shares",
       "total_demand_multiple", "total_demand_filter_status", "additional_sale_shares", "ipo_size_tl"]
PB = ["ipo_price_try", "planned_pre_ipo_capital", "planned_post_ipo_capital", "planned_capital_increase_shares",
      "planned_existing_share_sale", "planned_base_offer_shares", "planned_additional_sale_ceiling", "planned_max_offer_shares"]
DATES = ["first_trading_date", "bookbuilding_start", "bookbuilding_end"]
INPUTS = V15 + PB + DATES
CAND = ["investor_count", "investor_count_by_group", "retail_demand_multiple", "domestic_institutional_demand_multiple",
        "foreign_institutional_demand_multiple", "distributed_by_group", "retail_allocation_pct",
        "domestic_institutional_allocation_pct", "foreign_institutional_allocation_pct", "distribution_method", "lead_broker",
        "price_stability_planned", "price_stability_days", "issuer_lockup_days", "shareholder_lockup_days", "sector",
        "participation_index_eligible", "market", "sale_method"]
STATUS = {"CODEX_VERIFIED": "VERIFIED", "CODEX_CORRECTED": "CORRECTED", "FILLED_BY_CLAUDE_VERIFIER": "FILLED",
          "MISSING": "MISSING", "CODEX_UNVERIFIABLE": "UNVERIFIABLE"}


def codex_before(t, name):
    if name == "first_trading_date":
        return True
    if name == "total_demand_filter_status":
        f = CX[t]["fields"].get("total_demand_multiple") or {}
        return f.get("status") in ("OK", "PARTIAL") and f.get("value") not in ("BULUNAMADI", None)
    f = CX[t]["fields"].get(name) or {}
    return f.get("status") in ("OK", "PARTIAL") and f.get("value") not in ("BULUNAMADI", None, "")


def codex_ok(t, name):
    if name == "first_trading_date":
        return True
    if name == "total_demand_filter_status":
        name = "total_demand_multiple"
    f = CX[t]["fields"].get(name) or {}
    return f.get("status") == "OK" and f.get("value") not in ("BULUNAMADI", None, "")


def main():
    rows, logl = [], []
    tickers = sorted(p.stem for p in (REG / "inputs").glob("*.json"))
    before = collections.Counter()
    before_ok = collections.Counter()
    after = collections.Counter()
    stat = collections.defaultdict(collections.Counter)
    for t in tickers:
        doc = json.loads((REG / "inputs" / f"{t}.json").read_text())
        cand = json.loads((REG / "candidate_features" / f"{t}.json").read_text())
        for kind, fields, names in (("input", doc["fields"], INPUTS), ("candidate", cand["fields"], CAND)):
            for n in names:
                f = fields[n]
                st = STATUS.get(f.get("provenance"), f.get("provenance"))
                if st == "CORRECTED" and f.get("correction_kind") == "PRECISION_ONLY":
                    st = "CORRECTED_PRECISION"
                key = n if kind == "input" else "cand:" + n
                stat[key][st] += 1
                if codex_before(t, n):
                    before[key] += 1
                if codex_ok(t, n):
                    before_ok[key] += 1
                if f.get("value") is not None:
                    after[key] += 1
                v = f.get("value")
                rows.append({"ticker": t, "kind": kind, "field": n, "status": st,
                             "value": json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else ("" if v is None else v),
                             "source_id": f.get("source_id") or "", "codex_value": f.get("codex_value", ""),
                             "rule": f.get("carry_rule") or ("CALCULATED_FROM_SOURCE_TOTALS" if f.get("origin") == "CALCULATED_FROM_SOURCE_TOTALS" else ""),
                             "missing_reason": f.get("missing_reason") or ""})
                logl.append({"ticker": t, "kind": kind, "field": n, "verdict": st, "value": v,
                             "codex_value": f.get("codex_value"), "codex_status": f.get("codex_status"),
                             "source_id": f.get("source_id"), "source_published_at": f.get("source_published_at"),
                             "source_sha256": f.get("source_sha256"), "quote": f.get("quote"),
                             "carry_rule": f.get("carry_rule"), "origin": f.get("origin"), "derived": f.get("derived"),
                             "missing_reason": f.get("missing_reason"), "provenance": f.get("provenance")})
    with open(OUT / "coverage.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    # belge düzeyi satırlar
    shac = json.loads((W / "sha_compare.json").read_text())
    for x in shac["listing_vs_universe"]:
        logl.append({"ticker": x["ticker"], "kind": "document", "check": "LISTING_SHA_VS_UNIVERSE_PIN", "kap_id": x["id"],
                     "sha256": x["mine"], "pinned": x["universe"], "verdict": "EQUAL" if x["equal"] else "DIFFERENT"})
    for x in shac["codex_copies"]:
        logl.append({"ticker": x["ticker"], "kind": "document", "check": "CODEX_LOCAL_COPY_SHA", **x})
    with open(OUT / "verification_log.jsonl", "w", encoding="utf-8") as fh:
        for l in logl:
            fh.write(json.dumps(l, ensure_ascii=False) + "\n")
    json.dump({"n": len(tickers), "before": before, "before_ok": before_ok, "after": after,
               "status": {k: dict(v) for k, v in stat.items()}},
              open(W / "report_stats.json", "w"), ensure_ascii=False, indent=1)
    print(len(tickers), len(rows), len(logl))


if __name__ == "__main__":
    main()

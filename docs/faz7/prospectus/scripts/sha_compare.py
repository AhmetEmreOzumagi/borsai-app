"""Codex'in belge kayıtlarını (URL, KAP no, yayın zamanı, sha256) yeniden indirdiğimiz belgelerle karşılaştırır.
Çıktı: logs/sha_compare.json  {ticker: [{codex_doc..., our_files, sha_match, local_copy_match, published_match}]}"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import MEMBERS, T, codex_all  # noqa: E402
from tlib import fetched  # noqa: E402

LOCAL = json.loads((T / "cache" / "codex_local_sha.json").read_text())


def main():
    CX = codex_all()
    out = {}
    agg = {"docs": 0, "fetched": 0, "sha_claim_match": 0, "sha_claim_missing": 0, "sha_claim_mismatch": 0,
           "local_copy_match": 0, "published_match": 0, "published_mismatch": 0}
    for m in MEMBERS:
        t = m["ticker"]
        fn = fetched(t)
        rows = []
        for d in CX[t]["documents"]:
            agg["docs"] += 1
            nid = str(d.get("kap_notice_id") or "")
            if not nid:
                mm = re.search(r"Bildirim/(\d+)", d.get("url", ""))
                nid = mm.group(1) if mm else ""
            rec = fn.get(nid)
            r = {"codex_url": d.get("url"), "kap_notice_id": nid, "codex_type": d.get("type"),
                 "codex_published_at": d.get("published_at"), "codex_sha256": d.get("sha256") or None}
            if not rec:
                r["status"] = "NOT_FETCHED"
                rows.append(r)
                continue
            agg["fetched"] += 1
            ours = [{"source_id": f["source_id"], "sha256": f["sha256"], "raw": f.get("raw_java_wrapped_sha256"),
                     "url": f["url"]} for f in rec["files"]]
            r["our_files"] = ours
            r["our_published_at"] = rec["published_at"]
            allsha = {o["sha256"] for o in ours} | {o["raw"] for o in ours if o["raw"]}
            cs = (d.get("sha256") or "").lower()
            if not cs:
                r["sha_claim"] = "NO_CLAIM"; agg["sha_claim_missing"] += 1
            elif cs in allsha:
                r["sha_claim"] = "MATCH"; agg["sha_claim_match"] += 1
            else:
                r["sha_claim"] = "MISMATCH"; agg["sha_claim_mismatch"] += 1
            loc = sorted({p for o in ours for h in (o["sha256"], o["raw"]) if h for p in LOCAL.get(h, [])})
            r["codex_local_copies_same_sha"] = loc
            if loc:
                agg["local_copy_match"] += 1
            cp = (d.get("published_at") or "")[:19]
            if cp and rec["published_at"] and cp == rec["published_at"][:19]:
                r["published"] = "MATCH"; agg["published_match"] += 1
            else:
                r["published"] = "MISMATCH"; agg["published_mismatch"] += 1
            rows.append(r)
        out[t] = rows
    (T / "logs" / "sha_compare.json").write_text(json.dumps({"summary": agg, "tickers": out}, ensure_ascii=False, indent=1))
    print(agg)


if __name__ == "__main__":
    main()

"""Yeniden indirilen belgelerin sha256'sını (a) evren listesindeki BIST bildirimi pinleriyle, (b) Codex'in yerel kopyalarıyla karşılaştırır."""
import glob
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from blib import CODEX, EV, W, tick, sha_file  # noqa: E402

out = {"listing_vs_universe": [], "codex_copies": []}
for f in sorted(glob.glob(str(W / "tick/*.json"))):
    d = json.load(open(f))
    t = d["ticker"]
    L = [x for x in d["docs"] if x["role"] == "LISTING"][0]
    out["listing_vs_universe"].append({"ticker": t, "id": L["id"], "mine": L["pdf_sha256"], "universe": EV[t]["kap_pdf_sha256"],
                                       "equal": L["pdf_sha256"] == EV[t]["kap_pdf_sha256"]})
    mine = {}
    for doc in d["docs"]:
        mine[(doc["id"], 0)] = doc["pdf_sha256"]
        for a in doc["attachments"]:
            mine[(doc["id"], a["n"])] = (a["sha256"], a["raw_sha256"])
    for p in glob.glob(str(CODEX / f"sources/*/{t}_*_*_*.pdf")) + glob.glob(str(CODEX / f"sources/*/{t}_*_*.pdf")):
        m = re.search(rf"{t}_(?:result|tssd|listing)_(\d+)(?:_(\d+))?\.pdf$", p)
        if not m:
            continue
        idx, n = m.group(1), int(m.group(2) or 0)
        cs = sha_file(p)
        mv = mine.get((idx, n))
        rec = {"ticker": t, "codex_file": str(Path(p).relative_to(CODEX)), "kap_id": idx, "ek": n, "codex_sha256": cs}
        if mv is None:
            rec["verdict"] = "BENDE_YOK (bu belge doğrulama penceresinde seçilmedi)"
        else:
            un, raw = mv if isinstance(mv, tuple) else (mv, None)
            rec["mine_sha256"] = un
            rec["verdict"] = "ESIT" if cs in (un, raw) else "FARKLI"
        out["codex_copies"].append(rec)
Path(W / "sha_compare.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
lu = out["listing_vs_universe"]
cc = out["codex_copies"]
print("listeleme", len(lu), "eşit", sum(x["equal"] for x in lu))
from collections import Counter
print("codex kopyaları", len(cc), Counter(x["verdict"] for x in cc))

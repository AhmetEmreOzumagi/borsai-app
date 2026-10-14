"""SPK bültenlerinden numara/tarih ve A.1 'İlk Halka Arzlar' bölümü (ilk 10 sayfa, metin katmanı)."""
import glob
import json
import re
import sys
from pathlib import Path

import pdfplumber

W = Path(__file__).resolve().parent
out_p = W / "spk_a1.json"
res = json.loads(out_p.read_text()) if out_p.exists() else {}
for f in sorted(glob.glob(str(W / "cache/spk2/*/*.pdf"))):
    if f in res:
        continue
    meta = json.loads(Path(f + ".meta.json").read_text())
    try:
        with pdfplumber.open(f) as pp:
            texts = [(pg.extract_text(x_tolerance=1.5, y_tolerance=3) or "") for pg in pp.pages[:10]]
    except Exception as e:
        res[f] = {"error": str(e), "url": meta["url"]}
        continue
    full = "\n".join(texts)
    m = re.search(r"(20\d\d)\s*/\s*(\d{1,3})\s+(\d{1,2})[./](\d{1,2})[./](20\d\d)", full[:600])
    no = date = None
    if m:
        no = f"{m.group(1)}/{int(m.group(2))}"
        date = f"{m.group(5)}-{int(m.group(4)):02d}-{int(m.group(3)):02d}"
    i = full.find("İlk Halka Arz")
    sec = None
    if i >= 0:
        j = re.search(r"\n\s*2\.\s*(Halka Açık|Borçlanma|Payları|Diğer|Kayıtlı|Sermaye Art|Ortaklık)", full[i:])
        sec = full[i: i + (j.start() if j else 6000)]
    res[f] = {"url": meta["url"], "sha256": meta["sha256"], "no": no, "date": date, "a1": sec,
              "head": full[:300], "accessed_utc": meta["accessed_utc"], "last_modified": meta.get("last_modified")}
out_p.write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(len(res), sum(1 for v in res.values() if v.get("a1")), sum(1 for v in res.values() if not v.get("no")))

"""Ticker başına kuyruk tamamlanması ve metin durumu. --json ile tamamlanan listesi."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch2 import queue  # noqa: E402
from tlib import FN, TEXT, docs  # noqa: E402
from common import MEMBERS  # noqa: E402

q = queue()
need = {}
for t, it in q:
    need.setdefault(t, set()).add(str(it["id"]))
ready, rows = [], []
for m in MEMBERS:
    t = m["ticker"]
    have = {p.stem for p in (FN / t).glob("*.json")} if (FN / t).exists() else set()
    ds = docs(t)
    tx = sum(1 for d in ds if (TEXT / f"{d[3]['sha256']}.json").exists())
    pdfs = sum(1 for d in ds if str(d[1]).endswith(".pdf"))
    done = need.get(t, set()) <= have and tx >= pdfs
    rows.append(f"{t}:{len(have & need.get(t, set()))}/{len(need.get(t, set()))}{'*' if done else ''}")
    if done:
        ready.append(t)
if "--json" in sys.argv:
    print(json.dumps(ready))
else:
    print(" ".join(rows))
    print("hazır:", len(ready))

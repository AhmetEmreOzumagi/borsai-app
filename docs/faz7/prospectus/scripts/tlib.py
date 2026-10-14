"""Metin erişimi: ticker belgeleri, sayfa metinleri, arama."""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import T, V, N  # noqa: E402

TEXT = T / "cache" / "text"
FET = T / "cache" / "fetched"


FN = T / "cache" / "fnotice"


def fetched(t):
    out = {}
    for p in sorted((FN / t).glob("*.json")) if (FN / t).exists() else []:
        r = json.loads(p.read_text())
        out[r["id"]] = r
    return out


def docs(t):
    """[(source_id, file_path, notice_rec, file_rec)] PDF'ler."""
    out = []
    for nid, rec in fetched(t).items():
        for f in rec["files"]:
            out.append((f["source_id"], V / "source_docs" / t / f["file"], rec, f))
    return out


def pages_of(sha):
    p = TEXT / f"{sha}.json"
    return json.loads(p.read_text())["pages"] if p.exists() else None


def doc_pages(t, sid):
    for s, path, rec, f in docs(t):
        if s == sid:
            return pages_of(f["sha256"])
    return None


def norm(s):
    s = s.replace("­", "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return N(s)


def search(t, rx, ctx=250, flags=re.I, roles=None):
    r = re.compile(rx, flags)
    out = []
    for sid, path, rec, f in docs(t):
        if roles and rec["role"] not in roles:
            continue
        ps = pages_of(f["sha256"])
        if not ps:
            continue
        for p in ps:
            txt = N(p["text"])
            for m in r.finditer(txt):
                out.append((sid, p["n"], p["method"], txt[max(0, m.start() - ctx): m.end() + ctx]))
    return out


if __name__ == "__main__":
    t, rx = sys.argv[1], sys.argv[2]
    ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 250
    for sid, n, meth, s in search(t, rx, ctx):
        print(f"--- {sid} s.{n} [{meth}]\n{s}\n")


def match_page(page, quote):
    """Alıntının sayfadaki yeri: ana metin ya da (bozuk metin katmanı OCR'la değiştirilmişse) eski metin katmanı.
    Döner: eşleşen metnin yöntemi ("OCR"/"TEXT") ya da None."""
    q = norm(quote or "")
    if q and q in norm(page.get("text", "")):
        return page["method"]
    if q and page.get("alt_text") and q in norm(page["alt_text"]):
        return page.get("alt_method", "TEXT")
    return None

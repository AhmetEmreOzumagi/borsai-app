"""Seçili KAP bildirimlerini resmi URL'den indirir, pinler (sha256), source_docs/<T>/ altına yazar.

Girdi: cache/selected.json  {ticker: [{"id": "...", "role": "IZAHNAME|TSSD|...", "why": "..."}]}
Çıktı: source_docs/<T>/KAP_<id>_ek<n>.<ext> (+ eki yoksa KAP_<id>_bildirim.pdf), cache/fetched/<T>.json
Kullanım: python3 fetch.py [TICKER ...]
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import kaplib  # noqa: E402
from common import T, V  # noqa: E402

SEL = T / "cache" / "selected.json"
FET = T / "cache" / "fetched"
FET.mkdir(parents=True, exist_ok=True)


def ext_of(b: bytes) -> str:
    if b[:4] == b"%PDF":
        return "pdf"
    if b[:2] == b"PK":
        return "zip"
    if b[:4] == b"Rar!":
        return "rar"
    if b[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "doc"
    return "bin"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fetch_ticker(t, items):
    outp = FET / f"{t}.json"
    done = json.loads(outp.read_text()) if outp.exists() else {}
    d = V / "source_docs" / t
    d.mkdir(parents=True, exist_ok=True)
    for it in items:
        nid = str(it["id"])
        if nid in done and all(a.get("file") for a in done[nid]["files"]):
            done[nid]["role"] = it["role"]
            continue
        info = kaplib.kap_page_info(nid)
        rec = {"id": nid, "role": it["role"], "why": it.get("why"), "published_at": info["published_at"],
               "published_at_basis": "KAP_PAGE", "summary": info["summary"], "related": info["related"],
               "page_url": f"https://www.kap.org.tr/tr/Bildirim/{nid}", "page_accessed_utc": info["page_accessed_utc"],
               "files": []}
        for n, (fid, name) in enumerate(info["attachments"], 1):
            body, raw, meta = kaplib.kap_attachment(fid)
            e = ext_of(body)
            fn = f"KAP_{nid}_ek{n}.{e}"
            (d / fn).write_bytes(body)
            rec["files"].append({"source_id": f"KAP_{nid}_EK{n}", "file": fn, "sha256": sha(body), "bytes": len(body),
                                 "url": f"https://www.kap.org.tr/tr/api/file/download/{fid}", "attachment_name": name,
                                 "raw_java_wrapped_sha256": sha(raw) if raw != body else None,
                                 "accessed_at_utc": meta["accessed_utc"], "kind": "KAP_ATTACHMENT"})
        if not info["attachments"] or it.get("want_bildirim"):
            body, meta = kaplib.kap_pdf(nid)
            fn = f"KAP_{nid}_bildirim.pdf"
            (d / fn).write_bytes(body)
            rec["files"].append({"source_id": f"KAP_{nid}", "file": fn, "sha256": sha(body), "bytes": len(body),
                                 "url": f"https://www.kap.org.tr/tr/api/BildirimPdf/{nid}", "attachment_name": None,
                                 "raw_java_wrapped_sha256": None, "accessed_at_utc": meta["accessed_utc"],
                                 "kind": "KAP_NOTIFICATION_PDF"})
        done[nid] = rec
        outp.write_text(json.dumps(done, ensure_ascii=False, indent=1))
        print(t, nid, it["role"], rec["published_at"], len(rec["files"]), flush=True)


def main():
    sel = json.loads(SEL.read_text())
    ts = sys.argv[1:] or list(sel)
    for t in ts:
        fetch_ticker(t, sel[t])


if __name__ == "__main__":
    main()

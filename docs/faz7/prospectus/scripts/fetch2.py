"""Sıralı indirme kuyruğu (bildirim başına kayıt: cache/fnotice/<T>/<id>.json). İşçi k/n: python3 fetch2.py k n"""
import datetime as dt
import re
import hashlib
import json
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import kaplib  # noqa: E402
from common import MEMBERS, T, V, window  # noqa: E402
from fetch import ext_of, sha  # noqa: E402
from match import day  # noqa: E402

FN = T / "cache" / "fnotice"
SKIPATT = re.compile(r"denetim|fiyat tespit|de[gğ]erleme|hukuk[cç]u|finansal tablo|sorumluluk beyan|esas s[oö]zle[sş]me|"
                     r"i[cç] y[oö]nerge|fon kullan|mali tablo|bilan[cç]o|ekspertiz", re.I)


def queue():
    sel = json.loads((T / "cache" / "selected.json").read_text())
    cls = json.loads((T / "cache" / "classified.json").read_text())
    q1, q2, q3 = [], [], []
    for m in MEMBERS:
        t = m["ticker"]
        have = set()
        for it in sel[t]:
            q1.append((t, it)); have.add(it["id"])
        s, e = window(t)
        s = s - dt.timedelta(days=7)
        for h in cls[t]:
            if h["role"] not in ("TSSD", "BIST_BIRINCIL", "IZAHNAME", "IZAHNAME_DEGISIKLIK") or h["id"] in have:
                continue
            if not (s <= day(h) <= e):
                continue
            it = {"id": h["id"], "role": h["role"], "why": "kap_subject_discovery",
                  "want_bildirim": h["role"] in ("TSSD", "BIST_BIRINCIL")}
            (q2 if h["role"] != "IZAHNAME" else q3).append((t, it))
            have.add(h["id"])
    order = {m["ticker"]: i for i, m in enumerate(MEMBERS)}
    pri = {"TSSD": 0, "BIST_BIRINCIL": 1}
    allq = q1 + q2 + q3
    allq.sort(key=lambda x: (order[x[0]], pri.get(x[1]["role"], 2), int(x[1]["id"])))
    return allq


def fetch_one(t, it):
    nid = str(it["id"])
    p = FN / t / f"{nid}.json"
    if p.exists():
        return None
    d = V / "source_docs" / t
    d.mkdir(parents=True, exist_ok=True)
    info = kaplib.kap_page_info(nid)
    rec = {"id": nid, "role": it["role"], "why": it.get("why"), "published_at": info["published_at"],
           "published_at_basis": "KAP_PAGE", "summary": info["summary"], "related": info["related"],
           "page_url": f"https://www.kap.org.tr/tr/Bildirim/{nid}", "page_accessed_utc": info["page_accessed_utc"],
           "files": []}
    rec["skipped_attachments"] = []
    for n, (fid, name) in enumerate(info["attachments"], 1):
        if SKIPATT.search(name or "") and not str(it.get("why", "")).startswith("codex"):
            rec["skipped_attachments"].append({"n": n, "name": name,
                                               "url": f"https://www.kap.org.tr/tr/api/file/download/{fid}",
                                               "reason": "ek adı: denetim/değerleme/hukukçu/esas sözleşme vb. (görev kaynağı değil)"})
            continue
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
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    return rec


def main():
    k, n = int(sys.argv[1]), int(sys.argv[2])
    q = queue()
    print("kuyruk", len(q), flush=True)
    for t, it in q:
        if int(it["id"]) % n != k:
            continue
        try:
            rec = fetch_one(t, it)
        except Exception as e:  # noqa: BLE001
            print("HATA", t, it["id"], e, flush=True)
            continue
        if rec:
            print(t, rec["id"], rec["role"], rec["published_at"], len(rec["files"]), flush=True)


if __name__ == "__main__":
    main()

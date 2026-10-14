"""Ticker başına listeleme öncesi belge adaylarını seçer, indirir (PDF + sayfa + ekler), manifest yazar.

W/tick/<T>.json. Yalnız penceresi tamamen sorgulanmış tickerlar işlenir.
"""
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import kaplib  # noqa: E402
from fetch_days import FTD, LEAD_DAYS, bb_start, members  # noqa: E402

W = Path(__file__).parent
TICK = W / "tick"
TICK.mkdir(exist_ok=True)
CODEX = Path.home() / "Desktop/BorsAi_codex"

codex = {}
for b in ("B1", "B2", "B3", "B4"):
    d = json.load(open(CODEX / f"BORSAI_FAZ6_CODEX_INPUTS_{b}_20260924.json"))
    for ipo in d["ipos"]:
        codex[ipo["ticker"]] = ipo

done_days = set()
sp = kaplib.CACHE / "days_stats.jsonl"
if sp.exists():
    for l in sp.read_text().splitlines():
        if l.strip():
            x = json.loads(l)
            a = dt.date.fromisoformat(x["day"]); b = dt.date.fromisoformat(x.get("to", x["day"]))
            while a <= b:
                done_days.add(a.isoformat()); a += dt.timedelta(days=1)


def role_of(r):
    s = (r.get("subject") or "")
    sm = (r.get("summary") or "").lower()
    if s.startswith("Tasarruf Sahiplerine Satış Duyurusu"):
        return "TSSD"
    if s.startswith("Payların İşlem Görmeye Başlaması"):
        return "LISTING"
    if s.startswith("Payların Borsa Birincil Piyasada Halka Arzı"):
        return "BIST_PRIMARY"
    if s.startswith("Halka Arz İşlemlerinde Sermaye Piyasası Aracının % 5"):
        return "PCT5"
    if s.startswith("İzahname") or s.startswith("Fiyat Tespit") or s.startswith("Halka Arz Fiyatının") or s.startswith("Esas Sözleşme"):
        return "PROSPECTUS_OTHER"
    if "Özel Durum" in s or "Sonuç" in s or "sonu" in sm or "talep" in sm:
        if re.search(r"sonu[çc]|talep|dağıtım|dagitim|satış|satis|tahsis", sm + " " + s.lower()):
            return "RESULT"
        return "ODA_OTHER"
    return "OTHER"


def rows_for(t):
    ftd = FTD[t]
    start = bb_start(next(r for r in members if r["ticker"] == t)) - dt.timedelta(days=LEAD_DAYS)
    out = []
    d = start
    while d < ftd:
        p = kaplib.CACHE / "days" / f"{d.isoformat()}.json"
        if p.exists():
            for r in json.loads(p.read_text()):
                toks = {x.strip() for x in (r.get("relatedStocks") or "").split(",")}
                if t in toks:
                    out.append(r)
        d += dt.timedelta(days=1)
    return out


def window_done(t):
    start = bb_start(next(r for r in members if r["ticker"] == t)) - dt.timedelta(days=LEAD_DAYS)
    d = start
    while d < FTD[t]:
        if d.isoformat() not in done_days:
            return False
        d += dt.timedelta(days=1)
    return True


def fetch_doc(idx, role, row=None, want_atts=True):
    pdf, meta = kaplib.kap_pdf(idx)
    if row is not None and (not want_atts or not row.get("attachmentCount")):
        info = {"published_at": kaplib.kap_time(row["publishDate"]), "summary": row.get("summary"), "kap_title": row.get("kapTitle"),
                "related": row.get("relatedStocks"), "subject": row.get("subject"), "attachments": [], "page_accessed_utc": None,
                "published_at_basis": "KAP_LIST_API"}
    else:
        info = kaplib.kap_page_info(idx)
        info["published_at_basis"] = "KAP_PAGE"
    doc = {"id": str(idx), "role": role, "published_at": info["published_at"], "published_at_basis": info["published_at_basis"],
           "list_publish": kaplib.kap_time(row["publishDate"]) if row else None,
           "kap_title": info["kap_title"] or (row or {}).get("kapTitle"), "subject": info["subject"] or (row or {}).get("subject"),
           "summary": info["summary"] or (row or {}).get("summary"), "related": info["related"],
           "pdf": str(kaplib.CACHE / f"kap/{idx}_bildirim.pdf"), "pdf_sha256": meta["sha256"],
           "pdf_accessed_utc": meta["accessed_utc"], "page_accessed_utc": info["page_accessed_utc"], "attachments": []}
    if want_atts:
        for k, (fid, name) in enumerate(info["attachments"], 1):
            un, raw, am = kaplib.kap_attachment(fid)
            ext = ".pdf" if un[:4] == b"%PDF" else ".bin"
            p = kaplib.CACHE / f"kap_att/{fid}{ext}"
            if ext == ".pdf" and not p.exists():
                p.write_bytes(un)
            doc["attachments"].append({"n": k, "fid": fid, "name": name, "path": str(p) if ext == ".pdf" else None,
                                       "sha256": kaplib.sha256(un), "raw_sha256": am["sha256"], "is_pdf": ext == ".pdf",
                                       "accessed_utc": am["accessed_utc"],
                                       "url": f"https://www.kap.org.tr/tr/api/file/download/{fid}"})
    return doc


def main(only=None):
    ev = {r["ticker"]: r for r in members}
    for t in sorted(FTD, key=lambda x: (FTD[x], x)):
        if only and t not in only:
            continue
        outp = TICK / f"{t}.json"
        if outp.exists():
            continue
        if not window_done(t):
            continue
        rows = rows_for(t)
        docs = []
        seen = set()
        lid = ev[t]["kap_notice_id"]
        lrow = next((r for r in rows if str(r["disclosureIndex"]) == str(lid)), None)
        docs.append(fetch_doc(lid, "LISTING", lrow, want_atts=False))
        seen.add(lid)
        for r in sorted(rows, key=lambda r: kaplib.kap_time(r["publishDate"])):
            idx = str(r["disclosureIndex"])
            if idx in seen:
                continue
            role = role_of(r)
            if role == "RESULT" and "BORSA İSTANBUL" in (r.get("kapTitle") or ""):
                role = "BIST_NOTICE"
            if role in ("RESULT", "TSSD", "LISTING"):
                seen.add(idx)
                docs.append(fetch_doc(idx, role, r, want_atts=role in ("RESULT", "TSSD")))
        # Codex'in andığı KAP kimlikleri (sonuç/TSSD) listede yoksa ekle
        cx = codex.get(t, {})
        for dd in cx.get("documents", []):
            idx = dd.get("kap_notice_id")
            if idx and idx not in seen and dd["type"] in ("KAP_SONUC", "TSSD", "KAP_BIST_LISTELEME"):
                seen.add(idx)
                docs.append(fetch_doc(idx, {"KAP_SONUC": "RESULT", "TSSD": "TSSD", "KAP_BIST_LISTELEME": "LISTING"}[dd["type"]] + "_CODEX", None,
                                      want_atts=dd["type"] != "KAP_BIST_LISTELEME"))
        other = [{"id": str(r["disclosureIndex"]), "publish": kaplib.kap_time(r["publishDate"]), "subject": r["subject"],
                  "summary": r["summary"], "kap_title": r["kapTitle"], "att": r["attachmentCount"]}
                 for r in rows if str(r["disclosureIndex"]) not in seen]
        outp.write_text(json.dumps({"ticker": t, "first_trading_date": FTD[t].isoformat(), "docs": docs,
                                    "other_rows": other}, ensure_ascii=False, indent=1))
        print(t, len(docs), [d["role"] for d in docs], flush=True)


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)

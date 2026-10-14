"""Konu filtreli ve gün taramalı KAP satırlarını tickerlara eşler (yalnız listeleme öncesi pencere)."""
import datetime as dt
import glob
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import EV, FTD, MEMBERS, T, bb_start  # noqa: E402

STOP = {"a.ş.", "a.s.", "anonim", "şirketi", "sanayi", "ve", "ticaret", "san.", "tic.", "yatırım", "enerji", "gıda",
        "holding", "teknoloji", "teknolojileri", "gayrimenkul", "ortaklığı", "ürünleri", "hizmetleri", "i̇nşaat",
        "inşaat", "elektrik", "üretim", "ltd.", "şti."}


def fold(s):
    s = (s or "").replace("İ", "i").replace("I", "ı").lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).replace("ı", "i")


def name_keys(t):
    words = [w for w in re.split(r"[\s,]+", EV[t]["company"]) if w]
    ks = [fold(w) for w in words if fold(w) not in {fold(x) for x in STOP} and len(w) > 2]
    return ks[:2]


def rows():
    out = {}
    for f in glob.glob(str(T / "cache/subj/*.json")) + glob.glob(str(T / "cache/days/*.json")):
        for r in json.load(open(f)):
            out[r["disclosureIndex"]] = r
    return list(out.values())


def day(r):
    dd, mm, yy = r["publishDate"].split(" ")[0].split(".")
    return dt.date(int(yy), int(mm), int(dd))


def wide_window(t):
    r = EV[t]
    s = bb_start(r) - dt.timedelta(days=45)
    if r["approval_date_spk"]:
        s = min(s, dt.date.fromisoformat(r["approval_date_spk"]) - dt.timedelta(days=10))
    return s, FTD[t] - dt.timedelta(days=1)


def match_all():
    R = rows()
    res = {}
    for m in MEMBERS:
        t = m["ticker"]
        s, e = wide_window(t)
        ks = name_keys(t)
        hits = []
        for r in R:
            d = day(r)
            if not (s <= d <= e):
                continue
            toks = {x.strip() for x in (r.get("relatedStocks") or "").replace(";", ",").split(",") if x.strip()}
            text = fold(f"{r.get('summary') or ''} {r.get('kapTitle') or ''}")
            by = None
            if t in toks:
                by = "ticker"
            elif ks and all(k in text for k in ks):
                by = "name"
            if by:
                hits.append({"id": str(r["disclosureIndex"]), "publishDate": r["publishDate"], "subject": r["subject"],
                             "summary": r.get("summary"), "related": r.get("relatedStocks"), "kapTitle": r.get("kapTitle"),
                             "by": by, "attachmentCount": r.get("attachmentCount")})
        res[t] = sorted(hits, key=lambda h: int(h["id"]))
    return res


if __name__ == "__main__":
    res = match_all()
    (T / "cache" / "matched.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(sum(len(v) for v in res.values()), [t for t, v in res.items() if not v])

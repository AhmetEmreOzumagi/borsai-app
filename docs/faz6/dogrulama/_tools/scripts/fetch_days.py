"""Kohort üyelerinin listeleme öncesi pencerelerindeki KAP günlerini sorgular.

Yanıt bellekte süzülür: yalnız (a) ilgili kohort kodlarının HEPSİ o gün listeleme öncesiyse, ya da
(b) hiç ilgili kod yoksa ve metin 'halka arz' içeriyorsa ve riskli kelime yoksa satır tutulur.
Listeleme sonrası kohort satırları diske yazılmaz, ekrana basılmaz; yalnız sayısı tutulur.
"""
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import kaplib  # noqa: E402

REPO = Path("/Users/ahmet/Desktop/BorsAi")
OUT = kaplib.CACHE / "days"
OUT.mkdir(exist_ok=True)
RISKY = ("istikrar", "devre kesici", "tedbir", "işlem sırası", "brüt takas", "kredili", "açığa satış",
         "fiyat hareket", "volatilite", "tavan", "taban", "getiri", "performans")

members = [r for r in csv.DictReader(open(REPO / "docs/specs_faz6/ekler/evren_listesi.csv", encoding="utf-8"))
           if r["status"] == "MEMBER"]
FTD = {r["ticker"]: dt.date.fromisoformat(r["first_trading_date"]) for r in members}


def bb_start(r):
    b = r["bookbuilding_kap"].replace(".", "/")
    ftd = FTD[r["ticker"]]
    y = int(b[-4:])
    if re.fullmatch(r"[\d-]+/\d{2}/\d{4}", b):
        return dt.date(y, int(b.split("/")[1]), int(b.split("/")[0].split("-")[0]))
    d0, mo = b.split("-")[0].split("/")[:2]
    s = dt.date(y, int(mo), int(d0))
    return s if s <= ftd else dt.date(y - 1, int(mo), int(d0))


LEAD_DAYS = 7


def days_needed():
    days = set()
    for r in members:
        d = bb_start(r) - dt.timedelta(days=LEAD_DAYS)
        while d < FTD[r["ticker"]]:
            days.add(d)
            d += dt.timedelta(days=1)
    return sorted(days)


def filter_rows(rows, day_of):
    kept, n_post, n_mixed = [], 0, 0
    for r in rows:
        d = day_of(r)
        toks = {t.strip() for t in (r.get("relatedStocks") or "").replace(";", ",").split(",") if t.strip()}
        coh = toks & FTD.keys()
        text = f"{r.get('subject') or ''} {r.get('summary') or ''}".lower()
        risky = any(w in text for w in RISKY)
        if coh:
            pre = [d < FTD[t] for t in coh]
            if all(pre):
                kept.append(r)
            elif any(pre):
                n_mixed += 1
                if not risky:
                    kept.append(r)
            else:
                n_post += 1
        elif not toks and "halka arz" in text and not risky:
            kept.append(r)
    return kept, n_post, n_mixed


def row_day(r):
    dd, mm, yy = r["publishDate"].split(" ")[0].split(".")
    return dt.date(int(yy), int(mm), int(dd))


def query_range(d0, d1, stats_p):
    rows, meta = kaplib.kap_day_range(d0.isoformat(), d1.isoformat())
    if len(rows) >= 1990 and d1 > d0:
        mid = d0 + (d1 - d0) // 2
        query_range(d0, mid, stats_p)
        query_range(mid + dt.timedelta(days=1), d1, stats_p)
        return
    kept, n_post, n_mixed = filter_rows(rows, row_day)
    by = {}
    for r in kept:
        by.setdefault(row_day(r).isoformat(), []).append(r)
    d = d0
    while d <= d1:
        (OUT / f"{d.isoformat()}.json").write_text(json.dumps(by.get(d.isoformat(), []), ensure_ascii=False))
        d += dt.timedelta(days=1)
    with open(stats_p, "a") as fh:
        fh.write(json.dumps({"day": d0.isoformat(), "to": d1.isoformat(), "n_all": len(rows), "n_kept": len(kept),
                             "n_post_listing_cohort_dropped": n_post, "n_mixed": n_mixed, **meta}) + "\n")
    if len(rows) >= 1990:
        print("UYARI sınır", d0, d1, len(rows), flush=True)


def main():
    days = days_needed()
    stats_p = kaplib.CACHE / "days_stats.jsonl"
    done = set()
    if stats_p.exists():
        for l in stats_p.read_text().splitlines():
            if not l.strip():
                continue
            x = json.loads(l)
            a = dt.date.fromisoformat(x["day"]); b = dt.date.fromisoformat(x.get("to", x["day"]))
            while a <= b:
                done.add(a); a += dt.timedelta(days=1)
    todo = [d for d in days if d not in done]
    # ardışık günleri en çok 3 günlük parçalara böl
    chunks, cur = [], []
    for d in todo:
        if cur and (d - cur[-1]).days == 1 and len(cur) < 3:
            cur.append(d)
        else:
            if cur:
                chunks.append(cur)
            cur = [d]
    if cur:
        chunks.append(cur)
    print("parça", len(chunks), "gün", len(todo), flush=True)
    for c in chunks:
        query_range(c[0], c[-1], stats_p)
    print("bitti", len(days), flush=True)


if __name__ == "__main__":
    main()

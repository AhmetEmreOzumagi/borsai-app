"""Kohort üyelerinin listeleme öncesi pencerelerindeki KAP günlerini sorgular (byCriteria, 2 günlük parçalar).

Yanıt bellekte süzülür, ekrana basılmaz. Diske yalnız şu satırlar yazılır:
  (a) ilgili kohort kodlarının HEPSİ o gün listeleme öncesi olan satırlar;
  (b) kohort kodu içermeyen ve konu/özetinde izahname / TSSD / halka arz geçen, riskli kelime içermeyen satırlar.
Listeleme sonrası kohort satırları yazılmaz; yalnız sayısı tutulur (logs/days_stats.jsonl).
"""
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import kaplib  # noqa: E402
from common import FTD, MEMBERS, T, window  # noqa: E402

OUT = T / "cache" / "days"
OUT.mkdir(parents=True, exist_ok=True)
STATS = T / "logs" / "days_stats.jsonl"
RISKY = ("istikrar", "devre kesici", "tedbir", "işlem sırası", "brüt takas", "kredili", "açığa satış",
         "fiyat hareket", "volatilite", "tavan", "taban", "getiri", "performans")
KEYS = ("izahname", "tasarruf sahip", "satış duyuru", "halka arz")
SUBJ = ("İzahname", "Tasarruf Sahiplerine")


def row_day(r):
    dd, mm, yy = r["publishDate"].split(" ")[0].split(".")
    return dt.date(int(yy), int(mm), int(dd))


def keep(r):
    d = row_day(r)
    toks = {t.strip() for t in (r.get("relatedStocks") or "").replace(";", ",").split(",") if t.strip()}
    coh = toks & FTD.keys()
    text = f"{r.get('subject') or ''} {r.get('summary') or ''}".lower()
    risky = any(w in text for w in RISKY)
    if coh:
        pre = [d < FTD[t] for t in coh]
        if all(pre):
            return "K"
        if any(pre):
            return "M" if not risky else "P"
        return "P"
    subj_ok = any(s in (r.get("subject") or "") for s in SUBJ)
    if (subj_ok or any(k in text for k in KEYS)) and (subj_ok or not risky):
        return "K"
    return "D"


def days_needed():
    days = set()
    for r in MEMBERS:
        s, e = window(r["ticker"])
        d = s
        while d <= e:
            days.add(d)
            d += dt.timedelta(days=1)
    return sorted(days)


def chunks(days, n=2):
    out, cur = [], []
    for d in days:
        if cur and (d - cur[-1]).days == 1 and len(cur) < n:
            cur.append(d)
        else:
            if cur:
                out.append(cur)
            cur = [d]
    if cur:
        out.append(cur)
    return out


def main():
    days = days_needed()
    ch = chunks(days)
    print(f"gün={len(days)} parça={len(ch)}", flush=True)
    for i, c in enumerate(ch):
        d0, d1 = c[0].isoformat(), c[-1].isoformat()
        p = OUT / f"{d0}_{d1}.json"
        if p.exists():
            continue
        rows, meta = kaplib.kap_day_range(d0, d1)
        if len(rows) >= 1900 and len(c) > 1:
            print("UYARI çok satır", d0, d1, len(rows), flush=True)
        kept, cnt = [], {"K": 0, "M": 0, "P": 0, "D": 0}
        for r in rows:
            k = keep(r)
            cnt[k] += 1
            if k in ("K", "M"):
                kept.append(r)
        p.write_text(json.dumps(kept, ensure_ascii=False))
        with open(STATS, "a") as fh:
            fh.write(json.dumps({"d0": d0, "d1": d1, "n_rows": len(rows), "kept": cnt["K"], "mixed_kept": cnt["M"],
                                 "post_listing_dropped": cnt["P"], "other_dropped": cnt["D"], **meta}) + "\n")
        if i % 20 == 0:
            print(i, d0, d1, len(rows), cnt, flush=True)


if __name__ == "__main__":
    main()

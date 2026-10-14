"""Konu filtreli KAP keşfi: İzahname (SPK Tarafından Onaylanan, alt türleriyle), İzahname değişiklik-ekleme, TSSD,
Payların Borsa Birincil Piyasada Halka Arzı. 2019-11-01..2023-09-21, aylık parçalar.
Süzme discover.keep ile (listeleme sonrası kohort satırları diske yazılmaz, yalnız sayılır)."""
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import kaplib  # noqa: E402
from common import T  # noqa: E402
from discover import keep  # noqa: E402

S = ["4028328d5988e2630159d9b261b72ffe", "8aca490d507059f201507070951401c1", "8aca490d5075d4800150760138b7005d",
     "8aca490d4ff02191014ff0375bd800b1"]
OUT = T / "cache" / "subj"
OUT.mkdir(parents=True, exist_ok=True)
STATS = T / "logs" / "subj_stats.jsonl"

d = dt.date(2019, 11, 1)
end = dt.date(2023, 9, 21)
while d <= end:
    nx = (d.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    e = min(nx - dt.timedelta(days=1), end)
    p = OUT / f"{d}_{e}.json"
    if not p.exists():
        body = json.dumps({"fromDate": d.isoformat(), "toDate": e.isoformat(), "mkkMemberOidList": [],
                           "subjectList": S}).encode()
        raw, h = kaplib.http("https://www.kap.org.tr/tr/api/disclosure/members/byCriteria", data=body,
                             headers={"Content-Type": "application/json",
                                      "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu"})
        rows = json.loads(raw)
        kept, cnt = [], {"K": 0, "M": 0, "P": 0, "D": 0}
        for r in rows:
            k = keep(r)
            cnt[k] += 1
            if k in ("K", "M"):
                kept.append(r)
        p.write_text(json.dumps(kept, ensure_ascii=False))
        with open(STATS, "a") as fh:
            fh.write(json.dumps({"d0": str(d), "d1": str(e), "n_rows": len(rows), **cnt,
                                 "sha256": kaplib.sha256(raw), "accessed_utc": kaplib.now_utc()}) + "\n")
        print(d, e, len(rows), cnt, flush=True)
    d = nx

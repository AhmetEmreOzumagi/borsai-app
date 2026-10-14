"""PB özel durumları: SPK onay tarihi .. (talep toplama başlangıcı − LEAD_DAYS − 1) aralığını 3 günlük parçalarla sorgular;
yalnız hedef ticker'ın (ya da ilgili şirket alanı boş olup özetinde unvanı geçen) listeleme öncesi satırlarını tutar."""
import datetime as dt, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import kaplib
from fetch_days import FTD, LEAD_DAYS, bb_start, members, filter_rows, row_day
EVR = {r['ticker']: r for r in members}
SPKF = json.loads((Path(__file__).parent / 'spk_final.json').read_text())
A1 = json.loads((Path(__file__).parent / 'spk_a1.json').read_text())
def norm(s): return re.sub(r'\s+', ' ', (s or '').replace('İ', 'i').replace('I', 'ı').lower())
out = {}
for t in sys.argv[1:]:
    bdate = A1[SPKF[t]['file']]['date']
    d0 = dt.date.fromisoformat(bdate)
    d1 = bb_start(EVR[t]) - dt.timedelta(days=LEAD_DAYS + 1)
    k = norm(' '.join(EVR[t]['company'].split()[:2]))
    rows = []
    d = d0
    while d <= d1:
        e = min(d + dt.timedelta(days=2), d1)
        allr, meta = kaplib.kap_day_range(d.isoformat(), e.isoformat())
        kept, _, _ = filter_rows(allr, row_day)
        for r in kept:
            toks = {x.strip() for x in (r.get('relatedStocks') or '').split(',')}
            if t in toks or (not (r.get('relatedStocks') or '').strip() and k in norm(r.get('summary'))):
                rows.append(r)
        d = e + dt.timedelta(days=1)
    out[t] = rows
    print(t, bdate, d1, [(r['disclosureIndex'], r['publishDate'], r['subject'][:45], (r['summary'] or '')[:60], r['attachmentCount']) for r in rows], flush=True)
p = Path(__file__).parent / 'widesearch.json'
old = json.loads(p.read_text()) if p.exists() else {}
old.update(out); p.write_text(json.dumps(old, ensure_ascii=False, indent=1))

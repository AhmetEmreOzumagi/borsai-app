"""İlgili şirket alanı boş olup özetinde şirket unvanı geçen listeleme öncesi sonuç/TSSD bildirimlerini tick/<T>.json'a ekler."""
import datetime as dt, json, re, sys, glob
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import kaplib
from collect import fetch_doc, role_of
from fetch_days import FTD, LEAD_DAYS, bb_start, members
EVR = {r['ticker']: r for r in members}

def norm(s):
    return re.sub(r'\s+', ' ', (s or '').replace('İ', 'i').replace('I', 'ı').lower())

def key(company):
    w = [x for x in re.split(r'[\s,]+', company) if x]
    return norm(' '.join(w[:2]))

changed = []
only = set(sys.argv[1:])
for f in sorted(glob.glob('tick/*.json')):
    d = json.load(open(f)); t = d['ticker']
    if only and t not in only: continue
    if d.get('augmented_checked'): continue
    k = key(EVR[t]['company'])
    seen = {x['id'] for x in d['docs']}
    start = bb_start(EVR[t]) - dt.timedelta(days=LEAD_DAYS)
    day = start; add = []
    while day < FTD[t]:
        p = kaplib.CACHE / 'days' / f'{day.isoformat()}.json'
        for r in (json.loads(p.read_text()) if p.exists() else []):
            if (r.get('relatedStocks') or '').strip():
                continue
            if k in norm(r.get('summary')) or k in norm(r.get('kapTitle')):
                role = role_of(r)
                if role in ('RESULT', 'TSSD') and str(r['disclosureIndex']) not in seen:
                    add.append((r, role))
        day += dt.timedelta(days=1)
    for r, role in add:
        doc = fetch_doc(str(r['disclosureIndex']), role + '_UNRELATED', r, want_atts=True)
        doc['note'] = 'KAP satırında ilgili şirket alanı boş; özetteki unvanla eşleşti'
        d['docs'].append(doc); seen.add(doc['id'])
    d['augmented_checked'] = True
    json.dump(d, open(f, 'w'), ensure_ascii=False, indent=1)
    if add:
        changed.append(t); print(t, [(r['disclosureIndex'], role, (r.get('summary') or '')[:70]) for r, role in add], flush=True)
print('eklenen', changed)

"""İzahname parçasını indirip metinde desen arar. Kullanım: izsearch.py T KAPID 'regex' ..."""
import sys, json, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import kaplib
from pdftext import extract
t, idx = sys.argv[1], sys.argv[2]
pats = sys.argv[3:]
info = kaplib.kap_page_info(idx)
for fid, name in info['attachments']:
    un, raw, meta = kaplib.kap_attachment(fid)
    p = kaplib.CACHE / f'kap_att/{fid}.pdf'
    if not p.exists(): p.write_bytes(un)
    doc = extract(p)
    full = re.sub(r'\s+', ' ', ' '.join(x['text'] for x in doc['pages']))
    print('==', t, idx, info['published_at'], name, len(doc['pages']), 'sayfa', 'OCR' if any(x['method']=='OCR' for x in doc['pages']) else 'TEXT', fid)
    for pat in pats:
        for m in list(re.finditer(pat, full, re.I))[:6]:
            print('   [', pat, ']', full[max(0, m.start()-250):m.end()+300])

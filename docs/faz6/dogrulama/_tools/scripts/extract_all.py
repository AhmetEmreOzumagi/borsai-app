import json,glob,sys,time
sys.path.insert(0,'.')
from pdftext import extract
from pathlib import Path
while True:
    n=0
    for f in sorted(glob.glob('tick/*.json')):
        d=json.load(open(f))
        for doc in d['docs']:
            paths=[doc['pdf']]+[a['path'] for a in doc['attachments'] if a.get('path')]
            for p in paths:
                try:
                    extract(Path(p)); n+=1
                except Exception as e:
                    print('HATA',p,e,flush=True)
    done = Path('collect.log').exists() and 'LOOP BITTI' in Path('collect.log').read_text()
    print('tur',n,flush=True)
    if done: print('EXTRACT BITTI',flush=True); break
    time.sleep(60)

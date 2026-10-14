import json,sys,urllib.parse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import kaplib
d=json.load(open(Path(__file__).parent/'spk_index_full.json'))
n=0
for y,lst in d.items():
    for u in lst:
        if 'Ayd' in u: continue
        base=urllib.parse.unquote(u.split('/')[-1]).replace(' ','_')
        oid=u.split('/')[-2]
        try:
            kaplib.cached(f"spk2/{y}/{oid}_{base}", u.replace(' ','%20'))
            n+=1
        except Exception as ex:
            print('HATA',y,u,ex,flush=True)
print('bitti',n,flush=True)

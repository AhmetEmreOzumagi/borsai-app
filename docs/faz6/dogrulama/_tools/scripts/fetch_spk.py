import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import kaplib
d=json.load(open('/Users/ahmet/Desktop/BorsAi/docs/specs_faz6/ekler/spk_bulten_dizini_2020_2023.json'))
n=0
for y,lst in d.items():
    for e in lst:
        try:
            kaplib.cached(f"spk/{y}-{e['no']}.pdf", e['url'])
            n+=1
        except Exception as ex:
            print('HATA',y,e,ex,flush=True)
print('bitti',n,flush=True)

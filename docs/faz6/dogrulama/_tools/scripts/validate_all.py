"""Repo doğrulayıcısı: borsai.registry.validate_inputs + inputs_pit_problems (root=verified). Repo salt okunur."""
import json,sys,glob
from pathlib import Path
sys.path.insert(0,'/Users/ahmet/Desktop/BorsAi')
from borsai.registry import validate_inputs, inputs_pit_problems
ROOT=Path.home()/'Desktop/BorsAi_codex/verified'
res={}
files=sorted(glob.glob(str(ROOT/'registry/oot/inputs/*.json')))
for f in files:
    doc=json.load(open(f))
    t=doc['ticker']; ftd=doc['fields']['first_trading_date']['value']
    a=validate_inputs(doc)
    b=inputs_pit_problems(doc, root=ROOT, as_of=f"{ftd}T00:00:00+03:00")
    res[t]={'validate_inputs':a,'inputs_pit_problems':b,'as_of':f"{ftd}T00:00:00+03:00"}
    if a or b: print(t,a,b)
json.dump(res,open('validate_result.json','w'),ensure_ascii=False,indent=1)
print('dosya',len(files),'temiz',sum(1 for v in res.values() if not v['validate_inputs'] and not v['inputs_pit_problems']))

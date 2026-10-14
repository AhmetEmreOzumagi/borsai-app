import json,csv,re
def norm(s):
    s=s.replace('İ','i').replace('I','ı').lower()
    s=s.replace('â','a').replace('î','i').replace('û','u')
    return re.sub(r'\s+',' ',s)
d=json.load(open('spk_a1.json'))
m=[r for r in csv.DictReader(open('/Users/ahmet/Desktop/BorsAi/docs/specs_faz6/ekler/evren_listesi.csv')) if r['status']=='MEMBER']
res={}
for r in m:
    words=[w for w in re.split(r'[\s,]+',r['company']) if w]
    key=norm(' '.join(words[:2]))
    hits=[]
    for f,v in d.items():
        if not v.get('a1'): continue
        if v['date']>=r['first_trading_date']: continue
        if key in norm(v['a1'].replace('\n',' ')):
            hits.append((v['date'],v['no'],f))
    hits.sort()
    res[r['ticker']]={'key':key,'hits':hits,'ftd':r['first_trading_date'],'approval':r['approval_date_spk'],'company':r['company']}
json.dump(res,open('spk_match.json','w'),ensure_ascii=False,indent=1)
nohit=[t for t,v in res.items() if not v['hits']]
multi=[(t,[h[1] for h in v['hits']]) for t,v in res.items() if len(v['hits'])>1]
print('hit',sum(1 for v in res.values() if v['hits']),'nohit',nohit); print('multi',multi)
# approval date check
bad=[(t,v['approval'],v['hits'][-1][0]) for t,v in res.items() if v['hits'] and v['approval'] and v['hits'][-1][0]!=v['approval']]
print('approval!=bulletin date',bad)

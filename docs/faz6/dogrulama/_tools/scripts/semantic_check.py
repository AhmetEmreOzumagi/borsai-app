import json,glob,sys,collections
from decimal import Decimal
from pathlib import Path
sys.path.insert(0,'/Users/ahmet/Desktop/BorsAi')
from borsai.features import compute_features, compute_pb_features, FeatureError, PBRefusal
R=Path.home()/'Desktop/BorsAi_codex/verified/registry/oot/inputs'
res={}; cnt=collections.Counter(); probs=[]
for f in sorted(R.glob('*.json')):
    d=json.load(open(f)); t=d['ticker']; F={k:v.get('value') for k,v in d['fields'].items()}
    r={}
    so=Decimal(F['shares_offered']); 
    if all(F[k] is not None for k in ('capital_increase_shares','existing_share_sale_shares')):
        s=Decimal(F['capital_increase_shares'])+Decimal(F['existing_share_sale_shares'])+Decimal(F['additional_sale_shares'] or 0)
        r['split_sum_ok']= s==so
        if s!=so: probs.append(f"{t}: ayrım toplamı {s} != satılan {so} (ek={F['additional_sale_shares']})")
    pr=F['ipo_price_try']
    if pr and '-' not in pr[1:] and '–' not in pr and Decimal(pr)!=Decimal(F['ipo_price_tl']):
        probs.append(f"{t}: arz fiyatı {F['ipo_price_tl']} != SPK fiyatı {pr}")
    # V1.5
    try:
        compute_features(ipo_price_tl=F['ipo_price_tl'],shares_offered=F['shares_offered'],post_ipo_share_capital=F['post_ipo_share_capital'],
                         capital_increase_shares=F['capital_increase_shares'],total_demand_multiple=F['total_demand_multiple'],ipo_size_tl=F['ipo_size_tl'])
        r['v15_features']='OK'
    except FeatureError as e:
        r['v15_features']=f'ERR {e}'
    except Exception as e:
        r['v15_features']=f'ERR {type(e).__name__} {e}'
    r['f3']=F['total_demand_multiple']; r['f3_filter']=F['total_demand_filter_status']
    # hazard: f1,f2,f3 (fiyat, pay, sermaye, f3)
    r['hazard_inputs']= all(F[k] is not None for k in ('ipo_price_tl','shares_offered','post_ipo_share_capital','total_demand_multiple'))
    r['v15_complete']= r['v15_features']=='OK' and F['total_demand_multiple'] is not None and F['total_demand_filter_status']!='FILTERED'
    try:
        compute_pb_features({k:F[k] for k in ('ipo_price_try','planned_pre_ipo_capital','planned_post_ipo_capital','planned_capital_increase_shares','planned_existing_share_sale','planned_base_offer_shares','planned_additional_sale_ceiling','planned_max_offer_shares')})
        r['pb']='OK'
    except PBRefusal as e:
        r['pb']=f'REFUSE {e.code}:{e.field}'
    res[t]=r
json.dump(res,open('semantic.json','w'),ensure_ascii=False,indent=1)
print('\n'.join(probs))
C=collections.Counter(v['pb'] for v in res.values()); print('PB',C)
print('V15 features',collections.Counter(v['v15_features'][:60] for v in res.values()))
print('f3 var',sum(v['f3'] is not None for v in res.values()),'FILTERED',sum(v['f3_filter']=='FILTERED' for v in res.values()),'v15_complete',sum(v['v15_complete'] for v in res.values()),'hazard',sum(v['hazard_inputs'] for v in res.values()))

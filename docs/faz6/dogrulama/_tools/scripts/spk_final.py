import json,re
from decimal import Decimal
d=json.load(open('spk_rows.json'))
C=["mevcut_sermaye","yeni_sermaye","bedelli","bedelsiz","mevcut_pay_satisi","ek_pay_satisi","satis_fiyati"]
# elle: görüntüden okunmuş (None = hücre boş)
MAN={
 'DNISI':['16.000.000','24.700.000','8.700.000','-','-','-','3.52'],
 'ISKPL':['43.741.000','51.802.638','8.061.638','-','3.224.655','-','16,10'],
 'CANTE':['252.410.000','320.000.000','67.590.000','-','-','6.759.000','3.90'],
 'SELVA':['65.000.000','78.000.000','13.000.000','-','13.000.000','-','3.06'],
 'GESAN':['100.000.000','115.000.000','15.000.000','-','12.000.000','2.000.000','17'],
 'PRDGS':['141.000.000','196.00.000','55.000.000','-','-','11.000.000','2,29'],
 'HKTM':['25.000.000','35.000.000','10.000.000','-','2.000.000',None,'11,00'],
 'EYGYO':['66.000.000','82.500.000','16.500.000','-','8.250.000','-','14.23'],
 'ONCSM':['19.900.000','23.850.000','3.950.000','-','2.000.000','-','17.50'],
 'GRTRK':['100.000.000','125.000.000','25.000.000','-','-',None,'17,60'],
 'KTLEV':['150.000.000','180.000.000','30.000.000',None,'30.000.000',None,'13,43'],
 'A1CAP':['100.000.000','135.000.000','35.000.000','-','-',None,'25,00'],
 'ENERY':['120.000.000','145.000.000','25.000.000','-','14.000.000',None,'88,76'],
 'GENIL':['250.000.000','300.000.000','50.000.000','-','12.500.000','6.250.000','10,75'],
 'BVSAN':['30.000.000','37.600.000','7.600.000','-','3.900.000','-','31,00'],
}
def num(s):
    if s is None or s in ('-','–','—'): return Decimal(0)
    if re.search(r'\d-\d',s) or '–' in s: return None
    if re.fullmatch(r'\d{1,3}(\.\d{3})+(,\d+)?',s) or ',' in s: return Decimal(s.replace('.','').replace(',','.'))
    try:
        return Decimal(s)
    except Exception:
        print("PARSE?",repr(s)); return Decimal(-1)
out={}
for t,v in d.items():
    if t in MAN:
        cols=dict(zip(C,MAN[t])); src='MANUAL_IMAGE_CHECK'
    elif v.get('cols_order'):
        cols=v['cols_order']; src='AUTO_X_ORDER'
    else:
        print('EKSIK',t); continue
    ms,ys,be,bz=[num(cols[k]) for k in C[:4]]
    ok_a = ys==ms+be+bz
    out[t]={'cols':cols,'parse':src,'id_a_ok':ok_a}
    if not ok_a: print('ID-A tutmuyor',t,cols)
json.dump(out,open('spk_final.json','w'),ensure_ascii=False,indent=1)
print(len(out))

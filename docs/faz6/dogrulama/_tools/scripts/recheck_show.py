import sys,json,re
sys.path.insert(0,'.')
from blib import *
R=Path.home()/'Desktop/BorsAi_codex/verified/registry/oot'
SPK=json.load(open('spk_final.json')); SPKR=json.load(open('spk_rows.json'))
for t in sys.argv[1:]:
    d=tick(t); out=json.load(open(R/'inputs'/f'{t}.json'))['fields']
    print('#'*20,t,EV[t]['company'],'FTD',EV[t]['first_trading_date'])
    L=[x for x in d['docs'] if x['role']=='LISTING'][0]
    tx=fulltext(L['pdf']); i=tx.find('Borsa Karar'); print('LISTING',L['id'],L['published_at'],'::',tx[i:i+900])
    print('SPK',SPKR[t].get('no'),'::',SPK[t]['quote'],'| cols',SPK[t]['cols'])
    fo=SPKR[t].get('footnotes') or ''
    print('   dipnot::',re.sub(r'\s+',' ',fo)[:600])
    for x in d['docs']:
        if x['role'].startswith('RESULT'):
            for a in x['attachments'] or [None]:
                p=a['path'] if a else x['pdf']
                if a and not a.get('path'): continue
                ft=fulltext(p) or ''
                if a and ('dari' in a['name'] or 'İdari' in a['name']): continue
                j=ft.find('Açıklamalar'); ft=ft[j:] if 0<=j<400 else ft
                print('RESULT',x['id'],'EK'+str(a['n']) if a else 'bildirim',x['published_at'],'::',ft[:1800])
    print('--- ÇIKTI')
    for k,v in out.items(): print(f"   {k:32s} {str(v.get('value')):>18s}  {v.get('source_id') or ''}  {(v.get('carry_rule') or v.get('origin') or '')}  {(v.get('missing_reason') or '')[:80]}")

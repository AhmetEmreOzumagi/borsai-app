import csv,json,bisect
from decimal import Decimal
from datetime import date
T=list(csv.DictReader(open('data/training_table.csv',encoding='utf-8',newline='')))
rowsB=list(csv.DictReader(open('data/raw/v2_market20_official_pay_calendar_evidence_r4.csv',encoding='utf-8-sig',newline='')))
alld=[r['calendar_date'] for r in rowsB]; print('takvim B satir',len(alld),alld[0],alld[-1],'ardisik gun:',all((date.fromisoformat(b)-date.fromisoformat(a)).days==1 for a,b in zip(alld,alld[1:])))
print('half_day YES',sum(1 for r in rowsB if r['half_day']=='YES'),'verification',{r['verification_status'] for r in rowsB})
cal=sorted(r['calendar_date'] for r in rowsB if r['counts_as_official_session']=='YES')
X=json.load(open('data/raw/official_bist_xu100_graphic_pinned_through_20260819.json'),parse_float=Decimal); cl={r['hisTs']:r['clval'] for r in X['data']}
full=0; gaps=[]; s20min=None
for r in T:
    i=bisect.bisect_left(cal,r['first_trading_date'])-1
    w=cal[i-20:i+1]; full+=all(d in cl for d in w); gaps.append((date.fromisoformat(r['first_trading_date'])-date.fromisoformat(cal[i])).days)
    s20min=min(s20min or w[0],w[0])
print('21 kapanisin hepsi var:',full,'/99; en erken S20',s20min,'; T-S0 gun min/max',min(gaps),max(gaps))
print('T takvimde seans mi:',sum(1 for r in T if r['first_trading_date'] in set(cal)))

import csv, json, bisect, math
from decimal import Decimal
from fractions import Fraction
T=list(csv.DictReader(open('data/training_table.csv',encoding='utf-8',newline='')))
S=list(csv.DictReader(open('data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv',encoding='utf-8-sig',newline='')))
sd={(r['ticker'],int(r['session_number'])):r['target_session_date'] for r in S}
# --- A: hazard fold kurali: toplam olay>=5 ve sag kalim>=5
def pp(k,need_f3=True):
    Tk=k['first_trading_date']; ev=sv=0; nipo=0
    for j in T:
        if j['first_trading_date']>=Tk or (need_f3 and j['total_demand_multiple']==''): continue
        Lj=int(j['ceiling_streak_L']); got=False
        for d in range(1,11):
            if d-1>Lj or sd[(j['ticker'],d)]>=Tk: break
            got=True
            if Lj==d-1: ev+=1
            else: sv+=1
        nipo+=got
    return ev,sv,nipo
for need in (True,False):
  for m in (5,10):
    ok=[k for k in T if (not need or k['total_demand_multiple']!='') and min(pp(k,need)[:2])>=m and pp(k,need)[2]>=10]
    print('f3 sart',need,'min olay',m,'fold',len(ok),'ilk',ok[0]['ticker'],ok[0]['first_trading_date'],'egitim(ev,sv,nipo)',pp(ok[0],need),
      'test azinlik L<1,L<3,L<5,L>=10:',[sum(1 for k in ok if int(k['ceiling_streak_L'])<h) for h in (1,3,5)],sum(1 for k in ok if int(k['ceiling_streak_L'])>=10))
# --- B: PB
P=list(csv.DictReader(open('data/raw/PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv',encoding='utf-8-sig',newline='')))
pt={r['ticker']:r for r in P}; tt={r['ticker']:r for r in T}
print('PB ticker kumesi esit:',set(pt)==set(tt),'ftd esit:',all(pt[t]['canonical_first_trading_date']==tt[t]['first_trading_date'] for t in tt))
import collections
print('ek satis semantigi',collections.Counter(r['additional_sale_semantics'] for r in P))
pb={}
for r in P:
    D=lambda f:Decimal(r[f])
    assert D('planned_post_ipo_capital')==D('planned_pre_ipo_capital')+D('planned_capital_increase_shares'),r['ticker']
    assert D('planned_base_offer_shares')==D('planned_capital_increase_shares')+D('planned_existing_share_sale'),r['ticker']
    assert D('planned_max_offer_shares')==D('planned_base_offer_shares')+D('planned_additional_sale_ceiling'),r['ticker']
    base=D('planned_base_offer_shares')
    pb[r['ticker']]=(math.log(float(D('ipo_price_try')*base)),float(base/D('planned_post_ipo_capital')*100),float(D('planned_capital_increase_shares')/base*100),float(D('planned_additional_sale_ceiling')/base*100))
for i,nm in enumerate(['pb1','pb2','pb3','pb4']):
    v=sorted(x[i] for x in pb.values()); print(nm,'min',round(v[0],4),'med',round(v[49],4),'max',round(v[-1],4),'sifir',sum(1 for z in v if z==0),'==100',sum(1 for z in v if z==100))
print('pb4 degerleri',collections.Counter(round(x[3],2) for x in pb.values()))
# planli vs nihai farklar
dp=sum(1 for t in tt if Decimal(pt[t]['ipo_price_try'])!=Decimal(tt[t]['ipo_price_tl']))
ds=sum(1 for t in tt if Decimal(pt[t]['planned_base_offer_shares'])!=Decimal(tt[t]['shares_offered']))
dc=sum(1 for t in tt if Decimal(pt[t]['planned_capital_increase_shares'])!=Decimal(tt[t]['capital_increase_shares']))
print('planli!=nihai: fiyat',dp,'pay',ds,'sermaye artirimi',dc)
print([ (t,pt[t]['ipo_price_try'],tt[t]['ipo_price_tl']) for t in tt if Decimal(pt[t]['ipo_price_try'])!=Decimal(tt[t]['ipo_price_tl'])][:5])
from datetime import date
gaps=sorted((date.fromisoformat(r['canonical_first_trading_date'])-date.fromisoformat(r['first_bookbuilding_date'])).days for r in P)
print('ftd - ilk talep toplama gunu (gun): min,med,max',gaps[0],gaps[49],gaps[-1])
print('spk_pub < bookbuilding hepsi:',all(r['spk_publication_date']<r['first_bookbuilding_date'] for r in P))
# PB fold: hedef seans tarihi < first_bookbuilding_date(k)
hs={'D1':1,'D3':3,'D5':5,'D10':10}
for h,d in hs.items():
    n=[];
    for k in P:
        c=k['first_bookbuilding_date']
        n.append(sum(1 for j in P if sd[(j['ticker'],d)]<c))
    ok=[x for x in n if x>=10]; print('PB',h,'fold n>=10:',len(ok),'n_eff min/max',min(ok),max(ok))
    # azinlik (Y=0) skorlanabilir kumede
    okk=[k['ticker'] for k,x in zip(P,n) if x>=10]
    print('   Y=0 sayisi skorlanabilir:',sum(1 for t in okk if tt[t]['Y_'+h]=='0'),'tum:',sum(1 for t in tt if tt[t]['Y_'+h]=='0'))
# --- C: market20
cal=[r['calendar_date'] for r in csv.DictReader(open('data/raw/v2_market20_official_pay_calendar_evidence_r4.csv',encoding='utf-8-sig',newline='')) if r['counts_as_official_session']=='YES']
cal=sorted(set(cal)); print('takvim B seans',len(cal),cal[0],cal[-1])
calA=sorted({r['calendar_date'] for r in csv.DictReader(open('data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv',encoding='utf-8-sig',newline='')) if r['counts_as_official_session']=='TRUE'})
print('takvim A seans',len(calA),calA[0],calA[-1],'A alt kume B:',set(calA)<=set(cal), 'B∩[A araligi]==A:',[c for c in cal if c>=calA[0]]==calA)
X=json.load(open('data/raw/official_bist_xu100_graphic_pinned_through_20260819.json'),parse_float=Decimal)
cl={r['hisTs']:r['clval'] for r in X['data']}; print('xu100 kayit',len(cl),min(cl),max(cl))
miss=[c for c in cal if c not in cl]; print('takvim B seansinda XU100 kapanisi eksik:',len(miss),miss[:5])
extra=[d for d in cl if cal[0]<=d<=cal[-1] and d not in set(cal)]; print('XU100 var ama takvimde seans degil:',len(extra),extra[:5])
for name,c in (('A',calA),('B',cal)):
    okc=0;bad=[]
    for r in T:
        i=bisect.bisect_left(c,r['first_trading_date'])-1
        if i-20>=0 and c[i] in cl and c[i-20] in cl: okc+=1
        else: bad.append(r['ticker'])
    print('takvim',name,'hesaplanabilir',okc,bad)
vals=[]
for r in T:
    i=bisect.bisect_left(cal,r['first_trading_date'])-1; vals.append(float(cl[cal[i]]/cl[cal[i-20]]-1))
vals.sort(); print('f6 min/med/max',round(vals[0],4),round(vals[49],4),round(vals[-1],4))
# bayat S0 ornegi
i=bisect.bisect_left(cal,'2026-09-30')-1; print('T=2026-09-30 -> S0',cal[i])

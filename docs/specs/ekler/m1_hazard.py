# salt-okur olcum: hazard risk-gunu/olay sayilari, yeniden-tavan sayilari, fold uygunlugu
import csv, collections
T=list(csv.DictReader(open('data/training_table.csv',encoding='utf-8',newline='')))
S=list(csv.DictReader(open('data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv',encoding='utf-8-sig',newline='')))
sd={(r['ticker'],int(r['session_number'])):r['target_session_date'] for r in S}
print('n',len(T))
L={r['ticker']:int(r['ceiling_streak_L']) for r in T}
print('gun k: risk, olay(bozulma), hazard')
for k in range(1,11):
    risk=sum(1 for t in L if L[t]>=k-1); ev=sum(1 for t in L if L[t]==k-1)
    print(k,risk,ev,round(ev/risk,4))
print('toplam risk-gunu',sum(min(L[t]+1,10) for t in L),'olay',sum(1 for t in L if L[t]<10))
for g,(a,b) in {'g1':(1,1),'g2':(2,3),'g3':(4,10)}.items():
    risk=sum(sum(1 for t in L if L[t]>=k-1) for k in range(a,b+1)); ev=sum(sum(1 for t in L if L[t]==k-1) for k in range(a,b+1))
    print(g,risk,ev,round(ev/risk,4))
print('yeniden tavan: k, n(L<k), a(L<k & close_k=1)')
A=N=0
for k in range(2,11):
    n=sum(1 for r in T if int(r['ceiling_streak_L'])<k); a=sum(1 for r in T if int(r['ceiling_streak_L'])<k and r[f'ceiling_close_D{k}']=='1')
    A+=a;N+=n;print(k,n,a,round(a/n,4))
print('havuz',N,A,round(A/N,4))
# f3 eksikler
for r in T:
    if r['total_demand_multiple']=='': print('f3 eksik',r['ticker'],r['first_trading_date'],'L=',r['ceiling_streak_L'])
# walk-forward: test k icin egitim risk-gunleri = session_date(j,d) < T(k), j f3 dolu
rows=[r for r in T]
def train_pp(k):
    Tk=k['first_trading_date']; out=[]
    for j in rows:
        if j['first_trading_date']>=Tk or j['total_demand_multiple']=='': continue
        Lj=int(j['ceiling_streak_L'])
        for d in range(1,11):
            if d-1>Lj: break
            if sd[(j['ticker'],d)]>=Tk: break
            out.append((j['ticker'],d,1 if Lj==d-1 else 0))
    return out
grp=lambda d:0 if d==1 else (1 if d<=3 else 2)
def first_ok(minev,minsv):
    ok=[]
    for k in rows:
        if k['total_demand_multiple']=='': continue
        pp=train_pp(k); ev=[0,0,0]; sv=[0,0,0]
        for _,d,e in pp:
            (ev if e else sv)[grp(d)]+=1
        if min(ev)>=minev and min(sv)>=minsv: ok.append(k)
    return ok
for me in (1,2,3,5):
    ok=first_ok(me,me)
    print('min olay/grup',me,'-> skorlanabilir fold',len(ok),'ilk',ok[0]['ticker'],ok[0]['first_trading_date'],
          'L>=1,3,5,10 olmayan(azinlik):',[sum(1 for k in ok if int(k['ceiling_streak_L'])<h) for h in (1,3,5)],sum(1 for k in ok if int(k['ceiling_streak_L'])>=10))
# V1.5 kurali (n_eff>=10 D1 hedefi) ile karsilastirma
ok10=[k for k in rows if sum(1 for j in rows if j['first_trading_date']<k['first_trading_date'])>=10]
print('kronolojik n>=10 fold',len(ok10))

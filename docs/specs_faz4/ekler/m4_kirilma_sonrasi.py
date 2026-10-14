# salt-okur tanimlayici olcum (FAZ4, SPEC_CEILING_PATH_V0): yalniz H99 dosyalari, yalniz stdlib.
# Hicbir model fit edilmez, hicbir walk-forward skoru hesaplanmaz, ozellik-sonuc iliskisine bakilmaz.
# Okunan: data/training_table.csv (L, R_Dh, ipo fiyati), SESSIONS (kapanis, referans, ust/alt limit, tarih).
import csv, statistics as st
from decimal import Decimal as D, ROUND_FLOOR, ROUND_CEILING, ROUND_HALF_UP, ROUND_HALF_EVEN
T=list(csv.DictReader(open('data/training_table.csv',encoding='utf-8',newline='')))
S=list(csv.DictReader(open('data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv',encoding='utf-8-sig',newline='')))
ses={(r['ticker'],int(r['session_number'])):r for r in S}
L={r['ticker']:int(r['ceiling_streak_L']) for r in T}
P={r['ticker']:D(r['ipo_price_tl']) for r in T}
tick=[r['ticker'] for r in T]
def q(xs,p):
    xs=sorted(xs); n=len(xs)
    if n==1: return xs[0]
    h=(n-1)*p; i=int(h); f=h-i
    return xs[i]+(xs[min(i+1,n-1)]-xs[i])*f
def desc(xs):
    xs=[float(x) for x in xs]
    if not xs: return 'n=0'
    return f"n={len(xs)} min={min(xs):+.4f} p10={q(xs,.1):+.4f} p25={q(xs,.25):+.4f} med={st.median(xs):+.4f} p75={q(xs,.75):+.4f} p90={q(xs,.9):+.4f} max={max(xs):+.4f} ort={st.mean(xs):+.4f} sd={(st.pstdev(xs) if len(xs)>1 else 0):.4f}"
print('== 1. kirilma gunu dagilimi (L; L=10 sansurlu) ==')
for l in range(11): print(' L=',l,sum(1 for t in tick if L[t]==l))
print('== 2. ust limit / referans orani (990 seans) ==')
rat=[D(ses[(t,k)]['upper_limit'])/D(ses[(t,k)]['reference_price']) for t in tick for k in range(1,11)]
print(' ', desc(rat), ' tam 1.1 olan:',sum(1 for r in rat if r==D('1.1')))
print(' D1 referans == arz fiyati:',sum(1 for t in tick if D(ses[(t,1)]['reference_price'])==P[t]),'/99; farkli:',[ (t,ses[(t,1)]['reference_price'],str(P[t])) for t in tick if D(ses[(t,1)]['reference_price'])!=P[t]])
print(' referans(D_k) == kapanis(D_{k-1}) (k>=2):',sum(1 for t in tick for k in range(2,11) if D(ses[(t,k)]['reference_price'])==D(ses[(t,k-1)]['close'])),'/891')
print('== 3. fiyat adimi tablosu adaylari ve yuvarlama modu (ust limit = yuvarla(referans*1.1)) ==')
TABLE_A=[(D('20'),D('0.01')),(D('50'),D('0.02')),(D('100'),D('0.05')),(D('250'),D('0.10')),(D('500'),D('0.25')),(D('1000'),D('0.50')),(D('2500'),D('1.00')),(None,D('2.50'))]
def step(price,table):
    for lim,s in table:
        if lim is None or price<lim: return s
def lim_up(ref,mode,table,by='raw'):
    raw=ref*D('1.1'); s=step(raw if by=='raw' else ref,table)
    return (raw/s).quantize(D('1'),rounding=mode)*s
def lim_dn(ref,mode,table,by='raw'):
    raw=ref*D('0.9'); s=step(raw if by=='raw' else ref,table)
    return (raw/s).quantize(D('1'),rounding=mode)*s
for by in ('raw','ref'):
  for name,mode in (('FLOOR',ROUND_FLOOR),('CEIL',ROUND_CEILING),('HALF_UP',ROUND_HALF_UP),('HALF_EVEN',ROUND_HALF_EVEN)):
    okU=sum(1 for t in tick for k in range(1,11) if lim_up(D(ses[(t,k)]['reference_price']),mode,TABLE_A,by)==D(ses[(t,k)]['upper_limit']))
    okD=sum(1 for t in tick for k in range(1,11) if lim_dn(D(ses[(t,k)]['reference_price']),mode,TABLE_A,by)==D(ses[(t,k)]['lower_limit']))
    print(f'  adim {by} fiyata gore, mod {name}: ust limit tutan {okU}/990, alt limit tutan {okD}/990')
bad=[(t,k,ses[(t,k)]['reference_price'],ses[(t,k)]['upper_limit'],str(lim_up(D(ses[(t,k)]['reference_price']),ROUND_FLOOR,TABLE_A,'raw'))) for t in tick for k in range(1,11) if lim_up(D(ses[(t,k)]['reference_price']),ROUND_FLOOR,TABLE_A,'raw')!=D(ses[(t,k)]['upper_limit'])]
print('  FLOOR/raw ile tutmayan ust limitler (ilk 15):',bad[:15])
print('== 4. limit yolu C_h: gerceklesen (L>=h) vs 1.1^h ve deterministik yuvarlama ==')
def det_path(p,h):
    ref=p
    for _ in range(h): ref=lim_up(ref,ROUND_FLOOR,TABLE_A,'raw')
    return ref
for h in (1,3,5,10):
    real=[(t,D(ses[(t,h)]['close'])/P[t]-1) for t in tick if L[t]>=h]
    e11=[float(r-(D('1.1')**h-1)) for _,r in real]
    edet=[float(r-(det_path(P[t],h)/P[t]-1)) for t,r in real]
    print(f' h={h} n={len(real)} R_h-(1.1^h-1): {desc(e11)}')
    print(f'      R_h-(det.yol-1): {desc(edet)} tam esit {sum(1 for x in edet if x==0)}/{len(real)}')
print('== 5. L=t<h durum sayilari (h in 1,3,5,10; t=0 ayri) ==')
for h in (1,3,5,10):
    row={t_:sum(1 for t in tick if L[t]==t_) for t_ in range(h)}
    print(f' h={h}: L>=h {sum(1 for t in tick if L[t]>=h)}; L<h {sum(row.values())}; t=0 {row.get(0,0)}; t>=1 {sum(v for k,v in row.items() if k>=1)}; ayrinti {row}')
print('== 6. kirilma sonrasi getiri  G(t,h) = close(D_h)/close(D_t) - 1  (t>=1: D_t son tavan gunu; t=0: arz fiyati) ==')
def G(t,t_,h):
    base=P[t] if t_==0 else D(ses[(t,t_)]['close'])
    return D(ses[(t,h)]['close'])/base-1
print(' -- h sabit, t=0 ve t>=1 ayri --')
for h in (1,3,5,10):
    g0=[G(t,0,h) for t in tick if L[t]==0]
    g1=[G(t,L[t],h) for t in tick if 1<=L[t]<h]
    print(f' h={h} t=0 : {desc(g0)}')
    print(f' h={h} t>=1: {desc(g1)}')
print(' -- gecen seans sayisi m = h - t (tum h=1..10 birlestirilmis, t>=1; her arz-h cifti bir gozlem) --')
for m in range(1,10):
    g=[G(t,L[t],L[t]+m) for t in tick if 1<=L[t] and L[t]+m<=10]
    print(f' m={m}: {desc(g)}')
print(' -- ayni sey t=0 icin (m=h) --')
for m in (1,2,3,4,5,6,7,8,9,10):
    g=[G(t,0,m) for t in tick if L[t]==0]
    print(f' m={m}: {desc(g)}')
print(' -- ilk kirilma gunu getirisi (m=1) t gruplarina gore --')
for grp,ts in (('t=0',[0]),('t=1',[1]),('t=2,3',[2,3]),('t>=4',list(range(4,10)))):
    g=[G(t,L[t],L[t]+1) for t in tick if L[t] in ts and L[t]+1<=10]
    print(f' {grp}: {desc(g)}')
print(' -- seans basina ortalama log-getiri kirilma sonrasi: ln(1+G)/m, t>=1 --')
import math
for m in (1,2,3,5,9):
    g=[math.log(1+float(G(t,L[t],L[t]+m)))/m for t in tick if 1<=L[t] and L[t]+m<=10]
    print(f' m={m}: {desc(g)}')
print('== 7. kirilma sonrasi getiri fiziksel sinir icinde mi (0.9^m-1 <= G <= 1.1^m-1) ==')
viol=0; tot=0
for t in tick:
    for h in range(L[t]+1,11):
        if L[t]>=10: break
        m=h-L[t]; g=G(t,L[t],h); tot+=1
        if not (D('0.9')**m-1-D('0.0005')<=g<=D('1.1')**m-1+D('0.0005')): viol+=1
print(' toplam gozlem',tot,'sinir disi',viol)
print('== 8. kirilma sonrasi yeniden tavan ve taban (kapanis == ust limit / alt limit) sayilari, m gecen seans ==')
for m in range(1,10):
    n=u=d=0
    for t in tick:
        if L[t]>=10 or L[t]+m>10: continue
        k=L[t]+m; r=ses[(t,k)]; n+=1
        u+=D(r['close'])==D(r['upper_limit']); d+=D(r['close'])==D(r['lower_limit'])
    print(f' m={m}: n={n} tavan={u} taban={d}')
print('== 9. R_h > 0 (Y_h) oranlari: L>=h grubu ve L<h grubu ==')
for h in (1,3,5,10):
    a=[int(T[i][f'Y_D{h}']) for i in range(99) if L[T[i]['ticker']]>=h]; b=[int(T[i][f'Y_D{h}']) for i in range(99) if L[T[i]['ticker']]<h]
    print(f' h={h}: L>=h n={len(a)} Y=1 {sum(a)}; L<h n={len(b)} Y=1 {sum(b)} ({(sum(b)/len(b) if b else 0):.3f})')
print('== 10. kirilma sonrasi getirinin (t>=1, m=1..9 birlesik) medyani ve MAE-optimal sabitin ipucu: sadece tanimlayici ==')
allg=[float(G(t,L[t],L[t]+m)) for t in tick for m in range(1,10) if 1<=L[t] and L[t]+m<=10]
print(' ',desc(allg))
print('== 11. D1 referansi = arz fiyatinin fiyat adimina yuvarlanmasi mi? (4 farkli arz) ==')
for t in tick:
    ref=D(ses[(t,1)]['reference_price']); p=P[t]
    if ref!=p:
        s=step(p,TABLE_A)
        cands={m:(p/s).quantize(D('1'),rounding=mode)*s for m,mode in (('FLOOR',ROUND_FLOOR),('CEIL',ROUND_CEILING),('HALF_UP',ROUND_HALF_UP),('HALF_EVEN',ROUND_HALF_EVEN))}
        print(' ',t,'arz',p,'ref',ref,'adim',s,{m:str(v) for m,v in cands.items()},'tutan:',[m for m,v in cands.items() if v==ref])
print(' arz fiyati adim izgarasinda olan arz sayisi:',sum(1 for t in tick if (P[t]/step(P[t],TABLE_A))==(P[t]/step(P[t],TABLE_A)).to_integral_value()),'/99')
print('== 12. limit yolu C_h (arz fiyati once HALF_UP ile adima oturtulur, sonra FLOOR ile h kez ust limit) vs gerceklesen ==')
def snap(p): s=step(p,TABLE_A); return (p/s).quantize(D('1'),rounding=ROUND_HALF_UP)*s
def det_path2(p,h):
    ref=snap(p)
    for _ in range(h): ref=lim_up(ref,ROUND_FLOOR,TABLE_A,'raw')
    return ref
for h in range(1,11):
    real=[t for t in tick if L[t]>=h]
    eq=sum(1 for t in real if D(ses[(t,h)]['close'])==det_path2(P[t],h))
    print(f' h={h}: n={len(real)} kapanis == C_h(det) {eq}/{len(real)}')
print('== 13. C_h(det)/arz-1 ile 1.1^h-1 farki, 99 arzin hepsinde (tahmin aninda hesaplanabilir) ==')
for h in (1,3,5,10):
    e=[float(det_path2(P[t],h)/P[t]-1-(D('1.1')**h-1)) for t in tick]
    print(f' h={h}: {desc(e)}')
print('== 14. walk-forward hucre buyuklukleri: test arzi k (f3 dolu), kesim T=ilk islem gunu; hucre (g,m): Z=t=0 (m=h), B=t>=1 (m=h-t); gozlem ancak seans(D_{t+m}) < T ise ==')
sd={(r['ticker'],int(r['session_number'])):r['target_session_date'] for r in S}
f3ok=[r for r in T if r['total_demand_multiple']!='']
def cells(Tk):
    Z={m:0 for m in range(1,11)}; B={m:0 for m in range(1,10)}
    for j in T:
        if j['first_trading_date']>=Tk: continue
        Lj=L[j['ticker']]
        if Lj>=10: continue
        for h in range(Lj+1,11):
            if sd[(j['ticker'],h)]>=Tk: break
            (Z if Lj==0 else B)[h-Lj]+=1
    return Z,B
first=None; minB1=[]; minZ1=[]; rows_out=[]
for k in f3ok:
    Z,B=cells(k['first_trading_date'])
    rows_out.append((k['ticker'],k['first_trading_date'],Z,B))
for tk,Tk,Z,B in rows_out[:14]:
    print(f' {tk} {Tk} Z={list(Z.values())} B={list(B.values())} toplamZ={sum(Z.values())} toplamB={sum(B.values())}')
print(' ... son fold:',rows_out[-1][0],rows_out[-1][1],'Z=',list(rows_out[-1][2].values()),'B=',list(rows_out[-1][3].values()))
for nmin in (5,8,10,15):
    zc=[sum(1 for tk,Tk,Z,B in rows_out if Z[m]<nmin) for m in (1,3,5,10)]
    bc=[sum(1 for tk,Tk,Z,B in rows_out if B[m]<nmin) for m in (1,3,5,9)]
    print(f' N_MIN={nmin}: hucre n<N_MIN olan fold sayisi (97 test arzi) Z m=1,3,5,10: {zc}; B m=1,3,5,9: {bc}')
# ceiling plani skorlanabilir foldlarin (SPEC_CEILING_V0 §9: >=10 arz, >=5 olay, >=5 sag kalim) ilk 10'u
def pp_ok(Tk):
    n_ipo=set(); ev=sv_=0
    for j in f3ok:
        if j['first_trading_date']>=Tk: continue
        Lj=L[j['ticker']]
        for d in range(1,11):
            if d-1>Lj or sd[(j['ticker'],d)]>=Tk: break
            n_ipo.add(j['ticker']); 
            if Lj==d-1: ev+=1
            else: sv_+=1
    return len(n_ipo)>=10 and ev>=5 and sv_>=5
sc=[(tk,Tk,Z,B) for tk,Tk,Z,B in rows_out if pp_ok(Tk)]
print(' skorlanabilir fold (tavan plani kurali):',len(sc),'ilk',sc[0][0],sc[0][1])
for tk,Tk,Z,B in sc[:8]:
    print(f'  {tk} {Tk} Z={list(Z.values())} B={list(B.values())}')
for nmin in (5,8,10):
    print(f'  N_MIN={nmin}: skorlanabilir foldlarda Z toplam<N_MIN: {sum(1 for _,_,Z,B in sc if sum(Z.values())<nmin)}, B toplam<N_MIN: {sum(1 for _,_,Z,B in sc if sum(B.values())<nmin)}, Z[1]<N_MIN: {sum(1 for _,_,Z,B in sc if Z[1]<nmin)}, B[1]<N_MIN: {sum(1 for _,_,Z,B in sc if B[1]<nmin)}, B[9]<N_MIN: {sum(1 for _,_,Z,B in sc if B[9]<nmin)}, Z[10]<N_MIN: {sum(1 for _,_,Z,B in sc if Z[10]<nmin)}')

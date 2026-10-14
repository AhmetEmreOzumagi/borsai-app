import csv, random
from pathlib import Path
ROOT = Path('/Users/ahmet/Desktop/BorsAi'); G4 = ROOT/'tests/reference/macos_golden_faz4'
def rd(p):
    with open(p, encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def boot(diffs, months):
    rng = random.Random(20260921); by = {}
    for m, d in zip(months, diffs): by.setdefault(m, []).append(d)
    keys = list(by); out = []
    for _ in range(4000):
        s = []
        for k in rng.choices(keys, k=len(keys)): s += by[k]
        out.append(sum(s)/len(s))
    out.sort(); return out[100], out[3899]
R = {r['ticker']: float(r['R_D5']) for r in rd(ROOT/'data/training_table.csv')}
path = {r['ticker']: r for r in rd(G4/'ceiling_path_v0_fold_ledger.csv') if r['status']=='OK'}
inf = {r['ticker']: r for r in rd(G4/'ceiling_path_v0@INF_fold_ledger.csv') if r['status']=='OK'}
pairs = [(path[t]['first_trading_date'][:7], abs(float(path[t]['D5_return'])-R[t]), abs(float(inf[t]['D5_return'])-R[t])) for t in path if t in inf]
d = [a-b for _,a,b in pairs]; lo,hi = boot(d,[m for m,_,_ in pairs])
print('ceiling_path_v0 D5 MAE − @INF (tablo R_D5, 87 fold): n=%d diff=%+.4f [%+.4f, %+.4f]  kılavuz -0.1033 [-0.1462, -0.0628], 87' % (len(d), sum(d)/len(d), lo, hi))

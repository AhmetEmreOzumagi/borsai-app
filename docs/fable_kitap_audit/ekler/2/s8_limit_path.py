"""§4.6.2 limit yolu: C_h deterministik yuvarlama (HALF_UP snap, aşağı adım) ve gerçekleşen kapanışla Decimal eşitlik (seri ≥ h olan arz-günler)."""
import csv
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR
from pathlib import Path
ROOT = Path('/Users/ahmet/Desktop/BorsAi')
def rd(p):
    with open(p, encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
TICKS = [(Decimal('0.01'), Decimal('20'), Decimal('0.01')), (Decimal('20'), Decimal('50'), Decimal('0.02')), (Decimal('50'), Decimal('100'), Decimal('0.05')), (Decimal('100'), Decimal('250'), Decimal('0.10')),
         (Decimal('250'), Decimal('500'), Decimal('0.25')), (Decimal('500'), Decimal('1000'), Decimal('0.50')), (Decimal('1000'), Decimal('2500'), Decimal('1.00')), (Decimal('2500'), None, Decimal('2.50'))]
def tick(x):
    for lo, hi, t in TICKS:
        if x >= lo and (hi is None or x < hi): return t
    raise ValueError(x)
def U(b):
    x = b * Decimal('1.10'); t = tick(x); return (x / t).to_integral_value(rounding=ROUND_FLOOR) * t
def snap(P):
    t = tick(P); return (P / t).to_integral_value(rounding=ROUND_HALF_UP) * t
tbl = {r['ticker']: r for r in rd(ROOT / 'data/training_table.csv')}
closes = {}
for r in rd(ROOT / 'data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv'):
    closes.setdefault(r['ticker'], {})[int(r['session_number'])] = (Decimal(r['close']), Decimal(r['upper_limit']))
eq = [0] * 11; tot = [0] * 11; snapped = []; upper_eq = 0; upper_tot = 0
for t, r in tbl.items():
    P = Decimal(r['ipo_price_tl']); L = int(r['ceiling_streak_L']); b = snap(P)
    if b != P: snapped.append((t, str(P), str(b)))
    C = []; c = b
    for h in range(1, 11):
        c = U(c); C.append(c)
        if L >= h:
            tot[h] += 1; eq[h] += int(closes[t][h][0] == c)
    # THM üst limitiyle de karşılaştır: referans = önceki kapanış (D1: snap(P))
    ref = b
    for h in range(1, 11):
        upper_tot += 1; upper_eq += int(closes[t][h][1] == U(ref)); ref = closes[t][h][0]
print('C_h == gerçekleşen kapanış (seri ≥ h):', [f'{eq[h]}/{tot[h]}' for h in range(1, 11)], 'toplam', sum(eq[1:]), '/', sum(tot[1:]))
print('THM üst limiti == U(önceki kapanış):', upper_eq, '/', upper_tot)
print('snap(P) != P olan arzlar:', snapped)
P = Decimal('25.52'); b = snap(P); C = []; c = b
for h in range(1, 11): c = U(c); C.append(c)
print('NETGL C_h:', [str(x) for x in C[:5]], 'rho:', [round(float(x / P - 1), 4) for x in C[:5]])

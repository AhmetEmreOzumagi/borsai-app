"""KITAP_AUDIT_2 Adım 4: §4.9 (ve §4.3.6, §4.4.12, §4.5, §4.6.6, §4.7.4, §4.8.4) hükümlerini ledger'lardan kendi bootstrap'ımla yeniden üret.
borsai import edilmez. Bootstrap: SPEC_DEVIATIONS C7 / MODELS.md: ilk işlem ayı blokları, iadeli çekim (random.choices), 4000 tekrar,
random.Random(20260921) her hücrede ayrı, sıralı dağılımın 100. ve 3899. elemanı."""
import csv, json, math, random
from pathlib import Path
ROOT = Path('/Users/ahmet/Desktop/BorsAi')
G0 = ROOT / 'tests/reference/macos_golden'; G1 = ROOT / 'tests/reference/macos_golden_faz1b'; G4 = ROOT / 'tests/reference/macos_golden_faz4'
G7 = ROOT / 'tests/reference/macos_golden_faz7'; G7C = ROOT / 'tests/reference/macos_golden_faz7c'

def rd(p):
    with open(p, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def boot(diffs, months, reps=4000, seed=20260921):
    rng = random.Random(seed)
    by = {}
    for m, d in zip(months, diffs):
        by.setdefault(m, []).append(d)
    keys = list(by)
    out = []
    for _ in range(reps):
        s = []
        for k in rng.choices(keys, k=len(keys)):
            s += by[k]
        out.append(sum(s) / len(s))
    out.sort()
    return out[100], out[3899]

def verdict(lo, hi, kind='model'):
    if hi < 0: return 'geçiyor'
    if lo > 0: return 'geçemiyor'
    return 'ayırt edilemiyor'

def cell(pairs, label, expect=None):
    """pairs: list of (month, loss_model, loss_rule). Returns dict and prints comparison with guide expectation (diff, lo, hi, n)."""
    diffs = [a - b for _, a, b in pairs]; months = [m for m, _, _ in pairs]
    n = len(diffs); mean = sum(diffs) / n
    lo, hi = boot(diffs, months)
    res = dict(label=label, n=n, n_blocks=len(set(months)), diff=mean, lo=lo, hi=hi, verdict=verdict(lo, hi),
               model=sum(a for _, a, _ in pairs) / n, rule=sum(b for _, _, b in pairs) / n,
               wins=sum(1 for d in diffs if d < 0), losses=sum(1 for d in diffs if d > 0), ties=sum(1 for d in diffs if d == 0))
    ok = None
    if expect is not None:
        ed, elo, ehi, en = expect
        ok = (round(mean, 4) == ed and round(lo, 4) == elo and round(hi, 4) == ehi and n == en)
    res['guide'] = expect; res['guide_match_4dp'] = ok
    flag = '' if ok is None else ('  OK' if ok else '  **MISMATCH**')
    print(f"{label:70s} n={n:3d} ({len(set(months)):2d}) diff={mean:+.4f} [{lo:+.4f}, {hi:+.4f}] {res['verdict']:17s}{flag}  guide={expect}")
    return res

RES = []
def clip(p): return min(max(p, 0.01), 0.99)
def month_of(r): return (r.get('first_trading_date') or r['prediction_date'])[:7]

# ---------- V1.5 planı ledger'ları (macos_golden)
v15 = rd(G0 / 'v1_5_h99_fold_ledger.csv')
rules0 = {k: rd(G0 / f'{k}_fold_ledger.csv') for k in ('base_train_median', 'base_train_mean', 'base_zero', 'base_always_ceiling', 'base_rate', 'base_last10_rate')}
def key(r): return (r['horizon'], r['ticker'])
v15_ridge = {key(r): r for r in v15 if r['ridge_status'] == 'FIT_OK'}
v15_logit = {key(r): r for r in v15 if r['logit_status'] == 'FIT_OK'}
rule_by = {k: {key(r): r for r in v} for k, v in rules0.items()}
def mae_pairs(model_rows, rule_rows, h, mkey='ridge_prediction', rkey='rule_return', realized='realized_return'):
    out = []
    for k, r in model_rows.items():
        if k[0] != h or k not in rule_rows: continue
        y = float(r[realized]) if realized in r else float(rule_rows[k]['realized_return'])
        out.append((month_of(r), abs(float(r[mkey]) - y), abs(float(rule_rows[k][rkey]) - y)))
    return out
def brier_pairs(model_rows, rule_rows, h, mkey='logit_probability', rkey='rule_p_up', clipped=True):
    out = []
    for k, r in model_rows.items():
        if k[0] != h or k not in rule_rows: continue
        y = int(rule_rows[k]['realized_direction']) if 'realized_direction' in rule_rows[k] else int(r['realized_direction'])
        pm, pr = float(r[mkey]), float(rule_rows[k][rkey])
        if clipped: pm, pr = clip(pm), clip(pr)
        out.append((month_of(r), (pm - y) ** 2, (pr - y) ** 2))
    return out

print('==== §4.3.6 v1_5_h99')
exp = {('D1', 'base_train_median'): (0.0046, 0.0015, 0.0079, 89), ('D1', 'base_train_mean'): (-0.0035, -0.0060, -0.0011, 89),
       ('D3', 'base_train_median'): (-0.0157, -0.0524, 0.0190, 88), ('D5', 'base_train_median'): (-0.0839, -0.1343, -0.0321, 87),
       ('D10', 'base_train_median'): (-0.1163, -0.1996, -0.0208, 87), ('D10', 'base_zero'): (-0.0498, -0.2283, 0.1514, 87)}
for (h, rule), e in exp.items():
    RES.append(cell(mae_pairs(v15_ridge, rule_by[rule], h), f'v1_5_h99 {h} MAE − {rule}', e))
expb = {('D1', 'base_rate'): (-0.0078, -0.0286, 0.0115, 80), ('D3', 'base_rate'): (-0.0359, -0.0817, 0.0104, 80), ('D5', 'base_rate'): (-0.0343, -0.0773, 0.0106, 81),
        ('D10', 'base_rate'): (-0.0391, -0.0756, 0.0023, 81), ('D10', 'base_last10_rate'): (-0.0908, -0.1527, -0.0287, 81)}
for (h, rule), e in expb.items():
    RES.append(cell(brier_pairs(v15_logit, rule_by[rule], h), f'v1_5_h99 {h} Brier − {rule}', e))

# ---------- v1_6 ve market20 (V1.5'e karşı; aynı plan)
for mid, prim in (('v1_6_h99', ('D10', (0.0008, -0.0003, 0.0028, 87))), ('v1_5_market20_v0', ('D5', (-0.0008, -0.0178, 0.0137, 87)))):
    led = rd(G1 / f'{mid}_fold_ledger.csv')
    mr = {key(r): r for r in led if r['ridge_status'] == 'FIT_OK'}; ml = {key(r): r for r in led if r['logit_status'] == 'FIT_OK'}
    print(f'==== §4.3.7/8 {mid}')
    for h in ('D1', 'D3', 'D5', 'D10'):
        e = prim[1] if h == prim[0] else None
        RES.append(cell(mae_pairs(mr, v15_ridge, h, rkey='ridge_prediction'), f'{mid} {h} MAE − v1_5_h99', e))
    for h in ('D1', 'D3', 'D5', 'D10'):
        RES.append(cell(brier_pairs(ml, v15_logit, h, rkey='logit_probability'), f'{mid} {h} Brier − v1_5_h99 (kırpılı)', None))

# ---------- pb_v0 (PB planı kuralları)
pb = rd(G1 / 'pb_v0_fold_ledger.csv')
pbr = {key(r): r for r in pb if r['ridge_status'] == 'FIT_OK'}; pbl = {key(r): r for r in pb if r['logit_status'] == 'FIT_OK'}
rulesPB = {k: {key(r): r for r in rd(G1 / f'{k}__pb_fold_ledger.csv')} for k in ('base_train_median', 'base_rate')}
print('==== §4.5.3 pb_v0')
RES.append(cell(mae_pairs(pbr, rulesPB['base_train_median'], 'D5'), 'pb_v0 D5 MAE − base_train_median (birincil)', (-0.0355, -0.0775, 0.0102, 87)))
RES.append(cell(mae_pairs(pbr, rulesPB['base_train_median'], 'D1'), 'pb_v0 D1 MAE − base_train_median', (0.0083, 0.0047, 0.0125, 87)))
RES.append(cell(mae_pairs(pbr, rulesPB['base_train_median'], 'D10'), 'pb_v0 D10 MAE − base_train_median', (-0.0478, -0.1067, 0.0146, 84)))
RES.append(cell(brier_pairs(pbl, rulesPB['base_rate'], 'D1'), 'pb_v0 D1 Brier − base_rate', (-0.0025, -0.0080, 0.0018, 80)))
RES.append(cell(brier_pairs(pbl, rulesPB['base_rate'], 'D10'), 'pb_v0 D10 Brier − base_rate', (-0.0147, -0.0259, -0.0042, 80)))
for h, e in (('D1', None), ('D3', None), ('D5', (0.0530, 0.0337, 0.0726, None)), ('D10', (0.0880, -0.0062, 0.1732, None))):
    pairs = mae_pairs(pbr, v15_ridge, h, rkey='ridge_prediction')
    if e: e = (e[0], e[1], e[2], len(pairs))
    RES.append(cell(pairs, f'pb_v0 {h} MAE − v1_5_h99 (bilgi)', e))

# ---------- tavan: RPS
def S_of(r): return [float(r[f'S_{k}']) for k in range(1, 11)]
def rps(S, L): return sum((S[k] - (1.0 if L >= k + 1 else 0.0)) ** 2 for k in range(10)) / 10
def ok_c(r): return r['status'] in ('FIT_OK', 'RULE_OK')
def ceiling_pairs(model_rows, rule_rows, metric='rps', start=None):
    other = {r['ticker']: r for r in rule_rows if ok_c(r)}
    out = []
    for r in model_rows:
        if not ok_c(r) or r['ticker'] not in other: continue
        t = r['first_trading_date']
        if start and t < start: continue
        L = int(r['realized_L'])
        if metric == 'rps':
            a, b = rps(S_of(r), L), rps(S_of(other[r['ticker']]), L)
        else:
            k = int(metric[5:]); a = (S_of(r)[k - 1] - (1.0 if L >= k else 0.0)) ** 2; b = (S_of(other[r['ticker']])[k - 1] - (1.0 if L >= k else 0.0)) ** 2
        out.append((t[:7], a, b))
    return out
v0 = rd(G1 / 'ceiling_hazard_v0_fold_ledger.csv')
crules = {k: rd(G1 / f'{k}_fold_ledger.csv') for k in ('base_km_expanding', 'base_km_last10', 'ceiling_hazard_v0@INF', 'base_always_ceiling__ceiling')}
print('==== §4.4.12 ceiling_hazard_v0')
for k, e in (('base_km_expanding', (-0.0569, -0.0833, -0.0286, 87)), ('base_km_last10', (-0.0496, -0.0751, -0.0219, 87)),
             ('ceiling_hazard_v0@INF', (-0.0503, -0.0724, -0.0263, 87)), ('base_always_ceiling__ceiling', (-0.4462, -0.5488, -0.3236, 87))):
    RES.append(cell(ceiling_pairs(v0, crules[k]), f'ceiling_hazard_v0 RPS − {k}', e))
for k, e in ((1, (-0.0271, -0.0497, -0.0052, 87)), (3, (-0.0939, -0.1287, -0.0578, 87)), (5, (-0.0726, -0.1170, -0.0274, 87)),
             (8, (-0.0204, -0.0606, 0.0222, 87)), (9, (-0.0105, -0.0553, 0.0384, 87)), (10, (-0.0055, -0.0502, 0.0375, 87))):
    RES.append(cell(ceiling_pairs(v0, crules['base_km_last10'], f'brier{k}'), f'ceiling_hazard_v0 Brier k={k} − base_km_last10', e))
# kalibrasyon
okv0 = [r for r in v0 if ok_c(r)]
cal = {k: (sum(S_of(r)[k - 1] for r in okv0) / len(okv0), sum(1 for r in okv0 if int(r['realized_L']) >= k) / len(okv0)) for k in (1, 3, 5, 10)}
print('kalibrasyon (ort S_k, gözlenen):', {k: (round(a, 4), round(b, 4)) for k, (a, b) in cal.items()}, 'kılavuz: 1:(0.8655,0.8161) 3:(0.7041,0.6437) 5:(0.4342,0.3793) 10:(0.1874,0.1264)')
RES.append(dict(label='calibration_v0', values=cal))

# ---------- pb_ceiling_v0
pbc = rd(G1 / 'pb_ceiling_v0_fold_ledger.csv')
pbcr = {k: rd(G1 / f'{k}_fold_ledger.csv') for k in ('base_km_expanding__pb_ceiling', 'base_km_last10__pb_ceiling', 'pb_ceiling_v0@INF')}
print('==== §4.5.4 pb_ceiling_v0')
for k, e in (('base_km_expanding__pb_ceiling', (-0.0324, -0.0544, -0.0114, 87)), ('base_km_last10__pb_ceiling', (-0.0335, -0.0612, -0.0019, 87)), ('pb_ceiling_v0@INF', (-0.0235, -0.0367, -0.0083, 87))):
    RES.append(cell(ceiling_pairs(pbc, pbcr[k]), f'pb_ceiling_v0 RPS − {k}', e))
RES.append(cell(ceiling_pairs(pbc, v0), 'pb_ceiling_v0 RPS − ceiling_hazard_v0 (bilgi)', (0.0342, 0.0180, 0.0515, 85)))

# ---------- ceiling_path_v0 (V1.5 planı ledger'larıyla eşleştirme, ticker+ufuk)
path = rd(G4 / 'ceiling_path_v0_fold_ledger.csv'); pathI = rd(G4 / 'ceiling_path_v0@INF_fold_ledger.csv'); pbpath = rd(G4 / 'pb_ceiling_path_v0_fold_ledger.csv')
def path_mae_pairs(prow_list, rule_rows, h, rkey='rule_return', status_ok=('OK',)):
    out = []
    for r in prow_list:
        if r['status'] not in status_ok or r[f'{h}_post_break_status'] != 'OK' or r[f'{h}_return'] == '': continue
        k = (h, r['ticker'])
        if k not in rule_rows: continue
        y = float(rule_rows[k]['realized_return'])
        out.append((r['first_trading_date'][:7], abs(float(r[f'{h}_return']) - y), abs(float(rule_rows[k][rkey]) - y)))
    return out
def path_brier_pairs(prow_list, rule_rows, h, rkey='rule_p_up'):
    out = []
    for r in prow_list:
        if r['status'] != 'OK' or r[f'{h}_post_break_status'] != 'OK' or r[f'{h}_p_up'] == '': continue
        k = (h, r['ticker'])
        if k not in rule_rows: continue
        y = int(rule_rows[k]['realized_direction'])
        out.append((r['first_trading_date'][:7], (clip(float(r[f'{h}_p_up'])) - y) ** 2, (clip(float(rule_rows[k][rkey])) - y) ** 2))
    return out
print('==== §4.6.6 ceiling_path_v0')
RES.append(cell(path_mae_pairs(path, rule_by['base_train_median'], 'D5'), 'ceiling_path_v0 D5 MAE − base_train_median (birincil)', (-0.1158, -0.1611, -0.0738, 85)))
RES.append(cell(path_mae_pairs(path, rule_by['base_always_ceiling'], 'D1'), 'ceiling_path_v0 D1 MAE − base_always_ceiling', (0.0002, -0.0002, 0.0010, 87)))
RES.append(cell(path_mae_pairs(path, v15_ridge, 'D5', rkey='ridge_prediction'), 'ceiling_path_v0 D5 MAE − v1_5_h99', (-0.0360, -0.0579, -0.0176, 85)))
pI = {('D5', r['ticker']): dict(r, realized_return=rule_by['base_train_median'][('D5', r['ticker'])]['realized_return'], rule_return=r['D5_return']) for r in pathI if r['status'] == 'OK' and ('D5', r['ticker']) in rule_by['base_train_median']}
RES.append(cell(path_mae_pairs(path, pI, 'D5'), 'ceiling_path_v0 D5 MAE − ceiling_path_v0@INF', (-0.1033, -0.1462, -0.0628, 87)))
RES.append(cell(path_mae_pairs(path, v15_ridge, 'D10', rkey='ridge_prediction'), 'ceiling_path_v0 D10 MAE − v1_5_h99', (-0.0595, -0.1447, 0.0157, 85)))
RES.append(cell(path_brier_pairs(path, rule_by['base_rate'], 'D3'), 'ceiling_path_v0 D3 Brier − base_rate', (-0.0362, -0.0553, -0.0163, 86)))
RES.append(cell(path_brier_pairs(path, v15_logit, 'D10', rkey='logit_probability'), 'ceiling_path_v0 D10 Brier − v1_5_h99', (-0.0311, -0.0695, 0.0032, 79)))
# D1 beraberlik: |fark| < 0.001 ya da 0 sayısı
d1 = path_mae_pairs(path, rule_by['base_always_ceiling'], 'D1')
print('D1 beraberlik: bit-eşit 0:', sum(1 for _, a, b in d1 if a == b), ' |fark|<0.001:', sum(1 for _, a, b in d1 if abs(a - b) < 0.001), '/', len(d1), ' (kılavuz 84/87 şart ≥ 80)')
print('==== §4.6.6 pb_ceiling_path_v0')
RES.append(cell(path_mae_pairs(pbpath, rulesPB['base_train_median'], 'D5'), 'pb_ceiling_path_v0 D5 MAE − base_train_median__pb (keşif)', (-0.0479, -0.0838, -0.0113, 87)))
RES.append(cell(path_mae_pairs(pbpath, pbr, 'D5', rkey='ridge_prediction'), 'pb_ceiling_path_v0 D5 MAE − pb_v0', (-0.0124, -0.0391, 0.0162, None if False else len(path_mae_pairs(pbpath, pbr, 'D5', rkey='ridge_prediction')))))
pM = {('D5', r['ticker']): dict(realized_return=rule_by['base_train_median'][('D5', r['ticker'])]['realized_return'], rule_return=r['D5_return']) for r in path if r['status'] == 'OK' and ('D5', r['ticker']) in rule_by['base_train_median']}
pairs = path_mae_pairs(pbpath, pM, 'D5')
RES.append(cell(pairs, 'pb_ceiling_path_v0 D5 MAE − ceiling_path_v0 (bilgi)', (0.0728, 0.0421, 0.1088, len(pairs))))

# ---------- Faz 7 yakın dönem (v1 − v0, ftd ≥ 2024-01-01)
print('==== §4.7.4 v1 yakın dönem')
v1 = {k: rd(G7 / f'{k}_fold_ledger.csv') for k in ('ceiling_hazard_v1_clip', 'ceiling_hazard_v1_real', 'ceiling_hazard_v1_pooled', 'ceiling_hazard_v1_pooled@INF')}
NE = '2024-01-01'
for k, e in (('ceiling_hazard_v1_clip', (-0.0011, -0.0066, 0.0049, 78)), ('ceiling_hazard_v1_real', (0.0104, 0.0028, 0.0183, 78)),
             ('ceiling_hazard_v1_pooled', (0.0289, 0.0089, 0.0518, 78)), ('ceiling_hazard_v1_pooled@INF', (0.0547, 0.0287, 0.0806, 78))):
    r = cell(ceiling_pairs(v1[k], v0, start=NE), f'{k} RPS − ceiling_hazard_v0 (yakın dönem)', e)
    r['near_era_label'] = 'bozuyor' if r['lo'] > 0 else ('tolerans içinde' if r['hi'] <= 0.010 else 'belirsiz'); print('   etiket:', r['near_era_label']); RES.append(r)
RES.append(cell(ceiling_pairs(v1['ceiling_hazard_v1_real'], v1['ceiling_hazard_v1_clip'], start=NE), 'real − clip (deflasyon payı)', (0.0115, 0.0045, 0.0190, 78)))
RES.append(cell(ceiling_pairs(v1['ceiling_hazard_v1_pooled'], v1['ceiling_hazard_v1_real'], start=NE), 'pooled − real (havuz+rejim payı)', (0.0185, 0.0005, 0.0389, 78)))
for k, e in (('ceiling_hazard_v1_clip', (-0.0554, -0.0826, -0.0283, 78)), ('ceiling_hazard_v1_real', (-0.0439, -0.0692, -0.0170, 78)), ('ceiling_hazard_v1_pooled', (-0.0253, -0.0386, -0.0099, 78))):
    RES.append(cell(ceiling_pairs(v1[k], crules['base_km_expanding'], start=NE), f'{k} RPS − base_km_expanding (yakın dönem)', e))
for k in (1, 3, 5):
    RES.append(cell(ceiling_pairs(v1['ceiling_hazard_v1_pooled'], v0, f'brier{k}', start=NE), f'pooled Brier k={k} − v0 (yakın dönem)', None))

# ---------- Faz 7C yakın dönem (D10 Brier, kırpmasız)
print('==== §4.8.4 (C) yakın dönem')
fall = {k: rd(G7C / f'{k}_fold_ledger.csv') for k in ('fall_d10_v0_h99', 'fall_d10_v0_pooled', 'fall_d10_v0_addsale', 'fall_d10_v0_pooled@ZERO')}
def pup(r):
    if 'logit_status' in r: return float(r['logit_probability']) if r['logit_status'] == 'FIT_OK' else None
    return float(r['rule_p_up']) if r.get('rule_p_up') not in (None, '') else None
def fall_pairs(model_rows, other_rows, h='D10', start=NE):
    other = {r['ticker']: pup(r) for r in other_rows if r['horizon'] == h and pup(r) is not None}
    out = []
    for r in model_rows:
        if r['horizon'] != h: continue
        p = pup(r)
        if p is None or r['prediction_date'] < start or r['ticker'] not in other: continue
        y = int(r['realized_direction'])
        out.append((r['prediction_date'][:7], (p - y) ** 2, (other[r['ticker']] - y) ** 2))
    return out
r = cell(fall_pairs(fall['fall_d10_v0_pooled'], fall['fall_d10_v0_h99']), 'fall pooled − h99 D10 Brier (birincil, yakın dönem)', (-0.0058, -0.0340, 0.0219, 75))
r['near_era_label'] = 'bozuyor' if r['lo'] > 0 else ('tolerans içinde' if r['hi'] <= 0.008 else 'belirsiz'); print('   etiket:', r['near_era_label']); RES.append(r)
for k, e in (('fall_d10_v0_h99', (-0.0434, -0.0773, -0.0048, 75)), ('fall_d10_v0_pooled', (-0.0492, -0.0670, -0.0296, 75)), ('fall_d10_v0_addsale', (-0.0065, -0.0301, 0.0161, 76)), ('fall_d10_v0_pooled@ZERO', (-0.0043, -0.0162, 0.0080, 75))):
    RES.append(cell(fall_pairs(fall[k], rules0['base_rate']), f'{k} D10 Brier − base_rate (V1.5 planı ledger)', e))
for k, e in (('fall_d10_v0_h99', (-0.0055, -0.0228, 0.0154, 75)), ('fall_d10_v0_pooled', (-0.0113, -0.0465, 0.0281, 75)), ('fall_d10_v0_addsale', (0.0305, -0.0131, 0.0808, 76))):
    RES.append(cell(fall_pairs(fall[k], [r for r in v15 if r['logit_status'] == 'FIT_OK']), f'{k} D10 Brier − v1_5_h99', e))
RES.append(cell(fall_pairs(fall['fall_d10_v0_pooled'], fall['fall_d10_v0_pooled@ZERO']), 'fall pooled − pooled@ZERO D10 Brier', (-0.0449, -0.0629, -0.0262, 75)))

# ---------- (C) karşılaştırıcı kümesi: fall planı kendi taban oranı (94 arz; f3 ve ek satış dolu) ile yeniden
print('==== (C) base_rate, fall planının kendi eğitim kümesinden (94 arz, D10 seansı < T)')
tbl = rd(ROOT / 'data/training_table.csv')
sess = {}
for rr in rd(ROOT / 'data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv'):
    sess.setdefault(rr['ticker'], {})[int(rr['session_number'])] = rr['target_session_date']
fall_set = [t for t in tbl if t['total_demand_multiple'].strip() and t['additional_sale_shares'].strip()]
print('fall H99 kümesi n =', len(fall_set))
def own_base_rate(T, h='D10'):
    d = {'D10': 10, 'D5': 5}[h]
    ys = [int(t[f'Y_{h}']) for t in fall_set if sess[t['ticker']][d] < T]
    return sum(ys) / len(ys) if len(ys) >= 10 else None
for k in ('fall_d10_v0_h99', 'fall_d10_v0_pooled', 'fall_d10_v0_addsale'):
    pairs = []
    for rr in fall[k]:
        if rr['horizon'] != 'D10' or pup(rr) is None or rr['prediction_date'] < NE: continue
        br = own_base_rate(rr['prediction_date'])
        if br is None: continue
        y = int(rr['realized_direction']); pairs.append((rr['prediction_date'][:7], (pup(rr) - y) ** 2, (br - y) ** 2))
    RES.append(cell(pairs, f'{k} D10 Brier − base_rate(fall planı, 94 arz)', None))
# V1.5 planı base_rate ile fark örneği
diffs = []
for rr in rules0['base_rate']:
    if rr['horizon'] == 'D10' and rr['prediction_date'] >= NE:
        br = own_base_rate(rr['prediction_date'])
        if br is not None: diffs.append(abs(float(rr['rule_p_up']) - br))
print('V1.5-planı base_rate ile fall-planı base_rate |fark| (D10, yakın dönem): maks %.4f, ort %.4f, n=%d' % (max(diffs), sum(diffs) / len(diffs), len(diffs)))

json.dump(RES, open('/tmp/borsai_kitap_audit_2/s4_out.json', 'w'), ensure_ascii=False, indent=1)
n_cmp = sum(1 for r in RES if r.get('guide') is not None); n_ok = sum(1 for r in RES if r.get('guide_match_4dp'))
print(f'\nKILAVUZLA KARŞILAŞTIRILAN HÜCRE: {n_cmp}, 4 ondalıkta birebir: {n_ok}, uyuşmayan: {n_cmp - n_ok}')
for r in RES:
    if r.get('guide') is not None and not r.get('guide_match_4dp'): print('  UYUŞMAYAN:', r['label'], 'benim', round(r['diff'], 4), round(r['lo'], 4), round(r['hi'], 4), r['n'], 'kılavuz', r['guide'])

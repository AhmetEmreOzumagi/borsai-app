"""KITAP_AUDIT_2 Adım 6: model düzeyinde sızıntı. KLONDA çalışır (borsai = klonun paketi).
Kullanım: run <etiket> | mutate <T1,T2,...> | compare <önce> <sonra> <mutasyon-ticker'ları>
Her ailede iki fold: ilk skorlanabilir fold ve son arz (QUICK). Tur A: erken test arzlarının etiketi değiştirilir -> kendi fold'ları
bit-eşit kalmalı, QUICK'in fold'u (onlar eğitiminde) DEĞİŞMELİ (mutasyonun etkili olduğunun kanıtı). Tur B: yalnız QUICK değiştirilir ->
QUICK fold'ları bit-eşit kalmalı."""
import csv, hashlib, io, json, sys
from pathlib import Path
CLONE = Path('/tmp/borsai_kitap_audit_2/clone'); OUTD = Path('/tmp/borsai_kitap_audit_2')
sys.path.insert(0, str(CLONE))
import borsai
assert str(CLONE) in borsai.__file__, borsai.__file__
from borsai import backtest as bt, specs, data as dm, fit as fitmod, survival as sv
from borsai.provenance import identity_hash

LAST = 'QUICK'
KEYS_H = ['selected_lambda', 'gamma_g1', 'gamma_g2', 'gamma_g3', 'beta_f1', 'beta_f2', 'beta_f3', 'beta_pb1', 'beta_f1r', 'S_1', 'S_5', 'S_10', 'training_n_ipo', 'training_n_pp_rows', 'training_max_session_date', 'training_tickers_sha256']
KEYS_L = ['ridge_selected_alpha', 'ridge_prediction', 'logit_selected_C', 'logit_probability', 'training_n', 'training_tickers_sha256', 'target_session_date']
KEYS_F = ['logit_selected_C', 'logit_probability', 'logit_intercept', 'logit_coef', 'training_n', 'training_tickers_sha256', 'target_session_date']
GOLD = {'ceiling_hazard_v0': 'macos_golden_faz1b', 'pb_ceiling_v0': 'macos_golden_faz1b', 'v1_5_h99': 'macos_golden', 'pb_v0': 'macos_golden_faz1b',
        'ceiling_hazard_v1_clip': 'macos_golden_faz7', 'ceiling_hazard_v1_pooled': 'macos_golden_faz7', 'fall_d10_v0_h99': 'macos_golden_faz7c', 'fall_d10_v0_pooled': 'macos_golden_faz7c'}

def golden(mid):
    return list(csv.DictReader(open(CLONE / 'tests/reference' / GOLD[mid] / f'{mid}_fold_ledger.csv', encoding='utf-8-sig', newline='')))

def first_scorable(folds, pred=lambda f: True):
    return next(f for f in folds if f.status == bt.SCORABLE and pred(f))

def run_phase(label):
    out = {}; check = (label == 'before')
    ds = dm.load_dataset(); by = ds.by_ticker(); units = {r.ticker: sv.unit_of(r) for r in ds.rows}
    for mid, plan in (('ceiling_hazard_v0', specs.PLAN_CEILING), ('pb_ceiling_v0', specs.PLAN_PB_CEILING)):
        spec = specs.MODEL_SPECS[mid]; pb = dm.load_pb(ds) if plan == specs.PLAN_PB_CEILING else None
        folds = bt.plan_ceiling_folds(ds, plan, pb); fb = {f.test_ticker: f for f in folds}
        for f in (first_scorable(folds), fb[LAST]):
            t = f.test_ticker; assert f.status == bt.SCORABLE and t not in f.training
            maxd = max(units[j].session_dates[r.day - 1] for j in f.training for r in sv.pp_rows(units[j], f.cutoff_date))
            row = {**bt._ceiling_identity(f, by), **bt._run_hazard(spec, ds, [f], 1)[0]}
            out[f'{mid}|{t}'] = {k: row.get(k) for k in KEYS_H if k in row} | {'cutoff': f.cutoff_date, 'T': f.first_trading_date, 'max_label_session': maxd,
                                                                             'test_in_training': t in f.training, 'training': list(f.training), 'my_training_sha': identity_hash(f.training)}
    folds15 = bt.plan_folds(ds); fb = {(f.horizon, f.test_ticker): f for f in folds15}
    for f in (first_scorable(folds15, lambda f: f.horizon == 'D5'), fb[('D5', LAST)]):
        t = f.test_ticker; row = {**bt._fold_identity(f, by), **bt._run_v15(ds, [f], 1)[0]}; maxd = max(by[j].targets['D5'].session_date for j in f.training)
        out[f'v1_5_h99|D5|{t}'] = {k: row.get(k) for k in KEYS_L} | {'T': f.prediction_date, 'max_label_session': maxd, 'test_in_training': t in f.training, 'training': list(f.training), 'my_training_sha': identity_hash(f.training)}
    spec = specs.MODEL_SPECS['pb_v0']; pb = dm.load_pb(ds); foldsPB = bt.plan_folds_pb(ds, pb); fb = {(f.horizon, f.test_ticker): f for f in foldsPB}
    rawPB = fitmod.model_raw_features(spec, list(ds.rows))[0]
    for f in (first_scorable(foldsPB, lambda f: f.horizon == 'D5'), fb[('D5', LAST)]):
        t = f.test_ticker; row = {**bt._fold_identity_pb(f, by), **bt._run_linear(spec, ds, [f], 1, rawPB)[0]}; maxd = max(by[j].targets['D5'].session_date for j in f.training)
        out[f'pb_v0|D5|{t}'] = {k: row.get(k) for k in KEYS_L} | {'B': f.prediction_date, 'T': by[t].first_trading_date, 'max_label_session': maxd, 'test_in_training': t in f.training, 'training': list(f.training), 'my_training_sha': identity_hash(f.training)}
    for mid in ('ceiling_hazard_v1_clip', 'ceiling_hazard_v1_pooled'):
        spec = specs.FAZ7_MODEL_SPECS[mid]; dsv = bt.v1_dataset(mid); byv = dsv.by_ticker(); unitsv = {r.ticker: sv.unit_of(r) for r in dsv.rows}
        raw, tinfo = bt.v1_raw_features(spec, list(dsv.rows)); regime = bt.v1_regime(list(dsv.rows)) if 'regime' in spec else None
        folds = bt.v1_plan(mid, dsv, raw); fb = {f.test_ticker: f for f in folds}
        for f in (first_scorable(folds), fb[LAST]):
            t = f.test_ticker; assert t not in f.training
            maxd = max(unitsv[j].session_dates[r.day - 1] for j in f.training for r in sv.pp_rows(unitsv[j], f.cutoff_date))
            row = {**bt._v1_identity(f, byv, 'regime' in spec, tinfo), **bt._run_hazard_v1(spec, dsv, [f], 1, raw, regime)[0]}
            out[f'{mid}|{t}'] = {k: row.get(k) for k in KEYS_H if k in row} | {'n_oot_open': f.n_oot_open, 'cutoff': f.cutoff_date, 'T': f.first_trading_date, 'max_label_session': maxd,
                                                                             'test_in_training': t in f.training, 'training_h99': [x for x in f.training if x in by], 'my_training_sha': identity_hash(f.training)}
    for mid in ('fall_d10_v0_h99', 'fall_d10_v0_pooled'):
        spec = specs.FAZ7C_MODEL_SPECS[mid]; dsf = bt.fall_dataset(mid); byf = dsf.by_ticker(); add = dm.additional_sale_shares(dsf)
        rows = bt.fall_training_rows(spec, dsf, add, check=check); raw = bt.fall_raw_features(spec, rows, add)[0]
        folds = bt.plan_fall_folds(dsf, rows, raw, uses_f3=True); fb = {(f.horizon, f.test_ticker): f for f in folds}
        for f in (first_scorable(folds, lambda f: f.horizon == 'D10'), fb[('D10', LAST)]):
            t = f.test_ticker; assert t not in f.training
            row = {**bt._fall_identity(f, byf, raw, {}), **bt._run_fall(spec, dsf, [f], 1, raw)[0]}; maxd = max(byf[j].targets['D10'].session_date for j in f.training)
            out[f'{mid}|D10|{t}'] = {k: row.get(k) for k in KEYS_F} | {'n_oot_open': f.n_oot_open, 'T': f.prediction_date, 'max_label_session': maxd, 'test_in_training': t in f.training,
                                                                      'training_h99': [x for x in f.training if x in by], 'my_training_sha': identity_hash(f.training)}
    json.dump(out, open(OUTD / f's6_{label}.json', 'w'), indent=1, ensure_ascii=False, default=str)
    print(f'{label}: {len(out)} fold yazıldı:', list(out))

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mutate(tickers):
    def rewrite_table(path):
        text = Path(path).read_bytes().decode('utf-8'); rows = list(csv.DictReader(io.StringIO(text, newline=''))); cols = list(rows[0].keys()); changed = []
        for r in rows:
            if r['ticker'] in tickers:
                L = int(r['ceiling_streak_L']); nl = 2 if L != 2 else 5
                r['ceiling_streak_L'] = str(nl)
                for k in range(1, 11): r[f'ceiling_close_D{k}'] = '1' if k <= nl else '0'
                for h in ('D5', 'D10'): r[f'R_{h}'] = '-0.05'; r[f'Y_{h}'] = '0'
                changed.append((r['ticker'], L, nl))
        buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=cols, lineterminator='\n'); w.writeheader(); w.writerows(rows)
        Path(path).write_bytes(buf.getvalue().encode('utf-8')); return changed
    print('tablo mutasyonu (ticker, L_eski, L_yeni):', rewrite_table(CLONE / 'data/training_table.csv')); rewrite_table(CLONE / 'data/training_table_v2.csv')
    p = CLONE / 'data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv'
    text = p.read_bytes().decode('utf-8-sig'); rows = list(csv.DictReader(io.StringIO(text, newline=''))); cols = list(rows[0].keys())
    for r in rows:
        if r['ticker'] in tickers and r['horizon'] in ('D5', 'D10'): r['target_return'] = '-0.05'; r['above_ipo_flag'] = '0'
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=cols, lineterminator='\n'); w.writeheader(); w.writerows(rows); p.write_bytes(b'\xef\xbb\xbf' + buf.getvalue().encode('utf-8'))
    for vpath, tpath in (('data/data_version.json', 'data/training_table.csv'), ('data/data_version_v2.json', 'data/training_table_v2.csv')):
        vp = CLONE / vpath; v = json.loads(vp.read_text()); v['sha256'] = sha(CLONE / tpath); v['bytes'] = (CLONE / tpath).stat().st_size
        for s in v['sources']: s['sha256'] = sha(CLONE / s['path'])
        vp.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n')
    print('sürüm sha\'ları güncellendi')

def _num(x, y):
    try: return float(x) == float(y)
    except Exception: return str(x) == str(y)
def compare(b_label, a_label, mutated):
    before, after = json.load(open(OUTD / f's6_{b_label}.json')), json.load(open(OUTD / f's6_{a_label}.json'))
    print(f"\n### mutasyon: {sorted(mutated)}")
    print(f"{'fold':38s} {'test∉eğitim':>11s} {'maxEtiket<kesim':>15s} {'altın=önce':>10s} {'mutant∈eğitim':>13s} {'önce=sonra':>10s} {'planSha=ledger':>14s}  sonuç")
    for k in before:
        b, a = before[k], after[k]; mid = k.split('|')[0]; t = k.split('|')[-1]; g = golden(mid)
        h = 'D5' if '|D5|' in k else ('D10' if '|D10|' in k else None)
        grow = next((r for r in g if r['ticker'] == t and (h is None or r['horizon'] == h)), None)
        keys = [kk for kk in b if grow is not None and kk in grow and grow[kk] != '']
        gold_eq = grow is not None and all(_num(b[kk], grow[kk]) for kk in keys)
        skip = ('max_label_session', 'training', 'training_h99')
        same = all(str(b[kk]) == str(a[kk]) for kk in b if kk not in skip)
        tr = b.get('training', b.get('training_h99', [])); in_train = any(x in tr for x in mutated)
        cut = b.get('B', b['T']); own = t in mutated
        expect = 'KENDİ ETİKETİ: bit-eşit kalmalı' if own else ('eğitimde mutant: değişmeli' if in_train else 'bağımsız: bit-eşit kalmalı')
        verdict = ('OK' if same else 'SIZINTI?') if (own or not in_train) else ('OK' if not same else 'mutasyon etkisiz?')
        print(f"{k:38s} {str(not b['test_in_training']):>11s} {str(b['max_label_session'] < cut):>15s} {str(gold_eq):>10s} {str(in_train):>13s} {str(same):>10s} {str(b['my_training_sha'] == (grow or {}).get('training_tickers_sha256')):>14s}  {expect} -> {verdict}")
        if not same: print('   değişen:', {kk: (b[kk], a[kk]) for kk in b if str(b[kk]) != str(a[kk]) and kk not in skip})

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'run': run_phase(sys.argv[2])
    elif cmd == 'mutate': mutate(set(sys.argv[2].split(',')))
    elif cmd == 'compare': compare(sys.argv[2], sys.argv[3], set(sys.argv[4].split(',')))

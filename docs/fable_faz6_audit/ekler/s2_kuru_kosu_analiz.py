"""Kuru S2 koşusunun (klon /tmp/borsai_faz6_audit/clone; `python -m borsai.freeze --oot registry/oot/cohort_pre_h99.csv`) analizi: durum sayıları, NOT_APPLICABLE_REGIME hücreleri, karşılaştırıcılar, şema, 5 kayıtta bit-eşitlik."""
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from borsai import freeze as fz, registry as reg, predict as pr, predict_hazard as ph, predict_path as pth, predict_pb as ppb, predict_market20 as pm
from borsai.provenance import ROOT, sha256_file
assert str(ROOT).startswith('/private/tmp/borsai_faz6_audit/clone') or str(ROOT).startswith('/tmp/borsai_faz6_audit/clone'), ROOT
recs = {}
for p in sorted((ROOT/'registry/oot/records').rglob('*.json')):
    r = json.loads(p.read_text(encoding='utf-8')); recs[r['ticker']] = (p, r)
print('kayıt sayısı', len(recs), '| hücre toplamı', sum(len(r['models']) for _, r in recs.values()))
index = json.loads((ROOT/'models/INDEX.json').read_text())
ids = [e['model_id'] for e in index['models']]
print('INDEX model sayısı', len(ids))
assert all([c['model_id'] for c in r['models']] == ids for _, r in recs.values())
# durum sayıları model başına
st = collections.defaultdict(collections.Counter); ref = collections.defaultdict(collections.Counter); na = collections.defaultdict(collections.Counter)
open_st = collections.defaultdict(collections.Counter)
for t, (p, r) in recs.items():
    is_open = r['vault'] in ('OPEN', 'EXPOSED_ARCHIVE', 'EXPOSED_CODEX')
    for c in r['models']:
        st[c['model_id']][c['status']] += 1
        if is_open: open_st[c['model_id']][c['status']] += 1
        if c['status'] == 'REFUSED': ref[c['model_id']][c['refusal']['code']] += 1
        if c['status'] == 'NOT_APPLICABLE_REGIME': na[c['model_id']][c['not_applicable']['code']] += 1
print('\nmodel | PREDICTED/REFUSED/NA (135) | açık küme PREDICTED | ret kodları | NA kodları')
for m in ids:
    print(f"{m:24s} {st[m]['PREDICTED']:3d}/{st[m]['REFUSED']:3d}/{st[m]['NOT_APPLICABLE_REGIME']:2d} | {open_st[m]['PREDICTED']:3d} | {dict(ref[m])} | {dict(na[m])}")
# NA hücreleri doğru modellerde mi
bad = []
for t, (p, r) in recs.items():
    tags = r['regime_tags']; exp = reg.regime_not_applicable(tags)
    got = {c['model_id']: c['not_applicable']['code'] for c in r['models'] if c['status'] == 'NOT_APPLICABLE_REGIME'}
    if {k: v['code'] for k, v in exp.items()} != got: bad.append((t, exp, got))
    # bağımsız: MARGIN_NOT_10PCT -> 6 model; TICK -> 2 model
    exp2 = {}
    if tags.get('MARGIN_NOT_10PCT'): exp2.update({m: 'MARGIN_NOT_10PCT' for m in ('base_always_ceiling','ceiling_hazard_v0@INF','pb_ceiling_v0@INF','ceiling_path_v0@INF','ceiling_path_v0','pb_ceiling_path_v0')})
    if tags.get('TICK_TABLE_MISMATCH'):
        for m in ('ceiling_path_v0','pb_ceiling_path_v0'): exp2.setdefault(m, 'TICK_TABLE_MISMATCH')
    if exp2 != got: bad.append(('SPEC', t, exp2, got))
print('\nNA hücre eşleşmezliği:', bad)
print('NA taşıyan üye sayısı:', sum(1 for _, r in recs.values() if r['summary']['n_not_applicable_regime']))
# karşılaştırıcılar
notes = collections.Counter(); const_out = collections.defaultdict(set)
for t, (p, r) in recs.items():
    cells = {c['model_id']: c for c in r['models']}
    for rid, c in r['comparators'].items():
        notes[(rid, c['comparator_note'])] += 1
        assert c['output'] == cells[rid]['output'] and c['params_sha256'] == cells[rid]['params_sha256'] and c['status'] == cells[rid]['status']
        const_out[rid].add(json.dumps(c['output'], sort_keys=True))
print('\ncomparator_note sayıları:', dict(notes))
print('karşılaştırıcı çıktısı kayıtlar arasında kaç farklı değer alıyor:', {k: len(v) for k, v in const_out.items()})
# şema §5
need = ['schema_version','record_type','record_stage','scale','ticker','cohort_file_sha256','inputs_sha256','models_index','models','comparators','regime_tags','recorded_at_utc','code']
p0, r0 = next(iter(recs.values()))
print('\n§5 alanları var mı:', {k: k in r0 for k in need}, '| models_index anahtarları', list(r0['models_index']), '| code', list(r0['code']))
print('hücre anahtarları:', sorted(r0['models'][0]))
print('schema/stage/scale:', r0['schema_version'], r0['record_stage'], r0['scale'], '| cohort sha eşit:', r0['cohort_file_sha256'] == sha256_file(ROOT/'registry/oot/cohort_pre_h99.csv'))
print('inputs sha eşit:', all(r['inputs_sha256'] == sha256_file(ROOT/r['inputs']['path']) for _, r in recs.values()))
print('sonuç anahtarı var mı:', any(set(reg.json_keys(r)) & reg.OOT_OUTCOME_KEYS for _, r in recs.values()))
print('dosya adı içerik adresli:', all(p.name == fz.record_filename(p.read_bytes(), r['recorded_at_utc']) for p, r in recs.values()))
print('vault/regime_tags kohort satırından:', all(r['vault'] == r['cohort_row']['vault'] and r['regime_tags'] == reg.parse_regime_tags(r['cohort_row']['regime_tags']) for _, r in recs.values()))
print('market20 takvim C ve ref_date=ftd:', all(r['market20']['calendar'] == 'C' and r['market20']['ref_date'] == r['first_trading_date'] and r['market20']['refusal'] is None for _, r in recs.values()))
# 5 kayıtta bit-eşitlik: model_inputs -> doğrudan predict
import random
five = sorted(random.Random(20260925).sample(sorted(recs), 5))
params = {e['model_id']: (json.loads((ROOT/'models'/e['file']).read_bytes()), e) for e in index['models']}
neq = 0; ncmp = 0
for t in five:
    p, r = recs[t]
    inp = r['model_inputs']
    for c in r['models']:
        prm, e = params[c['model_id']]
        kind = fz.model_kind(prm)
        out = (ph.predict if kind in ('hazard','km') else pth.predict if kind == 'ceiling_path' else pm.predict if kind == 'market20' else ppb.predict if kind == 'pb' else pr.predict)(prm, inp)
        ncmp += 1
        same = (json.dumps(out, sort_keys=True) == json.dumps(c['output'], sort_keys=True)) and (out == c['output'])
        if not same: neq += 1; print('  FARK', t, c['model_id'])
        assert c['params_sha256'] == sha256_file(ROOT/'models'/e['file']) == e['sha256']
print(f'\n5 kayıt ({five}): {ncmp} hücre doğrudan predict ile karşılaştırıldı; eşit olmayan: {neq}')

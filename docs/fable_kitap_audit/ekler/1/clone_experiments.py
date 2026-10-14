"""Klonda: (a) build_training_table.py yeniden üretimi bayt-eşit mi; (b) build_tufe_csv --check; (c) load_dataset / load_dataset_v2 / load_pb geçer mi;
(d) 3 fold'da test arzının f3/f1 değerini değiştir: fit_preprocessing parametreleri bit-eşit kalmalı; (e) Takvim C yeniden üretimi bayt-eşit."""
import subprocess, sys, hashlib, json
from decimal import Decimal
from pathlib import Path
ROOT = Path("/tmp/borsai_kitap_audit_1/clone"); sys.path.insert(0, str(ROOT))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
out = []; P = lambda *a: out.append(" ".join(str(x) for x in a))
before = (sha(ROOT / "data/training_table.csv"), sha(ROOT / "data/data_version.json"))
r = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "data/build_training_table.py")], capture_output=True, text=True, cwd=ROOT)
after = (sha(ROOT / "data/training_table.csv"), sha(ROOT / "data/data_version.json"))
P("[ÖLÇTÜM] build_training_table.py klonda: rc", r.returncode, "| tablo bayt-eşit:", before[0] == after[0], "| data_version bayt-eşit:", before[1] == after[1], "|", r.stdout.strip()[:80])
r = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "data/build_training_table_v2.py"), "--check"], capture_output=True, text=True, cwd=ROOT)
P("[ÖLÇTÜM] build_training_table_v2.py --check: rc", r.returncode, (r.stdout + r.stderr).strip()[-160:])
r = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "data/raw/tuik/build_tufe_csv.py"), "--check"], capture_output=True, text=True, cwd=ROOT)
P("[ÖLÇTÜM] build_tufe_csv.py --check: rc", r.returncode, (r.stdout + r.stderr).strip()[-200:])
from borsai import data as bd, preprocess as pp, market20 as m20, features as ft
ds = bd.load_dataset(); P("[ÖLÇTÜM] load_dataset: n =", len(ds.rows), "through", ds.outcome_sessions_through, "dv sha", ds.data_version_sha256[:8])
ds2 = bd.load_dataset_v2(); P("[ÖLÇTÜM] load_dataset_v2: n =", len(ds2.rows), "| kohort:", {c: sum(r.cohort == c for r in ds2.rows) for c in ("H99", "OOT_OPEN")})
pb = bd.load_pb(ds); P("[ÖLÇTÜM] load_pb: n =", len(pb))
P("[ÖLÇTÜM] Takvim C: calendar_c_bytes() sha ==", hashlib.sha256(m20.calendar_c_bytes()).hexdigest() == m20.CALENDAR_C_SHA256)
# (d) ön işleme mutasyonu: walk-forward benzeri 3 fold (eğitim = target D5 tarihi < T(k) olan satırlar)
rows = list(ds.rows)
def raw(r):
    f = ft.compute_features(**r.feature_inputs()); return {"f1": f.f1, "f2": f.f2, "f3": f.f3, "f4": f.f4}
def fit(train, recipe):
    tr = {r.ticker: raw(r) for r in train}; fs = {r.ticker: r.total_demand_filter_status for r in train}
    return pp.fit_preprocessing(tr, fs, recipe=recipe)
def params_bits(fp):
    return json.dumps({"w": {k: [str(a), str(b)] for k, (a, b) in fp.winsor_exact.items()}, "med": {k: str(v) for k, v in fp.median_exact.items()},
                       "mean": {k: str(v) for k, v in fp.mean_dec.items()}, "std": {k: str(v) for k, v in fp.std_dec.items()}, "cols": fp.columns, "dropped": fp.dropped, "mode": fp.f3_filter_mode_after}, sort_keys=True)
for k_idx in (20, 55, 98):
    test = rows[k_idx]; T = test.first_trading_date
    train = [r for r in rows if r.targets["D5"].session_date < T]
    for name, recipe in (("V1_5", pp.V1_5_RECIPE), ("CEILING_V1_CLIP", pp.CEILING_V1_CLIP_RECIPE)):
        tr_rows = [r for r in train if not (name.startswith("CEILING") and r.inputs["total_demand_multiple"] is None)]
        fp0 = fit(tr_rows, recipe); b0 = params_bits(fp0)
        z0 = fp0.transform(raw(test) if test.inputs["total_demand_multiple"] is not None or name == "V1_5" else raw(rows[k_idx - 1]), test.total_demand_filter_status)
        # mutasyon: test arzının f3'ünü 1000, f1'ini 10 kat yap → eğitimde değil, parametreler değişmemeli
        mutated = dict(raw(test)); mutated["f3"] = Decimal("1000"); mutated["f1"] = mutated["f1"] * 10
        fp1 = fit(tr_rows, recipe); b1 = params_bits(fp1)
        # test satırı eğitimde mi?
        in_train = test.ticker in fp0.train_tickers
        z1 = fp1.transform(raw(test) if test.inputs["total_demand_multiple"] is not None or name == "V1_5" else raw(rows[k_idx - 1]), test.total_demand_filter_status)
        max_sess = max(r.session_dates[-1] for r in tr_rows) if name.startswith("CEILING") else max(r.targets["D5"].session_date for r in tr_rows)
        P(f"[ÖLÇTÜM] fold {test.ticker} T={T} {name}: n_train={fp0.n_train} test eğitimde={in_train} parametreler bit-eşit (test değeri değiştirilince)={b0 == b1} "
          f"z bit-eşit={z0['z'] == z1['z']} winsor_f3={[str(float(x))[:7] for x in fp0.winsor_exact.get('f3', ())]} max(eğitim D5/D10 seansı)={max_sess} < T={max_sess < T}")
Path("/tmp/borsai_kitap_audit_1/clone_experiments.out.txt").write_text("\n".join(out) + "\n"); print("\n".join(out))

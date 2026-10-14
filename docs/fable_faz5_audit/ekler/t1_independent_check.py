#!/usr/bin/env python3
"""T1 bağımsız denetimi (Fable): refactor'dan ÖNCEKİ paket (git archive 72a000f -> borsai_old) ile bugünkü paket (HEAD)
aynı girdilerde çalıştırılır; INDEX'teki bütün hazard/km modellerinin (6) predict çıktıları `==` ile karşılaştırılır.
Girdiler: H99'un 99 arzı (dataset), 7 resmi kaydın model_inputs'u, 300 tohumlu rastgele girdi, uç durumlar.
Ayrıca 7 kaydın saklı çıktıları bugünkü predict ile `==` karşılaştırılır. Opus'un anlık görüntüsü KULLANILMAZ."""
import json, random, sys
from decimal import Decimal
from pathlib import Path

ROOT = Path("/Users/ahmet/Desktop/BorsAi")
sys.path.insert(0, "/tmp/borsai_faz5_audit/old")
sys.path.insert(0, str(ROOT))
import borsai_old.predict_hazard as old   # noqa: E402  (72a000f)
import borsai.predict_hazard as new       # noqa: E402  (HEAD)
from borsai.data import load_dataset, load_pb  # noqa: E402

assert old.__file__.startswith("/tmp/borsai_faz5_audit/old") and new.__file__.startswith(str(ROOT))
index = json.loads((ROOT / "models" / "INDEX.json").read_text())
models = {}
for e in index["models"]:
    p = json.loads((ROOT / "models" / e["file"]).read_text())
    if p.get("algorithm") in ("discrete_time_hazard_logit_l2", "KM_EXPANDING", "KM_LAST10"):
        models[e["model_id"]] = p
print("hazard/km modelleri:", sorted(models))
ds = load_dataset()
pb = load_pb(ds)
FIELDS = ("ipo_price_tl", "shares_offered", "post_ipo_share_capital", "capital_increase_shares", "total_demand_multiple", "ipo_size_tl")
cases = []
for r in ds.rows:
    doc = {k: r.inputs[k] for k in FIELDS}
    doc["total_demand_filter_status"] = r.total_demand_filter_status
    doc.update(pb[r.ticker].fields)
    cases.append(("H99|" + r.ticker, doc))
for path in sorted((ROOT / "registry" / "records").rglob("*.json")):
    rec = json.loads(path.read_text())
    cases.append(("REC|" + path.name, rec["model_inputs"]))
rng = random.Random(4242)
base = [c for _, c in cases[:99]]
for i in range(300):
    doc = dict(rng.choice(base))
    for k in ("ipo_price_tl", "shares_offered", "total_demand_multiple", "ipo_size_tl"):
        if doc.get(k) is not None:
            doc[k] = str((Decimal(doc[k]) * Decimal(repr(rng.uniform(0.2, 4.0)))).quantize(Decimal("0.001")))
    if rng.random() < 0.1:
        doc["total_demand_multiple"] = None
    if rng.random() < 0.05:
        doc["shares_offered"] = "0"
    cases.append((f"RND|{i}", doc))
for name, change in {"f3_missing": {"total_demand_multiple": None}, "f3_high": {"total_demand_multiple": "999"}, "shares_zero": {"shares_offered": "0"},
                     "price_text": {"ipo_price_tl": "x"}, "size_none": {"ipo_size_tl": None}}.items():
    cases.append(("EDGE|" + name, {**base[0], **change}))


def run(mod, params, inputs):
    try:
        return mod.predict(params, inputs)
    except mod.PredictError as exc:
        return {"error": exc.code}


n = n_eq = 0
bad = []
for mid, params in models.items():
    for cid, inputs in cases:
        a, b = run(old, params, inputs), run(new, params, inputs)
        n += 1
        if a == b:
            n_eq += 1
        else:
            bad.append((mid, cid))
print(f"eski (72a000f) == yeni (HEAD): {n_eq}/{n} çıktı (6 model × {len(cases)} girdi); ret yolları dahil; uyuşmazlık: {bad[:5]}")
# 7 kaydın saklı çıktıları
m = m_eq = 0
for path in sorted((ROOT / "registry" / "records").rglob("*.json")):
    rec = json.loads(path.read_text())
    for cell in rec["models"]:
        if cell["kind"] in ("hazard", "km"):
            params = json.loads((ROOT / cell["file"]).read_text())
            m += 1
            m_eq += int(new.predict(params, rec["model_inputs"]) == cell["output"])
print(f"7 kaydın saklı hazard/km çıktıları == bugünkü predict: {m_eq}/{m}")
# linear_predictor yeni yardımcı: sigmoid(eta) == predict hazard (bit-eşit)
import borsai.survival as sv  # noqa: E402
k = k_eq = 0
for mid, params in models.items():
    if params.get("algorithm") != "discrete_time_hazard_logit_l2":
        continue
    for cid, inputs in cases:
        lp = new.linear_predictor(params, inputs)
        out = new.predict(params, inputs)
        k += 1
        k_eq += int(bool(lp["refused"] == out["refused"] and (out["refused"] or [sv.sigmoid(e) for e in lp["eta"]] == out["hazard"])))
print(f"linear_predictor -> sigmoid(eta) == predict hazard (4 hazard modeli): {k_eq}/{k}")
assert n_eq == n and m_eq == m and k_eq == k
print("T1 BAĞIMSIZ DENETİM: GEÇTİ")

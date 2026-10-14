"""Faz 1B dondurulmuş modeller: INDEX, JSON yapısı (şartnamelerdeki alanlar), yeniden
üretilebilirlik ve K3 (yeni predict yolları yalnız stdlib)."""
from __future__ import annotations

import ast
import json
import subprocess
import sys

import pytest

from borsai import survival as sv
from borsai.freeze import INDEX_PATH, MODELS_DIR, load_index
from borsai.provenance import ROOT, identity_hash, sha256_file
from borsai.specs import FAZ1B_MODEL_IDS, MODEL_SPECS, model_kind, spec_sha256

from faz1b_support import frozen, refit

VOLATILE = {"created_at", "code_version"}
STDLIB_ALLOWED = {"__future__", "math", "typing", "decimal", "dataclasses"}
PREDICT_MODULES = ("predict", "predict_market20", "predict_pb", "predict_hazard")


def test_index_has_the_nine_new_models_and_hashes():
    index = {e["model_id"]: e for e in load_index(INDEX_PATH)["models"]}
    assert set(FAZ1B_MODEL_IDS) <= set(index) and len(FAZ1B_MODEL_IDS) == 9
    for m in FAZ1B_MODEL_IDS:
        e = index[m]
        assert e["status"] == "FROZEN" and e["file"] == f"{m}.json" and sha256_file(MODELS_DIR / e["file"]) == e["sha256"]
        assert e["spec_sha256"] == spec_sha256(MODEL_SPECS[m])
        assert e["training_cutoff_date"] == "2026-08-19"
        assert e["training_n"] == (97 if MODEL_SPECS[m]["training"]["set"] == "H99_F3_PRESENT" else 99)


@pytest.mark.parametrize("model_id", FAZ1B_MODEL_IDS)
def test_refit_reproduces_frozen_parameters(model_id):
    fresh, _ = refit(model_id)
    old = frozen(model_id)
    assert {k: v for k, v in fresh.items() if k not in VOLATILE} == {k: v for k, v in old.items() if k not in VOLATILE}


@pytest.mark.parametrize("model_id", FAZ1B_MODEL_IDS)
def test_spec_document_recorded(model_id):
    params = frozen(model_id)
    doc = params["spec"]["spec_document"]
    assert sha256_file(ROOT / doc["path"]) == doc["sha256"]
    assert params["code_version"]["borsai_source_sha256"]


@pytest.mark.parametrize("model_id", ["ceiling_hazard_v0", "pb_ceiling_v0", "ceiling_hazard_v0@INF", "pb_ceiling_v0@INF"])
def test_hazard_json_fields(model_id, dataset):
    """SPEC_CEILING_V0 §12 'Model JSON ek alanları'."""
    p = frozen(model_id)
    assert p["algorithm"] == "discrete_time_hazard_logit_l2"
    assert p["day_groups"] == {"g1": [1], "g2": [2, 3], "g3": [4, 5, 6, 7, 8, 9, 10]}
    assert len(p["gamma"]) == 3 and set(p["beta"]) == set(p["features"])
    assert p["pseudo_rows"] == {"weight": 0.5}
    assert set(p["reclose_rates"]) == {"r_a", "r_b", "n_a", "a_a", "n_b", "a_b"}
    tr = p["training"]
    for key in ("tickers", "tickers_sha256", "n_ipo", "n_pp_rows", "n_events", "cutoff_date", "data_version_sha256"):
        assert key in tr
    assert tr["tickers_sha256"] == identity_hash(tr["tickers"])
    if model_id.startswith("ceiling"):
        assert (tr["n_ipo"], tr["n_pp_rows"], tr["n_events"]) == (97, 506, 83)
        assert not {"ALBTN", "ENDAE"} & set(tr["tickers"])
    else:
        assert (tr["n_ipo"], tr["n_pp_rows"], tr["n_events"]) == (99, 508, 85)
    if p["features"]:
        assert p["lambda"] in [0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, "INF"]
        assert [e["lambda"] for e in p["lambda_score_table"]] == [0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, "INF"]
        assert set(p["feature_ranges"]) == set(p["features"])
        assert p["preprocessing"]["columns"] == p["features"]
    else:
        assert p["lambda"] == "INF" and p["preprocessing"] is None and p["beta"] == {}
    # reclose oranları eğitim kümesinden yeniden hesaplanır
    rows = [r for r in dataset.rows if r.ticker in set(tr["tickers"])]
    assert p["reclose_rates"] == sv.reclose_counts([sv.unit_of(r) for r in rows])


def test_km_rule_json(dataset):
    units = [sv.unit_of(r) for r in dataset.rows]
    rows = sv.pp_table(units)
    for m, last_n in (("base_km_expanding", None), ("base_km_last10", 10)):
        p = frozen(m)
        assert p["survival"]["hazard"] == sv.km_hazards(rows, last_n=last_n)
        assert p["survival"]["S"] == sv.survival(p["survival"]["hazard"])
        assert p["training"]["n"] == 99
    assert frozen("base_km_expanding")["survival"]["hazard"][0] == 18 / 99


def test_linear_json_fields():
    v16 = frozen("v1_6_h99")
    for h in ("D1", "D3", "D5", "D10"):
        assert set(v16["horizons"][h]["p_up"]["inner_loocv_status"]) == {"ZERO", "0.0001", "0.001", "0.01", "0.1", "1.0", "10.0", "100.0"}
        assert set(v16["horizons"][h]["return"]["inner_loocv_mae"]) == {"0.001", "0.01", "0.1", "1.0", "10.0", "100.0", "1000.0",
                                                                          "10000.0", "INF"}
    m20 = frozen("v1_5_market20_v0")
    assert m20["preprocessing"]["columns"] == ["f1", "f2", "f3", "f4", "f5", "f6"] and "f6" in m20["feature_ranges"]
    assert "f6" not in m20["preprocessing"]["medians"] and len(m20["market20_training"]) == 99
    assert m20["spec"]["market20"]["sources"]["xu100"]["sha256"] == sha256_file(ROOT / m20["spec"]["market20"]["sources"]["xu100"]["path"])
    pb = frozen("pb_v0")
    assert pb["preprocessing"]["columns"] == ["pb1", "pb2", "pb3"] and pb["preprocessing"]["medians"] == {}
    assert set(pb["feature_ranges"]) == {"pb1", "pb2", "pb3"} and "pb4" in pb["feature_definitions"]
    src = pb["spec"]["sources"]["prebookbuild"]
    assert sha256_file(ROOT / src["path"]) == src["sha256"]


# ---------------------------------------------------------------- K3: yalnız stdlib

def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.module is None:  # from . import survival
                out |= {"." + a.name for a in node.names}
            else:
                out.add("." + (node.module or "") if node.level else node.module.split(".")[0])
    return out


def import_closure(module: str) -> dict[str, list[str]]:
    pkg = ROOT / "borsai"
    seen, queue, closure = set(), [module], {}
    while queue:
        mod = queue.pop()
        if mod in seen:
            continue
        seen.add(mod)
        imps = _imports(pkg / f"{mod}.py")
        closure[mod] = sorted(imps)
        queue += [i[1:] for i in imps if i.startswith(".")]
    return closure


@pytest.mark.parametrize("module", PREDICT_MODULES)
def test_k3_predict_import_closure_is_stdlib_only(module):
    closure = import_closure(module)
    external = {i for imps in closure.values() for i in imps if not i.startswith(".")}
    assert external <= STDLIB_ALLOWED, closure
    assert set(closure) <= {"predict", "predict_market20", "predict_pb", "predict_hazard", "features", "horizons", "survival"}


def test_k3_new_predict_paths_run_without_numpy():
    code = (
        "import json, sys\n"
        "import borsai.predict_hazard as ph, borsai.predict_pb as ppb, borsai.predict_market20 as pm, borsai.predict as pr\n"
        "load = lambda m: json.load(open(f'models/{m}.json', encoding='utf-8'))\n"
        "v15 = {'ipo_price_tl': '25.52', 'shares_offered': '87500000', 'post_ipo_share_capital': '312500000',"
        " 'capital_increase_shares': '62500000', 'total_demand_multiple': '2.84'}\n"
        "pbin = {'ipo_price_try': '76.60', 'planned_pre_ipo_capital': '433300000', 'planned_post_ipo_capital': '481612950',"
        " 'planned_capital_increase_shares': '48312950', 'planned_existing_share_sale': '0', 'planned_base_offer_shares': '48312950',"
        " 'planned_additional_sale_ceiling': '0', 'planned_max_offer_shares': '48312950'}\n"
        "assert pr.predict(load('v1_6_h99'), v15)['refused'] is None\n"
        "assert pm.predict(load('v1_5_market20_v0'), {**v15, 'f6_market20': '0.02'})['refused'] is None\n"
        "assert ppb.predict(load('pb_v0'), pbin)['refused'] is None\n"
        "for m in ('ceiling_hazard_v0', 'ceiling_hazard_v0@INF', 'base_km_expanding', 'base_km_last10'):\n"
        "    assert ph.predict(load(m), v15)['refused'] is None\n"
        "for m in ('pb_ceiling_v0', 'pb_ceiling_v0@INF'):\n"
        "    assert ph.predict(load(m), pbin)['refused'] is None\n"
        "print(json.dumps(sorted(m for m in sys.modules if m.split('.')[0] in "
        "('numpy', 'sklearn', 'scipy', 'joblib', 'threadpoolctl', 'narwhals'))))\n"
    )
    res = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert json.loads(res.stdout) == []


def test_model_kinds_cover_registry():
    kinds = {m: model_kind(m) for m in MODEL_SPECS}
    assert {m for m, k in kinds.items() if k == "hazard"} == {"ceiling_hazard_v0", "ceiling_hazard_v0@INF", "pb_ceiling_v0",
                                                              "pb_ceiling_v0@INF"}
    assert {m for m, k in kinds.items() if k == "km"} == {"base_km_expanding", "base_km_last10"}
    assert {m for m, k in kinds.items() if k == "linear"} == {"v1_5_h99", "v1_6_h99", "v1_5_market20_v0", "pb_v0"}

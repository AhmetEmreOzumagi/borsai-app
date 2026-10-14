"""Kabul testi 5 (predict paritesi, JSON <-> sklearn), 6 (training.tickers_sha256) ve K2 (predict yalnız stdlib)."""
from __future__ import annotations

import ast
import copy
import csv
import json
import subprocess
import sys

import numpy as np
import pytest

from borsai import predict as pr
from borsai.features import compute_features
from borsai.fit import fit_with_estimators
from borsai.horizons import HORIZONS, physical_return_bounds
from borsai.provenance import ROOT, identity_hash
from borsai.specs import V1_5_H99

from test_features import netgl_inputs

PROBE = json.loads((ROOT / "tests" / "reference" / "A_v1_5_probe_cikti.json").read_text(encoding="utf-8"))
NETGL_DIR = ROOT / "registry" / "legacy_frozen" / "NETGL_20260916_V1_5"
TOL = 1e-12
ZZTEST = {  # docs/checkup_20260921/araclar/probe_v1_5.py (eski repo): hayali arz
    "ipo_price_tl": "20.00", "shares_offered": "50000000", "post_ipo_share_capital": "250000000",
    "capital_increase_shares": "40000000", "total_demand_multiple": "5.5",
}


def _read(path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def frozen(frozen_models):
    return frozen_models["v1_5_h99"]


@pytest.fixture(scope="module")
def sk(dataset):
    """Aynı 99 arzla sklearn final modelleri (Decimal ön işleme + sklearn tahmini)."""
    return fit_with_estimators(V1_5_H99, list(dataset.rows), dataset_version=dataset.data_version_sha256)


INPUT_KEYS = ("ipo_price_tl", "shares_offered", "post_ipo_share_capital", "capital_increase_shares",
              "total_demand_multiple", "ipo_size_tl")


def sklearn_path(fits, h: str, inputs: dict) -> tuple[float, float]:
    """Legacy test-satırı yolu: kesin ön işleme (Decimal) + sklearn Ridge/Logit."""
    f = compute_features(**{k: inputs.get(k) for k in INPUT_KEYS})
    hf = fits[h]
    z = hf.final.transform(f.as_dict(), inputs.get("total_demand_filter_status"))["z"]
    x = np.array([[z[c] for c in hf.final.columns]], dtype=np.float64)
    return float(hf.ridge.estimator.predict(x)[0]), float(hf.logit.estimator.predict_proba(x)[0][1])


# ---------------------------------------------------------------- 5. parite

def test_5_netgl_matches_legacy_probe_and_frozen_registry(frozen):
    out = pr.predict(frozen, netgl_inputs())
    assert out["refused"] is None and out["warnings"] == []
    registry = {r["horizon"]: r for r in _read(NETGL_DIR / "NETGL_20260916_V1_5_frozen_prediction_ledger.csv")}
    for e in PROBE["netgl_replay_predictions"]:
        h = e["horizon"]
        heads = frozen["horizons"][h]
        assert heads["return"]["alpha"] == float(e["ridge_alpha"])
        assert heads["p_up"]["C"] == float(e["logistic_c"])
        for ref in (e, registry[h]):
            assert abs(out[h]["return"] - float(ref["ridge_predicted_return"])) <= TOL
            assert abs(out[h]["p_up"] - float(ref["p_up"])) <= TOL
            assert abs(out[h]["price"] - float(ref["ridge_predicted_price_tl"])) <= TOL
            assert out[h]["direction"] == ref["direction"]
        assert out[h]["return_clipped"] is None


def test_5_zztest_matches_legacy_probe(frozen):
    out = pr.predict(frozen, ZZTEST)
    assert out["refused"] is None
    for e in PROBE["manual_predictions"]:
        h = e["horizon"]
        assert frozen["horizons"][h]["return"]["alpha"] == float(e["ridge_alpha"])
        assert frozen["horizons"][h]["p_up"]["C"] == float(e["logistic_c"])
        assert abs(out[h]["return"] - float(e["ridge_predicted_return"])) <= TOL
        assert abs(out[h]["p_up"] - float(e["p_up"])) <= TOL
        assert abs(out[h]["price"] - float(e["ridge_predicted_price_tl"])) <= TOL


def test_5_all_99_training_rows_json_vs_sklearn(frozen, sk, dataset):
    """97 satır public predict ile; f3'süz ALBTN ve ENDAE predict'te RET, aynı matematik
    iç fonksiyonlarla (medyan + f5 = 1) sınanır."""
    _, fits = sk
    compared = refused = 0
    for i, row in enumerate(dataset.rows):
        inputs = {**row.feature_inputs(), "total_demand_filter_status": row.total_demand_filter_status}
        for h in HORIZONS:
            hf = fits[h]
            x = np.array([hf.final.matrix_rows([row.ticker])[0]], dtype=np.float64)
            r_sk = float(hf.ridge.estimator.predict(x)[0])
            p_sk = float(hf.logit.estimator.predict_proba(x)[0][1])
            if row.inputs["total_demand_multiple"] is None:
                out = pr.predict(frozen, inputs)
                assert out["refused"]["code"] == pr.REFUSED_F3_MISSING
                f = compute_features(**row.feature_inputs())
                feats = {k: (None if v is None else float(v)) for k, v in f.as_dict().items()}
                z = pr.z_vector(frozen["preprocessing"], feats)
                ret, p = pr.head_values(frozen["horizons"][h], z)
                refused += 1
            else:
                out = pr.predict(frozen, inputs)
                assert out["refused"] is None
                ret, p = out[h]["return_unclipped"], out[h]["p_up"]
                compared += 1
            assert abs(ret - r_sk) <= TOL, (row.ticker, h, ret, r_sk)
            assert abs(p - p_sk) <= TOL, (row.ticker, h, p, p_sk)
    assert compared == 97 * 4 and refused == 2 * 4


EDGE_CASES = {
    # ad: (girdi yaması, beklenen uyarı kodları, beklenen kırpma {ufuk: yön})
    "f3_below_p05": ({"total_demand_multiple": "1.01"}, {pr.WARN_F3_WINSORIZED}, {}),
    # Eğitim aralığı içindeki bir f3 bile D3'te fiziksel üst sınırı aşan doğrusal tahmin verir.
    "f3_above_p95": ({"total_demand_multiple": "12.5"}, {pr.WARN_F3_WINSORIZED, pr.WARN_RETURN_CLIPPED}, {"D3": "UPPER"}),
    "f4_zero": ({"capital_increase_shares": "0"}, {pr.WARN_OUT_OF_TRAINING_RANGE, pr.WARN_F4_ZERO}, {}),
    "f4_100": ({"capital_increase_shares": "87500000"}, set(), {}),
    "f1_out_of_range": ({"ipo_price_tl": "1000"}, {pr.WARN_OUT_OF_TRAINING_RANGE, pr.WARN_RETURN_CLIPPED}, {"D10": "LOWER"}),
    "return_above_physical_bound": (
        {"ipo_price_tl": "0.5", "shares_offered": "1000000", "post_ipo_share_capital": "1000000",
         "capital_increase_shares": "1000000", "total_demand_multiple": "12"},
        {pr.WARN_OUT_OF_TRAINING_RANGE, pr.WARN_F3_WINSORIZED, pr.WARN_RETURN_CLIPPED},
        {"D1": "UPPER", "D3": "UPPER", "D5": "UPPER", "D10": "UPPER"},
    ),
    "return_below_physical_bound": (
        {"ipo_price_tl": "100000", "shares_offered": "1000000", "post_ipo_share_capital": "200000000",
         "capital_increase_shares": "1000000", "total_demand_multiple": "1.01"},
        {pr.WARN_OUT_OF_TRAINING_RANGE, pr.WARN_F3_WINSORIZED, pr.WARN_RETURN_CLIPPED},
        {"D5": "LOWER", "D10": "LOWER"},
    ),
}


@pytest.mark.parametrize("name", list(EDGE_CASES))
def test_5_edge_vectors(name, frozen, sk):
    patch, warn_codes, clips = EDGE_CASES[name]
    _, fits = sk
    inputs = {**netgl_inputs(), **patch}
    out = pr.predict(frozen, inputs)
    assert out["refused"] is None
    assert {w["code"] for w in out["warnings"]} == warn_codes
    for h in HORIZONS:
        r_sk, p_sk = sklearn_path(fits, h, inputs)
        assert abs(out[h]["return_unclipped"] - r_sk) <= TOL, (name, h)
        assert abs(out[h]["p_up"] - p_sk) <= TOL, (name, h)
        lo, hi = physical_return_bounds(h)
        assert out[h]["return_clipped"] == clips.get(h)
        if h in clips:
            assert out[h]["return"] == (hi if clips[h] == "UPPER" else lo)
            assert out[h]["price"] == float(inputs["ipo_price_tl"]) * (1.0 + out[h]["return"])
        else:
            assert out[h]["return"] == out[h]["return_unclipped"]
    if name == "f4_zero":
        (w,) = [w for w in out["warnings"] if w["code"] == pr.WARN_F4_ZERO]
        assert "eğitimde" in w["message"]


def test_5_f3_missing_is_refused_with_reason(frozen):
    for missing in (None, "", "DATA_NOT_FOUND"):
        out = pr.predict(frozen, {**netgl_inputs(), "total_demand_multiple": missing})
        assert out["refused"]["code"] == pr.REFUSED_F3_MISSING
        assert "AUDIT §1.2-d" in out["refused"]["reason"]
        assert all(out[h] is None for h in HORIZONS)


def test_f3_filter_status_conflict_is_refused(frozen):
    assert frozen["preprocessing"]["f3_filter_mode"] == "NOT_SPECIFIED"
    assert pr.predict(frozen, {**netgl_inputs(), "total_demand_filter_status": "FILTERED"})["refused"] is None
    synthetic = copy.deepcopy(frozen)
    synthetic["preprocessing"]["f3_filter_mode"] = "UNFILTERED"
    out = pr.predict(synthetic, {**netgl_inputs(), "total_demand_filter_status": "FILTERED"})
    assert out["refused"]["code"] == pr.REFUSED_F3_FILTER_CONFLICT


@pytest.mark.parametrize(
    "patch, code",
    [
        ({"post_ipo_share_capital": "0"}, "DIVISION_BY_ZERO"),
        ({"shares_offered": "0"}, "DIVISION_BY_ZERO"),
        ({"ipo_price_tl": "0"}, "INPUT_NOT_POSITIVE"),
        ({"ipo_price_tl": "abc"}, "INPUT_NOT_NUMERIC"),
        ({"capital_increase_shares": None}, "INPUT_MISSING"),
        ({"capital_increase_shares": "-1"}, "INPUT_NEGATIVE"),
    ],
)
def test_bad_inputs_are_labeled_refusals(frozen, patch, code):
    out = pr.predict(frozen, {**netgl_inputs(), **patch})
    assert out["refused"]["code"] == code


def test_bad_params_raise_labeled_error(frozen):
    for mutate, code in (
        (lambda p: p.update(schema_version="borsai.model/999"), "SCHEMA_UNSUPPORTED"),
        (lambda p: p["horizons"]["D1"]["return"]["coef"].pop(), "PARAMS_INVALID"),
        (lambda p: p["horizons"]["D1"]["p_up"].update(kind="tree"), "PARAMS_INVALID"),
    ):
        broken = copy.deepcopy(frozen)
        mutate(broken)
        with pytest.raises(pr.PredictError) as exc:
            pr.predict(broken, netgl_inputs())
        assert exc.value.code == code


def test_rule_models_predict(frozen_models):
    inputs = {**netgl_inputs(), "total_demand_multiple": None}
    for model_id in ("base_always_ceiling", "base_train_median", "base_train_mean", "base_zero", "base_rate", "base_last10_rate"):
        params = frozen_models[model_id]
        out = pr.predict(params, inputs)
        assert out["refused"] is None and out["warnings"] == []
        for h in HORIZONS:
            heads = params["horizons"][h]
            if heads["return"] is None:
                assert out[h]["return"] is None
            else:
                assert out[h]["return"] == heads["return"]["value"] and out[h]["return_clipped"] is None
            assert out[h]["p_up"] == (None if heads["p_up"] is None else heads["p_up"]["value"])
    ceiling = pr.predict(frozen_models["base_always_ceiling"], inputs)
    assert [ceiling[h]["return"] for h in HORIZONS] == [physical_return_bounds(h)[1] for h in HORIZONS]
    assert pr.predict(frozen_models["base_zero"], {"ipo_price_tl": "10"})["D1"]["price"] == 10.0


# ---------------------------------------------------------------- 6. training.tickers_sha256

def test_6_training_tickers_sha256(frozen, dataset):
    tr = frozen["training"]
    assert tr["n"] == 99 and tr["tickers"] == list(dataset.tickers)
    assert tr["tickers_sha256"] == identity_hash(tr["tickers"]) == identity_hash(dataset.tickers)
    # NETGL paritesi yalnız eğitim kümeleri aynı olduğu için tutar (AUDIT §3a-6).
    eligibility = {r["horizon"]: r for r in _read(NETGL_DIR / "NETGL_20260916_V1_5_training_eligibility_summary.csv")}
    for h in HORIZONS:
        assert eligibility[h]["training_n"] == "99"
        assert eligibility[h]["training_tickers_sha256"] == tr["tickers_sha256"]
        assert eligibility[h]["training_targets_sha256"] == tr["targets_sha256"][h]


# ---------------------------------------------------------------- K2: yalnız stdlib

STDLIB_ALLOWED = {"__future__", "math", "typing", "decimal", "dataclasses"}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            out.add("." + (node.module or "") if node.level else node.module.split(".")[0])
    return out


def test_k2_predict_import_list_is_stdlib_only():
    pkg = ROOT / "borsai"
    seen, queue, closure = set(), ["predict"], {}
    while queue:
        mod = queue.pop()
        if mod in seen:
            continue
        seen.add(mod)
        imps = _imports(pkg / f"{mod}.py")
        closure[mod] = sorted(imps)
        queue += [i[1:] for i in imps if i.startswith(".")]
    external = {i for imps in closure.values() for i in imps if not i.startswith(".")}
    assert external <= STDLIB_ALLOWED, closure
    assert set(closure) == {"predict", "features", "horizons"}
    assert _imports(pkg / "__init__.py") == set()


def test_k2_predict_runs_without_numpy_or_sklearn():
    code = (
        "import json, sys\n"
        "import borsai.predict as p\n"
        "params = json.load(open('models/v1_5_h99.json', encoding='utf-8'))\n"
        "out = p.predict(params, {'ipo_price_tl': '25.52', 'shares_offered': '87500000', 'post_ipo_share_capital': '312500000',"
        " 'capital_increase_shares': '62500000', 'total_demand_multiple': '2.84'})\n"
        "assert out['refused'] is None\n"
        "print(json.dumps(sorted(m for m in sys.modules if m.split('.')[0] in "
        "('numpy', 'sklearn', 'scipy', 'joblib', 'threadpoolctl', 'narwhals'))))\n"
    )
    res = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert json.loads(res.stdout) == []

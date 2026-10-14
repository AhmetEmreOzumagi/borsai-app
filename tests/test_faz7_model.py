"""Faz 7 model kodu (SPEC_HAZARD_V1 §3, §4, §9, §11-4, §11-6, §11-10, §11-11). Commit A: gerçek veride walk-forward ya da nihai
fit sonucu yok; model davranışı sentetik veriyle, veri istatistikleri (kırpma sınırları) ve dondurulmuş karşılaştırıcılar gerçek
veriyle sınanır. Gerçek nihai fit isteyen sürümler tests/test_faz7_golden.py'de (commit B)."""
from __future__ import annotations

import json
import subprocess
import sys
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest

from borsai import backtest as bt
from borsai import hazard as hz
from borsai import predict_hazard as ph
from borsai import preprocess as pp
from borsai import registry as reg
from borsai import survival as sv
from borsai.data import load_dataset
from borsai.features import compute_features
from borsai.provenance import ROOT, pretty_json_bytes
from borsai.specs import FAZ7_MODEL_IDS, FAZ7_MODEL_SPECS

import faz7_support as f7

CLIP, REAL, POOLED, POOLED_INF = FAZ7_MODEL_IDS


@pytest.fixture(scope="module")
def h99_f3_rows():
    rows = [r for r in load_dataset().rows if r.inputs["total_demand_multiple"] is not None]
    assert len(rows) == 97
    return rows


def _raw(spec_id, rows):
    return bt.v1_raw_features(FAZ7_MODEL_SPECS[spec_id], rows)[0]


def test_recipes_old_defaults_and_new_fields():
    for r in (pp.V1_5_RECIPE, pp.MARKET20_RECIPE, pp.CEILING_RECIPE, pp.PB_RECIPE, pp.PB_CEILING_RECIPE):
        assert r.winsor == ("f3",) and r.log == ("f1",)
    assert pp.CEILING_V1_CLIP_RECIPE.winsor == ("f1", "f2", "f3") and pp.CEILING_V1_CLIP_RECIPE.log == ("f1",)
    assert pp.CEILING_V1_REAL_RECIPE.features == ("f1r", "f2", "f3") and pp.CEILING_V1_REAL_RECIPE.winsor == ("f1r", "f2", "f3")
    assert pp.CEILING_V1_REAL_RECIPE.log == ("f1r",)
    for m in (CLIP, REAL, POOLED):
        assert bt.fitmod.recipe_for(FAZ7_MODEL_SPECS[m]).winsor == tuple(FAZ7_MODEL_SPECS[m]["preprocessing_winsor"])


@pytest.mark.parametrize("model_id", [CLIP, REAL])
def test_winsor_bounds_are_training_type7_p05_p95_of_raw_values(model_id, h99_f3_rows):
    """§11-4: kırpma sınırları eğitim arzlarının HAM değerlerinin (f1/f1r log öncesi TL) Type-7 p05/p95'i (kesin Fraction)."""
    raw = _raw(model_id, h99_f3_rows)
    recipe = bt.fitmod.recipe_for(FAZ7_MODEL_SPECS[model_id])
    prep = pp.fit_preprocessing(raw, {r.ticker: r.total_demand_filter_status for r in h99_f3_rows}, recipe=recipe)
    assert set(prep.winsor_exact) == set(recipe.features)
    for f in recipe.features:
        vals = sorted(Fraction(raw[t][f]) for t in raw)
        assert prep.winsor_exact[f] == (pp.quantile_type7(vals, Fraction(1, 20)), pp.quantile_type7(vals, Fraction(19, 20))), f
    first = recipe.features[0]
    assert prep.winsor_exact[first][0] > 10 ** 7                                  # TL (2025 TL), log değil
    assert prep.params()["log_transform"] == [first] and prep.log_features == (first,)


def _v1_params(model_id, prep, raw, *, delta=None):
    """Elle verilmiş sabit katsayılarla v1 parametre sözlüğü (gerçek fit yok; §11-4 ve ret yolları için)."""
    spec = FAZ7_MODEL_SPECS[model_id]
    feats = list(spec["features"])
    beta = dict(zip(feats, (0.12, 0.05, -0.21)))
    p = {"schema_version": "borsai.model/1", "model_id": model_id, "algorithm": ph.HAZARD_ALGORITHM, "family": ph.FAMILY_V1,
         "variant": spec["variant"], "features": feats, "day_groups": spec["day_groups"], "gamma": [-1.5, -2.1, -1.4],
         "beta": beta if feats else {}, "preprocessing": prep.params() if prep else None,
         "feature_ranges": bt.fitmod.feature_ranges(raw, feats) if feats else {},
         "reclose_rates": {"r_a": 0.02, "r_b": 0.14}}
    if "deflator" in spec:
        p["deflator"] = dict(spec["deflator"])
    if "regime" in spec:
        p["regime"] = {**spec["regime"], "delta": 0.4 if delta is None else delta}
    return p


def test_clip_input_at_half_p05_gives_same_z_as_p05_and_flags(h99_f3_rows):
    """§11-4: f1 = p05'in yarısı olan girdi ile f1 = p05 girdisi aynı z'yi verir; clipped_features = ["f1"]; uyarı kodu ve used."""
    raw = _raw(CLIP, h99_f3_rows)
    prep = pp.fit_preprocessing(raw, {t: None for t in raw}, recipe=pp.CEILING_V1_CLIP_RECIPE)
    lo, hi = prep.winsor_exact["f1"]
    base = h99_f3_rows[40]
    f = compute_features(**base.feature_inputs())
    mid = {"f2": f.f2, "f3": Decimal("5")}
    assert all(prep.winsor_exact[k][0] <= Fraction(v) <= prep.winsor_exact[k][1] for k, v in mid.items())
    half = Decimal(lo.numerator) / Decimal(lo.denominator) / 2
    at = Decimal(lo.numerator) / Decimal(lo.denominator)
    t_half = prep.transform({"f1": half, **mid}, None)
    t_at = prep.transform({"f1": lo, **mid}, None)
    assert t_half["z"] == t_at["z"] and t_half["winsorized"] == {"f1": True, "f2": False, "f3": False}
    assert t_at["winsorized"]["f1"] is False and t_half["f3_winsorized"] is False
    params = json.loads(pretty_json_bytes(_v1_params(CLIP, prep, raw)))
    inputs = {**base.feature_inputs(), "ipo_size_tl": str(half), "total_demand_multiple": "5"}
    out = ph.predict(params, inputs)
    assert out["refused"] is None and out["clipped"] is True and out["clipped_features"] == ["f1"]
    w = [x for x in out["warnings"] if x["code"] == ph.WARN_FEATURE_CLIPPED]
    assert len(w) == 1 and w[0]["feature"] == "f1" and w[0]["value"] == float(half) and w[0]["used"] == params["preprocessing"]["winsor"]["f1"]["p05"]
    assert any(x["code"] == ph.WARN_OUT_OF_TRAINING_RANGE and x["feature"] == "f1" for x in out["warnings"])   # bilgi: ham değer
    out_at = ph.predict(params, {**inputs, "ipo_size_tl": str(at)})
    assert out_at["clipped_features"] == [] and out_at["clipped"] is False
    assert max(abs(a - b) for a, b in zip(out["S"], out_at["S"])) <= 1e-12


def test_v0_outputs_keep_their_keys_and_f3_code():
    v0 = json.loads((ROOT / "models" / "ceiling_hazard_v0.json").read_text(encoding="utf-8"))
    inputs = {"ipo_price_tl": "25.52", "shares_offered": "87500000", "post_ipo_share_capital": "312500000",
              "capital_increase_shares": "62500000", "total_demand_multiple": "250", "ipo_size_tl": "2233000000"}
    out = ph.predict(v0, inputs)
    assert list(out) == ["model_id", "hazard", "S", "P_L", "P_close_ceiling", "clipped", "warnings", "refused"]
    assert out["clipped"] is True and [x["code"] for x in out["warnings"] if "CLIPPED" in x["code"]] == [ph.WARN_F3_CLIPPED]
    lp = ph.linear_predictor(v0, inputs)
    assert list(lp) == ["model_id", "refused", "warnings", "clipped", "z", "lin", "eta"]


def _synthetic_pp(seed=3, n=240, regime_effect=0.8):
    rng = np.random.default_rng(seed)
    groups, events, Z, R = [], [], [], []
    for i in range(n):
        r = 1.0 if i < n // 2 else 0.0
        z = rng.normal(size=3)
        for d in range(1, 11):
            g = sv.GROUP_OF_DAY[d]
            eta = [-1.6, -2.2, -1.4][g] + regime_effect * r + 0.4 * z[0] - 0.3 * z[2]
            e = float(rng.random() < 1 / (1 + np.exp(-eta)))
            groups.append(g), events.append(e), Z.append(z), R.append([r])
            if e:
                break
    return np.array(groups, dtype=np.intp), np.array(Z), np.array(events), np.array(R)


def test_regime_lambda_1e9_equals_inf_newton_and_beta_vanishes():
    """§11-6 (sentetik; gerçek veride tests/test_faz7_golden.py): λ = 1e9 ile ‖β‖ ≤ 1e-6, |δ| > 1e-3 ve (γ, δ) λ = INF Newton
    çözümüne |Δ| ≤ 1e-6; INF'te β ≡ 0 ve çözücü yakınsar."""
    g, Z, e, R = _synthetic_pp()
    big = hz.fit_rows(g, Z, e, 1e9, ("a", "b", "c"), R=R, r_columns=("r_pre_equal",))
    inf = hz.fit_rows(g, Z, e, hz.INF, ("a", "b", "c"), R=R, r_columns=("r_pre_equal",))
    assert big.status == inf.status == hz.CONVERGED and inf.grad_max <= hz.GRAD_TOL
    assert float(np.linalg.norm(big.beta)) <= 1e-6 and not inf.beta.any() and abs(big.delta[0]) > 1e-3
    assert max(abs(a - b) for a, b in zip(np.concatenate([big.gamma, big.delta]), np.concatenate([inf.gamma, inf.delta]))) <= 1e-6
    # r yokken INF kapalı biçim (v0) ile r varken INF Newton farklı yollar; r ≡ 0 ise aynı γ'yı verirler
    zero = hz.fit_rows(g, Z, e, hz.INF, ("a", "b", "c"), R=np.zeros_like(R), r_columns=("r_pre_equal",))
    closed = hz.fit_rows(g, Z, e, hz.INF, ("a", "b", "c"))
    assert max(abs(a - b) for a, b in zip(zero.gamma, closed.gamma)) <= 1e-9 and abs(zero.delta[0]) <= 1e-9


def test_newton_with_unpenalized_column_matches_scipy():
    """SPEC_CEILING_V0 §13-6 kalıbı: pseudo-satırsız, λ > 0, R cezasız; BFGS ile |Δ| ≤ 1e-6 ve ‖∇‖ ≤ 1e-10."""
    from scipy.optimize import minimize

    g, Z, e, R = _synthetic_pp(seed=9, n=160)
    lam = 3.0
    fit = hz.fit_rows(g, Z, e, lam, ("a", "b", "c"), pseudo=False, R=R, r_columns=("r",))
    X = hz.design(g, Z, R)
    w = np.ones(len(e))
    res = minimize(lambda th: hz.objective(X, e, w, th, lam, 4), np.zeros(7), method="BFGS", options={"gtol": 1e-12, "maxiter": 10000})
    theta = np.concatenate([fit.gamma, fit.delta, fit.beta])
    assert fit.status == hz.CONVERGED and fit.grad_max <= 1e-10 and np.max(np.abs(theta - res.x)) <= 1e-6
    assert hz.objective(X, e, w, theta, lam, 4) <= hz.objective(X, e, w, np.concatenate([theta[:4], np.zeros(3)]), lam, 4)


def test_v0_solver_path_unchanged_without_regime():
    g, Z, e, _ = _synthetic_pp(seed=4, n=120)
    a = hz.fit_rows(g, Z, e, 30.0, ("a", "b", "c"))
    b = hz.fit_rows(g, Z, e, 30.0, ("a", "b", "c"), R=None)
    assert np.array_equal(a.gamma, b.gamma) and np.array_equal(a.beta, b.beta) and a.delta.size == 0 and a.r_columns == ()
    assert np.array_equal(hz.design(g, Z), hz.design(g, Z, None)) and np.array_equal(hz.row_nll(a, g, Z, e), hz.row_nll(a, g, Z, e, None))


def test_regime_values_live_and_oot_inputs():
    assert set(ph.REGIME_R) == set(reg.REGIME_VALUES["ALLOC_REGIME"]) and ph.REGIME_R[ph.EQUAL_DIST] == 0
    assert ph.regime_value("PRE_20211111") == ph.regime_value("THRESH100_20211111") == 1
    ds = f7.synthetic_dataset(seed=21, tag="syn_reg")
    params, res = bt.final_fit_v1(POOLED_INF, ds, spec=f7.synthetic_spec(POOLED_INF, ds))
    params = json.loads(pretty_json_bytes(params))
    live = ph.predict(params, {})
    assert live["refused"] is None and live["regime_value_used"] == 0 and live["regime_source"] == ph.REGIME_SOURCE_LIVE
    for label, r in (("PRE_20211111", 1), ("THRESH100_20211111", 1), ("EQUAL_DIST_20230330", 0)):
        out = ph.predict(params, {"alloc_regime": label})
        assert out["regime_value_used"] == r and out["regime_source"] == ph.REGIME_SOURCE_INPUT
    assert ph.predict(params, {"alloc_regime": "EQUAL_DIST_20230330"})["S"] == live["S"]
    for bad in ("", None, "PRE"):
        assert ph.predict(params, {"alloc_regime": bad})["refused"]["code"] == ph.REFUSED_REGIME_UNKNOWN
    h99_row = next(r for r in ds.rows if r.cohort == "H99")
    import dataclasses

    with pytest.raises(bt.BacktestStop):
        bt.v1_regime([dataclasses.replace(h99_row, alloc_regime="PRE_20211111")])


def test_tufe_refusals_in_predict(h99_f3_rows):
    raw = _raw(REAL, h99_f3_rows)
    prep = pp.fit_preprocessing(raw, {t: None for t in raw}, recipe=pp.CEILING_V1_REAL_RECIPE)
    params = json.loads(pretty_json_bytes(_v1_params(REAL, prep, raw)))
    inputs = h99_f3_rows[10].feature_inputs()
    assert ph.predict(params, inputs)["refused"]["code"] == ph.REFUSED_TUFE_MISSING
    for code in (ph.REFUSED_TUFE_NOT_PIT, ph.REFUSED_TUFE_FILE_MISMATCH, ph.REFUSED_TUFE_MISSING):
        out = ph.predict(params, {**inputs, "tufe_index": "120.5", "tufe_refusal": code})
        assert out["refused"]["code"] == code and out["refused"]["field"] == "tufe_index" and out["S"] is None
    assert ph.predict(params, {**inputs, "tufe_index": "abc"})["refused"]["code"] == ph.REFUSED_TUFE_MISSING
    assert ph.predict(params, {**inputs, "tufe_index": "-3"})["refused"]["code"] == ph.REFUSED_TUFE_MISSING
    ok = ph.predict(params, {**inputs, "tufe_index": "120.5"})
    assert ok["refused"] is None and ok["tufe_index_used"] == "120.5"
    assert ok["f1r_raw"] == float(ph.real_size(compute_features(**inputs).f1, "120.5"))
    assert ph.predict(params, {**inputs, "total_demand_multiple": None, "tufe_index": "120.5"})["refused"]["code"] == "F3_MISSING"


def test_f3_filter_exclusion_rule():
    raw = {t: {"f3": Decimal("2")} for t in "ABCDEFG"}
    st = {"A": "UNFILTERED", "B": "UNFILTERED", "C": "UNFILTERED", "D": "NOT_SPECIFIED", "E": "NOT_SPECIFIED", "F": "FILTERED",
          "G": None}
    assert hz.f3_filter_excluded(list(raw), raw, st) == ("F",)
    st2 = {**st, "D": "NOT_SPECIFIED", "E": "NOT_SPECIFIED", "G": "NOT_SPECIFIED", "A": "NOT_SPECIFIED"}
    assert hz.f3_filter_excluded(list(raw), raw, st2) == ()                        # mod NOT_SPECIFIED (açık değil)
    assert hz.f3_filter_excluded(list(raw), {t: {} for t in raw}, st) == ()        # f3 kullanmayan küme (PB, @INF)
    ds = f7.synthetic_dataset(seed=5, tag="syn_filter")
    spec = FAZ7_MODEL_SPECS[POOLED]
    raw_all = bt.v1_raw_features(spec, list(ds.rows))[0]
    folds = bt.plan_pooled_folds(ds, raw_all)
    excl = [f for f in folds if f.filter_excluded]
    assert excl and all(set(f.filter_excluded).isdisjoint(f.training) for f in excl)
    status = {r.ticker: r.total_demand_filter_status for r in ds.rows}
    for f in folds:
        cand = [r.ticker for r in ds.rows if r.inputs["total_demand_multiple"] is not None and r.first_trading_date < f.cutoff_date]
        assert set(hz.f3_filter_excluded(cand, raw_all, status)) == set(f.filter_excluded)
        assert hz.f3_filter_excluded(list(f.training), raw_all, status) == ()   # dışlama sonrası mod değişmez, yeni boşalma yok


@pytest.mark.parametrize("model_id", list(FAZ7_MODEL_IDS))
def test_json_params_predict_parity_synthetic(model_id):
    """§11-11 (sentetik; gerçek eğitim arzlarında tests/test_faz7_golden.py): nihai fit fonksiyonunun JSON'u stdlib predict ile numpy
    fit'inin tahminini |Δ| ≤ 1e-12 verir."""
    ds = f7.synthetic_dataset(n_oot=16 if "pooled" in model_id else 0, n_h99=34, seed=31, tag="syn_parity")
    params, res = bt.final_fit_v1(model_id, ds, spec=f7.synthetic_spec(model_id, ds))
    params = json.loads(pretty_json_bytes(params))
    assert params["family"] == "ceiling_hazard_v1" and params["spec_sha256"] and params["variant"] == FAZ7_MODEL_SPECS[model_id]["variant"]
    worst, n = 0.0, 0
    for r in ds.rows:
        if r.inputs["total_demand_multiple"] is None or r.ticker in res.excluded:
            continue
        inputs = dict(r.inputs)
        if "deflator" in params:
            inputs["tufe_index"] = r.tufe_index
        if "regime" in params and r.cohort != "H99":
            inputs["alloc_regime"] = r.alloc_regime
        out = ph.predict(params, inputs)
        raw = bt.v1_raw_features(FAZ7_MODEL_SPECS[model_id], [r])[0][r.ticker] if params["features"] else {}
        test_r = {bt.REGIME_COLUMN: float(ph.regime_value(r.alloc_regime))} if "regime" in params else None
        num = res.predict(raw, r.total_demand_filter_status, test_r)
        for a, b in (("hazard", "hazards"), ("S", "S"), ("P_L", "P_L"), ("P_close_ceiling", "P_close")):
            worst = max(worst, max(abs(x - y) for x, y in zip(out[a], num[b])))
        n += 1
    assert n >= 30 and worst <= 1e-12


@pytest.mark.parametrize("model_id", [CLIP, REAL])
def test_clip_and_real_at_inf_bit_equal_frozen_v0_at_inf(model_id, h99_f3_rows):
    """§11-11: v1_clip@INF ve v1_real@INF iç hesapları dondurulmuş ceiling_hazard_v0@INF JSON'uyla bit-eşit (bu yüzden kayıtlı
    değil): aynı 97 arz, özelliksiz uç, γ kapalı biçim."""
    frozen = json.loads((ROOT / "models" / "ceiling_hazard_v0@INF.json").read_text(encoding="utf-8"))
    spec = FAZ7_MODEL_SPECS[model_id]
    raw = _raw(model_id, h99_f3_rows)
    res = hz.fit_training_set([sv.unit_of(r) for r in h99_f3_rows], raw, {r.ticker: r.total_demand_filter_status for r in h99_f3_rows},
                              cutoff=None, features=tuple(spec["features"]), recipe=bt.fitmod.recipe_for(spec), grid=(hz.INF,))
    assert [float(x) for x in res.fit.gamma] == frozen["gamma"] and not res.fit.beta.any()
    assert res.reclose == frozen["reclose_rates"] and res.n_pp_rows == frozen["training"]["n_pp_rows"] == 506
    out = ph.predict(frozen, {})
    pred = res.predict(raw[h99_f3_rows[0].ticker], h99_f3_rows[0].total_demand_filter_status)
    assert pred["hazards"] == out["hazard"] and pred["S"] == out["S"] and pred["P_close"] == out["P_close_ceiling"]


def test_pooled_at_inf_is_a_separate_rule_row():
    s = FAZ7_MODEL_SPECS[POOLED_INF]
    assert s["features"] == [] and s["lambda_grid"] == ["INF"] and s["regime"] == FAZ7_MODEL_SPECS[POOLED]["regime"]
    assert s["parent_model_id"] == POOLED and s["training"] == FAZ7_MODEL_SPECS[POOLED]["training"]
    assert "(gamma, delta) pseudo-satırlı MLE, Newton" in s["lambda_INF"]


def test_predict_hazard_still_stdlib_only():
    code = ("import sys; import borsai.predict_hazard as ph; "
            "bad = [m for m in ('numpy', 'sklearn', 'scipy', 'fractions') if m in sys.modules]; print(bad)")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    assert out == "[]"

"""Faz 5: D1 sonrası güncelleme `post_d1_hazard_v0` (docs/specs_faz5/SPEC_POST_D1_V0.md §11 kabul testleri) ve görev
testleri T1, T2, T4, T6, T11 (docs/prompts/FAZ5_POST_D1_IMPL.md).

Commit A kuralı: bu dosyadaki hiçbir test gerçek veride δ fit etmez ve walk-forward skoru üretmez. Gerçek veriyle koşanlar
karşılaştırıcı ve veri tanımı testleridir (§11-1, 2, 3, 4, 8; T6) ve λ = INF ucudur (δ ≡ 0: karşılaştırıcının kendisi, T2).
§11-10 burada elle verilmiş sabit δ ile koşar; gerçek nihai fit'i ve altın ledger'ı okuyan testler
tests/test_faz5_golden.py'dedir (commit B)."""
from __future__ import annotations

import ast
import copy
import csv
import json
import math
import random
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from borsai import backtest as bt
from borsai import freeze as fz
from borsai import hazard as hz
from borsai import outcomes as oc
from borsai import post_d1 as pd
from borsai import predict_hazard as ph
from borsai import predict_path as pth
from borsai import predict_post_d1 as pd1
from borsai import registry as reg
from borsai import report_faz1b as rf
from borsai import report_faz5 as r5
from borsai import scoring as sc
from borsai import survival as sv
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes, sha256_file
from borsai.specs import (FAZ5_MODEL_IDS, MODEL_SPECS, PLAN_POST_D1, POST_D1_MODEL_SPECS, SPEC_DOCUMENTS_FAZ5, model_kind,
                          plan_of, spec_sha256)

import faz5_support as fs
import faz7_support as fs7
import faz8_support as fs8

MODEL = "post_d1_hazard_v0"
BASE_COMMIT = "72a000f48917946fc7a84da74767dca734f19f8a"       # görev başlangıcı (Faz 5 şartnamesi push kanıtlı)
# Faz 5'in son commit'i (BORSAI_FAZ5_FREEZE_B). "Salt okunur yollar Faz 5'te değişmedi" denetimi BASE..bu commit aralığında
# yapılır: sonraki commit'ler (proje sahibinin push kanıtı 988025c, canlı akış görevi: CLAUDE.md kural 1 cümlesi, scores/)
# bu yolları meşru olarak değiştirir (SPEC_DEVIATIONS H46).
FAZ5_LAST_COMMIT = "dd7a8cd"
SPEC_COMMIT = "c20c092"                                        # docs/specs_faz5/ (uygulamadan önce push edildi)
FAZ4_SPEC_COMMIT = "52e15679391320b721e99db12bc1dabee978c016"  # docs/specs_faz4/
NOW = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
STDLIB_ALLOWED = {"__future__", "math", "typing", "decimal", "dataclasses"}
PROFILE = ROOT / "docs" / "specs_faz5" / "ekler" / "profil_d1.txt"


def _git(*args: str, root: Path = ROOT) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


def _git_bytes(rev: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


# ---------------------------------------------------------------- ortak fikstürler

@pytest.fixture(scope="module")
def parent():
    return pd.load_frozen(POST_D1_MODEL_SPECS[MODEL]["parent"])


@pytest.fixture(scope="module")
def path_params():
    return pd.load_frozen(POST_D1_MODEL_SPECS[MODEL]["path_secondary"])


@pytest.fixture(scope="module")
def d1(dataset):
    return pd.h99_d1(dataset)


@pytest.fixture(scope="module")
def final_rows(dataset):
    return pd.final_training_rows(dataset)


@pytest.fixture(scope="module")
def prep81(final_rows, d1):
    """81 arzın D1 ön işlemesi (özellik istatistiği; fit değil)."""
    return pd.fit_d1_prep({r.ticker: d1[r.ticker].values.features() for r in final_rows})


@pytest.fixture(scope="module")
def make_params(parent, path_params, prep81):
    """Elle verilmiş sabit δ ile parametre sözlüğü (fit_params ile aynı kurucu: post_d1.build_params)."""
    def make(delta, lam="INF", prep=None):
        return json.loads(pretty_json_bytes(pd.build_params(
            parent=parent[0], parent_sha=parent[1], path_sha=path_params[1], prep=prep or prep81, delta=delta,
            lam=hz.lambda_parse(lam), score_table=[], solver={"iterations": 0, "grad_max": 0.0},
            training_block={"set": "SYNTHETIC_FIXED_DELTA", "n": 81, "tickers_sha256": None, "cutoff_date": None,
                            "data_version_sha256": None})))
    return make


@pytest.fixture(scope="module")
def folds(dataset):
    """Ana modelin fold fit'leri ve δ eğitim kümeleri; δ fit'i YOK (kabul testleri 3, 4, 8)."""
    return pd.fold_parts(dataset, delta_grid=None)


@pytest.fixture(scope="module")
def inf_ledger(dataset):
    """Gerçek boru hattı, λ ızgarası {INF}: δ ≡ 0, model = karşılaştırıcı (T2/T7 uçtan uca; yeni modelin sonucu değil)."""
    return pd.backtest_ledger(dataset, delta_grid=(hz.INF,))


def _block(U="10.12", low=None, open_=None, high=None, close=None, volume="250000", trades="3500", half_day=0, halt=0, **extra):
    fields = {"open": open_ or U, "high": high or U, "low": low or U, "close": close or U, "volume": volume,
              "trade_count": trades, "upper_limit": U, **extra}
    return {"session_date": "2026-09-30", "session_h": 1, "fields_raw": fields, "half_day": half_day, "halt_flag": halt}


# ---------------------------------------------------------------- T1: predict_hazard refactor'u davranışı değiştirmedi

@pytest.mark.requires_git_history
def test_t1_predict_hazard_bit_equal_to_pre_refactor_snapshot():
    snap = fs.load_snapshot()
    assert snap["code_version"]["git_commit"] == BASE_COMMIT and snap["code_version"]["borsai_dirty"] is False
    models = {m: (p, sha) for m, _, p, sha in fs.index_models() if m not in fs7.frozen_tail_ids()}   # Faz 7/7C: kendi testleri
    assert set(models) == set(snap["outputs"]) == {"ceiling_hazard_v0", "ceiling_hazard_v0@INF", "pb_ceiling_v0",
                                                   "pb_ceiling_v0@INF", "base_km_expanding", "base_km_last10"}
    n = 0
    for m, outs in snap["outputs"].items():
        params, sha = models[m]
        assert sha == snap["models"][m]["params_sha256"]
        for case in snap["cases"]:
            assert fs.run_case(params, case["inputs"]) == outs[case["id"]], (m, case["id"])
            n += 1
    assert n == 6 * (99 + 14 + fs.N_RANDOM) == 1878
    assert sum(1 for c in snap["cases"] if c["id"].startswith("H99|")) == 99


def test_t1_registry_records_rerun_bit_equal():
    """7 resmi kayıt: kaydın model_inputs'u ile yeniden çalıştırılan hazard/km çıktıları saklı çıktıyla ==."""
    n = 0
    for path in sorted((ROOT / "registry" / "records").rglob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        for cell in rec["models"]:
            if cell["kind"] not in ("hazard", "km"):
                continue
            params_path = ROOT / cell["file"]
            assert sha256_file(params_path) == cell["params_sha256"]
            params = json.loads(params_path.read_text(encoding="utf-8"))
            assert ph.predict(params, rec["model_inputs"]) == cell["output"], (path.name, cell["model_id"])
            n += 1
    assert n == 7 * 6


def test_t1_linear_predictor_is_the_predict_path():
    snap = fs.load_snapshot()
    params = {m: p for m, _, p, _ in fs.index_models()}
    for m in ("ceiling_hazard_v0", "ceiling_hazard_v0@INF", "pb_ceiling_v0", "pb_ceiling_v0@INF"):
        for case in snap["cases"]:
            lp = ph.linear_predictor(params[m], case["inputs"])
            out = ph.predict(params[m], case["inputs"])
            assert (lp["refused"], lp["warnings"], lp["clipped"]) == (out["refused"], out["warnings"], out["clipped"])
            if not out["refused"]:
                assert [sv.sigmoid(e) for e in lp["eta"]] == out["hazard"]
    with pytest.raises(ph.PredictError):
        ph.linear_predictor(params["base_km_expanding"], {})


# ---------------------------------------------------------------- §11-1 eğitim kümesi ve PP sayımı

def test_1_training_set_and_pp_counts(dataset, final_rows, d1):
    assert len(final_rows) == 81 == POST_D1_MODEL_SPECS[MODEL]["training"]["n"]
    assert sum(d1[r.ticker].values.lock for r in final_rows) == 70
    rows = [r for r in sv.pp_table([sv.unit_of(x) for x in final_rows]) if r.day >= 2]
    ev = sum(r.event for r in rows)
    assert (len(rows), ev, len(rows) - ev) == (409, 67, 342)
    risk = [sum(1 for r in rows if r.day == d) for d in range(2, 11)]
    events = [sum(r.event for r in rows if r.day == d) for d in range(2, 11)]
    assert risk == [81, 70, 66, 53, 41, 33, 27, 21, 17] and events == [11, 4, 13, 12, 8, 6, 6, 4, 3]   # SPEC_CEILING_V0 §2
    assert len(d1) == 99
    assert sum(v.row.half_day == 0 for v in d1.values()) == 99 and sum(v.row.halt_flag for v in d1.values()) == 0
    assert sum(int(v.row.fields_raw["trade_count"]) > 0 for v in d1.values()) == 99
    assert {v.row.session_type for v in d1.values()} == {"OPEN_FULL_DAY"}
    assert {v.row.trading_status for v in d1.values()} == {"ACTIVE_NOT_SUSPENDED"}
    assert all(v.row.session_date <= pd.OUTCOME_CUTOFF for v in d1.values())


# ---------------------------------------------------------------- §11-2 özellik tanımı

def test_2_feature_definitions(dataset, final_rows, d1):
    assert pd1.evaluate_d1(_block("10.12", low="10.120"), "1000000").lock == 1          # "10.12" == "10.120"
    assert pd1.evaluate_d1(_block("10.12", low="10.11"), "1000000").lock == 0
    # AUDIT K3: binary64'te ayırt edilemeyen ama Decimal'de farklı ham metin → kilit yok (float eşitliği kırmızı olur)
    assert float("10.12") == float("10.1200000000000000001")
    assert pd1.evaluate_d1(_block("10.12", low="10.1200000000000000001"), "1000000").lock == 0
    assert pd1.evaluate_d1(_block("10.12", low="10.120"), "1000000").lock == 1
    locked = [r for r in final_rows if d1[r.ticker].values.lock]
    assert len(locked) == 70 and all(all(d1[r.ticker].values.lock_consistency.values()) for r in locked)
    assert not any(w["code"] == pd1.WARN_D1_LOCK_INCONSISTENT for r in final_rows for w in d1[r.ticker].values.warnings)
    # d1_turnover = ln(hacim / shares_offered); shares_offered f1/f2'nin paydasıyla aynı alan
    for r in final_rows:
        v = d1[r.ticker].values
        ratio = Decimal(d1[r.ticker].row.fields_raw["volume"]) / Decimal(r.feature_inputs()["shares_offered"])
        assert abs(math.exp(v.turnover_ln) / float(ratio) - 1) < 1e-12
        with localcontext(pd1._LN):   # 60 hane
            assert v.turnover_ratio == Decimal(d1[r.ticker].row.fields_raw["volume"]) / Decimal(r.inputs["shares_offered"])
    # profil_d1.txt §3 (81 arz, oran): p05 / p50 / p95 = 0.0009841 / 0.004202 / 0.5402
    ratios = [float(d1[r.ticker].values.turnover_ratio) for r in final_rows]
    profile = [float(Decimal(d1[r.ticker].row.fields_raw["volume"]) / Decimal(r.inputs["shares_offered"])) for r in final_rows]

    def q(values, p):   # profil betiğinin Type-7 kantili (ekler/m5_d1_profil.py)
        xs = sorted(values)
        h = (len(xs) - 1) * p
        lo, hi = math.floor(h), math.ceil(h)
        return xs[lo] + (xs[hi] - xs[lo]) * (h - lo)

    got = [float(pd.pp.quantile_type7(sorted(Fraction(x) for x in ratios), Fraction(p))) for p in ("1/20", "1/2", "19/20")]
    want = [q(profile, p) for p in (0.05, 0.5, 0.95)]
    assert all(abs(a - b) <= 1e-9 for a, b in zip(got, want))
    assert [f"{x:.4g}" for x in got] == ["0.0009841", "0.004202", "0.5402"]
    text = PROFILE.read_text(encoding="utf-8")
    assert "0.0007325 / 0.0009841 / 0.001519 / 0.004202 / 0.01714 / 0.5402 / 1.964" in text


# ---------------------------------------------------------------- §11-3 ofset paritesi

def test_3_offset_parity_every_fold_and_final(folds, parent, final_rows):
    src = {r["fold_id"]: r for r in folds["src_rows"]}
    assert len(folds["parts"]) == 71
    worst = 0.0
    for fid, part in folds["parts"].items():
        pd._parity(src[fid], part)     # |Δ| ≤ 1e-9 yoksa PostD1Error
        s = src[fid]
        got = [*part["parent_gamma"], *(part["parent_beta"][f] for f in ("f1", "f2", "f3")), *part["parent_test_hazards"]]
        want = [float(s[f"gamma_{g}"]) for g in sv.GROUP_NAMES] + [float(s[f"beta_{f}"]) for f in ("f1", "f2", "f3")] + \
               [float(s[f"hazard_{k}"]) for k in range(1, 11)]
        worst = max(worst, max(abs(a - b) for a, b in zip(got, want)))
        assert bt._fmt(part["parent_lambda"]) == s["selected_lambda"]
    assert worst <= 1e-9
    # nihai fit: ofset dondurulmuş JSON'dan, predict_hazard.predict'e bit-eşit (h_1 birebir)
    for r in final_rows:
        inputs = pd.model_inputs_of(r)
        lp, out = ph.linear_predictor(parent[0], inputs), ph.predict(parent[0], inputs)
        assert [sv.sigmoid(e) for e in lp["eta"]] == out["hazard"]


def test_3b_mismatched_offset_stops(folds):
    fid, part = next(iter(folds["parts"].items()))
    src = next(r for r in folds["src_rows"] if r["fold_id"] == fid)
    bad = {**part, "parent_gamma": [part["parent_gamma"][0] + 2e-9, *part["parent_gamma"][1:]]}
    with pytest.raises(pd.PostD1Error, match="ofset paritesi"):
        pd._parity(src, bad)


# ---------------------------------------------------------------- §11-4 fold kümesi

def test_4_fold_set_and_leakage_dates(folds, dataset):
    by = dataset.by_ticker()
    src = folds["src_rows"]
    assert len(src) == 87
    applicable = [r["fold_id"] for r in src if by[r["ticker"]].ceiling_streak >= 1]
    assert list(folds["parts"]) == applicable and len(applicable) == 71 and len(src) - 71 == 16
    insufficient = [f for f, p in folds["parts"].items()
                    if not (p["n_ipo"] >= 10 and p["n_events"] >= 5 and p["n_survivals"] >= 5)]
    assert insufficient == ["CEILING|EKOS"]   # raporlanır (δ eğitim kümesi: d ≥ 2 satırları)
    for r in src:
        p = folds["parts"].get(r["fold_id"])
        if p is None:
            continue
        T = r["prediction_date"]
        assert p["max_session_date"] < T and p["max_d1_date"] < T      # training_max_session_date < T; D1(j) < T
        assert p["n_ipo"] <= int(r["training_n_ipo"])


# ---------------------------------------------------------------- §11-5 ve T2: INF paritesi (bit-eşit, genel yoldan)

def _random_cases(final_rows, n, seed):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        r = rng.choice(final_rows)
        inputs = pd.model_inputs_of(r)
        for k in ("ipo_price_tl", "total_demand_multiple"):
            inputs[k] = str((Decimal(inputs[k]) * Decimal(repr(rng.uniform(0.4, 2.5)))).quantize(Decimal("0.01")))
        inputs["ipo_size_tl"] = None
        U = Decimal(rng.choice(["9.87", "25.30", "101.50", "14.20", "57.95", "312.25"]))
        low = str(U) if rng.random() < 0.8 else str((U * Decimal("0.95")).quantize(Decimal("0.01")))
        volume = str(rng.randint(1_000, 400_000_000))
        out.append((inputs, _block(str(U), low=low, volume=volume, trades=str(rng.randint(1, 900_000)),
                                   half_day=int(rng.random() < 0.05), halt=int(rng.random() < 0.05))))
    return out


def test_5_t2_inf_endpoint_bit_equal(make_params, parent, final_rows, d1):
    params = make_params({"d1_lock": 0.0, "d1_turnover": 0.0}, lam="INF")
    assert params["d1_preprocessing"]["columns"] == ["d1_lock", "d1_turnover"]
    cases = [(pd.model_inputs_of(r), d1[r.ticker].row.block()) for r in final_rows] + _random_cases(final_rows, 1000, 20260924)
    n = 0
    for inputs, block in cases:
        out = pd1.predict_post_d1(params, parent[0], inputs, block)
        base = ph.predict(parent[0], inputs)
        assert out["refused"] is None and base["refused"] is None and out["not_applicable"] is None
        assert out["hazard"] == base["hazard"] and out["S"] == base["S"]            # h_1 dahil, bit-eşit
        s_cond, pl_cond = pth.conditional_weights(out["S"], 1)
        assert (s_cond, pl_cond) == pth.conditional_weights(base["S"], 1)
        assert out["conditional_j1"]["S_cond"] == {str(k): v for k, v in s_cond.items()}
        prod = 1.0
        for k in range(2, 11):
            prod *= 1.0 - out["hazard"][k - 1]
            assert abs(s_cond[k] - prod) <= 1e-12                                       # Π(1 − h_d), 1e-12
        assert abs(sum(pl_cond.values()) - 1.0) <= 1e-12
        n += 1
    assert n == 81 + 1000


def test_5b_no_special_branch_for_zero_delta(make_params, parent, final_rows, d1, monkeypatch):
    """δ = 0 çıktısı genel yoldan (updated_hazards) gelir: çağrı sayacı > 0."""
    params = make_params({"d1_lock": 0.0, "d1_turnover": 0.0})
    calls = []
    real = pd1.updated_hazards
    monkeypatch.setattr(pd1, "updated_hazards", lambda *a: calls.append(1) or real(*a))
    r = final_rows[0]
    pd1.predict_post_d1(params, parent[0], pd.model_inputs_of(r), d1[r.ticker].row.block())
    assert calls == [1]


def test_t2_t7_pipeline_inf_ledger_equals_comparator(inf_ledger):
    ledger, info = inf_ledger
    assert [r["fold_id"] for r in ledger] == [r["fold_id"] for r in rf.load_runs()["ceiling_hazard_v0"]]
    assert list(ledger[0]) == pd.ledger_columns()
    parent = {r["ticker"]: r for r in rf.load_runs()["ceiling_hazard_v0"]}
    path_src = {r["fold_id"]: r for r in pd.read_pinned_csv(POST_D1_MODEL_SPECS[MODEL]["path_ledger"])[0]}
    from collections import Counter
    assert Counter(r["status"] for r in ledger) == {"FIT_OK": 70, "INSUFFICIENT_TRAINING_HISTORY": 1, "NOT_APPLICABLE": 16}
    ok = [r for r in ledger if r["status"] == "FIT_OK"]
    for r in ok:
        p = parent[r["ticker"]]
        S = [float(p[f"S_{k}"]) for k in range(1, 11)]
        assert [r[f"S_{k}"] for k in range(1, 11)] == S                                   # bit-eşit (T7: |Δ| = 0)
        assert [r[f"hazard_{k}"] for k in range(1, 11)] == [float(p[f"hazard_{k}"]) for k in range(1, 11)]
        assert {str(k): r[f"S_cond_{k}"] for k in range(2, 11)} == {str(k): v for k, v in pth.conditional_weights(S, 1)[0].items()}
        assert r["selected_lambda"] == "INF" and r["delta_d1_lock"] == r["delta_d1_turnover"] == 0.0
        assert (r["path_cond_status"] == "NOT_PRODUCED") == (path_src[r["fold_id"]]["status"] != "OK")
    assert info["survival_ledger_sha256"] == POST_D1_MODEL_SPECS[MODEL]["survival_ledger"]["sha256"]


# ---------------------------------------------------------------- §11-6 çözücü

def _synthetic(m=400, seed=1):
    rng = np.random.default_rng(seed)
    U = rng.normal(size=(m, 2))
    o = rng.normal(-1.5, 0.7, size=m)
    e = (rng.random(m) < 1 / (1 + np.exp(-(o + U @ np.array([-0.8, 0.4]))))).astype(float)
    return U, o, e


def test_6_solver_matches_bfgs_and_penalty_limit():
    from scipy.optimize import minimize

    U, o, e = _synthetic()
    o_before = o.copy()
    for lam in (0.1, 1.0, 30.0):
        fit = pd.fit_delta(U, o, e, lam, pd1.D1_COLUMNS)
        grad = U.T @ (hz._stable_sigmoid(o + U @ fit.delta) - e) + lam * fit.delta
        ref = minimize(lambda d: pd.objective(U, o, e, d, lam), np.zeros(2), method="BFGS",
                       jac=lambda d: U.T @ (hz._stable_sigmoid(o + U @ d) - e) + lam * d, options={"gtol": 1e-12})
        assert fit.status == hz.CONVERGED and np.max(np.abs(fit.delta - ref.x)) <= 1e-6 and np.max(np.abs(grad)) <= 1e-10
    big = pd.fit_delta(U, o, e, 1e9, pd1.D1_COLUMNS)
    assert np.linalg.norm(big.delta) <= 1e-6
    assert np.array_equal(o, o_before)                                   # ofset (γ, β) dokunulmadı
    eta = [float(x) for x in np.linspace(-2.5, 0.5, 10)]
    u = {"d1_lock": 1.3, "d1_turnover": -0.7}
    s_big = pd1.curves(pd1.updated_hazards(eta, big.by_feature(), u, pd1.D1_COLUMNS), {"r_a": 0.1, "r_b": 0.2})
    s_inf = pd1.curves(pd1.updated_hazards(eta, {"d1_lock": 0.0, "d1_turnover": 0.0}, u, pd1.D1_COLUMNS), {"r_a": 0.1, "r_b": 0.2})
    assert all(abs(s_big["conditional_j1"]["S_cond"][k] - s_inf["conditional_j1"]["S_cond"][k]) <= 1e-6 for k in s_inf["conditional_j1"]["S_cond"])
    assert s_inf["hazard"] == [sv.sigmoid(x) for x in eta]
    inf = pd.fit_delta(U, o, e, hz.INF, pd1.D1_COLUMNS)
    assert list(inf.delta) == [0.0, 0.0] and inf.status == hz.CONVERGED


# ---------------------------------------------------------------- §11-7 seçim kuralı

def _delta_set(n_ipo=24, seed=3, lock_const=False):
    rng = random.Random(seed)
    rows, eta, feats = {}, {}, {}
    for i in range(n_ipo):
        t = f"S{i:02d}"
        L = rng.randint(1, 10)
        rows[t] = [(d, int(L == d - 1)) for d in range(2, 11) if d - 1 <= L]
        base = rng.uniform(-2.5, -0.5)
        eta[t] = [base - 0.3] + [base + (0.0 if d <= 3 else 0.4) for d in range(2, 11)]
        feats[t] = {"d1_lock": 1.0 if lock_const else float(rng.random() < 0.8), "d1_turnover": math.log(rng.uniform(0.001, 1.5))}
    return pd.DeltaSet(list(rows), rows, eta, feats)


def test_7_selection_ties_to_largest_and_drops_nonconverged(monkeypatch):
    table = [{"lambda": 1.0, "score": 0.5, "status": hz.SCORED}, {"lambda": 10.0, "score": 0.5, "status": hz.SCORED},
             {"lambda": "INF", "score": 0.6, "status": hz.SCORED}]
    assert hz.choose_lambda(table) == 10.0
    assert hz.choose_lambda([*table[:2], {"lambda": "INF", "score": 0.5, "status": hz.SCORED}]) == hz.INF
    ds = _delta_set()
    lam, table = pd.select_lambda(ds)
    assert [e["lambda"] for e in table] == [0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, "INF"]
    assert all(e["status"] == hz.SCORED for e in table)
    real = pd.newton_offset

    def failing(U, o, e, lam):
        res = real(U, o, e, lam)
        return hz.SolverResult(res.theta, hz.STATUS_NOT_CONVERGED if lam == 3.0 else res.status, res.iterations, res.grad_max, res.objective)

    monkeypatch.setattr(pd, "newton_offset", failing)
    lam2, table2 = pd.select_lambda(ds)
    st = {e["lambda"]: e["status"] for e in table2}
    assert st[3.0] == hz.CANDIDATE_NOT_CONVERGED and st["INF"] == hz.SCORED and lam2 != 3.0
    # hiç kolon kalmadı (σ = 0): bütün λ'lar bit-eşit skor alır, eşitlik INF'i seçer
    const = _delta_set(lock_const=True)
    for t in const.tickers:
        const.feats[t]["d1_turnover"] = -3.0
    lam3, table3 = pd.select_lambda(const)
    assert lam3 == hz.INF and len({e["score"] for e in table3}) == 1


def test_7b_dropped_column_gets_zero_coefficient():
    ds = _delta_set(lock_const=True)
    tr = pd.fit_delta_set(ds, (1.0,))
    assert tr.prep.dropped == ("d1_lock",) and tr.prep.columns == ("d1_turnover",)
    assert tr.fit.by_feature()["d1_lock"] == 0.0


# ---------------------------------------------------------------- §11-8 sızıntı

def test_8_sessions_loader_whitelist(monkeypatch):
    accessed: dict[int, set] = {1: set(), 2: set()}

    class Tracking(dict):
        def __getitem__(self, k):
            accessed[1 if dict.__getitem__(self, "session_number") == "1" else 2].add(k)
            return dict.__getitem__(self, k)

        def get(self, k, default=None):
            return self[k] if k in self else default

    real = csv.DictReader

    class Reader(real):
        def __next__(self):
            return Tracking(super().__next__())

    monkeypatch.setattr(csv, "DictReader", Reader)
    d1, dates = pd.load_d1_sessions()
    assert len(d1) == 99 and all(len(v) == 10 for v in dates.values())
    assert accessed[2] == {"ticker", "session_number", "target_session_date"}
    assert accessed[1] == {"ticker", "session_number", "target_session_date", *pd.SESSION_1_FIELDS.values(),
                           *pd.SESSION_1_STATUS_COLUMNS}
    assert not accessed[1] & {"open", "high", "low", "close", "volume", "turnover", "aof", "upper_limit", "lower_limit"}


def test_8b_test_ipo_d1_fields_do_not_touch_training(dataset, folds):
    """Test arzının D1 alanı değiştirilince kendi fold'unun ön işleme istatistikleri (μ, σ, p05, p95) ve δ eğitim kümesi
    aynı kalır; aynı arzı eğitimde gören sonraki bir fold'unkiler değişir (test duyarlı)."""
    fids = list(folds["parts"])
    own = fids[len(fids) // 2]
    t = own.split("|")[1]
    changed = pd.fold_parts(dataset, delta_grid=None, feats_override={t: {"d1_lock": 0.0, "d1_turnover": 5.0}})
    a, b = folds["parts"][own], changed["parts"][own]
    assert a["prep"] == b["prep"] and a["feats_used"] == b["feats_used"] and t not in a["feats_used"]
    later = next(f for f in fids if t in folds["parts"][f].get("feats_used", {}))
    assert folds["parts"][later]["prep"] != changed["parts"][later]["prep"]


# ---------------------------------------------------------------- §11-9 ret, uyarı, kapsam

def test_9_refusals_warnings_scope(make_params, parent, final_rows, d1):
    params = make_params({"d1_lock": -0.5, "d1_turnover": 0.2}, lam=10.0)
    r = final_rows[0]
    inputs = pd.model_inputs_of(r)
    block = d1[r.ticker].row.block()
    base = pd1.predict_post_d1(params, parent[0], inputs, block)
    assert base["refused"] is None and base["not_applicable"] is None
    out = pd1.predict_post_d1(params, parent[0], {**inputs, "total_demand_multiple": None}, block)
    assert out["refused"]["code"] == "F3_MISSING" and out["hazard"] is None
    U = block["fields_raw"]["upper_limit"]
    na = copy.deepcopy(block)
    na["fields_raw"]["upper_limit"] = ""
    assert pd1.predict_post_d1(params, parent[0], inputs, na)["refused"]["code"] == pd1.REFUSED_D1_LIMIT_NA == "D1_LIMIT_NA"
    not_ceiling = copy.deepcopy(block)
    not_ceiling["fields_raw"]["close"] = str(Decimal(U) - Decimal("0.01"))
    out = pd1.predict_post_d1(params, parent[0], inputs, not_ceiling)
    assert out["refused"] is None and out["not_applicable"]["code"] == pd1.NOT_APPLICABLE_D1_NOT_CEILING and out["S"] is None
    half = pd1.predict_post_d1(params, parent[0], inputs, {**block, "half_day": 1})
    assert half["hazard"] == base["hazard"] and pd1.WARN_D1_HALF_DAY in [w["code"] for w in half["warnings"]]
    halt = pd1.predict_post_d1(params, parent[0], inputs, {**block, "halt_flag": 1})
    assert halt["hazard"] == base["hazard"] and pd1.WARN_D1_INTRADAY_HALT in [w["code"] for w in halt["warnings"]]
    special = copy.deepcopy(block)
    special["fields_raw"]["special_trade_volume"] = "12345"
    sp = pd1.predict_post_d1(params, parent[0], inputs, special)
    assert sp["hazard"] == base["hazard"] and pd1.WARN_D1_SPECIAL_TRADES in [w["code"] for w in sp["warnings"]]
    assert sp["d1_features"]["d1_turnover_ratio"] == base["d1_features"]["d1_turnover_ratio"]   # hacim değişmez
    high = copy.deepcopy(block)
    high["fields_raw"]["volume"] = str(int(Decimal(inputs["shares_offered"]) * 50))
    hi = pd1.predict_post_d1(params, parent[0], inputs, high)
    assert hi["d1_features"]["clipped"] is True and pd1.WARN_D1_TURNOVER_CLIPPED in [w["code"] for w in hi["warnings"]]
    assert hi["d1_features"]["d1_turnover_used"] == params["d1_preprocessing"]["clip"]["d1_turnover"]["p95"]
    vol0 = copy.deepcopy(block)
    vol0["fields_raw"]["volume"] = "0"
    assert pd1.predict_post_d1(params, parent[0], inputs, vol0)["refused"]["code"] == "D1_VOLUME_INVALID"
    no_trade = copy.deepcopy(block)
    no_trade["fields_raw"]["trade_count"] = "0"
    with pytest.raises(pd1.PredictError) as exc:
        pd1.predict_post_d1(params, parent[0], inputs, no_trade)
    assert exc.value.code == pd1.D1_NOT_TRADED
    incons = copy.deepcopy(block)
    incons["fields_raw"]["low"] = U
    incons["fields_raw"]["open"] = str(Decimal(U) - Decimal("0.05"))
    assert pd1.WARN_D1_LOCK_INCONSISTENT in [w["code"] for w in pd1.predict_post_d1(params, parent[0], inputs, incons)["warnings"]]
    with pytest.raises(pd1.D1Refusal) as ref:
        pd1.evaluate_d1(block, "0")
    assert ref.value.code == pd1.REFUSED_INPUT_SHARES_OFFERED
    wrong = copy.deepcopy(params)
    wrong["parent"]["gamma"] = [g + 1e-12 for g in wrong["parent"]["gamma"]]
    with pytest.raises(pd1.PredictError) as bad:
        pd1.predict_post_d1(wrong, parent[0], inputs, block)
    assert bad.value.code == "PARAMS_INVALID"


# ---------------------------------------------------------------- §11-10 JSON ↔ predict paritesi (sabit δ) ve stdlib

def test_10_numpy_final_model_vs_stdlib_predict_fixed_delta(dataset, make_params, parent, final_rows, d1):
    params = make_params({"d1_lock": -0.61, "d1_turnover": 0.27}, lam=30.0)
    numpy_side = pd.final_predictions(dataset, params)
    assert len(numpy_side) == 81
    worst = 0.0
    for r in final_rows:
        a = numpy_side[r.ticker]
        b = pd1.predict_post_d1(params, parent[0], pd.model_inputs_of(r), d1[r.ticker].row.block())
        for key in ("hazard", "S"):
            worst = max(worst, max(abs(x - y) for x, y in zip(a[key], b[key])))
        for key in ("S_cond", "P_L_cond"):
            worst = max(worst, max(abs(a["conditional_j1"][key][k] - b["conditional_j1"][key][k]) for k in a["conditional_j1"][key]))
        assert a["hazard"][0] == b["hazard"][0] == ph.predict(parent[0], pd.model_inputs_of(r))["hazard"][0]
    assert worst <= 1e-12


def _imports(path):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.module is None:
                out |= {"." + a.name for a in node.names}
            else:
                out.add("." + (node.module or "") if node.level else node.module.split(".")[0])
    return out


def test_10b_predict_post_d1_imports_are_stdlib():
    pkg = ROOT / "borsai"
    seen, queue, closure = set(), ["predict_post_d1"], {}
    while queue:
        mod = queue.pop()
        if mod in seen:
            continue
        seen.add(mod)
        imps = _imports(pkg / f"{mod}.py")
        closure[mod] = imps
        queue += [i.lstrip(".") for i in imps if i.startswith(".")]
    assert {i for v in closure.values() for i in v if not i.startswith(".")} <= STDLIB_ALLOWED, closure
    assert set(closure) <= {"predict_post_d1", "predict_hazard", "predict_path", "features", "survival", "predict", "horizons"}
    code = ("import json, sys\nimport borsai.predict_post_d1 as p\nprint(json.dumps(sorted(m for m in sys.modules if "
            "m.split('.')[0] in ('numpy', 'sklearn', 'scipy', 'joblib', 'threadpoolctl'))))\n")
    res = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert json.loads(res.stdout) == []


# ---------------------------------------------------------------- §11-11 path_conditional

def test_11_path_conditional_single_definition(make_params, parent, path_params, final_rows, d1, monkeypatch):
    params = make_params({"d1_lock": 0.0, "d1_turnover": 0.0})
    calls = []
    real = pth.conditional
    monkeypatch.setattr(pth, "conditional", lambda *a, **k: calls.append(1) or real(*a, **k))
    for r in final_rows[:12]:
        inputs, block = pd.model_inputs_of(r), d1[r.ticker].row.block()
        out = pd1.predict_post_d1(params, parent[0], inputs, block, path_params=path_params[0])
        path_out = pth.predict(path_params[0], inputs)
        own = real(path_params[0], path_out, 1, [block["fields_raw"]["close"]])   # ceiling_path_v0'ın j = 1 koşullu çıktısı
        assert out["path_conditional"] == own                                    # S ≡ ana modelin S'i -> bit-eşit
    assert len(calls) == 12
    assert pd1.predict_post_d1(params, parent[0], pd.model_inputs_of(final_rows[0]), d1[final_rows[0].ticker].row.block())["path_conditional"] is None
    none = pd.path_summary(None)
    assert none["path_cond_status"] == "NOT_PRODUCED" != "TARGET_UNAVAILABLE" and none["path_cond_h5_median"] is None
    assert "def mixture_atoms" not in (ROOT / "borsai" / "predict_post_d1.py").read_text(encoding="utf-8")
    assert "def mixture_atoms" not in (ROOT / "borsai" / "post_d1.py").read_text(encoding="utf-8")


# ---------------------------------------------------------------- §11-12 koşullu metrikler (ortak fonksiyonlar)

def test_12_conditional_metrics_use_shared_functions(monkeypatch):
    runs = rf.load_runs()
    calls = {"rps": 0, "brier": 0}
    real_rps, real_brier = pth.conditional_rps, pth.conditional_brier
    monkeypatch.setattr(pth, "conditional_rps", lambda *a: calls.__setitem__("rps", calls["rps"] + 1) or real_rps(*a))
    monkeypatch.setattr(pth, "conditional_brier", lambda *a: calls.__setitem__("brier", calls["brier"] + 1) or real_brier(*a))
    r5.paired_conditional(runs["ceiling_hazard_v0"], runs["base_km_last10"], "rps")
    r5.paired_conditional(runs["ceiling_hazard_v0"], runs["base_km_last10"], "brier2")
    assert calls["rps"] > 0 and calls["brier"] > 0
    for L in range(1, 11):
        S = [1.0 if L >= k else 0.0 for k in range(1, 11)]
        assert r5.cond_loss("rps", S, L) == 0.0
    assert r5.cond_loss("rps", [1.0] * 10, 1) == 1.0
    assert "def conditional_rps" not in (ROOT / "borsai" / "report_faz5.py").read_text(encoding="utf-8")


def test_12b_scale_mix_is_refused():
    good = sc.PairedObs(scale=r5.SCALE, ticker="A", block="2024-01", model_loss=0.1, rule_loss=0.2, j=1)
    uncond = sc.PairedObs(scale=sc.SCALE_BACKTEST, ticker="B", block="2024-01", model_loss=0.1, rule_loss=0.2)
    with pytest.raises(sc.ScaleMixError):
        r5.summarize([good, uncond])
    with pytest.raises(sc.ScaleMixError):
        r5.summarize([uncond])
    with pytest.raises(sc.ScaleMixError):
        sc.merge_scales({"scale": r5.SCALE}, {"scale": sc.SCALE_BACKTEST})


# ---------------------------------------------------------------- T6: karşılaştırıcı MODELS.md j = 1 satırını yeniden üretir

def _models_md_row(table_header: str) -> list[str]:
    text = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8").split("### Koşullu güncelleme (keşif): H99, j = 1..9")[1]
    lines = text.split(table_header)[1].splitlines()
    return [c.strip() for c in next(l for l in lines if l.startswith("| 1 |")).strip("|").split("|")]


def test_t6_comparator_reproduces_models_md_j1():
    runs = rf.load_runs()
    model = runs["ceiling_hazard_v0"]
    comps = ("ceiling_hazard_v0@INF", "base_km_expanding", "base_km_last10", "base_always_ceiling__ceiling")
    row = _models_md_row("| j | n | model RPS_j |")
    assert row[:3] == ["1", "71", rf._f(r5.own_mean(model, "rps"))] and row[2] == "0.1706"
    for cell, c in zip(row[3:], comps):
        p = r5.paired_conditional(model, runs[c], "rps")
        assert p["n"] == 71 and cell == f"{rf._s(p['mean'])} {rf._ci(p)}", c
    brier = _models_md_row("| j | n | model Brier k = j+1 |")
    assert brier[2] == rf._f(r5.own_mean(model, "brier2")) == "0.1277" and brier[7] == rf._f(r5.own_mean(model, "brier10")) == "0.1370"
    for i, c in enumerate(comps):
        for metric, cell in (("brier2", brier[3 + i]), ("brier10", brier[8 + i])):
            p = r5.paired_conditional(model, runs[c], metric)
            assert cell == f"{rf._s(p['mean'])} {rf._ci(p)}", (c, metric)
    # şartname §5'in sayıları (aynı tablo)
    spec = r5.SPEC_PATH.read_text(encoding="utf-8")
    assert "j = 1, n = 71: RPS_1 = 0.1706; Brier k = 2: 0.1277; Brier k = 10: 0.1370" in spec


# ---------------------------------------------------------------- §11-15 (kod tarafı): beklenti kuralları, günlük satırı

def test_15_expectation_rows_verbatim_and_rules():
    rows = r5.expectation_rows()
    assert len(rows) == 18 and rows[0]["primary"] and sum(r["primary"] for r in rows) == 1
    spec_lines = r5.SPEC_PATH.read_text(encoding="utf-8").splitlines()
    for row in rows:
        raw = row["raw"]
        assert any(l.startswith(f"| {raw['hucre']} | {raw['karsilastirilan']} | {raw['beklenen']} | {raw['sifir']} |") for l in spec_lines)
    diffs = [r for r in rows if r["kind"] in ("diff", "path")]
    assert len(diffs) == 12 and (rows[0]["lo"], rows[0]["hi"]) == (-0.020, 0.003) and (rows[4]["lo"], rows[4]["hi"]) == (-0.42, -0.36)
    assert [r["kind"] for r in rows[12:]] == ["calibration", "lambda_final", "lambda_folds", "sign_lock", "sign_turn", "n_folds"]
    row = rows[0]
    assert r5.diff_label(row, {"mean": -0.03, "ci95": [-0.06, 0.0]}) == "tutmadı (daha iyi)"
    assert r5.diff_label(row, {"mean": 0.004, "ci95": [-0.01, 0.02]}) == "tutmadı (daha kötü)"
    assert r5.diff_label(row, {"mean": -0.01, "ci95": [-0.04, 0.02]}) == "tuttu"
    assert r5.diff_label(rows[4], {"mean": -0.40, "ci95": [-0.5, 0.01]}) == "tutmadı (aralık)"            # "dışlar"
    assert r5.diff_label(rows[5], {"mean": -0.01, "ci95": [0.001, 0.02]}) == "tutmadı (aralık)"          # içerir ya da negatif dışlar
    assert r5.diff_label(rows[1], {"mean": -0.03, "ci95": [-0.06, 0.01]}) == "tuttu"                     # dışlaması olası (kesin: alt ≤ 0)
    assert r5.ci_statement_holds(rows[1]["ci_category"], [-0.06, 0.01]) is False
    for rule in r5.OPERATIONAL_RULES_FAZ5:
        assert rule and rule == rule.strip()
    assert (r5.TOO_GOOD_PRIMARY_DIFF, r5.TOO_GOOD_PRIMARY_CI_HI, r5.TOO_GOOD_BRIER2_DIFF) == (-0.040, -0.020, -0.040)
    assert (r5.FAIL_B_INF_SHARE, r5.FAIL_C_CALIBRATION, r5.CALIBRATION_EXPECTED) == (0.80, 0.10, 0.05)
    # AUDIT K4: λ, δ işareti ve n satırlarının sabitleri §5 tablosundaki değerlerle (yalnız MODELS.md bayt-eşitliğine kalmasın)
    assert r5.LAMBDA_FINAL_LIKELY == (10.0, 100.0) and r5.LAMBDA_FOLD_INF_SHARE == (0.20, 0.50)
    assert r5.LOCK_SIGN_SHARE == 0.80 and r5.N_FOLDS_RANGE == (65, 71)
    by_kind = {r["kind"]: r["raw"] for r in rows[12:]}
    assert by_kind["lambda_final"]["beklenen"].startswith("10–100 en olası")
    assert "fold'ların %20–50'sinde INF" in by_kind["lambda_folds"]["beklenen"]
    assert "(fold'ların ≥ %80'inde)" in by_kind["sign_lock"]["beklenen"]
    assert by_kind["n_folds"]["beklenen"] == "65–71"


def test_15b_run_backtest_logs_one_line(dataset, tmp_path, monkeypatch, inf_ledger):
    """Günlük satırının alanları (koşu kodu gerçek; ledger λ = INF ucundan, yeni modelin sonucu değil)."""
    monkeypatch.setattr(pd, "backtest_ledger", lambda ds, workers=None: inf_ledger)
    log = tmp_path / "log.jsonl"
    log.write_text('{"sentinel": 1}\n', encoding="utf-8")
    res = pd.run_backtest(dataset, log_path=log, context="pytest")
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 and json.loads(lines[0]) == {"sentinel": 1}
    e = json.loads(lines[1])
    spec = POST_D1_MODEL_SPECS[MODEL]
    assert e["kind"] == "backtest" and e["model_id"] == MODEL and e["plan_id"] == PLAN_POST_D1 == plan_of(MODEL)
    assert e["spec_sha256"] == spec_sha256(spec) and e["spec_document_sha256"] == SPEC_DOCUMENTS_FAZ5["SPEC_POST_D1_V0"]["sha256"]
    assert e["survival_ledger_sha256"] == spec["survival_ledger"]["sha256"] and e["ledger_sha256"] == sha256_bytes(res.ledger_csv)
    assert e["metrics"]["scale"] == "backtest_conditional" and e["data_version_sha256"] == dataset.data_version_sha256
    assert {x["run_key"] for x in e["evaluated"]} == set(r5.COMPARATORS) | {"ceiling_path_v0"}
    assert {"git_commit", "borsai_source_sha256", "started_at", "finished_at", "context", "metrics"} <= set(e)


def test_15c_report_on_inf_endpoint_ledger(dataset, tmp_path, inf_ledger, parent):
    """Rapor kodu λ = INF ucunda (model ≡ karşılaştırıcı): birincil fark 0, hepsi eşitlik, (b) gerçekleşir -> canlı akış
    kurulmaz, T7 = 0, (d) yok. Bölüm başlıkları üretilir."""
    ledger, _ = inf_ledger
    d = tmp_path / "golden"
    d.mkdir()
    (d / pd.golden_filename()).write_bytes(bt.ledger_csv_bytes(ledger))
    preview = {"lambda": "INF", "delta": {"d1_lock": 0.0, "d1_turnover": 0.0}, "lambda_score_table": [],
               "solver": {"iterations": 0, "grad_max": 0.0}, "parent": {"sha256": parent[1]},
               "d1_preprocessing": {"columns": [], "dropped": [], "clip": {"d1_turnover": {"p05": 0.0, "p95": 0.0}}},
               "training": {"set": "H99_F3_PRESENT_L_GE_1", "n_delta_ipo": 81, "n_pp_rows": 409, "n_events": 67,
                            "n_survivals": 342, "cutoff_date": "2026-08-19"}}
    (d / pd.FINAL_PREVIEW_FILE).write_text(json.dumps(preview), encoding="utf-8")
    (d / "MANIFEST.json").write_text(json.dumps({"runs": {MODEL: {"ledger_sha256": "0" * 64}},
                                                 "final_fit_preview": {"file": pd.FINAL_PREVIEW_FILE}}), encoding="utf-8")
    rows = r5._read(d / pd.golden_filename())
    runs = rf.load_runs()
    ev = r5.evaluate(rows, runs, r5.path_comparator(dataset, rows), r5.realized_of(dataset), preview)
    prim = ev["primary"]
    assert prim["mean"] == 0.0 and prim["tie_n"] == prim["n"] == 70 and prim["verdict"] == "AYIRT_EDILEMIYOR"
    assert ev["fold"]["t7_max_abs"] == 0.0 and ev["fold"]["h1_mismatch"] == [] and not ev["failures"]["d"]
    assert ev["failures"]["b"] and ev["live_flow"] == "kurulmaz" and not ev["failures"]["a"]
    assert all(p is None or p["mean"] == 0.0 for (h, o), p in ev["path_cells"].items())
    assert len(ev["rows"]) == 18 and all(e["label"] for e in ev["rows"])
    lines: list[str] = []
    r5.render_faz5(lines.append, tmp_path / "log.jsonl", faz5_dir=d, runs=runs, dataset=dataset)
    text = "\n".join(lines)
    for heading in ("## Faz 5: D1 sonrası güncelleme", "### Birincil hücre", "### Başarısızlık tanımları (§5) ve canlı akış koşulu",
                    "### §5 beklentisi ile gerçekleşen (satır satır)", "### Bütün §4 hücreleri", "### Fold özeti",
                    "### Nihai fit önizlemesi (dondurulmadı)", "**Canlı akış koşulu (proje sahibi kararı 3): kurulmaz**"):
        assert heading in text, heading
    for rule in r5.OPERATIONAL_RULES_FAZ5:
        assert rule in text
    assert text.count("| RPS_1 (k = 2..10) |") == 5
    assert not r5.golden_available(tmp_path / "yok")


# ---------------------------------------------------------------- T4: POST_D1 modelleri ayrı dizinde

def _copy_models(tmp_path) -> Path:
    """Listeleme öncesi model ağacının kopyası: INDEX.json ve listelediği dosyalar (donmuş POST_D1 dosyaları ve
    INDEX_POST_D1.json hariç; bu testler dizinin yokken ve sentetik modelle nasıl davrandığını sınar)."""
    d = tmp_path / "models"
    d.mkdir(parents=True)
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
    for name in ["INDEX.json"] + [e["file"] for e in index["models"]]:
        (d / name).write_bytes((ROOT / "models" / name).read_bytes())
    return d


def _stub_params(make_params):
    p = make_params({"d1_lock": -0.3, "d1_turnover": 0.1}, lam=10.0)
    p["training"].update(n=81, cutoff_date="2026-08-19", tickers_sha256="stub", data_version_sha256="stub")
    return p


def test_t4_freeze_post_d1_writes_only_the_separate_index(tmp_path, dataset, monkeypatch, make_params):
    d = _copy_models(tmp_path)
    before = (d / "INDEX.json").read_bytes()
    monkeypatch.setattr(pd, "fit_params", lambda ds, models_dir=None: _stub_params(make_params))
    post = fz.freeze([MODEL], dataset, models_dir=d)
    assert (d / "INDEX.json").read_bytes() == before
    idx = json.loads((d / fz.INDEX_POST_D1_NAME).read_text(encoding="utf-8"))
    assert idx == post and idx["schema_version"] == fz.INDEX_SCHEMA == "borsai.model_index/1"
    assert [e["model_id"] for e in idx["models"]] == [MODEL] and idx["models"][0]["stage"] == "POST_D1"
    assert idx["models"][0]["sha256"] == sha256_file(d / f"{MODEL}.json")
    assert fz.model_kind(json.loads((d / f"{MODEL}.json").read_text(encoding="utf-8"))) == "post_d1" == model_kind(MODEL)
    with pytest.raises(fz.FreezeError, match="zaten"):
        fz.freeze([MODEL], dataset, models_dir=d)
    with pytest.raises(fz.FreezeError, match="aynı çağrıda"):
        fz.freeze([MODEL, "base_zero"], dataset, models_dir=d)
    # ön koşul: parent sha INDEX.json ile eşit
    d2 = _copy_models(tmp_path / "b")
    (d2 / "ceiling_hazard_v0.json").write_bytes((d2 / "ceiling_hazard_v0.json").read_bytes() + b" ")
    with pytest.raises(fz.FreezeError, match="ceiling_hazard_v0"):
        fz.freeze([MODEL], dataset, models_dir=d2)
    assert not (d2 / fz.INDEX_POST_D1_NAME).exists()
    d3 = _copy_models(tmp_path / "c")
    (d3 / "ceiling_path_v0.json").write_bytes(b"{}")
    with pytest.raises(fz.FreezeError, match="ceiling_path_v0"):
        fz.freeze([MODEL], dataset, models_dir=d3)
    assert run_model_error(_stub_params(make_params))


def run_model_error(params) -> bool:
    res = fz.run_model(params, {})
    return res["status"] == fz.STATUS_ERROR and res["kind"] == "post_d1"


def _synthetic_inputs(tmp_path, ticker, **field_values):
    doc = copy.deepcopy(reg.load_inputs(reg.INPUTS_DIR / f"{ticker}.json")[0])
    for name, value in field_values.items():
        doc["fields"][name]["value"] = value
    p = tmp_path / f"{ticker}_synthetic.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.mark.requires_raw_sources
def test_t4_pre_listing_record_ignores_post_d1_index(tmp_path, make_params):
    d = _copy_models(tmp_path)
    inputs = _synthetic_inputs(tmp_path, "CITAS", first_trading_date="2026-09-30")
    a = pretty_json_bytes(fz.build_record(inputs, now=NOW, models_dir=d))
    params = _stub_params(make_params)
    (d / f"{MODEL}.json").write_bytes(pretty_json_bytes(params))
    (d / fz.INDEX_POST_D1_NAME).write_bytes(pretty_json_bytes({"schema_version": fz.INDEX_SCHEMA, "models": [
        {**fz.index_entry(params, f"{MODEL}.json", sha256_file(d / f"{MODEL}.json")), "stage": "POST_D1"}]}))
    b = pretty_json_bytes(fz.build_record(inputs, now=NOW, models_dir=d))
    assert a == b
    rec = json.loads(b)
    assert MODEL not in rec["models_index"]["model_ids"] and rec["summary"]["n_models"] == 19 + len(fs7.frozen_tail_ids())


def _init(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)


def _commit_all(root: Path, msg: str, *paths: str) -> None:
    _git("add", *paths, root=root)
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", msg, root=root)


def test_t4_sequence_guard_reads_post_d1_index(tmp_path):
    root = tmp_path / "repo"
    (root / "models").mkdir(parents=True)
    (root / "registry" / "records").mkdir(parents=True)
    _init(root)
    (root / "models" / "INDEX.json").write_text('{"models": [{"file": "m.json"}]}', encoding="utf-8")
    (root / "models" / "m.json").write_text("{}", encoding="utf-8")
    _commit_all(root, "models", "models")
    oc.sequence_guard("2026-09-01", root=root)                                  # yalnız INDEX.json: serbest
    (root / "models" / "INDEX_POST_D1.json").write_text('{"models": [{"model_id": "p", "file": "p.json"}]}', encoding="utf-8")
    _commit_all(root, "post index", "models/INDEX_POST_D1.json")
    with pytest.raises(oc.SequenceRuleError, match="p.json"):                  # dizindeki model dosyası commit'li değil (yok)
        oc.sequence_guard("2026-09-01", root=root)
    (root / "models" / "p.json").write_text("{}", encoding="utf-8")
    with pytest.raises(oc.SequenceRuleError):                                    # commit edilmemiş POST_D1 model dosyası
        oc.sequence_guard("2026-09-01", root=root)
    _commit_all(root, "post model", "models/p.json")
    oc.sequence_guard("2026-09-01", root=root)
    oc.sequence_guard("2026-08-19", root=tmp_path)                              # sınırda: serbest (dizin bile gerekmez)


@pytest.mark.requires_git_history
def test_t4_scores_unchanged_with_post_d1_index(tmp_path):
    """Sahte INDEX_POST_D1.json varken build_scores çıktısı generated_at_utc ve code dışında aynı (commit'li ağacın klonu)."""
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", "--local", str(ROOT), str(clone)], check=True)
    code = ("import json, sys\nsys.path.insert(0, sys.argv[1])\nfrom borsai import scoring as sc\n"
            "from datetime import datetime, timezone\n"
            "s = sc.build_scores(now=datetime(2026, 9, 24, tzinfo=timezone.utc))\n"
            "s.pop('generated_at_utc'); s.pop('code')\nprint(json.dumps(s, sort_keys=True))\n")

    def run():
        res = subprocess.run([sys.executable, "-c", code, str(clone)], cwd=clone, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)

    before = run()
    (clone / "models" / "INDEX_POST_D1.json").write_text(json.dumps({"schema_version": fz.INDEX_SCHEMA, "models": [
        {"model_id": MODEL, "file": f"{MODEL}.json", "sha256": "0" * 64, "stage": "POST_D1"}]}), encoding="utf-8")
    (clone / "models" / f"{MODEL}.json").write_text("{}", encoding="utf-8")
    assert run() == before


# ---------------------------------------------------------------- T11 ve §11-14 (bu göreve düşen) bekçiler

@pytest.mark.requires_git_history
def test_t11_spec_pins_and_guards():
    for p in (ROOT / "docs" / "specs_faz5").rglob("*"):
        if p.is_file():
            rel = p.relative_to(ROOT).as_posix()
            assert p.read_bytes() == _git_bytes(SPEC_COMMIT, rel), rel
    listed = _git("ls-tree", "-r", "--name-only", SPEC_COMMIT, "docs/specs_faz5/").split()
    assert sorted(listed) == sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "docs" / "specs_faz5").rglob("*") if p.is_file())
    assert sha256_file(r5.SPEC_PATH) == SPEC_DOCUMENTS_FAZ5["SPEC_POST_D1_V0"]["sha256"] == \
           "a5b4675d84784b4a9db9c3b0f7fe3b6a1c1014e823c66b237b4613b51f7ead34"
    assert _git("status", "--porcelain", "--untracked-files=all", "--", "docs/specs", "docs/specs_faz4", "docs/specs_faz5") == ""
    assert len([p for p in (ROOT / "docs" / "specs").rglob("*") if p.is_file()]) == 11
    for p in (ROOT / "docs" / "specs_faz4").rglob("*"):
        if p.is_file():
            rel = p.relative_to(ROOT).as_posix()
            assert p.read_bytes() == _git_bytes(FAZ4_SPEC_COMMIT, rel), rel


@pytest.mark.requires_git_history
def test_14_models_goldens_and_read_only_paths_unchanged(dataset):
    """Dondurmadan (BORSAI_FAZ5_FREEZE) sonra models/'e yalnız iki POST_D1 dosyası eklenmiştir (commit'li); INDEX.json ve
    listeleme öncesi 19 model dosyası BASE_COMMIT'le bayt-eşit (donmuş dosyanın kendisi: tests/test_faz5_frozen.py)."""
    frozen_files = {f"{MODEL}.json", fz.INDEX_POST_D1_NAME}
    faz7_files = {f"{m}.json" for m in fs7.frozen_tail_ids()}          # Faz 7 ve 7C dondurmaları (SPEC_DEVIATIONS J23, K19)
    faz8_files = set(fs8.frozen_post_break_files())                     # Faz 8 dondurması: yalnız eklenen üç dosya (K-PIN, N25)
    models = sorted(p.name for p in (ROOT / "models").iterdir() if p.is_file() and p.suffix == ".json")
    pre = [m for m in models if m not in frozen_files | faz7_files | faz8_files]
    assert len(models) == 22 + len(faz7_files) + len(faz8_files) and frozen_files <= set(models) and len(pre) == 20
    assert "INDEX.json" in pre
    for name in pre:
        if name == "INDEX.json" and faz7_files:                             # ilk 19 giriş aynen, sonunda yalnız v1 ve (C) girişleri
            continue
        assert (ROOT / "models" / name).read_bytes() == _git_bytes(BASE_COMMIT, f"models/{name}"), name
    assert sorted(_git("diff", "--name-only", "--diff-filter=A", BASE_COMMIT, "--", "models").split()) == \
        sorted(f"models/{n}" for n in frozen_files | faz7_files | faz8_files)
    for d in ("tests/reference/macos_golden", "tests/reference/macos_golden_faz1b", "tests/reference/macos_golden_faz4"):
        for name in _git("ls-tree", "-r", "--name-only", BASE_COMMIT, d + "/").split():
            assert (ROOT / name).read_bytes() == _git_bytes(BASE_COMMIT, name), name
    assert _git("diff", "--name-only", BASE_COMMIT, FAZ5_LAST_COMMIT, "--", "scores", "registry", "data", "app",
                "docs/SCORES.md", "legacy", "CLAUDE.md") == ""
    assert _git("diff", "--name-only", "--diff-filter=CDMRTU", BASE_COMMIT, "--", "models").split() == (["models/INDEX.json"] if faz7_files else [])
    assert _git("status", "--porcelain", "--untracked-files=all", "--", "registry", "data", "models", "legacy") == ""
    base_log = _git_bytes(BASE_COMMIT, "experiments/log.jsonl")
    assert (ROOT / "experiments" / "log.jsonl").read_bytes().startswith(base_log)          # yalnız ekleme
    assert MODEL not in MODEL_SPECS and FAZ5_MODEL_IDS == (MODEL,) and model_kind(MODEL) == "post_d1"
    assert all(d <= pd.OUTCOME_CUTOFF for r in pd.final_training_rows(dataset) for d in r.session_dates)

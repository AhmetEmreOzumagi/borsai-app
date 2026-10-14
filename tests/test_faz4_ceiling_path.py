"""Faz 4: tavan yolu modelleri (docs/specs_faz4/SPEC_CEILING_PATH_V0.md §9 kabul testleri 1–13) ve bekçiler:
altın ledger bayt eşitliği, dondurma kararı (§6 "beklentiden çok iyi"), dondurulmuş JSON'ların alanları, scores.json'da
Faz 1 bloklarının değişmezliği, MODELS.md.

§6 "beklentiden çok iyi" tetiklendi; şartnamenin istediği bağımsız yeniden üretim (docs/fable_faz4_audit/AUDIT.md,
2026-09-22, maks |Δ| = 0, üç model için FREEZE_OK) yapıldıktan sonra üç model models/ altına donduruldu ve INDEX'in
sonuna eklendi (`test_freeze_decision_follows_too_good_check`). Dondurma yolunun ürettiği parametreler (`built`)
repo'daki dosyalarla ayrıca karşılaştırılır (`test_frozen_files_match_the_freeze_path`)."""
from __future__ import annotations

import ast
import copy
import json
import math
import random
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from borsai import backtest as bt
from borsai import ceiling_path as cp
from borsai import freeze as fz
from borsai import predict_hazard as ph
from borsai import predict_path as pth
from borsai import registry as reg
from borsai import report_faz4 as r4
from borsai import scoring as sc
from borsai import survival as sv
from borsai.data import load_pb
from borsai.horizons import HORIZONS
from borsai.provenance import ROOT, identity_hash, pretty_json_bytes, sha256_bytes, sha256_file
from borsai.specs import (FAZ1A_MODEL_IDS, FAZ1B_MODEL_IDS, FAZ4_MODEL_IDS, MODEL_SPECS,
                          PLAN_PB_CEILING_PATH, SPEC_DOCUMENTS_FAZ4, spec_sha256)

import faz5_support as fs
import faz7_support as fs7
import faz7c_support as fs7c
import faz8_support as fs8
from faz1b_support import refit

MAIN, ZERO, PB = FAZ4_MODEL_IDS
SPEC_COMMIT = "52e15679391320b721e99db12bc1dabee978c016"   # docs/specs_faz4/ (uygulamadan önce push edildi)
FAZ1B_COMMIT = "b09cab5c1bc7e2b7dfc3890358b6268a1801febf"  # Faz 1B modelleri ve altın ledger'ları
SCORES_COMMIT = "f1f9d444132e89f0377b026b76d775a82685c649"  # Faz 2B commit B: ilk canlı skorlama
OUTCOME_CUTOFF = "2026-08-19"
NOW = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
STDLIB_ALLOWED = {"__future__", "math", "typing", "decimal", "dataclasses"}
V15_INPUTS = {"ipo_price_tl": "25.52", "shares_offered": "87500000", "post_ipo_share_capital": "312500000",
              "capital_increase_shares": "62500000", "total_demand_multiple": "2.84"}
PB_INPUTS = {"ipo_price_try": "76.60", "planned_pre_ipo_capital": "433300000", "planned_post_ipo_capital": "481612950",
             "planned_capital_increase_shares": "48312950", "planned_existing_share_sale": "0",
             "planned_base_offer_shares": "48312950", "planned_additional_sale_ceiling": "0",
             "planned_max_offer_shares": "48312950"}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def _git_bytes(rev: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


@pytest.fixture(scope="module")
def sessions():
    return cp.load_sessions()


@pytest.fixture(scope="module")
def units(dataset, sessions):
    return cp.path_units(dataset.rows, sessions)


@pytest.fixture(scope="module")
def full_cells(units):
    return pth.build_cells(units)


@pytest.fixture(scope="module")
def ledgers(dataset):
    return {m: cp.backtest_ledger(MODEL_SPECS[m], dataset)[0] for m in FAZ4_MODEL_IDS}


@pytest.fixture(scope="module")
def built(dataset):
    """Dondurma yolunun (freeze -> fit -> ceiling_path.fit_params) üreteceği parametre dosyaları, dosyaya yazılıp
    okunmuş gibi (pretty_json_bytes gidiş-dönüşü). Repo'ya yazılmaz."""
    from borsai.fit import fit

    return {m: json.loads(pretty_json_bytes(fit(MODEL_SPECS[m], list(dataset.rows), dataset_version=dataset.data_version_sha256)))
            for m in FAZ4_MODEL_IDS}


# ---------------------------------------------------------------- §9-1 fiyat adımı ve limit

def test_1_tick_table_and_limits_reproduce_990_sessions(sessions):
    rows = [x for s in sessions.values() for x in s]
    assert len(rows) == 990
    assert sum(pth.upper_limit(x.reference) == x.upper for x in rows) == 990
    assert sum(pth.lower_limit(x.reference) == x.lower for x in rows) == 990
    assert pth.tick(Decimal("19.999")) == Decimal("0.01")
    assert pth.tick(Decimal("20")) == Decimal("0.02")
    assert pth.tick(Decimal("2500")) == Decimal("2.50")
    assert pth.tick(Decimal("49.999")) == Decimal("0.02") and pth.tick(Decimal("50")) == Decimal("0.05")


# ---------------------------------------------------------------- §9-2 limit yolu

def test_2_limit_path_equals_every_official_ceiling_close(dataset, sessions):
    equal, differ, snaps = [0] * 10, [0] * 10, {}
    for r in dataset.rows:
        P = Decimal(r.inputs["ipo_price_tl"])
        lp = pth.limit_path(P)
        if lp["snapped_ipo_price"] != P:
            snaps[r.ticker] = (str(P), str(lp["snapped_ipo_price"]))
        for h in range(1, 11):
            if r.ceiling_streak >= h:
                if lp["C"][h - 1] == sessions[r.ticker][h - 1].close:
                    equal[h - 1] += 1
                else:
                    differ[h - 1] += 1
    assert equal == [81, 70, 66, 53, 41, 33, 27, 21, 17, 14] and differ == [0] * 10
    assert snaps == {"BORLS": ("25.29", "25.30"), "AVPGY": ("55.08", "55.10"), "ARTMS": ("25.35", "25.36"),
                     "LILAK": ("37.39", "37.40")}


# ---------------------------------------------------------------- §9-3 hücre sayımı

def test_3_cell_counts_full_cohort(units, sessions, full_cells):
    cells, info = full_cells
    assert [len(cells[("Z", m)]) for m in range(1, 11)] == [18] * 10
    assert [len(cells[("B", m)]) for m in range(1, 10)] == [67, 64, 60, 54, 48, 40, 28, 15, 11]
    assert info["n_obs"] == 567 and info["max_session_date"] <= OUTCOME_CUTOFF
    out_of_bounds = floor = ceiling = n_m1 = 0
    for u in units:
        t = u.streak
        if t >= 10:
            continue
        base = u.ipo_price if t == 0 else u.closes[t - 1]
        for m in range(1, 11 - t):
            g = u.closes[t + m - 1] / base   # kesin Decimal
            out_of_bounds += not (Decimal("0.9") ** m <= g <= Decimal("1.1") ** m)
        s = sessions[u.ticker][t]            # m = 1: kırılma günü (Z: D1)
        n_m1 += 1
        floor += s.close == s.lower
        ceiling += s.close == s.upper
    assert out_of_bounds == 0
    assert (n_m1, floor, ceiling) == (85, 36, 0)
    for lst in cells.values():
        assert lst == sorted(lst)


# ---------------------------------------------------------------- §9-4 tutarlılık

def _random_S(rng: random.Random) -> list[float]:
    return sv.survival([rng.random() ** rng.choice((0.3, 1.0, 3.0)) * rng.choice((0.2, 0.6, 1.0)) for _ in range(10)])


def test_4_mixture_consistency_1000_random_S(dataset, full_cells):
    cells, _ = full_cells
    rng = random.Random(20260922)
    prices = [Decimal(r.inputs["ipo_price_tl"]) for r in dataset.rows]
    curves = [_random_S(rng) for _ in range(1000)] + [[1.0] * 10]
    checked = 0
    for i, S in enumerate(curves):
        P = prices[i % len(prices)]
        lp = pth.limit_path(P)
        P_L = sv.p_streak(S)
        for h in range(1, 11):
            parts = [(t, P_L[t], None if t == 0 else lp["scale"][t - 1]) for t in range(h)]
            atoms, used, ok = pth.mixture_atoms((lp["rho"][h - 1], S[h - 1]), parts, cells, h)
            assert ok
            out = pth.horizon_prediction(S, P_L, lp["scale"], lp["rho"], cells, h)
            rho, lo, hi = lp["rho"][h - 1], (0.9 ** h - 1), pth.rho_max(P, lp["snapped_ipo_price"], h)
            assert abs(sum(w for _, w in atoms) - 1.0) <= 1e-12
            assert out["return"] <= rho and out["q50"] == out["return"]
            if S[h - 1] >= 0.5:
                assert out["return"] == rho
            assert 0.0 <= out["p_up"] <= 1.0 and out["p_up"] >= S[h - 1]
            assert out["q10"] <= out["q50"] <= out["q90"]
            assert all(lo - 1e-12 <= r <= hi + 1e-12 for r, _ in atoms)
            if S == [1.0] * 10:
                assert out["q10"] == out["q50"] == out["q90"] == rho and out["p_up"] == 1.0
            checked += 1
    assert checked == 10010


# ---------------------------------------------------------------- §9-5 sıfır model

def test_5_zero_model_survival_and_embedded_copies(dataset, built):
    index = {e["model_id"]: e for e in json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]}
    for m in FAZ4_MODEL_IDS:
        p = built[m]
        surv_id = MODEL_SPECS[m]["survival_model_id"]
        assert p["survival_model_id"] == surv_id
        assert sha256_bytes(pretty_json_bytes(p["survival_model"])) == p["survival_model_sha256"] == index[surv_id]["sha256"]
        assert p["survival_model"] == json.loads((ROOT / "models" / index[surv_id]["file"]).read_text(encoding="utf-8"))
    z = built[ZERO]
    out = pth.predict(z, V15_INPUTS)
    ref = ph.predict(json.loads((ROOT / "models" / "ceiling_hazard_v0@INF.json").read_text(encoding="utf-8")), {})
    assert out["refused"] is None and out["S"] == ref["S"] and out["hazard"] == ref["hazard"]
    units = [sv.unit_of(r) for r in dataset.rows if r.inputs["total_demand_multiple"] is not None]
    events, risk = sv.group_counts(sv.pp_table(units))
    assert z["survival_model"]["gamma"] == [sv.closed_form_gamma(e, n) for e, n in zip(events, risk)]
    assert z["survival_model"]["beta"] == {} and z["survival_model"]["lambda"] == "INF"


# ---------------------------------------------------------------- §9-6 predict paritesi

def _survival_fits():
    from borsai import fit as fitmod

    out = {}
    for m in FAZ4_MODEL_IDS:
        surv_id = MODEL_SPECS[m]["survival_model_id"]
        spec = MODEL_SPECS[surv_id]
        rows = fitmod.select_training_rows(spec, list(__import__("borsai.data").data.load_dataset().rows))
        res = refit(surv_id)[1]["hazard"]
        raw = fitmod.model_raw_features(spec, rows)[0] if spec["features"] else {r.ticker: {} for r in rows}
        out[m] = (rows, res, raw)
    return out


def test_6_predict_parity_with_backtest_final_freeze(dataset, built):
    """Backtest kodunun nihai-dondurma hesabı (numpy fit'in S'i + veriden yeniden kurulan hücreler) ile stdlib
    predict_path.predict (dondurma yolunun JSON'u) |Δ| ≤ 1e-9: 97 (ana), 97 (sıfır), 99 (PB)."""
    pb = load_pb(dataset)
    fits = _survival_fits()
    sizes = {}
    for m in FAZ4_MODEL_IDS:
        params = built[m]
        rows, res, raw = fits[m]
        sizes[m] = len(rows)
        for r in rows:
            S = res.predict(raw[r.ticker], r.total_demand_filter_status)["S"]
            if m == PB:
                inputs, P = dict(pb[r.ticker].fields), Decimal(pb[r.ticker].fields["ipo_price_try"])
            else:
                inputs, P = r.feature_inputs(), Decimal(r.inputs["ipo_price_tl"])
            ref = cp.final_predictions(params, S, P)
            got = pth.predict(params, inputs)
            assert got["refused"] is None, (m, r.ticker)
            for h in range(1, 11):
                for key in ("return", "p_up", "q10", "q90", "mean"):
                    assert abs(got[f"D{h}"][key] - ref[h][key]) <= 1e-9, (m, r.ticker, h, key)
    assert sizes == {MAIN: 97, ZERO: 97, PB: 99}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
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


def test_6b_predict_path_imports_are_stdlib_plus_hazard_features_survival(built, tmp_path):
    own = _imports(ROOT / "borsai" / "predict_path.py")
    assert {i for i in own if i.startswith(".")} == {".predict_hazard", ".survival", ".features"}
    assert {i for i in own if not i.startswith(".")} <= STDLIB_ALLOWED
    pkg = ROOT / "borsai"
    seen, queue, closure = set(), ["predict_path"], {}
    while queue:
        mod = queue.pop()
        if mod in seen:
            continue
        seen.add(mod)
        imps = _imports(pkg / f"{mod}.py")
        closure[mod] = imps
        queue += [i[1:] for i in imps if i.startswith(".")]
    assert {i for v in closure.values() for i in v if not i.startswith(".")} <= STDLIB_ALLOWED, closure
    assert set(closure) <= {"predict_path", "predict_hazard", "features", "survival", "predict", "horizons"}
    for m in FAZ4_MODEL_IDS:
        (tmp_path / f"{m}.json").write_bytes(pretty_json_bytes(built[m]))
    code = ("import json, sys\nimport borsai.predict_path as p\n"
            f"load = lambda m: json.load(open({str(tmp_path)!r} + f'/{{m}}.json', encoding='utf-8'))\n"
            f"v15 = {V15_INPUTS!r}\npbin = {PB_INPUTS!r}\n"
            "assert p.predict(load('ceiling_path_v0'), v15)['refused'] is None\n"
            "assert p.predict(load('ceiling_path_v0@INF'), v15)['refused'] is None\n"
            "assert p.predict(load('pb_ceiling_path_v0'), pbin)['refused'] is None\n"
            "print(json.dumps(sorted(m for m in sys.modules if m.split('.')[0] in "
            "('numpy', 'sklearn', 'scipy', 'joblib', 'threadpoolctl', 'narwhals'))))\n")
    res = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert json.loads(res.stdout) == []


# ---------------------------------------------------------------- §9-7 koşullu formül (sentetik)

def test_7_conditional_update_synthetic(built):
    params = built[MAIN]
    out = pth.predict(params, V15_INPUTS)
    # j = 0 -> koşulsuzla bit-eşit
    c0 = pth.conditional(params, out, 0, [])
    for h in range(1, 11):
        a, b = out[f"D{h}"], c0[f"D{h}"]
        assert {k: a[k] for k in a} == {k: b[k] for k in a}, h
    rng = random.Random(7)
    for _ in range(50):
        hz = [rng.uniform(0.01, 0.6) for _ in range(10)]
        S = sv.survival(hz)
        for j in range(0, 10):
            s_cond, pl_cond = pth.conditional_weights(S, j)
            for k in range(j + 1, 11):
                assert abs(s_cond[k] - math.prod(1 - hz[d - 1] for d in range(j + 1, k + 1))) <= 1e-12
            assert abs(sum(pl_cond.values()) - 1.0) <= 1e-12
            fake = {**out, "S": S}
            obs = out["limit_path"]["C"][:j]
            c = pth.conditional(params, fake, j, obs)
            assert c["limit_path_mismatch"] == 0
            for h in range(1, 11):
                d = c[f"D{h}"]
                if h <= j:
                    assert d["status"] == pth.STATUS_REALIZED and "return" not in d
                    continue
                parts = [(t, pl_cond[t], None if t == 0 else pth.ratio(Decimal(out["limit_path"]["C"][t - 1]),
                                                                      Decimal(out["limit_path"]["ipo_price"])))
                         for t in range(j, h)]
                atoms, _, ok = pth.mixture_atoms((out["limit_path"]["rho"][h - 1], s_cond[h]), parts, pth.cells_of(params), h)
                assert ok and abs(sum(w for _, w in atoms) - 1.0) <= 1e-12 and d["return"] is not None
    # gözlenen kapanış C_t'den farklıysa limit_path_mismatch = 1
    bad = [str(Decimal(out["limit_path"]["C"][0]) - Decimal("0.02"))]
    assert pth.conditional(params, out, 1, bad)["limit_path_mismatch"] == 1
    # durum 2: S kısmı yok, ağırlık toplamı 1
    for t in range(0, 10):
        obs = out["limit_path"]["C"][:t] + ["20.00"]
        c2 = pth.conditional_after_break(params, out, t, obs)
        for h in range(1, 11):
            d = c2[f"D{h}"]
            if h <= t + 1:
                assert d["status"] == pth.STATUS_REALIZED
                continue
            assert d["S_h"] is None and d["limit_path_return"] is None
            scale = None if t == 0 else pth.ratio(Decimal(obs[t - 1]), Decimal(out["limit_path"]["ipo_price"]))
            atoms, _, ok = pth.mixture_atoms(None, [(t, 1.0, scale)], pth.cells_of(params), h)
            assert ok and abs(sum(w for _, w in atoms) - 1.0) <= 1e-12
    # koşullu RPS_j: S ≡ 1[L ≥ k] -> 0; her zaman tavan ve L = j -> 1
    for L in range(1, 11):
        perfect = [1.0 if L >= k else 0.0 for k in range(1, 11)]
        for j in range(1, min(L, 9) + 1):
            assert pth.conditional_rps(perfect, j, L) == 0.0
    for j in range(1, 10):
        assert pth.conditional_rps([1.0] * 10, j, j) == 1.0
        assert pth.conditional_brier([1.0] * 10, j, j, j + 1) == 1.0
    with pytest.raises(ValueError):
        pth.conditional_rps([1.0] * 10, 3, 2)


# ---------------------------------------------------------------- §9-8 walk-forward sızıntı

def test_8_walk_forward_leakage_and_first_fold(ledgers, dataset, full_cells):
    pb = load_pb(dataset)
    for m, led in ledgers.items():
        assert len(led) == 87 and all(r["status"] == cp.STATUS_OK for r in led)
        for r in led:
            assert r["cells_max_session_date"] < r["prediction_date"]
            assert all(r[f"D{h}_post_break_status"] == pth.STATUS_OK for h in range(1, 11))
            if m == PB:
                assert r["prediction_date"] == pb[r["ticker"]].first_bookbuilding_date
            else:
                assert r["prediction_date"] == r["first_trading_date"]
    first = ledgers[MAIN][0]
    assert first["ticker"] == "EKOS" and first["prediction_date"] == "2023-11-21"
    assert [first[f"cells_n_Z_{m}"] for m in range(1, 11)] == [0] * 10
    assert [first[f"cells_n_B_{m}"] for m in range(1, 10)] == [6, 6, 5, 4, 3, 2, 0, 0, 0]
    units = cp.path_units(dataset.rows)
    cells, _ = pth.build_cells(units, cutoff="2023-11-21")
    pc = pth.pool(cells, "B", 1)
    assert set(pc.sources) == {("B", 1), ("Z", 1), ("B", 2), ("Z", 2)} and pc.n == 12 and pc.pooled
    # sentetik: seri T'den 2 seans önce bitmiş (D_t = T − 2 seans), kırılma günü D_{t+1} T'den önceki son seans -> 1 gözlem
    dates = ("2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08", "2024-01-09", "2024-01-10",
             "2024-01-11", "2024-01-12", "2024-01-15")
    closes = tuple(Decimal(x) for x in ("11", "12.10", "13.31", "12.00", "12.5", "12.4", "12.3", "12.2", "12.1", "12.0"))
    syn = pth.PathUnit("SYNT", "2024-01-02", 3, Decimal("10"), closes, dates)
    c, info = pth.build_cells([syn], cutoff="2024-01-08")
    assert sum(len(v) for v in c.values()) == 1 and c[("B", 1)] == [(pth.ratio_minus_one(closes[3], closes[2]), "SYNT")]
    assert info["max_session_date"] == "2024-01-05"
    c, _ = pth.build_cells([syn], cutoff="2024-01-05")   # kırılma günü kesimde: seri hâlâ sürüyor sayılır
    assert sum(len(v) for v in c.values()) == 0


# ---------------------------------------------------------------- §9-9 havuzlama determinizmi

def test_9_pooling_determinism_and_clipping_only_when_pooled(dataset, ledgers, built):
    units = cp.path_units(dataset.rows)
    for m, led in ledgers.items():
        for r in led:
            a, _ = pth.build_cells(units, cutoff=r["prediction_date"])
            b, _ = pth.build_cells(units, cutoff=r["prediction_date"])
            assert a == b
            for g in pth.GROUPS:
                for mm in range(1, pth.M_MAX[g] + 1):
                    p1, p2 = pth.pool(a, g, mm), pth.pool(b, g, mm)
                    assert p1 == p2
                    if not p1.pooled:
                        assert p1.n_clipped == 0
                    lo, hi = pth.physical_bounds(mm)
                    for v, origin, (raw, _) in zip(p1.values, p1.origins, [x for k in p1.sources for x in a[k]]):
                        if origin[1] == mm:           # hedef m'nin kendi gözlemi: kırpma yok
                            assert v == raw
                        assert lo <= v <= hi
    for mid in FAZ4_MODEL_IDS:
        assert built[mid]["post_break"]["N_MIN"] == 10 == pth.N_MIN


# ---------------------------------------------------------------- §9-10 fold kümesi

def test_10_fold_sets_equal_source_ledgers(ledgers):
    for m, led in ledgers.items():
        spec = MODEL_SPECS[m]
        src, sha = cp.read_source_ledger(spec)
        assert sha == sha256_file(ROOT / spec["survival_ledger"]["path"]) == spec["survival_ledger"]["sha256"]
        assert [(r["fold_id"], r["ticker"]) for r in led] == [(s["fold_id"], s["ticker"]) for s in src]
        assert all(r["survival_ledger_sha256"] == sha and r["survival_model_id"] == spec["survival_model_id"] for r in led)
        for r, s in zip(led, src):
            assert [r[f"S_{k}"] for k in range(1, 11)] == [float(s[f"S_{k}"]) for k in range(1, 11)]
    assert [r["ticker"] for r in ledgers[MAIN]] == [r["ticker"] for r in ledgers[ZERO]]


# ---------------------------------------------------------------- §9-11 ret ve uyarı

def test_11_refusals_and_warnings(built):
    main, zero, pbm = built[MAIN], built[ZERO], built[PB]
    no_f3 = {**V15_INPUTS, "total_demand_multiple": None}
    out = pth.predict(main, no_f3)
    assert out["refused"]["code"] == "F3_MISSING"
    assert all(out[k] is None for k in ("S", "P_L", "hazard", "limit_path", *pth.HORIZON_KEYS))
    z = pth.predict(zero, no_f3)
    assert z["refused"] is None and z["D5"]["return"] is not None
    for field in ("planned_base_offer_shares", "ipo_price_try"):
        p = pth.predict(pbm, {**PB_INPUTS, field: None})
        assert p["refused"]["code"] == "PB_FIELD_MISSING" and p["refused"]["field"] == field
    assert pth.predict(pbm, {**PB_INPUTS, "total_demand_multiple": None})["refused"] is None   # f3 istemez
    w = pth.predict(main, {**V15_INPUTS, "ipo_price_tl": "25.29"})
    assert w["refused"] is None and w["limit_path"]["snapped_ipo_price"] == "25.30"
    assert [x["code"] for x in w["warnings"]].count(pth.WARN_IPO_PRICE_NOT_ON_TICK_GRID) == 1
    assert pth.predict(zero, {"ipo_price_tl": "25.29"})["limit_path"]["snapped_ipo_price"] == "25.30"
    assert pth.predict(zero, {})["refused"]["code"] == "INPUT_MISSING"   # limit yolu fiyatsız kurulamaz (SPEC_DEVIATIONS F2)
    with pytest.raises(pth.PredictError):
        pth.predict({**main, "limit_path": {**main["limit_path"], "margin": "0.20"}}, V15_INPUTS)


# ---------------------------------------------------------------- §9-12 günlük ve bekçiler

@pytest.mark.requires_git_history
def test_12_log_lines_and_guards(dataset, tmp_path, built):
    log = tmp_path / "log.jsonl"
    for m in FAZ4_MODEL_IDS:
        before = log.read_text(encoding="utf-8").count("\n") if log.exists() else 0
        res = bt.run_backtest(m, dataset, log_path=log, context="pytest")
        lines = log.read_text(encoding="utf-8").splitlines()
        assert len(lines) == before + 1
        e = json.loads(lines[-1])
        spec = MODEL_SPECS[m]
        assert e["kind"] == "backtest" and e["model_id"] == m and e["plan_id"] == spec["plan_id"]
        assert e["spec_sha256"] == spec_sha256(spec) and e["ledger_sha256"] == sha256_bytes(res.ledger_csv)
        assert e["spec_document"] == SPEC_DOCUMENTS_FAZ4["SPEC_CEILING_PATH_V0"]["path"]
        assert e["spec_document_sha256"] == SPEC_DOCUMENTS_FAZ4["SPEC_CEILING_PATH_V0"]["sha256"]
        assert e["survival_ledger_sha256"] == spec["survival_ledger"]["sha256"] and e["data_version_sha256"] == dataset.data_version_sha256
        assert set(e["metrics"]) >= set(HORIZONS) and e["folds_scorable"] == {"CEILING_PATH": 87}
    with pytest.raises(bt.BacktestStop):
        bt.run_backtest(MAIN, dataset, log_path=log, context="pytest", plan_id=PLAN_PB_CEILING_PATH)
    # şartname belgeleri: docs/specs 11 dosya ve temiz; docs/specs_faz4 uygulamadan önceki commit'le bayt eşit
    assert _git("status", "--porcelain", "--untracked-files=all", "--", "docs/specs", "docs/specs_faz4") == ""
    assert len([p for p in (ROOT / "docs" / "specs").rglob("*") if p.is_file()]) == 11
    for p in (ROOT / "docs" / "specs_faz4").rglob("*"):
        if p.is_file():
            rel = p.relative_to(ROOT).as_posix()
            assert p.read_bytes() == _git_bytes(SPEC_COMMIT, rel), rel
    assert sha256_file(ROOT / SPEC_DOCUMENTS_FAZ4["SPEC_CEILING_PATH_V0"]["path"]) == SPEC_DOCUMENTS_FAZ4["SPEC_CEILING_PATH_V0"]["sha256"]
    # Faz 1B altın ledger'ları ve Faz 1 model dosyaları bayt eşit (Faz 1A olanlar tests/test_faz1b_guardrails.py'de)
    for name in _git("ls-tree", "--name-only", FAZ1B_COMMIT, "tests/reference/macos_golden_faz1b/").split():
        assert (ROOT / name).read_bytes() == _git_bytes(FAZ1B_COMMIT, name), name
    old_index = json.loads(_git_bytes(SCORES_COMMIT, "models/INDEX.json"))["models"]
    new_index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]
    assert [e["model_id"] for e in old_index] == list(FAZ1A_MODEL_IDS + FAZ1B_MODEL_IDS)
    assert new_index[:16] == old_index   # ilk 16 kayıt aynen (Faz 4 dondurulmadı: bkz. test_freeze_decision_…)
    for e in old_index:
        assert (ROOT / "models" / e["file"]).read_bytes() == _git_bytes(SCORES_COMMIT, f"models/{e['file']}"), e["model_id"]
    # 2026-08-19 sonrası veri yok
    for m in FAZ4_MODEL_IDS:
        p = built[m]
        assert p["post_break"]["max_session_date"] <= OUTCOME_CUTOFF and p["training"]["cutoff_date"] <= OUTCOME_CUTOFF
        assert p["post_break"]["cutoff_date"] == OUTCOME_CUTOFF


# ---------------------------------------------------------------- §9-13 kayıt uyumu

def _synthetic_inputs(tmp_path, ticker, **field_values):
    doc = copy.deepcopy(reg.load_inputs(reg.INPUTS_DIR / f"{ticker}.json")[0])
    for name, value in field_values.items():
        doc["fields"][name]["value"] = value
        if value is None:
            doc["fields"][name]["missing_reason"] = "test"
    p = tmp_path / f"{ticker}_synthetic.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.mark.requires_raw_sources
def test_13_record_contains_new_models_and_scoring_reads_them(tmp_path, dataset):
    models_dir = ROOT / "models"   # üç model donduruldu; kayıt yolu repo'daki dosyaları okur
    index = json.loads((models_dir / "INDEX.json").read_text(encoding="utf-8"))
    ids = [e["model_id"] for e in index["models"]]
    # Faz 7 (ve Faz 7C) dondurmasından sonra INDEX'in sonunda dört v1 (ve dört (C)) girişi daha vardır (ilk 19 aynen;
    # tests/faz7_support.py: frozen_tail_ids)
    assert len(ids) == 19 + len(fs7.frozen_tail_ids()) and ids[16:19] == list(FAZ4_MODEL_IDS)
    assert index["models"][:16] == json.loads(_git_bytes(SCORES_COMMIT, "models/INDEX.json"))["models"]
    rec = fz.build_record(_synthetic_inputs(tmp_path, "CITAS", first_trading_date="2026-09-30"), now=NOW, models_dir=models_dir)
    assert [c["model_id"] for c in rec["models"]] == ids and rec["summary"]["n_models"] == len(ids)
    cells = {c["model_id"]: c for c in rec["models"]}
    for m in FAZ4_MODEL_IDS:
        c = cells[m]
        e = next(x for x in index["models"] if x["model_id"] == m)
        assert c["kind"] == "ceiling_path" and c["status"] == fz.STATUS_PREDICTED
        assert c["params_sha256"] == e["sha256"] == sha256_file(models_dir / e["file"]) and c["spec_sha256"] == e["spec_sha256"]
        pred = sc.prediction_of_cell(c)
        assert set(pred) == set(HORIZONS)
        for h in HORIZONS:
            assert pred[h] == {"return": c["output"][h]["return"], "p_up": c["output"][h]["p_up"]}
            assert pred[h]["return"] is not None and 0.0 <= pred[h]["p_up"] <= 1.0
        assert [c["output"][f"D{h}"]["S_h"] for h in range(1, 11)] == c["output"]["S"]
    veyas = fz.build_record(_synthetic_inputs(tmp_path, "CITAS", first_trading_date="2026-09-30", total_demand_multiple=None),
                            now=NOW, models_dir=models_dir)
    ref = {c["model_id"]: c for c in veyas["models"]}
    assert ref[MAIN]["status"] == fz.STATUS_REFUSED and sc.prediction_of_cell(ref[MAIN]) == {"refused": ref[MAIN]["refusal"]}
    assert ref[ZERO]["status"] == ref[PB]["status"] == fz.STATUS_PREDICTED


def test_13b_f3_models_are_exactly_the_models_that_refuse_without_f3():
    """SPEC_SCORING §6 (birincil kayıt): kayıtlı modellerde f3 isteyen modeller listesi, f3'süz girdiyi reddeden modellerle
    aynı. `ceiling_path_v0` donduruldu ve f3'süz reddediyor: `registry.F3_MODELS`'e eklendi (SPEC_DEVIATIONS F9, F13);
    sıfır model ve PB varyantı reddetmez (en erken kayıt kuralı)."""
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
    inputs = {**V15_INPUTS, **PB_INPUTS, "total_demand_multiple": None, "f6_market20": "0.01"}
    out = {e["model_id"]: fz.run_model(json.loads((ROOT / "models" / e["file"]).read_text(encoding="utf-8")), inputs)
           for e in index["models"]}
    refusing = {m for m, o in out.items() if o["status"] == fz.STATUS_REFUSED and o["refusal"]["code"] == "F3_MISSING"}
    # F3_MODELS Faz 7'nin ve Faz 7C'nin f3 isteyen adaylarını da adıyla taşır; INDEX'te olmayan ad etkisizdir (SPEC_DEVIATIONS
    # J24, K16): Faz 7C dondurmasından önce yalnız iki (C) adı INDEX dışında kalır
    assert refusing == set(reg.F3_MODELS) & set(out) and MAIN in refusing
    assert set(reg.F3_MODELS) - set(out) <= {"ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled",
                                             "fall_d10_v0_h99", "fall_d10_v0_pooled"}
    assert out[ZERO]["status"] == out[PB]["status"] == fz.STATUS_PREDICTED
    assert {ZERO, PB} & set(reg.F3_MODELS) == set()


# ---------------------------------------------------------------- altın ledger'lar ve dondurulmuş JSON

def test_backtest_byte_identical_to_faz4_golden(backtest_results):
    manifest = json.loads((bt.GOLDEN_FAZ4_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    sums = (bt.GOLDEN_FAZ4_DIR / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert sorted(manifest["runs"]) == sorted(FAZ4_MODEL_IDS) and len(sums) == 3
    for line in sums:
        sha, name = line.split("  ")
        assert sha256_file(bt.GOLDEN_FAZ4_DIR / name) == sha
    for m, p in bt.FAZ4_RUNS:
        info = manifest["runs"][m]
        assert (info["model_id"], info["plan_id"], info["spec_sha256"]) == (m, p, spec_sha256(MODEL_SPECS[m]))
        golden = (bt.GOLDEN_FAZ4_DIR / info["file"]).read_bytes()
        assert backtest_results[m].ledger_csv == golden, m
        assert sha256_bytes(golden) == info["ledger_sha256"]


def test_official_log_has_faz4_runs_and_one_conditional_eval():
    entries = [json.loads(x) for x in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    manifest = json.loads((bt.GOLDEN_FAZ4_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    for m, info in manifest["runs"].items():
        hits = [e for e in entries if e.get("model_id") == m and e["kind"] == "backtest"]
        assert {e["context"] for e in hits} == {"faz4_acceptance_run", "faz4_golden"}, m
        assert all(e["ledger_sha256"] == info["ledger_sha256"] for e in hits), m
    cond = [e for e in entries if e["kind"] == "conditional_eval"]
    assert len(cond) == 1 and cond[0]["model_id"] is None
    from borsai.report_faz1b import load_runs

    assert cond[0]["metrics"] == json.loads(json.dumps(cp.conditional_eval(load_runs())))
    assert {x["run_key"] for x in cond[0]["evaluated"]} == {k for key, comps in cp.CONDITIONAL_RUNS.values() for k in (key, *comps)}


def test_would_be_frozen_json_fields(dataset, full_cells, built):
    """Şartname §4'ün model JSON alanları (dondurma yolunun ürettiği parametreler)."""
    cells, info = full_cells
    for m in FAZ4_MODEL_IDS:
        p = built[m]
        e = fz.index_entry(p, f"{m}.json", sha256_bytes(pretty_json_bytes(p)))
        assert p["algorithm"] == pth.ALGORITHM and p["schema_version"] == "borsai.model/1"
        assert p["spec_sha256"] == spec_sha256(MODEL_SPECS[m]) == e["spec_sha256"]
        assert p["spec"]["spec_document"] == SPEC_DOCUMENTS_FAZ4["SPEC_CEILING_PATH_V0"]
        assert set(p["horizons"]) == set(pth.HORIZON_KEYS)
        assert all(p["horizons"][k] == {"return": {"kind": "mixture_median"}, "p_up": {"kind": "mixture_p_up"}} for k in pth.HORIZON_KEYS)
        lp = p["limit_path"]
        assert (lp["margin"], lp["tick_table"], lp["upper_rounding"], lp["d1_base"]) == ("0.10", pth.tick_table_json(),
                                                                                       "FLOOR_TO_TICK_AT_LIMIT_LEVEL", "HALF_UP_TO_TICK")
        assert lp["rule_source"]["page_sha256"] == "af1976338cc311b0cbdd5d89384d82cf97690e9feafd739a287fe4e8ec34cfa5"
        assert lp["price_field"] == ("ipo_price_try" if m == PB else "ipo_price_tl")
        pb_ = p["post_break"]
        assert pb_["groups"] == ["Z", "B"] and pb_["n_ipo"] == 99 and pb_["n_obs"] == 567
        assert pb_["ipos_sha256"] == identity_hash([r.ticker for r in dataset.rows]) and pb_["cutoff_date"] == OUTCOME_CUTOFF
        assert pth.cells_from_json(pb_["cells"]) == cells
        tr = p["training"]
        assert tr["set"] == "H99_ALL_ROWS" and tr["n"] == 99 == e["training_n"] and tr["cutoff_date"] == OUTCOME_CUTOFF
        assert p["survival_training"] == p["survival_model"]["training"]
        assert p["quantile_rule"] == MODEL_SPECS[m]["quantile_rule"]
        assert set(p["spec"]["limit_path"]) >= {"margin", "tick_table", "rule_source", "price_field"}


def test_final_freeze_is_reproducible(dataset, built):
    from borsai.fit import fit

    for m in FAZ4_MODEL_IDS:
        fresh = json.loads(pretty_json_bytes(fit(MODEL_SPECS[m], list(dataset.rows), dataset_version=dataset.data_version_sha256)))
        old = built[m]
        assert {k: v for k, v in fresh.items() if k not in ("created_at", "code_version")} == \
            {k: v for k, v in old.items() if k not in ("created_at", "code_version")}


def test_frozen_files_match_the_freeze_path(built):
    """models/ altındaki üç dosya, dondurma yolunun bugün ürettiğiyle aynı (üretim zamanı ve kod damgası dışında);
    INDEX kaydı dosyanın sha256'sı ve alanlarıyla tutarlı; dondurma temiz ağaçta yapıldı (`borsai_dirty` false)."""
    index = {e["model_id"]: e for e in json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]}
    for m in FAZ4_MODEL_IDS:
        e = index[m]
        raw = (ROOT / "models" / e["file"]).read_bytes()
        frozen = json.loads(raw)
        assert e["file"] == f"{m}.json" and e["sha256"] == sha256_bytes(raw) and e["status"] == "FROZEN"
        assert fz.index_entry(frozen, e["file"], e["sha256"]) == e
        assert {k: v for k, v in frozen.items() if k not in ("created_at", "code_version")} == \
            {k: v for k, v in built[m].items() if k not in ("created_at", "code_version")}
        assert frozen["code_version"]["borsai_dirty"] is False
        assert frozen["survival_model_sha256"] == index[frozen["survival_model_id"]]["sha256"]
        assert sha256_bytes(pretty_json_bytes(frozen["survival_model"])) == frozen["survival_model_sha256"]


# ---------------------------------------------------------------- scores.json: Faz 1 blokları değişmedi

def _stable_block(m: dict) -> dict:
    """f1f9d44'teki hâliyle karşılaştırma: sonuç commit'ine ve günlüğe bağlı alanlar dışarıda.
    - class_evidence.outcome_ingest_{commit,basis}, checked_against: f1f9d44'te sonuçlar henüz commit edilmemişti
      (HEAD'e karşı denetlendi, SPEC_DEVIATIONS E15); şimdi sonuç commit'i f1f9d44'tür. Sınıf aynıdır (ayrıca sınanır).
    - card.n_variants_same_data: aynı veri sürümünde denenen (model_id, spec) sayısı veri geneli bir sayaçtır (E16);
      Faz 4'ün üç yeni modeli onu 16'dan 19'a çıkarır. Değeri ayrıca günlükten sınanır.
    - conditional: Faz 2C'nin yeni bloğu (SPEC_DEVIATIONS G); tests/test_scoring_conditional.py sınar."""
    m = json.loads(json.dumps(m))
    m["card"].pop("n_variants_same_data")
    m.pop("conditional", None)
    for r in m["live"]["rows"] + m["live"]["self_reported_rows"]:
        for k in ("outcome_ingest_commit", "checked_against", "outcome_ingest_basis"):
            r["class_evidence"].pop(k)
    return m


# Sonuç ilerlemesi kuralı (SPEC_DEVIATIONS M24; BORSAI_LIVE_NETGL_D10): f1f9d44'te var olan arzların sonuçları ilerleyebilir
# (PENDING -> dolu); dondurulmuş her şey ve f1f9d44'te PENDING olmayan her ufuk aynen kalır. Genel kuraldır, bir arza özel değildir.
# Yeni bir arz (yeni ticker) kırmızı kalır: o ayrı karar.
PROGRESS_PENDING = "PENDING"
# live bloğunda sonuç ilerleyince değişebilen türev sayaçlar; öbür n_* (n_live, n_late, n_refused, n_rows, n_skipped) sınıf ve satır
# sayısıdır, sonuç ilerlemesiyle değişmez
PROGRESS_COUNTERS = {"n_pending", "n_partial_pending", "n_scored", "n_target_unavailable", "n_self_reported_scored"}
PROGRESS_LIST_FIELDS = ("ceiling_close", "half_day", "halt_flag", "row_status", "sessions", "shifted_by_suspension")


def _realized_progress_problems(old: dict, new: dict) -> list[str]:
    """`realized` bloğu: f1f9d44'te PENDING olmayan her ufuk aynen; yalnız PENDING -> dolu serbest. Yalnız alan adı döner."""
    out: list[str] = []
    if old.get("d1") != new.get("d1"):
        out.append("d1")
    status = old["row_status"]
    for key in PROGRESS_LIST_FIELDS:
        if len(old[key]) != len(new[key]):
            out.append(f"{key} uzunluk")
        out += [f"{key}[{i}]" for i, (a, b) in enumerate(zip(old[key], new[key])) if status[i] != PROGRESS_PENDING and a != b]
    for key in ("R", "Y"):
        if set(old[key]) != set(new[key]):
            out.append(f"{key} anahtarlar")
        out += [f"{key}.{h}" for h, a in old[key].items() if a is not None and new[key].get(h) != a]
    if old["L_status"] != PROGRESS_PENDING and (old["L"], old["L_status"]) != (new["L"], new["L_status"]):
        out.append("L")
    return out


def _targets_progress_problems(old: dict, new: dict) -> list[str]:
    out = [] if set(old) == set(new) else ["targets anahtarlar"]
    return out + [f"targets.{k}" for k, v in old.items() if v != PROGRESS_PENDING and new.get(k) != v]


def faz1_progress_problems(old: dict, new: dict) -> list[str]:
    """f1f9d44 scores.json (`old`) -> `new` (SPEC_DEVIATIONS M24). Eşit kalır: model listesi ve sırası; her satırın prediction, class,
    record_id, rules ve öbür alanları; backtest ve kart (n_variants hariç, `_stable_block`); separate_models, skipped, definitions,
    schema_version; inputs.records_sha256; `outcomes`'ta aynı arzlar aynı sırada. İlerleyebilir: sonucu ilerleyen satırların
    realized/targets alanları (yalnız PENDING -> dolu), PROGRESS_COUNTERS, as_of_session (eskisinden küçük olamaz),
    inputs.outcomes_sha256. Mesajlar değer değil yalnız alan adı taşır."""
    out: list[str] = []
    old_models = {m["model_id"]: m for m in old["models"]}
    new_models = {m["model_id"]: m for m in new["models"]}
    if list(new_models)[:len(old_models)] != list(old_models):
        out.append("model listesi/sırası")
    for mid, m_old in old_models.items():
        if mid not in new_models:
            continue
        a, b = _stable_block(m_old), _stable_block(new_models[mid])
        out += [f"{mid}: {key}" for key in ("backtest", "card", "kind", "model_id", "primary_cell") if a[key] != b[key]]
        live_a, live_b = a["live"], b["live"]
        out += [f"{mid}: live.{key}" for key in sorted(set(live_a) | set(live_b))
                if key not in ("rows", "self_reported_rows") and key not in PROGRESS_COUNTERS and live_a.get(key) != live_b.get(key)]
        for which in ("rows", "self_reported_rows"):
            if [r["ticker"] for r in live_a[which]] != [r["ticker"] for r in live_b[which]]:
                out.append(f"{mid}: live.{which} satırları")
                continue
            for r_a, r_b in zip(live_a[which], live_b[which]):
                tag = f"{mid}/{r_a['ticker']}"
                out += [f"{tag}: {key}" for key in sorted(set(r_a) | set(r_b))
                        if key not in ("realized", "targets") and r_a.get(key) != r_b.get(key)]
                out += [f"{tag}: realized {p}" for p in _realized_progress_problems(r_a["realized"], r_b["realized"])]
                out += [f"{tag}: {p}" for p in _targets_progress_problems(r_a["targets"], r_b["targets"])]
    if [o["ticker"] for o in old["outcomes"]] != [o["ticker"] for o in new["outcomes"]]:
        out.append("outcomes: arz listesi/sırası")
    else:
        for o_a, o_b in zip(old["outcomes"], new["outcomes"]):
            tag = f"outcomes/{o_a['ticker']}"
            out += [f"{tag}: {key}" for key in sorted(set(o_a) | set(o_b)) if key != "realized" and o_a.get(key) != o_b.get(key)]
            out += [f"{tag}: realized {p}" for p in _realized_progress_problems(o_a["realized"], o_b["realized"])]
    out += [key for key in ("separate_models", "skipped", "definitions", "schema_version") if old[key] != new[key]]
    if new["as_of_session"] < old["as_of_session"]:
        out.append("as_of_session geriye gitti")
    if new["inputs"]["records_sha256"] != old["inputs"]["records_sha256"]:
        out.append("inputs.records_sha256")
    return out


@pytest.mark.requires_git_history
def test_faz1_progress_rule_mutations():
    """M24 mutasyonları (bellekteki kopyalar; dosyaya yazılmaz): (a) bir prediction değeri, (b) f1f9d44'te dolu bir ufuk (satırın
    realized'ı, `outcomes`'taki liste ve başka bir arzın ufku), (c) records_sha256, (d) eklenmiş bir ticker -> her biri kırmızı;
    değişmemiş kopya ve bugünkü dosya yeşil; serbest alanlar (outcomes_sha256, ilerleyen sayaç, ileri as_of_session) yeşil kalır."""
    old = json.loads(_git_bytes(SCORES_COMMIT, "scores/scores.json"))
    new = json.loads((ROOT / "scores" / "scores.json").read_text(encoding="utf-8"))
    assert faz1_progress_problems(old, copy.deepcopy(old)) == []
    assert faz1_progress_problems(old, new) == []

    def mutated(fn, base=new):
        m = copy.deepcopy(base)
        fn(m)
        return faz1_progress_problems(old, m)

    def prediction(m):
        r = m["models"][0]["live"]["rows"][0]
        horizon = next(iter(r["prediction"]))
        r["prediction"][horizon]["return"] += 1e-6

    def filled_row_horizon(m):
        row = next(r for r in m["models"][0]["live"]["rows"] if r["ticker"] == "NETGL")
        row["realized"]["R"]["D1"] = "0.3"

    def filled_outcome_list(m):
        next(o for o in m["outcomes"] if o["ticker"] == "NETGL")["realized"]["ceiling_close"][0] = 0

    def filled_other_ticker(m):
        next(o for o in m["outcomes"] if o["ticker"] != "NETGL")["realized"]["row_status"][9] = PROGRESS_PENDING

    def added_ticker(m):
        m["outcomes"].append({**copy.deepcopy(m["outcomes"][0]), "ticker": "ZZZZZ"})

    assert mutated(prediction) != []
    assert mutated(filled_row_horizon) != []
    assert mutated(filled_outcome_list) != []
    assert mutated(filled_other_ticker) != []
    assert mutated(lambda m: m["inputs"].__setitem__("records_sha256", "0" * 64)) == ["inputs.records_sha256"]
    assert mutated(added_ticker) == ["outcomes: arz listesi/sırası"]
    assert mutated(lambda m: m.__setitem__("as_of_session", "2026-09-01")) == ["as_of_session geriye gitti"]
    assert mutated(lambda m: m["models"][0]["live"].__setitem__("n_live", 5)) == [f"{new['models'][0]['model_id']}: live.n_live"]
    assert mutated(lambda m: m["definitions"].__setitem__("x", 1)) == ["definitions"]
    assert mutated(lambda m: m["inputs"].__setitem__("outcomes_sha256", "1" * 64)) == []
    assert mutated(lambda m: m["models"][0]["live"].__setitem__("n_pending", 3)) == []
    assert mutated(lambda m: m.__setitem__("as_of_session", "2099-12-31")) == []


@pytest.mark.requires_git_history
def test_scores_json_faz1_blocks_unchanged_since_f1f9d44():
    old = json.loads(_git_bytes(SCORES_COMMIT, "scores/scores.json"))
    new = json.loads((ROOT / "scores" / "scores.json").read_text(encoding="utf-8"))
    old_models = {m["model_id"]: m for m in old["models"]}
    new_models = {m["model_id"]: m for m in new["models"]}
    assert list(old_models) == list(FAZ1A_MODEL_IDS + FAZ1B_MODEL_IDS)
    # Faz 4 sona eklendi; skorlar 27 modelle yeniden üretilince (BORSAI_FAZ7_OOT_RECORDS, SPEC_DEVIATIONS L) ardından dondurulmuş
    # Faz 7/7C kartları (8e3a623 durumunda, J30, yoklar)
    tail = [] if fs7.scores_json_is_pre_faz7() else fs7.frozen_tail_ids()
    assert list(new_models) == list(FAZ1A_MODEL_IDS + FAZ1B_MODEL_IDS + FAZ4_MODEL_IDS) + tail
    f1f9 = _git("rev-parse", SCORES_COMMIT).strip()
    dv = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"][0]["data_version_sha256"]
    # f1f9d44'te var olan arzların sonuçları ilerleyebilir (PENDING -> dolu); dondurulmuş her şey aynen (SPEC_DEVIATIONS M24)
    assert faz1_progress_problems(old, new) == []
    for mid in old_models:
        for r_old, r_new in zip(old_models[mid]["live"]["rows"], new_models[mid]["live"]["rows"]):
            assert r_new["class"] == r_old["class"]
            assert r_old["class_evidence"]["outcome_ingest_basis"] == "UNCOMMITTED_CHECKED_AGAINST_HEAD"
            assert r_new["class_evidence"]["outcome_ingest_commit"] == f1f9
        assert old_models[mid]["card"]["n_variants_same_data"] == 16
        # Faz 5 (SPEC_DEVIATIONS H22): POST_D1 modelinin backtest satırı sayacı artırır; scores.json o görevde yeniden üretilmedi.
        # İstisna yalnız dosya 72a000f'deki haliyle bayt-eşitken (19); yeniden üretilen scores.json günlükle tam eşittir (20; H44).
        lag = fs.faz5_variants(dv) if fs.scores_json_is_pre_faz5() else 0
        # Faz 7 (SPEC_DEVIATIONS J): aynı kalıp; scores.json 8e3a623'teki haliyle kaldıkça fark tam Faz 7 varyant sayısı kadardır.
        lag7 = fs7.faz7_variants(dv) if fs7.scores_json_is_pre_faz7() else 0
        # Faz 7C (SPEC_DEVIATIONS K; aynı kalıp): fall_d10_v0_h99'un backtest satırı H99 veri sürümünde sayacı 1 artırır (keşif
        # satırları v2 veri sürümündedir); scores.json 8e3a623'teki haliyle kaldıkça fark tam Faz 7C varyant sayısı kadardır.
        lag7c = fs7c.faz7c_variants(dv) if fs7.scores_json_is_pre_faz7() else 0
        # Faz 8 (SPEC_DEVIATIONS N19; proje sahibi kararı 2026-10-01; J16/K10 kalıbı): break_floor_v0'ın backtest satırı H99 sürümünde sayacı 1
        # artırır; scores.json 87434ff'teki haliyle kaldıkça fark tam Faz 8 varyant sayısı kadardır.
        lag8 = fs8.faz8_variants(dv) if fs8.scores_json_is_pre_faz8() else 0
        assert new_models[mid]["card"]["n_variants_same_data"] == sc._n_variants_same_data(dv, mid)[0] - lag - lag7 - lag7c - lag8 == \
            19 + (lag == 0) + (0 if fs7.scores_json_is_pre_faz7() else fs7.faz7_variants(dv) + fs7c.faz7c_variants(dv)) + \
            (0 if fs8.scores_json_is_pre_faz8() else fs8.faz8_variants(dv))
    # retro_info: eski 16 modelin satırları aynen; yeni satırlar yalnız Faz 4 modellerinin ve (skorlar 27 modelle yeniden
    # üretilince; BORSAI_FAZ7_OOT_RECORDS, SPEC_DEVIATIONS L) dondurulmuş Faz 7/7C modellerinindir
    tail = set(fs7.frozen_tail_ids())
    assert [x for x in new["retro_info"] if x["model_id"] not in set(FAZ4_MODEL_IDS) | tail] == old["retro_info"]


def test_new_models_are_retro_with_no_record_and_no_metric():
    """Üç yeni model 7 arzın hepsi için RETRO'dur (kural 3: sonuçlar repoya girdikten sonra donduruldular):
    `retro_info`'da görünürler, canlı n'e girmezler, hiçbir metrik üretmezler ve kayıtları yoktur."""
    new = json.loads((ROOT / "scores" / "scores.json").read_text(encoding="utf-8"))
    scored = [o["ticker"] for o in new["outcomes"]]
    for m in FAZ4_MODEL_IDS:
        block = next(x for x in new["models"] if x["model_id"] == m)["live"]
        assert block["rows"] == [] and block["self_reported_rows"] == [] and block["cells"] == []
        assert (block["n_live"], block["n_late"], block["n_scored"], block["n_refused"]) == (0, 0, 0, 0)
        retro = [x for x in new["retro_info"] if x["model_id"] == m]
        assert [x["ticker"] for x in retro] == scored and len(retro) == 7
        for x in retro:
            assert x["record_id"] is None and x["class_evidence"]["model_prospective"] is False
            assert x["class_evidence"]["basis"].startswith("MODEL_FROZEN_AFTER_OUTCOME_NO_RECORD")
    assert _git("status", "--porcelain", "--untracked-files=all", "--", "registry") == ""
    for p in (ROOT / "registry" / "records").rglob("*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        assert not set(FAZ4_MODEL_IDS) & {c["model_id"] for c in rec.get("models", [])}, p


# ---------------------------------------------------------------- MODELS.md Faz 4 bölümü

def test_expectation_rows_are_read_verbatim_from_spec():
    rows = r4.expectation_rows()
    assert len(rows) == 36
    text = (ROOT / SPEC_DOCUMENTS_FAZ4["SPEC_CEILING_PATH_V0"]["path"]).read_text(encoding="utf-8")
    for r in rows:
        raw = r["raw"]
        assert f"| {raw['ufuk']} | {raw['cikti']} | {raw['karsilastirilan']} | {raw['aralik']} | {raw['sifir']} |" in text
        assert r["lo"] <= r["hi"]
    assert [r for r in rows if r["primary"]] == [r for r in rows if (r["model"], r["horizon"], r["output"], r["comparator"]) ==
                                                 (MAIN, "D5", "MAE", "base_train_median")]
    assert r4.parse_range("\\|fark\\| < 0.001") == (-0.001, 0.001, True)
    assert r4.parse_range("**−0.090 … −0.020**") == (-0.09, -0.02, False)


def test_freeze_decision_follows_too_good_check():
    """§6: "beklentiden çok iyi" tetiklendi; dondurma ancak şartnamenin istediği bağımsız yeniden üretimden sonra
    yapılabilir (ilk uygulamayı görmeyen ayrı oturum, ledger'lar |Δ| ≤ 1e-9). O denetim repodadır ve üç model için
    FREEZE_OK der; üç model bu yüzden dondurulmuştur."""
    from borsai.report_faz1b import load_runs

    tg = r4.too_good(r4.evaluate_expectations(load_runs(), r4.load_faz4_runs()))
    index = {e["model_id"] for e in json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]}
    frozen_now = {m for m in FAZ4_MODEL_IDS if m in index and (ROOT / "models" / f"{m}.json").exists()}
    assert tg["triggered"] and frozen_now == set(FAZ4_MODEL_IDS)
    audit = (ROOT / r4.REPRO["doc"]).read_text(encoding="utf-8")
    for m in FAZ4_MODEL_IDS:
        assert f"| `{m}` | **FREEZE_OK** |" in audit, m
    assert "maks |Δ| = **0.0**" in audit


def test_models_md_faz4_section():
    text = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
    section = text.split("## Faz 4: tavan yolu modelleri")[1]
    for rule in r4.OPERATIONAL_RULES_FAZ4:
        assert rule in section
    for heading in ("### Birincil hücre", "### §6 beklentisi ile gerçekleşen (satır satır)", "### Başarısızlık tanımları (§6)",
                    "### Koşullu güncelleme (keşif): H99, j = 1..9", "### Dondurma"):
        assert heading in section
    assert section.count("| `ceiling_path_v0` | D") >= 32
    for letter in ("(a)", "(b)", "(c)", "(d)"):
        assert f"**{letter}" in section
    assert "**TETİKLENDİ**" in section and "**Dondurulmadı.**" not in section
    assert "**Donduruldu — §6'nın istediği bağımsız yeniden üretimden sonra.**" in section
    assert r4.D10_FOOTNOTE in section and section.count(r4.D10_FOOTNOTE) == 3
    assert f"`{r4.REPRO['dir']}`" in section
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]
    for e in index[16:19]:                      # Faz 4'ün üç modeli (Faz 7 girişleri kendi bölümünde)
        assert f"| `{e['model_id']}` | `{e['sha256'][:12]}` |" in section

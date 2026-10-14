"""Faz 7C model kodu (SPEC_C_V0 §2–§4, §8, §11-1, 2, 3, 4, 5, 9, 12; KARARLAR_C; görev kararları T1, T2). Commit A: gerçek veride
walk-forward skoru ve aday nihai fiti yok; model davranışı sentetik veriyle, veri sayımları, özellik değerleri ve kırpma sınırları
gerçek veriyle sınanır (`@ZERO` = eğitim oranı şartnamede yazılıdır). Gerçek koşu sonuçları tests/test_faz7c_golden.py'de (commit B)."""
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest

from borsai import backtest as bt
from borsai import fit as fitmod
from borsai import predict_fall as pf
from borsai import preprocess as pp
from borsai import registry as reg
from borsai.data import additional_sale_shares, load_dataset, load_dataset_v2, select_fall_training_rows
from borsai.features import FeatureError
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes, sha256_file
from borsai.specs import (DEFLATOR, FAZ7_MODEL_SPECS, FAZ7C_EXPLORATION, FAZ7C_MODEL_IDS, FAZ7C_MODEL_SPECS, H99_DATA_VERSION_SHA256,
                          MODEL_SPECS, POST_D1_MODEL_SPECS, SPEC_DOCUMENTS_FAZ7C, V1_6_H99, V2_DATA_VERSION_SHA256, model_kind,
                          plan_of, spec_sha256)

import faz7_support as fs7
import faz7c_support as f7c

H99, POOLED, ADDSALE, ZERO_ROW = FAZ7C_MODEL_IDS
PRE_FAZ7C_INDEX_COMMIT = "80670cb"      # models/INDEX.json'un Faz 7C dondurmasından önceki son hali (23 giriş; Faz 7 dondurması 66adbca)


@pytest.fixture(scope="module")
def real():
    h = load_dataset()
    v = load_dataset_v2()
    return {"h99": h, "v2": v, "as_h99": additional_sale_shares(h), "as_v2": additional_sale_shares(v)}


def _ds(real, model_id):
    return (real["h99"], real["as_h99"]) if model_id == H99 else (real["v2"], real["as_v2"])


# ---------------------------------------------------------------- §11-1 ek satış bayrağı

@pytest.mark.parametrize("value,expect", [("0", 0), ("35000000", 1), (0, 0), (0.0, 0), ("1", 1), (Decimal("0.5"), 1), (" 0 ", 0)])
def test_additional_sale_flag_values(value, expect):
    assert pf.additional_sale_flag(value) == expect


@pytest.mark.parametrize("value,code", [("", "ADDITIONAL_SALE_MISSING"), (None, "ADDITIONAL_SALE_MISSING"),
                                        ("DATA_NOT_FOUND", "ADDITIONAL_SALE_MISSING"), ("  ", "ADDITIONAL_SALE_MISSING"),
                                        ("-1", "INPUT_NEGATIVE"), ("abc", "INPUT_NOT_NUMERIC"), (True, "INPUT_NOT_NUMERIC")])
def test_additional_sale_flag_refusals(value, code):
    """KARARLAR_C C4: boş alan RET (0 varsayılmaz); negatif INPUT_NEGATIVE (features kalıbı)."""
    with pytest.raises(FeatureError) as exc:
        pf.additional_sale_flag(value)
    assert exc.value.code == code and exc.value.field == "additional_sale_shares"
    assert pf.REFUSED_ADDITIONAL_SALE_MISSING == pf.ADDITIONAL_SALE_MISSING == "ADDITIONAL_SALE_MISSING"


def test_additional_sale_flag_counts_on_real_tables(real):
    """§11-1: bayrak = 1 olan arz H99'da 6 (95 dolu alanda), açık kümede 13 (70); v2'nin H99 satırları training_table.csv ile aynı."""
    h99 = [pf.additional_sale_flag(x) for x in real["as_h99"].values() if x is not None]
    opn = [pf.additional_sale_flag(real["as_v2"][r.ticker]) for r in real["v2"].rows
           if r.cohort == "OOT_OPEN" and real["as_v2"][r.ticker] is not None]
    assert (sum(h99), len(h99), sum(opn), len(opn)) == (6, 95, 13, 70)
    assert {t: real["as_v2"][t] for t in real["as_h99"]} == real["as_h99"]
    assert sum(1 for x in real["as_h99"].values() if x is None) == 4
    assert sum(1 for r in real["v2"].rows if r.cohort == "OOT_OPEN" and real["as_v2"][r.ticker] is None) == 1


# ---------------------------------------------------------------- §11-2 eğitim kümeleri ve tablolar

def test_training_sets_counts_match_spec_and_measured_numbers(real):
    """§11-2 ve görev tablosu: H99_F3_AS_PRESENT 94 (D10 olay 26, D5 18); havuz f3 + ek satış 161 (39, 29); havuz ek satış 165
    (40, 30); kohort sayıları; şartname sözlüğüyle aynı (`backtest.fall_training_rows(check=True)`)."""
    expect = {H99: (94, 26, 18, {"H99": 94, "OOT_OPEN": 0}), POOLED: (161, 39, 29, {"H99": 94, "OOT_OPEN": 67}),
              ADDSALE: (165, 40, 30, {"H99": 95, "OOT_OPEN": 70}), ZERO_ROW: (161, 39, 29, {"H99": 94, "OOT_OPEN": 67})}
    for m, (n, e10, e5, coh) in expect.items():
        ds, a = _ds(real, m)
        spec = FAZ7C_MODEL_SPECS[m]
        rows = bt.fall_training_rows(spec, ds, a, check=True)
        got = (len(rows), sum(r.targets["D10"].Y == 0 for r in rows), sum(r.targets["D5"].Y == 0 for r in rows),
               {c: sum(1 for r in rows if (getattr(r, "cohort", "H99") or "H99") == c) for c in ("H99", "OOT_OPEN")})
        assert got == (n, e10, e5, coh) == (spec["training"]["n"], spec["training"]["events_D10"], spec["training"]["events_D5"],
                                            spec["training"]["cohort_counts"])
        assert [(r.first_trading_date, r.ticker) for r in rows] == sorted((r.first_trading_date, r.ticker) for r in rows)
        assert all(a[r.ticker] is not None for r in rows)
        assert all(r.inputs["total_demand_multiple"] is not None for r in rows) or m == ADDSALE
    assert FAZ7C_MODEL_SPECS[ZERO_ROW]["training"] == FAZ7C_MODEL_SPECS[POOLED]["training"]


def test_tables_and_data_versions_unchanged():
    """§11-2: training_table.csv, training_table_v2.csv ve data_version*.json değişmez (sha'lar sürüm dosyalarıyla ve şartname
    sabitleriyle aynı; data/ çalışma ağacında değişiklik yok)."""
    v1 = json.loads((ROOT / "data" / "data_version.json").read_text(encoding="utf-8"))
    v2 = json.loads((ROOT / "data" / "data_version_v2.json").read_text(encoding="utf-8"))
    assert sha256_file(ROOT / "data" / "training_table.csv") == v1["sha256"]
    assert sha256_file(ROOT / "data" / "training_table_v2.csv") == v2["sha256"]
    assert sha256_file(ROOT / "data" / "data_version.json") == H99_DATA_VERSION_SHA256
    assert sha256_file(ROOT / "data" / "data_version_v2.json") == V2_DATA_VERSION_SHA256
    out = subprocess.run(["git", "status", "--porcelain", "--", "data", "models", "registry", "scores", "legacy"], cwd=ROOT,
                         check=True, capture_output=True, text=True).stdout
    assert out == ""


def test_no_sealed_code_in_training_tables_or_new_files():
    """§11-2 ve §11-12: eğitim tablolarında ve bu görevin yeni dosyalarında kasa kodu yok; bülten adı kalıbı yok. (data/'nın tamamı:
    tests/test_outcome_guard.py::test_cohort_codes_appear_in_data_only_as_outcomes.)"""
    _, cohort = reg.read_cohort()
    sealed = sorted(r["ticker"] for r in reg.cohort_members(cohort) if r["vault"] == reg.VAULT_SEALED)
    n_sealed = len(sealed)                                                          # yerel değişken: hata çıktısı kod basmaz
    assert n_sealed == 64
    pattern = re.compile(r"\b(" + "|".join(sealed) + r")\b")
    paths = [ROOT / "data" / "training_table.csv", ROOT / "data" / "training_table_v2.csv", ROOT / "borsai" / "predict_fall.py",
             ROOT / "borsai" / "report_faz7c.py", ROOT / "tests" / "faz7c_support.py", ROOT / "tests" / "test_faz7c_model.py",
             ROOT / "tests" / "test_faz7c_backtest.py", ROOT / "docs" / "specs_faz7_c" / "KARARLAR_C.md",
             ROOT / "docs" / "prompts" / "FAZ7_C_IMPL.md", *sorted((ROOT / "docs" / "faz7c").rglob("*.*"))]
    for p in paths:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        n = len(set(pattern.findall(text)))
        assert n == 0, (p.name, n)
        assert not re.search(r"th[bm]20\d{6}", text), p.name


@pytest.mark.requires_git_history
def test_kesif_guard_stops_on_closed_code():
    """§11-12: `ekler/kesif_c.py` açık küme dışındaki bir eski kohort kodu istendiğinde durur (sentetik kapalı kod). İki kip
    (SPEC_DEVIATIONS M13): araç açık kümeyi data/outcomes_oot/*.csv adlarından okur ve 71 olduğunu varsayar. Kasa sonuçları repoya
    girdikten sonra (VB; işaret dosyası var, 135 dosya) araç yüklenirken durur ve yalnız sayıyı yazar: keşif aracı kasa üyeleriyle
    hiç çalışmaz. Kasanın sonuç dosyaları yokken iddia aynen."""
    import importlib.util

    from borsai import outcomes_oot as oo

    spec = importlib.util.spec_from_file_location("kesif_c", ROOT / "docs" / "specs_faz7_c" / "ekler" / "kesif_c.py")
    mod = importlib.util.module_from_spec(spec)
    n = len(list((ROOT / "data" / "outcomes_oot").glob("*.csv")))
    if n != 71:
        assert oo.vault_marker_state(ROOT).open_mode and n == 135
        with pytest.raises(AssertionError) as exc:
            spec.loader.exec_module(mod)
        assert str(exc.value) == str(n)
        return
    spec.loader.exec_module(mod)
    assert len(mod.OPEN_SET) == 71
    with pytest.raises(SystemExit) as exc:
        mod._assert_open("ZZZZ9")
    assert "HİJYEN" in str(exc.value) and "ZZZZ9" not in str(exc.value)


# ---------------------------------------------------------------- tarifler, şartname sözlükleri (T1)

def test_recipes_new_and_old_unchanged():
    """§3.2: FALL_V0 (f1r, f3, add_sale; winsor ve log f1r, f3), FALL_V0_ADDSALE (add_sale; winsor/log yok); imputasyon, f5, eksiklik
    düşürmesi yok. Eski tarifler aynen (altın ledger'lar ve legacy paritesi ayrıca bayt-eşit)."""
    r = pp.FALL_V0_RECIPE
    assert (r.substantive, r.winsor, r.log, r.indicator, r.impute, r.missingness_drop) == (
        ("f1r", "f3", "add_sale"), ("f1r", "f3"), ("f1r", "f3"), False, False, False)
    a = pp.FALL_V0_ADDSALE_RECIPE
    assert (a.substantive, a.winsor, a.log, a.indicator, a.impute) == (("add_sale",), (), (), False, False)
    for old in (pp.V1_5_RECIPE, pp.MARKET20_RECIPE, pp.CEILING_RECIPE, pp.PB_RECIPE, pp.PB_CEILING_RECIPE):
        assert old.winsor == ("f3",) and old.log == ("f1",)
    assert pp.CEILING_V1_REAL_RECIPE.winsor == ("f1r", "f2", "f3") and pp.CEILING_V1_REAL_RECIPE.log == ("f1r",)
    assert fitmod.recipe_for(FAZ7C_MODEL_SPECS[H99]) is fitmod.recipe_for(FAZ7C_MODEL_SPECS[POOLED]) is pp.FALL_V0_RECIPE
    assert fitmod.recipe_for(FAZ7C_MODEL_SPECS[ADDSALE]) is pp.FALL_V0_ADDSALE_RECIPE
    assert list(pp.RECIPES)[:7] == ["V1_5", "MARKET20", "CEILING", "PB", "PB_CEILING", "CEILING_V1_CLIP", "CEILING_V1_REAL"]


@pytest.mark.requires_git_history
def test_faz7c_specs_documents_and_registry():
    """§8 specs satırı: 4 kimlik (`FAZ7C_MODEL_IDS` sırası), ayrı sözlük (MODEL_SPECS'e girmez; INDEX'e yalnız dondurmayla, sona,
    FAZ7C sırasıyla: 23 → 27 giriş, SPEC_DEVIATIONS K19), şartname belgeleri (SPEC_C_V0 + KARARLAR_C) sha'ları dosyalarla aynı;
    logit bloğu V1.6'nınki (+ etiket notu); deflatör v1 ile aynı blok."""
    assert FAZ7C_MODEL_IDS == ("fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO")
    for doc in SPEC_DOCUMENTS_FAZ7C.values():
        assert sha256_file(ROOT / doc["path"]) == doc["sha256"]
    assert set(FAZ7C_MODEL_SPECS).isdisjoint(set(MODEL_SPECS) | set(POST_D1_MODEL_SPECS) | set(FAZ7_MODEL_SPECS))
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]
    frozen = fs7.frozen_faz7c_ids()
    assert frozen in ([], list(FAZ7C_MODEL_IDS)) and len(index) == 23 + len(frozen)
    assert [e["model_id"] for e in index if e["model_id"] in FAZ7C_MODEL_SPECS] == frozen == [e["model_id"] for e in index[23:]]
    assert len({spec_sha256(s) for s in FAZ7C_MODEL_SPECS.values()}) == 4
    for m, s in FAZ7C_MODEL_SPECS.items():
        assert model_kind(m) == "fall" and plan_of(m) == s["plan_id"] and s["family"] == "fall_d10_v0"
        assert s["horizons"] == ["D5", "D10"] and s["target_definition"] == "1 - Y_h (close(D_h) <= ipo_price)"
        assert s["spec_document"] == SPEC_DOCUMENTS_FAZ7C["SPEC_C_V0"] and s["decisions_document"] == SPEC_DOCUMENTS_FAZ7C["KARARLAR_C"]
        logit = {k: v for k, v in s["logit"].items() if k != "label"}
        base = dict(V1_6_H99["logit"])
        if m == ZERO_ROW:
            assert logit.pop("C_grid") == ["ZERO"] and base.pop("C_grid")
        assert logit == base
    for m in (H99, POOLED):
        assert FAZ7C_MODEL_SPECS[m]["deflator"] == DEFLATOR and FAZ7C_MODEL_SPECS[m]["features"] == ["f1r", "f3", "add_sale"]
        assert FAZ7C_MODEL_SPECS[m]["input_policy"]["f3_missing"] == "REFUSE"
    assert FAZ7C_MODEL_SPECS[ADDSALE]["features"] == ["add_sale"] and FAZ7C_MODEL_SPECS[ADDSALE]["input_policy"]["f3_missing"] == "NOT_USED"
    assert FAZ7C_MODEL_SPECS[ZERO_ROW]["features"] == [] and FAZ7C_MODEL_SPECS[ZERO_ROW]["parent_model_id"] == POOLED
    assert all(FAZ7C_MODEL_SPECS[m]["input_policy"]["additional_sale_missing"] == "REFUSE" for m in (H99, POOLED, ADDSALE))
    assert sha256_file(ROOT / FAZ7C_EXPLORATION["path"]) == FAZ7C_EXPLORATION["sha256"]
    assert fitmod.fall_grid(FAZ7C_MODEL_SPECS[H99]) == fitmod.V1_6_GRID and fitmod.fall_grid(FAZ7C_MODEL_SPECS[ZERO_ROW]) is None


# ---------------------------------------------------------------- §11-3 f1r ve ön işleme sırası

def test_f1r_bit_equal_ceiling_hazard_v1_real_on_training_rows(real):
    """§11-3: eğitim satırlarında f1r ham değeri `ceiling_hazard_v1_real`'in (ve havuzda `_pooled`'ın) f1r'siyle bit-eşit (aynı
    `tufe.index_for` ve `predict_hazard.real_size`); f3 `compute_features`'ınki; add_sale bayrağın kendisi."""
    from borsai.features import compute_features

    for m, v1 in ((H99, "ceiling_hazard_v1_real"), (POOLED, "ceiling_hazard_v1_pooled")):
        ds, a = _ds(real, m)
        rows = bt.fall_training_rows(FAZ7C_MODEL_SPECS[m], ds, a, check=True)
        fr, info = bt.fall_raw_features(FAZ7C_MODEL_SPECS[m], rows, a)
        vr, vinfo = bt.v1_raw_features(FAZ7_MODEL_SPECS[v1], rows)
        assert len(fr) == len(rows) and info == vinfo
        for r in rows:
            assert str(fr[r.ticker]["f1r"]) == str(vr[r.ticker]["f1r"]) and fr[r.ticker]["f1r"] == vr[r.ticker]["f1r"]
            assert fr[r.ticker]["f3"] == compute_features(**r.feature_inputs()).f3
            assert fr[r.ticker]["add_sale"] == pf.additional_sale_flag(a[r.ticker])


def test_winsor_bounds_type7_and_log_after_winsor(real):
    """§11-3: kırpma sınırları eğitim arzlarının HAM f1r (2025 TL) ve f3 değerlerinin Type-7 p05/p95'i (kesin Fraction); log kırpmadan
    sonra: p05/2 ile p05 aynı z; add_sale yalnız z-skor ((x − μ)/σ, kesin). Ön işleme; model fiti değil."""
    rows = bt.fall_training_rows(FAZ7C_MODEL_SPECS[H99], real["h99"], real["as_h99"], check=True)
    raw = bt.fall_raw_features(FAZ7C_MODEL_SPECS[H99], rows, real["as_h99"])[0]
    prep = pp.fit_preprocessing(raw, {r.ticker: r.total_demand_filter_status for r in rows}, recipe=pp.FALL_V0_RECIPE)
    assert prep.columns == ("f1r", "f3", "add_sale") and set(prep.winsor_exact) == {"f1r", "f3"}
    assert prep.log_features == ("f1r", "f3") and prep.f3_filter_nulled == ()
    for f in ("f1r", "f3"):
        vals = sorted(Fraction(raw[t][f]) for t in raw)
        assert prep.winsor_exact[f] == (pp.quantile_type7(vals, Fraction(1, 20)), pp.quantile_type7(vals, Fraction(19, 20)))
    t0 = rows[0].ticker
    lo = {**raw[t0], "f1r": Decimal(prep.winsor_exact["f1r"][0].numerator) / Decimal(prep.winsor_exact["f1r"][0].denominator)}
    half = {**raw[t0], "f1r": lo["f1r"] / 2}
    z_lo, z_half = prep.transform(lo, None), prep.transform(half, None)
    assert z_lo["z"]["f1r"] == z_half["z"]["f1r"] and z_half["winsorized"]["f1r"] is True
    big = {**raw[t0], "f3": Decimal(10) ** 6}
    zb = prep.transform(big, None)
    assert zb["winsorized"]["f3"] is True and zb["z"]["f3"] == prep.transform(
        {**raw[t0], "f3": Decimal(prep.winsor_exact["f3"][1].numerator) / Decimal(prep.winsor_exact["f3"][1].denominator)}, None)["z"]["f3"]
    params = prep.params()
    assert params["log_transform"] == ["f1r", "f3"] and set(params["winsor"]) == {"f1r", "f3"} and params["medians"] == {}
    vals = [Fraction(raw[t]["add_sale"]) for t in raw]
    mu = sum(vals, Fraction(0)) / len(vals)
    assert prep.mean_exact["add_sale"] == mu and set(vals) == {Fraction(0), Fraction(1)}


# ---------------------------------------------------------------- §11-5 fit yolu (sentetik) ve @ZERO

@pytest.fixture(scope="module")
def syn():
    v2, a2 = f7c.synthetic_fall_dataset(tag="syn_v2_model", seed=20260927)
    h99, ah = f7c.h99_subset(v2, a2, tag="syn_h99_model")
    return {"v2": (v2, a2), "h99": (h99, ah)}


def _syn(syn, m):
    return syn["h99"] if m == H99 else syn["v2"]


def test_fit_path_is_v1_6_logit_without_ridge(syn):
    """§4, §11-5: Ridge'siz yol `_fit_logit`'i V1.6 ızgarası ve aday başına politikayla çağırır: f3 filtre dışlaması yokken
    `fit_v1_5_horizon`'ın (aynı tarif ve V1_6_GRID) Logit başlığıyla bit-eşit (seçilen C, iç LOOCV tablosu, test olasılığı)."""
    ds, a = syn["h99"]
    rows = select_fall_training_rows(ds, "H99_F3_AS_PRESENT", a)
    raw = bt.fall_raw_features(FAZ7C_MODEL_SPECS[H99], rows, a)[0]
    status = {r.ticker: r.total_demand_filter_status for r in rows}
    order, test = [r.ticker for r in rows[:-1]], rows[-1]
    for h in ("D5", "D10"):
        Y = {r.ticker: r.targets[h].Y for r in rows}
        R = {r.ticker: float(r.targets[h].R) for r in rows}
        hf = fitmod.fit_fall_horizon(order, raw, Y, status, recipe=pp.FALL_V0_RECIPE, grid=fitmod.V1_6_GRID,
                                     test_raw=raw[test.ticker], test_filter_status=status[test.ticker])
        ref = fitmod.fit_v1_5_horizon(order, raw, R, Y, status, test_raw=raw[test.ticker], test_filter_status=status[test.ticker],
                                      grid=fitmod.V1_6_GRID, recipe=pp.FALL_V0_RECIPE)
        g, r = hf.logit, ref.logit
        assert (g.status, g.selected_C, g.score_table, g.probability, g.final_attempts) == (
            r.status, r.selected_C, r.score_table, r.probability, r.final_attempts)
        assert [e.hyperparameter for e in g.score_table] == list(fitmod.V1_6_C_GRID) and hf.excluded == ()
        zero = next(e for e in g.score_table if e.hyperparameter == fitmod.ZERO)
        loo = [(sum(Y[t] for t in order if t != j) / (len(order) - 1) - Y[j]) ** 2 for j in order]
        assert zero.score == pytest.approx(sum(loo) / len(loo), abs=1e-15)
        head = fitmod.fall_head(hf)
        assert head["return"] is None and head["p_up"]["kind"] == "logit" and len(head["p_up"]["inner_loocv_brier"]) == 8


def test_label_is_up_and_flip_symmetric(syn):
    """SPEC_DEVIATIONS K: başlıklar tablonun Y_h'siyle (p_up) fit edilir; y = 1 − Y_h ile fit edilen model aynı modeldir (L2-lojistik
    etiket çevirmesine simetrik): aynı C, p_fall = 1 − p_up (optimizasyon toleransında)."""
    ds, a = syn["v2"]
    rows = select_fall_training_rows(ds, "H99_PLUS_OOT_OPEN_F3_AS_PRESENT", a)
    raw = bt.fall_raw_features(FAZ7C_MODEL_SPECS[POOLED], rows, a)[0]
    status = {r.ticker: r.total_demand_filter_status for r in rows}
    order, test = [r.ticker for r in rows[:-1]], rows[-1]
    Y = {r.ticker: r.targets["D10"].Y for r in rows}
    up = fitmod.fit_fall_horizon(order, raw, Y, status, recipe=pp.FALL_V0_RECIPE, test_raw=raw[test.ticker],
                                 test_filter_status=status[test.ticker])
    down = fitmod.fit_fall_horizon(order, raw, {t: 1 - y for t, y in Y.items()}, status, recipe=pp.FALL_V0_RECIPE,
                                   test_raw=raw[test.ticker], test_filter_status=status[test.ticker])
    assert up.logit.selected_C == down.logit.selected_C
    assert abs(up.logit.probability - (1 - down.logit.probability)) <= 1e-6
    for e_up, e_down in zip(up.logit.score_table, down.logit.score_table):
        assert abs(e_up.score - e_down.score) <= 1e-9


def test_zero_rule_is_training_rate_bit_equal_fraction(real):
    """§11-5: `fall_d10_v0_pooled@ZERO` = havuz eğitim oranı: D10 p_up = 1 − 39/161, D5 = 1 − 29/161 (Fraction, bit-eşit); stdlib
    tahmin girdi istemez ve aynı değeri verir."""
    params, fits = bt.final_fit_fall(ZERO_ROW)
    for h, ev in (("D10", 39), ("D5", 29)):
        head = params["horizons"][h]
        assert head["return"] is None and head["p_up"]["kind"] == "constant" and head["p_up"]["C"] == "ZERO"
        assert head["p_up"]["value"] == float(Fraction(1) - Fraction(ev, 161)) == (161 - ev) / 161
        assert (head["p_up"]["n_class_0"], head["p_up"]["n_class_1"]) == (ev, 161 - ev)
    out = pf.predict(params, {})
    assert out["refused"] is None and out["D10"]["p_up"] == float(Fraction(122, 161)) and out["D5"]["p_up"] == float(Fraction(132, 161))
    assert params["preprocessing"] is None and params["features"] == [] and params["training"]["n"] == 161
    assert params["training"]["filter_excluded"] == [] and params["spec_sha256"] == spec_sha256(FAZ7C_MODEL_SPECS[ZERO_ROW])


def test_f3_filter_exclusion_rule_in_fall_fit():
    """SPEC_DEVIATIONS K (J10 kuralı aynen): imputasyonsuz tarifte f3'ü eğitim kümesinin filtre moduna açıkça zıt olan arz o kümede
    kullanılmaz; iç CV'de her iç kümenin moduyla ayrıca. Kural olmadan ön işleme eksik f3 hatası verir."""
    import random

    rng = random.Random(3)

    def rows(n_unf, n_ns, n_f):
        st = ["UNFILTERED"] * n_unf + ["NOT_SPECIFIED"] * n_ns + ["FILTERED"] * n_f
        raw = {f"R{i:02d}": {"f1r": Decimal(rng.randint(10**8, 10**10)), "f3": Decimal(str(round(rng.uniform(1.1, 30), 2))),
                             "add_sale": Decimal(i % 3 == 0)} for i in range(len(st))}
        return raw, dict(zip(raw, st)), {t: i % 2 for i, t in enumerate(raw)}

    raw, status, Y = rows(7, 6, 1)                              # mod UNFILTERED: FILTERED birim bu kümede kullanılmaz
    hf = fitmod.fit_fall_horizon(list(raw), raw, Y, status, recipe=pp.FALL_V0_RECIPE)
    f = [t for t, s in status.items() if s == "FILTERED"]
    assert hf.excluded == tuple(f) and f[0] not in hf.order and hf.logit.status == fitmod.STATUS_FIT_OK
    assert hf.stats["filter_excluded_n"] == 1 and hf.final.f3_filter_nulled == ()
    with pytest.raises(pp.MissingValueError):                   # kural olmadan: ön işleme boşalan f3'ü dolduramaz
        pp.fit_preprocessing(raw, status, recipe=pp.FALL_V0_RECIPE)
    raw, status, Y = rows(6, 6, 1)                              # eşitlik -> NOT_SPECIFIED: dış kümede dışlama yok
    hf = fitmod.fit_fall_horizon(list(raw), raw, Y, status, recipe=pp.FALL_V0_RECIPE)
    assert hf.excluded == () and hf.logit.status == fitmod.STATUS_FIT_OK
    assert hf.stats["inner_filter_excluded_n"] == 6             # bir NOT_SPECIFIED tutulunca iç mod UNFILTERED: FILTERED dışarıda
    assert hf.stats["inner_held_out_not_scored_n"] == 0 and hf.logit.inner_fold_n == len(raw)
    add = fitmod.fit_fall_horizon(list(raw), raw, Y, status, recipe=pp.FALL_V0_ADDSALE_RECIPE)
    assert add.excluded == () and add.stats["inner_filter_excluded_n"] == 0     # addsale f3 kullanmaz


# ---------------------------------------------------------------- §11-9 JSON ↔ stdlib tahmin, retler

@pytest.fixture(scope="module")
def syn_params(syn):
    out = {}
    for m in FAZ7C_MODEL_IDS:
        ds, a = _syn(syn, m)
        out[m] = bt.final_fit_fall(m, ds, spec=f7c.synthetic_spec(m, ds, a), add_sale=a)
    return out


def _inputs(r, a):
    return {**r.inputs, "total_demand_filter_status": r.total_demand_filter_status, "tufe_index": r.tufe_index,
            "additional_sale_shares": a[r.ticker]}


@pytest.mark.parametrize("model_id", FAZ7C_MODEL_IDS)
def test_json_params_predict_parity_synthetic(model_id, syn, syn_params):
    """§11-9 (sentetik): JSON + stdlib `predict_fall.predict`, nihai fit'in kendi olasılığıyla (sklearn predict_proba ya da sabit)
    eğitim arzlarının hepsinde |Δ| ≤ 1e-12; JSON şeması (§2.3 alanları) ve `@ZERO` sabit başlık."""
    ds, a = _syn(syn, model_id)
    params, fits = syn_params[model_id]
    # Dondurma ve önizleme JSON'u sıralı anahtarla yazar (`pretty_json_bytes`: D10, D5); tahmin yazılmış dosyayla çalışmalı
    # (commit B testleri yakaladı; SPEC_DEVIATIONS K14).
    params = json.loads(pretty_json_bytes(params))
    assert list(params["horizons"]) == ["D10", "D5"]
    spec = f7c.synthetic_spec(model_id, ds, a)
    for k in ("family", "variant", "target_definition", "horizons", "preprocessing", "feature_ranges", "input_policy", "training",
              "spec_sha256", "code_version", "runtime"):
        assert k in params, k
    assert params["family"] == "fall_d10_v0" and params["variant"] == spec["variant"] and ("deflator" in params) == ("f1r" in spec["features"])
    assert {"set", "table", "cohort_counts", "n", "events_D5", "events_D10", "filter_excluded"} <= set(params["training"])
    used = set(params["training"]["tickers"])
    worst = 0.0
    for r in ds.rows:
        if r.ticker not in used:
            continue
        out = pf.predict(params, _inputs(r, a))
        assert out["refused"] is None, out["refused"]
        for h in ("D5", "D10"):
            hf = fits[h]
            if hf.final is None:
                ref = hf.logit.constant
            else:
                raw = bt.fall_raw_features(spec, [r], a)[0][r.ticker]
                z = hf.final.transform(raw, r.total_demand_filter_status)["z"]
                x = np.array([[z[c] for c in hf.logit.columns]], dtype=np.float64)
                ref = hf.logit.constant if hf.logit.estimator is None else float(hf.logit.estimator.predict_proba(x)[0][1])
            worst = max(worst, abs(out[h]["p_up"] - ref))
            assert out[h]["return"] is None and out[h]["direction"] == ("UP" if out[h]["p_up"] > 0.5 else "DOWN")
    assert worst <= 1e-12


def test_predict_refusal_paths(syn, syn_params):
    """§11-9 ret yolları: f3 boş, ek satış boş / negatif, TÜFE eksik / PIT değil / dosya uyuşmazlığı, filtre uyuşmazlığı, V1.5 girdi
    hatası; addsale yalnız ek satış ister; @ZERO girdi istemez; kırpma uyarısı; parametre dosyası denetimi."""
    ds, a = syn["v2"]
    r = next(x for x in ds.rows if x.cohort == "H99" and a[x.ticker] is not None and x.inputs["total_demand_multiple"] is not None)
    base = _inputs(r, a)
    pooled, addsale, zero = syn_params[POOLED][0], syn_params[ADDSALE][0], syn_params[ZERO_ROW][0]

    def code(params, **over):
        out = pf.predict(params, {**base, **over})
        return None if out["refused"] is None else (out["refused"]["code"], out["refused"]["field"])

    assert code(pooled) is None
    assert code(pooled, total_demand_multiple=None) == ("F3_MISSING", "total_demand_multiple")
    assert code(pooled, additional_sale_shares="") == ("ADDITIONAL_SALE_MISSING", "additional_sale_shares")
    assert code(pooled, additional_sale_shares="DATA_NOT_FOUND") == ("ADDITIONAL_SALE_MISSING", "additional_sale_shares")
    assert code(pooled, additional_sale_shares="-5") == ("INPUT_NEGATIVE", "additional_sale_shares")
    assert code(pooled, tufe_index=None) == ("TUFE_MISSING", "tufe_index")
    assert code(pooled, tufe_refusal="TUFE_NOT_PIT") == ("TUFE_NOT_PIT", "tufe_index")
    assert code(pooled, tufe_refusal="TUFE_FILE_MISMATCH") == ("TUFE_FILE_MISMATCH", "tufe_index")
    assert code(pooled, shares_offered=None) == ("INPUT_MISSING", "shares_offered")
    conflict = copy.deepcopy(pooled)
    conflict["preprocessing"]["f3_filter_mode"] = "UNFILTERED"
    assert pf.predict(conflict, {**base, "total_demand_filter_status": "FILTERED"})["refused"]["code"] == "F3_FILTER_STATUS_CONFLICT"
    assert pf.predict(conflict, {**base, "total_demand_filter_status": "UNFILTERED"})["refused"] is None
    assert code(addsale, total_demand_multiple=None, tufe_index=None, shares_offered=None) is None
    assert code(addsale, additional_sale_shares=None) == ("ADDITIONAL_SALE_MISSING", "additional_sale_shares")
    out = pf.predict(zero, {})
    assert out["refused"] is None and out["D10"]["p_up"] == zero["horizons"]["D10"]["p_up"]["value"]
    big = pf.predict(pooled, {**base, "total_demand_multiple": "5000"})
    assert big["clipped"] is True and "f3" in big["clipped_features"]
    assert any(w["code"] == "FEATURE_CLIPPED_TO_TRAINING_P05_P95" and w["feature"] == "f3" for w in big["warnings"])
    assert big["add_sale_used"] in (0, 1) and big["tufe_index_used"] == str(r.tufe_index)
    bad = copy.deepcopy(pooled)
    bad["horizons"]["D10"]["return"] = {"kind": "constant", "value": 0.1}
    for broken in (bad, {**pooled, "family": "ceiling_hazard_v1"}, {**pooled, "features": ["f1", "f3"]}):
        with pytest.raises(pf.PredictError):
            pf.predict(broken, base)


def test_predict_fall_is_stdlib_only():
    code = ("import sys, borsai.predict_fall; bad = sorted(m for m in sys.modules if m.split('.')[0] in "
            "('numpy', 'sklearn', 'scipy', 'joblib')); print(bad)")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    assert out == "[]"


# ---------------------------------------------------------------- §11-4, T2: altın dosyalar ve uygulama pini

def test_app_golden_pins_unchanged():
    """T2 ve §11-4: pinli tahmin kaynakları (features, horizons, predict, predict_hazard, predict_market20, predict_path, predict_pb,
    survival) değişmedi; `gen_golden --check` 35 dosyanın hepsini bayt-eşit bulur (EK 3 P1 sonrası: +tufe_cases.json, +4 v1 altın dosyası; EK 3 P2 sonrası: +post_d1_hazard_v0.jsonl; EK 3 P4 sonrası: +4 (C) altın dosyası ve `predict_fall.py` pinli kaynak).
    Faz 7C dondurması (SPEC_DEVIATIONS K20; J31 kalıbı, orkestratör kararı): dondurma commit'i (F1) ile uygulamanın yeniden pini
    (APPPIN) arasında yalnız MANIFEST'in `models_index_sha256` alanı eski INDEX'i (23 giriş, 80670cb) adlandırabilir: o durumda
    yeniden üretilen MANIFEST bu tek alan dışında aynıdır ve öteki 24 dosya bayt-eşittir. APPPIN'den sonra kesin koşul."""
    manifest = json.loads((ROOT / "app" / "parity" / "golden" / "MANIFEST.json").read_text(encoding="utf-8"))
    for path, sha in manifest["predict_sources_sha256"].items():
        assert sha256_file(ROOT / path) == sha, path
    assert "borsai/predict_fall.py" in manifest["predict_sources_sha256"]
    res = subprocess.run([sys.executable, "app/parity/gen_golden.py", "--check"], cwd=ROOT, capture_output=True, text=True)
    out = json.loads(res.stdout.strip().splitlines()[-1])
    if out == {"checked": 35, "different": []}:
        assert res.returncode == 0
        return
    pre = subprocess.run(["git", "show", f"{PRE_FAZ7C_INDEX_COMMIT}:models/INDEX.json"], cwd=ROOT, check=True, capture_output=True).stdout
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]
    assert out == {"checked": 35, "different": ["golden/MANIFEST.json"]} and fs7.frozen_faz7c_ids() == list(FAZ7C_MODEL_IDS)
    assert index[:23] == json.loads(pre)["models"] and manifest["models_index_sha256"] == sha256_bytes(pre)
    code = ("import sys; sys.path.insert(0, 'app/parity'); import gen_golden as g; "
            "sys.stdout.buffer.write(g.generate()['golden/MANIFEST.json'])")
    fresh = json.loads(subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True, capture_output=True).stdout)
    assert fresh["models_index_sha256"] == sha256_file(ROOT / "models" / "INDEX.json")
    assert {**fresh, "models_index_sha256": manifest["models_index_sha256"]} == manifest

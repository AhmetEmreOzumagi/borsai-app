"""Faz 8 kırılma akşamı: tablo, özellikler, yükleyici sızıntısı, plan, yastık kuralı, ret/uyarı/kapsam ve hijyen (SPEC_BREAK_V0 §13-1,
2, 3, 4, 7, 8, 14). Commit A: gerçek veride walk-forward skoru ve nihai fit yok; gerçek veride yalnız tablo düzeyi (kırılma tablosu,
özellik değerleri, plan, hücre kesimleri, yastık aritmetiği), model davranışı sentetik veriyle (tests/test_faz8_support.py)."""
from __future__ import annotations

import copy
import csv
import math
import re
import subprocess
from collections import Counter
from datetime import date
from decimal import Decimal
from fractions import Fraction

import pytest

from borsai import post_break as pbk
from borsai import predict_break as pb
from borsai import predict_path as pth
from borsai import preprocess as pp
from borsai import registry as reg
from borsai.data import load_dataset
from borsai.predict import PredictError
from borsai.provenance import ROOT

import faz8_support as fs8
import test_faz8_support as f8

BASE_COMMIT = "7d78d43"          # origin/main, Faz 8 şartnamesi (bu görevden önce)


@pytest.fixture(scope="module")
def dataset():
    return load_dataset()


@pytest.fixture(scope="module")
def table(dataset):
    return pbk.load_break_table(dataset)


@pytest.fixture(scope="module")
def values(table):
    return pbk.break_values(table)


@pytest.fixture(scope="module")
def synth():
    t, path = f8.synthetic_table()
    params = {m: pbk.build_params(m, t, "synthetic", check=False)[0] for m in pbk.FAZ8_MODEL_IDS}
    return t, path, params


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


# ---------------------------------------------------------------- §13-1 kırılma tablosu

def test_1_break_table_counts_match_profile(table, values):
    units = table.units
    br = table.breaks()
    assert len(units) == 99 and len(br) == 82
    assert Counter(u.b for u in units if u.b is not None) == {1: 18, 2: 11, 3: 4, 4: 13, 5: 12, 6: 8, 7: 6, 8: 6, 9: 4, 10: 3}
    assert sum(u.status == pbk.UNIT_NO_BREAK for u in units) == 14 and sum(u.status == pbk.UNIT_B10 for u in units) == 3
    assert all(u.L == u.b - 1 for u in units if u.b is not None) and all(u.L == 10 for u in units if u.b is None)
    assert sum(v.b_floor for v in values.values()) == 35
    assert sum(values[u.ticker].b_floor for u in br if u.b >= 2) == 31 and sum(values[u.ticker].b_floor for u in br if u.b == 1) == 4
    every = [u for u in units if u.b is not None]                       # bütün b (b = 10 dahil; profil §7)
    assert sum(u.day["half_day"] for u in every) == 1 and sum(u.day["halt_flag"] for u in every) == 0
    assert sum(1 for u in br if u.day["half_day"]) == 1
    ge2 = [u for u in every if u.b >= 2]
    assert len(ge2) == 67
    assert sum(Decimal(u.day["fields_raw"]["reference_price"]) == Decimal(u.closes[u.b - 2]) for u in ge2) == 67
    assert sum(pth.lower_limit(Decimal(u.day["fields_raw"]["reference_price"])) == Decimal(u.day["fields_raw"]["lower_limit"])
               for u in every) == 85
    assert sum(1 for u in br if u.first_trading_date >= pbk.NEAR_ERA_START) == 69
    assert len(table.labels) == 82 and set(table.labels) == {u.ticker for u in br}
    assert all(v.band_rule_ok for v in values.values())
    assert sum(v.floor_lock_allday for v in values.values()) == 8          # profil §3: 7/64 + 1/18


def test_1b_streak_matches_table_and_snapshot_dates(dataset, table):
    by = dataset.by_ticker()
    for u in table.units:
        assert u.L == by[u.ticker].ceiling_streak and u.session_dates == tuple(by[u.ticker].session_dates)
        assert u.ipo_price == by[u.ticker].inputs["ipo_price_tl"] and u.shares_offered == by[u.ticker].inputs["shares_offered"]


# ---------------------------------------------------------------- §13-2 özellik tanımı

def _day(**fields):
    base = {"open": "10.50", "high": "11.00", "low": "10.12", "close": "10.12", "volume": "1000000", "trade_count": "500",
            "reference_price": "11.24", "upper_limit": "12.36", "lower_limit": "10.12"}
    base.update(fields)
    return {"fields_raw": base, "half_day": 0, "halt_flag": 0}


def test_2_b_floor_is_raw_text_decimal_equality():
    assert pb.evaluate_break_day(_day(close="10.12", lower_limit="10.120"), "1000000").b_floor == 1
    # float eşitliği bu satırı 1 yapardı (float("10.1200000000000000001") == 10.12): mutasyon kırmızı
    assert float("10.1200000000000000001") == float("10.12")
    assert pb.evaluate_break_day(_day(close="10.1200000000000000001", lower_limit="10.12", low="10.12"), "1000000").b_floor == 0
    assert pb.evaluate_break_day(_day(close="10.13"), "1000000").b_floor == 0


def _q(values, p):
    """Profil betiğinin `q` yöntemi (Type-7, float)."""
    xs = sorted(values)
    h = (len(xs) - 1) * p
    lo, hi = math.floor(h), math.ceil(h)
    return xs[lo] + (xs[hi] - xs[lo]) * (h - lo)


def test_2b_turnover_quantiles_match_profile_section_4(table, values):
    sub = [u for u in table.breaks() if u.b >= 2]
    assert len(sub) == 64
    mine = [float(values[u.ticker].turnover_ratio) for u in sub]
    prof = [float(Decimal(u.day["fields_raw"]["volume"]) / Decimal(u.shares_offered)) for u in sub]     # betikteki ifade
    stats = lambda xs: [min(xs), _q(xs, .05), _q(xs, .25), _q(xs, .5), _q(xs, .75), _q(xs, .95), max(xs)]  # noqa: E731
    for a, b in zip(stats(mine), stats(prof)):
        assert abs(a - b) <= 1e-9
    assert " / ".join(f"{x:.4g}" for x in stats(mine)) == "0.06236 / 0.1134 / 0.8542 / 1.632 / 2.228 / 2.897 / 3.219"
    for u in sub:
        assert values[u.ticker].turnover_ln == float(values[u.ticker].turnover_ratio.ln(pb._LN))


def test_2c_clip_is_type7_on_ln_scale(table, values):
    raw = pbk.raw_features(table, values)
    fitted = pp.fit_preprocessing(raw, {}, recipe=pbk.BREAK_V0_RECIPE)
    lns = sorted(Fraction(raw[t]["b_turnover"]) for t in raw)
    assert fitted.winsor_exact["b_turnover"] == (pp.quantile_type7(lns, pp.WINSOR_P05), pp.quantile_type7(lns, pp.WINSOR_P95))
    ratios = sorted(Fraction(values[t].turnover_ratio) for t in raw)
    raw_scale = math.log(float(pp.quantile_type7(ratios, pp.WINSOR_P05)))
    assert float(fitted.winsor_exact["b_turnover"][0]) != raw_scale          # ham ölçekte kırpma farklı olurdu
    assert fitted.columns == ("b_floor", "b_turnover") and "b_floor" not in fitted.winsor_exact
    assert pbk.BREAK_V0_RECIPE.log == () and pbk.BREAK_V0_RECIPE.winsor == ("b_turnover",)
    assert not pbk.BREAK_V0_RECIPE.indicator and not pbk.BREAK_V0_RECIPE.impute


# ---------------------------------------------------------------- §13-3 yükleyici sızıntısı (H20)

def test_3_loader_whitelist_access_counter(dataset, monkeypatch):
    accessed: dict[tuple[str, int], set] = {}

    class Tracking(dict):
        def __getitem__(self, k):
            key = (dict.__getitem__(self, "ticker"), int(dict.__getitem__(self, "session_number")))
            accessed.setdefault(key, set()).add(k)
            return dict.__getitem__(self, k)

        def get(self, k, default=None):
            return self[k] if k in self else default

    real = csv.DictReader

    class Reader(real):
        def __next__(self):
            return Tracking(super().__next__())

    monkeypatch.setattr(csv, "DictReader", Reader)
    t = pbk.load_break_table(dataset)
    after, at_b, streak = set(), set(), set()
    for u in t.units:
        for h in range(1, 11):
            keys = accessed[(u.ticker, h)]
            if u.b is None or h < u.b:
                streak |= keys
            elif h == u.b:
                at_b |= keys
            else:
                after |= keys
    assert after == {"ticker", "session_number", "target_session_date", "thb_raw_close", "thm_raw_lower_limit"}
    assert after == set(pbk.AFTER_BREAK_COLUMNS)
    assert streak == {"ticker", "session_number", "target_session_date", "thb_raw_close", "thm_raw_upper_limit"}
    assert at_b == {"ticker", "session_number", "target_session_date", *pbk.BREAK_DAY_FIELDS.values(), *pbk.BREAK_DAY_STATUS_COLUMNS}
    rows_after_b2 = [k for u in t.units if u.b is not None and u.b <= 7 for k in [(u.ticker, h) for h in range(u.b + 3, 11)]]
    assert rows_after_b2 and all(accessed[k] <= {"ticker", "session_number", "target_session_date"} for k in rows_after_b2)


def _fold_preps(table, values, override=None):
    raw = pbk.raw_features(table, values, override=override)
    out = {}
    for f in pbk.plan_break_folds(table):
        if f.training["F1"]:
            out[f.fold_id] = pp.fit_preprocessing({t: raw[t] for t in f.training["F1"]}, {}, recipe=pbk.BREAK_V0_RECIPE).params()
    return out


def test_3b_test_ipo_break_day_does_not_touch_its_own_fold(table, values):
    folds = pbk.plan_break_folds(table)
    k = next(f for f in folds[len(folds) // 2:] if f.status["F1"] == pbk.SCORABLE)
    base = _fold_preps(table, values)
    changed = _fold_preps(table, values, override={k.ticker: {"b_turnover": 9.0, "b_floor": Decimal(1 - values[k.ticker].b_floor)}})
    assert base[k.fold_id] == changed[k.fold_id] and k.ticker not in k.training["F1"]
    later = [f for f in folds if k.ticker in f.training["F1"]]
    assert later and all(base[f.fold_id] != changed[f.fold_id] for f in later)


# ---------------------------------------------------------------- §13-4 plan

def test_4_plan_counts_and_cutoffs(dataset, table):
    folds = pbk.plan_break_folds(table)
    assert len(folds) == 82 and len({f.fold_id for f in folds}) == 82
    assert sum(1 for f in folds if f.first_trading_date >= pbk.NEAR_ERA_START) == 69
    assert sum(1 for f in folds if f.first_trading_date < pbk.NEAR_ERA_START) == 13
    assert sum(1 for f in folds if f.status["F2"] != pb.TARGET_UNDEFINED_F2) == 78
    assert all(f.status["F2"] == pb.TARGET_UNDEFINED_F2 for f in folds if f.b == 9)
    for f in folds:
        assert f.break_date == table.by_ticker()[f.ticker].session_dates[f.b - 1]
        for head in pbk.HEADS:
            for t in f.training[head]:
                y, d = pbk.label_of(table.labels[t], head)
                assert y is not None and d < f.break_date and d <= pbk.OUTCOME_CUTOFF
            if f.max_label_date[head] is not None:
                assert f.max_label_date[head] < f.break_date
            n, ev = len(f.training[head]), f.events[head]
            if f.status[head] != pb.TARGET_UNDEFINED_F2:
                assert (f.status[head] == pbk.SCORABLE) == (n >= 10 and ev >= 5 and n - ev >= 5)
    cache = pbk.CellCache(pbk._path_units(dataset))
    for f in folds:
        _, info = cache.get(f.first_trading_date)
        assert info["max_session_date"] is None or info["max_session_date"] < f.first_trading_date
    # raporlanan sayılar (IMPL_RAPOR): yetersiz eğitim fold'ları kronolojik başta
    insufficient = [f for f in folds if f.status["F1"] == pbk.STATUS_INSUFFICIENT]
    assert insufficient and folds.index(insufficient[-1]) < len(insufficient) + 5


def test_4b_same_day_rule_synthetic():
    d = date(2025, 3, 3)
    k = f8.make_unit("KKK", d, L=2)                              # b = 3, T = 3. seans
    same_break = f8.make_unit("SBR", date(2025, 2, 28), L=3)     # aynı gün kırılır (bir seans önce listelendi, b = 4)
    same_list_b1 = f8.make_unit("SL1", d, L=0)                   # aynı gün listelenir, b = 1: F1 etiketi D2 < T ama F2 etiketi D3 = T
    label_on_T = f8.make_unit("LOT", d, L=1)                     # aynı gün listelenir, b = 2: F1 etiketi D3 = T
    early = [f8.make_unit(f"E{i:02d}", date(2024, 1, 1 + i), L=i % 3, b_floor=i % 2, seed=i) for i in range(20)]
    t, _ = f8.table_of([k, same_break, same_list_b1, label_on_T, *early])
    folds = {f.ticker: f for f in pbk.plan_break_folds(t)}
    fk = folds["KKK"]
    T = fk.break_date
    assert t.by_ticker()["SBR"].break_date == T and "SBR" not in fk.training["F1"] and "SBR" not in fk.training["F2"]
    assert t.labels["SL1"].y1_date < T and "SL1" in fk.training["F1"]          # etiketi T'den önce: formül içeri alır (N2)
    assert t.labels["SL1"].y2_date == T and "SL1" not in fk.training["F2"]     # etiket seansı = T: dışarıda
    assert t.labels["LOT"].y1_date == T and "LOT" not in fk.training["F1"] and "LOT" not in fk.training["F2"]
    assert all(f"E{i:02d}" in fk.training["F1"] for i in range(20))
    for f in folds.values():
        assert f.ticker not in f.training["F1"] and f.ticker not in f.training["F2"]


# ---------------------------------------------------------------- §13-7 yastık kuralı

def test_7_structural_zero_on_h99(table):
    br = table.breaks()
    sz = {u.ticker: pb.structural_zero_d10(u.closes[-1], u.b, u.ipo_price) for u in br}
    imp = [u for u in br if sz[u.ticker]["impossible"]]
    assert len(imp) == 16 and Counter(u.b for u in imp) == {7: 6, 8: 6, 9: 4}
    assert sum(s["impossible"] == s["approx_impossible"] for s in sz.values()) == 82
    assert all(s["r_b"] == 10 - table.by_ticker()[t].b for t, s in sz.items())


def test_7b_structural_zero_boundary_and_rounding():
    exact = pb.structural_zero_d10("12.50", 9, "11.25")            # Lo(12.50) = 11.25 = P: D10 = P mümkün (≤ arz)
    assert exact["min10"] == "11.25" and exact["impossible"] is False and exact["k_b"] == 1.0 and exact["approx_impossible"] is True
    rounded = pb.structural_zero_d10("12.50", 8, "10.126")         # Lo(Lo(12.50)) = 10.125 → yukarı adım 10.13 > P
    assert rounded["min10"] == "10.13" and rounded["impossible"] is True and rounded["k_b"] < 2 and rounded["approx_impossible"] is False
    assert pb.structural_zero_d10("12.50", 8, "10.13")["impossible"] is False
    with pytest.raises(ValueError):
        pb.structural_zero_d10("12.50", 10, "10.00")
    badge = pb.structural_zero_badge("12.50", 8, "10.126", band_rule_ok=False)
    assert badge["shown"] is False and badge["impossible"] is True


# ---------------------------------------------------------------- §13-8 ret, uyarı, kapsam

def test_8_refusals_warnings_scope(synth):
    t, _, params = synth
    P = params[pbk.MODEL_ID]
    u = next(x for x in t.breaks() if x.b <= 8)
    ok = pb.predict_break(P, u.day, u.shares_offered, b=u.b)
    assert ok["refused"] is None and ok["F1"]["p_floor"] is not None and ok["F2"]["p_floor"] is not None
    lim = copy.deepcopy(u.day)
    lim["fields_raw"]["lower_limit"] = ""
    assert pb.predict_break(P, lim, u.shares_offered, b=u.b)["refused"]["code"] == pb.REFUSED_B_LIMIT_NA == "B_LIMIT_NA"
    vol = copy.deepcopy(u.day)
    vol["fields_raw"]["volume"] = "0"
    assert pb.predict_break(P, vol, u.shares_offered, b=u.b)["refused"]["code"] == "B_VOLUME_INVALID"
    fld = copy.deepcopy(u.day)
    fld["fields_raw"]["high"] = "0"
    assert pb.predict_break(P, fld, u.shares_offered, b=u.b)["refused"]["code"] == "B_FIELD_INVALID"
    assert pb.predict_break(P, u.day, "0", b=u.b)["refused"]["code"] == "INPUT_SHARES_OFFERED"
    assert pb.predict_break(P, u.day, None, b=u.b)["refused"]["code"] == "INPUT_SHARES_OFFERED"
    nt = copy.deepcopy(u.day)
    nt["fields_raw"]["trade_count"] = "0"
    with pytest.raises(PredictError):
        pb.predict_break(P, nt, u.shares_offered, b=u.b)
    b10 = pb.predict_break(P, u.day, u.shares_offered, b=10)
    assert b10["not_applicable"]["code"] == "B10" and b10["refused"] is None and b10["F1"] is None
    nb = pb.predict_break(P, None, u.shares_offered, b=None)
    assert nb["not_applicable"]["code"] == "NO_BREAK" and nb["F1"] is None
    b9 = pb.predict_break(P, u.day, u.shares_offered, b=9)
    assert b9["F2"] is None and b9["f2_status"] == "TARGET_UNDEFINED_F2" and b9["F1"]["p_floor"] == ok["F1"]["p_floor"]
    lock = copy.deepcopy(u.day)
    lock["fields_raw"]["high"] = lock["fields_raw"]["lower_limit"]
    out = pb.predict_break(P, lock, u.shares_offered, b=u.b)
    assert "WARN_B_FLOOR_LOCK_ALLDAY" in [w["code"] for w in out["warnings"]] and out["F1"] == ok["F1"]
    band = copy.deepcopy(u.day)
    ref = Decimal(band["fields_raw"]["reference_price"])
    band["fields_raw"]["lower_limit"] = str(ref * Decimal("0.89"))
    bo = pb.predict_break(P, band, u.shares_offered, b=u.b)
    assert "BAND_RULE_MISMATCH" in [w["code"] for w in bo["warnings"]] and "BAND_CHANGED" in bo["regime_tags"]
    assert bo["features"]["band_rule_ok"] is False and bo["F1"]["p_floor"] is not None        # tahmin yine üretilir
    half = pb.predict_break(P, {**u.day, "half_day": 1}, u.shares_offered, b=u.b)
    assert "WARN_B_HALF_DAY" in [w["code"] for w in half["warnings"]] and half["F1"] == ok["F1"]
    halt = pb.predict_break(P, {**u.day, "halt_flag": 1}, u.shares_offered, b=u.b)
    assert "WARN_B_INTRADAY_HALT" in [w["code"] for w in halt["warnings"]]
    sp = copy.deepcopy(u.day)
    sp["fields_raw"]["special_trade_volume"] = "12345"
    assert "WARN_B_SPECIAL_TRADES" in [w["code"] for w in pb.predict_break(P, sp, u.shares_offered, b=u.b)["warnings"]]
    big = pb.predict_break(P, u.day, str(int(Decimal(u.shares_offered) / 1000)), b=u.b)
    assert "B_TURNOVER_CLIPPED_TO_TRAINING_P05_P95" in [w["code"] for w in big["warnings"]]
    assert "OUT_OF_TRAINING_RANGE" in [w["code"] for w in big["warnings"]]
    assert pb.predict_break(P, u.day, u.shares_offered, b=u.b, first_trading_date="2026-09-16")["regime_tags"] == ["FON_KRIZI_2026"]
    assert pb.predict_break(P, u.day, u.shares_offered, b=u.b, first_trading_date="2026-09-15")["regime_tags"] == []
    # shares_offered PIT değil: tahmin üretilir (predict PIT bilmez), sınıf RETRO (§9.3)
    assert ok["F1"] is not None
    assert pb.class_break(model_prospective=True, record_live=False, inputs_pit_ok=False) == "RETRO"
    assert pb.class_break(model_prospective=True, record_live=False, inputs_pit_ok=True) == "MACHINE_SEQUENCED"
    assert pb.class_break(model_prospective=True, record_live=True, inputs_pit_ok=True) == "LIVE"
    assert pb.class_break(model_prospective=False, record_live=True, inputs_pit_ok=True) == "RETRO"
    z = pb.predict_break(params[pbk.ZERO_ID], None, None, b=u.b)                # @ZERO girdi istemez
    assert z["refused"] is None and z["F1"]["p_floor"] == params[pbk.ZERO_ID]["horizons"]["F1"]["p_floor"]["value"]


def test_8b_params_check(synth):
    _, _, params = synth
    P = params[pbk.MODEL_ID]
    for mutate in (lambda p: p.update(stage="POST_D1"), lambda p: p["horizons"].pop("F2"),
                   lambda p: p["preprocessing"]["F1"]["winsor"].pop("b_turnover"), lambda p: p.update(features=["b_floor"]),
                   lambda p: p["horizons"]["F1"]["p_floor"].update(coef=[1.0])):
        bad = copy.deepcopy(P)
        mutate(bad)
        with pytest.raises(PredictError):
            pb.check_params(bad)


# ---------------------------------------------------------------- §13-14 hijyen

def test_14_no_bulletin_names_or_sealed_codes_in_faz8_files():
    _, cohort = reg.read_cohort()
    sealed = sorted(r["ticker"] for r in reg.cohort_members(cohort) if r["vault"] == reg.VAULT_SEALED)
    n_sealed = len(sealed)                                                          # yerel değişken: hata çıktısı kod basmaz
    assert n_sealed == 64
    pattern = re.compile(r"\b(" + "|".join(sealed) + r")\b")
    paths = [*sorted((ROOT / "docs" / "specs_faz8").rglob("*.*")), ROOT / "borsai" / "post_break.py", ROOT / "borsai" / "predict_break.py",
             ROOT / "borsai" / "report_faz8.py", *sorted((ROOT / "tests").glob("test_faz8_*.py")), ROOT / "docs" / "prompts" / "FAZ8_BREAK_IMPL.md",
             *sorted(p for p in (ROOT / "docs" / "faz8").rglob("*.*") if p.suffix in (".md", ".txt", ".csv", ".json"))]
    assert len(paths) >= 10
    for p in paths:
        text = p.read_text(encoding="utf-8")
        n = len(set(pattern.findall(text)))
        assert n == 0, (p.name, n)
        assert not re.search(r"th[bm]20\d{6}", text, re.IGNORECASE), p.name


@pytest.mark.requires_git_history
def test_14b_old_specs_models_and_cutoff_unchanged(table):
    for d in ("docs/specs", "docs/specs_faz4", "docs/specs_faz5", "docs/specs_faz6", "docs/specs_faz7", "docs/specs_faz7_c"):
        assert _git("diff", "--name-only", BASE_COMMIT, "--", d) == "", d
        assert _git("status", "--porcelain", "--", d) == "", d
    assert _git("diff", "--name-only", BASE_COMMIT, "--", "docs/specs_faz8/SPEC_BREAK_V0.md", "docs/specs_faz8/ekler") == ""
    for p in ("models/INDEX.json", "models/INDEX_POST_D1.json"):
        assert (ROOT / p).read_bytes() == subprocess.run(["git", "show", f"{BASE_COMMIT}:{p}"], cwd=ROOT, check=True,
                                                         capture_output=True).stdout
    fs8.frozen_post_break_files()        # K-PIN (N25): dondurmadan önce INDEX_POST_BREAK yok; sonra yalnız üç dosya, dizin doğrulanmış
    assert _git("status", "--porcelain", "--", "models", "registry", "data", "scores", "legacy", "app") == ""
    for lbl in table.labels.values():                                # 2026-08-19 sonrası veri eğitime girmez
        assert lbl.y1_date <= pbk.OUTCOME_CUTOFF and (lbl.y2_date is None or lbl.y2_date <= pbk.OUTCOME_CUTOFF)


def test_14c_label_fields_only_in_label_code():
    """§7.2 (v): etiket alanları (`y1`, `y2`, tarihleri, `labels`) yalnız tablo yükleyicisinde, plan/etiket erişiminde, ledger'ın
    gerçekleşen sütunlarında ve nihai fit'in başlık kümelerinde; özellik ve tahmin kodu (predict_break) onları görmez."""
    import ast

    allowed = {"load_break_table", "label_of", "plan_break_folds", "backtest_ledger", "training_rows", "build_params"}
    tree = ast.parse((ROOT / "borsai" / "post_break.py").read_text(encoding="utf-8"))
    users = set()
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Attribute) and node.attr in ("y1", "y2", "y1_date", "y2_date", "labels"):
                users.add(fn.name)
    assert users <= allowed, users - allowed
    src = (ROOT / "borsai" / "predict_break.py").read_text(encoding="utf-8")
    assert not re.search(r"\b(y1|y2|labels|realized)\b", src)

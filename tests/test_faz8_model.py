"""Faz 8 model kodu: fit yolu, ürün karşılaştırıcısı, JSON ↔ stdlib paritesi, etiket kuralları, günlük ve rapor iskeleti (SPEC_BREAK_V0
§13-5, 6, 9, 10, 15). Commit A: model davranışı sentetik veriyle (tests/test_faz8_support.py); gerçek veride yalnız hücre kesimleri ve
Faz 4 paritesi (karşılaştırıcının malzemesi, model skoru değil). Gerçek koşu sonuçları commit B'de."""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

from borsai import fit as fitmod
from borsai import post_break as pbk
from borsai import post_d1 as pd
from borsai import predict_break as pb
from borsai import predict_path as pth
from borsai import report_faz8 as r8
from borsai import scoring as sc
from borsai.data import load_dataset
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes, sha256_file
from borsai.specs import (FAZ8_MODEL_IDS, FAZ8_SENSITIVITIES, OPERATIONAL_RULES_FAZ8, POST_BREAK_MODEL_SPECS, SPEC_DOCUMENTS_FAZ8,
                          spec_sha256)

import faz8_support as fs8
import test_faz8_support as f8

BASE_COMMIT = "7d78d43"
FREEZE_TASK_BASE = "6d3f674"       # dondurma görevinin başladığı HEAD (Fable denetimi); K-PIN, SPEC_DEVIATIONS N25
FREEZE_K_SUBJECT = "BORSAI_FAZ8_FREEZE_K:"
LIVE_A_SUBJECT = "BORSAI_FAZ8_LIVE_A:"   # canlı POST_BREAK görevinin kod commit'i (K-PIN-L, SPEC_DEVIATIONS N26)
# app/'a dokunan görevler (önek, app/'a dokunan son commit'in konusu); K-PIN-UI (SPEC_DEVIATIONS O), K-PIN-FIX (FAZ9_UI_FIX)
APP_TASKS = (("BORSAI_FAZ9_APP_UI_", "BORSAI_FAZ9_APP_UI_C:"), ("BORSAI_FAZ9_UI_FIX_", "BORSAI_FAZ9_UI_FIX_C:"),
             ("BORSAI_FAZ9_WINDOWS_", "BORSAI_FAZ9_WINDOWS_R:"), ("BORSAI_FAZ9_SNAPSHOT_", "BORSAI_FAZ9_SNAPSHOT_R:"),
             ("BORSAI_FAZ9_PUBLIC_MIRROR_", "BORSAI_FAZ9_PUBLIC_MIRROR_R:"))
# app/'a dokunan her yeni görev bu listeye kendi satırını ekler (önceden onaylı pin)
STDLIB_ALLOWED = {"__future__", "math", "typing", "decimal", "dataclasses"}


@pytest.fixture(scope="module")
def dataset():
    return load_dataset()


@pytest.fixture(scope="module")
def table(dataset):
    return pbk.load_break_table(dataset)


@pytest.fixture(scope="module")
def path_units(dataset):
    return pbk._path_units(dataset)


@pytest.fixture(scope="module")
def synth():
    return f8.synthetic_table()


@pytest.fixture(scope="module")
def synth_small():
    return f8.synthetic_table(n=34, gap_days=31)


@pytest.fixture(scope="module")
def synth_ledger(synth):
    t, path = synth
    ledger, info = pbk.backtest_ledger(t, path, workers=1, faz4_ref=None)
    return ledger, info


# ---------------------------------------------------------------- §13-5 fit yolu

def test_5_fit_path_is_v1_6_logit_with_candidate_policy(synth, monkeypatch):
    t, path = synth
    calls = []
    real = fitmod._fit_logit

    def counting(order, Y, inner, final, test, grid=fitmod.V1_5_GRID):
        calls.append(grid)
        return real(order, Y, inner, final, test, grid)

    monkeypatch.setattr(fitmod, "_fit_logit", counting)
    small = pbk.BreakTable(t.units[:30], {k: v for k, v in t.labels.items() if k in {u.ticker for u in t.units[:30]}}, {})
    ledger, _ = pbk.backtest_ledger(small, path, workers=1, faz4_ref=None)
    assert len(calls) > 0 and all(g == fitmod.V1_6_GRID for g in calls)
    assert fitmod.V1_6_GRID.convergence_policy == fitmod.POLICY_CANDIDATE and fitmod.V1_6_GRID.C_grid[0] == fitmod.ZERO
    assert sum(1 for r in ledger if r["status"] == "FIT_OK") + sum(
        1 for r in ledger if json.loads(r["inner_table_F2"])["status"] == "FIT_OK") == len(calls)


def test_5b_zero_rate_is_exact_fraction(synth, synth_ledger):
    t, _ = synth
    ledger, _ = synth_ledger
    folds = {f.fold_id: f for f in pbk.plan_break_folds(t)}
    for r in ledger:
        f = folds[r["fold_id"]]
        n1, n = f.events["F1"], len(f.training["F1"])
        if n:
            assert r["zero_F1"] == float(Fraction(n1, n)) == n1 / n
    ok = [r for r in ledger if r["status"] == "FIT_OK"]
    assert ok and all(json.loads(r["inner_table_F1"])["scores"].keys() >= {"ZERO", "0.0001", "100.0"} for r in ok
                      if json.loads(r["inner_table_F1"])["tuning_status"] == "TUNED_INNER_LOOCV")
    zero_rows = [r for r in ok if r["selected_C_F1"] == "ZERO"]
    for r in zero_rows:                                   # ZERO seçilirse p = eğitim oranı (bit-eşit)
        assert r["p_F1"] == r["zero_F1"] and r["coef_floor_F1"] == 0.0


def _freeze_k_ref(path: str) -> str:
    """K-PIN (SPEC_DEVIATIONS N25): `path`'teki fark dondurma görevinin başlangıcından (6d3f674) bu yana yalnız K commit'inden gelir.
    Dönen: karşılaştırma ucu — K commit'i (varsa; çalışma ağacı ona eşit olmalı) ya da görev başlangıcı (K henüz commit'lenmediyse:
    K'nın commit öncesi koşusu; HEAD'deki dosya başlangıçtakiyle aynı). Dondurma dosyaları ancak K commit'liyken var olabilir."""
    log = subprocess.run(["git", "log", "--format=%H %s", f"{FREEZE_TASK_BASE}..HEAD", "--", path], cwd=ROOT, check=True,
                         capture_output=True, text=True).stdout.splitlines()
    assert len(log) <= 1 and all(x.split(" ", 1)[1].startswith(FREEZE_K_SUBJECT) for x in log), log
    if not log:
        assert not fs8.frozen_post_break_files(), "dondurma dosyaları K commit'inden önce"
        return FREEZE_TASK_BASE
    k = log[0].split(" ", 1)[0]
    assert subprocess.run(["git", "diff", "--quiet", k, "--", path], cwd=ROOT).returncode == 0, path
    return k


def _task_commits_ref(path: str, subjects: tuple[str, ...]) -> str:
    """K-PIN-L (SPEC_DEVIATIONS N26; `_freeze_k_ref`'in genellemesi): `path`'teki fark dondurma görevinin başlangıcından (6d3f674) bu
    yana yalnız konusu `subjects`'ten biriyle başlayan commit'lerden gelir (her önek en çok bir kez). Dönen: karşılaştırma ucu (en son
    böyle commit; yoksa görev başlangıcı). Çalışma ağacı ona eşit olmalı; tek istisna canlı görevin commit öncesi koşusudur: geçmişte
    henüz hiçbir `BORSAI_FAZ8_LIVE_A:` commit'i yoksa ağaçtaki commit'siz A değişikliği kabul edilir (K'nın commit öncesi kalıbı).
    Dondurma dosyaları ancak K commit'liyken var olabilir (freeze.py için)."""
    log = subprocess.run(["git", "log", "--format=%H %s", f"{FREEZE_TASK_BASE}..HEAD", "--", path], cwd=ROOT, check=True,
                         capture_output=True, text=True).stdout.splitlines()
    prefixes = [next((p for p in subjects if x.split(" ", 1)[1].startswith(p)), None) for x in log]
    assert None not in prefixes and len(set(prefixes)) == len(prefixes), log
    if path == "borsai/freeze.py" and FREEZE_K_SUBJECT not in prefixes:
        assert not fs8.frozen_post_break_files(), "dondurma dosyaları K commit'inden önce"
    ref = log[0].split(" ", 1)[0] if log else FREEZE_TASK_BASE
    live_a = subprocess.run(["git", "log", "--format=%H", "--grep", f"^{LIVE_A_SUBJECT}", f"{FREEZE_TASK_BASE}..HEAD"], cwd=ROOT,
                            check=True, capture_output=True, text=True).stdout.split()
    if live_a or LIVE_A_SUBJECT not in subjects:
        assert subprocess.run(["git", "diff", "--quiet", ref, "--", path], cwd=ROOT).returncode == 0, path
    return ref


def _app_ui_commits_only() -> None:
    """K-PIN-UI (a) ve K-PIN-FIX (a) (SPEC_DEVIATIONS O; `_task_commits_ref` kalıbı): `7d78d43..HEAD` arasında app/'a dokunan her
    commit'in konusu APP_TASKS'taki öneklerden biriyle başlar; commit'lenmemiş app/ değişikliği yalnız listedeki SON görevin app/'a
    dokunan son commit'i (kapanış konusu) log'da yokken kabul edilir. app/parity/ 7d78d43'ten beri hiç değişmez (çalışma ağacı dahil)."""
    log = subprocess.run(["git", "log", "--format=%H %s", f"{BASE_COMMIT}..HEAD", "--", "app"], cwd=ROOT, check=True,
                         capture_output=True, text=True).stdout.splitlines()
    prefixes = tuple(p for p, _ in APP_TASKS)
    assert all(x.split(" ", 1)[1].startswith(prefixes) for x in log), log
    assert subprocess.run(["git", "diff", "--quiet", BASE_COMMIT, "--", "app/parity"], cwd=ROOT).returncode == 0, "app/parity"
    closed = subprocess.run(["git", "log", "--format=%H", "--grep", f"^{APP_TASKS[-1][1]}", f"{BASE_COMMIT}..HEAD"], cwd=ROOT,
                            check=True, capture_output=True, text=True).stdout.split()
    if closed:
        status = subprocess.run(["git", "status", "--porcelain", "--", "app"], cwd=ROOT, check=True, capture_output=True,
                                text=True).stdout
        assert status == "", status


@pytest.mark.requires_git_history
def test_5c_old_goldens_and_app_pins_unchanged():
    # K-PIN (SPEC_DEVIATIONS N25): dondurmadan önce models/ farkı boş; sonra yalnız eklenen üç dosya (fs8.frozen_post_break_files)
    frozen = sorted(f"models/{n}" for n in fs8.frozen_post_break_files())
    out = subprocess.run(["git", "diff", "--name-only", BASE_COMMIT, "--", "tests/reference", "models"], cwd=ROOT, check=True,
                         capture_output=True, text=True).stdout
    assert out.split() == frozen
    _app_ui_commits_only()    # K-PIN-UI (a) / K-PIN-FIX (a): app yol listesinden çıktı; yerine görev listesi iddiaları
    added = subprocess.run(["git", "diff", "--name-only", "--diff-filter=A", BASE_COMMIT, "--", "models"], cwd=ROOT, check=True,
                           capture_output=True, text=True).stdout
    assert added.split() == frozen
    for name in ("features", "horizons", "predict", "predict_fall", "predict_hazard", "predict_market20", "predict_path", "predict_pb",
                 "predict_post_d1", "survival", "tufe"):
        assert subprocess.run(["git", "diff", "--quiet", BASE_COMMIT, "--", f"borsai/{name}.py"], cwd=ROOT).returncode == 0, name
    for name in ("preprocess", "fit", "backtest", "metrics", "post_d1", "ceiling_path", "outcomes"):
        assert subprocess.run(["git", "diff", "--quiet", BASE_COMMIT, "--", f"borsai/{name}.py"], cwd=ROOT).returncode == 0, name
    # freeze.py, scoring.py, registry.py: 7d78d43 → 6d3f674 değişmedi; sonrası yalnız dondurma görevinin K commit'i (K-PIN) ve canlı
    # POST_BREAK görevinin A commit'i (K-PIN-L, N26); specs.py: yalnız K ve K da yalnız ekler
    for name in ("freeze", "scoring", "registry"):
        assert subprocess.run(["git", "diff", "--quiet", BASE_COMMIT, FREEZE_TASK_BASE, "--", f"borsai/{name}.py"],
                              cwd=ROOT).returncode == 0, name
        _task_commits_ref(f"borsai/{name}.py", (FREEZE_K_SUBJECT, LIVE_A_SUBJECT))
    _freeze_k_ref("borsai/specs.py")
    rdiff = subprocess.run(["git", "diff", "-U0", BASE_COMMIT, "--", "borsai/report.py"], cwd=ROOT, check=True, capture_output=True,
                           text=True).stdout.splitlines()
    removed = [x for x in rdiff if x.startswith("-") and not x.startswith("---")]
    added = [x for x in rdiff if x.startswith("+") and not x.startswith("+++")]
    assert removed == ["-skorlar yeniden üretilince bu belge de yeniden üretilir."]           # yalnız Faz 8 kancası (N19)
    assert len(added) == 6 and sum("faz8" in x.lower() or "Faz 8" in x for x in added) >= 4
    diff = subprocess.run(["git", "diff", BASE_COMMIT, "--", "borsai/specs.py"], cwd=ROOT, check=True, capture_output=True,
                          text=True).stdout
    assert not [x for x in diff.splitlines() if x.startswith("-") and not x.startswith("---")]      # specs.py: yalnız ekleme
    res = subprocess.run([sys.executable, "app/parity/gen_golden.py", "--check"], cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 0 and json.loads(res.stdout)["different"] == [], res.stdout + res.stderr


# ---------------------------------------------------------------- §13-6 ürün karşılaştırıcısı

def _const_cells(v: float) -> dict:
    return {(g, m): [(v, f"X{i}") for i in range(12)] for g in pth.GROUPS for m in range(1, pth.M_MAX[g] + 1)}


def test_6_product_extremes():
    P = "10.00"
    closes = [str(pth.upper_limit(pth.snap(Decimal(P))))]
    closes.append(str(pth.upper_limit(Decimal(closes[0]))))
    closes.append(str(pth.lower_limit(Decimal(closes[1]))))           # L = 2, b = 3: tabanda bozuldu
    down = pb.product_from_cells(_const_cells(-0.5), P, 2, closes)      # hücreler fiziksel sınıra (0.9^m − 1) kırpılır: çift taban
    assert down["F1"] == pytest.approx(1.0, abs=1e-12) and down["F2"] == pytest.approx(1.0, abs=1e-12) and down["status"] == "OK"
    up = pb.product_from_cells(_const_cells(0.05), P, 2, closes)
    assert up["F1"] == 0.0 and up["F2"] == 0.0
    z = pb.product_from_cells(_const_cells(-0.5), P, 0, [str(pth.lower_limit(pth.snap(Decimal(P))))])    # L = 0 (Z grubu, ölçek yok)
    assert z["F1"] == pytest.approx(1.0, abs=1e-12)
    b9 = pb.product_from_cells(_const_cells(-0.5), P, 8, [closes[0]] * 9)
    assert b9["F2"] is None and b9["F1"] is not None
    empty = {k: [] for k in _const_cells(0.0)}
    ins = pb.product_from_cells(empty, P, 2, closes)
    assert ins["status"] == "POST_BREAK_INSUFFICIENT" and ins["F1"] is None and ins["F2"] is None


def test_6b_atoms_are_conditional_after_break_atoms(table, path_units, monkeypatch):
    """(c): aynı atomlar — `predict_path.conditional_after_break` özetleri (medyan, p_up, ortalama, q10/q50/q90) atomlarımızın özetiyle
    bit-eşit; ikinci karışım kodu yok (`mixture_atoms` çağrılır)."""
    template = pd.load_path_template()
    calls = []
    real = pth.mixture_atoms
    monkeypatch.setattr(pth, "mixture_atoms", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    cache = pbk.CellCache(path_units)
    checked = 0
    for u in table.breaks()[::3]:
        cells, _ = cache.get(u.first_trading_date)
        params = pd.fold_path_params(template, cells)
        output = pd.fold_path_output(Decimal(u.ipo_price), [0.5] * 10)
        out = pb.product_break_floor(params, output, u.L, u.closes)
        cond = out["conditional"]
        for head, h in (("F1", u.b + 1), ("F2", u.b + 2)):
            if h > 10:
                continue
            atoms, _, ok = pb.product_atoms(cells, u.ipo_price, u.L, u.closes, h)
            if not ok:
                assert cond[f"D{h}"]["status"] == "POST_BREAK_INSUFFICIENT"
                continue
            s = pth.summarize(atoms)
            for k in ("return", "p_up", "mean", "q10", "q50", "q90"):
                assert s[k] == cond[f"D{h}"][k], (u.ticker, h, k)
            checked += 1
        same = pb.product_from_cells(cells, u.ipo_price, u.L, u.closes)
        assert (same["F1"], same["F2"]) == (out["F1"], out["F2"])
    assert checked >= 40 and calls


def test_6c_cells_match_faz4_ledger_87_folds(path_units):
    res = pbk.faz4_cell_parity(pbk.CellCache(path_units))
    assert res["n_checked"] == 87


def test_6d_product_insufficient_is_counted(table, path_units):
    cache = pbk.CellCache(path_units)
    statuses = []
    for u in table.breaks():
        cells, _ = cache.get(u.first_trading_date)
        prod = pb.product_from_cells(cells, u.ipo_price, u.L, u.closes)
        statuses.append(prod["status"])
        for head in ("F1", "F2"):
            if head in prod["cells"]:
                assert (prod[head] is None) == any(c["n"] < pth.N_MIN for c in prod["cells"][head])
        assert (prod["status"] == "OK") == all(prod[h] is not None for h in prod["cells"])
    assert len(statuses) == 82 and set(statuses) <= {"OK", "POST_BREAK_INSUFFICIENT"}


# ---------------------------------------------------------------- §13-9 JSON ↔ stdlib paritesi

def test_9_numpy_vs_stdlib_parity_synthetic(synth):
    t, _ = synth
    for m in FAZ8_MODEL_IDS:
        params, fits = pbk.build_params(m, t, "synthetic", check=False)
        params = json.loads(pretty_json_bytes(params))                 # yazılan dosyanın gidiş-dönüşü (sıralı anahtar)
        pb.check_params(params)
        par = pbk.parity_rows(params, fits, t)
        assert max(par.values()) <= pbk.PARITY_TOL, (m, par)
        assert sorted(params["horizons"]) == ["F1", "F2"]
    model, _ = pbk.build_params(pbk.MODEL_ID, t, "synthetic", check=False)
    assert set(model["preprocessing"]) == {"F1", "F2"} and model["training"]["n_F1"] > model["training"]["n_F2"]
    assert set(model["comparators"]["by_type_F1"]) == {"0", "1"}


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


def test_9b_predict_break_import_closure_is_stdlib():
    pkg = ROOT / "borsai"
    seen, queue, closure = set(), ["predict_break"], {}
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
    assert set(closure) <= {"predict_break", "predict_path", "predict", "predict_hazard", "features", "horizons", "survival"}


# ---------------------------------------------------------------- §13-10 etiket kuralları

def _cell(mean, lo, hi, n=65, months=22):
    return {"mean": mean, "ci95": None if lo is None else [lo, hi], "n": n, "n_months": months}


def test_10_too_good_triggers():
    assert r8.too_good({"F1_product": _cell(-0.17, -0.25, -0.07), "F1_zero": _cell(-0.04, -0.07, -0.01)}) == \
        ["birincil fark < -0.160"]
    assert r8.too_good({"F1_product": _cell(-0.10, -0.15, -0.079), "F1_zero": _cell(-0.04, -0.07, -0.01)}) == []
    assert r8.too_good({"F1_product": _cell(-0.10, -0.15, -0.081), "F1_zero": _cell(-0.04, -0.07, -0.01)}) == \
        ["birincil aralığın üst ucu < -0.080"]
    assert r8.too_good({"F1_product": _cell(-0.08, -0.14, -0.02), "F1_zero": _cell(-0.095, -0.15, -0.04)}) == \
        ["F1 − @ZERO farkı < -0.090"]


def test_10b_diff_labels_and_positions():
    rows = {(r["kind"], r.get("cell")): r for r in r8.expectation_rows()}
    prim = rows[("diff", "F1_product")]
    assert (prim["lo"], prim["hi"], prim["ci_category"]) == (-0.14, -0.02, "MAY_EXCLUDE_NEG")
    assert r8.diff_label(prim, _cell(-0.08, -0.13, -0.03)) == "tuttu"
    assert r8.diff_label(prim, _cell(-0.08, -0.13, 0.01)) == "tuttu"                  # kesin kısım: alt uç ≤ 0
    assert r8.ci_statement_holds("MAY_EXCLUDE_NEG", [-0.13, 0.01]) is False            # ifadenin tamamı (üst uç < 0) ayrı
    assert r8.diff_label(prim, _cell(-0.03, 0.001, 0.05)) == "tutmadı (aralık)"        # alt uç > 0
    assert r8.diff_label(prim, _cell(-0.15, -0.2, -0.1)) == "tutmadı (daha iyi)"
    assert r8.diff_label(prim, _cell(0.01, -0.02, 0.04)) == "tutmadı (daha kötü)"
    assert r8.diff_label(prim, _cell(-0.08, None, None)) == "tutmadı (aralık yok)"
    assert r8.diff_label(prim, None) == "tutmadı (hücre yok)"
    assert r8.position(-0.15, -0.14, -0.02) == "altında" and r8.position(-0.14, -0.14, -0.02) == "aralık içinde"
    assert r8.position(-0.019, -0.14, -0.02) == "üstünde"
    zero = rows[("diff", "F1_zero")]
    assert (zero["lo"], zero["hi"], zero["ci_category"]) == (-0.08, 0.0, "MAY_EXCLUDE_NEG")
    inc = rows[("diff", "F1_by_type")]
    assert r8.diff_label(inc, _cell(0.0, -0.01, 0.01)) == "tuttu" and r8.diff_label(inc, _cell(-0.01, -0.02, -0.001)) == "tutmadı (aralık)"
    notpos = rows[("diff", "F2_product")]
    assert notpos["ci_category"] == "NOT_POS" and r8.diff_label(notpos, _cell(-0.05, 0.001, 0.09)) == "tutmadı (aralık)"
    info = rows[("diff", "info_product_zero_F1")]
    assert info["ci_category"] == "NOT_NEG" and r8.diff_label(info, _cell(0.04, -0.01, 0.09)) == "tuttu"
    assert r8.diff_label(info, _cell(0.0, -0.05, -0.001)) == "tutmadı (aralık)"


def test_10c_k1_and_failures():
    good = {"F1_product": _cell(-0.08, -0.13, -0.03), "F1_zero": _cell(-0.04, -0.07, -0.01)}
    assert r8.k1(good)["holds"] is True
    weak = {"F1_product": _cell(-0.08, -0.13, -0.03), "F1_zero": _cell(-0.02, -0.05, 0.01)}
    k = r8.k1(weak)
    assert k["holds"] is False and k["legs"] == {"birincil (− ürün)": True, "− @ZERO": False}
    f = r8.failures(weak, 1.0, 0.1, {"n": 60, "diff": 0.02})
    assert f == {"a": True, "b": False, "c": False, "d": False}
    f = r8.failures({"F1_product": _cell(0.05, 0.01, 0.09), "F1_zero": _cell(0.03, 0.01, 0.05)}, "ZERO", 0.6, {"n": 30, "diff": -0.2})
    assert f == {"a": False, "b": True, "c": True, "d": True}
    assert r8.failures(good, 0.1, 0.5, {"n": 29, "diff": 0.5}) == {"a": False, "b": False, "c": True, "d": False}


def test_10d_rules_text_fixed_before_results():
    assert len(OPERATIONAL_RULES_FAZ8) == 13
    text = " ".join(OPERATIONAL_RULES_FAZ8)
    for needle in ("−0.160", "−0.080", "−0.090", "0.06", "%90", "[0.1, 1]", "%20", "[60, 69]", "[55, 65]", "%50", "0.15",
                   "random.Random(20260921)", "tasarıma maruz"):
        assert needle in text, needle


# ---------------------------------------------------------------- §13-15 günlük ve ölçek

def test_15_log_lines_and_variant_counter(dataset, synth_small, tmp_path):
    t, path = synth_small
    log = tmp_path / "log.jsonl"
    res = pbk.run_backtest(dataset, log_path=log, context="pytest", workers=1, table=t, path_units=path, faz4_ref=None)
    for n in FAZ8_SENSITIVITIES:
        pbk.run_sensitivity(n, dataset, log_path=log, context="pytest", ledger_file=f"sens/{n}.csv", workers=1, table=t,
                            path_units=path, out_dir=tmp_path, faz4_ref=None)
    lines = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert [e["kind"] for e in lines] == ["backtest", "sensitivity", "sensitivity", "sensitivity"]
    e = lines[0]
    doc = SPEC_DOCUMENTS_FAZ8["SPEC_BREAK_V0"]
    assert e["spec_document_sha256"] == sha256_file(ROOT / doc["path"]) == doc["sha256"]
    assert e["decisions_document_sha256"] == sha256_file(ROOT / SPEC_DOCUMENTS_FAZ8["KARARLAR_FAZ8"]["path"])
    assert e["spec_sha256"] == spec_sha256(POST_BREAK_MODEL_SPECS[pbk.MODEL_ID]) and e["model_id"] == pbk.MODEL_ID
    assert e["ledger_sha256"] == sha256_bytes(res.ledger_csv) and e["plan_id"] == pbk.PLAN_BREAK_H99
    assert {"git_commit", "borsai_dirty", "borsai_source_sha256", "runtime", "near_era", "metrics", "sessions_file_sha256",
            "path_cells_source", "started_at", "finished_at"} <= set(e)
    assert e["rule_rows_in_ledger"][pbk.ZERO_ID]["spec_sha256"] == spec_sha256(POST_BREAK_MODEL_SPECS[pbk.ZERO_ID])
    for s in lines[1:]:
        assert s["is_model"] is False and "model değil" in s["note"] and s["base_model_id"] == pbk.MODEL_ID
        assert s["model_id"] in FAZ8_SENSITIVITIES and sha256_file(tmp_path / s["ledger_file"]) == s["ledger_sha256"]
        assert s["spec_document_sha256"] == doc["sha256"]
    nv, nr = sc._n_variants_same_data(dataset.data_version_sha256, pbk.MODEL_ID, log_path=log)
    assert (nv, nr) == (1, 1)                         # backtest satırı sayılır, duyarlılıklar sayılmaz (kart sayacı)
    assert len({s["spec_sha256"] for s in lines}) == 4


def test_15b_scale_mix_is_refused(synth_ledger):
    ledger, _ = synth_ledger
    rows = [{k: pbk._fmt(v) for k, v in r.items()} for r in ledger]
    with pytest.raises(pbk.ScaleMixError):
        pbk.paired_brier(rows, "p_F1", "zero_F1", realized="realized_F1", scale="backtest_conditional")
    c = pbk.paired_brier(rows, "p_F1", "zero_F1", realized="realized_F1")
    assert c["scale"] == "backtest_break"
    with pytest.raises(pbk.ScaleMixError):
        pbk.merge_cells(c, {"scale": "live"})
    with pytest.raises(pbk.ScaleMixError):
        pbk.merge_cells(c, c)


def test_15c_ledger_columns_fixed_and_report_renders_synthetic(dataset, synth_small, synth_ledger, tmp_path):
    t, path = synth_small
    ledger, _ = synth_ledger
    assert all(tuple(r) == pbk.LEDGER_COLUMNS for r in ledger) and len(pbk.LEDGER_COLUMNS) == 47
    log = tmp_path / "log.jsonl"
    res = pbk.run_backtest(dataset, log_path=log, context="pytest", workers=1, table=t, path_units=path, faz4_ref=None)
    out = tmp_path / "golden"
    sens = {n: pbk.run_sensitivity(n, dataset, log_path=log, context="pytest", ledger_file=f"golden/{n}_fold_ledger.csv", workers=1,
                                   table=t, path_units=path, out_dir=tmp_path, faz4_ref=None) for n in FAZ8_SENSITIVITIES}
    previews, parity = {}, {}
    for m in FAZ8_MODEL_IDS:
        params, fits = pbk.build_params(m, t, "synthetic", check=False)
        previews[m], parity[m] = params, pbk.parity_rows(params, fits, t)
    pbk.write_golden(res, sens, previews, parity, out_dir=out)
    lines: list[str] = []
    r8.render_faz8(lines.append, log, out_dir=out)
    text = "\n".join(lines)
    assert text.startswith("## Faz 8: kırılma akşamı")
    for rule in OPERATIONAL_RULES_FAZ8:
        assert rule in text
    sec6 = text.split("### §6 önceden yazılmış beklenti, satır satır")[1].split("### Keşif")[0]
    assert sum(1 for line in sec6.splitlines() if line.startswith("| ") and not line.startswith("| Hücre")) == 13
    assert "Hüküm sayıları: tuttu" in text and "backtest" in text
    assert not any(n in text for n in FAZ8_SENSITIVITIES)              # duyarlılık kimlikleri belgeye girmez (test_experiment_log)
    lines2: list[str] = []
    r8.render_faz8(lines2.append, log, out_dir=tmp_path / "yok")
    assert lines2 == []

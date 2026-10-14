"""borsai/scoring.py: SPEC_SCORING §10 kabul testleri 5–9 ve 11 (sınıflama, birincil kayıt, payda, bootstrap, dil,
RPS); backtest hücrelerinin docs/MODELS.md ile aynı olması; scores.json şeması ve küçük-n kuralları."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from borsai import registry as reg
from borsai import report as r1
from borsai import report_faz1b as rf
from borsai import scoring as sc
from borsai import survival as sv
from borsai.horizons import HORIZONS
from borsai.provenance import ROOT, sha256_file

import faz5_support as fs
import faz7_support as fs7
import faz7c_support as fs7c
import faz8_support as fs8

MODELS_MD = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
CLASS_KEYS = {"class", "record_class", "classification", "live_class", "klass"}


@pytest.fixture(scope="module")
def scores():
    """Ağsız ve dosya yazmadan yeniden hesap (commit edilen scores.json ile karşılaştırma için de)."""
    return sc.build_scores()


def by_model(scores, model_id):
    return next(m for m in scores["models"] if m["model_id"] == model_id)


# ---------------------------------------------------------------- §10-5 sınıflama (geçici git deposu)

def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


def _commit(root, rel, text="x"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    _git(root, "add", rel)
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", rel)
    return _git(root, "rev-parse", "HEAD")


def _proof(sha, created_at):
    return {"proven_commit_sha": sha, "created_at": created_at}


def scenario(tmp_path, steps, *, pit_ok=True, d1="2026-09-17"):
    """steps: sırayla ('model'|'record'|'outcome', kanıt zamanı ya da None)."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    paths = {"model": "models/m.json", "record": "registry/records/X/r.json", "outcome": "data/outcomes/X.csv"}
    proofs, commits = [], {}
    for what, at in steps:
        commits[what] = _commit(root, paths[what])
        if at:
            proofs.append(_proof(commits[what], at))
    git = sc.Git(root)
    model_ev = sc.model_evidence(git, "m.json", proofs)
    oc_commit = sc.outcome_ingest_commit(git, "X", [])
    cand = reg.Candidate("r.json", "m", "REGISTRY", True, "2026-09-10T00:00:00Z",
                         push_created_at=sc.proof_time(git, git.added_commit(paths["record"]), proofs), inputs_pit_ok=pit_ok)
    return sc.pair_class(git, model_ev, oc_commit, cand, d1)


def test_5a_live(tmp_path):
    cls, ev = scenario(tmp_path, [("model", "2026-09-01T10:00:00Z"), ("record", "2026-09-10T10:00:00Z"), ("outcome", None)])
    assert cls == sc.CLASS_LIVE and ev["model_prospective"] and ev["record_live"]


def test_5b_late_record(tmp_path):
    cls, ev = scenario(tmp_path, [("model", "2026-09-01T10:00:00Z"), ("outcome", None), ("record", "2026-09-20T10:00:00Z")])
    assert cls == sc.CLASS_LATE and ev["model_prospective"] and not ev["record_live"]


def test_5c_outcome_before_model_is_retro(tmp_path):
    cls, ev = scenario(tmp_path, [("outcome", None), ("model", "2026-09-01T10:00:00Z"), ("record", "2026-09-10T10:00:00Z")])
    assert cls == sc.CLASS_RETRO and not ev["model_prospective"]


def test_5d_no_push_proof_is_retro(tmp_path):
    cls, ev = scenario(tmp_path, [("model", None), ("record", None), ("outcome", None)])
    assert cls == sc.CLASS_RETRO and ev["model_push_proof_created_at"] is None


def test_5e_inputs_not_pit_is_retro(tmp_path):
    cls, _ = scenario(tmp_path, [("model", "2026-09-01T10:00:00Z"), ("outcome", None), ("record", "2026-09-20T10:00:00Z")],
                      pit_ok=False)
    assert cls == sc.CLASS_RETRO


def test_5f_uncommitted_outcome_checked_against_head(tmp_path):
    cls, ev = scenario(tmp_path, [("model", "2026-09-01T10:00:00Z"), ("record", "2026-09-10T10:00:00Z")])
    assert cls == sc.CLASS_LIVE and ev["outcome_ingest_basis"] == "UNCOMMITTED_CHECKED_AGAINST_HEAD"


def test_5g_descendant_proof_covers_ancestor(tmp_path):
    """Kanıt torun commit için üretildiyse atası da kapsanır (push_proof modülü ile aynı kural)."""
    cls, ev = scenario(tmp_path, [("model", None), ("record", "2026-09-10T10:00:00Z"), ("outcome", None)])
    assert ev["model_push_proof_created_at"] == "2026-09-10T10:00:00Z" and cls == sc.CLASS_LIVE


def test_5h_formula_is_pure():
    assert sc.classify(True, True, False) == sc.CLASS_LIVE
    assert sc.classify(True, False, True) == sc.CLASS_LATE
    assert sc.classify(True, False, False) == sc.CLASS_RETRO
    assert sc.classify(False, True, True) == sc.CLASS_RETRO


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


def test_5i_no_hand_class_field_in_any_input():
    """Sınıf, skorlamanın okuduğu hiçbir girdi dosyasında elle yazılı değil: tahmin kayıtları, girdi belgeleri,
    legacy rolleri, push kanıtları, payda. (registry/legacy_frozen eski repodan birebir kopyadır; skorlama oradan
    yalnız tahmin değerlerini ve girdi paketini okur, hiçbir sınıf alanını okumaz.)"""
    files = [*(ROOT / "registry" / "records").rglob("*.json"), *(ROOT / "registry" / "inputs").glob("*.json"),
             *(ROOT / "registry" / "push_proofs").glob("*.json"), ROOT / "registry" / "legacy_roles.json"]
    assert len(files) > 10
    for p in files:
        assert not set(_keys(json.loads(p.read_text(encoding="utf-8")))) & CLASS_KEYS, p
    header, _ = reg.read_ipos()
    assert not set(header) & CLASS_KEYS


@pytest.mark.requires_git_history
def test_5j_every_class_in_scores_is_recomputed_from_evidence(scores):
    for m in scores["models"]:
        for r in m["live"]["rows"]:
            ev = r["class_evidence"]
            assert r["class"] == sc.classify(ev["model_prospective"], ev["record_live"], ev["inputs_pit_ok"])
            assert r["class"] in sc.PROSPECTIVE_CLASSES
        for r in m["live"]["self_reported_rows"]:
            assert r["class"] == sc.CLASS_LEGACY_SELF and r["class_evidence"]["record_track"] == "SELF_REPORTED"


# ---------------------------------------------------------------- §10-6 birincil kayıt

@pytest.mark.requires_raw_sources
def test_6_primary_records(scores):
    v15 = by_model(scores, "v1_5_h99")
    rows = {r["ticker"]: r for r in v15["live"]["rows"]}
    self_rows = {r["ticker"]: r for r in v15["live"]["self_reported_rows"]}
    # BKRGY: üç legacy kaydından yalnız 20260827_POST_BOOKBUILD skorlanır (ikincil iz); R1/R2 geçersiz kullanım
    assert self_rows["BKRGY"]["record_id"] == "BKRGY_20260827_V1_5_POST_BOOKBUILD_PRE_LISTING"
    assert self_rows["INTET"]["record_id"] == "INTET_20260831_V1_5_POST_BOOKBUILD_PRE_LISTING"
    invalid = {(r["ticker"], r["record_id"]) for r in v15["live"]["invalid_use_rows"]}
    assert invalid == {("BKRGY", "BKRGY_20260825_V1_5"), ("BKRGY", "BKRGY_20260825_V1_5_R2"), ("INTET", "INTET_20260825_V1_5")}
    used = {r["record_id"] for m in scores["models"] for r in m["live"]["rows"] + m["live"]["self_reported_rows"]}
    assert not used & {rid for _, rid in invalid}
    # NETGL: legacy git+push kaydı birincil ve LIVE
    netgl = rows["NETGL"]
    assert netgl["record_id"] == "NETGL_20260916_V1_5" and netgl["class"] == sc.CLASS_LIVE
    assert netgl["class_evidence"]["record_track"] == "GIT_PUSH" and netgl["selection_rule"] == "LATEST_PUSH_PROVEN_BEFORE_D1"
    assert netgl["class_evidence"]["record_push_proof_created_at"] == "2026-09-16T11:32:27Z"
    # TKNKA: v1_5_h99 satırı sicil kaydıdır; FULL20 kaydı yalnız ayrı modelin listesinde
    assert rows["TKNKA"]["record_source"] == "REGISTRY"
    assert "TKNKA_20260819_V1_5_FULL20" not in used
    [full20] = scores["separate_models"]
    assert full20["model_id"] == "v1_5_full20" and not full20["in_models_index"] and full20["cells"] == []
    assert [(r["ticker"], r["record_id"]) for r in full20["rows"]] == [("TKNKA", "TKNKA_20260819_V1_5_FULL20")]


@pytest.mark.requires_raw_sources
def test_6b_f3_models_refuse_without_f3_and_pb_models_use_earliest(scores):
    for m in ("v1_5_h99", "v1_6_h99", "v1_5_market20_v0", "ceiling_hazard_v0"):
        veyas = next(r for r in by_model(scores, m)["live"]["rows"] if r["ticker"] == "VEYAS")
        assert veyas["status"] == sc.ROW_REFUSED and veyas["prediction"]["refused"]["code"] == "F3_MISSING"
    for m in ("pb_v0", "pb_ceiling_v0", "base_train_median"):
        for r in by_model(scores, m)["live"]["rows"]:
            assert r["selection_rule"] == "EARLIEST_RECORD"


def test_6c_primary_selection_rule_directly():
    """select_primary: f3 modelinde D_1'den önce kanıtlı en son kayıt, yoksa en erken LATE."""
    c = lambda rid, push, rec, **kw: reg.Candidate(rid, "v1_5_h99", kw.pop("track", "REGISTRY"), True, rec,  # noqa: E731
                                                   push_created_at=push, **kw)
    sel = reg.select_primary("v1_5_h99", [c("a", "2026-09-01T00:00:00Z", "1"), c("b", "2026-09-05T00:00:00Z", "2"),
                                          c("late", "2026-09-30T00:00:00Z", "3")], "2026-09-10")
    assert sel["proven"] == {"record_id": "b", "rule": "LATEST_PUSH_PROVEN_BEFORE_D1"}
    sel = reg.select_primary("v1_5_h99", [c("x", "2026-09-30T00:00:00Z", "2"), c("y", "2026-10-01T00:00:00Z", "1"),
                                          c("z", "2026-09-29T00:00:00Z", "0", cancelled=True)], "2026-09-10")
    assert sel["proven"] == {"record_id": "x", "rule": "EARLIEST_LATE_RECORD"}


# ---------------------------------------------------------------- §10-7 payda

@pytest.mark.requires_git_history
def test_7_denominator(scores):
    header, rows = reg.read_ipos()
    assert reg.validate_ipos(header, rows) == []
    for r in rows:
        if r["status"] != "FROZEN":
            assert reg.valid_skip_reason(r["skip_reason"])
    assert set(reg.KNOWN_TICKERS) <= {r["ticker"] for r in rows}
    n_skipped = sum(r["status"] == "SKIPPED" for r in rows)
    for m in scores["models"]:
        assert m["live"]["n_skipped"] == n_skipped
    assert {r["ticker"] for r in scores["skipped"]} == {r["ticker"] for r in rows if r["status"] != "FROZEN"}
    assert [o["ticker"] for o in scores["outcomes"]] == [r["ticker"] for r in rows if r["status"] in reg.IPO_STATUSES]


# ---------------------------------------------------------------- §10-8 bootstrap

def test_8a_bootstrap_deterministic_and_conditions():
    d = [0.01 * ((i * 7) % 11 - 5) for i in range(40)]
    blocks = [f"2026-{1 + i % 8:02d}" for i in range(40)]
    a, b = sc.block_bootstrap_ci(d, blocks), sc.block_bootstrap_ci(d, blocks)
    assert a == b and a[0] < a[1]
    assert sc.block_bootstrap_ci(d[:9], blocks[:9]) is None                       # n = 9
    assert sc.block_bootstrap_ci(d, [f"2026-{1 + i % 5:02d}" for i in range(40)]) is None   # 5 blok


def test_8b_bootstrap_reproduces_audit_d1_mae_vs_median():
    """H99 fold ledger'ından D1 MAE (V1.5 − medyan): +0.0046 ve aralık [+0.0015, +0.0079] ±0.001 (numpy PCG64)."""
    v15 = r1._read(r1.GOLDEN_DIR / r1.golden_filename("v1_5_h99"))
    med = {r["fold_id"]: r for r in r1._read(r1.GOLDEN_DIR / r1.golden_filename("base_train_median"))}
    d, blocks = [], []
    for r in v15:
        if r["horizon"] == "D1" and r["ridge_status"] == "FIT_OK":
            y = float(r["realized_return"])
            d.append(abs(float(r["ridge_prediction"]) - y) - abs(float(med[r["fold_id"]]["rule_return"]) - y))
            blocks.append(r["prediction_date"][:7])
    assert len(d) == 89
    assert round(sum(d) / len(d), 4) == 0.0046
    lo, hi = sc.block_bootstrap_ci(d, blocks)
    assert abs(lo - 0.0015) <= 0.001 and abs(hi - 0.0079) <= 0.001, (lo, hi)


# ---------------------------------------------------------------- §10-9 dil

def _obs(n, diffs, scale=sc.SCALE_LIVE):
    return [sc.PairedObs(scale, f"T{i}", f"2026-{1 + i % 8:02d}", 0.5 + diffs[i % len(diffs)], 0.5, sc.CLASS_LATE)
            for i in range(n)]


def test_9a_interval_including_zero_says_indistinguishable():
    res = sc.paired_metric(_obs(40, [0.02, -0.02, 0.01, -0.01]))
    assert res["ci95"][0] < 0 < res["ci95"][1] and res["verdict"] == "ayırt edilemiyor"
    passing = sc.paired_metric(_obs(40, [-0.02, -0.03, -0.01]))
    assert passing["ci95"][1] < 0 and passing["verdict"] == "geçiyor"
    failing = sc.paired_metric(_obs(40, [0.02, 0.03, 0.01]))
    assert failing["verdict"] == "geçemiyor"
    small = sc.paired_metric(_obs(12, [-0.02, -0.03, -0.01]))
    assert small["verdict"] == "yetersiz örnek"                         # 10 ≤ n < 30: "geçiyor" yok


def test_9b_small_n_has_no_metric_fields():
    res = sc.paired_metric(_obs(7, [-0.05]))
    assert res["n"] == 7 and all(res[k] is None for k in ("model_value", "rule_value", "diff", "ci95", "wins", "verdict"))


@pytest.mark.requires_git_history
def test_9c_live_block_row_table_only_below_ten(scores):
    for m in scores["models"]:
        live = m["live"]
        assert live["title"] == sc.LIVE_TITLE and m["backtest"]["title"] == sc.BACKTEST_TITLE
        assert live["n_live"] + live["n_late"] == live["n_scored"]
        if live["n_scored"] < sc.MIN_N_METRIC:
            assert live["cells"] == [] and live["self_reported_cells"] == []
        assert len(live["rows"]) == live["n_rows"]


def test_9d_scales_never_combined():
    with pytest.raises(sc.ScaleMixError):
        sc.paired_metric(_obs(12, [0.01]) + _obs(12, [0.01], scale=sc.SCALE_BACKTEST))
    with pytest.raises(sc.ScaleMixError):
        sc.merge_scales({"scale": sc.SCALE_BACKTEST}, {"scale": sc.SCALE_LIVE})


@pytest.mark.requires_git_history
def test_9e_verdict_vocabulary(scores):
    for m in scores["models"]:
        for c in m["backtest"]["cells"] + m["live"]["cells"]:
            assert c["verdict"] in sc.VERDICTS
            if c["verdict"] in ("geçiyor", "geçemiyor"):
                assert c["n"] >= 30 and c["ci95"] is not None and not (c["ci95"][0] <= 0 <= c["ci95"][1])
            if c["verdict"] == "ayırt edilemiyor":
                assert c["ci95"][0] <= 0 <= c["ci95"][1]


# ---------------------------------------------------------------- §10-11 RPS

def test_11_rps():
    for L in range(0, 11):
        S = [1.0 if L >= k else 0.0 for k in range(1, 11)]
        assert sv.rps(S, L) == 0.0
    assert sv.rps([1.0] * 10, 0) == 1.0
    assert sv.rps([1.0] * 10, 10) == 0.0
    assert sc.loss_rps([1.0] * 10, 0) == 1.0


# ---------------------------------------------------------------- backtest hücreleri = docs/MODELS.md

def _section(start, end=None):
    i = MODELS_MD.index(start)
    j = MODELS_MD.index(end, i + len(start)) if end else len(MODELS_MD)
    return MODELS_MD[i:j]


def _p(c):
    lo, hi = c["ci95"]
    verdict = "KURAL_DAHA_IYI" if lo > 0 else "MODEL_DAHA_IYI" if hi < 0 else "AYIRT_EDILEMIYOR"
    return {"n": c["n"], "n_months": c["n_blocks"], "model_metric": c["model_value"], "rule_metric": c["rule_value"],
            "mean": c["diff"], "ci95": c["ci95"], "model_better_n": c["wins"], "rule_better_n": c["losses"],
            "tie_n": c["ties"], "verdict": verdict}


def test_backtest_cells_equal_models_md():
    runs = rf.load_runs()
    sections = {
        "v1_5_h99": _section("## Eşleşik farklar: V1.5 − basit kural", "## Faz 1A modellerinin"),
        "v1_6_h99": _section("### `v1_6_h99`", "### `v1_5_market20_v0`"),
        "v1_5_market20_v0": _section("### `v1_5_market20_v0`", "### `pb_v0`"),
        "pb_v0": _section("### `pb_v0`", "### `ceiling_hazard_v0`"),
        "ceiling_hazard_v0": _section("### `ceiling_hazard_v0`", "### `pb_ceiling_v0`"),
        "pb_ceiling_v0": _section("### `pb_ceiling_v0`", "### Faz 1B koşuları"),
    }
    checked = 0
    for model_id, text in sections.items():
        cells = sc.backtest_cells(model_id, runs)
        assert cells and all(c["scale"] == sc.SCALE_BACKTEST for c in cells)
        per_k = {}
        for c in cells:
            p = _p(c)
            if model_id == "v1_5_h99":
                lo, hi = p["ci95"]
                line = (f"| {c['horizon_or_k']} | `{c['rule_id']}` | {p['n']} ({p['n_months']}) | {r1._fmt(p['model_metric'])} | "
                        f"{r1._fmt(p['rule_metric'])} | {r1._signed(p['mean'])} | [{r1._signed(lo)}, {r1._signed(hi)}] | "
                        f"{p['model_better_n']} / {p['rule_better_n']} / {p['tie_n']} | {r1.VERDICT_TEXT[p['verdict']]} |")
            elif c["output"] == "S" and c["horizon_or_k"] is not None:
                per_k.setdefault(c["horizon_or_k"], []).append(p)
                continue
            elif c["output"] == "S":
                line = rf._row([f"`{c['rule_id']}`"], p)
            elif c["output"] == "P_close_ceiling":
                line = rf._row([str(c["horizon_or_k"]), f"`{c['rule_id']}`"], p)
            elif c["rule_id"] == "v1_5_h99":
                line = rf._row([c["horizon_or_k"], c["metric"]], p)
            else:
                line = rf._row([c["horizon_or_k"], f"`{c['rule_id']}`"], p)
            assert line in text, (model_id, line)
            checked += 1
        for k, (p, q) in per_k.items():
            line = (f"| {k} | {p['n']} | {rf._f(p['model_metric'])} | {rf._f(p['rule_metric'])} | {rf._s(p['mean'])} | "
                    f"{rf._ci(p)} | {rf._f(q['model_metric'])} | {rf._f(q['rule_metric'])} | {rf._s(q['mean'])} | {rf._ci(q)} |")
            assert line in text, (model_id, line)
            checked += 2
    assert checked == sum(len(sc.backtest_cells(m, runs)) for m in sections)


@pytest.mark.requires_git_history
def test_backtest_primary_cells_and_verdicts(scores):
    for m in scores["models"]:
        prim = [c for c in m["backtest"]["cells"] if c["label"] == "birincil"]
        if m["model_id"] in sc.NEW_MODEL_COMPARATORS:
            # Dondurulmuş Faz 7/7C (SPEC_DEVIATIONS L): kartın birincil hücresi canlı/kasa hücresidir (SPEC_HAZARD_V1 §5.3, SPEC_C_V0
            # §5.3); backtest terazisindeki birincil hücre `backtest.near_era` bloğudur, `backtest.cells` boş.
            assert m["primary_cell"] == sc.primary_cell_of(m["model_id"]) and m["backtest"]["cells"] == []
            assert m["backtest"]["near_era"]["schema_version"] == sc.NEAR_ERA_SCHEMA
            continue
        pc = sc.PRIMARY_CELLS.get(m["model_id"])
        if pc is None:
            assert m["primary_cell"] is None and prim == []
            continue
        assert m["primary_cell"] == pc and len(prim) == len(pc["rule_ids"])
        for c in prim:
            assert c["verdict"] == sc.verdict(c["n"], c["ci95"])
    v15 = [c for c in by_model(scores, "v1_5_h99")["backtest"]["cells"] if c["label"] == "birincil"]
    assert [(c["horizon_or_k"], c["rule_id"], round(c["diff"], 4)) for c in v15] == [("D5", "base_train_median", -0.0839)]


# ---------------------------------------------------------------- şema ve commit edilen çıktı

REQUIRED_TOP = {"schema_version", "generated_at_utc", "as_of_session", "code", "inputs", "models", "skipped", "retro_info"}
REQUIRED_MODEL = {"model_id", "kind", "card", "primary_cell", "backtest", "live"}
REQUIRED_LIVE = {"title", "n_live", "n_late", "n_scored", "n_refused", "n_skipped", "n_target_unavailable", "n_pending",
                 "rows", "cells", "self_reported_rows"}
REQUIRED_ROW = {"ticker", "d1", "class", "record_id", "prediction", "rules", "realized", "status"}
REQUIRED_CELL = {"output", "horizon_or_k", "metric", "model_value", "rule_id", "rule_value", "diff", "ci95", "n", "wins",
                 "losses", "ties", "verdict"}


def check_schema(s, drop=()):
    """`drop`: INDEX'te olup dosyada beklenmeyen kimlikler (yalnız Faz 7 ve 7C dondurmaları sonrası commit'li eski scores.json;
    J30, K19)."""
    assert s["schema_version"] == sc.SCHEMA and REQUIRED_TOP <= set(s)
    assert {"git_head", "borsai_source_sha256"} <= set(s["code"])
    assert {"outcomes_sha256", "records_sha256", "models_index_sha256"} <= set(s["inputs"])
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
    assert [m["model_id"] for m in s["models"]] == [e["model_id"] for e in index["models"] if e["model_id"] not in drop]
    for m in s["models"]:
        assert REQUIRED_MODEL <= set(m)
        assert {"training_n", "training_cutoff", "params_sha256_8", "n_variants_same_data"} <= set(m["card"])
        assert REQUIRED_LIVE <= set(m["live"]) and {"title", "cells"} <= set(m["backtest"])
        for r in m["live"]["rows"] + m["live"]["self_reported_rows"]:
            assert REQUIRED_ROW <= set(r)
        for c in m["backtest"]["cells"] + m["live"]["cells"]:
            assert REQUIRED_CELL <= set(c)


@pytest.mark.requires_git_history
def test_built_scores_schema(scores):
    check_schema(scores)
    assert scores["inputs"]["models_index_sha256"] == sha256_file(ROOT / "models" / "INDEX.json")


def _stable(s):
    """Üretim anına bağlı alanlar dışarıda: zaman, kod durumu ve sonuç commit'inin kendisi."""
    s = json.loads(json.dumps(s))
    s.pop("generated_at_utc")
    s.pop("code")
    for m in s["models"]:
        for r in m["live"]["rows"] + m["live"]["self_reported_rows"]:
            for k in ("outcome_ingest_commit", "checked_against", "outcome_ingest_basis"):
                r["class_evidence"].pop(k)
    for x in s["retro_info"]:
        for k in ("outcome_ingest_commit", "checked_against", "outcome_ingest_basis"):
            x["class_evidence"].pop(k)
    return s


PRE_FAZ2C_SCORES_COMMIT = "0c3cb997a41157ba211870473efd2c027e66db2e"   # koşullu bloklardan önce scores.json'ı yazan son commit


@pytest.mark.requires_raw_sources
def test_committed_scores_json_matches_recomputation(scores):
    path = sc.SCORES_PATH
    if not path.exists():
        return
    committed = json.loads(path.read_text(encoding="utf-8"))
    check_schema(committed, drop=fs7.frozen_tail_ids() if fs7.scores_json_is_pre_faz7() else ())
    if not any("conditional" in m for m in committed["models"]):
        # Faz 2C commit A → B arası: koşullu bloklar yalnız B'de yazılır (SPEC_DEVIATIONS G, test düzenlemeleri). İstisna
        # yalnız dosya 0c3cb99'daki haliyle bayt-eşitken geçerlidir; yeniden üretilen her scores.json blokları taşır.
        assert path.read_bytes() == _show(PRE_FAZ2C_SCORES_COMMIT, "scores/scores.json")
        scores = {**scores, "models": [{k: v for k, v in m.items() if k != "conditional"} for m in scores["models"]]}
    if fs.scores_json_is_pre_faz5():
        # Faz 5 (SPEC_DEVIATIONS H): scores.json bu görevde yeniden üretilmez; post_d1_hazard_v0'ın backtest satırı veri
        # geneli varyant sayacını (E16) artırır. İstisna yalnız dosya 72a000f'deki haliyle bayt-eşitken ve fark tam olarak
        # günlükteki POST_D1 varyant sayısı kadarken geçerlidir; yeniden üretilen her scores.json tam karşılaştırılır.
        dv = {e["model_id"]: e["data_version_sha256"] for e in json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]}
        scores = json.loads(json.dumps(scores))
        for m in scores["models"]:
            m["card"]["n_variants_same_data"] -= fs.faz5_variants(dv[m["model_id"]])
    if fs7.scores_json_is_pre_faz7():
        # Faz 7 (SPEC_DEVIATIONS J; H22 kalıbı): scores.json bu görevde yeniden üretilmez; v1_clip/v1_real backtest satırları H99
        # veri sürümünde varyant sayacını (E16) artırır. İstisna yalnız dosya 8e3a623'teki haliyle bayt-eşitken ve fark tam olarak
        # günlükteki Faz 7 varyant sayısı kadarken geçerlidir; yeniden üretilen her scores.json tam karşılaştırılır.
        # Faz 7 dondurması (SPEC_DEVIATIONS J23; aynı kalıp): dört v1 modeli INDEX'e girer, scores/ yeniden üretilmez; yeniden
        # hesaptan YALNIZ onların kartları, retro_info satırları ve INDEX sha'sı çıkarılır (`faz7_support.strip_frozen_faz7`).
        # Faz 7C dondurması (SPEC_DEVIATIONS K19; orkestratör kararı, aynı koşullar): dört (C) kimliği de aynı biçimde çıkarılır.
        scores = fs7.strip_frozen_faz7(scores)
        dv = {e["model_id"]: e["data_version_sha256"] for e in json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]}
        scores = json.loads(json.dumps(scores))
        for m in scores["models"]:      # Faz 7C (SPEC_DEVIATIONS K): aynı istisna, Faz 7C varyantlarıyla (backtest + keşif)
            m["card"]["n_variants_same_data"] -= fs7.faz7_variants(dv[m["model_id"]]) + fs7c.faz7c_variants(dv[m["model_id"]])
    if fs8.scores_json_is_pre_faz8():
        # Faz 8 (SPEC_DEVIATIONS N19; proje sahibi kararı 2026-10-01; J16/K10 kalıbı): scores/ bu görevde yeniden üretilmez; break_floor_v0'ın
        # backtest satırı H99 veri sürümünde varyant sayacını (E16) artırır. İstisna yalnız dosya 87434ff'teki haliyle bayt-eşitken ve
        # fark tam olarak günlükteki Faz 8 varyant sayısı kadarken geçerlidir; yeniden üretilen her scores.json tam karşılaştırılır.
        dv = {e["model_id"]: e["data_version_sha256"] for e in json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]}
        scores = json.loads(json.dumps(scores))
        for m in scores["models"]:
            m["card"]["n_variants_same_data"] -= fs8.faz8_variants(dv[m["model_id"]])
    assert _stable(committed) == _stable(scores)
    post = sc.load_post_d1_scores()
    if post is None:
        # Canlı POST_D1 akışı A → B arası (SPEC_DEVIATIONS H28): scores_post_d1.json ve SCORES.md §7 yalnız B'de yazılır.
        # İstisna yalnız scores.json 72a000f'deki haliyle bayt-eşitken; yeniden üretilen her skor ikisini de taşır.
        assert fs.scores_json_is_pre_faz5()
    doc = sc.DOC_PATH.read_text(encoding="utf-8")
    assert doc == sc.render_doc(committed, post)


def test_scores_doc_has_no_live_verdict_or_average():
    """K4: canlı bölümlerde metrik/ortalama/"geçiyor" yok; "geçiyor" yalnız backtest bölümünde (varsa)."""
    if not sc.DOC_PATH.exists():
        return
    doc = sc.DOC_PATH.read_text(encoding="utf-8")
    live_part, _, backtest_part = doc.partition("## 5. Geçmiş veri testi")
    assert backtest_part, "backtest bölümü yok"
    cond_part = backtest_part.partition("## 6. Koşullu tavan skorları")[2]   # koşullu canlı bölüm (varsa), SPEC_DEVIATIONS G11
    for word in ("geçiyor", "geçemiyor", "ayırt edilemiyor", "ortalama MAE", "Brier =", "RPS ="):
        assert word not in live_part, word
        assert word not in cond_part, word


# ---------------------------------------------------------------- n ≥ 10 yolu (sentetik satırlar)

def _synthetic_rows(n, kind="linear"):
    rows = []
    for i in range(n):
        R = {h: f"{0.05 * (i % 5) - 0.05:.4f}" for h in HORIZONS}
        Y = {h: int(float(R[h]) > 0) for h in HORIZONS}
        L = i % 11
        linear = {h: {"return": 0.1 - 0.01 * (i % 3), "p_up": 0.8} for h in HORIZONS}
        rule_lin = {h: {"return": 0.1, "p_up": 1.0} for h in HORIZONS}
        S = [max(0.0, 0.9 - 0.08 * k) for k in range(10)]
        rows.append({
            "ticker": f"SNT{i:02d}", "d1": f"2027-{1 + i % 7:02d}-15", "class": sc.CLASS_LATE, "status": sc.ROW_SCORED,
            "prediction": {**linear, "S": S, "P_close_ceiling": S},
            "rules": ({r: {"values": rule_lin} for r in (*sc.RETURN_RULES, *sc.PROB_RULES, sc.V15)} if kind == "linear" else
                      {r: {"values": {"S": [0.8] * 10, "P_close_ceiling": [0.8] * 10}} for r in
                       ("ceiling_hazard_v0@INF", "base_km_expanding", "base_km_last10", "base_always_ceiling")}
                      | {sc.P_UP_AS_CEILING: {"values": {"P_close_ceiling_k": {str(k): 0.8 for k in sc.KS}}}}),
            "realized": {"row_status": ["OK"] * 10, "R": R, "Y": Y, "L": L,
                         "ceiling_close": [1 if k < L else (i % 2) for k in range(10)]},
        })
    return rows


def test_live_cells_and_descriptive_when_n_at_least_ten():
    rows = _synthetic_rows(12)
    lin = sc.live_cells("v1_6_h99", "linear", rows)
    assert lin and all(c["n"] == 12 and c["verdict"] == "yetersiz örnek" and c["scale"] == sc.SCALE_LIVE for c in lin)
    assert {(c["metric"], c["rule_id"]) for c in lin} >= {("MAE", "v1_5_h99"), ("MAE", "base_train_median"),
                                                          ("DirMiss", "base_always_ceiling"), ("Brier", "base_rate"),
                                                          ("LogLoss", "base_last10_rate"), ("HitMiss", "base_rate")}
    prim = [c for c in lin if c["label"] == "birincil"]
    assert [(c["horizon_or_k"], c["metric"], c["rule_id"]) for c in prim] == [("D10", "MAE", "v1_5_h99")]
    crows = _synthetic_rows(12, "hazard")
    ceil = sc.live_cells("ceiling_hazard_v0", "hazard", crows)
    assert {c["metric"] for c in ceil} == {"RPS", "Brier"} and all(c["n"] == 12 for c in ceil)
    assert sum(c["label"] == "birincil" for c in ceil) == 2
    assert sc.live_cells("v1_5_h99", "linear", rows[:9]) == []
    assert sc.live_cells("base_zero", "rule", rows) == []
    d = sc.live_descriptive("v1_5_h99", "linear", rows)
    assert [x["metric"] for x in d] == ["MedAE"] * 4 and all("base_train_median" in x["rules"] for x in d)
    dc = sc.live_descriptive("ceiling_hazard_v0", "hazard", crows)
    assert [x["horizon_or_k"] for x in dc] == list(sc.KS) and all(0 <= x["observed"] <= 1 for x in dc)
    with pytest.raises(sc.ScaleMixError):
        sc.paired_metric(sc.live_obs("v1_5_h99", "linear", rows, "return", "D1", "MAE", "base_zero")
                         + [sc.PairedObs(sc.SCALE_BACKTEST, "X", "2027-01", 0.1, 0.2)])


# ------------------------------------------- Faz 4: tavan yolu hücreleri (SPEC_CEILING_PATH_V0 §5, SPEC_APP_EK2 §8 Ö1/Ö3)

FAZ4_FREEZE_COMMIT = "a0df5b773890d4847bc95793b8ae6b5986f19a0e"   # scores.json'ı en son yazan commit (Faz 4 dondurma)

# MODELS.md'deki §5 tabloları. PB bölümü "bilgi amaçlı" tablodan ÖNCE biter: o satırlar hücre değildir.
FAZ4_SECTIONS = {
    "ceiling_path_v0": ("### `ceiling_path_v0`: bütün hücreler", "### `ceiling_path_v0@INF` (sıfır model"),
    "ceiling_path_v0@INF": ("### `ceiling_path_v0@INF` (sıfır model", "### `pb_ceiling_path_v0` (PB varyantı"),
    "pb_ceiling_path_v0": ("### `pb_ceiling_path_v0` (PB varyantı", "Kurallar PB planının kendi koşularıdır"),
}

# §5 canlı karşılaştırılanları: kurallar + model karşılaştırılanları (PB kuralları için SPEC_DEVIATIONS F17).
RULES_LIVE = ["base_always_ceiling", "base_train_median", "base_train_mean", "base_zero", "base_rate", "base_last10_rate"]
FAZ4_LIVE_COMPARATORS = {
    "ceiling_path_v0": ["v1_5_h99", "ceiling_path_v0@INF"] + RULES_LIVE,
    "ceiling_path_v0@INF": RULES_LIVE,
    "pb_ceiling_path_v0": ["pb_v0"] + RULES_LIVE,
}


def _show(commit: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{path}"], check=True, capture_output=True).stdout


@pytest.mark.requires_git_history
def test_faz4_backtest_cells_equal_models_md(scores):
    """(a) Üç modelin scores.json hücreleri, MODELS.md'yi üreten `report_faz4.compare` değerleriyle bit-eşit ve
    satırları MODELS.md'nin Faz 4 tablolarında aynen vardır (aynı ledger'lar, aynı eşleştirme, aynı bootstrap)."""
    from borsai import report_faz4 as r4

    runs, runs4 = rf.load_runs(), r4.load_faz4_runs()
    keys = (("model_value", "model_metric"), ("rule_value", "rule_metric"), ("diff", "mean"), ("n", "n"),
            ("n_blocks", "n_months"), ("wins", "model_better_n"), ("losses", "rule_better_n"), ("ties", "tie_n"))
    checked, max_delta = 0, 0.0
    for model_id, (start, end) in FAZ4_SECTIONS.items():
        text = _section(start, end)
        cells = by_model(scores, model_id)["backtest"]["cells"]
        assert len(cells) == len(HORIZONS) * len(sc.CEILING_PATH_SPECS[model_id])
        assert all(c["scale"] == sc.SCALE_BACKTEST and c["verdict"] == sc.verdict(c["n"], c["ci95"]) for c in cells)
        for c in cells:
            p = r4.compare(model_id, c["rule_id"], c["horizon_or_k"], c["metric"], runs, runs4)
            max_delta = max([max_delta] + [abs(c[a] - p[b]) for a, b in keys]
                            + [abs(x - y) for x, y in zip(c["ci95"], p["ci95"])])
            name = f"`{c['rule_id']}`" + (" **(BİRİNCİL)**" if c["label"] == "birincil" else "")
            assert rf._row([c["horizon_or_k"], c["metric"], name], p) in text, (model_id, c)
            checked += 1
    assert (checked, max_delta) == (72, 0.0)


@pytest.mark.requires_git_history
def test_faz4_information_only_rows_are_not_cells(scores):
    """§5'in son satırı (PB ↔ ana model / sıfır model, kesimleri farklı) "bilgi amaçlı"dır: hücre olmaz."""
    pb = by_model(scores, "pb_ceiling_path_v0")["backtest"]["cells"]
    assert [c for c in pb if c["rule_id"] in ("ceiling_path_v0", "ceiling_path_v0@INF")] == []
    assert {(c["metric"], c["rule_id"]) for c in pb} == {
        ("MAE", "pb_v0"), ("MAE", "base_train_median"), ("MAE", "base_always_ceiling"),
        ("Brier", "pb_v0"), ("Brier", "base_rate"), ("Brier", "base_last10_rate")}


@pytest.mark.requires_git_history
def test_faz4_primary_cell_values(scores):
    """(b) Birincil hücre `ceiling_path_v0` D5 getiri MAE − `base_train_median`: MODELS.md'deki değerler."""
    m = by_model(scores, "ceiling_path_v0")
    assert m["primary_cell"] == sc.PRIMARY_CELLS["ceiling_path_v0"] == {
        "output": "return", "horizon_or_k": "D5", "metric": "MAE", "rule_ids": ["base_train_median"]}
    prim = [c for c in m["backtest"]["cells"] if c["label"] == "birincil"]
    assert len(prim) == 1
    c = prim[0]
    assert (c["output"], c["horizon_or_k"], c["metric"], c["rule_id"]) == ("return", "D5", "MAE", "base_train_median")
    assert (round(c["diff"], 4), [round(x, 4) for x in c["ci95"]], c["n"]) == (-0.1158, [-0.1611, -0.0738], 85)
    assert (round(c["model_value"], 4), round(c["rule_value"], 4)) == (0.1842, 0.3000)
    assert (c["n_blocks"], c["wins"], c["losses"], c["ties"]) == (23, 63, 22, 0)
    assert c["verdict"] == sc.V_PASS == "geçiyor" and c["label"] == "birincil"
    for other in ("ceiling_path_v0@INF", "pb_ceiling_path_v0"):
        b = by_model(scores, other)
        assert b["primary_cell"] is None
        assert b["backtest"]["cells"] and all(x["label"] == "keşif" for x in b["backtest"]["cells"])


def test_faz4_primary_cells_registry_only_main_added():
    """(c) PRIMARY_CELLS'e §5 gereği YALNIZ `ceiling_path_v0` eklendi."""
    from borsai.specs import FAZ4_MODEL_IDS

    assert set(sc.PRIMARY_CELLS) & set(FAZ4_MODEL_IDS) == {"ceiling_path_v0"}
    assert set(sc.PRIMARY_CELLS) == {"v1_5_h99", "pb_v0", "v1_5_market20_v0", "v1_6_h99", "ceiling_hazard_v0",
                                     "pb_ceiling_v0", "ceiling_path_v0"}


@pytest.mark.requires_git_history
def test_faz4_scores_json_existing_blocks_unchanged():
    """(d) a0df5b7'ye göre 16 eski modelin blokları içerik olarak aynı (üretim anı, kod sha'sı ve
    `n_variants_same_data` dışında); üç tavan yolu modelinde yalnız `backtest.cells` ve `primary_cell` doldu."""
    from borsai.specs import FAZ1A_MODEL_IDS, FAZ1B_MODEL_IDS, FAZ4_MODEL_IDS

    def stable(block):
        b = json.loads(json.dumps(block))
        b["card"].pop("n_variants_same_data")
        b.pop("conditional", None)   # Faz 2C'nin yeni bloğu (SPEC_DEVIATIONS G); tests/test_scoring_conditional.py sınar
        return b

    old = json.loads(_show(FAZ4_FREEZE_COMMIT, "scores/scores.json"))
    new = json.loads((ROOT / "scores" / "scores.json").read_text(encoding="utf-8"))
    o = {m["model_id"]: m for m in old["models"]}
    n = {m["model_id"]: m for m in new["models"]}
    # BORSAI_FAZ7_OOT_RECORDS (SPEC_DEVIATIONS L): skorlar 27 modelle yeniden üretilince dondurulmuş Faz 7/7C kartları sona eklenir;
    # ilk 19 kart burada sınanır, yeni kartlar tests/test_faz7_oot.py'de. 8e3a623 durumunda (J30) liste 19'dur.
    tail = [] if fs7.scores_json_is_pre_faz7() else fs7.frozen_tail_ids()
    assert list(o) == list(n)[:len(o)] == list(FAZ1A_MODEL_IDS + FAZ1B_MODEL_IDS + FAZ4_MODEL_IDS)
    assert list(n)[len(o):] == tail
    # 16 eski modelin blokları a0df5b7'dekiyle aynı; yalnız f1f9d44'te var olan arzların sonucu PENDING -> dolu ilerleyebilir
    # (SPEC_DEVIATIONS M24; kural tests/test_faz4_ceiling_path.py::faz1_progress_problems: dondurulmuş alanlar, dolu ufuklar,
    # kart, backtest ve model listesi aynen; `outcomes` aynı arzlar aynı sırada, as_of_session geriye gitmez).
    import test_faz4_ceiling_path as tf4

    ids16 = list(FAZ1A_MODEL_IDS + FAZ1B_MODEL_IDS)
    assert len(ids16) == 16
    only16 = lambda d: {**d, "models": [m for m in d["models"] if m["model_id"] in ids16]}  # noqa: E731
    assert [m["model_id"] for m in only16(new)["models"]] == [m["model_id"] for m in only16(old)["models"]] == ids16
    assert tf4.faz1_progress_problems(only16(old), only16(new)) == []
    # 19: a0df5b7; scores.json yeniden üretilince günlükteki POST_D1 varyantıyla 20 (SPEC_DEVIATIONS H22, H44); Faz 7 varyantları
    # (SPEC_DEVIATIONS J) scores.json yeniden üretilince eklenir.
    dv0 = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"][0]["data_version_sha256"]
    now_n = 19 if fs.scores_json_is_pre_faz5() else 20 + (0 if fs7.scores_json_is_pre_faz7() else
                                                          fs7.faz7_variants(dv0) + fs7c.faz7c_variants(dv0))
    for mid in FAZ1A_MODEL_IDS + FAZ1B_MODEL_IDS:
        assert o[mid]["card"]["n_variants_same_data"] == 19 and n[mid]["card"]["n_variants_same_data"] == now_n
    for mid in FAZ4_MODEL_IDS:
        assert o[mid]["backtest"]["cells"] == [] and o[mid]["primary_cell"] is None
        card = lambda m: {k: v for k, v in m["card"].items() if k != "n_variants_same_data"}  # noqa: E731
        assert n[mid]["live"] == o[mid]["live"] and card(n[mid]) == card(o[mid]) and n[mid]["kind"] == "ceiling_path"
        assert o[mid]["card"]["n_variants_same_data"] == 19 and n[mid]["card"]["n_variants_same_data"] == now_n
        assert len(n[mid]["backtest"]["cells"]) == len(HORIZONS) * len(sc.CEILING_PATH_SPECS[mid])
    # `outcomes` ve `as_of_session` M24 kuralıyla yukarıda sınandı (ilerleyebilir); öbürleri aynen
    for key in ("separate_models", "skipped", "definitions", "schema_version"):
        assert new[key] == old[key], key
    # retro_info: eski 21 çift aynen; yeniden üretimden sonra yeni çiftler yalnız dondurulmuş Faz 7/7C kimliklerinindir (7 canlı arz ×
    # 8 model; formülle RETRO). inputs: yalnız models_index_sha256 bugünkü INDEX'i adlandırır.
    assert [x for x in new["retro_info"] if x["model_id"] not in tail] == old["retro_info"] and len(old["retro_info"]) == 21
    assert len(new["retro_info"]) == 21 + 7 * len(tail)
    # outcomes_sha256 sonuç ilerleyince değişir (M24); records_sha256 aynen
    assert {k: v for k, v in new["inputs"].items() if k not in ("outcomes_sha256",) and (k != "models_index_sha256" or not tail)} == \
        {k: v for k, v in old["inputs"].items() if k not in ("outcomes_sha256",) and (k != "models_index_sha256" or not tail)}
    if tail:
        assert new["inputs"]["models_index_sha256"] == sha256_file(ROOT / "models" / "INDEX.json")
    assert _git(ROOT, "status", "--porcelain", "--", "registry", "data") == ""


@pytest.mark.requires_git_history
def test_faz4_live_comparators_follow_spec(scores):
    """(e) §5 canlı karşılaştırılanları: ana model kurallar + `v1_5_h99` + sıfır model; sıfır model yalnız
    kurallar; PB varyantı kurallar + `pb_v0`. Canlı n bugün 0 -> hiçbir canlı hücre ya da metrik yok (§8)."""
    both = lambda c: c not in sc.RETURN_RULES and c not in sc.PROB_RULES   # noqa: E731
    for model_id, expected in FAZ4_LIVE_COMPARATORS.items():
        assert sc.comparators(model_id, "ceiling_path") == expected
        specs = sc.live_cell_specs(model_id, "ceiling_path")
        for h in HORIZONS:
            for output, metric, rules in (("return", "MAE", sc.RETURN_RULES), ("p_up", "Brier", sc.PROB_RULES)):
                got = [r for o, hk, mt, r in specs if (o, hk, mt) == (output, h, metric)]
                assert got == [c for c in expected if c in rules or both(c)], (model_id, h, output)
        block = by_model(scores, model_id)["live"]
        assert (block["n_rows"], block["n_scored"], block["cells"], block["descriptive"]) == (0, 0, [], [])
    # eski modellerin canlı karşılaştırıcıları değişmedi
    assert sc.comparators("pb_v0", "pb") == ["v1_5_h99"] + RULES_LIVE
    assert sc.comparators("v1_5_h99", "linear") == RULES_LIVE
    assert sc.comparators("ceiling_hazard_v0", "hazard") == ["ceiling_hazard_v0@INF", "base_km_expanding",
                                                             "base_km_last10", "base_always_ceiling",
                                                             "v1_5_p_up_as_ceiling"]

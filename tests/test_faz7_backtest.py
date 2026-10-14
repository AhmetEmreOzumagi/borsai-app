"""Faz 7 backtest altyapısı (SPEC_HAZARD_V1 §5.1, §11-7, §11-8, §11-9, §11-14; görev kararları T5, T6). Commit A: fold PLANLARI
gerçek veride (skor değil), koşular ve rapor sentetik veriyle; gerçek koşu sonuçları tests/test_faz7_golden.py'de (commit B)."""
from __future__ import annotations

import csv
import io
import json
import re

import pytest

from borsai import backtest as bt
from borsai import preprocess as pp
from borsai import report as r1
from borsai import report_faz4 as r4
from borsai import report_faz7 as r7
from borsai import survival as sv
from borsai.data import load_dataset, load_dataset_v2
from borsai.provenance import ROOT, sha256_bytes, sha256_file
from borsai.specs import DEFLATOR, FAZ7_MODEL_IDS, FAZ7_MODEL_SPECS, PLAN_CEILING, SPEC_DOCUMENTS_FAZ7, spec_sha256

import faz7_support as f7

CLIP, REAL, POOLED, POOLED_INF = FAZ7_MODEL_IDS


@pytest.fixture(scope="module")
def v0_rows():
    return bt.read_pinned_ledger(bt.FAZ7_COMPARATOR_LEDGERS["ceiling_hazard_v0"])


@pytest.fixture(scope="module")
def plans():
    h99 = load_dataset()
    v2 = load_dataset_v2()
    raw_real = bt.v1_raw_features(FAZ7_MODEL_SPECS[REAL], list(h99.rows))[0]
    raw_pool = bt.v1_raw_features(FAZ7_MODEL_SPECS[POOLED], list(v2.rows))[0]
    return {CLIP: bt.v1_plan(CLIP, h99, raw_real), REAL: bt.v1_plan(REAL, h99, raw_real),
            POOLED: bt.v1_plan(POOLED, v2, raw_pool), "v2": v2, "raw_pool": raw_pool}


def _scorable(folds):
    return [f for f in folds if f.status == bt.SCORABLE]


def test_fold_plans_same_tickers_near_era_78_and_no_leakage(plans, v0_rows):
    """§11-7: clip/real ledger ticker kümesi = v0'ın 87'si; pooled 87'nin hepsini içerir (97'ye çıkar); yakın dönem alt kümesi üçünde
    aynı 78 ticker (22 ay); her fold'da max(eğitim seans tarihi) < T (açık üyeler dahil)."""
    v0 = [r["ticker"] for r in v0_rows]
    assert len(v0) == 87
    for m in (CLIP, REAL):
        assert [f.test_ticker for f in _scorable(plans[m])] == v0
    pooled = _scorable(plans[POOLED])
    assert set(v0) <= {f.test_ticker for f in pooled} and len(pooled) == 97 == len(plans[POOLED])
    near = [{f.test_ticker for f in _scorable(plans[m]) if f.first_trading_date >= bt.NEAR_ERA_START} for m in (CLIP, REAL, POOLED)]
    assert near[0] == near[1] == near[2] and len(near[0]) == 78
    assert len({f.first_trading_date[:7] for f in pooled if f.test_ticker in near[0]}) == 22
    units = {r.ticker: sv.unit_of(r) for r in plans["v2"].rows}
    for f in pooled:
        rows = sv.pp_table([units[t] for t in f.training], f.cutoff_date)
        assert len(rows) == f.n_pp_rows and all(units[r.ticker].session_dates[r.day - 1] < f.cutoff_date for r in rows)
        assert f.max_session_date < f.first_trading_date == f.cutoff_date and f.test_ticker not in f.training


def test_pooled_plan_filter_exclusion_matches_independent_mode(plans):
    """Proje sahibi kararı (SPEC_DEVIATIONS J): fold'un f3'lü aday birimlerinin filtre modu UNFILTERED olan fold'larda açık kümenin
    FILTERED f3'lü 3 üyesi o fold'da kullanılmaz; bağımsız sayım 44 fold."""
    v2 = plans["v2"]
    cand_rows = [r for r in v2.rows if r.inputs["total_demand_multiple"] is not None]
    n_mode_unf = 0
    for f in _scorable(plans[POOLED]):
        statuses = [r.total_demand_filter_status for r in cand_rows if r.first_trading_date < f.cutoff_date]
        mode, _ = pp.filter_mode(statuses)
        expect = {r.ticker for r in cand_rows if r.first_trading_date < f.cutoff_date and pp.opposite_explicit_status(r.total_demand_filter_status, mode)}
        assert set(f.filter_excluded) == expect
        n_mode_unf += mode == "UNFILTERED"
        assert f.n_oot_open == sum(1 for t in f.training if not t in {r.ticker for r in cand_rows if r.cohort == "H99"})
    assert n_mode_unf == 44 == sum(1 for f in plans[POOLED] if f.filter_excluded)
    assert {len(f.filter_excluded) for f in plans[POOLED] if f.filter_excluded} == {3}
    assert all(v2.by_ticker()[t].cohort == "OOT_OPEN" and v2.by_ticker()[t].total_demand_filter_status == "FILTERED"
               for f in plans[POOLED] for t in f.filter_excluded)


def test_v0_comparator_ledger_pinned_and_mean_rps_reproduced(v0_rows):
    """§11-8: ledger sha `976b4dcea981…` pinli; v0'ın 87-fold ortalama RPS'i ledger'daki S_1..S_10'dan 0.1503 (|Δ| ≤ 1e-9)."""
    assert bt.FAZ7_COMPARATOR_LEDGERS["ceiling_hazard_v0"]["sha256"].startswith("976b4dcea981")
    assert FAZ7_MODEL_SPECS[CLIP]["plan_id"] == PLAN_CEILING
    m = bt.v0_mean_rps(v0_rows)
    assert abs(m - bt.compute_ceiling_metrics([{**r, "realized_L": int(r["realized_L"]), **{f"S_{k}": float(r[f"S_{k}"]) for k in range(1, 11)},
                                                  **{f"P_close_{k}": float(r[f"P_close_{k}"]) for k in range(1, 11)},
                                                  **{f"realized_close_D{k}": int(r[f"realized_close_D{k}"]) for k in range(1, 11)}}
                                                 for r in v0_rows])["rps"]) <= 1e-9
    assert round(m, 4) == bt.V0_PUBLISHED_MEAN_RPS == 0.1503 and abs(m - 0.1503154628757853) <= 1e-9
    text = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
    section = text.split("### `ceiling_hazard_v0` (SPEC_CEILING_V0)")[1].split("### `pb_ceiling_v0`")[0]
    assert "0.1503" in section
    with pytest.raises(bt.BacktestStop):
        bt.read_pinned_ledger({**bt.FAZ7_COMPARATOR_LEDGERS["ceiling_hazard_v0"], "sha256": "0" * 64})


def test_near_era_label_rule_synthetic():
    """§11-9 ve T5."""
    assert bt.near_era_label([0.001, 0.02]) == "bozuyor"
    assert bt.near_era_label([-0.02, 0.009]) == "tolerans içinde"
    assert bt.near_era_label([-0.005, 0.02]) == "belirsiz"
    assert bt.near_era_label([0.000, 0.02]) == "belirsiz"                        # alt = 0 dışlamaz
    assert bt.near_era_label([-0.02, 0.010]) == "tolerans içinde" and bt.near_era_label(None) == "belirsiz"
    assert bt.near_era_label([0.001, 0.009]) == "bozuyor"                         # önce "bozuyor"


def test_near_era_tolerance_constant_and_rule_text():
    """Fable denetimi B3 (mutasyon j: eşik +0.015 iken bütün testler yeşil kalıyordu): §5.1 δ = 0.010 sabiti; üst ucu (0.010,
    0.015] içindeki sentinel aralık "belirsiz"; MODELS.md'deki kural metni eşiği sabitten üretir."""
    assert bt.NEAR_ERA_TOLERANCE == 0.010
    assert bt.near_era_label([-0.02, 0.012]) == "belirsiz"
    assert bt.near_era_label([-0.02, 0.0100000001]) == "belirsiz"
    rule = next(r for r in r7.OPERATIONAL_RULES_FAZ7 if r.startswith("Etiket (§5.1)"))
    assert f"üst ucu ≤ {bt.NEAR_ERA_TOLERANCE:+.3f} → **tolerans" in rule and "üst ucu ≤ +0.010 → **tolerans" in rule


def test_near_era_cell_of_v0_against_itself(v0_rows):
    c = bt.near_era_cell(v0_rows, v0_rows)
    assert (c["n"], c["n_months"], c["mean"], c["ci95"], c["label"]) == (78, 22, 0.0, [0.0, 0.0], "tolerans içinde")
    assert c["tie_n"] == c["tie_n_1e12"] == 78
    early = bt.paired_ceiling(v0_rows, v0_rows, end=bt.NEAR_ERA_START)
    assert early["n"] == 9 and early["ci95"] is None                               # 2023 fold'ları (v0'da 9): aralık yok


@pytest.fixture(scope="module")
def synthetic_runs(tmp_path_factory):
    log = tmp_path_factory.mktemp("faz7_log") / "log.jsonl"
    h99 = f7.synthetic_dataset(n_oot=0, n_h99=34, seed=41, tag="syn_h99")
    v2 = f7.synthetic_dataset(seed=42, tag="syn_v2")
    res = {m: bt.run_backtest_v1(m, log_path=log, context="pytest_synthetic", workers=2, dataset=v2 if "pooled" in m else h99)
           for m in FAZ7_MODEL_IDS}
    return res, log, {"h99": h99, "v2": v2}


def test_log_entries_and_ledgers_synthetic(synthetic_runs):
    """§11-14 (sentetik; resmi satırlar tests/test_faz7_golden.py): her koşu günlüğe bir satır; spec_sha256 şartname sözlüğünün,
    spec_document_sha256 şartname dosyasının sha256'sı; veri sürümü pooled için v2 (burada sentetik etiket)."""
    res, log, ds = synthetic_runs
    entries = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert [e["model_id"] for e in entries] == list(FAZ7_MODEL_IDS)
    for e in entries:
        m = e["model_id"]
        spec = FAZ7_MODEL_SPECS[m]
        assert e["kind"] == "backtest" and e["spec_sha256"] == spec_sha256(spec) and e["plan_id"] == spec["plan_id"]
        assert e["spec_document_sha256"] == SPEC_DOCUMENTS_FAZ7["SPEC_HAZARD_V1"]["sha256"] == sha256_file(ROOT / e["spec_document"])
        assert e["decisions_document_sha256"] == SPEC_DOCUMENTS_FAZ7["KARARLAR_FAZ7"]["sha256"]
        assert e["data_version_sha256"] == ("syn_v2" if "pooled" in m else "syn_h99")
        assert e["ledger_sha256"] == sha256_bytes(res[m].ledger_csv) and e["folds_scorable"]["CEILING"] == len(res[m].ledger)
        assert {"git_commit", "borsai_dirty", "borsai_source_sha256", "runtime", "near_era", "evaluated"} <= set(e)
        assert ("tufe" in e) == ("deflator" in spec) and e.get("tufe", {}).get("prefix_sha256", DEFLATOR["file_sha256"]) == DEFLATOR["file_sha256"]
    pooled = entries[2]
    assert set(pooled["comparator_ledgers"]) == {"base_km_expanding__pooled", "base_km_last10__pooled"}
    assert pooled["filter_excluded_folds"] == sum(1 for f in res[POOLED].folds if f.status == bt.SCORABLE and f.filter_excluded) > 0
    assert entries[3]["filter_excluded_folds"] == pooled["filter_excluded_folds"]    # @INF aynı plan (aynı eğitim kümeleri)
    assert [r["ticker"] for r in res[POOLED].ledger] == [r["ticker"] for r in res[POOLED_INF].ledger]
    head = list(res[CLIP].ledger[0])
    v0_head = next(csv.reader(io.StringIO(bt.FAZ7_COMPARATOR_LEDGERS["ceiling_hazard_v0"]["path"] and
                                          (ROOT / bt.FAZ7_COMPARATOR_LEDGERS["ceiling_hazard_v0"]["path"]).read_text(encoding="utf-8"))))
    assert head[:24] == v0_head[:24]                                               # kimlik sütunları v0 ledger'ıyla aynı
    assert "delta_r_pre_equal" in res[POOLED].ledger[0] and "delta_r_pre_equal" not in res[REAL].ledger[0]
    assert all(r["test_r_pre_equal"] == 0.0 for r in res[POOLED].ledger)


def test_golden_writer_and_models_md_section_synthetic(synthetic_runs, tmp_path):
    """Bölüm yalnız altın dizinden üretilir; sentetik koşularla: başlıklar, kurallar, "kasa: bekliyor", yasak kalıplar yok."""
    res, log, ds = synthetic_runs
    previews = {m: bt.final_fit_v1(m, ds["v2" if "pooled" in m else "h99"], spec=f7.synthetic_spec(m, ds["v2" if "pooled" in m else "h99"]))[0]
                for m in FAZ7_MODEL_IDS}
    manifest = bt.write_golden_faz7(res, previews, tmp_path / "g")
    sums = (tmp_path / "g" / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert len(sums) == 4 + 2 + 4 and set(manifest["runs"]) == set(FAZ7_MODEL_IDS) | {"base_km_expanding__pooled", "base_km_last10__pooled"}
    with pytest.raises(bt.BacktestStop):
        bt.write_golden_faz7(res, previews, tmp_path / "g")                         # üzerine yazmaz
    runs = r7.load_faz7(tmp_path / "g")[0]
    cmp = {"ceiling_hazard_v0": runs[CLIP], "ceiling_hazard_v0@INF": runs[REAL], "base_km_expanding": runs[CLIP],
           "base_km_last10": runs[REAL]}
    lines: list[str] = []
    r7.render_faz7(lines.append, log, faz7_dir=tmp_path / "g", cmp=cmp)
    text = "\n".join(lines)
    for h in ("## Faz 7: tavan serisi v1", "### Kartlar", "### Yakın dönem birincil hücreleri", "### İkincil hücreler",
              "### Merdiven", "### Keşif", "### Fold özeti", "### Nihai fit önizlemesi (dondurulmadı)", "### Faz 7 koşuları ve deney günlüğü"):
        assert h in text
    for rule in r7.OPERATIONAL_RULES_FAZ7:
        assert rule in text
    assert text.count("kasa: bekliyor") == 4 and "**Dondurulmadı.**" not in text and r4.D10_FOOTNOTE not in text
    assert "### `ceiling_hazard_v0`" not in text and "### `pb_ceiling_v0`" not in text and not re.search(r"th[bm]20\d{6}", text)
    for row in r7.expectation_rows():
        assert row["raw"]["beklenen"] in text and row["raw"]["aralik"] in text


def test_expectation_62_parsed_verbatim_and_position_rule():
    rows = r7.expectation_rows()
    assert [(r["model"], r["comparator"], r["point"], r["lo"], r["hi"]) for r in rows] == [
        (CLIP, "ceiling_hazard_v0", -0.003, -0.010, 0.005), (REAL, "ceiling_hazard_v0", -0.004, -0.015, 0.008),
        (POOLED, "ceiling_hazard_v0", 0.002, -0.010, 0.015), (POOLED, "base_km_expanding", -0.05, -0.08, -0.02)]
    spec = r7.SPEC_PATH.read_text(encoding="utf-8")
    for r in rows:
        assert f"| {r['raw']['aday']} | {r['raw']['beklenen']} | {r['raw']['aralik']} |" in spec
    assert r7.position(-0.011, -0.010, 0.005) == "altında" and r7.position(-0.010, -0.010, 0.005) == "aralık içinde"
    assert r7.position(0.0051, -0.010, 0.005) == "üstünde" and "beklentiden çok iyi" in r7.position_text("altında")


def test_models_md_faz7_section_only_with_golden_and_before_faz5():
    text = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
    assert ("## Faz 7: tavan serisi v1" in text) == r7.golden_available()
    if r7.golden_available():
        assert text.index("## Faz 4: tavan yolu modelleri") < text.index("## Faz 7: tavan serisi v1") < text.index("## Faz 5: D1 sonrası")
    assert text == r1.render()

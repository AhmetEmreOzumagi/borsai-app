"""Faz 7C backtest altyapısı ve kurallar (SPEC_C_V0 §5, §6.2, §8, §11-6, 7, 8, 11, 13; görev kararları T4, T5, T6). Commit A: fold
PLANLARI gerçek veride (skor değil), koşular, rapor ve skor satırı sentetik veriyle; gerçek koşu sonuçları tests/test_faz7c_golden.py'de
(commit B)."""
from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter

import pytest

from borsai import backtest as bt
from borsai import preprocess as pp
from borsai import report as r1
from borsai import report_faz7c as r7c
from borsai import scoring as sc
from borsai.data import additional_sale_shares, load_dataset, load_dataset_v2
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes, sha256_file
from borsai.specs import (FAZ7C_EXPLORATION, FAZ7C_MODEL_IDS, FAZ7C_MODEL_SPECS, H99_DATA_VERSION_SHA256, SPEC_DOCUMENTS_FAZ7C,
                          V2_DATA_VERSION_SHA256, spec_sha256)

import faz7_support as fs7
import faz7c_support as f7c

H99, POOLED, ADDSALE, ZERO_ROW = FAZ7C_MODEL_IDS


# ---------------------------------------------------------------- §11-6 fold planları (gerçek veri; fit yok)

@pytest.fixture(scope="module")
def plans():
    out = {}
    h, v = load_dataset(), load_dataset_v2()
    for m in FAZ7C_MODEL_IDS:
        ds = h if m == H99 else v
        a = additional_sale_shares(ds)
        spec = FAZ7C_MODEL_SPECS[m]
        rows = bt.fall_training_rows(spec, ds, a, check=True)
        plan_spec = FAZ7C_MODEL_SPECS[spec.get("parent_model_id", m)]
        raw = bt.fall_raw_features(plan_spec, rows, a)[0]
        out[m] = {"folds": bt.plan_fall_folds(ds, rows, raw, uses_f3="f3" in plan_spec["features"]), "ds": ds, "rows": rows}
    return out


def _tests(folds, h):
    return [f.test_ticker for f in folds if f.horizon == h]


def test_fold_plans_test_sets_near_era_and_no_leakage(plans):
    """§11-6: PLAN_FALL_H99 ve PLAN_FALL_POOLED 94 test arzı (ufuk başına, aynı ticker'lar); yakın dönem D10 alt kümesi ikisinde aynı
    75 ticker, 22 ay bloğu; PLAN_FALL_ADDSALE 95 test arzı; her fold'da eğitim D_h seansı < T (D10 fold'larında D10 seansı < T; açık
    üyeler dahil), kendisi ve aynı gün yok; `@ZERO` modelinin planını kullanır."""
    for h in ("D5", "D10"):
        th, tp, ta = _tests(plans[H99]["folds"], h), _tests(plans[POOLED]["folds"], h), _tests(plans[ADDSALE]["folds"], h)
        assert th == tp and len(th) == 94 and len(ta) == 95 and set(th) < set(ta)
    near = {m: [f.test_ticker for f in plans[m]["folds"] if f.horizon == "D10" and f.status == bt.SCORABLE
                and f.prediction_date >= bt.NEAR_ERA_START] for m in (H99, POOLED)}
    assert near[H99] == near[POOLED] and len(near[H99]) == 75
    by = plans[H99]["ds"].by_ticker()
    assert len({by[t].first_trading_date[:7] for t in near[H99]}) == 22
    for m in FAZ7C_MODEL_IDS:
        byt = plans[m]["ds"].by_ticker()
        for f in plans[m]["folds"]:
            assert f.test_ticker not in f.training
            assert all(byt[t].targets[f.horizon].session_date < f.prediction_date == byt[f.test_ticker].first_trading_date
                       for t in f.training)
            assert all(byt[t].first_trading_date < f.prediction_date for t in f.training)
            if f.horizon == "D10":
                assert all(byt[t].targets["D10"].session_date < f.prediction_date for t in f.training)
        # Proje sahibi kararı (SPEC_DEVIATIONS K6, seçenek A): D5 fold'larında kesim D5 seansıdır (PLAN_V15); D10 seansı T'den sonra
        # olan eğitim satırları (sızıntı değil: D5 fold'u yalnız D5 etiketini kullanır).
        late = sum(1 for f in plans[m]["folds"] if f.horizon == "D5" for t in f.training
                   if not byt[t].targets["D10"].session_date < f.prediction_date)
        assert late == {H99: 94, POOLED: 98, ADDSALE: 103, ZERO_ROW: 98}[m]
    zero = [(f.fold_id, f.training, f.filter_excluded, f.status) for f in plans[ZERO_ROW]["folds"]]
    assert zero == [(f.fold_id, f.training, f.filter_excluded, f.status) for f in plans[POOLED]["folds"]]
    # Açık üyelerin son D10 seansı 2023-10-04: T > 2023-10-04 olan her havuz fold'unda açık küme (f3 filtre dışlaması hariç) tam
    # girer; daha erken fold'larda (D10'da 2, D5'te 1) D_h seansı < T kuralı bazılarını dışarıda bırakır (SPEC_DEVIATIONS K).
    for m in (POOLED, ADDSALE):
        opn = [r for r in plans[m]["rows"] if r.cohort == "OOT_OPEN"]
        assert max(r.session_dates[-1] for r in opn) == "2023-10-04"
        partial = Counter(f.horizon for f in plans[m]["folds"] if f.n_oot_open + len(f.filter_excluded) < len(opn))
        assert partial == Counter({"D10": 2, "D5": 1})
        assert all(f.n_oot_open + len(f.filter_excluded) == len(opn) for f in plans[m]["folds"] if f.prediction_date > "2023-10-04")
        assert all(f.status == bt.SCORABLE for f in plans[m]["folds"])


def test_pooled_plan_filter_exclusion_matches_independent_mode(plans):
    """SPEC_DEVIATIONS K (J10 kuralı aynen): havuz fold'unun f3'lü eğitim arzlarının filtre modu açık ve arzın durumu ona zıtsa arz o
    fold'da kullanılmaz; bağımsız mod hesabıyla aynı; dışlananlar açık kümenin FILTERED üyeleri; addsale'de dışlama yok."""
    ds = plans[POOLED]["ds"]
    by = ds.by_ticker()
    n_ex = Counter()
    for f in plans[POOLED]["folds"]:
        cand = [t for t in (*f.training, *f.filter_excluded)]
        mode, _ = pp.filter_mode([by[t].total_demand_filter_status for t in cand])
        expect = {t for t in cand if pp.opposite_explicit_status(by[t].total_demand_filter_status, mode)}
        assert set(f.filter_excluded) == expect
        assert all(by[t].cohort == "OOT_OPEN" and by[t].total_demand_filter_status == "FILTERED" for t in f.filter_excluded)
        n_ex[f.horizon] += bool(f.filter_excluded)
    assert n_ex["D10"] > 0 and n_ex["D5"] > 0
    assert all(not f.filter_excluded for f in plans[ADDSALE]["folds"]) and all(not f.filter_excluded for f in plans[H99]["folds"])


# ---------------------------------------------------------------- §11-7 karşılaştırıcılar

def test_comparator_ledgers_pinned_and_v15_d10_brier_reproduced():
    """§11-7: `base_rate` ve `v1_5_h99` ledger sha'ları pinli (Faz 1A MANIFEST'iyle aynı); V1.5'in D10 Brier'i 0.1883 (81 fold)
    ledger'dan günlükteki değere |Δ| ≤ 1e-9."""
    manifest = json.loads((ROOT / "tests" / "reference" / "macos_golden" / "MANIFEST.json").read_text(encoding="utf-8"))
    for k, v in bt.FAZ7C_COMPARATOR_LEDGERS.items():
        assert v["sha256"] == manifest["models"][k]["ledger_sha256"] == sha256_file(ROOT / v["path"])
    rows = bt.read_pinned_ledger(bt.FAZ7C_COMPARATOR_LEDGERS["v1_5_h99"])
    n, brier = bt.v15_d10_brier(rows)
    logged = [json.loads(x) for x in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    ref = next(e for e in logged if e.get("model_id") == "v1_5_h99" and e["kind"] == "backtest" and
               e["ledger_sha256"] == bt.FAZ7C_COMPARATOR_LEDGERS["v1_5_h99"]["sha256"])["metrics"]["D10"]["p_up"]
    assert n == ref["n"] == 81 and abs(brier - ref["brier"]) <= 1e-9 and round(brier, 4) == bt.V15_PUBLISHED_D10_BRIER == 0.1883
    unclipped = [(float(r["logit_probability"]) - int(r["realized_direction"])) ** 2 for r in rows
                 if r["horizon"] == "D10" and r["logit_status"] == "FIT_OK"]
    assert abs(sum(unclipped) / len(unclipped) - brier) <= 1e-15
    with pytest.raises(bt.BacktestStop):
        bt.read_pinned_ledger({**bt.FAZ7C_COMPARATOR_LEDGERS["base_rate"], "sha256": "0" * 64})


def test_paired_p_up_of_rule_ledger_against_itself():
    rows = bt.read_pinned_ledger(bt.FAZ7C_COMPARATOR_LEDGERS["base_rate"])
    c = bt.paired_p_up(rows, rows, horizon="D10", start=bt.NEAR_ERA_START)
    assert (c["mean"], c["ci95"], c["tie_n"], c["n_months"]) == (0.0, [0.0, 0.0], c["n"], 22) and c["n"] >= 75
    assert bt.near_era_label_fall(c["ci95"]) == "tolerans içinde"


# ---------------------------------------------------------------- §11-8 karar etiketi (T5)

def test_near_era_label_fall_rule_synthetic():
    """§11-8 ve T5: sentetik aralıklar."""
    assert bt.near_era_label_fall([0.001, 0.02]) == "bozuyor"
    assert bt.near_era_label_fall([-0.02, 0.007]) == "tolerans içinde"
    assert bt.near_era_label_fall([-0.005, 0.02]) == "belirsiz"
    assert bt.near_era_label_fall([0.000, 0.02]) == "belirsiz"                 # alt = 0 dışlamaz
    assert bt.near_era_label_fall([-0.02, 0.008]) == "tolerans içinde" and bt.near_era_label_fall(None) == "belirsiz"
    assert bt.near_era_label_fall([0.001, 0.005]) == "bozuyor"                 # önce "bozuyor"


def test_near_era_tolerance_constant():
    """T5 eşik mutasyonu (1/3): δ = 0.008 sabiti (`NEAR_ERA_TOLERANCE_FALL`); v1'in δ'sı (0.010) ayrı ve değişmedi."""
    assert bt.NEAR_ERA_TOLERANCE_FALL == 0.008 and bt.NEAR_ERA_TOLERANCE == 0.010


def test_near_era_sentinel_intervals():
    """T5 eşik mutasyonu (2/3): üst ucu (0.008, 0.015] içindeki sentinel aralıklar "belirsiz" (δ 0.015'e çevrilirse "tolerans
    içinde" olur ve bu test kırmızı)."""
    assert bt.near_era_label_fall([-0.02, 0.012]) == "belirsiz"
    assert bt.near_era_label_fall([-0.02, 0.0080000001]) == "belirsiz"


def test_near_era_rule_text_from_constant():
    """T5 eşik mutasyonu (3/3): MODELS.md kural metni eşiği sabitten üretir ve +0.008 yazar."""
    rule = next(r for r in r7c.OPERATIONAL_RULES_FAZ7C if r.startswith("Etiket (§5.1)"))
    assert f"üst ucu ≤ {bt.NEAR_ERA_TOLERANCE_FALL:+.3f} → **tolerans içinde**" in rule and "üst ucu ≤ +0.008 → **tolerans" in rule


# ---------------------------------------------------------------- sentetik koşular, günlük ve rapor (§11-11 sentetik)

@pytest.fixture(scope="module")
def synthetic_runs(tmp_path_factory):
    log = tmp_path_factory.mktemp("faz7c_log") / "log.jsonl"
    v2, a2 = f7c.synthetic_fall_dataset(tag="syn_v2")
    h99, ah = f7c.h99_subset(v2, a2, tag="syn_h99")
    res, prev = {}, {}
    for m in FAZ7C_MODEL_IDS:
        ds, a = (h99, ah) if m == H99 else (v2, a2)
        spec = f7c.synthetic_spec(m, ds, a)
        res[m] = bt.run_backtest_fall(m, log_path=log, context="pytest_synthetic", workers=2, dataset=ds, add_sale=a, spec=spec,
                                      h99_ledger=res[H99].ledger if m == POOLED else None)
        prev[m] = bt.final_fit_fall(m, ds, spec=spec, add_sale=a)[0]
    return res, prev, log


def test_log_entries_and_ledgers_synthetic(synthetic_runs):
    """§11-11 (sentetik; resmi satırlar commit B): her koşu günlüğe bir `kind: backtest` satırı; spec_sha256 şartname sözlüğünün,
    spec_document_sha256 SPEC_C_V0.md'nin, decisions_document_sha256 KARARLAR_C.md'nin sha256'sı; havuz satırı birincil hücreyi taşır."""
    res, _, log = synthetic_runs
    entries = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert [e["model_id"] for e in entries] == list(FAZ7C_MODEL_IDS)
    for e in entries:
        m = e["model_id"]
        assert e["kind"] == "backtest" and e["plan_id"] == FAZ7C_MODEL_SPECS[m]["plan_id"]
        assert e["spec_document_sha256"] == SPEC_DOCUMENTS_FAZ7C["SPEC_C_V0"]["sha256"] == sha256_file(ROOT / e["spec_document"])
        assert e["decisions_document_sha256"] == SPEC_DOCUMENTS_FAZ7C["KARARLAR_C"]["sha256"] == sha256_file(ROOT / e["decisions_document"])
        assert e["data_version_sha256"] == ("syn_h99" if m == H99 else "syn_v2") and e["ledger_sha256"] == sha256_bytes(res[m].ledger_csv)
        assert set(e["folds_scorable"]) == {"D5", "D10"} and sum(e["folds_scorable"].values()) == len(res[m].ledger)
        assert {"git_commit", "borsai_dirty", "borsai_source_sha256", "runtime", "near_era_secondary", "evaluated", "metrics"} <= set(e)
        assert ("tufe" in e) == (m in (H99, POOLED))
        assert (e["near_era"] is None) == (m != POOLED)
    assert entries[1]["near_era"]["label"] in ("bozuyor", "tolerans içinde", "belirsiz")
    assert entries[1]["filter_excluded_folds"] > 0 and entries[3]["filter_excluded_folds"] == entries[1]["filter_excluded_folds"]
    head = list(res[POOLED].ledger[0])
    assert head[:15] == ["model_id", "fold_id", "horizon", "ticker", "prediction_date", "prediction_cutoff_date", "target_session_date",
                         "training_n", "n_chronological_train", "training_tickers_sha256", "training_targets_sha256", "ipo_price",
                         "realized_return", "realized_direction", "official_close"]
    assert all(list(r) == head for m in FAZ7C_MODEL_IDS for r in res[m].ledger)
    assert all(r["realized_fall_event"] == 1 - int(r["realized_direction"]) for r in res[POOLED].ledger)
    assert {r["logit_selected_C"] for r in res[ZERO_ROW].ledger} == {"ZERO"}
    assert [(r["fold_id"], r["training_n"]) for r in res[ZERO_ROW].ledger] == [(r["fold_id"], r["training_n"]) for r in res[POOLED].ledger]


def test_near_era_cell_is_pooled_minus_h99_d10_brier(synthetic_runs):
    res, _, log = synthetic_runs
    cell = bt.near_era_cell_fall(res[POOLED].ledger, res[H99].ledger)
    pooled = {r["ticker"]: r for r in res[POOLED].ledger if r["horizon"] == "D10" and r["prediction_date"] >= bt.NEAR_ERA_START}
    h99 = {r["ticker"]: r for r in res[H99].ledger if r["horizon"] == "D10"}
    common = [t for t in pooled if t in h99 and pooled[t]["logit_status"] == h99[t]["logit_status"] == "FIT_OK"]
    diffs = [(pooled[t]["logit_probability"] - pooled[t]["realized_direction"]) ** 2
             - (h99[t]["logit_probability"] - h99[t]["realized_direction"]) ** 2 for t in common]
    assert cell["n"] == len(common) and abs(cell["mean"] - sum(diffs) / len(diffs)) <= 1e-15
    entry = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()][1]
    assert entry["near_era"]["n"] == cell["n"] and entry["near_era"]["mean"] == cell["mean"]


def test_golden_writer_and_models_md_section_synthetic(synthetic_runs, tmp_path):
    """Bölüm yalnız altın dizinden üretilir; sentetik koşularla: başlıklar, kurallar, "kasa: bekliyor", §6.2 satırları aynen, yasak
    kalıplar ve "geçiyor" yok."""
    res, prev, log = synthetic_runs
    manifest = bt.write_golden_faz7c(res, prev, tmp_path / "g")
    sums = (tmp_path / "g" / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert len(sums) == 8 and set(manifest["runs"]) == set(FAZ7C_MODEL_IDS) == set(manifest["final_fit_previews"])
    with pytest.raises(bt.BacktestStop):
        bt.write_golden_faz7c(res, prev, tmp_path / "g")                           # üzerine yazmaz
    runs = r7c.load_faz7c(tmp_path / "g")[0]
    cmp = {"base_rate": runs[ZERO_ROW], "v1_5_h99": runs[ADDSALE]}
    lines: list[str] = []
    orig = bt.v15_d10_brier
    try:
        bt.v15_d10_brier = lambda rows: (0, 0.0)
        r7c.render_faz7c(lines.append, log, faz7c_dir=tmp_path / "g", cmp=cmp)
    finally:
        bt.v15_d10_brier = orig
    text = "\n".join(lines)
    for h in ("## Faz 7C: düşen arz modeli v0", "### Kartlar", "### Yakın dönem birincil hücresi", "### İkincil hücreler",
              "### Merdiven", "### Keşif (hüküm yok)", "### Fold özeti", "### Nihai fit önizlemesi (dondurulmadı)",
              "### Faz 7C koşuları ve deney günlüğü"):
        assert h in text
    for rule in r7c.OPERATIONAL_RULES_FAZ7C:
        assert rule in text
    assert text.count("kasa: bekliyor") == 4 and "geçiyor" not in text and not re.search(r"th[bm]20\d{6}", text)
    for row in r7c.expectation_rows():
        assert row["raw"]["beklenen"] in text and row["raw"]["aralik"] in text
    assert "(BİRİNCİL)" in text and "Proje sahibinin sorusunun cevabı" in text


def test_expectation_62_parsed_verbatim_and_position_rule():
    """T6: §6.2 tablosu şartnameden aynen okunur (5 satır; son satır her aday için ayrı hücre); konum kuralı kapalı aralık."""
    rows = r7c.expectation_rows()
    assert [(r["models"], r["comparator"], r["point"], r["lo"], r["hi"]) for r in rows] == [
        ((POOLED,), H99, -0.002, -0.015, 0.012), ((H99,), "base_rate", -0.025, -0.055, 0.005),
        ((POOLED,), "base_rate", -0.025, -0.055, 0.005), ((ADDSALE,), "base_rate", -0.005, -0.020, 0.010),
        ((H99, POOLED, ADDSALE), "v1_5_h99", 0.010, -0.020, 0.040)]
    spec = r7c.SPEC_PATH.read_text(encoding="utf-8")
    for r in rows:
        assert f"| {r['raw']['hucre']} | {r['raw']['beklenen']} | {r['raw']['aralik']} |" in spec
    assert r7c.position(-0.016, -0.015, 0.012) == "altında" and r7c.position(-0.015, -0.015, 0.012) == "aralık içinde"
    assert r7c.position(0.0121, -0.015, 0.012) == "üstünde" and "beklentiden çok iyi" in r7c.position_text("altında")


def test_models_md_faz7c_section_only_with_golden_and_between_faz4_and_faz7():
    """K15: Faz 7C bölümü Faz 4 ile Faz 7 arasında (Faz 7 bölüm testleri Faz 5 başlığına kadar keser; Faz 5 belgenin sonunda biter)."""
    text = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
    assert ("## Faz 7C: düşen arz modeli v0" in text) == r7c.golden_available()
    if r7c.golden_available():
        assert text.index("## Faz 4: tavan yolu modelleri") < text.index("## Faz 7C: düşen arz modeli v0") < \
            text.index("## Faz 7: tavan serisi v1") < text.index("## Faz 5: D1 sonrası")
        faz7 = text.split("## Faz 7: tavan serisi v1")[1].split("## Faz 5: D1 sonrası")[0]
        assert "## Faz 7C" not in faz7 and faz7.count("kasa: bekliyor") == 5
    assert text == r1.render()


# ---------------------------------------------------------------- T4: keşif varyantları ve varyant sayacı

def test_exploration_entries_and_counter(tmp_path):
    """T4 (SPEC_C_V0 §8; KARARLAR_C "Çokluk"): `denenenler.csv`'nin 2 054 satırı birer `kind: exploration` satırı; dosya yolu ve sha'sı
    her satırda; satır içeriği CSV'deki gibi; ikinci içe aktarma durur; kart sayacı bunları v2 veri sürümünde sayar (H99'da değil)."""
    raw = (ROOT / FAZ7C_EXPLORATION["path"]).read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))
    entries = bt.exploration_entries("pytest", recorded_at="2026-09-27T00:00:00+03:00")
    assert len(entries) == len(rows) == 2054 == FAZ7C_EXPLORATION["n"]
    assert [e["variant"] for e in entries] == rows and len({e["variant_id"] for e in entries}) == 2054
    assert {(e["kind"], e["model_id"], e["source"], e["source_sha256"], e["data_version_sha256"]) for e in entries} == {
        ("exploration", None, FAZ7C_EXPLORATION["path"], sha256_bytes(raw), V2_DATA_VERSION_SHA256)}
    log = tmp_path / "log.jsonl"                   # resmi günlüğün keşif dışı satırları (A'da hepsi; B'de keşif satırları çıkarılmış)
    lines = [x for x in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines()
             if x.strip() and json.loads(x).get("kind") != "exploration"]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    before = {dv: sc._n_variants_same_data(dv, "v1_5_h99", log_path=log) for dv in (H99_DATA_VERSION_SHA256, V2_DATA_VERSION_SHA256)}
    c_v2 = f7c.faz7c_variants(V2_DATA_VERSION_SHA256, log_path=log)          # Faz 7C backtest varyantları (A'da 0, B'de 3)
    assert bt.import_exploration(log, context="pytest") == 2054
    with pytest.raises(bt.BacktestStop):
        bt.import_exploration(log, context="pytest")
    after = {dv: sc._n_variants_same_data(dv, "v1_5_h99", log_path=log) for dv in before}
    assert after[H99_DATA_VERSION_SHA256] == before[H99_DATA_VERSION_SHA256]
    assert after[V2_DATA_VERSION_SHA256] == (before[V2_DATA_VERSION_SHA256][0] + 2054, before[V2_DATA_VERSION_SHA256][1])
    assert f7c.faz7c_variants(V2_DATA_VERSION_SHA256, log_path=log) == c_v2 + 2054
    assert r7c.exploration_count(log) == 2054


# ---------------------------------------------------------------- skorlama hücre tanımları ve SCORES.md satırı (§5, §11-13)

def test_scoring_cell_definitions_follow_spec_5():
    """§5.1–§5.3 hücre tanımları (commit A): üç adayın birincil hücresi D10 Brier − `base_rate` (canlı, kasa); ikinciller §5.2 ve
    §5.3 listeleri; var olan PRIMARY_CELLS / OOT_PRIMARY_CELLS değişmedi (ayrı sözlükler)."""
    cands = FAZ7C_MODEL_IDS[:3]
    assert sc.FAZ7C_CANDIDATES == cands and sc.FAZ7C_RULE_ROW == ZERO_ROW
    for m in cands:
        assert sc.FAZ7C_PRIMARY_CELLS[m] == sc.FAZ7C_OOT_PRIMARY_CELLS[m] == {"output": "p_up", "horizon_or_k": "D10",
                                                                              "metric": "Brier", "rule_ids": ["base_rate"]}
    key = lambda cells: [(c["horizon_or_k"], c["rule_id"]) for c in cells]  # noqa: E731
    common = [("D10", "v1_5_h99"), ("D10", "base_last10_rate"), ("D5", "base_rate"), ("D5", "v1_5_h99")]
    assert key(sc.FAZ7C_OOT_SECONDARY_CELLS[H99]) == common + [("D10", ADDSALE)]
    assert key(sc.FAZ7C_OOT_SECONDARY_CELLS[POOLED]) == common + [("D10", ADDSALE), ("D10", H99), ("D10", ZERO_ROW)]
    assert key(sc.FAZ7C_OOT_SECONDARY_CELLS[ADDSALE]) == common + [("D5", "base_last10_rate")]
    assert all(key(sc.FAZ7C_LIVE_SECONDARY_CELLS[m]) == common + [("D5", "base_last10_rate")] for m in cands)
    assert sc.FAZ7C_BACKTEST_NEAR_ERA["primary"]["model_id"] == POOLED and sc.FAZ7C_BACKTEST_NEAR_ERA["primary"]["rule_id"] == H99
    assert not set(sc.PRIMARY_CELLS) & set(FAZ7C_MODEL_IDS) and not set(sc.OOT_PRIMARY_CELLS) & set(FAZ7C_MODEL_IDS)


@pytest.mark.requires_git_history
def test_scores_panel_row_only_with_block_and_verdict_language():
    """SCORES.md backtest paneli (C) satırı yalnız (C) adayları INDEX'teyken (skor dosyasında `faz7c_near_era` bloğu) yazılır; hüküm
    sütunu §5.1 etiketidir ("geçiyor" yok). §11-13: "geçiyor" yalnız n ≥ 30 ve aralık 0'ın altında; zaman-dışı satırda ek."""
    committed = json.loads((ROOT / "scores" / "scores.json").read_text(encoding="utf-8"))
    # 8e3a623 durumunda (J30/K19) blok ve satır yok; skorlar 27 modelle yeniden üretilince (BORSAI_FAZ7_OOT_RECORDS, SPEC_DEVIATIONS L)
    # blok altın ledger'larla aynı ve satır belgede.
    if fs7.scores_json_is_pre_faz7():
        assert "faz7c_near_era" not in committed and "(C) yakın dönem" not in (ROOT / "docs" / "SCORES.md").read_text(encoding="utf-8")
    else:
        assert committed["faz7c_near_era"] == json.loads(pretty_json_bytes(sc.faz7c_near_era_block()))
        assert sc.render_faz7c_panel_row(committed["faz7c_near_era"]) in (ROOT / "docs" / "SCORES.md").read_text(encoding="utf-8")
    full = committed
    committed = {k: v for k, v in committed.items() if k != "faz7c_near_era"}
    block = {"title": sc.FAZ7C_PANEL_TITLE, "model_id": POOLED, "rule_id": H99, "output": "p_up", "horizon_or_k": "D10",
             "metric": "Brier", "first_trading_date_from": "2024-01-01", "n": 75, "n_blocks": 22, "model_value": 0.2,
             "rule_value": 0.21, "diff": -0.01, "ci95": [-0.03, 0.01], "label": "belirsiz", "tolerance": 0.008, "scale": "backtest"}
    row = sc.render_faz7c_panel_row(block)
    assert row.startswith("| (C) yakın dönem: `fall_d10_v0_pooled` |") and "belirsiz (§5.1 etiketi, δ = +0.008)" in row
    assert "geçiyor" not in row
    post = sc.load_post_d1_scores()
    doc = sc.render_doc({**committed, "faz7c_near_era": block}, post)
    assert row in doc and doc.index(row) > doc.index("## 5. Geçmiş veri testi")
    assert sc.render_doc(full, post) == (ROOT / "docs" / "SCORES.md").read_text(encoding="utf-8")
    assert sc.verdict(29, [-0.05, -0.01]) == "yetersiz örnek" and sc.verdict(30, [-0.05, -0.01]) == "geçiyor"
    assert sc.verdict(30, [-0.05, 0.01]) == "ayırt edilemiyor" and sc.verdict(9, [-0.05, -0.01]) is None
    assert sc._oot_verdict({"diff": -0.02, "verdict": sc.V_PASS}) == "geçiyor (zaman-dışı terazide)"
    assert sc._oot_verdict({"diff": -0.02, "verdict": sc.V_NEUTRAL}) == "ayırt edilemiyor"

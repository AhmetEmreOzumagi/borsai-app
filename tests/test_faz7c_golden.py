"""Faz 7C (commit B): düşen arz modeli v0 adaylarının resmi walk-forward koşuları, altın ledger'ları, nihai fit önizlemeleri, keşif
satırları ve MODELS.md Faz 7C bölümü (SPEC_C_V0 §5.1, §5.4, §6.2, §11-5, §11-6, §11-7, §11-9, §11-11; görev kararları T3, T4, T6).
Bu dosyadaki testler gerçek walk-forward'u ve nihai fit'leri koşar (commit A'dan sonra). Modeller dondurulmadı: models/ değişmez."""
from __future__ import annotations

import csv
import io
import json
import re
import subprocess
from fractions import Fraction

import numpy as np
import pytest

from borsai import backtest as bt
from borsai import predict_fall as pf
from borsai import registry as reg
from borsai import report as r1
from borsai import report_faz7c as r7c
from borsai import scoring as sc
from borsai.data import additional_sale_shares
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes, sha256_file
from borsai.specs import (FAZ7C_EXPLORATION, FAZ7C_MODEL_IDS, FAZ7C_MODEL_SPECS, H99_DATA_VERSION_SHA256, SPEC_DOCUMENTS_FAZ7C,
                          V2_DATA_VERSION_SHA256, spec_sha256)

import faz7_support as fs7
import faz7c_support as f7c
import faz8_support as fs8

H99, POOLED, ADDSALE, ZERO_ROW = FAZ7C_MODEL_IDS
GOLDEN = bt.GOLDEN_FAZ7C_DIR
COMMIT_A = "3c93f9c731bdda0280e00c5e7f90b7f805572dca"      # BORSAI_FAZ7C_A: resmi koşunun kodu (borsai_dirty = false)
COMMIT_A2 = "1239e450aa969e2d01d8b7198ed54129932d7169"     # BORSAI_FAZ7C_A2: yalnız predict_fall ufuk denetimi (SPEC_DEVIATIONS K14)
COMMIT_A3 = "77d0ee5412ca8395ae29d4674008b67400216bf8"     # BORSAI_FAZ7C_A3: yalnız MODELS.md bölüm sırası (report.py; K15)
CONTEXT = "faz7c_golden"
VOLATILE = ("created_at", "code_version", "runtime")


@pytest.fixture(scope="module")
def golden():
    return r7c.load_faz7c(GOLDEN)


@pytest.fixture(scope="module")
def rerun(tmp_path_factory):
    """Aynı kodla dört koşu; kendi geçici günlüğüne yazar (resmi günlük yalnız `faz7c_golden` satırlarını taşır)."""
    log = tmp_path_factory.mktemp("faz7c_log") / "log.jsonl"
    res = bt.run_faz7c(log_path=log, context="pytest")
    assert len(log.read_text(encoding="utf-8").splitlines()) == len(FAZ7C_MODEL_IDS)
    return res


@pytest.fixture(scope="module")
def log_entries():
    return [json.loads(x) for x in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]


def _roundtrip(obj):
    return json.loads(json.dumps(obj))


# ---------------------------------------------------------------- altın dosyalar, yeniden koşu, günlük

def test_backtest_byte_identical_to_faz7c_golden(rerun, golden):
    """Koşu deterministiktir: dört ledger altın dosyalarla bayt bayt aynı."""
    _, manifest, _ = golden
    assert list(rerun) == list(FAZ7C_MODEL_IDS)
    for m, res in rerun.items():
        assert res.ledger_csv == (GOLDEN / bt.golden_filename(m)).read_bytes(), m
        assert res.log_entry["ledger_sha256"] == manifest["runs"][m]["ledger_sha256"]


@pytest.mark.requires_git_history
def test_code_after_official_run_changed_only_predict_fall_and_report_order():
    """Resmi koşu commit A'nın temiz koduyla; A → A2 arasında borsai/'de yalnız `predict_fall.py` (K14), A2 → A3 arasında yalnız
    `report.py` (bölüm sırası; K15) değişti: backtest, fit ve önizleme kodu aynı (yeniden koşu testi bu kodla bayt-eşit)."""
    def changed(a, b):
        return subprocess.run(["git", "diff", "--name-only", a, b, "--", "borsai"], cwd=ROOT, check=True, capture_output=True,
                              text=True).stdout.split()
    assert changed(COMMIT_A, COMMIT_A2) == ["borsai/predict_fall.py"] and changed(COMMIT_A2, COMMIT_A3) == ["borsai/report.py"]


@pytest.mark.requires_git_history
def test_manifest_and_sha256sums(golden):
    _, manifest, _ = golden
    files = {v["file"]: v["ledger_sha256"] for v in manifest["runs"].values()}
    files.update({v["file"]: v["sha256"] for v in manifest["final_fit_previews"].values()})
    assert len(files) == 4 + 4
    for name, sha in files.items():
        assert sha256_file(GOLDEN / name) == sha, name
    lines = (GOLDEN / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert sorted(lines) == sorted(f"{sha}  {name}" for name, sha in files.items())
    assert sorted(p.name for p in GOLDEN.iterdir()) == sorted([*files, "MANIFEST.json", "SHA256SUMS"])
    assert set(manifest["runs"]) == set(manifest["final_fit_previews"]) == set(FAZ7C_MODEL_IDS)
    for m in FAZ7C_MODEL_IDS:
        info = manifest["runs"][m]
        assert info["spec_sha256"] == spec_sha256(FAZ7C_MODEL_SPECS[m]) and info["plan_id"] == FAZ7C_MODEL_SPECS[m]["plan_id"]
        assert info["data_version_sha256"] == FAZ7C_MODEL_SPECS[m]["training"]["data_version_sha256"]
        assert info["log_entry"]["context"] == CONTEXT
    assert manifest["comparator_ledgers"] == bt.FAZ7C_COMPARATOR_LEDGERS
    assert manifest["borsai_dirty"] is False and manifest["git_commit"] == COMMIT_A
    assert fs_tree(COMMIT_A) == manifest["borsai_source_sha256"]


def fs_tree(rev):
    import faz7_support as fs7

    return fs7.borsai_tree_sha256_at(rev)


@pytest.mark.requires_git_history
def test_official_log_has_one_backtest_line_per_model(golden, log_entries, rerun):
    """§11-11: her koşu günlükte bir `kind: backtest` satırı (context faz7c_golden, commit A'nın temiz kodu); spec_sha256 şartname
    sözlüğünün, spec_document_sha256 SPEC_C_V0.md'nin, decisions_document_sha256 KARARLAR_C.md'nin sha256'sı; veri sürümü h99 için
    H99, ötekiler için v2; metrikler ve hücreler yeniden koşuyla aynı."""
    _, manifest, _ = golden
    for m in FAZ7C_MODEL_IDS:
        hits = [e for e in log_entries if e.get("model_id") == m]
        assert [e["context"] for e in hits] == [CONTEXT], m
        e = hits[0]
        assert e["kind"] == "backtest" and e["plan_id"] == FAZ7C_MODEL_SPECS[m]["plan_id"]
        assert e["spec_sha256"] == spec_sha256(FAZ7C_MODEL_SPECS[m])
        assert e["spec_document_sha256"] == SPEC_DOCUMENTS_FAZ7C["SPEC_C_V0"]["sha256"] == sha256_file(ROOT / "docs/specs_faz7_c/SPEC_C_V0.md")
        assert e["decisions_document_sha256"] == SPEC_DOCUMENTS_FAZ7C["KARARLAR_C"]["sha256"]
        assert e["data_version_sha256"] == (H99_DATA_VERSION_SHA256 if m == H99 else V2_DATA_VERSION_SHA256)
        assert e["evaluated"] == [{"run_key": k, "ledger_sha256": v["sha256"]} for k, v in bt.FAZ7C_COMPARATOR_LEDGERS.items()]
        assert e["borsai_dirty"] is False and e["git_commit"] == COMMIT_A and e["borsai_source_sha256"] == fs_tree(COMMIT_A)
        assert e["ledger_sha256"] == manifest["runs"][m]["ledger_sha256"] and e["started_at"] == manifest["runs"][m]["log_entry"]["started_at"]
        fresh = rerun[m].log_entry
        for key in ("metrics", "near_era", "near_era_secondary", "folds_total", "folds_scorable", "tufe", "filter_excluded_folds"):
            assert e.get(key) == _roundtrip(fresh.get(key)), (m, key)
    assert f7c.faz7c_variants(H99_DATA_VERSION_SHA256) == 1


def test_official_log_has_the_2054_exploration_lines(log_entries):
    """T4 (SPEC_C_V0 §8, §11-11; KARARLAR_C "Çokluk"): `denenenler.csv`'nin 2 054 satırı birer `kind: exploration` satırı, dosyanın
    sha'sıyla; sıra ve içerik CSV'dekiyle aynı; v2 veri sürümünde; kart sayacı bunları sayar."""
    ex = [e for e in log_entries if e.get("kind") == "exploration"]
    raw = (ROOT / FAZ7C_EXPLORATION["path"]).read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))
    assert len(ex) == 2054 == len(rows) and [e["variant"] for e in ex] == rows
    assert {(e["context"], e["source_sha256"], e["source"], e["data_version_sha256"], e["model_id"]) for e in ex} == {
        (bt.FAZ7C_EXPLORATION_CONTEXT, sha256_bytes(raw), FAZ7C_EXPLORATION["path"], V2_DATA_VERSION_SHA256, None)}
    assert len({e["recorded_at"] for e in ex}) == 1 and len({e["variant_id"] for e in ex}) == 2054
    assert f7c.faz7c_variants(V2_DATA_VERSION_SHA256) == 3 + 2054
    assert sc._n_variants_same_data(V2_DATA_VERSION_SHA256, POOLED)[0] == 2 + 3 + 2054
    # Faz 8 (SPEC_DEVIATIONS N19; proje sahibi kararı 2026-10-01; J16/K10 kalıbı): break_floor_v0'ın backtest satırı H99 sürümünde sayılır
    assert sc._n_variants_same_data(H99_DATA_VERSION_SHA256, H99)[0] == 22 + 1 + fs8.faz8_variants(H99_DATA_VERSION_SHA256)
    with pytest.raises(bt.BacktestStop):
        bt.import_exploration(ROOT / "experiments" / "log.jsonl")                  # ikinci içe aktarma durur (dosyaya yazmadan)


# ---------------------------------------------------------------- ledger'lar

def test_ledger_fold_sets_statuses_and_leakage(golden):
    """§11-6 (gerçek ledger'larda): h99 ve pooled 94, addsale 95 test arzı (ufuk başına); yakın dönem D10'da h99 ve pooled aynı 75
    FIT_OK fold, 22 ay; her fold'da eğitim D_h seansı < T (plan testinde; burada eğitim ticker sha'ları plana eşit)."""
    runs = golden[0]
    for m, n in ((H99, 82), (POOLED, 94), (ADDSALE, 95), (ZERO_ROW, 94)):          # ledger'da skorlanabilir fold'lar (h99: 94'ün 82'si)
        for h in ("D5", "D10"):
            hr = [r for r in runs[m] if r["horizon"] == h]
            assert len({r["ticker"] for r in hr}) == len(hr) == n, (m, h)
    assert {r["ticker"] for r in runs[H99]} <= {r["ticker"] for r in runs[POOLED]} < {r["ticker"] for r in runs[ADDSALE]}
    near = {m: [r["ticker"] for r in runs[m] if r["horizon"] == "D10" and r["logit_status"] == "FIT_OK"
                and r["prediction_date"] >= bt.NEAR_ERA_START] for m in (H99, POOLED)}
    assert near[H99] == near[POOLED] and len(near[H99]) == 75
    assert len({r["prediction_date"][:7] for r in runs[H99] if r["ticker"] in set(near[H99])}) == 22


def test_near_era_primary_cell_and_label(golden, log_entries):
    """§5.1: birincil hücre `pooled − h99` (D10 Brier, T ≥ 2024-01-01) altın ledger'lardan yeniden hesaplanır, günlükteki havuz
    satırıyla aynı; etiket `near_era_label_fall` (δ = 0.008)."""
    runs = golden[0]
    cell = bt.near_era_cell_fall(runs[POOLED], runs[H99])
    e = next(x for x in log_entries if x.get("model_id") == POOLED)["near_era"]
    assert (cell["n"], cell["n_months"], cell["mean"], cell["ci95"], cell["label"]) == (e["n"], e["n_months"], e["mean"], e["ci95"], e["label"])
    assert cell["label"] == bt.near_era_label_fall(cell["ci95"]) and cell["n"] == 75 and cell["n_months"] == 22
    ev = r7c.evaluate(runs, r7c.comparators())
    assert ev["near"]["mean"] == cell["mean"] and len(ev["rows62"]) == 7


# ---------------------------------------------------------------- nihai fit önizlemesi (§11-5, §11-9)

@pytest.mark.parametrize("model_id", FAZ7C_MODEL_IDS)
def test_final_fit_preview_reproducible_and_stdlib_parity(model_id, golden):
    """§11-9: önizleme `final_fit_fall`'ın yeniden koşusuyla (created_at, code_version, runtime dışında) aynı; eğitim arzlarının
    hepsinde stdlib `predict_fall.predict` (JSON) ile nihai fit (sklearn predict_proba ya da sabit) |Δ| ≤ 1e-12."""
    preview = golden[2][model_id]
    params, fits = bt.final_fit_fall(model_id)
    strip = lambda d: {k: v for k, v in json.loads(pretty_json_bytes(dict(d))).items() if k not in VOLATILE}   # noqa: E731
    assert strip(params) == strip(preview)
    spec = FAZ7C_MODEL_SPECS[model_id]
    assert preview["spec_sha256"] == spec_sha256(spec) and preview["model_id"] == model_id
    ds = bt.fall_dataset(model_id)
    add = additional_sale_shares(ds)
    rows = bt.fall_training_rows(spec, ds, add, check=True)
    raw, info = bt.fall_raw_features(spec, rows, add)
    worst, n = 0.0, 0
    for r in rows:
        inputs = {**r.inputs, "total_demand_filter_status": r.total_demand_filter_status, "additional_sale_shares": add[r.ticker]}
        if info:
            inputs["tufe_index"] = info[r.ticker]["index"]
        out = pf.predict(preview, inputs)
        assert out["refused"] is None, out["refused"]
        for h in ("D5", "D10"):
            hf = fits[h]
            if hf.final is None or hf.logit.estimator is None:
                ref = hf.logit.constant
            else:
                z = hf.final.transform(raw[r.ticker], r.total_demand_filter_status)["z"]
                ref = float(hf.logit.estimator.predict_proba(np.array([[z[c] for c in hf.logit.columns]]))[0][1])
            worst = max(worst, abs(out[h]["p_up"] - ref))
        n += 1
    assert n == spec["training"]["n"] and worst <= 1e-12
    assert preview["training"]["n"] == spec["training"]["n"]
    assert (preview["training"]["events_D10"], preview["training"]["events_D5"]) == (spec["training"]["events_D10"], spec["training"]["events_D5"])


def test_zero_preview_is_training_rate_fraction(golden):
    p = golden[2][ZERO_ROW]
    assert p["horizons"]["D10"]["p_up"]["value"] == float(Fraction(1) - Fraction(39, 161))
    assert p["horizons"]["D5"]["p_up"]["value"] == float(Fraction(1) - Fraction(29, 161))


# ---------------------------------------------------------------- MODELS.md, models/, hijyen

@pytest.mark.requires_git_history
def test_models_md_faz7c_section(golden):
    text = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
    assert text == r1.render()
    sec = text.split("## Faz 7C: düşen arz modeli v0")[1].split("## Faz 7: tavan serisi v1")[0]
    assert text.index("## Faz 4: tavan yolu modelleri") < text.index("## Faz 7C: düşen arz modeli v0") < \
        text.index("## Faz 7: tavan serisi v1") < text.index("## Faz 5: D1 sonrası")        # K15
    for rule in r7c.OPERATIONAL_RULES_FAZ7C:
        assert rule in sec
    for row in r7c.expectation_rows():
        assert row["raw"]["beklenen"] in sec and row["raw"]["aralik"] in sec
    # dondurmadan sonra (BORSAI_FAZ7C_FREEZE, commit F2) bölümün sonunda "### Dondurma" notu: bir "kasa: bekliyor" satırı daha
    # (not yalnız INDEX (C)'yi listeleyince yazılır; varlığı tests/test_faz7c_frozen.py'de)
    assert sec.count("### Dondurma") <= (1 if fs7.frozen_faz7c_ids() else 0)
    assert sec.count("kasa: bekliyor") == 4 + sec.count("### Dondurma") and "günlükte 2054 `kind: exploration` satırı" in sec
    cell = bt.near_era_cell_fall(golden[0][POOLED], golden[0][H99])
    assert f"→ **{cell['label']}**" in sec and "geçiyor" not in sec and not re.search(r"th[bm]20\d{6}", sec)


@pytest.mark.requires_git_history
def test_models_dir_registry_scores_unchanged():
    """K2: önizlemeler models/'e yazılmadı; INDEX 23 giriş, (C) yok; models/, registry/, scores/ çalışma ağacında değişmedi.
    Dondurmadan (BORSAI_FAZ7C_FREEZE) sonra models/'de yalnız dört (C) dosyası ve INDEX.json'un sonundaki dört girişi vardır
    (ilk 23 giriş aynen; donmuş dosyaların kendisi tests/test_faz7c_frozen.py; SPEC_DEVIATIONS K19)."""
    entries = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]
    frozen = fs7.frozen_faz7c_ids()
    assert frozen in ([], list(FAZ7C_MODEL_IDS)) and len(entries) == 23 + len(frozen)
    assert [e["model_id"] for e in entries if e["model_id"] in FAZ7C_MODEL_SPECS] == frozen
    assert sorted(p.name for p in (ROOT / "models").iterdir() if p.name.startswith("fall_d10")) == sorted(f"{m}.json" for m in frozen)
    status = subprocess.run(["git", "status", "--porcelain", "--", "models", "registry", "scores"], cwd=ROOT, check=True,
                            capture_output=True, text=True).stdout
    assert status == ""


def test_no_sealed_code_in_golden_files_and_new_log_lines(log_entries):
    """§11-12: altın dizinin dosyalarında ve Faz 7C günlük satırlarında kasa kodu ve bülten adı kalıbı yok."""
    _, cohort = reg.read_cohort()
    sealed = sorted(r["ticker"] for r in reg.cohort_members(cohort) if r["vault"] == reg.VAULT_SEALED)
    n_sealed = len(sealed)                                                          # yerel değişken: hata çıktısı kod basmaz
    assert n_sealed == 64
    pattern = re.compile(r"\b(" + "|".join(sealed) + r")\b")
    texts = [(p.name, p.read_text(encoding="utf-8")) for p in sorted(GOLDEN.iterdir())]
    texts.append(("log", "\n".join(json.dumps(e, ensure_ascii=False) for e in log_entries
                                   if e.get("kind") == "exploration" or e.get("model_id") in FAZ7C_MODEL_IDS)))
    md = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
    texts.append(("MODELS.md Faz 7C", md.split("## Faz 7C: düşen arz modeli v0")[1].split("## Faz 7: tavan serisi v1")[0]))
    for name, text in texts:
        n = len(set(pattern.findall(text)))
        assert n == 0, (name, n)
        assert not re.search(r"th[bm]20\d{6}", text), name

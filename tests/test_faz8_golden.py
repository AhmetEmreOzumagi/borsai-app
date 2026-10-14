"""Faz 8 resmi koşusu (commit B): docs/faz8/backtest/ çıktıları, deney günlüğü, nihai fit önizlemeleri ve docs/MODELS.md Faz 8 bölümü
(SPEC_BREAK_V0 §7, §13-1, 4, 5, 6, 9, 15). Ledger'lar bu makinede bit-eşit yeniden üretilir; önizlemeler numpy ↔ stdlib paritesiyle
sınanır. Modeller dondurulmadı."""
from __future__ import annotations

import json
import subprocess
from collections import Counter
from fractions import Fraction

import pytest

from borsai import post_break as pbk
from borsai import predict_break as pb
from borsai import report as r1
from borsai import report_faz8 as r8
from borsai import scoring as sc
from borsai.data import load_dataset
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes, sha256_file
from borsai.specs import (FAZ8_MODEL_IDS, FAZ8_SENSITIVITIES, H99_DATA_VERSION_SHA256, OPERATIONAL_RULES_FAZ8, POST_BREAK_MODEL_SPECS,
                          SPEC_DOCUMENTS_FAZ8, spec_sha256)

import faz8_support as fs8

GOLDEN = pbk.GOLDEN_DIR
VOLATILE = ("created_at", "code_version", "runtime")


@pytest.fixture(scope="module")
def dataset():
    return load_dataset()


@pytest.fixture(scope="module")
def table(dataset):
    return pbk.load_break_table(dataset)


@pytest.fixture(scope="module")
def golden():
    rows, sens, manifest, previews = r8.load_faz8()
    return {"rows": rows, "sens": sens, "manifest": manifest, "previews": previews}


@pytest.fixture(scope="module")
def log_entries():
    return [json.loads(x) for x in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]


def test_b1_files_and_shas_match_manifest_and_log(golden, log_entries):
    m = golden["manifest"]
    sums = dict(reversed(line.split("  ")) for line in (GOLDEN / "SHA256SUMS").read_text(encoding="utf-8").splitlines())
    for name, sha in sums.items():
        assert sha256_file(GOLDEN / name) == sha, name
    run = m["runs"][pbk.MODEL_ID]
    assert sha256_file(GOLDEN / run["file"]) == run["ledger_sha256"] and run["plan_id"] == pbk.PLAN_BREAK_H99
    bt = [e for e in log_entries if e.get("kind") == "backtest" and e.get("model_id") == pbk.MODEL_ID]
    assert len(bt) == 1 and bt[0]["ledger_sha256"] == run["ledger_sha256"] and bt[0]["context"] == "official"
    e = bt[0]
    assert e["spec_sha256"] == spec_sha256(POST_BREAK_MODEL_SPECS[pbk.MODEL_ID]) == run["spec_sha256"]
    assert e["spec_document_sha256"] == sha256_file(ROOT / SPEC_DOCUMENTS_FAZ8["SPEC_BREAK_V0"]["path"]) == \
        SPEC_DOCUMENTS_FAZ8["SPEC_BREAK_V0"]["sha256"]
    assert e["decisions_document_sha256"] == SPEC_DOCUMENTS_FAZ8["KARARLAR_FAZ8"]["sha256"]
    assert e["data_version_sha256"] == H99_DATA_VERSION_SHA256 and e["borsai_dirty"] is False
    assert e["sessions_file_sha256"] == POST_BREAK_MODEL_SPECS[pbk.MODEL_ID]["training"]["sessions_file_sha256"]
    assert e["path_cells_source"]["faz4_cell_parity_folds"] == 87
    sens = fs8.faz8_sensitivity_lines()
    assert sorted(s["model_id"] for s in sens) == sorted(FAZ8_SENSITIVITIES) and all(s["context"] == "official" for s in sens)
    for s in sens:
        assert sha256_file(ROOT / s["ledger_file"]) == s["ledger_sha256"] == m["sensitivities"][s["model_id"]]["ledger_sha256"]
        assert s["is_model"] is False and s["spec_document_sha256"] == SPEC_DOCUMENTS_FAZ8["SPEC_BREAK_V0"]["sha256"]


def test_b2_variant_counter_counts_backtest_not_sensitivity(log_entries):
    """§13-15: kart varyant sayacı backtest satırını sayar (H99 sürümünde Faz 8 varyantı 1), duyarlılık satırlarını saymaz."""
    assert fs8.faz8_variants(H99_DATA_VERSION_SHA256) == 1
    n_bt = len({(e["model_id"], e["spec_sha256"]) for e in log_entries
                if e.get("kind") == "backtest" and e.get("data_version_sha256") == H99_DATA_VERSION_SHA256})
    n_ex = len({e["variant_id"] for e in log_entries if e.get("kind") == "exploration" and e.get("data_version_sha256") == H99_DATA_VERSION_SHA256})
    assert sc._n_variants_same_data(H99_DATA_VERSION_SHA256, pbk.MODEL_ID) == (n_bt + n_ex, 1)


def test_b3_ledger_structure_and_plan(golden, table):
    rows = golden["rows"]
    assert len(rows) == 82 and tuple(rows[0]) == pbk.LEDGER_COLUMNS
    assert sum(r["first_trading_date"] >= pbk.NEAR_ERA_START for r in rows) == 69
    assert Counter(r["b"] for r in rows) == {"1": 18, "2": 11, "3": 4, "4": 13, "5": 12, "6": 8, "7": 6, "8": 6, "9": 4}
    assert sum(r["structural_zero_D10"] == "1" for r in rows) == 16 and sum(r["test_b_floor"] == "1" for r in rows) == 35
    folds = {f.fold_id: f for f in pbk.plan_break_folds(table)}
    for r in rows:
        f = folds[r["fold_id"]]
        assert r["training_max_label_date"] == "" or r["training_max_label_date"] < r["break_date"]
        assert r["cells_max_session_date"] == "" or r["cells_max_session_date"] < r["first_trading_date"]
        lbl = table.labels[r["ticker"]]
        assert r["realized_F1"] == str(lbl.y1) and r["realized_F2"] == ("" if lbl.y2 is None else str(lbl.y2))
        if f.training["F1"]:
            assert float(r["zero_F1"]) == float(Fraction(f.events["F1"], len(f.training["F1"])))
        it2 = json.loads(r["inner_table_F2"])
        assert (it2["status"] == pb.TARGET_UNDEFINED_F2) == (r["b"] == "9")
        assert r["status"] in pbk.FOLD_STATUSES and (r["p_F1"] != "") == (r["status"] == "FIT_OK")
    assert sum(json.loads(r["inner_table_F2"])["status"] != pb.TARGET_UNDEFINED_F2 for r in rows) == 78


def test_b4_ledger_reproduces_bit_exact(dataset, table, golden):
    """Resmi ledger bu makinede yeniden koşuyla bayt-eşit (ilk koşu dondurulmuş kabul edilmez; Fable'ın bağımsız yeniden üretimi ayrı)."""
    ledger, info = pbk.backtest_ledger(table, pbk._path_units(dataset))
    assert pbk.ledger_csv_bytes(ledger) == (GOLDEN / golden["manifest"]["runs"][pbk.MODEL_ID]["file"]).read_bytes()
    assert info == golden["manifest"]["info"]


def test_b5_previews_refit_and_stdlib_parity(dataset, table, golden):
    """§13-9: 82 (F2 78) eğitim satırında numpy nihai model ile stdlib `predict_break` |Δp| ≤ 1e-12; önizleme yeniden fit'le
    (`created_at`, `code_version`, `runtime` dışında) aynı."""
    for m in FAZ8_MODEL_IDS:
        params, fits = pbk.final_fit(m, dataset, table=table)
        fresh = json.loads(pretty_json_bytes(params))
        old = golden["previews"][m]
        assert {k: v for k, v in fresh.items() if k not in VOLATILE} == {k: v for k, v in old.items() if k not in VOLATILE}, m
        par = pbk.parity_rows(old, fits, table)
        assert max(par.values()) <= pbk.PARITY_TOL and golden["manifest"]["final_fit_previews"][m]["parity_max_abs"] == par
        assert old["training"]["n_F1"] == 82 and old["training"]["n_F2"] == 78 and old["training"]["cutoff_date"] <= pbk.OUTCOME_CUTOFF
        pb.check_params(old)


def test_b6_models_md_faz8_section(golden):
    text = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
    assert text == r1.render()
    assert text.index("## Faz 4: tavan yolu modelleri") < text.index("## Faz 8: kırılma akşamı") < \
        text.index("## Faz 7C: düşen arz modeli v0") < text.index("## Faz 7: tavan serisi v1") < text.index("## Faz 5: D1 sonrası")
    sec = text.split("## Faz 8: kırılma akşamı")[1].split("## Faz 7C: düşen arz modeli v0")[0]
    for rule in OPERATIONAL_RULES_FAZ8:
        assert rule in sec
    six = sec.split("### §6 önceden yazılmış beklenti, satır satır")[1].split("### Keşif")[0]
    assert sum(1 for line in six.splitlines() if line.startswith("| ") and not line.startswith("| Hücre")) == 13
    for heading in ("### Kartlar", "### Birincil hücre ve `@ZERO` hücresi", "### İkincil ve bilgi hücreleri", "### Keşif (hüküm yok)",
                    "### Fold özeti", "### Nihai fit önizlemesi (dondurulmadı)", "### Faz 8 koşusu ve deney günlüğü"):
        assert heading in sec
    assert not any(n in text for n in FAZ8_SENSITIVITIES)
    ev = r8.evaluate(golden["rows"], golden["previews"][pbk.MODEL_ID])
    p = ev["cells"]["near"]["F1_product"]
    assert f"{p['mean']:+.4f}" in sec and "Hüküm sayıları: tuttu" in sec


FAZ8_LAST_COMMIT = "57dcd0c"     # Faz 8'in son commit'i (dondurma F2); sonrası sabit aralık dışı (K-PIN-L, SPEC_DEVIATIONS N26)


@pytest.mark.requires_git_history
def test_b7_old_outputs_unchanged():
    # K-PIN-L (N26; proje sahibi kararı 2026-10-02): yol listesinin tamamı sabit 5d84e88..57dcd0c aralığına bağlı; o aralıkta yalnız üç
    # dondurma dosyası. Sonraki commit'lerin (push kanıtları, canlı POST_BREAK çıktıları) denetimi kendi testlerinde (test_faz8_live).
    out = subprocess.run(["git", "diff", "--name-only", "5d84e88", FAZ8_LAST_COMMIT, "--", "tests/reference", "models", "registry", "data",
                          "scores", "app", "docs/specs", "docs/specs_faz4", "docs/specs_faz5", "docs/specs_faz6", "docs/specs_faz7",
                          "docs/specs_faz7_c", "docs/specs_faz8"], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    frozen = sorted(f"models/{n}" for n in fs8.frozen_post_break_files())      # K-PIN (N25): dondurmadan sonra yalnız üç dosya
    assert out.split() == frozen
    added = subprocess.run(["git", "diff", "--name-only", "--diff-filter=A", "5d84e88", FAZ8_LAST_COMMIT, "--", "models"], cwd=ROOT,
                           check=True, capture_output=True, text=True).stdout
    assert added.split() == frozen
    log = subprocess.run(["git", "show", "5d84e88:experiments/log.jsonl"], cwd=ROOT, check=True, capture_output=True).stdout
    assert (ROOT / "experiments" / "log.jsonl").read_bytes().startswith(log)        # yalnız ekleme

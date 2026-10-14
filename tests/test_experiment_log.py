"""K4: her backtest koşusu deney günlüğüne otomatik yazılır (CLAUDE.md kural 4)."""
from __future__ import annotations

import json

from borsai import backtest as bt
from borsai.provenance import ROOT, sha256_file
from borsai.specs import FAZ7_MODEL_SPECS, FAZ7C_MODEL_SPECS, MODEL_SPECS, POST_BREAK_MODEL_SPECS, POST_D1_MODEL_SPECS, spec_sha256

import faz8_support as fs8

REQUIRED = {"kind", "context", "model_id", "spec_sha256", "data_version_sha256", "ledger_sha256", "metrics",
            "started_at", "finished_at", "git_commit", "borsai_source_sha256", "plan_id"}
# SPEC_CEILING_PATH_V0 §7: H99 koşullu değerlendirme yeni model değildir; günlüğe `kind: conditional_eval` satırıyla düşer.
REQUIRED_CONDITIONAL = {"kind", "context", "model_id", "evaluated", "spec_document", "spec_document_sha256",
                        "data_version_sha256", "metrics", "started_at", "finished_at", "git_commit", "borsai_source_sha256"}
# Bağımsız denetimin (docs/fable_faz4_audit/) duyarlılık koşuları: `kind: sensitivity`, `is_model: false`.
# MODEL DEĞİLDİR: dondurulmaz, INDEX'e girmez, hiçbir tabloya ve skora girmez; yalnız kural 4'ün kaydıdır.
REQUIRED_SENSITIVITY = {"kind", "context", "model_id", "base_model_id", "variant", "is_model", "note", "plan_id",
                        "spec_sha256", "spec_document", "spec_document_sha256", "data_version_sha256", "ledger_file",
                        "ledger_sha256", "metrics", "started_at", "finished_at", "git_commit", "borsai_source_sha256"}
# Faz 5 bağımsız denetiminin (docs/fable_faz5_audit/) iki duyarlılık koşusu: temel model POST_D1 (`stage`), satırlar
# denetimin `ekler/sensitivity_runs.jsonl` dosyasındaki içerikle aynen (Faz 4 kalıbı; alan kümesi denetiminki). Model
# olmadıkları `variation.note`'ta yazılıdır ("model değil; dondurulmaz"); aynı kural: hiçbir tabloya ve skora girmezler.
REQUIRED_SENSITIVITY_POST_D1 = {"kind", "context", "audit_task", "model_id", "base_model_id", "stage", "variation", "code",
                                "plan_id", "spec_sha256", "spec_document", "spec_document_sha256", "data_version_sha256",
                                "ledger_file", "ledger_sha256", "metrics", "started_at"}
FAZ5_SENSITIVITY_SOURCE = ROOT / "docs" / "fable_faz5_audit" / "ekler" / "sensitivity_runs.jsonl"
# Faz 7 bağımsız denetiminin (docs/fable_faz7_audit/) dört duyarlılık koşusu: temel model `ceiling_hazard_v1_pooled` (Faz 7 sözlüğü,
# SPEC_DEVIATIONS J21), satırlar denetimin `ekler/sensitivity_runs.jsonl` içeriğiyle aynen (Faz 5 kalıbı; alan kümesi denetiminki).
# `note` "model değil; dondurulmaz" der; hiçbir tabloya, skora ve varyant sayacına girmezler (dondurma görevi K7).
REQUIRED_SENSITIVITY_FAZ7 = {"kind", "context", "audit_task", "model_id", "base_model_id", "variation", "note", "code", "plan_id",
                             "spec_sha256", "spec_document", "spec_document_sha256", "decisions_document_sha256",
                             "data_version_sha256", "training_table_sha256", "ledger_file", "ledger_sha256", "metrics", "started_at"}
FAZ7_SENSITIVITY_SOURCE = ROOT / "docs" / "fable_faz7_audit" / "ekler" / "sensitivity_runs.jsonl"
# Faz 7C bağımsız denetiminin (docs/fable_faz7c_audit/) beş duyarlılık koşusu (K6 seçenek B × 3, J10 dışlaması kapalı, aralık üreteci):
# temel modeller Faz 7C sözlüğünden, satırlar denetimin `ekler/sensitivity_runs.jsonl` içeriğiyle aynen (Faz 7 kalıbı; alan kümesi
# denetiminki; dondurma görevi K5). `note` "model değil" der; hiçbir tabloya, skora ve varyant sayacına girmezler.
REQUIRED_SENSITIVITY_FAZ7C = {"kind", "context", "audit_task", "model_id", "base_model_id", "variant", "note", "code", "spec_sha256",
                              "spec_document", "spec_document_sha256", "decisions_document_sha256", "data_version_sha256",
                              "training_table_sha256", "ledger_file", "ledger_sha256", "metrics", "started_at"}
FAZ7C_SENSITIVITY_SOURCE = ROOT / "docs" / "fable_faz7c_audit" / "ekler" / "sensitivity_runs.jsonl"
# Faz 7C keşif varyantları (SPEC_C_V0 §8, §10; KARARLAR_C "Çokluk"; SPEC_DEVIATIONS K): `docs/specs_faz7_c/ekler/denenenler.csv`'nin
# her satırı bir `kind: exploration` satırı (2 054; özet satır değil). MODEL DEĞİLDİR: dondurulmaz, INDEX'e girmez; kart varyant
# sayacı bunları kendi veri sürümünde (v2) sayar (CLAUDE.md kural 4).
# Faz 8 (SPEC_BREAK_V0 §7.2; SPEC_DEVIATIONS N17, N19): resmi koşunun üç duyarlılık satırı (`__sens_floor_only`, `__sens_turnover_only`,
# `__sens_with_group_Z`); temel model Faz 8 sözlüğünde (`POST_BREAK_MODEL_SPECS`), aşama POST_BREAK; ledger'ları docs/faz8/backtest/.
# MODEL DEĞİLDİR: dondurulmaz, hiçbir tabloya, skora ve varyant sayacına girmez.
REQUIRED_SENSITIVITY_FAZ8 = {"kind", "context", "model_id", "base_model_id", "variant", "is_model", "note", "stage", "plan_id",
                             "spec_sha256", "spec_document", "spec_document_sha256", "decisions_document_sha256",
                             "data_version_sha256", "ledger_file", "ledger_sha256", "metrics", "started_at", "finished_at",
                             "git_commit", "borsai_source_sha256"}
REQUIRED_EXPLORATION = {"kind", "context", "model_id", "family", "variant_id", "variant", "source", "source_sha256", "source_commit",
                        "data_version_sha256", "spec_document", "spec_document_sha256", "note", "recorded_at"}


def _lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_session_backtests_were_logged(backtest_results, test_log_path, dataset):
    entries = _lines(test_log_path)
    assert len(entries) == len(MODEL_SPECS)
    for e in entries:
        assert REQUIRED <= set(e)
        res = backtest_results[e["model_id"]]
        assert e["ledger_sha256"] == res.log_entry["ledger_sha256"]
        assert e["spec_sha256"] == spec_sha256(MODEL_SPECS[e["model_id"]])
        assert e["data_version_sha256"] == dataset.data_version_sha256


def test_run_backtest_appends_exactly_one_line(dataset, tmp_path):
    log = tmp_path / "log.jsonl"
    log.write_text('{"sentinel": 1}\n', encoding="utf-8")
    bt.run_backtest("base_zero", dataset, log_path=log, context="pytest")
    bt.run_backtest("base_zero", dataset, log_path=log, context="pytest")
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3 and json.loads(lines[0]) == {"sentinel": 1}


def test_official_log_contains_golden_runs():
    entries = _lines(ROOT / "experiments" / "log.jsonl")
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
    frozen = {e["model_id"] for e in index["models"]}
    post_index = ROOT / "models" / "INDEX_POST_D1.json"
    if post_index.exists():
        frozen |= {e["model_id"] for e in json.loads(post_index.read_text(encoding="utf-8"))["models"]}
    for e in entries:
        if e["kind"] == "conditional_eval":
            assert REQUIRED_CONDITIONAL <= set(e) and e["model_id"] is None
            assert all({"run_key", "model_id", "plan_id", "ledger_sha256"} <= set(x) for x in e["evaluated"])
            continue
        if e["kind"] == "sensitivity":
            assert e["model_id"] not in frozen and e["model_id"] not in MODEL_SPECS   # model değil
            assert e["model_id"] not in POST_D1_MODEL_SPECS and e["model_id"] not in FAZ7_MODEL_SPECS
            assert e["model_id"] not in FAZ7C_MODEL_SPECS and e["model_id"] not in POST_BREAK_MODEL_SPECS
            if e.get("base_model_id") in POST_BREAK_MODEL_SPECS:           # Faz 8 (SPEC_DEVIATIONS N19)
                assert REQUIRED_SENSITIVITY_FAZ8 <= set(e) and e["is_model"] is False and "model değil" in e["note"]
                assert e["stage"] == "POST_BREAK" and e["variant"]
            elif e.get("context") == "fable_faz7c_audit_sensitivity":
                assert REQUIRED_SENSITIVITY_FAZ7C <= set(e) and "model değil" in e["note"]
                assert e["base_model_id"] in FAZ7C_MODEL_SPECS
            elif e.get("context") == "fable_faz7_audit_sensitivity":
                assert REQUIRED_SENSITIVITY_FAZ7 <= set(e) and "model değil" in e["note"]
                assert e["base_model_id"] in FAZ7_MODEL_SPECS
            elif e.get("stage") == "POST_D1":
                assert REQUIRED_SENSITIVITY_POST_D1 <= set(e) and "model değil" in e["variation"]["note"]
                assert e["base_model_id"] in POST_D1_MODEL_SPECS
            else:
                assert REQUIRED_SENSITIVITY <= set(e) and e["is_model"] is False
                assert e["base_model_id"] in MODEL_SPECS and e["variant"]
            assert sha256_file(ROOT / e["ledger_file"]) == e["ledger_sha256"]
            continue
        if e["kind"] == "exploration":
            from borsai.specs import FAZ7C_EXPLORATION

            assert REQUIRED_EXPLORATION <= set(e) and e["model_id"] is None and "model değil" in e["note"]
            assert (e["source"], e["source_sha256"], e["data_version_sha256"]) == (
                FAZ7C_EXPLORATION["path"], FAZ7C_EXPLORATION["sha256"], FAZ7C_EXPLORATION["data_version_sha256"])
            continue
        assert REQUIRED <= set(e) and e["kind"] == "backtest"
    manifest = json.loads((bt.GOLDEN_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    for model_id, info in manifest["models"].items():
        logged = {e["ledger_sha256"] for e in entries if e["model_id"] == model_id}
        assert info["ledger_sha256"] in logged, model_id


def test_sensitivity_lines_are_logged_but_enter_no_table():
    """Duyarlılık satırları kural 4 gereği günlüktedir ama model değildir: hiçbir belgeye, skora ya da
    varyant sayacına girmezler (sayaç `kind: backtest` ve — Faz 7C'den beri — `kind: exploration` satırlarını sayar, SPEC_DEVIATIONS
    E16, K; duyarlılık satırlarını saymaz)."""
    from borsai import scoring as sc

    entries = _lines(ROOT / "experiments" / "log.jsonl")
    sens = [e for e in entries if e["kind"] == "sensitivity"]
    # Faz 8 (SPEC_DEVIATIONS N19; proje sahibi kararı 2026-10-01): resmi koşunun üç duyarlılık satırı (commit A'da 0, B'de 3); temel
    # model Faz 8 sözlüğünde. Diğer 16 satır ve bağlamları aynen.
    faz8 = fs8.faz8_sensitivity_lines()
    assert len(faz8) in (0, 3) and all(e in sens for e in faz8)
    assert len(sens) == 16 + len(faz8)
    assert {e["context"] for e in sens if e not in faz8} == {"faz4_fable_sensitivity", "fable_faz5_audit_sensitivity",
                                                              "fable_faz7_audit_sensitivity", "fable_faz7c_audit_sensitivity"}
    faz5 = [e for e in sens if e["context"] == "fable_faz5_audit_sensitivity"]
    assert faz5 == _lines(FAZ5_SENSITIVITY_SOURCE) and len(faz5) == 2
    faz7 = [e for e in sens if e["context"] == "fable_faz7_audit_sensitivity"]
    assert faz7 == _lines(FAZ7_SENSITIVITY_SOURCE) and len(faz7) == 4
    faz7c = [e for e in sens if e["context"] == "fable_faz7c_audit_sensitivity"]
    assert faz7c == _lines(FAZ7C_SENSITIVITY_SOURCE) and len(faz7c) == 5
    ids = {e["model_id"] for e in sens}
    scores = json.loads((ROOT / "scores" / "scores.json").read_text(encoding="utf-8"))
    assert not ids & {m["model_id"] for m in scores["models"]}
    assert not ids & {x["model_id"] for x in scores["retro_info"]}
    for doc in ("docs/MODELS.md", "docs/SCORES.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        for mid in ids:
            assert mid not in text, (doc, mid)
    dv = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"][0]["data_version_sha256"]
    n_backtest = len({(e["model_id"], e["spec_sha256"]) for e in entries
                      if e["kind"] == "backtest" and e["data_version_sha256"] == dv})
    n_exploration = len({e["variant_id"] for e in entries if e["kind"] == "exploration" and e["data_version_sha256"] == dv})
    assert sc._n_variants_same_data(dv, "v1_5_h99")[0] == n_backtest + n_exploration

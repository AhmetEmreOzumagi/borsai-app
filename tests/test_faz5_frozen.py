"""Faz 5 dondurma (BORSAI_FAZ5_FREEZE_20260924): `models/post_d1_hazard_v0.json` ve `models/INDEX_POST_D1.json`.

Donmuş dosya, bağımsız yeniden üretimden (Fable FREEZE_OK, `docs/fable_faz5_audit/`) sonra temiz ağaçta
`python -m borsai.freeze --models post_d1_hazard_v0` ile yazıldı ve altın nihai fit önizlemesinin aynısıdır
(`created_at`, `code_version`, `runtime` dışında `==`). POST_D1 modelleri ayrı dizindedir (proje sahibi kararı 4):
`models/INDEX.json` ve listeleme öncesi 19 model dosyası dondurmadan önceki haliyle bayt-eşittir."""
from __future__ import annotations

import json
import subprocess

import pytest

from borsai import freeze as fz
from borsai import post_d1 as pd
from borsai import predict_hazard as ph
from borsai import predict_path as pth
from borsai import predict_post_d1 as pd1
from borsai import report_faz5 as r5
from borsai.provenance import ROOT, sha256_bytes, sha256_file
from borsai.specs import POST_D1_MODEL_SPECS, SPEC_DOCUMENTS_FAZ5, spec_sha256

import faz7_support as fs7
import faz8_support as fs8

MODEL = "post_d1_hazard_v0"
FROZEN = ROOT / "models" / f"{MODEL}.json"
PRE_FREEZE_COMMIT = "72a000f48917946fc7a84da74767dca734f19f8a"   # INDEX.json'un ve 19 model dosyasının son hali
VOLATILE = ("created_at", "code_version", "runtime")
SPEC = POST_D1_MODEL_SPECS[MODEL]


def _git_bytes(rev: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


@pytest.fixture(scope="module")
def frozen():
    return json.loads(FROZEN.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def parent():
    return pd.load_frozen(SPEC["parent"])[0]


@pytest.fixture(scope="module")
def golden():
    _, manifest, preview = r5.load_faz5()
    return manifest, preview


def test_frozen_equals_final_fit_preview(frozen, golden):
    manifest, preview = golden
    strip = lambda d: {k: v for k, v in d.items() if k not in VOLATILE}   # noqa: E731
    assert set(frozen) == set(preview) and strip(frozen) == strip(preview)
    assert frozen["lambda"] == 30.0 and frozen["stage"] == "POST_D1" and frozen["model_id"] == MODEL
    # temiz ağaçta, altın koşunun kaynağıyla (7ce0593'ten beri borsai/ değişmedi)
    assert frozen["code_version"]["borsai_dirty"] is False
    assert frozen["code_version"]["borsai_source_sha256"] == preview["code_version"]["borsai_source_sha256"] \
        == manifest["borsai_source_sha256"]


def test_frozen_pins(frozen):
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
    by_id = {e["model_id"]: e for e in index["models"]}
    for key in ("parent", "path_secondary"):
        ref = SPEC[key]
        assert frozen[key]["model_id"] == ref["model_id"] and frozen[key]["file"] == ref["file"]
        assert frozen[key]["sha256"] == ref["sha256"] == by_id[ref["model_id"]]["sha256"] \
            == sha256_file(ROOT / "models" / ref["file"])
    doc = SPEC_DOCUMENTS_FAZ5["SPEC_POST_D1_V0"]
    assert frozen["spec_document"] == {"path": doc["path"], "sha256": doc["sha256"]}
    assert doc["sha256"] == sha256_file(ROOT / doc["path"]) and doc["sha256"].startswith("a5b4675d")
    assert frozen["spec_sha256"] == spec_sha256(dict(SPEC)) and frozen["spec"] == json.loads(json.dumps(SPEC))
    parent_json = json.loads((ROOT / "models" / SPEC["parent"]["file"]).read_text(encoding="utf-8"))
    assert frozen["parent"]["gamma"] == parent_json["gamma"] and frozen["parent"]["beta"] == parent_json["beta"]
    tr = frozen["training"]
    assert (tr["n"], tr["n_delta_ipo"], tr["n_pp_rows"], tr["n_events"], tr["n_survivals"]) == (81, 81, 409, 67, 342)
    assert tr["cutoff_date"] <= pd.OUTCOME_CUTOFF and tr["data_version_sha256"] == SPEC["training"]["data_version_sha256"]


def test_post_d1_index_single_entry(frozen):
    raw = fz.INDEX_POST_D1_PATH.read_bytes()
    idx = json.loads(raw)
    assert set(idx) == {"schema_version", "models"} and idx["schema_version"] == fz.INDEX_SCHEMA == "borsai.model_index/1"
    assert len(idx["models"]) == 1
    entry = idx["models"][0]
    sha = sha256_bytes(FROZEN.read_bytes())
    assert entry == {**fz.index_entry(frozen, FROZEN.name, sha), "stage": "POST_D1",
                     "parent_model_id": "ceiling_hazard_v0", "parent_sha256": SPEC["parent"]["sha256"]}
    assert entry["file"] == f"{MODEL}.json" and entry["sha256"] == sha and entry["status"] == "FROZEN"
    assert fz.model_kind(frozen) == "post_d1"
    assert fz.run_model(frozen, {})["status"] == fz.STATUS_ERROR   # listeleme öncesi kayıtta çalışmaz


@pytest.mark.requires_git_history
def test_pre_listing_index_and_models_byte_identical():
    """INDEX.json 72a000f'deki haliyle bayt-eşit; Faz 7 dondurmasından sonra (SPEC_DEVIATIONS J23) ilk 19 girişi metin olarak
    aynı ve sonunda yalnız dört v1 girişi (Faz 7C dondurmasından sonra ardından dört (C) girişi; K19). 19 model dosyası bayt-eşit;
    POST_D1 modeli INDEX.json'da yok."""
    index_raw = (ROOT / "models" / "INDEX.json").read_bytes()
    faz7 = fs7.frozen_tail_ids()
    if not faz7:
        assert index_raw == _git_bytes(PRE_FREEZE_COMMIT, "models/INDEX.json")
    all_entries = json.loads(index_raw)["models"]
    entries = all_entries[:19]
    assert entries == json.loads(_git_bytes(PRE_FREEZE_COMMIT, "models/INDEX.json"))["models"]
    assert [e["model_id"] for e in all_entries[19:]] == faz7 and MODEL not in {e["model_id"] for e in all_entries}
    for e in entries:
        assert (ROOT / "models" / e["file"]).read_bytes() == _git_bytes(PRE_FREEZE_COMMIT, f"models/{e['file']}"), e["file"]
    on_disk = sorted(p.name for p in (ROOT / "models").iterdir() if p.is_file() and p.suffix == ".json")
    assert on_disk == sorted(["INDEX.json", fz.INDEX_POST_D1_NAME, FROZEN.name] + [e["file"] for e in all_entries]
                             + fs8.frozen_post_break_files())             # Faz 8: ayrı dizin + iki dosya (K-PIN, N25)


def test_frozen_numpy_final_fit_vs_stdlib_81(dataset, frozen, parent):
    """§11-10 donmuş dosyayla: numpy nihai model (δ, λ dosyadan; D1 ön işlemesi veriden yeniden) ile stdlib
    `predict_post_d1` 81 eğitim arzında |Δ| ≤ 1e-12; h_1 ana modelle bit-eşit."""
    numpy_side = pd.final_predictions(dataset, frozen)
    d1 = pd.h99_d1(dataset)
    rows = pd.final_training_rows(dataset)
    assert len(rows) == 81 == len(numpy_side)
    worst = 0.0
    for r in rows:
        inputs = pd.model_inputs_of(r)
        a = numpy_side[r.ticker]
        b = pd1.predict_post_d1(frozen, parent, inputs, d1[r.ticker].row.block())
        assert b["refused"] is None and b["not_applicable"] is None
        for key in ("hazard", "S"):
            worst = max(worst, max(abs(x - y) for x, y in zip(a[key], b[key])))
        for key in ("S_cond", "P_L_cond"):
            worst = max(worst, max(abs(a["conditional_j1"][key][k] - b["conditional_j1"][key][k]) for k in a["conditional_j1"][key]))
        assert a["hazard"][0] == b["hazard"][0] == ph.predict(parent, inputs)["hazard"][0]
    assert worst <= 1e-12


def test_frozen_inf_endpoint_bit_equal(dataset, frozen, parent):
    """Donmuş dosyanın ofseti ve D1 ön işlemesiyle δ = 0 (λ = INF ucu): hazard, S ve koşullu ağırlıklar
    `ceiling_hazard_v0`'a bit-eşit (SPEC_POST_D1_V0 §3.4, §5 (d)); kilitli ve kilitsiz D1 bloklarında."""
    params = {**frozen, "delta": {c: 0.0 for c in frozen["delta"]}, "lambda": "INF"}
    d1 = pd.h99_d1(dataset)
    n = 0
    for r in pd.final_training_rows(dataset):
        inputs = pd.model_inputs_of(r)
        base = ph.predict(parent, inputs)
        real = d1[r.ticker].row.block()
        unlocked = json.loads(json.dumps(real))
        unlocked["fields_raw"]["low"] = "0.01"                        # d1_lock = 0 varyantı
        for block in (real, unlocked):
            out = pd1.predict_post_d1(params, parent, inputs, block)
            assert out["refused"] is None and out["not_applicable"] is None
            assert out["hazard"] == base["hazard"] and out["S"] == base["S"]
            assert pth.conditional_weights(out["S"], 1) == pth.conditional_weights(base["S"], 1)
            n += 1
    assert n == 2 * 81


def test_models_md_faz5_frozen_note(frozen):
    """MODELS.md Faz 5 bölümünün sonu: bağımsız yeniden üretim, donmuş sha ve k = 10 dipnotu (AUDIT §5-3); öncesi aynen."""
    text = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
    section = text.split("## Faz 5: D1 sonrası güncelleme")[1]
    before, note = section.split("### Faz 5 koşusu ve deney günlüğü")[1].split("### Dondurma")
    assert "Model **dondurulmadı**" in section and "### Nihai fit önizlemesi (dondurulmadı)" in section   # backtest anının kaydı
    assert f"`{MODEL}` | post_d1 | 87 |" in before
    assert "maks |Δ| = 1.5e-11" in note and "`docs/fable_faz5_audit/`" in note and "**FREEZE_OK**" in note
    assert f"sha256 `{sha256_file(FROZEN)}`" in note and "`models/INDEX_POST_D1.json`" in note
    assert note.rstrip().endswith(r5.K10_FOOTNOTE) and "gün-grubu etkileşimi yeni model_id'dir" in r5.K10_FOOTNOTE
    assert r5.frozen_entry()["sha256"] == sha256_file(FROZEN)

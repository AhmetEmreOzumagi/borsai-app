"""Faz 7C dondurması (BORSAI_FAZ7C_FREEZE_20260928): `fall_d10_v0_h99`, `_pooled`, `_addsale`, `_pooled@ZERO` models/'de ve
models/INDEX.json'un sonunda (SPEC_C_V0 §2.3, §7.1-2, §8, §9, §11-9; SPEC_DEVIATIONS K16–K23). Donmuş dosyalar ↔ nihai fit
önizlemeleri, INDEX şeması ve bayt-eşitlikler, stdlib tahmin ↔ sklearn nihai fit, `@ZERO` sabiti (Fraction), ret yolları, canlı kayıt
yolu, MODELS.md notu."""
from __future__ import annotations

import copy
import json
import subprocess
from datetime import datetime, timezone
from fractions import Fraction

import numpy as np
import pytest

from borsai import backtest as bt
from borsai import freeze as fz
from borsai import predict_fall as pf
from borsai import registry as reg
from borsai import report_faz7c as r7c
from borsai import tufe
from borsai.data import additional_sale_shares
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes, sha256_file
from borsai.specs import FAZ7_MODEL_IDS, FAZ7C_MODEL_IDS, FAZ7C_MODEL_SPECS, SPEC_DOCUMENTS_FAZ7C, spec_sha256

import faz7_support as fs7

H99, POOLED, ADDSALE, ZERO_ROW = FAZ7C_MODEL_IDS
VOLATILE = ("created_at", "code_version", "runtime")
PRE_FREEZE_COMMIT = "80670cb"          # dondurma görevinin başladığı HEAD (denetim commit'i); models/ Faz 7C öncesi (23 giriş)
SPEC_C_V0_SHA256 = "d75c17cfec09712174c86ac8619b5d51fb5681fc161f48455423b84d9e8db5ac"
NOW = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def _git_bytes(rev: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


@pytest.fixture(scope="module")
def frozen():
    return {m: json.loads((ROOT / "models" / f"{m}.json").read_text(encoding="utf-8")) for m in FAZ7C_MODEL_IDS}


@pytest.fixture(scope="module")
def previews():
    return {m: json.loads((bt.GOLDEN_FAZ7C_DIR / bt.final_preview_filename(m)).read_text(encoding="utf-8")) for m in FAZ7C_MODEL_IDS}


def _strip(d):
    return {k: v for k, v in json.loads(pretty_json_bytes(dict(d))).items() if k not in VOLATILE}


# ---------------------------------------------------------------- dosyalar, INDEX, bayt-eşitlikler

@pytest.mark.requires_git_history
def test_frozen_files_equal_previews_and_clean_code(frozen, previews):
    """Donmuş JSON ↔ nihai fit önizlemesi (`created_at`, `code_version`, `runtime` dışında `==`); dondurma temiz ağaçta
    (`borsai_dirty` false) ve JSON'un borsai kaynak sha'sı adlandırdığı commit'in (kod commit'i K) borsai/ ağacı; şartname belge sha'sı
    SPEC_C_V0.md'nin sha'sı (AUDIT F2: `spec.spec_document.sha256`)."""
    for m in FAZ7C_MODEL_IDS:
        f = frozen[m]
        assert _strip(f) == _strip(previews[m]), m
        cv = f["code_version"]
        assert cv["borsai_dirty"] is False and cv["borsai_source_sha256"] == fs7.borsai_tree_sha256_at(cv["git_commit"]), m
        assert f["model_id"] == m and f["spec_sha256"] == spec_sha256(FAZ7C_MODEL_SPECS[m]) and f["family"] == pf.FAMILY_FALL
        for key, doc in (("spec_document", "SPEC_C_V0"), ("decisions_document", "KARARLAR_C")):
            ref = f["spec"][key]
            assert ref == SPEC_DOCUMENTS_FAZ7C[doc] and ref["sha256"] == sha256_file(ROOT / ref["path"]), (m, key)
        assert f["spec"]["spec_document"]["sha256"] == SPEC_C_V0_SHA256
        assert set(f["runtime"]) == set(previews[m]["runtime"])


@pytest.mark.requires_git_history
def test_index_27_entries_first_23_unchanged_and_post_d1_index_unchanged(frozen):
    """INDEX: şema, 27 giriş; yeni dosya eski INDEX metninin son girişine kadarki önekiyle başlar (ilk 23 giriş metin olarak aynı);
    son dört FAZ7C_MODEL_IDS sırasıyla ve `freeze.index_entry` alanlarıyla; dosya sha'ları. 23 eski model dosyası,
    post_d1_hazard_v0.json ve INDEX_POST_D1.json dondurma öncesiyle bayt-eşit."""
    raw = (ROOT / "models" / "INDEX.json").read_bytes()
    old = _git_bytes(PRE_FREEZE_COMMIT, "models/INDEX.json")
    cut = old.rindex(b"\n    }") + len(b"\n    }")
    assert raw.startswith(old[:cut]) and raw[cut:cut + 2] == b",\n"
    index = json.loads(raw)
    assert index["schema_version"] == fz.INDEX_SCHEMA and len(index["models"]) == 27
    assert index["models"][:23] == json.loads(old)["models"]
    assert fs7.frozen_tail_ids() == list(FAZ7_MODEL_IDS) + list(FAZ7C_MODEL_IDS) and fs7.frozen_faz7c_ids() == list(FAZ7C_MODEL_IDS)
    for e in index["models"][23:]:
        data = (ROOT / "models" / e["file"]).read_bytes()
        assert e["file"] == f"{e['model_id']}.json" and e["sha256"] == sha256_bytes(data)
        assert e == fz.index_entry(frozen[e["model_id"]], e["file"], e["sha256"]) and e["status"] == "FROZEN"
    for e in index["models"][:23]:
        assert (ROOT / "models" / e["file"]).read_bytes() == _git_bytes(PRE_FREEZE_COMMIT, f"models/{e['file']}"), e["file"]
    for name in ("post_d1_hazard_v0.json", "INDEX_POST_D1.json"):
        assert (ROOT / "models" / name).read_bytes() == _git_bytes(PRE_FREEZE_COMMIT, f"models/{name}"), name
    assert not any(e["model_id"] in FAZ7C_MODEL_SPECS for e in json.loads((ROOT / "models" / "INDEX_POST_D1.json").read_text())["models"])


@pytest.mark.requires_git_history
def test_freeze_commit_holds_only_model_files_and_index():
    """F1: dört model dosyası + INDEX.json, başka yol yok. JSON'ların adlandırdığı commit (kod commit'i K) F1'in atasıdır ve
    K ile F1 arasında borsai/ değişmedi (donmuş JSON'un kodu K'nın kodudur); K denetim commit'inin torunudur."""
    f1 = _git("log", "--diff-filter=A", "--format=%H", "--", f"models/{H99}.json").split()[-1]
    files = _git("show", "--name-only", "--format=", f1).split()
    assert sorted(files) == sorted(["models/INDEX.json", *(f"models/{m}.json" for m in FAZ7C_MODEL_IDS)])
    for m in FAZ7C_MODEL_IDS:
        k = json.loads(_git_bytes(f1, f"models/{m}.json"))["code_version"]["git_commit"]
        assert subprocess.run(["git", "merge-base", "--is-ancestor", k, f1], cwd=ROOT).returncode == 0
        assert subprocess.run(["git", "merge-base", "--is-ancestor", PRE_FREEZE_COMMIT, k], cwd=ROOT).returncode == 0
        assert _git("diff", "--name-only", k, f1, "--", "borsai") == ""


def test_refreeze_is_refused():
    """Dondurulmuş dosyanın ya da INDEX kaydının üzerine yazılmaz (kural 1): (C) kimliği ikinci kez dondurulamaz."""
    from borsai.data import load_dataset

    for m in FAZ7C_MODEL_IDS:
        with pytest.raises(fz.FreezeError, match="zaten dondurulmuş"):
            fz.freeze([m], load_dataset())


# ---------------------------------------------------------------- tahmin: stdlib ↔ sklearn, @ZERO, ret yolları

@pytest.mark.parametrize("model_id", list(FAZ7C_MODEL_IDS))
def test_frozen_json_stdlib_predict_matches_final_fit(model_id, frozen):
    """§11-9: donmuş JSON'la stdlib `predict_fall.predict` ↔ nihai fit (sklearn `predict_proba`; `@ZERO`'da sabit), modelin bütün
    eğitim arzlarında ve iki ufukta |Δ| ≤ 1e-12; h99/pooled `tufe_index` ile; ret yok; `freeze.run_model` aynı çıktıyı verir."""
    f = frozen[model_id]
    params, fits = bt.final_fit_fall(model_id)
    assert _strip(params) == _strip(f)
    spec = FAZ7C_MODEL_SPECS[model_id]
    ds = bt.fall_dataset(model_id)
    add = additional_sale_shares(ds)
    rows = bt.fall_training_rows(spec, ds, add, check=True)
    raw, info = bt.fall_raw_features(spec, rows, add)
    worst, n = 0.0, 0
    for r in rows:
        inputs = {**r.inputs, "total_demand_filter_status": r.total_demand_filter_status, pf.ADDITIONAL_SALE_FIELD: add[r.ticker]}
        if info:
            inputs["tufe_index"] = info[r.ticker]["index"]
        out = pf.predict(f, inputs)
        assert out["refused"] is None, out["refused"]
        for h in pf.FALL_HORIZONS:
            hf = fits[h]
            if hf.final is None or hf.logit.estimator is None:
                ref = hf.logit.constant
            else:
                z = hf.final.transform(raw[r.ticker], r.total_demand_filter_status)["z"]
                ref = float(hf.logit.estimator.predict_proba(np.array([[z[c] for c in hf.logit.columns]]))[0][1])
            worst = max(worst, abs(out[h]["p_up"] - ref))
        if info:
            assert out["tufe_index_used"] == info[r.ticker]["index"]
        n += 1
    assert n == spec["training"]["n"] == f["training"]["n"] and worst <= 1e-12
    assert fz.run_model(f, inputs)["output"] == out


def test_zero_rule_row_is_training_rate_fraction(frozen):
    """`@ZERO` sabit (kural satırı): D10 = 1 − 39/161, D5 = 1 − 29/161 (Fraction ile bit-eşit); girdi istemez; özellik yok;
    `pooled`'ın eğitim kümesiyle aynı arzlar."""
    z = frozen[ZERO_ROW]
    assert z["features"] == [] and z["preprocessing"] is None and "deflator" not in z
    assert z["horizons"]["D10"]["p_up"] == {**z["horizons"]["D10"]["p_up"], "kind": "constant", "C": "ZERO"}
    assert z["horizons"]["D10"]["p_up"]["value"] == float(Fraction(1) - Fraction(39, 161))
    assert z["horizons"]["D5"]["p_up"]["value"] == float(Fraction(1) - Fraction(29, 161))
    assert z["training"]["tickers"] == frozen[POOLED]["training"]["tickers"]
    out = pf.predict(z, {})
    assert out["refused"] is None and (out["D10"]["p_up"], out["D5"]["p_up"]) == (z["horizons"]["D10"]["p_up"]["value"],
                                                                               z["horizons"]["D5"]["p_up"]["value"])


def test_refusal_paths_on_frozen_json(frozen):
    """§9 ret yolları donmuş JSON'larla: f3 boş → h99/pooled F3_MISSING (addsale ve @ZERO tahmin verir); ek satış boş / DATA_NOT_FOUND
    → üç aday ADDITIONAL_SALE_MISSING (0 varsayılmaz, C4); negatif → INPUT_NEGATIVE; TÜFE eksik → TUFE_MISSING, PIT değil →
    TUFE_NOT_PIT, önek pini tutmuyor → TUFE_FILE_MISMATCH (h99, pooled); filtre uyuşmazlığı: nihai fit modu açık olsaydı
    (FILTERED/UNFILTERED) zıt açık girdi F3_FILTER_STATUS_CONFLICT (gerçek mod NOT_SPECIFIED: açık girdi ret değil)."""
    base = reg.model_inputs(reg.load_inputs(reg.INPUTS_DIR / "CITAS.json")[0])
    t = tufe.index_for("2026-08-18", tufe.load())
    ok = {**base, "tufe_index": t["index"]}

    def code(m, inputs, params=None):
        out = pf.predict(params or frozen[m], inputs)
        return None if out["refused"] is None else out["refused"]["code"]

    assert all(code(m, ok) is None for m in FAZ7C_MODEL_IDS)
    for m in (H99, POOLED):
        assert code(m, {**ok, "total_demand_multiple": None}) == "F3_MISSING"
        assert code(m, dict(base)) == "TUFE_MISSING"
        for c in ("TUFE_NOT_PIT", "TUFE_FILE_MISMATCH", "TUFE_MISSING"):
            assert code(m, {**base, "tufe_refusal": c}) == c
        assert frozen[m]["preprocessing"]["f3_filter_mode"] == "NOT_SPECIFIED"
        assert all(code(m, {**ok, "total_demand_filter_status": s}) is None for s in ("FILTERED", "UNFILTERED"))
        explicit = copy.deepcopy(frozen[m])
        explicit["preprocessing"]["f3_filter_mode"] = "UNFILTERED"
        assert code(m, {**ok, "total_demand_filter_status": "FILTERED"}, explicit) == "F3_FILTER_STATUS_CONFLICT"
        assert code(m, {**ok, "total_demand_filter_status": "UNFILTERED"}, explicit) is None
    assert code(ADDSALE, {**ok, "total_demand_multiple": None}) is None and code(ADDSALE, {pf.ADDITIONAL_SALE_FIELD: "0"}) is None
    for m in (H99, POOLED, ADDSALE):
        for v in (None, "", "DATA_NOT_FOUND"):
            assert code(m, {**ok, pf.ADDITIONAL_SALE_FIELD: v}) == pf.ADDITIONAL_SALE_MISSING, (m, v)
        assert code(m, {**ok, pf.ADDITIONAL_SALE_FIELD: "-1"}) == "INPUT_NEGATIVE"
    assert code(ZERO_ROW, {}) is None and code(ZERO_ROW, {pf.ADDITIONAL_SALE_FIELD: None, "total_demand_multiple": None}) is None


@pytest.mark.requires_raw_sources
def test_live_record_with_the_real_index_carries_four_fall_cells():
    """Dondurmadan sonraki canlı kayıt (kural 1) INDEX'teki 27 modelin hepsini içerir; (C) hücreleri sonda, `fall` türü, PREDICTED;
    `tufe` bloğu h99 ve pooled'ı da pinler; f3'süz girdide h99 ve pooled F3_MISSING (K16), addsale ve @ZERO tahmin verir."""
    rec = fz.build_record(reg.INPUTS_DIR / "CITAS.json", now=NOW)
    cells = {c["model_id"]: c for c in rec["models"]}
    assert rec["summary"]["n_models"] == 27 and list(cells)[19:23] == list(FAZ7_MODEL_IDS) and list(cells)[23:] == list(FAZ7C_MODEL_IDS)
    assert {H99, POOLED} <= set(rec["tufe"]["pins"]) and rec["tufe"]["refusal"] is None
    for m in FAZ7C_MODEL_IDS:
        c = cells[m]
        assert c["kind"] == "fall" and c["status"] == fz.STATUS_PREDICTED and c["params_sha256"] == sha256_file(ROOT / "models" / f"{m}.json")
        assert c["output"] == pf.predict(json.loads((ROOT / "models" / f"{m}.json").read_text(encoding="utf-8")), rec["model_inputs"])
    veyas = {c["model_id"]: c for c in fz.build_record(reg.INPUTS_DIR / "VEYAS.json", now=NOW)["models"]}
    assert {m for m in FAZ7C_MODEL_IDS if veyas[m]["status"] == fz.STATUS_REFUSED} == {H99, POOLED}
    assert {veyas[m]["refusal"]["code"] for m in (H99, POOLED)} == {"F3_MISSING"}
    assert {H99, POOLED} <= set(reg.F3_MODELS) and not {ADDSALE, ZERO_ROW} & reg.F3_MODELS


# ---------------------------------------------------------------- MODELS.md dondurma notu

def test_models_md_freeze_note():
    """Faz 7C bölümünün sonunda "### Dondurma": tarih ve donmuş dosya sha'ları, bağımsız yeniden üretim (2026-09-27, maks |Δ| = 0,
    `docs/fable_faz7c_audit/`), "kasa: bekliyor (tavan serisi v1 ile birlikte tek seferde açılır)", "canlı n: dondurma commit'inden
    sonra listelenen arzlarla başlar"; "Kayıtlı modeller" tablosunda dört (C) satırı (P(kapanış > arz); K22). Faz 7 bölümü etkilenmez."""
    text = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
    section = text.split("## Faz 7C: düşen arz modeli v0")[1].split("## Faz 7: tavan serisi v1")[0]
    note = section.split("### Dondurma")[1]
    assert section.count("### Dondurma") == 1 and "henüz dondurulmadı" in section.split("### Dondurma")[0]
    for e in r7c.frozen_entries():
        assert f"| `{e['model_id']}` | `models/{e['file']}` | `{e['sha256']}` | {e['frozen_at'][:10]} |" in note
    assert [e["model_id"] for e in r7c.frozen_entries()] == list(FAZ7C_MODEL_IDS)
    assert "2026-09-27" in note and "maks |Δ| = 0" in note and "docs/fable_faz7c_audit/" in note and "FREEZE_OK" in note
    assert "kasa: bekliyor (tavan serisi v1 ile birlikte tek seferde açılır)" in note
    assert "canlı n: dondurma commit'inden sonra listelenen arzlarla başlar" in note
    assert SPEC_C_V0_SHA256[:12] in note
    registered = text.split("## Kayıtlı modeller")[1].split("\n## ")[0]
    for m in FAZ7C_MODEL_IDS:
        assert f"| `{m}` |" in registered and "P(kapanış > arz)" in registered.split(f"| `{m}` |")[1].split("\n")[0]
    faz7 = text.split("## Faz 7: tavan serisi v1")[1].split("## Faz 5: D1 sonrası")[0]
    assert faz7.count("### Dondurma") == 1 and "## Faz 7C" not in faz7

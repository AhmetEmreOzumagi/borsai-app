"""Faz 7 dondurması (BORSAI_FAZ7_FREEZE_20260927): `ceiling_hazard_v1_clip`, `_real`, `_pooled`, `_pooled@INF` models/'de ve
models/INDEX.json'un sonunda (SPEC_HAZARD_V1 §7.1-2, §8, §11-11; SPEC_DEVIATIONS J23–J31). Donmuş dosyalar ↔ nihai fit önizlemeleri,
INDEX şeması ve bayt-eşitlikler, stdlib tahmin ↔ numpy nihai fit, @INF, rejim ve TÜFE yolları, canlı kayıt yolu, MODELS.md notu."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone

import pytest

from borsai import backtest as bt
from borsai import freeze as fz
from borsai import predict_hazard as ph
from borsai import registry as reg
from borsai import report_faz7 as r7
from borsai import tufe
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes, sha256_file
from borsai.specs import FAZ7_MODEL_IDS, FAZ7_MODEL_SPECS, SPEC_DOCUMENTS_FAZ7, spec_sha256

import faz7_support as fs7

CLIP, REAL, POOLED, POOLED_INF = FAZ7_MODEL_IDS
VOLATILE = ("created_at", "code_version", "runtime")
PRE_FREEZE_COMMIT = "eda9732"          # dondurma görevinin başladığı HEAD (denetim commit'i); models/ Faz 7 öncesi
NOW = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def _git_bytes(rev: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


@pytest.fixture(scope="module")
def frozen():
    return {m: json.loads((ROOT / "models" / f"{m}.json").read_text(encoding="utf-8")) for m in FAZ7_MODEL_IDS}


@pytest.fixture(scope="module")
def previews():
    return {m: json.loads((bt.GOLDEN_FAZ7_DIR / bt.final_preview_filename(m)).read_text(encoding="utf-8")) for m in FAZ7_MODEL_IDS}


@pytest.fixture(scope="module")
def fits():
    return {m: bt.final_fit_v1(m) for m in FAZ7_MODEL_IDS}


def _strip(d):
    return {k: v for k, v in json.loads(pretty_json_bytes(dict(d))).items() if k not in VOLATILE}


# ---------------------------------------------------------------- dosyalar, INDEX, bayt-eşitlikler

@pytest.mark.requires_git_history
def test_frozen_files_equal_previews_and_clean_code(frozen, previews):
    """Donmuş JSON ↔ nihai fit önizlemesi (`created_at`, `code_version`, `runtime` dışında `==`); dondurma temiz ağaçta
    (`borsai_dirty` false) ve JSON'un borsai kaynak sha'sı adlandırdığı commit'in (kod commit'i K) borsai/ ağacı."""
    for m in FAZ7_MODEL_IDS:
        f = frozen[m]
        assert _strip(f) == _strip(previews[m]), m
        cv = f["code_version"]
        assert cv["borsai_dirty"] is False and cv["borsai_source_sha256"] == fs7.borsai_tree_sha256_at(cv["git_commit"]), m
        assert f["model_id"] == m and f["spec_sha256"] == spec_sha256(FAZ7_MODEL_SPECS[m]) and f["family"] == "ceiling_hazard_v1"
        for key, doc in (("spec_document", "SPEC_HAZARD_V1"), ("decisions_document", "KARARLAR_FAZ7")):
            ref = f["spec"][key]
            assert ref == SPEC_DOCUMENTS_FAZ7[doc] and ref["sha256"] == sha256_file(ROOT / ref["path"]), (m, key)
        assert f["spec"]["spec_document"]["sha256"] == "25229cea8f6f235db6562f3dee4992e6b8e22e0cbc23b44b25eeb6d2704d0944"
        assert set(f["runtime"]) == set(previews[m]["runtime"])


@pytest.mark.requires_git_history
def test_index_23_entries_first_19_unchanged_and_post_d1_index_unchanged(frozen):
    """INDEX: şema, 23 giriş (Faz 7C dondurmasından sonra 27: sonraki dört giriş tests/test_faz7c_frozen.py; SPEC_DEVIATIONS K19);
    ilk 19 giriş Faz 7 öncesiyle (a0df5b7) metin olarak aynı; 20.–23. girişler FAZ7_MODEL_IDS sırasıyla ve `freeze.index_entry`
    alanlarıyla; dosya sha'ları. 19 eski model dosyası, post_d1_hazard_v0.json ve INDEX_POST_D1.json dondurma öncesiyle bayt-eşit."""
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
    assert index["schema_version"] == fz.INDEX_SCHEMA and len(index["models"]) == 19 + len(fs7.frozen_tail_ids()) in (23, 27)
    assert fs7.frozen_faz7_ids() == list(FAZ7_MODEL_IDS) and fs7.frozen_tail_ids()[:4] == list(FAZ7_MODEL_IDS)
    for e in index["models"][19:23]:
        raw = (ROOT / "models" / e["file"]).read_bytes()
        assert e["sha256"] == sha256_bytes(raw) and e == fz.index_entry(frozen[e["model_id"]], e["file"], e["sha256"])
    for e in index["models"][:19]:
        assert (ROOT / "models" / e["file"]).read_bytes() == _git_bytes(PRE_FREEZE_COMMIT, f"models/{e['file']}"), e["file"]
    for name in ("post_d1_hazard_v0.json", "INDEX_POST_D1.json"):
        assert (ROOT / "models" / name).read_bytes() == _git_bytes(PRE_FREEZE_COMMIT, f"models/{name}"), name
    assert not any(e["model_id"] in FAZ7_MODEL_SPECS for e in json.loads((ROOT / "models" / "INDEX_POST_D1.json").read_text())["models"])


@pytest.mark.requires_git_history
def test_freeze_commit_holds_only_model_files_and_index():
    """F1: dört model dosyası + INDEX.json, başka yol yok. JSON'ların adlandırdığı commit (kod commit'i K) F1'in atasıdır ve
    K ile F1 arasında borsai/ değişmedi (donmuş JSON'un kodu K'nın kodudur)."""
    f1 = _git("log", "--diff-filter=A", "--format=%H", "--", "models/ceiling_hazard_v1_clip.json").split()[-1]
    files = _git("show", "--name-only", "--format=", f1).split()
    assert sorted(files) == sorted(["models/INDEX.json", *(f"models/{m}.json" for m in FAZ7_MODEL_IDS)])
    for m in FAZ7_MODEL_IDS:
        k = json.loads(_git_bytes(f1, f"models/{m}.json"))["code_version"]["git_commit"]
        assert subprocess.run(["git", "merge-base", "--is-ancestor", k, f1], cwd=ROOT).returncode == 0
        assert _git("diff", "--name-only", k, f1, "--", "borsai") == ""


def test_refreeze_is_refused():
    """Dondurulmuş dosyanın ya da INDEX kaydının üzerine yazılmaz (kural 1): v1 kimliği ikinci kez dondurulamaz."""
    from borsai.data import load_dataset

    for m in FAZ7_MODEL_IDS:
        with pytest.raises(fz.FreezeError, match="zaten dondurulmuş"):
            fz.freeze([m], load_dataset())


# ---------------------------------------------------------------- tahmin: stdlib ↔ numpy, @INF, rejim, TÜFE

@pytest.mark.parametrize("model_id", list(FAZ7_MODEL_IDS))
def test_frozen_json_stdlib_predict_matches_numpy_final_fit(model_id, frozen, fits):
    """§11-11: donmuş JSON'la stdlib `predict_hazard.predict` ↔ numpy nihai fit, modelin bütün eğitim arzlarında |Δ| ≤ 1e-12
    (hazard, S, P_L, P_close); real/pooled `tufe_index` ile, pooled'ın açık küme arzları kohort etiketiyle (r = etiket)."""
    params, res = fits[model_id]
    f = frozen[model_id]
    spec = FAZ7_MODEL_SPECS[model_id]
    ds = bt.v1_dataset(model_id)
    rows = [r for r in ds.rows if r.inputs["total_demand_multiple"] is not None]
    raw, info = bt.v1_raw_features(spec, rows) if spec["features"] else ({r.ticker: {} for r in rows}, {})
    worst, n = 0.0, 0
    for r in rows:
        inputs = dict(r.inputs)
        if "f1r" in spec["features"]:
            inputs["tufe_index"] = info[r.ticker]["index"]
        if "regime" in f and r.cohort != "H99":
            inputs["alloc_regime"] = r.alloc_regime
        out = ph.predict(f, inputs)
        assert out["refused"] is None, r.ticker
        test_r = {bt.REGIME_COLUMN: float(ph.regime_value(r.alloc_regime))} if "regime" in f else None
        num = res.predict(raw[r.ticker], r.total_demand_filter_status, test_r)
        for a, b in (("hazard", "hazards"), ("S", "S"), ("P_L", "P_L"), ("P_close_ceiling", "P_close")):
            worst = max(worst, max(abs(x - y) for x, y in zip(out[a], num[b])))
        if "f1r" in spec["features"]:
            assert out["tufe_index_used"] == info[r.ticker]["index"]
        n += 1
    assert n == spec["training"]["n"] == f["training"]["n"] and worst <= 1e-12


def test_at_inf_rule_row_and_regime_paths(frozen):
    """@INF özelliksiz (β yok, girdi istemez; canlı r = 0); rejim yolu: anahtar yoksa `LIVE_VALUE` r = 0 (= EQUAL_DIST etiketi),
    OOT girdisi PRE/THRESH → r = 1 (S farklı), bilinmeyen etiket RET REGIME_UNKNOWN; v0@INF'ten farklı (havuz + δ)."""
    inf = frozen[POOLED_INF]
    assert inf["features"] == [] and inf["beta"] == {} and inf["lambda"] == "INF" and inf["regime"]["delta"] != 0.0
    v0inf = json.loads((ROOT / "models" / "ceiling_hazard_v0@INF.json").read_text(encoding="utf-8"))
    live = ph.predict(inf, {})
    assert (live["regime_value_used"], live["regime_source"]) == (0, ph.REGIME_SOURCE_LIVE) and live["S"] != ph.predict(v0inf, {})["S"]
    assert ph.predict(inf, {"alloc_regime": "EQUAL_DIST_20230330"})["S"] == live["S"]
    for label in ("PRE_20211111", "THRESH100_20211111"):
        o = ph.predict(inf, {"alloc_regime": label})
        assert (o["regime_value_used"], o["regime_source"]) == (1, ph.REGIME_SOURCE_INPUT) and o["S"] != live["S"]
    assert ph.predict(inf, {"alloc_regime": "BILINMIYOR"})["refused"]["code"] == ph.REFUSED_REGIME_UNKNOWN
    base = dict(json.loads(json.dumps(reg.model_inputs(reg.load_inputs(reg.INPUTS_DIR / "CITAS.json")[0]))))
    t = tufe.index_for("2026-08-18", tufe.load())
    pooled = frozen[POOLED]
    a = ph.predict(pooled, {**base, "tufe_index": t["index"]})
    b = ph.predict(pooled, {**base, "tufe_index": t["index"], "alloc_regime": "PRE_20211111"})
    assert a["regime_value_used"] == 0 and b["regime_value_used"] == 1 and a["S"] != b["S"]


def test_tufe_paths_for_real_and_pooled(frozen):
    """real ve pooled: `tufe_index` ile tahmin (f1r_raw = real_size); yoksa RET TUFE_MISSING; `tufe_refusal` kodu aynen RET;
    clip TÜFE istemez."""
    base = reg.model_inputs(reg.load_inputs(reg.INPUTS_DIR / "CITAS.json")[0])
    t = tufe.index_for("2026-08-18", tufe.load())
    for m in (REAL, POOLED):
        ok = ph.predict(frozen[m], {**base, "tufe_index": t["index"]})
        assert ok["refused"] is None and ok["tufe_index_used"] == t["index"] and ok["f1r_raw"] > 0
        assert ph.predict(frozen[m], dict(base))["refused"]["code"] == ph.REFUSED_TUFE_MISSING
        for code in (ph.REFUSED_TUFE_NOT_PIT, ph.REFUSED_TUFE_FILE_MISMATCH):
            assert ph.predict(frozen[m], {**base, "tufe_refusal": code})["refused"]["code"] == code
    assert ph.predict(frozen[CLIP], dict(base))["refused"] is None


@pytest.mark.requires_raw_sources
def test_live_record_with_the_real_index_carries_four_v1_cells(tmp_path):
    """Dondurmadan sonraki canlı kayıt (kural 1) INDEX'teki bütün modelleri içerir (23; Faz 7C dondurmasından sonra 27, K19);
    `tufe` bloğu, v1 hücreleri PREDICTED, pooled r = 0; f3'süz girdide üç aday F3_MISSING (J24), @INF tahmin verir."""
    rec = fz.build_record(reg.INPUTS_DIR / "CITAS.json", now=NOW)
    cells = {c["model_id"]: c for c in rec["models"]}
    assert rec["summary"]["n_models"] == 19 + len(fs7.frozen_tail_ids()) and list(cells)[19:23] == list(FAZ7_MODEL_IDS)
    assert rec["tufe"]["month"] == "2026-06" and rec["tufe"]["refusal"] is None and "alloc_regime" not in rec["model_inputs"]
    for m in FAZ7_MODEL_IDS:
        assert cells[m]["status"] == fz.STATUS_PREDICTED and cells[m]["params_sha256"] == sha256_file(ROOT / "models" / f"{m}.json")
    assert cells[POOLED]["output"]["regime_value_used"] == 0
    veyas = fz.build_record(reg.INPUTS_DIR / "VEYAS.json", now=NOW)
    ref = {c["model_id"]: c for c in veyas["models"]}
    assert {m for m in FAZ7_MODEL_IDS if ref[m]["status"] == fz.STATUS_REFUSED} == {CLIP, REAL, POOLED}
    assert {ref[m]["refusal"]["code"] for m in (CLIP, REAL, POOLED)} == {"F3_MISSING"}
    assert {CLIP, REAL, POOLED} <= set(reg.F3_MODELS) and POOLED_INF not in reg.F3_MODELS


# ---------------------------------------------------------------- MODELS.md dondurma notu

def test_models_md_freeze_note():
    text = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
    section = text.split("## Faz 7: tavan serisi v1")[1].split("## Faz 5: D1 sonrası güncelleme")[0]
    note = section.split("### Dondurma")[1]
    assert section.count("### Dondurma") == 1 and "henüz dondurulmadı" in section.split("### Dondurma")[0]
    for e in r7.frozen_entries():
        assert f"| `{e['model_id']}` | `models/{e['file']}` | `{e['sha256']}` | {e['frozen_at'][:10]} |" in note
    assert "4.3e-11" in note and "docs/fable_faz7_audit/" in note and "2026-09-26" in note and "FREEZE_OK" in note
    assert "kasa: bekliyor ((C) şartnamesiyle birlikte açılır)" in note
    assert "canlı n: dondurma commit'inden sonra listelenen arzlarla başlar; var olan 7 canlı kayıt v1 için RETRO" in note
    assert "§5.5 k3: uygulama birincili olamaz" in note
    for m in r7.NOT_APP_PRIMARY:
        assert f"| `{m}` | `models/{m}.json` |" in note and m in note

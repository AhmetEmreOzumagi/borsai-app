"""Faz 7 dondurma görevi, kod commit'i (K): `ceiling_hazard_v1_*` dondurma yolu ve kayıt yazıcının v1 girdileri
(SPEC_HAZARD_V1 §3.2, §3.3, §8, §9; SPEC_DEVIATIONS J4–J6; Fable denetimi B7). Hepsi geçici dizinde; gerçek models/ ve
registry/ yazılmaz. v1 JSON'ları yerine nihai fit önizlemeleri kullanılır (dondurulacak dosyalarla `created_at`,
`code_version`, `runtime` dışında aynı; tests/test_faz7_golden.py)."""
from __future__ import annotations

import copy
import json
import shutil
from datetime import datetime, timezone

import pytest

from borsai import backtest as bt
from borsai import fit as fitmod
from borsai import freeze as fz
from borsai import predict_hazard as ph
from borsai import registry as reg
from borsai import tufe
from borsai.data import load_dataset
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes, sha256_file
from borsai.specs import DEFLATOR, FAZ7_MODEL_IDS, FAZ7_MODEL_SPECS, FAZ7C_MODEL_SPECS

from test_outcome_guard import OUTCOME_KEYS

CLIP, REAL, POOLED, POOLED_INF = FAZ7_MODEL_IDS
NOW = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
GOLDEN = bt.GOLDEN_FAZ7_DIR


def _preview(model_id):
    return json.loads((GOLDEN / bt.final_preview_filename(model_id)).read_text(encoding="utf-8"))


def _models_dir(tmp_path, with_v1=True):
    """models/'in listeleme öncesi 19 modeli (Faz 7 ve Faz 7C dışı INDEX girdileri; Faz 7C dondurmasından sonra da aynı küme,
    SPEC_DEVIATIONS K19) + istenirse dört v1 önizlemesi INDEX'in sonunda."""
    d = tmp_path / "models"
    d.mkdir()
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
    index["models"] = [e for e in index["models"] if e["model_id"] not in FAZ7_MODEL_SPECS and e["model_id"] not in FAZ7C_MODEL_SPECS]
    for e in index["models"]:
        shutil.copyfile(ROOT / "models" / e["file"], d / e["file"])
    if with_v1:
        for m in FAZ7_MODEL_IDS:
            payload = pretty_json_bytes(_preview(m))
            (d / f"{m}.json").write_bytes(payload)
            index["models"].append(fz.index_entry(_preview(m), f"{m}.json", sha256_bytes(payload)))
    (d / "INDEX.json").write_bytes(pretty_json_bytes(index))
    return d


def _inputs(tmp_path, ticker="CITAS", **field_values):
    doc = copy.deepcopy(reg.load_inputs(reg.INPUTS_DIR / f"{ticker}.json")[0])
    for name, value in field_values.items():
        doc["fields"][name]["value"] = value
        if value is None:
            doc["fields"][name]["missing_reason"] = "test"
    p = tmp_path / f"{ticker}_synthetic.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


# ---------------------------------------------------------------- (1) model dondurma yolu

def test_freeze_routes_v1_ids_to_final_fit_v1(tmp_path, monkeypatch):
    """`freeze` v1 kimliklerini `backtest.final_fit_v1`'e yönlendirir (fit.fit v1'i bilmez); INDEX'in sonuna FAZ7 sırasıyla
    eklenir, ilk girdiler metin olarak aynı kalır; aynı kimlik ikinci kez dondurulmaz; CLI v1 kimliklerini tanır."""
    d = _models_dir(tmp_path, with_v1=False)
    before = json.loads((d / "INDEX.json").read_text(encoding="utf-8"))["models"]
    calls = []
    monkeypatch.setattr(bt, "final_fit_v1", lambda m, *a, **k: (calls.append(m) or _preview(m), None))
    monkeypatch.setattr(fitmod, "fit", lambda *a, **k: pytest.fail("fit.fit v1 için çağrılmamalı"))
    index = fz.freeze(list(FAZ7_MODEL_IDS), load_dataset(), models_dir=d)
    assert calls == list(FAZ7_MODEL_IDS)
    assert index["models"][:len(before)] == before and [e["model_id"] for e in index["models"][len(before):]] == list(FAZ7_MODEL_IDS)
    for e in index["models"][len(before):]:
        raw = (d / e["file"]).read_bytes()
        assert e["file"] == f"{e['model_id']}.json" and e["sha256"] == sha256_bytes(raw) and json.loads(raw) == _preview(e["model_id"])
        assert e["spec_sha256"] == _preview(e["model_id"])["spec_sha256"] and e["status"] == "FROZEN"
    with pytest.raises(fz.FreezeError):
        fz.freeze([CLIP], load_dataset(), models_dir=d)
    seen = {}
    monkeypatch.setattr(fz, "freeze", lambda ids, ds: seen.setdefault("ids", ids) and {"models": []})
    monkeypatch.setattr("borsai.data.load_dataset", lambda: None)
    assert fz.main(["--models", *FAZ7_MODEL_IDS]) == 0 and seen["ids"] == list(FAZ7_MODEL_IDS)


# ---------------------------------------------------------------- (2) canlı kayıt: TÜFE bloğu, ön koşul, rejim

@pytest.mark.requires_raw_sources
def test_live_record_writes_tufe_block_and_inputs(tmp_path):
    """§3.2 (market20 kalıbı): `tufe` bloğu {ay (T − 2), endeks, yayım < T, bülten, dosya sha, kural, model pinleri} ve
    model_inputs["tufe_index"]; real/pooled TÜFE'yi bu girdiden alır; canlıda alloc_regime anahtarı yok, pooled r = 0.
    v1 dışındaki 19 hücre v1'siz INDEX'le kurulan kayıttakiyle aynı; kayıtta sonuç alanı adı yok (§11-15)."""
    rec = fz.build_record(reg.INPUTS_DIR / "CITAS.json", now=NOW, models_dir=_models_dir(tmp_path))
    t = rec["inputs"]["document"]["fields"]["first_trading_date"]["value"]
    want = tufe.index_for(t, tufe.load())
    block = rec["tufe"]
    assert (block["month"], block["index"], block["release_date"], block["bulletin_id"]) == \
        (tufe.month_for(t), want["index"], want["release_date"], want["bulletin_id"])
    assert block["release_date"] < t and block["rule"] == "T_MONTH_MINUS_2" and block["refusal"] is None
    assert block["file"] == tufe.TUFE_REL and block["file_sha256"] == sha256_file(ROOT / tufe.TUFE_REL)
    pin = {"through_month": DEFLATOR["through_month"], "prefix_sha256": DEFLATOR["file_sha256"]}
    assert block["pins"] == {REAL: pin, POOLED: pin}
    inputs = rec["model_inputs"]
    assert inputs["tufe_index"] == want["index"] and inputs["tufe_refusal"] is None and "alloc_regime" not in inputs
    cells = {c["model_id"]: c for c in rec["models"]}
    assert [c["model_id"] for c in rec["models"]][-4:] == list(FAZ7_MODEL_IDS)
    for m in FAZ7_MODEL_IDS:
        assert cells[m]["status"] == fz.STATUS_PREDICTED, m
        assert cells[m]["output"] == ph.predict(_preview(m), inputs)
    for m in (REAL, POOLED):
        assert cells[m]["output"]["tufe_index_used"] == want["index"]
    for m in (POOLED, POOLED_INF):
        assert (cells[m]["output"]["regime_value_used"], cells[m]["output"]["regime_source"]) == (0, ph.REGIME_SOURCE_LIVE)
    (tmp_path / "b").mkdir()
    base = fz.build_record(reg.INPUTS_DIR / "CITAS.json", now=NOW, models_dir=_models_dir(tmp_path / "b", with_v1=False))
    assert "tufe" not in base and "tufe_index" not in base["model_inputs"]              # deflatörlü model yoksa blok yok
    assert len(base["models"]) == 19 and rec["models"][:19] == base["models"]
    assert not set(_keys(rec)) & OUTCOME_KEYS


@pytest.mark.requires_raw_sources
def test_live_record_stops_before_writing_when_tufe_month_missing(tmp_path):
    """§9 kayıt ön koşulu: deflatörlü model varken T'nin ayı − 2 dosyada yoksa kayıt YAZILMAZ; ileti eksik ayı ve aylık
    ekleme komutunu söyler. Deflatörlü model yoksa aynı girdiyle kayıt kurulur (ön koşul yalnız TÜFE kullanan INDEX'te)."""
    late = _inputs(tmp_path, first_trading_date="2026-11-02")                     # T − 2 = 2026-09 (dosyada 2026-08'e kadar)
    d = _models_dir(tmp_path)
    with pytest.raises(fz.TufeMissing) as e:
        fz.build_record(late, now=NOW, models_dir=d)
    assert e.value.month == "2026-09" and e.value.code == "TUFE_MISSING"
    assert "2026-09" in str(e.value) and tufe.append_command("2026-09") in str(e.value)
    records = tmp_path / "records"
    with pytest.raises(fz.TufeMissing):
        fz.write_record(late, now=NOW, records_dir=records, models_dir=d)
    assert not records.exists() or not any(records.rglob("*.json"))
    (tmp_path / "b").mkdir()
    ok = fz.build_record(late, now=NOW, models_dir=_models_dir(tmp_path / "b", with_v1=False))
    assert "tufe" not in ok and len(ok["models"]) == 19


@pytest.mark.requires_raw_sources
def test_live_record_tufe_pin_mismatch_refuses_only_deflated_models(tmp_path, monkeypatch):
    """§9: TÜFE dosyasının pinli öneki değiştiyse (eski satır, temel yıl, zincirleme) deflatörlü modeller RET
    TUFE_FILE_MISMATCH; kayıt yazılır, v1_clip ve öteki modeller tahmin verir."""
    table = tufe.load()
    changed = tufe.parse(table.raw.replace(b"2019-11,13.736052,", b"2019-11,13.736053,"))
    monkeypatch.setattr(tufe, "load", lambda path=tufe.TUFE_PATH: changed)
    rec = fz.build_record(reg.INPUTS_DIR / "CITAS.json", now=NOW, models_dir=_models_dir(tmp_path))
    cells = {c["model_id"]: c for c in rec["models"]}
    assert rec["tufe"]["refusal"] == tufe.TUFE_FILE_MISMATCH and rec["model_inputs"]["tufe_index"] is None
    for m in (REAL, POOLED):
        assert cells[m]["status"] == fz.STATUS_REFUSED and cells[m]["refusal"]["code"] == tufe.TUFE_FILE_MISMATCH
    assert cells[CLIP]["status"] == cells[POOLED_INF]["status"] == cells["ceiling_hazard_v0"]["status"] == fz.STATUS_PREDICTED


@pytest.mark.requires_raw_sources
def test_live_record_unknown_T_refuses_deflated_models(tmp_path):
    """T bilinmiyorsa ay belirlenemez (f6'nın T_UNKNOWN kalıbı): kayıt yazılır, real/pooled RET TUFE_MISSING."""
    rec = fz.build_record(_inputs(tmp_path, first_trading_date=None), now=NOW, models_dir=_models_dir(tmp_path))
    assert rec["tufe"]["refusal"] == tufe.TUFE_MISSING and rec["tufe"]["month"] is None
    cells = {c["model_id"]: c for c in rec["models"]}
    assert cells[REAL]["refusal"]["code"] == cells[POOLED]["refusal"]["code"] == tufe.TUFE_MISSING


def test_regime_input_guard_b7():
    """Fable denetimi B7 (J6): eski kohort kaydında (OOT_PRE_LISTING) rejimli model varken alloc_regime anahtarı zorunlu;
    canlı kayıtta anahtar olamaz; rejimli model yoksa iki aşamada da serbest."""
    pooled = ({"model_id": POOLED}, _preview(POOLED), "x")
    clip = ({"model_id": CLIP}, _preview(CLIP), "y")
    assert fz.regime_input_problems(fz.OOT_STAGE, [clip, pooled], {}) != []
    assert fz.regime_input_problems(fz.OOT_STAGE, [clip, pooled], {"alloc_regime": "EQUAL_DIST_20230330"}) == []
    assert fz.regime_input_problems(fz.OOT_STAGE, [clip], {}) == []
    assert fz.regime_input_problems(None, [clip, pooled], {}) == []
    assert fz.regime_input_problems(None, [clip, pooled], {"alloc_regime": "PRE_20211111"}) != []


@pytest.mark.requires_raw_sources
def test_oot_record_carries_cohort_regime_and_tufe_and_guard_b7():
    """J2/J6/B7: INDEX'te rejimli ve deflatörlü model varken eski kohort kaydı (OOT_PRE_LISTING) model_inputs["alloc_regime"] =
    kohort satırının ALLOC_REGIME etiketi ve `tufe` bloğunu taşır; pooled r'yi etiketten alır (ALLOC_REGIME_INPUT). Anahtar
    unutulursa (etiketsiz çağrı) kayıt kurulmaz. v1'siz model listesiyle kayıt S2 biçimindedir (anahtar ve blok yok).
    Açık küme üyesi, bellekte, yazmadan (ikinci kayıt akışı `--only-missing-models` ayrı görev)."""
    header, rows = reg.read_cohort()
    member = next(r for r in reg.cohort_members(rows) if r["vault"] == "OPEN" and (reg.OOT_INPUTS_DIR / f"{r['ticker']}.json").exists()
                  and reg.load_inputs(reg.OOT_INPUTS_DIR / f"{r['ticker']}.json")[0]["fields"]["total_demand_multiple"]["value"])
    label = reg.parse_regime_tags(member["regime_tags"])["ALLOC_REGIME"]
    index, index_sha, models = fz._index_models(fz.MODELS_DIR)
    base = [x for x in models if x[0]["model_id"] not in FAZ7_MODEL_SPECS and x[0]["model_id"] not in FAZ7C_MODEL_SPECS]
    v1 = [({"model_id": m, "file": f"{m}.json", "spec_sha256": _preview(m)["spec_sha256"], "algorithm": _preview(m)["algorithm"]},
           _preview(m), "0" * 64) for m in FAZ7_MODEL_IDS]
    kw = dict(cohort_sha256=sha256_file(reg.COHORT_PATH), inputs_path=reg.OOT_INPUTS_DIR / f"{member['ticker']}.json", now=NOW)
    rec = fz.build_oot_record(member, index_models=(index, index_sha, base + v1), **kw)
    assert rec["model_inputs"]["alloc_regime"] == label and rec["tufe"]["month"] == tufe.month_for(member["first_trading_date"])
    assert rec["model_inputs"]["tufe_index"] == rec["tufe"]["index"] and rec["tufe"]["refusal"] is None
    cells = {c["model_id"]: c for c in rec["models"]}
    for m in (POOLED, POOLED_INF):
        out = cells[m]["output"]
        assert (out["regime_value_used"], out["regime_source"]) == (ph.regime_value(label), ph.REGIME_SOURCE_INPUT)
    assert cells[REAL]["status"] == fz.STATUS_PREDICTED and cells[REAL]["output"]["tufe_index_used"] == rec["tufe"]["index"]
    s2 = fz.build_oot_record(member, index_models=(index, index_sha, base), **kw)
    assert "tufe" not in s2 and "alloc_regime" not in s2["model_inputs"] and "tufe_index" not in s2["model_inputs"]
    assert rec["models"][:len(base)] == s2["models"]
    with pytest.raises(fz.FreezeError, match="alloc_regime"):
        fz.v1_record_inputs(fz.OOT_STAGE, member["first_trading_date"], base + v1, {}, alloc_regime=None)

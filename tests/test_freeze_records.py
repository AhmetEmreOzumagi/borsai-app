"""Kayıt yazıcı (borsai/freeze.py, CLAUDE.md kural 1; SPEC_SCORING §5-§6): bütün modeller kayıtta,
ret hücreleri, üzerine yazma reddi, iptal kaydı; commit edilen kayıtların tutarlılığı ve paritesi."""
from __future__ import annotations

import copy
import json
import math
from datetime import datetime, timezone

import pytest

from borsai import freeze as fz
from borsai import registry as reg
from borsai.provenance import ROOT, sha256_bytes, sha256_file

NOW = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
INDEX = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
MODEL_IDS = [e["model_id"] for e in INDEX["models"]]
F3_MODELS = sorted(set(reg.F3_MODELS) & set(MODEL_IDS))   # INDEX'te olmayan ad etkisiz (Faz 7C adayları dondurulana dek; K16)
EXPECTED_REFUSALS = {  # arz -> {model: ret kodu}; boş = bütün modeller tahmin verdi
    "CITAS": {}, "TKNKA": {}, "KPEKS": {}, "INTET": {}, "BKRGY": {}, "NETGL": {},
    "VEYAS": {m: "F3_MISSING" for m in F3_MODELS},
}
CLASS_WORDS = ("LIVE", "LATE_RECORD", "RETRO", "LEGACY_SELF_REPORTED")


def inputs_path(ticker):
    return reg.INPUTS_DIR / f"{ticker}.json"


def synthetic_inputs(tmp_path, ticker="CITAS", **field_values):
    doc = copy.deepcopy(reg.load_inputs(inputs_path(ticker))[0])
    for name, value in field_values.items():
        doc["fields"][name]["value"] = value
        if value is None:
            doc["fields"][name]["missing_reason"] = "test"
    p = tmp_path / f"{ticker}_synthetic.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


def keys_of(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from keys_of(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from keys_of(v)


# ---------------------------------------------------------------- yazıcı (geçici dizin)

@pytest.mark.requires_raw_sources
def test_record_contains_every_registered_model(tmp_path):
    path = fz.write_record(inputs_path("CITAS"), now=NOW, records_dir=tmp_path)
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["schema_version"] == fz.RECORD_SCHEMA and rec["record_type"] == "PREDICTION"
    assert [c["model_id"] for c in rec["models"]] == MODEL_IDS == rec["models_index"]["model_ids"]
    for c in rec["models"]:
        assert c["params_sha256"] == sha256_file(ROOT / c["file"])
        assert c["status"] in ("PREDICTED", "REFUSED")
    assert rec["input_sha256"] == sha256_file(inputs_path("CITAS")) == rec["inputs"]["sha256"]
    assert rec["inputs"]["document"] == reg.load_inputs(inputs_path("CITAS"))[0]
    assert rec["recorded_at_utc"] == "2026-09-22T12:00:00Z" and rec["recorded_at_istanbul"] == "2026-09-22T15:00:00+03:00"
    assert rec["code"]["borsai_source_sha256"] and "git_head" in rec["code"]
    assert rec["market20"]["ref_date"] == "2026-08-18" and rec["market20"]["refusal"] is None
    assert path.name == f"20260922T120000Z_{sha256_bytes(path.read_bytes())[:12]}.json"
    # sınıf elle etiketlenmez (SPEC_SCORING §10-5)
    assert not any(k in ("class", "record_class", "classification") for k in keys_of(rec))
    assert not any(w in json.dumps(rec["summary"]) for w in CLASS_WORDS)


@pytest.mark.requires_raw_sources
def test_refusal_cells_carry_code_and_reason(tmp_path):
    rec = json.loads(fz.write_record(inputs_path("VEYAS"), now=NOW, records_dir=tmp_path).read_text(encoding="utf-8"))
    refused = {c["model_id"]: c for c in rec["models"] if c["status"] == "REFUSED"}
    assert set(refused) == set(F3_MODELS)
    for c in refused.values():
        assert c["refusal"]["code"] == "F3_MISSING" and c["refusal"]["reason"] and c["refusal"]["field"] == "total_demand_multiple"
        hs = [h for h in ("D1", "D3", "D5", "D10") if h in c["output"]]      # düşen arz ailesi yalnız D5 ve D10 (SPEC_C_V0 §2.3)
        assert all(c["output"][h] is None for h in hs) if hs else c["output"]["S"] is None
    assert rec["summary"]["refusals"] == EXPECTED_REFUSALS["VEYAS"]


@pytest.mark.requires_raw_sources
def test_pb_field_missing_refuses_only_pb_models(tmp_path):
    p = synthetic_inputs(tmp_path, planned_base_offer_shares=None)
    rec = fz.build_record(p, now=NOW)
    assert rec["summary"]["refusals"] == {"pb_v0": "PB_FIELD_MISSING", "pb_ceiling_v0": "PB_FIELD_MISSING",
                                          "pb_ceiling_path_v0": "PB_FIELD_MISSING"}


@pytest.mark.requires_raw_sources
def test_no_overwrite_and_duplicate_record_rejected(tmp_path):
    first = fz.write_record(inputs_path("KPEKS"), now=NOW, records_dir=tmp_path)
    before = first.read_bytes()
    with pytest.raises(fz.DuplicateRecord, match="DUPLICATE_RECORD"):   # aynı girdi + aynı model dizini
        fz.write_record(inputs_path("KPEKS"), now=datetime(2026, 9, 22, 13, 0, tzinfo=timezone.utc), records_dir=tmp_path)
    with pytest.raises(FileExistsError):
        fz._write_new(first, b"{}")
    assert first.read_bytes() == before
    # KPEKS ilk işlem günü (2026-08-21) geçti: iptal reddedilir
    with pytest.raises(fz.FreezeError, match="ilk işlem"):
        fz.cancel_record(first, "hatalı girdi", now=NOW, records_dir=tmp_path)


@pytest.mark.requires_raw_sources
def test_second_active_record_with_different_inputs_is_allowed(tmp_path):
    """SPEC_SCORING §6: aynı arz için birden çok etkin kayıt olabilir (önce talep öncesi PB kaydı, sonra talep
    katlı kayıt); hangisinin skorlandığına select_primary karar verir. İptal gerekmez."""
    pre = tmp_path / "pre.json"
    pre.write_text(synthetic_inputs(tmp_path, first_trading_date="2026-09-30", total_demand_multiple=None)
                   .read_text(encoding="utf-8"), encoding="utf-8")
    post = tmp_path / "post.json"
    post.write_text(synthetic_inputs(tmp_path, first_trading_date="2026-09-30").read_text(encoding="utf-8"), encoding="utf-8")
    a = fz.write_record(pre, now=NOW, records_dir=tmp_path / "rec")
    b = fz.write_record(post, now=datetime(2026, 9, 22, 13, 0, tzinfo=timezone.utc), records_dir=tmp_path / "rec")
    active = [x.name for x, _ in fz.active_records("CITAS", tmp_path / "rec")]
    assert active == sorted([a.name, b.name])
    ra, rb = (json.loads(x.read_text(encoding="utf-8")) for x in (a, b))
    assert ra["summary"]["refusals"] == {m: "F3_MISSING" for m in F3_MODELS} and rb["summary"]["refusals"] == {}
    with pytest.raises(fz.DuplicateRecord):
        fz.write_record(post, now=datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc), records_dir=tmp_path / "rec")


@pytest.mark.requires_raw_sources
def test_cancellation_record_then_new_record(tmp_path):
    p = synthetic_inputs(tmp_path, first_trading_date="2026-09-30")
    first = fz.write_record(p, now=NOW, records_dir=tmp_path)
    rec = json.loads(first.read_text(encoding="utf-8"))
    assert rec["market20"]["ref_date_rule"] == "LIVE_PREDICTION_DATE" and rec["market20"]["ref_date"] == "2026-09-22"
    with pytest.raises(fz.FreezeError):
        fz.cancel_record(first, "  ", now=NOW, records_dir=tmp_path)
    cancel = fz.cancel_record(first, "test: girdi hatası", now=datetime(2026, 9, 22, 13, 0, tzinfo=timezone.utc), records_dir=tmp_path)
    c = json.loads(cancel.read_text(encoding="utf-8"))
    assert c["record_type"] == "CANCELLATION" and c["cancels"] == {"file": first.name, "sha256": sha256_file(first)}
    assert fz.active_records("CITAS", tmp_path) == []
    with pytest.raises(fz.FreezeError):  # iki kez iptal yok
        fz.cancel_record(first, "yine", now=NOW, records_dir=tmp_path)
    second = fz.write_record(p, now=datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc), records_dir=tmp_path)
    assert [x.name for x, _ in fz.active_records("CITAS", tmp_path)] == [second.name]
    assert first.exists() and json.loads(first.read_text(encoding="utf-8")) == rec  # iptal edilen dosya değişmez


def test_writer_refuses_non_pit_inputs(tmp_path):
    p = synthetic_inputs(tmp_path, first_trading_date="2026-08-13")  # sonuç bildirimi 08-13 13:12, T'den önce değil
    with pytest.raises(fz.FreezeError, match="girdi belgesi"):
        fz.write_record(p, now=NOW, records_dir=tmp_path)
    assert not (tmp_path / "CITAS").exists()


@pytest.mark.requires_raw_sources
def test_record_is_deterministic_given_time():
    a = fz.build_record(inputs_path("NETGL"), now=NOW)
    b = fz.build_record(inputs_path("NETGL"), now=NOW)
    assert a == b


def test_record_writer_is_stdlib_only():
    """Masaüstü 'dondur' düğmesi aynı yolu çağırır: numpy/scikit-learn/scipy yüklenmez."""
    import subprocess
    import sys

    code = ("import sys, borsai.freeze, borsai.registry, borsai.push_proof; "
            "print(sorted(m for m in ('numpy', 'sklearn', 'scipy') if m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    assert out.strip() == "[]"


def test_cli_writes_record(tmp_path, monkeypatch):
    monkeypatch.setattr(fz, "write_record", lambda path: tmp_path / f"called_{path.name}")
    assert fz.main([str(inputs_path("TKNKA"))]) == 0


# ---------------------------------------------------------------- commit edilen kayıtlar

def committed():
    _, rows = reg.read_ipos()
    frozen = [r["ticker"] for r in rows if r["status"] == "FROZEN"]
    return {t: fz.active_records(t) for t in frozen}


def test_each_frozen_ipo_has_an_active_record_and_no_duplicates():
    recs = committed()
    assert set(recs) == set(reg.KNOWN_TICKERS)
    for t, active in recs.items():
        assert active, t
        keys = [(r["input_sha256"], r["models_index"]["sha256"]) for _, r in active]
        assert len(keys) == len(set(keys)), t


@pytest.mark.requires_raw_sources
@pytest.mark.parametrize("ticker", sorted(reg.KNOWN_TICKERS))
def test_committed_record_consistency(ticker):
    (path, rec), *_ = fz.active_records(ticker)
    assert path.name.split("_")[1][:12] == sha256_bytes(path.read_bytes())[:12]
    assert rec["ticker"] == ticker and rec["input_sha256"] == sha256_file(inputs_path(ticker))
    assert rec["inputs"]["document"] == reg.load_inputs(inputs_path(ticker))[0]
    # Kayıt, yazıldığı andaki models/INDEX.json'ın fotoğrafıdır (`models_index.sha256`). INDEX'e yalnız sona
    # eklenir ve dondurulmuş dosya değişmez (kural 1, 5): kayıttaki liste bugünkü INDEX'in ön ekidir ve
    # parametre sha'ları aynı kalır. Sonradan dondurulan model o arz için RETRO'dur (scores.json: retro_info).
    ids = [c["model_id"] for c in rec["models"]]
    assert ids == MODEL_IDS[:len(ids)]
    for c in rec["models"]:
        assert c["params_sha256"] == next(e["sha256"] for e in INDEX["models"] if e["model_id"] == c["model_id"])
    assert rec["summary"]["refusals"] == {m: c for m, c in EXPECTED_REFUSALS[ticker].items() if m in ids}
    assert rec["summary"]["n_models"] == len(ids)
    t = rec["inputs"]["document"]["fields"]["first_trading_date"]["value"]
    m = rec["market20"]
    assert m["refusal"] is None and m["S0_date"] < m["ref_date"] <= t  # f6'nın inputs_pit_ok kısmı
    assert reg.inputs_pit_problems(rec["inputs"]["document"]) == []
    assert [l["record"] for l in rec["legacy_links"]] == [e["record"] for e in reg.legacy_links(ticker)]


def _close(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=0, abs_tol=1e-9)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    return a == b


@pytest.mark.parametrize("ticker", sorted(reg.KNOWN_TICKERS))
def test_committed_record_parity(ticker):
    """Dondurulmuş değer yeniden hesaplanmaz; yeniden hesap yalnız parite denetimidir (|Δ| ≤ 1e-9)."""
    (_, rec), *_ = fz.active_records(ticker)
    for c in rec["models"]:
        params = json.loads((ROOT / c["file"]).read_text(encoding="utf-8"))
        again = fz.run_model(params, rec["model_inputs"])
        assert again["status"] == c["status"] and _close(again["output"], c["output"]), (ticker, c["model_id"])

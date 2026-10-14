"""Faz 8 dondurma görevi, kod commit'i (K): `break_floor_v0` ve kural satırı `break_floor_v0@ZERO` için dondurma yolu (SPEC_BREAK_V0
§4.4, §7.3, §9.2; SPEC_DEVIATIONS N21–N23). `freeze` iki kimliği `freeze_post_break`'e yönlendirir (yalnız birlikte, FAZ8_MODEL_IDS
sırasıyla); dosyalar models/<id>.json + models/INDEX_POST_BREAK.json; INDEX.json ve INDEX_POST_D1.json'a yazılmaz. `model_kind`
aşama/aile ile "post_break" döner (algoritma adı Faz 7C ile ortak); `run_model` listeleme öncesi kayıtta çalıştırmaz. Testler geçici
dizinde; gerçek models/ yazılmaz. Nihai fit yerine nihai fit önizlemeleri kullanılır (dondurulacak dosyalarla `created_at`,
`code_version`, `runtime` dışında aynı; tests/test_faz8_golden.py::test_b5)."""
from __future__ import annotations

import json

import pytest

from borsai import backtest as bt
from borsai import fit as fitmod
from borsai import freeze as fz
from borsai import post_break as pbk
from borsai import post_d1 as pd
from borsai import predict_break as pb
from borsai import predict_fall as pf
from borsai import specs
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes
from borsai.specs import FAZ8_MODEL_IDS, POST_BREAK_MODEL_SPECS

MODEL_ID, ZERO_ID = FAZ8_MODEL_IDS
INDEX_ENTRY_KEYS = ("model_id", "file", "sha256", "algorithm", "schema_version", "spec_sha256", "training_n", "training_cutoff_date",
                    "training_tickers_sha256", "data_version_sha256", "frozen_at", "frozen_at_basis", "status")
EXTRA_KEYS = ("stage", "training_n_F2", "training_tickers_sha256_F2", "sessions_file_sha256")
# Var olan 28 donmuş modelin türü (freeze.model_kind: parametre dosyasından; specs.model_kind: şartnameden), dondurma görevinin
# provasında K'dan önce ve sonra ölçüldü (aynı; SPEC_DEVIATIONS N23). market20 ve pb'yi şartname "linear" sayar (eski ayrım).
KINDS_28 = {
    "v1_5_h99": ("linear", "linear"), "base_always_ceiling": ("rule", "rule"), "base_train_median": ("rule", "rule"),
    "base_train_mean": ("rule", "rule"), "base_zero": ("rule", "rule"), "base_rate": ("rule", "rule"),
    "base_last10_rate": ("rule", "rule"), "v1_6_h99": ("linear", "linear"), "v1_5_market20_v0": ("market20", "linear"),
    "pb_v0": ("pb", "linear"), "ceiling_hazard_v0": ("hazard", "hazard"), "ceiling_hazard_v0@INF": ("hazard", "hazard"),
    "pb_ceiling_v0": ("hazard", "hazard"), "pb_ceiling_v0@INF": ("hazard", "hazard"), "base_km_expanding": ("km", "km"),
    "base_km_last10": ("km", "km"), "ceiling_path_v0": ("ceiling_path", "ceiling_path"),
    "ceiling_path_v0@INF": ("ceiling_path", "ceiling_path"), "pb_ceiling_path_v0": ("ceiling_path", "ceiling_path"),
    "ceiling_hazard_v1_clip": ("hazard", "hazard"), "ceiling_hazard_v1_real": ("hazard", "hazard"),
    "ceiling_hazard_v1_pooled": ("hazard", "hazard"), "ceiling_hazard_v1_pooled@INF": ("hazard", "hazard"),
    "fall_d10_v0_h99": ("fall", "fall"), "fall_d10_v0_pooled": ("fall", "fall"), "fall_d10_v0_addsale": ("fall", "fall"),
    "fall_d10_v0_pooled@ZERO": ("fall", "fall"), "post_d1_hazard_v0": ("post_d1", "post_d1"),
}


def _preview(model_id):
    return json.loads((pbk.GOLDEN_DIR / pbk.preview_file(model_id)).read_text(encoding="utf-8"))


def _models_dir(tmp_path):
    """Gerçek INDEX.json ve INDEX_POST_D1.json'un baytları (model dosyaları gerekmez: dondurma yalnız dizinleri ve dosya varlığını
    okur)."""
    d = tmp_path / "models"
    d.mkdir()
    for name in ("INDEX.json", fz.INDEX_POST_D1_NAME):
        (d / name).write_bytes((ROOT / "models" / name).read_bytes())
    return d


@pytest.fixture
def fake_fit(monkeypatch):
    """`post_break.final_fit` -> önizleme (dataset nesnesi aynen geçer); öteki fit yolları çağrılırsa test düşer."""
    calls = []

    def final_fit(model_id, dataset, **kw):
        calls.append((model_id, dataset, kw))
        return _preview(model_id), None

    monkeypatch.setattr(pbk, "final_fit", final_fit)
    for mod, name in ((fitmod, "fit"), (bt, "final_fit_v1"), (bt, "final_fit_fall"), (pd, "fit_params")):
        monkeypatch.setattr(mod, name, lambda *a, _n=name, **k: pytest.fail(f"{_n} Faz 8 kimlikleri için çağrılmamalı"))
    return calls


# ---------------------------------------------------------------- (1) dondurma yolu

def test_freeze_writes_two_files_and_post_break_index_only(tmp_path, fake_fit):
    """§7.3: iki kimlik `freeze` üzerinden `post_break.final_fit`'e gider (FAZ8_MODEL_IDS sırasıyla, dataset aynen); models/<id>.json =
    `pretty_json_bytes(params)`; INDEX_POST_BREAK.json yeni (borsai.model_index/1, iki giriş, sha'lar dosyalarla eşit); INDEX.json ve
    INDEX_POST_D1.json bayt-eşit; başka dosya yazılmaz."""
    d = _models_dir(tmp_path)
    before = {p.name: p.read_bytes() for p in d.iterdir()}
    ds = object()
    index = fz.freeze(list(FAZ8_MODEL_IDS), ds, models_dir=d)
    assert [(m, x) for m, x, _ in fake_fit] == [(MODEL_ID, ds), (ZERO_ID, ds)]
    assert sorted(p.name for p in d.iterdir()) == sorted([*before, fz.INDEX_POST_BREAK_NAME, f"{MODEL_ID}.json", f"{ZERO_ID}.json"])
    for name, raw in before.items():
        assert (d / name).read_bytes() == raw, name
    raw_index = (d / fz.INDEX_POST_BREAK_NAME).read_bytes()
    assert raw_index == pretty_json_bytes(index) and json.loads(raw_index) == index
    assert index["schema_version"] == fz.INDEX_SCHEMA and [e["model_id"] for e in index["models"]] == list(FAZ8_MODEL_IDS)
    for e in index["models"]:
        raw = (d / e["file"]).read_bytes()
        assert e["file"] == f"{e['model_id']}.json" and raw == pretty_json_bytes(_preview(e["model_id"]))
        assert e["sha256"] == sha256_bytes(raw)
    assert fz.INDEX_POST_BREAK_PATH == fz.MODELS_DIR / "INDEX_POST_BREAK.json"


def test_post_break_index_entry_fields(tmp_path, fake_fit):
    """K-FRZ-2 (SPEC_DEVIATIONS N22): giriş = `index_entry`'nin alanları (`training_n` = n_F1; `index_entry` kırılma JSON'unda KeyError
    verir: tek `n` yok) + `stage`, `training_n_F2`, `training_tickers_sha256_F2`, `sessions_file_sha256`."""
    d = _models_dir(tmp_path)
    index = fz.freeze(list(FAZ8_MODEL_IDS), object(), models_dir=d)
    for e in index["models"]:
        p = _preview(e["model_id"])
        tr = p["training"]
        with pytest.raises(KeyError):
            fz.index_entry(p, e["file"], e["sha256"])
        assert tuple(e) == INDEX_ENTRY_KEYS + EXTRA_KEYS
        assert e == fz.post_break_index_entry(p, e["file"], e["sha256"])
        assert e["algorithm"] == pb.ALGORITHM and e["schema_version"] == p["schema_version"] and e["status"] == "FROZEN"
        assert e["spec_sha256"] == p["spec_sha256"] == specs.spec_sha256(POST_BREAK_MODEL_SPECS[e["model_id"]])
        assert (e["training_n"], e["training_n_F2"]) == (tr["n_F1"], tr["n_F2"]) == (82, 78)
        assert e["training_tickers_sha256"] == tr["tickers_sha256"] and e["training_tickers_sha256_F2"] == tr["tickers_sha256_F2"]
        assert e["training_cutoff_date"] == tr["cutoff_date"] == "2026-08-10"
        assert e["data_version_sha256"] == tr["data_version_sha256"] == specs.H99_DATA_VERSION_SHA256
        assert e["sessions_file_sha256"] == tr["sessions_file_sha256"] == specs.H99_BREAK_TRAINING["sessions_file_sha256"]
        assert e["stage"] == pb.STAGE and e["frozen_at"] == p["created_at"] and e["frozen_at_basis"] == fz.FROZEN_AT_BASIS


def test_refreeze_and_wrong_calls_are_refused_without_writing(tmp_path, fake_fit):
    """Kural 1: ikinci çağrı reddedilir (dosyalar değişmez). Tek kimlik, ters sıra, başka (listeleme öncesi, POST_D1) modellerle
    karışık çağrı FreezeError; kimlik üç dizinden birinde ya da diskte varsa hiçbir şey yazılmadan FreezeError."""
    d = _models_dir(tmp_path)
    for ids in ([MODEL_ID], [ZERO_ID], [ZERO_ID, MODEL_ID], [MODEL_ID, ZERO_ID, MODEL_ID], [MODEL_ID, ZERO_ID, "v1_5_h99"],
                ["post_d1_hazard_v0", MODEL_ID, ZERO_ID], ["fall_d10_v0_h99", MODEL_ID]):
        with pytest.raises(fz.FreezeError, match="yalnız birlikte"):
            fz.freeze(ids, object(), models_dir=d)
    assert not fake_fit and not (d / fz.INDEX_POST_BREAK_NAME).exists()
    for name in ("INDEX.json", fz.INDEX_POST_D1_NAME, fz.INDEX_POST_BREAK_NAME):     # bir dizinde aynı kimlik (sentetik giriş)
        original = (d / name).read_bytes() if (d / name).exists() else None
        idx = fz.load_index(d / name)
        idx["models"].append({"model_id": ZERO_ID, "file": f"{ZERO_ID}.json"})
        (d / name).write_bytes(pretty_json_bytes(idx))
        with pytest.raises(fz.FreezeError, match="zaten dondurulmuş"):
            fz.freeze(list(FAZ8_MODEL_IDS), object(), models_dir=d)
        if original is None:
            (d / name).unlink()
        else:
            (d / name).write_bytes(original)
    (d / f"{MODEL_ID}.json").write_text("{}", encoding="utf-8")       # diskte dosya var
    with pytest.raises(fz.FreezeError, match="zaten dondurulmuş"):
        fz.freeze(list(FAZ8_MODEL_IDS), object(), models_dir=d)
    (d / f"{MODEL_ID}.json").unlink()
    assert not fake_fit and not (d / fz.INDEX_POST_BREAK_NAME).exists() and not (d / f"{ZERO_ID}.json").exists()
    fz.freeze(list(FAZ8_MODEL_IDS), object(), models_dir=d)
    frozen = {p.name: p.read_bytes() for p in d.iterdir()}
    with pytest.raises(fz.FreezeError, match="zaten dondurulmuş"):
        fz.freeze(list(FAZ8_MODEL_IDS), object(), models_dir=d)
    assert {p.name: p.read_bytes() for p in d.iterdir()} == frozen and len(fake_fit) == 2


def test_cli_models_flag_passes_both_ids_to_freeze(monkeypatch):
    """K-FRZ-1 (SPEC_DEVIATIONS N21): tek dondurma yolu var olan bayraktır, `--post-break` bayrağı yok; CLI iki kimliği tanır ve
    `freeze`'e aynen verir."""
    seen = {}
    monkeypatch.setattr(fz, "freeze", lambda ids, ds: seen.setdefault("ids", ids) and {"models": []})
    monkeypatch.setattr("borsai.data.load_dataset", lambda: None)
    assert fz.main(["--models", *FAZ8_MODEL_IDS]) == 0 and seen["ids"] == list(FAZ8_MODEL_IDS)
    with pytest.raises(SystemExit):
        fz.main(["--post-break", *FAZ8_MODEL_IDS])


# ---------------------------------------------------------------- (2) tür dalları

def test_model_kind_post_break_before_shared_algorithm():
    """K-FRZ-3 (SPEC_DEVIATIONS N23): algoritma adı ortak (`l2_logit_v1_6_grid`); kırılma JSON'u (iki kimlik) `freeze.model_kind` ve
    `specs.model_kind`'de "post_break"; aşama ya da aile tutmazsa dal çalışmaz (algoritma yoluna düşer: "fall")."""
    assert pb.ALGORITHM == pf.FALL_ALGORITHM
    for m in FAZ8_MODEL_IDS:
        p = _preview(m)
        assert fz.model_kind(p) == specs.model_kind(m) == "post_break", m
        assert specs._spec_of(m) is POST_BREAK_MODEL_SPECS[m] and specs.plan_of(m) == specs.PLAN_BREAK_H99
        assert fz.model_kind({**p, "stage": "POST_D1"}) == "fall" and fz.model_kind({**p, "family": "fall_d10_v0"}) == "fall"


def test_existing_28_model_kinds_unchanged():
    """Var olan 28 donmuş modelin (INDEX.json 27 + INDEX_POST_D1.json 1) iki fonksiyondaki türü değişmedi (sabit sözlük)."""
    got = {}
    for name in ("INDEX.json", fz.INDEX_POST_D1_NAME):
        for e in json.loads((ROOT / "models" / name).read_text(encoding="utf-8"))["models"]:
            p = json.loads((ROOT / "models" / e["file"]).read_text(encoding="utf-8"))
            got[e["model_id"]] = (fz.model_kind(p), specs.model_kind(e["model_id"]))
    assert got == KINDS_28


def test_run_model_refuses_post_break_in_pre_listing_record():
    """K-FRZ-3: POST_BREAK modeli listeleme öncesi kayıtta çalışmaz (`post_d1` kalıbı): ERROR + PARAMS_INVALID; tahmin yolu
    (`predict_fall.predict`) çağrılmaz. `post_d1` dalı aynen."""
    for m in FAZ8_MODEL_IDS:
        out = fz.run_model(_preview(m), {})
        assert out == {"kind": "post_break", "status": fz.STATUS_ERROR, "output": None,
                       "refusal": {"code": "PARAMS_INVALID", "field": None,
                                   "reason": "POST_BREAK modeli listeleme öncesi kayıtta çalışmaz"}}
    post = json.loads((ROOT / "models" / "post_d1_hazard_v0.json").read_text(encoding="utf-8"))
    assert fz.run_model(post, {})["refusal"]["reason"] == "POST_D1 modeli listeleme öncesi kayıtta çalışmaz"

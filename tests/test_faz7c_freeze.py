"""Faz 7C dondurma görevi, kod commit'i (K): `fall_d10_v0_*` dondurma yolu ve kayıt yazıcının (C) girdileri (SPEC_C_V0 §2.3, §8,
§9, §11-9; SPEC_DEVIATIONS K16), Fable denetimi F9'un semantik testleri (etiket yönü, test arzından bağımsız fold fit'i). Kayıt testleri
geçici dizinde; gerçek models/ ve registry/ yazılmaz. (C) JSON'ları yerine nihai fit önizlemeleri kullanılır (dondurulacak dosyalarla
`created_at`, `code_version`, `runtime` dışında aynı; tests/test_faz7c_golden.py)."""
from __future__ import annotations

import copy
import json
import random
import shutil
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from borsai import backtest as bt
from borsai import fit as fitmod
from borsai import freeze as fz
from borsai import predict_fall as pf
from borsai import registry as reg
from borsai import scoring as sc
from borsai import specs
from borsai import tufe
from borsai.data import Dataset, IPORowV2, Target, additional_sale_shares, load_dataset, load_dataset_v2
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes
from borsai.specs import DEFLATOR, FAZ7_MODEL_IDS, FAZ7C_MODEL_IDS, FAZ7C_MODEL_SPECS

import faz7c_support as f7c
from test_outcome_guard import OUTCOME_KEYS

H99, POOLED, ADDSALE, ZERO_ROW = FAZ7C_MODEL_IDS
NOW = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
GOLDEN = bt.GOLDEN_FAZ7C_DIR


def _preview(model_id):
    return json.loads((GOLDEN / bt.final_preview_filename(model_id)).read_text(encoding="utf-8"))


def _models_dir(tmp_path, with_fall=True):
    """models/'in (C) dışındaki INDEX girdileri (19 + dört v1; dondurmadan sonra da aynı küme) + istenirse dört (C) önizlemesi
    INDEX'in sonunda (FAZ7C_MODEL_IDS sırası)."""
    d = tmp_path / "models"
    d.mkdir()
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
    index["models"] = [e for e in index["models"] if e["model_id"] not in FAZ7C_MODEL_SPECS]
    for e in index["models"]:
        shutil.copyfile(ROOT / "models" / e["file"], d / e["file"])
    if with_fall:
        for m in FAZ7C_MODEL_IDS:
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

def test_freeze_routes_fall_ids_to_final_fit_fall(tmp_path, monkeypatch):
    """`freeze` (C) kimliklerini `backtest.final_fit_fall`'a yönlendirir (fit.fit ve final_fit_v1 çağrılmaz); INDEX'in sonuna
    FAZ7C sırasıyla eklenir, önceki girdiler metin olarak aynı kalır; aynı kimlik ikinci kez dondurulmaz; CLI (C) kimliklerini tanır."""
    d = _models_dir(tmp_path, with_fall=False)
    before_bytes = (d / "INDEX.json").read_bytes()
    before = json.loads(before_bytes)["models"]
    calls = []
    monkeypatch.setattr(bt, "final_fit_fall", lambda m, *a, **k: (calls.append(m) or _preview(m), None))
    monkeypatch.setattr(bt, "final_fit_v1", lambda *a, **k: pytest.fail("final_fit_v1 (C) için çağrılmamalı"))
    monkeypatch.setattr(fitmod, "fit", lambda *a, **k: pytest.fail("fit.fit (C) için çağrılmamalı"))
    index = fz.freeze(list(FAZ7C_MODEL_IDS), load_dataset(), models_dir=d)
    assert calls == list(FAZ7C_MODEL_IDS)
    assert index["models"][:len(before)] == before and [e["model_id"] for e in index["models"][len(before):]] == list(FAZ7C_MODEL_IDS)
    after = (d / "INDEX.json").read_bytes()
    assert after.startswith(before_bytes[:before_bytes.rindex(b"\n    }") + len(b"\n    }")])     # önceki girdiler metin olarak aynı
    for e in index["models"][len(before):]:
        raw = (d / e["file"]).read_bytes()
        assert e["file"] == f"{e['model_id']}.json" and e["sha256"] == sha256_bytes(raw) and json.loads(raw) == _preview(e["model_id"])
        assert e["spec_sha256"] == _preview(e["model_id"])["spec_sha256"] and e["status"] == "FROZEN"
        assert e["algorithm"] == pf.FALL_ALGORITHM and e["training_n"] == FAZ7C_MODEL_SPECS[e["model_id"]]["training"]["n"]
    with pytest.raises(fz.FreezeError, match="zaten dondurulmuş"):
        fz.freeze([H99], load_dataset(), models_dir=d)
    seen = {}
    monkeypatch.setattr(fz, "freeze", lambda ids, ds: seen.setdefault("ids", ids) and {"models": []})
    monkeypatch.setattr("borsai.data.load_dataset", lambda: None)
    assert fz.main(["--models", *FAZ7C_MODEL_IDS]) == 0 and seen["ids"] == list(FAZ7C_MODEL_IDS)


def test_model_kind_fall_consistent_with_specs_and_run_model_uses_predict_fall():
    """`freeze.model_kind` (parametre dosyasından) ile `specs.model_kind` (şartnameden) (C) için aynı: "fall" (`@ZERO` dahil; önceden
    "rule"a düşüyordu, AUDIT §8); `run_model` `predict_fall.predict`'i çağırır. Var olan INDEX modellerinin türü değişmedi."""
    for m in FAZ7C_MODEL_IDS:
        p = _preview(m)
        assert fz.model_kind(p) == specs.model_kind(m) == "fall", m
        assert fz.run_model(p, {})["kind"] == "fall"
    for e in fz.load_index()["models"]:
        p = json.loads((ROOT / "models" / e["file"]).read_text(encoding="utf-8"))
        if e["model_id"] in FAZ7C_MODEL_SPECS:
            continue
        assert fz.model_kind(p) != "fall", e["model_id"]
    zero = fz.run_model(_preview(ZERO_ROW), {})
    assert zero["status"] == fz.STATUS_PREDICTED and zero["output"]["D10"]["p_up"] == _preview(ZERO_ROW)["horizons"]["D10"]["p_up"]["value"]


def test_f3_models_include_h99_and_pooled_only():
    """SPEC_SCORING §6 / F13 / J24 kalıbı: f3'süz girdiyi reddeden (C) modelleri (h99, pooled) `F3_MODELS`'te; addsale ve `@ZERO`
    f3 istemez (en erken kayıt kuralı)."""
    assert {H99, POOLED} <= reg.F3_MODELS and not {ADDSALE, ZERO_ROW} & reg.F3_MODELS
    for m in FAZ7C_MODEL_IDS:
        refused = pf.predict(_preview(m), {"additional_sale_shares": "0", "total_demand_multiple": None, "ipo_price_tl": "10",
                                           "shares_offered": "1000000", "post_ipo_share_capital": "5000000",
                                           "capital_increase_shares": "500000"})["refused"]
        assert (refused is not None and refused["code"] == "F3_MISSING") == (m in reg.F3_MODELS), m


# ---------------------------------------------------------------- (2) canlı kayıt: (C) girdileri, TÜFE bloğu, ret yolları

@pytest.mark.requires_raw_sources
def test_live_record_carries_fall_cells_additional_sale_and_tufe(tmp_path):
    """§8 "canlı girdi şeması genişlemez": `build_record` (C) modelleri için gerekli girdileri zaten yazar — `additional_sale_shares`
    (V1.5 alanı) model_inputs'ta; `tufe` bloğu h99 ve pooled'ı da pinler (v1 ile aynı önek pini; ön koşul ortak); dört (C) hücresi
    `predict_fall.predict(önizleme, model_inputs)` ile aynı. (C) dışındaki 23 hücre (C)'siz INDEX'le kurulan kayıttakiyle aynı; kayıtta
    sonuç alanı adı yok."""
    rec = fz.build_record(reg.INPUTS_DIR / "CITAS.json", now=NOW, models_dir=_models_dir(tmp_path))
    inputs = rec["model_inputs"]
    assert inputs[pf.ADDITIONAL_SALE_FIELD] == rec["inputs"]["document"]["fields"][pf.ADDITIONAL_SALE_FIELD]["value"] == "0"
    t = rec["inputs"]["document"]["fields"]["first_trading_date"]["value"]
    want = tufe.index_for(t, tufe.load())
    pin = {"through_month": DEFLATOR["through_month"], "prefix_sha256": DEFLATOR["file_sha256"]}
    assert rec["tufe"]["pins"] == {m: pin for m in ("ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", H99, POOLED)}
    assert inputs["tufe_index"] == want["index"] and rec["tufe"]["refusal"] is None
    cells = {c["model_id"]: c for c in rec["models"]}
    assert [c["model_id"] for c in rec["models"]][-4:] == list(FAZ7C_MODEL_IDS)
    for m in FAZ7C_MODEL_IDS:
        assert cells[m]["kind"] == "fall" and cells[m]["status"] == fz.STATUS_PREDICTED, m
        assert cells[m]["output"] == pf.predict(_preview(m), inputs)
        assert cells[m]["output"]["D10"]["return"] is None and 0.0 < cells[m]["output"]["D10"]["p_up"] < 1.0
    for m in (H99, POOLED):
        assert cells[m]["output"]["tufe_index_used"] == want["index"] and cells[m]["output"]["add_sale_used"] == 0
    # SPEC_DEVIATIONS K22: skorlama kaydın (C) hücresini V1.5 yolundan okur — yalnız D5 ve D10 p_up (getiri başlığı yok); D1/D3 yok
    for m in FAZ7C_MODEL_IDS:
        assert sc.prediction_of_cell(cells[m]) == {h: {"return": None, "p_up": cells[m]["output"][h]["p_up"]} for h in ("D5", "D10")}
    (tmp_path / "b").mkdir()
    base = fz.build_record(reg.INPUTS_DIR / "CITAS.json", now=NOW, models_dir=_models_dir(tmp_path / "b", with_fall=False))
    n_base = len(base["models"])
    assert n_base == len(rec["models"]) - 4 and rec["models"][:n_base] == base["models"]
    assert base["tufe"]["pins"] == {m: pin for m in ("ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled")}
    assert not set(_keys(rec)) & OUTCOME_KEYS


@pytest.mark.requires_raw_sources
def test_live_record_refusal_paths_for_fall_models(tmp_path):
    """§9 ret yolları kayıt içinde (hücre REFUSED, kayıt yazılır): f3 boş → h99/pooled F3_MISSING, addsale ve @ZERO tahmin verir;
    ek satış boş → üç aday ADDITIONAL_SALE_MISSING (0 varsayılmaz, C4), @ZERO tahmin verir; eğitim modu açık olmadığından açık f3
    filtre durumu ret değildir; TÜFE önek pini tutmazsa deflatörlü hücreler (v1 ve (C)) TUFE_FILE_MISMATCH."""
    d = _models_dir(tmp_path)

    def cells(**fields):
        rec = fz.build_record(_inputs(tmp_path, **fields), now=NOW, models_dir=d)
        return {c["model_id"]: c for c in rec["models"]}

    c = cells(total_demand_multiple=None)
    assert {m: c[m]["refusal"]["code"] for m in (H99, POOLED)} == {H99: "F3_MISSING", POOLED: "F3_MISSING"}
    assert c[ADDSALE]["status"] == c[ZERO_ROW]["status"] == fz.STATUS_PREDICTED
    c = cells(additional_sale_shares=None)
    assert {m: c[m]["refusal"]["code"] for m in (H99, POOLED, ADDSALE)} == dict.fromkeys((H99, POOLED, ADDSALE), pf.ADDITIONAL_SALE_MISSING)
    assert c[ZERO_ROW]["status"] == fz.STATUS_PREDICTED
    # Nihai fit'lerin f3 filtre modu NOT_SPECIFIED (açık değil): açık durumlu girdi (UNFILTERED / FILTERED) uyuşmazlık sayılmaz
    # (V1.5 kuralı; uyuşmazlık reddi açık modlu JSON'la tests/test_faz7c_model.py ve donmuş JSON testlerinde).
    assert {_preview(m)["preprocessing"]["f3_filter_mode"] for m in (H99, POOLED)} == {"NOT_SPECIFIED"}
    for status in ("UNFILTERED", "FILTERED"):
        c = cells(total_demand_filter_status=status)
        assert all(c[m]["status"] == fz.STATUS_PREDICTED for m in FAZ7C_MODEL_IDS), status
    bad = copy.deepcopy(_preview(H99))
    bad["deflator"]["file_sha256"] = "0" * 64
    payload = pretty_json_bytes(bad)
    (d / f"{H99}.json").write_bytes(payload)
    index = json.loads((d / "INDEX.json").read_text(encoding="utf-8"))
    for e in index["models"]:
        if e["model_id"] == H99:
            e["sha256"] = sha256_bytes(payload)
    (d / "INDEX.json").write_bytes(pretty_json_bytes(index))
    rec = fz.build_record(reg.INPUTS_DIR / "CITAS.json", now=NOW, models_dir=d)
    c = {x["model_id"]: x for x in rec["models"]}
    assert rec["tufe"]["refusal"] == tufe.TUFE_FILE_MISMATCH and rec["model_inputs"]["tufe_index"] is None
    for m in ("ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", H99, POOLED):
        assert c[m]["refusal"]["code"] == tufe.TUFE_FILE_MISMATCH, m
    assert c[ADDSALE]["status"] == c[ZERO_ROW]["status"] == fz.STATUS_PREDICTED


@pytest.mark.requires_raw_sources
def test_record_precondition_tufe_missing_applies_with_fall_models_only(tmp_path):
    """Kayıt ön koşulu (SPEC_HAZARD_V1 §9, J26) v1 ile ortaktır ve yeniden yazılmadı: INDEX'te deflatörlü model olarak yalnız (C)
    modelleri olsa da T'nin ayı − 2 dosyada yoksa `TufeMissing`, kayıt yazılmaz; T bilinmiyorsa deflatörlü (C) hücreleri TUFE_MISSING
    ile RET, addsale ve @ZERO tahmin verir."""
    d = tmp_path / "models"
    d.mkdir()
    index = {"schema_version": fz.INDEX_SCHEMA, "models": []}
    for m in FAZ7C_MODEL_IDS:
        payload = pretty_json_bytes(_preview(m))
        (d / f"{m}.json").write_bytes(payload)
        index["models"].append(fz.index_entry(_preview(m), f"{m}.json", sha256_bytes(payload)))
    (d / "INDEX.json").write_bytes(pretty_json_bytes(index))
    late = _inputs(tmp_path, first_trading_date="2026-11-02")                     # T − 2 = 2026-09 (dosyada 2026-08'e kadar)
    with pytest.raises(fz.TufeMissing) as e:
        fz.build_record(late, now=NOW, models_dir=d)
    assert e.value.month == "2026-09" and tufe.append_command("2026-09") in str(e.value)
    rec = fz.build_record(_inputs(tmp_path, first_trading_date=None), now=NOW, models_dir=d)
    c = {x["model_id"]: x for x in rec["models"]}
    assert rec["tufe"]["refusal"] == tufe.TUFE_MISSING and {c[m]["refusal"]["code"] for m in (H99, POOLED)} == {tufe.TUFE_MISSING}
    assert c[ADDSALE]["status"] == c[ZERO_ROW]["status"] == fz.STATUS_PREDICTED


# ---------------------------------------------------------------- (3) F9: semantik testler (etiket yönü, test arzından bağımsızlık)

def _f3_driven(dataset: Dataset, seed: int = 5, flip: float = 0.15) -> Dataset:
    """Sentetik havuzun hedefleri yeniden: Y_h = 1 (kapanış > arz) ⇔ f3 > 8 (her ufuk; %15 rastgele çevrilir). Yüksek f3 ⇒ yukarı."""
    rng = random.Random(seed)
    rows = []
    for r in dataset.rows:
        f3 = r.inputs["total_demand_multiple"]
        if f3 is not None:
            targets = {}
            for h, t in r.targets.items():
                up = int(float(f3) > 8.0)
                up = 1 - up if rng.random() < flip else up
                targets[h] = Target(R="0.1" if up else "-0.1", Y=up, session_date=t.session_date, close=t.close)
            r = IPORowV2(**{**{k: getattr(r, k) for k in IPORowV2.__dataclass_fields__}, "targets": targets})
        rows.append(r)
    return Dataset(rows=tuple(rows), data_version_sha256=dataset.data_version_sha256, table_sha256=dataset.table_sha256,
                   outcome_sessions_through=dataset.outcome_sessions_through)


@pytest.mark.parametrize("model_id", [H99, POOLED])
def test_f9_high_f3_in_training_gives_higher_p_up(model_id):
    """F9 (AUDIT §7; K3 etiket yönü): eğitim satırlarında yüksek f3 yukarı kapanışla (Y_h = 1) gelir ⇒ ln f3 katsayısı pozitif ve p_up
    f3'te artar — hem backtest fold'unda (`_run_fall`, son iki skorlanabilir D10 fold'u) hem nihai fit'te (`final_fit_fall` → JSON →
    stdlib `predict_fall`, her eğitim satırında f3 = p95 > f3 = p05, D5 ve D10). Başlıklar y = 1 − Y_h ile fit edilip p_up diye
    yazılsaydı (denetimin mutasyonu p) işaret dönerdi."""
    ds, a = f7c.synthetic_fall_dataset(seed=11)
    if model_id == H99:
        ds, a = f7c.h99_subset(ds, a)
    ds = _f3_driven(ds)
    spec = f7c.synthetic_spec(model_id, ds, a)
    rows = bt.fall_training_rows(spec, ds, a, check=False)
    raw = bt.fall_raw_features(spec, rows, a)[0]
    folds = [f for f in bt.plan_fall_folds(ds, rows, raw, uses_f3=True) if f.status == bt.SCORABLE and f.horizon == "D10"]
    for part in bt._run_fall(spec, ds, folds[-2:], 1, raw):
        assert part["logit_status"] == fitmod.STATUS_FIT_OK and json.loads(part["logit_coef"])["f3"] > 0
    params = json.loads(pretty_json_bytes(bt.final_fit_fall(model_id, dataset=ds, spec=spec, add_sale=a)[0]))
    w = params["preprocessing"]["winsor"]["f3"]
    for h in ("D5", "D10"):
        head = params["horizons"][h]["p_up"]
        assert dict(zip(head["columns"], head["coef"]))["f3"] > 0, h
    for r in rows:
        inputs = {**r.inputs, "tufe_index": r.tufe_index, pf.ADDITIONAL_SALE_FIELD: a[r.ticker], "total_demand_filter_status": None}
        lo = pf.predict(params, {**inputs, "total_demand_multiple": repr(w["p05"])})
        hi = pf.predict(params, {**inputs, "total_demand_multiple": repr(w["p95"])})
        assert lo["refused"] is None and all(hi[h]["p_up"] > lo[h]["p_up"] for h in ("D5", "D10")), r.ticker


@pytest.mark.parametrize("model_id,h", [(H99, "D10"), (POOLED, "D10"), (ADDSALE, "D5")])
def test_f9_fold_fit_is_bit_equal_when_test_ipo_inputs_change(model_id, h):
    """F9 (Fable yeniden üretimi 2-i kalıbı): gerçek bir fold'da (ufkun son skorlanabilir fold'u) test arzının girdileri değişince
    (f1r × 7, f3 / 3, ek satış bayrağı çevrilmiş) ön işleme (kırpma sınırları, μ, σ, f3 filtre modu), kullanılan/dışlanan eğitim arzları,
    seçilen C, sabit, katsayılar ve iç LOOCV tablosu bit-eşit; yalnız test olasılığı değişir. Test arzının sonucu fit'e hiçbir
    argümanla verilemez (yapısal). Kırpma sınırları ya da z istatistikleri test arzını içerseydi (denetimin mutasyonu d) kırmızı."""
    ds = load_dataset() if model_id == H99 else load_dataset_v2()
    a = additional_sale_shares(ds)
    spec = FAZ7C_MODEL_SPECS[model_id]
    rows = bt.fall_training_rows(spec, ds, a, check=True)
    raw = bt.fall_raw_features(spec, rows, a)[0]
    fold = [f for f in bt.plan_fall_folds(ds, rows, raw, uses_f3="f3" in spec["features"])
            if f.horizon == h and f.status == bt.SCORABLE][-1]
    by = ds.by_ticker()
    status = {r.ticker: r.total_demand_filter_status for r in rows}
    changed = {k: dict(v) for k, v in raw.items()}
    t = changed[fold.test_ticker]
    if "f1r" in t:
        t["f1r"] = t["f1r"] * 7
    if "f3" in t:
        t["f3"] = t["f3"] / 3
    t["add_sale"] = Decimal(1) - t["add_sale"]

    def fit(r):
        return fitmod.fit_fall_horizon(list(fold.training), r, {x: by[x].targets[h].Y for x in fold.training}, status,
                                       recipe=fitmod.recipe_for(spec), grid=fitmod.fall_grid(spec), test_raw=r[fold.test_ticker],
                                       test_filter_status=status[fold.test_ticker])

    a1, a2 = fit(raw), fit(changed)
    assert a1.logit.status == a2.logit.status == fitmod.STATUS_FIT_OK
    assert (a1.order, a1.excluded) == (a2.order, a2.excluded) and a1.final.params() == a2.final.params()
    assert a1.logit.selected_C == a2.logit.selected_C and a1.logit.intercept_coef() == a2.logit.intercept_coef()
    table = lambda g: [(e.hyperparameter, e.score, e.status) for e in g.score_table]     # noqa: E731
    assert table(a1.logit) == table(a2.logit) and a1.logit.inner_fold_n == a2.logit.inner_fold_n
    assert a1.logit.probability != a2.logit.probability

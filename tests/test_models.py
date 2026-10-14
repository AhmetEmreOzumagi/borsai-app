"""K3: dondurulmuş modeller ve models/INDEX.json."""
from __future__ import annotations

import statistics

import pytest

from borsai import predict_path as pth
from borsai.fit import fit_with_estimators, select_training_rows
from borsai.freeze import INDEX_PATH, MODELS_DIR, load_index
from borsai.horizons import HORIZONS, physical_return_bounds
from borsai.provenance import identity_hash, sha256_file
from borsai.predict_fall import FALL_HORIZONS
from borsai.specs import FAZ7_MODEL_SPECS, FAZ7C_MODEL_SPECS, MODEL_SPECS, spec_sha256

import faz7_support as fs7

EXPECTED_IDS = {
    "v1_5_h99", "base_always_ceiling", "base_train_median", "base_train_mean", "base_zero", "base_rate", "base_last10_rate",
    # Faz 1B (tests/test_faz1b_models.py yeni modellerin yapısını ayrıca sınar)
    "v1_6_h99", "v1_5_market20_v0", "pb_v0", "ceiling_hazard_v0", "ceiling_hazard_v0@INF", "pb_ceiling_v0",
    "pb_ceiling_v0@INF", "base_km_expanding", "base_km_last10",
    # Faz 4 (tests/test_faz4_ceiling_path.py yapılarını ve dondurma kararını ayrıca sınar)
    "ceiling_path_v0", "ceiling_path_v0@INF", "pb_ceiling_path_v0",
}
VOLATILE = {"created_at", "code_version"}


@pytest.mark.requires_git_history
def test_index_lists_all_frozen_models_with_hashes():
    index = load_index(INDEX_PATH)
    assert index["schema_version"] == "borsai.model_index/1"
    ids = [e["model_id"] for e in index["models"]]
    # Faz 7 dondurması (SPEC_DEVIATIONS J23): dört v1 girişi sonda; Faz 7C dondurmasından sonra ardından dört (C) girişi (K19);
    # ayrıntı tests/test_faz7_frozen.py, tests/test_faz7c_frozen.py
    assert len(ids) == len(set(ids)) and set(ids) == EXPECTED_IDS | set(fs7.frozen_tail_ids())
    for e in index["models"]:
        path = MODELS_DIR / e["file"]
        assert path.name == f"{e['model_id']}.json"
        assert sha256_file(path) == e["sha256"]
        for key in ("training_n", "training_cutoff_date", "frozen_at", "spec_sha256", "status"):
            assert key in e
        assert e["status"] == "FROZEN"


def test_frozen_files_are_consistent_with_index_and_specs(frozen_models):
    index = {e["model_id"]: e for e in load_index(INDEX_PATH)["models"]}
    for model_id, params in frozen_models.items():
        e = index[model_id]
        assert params["model_id"] == model_id and params["schema_version"] == "borsai.model/1"
        assert params["training"]["n"] == e["training_n"]
        assert params["training"]["cutoff_date"] == e["training_cutoff_date"]
        assert params["created_at"] == e["frozen_at"]
        # CLAUDE.md kural 5: dondurulmuş model_id'nin şartnamesi sessizce değişemez.
        spec = (MODEL_SPECS.get(model_id) or FAZ7_MODEL_SPECS.get(model_id)                        # J21: ayrı sözlük
                or FAZ7C_MODEL_SPECS[model_id])                                                       # K: ayrı sözlük
        assert params["spec_sha256"] == spec_sha256(spec) == e["spec_sha256"]
        # tavan yolu modelleri h = 1..10 üretir (SPEC_CEILING_PATH_V0 §4); düşen arz ailesi D5 ve D10 (SPEC_C_V0 §2.3); ötekiler
        # skorlanan dört ufku
        want = (set(pth.HORIZON_KEYS) if params["algorithm"] == pth.ALGORITHM else set(FALL_HORIZONS) if model_id in FAZ7C_MODEL_SPECS
                else set(HORIZONS))
        assert set(params["horizons"]) == want


def test_training_blocks(frozen_models, dataset):
    for model_id, params in frozen_models.items():
        tr = params["training"]
        if model_id in FAZ7_MODEL_SPECS or model_id in FAZ7C_MODEL_SPECS:
            # kendi tablo/veri sürümü (havuz: training_table_v2); tests/test_faz7_frozen.py, tests/test_faz7c_frozen.py
            spec = (FAZ7_MODEL_SPECS.get(model_id) or FAZ7C_MODEL_SPECS[model_id])["training"]
            assert (tr["n"], tr["data_version_sha256"], tr["cutoff_date"]) == (spec["n"], spec["data_version_sha256"], "2026-08-19")
            assert tr["tickers_sha256"] == identity_hash(tr["tickers"])
            continue
        assert tr["data_version_sha256"] == dataset.data_version_sha256
        if MODEL_SPECS[model_id]["training"]["set"] == "NONE":
            assert tr["n"] == 0 and tr["tickers"] == [] and tr["cutoff_date"] is None
        else:  # H99_ALL_ROWS: 99 arz; H99_F3_PRESENT (ceiling_hazard_v0): f3 dolu 97 arz
            expected = [r.ticker for r in select_training_rows(MODEL_SPECS[model_id], dataset.rows)]
            assert tr["n"] == len(expected) == MODEL_SPECS[model_id]["training"]["n"] and tr["tickers"] == expected
            assert tr["tickers_sha256"] == identity_hash(expected)
            assert tr["cutoff_date"] == "2026-08-19"


def test_rule_values_recomputed_from_training_table(frozen_models, dataset):
    rows = dataset.rows
    for h in HORIZONS:
        R = [r.targets[h].R_float for r in rows]
        Y = [r.targets[h].Y for r in rows]
        hz = {m: frozen_models[m]["horizons"][h] for m in frozen_models if h in frozen_models[m]["horizons"]}
        assert hz["base_train_median"]["return"]["value"] == statistics.median(R)
        assert hz["base_train_mean"]["return"]["value"] == statistics.mean(R)
        assert hz["base_zero"]["return"]["value"] == 0.0
        assert hz["base_always_ceiling"]["return"]["value"] == physical_return_bounds(h)[1]
        assert hz["base_always_ceiling"]["p_up"]["value"] == 1.0
        assert hz["base_rate"]["p_up"]["value"] == sum(Y) / 99
        assert hz["base_last10_rate"]["p_up"]["value"] == sum(Y[-10:]) / 10


def test_v1_5_h99_refit_reproduces_frozen_parameters(frozen_models, dataset):
    """Kod + veri aynıysa dondurulmuş sayılar aynen yeniden üretilir (bu makinede)."""
    fresh, _ = fit_with_estimators(MODEL_SPECS["v1_5_h99"], list(dataset.rows), dataset_version=dataset.data_version_sha256)
    frozen = frozen_models["v1_5_h99"]
    assert {k: v for k, v in fresh.items() if k not in VOLATILE} == {k: v for k, v in frozen.items() if k not in VOLATILE}


def test_v1_5_h99_structure(frozen_models):
    m = frozen_models["v1_5_h99"]
    prep = m["preprocessing"]
    assert prep["columns"] == ["f1", "f2", "f3", "f4", "f5"]
    for key in ("winsor", "medians", "mean", "std"):
        assert prep[key]
    for h in HORIZONS:
        ret, p = m["horizons"][h]["return"], m["horizons"][h]["p_up"]
        assert ret["kind"] == "ridge" and set(ret) >= {"alpha", "intercept", "coef"} and len(ret["coef"]) == 5
        assert p["kind"] == "logit" and set(p) >= {"C", "intercept", "coef"} and len(p["coef"]) == 5
    assert set(m["feature_ranges"]) == {"f1", "f2", "f3", "f4"}
    assert m["feature_ranges"]["f4"]["min"] > 0  # f4 = 0 eğitimde yok (AUDIT §1.2-g)
    assert m["input_policy"]["f3_missing"] == "REFUSE"
    assert m["code_version"]["borsai_source_sha256"]
    assert m["runtime"]["scikit-learn"] == "1.9.0"


@pytest.mark.parametrize("model_id", sorted(EXPECTED_IDS))
def test_freeze_refuses_to_overwrite(model_id, dataset, tmp_path):
    from borsai.freeze import FreezeError, freeze

    (tmp_path / f"{model_id}.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FreezeError):
        freeze([model_id], dataset, models_dir=tmp_path)

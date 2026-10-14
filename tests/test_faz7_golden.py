"""Faz 7 (commit B): tavan serisi v1 adaylarının resmi walk-forward koşuları, altın ledger'ları, nihai fit önizlemeleri ve
MODELS.md Faz 7 bölümü (SPEC_HAZARD_V1 §5.1, §5.4, §6.2, §11-6, §11-7, §11-8, §11-11, §11-14). Bu dosyadaki testler gerçek
walk-forward'u ve nihai fit'leri koşar (commit A'dan sonra). Modeller dondurulmadı: models/ değişmez."""
from __future__ import annotations

import csv
import json
import subprocess
from dataclasses import replace

import numpy as np
import pytest

from borsai import backtest as bt
from borsai import hazard as hz
from borsai import predict_hazard as ph
from borsai import report_faz7 as r7
from borsai import survival as sv
from borsai import tufe
from borsai.data import load_dataset, load_dataset_v2
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes, sha256_file
from borsai.specs import (FAZ7_MODEL_IDS, FAZ7_MODEL_SPECS, H99_DATA_VERSION_SHA256, PLAN_CEILING, SPEC_DOCUMENTS_FAZ7,
                          V2_DATA_VERSION_SHA256, spec_sha256)

import faz7_support as fs7

CLIP, REAL, POOLED, POOLED_INF = FAZ7_MODEL_IDS
GOLDEN = bt.GOLDEN_FAZ7_DIR
COMMIT_A = "2a21a96c950579cd56f4983f72175f130c1b3bb0"      # BORSAI_FAZ7_A: resmi koşunun kodu (borsai_dirty = false)
POOLED_KM = tuple(key for key, _ in bt.POOLED_KM_RULES)
VOLATILE = ("created_at", "code_version", "runtime")


@pytest.fixture(scope="module")
def golden():
    return r7.load_faz7(GOLDEN)


@pytest.fixture(scope="module")
def rerun(tmp_path_factory):
    """Aynı kodla dört koşu; kendi geçici günlüğüne yazar (resmi günlük yalnız `faz7_golden` satırlarını taşır)."""
    log = tmp_path_factory.mktemp("faz7_log") / "log.jsonl"
    res = bt.run_faz7(log_path=log, context="pytest")
    assert len(log.read_text(encoding="utf-8").splitlines()) == len(FAZ7_MODEL_IDS)
    return res


@pytest.fixture(scope="module")
def log_entries():
    return [json.loads(x) for x in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]


def _roundtrip(obj):
    return json.loads(json.dumps(obj))


# ---------------------------------------------------------------- altın dosyalar, yeniden koşu, günlük

def test_backtest_byte_identical_to_faz7_golden(rerun, golden):
    """Koşu deterministiktir: dört ledger ve havuz planının iki KM ledger'ı altın dosyalarla bayt bayt aynı."""
    _, manifest, _ = golden
    assert list(rerun) == list(FAZ7_MODEL_IDS)
    for m, res in rerun.items():
        assert res.ledger_csv == (GOLDEN / bt.golden_filename(m)).read_bytes(), m
        assert res.log_entry["ledger_sha256"] == manifest["runs"][m]["ledger_sha256"]
        for key, (_, payload) in res.comparators.items():
            assert payload == (GOLDEN / bt.golden_filename(key)).read_bytes(), key
    assert set(rerun[POOLED].comparators) == set(POOLED_KM)
    assert not rerun[CLIP].comparators and not rerun[REAL].comparators and not rerun[POOLED_INF].comparators


@pytest.mark.requires_git_history
def test_manifest_and_sha256sums(golden):
    _, manifest, _ = golden
    files = {v["file"]: v["ledger_sha256"] for v in manifest["runs"].values()}
    files.update({v["file"]: v["sha256"] for v in manifest["final_fit_previews"].values()})
    assert len(files) == 4 + 2 + 4
    for name, sha in files.items():
        assert sha256_file(GOLDEN / name) == sha, name
    lines = (GOLDEN / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert sorted(lines) == sorted(f"{sha}  {name}" for name, sha in files.items())
    assert sorted(p.name for p in GOLDEN.iterdir()) == sorted([*files, "MANIFEST.json", "SHA256SUMS"])
    assert set(manifest["runs"]) == set(FAZ7_MODEL_IDS) | set(POOLED_KM) and set(manifest["final_fit_previews"]) == set(FAZ7_MODEL_IDS)
    for m in FAZ7_MODEL_IDS:
        info = manifest["runs"][m]
        assert info["spec_sha256"] == spec_sha256(FAZ7_MODEL_SPECS[m]) and info["plan_id"] == FAZ7_MODEL_SPECS[m]["plan_id"]
        assert info["data_version_sha256"] == FAZ7_MODEL_SPECS[m]["training"]["data_version_sha256"]
    for key in POOLED_KM:
        assert manifest["runs"][key]["computed_in_run"] == POOLED and manifest["runs"][key]["plan_id"] == FAZ7_MODEL_SPECS[POOLED]["plan_id"]
    assert manifest["comparator_ledgers"] == bt.FAZ7_COMPARATOR_LEDGERS
    # K1 (Fable denetimi B1; SPEC_DEVIATIONS J23): altın dizin `faz7_golden_b1` koşusuyla yeniden yazıldı; kod düzeltmesi ve altın
    # dosyalar aynı commit'te (K) olduğu için koşu anında borsai/ kirliydi: MANIFEST'in borsai_source_sha256'sı o commit'in
    # borsai/ ağacıdır. İlk yazım (70b67d1) commit A'nın temiz koduyla.
    first = json.loads(subprocess.run(["git", "show", f"{fs7.PRE_B1_GOLDEN_COMMIT}:tests/reference/macos_golden_faz7/MANIFEST.json"],
                                      cwd=ROOT, check=True, capture_output=True).stdout)
    assert first["borsai_dirty"] is False and first["git_commit"] == COMMIT_A
    assert manifest["git_commit"] == fs7.B1_PARENT_COMMIT and manifest["borsai_dirty"] is True
    assert fs7.code_sha_matches_introducing_commit(manifest["borsai_source_sha256"], "tests/reference/macos_golden_faz7/MANIFEST.json",
                                                   manifest["created_at"])
    assert {k: v["sha256"] for k, v in manifest["final_fit_previews"].items()} == \
        {k: v["sha256"] for k, v in first["final_fit_previews"].items()}              # önizlemeler B1'den etkilenmez


@pytest.mark.requires_git_history
def test_official_log_has_one_line_per_model(golden, log_entries, rerun):
    """§11-14: her koşu günlükte bir satır; spec_sha256 şartname sözlüğünün, spec_document_sha256 şartname dosyasının sha256'sı;
    data_version_sha256 pooled için v2; metrikler ve yakın dönem hücresi yeniden koşuyla aynı. Model başına iki resmi satır: commit
    B'nin `faz7_golden` koşusu (commit A'nın temiz kodu; ledger'ı 70b67d1'deki altın dosya) ve K1'in `faz7_golden_b1` koşusu (B1:
    `test_clipped` herhangi bir sütun; altın dizin buna bağlı). İkisinin metrikleri, yakın dönem hücresi ve öteki özetleri aynı:
    B1 yalnız o sütunu değiştirdi (SPEC_DEVIATIONS J23); varyant sayacı (model_id, spec_sha256) değişmez."""
    _, manifest, _ = golden
    for m in FAZ7_MODEL_IDS:
        hits = [e for e in log_entries if e.get("model_id") == m]
        assert [e["context"] for e in hits] == ["faz7_golden", fs7.B1_CONTEXT], m
        old, e = hits
        for x in hits:
            assert x["kind"] == "backtest" and x["plan_id"] == FAZ7_MODEL_SPECS[m]["plan_id"]
            assert x["spec_sha256"] == spec_sha256(FAZ7_MODEL_SPECS[m])
            assert x["spec_document_sha256"] == SPEC_DOCUMENTS_FAZ7["SPEC_HAZARD_V1"]["sha256"]
            assert x["decisions_document_sha256"] == SPEC_DOCUMENTS_FAZ7["KARARLAR_FAZ7"]["sha256"]
            assert x["data_version_sha256"] == (V2_DATA_VERSION_SHA256 if "pooled" in m else H99_DATA_VERSION_SHA256)
            assert x["evaluated"] == [{"run_key": k, "ledger_sha256": v["sha256"]} for k, v in bt.FAZ7_COMPARATOR_LEDGERS.items()]
        assert old["borsai_dirty"] is False and old["git_commit"] == COMMIT_A
        old_file = subprocess.run(["git", "show", f"{fs7.PRE_B1_GOLDEN_COMMIT}:tests/reference/macos_golden_faz7/{bt.golden_filename(m)}"],
                                  cwd=ROOT, check=True, capture_output=True).stdout
        assert old["ledger_sha256"] == sha256_bytes(old_file)
        assert e["ledger_sha256"] == manifest["runs"][m]["ledger_sha256"] and e["started_at"] == manifest["runs"][m]["log_entry"]["started_at"]
        assert e["git_commit"] == fs7.B1_PARENT_COMMIT and e["borsai_dirty"] is True
        assert fs7.code_sha_matches_introducing_commit(e["borsai_source_sha256"], "experiments/log.jsonl", e["started_at"])
        assert (old["ledger_sha256"] == e["ledger_sha256"]) == (m == POOLED_INF)      # @INF'in kırpması yok: ledger aynı
        fresh = rerun[m].log_entry
        for key in ("metrics", "near_era", "folds_total", "folds_scorable", "tufe", "filter_excluded_folds", "comparator_ledgers"):
            assert old.get(key) == e.get(key) == _roundtrip(fresh.get(key)), (m, key)
    assert "tufe" not in next(e for e in log_entries if e.get("model_id") == CLIP)
    for m in (REAL, POOLED):
        pin = next(e for e in log_entries if e.get("model_id") == m)["tufe"]
        assert pin["prefix_sha256"] == FAZ7_MODEL_SPECS[m]["deflator"]["file_sha256"]
        tufe.verify_pin(tufe.load(), pin)                   # ay eklemesi serbest; önek değişirse TUFE_FILE_MISMATCH
    assert fs7.faz7_variants(H99_DATA_VERSION_SHA256) == fs7.faz7_variants(V2_DATA_VERSION_SHA256) == 2


@pytest.mark.requires_git_history
def test_b1_changed_only_test_clipped_any_feature():
    """Fable denetimi B1 (SPEC_HAZARD_V1 §3.1: `clipped` herhangi bir sütun kırpıldıysa): altın ledger'larda eski sürümden (70b67d1)
    yalnız `test_clipped` sütunu değişti (FALSE → TRUE); herhangi-sütun sayıları 35 / 36 / 23 (yalnız f3: 20 / 20 / 7); @INF ve havuz
    KM ledger'ları bayt-eşit; bayrak `test_clipped_features`'ın boş olmamasıyla aynı."""
    import csv as _csv
    import io as _io

    def rows(payload):
        return list(_csv.DictReader(_io.StringIO(payload.decode("utf-8"), newline="")))

    want = {CLIP: (35, 20), REAL: (36, 20), POOLED: (23, 7), POOLED_INF: (0, 0)}
    for key in (*FAZ7_MODEL_IDS, *POOLED_KM):
        name = bt.golden_filename(key)
        old = subprocess.run(["git", "show", f"{fs7.PRE_B1_GOLDEN_COMMIT}:tests/reference/macos_golden_faz7/{name}"], cwd=ROOT,
                             check=True, capture_output=True).stdout
        new = (GOLDEN / name).read_bytes()
        if key not in (CLIP, REAL, POOLED):
            assert new == old, key
            continue
        a, b = rows(old), rows(new)
        assert list(a[0]) == list(b[0]) and len(a) == len(b)
        assert {c for x, y in zip(a, b) for c in x if x[c] != y[c]} == {"test_clipped"}
        assert {(x["test_clipped"], y["test_clipped"]) for x, y in zip(a, b) if x != y} == {("FALSE", "TRUE")}
    for m, (n_any, n_f3) in want.items():
        r = rows((GOLDEN / bt.golden_filename(m)).read_bytes())
        assert sum(x["test_clipped"] == "TRUE" for x in r) == n_any
        assert sum(bool(x["test_clipped_features"]) and "f3" in json.loads(x["test_clipped_features"]) for x in r) == n_f3
        assert all((x["test_clipped"] == "TRUE") == bool(json.loads(x["test_clipped_features"] or "[]")) for x in r)


# ---------------------------------------------------------------- fold planları, sızıntı, TÜFE (§11-5, §11-7)

def test_ledger_fold_sets_statuses_and_leakage(golden):
    """§11-7: clip ve real ticker kümesi = v0'ın 87'si; pooled 87'nin hepsini içerir (97); yakın dönem 78 ticker üçünde aynı
    (22 ay bloğu); her fold'da max(eğitim seans tarihi) < T (açık üyeler dahil); pooled fold'larında test r = 0."""
    runs = golden[0]
    v0 = [r["ticker"] for r in bt.read_pinned_ledger(bt.FAZ7_COMPARATOR_LEDGERS["ceiling_hazard_v0"])]
    assert len(v0) == 87
    assert [r["ticker"] for r in runs[CLIP]] == [r["ticker"] for r in runs[REAL]] == v0
    pooled = [r["ticker"] for r in runs[POOLED]]
    assert len(pooled) == 97 and set(v0) <= set(pooled) and pooled == [r["ticker"] for r in runs[POOLED_INF]]
    near = [{r["ticker"] for r in runs[m] if r["first_trading_date"] >= bt.NEAR_ERA_START} for m in (CLIP, REAL, POOLED, POOLED_INF)]
    assert all(s == near[0] for s in near) and len(near[0]) == 78
    assert len({r["first_trading_date"][:7] for r in runs[CLIP] if r["ticker"] in near[0]}) == 22
    for m in FAZ7_MODEL_IDS:
        for r in runs[m]:
            assert r["status"] == hz.STATUS_FIT_OK and r["training_max_session_date"] < r["first_trading_date"], m
    for m in (POOLED, POOLED_INF):
        assert {r["test_r_pre_equal"] for r in runs[m]} == {"0.0"}
        assert {int(r["training_n_oot_open"]) for r in runs[m]} <= set(range(60, 69))
        assert sum(1 for r in runs[m] if int(r["training_n_filter_excluded"]) > 0) == 44


def test_tufe_month_and_index_in_ledgers(golden):
    """§11-5: real ve pooled ledger'larındaki test arzının TÜFE ayı T'nin m − 2'si, endeksi dosyadaki değer; yayım T'den önce."""
    runs = golden[0]
    table = tufe.load()
    for m in (REAL, POOLED):
        for r in runs[m]:
            t = tufe.index_for(r["first_trading_date"], table)
            assert r["test_tufe_month"] == t["month"] == tufe.month_for(r["first_trading_date"])
            assert r["test_tufe_index"] == t["index"] and t["release_date"] < r["first_trading_date"]
    assert "test_tufe_month" not in runs[CLIP][0] and "test_tufe_month" not in runs[POOLED_INF][0]


def test_deflator_is_the_only_difference_between_clip_and_real(golden):
    """Merdivenin (b) basamağı: v1_real'in fold hesabı f1r := f1 (TÜFE sabit 100) ile koşulunca v1_clip ledger'ının seçilen λ'ları
    ve S eğrileri bit-eşit çıkar; iki aday arasındaki fark yalnız deflatördür."""
    runs = golden[0]
    h99 = load_dataset()
    raw_clip = bt.v1_raw_features(FAZ7_MODEL_SPECS[CLIP], list(h99.rows))[0]
    raw = {t: {"f1r": v["f1"], "f2": v["f2"], "f3": v["f3"]} for t, v in raw_clip.items()}
    folds = [f for f in bt.plan_ceiling_folds(h99, PLAN_CEILING) if f.status == bt.SCORABLE]
    parts = bt._run_hazard_v1(FAZ7_MODEL_SPECS[REAL], h99, folds, bt.default_workers(), raw, None)
    ref = {r["ticker"]: r for r in runs[CLIP]}
    assert [f.test_ticker for f in folds] == [r["ticker"] for r in runs[CLIP]]
    for f, p in zip(folds, parts):
        g = ref[f.test_ticker]
        assert bt._fmt(p["selected_lambda"]) == g["selected_lambda"]
        assert [bt._fmt(p[f"S_{k}"]) for k in range(1, 11)] == [g[f"S_{k}"] for k in range(1, 11)]


def test_pooled_plan_on_h99_rows_reproduces_real(golden):
    """Merdivenin (c) basamağının yolu: PLAN_CEILING_POOLED + training_table_v2 yalnız H99 satırlarıyla, rejimsiz ve v1_real
    özellikleriyle koşulunca fold'lar PLAN_CEILING'in skorlanabilir 87'si (aynı eğitim kümesi ve PP sha'sı) ve ledger v1_real'in
    λ'ları ve S eğrileriyle bit-eşit. (c)'nin payı yalnız açık küme satırları ve rejim teriminden gelir."""
    runs = golden[0]
    h99 = load_dataset()
    base = [f for f in bt.plan_ceiling_folds(h99, PLAN_CEILING) if f.status == bt.SCORABLE]
    v2 = load_dataset_v2()
    only = replace(v2, rows=tuple(r for r in v2.rows if r.cohort == "H99"))
    raw = bt.v1_raw_features(FAZ7_MODEL_SPECS[REAL], list(only.rows))[0]
    folds = [f for f in bt.plan_pooled_folds(only, raw) if f.status == bt.SCORABLE]
    key = lambda f: (f.test_ticker, f.training, f.pp_sha256, f.n_pp_rows, f.n_events, f.max_session_date)   # noqa: E731
    assert [key(f) for f in folds] == [key(f) for f in base] and all(f.n_oot_open == 0 for f in folds)
    parts = bt._run_hazard_v1(FAZ7_MODEL_SPECS[REAL], only, folds, bt.default_workers(), raw, None)
    ref = {r["ticker"]: r for r in runs[REAL]}
    for f, p in zip(folds, parts):
        g = ref[f.test_ticker]
        assert bt._fmt(p["selected_lambda"]) == g["selected_lambda"]
        assert [bt._fmt(p[f"S_{k}"]) for k in range(1, 11)] == [g[f"S_{k}"] for k in range(1, 11)]


# ---------------------------------------------------------------- hücreler, etiketler, MODELS.md (§5.1, §5.4, §6.2, §11-8)

def test_near_era_cells_labels_and_v0_comparator(golden, log_entries):
    runs = golden[0]
    cmp = r7.comparators()
    assert abs(bt.v0_mean_rps(cmp["ceiling_hazard_v0"]) - bt.V0_PUBLISHED_MEAN_RPS) <= 5e-5
    ev = r7.evaluate(runs, cmp)
    for m in FAZ7_MODEL_IDS:
        c = ev["near"][m]
        assert (c["n"], c["n_months"]) == (78, 22) and c["label"] == bt.near_era_label(c["ci95"])
        logged = next(e for e in log_entries if e.get("model_id") == m)["near_era"]
        assert logged == _roundtrip({k: c[k] for k in logged})
    for a, b, _ in r7.LADDER:
        assert ev["ladder"][(a, b)]["n"] == 78
    assert [r["position"] for r in ev["rows62"]] == [r7.position(r["cell"]["mean"], r["lo"], r["hi"]) for r in ev["rows62"]]


def test_models_md_faz7_section(golden):
    runs = golden[0]
    ev = r7.evaluate(runs, r7.comparators())
    text = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
    head7, head4, head5 = "## Faz 7: tavan serisi v1", "## Faz 4: tavan yolu modelleri", "## Faz 5: D1 sonrası güncelleme"
    assert text.count(head7) == 1 and text.index(head4) < text.index(head7) < text.index(head5)
    section = text.split(head7)[1].split(head5)[0]
    for rule in r7.OPERATIONAL_RULES_FAZ7:
        assert rule in section
    for heading in ("### Kartlar", "### Yakın dönem birincil hücreleri", "### İkincil hücreler (ilan edilmiş", "### Merdiven (§5.4",
                    "### Keşif (hüküm yok)", "### Fold özeti", "### Nihai fit önizlemesi (dondurulmadı)",
                    "### Faz 7 koşuları ve deney günlüğü"):
        assert heading in section
    for m in r7.CANDIDATES:
        assert f"| `{m}` **(BİRİNCİL)** |" in section
    # dondurmadan sonra (BORSAI_FAZ7_FREEZE) bölümün sonunda "### Dondurma" notu: bir "kasa: bekliyor" satırı daha
    assert section.count("kasa: bekliyor") == 4 + (1 if r7.frozen_entries() else 0) and "henüz dondurulmadı" in section
    for r in ev["rows62"]:
        if r["comparator"] == r7.PRIMARY_COMPARATOR:
            row = f"| {r['raw']['beklenen']} | {r['raw']['aralik']} | {r['raw']['etiket']} | {r7.position_text(r['position'])} |"
        else:
            row = f"§6.2 {r['raw']['beklenen']} {r['raw']['aralik']} → {r7.position_text(r['position'])}"
        assert row in section, r["raw"]["aday"]
    for _, _, name in r7.LADDER:
        assert f"- {name} (" in section


# ---------------------------------------------------------------- nihai fit önizlemeleri (§11-6, §11-11)

def test_regime_fit_lambda_1e9_matches_inf_on_real_data(golden):
    """§11-6 (gerçek veri, 165 arz): v1_pooled λ = 1e9 → ‖β‖ ≤ 1e-6, |δ| > 1e-3 ve λ = INF (γ, δ) Newton çözümüne |Δ| ≤ 1e-6;
    INF çözümü `ceiling_hazard_v1_pooled@INF` önizlemesinin (γ, δ)'sıyla |Δ| ≤ 1e-12."""
    preview = golden[2][POOLED_INF]
    rows = [r for r in load_dataset_v2().rows if r.inputs["total_demand_multiple"] is not None]
    spec = FAZ7_MODEL_SPECS[POOLED]
    raw = bt.v1_raw_features(spec, rows)[0]
    status = {r.ticker: r.total_demand_filter_status for r in rows}
    kw = dict(cutoff=None, features=tuple(spec["features"]), recipe=bt.fitmod.recipe_for(spec), regime=bt.v1_regime(rows),
              r_columns=(bt.REGIME_COLUMN,))
    units = [sv.unit_of(r) for r in rows]
    big = hz.fit_training_set(units, raw, status, grid=(1e9,), **kw)
    inf = hz.fit_training_set(units, raw, status, grid=(hz.INF,), **kw)
    assert big.status == inf.status == hz.STATUS_FIT_OK and (inf.n_ipo, inf.n_pp_rows, inf.n_events) == (165, 880, 142)
    assert float(np.linalg.norm(big.fit.beta)) <= 1e-6 and abs(float(big.fit.delta[0])) > 1e-3
    theta_big = np.concatenate([big.fit.gamma, big.fit.delta])
    theta_inf = np.concatenate([inf.fit.gamma, inf.fit.delta])
    assert float(np.max(np.abs(theta_big - theta_inf))) <= 1e-6
    ref = np.array([*preview["gamma"], preview["regime"]["delta"]])
    assert float(np.max(np.abs(theta_inf - ref))) <= 1e-12


@pytest.mark.parametrize("model_id", list(FAZ7_MODEL_IDS))
def test_final_fit_preview_reproducible_and_stdlib_parity(model_id, golden):
    """§11-11: önizleme `final_fit_v1`'in yeniden koşusuyla (created_at, code_version, runtime dışında) aynı; eğitim arzlarının
    hepsinde stdlib `predict_hazard.predict` (JSON) ile numpy nihai fit |Δ| ≤ 1e-12 (hazard, S, P_L, P_close)."""
    preview = golden[2][model_id]
    params, res = bt.final_fit_v1(model_id)
    strip = lambda d: {k: v for k, v in json.loads(pretty_json_bytes(dict(d))).items() if k not in VOLATILE}   # noqa: E731
    assert strip(params) == strip(preview)
    spec = FAZ7_MODEL_SPECS[model_id]
    assert preview["spec_sha256"] == spec_sha256(spec) and preview["model_id"] == model_id
    ds = bt.v1_dataset(model_id)
    rows = [r for r in ds.rows if r.inputs["total_demand_multiple"] is not None]
    raw, info = bt.v1_raw_features(spec, rows) if spec["features"] else ({r.ticker: {} for r in rows}, {})
    worst, n = 0.0, 0
    for r in rows:
        inputs = dict(r.inputs)
        if "f1r" in spec["features"]:
            inputs["tufe_index"] = info[r.ticker]["index"]
        if "regime" in preview and r.cohort != "H99":
            inputs["alloc_regime"] = r.alloc_regime
        out = ph.predict(preview, inputs)
        assert out["refused"] is None
        test_r = {bt.REGIME_COLUMN: float(ph.regime_value(r.alloc_regime))} if "regime" in preview else None
        num = res.predict(raw[r.ticker], r.total_demand_filter_status, test_r)
        for a, b in (("hazard", "hazards"), ("S", "S"), ("P_L", "P_L"), ("P_close_ceiling", "P_close")):
            worst = max(worst, max(abs(x - y) for x, y in zip(out[a], num[b])))
        n += 1
    assert n == spec["training"]["n"] and worst <= 1e-12


def test_pooled_at_inf_differs_from_v0_at_inf(golden):
    """§11-11: v1_pooled@INF farklı (havuz + δ) ve ayrı satırdır; canlı girdide r = 0."""
    frozen = json.loads((ROOT / "models" / "ceiling_hazard_v0@INF.json").read_text(encoding="utf-8"))
    p = golden[2][POOLED_INF]
    assert p["gamma"] != frozen["gamma"] and p["regime"]["delta"] != 0.0 and p["beta"] == {}
    live = ph.predict(p, {})
    assert live["regime_value_used"] == 0 and live["S"] != ph.predict(frozen, {})["S"]


@pytest.mark.requires_git_history
def test_models_dir_unchanged():
    """K2: önizlemeler models/'e yazılmadı; INDEX'ler ve models/ çalışma ağacında değişmedi. Dondurmadan (BORSAI_FAZ7_FREEZE)
    sonra models/'de yalnız dört v1 dosyası ve INDEX.json'un sonundaki dört girişi vardır (ilk 19 giriş aynen; donmuş dosyaların
    kendisi tests/test_faz7_frozen.py); INDEX_POST_D1.json v1 taşımaz."""
    import faz7_support as fs7

    frozen = fs7.frozen_faz7_ids()
    names = sorted(x.name for x in (ROOT / "models").iterdir() if x.is_file())
    assert [n for n in names if n.startswith("ceiling_hazard_v1")] == sorted(f"{m}.json" for m in frozen)
    entries = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]
    assert [e["model_id"] for e in entries if e["model_id"] in FAZ7_MODEL_SPECS] == frozen
    entries = json.loads((ROOT / "models" / "INDEX_POST_D1.json").read_text(encoding="utf-8"))["models"]
    assert not any(e["model_id"] in FAZ7_MODEL_SPECS for e in entries)
    status = subprocess.run(["git", "status", "--porcelain", "--", "models"], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    assert status == ""


def test_golden_ledger_columns():
    """Ledger sütunları: pooled ve @INF açık küme / filtre dışlaması / rejim sütunlarını, real ve pooled TÜFE sütunlarını taşır."""
    def header(m):
        with (GOLDEN / bt.golden_filename(m)).open(encoding="utf-8", newline="") as fh:
            return next(csv.reader(fh))
    for m in FAZ7_MODEL_IDS:
        cols = header(m)
        pooled = "pooled" in m
        assert ("training_n_oot_open" in cols) == pooled and ("delta_r_pre_equal" in cols) == pooled
        assert ("test_r_pre_equal" in cols) == pooled and ("test_tufe_month" in cols) == (m in (REAL, POOLED))
        assert "test_clipped_features" in cols and cols[0] == "model_id"

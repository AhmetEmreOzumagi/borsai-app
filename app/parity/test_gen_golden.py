"""U1 (Python tarafı, SPEC_APP §5.1): gen_golden.py yalnız stdlib predict yolunu import eder
(numpy/scikit-learn yüklenirse kırmızı; tests/test_predict.py yöntemi: alt süreçte sys.modules
taraması), altın dosyalar bayt bayt yeniden üretilebilir ve kayıtlı her model için ≥ 200 satır var.
EK 2 P1'den sonra üç tavan yolu modelinin ayrıca koşullu karışım dosyası vardır; EK 3 P1'den sonra küme 23
modeldir (son dördü Faz 7 `ceiling_hazard_v1`). Eski kohort açık küme satırları kodsuzdur ve kasa (SEALED) üyesinin
hiçbir kodu altın dosyalarda geçmez (sayı ile sınanır; kod basılmaz). EK 3 P2: ikinci dizinin `post_d1_hazard_v0`'ı ayrı
dosyada, sentetik D_1 bloklarıyla (sonuç dosyası okunmaz). EK 3 P4: küme 27 (son dördü Faz 7C düşen arz `fall_d10_v0`).

  .venv/bin/pytest -q app/parity/test_gen_golden.py      (repo kökünden)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def test_generator_imports_only_stdlib_predict_path():
    code = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(HERE)!r})\n"
        "import gen_golden as g\n"
        "files = g.generate()\n"
        "assert len(files) >= 19\n"
        "print(json.dumps(sorted(m for m in sys.modules if m.split('.')[0] in g.BANNED_MODULES)))\n"
    )
    res = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert json.loads(res.stdout.strip().splitlines()[-1]) == []


def test_golden_files_are_reproducible():
    res = subprocess.run([sys.executable, str(HERE / "gen_golden.py"), "--check"], cwd=ROOT,
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr


def test_every_pinned_model_has_at_least_200_rows():
    sys.path.insert(0, str(HERE))
    import gen_golden as g

    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
    assert tuple(e["model_id"] for e in index["models"][: len(g.PINNED_MODEL_IDS)]) == g.PINNED_MODEL_IDS
    manifest = json.loads((HERE / "golden" / "MANIFEST.json").read_text(encoding="utf-8"))
    assert tuple(manifest["model_ids"]) == g.PINNED_MODEL_IDS
    for mid in g.PINNED_MODEL_IDS:
        rows = (HERE / "golden" / f"{mid}.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(rows) >= 200, mid
        assert all(json.loads(r)["model_id"] == mid for r in rows)


def test_ceiling_path_models_have_conditional_files():
    """EK 2 §3.1/§3.4: üç tavan yolu modeli ≥ 450 satır + 40 taban satırlı koşullu dosya."""
    sys.path.insert(0, str(HERE))
    import gen_golden as g

    assert g.PATH_IDS == ("ceiling_path_v0", "ceiling_path_v0@INF", "pb_ceiling_path_v0")
    assert set(g.PATH_IDS) <= set(g.PINNED_MODEL_IDS)
    manifest = json.loads((HERE / "golden" / "MANIFEST.json").read_text(encoding="utf-8"))
    for mid in g.PATH_IDS:
        rows = (HERE / "golden" / f"{mid}.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(rows) >= 450, (mid, len(rows))
        cond = (HERE / "golden" / f"{mid}.conditional.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(cond) == g.N_COND_BASE, (mid, len(cond))
        assert manifest["conditional_rows"][mid] == len(cond)
        first = json.loads(cond[0])
        assert len(first["streak_ongoing"]) == 10
        assert len(first["streak_ongoing_mismatch"]) == 3
        assert len(first["after_break"]) == 10
        assert first["output"]["limit_path"] is not None
    # borsai/predict_path.py portun tanımına girdi
    assert "borsai/predict_path.py" in g.PREDICT_SOURCES
    assert "borsai/predict_path.py" in manifest["predict_sources_sha256"]


V1_IDS = ("ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF")


def test_v1_models_pinned_with_at_least_600_rows():
    """EK 3 §4.1–§4.2 (U53): küme 23; dört v1 dosyası ≥ 600 satır; TÜFE kaynağı ve pin MANIFEST'te; 9 kaynak dosya."""
    sys.path.insert(0, str(HERE))
    import gen_golden as g

    assert len(g.PINNED_MODEL_IDS) == 27 and g.PINNED_MODEL_IDS[19:23] == V1_IDS == g.V1_IDS
    manifest = json.loads((HERE / "golden" / "MANIFEST.json").read_text(encoding="utf-8"))
    for mid in V1_IDS:
        assert manifest["rows"][mid] >= 600, (mid, manifest["rows"][mid])
    assert "borsai/tufe.py" in manifest["predict_sources_sha256"] and len(manifest["predict_sources_sha256"]) == 11
    specs = (ROOT / "borsai" / "specs.py").read_text(encoding="utf-8")
    assert manifest["tufe_prefix_sha256"] in specs and manifest["tufe_through_month"] in specs
    assert manifest["oot_open_rows"] == 71 and manifest["oot_sealed_rows_excluded_by_guard"] is True
    assert manifest["patched_rows"] == 61


def test_no_sealed_code_in_golden():
    """Hijyen (EK 3 §4.2): kasa (SEALED) üyelerinin kodu hiçbir altın dosyada geçmez; açık küme satırları kodsuzdur
    (case_id `<model>/oot/<sıra>`, girdide ticker yok). Kod kümeleri yerel değişkendir: hata çıktısı yalnız sayı basar."""
    sys.path.insert(0, str(ROOT))
    from borsai import registry as reg

    _, rows = reg.read_cohort()
    members = reg.cohort_members(rows)
    sealed = sorted(r["ticker"] for r in members if r["vault"] == reg.VAULT_SEALED)
    opn = sorted(r["ticker"] for r in members if reg.is_open(r["vault"]))
    n_sealed = len(sealed)
    assert n_sealed == 64
    pattern = re.compile(r"\b(" + "|".join(sealed) + r")\b")
    open_pattern = re.compile(r"\b(" + "|".join(opn) + r")\b")
    files = sorted((HERE / "golden").glob("*.json*")) + [HERE / "dec_cases.json", HERE / "tufe_cases.json"]
    hits = {p.name: len(set(pattern.findall(p.read_text(encoding="utf-8")))) for p in files}
    assert sum(hits.values()) == 0, {k: v for k, v in hits.items() if v}
    n_oot = 0
    for mid in V1_IDS:
        for line in (HERE / "golden" / f"{mid}.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if "/oot/" not in row["case_id"]:
                continue
            n_oot += 1
            assert "ticker" not in row["inputs"] and not open_pattern.search(line), row["case_id"]
            assert row["inputs"]["alloc_regime"] in ("PRE_20211111", "THRESH100_20211111", "EQUAL_DIST_20230330")
    assert n_oot == 4 * 71
    # (C) açık küme satırları da kodsuz; rejim anahtarı verilmez ((C)'de rejim yok)
    n_fall = 0
    for mid in FALL_IDS:
        for line in (HERE / "golden" / f"{mid}.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if "/oot/" not in row["case_id"]:
                continue
            n_fall += 1
            assert "ticker" not in row["inputs"] and "alloc_regime" not in row["inputs"], row["case_id"]
            assert not open_pattern.search(line), row["case_id"]
    assert n_fall == 4 * 71


def test_post_d1_golden_pinned():
    """EK 3 §6.4 (U64 Python tarafı): ikinci dizin sabit listeyle aynı; ≥ 220 satır, her satır sentetik `d1` bloğu ve
    `path_params` bayrağı taşır; sonuç dosyası (data/outcomes*) okunmaz; yamalı 8 satır dosyanın SONUNDA; kaynak pini."""
    sys.path.insert(0, str(HERE))
    import gen_golden as g

    index = json.loads((ROOT / "models" / "INDEX_POST_D1.json").read_text(encoding="utf-8"))
    assert tuple(e["model_id"] for e in index["models"]) == g.PINNED_POST_D1_MODEL_IDS == ("post_d1_hazard_v0",)
    manifest = json.loads((HERE / "golden" / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["post_d1_model_ids"] == ["post_d1_hazard_v0"]
    assert "borsai/predict_post_d1.py" in manifest["predict_sources_sha256"]
    rows = [json.loads(r) for r in (HERE / "golden" / "post_d1_hazard_v0.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == manifest["post_d1_rows"]["post_d1_hazard_v0"] >= 220
    assert all(set(r["d1"]) >= {"half_day", "halt_flag"} and isinstance(r["path_params"], bool) for r in rows)
    # tek uç satır (`not_traded:no_fields`) fields_raw taşımaz
    assert [r["tags"][0] for r in rows if "fields_raw" not in r["d1"]] == ["edge:post_d1:not_traded:no_fields"]
    assert sum(1 for r in rows if not r["path_params"]) >= 2
    src = (HERE / "gen_golden.py").read_text(encoding="utf-8")
    assert "outcomes" not in src.replace("Sonuç dosyaları (data/outcomes*/) OKUNMAZ", "")
    patched = [json.loads(r) for r in (HERE / "golden" / "_patched_params.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["model_id"] for r in patched[43:51]] == ["post_d1_hazard_v0"] * 8
    assert all(r["model_id"] != "post_d1_hazard_v0" for r in patched[:43])


FALL_IDS = ("fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO")
FALL_OUTPUT_KEYS = ["model_id", "D5", "D10", "warnings", "refused", "clipped", "clipped_features", "f1r_raw", "tufe_index_used",
                    "add_sale_used"]


def test_fall_models_pinned():
    """EK 3 §8.3 (U77 Python tarafı): küme 27, son dördü (C); her (C) dosyası ≥ 560 satır; `predict_fall.py` portun tanımına
    girdi (11 kaynak); açık küme satırları 71 (kodsuz); yamalı 10 satır dosyanın SONUNDA (ilk 51 satır P2 ile aynı kalır);
    çıktı anahtar kümesi Python'unki (sıra `fall_semantics.rs`'te) ve ufuk hücrelerinde getiri alanları null."""
    sys.path.insert(0, str(HERE))
    import gen_golden as g

    assert g.FALL_IDS == FALL_IDS == g.PINNED_MODEL_IDS[23:]
    manifest = json.loads((HERE / "golden" / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["fall_model_ids"] == list(FALL_IDS) and manifest["fall_oot_open_rows"] == 71
    assert "borsai/predict_fall.py" in g.PREDICT_SOURCES and "borsai/predict_fall.py" in manifest["predict_sources_sha256"]
    for mid in FALL_IDS:
        rows = [json.loads(r) for r in (HERE / "golden" / f"{mid}.jsonl").read_text(encoding="utf-8").splitlines()]
        assert len(rows) == manifest["rows"][mid] >= 560, (mid, len(rows))
        for r in rows:
            out = r["expected"].get("output")
            if out is None:
                continue
            assert sorted(out) == sorted(FALL_OUTPUT_KEYS), r["case_id"]     # dosya sort_keys ile yazılır; sıra Rust testinde
            for h in ("D5", "D10"):
                if out[h] is not None:
                    assert all(out[h][k] is None for k in ("return", "return_unclipped", "return_clipped", "price")), r["case_id"]
    patched = [json.loads(r) for r in (HERE / "golden" / "_patched_params.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(patched) == 61 and all(r["model_id"] in FALL_IDS for r in patched[51:])
    assert all(r["model_id"] not in FALL_IDS for r in patched[:51])

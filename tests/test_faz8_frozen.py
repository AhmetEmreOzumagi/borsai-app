"""Faz 8 dondurması (BORSAI_FAZ8_FREEZE_20261002): `break_floor_v0` ve kural satırı `break_floor_v0@ZERO` models/'de ve
models/INDEX_POST_BREAK.json'da (SPEC_BREAK_V0 §4.4, §7.3, §9.2, §13-9; SPEC_DEVIATIONS N21–N25). Donmuş dosyalar ↔ nihai fit
önizlemeleri, dizin ve bayt-eşitlikler, stdlib `predict_break` ↔ numpy nihai fit, `@ZERO` ve `by_type` oranları (Fraction), kapsam
kuralları (b = 9, b = 10, L = 10), tür ve listeleme öncesi kayıt yolu, MODELS.md dondurma notu."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from fractions import Fraction

import pytest

from borsai import freeze as fz
from borsai import post_break as pbk
from borsai import predict_break as pb
from borsai import registry as reg
from borsai import report_faz8 as r8
from borsai import specs
from borsai.data import load_dataset
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes, sha256_file
from borsai.specs import FAZ8_MODEL_IDS, POST_BREAK_MODEL_SPECS, SPEC_DOCUMENTS_FAZ8, spec_sha256

import faz7_support as fs7
import faz8_support as fs8

MODEL_ID, ZERO_ID = FAZ8_MODEL_IDS
VOLATILE = ("created_at", "code_version", "runtime")
PRE_FREEZE_COMMIT = "6d3f674"          # dondurma görevinin başladığı HEAD (Fable denetimi); models/ Faz 8 öncesi (30 dosya)
INDEX_SHA256 = "7e636e8bf64b25d79bac04f4bf78b9f870cded8d4d1c10009b6926941e4edb59"            # 27 giriş (Faz 7C dondurması)
INDEX_POST_D1_SHA256 = "94ac36faffac6017d54ff406b97b37623c27633c847bd0117fb51bf42975b820"
SPEC_BREAK_V0_SHA256 = "da98351c2b1bb4d7ef3c9ee5954ff4daade0960eab0ec44daa0b4ba540001f31"
NOW = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
# Görev metninin "beklenen sayılar" tablosu (önizlemelerden ölçüldü): başlık -> (C, sabit, b_floor, b_turnover)
EXPECTED_HEADS = {"F1": (1.0, -1.0006869243500793, 0.9866556408087268, 0.06286893543556789),
                  "F2": (0.1, -1.89485164203132, 0.28721801132023284, -0.3079897535288709)}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def _git_bytes(rev: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


@pytest.fixture(scope="module")
def frozen():
    return {m: json.loads((ROOT / "models" / f"{m}.json").read_text(encoding="utf-8")) for m in FAZ8_MODEL_IDS}


@pytest.fixture(scope="module")
def previews():
    return {m: json.loads((pbk.GOLDEN_DIR / pbk.preview_file(m)).read_text(encoding="utf-8")) for m in FAZ8_MODEL_IDS}


@pytest.fixture(scope="module")
def dataset():
    return load_dataset()


@pytest.fixture(scope="module")
def table(dataset):
    return pbk.load_break_table(dataset)


def _strip(d):
    return {k: v for k, v in json.loads(pretty_json_bytes(dict(d))).items() if k not in VOLATILE}


# ---------------------------------------------------------------- dizin, dosyalar, bayt-eşitlikler

@pytest.mark.requires_git_history
def test_post_break_index_and_old_models_byte_identical(frozen):
    """INDEX_POST_BREAK: şema, 2 giriş (FAZ8_MODEL_IDS sırası), sha'lar dosyalarla eşit, giriş = `post_break_index_entry` (N22).
    INDEX.json (27 giriş), INDEX_POST_D1.json ve 28 model dosyası dondurma öncesiyle (6d3f674) bayt-eşit; models/'e yalnız üç dosya
    eklendi; Faz 8 kimlikleri öteki iki dizinde yok."""
    raw = (ROOT / "models" / fz.INDEX_POST_BREAK_NAME).read_bytes()
    index = json.loads(raw)
    assert raw == pretty_json_bytes(index) and index["schema_version"] == fz.INDEX_SCHEMA
    assert [e["model_id"] for e in index["models"]] == list(FAZ8_MODEL_IDS)
    assert fs8.frozen_post_break_files() == [fz.INDEX_POST_BREAK_NAME] + [f"{m}.json" for m in FAZ8_MODEL_IDS]
    for e in index["models"]:
        data = (ROOT / "models" / e["file"]).read_bytes()
        assert e["file"] == f"{e['model_id']}.json" and e["sha256"] == sha256_bytes(data)
        assert e == fz.post_break_index_entry(frozen[e["model_id"]], e["file"], e["sha256"])
        assert (e["stage"], e["status"], e["training_n"], e["training_n_F2"]) == (pb.STAGE, "FROZEN", 82, 78)
    old = _git("ls-tree", "--name-only", PRE_FREEZE_COMMIT, "models/").split()          # + models/.gitkeep
    assert len([n for n in old if n.endswith(".json")]) == 30 and "models/.gitkeep" in old    # 2 dizin + 28 model dosyası
    for name in old:
        assert (ROOT / name).read_bytes() == _git_bytes(PRE_FREEZE_COMMIT, name), name
    assert sha256_file(ROOT / "models" / "INDEX.json") == INDEX_SHA256
    assert sha256_file(ROOT / "models" / fz.INDEX_POST_D1_NAME) == INDEX_POST_D1_SHA256
    on_disk = sorted(f"models/{p.name}" for p in (ROOT / "models").iterdir() if p.is_file())
    assert on_disk == sorted(old + [f"models/{n}" for n in fs8.frozen_post_break_files()])
    for name in ("INDEX.json", fz.INDEX_POST_D1_NAME):
        ids = {e["model_id"] for e in json.loads((ROOT / "models" / name).read_text(encoding="utf-8"))["models"]}
        assert not ids & set(FAZ8_MODEL_IDS), name
    assert len(json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]) == 27


@pytest.mark.requires_git_history
def test_frozen_files_equal_previews_and_clean_code(frozen, previews):
    """Donmuş JSON ↔ nihai fit önizlemesi (`created_at`, `code_version`, `runtime` dışında `==`); `code_version.git_commit` dondurma
    commit'inin (models/break_floor_v0.json'ı ekleyen) üstüdür (kod commit'i K), `borsai_dirty` false, borsai kaynak sha'sı o commit'in
    borsai/ ağacı; K ile dondurma commit'i arasında borsai/ değişmedi; dondurma commit'i yalnız üç dosyayı taşır; K görev başlangıcının
    torunudur. `predict_break.check_params` geçer; şartname ve KARARLAR belgeleri pinli sha'larla."""
    f1 = _git("log", "--diff-filter=A", "--format=%H", "--", f"models/{MODEL_ID}.json").split()[-1]
    assert sorted(_git("show", "--name-only", "--format=", f1).split()) == \
        sorted(f"models/{n}" for n in [fz.INDEX_POST_BREAK_NAME] + [f"{m}.json" for m in FAZ8_MODEL_IDS])
    k = _git("rev-parse", f"{f1}^").strip()
    assert subprocess.run(["git", "merge-base", "--is-ancestor", PRE_FREEZE_COMMIT, k], cwd=ROOT).returncode == 0
    assert _git("diff", "--name-only", k, f1, "--", "borsai") == ""
    for m in FAZ8_MODEL_IDS:
        f = frozen[m]
        assert _strip(f) == _strip(previews[m]), m
        assert set(f["runtime"]) == set(previews[m]["runtime"])
        cv = f["code_version"]
        assert cv["git_commit"] == k and cv["borsai_dirty"] is False and cv["borsai_source_sha256"] == fs7.borsai_tree_sha256_at(k), m
        assert f["model_id"] == m and f["spec_sha256"] == spec_sha256(POST_BREAK_MODEL_SPECS[m])
        for key, doc in (("spec_document", "SPEC_BREAK_V0"), ("decisions_document", "KARARLAR_FAZ8")):
            assert f[key] == SPEC_DOCUMENTS_FAZ8[doc] and f[key]["sha256"] == sha256_file(ROOT / f[key]["path"]), (m, key)
        assert f["spec_document"]["sha256"] == SPEC_BREAK_V0_SHA256
        assert (f["stage"], f["family"], f["algorithm"]) == (pb.STAGE, pb.FAMILY, pb.ALGORITHM)
        assert f["training"]["cutoff_date"] == "2026-08-10" and f["training"]["cutoff_date"] <= pbk.OUTCOME_CUTOFF
        pb.check_params(f)


def test_refreeze_is_refused():
    """Kural 1: dondurulmuş dosyanın ya da dizin kaydının üzerine yazılmaz (fit çağrılmadan reddedilir)."""
    with pytest.raises(fz.FreezeError, match="zaten dondurulmuş"):
        fz.freeze(list(FAZ8_MODEL_IDS), None)


# ---------------------------------------------------------------- tahmin: stdlib ↔ numpy, sayılar, kapsam

def test_frozen_json_stdlib_matches_numpy_final_fit(frozen, dataset, table):
    """§13-9 donmuş dosyayla: stdlib `predict_break` ↔ numpy nihai fit (`predict_proba`, kesin z; `@ZERO`'da sabit), 82 (F2 78) eğitim
    satırında |Δp| ≤ 1e-12 (`post_break.parity_rows`); yeniden fit donmuş dosyaya (3 alan dışında) eşit; katsayılar ve C beklenen."""
    for m in FAZ8_MODEL_IDS:
        params, fits = pbk.final_fit(m, dataset, table=table)
        assert _strip(params) == _strip(frozen[m]), m
        assert (len(fits["F1"].order), len(fits["F2"].order)) == (82, 78)
        par = pbk.parity_rows(frozen[m], fits, table)
        assert set(par) == {"F1", "F2"} and max(par.values()) <= pbk.PARITY_TOL, (m, par)
    for head, (C, icpt, b_floor, b_turn) in EXPECTED_HEADS.items():
        hd = frozen[MODEL_ID]["horizons"][head]["p_floor"]
        assert hd["kind"] == "logit" and hd["C"] == C and hd["intercept"] == icpt
        assert dict(zip(hd["columns"], hd["coef"])) == {"b_floor": b_floor, "b_turnover": b_turn}


def test_zero_and_by_type_rates_are_exact_fractions(frozen):
    """`@ZERO` F1 = 25/82, F2 = 11/78; `by_type_F1` b_floor = 1: 19/35, b_floor = 0: 6/47 (Fraction ile bit-eşit; canlıda
    karşılaştırıcılar bunlardır, §9.3). Kural satırı özellik okumaz: kırılma günü alanı olmadan aynı sabiti verir."""
    z, m = frozen[ZERO_ID], frozen[MODEL_ID]
    want = {"F1": float(Fraction(25, 82)), "F2": float(Fraction(11, 78))}
    assert want == {"F1": 0.3048780487804878, "F2": 0.14102564102564102}
    assert z["features"] == [] and z["preprocessing"] is None
    for head, v in want.items():
        assert z["horizons"][head]["p_floor"] == {**z["horizons"][head]["p_floor"], "kind": "constant", "C": "ZERO", "value": v}
    for doc in (z, m):
        assert doc["comparators"]["zero"] == want
        assert doc["comparators"]["by_type_F1"] == {"1": {"rate": float(Fraction(19, 35)), "n": 35, "events": 19},
                                                   "0": {"rate": float(Fraction(6, 47)), "n": 47, "events": 6}}
        assert (doc["training"]["n_F1"], doc["training"]["events_F1"], doc["training"]["n_F2"], doc["training"]["events_F2"]) == \
            (82, 25, 78, 11)
    assert float(Fraction(19, 35)) == 0.5428571428571428 and float(Fraction(6, 47)) == 0.1276595744680851
    out = pb.predict_break(z, None, None, b=3)
    assert out["refused"] is None and (out["F1"]["p_floor"], out["F2"]["p_floor"]) == (want["F1"], want["F2"])


def test_scope_b9_b10_no_break_on_frozen_json(frozen, table):
    """Kapsam (§1, §11; K-FRZ-4/2): b = 9'da F2 yazılmaz (`TARGET_UNDEFINED_F2`), F1 dolu — H99'un dört b = 9 arzında donmuş JSON'la;
    b = 10 → `B10`, L = 10 → `NO_BREAK` (ret değil, tahmin yok)."""
    b9 = [u for u in table.breaks() if u.b == 9]
    assert len(b9) == 4
    for m in FAZ8_MODEL_IDS:
        for u in b9:
            out = pb.predict_break(frozen[m], u.day, u.shares_offered, b=u.b, first_trading_date=u.first_trading_date)
            assert out["refused"] is None and out["not_applicable"] is None, (m, out["refused"])
            assert out["F2"] is None and out["f2_status"] == pb.TARGET_UNDEFINED_F2 and 0.0 < out["F1"]["p_floor"] < 1.0
        b10 = [u for u in table.units if u.status == pb.NOT_APPLICABLE_B10]
        assert b10
        out = pb.predict_break(frozen[m], b10[0].day, b10[0].shares_offered, b=10)
        assert out["not_applicable"]["code"] == pb.NOT_APPLICABLE_B10 and out["F1"] is None and out["F2"] is None
        out = pb.predict_break(frozen[m], None, None, b=None)
        assert out["not_applicable"]["code"] == pb.NOT_APPLICABLE_NO_BREAK and out["F1"] is None and out["refused"] is None


@pytest.mark.requires_raw_sources
def test_kind_post_break_and_pre_listing_record_runs_only_index_models(frozen):
    """K3: donmuş kırılma JSON'unun türü `post_break` (iki fonksiyonda); `run_model` → PARAMS_INVALID; listeleme öncesi kayıt yolu
    (`build_record`) hâlâ yalnız INDEX.json'un 27 modelini çalıştırır (tests/test_faz7c_frozen.py::
    test_live_record_with_the_real_index_carries_four_fall_cells de 27'yi sınar); kayıtta Faz 8 hücresi ve INDEX_POST_BREAK yok."""
    for m in FAZ8_MODEL_IDS:
        assert fz.model_kind(frozen[m]) == specs.model_kind(m) == "post_break"
        out = fz.run_model(frozen[m], {})
        assert out["status"] == fz.STATUS_ERROR and out["refusal"]["code"] == "PARAMS_INVALID" and out["output"] is None
    rec = fz.build_record(reg.INPUTS_DIR / "CITAS.json", now=NOW)
    ids = [c["model_id"] for c in rec["models"]]
    assert rec["summary"]["n_models"] == 27 == len(ids) and not set(ids) & set(FAZ8_MODEL_IDS)
    assert ids == [e["model_id"] for e in json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]]
    assert "INDEX_POST_BREAK" not in json.dumps(rec, ensure_ascii=False)


# ---------------------------------------------------------------- MODELS.md dondurma notu

def _audit_section(text: str, source: str) -> str:
    if source == "başlık":
        return text.split("\n## 0. ")[0]
    num = source.lstrip("§")
    start = text.index(f"\n{'##' if num.isdigit() else '###'} {num}. ") + 1
    nxt = re.search(r"\n#{2,3} ", text[start:])
    return text[start:start + nxt.start()] if nxt else text[start:]


def test_models_md_freeze_note(frozen):
    """Faz 8 bölümünün sonunda tek "### Dondurma": donmuş dosyaların sha'ları diskteki dosyalarla eşit; REPRO sabitlerinin her biri
    AUDIT.md'nin gösterilen bölümünde birebir geçer ve notta yazılıdır; `@ZERO` hücresi ledger'dan (yukarıdaki tabloyla aynı);
    k1 etiketi aynen; yedi kart uyarısı; "(dondurulmadı)" başlıkları yerinde (backtest anının kaydı)."""
    text = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
    sec = text.split("## Faz 8: kırılma akşamı")[1].split("## Faz 7C: düşen arz modeli v0")[0]
    assert sec.count("### Dondurma") == 1 and sec.index("### Faz 8 koşusu ve deney günlüğü") < sec.index("### Dondurma")
    note = sec.split("### Dondurma")[1]
    assert "\n### " not in note and "### Nihai fit önizlemesi (dondurulmadı)" in sec
    entries = r8.frozen_entries()
    assert [e["model_id"] for e in entries] == list(FAZ8_MODEL_IDS)
    for e in entries:
        assert e["sha256"] == sha256_file(ROOT / "models" / e["file"])
        assert f"| `{e['model_id']}` | `models/{e['file']}` | `{e['sha256']}` | {e['frozen_at'][:10]} | {r8.FREEZE_ROLE[e['model_id']]} |" in note
    audit = (ROOT / "docs" / "fable_faz8_audit" / "AUDIT.md").read_text(encoding="utf-8")
    assert audit.startswith("**REPRO_OK**")
    for key, (value, source) in r8.REPRO.items():
        assert value in _audit_section(audit, source), (key, source)
        assert value in note, key
    rows, _, _, previews = r8.load_faz8()
    ev = r8.evaluate(rows, previews[MODEL_ID])
    z = ev["cells"]["near"]["F1_zero"]
    assert ev["k1"]["holds"] and f"{r8._s(z['mean'])} {r8._ci(z)}" in note
    assert f"\"{r8.PROMOTION_LABEL}\"" in note and r8.PROMOTION_LABEL == "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0"
    assert "Yukarıdaki 'dondurulmadı' ifadeleri backtest anının kaydıdır." in note
    assert "`models/INDEX_POST_BREAK.json` ayrı dizindir" in note and "`live_break`" in note and "RETRO" in note
    warnings = r8.card_warnings()
    assert len(warnings) == 7 and all(f"  {i}. {w}" in note for i, w in enumerate(warnings, 1))
    assert SPEC_BREAK_V0_SHA256[:12] in note

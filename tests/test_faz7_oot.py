"""Eski kohort ek kayıtları, model başına kohort kapısı ve kasa skorlama kodu (BORSAI_FAZ7_OOT_RECORDS; SPEC_HAZARD_V1 §7.1-3,
§7.2, §7.3, §11-12, §11-13; SPEC_C_V0 §5.2, §7, §11-10; SPEC_DEVIATIONS L).

Sentetik geçici git depolarında (gerçek kasa verisi YOK; gerçek kasa skoru üretilmez): zaman çizelgesi gerçek sıranın aynısıdır —
19 eski model (Faz 7 öncesi INDEX) → S1 → S2 kayıtları → açık kümenin sonuçları (S5) → 8 yeni model (Faz 7 + 7C dondurması) → ek
kayıtlar (`--only-missing-models`) → kasa açılışı (SEALED sonuçlar). Kodlar sentetiktir (SYN*, SYK*); gerçek kohort kodu hiçbir
çıktıya yazılmaz. Gerçek depoda yalnız bellekte kuru koşu ve yakın dönem blokları (altın ledger'lar ↔ günlük) denetlenir."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from borsai import backtest as bt
from borsai import freeze as fz
from borsai import market20 as m20
from borsai import outcomes as oc
from borsai import outcomes_oot as oo
from borsai import registry as reg
from borsai import scoring as sc
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes, sha256_file
from borsai.specs import FAZ7_MODEL_IDS, FAZ7C_MODEL_IDS

import faz6_support as f6
import faz7_support as fs7

NOW = datetime(2026, 9, 28, 20, 0, 0, tzinfo=timezone.utc)
NEW_IDS = list(FAZ7_MODEL_IDS) + list(FAZ7C_MODEL_IDS)
MARGIN_T, ADDSALE_T, F3_T = "SYKM", "SYKN", "SYKO"          # kasada: 2020-02-06 (marj %20), ek satış boş, f3 boş


@pytest.fixture(scope="module")
def cal():
    return oo.load_calendar_oot()


def _members(cal):
    """12 açık + 12 kasa üyesi (2021-03 … 2021-11, ≥ 6 ay bloğu) + kasada üç özel üye."""
    days = [s for s in cal.sessions if "2021-03-01" <= s <= "2021-11-30"]
    picks = days[::7][:24]
    out = [{"ticker": f"SYN{chr(65 + i)}", "ftd": d} for i, d in enumerate(picks[0::2])]
    out += [{"ticker": f"SYK{chr(65 + i)}", "ftd": d, "vault": reg.VAULT_SEALED} for i, d in enumerate(picks[1::2])]
    out += [{"ticker": MARGIN_T, "ftd": "2020-02-06", "market": "ANA", "sale_method": reg.SALE_ON_EXCHANGE, "f3": None,
             "vault": reg.VAULT_SEALED},
            {"ticker": ADDSALE_T, "ftd": days[-3], "vault": reg.VAULT_SEALED},
            {"ticker": F3_T, "ftd": days[-2], "f3": None, "vault": reg.VAULT_SEALED}]
    return out


def _paths(cal, members):
    out = {}
    for i, m in enumerate(members):
        k = Decimal(i) / 100
        closes = ["11.55", "12.70", f"{Decimal('12.00') + k}"] + [f"{Decimal('12.10') + k}"] * 9
        uppers = ["11.55", "12.70", "13.97"] + ["13.30"] * 9
        out[m["ticker"]] = f6.ceiling_path(cal.sessions, m["ftd"], closes, uppers)
    return out


def _copy_models(dst: Path, n: int | None) -> None:
    """models/: ilk `n` INDEX girişi (None: bugünkü INDEX'in tamamı) ve dosyaları. n = 19: Faz 7 öncesi INDEX (a0df5b7) baytları."""
    dst.mkdir(parents=True, exist_ok=True)
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
    entries = index["models"] if n is None else index["models"][:n]
    for e in entries:
        shutil.copyfile(ROOT / "models" / e["file"], dst / e["file"])
    (dst / "INDEX.json").write_bytes((ROOT / "models" / "INDEX.json").read_bytes() if n is None else fs7.pre_faz7_index_bytes())


def _batch_delta(root, **kw):
    return fz.write_oot_delta_records(root / "registry" / "oot" / "cohort_pre_h99.csv", now=NOW,
                                      records_dir=root / "registry" / "oot" / "records", models_dir=root / "models", root=root,
                                      code_root=root, **kw)


@pytest.fixture(scope="module")
def prefix(tmp_path_factory, cal):
    """Ortak önek: 19 model → S1 → S2 (19 model) → açık küme sonuçları (S5) → 8 yeni model (F1). Her commit kanıtlı, sırayla."""
    tmp = tmp_path_factory.mktemp("faz7_oot")
    root = f6.init_repo(tmp)
    members = _members(cal)
    _copy_models(root / "models", fs7.N_PRE_FAZ7)
    c = {"models19": f6.commit(root, "19 model", "models")}
    rows = f6.write_members(root, members, sessions=cal.sessions)
    doc_p = root / "registry" / "oot" / "inputs" / f"{ADDSALE_T}.json"
    doc = json.loads(doc_p.read_text(encoding="utf-8"))
    f = doc["fields"]["additional_sale_shares"]
    for k in reg.FIELD_SOURCE_KEYS:
        f.pop(k, None)
    f.update(value=None, missing_reason="SENTETIK_TEST")
    doc_p.write_bytes(pretty_json_bytes(doc))
    c["s1"] = f6.commit(root, "S1", "registry/oot")
    fz.write_oot_records(root / "registry" / "oot" / "cohort_pre_h99.csv", now=datetime(2026, 9, 24, 22, 0, tzinfo=timezone.utc),
                         records_dir=root / "registry" / "oot" / "records", models_dir=root / "models", root=root, code_root=root)
    c["s2"] = f6.commit(root, "S2", "registry/oot/records")
    window = [s for s in cal.sessions if s >= "2020-01-20"][:520]
    files = f6.market(window, _paths(cal, members))
    for key, t in (("models19", "10:00"), ("s1", "10:05"), ("s2", "10:10")):
        f6.make_proof(root, c[key], f"2026-09-25T{t}:00Z")
    oo.extract_open_members(root=root, qdir=tmp / "q", downloader=f6.FakeDownloader(files), prober=lambda u: False, calendar=cal)
    c["s5"] = f6.commit(root, "S5 açık küme sonuçları", "data")
    f6.make_proof(root, c["s5"], "2026-09-25T13:45:00Z")
    _copy_models(root / "models", None)
    c["f1"] = f6.commit(root, "F1: Faz 7 + 7C", "models")
    f6.make_proof(root, c["f1"], "2026-09-28T19:06:00Z")
    return {"root": root, "tmp": tmp, "commits": c, "members": members, "rows": rows, "files": files}


def _clone(prefix, dst: Path) -> Path:
    shutil.copytree(prefix["root"], dst / "repo", symlinks=True)
    return dst / "repo"


def _vault_ingest(root: Path, prefix, cal) -> str:
    """Kasa açılışının sentetik eşi: SEALED üyelerin D_1…D_10 satırları (açılış yetkisiyle: `VaultUnsealed`, SPEC_DEVIATIONS M-E (d))
    data/outcomes_oot/'a; tek commit."""
    vault = {r["ticker"]: r["vault"] for r in prefix["rows"] if r["status"] == reg.COHORT_MEMBER}
    q = root.parent / "q_vault"
    dl = f6.FakeDownloader(prefix["files"])
    for m in prefix["members"]:
        t = m["ticker"]
        if vault[t] != reg.VAULT_SEALED:
            continue
        ext = oo.resolve_member(t, m["ftd"], cal, vault, unsealed=oo.VaultUnsealed({t}, oo.UNSEALED_BY_OPEN_VAULT),
                                fetch=lambda s, k: oo.fetch_quarantine(s, k, qdir=q, downloader=dl))
        doc = reg.load_inputs(root / "registry" / "oot" / "inputs" / f"{t}.json")[0]
        oo.write_outcome_oot(t, oo.outcome_rows_oot(ext, doc["fields"]["ipo_price_tl"]["value"], cal), root / "data" / "outcomes_oot")
    return f6.commit(root, "kasa açılışı (sentetik)", "data/outcomes_oot")


def _delta_files(root: Path) -> dict[str, Path]:
    out = {}
    for p in sorted((root / "registry" / "oot" / "records").rglob("*.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("record_scope") == fz.OOT_DELTA_SCOPE:
            out[rec["ticker"]] = p
    return out


# ================================================================ ek kayıt yazıcısı (`--only-missing-models`)

@pytest.mark.requires_git_history
def test_delta_records_hold_only_missing_models_and_byte_equal_inputs(prefix, tmp_path):
    root = _clone(prefix, tmp_path)
    out = _batch_delta(root)
    members = prefix["members"]
    assert len(out["written"]) == len(members) and out["complete"] == [] and out["skipped"] == []
    index_ids = [e["model_id"] for e in json.loads((root / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]]
    rd = root / "registry" / "oot" / "records"
    for p in map(Path, out["written"]):
        rec = json.loads(p.read_text(encoding="utf-8"))
        t = rec["ticker"]
        first_path, first = fz.oot_base_record(t, rd)
        assert p.name == fz.record_filename(p.read_bytes(), rec["recorded_at_utc"]) and p.parent.name == t
        assert rec["schema_version"] == fz.OOT_RECORD_SCHEMA and rec["record_stage"] == fz.OOT_STAGE == first["record_stage"]
        assert rec["record_type"] == "PREDICTION" and rec["record_scope"] == fz.OOT_DELTA_SCOPE
        assert [c["model_id"] for c in rec["models"]] == NEW_IDS and len(first["models"]) == fs7.N_PRE_FAZ7
        assert rec["models_index"] == {"path": "models/INDEX.json", "sha256": sha256_file(root / "models" / "INDEX.json"),
                                       "model_ids": index_ids}
        assert rec["delta_of"] == first_path.name and rec["delta_of_sha256"] == sha256_file(first_path)
        for key in fz.OOT_DELTA_SAME_KEYS:                                       # girdiler ve bağlam ilk kayıtla bayt-eşit
            want = {k: v for k, v in first[key].items() if k != "vault"} if key == "cohort_row" else first[key]
            assert pretty_json_bytes(rec[key]) == pretty_json_bytes(want), (t, key)
        assert "vault" not in rec and "vault" not in rec["cohort_row"] and b'"vault"' not in p.read_bytes()   # hijyen: kasa ayrımı yok
        assert b"SEALED" not in p.read_bytes() and "vault" in first
        mi = rec["model_inputs"]
        assert set(mi) - set(first["model_inputs"]) == {"tufe_index", "tufe_refusal", "alloc_regime"}
        assert pretty_json_bytes({k: v for k, v in mi.items() if k in first["model_inputs"]}) == pretty_json_bytes(first["model_inputs"])
        assert mi["alloc_regime"] == reg.parse_regime_tags(rec["cohort_row"]["regime_tags"])["ALLOC_REGIME"]
        assert rec["tufe"]["month"] and rec["tufe"]["refusal"] is None and mi["tufe_index"] == rec["tufe"]["index"]
        assert rec["comparators"] == {} and not set(reg.json_keys(rec)) & reg.OOT_OUTCOME_KEYS
        assert fz.oot_delta_problems(first, rec) == []
        for c in rec["models"]:
            assert c["params_sha256"] == sha256_file(root / c["file"])
    cells = lambda t: {c["model_id"]: c for c in json.loads(_delta_files(root)[t].read_text(encoding="utf-8"))["models"]}  # noqa: E731
    f3 = cells(F3_T)                                                           # ret model başına "ret + neden"; üye düşmez
    for mid in ("ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "fall_d10_v0_h99", "fall_d10_v0_pooled"):
        assert f3[mid]["status"] == "REFUSED" and f3[mid]["refusal"]["code"] == "F3_MISSING", mid
    assert f3["ceiling_hazard_v1_pooled@INF"]["status"] == f3["fall_d10_v0_addsale"]["status"] == "PREDICTED"
    add = cells(ADDSALE_T)
    for mid in ("fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale"):
        assert add[mid]["status"] == "REFUSED" and add[mid]["refusal"]["code"] == "ADDITIONAL_SALE_MISSING", mid
    assert add["fall_d10_v0_pooled@ZERO"]["status"] == "PREDICTED"
    mg = cells(MARGIN_T)                                                       # 2020-02-06: marj %20 → @INF kural satırı uygulanamaz
    assert mg["ceiling_hazard_v1_pooled@INF"]["status"] == "NOT_APPLICABLE_REGIME"
    assert mg["ceiling_hazard_v1_pooled@INF"]["not_applicable"]["code"] == "MARGIN_NOT_10PCT"
    assert json.loads(_delta_files(root)[MARGIN_T].read_text(encoding="utf-8"))["model_inputs"]["alloc_regime"] == "PRE_20211111"


@pytest.mark.requires_git_history
def test_delta_writer_is_idempotent_and_all_or_nothing(prefix, tmp_path):
    root = _clone(prefix, tmp_path)
    first = _batch_delta(root)
    again = _batch_delta(root)                                               # commit'lenmeden yeniden koşu: yazılmaz
    assert again["written"] == [] and sorted(again["complete"]) == sorted(m["ticker"] for m in prefix["members"])
    f6.commit(root, "R1", "registry/oot/records")
    assert _batch_delta(root)["written"] == []                                # commit'ten sonra da
    assert len(first["written"]) == len(prefix["members"])
    root2 = _clone(prefix, tmp_path / "b")                                     # girdi ilk kayıttan sonra değişmiş (commit'li): DUR
    p = root2 / "registry" / "oot" / "inputs" / "SYNA.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["fields"]["ipo_price_tl"]["value"] = "10.6"
    p.write_bytes(pretty_json_bytes(doc))
    f6.commit(root2, "girdi değişti", "registry/oot/inputs")
    with pytest.raises(fz.FreezeError, match="ilk kayıtla"):
        _batch_delta(root2)
    assert _delta_files(root2) == {}
    root3 = _clone(prefix, tmp_path / "c")                                     # kirli ağaç: ön koşul
    (root3 / "registry" / "oot" / "inputs" / "SYNX.json").write_text("{}", encoding="utf-8")
    with pytest.raises(fz.OotPreconditionError):
        _batch_delta(root3)


def test_delta_problems_detects_every_changed_block():
    first = {"ticker": "A", "first_trading_date": "2021-01-04", "record_stage": fz.OOT_STAGE, "scale": reg.OOT_SCALE,
             "cohort_row": {"x": "1"}, "vault": "OPEN", "regime_tags": {"R": True}, "inputs_sha256": "a" * 64,
             "inputs": {"path": "p", "sha256": "a" * 64}, "market20": {"f6": "0.1"}, "model_inputs": {"f": "1", "g": None}}
    ok = {**{k: v for k, v in first.items() if k != "vault"},
          "model_inputs": {"f": "1", "g": None, "tufe_index": "100", "tufe_refusal": None, "alloc_regime": "PRE_20211111"}}
    assert fz.oot_delta_problems(first, ok) == []
    for key in fz.OOT_DELTA_SAME_KEYS:
        assert fz.oot_delta_problems(first, {**ok, key: "değişti"}) == [f"{key} ilk kayıttan farklı"], key
    assert fz.oot_delta_problems({**first, "vault": "OPEN", "cohort_row": {"x": "1", "vault": "OPEN"}}, ok) == []
    assert fz.oot_delta_problems(first, {**ok, "vault": "OPEN"}) == ["ek kayıt kasa alanını (vault) taşıyor"]
    assert fz.oot_delta_problems(first, {**ok, "cohort_row": {"x": "1", "vault": "OPEN"}}) == ["ek kayıt kasa alanını (vault) taşıyor"]
    assert fz.oot_delta_problems(first, {**ok, "model_inputs": {**ok["model_inputs"], "f": "2"}}) == [
        "model_inputs ilk kayıtla bayt-eşit değil"]
    assert fz.oot_delta_problems(first, {**ok, "model_inputs": {**ok["model_inputs"], "yeni": 1}}) == [
        "model_inputs'ta beklenmeyen yeni anahtar yeni"]
    assert fz.oot_delta_problems(first, {**ok, "model_inputs": {"f": "1"}}) == ["model_inputs'ta ilk kayıttaki g yok",
                                                                               "model_inputs ilk kayıtla bayt-eşit değil"]


def test_delta_cli_prints_numbers_only(monkeypatch, capsys, tmp_path):
    seen = {}

    def fake(cohort):
        seen["cohort"] = cohort
        return {"written": [str(tmp_path / "SYKA" / "x.json")], "complete": ["SYNA", "SYNB"],
                "skipped": [{"ticker": "SYKB", "status": "SKIPPED", "skip_reason": "NO_BASE_RECORD"}], "cohort_file_sha256": "c" * 64}

    monkeypatch.setattr(fz, "write_oot_delta_records", fake)
    assert fz.main(["--oot", "registry/oot/cohort_pre_h99.csv", "--only-missing-models"]) == 0
    out = capsys.readouterr().out
    assert json.loads(out) == {"written": 1, "complete": 2, "skipped": 1, "skip_reasons": {"NO_BASE_RECORD": 1},
                               "cohort_file_sha256": "c" * 64}
    assert seen["cohort"] == Path("registry/oot/cohort_pre_h99.csv")
    for code in ("SYKA", "SYNA", "SYNB", "SYKB"):
        assert code not in out
    with pytest.raises(SystemExit):
        fz.main(["--only-missing-models"])


@pytest.mark.requires_git_history
def test_delta_skips_member_without_first_record(prefix, tmp_path):
    root = _clone(prefix, tmp_path)
    shutil.rmtree(root / "registry" / "oot" / "records" / "SYNA")
    out = fz.build_oot_delta_records(root / "registry" / "oot" / "cohort_pre_h99.csv", now=NOW,
                                     records_dir=root / "registry" / "oot" / "records", models_dir=root / "models", root=root,
                                     code_root=root)
    assert out["skipped"] == [{"ticker": "SYNA", "status": "SKIPPED", "skip_reason": "NO_BASE_RECORD"}]
    assert "SYNA" not in [t for t, _ in out["records"]] and len(out["records"]) == len(prefix["members"]) - 1


# ================================================================ model başına kapı (SPEC_HAZARD_V1 §7.3)

@pytest.mark.requires_git_history
def test_download_gate_is_per_model_and_blocks_downloads(prefix, tmp_path, cal):
    """İndirme kapısı: INDEX'in her modeli × her MEMBER için modeli içeren kayıt commit'li ve push kanıtlı olmalı. Ek kayıtlar yokken
    (INDEX 27, kayıtlar 19 model) kapı kırmızı; bir kasa üyesinin ek kaydı eksikken kırmızı (yalnız o üye); commit'siz ve kanıtsız
    ek kayıtta kırmızı; hepsi tamamken yeşil. Kapı kapalıyken kasa açılışı hiçbir zip indirmez."""
    root = _clone(prefix, tmp_path)
    n = len(prefix["members"])
    problems = oo.s2_gate_problems(root=root)
    assert len(problems) == n and all("8 model için etkin kayıt yok" in p for p in problems)
    with pytest.raises(oo.GateError):
        oo.download_gate(root=root)
    _batch_delta(root)
    missing = _delta_files(root)["SYKB"]
    missing.unlink()                                                          # bir kasa üyesinin ek kaydı eksik
    c_r1 = f6.commit(root, "R1 (bir üye eksik)", "registry/oot/records")
    f6.make_proof(root, c_r1, "2026-09-28T21:00:00Z")
    assert oo.s2_gate_problems(root=root) == ["SYKB: 8 model için etkin kayıt yok (ceiling_hazard_v1_clip, ceiling_hazard_v1_real, "
                                              "ceiling_hazard_v1_pooled …)"]
    (root / "docs" / "specs_x").mkdir(parents=True)
    (root / "docs" / "specs_x" / "SPEC.md").write_text("özellik\n", encoding="utf-8")
    f6.make_proof(root, f6.commit(root, "özellik şartnamesi", "docs"), "2026-09-28T21:05:00Z")
    dl = f6.FakeDownloader({})
    with pytest.raises(oo.GateError, match="SYKB"):
        oo.open_vault(feature_spec="docs/specs_x/SPEC.md", root=root, qdir=tmp_path / "qv", downloader=dl)
    assert dl.calls == [] and not (tmp_path / "qv").exists()
    _batch_delta(root)                                                        # yalnız eksik üyeye yazar
    assert list(_delta_files(root)) and oo.s2_gate_problems(root=root)[0].startswith("registry/oot temiz değil")
    new_rel = _delta_files(root)["SYKB"].relative_to(root).as_posix()
    assert f"{new_rel}: commit'li değil" in oo.s2_gate_problems(root=root)
    c_fix = f6.commit(root, "R1b", "registry/oot/records")
    assert oo.s2_gate_problems(root=root) == [f"{new_rel}: push kanıtı yok"]
    f6.make_proof(root, c_fix, "2026-09-28T21:10:00Z")
    assert oo.s2_gate_problems(root=root) == []
    oo.download_gate(root=root)


def _complete_repo(prefix, dst: Path, cal, *, r1_proof: str | None = "2026-09-28T21:00:00Z", drop: str | None = None):
    root = _clone(prefix, dst)
    _batch_delta(root)
    if drop is not None:
        _delta_files(root)[drop].unlink()
    c_r1 = f6.commit(root, "R1", "registry/oot/records")
    if r1_proof is not None:
        f6.make_proof(root, c_r1, r1_proof)
    c_v = _vault_ingest(root, prefix, cal)
    f6.make_proof(root, c_v, "2026-09-29T10:00:00Z")
    return root, c_r1, c_v


@pytest.mark.requires_git_history
def test_scoring_gate_red_when_a_second_record_is_missing(prefix, tmp_path, cal):
    root, _, c_v = _complete_repo(prefix, tmp_path, cal, drop="SYKB")
    ctx = sc.OotContext(root)
    for mid in NEW_IDS:
        assert sc.cohort_gate_ok(ctx, c_v, mid) == (False, ["SYKB"]), mid
    klass, ev = sc.class_oot(ctx, "ceiling_hazard_v1_clip", "SYKA", c_v)
    assert klass == "OOT_RETRO" and ev["model_frozen_before_ingest"] and ev["record_before_ingest"]
    assert ev["record_proof_before_ingest_proof"] and not ev["cohort_gate_ok"] and ev["cohort_gate_missing_n"] == 1
    assert sc.cohort_gate_ok(ctx, c_v, "v1_5_h99") == (True, [])                # eski model: S2 kayıtları tam
    assert sc.class_oot(ctx, "v1_5_h99", "SYKA", c_v)[0] == "OOT_BLIND"
    assert sc.cohort_gate_ok(ctx, c_v)[0] is False                              # model verilmezse bütün INDEX modelleri


@pytest.mark.requires_git_history
def test_scoring_gate_red_when_second_record_proof_is_not_before_ingest(prefix, tmp_path, cal):
    root, c_r1, c_v = _complete_repo(prefix, tmp_path, cal, r1_proof=None)     # R1'in kendi kanıtı yok: yalnız kasa commit'inin kanıtı
    ctx = sc.OotContext(root)
    assert sc.proof_time(ctx.git, c_r1, ctx.proofs) == sc.proof_time(ctx.git, c_v, ctx.proofs)
    gate, missing = sc.cohort_gate_ok(ctx, c_v, "fall_d10_v0_pooled")
    assert gate is False and len(missing) == len(prefix["members"])
    klass, ev = sc.class_oot(ctx, "fall_d10_v0_pooled", "SYKA", c_v)
    assert klass == "OOT_RETRO" and ev["record_before_ingest"] and not ev["record_proof_before_ingest_proof"]
    f6.make_proof(root, c_r1, "2026-09-29T11:00:00Z")                           # kanıt kasa kanıtından SONRA: yine kırmızı
    ctx = sc.OotContext(root)
    assert sc.cohort_gate_ok(ctx, c_v, "fall_d10_v0_pooled")[0] is False
    f6.make_proof(root, c_r1, "2026-09-28T21:00:00Z")                           # önce: yeşil
    ctx = sc.OotContext(root)
    assert sc.cohort_gate_ok(ctx, c_v, "fall_d10_v0_pooled") == (True, [])
    assert sc.class_oot(ctx, "fall_d10_v0_pooled", "SYKA", c_v)[0] == "OOT_BLIND"


# ================================================================ kasa skorlaması (sentetik; `oot_pre_h99_sealed` / `_all`)

@pytest.fixture(scope="module")
def vault_scores(prefix, tmp_path_factory, cal):
    tmp = tmp_path_factory.mktemp("faz7_oot_vault")
    root, c_r1, c_v = _complete_repo(prefix, tmp, cal)
    pre = _clone(prefix, tmp / "pre")                                          # ek kayıtlardan önce (commit C durumu)
    return {"root": root, "c_r1": c_r1, "c_v": c_v, "scores": sc.build_oot_scores(root=root, now=NOW),
            "pre": sc.build_oot_scores(root=pre, now=NOW)}


def _block(scores, key, mid):
    return next(m for m in scores[key]["models"] if m["model_id"] == mid)


@pytest.mark.requires_git_history
def test_open_set_rows_of_new_models_are_oot_retro_by_formula(vault_scores):
    """§7.2: açık üyenin ingest'i yeni modellerin dondurulmasından önce → frozen_ok yanlış → OOT_RETRO (n_oot_retro = açık küme);
    ek kayıtlardan önce de (kayıtsız, kayıt kimliği yok) aynı sayı. Eski modellerin açık satırları OOT_BLIND ve değişmez."""
    s, pre = vault_scores["scores"], vault_scores["pre"]
    n_open = s[sc.OOT_SUBSET_OPEN]["n_open"]
    assert n_open == 12
    for doc, has_record in ((s, True), (pre, False)):
        for mid in NEW_IDS:
            b = _block(doc, sc.OOT_SUBSET_OPEN, mid)
            assert b["rows"] == [] and b["n_oot_retro"] == n_open and b["cells"] == [], mid
            retro = [x for x in doc["retro_info"] if x["model_id"] == mid]
            assert len(retro) == n_open and all(not x["class_evidence"]["model_frozen_before_ingest"] for x in retro)
            assert all((x["record_id"] is not None) == has_record for x in retro)
        v15 = _block(doc, sc.OOT_SUBSET_OPEN, "v1_5_h99")
        assert v15["n_oot_retro"] == 0 and {r["class"] for r in v15["rows"]} == {"OOT_BLIND"} and v15["n_scored"] == n_open
    assert len(s["retro_info"]) == len(NEW_IDS) * n_open
    assert sc.OOT_SUBSET_SEALED not in pre and sc.OOT_SUBSET_ALL not in pre      # kasa açılmadan anahtar yok
    old = lambda doc: [m for m in doc[sc.OOT_SUBSET_OPEN]["models"] if m["model_id"] not in NEW_IDS]  # noqa: E731
    strip = lambda ms: [{**m, "rows": [{**r, "class_evidence": {k: v for k, v in r["class_evidence"].items()  # noqa: E731
                                                                  if k not in ("checked_against",)}} for r in m["rows"]]} for m in ms]
    assert strip(old(s)) == strip(old(pre))                                   # ek kayıtlar eski modellerin açık tablosunu değiştirmez


@pytest.mark.requires_git_history
def test_sealed_rows_are_blind_with_earliest_record_rule(vault_scores):
    s, root = vault_scores["scores"], vault_scores["root"]
    sealed = s[sc.OOT_SUBSET_SEALED]
    assert sealed["scale"] == sc.SCALE_OOT and sealed["n_sealed"] == 15 and sealed["n_in_table"] == 15
    index_ids = [e["model_id"] for e in json.loads((root / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]]
    assert [m["model_id"] for m in sealed["models"]] == index_ids and index_ids[-8:] == NEW_IDS
    assert sealed["retro_info"] == []
    deltas = _delta_files(root)
    rd = root / "registry" / "oot" / "records"
    for mid in NEW_IDS:
        b = _block(s, sc.OOT_SUBSET_SEALED, mid)
        assert b["n_oot_retro"] == 0 and b["subset"] == sc.OOT_SUBSET_SEALED
        assert {r["class"] for r in b["rows"]} == {"OOT_BLIND"} and all(not r["open"] for r in b["rows"])
        for r in b["rows"]:
            assert r["record_id"] == deltas[r["ticker"]].name                   # modeli içeren en erken kayıt: ek kayıt
            for rid, v in r["rules"].items():
                if v.get("record_id") is not None:                            # karşılaştırılan kendi birincil kaydından
                    want = fz.oot_primary_record(r["ticker"], rid, rd)[0].name
                    assert v["record_id"] == want, (mid, rid)
    s2 = lambda t: fz.oot_base_record(t, rd)[0].name  # noqa: E731
    v1 = _block(s, sc.OOT_SUBSET_SEALED, "ceiling_hazard_v1_clip")
    row = next(r for r in v1["rows"] if r["ticker"] == "SYKA")
    assert row["rules"]["base_km_expanding"]["record_id"] == row["rules"]["ceiling_hazard_v0"]["record_id"] == s2("SYKA")
    pooled = _block(s, sc.OOT_SUBSET_SEALED, "ceiling_hazard_v1_pooled")
    row = next(r for r in pooled["rows"] if r["ticker"] == "SYKA")
    assert row["rules"]["ceiling_hazard_v1_real"]["record_id"] == row["rules"][sc.FAZ7_RULE_ROW]["record_id"] == deltas["SYKA"].name
    inf = _block(s, sc.OOT_SUBSET_SEALED, sc.FAZ7_RULE_ROW)
    assert next(r for r in inf["rows"] if r["ticker"] == MARGIN_T)["status"] == "NOT_APPLICABLE_REGIME"
    v15 = _block(s, sc.OOT_SUBSET_SEALED, "v1_5_h99")
    assert {r["class"] for r in v15["rows"]} == {"OOT_BLIND"} and all(r["record_id"] == s2(r["ticker"]) for r in v15["rows"])


@pytest.mark.requires_git_history
def test_sealed_primary_and_declared_secondary_cells(vault_scores):
    s = vault_scores["scores"]
    key = lambda c: (c["output"], c["horizon_or_k"], c["metric"], c["rule_id"])  # noqa: E731
    for mid in sc.FAZ7_CANDIDATES:
        b = _block(s, sc.OOT_SUBSET_SEALED, mid)
        assert b["primary_cell"] == {"output": "S", "horizon_or_k": None, "metric": "RPS", "rule_ids": ["base_km_expanding"]}
        prim = [c for c in b["cells"] if c["label"] == "birincil"]
        assert [key(c) for c in prim] == [("S", None, "RPS", "base_km_expanding")] and prim[0]["n"] >= 10
        assert prim[0]["scale"] == sc.SCALE_OOT and prim[0]["n_blocks"] >= 6 and prim[0]["ci95"] is not None
        sec = {key(c) for c in b["cells"] if c["label"] == "ikincil"}
        assert sec == {key(c) for c in sc.FAZ7_OOT_SECONDARY_CELLS[mid]}, mid
        assert b["by_year"] and b["by_regime"]
    for mid in sc.FAZ7C_CANDIDATES:
        b = _block(s, sc.OOT_SUBSET_SEALED, mid)
        prim = [c for c in b["cells"] if c["label"] == "birincil"]
        assert [key(c) for c in prim] == [("p_up", "D10", "Brier", "base_rate")] and prim[0]["n"] >= 10
        sec = {key(c) for c in b["cells"] if c["label"] == "ikincil"}
        assert sec <= {key(c) for c in sc.FAZ7C_OOT_SECONDARY_CELLS[mid]} and sec, mid
        assert all(c["horizon_or_k"] in ("D5", "D10") for c in b["cells"])
        info = b["info"][0]
        assert info["metric"] == "calibration_mean_vs_observed" and info["n"] >= 10 and info["observed"] == 0.0
    for mid in (sc.FAZ7_RULE_ROW, sc.FAZ7C_RULE_ROW):
        b = _block(s, sc.OOT_SUBSET_SEALED, mid)
        assert b["primary_cell"] is None and b["cells"] == [] and b["n_scored"] > 0
    assert "primary_cells_faz7" in s["definitions"] and s["definitions"]["secondary_cells_faz7"] == sc.OOT_SECONDARY_CELLS


@pytest.mark.requires_git_history
def test_all_key_never_merges_new_models(vault_scores):
    """§7.1-5: `oot_pre_h99_all` yalnız açık kümede OOT_BLIND olan (eski) modeller; yeni 8 model için tanımsız, birleştirilmez."""
    s = vault_scores["scores"]
    total = s[sc.OOT_SUBSET_ALL]
    ids = [m["model_id"] for m in total["models"]]
    assert not set(ids) & set(NEW_IDS) and len(ids) == fs7.N_PRE_FAZ7
    assert [x["model_id"] for x in total["excluded_models"]] == NEW_IDS
    assert all(x["n_open_oot_blind"] == 0 and x["n_open_oot_retro"] == 12 and x["reason"] == sc.OOT_ALL_UNDEFINED
               for x in total["excluded_models"])
    v15_all = _block(s, sc.OOT_SUBSET_ALL, "v1_5_h99")
    v15_open = _block(s, sc.OOT_SUBSET_OPEN, "v1_5_h99")
    v15_sealed = _block(s, sc.OOT_SUBSET_SEALED, "v1_5_h99")
    assert len(v15_all["rows"]) == len(v15_open["rows"]) + len(v15_sealed["rows"])
    assert v15_all["n_scored"] == v15_open["n_scored"] + v15_sealed["n_scored"] and total["n_in_table"] == 27
    ok, n_blind, n_retro = sc.all_eligible(sc.OotContext(vault_scores["root"]), *sc.oot_model_rows(
        sc.OotContext(vault_scores["root"]), "ceiling_hazard_v1_clip"))
    assert (ok, n_blind, n_retro) == (False, 0, 12)


@pytest.mark.requires_git_history
def test_vault_doc_sections_without_member_codes(vault_scores):
    s = vault_scores["scores"]
    doc = sc.render_oot_doc(json.loads(pretty_json_bytes(s)))
    assert doc == sc.render_oot_doc(s)
    assert "## 8. " + sc.OOT_SEALED_TITLE in doc and "## 9. " + sc.OOT_ALL_TITLE in doc
    part = doc.partition("## 8.")[2]
    assert "| `ceiling_hazard_v1_pooled` | S RPS | `base_km_expanding` |" in part
    assert "| `fall_d10_v0_pooled` | p_up D10 Brier | `base_rate` |" in part
    head = doc.partition("## 8.")[0]
    assert "OOT_RETRO (12 çift; bu alt küme bu model için test değil)" in head
    for m in vault_scores["scores"][sc.OOT_SUBSET_SEALED]["models"][0]["rows"]:
        assert m["ticker"] not in doc
    for code in ("SYNA", "SYKA", MARGIN_T):
        assert code not in doc


def test_committed_oot_doc_unchanged_by_new_renderer():
    """Commit'li SCORES_OOT.md, commit'li scores_oot.json'un bugünkü render'ıyla bayt-eşit. FAZ7_VAULT_SCORE T7 (SPEC_DEVIATIONS M21;
    proje sahibi kararı 2026-09-29): kasa skorları commit'lendi, dosya kasa ve toplam anahtarlarını taşır (pin: önce "yok", şimdi
    "var"); belge §8–§11'i içerir. Karşılaştırma metin yerine bayt."""
    committed = json.loads((ROOT / "scores" / "scores_oot.json").read_text(encoding="utf-8"))
    assert {sc.OOT_SUBSET_SEALED, sc.OOT_SUBSET_ALL, sc.OOT_POST_D1_SEALED, sc.OOT_POST_D1_ALL} <= set(committed)
    assert sc.render_oot_doc(committed).encode("utf-8") == (ROOT / "docs" / "SCORES_OOT.md").read_bytes()


# ================================================================ canlı hücre tanımları ve (C) satırları

def test_new_model_comparators_and_labels_follow_spec():
    assert sc.comparators("ceiling_hazard_v1_clip", "hazard") == ["base_km_expanding", "ceiling_hazard_v0", "ceiling_hazard_v0@INF"]
    assert sc.comparators("ceiling_hazard_v1_pooled", "hazard")[-2:] == ["ceiling_hazard_v1_real", sc.FAZ7_RULE_ROW]
    assert sc.comparators(sc.FAZ7_RULE_ROW, "hazard") == [] == sc.comparators(sc.FAZ7C_RULE_ROW, "fall")
    assert sc.comparators("fall_d10_v0_pooled", "fall") == ["base_rate", "base_last10_rate", "v1_5_h99", "fall_d10_v0_addsale",
                                                              "fall_d10_v0_h99", sc.FAZ7C_RULE_ROW]
    assert sc.comparators("ceiling_hazard_v0", "hazard")[0] == "ceiling_hazard_v0@INF"          # eski modeller aynen
    specs = sc.live_cell_specs("fall_d10_v0_h99", "fall")
    assert {h for _, h, _, _ in specs} == {"D5", "D10"} and {o for o, _, _, _ in specs} == {"p_up"}
    assert ("p_up", "D10", "Brier", "base_rate") in specs and ("p_up", "D5", "HitMiss", "base_rate") in specs
    assert sc._label("fall_d10_v0_h99", "p_up", "D10", "Brier", "base_rate") == "birincil"
    assert sc._label("fall_d10_v0_h99", "p_up", "D10", "Brier", "v1_5_h99") == "ikincil"
    assert sc._label("fall_d10_v0_h99", "p_up", "D10", "LogLoss", "base_rate") == "keşif"
    assert sc._label("ceiling_hazard_v1_real", "S", None, "RPS", "base_km_expanding") == "birincil"
    assert sc._label("ceiling_hazard_v1_real", "S", 10, "Brier", "ceiling_hazard_v0") == "ikincil"
    assert sc._label("ceiling_hazard_v1_real", "S", None, "RPS", "ceiling_hazard_v1_clip") == "keşif"     # canlıda ilan yok
    assert sc._oot_label("ceiling_hazard_v1_real", "S", None, "RPS", "ceiling_hazard_v1_clip") == "ikincil"
    assert sc._label("v1_5_h99", "p_up", "D10", "Brier", "base_rate") == "keşif"                       # eski etiketler aynen
    assert sc.primary_cell_of("ceiling_hazard_v0") == sc.PRIMARY_CELLS["ceiling_hazard_v0"]
    assert sc.primary_cell_of(sc.FAZ7_RULE_ROW) is None and sc.oot_primary_cell_of(sc.FAZ7C_RULE_ROW) is None
    assert sc._need_names("fall") == ["D5", "D10"]


def test_fall_rows_render_and_descriptive_without_d1(cal):
    """(C) canlı satırı: yalnız D5/D10 (D1 anahtarı yok); SCORES.md satır tablosu ve betimsel ölçü çökmez."""
    pred = {"D5": {"return": None, "p_up": 0.7}, "D10": {"return": None, "p_up": 0.6}}
    rv = {"D5": {"return": 0.01, "p_up": 0.8}, "D10": {"return": 0.02, "p_up": 0.75}}
    realized = {"R": {"D1": "0.1", "D3": "0.2", "D5": "0.15", "D10": "0.05"}, "Y": {"D1": 1, "D3": 1, "D5": 1, "D10": 1},
                "row_status": ["OK"] * 10}
    row = {"ticker": "SYNQ", "class": "LIVE", "record_id": "r.json", "status": "SCORED", "prediction": pred,
           "rules": {c: {"values": rv} for c in sc.comparators("fall_d10_v0_h99", "fall")}, "realized": realized, "d1": "2026-10-01"}
    lines: list[str] = []
    sc._render_model_rows(lines.append, {"model_id": "fall_d10_v0_h99", "kind": "fall",
                                         "live": {"rows": [row], "self_reported_rows": [], "n_scored": 1, "n_skipped": 0, "n_live": 1,
                                                  "n_late": 0, "n_refused": 0, "n_target_unavailable": 0, "n_pending": 0,
                                                  "n_partial_pending": 0, "cells": []}})
    body = [x for x in lines if x.startswith("| SYNQ")]
    assert [x.split(" | ")[1] for x in body] == ["D5", "D10"]
    head = next(x for x in lines if x.startswith("| Arz |"))
    assert "`fall_d10_v0_addsale` p̂" in head and "R̂" not in head.replace("model R̂", "")
    assert sc.live_descriptive("fall_d10_v0_h99", "fall", [row] * 12) == []
    assert sc._losses("fall", "p_up", "D10", "Brier", pred, rv, realized) == ((0.6 - 1) ** 2, (0.75 - 1) ** 2)


# ================================================================ yakın dönem blokları (EK3 §5.5, Ö1) ve aile keşif sayacı

EK3_KEYS = {"schema_version", "scale", "label", "comparator", "metric", "subset", "diff", "ci95", "n", "n_blocks", "tolerance",
            "source"}


def _last_backtest_lines():
    out = {}
    for line in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            if e.get("kind") == "backtest":
                out[e["model_id"]] = e
    return out


def test_near_era_blocks_equal_golden_ledgers_and_log():
    blocks = sc.near_era_blocks()
    log = _last_backtest_lines()
    assert list(blocks) == NEW_IDS
    for mid, b in blocks.items():
        assert set(b) == EK3_KEYS and b["schema_version"] == "borsai.near_era/1" and b["scale"] == "backtest_near_era"
        assert b["subset"] == "first_trading_date >= 2024-01-01" and b["label"] in ("tolerans içinde", "bozuyor", "belirsiz")
        e = log[mid]
        if mid in FAZ7_MODEL_IDS:
            want, label = e["near_era"], e["near_era"]["label"]
            assert (b["comparator"], b["metric"], b["tolerance"]) == ("ceiling_hazard_v0", "RPS", 0.010)
        elif mid == "fall_d10_v0_pooled":
            want, label = e["near_era"], e["near_era"]["label"]
            assert (b["comparator"], b["metric"], b["tolerance"]) == ("fall_d10_v0_h99", "D10 Brier", 0.008)
        else:
            assert e["near_era"] is None
            want = e["near_era_secondary"]["base_rate|D10"]
            label = bt.near_era_label_fall(want["ci95"])
            assert (b["comparator"], b["metric"], b["tolerance"]) == ("base_rate", "D10 Brier", 0.008)
        assert (b["diff"], b["ci95"], b["n"], b["n_blocks"], b["label"]) == (want["mean"], want["ci95"], want["n"], want["n_months"],
                                                                               label), mid
    assert blocks["ceiling_hazard_v1_pooled"]["label"] == "bozuyor" and blocks["fall_d10_v0_pooled"]["label"] == "belirsiz"


def test_family_exploration_counter_is_log_exploration_count():
    from borsai import report_faz7c as r7c
    from borsai.specs import FAZ7C_EXPLORATION

    card = sc.family_exploration_card()
    n = sum(1 for line in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip() and json.loads(line).get("kind") == "exploration")
    assert card["n_exploration_family"] == n == r7c.exploration_count(sc.LOG_PATH) == FAZ7C_EXPLORATION["n"] == 2054
    assert card["exploration_family_source"] == {"path": FAZ7C_EXPLORATION["path"], "sha256": FAZ7C_EXPLORATION["sha256"],
                                                 "kind": "exploration"}
    assert sha256_file(ROOT / FAZ7C_EXPLORATION["path"]) == FAZ7C_EXPLORATION["sha256"]


# ================================================================ gerçek depo: ek kayıtların kuru koşusu / commit'li ek kayıtlar

def _real_deltas():
    out = []
    for p in sorted(reg.OOT_RECORDS_DIR.rglob("*.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("record_scope") == fz.OOT_DELTA_SCOPE:
            out.append((p, rec))
    return out


def test_real_second_records_hold_the_eight_models_with_byte_equal_inputs():
    """K2: ek kayıtlar commit'liyse her MEMBER'da tam bir ek kayıt, tam 8 yeni model, girdiler ilk kayıtla bayt-eşit, sonuç alanı yok;
    yoksa (commit C durumu) aynı denetim bellekte kuru koşuyla (yazmadan). Kod basılmaz: iletiler yalnız sayı."""
    _, rows = reg.read_cohort()
    members = reg.cohort_members(rows)
    deltas = _real_deltas()
    if deltas:
        recs = [(p, r) for p, r in deltas]
        assert len(recs) == len(members) == 135
    else:
        built = fz.build_oot_delta_records(now=NOW, require_clean=False)
        assert built["complete"] == [] and built["skipped"] == [] and len(built["records"]) == 135
        recs = [(None, r) for _, r in built["records"]]
    bad = 0
    for p, rec in recs:
        first_path, first = fz.oot_base_record(rec["ticker"])
        bad += [c["model_id"] for c in rec["models"]] != NEW_IDS
        bad += fz.oot_delta_problems(first, rec) != []
        bad += rec["delta_of"] != first_path.name or rec["delta_of_sha256"] != sha256_file(first_path)
        bad += bool(set(reg.json_keys(rec)) & reg.OOT_OUTCOME_KEYS)
        bad += "vault" in rec or "vault" in rec["cohort_row"] or (p is not None and b'"vault"' in p.read_bytes())
        bad += rec["models_index"]["sha256"] != sha256_file(ROOT / "models" / "INDEX.json")
    assert bad == 0

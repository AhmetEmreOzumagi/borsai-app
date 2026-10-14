"""Canlı POST_D1 akışı (BORSAI_FAZ5_POST_D1_LIVE; SPEC_POST_D1_V0 §7, §9, §11-13, §11-14; SPEC_DEVIATIONS H28–H47).

§11-13 (a)–(j) geçici git depolarında (push kanıtı taklidi, zaman damgası enjeksiyonu; sistem saatine dokunulmaz); kayıt
şeması ve yazıcı (NETGL'in gerçek pinli D_1 bülteniyle, geçici dizinde); payda ve j = 1 blok (sentetik bağlam); L4 uçtan uca
prova (geçici klon), L5 bülten sütunları, L6 takvim sınırı, L7 bekçi, L8 kart, L9 varyant sayacı."""
from __future__ import annotations

import inspect
import json
import subprocess
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from borsai import freeze as fz
from borsai import outcomes as oc
from borsai import predict_path as pth
from borsai import predict_post_d1 as pd1
from borsai import registry as reg
from borsai import scoring as sc
from borsai.provenance import ROOT, pretty_json_bytes

import faz5_live_support as fls
import faz5_support as fs
import faz7_support as fs7
import faz7c_support as fs7c
import faz8_support as fs8
from test_scoring_conditional import S_MODEL, S_RULES, realized

MODEL = "post_d1_hazard_v0"
IST = timezone(timedelta(hours=3))
D1 = "2026-10-01"                       # Perşembe; D2_cal = 2026-10-02 (Cuma), T_open = 06:40:00Z
T_OPEN_Z = "2026-10-02T06:40:00Z"
NETGL_NOW = fls.PROVA_NOW


@pytest.fixture(scope="module")
def calendar():
    return oc.load_calendar()


@pytest.fixture(scope="module")
def netgl(tmp_path_factory, calendar):
    """NETGL'in gerçek D_1 bülteni ve birincil kaydıyla kayıt (gerçek repodan okunur, geçici dizine yazılır)."""
    post_dir = tmp_path_factory.mktemp("post_d1")
    path = fz.write_post_d1_record("NETGL", now=NETGL_NOW, post_dir=post_dir, calendar=calendar)
    return path, json.loads(path.read_text(encoding="utf-8")), post_dir


@pytest.fixture(scope="module")
def committed_scores():
    return json.loads((ROOT / "scores" / "scores.json").read_text(encoding="utf-8"))


def _manifest():
    return {(r["date"], r["kind"]): r for r in oc.read_manifest()}


# ---------------------------------------------------------------- §11-13 geçici git deposu senaryoları

def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


def _commit(root, rel, text="x"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    _git(root, "add", rel)
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", rel)
    return _git(root, "rev-parse", "HEAD")


def _outcome_csv(dates, n_filled):
    rows = []
    for h in range(1, 11):
        r = dict.fromkeys(oc.OUTCOME_COLUMNS, "")
        filled = h <= n_filled
        r.update(h=str(h), session_date=dates[h - 1] if filled else "", ceiling_close="1" if filled else "",
                 status=oc.STATUS_OK if filled else oc.STATUS_PENDING)
        rows.append(",".join(r[c] for c in oc.OUTCOME_COLUMNS))
    return ",".join(oc.OUTCOME_COLUMNS) + "\n" + "\n".join(rows) + "\n"


def scenario(tmp_path, calendar, steps, *, pit_ok=True, d1=D1):
    """steps: sırayla (adım, kanıt zamanı | None). Adımlar: model, d1_bulletin, d1_outcome, record, d2_bulletin, d2_outcome.
    Dönen: class_post_d1(...) -> (sınıf, kanıt)."""
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    _git(root, "init", "-q")
    dates = list(calendar.sessions_from(d1)[:10])
    bist = root / "data" / "raw" / "bist"
    paths = {"model": ["models/p.json"], "record": ["registry/post_d1/X/r.json"],
             "d1_bulletin": [oc.local_path(dates[0], k, bist).relative_to(root).as_posix() for k in oc.KINDS],
             "d2_bulletin": [oc.local_path(dates[1], k, bist).relative_to(root).as_posix() for k in oc.KINDS]}
    proofs, commits = [], {}
    for what, at in steps:
        if what in ("d1_outcome", "d2_outcome"):
            commits[what] = _commit(root, "data/outcomes/X.csv", _outcome_csv(dates, 1 if what == "d1_outcome" else 2))
        else:
            for rel in paths[what]:
                commits[what] = _commit(root, rel)
        if at:
            proofs.append({"proven_commit_sha": commits[what], "created_at": at})
    git = sc.Git(root)
    model_ev = sc.model_evidence(git, "p.json", proofs)
    oc_commit = sc.outcome_ingest_commit_post_d1(git, "X", dates[0])
    push = sc.proof_time(git, git.added_commit("registry/post_d1/X/r.json"), proofs)
    return sc.class_post_d1(git, model_ev, oc_commit, push, reg.t_open(dates[0], calendar), pit_ok, dates[0])


LIVE_FLOW = [("model", "2026-09-30T10:00:00Z"), ("d1_bulletin", None), ("d1_outcome", None)]


def test_13a_live(tmp_path, calendar):
    """(a) model → D1 bülteni + sonuç (h = 1) → kayıt + kanıt < T_open → D2 bülteni ⇒ LIVE."""
    cls, ev = scenario(tmp_path, calendar, LIVE_FLOW + [("record", "2026-10-01T17:00:00Z"), ("d2_bulletin", None),
                                                        ("d2_outcome", None)])
    assert cls == sc.CLASS_LIVE and ev["model_prospective"] and ev["record_live"]
    assert ev["t_open"] == "2026-10-02T09:40:00+03:00" and ev["outcome_ingest_basis"] == "COMMITTED"


def test_13a2_boundary_is_strict_and_uses_instants(tmp_path, calendar):
    """Kanıt T_open'dan 1 saniye önce LIVE; tam T_open'da değil (kesin <; an karşılaştırması, tarih değil)."""
    cls, _ = scenario(tmp_path, calendar, LIVE_FLOW + [("record", "2026-10-02T06:39:59Z"), ("d2_bulletin", None)])
    assert cls == sc.CLASS_LIVE
    assert not sc.record_live_post_d1(T_OPEN_Z, reg.t_open(D1, calendar))
    assert sc.record_live_post_d1("2026-10-02T09:39:59+03:00", reg.t_open(D1, calendar))


def test_13b_proof_at_or_after_t_open_is_late_record(tmp_path, calendar):
    """(b) kanıt ≥ T_open ⇒ LATE_RECORD (model prospektif, inputs_pit_ok_post_d1)."""
    cls, ev = scenario(tmp_path, calendar, LIVE_FLOW + [("record", T_OPEN_Z), ("d2_bulletin", None)])
    assert cls == sc.CLASS_LATE and ev["model_prospective"] and not ev["record_live"]


def test_13c_d2_bulletin_before_model_is_retro(tmp_path, calendar):
    """(c) D2 bülteni modelden önce repoya girdi ⇒ RETRO (kayıt kanıtı T_open'dan önce olsa da)."""
    cls, ev = scenario(tmp_path, calendar, [("d1_bulletin", None), ("d2_bulletin", None), ("model", "2026-09-30T10:00:00Z"),
                                            ("record", "2026-10-01T17:00:00Z")])
    assert cls == sc.CLASS_RETRO and not ev["model_prospective"]


def test_13c2_h_ge_2_outcome_row_also_counts_as_ingest(tmp_path, calendar):
    """outcome_ingest_commit_post_d1 = min(bülten, h ≥ 2 dolu satır): satır bültenden önce girmişse (bekçi ihlali) o da sayılır."""
    cls, ev = scenario(tmp_path, calendar, [("d2_outcome", None), ("model", "2026-09-30T10:00:00Z"),
                                            ("record", "2026-10-01T17:00:00Z"), ("d2_bulletin", None)])
    assert cls == sc.CLASS_RETRO and not ev["model_prospective"]


@pytest.mark.requires_raw_sources
def test_13d_non_d1_bulletin_sha_makes_pit_false_retro_and_guard_red(tmp_path, calendar, netgl):
    """(d) kayıtta D_1 dışı tarihli bülten sha'sı ⇒ inputs_pit_ok_post_d1 yanlış ⇒ (geç kayıtta) RETRO; bekçi kırmızı."""
    _, rec, _ = netgl
    d1 = rec["d1"]["session_date"]
    man = _manifest()
    assert sc.inputs_pit_problems_post_d1(rec, d1, manifest=man) == []
    bad = json.loads(json.dumps(rec))
    other = next(k for k in sorted(man) if k[0] > d1 and k[1] == "thm")
    bad["d1"]["thm"]["sha256"] = man[other]["sha256"]
    pit = sc.inputs_pit_problems_post_d1(bad, d1, manifest=man)
    assert pit and reg.post_d1_record_problems(bad, man)
    late = LIVE_FLOW + [("record", T_OPEN_Z), ("d2_bulletin", None)]
    assert scenario(tmp_path / "ok", calendar, late, pit_ok=True)[0] == sc.CLASS_LATE
    assert scenario(tmp_path / "bad", calendar, late, pit_ok=not pit)[0] == sc.CLASS_RETRO


def test_13e_no_base_record_no_post_d1_record(tmp_path, calendar):
    """(e) uygun listeleme öncesi kayıt yok ⇒ POST_D1 kaydı yazılmaz (NoBaseRecord, SKIPPED_POST_D1 kodu)."""
    empty = tmp_path / "records"
    empty.mkdir()
    post_dir = tmp_path / "post_d1"
    with pytest.raises(fz.NoBaseRecord) as exc:
        fz.write_post_d1_record("NETGL", now=NETGL_NOW, post_dir=post_dir, records_dir=empty, calendar=calendar)
    assert exc.value.code == "SKIPPED_POST_D1: NO_PRE_LISTING_RECORD"
    assert not post_dir.exists()


@pytest.mark.requires_raw_sources
def test_13f_cancel_only_before_t_open(tmp_path, calendar):
    """(f) T_open sonrası iptal ⇒ hata; öncesinde iptal kaydı aynı dizinde, iptal edilen dosya değişmez."""
    post_dir = tmp_path / "post_d1"
    path = fz.write_post_d1_record("NETGL", now=NETGL_NOW, post_dir=post_dir, calendar=calendar)
    before = path.read_bytes()
    t_open_at = reg.t_open("2026-09-17", calendar)
    with pytest.raises(fz.FreezeError, match="T_open"):
        fz.cancel_post_d1_record(path, "deneme", now=t_open_at, post_dir=post_dir, calendar=calendar)
    with pytest.raises(fz.FreezeError, match="T_open"):
        fz.cancel_post_d1_record(path, "deneme", now=t_open_at + timedelta(days=3), post_dir=post_dir, calendar=calendar)
    c = fz.cancel_post_d1_record(path, "bülten yeniden indirildi", now=t_open_at - timedelta(seconds=1), post_dir=post_dir,
                                 calendar=calendar)
    doc = json.loads(c.read_text(encoding="utf-8"))
    assert doc["record_type"] == "CANCELLATION" and doc["record_stage"] == "POST_D1" and doc["cancels"]["file"] == path.name
    assert c.parent == path.parent and path.read_bytes() == before
    assert fz.active_post_d1_records("NETGL", post_dir) == []
    with pytest.raises(fz.FreezeError, match="etkin"):
        fz.cancel_post_d1_record(path, "ikinci", now=NETGL_NOW, post_dir=post_dir, calendar=calendar)


def test_13g_half_day_d2_cal_still_0940(calendar):
    """(g) D2_cal yarım gün (2026-10-28) olsa da T_open 09:40:00+03:00 (Ek-9: açılış emir toplama tam ve yarım günde aynı)."""
    assert calendar.is_half("2026-10-28") and reg.d2_cal("2026-10-27", calendar) == "2026-10-28"
    assert reg.t_open("2026-10-27", calendar) == datetime(2026, 10, 28, 9, 40, tzinfo=IST)


def test_13h_unannounced_closure_on_next_day_same_rule(calendar):
    """(h) D_1'i izleyen takvim günü ilan dışı kapanış olsa da sınır aynı kuraldır (§7.3 lafzı, H32): D2_cal kapanışın
    düşüldüğü resmi takvimde D_1'den sonraki ilk seans, T_open onun 09:40'ı; özel durum ya da yerel saat yok."""
    cal2 = calendar.without(["2026-10-02"])
    assert reg.d2_cal(D1, calendar) == "2026-10-02" and reg.d2_cal(D1, cal2) == "2026-10-05"
    assert reg.t_open(D1, cal2) == datetime(2026, 10, 5, 9, 40, tzinfo=IST)
    assert reg.t_open(D1, cal2).timetz() == reg.t_open(D1, calendar).timetz()


@pytest.mark.requires_raw_sources
def test_13i_comparator_copy_equals_faz2c_j1_row(netgl, committed_scores):
    """(i) comparators_conditional kopyası, Faz 2C scores.json j = 1 NETGL satırıyla |Δ| ≤ 1e-12; aşım -> ScoringError."""
    _, rec, _ = netgl
    haz = next(m for m in committed_scores["models"] if m["model_id"] == "ceiling_hazard_v0")
    row = next(r for r in next(b for b in haz["conditional"]["by_j"] if b["j"] == 1)["rows"] if r["ticker"] == "NETGL")
    rules = {rid: {"S_cond": v["S_cond"]} for rid, v in rec["comparators_conditional"].items()}
    par = sc.post_d1_comparator_parity(rules, row)
    assert par["status"] == "OK" and par["max_abs_diff"] <= 1e-12
    for rid, v in rec["comparators_conditional"].items():
        assert v["S_cond"] == {str(k): x for k, x in pth.conditional_weights(v["S"], 1)[0].items()}
    rules["base_km_last10"] = {"S_cond": {k: x + 1e-9 for k, x in rules["base_km_last10"]["S_cond"].items()}}
    with pytest.raises(sc.ScoringError, match="1e-12"):
        sc.post_d1_comparator_parity(rules, row)
    assert sc.post_d1_comparator_parity(rules, None)["status"] == "NOT_AVAILABLE"


def test_13j_t_open_from_constant_no_local_clock(calendar, monkeypatch):
    """(j) T_open, Ek-9 sabitinden (09:40:00+03:00); sistem saat dilimi değişse de aynı; kodda yerel saat çağrısı yok."""
    want = reg.t_open(D1, calendar)
    assert want.isoformat() == "2026-10-02T09:40:00+03:00" and (reg.T_OPEN_TIME.hour, reg.T_OPEN_TIME.minute) == (9, 40)
    monkeypatch.setenv("TZ", "Pacific/Kiritimati")
    time.tzset()
    try:
        assert reg.t_open(D1, calendar) == want and reg.t_open(D1, calendar).utcoffset() == timedelta(hours=3)
    finally:
        monkeypatch.undo()
        time.tzset()
    for fn in (reg.t_open, reg.d2_cal, reg.before_t_open, reg.select_primary_post_d1, sc.record_live_post_d1, sc.class_post_d1):
        src = inspect.getsource(fn)
        assert "now(" not in src and "time.time" not in src and "localtime" not in src, fn.__name__


# ---------------------------------------------------------------- kayıt yazıcı (NETGL, gerçek D_1 bülteni)

@pytest.mark.requires_raw_sources
def test_record_schema_is_7_4_exactly(netgl):
    path, rec, post_dir = netgl
    assert fls.schema_problems(rec) == []
    assert path.parent == post_dir / "NETGL" and path.name.startswith("20260917T160000Z_")
    assert rec["models_index"] == {"path": "models/INDEX_POST_D1.json", "model_ids": [MODEL],
                                   "sha256": fz.sha256_file(ROOT / "models" / "INDEX_POST_D1.json")}
    assert [c["model_id"] for c in rec["models"]] == [e["model_id"] for e in
                                                     json.loads((ROOT / "models" / "INDEX_POST_D1.json").read_text())["models"]]
    assert rec["models"][0]["params_sha256"] == fz.sha256_file(ROOT / "models" / f"{MODEL}.json")
    assert rec["comparators_conditional"]["base_always_ceiling"]["source"] == fz.ALWAYS_CEILING_SOURCE
    assert all(v["source"] == "base_record" for k, v in rec["comparators_conditional"].items() if k != "base_always_ceiling")


@pytest.mark.requires_raw_sources
def test_record_models_equal_direct_predict(netgl):
    _, rec, _ = netgl
    base = json.loads((ROOT / rec["base_record"]["file"]).read_text(encoding="utf-8"))
    params = json.loads((ROOT / "models" / f"{MODEL}.json").read_text(encoding="utf-8"))
    parent = json.loads((ROOT / "models" / "ceiling_hazard_v0.json").read_text(encoding="utf-8"))
    d1 = {k: rec["d1"][k] for k in ("fields_raw", "half_day", "halt_flag")}
    direct = pd1.predict_post_d1(params, parent, base["model_inputs"], d1)
    assert json.loads(json.dumps(direct)) == rec["models"][0]["output"]
    assert rec["models"][0]["output"]["hazard"][0] == base["models"][[c["model_id"] for c in base["models"]].index(
        "ceiling_hazard_v0")]["output"]["hazard"][0]                                      # h_1 ana modelden (bit-eşit)
    assert rec["base_record"]["model_inputs_sha256"] == fz.canonical_sha256(base["model_inputs"])


@pytest.mark.requires_raw_sources
def test_record_uses_only_d1_bulletins(netgl):
    _, rec, _ = netgl
    man = _manifest()
    d1 = rec["d1"]["session_date"]
    assert reg.post_d1_record_problems(rec, man) == []
    for kind in oc.KINDS:
        assert rec["d1"][kind]["sha256"] == man[(d1, kind)]["sha256"] == fz.sha256_file(ROOT / rec["d1"][kind]["file"])
    row = oc.read_outcome(oc.outcome_path("NETGL"))[0]
    assert (row["session_date"], row["thb_sha256"], row["thm_sha256"]) == (d1, rec["d1"]["thb"]["sha256"], rec["d1"]["thm"]["sha256"])
    fr = rec["d1"]["fields_raw"]
    assert fr["close"] == row["close_raw"] and fr["upper_limit"] == row["upper_limit_raw"]
    assert rec["d1"]["ceiling_close_D1"] == int(Decimal(fr["close"]) == Decimal(fr["upper_limit"])) == int(row["ceiling_close"])


def test_record_refuses_without_d1_and_on_bad_params(tmp_path, calendar):
    """§9: D_1 yoksa (sonuç dosyası yok / h = 1 bekleniyor) kayıt yazılmaz (D1_NOT_TRADED); parent sha uyuşmazlığı PARAMS_INVALID."""
    with pytest.raises(fz.D1NotAvailable) as exc:
        fz.build_post_d1_record("NETGL", now=NETGL_NOW, outcomes_dir=tmp_path, calendar=calendar)
    assert exc.value.code == "D1_NOT_TRADED"
    (tmp_path / "NETGL.csv").write_text(_outcome_csv([""] * 10, 0), encoding="utf-8")
    with pytest.raises(fz.D1NotAvailable):
        fz.build_post_d1_record("NETGL", now=NETGL_NOW, outcomes_dir=tmp_path, calendar=calendar)
    with pytest.raises(fz.FreezeError, match="PARAMS_INVALID"):
        fz._frozen_ref(ROOT / "models", {"model_id": "ceiling_hazard_v0", "file": "ceiling_hazard_v0.json", "sha256": "0" * 64})


@pytest.mark.requires_raw_sources
def test_duplicate_post_d1_record(tmp_path, calendar):
    post_dir = tmp_path / "post_d1"
    first = fz.write_post_d1_record("NETGL", now=NETGL_NOW, post_dir=post_dir, calendar=calendar)
    with pytest.raises(fz.DuplicateRecord, match="DUPLICATE_RECORD"):
        fz.write_post_d1_record("NETGL", now=NETGL_NOW + timedelta(minutes=5), post_dir=post_dir, calendar=calendar)
    fz.cancel_post_d1_record(first, "yeniden", now=NETGL_NOW + timedelta(minutes=1), post_dir=post_dir, calendar=calendar)
    second = fz.write_post_d1_record("NETGL", now=NETGL_NOW + timedelta(minutes=5), post_dir=post_dir, calendar=calendar)
    assert second != first and first.exists()


@pytest.mark.requires_raw_sources
def test_base_record_selection_matches_scoring_primary(netgl):
    """base_record = skorlamanın ceiling_hazard_v0 birincil kaydı (aynı kural, aynı aday kurucusu)."""
    _, rec, _ = netgl
    ctx = sc.load_context()
    sel = sc.select(ctx, "NETGL", "ceiling_hazard_v0", rec["d1"]["session_date"])["selection"]["proven"]
    assert sel["record_id"] == rec["base_record"]["file"].rsplit("/", 1)[1]


@pytest.mark.requires_raw_sources
def test_d1_block_fields_are_raw_text_and_columns_named(netgl):
    _, rec, _ = netgl
    assert set(rec["d1"]["fields_raw"]) == set(reg.POST_D1_FIELDS_RAW)
    assert all(isinstance(v, str) for v in rec["d1"]["fields_raw"].values())
    assert rec["d1"]["session_h"] == 1 and rec["d1_features"]["d1_lock"] in (0, 1)


# ---------------------------------------------------------------- birincil POST_D1 kaydı, hedefler

def test_select_primary_post_d1():
    t = datetime(2026, 10, 2, 9, 40, tzinfo=IST)
    C = reg.PostD1Candidate
    live = [C("a.json", "2026-10-01T15:00:00Z", "2026-10-01T18:00:00Z"), C("b.json", "2026-10-01T16:00:00Z", "2026-10-01T17:00:00Z")]
    assert reg.select_primary_post_d1(live, t) == {"record_id": "b.json", "rule": "EARLIEST_PUSH_PROVEN_BEFORE_T_OPEN"}
    late = [C("c.json", "2026-10-02T10:00:00Z", "2026-10-02T11:00:00Z"), C("d.json", "2026-10-01T10:00:00Z", None)]
    assert reg.select_primary_post_d1(late, t) == {"record_id": "c.json", "rule": "EARLIEST_INPUTS_PIT_OK"}
    assert reg.select_primary_post_d1([C("e.json", "x", None, inputs_pit_ok=False)], t)["record_id"] is None
    assert reg.select_primary_post_d1([C("f.json", "x", "2026-10-01T17:00:00Z", cancelled=True)], t)["record_id"] is None


def test_need_names_post_d1_never_d1():
    names = sc._need_names("post_d1")
    assert names == [f"ceiling_close_D{k}" for k in range(2, 11)]
    assert sc._need_names("post_d1", path=True) == names + ["D3", "D5", "D10"]
    assert not any(n.endswith("D1") or n == "L" for n in sc._need_names("post_d1", path=True))
    r = realized("X", 3, n_in=1)
    assert sc._needs("post_d1", r) == [oc.STATUS_PENDING] * 9


# ---------------------------------------------------------------- satır, hücre, ölçek (sentetik)

def _rec(S=S_MODEL, *, status="PREDICTED", path_conditional=None):
    comps = {rid: {"record_cell_sha256": None, "S": list(v), "S_cond": None, "source": "base_record"} for rid, v in S_RULES.items()
             if rid in fz.POST_D1_COMPARATORS}
    comps["base_always_ceiling"] = {"record_cell_sha256": None, "S": [1.0] * 10, "S_cond": None, "source": fz.ALWAYS_CEILING_SOURCE}
    comps["ceiling_hazard_v0"] = {"record_cell_sha256": None, "S": [0.9, 0.7, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1, 0.08, 0.05],
                                  "S_cond": None, "source": "base_record"}
    for v in comps.values():
        v["S_cond"] = {str(k): x for k, x in pth.conditional_weights(v["S"], 1)[0].items()}
    refusal = {"code": "F3_MISSING", "field": "f3", "reason": "x"} if status == "REFUSED" else None
    return {"base_record": {"file": "registry/records/X/yok.json"}, "comparators_conditional": comps,
            "models": [{"model_id": MODEL, "status": status, "refusal": refusal,
                        "output": {"S": list(S), "path_conditional": path_conditional}}]}


def _row(ticker, L, klass=sc.CLASS_LIVE, d1="2027-01-10", **kw):
    r = realized(ticker, L, d1=d1, **{k: v for k, v in kw.items() if k in ("n_in", "status_at", "na_at")})
    rec = _rec(**{k: v for k, v in kw.items() if k in ("S", "status", "path_conditional")})
    return sc.post_d1_row(MODEL, ticker, d1, klass, ROOT / f"{ticker}.json", rec, r, datetime(2027, 1, 11, 9, 40, tzinfo=IST),
                          {}, [], None, None, ROOT)


def test_post_d1_row_metrics_are_shared_functions_and_d1_not_scored():
    row = _row("A", 4)
    want_S = {str(k): x for k, x in pth.conditional_weights(S_MODEL, 1)[0].items()}
    assert row["status"] == sc.ROW_SCORED and row["S_cond"] == want_S and list(row["S_cond"]) == [str(k) for k in range(2, 11)]
    assert row["rps_cond"] == pth.conditional_rps(S_MODEL, 1, 4)
    assert (row["brier_next"], row["brier_10"]) == (pth.conditional_brier(S_MODEL, 1, 4, 2), pth.conditional_brier(S_MODEL, 1, 4, 10))
    assert row["rules"]["ceiling_hazard_v0"]["rps_cond"] == pth.conditional_rps(_rec()["comparators_conditional"]["ceiling_hazard_v0"]["S"], 1, 4)
    assert row["comparator_parity"]["status"] == "NOT_AVAILABLE"
    assert _row("B", 4, n_in=5)["status"] == sc.ROW_PENDING                               # D6 bekleniyor
    assert _row("C", 4, status="REFUSED")["status"] == sc.ROW_REFUSED
    # D1 hedefi skorlanmaz: D1 satırının durumu (ör. NA etiket) satırı değiştirmez, yalnız D2..D10
    assert _row("D", 4, status_at={1: oc.STATUS_NA_LIMIT})["status"] == sc.ROW_SCORED


def test_path_not_produced():
    """§11-11: path_conditional null -> path satırı NOT_PRODUCED (TARGET_UNAVAILABLE değil); karşılaştırıcı da üretilmez."""
    row = _row("P", 3)
    assert row["path"] is None and row["path_status"] == sc.ROW_NOT_PRODUCED
    assert row["rules"][sc.POST_D1_PATH_COMPARATOR] == {"record_id": None, "not_produced": True}
    assert sc._cond_losses(row, "return_cond", "D5", "MAE", sc.POST_D1_PATH_COMPARATOR) is None


def twelve_rows():
    Ls = [1, 1, 2, 2, 1, 2, 1, 2, 3, 5, 7, 10]
    return [_row(f"P{i:02d}", L, klass=sc.CLASS_LIVE if i % 2 else sc.CLASS_LATE, d1=f"2027-{i + 1:02d}-10") for i, L in enumerate(Ls)]


def test_post_d1_cells_small_n_rules_and_labels():
    rows = twelve_rows()
    cells = sc.post_d1_cells(rows)
    s_specs = [s for s in sc.post_d1_cell_specs() if s[0] == "S_cond"]
    assert [(c["output"], c["horizon_or_k"], c["metric"], c["rule_id"]) for c in cells] == s_specs   # path: NOT_PRODUCED
    assert all(c["n"] == 12 and c["scale"] == sc.SCALE_LIVE_POST_D1 and c["verdict"] == sc.V_SMALL for c in cells)
    assert [c["rule_id"] for c in cells if c["label"] == "birincil"] == ["ceiling_hazard_v0"]
    assert {c["label"] for c in cells if c["metric"] == "RPS" and c["rule_id"] != "ceiling_hazard_v0"} == {"kural"}
    assert {c["label"] for c in cells if c["metric"] == "Brier"} == {"ikincil"}
    assert sc.post_d1_cells(rows[:9]) == [] and len(sc.post_d1_descriptive(rows)) == 5 and sc.post_d1_descriptive(rows[:9]) == []
    assert sc.POST_D1_PRIMARY == {"output": "S_cond", "horizon_or_k": None, "metric": "RPS", "rule_ids": ["ceiling_hazard_v0"]}


def test_scale_mix_post_d1():
    rows = twelve_rows()
    post = sc.post_d1_obs(rows, "S_cond", None, "RPS", "ceiling_hazard_v0")
    cond = [sc.PairedObs(sc.SCALE_LIVE_CONDITIONAL, f"C{i}", "2027-01", 0.1, 0.2, sc.CLASS_LATE, 1) for i in range(12)]
    live = [sc.PairedObs(sc.SCALE_LIVE, f"L{i}", "2027-01", 0.1, 0.2, sc.CLASS_LATE) for i in range(12)]
    bt = [sc.PairedObs(sc.SCALE_BACKTEST, "B", "2027-01", 0.1, 0.2)]
    for other in (cond, live, bt):
        with pytest.raises(sc.ScaleMixError):
            sc.paired_metric(post + other)
    for other in (sc.SCALE_LIVE, sc.SCALE_LIVE_CONDITIONAL, sc.SCALE_BACKTEST, sc.SCALE_LIVE_POST_D1):
        with pytest.raises(sc.ScaleMixError):
            sc.merge_scales({"scale": sc.SCALE_LIVE_POST_D1}, {"scale": other})
    assert sc.paired_metric(post)["scale"] == sc.SCALE_LIVE_POST_D1


# ---------------------------------------------------------------- payda (§7.5) sentetik bağlamda

def _ctx(tmp_path, units, *, model_proof=True):
    """units: {ticker: Realized | None}. Model dosyası geçici depoda commit'li (kanıtlı ya da değil); sonuç commit'siz."""
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    _git(root, "init", "-q")
    sha = _commit(root, "models/p.json", "{}")
    proofs = [{"proven_commit_sha": sha, "created_at": "2026-09-30T10:00:00Z"}] if model_proof else []
    ipos = [{"ticker": t, "status": "FROZEN", "first_trading_date": (r.d1 if r and r.d1 else "2027-01-10")} for t, r in units.items()]
    ctx = sc.Context(git=sc.Git(root), proofs=proofs, index={"models": []}, models={}, legacy={"records": []}, ipos=ipos,
                     realized=dict(units), records={t: [] for t in units}, cancelled={t: {} for t in units}, inputs_docs={},
                     root=root)
    entry = {"model_id": MODEL, "file": "p.json", "frozen_at": "x", "sha256": "0" * 64}
    pctx = sc.PostD1Context(None, [entry], {MODEL: {"path_secondary": {"model_id": "ceiling_path_v0"}}}, {}, {}, {},
                            oc.load_calendar())
    return ctx, pctx, entry


def test_denominator_rows(tmp_path):
    units = {"CEIL": realized("CEIL", 3, d1="2026-10-01"), "NOTC": realized("NOTC", 0, d1="2026-10-01"),
             "NALB": realized("NALB", 3, d1="2026-10-01", na_at=(1,)), "WAIT": realized("WAIT", 3, n_in=0, d1="2026-10-01"),
             "NOOUT": None}
    ctx, pctx, entry = _ctx(tmp_path, units)
    block, retro = sc.post_d1_block(ctx, pctx, entry, {})
    st = {d["ticker"]: (d["stage_status"], d["skip_reason"]) for d in block["denominator"]}
    assert st == {"CEIL": ("SKIPPED_POST_D1", "NO_PRE_LISTING_RECORD"), "NOTC": ("NOT_APPLICABLE", None),
                  "NALB": ("NOT_SCORABLE_D1_LABEL_NA", None), "WAIT": ("D1_PENDING", None), "NOOUT": ("D1_PENDING", None)}
    assert (block["n_skipped"], block["n_not_applicable"], block["n_d1_label_na"], block["n_undetermined"]) == (1, 1, 1, 2)
    assert (block["n_scored"], block["n_live"], block["n_late"], block["rows"], block["cells"], retro) == (0, 0, 0, [], [], [])
    # push kanıtı olmayan model: her arz RETRO (retro_info), hiçbir n'e girmez
    ctx2, pctx2, entry2 = _ctx(tmp_path / "noproof", units, model_proof=False)
    block2, retro2 = sc.post_d1_block(ctx2, pctx2, entry2, {})
    assert {x["ticker"] for x in retro2} == set(units) and block2["n_retro"] == 5
    assert (block2["n_skipped"], block2["n_not_applicable"], block2["n_scored"]) == (0, 0, 0)


def test_denominator_live_row_end_to_end(tmp_path):
    """(a)'nın skorlama tarafı: kanıtlı kayıt T_open'dan önce -> satır LIVE, n_live = 1; D2 bülteni commit'siz (HEAD'e karşı)."""
    r = realized("LV", 4, d1="2026-10-01")
    ctx, pctx, entry = _ctx(tmp_path, {"LV": r})
    rec = {**_rec(), "record_type": "PREDICTION", "ticker": "LV", "recorded_at_utc": "2026-10-01T16:00:00Z",
           "d1": {"session_date": "2026-10-01"}}
    rel = "registry/post_d1/LV/r.json"
    sha = _commit(ctx.root, rel, json.dumps(rec))
    ctx.proofs.append({"proven_commit_sha": sha, "created_at": "2026-10-01T17:00:00Z"})
    pctx.records["LV"] = [(ctx.root / rel, rec)]
    block, retro = sc.post_d1_block(ctx, pctx, entry, {})
    assert retro == [] and block["n_scored"] == block["n_live"] == 1 and block["n_late"] == 0
    row = block["rows"][0]
    assert row["class"] == sc.CLASS_LIVE and row["record_id"] == "r.json" and row["L"] == 4
    assert row["inputs_pit_problems"]                                   # sentetik kayıt pit değil; LIVE için gerekmez
    assert row["class_evidence"]["selection_rule"] == "EARLIEST_PUSH_PROVEN_BEFORE_T_OPEN"


# ---------------------------------------------------------------- gerçek veri: 7 arz RETRO (L3), L8, L9

@pytest.fixture(scope="module")
def built():
    scores = sc.build_scores()
    return scores, sc.build_post_d1_scores(scores)


@pytest.mark.requires_git_history
def test_real_seven_are_retro_info_only(built):
    """L3: bugünkü 7 arz bu model için RETRO: yalnız retro_info; sayaçlar 0, satır ve hücre yok; gerçek registry/post_d1 boş."""
    _, post = built
    [m] = post["models"]
    b = m["conditional_j1"]
    assert m["model_id"] == MODEL and m["kind"] == "post_d1" and post["schema_version"] == sc.POST_D1_SCHEMA
    for k in ("n_scored", "n_refused", "n_skipped", "n_not_applicable", "n_target_unavailable", "n_live", "n_late", "n_pending"):
        assert b[k] == 0, k
    assert b["rows"] == [] and b["cells"] == [] and b["descriptive"] == []
    frozen = [r["ticker"] for r in reg.read_ipos()[1] if r["status"] == "FROZEN"]
    assert [x["ticker"] for x in post["retro_info"]] == frozen and set(frozen) == set(reg.KNOWN_TICKERS) and b["n_retro"] == 7
    assert all(d["stage_status"] == "RETRO" for d in b["denominator"])
    assert all(not x["class_evidence"]["model_prospective"] and x["class_evidence"]["outcome_ingest_basis"] == "COMMITTED"
               for x in post["retro_info"])
    assert not list((ROOT / "registry" / "post_d1").rglob("*"))


@pytest.mark.requires_git_history
def test_scores_json_structure_unchanged_by_post_d1(built):
    """L1: scores.json'a POST_D1 bloğu eklenmez; modeller yalnız INDEX.json'dakiler."""
    scores, _ = built
    assert MODEL not in {m["model_id"] for m in scores["models"]} and "post_d1" not in json.dumps(list(scores))
    assert all("conditional_j1" not in m for m in scores["models"])


@pytest.mark.requires_git_history
def test_l8_card_does_not_call_it_cutoff(built):
    _, post = built
    card = post["models"][0]["card"]
    assert "training_cutoff" not in card and card["training_last_session_date"] == "2026-08-13"
    assert card["spec_training_cutoff"] == "2026-08-19" and "kesim değil" in card["training_last_session_date_meaning"]
    doc = sc.render_doc(json.loads(pretty_json_bytes(built[0])), json.loads(pretty_json_bytes(post)))
    part = doc.partition("## 7. D1 sonrası güncelleme")[2]
    assert "2026-08-13 (kesim değil" in part and "kesim 2026-08-13" not in part


@pytest.mark.requires_git_history
def test_l9_variant_counter_is_20_and_allowance_retires(built):
    """L9 (AUDIT K5): yeniden üretimde bütün kartlarda n_variants_same_data = 20; commit edilen scores.json ya Faz 5 öncesi
    haliyle bayt-eşittir (19, H22 istisnası) ya da tam 20'dir (istisna kendiliğinden devre dışı)."""
    scores, post = built
    # Faz 7 (SPEC_DEVIATIONS J): v1_clip/v1_real'in backtest satırları aynı veri sürümünde sayacı tam olarak Faz 7 varyant sayısı kadar
    # artırır; commit edilen scores.json 8e3a623'teki haliyle kaldıkça 20'dir (istisna kendiliğinden devre dışı kalır).
    dv = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"][0]["data_version_sha256"]
    lag7 = fs7.faz7_variants(dv)
    # Faz 7C (SPEC_DEVIATIONS K; aynı kalıp): fall_d10_v0_h99'un backtest satırı H99 sürümünde, üç havuz koşusu ve 2 054 keşif satırı
    # v2 sürümünde sayılır.
    lag7c = fs7c.faz7c_variants(dv)
    # Faz 8 (SPEC_DEVIATIONS N19; proje sahibi kararı 2026-10-01; J16/K10 kalıbı): break_floor_v0'ın backtest satırı H99 sürümünde sayılır;
    # commit edilen scores.json 87434ff'teki haliyle kaldıkça H99 kartları Faz 8 öncesi sayıdadır.
    lag8 = fs8.faz8_variants(dv)
    # Faz 7 dondurmasından sonra (SPEC_DEVIATIONS J23) v1_pooled ve @INF kartları, Faz 7C dondurmasından sonra (K19) (C)'nin
    # pooled, addsale ve @ZERO kartları kendi veri sürümlerinde (v2) sayılır.
    by_dv = {e["model_id"]: e["data_version_sha256"] for e in json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]}
    assert {m["card"]["n_variants_same_data"] for m in scores["models"] if by_dv[m["model_id"]] == dv} == {20 + lag7 + lag7c + lag8}
    for m in scores["models"]:
        if by_dv[m["model_id"]] != dv:
            v = by_dv[m["model_id"]]
            assert m["model_id"] in fs7.frozen_tail_ids() and \
                m["card"]["n_variants_same_data"] == fs7.faz7_variants(v) + fs7c.faz7c_variants(v)
    assert post["models"][0]["card"]["n_variants_same_data"] == 20 + lag7 + lag7c + lag8
    committed = json.loads((ROOT / "scores" / "scores.json").read_text(encoding="utf-8"))
    # BORSAI_FAZ7_OOT_RECORDS (SPEC_DEVIATIONS L): yeniden üretilen dosyada v2 veri sürümündeki kartlar kendi sayacını taşır (yukarıda
    # yeniden hesapla sınandı); H99 sürümündeki kartlar burada.
    counts = {m["card"]["n_variants_same_data"] for m in committed["models"] if by_dv[m["model_id"]] == dv}
    assert counts == ({19} if fs.scores_json_is_pre_faz5() else {20} if fs7.scores_json_is_pre_faz7() else
                      {20 + lag7 + lag7c + (0 if fs8.scores_json_is_pre_faz8() else lag8)})
    for m in committed["models"]:
        if by_dv[m["model_id"]] != dv:
            assert not fs7.scores_json_is_pre_faz7() and \
                m["card"]["n_variants_same_data"] == fs7.faz7_variants(by_dv[m["model_id"]]) + fs7c.faz7c_variants(by_dv[m["model_id"]])


def _stable_post(p):
    p = json.loads(json.dumps(p))
    p.pop("generated_at_utc")
    p.pop("code")
    for x in p["retro_info"]:
        for k in ("outcome_ingest_commit", "checked_against", "outcome_ingest_basis"):
            x["class_evidence"].pop(k, None)
    for m in p["models"]:
        for r in m["conditional_j1"]["rows"]:
            for k in ("outcome_ingest_commit", "checked_against", "outcome_ingest_basis"):
                r["class_evidence"].pop(k, None)
    return p


@pytest.mark.requires_raw_sources
def test_committed_post_d1_scores_match_recomputation(built):
    """B'den sonra: commit edilen scores_post_d1.json yeniden hesapla aynı (üretim anı, kod ve sonuç commit'i dışında).
    A → B arası dosya yoktur; istisna yalnız scores.json Faz 5 öncesi haliyle bayt-eşitken (H28).
    Faz 7 (SPEC_DEVIATIONS J16 kalıbı; docs/faz7/IMPL_RAPOR.md): v1_clip/v1_real'in backtest satırları kartın varyant sayacını
    artırır ve scores/ o görevde yeniden üretilmez. İstisna yalnız scores.json ve scores_post_d1.json 8e3a623'teki halleriyle
    bayt-eşitken ve fark tam olarak günlükteki Faz 7 varyant sayısı kadarken; yeniden üretilen dosya tam karşılaştırılır."""
    committed = sc.load_post_d1_scores()
    if committed is None:
        assert fs.scores_json_is_pre_faz5()
        return
    fresh = built[1]
    if fs7.scores_json_is_pre_faz7() and fs7.scores_post_d1_is_pre_faz7():
        dv = {e["model_id"]: e["data_version_sha256"]
              for e in json.loads((ROOT / "models" / "INDEX_POST_D1.json").read_text(encoding="utf-8"))["models"]}
        fresh = fs7.strip_frozen_faz7(fresh)        # dondurmalardan sonra yalnız inputs.models_index_sha256 (J23, K19)
        for m in fresh["models"]:          # Faz 7C (SPEC_DEVIATIONS K): aynı istisna, Faz 7C varyantlarıyla
            m["card"]["n_variants_same_data"] -= fs7.faz7_variants(dv[m["model_id"]]) + fs7c.faz7c_variants(dv[m["model_id"]])
    if fs8.scores_post_d1_is_pre_faz8():
        # Faz 8 (SPEC_DEVIATIONS N19; proje sahibi kararı 2026-10-01; J16/K10 kalıbı): aynı istisna, yalnız scores_post_d1.json 87434ff'teki
        # haliyle bayt-eşitken ve fark tam Faz 8 varyant sayısı kadarken.
        dv8 = {e["model_id"]: e["data_version_sha256"]
               for e in json.loads((ROOT / "models" / "INDEX_POST_D1.json").read_text(encoding="utf-8"))["models"]}
        fresh = json.loads(json.dumps(fresh))
        for m in fresh["models"]:
            m["card"]["n_variants_same_data"] -= fs8.faz8_variants(dv8[m["model_id"]])
    assert _stable_post(committed) == _stable_post(fresh)
    assert sc.render_doc(json.loads(pretty_json_bytes(built[0])), committed) == sc.render_doc(built[0], fresh)


@pytest.mark.requires_git_history
def test_post_d1_doc_section_has_no_verdict_words(built):
    doc = sc.render_doc(built[0], built[1])
    part = doc.partition("## 7. D1 sonrası güncelleme")[2]
    assert part and "RETRO" in part
    for word in ("geçiyor", "geçemiyor", "ayırt edilemiyor", "ortalama", "Brier =", "RPS ="):
        assert word not in part, word


# ---------------------------------------------------------------- L4 uçtan uca prova (geçici klon)

@pytest.mark.requires_raw_sources
def test_l4_netgl_end_to_end(tmp_path):
    lines, facts = fls.prova_netgl(tmp_path)
    assert facts["schema_problems"] == [] and facts["model_equal"]
    assert facts["comparator_max_abs_diff"] <= 1e-12
    assert facts["klass"] == sc.CLASS_RETRO and not facts["evidence"]["model_prospective"]
    assert facts["guard_blocks_uncommitted"] and not any(facts["guards"].values())
    assert facts["ok"] and lines[-1] == "SONUÇ: PROVA_OK"
    assert not any(fls.re.search(r"th[bm]20\d{6}", x) for x in lines)                     # bülten adları maskeli


def test_l4_committed_prova_output_matches():
    """docs/faz5/ekler/prova_netgl.txt bu yardımcının çıktısıdır (klon HEAD ve kayıt adı hariç satır satır)."""
    p = ROOT / "docs" / "faz5" / "ekler" / "prova_netgl.txt"
    text = p.read_text(encoding="utf-8")
    assert "SONUÇ: PROVA_OK" in text and "[1] kayıt şeması §7.4 birebir: EVET" in text
    assert "class_post_d1 = RETRO" in text


# ---------------------------------------------------------------- L5, L6, L7

@pytest.mark.requires_raw_sources
def test_l5_thb_d1_columns_match_pinned_2026_header():
    """§7.6 + H19 adları, repodaki pinli 2026 THB başlıklarında birebir; OUTCOME_COLUMNS değişmedi."""
    assert set(oc.THB_D1_COLUMNS) == {"open", "high", "low", "volume", "turnover", "aof", "special_volume", "special_turnover"}
    assert oc.THB_D1_COLUMNS["special_volume"] == "OZEL ISLEM BILDIRIMI ISLEM ADEDI"
    assert oc.THB_D1_COLUMNS["special_turnover"] == "OZEL ISLEM BILDIRIMI ISLEM HACMI"
    n = 0
    for r in oc.read_manifest():
        if r["kind"] != "thb":
            continue
        parsed = oc.parse_archive_bytes(oc.local_path(r["date"], "thb").read_bytes(), oc.internal_name(r["date"], "thb"))
        assert set(oc.REQUIRED["thb"]) <= set(parsed["headers"]), r["date"]
        n += 1
    assert n >= 30
    assert oc.OUTCOME_COLUMNS == ("h", "session_date", "close_raw", "upper_limit_raw", "reference_raw", "trade_count_raw",
                                  "halt_flag", "half_day", "shifted_by_suspension", "ceiling_close", "R_h", "Y_h", "ipo_price",
                                  "thb_sha256", "thm_sha256", "status")


@pytest.mark.requires_raw_sources
def test_l5_outcomes_regenerate_byte_equal():
    """Ağsız regresyon: pinli yerel bültenlerden data/outcomes/*.csv yeniden üretilince bayt-eşit (REQUIRED genişledi, sonuç
    değişmedi)."""
    calendar = oc.load_calendar()
    built = oc.build_outcomes(calendar, oc.as_of_session(calendar), write=False)
    assert built
    for t, o in built.items():
        assert oc._rows_bytes(o["rows"]) == oc.outcome_path(t).read_bytes(), t


@pytest.mark.requires_raw_sources
def test_update_downloads_d1_bulletins_h1_ok_rest_pending(tmp_path, calendar):
    """§7.4 akışının ilk adımı: `outcomes update --through <D_1>` D_1 bültenlerini indirir; NETGL h = 1 OK, h ≥ 2 PENDING.
    Ağsız: sahte indirici repodaki pinli baytları sunar; D_1'den önceki bültenler geçici dizine kopyalı."""
    d1 = oc.read_outcome(oc.outcome_path("NETGL"))[0]["session_date"]
    bist = tmp_path / "bist"
    for r in oc.read_manifest():
        if r["date"] < d1:
            oc._write_new(oc.local_path(r["date"], r["kind"], bist), oc.local_path(r["date"], r["kind"]).read_bytes())
            oc._append_csv(bist / oc.MANIFEST_NAME, oc.MANIFEST_COLUMNS, r)
    served = {oc.source_url(d1, k): (oc.local_path(d1, k).read_bytes(), "x") for k in oc.KINDS}
    calls = []

    def downloader(url):
        calls.append(url)
        if url in served:
            return served[url]
        raise oc.NotPublished(url)

    res = oc.update(through=d1, today=d1, bist_dir=bist, outcomes_dir=tmp_path / "out", downloader=downloader, root=ROOT)
    assert res["through_session"] == d1 and res["files_fetched"] == 2 and sorted(calls) == sorted(served)
    rows = oc.read_outcome(oc.outcome_path("NETGL", tmp_path / "out"))
    assert rows[0]["status"] in (oc.STATUS_OK, oc.STATUS_NA_LIMIT) and rows[0]["session_date"] == d1
    assert all(r["status"] == oc.STATUS_PENDING for r in rows[1:])


def test_l6_calendar_end_is_labelled_error(calendar):
    """L6: takvim 2026-12-31'de bitiyor; takvim dışı ya da son seansta D_1 için T_open tahmin edilmez (CALENDAR_NOT_AVAILABLE)."""
    assert calendar.last_day == "2026-12-31" and calendar.sessions[-1] == "2026-12-31"
    assert reg.t_open("2026-12-30", calendar) == datetime(2026, 12, 31, 9, 40, tzinfo=IST)
    for d in ("2026-12-31", "2027-01-04"):
        with pytest.raises(reg.CalendarNotAvailable) as exc:
            reg.t_open(d, calendar)
        assert exc.value.code == "CALENDAR_NOT_AVAILABLE"


def test_sequence_guard_blocks_on_uncommitted_post_d1(tmp_path):
    """L7 (§7.4 son madde): registry/post_d1/ altında commit edilmemiş (izlenmeyen ya da değişmiş) dosya varken bülten
    indirilmez; commit'ten sonra serbest."""
    root = tmp_path
    _git(root, "init", "-q")
    _commit(root, "models/INDEX.json", json.dumps({"models": [{"file": "m.json"}]}))
    _commit(root, "models/m.json", "{}")
    (root / "registry" / "records").mkdir(parents=True)
    oc.sequence_guard("2026-10-02", root=root)
    p = root / "registry" / "post_d1" / "X" / "r.json"
    p.parent.mkdir(parents=True)
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(oc.SequenceRuleError):
        oc.sequence_guard("2026-10-02", root=root)
    _commit(root, "registry/post_d1/X/r.json", "{}")
    oc.sequence_guard("2026-10-02", root=root)
    p.write_text('{"x": 1}', encoding="utf-8")
    with pytest.raises(oc.SequenceRuleError):
        oc.sequence_guard("2026-10-02", root=root)
    oc.sequence_guard("2026-08-19", root=root)                          # sınırda serbest (Faz 2B kuralı aynen)


# ---------------------------------------------------------------- CLAUDE.md (karar 4)

def test_claude_md_rule_1_sentence_verbatim():
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    sentence = ("Her kayıt kendi aşamasının dizinindeki tüm modelleri içerir (listeleme öncesi: models/INDEX.json; POST_D1: "
                "models/INDEX_POST_D1.json). POST_D1 kaydının zaman sınırı D1'i izleyen ilk seans günü 09:40 (Europe/Istanbul), "
                "zaman kanıtı push kanıtıdır. Bir POST_D1 modeli, kendisinden sonra repoya giren her sonuç commit'inin atasıdır; "
                "ondan önce girmiş sonuçlar o model için RETRO'dur.")
    line = next(x for x in text.splitlines() if x.startswith("1. Dondurma:"))
    assert line.endswith("hatalıysa iptal kaydı düşülür. " + sentence)

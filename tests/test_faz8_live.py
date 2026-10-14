"""Kırılma akşamı canlı aşaması `POST_BREAK` (makine sıralı; BORSAI_FAZ8_LIVE_BREAK; SPEC_BREAK_V0 §9, §13-11..13; SPEC_DEVIATIONS N26+).

§13-11 sınıf (a)–(g) geçici git depolarında (push kanıtı taklidi; sistem saatine dokunulmaz); makine kaydı şeması ve yazıcısı (gerçek
pinli bültenlerle, geçici dizine); §13-12 payda dalları ve §13-13 ölçek/dil uçtan uca sentetik depoda (sentetik bültenler, girdiler,
sonuç dosyaları; gerçek repoya hiçbir şey yazılmaz); K-LB-3 mükerrer kayıt ve parite. Gerçek dosya testleri (registry/post_break/,
scores/scores_break.json, docs/SCORES_BREAK.md) dosyalar commit'liyken koşar. Metinde bülten adı kalıbı ve kasa kodu yoktur."""
from __future__ import annotations

import copy
import inspect
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from borsai import freeze as fz
from borsai import outcomes as oc
from borsai import predict_break as pbrk
from borsai import predict_path as pth
from borsai import registry as reg
from borsai import scoring as sc
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes, sha256_file
from borsai.specs import FAZ8_MODEL_IDS

import faz6_support as fs6

NOW = datetime(2026, 10, 2, 16, 0, 0, tzinfo=timezone.utc)
TASK_BASE = "fd88be3"                       # görev başlangıcı (HEAD = origin/main; SPEC_DEVIATIONS N26)
LIVE_PREFIX = "BORSAI_FAZ8_LIVE_"
SYN_D1 = "2026-10-01"
P = "10.00"
BACKTEST = {"scale": "backtest_break", "subset": "first_trading_date >= 2024-01-01", "k1": True, "label": sc.BREAK_BACKTEST_PASS,
            "F1_product": {"diff": -0.19, "ci95": [-0.25, -0.12], "n": 69, "n_months": 22},
            "F1_zero": {"diff": -0.03, "ci95": [-0.05, -0.01], "n": 69, "n_months": 22}}
REAL_EXPECTED = {   # görev metni "Beklenen sayılar" (donmuş JSON + stdlib predict_break; orkestratör)
    "CITAS": ("2026-08-18", 5, 6, "2026-08-25", 0, 0.13833264286466687, 0.09464223345801025),
    "TKNKA": ("2026-08-20", 7, 8, "2026-08-31", 0, 0.13817491254287276, 0.09521214961923939),
    "VEYAS": ("2026-08-20", 0, 1, "2026-08-20", 0, 0.1376436522563838, 0.09715847417357594),
    "KPEKS": ("2026-08-21", 5, 6, "2026-08-28", 1, 0.5389117003850694, 0.16401056260438845),
    "INTET": ("2026-09-01", 4, 5, "2026-09-07", 0, 0.14182539930275256, 0.08290496022647753),
    "BKRGY": ("2026-09-02", 0, 1, "2026-09-02", 1, 0.5432679533511754, 0.15231130173471372),
    "NETGL": ("2026-09-17", 3, 4, "2026-09-22", 1, 0.4990578357497034, 0.30432770420243327),
}


@pytest.fixture(scope="module")
def calendar():
    return oc.load_calendar()


def _manifest(bist=None):
    return {(r["date"], r["kind"]): r for r in oc.read_manifest(bist or oc.BIST_DIR)}


# ================================================================ §13-11 sınıf (geçici git deposu)

def _outcome_csv(dates, n_filled):
    rows = []
    for h in range(1, 11):
        r = dict.fromkeys(oc.OUTCOME_COLUMNS, "")
        filled = h <= n_filled
        r.update(h=str(h), session_date=dates[h - 1] if filled else "", ceiling_close="1" if filled else "",
                 status=oc.STATUS_OK if filled else oc.STATUS_PENDING)
        rows.append(",".join(r[c] for c in oc.OUTCOME_COLUMNS))
    return ",".join(oc.OUTCOME_COLUMNS) + "\n" + "\n".join(rows) + "\n"


def _commit_text(root, rel, text="x"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return fs6.commit(root, rel, rel)


def class_scenario(tmp_path, calendar, steps, *, b=2, pit_ok=True):
    """steps: sırayla (adım, kanıt zamanı | None). Adımlar: model, db_bulletin (D_1..D_b THB+THM), db_outcome (h ≤ b dolu),
    next_bulletin (D_{b+1}), next_outcome (h = b + 1 dolu). Dönen: class_break_evidence(...) -> (sınıf, kanıt)."""
    root = fs6.init_repo(tmp_path)
    dates = list(calendar.sessions_from(SYN_D1)[:10])
    bist = root / "data" / "raw" / "bist"
    rel = lambda d, k: oc.local_path(d, k, bist).relative_to(root).as_posix()  # noqa: E731
    paths = {"model": ["models/k.json"], "db_bulletin": [rel(d, k) for d in dates[:b] for k in oc.KINDS],
             "next_bulletin": [rel(dates[b], k) for k in oc.KINDS]}
    proofs = []
    for what, at in steps:
        if what in ("db_outcome", "next_outcome"):
            sha = _commit_text(root, "data/outcomes/X.csv", _outcome_csv(dates, b if what == "db_outcome" else b + 1))
        else:
            for r in paths[what]:
                sha = _commit_text(root, r)
        if at:
            proofs.append({"proven_commit_sha": sha, "created_at": at})
    git = sc.Git(root)
    ingest = sc.outcome_ingest_commit_after(git, "X", dates[b - 1], b + 1)
    return sc.class_break_evidence(git, sc.model_evidence(git, "k.json", proofs), ingest, pit_ok, dates[b - 1],
                                   reg.t_open(dates[b - 1], calendar))


MODEL_PROVEN = ("model", "2026-09-30T10:00:00Z")


def test_13_11a_model_then_db_then_next_bulletin_is_machine_sequenced(tmp_path, calendar):
    """(a) model (push kanıtlı) → D_b bülteni ve sonucu → D_{b+1} bülteni ⇒ MACHINE_SEQUENCED (insan kaydı yok)."""
    cls, ev = class_scenario(tmp_path, calendar, [MODEL_PROVEN, ("db_bulletin", None), ("db_outcome", None),
                                                  ("next_bulletin", None), ("next_outcome", None)])
    assert cls == pbrk.CLASS_MACHINE_SEQUENCED == sc.CLASS_MACHINE
    assert ev["model_prospective"] and not ev["record_live"] and ev["outcome_ingest_basis"] == "COMMITTED"
    # D_{b+1} henüz commit'li değil: HEAD'e karşı (E15 kalıbı), yine MACHINE_SEQUENCED
    cls2, ev2 = class_scenario(tmp_path / "pending", calendar, [MODEL_PROVEN, ("db_bulletin", None), ("db_outcome", None)])
    assert cls2 == sc.CLASS_MACHINE and ev2["outcome_ingest_basis"] == "UNCOMMITTED_CHECKED_AGAINST_HEAD"


def test_13_11b_next_bulletin_before_model_is_retro(tmp_path, calendar):
    """(b) D_{b+1} bülteni modelden önce repoya girdi ⇒ RETRO; h ≥ b + 1 dolu sonuç satırı da aynı sayılır (min)."""
    cls, ev = class_scenario(tmp_path, calendar, [("db_bulletin", None), ("next_bulletin", None), MODEL_PROVEN])
    assert cls == pbrk.CLASS_RETRO and not ev["model_prospective"]
    cls2, _ = class_scenario(tmp_path / "row", calendar, [("db_bulletin", None), ("next_outcome", None), MODEL_PROVEN,
                                                          ("next_bulletin", None)])
    assert cls2 == pbrk.CLASS_RETRO
    # D_b'nin kendi bülteni ve h ≤ b satırları modelden önce girse de prospektif (kırılma akşamı girdisidir, sonuç değil)
    cls3, _ = class_scenario(tmp_path / "db", calendar, [("db_bulletin", None), ("db_outcome", None), MODEL_PROVEN,
                                                         ("next_bulletin", None)])
    assert cls3 == sc.CLASS_MACHINE


def test_13_11c_no_push_proof_is_retro(tmp_path, calendar):
    """(c) model commit'i sonuçtan önce ama push kanıtı yok ⇒ RETRO."""
    cls, ev = class_scenario(tmp_path, calendar, [("model", None), ("db_bulletin", None), ("next_bulletin", None)])
    assert cls == pbrk.CLASS_RETRO and not ev["model_prospective"] and ev["model_push_proof_created_at"] is None


@pytest.mark.requires_raw_sources
def test_13_11d_shares_offered_not_pit_is_retro(tmp_path, calendar):
    """(d) shares_offered'ın kaynağı D_1'den önce yayımlanmamış ⇒ inputs PIT değil ⇒ RETRO (tahmin yine üretilir)."""
    doc = json.loads((ROOT / "registry" / "inputs" / "NETGL.json").read_text(encoding="utf-8"))
    d1 = REAL_EXPECTED["NETGL"][0]
    assert reg.post_break_inputs_pit_problems(doc, d1) == []
    bad = copy.deepcopy(doc)
    bad["fields"]["shares_offered"]["source_published_at"] = f"{d1}T08:00:00+03:00"
    probs = reg.post_break_inputs_pit_problems(bad, d1)
    assert any(x.startswith("shares_offered: kaynak yayını") for x in probs)
    flow = [MODEL_PROVEN, ("db_bulletin", None), ("next_bulletin", None)]
    assert class_scenario(tmp_path / "ok", calendar, flow, pit_ok=True)[0] == sc.CLASS_MACHINE
    assert class_scenario(tmp_path / "bad", calendar, flow, pit_ok=not probs)[0] == pbrk.CLASS_RETRO


def test_13_11e_live_formula_is_pure(calendar):
    """(e) LIVE formülü (v0'da insan kaydı üreticisi yok): prospektif ∧ insan kaydı T_open'dan kesin önce ∧ PIT ⇒ LIVE."""
    t_open = reg.t_open("2026-10-01", calendar)
    assert t_open.isoformat() == "2026-10-02T09:40:00+03:00"
    assert sc.record_live_break("2026-10-02T06:39:59Z", t_open) and not sc.record_live_break("2026-10-02T06:40:00Z", t_open)
    assert not sc.record_live_break(None, t_open)
    table = {(True, True, True): "LIVE", (True, False, True): "MACHINE_SEQUENCED", (True, True, False): "RETRO",
             (False, True, True): "RETRO", (False, False, True): "RETRO", (True, False, False): "RETRO"}
    for args, want in table.items():
        assert pbrk.class_break(*args) == want, args


def _git_scoring_at(rev):
    return subprocess.run(["git", "show", f"{rev}:borsai/scoring.py"], cwd=ROOT, check=True, capture_output=True, text=True).stdout


@pytest.mark.requires_git_history
def test_13_11f_ingest_after_d1_h2_is_bit_equal_to_post_d1(tmp_path, calendar):
    """(f) K-LB-5: `outcome_ingest_commit_after(day = D_1, h_min = 2)` == `outcome_ingest_commit_post_d1` (bit-eşit commit) — 7 gerçek
    arzda ve sentetik depolarda; post_d1 fonksiyonu ve post_d1 bekçisi görev başlangıcındaki metinle aynı (değişmedi)."""
    git = sc.Git(ROOT)
    for t, (d1, *_) in REAL_EXPECTED.items():
        a, b = sc.outcome_ingest_commit_after(git, t, d1, 2), sc.outcome_ingest_commit_post_d1(git, t, d1)
        assert a == b and a is not None, t
    for i, steps in enumerate(([MODEL_PROVEN, ("db_bulletin", None), ("db_outcome", None), ("next_outcome", None), ("next_bulletin", None)],
                               [("db_bulletin", None), ("next_bulletin", None), MODEL_PROVEN],
                               [MODEL_PROVEN, ("db_bulletin", None)])):
        root = tmp_path / f"r{i}" / "repo"
        class_scenario(tmp_path / f"r{i}", calendar, steps, b=1)
        g = sc.Git(root)
        assert sc.outcome_ingest_commit_after(g, "X", SYN_D1, 2) == sc.outcome_ingest_commit_post_d1(g, "X", SYN_D1), steps
    assert inspect.getsource(sc.outcome_ingest_commit_post_d1) in _git_scoring_at(TASK_BASE)
    old_reg = subprocess.run(["git", "show", f"{TASK_BASE}:borsai/registry.py"], cwd=ROOT, check=True, capture_output=True,
                             text=True).stdout
    assert inspect.getsource(reg.post_d1_record_problems) in old_reg


# ---------------------------------------------------------------- (g) kayıt bekçisi (+ mutasyon)

@pytest.fixture(scope="module")
def netgl_record():
    """NETGL'in gerçek pinli bültenleri ve girdisiyle bellekte kurulan makine kaydı (dosya yazılmaz)."""
    return fz.build_post_break_machine_record("NETGL", now=NOW)


def guard_cases(guard, rec0, man):
    """(durum, kırmızı beklenir mi, bekçi sonucu). `guard` = registry.post_break_record_problems ya da mutasyonu."""
    db, b = rec0["streak"]["break_date"], rec0["streak"]["b"]
    later = next(k for k in sorted(man) if k[0] > db and k[1] == "thb")
    earlier = next(k for k in sorted(man) if k[0] < rec0["streak"]["sessions"][0]["date"] and k[1] == "thm")
    name = lambda k: f"data/raw/bist/{k[1]}/{k[0][:4]}/{k[1]}{k[0].replace('-', '')}1.zip"  # noqa: E731

    def mutated(fn):
        rec = copy.deepcopy(rec0)
        fn(rec)
        return guard(rec, man)

    return [
        ("temiz", False, guard(copy.deepcopy(rec0), man)),
        ("h > b sonuç anahtarı", True, mutated(lambda r: r["models"][0]["output"].update({f"ceiling_close_D{b + 1}": 1}))),
        ("h > b alt limit anahtarı", True, mutated(lambda r: r["break_day"].update({f"lower_limit_D{b + 1}": "1"}))),
        ("sonuç sözcüğü", True, mutated(lambda r: r["summary"].update({"y_F1": 1}))),
        ("D_b sonrası bülten sha'sı", True, mutated(lambda r: r["summary"].update({"note": man[later]["sha256"]}))),
        ("D_b sonrası bülten adı", True, mutated(lambda r: r["summary"].update({"note": name(later)}))),
        ("D_1 öncesi bülten adı", True, mutated(lambda r: r["summary"].update({"note": name(earlier)}))),
        ("D_b sonrası tarih", True, mutated(lambda r: r["streak"]["sessions"][-1].update({"date": later[0]}))),
        ("seans sırası", True, mutated(lambda r: r["streak"]["sessions"].reverse())),
        ("h = 1..b değil", True, mutated(lambda r: r["streak"]["sessions"].pop(0))),
        ("pinli sha değil", True, mutated(lambda r: r["streak"]["sessions"][0]["thb"].update({"sha256": "0" * 64}))),
    ]


@pytest.mark.requires_raw_sources
def test_13_11g_record_guard_red_cases_and_mutation(netgl_record):
    """(g) bekçi: h > b anahtarı, D_b sonrası bülten adı ya da sha'sı (ve D_1..D_b dışı atıflar, seans sırası, pinli olmayan sha) →
    kırmızı; temiz kayıt yeşil. Mutasyon: bekçi kapatılınca (her zaman boş) kırmızı beklenen hiçbir durum yakalanmaz."""
    man = _manifest()
    cases = guard_cases(reg.post_break_record_problems, netgl_record, man)
    assert [(n, bool(p)) for n, red, p in cases if bool(p) != red] == []
    off = guard_cases(lambda rec, m: [], netgl_record, man)
    assert [n for n, red, p in off if bool(p) != red] == [n for n, red, _ in cases if red]


# ================================================================ makine kaydı şeması ve yazıcı (gerçek pinli bültenler, geçici dizin)

SCHEMA = {
    "code": {"git_head", "borsai_dirty", "borsai_source_sha256", "predict_break_sha256"},
    "inputs_ref": {"file", "sha256", "shares_offered", "ipo_price_tl", "inputs_pit_ok"},
    "streak": {"L", "b", "break_date", "sessions"},
    "break_day": {"h", "session_date", "half_day", "halt_flag", "fields_raw", "b_floor", "band_ratio", "warnings"},
    "features": {"b_floor", "b_turnover_ratio", "b_turnover_ln", "clipped", "z"},
    "models_index": {"path", "sha256", "model_ids"},
    "comparators": {"PRODUCT_BREAK_FLOOR", "base_floor_by_type"},
    "structural_zero_D10": {"min10", "P", "impossible", "k_b", "r_b", "band_rule_ok"},
    "summary": {"n_models", "n_predicted", "n_refused", "n_not_applicable"},
}


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


@pytest.mark.requires_raw_sources
def test_record_schema_is_9_2(netgl_record):
    rec = netgl_record
    assert set(rec) == fz.POST_BREAK_RECORD_KEYS
    for key, want in SCHEMA.items():
        assert set(rec[key]) == want, key
    assert (rec["schema_version"], rec["record_type"], rec["record_stage"], rec["exposure_class"]) == (
        "borsai.post_break_machine_record/1", "MACHINE", "POST_BREAK", "MACHINE_SEQUENCED")
    assert "class" not in {k for k in _keys(rec)}                         # kayıt sınıf taşımaz (K-LB-2)
    assert set(rec["break_day"]["fields_raw"]) == set(reg.POST_D1_FIELDS_RAW)
    assert set(rec["inputs_ref"]["shares_offered"]) == {"value", "source_published_at"}
    for s in rec["streak"]["sessions"]:
        assert set(s) == {"h", "date", "thb", "thm", "close_raw", "upper_limit_raw", "ceiling_close"}
        assert set(s["thb"]) == set(s["thm"]) == {"file", "sha256"}
    assert [s["ceiling_close"] for s in rec["streak"]["sessions"]] == [1, 1, 1, 0]
    assert rec["models_index"] == {"path": "models/INDEX_POST_BREAK.json", "sha256": sha256_file(ROOT / "models" / "INDEX_POST_BREAK.json"),
                                   "model_ids": list(FAZ8_MODEL_IDS)}
    for c in rec["models"]:
        assert set(c) == {"model_id", "file", "params_sha256", "spec_sha256", "status", "refused", "not_applicable", "output"}
        assert set(c["output"]) == {"F1", "F2", "warnings"}
        assert c["params_sha256"] == sha256_file(ROOT / c["file"])
    assert rec["comparators"] == {"PRODUCT_BREAK_FLOOR": {"source_record": None, "source_model_id": None, "F1": None, "F2": None,
                                                          "status": "NOT_AVAILABLE"}, "base_floor_by_type": None}
    assert rec["t_open"] == "2026-09-23T09:40:00+03:00" and rec["inputs_ref"]["inputs_pit_ok"] is True
    assert rec["structural_zero_D10"]["band_rule_ok"] is True and rec["break_day"]["band_ratio"]["rule_ok"] is True


@pytest.mark.requires_raw_sources
def test_zero_rule_does_not_read_break_fields(netgl_record):
    """`@ZERO` kırılma günü alanlarını okumaz: kayıttaki çıktısı, alanlar boş ya da bozukken de aynıdır (donmuş JSON'un oranı)."""
    params = json.loads((ROOT / "models" / "break_floor_v0@ZERO.json").read_text(encoding="utf-8"))
    cell = next(c for c in netgl_record["models"] if c["model_id"] == "break_floor_v0@ZERO")
    for day in (None, {"fields_raw": {}}, {"fields_raw": {"close": "x", "lower_limit": "-1"}, "half_day": 1}):
        out = pbrk.predict_break(params, day, None, b=4, first_trading_date="2026-09-17")
        assert {"F1": out["F1"], "F2": out["F2"], "warnings": out["warnings"]} == cell["output"]
    assert cell["output"]["F1"]["p_floor"] == params["comparators"]["zero"]["F1"] == 25 / 82
    assert cell["output"]["F2"]["p_floor"] == params["comparators"]["zero"]["F2"] == 11 / 78


@pytest.mark.requires_raw_sources
def test_record_writer_append_only_and_no_duplicate(tmp_path):
    """Dosya adı `machine_<UTC>_<kısa-sha>.json` (içerik adresli); aynı INDEX + bülten + girdi sha'larıyla ikinci yazım reddedilir
    (yeni dosya yok; kod değişse de); 'xb' — var olan dosya yeniden yazılmaz."""
    post = tmp_path / "post_break"
    path = fz.write_post_break_machine_record("NETGL", now=NOW, post_dir=post)
    data = path.read_bytes()
    assert path.parent == post / "NETGL" and path.name == f"machine_20261002T160000Z_{sha256_bytes(data)[:12]}.json"
    assert path.name == fz.machine_record_filename(data, json.loads(data)["produced_at_utc"])
    with pytest.raises(fz.DuplicateRecord):
        fz.write_post_break_machine_record("NETGL", now=NOW + timedelta(hours=1), post_dir=post)
    assert [p.name for p in post.rglob("*.json")] == [path.name]
    with pytest.raises(FileExistsError):
        fz._write_new(path, b"{}")


# ================================================================ uçtan uca sentetik depo (§13-12 payda dalları, §13-13, K-LB-3)

# Seri kodları (D_1'den itibaren her seans): C tavanda kapanış, F tabanda, M referansta (ne tavan ne taban), N üst limit boş (NA),
# L alt limit boş. Fiyatlar adım tablosuyla (`predict_path.upper_limit` / `lower_limit`); D_1 referansı arz fiyatı.
SCENARIOS = {
    "ZBA": (0, "CCFFF"),            # b = 3, F1 = 1, F2 = 1 -> skorlanan (makine sıralı)
    "ZBB": (0, "MMF"),              # b = 1, F1 = 0 -> F2 = 0 (D3 tabanda olsa da; backtest etiket kuralı)
    "ZBC": (0, "CCCCCCCCFF"),       # b = 9: F2 tanımsız
    "ZBD": (18, "CC"),              # seri sürüyor: STREAK_PENDING
    "ZBE": (0, "CCCCCCCCCC"),       # L = 10: NOT_APPLICABLE_NO_BREAK
    "ZBF": (0, "CCCCCCCCCM"),       # b = 10: NOT_APPLICABLE_B10
    "ZBG": (0, "CNM"),              # D2 üst limit NA: NOT_SCORABLE_STREAK_NA
    "ZBH": (0, "CMM"),              # girdi dosyası yok: INPUTS_NOT_AVAILABLE
    "ZBI": (30, "CMM"),             # D_1 THB'si pinli değil: BULLETIN_NOT_PINNED
    "ZBJ": ("last", "M"),           # D_b = takvimin son seansı: CALENDAR_NOT_AVAILABLE
    "ZBK": (0, "CML"),              # D3 alt limit boş: TARGET_LABEL_NA
    "ZBL": (0, "CMF"),              # shares_offered PIT değil: RETRO (sınıf)
    "ZBM": (18, "CM"),              # D3 henüz yok: satır PENDING
    "ZBN": (0, "CLM"),              # D_b alt limit boş: model reddi B_LIMIT_NA (REFUSED)
}
EXPECTED_STAGES = {"ZBA": "RECORD", "ZBB": "RECORD", "ZBC": "RECORD", "ZBD": "STREAK_PENDING", "ZBE": "NOT_APPLICABLE_NO_BREAK",
                   "ZBF": "NOT_APPLICABLE_B10", "ZBG": "NOT_SCORABLE_STREAK_NA", "ZBH": "INPUTS_NOT_AVAILABLE",
                   "ZBI": "BULLETIN_NOT_PINNED", "ZBJ": "CALENDAR_NOT_AVAILABLE", "ZBK": "RECORD", "ZBL": "RETRO", "ZBM": "RECORD",
                   "ZBN": "RECORD"}
AVAILABLE = 20                      # paylaşılan pencerede bülteni olan ilk 20 seans (sonrası bekleniyor)


def _paths(calendar):
    """arz -> {gün: (kapanış, referans, üst, alt)} ve yazılacak günler."""
    S = list(calendar.sessions_from(SYN_D1))
    out = {}
    for t, (start, codes) in SCENARIOS.items():
        days = [calendar.sessions[-1]] if start == "last" else S[start:start + len(codes)]
        ref = pth.snap(Decimal(P))
        path = {}
        for d, ch in zip(days, codes):
            up, lo = pth.upper_limit(ref), pth.lower_limit(ref)
            close = {"C": up, "F": lo, "M": ref, "N": ref, "L": ref}[ch]
            path[d] = (str(close), str(ref), "" if ch == "N" else str(up), "" if ch == "L" else str(lo))
            ref = close
        out[t] = path
    written = set(S[:AVAILABLE]) | set(S[30:33]) | {calendar.sessions[-1]}
    unpinned = {(S[30], "thb")}            # ZBI'nin D_1 THB'si yerelde/MANIFEST'te yok (sonuç dosyası bellekteki bültenlerden)
    return out, sorted(written), unpinned


def break_repo(tmp_path, calendar, *, model_proof=True, outcomes_first=False):
    """Sentetik depo: models/INDEX_POST_BREAK.json + iki donmuş JSON (gerçek kopya), registry (ipos, girdiler, kaynak belgeler),
    sentetik THB/THM + MANIFEST, sonuç dosyaları (`outcomes.outcome_rows`). Model commit'i (kanıtlı) sonuçlardan önce; `outcomes_first`
    ise sonra."""
    root = fs6.init_repo(tmp_path)
    (root / "models").mkdir()
    for name in ("INDEX_POST_BREAK.json", "break_floor_v0.json", "break_floor_v0@ZERO.json"):
        (root / "models" / name).write_bytes((ROOT / "models" / name).read_bytes())
    paths, written, unpinned = _paths(calendar)
    bist = root / "data" / "raw" / "bist"
    thb, thm = {}, {}
    for d in written:
        rows_b = [fs6.thb_row(fs6.FILLER, "5.00")]
        rows_m = [fs6.thm_row(fs6.FILLER, "5.00", "5.50", "4.50")]
        for t, path in paths.items():
            if d in path:
                close, ref, up, lo = path[d]
                rows_b.append(fs6.thb_row(oc.equity_code(t), close))
                rows_m.append(fs6.thm_row(oc.equity_code(t), ref, up, lo))
        for kind, rows, store in (("thb", rows_b, thb), ("thm", rows_m, thm)):
            data = fs6.make_zip(d, kind, rows)
            store[d] = oc.parse_bulletin(data, d, kind)
            if (d, kind) in unpinned:
                continue
            oc._write_new(oc.local_path(d, kind, bist), data)
            oc._append_csv(bist / oc.MANIFEST_NAME, oc.MANIFEST_COLUMNS, {
                "date": d, "kind": kind, "url": oc.source_url(d, kind), "sha256": sha256_bytes(data), "bytes": len(data),
                "internal_filename": oc.internal_name(d, kind), "downloaded_at": "test", "http_last_modified": ""})
    ipos = [",".join(reg.IPOS_COLUMNS)]
    for t, path in paths.items():
        d1 = min(path)
        ipos.append(f"{t},{t} Sentetik A.Ş.,{d1},KAP_1,FROZEN,,,2026-09-30T00:00:00+03:00")
        rows = oc.outcome_rows(t, P, calendar, thb, thm, start=d1)
        oc.write_outcome(t, rows, root / "data" / "outcomes")
        if t == "ZBH":
            continue
        pub = f"{d1}T08:00:00+03:00" if t == "ZBL" else None
        doc = fs6.inputs_doc(t, d1, price=P, published=pub)
        (root / "registry" / "inputs").mkdir(parents=True, exist_ok=True)
        (root / "registry" / "inputs" / f"{t}.json").write_bytes(pretty_json_bytes(doc))
        src = root / "registry" / "oot" / "source_docs" / t / "KAP_1_bildirim.pdf"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_bytes(fs6.SRC_BYTES)
    (root / "registry" / "ipos.csv").write_text("\n".join(ipos) + "\n", encoding="utf-8")
    order = (["data", "registry", "models"] if outcomes_first else ["models", "registry", "data"])
    shas = {part: fs6.commit(root, part, part) for part in order}
    if model_proof:
        fs6.make_proof(root, shas["models"], "2026-09-30T10:00:00Z")
        fs6.commit(root, "proof", "registry/push_proofs")
    return root


@pytest.fixture(scope="module")
def syn(tmp_path_factory, calendar):
    """Kayıtları yazılmış sentetik depo ve skor içeriği (main_break: kayıt + skor + belge)."""
    root = break_repo(tmp_path_factory.mktemp("syn"), calendar)
    first = sc.ensure_post_break_records(root, now=NOW, calendar=calendar)
    second = sc.ensure_post_break_records(root, now=NOW + timedelta(hours=1), calendar=calendar)
    scores = sc.build_break_scores(root=root, now=NOW, calendar=calendar, backtest=BACKTEST)
    return root, first, second, scores


def test_13_12_denominator_branches_and_identity(syn):
    """§13-12: payda ipos.csv'de FROZEN her arz için bir satır; dallar STREAK_PENDING (seri sürüyor), NO_BREAK (L = 10), B10, seride
    NA, BULLETIN_NOT_PINNED, INPUTS_NOT_AVAILABLE, CALENDAR_NOT_AVAILABLE, RETRO (PIT) ve satırlar; özdeşlik tutar."""
    _, first, _, scores = syn
    b = scores["models"][0]["live_break"]
    assert {d["ticker"]: d["stage_status"] for d in b["denominator"]} == EXPECTED_STAGES
    assert sc.break_denominator_problems(b) == []
    stage_sum = sum(b[c] for c in sc.BREAK_STAGE_COUNTERS.values())
    assert len(b["denominator"]) == 14 == stage_sum + b["n_rows"] and b["n_rows"] == len(b["rows"]) == 6
    assert (b["n_scored"], b["n_machine"], b["n_live"], b["n_refused"], b["n_pending"], b["n_target_label_na"],
            b["n_target_unavailable"], b["n_retro"]) == (3, 3, 0, 1, 1, 1, 0, 1)
    for c in ("n_streak_pending", "n_not_applicable_no_break", "n_not_applicable_b10", "n_not_scorable_streak_na",
              "n_bulletin_not_pinned", "n_inputs_not_available", "n_calendar_not_available"):
        assert b[c] == 1, c
    assert first["not_written"] == {"ZBD": "STREAK_PENDING", "ZBE": "NOT_APPLICABLE_NO_BREAK", "ZBF": "NOT_APPLICABLE_B10",
                                    "ZBG": "NOT_SCORABLE_STREAK_NA", "ZBH": "INPUTS_NOT_AVAILABLE", "ZBI": "BULLETIN_NOT_PINNED",
                                    "ZBJ": "CALENDAR_NOT_AVAILABLE"}
    assert sorted(Path(p).parent.name for p in first["written"]) == ["ZBA", "ZBB", "ZBC", "ZBK", "ZBL", "ZBM", "ZBN"]
    assert [x["ticker"] for x in scores["retro_info"]] == ["ZBL"] and scores["retro_info"][0]["inputs_pit_problems"]


def test_13_12_rows_labels_b9_and_refusal(syn):
    """Satırlar: makine sıralı; F1/F2 etiketleri pinli THM'den; b = 9'da F2 yok; F1 = 0 iken F2 = 0; D_b alt limiti yoksa REFUSED."""
    _, _, _, scores = syn
    rows = {r["ticker"]: r for r in scores["models"][0]["live_break"]["rows"]}
    a, bb, c = rows["ZBA"], rows["ZBB"], rows["ZBC"]
    assert {r["class"] for r in rows.values()} == {sc.CLASS_MACHINE}
    assert (a["b"], a["L"], a["b_floor"], a["status"], a["realized"]["F1"]["y"], a["realized"]["F2"]["y"]) == (3, 2, 1, "SCORED", 1, 1)
    assert (bb["b"], bb["b_floor"], bb["realized"]["F1"]["y"], bb["realized"]["F2"]["y"]) == (1, 0, 0, 0)
    assert (c["b"], c["status"], c["realized"]["F1"]["y"], c["p"]["F2"], c["f2_status"]) == (9, "SCORED", 1, None,
                                                                                            "TARGET_UNDEFINED_F2")
    assert "F2" not in c["losses"] and c["comparators"]["break_floor_v0@ZERO"]["F2"] is None
    assert (rows["ZBK"]["status"], rows["ZBM"]["status"], rows["ZBN"]["status"]) == ("TARGET_LABEL_NA", "PENDING", "REFUSED")
    assert rows["ZBN"]["refused"]["code"] == "B_LIMIT_NA"
    params = json.loads((ROOT / "models" / "break_floor_v0.json").read_text(encoding="utf-8"))
    for r in (a, bb):
        assert r["comparators"]["base_floor_by_type"]["F1"] == params["comparators"]["by_type_F1"][str(r["b_floor"])]["rate"]
        assert r["comparators"]["break_floor_v0@ZERO"] == params["comparators"]["zero"]
        assert r["comparators"]["PRODUCT_BREAK_FLOOR"]["status"] == "NOT_AVAILABLE"
        y = r["realized"]["F1"]["y"]
        assert r["losses"]["F1"]["model"] == (r["p"]["F1"] - y) ** 2 and r["losses"]["F1"]["PRODUCT_BREAK_FLOOR"] is None
        assert r["parity"] == {"status": "OK", "max_abs_diff": 0.0, "basis": "IN_MEMORY_REBUILD"}
        assert "FON_KRIZI_2026" in r["regime_tags"]


def test_k_lb_3_second_run_writes_nothing(syn):
    """K-LB-3: ikinci `--break` kayıt adımı 0 yeni kayıt yazar (mükerrer anahtar: INDEX + D_1..D_b bülten + girdi sha'ları)."""
    root, first, second, _ = syn
    assert second["written"] == [] and sorted(second["existing"]) == sorted(Path(p).parent.name for p in first["written"])
    assert second["not_written"] == first["not_written"]
    assert len(list((root / "registry" / "post_break").rglob("*.json"))) == 7


def test_k_lb_3_tampered_record_fails_parity(tmp_path, calendar):
    """Birincil kaydın tahmini bozulunca skorlama ScoringError verir (bellekte yeniden üretimle |Δ| > 1e-12)."""
    root = break_repo(tmp_path, calendar)
    sc.ensure_post_break_records(root, now=NOW, calendar=calendar)
    [p] = list((root / "registry" / "post_break" / "ZBA").glob("*.json"))
    rec = json.loads(p.read_text(encoding="utf-8"))
    rec["models"][0]["output"]["F1"]["p_floor"] += 1e-9
    p.write_bytes(pretty_json_bytes(rec))
    with pytest.raises(sc.ScoringError, match="parite"):
        sc.build_break_scores(root=root, now=NOW, calendar=calendar, backtest=BACKTEST)


def test_no_proof_or_outcomes_first_is_all_retro(tmp_path, calendar):
    """Push kanıtı yoksa ya da sonuçlar modelden önce girdiyse her arz RETRO (yalnız retro_info); kayıtlar yine yazılır ve bilgi
    satırları onlardan okunur."""
    for name, kw in (("noproof", {"model_proof": False}), ("first", {"outcomes_first": True})):
        root = break_repo(tmp_path / name, calendar, **kw)
        sc.ensure_post_break_records(root, now=NOW, calendar=calendar)
        s = sc.build_break_scores(root=root, now=NOW, calendar=calendar, backtest=BACKTEST)
        b = s["models"][0]["live_break"]
        retro = {x["ticker"] for x in s["retro_info"]}
        if name == "noproof":
            assert b["n_retro"] == 14 and retro == set(SCENARIOS) and b["rows"] == []
        else:   # D_b'si belirsiz seriler (ZBD sürüyor, ZBG NA) ve takvim sonu arzı (ZBJ: D_b'den sonra bülten yok) HEAD'e karşı
            # prospektif (SPEC_DEVIATIONS N); ZBM'nin D_b'sinden sonra tarihli (başka günlerin) bültenleri modelden önce girdi: RETRO
            assert retro == set(SCENARIOS) - {"ZBD", "ZBG", "ZBJ"}, retro
        zba = next(x for x in s["retro_info"] if x["ticker"] == "ZBA")
        assert zba["record_id"].startswith("machine_") and zba["b"] == 3 and zba["p"]["F1"] is not None


def test_main_break_writes_three_outputs_and_doc_is_render_of_written_json(tmp_path, calendar):
    """K-LB-1: main_break (i) makine kayıtları, (ii) scores_break.json, (iii) yazılmış JSON'un render'ı SCORES_BREAK.md; belge sözlük
    sırasından bağımsız; bülten adı kalıbı yok."""
    root = break_repo(tmp_path, calendar)
    assert sc.main_break(root, now=NOW) == 0
    written = json.loads((root / "scores" / "scores_break.json").read_text(encoding="utf-8"))
    doc = (root / "docs" / "SCORES_BREAK.md").read_text(encoding="utf-8")
    assert doc == sc.render_break_doc(written) and written["schema_version"] == "borsai.scores_break/1"
    mem = sc.build_break_scores(root=root, now=NOW, calendar=calendar)
    assert sc.render_break_doc(mem) == sc.render_break_doc(json.loads(pretty_json_bytes(mem)))
    assert not re.search(r"th[bm]20\d{6}", doc + json.dumps(written))
    assert doc.startswith(f"# {sc.BREAK_TITLE}\n") and "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 3" in doc


def test_main_flag_dispatch_and_bare_main_unchanged(monkeypatch):
    """`--break` yalnız main_break'i çağırır; bayraksız main() aynı (test_faz6_s6 kalıbı; kırılma dosyalarına dokunmaz)."""
    calls = []
    monkeypatch.setattr(sc, "main_break", lambda: calls.append("break") or 0)
    monkeypatch.setattr(sc, "main_oot", lambda: calls.append("oot") or 0)
    for name in ("build_scores", "build_post_d1_scores", "write_scores", "write_post_d1_scores", "write_doc", "build_break_scores",
                 "write_break_scores", "write_break_doc", "ensure_post_break_records"):
        monkeypatch.setattr(sc, name, lambda *a, _n=name, **k: calls.append(_n) or {})
    monkeypatch.setattr(sc, "pretty_json_bytes", lambda x: b"{}")
    assert sc.main(["--break"]) == 0 and calls == ["break"]
    calls.clear()
    assert sc.main([]) == 0
    assert calls == ["build_scores", "build_post_d1_scores", "write_scores", "write_post_d1_scores", "write_doc"]
    with pytest.raises(SystemExit):
        sc.main(["--break", "--oot"])


# ================================================================ §13-13 ölçek ve dil (sentetik skor satırları)

def _rows(diffs, *, months=12, head="F1"):
    """Sentetik skorlanmış satırlar: model kaybı 0.25 + d, karşılaştırıcı 0.25."""
    out = []
    for i, d in enumerate(diffs):
        loss = {"model": 0.25 + d, "break_floor_v0@ZERO": 0.25, "base_floor_by_type": 0.25, "PRODUCT_BREAK_FLOOR": 0.25}
        out.append({"ticker": f"T{i}", "d1": f"2027-{1 + i % months:02d}-15", "class": sc.CLASS_MACHINE, "status": "SCORED",
                    "losses": {head: loss}})
    return out


def test_13_13_scale_mix_is_refused():
    obs = [sc.PairedObs(sc.SCALE_LIVE_BREAK, f"T{i}", "2027-01", 0.1, 0.2, sc.CLASS_MACHINE) for i in range(12)]
    assert sc.paired_metric(obs)["scale"] == "live_break"
    for other in (sc.SCALE_LIVE, sc.SCALE_BACKTEST, sc.SCALE_LIVE_CONDITIONAL, sc.SCALE_LIVE_POST_D1, sc.SCALE_OOT, "backtest_break"):
        with pytest.raises(sc.ScaleMixError):
            sc.paired_metric(obs + [sc.PairedObs(other, "X", "2027-01", 0.1, 0.2, sc.CLASS_LIVE)])
        with pytest.raises(sc.ScaleMixError):
            sc.merge_scales({"scale": sc.SCALE_LIVE_BREAK}, {"scale": other})


def test_13_13_passes_only_at_n_30_with_interval_below_zero():
    """"geçiyor" yalnız n ≥ 30 ve aralık tamamen 0'ın altında; 10 ≤ n < 30 "yetersiz örnek"; n < 10 hücre yok; hücreler n_machine
    kırılımıyla; bilgi hücresi ürün − @ZERO."""
    assert sc.break_cells(_rows([-0.1] * 9)) == []
    small = sc.break_cells(_rows([-0.1 - 0.001 * i for i in range(29)]))
    assert {c["verdict"] for c in small} == {"yetersiz örnek"} and all(c["n"] == 29 == c["n_machine"] for c in small)
    full = sc.break_cells(_rows([-0.1 - 0.001 * i for i in range(30)]))
    by = {(c["model_id"], c["horizon_or_k"], c["rule_id"]): c for c in full}
    assert by[("break_floor_v0", "F1", "PRODUCT_BREAK_FLOOR")]["verdict"] == "geçiyor"
    assert by[("break_floor_v0", "F1", "PRODUCT_BREAK_FLOOR")]["label"] == "birincil"
    assert by[("PRODUCT_BREAK_FLOOR", "F1", "break_floor_v0@ZERO")]["label"] == "bilgi"
    neutral = sc.break_cells(_rows([(-1) ** i * 0.1 for i in range(40)]))
    assert {c["verdict"] for c in neutral if c["label"] != "bilgi"} == {"ayırt edilemiyor"}
    worse = sc.break_cells(_rows([0.1 + 0.001 * i for i in range(40)]))
    assert {c["verdict"] for c in worse if c["model_id"] == "break_floor_v0"} == {"geçemiyor"}


def test_13_13_promotion_label_stage_1_and_2():
    """§8: n_scored < 30 → backtest k1 ile "ön eleme …; canlı n = k" (k1 yoksa "basit kuraldan ayırt edilemiyor (backtest)"); n ≥ 30 →
    yalnız canlı k2 (birincil ve @ZERO ikisi de "geçiyor")."""
    from borsai import report_faz8 as r8

    assert sc.BREAK_PROMOTION_STAGE1.format(n=0) == r8.PROMOTION_LABEL
    p = sc.break_promotion(12, 12, 0, [], BACKTEST)
    assert (p["stage"], p["promoted"], p["label"]) == (1, True, "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 12")
    assert sc.break_promotion(12, 12, 0, [], {**BACKTEST, "k1": False})["label"] == "basit kuraldan ayırt edilemiyor (backtest)"
    good = sc.break_cells(_rows([-0.1 - 0.001 * i for i in range(30)]))
    p2 = sc.break_promotion(30, 30, 0, good, {**BACKTEST, "k1": False})
    assert (p2["stage"], p2["promoted"], p2["live_verdict"]) == (2, True, "geçiyor")
    assert p2["label"] == "canlı sicil (prospektif, n = 30; makine sıralı 30 / LIVE 0)"
    mixed = [dict(c, verdict="ayırt edilemiyor") if c["rule_id"] == "break_floor_v0@ZERO" else c for c in good]
    p3 = sc.break_promotion(30, 30, 0, mixed, BACKTEST)
    assert (p3["promoted"], p3["label"]) == (False, "ayırt edilemiyor")


def test_13_13_doc_says_gecer_only_with_passing_cells(syn):
    _, _, _, scores = syn
    base = json.loads(pretty_json_bytes(scores))
    doc0 = sc.render_break_doc(base)
    assert "| geçiyor |" not in doc0 and "hücre yok, hüküm yok" in doc0
    for diffs, want in (([-0.1 - 0.001 * i for i in range(30)], True), ([-0.1 - 0.001 * i for i in range(29)], False)):
        s = copy.deepcopy(base)
        s["models"][0]["live_break"]["cells"] = json.loads(pretty_json_bytes(sc.break_cells(_rows(diffs))))
        assert ("| geçiyor |" in sc.render_break_doc(s)) is want


# ================================================================ bu görevin commit'leri (K-PIN-L; SPEC_DEVIATIONS N26)

def _task_commits():
    out = subprocess.run(["git", "log", "--format=%H %s", f"{TASK_BASE}..HEAD"], cwd=ROOT, check=True, capture_output=True,
                         text=True).stdout.splitlines()
    return [x.split(" ", 1) for x in out if x.split(" ", 1)[1].startswith(LIVE_PREFIX)]


@pytest.mark.requires_git_history
def test_task_commits_only_add_post_break_records_and_scores_break():
    """Proje sahibi kararı (2026-10-02): bu görevin commit'leri (konusu BORSAI_FAZ8_LIVE_ ile başlayanlar) registry/ ve scores/'ta
    yalnız registry/post_break/** ve scores/scores_break.json EKLER; models/, data/, app/, legacy/, tests/reference/, docs/specs*,
    CLAUDE.md ve experiments/log.jsonl'a dokunmaz. Commit öncesi koşuda (bu görevin commit'i yokken) denetlenecek commit yoktur."""
    for sha, subject in _task_commits():
        st = subprocess.run(["git", "diff", "--name-status", f"{sha}^", sha, "--", "registry", "scores"], cwd=ROOT, check=True,
                            capture_output=True, text=True).stdout.splitlines()
        for line in st:
            status, path = line.split("\t", 1)
            assert status == "A" and (path.startswith("registry/post_break/") or path == "scores/scores_break.json"), (subject, line)
        other = subprocess.run(["git", "diff", "--name-only", f"{sha}^", sha, "--", "models", "data", "app", "legacy", "tests/reference",
                                "docs/specs", "docs/specs_faz4", "docs/specs_faz5", "docs/specs_faz6", "docs/specs_faz7",
                                "docs/specs_faz7_c", "docs/specs_faz8", "CLAUDE.md", "experiments/log.jsonl", "scores/scores.json",
                                "scores/scores_post_d1.json", "scores/scores_oot.json", "docs/SCORES.md", "docs/SCORES_OOT.md",
                                "docs/MODELS.md"], cwd=ROOT, check=True, capture_output=True, text=True).stdout
        assert other == "", (subject, other)


def test_hygiene_no_bulletin_names_or_sealed_codes_in_live_outputs():
    """Görev kuralı: belgelerde ve skor dosyasında bülten adı kalıbı ve kasa kodu yok (makine kayıtları bülten atfı taşır; onları
    kayıt bekçisi denetler)."""
    _, cohort = reg.read_cohort()
    sealed = sorted(r["ticker"] for r in reg.cohort_members(cohort) if r["vault"] == reg.VAULT_SEALED)
    pattern = re.compile(r"\b(" + "|".join(sealed) + r")\b")
    paths = [ROOT / "scores" / "scores_break.json", ROOT / "docs" / "SCORES_BREAK.md", Path(__file__)]
    for p in [x for x in paths if x.exists()]:
        text = p.read_text(encoding="utf-8")
        n = len(set(pattern.findall(text)))                                       # yerel değişken: hata çıktısı kod basmaz
        assert n == 0, (p.name, n)
        assert not re.search(r"th[bm]20\d{6}", text, re.IGNORECASE), p.name


# ================================================================ gerçek dosyalar (commit B: ilk `--break` koşusu; §13-12, K1, K2)

FROZEN_7 = list(REAL_EXPECTED)


def _real_records():
    out = {}
    for p in sorted((ROOT / "registry" / "post_break").rglob("*.json")):
        out.setdefault(p.parent.name, []).append((p, json.loads(p.read_text(encoding="utf-8"))))
    return out


def _subject(sha):
    return subprocess.run(["git", "log", "-1", "--format=%s", sha], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


@pytest.mark.requires_git_history
def test_real_seven_machine_records_match_expected_and_pass_guard():
    """K1: registry/post_break/ altında arz başına tam bir kayıt; değerler görev metninin beklenen tablosuyla (b, D_b, b_floor birebir;
    |Δp| ≤ 1e-12); bekçi temiz; dosya adı içerik adresli; kod A commit'inde temiz ağaçla (borsai_dirty false) üretildi; ürün 7/7
    NOT_AVAILABLE; NETGL kırpma uyarısı."""
    recs = _real_records()
    assert sorted(recs) == sorted(FROZEN_7) and all(len(v) == 1 for v in recs.values())
    man = _manifest()
    index_sha = sha256_file(ROOT / "models" / "INDEX_POST_BREAK.json")
    for t, [(p, rec)] in recs.items():
        d1, L, b, db, floor, p1, p2 = REAL_EXPECTED[t]
        cells = {c["model_id"]: c for c in rec["models"]}
        out = cells["break_floor_v0"]["output"]
        assert (rec["streak"]["sessions"][0]["date"], rec["streak"]["L"], rec["streak"]["b"], rec["streak"]["break_date"],
                rec["break_day"]["b_floor"]) == (d1, L, b, db, floor), t
        assert abs(out["F1"]["p_floor"] - p1) <= 1e-12 and abs(out["F2"]["p_floor"] - p2) <= 1e-12, t
        assert cells["break_floor_v0@ZERO"]["output"]["F1"]["p_floor"] == 25 / 82, t
        assert reg.post_break_record_problems(rec, man) == [], t
        assert p.name == fz.machine_record_filename(p.read_bytes(), rec["produced_at_utc"]), t
        assert rec["models_index"]["sha256"] == index_sha and rec["inputs_ref"]["inputs_pit_ok"] is True, t
        assert rec["code"]["borsai_dirty"] is False and _subject(rec["code"]["git_head"]).startswith("BORSAI_FAZ8_LIVE_A:"), t
        assert rec["comparators"]["PRODUCT_BREAK_FLOOR"]["status"] == "NOT_AVAILABLE", t
        codes = [w["code"] for w in out["warnings"]]
        assert codes == (["B_TURNOVER_CLIPPED_TO_TRAINING_P05_P95"] if t == "NETGL" else []), (t, codes)


@pytest.fixture(scope="module")
def real_scores():
    return json.loads((ROOT / "scores" / "scores_break.json").read_text(encoding="utf-8"))


def test_real_scores_break_all_retro_n_scored_zero_identity(real_scores):
    """K2 / §13-12: bugünkü 7 arz RETRO (yalnız retro_info), n_scored = n_machine = n_live = 0; payda 7 satır, hepsi RETRO; özdeşlik;
    NETGL b = 4, b_floor = 1, FON_KRIZI_2026; ürün 7/7 NOT_AVAILABLE; öne çıkan durum aşama 1 "ön eleme …; canlı n = 0"."""
    s = real_scores
    [m] = s["models"]
    b = m["live_break"]
    assert (s["schema_version"], s["scale"], m["model_id"], m["kind"]) == ("borsai.scores_break/1", "live_break", "break_floor_v0",
                                                                         "post_break")
    assert (b["n_scored"], b["n_machine"], b["n_live"], b["n_rows"], b["n_retro"]) == (0, 0, 0, 0, 7)
    assert b["rows"] == [] and b["cells"] == [] and b["descriptive"] == [] and sc.break_denominator_problems(b) == []
    frozen = [r["ticker"] for r in reg.read_ipos()[1] if r["status"] == "FROZEN"]
    assert [d["ticker"] for d in b["denominator"]] == frozen == FROZEN_7
    assert {(d["stage_status"], d["class"]) for d in b["denominator"]} == {("RETRO", "RETRO")}
    retro = {x["ticker"]: x for x in s["retro_info"]}
    assert list(retro) == FROZEN_7
    for t, x in retro.items():
        d1, L, bb, db, floor, p1, p2 = REAL_EXPECTED[t]
        assert (x["d1"], x["L"], x["b"], x["break_date"], x["b_floor"]) == (d1, L, bb, db, floor), t
        assert x["p"] == {"F1": p1, "F2": p2} and x["comparators"]["PRODUCT_BREAK_FLOOR"]["status"] == "NOT_AVAILABLE", t
        assert x["class_evidence"]["model_prospective"] is False and x["parity"]["max_abs_diff"] <= 1e-12, t
        assert x["comparators"]["base_floor_by_type"]["F1"] == (0.5428571428571428 if floor else 0.1276595744680851), t
    netgl = retro["NETGL"]
    assert (netgl["b"], netgl["b_floor"], netgl["regime_tags"]) == (4, 1, ["FON_KRIZI_2026"])
    assert [t for t, x in retro.items() if x["regime_tags"]] == ["NETGL"]
    card = m["card"]
    assert card["model_commit"].startswith("4d3c9a2") and card["model_push_proof_created_at"] == "2026-10-02T14:45:08Z"
    assert (card["promotion"]["stage"], card["promotion"]["promoted"], card["promotion"]["label"]) == (
        1, True, "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0")
    assert card["backtest_info"]["k1"] is True and card["backtest_info"]["label"] == "backtest'te geçiyor (tasarıma maruz)"


def test_real_scores_break_doc_is_render_of_written_json(real_scores):
    doc = (ROOT / "docs" / "SCORES_BREAK.md").read_text(encoding="utf-8")
    assert doc == sc.render_break_doc(real_scores)
    assert "| NETGL | 2026-09-17 | 3 | 4 | 2026-09-22 | 1 | 0.4991 | 0.3043 |" in doc


@pytest.mark.requires_raw_sources
def test_real_scores_break_seven_rows_match_recomputation(real_scores):
    """Yeniden hesap (bugünkü kod ve dosyalar; kayıt yazılmaz): 7 arzın payda ve retro satırları commit'li dosyayla aynı (sonra
    eklenecek arzlar bu satırları değiştirmez)."""
    mem = json.loads(pretty_json_bytes(sc.build_break_scores()))
    for key in ("denominator",):
        got = {x["ticker"]: x for x in mem["models"][0]["live_break"][key] if x["ticker"] in REAL_EXPECTED}
        want = {x["ticker"]: x for x in real_scores["models"][0]["live_break"][key] if x["ticker"] in REAL_EXPECTED}
        assert got == want
    got = {x["ticker"]: x for x in mem["retro_info"] if x["ticker"] in REAL_EXPECTED}
    want = {x["ticker"]: x for x in real_scores["retro_info"] if x["ticker"] in REAL_EXPECTED}
    assert got == want

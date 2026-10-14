"""borsai/outcomes.py: SPEC_SCORING §10 kabul testleri 1–4 (H99 yeniden üretim, yarım gün, durdurma, tavan
etiketi), indirici (yeniden yazmama, manifest, pinli sha, izinli kaynak, sıra kuralı), sonuç dosyası (yalnız
PENDING satırlar dolar), ilan dışı kapanış ve tamlık denetimi kuralları."""
from __future__ import annotations

import csv
import io
import subprocess
import zipfile
from decimal import Decimal

import pytest

from borsai import outcomes as oc
from borsai import registry as reg
from borsai.provenance import ROOT, sha256_bytes, sha256_file

H99_TABLE = ROOT / "data" / "training_table.csv"


def _read(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def calendar():
    return oc.load_calendar()


@pytest.fixture(scope="module")
def h99():
    """SESSIONS dosyasının ham THB/THM alanlarından tarih -> kod -> satır (SPEC_SCORING §10-1)."""
    rows = _read(oc.SESSIONS_PATH)
    thb, thm = {}, {}
    for r in rows:
        d, code = r["target_session_date"], r["ticker"] + ".E"
        halt = {"ACTIVE_NOT_SUSPENDED": "0", "SUSPENDED": "1"}[r["security_trading_status"]]
        thb.setdefault(d, {})[code] = oc.ThbRow(code, r["thb_raw_close"], r["thb_raw_trade_count"], halt)
        thm.setdefault(d, {})[code] = oc.ThmRow(code, r["thm_raw_reference_price"], r["thm_raw_upper_limit"],
                                                r["thm_raw_lower_limit"])
    sessions = {}
    for r in rows:
        sessions.setdefault(r["ticker"], {})[int(r["session_number"])] = r["target_session_date"]
    return {"thb": thb, "thm": thm, "sessions": sessions, "table": {r["ticker"]: r for r in _read(H99_TABLE)}}


@pytest.fixture(scope="module")
def h99_outcomes(calendar, h99):
    return {t: oc.outcome_rows(t, tr["ipo_price_tl"], calendar, h99["thb"], h99["thm"], start=tr["first_trading_date"])
            for t, tr in h99["table"].items()}


# ---------------------------------------------------------------- §10-1 H99 yeniden üretim

def test_1_h99_reproduction_is_exact(h99, h99_outcomes):
    n_dates = n_targets = n_labels = 0
    close = {k: 0 for k in (1, 3, 5, 10)}
    streak = {k: 0 for k in (1, 3, 5, 10)}
    for t, tr in h99["table"].items():
        rows = h99_outcomes[t]
        assert [r["status"] for r in rows] == [oc.STATUS_OK] * 10, t
        for r in rows:
            h = int(r["h"])
            assert r["session_date"] == h99["sessions"][t][h], (t, h)
            n_dates += 1
            assert r["ceiling_close"] == tr[f"ceiling_close_D{h}"], (t, h)
            n_labels += 1
            if h in oc.TARGET_H:
                assert Decimal(r["R_h"]) == Decimal(tr[f"R_D{h}"]), (t, h)
                assert r["Y_h"] == tr[f"Y_D{h}"], (t, h)
                n_targets += 1
                close[h] += int(r["ceiling_close"])
            else:
                assert r["R_h"] == r["Y_h"] == ""
        L = oc.streak([int(r["ceiling_close"]) for r in rows])
        assert L == int(tr["ceiling_streak_L"]), t
        for k in streak:
            streak[k] += L >= k
    assert (n_dates, n_targets, n_labels, len(h99["table"])) == (990, 396, 990, 99)
    assert close == {1: 81, 3: 67, 5: 48, 10: 25}
    assert streak == {1: 81, 3: 66, 5: 41, 10: 14}


def test_1b_exact_return_matches_legacy_targets_file():
    """R_h metni legacy exact_return ile aynı (50 anlamlı hane): TARGETS dosyasıyla metin eşitliği."""
    for r in _read(ROOT / "data" / "raw" / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv"):
        text, y = oc.exact_return(r["official_close"], r["ipo_price"])
        assert text == r["target_return"] and str(y) == r["above_ipo_flag"], (r["ticker"], r["horizon"])


# ---------------------------------------------------------------- §10-2 yarım gün

def test_2_half_days_count_as_sessions(h99_outcomes, calendar):
    half = sorted((t, int(r["h"])) for t, rows in h99_outcomes.items() for r in rows if r["half_day"] == "1")
    assert ("EKDMR", 3) in half and ("GENKM", 10) in half
    assert half == sorted([("EKDMR", 3), ("MCARD", 7), ("LXGYO", 8), ("GENKM", 10), ("SVGYO", 10), ("ENTRA", 4)])
    assert all(calendar.is_half(r["session_date"]) for rows in h99_outcomes.values() for r in rows if r["half_day"] == "1")
    assert calendar.is_half("2026-10-28") and "2026-10-29" not in calendar.sessions and "2026-10-28" in calendar.sessions


# ---------------------------------------------------------------- §10-3 durdurma (sentetik)

START = "2026-09-01"


def synthetic(calendar, n, *, untraded=(), halted=(), code="SNT.E", close="11", limit="11", halt_code="1"):
    """START'tan itibaren n resmi seans; `untraded` (1'den sayılan seans sırası) sözleşme = 0."""
    thb, thm = {}, {}
    for i, s in enumerate(calendar.sessions_from(START)[:n], start=1):
        tc = "0" if i in untraded else "100"
        halt = halt_code if i in halted else "0"
        thb[s] = {code: oc.ThbRow(code, close, tc, halt)}
        thm[s] = {code: oc.ThmRow(code, "10", limit, "9")}
    return thb, thm


def test_3a_full_day_suspension_shifts_without_breaking_streak(calendar):
    thb, thm = synthetic(calendar, 11, untraded={4})
    rows = oc.outcome_rows("SNT", "10", calendar, thb, thm)
    sessions = calendar.sessions_from(START)
    assert [r["session_date"] for r in rows[:3]] == list(sessions[:3])
    assert rows[3]["session_date"] == sessions[4]          # D_4 bir sonraki seansa kaydı
    assert [r["shifted_by_suspension"] for r in rows] == ["0"] * 3 + ["1"] * 7
    assert oc.streak([int(r["ceiling_close"]) for r in rows]) == 10   # seri bozulmadı
    assert all(r["status"] == oc.STATUS_OK for r in rows)


def test_3b_intraday_halt_counts(calendar):
    thb, thm = synthetic(calendar, 10, halted={2})
    rows = oc.outcome_rows("SNT", "10", calendar, thb, thm)
    assert rows[1]["halt_flag"] == "1" and rows[1]["session_date"] == calendar.sessions_from(START)[1]
    assert [r["halt_flag"] for r in rows].count("1") == 1


def test_3c_fifteen_session_limit(calendar):
    thb, thm = synthetic(calendar, 20, untraded={2, 3, 4, 5, 6, 7})   # 15 seansta yalnız 9 işlem
    rows = oc.outcome_rows("SNT", "10", calendar, thb, thm)
    assert [r["status"] for r in rows] == [oc.STATUS_OK] * 9 + [oc.STATUS_TARGET_UNAVAILABLE]
    assert rows[9]["R_h"] == ""


def test_3d_unknown_official_code_stops(calendar):
    thb, thm = synthetic(calendar, 10, halted={3}, halt_code="7")
    with pytest.raises(oc.UnknownOfficialCode):
        oc.outcome_rows("SNT", "10", calendar, thb, thm)


def test_3e_missing_bulletin_is_pending(calendar):
    thb, thm = synthetic(calendar, 4)
    rows = oc.outcome_rows("SNT", "10", calendar, thb, thm)
    assert [r["status"] for r in rows] == [oc.STATUS_OK] * 4 + [oc.STATUS_PENDING] * 6
    assert rows[4]["session_date"] == "" and rows[4]["ceiling_close"] == ""
    assert oc.streak([int(r["ceiling_close"]) for r in rows[:4]]) is None   # seri sürüyor: L bilinmiyor


# ---------------------------------------------------------------- §10-4 tavan etiketi

def _session(close):
    return oc.Session("2026-09-01", 1, close, "10", 0, 0, 0)


@pytest.mark.parametrize("close,upper,expected", [("10.12", "10.120", 1), ("10.11", "10.120", 0), ("10.12", "", None),
                                                  ("10.12", "0", None), ("10.12", None, None)])
def test_4_ceiling_label_decimal(close, upper, expected):
    thm = {} if upper is None else {"2026-09-01": {"SNT.E": oc.ThmRow("SNT.E", "9.2", upper, "8.28")}}
    assert oc.ceiling_label("SNT", _session(close), thm) == expected


def test_4b_na_limit_row_and_streak(calendar):
    thb, thm = synthetic(calendar, 10)
    first = calendar.sessions_from(START)[0]
    thm[first] = {"SNT.E": oc.ThmRow("SNT.E", "10", "", "9")}
    rows = oc.outcome_rows("SNT", "10", calendar, thb, thm)
    assert rows[0]["status"] == oc.STATUS_NA_LIMIT and rows[0]["ceiling_close"] == oc.NA and rows[0]["R_h"] == "0.1"
    assert oc.streak([None if r["ceiling_close"] == oc.NA else int(r["ceiling_close"]) for r in rows]) is None


def test_4c_lilak_borls_d1_ceiling_despite_return_above_ten_percent(h99, h99_outcomes):
    for t in ("LILAK", "BORLS"):
        d1 = h99_outcomes[t][0]
        assert Decimal(d1["R_h"]) != Decimal("0.1") and d1["ceiling_close"] == "1"


# ---------------------------------------------------------------- kaynak: 2026-08-17 (commit A)

@pytest.mark.requires_raw_sources
def test_source_check_2026_08_17_matches_h99_sessions():
    pinned = oc.h99_pinned_sha256()
    manifest = {(r["date"], r["kind"]): r for r in oc.read_manifest()}
    for kind in oc.KINDS:
        path = oc.local_path("2026-08-17", kind)
        assert path.exists(), path
        sha = sha256_file(path)
        assert sha == pinned[("2026-08-17", kind)]
        m = manifest[("2026-08-17", kind)]
        assert m["sha256"] == sha and int(m["bytes"]) == path.stat().st_size
        assert m["url"] == oc.source_url("2026-08-17", kind) == f"https://www.borsaistanbul.com/data/{kind}/2026/08/{kind}202608171.zip"
        assert m["internal_filename"] == f"{kind}202608171.csv"


@pytest.mark.requires_raw_sources
def test_parsed_2026_08_17_equals_h99_raw_fields():
    """QUICK D8 (2026-08-17): ayrıştırılan ham metin SESSIONS'taki thb_raw_* / thm_raw_* ile aynı."""
    ref = next(r for r in _read(oc.SESSIONS_PATH) if r["ticker"] == "QUICK" and r["target_session_date"] == "2026-08-17")
    thb, thm = oc.local_bulletin("2026-08-17", "thb"), oc.local_bulletin("2026-08-17", "thm")
    b, m = thb.get("QUICK.E"), thm.get("QUICK.E")
    assert (b.close, b.trade_count, b.halt) == (ref["thb_raw_close"], ref["thb_raw_trade_count"], "0")
    assert (m.reference, m.upper, m.lower) == (ref["thm_raw_reference_price"], ref["thm_raw_upper_limit"], ref["thm_raw_lower_limit"])


@pytest.mark.requires_raw_sources
def test_manifest_rows_match_files():
    rows = oc.read_manifest()
    assert rows, "MANIFEST.csv boş"
    assert tuple(_read(oc.BIST_DIR / oc.MANIFEST_NAME)[0].keys()) == oc.MANIFEST_COLUMNS
    keys = [(r["date"], r["kind"]) for r in rows]
    assert len(keys) == len(set(keys))
    on_disk = {p.relative_to(oc.BIST_DIR).as_posix() for p in oc.BIST_DIR.rglob("*.zip")}
    assert on_disk == {oc.local_path(d, k).relative_to(oc.BIST_DIR).as_posix() for d, k in keys}
    pinned = oc.h99_pinned_sha256()
    for r in rows:
        assert sha256_file(oc.local_path(r["date"], r["kind"])) == r["sha256"]
        assert r["url"] == oc.source_url(r["date"], r["kind"])
        if (r["date"], r["kind"]) in pinned:
            assert pinned[(r["date"], r["kind"])] == r["sha256"], (r["date"], r["kind"])


# ---------------------------------------------------------------- indirici (sahte indirici, geçici dizin)

HEAD_TR = ["TARIH", "ISLEM  KODU", "BULTEN ADI", "PAZAR", "ENSTRUMAN GRUBU", "GECICI DURDURMA", "KAPANIS FIYATI",
           "TOPLAM SOZLESME SAYISI"]
HEAD_THM = ["TARIH", "ISLEM  KODU", "REFERANS FIYATI", "UST LIMIT FIYATI", "ALT LIMIT FIYATI"]


def make_zip(day, kind, rows, head=None):
    head = list(head or (HEAD_TR if kind == "thb" else HEAD_THM))
    if kind == "thb":   # SPEC_POST_D1_V0 §7.6: REQUIRED genişledi; sentetik bültenlerde D_1 alanları boş sütun olarak sonda
        extra = [c for c in oc.THB_D1_COLUMNS.values() if c not in head]
        head += extra
        rows = [list(r) + [""] * len(extra) for r in rows]
    text = "\n".join(";".join(r) for r in [head, [h.lower() for h in head]] + [[day] + list(r) for r in rows]) + "\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(oc.internal_name(day, kind), text.encode("cp1254"))
    return buf.getvalue()


def put(bist_dir, day, kind, rows, head=None):
    data = make_zip(day, kind, rows, head)
    oc._write_new(oc.local_path(day, kind, bist_dir), data)
    oc._append_csv(bist_dir / oc.MANIFEST_NAME, oc.MANIFEST_COLUMNS, {
        "date": day, "kind": kind, "url": oc.source_url(day, kind), "sha256": sha256_bytes(data), "bytes": len(data),
        "internal_filename": oc.internal_name(day, kind), "downloaded_at": "test", "http_last_modified": ""})


class FakeDownloader:
    def __init__(self, files, missing=()):
        self.files, self.missing, self.calls = files, set(missing), []

    def __call__(self, url):
        self.calls.append(url)
        if url in self.missing or url not in self.files:
            raise oc.NotPublished(url)
        return self.files[url], "Tue, 22 Sep 2026 15:00:00 GMT"


def test_fetch_writes_once_and_never_overwrites(tmp_path):
    day = "2025-01-02"
    url = oc.source_url(day, "thb")
    dl = FakeDownloader({url: make_zip(day, "thb", [["AAA.E", "A", "Z", "EQT", "0", "5", "3"]])})
    b = oc.fetch(day, "thb", bist_dir=tmp_path, downloader=dl, pinned={})
    assert b.get("AAA.E").close == "5" and len(dl.calls) == 1
    oc.fetch(day, "thb", bist_dir=tmp_path, downloader=dl, pinned={})
    assert len(dl.calls) == 1                                  # yerelde var: ağa çıkılmaz
    [m] = oc.read_manifest(tmp_path)
    assert m["sha256"] == sha256_file(oc.local_path(day, "thb", tmp_path)) and m["http_last_modified"]
    with pytest.raises(FileExistsError):
        oc._write_new(oc.local_path(day, "thb", tmp_path), b"x")
    oc.local_path(day, "thb", tmp_path).write_bytes(make_zip(day, "thb", [["AAA.E", "A", "Z", "EQT", "0", "6", "3"]]))
    with pytest.raises(oc.OutcomeError, match="manifest"):
        oc.fetch(day, "thb", bist_dir=tmp_path, downloader=dl, pinned={})


def test_fetch_rejects_changed_pinned_source(tmp_path):
    day = "2025-01-02"
    url = oc.source_url(day, "thb")
    dl = FakeDownloader({url: make_zip(day, "thb", [["AAA.E", "A", "Z", "EQT", "0", "5", "3"]])})
    with pytest.raises(oc.SourceChanged):
        oc.fetch(day, "thb", bist_dir=tmp_path, downloader=dl, pinned={(day, "thb"): "0" * 64})
    assert not oc.local_path(day, "thb", tmp_path).exists() and oc.read_manifest(tmp_path) == []


def test_download_only_from_official_host():
    with pytest.raises(oc.OutcomeError, match="izinli"):
        oc.download_bytes("https://example.com/data/thb/2026/08/thb202608171.zip")


def test_parse_rejects_wrong_internal_name_and_duplicates():
    data = make_zip("2025-01-02", "thb", [["AAA.E", "A", "Z", "EQT", "0", "5", "3"]])
    with pytest.raises(oc.OutcomeError, match="iç dosya"):
        oc.parse_archive_bytes(data, "thb202501031.csv")
    dup = oc.parse_bulletin(make_zip("2025-01-02", "thb", [["AAA.E", "A", "Z", "EQT", "0", "5", "3"]] * 2), "2025-01-02", "thb")
    with pytest.raises(oc.OutcomeError, match="SOURCE_CONFLICT"):
        dup.get("AAA.E")


def test_sequence_guard_blocks_post_cutoff_download_without_committed_models(tmp_path):
    oc.sequence_guard("2026-08-19", root=tmp_path)             # sınırda: serbest
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "INDEX.json").write_text('{"models": [{"file": "m.json"}]}', encoding="utf-8")
    (tmp_path / "registry" / "records").mkdir(parents=True)
    with pytest.raises(oc.SequenceRuleError):
        oc.sequence_guard("2026-08-20", root=tmp_path)
    url = oc.source_url("2026-09-01", "thb")
    dl = FakeDownloader({url: b"never"})
    with pytest.raises(oc.SequenceRuleError):
        oc.fetch("2026-09-01", "thb", bist_dir=tmp_path / "bist", downloader=dl, pinned={}, root=tmp_path)
    assert dl.calls == []
    oc.sequence_guard("2026-09-01", root=ROOT)                  # bu repoda modeller ve kayıtlar commit edilmiş


def test_unannounced_closure_and_stop_at_unpublished(tmp_path, calendar):
    s = calendar.sessions_from("2025-02-03")[:4]
    files = {}
    for d in (s[0], s[2]):
        for kind in oc.KINDS:
            rows = [["AAA.E", "A", "Z", "EQT", "0", "5", "3"]] if kind == "thb" else [["AAA.E", "5", "5.5", "4.5"]]
            files[oc.source_url(d, kind)] = make_zip(d, kind, rows)
    dl = FakeDownloader(files)
    res = oc.download_range(calendar, s[0], s[3], bist_dir=tmp_path, downloader=dl, root=ROOT, pinned={})
    assert res["unannounced_closures"] == [s[1]] and res["through_session"] == s[2]   # s[3] yayımlanmamış: dur
    [c] = oc.read_closures(tmp_path)
    assert c["date"] == s[1] and c["later_session_published"] == s[2]
    cal2 = oc.load_calendar(bist_dir=tmp_path)
    assert s[1] not in cal2.sessions and s[1] in cal2.closures


# ---------------------------------------------------------------- sonuç dosyası

def test_outcome_file_only_pending_rows_change(tmp_path, calendar):
    thb, thm = synthetic(calendar, 4)
    first = oc.outcome_rows("SNT", "10", calendar, thb, thm)
    assert oc.write_outcome("SNT", first, tmp_path) == "CREATED"
    assert oc.write_outcome("SNT", first, tmp_path) == "UNCHANGED"
    thb, thm = synthetic(calendar, 11)
    full = oc.outcome_rows("SNT", "10", calendar, thb, thm)
    assert oc.write_outcome("SNT", full, tmp_path) == "UPDATED"
    assert oc.read_outcome(oc.outcome_path("SNT", tmp_path)) == full
    changed = [dict(r) for r in full]
    changed[0]["close_raw"] = "11.00"
    with pytest.raises(oc.OutcomeConflict):
        oc.write_outcome("SNT", changed, tmp_path)
    assert oc.read_outcome(oc.outcome_path("SNT", tmp_path)) == full


@pytest.mark.requires_raw_sources
def test_committed_outcomes_rebuild_from_raw_bulletins():
    """data/outcomes/<T>.csv, yerel ham bültenlerden ağsız yeniden hesaplanınca birebir aynı (dosya varsa)."""
    files = sorted(p for p in oc.OUTCOMES_DIR.glob("*.csv") if p.name != oc.COMPLETENESS_NAME) if oc.OUTCOMES_DIR.exists() else []
    if not files:
        assert oc.as_of_session() in (None, "2026-08-17")
        return
    cal = oc.load_calendar()
    built = oc.build_outcomes(cal, oc.as_of_session(cal), write=False)
    assert {p.stem for p in files} == {t for t, o in built.items() if "rows" in o}
    for p in files:
        assert oc.read_outcome(p) == [{k: r[k] for k in oc.OUTCOME_COLUMNS} for r in built[p.stem]["rows"]], p.stem
        assert all(r["status"] in oc.ROW_STATUSES for r in oc.read_outcome(p))


# ---------------------------------------------------------------- tamlık denetimi (SPEC_SCORING §4)

def test_completeness_rules(tmp_path, calendar):
    d0, d1, d2 = calendar.sessions_from("2025-02-03")[:3]
    base = [["OLD.E", "ESKI AS", "Z", "EQT", "0", "5", "3"], ["WAR.V", "W", "K", "ECW", "0", "1", "1"]]
    put(tmp_path, d0, "thb", base)
    put(tmp_path, d1, "thb", base + [["NEWV.V", "V", "K", "EPW", "0", "1", "1"], ["IPO.E", "IPO AS", "Z", "EQT", "0", "5", "9"],
                                     ["OOS.E", "OOS AS", "W", "EQT", "0", "5", "1"]])
    put(tmp_path, d2, "thb", [["WAR.V", "W", "K", "ECW", "0", "1", "1"], ["IPO.E", "IPO AS", "Z", "EQT", "0", "5", "9"],
                              ["OOS.E", "OOS AS", "W", "EQT", "0", "5", "1"], ["NEW.E", "ESKI AS", "Z", "EQT", "0", "5", "3"],
                              ["ZZZ.E", "BILINMEYEN AS", "Z", "EQT", "0", "5", "3"]])
    ipos = [{"ticker": "IPO", "status": "FROZEN", "skip_reason": "", "first_trading_date": d1},
            {"ticker": "OOS", "status": "OUT_OF_SCOPE", "skip_reason": "OTHER:PAZAR_DEGISIKLIGI", "first_trading_date": ""},
            {"ticker": "LATE", "status": "FROZEN", "skip_reason": "", "first_trading_date": d2}]
    res = oc.completeness(calendar, d1, d2, bist_dir=tmp_path, ipos_rows=ipos)
    got = {e["code"]: (e["first_seen"], e["classification"], e["reason"]) for e in res["new_codes"]}
    assert got == {
        "NEWV.V": (d1, oc.C_NON_EQUITY, "varant (satım)"),
        "IPO.E": (d1, oc.C_REGISTERED, "FROZEN"),
        "OOS.E": (d1, oc.C_REGISTERED, "OUT_OF_SCOPE:OTHER:PAZAR_DEGISIKLIGI"),
        "NEW.E": (d2, oc.C_CODE_CHANGE, "eski kod OLD.E"),
        "ZZZ.E": (d2, oc.C_UNEXPLAINED, "olası yeni halka arz; DUR ve raporla"),
    }
    assert res["listed_not_seen"] == ["LATE"] and not res["ok"]
    assert [e["code"] for e in res["unexplained"]] == ["ZZZ.E"]


@pytest.mark.requires_raw_sources
def test_committed_completeness_file_rebuilds():
    path = oc.OUTCOMES_DIR / oc.COMPLETENESS_NAME
    if not path.exists():
        return
    cal = oc.load_calendar()
    rows = _read(path)
    through = max(r["first_seen"] for r in rows)
    res = oc.completeness(cal, reg.SCOPE_START, oc.as_of_session(cal))
    assert through <= oc.as_of_session(cal)
    assert rows == [{k: e.get(k, "") for k in oc.COMPLETENESS_COLUMNS} for e in res["new_codes"]]
    assert res["ok"], (res["unexplained"], res["listed_not_seen"])


HEAD_BUYIN = HEAD_TR + ["YAPISAL BAZDA PIYASA ALT BOLUMU", "ENSTRUMAN TIPI"]


def test_completeness_buyin_rule_is_general(tmp_path, calendar):
    """EK 1: temerrüt (buy-in) pazarı satırı -> TEMERRUT_PAZARI; koşullardan herhangi biri yeter (PAZAR ya da
    YAPISAL BAZDA PIYASA ALT BOLUMU = BUYIN, ENSTRUMAN TIPI BUYIN ile başlıyor). Kural başka hiçbir yeni
    payı açıklamaz."""
    d0, d1 = calendar.sessions_from("2025-02-03")[:2]
    base = [["AAA.E", "AAA AS", "Z", "EQT", "0", "5", "3", "MSPOT", "MSPOTEQT"],
            ["BBB.E", "BBB AS", "Z", "EQT", "0", "5", "3", "MSPOT", "MSPOTEQT"]]
    put(tmp_path, d0, "thb", base, HEAD_BUYIN)
    put(tmp_path, d1, "thb", base + [
        ["AAA.TE", "AAA AS -TEMERR", "Z", "EQT", "0", "5", "3", "BUYIN", "BUYINEQT"],   # OYAKC.TE biçimi
        ["BBB.TE", "BBB AS -TEMERR", "Z", "EQT", "0", "5", "1", "MSPOT", "BUYINEQT"],   # yalnız tip
        ["CCC.TE", "CCC AS -TEMERR", "BUYIN", "EQT", "0", "5", "1", "MSPOT", "X"],     # yalnız PAZAR
        ["DDD.E", "DDD AS", "Z", "EQT", "0", "5", "1", "MSPOT", "MSPOTEQT"],           # gerçekten yeni pay
    ], HEAD_BUYIN)
    res = oc.completeness(calendar, d1, d1, bist_dir=tmp_path, ipos_rows=[])
    got = {e["code"]: (e["classification"], e["reason"]) for e in res["new_codes"]}
    assert got == {"AAA.TE": (oc.C_BUYIN, oc.BUYIN_REASON), "BBB.TE": (oc.C_BUYIN, oc.BUYIN_REASON),
                   "CCC.TE": (oc.C_BUYIN, oc.BUYIN_REASON),
                   "DDD.E": (oc.C_UNEXPLAINED, "olası yeni halka arz; DUR ve raporla")}
    assert [e["code"] for e in res["unexplained"]] == ["DDD.E"] and not res["ok"]
    assert oc.BUYIN_REASON == "var olan payın temerrüt işlem kodu; halka arz değil" and oc.C_BUYIN == "TEMERRUT_PAZARI"

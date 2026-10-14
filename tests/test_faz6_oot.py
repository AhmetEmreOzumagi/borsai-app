"""Faz 6 eski kohort altyapısı (BORSAI_FAZ6_OOT_INFRA; SPEC_OOT_PRE_H99_V0, KARARLAR D1–D8; SPEC_DEVIATIONS I).

Takvim C, kohort dosyası ve doğrulayıcısı, kasa çekilişi, rejim etiketleri, `freeze --oot` toplu kayıt yazıcısı, karantina +
indirme kapısı + ayıklayıcı (sentetik zip'ler; ağ yok), S3 (D_1 satırı + eski kohort POST_D1 kaydı), üçüncü terazi
(`OOT_PRE_H99`, ScaleMixError, `class_oot`) ve sentetik skor çıktısı. Gerçek kayıt, bülten ya da sonuç yazılmaz: bütün yazan
testler geçici dizinde koşar. Gerçek kohort dosyasını denetleyen testler S1 commit'inden sonra koşar (öncesinde dosya yok;
`test_s1_files_present_after_s1_commit` sessiz atlamayı engeller)."""
from __future__ import annotations

import csv
import dataclasses
import io
import json
import random
import re
import zipfile
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from borsai import freeze as fz
from borsai import market20 as m20
from borsai import outcomes as oc
from borsai import outcomes_oot as oo
from borsai import predict_path as pth
from borsai import registry as reg
from borsai import scoring as sc
from borsai.provenance import ROOT, pretty_json_bytes, sha256_bytes, sha256_file

import faz6_support as f6
import faz7_support as fs7

NOW = datetime(2026, 9, 25, 9, 0, 0, tzinfo=timezone.utc)
INDEX_IDS = [e["model_id"] for e in json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]]
UNIVERSE = list(csv.DictReader(reg.UNIVERSE_PATH.open(encoding="utf-8")))
S1_PRESENT = reg.COHORT_PATH.exists()
CLASS_WORDS = ("OOT_BLIND", "OOT_RETRO", "LIVE", "LATE_RECORD", "RETRO")


@pytest.fixture(scope="module")
def cal():
    return oo.load_calendar_oot()


# ================================================================ Takvim C (SPEC_MARKET20_V0 §3–§4; takvim_2020_2023.md)

def test_calendar_c_file_is_rebuilt_from_transcribed_constants_and_pinned():
    assert m20.CALENDAR_C_PATH.read_bytes() == m20.calendar_c_bytes()
    assert sha256_file(m20.CALENDAR_C_PATH) == m20.CALENDAR_C_SHA256
    rows = m20.calendar_c_rows()
    assert tuple(rows[0]) == m20.CALENDAR_COLUMNS
    header = m20.CALENDAR_B_EXT_PATH.read_text(encoding="utf-8").splitlines()[0]
    assert ",".join(m20.CALENDAR_COLUMNS) == header                       # Takvim B uzatmasıyla aynı sütunlar
    assert (rows[0]["calendar_date"], rows[-1]["calendar_date"]) == ("2020-01-01", "2023-09-21") and len(rows) == 1360
    ekler = (ROOT / "docs" / "specs_faz6" / "ekler" / "takvim_2020_2023.md").read_text(encoding="utf-8")
    for year, t in m20.HOLIDAY_TABLES_2020_2023.items():                  # kaynak URL ve sha eklerle aynı (PDF repoda değil)
        assert t["url"] in ekler and t["sha256"] in ekler, year


def test_calendar_c_weekday_xu100_gaps_equal_official_closures():
    """Hafta içi XU100 boşlukları = resmi kapanışlar (tatil tablosunun hafta içi tam kapanışları ∪ XU100-boşluk kapanışları);
    yarım günler seanstır ve XU100 kapanışı taşır; yıllık seans sayısı XU100 gün sayısına eşit."""
    c = m20.load_calendar_c()
    records, _ = m20.load_xu100_latest()
    closes = {r.date for r in records}
    weekdays = [d for d in c.days if date.fromisoformat(d).weekday() < 5]
    gaps = {d for d in weekdays if d not in closes}
    closures = {d for d in weekdays if d not in c.sessions}
    table = {d for t in m20.HOLIDAY_TABLES_2020_2023.values() for d in t["full"]
             if d <= m20.CALENDAR_C_LAST and date.fromisoformat(d).weekday() < 5}
    assert gaps == closures == table | set(m20.XU100_GAP_CLOSURES) and len(gaps) == 42
    assert not table & set(m20.XU100_GAP_CLOSURES)
    half = m20.half_days_c()
    assert half == {"2020-07-30", "2020-10-28", "2021-05-12", "2021-07-19", "2021-10-28", "2022-07-08", "2022-10-28",
                    "2023-04-20", "2023-06-27"}                             # takvim_2020_2023.md tablosu
    assert half <= set(c.sessions) and half <= closes
    assert {"2023-02-09", "2023-02-10", "2023-02-13", "2023-02-14"} <= closures   # deprem kapanışı
    assert [sum(s.startswith(str(y)) for s in c.sessions) for y in (2020, 2021, 2022, 2023)] == [252, 249, 252, 177]
    m20.check_calendar_vs_xu100(c, records, m20.CALENDAR_C_FIRST, m20.CALENDAR_C_LAST)


def test_calendar_c_equals_calendar_b_on_overlap_except_xu100_gap_days():
    """2023-01-01…2023-09-21 ortak aralık: aynı; tek fark Takvim B'nin seans saydığı 5 XU100-boşluk günü (SPEC_MARKET20_V0 §1:
    B'nin 2023-09-22 öncesi kısmı yeniden kurma kuralıyla, 5 seansta XU100 yok)."""
    b = {r["calendar_date"]: r for r in csv.DictReader(m20.CALENDAR_B_PATH.open(encoding="utf-8"))}
    diff = [r["calendar_date"] for r in m20.calendar_c_rows() if r["calendar_date"] in b and any(
        r[k] != b[r["calendar_date"]][k] for k in ("weekday_name", "is_weekend", "full_closure", "half_day",
                                                   "counts_as_official_session"))]
    assert diff == list(m20.XU100_GAP_CLOSURES)
    assert all(b[d]["counts_as_official_session"] == "YES" for d in diff)


def test_oot_calendar_is_contiguous_with_h99_calendar(cal):
    """Sonuç takvimi = Takvim C seansları ∪ bülten kanıtında TRADING_SESSION olan günler (EK1 K2; kanıt yoksa Takvim C)."""
    a = oc.load_calendar()
    assert cal.first_day == "2020-01-01" and cal.last_day == a.last_day
    assert tuple(s for s in cal.sessions if s >= "2023-09-22") == a.sessions
    evidence = ROOT / oo.CAL_EVIDENCE_REL
    trading = {r["date"] for r in oo.read_calendar_evidence(evidence) if r["decision"] == oo.EV_TRADING_SESSION} \
        if evidence.exists() else set()
    assert tuple(s for s in cal.sessions if s <= "2023-09-21") == tuple(sorted(set(m20.load_calendar_c().sessions) | trading))
    assert cal.half_days == m20.half_days_c() | a.half_days


def test_oot_market20_ref_date_is_first_trading_date_on_calendar_c():
    """SPEC_MARKET20_V0 §4-e: ref_date = T; Takvim C; kohortun her ilk işlem gününde f6 üretilir (21 kapanış var)."""
    r = m20.oot_market20("2020-02-06")
    assert (r.refusal, r.S0_date, r.S20_date, r.ref_date) == (None, "2020-02-05", "2020-01-08", "2020-02-06")
    assert r.calendar_sha256 == m20.CALENDAR_C_SHA256
    sources = m20.load_oot_sources()
    for u in UNIVERSE:
        res = m20.oot_market20(u["first_trading_date"], sources)
        assert res.refusal is None and res.S0_date < u["first_trading_date"], u["ticker"]


# ================================================================ kohort dosyası (§1) ve doğrulayıcı

def _rows(cal, members, **kw):
    out = []
    for i, m in enumerate(members, start=1):
        doc = f6.inputs_doc(m["ticker"], m["ftd"], price=m.get("price", "10.5"), price_try=m.get("price_try"))
        out.append(f6.cohort_row(doc, sessions=cal.sessions, vault=m.get("vault", reg.VAULT_OPEN),
                                 market=m.get("market", "YILDIZ"), sale_method=m.get("sale_method", reg.SALE_OFF_EXCHANGE),
                                 kap_id=i))
    return out


def test_validate_cohort_accepts_valid_and_rejects_each_violation(cal):
    good = _rows(cal, [{"ticker": "SYNA", "ftd": "2021-03-01"}, {"ticker": "SYNB", "ftd": "2022-06-01", "vault": "SEALED"}])
    good.append(dict(f6.OOS_ROW))
    H = list(reg.COHORT_COLUMNS)
    assert reg.validate_cohort(H, good) == []
    assert reg.validate_cohort(H[::-1], good) != []
    bad = {
        "status": {"status": "MEMBERX"},
        "vault": {"vault": "LOCKED"},
        "window": {"first_trading_date": "2023-09-22", "year": "2023"},
        "year": {"year": "2020"},
        "source": {"listing_source_id": "BIST_1"},
        "reason": {"reason": "neden"},
        "tags": {"regime_tags": "MARKET=YILDIZ"},
        "tag_unknown": {"regime_tags": good[0]["regime_tags"] + "|FOO"},
        "market": {"market": "GIP", "regime_tags": good[0]["regime_tags"]},
        "added_at": {"added_at": "2026-09-24"},
    }
    for name, change in bad.items():
        rows = [dict(good[0], **change)] + good[1:]
        assert reg.validate_cohort(H, rows), name
    oos = dict(f6.OOS_ROW, vault="OPEN")
    assert reg.validate_cohort(H, good[:2] + [oos])
    exposed = _rows(cal, [{"ticker": "PNLSN", "ftd": "2022-01-10", "vault": "SEALED"}])      # D2: maruz kod kasaya giremez
    assert any("maruz" in p for p in reg.validate_cohort(H, exposed))
    exposed = _rows(cal, [{"ticker": "PNLSN", "ftd": "2022-01-10", "vault": reg.VAULT_EXPOSED_CODEX}])
    assert reg.validate_cohort(H, exposed) == []
    fake = _rows(cal, [{"ticker": "SYNC", "ftd": "2022-01-10", "vault": reg.VAULT_EXPOSED_ARCHIVE}])
    assert reg.validate_cohort(H, fake)                                      # listede olmayan kod maruz yazılamaz


def test_cancelled_rule_and_single_active_row(cal):
    H = list(reg.COHORT_COLUMNS)
    a = _rows(cal, [{"ticker": "SYNA", "ftd": "2021-03-01"}])[0]
    assert reg.validate_cohort(H, [a, dict(a)])                             # ikinci etkin satır
    cancel = dict(a, status=reg.COHORT_CANCELLED, reason="yanlış pazar")
    fixed = dict(a, market="ANA", regime_tags=a["regime_tags"].replace("MARKET=YILDIZ", "MARKET=ANA"))
    assert reg.validate_cohort(H, [a, cancel, fixed]) == []
    assert reg.active_cohort([a, cancel, fixed])["SYNA"]["market"] == "ANA"
    assert reg.validate_cohort(H, [cancel])                                 # düşecek etkin satır yok
    assert reg.validate_cohort(H, [a, dict(cancel, reason="")])             # nedensiz iptal


def test_append_cohort_is_append_only(tmp_path, cal):
    p = tmp_path / "cohort.csv"
    rows = _rows(cal, [{"ticker": "SYNA", "ftd": "2021-03-01"}, {"ticker": "SYNB", "ftd": "2021-04-01"}])
    reg.append_cohort(rows[:1], p)
    first = p.read_bytes()
    reg.append_cohort(rows[1:], p)
    assert p.read_bytes().startswith(first) and reg.cohort_append_only_problems(first, p.read_bytes()) == []
    before = p.read_bytes()
    with pytest.raises(reg.RegistryError):
        reg.append_cohort([dict(rows[0])], p)                               # aynı arz ikinci kez (iptalsiz)
    assert p.read_bytes() == before
    assert reg.cohort_append_only_problems(before, before.replace(b"SYNA", b"SYNX"))


# ================================================================ kasa çekilişi (KARARLAR D2)

def _synthetic_members(n_by_year):
    out = []
    for year, n in n_by_year.items():
        for i in range(n):
            out.append({"ticker": f"S{year % 100}{i:02d}", "first_trading_date": f"{year}-{1 + i % 12:02d}-{1 + i % 27:02d}",
                        "status": "MEMBER"})
    return out


def test_vault_draw_is_deterministic_stratified_and_exposed_stay_open():
    members = _synthetic_members({2020: 8, 2021: 11, 2022: 7}) + [
        {"ticker": "TARKM", "first_trading_date": "2022-03-03"}, {"ticker": "PNLSN", "first_trading_date": "2022-01-01"}]
    a = reg.draw_vault(members)
    assert a == reg.draw_vault(list(reversed(members)))                     # girdi sırası etkisiz (sıralama kuralı)
    assert a["TARKM"] == reg.VAULT_EXPOSED_ARCHIVE and a["PNLSN"] == reg.VAULT_EXPOSED_CODEX
    for year, n in ((2020, 8), (2021, 11), (2022, 7)):
        got = [a[m["ticker"]] for m in members if m["first_trading_date"].startswith(str(year)) and m["ticker"] not in
               reg.EXPOSED_TICKERS]
        assert got.count(reg.VAULT_SEALED) == n // 2 and got.count(reg.VAULT_OPEN) == n - n // 2
    assert reg.draw_vault(members, seed=reg.VAULT_SEED + 1) != a
    # algoritma kilidi (sonuçtan bağımsız sentetik girdi): PCG64(20260924), yıl sırası, tabaka içi (tarih, ticker) sırası
    sealed = sorted(t for t, v in a.items() if v == reg.VAULT_SEALED)
    assert sha256_bytes(",".join(sealed).encode()) == SYNTHETIC_SEALED_SHA


SYNTHETIC_SEALED_SHA = "c944e4281ee8c91bef254851c4d9108af2355d487caa12df770cb33f283f4ba6"


def test_vault_draw_on_universe_counts():
    """Evren listesi (S0 eki) üzerinde yıl × küme sayıları (kod adı yok): %50 aşağı yuvarlama, maruz 5 kod açık kümede."""
    members = [u for u in UNIVERSE if u["status"] == "MEMBER"]
    v = reg.draw_vault(members)
    counts = {}
    for u in members:
        counts.setdefault(u["year"], {}).setdefault(v[u["ticker"]], 0)
        counts[u["year"]][v[u["ticker"]]] += 1
    assert counts == {"2020": {"OPEN": 4, "SEALED": 4}, "2021": {"OPEN": 26, "SEALED": 26},
                      "2022": {"OPEN": 19, "SEALED": 18, "EXPOSED_CODEX": 1},
                      "2023": {"OPEN": 17, "SEALED": 16, "EXPOSED_ARCHIVE": 4}}
    assert {t for t in v if v[t].startswith("EXPOSED")} == set(reg.EXPOSED_TICKERS)


def test_exposed_archive_set_equals_members_whose_calendar_d10_is_in_archive(cal):
    """Şartname §7: EXPOSED_ARCHIVE = takvim D_10'u ≥ 2023-09-22 olan üyeler (arşivdeki ilk bülten); KARARLAR D2 listesiyle aynı."""
    got = {u["ticker"] for u in UNIVERSE if u["status"] == "MEMBER"
           and reg.calendar_window(u["first_trading_date"], cal.sessions)[-1] >= reg.EXPOSED_ARCHIVE_FIRST_BULLETIN}
    assert got == {t for t, v in reg.EXPOSED_TICKERS.items() if v == reg.VAULT_EXPOSED_ARCHIVE}


# ================================================================ rejim etiketleri (§7)

def test_limit_path_with_json_table_equals_frozen_predict_path():
    rng = random.Random(20260924)
    for _ in range(2000):
        p = Decimal(rng.randint(1, 400000)) / Decimal(100)
        lp = pth.limit_path(p)
        assert reg.limit_path_with(p, pth.TICK_TABLE) == (lp["snapped_ipo_price"], tuple(lp["C"])), p


def test_tick_table_mismatch_only_where_path_reaches_250():
    """T2015 (dört kademe) ile JSON tablosu yalnız ≥ 250 TL seviyesinde ayrışır (FEASIBILITY §4-3)."""
    assert not reg.tick_table_mismatch("30", "T2015") and not reg.tick_table_mismatch("96.38", "T2015")
    assert reg.tick_table_mismatch("107.5", "T2015") and reg.tick_table_mismatch("300", "T2015")
    assert not reg.tick_table_mismatch("300", "T2023")
    snapped, C = reg.limit_path_with("107.5", reg.TICK_TABLE_T2015)
    assert C[-1] > 250 and all(c % Decimal("0.10") == 0 for c in C if c >= 100)
    assert reg.tick_table_epoch("2023-11-05") == "T2015" and reg.tick_table_epoch("2023-11-06") == "T2023"


def test_regime_tags_follow_rule_dates(cal):
    def tags(ftd, **kw):
        base = dict(first_trading_date=ftd, market="YILDIZ", sale_method=reg.SALE_OFF_EXCHANGE, ipo_price_tl="10",
                    ipo_price_try="10", bookbuilding_start=f6.iso(ftd, -9), sessions=cal.sessions, vault="OPEN")
        return reg.compute_regime_tags(**{**base, **kw})

    t = tags("2020-02-06")
    assert t["MARGIN_RULE"] == "PRE_20200313" and t["MARGIN_NOT_10PCT"] and "SHORT_SELL_BAN_2020_END_NOT_FOUND" not in t
    assert "MARGIN_NOT_10PCT" not in tags("2020-02-06", market="ALT")
    assert tags("2020-03-13")["MARGIN_RULE"] == "POST_20200313" and "MARGIN_NOT_10PCT" not in tags("2020-03-13")
    assert tags("2020-02-24")["SHORT_SELL_BAN_2020_END_NOT_FOUND"]          # pencere 2020-03-02'yi kesiyor
    assert tags("2023-02-01")["SHORT_SELL_BAN"] and "SHORT_SELL_BAN" not in tags("2023-01-10")
    assert tags("2021-11-19", bookbuilding_start="2021-11-10")["ALLOC_REGIME"] == "PRE_20211111"
    assert tags("2021-11-19", bookbuilding_start="2021-11-11")["ALLOC_REGIME"] == "THRESH100_20211111"
    assert tags("2023-04-10", bookbuilding_start="2023-03-30")["ALLOC_REGIME"] == "EQUAL_DIST_20230330"
    assert tags("2021-05-03", sale_method=reg.SALE_ON_EXCHANGE)["SALE_ON_EXCHANGE"]
    assert tags("2021-05-03", ipo_price_try="8.50-9.90")["PRICE_RANGE_BOOKBUILD"]
    assert tags("2021-05-03", ipo_price_tl="107.5", ipo_price_try="8.50-9.90")["TICK_TABLE_MISMATCH"]
    assert tags("2021-05-03", vault=reg.VAULT_EXPOSED_CODEX)[reg.VAULT_EXPOSED_CODEX]
    text = reg.format_regime_tags(t)
    assert reg.parse_regime_tags(text) == t
    for broken in (text + "|FOO", text.replace("MARKET=YILDIZ", "MARKET=NASDAQ"), "|".join(reversed(text.split("|")))):
        with pytest.raises(reg.RegistryError):
            reg.parse_regime_tags(broken)


def test_regime_not_applicable_models():
    na = reg.regime_not_applicable({"MARGIN_NOT_10PCT": True, "MARGIN_RULE": "PRE_20200313"})
    assert set(na) == set(reg.MARGIN_MODELS) and {v["code"] for v in na.values()} == {"MARGIN_NOT_10PCT"}
    na = reg.regime_not_applicable({"TICK_TABLE_MISMATCH": True, "TICK_TABLE_EPOCH": "T2015"})
    assert set(na) == {"ceiling_path_v0", "pb_ceiling_path_v0"} and {v["code"] for v in na.values()} == {"TICK_TABLE_MISMATCH"}
    assert reg.regime_not_applicable({"MARKET": "YILDIZ"}) == {}
    assert set(reg.MARGIN_MODELS) | set(reg.PATH_MODELS) <= set(INDEX_IDS)


# ================================================================ freeze --oot (§5; geçici depo)

MEMBERS = [{"ticker": "SYNA", "ftd": "2021-03-01"}, {"ticker": "SYNB", "ftd": "2021-03-08", "vault": "SEALED"},
           {"ticker": "SYNM", "ftd": "2020-02-06", "market": "ANA", "sale_method": reg.SALE_ON_EXCHANGE, "f3": None},
           {"ticker": "SYNT", "ftd": "2021-03-15", "price": "107.5", "price_try": "8.50-9.90"}]


def _s1_repo(tmp_path, cal, members=MEMBERS, with_models=False):
    root = f6.init_repo(tmp_path, with_models=with_models)
    rows = f6.write_members(root, members, sessions=cal.sessions)
    f6.commit(root, "S1", "registry/oot")
    return root, rows


def _batch(root, **kw):
    return fz.write_oot_records(root / "registry" / "oot" / "cohort_pre_h99.csv", now=NOW,
                                records_dir=root / "registry" / "oot" / "records", root=root, **kw)


def test_oot_batch_one_record_per_member_with_every_model(tmp_path, cal):
    root, rows = _s1_repo(tmp_path, cal)
    out = _batch(root)
    assert len(out["written"]) == 4 and out["skipped"] == [] and out["duplicates"] == []
    assert out["cohort_file_sha256"] == sha256_file(root / "registry" / "oot" / "cohort_pre_h99.csv")
    for p in map(Path, out["written"]):
        rec = json.loads(p.read_text(encoding="utf-8"))
        assert p.parent.name == rec["ticker"] and p.parent.parent == root / "registry" / "oot" / "records"
        assert p.name == fz.record_filename(p.read_bytes(), rec["recorded_at_utc"])       # içerik adresli, yeniden yazılmaz
        assert rec["schema_version"] == "borsai.oot_record/1" and rec["record_stage"] == "OOT_PRE_LISTING"
        assert rec["scale"] == "OOT_PRE_H99" and rec["record_type"] == "PREDICTION"
        assert [c["model_id"] for c in rec["models"]] == INDEX_IDS == rec["models_index"]["model_ids"]
        assert rec["models_index"]["sha256"] == sha256_file(ROOT / "models" / "INDEX.json")
        for c in rec["models"]:
            assert c["params_sha256"] == sha256_file(ROOT / c["file"])
            assert c["status"] in ("PREDICTED", "REFUSED", "NOT_APPLICABLE_REGIME")
        row = next(r for r in rows if r["ticker"] == rec["ticker"])
        assert rec["cohort_row"] == row and rec["vault"] == row["vault"]
        assert rec["regime_tags"] == reg.parse_regime_tags(row["regime_tags"])
        inp = root / "registry" / "oot" / "inputs" / f"{rec['ticker']}.json"
        assert rec["inputs_sha256"] == sha256_file(inp) == rec["inputs"]["sha256"]
        assert rec["market20"]["ref_date"] == row["first_trading_date"] and rec["market20"]["calendar"] == "C"
        assert rec["market20"]["calendar_sha256"] == m20.CALENDAR_C_SHA256
        assert set(rec["comparators"]) == set(fz.OOT_COMPARATOR_RULES)
        for rid, c in rec["comparators"].items():
            assert c["comparator_note"] == ("FROZEN_H99_LAST10_NOT_CHRONOLOGICAL" if rid in ("base_last10_rate", "base_km_last10")
                                            else "FROZEN_H99")
            cell = next(x for x in rec["models"] if x["model_id"] == rid)
            assert c["output"] == cell["output"] and c["params_sha256"] == cell["params_sha256"]
        assert not set(reg.json_keys(rec)) & reg.OOT_OUTCOME_KEYS
        assert not any(w in json.dumps(rec["summary"]) for w in CLASS_WORDS)
        assert rec["code"]["borsai_source_sha256"] and "git_head" in rec["code"]


def test_oot_regime_cells_and_refusals(tmp_path, cal):
    root, _ = _s1_repo(tmp_path, cal)
    recs = {json.loads(Path(p).read_text(encoding="utf-8"))["ticker"]: json.loads(Path(p).read_text(encoding="utf-8"))
            for p in _batch(root)["written"]}
    cells = lambda t: {c["model_id"]: c for c in recs[t]["models"]}  # noqa: E731
    m = cells("SYNM")                                                        # 2020-02-06: marj %20, f3 yok
    for mid in reg.MARGIN_MODELS:
        assert m[mid]["status"] == "NOT_APPLICABLE_REGIME" and m[mid]["not_applicable"]["code"] == "MARGIN_NOT_10PCT"
        assert m[mid]["model_status"] in ("PREDICTED", "REFUSED")
    assert m["v1_5_h99"]["status"] == "REFUSED" and m["v1_5_h99"]["refusal"]["code"] == "F3_MISSING"
    assert recs["SYNM"]["comparators"]["base_always_ceiling"]["status"] == "NOT_APPLICABLE_REGIME"
    t = cells("SYNT")                                                        # 107.5 TL: T2015 ≠ JSON; PB fiyat aralığı
    for mid in reg.PATH_MODELS:
        assert t[mid]["status"] == "NOT_APPLICABLE_REGIME" and t[mid]["not_applicable"]["code"] == "TICK_TABLE_MISMATCH"
    assert t["pb_v0"]["status"] == "REFUSED" and t["pb_v0"]["refusal"]["code"] == "PB_PRICE_RANGE"
    assert all(c["status"] == "PREDICTED" for c in cells("SYNA").values())


def test_oot_batch_requires_committed_clean_tree_and_is_all_or_nothing(tmp_path, cal):
    root, _ = _s1_repo(tmp_path, cal)
    cohort = root / "registry" / "oot" / "cohort_pre_h99.csv"
    cohort.write_bytes(cohort.read_bytes() + b"")
    (root / "registry" / "oot" / "inputs" / "SYNX.json").write_text("{}", encoding="utf-8")     # izlenmeyen dosya
    with pytest.raises(fz.OotPreconditionError):
        _batch(root)
    (root / "registry" / "oot" / "inputs" / "SYNX.json").unlink()
    doc = json.loads((root / "registry" / "oot" / "inputs" / "SYNA.json").read_text(encoding="utf-8"))
    doc["fields"]["ipo_price_tl"]["value"] = "10.6"                         # commit'lenmemiş değişiklik
    (root / "registry" / "oot" / "inputs" / "SYNA.json").write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(fz.OotPreconditionError):
        _batch(root)
    # yayını ilk işlem gününden sonra olan kaynak: hiçbir kayıt yazılmaz
    root2, _ = _s1_repo(tmp_path / "b", cal, members=MEMBERS[:1] + [{"ticker": "SYNP", "ftd": "2021-03-22",
                                                                    "published": "2021-03-23T10:00:00+03:00"}])
    with pytest.raises(fz.FreezeError):
        _batch(root2)
    assert not (root2 / "registry" / "oot" / "records").exists()


def test_oot_batch_skips_duplicates_and_members_without_inputs(tmp_path, cal):
    root, _ = _s1_repo(tmp_path, cal)
    first = _batch(root)
    f6.commit(root, "S2", "registry/oot/records")
    again = _batch(root)
    assert again["written"] == [] and sorted(again["duplicates"]) == sorted(m["ticker"] for m in MEMBERS)
    root2 = f6.init_repo(tmp_path / "c")
    f6.write_members(root2, MEMBERS[:2], sessions=cal.sessions)
    (root2 / "registry" / "oot" / "inputs" / "SYNB.json").unlink()
    f6.commit(root2, "S1", "registry/oot")
    out = _batch(root2)
    assert len(out["written"]) == 1 and out["skipped"] == [{"ticker": "SYNB", "status": "SKIPPED",
                                                          "skip_reason": "INPUTS_NOT_AVAILABLE"}]
    assert len(first["written"]) == 4


def test_oot_cancel_record_only_before_outcome(tmp_path, cal):
    root, _ = _s1_repo(tmp_path, cal)
    paths = [Path(p) for p in _batch(root)["written"]]
    target = next(p for p in paths if p.parent.name == "SYNA")
    rd = root / "registry" / "oot" / "records"
    c = fz.cancel_oot_record(target, "sentetik iptal", now=NOW, records_dir=rd, root=root)
    assert json.loads(c.read_text(encoding="utf-8"))["cancels"]["file"] == target.name
    assert fz.active_oot_records("SYNA", rd) == []
    with pytest.raises(fz.FreezeError):
        fz.cancel_oot_record(target, "ikinci", now=NOW, records_dir=rd, root=root)
    other = next(p for p in paths if p.parent.name == "SYNB")
    (root / "data" / "outcomes_oot").mkdir(parents=True)
    (root / "data" / "outcomes_oot" / "SYNB.csv").write_text("h\n", encoding="utf-8")
    with pytest.raises(fz.FreezeError, match="iptal yapılamaz"):
        fz.cancel_oot_record(other, "sonuçtan sonra", now=NOW, records_dir=rd, root=root)


def test_freeze_cli_oot_calls_batch_writer(monkeypatch, tmp_path):
    seen = {}
    monkeypatch.setattr(fz, "write_oot_records", lambda p: seen.setdefault("p", p) and {"written": []})
    assert fz.main(["--oot", str(tmp_path / "c.csv")]) == 0 and seen["p"] == tmp_path / "c.csv"
    monkeypatch.setattr(fz, "write_oot_post_d1_record", lambda t: seen.setdefault("t", t))
    assert fz.main(["--oot-post-d1", "SYNA"]) == 0 and seen["t"] == "SYNA"


def test_oot_modules_are_stdlib_only():
    import subprocess
    import sys

    code = ("import sys, borsai.freeze, borsai.registry, borsai.outcomes_oot; "
            "print(sorted(m for m in ('numpy', 'sklearn', 'scipy') if m in sys.modules))")
    assert subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True, capture_output=True,
                          text=True).stdout.strip() == "[]"


# ================================================================ karantina, kapı, ayıklama (KARARLAR D6; sentetik zip'ler)

def test_quarantine_dir_is_outside_repo_and_configurable(tmp_path, monkeypatch):
    assert oo.quarantine_dir(tmp_path / "q") == (tmp_path / "q").resolve()
    monkeypatch.setenv(oo.QUARANTINE_ENV, str(tmp_path / "env_q"))
    assert oo.quarantine_dir() == (tmp_path / "env_q").resolve()
    monkeypatch.delenv(oo.QUARANTINE_ENV)
    assert oo.quarantine_dir() == oo.DEFAULT_QUARANTINE.resolve()
    for inside in (ROOT, ROOT / "data" / "q"):
        with pytest.raises(oo.QuarantineError):
            oo.quarantine_dir(inside)


def _pipeline_repo(tmp_path, cal, members, *, proofs=True):
    """S1 + S2 commit'li geçici depo (modeller dahil); proofs=True ise model, S1 ve S2 commit'lerine push kanıtı."""
    root = f6.init_repo(tmp_path, with_models=True)
    c_models = f6.git(root, "rev-parse", "HEAD")
    f6.write_members(root, members, sessions=cal.sessions)
    c_s1 = f6.commit(root, "S1", "registry/oot")
    _batch(root)
    c_s2 = f6.commit(root, "S2", "registry/oot/records")
    if proofs:
        f6.make_proof(root, c_models, "2026-09-25T10:00:00Z")
        f6.make_proof(root, c_s1, "2026-09-25T10:05:00Z")
        f6.make_proof(root, c_s2, "2026-09-25T10:10:00Z")
    return root


def _paths_for(cal, members):
    """Her üye: D1 ve D2 tavan, D3'te kırılma; sonra düz. Kapanışlar üye başına farklı."""
    out = {}
    for i, m in enumerate(members):
        start = m.get("appear", m["ftd"])
        k = Decimal(i) / 100
        closes = ["11.55", "12.70", f"{Decimal('12.00') + k}"] + [f"{Decimal('12.10') + k}"] * 9
        uppers = ["11.55", "12.70", "13.97"] + ["13.30"] * 9
        out[m["ticker"]] = f6.ceiling_path(cal.sessions, start, closes, uppers)
    return out


def _window(cal, start, n=16):
    return [s for s in cal.sessions if s >= start][:n]


def test_download_gate_requires_committed_and_pushed_s2_records(tmp_path, cal):
    members = MEMBERS[:2]
    root = _pipeline_repo(tmp_path, cal, members, proofs=False)
    with pytest.raises(oo.GateError, match="push kanıtı yok"):
        oo.download_gate(root=root)
    f6.make_proof(root, f6.git(root, "rev-parse", "HEAD"), "2026-09-25T10:10:00Z")
    oo.download_gate(root=root)
    rec = next((root / "registry" / "oot" / "records" / "SYNA").glob("*.json"))
    rec.unlink()                                                             # bir üyenin kaydı eksik -> kapalı
    with pytest.raises(oo.GateError):
        oo.download_gate(root=root)
    root2 = f6.init_repo(tmp_path / "b", with_models=True)
    f6.write_members(root2, members, sessions=cal.sessions)
    f6.commit(root2, "S1", "registry/oot")
    _batch(root2)                                                            # kayıtlar commit'lenmemiş
    with pytest.raises(oo.GateError):
        oo.download_gate(root=root2)
    fake = f6.FakeDownloader({})
    with pytest.raises(oo.GateError):
        oo.extract_open_members(root=root2, qdir=tmp_path / "q", downloader=fake, prober=lambda u: False, calendar=cal)
    assert fake.calls == [] and not (tmp_path / "q").exists()                # kapı kapalıyken hiçbir indirme yok


def test_extractor_reads_only_open_codes_and_never_opens_sealed(tmp_path, cal):
    members = [{"ticker": "SYNA", "ftd": "2021-03-01"}, {"ticker": "SYNB", "ftd": "2021-03-03", "vault": "SEALED"}]
    root = _pipeline_repo(tmp_path, cal, members)
    files = f6.market(_window(cal, "2021-02-26", 20), _paths_for(cal, members))
    fake = f6.FakeDownloader(files)
    out = oo.extract_open_members(root=root, qdir=tmp_path / "q", downloader=fake, prober=lambda u: False, calendar=cal)
    assert set(out["extracted"]) == {"SYNA"} and out["sealed_not_opened"] == 1
    written = [p for p in (root / "data").rglob("*") if p.is_file()]
    assert {p.relative_to(root).as_posix() for p in written} == {
        "data/outcomes_oot/SYNA.csv", "data/outcomes_oot/raw/SYNA.json", "data/raw/bist/MANIFEST_OOT.csv"}
    for p in written:
        text = p.read_text(encoding="utf-8")
        assert "SYNB" not in text and f6.FILLER.split(".")[0] not in text, p   # kasadaki ve başka kodların satırı yok
    vault = {"SYNA": "OPEN", "SYNB": "SEALED"}
    calls = []
    with pytest.raises(oo.SealedAccessError):
        oo.resolve_member("SYNB", "2021-03-03", cal, vault, fetch=lambda s, k: calls.append(s))
    with pytest.raises(oo.SealedAccessError):
        oo.resolve_member("SYNX", "2021-03-03", cal, vault, fetch=lambda s, k: calls.append(s))
    with pytest.raises(oo.SealedAccessError):                                # düz küme yetki değil (SPEC_DEVIATIONS M-E (d))
        oo.resolve_member("SYNB", "2021-03-03", cal, vault, unsealed={"SYNB"}, fetch=lambda s, k: calls.append(s))
    assert calls == []                                                       # bülten açılmadan hata
    assert oo.resolve_member("SYNB", "2021-03-03", cal, vault, unsealed=oo.VaultUnsealed({"SYNB"}, oo.UNSEALED_BY_OPEN_VAULT),
                             fetch=lambda s, k: (files[oc.source_url(s, k)], None)).resolution.d1 == "2021-03-03"


def test_extracted_rows_equal_outcomes_definitions(tmp_path, cal):
    """Ayıklanan satırlar outcomes.outcome_rows'un tam bülten üzerindeki çıktısıyla aynı (+ outcome_basis); D_1 kuralı: KAP
    tarihinden önceki görünüş ve işlemsiz ilk gün sayılmaz."""
    sessions = _window(cal, "2021-02-24", 20)
    paths = {"SYNA": f6.ceiling_path(cal.sessions, "2021-02-26", ["10.10", "10.20"])}          # KAP tarihinden önce görünüş
    paths["SYNA"].update(f6.ceiling_path(cal.sessions, "2021-03-01", ["11.55"] * 1))
    paths["SYNA"]["2021-03-01"] = ("11.55", "0", "11.55")                                      # ilk gün işlemsiz
    paths["SYNA"].update({s: ("11.55", "10", "11.55") for s in sessions if "2021-03-02" <= s <= "2021-03-19"})
    files = f6.market(sessions, paths)
    fetch = lambda s, k: (files[oc.source_url(s, k)], oo.Pin(s, k, oc.source_url(s, k), sha256_bytes(files[oc.source_url(s, k)]),  # noqa: E731
                                                             len(files[oc.source_url(s, k)]), "", "t", oc.internal_name(s, k)))
    ext = oo.resolve_member("SYNA", "2021-03-01", cal, {"SYNA": "OPEN"}, fetch=fetch)
    assert ext.resolution.first_appearance == "2021-03-01" and ext.resolution.d1 == "2021-03-02"
    rows = oo.outcome_rows_oot(ext, "10.5", cal)
    full_thb = {s: oc.parse_bulletin(files[oc.source_url(s, "thb")], s, "thb") for s in sessions}
    full_thm = {s: oc.parse_bulletin(files[oc.source_url(s, "thm")], s, "thm") for s in sessions}
    ref = oc.outcome_rows("SYNA", "10.5", cal, full_thb, full_thm, start="2021-03-01")
    assert [{k: v for k, v in r.items() if k != "outcome_basis"} for r in rows] == ref
    assert {r["outcome_basis"] for r in rows} == {"MACHINE_EXTRACTED"} and tuple(rows[0]) == oo.OOT_OUTCOME_COLUMNS
    assert all(r["status"] == "OK" for r in rows) and rows[0]["session_date"] == "2021-03-02"
    raw = oo.raw_copies(ext)
    assert raw["code"] == "SYNA.E" and "ZZZZ" not in json.dumps(raw)


def test_manifest_oot_pins_and_source_change(tmp_path):
    p = tmp_path / "MANIFEST_OOT.csv"
    pin = oo.Pin("2021-03-01", "thb", oc.source_url("2021-03-01", "thb"), "a" * 64, 10, "LM", "t", "x.csv")
    assert oo.append_manifest_oot([pin, pin], p) == 1 and oo.append_manifest_oot([pin], p) == 0
    assert tuple(oo.read_manifest_oot(p)[0]) == oo.MANIFEST_OOT_COLUMNS
    with pytest.raises(oc.SourceChanged):
        oo.append_manifest_oot([oo.Pin(**{**pin.__dict__, "sha256": "b" * 64})], p)


def test_xu100_gap_closure_probe(cal):
    urls = []
    assert oo.check_xu100_gap_closures(lambda u: urls.append(u) or False) == list(m20.XU100_GAP_CLOSURES)
    assert urls == [oc.source_url(d, "thb") for d in m20.XU100_GAP_CLOSURES]
    with pytest.raises(oo.CalendarConflict):
        oo.check_xu100_gap_closures(lambda u: u.endswith(f"thb{'2023' + '0424'}1.zip"))


def test_open_vault_skeleton(tmp_path, cal):
    root = _pipeline_repo(tmp_path, cal, MEMBERS[:2])
    with pytest.raises(oo.GateError):
        oo.open_vault(feature_spec="docs/specs_faz7/SPEC_X.md", root=root)
    (root / "docs" / "specs_faz7").mkdir(parents=True)
    (root / "docs" / "specs_faz7" / "SPEC_X.md").write_text("özellik\n", encoding="utf-8")
    c = f6.commit(root, "spec", "docs")
    f6.make_proof(root, c, "2026-09-26T10:00:00Z")
    man = root / "data" / "raw" / "bist" / "MANIFEST_OOT.csv"
    data = f6.make_zip("2021-03-01", "thb", [f6.thb_row("SYNA.E", "1")])
    oo.append_manifest_oot([oo.Pin("2021-03-01", "thb", oc.source_url("2021-03-01", "thb"), sha256_bytes(data), len(data),
                                   "", "t", "x")], man)
    assert oo.open_vault(feature_spec="docs/specs_faz7/SPEC_X.md", root=root, qdir=tmp_path / "q",
                         downloader=f6.FakeDownloader({oc.source_url("2021-03-01", "thb"): data})) == {"SYNB"}
    with pytest.raises(oc.SourceChanged):
        oo.open_vault(feature_spec="docs/specs_faz7/SPEC_X.md", root=root, qdir=tmp_path / "q",
                      downloader=f6.FakeDownloader({oc.source_url("2021-03-01", "thb"): data + b"x"}))


# ================================================================ S3: D_1 satırı ve eski kohort POST_D1 kaydı

def test_d1_rows_and_oot_post_d1_record(tmp_path, cal):
    members = [{"ticker": "SYNA", "ftd": "2021-03-01"}, {"ticker": "SYNB", "ftd": "2021-03-03", "vault": "SEALED"}]
    root = _pipeline_repo(tmp_path, cal, members)
    files = f6.market(_window(cal, "2021-02-26", 20), _paths_for(cal, members))
    fake = f6.FakeDownloader(files)
    out = oo.extract_d1_rows(root=root, qdir=tmp_path / "q", downloader=fake, prober=lambda u: False, calendar=cal)
    assert out["written"] == ["SYNA"]
    assert all("20210301" in u for u in fake.calls if "thb" in u) and len(fake.calls) == 2   # yalnız D_1'e kadar
    doc = json.loads((root / "registry" / "oot" / "d1_rows" / "SYNA.json").read_text(encoding="utf-8"))
    manifest = oo.read_manifest_oot(root / "data" / "raw" / "bist" / "MANIFEST_OOT.csv")
    assert oo.d1_rows_problems(doc, manifest) == [] and doc["d1"]["session_date"] == "2021-03-01"
    assert doc["exposure_class"] == "MACHINE_SEQUENCED" and doc["d1"]["ceiling_close_D1"] == 1
    assert not (root / "registry" / "oot" / "d1_rows" / "SYNB.json").exists()
    bad = json.loads(json.dumps(doc))
    bad["d1"]["ceiling_close_D2"] = 1
    assert oo.d1_rows_problems(bad, manifest)
    rec = fz.build_oot_post_d1_record("SYNA", doc, now=NOW, records_dir=root / "registry" / "oot" / "records", root=root)
    assert rec["exposure_class"] == "MACHINE_SEQUENCED" and rec["record_stage"] == "OOT_POST_D1"
    assert rec["models_index"]["model_ids"] == ["post_d1_hazard_v0"] and rec["models"][0]["status"] == "PREDICTED"
    assert rec["base_record"]["file"].startswith("registry/oot/records/SYNA/")
    assert reg.post_d1_record_problems(rec, {(r["date"], r["kind"]): r for r in manifest}) == []
    p = fz.write_oot_post_d1_record("SYNA", now=NOW, post_dir=tmp_path / "post", d1_rows_dir=root / "registry" / "oot" / "d1_rows",
                                    records_dir=root / "registry" / "oot" / "records", root=root)
    assert p.parent.name == "SYNA"
    with pytest.raises(fz.DuplicateRecord):
        fz.write_oot_post_d1_record("SYNA", now=NOW, post_dir=tmp_path / "post", d1_rows_dir=root / "registry" / "oot" / "d1_rows",
                                    records_dir=root / "registry" / "oot" / "records", root=root)


# ================================================================ üçüncü terazi (§3), class_oot (§2), sentetik skor (§6)

def test_scale_mixing_with_oot_is_rejected():
    mk = lambda scale, j=None: [sc.PairedObs(scale, f"T{i}", "2021-03", 0.1, 0.2, "x", j) for i in range(12)]  # noqa: E731
    oot = mk(sc.SCALE_OOT)
    assert sc.paired_metric(oot)["scale"] == "OOT_PRE_H99"
    for other in (mk(sc.SCALE_BACKTEST), mk(sc.SCALE_LIVE), mk(sc.SCALE_LIVE_POST_D1, 1), mk(sc.SCALE_OOT_POST_D1, 1),
                  mk(sc.SCALE_LIVE_CONDITIONAL, 1)):
        with pytest.raises(sc.ScaleMixError):
            sc.paired_metric(oot + other)
        with pytest.raises(sc.ScaleMixError):
            sc.merge_scales({"scale": sc.SCALE_OOT}, {"scale": other[0].scale})
    with pytest.raises(sc.ScaleMixError):
        sc.merge_scales({"scale": sc.SCALE_OOT}, {"scale": sc.SCALE_OOT})


SCORE_MEMBERS = [{"ticker": f"SYN{chr(65 + i)}", "ftd": d} for i, d in enumerate(
    ["2021-03-01", "2021-03-08", "2021-03-15", "2021-03-22", "2021-03-29", "2021-04-05", "2021-04-12", "2021-04-19",
     "2021-04-26", "2021-05-03", "2021-05-10", "2021-05-17"])] + [{"ticker": "SYNZ", "ftd": "2021-03-02", "vault": "SEALED"}]


@pytest.fixture(scope="module")
def scored_repo(tmp_path_factory, cal):
    tmp = tmp_path_factory.mktemp("oot_scores")
    root = _pipeline_repo(tmp, cal, SCORE_MEMBERS)
    files = f6.market(_window(cal, "2021-02-26", 80), _paths_for(cal, SCORE_MEMBERS))
    before = sc.build_oot_scores(root=root, now=NOW)                         # sonuç commit edilmeden
    oo.extract_open_members(root=root, qdir=tmp / "q", downloader=f6.FakeDownloader(files), prober=lambda u: False,
                            calendar=cal)
    uncommitted = sc.build_oot_scores(root=root, now=NOW)
    c_s5 = f6.commit(root, "S5", "data")
    return {"root": root, "before": before, "uncommitted": uncommitted, "c_s5": c_s5, "tmp": tmp}


def test_class_oot_requires_dag_order_and_proof_order(scored_repo):
    root = scored_repo["root"]
    for s in (scored_repo["before"], scored_repo["uncommitted"]):          # kanıtlı sonuç commit'i yok -> OOT_RETRO
        v15 = next(m for m in s["oot_pre_h99"]["models"] if m["model_id"] == "v1_5_h99")
        assert v15["rows"] == [] and v15["n_oot_retro"] == 12
    ctx = sc.OotContext(root)
    ingest = sc.oot_ingest_commit(ctx.git, "SYNA", [])
    assert ingest == scored_repo["c_s5"]
    klass, ev = sc.class_oot(ctx, "v1_5_h99", "SYNA", ingest)
    assert klass == "OOT_RETRO" and ev["record_before_ingest"] and not ev["record_proof_before_ingest_proof"]
    f6.make_proof(root, scored_repo["c_s5"], "2026-09-25T10:20:00Z")
    ctx = sc.OotContext(root)
    klass, ev = sc.class_oot(ctx, "v1_5_h99", "SYNA", ingest)
    assert klass == "OOT_BLIND" and ev["cohort_gate_ok"] and ev["model_frozen_before_ingest"]
    f6.make_proof(root, scored_repo["c_s5"], "2026-09-25T10:09:00Z")      # sonuç kanıtı kayıt kanıtından önce -> RETRO
    assert sc.class_oot(sc.OotContext(root), "v1_5_h99", "SYNA", ingest)[0] == "OOT_RETRO"
    f6.make_proof(root, scored_repo["c_s5"], "2026-09-25T10:20:00Z")


def test_class_oot_cohort_gate_and_outcome_before_record(tmp_path, cal):
    """Sonuç, kohortun bir üyesinin S2 kaydından önce girerse (sıra ihlali) bütün arzlar OOT_RETRO. (BORSAI_FAZ7_OOT_RECORDS,
    SPEC_DEVIATIONS L: kapı model başına ve kanıt sırasını da ister; S2a ve sonuç commit'lerinin kendi kanıtları senaryoya eklendi ki
    eksik üye yalnız ata terimiyle düşen SYNB olsun.)"""
    root = f6.init_repo(tmp_path, with_models=True)
    f6.make_proof(root, f6.git(root, "rev-parse", "HEAD"), "2026-09-25T10:00:00Z")
    f6.write_members(root, SCORE_MEMBERS[:2], sessions=cal.sessions)
    f6.commit(root, "S1", "registry/oot")
    _batch(root)
    rec_b = root / "registry" / "oot" / "records" / "SYNB"
    c_s2a = f6.commit(root, "S2a", "registry/oot/records/SYNA")
    (root / "data" / "outcomes_oot").mkdir(parents=True)
    (root / "data" / "outcomes_oot" / "SYNA.csv").write_text(",".join(oo.OOT_OUTCOME_COLUMNS) + "\n", encoding="utf-8")
    c_out = f6.commit(root, "sonuç erken", "data")
    f6.commit(root, "S2b", rec_b.relative_to(root).as_posix())
    head = f6.git(root, "rev-parse", "HEAD")
    f6.make_proof(root, c_s2a, "2026-09-25T10:30:00Z")
    f6.make_proof(root, c_out, "2026-09-25T10:40:00Z")
    f6.make_proof(root, head, "2026-09-25T11:00:00Z")
    ctx = sc.OotContext(root)
    klass, ev = sc.class_oot(ctx, "v1_5_h99", "SYNA", c_out)
    assert klass == "OOT_RETRO" and not ev["cohort_gate_ok"] and ev["cohort_gate_missing_n"] == 1


def test_build_oot_scores_synthetic(scored_repo):
    f6.make_proof(scored_repo["root"], scored_repo["c_s5"], "2026-09-25T10:20:00Z")
    before_scores = (ROOT / "scores" / "scores.json").read_bytes()
    oot_state = lambda: sc.OOT_SCORES_PATH.read_bytes() if sc.OOT_SCORES_PATH.exists() else None  # noqa: E731
    before_oot = oot_state()
    s = sc.build_oot_scores(root=scored_repo["root"], now=NOW)
    assert s["schema_version"] == "borsai.scores_oot/1" and s["scale"] == "OOT_PRE_H99"
    block = s["oot_pre_h99"]
    assert (block["n_member"], block["n_open"], block["n_sealed"], block["n_out_of_scope"]) == (13, 12, 1, 1)
    assert block["n_spk_corporate_action_seen"] is None and block["n_spk_corporate_action_seen_cohort_total"] == 28
    v15 = next(m for m in block["models"] if m["model_id"] == "v1_5_h99")
    assert v15["scale"] == "OOT_PRE_H99" and v15["n_scored"] == 12 and v15["n_oot_retro"] == 0
    assert all(r["class"] == "OOT_BLIND" and r["open"] for r in v15["rows"])
    assert "SYNZ" not in {r["ticker"] for m in block["models"] for r in m["rows"]}
    primary = [c for c in v15["cells"] if c["label"] == "birincil"]
    assert [(c["output"], c["horizon_or_k"], c["metric"], c["rule_id"]) for c in primary] == [("return", "D5", "MAE",
                                                                                              "base_train_median")]
    assert primary[0]["scale"] == "OOT_PRE_H99" and primary[0]["n"] == 12
    assert [r["subset"] for r in v15["by_year"]] == ["2021"]
    hz = next(m for m in block["models"] if m["model_id"] == "ceiling_hazard_v0")
    assert [(c["metric"], c["rule_id"]) for c in hz["cells"] if c["label"] == "birincil"] == [("RPS", "base_km_expanding")]
    out = sc.write_oot_scores(s, scored_repo["tmp"] / "scores_oot.json")
    assert json.loads(out.read_text(encoding="utf-8"))["oot_pre_h99"]["n_open"] == 12
    assert (ROOT / "scores" / "scores.json").read_bytes() == before_scores
    assert oot_state() == before_oot          # build ve write_oot_scores(yol) gerçek dosyaya yazmaz (S6'dan sonra dosya commit'li)


def test_oot_primary_cells_follow_spec_6():
    assert set(sc.OOT_PRIMARY_CELLS) | {"post_d1_hazard_v0"} == {
        "v1_5_h99", "v1_6_h99", "v1_5_market20_v0", "pb_v0", "ceiling_hazard_v0", "pb_ceiling_v0", "ceiling_path_v0",
        "pb_ceiling_path_v0", "post_d1_hazard_v0"}
    assert sc.OOT_POST_D1_PRIMARY == sc.POST_D1_PRIMARY
    for mid in ("ceiling_hazard_v0", "pb_ceiling_v0"):
        assert sc.OOT_PRIMARY_CELLS[mid]["rule_ids"] == ["base_km_expanding"]


# ================================================================ gerçek kohort (S1 commit'inden sonra)

def test_s1_files_present_after_s1_commit():
    """Sessiz atlama yok: S1 commit'i HEAD geçmişindeyse kohort dosyası ve 135 girdi dosyası vardır."""
    log = f6.git(ROOT, "log", "--format=%s")
    if any(line.startswith("BORSAI_FAZ6_S1") for line in log.splitlines()):
        assert S1_PRESENT and len(list(reg.OOT_INPUTS_DIR.glob("*.json"))) == 135


needs_s1 = pytest.mark.skipif(not S1_PRESENT, reason="S1 (kohort + girdiler) henüz repoda değil")


@needs_s1
def test_real_cohort_validates_and_reproduces_from_code(cal):
    header, rows = reg.read_cohort()
    assert reg.validate_cohort(header, rows) == []
    rebuilt = reg.build_cohort_rows(UNIVERSE, reg.OOT_INPUTS_DIR, cal.sessions, rows[0]["added_at"])
    assert rows[:len(rebuilt)] == rebuilt                                    # S1 satırları: vault ve regime_tags koddan
    assert reg.COHORT_PATH.read_bytes().startswith(reg.cohort_bytes(rebuilt))
    assert len(reg.cohort_members(rows)) == 135 and sum(r["status"] == "OUT_OF_SCOPE" for r in rows) == 1


@pytest.mark.requires_raw_sources
@needs_s1
def test_real_inputs_validate_and_are_byte_equal_imports():
    header, rows = reg.read_cohort()
    members = reg.cohort_members(rows)
    assert sorted(p.stem for p in reg.OOT_INPUTS_DIR.glob("*.json")) == sorted(r["ticker"] for r in members)
    for r in members:
        doc = reg.load_inputs(reg.OOT_INPUTS_DIR / f"{r['ticker']}.json")[0]
        assert reg.validate_inputs(doc) == [], r["ticker"]
        assert reg.inputs_pit_problems(doc, root=ROOT) == [], r["ticker"]
        assert doc["fields"]["first_trading_date"]["value"] == r["first_trading_date"]
        assert "vault" not in doc and "regime_tags" not in doc                # tek kaynak kohort dosyası (I2)
    manifest = ROOT / "docs" / "faz6" / "dogrulama" / "import_sha256.csv"
    for line in csv.DictReader(manifest.open(encoding="utf-8")):
        assert sha256_file(ROOT / line["path"]) == line["sha256"], line["path"]


@needs_s1
def test_real_listing_source_matches_pinned_document():
    header, rows = reg.read_cohort()
    for r in reg.cohort_members(rows):
        man = json.loads((reg.OOT_SOURCE_DOCS_DIR / r["ticker"] / "MANIFEST.json").read_text(encoding="utf-8"))
        docs = {d["source_id"]: d for d in man["documents"]}
        assert docs[r["listing_source_id"]]["sha256"] == r["listing_source_sha256"], r["ticker"]


@pytest.mark.requires_raw_sources
@needs_s1
def test_real_dry_run_builds_every_member_without_writing(cal):
    """S2 yolu gerçek girdilerle bellekte (yazmadan): 135 üye × 19 model; sonuç alanı yok."""
    header, rows = reg.read_cohort()
    sources, im = m20.load_oot_sources(), fz._index_models(fz.MODELS_DIR)
    for r in reg.cohort_members(rows):
        rec = fz.build_oot_record(r, cohort_sha256=sha256_file(reg.COHORT_PATH), inputs_path=reg.OOT_INPUTS_DIR /
                                  f"{r['ticker']}.json", now=NOW, m20_sources=sources, index_models=im)
        assert len(rec["models"]) == 19 + len(fs7.frozen_tail_ids()) and not set(reg.json_keys(rec)) & reg.OOT_OUTCOME_KEYS



def test_oot_post_d1_block_machine_sequenced_rows(tmp_path, cal):
    """S3 → S5 sırası: D_1 satırları ve eski kohort POST_D1 kayıtları commit + kanıt, sonra sonuçlar. POST_D1 alt tablosu ayrı
    ölçekte, satırlar MACHINE_SEQUENCED ve OOT_BLIND; d1_rows dosyası kayıttakiyle aynı değilse OOT_RETRO."""
    members = [{"ticker": "SYNA", "ftd": "2021-03-01"}, {"ticker": "SYNC", "ftd": "2021-03-08"},
               {"ticker": "SYNB", "ftd": "2021-03-03", "vault": "SEALED"}]
    root = _pipeline_repo(tmp_path, cal, members)
    files = f6.market(_window(cal, "2021-02-26", 30), _paths_for(cal, members))
    kw = dict(root=root, qdir=tmp_path / "q", downloader=f6.FakeDownloader(files), prober=lambda u: False, calendar=cal)
    assert oo.extract_d1_rows(**kw)["written"] == ["SYNA", "SYNC"]
    rd, od = root / "registry" / "oot" / "records", root / "registry" / "oot"
    for t in ("SYNA", "SYNC"):
        fz.write_oot_post_d1_record(t, now=NOW, post_dir=od / "post_d1", d1_rows_dir=od / "d1_rows", records_dir=rd, root=root)
    c_s3 = f6.commit(root, "S3", "registry/oot/d1_rows", "registry/oot/post_d1", "data/raw/bist/MANIFEST_OOT.csv")
    f6.make_proof(root, c_s3, "2026-09-25T10:15:00Z")
    oo.extract_open_members(**kw)
    c_s5 = f6.commit(root, "S5", "data")
    f6.make_proof(root, c_s5, "2026-09-25T10:20:00Z")
    s = sc.build_oot_scores(root=root, now=NOW)
    post = s["post_d1"]
    assert post["scale"] == sc.SCALE_OOT_POST_D1 != s["scale"]
    m = post["models"][0]
    assert m["model_id"] == "post_d1_hazard_v0" and m["exposure_class"] == "MACHINE_SEQUENCED"
    assert [(r["ticker"], r["class"], r["status"], r["exposure_class"]) for r in m["rows"]] == [
        ("SYNA", "OOT_BLIND", "SCORED", "MACHINE_SEQUENCED"), ("SYNC", "OOT_BLIND", "SCORED", "MACHINE_SEQUENCED")]
    assert all(r["L"] == 2 for r in m["rows"])
    v15 = next(x for x in s["oot_pre_h99"]["models"] if x["model_id"] == "v1_5_h99")
    assert {r["class"] for r in v15["rows"]} == {"OOT_BLIND"} and v15["n_scored"] == 2
    d1p = od / "d1_rows" / "SYNA.json"
    d1p.write_text(d1p.read_text(encoding="utf-8").replace('"session_h": 1', '"session_h": 1, "note": "x"'), encoding="utf-8")
    m = sc.build_oot_scores(root=root, now=NOW)["post_d1"]["models"][0]
    assert [r["ticker"] for r in m["rows"]] == ["SYNC"] and m["retro_info"][0]["ticker"] == "SYNA"
    assert m["retro_info"][0]["class_evidence"]["extra_ok"] is False


# ================================================================ Fable denetimi bulguları F1, F2, F3, F6 (BORSAI_FAZ6_S2_RECORDS)

def test_download_gate_covers_sealed_members(tmp_path, cal):
    """F1 (a): kapı SEALED üyeleri de kapsar. Açık üyenin kaydı commit'li ve kanıtlı; yalnız kasadaki üyenin kaydı (i) commit'le
    silinmiş, (ii) commit'lenmemiş, (iii) commit'li ama push kanıtsız -> GateError, sorunların hepsi kasadaki üyeye ait."""
    members = MEMBERS[:2]
    assert [m.get("vault", reg.VAULT_OPEN) for m in members] == [reg.VAULT_OPEN, reg.VAULT_SEALED]
    root = _pipeline_repo(tmp_path / "a", cal, members)
    oo.download_gate(root=root)                                              # kontrol: bütün kayıtlar tamam -> açık
    f6.git(root, "rm", "-q", "-r", "--", "registry/oot/records/SYNB")
    f6.make_proof(root, f6.commit(root, "kasadaki üyenin kaydı silindi", "registry/oot/records"), "2026-09-25T10:30:00Z")
    assert oo.s2_gate_problems(root=root) == ["SYNB: S2 kaydı yok"]           # (i)
    with pytest.raises(oo.GateError, match="SYNB"):
        oo.download_gate(root=root)

    root = f6.init_repo(tmp_path / "b", with_models=True)
    c_models = f6.git(root, "rev-parse", "HEAD")
    f6.write_members(root, members, sessions=cal.sessions)
    f6.commit(root, "S1", "registry/oot")
    _batch(root)
    f6.make_proof(root, c_models, "2026-09-25T10:00:00Z")
    f6.make_proof(root, f6.commit(root, "S2 yalnız açık üye", "registry/oot/records/SYNA"), "2026-09-25T10:10:00Z")
    sealed_rec = next((root / "registry" / "oot" / "records" / "SYNB").glob("*.json")).relative_to(root).as_posix()
    problems = oo.s2_gate_problems(root=root)                                # (ii)
    assert f"{sealed_rec}: commit'li değil" in problems and all("SYNB" in p for p in problems)
    with pytest.raises(oo.GateError):
        oo.download_gate(root=root)
    c_sealed = f6.commit(root, "S2 kasadaki üye", "registry/oot/records/SYNB")
    assert oo.s2_gate_problems(root=root) == [f"{sealed_rec}: push kanıtı yok"]   # (iii)
    with pytest.raises(oo.GateError, match="push kanıtı yok"):
        oo.download_gate(root=root)
    f6.make_proof(root, c_sealed, "2026-09-25T10:20:00Z")
    oo.download_gate(root=root)


def test_cohort_gate_covers_sealed_members_and_record_ancestor_term(tmp_path, cal):
    """F1 (b): açık üyenin sonuç commit'i kasadaki üyenin S2 kaydından önce girerse kohort kapısı kapalı ve açık üye OOT_RETRO
    (başka bütün terimler tamam); kasadaki kayıt ata olunca kapı açık. F3: kayıt-atası terimi tek başına (kapı açık, model ve
    kanıt sırası tamam) sınıfı OOT_RETRO yapar. (BORSAI_FAZ7_OOT_RECORDS, SPEC_DEVIATIONS L: kapı model başına ve kasadaki kaydın
    kanıtının da sonuç kanıtından önce olmasını ister; "kapı açık" denetimleri kasadaki kayıttan SONRA gelen ayrı bir commit'le
    (`c_late`, kendi kanıtıyla) yapılır; kasadaki kayıt commit'inin kendisi sonuç sayılınca kanıtlar eşit, kapı kapalı.)"""
    members = [{"ticker": "SYNA", "ftd": "2021-03-01"}, {"ticker": "SYNZ", "ftd": "2021-03-02", "vault": "SEALED"}]
    root = f6.init_repo(tmp_path, with_models=True)
    c_models = f6.git(root, "rev-parse", "HEAD")
    f6.write_members(root, members, sessions=cal.sessions)
    c_s1 = f6.commit(root, "S1", "registry/oot")
    _batch(root)
    c_open = f6.commit(root, "S2 açık üye", "registry/oot/records/SYNA")
    (root / "data" / "outcomes_oot").mkdir(parents=True)
    (root / "data" / "outcomes_oot" / "SYNA.csv").write_text(",".join(oo.OOT_OUTCOME_COLUMNS) + "\n", encoding="utf-8")
    c_out = f6.commit(root, "açık üyenin sonucu, kasadaki kayıttan önce", "data")
    c_sealed = f6.commit(root, "S2 kasadaki üye", "registry/oot/records/SYNZ")
    (root / "docs").mkdir()
    (root / "docs" / "sonra.txt").write_text("kasadaki kayıttan sonra\n", encoding="utf-8")
    c_late = f6.commit(root, "kasadaki kayıttan sonraki commit", "docs")
    side = f6.git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit-tree", f"{c_open}^{{tree}}", "-p", c_s1,
                  "-m", "yan dal: HEAD geçmişinde değil")
    for sha, t in ((c_models, "10:00"), (side, "10:05"), (c_open, "10:10"), (c_out, "10:20"), (c_sealed, "11:00"),
                   (c_late, "11:30")):
        f6.make_proof(root, sha, f"2026-09-25T{t}:00Z")
    ctx = sc.OotContext(root)
    assert (ctx.record_commit("SYNA"), ctx.record_commit("SYNZ")) == (c_open, c_sealed)
    assert sc.cohort_gate_ok(ctx, c_out) == (False, ["SYNZ"])
    klass, ev = sc.class_oot(ctx, "v1_5_h99", "SYNA", c_out)
    assert ev["model_frozen_before_ingest"] and ev["record_before_ingest"] and ev["record_proof_before_ingest_proof"]
    assert (klass, ev["cohort_gate_ok"], ev["cohort_gate_missing_n"]) == ("OOT_RETRO", False, 1)
    assert sc.cohort_gate_ok(ctx, c_sealed) == (False, ["SYNZ"])                   # kasadaki kaydın kanıtı sonucunkinden önce değil
    assert sc.cohort_gate_ok(ctx, c_late) == (True, [])
    assert sc.class_oot(ctx, "v1_5_h99", "SYNA", c_late)[0] == "OOT_BLIND"         # kontrol: her terim tamam
    klass, ev = sc.class_oot(ctx, "v1_5_h99", "SYNA", c_late, record_commit=side)
    assert ev["model_frozen_before_ingest"] and ev["record_proof_before_ingest_proof"] and ev["cohort_gate_ok"]
    assert (klass, ev["record_before_ingest"]) == ("OOT_RETRO", False)             # F3: yalnız kayıt-atası terimi


def _pinned_fetch(files, calls, last):
    def fetch(s, k):
        calls.append((s, k))
        if s > last:                                                         # piyasa sürüyor; istek doğrudan kırmızı
            pytest.fail(f"D_10'dan ({last}) sonraki seansın bülteni istendi: {k} {s}")
        data = files[oc.source_url(s, k)]
        return data, oo.Pin(s, k, oc.source_url(s, k), sha256_bytes(data), len(data), "", "t", oc.internal_name(s, k))
    return fetch


def test_extraction_never_requests_a_bulletin_after_d10(tmp_path, cal, monkeypatch):
    """F2 (D6-2): 40 seanslık sentetik piyasada (kod her gün işlemde, piyasa D_10'dan çok sonra da sürüyor) resolve_member,
    raw_copies ve extract_open_members D_10'dan sonraki hiçbir seansın bültenini istemez; ham kopyanın seans sayısı = çözümlenen
    seans sayısı ≤ 10. Savunma: D_10 sonrası okunmuş ya da 10'dan fazla seanslı bir ayıklama hiçbir çıktıya dönüşmez."""
    sessions = _window(cal, "2021-02-26", 40)
    assert len(sessions) >= 30
    members = [{"ticker": "SYNA", "ftd": "2021-03-01"}, {"ticker": "SYNB", "ftd": "2021-03-03", "vault": "SEALED"}]
    files = f6.market(sessions, {m["ticker"]: f6.ceiling_path(cal.sessions, m["ftd"], ["11.55"] * 35) for m in members})
    window = _window(cal, "2021-03-01", oc.N_SESSIONS)
    calls = []
    ext = oo.resolve_member("SYNA", "2021-03-01", cal, {"SYNA": "OPEN"}, fetch=_pinned_fetch(files, calls, window[-1]))
    assert [s.date for s in ext.resolution.sessions] == window
    assert max(s for s, _ in calls) == window[-1] and len(calls) == 2 * oc.N_SESSIONS
    raw = oo.raw_copies(ext)
    assert len(raw["sessions"]) == len(ext.resolution.sessions) <= oc.N_SESSIONS

    root = _pipeline_repo(tmp_path, cal, members)
    fake = f6.FakeDownloader(files)
    allowed = {oc.source_url(s, k) for s in window for k in oc.KINDS}

    def downloader(url):
        if url not in allowed:
            pytest.fail(f"D_10'dan sonraki ya da pencere dışı bülten istendi: {url}")
        return fake(url)

    out = oo.extract_open_members(root=root, qdir=tmp_path / "q", downloader=downloader, prober=lambda u: False, calendar=cal)
    assert out["extracted"]["SYNA"]["n_sessions"] == oc.N_SESSIONS
    assert sorted(fake.calls) == sorted(allowed)
    doc = json.loads((root / "data" / "outcomes_oot" / "raw" / "SYNA.json").read_text(encoding="utf-8"))
    assert [r["session_date"] for r in doc["sessions"]] == window

    late = sessions[sessions.index(window[-1]) + 1]
    over = dataclasses.replace(ext, thb={**ext.thb, late: ext.thb[window[-1]]}, thm={**ext.thm, late: ext.thm[window[-1]]})
    with pytest.raises(oo.OotOutcomeError, match="D_10"):
        oo.raw_copies(over)
    many = dataclasses.replace(ext, resolution=dataclasses.replace(
        ext.resolution, sessions=ext.resolution.sessions + ext.resolution.sessions[-1:]))
    with pytest.raises(oo.OotOutcomeError, match="seans çözümlendi"):
        oo.raw_copies(many)
    real = oo.resolve_member

    def reads_past_d10(*a, **kw):                                            # D_10'da durmayan bir ayıklayıcının etkisi
        got = real(*a, **kw)
        return dataclasses.replace(got, thb={**got.thb, late: got.thb[window[-1]]}, thm={**got.thm, late: got.thm[window[-1]]})

    monkeypatch.setattr(oo, "resolve_member", reads_past_d10)
    root2 = _pipeline_repo(tmp_path / "d", cal, members)
    with pytest.raises(oo.OotOutcomeError, match="D_10"):
        oo.extract_open_members(root=root2, qdir=tmp_path / "q2", downloader=f6.FakeDownloader(files),
                                prober=lambda u: False, calendar=cal)
    assert not (root2 / "data").exists()                                     # sonuç, ham kopya, manifest yazılmadı


def test_download_gate_ignores_s3_outputs_only(tmp_path, cal):
    """F6: yarım kalan bir S3 koşusunun izlenmeyen çıktıları (registry/oot/d1_rows/, registry/oot/post_d1/) kapıyı kapatmaz
    (o dizinlerin bekçileri ayrı: d1_rows_problems, G1); registry/oot'un başka her yerindeki kirlilik kapatır."""
    root = _pipeline_repo(tmp_path, cal, MEMBERS[:2])
    oot = root / "registry" / "oot"
    (oot / "d1_rows").mkdir()
    (oot / "d1_rows" / "SYNA.json").write_text("{}\n", encoding="utf-8")
    (oot / "post_d1" / "SYNA").mkdir(parents=True)
    (oot / "post_d1" / "SYNA" / "kayit.json").write_text("{}\n", encoding="utf-8")
    assert oo.s2_gate_problems(root=root) == []
    oo.download_gate(root=root)
    assert oo.d1_rows_problems({}, [])                                       # d1_rows bekçisi ayrı ve hâlâ reddediyor
    for rel in ("d1_rows_x.json", "post_d1x/a.json", "inputs/SYNX.json", "not.txt"):
        p = oot / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}\n", encoding="utf-8")
        problems = oo.s2_gate_problems(root=root)
        assert any(q.startswith("registry/oot temiz değil") and f"registry/oot/{rel}" in q for q in problems), rel
        p.unlink()
    inputs = oot / "inputs" / "SYNA.json"
    inputs.write_bytes(inputs.read_bytes() + b"\n")
    with pytest.raises(oo.GateError, match="temiz değil"):
        oo.download_gate(root=root)


# ================================================================ S3/S5 ayıklama görevi (BORSAI_FAZ6_S3_S5_EXTRACT): T1, T2, T3

S3_MEMBERS = [{"ticker": "SYNA", "ftd": "2021-03-01"}, {"ticker": "SYNC", "ftd": "2021-03-08"},
              {"ticker": "SYNB", "ftd": "2021-03-03", "vault": "SEALED"}]


def test_extract_d1_rows_is_rerun_safe_unchanged_or_stop(tmp_path, cal):
    """T1 (F6 kalıntısı): yeniden koşu aynı baytları UNCHANGED sayar ve karantinadan okur (indirme yok); yarım kalmış koşu yalnız
    eksik dosyayı yazar; var olan dosya yeni belgeyle bayt-eşit değilse OotOutcomeError (DUR) ve hiçbir dosya değişmez."""
    root = _pipeline_repo(tmp_path, cal, S3_MEMBERS)
    fake = f6.FakeDownloader(f6.market(_window(cal, "2021-02-26", 30), _paths_for(cal, S3_MEMBERS)))
    kw = dict(root=root, qdir=tmp_path / "q", downloader=fake, prober=lambda u: False, calendar=cal)
    d1_dir, man = root / "registry" / "oot" / "d1_rows", root / "data" / "raw" / "bist" / "MANIFEST_OOT.csv"
    snap = lambda: ({p.name: p.read_bytes() for p in sorted(d1_dir.glob("*.json"))}, man.read_bytes())  # noqa: E731
    first = oo.extract_d1_rows(**kw)
    assert first["written"] == ["SYNA", "SYNC"]
    before, n_calls = snap(), len(fake.calls)
    again = oo.extract_d1_rows(**kw)                                         # F6 öncesi kod: FileExistsError
    assert (again["written"], again["unchanged"]) == ([], ["SYNA", "SYNC"])
    assert (first["unchanged"], first["d1_after_first_trading_date"]) == ([], [])
    assert snap() == before and len(fake.calls) == n_calls                  # dokunulmadı; karantina önbellek
    (d1_dir / "SYNC.json").unlink()                                          # yarım kalmış koşu
    resumed = oo.extract_d1_rows(**kw)
    assert (resumed["written"], resumed["unchanged"]) == (["SYNC"], ["SYNA"]) and snap() == before
    (d1_dir / "SYNA.json").write_bytes(before[0]["SYNA.json"] + b"\n")      # farklı baytlar
    with pytest.raises(oo.OotOutcomeError, match="bayt-eşit değil"):
        oo.extract_d1_rows(**kw)
    assert snap() == ({**before[0], "SYNA.json": before[0]["SYNA.json"] + b"\n"}, before[1])
    assert sorted(p.name for p in d1_dir.iterdir()) == ["SYNA.json", "SYNC.json"]   # kasadaki üye yok


def _s3_outputs(tmp_path, cal, members):
    """S1 + S2 (kanıtlı) depo, S3a ayıklaması yapılmış (commit'siz)."""
    root = _pipeline_repo(tmp_path, cal, members)
    files = f6.market(_window(cal, "2021-02-26", 40), _paths_for(cal, members))
    oo.extract_d1_rows(root=root, qdir=tmp_path / "q", downloader=f6.FakeDownloader(files), prober=lambda u: False,
                       calendar=cal)
    return root


def _write_post_d1(root, tickers):
    od = root / "registry" / "oot"
    return {t: fz.write_oot_post_d1_record(t, now=NOW, post_dir=od / "post_d1", d1_rows_dir=od / "d1_rows",
                                           records_dir=od / "records", root=root).relative_to(root).as_posix()
            for t in tickers}


def test_s3_gate_requires_committed_unchanged_pushed_d1_rows_and_post_d1(tmp_path, cal):
    """T3: S5 kapısı açık kümenin her üyesi için D_1 satırı dosyasını ve POST_D1 kaydını ister: commit'li, değişmemiş, push
    kanıtlı; kayıt dosyanın kanonik sha'sını taşır. Eksik kanıt -> sorun listelenir; tam -> []. Kasadaki üye için dosya
    beklenmez; açık küme dışındaki bir ad yalnız sayı olarak görünür."""
    root = _s3_outputs(tmp_path, cal, S3_MEMBERS)
    d1 = {t: f"registry/oot/d1_rows/{t}.json" for t in ("SYNA", "SYNC")}
    problems = oo.s3_gate_problems(root=root)
    assert "data/raw/bist/MANIFEST_OOT.csv: HEAD'de yok (D_1 pinleri commit'li değil)" in problems
    assert {f"{d1[t]}: commit'li değil" for t in d1} | {f"{t}: etkin eski kohort POST_D1 kaydı yok" for t in d1} <= set(problems)
    c_s3a = f6.commit(root, "S3a", "registry/oot/d1_rows", "data/raw/bist/MANIFEST_OOT.csv")
    rec = _write_post_d1(root, ["SYNA", "SYNC"])
    assert sorted(oo.s3_gate_problems(root=root)) == sorted(
        ["S3 çıktı dizinlerinde izlenmeyen 2 dosya"] + [f"{d1[t]}: push kanıtı yok" for t in d1]
        + [f"{rec[t]}: commit'li değil" for t in rec])
    f6.git(root, "add", "--", "registry/oot/post_d1")                        # sahnelenmiş ama commit'lenmemiş
    assert {f"{rec[t]}: commit'li değil" for t in rec} <= set(oo.s3_gate_problems(root=root))
    c_s3b = f6.commit(root, "S3b", "registry/oot/post_d1")
    assert sorted(oo.s3_gate_problems(root=root)) == sorted(
        [f"{d1[t]}: push kanıtı yok" for t in d1] + [f"{rec[t]}: push kanıtı yok" for t in rec])
    f6.make_proof(root, c_s3a, "2026-09-25T10:15:00Z")
    assert sorted(oo.s3_gate_problems(root=root)) == sorted(f"{rec[t]}: push kanıtı yok" for t in rec)
    f6.make_proof(root, c_s3b, "2026-09-25T10:16:00Z")
    assert oo.s3_gate_problems(root=root) == []

    p = root / d1["SYNA"]
    orig = p.read_bytes()
    p.write_bytes(orig + b"\n")                                              # commit'ten sonra değişmiş (kanonik sha aynı)
    assert oo.s3_gate_problems(root=root) == [f"{d1['SYNA']}: commit'ten sonra değişmiş"]
    p.write_bytes(orig)
    sealed = root / "registry" / "oot" / "d1_rows" / "SYNB.json"
    sealed.write_text("{}\n", encoding="utf-8")                              # açık küme dışı ad: yalnız sayı
    problems = oo.s3_gate_problems(root=root)
    assert problems == ["S3 çıktı dizinlerinde izlenmeyen 1 dosya", "S3 çıktı dizinlerinde açık küme dışında 1 ad"]
    assert not any("SYNB" in q for q in problems)
    sealed.unlink()

    doc = json.loads(p.read_text(encoding="utf-8"))                          # kayıt başka bir D_1 dosyasına bağlı
    doc["d1"]["fields_raw"]["aof"] = doc["d1"]["fields_raw"]["aof"] + "0"
    p.write_bytes(pretty_json_bytes(doc))
    f6.make_proof(root, f6.commit(root, "d1_rows değişti", d1["SYNA"]), "2026-09-25T10:17:00Z")
    assert oo.s3_gate_problems(root=root) == [f"{rec['SYNA']}: d1_rows sha256'sı D_1 satırı dosyasının kanonik sha'sı değil"]
    p.write_bytes(orig)
    f6.make_proof(root, f6.commit(root, "d1_rows geri", d1["SYNA"]), "2026-09-25T10:18:00Z")
    assert oo.s3_gate_problems(root=root) == []

    f6.git(root, "rm", "-q", "-r", "--", "registry/oot/post_d1/SYNC")       # POST_D1 kaydı commit'le silindi (kanıtlı)
    f6.make_proof(root, f6.commit(root, "post_d1 SYNC silindi", "registry/oot/post_d1"), "2026-09-25T10:19:00Z")
    assert oo.s3_gate_problems(root=root) == ["SYNC: etkin eski kohort POST_D1 kaydı yok"]


def test_cli_s5_calls_s3_gate_before_any_extraction(monkeypatch, tmp_path, capsys):
    """T3: `s5` önce `s3_gate_problems`'ı çağırır; sorun varsa `extract_open_members` çağrılmaz (hiçbir bülten indirilmez)."""
    calls = []
    monkeypatch.setattr(oo, "s3_gate_problems", lambda **kw: ["SYNA: etkin eski kohort POST_D1 kaydı yok"])
    monkeypatch.setattr(oo, "extract_open_members", lambda **kw: calls.append(kw) or {"extracted": {}, "sealed_not_opened": 0})
    assert oo.main(["s5", "--quarantine", str(tmp_path / "q"), "--pace", "0"]) == 2
    out = json.loads(capsys.readouterr().out)
    assert (out["durum"], out["hata"], calls) == ("DUR", "GateError", [])
    monkeypatch.setattr(oo, "s3_gate_problems", lambda **kw: [])
    assert oo.main(["s5", "--quarantine", str(tmp_path / "q"), "--pace", "0"]) == 0 and len(calls) == 1
    assert json.loads(capsys.readouterr().out)["durum"] == "TAMAM"


def test_cli_commands_print_numbers_only_pace_downloads_and_rerun(tmp_path, cal, capsys):
    """T2: probe -> s3 -> s3-post-d1 -> (commit + kanıt) -> s5 sentetik depoda. Çıktı JSON, hiçbir kod yok; --pace yalnız gerçek
    indirmeden önce bekler (karantinadan okuma beklemez); her komut yeniden koşulabilir (UNCHANGED / zaten var). POST_D1
    kaydı d1_rows'u olan HER açık üyeye yazılır: f3'süz üye REFUSED, D_1'i tavan olmayan üye NOT_APPLICABLE (T4)."""
    members = S3_MEMBERS + [{"ticker": "SYNM", "ftd": "2021-03-15", "f3": None},
                            {"ticker": "SYNN", "ftd": "2021-03-22"}, {"ticker": "SYNL", "ftd": "2021-03-24"}]
    paths = _paths_for(cal, members[:4])
    paths["SYNN"] = f6.ceiling_path(cal.sessions, "2021-03-22", ["11.00"] * 12, ["11.55"] * 12)      # D_1 tavan değil
    paths["SYNL"] = f6.ceiling_path(cal.sessions, "2021-03-26", ["11.55"] * 12)                    # ilk görünüş sonra
    root = _pipeline_repo(tmp_path, cal, members)
    fake = f6.FakeDownloader(f6.market(_window(cal, "2021-02-26", 60), paths))
    heads, sleeps = [], []
    inject = dict(root=root, downloader=fake, calendar=cal, now=NOW, sleep=sleeps.append,
                  head=lambda u: heads.append(u) or {"status": 404, "content_type": "text/html", "content_length": "123"})
    args = ["--quarantine", str(tmp_path / "q"), "--pace", "0.25"]

    def run(cmd):
        rc = oo.main([cmd, *args], **inject)
        text = capsys.readouterr().out
        out = json.loads(text)
        assert "SYNB" not in text                                            # kasadaki kod hiçbir çıktıda yok
        if out["durum"] == "TAMAM":
            assert not re.search(r"SYN[A-Z]", text), text                    # yalnız sayı (DUR açık kodu adlandırabilir)
        return rc, out

    rc, out = run("probe")
    assert (rc, out["durum"], out["published"], out["mode"]) == (0, "TAMAM", 0, "XU100_GAP_ONLY")
    assert fake.calls == [] and sleeps == [] and out["n_checked"] == 5
    assert [(d["date"], d["status"]) for d in out["checked"]] == [(d, 404) for d in m20.XU100_GAP_CLOSURES]
    rc, out = run("s3")
    assert (rc, out["written"], out["unchanged"], out["total"], out["d1_after_first_trading_date"]) == (0, 5, 0, 5, 1)
    assert out["network_downloads"] == len(fake.calls) == len(sleeps) > 0 and set(sleeps) == {0.25}
    assert out["probe_status"] == {"404": 5}
    rc, out = run("s3")
    assert (rc, out["written"], out["unchanged"], out["network_downloads"]) == (0, 0, 5, 0)
    assert len(sleeps) == len(fake.calls)                                   # karantinadan okuma beklemedi
    rc, out = run("s5")                                                      # S3 çıktıları commit'siz: kapı kapalı
    assert (rc, out["durum"], out["hata"]) == (2, "DUR", "GateError") and len(sleeps) == len(fake.calls)
    rc, out = run("s3-post-d1")
    assert (rc, out["d1_rows"], out["written"], out["already_present"]) == (0, 5, 5, 0)
    assert out["status"] == {"NOT_APPLICABLE": 1, "PREDICTED": 3, "REFUSED": 1}
    assert out["codes"] == {"NOT_APPLICABLE:D1_NOT_CEILING": 1, "REFUSED:F3_MISSING": 1}
    rc, out = run("s3-post-d1")
    assert (rc, out["written"], out["already_present"], out["records"]) == (0, 0, 5, 5)
    c_s3a = f6.commit(root, "S3a", "registry/oot/d1_rows", "data/raw/bist/MANIFEST_OOT.csv")
    c_s3b = f6.commit(root, "S3b", "registry/oot/post_d1")
    f6.make_proof(root, c_s3a, "2026-09-25T10:15:00Z")
    f6.make_proof(root, c_s3b, "2026-09-25T10:16:00Z")
    n = len(fake.calls)
    rc, out = run("s5")
    assert (rc, out["extracted"], out["actions"], out["n_sessions"], out["sealed_not_opened"]) == (
        0, 5, {"CREATED": 5}, {"10": 5}, 1)
    assert out["network_downloads"] == len(fake.calls) - n == len(sleeps) - n > 0
    rc, out = run("s5")
    assert (rc, out["actions"], out["network_downloads"]) == (0, {"UNCHANGED": 5}, 0)
    assert not any("SYNB" in u for u in fake.calls) and not (root / "data" / "outcomes_oot" / "SYNB.csv").exists()


def test_cli_stops_on_closed_gate_head_codes_published_gap_day_and_unpublished_session(tmp_path, cal, capsys):
    """T6: kapı kapalı -> HEAD bile yok; HEAD 200/404 dışı -> DUR (durum kodu, Content-Type, Content-Length; GET yok); XU100
    boşluk günü yayımlanmış -> CalendarConflict; takvimde seans olan bir günün bülteni 404 -> NotPublished (DUR)."""
    heads = []

    def head(status_for):
        return lambda u: heads.append(u) or {"status": status_for(u), "content_type": "text/html", "content_length": "9"}

    def run(cmd, root, **kw):
        rc = oo.main([cmd, "--quarantine", str(tmp_path / "q"), "--pace", "0"], root=root, calendar=cal, now=NOW, **kw)
        return rc, json.loads(capsys.readouterr().out)

    closed = _pipeline_repo(tmp_path / "closed", cal, S3_MEMBERS, proofs=False)
    rc, out = run("probe", closed, head=head(lambda u: 404))
    assert (rc, out["hata"], heads) == (2, "GateError", [])
    root = _pipeline_repo(tmp_path / "open", cal, S3_MEMBERS)
    fake = f6.FakeDownloader({})
    rc, out = run("probe", root, head=head(lambda u: 403), downloader=fake)
    assert (rc, out["hata"]) == (2, "OotOutcomeError") and "HEAD 403" in out["mesaj"] and "text/html" in out["mesaj"]
    rc, out = run("s3", root, head=head(lambda u: 200 if oc.compact("2023-04-24") in u else 404), downloader=fake)
    assert (rc, out["hata"]) == (2, "CalendarConflict") and fake.calls == []
    files = f6.market(_window(cal, "2021-02-26", 30), _paths_for(cal, S3_MEMBERS))
    missing = oc.source_url("2021-03-08", "thm")
    rc, out = run("s3", root, head=head(lambda u: 404),
                  downloader=f6.FakeDownloader({u: b for u, b in files.items() if u != missing}))
    assert (rc, out["hata"]) == (2, "NotPublished") and missing in out["mesaj"]


# ================================================================ EK1: Takvim C kapanışları için bülten kanıtı (K1–K7)

GAP_FEB = ("2023-02-09", "2023-02-10", "2023-02-13", "2023-02-14")


def _closure_bulletins(trading=("2023-04-24",), no_trading=GAP_FEB, few=()):
    """Sentetik sunucu (yalnız kapanış günleri): `trading` günlerinde 60 işlemli pay satırı, `no_trading` günlerinde 60
    işlemsiz pay satırı, `few` günlerinde 3 işlemli pay satırı; hepsinde ayrıca işlemli bir pay DIŞI satır (sayılmaz). Diğer
    kapanışlar 404. Dönen: (URL -> zip, HEAD fonksiyonu)."""
    def rows(n_traded):
        return [f6.thb_row(f"Z{i:03d}.E", "5.00", "10" if i < n_traded else "0") for i in range(60)] + [
            f6.thb_row("ZZF.F", "1.00", "7")]
    files = {oc.source_url(d, "thb"): f6.make_zip(d, "thb", rows(n))
             for days, n in ((trading, 60), (no_trading, 0), (few, 3)) for d in days}
    return files, _head_for(files)


def _head_for(files, override=None):
    def head(url):
        for d, status in (override or {}).items():
            if url == oc.source_url(d, "thb"):
                return {"status": status, "content_type": "x", "content_length": "1"}
        return {"status": 200 if url in files else 404, "content_type": "x", "content_length": "1"}
    return head


def _evidence(tmp_path, files, head):
    """Kanıt dosyası tmp/data/raw/<ad> (`load_calendar_oot(bist_dir=tmp/data/raw/bist)` onu okur) ve karantinası tmp/q."""
    rows = oo.calendar_evidence_rows(qdir=tmp_path / "q", downloader=f6.FakeDownloader(files), head=head, now=NOW)
    path = tmp_path / "data" / "raw" / oo.CAL_EVIDENCE_NAME
    assert oo.write_calendar_evidence(rows, path) == "CREATED"
    return path, rows


def test_evidence_decision_rule_k4_and_aggregate_counts():
    """K4 (önceden yazılmış): 404 -> NOT_PUBLISHED; 200 + 0 işlemli pay satırı -> PUBLISHED_NO_TRADING; ≥ 50 -> TRADING_SESSION;
    1–49 ya da başka HEAD kodu -> DUR. K3 sayıları yalnız toplam; pay dışı satır işlemli sayılmaz; bülten geçerliliği
    `parse_bulletin` kuralıyla (iç ad, satır TARIH'i)."""
    assert oo.evidence_decision(404, None) == "NOT_PUBLISHED"
    assert oo.evidence_decision(200, 0) == "PUBLISHED_NO_TRADING"
    assert oo.evidence_decision(200, 50) == oo.evidence_decision(200, 700) == "TRADING_SESSION"
    for n in (1, 3, 49):
        with pytest.raises(oo.OotOutcomeError, match="1–49"):
            oo.evidence_decision(200, n)
    for status in (301, 403, 500):
        with pytest.raises(oo.OotOutcomeError, match=f"HEAD {status}"):
            oo.evidence_decision(status, 0)
    files, _ = _closure_bulletins(few=("2020-05-01",))
    count = lambda d: oo.bulletin_trade_counts(files[oc.source_url(d, "thb")], d)  # noqa: E731
    assert count("2023-04-24") == {"n_rows": 61, "n_equity_rows": 60, "n_equity_rows_traded": 60}
    assert count("2023-02-09") == {"n_rows": 61, "n_equity_rows": 60, "n_equity_rows_traded": 0}
    assert count("2020-05-01") == {"n_rows": 61, "n_equity_rows": 60, "n_equity_rows_traded": 3}
    assert oo.bulletin_trade_counts(f6.make_zip("2023-02-10", "thb", []), "2023-02-10") == {
        "n_rows": 0, "n_equity_rows": 0, "n_equity_rows_traded": 0}
    with pytest.raises(oo.OotOutcomeError, match="iç dosya"):
        oo.bulletin_trade_counts(f6.make_zip("2023-02-10", "thb", []), "2023-02-13")
    other_day = f6.make_zip("2023-04-21", "thb", [f6.thb_row("Z000.E", "5.00")])
    with zipfile.ZipFile(io.BytesIO(other_day)) as z:
        text = z.read(z.namelist()[0])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(oc.internal_name("2023-04-24", "thb"), text)                # satır TARIH'i bülten günü değil
    with pytest.raises(oo.OotOutcomeError, match="TARIH"):
        oo.bulletin_trade_counts(buf.getvalue(), "2023-04-24")


def test_calendar_evidence_command_writes_once_unchanged_or_stop(tmp_path, cal, capsys):
    """K3/E1: `calendar-evidence` önce kapı, sonra Takvim C'nin 42 hafta içi tam kapanışı (37 tatil tablosu + 5 XU100 boşluğu)
    için HEAD; 200 günlerinin zip'i karantinaya, dosyaya yalnız sayılar. Yeniden koşu UNCHANGED (checked_at karşılaştırılmaz,
    ilk yazım korunur, indirme yok); farklı ölçüm, 1–49 işlemli satır ya da 200/404 dışı HEAD -> DUR, dosyaya dokunulmaz."""
    closures = oo.calendar_c_weekday_closures()
    assert len(closures) == 42 and Counter(s for _, s in closures) == {"HOLIDAY_TABLE": 37, "XU100_GAP": 5}
    assert [d for d, s in closures if s == "XU100_GAP"] == list(m20.XU100_GAP_CLOSURES)
    files, head = _closure_bulletins()

    def run(root, q, now=NOW, head=head, downloader=None):
        rc = oo.main(["calendar-evidence", "--quarantine", str(q), "--pace", "0"], root=root, head=head, now=now,
                     downloader=downloader or f6.FakeDownloader(files))
        return rc, json.loads(capsys.readouterr().out)

    root = _pipeline_repo(tmp_path / "a", cal, MEMBERS[:2])
    path = root / oo.CAL_EVIDENCE_REL
    rc, out = run(root, tmp_path / "qa")
    assert (rc, out["action"], out["n_rows"], out["sources"]) == (0, "CREATED", 42, {"HOLIDAY_TABLE": 37, "XU100_GAP": 5})
    assert out["decisions"] == {"NOT_PUBLISHED": 37, "PUBLISHED_NO_TRADING": 4, "TRADING_SESSION": 1}
    assert out["xu100_gap"] == {**{d: "PUBLISHED_NO_TRADING" for d in GAP_FEB}, "2023-04-24": "TRADING_SESSION"}
    assert (out["trading_sessions"], out["network_downloads"], out["probe_status"]) == (["2023-04-24"], 5, {"200": 5, "404": 37})
    rows = {r["date"]: r for r in oo.read_calendar_evidence(path)}
    assert list(rows) == [d for d, _ in closures]
    zip_424 = files[oc.source_url("2023-04-24", "thb")]
    assert [rows["2023-04-24"][k] for k in ("thb_head_status", "thb_sha256", "thb_bytes", *oo.CAL_EVIDENCE_COUNTS)] == [
        "200", sha256_bytes(zip_424), str(len(zip_424)), "61", "60", "60"]
    assert all(rows["2020-01-01"][k] == "" for k in ("thb_sha256", "thb_bytes", *oo.CAL_EVIDENCE_COUNTS))
    text = path.read_text(encoding="utf-8")
    assert ".E" not in text and "Z000" not in text and not re.search(r"th[bm]20\d{6}", text)   # yalnız sayılar
    before = path.read_bytes()
    rc, out = run(root, tmp_path / "qa", now=NOW + timedelta(hours=3))
    assert (rc, out["action"], out["network_downloads"]) == (0, "UNCHANGED", 0) and path.read_bytes() == before
    changed = {**files, oc.source_url("2020-01-01", "thb"): f6.make_zip("2020-01-01", "thb", [])}
    rc, out = run(root, tmp_path / "qa", head=_head_for(changed), downloader=f6.FakeDownloader(changed))
    assert (rc, out["hata"]) == (2, "OotOutcomeError") and "aynı değil" in out["mesaj"] and path.read_bytes() == before

    root = _pipeline_repo(tmp_path / "b", cal, MEMBERS[:2])
    few, few_head = _closure_bulletins(trading=(), few=("2023-04-24",))
    rc, out = run(root, tmp_path / "qb", head=few_head, downloader=f6.FakeDownloader(few))
    assert (rc, out["hata"]) == (2, "OotOutcomeError") and "işlemli pay satırı 3 (1–49)" in out["mesaj"]
    rc, out = run(root, tmp_path / "qc", head=_head_for(files, {"2021-05-19": 403}))
    assert (rc, out["hata"]) == (2, "OotOutcomeError") and "HEAD 403" in out["mesaj"]
    assert not (root / oo.CAL_EVIDENCE_REL).exists()
    closed, heads = _pipeline_repo(tmp_path / "c", cal, MEMBERS[:2], proofs=False), []
    rc, out = run(closed, tmp_path / "qd", head=lambda u: heads.append(u) or head(u))
    assert (rc, out["hata"], heads) == (2, "GateError", [])


def test_outcome_calendar_counts_trading_session_evidence_days_only(tmp_path):
    """K2: sonuç takvimi = Takvim C seansları ∪ TRADING_SESSION günleri; PUBLISHED_NO_TRADING ve NOT_PUBLISHED günleri kapalı
    kalır; yarım günler değişmez; kanıt yoksa Takvim C (K1: Takvim C dosyası ve market20 sabitleri aynen)."""
    bist = tmp_path / "data" / "raw" / "bist"
    base = oo.load_calendar_oot(bist_dir=bist)
    assert tuple(s for s in base.sessions if s <= "2023-09-21") == m20.load_calendar_c().sessions
    files, head = _closure_bulletins()
    path, rows = _evidence(tmp_path, files, head)
    cal2 = oo.load_calendar_oot(bist_dir=bist)
    assert sorted(set(cal2.sessions) - set(base.sessions)) == ["2023-04-24"] and set(base.sessions) <= set(cal2.sessions)
    assert not set(GAP_FEB) & set(cal2.sessions) and "2020-01-01" not in cal2.sessions
    assert cal2.sessions == tuple(sorted(cal2.sessions)) and cal2.half_days == base.half_days
    assert sha256_file(path) in cal2.sha256.split("+") and cal2.sha256 != base.sha256
    assert sha256_file(m20.CALENDAR_C_PATH) == m20.CALENDAR_C_SHA256 and m20.XU100_GAP_CLOSURES[-1] == "2023-04-24"
    lying = [dict(r, decision="TRADING_SESSION") if r["date"] == "2023-02-09" else r for r in rows]
    path.write_bytes(oo.evidence_bytes(lying))                               # karar sayılarla (K4) tutarsız
    with pytest.raises(oo.OotOutcomeError, match="K4"):
        oo.load_calendar_oot(bist_dir=bist)
    stray = [dict(r, date="2023-04-25") if r["date"] == "2023-04-24" else r for r in rows]
    path.write_bytes(oo.evidence_bytes(stray))                               # seans günü TRADING_SESSION yazılmış
    with pytest.raises(oo.OotOutcomeError, match="kapanışı değil"):
        oo.load_calendar_oot(bist_dir=bist)


def test_calendar_probe_checks_every_weekday_closure_against_evidence(tmp_path, cal, capsys):
    """K5: kanıt varken Takvim C'nin her hafta içi kapanışı denetlenir; kanıtta satırı yok / kanıtta kapanış olmayan gün,
    NOT_PUBLISHED ama HEAD 200, PUBLISHED_* ya da TRADING_SESSION ama HEAD 404, karantina zip'i yok ya da sha'sı pinle eşit
    değil -> CalendarConflict. Kanıt yoksa eski davranış (5 XU100-boşluk günü; yayımlanmışsa DUR)."""
    files, head = _closure_bulletins()
    path, rows = _evidence(tmp_path, files, head)
    q = tmp_path / "q"

    def check(h, p=path):
        return oo.check_calendar_closures(oo.strict_prober(h), qdir=q, evidence_path=p)

    assert check(head) == [d for d, _ in oo.calendar_c_weekday_closures()]
    for override, message in (({"2020-01-01": 200}, "2020-01-01: kanıt NOT_PUBLISHED ama HEAD 200"),
                              ({"2023-02-09": 404}, "2023-02-09: kanıt PUBLISHED_NO_TRADING ama HEAD 404"),
                              ({"2023-04-24": 404}, "2023-04-24: kanıt TRADING_SESSION ama HEAD 404")):
        with pytest.raises(oo.CalendarConflict, match=message):
            check(_head_for(files, override))
    other = tmp_path / "other" / oo.CAL_EVIDENCE_NAME
    other.parent.mkdir()
    other.write_bytes(oo.evidence_bytes([r for r in rows if r["date"] != "2020-01-01"]))
    with pytest.raises(oo.CalendarConflict, match="2020-01-01: kanıtta satırı yok"):
        check(head, other)
    extra = dict(next(r for r in rows if r["date"] == "2020-01-01"), date="2020-01-02")
    other.write_bytes(oo.evidence_bytes(sorted(rows + [extra], key=lambda r: r["date"])))
    with pytest.raises(oo.CalendarConflict, match="2020-01-02: kanıtta var ama Takvim C'nin hafta içi kapanışı değil"):
        check(head, other)
    z = oc.local_path("2023-02-10", "thb", q)
    original = z.read_bytes()
    z.write_bytes(original + b"\0")
    with pytest.raises(oo.CalendarConflict, match="2023-02-10: karantinadaki zip'in sha256'sı kanıttaki pinle eşit değil"):
        check(head)
    z.unlink()
    with pytest.raises(oo.CalendarConflict, match="2023-02-10: karantinada zip yok"):
        check(head)
    z.write_bytes(original)
    assert check(head) == [d for d, _ in oo.calendar_c_weekday_closures()]
    missing = tmp_path / "yok.csv"                                            # kanıt yok: eski davranış
    assert check(_head_for({}), missing) == list(m20.XU100_GAP_CLOSURES)
    with pytest.raises(oo.CalendarConflict, match="yayımlanmış"):
        check(head, missing)

    root = _pipeline_repo(tmp_path / "cli", cal, MEMBERS[:2])                 # CLI: calendar-evidence -> probe
    args = ["--quarantine", str(tmp_path / "q_cli"), "--pace", "0"]
    assert oo.main(["calendar-evidence", *args], root=root, head=head, downloader=f6.FakeDownloader(files), now=NOW) == 0
    capsys.readouterr()
    assert oo.main(["probe", *args], root=root, head=head) == 0
    out = json.loads(capsys.readouterr().out)
    assert (out["mode"], out["n_checked"], out["published"]) == ("EVIDENCE", 42, 5)
    assert oo.main(["probe", *args], root=root, head=_head_for(files, {"2023-04-24": 404})) == 2
    assert json.loads(capsys.readouterr().out)["hata"] == "CalendarConflict"
    market = {**f6.market(_window(cal, "2021-02-26", 20), _paths_for(cal, MEMBERS[:2])), **files}
    assert oo.main(["s3", *args], root=root, head=head, downloader=f6.FakeDownloader(market), calendar=cal) == 0
    out = json.loads(capsys.readouterr().out)                                # ayıklayıcı da kanıtlı probu kullanır
    assert (out["written"], out["probe_status"]) == (1, {"200": 5, "404": 37})

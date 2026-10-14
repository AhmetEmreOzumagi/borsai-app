"""Faz 7: eğitim tablosu v2 ve tahsis rejimi (SPEC_HAZARD_V1 §3.3, §3.4, §11-1, §11-3; SPEC_DEVIATIONS J).

Kasa (SEALED) üyelerinin dosyaları okunmaz; kasa kodları hiçbir çıktıya yazılmaz (yalnız sayılar)."""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import re
from collections import Counter
from datetime import date, timedelta

import pytest

from borsai import data as dm
from borsai import registry as reg
from borsai import survival as sv
from borsai.provenance import ROOT, sha256_file
from borsai.specs import H99_DATA_VERSION_SHA256, POOLED_TRAINING, V2_DATA_VERSION_SHA256

L_DIST_OPEN = {0: 9, 1: 11, 2: 5, 3: 4, 4: 3, 5: 8, 6: 5, 7: 6, 8: 5, 9: 6, 10: 9}     # §11-1 [ÖLÇTÜM §9]


@pytest.fixture(scope="module")
def v2():
    return dm.load_dataset_v2()


@pytest.fixture(scope="module")
def cohort():
    return reg.read_cohort()[1]


def _table_rows():
    return list(csv.DictReader(io.StringIO(dm.TABLE_V2_PATH.read_text(encoding="utf-8"), newline="")))


def test_v2_rows_columns_and_order(v2):
    rows = _table_rows()
    assert len(rows) == len(v2.rows) == 170
    assert Counter(r["cohort"] for r in rows) == {"H99": 99, "OOT_OPEN": 71}
    assert list(rows[0]) == dm.v2_columns() == dm.h99_columns() + list(dm.V2_EXTRA_COLUMNS) and len(dm.v2_columns()) == 39
    order = [(r["first_trading_date"], r["ticker"]) for r in rows]
    assert order == sorted(order) and len({r["ticker"] for r in rows}) == 170
    assert v2.data_version_sha256 == V2_DATA_VERSION_SHA256 == POOLED_TRAINING["data_version_sha256"]
    version = json.loads(dm.VERSION_V2_PATH.read_text(encoding="utf-8"))
    assert version["sha256"] == sha256_file(dm.TABLE_V2_PATH) and version["sealed_rows"] == 0
    assert version["cohorts"] == {"H99": 99, "OOT_OPEN": 71}


def test_h99_rows_byte_equal_on_shared_columns_and_originals_untouched():
    """§11-1: H99'un 99 satırı training_table.csv ile paylaşılan 31 sütunda bayt-eşit; training_table.csv, data_version.json ve
    build_training_table.py değişmedi."""
    old_lines = dm.TABLE_PATH.read_bytes().decode("utf-8").splitlines()
    old = {line.split(",", 1)[0]: line for line in old_lines[1:]}
    cols = dm.h99_columns()
    for r in _table_rows():
        if r["cohort"] != "H99":
            continue
        buf = io.StringIO(newline="")
        csv.writer(buf, lineterminator="").writerow([r[c] for c in cols])
        assert buf.getvalue() == old[r["ticker"]], r["ticker"]
    version = json.loads(dm.VERSION_PATH.read_text(encoding="utf-8"))
    assert sha256_file(dm.TABLE_PATH) == version["sha256"] == "b307cd0e3a015f5d251512541007c5b16f8458224ab047e493c01551ccda7fb5"
    assert sha256_file(dm.VERSION_PATH) == H99_DATA_VERSION_SHA256
    assert sha256_file(ROOT / "data" / "build_training_table.py") == version["builder_sha256"]


def test_open_members_L_distribution_matches_outcomes(v2):
    from borsai import outcomes as oc
    from borsai import outcomes_oot as oo

    oot = [r for r in v2.rows if r.cohort == "OOT_OPEN"]
    assert len(oot) == 71 and dict(sorted(Counter(r.ceiling_streak for r in oot).items())) == L_DIST_OPEN
    for r in oot:
        rows = oo.read_outcome_oot(oo.outcome_path(r.ticker))
        assert r.ceiling_streak == oc.streak([int(x["ceiling_close"]) for x in rows])
        assert list(r.session_dates) == [x["session_date"] for x in rows] and r.session_dates[0] == r.first_trading_date
    assert max(d for r in oot for d in r.session_dates) <= "2023-10-04"         # §5.1: ilk v0 fold'undan (2023-11-21) önce


def test_alloc_regime_single_definition_equals_cohort_labels(v2, cohort):
    """§3.3/§11-1: v2'nin alloc_regime sütunu tek fonksiyondan (data.alloc_regime, talep toplama başlangıcı; I8) ve açık kümede
    kohort etiketiyle 71/71, H99'da 99/99 EQUAL_DIST. Kasa üyeleri için 135/135: data.alloc_regime ≡ registry.compute_regime_tags
    (bütün günlerde, aşağıda) ve kohort etiketleri compute_regime_tags(bookbuilding_start)'tan yeniden üretilir
    (tests/test_faz6_oot.py::test_real_cohort_validates_and_reproduces_from_code); kasa girdileri bu testte okunmaz."""
    members = {r["ticker"]: r for r in reg.cohort_members(cohort)}
    for r in v2.rows:
        assert r.alloc_regime == dm.alloc_regime(r.alloc_regime_date)
        if r.cohort == "OOT_OPEN":
            assert reg.is_open(members[r.ticker]["vault"])
            assert r.alloc_regime == reg.parse_regime_tags(members[r.ticker]["regime_tags"])["ALLOC_REGIME"]
        else:
            assert r.alloc_regime == "EQUAL_DIST_20230330"
    assert Counter(r.alloc_regime for r in v2.rows if r.cohort == "OOT_OPEN") == \
        {"EQUAL_DIST_20230330": 15, "PRE_20211111": 25, "THRESH100_20211111": 31}


def test_alloc_regime_function_equivalent_to_registry_rule():
    base = dict(first_trading_date="2021-06-01", market="ANA", sale_method="ON_EXCHANGE", ipo_price_tl="10", ipo_price_try="10",
                sessions=[(date(2021, 6, 1) + timedelta(days=i)).isoformat() for i in range(20)], vault="OPEN")
    d = date(2019, 1, 1)
    while d <= date(2026, 12, 31):
        s = d.isoformat()
        assert dm.alloc_regime(s) == reg.compute_regime_tags(bookbuilding_start=s, **base)["ALLOC_REGIME"], s
        d += timedelta(days=1)


def test_first_trading_day_reading_changes_label_in_4_never_r(cohort):
    """SPEC_DEVIATIONS J: şartnamenin `alloc_regime(first_trading_date)` okuması kohort etiketinden 4 üyede (hepsi 2021-11-11
    sınırı) ayrışır; ikili r (modelin tek girdisi) 135/135 aynı. Yalnız kohort dosyası okunur."""
    from borsai.predict_hazard import regime_value

    mem = reg.cohort_members(cohort)
    labels = [reg.parse_regime_tags(r["regime_tags"])["ALLOC_REGIME"] for r in mem]
    by_ftd = [dm.alloc_regime(r["first_trading_date"]) for r in mem]
    assert len(mem) == 135
    diff = [(a, b) for a, b in zip(labels, by_ftd) if a != b]
    assert len(diff) == 4 and set(diff) == {("PRE_20211111", "THRESH100_20211111")}
    assert all(regime_value(a) == regime_value(b) for a, b in zip(labels, by_ftd))


def test_no_sealed_code_in_v2_files(cohort):
    sealed = sorted(r["ticker"] for r in reg.cohort_members(cohort) if r["vault"] == reg.VAULT_SEALED)
    n_sealed = len(sealed)                                                          # yerel değişken: hata çıktısı kod basmaz
    assert n_sealed == 64
    pattern = re.compile(r"\b(" + "|".join(sealed) + r")\b")
    for p in (dm.TABLE_V2_PATH, dm.VERSION_V2_PATH, ROOT / dm.BUILDER_V2_REL):
        n = len(set(pattern.findall(p.read_text(encoding="utf-8"))))
        assert n == 0, (p.name, n)
    opn = sorted(r["ticker"] for r in reg.cohort_members(cohort) if reg.is_open(r["vault"]))
    text = dm.VERSION_V2_PATH.read_text(encoding="utf-8") + (ROOT / dm.BUILDER_V2_REL).read_text(encoding="utf-8")
    assert not re.search(r"\b(" + "|".join(opn) + r")\b", text)                    # açık kodlar yalnız tabloda


@pytest.mark.requires_raw_sources
def test_builder_reproduces_table_and_version():
    spec = importlib.util.spec_from_file_location("build_v2", ROOT / dm.BUILDER_V2_REL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    table, version, n = mod.build()
    assert n == 170 and table == dm.TABLE_V2_PATH.read_bytes() and version == dm.VERSION_V2_PATH.read_bytes()


def test_loader_detects_tampering(tmp_path, monkeypatch):
    raw = dm.TABLE_V2_PATH.read_bytes()
    t = tmp_path / "training_table_v2.csv"
    t.write_bytes(raw.replace(b"EQUAL_DIST_20230330", b"PRE_20211111", 1))
    monkeypatch.setattr(dm, "TABLE_V2_PATH", t)
    with pytest.raises(dm.DataIntegrityError):
        dm.load_dataset_v2()                                                      # sha
    version = json.loads(dm.VERSION_V2_PATH.read_text(encoding="utf-8"))
    from borsai.provenance import pretty_json_bytes, sha256_bytes

    version.update(sha256=sha256_bytes(t.read_bytes()), bytes=len(t.read_bytes()))
    v = tmp_path / "data_version_v2.json"
    v.write_bytes(pretty_json_bytes(version))
    monkeypatch.setattr(dm, "VERSION_V2_PATH", v)
    with pytest.raises(dm.DataIntegrityError, match="yeniden üretilemiyor"):
        dm.load_dataset_v2()                                                      # sha tutsa da satır koddan üretilemiyor


def test_pp_counts_h99_open_pooled_and_groups(v2):
    """§11-3: H99 f3'lü 506/83 (v0 ile aynı); açık f3'lü 374/59; havuz 880/142; grup olay/risk 25/165, 31/258, 86/457."""
    f3 = [r for r in v2.rows if r.inputs["total_demand_multiple"] is not None]
    h99 = sv.pp_table([sv.unit_of(r) for r in f3 if r.cohort == "H99"])
    oot = sv.pp_table([sv.unit_of(r) for r in f3 if r.cohort == "OOT_OPEN"])
    pool = sv.pp_table([sv.unit_of(r) for r in f3])
    assert (len(h99), sum(r.event for r in h99)) == (506, 83)
    assert (len(oot), sum(r.event for r in oot)) == (374, 59)
    assert (len(pool), sum(r.event for r in pool)) == (880, 142) and len(f3) == 165
    events, risk = sv.group_counts(pool)
    assert list(zip(events, risk)) == [(25, 165), (31, 258), (86, 457)]
    assert Counter(r.cohort for r in f3) == POOLED_TRAINING["cohort_counts"]


def test_v2_sessions_from_two_sources(v2):
    h99 = dm.load_dataset().by_ticker()
    for r in v2.rows:
        if r.cohort == "H99":
            assert r.session_dates == h99[r.ticker].session_dates and r.inputs == h99[r.ticker].inputs
        assert len(r.session_dates) == 10 and list(r.session_dates) == sorted(set(r.session_dates))


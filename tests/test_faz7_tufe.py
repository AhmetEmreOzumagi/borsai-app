"""Faz 7: TÜİK TÜFE dosyası ve T − 2 kuralı (SPEC_HAZARD_V1 §3.2, §9, §11-2, §11-5; KARARLAR K3)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import random
from decimal import Decimal
from fractions import Fraction

import pytest

from borsai import backtest as bt
from borsai import predict_hazard as ph
from borsai import tufe
from borsai.data import load_dataset, load_dataset_v2
from borsai.provenance import ROOT, sha256_file
from borsai.specs import DEFLATOR, FAZ7_MODEL_SPECS, TUFE_PIN

TUIK = ROOT / "data" / "raw" / "tuik"


@pytest.fixture(scope="module")
def table():
    return tufe.load()


def _builder():
    spec = importlib.util.spec_from_file_location("build_tufe_csv", TUIK / "build_tufe_csv.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_months_contiguous_from_2019_11_and_base_year(table):
    months = table.months
    assert months[0] == "2019-11" == tufe.FIRST_MONTH and months[-1] == "2026-08" and len(months) == 82
    assert all(tufe.month_add(a, 1) == b for a, b in zip(months, months[1:]))
    avg = sum(Fraction(table.rows[f"2025-{m:02d}"].index) for m in range(1, 13)) / 12
    assert abs(avg - 100) <= Fraction(5, 100)                                      # 2025=100 temeli
    for m, r in table.rows.items():
        assert r.release_date[:7] == tufe.month_add(m, 1) and int(r.release_date[8:]) >= 3, m
        assert r.source_sha256 == json.loads((TUIK / "tufe_degisim_oranlari_bulten_58290.source.json").read_text())["sha256"]


def test_file_sha_pinned_in_specs_and_provenance(table):
    assert table.file_sha256 == TUFE_PIN["prefix_sha256"] == DEFLATOR["file_sha256"]
    assert table.prefix_sha256(TUFE_PIN["through_month"]) == TUFE_PIN["prefix_sha256"]
    for m in ("ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled"):
        assert FAZ7_MODEL_SPECS[m]["deflator"] == DEFLATOR
    assert "deflator" not in FAZ7_MODEL_SPECS["ceiling_hazard_v1_clip"]
    prov = (ROOT / "docs" / "PROVENANCE.md").read_text(encoding="utf-8")
    assert "data/raw/tuik/tufe_genel_2025_100.csv" in prov and table.file_sha256 in prov
    assert "6f7ee8e4ce7e8a7ac79a332db375c4a3179d02162a5d72f684d352aa6c70ff86" in prov


def test_month_for_examples():
    """§11-2 örnekleri + yıl sınırı."""
    assert tufe.month_for("2026-09-02") == "2026-07"
    assert tufe.month_for("2026-09-25") == "2026-07"
    assert tufe.month_for("2026-10-01") == "2026-08"
    assert tufe.month_for("2020-01-06") == "2019-11"
    assert tufe.month_for("2021-02-28") == "2020-12"


def test_index_for_is_pit_on_all_170_rows(table):
    ds = load_dataset_v2()
    assert len(ds.rows) == 170
    for r in ds.rows:
        t = tufe.index_for(r.first_trading_date, table)
        assert t["release_date"] < r.first_trading_date, r.first_trading_date
        assert (t["month"], t["index"]) == (r.tufe_month, r.tufe_index) and t["rule"] == "T_MONTH_MINUS_2"


def test_refusals_missing_not_pit_and_file_mismatch(table):
    with pytest.raises(tufe.TufeRefusal) as e:
        tufe.index_for("2019-12-31", table)                                        # 2019-10 dosyada yok
    assert e.value.code == tufe.TUFE_MISSING and e.value.month == "2019-10"
    with pytest.raises(tufe.TufeRefusal) as e:
        tufe.index_for("2026-11-02", table)                                        # 2026-09 henüz yok
    assert e.value.code == tufe.TUFE_MISSING
    late = dict(table.rows)
    late["2026-06"] = tufe.TufeRow(**{**late["2026-06"].__dict__, "release_date": "2026-08-10"})
    with pytest.raises(tufe.TufeRefusal) as e:                                     # bekçi: kural gereği olamaz, elle kurulan tablo
        tufe.index_for("2026-08-06", tufe.TufeTable(rows=late, raw=table.raw, file_sha256=table.file_sha256, path=table.path))
    assert e.value.code == tufe.TUFE_NOT_PIT


def test_release_on_T_itself_is_not_pit(table):
    """Fable denetimi B2 (mutasyon c2: bekçi `release_date ≤ T`'yi kabul ederse yeşil kalıyordu): yayım günü T'nin kendisi olan
    satır da RET TUFE_NOT_PIT (bülten 10:00'da, ilk işlem seansı 10:00'da açılır; §3.2 "release_date < T" kesin)."""
    same = dict(table.rows)
    same["2026-06"] = tufe.TufeRow(**{**same["2026-06"].__dict__, "release_date": "2026-08-06"})
    tt = tufe.TufeTable(rows=same, raw=table.raw, file_sha256=table.file_sha256, path=table.path)
    with pytest.raises(tufe.TufeRefusal) as e:
        tufe.index_for("2026-08-06", tt)                                           # T − 2 = 2026-06, yayım = T
    assert e.value.code == tufe.TUFE_NOT_PIT and e.value.month == "2026-06"
    assert tufe.index_for("2026-08-07", tt)["month"] == "2026-06"                  # bir gün sonra PIT


def test_append_keeps_pin_changed_old_row_breaks_it(table):
    appended = table.raw + b"2026-09,136.10,2026-10-05,99999,https://veriportali.tuik.gov.tr/x," + b"a" * 64 + b"\n"
    t2 = tufe.parse(appended)
    assert t2.months[-1] == "2026-09" and t2.prefix_sha256("2026-08") == TUFE_PIN["prefix_sha256"]
    tufe.verify_pin(t2, TUFE_PIN)
    changed = table.raw.replace(b"2019-11,13.736052,", b"2019-11,13.736053,")
    assert changed != table.raw
    with pytest.raises(tufe.TufeRefusal) as e:
        tufe.verify_pin(tufe.parse(changed), TUFE_PIN)
    assert e.value.code == tufe.TUFE_FILE_MISMATCH
    with pytest.raises(tufe.TufeError):                                            # ay atlaması (süreklilik)
        tufe.parse(table.raw + b"2026-10,1,2026-11-03,1,https://x," + b"a" * 64 + b"\n")


def test_builder_reproduces_csv_from_pinned_xls():
    mod = _builder()
    assert mod.render(mod.build_rows()) == (TUIK / "tufe_genel_2025_100.csv").read_bytes()
    assert sha256_file(TUIK / "tufe_degisim_oranlari_bulten_58290.xls") == \
        "6f7ee8e4ce7e8a7ac79a332db375c4a3179d02162a5d72f684d352aa6c70ff86"
    levels, mom = mod.table_levels((TUIK / "tufe_degisim_oranlari_bulten_58290.xls").read_bytes())
    assert levels["2026-08"] == 134.75 and levels["2019-11"] == 13.736052 and mom["2026-08"] == 1.84
    bulletins = mod.read_bulletins()
    assert [b["month"] for b in bulletins] == tufe.load().months
    assert all(b["bulletin_url"].startswith("https://veriportali.tuik.gov.tr/tr/press/") for b in bulletins)


def test_real_size_scale_invariance():
    """§11-5: büyüklük ve endeks aynı k katıyla çarpılınca f1r değişmez (|Δ| ≤ 1e-12; burada kesin eşit)."""
    rng = random.Random(5)
    for _ in range(500):
        size = Decimal(rng.randint(10**6, 10**11)) / Decimal(rng.choice([1, 100]))
        idx = Decimal(f"{rng.uniform(5, 200):.6f}")
        k = Decimal(rng.choice(["2", "3.5", "10", "0.25", "7.125"]))
        a, b = ph.real_size(size, idx), ph.real_size(size * k, idx * k)
        assert a == b and abs(float(a) - float(b)) <= 1e-12


def test_v1_real_f1r_on_97_reproduced_with_index_for(table):
    """§11-5: eğitimdeki her arz için tufe_month = T'nin m − 2'si; v1_real'in 97 arzdaki f1r'leri tufe.index_for ile üretilir."""
    ds = load_dataset()
    rows = [r for r in ds.rows if r.inputs["total_demand_multiple"] is not None]
    assert len(rows) == 97
    raw, info = bt.v1_raw_features(FAZ7_MODEL_SPECS["ceiling_hazard_v1_real"], rows)
    from decimal import ROUND_HALF_EVEN, Context, localcontext

    from borsai.features import compute_features

    for r in rows:
        t = tufe.index_for(r.first_trading_date, table)
        assert info[r.ticker]["month"] == tufe.month_for(r.first_trading_date) == t["month"]
        f1 = compute_features(**r.feature_inputs()).f1
        with localcontext(Context(prec=60, rounding=ROUND_HALF_EVEN)):
            direct = f1 / (Decimal(t["index"]) / 100)
        assert raw[r.ticker]["f1r"] == ph.real_size(f1, t["index"]) == direct


# ---------------------------------------------------------------- aylık ekleme yolu (dondurma görevi K5; ağ yok, gerçek ay eklenmez)

FAKE_XLS = b"synthetic stand-in for the 2026-09 bulletin table (not an xls)"
FAKE_URL = "https://veriportali.tuik.gov.tr/api/tr/data/downloads?t=t&pid=99999&p=synthetic"


def _tuik_copy(tmp_path):
    d = tmp_path / "tuik"
    d.mkdir()
    for name in ("tufe_degisim_oranlari_bulten_58290.xls", "tufe_degisim_oranlari_bulten_58290.source.json",
                 "tufe_bultenleri.csv", "tufe_genel_2025_100.csv"):
        (d / name).write_bytes((TUIK / name).read_bytes())
    return d


def _fake_reader(mod, monkeypatch, **overrides):
    """Sentetik ay tablosu: taban tablonun bütün düzeyleri + 2026-09 = 136.1 (aylık %1.00); `overrides` eski ayları değiştirir.
    Gerçek BIFF8 dosyası üretmek yerine okuyucu yalnız sentetik baytlar için değiştirilir (taban tablo gerçek okuyucuyla)."""
    real = mod.table_levels
    base_levels, base_mom = real((TUIK / "tufe_degisim_oranlari_bulten_58290.xls").read_bytes())
    levels = {**base_levels, "2026-09": 136.1, **overrides}
    mom = {**base_mom, "2026-09": round((136.1 / base_levels["2026-08"] - 1) * 100, 2)}
    monkeypatch.setattr(mod, "table_levels", lambda data: (dict(levels), dict(mom)) if data == FAKE_XLS else real(data))


def _append(mod, d, tmp_path, **kw):
    xls = tmp_path / "indirilen.xls"
    xls.write_bytes(FAKE_XLS)
    args = dict(month="2026-09", bulletin_id="99999", release="2026-10-05T10:00:00+03:00", xls=xls, download_url=FAKE_URL,
                sha256=hashlib.sha256(FAKE_XLS).hexdigest(), fetched_at_utc="2026-10-05T08:00:00Z", here=d)
    args.update(kw)
    return mod.append_month(**args)


def test_monthly_append_adds_one_row_and_keeps_the_pin(tmp_path, monkeypatch):
    """§3.2 "ay eklemek veri sürümünü değiştirmez": ekleme komutu dosyanın sonuna TEK satır yazar (eski baytlar aynen), pin
    (`TUFE_PIN`, 2026-08'e kadarki önek) tutar, yeni ay `index_for`'da görünür (T = 2026-11-02 önce TUFE_MISSING idi), satır ayın
    kendi bülteninin tablosunu (url, sha) adlandırır ve tam derleme (`--check`) yeni dosyayı bayt bayt yeniden üretir."""
    mod = _builder()
    d = _tuik_copy(tmp_path)
    _fake_reader(mod, monkeypatch)
    old = (d / "tufe_genel_2025_100.csv").read_bytes()
    with pytest.raises(tufe.TufeRefusal):
        tufe.index_for("2026-11-02", tufe.parse(old))
    res = _append(mod, d, tmp_path)
    new = (d / "tufe_genel_2025_100.csv").read_bytes()
    assert new.startswith(old) and new.count(b"\n") == old.count(b"\n") + 1
    assert new[len(old):] == (b"2026-09,136.1,2026-10-05,99999," + FAKE_URL.encode() + b","
                              + hashlib.sha256(FAKE_XLS).hexdigest().encode() + b"\n")
    assert res["month"] == "2026-09" and res["file_sha256"] == hashlib.sha256(new).hexdigest()
    t2 = tufe.parse(new)
    tufe.verify_pin(t2, TUFE_PIN)
    assert t2.prefix_sha256("2026-08") == TUFE_PIN["prefix_sha256"]
    got = tufe.index_for("2026-11-02", t2)
    assert (got["month"], got["index"], got["release_date"]) == ("2026-09", "136.1", "2026-10-05")
    assert (d / "tufe_bultenleri.csv").read_bytes() == (TUIK / "tufe_bultenleri.csv").read_bytes() + \
        "2026-09,99999,Eylül 2026,2026-10-05T10:00:00+03:00,https://veriportali.tuik.gov.tr/tr/press/99999\n".encode()
    src = json.loads((d / "tufe_degisim_oranlari_bulten_99999.source.json").read_text(encoding="utf-8"))
    assert src["sha256"] == hashlib.sha256(FAKE_XLS).hexdigest() and src["download_url"] == FAKE_URL and src["table_base"] == "[2025=100]"
    assert (d / "tufe_degisim_oranlari_bulten_99999.xls").read_bytes() == FAKE_XLS
    assert mod.render(mod.build_rows(d)) == new and mod.main(["--check", "--dir", str(d)]) == 0
    with pytest.raises(mod.SourceInvariantError):                                  # aynı ay ikinci kez eklenmez
        _append(mod, d, tmp_path)


@pytest.mark.parametrize("case", ["revision", "skip_month", "sha_mismatch", "release_before_3rd", "table_ends_elsewhere"])
def test_monthly_append_refuses_and_leaves_files_unchanged(case, tmp_path, monkeypatch):
    """Eski bir ayın değeri değişmişse (revizyon, temel yıl, zincirleme: yeni veri sürümü = yeni model_id), ay atlanıyorsa,
    indirilen dosyanın sha'sı verilenle tutmuyorsa, yayım ayın 3'ünden önceyse ya da tablo o ayda bitmiyorsa komut durur ve
    hiçbir dosya değişmez."""
    mod = _builder()
    d = _tuik_copy(tmp_path)
    _fake_reader(mod, monkeypatch, **({"2019-11": 13.736053} if case == "revision" else
                                      {"2026-10": 137.0} if case == "table_ends_elsewhere" else {}))
    before = {p.name: p.read_bytes() for p in d.iterdir()}
    kw = {"skip_month": {"month": "2026-10"}, "sha_mismatch": {"sha256": "0" * 64},
          "release_before_3rd": {"release": "2026-10-02T10:00:00+03:00"}}.get(case, {})
    with pytest.raises(mod.SourceInvariantError):
        _append(mod, d, tmp_path, **kw)
    assert {p.name: p.read_bytes() for p in d.iterdir()} == before


def test_append_command_documented_in_provenance():
    """Kayıt ön koşulunun iletisindeki komut (`tufe.APPEND_COMMAND`) PROVENANCE §11'de aynen yazılı; argümanları üreticinin
    CLI'sıyla aynı."""
    prov = (ROOT / "docs" / "PROVENANCE.md").read_text(encoding="utf-8")
    assert tufe.append_command("<YYYY-MM>") in prov
    mod = _builder()
    for flag in ("--append-month", "--bulletin-id", "--release", "--xls", "--download-url", "--sha256"):
        assert flag in tufe.APPEND_COMMAND and flag in mod.__doc__ + open(mod.__file__, encoding="utf-8").read()

#!/usr/bin/env python3
"""Rejim etiketlerinin (şartname §7; SPEC_DEVIATIONS I6–I9, I18, I21) BAĞIMSIZ yeniden hesabı: `borsai` import edilmez.
Girdiler: kohort dosyası (yalnız ticker/first_trading_date/regime_tags/vault sütunları karşılaştırma için), evren listesi
(pazar ve KAP satış yöntemi; S0 eki), girdi belgeleri (ipo_price_tl, ipo_price_try, bookbuilding_start), pinli XU100 serisi
(seans günleri: takvim_2020_2023.md "XU100 gün kümesi = seans kümesi"), donmuş tavan yolu JSON'unun adım tablosu (veri).
Kural tarihleri kurallar_arastirma.md §1, §3, §6–7, §10'dan; limit yolu SPEC_CEILING_PATH_V0 §2 lafzından. Sonuç verisi okunmaz."""
import csv
import json
import sys
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal, getcontext
from pathlib import Path

getcontext().prec = 60
ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]
cohort = [r for r in csv.DictReader((ROOT / "registry/oot/cohort_pre_h99.csv").open(encoding="utf-8", newline=""))
          if r["status"] == "MEMBER"]
universe = {r["ticker"]: r for r in csv.DictReader((ROOT / "docs/specs_faz6/ekler/evren_listesi.csv").open(encoding="utf-8"))}
xu = json.load((ROOT / "data/raw/xu100/xu100_graphic_20260922.json").open())["data"]
SESSIONS = sorted({r["hisTs"] for r in xu if r["indexName"] == "XU100" and r["hisTs"] >= "2020-01-01"})
JSON_TABLE = [(None if e["below"] is None else Decimal(e["below"]), Decimal(e["tick"]))
              for e in json.load((ROOT / "models/ceiling_path_v0.json").open())["limit_path"]["tick_table"]]
T2015 = [(Decimal(20), Decimal("0.01")), (Decimal(50), Decimal("0.02")), (Decimal(100), Decimal("0.05")), (None, Decimal("0.10"))]
MARGIN = Decimal("0.10")
MARGIN_CHANGE = "2020-03-13"          # Duyuru 2020/20: Yıldız ve Ana %10 (kurallar §1); öncesi Yıldız %20, Ana G1 %20 / G2 %15
TICK_T2023 = "2023-11-06"             # Duyuru 2023/19412 (kurallar §3)
SHORT_BANS = [("2020-03-02", None, "SHORT_SELL_BAN_2020_END_NOT_FOUND"), ("2023-02-06", None, "SHORT_SELL_BAN")]   # §10
ALLOC = [("2021-11-11", "THRESH100_20211111"), ("2023-03-30", "EQUAL_DIST_20230330")]                               # §6–7
EXPOSED = {"TARKM": "EXPOSED_ARCHIVE", "GIPTA": "EXPOSED_ARCHIVE", "ADGYO": "EXPOSED_ARCHIVE", "REEDR": "EXPOSED_ARCHIVE",
           "PNLSN": "EXPOSED_CODEX"}
ARCHIVE_FIRST = "2023-09-22"


def tick(x, table):
    for lim, s in table:
        if lim is None or x < lim:
            return s
    raise AssertionError


def limit_path(P, table, days=10):
    """SPEC_CEILING_PATH_V0 §2: snap(P) = round_half_up(P/adim(P))·adim(P); C_k = floor(C_{k−1}·1.10/adim(C_{k−1}·1.10))·adim(...)."""
    s = tick(P, table)
    b = (P / s).to_integral_value(rounding=ROUND_HALF_UP) * s
    snapped, C = b, []
    for _ in range(days):
        y = b * (1 + MARGIN)
        st = tick(y, table)
        b = (y / st).to_integral_value(rounding=ROUND_FLOOR) * st
        C.append(b)
    return snapped, tuple(C)


def parse_price(v):
    """(tek Decimal | None, aralık mı)."""
    if v in (None, ""):
        return None, False
    t = str(v).strip()
    for sep in ("-", "–", "—"):
        parts = t[1:].split(sep, 1)
        if len(parts) == 2:
            try:
                Decimal((t[0] + parts[0]).strip()), Decimal(parts[1].strip())
                return None, True
            except Exception:
                pass
    return Decimal(t), False


def tags_for(r):
    u = universe[r["ticker"]]
    doc = json.load((ROOT / "registry/oot/inputs" / f"{r['ticker']}.json").open(encoding="utf-8"))
    f = doc["fields"]
    ftd, market, sale = r["first_trading_date"], u["market"], u["sale_method_kap"]
    assert f["first_trading_date"]["value"] == ftd == u["first_trading_date"]
    tags = {"MARKET": market}
    if sale == "ON_EXCHANGE":
        tags["SALE_ON_EXCHANGE"] = True
    p_try, is_range = parse_price(f["ipo_price_try"]["value"])
    if is_range:
        tags["PRICE_RANGE_BOOKBUILD"] = True
    epoch = "T2023" if ftd >= TICK_T2023 else "T2015"
    tags["TICK_TABLE_EPOCH"] = epoch
    prices = [Decimal(f["ipo_price_tl"]["value"])] + ([p_try] if p_try is not None else [])
    table = T2015 if epoch == "T2015" else JSON_TABLE
    if any(limit_path(p, table) != limit_path(p, JSON_TABLE) for p in prices):
        tags["TICK_TABLE_MISMATCH"] = True
    pre = ftd < MARGIN_CHANGE
    tags["MARGIN_RULE"] = "PRE_20200313" if pre else "POST_20200313"
    if pre and market in ("YILDIZ", "ANA"):
        tags["MARGIN_NOT_10PCT"] = True
    window = [s for s in SESSIONS if s >= ftd][:10]
    assert len(window) == 10
    for start, end, name in SHORT_BANS:
        if window[-1] >= start and (end is None or window[0] <= end):
            tags[name] = True
    bb = f["bookbuilding_start"]["value"]
    tags["ALLOC_REGIME"] = "PRE_20211111"
    for start, name in ALLOC:
        if bb >= start:
            tags["ALLOC_REGIME"] = name
    if r["ticker"] in EXPOSED:
        tags[EXPOSED[r["ticker"]]] = True
    text = "|".join(sorted(k if v is True else f"{k}={v}" for k, v in tags.items()))
    return text, tags, window, prices


match, mism, counts = 0, [], {}
archive_calc = set()
for r in cohort:
    text, tags, window, prices = tags_for(r)
    if window[-1] >= ARCHIVE_FIRST:
        archive_calc.add(r["ticker"])
    if text == r["regime_tags"]:
        match += 1
    else:
        mism.append((r["ticker"], r["regime_tags"], text))
    for k, v in tags.items():
        counts[k if v is True else f"{k}={v}"] = counts.get(k if v is True else f"{k}={v}", 0) + 1
print(f"üye {len(cohort)}; regime_tags birebir eşleşme: {match}/{len(cohort)}")
for m in mism:
    print("  FARK", m)
print("etiket sayıları (bağımsız hesap):")
for k in sorted(counts):
    print(f"  {k}: {counts[k]}")
print("EXPOSED_ARCHIVE takvimden (D_10 ≥ 2023-09-22):", sorted(archive_calc),
      "== D2 listesi:", archive_calc == {t for t, v in EXPOSED.items() if v == "EXPOSED_ARCHIVE"})
# I8 duyarlılık: ALLOC D_1'e göre okunsaydı kaç üye değişirdi?
n_diff = 0
for r in cohort:
    f = json.load((ROOT / "registry/oot/inputs" / f"{r['ticker']}.json").open(encoding="utf-8"))["fields"]
    a_bb = "PRE_20211111"
    a_d1 = "PRE_20211111"
    for start, name in ALLOC:
        if f["bookbuilding_start"]["value"] >= start:
            a_bb = name
        if r["first_trading_date"] >= start:
            a_d1 = name
    n_diff += a_bb != a_d1
print("I8: ALLOC_REGIME talep toplama başlangıcı yerine D_1'e göre okunsaydı farklı çıkan üye:", n_diff)
# I7 duyarlılık: TICK mismatch yalnız ≥ 100 TL fiyatlarda mı? (eşik: yol 250'yi geçiyor)
hi = [r["ticker"] for r in cohort if Decimal(json.load((ROOT / "registry/oot/inputs" / f"{r['ticker']}.json").open())["fields"]["ipo_price_tl"]["value"]) >= 100]
print("arz fiyatı ≥ 100 TL olan üye sayısı:", len(hi), "| TICK_TABLE_MISMATCH sayısı:", counts.get("TICK_TABLE_MISMATCH", 0))
print("borsai sys.modules içinde mi:", "borsai" in sys.modules)

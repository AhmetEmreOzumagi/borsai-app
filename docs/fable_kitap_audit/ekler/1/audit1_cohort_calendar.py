"""KITAP_AUDIT_1 Adım 5: H99 kohortu, MASTER/PROV/READY/SESSIONS/TARGETS tutarlılığı, D_h eşlemesi ve takvim A/B/C iddiaları.
borsai import edilmez. Yalnız stdlib."""
import csv, json, hashlib
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data" / "raw"
def rd(p, enc="utf-8-sig"):
    with open(p, encoding=enc, newline="") as fh:
        return list(csv.DictReader(fh))
out = []
P = lambda *a: out.append(" ".join(str(x) for x in a))

mem = rd(RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_membership.csv")
master = rd(RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv")
prov = rd(RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_provenance.csv")
ready = rd(RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_feature_readiness.csv")
sess = rd(RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv")
targ = rd(RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv")
fprov = rd(RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_field_provenance.csv")
pb = rd(RAW / "PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv")

# --- §3.3.1 üyelik
P("[ÖLÇTÜM] membership satır", len(mem), "sütun", len(mem[0]))
for c in ("historical_anchor", "historical_anchor_date", "original_target_universe_size", "current_frozen_cohort_size", "known_membership_gap_count", "membership_gap_status"):
    P("   ", c, dict(Counter(r[c] for r in mem)))
P("[ÖLÇTÜM] membership_source:", dict(Counter(r["membership_source"] for r in mem)))
can20 = sorted(r["ticker"] for r in mem if r["membership_source"] == "CANONICAL20_PROTECTED_INPUT")
ords = sorted(int(r["membership_ordinal"]) for r in mem if r["membership_source"] == "CANONICAL20_PROTECTED_INPUT")
P("[ÖLÇTÜM] kanonik 20:", can20, "| sıra no:", ords[0], "…", ords[-1])
ftd = {r["ticker"]: r["first_trading_date"] for r in mem}
P("[ÖLÇTÜM] kanonik 20 ilk işlem aralığı:", min(ftd[t] for t in can20), "…", max(ftd[t] for t in can20))
ext = [r for r in mem if r["membership_source"] != "CANONICAL20_PROTECTED_INPUT"]
P("[ÖLÇTÜM] dış kanıt grubu n =", len(ext), "| QUICK'ten sonra ilk işlem:", sum(r["first_trading_date"] > "2026-08-06" for r in ext),
  "| SOHOE kaynağı:", next(r["membership_source"] for r in mem if r["ticker"] == "SOHOE"), ftd.get("SOHOE"))
dates = sorted(ftd.values())
P("[ÖLÇTÜM] ilk işlem günleri:", dates[0], "(", min(ftd, key=ftd.get), ")…", dates[-1], "| farklı gün:", len(set(dates)),
  "| ikişer arz günleri:", sorted(d for d, c in Counter(dates).items() if c > 1), "| yıl:", dict(sorted(Counter(d[:4] for d in dates).items())))
# membership ile master ftd aynı mı
mftd = {r["ticker"]: r["first_trading_date"] for r in master}
P("[ÖLÇTÜM] membership ↔ MASTER ilk işlem günü farkı:", sum(mftd[t] != ftd[t] for t in ftd), "| ticker kümeleri eşit:", set(mftd) == set(ftd) == {r["ticker"] for r in prov} == {r["ticker"] for r in ready})

# --- §3.3.2 PROV/MASTER alanları
P("[ÖLÇTÜM] PROV point_in_time_status:", dict(Counter(r["point_in_time_status"] for r in prov)), "| conflict_status:", dict(Counter(r["conflict_status"] for r in prov)),
  "| superseded_result_status:", dict(Counter(r["superseded_result_status"] for r in prov)))
P("[ÖLÇTÜM] READY pit == PROV pit farkı:", sum(a["point_in_time_status"] != b["point_in_time_status"] for a, b in zip(sorted(ready, key=lambda r: r["ticker"]), sorted(prov, key=lambda r: r["ticker"]))))
P("[ÖLÇTÜM] MASTER data_completeness_status:", dict(Counter(r["data_completeness_status"] for r in master)),
  "| DATA_NOT_FOUND sayısı: distribution_method", sum(r["distribution_method"] == "DATA_NOT_FOUND" for r in master),
  "lead_broker", sum(r["lead_broker"] == "DATA_NOT_FOUND" for r in master), "sector", sum(r["sector"] == "DATA_NOT_FOUND" for r in master))
P("[ÖLÇTÜM] MASTER sütun sayısı", len(master[0]), "PROV", len(prov[0]), "READY", len(ready[0]), "SESSIONS", len(sess[0]), "TARGETS", len(targ[0]), "field_prov", len(fprov), "×", len(fprov[0]), "PB", len(pb), "×", len(pb[0]))
P("[ÖLÇTÜM] field_provenance: (arz,seans) çifti", len({(r.get("ticker"), r.get("session_number")) for r in fprov}), "| alan adı sayısı", len({r.get("field_name") for r in fprov}), "| sütunlar:", list(fprov[0].keys())[:6])

# --- Takvim A
calA = rd(RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv")
daysA = [r["calendar_date"] for r in calA]
consec = all(date.fromisoformat(b) - date.fromisoformat(a) == timedelta(days=1) for a, b in zip(daysA, daysA[1:]))
P("[ÖLÇTÜM] Takvim A:", daysA[0], "…", daysA[-1], "gün", len(daysA), "ardışık", consec, "| status:", dict(Counter(r["session_status"] for r in calA)),
  "| counts:", dict(Counter((r["session_status"], r["counts_as_official_session"]) for r in calA)))
sessA = [r["calendar_date"] for r in calA if r["counts_as_official_session"] == "TRUE"]
halfA = [r["calendar_date"] for r in calA if r["session_status"] == "OPEN_HALF_DAY"]
usedA = {r["calendar_date"] for r in calA if r["used_by_historical99"] == "TRUE"}
sess_dates = {r["target_session_date"] for r in sess}
P("[ÖLÇTÜM] A seans", len(sessA), "yarım gün", halfA, "| used_by_historical99 TRUE", len(usedA), "== SESSIONS farklı tarih", len(sess_dates), usedA == sess_dates,
  "| semantics:", dict(Counter(r["session_semantics_version"] for r in calA)), "| kaynak sha/yıl:", {y: {r["calendar_source_sha256"][:8] for r in calA if r["calendar_evidence_year"] == y} for y in sorted({r["calendar_evidence_year"] for r in calA})})
# D_h eşlemesi: Takvim A'dan say
by = {}
for r in sess: by.setdefault(r["ticker"], {})[int(r["session_number"])] = r["target_session_date"]
import bisect
dh_mism = []
for t, d in by.items():
    i = bisect.bisect_left(sessA, mftd[t])
    exp = sessA[i:i + 10]
    got = [d[k] for k in range(1, 11)]
    if exp != got: dh_mism.append((t, exp[:2], got[:2]))
P("[ÖLÇTÜM] D_h = takvim A'dan n'inci seans; SESSIONS ile uyuşmayan arz:", len(dh_mism), dh_mism[:3])
tg = {(r["ticker"], r["horizon"]): r["target_session_date"] for r in targ}
P("[ÖLÇTÜM] TARGETS target_session_date ≠ SESSIONS:", sum(tg[(t, f"D{h}")] != by[t][h] for t in by for h in (1, 3, 5, 10)),
  "| en geç hedef seansı:", max(tg.values()), "| D1 == MASTER ftd farkı:", sum(by[t][1] != mftd[t] for t in by))

# --- Takvim B ve uzatma
calB = rd(RAW / "v2_market20_official_pay_calendar_evidence_r4.csv", "utf-8")
daysB = [r["calendar_date"] for r in calB]
sessB = [r["calendar_date"] for r in calB if r["counts_as_official_session"] == "YES"]
P("[ÖLÇTÜM] Takvim B:", daysB[0], "…", daysB[-1], "gün", len(daysB), "seans", len(sessB), "yarım", sum(r["half_day"] == "YES" for r in calB),
  "ardışık", all(date.fromisoformat(b) - date.fromisoformat(a) == timedelta(days=1) for a, b in zip(daysB, daysB[1:])),
  "| verification:", dict(Counter(r["verification_status"] for r in calB)))
A_map = {r["calendar_date"]: r["counts_as_official_session"] == "TRUE" for r in calA}
B_map = {r["calendar_date"]: r["counts_as_official_session"] == "YES" for r in calB}
P("[ÖLÇTÜM] A ∩ B ortak gün", len(set(A_map) & set(B_map)), "| seans bayrağı farklı:", sum(A_map[d] != B_map[d] for d in set(A_map) & set(B_map)),
  "| A yarım günler B'de yarım:", all(next(r["half_day"] for r in calB if r["calendar_date"] == d) == "YES" for d in halfA),
  "| B yarım günler:", [r["calendar_date"] for r in calB if r["half_day"] == "YES"])
ext_ = rd(RAW / "pay_calendar_b_extension_20260820_20261231.csv", "utf-8")
P("[ÖLÇTÜM] B uzatma:", ext_[0]["calendar_date"], "…", ext_[-1]["calendar_date"], "gün", len(ext_), "seans", sum(r["counts_as_official_session"] == "YES" for r in ext_),
  "yarım", [r["calendar_date"] for r in ext_ if r["half_day"] == "YES"], "tam kapanış", [r["calendar_date"] for r in ext_ if r["full_closure"] == "YES"],
  "| verification:", dict(Counter(r["verification_status"] for r in ext_)), "| kaynak sha:", {r["source_pdf_sha256"][:8] for r in ext_})
# XU100 çapraz denetim (B uzatması ↔ yeni XU100)
def xu(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"), parse_float=Decimal)
    return {r["hisTs"]: r["clval"] for r in d["data"]}, d
xu_old, dold = xu(RAW / "official_bist_xu100_graphic_pinned_through_20260819.json")
xu_new, dnew = xu(RAW / "xu100" / "xu100_graphic_20260922.json")
P("[ÖLÇTÜM] XU100 eski: kayıt", len(dold["data"]), min(xu_old), "…", max(xu_old), "| yeni: kayıt", len(dnew["data"]), min(xu_new), "…", max(xu_new),
  "| indexName≠XU100:", sum(r["indexName"] != "XU100" for r in dnew["data"]), "| eski kayıt yeni dosyada farklı/eksik:", sum(xu_new.get(d) != v for d, v in xu_old.items()),
  "| yeni ek kayıt:", len(set(xu_new) - set(xu_old)), "| tekrarlı tarih yeni:", len(dnew["data"]) - len(xu_new))
ext_sess = {r["calendar_date"] for r in ext_ if r["counts_as_official_session"] == "YES" and r["calendar_date"] <= "2026-09-21"}
xu_ext = {d for d in xu_new if "2026-08-20" <= d <= "2026-09-21"}
P("[ÖLÇTÜM] B uzatması 2026-08-20…09-21 seans günleri", len(ext_sess), "== XU100 kayıt günleri", len(xu_ext), ext_sess == xu_ext)
# B'de XU100 kapanışı olmayan hafta içi seanslar
gapB = sorted(d for d in sessB if d not in xu_old)
P("[ÖLÇTÜM] Takvim B seansı olup eski XU100'de kapanışı olmayan günler:", gapB)
# A'da XU100 olmayan seans
P("[ÖLÇTÜM] Takvim A seansı olup XU100'de olmayan:", sorted(d for d in sessA if d not in xu_old), "| XU100'de olup A seansı olmayan (A aralığı):", sorted(d for d in xu_old if daysA[0] <= d <= daysA[-1] and d not in set(sessA)))

# --- Takvim C
calC = rd(RAW / "pay_calendar_c_20200101_20230921.csv", "utf-8")
sessC = [r["calendar_date"] for r in calC if r["counts_as_official_session"] == "YES"]
P("[ÖLÇTÜM] Takvim C:", calC[0]["calendar_date"], "…", calC[-1]["calendar_date"], "gün", len(calC), "seans", len(sessC), "yarım", sum(r["half_day"] == "YES" for r in calC),
  "| locator:", dict(Counter(r["source_locator"] for r in calC)), "| verification:", dict(Counter(r["verification_status"] for r in calC)))
gapC = [r["calendar_date"] for r in calC if "XU100" in r["source_locator"]]
P("[ÖLÇTÜM] C XU100-boşluk kapanışları:", gapC, "| C seansı olup yeni XU100'de olmayan:", sorted(d for d in sessC if d not in xu_new)[:10],
  "| XU100'de olup C seansı olmayan:", sorted(d for d in xu_new if "2020-01-01" <= d <= "2023-09-21" and d not in set(sessC)))
ev = rd(RAW / "pay_calendar_c_bulletin_evidence_20200101_20230921.csv", "utf-8")
P("[ÖLÇTÜM] C bülten kanıtı satır", len(ev), "| karar:", dict(Counter(r["decision"] for r in ev)), "| kaynak:", dict(Counter(r["source"] for r in ev)),
  "| TRADING_SESSION günleri:", [r["date"] for r in ev if r["decision"] == "TRADING_SESSION"], "| PUBLISHED_NO_TRADING:", [r["date"] for r in ev if r["decision"] == "PUBLISHED_NO_TRADING"])
wk_clos = [r["calendar_date"] for r in calC if r["counts_as_official_session"] == "NO" and date.fromisoformat(r["calendar_date"]).weekday() < 5]
P("[ÖLÇTÜM] C hafta içi kapanış sayısı:", len(wk_clos), "== kanıt satırı:", len(wk_clos) == len(ev), "| kümeler eşit:", set(wk_clos) == {r["date"] for r in ev})
P("[ÖLÇTÜM] C ↔ A ardışık:", date.fromisoformat(daysA[0]) - date.fromisoformat(calC[-1]["calendar_date"]) == timedelta(days=1))

# --- PB dosyası
P("[ÖLÇTÜM] PB pit_status:", dict(Counter(r["pit_status"] for r in pb)), "| price_source_semantics:", dict(Counter(r["price_source_semantics"] for r in pb)),
  "| SPK<B<T sırası ihlali:", sum(not (r["spk_publication_date"] < r["first_bookbuilding_date"] < r["canonical_first_trading_date"]) for r in pb),
  "| canonical ftd ≠ MASTER:", sum(r["canonical_first_trading_date"] != mftd[r["ticker"]] for r in pb))
gaps1 = sorted((date.fromisoformat(r["first_bookbuilding_date"]) - date.fromisoformat(r["spk_publication_date"])).days for r in pb)
gaps2 = sorted((date.fromisoformat(r["canonical_first_trading_date"]) - date.fromisoformat(r["first_bookbuilding_date"])).days for r in pb)
P("[ÖLÇTÜM] SPK→talep toplama gün (min/medyan/maks):", gaps1[0], gaps1[49], gaps1[-1], "| talep→ilk işlem:", gaps2[0], gaps2[49], gaps2[-1])
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))

"""KITAP_AUDIT_1 Adım 2 (f1–f5, pb1–pb4, TÜFE ayı, tahsis rejimi): ham kaynaklardan sıfırdan; READY, training_table_v2 ve kılavuzla karşılaştır.
borsai import edilmez. Yalnız stdlib."""
import csv, json, math
from collections import Counter
from decimal import Decimal, Context, ROUND_HALF_EVEN, ROUND_HALF_UP, localcontext
from fractions import Fraction
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]; RAW = ROOT / "data" / "raw"
def rd(p, enc="utf-8-sig"):
    with open(p, encoding=enc, newline="") as fh: return list(csv.DictReader(fh))
out = []; P = lambda *a: out.append(" ".join(str(x) for x in a))
master = {r["ticker"]: r for r in rd(RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv")}
ready = {r["ticker"]: r for r in rd(RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_feature_readiness.csv")}
tt = {r["ticker"]: r for r in rd(ROOT / "data/training_table.csv")}
tt2 = {r["ticker"]: r for r in rd(ROOT / "data/training_table_v2.csv")}
pb = {r["ticker"]: r for r in rd(RAW / "PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv")}
LEG = Context(prec=28, rounding=ROUND_HALF_EVEN); Q = Decimal(1).scaleb(-10)
def pct(n, d):
    with localcontext(LEG):
        raw = n / d * Decimal(100)
        return Decimal(format(raw.quantize(Q, rounding=ROUND_HALF_UP), "f").rstrip("0").rstrip(".") or "0")
def D(x): return None if x in ("", "DATA_NOT_FOUND") else Decimal(x)
# ---- f1–f5
f1m = []; f2m = []; f3m = []; f4m = []; f5m = []; f1_src_ne = []; vals = {"f1": [], "f2": [], "f3": [], "f4": []}; f5n = 0
for t, m in master.items():
    price, sh, post, ci = D(m["ipo_price"]), D(m["shares_offered"]), D(m["post_ipo_share_capital"]), D(m["capital_increase_shares"])
    size = D(m["ipo_size_tl"])
    with localcontext(LEG): prod = sh * price
    f1 = size if size is not None else prod
    if size is not None and size != prod: f1_src_ne.append((t, str(size), str(prod), str(abs(size - prod))))
    f2, f4, f3 = pct(sh, post), pct(ci, sh), D(m["total_demand_multiple"])
    r = ready[t]
    if f1 != D(r["f1_raw_ipo_size_tl"]): f1m.append(t)
    if f2 != D(r["f2_free_float_pct"]): f2m.append((t, str(f2), r["f2_free_float_pct"]))
    if (f3 is None) != (D(r["f3_total_demand_multiple"]) is None) or (f3 is not None and f3 != D(r["f3_total_demand_multiple"])): f3m.append(t)
    if f4 != D(r["f4_capital_increase_pct_of_offer"]): f4m.append((t, str(f4), r["f4_capital_increase_pct_of_offer"]))
    if str(int(f3 is None)) != r["f5_total_demand_missing"]: f5m.append(t)
    f5n += f3 is None
    # tablo ile
    if D(tt[t]["total_demand_multiple"]) != f3 or D(tt[t]["ipo_price_tl"]) != price or D(tt[t]["shares_offered"]) != sh: f3m.append(("tablo", t))
    vals["f1"].append(f1); vals["f2"].append(f2); vals["f4"].append(f4)
    if f3 is not None: vals["f3"].append(f3)
def mmm(v): v = sorted(v); return f"{v[0]} / {v[len(v)//2] if len(v)%2 else (v[len(v)//2-1]+v[len(v)//2])/2} / {v[-1]}"
P("[ÖLÇTÜM] f1 READY farkı:", f1m, "| f2:", f2m, "| f3:", f3m, "| f4:", f4m, "| f5:", f5m, "| f5=1 sayısı:", f5n)
P("[ÖLÇTÜM] f1 kaynak ≠ fiyat×pay:", f1_src_ne)
for k in ("f1", "f2", "f3", "f4"): P(f"[ÖLÇTÜM] {k} min/medyan/maks (n={len(vals[k])}):", mmm(vals[k]))
P("[ÖLÇTÜM] READY f2_formula:", dict(Counter(r["f2_formula"] for r in ready.values())), "| f4_formula:", dict(Counter(r["f4_formula"] for r in ready.values())))
# ek satış özdeşliği
eq93 = [t for t, m in master.items() if D(m["shares_offered"]) == D(m["capital_increase_shares"]) + D(m["existing_share_sale"])]
addl = {t: D(m["additional_sale_shares"]) for t, m in master.items()}
eq_add = [t for t, m in master.items() if t not in eq93 and addl[t] is not None and D(m["shares_offered"]) == D(m["capital_increase_shares"]) + D(m["existing_share_sale"]) + addl[t]]
P("[ÖLÇTÜM] shares = cap_inc + existing:", len(eq93), "| ek satışla tamamlanan:", sorted(eq_add), "| ikisi de değil:", sorted(set(master) - set(eq93) - set(eq_add)))
P("[ÖLÇTÜM] additional_sale: dolu", sum(v is not None for v in addl.values()), "sıfır", sum(v == 0 for v in addl.values() if v is not None), "pozitif", sorted(t for t, v in addl.items() if v and v > 0), "eksik", sorted(t for t, v in addl.items() if v is None))
P("[ÖLÇTÜM] f3 origin:", dict(Counter(m["total_demand_multiple_origin"] for m in master.values())), "| filter:", dict(Counter(m["total_demand_filter_status"] for m in master.values())),
  "| definition farklı metin:", len({m["total_demand_definition"] for m in master.values()}), "| f3 eksik:", [(t, m["total_demand_multiple_origin"]) for t, m in master.items() if D(m["total_demand_multiple"]) is None])
# ---- PB
PBC = Context(prec=60, rounding=ROUND_HALF_EVEN); ids = Counter(); pbv = {"pb1": [], "pb2": [], "pb3": [], "pb4": []}
price_ne = []; base_ne = []
for t, r in pb.items():
    v = {k: Decimal(r[k]) for k in ("ipo_price_try", "planned_pre_ipo_capital", "planned_post_ipo_capital", "planned_capital_increase_shares", "planned_existing_share_sale", "planned_base_offer_shares", "planned_additional_sale_ceiling", "planned_max_offer_shares")}
    ids["A"] += v["planned_post_ipo_capital"] == v["planned_pre_ipo_capital"] + v["planned_capital_increase_shares"]
    ids["B"] += v["planned_base_offer_shares"] == v["planned_capital_increase_shares"] + v["planned_existing_share_sale"]
    ids["C"] += v["planned_max_offer_shares"] == v["planned_base_offer_shares"] + v["planned_additional_sale_ceiling"]
    with localcontext(PBC): pb1 = float((v["ipo_price_try"] * v["planned_base_offer_shares"]).ln())
    pbv["pb1"].append(round(pb1, 4)); pbv["pb2"].append(round(float(Fraction(v["planned_base_offer_shares"]) / Fraction(v["planned_post_ipo_capital"]) * 100), 4))
    pbv["pb3"].append(round(float(Fraction(v["planned_capital_increase_shares"]) / Fraction(v["planned_base_offer_shares"]) * 100), 4)); pbv["pb4"].append(round(float(Fraction(v["planned_additional_sale_ceiling"]) / Fraction(v["planned_base_offer_shares"]) * 100), 4))
    if v["ipo_price_try"] != Decimal(master[t]["ipo_price"]): price_ne.append(t)
    if v["planned_base_offer_shares"] != Decimal(master[t]["shares_offered"]): base_ne.append(t)
P("[ÖLÇTÜM] PB özdeşlikler A/B/C tutan:", dict(ids), "| pb1/pb2/pb3 min/medyan/maks:", mmm(pbv["pb1"]), "|", mmm(pbv["pb2"]), "|", mmm(pbv["pb3"]),
  "| pb3=100:", sum(x == 100 for x in pbv["pb3"]), "| pb4 dağılımı:", dict(Counter(pbv["pb4"])))
P("[ÖLÇTÜM] PB fiyat ≠ nihai:", price_ne, "| planlanan taban ≠ nihai shares_offered:", len(base_ne), sorted(base_ne))
# ---- TÜFE ayı ve rejim (v2 tablosu)
def month_for(T):
    y, m = int(T[:4]), int(T[5:7]) - 2
    if m <= 0: y, m = y - 1, m + 12
    return f"{y:04d}-{m:02d}"
tufe = {r["month"]: r for r in rd(RAW / "tuik/tufe_genel_2025_100.csv", "utf-8")}
mism = [t for t, r in tt2.items() if r["tufe_month"] != month_for(r["first_trading_date"]) or r["tufe_index"] != tufe[month_for(r["first_trading_date"])]["index"]]
P("[ÖLÇTÜM] v2 tufe_month/tufe_index ≠ T−2 kuralı:", mism, "| v2 satır", len(tt2), "| kohort:", dict(Counter(r["cohort"] for r in tt2.values())))
def regime(d): return "PRE_20211111" if d < "2021-11-11" else ("THRESH100_20211111" if d < "2023-03-30" else "EQUAL_DIST_20230330")
rm = [t for t, r in tt2.items() if regime(r["alloc_regime_date"]) != r["alloc_regime"]]
h99rd = [t for t, r in tt2.items() if r["cohort"] == "H99" and r["alloc_regime_date"] != pb[t]["first_bookbuilding_date"]]
P("[ÖLÇTÜM] alloc_regime ≠ tarih kuralı:", rm, "| H99 alloc_regime_date ≠ PB first_bookbuilding_date:", h99rd,
  "| rejim (H99):", dict(Counter(r["alloc_regime"] for r in tt2.values() if r["cohort"] == "H99")), "| rejim (OOT):", dict(Counter(r["alloc_regime"] for r in tt2.values() if r["cohort"] == "OOT_OPEN")))
oot = [r for r in tt2.values() if r["cohort"] == "OOT_OPEN"]
P("[ÖLÇTÜM] OOT açık: ftd", min(r["first_trading_date"] for r in oot), "…", max(r["first_trading_date"] for r in oot), "| yıl:", dict(sorted(Counter(r["first_trading_date"][:4] for r in oot).items())),
  "| pit:", dict(Counter(r["point_in_time_status"] for r in oot)), "| f3 boş:", sum(r["total_demand_multiple"] == "" for r in oot), "| ek satış boş:", sum(r["additional_sale_shares"] == "" for r in oot),
  "| origin:", dict(Counter(r["total_demand_multiple_origin"] for r in oot if r["total_demand_multiple"])), "| filter:", dict(Counter(r["total_demand_filter_status"] for r in oot)),
  "| sale_method:", dict(Counter(r["sale_method"] for r in oot)), "| market:", dict(Counter(r["market"] for r in oot)))
# eğitim kümesi büyüklükleri (§3.8.4)
h99 = [r for r in tt2.values() if r["cohort"] == "H99"]
P("[ÖLÇTÜM] küme n: H99 f3 dolu", sum(r["total_demand_multiple"] != "" for r in h99), "| OOT f3 dolu", sum(r["total_demand_multiple"] != "" for r in oot),
  "| düşen h99 (f3+ek satış dolu)", sum(r["total_demand_multiple"] != "" and r["additional_sale_shares"] != "" for r in h99),
  "| pooled", sum(r["total_demand_multiple"] != "" and r["additional_sale_shares"] != "" for r in tt2.values()), "| addsale (ek satış dolu)", sum(r["additional_sale_shares"] != "" for r in tt2.values()))
# NETGL §3.6.3 / §3.9.1
inp = json.loads((ROOT / "registry/inputs/NETGL.json").read_text())["fields"]
g = lambda k: inp[k]["value"]
with localcontext(Context(prec=60)): f1r = Decimal(g("ipo_size_tl")) / (Decimal(tufe["2026-07"]["index"]) / 100)
P("[ÖLÇTÜM] NETGL: tufe_month", month_for(g("first_trading_date")), "endeks", tufe["2026-07"]["index"], "yayım", tufe["2026-07"]["release_date"], "| f1r_ham =", f1r,
  "| f2 =", pct(Decimal(g("shares_offered")), Decimal(g("post_ipo_share_capital"))), "| f4 =", pct(Decimal(g("capital_increase_shares")), Decimal(g("shares_offered"))),
  "| pb1 =", math.log(float(Decimal(g("ipo_price_try")) * Decimal(g("planned_base_offer_shares")))), "| f1 == fiyat×pay:", Decimal(g("ipo_size_tl")) == Decimal(g("ipo_price_tl")) * Decimal(g("shares_offered")))
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n", encoding="utf-8"); print("\n".join(out))

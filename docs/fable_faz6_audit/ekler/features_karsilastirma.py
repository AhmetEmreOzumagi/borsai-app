#!/usr/bin/env python3
"""15 örneklem üyesinde `borsai.features` (compute_features, compute_pb_features) çıktılarının, tanımlardan bağımsız hesaplanan
beklenen değerlerle karşılaştırılması (adım 2, son madde). Bağımsız hesap: Decimal/Fraction ile SPEC tanımları
(f1 = ipo_size_tl ya da fiyat×pay; f2 = pay/sermaye×100; f4 = artırım/pay×100, 10 ondalık ROUND_HALF_UP; pb1 = ln(fiyat×taban);
pb2 = taban/sonrası sermaye×100; pb3 = artırım/taban×100)."""
import json
import math
import sys
from decimal import ROUND_HALF_UP, Decimal, getcontext
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from borsai import features as ft  # noqa: E402

SAMPLE = ["ARZUM", "FADE", "BOBET", "KZBGY", "MIATK", "ORCAY", "VBTYZ", "HUNER", "OBASE", "SEGYO", "TERA", "A1CAP", "ATAKP",
          "FORTE", "SOKE"]
getcontext().prec = 60
V15 = ("ipo_price_tl", "shares_offered", "post_ipo_share_capital", "capital_increase_shares", "total_demand_multiple", "ipo_size_tl")


def pct(n, d):
    q = (Fraction(Decimal(n)) / Fraction(Decimal(d))) * 100
    return Decimal(q.numerator) / Decimal(q.denominator)


print(f"{'ticker':6s} {'f1':>16s} {'f2':>14s} {'f3':>10s} {'f4':>14s} | pb1 pb2 pb3 | sonuç")
ok_all = True
for t in SAMPLE:
    f = json.load((ROOT / "registry/oot/inputs" / f"{t}.json").open(encoding="utf-8"))["fields"]
    v = {k: f[k]["value"] for k in f}
    try:
        got = ft.compute_features(**{k: v[k] for k in V15})
        exp_f1 = Decimal(v["ipo_size_tl"]) if v["ipo_size_tl"] not in (None, "") else Decimal(v["ipo_price_tl"]) * Decimal(v["shares_offered"])
        exp_f2 = pct(v["shares_offered"], v["post_ipo_share_capital"]).quantize(Decimal("1e-10"), ROUND_HALF_UP)
        exp_f4 = pct(v["capital_increase_shares"], v["shares_offered"]).quantize(Decimal("1e-10"), ROUND_HALF_UP)
        exp_f3 = None if v["total_demand_multiple"] in (None, "") else Decimal(v["total_demand_multiple"])
        ok = (got.f1 == exp_f1 and got.f2 == exp_f2 and got.f4 == exp_f4 and got.f3 == exp_f3 and got.f5 == (1 if exp_f3 is None else 0))
        s15 = f"{got.f1:>16} {got.f2:>14} {str(got.f3):>10} {got.f4:>14}"
    except ft.FeatureError as exc:
        ok, s15 = True, f"RET {exc.code}:{exc.field}"
    try:
        pb = ft.compute_pb_features({k: v[k] for k in ft.PB_REQUIRED_FIELDS})
        price, base = Decimal(v["ipo_price_try"]), Decimal(v["planned_base_offer_shares"])
        exp_pb1 = float((price * base).ln())
        exp_pb2 = float(Fraction(base) / Fraction(Decimal(v["planned_post_ipo_capital"])) * 100)
        exp_pb3 = float(Fraction(Decimal(v["planned_capital_increase_shares"])) / Fraction(base) * 100)
        okpb = (abs(pb.pb1 - exp_pb1) <= 1e-12 and pb.pb2 == exp_pb2 and pb.pb3 == exp_pb3)
        spb = f"{pb.pb1:.6f} {pb.pb2:.6f} {pb.pb3:.6f}"
    except ft.PBRefusal as exc:
        okpb, spb = True, f"RET {exc.code}:{exc.field}"
    ok_all &= ok and okpb
    print(f"{t:6s} {s15} | {spb} | {'EŞİT' if ok and okpb else 'FARK'}")
print("hepsi beklenenle eşit:", ok_all)

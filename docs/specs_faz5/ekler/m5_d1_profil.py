"""m5_d1_profil.py — SPEC_POST_D1_V0 için TEK DEĞİŞKENLİ D1 alan profili (H99).

Görev: BORSAI_FAZ5_FABLE_POST_D1_SPEC_20260924, adım 2. Yalnız okur; hiçbir şey yazmaz.
- Girdi: SESSIONS (session_number == 1 satırları, thb_raw_*/thm_raw_* ham metin) ve
  training_table (shares_offered, ceiling_close_D1). Değerler Decimal (ham metinden).
- ceiling_close_D1 YALNIZ alt küme seçimi için kullanılır (görev metnindeki tek istisna).
- Sonuç sütunlarıyla (L, R_h, Y_h, D2+ alanları) HİÇBİR birleştirme yapılmaz; özellik–sonuç
  ilişkisine bakılmaz. Çıktı yalnız tek değişkenli sayım/kantil tablolarıdır.
Çalıştırma: .venv/bin/python docs/specs_faz5/ekler/m5_d1_profil.py > docs/specs_faz5/ekler/profil_d1.txt
"""
from __future__ import annotations

import csv
import math
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = ROOT / "data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv"
TRAIN = ROOT / "data/training_table.csv"

D1_FIELDS = ("thb_raw_open", "thb_raw_high", "thb_raw_low", "thb_raw_close", "thb_raw_volume", "thb_raw_turnover",
             "thb_raw_aof", "thb_raw_trade_count", "thm_raw_reference_price", "thm_raw_upper_limit", "thm_raw_lower_limit")
ALLOWED_TRAIN = ("ticker", "first_trading_date", "ipo_price_tl", "shares_offered", "post_ipo_share_capital", "ceiling_close_D1")


def q(values, p):
    """Type-7 doğrusal kantil (numpy varsayılanı)."""
    xs = sorted(values)
    if not xs:
        return None
    h = (len(xs) - 1) * p
    lo, hi = math.floor(h), math.ceil(h)
    return xs[lo] + (xs[hi] - xs[lo]) * (h - lo)


def summarize(name, values, unit=""):
    vals = [float(v) for v in values]
    print(f"{name} (n = {len(vals)}{', ' + unit if unit else ''}):")
    print("  min / p05 / p25 / p50 / p75 / p95 / max = " + " / ".join(
        "NA" if x is None else f"{x:.4g}" for x in (min(vals), q(vals, .05), q(vals, .25), q(vals, .5), q(vals, .75), q(vals, .95), max(vals))))
    print(f"  ortalama = {sum(vals) / len(vals):.4g}")


def main() -> None:
    with SESSIONS.open(encoding="utf-8-sig", newline="") as fh:
        d1 = {r["ticker"]: r for r in csv.DictReader(fh) if r["session_number"] == "1"}
    with TRAIN.open(encoding="utf-8", newline="") as fh:
        train = {r["ticker"]: {k: r[k] for k in ALLOWED_TRAIN} for r in csv.DictReader(fh)}
    assert set(d1) == set(train) and len(d1) == 99, (len(d1), len(train))

    print("# D1 tek değişkenli profil — H99, yalnız 1. seans alanları (thb_raw_*/thm_raw_*), Decimal ham metinden")
    print(f"# SESSIONS: {SESSIONS.name}; training_table sütunları: {ALLOWED_TRAIN}")
    print("# Sonuç sütunlarıyla birleştirme YOK; ceiling_close_D1 yalnız alt küme seçimi için.\n")

    rows = []
    for t, s in d1.items():
        f = {k: Decimal(s[k]) for k in D1_FIELDS}
        tr = train[t]
        rows.append({
            "ticker": t, "date": s["target_session_date"], "session_type": s["session_type"],
            "status": s["security_trading_status"], "row_status": s["row_status"],
            "d1_ceiling": tr["ceiling_close_D1"] == "1",
            "lock": f["thb_raw_low"] == f["thm_raw_upper_limit"],
            "open_at_U": f["thb_raw_open"] == f["thm_raw_upper_limit"],
            "high_at_U": f["thb_raw_high"] == f["thm_raw_upper_limit"],
            "close_at_U": f["thb_raw_close"] == f["thm_raw_upper_limit"],
            "aof_at_U": f["thb_raw_aof"] == f["thm_raw_upper_limit"],
            "low_at_Lo": f["thb_raw_low"] == f["thm_raw_lower_limit"],
            "dip": float((f["thm_raw_upper_limit"] - f["thb_raw_low"]) / f["thm_raw_upper_limit"]),
            "aof_gap": float((f["thm_raw_upper_limit"] - f["thb_raw_aof"]) / f["thm_raw_upper_limit"]),
            "turnover_ratio": float(f["thb_raw_volume"] / Decimal(tr["shares_offered"])),
            "turnover_capital": float(f["thb_raw_volume"] / Decimal(tr["post_ipo_share_capital"])),
            "volume": float(f["thb_raw_volume"]), "trade_count": float(f["thb_raw_trade_count"]),
            "shares_per_trade": float(f["thb_raw_volume"] / f["thb_raw_trade_count"]) if f["thb_raw_trade_count"] > 0 else None,
            "turnover_tl": float(f["thb_raw_turnover"]),
            "aof_x_vol_vs_turnover": float(abs(f["thb_raw_aof"] * f["thb_raw_volume"] - f["thb_raw_turnover"]) / f["thb_raw_turnover"]) if f["thb_raw_turnover"] > 0 else None,
            "ref_eq_ipo": f["thm_raw_reference_price"] == Decimal(tr["ipo_price_tl"]),
        })

    print("## 1. Satır durumu ve seans tipi (99 arz, D1)")
    from collections import Counter
    print("  row_status:", dict(Counter(r["row_status"] for r in rows)))
    print("  security_trading_status:", dict(Counter(r["status"] for r in rows)))
    print("  session_type:", dict(Counter(r["session_type"] for r in rows)))
    print("  D1 referans == arz fiyatı (Decimal):", sum(r["ref_eq_ipo"] for r in rows), "/ 99")
    print("  trade_count > 0:", sum(r["trade_count"] > 0 for r in rows), "/ 99; volume > 0:", sum(r["volume"] > 0 for r in rows), "/ 99")
    print("  |AOF×hacim − ciro| / ciro > 1e-3:", sum(1 for r in rows if r["aof_x_vol_vs_turnover"] is not None and r["aof_x_vol_vs_turnover"] > 1e-3), "/ 99 (özel işlem bildirimi payı; yalnız bilgi)")
    print()

    for label, sub in (("99 arz (tamamı)", rows), ("D1 tavan kapatanlar (ceiling_close_D1 = 1)", [r for r in rows if r["d1_ceiling"]]),
                       ("D1 tavan kapatmayanlar (ceiling_close_D1 = 0)", [r for r in rows if not r["d1_ceiling"]])):
        n = len(sub)
        print(f"## {label}: n = {n}")
        print("### 2. Limit eşitlikleri (Decimal, ham metin)")
        for k, desc in (("close_at_U", "kapanış == üst limit"), ("lock", "en düşük == üst limit (gün boyu tek fiyat = kilit)"),
                        ("open_at_U", "açılış == üst limit"), ("high_at_U", "en yüksek == üst limit"), ("aof_at_U", "AOF == üst limit"),
                        ("low_at_Lo", "en düşük == alt limit")):
            c = sum(r[k] for r in sub)
            print(f"  {desc}: {c} / {n} ({c / n:.3f})" if n else f"  {desc}: —")
        both = sum(r["lock"] and r["open_at_U"] for r in sub)
        print(f"  kilit VE açılış == üst limit: {both} / {n}   (kilit ⇒ açılış = en yüksek = kapanış = üst limit; tutarlılık: {sum(r['lock'] and not (r['open_at_U'] and r['high_at_U'] and r['close_at_U']) for r in sub)} aykırı)")
        print("### 3. Sürekli alanlar")
        if n:
            summarize("  dip = (U − en düşük)/U", [r["dip"] for r in sub])
            nz = [r["dip"] for r in sub if r["dip"] > 0]
            if nz:
                summarize("  dip | dip > 0", nz)
            summarize("  aof_gap = (U − AOF)/U", [r["aof_gap"] for r in sub])
            summarize("  el değiştirme = hacim / shares_offered", [r["turnover_ratio"] for r in sub], "pay/pay")
            summarize("  ln(el değiştirme)", [math.log(r["turnover_ratio"]) for r in sub if r["turnover_ratio"] > 0])
            summarize("  hacim / post_ipo_share_capital", [r["turnover_capital"] for r in sub])
            summarize("  hacim (pay adedi)", [r["volume"] for r in sub])
            summarize("  sözleşme sayısı", [r["trade_count"] for r in sub])
            summarize("  ln(sözleşme sayısı)", [math.log(r["trade_count"]) for r in sub if r["trade_count"] > 0])
            summarize("  pay / sözleşme", [r["shares_per_trade"] for r in sub if r["shares_per_trade"] is not None])
            summarize("  ciro (TL)", [r["turnover_tl"] for r in sub])
            print("  el değiştirme > 1 (hacim > arz edilen pay):", sum(r["turnover_ratio"] > 1 for r in sub), "/", n)
            print("  el değiştirme ≥ 0.5:", sum(r["turnover_ratio"] >= 0.5 for r in sub), "/", n)
            print("  el değiştirme < 0.1:", sum(r["turnover_ratio"] < 0.1 for r in sub), "/", n)
            print("  kilitli alt kümede el değiştirme p25/p50/p75:", " / ".join(f"{x:.3g}" for x in (
                q([r["turnover_ratio"] for r in sub if r["lock"]], .25), q([r["turnover_ratio"] for r in sub if r["lock"]], .5), q([r["turnover_ratio"] for r in sub if r["lock"]], .75))) if any(r["lock"] for r in sub) else "  (kilitli yok)")
            print("  kilitsiz alt kümede el değiştirme p25/p50/p75:", " / ".join(f"{x:.3g}" for x in (
                q([r["turnover_ratio"] for r in sub if not r["lock"]], .25), q([r["turnover_ratio"] for r in sub if not r["lock"]], .5), q([r["turnover_ratio"] for r in sub if not r["lock"]], .75))) if any(not r["lock"] for r in sub) else "  (kilitsiz yok)")
        print()

    print("## 4. D1 tavan kapatanlarda kilit oranının yıllara göre dağılımı (yalnız özellik; sonuç yok)")
    sub = [r for r in rows if r["d1_ceiling"]]
    for y in sorted({r["date"][:4] for r in sub}):
        ys = [r for r in sub if r["date"][:4] == y]
        print(f"  {y}: n = {len(ys)}, kilit = {sum(r['lock'] for r in ys)}, el değiştirme medyanı = {q([r['turnover_ratio'] for r in ys], .5):.3g}")
    print("\n## 5. Aylık blok sayısı (D1 tavan kapatanlar; aralık koşulu ≥ 6 blok için bilgi)")
    print("  ayrı YYYY-MM:", len({r["date"][:7] for r in sub}))


if __name__ == "__main__":
    main()

"""m8_kirilma_profil.py — SPEC_BREAK_V0 için TEK DEĞİŞKENLİ kırılma akşamı profili (H99).

Görev: BORSAI_FAZ8_FABLE_BREAK_SPEC_20261001, adım 2. Yalnız okur; hiçbir şey yazmaz.
- Girdi: SESSIONS dosyası (thb_raw_*/thm_raw_* ham metin, Decimal) ve training_table'ın yalnız
  ticker / first_trading_date / ipo_price_tl / shares_offered sütunları (sonuç sütunları okunmaz).
- Kırılma günü b = L + 1: D1'den başlayan tavan serisinin ilk tavan-olmayan kapanışı. Seri, seanslar
  sırayla okunarak bulunur ve b. seansta DURULUR: b'den sonraki hiçbir seansın alanı okunmaz.
  (Yalnız seans tarihleri, aylık blok sayımı için, bütün satırlardan alınır.)
- Sonuç sütunlarıyla (R_h, Y_h, D_{b+1}.. alanları) HİÇBİR birleştirme yapılmaz; özellik–sonuç
  ilişkisine bakılmaz. Çıktı yalnız tek değişkenli sayım/kantil tablolarıdır. Tek istisna görev
  metnindeki maruziyet tablosudur; o burada YENİDEN HESAPLANMAZ.
Çalıştırma: .venv/bin/python docs/specs_faz8/ekler/m8_kirilma_profil.py > docs/specs_faz8/ekler/profil_kirilma.txt
"""
from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = ROOT / "data/raw/HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv"
TRAIN = ROOT / "data/training_table.csv"

FIELDS = ("thb_raw_open", "thb_raw_high", "thb_raw_low", "thb_raw_close", "thb_raw_volume", "thb_raw_turnover",
          "thb_raw_aof", "thb_raw_trade_count", "thm_raw_reference_price", "thm_raw_upper_limit", "thm_raw_lower_limit")
ALLOWED_TRAIN = ("ticker", "first_trading_date", "ipo_price_tl", "shares_offered")
LN_STEP = math.log(1 / 0.9)

# Fiyat adımı tablosu (SPEC_CEILING_PATH_V0 §2; H99'da alt limit 990/990 birebir)
TICKS = ((Decimal("20"), Decimal("0.01")), (Decimal("50"), Decimal("0.02")), (Decimal("100"), Decimal("0.05")),
         (Decimal("250"), Decimal("0.10")), (Decimal("500"), Decimal("0.25")), (Decimal("1000"), Decimal("0.50")),
         (Decimal("2500"), Decimal("1.00")), (None, Decimal("2.50")))


def tick(x: Decimal) -> Decimal:
    for lim, s in TICKS:
        if lim is None or x < lim:
            return s
    raise AssertionError


def lower_limit(base: Decimal) -> Decimal:
    y = base * Decimal("0.9")
    s = tick(y)
    return (y / s).to_integral_value(rounding=ROUND_CEILING) * s


def q(values, p):
    """Type-7 doğrusal kantil (numpy varsayılanı)."""
    xs = sorted(values)
    if not xs:
        return None
    h = (len(xs) - 1) * p
    lo, hi = math.floor(h), math.ceil(h)
    return xs[lo] + (xs[hi] - xs[lo]) * (h - lo)


def summarize(name, values, unit=""):
    vals = [float(v) for v in values if v is not None]
    if not vals:
        print(f"{name}: (boş)")
        return
    print(f"{name} (n = {len(vals)}{', ' + unit if unit else ''}):")
    print("  min / p05 / p25 / p50 / p75 / p95 / max = " + " / ".join(
        f"{x:.4g}" for x in (min(vals), q(vals, .05), q(vals, .25), q(vals, .5), q(vals, .75), q(vals, .95), max(vals))))
    print(f"  ortalama = {sum(vals) / len(vals):.4g}")


def main() -> None:
    with SESSIONS.open(encoding="utf-8-sig", newline="") as fh:
        by_ticker: dict[str, dict[int, dict]] = defaultdict(dict)
        for r in csv.DictReader(fh):
            by_ticker[r["ticker"]][int(r["session_number"])] = r
    with TRAIN.open(encoding="utf-8", newline="") as fh:
        train = {r["ticker"]: {k: r[k] for k in ALLOWED_TRAIN} for r in csv.DictReader(fh)}
    assert set(by_ticker) == set(train) and len(train) == 99, (len(by_ticker), len(train))
    assert all(len(v) == 10 for v in by_ticker.values())

    # --- seri ve kırılma günü: sırayla oku, ilk tavan-olmayan kapanışta DUR -------------------------------------------
    units = []
    for t in sorted(by_ticker):
        P = Decimal(train[t]["ipo_price_tl"])
        shares = Decimal(train[t]["shares_offered"])
        streak_rows = []          # D1..D_L (hepsi tavan)
        brk = None                # D_b satırı
        for k in range(1, 11):
            s = by_ticker[t][k]
            f = {name: Decimal(s[name]) for name in FIELDS}
            f["_type"] = s["session_type"]
            f["_status"] = s["security_trading_status"]
            f["_date"] = s["target_session_date"]
            if f["thb_raw_close"] == f["thm_raw_upper_limit"]:
                streak_rows.append(f)
                continue
            brk = (k, f)
            break                 # b'den sonraki seanslar OKUNMAZ
        L = len(streak_rows)
        u = {"ticker": t, "P": P, "shares": shares, "L": L, "d1_date": train[t]["first_trading_date"],
             "streak": streak_rows, "b": None if brk is None else brk[0], "brk": None if brk is None else brk[1]}
        units.append(u)

    n_all = len(units)
    print("# Kırılma akşamı tek değişkenli profil — H99 (99 arz), yalnız D1..D_b alanları (thb_raw_*/thm_raw_*), Decimal")
    print(f"# SESSIONS: {SESSIONS.name}; training_table sütunları: {ALLOWED_TRAIN}")
    print("# b = L + 1 (ilk tavan olmayan kapanış). b'den sonraki seanslar okunmadı; sonuç sütunlarıyla birleştirme YOK.\n")

    # ---------------------------------------------------------------- 1. L ve b dağılımı
    print("## 1. Seri uzunluğu L ve kırılma günü b")
    cL = Counter(u["L"] for u in units)
    print("  L dağılımı (L: arz sayısı):", ", ".join(f"{k}: {cL[k]}" for k in range(0, 11)))
    print("  seri hiç bozulmayan (L = 10):", cL[10], "/ 99 → kırılma akşamı YOK")
    cb = Counter(u["b"] for u in units if u["b"] is not None)
    print("  b dağılımı (b: arz sayısı):", ", ".join(f"{k}: {cb[k]}" for k in range(1, 11)), f"; toplam {sum(cb.values())}")
    print("  b = 1 (D1 tavan değil):", cb[1], "; 2 ≤ b ≤ 9:", sum(cb[k] for k in range(2, 10)), "; b = 10:", cb[10])
    print("  D10'a kalan seans r = 10 − b dağılımı (r: arz):", ", ".join(f"{10 - k}: {cb[k]}" for k in range(1, 11)))
    print("  r ≥ 1 (D10 henüz gelmedi; kırılma akşamı D10 hedefi tanımlı):", sum(cb[k] for k in range(1, 10)),
          "; r = 0 (b = 10; D10 hedefi kırılma akşamı gerçekleşmiş):", cb[10])
    yrs = Counter(u["d1_date"][:4] for u in units if u["b"] is not None)
    print("  kırılma akşamı olan arzların ilk işlem yılı:", dict(sorted(yrs.items())))
    months_b = {u["brk"]["_date"][:7] for u in units if u["b"] is not None and u["b"] <= 9}
    months_d1 = {u["d1_date"][:7] for u in units if u["b"] is not None and u["b"] <= 9}
    print(f"  b ≤ 9 arzlarda ayrı YYYY-MM: kırılma günü ayı {len(months_b)}, D1 ayı {len(months_d1)} (aralık koşulu ≥ 6 blok için bilgi)")
    print("  ilk işlem ≥ 2024-01-01 olan ve b ≤ 9 olan arz:", sum(1 for u in units if u["b"] is not None and u["b"] <= 9 and u["d1_date"] >= "2024-01-01"),
          "; 2023 fold'ları:", sum(1 for u in units if u["b"] is not None and u["b"] <= 9 and u["d1_date"] < "2024-01-01"))
    print()

    # ---------------------------------------------------------------- 2. kırılma türü
    def kind(f):
        if f["thb_raw_close"] == f["thm_raw_lower_limit"]:
            return "taban"
        if f["thb_raw_close"] < f["thm_raw_reference_price"]:
            return "düşüş"
        return "yükseliş/yatay"

    brk_units = [u for u in units if u["b"] is not None]
    print("## 2. Kırılma türü (b. seans kapanışı; Decimal ham metin)")
    for label, sub in (("bütün kırılmalar (b = 1..10)", brk_units),
                       ("L ≥ 1, b ≤ 9 (orkestratör tablosunun kümesi: 2 ≤ b ≤ 9)", [u for u in brk_units if 2 <= u["b"] <= 9]),
                       ("b = 1 (D1 tavan değil)", [u for u in brk_units if u["b"] == 1]),
                       ("b = 10", [u for u in brk_units if u["b"] == 10])):
        c = Counter(kind(u["brk"]) for u in sub)
        print(f"  {label}: n = {len(sub)}; taban {c['taban']}, düşüş (taban üstü, referans altı) {c['düşüş']}, yükseliş/yatay {c['yükseliş/yatay']}")
    print("  b'ye göre (b: taban / düşüş / yükseliş-yatay):")
    for k in range(1, 11):
        sub = [u for u in brk_units if u["b"] == k]
        c = Counter(kind(u["brk"]) for u in sub)
        print(f"    b = {k:2d}: n = {len(sub):2d}; {c['taban']} / {c['düşüş']} / {c['yükseliş/yatay']}")
    print("  yıla göre (ilk işlem yılı; taban / düşüş / yükseliş-yatay), 2 ≤ b ≤ 9:")
    for y in sorted({u["d1_date"][:4] for u in brk_units}):
        sub = [u for u in brk_units if u["d1_date"][:4] == y and 2 <= u["b"] <= 9]
        c = Counter(kind(u["brk"]) for u in sub)
        print(f"    {y}: n = {len(sub):2d}; {c['taban']} / {c['düşüş']} / {c['yükseliş/yatay']}")
    print()

    # ince tür: kapanışın alt limite adım uzaklığı; kilit (gün boyu taban) ve dokunma ayrımı
    print("## 3. Kırılma günü limit eşitlikleri ve ince tür (2 ≤ b ≤ 9; ayrıca b = 1)")
    for label, sub in (("2 ≤ b ≤ 9", [u for u in brk_units if 2 <= u["b"] <= 9]), ("b = 1", [u for u in brk_units if u["b"] == 1])):
        n = len(sub)
        f = lambda key: sum(1 for u in sub if key(u["brk"]))
        print(f"### {label}: n = {n}")
        print(f"  kapanış == alt limit (taban kapanış): {f(lambda x: x['thb_raw_close'] == x['thm_raw_lower_limit'])} / {n}")
        print(f"  en düşük == alt limit (gün içinde tabana dokundu): {f(lambda x: x['thb_raw_low'] == x['thm_raw_lower_limit'])} / {n}")
        print(f"  en yüksek == alt limit (GÜN BOYU tabanda = taban kilidi; tavan kilidinin aynası): {f(lambda x: x['thb_raw_high'] == x['thm_raw_lower_limit'])} / {n}")
        print(f"  açılış == alt limit: {f(lambda x: x['thb_raw_open'] == x['thm_raw_lower_limit'])} / {n}")
        print(f"  AOF == alt limit: {f(lambda x: x['thb_raw_aof'] == x['thm_raw_lower_limit'])} / {n}")
        print(f"  taban kapanış VE en yüksek > alt limit (gün içinde tabandan yukarıda işlem gördü, tabanda kapandı): "
              f"{f(lambda x: x['thb_raw_close'] == x['thm_raw_lower_limit'] and x['thb_raw_high'] > x['thm_raw_lower_limit'])} / {n}")
        print(f"  tabana dokundu ama taban üstünde kapandı: {f(lambda x: x['thb_raw_low'] == x['thm_raw_lower_limit'] and x['thb_raw_close'] > x['thm_raw_lower_limit'])} / {n}")
        print(f"  en yüksek == üst limit (gün içinde tavana dokundu, tavanda kapanmadı): {f(lambda x: x['thb_raw_high'] == x['thm_raw_upper_limit'])} / {n}")
        print(f"  açılış == üst limit (tavandan açıldı): {f(lambda x: x['thb_raw_open'] == x['thm_raw_upper_limit'])} / {n}")
        print(f"  açılış == referans: {f(lambda x: x['thb_raw_open'] == x['thm_raw_reference_price'])} / {n}; açılış < referans: "
              f"{f(lambda x: x['thb_raw_open'] < x['thm_raw_reference_price'])} / {n}; açılış > referans: {f(lambda x: x['thb_raw_open'] > x['thm_raw_reference_price'])} / {n}")
        print(f"  kapanış ≤ referans (düşüş ya da yatay): {f(lambda x: x['thb_raw_close'] <= x['thm_raw_reference_price'])} / {n}")
        # kapanışın alt limite uzaklığı, adım cinsinden
        dist = []
        for u in sub:
            x = u["brk"]
            s = tick(x["thb_raw_close"])
            dist.append(int(((x["thb_raw_close"] - x["thm_raw_lower_limit"]) / s).to_integral_value()))
        cd = Counter(min(d, 5) for d in dist)
        print("  kapanış − alt limit, fiyat adımı cinsinden (0 = taban; 5 = ≥ 5 adım):", ", ".join(f"{k}: {cd[k]}" for k in range(0, 6)))
        pos = []
        for u in sub:
            x = u["brk"]
            rng = x["thm_raw_upper_limit"] - x["thm_raw_lower_limit"]
            pos.append(float((x["thb_raw_close"] - x["thm_raw_lower_limit"]) / rng) if rng > 0 else None)
        summarize("  kapanışın bant içindeki konumu (0 = alt limit, 1 = üst limit)", pos)
        cpos = Counter("<0.1" if p < 0.1 else "<0.5" if p < 0.5 else "<0.9" if p < 0.9 else "≥0.9" for p in pos if p is not None)
        print("    kutular [0,0.1) / [0.1,0.5) / [0.5,0.9) / [0.9,1]:", cpos["<0.1"], "/", cpos["<0.5"], "/", cpos["<0.9"], "/", cpos["≥0.9"])
        aofpos = []
        for u in sub:
            x = u["brk"]
            rng = x["thm_raw_upper_limit"] - x["thm_raw_lower_limit"]
            aofpos.append(float((x["thb_raw_aof"] - x["thm_raw_lower_limit"]) / rng) if rng > 0 else None)
        summarize("  AOF'nin bant içindeki konumu", aofpos)
        print()

    # ---------------------------------------------------------------- 4. kırılma günü sürekli alanları
    print("## 4. Kırılma günü sürekli alanları (2 ≤ b ≤ 9), kırılma türüne göre alt kümeler (tür = girdi, sonuç değil)")
    sub9 = [u for u in brk_units if 2 <= u["b"] <= 9]
    groups = (("hepsi", sub9), ("taban", [u for u in sub9 if kind(u["brk"]) == "taban"]),
              ("düşüş", [u for u in sub9 if kind(u["brk"]) == "düşüş"]), ("yükseliş/yatay", [u for u in sub9 if kind(u["brk"]) == "yükseliş/yatay"]))
    for label, sub in groups:
        n = len(sub)
        print(f"### {label}: n = {n}")
        if not n:
            continue
        summarize("  el değiştirme_b = hacim_b / shares_offered", [u["brk"]["thb_raw_volume"] / u["shares"] for u in sub], "pay/pay")
        summarize("  ln(el değiştirme_b)", [math.log(float(u["brk"]["thb_raw_volume"] / u["shares"])) for u in sub if u["brk"]["thb_raw_volume"] > 0])
        ratio = []
        for u in sub:
            mean_streak = sum(f["thb_raw_volume"] for f in u["streak"]) / len(u["streak"])
            ratio.append(float(u["brk"]["thb_raw_volume"] / mean_streak) if mean_streak > 0 else None)
        summarize("  hacim_b / ort(hacim D1..D_L) (seri günlerine göre hacim şoku)", ratio)
        last = [u["streak"][-1] for u in sub]
        summarize("  hacim_b / hacim_{b−1} (son tavan gününe göre)", [float(u["brk"]["thb_raw_volume"] / lf["thb_raw_volume"]) for u, lf in zip(sub, last) if lf["thb_raw_volume"] > 0])
        summarize("  sözleşme sayısı_b", [u["brk"]["thb_raw_trade_count"] for u in sub])
        summarize("  pay / sözleşme (b)", [u["brk"]["thb_raw_volume"] / u["brk"]["thb_raw_trade_count"] for u in sub if u["brk"]["thb_raw_trade_count"] > 0])
        summarize("  açılış_b / referans_b − 1", [float(u["brk"]["thb_raw_open"] / u["brk"]["thm_raw_reference_price"] - 1) for u in sub])
        summarize("  kapanış_b / referans_b − 1 (gün getirisi)", [float(u["brk"]["thb_raw_close"] / u["brk"]["thm_raw_reference_price"] - 1) for u in sub])
        summarize("  (en yüksek − en düşük)_b / referans_b (gün içi aralık)", [float((u["brk"]["thb_raw_high"] - u["brk"]["thb_raw_low"]) / u["brk"]["thm_raw_reference_price"]) for u in sub])
        summarize("  kapanış_b / arz fiyatı − 1 (kırılma akşamı yastık, getiri)", [float(u["brk"]["thb_raw_close"] / u["P"] - 1) for u in sub])
        print("  son tavan günü (D_{b−1}) kilitli miydi (en düşük == üst limit):", sum(1 for lf in last if lf["thb_raw_low"] == lf["thm_raw_upper_limit"]), "/", n)
        print("  seri günlerinin hepsi kilitli (D1..D_L en düşük == üst limit):", sum(1 for u in sub if all(f["thb_raw_low"] == f["thm_raw_upper_limit"] for f in u["streak"])), "/", n)
        print("  kırılma günü yarım gün:", sum(1 for u in sub if u["brk"]["_type"] != "OPEN_FULL_DAY"), "/", n,
              "; durdurma kodu:", sum(1 for u in sub if u["brk"]["_status"] != "ACTIVE_NOT_SUSPENDED"), "/", n)
        print()

    # ---------------------------------------------------------------- 5. yastık aritmetiği
    print("## 5. Yastık aritmetiği, kırılma akşamı (b ≤ 9; D10 hedefi henüz gerçekleşmemiş)")
    print("  k_b = ln(kapanış_b / P) / ln(1/0.9); r_b = 10 − b; 'imkânsız' = alt limit zinciri r_b kez uygulanınca bile D10 > P")
    sub = [u for u in brk_units if u["b"] <= 9]
    rows = []
    for u in sub:
        c = u["brk"]["thb_raw_close"]
        r = 10 - u["b"]
        k = math.log(float(c / u["P"])) / LN_STEP if c > 0 else None
        x = c
        for _ in range(r):
            x = lower_limit(x)
        rows.append({"b": u["b"], "r": r, "k": k, "min10": x, "P": u["P"], "impossible": x > u["P"], "approx_impossible": (k is not None and k >= r),
                     "kind": kind(u["brk"]), "year": u["d1_date"][:4], "ratio": float(x / u["P"])})
    n = len(rows)
    print(f"  n = {n}; mekanik olarak imkânsız (adım zinciri): {sum(r['impossible'] for r in rows)}; yaklaşık kural k_b ≥ r_b: {sum(r['approx_impossible'] for r in rows)}; iki kural farklı: {sum(r['impossible'] != r['approx_impossible'] for r in rows)}")
    print("  b'ye göre (b: n, imkânsız):", ", ".join(f"{k}: {sum(1 for r in rows if r['b'] == k)}, {sum(1 for r in rows if r['b'] == k and r['impossible'])}" for k in range(1, 10)))
    print("  türe göre (tür: n, imkânsız):", ", ".join(f"{t}: {sum(1 for r in rows if r['kind'] == t)}, {sum(1 for r in rows if r['kind'] == t and r['impossible'])}" for t in ("taban", "düşüş", "yükseliş/yatay")))
    print("  yıla göre (yıl: n, imkânsız):", ", ".join(f"{y}: {sum(1 for r in rows if r['year'] == y)}, {sum(1 for r in rows if r['year'] == y and r['impossible'])}" for y in sorted({r['year'] for r in rows})))
    summarize("  k_b (yastık, limit adımı cinsinden)", [r["k"] for r in rows])
    summarize("  k_b − r_b (negatif = arz altı mekanik olarak mümkün)", [r["k"] - r["r"] for r in rows if r["k"] is not None])
    summarize("  mümkün en düşük D10 / P (adım zinciri)", [r["ratio"] for r in rows])
    feas = [r for r in rows if not r["impossible"]]
    print(f"  mümkün olan {len(feas)} arzda: ", end="")
    print("b'ye göre:", ", ".join(f"{k}: {sum(1 for r in feas if r['b'] == k)}" for k in range(1, 10)), "; türe göre:",
          ", ".join(f"{t}: {sum(1 for r in feas if r['kind'] == t)}" for t in ("taban", "düşüş", "yükseliş/yatay")))
    print("  mümkün olanlarda 'bütün kalan günler taban olmalı' (mümkün en düşük D10 / P ∈ (0.9, 1]):", sum(1 for r in feas if r["ratio"] > 0.9), "/", len(feas))
    print("  ilk işlem ≥ 2024-01-01 ve mümkün:", sum(1 for u, r in zip(sub, rows) if u["d1_date"] >= "2024-01-01" and not r["impossible"]), "/",
          sum(1 for u in sub if u["d1_date"] >= "2024-01-01"))
    print()

    # ---------------------------------------------------------------- 6. seri sırasında (D1..D_L) alanlar — bilgi
    print("## 6. Seri günleri (D1..D_L) özetleri, 2 ≤ b ≤ 9 (yalnız girdi; sonuç yok)")
    sub = [u for u in brk_units if 2 <= u["b"] <= 9]
    summarize("  seri günlerinde ortalama el değiştirme (hacim/shares_offered)", [float(sum(f["thb_raw_volume"] for f in u["streak"]) / len(u["streak"]) / u["shares"]) for u in sub])
    summarize("  D1 el değiştirme", [float(u["streak"][0]["thb_raw_volume"] / u["shares"]) for u in sub])
    summarize("  D_{b−1} (son tavan günü) el değiştirme", [float(u["streak"][-1]["thb_raw_volume"] / u["shares"]) for u in sub])
    print("  D1 kilitli (en düşük == üst limit):", sum(1 for u in sub if u["streak"][0]["thb_raw_low"] == u["streak"][0]["thm_raw_upper_limit"]), "/", len(sub))
    print("  seri boyunca kilitsiz gün sayısı dağılımı:", dict(sorted(Counter(sum(1 for f in u["streak"] if f["thb_raw_low"] != f["thm_raw_upper_limit"]) for u in sub).items())))
    print()

    # ---------------------------------------------------------------- 7. b = 1 ve b = 10 notları
    print("## 7. Uç durumlar")
    b1 = [u for u in brk_units if u["b"] == 1]
    print(f"  b = 1 (D1 tavan değil): n = {len(b1)}; taban kapanış {sum(1 for u in b1 if kind(u['brk']) == 'taban')}; D1 kapanış ≤ arz fiyatı "
          f"{sum(1 for u in b1 if u['brk']['thb_raw_close'] <= u['P'])}; D1 kapanış < referans {sum(1 for u in b1 if u['brk']['thb_raw_close'] < u['brk']['thm_raw_reference_price'])}")
    b10 = [u for u in brk_units if u["b"] == 10]
    print(f"  b = 10: n = {len(b10)} (kırılma akşamı = D10 akşamı; D10 hedefi gerçekleşmiş, model çağrılmaz)")
    print("  kırılma günü yarım gün olan arz (bütün b):", sum(1 for u in brk_units if u["brk"]["_type"] != "OPEN_FULL_DAY"),
          "; durdurma:", sum(1 for u in brk_units if u["brk"]["_status"] != "ACTIVE_NOT_SUSPENDED"))
    print("  kırılma günü alt limit boş/≤ 0:", sum(1 for u in brk_units if u["brk"]["thm_raw_lower_limit"] <= 0),
          "; üst limit/referans aralığı:", f"{min(float(u['brk']['thm_raw_upper_limit'] / u['brk']['thm_raw_reference_price']) for u in brk_units):.5f}",
          "…", f"{max(float(u['brk']['thm_raw_upper_limit'] / u['brk']['thm_raw_reference_price']) for u in brk_units):.5f}",
          "; alt limit/referans:", f"{min(float(u['brk']['thm_raw_lower_limit'] / u['brk']['thm_raw_reference_price']) for u in brk_units):.5f}",
          "…", f"{max(float(u['brk']['thm_raw_lower_limit'] / u['brk']['thm_raw_reference_price']) for u in brk_units):.5f}")
    print("  referans_b == kapanış_{b−1} (2 ≤ b):", sum(1 for u in brk_units if u["b"] >= 2 and u["brk"]["thm_raw_reference_price"] == u["streak"][-1]["thb_raw_close"]), "/",
          sum(1 for u in brk_units if u["b"] >= 2))
    print("  alt limit zinciri doğrulaması (Lo(referans_b) == alt limit_b):", sum(1 for u in brk_units if lower_limit(u["brk"]["thm_raw_reference_price"]) == u["brk"]["thm_raw_lower_limit"]), "/", len(brk_units))


if __name__ == "__main__":
    main()

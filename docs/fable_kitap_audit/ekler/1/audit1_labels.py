"""KITAP_AUDIT_1 Adım 1: etiketleri ham bülten metninden (SESSIONS thb_raw_*/thm_raw_*) sıfırdan üret, tablolarla karşılaştır.
borsai import edilmez. Yalnız stdlib. Çıktıya bülten dosya adı yazılmaz."""
import csv, sys
from collections import Counter
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data" / "raw"
def rd(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))

sess = rd(RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv")
targ = rd(RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv")
master = {r["ticker"]: r for r in rd(RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv")}
tt = {r["ticker"]: r for r in rd(ROOT / "data" / "training_table.csv")}
tt2 = {r["ticker"]: r for r in rd(ROOT / "data" / "training_table_v2.csv") if r["cohort"] == "H99"}
out = []
P = lambda *a: out.append(" ".join(str(x) for x in a))

P("[ÖLÇTÜM] SESSIONS satır", len(sess), "TARGETS satır", len(targ), "tablo satır", len(tt), "v2 H99 satır", len(tt2))
# ham == normalleştirilmiş?
pairs = [("thb_raw_open","open"),("thb_raw_high","high"),("thb_raw_low","low"),("thb_raw_close","close"),("thb_raw_volume","volume"),
         ("thb_raw_turnover","turnover"),("thb_raw_aof","aof"),("thb_raw_trade_count","trade_count"),("thm_raw_reference_price","reference_price"),
         ("thm_raw_upper_limit","upper_limit"),("thm_raw_lower_limit","lower_limit")]
str_diff = Counter(); dec_diff = Counter()
for r in sess:
    for a, b in pairs:
        if r[a] != r[b]: str_diff[a] += 1
        if Decimal(r[a]) != Decimal(r[b]): dec_diff[a] += 1
P("[ÖLÇTÜM] ham≠normalleştirilmiş (metin):", dict(str_diff) or 0, "| (Decimal):", dict(dec_diff) or 0)
P("[ÖLÇTÜM] security_trading_status:", dict(Counter(r["security_trading_status"] for r in sess)))
P("[ÖLÇTÜM] session_type:", dict(Counter(r["session_type"] for r in sess)))
half = [(r["ticker"], int(r["session_number"]), r["target_session_date"]) for r in sess if r["session_type"] == "OPEN_HALF_DAY"]
P("[ÖLÇTÜM] yarım gün seansları:", sorted(half, key=lambda x: x[2]))

by = {}
for r in sess:
    by.setdefault(r["ticker"], {})[int(r["session_number"])] = r
assert all(sorted(v) == list(range(1, 11)) for v in by.values())

def exact_return(close, price):
    c, p = Fraction(Decimal(close)), Fraction(Decimal(price))
    r = c / p - 1
    if r == 0: return "0", 0
    with localcontext() as ctx:
        ctx.prec = 50
        return format(Decimal(r.numerator) / Decimal(r.denominator), "f").rstrip("0").rstrip("."), int(r > 0)

# tavan etiketi, L, R_h, Y_h
ceil_cnt = Counter(); L_dist = Counter(); mism = []; r_mism = []; y_mism = []; v2_mism = 0
close_gt_upper = close_lt_lower = 0
ratio_min, ratio_max = Decimal(10), Decimal(0)
d1_ceiling = []; d1_ref_ne_price = []
for t, ses in by.items():
    labels = []
    for k in range(1, 11):
        s = ses[k]
        c, u, lo, ref = (Decimal(s[x]) for x in ("thb_raw_close", "thm_raw_upper_limit", "thm_raw_lower_limit", "thm_raw_reference_price"))
        if c > u: close_gt_upper += 1
        if c < lo: close_lt_lower += 1
        ratio = u / ref; ratio_min, ratio_max = min(ratio_min, ratio), max(ratio_max, ratio)
        lab = int(c == u); labels.append(lab)
        if lab: ceil_cnt[k] += 1
        if str(lab) != tt[t][f"ceiling_close_D{k}"]: mism.append((t, k, lab, tt[t][f"ceiling_close_D{k}"]))
    L = 0
    for x in labels:
        if x == 0: break
        L += 1
    L_dist[L] += 1
    if str(L) != tt[t]["ceiling_streak_L"]: mism.append((t, "L", L, tt[t]["ceiling_streak_L"]))
    price = master[t]["ipo_price"]
    for h in (1, 3, 5, 10):
        rtxt, y = exact_return(ses[h]["thb_raw_close"], price)
        if rtxt != tt[t][f"R_D{h}"] or Decimal(rtxt) != Decimal(tt[t][f"R_D{h}"]): r_mism.append((t, h, rtxt[:12], tt[t][f"R_D{h}"][:12]))
        if str(y) != tt[t][f"Y_D{h}"]: y_mism.append((t, h, y, tt[t][f"Y_D{h}"]))
    # v2 H99 satırı tabloyla aynı mı
    if any(tt2[t][c] != tt[t][c] for c in tt[t]): v2_mism += 1
    if labels[0] == 1:
        d1_ceiling.append((t, Decimal(tt[t]["R_D1"])))
    d1ref = Decimal(ses[1]["thm_raw_reference_price"])
    if d1ref != Decimal(price): d1_ref_ne_price.append((t, str(price), str(d1ref)))

P("[ÖLÇTÜM] kapanış > üst limit:", close_gt_upper, "| kapanış < alt limit:", close_lt_lower)
P("[ÖLÇTÜM] üst limit/referans aralığı:", f"{ratio_min:.6f}…{ratio_max:.6f}")
P("[ÖLÇTÜM] seans başına tavan (D1..D10):", [ceil_cnt[k] for k in range(1, 11)])
P("[ÖLÇTÜM] L dağılımı 0..10:", [L_dist[k] for k in range(11)], "| L≥1/3/5/10:", [sum(v for k, v in L_dist.items() if k >= m) for m in (1, 3, 5, 10)])
P("[ÖLÇTÜM] tavan/L uyuşmazlığı tabloyla:", len(mism), mism[:5])
P("[ÖLÇTÜM] R_h metin uyuşmazlığı:", len(r_mism), r_mism[:5], "| Y_h uyuşmazlığı:", len(y_mism), y_mism[:5])
P("[ÖLÇTÜM] v2 H99 satırlarında 31 sütun v1'den farklı olan arz:", v2_mism)
yc = {h: sum(int(tt[t][f"Y_D{h}"]) for t in tt) for h in (1, 3, 5, 10)}
P("[ÖLÇTÜM] Y=1 sayıları D1/D3/D5/D10:", yc)
P("[ÖLÇTÜM] D1 referans ≠ arz fiyatı:", d1_ref_ne_price)
exact01 = [t for t, r in d1_ceiling if r == Decimal("0.1")]
P("[ÖLÇTÜM] D1 tavan kapatan:", len(d1_ceiling), "| R_D1 tam 0.1:", len(exact01), "| min:", min(r for _, r in d1_ceiling), "| max:", max(r for _, r in d1_ceiling),
  "| >0.1:", [(t, str(r)[:9]) for t, r in d1_ceiling if r > Decimal("0.1")])

# TARGETS ile karşılaştırma
tg = {(r["ticker"], r["horizon"]): r for r in targ}
tdiff = 0
for t, ses in by.items():
    for h in (1, 3, 5, 10):
        g = tg[(t, f"D{h}")]
        if g["target_session_date"] != ses[h]["target_session_date"] or Decimal(g["official_close"]) != Decimal(ses[h]["thb_raw_close"]) \
           or Decimal(g["ipo_price"]) != Decimal(master[t]["ipo_price"]) or g["target_return"] != exact_return(ses[h]["thb_raw_close"], master[t]["ipo_price"])[0]:
            tdiff += 1
        fr = Fraction(Decimal(ses[h]["thb_raw_close"])) / Fraction(Decimal(master[t]["ipo_price"])) - 1
        if fr != Fraction(int(g["target_return_exact_numerator"]), int(g["target_return_exact_denominator"])): tdiff += 1
P("[ÖLÇTÜM] TARGETS ↔ SESSIONS/MASTER/kesin kesir uyuşmazlığı:", tdiff, "(396 hedef)")

# Fiyat adımı: üst limit = ref*1.1'in adıma yuvarlanmışı mı? (adım tablosu: fiyat düzeyine göre)
def tick(p):
    for lim, tk in ((20, "0.01"), (50, "0.02"), (100, "0.05"), (250, "0.1"), (500, "0.25"), (1000, "0.5"), (2500, "1")):
        if p < lim: return Decimal(tk)
    return Decimal("2.5")
variants = Counter(); fails = []
for t, ses in by.items():
    for k in range(1, 11):
        s = ses[k]; ref = Decimal(s["thm_raw_reference_price"]); u = Decimal(s["thm_raw_upper_limit"]); lo = Decimal(s["thm_raw_lower_limit"])
        raw_u, raw_l = ref * Decimal("1.1"), ref * Decimal("0.9")
        ok = {}
        for name, base in (("adım(ref)", ref), ("adım(ham üst)", raw_u)):
            tk = tick(base)
            ok[name + "/floor"] = (raw_u / tk).to_integral_value(rounding=ROUND_FLOOR) * tk == u
            ok[name + "/round"] = (raw_u / tk).quantize(Decimal(1)) * tk == u
        tkl = tick(raw_l)
        ok["alt: adım(ham alt)/ceil"] = (raw_l / tkl).to_integral_value(rounding=ROUND_CEILING) * tkl == lo
        ok["alt: adım(ham alt)/round"] = (raw_l / tkl).quantize(Decimal(1)) * tkl == lo
        for n, v in ok.items(): variants[n] += int(v)
        if not ok["adım(ham üst)/floor"]: fails.append((t, k, str(ref), str(u)))
P("[ÖLÇTÜM] üst/alt limit = ref×1.1 / ref×0.9 adıma yuvarlama varyantlarının tuttuğu seans sayısı (990):", dict(variants))
P("[ÖLÇTÜM] 'adım(ham üst)/floor' tutmayan seanslar (ilk 10):", fails[:10], "toplam", len(fails))

# NETGL (data/outcomes) kontrolü — §3.5.5
net = rd(ROOT / "data" / "outcomes" / "NETGL.csv")
labs = [int(r["ceiling_close"]) for r in net]
L = 0
for x in labs:
    if x == 0: break
    L += 1
r10, y10 = exact_return(net[9]["close_raw"], "25.52"); r1, _ = exact_return(net[0]["close_raw"], "25.52")
P("[ÖLÇTÜM] NETGL: L =", L, "| R_D10 =", r10, "| Y_D10 =", y10, "| R_D1 =", r1[:14], "| 1629/2552-1 =", Fraction(1629, 2552) - 1,
  "| dosya R_D10 eşit:", net[9]["R_h"] == r10, "| D4 alt limit =", net[3]["upper_limit_raw"], "(ref", net[3]["reference_raw"], ")")
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))

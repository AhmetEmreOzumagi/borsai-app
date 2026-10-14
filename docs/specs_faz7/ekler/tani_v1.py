"""Faz 7 tanı (KEŞİF): `ceiling_hazard_v0`'ın açık kümedeki hatasının kaynağı.

Görev: BORSAI_FAZ7_FABLE_HAZARD_V1_SPEC_20260925, adım 2. Kurallar:
- Yalnız okur: donmuş model JSON'u, S2 kayıtları (yalnız açık küme), açık küme sonuçları,
  H99 eğitim tablosu, v0/KM fold ledger'ları (H99 backtest).
- Kasa (SEALED) üyelerinin HİÇBİR dosyası açılmaz: kohort dosyasından vault ∈ {OPEN,
  EXPOSED_ARCHIVE, EXPOSED_CODEX} olanlar seçilir; başka dizin taranmaz.
- Hiçbir model fit edilmez, walk-forward skorlanmaz. Tek "duyarlılık" hesabı (§6) donmuş
  v0'ın parametreleriyle, yalnız girdi z'si kırpılarak yapılır (aday fit değildir).
- Hiçbir üye kodu basılmaz; yalnız toplam ve kutu istatistikleri.
Çıktı: ekler/tani_v1_cikti.txt (komut: .venv/bin/python docs/specs_faz7/ekler/tani_v1.py)
"""
from __future__ import annotations

import csv
import glob
import json
import math
import statistics as st
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from borsai import survival as sv  # noqa: E402
from borsai.data import load_dataset  # noqa: E402
from borsai.features import compute_features  # noqa: E402
from borsai.predict import z_vector  # noqa: E402
from borsai.preprocess import quantile_type7  # noqa: E402

OPEN_VAULTS = {"OPEN", "EXPOSED_ARCHIVE", "EXPOSED_CODEX"}
V0 = "ceiling_hazard_v0"
KM = "base_km_expanding"
KS = (1, 2, 3, 5, 10)

out_lines: list[str] = []


def w(s: str = "") -> None:
    out_lines.append(s)


def q(vals, p):
    return float(quantile_type7(sorted(Fraction(v) for v in vals), Fraction(p)))


def fmt(x, nd=3):
    return "—" if x is None else f"{x:+.{nd}f}" if isinstance(x, float) and nd else str(x)


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


# ---------------------------------------------------------------- yükle
params = json.loads((ROOT / "models" / f"{V0}.json").read_text())
prep = params["preprocessing"]
beta = params["beta"]
gamma = params["gamma"]

cohort = list(csv.DictReader(open(ROOT / "registry/oot/cohort_pre_h99.csv")))
open_rows = [r for r in cohort if r["status"] == "MEMBER" and r["vault"] in OPEN_VAULTS]
assert len(open_rows) == 71, len(open_rows)
assert all(r["vault"] != "SEALED" for r in open_rows)


def regime(r):
    tags = dict(t.split("=", 1) for t in r["regime_tags"].split("|") if "=" in t)
    return tags.get("ALLOC_REGIME")


members = []
for r in open_rows:
    t = r["ticker"]
    recs = sorted(glob.glob(str(ROOT / "registry/oot/records" / t / "*.json")))
    rec = json.load(open(recs[0]))
    assert rec["vault"] in OPEN_VAULTS
    cell = next(m for m in rec["models"] if m["model_id"] == V0)
    km = rec["comparators"][KM]
    mi = rec["model_inputs"]
    # sonuç (açık küme; MACHINE_EXTRACTED)
    oc = list(csv.DictReader(open(ROOT / "data/outcomes_oot" / f"{t}.csv")))
    closes = []
    for row in sorted(oc, key=lambda x: int(x["h"])):
        v = row["ceiling_close"]
        closes.append(None if v in ("", "NA") else int(v))
    L = 0
    for c in closes:
        if c == 1:
            L += 1
        else:
            break
    m = {
        "year": r["year"], "regime": regime(r), "sale": r["sale_method"], "market": r["market"],
        "ftd": r["first_trading_date"], "L": L, "closes": closes, "status": cell["status"],
        "S": cell["output"]["S"] if cell["status"] == "PREDICTED" else None,
        "warn": [x["code"] + ":" + str(x.get("feature")) for x in (cell["output"] or {}).get("warnings", [])]
        if cell["status"] == "PREDICTED" else [],
        "kmS": km["output"]["S"] if km.get("output") else None,
        "inputs": mi,
    }
    if cell["status"] == "PREDICTED":
        f = compute_features(ipo_price_tl=mi["ipo_price_tl"], shares_offered=mi["shares_offered"],
                             post_ipo_share_capital=mi["post_ipo_share_capital"],
                             capital_increase_shares=mi["capital_increase_shares"],
                             total_demand_multiple=mi["total_demand_multiple"], ipo_size_tl=mi["ipo_size_tl"])
        vals = {k: float(v) for k, v in f.as_dict().items() if k in ("f1", "f2", "f3")}
        m["z"] = dict(zip(prep["columns"], z_vector(prep, vals)))
        # ham f1 TL büyüklüğüdür (ln ön işlemede); tanıda f1 = ln(büyüklük) olarak taşınır
        m["raw"] = {"f1": math.log(vals["f1"]), "f2": vals["f2"], "f3": vals["f3"]}
        # parite: donmuş JSON'dan S yeniden kurulunca kayıttaki S ile eşit mi
        lin = sum(beta[c] * m["z"][c] for c in m["z"])
        S = sv.survival([sv.sigmoid(gamma[sv.GROUP_OF_DAY[d]] + lin) for d in range(1, 11)])
        assert max(abs(a - b) for a, b in zip(S, m["S"])) < 1e-9
        m["lin"] = lin
    members.append(m)

scored = [m for m in members if m["status"] == "PREDICTED"]
assert len(scored) == 68, len(scored)

# H99
ds = load_dataset()
h99 = []
for row in ds.rows:
    f = compute_features(**row.feature_inputs())
    d = f.as_dict()
    h99.append({"ftd": row.first_trading_date, "year": row.first_trading_date[:4], "L": row.ceiling_streak,
                "f1": math.log(float(d["f1"])), "f2": float(d["f2"]), "f3": None if d["f3"] is None else float(d["f3"]),
                "size_tl": float(d["f1"])})
h99_f3 = [h for h in h99 if h["f3"] is not None]
assert len(h99_f3) == 97


def rps(S, L):
    return sv.rps(S, L)


def obs(ms, k):
    return mean(1.0 if m["L"] >= k else 0.0 for m in ms)


# ---------------------------------------------------------------- §1 girdi aralığı
w("# Faz 7 tanı çıktısı (KEŞİF; sonuç görüldükten sonra hesaplandı; hüküm değildir)")
w(f"Açık küme: {len(members)} üye; v0 skorlanan {len(scored)}; H99: 99 arz, f3'lü 97.")
w("Hiçbir üye kodu yok. Sayılar açık küme (OPEN ∪ EXPOSED_*) ve H99 üzerindedir; kasa üyesi hiçbir dosya açılmadı.")
w()
w("## 1. Özellik aralıkları: H99 eğitim (97) ile açık küme (68 skorlanan)")
w()
w("f1 = ln(arz büyüklüğü, nominal TL). Eğitim ortalaması/std (JSON): "
  f"{prep['mean']['f1']:.3f} / {prep['std']['f1']:.3f}; eğitim min–max TL: "
  f"{params['feature_ranges']['f1']['min']:,.0f} – {params['feature_ranges']['f1']['max']:,.0f}")
w()
w("| küme | n | f1 min | p05 | p25 | medyan | p75 | p95 | max | medyan TL (mn) |")
w("|---|---|---|---|---|---|---|---|---|---|")


def f1row(label, vals):
    vals = sorted(vals)
    w(f"| {label} | {len(vals)} | {vals[0]:.2f} | {q(vals,0.05):.2f} | {q(vals,0.25):.2f} | {q(vals,0.5):.2f} | "
      f"{q(vals,0.75):.2f} | {q(vals,0.95):.2f} | {vals[-1]:.2f} | {math.exp(q(vals,0.5))/1e6:,.0f} |")


f1row("H99 f3'lü (eğitim)", [h["f1"] for h in h99_f3])
for y in ("2023", "2024", "2025", "2026"):
    f1row(f"H99 {y}", [h["f1"] for h in h99_f3 if h["year"] == y])
f1row("açık küme (68)", [m["raw"]["f1"] for m in scored])
for y in ("2020", "2021", "2022", "2023"):
    vs = [m["raw"]["f1"] for m in scored if m["year"] == y]
    if vs:
        f1row(f"açık {y}", vs)
for rg in ("PRE_20211111", "THRESH100_20211111", "EQUAL_DIST_20230330"):
    f1row(f"açık {rg}", [m["raw"]["f1"] for m in scored if m["regime"] == rg])
w()
f1min = params["feature_ranges"]["f1"]["min"]
f1p05 = q([h["f1"] for h in h99_f3], 0.05)
f2p05, f2p95 = q([h["f2"] for h in h99_f3], 0.05), q([h["f2"] for h in h99_f3], 0.95)
w(f"H99 f1 p05 = {f1p05:.3f} (ln) = {math.exp(f1p05)/1e6:,.0f} mn TL; z(p05) = {(f1p05-prep['mean']['f1'])/prep['std']['f1']:+.2f}; "
  f"z(min) = {(math.log(f1min)-prep['mean']['f1'])/prep['std']['f1']:+.2f}")
n_below_min = sum(m["raw"]["f1"] < math.log(f1min) for m in scored)
n_below_p05 = sum(m["raw"]["f1"] < f1p05 for m in scored)
w(f"Açık kümede f1 < H99 min: {n_below_min}/68; f1 < H99 p05: {n_below_p05}/68")
for y in ("2020", "2021", "2022", "2023"):
    ms = [m for m in scored if m["year"] == y]
    if ms:
        w(f"- {y}: n {len(ms)}, f1 < min {sum(m['raw']['f1'] < math.log(f1min) for m in ms)}, "
          f"f1 < p05 {sum(m['raw']['f1'] < f1p05 for m in ms)}, medyan z_f1 {q([m['z']['f1'] for m in ms],0.5):+.2f}, "
          f"min z_f1 {min(m['z']['f1'] for m in ms):+.2f}")
w()
w("z-skor dağılımları (donmuş ön işleme; f3 z'si kırpılmış değerden):")
w()
w("| küme | z_f1 min / medyan / max | z_f2 min / medyan / max | z_f3 min / medyan / max | f3 kırpılan (p05 altı / p95 üstü) |")
w("|---|---|---|---|---|")


def zrow(label, ms):
    def trip(c):
        vs = [m["z"][c] for m in ms]
        return f"{min(vs):+.2f} / {q(vs,0.5):+.2f} / {max(vs):+.2f}"
    lo = sum(m["raw"]["f3"] < prep["winsor"]["f3"]["p05"] for m in ms)
    hi = sum(m["raw"]["f3"] > prep["winsor"]["f3"]["p95"] for m in ms)
    w(f"| {label} | {trip('f1')} | {trip('f2')} | {trip('f3')} | {lo} / {hi} |")


zrow("açık küme (68)", scored)
for y in ("2020", "2021", "2022", "2023"):
    ms = [m for m in scored if m["year"] == y]
    if ms:
        zrow(f"açık {y}", ms)
w()
wc = Counter(x for m in scored for x in m["warn"])
w(f"Kayıttaki uyarılar (68 skorlanan): {dict(wc)}")
w("f2 H99 p05/p95: " + f"{f2p05:.2f} / {f2p95:.2f}; açık kümede f2 < p05: "
  f"{sum(m['raw']['f2'] < f2p05 for m in scored)}, > p95: {sum(m['raw']['f2'] > f2p95 for m in scored)}")
w()
w("Ham f3 (talep katı) kutuları: H99 f3'lü 97 / açık 68")
w()
w("| küme | f3 min | p25 | medyan | p75 | max | ort |")
w("|---|---|---|---|---|---|---|")
for label, vs in (("H99", [h["f3"] for h in h99_f3]), ("açık", [m["raw"]["f3"] for m in scored]),
                  *((f"açık {y}", [m["raw"]["f3"] for m in scored if m["year"] == y]) for y in ("2021", "2022", "2023"))):
    vs = sorted(vs)
    w(f"| {label} | {vs[0]:.2f} | {q(vs,0.25):.2f} | {q(vs,0.5):.2f} | {q(vs,0.75):.2f} | {vs[-1]:.2f} | {mean(vs):.2f} |")
w()
w("Satış yöntemi ve f3 (açık küme 71): " + str(Counter((m["sale"], m["status"]) for m in members)))
w()

# ---------------------------------------------------------------- §2 doğrusal öngörücü ayrışımı
w("## 2. Doğrusal öngörücünün (β·z) özellik payları — ortalama, hazard logit'i üzerinde")
w()
w(f"β (JSON): f1 {beta['f1']:+.3f}, f2 {beta['f2']:+.3f}, f3 {beta['f3']:+.3f}. Negatif pay = hazard düşer = seri uzar.")
w()
w("| küme | n | β_f1·z_f1 | β_f2·z_f2 | β_f3·z_f3 | toplam β·z | ort L gözlenen |")
w("|---|---|---|---|---|---|---|")


def linrow(label, ms):
    parts = {c: mean(beta[c] * m["z"][c] for m in ms) for c in ("f1", "f2", "f3")}
    w(f"| {label} | {len(ms)} | {parts['f1']:+.3f} | {parts['f2']:+.3f} | {parts['f3']:+.3f} | "
      f"{sum(parts.values()):+.3f} | {mean(m['L'] for m in ms):.2f} |")


linrow("açık (68)", scored)
for y in ("2020", "2021", "2022", "2023"):
    ms = [m for m in scored if m["year"] == y]
    if ms:
        linrow(f"açık {y}", ms)
for rg in ("PRE_20211111", "THRESH100_20211111", "EQUAL_DIST_20230330"):
    linrow(f"açık {rg}", [m for m in scored if m["regime"] == rg])
w()
w("Karşılaştırma: H99 eğitiminde β·z'nin ortalaması tanım gereği 0 (z ortalaması 0).")
w()

# ---------------------------------------------------------------- §3 kalibrasyon kutuları
w("## 3. Kalibrasyon: ortalama S_k (v0 / donmuş H99 KM) ve gözlenen P(L ≥ k); RPS")
w()


def calib_table(title, groups):
    w(f"### {title}")
    w()
    w("| kutu | n | k=1 v0/KM/göz | k=2 | k=3 | k=5 | k=10 | RPS v0 | RPS KM | fark | v0 iyi/kötü |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for label, ms in groups:
        if not ms:
            continue
        cells = []
        for k in KS:
            cells.append(f"{mean(m['S'][k-1] for m in ms):.2f}/{mean(m['kmS'][k-1] for m in ms):.2f}/{obs(ms,k):.2f}")
        r0 = mean(rps(m["S"], m["L"]) for m in ms)
        rk = mean(rps(m["kmS"], m["L"]) for m in ms)
        wins = sum(rps(m["S"], m["L"]) < rps(m["kmS"], m["L"]) for m in ms)
        w(f"| {label} | {len(ms)} | " + " | ".join(cells) + f" | {r0:.3f} | {rk:.3f} | {r0-rk:+.3f} | {wins}/{len(ms)-wins} |")
    w()


zb = [("z_f1 < −2", lambda m: m["z"]["f1"] < -2), ("−2 ≤ z_f1 < −1", lambda m: -2 <= m["z"]["f1"] < -1),
      ("−1 ≤ z_f1 < 0", lambda m: -1 <= m["z"]["f1"] < 0), ("z_f1 ≥ 0", lambda m: m["z"]["f1"] >= 0)]
calib_table("3.1 z_f1 kutuları (açık küme, 68)", [(lb, [m for m in scored if f(m)]) for lb, f in zb])
zb2 = [("z_f2 < −1", lambda m: m["z"]["f2"] < -1), ("−1 ≤ z_f2 < 0", lambda m: -1 <= m["z"]["f2"] < 0),
       ("0 ≤ z_f2 < 1", lambda m: 0 <= m["z"]["f2"] < 1), ("z_f2 ≥ 1", lambda m: m["z"]["f2"] >= 1)]
calib_table("3.2 z_f2 kutuları", [(lb, [m for m in scored if f(m)]) for lb, f in zb2])
zb3 = [("z_f3 < −0.5", lambda m: m["z"]["f3"] < -0.5), ("−0.5 ≤ z_f3 < 0.5", lambda m: -0.5 <= m["z"]["f3"] < 0.5),
       ("z_f3 ≥ 0.5", lambda m: m["z"]["f3"] >= 0.5)]
calib_table("3.3 z_f3 kutuları", [(lb, [m for m in scored if f(m)]) for lb, f in zb3])
calib_table("3.4 yıl", [(y, [m for m in scored if m["year"] == y]) for y in ("2020", "2021", "2022", "2023")])
calib_table("3.5 tahsis rejimi", [(rg, [m for m in scored if m["regime"] == rg])
                                   for rg in ("PRE_20211111", "THRESH100_20211111", "EQUAL_DIST_20230330")])
calib_table("3.6 satış yöntemi / pazar", [("borsa dışı", [m for m in scored if m["sale"] == "OFF_EXCHANGE_BOOKBUILD"]),
                                          ("borsada satış", [m for m in scored if m["sale"] == "ON_EXCHANGE"]),
                                          ("YILDIZ", [m for m in scored if m["market"] == "YILDIZ"]),
                                          ("ANA", [m for m in scored if m["market"] == "ANA"])])
# yıl × z_f1 çapraz
calib_table("3.7 yıl × (z_f1 < −1 / ≥ −1)",
            [(f"{y} z_f1<−1", [m for m in scored if m["year"] == y and m["z"]["f1"] < -1]) for y in ("2021", "2022", "2023")]
            + [(f"{y} z_f1≥−1", [m for m in scored if m["year"] == y and m["z"]["f1"] >= -1]) for y in ("2021", "2022", "2023")])

# ---------------------------------------------------------------- §4 dönem başına KM
w("## 4. Dönem başına Kaplan–Meier (sonuçtan kurulan eğriler; keşif)")
w()
w("| dönem | n | olay | S_1 | S_2 | S_3 | S_5 | S_10 | ort L | L=0 | L=10 |")
w("|---|---|---|---|---|---|---|---|---|---|---|")


def km_row(label, Ls):
    units = [sv.Unit(f"u{i}", "x", L, tuple(["x"] * 10), tuple([1] * L + [0] * (10 - L))) for i, L in enumerate(Ls)]
    rows = sv.pp_table(units)
    S = sv.survival(sv.km_hazards(rows))
    ev = sum(r.event for r in rows)
    w(f"| {label} | {len(Ls)} | {ev} | {S[0]:.2f} | {S[1]:.2f} | {S[2]:.2f} | {S[4]:.2f} | {S[9]:.2f} | "
      f"{mean(Ls):.2f} | {sum(L == 0 for L in Ls)} | {sum(L == 10 for L in Ls)} |")


allo = [m for m in members]
for y in ("2020", "2021", "2022", "2023"):
    km_row(f"açık {y} (71'lik)", [m["L"] for m in allo if m["year"] == y])
for rg in ("PRE_20211111", "THRESH100_20211111", "EQUAL_DIST_20230330"):
    km_row(f"açık {rg}", [m["L"] for m in allo if m["regime"] == rg])
km_row("açık küme (71)", [m["L"] for m in allo])
km_row("açık f3'lü (68)", [m["L"] for m in scored])
for y in ("2023", "2024", "2025", "2026"):
    km_row(f"H99 {y}", [h["L"] for h in h99 if h["year"] == y])
km_row("H99 (99)", [h["L"] for h in h99])
w()
w(f"Donmuş H99 KM (kayıttaki karşılaştırıcı; 97 f3'lü): S_1 {scored[0]['kmS'][0]:.3f}, S_3 {scored[0]['kmS'][2]:.3f}, "
  f"S_5 {scored[0]['kmS'][4]:.3f}, S_10 {scored[0]['kmS'][9]:.3f}")
w()

# ---------------------------------------------------------------- §5 bütçe
w("## 5. Havuzlanmış eğitim bütçesi (kişi-dönem satırları; açık küme f3'lü 68 + H99 f3'lü 97)")
w()
w("| küme | arz | PP satırı | olay | sağ kalım | g1 olay/risk | g2 | g3 |")
w("|---|---|---|---|---|---|---|---|")


def pp_stats(label, Ls):
    units = [sv.Unit(f"u{i}", "x", L, tuple(["x"] * 10), tuple([1] * L + [0] * (10 - L))) for i, L in enumerate(Ls)]
    rows = sv.pp_table(units)
    ev, risk = sv.group_counts(rows)
    e = sum(ev)
    w(f"| {label} | {len(Ls)} | {len(rows)} | {e} | {len(rows)-e} | {ev[0]}/{risk[0]} | {ev[1]}/{risk[1]} | {ev[2]}/{risk[2]} |")
    return len(rows), e


pp_stats("H99 f3'lü", [h["L"] for h in h99_f3])
for rg in ("PRE_20211111", "THRESH100_20211111", "EQUAL_DIST_20230330"):
    pp_stats(f"açık {rg}", [m["L"] for m in scored if m["regime"] == rg])
pp_stats("açık f3'lü", [m["L"] for m in scored])
pp_stats("havuz (H99 + açık)", [h["L"] for h in h99_f3] + [m["L"] for m in scored])
pp_stats("açık 71 (PB için)", [m["L"] for m in members])
pp_stats("havuz PB (99 + 71)", [h["L"] for h in h99] + [m["L"] for m in members])
w()

# ---------------------------------------------------------------- §6 donmuş v0 girdi duyarlılığı
w("## 6. Donmuş v0'ın girdi kırpma duyarlılığı (KEŞİF; parametre değişmedi, fit yok)")
w()
w("z_f1 ve z_f2, H99 eğitim [p05, p95] sınırlarına kırpılıp donmuş γ, β ile S yeniden kurulur. Bu, (a) adayının")
w("prospektif skoru DEĞİLDİR (a yeniden fit eder, kırpma eğitimde de uygulanır); yalnız ekstrapolasyon payının büyüklüğünü gösterir.")
w()
zf1_lo = (f1p05 - prep["mean"]["f1"]) / prep["std"]["f1"]
zf1_hi = (q([h["f1"] for h in h99_f3], 0.95) - prep["mean"]["f1"]) / prep["std"]["f1"]
zf2_lo = (f2p05 - prep["mean"]["f2"]) / prep["std"]["f2"]
zf2_hi = (f2p95 - prep["mean"]["f2"]) / prep["std"]["f2"]
w(f"Kırpma sınırları (z): f1 [{zf1_lo:+.2f}, {zf1_hi:+.2f}], f2 [{zf2_lo:+.2f}, {zf2_hi:+.2f}]")
w()


def S_with(m, clip_f1=False, clip_f2=False, drop_f1=False):
    z = dict(m["z"])
    if clip_f1:
        z["f1"] = min(max(z["f1"], zf1_lo), zf1_hi)
    if clip_f2:
        z["f2"] = min(max(z["f2"], zf2_lo), zf2_hi)
    if drop_f1:
        z["f1"] = 0.0
    lin = sum(beta[c] * z[c] for c in z)
    return sv.survival([sv.sigmoid(gamma[sv.GROUP_OF_DAY[d]] + lin) for d in range(1, 11)])


w("| küme | n | RPS v0 | v0 f1 kırpılı | v0 f1+f2 kırpılı | v0 f1 = eğitim ort. (z=0) | RPS KM | ort S_5 v0 / f1 kırpılı / göz | ort S_10 v0 / f1 kırpılı / göz |")
w("|---|---|---|---|---|---|---|---|---|")
for label, ms in [("açık (68)", scored)] + [(y, [m for m in scored if m["year"] == y]) for y in ("2021", "2022", "2023")] + \
        [(rg, [m for m in scored if m["regime"] == rg]) for rg in ("PRE_20211111", "THRESH100_20211111", "EQUAL_DIST_20230330")]:
    if not ms:
        continue
    r0 = mean(rps(m["S"], m["L"]) for m in ms)
    r1 = mean(rps(S_with(m, clip_f1=True), m["L"]) for m in ms)
    r12 = mean(rps(S_with(m, clip_f1=True, clip_f2=True), m["L"]) for m in ms)
    rd = mean(rps(S_with(m, drop_f1=True), m["L"]) for m in ms)
    rk = mean(rps(m["kmS"], m["L"]) for m in ms)
    s5 = f"{mean(m['S'][4] for m in ms):.2f} / {mean(S_with(m, clip_f1=True)[4] for m in ms):.2f} / {obs(ms,5):.2f}"
    s10 = f"{mean(m['S'][9] for m in ms):.2f} / {mean(S_with(m, clip_f1=True)[9] for m in ms):.2f} / {obs(ms,10):.2f}"
    w(f"| {label} | {len(ms)} | {r0:.3f} | {r1:.3f} | {r12:.3f} | {rd:.3f} | {rk:.3f} | {s5} | {s10} |")
w()

# ---------------------------------------------------------------- §7 H99 backtest: v0 − KM yıl kırılımı (yakın dönem testi tabanı)
w("## 7. H99 backtest (yayımlı ledger'lar): v0 − KM RPS, ilk işlem yılına göre; yakın dönem fold sayıları")
w()
led_dir = ROOT / "tests/reference/macos_golden_faz1b"
v0led = {r["ticker"]: r for r in csv.DictReader(open(led_dir / f"{V0}_fold_ledger.csv")) if r["status"] == "FIT_OK"}
kmled = {r["ticker"]: r for r in csv.DictReader(open(led_dir / f"{KM}_fold_ledger.csv"))}
infled = {r["ticker"]: r for r in csv.DictReader(open(led_dir / f"{V0}@INF_fold_ledger.csv"))}
w("| yıl | fold | v0 RPS | KM RPS | fark | @INF RPS | v0 − @INF | fark sd (fold) |")
w("|---|---|---|---|---|---|---|---|")
by_year = defaultdict(list)
for t, r in v0led.items():
    k = kmled[t]
    i = infled[t]
    L = int(r["realized_L"])
    S0 = [float(r[f"S_{j}"]) for j in range(1, 11)]
    Sk = [float(k[f"S_{j}"]) for j in range(1, 11)]
    Si = [float(i[f"S_{j}"]) for j in range(1, 11)]
    by_year[r["first_trading_date"][:4]].append((rps(S0, L), rps(Sk, L), rps(Si, L)))
tot = []
for y in sorted(by_year):
    v = by_year[y]
    tot += v
    d = [a - b for a, b, _ in v]
    w(f"| {y} | {len(v)} | {mean(a for a,_,_ in v):.3f} | {mean(b for _,b,_ in v):.3f} | {mean(d):+.3f} | "
      f"{mean(c for _,_,c in v):.3f} | {mean(a-c for a,_,c in v):+.3f} | {st.pstdev(d) if len(d)>1 else 0:.3f} |")
d = [a - b for a, b, _ in tot]
w(f"| hepsi | {len(tot)} | {mean(a for a,_,_ in tot):.3f} | {mean(b for _,b,_ in tot):.3f} | {mean(d):+.3f} | "
  f"{mean(c for _,_,c in tot):.3f} | {mean(a-c for a,_,c in tot):+.3f} | {st.pstdev(d):.3f} |")
near = [t for t, r in v0led.items() if r["first_trading_date"] >= "2024-01-01"]
w()
w(f"Yakın dönem (ilk işlem ≥ 2024-01-01) skorlanabilir fold: {len(near)}; 2023 fold: {len(v0led)-len(near)}; toplam {len(v0led)}.")
months = Counter(v0led[t]["first_trading_date"][:7] for t in near)
w(f"Yakın dönem ay-blok sayısı: {len(months)}; olay (L<10) sayısı: {sum(int(v0led[t]['realized_L']) < 10 for t in near)}")
w()

# ---------------------------------------------------------------- §8 nominal büyüklük zaman serisi (deflatör ihtiyacı)
w("## 8. Nominal arz büyüklüğü (medyan, mn TL) yıl-yarıyıla göre: gerekli deflatörün mertebesi (keşif)")
w()
w("| dönem | küme | n | medyan mn TL | p25 | p75 |")
w("|---|---|---|---|---|---|")
allm = [("açık", m["ftd"], math.exp(m["raw"]["f1"]) / 1e6) for m in scored] + [("H99", h["ftd"], h["size_tl"] / 1e6) for h in h99_f3]
halves = defaultdict(list)
for src, ftd, sz in allm:
    halves[(ftd[:4] + ("H1" if ftd[5:7] <= "06" else "H2"), src)].append(sz)
for key in sorted(halves):
    vs = sorted(halves[key])
    w(f"| {key[0]} | {key[1]} | {len(vs)} | {q(vs,0.5):,.0f} | {q(vs,0.25):,.0f} | {q(vs,0.75):,.0f} |")
w()
w("Medyan oranı H99 (97) / açık 2021: "
  f"{q([h['size_tl'] for h in h99_f3],0.5) / q([math.exp(m['raw']['f1']) for m in scored if m['year']=='2021'],0.5):.1f}×; "
  f"H99 / açık 2022: {q([h['size_tl'] for h in h99_f3],0.5) / q([math.exp(m['raw']['f1']) for m in scored if m['year']=='2022'],0.5):.1f}×; "
  f"H99 / açık 2023: {q([h['size_tl'] for h in h99_f3],0.5) / q([math.exp(m['raw']['f1']) for m in scored if m['year']=='2023'],0.5):.1f}×")
w()

# ---------------------------------------------------------------- §9 D1 etiketi NA, sansür, vs.
w("## 9. Sonuç etiketi bütünlüğü (açık küme)")
na = sum(any(c is None for c in m["closes"]) for m in members)
w(f"Tavan etiketi NA içeren üye: {na}/71. L dağılımı (71): {dict(sorted(Counter(m['L'] for m in members).items()))}")
w(f"L dağılımı H99 (99): {dict(sorted(Counter(h['L'] for h in h99).items()))}")
w()

(ROOT / "docs/specs_faz7/ekler/tani_v1_cikti.txt").write_text("\n".join(out_lines) + "\n", encoding="utf-8")
print("\n".join(out_lines))

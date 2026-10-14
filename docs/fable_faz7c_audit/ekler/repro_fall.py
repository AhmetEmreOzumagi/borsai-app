#!/usr/bin/env python3
"""BORSAI_FAZ7C_FABLE_REPRO_AUDIT_20260927 — `fall_d10_v0_{h99,pooled,addsale,pooled@ZERO}` ailesinin SIFIRDAN, bağımsız
yeniden üretimi (Fable). `borsai` paketi İMPORT EDİLMEZ (dosyada import satırı yok; sonda ve alt süreçte sys.modules denetimi);
stdlib + numpy + scikit-learn (çözücü şartnamede sklearn L2 LogisticRegression olarak tanımlıdır; SPEC_C_V0 §4, SPEC_V1_6 §2).

Kodlandığı şartnameler: SPEC_C_V0 §1.3, §2, §3, §4, §5.1, §5.4, §6.2, §11, §13; KARARLAR_C C1–C4; SPEC_V1_6 §2–§4, §9;
SPEC_HAZARD_V1 §3.2 (f1r, TÜFE m−2); SPEC_SCORING §3, §7, §8; SPEC_DEVIATIONS C7 (ay-blok bootstrap, random.Random), J10 (f3 filtre
dışlaması; proje sahibi kararı), K6 (D5 fold'unda D5 seansı < T; proje sahibi kararı). Faz 7 denetim betiğimin parçaları (Type-7 kantil,
blok bootstrap, TÜFE okuyucu) yeniden kullanıldı.

Girdiler (yalnız okunur): data/training_table.csv, MASTER (ipo_size_tl), SESSIONS (yalnız tarih ve kapanış sütunları),
data/raw/tuik/tufe_genel_2025_100.csv, data/training_table_v2.csv, data/outcomes_oot/<açık üye>.csv (yalnız v2'de OOT_OPEN olan
kodlar; kasa üyesi dosya yok), Faz 1A altın ledger'ları (karşılaştırıcı), Faz 7C altın dizini (yalnız karşılaştırma), docs/MODELS.md
ve experiments/log.jsonl (yalnız karşılaştırma). data/outcomes/, scores/, registry/ OKUNMAZ. Hiçbir çıktıya kasa kodu yazılmaz.

Çıktı: stdout raporu (ekler/repro_stdout.txt), repro_output.json, repro_ledgers/*.csv (kompakt), sensitivity_runs.jsonl.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import csv
import hashlib
import json
import math
import multiprocessing
import random
import re
import sys
import time
import warnings
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

assert not any(m == "borsai" or m.startswith("borsai.") for m in sys.modules), "borsai import edilmiş!"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
assert (ROOT / "CLAUDE.md").exists(), ROOT
OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
(OUT_DIR / "repro_ledgers").mkdir(parents=True, exist_ok=True)
RAW = ROOT / "data" / "raw"
GOLD = ROOT / "tests" / "reference" / "macos_golden_faz7c"
GOLD1A = ROOT / "tests" / "reference" / "macos_golden"
CTX28 = Context(prec=28, rounding=ROUND_HALF_EVEN)
CTX60 = Context(prec=60, rounding=ROUND_HALF_EVEN)
TOL = 1e-9
NEAR_START = "2024-01-01"
DELTA = 0.008
ZERO = 0.0
GRID = (ZERO, 0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0)
FALLBACK_C = 0.01
MIN_TRAIN = 10
HORIZONS = ("D5", "D10")
EXPLICIT = {"FILTERED", "UNFILTERED"}
H99M, POOL, ADDS, ZROW = "fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO"
MODELS = (H99M, POOL, ADDS, ZROW)
FEATS = {H99M: ("f1r", "f3", "add_sale"), POOL: ("f1r", "f3", "add_sale"), ADDS: ("add_sale",), ZROW: ()}
LOGCOL = {"f1r", "f3"}
WINSCOL = {"f1r", "f3"}
SETS = {H99M: "H99_F3_AS_PRESENT", POOL: "H99_PLUS_OOT_OPEN_F3_AS_PRESENT", ADDS: "H99_PLUS_OOT_OPEN_AS_PRESENT",
        ZROW: "H99_PLUS_OOT_OPEN_F3_AS_PRESENT"}
LOGIT_KW = dict(l1_ratio=0.0, solver="lbfgs", fit_intercept=True, class_weight=None, max_iter=10000, tol=1e-10)
CMP_PINS = {"base_rate": "898d2d849cc21a0461c88b816338c9d64d7b93b7d4ffafe726bfd3c56d5147e2",
            "v1_5_h99": "5c56da37bf7cece261fc5472ff0a2de8e242169755afc3aefb3c6c12b7fb049b"}
OUT: dict = {}
LOG: list[str] = []
T0 = time.time()


def say(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


def rd(path, enc="utf-8-sig"):
    with open(path, encoding=enc, newline="") as fh:
        return list(csv.DictReader(fh))


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ihash(items):
    return hashlib.sha256(("\n".join(items) + "\n").encode("utf-8")).hexdigest()


def q7(vals, p: Fraction):
    """R Type-7 kantil, kesin Fraction (SPEC_C_V0 §3.2: Type-7)."""
    vals = sorted(vals)
    n = len(vals)
    if n == 1:
        return vals[0]
    h = Fraction(n - 1) * p + 1
    lo = h.numerator // h.denominator
    fr = h - lo
    if lo == n:
        return vals[-1]
    return vals[lo - 1] + fr * (vals[lo] - vals[lo - 1])


def month_for(T: str) -> str:
    y, m = int(T[:4]), int(T[5:7]) - 2
    if m <= 0:
        y, m = y - 1, m + 12
    return f"{y:04d}-{m:02d}"


def month_add(m: str, k: int) -> str:
    y, mo = int(m[:4]), int(m[5:7]) - 1 + k
    return f"{y + mo // 12:04d}-{mo % 12 + 1:02d}"


def cell(v):
    return None if v in ("", "DATA_NOT_FOUND", None) else v


def hp_label(C):
    return "ZERO" if C == ZERO else C


# ============================================================ 0. TÜFE (SPEC_HAZARD_V1 §3.2; SPEC_C_V0 §3.2 "aynen")
TUFE = {}
_prev = None
for _r in rd(RAW / "tuik" / "tufe_genel_2025_100.csv", enc="utf-8"):
    assert _prev is None or _r["month"] == month_add(_prev, 1), ("TÜFE ay sürekliliği", _prev, _r["month"])
    _prev = _r["month"]
    TUFE[_r["month"]] = _r
say(f"[tufe] {len(TUFE)} ay ({list(TUFE)[0]} … {list(TUFE)[-1]}), dosya sha {sha_file(RAW / 'tuik' / 'tufe_genel_2025_100.csv')[:12]}…")

# ============================================================ 1. veri
T99 = rd(ROOT / "data" / "training_table.csv")
V2 = rd(ROOT / "data" / "training_table_v2.csv", enc="utf-8")
MASTER = {r["ticker"]: r for r in rd(RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv")}
SESS = {}
for s in rd(RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv"):
    SESS.setdefault(s["ticker"], {})[int(s["session_number"])] = (s["target_session_date"], s["thb_raw_close"])
assert len(T99) == 99 and len(V2) == 170
V2_BY = {r["ticker"]: r for r in V2}
OPEN_TICKERS = [r["ticker"] for r in V2 if r["cohort"] == "OOT_OPEN"]
assert len(OPEN_TICKERS) == 71 and [r["ticker"] for r in T99] == [r["ticker"] for r in V2 if r["cohort"] == "H99"]
say(f"[veri] H99 99 (training_table.csv sha {sha_file(ROOT / 'data' / 'training_table.csv')[:12]}…), v2 170 "
    f"(sha {sha_file(ROOT / 'data' / 'training_table_v2.csv')[:12]}…), açık 71; v2 H99 sırası training_table.csv ile aynı")


def size_tl(price, shares, ipo_size):
    if cell(ipo_size) is not None:
        return Decimal(ipo_size)
    with localcontext(CTX28):
        return Decimal(shares) * Decimal(price)


def real_size(f1: Decimal, idx: str) -> Decimal:
    with localcontext(CTX60):
        return f1 / (Decimal(idx) / Decimal(100))


def add_sale_flag(raw):
    """SPEC_C_V0 §3.1: 1[Decimal(alan) > 0]; boş → küme dışı (RET); negatif → hata."""
    if cell(raw) is None:
        return None
    d = Decimal(raw)
    assert d >= 0, raw
    return 1 if d > 0 else 0


UNITS: dict[str, dict] = {}
for r in T99:
    t = r["ticker"]
    v2 = V2_BY[t]
    for c in T99[0].keys():
        assert r[c] == v2[c], (t, c)
    u = {"ticker": t, "ftd": r["first_trading_date"], "cohort": "H99", "price": r["ipo_price_tl"], "shares": r["shares_offered"],
         "post": r["post_ipo_share_capital"], "capinc": r["capital_increase_shares"],
         "f3": None if r["total_demand_multiple"] == "" else Decimal(r["total_demand_multiple"]),
         "status": cell(r["total_demand_filter_status"]), "add_raw": cell(r["additional_sale_shares"]),
         "ipo_size": cell(MASTER[t]["ipo_size_tl"]), "Y": {h: int(r[f"Y_{h}"]) for h in HORIZONS},
         "R": {h: r[f"R_{h}"] for h in HORIZONS}, "sess": {"D5": SESS[t][5][0], "D10": SESS[t][10][0]},
         "close": {"D5": SESS[t][5][1], "D10": SESS[t][10][1]}}
    assert (cell(v2["ipo_size_tl"]) or None) == u["ipo_size"], t
    UNITS[t] = u
for t in OPEN_TICKERS:
    r = V2_BY[t]
    oc = rd(ROOT / "data" / "outcomes_oot" / f"{t}.csv", enc="utf-8")
    by = {int(x["h"]): x for x in oc}
    assert sorted(by) == list(range(1, 11)) and all(x["status"] == "OK" for x in oc), t
    for h, k in (("D5", 5), ("D10", 10)):
        assert by[k]["Y_h"] == r[f"Y_{h}"] and by[k]["R_h"] == r[f"R_{h}"] and Decimal(by[k]["ipo_price"]) == Decimal(r["ipo_price_tl"]), (t, h)
    UNITS[t] = {"ticker": t, "ftd": r["first_trading_date"], "cohort": "OOT_OPEN", "price": r["ipo_price_tl"],
                "shares": r["shares_offered"], "post": r["post_ipo_share_capital"], "capinc": r["capital_increase_shares"],
                "f3": None if r["total_demand_multiple"] == "" else Decimal(r["total_demand_multiple"]),
                "status": cell(r["total_demand_filter_status"]), "add_raw": cell(r["additional_sale_shares"]),
                "ipo_size": cell(r["ipo_size_tl"]), "Y": {h: int(r[f"Y_{h}"]) for h in HORIZONS},
                "R": {h: r[f"R_{h}"] for h in HORIZONS}, "sess": {"D5": by[5]["session_date"], "D10": by[10]["session_date"]},
                "close": {"D5": by[5]["close_raw"], "D10": by[10]["close_raw"]}}
for u in UNITS.values():
    u["f1"] = size_tl(u["price"], u["shares"], u["ipo_size"])
    m = month_for(u["ftd"])
    u["tufe_month"], u["tufe_index"], u["tufe_release"] = m, TUFE[m]["index"], TUFE[m]["release_date"]
    assert u["tufe_release"] < u["ftd"], (u["ticker"], "TÜFE PIT")
    if u["cohort"] == "OOT_OPEN":
        assert (V2_BY[u["ticker"]]["tufe_month"], V2_BY[u["ticker"]]["tufe_index"]) == (m, u["tufe_index"])
    u["f1r"] = real_size(u["f1"], u["tufe_index"])
    u["add_sale"] = add_sale_flag(u["add_raw"])
ORDER_H99 = [r["ticker"] for r in T99]
ORDER_V2 = [r["ticker"] for r in V2]
assert ORDER_V2 == sorted(ORDER_V2, key=lambda t: (UNITS[t]["ftd"], t))


def set_rows(model):
    """SPEC_C_V0 §1.3 eğitim kümeleri, tablo sırasıyla."""
    base = ORDER_H99 if model == H99M else ORDER_V2
    need_f3 = model != ADDS
    return [t for t in base if UNITS[t]["add_sale"] is not None and (not need_f3 or UNITS[t]["f3"] is not None)]


say("\n=== 1a. Eğitim kümeleri ve özellikler (§1.3, §3, §11-1..3) ===")
for model in (H99M, POOL, ADDS):
    rows = set_rows(model)
    ev = {h: sum(1 for t in rows if UNITS[t]["Y"][h] == 0) for h in HORIZONS}
    coh = Counter(UNITS[t]["cohort"] for t in rows)
    flags = sum(UNITS[t]["add_sale"] for t in rows)
    say(f"[1a] {SETS[model]}: n={len(rows)} (H99 {coh['H99']}, açık {coh.get('OOT_OPEN', 0)}), olay D10 {ev['D10']}, D5 {ev['D5']}, "
        f"ek satış bayrağı=1: {flags}")
    OUT.setdefault("sets", {})[model] = {"n": len(rows), "events": ev, "cohorts": dict(coh), "flags": flags}
exp = {H99M: (94, 26, 18), POOL: (161, 39, 29), ADDS: (165, 40, 30)}
OUT["sets_ok"] = all((OUT["sets"][m]["n"], OUT["sets"][m]["events"]["D10"], OUT["sets"][m]["events"]["D5"]) == exp[m] for m in exp)
say(f"[1a] beklenen 94/26/18, 161/39/29, 165/40/30: {OUT['sets_ok']}")
fl_h99 = sum(1 for t in ORDER_H99 if UNITS[t]["add_sale"] == 1)
fl_open = sum(1 for t in OPEN_TICKERS if UNITS[t]["add_sale"] == 1)
say(f"[1a] bayrak = 1: H99 {fl_h99} (beklenen 6), açık {fl_open} (beklenen 13); alan boş: H99 {sum(1 for t in ORDER_H99 if UNITS[t]['add_sale'] is None)}, "
    f"açık {sum(1 for t in OPEN_TICKERS if UNITS[t]['add_sale'] is None)}")
OUT["flags"] = {"h99": fl_h99, "open": fl_open}
# f1r bit-eşitliği (§11-3): Faz 7 altın önizlemeleri `ceiling_hazard_v1_real` (H99'un f3'lü 97 arzı) ve `_pooled` (havuzun f3'lü 165
# arzı) f1r ham değerlerinin Type-7 [p05, p95] sınırlarını ve min/max'ını float olarak taşır; aynı satırlardan kendi f1r'imle yeniden
# hesaplanınca float-eşit olmalı (bit-eşitlik; Faz 7 denetimimde 97/97 satır zaten bit-eşitti).
f1r_chk = {}
for name, rows in (("ceiling_hazard_v1_real", [t for t in ORDER_H99 if UNITS[t]["f3"] is not None]),
                   ("ceiling_hazard_v1_pooled", [t for t in ORDER_V2 if UNITS[t]["f3"] is not None])):
    pv = json.loads((ROOT / "tests" / "reference" / "macos_golden_faz7" / f"{name}_final_fit_preview.json").read_text(encoding="utf-8"))
    vals = [Fraction(UNITS[t]["f1r"]) for t in rows]
    mine = {"p05": float(q7(vals, Fraction(1, 20))), "p95": float(q7(vals, Fraction(19, 20))), "min": float(min(vals)), "max": float(max(vals)), "n": len(vals)}
    gold = {"p05": pv["preprocessing"]["winsor"]["f1r"]["p05"], "p95": pv["preprocessing"]["winsor"]["f1r"]["p95"],
            "min": pv["feature_ranges"]["f1r"]["min"], "max": pv["feature_ranges"]["f1r"]["max"], "n": pv["feature_ranges"]["f1r"]["n"]}
    f1r_chk[name] = {"mine": mine, "gold": gold, "equal": mine == gold}
    say(f"[1a] f1r ham değerleri {name} önizlemesiyle (n={gold['n']}): Type-7 p05/p95 ve min/max float-eşit: {mine == gold}")
OUT["f1r_bit_equal"] = f1r_chk

# ============================================================ 2. ön işleme (§3.2; SPEC_V1_6 §2 kalıbı) ve fit (§4)
_LN_CACHE: dict[Fraction, Decimal] = {}


def ln_dec(v: Fraction) -> Decimal:
    d = _LN_CACHE.get(v)
    if d is None:
        with localcontext(CTX60):
            d = (Decimal(v.numerator) / Decimal(v.denominator)).ln()
        _LN_CACHE[v] = d
    return d


def raw_of(t, feats):
    u = UNITS[t]
    out = {}
    for c in feats:
        if c == "f1r":
            out[c] = Fraction(u["f1r"])
        elif c == "f3":
            out[c] = Fraction(u["f3"])
        else:
            out[c] = Fraction(u["add_sale"])
    return out


def filter_mode(statuses):
    usable = [s for s in statuses if s is not None]
    if not usable:
        return None, False
    cnt = Counter(usable)
    best = max(cnt.values())
    tied = sorted(s for s, c in cnt.items() if c == best)
    return tied[0], len(tied) > 1


def opposite(a, b):
    return a in EXPLICIT and b in EXPLICIT and a != b


def f3_excluded(tickers):
    """J10: kümenin f3'lü arzlarının filtre modu açık ve arzın durumu ona açıkça zıtsa arz o kümede kullanılmaz."""
    present = [t for t in tickers if UNITS[t]["f3"] is not None]
    mode, _ = filter_mode([UNITS[t]["status"] for t in present])
    return tuple(t for t in present if opposite(UNITS[t]["status"], mode))


class Prep:
    """Arz düzeyi ön işleme: winsor (Type-7 [p05, p95], ham) -> ln (f1r, f3) -> z (ddof = 0); add_sale yalnız z. Yalnız eğitimden."""

    def __init__(self, tickers, feats, check_filter=True):
        self.feats = tuple(feats)
        self.n = len(tickers)
        raw = {t: raw_of(t, feats) for t in tickers}
        uses_f3 = "f3" in feats
        self.mode, self.mode_tie = filter_mode([UNITS[t]["status"] for t in tickers if uses_f3 and UNITS[t]["f3"] is not None])
        if uses_f3 and check_filter:
            assert not any(opposite(UNITS[t]["status"], self.mode) for t in tickers), "f3 filtre adımı dışlamadan sonra arz boşaltırdı"
        self.lo, self.hi = {}, {}
        for c in feats:
            if c in WINSCOL:
                vals = [raw[t][c] for t in tickers]
                self.lo[c], self.hi[c] = q7(vals, Fraction(1, 20)), q7(vals, Fraction(19, 20))
        exact = {t: {c: (min(max(raw[t][c], self.lo[c]), self.hi[c]) if c in self.lo else raw[t][c]) for c in feats} for t in tickers}
        self.cols, self.mean, self.std, self.dropped = [], {}, {}, []
        for c in feats:
            if len({exact[t][c] for t in tickers}) <= 1:
                self.dropped.append(c)
                continue
            self.cols.append(c)
            with localcontext(CTX60):
                if c in LOGCOL:
                    vals = [ln_dec(exact[t][c]) for t in tickers]
                    mean = sum(vals, Decimal(0)) / Decimal(self.n)
                    var = sum(((v - mean) ** 2 for v in vals), Decimal(0)) / Decimal(self.n)
                    self.mean[c], self.std[c] = mean, var.sqrt()
                else:
                    vf = [exact[t][c] for t in tickers]
                    mf = sum(vf, Fraction(0)) / self.n
                    varf = sum(((v - mf) ** 2 for v in vf), Fraction(0)) / self.n
                    self.mean[c] = mf
                    self.std[c] = (Decimal(varf.numerator) / Decimal(varf.denominator)).sqrt()
        self.cols = tuple(self.cols)
        self.insufficient = not self.cols
        self.Z = {t: self._z(exact[t]) for t in tickers} if not self.insufficient else {}

    def _z(self, ex):
        out = []
        with localcontext(CTX60):
            for c in self.cols:
                if c in LOGCOL:
                    out.append(float((ln_dec(ex[c]) - self.mean[c]) / self.std[c]))
                else:
                    d = ex[c] - self.mean[c]
                    out.append(float((Decimal(d.numerator) / Decimal(d.denominator)) / self.std[c]))
        return out

    def transform(self, t):
        r = raw_of(t, self.feats)
        ex, clipped = {}, []
        for c in self.feats:
            v = r[c]
            if c in self.lo:
                cl = min(max(v, self.lo[c]), self.hi[c])
                if cl != v:
                    clipped.append(c)
                v = cl
            ex[c] = v
        return self._z(ex), clipped

    def params(self):
        return {"columns": list(self.cols), "winsor": {c: {"p05": float(self.lo[c]), "p95": float(self.hi[c])} for c in self.lo},
                "mean": {c: float(self.mean[c]) for c in self.cols}, "std": {c: float(self.std[c]) for c in self.cols},
                "f3_filter_mode": self.mode, "f3_filter_mode_tie": self.mode_tie, "dropped": list(self.dropped), "n_train": self.n}


def sk_fit(C, X, y):
    est = LogisticRegression(C=C, **LOGIT_KW)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        est.fit(X, y)
    conv = [w for w in caught if issubclass(w.category, ConvergenceWarning)]
    other = [str(w.message) for w in caught if not issubclass(w.category, ConvergenceWarning)]
    return est, bool(conv), other


def p1(est, z):
    proba = est.predict_proba(np.array(z, dtype=np.float64).reshape(1, -1))[0]
    return float(proba[list(est.classes_).index(1)])


def newton_logit(X, y, C, iters=200):
    """Bağımsız çözüm: min 0.5‖β‖² + C Σ log(1 + exp(−s_i (b + βᵀx_i))), sabit cezasız (sklearn amacı; SPEC_V1_6 §2)."""
    n, p = X.shape
    A = np.hstack([np.ones((n, 1)), X])
    w = np.zeros(p + 1)
    pen = np.concatenate([[0.0], np.ones(p)])
    for _ in range(iters):
        eta = A @ w
        mu = 1.0 / (1.0 + np.exp(-eta))
        g = C * A.T @ (mu - y) + pen * w
        H = C * (A.T * (mu * (1 - mu))) @ A + np.diag(pen)
        step = np.linalg.solve(H, g)
        w -= step
        if np.max(np.abs(step)) < 1e-14:
            break
    return w[0], w[1:]


def fit_logit(order, feats, h, test=None, uses_f3=None, rate_only=False, j10=True):
    """Bir ufuk fold'u (SPEC_C_V0 §4; SPEC_V1_6 §4; J10 iç CV dahil). `order` = plan dışlamasından sonraki eğitim sırası."""
    uses_f3 = ("f3" in feats) if uses_f3 is None else uses_f3
    Y = {t: UNITS[t]["Y"][h] for t in order}
    n = len(order)
    y_seq = [Y[t] for t in order]
    n1 = sum(y_seq)
    n0 = n - n1
    res = {"n_class_0": n0, "n_class_1": n1, "inner_fold_n": 0, "score_table": [], "columns": [], "C": None, "tuning": "TUNING_NOT_APPLICABLE",
           "p": None, "pred": None, "intercept": None, "coef": None, "attempts": [], "clipped": None, "warnings": [],
           "inner_filter_excluded_n": 0, "inner_held_out_not_scored_n": 0, "f3_filter_mode_ties_n": 0, "prep": None}
    if n < MIN_TRAIN:
        return {**res, "status": "INSUFFICIENT_TRAINING_HISTORY"}
    if rate_only:
        if n0 == 0 or n1 == 0:
            return {**res, "status": "MODEL_NOT_FIT_SINGLE_CLASS"}
        p = n1 / n
        return {**res, "status": "FIT_OK", "C": ZERO, "p": p if test is not None else None, "pred": (1 if p > 0.5 else 0) if test is not None else None,
                "intercept": math.log(p / (1 - p)), "coef": {}, "constant": p}
    # nihai ön işleme (yalnız eğitim satırlarından); kodun kalıbında tek sınıf fold'unda da kurulur (test kırpma bayrağı yazılır)
    final = Prep(order, feats, check_filter=j10)
    res["f3_filter_mode_ties_n"] += int(final.mode_tie) * 2
    res["prep"] = final
    tz = None
    if test is not None and not final.insufficient:
        assert not (uses_f3 and j10 and opposite(UNITS[test]["status"], final.mode)), "test arzı filtre çatışması (oluşmamalı)"
        tz, clipped = final.transform(test)
        res["clipped"] = clipped
    if n0 == 0 or n1 == 0:
        return {**res, "status": "MODEL_NOT_FIT_SINGLE_CLASS"}
    if min(n0, n1) < 2:
        selected, tuning = FALLBACK_C, "TUNING_SKIPPED_MINORITY_COUNT_LT_2"
        ranked = [selected, ZERO]
        inner_n, table = 0, []
    else:
        folds = []
        for held in order:
            inner = [t for t in order if t != held]
            if uses_f3 and j10:
                ex = set(f3_excluded(inner))
                if ex:
                    inner = [t for t in inner if t not in ex]
                    res["inner_filter_excluded_n"] += len(ex)
            pr = Prep(inner, feats, check_filter=j10)
            if not pr.insufficient and uses_f3 and j10 and opposite(UNITS[held]["status"], pr.mode):
                res["inner_held_out_not_scored_n"] += 1
                continue
            res["f3_filter_mode_ties_n"] += int(pr.mode_tie) * 2
            folds.append((held, inner, pr, None if pr.insufficient else pr.transform(held)[0]))
        for held, inner, pr, val in folds:
            if pr.insufficient:
                return {**res, "status": "INNER_INSUFFICIENT_FEATURE_VARIATION", "inner_fold_n": n}
            if len({Y[t] for t in inner}) < 2:
                return {**res, "status": "INNER_SINGLE_CLASS", "inner_fold_n": n}
        table = []
        for C in GRID:
            terms, dropped = [], False
            for held, inner, pr, val in folds:
                if C == ZERO:
                    pp_ = sum(Y[t] for t in inner) / len(inner)
                else:
                    est, nc, _ = sk_fit(C, np.array([pr.Z[t] for t in inner]), np.array([Y[t] for t in inner], dtype=np.float64))
                    if nc:
                        dropped = True
                        break
                    pp_ = p1(est, val)
                terms.append((pp_ - Y[held]) ** 2)
            table.append({"hyperparameter": hp_label(C), "score": None if dropped else sum(terms) / len(terms), "fold_count": len(folds),
                          "status": "CANDIDATE_NOT_CONVERGED" if dropped else "SCORED"})
        scored = [(e["score"], 0.0 if e["hyperparameter"] == "ZERO" else e["hyperparameter"]) for e in table if e["status"] == "SCORED"]
        ranked = [c for _, c in sorted(scored)]
        selected, tuning, inner_n = ranked[0], "TUNED_INNER_LOOCV", len(folds)
    res.update(tuning=tuning, inner_fold_n=inner_n, score_table=table)
    if final.insufficient:
        return {**res, "status": "INSUFFICIENT_FEATURE_VARIATION", "C": selected}
    res["columns"] = list(final.cols)
    X = np.array([final.Z[t] for t in order])
    y = np.array(y_seq, dtype=np.float64)
    for C in ranked:
        if C == ZERO:
            p = n1 / n
            res["attempts"].append(["ZERO", "FIT_OK"])
            return {**res, "status": "FIT_OK", "C": ZERO, "p": p if test is not None else None, "pred": (1 if p > 0.5 else 0) if test is not None else None,
                    "intercept": math.log(p / (1 - p)), "coef": {c: 0.0 for c in final.cols}, "constant": p, "est": None, "X": X, "y": y}
        est, nc, other = sk_fit(C, X, y)
        if nc:
            res["attempts"].append([C, "NOT_CONVERGED"])
            continue
        res["attempts"].append([C, "FIT_OK"])
        p = p1(est, tz) if tz is not None else None
        return {**res, "status": "FIT_OK", "C": C, "p": p, "pred": None if p is None else (1 if p > 0.5 else 0),
                "intercept": float(est.intercept_[0]), "coef": {c: float(v) for c, v in zip(final.cols, est.coef_[0])}, "warnings": other,
                "est": est, "X": X, "y": y}
    return {**res, "status": "MODEL_NOT_FIT_OPTIMIZER_DID_NOT_CONVERGE", "C": selected}


# ============================================================ 3. fold planları (§5.1; K6; J10)
def plan(model, j10=True, d5_rule="D5"):
    rows = set_rows(model)
    feats = FEATS[POOL] if model == ZROW else FEATS[model]
    uses_f3 = "f3" in feats
    tests = [t for t in rows if UNITS[t]["cohort"] == "H99"]
    folds = []
    for h in HORIZONS:
        key = h if (h == "D10" or d5_rule == "D5") else "D10"       # K6-A: D5 fold'unda D5 seansı < T; duyarlılık: D10 < T
        for test in tests:
            pdate = UNITS[test]["ftd"]
            training = [t for t in rows if UNITS[t]["sess"][key] < pdate]
            assert test not in training and all(UNITS[t]["ftd"] < pdate for t in training)
            excl = f3_excluded(training) if (uses_f3 and j10) else ()
            training = [t for t in training if t not in set(excl)]
            folds.append({"model": model, "h": h, "test": test, "T": pdate, "training": training, "excluded": excl,
                          "n_oot_open": sum(1 for t in training if UNITS[t]["cohort"] != "H99"),
                          "n_chrono": sum(1 for t in rows if UNITS[t]["ftd"] < pdate), "scorable": len(training) >= MIN_TRAIN})
    return folds


def run_fold(f, j10=True):
    model = f["model"]
    if not f["scorable"]:
        return None
    if model == ZROW:
        r = fit_logit(f["training"], (), f["h"], test=f["test"], uses_f3=False, rate_only=True)
    else:
        r = fit_logit(f["training"], FEATS[model], f["h"], test=f["test"], j10=j10)
    r.pop("est", None)
    r.pop("X", None)
    r.pop("y", None)
    r.pop("prep", None)
    return r


def _task(args):
    f, j10 = args
    return run_fold(f, j10)


def row_of(f, r):
    u = UNITS[f["test"]]
    h = f["h"]
    coef = None if r["coef"] is None else json.dumps(r["coef"], sort_keys=True, separators=(",", ":"))
    from datetime import date, timedelta
    return {"model_id": f["model"], "fold_id": f"{h}|{f['test']}", "horizon": h, "ticker": f["test"], "prediction_date": f["T"],
            "prediction_cutoff_date": (date.fromisoformat(f["T"]) - timedelta(days=1)).isoformat(), "target_session_date": u["sess"][h],
            "training_n": len(f["training"]), "n_chronological_train": f["n_chrono"], "training_tickers_sha256": ihash(f["training"]),
            "training_targets_sha256": ihash([f"{t}|{UNITS[t]['sess'][h]}|{UNITS[t]['R'][h]}|{UNITS[t]['Y'][h]}" for t in f["training"]]),
            "ipo_price": u["price"], "realized_return": u["R"][h], "realized_direction": u["Y"][h], "official_close": u["close"][h],
            "first_trading_date": u["ftd"], "realized_fall_event": 1 - u["Y"][h], "training_n_oot_open": f["n_oot_open"],
            "training_n_filter_excluded": len(f["excluded"]), "training_filter_excluded_sha256": ihash(f["excluded"]) if f["excluded"] else "",
            "test_f1r_raw": repr(float(u["f1r"])) if "f1r" in (FEATS[f["model"]]) else "",
            "test_f3": repr(float(u["f3"])) if "f3" in FEATS[f["model"]] else "",
            "test_add_sale": str(u["add_sale"]) if "add_sale" in FEATS[f["model"]] else "",
            "test_tufe_month": u["tufe_month"] if "f1r" in FEATS[f["model"]] else "", "test_tufe_index": u["tufe_index"] if "f1r" in FEATS[f["model"]] else "",
            "logit_status": r["status"], "logit_selected_C": "" if r["C"] is None else str(hp_label(r["C"])), "logit_tuning_status": r["tuning"],
            "logit_inner_fold_n": r["inner_fold_n"], "logit_columns": json.dumps(r["columns"], separators=(",", ":")),
            "logit_score_table": r["score_table"], "logit_n_class_0": r["n_class_0"], "logit_n_class_1": r["n_class_1"],
            "logit_probability": r["p"], "logit_predicted_class": r["pred"], "logit_final_fit_attempts": r["attempts"],
            "logit_intercept": r["intercept"], "logit_coef": coef, "test_clipped_features": None if r["clipped"] is None else json.dumps(r["clipped"], separators=(",", ":")),
            "f3_filter_mode_ties_n": r["f3_filter_mode_ties_n"], "inner_filter_excluded_n": r["inner_filter_excluded_n"],
            "inner_held_out_not_scored_n": r["inner_held_out_not_scored_n"]}


def run_model(model, j10=True, d5_rule="D5", workers=None, horizons=HORIZONS, tag=None):
    folds = [f for f in plan(model, j10=j10, d5_rule=d5_rule) if f["h"] in horizons]
    scorable = [f for f in folds if f["scorable"]]
    t1 = time.time()
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("fork")) as pool:
            parts = list(pool.map(_task, [(f, j10) for f in scorable], chunksize=1))
    else:
        parts = [run_fold(f, j10) for f in scorable]
    rows = [row_of(f, r) for f, r in zip(scorable, parts)]
    say(f"[koşu] {tag or model}: fold {len(folds)} (skorlanabilir {len(scorable)}: " + ", ".join(f"{h} {sum(1 for f in scorable if f['h'] == h)}" for h in horizons)
        + f"); durumlar {dict(Counter(r['logit_status'] for r in rows))}; {time.time() - t1:.0f} sn")
    return folds, rows


say("\n=== 1b. Fold planları (§5.1, §11-6; K6-A) ===")
PLANS = {m: plan(m) for m in MODELS}
for m in MODELS:
    fs = PLANS[m]
    tests = sorted({f["test"] for f in fs})
    near = [f for f in fs if f["h"] == "D10" and f["scorable"] and f["T"] >= NEAR_START]
    say(f"[1b] {m}: test arzı {len(tests)}; skorlanabilir D10 {sum(1 for f in fs if f['h'] == 'D10' and f['scorable'])}, D5 "
        f"{sum(1 for f in fs if f['h'] == 'D5' and f['scorable'])}; yakın dönem D10 fold {len(near)} ({len({f['T'][:7] for f in near})} ay); "
        f"f3 dışlamalı fold D10 {sum(1 for f in fs if f['h'] == 'D10' and f['excluded'])}, D5 {sum(1 for f in fs if f['h'] == 'D5' and f['excluded'])}")
near_h99 = {f["test"] for f in PLANS[H99M] if f["h"] == "D10" and f["scorable"] and f["T"] >= NEAR_START}
near_pool = {f["test"] for f in PLANS[POOL] if f["h"] == "D10" and f["scorable"] and f["T"] >= NEAR_START}
say(f"[1b] yakın dönem ticker kümesi h99 == pooled: {near_h99 == near_pool} ({len(near_h99)}); plan test kümeleri h99 == pooled: "
    f"{ {f['test'] for f in PLANS[H99M]} == {f['test'] for f in PLANS[POOL]} }")
OUT["plans"] = {m: {"tests": len({f["test"] for f in PLANS[m]}), "scorable": {h: sum(1 for f in PLANS[m] if f["h"] == h and f["scorable"]) for h in HORIZONS},
                    "near_d10": sum(1 for f in PLANS[m] if f["h"] == "D10" and f["scorable"] and f["T"] >= NEAR_START),
                    "excluded_folds": {h: sum(1 for f in PLANS[m] if f["h"] == h and f["excluded"]) for h in HORIZONS}} for m in MODELS}
# (ii) eğitim kesimi: her eğitim satırında D_h seansı < T; D5 fold'larında D10 seansı ≥ T olan satır sayısı (K6 bilgisi)
viol = {m: sum(1 for f in PLANS[m] for t in f["training"] if not UNITS[t]["sess"][f["h"]] < f["T"]) for m in MODELS}
d5_d10_after = {m: sum(1 for f in PLANS[m] if f["h"] == "D5" for t in f["training"] if UNITS[t]["sess"]["D10"] >= f["T"]) for m in MODELS}   # bütün fold'lar (K6 sayımı kalıbı)
same_day = {m: sum(1 for f in PLANS[m] for t in f["training"] if UNITS[t]["ftd"] == f["T"]) for m in MODELS}
say(f"[2-ii] D_h seansı < T ihlali (ufuk başına, K6): {viol}; D5 fold'unda D10 seansı ≥ T olan (fold, satır) çifti: {d5_d10_after} "
    f"(K6 kaydı: h99 94, havuz 98, addsale 103); aynı gün eğitim satırı: {same_day}")
OUT["leak_ii"] = {"violations": viol, "d5_rows_with_d10_after_T": d5_d10_after, "same_day": same_day}
# (iii) TÜFE: her kullanımda release_date < T (satırın kendi T'si ve fold'un T'si)
tufe_viol = sum(1 for m in (H99M, POOL) for f in PLANS[m] if f["scorable"] for t in (*f["training"], f["test"]) if not UNITS[t]["tufe_release"] < f["T"])
say(f"[2-iii] TÜFE yayım günü ≥ fold T'si olan kullanım: {tufe_viol}; satırın kendi T'sine göre PIT ihlali: "
    f"{sum(1 for u in UNITS.values() if not u['tufe_release'] < u['ftd'])}/170; ay kuralı m−2 (ör. {UNITS[ORDER_H99[-1]]['ftd']} → {UNITS[ORDER_H99[-1]]['tufe_month']})")
OUT["leak_iii"] = {"fold_violations": tufe_viol}

# ============================================================ 1c. koşular ve ledger karşılaştırması
say("\n=== 1c. Walk-forward koşuları ve altın ledger karşılaştırması (|Δ| ≤ 1e-9) ===")
GOLDL = {m: rd(GOLD / f"{m}_fold_ledger.csv", enc="utf-8") for m in MODELS}
RUNS: dict[str, list[dict]] = {}
for m in MODELS:
    RUNS[m] = run_model(m)[1]

EXACT = ("fold_id", "horizon", "ticker", "prediction_date", "prediction_cutoff_date", "target_session_date", "training_n", "n_chronological_train", "training_tickers_sha256",
         "training_targets_sha256", "ipo_price", "realized_return", "realized_direction", "first_trading_date", "realized_fall_event",
         "training_n_oot_open", "training_n_filter_excluded", "training_filter_excluded_sha256", "test_f1r_raw", "test_f3", "test_add_sale",
         "test_tufe_month", "test_tufe_index", "logit_status", "logit_selected_C", "logit_tuning_status", "logit_inner_fold_n", "logit_columns",
         "logit_n_class_0", "logit_n_class_1", "logit_predicted_class", "test_clipped_features", "f3_filter_mode_ties_n",
         "inner_filter_excluded_n", "inner_held_out_not_scored_n")


def compare_ledger(m, mine, gold):
    gb = {r["fold_id"]: r for r in gold}
    mb = {r["fold_id"]: r for r in mine}
    res = {"n_mine": len(mine), "n_gold": len(gold), "fold_ids_equal": list(mb) == list(gb), "exact_mismatch": Counter(), "max_abs": {},
           "official_close_dec_eq": 0}
    maxd = {"logit_probability": 0.0, "logit_intercept": 0.0, "logit_coef": 0.0, "logit_score_table": 0.0}
    n_p = 0
    for fid, g in gb.items():
        r = mb.get(fid)
        if r is None:
            res["exact_mismatch"]["missing_fold"] += 1
            continue
        for k in EXACT:
            gv, rv = g[k], r[k]
            rv = "" if rv is None else str(rv)
            if k == "logit_selected_C" and rv and gv and rv != "ZERO" and gv != "ZERO":
                ok = float(rv) == float(gv)
            else:
                ok = rv == gv
            if not ok:
                res["exact_mismatch"][k] += 1
        res["official_close_dec_eq"] += Decimal(g["official_close"]) == Decimal(r["official_close"])
        if g["logit_status"] == "FIT_OK" and r["logit_status"] == "FIT_OK":
            n_p += 1
            maxd["logit_probability"] = max(maxd["logit_probability"], abs(float(g["logit_probability"]) - r["logit_probability"]))
            maxd["logit_intercept"] = max(maxd["logit_intercept"], abs(float(g["logit_intercept"]) - r["logit_intercept"]))
            gc = json.loads(g["logit_coef"]) if g["logit_coef"] else {}
            rc = json.loads(r["logit_coef"]) if r["logit_coef"] else {}
            if set(gc) != set(rc):
                res["exact_mismatch"]["coef_keys"] += 1
            for c in gc:
                maxd["logit_coef"] = max(maxd["logit_coef"], abs(gc[c] - rc.get(c, float("nan"))))
        gt = json.loads(g["logit_score_table"]) if g["logit_score_table"] else []
        rt = r["logit_score_table"] or []
        if [(e["hyperparameter"], e["fold_count"], e["status"]) for e in gt] != [(e["hyperparameter"], e["fold_count"], e["status"]) for e in rt]:
            res["exact_mismatch"]["score_table_shape"] += 1
        else:
            for ge, re_ in zip(gt, rt):
                if ge["score"] is not None:
                    maxd["logit_score_table"] = max(maxd["logit_score_table"], abs(ge["score"] - re_["score"]))
        ga = json.loads(g["logit_final_fit_attempts"]) if g["logit_final_fit_attempts"] else []
        if [(str(a[0]), a[1]) for a in ga] != [(str(a[0]), a[1]) for a in r["logit_final_fit_attempts"]]:
            res["exact_mismatch"]["final_fit_attempts"] += 1
    res["max_abs"] = maxd
    res["n_fit_ok_compared"] = n_p
    res["exact_mismatch"] = dict(res["exact_mismatch"])
    res["ok"] = not res["exact_mismatch"] and res["fold_ids_equal"] and all(v <= TOL for v in maxd.values())
    return res


OUT["ledgers"] = {}
for m in MODELS:
    c = compare_ledger(m, RUNS[m], GOLDL[m])
    OUT["ledgers"][m] = c
    say(f"[1c] {m}: satır {c['n_mine']}/{c['n_gold']}, fold sırası aynı {c['fold_ids_equal']}, birebir uyuşmazlık {c['exact_mismatch'] or 'yok'}, "
        f"FIT_OK karşılaştırılan {c['n_fit_ok_compared']}, maks |Δ| p {c['max_abs']['logit_probability']:.2e}, sabit {c['max_abs']['logit_intercept']:.2e}, "
        f"katsayı {c['max_abs']['logit_coef']:.2e}, iç LOOCV tablosu {c['max_abs']['logit_score_table']:.2e}; official_close Decimal-eşit "
        f"{c['official_close_dec_eq']}/{c['n_gold']} → {'TUTTU' if c['ok'] else 'TUTMADI'}")

# Newton doğrulaması: birkaç fold'da (ve nihai fit'lerde) sklearn ile bağımsız Newton optimumunun |Δp| ≤ 1e-6
say("\n=== Çözücüden bağımsızlık: Newton (|Δp| ≤ 1e-6) ===")
newton = []
for m, fid in ((H99M, "D10|NETCD"), (POOL, "D10|ODINE"), (ADDS, "D5|BALSU"), (POOL, "D5|EKDMR")):
    f = next(f for f in PLANS[m] if f"{f['h']}|{f['test']}" == fid and f["scorable"])
    r = fit_logit(f["training"], FEATS[m], f["h"], test=f["test"])
    if r["status"] != "FIT_OK" or r["C"] == ZERO:
        newton.append({"fold": fid, "status": r["status"]})
        continue
    b, beta = newton_logit(r["X"], r["y"], r["C"])
    tz, _ = r["prep"].transform(f["test"])
    p_new = 1 / (1 + math.exp(-(b + float(np.dot(beta, tz)))))
    d = abs(p_new - r["p"])
    mcd = float(max(abs(b - r["intercept"]), float(np.max(np.abs(beta - np.array(list(r["coef"].values())))))))
    newton.append({"fold": fid, "model": m, "C": r["C"], "p_sklearn": r["p"], "p_newton": p_new, "abs_diff": d, "max_coef_diff": mcd})
    say(f"[newton] {m} {fid}: C={r['C']} p_sklearn={r['p']:.12f} p_newton={p_new:.12f} |Δp|={d:.2e} maks |Δβ|={newton[-1]['max_coef_diff']:.2e}")
OUT["newton"] = newton

# ============================================================ 1d. nihai fit önizlemeleri (4)
say("\n=== 1d. Nihai fit önizlemeleri (§2.3, §11-5; |Δ| ≤ 1e-9, C birebir) ===")
PREV = {m: json.loads((GOLD / f"{m}_final_fit_preview.json").read_text(encoding="utf-8")) for m in MODELS}
FINAL: dict[str, dict[str, dict]] = {}
OUT["previews"] = {}
for m in MODELS:
    rows = set_rows(m)
    excl = f3_excluded(rows) if "f3" in (FEATS[POOL] if m == ZROW else FEATS[m]) else ()
    used = [t for t in rows if t not in set(excl)]
    fits = {}
    for h in HORIZONS:
        fits[h] = fit_logit(used, (), h, uses_f3=False, rate_only=True) if m == ZROW else fit_logit(used, FEATS[m], h)
    FINAL[m] = fits
    g = PREV[m]
    res = {"C_equal": {}, "max_abs": {}, "exact": {}}
    for h in HORIZONS:
        gh, r = g["horizons"][h]["p_up"], fits[h]
        if gh["kind"] == "constant":
            res["C_equal"][h] = gh["C"] == "ZERO" and r["C"] == ZERO
            res["exact"][h] = {"value_bit_equal": gh["value"] == r["constant"], "n0": gh["n_class_0"] == r["n_class_0"], "n1": gh["n_class_1"] == r["n_class_1"]}
            frac = float(1 - Fraction(g["training"][f"events_{h}"], g["training"]["n"]))
            res["exact"][h]["fraction_bit_equal"] = frac == r["constant"] == gh["value"]
            continue
        res["C_equal"][h] = float(gh["C"]) == r["C"]
        md = {"intercept": abs(gh["intercept"] - r["intercept"]), "coef": max(abs(a - r["coef"][c]) for c, a in zip(gh["columns"], gh["coef"])),
              "inner_loocv_brier": max(abs(v - next(e["score"] for e in r["score_table"] if str(e["hyperparameter"]) == k)) for k, v in gh["inner_loocv_brier"].items())}
        res["max_abs"][h] = md
        res["exact"][h] = {"columns": gh["columns"] == r["columns"], "n0": gh["n_class_0"] == r["n_class_0"], "n1": gh["n_class_1"] == r["n_class_1"],
                           "inner_folds": gh["inner_loocv_folds"] == r["inner_fold_n"], "attempts": [[str(a[0]), a[1]] for a in gh["final_fit_attempts"]] == [[str(a[0]), a[1]] for a in r["attempts"]],
                           "status_all_scored": all(v == "SCORED" for v in gh["inner_loocv_status"].values()) == all(e["status"] == "SCORED" for e in r["score_table"])}
    if m != ZROW:
        pr = fits["D10"]["prep"].params()
        gp = g["preprocessing"]
        pm = {"winsor": max([abs(gp["winsor"][c][k] - pr["winsor"][c][k]) for c in gp["winsor"] for k in ("p05", "p95")] or [0.0]),
              "mean": max(abs(gp["mean"][c] - pr["mean"][c]) for c in gp["mean"]), "std": max(abs(gp["std"][c] - pr["std"][c]) for c in gp["std"])}
        res["prep_max_abs"] = pm
        res["prep_exact"] = {"columns": gp["columns"] == pr["columns"], "f3_filter_mode": gp["f3_filter_mode"] == pr["f3_filter_mode"],
                             "log_transform": sorted(gp["log_transform"]) == sorted(c for c in FEATS[m] if c in LOGCOL),
                             "winsor_cols": sorted(gp["winsor"]) == sorted(c for c in FEATS[m] if c in WINSCOL), "nulled": gp["f3_filter_nulled_tickers"] == []}
        fr = {c: (min(float(raw_of(t, FEATS[m])[c]) for t in used), max(float(raw_of(t, FEATS[m])[c]) for t in used)) for c in FEATS[m]}
        res["feature_ranges_equal"] = all((g["feature_ranges"][c]["min"], g["feature_ranges"][c]["max"], g["feature_ranges"][c]["n"]) == (fr[c][0], fr[c][1], len(used)) for c in FEATS[m])
    tr = g["training"]
    res["training_equal"] = {"n": tr["n"] == len(used), "tickers_sha256": tr["tickers_sha256"] == ihash(used), "tickers_list": tr["tickers"] == used,
                             "events": (tr["events_D5"], tr["events_D10"]) == tuple(sum(1 for t in used if UNITS[t]["Y"][h] == 0) for h in HORIZONS),
                             "cohort_counts": tr["cohort_counts"] == {c: sum(1 for t in used if UNITS[t]["cohort"] == c) for c in ("H99", "OOT_OPEN")},
                             "filter_excluded": tr["filter_excluded"] == list(excl), "set": tr["set"] == SETS[m],
                             "ftd_range": tr["first_trading_date_range"] == [min(UNITS[t]["ftd"] for t in used), max(UNITS[t]["ftd"] for t in used)]}
    res["spec_doc_sha_equal"] = g["spec"]["spec_document"]["sha256"] == sha_file(ROOT / "docs" / "specs_faz7_c" / "SPEC_C_V0.md") and \
        g["spec"]["decisions_document"]["sha256"] == sha_file(ROOT / "docs" / "specs_faz7_c" / "KARARLAR_C.md")
    allmax = [v for d in res["max_abs"].values() for v in d.values()] + list(res.get("prep_max_abs", {}).values())
    res["ok"] = all(res["C_equal"].values()) and all(all(d.values()) for d in res["exact"].values()) and all(res["training_equal"].values()) \
        and all(v <= TOL for v in allmax) and res.get("feature_ranges_equal", True) and all(res.get("prep_exact", {True: True}).values())
    OUT["previews"][m] = res
    say(f"[1d] {m}: C birebir {res['C_equal']}, maks |Δ| {({h: {k: f'{v:.1e}' for k, v in d.items()} for h, d in res['max_abs'].items()}) or '—'}, ön işleme maks |Δ| "
        f"{({k: f'{v:.1e}' for k, v in res.get('prep_max_abs', {}).items()}) or '—'}, eğitim bloğu {all(res['training_equal'].values())}, "
        f"özellik aralıkları {res.get('feature_ranges_equal', '—')}, belge sha {res['spec_doc_sha_equal']} → {'TUTTU' if res['ok'] else 'TUTMADI'}")
zr = OUT["previews"][ZROW]["exact"]
say(f"[1d] @ZERO: D10 {PREV[ZROW]['horizons']['D10']['p_up']['value']!r} == float(1 − 39/161) {zr['D10']['fraction_bit_equal']}; D5 "
    f"{PREV[ZROW]['horizons']['D5']['p_up']['value']!r} == float(1 − 29/161) {zr['D5']['fraction_bit_equal']}")
# Newton nihai fit'lerde
for m in (H99M, POOL, ADDS):
    for h in HORIZONS:
        r = FINAL[m][h]
        b, beta = newton_logit(r["X"], r["y"], r["C"])
        d = float(max(abs(b - r["intercept"]), float(np.max(np.abs(beta - np.array(list(r["coef"].values())))))))
        pmax = float(np.max(np.abs(1 / (1 + np.exp(-(b + r["X"] @ beta))) - 1 / (1 + np.exp(-(r["intercept"] + r["X"] @ np.array(list(r["coef"].values()))))))))
        newton.append({"fold": f"final|{m}|{h}", "max_coef_diff": d, "max_train_p_diff": pmax})
        say(f"[newton] nihai {m} {h}: maks |Δβ| {d:.2e}, eğitim satırlarında maks |Δp| {pmax:.2e}")

# ============================================================ 1e. hücreler (§5.1, §5.4, §6.2; C7 aralık)
say("\n=== 1e. Hücreler (§5.1 birincil, ikinciller, merdiven, keşif; C7 aralık) ===")
for k, pin in CMP_PINS.items():
    assert sha_file(GOLD1A / f"{k}_fold_ledger.csv") == pin, k
CMP = {k: rd(GOLD1A / f"{k}_fold_ledger.csv", enc="utf-8") for k in CMP_PINS}
v15 = [(float(r["logit_probability"]), int(r["realized_direction"])) for r in CMP["v1_5_h99"] if r["horizon"] == "D10" and r["logit_status"] == "FIT_OK"]
v15_brier = sum((p - y) ** 2 for p, y in v15) / len(v15)
say(f"[1e] karşılaştırıcı ledger sha'ları pinli; V1.5 D10 Brier (Logit FIT_OK, kırpmasız) {v15_brier:.10f} n={len(v15)} (yayımlı 0.1883, 81 fold)")
OUT["v15_d10_brier"] = {"n": len(v15), "brier": v15_brier}


def p_of(r):
    if "logit_status" in r:
        return float(r["logit_probability"]) if r["logit_status"] == "FIT_OK" else None
    v = r.get("rule_p_up")
    return None if v in (None, "") else float(v)


def boot(diffs, months, seed=20260921, reps=4000):
    by = {}
    for mo, d in zip(months, diffs):
        by.setdefault(mo, []).append(d)
    keys = list(by)
    rng = random.Random(seed)
    out = []
    for _ in range(reps):
        s = []
        for kk in rng.choices(keys, k=len(keys)):
            s += by[kk]
        out.append(sum(s) / len(s))
    out.sort()
    return out[100], out[3899]


def paired(model_rows, other_rows, horizon="D10", start=None, end=None, seed=20260921):
    other = {}
    for r in other_rows:
        if r["horizon"] == horizon:
            p = p_of(r)
            if p is not None:
                other[r["ticker"]] = p
    diffs, months, a, b, tk = [], [], [], [], []
    for r in model_rows:
        T = r["prediction_date"]
        p = p_of(r) if r["horizon"] == horizon else None
        if p is None or (start and T < start) or (end and T >= end) or r["ticker"] not in other:
            continue
        y = int(r["realized_direction"])
        la, lb = (p - y) ** 2, (other[r["ticker"]] - y) ** 2
        diffs.append(la - lb)
        months.append(T[:7])
        a.append(la)
        b.append(lb)
        tk.append(r["ticker"])
    if not diffs:
        return None
    ci = list(boot(diffs, months, seed=seed)) if len(diffs) >= 10 and len(set(months)) >= 6 else None
    return {"n": len(diffs), "n_months": len(set(months)), "model": sum(a) / len(a), "rule": sum(b) / len(b), "mean": sum(diffs) / len(diffs), "ci95": ci,
            "wins": sum(1 for d in diffs if d < 0), "losses": sum(1 for d in diffs if d > 0), "ties": sum(1 for d in diffs if d == 0),
            "ties_1e12": sum(1 for d in diffs if abs(d) <= 1e-12), "events": sum(1 for r in model_rows if r["horizon"] == horizon and r["ticker"] in tk and int(r["realized_direction"]) == 0),
            "diffs": dict(zip(tk, diffs)), "months": months}


def label(ci):
    if ci is None:
        return "belirsiz"
    lo, hi = ci
    if lo > 0:
        return "bozuyor"
    if hi <= DELTA:
        return "tolerans içinde"
    return "belirsiz"


def position(d, lo, hi):
    return "altında (beklentiden çok iyi)" if d < lo else ("üstünde" if d > hi else "aralık içinde")


# §6.2 tablosu şartname dosyasından (aynen)
spec_txt = (ROOT / "docs" / "specs_faz7_c" / "SPEC_C_V0.md").read_text(encoding="utf-8")
sec = spec_txt.split("### 6.2")[1].split("### 6.3")[0]
EXP62 = {}
for line in sec.splitlines():
    if line.startswith("| `") or line.startswith("| her aday"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        key = cells[0].replace("**", "").replace("`", "").replace("(birincil)", "").replace("(ikincil)", "").strip()
        pt = float(cells[1].replace("−", "-").replace("**", ""))
        lo, hi = (float(x.replace("−", "-")) for x in cells[2].replace("**", "").strip("[]").split(","))
        EXP62[key] = (pt, lo, hi, cells[3].replace("**", ""))
say(f"[1e] §6.2 tablosu şartnameden okundu: {len(EXP62)} satır: {list(EXP62)}")
assert EXP62["pooled − h99"] == (-0.002, -0.015, 0.012, '"belirsiz" ya da "tolerans içinde"')

# Ledger sözlüklerinin ortak biçimi (benimkiler p float; altın metin)
MY = {m: [{**r, "logit_probability": r["logit_probability"]} for r in RUNS[m]] for m in MODELS}
CANDS = (H99M, POOL, ADDS)
DECLARED = [(m, c, h) for m in CANDS for c, h in (("base_rate", "D10"), ("base_rate", "D5"), ("v1_5_h99", "D10"))] + [(POOL, ZROW, "D10")]
EXPLOR = [(m, "v1_5_h99", "D5") for m in CANDS] + [(POOL, ZROW, "D5")]
LADDER = [(H99M, ADDS, "D10"), (POOL, H99M, "D10"), (POOL, ZROW, "D10")]
OTHER_PAIRS = [(POOL, H99M)] + [(m, "base_rate") for m in CANDS] + [(m, "v1_5_h99") for m in CANDS] + [(POOL, ZROW)]


def all_cells(src):
    cells = {}
    cells["near"] = paired(src[POOL], src[H99M], "D10", start=NEAR_START)
    for k in DECLARED + EXPLOR + LADDER:
        cells[f"declared|{k[0]}|{k[1]}|{k[2]}"] = paired(src[k[0]], src[k[1]], k[2], start=NEAR_START)
    for a, b in OTHER_PAIRS:
        cells[f"2023|{a}|{b}|D10"] = paired(src[a], src[b], "D10", end=NEAR_START)
        cells[f"all|{a}|{b}|D10"] = paired(src[a], src[b], "D10")
    return cells


CELLS_MINE = all_cells({**CMP, **MY})
CELLS_GOLD = all_cells({**CMP, **GOLDL})


def cell_diff(a, b):
    if a is None or b is None:
        return {"both": a is None and b is None}
    d = {"n": a["n"] == b["n"], "months": a["n_months"] == b["n_months"], "wlt": (a["wins"], a["losses"], a["ties"]) == (b["wins"], b["losses"], b["ties"]),
         "mean": abs(a["mean"] - b["mean"]), "model": abs(a["model"] - b["model"]), "rule": abs(a["rule"] - b["rule"])}
    if a["ci95"] is None or b["ci95"] is None:
        d["ci"] = a["ci95"] is None and b["ci95"] is None
    else:
        d["ci"] = max(abs(a["ci95"][0] - b["ci95"][0]), abs(a["ci95"][1] - b["ci95"][1]))
    d["ok"] = d["n"] and d["months"] and d["wlt"] and d["mean"] <= TOL and d["model"] <= TOL and d["rule"] <= TOL and (d["ci"] is True or d["ci"] <= TOL)
    return d


OUT["cells"] = {}
worst = 0.0
for k in CELLS_MINE:
    dd = cell_diff(CELLS_MINE[k], CELLS_GOLD[k])
    OUT["cells"][k] = {"mine": {kk: v for kk, v in (CELLS_MINE[k] or {}).items() if kk not in ("diffs", "months")},
                       "from_gold": {kk: v for kk, v in (CELLS_GOLD[k] or {}).items() if kk not in ("diffs", "months")}, "diff": dd}
    if "mean" in dd:
        worst = max(worst, dd["mean"], dd["ci"] if dd["ci"] is not True else 0.0)
say(f"[1e] {len(CELLS_MINE)} hücre: benim ledger'larımdan vs Opus ledger'larından hesap; hepsi tutuyor: "
    f"{all(OUT['cells'][k]['diff'].get('ok', OUT['cells'][k]['diff'].get('both')) for k in OUT['cells'])}; maks |Δ| (fark, aralık) {worst:.2e}")


def fmt(c):
    if c is None:
        return "—"
    ci = "—" if c["ci95"] is None else f"[{c['ci95'][0]:+.4f}, {c['ci95'][1]:+.4f}]"
    return f"{c['mean']:+.4f} {ci} n={c['n']} ({c['n_months']} ay, olay {c['events']}) {c['wins']}/{c['losses']}/{c['ties']} (|d|≤1e-12: {c['ties_1e12']}) model {c['model']:.4f} karş {c['rule']:.4f}"


near = CELLS_MINE["near"]
say(f"[1e] BİRİNCİL pooled − h99 D10 (yakın dönem): {fmt(near)} → etiket {label(near['ci95'])}; §6.2 konumu: "
    f"{position(near['mean'], EXP62['pooled − h99'][1], EXP62['pooled − h99'][2])}")
OUT["primary"] = {"mine": {k: v for k, v in near.items() if k not in ("diffs", "months")}, "label": label(near["ci95"]),
                  "position": position(near["mean"], EXP62["pooled − h99"][1], EXP62["pooled − h99"][2])}
# günlükteki tam hassasiyetli birincil hücre
log_near = None
for line in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines():
    e = json.loads(line)
    if e.get("kind") == "backtest" and e.get("model_id") == POOL and e.get("near_era"):
        log_near = e["near_era"]
d_log = max(abs(log_near["mean"] - near["mean"]), abs(log_near["ci95"][0] - near["ci95"][0]), abs(log_near["ci95"][1] - near["ci95"][1]))
say(f"[1e] günlükteki (Opus, tam hassasiyet) birincil hücreyle |Δ| {d_log:.2e}; etiket günlük '{log_near['label']}', n {log_near['n']}, ay {log_near['n_months']}, "
    f"kazanç/kayıp {log_near['model_better_n']}/{log_near['rule_better_n']}")
OUT["primary"]["log_max_abs"] = d_log
say("[1e] ilan edilmiş ikinciller (yakın dönem):")
SHORT = {H99M: "h99", POOL: "pooled", ADDS: "addsale", ZROW: "pooled@ZERO"}
for m, c, h in DECLARED:
    cc = CELLS_MINE[f"declared|{m}|{c}|{h}"]
    row62 = EXP62.get(f"{SHORT[m]} − {c}") or (EXP62.get("her aday − v1_5_h99") if c == "v1_5_h99" else None)
    pos = position(cc["mean"], row62[1], row62[2]) if (row62 and h == "D10") else "—"
    verdict = "aralık 0'ın altında" if cc["ci95"][1] < 0 else ("aralık 0'ın üstünde" if cc["ci95"][0] > 0 else "aralık 0'ı içeriyor")
    say(f"  {SHORT[m]} − {SHORT.get(c, c)} {h}: {fmt(cc)} → {verdict}; §6.2: {pos}")
    OUT["cells"][f"declared|{m}|{c}|{h}"]["verdict"] = verdict
    OUT["cells"][f"declared|{m}|{c}|{h}"]["position62"] = pos
say("[1e] merdiven (§5.4):")
for a, b, h in LADDER:
    say(f"  {SHORT[a]} − {SHORT[b]} {h}: {fmt(CELLS_MINE[f'declared|{a}|{b}|{h}'])}")
say("[1e] keşif:")
for m, c, h in EXPLOR:
    say(f"  {SHORT[m]} − {SHORT.get(c, c)} {h}: {fmt(CELLS_MINE[f'declared|{m}|{c}|{h}'])}")
for a, b in OTHER_PAIRS:
    for s in ("2023", "all"):
        say(f"  {SHORT[a]} − {SHORT.get(b, b)} D10 [{s}]: {fmt(CELLS_MINE[f'{s}|{a}|{b}|D10'])}")

# MODELS.md metniyle (basılı hassasiyet) karşılaştırma
md = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
sec7c = md.split("## Faz 7C")[1].split("\n## Faz 7:")[0]


def md_nums(line_prefix):
    for line in sec7c.splitlines():
        if line.startswith(line_prefix):
            return re.findall(r"[-+]?\d+\.\d{4}", line.replace("−", "-"))
    return None


md_checks = {}
r = md_nums("| `pooled − h99` **(BİRİNCİL)**")
md_checks["primary"] = [float(x) for x in r[:5]] == [round(near["model"], 4), round(near["rule"], 4), round(near["mean"], 4), round(near["ci95"][0], 4), round(near["ci95"][1], 4)]
for m, c, h in DECLARED:
    cc = CELLS_MINE[f"declared|{m}|{c}|{h}"]
    r = md_nums(f"| `{m}` | `{c}` | {h} |")
    md_checks[f"{SHORT[m]}-{SHORT.get(c, c)}-{h}"] = r is not None and [float(x) for x in r[:5]] == [round(cc["model"], 4), round(cc["rule"], 4), round(cc["mean"], 4), round(cc["ci95"][0], 4), round(cc["ci95"][1], 4)]
    if r is not None:
        line = next(l for l in sec7c.splitlines() if l.startswith(f"| `{m}` | `{c}` | {h} |"))
        md_checks[f"{SHORT[m]}-{SHORT.get(c, c)}-{h}-n-wlt"] = f"| {cc['n']} ({cc['n_months']}) |" in line and f"| {cc['wins']} / {cc['losses']} / {cc['ties']} (" in line
md_checks["label_belirsiz"] = "→ **belirsiz**" in sec7c and label(near["ci95"]) == "belirsiz"
md_checks["too_good_none"] = "Beklentiden çok iyi (T6: nokta §6.2 aralığının altında): yok." in sec7c
for a, b, h in LADDER:
    cc = CELLS_MINE[f"declared|{a}|{b}|{h}"]
    line = next((l for l in sec7c.splitlines() if f"`{SHORT[a]} − {SHORT[b]}` =" in l), "")
    nums = re.findall(r"[-+]?\d+\.\d{4}", line.replace("−", "-"))
    md_checks[f"ladder-{SHORT[a]}-{SHORT[b]}"] = [float(x) for x in nums[:3]] == [round(cc["mean"], 4), round(cc["ci95"][0], 4), round(cc["ci95"][1], 4)] and f"n = {cc['n']} ({cc['n_months']} ay)" in line
OUT["models_md"] = md_checks
say(f"[1e] MODELS.md Faz 7C bölümü (basılı 4 ondalık) ile: {sum(md_checks.values())}/{len(md_checks)} eşleşme; eşleşmeyen: {[k for k, v in md_checks.items() if not v] or 'yok'}")

# ============================================================ 2-i. test arzı sızıntısı: 3 fold'da test arzının özellik ve sonucunu değiştir
say("\n=== 2-i. Test arzı eğitime, kırpma sınırlarına ya da z istatistiklerine girmiyor (3 fold, mutasyonlu test arzı) ===")
leak_i = []
for m, fid in ((H99M, "D10|NETCD"), (POOL, "D10|ODINE"), (ADDS, "D5|BALSU")):
    f = next(f for f in PLANS[m] if f"{f['h']}|{f['test']}" == fid)
    base = fit_logit(f["training"], FEATS[m], f["h"], test=f["test"])
    u = UNITS[f["test"]]
    saved = {k: u[k] for k in ("f1r", "f3", "add_sale", "Y")}
    u["f1r"] = u["f1r"] * 7
    u["f3"] = (u["f3"] or Decimal(1)) / 3
    u["add_sale"] = 1 - u["add_sale"]
    u["Y"] = {h: 1 - v for h, v in u["Y"].items()}
    mut = fit_logit(f["training"], FEATS[m], f["h"], test=f["test"])
    u.update(saved)
    same = (base["intercept"] == mut["intercept"] and base["coef"] == mut["coef"] and base["score_table"] == mut["score_table"] and base["C"] == mut["C"]
            and base["prep"].params() == mut["prep"].params())
    leak_i.append({"fold": fid, "model": m, "fit_bit_equal": bool(same), "p_base": base["p"], "p_mutated": mut["p"]})
    say(f"[2-i] {m} {fid}: sabit/katsayı/iç tablo/C/ön işleme bit-eşit {same}; p {base['p']:.6f} → {mut['p']:.6f} (yalnız test satırı değişti)")
OUT["leak_i"] = leak_i

# ============================================================ 4. Tanı (model seçimine girmez)
say("\n=== 4. Tanı (bilgi; model seçimine girmez) ===")
near_rows = {m: [r for r in MY[m] if r["horizon"] == "D10" and r["logit_status"] == "FIT_OK" and r["prediction_date"] >= NEAR_START] for m in MODELS}
ads = near_rows[ADDS]
n_flag = sum(1 for r in ads if r["test_add_sale"] == "1")
ev_flag = sum(1 for r in ads if r["test_add_sale"] == "1" and r["realized_direction"] == 0)
ev_all = sum(1 for r in ads if r["realized_direction"] == 0)
ps = sorted({round(r["logit_probability"], 4) for r in ads})
say(f"[4a] addsale yakın dönem: {len(ads)} fold, test arzı bayrağı 1 olan {n_flag} (olay {ev_flag}); bayrak 0 olan {len(ads) - n_flag} (olay {ev_all - ev_flag}); "
    f"modelin verdiği farklı p_up sayısı {len(ps)} (aralık {ps[0]}…{ps[-1]}) — tek ikili özellik: fold içinde yalnız iki değer")
brate = {r["ticker"]: float(r["rule_p_up"]) for r in CMP["base_rate"] if r["horizon"] == "D10"}
d_flag = [(r["logit_probability"] - r["realized_direction"]) ** 2 - (brate[r["ticker"]] - r["realized_direction"]) ** 2 for r in ads if r["test_add_sale"] == "1" and r["ticker"] in brate]
d_nof = [(r["logit_probability"] - r["realized_direction"]) ** 2 - (brate[r["ticker"]] - r["realized_direction"]) ** 2 for r in ads if r["test_add_sale"] == "0" and r["ticker"] in brate]
say(f"[4a] addsale − base_rate D10 farkının kaynağı: bayraklı {len(d_flag)} fold ort. {sum(d_flag) / max(1, len(d_flag)):+.4f}, bayraksız {len(d_nof)} fold ort. "
    f"{sum(d_nof) / max(1, len(d_nof)):+.4f}; H99 eğitiminde bayraklı arz sayısı fold başına {sorted({sum(1 for t in f['training'] if UNITS[t]['add_sale'] == 1 and UNITS[t]['cohort'] == 'H99') for f in PLANS[ADDS] if f['h'] == 'D10' and f['T'] >= NEAR_START})} "
    f"(açık kümeden 13 sabit)")
OUT["diag_addsale"] = {"near_folds": len(ads), "flag1": n_flag, "flag1_events": ev_flag, "events": ev_all, "mean_diff_flag1": sum(d_flag) / max(1, len(d_flag)),
                       "mean_diff_flag0": sum(d_nof) / max(1, len(d_nof))}


def auc(ps, ys):
    pos = [p for p, y in zip(ps, ys) if y == 1]
    neg = [p for p, y in zip(ps, ys) if y == 0]
    if not pos or not neg:
        return None
    s = sum((1.0 if a > b else 0.5 if a == b else 0.0) for a in pos for b in neg)
    return s / (len(pos) * len(neg))


def decomp(ps, ys, bins=10):
    """Murphy ayrışımı: Brier = güvenilirlik − çözünürlük + belirsizlik (10 eşit kutu)."""
    n = len(ps)
    ybar = sum(ys) / n
    rel = res = 0.0
    for k in range(bins):
        idx = [i for i in range(n) if (k / bins <= ps[i] < (k + 1) / bins) or (k == bins - 1 and ps[i] == 1.0)]
        if not idx:
            continue
        pk = sum(ps[i] for i in idx) / len(idx)
        ok = sum(ys[i] for i in idx) / len(idx)
        rel += len(idx) * (pk - ok) ** 2
        res += len(idx) * (ok - ybar) ** 2
    return {"reliability": rel / n, "resolution": res / n, "uncertainty": ybar * (1 - ybar), "mean_p": sum(ps) / n, "obs": ybar}


pairs = {r["ticker"]: r for r in near_rows[H99M]}
common = [r for r in near_rows[POOL] if r["ticker"] in pairs]
ps_p = [r["logit_probability"] for r in common]
ps_h = [pairs[r["ticker"]]["logit_probability"] for r in common]
ys = [r["realized_direction"] for r in common]
dp, dh = decomp(ps_p, ys), decomp(ps_h, ys)
say(f"[4b] pooled − h99 (75 fold): ort p_up pooled {dp['mean_p']:.4f}, h99 {dh['mean_p']:.4f}, gözlenen yukarı oranı {dp['obs']:.4f}; AUC pooled {auc(ps_p, ys):.4f}, "
    f"h99 {auc(ps_h, ys):.4f}; Murphy: güvenilirlik pooled {dp['reliability']:.4f} / h99 {dh['reliability']:.4f}, çözünürlük pooled {dp['resolution']:.4f} / h99 "
    f"{dh['resolution']:.4f}, belirsizlik {dp['uncertainty']:.4f}")
# düzey (kalibrasyon) payı: h99'un p'sini pooled'ın ortalama düzeyine kaydırınca (logit ötelemesi) Brier ne olur
def shift_to_mean(ps, target):
    lo, hi = -10.0, 10.0
    for _ in range(100):
        mid = (lo + hi) / 2
        m = sum(1 / (1 + math.exp(-(math.log(p / (1 - p)) + mid))) for p in ps) / len(ps)
        lo, hi = (mid, hi) if m < target else (lo, mid)
    return [1 / (1 + math.exp(-(math.log(p / (1 - p)) + mid))) for p in ps]
b_p = sum((p - y) ** 2 for p, y in zip(ps_p, ys)) / len(ys)
b_h = sum((p - y) ** 2 for p, y in zip(ps_h, ys)) / len(ys)
ps_h_shift = shift_to_mean(ps_h, dp["mean_p"])
b_hs = sum((p - y) ** 2 for p, y in zip(ps_h_shift, ys)) / len(ys)
say(f"[4b] Brier pooled {b_p:.4f}, h99 {b_h:.4f} (fark {b_p - b_h:+.4f}); h99'un p'leri pooled'ın ortalama düzeyine logit ötelemesiyle kaydırılınca {b_hs:.4f} → "
    f"düzey payı {b_hs - b_h:+.4f}, kalan (ayırma) payı {b_p - b_hs:+.4f}")
by_year = {}
for r in common:
    y_ = r["prediction_date"][:4]
    d = (r["logit_probability"] - r["realized_direction"]) ** 2 - (pairs[r["ticker"]]["logit_probability"] - r["realized_direction"]) ** 2
    by_year.setdefault(y_, []).append((d, r["realized_direction"]))
for y_, ds in sorted(by_year.items()):
    say(f"[4b] yıl {y_}: n={len(ds)}, olay {sum(1 for _, yy in ds if yy == 0)}, ort. fark {sum(d for d, _ in ds) / len(ds):+.4f}, pooled iyi {sum(1 for d, _ in ds if d < 0)}")
c_p = Counter(r["logit_selected_C"] for r in common)
c_h = Counter(pairs[r["ticker"]]["logit_selected_C"] for r in common)
say(f"[4b] seçilen C (yakın dönem D10): pooled {dict(c_p)}, h99 {dict(c_h)}; h99 eğitim n {min(int(pairs[r['ticker']]['training_n']) for r in common)}…{max(int(pairs[r['ticker']]['training_n']) for r in common)}, "
    f"pooled {min(int(r['training_n']) for r in common)}…{max(int(r['training_n']) for r in common)}")
OUT["diag_pooled_h99"] = {"mean_p": [dp["mean_p"], dh["mean_p"]], "obs": dp["obs"], "auc": [auc(ps_p, ys), auc(ps_h, ys)], "murphy": [dp, dh],
                         "brier": [b_p, b_h], "level_share": b_hs - b_h, "discrimination_share": b_p - b_hs,
                         "by_year": {y_: {"n": len(ds), "events": sum(1 for _, yy in ds if yy == 0), "mean_diff": sum(d for d, _ in ds) / len(ds)} for y_, ds in by_year.items()}}

# Kasa için gerçekçi güç: (a) yakın dönem farklarının dağılımından; (b) açık küme benzetimi (h99 nihai fit → açık kümede skor; 60'lık alt örnekler)
say("[4c] kasa gücü (beklenen ≈ 12 olay, n ≈ 60):")
d_hb = list(CELLS_MINE[f"declared|{H99M}|base_rate|D10"]["diffs"].values())
sd = float(np.std(d_hb, ddof=1))
ci_w = CELLS_MINE[f"declared|{H99M}|base_rate|D10"]["ci95"]
iid_w = 2 * 1.96 * sd / math.sqrt(len(d_hb))
say(f"[4c] (a) h99 − base_rate D10 yakın dönem: n={len(d_hb)}, sd(fark)={sd:.4f}; iid %95 genişlik {iid_w:.4f}, ay-blok genişlik {ci_w[1] - ci_w[0]:.4f} "
    f"(oran {(ci_w[1] - ci_w[0]) / iid_w:.2f}); n=60 için iid genişlik ≈ {2 * 1.96 * sd / math.sqrt(60):.4f}, blok oranıyla ≈ {2 * 1.96 * sd / math.sqrt(60) * (ci_w[1] - ci_w[0]) / iid_w:.4f}")
fin = FINAL[H99M]["D10"]
prep = fin["prep"]
open_f3 = [t for t in OPEN_TICKERS if UNITS[t]["f3"] is not None and UNITS[t]["add_sale"] is not None]
p_open = {}
for t in open_f3:
    z, _ = prep.transform(t)
    p_open[t] = 1 / (1 + math.exp(-(fin["intercept"] + sum(c * v for c, v in zip(fin["coef"].values(), z)))))
h99_rate = sum(UNITS[t]["Y"]["D10"] for t in ORDER_H99) / 99
d_open = {t: (p_open[t] - UNITS[t]["Y"]["D10"]) ** 2 - (h99_rate - UNITS[t]["Y"]["D10"]) ** 2 for t in open_f3}
mo_open = {t: UNITS[t]["ftd"][:7] for t in open_f3}
full = boot(list(d_open.values()), [mo_open[t] for t in open_f3])
say(f"[4c] (b) h99 nihai fit → açık kümede (n={len(open_f3)}, olay {sum(1 for t in open_f3 if UNITS[t]['Y']['D10'] == 0)}): Brier − taban(H99 oranı {h99_rate:.4f}) "
    f"= {sum(d_open.values()) / len(d_open):+.4f} [{full[0]:+.4f}, {full[1]:+.4f}] (aktarım hücresi; keşifte −0.023 [−0.066, +0.016])")
rng = random.Random(7)
widths, evs = [], []
for _ in range(200):
    sub = rng.sample(open_f3, 60)
    lo, hi = boot([d_open[t] for t in sub], [mo_open[t] for t in sub], seed=20260921)
    widths.append(hi - lo)
    evs.append(sum(1 for t in sub if UNITS[t]["Y"]["D10"] == 0))
widths.sort()
say(f"[4c] (b) 60'lık 200 alt örnek: aralık genişliği medyan {widths[100]:.4f} (IQR {widths[50]:.4f}–{widths[150]:.4f}), olay medyan {sorted(evs)[100]}; "
    f"yani kasada |fark| ≈ 0.02–0.03 olsa bile aralık 0'ı içerebilir (§6.1 beklentisiyle uyumlu)")
OUT["power"] = {"sd_diff_h99_base": sd, "iid_width_n60": 2 * 1.96 * sd / math.sqrt(60), "block_ratio": (ci_w[1] - ci_w[0]) / iid_w,
                "open_transfer": {"n": len(open_f3), "mean": sum(d_open.values()) / len(d_open), "ci95": list(full)},
                "sub60_width_median": widths[100], "sub60_width_iqr": [widths[50], widths[150]], "sub60_events_median": sorted(evs)[100]}

# ============================================================ 4d. Duyarlılıklar (bilgi; model DEĞİL) — sensitivity_runs.jsonl
say("\n=== 4d. Duyarlılıklar (kind: sensitivity; model değil, hiçbir tabloya girmez) ===")
SENS = []
SPEC_SHA = sha_file(ROOT / "docs" / "specs_faz7_c" / "SPEC_C_V0.md")
DEC_SHA = sha_file(ROOT / "docs" / "specs_faz7_c" / "KARARLAR_C.md")


def sens_entry(name, base, variant, rows, metrics, folds):
    p = OUT_DIR / "repro_ledgers" / f"sens_{name}.csv"
    write_compact(p, rows)
    e = {"kind": "sensitivity", "context": "fable_faz7c_audit_sensitivity", "audit_task": "BORSAI_FAZ7C_FABLE_REPRO_AUDIT_20260927",
         "model_id": f"{base}__sens_{name}", "base_model_id": base, "variant": variant, "code": "docs/fable_faz7c_audit/ekler/repro_fall.py",
         "spec_sha256": None, "spec_document": "docs/specs_faz7_c/SPEC_C_V0.md", "spec_document_sha256": SPEC_SHA, "decisions_document_sha256": DEC_SHA,
         "data_version_sha256": sha_file(ROOT / "data" / ("data_version.json" if base == H99M else "data_version_v2.json")),
         "training_table_sha256": sha_file(ROOT / "data" / ("training_table.csv" if base == H99M else "training_table_v2.csv")),
         "ledger_file": f"docs/fable_faz7c_audit/ekler/repro_ledgers/sens_{name}.csv", "ledger_sha256": sha_file(p),
         "folds_total": len(folds), "folds_scorable": sum(1 for f in folds if f["scorable"]), "metrics": metrics,
         "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "note": "denetim duyarlılığı; model değil; hiçbir skora/karta girmez"}
    SENS.append(e)
    return e


def write_compact(path, rows):
    keys = ["model_id", "fold_id", "horizon", "ticker", "prediction_date", "training_n", "training_n_oot_open", "training_n_filter_excluded",
            "logit_status", "logit_selected_C", "logit_n_class_0", "logit_n_class_1", "logit_probability", "realized_direction", "logit_intercept", "logit_coef",
            "logit_columns", "inner_filter_excluded_n", "test_clipped_features"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(keys)
        for r in rows:
            w.writerow(["" if r.get(k) is None else (repr(r[k]) if isinstance(r[k], float) else r[k]) for k in keys])


def strip(c):
    return None if c is None else {k: v for k, v in c.items() if k not in ("diffs", "months")}


# s1: K6 seçenek B — D5 fold'larında da D10 seansı < T (h99, pooled, addsale; yalnız D5)
s1 = {}
for m in (H99M, POOL, ADDS):
    folds, rows = run_model(m, d5_rule="D10", horizons=("D5",), tag=f"s1 K6-B {m}")
    cb = paired(rows, CMP["base_rate"], "D5", start=NEAR_START)
    s1[m] = {"vs_base_rate_D5": strip(cb), "official": strip(CELLS_MINE[f"declared|{m}|base_rate|D5"])}
    say(f"[s1] {SHORT[m]} − base_rate D5, K6-B (D10 < T): {fmt(cb)}  | resmi (K6-A): {fmt(CELLS_MINE[f'declared|{m}|base_rate|D5'])}")
    sens_entry(f"k6b_d5_cut_d10_{SHORT[m]}", m, "K6 seçenek B: D5 fold'unda eğitim satırı ancak D10 seansı < T", rows, s1[m], folds)
OUT["sens_s1"] = s1
# s2: J10 dışlaması kapalı (filtre adımı yok; FILTERED üyeler kalır) — pooled D10 ve @ZERO D10 → birincil hücre ve pooled − base_rate
folds2, rows2 = run_model(POOL, j10=False, horizons=("D10",), tag="s2 J10 kapalı pooled")
folds2z, rows2z = run_model(ZROW, j10=False, horizons=("D10",), tag="s2 J10 kapalı @ZERO")
c_near2 = paired(rows2, MY[H99M], "D10", start=NEAR_START)
c_b2 = paired(rows2, CMP["base_rate"], "D10", start=NEAR_START)
c_z2 = paired(rows2, rows2z, "D10", start=NEAR_START)
say(f"[s2] J10 kapalı: pooled − h99 D10: {fmt(c_near2)} → {label(c_near2['ci95'])} | resmi: {fmt(near)} → {label(near['ci95'])}")
say(f"[s2] J10 kapalı: pooled − base_rate D10: {fmt(c_b2)}; pooled − @ZERO: {fmt(c_z2)}")
OUT["sens_s2"] = {"near": strip(c_near2), "label": label(c_near2["ci95"]), "vs_base_rate": strip(c_b2), "vs_zero": strip(c_z2)}
sens_entry("j10_exclusion_off_pooled", POOL, "J10 f3 filtre dışlaması kapalı (3 FILTERED açık üye her fold'da eğitimde)", rows2 + rows2z, OUT["sens_s2"], folds2)
# s3: aralık üreteci — SPEC_SCORING §8 lafzı numpy Generator(PCG64(20260921)) ile (C7 kararı random.Random); yeniden fit yok
def boot_np(diffs, months, seed=20260921, reps=4000):
    by = {}
    for mo, d in zip(months, diffs):
        by.setdefault(mo, []).append(d)
    keys = list(by)
    g = np.random.Generator(np.random.PCG64(seed))
    stats = []
    for _ in range(reps):
        s = []
        for kk in g.choice(len(keys), size=len(keys), replace=True):
            s += by[keys[kk]]
        stats.append(sum(s) / len(s))
    return [float(x) for x in np.percentile(stats, [2.5, 97.5])]
s3 = {}
for k in ("near", f"declared|{H99M}|base_rate|D10", f"declared|{POOL}|base_rate|D10", f"declared|{ADDS}|base_rate|D10"):
    c = CELLS_MINE[k]
    ci_np = boot_np(list(c["diffs"].values()), c["months"])
    ci_alt = list(boot(list(c["diffs"].values()), c["months"], seed=1))
    s3[k] = {"c7_random": c["ci95"], "numpy_pcg64": ci_np, "random_seed_1": ci_alt, "label_c7": label(c["ci95"]), "label_np": label(ci_np), "label_seed1": label(ci_alt)}
    say(f"[s3] {k}: C7 random.Random {c['ci95'][0]:+.4f}/{c['ci95'][1]:+.4f} ({label(c['ci95'])}); numpy PCG64 {ci_np[0]:+.4f}/{ci_np[1]:+.4f} ({label(ci_np)}); "
        f"random seed 1 {ci_alt[0]:+.4f}/{ci_alt[1]:+.4f} ({label(ci_alt)})")
OUT["sens_s3"] = s3
sens_entry("bootstrap_generator", POOL, "aralık üreteci: numpy PCG64(20260921) ve random.Random(1) (yeniden fit yok)", MY[POOL], s3, PLANS[POOL])
with open(OUT_DIR / "sensitivity_runs.jsonl", "w", encoding="utf-8") as fh:
    for e in SENS:
        fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

# ============================================================ çıktılar
for m in MODELS:
    write_compact(OUT_DIR / "repro_ledgers" / f"{m}.csv", MY[m])
OUT["borsai_in_sys_modules"] = sorted(x for x in sys.modules if x == "borsai" or x.startswith("borsai."))
OUT["runtime"] = {"python": sys.version.split()[0], "numpy": np.__version__, "sklearn": __import__("sklearn").__version__, "seconds": round(time.time() - T0)}
OUT["verdict"] = {m: bool(OUT["ledgers"][m]["ok"] and OUT["previews"][m]["ok"]) for m in MODELS}
OUT["cells_all_ok"] = all(OUT["cells"][k]["diff"].get("ok", OUT["cells"][k]["diff"].get("both")) for k in OUT["cells"])
say(f"\n[son] borsai sys.modules'ta: {OUT['borsai_in_sys_modules'] or 'YOK'}; süre {OUT['runtime']['seconds']} sn; "
    f"ledger+önizleme tuttu: {OUT['verdict']}; hücreler tuttu: {OUT['cells_all_ok']}")
(OUT_DIR / "repro_output.json").write_text(json.dumps(OUT, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
(OUT_DIR / "repro_stdout.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")

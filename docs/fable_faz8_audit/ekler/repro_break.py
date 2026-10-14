#!/usr/bin/env python3
"""BORSAI_FAZ8_FABLE_REPRO_AUDIT_20261002 — `break_floor_v0` (+ kural satırı `break_floor_v0@ZERO`) SIFIRDAN, bağımsız
yeniden üretimi (Fable). `borsai` paketi İMPORT EDİLMEZ (dosyada import satırı yok; sonda ve çağıran alt süreçte sys.modules
denetimi). stdlib + numpy + scikit-learn (çözücü şartnamede sklearn L2 LogisticRegression; SPEC_V1_6 §3, §9).

Kodlandığı belgeler: SPEC_BREAK_V0 §1.2, §2, §3, §4, §5.1, §5.2, §6, §7, §13 (sözde kod); KARARLAR §A–§C; SPEC_V1_6 §3, §4, §9;
SPEC_CEILING_PATH_V0 §2, §3, §4, §7 (ürün karşılaştırıcısı; Faz 4 denetim betiğimin tick/Lo/hücre/merdiven parçaları yeniden
kullanıldı); SPEC_SCORING §2, §3, §8; SPEC_DEVIATIONS C7 (ay-blok bootstrap, random.Random(20260921), indeks 100/3899), H11
(Type-7 kesin Fraction, z 60 haneli Decimal), N2 (formül aynen), N3 (başlık başına ön işleme), N5 (@ZERO Fraction), N6, N7.
Girdiler (yalnız okunur): data/training_table.csv (P, shares_offered, ilk işlem günü), SESSIONS CSV (ham thb/thm alanları),
docs/faz8/backtest/* (yalnız karşılaştırma), tests/reference/macos_golden_faz4/ceiling_path_v0_fold_ledger.csv (hücre paritesi),
experiments/log.jsonl ve docs/MODELS.md (yalnız karşılaştırma). data/outcomes/, data/outcomes_oot/, scores/, registry/ OKUNMAZ.
Çıktı: stdout raporu, repro_output.json, repro_ledgers/*.csv (kompakt) — çıktı dizini argv[1] (varsayılan: bu dizin).
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
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal, localcontext
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

SESS_CSV = ROOT / "data" / "raw" / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv"
TT_CSV = ROOT / "data" / "training_table.csv"
LEDGER_DIR = ROOT / "docs" / "faz8" / "backtest"
G4_LEDGER = ROOT / "tests" / "reference" / "macos_golden_faz4" / "ceiling_path_v0_fold_ledger.csv"
LOG_PATH = ROOT / "experiments" / "log.jsonl"
MODELS_MD = ROOT / "docs" / "MODELS.md"

CTX60 = Context(prec=60, rounding=ROUND_HALF_EVEN)
TOL = 1e-9
NEAR_START = "2024-01-01"
CUTOFF_MAX = "2026-08-19"
ZERO = 0.0
GRID = (ZERO, 0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0)
FALLBACK_C = 0.01
MIN_ROWS, MIN_EV, MIN_NE = 10, 5, 5
N_MIN = 10
LOGIT_KW = dict(l1_ratio=0.0, solver="lbfgs", fit_intercept=True, class_weight=None, max_iter=10000, tol=1e-10)
MODEL = "break_floor_v0"
# varyant → (özellikler, kırpılan sütunlar)   (§3, §4.1; duyarlılıklar §7.2)
VARIANTS = {
    MODEL: (("b_floor", "b_turnover"), ("b_turnover",)),
    "break_floor_v0__sens_floor_only": (("b_floor",), ()),
    "break_floor_v0__sens_turnover_only": (("b_turnover",), ("b_turnover",)),
    "break_floor_v0__sens_with_group_Z": (("b_floor", "b_turnover", "group_Z"), ("b_turnover",)),
}
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
    """R Type-7 kantil, kesin Fraction (H11)."""
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


def D(x) -> Decimal:
    return Decimal(x)


def hp(C):
    return "ZERO" if C == ZERO else str(float(C))


# ============================================================ 0. Limit işlevleri (SPEC_CEILING_PATH_V0 §2; Faz 4 betiğim)
TICKS = [(Decimal(20), Decimal("0.01")), (Decimal(50), Decimal("0.02")), (Decimal(100), Decimal("0.05")),
         (Decimal(250), Decimal("0.10")), (Decimal(500), Decimal("0.25")), (Decimal(1000), Decimal("0.50")),
         (Decimal(2500), Decimal("1.00")), (None, Decimal("2.50"))]


def tick(x: Decimal) -> Decimal:
    for lim, s in TICKS:
        if lim is None or x < lim:
            return s
    raise AssertionError


def U_(b: Decimal) -> Decimal:
    y = b * Decimal("1.1")
    s = tick(y)
    return (y / s).to_integral_value(rounding=ROUND_FLOOR) * s


def Lo(b: Decimal) -> Decimal:
    y = b * Decimal("0.9")
    s = tick(y)
    return (y / s).to_integral_value(rounding=ROUND_CEILING) * s


def snap(P: Decimal) -> Decimal:
    s = tick(P)
    return (P / s).to_integral_value(rounding=ROUND_HALF_UP) * s


# ============================================================ 1. Veri ve kırılma tablosu (§1.2, §3, §7.1, §13-1)
TT_ROWS = rd(TT_CSV)
TT = {r["ticker"]: r for r in TT_ROWS}
assert len(TT) == 99
SESS_ROWS = rd(SESS_CSV)
S: dict[str, dict[int, dict]] = defaultdict(dict)
for r in SESS_ROWS:
    S[r["ticker"]][int(r["session_number"])] = r
assert len(SESS_ROWS) == 990 and all(len(S[t]) == 10 for t in TT)
assert max(r["target_session_date"] for r in SESS_ROWS) <= CUTOFF_MAX
# ham metin ↔ düzeltilmiş sütun Decimal eşitliği (N7 denetimi; hücreler ham kapanıştan kurulur)
assert all(D(r["thb_raw_close"]) == D(r["close"]) and D(r["thm_raw_lower_limit"]) == D(r["lower_limit"]) for r in SESS_ROWS)
ORDER = sorted(TT, key=lambda t: (TT[t]["first_trading_date"], t))


def label(r):
    lo = r["thm_raw_lower_limit"]
    if lo in ("", None) or D(lo) <= 0:
        return None
    return int(D(r["thb_raw_close"]) == D(lo))


U: dict[str, dict] = {}
for t in ORDER:
    P = D(TT[t]["ipo_price_tl"])
    shares = D(TT[t]["shares_offered"])
    L = 0
    for h in range(1, 11):
        r = S[t][h]
        if D(r["thb_raw_close"]) == D(r["thm_raw_upper_limit"]):
            L += 1
        else:
            break
    assert L == int(TT[t]["ceiling_streak_L"]), (t, L, TT[t]["ceiling_streak_L"])
    u = {"ticker": t, "ftd": TT[t]["first_trading_date"], "P": P, "shares": shares, "L": L, "group_Z": int(L == 0)}
    if L == 10:
        u["kind"] = "NO_BREAK"
        u["b"] = None
        U[t] = u
        continue
    b = L + 1
    r = S[t][b]
    u["b"] = b
    u["E"] = r["target_session_date"]
    u["closes"] = [D(S[t][h]["thb_raw_close"]) for h in range(1, b + 1)]
    u["close_b"], u["lower_b"], u["upper_b"], u["ref_b"] = D(r["thb_raw_close"]), D(r["thm_raw_lower_limit"]), D(r["thm_raw_upper_limit"]), D(r["thm_raw_reference_price"])
    u["high_b"], u["vol_b"], u["tc_b"] = D(r["thb_raw_high"]), D(r["thb_raw_volume"]), D(r["thb_raw_trade_count"])
    u["half"] = int(r["session_type"] == "OPEN_HALF_DAY")
    u["halt"] = int(r["security_trading_status"] != "ACTIVE_NOT_SUSPENDED")
    assert u["lower_b"] > 0 and u["vol_b"] > 0 and u["tc_b"] > 0
    u["b_floor"] = int(u["close_b"] == u["lower_b"])
    u["lock"] = int(u["high_b"] == u["lower_b"])
    u["band"] = u["lower_b"] / u["ref_b"]
    with localcontext(CTX60):
        ratio = u["vol_b"] / shares
        u["ratio"] = ratio
        u["b_turnover"] = float(ratio.ln())
    if b == 10:
        u["kind"] = "B10"
        U[t] = u
        continue
    u["kind"] = "BREAK"
    y1 = label(S[t][b + 1])
    u["y1"], u["y1_date"] = y1, S[t][b + 1]["target_session_date"]
    if b <= 8:
        y2x = label(S[t][b + 2])
        u["y2"] = None if (y1 is None or y2x is None) else int(y1 == 1 and y2x == 1)
        u["y2_date"] = S[t][b + 2]["target_session_date"]
    else:
        u["y2"], u["y2_date"] = None, None
    # yastık kuralı (§2.4)
    x = u["close_b"]
    for _ in range(10 - b):
        x = Lo(x)
    with localcontext(CTX60):
        k_b = float((u["close_b"] / P).ln() / (Decimal(1) / Decimal("0.9")).ln())
    u["sz"] = {"min10": x, "impossible": x > P, "k_b": k_b, "r_b": 10 - b, "approx": k_b >= 10 - b}
    U[t] = u

BREAKS = [t for t in ORDER if U[t]["kind"] == "BREAK"]
F2_UNITS = [t for t in BREAKS if U[t]["b"] <= 8]
NEAR = [t for t in BREAKS if U[t]["ftd"] >= NEAR_START]
acc = {
    "n_break_evenings": len(BREAKS),
    "b_dist": {b: sum(1 for t in BREAKS if U[t]["b"] == b) for b in range(1, 10)},
    "n_L10": sum(1 for t in ORDER if U[t]["kind"] == "NO_BREAK"),
    "n_b10": sum(1 for t in ORDER if U[t]["kind"] == "B10"),
    "b_floor_total": sum(U[t]["b_floor"] for t in BREAKS),
    "b_floor_2_9": sum(U[t]["b_floor"] for t in BREAKS if U[t]["b"] >= 2),
    "b_floor_1": sum(U[t]["b_floor"] for t in BREAKS if U[t]["b"] == 1),
    "half_day_b": sum(U[t]["half"] for t in ORDER if U[t]["kind"] != "NO_BREAK"),
    "halt_b": sum(U[t]["halt"] for t in ORDER if U[t]["kind"] != "NO_BREAK"),
    "ref_eq_prev_close": [sum(1 for t in ORDER if U[t]["kind"] != "NO_BREAK" and U[t]["b"] >= 2 and U[t]["ref_b"] == U[t]["closes"][-2]),
                          sum(1 for t in ORDER if U[t]["kind"] != "NO_BREAK" and U[t]["b"] >= 2)],
    "Lo_ref_eq_lower": [sum(1 for t in ORDER if U[t]["kind"] != "NO_BREAK" and Lo(U[t]["ref_b"]) == U[t]["lower_b"]),
                        sum(1 for t in ORDER if U[t]["kind"] != "NO_BREAK")],
    "floor_lock_allday": sum(U[t]["lock"] for t in BREAKS),
    "band_mismatch": sum(1 for t in BREAKS if not (Decimal("0.9") <= U[t]["band"] <= Decimal("0.9020"))),
    "structural_zero": {b: sum(1 for t in BREAKS if U[t]["b"] == b and U[t]["sz"]["impossible"]) for b in range(1, 10)},
    "structural_zero_total": sum(1 for t in BREAKS if U[t]["sz"]["impossible"]),
    "approx_rule_agrees": sum(1 for t in BREAKS if U[t]["sz"]["impossible"] == U[t]["sz"]["approx"]),
    "near_era": len(NEAR), "n_2023": len(BREAKS) - len(NEAR), "F2_units": len(F2_UNITS),
    "events_F1": sum(U[t]["y1"] for t in BREAKS), "events_F2": sum(U[t]["y2"] for t in F2_UNITS),
    "max_label_date_F1": max(U[t]["y1_date"] for t in BREAKS), "max_label_date_F2": max(U[t]["y2_date"] for t in F2_UNITS),
    "turnover_range": [min(U[t]["b_turnover"] for t in BREAKS), max(U[t]["b_turnover"] for t in BREAKS)],
    "by_type_full": {c: [sum(U[t]["y1"] for t in BREAKS if U[t]["b_floor"] == c), sum(1 for t in BREAKS if U[t]["b_floor"] == c)] for c in (0, 1)},
}
say(f"[veri] 99 arz, 990 seans; SESSIONS sha256 {sha_file(SESS_CSV)[:12]}; training_table sha256 {sha_file(TT_CSV)[:12]}")
say(f"[1a] kırılma akşamı {acc['n_break_evenings']}; b dağılımı " + "/".join(str(acc['b_dist'][b]) for b in range(1, 10)) +
    f"; L=10: {acc['n_L10']}; b=10: {acc['n_b10']}; b_floor {acc['b_floor_total']} (2≤b≤9: {acc['b_floor_2_9']}, b=1: {acc['b_floor_1']})")
say(f"[1a] yarım gün {acc['half_day_b']}, durdurma {acc['halt_b']}; ref==kapanış_{{b−1}} {acc['ref_eq_prev_close'][0]}/{acc['ref_eq_prev_close'][1]}; "
    f"Lo(ref)==alt {acc['Lo_ref_eq_lower'][0]}/{acc['Lo_ref_eq_lower'][1]}; gün boyu taban kilidi {acc['floor_lock_allday']}; bant uyuşmazlığı {acc['band_mismatch']}")
say(f"[1a] yapısal sıfır {acc['structural_zero_total']} (b: {acc['structural_zero']}); yaklaşık kuralla aynı {acc['approx_rule_agrees']}/82; "
    f"yakın dönem {acc['near_era']}, 2023: {acc['n_2023']}; F2 birimi {acc['F2_units']}; olay F1 {acc['events_F1']} / F2 {acc['events_F2']}; "
    f"son etiket F1 {acc['max_label_date_F1']} F2 {acc['max_label_date_F2']}; b_turnover aralığı {acc['turnover_range']}")
assert acc["n_break_evenings"] == 82 and [acc["b_dist"][b] for b in range(1, 10)] == [18, 11, 4, 13, 12, 8, 6, 6, 4]
assert acc["n_L10"] == 14 and acc["n_b10"] == 3 and acc["b_floor_total"] == 35 and acc["b_floor_2_9"] == 31 and acc["b_floor_1"] == 4
assert acc["ref_eq_prev_close"] == [67, 67] and acc["Lo_ref_eq_lower"] == [85, 85] and acc["structural_zero_total"] == 16
assert acc["structural_zero"][7] == 6 and acc["structural_zero"][8] == 6 and acc["structural_zero"][9] == 4 and acc["approx_rule_agrees"] == 82
assert acc["near_era"] == 69 and acc["n_2023"] == 13 and acc["F2_units"] == 78 and acc["max_label_date_F1"] <= CUTOFF_MAX
OUT["accept_1a"] = {k: (v if not isinstance(v, dict) else {str(kk): vv for kk, vv in v.items()}) for k, v in acc.items()}
# §13-2: b_turnover oranının kantilleri (Type-7) ve {:.4g} basımı profil §4 "hepsi" satırı (2 ≤ b ≤ 9, 64 arz)
ratios = sorted(Fraction(U[t]["ratio"]) for t in BREAKS if U[t]["b"] >= 2)
qs = [float(min(ratios))] + [float(q7(ratios, Fraction(p, 100))) for p in (5, 25, 50, 75, 95)] + [float(max(ratios))]
say("[1b] el değiştirme (2≤b≤9, n=64) min/p05/p25/p50/p75/p95/max = " + " / ".join(f"{v:.4g}" for v in qs))
OUT["accept_1b_turnover_quantiles"] = [f"{v:.4g}" for v in qs]
assert [f"{v:.4g}" for v in qs] == ["0.06236", "0.1134", "0.8542", "1.632", "2.228", "2.897", "3.219"]


# ============================================================ 2. Ürün karşılaştırıcısı: hücreler, merdiven, atomlar (SPEC_CEILING_PATH_V0 §3, §4, §7; SPEC_BREAK §5.1)
def valid(g, m):
    return 1 <= m <= (10 if g == "Z" else 9)


def build_cells(cutoff: str):
    """Faz 4 §3: seans tarihi < cutoff olan gözlemler; 99 arz; f3 şartı yok. Döner cells, max tarih."""
    cells = {("Z", m): [] for m in range(1, 11)} | {("B", m): [] for m in range(1, 10)}
    max_date = None
    for tk in ORDER:
        t = U[tk]["L"]
        if t >= 10:
            continue
        base = U[tk]["P"] if t == 0 else D(S[tk][t]["thb_raw_close"])
        g = "Z" if t == 0 else "B"
        for m in range(1, 11 - t):
            d = S[tk][t + m]["target_session_date"]
            if d >= cutoff:
                break
            G = float(D(S[tk][t + m]["thb_raw_close"]) / base - 1)
            cells[(g, m)].append((G, tk))
            max_date = d if max_date is None or d > max_date else max_date
    return {k: sorted(v) for k, v in cells.items()}, max_date


def ladder(g, m):
    other = "B" if g == "Z" else "Z"
    steps = [[(g, m)], [(other, m)] if valid(other, m) else []]
    for d in range(1, 10):
        for mm in (m - d, m + d):
            steps.append([(gg, mm) for gg in ("Z", "B") if valid(gg, mm)])
    return [s for s in steps if s]


def bounds(m):
    return float(Decimal("0.9") ** m - 1), float(Decimal("1.1") ** m - 1)


def pooled(cells, g, m, n_min=N_MIN):
    out, used = [], []
    for step in ladder(g, m):
        for key in step:
            used.append(key)
            out += cells[key]
        if len(out) >= n_min:
            break
    if len(out) < n_min:
        return None, used, True
    is_pooled = len(used) > 1
    if is_pooled:
        lo, hi = bounds(m)
        out = [(min(max(v, lo), hi), tk) for v, tk in out]
    return out, used, is_pooled


CELLS_CACHE: dict[str, tuple] = {}


def cells_at(cutoff):
    if cutoff not in CELLS_CACHE:
        CELLS_CACHE[cutoff] = build_cells(cutoff)
    return CELLS_CACHE[cutoff]


def product_atoms(k, cells):
    """Durum-2 atomları: h = b+1 (F1) ve b+2 (F2); (r, w, kaynak, v). Döner {head: (atoms | None, status)}."""
    u = U[k]
    L, b, P = u["L"], u["b"], u["P"]
    scale = 1.0 if L == 0 else float(u["closes"][L - 1] / P)
    g = "Z" if L == 0 else "B"
    out = {}
    for head, h in (("F1", b + 1), ("F2", b + 2)):
        if h > 10:
            out[head] = (None, "UNDEFINED")
            continue
        vals, used, is_pooled = pooled(cells, g, h - L)
        if vals is None:
            out[head] = (None, "INSUFFICIENT")
            continue
        w = 1.0 / len(vals)
        atoms = [((scale * (1 + v) - 1) if L else v, w, tk, v) for v, tk in vals]
        out[head] = (atoms, {"used": used, "pooled": is_pooled, "n": len(vals)})
    return out


def product_prob(atoms, thr: float, tol=1e-12):
    return sum(w for r, w, _, _ in atoms if r <= thr + tol)


def thresholds(k):
    u = U[k]
    cb, P = u["close_b"], u["P"]
    return {"F1": float(Lo(cb) / P - 1), "F2": float(Lo(Lo(cb)) / P - 1)}


# Faz 4 altın ledger'ıyla hücre sayısı paritesi (§7.2 (vi), §13-6)
g4 = rd(G4_LEDGER)
par_ok, par_bad, par_date_bad = 0, [], []
for r in g4:
    if r["status"] != "OK":
        continue
    cells, mx = cells_at(r["prediction_date"])
    mine = {f"cells_n_{g}_{m}": len(cells[(g, m)]) for (g, m) in cells}
    if all(int(r[c]) == v for c, v in mine.items()):
        par_ok += 1
    else:
        par_bad.append(r["ticker"])
    if r["cells_max_session_date"] != mx:
        par_date_bad.append((r["ticker"], r["cells_max_session_date"], mx))
say(f"[1e] Faz 4 ledger'ı (sha {sha_file(G4_LEDGER)[:12]}) hücre sayısı paritesi: {par_ok}/{sum(1 for r in g4 if r['status']=='OK')} birebir; farklı: {par_bad}; max tarih farkı: {par_date_bad}")
assert par_ok == 87 and not par_bad and not par_date_bad
OUT["faz4_cell_parity"] = {"ok": par_ok, "bad": par_bad}


# ============================================================ 3. Ön işleme ve lojistik yol (§3, §4.1; SPEC_V1_6 §3, §4, §9; H11; N3)
class Prep:
    """Başlık başına, yalnız eğitim satırlarından: kırpma (Type-7 [p05, p95], ln ölçeğinde — özellik zaten ln) → z (ddof = 0)."""

    def __init__(self, tickers, feats, wins):
        self.feats, self.n = tuple(feats), len(tickers)
        raw = {t: {c: Fraction(U[t][c]) for c in feats} for t in tickers}
        self.lo, self.hi = {}, {}
        for c in wins:
            vals = [raw[t][c] for t in tickers]
            self.lo[c], self.hi[c] = q7(vals, Fraction(1, 20)), q7(vals, Fraction(19, 20))
        exact = {t: {c: (min(max(raw[t][c], self.lo[c]), self.hi[c]) if c in self.lo else raw[t][c]) for c in feats} for t in tickers}
        self.cols, self.mean, self.std, self.dropped = [], {}, {}, []
        for c in feats:
            if len({exact[t][c] for t in tickers}) <= 1:
                self.dropped.append(c)
                continue
            self.cols.append(c)
            vf = [exact[t][c] for t in tickers]
            mf = sum(vf, Fraction(0)) / self.n
            varf = sum(((v - mf) ** 2 for v in vf), Fraction(0)) / self.n
            self.mean[c] = mf
            with localcontext(CTX60):
                self.std[c] = (Decimal(varf.numerator) / Decimal(varf.denominator)).sqrt()
        self.cols = tuple(self.cols)
        self.insufficient = not self.cols
        self.Z = {t: self._z(exact[t]) for t in tickers} if not self.insufficient else {}

    def _z(self, ex):
        out = []
        with localcontext(CTX60):
            for c in self.cols:
                d = ex[c] - self.mean[c]
                out.append(float((Decimal(d.numerator) / Decimal(d.denominator)) / self.std[c]))
        return out

    def transform(self, t):
        ex, clipped = {}, []
        for c in self.feats:
            v = Fraction(U[t][c])
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
                "dropped": list(self.dropped), "n_train": self.n}


def sk_fit(C, X, y):
    est = LogisticRegression(C=C, **LOGIT_KW)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        est.fit(X, y)
    conv = [w for w in caught if issubclass(w.category, ConvergenceWarning)]
    return est, bool(conv)


def p1(est, z):
    proba = est.predict_proba(np.array(z, dtype=np.float64).reshape(1, -1))[0]
    return float(proba[list(est.classes_).index(1)])


def newton_logit(X, y, C, iters=200):
    """Bağımsız çözüm: min 0.5‖β‖² + C Σ log(1 + exp(−s_i (b + βᵀx_i))) (sabit cezasız; sklearn amacı)."""
    n, p = X.shape
    A = np.hstack([np.ones((n, 1)), X])
    w = np.zeros(p + 1)
    pen = np.concatenate([[0.0], np.ones(p)])
    for _ in range(iters):
        mu = 1.0 / (1.0 + np.exp(-(A @ w)))
        g = C * A.T @ (mu - y) + pen * w
        H = C * (A.T * (mu * (1 - mu))) @ A + np.diag(pen)
        step = np.linalg.solve(H, g)
        w -= step
        if np.max(np.abs(step)) < 1e-14:
            break
    return w[0], w[1:]


def fit_head(order, feats, wins, Y, test=None):
    """Bir başlık (F1 ya da F2) için V1.6 Logit yolu: iç arz-bırak LOOCV (ön işleme her bölmede yeniden) → C → nihai fit → p_test."""
    n = len(order)
    y_seq = [Y[t] for t in order]
    n1, n0 = sum(y_seq), n - sum(y_seq)
    res = {"n": n, "events": n1, "nonevents": n0, "inner_fold_n": 0, "scores": {}, "score_status": {}, "columns": [], "C": None,
           "tuning_status": "TUNING_NOT_APPLICABLE", "p": None, "intercept": None, "coef": None, "final_attempts": [], "clipped": None,
           "prep": None, "status": None, "X": None, "y": None}
    if n < MIN_ROWS or n1 < MIN_EV or n0 < MIN_NE:
        return {**res, "status": "INSUFFICIENT_TRAINING_HISTORY"}
    final = Prep(order, feats, wins)
    res["prep"] = final.params()
    tz = None
    if test is not None and not final.insufficient:
        tz, clipped = final.transform(test)
        res["clipped"] = clipped
    if n0 == 0 or n1 == 0:
        return {**res, "status": "MODEL_NOT_FIT_SINGLE_CLASS"}
    if min(n0, n1) < 2:
        selected, tuning = FALLBACK_C, "TUNING_SKIPPED_MINORITY_COUNT_LT_2"
        ranked, inner_n = [selected, ZERO], 0
    else:
        folds = []
        for held in order:
            inner = [t for t in order if t != held]
            pr = Prep(inner, feats, wins)
            folds.append((held, inner, pr, None if pr.insufficient else pr.transform(held)[0]))
        for held, inner, pr, val in folds:
            if pr.insufficient:
                return {**res, "status": "INNER_INSUFFICIENT_FEATURE_VARIATION", "inner_fold_n": n}
            if len({Y[t] for t in inner}) < 2:
                return {**res, "status": "INNER_SINGLE_CLASS", "inner_fold_n": n}
        for C in GRID:
            terms, dropped = [], False
            for held, inner, pr, val in folds:
                if C == ZERO:
                    pp_ = sum(Y[t] for t in inner) / len(inner)
                else:
                    est, nc = sk_fit(C, np.array([pr.Z[t] for t in inner]), np.array([Y[t] for t in inner], dtype=np.float64))
                    if nc:
                        dropped = True
                        break
                    pp_ = p1(est, val)
                terms.append((pp_ - Y[held]) ** 2)
            res["score_status"][hp(C)] = "CANDIDATE_NOT_CONVERGED" if dropped else "SCORED"
            if not dropped:
                res["scores"][hp(C)] = sum(terms) / len(terms)
        scored = [(res["scores"][hp(C)], C) for C in GRID if res["score_status"][hp(C)] == "SCORED"]
        ranked = [c for _, c in sorted(scored)]   # (skor artan, C artan; ZERO = 0.0 en küçük)
        selected, tuning, inner_n = ranked[0], "TUNED_INNER_LOOCV", len(folds)
    res.update(tuning_status=tuning, inner_fold_n=inner_n)
    if final.insufficient:
        return {**res, "status": "INSUFFICIENT_FEATURE_VARIATION", "C": selected}
    res["columns"] = list(final.cols)
    X = np.array([final.Z[t] for t in order])
    y = np.array(y_seq, dtype=np.float64)
    res["X"], res["y"], res["tz"] = X, y, tz
    for C in ranked:
        if C == ZERO:
            p = n1 / n
            res["final_attempts"].append(["ZERO", "FIT_OK"])
            return {**res, "status": "FIT_OK", "C": ZERO, "p": p if test is not None else None, "intercept": math.log(p / (1 - p)),
                    "coef": {c: 0.0 for c in final.cols}}
        est, nc = sk_fit(C, X, y)
        if nc:
            res["final_attempts"].append([C, "NOT_CONVERGED"])
            continue
        res["final_attempts"].append([C, "FIT_OK"])
        return {**res, "status": "FIT_OK", "C": C, "p": p1(est, tz) if tz is not None else None, "intercept": float(est.intercept_[0]),
                "coef": {c: float(v) for c, v in zip(final.cols, est.coef_[0])}}
    return {**res, "status": "MODEL_NOT_FIT_DID_NOT_CONVERGE", "C": selected}


# ============================================================ 4. Fold planı ve koşu (§7.2; N2 formül aynen; N5; N6)
Y1 = {t: U[t]["y1"] for t in BREAKS}
Y2 = {t: U[t]["y2"] for t in F2_UNITS}


def plan(k):
    T = U[k]["E"]
    tr1 = [j for j in BREAKS if U[j]["y1"] is not None and U[j]["y1_date"] < T]
    # b = 9: F2 başlığı tanımsız (§1.2) → F2 eğitim kümesi kurulmaz (ilk koşuda kurmuştum; ledger'da n = 0, zero_F2 boş — Opus'un
    # okuması; şartname bu sütun için b = 9'da bir şey demiyor, iki okuma da hücreleri değiştirmez)
    tr2 = [] if U[k]["b"] == 9 else [j for j in F2_UNITS if U[j]["y2"] is not None and U[j]["y2_date"] < T]
    return T, tr1, tr2


def rate(tickers, Y):
    if not tickers:
        return None
    return float(Fraction(sum(Y[t] for t in tickers), len(tickers)))


def run_fold(k, variant):
    feats, wins = VARIANTS[variant]
    u = U[k]
    T, tr1, tr2 = plan(k)
    h1 = fit_head(tr1, feats, wins, Y1, test=k)
    if u["b"] == 9:
        h2 = {"status": "TARGET_UNDEFINED_F2", "n": len(tr2), "events": sum(Y2[t] for t in tr2), "prep": None, "C": None, "p": None, "coef": None,
              "intercept": None, "scores": {}, "score_status": {}, "final_attempts": [], "inner_fold_n": 0, "clipped": None}
    else:
        h2 = fit_head(tr2, feats, wins, Y2, test=k)
    cells, mx = cells_at(u["ftd"])
    pa = product_atoms(k, cells)
    thr = thresholds(k)
    prod = {}
    for head in ("F1", "F2"):
        atoms, st = pa[head]
        prod[head] = None if atoms is None else product_prob(atoms, thr[head])
    defined = [h for h in ("F1", "F2") if pa[h][1] != "UNDEFINED"]
    product_status = "OK" if all(pa[h][0] is not None for h in defined) else "POST_BREAK_INSUFFICIENT"
    same_class = [j for j in tr1 if U[j]["b_floor"] == u["b_floor"]]
    row = {
        "model_id": variant, "fold_id": f"{k}|{T}", "ticker": k, "first_trading_date": u["ftd"], "b": u["b"], "break_date": T,
        "training_n": len(tr1), "training_events": sum(Y1[t] for t in tr1), "training_nonevents": len(tr1) - sum(Y1[t] for t in tr1),
        # şartname sütunu tek: ledger'da iki başlığın etiket tarihlerinin maksimumu yazılı (F2'nin D_{b+2} tarihi F1'inkinden geç
        # olabilir; ikisi de < T). İlk koşuda yalnız F1'i almıştım (61 satırda fark; her ikisi de < T). F1'inki ayrıca saklanır.
        "training_max_label_date": max([U[t]["y1_date"] for t in tr1] + [U[t]["y2_date"] for t in tr2], default=""),
        "training_max_label_date_F1": max((U[t]["y1_date"] for t in tr1), default=""), "training_tickers_sha256": ihash(tr1),
        "training_tickers_sha256_sorted": ihash(sorted(tr1)), "training_n_F2": len(tr2),
        "training_max_label_date_F2": max((U[t]["y2_date"] for t in tr2), default=""),
        "selected_C_F1": None if h1["C"] is None else hp(h1["C"]), "selected_C_F2": None if h2["C"] is None else hp(h2["C"]),
        "columns": list(h1["columns"]) if h1["status"] == "FIT_OK" else None,
        "coef_F1": h1["coef"], "intercept_F1": h1["intercept"], "coef_F2": h2["coef"], "intercept_F2": h2["intercept"],
        "prep_F1": h1["prep"], "prep_F2": h2["prep"], "scores_F1": h1["scores"], "scores_F2": h2["scores"],
        "score_status_F1": h1["score_status"], "score_status_F2": h2["score_status"],
        "final_attempts_F1": h1["final_attempts"], "final_attempts_F2": h2["final_attempts"],
        "inner_fold_n_F1": h1["inner_fold_n"], "inner_fold_n_F2": h2["inner_fold_n"],
        "status_F1": h1["status"], "status_F2": h2["status"], "n_F2": h2["n"], "events_F2": h2["events"],
        "test_b_floor": u["b_floor"], "test_b_turnover_ratio": str(u["ratio"]), "test_b_turnover": u["b_turnover"],
        "test_b_turnover_clipped": None if h1["clipped"] is None else int("b_turnover" in h1["clipped"]),
        "test_floor_lock_allday": u["lock"], "test_half_day": u["half"],
        "p_F1": h1["p"], "p_F2": h2["p"], "zero_F1": rate(tr1, Y1), "zero_F2": rate(tr2, Y2), "by_type_F1": rate(same_class, Y1),
        "product_F1": prod["F1"], "product_F2": prod["F2"], "product_status": product_status, "cells_max_session_date": mx,
        "product_cells": {h: (pa[h][1] if isinstance(pa[h][1], dict) else pa[h][1]) for h in ("F1", "F2")},
        "structural_zero_D10": int(u["sz"]["impossible"]), "realized_F1": u["y1"], "realized_F2": u["y2"], "status": h1["status"],
        "near": u["ftd"] >= NEAR_START, "group_Z": u["group_Z"], "thr": thr,
    }
    # Newton paritesi (yalnız ana model, FIT_OK, C ≠ ZERO): bağımsız çözümle |Δp| ve |Δβ|
    if variant == MODEL and h1["status"] == "FIT_OK" and h1["C"] != ZERO:
        b0, beta = newton_logit(h1["X"], h1["y"], h1["C"])
        pn = 1 / (1 + math.exp(-(b0 + float(np.dot(beta, h1["tz"])))))
        row["newton"] = {"dp": abs(pn - h1["p"]), "dcoef": float(np.max(np.abs(beta - np.array([h1["coef"][c] for c in h1["columns"]])))),
                         "dint": abs(b0 - h1["intercept"])}
    return row


def _task(args):
    k, variant = args
    return run_fold(k, variant)


def run_variant(variant, workers):
    t0 = time.time()
    ctx = multiprocessing.get_context("fork")
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as ex:
        rows = list(ex.map(_task, [(k, variant) for k in BREAKS]))
    say(f"[koşu] {variant}: {len(rows)} fold, {time.time() - t0:.1f} sn; F1 durumları {dict(Counter(r['status'] for r in rows))}; "
        f"F2 {dict(Counter(r['status_F2'] for r in rows))}; seçilen C F1 {dict(Counter(r['selected_C_F1'] for r in rows if r['status']=='FIT_OK'))}; "
        f"F2 {dict(Counter(r['selected_C_F2'] for r in rows if r['status_F2']=='FIT_OK'))}; ürün yetersiz {sum(1 for r in rows if r['product_status']!='OK')}")
    return rows


# ============================================================ 5. Ledger karşılaştırması (1d, 1e, 1h)
NUM_COLS = {"coef_floor_F1": ("coef_F1", "b_floor"), "coef_turn_F1": ("coef_F1", "b_turnover"), "intercept_F1": ("intercept_F1", None),
            "coef_floor_F2": ("coef_F2", "b_floor"), "coef_turn_F2": ("coef_F2", "b_turnover"), "intercept_F2": ("intercept_F2", None),
            "clip_p05": ("prep_F1", "winsor.b_turnover.p05"), "clip_p95": ("prep_F1", "winsor.b_turnover.p95"),
            "mean_floor": ("prep_F1", "mean.b_floor"), "std_floor": ("prep_F1", "std.b_floor"), "mean_turn": ("prep_F1", "mean.b_turnover"),
            "std_turn": ("prep_F1", "std.b_turnover"), "p_F1": ("p_F1", None), "p_F2": ("p_F2", None), "product_F1": ("product_F1", None),
            "product_F2": ("product_F2", None)}
EXACT_COLS = ["fold_id", "ticker", "first_trading_date", "b", "break_date", "training_n", "training_events", "training_nonevents",
              "training_max_label_date", "selected_C_F1", "selected_C_F2", "test_b_floor", "test_b_turnover_clipped",
              "test_floor_lock_allday", "test_half_day", "product_status", "cells_max_session_date", "structural_zero_D10",
              "realized_F1", "realized_F2", "status"]


def dig(obj, path):
    if obj is None:
        return None
    for part in path.split("."):
        if obj is None or part not in obj:
            return None
        obj = obj[part]
    return obj


def mine_value(row, col):
    src, sub = NUM_COLS[col]
    base = row[src]
    if base is None:
        return None
    if sub is None:
        return base
    if "." in sub:
        return dig(base, sub)
    return base.get(sub) if isinstance(base, dict) else None


def to_f(s):
    return None if s in ("", None) else float(s)


def compare_ledger(variant, rows):
    gold = {r["ticker"]: r for r in rd(LEDGER_DIR / f"{variant}_fold_ledger.csv")}
    assert set(gold) == set(r["ticker"] for r in rows) and len(gold) == 82
    feats = VARIANTS[variant][0]
    maxd: dict[str, float] = {}
    mism: dict[str, list] = defaultdict(list)
    sha_mode = Counter()
    for r in rows:
        g = gold[r["ticker"]]
        for c in EXACT_COLS:
            mv = r[c]
            mv = "" if mv is None else str(mv)
            if mv != g[c]:
                mism[c].append((r["ticker"], mv, g[c]))
        # kimlik sha: plan sırası mı, sıralı mı
        if r["training_tickers_sha256"] == g["training_tickers_sha256"]:
            sha_mode["plan_order"] += 1
        elif r["training_tickers_sha256_sorted"] == g["training_tickers_sha256"]:
            sha_mode["sorted"] += 1
        else:
            mism["training_tickers_sha256"].append((r["ticker"], r["training_tickers_sha256"][:12], g["training_tickers_sha256"][:12]))
        # columns / dropped
        gc = json.loads(g["columns"]) if g["columns"] else None
        if (r["columns"] or None) != gc:
            mism["columns"].append((r["ticker"], r["columns"], gc))
        gd = json.loads(g["dropped"]) if g["dropped"] else None
        md = (r["prep_F1"] or {}).get("dropped") if r["prep_F1"] else None
        if (md or None) != (gd or None):
            mism["dropped"].append((r["ticker"], md, gd))
        # bit-eşit Fraction oranları
        for c in ("zero_F1", "zero_F2", "by_type_F1"):
            gv, mv = to_f(g[c]), r[c]
            if (gv is None) != (mv is None) or (gv is not None and gv != mv):
                mism[c].append((r["ticker"], mv, gv))
        # Decimal oran
        if D(g["test_b_turnover_ratio"]) != D(r["test_b_turnover_ratio"]):
            d = abs(float(D(g["test_b_turnover_ratio"]) - D(r["test_b_turnover_ratio"])))
            maxd["test_b_turnover_ratio"] = max(maxd.get("test_b_turnover_ratio", 0.0), d)
            if d > TOL:
                mism["test_b_turnover_ratio"].append((r["ticker"], r["test_b_turnover_ratio"][:20], g["test_b_turnover_ratio"][:20]))
        else:
            maxd.setdefault("test_b_turnover_ratio", 0.0)
        # sayısal sütunlar
        for c in NUM_COLS:
            if ("floor" in c and "b_floor" not in feats) or ("turn" in c and "b_turnover" not in feats) or (c.startswith("clip") and "b_turnover" not in feats):
                continue
            gv, mv = to_f(g[c]), mine_value(r, c)
            if gv is None and mv is None:
                maxd.setdefault(c, 0.0)
                continue
            if (gv is None) != (mv is None):
                mism[c].append((r["ticker"], mv, gv))
                continue
            d = abs(gv - mv)
            maxd[c] = max(maxd.get(c, 0.0), d)
            if d > TOL:
                mism[c].append((r["ticker"], mv, gv))
        # iç tablolar: durum, n, olay, skorlar, aday durumları, nihai denemeler, F2 ön işlemesi, grup katsayıları
        for head, st_key, prep_key, coef_key, int_key in (("F1", "status_F1", "prep_F1", "coef_F1", "intercept_F1"), ("F2", "status_F2", "prep_F2", "coef_F2", "intercept_F2")):
            it = json.loads(g[f"inner_table_{head}"])
            if it.get("status") != r[st_key]:
                mism[f"inner_{head}.status"].append((r["ticker"], r[st_key], it.get("status")))
            n_mine = r["training_n"] if head == "F1" else r["n_F2"]
            ev_mine = r["training_events"] if head == "F1" else r["events_F2"]
            if it.get("n") != n_mine or it.get("events") != ev_mine:
                mism[f"inner_{head}.n_events"].append((r["ticker"], (n_mine, ev_mine), (it.get("n"), it.get("events"))))
            if it.get("status") != "FIT_OK":
                continue
            for C, sc in it.get("scores", {}).items():
                mv = r[f"scores_{head}"].get(C)
                if sc is None:          # yakınsamayan aday: skor yok (ledger'da null); durumu score_status karşılaştırmasında
                    if r[f"score_status_{head}"].get(C) != "CANDIDATE_NOT_CONVERGED":
                        mism[f"inner_{head}.scores"].append((r["ticker"], C, mv, None))
                    continue
                if mv is None:
                    mism[f"inner_{head}.scores"].append((r["ticker"], C, "missing", sc))
                    continue
                d = abs(sc - mv)
                maxd[f"inner_{head}.scores"] = max(maxd.get(f"inner_{head}.scores", 0.0), d)
                if d > TOL:
                    mism[f"inner_{head}.scores"].append((r["ticker"], C, mv, sc))
            if it.get("score_status") != r[f"score_status_{head}"]:
                mism[f"inner_{head}.score_status"].append((r["ticker"], r[f"score_status_{head}"], it.get("score_status")))
            fa_g = [[("ZERO" if a == "ZERO" else float(a)), s] for a, s in it.get("final_attempts", [])]
            fa_m = [[("ZERO" if a == "ZERO" else float(a)), s] for a, s in r[f"final_attempts_{head}"]]
            if fa_g != fa_m:
                mism[f"inner_{head}.final_attempts"].append((r["ticker"], fa_m, fa_g))
            if it.get("inner_fold_n") != r[f"inner_fold_n_{head}"]:
                mism[f"inner_{head}.inner_fold_n"].append((r["ticker"], r[f"inner_fold_n_{head}"], it.get("inner_fold_n")))
            pr = it.get("prep", {})
            mp = r[prep_key] or {}
            for c in feats:
                for key in ("mean", "std"):
                    gv, mv = (pr.get(key) or {}).get(c), (mp.get(key) or {}).get(c)
                    if gv is None and mv is None:
                        continue
                    if (gv is None) != (mv is None):
                        mism[f"inner_{head}.prep.{key}"].append((r["ticker"], c, mv, gv))
                        continue
                    d = abs(gv - mv)
                    maxd[f"inner_{head}.prep.{key}"] = max(maxd.get(f"inner_{head}.prep.{key}", 0.0), d)
                    if d > TOL:
                        mism[f"inner_{head}.prep.{key}"].append((r["ticker"], c, mv, gv))
                gv, mv = (it.get("coef") or {}).get(c), (r[coef_key] or {}).get(c)
                if gv is not None or mv is not None:
                    if (gv is None) != (mv is None):
                        mism[f"inner_{head}.coef"].append((r["ticker"], c, mv, gv))
                    else:
                        d = abs(gv - mv)
                        maxd[f"inner_{head}.coef"] = max(maxd.get(f"inner_{head}.coef", 0.0), d)
                        if d > TOL:
                            mism[f"inner_{head}.coef"].append((r["ticker"], c, mv, gv))
            for c, wv in (pr.get("winsor") or {}).items():
                for key in ("p05", "p95"):
                    gv, mv = wv.get(key), ((mp.get("winsor") or {}).get(c) or {}).get(key)
                    if mv is None:
                        mism[f"inner_{head}.prep.winsor"].append((r["ticker"], c, key, "missing"))
                        continue
                    d = abs(gv - mv)
                    maxd[f"inner_{head}.prep.winsor"] = max(maxd.get(f"inner_{head}.prep.winsor", 0.0), d)
                    if d > TOL:
                        mism[f"inner_{head}.prep.winsor"].append((r["ticker"], c, key, mv, gv))
            if it.get("intercept") is not None:
                d = abs(it["intercept"] - r[int_key])
                maxd[f"inner_{head}.intercept"] = max(maxd.get(f"inner_{head}.intercept", 0.0), d)
                if d > TOL:
                    mism[f"inner_{head}.intercept"].append((r["ticker"], r[int_key], it["intercept"]))
    ok = not mism
    say(f"[ledger] {variant}: {'EŞLEŞTİ' if ok else 'UYUŞMAZLIK'}; kimlik sha kipi {dict(sha_mode)}; maks |Δ| (sayısal sütunlar, 1e-9 eşiği):")
    for c in sorted(maxd):
        say(f"    {c:<28} max|Δ| = {maxd[c]:.3e}")
    for c, lst in mism.items():
        say(f"    UYUŞMAZLIK {c}: {len(lst)} satır; ilk 3: {lst[:3]}")
    return {"ok": ok, "max_abs_delta": maxd, "mismatches": {c: lst[:10] for c, lst in mism.items()}, "n_mismatch_cols": len(mism),
            "sha_mode": dict(sha_mode), "ledger_sha256": sha_file(LEDGER_DIR / f"{variant}_fold_ledger.csv")}


# ============================================================ 6. Hücreler (§5.2; C7) ve §6 kuralları
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


def paired(rows, a_key, b_key, y_key, subset=None, a_status="status", a_fit="FIT_OK"):
    diffs, months, A, B, tk = [], [], [], [], []
    for r in rows:
        if subset is not None and not subset(r):
            continue
        if a_status is not None and r[a_status] != a_fit:
            continue
        pa, pb, y = r[a_key], r[b_key], r[y_key]
        if pa is None or pb is None or y is None:
            continue
        la, lb = (pa - y) ** 2, (pb - y) ** 2
        diffs.append(la - lb)
        months.append(r["first_trading_date"][:7])
        A.append(la)
        B.append(lb)
        tk.append(r["ticker"])
    if not diffs:
        return {"n": 0}
    ci = list(boot(diffs, months)) if len(diffs) >= 10 and len(set(months)) >= 6 else None
    return {"n": len(diffs), "n_months": len(set(months)), "a_metric": sum(A) / len(A), "b_metric": sum(B) / len(B), "mean": sum(diffs) / len(diffs),
            "ci95": ci, "model_better_n": sum(1 for d in diffs if d < 0), "rule_better_n": sum(1 for d in diffs if d > 0),
            "tie_n": sum(1 for d in diffs if d == 0), "tie_n_1e12": sum(1 for d in diffs if abs(d) <= 1e-12),
            "events": sum(1 for r in rows if r["ticker"] in tk and r[y_key] == 1), "diffs": dict(zip(tk, diffs)), "months": months}


def calib(rows, subset):
    ps = [(r["p_F1"], r["realized_F1"]) for r in rows if r["status"] == "FIT_OK" and r["realized_F1"] is not None and subset(r)]
    if not ps:
        return {"n": 0}
    return {"n": len(ps), "mean_p": sum(p for p, _ in ps) / len(ps), "observed": sum(y for _, y in ps) / len(ps)}


def all_cells(rows):
    near = lambda r: r["near"]
    old = lambda r: not r["near"]
    every = lambda r: True
    C = {
        "F1_product": paired(rows, "p_F1", "product_F1", "realized_F1", near),
        "F1_zero": paired(rows, "p_F1", "zero_F1", "realized_F1", near),
        "F1_by_type": paired(rows, "p_F1", "by_type_F1", "realized_F1", near),
        "F2_product": paired(rows, "p_F2", "product_F2", "realized_F2", near, a_status="status_F2"),
        "F2_zero": paired(rows, "p_F2", "zero_F2", "realized_F2", near, a_status="status_F2"),
    }
    prim = set(C["F1_product"].get("diffs", {}))
    C["info_product_zero_F1"] = paired(rows, "product_F1", "zero_F1", "realized_F1", lambda r: r["near"] and r["ticker"] in prim, a_status=None)
    X = {}
    for name, sub in (("2023", old), ("all", every), ("b1", lambda r: r["b"] == 1), ("b2_9", lambda r: r["b"] >= 2)):
        X[f"F1_product|{name}"] = paired(rows, "p_F1", "product_F1", "realized_F1", sub)
        X[f"F1_zero|{name}"] = paired(rows, "p_F1", "zero_F1", "realized_F1", sub)
        if name in ("2023", "all"):
            X[f"F2_product|{name}"] = paired(rows, "p_F2", "product_F2", "realized_F2", sub, a_status="status_F2")
            X[f"F2_zero|{name}"] = paired(rows, "p_F2", "zero_F2", "realized_F2", sub, a_status="status_F2")
    K = {"near": calib(rows, near), "2023": calib(rows, old), "all": calib(rows, every),
         "all_floor1": calib(rows, lambda r: r["test_b_floor"] == 1), "all_floor0": calib(rows, lambda r: r["test_b_floor"] == 0)}
    for yr in ("2023", "2024", "2025", "2026"):
        K[f"year_{yr}"] = calib(rows, lambda r, yr=yr: r["first_trading_date"][:4] == yr)
    return C, X, K


def fmt_cell(c):
    if c.get("n", 0) == 0:
        return "n = 0"
    ci = c["ci95"]
    cis = f"[{ci[0]:+.4f}, {ci[1]:+.4f}]" if ci else "—"
    return (f"n {c['n']} ({c['n_months']} ay) model {c['a_metric']:.4f} karş {c['b_metric']:.4f} fark {c['mean']:+.4f} {cis} "
            f"iyi/kötü/eşit {c['model_better_n']}/{c['rule_better_n']}/{c['tie_n']} (≤1e-12: {c['tie_n_1e12']})")


def strip_cell(c):
    return {k: v for k, v in c.items() if k not in ("diffs", "months")}


# §6 satırları (aynen; OPERATIONAL_RULES_FAZ8 kalıbı MODELS.md'deki kural metninden): [alt, üst] kapalı; "Aralık 0'ı" kesin kısmı
EXPECT = [("F1_product", -0.080, (-0.140, -0.020), "dışlaması olası"), ("F1_zero", -0.040, (-0.080, 0.000), "dışlaması olası, garanti değil (alt uç ≤ 0)"),
          ("F1_by_type", -0.005, (-0.025, 0.015), "içerir"), ("F2_product", -0.050, (-0.110, 0.010), "içerir ya da negatif dışlar"),
          ("F2_zero", -0.030, (-0.070, 0.010), "içerir"), ("info_product_zero_F1", 0.040, (0.000, 0.090), "pozitif dışlar ya da içerir (alt uç ≥ 0)")]


def certain_part(phrase, ci):
    lo, hi = ci
    if phrase.startswith("dışlaması olası"):
        return lo <= 0
    if phrase == "içerir":
        return lo <= 0 <= hi
    if phrase == "içerir ya da negatif dışlar":
        return lo <= 0
    if phrase.startswith("pozitif dışlar ya da içerir"):
        return hi >= 0
    raise AssertionError(phrase)


def judge6(C, final, rows):
    out = []
    for key, pt, (lo, hi), phrase in EXPECT:
        c = C[key]
        d = c["mean"]
        if d < lo:
            pos, verdict = "altında — beklentiden çok iyi", "tutmadı (daha iyi)"
        elif d > hi:
            pos, verdict = "üstünde", "tutmadı (daha kötü)"
        else:
            pos = "aralık içinde"
            verdict = ("tuttu" if certain_part(phrase, c["ci95"]) else "tutmadı (aralık)") if c["ci95"] else "tutmadı (aralık yok)"
        out.append((key, pos, verdict))
    k = C["F1_zero"]
    cal = calib(rows, lambda r: r["near"])
    dcal = cal["mean_p"] - cal["observed"]
    out.append(("calibration", f"{dcal:+.4f}", "tuttu" if abs(dcal) <= 0.06 else ("tutmadı (model yüksek)" if dcal > 0 else "tutmadı (model düşük)")))
    fit_ok = [r for r in rows if r["status"] == "FIT_OK" and r["selected_C_F1"] != "ZERO" and "b_floor" in (r["columns"] or [])]
    share_floor = sum(1 for r in fit_ok if r["coef_F1"]["b_floor"] > 0) / len(fit_ok)
    part1, part2 = final["F1"]["coef"]["b_floor"] > 0, share_floor >= 0.9
    out.append(("beta_floor", f"nihai {final['F1']['coef']['b_floor']:+.4f}; fold payı {sum(1 for r in fit_ok if r['coef_F1']['b_floor'] > 0)}/{len(fit_ok)}",
                "tuttu" if part1 and part2 else ("tutmadı" if not part1 and not part2 else "kısmen")))
    bt = final["F1"]["coef"]["b_turnover"]
    out.append(("beta_turn", f"nihai {bt:+.4f}; fold payı < 0: {sum(1 for r in fit_ok if r['coef_F1']['b_turnover'] < 0)}/{len(fit_ok)}",
                "tuttu" if bt < 0 else ("tutmadı (> 0)" if bt > 0 else "tutmadı (= 0)")))
    Cf = final["F1"]["C"]
    out.append(("C_final", hp(Cf), "tuttu" if Cf != ZERO and 0.1 <= Cf <= 1 else ("tutmadı (ZERO)" if Cf == ZERO else "tutmadı")))
    near_ok = [r for r in rows if r["near"] and r["status"] == "FIT_OK"]
    zshare = sum(1 for r in near_ok if r["selected_C_F1"] == "ZERO") / len(near_ok)
    out.append(("C_folds_zero_share", f"{zshare:.0%}", "tuttu" if zshare <= 0.20 else "tutmadı"))
    n1, n2 = C["F1_product"]["n"], C["F2_product"]["n"]
    out.append(("n_F1", str(n1), "tuttu" if 60 <= n1 <= 69 else ("tutmadı (az)" if n1 < 60 else "tutmadı (çok)")))
    out.append(("n_F2", str(n2), "tuttu" if 55 <= n2 <= 65 else ("tutmadı (az)" if n2 < 55 else "tutmadı (çok)")))
    prim = C["F1_product"]
    too_good = {"primary_lt_-0.160": prim["mean"] < -0.160, "primary_hi_lt_-0.080": bool(prim["ci95"]) and prim["ci95"][1] < -0.080,
                "zero_lt_-0.090": k["mean"] < -0.090}
    fail = {"a_indistinguishable": (k["ci95"] is None) or (k["ci95"][0] <= 0 <= k["ci95"][1]),
            "b_harms": bool(prim["ci95"]) and prim["ci95"][0] > 0,
            "c_no_info": Cf == ZERO or zshare >= 0.5,
            "d_level_shift": n1 >= 30 and abs(dcal) > 0.15}
    k1 = bool(prim["ci95"]) and prim["ci95"][1] < 0 and bool(k["ci95"]) and k["ci95"][1] < 0
    return out, too_good, fail, k1


# ============================================================ 7. Nihai fit (§4.4; önizleme karşılaştırması 1g)
def final_fits(variant):
    feats, wins = VARIANTS[variant]
    f1 = fit_head(BREAKS, feats, wins, Y1)
    f2 = fit_head(F2_UNITS, feats, wins, Y2)
    return {"F1": f1, "F2": f2}


def compare_preview(final):
    pv = json.load(open(LEDGER_DIR / f"{MODEL}_final_fit_preview.json", encoding="utf-8"))
    pz = json.load(open(LEDGER_DIR / f"{MODEL}@ZERO_final_fit_preview.json", encoding="utf-8"))
    res, maxd = {}, {}
    for head in ("F1", "F2"):
        h = pv["horizons"][head]["p_floor"]
        f = final[head]
        res[f"{head}.C"] = (hp(f["C"]), hp(h["C"]) if h["C"] != "ZERO" else "ZERO")
        for i, c in enumerate(h["columns"]):
            maxd[f"{head}.coef.{c}"] = abs(h["coef"][i] - f["coef"][c])
        maxd[f"{head}.intercept"] = abs(h["intercept"] - f["intercept"])
        for C, sc in h["inner_loocv_brier"].items():
            maxd[f"{head}.inner_brier"] = max(maxd.get(f"{head}.inner_brier", 0.0), abs(sc - f["scores"][C]))
        pp = pv["preprocessing"][head]
        for key in ("mean", "std"):
            for c, v in pp[key].items():
                maxd[f"{head}.prep.{key}"] = max(maxd.get(f"{head}.prep.{key}", 0.0), abs(v - f["prep"][key][c]))
        for c, wv in pp["winsor"].items():
            for key in ("p05", "p95"):
                maxd[f"{head}.prep.winsor"] = max(maxd.get(f"{head}.prep.winsor", 0.0), abs(wv[key] - f["prep"]["winsor"][c][key]))
        res[f"{head}.n_class"] = ((f["nonevents"], f["events"]), (h["n_class_0"], h["n_class_1"]))
        res[f"{head}.inner_folds"] = (f["inner_fold_n"], h["inner_loocv_folds"])
        res[f"{head}.attempts"] = (f["final_attempts"], h["final_fit_attempts"])
        res[f"{head}.zero"] = (rate(BREAKS if head == "F1" else F2_UNITS, Y1 if head == "F1" else Y2), pz["horizons"][head]["p_floor"]["value"], pv["comparators"]["zero"][head])
    bt = {c: [sum(U[t]["y1"] for t in BREAKS if U[t]["b_floor"] == c), sum(1 for t in BREAKS if U[t]["b_floor"] == c)] for c in (0, 1)}
    res["by_type"] = ({str(c): {"events": e, "n": n, "rate": float(Fraction(e, n))} for c, (e, n) in bt.items()}, pv["comparators"]["by_type_F1"])
    res["tickers_sha256"] = (ihash(BREAKS), pv["training"]["tickers_sha256"], ihash(F2_UNITS), pv["training"]["tickers_sha256_F2"])
    res["cutoff_date"] = (acc["max_label_date_F1"], pv["training"]["cutoff_date"])
    res["feature_ranges"] = (acc["turnover_range"], [pv["feature_ranges"]["b_turnover"]["min"], pv["feature_ranges"]["b_turnover"]["max"]])
    # break_fields_sha256 (82 × (ticker, b, close_b, lower_b, volume_b) ham metin) — biçim şartnamede açık değil; birkaç aday
    cands = {}
    for name, fn in (("csv", lambda u: ",".join([u["ticker"], str(u["b"]), str(u["close_b"]), str(u["lower_b"]), str(u["vol_b"])])),
                     ("pipe", lambda u: "|".join([u["ticker"], str(u["b"]), str(u["close_b"]), str(u["lower_b"]), str(u["vol_b"])])),
                     ("tab", lambda u: "\t".join([u["ticker"], str(u["b"]), str(u["close_b"]), str(u["lower_b"]), str(u["vol_b"])]))):
        for raw in (True,):
            items = [fn({**U[t], "close_b": S[t][U[t]["b"]]["thb_raw_close"], "lower_b": S[t][U[t]["b"]]["thm_raw_lower_limit"], "vol_b": S[t][U[t]["b"]]["thb_raw_volume"]}) for t in BREAKS]
            cands[name] = ihash(items)
            cands[name + "_json"] = hashlib.sha256(json.dumps([[t, U[t]["b"], S[t][U[t]["b"]]["thb_raw_close"], S[t][U[t]["b"]]["thm_raw_lower_limit"], S[t][U[t]["b"]]["thb_raw_volume"]] for t in BREAKS], separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    res["break_fields_sha256"] = ({k: v[:12] for k, v in cands.items()}, pv["training"]["break_fields_sha256"][:12],
                                  [k for k, v in cands.items() if v == pv["training"]["break_fields_sha256"]])
    ok = all(a == b for a, b in (res["F1.C"], res["F2.C"])) and max(maxd.values()) <= TOL and res["F1.zero"][0] == res["F1.zero"][1] == res["F1.zero"][2] \
        and res["F2.zero"][0] == res["F2.zero"][1] == res["F2.zero"][2] and res["by_type"][0] == {k: {"events": v["events"], "n": v["n"], "rate": v["rate"]} for k, v in res["by_type"][1].items()} \
        and res["tickers_sha256"][0] == res["tickers_sha256"][1] and res["tickers_sha256"][2] == res["tickers_sha256"][3]
    say(f"[1g] nihai fit önizlemesi: {'EŞLEŞTİ' if ok else 'UYUŞMAZLIK'}; C F1 {res['F1.C']} F2 {res['F2.C']}; sınıf sayıları {res['F1.n_class']} {res['F2.n_class']}; "
        f"iç fold {res['F1.inner_folds']} {res['F2.inner_folds']}; @ZERO F1 {res['F1.zero']} F2 {res['F2.zero']}; by_type {res['by_type'][0]}")
    say("[1g] maks |Δ|: " + "; ".join(f"{k} {v:.2e}" for k, v in sorted(maxd.items())))
    say(f"[1g] tickers_sha256 F1 eşit {res['tickers_sha256'][0] == res['tickers_sha256'][1]}, F2 eşit {res['tickers_sha256'][2] == res['tickers_sha256'][3]}; "
        f"kesim {res['cutoff_date']}; feature_ranges {res['feature_ranges']}; break_fields_sha256 adayları {res['break_fields_sha256']}")
    return {"ok": ok, "max_abs_delta": maxd, "details": {k: (v if not isinstance(v, tuple) else list(v)) for k, v in res.items()}}


# ============================================================ 8. Günlük ve MODELS.md ile hücre karşılaştırması
def compare_cells(C, X, K):
    log_rows = [json.loads(l) for l in open(LOG_PATH, encoding="utf-8") if l.strip()]
    log_rows = [r for r in log_rows if r.get("model_id") == MODEL and r.get("kind") == "backtest"]
    assert len(log_rows) == 1, len(log_rows)
    ne = log_rows[0]["near_era"]
    maxd, mism = {}, []
    for key in ("F1_product", "F1_zero", "F1_by_type", "F2_product", "F2_zero", "info_product_zero_F1"):
        g, m = ne[key], C[key]
        for f in ("n", "n_months", "model_better_n", "rule_better_n", "tie_n", "tie_n_1e12"):
            if g[f] != m[f]:
                mism.append((key, f, m[f], g[f]))
        for f in ("a_metric", "b_metric", "mean"):
            d = abs(g[f] - m[f])
            maxd[f"{key}.{f}"] = d
            if d > TOL:
                mism.append((key, f, m[f], g[f]))
        for i in (0, 1):
            d = abs(g["ci95"][i] - m["ci95"][i])
            maxd[f"{key}.ci95[{i}]"] = d
            if d > TOL:
                mism.append((key, f"ci95[{i}]", m["ci95"][i], g["ci95"][i]))
    met = log_rows[0]["metrics"]
    for head in ("F1", "F2"):
        kk = K["near"] if head == "F1" else None
        if head == "F1":
            for f, mv in (("brier", C["F1_product"]["a_metric"]), ("mean_p", kk["mean_p"]), ("observed", kk["observed"])):
                d = abs(met["F1_near"][f] - mv)
                maxd[f"metrics.F1_near.{f}"] = d
                if d > TOL:
                    mism.append(("metrics.F1_near", f, mv, met["F1_near"][f]))
    # MODELS.md keşif ve kalibrasyon tabloları (4 ondalık gösterim)
    md = MODELS_MD.read_text(encoding="utf-8").split("## Faz 8")[1].split("## Faz 7C")[0]
    rend = []
    for key, label_md, fset in (("F1_product|b1", "F1 − `PRODUCT_BREAK_FLOOR` | b = 1", None), ("F1_zero|b1", "F1 − `break_floor_v0@ZERO` | b = 1", None),
                                ("F1_product|b2_9", "F1 − `PRODUCT_BREAK_FLOOR` | 2 ≤ b ≤ 9", None), ("F1_zero|b2_9", "F1 − `break_floor_v0@ZERO` | 2 ≤ b ≤ 9", None)):
        line = [l for l in md.splitlines() if l.startswith("| " + label_md)]
        assert len(line) == 1, label_md
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line[0].strip("|"))]      # kaçışlı \| hücre ayracı değil
        m = X[key]
        got = [f"{m['n']} ({m['n_months']})", f"{m['a_metric']:.4f}", f"{m['b_metric']:.4f}", f"{m['mean']:.4f}".replace("-0.", "-0."),
               f"[{m['ci95'][0]:+.4f}, {m['ci95'][1]:+.4f}]".replace("+-", "-") if m["ci95"] else "—",
               f"{m['model_better_n']} / {m['rule_better_n']} / {m['tie_n']} (|fark| ≤ 1e-12: {m['tie_n_1e12']})"]
        exp = cells[2:8]
        exp = [e.replace("\\|", "|") for e in exp]
        rend.append((key, got == exp, got, exp))
    for key, label_md in (("all_floor1", "bütün, b_floor = 1"), ("all_floor0", "bütün, b_floor = 0"), ("year_2024", "ilk işlem yılı 2024"),
                          ("year_2025", "ilk işlem yılı 2025"), ("year_2026", "ilk işlem yılı 2026")):
        line = [l for l in md.splitlines() if l.startswith("| " + label_md + " |")]
        assert len(line) == 1, label_md
        cells = [c.strip() for c in line[0].strip("|").split("|")]
        k = K[key]
        got = [str(k["n"]), f"{k['mean_p']:.4f}", f"{k['observed']:.4f}", f"{k['mean_p'] - k['observed']:+.4f}"]
        rend.append((key, got == cells[1:5], got, cells[1:5]))
    ok = not mism and all(r[1] for r in rend)
    say(f"[1f] hücreler günlük satırıyla (near_era, tam hassasiyet): {'EŞLEŞTİ' if not mism else 'UYUŞMAZLIK ' + str(mism[:5])}; maks |Δ| {max(maxd.values()):.2e}")
    for r in rend:
        say(f"[1f] MODELS.md keşif/kalibrasyon '{r[0]}': {'eşit' if r[1] else 'FARKLI'} {r[2] if not r[1] else ''} {r[3] if not r[1] else ''}")
    return {"ok": ok, "max_abs_delta": maxd, "mismatches": mism, "rendered": [(r[0], r[1]) for r in rend]}


# ============================================================ 9. N20: eşik duyarlılığı ve atom düzeyi örnekler (görev adım 2)
def n20_analysis(rows):
    near_floor = [r for r in rows if r["near"] and r["status"] == "FIT_OK" and r["test_b_floor"] == 1 and r["product_status"] == "OK"]
    near_above = [r for r in rows if r["near"] and r["status"] == "FIT_OK" and r["test_b_floor"] == 0 and r["product_status"] == "OK"]
    exact_share, near_double_share, examples = [], [], []
    alt = {name: {} for name in ("spec", "plus_one_tick", "nominal_0_9", "rel_1pct", "half_tick")}
    alt2 = {name: {} for name in ("spec", "plus_one_tick")}
    for r in [x for x in rows if x["status"] == "FIT_OK" and x["product_status"] == "OK"]:
        k = r["ticker"]
        u = U[k]
        cells, _ = cells_at(u["ftd"])
        pa = product_atoms(k, cells)
        atoms = pa["F1"][0]
        cb, P = u["close_b"], u["P"]
        lo1 = Lo(cb)
        thr_spec = float(lo1 / P - 1)
        thr_tick = float((lo1 + tick(lo1)) / P - 1)
        thr_nom = float(cb * Decimal("0.9") / P - 1)
        thr_rel = float(lo1 * Decimal("1.01") / P - 1)
        thr_half = float((lo1 + tick(lo1) / 2) / P - 1)
        for name, thr in (("spec", thr_spec), ("plus_one_tick", thr_tick), ("nominal_0_9", thr_nom), ("rel_1pct", thr_rel), ("half_tick", thr_half)):
            alt[name][k] = product_prob(atoms, thr)
        if pa["F2"][0] is not None:
            lo2 = Lo(lo1)
            alt2["spec"][k] = product_prob(pa["F2"][0], float(lo2 / P - 1))
            alt2["plus_one_tick"][k] = product_prob(pa["F2"][0], float((lo2 + tick(lo2)) / P - 1))
        if r in near_floor:
            exact_share.append(product_prob(atoms, thr_spec))
            near_double_share.append(sum(w for _, w, _, v in atoms if v <= -0.185))
    # 3 atom düzeyi örnek: eşiğin hemen üstünde kalan çift taban atomları (kaynak arzın kendi fiyat seviyesinde)
    for r in sorted(near_floor, key=lambda x: -(alt["plus_one_tick"][x["ticker"]] - alt["spec"][x["ticker"]]))[:3]:
        k = r["ticker"]
        u = U[k]
        cells, _ = cells_at(u["ftd"])
        atoms = product_atoms(k, cells)["F1"][0]
        cb, P, L = u["close_b"], u["P"], u["L"]
        scale = float(u["closes"][L - 1] / P) if L else 1.0
        thr_spec = float(Lo(cb) / P - 1)
        thr_tick = float((Lo(cb) + tick(Lo(cb))) / P - 1)
        # v uzayında eşik: scale·(1+v) − 1 ≤ thr ⇔ v ≤ (1+thr)/scale − 1
        v_thr = (1 + thr_spec) / scale - 1
        near_atoms = sorted([a for a in atoms if thr_spec + 1e-12 < a[0] <= thr_tick + 1e-12], key=lambda a: a[0])
        ex = {"ticker": k, "b": u["b"], "L": L, "P": str(P), "close_L": str(u["closes"][L - 1]) if L else None, "close_b": str(cb), "Lo(close_b)": str(Lo(cb)),
              "tick": str(tick(Lo(cb))), "thr_spec_r": thr_spec, "thr_plus_tick_r": thr_tick, "thr_spec_v": v_thr, "n_atoms": len(atoms),
              "p_spec": alt["spec"][k], "p_plus_tick": alt["plus_one_tick"][k], "p_nominal": alt["nominal_0_9"][k],
              "atoms_between_thr_and_plus_tick": []}
        for rr, w, src, v in near_atoms[:6]:
            su = U[src]
            t = su["L"]
            base = su["P"] if t == 0 else D(S[src][t]["thb_raw_close"])
            m = (u["b"] + 1) - L
            # kaynak atomun kendi fiyat seviyesi: base → close(D_{t+m}); çift taban olurdu: Lo(Lo(base))
            ex["atoms_between_thr_and_plus_tick"].append({"source": src, "source_L": t, "source_base": str(base), "source_close_t+m": S[src][t + m]["thb_raw_close"] if t + m <= 10 else None,
                                                          "source_LoLo(base)": str(Lo(Lo(base))), "v": v, "r": rr, "r_minus_thr": rr - thr_spec,
                                                          "price_equiv_at_test_level": str((Decimal(rr) + 1) * P)})
        examples.append(ex)
    summ = {"near_floor_n": len(near_floor), "mean_exact_share": sum(exact_share) / len(exact_share), "mean_near_double_share_v_le_-0.185": sum(near_double_share) / len(near_double_share),
            "near_above_n": len(near_above)}
    say(f"[N20] yakın dönem taban kırılması n={summ['near_floor_n']}: kesin eşik payı ort {summ['mean_exact_share']:.4f}; v ≤ −0.185 payı ort {summ['mean_near_double_share_v_le_-0.185']:.4f}")
    return alt, alt2, examples, summ


def alt_cells(rows, alt, alt2):
    out = {}
    for name, pm in alt.items():
        rr = [{**r, "product_alt": pm.get(r["ticker"])} for r in rows]
        c = paired(rr, "p_F1", "product_alt", "realized_F1", lambda r: r["near"])
        c["mean_p_floor_break"] = sum(pm[r["ticker"]] for r in rows if r["near"] and r["status"] == "FIT_OK" and r["test_b_floor"] == 1 and r["ticker"] in pm) / \
            sum(1 for r in rows if r["near"] and r["status"] == "FIT_OK" and r["test_b_floor"] == 1 and r["ticker"] in pm)
        c["mean_p_above_floor"] = sum(pm[r["ticker"]] for r in rows if r["near"] and r["status"] == "FIT_OK" and r["test_b_floor"] == 0 and r["ticker"] in pm) / \
            sum(1 for r in rows if r["near"] and r["status"] == "FIT_OK" and r["test_b_floor"] == 0 and r["ticker"] in pm)
        info = paired([{**r, "product_alt": pm.get(r["ticker"])} for r in rows], "product_alt", "zero_F1", "realized_F1", lambda r: r["near"] and r["ticker"] in c["diffs"], a_status=None)
        out[f"F1|{name}"] = {**strip_cell(c), "info_product_zero": strip_cell(info)}
        say(f"[N20-b] F1 model − ürün[{name}]: {fmt_cell(c)}; ürün ort p taban/taban üstü {c['mean_p_floor_break']:.3f}/{c['mean_p_above_floor']:.3f}; "
            f"ürün − @ZERO {info['mean']:+.4f} [{info['ci95'][0]:+.4f}, {info['ci95'][1]:+.4f}]")
    for name, pm in alt2.items():
        rr = [{**r, "product_alt": pm.get(r["ticker"])} for r in rows]
        c = paired(rr, "p_F2", "product_alt", "realized_F2", lambda r: r["near"], a_status="status_F2")
        out[f"F2|{name}"] = strip_cell(c)
        say(f"[N20-b] F2 model − ürün[{name}]: {fmt_cell(c)}")
    return out


# ============================================================ 10. Test arzı sızıntı denetimi (kendi kodumda; 3 fold)
def leak_check(rows):
    out = []
    for r in [x for x in rows if x["status"] == "FIT_OK"][:3]:
        k = r["ticker"]
        saved = {c: U[k][c] for c in ("b_floor", "b_turnover", "group_Z", "ratio")}
        U[k]["b_floor"] = 1 - U[k]["b_floor"]
        U[k]["b_turnover"] = U[k]["b_turnover"] + 3.0
        r2 = run_fold(k, MODEL)
        for c, v in saved.items():
            U[k][c] = v
        same = (r2["coef_F1"] == r["coef_F1"] and r2["intercept_F1"] == r["intercept_F1"] and r2["prep_F1"] == r["prep_F1"] and r2["scores_F1"] == r["scores_F1"]
                and r2["coef_F2"] == r["coef_F2"] and r2["prep_F2"] == r["prep_F2"] and r2["zero_F1"] == r["zero_F1"] and r2["product_F1"] == r["product_F1"])
        out.append({"ticker": k, "fit_bit_equal": same, "p_before": r["p_F1"], "p_after": r2["p_F1"], "by_type_before": r["by_type_F1"], "by_type_after": r2["by_type_F1"]})
        say(f"[sızıntı-i] {k}: test arzı alanları değiştirildi → katsayı/ön işleme/iç skorlar/@ZERO/ürün bit-eşit {same}; p_F1 {r['p_F1']:.4f} → {r2['p_F1']:.4f} (yalnız test satırı)")
    return out


def write_compact(variant, rows):
    cols = ["ticker", "first_trading_date", "b", "break_date", "status", "status_F2", "training_n", "training_events", "n_F2", "events_F2", "selected_C_F1",
            "selected_C_F2", "columns", "coef_F1", "intercept_F1", "coef_F2", "intercept_F2", "prep_F1", "prep_F2", "test_b_floor", "test_b_turnover_clipped",
            "p_F1", "p_F2", "zero_F1", "zero_F2", "by_type_F1", "product_F1", "product_F2", "product_status", "cells_max_session_date", "structural_zero_D10",
            "realized_F1", "realized_F2"]
    with open(OUT_DIR / "repro_ledgers" / f"repro_{variant}.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow([json.dumps(r[c], ensure_ascii=False, sort_keys=True) if isinstance(r[c], (dict, list)) else ("" if r[c] is None else r[c]) for c in cols])


# ============================================================ main
def main():
    workers = max(2, min(6, os.cpu_count() or 2))
    say(f"[ortam] python {sys.version.split()[0]}, numpy {np.__version__}, sklearn {__import__('sklearn').__version__}; işçi {workers}")
    results, cmp_ledgers = {}, {}
    rows = run_variant(MODEL, workers)
    results[MODEL] = rows
    write_compact(MODEL, rows)
    cmp_ledgers[MODEL] = compare_ledger(MODEL, rows)
    # Newton paritesi
    nw = [r["newton"] for r in rows if "newton" in r]
    say(f"[çözücü] Newton paritesi (ana model, F1, C≠ZERO, {len(nw)} fold): maks |Δp| {max(x['dp'] for x in nw):.2e}, maks |Δβ| {max(x['dcoef'] for x in nw):.2e}, maks |Δsabit| {max(x['dint'] for x in nw):.2e}")
    OUT["newton"] = {"n": len(nw), "max_dp": max(x["dp"] for x in nw), "max_dcoef": max(x["dcoef"] for x in nw), "max_dint": max(x["dint"] for x in nw)}
    # hücreler
    C, X, K = all_cells(rows)
    say("[1f] yakın dönem hücreleri:")
    for key in ("F1_product", "F1_zero", "F1_by_type", "F2_product", "F2_zero", "info_product_zero_F1"):
        say(f"    {key:<22} {fmt_cell(C[key])}")
    say("[1f] keşif:")
    for key, c in X.items():
        say(f"    {key:<22} {fmt_cell(c)}")
    say("[1f] kalibrasyon: " + "; ".join(f"{k}: n {v['n']}" + (f" ort p {v['mean_p']:.4f} gözlenen {v['observed']:.4f} fark {v['mean_p']-v['observed']:+.4f}" if v["n"] else "") for k, v in K.items()))
    OUT["cells_near"] = {k: strip_cell(v) for k, v in C.items()}
    OUT["cells_exploration"] = {k: strip_cell(v) for k, v in X.items()}
    OUT["calibration"] = K
    OUT["cells_compare"] = compare_cells(C, X, K)
    # nihai fit
    final = final_fits(MODEL)
    OUT["final_fit_compare"] = compare_preview(final)
    OUT["final_fit"] = {h: {"C": hp(final[h]["C"]), "coef": final[h]["coef"], "intercept": final[h]["intercept"], "prep": final[h]["prep"], "scores": final[h]["scores"],
                            "n": final[h]["n"], "events": final[h]["events"]} for h in ("F1", "F2")}
    # §6
    j6, too_good, fail, k1 = judge6(C, final, rows)
    say("[§6] satır satır hüküm:")
    for key, pos, verdict in j6:
        say(f"    {key:<22} {pos:<40} {verdict}")
    say(f"[§6] beklentiden çok iyi tetikleri: {too_good}; başarısızlık tanımları: {fail}; k1 (ön eleme): {k1}")
    OUT["judge6"] = {"rows": j6, "too_good": too_good, "fail": fail, "k1": k1,
                     "verdict_sequence": [v for _, _, v in j6],
                     "models_md_verdicts": ["tutmadı (daha iyi)", "tuttu", "tuttu", "tuttu", "tuttu", "tutmadı (daha kötü)", "tuttu", "tuttu", "tutmadı (> 0)", "tuttu", "tuttu", "tuttu", "tutmadı (az)"]}
    OUT["judge6"]["matches_models_md"] = OUT["judge6"]["verdict_sequence"] == OUT["judge6"]["models_md_verdicts"]
    say(f"[§6] hüküm dizisi MODELS.md ile aynı: {OUT['judge6']['matches_models_md']}")
    # N20
    alt, alt2, examples, summ = n20_analysis(rows)
    OUT["n20"] = {"summary": summ, "examples": examples, "alt_cells": alt_cells(rows, alt, alt2)}
    # sızıntı (kendi kodum)
    OUT["leak_check_own"] = leak_check(rows)
    # duyarlılıklar
    for variant in [v for v in VARIANTS if v != MODEL]:
        rws = run_variant(variant, workers)
        results[variant] = rws
        write_compact(variant, rws)
        cmp_ledgers[variant] = compare_ledger(variant, rws)
        Cv, _, _ = all_cells(rws)
        OUT.setdefault("sens_cells", {})[variant] = {k: strip_cell(v) for k, v in Cv.items()}
        say(f"[1h] {variant}: F1−ürün {fmt_cell(Cv['F1_product'])}; F1−@ZERO {fmt_cell(Cv['F1_zero'])}")
    OUT["ledger_compare"] = cmp_ledgers
    OUT["all_ok"] = all(c["ok"] for c in cmp_ledgers.values()) and OUT["final_fit_compare"]["ok"] and OUT["cells_compare"]["ok"]
    OUT["sys_modules_borsai"] = sorted(m for m in sys.modules if m == "borsai" or m.startswith("borsai."))
    OUT["elapsed_s"] = round(time.time() - T0, 1)
    say(f"[son] borsai sys.modules: {OUT['sys_modules_borsai']}; toplam süre {OUT['elapsed_s']} sn; HEPSİ EŞLEŞTİ: {OUT['all_ok']}")
    with open(OUT_DIR / "repro_output.json", "w", encoding="utf-8") as fh:
        json.dump(OUT, fh, ensure_ascii=False, indent=1, sort_keys=True, default=str)
    with open(OUT_DIR / "repro_stdout.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

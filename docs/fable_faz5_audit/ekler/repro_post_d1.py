#!/usr/bin/env python3
"""BORSAI_FAZ5_FABLE_REPRO_AUDIT_20260924 — `post_d1_hazard_v0`'ın SIFIRDAN, bağımsız yeniden üretimi (Fable).

`borsai` paketi İMPORT EDİLMEZ; yalnız stdlib + numpy. Yalnız şartnameden kodlanmıştır:
SPEC_POST_D1_V0 §1.3, §2, §3.1, §3.5, §6.1, §12; SPEC_CEILING_V0 §2, §4, §5, §9, §12 (ana model ofseti);
SPEC_CEILING_PATH_V0 §2–§4, §7 durum 1 (path_conditional); SPEC_SCORING §7–§8 ve SPEC_DEVIATIONS C7 (aralık).
Faz 1B (independent_repro.py) ve Faz 4 (repro_ceiling_path.py) bağımsız betiklerimin parçaları yeniden kullanıldı.

Girdiler (H99, ≤ 2026-08-19): data/training_table.csv, pretrade master (ipo_size_tl), SESSIONS dosyası
(1. seans ham alanları; 2..10. seanslardan D1 modeli için YALNIZ target_session_date; path hücreleri için
SPEC_CEILING_PATH_V0 §8 gereği kesim T öncesi kapanışlar), Faz 1B altın ledger'ları (karşılaştırıcılar),
models/ceiling_hazard_v0.json (nihai fit ofseti). data/outcomes, data/raw/bist, scores, docs/SCORES.md OKUNMAZ.

Çıktı: stdout raporu, repro_output.json, repro_post_d1_fold_ledger.csv, sens_*_fold_ledger.csv, sensitivity_runs.jsonl.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
assert (ROOT / "CLAUDE.md").exists(), ROOT
RAW = ROOT / "data" / "raw"
GOLD1B = ROOT / "tests" / "reference" / "macos_golden_faz1b"
GOLD5 = ROOT / "tests" / "reference" / "macos_golden_faz5"
OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
OUT_DIR.mkdir(parents=True, exist_ok=True)

INF = math.inf
LAMBDA_GRID = (0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, INF)
GROUP = {1: 0, 2: 1, 3: 1, **{d: 2 for d in range(4, 11)}}
RECLOSE = {**{k: "a" for k in (2, 3, 4)}, **{k: "b" for k in range(5, 11)}}
CTX28 = Context(prec=28, rounding=ROUND_HALF_EVEN)
CTX60 = Context(prec=60, rounding=ROUND_HALF_EVEN)
TOL = 1e-9
CUTOFF_MAX = "2026-08-19"
D1_COLS = ("d1_lock", "d1_turnover")
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


def ihash(items):
    return hashlib.sha256(("\n".join(items) + "\n").encode()).hexdigest()


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ============================================================ 0. veri (yalnız H99)
T = rd(ROOT / "data" / "training_table.csv")
M = {r["ticker"]: r for r in rd(RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv")}
SESS_PATH = RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv"
SES = rd(SESS_PATH)
ORDER = [r["ticker"] for r in T]
assert ORDER == [t for _, t in sorted((r["first_trading_date"], r["ticker"]) for r in T)] and len(ORDER) == 99
ROW = {r["ticker"]: r for r in T}
FTD = {t: ROW[t]["first_trading_date"] for t in ORDER}
L = {t: int(ROW[t]["ceiling_streak_L"]) for t in ORDER}
CLOSE_LBL = {t: [int(ROW[t][f"ceiling_close_D{k}"]) for k in range(1, 11)] for t in ORDER}
P_OF = {t: Decimal(ROW[t]["ipo_price_tl"]) for t in ORDER}
R_OF = {t: {h: float(Decimal(ROW[t][f"R_D{h}"])) for h in (1, 3, 5, 10)} for t in ORDER}
Y_OF = {t: {h: int(ROW[t][f"Y_D{h}"]) for h in (1, 3, 5, 10)} for t in ORDER}
F3_PRESENT = [t for t in ORDER if ROW[t]["total_demand_multiple"] != ""]
assert len(F3_PRESENT) == 97

# SESSIONS: D1 modeli için 1. seans ham alanları + bütün seansların tarihi; path hücreleri için kapanışlar (Faz 4 §8)
D1RAW: dict[str, dict] = {}
SESS_DATE: dict[str, dict[int, str]] = defaultdict(dict)
SESS_CLOSE: dict[str, dict[int, Decimal]] = defaultdict(dict)   # yalnız path hücreleri (kesim T öncesi gözlemler)
for s in SES:
    t, k = s["ticker"], int(s["session_number"])
    SESS_DATE[t][k] = s["target_session_date"]
    SESS_CLOSE[t][k] = Decimal(s["close"])
    if k == 1:
        D1RAW[t] = {"open": s["thb_raw_open"], "high": s["thb_raw_high"], "low": s["thb_raw_low"], "close": s["thb_raw_close"],
                    "volume": s["thb_raw_volume"], "trade_count": s["thb_raw_trade_count"], "upper": s["thm_raw_upper_limit"],
                    "session_type": s["session_type"], "status": s["security_trading_status"], "date": s["target_session_date"]}
SESSD = {t: [SESS_DATE[t][k] for k in range(1, 11)] for t in ORDER}
assert len(SES) == 990 and all(len(SESS_DATE[t]) == 10 for t in ORDER)
assert max(r["target_session_date"] for r in SES) <= CUTOFF_MAX
for t in ORDER:
    assert D1RAW[t]["date"] == FTD[t] == SESSD[t][0]
say(f"[veri] 99 arz, 990 seans; training_table sha256 {sha_file(ROOT / 'data' / 'training_table.csv')[:12]}, "
    f"SESSIONS sha256 {sha_file(SESS_PATH)[:12]}")


# ============================================================ 1. ana model özellikleri ve ön işlemesi (SPEC_CEILING_V0 §4; Faz 1B betiğim)
def pct(num: Decimal, den: Decimal) -> float:
    with localcontext(CTX28):
        raw = num / den * Decimal(100)
    return float(raw.quantize(Decimal("1e-10"), rounding=ROUND_HALF_UP))


def v15_raw(t):
    r = ROW[t]
    size = M[t]["ipo_size_tl"]
    if size in ("", "DATA_NOT_FOUND"):
        with localcontext(CTX28):
            f1 = Decimal(r["shares_offered"]) * Decimal(r["ipo_price_tl"])
    else:
        f1 = Decimal(size)
    f2 = pct(Decimal(r["shares_offered"]), Decimal(r["post_ipo_share_capital"]))
    f3 = None if r["total_demand_multiple"] == "" else float(Decimal(r["total_demand_multiple"]))
    return {"f1": float(f1), "f2": f2, "f3": f3}


V15 = {t: v15_raw(t) for t in ORDER}


def q7(vals, p):
    vals = sorted(vals)
    n = len(vals)
    h = (n - 1) * p
    lo = math.floor(h)
    if lo >= n - 1:
        return vals[-1]
    return vals[lo] + (h - lo) * (vals[lo + 1] - vals[lo])


class Prep:
    """Ana model ön işlemesi (arz düzeyinde): f1 ln, f3 [p05, p95] Type-7 kırpma, z-skor (popülasyon std)."""

    def __init__(self, tickers, raw):
        f3s = [raw[t]["f3"] for t in tickers]
        assert all(v is not None for v in f3s)
        self.lo, self.hi = q7(f3s, 0.05), q7(f3s, 0.95)
        X = {t: {"f1": math.log(raw[t]["f1"]), "f2": raw[t]["f2"], "f3": min(max(raw[t]["f3"], self.lo), self.hi)} for t in tickers}
        self.cols, self.mean, self.std = [], {}, {}
        for c in ("f1", "f2", "f3"):
            v = np.array([X[t][c] for t in tickers])
            if len(set(v.tolist())) <= 1:
                continue
            self.cols.append(c)
            self.mean[c], self.std[c] = float(v.mean()), float(v.std(ddof=0))
        self.Z = {t: self.transform_row(X[t]) for t in tickers}

    def transform_raw(self, r):
        return self.transform_row({"f1": math.log(r["f1"]), "f2": r["f2"], "f3": min(max(r["f3"], self.lo), self.hi)}), \
            (r["f3"] < self.lo or r["f3"] > self.hi)

    def transform_row(self, x):
        return np.array([(x[c] - self.mean[c]) / self.std[c] for c in self.cols])


# ============================================================ 2. PP tablosu ve fold planı (SPEC_CEILING_V0 §2, §9)
def pp_rows(t, cutoff=None):
    out = []
    for d in range(1, 11):
        if d - 1 > L[t]:
            break
        if cutoff is not None and SESSD[t][d - 1] >= cutoff:
            break
        out.append((t, d, GROUP[d], 1 if L[t] == d - 1 else 0))
    return out


def reclose(tickers, cutoff):
    n = {"a": 0, "b": 0}
    a = {"a": 0, "b": 0}
    for t in tickers:
        for k in range(2, 11):
            if L[t] < k and (cutoff is None or SESSD[t][k - 1] < cutoff):
                n[RECLOSE[k]] += 1
                a[RECLOSE[k]] += CLOSE_LBL[t][k - 1]
    return {"r_a": (a["a"] + 0.5) / (n["a"] + 1), "r_b": (a["b"] + 0.5) / (n["b"] + 1)}


def ceiling_fold(k):
    c = FTD[k]
    rows = [r for j in F3_PRESENT if FTD[j] < c for r in pp_rows(j, c)]
    training = list(dict.fromkeys(r[0] for r in rows))
    ev = sum(r[3] for r in rows)
    ok = len(training) >= 10 and ev >= 5 and len(rows) - ev >= 5
    return c, rows, training, ok


# ============================================================ 3. ana model fit'i (SPEC_CEILING_V0 §5; Faz 1B betiğim)
def fit_hazard(rows, Z, lam, p):
    g = np.array([r[2] for r in rows])
    e = np.array([r[3] for r in rows], dtype=float)
    X = np.zeros((len(rows) + 6, 3 + p))
    X[np.arange(len(rows)), g] = 1.0
    if p:
        X[: len(rows), 3:] = np.array([Z[r[0]] for r in rows])
    for i in range(3):
        X[len(rows) + 2 * i, i] = 1.0
        X[len(rows) + 2 * i + 1, i] = 1.0
    e = np.r_[e, np.tile([1.0, 0.0], 3)]
    w = np.r_[np.ones(len(rows)), np.full(6, 0.5)]
    ev = np.bincount(g, weights=e[: len(rows)], minlength=3)
    risk = np.bincount(g, minlength=3)
    gamma0 = np.log((ev + 0.5) / (risk - ev + 0.5))
    if lam == INF or p == 0:
        return gamma0, np.zeros(p), 0.0
    pen = np.r_[np.zeros(3), np.full(p, lam)]

    def J(th):
        eta = X @ th
        return float(np.sum(w * (np.logaddexp(0, eta) - e * eta)) + 0.5 * lam * th[3:] @ th[3:])

    def grad(th):
        h = 1 / (1 + np.exp(-(X @ th)))
        return X.T @ (w * (h - e)) + pen * th

    def hess(th):
        h = 1 / (1 + np.exp(-(X @ th)))
        return (X * (w * h * (1 - h))[:, None]).T @ X + np.diag(pen)

    th = np.r_[gamma0, np.zeros(p)]
    for _ in range(200):
        gr = grad(th)
        if np.max(np.abs(gr)) <= 1e-11:
            break
        step = np.linalg.solve(hess(th), gr)
        t0, J0 = 1.0, J(th)
        while J(th - t0 * step) > J0 + 1e-12 * max(1, abs(J0)) and t0 > 1e-8:
            t0 /= 2
        th = th - t0 * step
    return th[:3], th[3:], float(np.max(np.abs(grad(th))))


def hazards_of(gamma, beta, z):
    lin = float(beta @ z) if len(beta) else 0.0
    return [1 / (1 + math.exp(-(gamma[GROUP[d]] + lin))) for d in range(1, 11)]


def etas_of(gamma, beta, z):
    lin = float(beta @ z) if len(beta) else 0.0
    return [float(gamma[GROUP[d]]) + lin for d in range(1, 11)]


def sigmoid(x):
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def surv(h):
    out, s = [], 1.0
    for x in h:
        s *= 1 - x
        out.append(s)
    return out


def select_lambda_parent(training, rows, raw):
    by = {}
    for r in rows:
        by.setdefault(r[0], []).append(r)
    tot = {lam: 0.0 for lam in LAMBDA_GRID}
    n = 0
    for j in training:
        inner = [t for t in training if t != j]
        prep = Prep(inner, raw)
        p = len(prep.cols)
        zj, _ = prep.transform_raw(raw[j])
        irows = [r for t in inner for r in by[t]]
        for lam in LAMBDA_GRID:
            gam, bet, _ = fit_hazard(irows, prep.Z, lam, p)
            h = hazards_of(gam, bet, zj)
            for (_, d, _, ev) in by[j]:
                hh = min(max(h[d - 1], 1e-12), 1 - 1e-12)
                tot[lam] += -(ev * math.log(hh) + (1 - ev) * math.log(1 - hh))
        n += len(by[j])
    score = {lam: tot[lam] / n for lam in LAMBDA_GRID}
    best = min(score.values())
    return max(lam for lam, s in score.items() if s == best), score


def parent_fold(k):
    """Fold'un kendi ceiling_hazard_v0 fit'i: (kesim, satırlar, eğitim arzları, prep, γ, β, λ, test η, test hazard)."""
    c, rows, training, ok = ceiling_fold(k)
    assert ok
    sel, score = select_lambda_parent(training, rows, V15)
    prep = Prep(training, V15)
    gam, bet, gmax = fit_hazard(rows, prep.Z, sel, len(prep.cols))
    z_test, clipped = prep.transform_raw(V15[k])
    return {"cutoff": c, "rows": rows, "training": training, "prep": prep, "gamma": gam, "beta": bet, "lambda": sel,
            "score": score, "eta_test": etas_of(gam, bet, z_test), "hazard_test": hazards_of(gam, bet, z_test),
            "reclose": reclose(training, c), "grad_max": gmax}


# ============================================================ 4. D1 özellikleri (SPEC_POST_D1_V0 §2, §12)
def d1_features(t):
    f = D1RAW[t]
    close, trades = Decimal(f["close"]), Decimal(f["trade_count"])
    assert close > 0 and trades > 0, t                      # D_1 oluşmuş
    U = Decimal(f["upper"])
    assert U > 0, t                                         # limit var
    if close != U:
        return None                                         # NOT_APPLICABLE_D1_NOT_CEILING
    low, vol, shares = Decimal(f["low"]), Decimal(f["volume"]), Decimal(ROW[t]["shares_offered"])
    assert vol > 0 and shares > 0, t
    lock = int(low == U)
    consistent = (Decimal(f["open"]) == U) and (Decimal(f["high"]) == U) and (close == U)
    with localcontext(CTX60):
        ratio = vol / shares
        ln = ratio.ln()
    return {"d1_lock": float(lock), "d1_turnover": float(ln), "ratio": float(ratio), "lock": lock,
            "warn_inconsistent": bool(lock and not consistent), "half_day": f["session_type"] != "OPEN_FULL_DAY",
            "halt": f["status"] != "ACTIVE_NOT_SUSPENDED"}


D1F = {t: d1_features(t) for t in ORDER}
for t in ORDER:
    assert (D1F[t] is not None) == (CLOSE_LBL[t][0] == 1), t   # ham metin tavan etiketi = training_table etiketi
n_lge1 = sum(1 for t in ORDER if D1F[t] is not None)
FINAL81 = [t for t in F3_PRESENT if D1F[t] is not None]
say(f"[§2] D1 tavan (ham metin Decimal) = training_table etiketi: 99/99; L ≥ 1: {n_lge1}; f3 dolu ∧ L ≥ 1: {len(FINAL81)}; "
    f"kilit {sum(D1F[t]['lock'] for t in FINAL81)}/{len(FINAL81)}; tutarsız kilit {sum(D1F[t]['warn_inconsistent'] for t in FINAL81)}; "
    f"yarım gün {sum(D1F[t]['half_day'] for t in FINAL81)}; durdurma {sum(D1F[t]['halt'] for t in FINAL81)}")
assert len(FINAL81) == 81 and sum(D1F[t]["lock"] for t in FINAL81) == 70
ratios81 = sorted(D1F[t]["ratio"] for t in FINAL81)
say("[§2] el değiştirme oranı p05/p50/p95 (81, Type-7): " + " / ".join(f"{q7(ratios81, p):.4g}" for p in (0.05, 0.5, 0.95)))
OUT["d1_features"] = {"n_L_ge_1": n_lge1, "n_final": len(FINAL81), "lock": sum(D1F[t]["lock"] for t in FINAL81),
                      "ratio_q": [q7(ratios81, p) for p in (0.05, 0.5, 0.95)]}


# ============================================================ 5. D1 ön işlemesi ve δ fit'i (§2, §3.1, §6.1-5)
class D1Prep:
    def __init__(self, feats: dict, columns=D1_COLS):
        tk = list(feats)
        turn = [feats[t]["d1_turnover"] for t in tk]
        self.p05, self.p95 = q7(turn, 0.05), q7(turn, 0.95)
        vals = {"d1_lock": [feats[t]["d1_lock"] for t in tk],
                "d1_turnover": [min(max(feats[t]["d1_turnover"], self.p05), self.p95) for t in tk]}
        self.cols, self.dropped, self.mean, self.std = [], [], {}, {}
        for c in D1_COLS:
            v = np.array(vals[c], dtype=float)
            self.mean[c] = float(v.mean())
            sd = float(v.std(ddof=0))
            if c not in columns:                     # duyarlılık koşuları: kolon şartname dışı bırakılır
                continue
            if sd == 0.0:
                self.dropped.append(c)
                self.std[c] = 0.0
                continue
            self.std[c] = sd
            self.cols.append(c)
        self.n = len(tk)

    def transform(self, f):
        raw = f["d1_turnover"]
        x = {"d1_lock": f["d1_lock"], "d1_turnover": min(max(raw, self.p05), self.p95)}
        return np.array([(x[c] - self.mean[c]) / self.std[c] for c in self.cols]), not (self.p05 <= raw <= self.p95)


def delta_arrays(ds_rows, eta, feats, tickers, prep):
    U, o, e = [], [], []
    for t in tickers:
        u, _ = prep.transform(feats[t])
        for d, ev in ds_rows[t]:
            U.append(u)
            o.append(eta[t][d - 1])
            e.append(float(ev))
    return np.array(U, dtype=float).reshape(len(o), len(prep.cols)), np.array(o, dtype=float), np.array(e, dtype=float)


def fit_delta(U, o, e, lam):
    """J(δ) = −Σ [e ln h + (1−e) ln(1−h)] + (λ/2)‖δ‖², h = σ(o + Uδ); tam Newton, δ0 = 0, ∇ ≤ 1e-10 (burada 1e-12'ye
    kadar sürdürülür), adım yarılama. Pseudo-satır yok; ofset sabit."""
    p = U.shape[1]
    if lam == INF or p == 0:
        return np.zeros(p), 0, 0.0
    pen = lam * np.eye(p)

    def J(d):
        eta = o + U @ d
        return float(np.sum(np.logaddexp(0.0, eta) - e * eta) + 0.5 * lam * d @ d)

    d = np.zeros(p)
    it = 0
    for it in range(100):
        h = 1 / (1 + np.exp(-(o + U @ d)))
        g = U.T @ (h - e) + lam * d
        if np.max(np.abs(g)) <= 1e-12:
            break
        H = (U * (h * (1 - h))[:, None]).T @ U + pen
        step = np.linalg.solve(H, g)
        t0, J0 = 1.0, J(d)
        while J(d - t0 * step) > J0 + 1e-12 * max(1.0, abs(J0)) and t0 > 1e-9:
            t0 /= 2
        d = d - t0 * step
    h = 1 / (1 + np.exp(-(o + U @ d)))
    gmax = float(np.max(np.abs(U.T @ (h - e) + lam * d)))
    assert gmax <= 1e-10, gmax
    return d, it, gmax


def nll_rows(U, o, e, d):
    h = np.clip(1 / (1 + np.exp(-(o + (U @ d if U.shape[1] else 0.0)))), 1e-12, 1 - 1e-12)
    return -(e * np.log(h) + (1 - e) * np.log(1 - h))


def select_lambda_delta(ds_rows, eta, feats, tickers, columns=D1_COLS):
    tot = {lam: 0.0 for lam in LAMBDA_GRID}
    n = 0
    for j in tickers:
        inner = [t for t in tickers if t != j]
        prep = D1Prep({t: feats[t] for t in inner}, columns)
        U, o, e = delta_arrays(ds_rows, eta, feats, inner, prep)
        Uj, oj, ej = delta_arrays(ds_rows, eta, feats, [j], prep)
        for lam in LAMBDA_GRID:
            d, _, _ = fit_delta(U, o, e, lam)
            tot[lam] += float(np.sum(nll_rows(Uj, oj, ej, d)))
        n += len(ds_rows[j])
    score = {lam: tot[lam] / n for lam in LAMBDA_GRID}
    best = min(score.values())
    return max(lam for lam, s in score.items() if s == best), score


def fit_delta_set(ds_rows, eta, feats, tickers, columns=D1_COLS):
    sel, score = select_lambda_delta(ds_rows, eta, feats, tickers, columns)
    prep = D1Prep({t: feats[t] for t in tickers}, columns)
    U, o, e = delta_arrays(ds_rows, eta, feats, tickers, prep)
    d, it, gmax = fit_delta(U, o, e, sel)
    delta = {c: 0.0 for c in D1_COLS}
    for c, v in zip(prep.cols, d):
        delta[c] = float(v)
    return {"lambda": sel, "score": score, "prep": prep, "delta": delta, "iterations": it, "grad_max": gmax,
            "n_rows": len(e), "n_events": int(e.sum())}


def predict_post(eta, feats_t, fit):
    u, clipped = fit["prep"].transform(feats_t)
    shift = float(sum(fit["delta"][c] * u[i] for i, c in enumerate(fit["prep"].cols)))
    hz = [sigmoid(eta[0])] + [sigmoid(eta[d - 1] + shift) for d in range(2, 11)]
    S = surv(hz)
    S0 = [1.0] + S
    s_cond = {k: S0[k] / S0[1] for k in range(2, 11)}
    pl_cond = {t: (S0[t] - S0[t + 1]) / S0[1] for t in range(1, 10)}
    pl_cond[10] = S0[10] / S0[1]
    return {"hazard": hz, "S": S, "S_cond": s_cond, "P_L_cond": pl_cond, "u": u, "clipped": clipped}


# ============================================================ 6. path_conditional (SPEC_CEILING_PATH_V0 §2–§4, §7 durum 1; Faz 4 betiğim)
TICKS = [(Decimal(20), Decimal("0.01")), (Decimal(50), Decimal("0.02")), (Decimal(100), Decimal("0.05")),
         (Decimal(250), Decimal("0.10")), (Decimal(500), Decimal("0.25")), (Decimal(1000), Decimal("0.50")),
         (Decimal(2500), Decimal("1.00")), (None, Decimal("2.50"))]


def tick(x):
    for lim, s in TICKS:
        if lim is None or x < lim:
            return s
    raise AssertionError


def Ulim(b):
    y = b * Decimal("1.1")
    s = tick(y)
    return (y / s).to_integral_value(rounding=ROUND_FLOOR) * s


def snap(P):
    s = tick(P)
    return (P / s).to_integral_value(rounding=ROUND_HALF_UP) * s


def limit_path(P):
    C, b = [], snap(P)
    for _ in range(10):
        b = Ulim(b)
        C.append(b)
    return C, [float(c / P - 1) for c in C]


def build_cells(cutoff):
    cells = {("Z", m): [] for m in range(1, 11)} | {("B", m): [] for m in range(1, 10)}
    max_date = None
    for tk in ORDER:
        t = L[tk]
        if t >= 10:
            continue
        base = P_OF[tk] if t == 0 else SESS_CLOSE[tk][t]
        g = "Z" if t == 0 else "B"
        for m in range(1, 11 - t):
            d = SESSD[tk][t + m - 1]
            if d >= cutoff:
                break
            cells[(g, m)].append((float(SESS_CLOSE[tk][t + m] / base - 1), tk))
            max_date = d if max_date is None or d > max_date else max_date
    return {k: sorted(v) for k, v in cells.items()}, max_date


def valid(g, m):
    return 1 <= m <= (10 if g == "Z" else 9)


def ladder(g, m):
    other = "B" if g == "Z" else "Z"
    steps = [[(g, m)], [(other, m)] if valid(other, m) else []]
    for d in range(1, 10):
        for mm in (m - d, m + d):
            steps.append([(gg, mm) for gg in ("Z", "B") if valid(gg, mm)])
    return [s for s in steps if s]


def pooled(cells, g, m, n_min=10):
    out, used = [], []
    for step in ladder(g, m):
        for key in step:
            used.append(key)
            out += cells[key]
        if len(out) >= n_min:
            break
    if len(out) < n_min:
        return None
    if len(used) > 1:
        lo, hi = float(Decimal("0.9") ** m - 1), float(Decimal("1.1") ** m - 1)
        out = [(min(max(v, lo), hi), tk) for v, tk in out]
    return out


def cond_mixture(S, P, C, rho, cells, h, close_d1: Decimal):
    """§7 durum 1, j = 1: [(ρ_h, S_h/S_1)] + t = 1..h−1 için hücre(B, h − t), ağırlık P(L = t | L ≥ 1)/n; ölçek t = 1 için
    gözlenen kapanış(D_1)/P, t > 1 için C_t/P."""
    S0 = [1.0] + list(S)
    s_cond = {k: S0[k] / S0[1] for k in range(2, 11)}
    pl = {t: (S0[t] - S0[t + 1]) / S0[1] for t in range(1, 10)}
    pl[10] = S0[10] / S0[1]
    atoms = [(rho[h - 1], s_cond[h])]
    for t in range(1, h):
        vals = pooled(cells, "B", h - t)
        if vals is None:
            return None
        scale = float(close_d1 / P) if t == 1 else float(C[t - 1] / P)
        w = pl[t] / len(vals)
        atoms += [(scale * (1 + v) - 1, w) for v, _ in vals]
    atoms.sort(key=lambda a: a[0])

    def Q(q):
        cum = 0.0
        for r, w in atoms:
            cum += w
            if cum >= q - 1e-12:
                return r
        return atoms[-1][0]

    return {"median": Q(0.5), "p_up": sum(w for r, w in atoms if r > 0), "n_atoms": len(atoms)}


# ============================================================ 7. walk-forward (§6.1)
LED1B = {name: rd(GOLD1B / f"{name}_fold_ledger.csv", enc="utf-8") for name in
         ("ceiling_hazard_v0", "ceiling_hazard_v0@INF", "base_km_expanding", "base_km_last10", "base_always_ceiling__ceiling")}
SRC = LED1B["ceiling_hazard_v0"]
assert len(SRC) == 87 and all(r["status"] == "FIT_OK" for r in SRC)
SRC_BY = {r["ticker"]: r for r in SRC}
OPUS = rd(GOLD5 / "post_d1_hazard_v0_fold_ledger.csv", enc="utf-8")
OPUS_BY = {r["ticker"]: r for r in OPUS}
assert [r["fold_id"] for r in OPUS] == [r["fold_id"] for r in SRC]
PARENT_CACHE: dict[str, dict] = {}


def run_fold(k, columns=D1_COLS, with_path=True):
    """Bir fold: durum, ana model ofseti, δ eğitim kümesi, λ, δ, test tahmini, path_conditional."""
    src = SRC_BY[k]
    T_ = src["prediction_date"]
    assert T_ == FTD[k] == D1RAW[k]["date"]
    out = {"fold_id": src["fold_id"], "ticker": k, "T": T_, "realized_L": L[k]}
    if L[k] < 1:
        out["status"] = "NOT_APPLICABLE"
        return out
    if k not in PARENT_CACHE:
        PARENT_CACHE[k] = parent_fold(k)
    pf = PARENT_CACHE[k]
    out.update(parent_gamma=[float(x) for x in pf["gamma"]], parent_beta=dict(zip(pf["prep"].cols, (float(x) for x in pf["beta"]))),
               parent_lambda=pf["lambda"], parent_hazard_test=pf["hazard_test"], parent_score=pf["score"])
    # δ eğitim kümesi: d ≥ 2 satırları; D1(j) < T zorunlu (D2 tarihi < T ⇒ D1 tarihi < T)
    ds_rows: dict[str, list] = {}
    for (t, d, _, ev) in pf["rows"]:
        if d >= 2:
            ds_rows.setdefault(t, []).append((d, ev))
    tickers = list(ds_rows)
    assert k not in tickers and all(FTD[t] < T_ for t in tickers)
    assert all(SESSD[t][0] < T_ for t in tickers) and all(SESSD[t][d - 1] < T_ for t in tickers for d, _ in ds_rows[t])
    feats = {t: D1F[t] for t in tickers}
    assert all(f is not None for f in feats.values())              # d ≥ 2 satırı olan arz L ≥ 1
    eta = {t: etas_of(pf["gamma"], pf["beta"], pf["prep"].Z[t]) for t in tickers}
    n_rows = sum(len(v) for v in ds_rows.values())
    n_ev = sum(ev for v in ds_rows.values() for _, ev in v)
    out.update(n_ipo=len(tickers), n_pp_rows=n_rows, n_events=n_ev, n_survivals=n_rows - n_ev,
               max_session_date=max(SESSD[t][d - 1] for t in tickers for d, _ in ds_rows[t]),
               tickers_sha256=ihash(tickers), pp_sha256=ihash([f"{t}|{d}|{e}" for t in tickers for d, e in ds_rows[t]]))
    if not (len(tickers) >= 10 and n_ev >= 5 and n_rows - n_ev >= 5):
        out["status"] = "INSUFFICIENT_TRAINING_HISTORY"
        return out
    fit = fit_delta_set(ds_rows, eta, feats, tickers, columns)
    pred = predict_post(pf["eta_test"], D1F[k], fit)
    out.update(status="FIT_OK", selected_lambda=fit["lambda"], score=fit["score"], columns=list(fit["prep"].cols),
               dropped=list(fit["prep"].dropped), delta=fit["delta"], p05=fit["prep"].p05, p95=fit["prep"].p95,
               mean=fit["prep"].mean, std=fit["prep"].std, iterations=fit["iterations"], grad_max=fit["grad_max"],
               test_lock=D1F[k]["lock"], test_ratio=D1F[k]["ratio"], test_clipped=pred["clipped"],
               hazard=pred["hazard"], S=pred["S"], S_cond=pred["S_cond"], P_L_cond=pred["P_L_cond"])
    if with_path:
        cells, max_date = build_cells(T_)
        assert max_date is None or max_date < T_
        C, rho = limit_path(P_OF[k])
        close_d1 = Decimal(D1RAW[k]["close"])
        pc = {h: cond_mixture(pred["S"], P_OF[k], C, rho, cells, h, close_d1) for h in (3, 5, 10)}
        S_cmp = [float(src[f"S_{i}"]) for i in range(1, 11)]
        pc_cmp = {h: cond_mixture(S_cmp, P_OF[k], C, rho, cells, h, close_d1) for h in (3, 5, 10)}
        out.update(path=pc, path_cmp=pc_cmp, path_status="OK" if all(v is not None for v in pc.values()) else "POST_BREAK_INSUFFICIENT")
    return out


say("\n=== 1. Walk-forward: 87 fold sıfırdan (ana model ofseti dahil) ===")
t0 = time.time()
FOLDS = [run_fold(r["ticker"]) for r in SRC]
say(f"[koşu] {len(FOLDS)} fold, {time.time() - t0:.0f} s; durumlar {dict(Counter(f['status'] for f in FOLDS))}")

# ---- (a) fold ledger karşılaştırması
NUM_COLS = (["delta_d1_lock", "delta_d1_turnover", "d1_clip_p05", "d1_clip_p95", "d1_mean_lock", "d1_std_lock", "d1_mean_turnover",
             "d1_std_turnover", "test_d1_turnover_ratio"] + [f"hazard_{k}" for k in range(1, 11)] + [f"S_{k}" for k in range(1, 11)]
            + [f"S_cond_{k}" for k in range(2, 11)])


def mine_row(f):
    if f["status"] != "FIT_OK":
        return {}
    r = {"delta_d1_lock": f["delta"]["d1_lock"], "delta_d1_turnover": f["delta"]["d1_turnover"], "d1_clip_p05": f["p05"],
         "d1_clip_p95": f["p95"], "d1_mean_lock": f["mean"]["d1_lock"], "d1_std_lock": f["std"].get("d1_lock", 0.0),
         "d1_mean_turnover": f["mean"]["d1_turnover"], "d1_std_turnover": f["std"].get("d1_turnover", 0.0),
         "test_d1_turnover_ratio": f["test_ratio"]}
    r.update({f"hazard_{k}": f["hazard"][k - 1] for k in range(1, 11)})
    r.update({f"S_{k}": f["S"][k - 1] for k in range(1, 11)})
    r.update({f"S_cond_{k}": f["S_cond"][k] for k in range(2, 11)})
    return r


def lam_of(s):
    return INF if s == "INF" else float(s)


CMP = {"status_exact": 0, "lambda_exact": 0, "training_exact": 0, "parent_exact": 0, "n_fit_ok": 0, "max_abs": defaultdict(float),
       "score_table_max_abs": 0.0, "parent_max_abs": 0.0, "test_lock_exact": 0, "clipped_exact": 0, "columns_exact": 0,
       "path_status_exact": 0, "path_max_abs": defaultdict(float), "mismatch": []}
for f in FOLDS:
    o = OPUS_BY[f["ticker"]]
    CMP["status_exact"] += int(o["status"] == f["status"])
    if o["status"] != f["status"]:
        CMP["mismatch"].append((f["ticker"], "status", o["status"], f["status"]))
    if f["status"] == "NOT_APPLICABLE":
        continue
    # ana model (ofset) paritesi: Faz 1B ledger'ı ve Opus'un parent_* sütunları
    src = SRC_BY[f["ticker"]]
    got = [*f["parent_gamma"], *(f["parent_beta"].get(c, 0.0) for c in ("f1", "f2", "f3")), *f["parent_hazard_test"]]
    want = [float(src[f"gamma_g{i}"]) for i in (1, 2, 3)] + [float(src[f"beta_{c}"]) for c in ("f1", "f2", "f3")] + \
           [float(src[f"hazard_{k}"]) for k in range(1, 11)]
    want_o = [float(o[f"parent_gamma_g{i}"]) for i in (1, 2, 3)] + [float(o[f"parent_beta_{c}"]) for c in ("f1", "f2", "f3")]
    CMP["parent_max_abs"] = max(CMP["parent_max_abs"], max(abs(a - b) for a, b in zip(got, want)), max(abs(a - b) for a, b in zip(got[:6], want_o)))
    CMP["parent_exact"] += int(lam_of(src["selected_lambda"]) == f["parent_lambda"] == lam_of(o["parent_selected_lambda"]))
    CMP["training_exact"] += int((int(o["training_n_ipo"]), int(o["training_n_pp_rows"]), int(o["training_n_events"]), int(o["training_n_survivals"]),
                                  o["training_max_session_date"], o["training_tickers_sha256"], o["training_pp_sha256"]) ==
                                 (f["n_ipo"], f["n_pp_rows"], f["n_events"], f["n_survivals"], f["max_session_date"], f["tickers_sha256"], f["pp_sha256"]))
    if f["status"] != "FIT_OK":
        continue
    CMP["n_fit_ok"] += 1
    CMP["lambda_exact"] += int(lam_of(o["selected_lambda"]) == f["selected_lambda"])
    if lam_of(o["selected_lambda"]) != f["selected_lambda"]:
        CMP["mismatch"].append((f["ticker"], "selected_lambda", o["selected_lambda"], f["selected_lambda"]))
    tab = {lam_of(str(e["lambda"])): e["score"] for e in json.loads(o["lambda_score_table"])}
    CMP["score_table_max_abs"] = max(CMP["score_table_max_abs"], max(abs(tab[l] - f["score"][l]) for l in LAMBDA_GRID))
    mr = mine_row(f)
    for c in NUM_COLS:
        d = abs(float(o[c]) - mr[c])
        CMP["max_abs"][c] = max(CMP["max_abs"][c], d)
        if d > TOL:
            CMP["mismatch"].append((f["ticker"], c, o[c], mr[c]))
    CMP["test_lock_exact"] += int(int(o["test_d1_lock"]) == f["test_lock"])
    CMP["clipped_exact"] += int((o["test_d1_turnover_clipped"] == "TRUE") == f["test_clipped"])
    CMP["columns_exact"] += int(json.loads(o["columns"]) == f["columns"])
    CMP["path_status_exact"] += int(o["path_cond_status"] == f["path_status"])
    for h in (3, 5, 10):
        for x, key in (("median", "median"), ("p_up", "p_up")):
            d = abs(float(o[f"path_cond_h{h}_{x}"]) - f["path"][h][key])
            CMP["path_max_abs"][f"h{h}_{x}"] = max(CMP["path_max_abs"][f"h{h}_{x}"], d)
            if d > TOL:
                CMP["mismatch"].append((f["ticker"], f"path_cond_h{h}_{x}", o[f"path_cond_h{h}_{x}"], f["path"][h][key]))
CMP["max_abs"] = dict(CMP["max_abs"])
CMP["path_max_abs"] = dict(CMP["path_max_abs"])
say("\n=== (a) Fold ledger karşılaştırması (tests/reference/macos_golden_faz5) ===")
say(f"status birebir {CMP['status_exact']}/87; λ birebir {CMP['lambda_exact']}/{CMP['n_fit_ok']}; training_* birebir {CMP['training_exact']}/71; "
    f"parent λ birebir {CMP['parent_exact']}/71; parent γ/β/test hazard maks|Δ| {CMP['parent_max_abs']:.3e}")
say(f"λ skor tablosu maks|Δ| {CMP['score_table_max_abs']:.3e}; test_d1_lock birebir {CMP['test_lock_exact']}/70; kırpma bayrağı birebir "
    f"{CMP['clipped_exact']}/70; columns birebir {CMP['columns_exact']}/70; path_cond_status birebir {CMP['path_status_exact']}/70")
worst = max(CMP["max_abs"].values())
say(f"sayısal sütunlar maks|Δ| = {worst:.3e} (en kötü sütun {max(CMP['max_abs'], key=CMP['max_abs'].get)}); "
    + ", ".join(f"{k} {v:.1e}" for k, v in sorted(CMP["max_abs"].items(), key=lambda kv: -kv[1])[:6]))
say(f"path_conditional maks|Δ|: " + ", ".join(f"{k} {v:.1e}" for k, v in CMP["path_max_abs"].items()))
say(f"|Δ| > 1e-9 ya da birebir olmayan: {len(CMP['mismatch'])}")
for m in CMP["mismatch"][:20]:
    say("   UYUŞMAZLIK:", m)
OUT["a_ledger_compare"] = CMP

# (d) paritesi: INF fold'larında S_cond ≡ karşılaştırıcı; h_1 ≡ Faz 1B ledger hazard_1 (metin düzeyinde, Opus ledger'ı)
inf_folds = [f for f in FOLDS if f["status"] == "FIT_OK" and f["selected_lambda"] == INF]
d_inf_mine = max((max(abs(f["S_cond"][k] - float(SRC_BY[f["ticker"]][f"S_{k}"]) / float(SRC_BY[f["ticker"]]["S_1"])) for k in range(2, 11)) for f in inf_folds), default=0.0)
d_inf_opus = max((max(abs(float(OPUS_BY[f["ticker"]][f"S_cond_{k}"]) - float(SRC_BY[f["ticker"]][f"S_{k}"]) / float(SRC_BY[f["ticker"]]["S_1"])) for k in range(2, 11)) for f in inf_folds), default=0.0)
h1_text_eq = sum(1 for f in FOLDS if f["status"] == "FIT_OK" and OPUS_BY[f["ticker"]]["hazard_1"] == SRC_BY[f["ticker"]]["hazard_1"])
h1_mine = max(abs(f["hazard"][0] - float(SRC_BY[f["ticker"]]["hazard_1"])) for f in FOLDS if f["status"] == "FIT_OK")
say(f"(d) INF fold'ları {[f['ticker'] for f in inf_folds]}: S_cond − karşılaştırıcı S_cond maks|Δ| benim {d_inf_mine:.1e}, Opus {d_inf_opus:.1e}; "
    f"h_1 Opus ledger metni == Faz 1B ledger metni: {h1_text_eq}/70; benim h_1 maks|Δ| {h1_mine:.1e}")
OUT["d_parity"] = {"inf_folds": [f["ticker"] for f in inf_folds], "inf_scond_max_abs_mine": d_inf_mine, "inf_scond_max_abs_opus": d_inf_opus,
                   "h1_text_equal": h1_text_eq, "h1_max_abs_mine": h1_mine}

# ============================================================ 8. nihai fit (§3.5; ofset dondurulmuş JSON'dan)
say("\n=== (b) Nihai fit (81 arz, ofset models/ceiling_hazard_v0.json) ===")
PJ = json.load(open(ROOT / "models" / "ceiling_hazard_v0.json"))
pp_ = PJ["preprocessing"]


def eta_from_json(t):
    v = V15[t]
    x = {"f1": math.log(v["f1"]), "f2": v["f2"], "f3": min(max(v["f3"], pp_["winsor"]["f3"]["p05"]), pp_["winsor"]["f3"]["p95"])}
    z = {c: (x[c] - pp_["mean"][c]) / pp_["std"][c] for c in pp_["columns"]}
    lin = sum(PJ["beta"][c] * z[c] for c in z)
    return [PJ["gamma"][GROUP[d]] + lin for d in range(1, 11)]


fin_rows = {}
for t in FINAL81:
    rows = [(d, ev) for (_, d, _, ev) in pp_rows(t) if d >= 2]
    if rows:
        fin_rows[t] = rows
fin_tk = [t for t in FINAL81 if t in fin_rows]
fin_eta = {t: eta_from_json(t) for t in fin_tk}
fin_feats = {t: D1F[t] for t in fin_tk}
n_rows_f = sum(len(v) for v in fin_rows.values())
n_ev_f = sum(ev for v in fin_rows.values() for _, ev in v)
say(f"δ eğitim kümesi: {len(fin_tk)} arz, {n_rows_f} satır (d ≥ 2), {n_ev_f} olay, {n_rows_f - n_ev_f} sağ kalım; "
    f"en son eğitim seansı {max(SESSD[t][d - 1] for t in fin_tk for d, _ in fin_rows[t])}")
assert (len(fin_tk), n_rows_f, n_ev_f) == (81, 409, 67)
FINFIT = fit_delta_set(fin_rows, fin_eta, fin_feats, fin_tk)
PREV = json.load(open(GOLD5 / "post_d1_hazard_v0_final_fit_preview.json"))
ptab = {lam_of(str(e["lambda"])): e["score"] for e in PREV["lambda_score_table"]}
B = {"lambda": (FINFIT["lambda"], PREV["lambda"]), "lambda_exact": lam_of(str(PREV["lambda"])) == FINFIT["lambda"],
     "delta_max_abs": max(abs(FINFIT["delta"][c] - PREV["delta"][c]) for c in D1_COLS),
     "clip_max_abs": max(abs(FINFIT["prep"].p05 - PREV["d1_preprocessing"]["clip"]["d1_turnover"]["p05"]),
                         abs(FINFIT["prep"].p95 - PREV["d1_preprocessing"]["clip"]["d1_turnover"]["p95"])),
     "mean_max_abs": max(abs(FINFIT["prep"].mean[c] - PREV["d1_preprocessing"]["mean"][c]) for c in D1_COLS),
     "std_max_abs": max(abs(FINFIT["prep"].std[c] - PREV["d1_preprocessing"]["std"][c]) for c in D1_COLS),
     "score_table_max_abs": max(abs(FINFIT["score"][l] - ptab[l]) for l in LAMBDA_GRID),
     "columns": (FINFIT["prep"].cols, PREV["d1_preprocessing"]["columns"]), "dropped": (FINFIT["prep"].dropped, PREV["d1_preprocessing"]["dropped"]),
     "counts": ((len(fin_tk), n_rows_f, n_ev_f, n_rows_f - n_ev_f), (PREV["training"]["n_delta_ipo"], PREV["training"]["n_pp_rows"],
                PREV["training"]["n_events"], PREV["training"]["n_survivals"])),
     "delta_mine": FINFIT["delta"], "delta_opus": PREV["delta"], "grad_max_mine": FINFIT["grad_max"], "iterations_mine": FINFIT["iterations"],
     "score_mine": {("INF" if l == INF else l): s for l, s in FINFIT["score"].items()},
     "parent_sha256_pinned": PREV["parent"]["sha256"], "parent_sha256_file": sha_file(ROOT / "models" / "ceiling_hazard_v0.json")}
say(f"λ: benim {FINFIT['lambda']} / Opus {PREV['lambda']} (birebir {B['lambda_exact']}); δ maks|Δ| {B['delta_max_abs']:.2e} "
    f"(benim {FINFIT['delta']}, Opus {PREV['delta']}); kırpma maks|Δ| {B['clip_max_abs']:.2e}; μ maks|Δ| {B['mean_max_abs']:.2e}; "
    f"σ maks|Δ| {B['std_max_abs']:.2e}; skor tablosu maks|Δ| {B['score_table_max_abs']:.2e}; kolon/düşen {B['columns']} / {B['dropped']}; "
    f"sayılar {B['counts']}; parent sha pin == dosya: {B['parent_sha256_pinned'] == B['parent_sha256_file']}")
OUT["b_final_fit"] = B
# nihai modelin h_1'i ana modelle bit-eşit mi (81 arz; kendi hesabım)
h1_fin = all(sigmoid(fin_eta[t][0]) == sigmoid(PJ["gamma"][0] + sum(PJ["beta"][c] * ((({"f1": math.log(V15[t]["f1"]), "f2": V15[t]["f2"],
              "f3": min(max(V15[t]["f3"], pp_["winsor"]["f3"]["p05"]), pp_["winsor"]["f3"]["p95"])}[c]) - pp_["mean"][c]) / pp_["std"][c]) for c in pp_["columns"])) for t in fin_tk)
say(f"nihai fit h_1 (ofset) ana modelin kendi h_1'iyle bit-eşit (81 arz, kendi hesabım): {h1_fin}")


# ============================================================ 9. §4 hücreleri, aralıklar (SPEC_SCORING §7–§8, C7)
def boot(diffs, months, seed=20260921, reps=4000):
    by = {}
    for m, d in zip(months, diffs):
        by.setdefault(m, []).append(d)
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


def paired(rows):
    diffs = [a - b for _, _, a, b in rows]
    months = [m for _, m, _, _ in rows]
    lo, hi = boot(diffs, months)
    return {"n": len(rows), "n_months": len(set(months)), "model": sum(a for *_, a, _ in rows) / len(rows),
            "rule": sum(b for *_, _, b in rows) / len(rows), "diff": sum(diffs) / len(diffs), "ci": [lo, hi],
            "wins": sum(1 for d in diffs if d < 0), "losses": sum(1 for d in diffs if d > 0), "ties": sum(1 for d in diffs if d == 0),
            "wins_tol": sum(1 for d in diffs if d < -1e-12), "losses_tol": sum(1 for d in diffs if d > 1e-12),
            "ties_tol": sum(1 for d in diffs if abs(d) <= 1e-12),      # bağımsız refit bit-eşit olamaz: |d| ≤ 1e-12 eşitlik sayılır
            "verdict": "MODEL" if hi < 0 else ("RULE" if lo > 0 else "AYIRT_EDILEMIYOR"), "diffs": {r[0]: d for r, d in zip(rows, diffs)}}


def cond_S(S):
    return {k: S[k - 1] / S[0] for k in range(2, 11)}


def cond_rps(S, Lv):
    sc = cond_S(S)
    return sum((sc[k] - (1.0 if Lv >= k else 0.0)) ** 2 for k in range(2, 11)) / 9


def cond_brier(S, Lv, k):
    return (cond_S(S)[k] - (1.0 if Lv >= k else 0.0)) ** 2


OKF = [f for f in FOLDS if f["status"] == "FIT_OK"]
COMPS = ("ceiling_hazard_v0", "base_km_expanding", "base_km_last10", "ceiling_hazard_v0@INF", "base_always_ceiling__ceiling")


def cell(metric, comp, folds=None):
    folds = OKF if folds is None else folds
    led = {r["ticker"]: r for r in LED1B[comp]}
    rows = []
    for f in folds:
        o = led[f["ticker"]]
        assert o["status"] in ("FIT_OK", "RULE_OK") and int(o["realized_L"]) == f["realized_L"] >= 1
        Sc = [float(o[f"S_{k}"]) for k in range(1, 11)]
        if Sc[0] <= 0:
            continue
        if metric == "rps":
            a, b = cond_rps(f["S"], f["realized_L"]), cond_rps(Sc, f["realized_L"])
        else:
            k = int(metric[5:])
            a, b = cond_brier(f["S"], f["realized_L"], k), cond_brier(Sc, f["realized_L"], k)
        rows.append((f["ticker"], FTD[f["ticker"]][:7], a, b))
    return paired(rows)


say("\n=== (c) §4 hücreleri: fark, %95 aralık, n (bağımsız hesap) ===")
CELLS = {}
for m in ("rps", "brier2", "brier10"):
    for c in COMPS:
        CELLS[(m, c)] = cell(m, c)
for k in range(3, 10):
    CELLS[(f"brier{k}", "ceiling_hazard_v0")] = cell(f"brier{k}", "ceiling_hazard_v0")


def path_cell(h, kind):
    rows = []
    for f in OKF:
        a_, b_ = f["path"][h], f["path_cmp"][h]
        if a_ is None or b_ is None:
            continue
        if kind == "MAE":
            rows.append((f["ticker"], FTD[f["ticker"]][:7], abs(a_["median"] - R_OF[f["ticker"]][h]), abs(b_["median"] - R_OF[f["ticker"]][h])))
        else:
            y = Y_OF[f["ticker"]][h]
            cl = lambda p: min(max(p, 0.01), 0.99)  # noqa: E731
            rows.append((f["ticker"], FTD[f["ticker"]][:7], (cl(a_["p_up"]) - y) ** 2, (cl(b_["p_up"]) - y) ** 2))
    return paired(rows)


PATHC = {(h, kind): path_cell(h, kind) for h in (3, 5, 10) for kind in ("MAE", "Brier")}

# MODELS.md Faz 5 bölümündeki sayılarla karşılaştırma (basılı hassasiyet)
MD = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8").split("## Faz 5: D1 sonrası güncelleme")[1]


def md_rows(after, until):
    block = MD.split(after)[1].split(until)[0]
    return [[c.strip() for c in l.strip().strip("|").split("|")] for l in block.splitlines() if l.startswith("| ") and "---" not in l]


def fmt_s(x):
    return f"{x:+.4f}"


def fmt_ci(ci):
    return f"[{ci[0]:+.4f}, {ci[1]:+.4f}]"


md_main = md_rows("### Bütün §4 hücreleri", "Kalibrasyon (ikincil")[1:]
md_path = md_rows("`path_conditional` (ikincil", "Keşif: koşullu Brier")[1:]
md_expl = md_rows("Keşif: koşullu Brier k = 3..9", "### Fold özeti")[1:]
label = {"ceiling_hazard_v0": "`ceiling_hazard_v0` koşullu (karşılaştırıcı)", "base_km_expanding": "`base_km_expanding` koşullu",
         "base_km_last10": "`base_km_last10` koşullu", "ceiling_hazard_v0@INF": "`ceiling_hazard_v0@INF` koşullu",
         "base_always_ceiling__ceiling": "`base_always_ceiling` (S_cond ≡ 1)"}
C_CMP = {"printed_match": 0, "checked": 0, "rows": [], "mismatch": []}
i = 0
for m in ("rps", "brier2", "brier10"):
    for c in COMPS:
        p = CELLS[(m, c)]
        md = md_main[i]
        i += 1
        ok = (md[2].startswith(str(p["n"])) and md[3] == f"{p['model']:.4f}" and md[4] == f"{p['rule']:.4f}" and md[5] == fmt_s(p["diff"])
              and md[6] == fmt_ci(p["ci"]) and md[7] in (f"{p['wins']} / {p['losses']} / {p['ties']}", f"{p['wins_tol']} / {p['losses_tol']} / {p['ties_tol']}"))
        ok_exact_counts = md[7] == f"{p['wins']} / {p['losses']} / {p['ties']}"
        C_CMP["checked"] += 1
        C_CMP["printed_match"] += int(ok)
        row = {"metric": m, "comparator": c, "n": p["n"], "n_months": p["n_months"], "model": p["model"], "rule": p["rule"], "diff": p["diff"],
               "ci": p["ci"], "wins": p["wins"], "losses": p["losses"], "ties": p["ties"], "counts_tol": [p["wins_tol"], p["losses_tol"], p["ties_tol"]],
               "verdict": p["verdict"], "models_md": md[2:8], "match": ok, "counts_bit_exact_match": ok_exact_counts}
        C_CMP["rows"].append(row)
        if not ok:
            C_CMP["mismatch"].append(row)
        say(f"{m:8s} vs {c:30s} fark {fmt_s(p['diff'])} {fmt_ci(p['ci'])} n={p['n']} ({p['n_months']} ay) model {p['model']:.4f} karş. {p['rule']:.4f} "
            f"{p['wins']}/{p['losses']}/{p['ties']} (|d|≤1e-12 eşitlik: {p['wins_tol']}/{p['losses_tol']}/{p['ties_tol']}) → {p['verdict']}  MODELS.md {'✓' if ok else '✗ ' + str(md[2:8])}")
i = 0
for h in (3, 5, 10):
    for kind in ("MAE", "Brier"):
        p = PATHC[(h, kind)]
        md = md_path[i]
        i += 1
        ok = (md[2].startswith(str(p["n"])) and md[3] == f"{p['model']:.4f}" and md[4] == f"{p['rule']:.4f}" and md[5] == fmt_s(p["diff"])
              and md[6] == fmt_ci(p["ci"]) and md[7] in (f"{p['wins']} / {p['losses']} / {p['ties']}", f"{p['wins_tol']} / {p['losses_tol']} / {p['ties_tol']}"))
        ok_exact_counts = md[7] == f"{p['wins']} / {p['losses']} / {p['ties']}"
        C_CMP["checked"] += 1
        C_CMP["printed_match"] += int(ok)
        row = {"metric": f"path_D{h}_{kind}", "comparator": "ceiling_path_v0 (j = 1)", "n": p["n"], "n_months": p["n_months"], "model": p["model"],
               "rule": p["rule"], "diff": p["diff"], "ci": p["ci"], "wins": p["wins"], "losses": p["losses"], "ties": p["ties"],
               "counts_tol": [p["wins_tol"], p["losses_tol"], p["ties_tol"]], "verdict": p["verdict"], "models_md": md[2:8], "match": ok,
               "counts_bit_exact_match": ok_exact_counts}
        C_CMP["rows"].append(row)
        if not ok:
            C_CMP["mismatch"].append(row)
        say(f"path D{h:<2d} {kind:5s} vs ceiling_path_v0 j=1        fark {fmt_s(p['diff'])} {fmt_ci(p['ci'])} n={p['n']} model {p['model']:.4f} "
            f"karş. {p['rule']:.4f} {p['wins']}/{p['losses']}/{p['ties']} → {p['verdict']}  MODELS.md {'✓' if ok else '✗ ' + str(md[2:8])}")
for idx, k in enumerate(range(3, 10)):
    p = CELLS[(f"brier{k}", "ceiling_hazard_v0")]
    md = md_expl[idx]
    ok = (md[0] == str(k) and md[1].startswith(str(p["n"])) and md[2] == f"{p['model']:.4f}" and md[3] == f"{p['rule']:.4f}" and md[4] == fmt_s(p["diff"])
          and md[5] == fmt_ci(p["ci"]) and md[6] in (f"{p['wins']} / {p['losses']} / {p['ties']}", f"{p['wins_tol']} / {p['losses_tol']} / {p['ties_tol']}"))
    ok_exact_counts = md[6] == f"{p['wins']} / {p['losses']} / {p['ties']}"
    C_CMP["checked"] += 1
    C_CMP["printed_match"] += int(ok)
    row = {"metric": f"brier{k} (keşif)", "comparator": "ceiling_hazard_v0", "n": p["n"], "model": p["model"], "rule": p["rule"], "diff": p["diff"],
           "ci": p["ci"], "wins": p["wins"], "losses": p["losses"], "ties": p["ties"], "counts_tol": [p["wins_tol"], p["losses_tol"], p["ties_tol"]],
           "verdict": p["verdict"], "models_md": md[1:7], "match": ok, "counts_bit_exact_match": ok_exact_counts}
    C_CMP["rows"].append(row)
    if not ok:
        C_CMP["mismatch"].append(row)
    say(f"keşif brier{k} vs ceiling_hazard_v0          fark {fmt_s(p['diff'])} {fmt_ci(p['ci'])} n={p['n']} {p['wins']}/{p['losses']}/{p['ties']} "
        f"(|d|≤1e-12 eşitlik: {p['wins_tol']}/{p['losses_tol']}/{p['ties_tol']}) → {p['verdict']}  MODELS.md {'✓' if ok else '✗ ' + str(md[1:7])}")
say(f"MODELS.md ile basılı hassasiyette eşleşen hücre: {C_CMP['printed_match']}/{C_CMP['checked']} (15 §4 + 6 path + 7 keşif); "
    f"kazanç/kayıp/eşitlik bit-eşit sayımla eşleşen: {sum(1 for r in C_CMP['rows'] if r['counts_bit_exact_match'])}/{C_CMP['checked']} "
    f"(eşleşmeyenler yalnız λ = INF fold'larının eşitliği; bağımsız refit bit-eşit değil, |Δ| ~1e-16)")
OUT["c_cells"] = C_CMP

# kalibrasyon
LS = [f["realized_L"] for f in OKF]
cal = {"n": len(OKF), "mean_h2": statistics.mean(f["hazard"][1] for f in OKF), "observed_break_d2": statistics.mean(float(x == 1) for x in LS),
       "cmp_mean_h2": statistics.mean(1 - float(SRC_BY[f["ticker"]]["S_2"]) / float(SRC_BY[f["ticker"]]["S_1"]) for f in OKF), "k": {}}
for k in (2, 3, 5, 10):
    cal["k"][k] = {"model": statistics.mean(f["S_cond"][k] for f in OKF),
                   "comparator": statistics.mean(float(SRC_BY[f["ticker"]][f"S_{k}"]) / float(SRC_BY[f["ticker"]]["S_1"]) for f in OKF),
                   "observed": statistics.mean(float(x >= k) for x in LS)}
say(f"kalibrasyon: ort(h_2) model {cal['mean_h2']:.4f} / karş. {cal['cmp_mean_h2']:.4f} / gözlenen {cal['observed_break_d2']:.4f}; "
    + "; ".join(f"k={k}: {v['model']:.4f}/{v['comparator']:.4f}/{v['observed']:.4f}" for k, v in cal["k"].items()))
OUT["calibration"] = cal

# ============================================================ 10. §5'in 18 satırı (kendi okumamla), (a)–(d), çok iyi, canlı akış
say("\n=== (d) §5'in 18 satırı, başarısızlık (a)–(d), 'çok iyi', canlı akış koşulu (bağımsız değerlendirme) ===")
lam_counts = Counter("INF" if f["selected_lambda"] == INF else f["selected_lambda"] for f in OKF)
n_inf = lam_counts["INF"]
early20 = OKF[:20]
early_inf = sum(1 for f in early20 if f["selected_lambda"] == INF)
finite = [f for f in OKF if f["selected_lambda"] != INF]
lock_active = [f for f in finite if "d1_lock" in f["columns"]]
lock_neg = sum(1 for f in lock_active if f["delta"]["d1_lock"] < 0)
turn_pos = sum(1 for f in finite if f["delta"]["d1_turnover"] > 0)
prim = CELLS[("rps", "ceiling_hazard_v0")]
b2 = CELLS[("brier2", "ceiling_hazard_v0")]


def in_range(x, lo, hi):
    return lo <= x <= hi


def diff_row(name, p, lo, hi, firm):
    """firm: 'includes' | 'excl_neg' | 'not_pos' | 'may' | None (yalnız fark aralığı)."""
    if p["diff"] < lo:
        lab = "tutmadı (daha iyi)"
    elif p["diff"] > hi:
        lab = "tutmadı (daha kötü)"
    else:
        ok = {"includes": p["ci"][0] <= 0 <= p["ci"][1], "excl_neg": p["ci"][1] < 0, "not_pos": p["ci"][0] <= 0, "may": p["ci"][0] <= 0, None: True}[firm]
        lab = "tuttu" if ok else "tutmadı (aralık)"
    return {"row": name, "expected": [lo, hi], "got": p["diff"], "ci": p["ci"], "label": lab}


ROWS18 = [
    diff_row("RPS_1 vs ceiling_hazard_v0 (BİRİNCİL)", prim, -0.020, 0.003, None),
    diff_row("RPS_1 vs @INF", CELLS[("rps", "ceiling_hazard_v0@INF")], -0.055, -0.015, "may"),
    diff_row("RPS_1 vs base_km_expanding", CELLS[("rps", "base_km_expanding")], -0.060, -0.020, "may"),
    diff_row("RPS_1 vs base_km_last10", CELLS[("rps", "base_km_last10")], -0.065, -0.025, "may"),
    diff_row("RPS_1 vs her-zaman-tavan", CELLS[("rps", "base_always_ceiling__ceiling")], -0.42, -0.36, "excl_neg"),
    diff_row("Brier k=2 vs ceiling_hazard_v0", b2, -0.025, 0.000, "not_pos"),
    diff_row("Brier k=2 vs @INF", CELLS[("brier2", "ceiling_hazard_v0@INF")], -0.040, -0.010, "may"),
    diff_row("Brier k=2 vs base_km_last10", CELLS[("brier2", "base_km_last10")], -0.065, -0.030, "may"),
    diff_row("Brier k=10 vs ceiling_hazard_v0", CELLS[("brier10", "ceiling_hazard_v0")], -0.006, 0.006, "includes"),
    diff_row("Brier k=3 (keşif) vs ceiling_hazard_v0", CELLS[("brier3", "ceiling_hazard_v0")], -0.020, 0.003, "includes"),
    diff_row("path h=5 MAE", PATHC[(5, "MAE")], -0.015, 0.005, "includes"),
    diff_row("path h=3 p_up Brier", PATHC[(3, "Brier")], -0.015, 0.005, "includes"),
]
cal_d = cal["mean_h2"] - cal["observed_break_d2"]
ROWS18.append({"row": "Kalibrasyon |ort(h_2) − gözlenen| ≤ 0.05", "got": cal_d, "label": "tuttu" if abs(cal_d) <= 0.05 else "tutmadı"})
fl = FINFIT["lambda"]
ROWS18.append({"row": "λ nihai fit 10–100 en olası; INF olası", "got": fl, "label": "tuttu" if (10 <= fl <= 100 or fl == INF) else "tutmadı"})
share_inf = n_inf / len(OKF)
part_early = early_inf / 20 > 0.5
part_share = 0.20 <= share_inf <= 0.50
ROWS18.append({"row": "λ fold'lar: erken fold'larda INF; %20–50'sinde INF", "got": f"INF {n_inf}/{len(OKF)} ({share_inf:.0%}); ilk 20'de {early_inf}",
               "label": "tuttu" if (part_early and part_share) else ("tutmadı" if not (part_early or part_share) else "kısmen")})
ROWS18.append({"row": "δ_lock < 0 (nihai; λ<INF fold'ların ≥ %80'i)", "got": f"nihai {FINFIT['delta']['d1_lock']:+.4f}; {lock_neg}/{len(lock_active)}",
               "label": "tuttu" if (FINFIT["delta"]["d1_lock"] < 0 and lock_neg / max(1, len(lock_active)) >= 0.8) else "tutmadı"})
ROWS18.append({"row": "δ_turn > 0 (nihai)", "got": FINFIT["delta"]["d1_turnover"], "label": "tuttu" if FINFIT["delta"]["d1_turnover"] > 0 else "tutmadı"})
ROWS18.append({"row": "n (fold) 65–71", "got": prim["n"], "label": "tuttu" if 65 <= prim["n"] <= 71 else "tutmadı"})
for r in ROWS18:
    say(f"  {r['row']:52s} → {r['label']:22s} gerçekleşen {r['got'] if not isinstance(r['got'], float) else f'{r['got']:+.4f}'}"
        + (f" {fmt_ci(r['ci'])}" if "ci" in r else ""))
lab_counts = Counter(r["label"].split(" (")[0] for r in ROWS18)
say(f"etiketler: {dict(lab_counts)}")
too_good = {"primary_diff_lt_-0.040": prim["diff"] < -0.040, "primary_ci_hi_lt_-0.020": prim["ci"][1] < -0.020, "brier2_diff_lt_-0.040": b2["diff"] < -0.040}
fail = {"a": prim["ci"][0] > 0, "b": fl == INF or share_inf >= 0.80, "c": len(OKF) >= 30 and abs(cal_d) > 0.10,
        "d": (h1_text_eq != len(OKF)) or d_inf_opus != 0.0}
live_flow = "kurulmaz" if fail["b"] else "kurulur"
gains = {"rps": prim["diff"], "brier2": b2["diff"], "brier3": CELLS[("brier3", "ceiling_hazard_v0")]["diff"], "brier10": CELLS[("brier10", "ceiling_hazard_v0")]["diff"]}
say(f"çok iyi: {too_good} → TETİKLENDİ: {any(too_good.values())}")
say(f"başarısızlık: {fail}; (b) paydası FIT_OK {len(OKF)} (INSUFFICIENT {sum(1 for f in FOLDS if f['status'] == 'INSUFFICIENT_TRAINING_HISTORY')}, "
    f"NOT_APPLICABLE {sum(1 for f in FOLDS if f['status'] == 'NOT_APPLICABLE')} paydada değil); INF {n_inf}/{len(OKF)} = {share_inf:.1%}; nihai λ = {fl}")
say(f"canlı akış koşulu: {live_flow}; 'kazanç en olası Brier k=2' → {min(gains, key=gains.get) == 'brier2'} {gains}")
OUT["d_evaluation"] = {"rows18": ROWS18, "labels": dict(lab_counts), "too_good": too_good, "failures": fail, "live_flow": live_flow,
                       "lambda_counts": {str(k): v for k, v in lam_counts.items()}, "early20_inf": early_inf, "lock_neg": [lock_neg, len(lock_active)],
                       "turn_pos": [turn_pos, len(finite)], "gains": gains, "final_lambda": fl}

# ============================================================ 11. tanı (model seçimine girmez)
say("\n=== Tanı: Brier k = 2 kazancı nereden geliyor? ===")
d2 = b2["diffs"]
DIAG = {}
by_lock = {}
for f in OKF:
    by_lock.setdefault("kilitli" if f["test_lock"] else "kilitsiz", []).append(d2[f["ticker"]])
DIAG["by_lock"] = {g: {"n": len(v), "mean_diff": sum(v) / len(v), "sum_diff": sum(v), "share": sum(v) / sum(d2.values())} for g, v in by_lock.items()}
say("kilit gruplarına göre (fark toplamı payı): " + json.dumps({g: {k: round(x, 4) for k, x in d.items()} for g, d in DIAG["by_lock"].items()}))
# gerçekleşen D2 kırılma oranı kilit gruplarında
for g, sel in (("kilitli", [f for f in OKF if f["test_lock"]]), ("kilitsiz", [f for f in OKF if not f["test_lock"]])):
    obs = statistics.mean(float(f["realized_L"] == 1) for f in sel)
    mh = statistics.mean(f["hazard"][1] for f in sel)
    ch = statistics.mean(1 - float(SRC_BY[f["ticker"]]["S_2"]) / float(SRC_BY[f["ticker"]]["S_1"]) for f in sel)
    DIAG[f"d2_{g}"] = {"n": len(sel), "observed_break": obs, "model_mean_h2": mh, "comparator_mean_h2": ch}
    say(f"  {g}: n={len(sel)} gözlenen D2 kırılma {obs:.3f}; ort h_2 model {mh:.3f} / karşılaştırıcı {ch:.3f}")


def reliability_resolution(probs, ys, bins):
    """Brier = güvenilirlik − çözünürlük + belirsizlik (Murphy). bins: p -> grup anahtarı."""
    n = len(probs)
    ybar = sum(ys) / n
    groups = {}
    for p, y in zip(probs, ys):
        groups.setdefault(bins(p), []).append((p, y))
    rel = sum(len(g) * (statistics.mean(p for p, _ in g) - statistics.mean(y for _, y in g)) ** 2 for g in groups.values()) / n
    res = sum(len(g) * (statistics.mean(y for _, y in g) - ybar) ** 2 for g in groups.values()) / n
    unc = ybar * (1 - ybar)
    return {"brier": sum((p - y) ** 2 for p, y in zip(probs, ys)) / n, "reliability": rel, "resolution": res, "uncertainty": unc,
            "n_groups": len(groups)}


ys = [float(f["realized_L"] == 1) for f in OKF]
pm = [f["hazard"][1] for f in OKF]
pc = [1 - float(SRC_BY[f["ticker"]]["S_2"]) / float(SRC_BY[f["ticker"]]["S_1"]) for f in OKF]
bins5 = lambda p: min(int(p * 20), 19)  # noqa: E731  0.05 genişliğinde kutular
DIAG["murphy_model"] = reliability_resolution(pm, ys, bins5)
DIAG["murphy_comparator"] = reliability_resolution(pc, ys, bins5)
DIAG["murphy_model_lockbins"] = reliability_resolution(pm, ys, lambda p: 0)   # tek grup: yalnız kalibrasyon açığı
DIAG["murphy_comparator_lockbins"] = reliability_resolution(pc, ys, lambda p: 0)
say(f"  Murphy (0.05 kutu): model {json.dumps({k: round(v, 4) for k, v in DIAG['murphy_model'].items()})}")
say(f"                      karş. {json.dumps({k: round(v, 4) for k, v in DIAG['murphy_comparator'].items()})}")
# ortalama kalibrasyon açığının payı: (ort p − ort y)²
DIAG["mean_bias_sq"] = {"model": (statistics.mean(pm) - statistics.mean(ys)) ** 2, "comparator": (statistics.mean(pc) - statistics.mean(ys)) ** 2}
say(f"  ortalama kalibrasyon açığı²: model {DIAG['mean_bias_sq']['model']:.4f}, karş. {DIAG['mean_bias_sq']['comparator']:.4f} "
    f"(toplam Brier farkı {b2['diff']:+.4f})")
# karşılaştırıcının h_2'si sabit kaydırılsa (kalibrasyon düzeltmesi) Brier ne olurdu? -> ayırt etme payı
shift = statistics.mean(ys) - statistics.mean(pc)
DIAG["comparator_recalibrated_brier"] = sum((min(max(p + shift, 0), 1) - y) ** 2 for p, y in zip(pc, ys)) / len(ys)
say(f"  karşılaştırıcı h_2 ortalamaya kaydırılsa (+{shift:.4f}) Brier {DIAG['comparator_recalibrated_brier']:.4f} vs model {b2['model']:.4f} "
    f"(kalan fark = ayırt etme payı {b2['model'] - DIAG['comparator_recalibrated_brier']:+.4f})")
years = {}
for f in OKF:
    years.setdefault(FTD[f["ticker"]][:4], []).append(d2[f["ticker"]])
DIAG["by_year"] = {y: {"n": len(v), "mean_diff": sum(v) / len(v), "sum_diff": sum(v)} for y, v in sorted(years.items())}
say("  yıllara göre: " + json.dumps({y: {k: round(x, 4) for k, x in d.items()} for y, d in DIAG["by_year"].items()}))
top = sorted(d2.items(), key=lambda kv: kv[1])[:10]
DIAG["top10"] = [{"ticker": t, "ftd": FTD[t], "L": L[t], "lock": D1F[t]["lock"], "turnover_ratio": D1F[t]["ratio"],
                  "h2_model": next(f for f in OKF if f["ticker"] == t)["hazard"][1],
                  "h2_cmp": 1 - float(SRC_BY[t]["S_2"]) / float(SRC_BY[t]["S_1"]), "diff": d} for t, d in top]
say("  en çok katkı veren 10 arz: " + "; ".join(f"{r['ticker']}(L={r['L']},kilit={r['lock']},oran={r['turnover_ratio']:.3g},h2 {r['h2_model']:.2f} vs {r['h2_cmp']:.2f},Δ={r['diff']:+.3f})" for r in DIAG["top10"]))
# k = 10 kötüleşmesi ve path D10
d10 = CELLS[("brier10", "ceiling_hazard_v0")]["diffs"]
DIAG["k10"] = {"by_L10": {}, "by_lock": {}}
for f in OKF:
    DIAG["k10"]["by_L10"].setdefault("L=10" if f["realized_L"] >= 10 else "L<10", []).append(d10[f["ticker"]])
    DIAG["k10"]["by_lock"].setdefault("kilitli" if f["test_lock"] else "kilitsiz", []).append(d10[f["ticker"]])
DIAG["k10"] = {grp: {g: {"n": len(v), "sum_diff": sum(v), "mean_diff": sum(v) / len(v)} for g, v in d.items()} for grp, d in DIAG["k10"].items()}
say("  k=10 farkı: " + json.dumps({grp: {g: {k: round(x, 4) for k, x in dd.items()} for g, dd in d.items()} for grp, d in DIAG["k10"].items()}))
say(f"  k=10: ort S_cond_10 model {cal['k'][10]['model']:.4f} / karş. {cal['k'][10]['comparator']:.4f} / gözlenen {cal['k'][10]['observed']:.4f}; "
    f"kilitli arzlarda ort S_cond_10 model {statistics.mean(f['S_cond'][10] for f in OKF if f['test_lock']):.4f} karş. "
    f"{statistics.mean(float(SRC_BY[f['ticker']]['S_10']) / float(SRC_BY[f['ticker']]['S_1']) for f in OKF if f['test_lock']):.4f}")
pd10 = PATHC[(10, "MAE")]["diffs"]
DIAG["path_d10"] = {"by_L10": {}, "median_eq_rho10": 0}
for f in OKF:
    DIAG["path_d10"]["by_L10"].setdefault("L=10" if f["realized_L"] >= 10 else "L<10", []).append(pd10[f["ticker"]])
DIAG["path_d10"]["by_L10"] = {g: {"n": len(v), "sum_diff": sum(v), "mean_diff": sum(v) / len(v)} for g, v in DIAG["path_d10"]["by_L10"].items()}
n_rho = sum(1 for f in OKF if f["path"][10]["median"] == limit_path(P_OF[f["ticker"]])[1][9])
n_rho_c = sum(1 for f in OKF if f["path_cmp"][10]["median"] == limit_path(P_OF[f["ticker"]])[1][9])
DIAG["path_d10"]["median_eq_rho10"] = {"model": n_rho, "comparator": n_rho_c}
say(f"  path D10 MAE farkı: {json.dumps({g: {k: round(x, 4) for k, x in d.items()} for g, d in DIAG['path_d10']['by_L10'].items()})}; "
    f"medyan = ρ_10 (tam limit yolu) olan fold: model {n_rho}, karş. {n_rho_c}")
OUT["diagnosis"] = DIAG

# ============================================================ 12. duyarlılık (bilgi; model DEĞİL)
say("\n=== Duyarlılık (bilgi; model değil, şartname değişmez): yalnız d1_lock / yalnız d1_turnover ===")
SENS = {}
for name, cols in (("lock_only", ("d1_lock",)), ("turnover_only", ("d1_turnover",))):
    t0 = time.time()
    folds_s = [run_fold(r["ticker"], columns=cols, with_path=False) for r in SRC]
    ok_s = [f for f in folds_s if f["status"] == "FIT_OK"]
    p_rps = cell("rps", "ceiling_hazard_v0", ok_s)
    p_b2 = cell("brier2", "ceiling_hazard_v0", ok_s)
    p_b10 = cell("brier10", "ceiling_hazard_v0", ok_s)
    lamc = Counter("INF" if f["selected_lambda"] == INF else f["selected_lambda"] for f in ok_s)
    SENS[name] = {"columns": list(cols), "primary": {k: v for k, v in p_rps.items() if k != "diffs"}, "brier2": {k: v for k, v in p_b2.items() if k != "diffs"},
                  "brier10": {k: v for k, v in p_b10.items() if k != "diffs"}, "lambda_counts": {str(k): v for k, v in lamc.items()},
                  "n_fit_ok": len(ok_s), "folds": folds_s, "seconds": time.time() - t0}
    say(f"{name:14s} birincil RPS_1 fark {fmt_s(p_rps['diff'])} {fmt_ci(p_rps['ci'])} n={p_rps['n']}; Brier k=2 {fmt_s(p_b2['diff'])} {fmt_ci(p_b2['ci'])}; "
        f"Brier k=10 {fmt_s(p_b10['diff'])} {fmt_ci(p_b10['ci'])}; λ {dict(lamc)}")
OUT["sensitivity"] = {k: {kk: vv for kk, vv in v.items() if kk != "folds"} for k, v in SENS.items()}

# ============================================================ 13. çıktı dosyaları
assert not any(m == "borsai" or m.startswith("borsai.") for m in sys.modules), "borsai import edilmiş!"
LEDGER_COLS = ("model_id,fold_id,ticker,first_trading_date,prediction_date,training_n_ipo,training_n_pp_rows,training_n_events,training_n_survivals,"
               "training_max_session_date,training_tickers_sha256,training_pp_sha256,parent_fold_status,parent_gamma_g1,parent_gamma_g2,parent_gamma_g3,"
               "parent_beta_f1,parent_beta_f2,parent_beta_f3,parent_selected_lambda,parent_ledger_row_sha256,selected_lambda,lambda_score_table,"
               "n_lambda_not_converged,columns,delta_d1_lock,delta_d1_turnover,d1_clip_p05,d1_clip_p95,d1_mean_lock,d1_std_lock,d1_mean_turnover,"
               "d1_std_turnover,solver_iterations,solver_grad_max,test_d1_lock,test_d1_turnover_ratio,test_d1_turnover_clipped").split(",")
LEDGER_COLS += [f"hazard_{k}" for k in range(1, 11)] + [f"S_{k}" for k in range(1, 11)] + [f"S_cond_{k}" for k in range(2, 11)]
LEDGER_COLS += ["path_cond_status"] + [f"path_cond_h{h}_{x}" for h in (3, 5, 10) for x in ("median", "p_up")] + ["realized_L", "status"]


def write_ledger(path, folds, model_id):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=LEDGER_COLS, lineterminator="\n")
        w.writeheader()
        for f in folds:
            row = {c: "" for c in LEDGER_COLS}
            row.update(model_id=model_id, fold_id=f["fold_id"], ticker=f["ticker"], first_trading_date=FTD[f["ticker"]], prediction_date=f["T"],
                       parent_fold_status="FIT_OK", realized_L=f["realized_L"], status=f["status"])
            if f["status"] != "NOT_APPLICABLE":
                row.update(training_n_ipo=f["n_ipo"], training_n_pp_rows=f["n_pp_rows"], training_n_events=f["n_events"], training_n_survivals=f["n_survivals"],
                           training_max_session_date=f["max_session_date"], training_tickers_sha256=f["tickers_sha256"], training_pp_sha256=f["pp_sha256"],
                           parent_gamma_g1=f["parent_gamma"][0], parent_gamma_g2=f["parent_gamma"][1], parent_gamma_g3=f["parent_gamma"][2],
                           parent_beta_f1=f["parent_beta"].get("f1", 0.0), parent_beta_f2=f["parent_beta"].get("f2", 0.0), parent_beta_f3=f["parent_beta"].get("f3", 0.0),
                           parent_selected_lambda="INF" if f["parent_lambda"] == INF else f["parent_lambda"])
            if f["status"] == "FIT_OK":
                row.update(selected_lambda="INF" if f["selected_lambda"] == INF else f["selected_lambda"],
                           lambda_score_table=json.dumps([{"lambda": ("INF" if l == INF else l), "score": f["score"][l], "status": "SCORED"} for l in LAMBDA_GRID], separators=(",", ":")),
                           n_lambda_not_converged=0, columns=json.dumps(f["columns"]), solver_iterations=f["iterations"], solver_grad_max=f["grad_max"],
                           test_d1_lock=f["test_lock"], test_d1_turnover_clipped="TRUE" if f["test_clipped"] else "FALSE", **mine_row(f))
                if "path" in f:
                    row["path_cond_status"] = f["path_status"]
                    for h in (3, 5, 10):
                        if f["path"][h] is not None:
                            row[f"path_cond_h{h}_median"] = f["path"][h]["median"]
                            row[f"path_cond_h{h}_p_up"] = f["path"][h]["p_up"]
            w.writerow(row)


write_ledger(OUT_DIR / "repro_post_d1_fold_ledger.csv", FOLDS, "post_d1_hazard_v0")
for name, v in SENS.items():
    write_ledger(OUT_DIR / f"sens_{name}_fold_ledger.csv", v["folds"], f"post_d1_hazard_v0__sens_{name}")
# duyarlılık günlüğü (experiments/log.jsonl biçimi; kind: sensitivity)
LOG65 = json.loads((ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines()[64])
assert LOG65["model_id"] == "post_d1_hazard_v0"
with open(OUT_DIR / "sensitivity_runs.jsonl", "w", encoding="utf-8") as fh:
    for name, v in SENS.items():
        entry = {"kind": "sensitivity", "context": "fable_faz5_audit_sensitivity", "model_id": f"post_d1_hazard_v0__sens_{name}",
                 "base_model_id": "post_d1_hazard_v0", "stage": "POST_D1", "spec_sha256": LOG65["spec_sha256"],
                 "spec_document": LOG65["spec_document"], "spec_document_sha256": LOG65["spec_document_sha256"],
                 "plan_id": LOG65["plan_id"] + "__SENS_" + name.upper(), "variation": {"d1_columns": v["columns"], "note": "şartname dışı; model değil; dondurulmaz"},
                 "data_version_sha256": LOG65["data_version_sha256"], "training_table_sha256": LOG65["training_table_sha256"],
                 "survival_ledger_sha256": LOG65["survival_ledger_sha256"], "sessions_file_sha256": sha_file(SESS_PATH),
                 "folds_total": 87, "folds_scorable": {"POST_D1": v["n_fit_ok"]}, "ledger_file": f"docs/fable_faz5_audit/ekler/sens_{name}_fold_ledger.csv",
                 "ledger_sha256": sha_file(OUT_DIR / f"sens_{name}_fold_ledger.csv"),
                 "metrics": {"scale": "backtest_conditional", "j": 1, "n": v["primary"]["n"], "rps_cond": v["primary"]["model"],
                             "brier_cond_k2": v["brier2"]["model"], "brier_cond_k10": v["brier10"]["model"],
                             "primary_vs_ceiling_hazard_v0": {"diff": v["primary"]["diff"], "ci95": v["primary"]["ci"], "n": v["primary"]["n"]},
                             "brier2_vs_ceiling_hazard_v0": {"diff": v["brier2"]["diff"], "ci95": v["brier2"]["ci"], "n": v["brier2"]["n"]},
                             "lambda_counts": v["lambda_counts"]},
                 "code": "docs/fable_faz5_audit/ekler/repro_post_d1.py (bağımsız betik; borsai import edilmedi)",
                 "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "seconds": round(v["seconds"], 1), "audit_task": "BORSAI_FAZ5_FABLE_REPRO_AUDIT_20260924"}
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
OUT["inputs_sha256"] = {str(p.relative_to(ROOT)): sha_file(p) for p in (ROOT / "data" / "training_table.csv", SESS_PATH,
                                                                          RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv",
                                                                          ROOT / "models" / "ceiling_hazard_v0.json",
                                                                          GOLD5 / "post_d1_hazard_v0_fold_ledger.csv",
                                                                          GOLD5 / "post_d1_hazard_v0_final_fit_preview.json")}
OUT["inputs_sha256"].update({f"faz1b:{k}": sha_file(GOLD1B / f"{k}_fold_ledger.csv") for k in LED1B})
OUT["seconds"] = time.time() - T0
(OUT_DIR / "repro_output.json").write_text(json.dumps(OUT, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
(OUT_DIR / "repro_stdout.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
say(f"DONE ({OUT['seconds']:.0f} s); borsai in sys.modules: {any(m.startswith('borsai') for m in sys.modules)}")

"""Bağımsız sızıntı denetimi ve fold yeniden üretimi (BORSAI_FAZ1B_FABLE_CONFORMITY_20260922).

borsai/ paketi İMPORT EDİLMEZ. Yalnız ham veri dosyaları + numpy/scipy/sklearn.
Karşılaştırma hedefi: tests/reference/macos_golden_faz1b/*_fold_ledger.csv ve models/*.json.

Bölümler:
  A. Fold planı (tavan T-kesimi, PB-tavan B-kesimi, PB B-kesimi, V1.5 T-kesimi): TÜM fold'larda
     eğitim kümesi ve PP satır kümesi hash'i ledger ile karşılaştırılır (sha256("\n".join + "\n")).
  B. ceiling_hazard_v0: 3 fold (erken/orta/geç) + kırpmalı bir fold sıfırdan: ön işleme, λ iç CV,
     Newton (kendi) + scipy çapraz kontrol, S_k, P_close, reclose.
  C. pb_ceiling_v0: 2 fold sıfırdan.
  D. KM kuralları: 87+87 fold'da S_k yeniden üretimi.
  E. pb_v0: 1 fold (D5|ARMGD) sıfırdan (sklearn Ridge/Logit, V1.6 ızgarası, iç LOOCV).
  F. v1_5_market20_v0: 1 fold (D5|ARMGD) sıfırdan + f6'nın yalnız S0 < T kayıtlarından geldiği.
  G. Nihai (dondurulmuş) hazard modellerinin yeniden fit'i ve JSON ile karşılaştırma.
  H. Ledger'dan RPS eşleşik farkları ve blok bootstrap aralığı (MODELS.md sayıları).
"""
from __future__ import annotations

import bisect
import csv
import hashlib
import json
import math
import random
import sys
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal, localcontext, Context, ROUND_HALF_EVEN
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from sklearn.linear_model import LogisticRegression, Ridge

ROOT = Path("/Users/ahmet/Desktop/BorsAi")
RAW = ROOT / "data" / "raw"
GOLD = ROOT / "tests" / "reference" / "macos_golden_faz1b"
GOLD_A = ROOT / "tests" / "reference" / "macos_golden"

INF = math.inf
LAMBDA_GRID = (0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, INF)
GROUP = {1: 0, 2: 1, 3: 1, **{d: 2 for d in range(4, 11)}}
RECLOSE = {**{k: "a" for k in (2, 3, 4)}, **{k: "b" for k in range(5, 11)}}
CTX28 = Context(prec=28, rounding=ROUND_HALF_EVEN)

OUT: dict = {}


def say(*a):
    print(*a, flush=True)


def rd(path, enc="utf-8-sig"):
    with open(path, encoding=enc, newline="") as fh:
        return list(csv.DictReader(fh))


def ihash(items):
    return hashlib.sha256(("\n".join(items) + "\n").encode()).hexdigest()


# ---------------------------------------------------------------- veri
T = rd(ROOT / "data" / "training_table.csv")
M = {r["ticker"]: r for r in rd(RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv")}
SES = rd(RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv")
TG = rd(RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv")
PB = {r["ticker"]: r for r in rd(RAW / "PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv")}
sd = {}
for s in SES:
    sd.setdefault(s["ticker"], {})[int(s["session_number"])] = s["target_session_date"]
tgd = {(t["ticker"], t["horizon"]): t["target_session_date"] for t in TG}
ORDER = [r["ticker"] for r in T]  # (first_trading_date, ticker) sırası
assert ORDER == [t for _, t in sorted((r["first_trading_date"], r["ticker"]) for r in T)]
ROW = {r["ticker"]: r for r in T}
FTD = {t: ROW[t]["first_trading_date"] for t in ORDER}
L = {t: int(ROW[t]["ceiling_streak_L"]) for t in ORDER}
CLOSE = {t: [int(ROW[t][f"ceiling_close_D{k}"]) for k in range(1, 11)] for t in ORDER}
SESS = {t: [sd[t][k] for k in range(1, 11)] for t in ORDER}
BB = {t: PB[t]["first_bookbuilding_date"] for t in ORDER}
F3_PRESENT = [t for t in ORDER if ROW[t]["total_demand_multiple"] != ""]
assert len(F3_PRESENT) == 97


# ---------------------------------------------------------------- özellikler (ham)
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
    f4 = pct(Decimal(r["capital_increase_shares"]), Decimal(r["shares_offered"]))
    return {"f1": float(f1), "f2": f2, "f3": f3, "f4": f4}


def pb_raw(t):
    r = PB[t]
    D = lambda f: Decimal(r[f])  # noqa: E731
    base, post = D("planned_base_offer_shares"), D("planned_post_ipo_capital")
    with localcontext(Context(prec=60, rounding=ROUND_HALF_EVEN)):
        pb1 = float((D("ipo_price_try") * base).ln())
    pb2 = float(Fraction(base) / Fraction(post) * 100)
    pb3 = float(Fraction(D("planned_capital_increase_shares")) / Fraction(base) * 100)
    return {"pb1": pb1, "pb2": pb2, "pb3": pb3}


V15 = {t: v15_raw(t) for t in ORDER}
PBF = {t: pb_raw(t) for t in ORDER}


def q7(vals, p):
    vals = sorted(vals)
    n = len(vals)
    h = (n - 1) * p
    lo = math.floor(h)
    if lo >= n - 1:
        return vals[-1]
    return vals[lo] + (h - lo) * (vals[lo + 1] - vals[lo])


class Prep:
    """Arz düzeyinde ön işleme. recipe: 'ceiling' (f1 ln, f3 clip, z), 'pb' (z), 'v15' (V1.3: f3 winsor+medyan, f5, f1 ln, z)."""

    def __init__(self, tickers, raw, recipe):
        self.recipe = recipe
        self.cols = []
        X = {}
        if recipe == "ceiling":
            f3s = [raw[t]["f3"] for t in tickers]
            assert all(v is not None for v in f3s)
            self.lo, self.hi = q7(f3s, 0.05), q7(f3s, 0.95)
            for t in tickers:
                X[t] = {"f1": math.log(raw[t]["f1"]), "f2": raw[t]["f2"], "f3": min(max(raw[t]["f3"], self.lo), self.hi)}
            cand = ["f1", "f2", "f3"]
        elif recipe == "pb":
            for t in tickers:
                X[t] = dict(raw[t])
            cand = list(next(iter(raw.values())).keys())
        elif recipe == "v15":
            present = [raw[t]["f3"] for t in tickers if raw[t]["f3"] is not None]
            self.lo, self.hi = q7(present, 0.05), q7(present, 0.95)
            wins = sorted(min(max(v, self.lo), self.hi) for v in present)
            n = len(wins)
            self.med = wins[n // 2] if n % 2 else (wins[n // 2 - 1] + wins[n // 2]) / 2
            for t in tickers:
                f3 = raw[t]["f3"]
                miss = f3 is None
                X[t] = {"f1": math.log(raw[t]["f1"]), "f2": raw[t]["f2"],
                        "f3": self.med if miss else min(max(f3, self.lo), self.hi), "f4": raw[t]["f4"],
                        "f5": 1.0 if miss else 0.0}
                if "f6" in raw[t]:
                    X[t]["f6"] = raw[t]["f6"]
            cand = ["f1", "f2", "f3", "f4", "f5"] + (["f6"] if "f6" in raw[tickers[0]] else [])
        self.mean, self.std = {}, {}
        for c in cand:
            v = np.array([X[t][c] for t in tickers])
            if len(set(v.tolist())) <= 1:
                continue  # sıfır varyans -> düşer
            self.cols.append(c)
            self.mean[c], self.std[c] = float(v.mean()), float(v.std(ddof=0))
        if recipe == "v15" and "f3" not in self.cols and "f5" in self.cols:
            self.cols.remove("f5")
        self.Z = {t: self.transform_row(X[t]) for t in tickers}

    def transform_raw(self, r):
        if self.recipe == "ceiling":
            x = {"f1": math.log(r["f1"]), "f2": r["f2"], "f3": min(max(r["f3"], self.lo), self.hi)}
        elif self.recipe == "pb":
            x = dict(r)
        else:
            f3 = r["f3"]
            miss = f3 is None
            x = {"f1": math.log(r["f1"]), "f2": r["f2"], "f3": self.med if miss else min(max(f3, self.lo), self.hi),
                 "f4": r["f4"], "f5": 1.0 if miss else 0.0}
            if "f6" in r:
                x["f6"] = r["f6"]
        return self.transform_row(x)

    def transform_row(self, x):
        return np.array([(x[c] - self.mean[c]) / self.std[c] for c in self.cols])


# ---------------------------------------------------------------- PP tablosu
def pp_rows(t, cutoff=None):
    out = []
    for d in range(1, 11):
        if d - 1 > L[t]:
            break
        if cutoff is not None and SESS[t][d - 1] >= cutoff:
            break
        out.append((t, d, GROUP[d], 1 if L[t] == d - 1 else 0))
    return out


def reclose(tickers, cutoff):
    n = {"a": 0, "b": 0}
    a = {"a": 0, "b": 0}
    for t in tickers:
        for k in range(2, 11):
            if L[t] < k and (cutoff is None or SESS[t][k - 1] < cutoff):
                n[RECLOSE[k]] += 1
                a[RECLOSE[k]] += CLOSE[t][k - 1]
    return {"n_a": n["a"], "a_a": a["a"], "r_a": (a["a"] + 0.5) / (n["a"] + 1),
            "n_b": n["b"], "a_b": a["b"], "r_b": (a["b"] + 0.5) / (n["b"] + 1)}


def ceiling_fold(k, plan):
    """plan 'ceiling': f3 dolu arzlar, kesim T; 'pb_ceiling': 99 arz, kesim B."""
    pool = F3_PRESENT if plan == "ceiling" else ORDER
    c = FTD[k] if plan == "ceiling" else BB[k]
    rows = [r for j in pool if FTD[j] < c for r in pp_rows(j, c)]
    training = list(dict.fromkeys(r[0] for r in rows))
    ev = sum(r[3] for r in rows)
    ok = len(training) >= 10 and ev >= 5 and len(rows) - ev >= 5
    return c, rows, training, ok


# ---------------------------------------------------------------- hazard fit
def fit_hazard(rows, Z, lam, p):
    """rows: (t,d,g,e); Z: t -> z vektörü (p boyutlu). Pseudo satırlar dahil. Kendi Newton'um + scipy çapraz."""
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


def scipy_check(rows, Z, lam, p, theta_mine):
    g = np.array([r[2] for r in rows])
    e = np.array([r[3] for r in rows], dtype=float)
    X = np.zeros((len(rows) + 6, 3 + p))
    X[np.arange(len(rows)), g] = 1.0
    X[: len(rows), 3:] = np.array([Z[r[0]] for r in rows])
    for i in range(3):
        X[len(rows) + 2 * i, i] = 1.0
        X[len(rows) + 2 * i + 1, i] = 1.0
    e = np.r_[e, np.tile([1.0, 0.0], 3)]
    w = np.r_[np.ones(len(rows)), np.full(6, 0.5)]
    pen = np.r_[np.zeros(3), np.full(p, lam)]

    def J(th):
        eta = X @ th
        return float(np.sum(w * (np.logaddexp(0, eta) - e * eta)) + 0.5 * lam * th[3:] @ th[3:])

    def grad(th):
        h = 1 / (1 + np.exp(-(X @ th)))
        return X.T @ (w * (h - e)) + pen * th

    res = minimize(J, np.zeros(3 + p), jac=grad, method="BFGS", options={"gtol": 1e-11, "maxiter": 20000})
    return float(np.max(np.abs(res.x - theta_mine)))


def hazards(gamma, beta, z):
    lin = float(beta @ z) if len(beta) else 0.0
    return [1 / (1 + math.exp(-(gamma[GROUP[d]] + lin))) for d in range(1, 11)]


def surv(h):
    out, s = [], 1.0
    for x in h:
        s *= 1 - x
        out.append(s)
    return out


def pclose(S, ra, rb):
    return [S[0]] + [S[k - 1] + (1 - S[k - 1]) * (ra if RECLOSE[k] == "a" else rb) for k in range(2, 11)]


def select_lambda(training, rows, raw, recipe):
    by = {}
    for r in rows:
        by.setdefault(r[0], []).append(r)
    tot = {lam: 0.0 for lam in LAMBDA_GRID}
    n = 0
    for j in training:
        inner = [t for t in training if t != j]
        prep = Prep(inner, raw, recipe)
        p = len(prep.cols)
        zj = prep.transform_raw(raw[j])
        irows = [r for t in inner for r in by[t]]
        for lam in LAMBDA_GRID:
            gam, bet, _ = fit_hazard(irows, prep.Z, lam, p)
            h = hazards(gam, bet, zj)
            for (_, d, _, ev) in by[j]:
                hh = min(max(h[d - 1], 1e-12), 1 - 1e-12)
                tot[lam] += -(ev * math.log(hh) + (1 - ev) * math.log(1 - hh))
        n += len(by[j])
    score = {lam: tot[lam] / n for lam in LAMBDA_GRID}
    best = min(score.values())
    sel = max(lam for lam, s in score.items() if s == best)
    return sel, score


def run_hazard_fold(k, plan, raw, recipe):
    c, rows, training, ok = ceiling_fold(k, plan)
    assert ok
    sel, score = select_lambda(training, rows, raw, recipe)
    prep = Prep(training, raw, recipe)
    p = len(prep.cols)
    gam, bet, gmax = fit_hazard(rows, prep.Z, sel, p)
    sc = scipy_check(rows, prep.Z, sel, p, np.r_[gam, bet]) if sel != INF else 0.0
    z = prep.transform_raw(raw[k])
    h = hazards(gam, bet, z)
    S = surv(h)
    rc = reclose(training, c)
    return {"cutoff": c, "n_ipo": len(training), "n_rows": len(rows), "n_events": sum(r[3] for r in rows),
            "training_sha": ihash(training), "pp_sha": ihash([f"{r[0]}|{r[1]}|{r[3]}" for r in rows]),
            "selected_lambda": sel, "score": score, "gamma": gam.tolist(), "beta": dict(zip(prep.cols, bet.tolist())),
            "grad_max_mine": gmax, "scipy_max_abs_diff": sc, "hazard": h, "S": S, "P_close": pclose(S, rc["r_a"], rc["r_b"]),
            "reclose": rc, "max_session": max(SESS[r[0]][r[1] - 1] for r in rows),
            "clipped": (raw[k]["f3"] < prep.lo or raw[k]["f3"] > prep.hi) if recipe == "ceiling" else None}


def ledger(name):
    return rd(GOLD / f"{name}_fold_ledger.csv", enc="utf-8")


def cmp_fold(mine, led, feats):
    d = {}
    d["selected_lambda"] = (mine["selected_lambda"], led["selected_lambda"])
    tab = {("INF" if e["lambda"] == "INF" else float(e["lambda"])): e["score"] for e in json.loads(led["lambda_score_table"])}
    d["max_abs_score_diff"] = max(abs(mine["score"][lam] - tab["INF" if lam == INF else lam]) for lam in LAMBDA_GRID)
    d["max_abs_gamma_diff"] = max(abs(mine["gamma"][i] - float(led[f"gamma_g{i+1}"])) for i in range(3))
    d["max_abs_beta_diff"] = max(abs(mine["beta"].get(f, 0.0) - float(led[f"beta_{f}"])) for f in feats)
    d["max_abs_S_diff"] = max(abs(mine["S"][k - 1] - float(led[f"S_{k}"])) for k in range(1, 11))
    d["max_abs_hazard_diff"] = max(abs(mine["hazard"][k - 1] - float(led[f"hazard_{k}"])) for k in range(1, 11))
    d["max_abs_Pclose_diff"] = max(abs(mine["P_close"][k - 1] - float(led[f"P_close_{k}"])) for k in range(1, 11))
    d["reclose_equal"] = all(abs(mine["reclose"][x] - float(led[f"reclose_{x}"])) < 1e-15 for x in ("n_a", "a_a", "r_a", "n_b", "a_b", "r_b"))
    d["training_sha_equal"] = mine["training_sha"] == led["training_tickers_sha256"]
    d["pp_sha_equal"] = mine["pp_sha"] == led["training_pp_sha256"]
    d["counts_equal"] = (mine["n_ipo"], mine["n_rows"], mine["n_events"]) == (int(led["training_n_ipo"]), int(led["training_n_pp_rows"]), int(led["training_n_events"]))
    d["max_session_lt_cutoff"] = mine["max_session"] < mine["cutoff"] and led["training_max_session_date"] == mine["max_session"]
    d["clipped"] = (mine["clipped"], led["test_f3_clipped"])
    return d


# ================================================================ A. plan hash'leri (tüm fold'lar)
say("=== A. Fold planı: TÜM fold'larda eğitim kümesi ve PP hash'i (bağımsız kurgu vs ledger)")
A = {}
for plan, lname in (("ceiling", "ceiling_hazard_v0"), ("pb_ceiling", "pb_ceiling_v0")):
    led = ledger(lname)
    pool = F3_PRESENT if plan == "ceiling" else ORDER
    mine = []
    for k in pool:
        c, rows, training, ok = ceiling_fold(k, plan)
        if ok:
            mine.append((k, c, ihash(training), ihash([f"{r[0]}|{r[1]}|{r[3]}" for r in rows]),
                         max(SESS[r[0]][r[1] - 1] for r in rows), len(training), sum(r[3] for r in rows), len(rows)))
    assert [m[0] for m in mine] == [r["ticker"] for r in led], (plan, "test kümesi")
    ok_tr = sum(m[2] == r["training_tickers_sha256"] for m, r in zip(mine, led))
    ok_pp = sum(m[3] == r["training_pp_sha256"] for m, r in zip(mine, led))
    ok_ms = sum(m[4] == r["training_max_session_date"] and m[4] < m[1] == r["prediction_date"] for m, r in zip(mine, led))
    ok_ct = sum((m[5], m[6], m[7]) == (int(r["training_n_ipo"]), int(r["training_n_events"]), int(r["training_n_pp_rows"])) for m, r in zip(mine, led))
    ok_L = sum(int(r["realized_L"]) == L[r["ticker"]] for r in led)
    self_in = sum(r["ticker"] in set() for r in led)
    A[plan] = dict(folds=len(mine), training_sha_ok=ok_tr, pp_sha_ok=ok_pp, max_session_lt_cutoff_ok=ok_ms, counts_ok=ok_ct, realized_L_ok=ok_L)
    say(plan, A[plan])
    # test arzı kendi eğitiminde mi? (hash eşitliği bunu zaten dışlar; ayrıca açık kontrol)
    assert all(k not in tr for k, tr in ((m[0], [j for j in pool if FTD[j] < m[1]]) for m in mine))
OUT["A_ceiling_plans"] = A

# V1.5 planı (market20 ve v1_6) ve PB planı (pb_v0): tüm fold'lar
HZ = {"D1": 1, "D3": 3, "D5": 5, "D10": 10}
for lname, cut in (("v1_5_market20_v0", "T"), ("v1_6_h99", "T"), ("pb_v0", "B")):
    led = ledger(lname)
    okc = tot = 0
    for r in led:
        h, k = r["horizon"], r["ticker"]
        c = FTD[k] if cut == "T" else BB[k]
        training = [j for j in ORDER if tgd[(j, h)] < c]
        assert k not in training
        assert all(FTD[j] < c for j in training)
        tot += 1
        okc += (ihash(training) == r["training_tickers_sha256"] and len(training) >= 10 and r["prediction_date"] == c
                and max(tgd[(j, h)] for j in training) < c)
    A[lname] = dict(folds=tot, training_sha_and_cutoff_ok=okc)
    say(lname, A[lname])
OUT["A_linear_plans"] = {k: A[k] for k in ("v1_5_market20_v0", "v1_6_h99", "pb_v0")}

# ================================================================ B. ceiling_hazard_v0: 3 fold + kırpmalı fold
say("\n=== B. ceiling_hazard_v0: erken / orta / geç fold sıfırdan")
led_c = {r["ticker"]: r for r in ledger("ceiling_hazard_v0")}
clipped_folds = [t for t, r in led_c.items() if r["test_f3_clipped"] == "TRUE"]
say("kırpmalı test fold'ları:", clipped_folds)
picks = ["EKOS", "EGEGY", "QUICK"] + ([clipped_folds[len(clipped_folds) // 2]] if clipped_folds else [])
B = {}
for k in picks:
    mine = run_hazard_fold(k, "ceiling", V15, "ceiling")
    d = cmp_fold(mine, led_c[k], ("f1", "f2", "f3"))
    d.update(n_ipo=mine["n_ipo"], n_rows=mine["n_rows"], n_events=mine["n_events"], cutoff=mine["cutoff"],
             grad_max_mine=mine["grad_max_mine"], scipy_max_abs_diff=mine["scipy_max_abs_diff"],
             S=[round(x, 6) for x in mine["S"]], realized_L=L[k])
    B[k] = d
    say(k, json.dumps(d, default=str))
OUT["B_ceiling_folds"] = B

# ================================================================ C. pb_ceiling_v0: 2 fold
say("\n=== C. pb_ceiling_v0: erken ve orta fold sıfırdan (kesim B)")
led_p = {r["ticker"]: r for r in ledger("pb_ceiling_v0")}
PB2 = {t: {"pb1": PBF[t]["pb1"], "pb2": PBF[t]["pb2"]} for t in ORDER}
C = {}
for k in ("SKYMD", "KLYPV"):
    mine = run_hazard_fold(k, "pb_ceiling", PB2, "pb")
    d = cmp_fold(mine, led_p[k], ("pb1", "pb2"))
    d.update(n_ipo=mine["n_ipo"], n_rows=mine["n_rows"], n_events=mine["n_events"], cutoff=mine["cutoff"],
             cutoff_is_B=mine["cutoff"] == BB[k], cutoff_lt_T=mine["cutoff"] < FTD[k],
             grad_max_mine=mine["grad_max_mine"], scipy_max_abs_diff=mine["scipy_max_abs_diff"], realized_L=L[k])
    C[k] = d
    say(k, json.dumps(d, default=str))
OUT["C_pb_ceiling_folds"] = C

# ================================================================ D. KM kuralları
say("\n=== D. KM kuralları: aynı PP eğitim kümesinden yeniden üretim (tüm fold'lar)")


def km(rows, last_n=None):
    out = []
    for d in range(1, 11):
        day = sorted((r for r in rows if r[1] == d), key=lambda r: (FTD[r[0]], r[0]))
        if last_n:
            day = day[-last_n:]
        if day:
            out.append(sum(r[3] for r in day) / len(day))
        else:
            out.append(out[-1])
    return out


D = {}
for plan, suffix in (("ceiling", ""), ("pb_ceiling", "__pb_ceiling")):
    for rule, last_n in (("base_km_expanding", None), ("base_km_last10", 10)):
        led = ledger(rule + suffix)
        mx_ = 0.0
        for r in led:
            c, rows, training, ok = ceiling_fold(r["ticker"], plan)
            S = surv(km(rows, last_n))
            rc = reclose(training, c)
            Pc = pclose(S, rc["r_a"], rc["r_b"])
            mx_ = max(mx_, max(abs(S[k - 1] - float(r[f"S_{k}"])) for k in range(1, 11)),
                      max(abs(Pc[k - 1] - float(r[f"P_close_{k}"])) for k in range(1, 11)))
        D[rule + suffix] = dict(folds=len(led), max_abs_diff_S_and_Pclose=mx_)
        say(rule + suffix, D[rule + suffix])
    led = ledger("base_always_ceiling__" + ("ceiling" if plan == "ceiling" else "pb_ceiling"))
    D["always" + suffix] = all(float(r[f"S_{k}"]) == 1.0 for r in led for k in range(1, 11))
    # @INF kuralı: kapalı biçim
    led = ledger(("ceiling_hazard_v0" if plan == "ceiling" else "pb_ceiling_v0") + "@INF")
    mx_ = 0.0
    for r in led:
        c, rows, training, ok = ceiling_fold(r["ticker"], plan)
        g = np.array([x[2] for x in rows])
        e = np.array([x[3] for x in rows], dtype=float)
        ev, risk = np.bincount(g, weights=e, minlength=3), np.bincount(g, minlength=3)
        gam = np.log((ev + 0.5) / (risk - ev + 0.5))
        mx_ = max(mx_, max(abs(gam[i] - float(r[f"gamma_g{i+1}"])) for i in range(3)))
    D["at_inf" + suffix] = dict(folds=len(led), max_abs_gamma_diff=mx_)
    say("@INF" + suffix, D["at_inf" + suffix])
OUT["D_km_rules"] = D

# ================================================================ E. pb_v0: D5|ARMGD sıfırdan
say("\n=== E. pb_v0 fold D5|ARMGD sıfırdan (kesim B, V1.6 ızgarası, iç LOOCV)")
ALPHA = (0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0, INF)
CG = (0.0, 0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0)
LOGIT = dict(l1_ratio=0.0, solver="lbfgs", fit_intercept=True, class_weight=None, max_iter=10000, tol=1e-10)


def linear_fold(k, h, raw, recipe, cut, alpha_grid, c_grid):
    c = FTD[k] if cut == "T" else BB[k]
    training = [j for j in ORDER if tgd[(j, h)] < c]
    R = {j: float(ROW[j][f"R_{h}"]) for j in training}
    Y = {j: int(ROW[j][f"Y_{h}"]) for j in training}
    # iç LOOCV
    mae = {a: 0.0 for a in alpha_grid}
    bri = {cc: 0.0 for cc in c_grid}
    for j in training:
        inner = [t for t in training if t != j]
        prep = Prep(inner, raw, recipe)
        Xi = np.array([prep.Z[t] for t in inner])
        zj = prep.transform_raw(raw[j]).reshape(1, -1)
        yr = np.array([R[t] for t in inner])
        yc = np.array([Y[t] for t in inner], dtype=float)
        for a in alpha_grid:
            yhat = yr.mean() if a == INF else float(Ridge(alpha=a, fit_intercept=True, solver="svd").fit(Xi, yr).predict(zj)[0])
            mae[a] += abs(R[j] - yhat)
        for cc in c_grid:
            if cc == 0.0:
                p1 = yc.mean()
            else:
                est = LogisticRegression(C=cc, **LOGIT).fit(Xi, yc)
                p1 = float(est.predict_proba(zj)[0][list(est.classes_).index(1)])
            bri[cc] += (p1 - Y[j]) ** 2
    n = len(training)
    mae = {a: v / n for a, v in mae.items()}
    bri = {cc: v / n for cc, v in bri.items()}
    best = min(mae.values())
    a_sel = max(a for a, v in mae.items() if v == best)
    best = min(bri.values())
    c_sel = min(cc for cc, v in bri.items() if v == best)
    prep = Prep(training, raw, recipe)
    X = np.array([prep.Z[t] for t in training])
    zk = prep.transform_raw(raw[k]).reshape(1, -1)
    yr = np.array([R[t] for t in training])
    yc = np.array([Y[t] for t in training], dtype=float)
    pred = yr.mean() if a_sel == INF else float(Ridge(alpha=a_sel, fit_intercept=True, solver="svd").fit(X, yr).predict(zk)[0])
    if c_sel == 0.0:
        prob = yc.mean()
    else:
        est = LogisticRegression(C=c_sel, **LOGIT).fit(X, yc)
        prob = float(est.predict_proba(zk)[0][list(est.classes_).index(1)])
    return dict(cutoff=c, n=n, training_sha=ihash(training), alpha=a_sel, C=c_sel, ridge_prediction=pred, logit_probability=prob,
                mae_table=mae, brier_table=bri, columns=prep.cols, max_target_date=max(tgd[(j, h)] for j in training))


led = {r["fold_id"]: r for r in ledger("pb_v0")}
r = led["D5|ARMGD"]
mine = linear_fold("ARMGD", "D5", PBF, "pb", "B", ALPHA, CG)
tab_a = {("INF" if e["hyperparameter"] == "INF" else float(e["hyperparameter"])): e["score"] for e in json.loads(r["ridge_score_table"])}
tab_c = {(0.0 if e["hyperparameter"] == "ZERO" else float(e["hyperparameter"])): e["score"] for e in json.loads(r["logit_score_table"])}
E = dict(cutoff=(mine["cutoff"], r["prediction_date"], BB["ARMGD"]), cutoff_lt_T=mine["cutoff"] < FTD["ARMGD"],
         max_target_date_lt_cutoff=mine["max_target_date"] < mine["cutoff"], n=(mine["n"], int(r["training_n"])),
         training_sha_equal=mine["training_sha"] == r["training_tickers_sha256"],
         alpha=(mine["alpha"], r["ridge_selected_alpha"]), C=(mine["C"], r["logit_selected_C"]),
         ridge_prediction_diff=abs(mine["ridge_prediction"] - float(r["ridge_prediction"])),
         logit_probability_diff=abs(mine["logit_probability"] - float(r["logit_probability"])),
         max_abs_mae_table_diff=max(abs(mine["mae_table"][a] - tab_a["INF" if a == INF else a]) for a in ALPHA),
         max_abs_brier_table_diff=max(abs(mine["brier_table"][c] - tab_c[c]) for c in CG), columns=mine["columns"])
say(json.dumps(E, default=str))
OUT["E_pb_v0_fold"] = E

# ================================================================ F. market20: f6 bağımsız + D5|ARMGD fold
say("\n=== F. v1_5_market20_v0: f6 bağımsız hesap (yalnız S0 < T) ve D5|ARMGD fold")
calB = [rr["calendar_date"] for rr in rd(RAW / "v2_market20_official_pay_calendar_evidence_r4.csv") if rr["counts_as_official_session"] == "YES"]
X = json.load(open(RAW / "official_bist_xu100_graphic_pinned_through_20260819.json"), parse_float=Decimal)
assert all(rec["indexName"] == "XU100" for rec in X["data"])
closes = {rec["hisTs"]: rec["clval"] for rec in X["data"]}


def f6_of(ref):
    vis = {d: v for d, v in closes.items() if d < ref}  # as_of: yalnız ref öncesi
    i = bisect.bisect_left(calB, ref) - 1
    s0, s20 = calB[i], calB[i - 20]
    win = calB[i - 20: i + 1]
    assert len(win) == 21 and all(d in vis for d in win) and s0 < ref
    with localcontext(Context(prec=60, rounding=ROUND_HALF_EVEN)):
        return vis[s0] / vis[s20] - 1, s0, s20


mledger = ledger("v1_5_market20_v0")
F = {}
ok_f6 = 0
for rr in mledger:
    f6, s0, s20 = f6_of(FTD[rr["ticker"]])
    ok_f6 += (str(f6) == rr["test_f6"] and s0 == rr["test_f6_S0_date"] and s20 == rr["test_f6_S20_date"] and s0 < rr["prediction_date"])
F["f6_ledger_rows_matching_independent_and_S0_lt_T"] = (ok_f6, len(mledger))
frozen_m20 = json.load(open(ROOT / "models" / "v1_5_market20_v0.json"))
ok_j = sum(str(f6_of(FTD[t])[0]) == rec["f6"] and f6_of(FTD[t])[1] == rec["S0_date"] < rec["ref_date"] == FTD[t]
           for t, rec in frozen_m20["market20_training"].items())
F["f6_frozen_json_matching"] = (ok_j, len(frozen_m20["market20_training"]))
# as_of zehirleme: ref ve sonrası saçma değerler eklense f6 değişmez (bağımsız fonksiyonda tanım gereği; kod tarafı market20.py:223)
V15F6 = {t: {**V15[t], "f6": float(f6_of(FTD[t])[0])} for t in ORDER}
r = {x["fold_id"]: x for x in mledger}["D5|ARMGD"]
mine = linear_fold("ARMGD", "D5", V15F6, "v15", "T", (0.1, 1.0, 10.0, 100.0), (0.01, 0.1, 1.0, 10.0))
tab_a = {float(e["hyperparameter"]): e["score"] for e in json.loads(r["ridge_score_table"])}
tab_c = {float(e["hyperparameter"]): e["score"] for e in json.loads(r["logit_score_table"])}
F["fold_D5_ARMGD"] = dict(cutoff=(mine["cutoff"], r["prediction_date"]), max_target_date_lt_cutoff=mine["max_target_date"] < mine["cutoff"],
                          n=(mine["n"], int(r["training_n"])), training_sha_equal=mine["training_sha"] == r["training_tickers_sha256"],
                          alpha=(mine["alpha"], r["ridge_selected_alpha"]), C=(mine["C"], r["logit_selected_C"]),
                          ridge_prediction_diff=abs(mine["ridge_prediction"] - float(r["ridge_prediction"])),
                          logit_probability_diff=abs(mine["logit_probability"] - float(r["logit_probability"])),
                          max_abs_mae_table_diff=max(abs(mine["mae_table"][a] - tab_a[a]) for a in (0.1, 1.0, 10.0, 100.0)),
                          max_abs_brier_table_diff=max(abs(mine["brier_table"][c] - tab_c[c]) for c in (0.01, 0.1, 1.0, 10.0)),
                          columns=mine["columns"], albtn_endae_in_training=[t for t in ("ALBTN", "ENDAE") if tgd[(t, "D5")] < mine["cutoff"]])
say(json.dumps(F, default=str))
OUT["F_market20"] = F

# ================================================================ G. nihai hazard modelleri (JSON)
say("\n=== G. Dondurulmuş hazard JSON'larının bağımsız yeniden fit'i")
G = {}
for mid, pool, raw, recipe, feats in (("ceiling_hazard_v0", F3_PRESENT, V15, "ceiling", ("f1", "f2", "f3")),
                                      ("pb_ceiling_v0", ORDER, PB2, "pb", ("pb1", "pb2"))):
    js = json.load(open(ROOT / "models" / f"{mid}.json"))
    rows = [r for t in pool for r in pp_rows(t)]
    sel, score = select_lambda(pool, rows, raw, recipe)
    prep = Prep(pool, raw, recipe)
    gam, bet, gmax = fit_hazard(rows, prep.Z, sel, len(prep.cols))
    sc = scipy_check(rows, prep.Z, sel, len(prep.cols), np.r_[gam, bet])
    rc = reclose(pool, None)
    tab = {("INF" if e["lambda"] == "INF" else float(e["lambda"])): e["score"] for e in js["lambda_score_table"]}
    G[mid] = dict(n_ipo=(len(pool), js["training"]["n_ipo"]), n_rows=(len(rows), js["training"]["n_pp_rows"]),
                  n_events=(sum(r[3] for r in rows), js["training"]["n_events"]), tickers_sha_equal=ihash(pool) == js["training"]["tickers_sha256"],
                  selected_lambda=(sel, js["lambda"]), max_abs_score_diff=max(abs(score[l] - tab["INF" if l == INF else l]) for l in LAMBDA_GRID),
                  max_abs_gamma_diff=max(abs(gam[i] - js["gamma"][i]) for i in range(3)),
                  max_abs_beta_diff=max(abs(bet[i] - js["beta"][c]) for i, c in enumerate(prep.cols)),
                  reclose_equal=all(abs(rc[x] - js["reclose_rates"][x]) < 1e-15 for x in rc), scipy_max_abs_diff=sc,
                  mean_diff=max(abs(prep.mean[c] - js["preprocessing"]["mean"][c]) for c in prep.cols),
                  std_diff=max(abs(prep.std[c] - js["preprocessing"]["std"][c]) for c in prep.cols),
                  winsor=(getattr(prep, "lo", None), getattr(prep, "hi", None), js["preprocessing"]["winsor"]),
                  gamma_mine=gam.tolist(), beta_mine=dict(zip(prep.cols, bet.tolist())))
    say(mid, json.dumps(G[mid], default=str))
    # bağımsız tahmin: 5 girdi (eğitimden 3 + uç 2) -> JSON'dan stdlib benzeri hesap ile aynı mı (Q4 için referans)
OUT["G_frozen_refit"] = G

# ================================================================ H. RPS eşleşik farklar + blok bootstrap
say("\n=== H. Ledger'dan RPS eşleşik farkları (MODELS.md ile karşılaştırma)")


def rps(S, Lv):
    return sum((S[k - 1] - (1.0 if Lv >= k else 0.0)) ** 2 for k in range(1, 11)) / 10


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


H = {}
for model, suffix in (("ceiling_hazard_v0", ""), ("pb_ceiling_v0", "__pb_ceiling")):
    ml = ledger(model)
    for rule in (f"{model}@INF", "base_km_expanding" + suffix, "base_km_last10" + suffix):
        rl = {r["ticker"]: r for r in ledger(rule)}
        diffs, months, a, b = [], [], [], []
        for r in ml:
            o = rl[r["ticker"]]
            la = rps([float(r[f"S_{k}"]) for k in range(1, 11)], int(r["realized_L"]))
            lb = rps([float(o[f"S_{k}"]) for k in range(1, 11)], int(o["realized_L"]))
            diffs.append(la - lb)
            a.append(la)
            b.append(lb)
            months.append(r["first_trading_date"][:7])
        lo, hi = boot(diffs, months)
        H[f"{model} - {rule}"] = dict(n=len(diffs), model=round(sum(a) / len(a), 4), rule=round(sum(b) / len(b), 4),
                                      diff=round(sum(diffs) / len(diffs), 4), ci=(round(lo, 4), round(hi, 4)))
        say(f"{model} - {rule}", H[f"{model} - {rule}"])
# gün başına: modelin en çok kazandığı k ve kalibrasyon
ml = ledger("ceiling_hazard_v0")
cal = {k: (round(sum(float(r[f"S_{k}"]) for r in ml) / len(ml), 4), round(sum(1.0 for r in ml if int(r["realized_L"]) >= k) / len(ml), 4)) for k in (1, 3, 5, 10)}
H["ceiling_calibration_meanS_vs_observed"] = cal
say("kalibrasyon", cal)
OUT["H_rps"] = H

json.dump(OUT, open(Path(__file__).with_name("independent_repro_output.json"), "w"), indent=1, default=str)
say("\nDONE")

#!/usr/bin/env python3
"""BORSAI_FAZ4_FABLE_REPRO_AUDIT_20260922 — SPEC_CEILING_PATH_V0'ın sıfırdan, bağımsız
yeniden üretimi (Fable). `borsai` paketi IMPORT EDİLMEZ; yalnız stdlib.

Yalnız şartnameden kodlanmıştır (docs/specs_faz4/SPEC_CEILING_PATH_V0.md §2, §3, §4, §12;
SPEC_SCORING §7; SPEC_DEVIATIONS C7). Girdiler (hepsi ≤ 2026-08-19):
  data/training_table.csv, H99 SESSIONS CSV, H99 takvimi (yalnız denetim), PB CSV,
  Faz 1B altın ledger'ları (S_k), Faz 1A/1B altın kural ledger'ları (karşılaştırma).
Çıktı: stdout raporu + repro_output.json (aynı dizin). data/outcomes, data/raw/bist, scores okunmaz.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import statistics
import sys
import time
from collections import defaultdict
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # docs/fable_faz4_audit/ekler -> repo kökü
assert (ROOT / "CLAUDE.md").exists(), ROOT

DATA = ROOT / "data"
SESS_CSV = DATA / "raw" / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv"
CAL_CSV = DATA / "raw" / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_pay_session_calendar.csv"
PB_CSV = DATA / "raw" / "PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv"
TT_CSV = DATA / "training_table.csv"
G1A = ROOT / "tests" / "reference" / "macos_golden"
G1B = ROOT / "tests" / "reference" / "macos_golden_faz1b"
G4 = ROOT / "tests" / "reference" / "macos_golden_faz4"
CUTOFF_MAX = "2026-08-19"
N_MIN = 10
TOL = 1e-9

OUT: dict = {}
LOG: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha256_items(items) -> str:
    return hashlib.sha256(("\n".join(items) + "\n").encode("utf-8")).hexdigest()


def read_csv(p: Path) -> list[dict]:
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ============================================================ 0. veri (yalnız H99, ≤ 2026-08-19)
tt_rows = read_csv(TT_CSV)
IPO_ORDER = [r["ticker"] for r in tt_rows]
TT = {r["ticker"]: r for r in tt_rows}
assert len(IPO_ORDER) == 99 and len(set(IPO_ORDER)) == 99
P_OF = {t: Decimal(TT[t]["ipo_price_tl"]) for t in IPO_ORDER}
L_OF = {t: int(TT[t]["ceiling_streak_L"]) for t in IPO_ORDER}
FTD = {t: TT[t]["first_trading_date"] for t in IPO_ORDER}

sess_rows = read_csv(SESS_CSV)
SESS: dict[str, dict[int, dict]] = defaultdict(dict)
for r in sess_rows:
    SESS[r["ticker"]][int(r["session_number"])] = {
        "date": r["target_session_date"], "close": Decimal(r["close"]),
        "upper": Decimal(r["upper_limit"]), "lower": Decimal(r["lower_limit"]), "ref": Decimal(r["reference_price"]),
    }
assert len(sess_rows) == 990 and all(len(SESS[t]) == 10 for t in IPO_ORDER)
max_sess_date = max(r["target_session_date"] for r in sess_rows)
assert max_sess_date <= CUTOFF_MAX, max_sess_date
say(f"[veri] 99 arz, 990 seans, en son seans {max_sess_date} ≤ {CUTOFF_MAX}; training_table sha256 {sha256_file(TT_CSV)[:12]}")

pb_rows = read_csv(PB_CSV)
PB = {r["ticker"]: r for r in pb_rows}
assert set(PB) == set(IPO_ORDER)
B_OF = {t: PB[t]["first_bookbuilding_date"] for t in IPO_ORDER}
PB_PRICE = {t: Decimal(PB[t]["ipo_price_try"]) for t in IPO_ORDER}

cal_rows = read_csv(CAL_CSV)
OFFICIAL_DAYS = sorted(r["calendar_date"] for r in cal_rows if r["counts_as_official_session"] == "TRUE")
# takvim denetimi: her arzın 10 seansı resmi seans günleri ve artan sırada
for t in IPO_ORDER:
    ds = [SESS[t][k]["date"] for k in range(1, 11)]
    assert ds == sorted(ds) and all(d in OFFICIAL_DAYS for d in ds), t
    assert ds[0] == FTD[t], (t, ds[0], FTD[t])

# ============================================================ 1. Limit yolu (§2, §12)
TICKS = [(Decimal(20), Decimal("0.01")), (Decimal(50), Decimal("0.02")), (Decimal(100), Decimal("0.05")),
         (Decimal(250), Decimal("0.10")), (Decimal(500), Decimal("0.25")), (Decimal(1000), Decimal("0.50")),
         (Decimal(2500), Decimal("1.00")), (None, Decimal("2.50"))]


def tick(x: Decimal) -> Decimal:
    for lim, s in TICKS:
        if lim is None or x < lim:
            return s
    raise AssertionError


def U(b: Decimal) -> Decimal:
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


def limit_path(P: Decimal):
    C = []
    b = snap(P)
    for _ in range(10):
        b = U(b)
        C.append(b)
    rho = [float(c / P - 1) for c in C]
    return C, rho


# kabul 9-1 / 9-2: 990 seansta U(ref) = üst limit, Lo(ref) = alt limit; C_h = seri ≥ h olan arzın kapanışı
n_up = sum(1 for t in IPO_ORDER for k in range(1, 11) if U(SESS[t][k]["ref"]) == SESS[t][k]["upper"])
n_lo = sum(1 for t in IPO_ORDER for k in range(1, 11) if Lo(SESS[t][k]["ref"]) == SESS[t][k]["lower"])
ch_eq = {h: [0, 0] for h in range(1, 11)}
snapped = []
for t in IPO_ORDER:
    C, _ = limit_path(P_OF[t])
    if snap(P_OF[t]) != P_OF[t]:
        snapped.append((t, str(P_OF[t]), str(snap(P_OF[t]))))
    for h in range(1, 11):
        if L_OF[t] >= h:
            ch_eq[h][1] += 1
            ch_eq[h][0] += int(C[h - 1] == SESS[t][h]["close"])
say(f"[§2] U(ref)=üst limit {n_up}/990; Lo(ref)=alt limit {n_lo}/990; snap≠P: {snapped}")
say(f"[§2] C_h == kapanış (L≥h): " + " ".join(f"h{h}:{a}/{b}" for h, (a, b) in ch_eq.items()))
assert n_up == 990 and n_lo == 990 and all(a == b for a, b in ch_eq.values())
assert tick(Decimal("19.999")) == Decimal("0.01") and tick(Decimal(20)) == Decimal("0.02") and tick(Decimal(2500)) == Decimal("2.50")
OUT["limit_path_checks"] = {"U_eq": n_up, "Lo_eq": n_lo, "C_h_eq": ch_eq, "snapped": snapped}

# ============================================================ 2. Hücreler (§3)
def valid(g: str, m: int) -> bool:
    return 1 <= m <= (10 if g == "Z" else 9)


def build_cells(cutoff: str, *, single_group: bool = False):
    """Kesim: seans tarihi < cutoff olan gözlemler. 99 arz; f3 şartı yok. Döner: cells, katkı verenler, max tarih."""
    if single_group:
        cells = {("G", m): [] for m in range(1, 11)}
    else:
        cells = {("Z", m): [] for m in range(1, 11)} | {("B", m): [] for m in range(1, 10)}
    contributors, max_date = [], None
    for tk in IPO_ORDER:
        t = L_OF[tk]
        if t >= 10:
            continue
        base = P_OF[tk] if t == 0 else SESS[tk][t]["close"]
        g = "G" if single_group else ("Z" if t == 0 else "B")
        added = False
        for m in range(1, 11 - t):
            d = SESS[tk][t + m]["date"]
            if d >= cutoff:
                break
            G = float(SESS[tk][t + m]["close"] / base - 1)
            cells[(g, m)].append((G, tk))
            added = True
            max_date = d if max_date is None or d > max_date else max_date
        if added:
            contributors.append(tk)
    return {k: sorted(v) for k, v in cells.items()}, contributors, max_date


def ladder(g: str, m: int, *, single_group: bool = False):
    if single_group:
        steps = [[("G", m)]]
        for d in range(1, 10):
            for mm in (m - d, m + d):
                if 1 <= mm <= 10:
                    steps.append([("G", mm)])
        return steps
    other = "B" if g == "Z" else "Z"
    steps = [[(g, m)], [(other, m)] if valid(other, m) else []]
    for d in range(1, 10):
        for mm in (m - d, m + d):
            steps.append([(gg, mm) for gg in ("Z", "B") if valid(gg, mm)])
    return [s for s in steps if s]


CLIP_EVENTS: list = []


def bounds(m: int):
    return float(Decimal("0.9") ** m - 1), float(Decimal("1.1") ** m - 1)


def pooled(cells, g, m, n_min=N_MIN, *, single_group=False, nearest_only=False):
    """§3 merdiveni. Döner (değerler, bakılan hücreler, pooled bayrağı) ya da (None, bakılan, True)."""
    if nearest_only:
        # duyarlılık (iv): havuzlama yok; kendi hücresi n ≥ n_min değilse aynı gruptaki en yakın yeterli m;
        # grup içinde yoksa öteki grubun en yakın yeterli m'si; hiç yoksa ret.
        if len(cells[(g, m)]) >= n_min:
            return list(cells[(g, m)]), [(g, m)], False
        cands = []
        for (gg, mm), lst in cells.items():
            if len(lst) >= n_min:
                cands.append((0 if gg == g else 1, abs(mm - m), mm, gg))
        if not cands:
            return None, [(g, m)], True
        cands.sort()
        _, _, mm, gg = cands[0]
        lo, hi = bounds(m)
        return [(min(max(v, lo), hi), tk) for v, tk in cells[(gg, mm)]], [(g, m), (gg, mm)], True
    out, used = [], []
    for step in ladder(g, m, single_group=single_group):
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
        clipped = []
        for v, tk in out:
            c = min(max(v, lo), hi)
            if c != v:
                CLIP_EVENTS.append((g, m, tk, v, c))
            clipped.append((c, tk))
        out = clipped
    return out, used, is_pooled


# ============================================================ 3. Karışım ve kuantiller (§4)
def p_streak(S):
    return [1 - S[0]] + [S[t - 1] - S[t] for t in range(1, 10)] + [S[9]]


def mixture(S, P: Decimal, C, rho, cells, h, **kw):
    PL = p_streak(S)
    atoms = [(rho[h - 1], S[h - 1])]
    cell_info = []
    for t in range(0, h):
        g = "G" if kw.get("single_group") else ("Z" if t == 0 else "B")
        m = h - t
        vals, used, is_pooled = pooled(cells, g, m, **kw)
        if vals is None:
            return None, cell_info + [{"group": g, "m": m, "n": 0, "pooled": True, "sources": used}]
        cell_info.append({"group": g, "m": m, "n": len(vals), "pooled": is_pooled, "sources": [list(u) for u in used]})
        scale = 1.0 if t == 0 else float(C[t - 1] / P)
        w = PL[t] / len(vals)
        for v, _ in vals:
            atoms.append(((scale * (1 + v) - 1) if t else v, w))
    atoms.sort(key=lambda a: a[0])  # kararlı: eşit r'de ekleme sırası

    def Q(q):
        cum = 0.0
        for r, w in atoms:
            cum += w
            if cum >= q - 1e-12:
                return r
        return atoms[-1][0]

    res = {"return": Q(0.5), "q10": Q(0.1), "q50": Q(0.5), "q90": Q(0.9),
           "p_up": sum(w for r, w in atoms if r > 0), "mean": sum(r * w for r, w in atoms),
           "limit_path_return": rho[h - 1], "S_h": S[h - 1], "n_atoms": len(atoms),
           "weight_sum": sum(w for _, w in atoms)}
    return res, cell_info


# ============================================================ 4. Walk-forward koşu (§8)
def realized(tk):
    P = P_OF[tk]
    R = {h: float(Decimal(TT[tk][f"R_D{h}"])) for h in (1, 3, 5, 10)}
    Y = {h: int(SESS[tk][h]["close"] > P) for h in range(1, 11)}
    for h in (1, 3, 5, 10):
        assert Y[h] == int(TT[tk][f"Y_D{h}"])
        assert Decimal(TT[tk][f"R_D{h}"]) == SESS[tk][h]["close"] / P or abs(Decimal(TT[tk][f"R_D{h}"]) - (SESS[tk][h]["close"] / P - 1)) < Decimal("1e-20")
    return R, Y


def run_plan(model_id, source_ledger_name, price_source, cutoff_field="prediction_date", **kw):
    src_path = G1B / f"{source_ledger_name}_fold_ledger.csv"
    src_sha = sha256_file(src_path)
    src = read_csv(src_path)
    folds = []
    for r in src:
        tk = r["ticker"]
        assert r["status"] == "FIT_OK", (model_id, tk, r["status"])
        T = r[cutoff_field]
        S = [float(r[f"S_{k}"]) for k in range(1, 11)]
        P = P_OF[tk] if price_source == "training" else PB_PRICE[tk]
        C, rho = limit_path(P)
        cells, contributors, max_date = build_cells(T, single_group=bool(kw.get("single_group")))
        # sızıntı denetimleri (adım 2)
        assert max_date is None or max_date < T, (tk, max_date, T)
        assert tk not in contributors, tk
        assert T <= FTD[tk]
        fold = {"model_id": model_id, "fold_id": r["fold_id"], "ticker": tk, "first_trading_date": r["first_trading_date"],
                "prediction_date": T, "survival_model_id": source_ledger_name, "survival_ledger_sha256": src_sha,
                "survival_fold_status": r["status"], "S": S, "S_str": [r[f"S_{k}"] for k in range(1, 11)],
                "P_L": p_streak(S), "ipo_price": str(P), "snapped_ipo_price": str(snap(P)), "tick": str(tick(P)),
                "C": [str(c) for c in C], "rho": rho,
                "cells_n": {f"{g}_{m}": len(v) for (g, m), v in cells.items()},
                "cells_max_session_date": max_date, "cells_ipos_sha256": sha256_items(contributors),
                "n_contributors": len(contributors), "status": "OK", "D": {}}
        for h in range(1, 11):
            res, info = mixture(S, P, C, rho, cells, h, **kw)
            if res is None:
                fold["status"] = "POST_BREAK_INSUFFICIENT"
                fold["D"][h] = {"post_break_status": "POST_BREAK_INSUFFICIENT", "pooled_cells": info}
            else:
                assert abs(res["weight_sum"] - 1) <= 1e-12
                assert res["return"] <= rho[h - 1] + 1e-15
                if S[h - 1] >= 0.5:
                    assert res["return"] == rho[h - 1]
                assert 0 <= res["p_up"] <= 1 + 1e-12 and res["p_up"] >= S[h - 1] - 1e-12
                assert res["q10"] <= res["q50"] <= res["q90"]
                fold["D"][h] = {**res, "post_break_status": "OK", "pooled_cells": info}
        R, Y = realized(tk)
        fold["realized_R"] = R
        fold["realized_Y"] = Y
        fold["realized_L"] = L_OF[tk]
        folds.append(fold)
    return folds, src_sha


# kabul 9-3: tam kohort (kesim yok) hücre sayımı
_full, _contrib, _maxd = build_cells("9999-12-31")
_Z = [len(_full[("Z", m)]) for m in range(1, 11)]
_B = [len(_full[("B", m)]) for m in range(1, 10)]
say(f"[§3] tam kohort: Z {_Z}; B {_B}; toplam {sum(len(v) for v in _full.values())}; katkı veren arz {len(_contrib)}; son seans {_maxd}")
assert _Z == [18] * 10 and _B == [67, 64, 60, 54, 48, 40, 28, 15, 11] and sum(len(v) for v in _full.values()) == 567 and _maxd <= CUTOFF_MAX
OUT["full_cohort_cells"] = {"Z": _Z, "B": _B, "n_obs": 567, "max_session_date": _maxd}

t0 = time.time()
RUNS = {
    "ceiling_path_v0": run_plan("ceiling_path_v0", "ceiling_hazard_v0", "training"),
    "ceiling_path_v0@INF": run_plan("ceiling_path_v0@INF", "ceiling_hazard_v0@INF", "training"),
    "pb_ceiling_path_v0": run_plan("pb_ceiling_path_v0", "pb_ceiling_v0", "pb"),
}
say(f"[koşu] üç plan {time.time() - t0:.1f} s; fold sayıları " + ", ".join(f"{k}: {len(v[0])}" for k, v in RUNS.items()))
say(f"[F4] PB planlanan fiyat == kesin arz fiyatı: {sum(1 for t in IPO_ORDER if PB_PRICE[t] == P_OF[t])}/99")
say(f"[§3] havuzda kırpılan gözlem sayısı (üç koşu, tüm fold×h×hücre): {len(CLIP_EVENTS)}")
OUT["clip_events"] = {"n": len(CLIP_EVENTS), "max_abs_change": max((abs(v - c) for *_, v, c in CLIP_EVENTS), default=0.0),
                      "by_m": {m: sum(1 for e in CLIP_EVENTS if e[1] == m) for m in range(1, 11)}, "first20": CLIP_EVENTS[:20]}
say(f"[§3] kırpma: en büyük |değişim| {OUT['clip_events']['max_abs_change']:.3e}; m'ye göre {OUT['clip_events']['by_m']}")

# ============================================================ 5. (a) Ledger karşılaştırması
def compare_ledger(model_id, folds):
    gl = read_csv(G4 / f"{model_id}_fold_ledger.csv")
    assert len(gl) == len(folds), (len(gl), len(folds))
    mx = defaultdict(float)
    exact = defaultdict(int)
    n_checked = defaultdict(int)
    mismatches = []
    for g, f in zip(gl, folds):
        assert g["fold_id"] == f["fold_id"] and g["ticker"] == f["ticker"] and g["prediction_date"] == f["prediction_date"]
        assert g["survival_ledger_sha256"] == f["survival_ledger_sha256"] and g["survival_model_id"] == f["survival_model_id"]
        # S bit-eşit (kaynak ledger metniyle)
        for k in range(1, 11):
            exact["S_str"] += int(g[f"S_{k}"] == f["S_str"][k - 1])
            n_checked["S_str"] += 1
            mx["P_L"] = max(mx["P_L"], abs(float(g[f"P_L_{k}"]) - f["P_L"][k]))
        mx["P_L"] = max(mx["P_L"], abs(float(g["P_L_0"]) - f["P_L"][0]))
        for name in ("ipo_price", "snapped_ipo_price", "tick"):
            exact[name] += int(Decimal(g[name]) == Decimal(f[name]))
            n_checked[name] += 1
        for h in range(1, 11):
            exact["C"] += int(Decimal(g[f"C_{h}"]) == Decimal(f["C"][h - 1]))
            exact["C_str"] += int(g[f"C_{h}"] == f["C"][h - 1])
            exact["rho_exact"] += int(float(g[f"rho_{h}"]) == f["rho"][h - 1])
            n_checked["C"] += 1
            n_checked["C_str"] += 1
            n_checked["rho_exact"] += 1
            mx["rho"] = max(mx["rho"], abs(float(g[f"rho_{h}"]) - f["rho"][h - 1]))
        for key, n in f["cells_n"].items():
            exact["cells_n"] += int(int(g[f"cells_n_{key}"]) == n)
            n_checked["cells_n"] += 1
        exact["cells_max_session_date"] += int(g["cells_max_session_date"] == (f["cells_max_session_date"] or ""))
        exact["cells_ipos_sha256"] += int(g["cells_ipos_sha256"] == f["cells_ipos_sha256"])
        exact["status"] += int(g["status"] == f["status"])
        n_checked["cells_max_session_date"] += 1
        n_checked["cells_ipos_sha256"] += 1
        n_checked["status"] += 1
        for h in range(1, 11):
            d = f["D"][h]
            for col, key in (("return", "return"), ("p_up", "p_up"), ("q10", "q10"), ("q90", "q90"), ("mean", "mean")):
                delta = abs(float(g[f"D{h}_{col}"]) - d[key])
                mx[key] = max(mx[key], delta)
                if delta > TOL:
                    mismatches.append((f["ticker"], h, key, g[f"D{h}_{col}"], d[key]))
            exact["n_atoms"] += int(int(g[f"D{h}_n_atoms"]) == d["n_atoms"])
            exact["post_break_status"] += int(g[f"D{h}_post_break_status"] == d["post_break_status"])
            n_checked["n_atoms"] += 1
            n_checked["post_break_status"] += 1
            gp = json.loads(g[f"D{h}_pooled_cells"])
            mine = d["pooled_cells"]
            same = len(gp) == len(mine) and all(
                a["group"] == b["group"] and a["m"] == b["m"] and a["n"] == b["n"] and a["pooled"] == b["pooled"]
                and [list(x) for x in a["sources"]] == b["sources"] for a, b in zip(gp, mine))
            exact["pooled_cells"] += int(same)
            n_checked["pooled_cells"] += 1
            if not same and len(mismatches) < 50:
                mismatches.append((f["ticker"], h, "pooled_cells", gp, mine))
        for h in (1, 3, 5, 10):
            mx["realized_R"] = max(mx["realized_R"], abs(float(g[f"realized_R_D{h}"]) - f["realized_R"][h]))
        for h in range(1, 11):
            exact["realized_Y"] += int(int(g[f"realized_Y_D{h}"]) == f["realized_Y"][h])
            n_checked["realized_Y"] += 1
        exact["realized_L"] += int(int(g["realized_L"]) == f["realized_L"])
        n_checked["realized_L"] += 1
    return {"max_abs_delta": dict(mx), "exact": {k: f"{exact[k]}/{n_checked[k]}" for k in n_checked},
            "all_exact": all(exact[k] == n_checked[k] for k in n_checked), "n_mismatch_gt_tol": len(mismatches),
            "mismatches": mismatches[:20]}


OUT["ledger_compare"] = {}
say("\n=== (a) Fold ledger karşılaştırması: tests/reference/macos_golden_faz4/ ===")
for mid, (folds, _) in RUNS.items():
    cmpres = compare_ledger(mid, folds)
    OUT["ledger_compare"][mid] = cmpres
    say(f"{mid}: maks|Δ| " + ", ".join(f"{k}={v:.3e}" for k, v in cmpres["max_abs_delta"].items()))
    say(f"  birebir: {cmpres['exact']}  hepsi birebir: {cmpres['all_exact']}; |Δ|>1e-9 sayısı: {cmpres['n_mismatch_gt_tol']}")
    for m in cmpres["mismatches"][:5]:
        say("   UYUŞMAZLIK:", m)

# ============================================================ 6. (b) Eşleşik karşılaştırmalar (SPEC_SCORING §7, C7)
PROB_CLIP = (0.01, 0.99)


def clip(p):
    return min(max(p, PROB_CLIP[0]), PROB_CLIP[1])


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
    """rows: [(ticker, month, loss_model, loss_rule)] model ledger sırasıyla."""
    diffs = [a - b for _, _, a, b in rows]
    months = [m for _, m, _, _ in rows]
    lo, hi = boot(diffs, months)
    return {"n": len(rows), "n_months": len(set(months)), "model": sum(a for *_, a, _ in rows) / len(rows),
            "rule": sum(b for *_, _, b in rows) / len(rows), "diff": sum(diffs) / len(diffs), "ci": [lo, hi],
            "model_better": sum(1 for d in diffs if d < 0), "rule_better": sum(1 for d in diffs if d > 0),
            "tie": sum(1 for d in diffs if d == 0),
            "verdict": "MODEL" if hi < 0 else ("RULE" if lo > 0 else "AYIRT_EDILEMIYOR"), "diffs": dict((r[0], d) for r, d in zip(rows, diffs))}


def rule_ledger(dirpath, name):
    rows = read_csv(dirpath / f"{name}_fold_ledger.csv")
    return {(r["ticker"], r["horizon"]): r for r in rows}


LEDGERS_1A = {n: rule_ledger(G1A, n) for n in ("base_always_ceiling", "base_train_median", "base_rate", "base_last10_rate", "v1_5_h99")}
LEDGERS_PB = {n: rule_ledger(G1B, n) for n in ("pb_v0", "base_train_median__pb", "base_always_ceiling__pb", "base_rate__pb", "base_last10_rate__pb")}
MODEL_BY_TICKER = {mid: {f["ticker"]: f for f in folds} for mid, (folds, _) in RUNS.items()}


def rule_value(ledger, tk, h, kind):
    r = ledger.get((tk, f"D{h}"))
    if r is None:
        return None
    if kind == "return":
        v = r.get("rule_return") if "rule_return" in r else r.get("ridge_prediction")
        if v in (None, ""):
            return None
        if "ridge_status" in r and r["ridge_status"] != "FIT_OK":
            return None
        return float(v)
    v = r.get("rule_p_up") if "rule_p_up" in r else r.get("logit_probability")
    if v in (None, ""):
        return None
    if "logit_status" in r and r["logit_status"] != "FIT_OK":
        return None
    return float(v)


def compare(model_id, h, kind, rule_name, rule_source):
    folds = RUNS[model_id][0]
    rows = []
    for f in folds:
        tk = f["ticker"]
        if rule_source == "model":
            other = MODEL_BY_TICKER[rule_name].get(tk)
            if other is None:
                continue
            rv = other["D"][h][kind]
        else:
            rv = rule_value(rule_source[rule_name], tk, h, kind)
            if rv is None:
                continue
        mv = f["D"][h][kind]
        if kind == "return":
            y = f["realized_R"][h]
            rows.append((tk, f["first_trading_date"][:7], abs(mv - y), abs(rv - y)))
        else:
            y = f["realized_Y"][h]
            rows.append((tk, f["first_trading_date"][:7], (clip(mv) - y) ** 2, (clip(rv) - y) ** 2))
    return paired(rows)


# §6 tablosu: (model, ufuk, çıktı, karşılaştırılan, beklenen alt, beklenen üst, "aralık 0'ı" ifadesi)
EXPECT = [
    ("ceiling_path_v0", 1, "return", "base_always_ceiling", 0.000, 0.005, "içerir"),
    ("ceiling_path_v0", 1, "return", "base_train_median", 0.000, 0.005, "içerir"),
    ("ceiling_path_v0", 1, "return", "v1_5_h99", -0.007, -0.002, "dışlayabilir (negatif)"),
    ("ceiling_path_v0", 1, "return", "ceiling_path_v0@INF", -0.001, 0.001, "içerir"),
    ("ceiling_path_v0", 1, "p_up", "base_rate", -0.005, 0.005, "içerir"),
    ("ceiling_path_v0", 1, "p_up", "base_last10_rate", -0.010, 0.002, "içerir"),
    ("ceiling_path_v0", 1, "p_up", "v1_5_h99", -0.002, 0.010, "içerir"),
    ("ceiling_path_v0", 1, "p_up", "ceiling_path_v0@INF", -0.003, 0.003, "içerir"),
    ("ceiling_path_v0", 3, "return", "base_always_ceiling", -0.020, 0.005, "içerir"),
    ("ceiling_path_v0", 3, "return", "base_train_median", -0.020, 0.005, "içerir"),
    ("ceiling_path_v0", 3, "return", "v1_5_h99", -0.010, 0.020, "içerir"),
    ("ceiling_path_v0", 3, "return", "ceiling_path_v0@INF", -0.015, 0.000, "içerir"),
    ("ceiling_path_v0", 3, "p_up", "base_rate", -0.040, -0.005, "büyük olasılıkla içerir"),
    ("ceiling_path_v0", 3, "p_up", "base_last10_rate", -0.040, -0.005, "büyük olasılıkla içerir"),
    ("ceiling_path_v0", 3, "p_up", "v1_5_h99", -0.010, 0.030, "içerir"),
    ("ceiling_path_v0", 3, "p_up", "ceiling_path_v0@INF", -0.025, 0.000, "içerir"),
    ("ceiling_path_v0", 5, "return", "base_train_median", -0.090, -0.020, "dışlaması olası, garanti değil"),
    ("ceiling_path_v0", 5, "return", "base_always_ceiling", -0.110, -0.040, "dışlaması olası"),
    ("ceiling_path_v0", 5, "return", "v1_5_h99", -0.020, 0.050, "içerir"),
    ("ceiling_path_v0", 5, "return", "ceiling_path_v0@INF", -0.050, -0.005, "içerir"),
    ("ceiling_path_v0", 5, "p_up", "base_rate", -0.030, 0.000, "içerir"),
    ("ceiling_path_v0", 5, "p_up", "base_last10_rate", -0.035, -0.005, "içerir"),
    ("ceiling_path_v0", 5, "p_up", "v1_5_h99", 0.000, 0.040, "içerir"),
    ("ceiling_path_v0", 5, "p_up", "ceiling_path_v0@INF", -0.020, 0.005, "içerir"),
    ("ceiling_path_v0", 10, "return", "base_train_median", -0.100, -0.010, "büyük olasılıkla içerir"),
    ("ceiling_path_v0", 10, "return", "base_always_ceiling", -0.750, -0.550, "dışlar (negatif)"),
    ("ceiling_path_v0", 10, "return", "v1_5_h99", -0.020, 0.100, "içerir"),
    ("ceiling_path_v0", 10, "return", "ceiling_path_v0@INF", -0.050, 0.010, "içerir"),
    ("ceiling_path_v0", 10, "p_up", "base_rate", -0.020, 0.010, "içerir"),
    ("ceiling_path_v0", 10, "p_up", "base_last10_rate", -0.070, -0.020, "dışlayabilir"),
    ("ceiling_path_v0", 10, "p_up", "v1_5_h99", 0.010, 0.060, "içerir ya da pozitif dışlar"),
    ("ceiling_path_v0", 10, "p_up", "ceiling_path_v0@INF", -0.010, 0.005, "içerir"),
    ("ceiling_path_v0@INF", 5, "return", "base_train_median", -0.040, 0.010, "içerir"),
    ("ceiling_path_v0@INF", 10, "return", "base_train_median", -0.060, 0.020, "içerir"),
    ("pb_ceiling_path_v0", 5, "return", "pb_v0", -0.040, 0.030, "içerir"),
    ("pb_ceiling_path_v0", 5, "return", "ceiling_path_v0", 0.000, 0.050, "içerir ya da pozitif dışlar"),
]
assert len(EXPECT) == 36

say("\n=== (b) §6'nın 36 satırı: eşleşik fark, %95 aralık, n (bağımsız hesap) ===")
ROWS36 = []
for mid, h, kind, rule, lo_e, hi_e, phrase in EXPECT:
    if rule in RUNS:
        res = compare(mid, h, kind, rule, "model")
    elif mid == "pb_ceiling_path_v0":
        res = compare(mid, h, kind, rule, LEDGERS_PB)
    else:
        res = compare(mid, h, kind, rule, LEDGERS_1A)
    row = {"model_id": mid, "h": h, "kind": kind, "rule": rule, "expect": [lo_e, hi_e], "phrase": phrase,
           **{("model_loss" if k == "model" else "rule_loss" if k == "rule" else k): v for k, v in res.items() if k != "diffs"}}
    row["label"] = "daha iyi" if res["diff"] < lo_e else ("daha kötü" if res["diff"] > hi_e else "aralıkta")
    row["much_better"] = (h in (3, 5, 10)) and (res["diff"] < lo_e - 0.03)
    ROWS36.append(row)
    say(f"{mid:20s} D{h:<2d} {kind:6s} vs {rule:22s} fark {res['diff']:+.4f} [{res['ci'][0]:+.4f}, {res['ci'][1]:+.4f}] n={res['n']} ({res['n_months']} ay) "
        f"model {res['model']:.4f} kural {res['rule']:.4f} {res['model_better']}/{res['rule_better']}/{res['tie']} → {row['label']}"
        + ("  [ÇOK İYİ: fark < alt uç − 0.03]" if row["much_better"] else ""))
OUT["rows36"] = ROWS36

# (c) birincil hücre ve "çok iyi" denetimi
prim = next(r for r in ROWS36 if r["model_id"] == "ceiling_path_v0" and r["h"] == 5 and r["kind"] == "return" and r["rule"] == "base_train_median")
conds = []
if prim["diff"] < -0.120:
    conds.append(f"birincil fark {prim['diff']:.4f} < -0.120")
if prim["ci"][1] < -0.060:
    conds.append(f"birincil aralık üst ucu {prim['ci'][1]:.4f} < -0.060")
for r in ROWS36:
    if r["much_better"]:
        conds.append(f"{r['model_id']} D{r['h']} {r['kind']} − {r['rule']}: fark {r['diff']:.4f} < alt uç {r['expect'][0]:+.3f} − 0.03")
say(f"\n=== (c) Birincil hücre: fark {prim['diff']:.6f} [{prim['ci'][0]:.6f}, {prim['ci'][1]:.6f}] n={prim['n']}; model {prim['model_loss']:.6f} kural {prim['rule_loss']:.6f}")
say(f"'Beklentiden çok iyi' koşulları ({len(conds)}):")
for c in conds:
    say("  -", c)
OUT["primary"] = {k: v for k, v in prim.items()}
OUT["much_better_conditions"] = conds

# D1 beraberlik cümlesi ve başarısızlık tanımları (a)-(d)
d1 = compare("ceiling_path_v0", 1, "return", "base_always_ceiling", LEDGERS_1A)
zero = sum(1 for d in d1["diffs"].values() if d == 0)
small = sum(1 for d in d1["diffs"].values() if d == 0 or abs(d) < 0.001)
say(f"D1 beraberlik: bit-eşit 0 olan fold {zero}/{d1['n']}, |fark|<0.001 ya da 0: {small}/{d1['n']} (≥ 80 gerekir)")
OUT["d1_tie"] = {"zero": zero, "small": small, "n": d1["n"]}
fa = {}
for h in (3, 5, 10):
    for kind in ("return", "p_up"):
        r = compare("ceiling_path_v0", h, kind, "ceiling_path_v0@INF", "model")
        fa[f"D{h}_{kind}"] = (r["diff"], r["ci"])
fail_a = all(ci[0] <= 0 <= ci[1] and d >= -0.005 for d, ci in fa.values())
fb = {h: compare("ceiling_path_v0@INF", h, "return", "base_train_median", LEDGERS_1A) for h in (5, 10)}
fail_b = all(fb[h]["ci"][0] > 0 for h in (5, 10))
fail_c = d1["ci"][0] > 0
folds_main = RUNS["ceiling_path_v0"][0]
mean_pup3 = statistics.mean(f["D"][3]["p_up"] for f in folds_main)
obs_y3 = statistics.mean(f["realized_Y"][3] for f in folds_main)
fail_d = abs(mean_pup3 - obs_y3) > 0.15
say(f"Başarısızlık (a) {fail_a} (b) {fail_b} (c) {fail_c} (d) {fail_d} [ort p_up_3 {mean_pup3:.4f}, gözlenen {obs_y3:.4f}]")
OUT["failures"] = {"a": fail_a, "b": fail_b, "c": fail_c, "d": fail_d, "mean_p_up_3": mean_pup3, "obs_Y3": obs_y3}

# ============================================================ 7. Tanı: kazanç nereden geliyor? (adım 3)
say("\n=== Tanı: D5 ve D10 kazancının kaynağı (ceiling_path_v0 − base_train_median) ===")
DIAG = {}
for h in (5, 10):
    r = compare("ceiling_path_v0", h, "return", "base_train_median", LEDGERS_1A)
    r_inf = compare("ceiling_path_v0", h, "return", "ceiling_path_v0@INF", "model")
    r_v15 = compare("ceiling_path_v0", h, "return", "v1_5_h99", LEDGERS_1A)
    by = {}
    for f in folds_main:
        tk = f["ticker"]
        if tk not in r["diffs"]:
            continue
        S_h = f["S"][h - 1]
        grp = "S_h<0.5" if S_h < 0.5 else "S_h>=0.5"
        by.setdefault(grp, []).append(r["diffs"][tk])
    groups = {g: {"n": len(v), "mean_diff": sum(v) / len(v), "sum_diff": sum(v), "share_of_total": sum(v) / sum(r["diffs"].values())} for g, v in by.items()}
    # S_5 ile de böl (D10 için)
    by5 = {}
    for f in folds_main:
        tk = f["ticker"]
        if tk in r["diffs"]:
            by5.setdefault("S_5<0.5" if f["S"][4] < 0.5 else "S_5>=0.5", []).append(r["diffs"][tk])
    groups5 = {g: {"n": len(v), "mean_diff": sum(v) / len(v), "sum_diff": sum(v)} for g, v in by5.items()}
    years = {}
    for f in folds_main:
        tk = f["ticker"]
        if tk in r["diffs"]:
            years.setdefault(f["first_trading_date"][:4], []).append(r["diffs"][tk])
    by_year = {y: {"n": len(v), "mean_diff": sum(v) / len(v), "sum_diff": sum(v)} for y, v in sorted(years.items())}
    top = sorted(r["diffs"].items(), key=lambda kv: kv[1])[:10]
    top_rows = []
    for tk, d in top:
        f = MODEL_BY_TICKER["ceiling_path_v0"][tk]
        top_rows.append({"ticker": tk, "ftd": f["first_trading_date"], "L": f["realized_L"], "S_h": f["S"][h - 1],
                         "model_return": f["D"][h]["return"], "rho_h": f["rho"][h - 1], "median_rule": rule_value(LEDGERS_1A["base_train_median"], tk, h, "return"),
                         "realized": f["realized_R"][h], "diff_AE": d})
    # AE = 0 payı: model tahmini limit yolu ve gerçekleşen tam limit yolu
    exact_hits = sum(1 for f in folds_main if f["ticker"] in r["diffs"] and f["D"][h]["return"] == f["rho"][h - 1] and abs(f["realized_R"][h] - f["rho"][h - 1]) < 1e-12)
    on_path = sum(1 for f in folds_main if f["ticker"] in r["diffs"] and f["D"][h]["return"] == f["rho"][h - 1])
    ae_model = [abs(f["D"][h]["return"] - f["realized_R"][h]) for f in folds_main if f["ticker"] in r["diffs"]]
    ae_v15 = [abs(rule_value(LEDGERS_1A["v1_5_h99"], f["ticker"], h, "return") - f["realized_R"][h]) for f in folds_main if f["ticker"] in r_v15["diffs"]]
    ae_med = [abs(rule_value(LEDGERS_1A["base_train_median"], f["ticker"], h, "return") - f["realized_R"][h]) for f in folds_main if f["ticker"] in r["diffs"]]
    qs = lambda v: [round(statistics.quantiles(v, n=10)[i], 4) for i in (0, 2, 4, 6, 8)] if len(v) > 10 else v
    DIAG[f"D{h}"] = {"total": {"diff": r["diff"], "ci": r["ci"], "n": r["n"]}, "by_S_h": groups, "by_S_5": groups5, "by_year": by_year,
                     "top10": top_rows, "vs_INF": {"diff": r_inf["diff"], "ci": r_inf["ci"], "n": r_inf["n"]},
                     "vs_v15": {"diff": r_v15["diff"], "ci": r_v15["ci"], "n": r_v15["n"]},
                     "model_return_eq_rho": on_path, "exact_hits_AE0": exact_hits,
                     "ae_quantiles_p10_30_50_70_90": {"model": qs(ae_model), "v1_5": qs(ae_v15), "median_rule": qs(ae_med)},
                     "ae_zero_count": {"model": sum(1 for a in ae_model if a < 1e-12), "v1_5": sum(1 for a in ae_v15 if a < 1e-12), "median_rule": sum(1 for a in ae_med if a < 1e-12)},
                     "vs_INF_by_S_h": None}
    # özellik bilgisinin payı: (ana − INF) grup bazında
    byi = {}
    for f in folds_main:
        tk = f["ticker"]
        if tk in r_inf["diffs"]:
            byi.setdefault("S_h<0.5" if f["S"][h - 1] < 0.5 else "S_h>=0.5", []).append(r_inf["diffs"][tk])
    DIAG[f"D{h}"]["vs_INF_by_S_h"] = {g: {"n": len(v), "mean_diff": sum(v) / len(v), "sum_diff": sum(v)} for g, v in byi.items()}
    say(f"D{h}: toplam fark {r['diff']:+.4f} n={r['n']}; gruplar {json.dumps({g: {k: round(x, 4) for k, x in d.items()} for g, d in groups.items()})}")
    say(f"     yıllara göre {json.dumps({y: {k: round(x, 4) for k, x in d.items()} for y, d in by_year.items()})}")
    say(f"     model tahmini = ρ_h olan fold {on_path}/{r['n']}; bunların gerçekleşeni de ρ_h (AE = 0) olan {exact_hits}")
    say(f"     ana − INF {r_inf['diff']:+.4f}; gruplar {json.dumps({g: {k: round(x, 4) for k, x in d.items()} for g, d in DIAG[f'D{h}']['vs_INF_by_S_h'].items()})}")
    say(f"     AE kuantilleri p10/30/50/70/90 model {qs(ae_model)} V1.5 {qs(ae_v15)} medyan kuralı {qs(ae_med)}; AE=0 sayısı {DIAG[f'D{h}']['ae_zero_count']}")
    say("     en çok katkı veren 10 arz: " + "; ".join(f"{t['ticker']}(L={t['L']},S={t['S_h']:.2f},Δ={t['diff_AE']:+.3f})" for t in top_rows))
OUT["diagnosis"] = DIAG

# INF'in medyan kuralına karşı D5/D10 kazancının kaynağı (mekanik kısım)
for h in (5, 10):
    r = compare("ceiling_path_v0@INF", h, "return", "base_train_median", LEDGERS_1A)
    folds_inf = RUNS["ceiling_path_v0@INF"][0]
    on_path = sum(1 for f in folds_inf if f["ticker"] in r["diffs"] and f["D"][h]["return"] == f["rho"][h - 1])
    say(f"@INF D{h}: fark {r['diff']:+.4f} [{r['ci'][0]:+.4f}, {r['ci'][1]:+.4f}]; tahmin = ρ_h olan fold {on_path}/{r['n']}")

# ============================================================ 8. Duyarlılık (adım 4): yalnız birincil hücre
say("\n=== Duyarlılık (bilgi amaçlı; model DEĞİL): birincil hücre D5 MAE − base_train_median ===")
SENS = {}


def sens_run(name, **kw):
    folds, src_sha = run_plan(f"ceiling_path_v0__sens_{name}", "ceiling_hazard_v0", "training", **kw)
    rows = []
    for f in folds:
        tk = f["ticker"]
        rv = rule_value(LEDGERS_1A["base_train_median"], tk, 5, "return")
        if rv is None or f["D"][5].get("post_break_status") != "OK":
            continue
        y = f["realized_R"][5]
        rows.append((tk, f["first_trading_date"][:7], abs(f["D"][5]["return"] - y), abs(rv - y)))
    res = paired(rows)
    res.pop("diffs")
    n_insuff = sum(1 for f in folds if f["status"] != "OK")
    brier = statistics.mean((clip(f["D"][5]["p_up"]) - f["realized_Y"][5]) ** 2 for f in folds if f["D"][5].get("post_break_status") == "OK")
    mae_all = statistics.mean(abs(f["D"][5]["return"] - f["realized_R"][5]) for f in folds if f["D"][5].get("post_break_status") == "OK")
    SENS[name] = {"primary": res, "n_folds_insufficient": n_insuff, "D5_brier": brier, "D5_mae_own_set": mae_all, "folds": folds, "src_sha": src_sha, "kw": kw}
    say(f"{name:14s} fark {res['diff']:+.4f} [{res['ci'][0]:+.4f}, {res['ci'][1]:+.4f}] n={res['n']} model {res['model']:.4f} kural {res['rule']:.4f}; POST_BREAK_INSUFFICIENT fold {n_insuff}")
    return res


sens_run("v0_ref")  # kontrol: şartname v0 (aynı olmalı)
sens_run("nmin5", n_min=5)
sens_run("nmin20", n_min=20)
sens_run("single_group", single_group=True)
sens_run("nearest_only", nearest_only=True)
assert abs(SENS["v0_ref"]["primary"]["diff"] - prim["diff"]) < 1e-15
OUT["sensitivity"] = {k: {kk: vv for kk, vv in v.items() if kk not in ("folds",)} for k, v in SENS.items()}

# ============================================================ 9. Çıktı
assert not any(m == "borsai" or m.startswith("borsai.") for m in sys.modules), "borsai import edilmiş!"


def write_ledger_csv(path: Path, folds):
    cols = ["model_id", "fold_id", "ticker", "first_trading_date", "prediction_date", "survival_model_id",
            "survival_ledger_sha256", "survival_fold_status"] + [f"S_{k}" for k in range(1, 11)] + [f"P_L_{l}" for l in range(11)]
    cols += ["ipo_price", "snapped_ipo_price", "tick"] + [f"C_{k}" for k in range(1, 11)] + [f"rho_{k}" for k in range(1, 11)]
    cols += [f"cells_n_{k}" for k in folds[0]["cells_n"]] + ["cells_max_session_date", "cells_ipos_sha256", "status"]
    for h in range(1, 11):
        cols += [f"D{h}_{x}" for x in ("return", "mean", "p_up", "q10", "q90", "post_break_status", "pooled_cells", "n_atoms")]
    cols += [f"realized_R_D{h}" for h in (1, 3, 5, 10)] + [f"realized_Y_D{h}" for h in range(1, 11)] + ["realized_L"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for f in folds:
            row = {k: f[k] for k in cols[:8]}
            row.update({f"S_{k}": f["S_str"][k - 1] for k in range(1, 11)})
            row.update({f"P_L_{l}": f["P_L"][l] for l in range(11)})
            row.update({"ipo_price": f["ipo_price"], "snapped_ipo_price": f["snapped_ipo_price"], "tick": f["tick"]})
            row.update({f"C_{k}": f["C"][k - 1] for k in range(1, 11)})
            row.update({f"rho_{k}": f["rho"][k - 1] for k in range(1, 11)})
            row.update({f"cells_n_{k}": v for k, v in f["cells_n"].items()})
            row.update({"cells_max_session_date": f["cells_max_session_date"], "cells_ipos_sha256": f["cells_ipos_sha256"], "status": f["status"]})
            for h in range(1, 11):
                d = f["D"][h]
                for x in ("return", "mean", "p_up", "q10", "q90"):
                    row[f"D{h}_{x}"] = d.get(x)
                row[f"D{h}_post_break_status"] = d["post_break_status"]
                row[f"D{h}_pooled_cells"] = json.dumps(d["pooled_cells"], separators=(",", ":"))
                row[f"D{h}_n_atoms"] = d.get("n_atoms", 0)
            for h in (1, 3, 5, 10):
                row[f"realized_R_D{h}"] = f["realized_R"][h]
            for h in range(1, 11):
                row[f"realized_Y_D{h}"] = f["realized_Y"][h]
            row["realized_L"] = f["realized_L"]
            w.writerow(row)


for mid, (folds, _) in RUNS.items():
    write_ledger_csv(HERE / f"repro_{mid}_fold_ledger.csv", folds)
for name, v in SENS.items():
    write_ledger_csv(HERE / f"sens_{name}_fold_ledger.csv", v["folds"])
OUT["ledger_files"] = {mid: f"repro_{mid}_fold_ledger.csv" for mid in RUNS} | {f"sens_{k}": f"sens_{k}_fold_ledger.csv" for k in SENS}
OUT["inputs_sha256"] = {str(p.relative_to(ROOT)): sha256_file(p) for p in (TT_CSV, SESS_CSV, CAL_CSV, PB_CSV)}
OUT["source_ledgers_sha256"] = {mid: sha for mid, (_, sha) in RUNS.items()}
(HERE / "repro_output.json").write_text(json.dumps(OUT, indent=1, default=str), encoding="utf-8")
(HERE / "repro_stdout.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
say("DONE")

#!/usr/bin/env python
"""BORSAI_FAZ7_FABLE_C_SPEC_20260927 — (C) keşif betiği. Yalnız okur; hiçbir dosyaya yazmaz (çıktı stdout).

Keşif kümesi: H99 (99) + eski kohortun açık kümesi (71 = data/outcomes_oot/*.csv adları).
Kasa: hiçbir kasa üyesinin dosyası açılmaz. Kasa hakkında yalnız kohort dosyasındaki yıl/rejim sayımları ve
coverage.csv'lerden alan başına DOLU sayıları kullanılır; hiçbir kasa kodu basılmaz (bekçi: `_assert_open`).
Kullanım:
  .venv/bin/python docs/specs_faz7_c/ekler/kesif_c.py            # rapor (metin)
  .venv/bin/python docs/specs_faz7_c/ekler/kesif_c.py --csv      # denenenler.csv (stdout)
  .venv/bin/python docs/specs_faz7_c/ekler/kesif_c.py --kasa     # yalnız kasa sayımları
"""
from __future__ import annotations

import csv
import glob
import itertools
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

OPEN_SET = frozenset(os.path.basename(p)[:-4] for p in glob.glob(str(ROOT / "data/outcomes_oot/*.csv")))
assert len(OPEN_SET) == 71, len(OPEN_SET)
BLOCK_SEED = 20260921
B_REPS = 4000
VARIANTS: list[dict] = []          # denenenler.csv satırları
_vid = itertools.count(1)


def log_variant(kind, target, features, method, param, subset, n, metric, value, note=""):
    VARIANTS.append(dict(id=next(_vid), kind=kind, target=target, features="+".join(features) if isinstance(features, (list, tuple)) else features,
                         method=method, param=param, subset=subset, n=n, metric=metric,
                         value="" if value is None else f"{value:.4f}", note=note))


def _assert_open(ticker: str) -> None:
    if ticker not in OPEN_SET:
        raise SystemExit(f"HİJYEN: açık kümede olmayan eski kohort üyesi dosyası istendi (kod basılmıyor)")


# ------------------------------------------------------------------ veri
def read_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def dec(x):
    return None if x in (None, "", "DATA_NOT_FOUND", "NA") else float(x)


def load_rows():
    v2 = read_csv(ROOT / "data/training_table_v2.csv")
    assert len(v2) == 170
    master = {r["ticker"]: r for r in read_csv(ROOT / "data/raw/HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv")}
    rows = []
    for r in v2:
        t = r["ticker"]
        coh = r["cohort"]
        if coh == "OOT_OPEN":
            _assert_open(t)
        price = float(r["ipo_price_tl"]); shares = float(r["shares_offered"]); post = float(r["post_ipo_share_capital"])
        size = dec(r["ipo_size_tl"]) or price * shares
        f3 = dec(r["total_demand_multiple"])
        tufe = float(r["tufe_index"])
        d = dict(ticker=t, cohort=coh, T=r["first_trading_date"], year=r["first_trading_date"][:4], month=r["first_trading_date"][:7],
                 alloc=r["alloc_regime"], sale=r["sale_method"] or None, market=r["market"] or None,
                 f1=math.log(size), f1r=math.log(size / (tufe / 100.0)), f2=shares / post * 100.0, f3=f3,
                 ln_f3=(math.log(f3) if f3 else None), f3_missing=1.0 if f3 is None else 0.0,
                 f4=float(r["capital_increase_shares"]) / shares * 100.0, ln_price=math.log(price), price=price,
                 add_sale=1.0 if dec(r["additional_sale_shares"]) else 0.0, shares=shares, size_real=size / (tufe / 100.0),
                 L=int(r["ceiling_streak_L"]),
                 y1=1 - int(r["ceiling_close_D1"]), y2=1 - int(r["Y_D1"]), y3=1 - int(r["Y_D5"]), y4=1 - int(r["Y_D10"]),
                 y2s=1 if float(r["R_D1"]) < 0 else 0, y3s=1 if float(r["R_D5"]) < 0 else 0, y4s=1 if float(r["R_D10"]) < 0 else 0)
        # aday alanlar
        if coh == "H99":
            m = master[t]
            if m["distribution_method"] != "DATA_NOT_FOUND":
                d.update(prospectus_from_master(m))
                d["sale"] = "ON_EXCHANGE" if "Borsa'da satış" in m["price_determination_method"] else "OFF_EXCHANGE_BOOKBUILD"
            ic = dec(m["investor_count"])
            if ic:
                d["investor_count"] = ic
            d["retail_alloc"] = dec(m["retail_allocation_pct"]); d["retail_mult"] = dec(m["retail_demand_multiple"])
        else:
            d.update(prospectus_from_faz7(t))
            d.update(candidates_from_faz6(t))
        if d.get("investor_count"):
            d["ln_inv"] = math.log(d["investor_count"]); d["ln_lot"] = math.log(shares / d["investor_count"])
            d["ln_tl_inv_real"] = math.log(d["size_real"] / d["investor_count"])
        d["add_sale_pct"] = (dec(r["additional_sale_shares"]) or 0.0) / shares * 100.0
        d["add_sale_missing"] = 1.0 if r["additional_sale_shares"] == "" else 0.0
        d["on_ex"] = None if d.get("sale") is None else (1.0 if d["sale"] == "ON_EXCHANGE" else 0.0)
        d["sh_lt365"] = None if d.get("sh_lock") is None else (1.0 if d["sh_lock"] < 365 else 0.0)
        d["r_pre_equal"] = 0.0 if d["alloc"] == "EQUAL_DIST_20230330" else 1.0
        rows.append(d)
    return rows


def _dm_flags(dm: str) -> dict:
    s = dm.lower()
    on_ex = ("birincil piyasa" in s) or ("borsa'da satış" in s) or ("borsada satış" in s)
    retail_equal = (not on_ex) and ("eşit" in s.split(";")[0])
    return dict(dm_on_exchange=1.0 if on_ex else 0.0, dm_retail_equal=1.0 if retail_equal else 0.0,
                dm_retail_prop=0.0 if (on_ex or retail_equal) else 1.0)


def prospectus_from_master(m):
    d = dict(ps_planned=1.0 if m["price_stability_planned"] == "TRUE" else 0.0, ps_days=float(m["price_stability_days"]),
             issuer_lock=float(m["issuer_lockup_days"]), sh_lock=float(m["shareholder_lockup_days"]),
             gyo=1.0 if m["sector"].lower().startswith("gayrimenkul yatırım") else 0.0, sector=m["sector"])
    d.update(_dm_flags(m["distribution_method"])); d["dm_raw"] = m["distribution_method"]
    return d


def prospectus_from_faz7(t):
    _assert_open(t)
    f = json.load(open(ROOT / f"registry/oot/candidate_features_faz7/{t}.json"))["fields"]
    days = float(f["price_stability_days"]["value"])
    if f["price_stability_days"].get("unit") == "iş günü":
        days = days * 7 / 5          # yaklaşık takvim günü (10 iş günü ≈ 14); denenenler.csv'de not
    d = dict(ps_planned=1.0 if f["price_stability_planned"]["value"] == "TRUE" else 0.0, ps_days=days,
             issuer_lock=float(f["issuer_lockup_days"]["value"]), sh_lock=float(f["shareholder_lockup_days"]["value"]),
             gyo=1.0 if f["sector"]["value"].lower().startswith("gayrimenkul yatırım") else 0.0, sector=f["sector"]["value"],
             part_idx=f["participation_index_eligible"]["value"])
    comps = f["shareholder_lockup_days"].get("components") or []
    mutlak = [float(c["days"]) for c in comps if c.get("type") == "MUTLAK"]
    d["sh_lock_mutlak_max"] = max(mutlak) if mutlak else 0.0
    d.update(_dm_flags(f["distribution_method"]["value"])); d["dm_raw"] = f["distribution_method"]["value"]
    return d


def candidates_from_faz6(t):
    _assert_open(t)
    f = json.load(open(ROOT / f"registry/oot/candidate_features/{t}.json"))["fields"]
    g = lambda k: dec((f.get(k) or {}).get("value"))
    return dict(investor_count=g("investor_count"), retail_alloc=g("retail_allocation_pct"), retail_mult=g("retail_demand_multiple"))


def add_winsor(rows):
    """Keşif amaçlı: f3 ham değeri havuzun Type-7 [p05, p95]'ine kırpılır (V1.5 winsor kalıbı); f1r de."""
    for col, src in (("f3_w", "f3"), ("f1r_w_raw", "size_real")):
        vals = np.array(sorted(r[src] for r in rows if r.get(src) is not None))
        lo, hi = np.percentile(vals, 5, method="linear"), np.percentile(vals, 95, method="linear")
        for r in rows:
            if r.get(src) is not None:
                r[col] = float(min(max(r[src], lo), hi))
    for r in rows:
        r["ln_f1r_w"] = math.log(r["f1r_w_raw"])
    return rows


def section_focus(rows):
    print("\n## 5b. Odak: aday özellik kümeleri, aktarım hücrelerinde aralık [KEŞİF]\n")
    print("Aktarım hücresi kasa testinin en yakın benzeridir: model yalnız H99'da fit, açık kümede skor; taban = H99 oranı (donmuş base_rate gibi).")
    print("Ay-blok bootstrap aralığı keşif etiketlidir.\n")
    print("| hedef | özellikler | λ | LOO fark [%95] (n) | H99→açık fark [%95] (n) | açık→H99 fark [%95] (n) | AUC açık (H99 fit) |")
    print("|---|---|---|---|---|---|---|")
    sets = [["f1r", "ln_f3", "add_sale"], ["ln_f1r_w", "f3_w", "add_sale"], ["f1r", "f3_w", "add_sale"], ["f1r", "ln_f3", "add_sale_pct"],
            ["f1r", "add_sale"], ["ln_f3", "add_sale"], ["add_sale"], ["f1r", "ln_f3"], ["f1r"], ["ln_f3"], ["ln_f1r_w", "f3_w"]]
    for k in ("y4", "y1", "y3"):
        for feats in sets:
            for lam in (1.0, 10.0):
                preds = loo_eval(rows, feats, k, lam)
                y = np.array([q["y"] for q in preds]); p = np.array([q["p"] for q in preds]); pb = np.array([q["pb"] for q in preds])
                d = (p - y) ** 2 - (pb - y) ** 2; ci = block_bootstrap(d, [q["month"] for q in preds])
                cells = [f"{d.mean():+.4f} {fmt_ci(ci)} ({len(y)})"]
                auc_open = None
                for a, b in (("H99", "OOT_OPEN"), ("OOT_OPEN", "H99")):
                    t = transfer_eval(rows, feats, k, lam, a, b)
                    if not t:
                        cells.append("—"); continue
                    yy = np.array([q["y"] for q in t]); pp_ = np.array([q["p"] for q in t]); pbb = np.array([q["pb"] for q in t])
                    dd = (pp_ - yy) ** 2 - (pbb - yy) ** 2; cci = block_bootstrap(dd, [q["month"] for q in t])
                    cells.append(f"{dd.mean():+.4f} {fmt_ci(cci)} ({len(yy)})")
                    log_variant("focus", k, feats, f"l2_logit_transfer_{a}_to_{b}", lam, f"{a}→{b}", len(yy), "brier_diff_vs_train_rate", float(dd.mean()))
                    if a == "H99":
                        auc_open = auc(pp_, yy)
                log_variant("focus", k, feats, "l2_logit_loo", lam, "H99+açık", len(y), "brier_diff_vs_base", float(d.mean()))
                print(f"| {k} | {'+'.join(feats)} | {lam:g} | {cells[0]} | {cells[1]} | {cells[2]} | {'—' if auc_open is None else f'{auc_open:.3f}'} |")
    # katsayı işaretleri (havuz, λ = 10) — yön beyanı için
    print("\nHavuzda (H99+açık, λ = 10) standartlaştırılmış katsayılar (sabit hariç):\n")
    for k in ("y4", "y1"):
        for feats in (["f1r", "ln_f3", "add_sale"], ["f1r", "add_sale"], ["add_sale"]):
            sub = [r for r in rows if all(r.get(f) is not None for f in feats)]
            X = np.array([[r[f] for f in feats] for r in sub]); yv = np.array([r[k] for r in sub])
            b, mu, sd = fit_logit_l2(X, yv, 10.0)
            print(f"- {k} {'+'.join(feats)}: sabit {b[0]:+.3f}; " + ", ".join(f"{f} {c:+.3f}" for f, c in zip(feats, b[1:])) + f"; add_sale ham katsayı (logit farkı) ≈ {b[feats.index('add_sale')+1]/sd[feats.index('add_sale')]:+.2f}" if "add_sale" in feats else "")
    print("\nEk satış alanı boş (add_sale_missing = 1) satır sayısı: H99", sum(1 for r in rows if r["cohort"] == "H99" and r["add_sale_missing"] == 1), "açık", sum(1 for r in rows if r["cohort"] != "H99" and r["add_sale_missing"] == 1))


def load_same_week(rows):
    """Aynı hafta listelenen arz sayısı: H99 99 + kohortun 135 MEMBER'ı (kasa dahil; yalnız tarih okunur, kod basılmaz)."""
    dates = [r["T"] for r in rows if r["cohort"] == "H99"]
    for c in read_csv(ROOT / "registry/oot/cohort_pre_h99.csv"):
        if c["status"] == "MEMBER":
            dates.append(c["first_trading_date"])
    dates = sorted(dates)
    def wd_between(a, b):   # hafta içi gün farkı (tatiller yok sayılır; deterministik yaklaşım)
        a, b = date.fromisoformat(a), date.fromisoformat(b)
        if a > b: a, b = b, a
        return sum(1 for i in range((b - a).days) if (a + timedelta(days=i)).weekday() < 5)
    for r in rows:
        T = r["T"]
        r["same_wk"] = float(sum(1 for d in dates if d != T and wd_between(d, T) <= 5) + sum(1 for d in dates if d == T) - 1)
        r["prior_5wd"] = float(sum(1 for d in dates if d < T and wd_between(d, T) <= 5))
    return rows


def load_market20(rows):
    from borsai import market20 as m20
    h99 = m20.h99_market20([(r["ticker"], r["T"]) for r in rows if r["cohort"] == "H99"])
    src = m20.load_oot_sources()
    for r in rows:
        if r["cohort"] == "H99":
            res = h99[r["ticker"]]
        else:
            res = m20.oot_market20(r["T"], src)
        r["f6"] = None if res.f6 is None else float(res.f6)


def load_comparators(rows):
    """Donmuş modellerin tahminleri: H99 walk-forward ledger'ları; açık küme S2 kayıtları (yalnız açık üyeler)."""
    v15 = {}
    for r in read_csv(ROOT / "tests/reference/macos_golden/v1_5_h99_fold_ledger.csv"):
        if r["logit_probability"] not in ("", None):
            v15[(r["ticker"], r["horizon"])] = float(r["logit_probability"])
    brate = {}
    for r in read_csv(ROOT / "tests/reference/macos_golden/base_rate_fold_ledger.csv"):
        if r.get("rule_p_up") not in ("", None):
            brate[(r["ticker"], r["horizon"])] = float(r["rule_p_up"])
    haz = {r["ticker"]: float(r["S_1"]) for r in read_csv(ROOT / "tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv") if r["status"] == "FIT_OK"}
    km = {r["ticker"]: float(r["S_1"]) for r in read_csv(ROOT / "tests/reference/macos_golden_faz1b/base_km_expanding_fold_ledger.csv") if r.get("S_1")}
    for r in rows:
        t = r["ticker"]
        if r["cohort"] == "H99":
            for h in ("D1", "D5", "D10"):
                r[f"v15_pdown_{h}"] = None if (t, h) not in v15 else 1 - v15[(t, h)]
                r[f"brate_pdown_{h}"] = None if (t, h) not in brate else 1 - brate[(t, h)]
            r["haz_p_noceil"] = None if t not in haz else 1 - haz[t]
            r["km_p_noceil"] = None if t not in km else 1 - km[t]
        else:
            _assert_open(t)
            files = sorted(glob.glob(str(ROOT / f"registry/oot/records/{t}/*.json")))
            rec = json.load(open(files[0]))
            models = {m["model_id"]: m for m in rec["models"]}
            v = models["v1_5_h99"]
            for h in ("D1", "D5", "D10"):
                r[f"v15_pdown_{h}"] = None if v["status"] != "PREDICTED" else 1 - v["output"][h]["p_up"]
                r[f"brate_pdown_{h}"] = 1 - rec["comparators"]["base_rate"]["output"][h]["p_up"]
            hz = models["ceiling_hazard_v0"]
            r["haz_p_noceil"] = None if hz["status"] != "PREDICTED" else 1 - hz["output"]["S"][0]
            r["km_p_noceil"] = 1 - rec["comparators"]["base_km_expanding"]["output"]["S"][0]


# ------------------------------------------------------------------ istatistik
def auc(x, y):
    x = np.asarray(x, float); y = np.asarray(y, int)
    pos, neg = x[y == 1], x[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return None
    gt = (pos[:, None] > neg[None, :]).sum(); eq = (pos[:, None] == neg[None, :]).sum()
    return (gt + 0.5 * eq) / (len(pos) * len(neg))


def block_bootstrap(d, blocks, B=B_REPS, seed=BLOCK_SEED):
    d = np.asarray(d, float)
    if len(d) < 10 or len(set(blocks)) < 6:
        return None
    rng = np.random.Generator(np.random.PCG64(seed))
    ids = sorted(set(blocks)); by = {b: d[[i for i, bb in enumerate(blocks) if bb == b]] for b in ids}
    stats = np.empty(B)
    for i in range(B):
        pick = rng.choice(ids, size=len(ids), replace=True)
        stats[i] = np.concatenate([by[b] for b in pick]).mean()
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def fit_logit_l2(X, y, lam, w=None):
    """Standartlaştırılmış X (sabit ekli), cezasız sabit; Newton. Döner (coef, mu, sd)."""
    mu = X.mean(0); sd = X.std(0); sd[sd == 0] = 1.0
    Z = np.c_[np.ones(len(X)), (X - mu) / sd]
    pen = np.r_[0.0, np.full(X.shape[1], lam)]
    b = np.zeros(Z.shape[1]); ww = np.ones(len(y)) if w is None else w
    for _ in range(100):
        p = 1 / (1 + np.exp(-Z @ b))
        g = Z.T @ (ww * (p - y)) + pen * b
        H = (Z * (ww * p * (1 - p))[:, None]).T @ Z + np.diag(pen)
        step = np.linalg.solve(H, g)
        b -= step
        if np.abs(step).max() < 1e-10:
            break
    return b, mu, sd


def predict_logit(b, mu, sd, X):
    Z = np.c_[np.ones(len(X)), (X - mu) / sd]
    return 1 / (1 + np.exp(-Z @ b))


def loo_eval(rows, feats, target, lam):
    """Arz-bırak (LOO) L2 lojistik; taban oran da LOO. Döner satır başına (p, p_base, y, month, cohort)."""
    sub = [r for r in rows if all(r.get(f) is not None for f in feats)]
    X = np.array([[r[f] for f in feats] for r in sub]); y = np.array([r[target] for r in sub])
    out = []
    for i in range(len(sub)):
        m = np.ones(len(sub), bool); m[i] = False
        if y[m].sum() in (0, m.sum()):
            continue
        b, mu, sd = fit_logit_l2(X[m], y[m], lam)
        p = float(predict_logit(b, mu, sd, X[i:i + 1])[0])
        out.append(dict(p=p, pb=float(y[m].mean()), y=int(y[i]), month=sub[i]["month"], cohort=sub[i]["cohort"], year=sub[i]["year"], alloc=sub[i]["alloc"]))
    return out


def transfer_eval(rows, feats, target, lam, train_coh, test_coh):
    tr = [r for r in rows if r["cohort"] == train_coh and all(r.get(f) is not None for f in feats)]
    te = [r for r in rows if r["cohort"] == test_coh and all(r.get(f) is not None for f in feats)]
    if len(tr) < 10 or len(te) < 10:
        return None
    Xtr = np.array([[r[f] for f in feats] for r in tr]); ytr = np.array([r[target] for r in tr])
    if ytr.sum() in (0, len(ytr)):
        return None
    b, mu, sd = fit_logit_l2(Xtr, ytr, lam)
    Xte = np.array([[r[f] for f in feats] for r in te]); yte = np.array([r[target] for r in te])
    p = predict_logit(b, mu, sd, Xte)
    return [dict(p=float(pi), pb=float(ytr.mean()), y=int(yi), month=r["month"], cohort=r["cohort"], year=r["year"], alloc=r["alloc"]) for pi, yi, r in zip(p, yte, te)]


def summarize(preds, label, target, feats, method, param, subset_note=""):
    if not preds:
        return None
    y = np.array([q["y"] for q in preds]); p = np.array([q["p"] for q in preds]); pb = np.array([q["pb"] for q in preds])
    d = (p - y) ** 2 - (pb - y) ** 2
    ci = block_bootstrap(d, [q["month"] for q in preds])
    a = auc(p, y)
    res = dict(n=len(y), events=int(y.sum()), brier=float(((p - y) ** 2).mean()), brier_base=float(((pb - y) ** 2).mean()),
               diff=float(d.mean()), ci=ci, auc=a)
    log_variant("multi" if len(feats) > 1 else "uni-model", target, feats, method, param, subset_note or label, len(y), "brier_diff_vs_base", res["diff"],
                note=f"auc={a:.3f}" if a is not None else "")
    return res


def fmt_ci(ci):
    return "—" if ci is None else f"[{ci[0]:+.4f}, {ci[1]:+.4f}]"


# ------------------------------------------------------------------ bölümler
TARGETS = [("y1", "D1'de tavan yok (L = 0)"), ("y2", "D1 kapanışı ≤ arz (1 − Y_D1)"), ("y3", "D5 kapanışı ≤ arz (1 − Y_D5)"), ("y4", "D10 kapanışı ≤ arz (1 − Y_D10)")]


def section_counts(rows, sealed_counts):
    print("## 1. Olay tanımları ve sayımlar [ÖLÇTÜM]\n")
    print("Kesin-altı (R_h < 0) sayıları da verilir; 1 − Y_h tanımı kapanış = arz fiyatını da olay sayar.\n")
    print("| hedef | H99 n / olay / oran | açık n / olay / oran | H99 kesin-altı | açık kesin-altı |")
    print("|---|---|---|---|---|")
    for k, lab in TARGETS:
        h = [r for r in rows if r["cohort"] == "H99"]; o = [r for r in rows if r["cohort"] != "H99"]
        eh, eo = sum(r[k] for r in h), sum(r[k] for r in o)
        sh = sum(r[k + "s"] for r in h) if k != "y1" else eh; so = sum(r[k + "s"] for r in o) if k != "y1" else eo
        print(f"| {k}: {lab} | {len(h)} / {eh} / {eh/len(h):.3f} | {len(o)} / {eo} / {eo/len(o):.3f} | {sh} | {so} |")
    print("\n### 1.1 Yıl kırılımı (n / olay: y1, y2, y3, y4)\n")
    print("| kohort | yıl | n | y1 | y2 | y3 | y4 |")
    print("|---|---|---|---|---|---|---|")
    strata = {}
    for coh in ("H99", "OOT_OPEN"):
        for yr in sorted(set(r["year"] for r in rows if r["cohort"] == coh)):
            s = [r for r in rows if r["cohort"] == coh and r["year"] == yr]
            strata[(coh, yr)] = s
            print(f"| {coh} | {yr} | {len(s)} | " + " | ".join(str(sum(r[k] for r in s)) for k, _ in TARGETS) + " |")
    print("\n### 1.2 Tahsis rejimi kırılımı\n")
    print("| kohort | rejim | n | y1 | y2 | y3 | y4 |")
    print("|---|---|---|---|---|---|---|")
    for coh in ("H99", "OOT_OPEN"):
        for al in sorted(set(r["alloc"] for r in rows if r["cohort"] == coh)):
            s = [r for r in rows if r["cohort"] == coh and r["alloc"] == al]
            print(f"| {coh} | {al} | {len(s)} | " + " | ".join(str(sum(r[k] for r in s)) for k, _ in TARGETS) + " |")
    print("\n### 1.3 Açık kümede satış yöntemi kırılımı\n")
    print("| satış | n | y1 | y2 | y3 | y4 |\n|---|---|---|---|---|---|")
    for sm in ("ON_EXCHANGE", "OFF_EXCHANGE_BOOKBUILD"):
        s = [r for r in rows if r["cohort"] != "H99" and r["sale"] == sm]
        print(f"| {sm} | {len(s)} | " + " | ".join(str(sum(r[k] for r in s)) for k, _ in TARGETS) + " |")
    print("\n### 1.4 Kasa için beklenen olay sayısı (kasanın yıl sayımları × açık kümenin yıl oranları; kasa sonucu yok)\n")
    print(f"Kasa yıl sayımları (kohort dosyası, yalnız sayım): {dict(sealed_counts['year'])}; rejim: {dict(sealed_counts['alloc'])}; satış: {dict(sealed_counts['sale'])}\n")
    print("| hedef | beklenen (yıl ağırlıklı, açık oranlar) | beklenen (rejim ağırlıklı, açık oranlar) | beklenen (açık havuz oranı) | beklenen (H99 oranı; üst sınır) |")
    print("|---|---|---|---|---|")
    exp = {}
    for k, _ in TARGETS:
        e_year = sum(n * (sum(r[k] for r in strata[("OOT_OPEN", yr)]) / len(strata[("OOT_OPEN", yr)])) for yr, n in sealed_counts["year"].items())
        e_reg = 0.0
        for al, n in sealed_counts["alloc"].items():
            s = [r for r in rows if r["cohort"] != "H99" and r["alloc"] == al]
            e_reg += n * sum(r[k] for r in s) / len(s)
        o = [r for r in rows if r["cohort"] != "H99"]; h = [r for r in rows if r["cohort"] == "H99"]
        e_pool = 64 * sum(r[k] for r in o) / len(o); e_h = 64 * sum(r[k] for r in h) / len(h)
        exp[k] = (e_year, e_reg, e_pool, e_h)
        print(f"| {k} | {e_year:.1f} | {e_reg:.1f} | {e_pool:.1f} | {e_h:.1f} |")
    return exp


def section_coverage(rows):
    print("\n## 2. Özellik kapsaması (dolu değer sayısı; H99 / açık)\n")
    feats = ["f1", "f1r", "f2", "f3", "f4", "ln_price", "f6", "same_wk", "prior_5wd", "sale", "market", "alloc",
             "ps_planned", "ps_days", "issuer_lock", "sh_lock", "dm_retail_equal", "dm_on_exchange", "gyo", "part_idx",
             "investor_count", "ln_lot", "retail_alloc", "retail_mult", "v15_pdown_D10", "haz_p_noceil"]
    print("| alan | H99 | açık |\n|---|---|---|")
    for f in feats:
        h = sum(1 for r in rows if r["cohort"] == "H99" and r.get(f) is not None)
        o = sum(1 for r in rows if r["cohort"] != "H99" and r.get(f) is not None)
        print(f"| {f} | {h} | {o} |")
    print("\nKategori dağılımları (açık / H99-20):")
    for f in ("dm_raw", "sale", "market", "ps_days", "issuer_lock", "sh_lock", "sh_lock_mutlak_max", "part_idx"):
        co = Counter(r.get(f) for r in rows if r["cohort"] != "H99"); ch = Counter(r.get(f) for r in rows if r["cohort"] == "H99" and r.get("dm_raw"))
        print(f"- {f}: açık {dict(co.most_common(8))} | H99-20 {dict(ch.most_common(8))}")


NUMERIC = [("f1", "ln arz büyüklüğü (nominal TL)"), ("f1r", "ln reel büyüklük (TÜFE 2025=100)"), ("f2", "halka açıklık %"),
           ("ln_f3", "ln talep katı (f3 dolu)"), ("f4", "sermaye artırımı payı %"), ("ln_price", "ln arz fiyatı"),
           ("f6", "XU100 20 seans getirisi"), ("same_wk", "±5 iş günü listelenen arz sayısı"), ("prior_5wd", "önceki 5 iş günü arz sayısı"),
           ("ps_days", "fiyat istikrarı gün"), ("issuer_lock", "ihraççı satmama gün"), ("sh_lock", "ortak satmama gün (ilk gevşeyen)"),
           ("ln_inv", "ln yatırımcı sayısı"), ("ln_lot", "ln kişi başı lot"), ("ln_tl_inv_real", "ln kişi başı reel TL"),
           ("retail_alloc", "bireysel tahsisat %"), ("retail_mult", "bireysel talep katı")]
BINARY = [("f3_missing", "talep katı yok"), ("add_sale", "ek satış kullanıldı"), ("on_ex", "borsada satış (kohort/ana tablo)"), ("sh_lt365", "ortak satmama < 365"), ("ps_planned", "fiyat istikrarı planlı"),
          ("dm_retail_equal", "bireysele eşit dağıtım"), ("dm_on_exchange", "borsada satış (dağıtım alanından)"), ("gyo", "GYO")]


def section_univariate(rows):
    print("\n## 3. Tek değişkenli keşif [KEŞİF]\n")
    print("AUC: özellik yükseldikçe olay olasılığı artıyorsa > 0.5. Her satır bir denenen varyanttır.\n")
    for k, lab in TARGETS:
        print(f"\n### 3.{k} — {lab}\n")
        print("| özellik | küme | n (olay) | medyan olay / diğer | AUC | rejim AUC'leri (PRE / THRESH / EQUAL-açık / H99) |")
        print("|---|---|---|---|---|---|")
        for f, flab in NUMERIC:
            for coh, cname in (("ALL", "H99+açık"), ("H99", "H99"), ("OOT_OPEN", "açık")):
                s = [r for r in rows if r.get(f) is not None and (coh == "ALL" or r["cohort"] == coh)]
                if len(s) < 10:
                    continue
                y = [r[k] for r in s]; x = [r[f] for r in s]
                if sum(y) < 2:
                    continue
                a = auc(x, y)
                me = np.median([r[f] for r in s if r[k] == 1]); mo = np.median([r[f] for r in s if r[k] == 0])
                regs = []
                if coh == "ALL":
                    for al in ("PRE_20211111", "THRESH100_20211111"):
                        ss = [r for r in s if r["alloc"] == al]
                        aa = auc([r[f] for r in ss], [r[k] for r in ss]) if len(ss) >= 8 else None
                        regs.append("—" if aa is None else f"{aa:.2f}")
                    ss = [r for r in s if r["alloc"] == "EQUAL_DIST_20230330" and r["cohort"] != "H99"]
                    aa = auc([r[f] for r in ss], [r[k] for r in ss]) if len(ss) >= 8 else None
                    regs.append("—" if aa is None else f"{aa:.2f}")
                    ss = [r for r in s if r["cohort"] == "H99"]
                    aa = auc([r[f] for r in ss], [r[k] for r in ss]) if len(ss) >= 8 else None
                    regs.append("—" if aa is None else f"{aa:.2f}")
                log_variant("uni", k, f, "auc", "", cname, len(s), "auc", a)
                print(f"| {f} ({flab}) | {cname} | {len(s)} ({sum(y)}) | {me:.2f} / {mo:.2f} | {a:.3f} | {' / '.join(regs) if regs else ''} |")
        print("\n| ikili özellik | küme | seviye 0: n (olay, oran) | seviye 1: n (olay, oran) | oran farkı |")
        print("|---|---|---|---|---|")
        for f, flab in BINARY:
            for coh, cname in (("ALL", "H99+açık"), ("H99", "H99"), ("OOT_OPEN", "açık")):
                s = [r for r in rows if r.get(f) is not None and (coh == "ALL" or r["cohort"] == coh)]
                s0 = [r for r in s if r[f] == 0]; s1 = [r for r in s if r[f] == 1]
                if len(s0) < 5 or len(s1) < 5:
                    continue
                r0 = sum(r[k] for r in s0) / len(s0); r1 = sum(r[k] for r in s1) / len(s1)
                log_variant("uni", k, f, "rate_diff", "", cname, len(s), "rate_diff", r1 - r0)
                print(f"| {f} ({flab}) | {cname} | {len(s0)} ({sum(r[k] for r in s0)}, {r0:.2f}) | {len(s1)} ({sum(r[k] for r in s1)}, {r1:.2f}) | {r1-r0:+.2f} |")
        # kategorik: tahsis rejimi, satış, pazar
        print("\n| kategorik | seviye | küme | n | olay | oran |\n|---|---|---|---|---|---|")
        for f in ("alloc", "sale", "market"):
            for coh, cname in (("ALL", "H99+açık"), ("OOT_OPEN", "açık")):
                s = [r for r in rows if r.get(f) is not None and (coh == "ALL" or r["cohort"] == coh)]
                for lv in sorted(set(r[f] for r in s)):
                    ss = [r for r in s if r[f] == lv]
                    print(f"| {f} | {lv} | {cname} | {len(ss)} | {sum(r[k] for r in ss)} | {sum(r[k] for r in ss)/len(ss):.2f} |")
            log_variant("uni", k, f, "level_rates", "", "H99+açık", len(rows), "", None)


def section_comparators(rows):
    print("\n## 4. Var olan donmuş modellerin bu olayları görme gücü [KEŞİF]\n")
    print("H99: walk-forward ledger tahminleri (v1_5_h99 logit p_up → 1 − p_up; ceiling_hazard_v0 S_1 → 1 − S_1). Açık: S2 kayıtları.\n")
    print("| hedef | karşılaştırıcı | küme | n (olay) | Brier model | Brier taban | fark | %95 aralık (keşif) | AUC |")
    print("|---|---|---|---|---|---|---|---|---|")
    pairs = [("y1", "haz_p_noceil", "km_p_noceil", "ceiling_hazard_v0 1−S_1 vs KM"), ("y2", "v15_pdown_D1", "brate_pdown_D1", "V1.5 1−p_up D1 vs taban"),
             ("y3", "v15_pdown_D5", "brate_pdown_D5", "V1.5 1−p_up D5 vs taban"), ("y4", "v15_pdown_D10", "brate_pdown_D10", "V1.5 1−p_up D10 vs taban")]
    for k, mf, bf, lab in pairs:
        for coh, cname in (("H99", "H99"), ("OOT_OPEN", "açık"), ("ALL", "H99+açık")):
            s = [r for r in rows if r.get(mf) is not None and r.get(bf) is not None and (coh == "ALL" or r["cohort"] == coh)]
            if len(s) < 10:
                continue
            y = np.array([r[k] for r in s]); p = np.array([r[mf] for r in s]); pb = np.array([r[bf] for r in s])
            d = (p - y) ** 2 - (pb - y) ** 2
            ci = block_bootstrap(d, [r["month"] for r in s]); a = auc(p, y)
            log_variant("comparator", k, mf, "frozen", "", cname, len(s), "brier_diff_vs_base", float(d.mean()), note=f"auc={a:.3f}")
            print(f"| {k} | {lab} | {cname} | {len(s)} ({y.sum()}) | {((p-y)**2).mean():.4f} | {((pb-y)**2).mean():.4f} | {d.mean():+.4f} | {fmt_ci(ci)} | {a:.3f} |")


def section_multivariate(rows):
    print("\n## 5. Çok değişkenli küçük modeller (≤ 3 özellik, L2 lojistik, arz-bırak) [KEŞİF]\n")
    print("Fark = Brier(model) − Brier(LOO taban oranı); negatif = model iyi. Aralık ay-blok bootstrap (keşif; hüküm değil).")
    print("Aktarım: yalnız H99'da fit → açık kümede test ve tersi (dönem dayanıklılığı; taban = eğitim kohortunun oranı).\n")
    lam_grid = [1.0, 10.0]
    universal = ["f1r", "f2", "ln_f3", "f4", "ln_price", "f6", "same_wk", "f1", "add_sale", "r_pre_equal"]
    prospectus = ["ps_planned", "sh_lock", "issuer_lock", "dm_retail_equal", "ln_lot", "ln_inv", "ln_tl_inv_real", "on_ex", "sh_lt365"]
    results = {}
    for k, lab in TARGETS:
        if k == "y2":
            continue   # açık kümede 2 olay: model anlamsız (yalnız sayım raporlanır)
        print(f"\n### 5.{k} — {lab}\n")
        print("| özellikler | λ | LOO n (olay) | Brier | taban | fark | %95 (keşif) | AUC | H99→açık fark (n) | açık→H99 fark (n) |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        sets = [[f] for f in universal] + [list(c) for c in itertools.combinations(["f1r", "f2", "ln_f3", "f4", "ln_price", "f6", "same_wk"], 2)] \
             + [["f1r", "ln_f3", "f2"], ["f1r", "ln_f3", "f4"], ["f1r", "ln_f3", "ln_price"], ["f1r", "ln_f3", "same_wk"], ["f1r", "ln_f3", "f6"], ["f2", "ln_f3", "ln_price"]] \
             + [["f1r", "add_sale"], ["ln_f3", "add_sale"], ["f2", "add_sale"], ["f1r", "ln_f3", "add_sale"], ["f1r", "f2", "add_sale"], ["f1r", "add_sale", "r_pre_equal"],
                ["f1r", "ln_f3", "r_pre_equal"], ["f1r", "r_pre_equal"], ["ln_f3", "r_pre_equal"], ["f1r", "ln_f3", "add_sale", "r_pre_equal"]] \
             + [["f1r", "ln_inv"], ["f1r", "ln_tl_inv_real"], ["ln_f3", "ln_tl_inv_real"], ["f1r", "ln_f3", "ln_inv"], ["add_sale", "ln_tl_inv_real"], ["f1r", "add_sale", "ln_tl_inv_real"],
                ["f1r", "on_ex"], ["f1r", "sh_lt365"], ["f1r", "add_sale", "sh_lt365"], ["f1r", "ln_f3", "on_ex"], ["ln_f3", "on_ex"], ["add_sale", "on_ex"], ["add_sale", "sh_lt365"]] \
             + [[f] for f in prospectus] + [["ps_planned", "sh_lock"], ["ps_planned", "ln_lot"], ["sh_lock", "ln_lot"], ["f1r", "ps_planned"], ["f1r", "sh_lock"], ["ln_f3", "ps_planned"], ["ln_f3", "sh_lock"],
                                            ["ln_f3", "ln_lot"], ["f1r", "ln_f3", "ps_planned"], ["f1r", "ln_f3", "sh_lock"], ["f1r", "ln_f3", "ln_lot"]]
        for feats in sets:
            for lam in lam_grid:
                preds = loo_eval(rows, feats, k, lam)
                res = summarize(preds, "LOO H99+açık", k, feats, "l2_logit_loo", lam)
                if res is None or res["n"] < 30:
                    continue
                tr1 = transfer_eval(rows, feats, k, lam, "H99", "OOT_OPEN"); tr2 = transfer_eval(rows, feats, k, lam, "OOT_OPEN", "H99")
                def tdiff(t):
                    if not t:
                        return "—"
                    y = np.array([q["y"] for q in t]); p = np.array([q["p"] for q in t]); pb = np.array([q["pb"] for q in t])
                    return f"{(((p-y)**2)-((pb-y)**2)).mean():+.4f} ({len(t)})"
                if tr1: summarize(tr1, "H99→açık", k, feats, "l2_logit_transfer_H99_to_open", lam)
                if tr2: summarize(tr2, "açık→H99", k, feats, "l2_logit_transfer_open_to_H99", lam)
                results[(k, tuple(feats), lam)] = res
                print(f"| {'+'.join(feats)} | {lam:g} | {res['n']} ({res['events']}) | {res['brier']:.4f} | {res['brier_base']:.4f} | {res['diff']:+.4f} | {fmt_ci(res['ci'])} | {res['auc']:.3f} | {tdiff(tr1)} | {tdiff(tr2)} |")
    return results


def section_crosstabs(rows):
    print("\n## 6a. Çapraz tablolar (dönem karışması denetimi) [KEŞİF]\n")
    print("| kohort | yıl | n | ek satış n (y4 olay) | ek satış yok n (y4 olay) | y1 olay (ek satış / yok) |\n|---|---|---|---|---|---|")
    for coh in ("H99", "OOT_OPEN"):
        for yr in sorted(set(r["year"] for r in rows if r["cohort"] == coh)):
            s = [r for r in rows if r["cohort"] == coh and r["year"] == yr]
            a = [r for r in s if r["add_sale"] == 1]; b = [r for r in s if r["add_sale"] == 0]
            print(f"| {coh} | {yr} | {len(s)} | {len(a)} ({sum(r['y4'] for r in a)}) | {len(b)} ({sum(r['y4'] for r in b)}) | {sum(r['y1'] for r in a)} / {sum(r['y1'] for r in b)} |")
    print("\nEk satış × satış yöntemi (açık küme): | satış | ek satış n (y4) | ek satış yok n (y4) |\n|---|---|---|")
    for sm in ("ON_EXCHANGE", "OFF_EXCHANGE_BOOKBUILD"):
        s = [r for r in rows if r["cohort"] != "H99" and r["sale"] == sm]
        a = [r for r in s if r["add_sale"] == 1]; b = [r for r in s if r["add_sale"] == 0]
        print(f"| {sm} | {len(a)} ({sum(r['y4'] for r in a)}) | {len(b)} ({sum(r['y4'] for r in b)}) |")
    print("\nOrtak satmama < 365 × yıl (açık küme): | yıl | <365 n (y4, y1) | ≥365 n (y4, y1) |\n|---|---|---|")
    for yr in ("2020", "2021", "2022", "2023"):
        s = [r for r in rows if r["cohort"] != "H99" and r["year"] == yr]
        a = [r for r in s if r["sh_lt365"] == 1]; b = [r for r in s if r["sh_lt365"] == 0]
        print(f"| {yr} | {len(a)} ({sum(r['y4'] for r in a)}, {sum(r['y1'] for r in a)}) | {len(b)} ({sum(r['y4'] for r in b)}, {sum(r['y1'] for r in b)}) |")
    print("\nEk satış × f3 (açık+H99): | ek satış | n | f3 medyan | f1r medyan | y4 oran |\n|---|---|---|---|---|")
    for v in (0.0, 1.0):
        s = [r for r in rows if r["add_sale"] == v]
        f3s = [r["f3"] for r in s if r["f3"] is not None]
        print(f"| {int(v)} | {len(s)} | {np.median(f3s):.2f} | {np.median([r['f1r'] for r in s]):.2f} | {sum(r['y4'] for r in s)/len(s):.2f} |")
    print("\nKişi başı reel TL × yıl (açık): | yıl | n | medyan ln_tl_inv_real | y4 oran üst yarı / alt yarı |\n|---|---|---|---|")
    for yr in ("2021", "2022", "2023"):
        s = sorted([r for r in rows if r["cohort"] != "H99" and r["year"] == yr and r.get("ln_tl_inv_real") is not None], key=lambda r: r["ln_tl_inv_real"])
        h = len(s) // 2
        lo, hi = s[:h], s[h:]
        print(f"| {yr} | {len(s)} | {np.median([r['ln_tl_inv_real'] for r in s]):.2f} | {sum(r['y4'] for r in hi)/len(hi):.2f} / {sum(r['y4'] for r in lo)/len(lo):.2f} |")


def section_rules(rows):
    print("\n## 6. Tek eşikli kurallar [KEŞİF]\n")
    print("| hedef | kural | küme | n | seçilen olay / seçilen n (oran) | dışarıda olay / n (oran) |\n|---|---|---|---|---|---|")
    rules = [("ln_f3", "<", math.log(1.5), "f3 < 1.5"), ("ln_f3", "<", math.log(2.0), "f3 < 2"), ("ln_f3", "<", math.log(3.0), "f3 < 3"),
             ("f2", ">", 30.0, "halka açıklık > 30"), ("f2", ">", 25.0, "halka açıklık > 25"), ("f1r", ">", np.log(2.0e9), "reel büyüklük > 2 mlr (2025 TL)"),
             ("f1r", ">", np.log(4.0e9), "reel büyüklük > 4 mlr (2025 TL)"), ("ps_planned", "==", 0.0, "fiyat istikrarı yok"), ("sh_lock", "<", 365, "ortak satmama < 365"),
             ("same_wk", ">=", 3, "aynı hafta ≥ 3 arz"), ("add_sale", "==", 1.0, "ek satış kullanıldı"), ("on_ex", "==", 1.0, "borsada satış"), ("f6", "<", 0.0, "XU100 20 seans negatif"), ("ln_lot", "<", math.log(100), "kişi başı lot < 100")]
    for k, lab in TARGETS:
        if k == "y2":
            continue
        for f, op, thr, rl in rules:
            for coh, cname in (("ALL", "H99+açık"), ("H99", "H99"), ("OOT_OPEN", "açık")):
                s = [r for r in rows if r.get(f) is not None and (coh == "ALL" or r["cohort"] == coh)]
                if len(s) < 20:
                    continue
                sel = [r for r in s if (r[f] < thr if op == "<" else r[f] > thr if op == ">" else r[f] >= thr if op == ">=" else r[f] == thr)]
                out = [r for r in s if r not in sel]
                if len(sel) < 5 or len(out) < 5:
                    continue
                rs = sum(r[k] for r in sel) / len(sel); ro = sum(r[k] for r in out) / len(out)
                log_variant("rule", k, f, "threshold", f"{op}{thr:.3g}", cname, len(s), "rate_diff", rs - ro)
                print(f"| {k} | {rl} | {cname} | {len(s)} | {sum(r[k] for r in sel)} / {len(sel)} ({rs:.2f}) | {sum(r[k] for r in out)} / {len(out)} ({ro:.2f}) |")


def sealed_counts():
    """Kasa hakkında yalnız sayımlar: yıl, rejim, satış yöntemi (kohort dosyası) ve alan başına dolu sayısı (coverage.csv'ler)."""
    out = dict(year=Counter(), alloc=Counter(), sale=Counter(), market=Counter(), f7=Counter(), f6=Counter())
    vault = {}
    for c in read_csv(ROOT / "registry/oot/cohort_pre_h99.csv"):
        if c["status"] != "MEMBER":
            continue
        vault[c["ticker"]] = c["vault"]
        if c["vault"] == "SEALED":
            out["year"][c["year"]] += 1; out["sale"][c["sale_method"]] += 1; out["market"][c["market"]] += 1
            tags = dict(p.split("=", 1) for p in c["regime_tags"].split("|") if "=" in p)
            out["alloc"][tags.get("ALLOC_REGIME", "?")] += 1
    for r in read_csv(ROOT / "docs/faz7/prospectus/coverage.csv"):
        if vault.get(r["ticker"]) == "SEALED":
            for f in ("distribution_method", "price_stability_planned", "price_stability_days", "issuer_lockup_days", "shareholder_lockup_days", "sector", "participation_index_eligible"):
                if r[f] in ("VERIFIED", "CORRECTED", "FILLED"):
                    out["f7"][f] += 1
    for r in read_csv(ROOT / "docs/faz6/dogrulama/coverage.csv"):
        if vault.get(r["ticker"]) == "SEALED" and r["status"] not in ("MISSING", "UNVERIFIABLE") and r["value"] not in ("", None):
            out["f6"][f"{r['kind']}:{r['field']}"] += 1
    assert sum(out["year"].values()) == 64
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    sc = sealed_counts()
    if mode == "--kasa":
        print("# Kasa sayımları (yalnız sayı; kod yok)")
        for k in ("year", "alloc", "sale", "market"):
            print(k, dict(sorted(sc[k].items())))
        print("Faz 7 alanı dolu (kasa, 64 üye):", dict(sorted(sc["f7"].items())))
        print("Faz 6 alanı dolu (kasa, 64 üye):", dict(sorted(sc["f6"].items())))
        return
    rows = load_rows(); add_winsor(rows); load_same_week(rows); load_market20(rows); load_comparators(rows)
    if mode == "--csv":
        # rapor koşusuyla aynı varyant listesi: bölümleri sessiz koş
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            section_counts(rows, sc); section_coverage(rows); section_univariate(rows); section_comparators(rows); section_multivariate(rows); section_focus(rows); section_crosstabs(rows); section_rules(rows)
        w = csv.DictWriter(sys.stdout, fieldnames=list(VARIANTS[0].keys()), lineterminator="\n")
        w.writeheader()
        for v in VARIANTS:
            w.writerow(v)
        return
    print("# (C) keşif çıktısı — BORSAI_FAZ7_FABLE_C_SPEC_20260927 [KEŞİF; H99 + açık küme; doğrulanmadı]\n")
    print(f"Satır: {len(rows)} (H99 {sum(1 for r in rows if r['cohort']=='H99')}, açık {sum(1 for r in rows if r['cohort']!='H99')}). Kasa dosyası açılmadı.\n")
    section_counts(rows, sc); section_coverage(rows); section_univariate(rows); section_comparators(rows); section_multivariate(rows); section_focus(rows); section_crosstabs(rows); section_rules(rows)
    print(f"\n## 7. Denenen varyant sayısı: {len(VARIANTS)} (denenenler.csv)\n")
    print("Kasa alan dolu sayıları (64):", dict(sorted(sc["f7"].items())))


if __name__ == "__main__":
    main()

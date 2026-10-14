"""perf_view hücre seçimi (sade.rs perf_view_value) ve hüküm tutarlılığı: geçiyor ⇒ ci95 üst < 0 ve n ≥ 30;
geçemiyor ⇒ ci95 alt > 0 ve n ≥ 30; ayırt edilemiyor ⇒ ci95 0'ı kesiyor. Dosyalar: scores/*.json (salt okunur)."""
import json, sys
R = sys.argv[1] if len(sys.argv) > 1 else "/Users/ahmet/Desktop/BorsAi"
def load(n):
    try: return json.load(open(f"{R}/scores/{n}"))
    except Exception as e: print("NOFILE", n, e); return None
S = load("scores.json"); P = load("scores_post_d1.json"); B = load("scores_break.json"); O = load("scores_oot.json")
PASS, FAIL, UND = "geçiyor", "geçemiyor", "ayırt edilemiyor"
bad = 0
def chk(tag, c):
    global bad
    v = c.get("verdict"); ci = c.get("ci95"); n = c.get("n")
    ok = True
    if v == PASS: ok = ci is not None and ci[1] < 0 and n is not None and n >= 30
    elif v == FAIL: ok = ci is not None and ci[0] > 0 and n is not None and n >= 30
    elif v == UND: ok = ci is not None and ci[0] <= 0 <= ci[1]
    print(f"{'OK ' if ok else 'BAD'} {tag} verdict={v!r} n={n} ci={ci} diff={c.get('diff')}")
    if not ok: bad += 1
def models(d): return d.get("models", []) if isinstance(d, dict) else []
def primary_rows(cells, pc):
    rules = pc.get("rule_ids") or ([pc["rule_id"]] if pc.get("rule_id") else [])
    return [c for c in cells if c.get("output") == pc.get("output") and c.get("metric") == pc.get("metric")
            and str(c.get("horizon_or_k")) == str(pc.get("horizon_or_k")) and c.get("label") == "birincil" and c.get("rule_id") in rules]
print("== scores.json birincil hücreler (perf_view satırları) ==")
if S:
    for mid in ("ceiling_hazard_v0", "v1_5_h99"):
        m = next((x for x in models(S) if x.get("model_id") == mid), None)
        if not m: print("NO MODEL", mid); continue
        pc = m.get("primary_cell") or {}
        print(" primary_cell", mid, {k: pc.get(k) for k in ("output","horizon_or_k","metric","rule_ids","rule_id")})
        for c in primary_rows(m["backtest"]["cells"], pc): chk(f"{mid} {c['output']} {c.get('horizon_or_k')} {c['metric']} {c['rule_id']}", c)
    m = next(x for x in models(S) if x.get("model_id") == "v1_5_h99")
    for c in m["backtest"]["cells"]:
        if c.get("output") == "p_up" and c.get("horizon_or_k") == "D10" and c.get("metric") == "Brier" and c.get("rule_id") == "base_rate":
            chk("PERF_EXTRA v1_5_h99 p_up D10 Brier base_rate label=" + str(c.get("label")), c)
    print("== scores.json: TÜM backtest hücreleri (bütünlük) ==")
    for m in models(S):
        for c in m.get("backtest", {}).get("cells", []): chk(f"ALL {m['model_id']} {c.get('output')} {c.get('horizon_or_k')} {c.get('metric')} {c.get('rule_id')} {c.get('label')}", c)
        live = m.get("live", {})
        print(" live", m["model_id"], {k: live.get(k) for k in ("n_scored","n_live","n_late","n_refused","n_retro","verdict","min_n")}, "cells", len(live.get("cells", [])))
print("== scores_post_d1.json ==")
if P:
    for m in models(P):
        pc = m.get("primary_cell") or {}
        print(" primary_cell", m["model_id"], pc)
        cj = m.get("conditional_j1", {})
        print(" conditional_j1 keys", sorted(cj.keys()), "n_live", cj.get("n_live"), "n_scored", cj.get("n_scored"), "n_retro", cj.get("n_retro"))
        cells = cj.get("cells", [])
        for c in cells: chk(f"PD1 {m['model_id']} {c.get('output')} h={c.get('horizon_or_k')!r} {c.get('metric')} {c.get('rule_id')} label={c.get('label')!r}", c)
        print(" primary_rows (sade.rs eşlemesi) =", len(primary_rows(cells, pc)))
print("== scores_break.json ==")
if B:
    for m in models(B):
        card = m.get("card", {}); bi = card.get("backtest_info", {}); lb = m.get("live_break", {})
        print(" card.promotion", card.get("promotion"), "\n backtest_info keys", sorted(bi.keys()), "label", bi.get("label"), "scale", bi.get("scale"))
        for k in ("F1_product", "F1_zero"):
            b = bi.get(k, {}); print("  ", k, {kk: b.get(kk) for kk in ("diff","ci95","n","n_months","verdict")})
        print(" live_break", {k: lb.get(k) for k in ("n_scored","n_live","n_late","n_refused","n_retro","n_machine")}, "denominator classes", sorted({r.get("class") for r in lb.get("denominator", [])}))
print("== scores_oot.json (PRODUCTION_MODELS blokları) ==")
if O:
    print(" top keys", sorted(O.keys())[:20])
    for blk, mid in (("oot_pre_h99_all","ceiling_hazard_v0"),("oot_pre_h99_all","v1_5_h99"),("post_d1_all","post_d1_hazard_v0")):
        bl = O.get("blocks", O).get(blk) if isinstance(O.get("blocks", O), dict) else None
        if bl is None: print(" NO BLOCK", blk); continue
        ms = bl.get("models", [])
        m = next((x for x in ms if x.get("model_id") == mid), None)
        if not m: print(" NO MODEL", blk, mid, "keys", sorted(bl.keys())[:10]); continue
        pcs = [c for c in m.get("cells", []) if c.get("label") == "birincil" or c.get("primary")]
        print(" ", blk, mid, "n_scored", m.get("n_scored"), "cells", len(m.get("cells", [])), "primary-like", len(pcs))
        for c in pcs: chk(f"OOT {blk} {mid} {c.get('output')} {c.get('horizon_or_k')} {c.get('metric')} {c.get('rule_id')}", c)
print("BAD TOTAL", bad)

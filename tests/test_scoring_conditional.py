"""Koşullu canlı skorlama (SPEC_CEILING_PATH_V0 §7 "Canlı skorlama tanımı"; SPEC_APP_EK2 §5; SPEC_DEVIATIONS G):
t1 küçük-n, t2 elle hesaplanmış RPS_j/Brier, t3 sınıf mirası, t4 eksik ufuk bütün modellerde aynı anda, t5 payda,
t6 birleştirme yasağı, t7 EK2 şeması ve uygulama fixture'ı, t8 ortak metrik fonksiyonları; tavan-yolu ikincilleri
sentetik kayıtla; gerçek veride değişmezler (bugün n < 10: hücre ve hüküm yok)."""
from __future__ import annotations

import inspect
import json
from decimal import Decimal

import pytest

from borsai import outcomes as oc
from borsai import predict_path as pth
from borsai import scoring as sc
from borsai.provenance import ROOT

import faz7_support as fs7

APP_FIXTURE = ROOT / "app" / "tests" / "fixtures" / "scores" / "conditional.json"
HAZARD = "ceiling_hazard_v0"
S_MODEL = [0.9, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1, 0.05]
S_RULES = {"ceiling_hazard_v0@INF": [0.85, 0.7, 0.55, 0.45, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1],
           "pb_ceiling_v0@INF": [0.86, 0.72, 0.56, 0.46, 0.36, 0.31, 0.26, 0.21, 0.16, 0.11],
           "base_km_expanding": [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.15, 0.12, 0.1],
           "base_km_last10": [0.8, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.1, 0.1, 0.1]}
V15_INPUTS = {"ipo_price_tl": "25.52", "shares_offered": "87500000", "post_ipo_share_capital": "312500000",
              "capital_increase_shares": "62500000", "total_demand_multiple": "2.84"}


# ---------------------------------------------------------------- sentetik sonuç ve payda birimleri

def realized(ticker, L, *, n_in=10, d1="2027-01-15", closes=None, ipo_price="10.00", status_at=None, na_at=()):
    """`data/outcomes/<T>.csv` biçiminde 10 satır: D_1..D_L tavan (1), sonrası 0; n_in'den sonrası PENDING;
    status_at = {h: durum}; na_at: NA tavan etiketli seanslar."""
    rows = []
    for h in range(1, 11):
        close = closes[h - 1] if closes else "10.00"
        st = (status_at or {}).get(h, oc.STATUS_OK if h <= n_in else oc.STATUS_PENDING)
        filled = st in (oc.STATUS_OK, oc.STATUS_NA_LIMIT)
        label = "" if not filled else (oc.NA if h in na_at else ("1" if h <= L else "0"))
        R = Decimal(close) / Decimal(ipo_price) - 1
        rows.append({"h": str(h), "session_date": f"{d1[:8]}{int(d1[8:]) + h:02d}" if filled else "",
                     "close_raw": close if filled else "", "upper_limit_raw": "", "reference_raw": "", "trade_count_raw": "",
                     "halt_flag": "0", "half_day": "0", "shifted_by_suspension": "0", "ceiling_close": label,
                     "R_h": str(R) if filled and h in oc.TARGET_H else "", "Y_h": str(int(R > 0)) if filled and h in oc.TARGET_H else "",
                     "ipo_price": ipo_price, "thb_sha256": "", "thm_sha256": "",
                     "status": oc.STATUS_NA_LIMIT if h in na_at and filled else st})
    rows[0]["session_date"] = d1 if rows[0]["session_date"] else ""
    return sc.Realized(ticker, tuple(rows))


def rule_sources(extra=None):
    out = {rid: {"record_id": f"{rid}.json", "output": {"S": S}} for rid, S in S_RULES.items()}
    out[sc.ALWAYS_CEILING_CURVE] = {"record_id": None, "output": {"S": [1.0] * 10}}
    return {**out, **(extra or {})}


def unit(ticker, L, *, klass=sc.CLASS_LATE, S=S_MODEL, ipo_status="FROZEN", retro=False, refused=None, rules=None,
         output=None, **kw):
    r = realized(ticker, L, **kw)
    return {"ticker": ticker, "ipo_status": ipo_status, "realized": r, "retro": retro, "d1": r.d1 or "2027-01-15",
            "class": None if retro else klass, "record_id": None if retro else f"{ticker}.json",
            "output": None if refused or retro else (output or {"S": list(S)}), "refused": refused,
            "rules": {} if retro else (rules if rules is not None else rule_sources())}


def twelve():
    """12 arz, D_1 ayları 2027-01..12 (12 blok): L = 1,1,2,2,1,2,1,2,3,5,7,10 -> j = 1: 12, j = 2: 8, j = 3: 4."""
    Ls = [1, 1, 2, 2, 1, 2, 1, 2, 3, 5, 7, 10]
    return [unit(f"SN{i:02d}", L, klass=sc.CLASS_LIVE if i % 2 else sc.CLASS_LATE, d1=f"2027-{i + 1:02d}-10")
            for i, L in enumerate(Ls)]


def by_j(block, j):
    return next(b for b in block["by_j"] if b["j"] == j)


# ---------------------------------------------------------------- t1 küçük-n

def test_t1_small_n_rules_per_j():
    block = sc.conditional_block(HAZARD, twelve(), {})
    j1, j2, j3 = by_j(block, 1), by_j(block, 2), by_j(block, 3)
    assert (j1["n_scored"], j2["n_scored"], j3["n_scored"]) == (12, 8, 4)
    assert j1["cells"] and all(c["n"] == 12 and c["verdict"] == "yetersiz örnek" and c["scale"] == sc.SCALE_LIVE_CONDITIONAL
                               for c in j1["cells"])
    assert all(c["ci95"] is not None for c in j1["cells"])                      # 12 blok ≥ 6, n ≥ 10: aralık var
    comps = sc.CONDITIONAL_S_COMPARATORS[HAZARD]
    assert [(c["output"], c["horizon_or_k"], c["metric"], c["rule_id"]) for c in j1["cells"]] == (
        [("S_cond", None, "RPS", c) for c in comps] + [("S_cond", 2, "Brier", c) for c in comps]
        + [("S_cond", 10, "Brier", c) for c in comps])
    assert [c["rule_id"] for c in j1["cells"] if c["label"] == "birincil"] == ["base_km_expanding", "base_km_last10"]
    assert j2["cells"] == [] and j3["cells"] == []                              # n < 10: yalnız satır tablosu
    assert len(j3["rows"]) == 4 and all(r["rps_cond"] is not None for r in j3["rows"])
    # j = 9: "yarın" ve "sonuna kadar" aynı hücre (k = 10)
    assert [s for s in sc.conditional_cell_specs(HAZARD, 9) if s[2] == "Brier"] == [("S_cond", 10, "Brier", c) for c in comps]


def test_t1b_n_between_10_and_30_never_passes_and_row_losses_are_paired():
    block = sc.conditional_block(HAZARD, twelve(), {})
    j1 = by_j(block, 1)
    for c in j1["cells"]:
        assert c["verdict"] not in ("geçiyor", "geçemiyor", "ayırt edilemiyor")
        key = "rps_cond" if c["metric"] == "RPS" else ("brier_10" if c["horizon_or_k"] == 10 else "brier_next")
        m = [r[key] for r in j1["rows"]]
        q = [r["rules"][c["rule_id"]][key] for r in j1["rows"]]
        assert c["model_value"] == sum(m) / len(m) and c["rule_value"] == sum(q) / len(q)


# ---------------------------------------------------------------- t2 elle hesaplanmış değerler

S_DYADIC = [1.0, 0.5, 0.5, 0.25, 0.25, 0.125, 0.125, 0.0625, 0.0625, 0.03125]
# (L, j) -> (RPS_j, Brier k = j + 1, Brier k = 10); terimler (S_k/S_j − 1[L ≥ k])², k = j+1..10, elle yazıldı.
HAND = {
    # j = 1 (S_1 = 1): S_k/S_1 = .5 .5 .25 .25 .125 .125 .0625 .0625 .03125
    (4, 1): ((0.25 + 0.25 + 0.5625 + 0.0625 + 0.015625 + 0.015625 + 0.00390625 + 0.00390625 + 0.0009765625) / 9, 0.25, 0.0009765625),
    (2, 1): ((0.25 + 0.25 + 0.0625 + 0.0625 + 0.015625 + 0.015625 + 0.00390625 + 0.00390625 + 0.0009765625) / 9, 0.25, 0.0009765625),
    (7, 1): ((0.25 + 0.25 + 0.5625 + 0.5625 + 0.765625 + 0.765625 + 0.00390625 + 0.00390625 + 0.0009765625) / 9, 0.25,
             0.0009765625),
    # j = 2 (S_2 = .5): S_k/S_2 = 1 .5 .5 .25 .25 .125 .125 .0625
    (4, 2): ((0.0 + 0.25 + 0.25 + 0.0625 + 0.0625 + 0.015625 + 0.015625 + 0.00390625) / 8, 0.0, 0.00390625),
    (2, 2): ((1.0 + 0.25 + 0.25 + 0.0625 + 0.0625 + 0.015625 + 0.015625 + 0.00390625) / 8, 1.0, 0.00390625),
    (7, 2): ((0.0 + 0.25 + 0.25 + 0.5625 + 0.5625 + 0.015625 + 0.015625 + 0.00390625) / 8, 0.0, 0.00390625),
}


def test_t2_hand_computed_conditional_rps_and_brier():
    units = [unit(t, L, S=S_DYADIC) for t, L in (("HA", 4), ("HB", 2), ("HC", 7))]
    block = sc.conditional_block(HAZARD, units, {})
    for (L, j), (rps, b_next, b_10) in HAND.items():
        row = next(r for r in by_j(block, j)["rows"] if r["L"] == L)
        assert row["status"] == sc.ROW_SCORED
        assert (row["rps_cond"], row["brier_next"], row["brier_10"]) == (rps, b_next, b_10), (L, j)
    assert by_j(block, 2)["rows"][0]["S_cond"] == {"3": 1.0, "4": 0.5, "5": 0.5, "6": 0.25, "7": 0.25, "8": 0.125,
                                                   "9": 0.125, "10": 0.0625}
    # her-zaman-tavan (S_k/S_j ≡ 1), j = 2, L = 4: k = 3, 4 isabet, k = 5..10 altı ıska -> 6/8
    a = next(r for r in by_j(block, 2)["rows"] if r["L"] == 4)["rules"][sc.ALWAYS_CEILING_CURVE]
    assert (a["rps_cond"], a["brier_next"], a["brier_10"]) == (0.75, 0.0, 1.0)
    # §9-7: S ≡ 1[L ≥ k] -> 0
    perfect = sc.conditional_block(HAZARD, [unit("HP", 4, S=[1.0] * 4 + [0.0] * 6)], {})
    assert by_j(perfect, 2)["rows"][0]["rps_cond"] == 0.0


# ---------------------------------------------------------------- t3 sınıf mirası

def test_t3_class_is_inherited_per_j():
    units = [unit("CL", 5, klass=sc.CLASS_LIVE), unit("CT", 5, klass=sc.CLASS_LATE)]
    block = sc.conditional_block(HAZARD, units, {})
    for j in range(1, 6):
        b = by_j(block, j)
        assert {r["ticker"]: r["class"] for r in b["rows"]} == {"CL": sc.CLASS_LIVE, "CT": sc.CLASS_LATE}
        assert (b["n_live"], b["n_late"], b["n_scored"]) == (1, 1, 2)
        assert {r["record_id"] for r in b["rows"]} == {"CL.json", "CT.json"}
    # RETRO çift satır olmaz, bilgi sayımıdır; kaydı olmayan prospektif model ayrı sayılır
    retro = sc.conditional_block(HAZARD, [unit("RT", 5, retro=True), {**unit("NR", 5), "class": None, "record_id": None}], {})
    assert [(b["n_retro"], b["n_no_record"], b["rows"]) for b in retro["by_j"][:5]] == [(1, 1, [])] * 5
    with pytest.raises(sc.ScoringError):
        sc.conditional_block(HAZARD, [unit("BAD", 3, klass=sc.CLASS_RETRO)], {})


# ---------------------------------------------------------------- t4 eksik ufuk bütün modellerde aynı anda

def test_t4_missing_horizon_drops_pair_for_all_models_at_once():
    pend = unit("PN", 3, n_in=7)                                    # D8 bekleniyor, L ≥ 3 biliniyor
    tu = unit("TU", 6, status_at={10: oc.STATUS_TARGET_UNAVAILABLE})
    na = unit("NA", 9, na_at=(5,))                                  # D5 NA: L ≥ 4 biliniyor, L belirsiz
    ok = unit("OK", 3)
    models = [HAZARD, "ceiling_hazard_v0@INF", "base_km_expanding", "base_km_last10", "pb_ceiling_v0"]
    blocks = {m: sc.conditional_block(m, [pend, tu, na, ok], {}) for m in models}
    for j in range(1, 10):
        states = {m: {r["ticker"]: (r["status"], r["target_status"], r["target_reason"]) for r in by_j(b, j)["rows"]}
                  for m, b in blocks.items()}
        assert len({json.dumps(s, sort_keys=True) for s in states.values()}) == 1, j
    s = {r["ticker"]: r for r in by_j(blocks[HAZARD], 3)["rows"]}
    assert s["PN"]["status"] == sc.ROW_PENDING and s["PN"]["rps_cond"] is None and s["PN"]["S_cond"] is not None
    assert s["PN"]["L"] is None and s["PN"]["L_at_least"] == 3
    assert s["TU"]["status"] == sc.ROW_TARGET_UNAVAILABLE and s["TU"]["target_reason"] == "SESSION_NOT_FORMED"
    assert s["NA"]["status"] == sc.ROW_TARGET_UNAVAILABLE and s["NA"]["target_reason"] == "NA_LIMIT"
    assert s["OK"]["status"] == sc.ROW_SCORED
    b3 = by_j(blocks[HAZARD], 3)
    assert (b3["n_scored"], b3["n_pending"], b3["n_target_unavailable"]) == (1, 1, 2)
    # D5 NA: j ≥ 5 için L ≥ j belirlenemez (PN'de D4 = 0, OK'de D4 = 0: L < 5 kesin)
    assert "NA" not in {r["ticker"] for r in by_j(blocks[HAZARD], 5)["rows"]} and by_j(blocks[HAZARD], 5)["n_undetermined"] == 1
    # ret model düzeyidir: payda aynı, satır REFUSED, hedef durumu yine veriden
    ref = sc.conditional_block(HAZARD, [unit("RF", 4, refused={"code": "F3_MISSING", "field": "f3", "reason": "x"})], {})
    r = by_j(ref, 2)["rows"][0]
    assert (r["status"], r["target_status"], by_j(ref, 2)["n_refused"], by_j(ref, 2)["n_scored"]) == \
        (sc.ROW_REFUSED, sc.ROW_SCORED, 1, 0)


# ---------------------------------------------------------------- t5 payda

def test_t5_arz_with_L_below_j_is_not_in_the_denominator():
    units = [unit("L0", 0), unit("L2", 2), unit("L5", 5), unit("SK", 0, ipo_status="SKIPPED"),
             unit("SK4", 4, ipo_status="SKIPPED"), {**unit("NOOUT", 0), "realized": None}]
    block = sc.conditional_block(HAZARD, units, {})
    for j in range(1, 10):
        b = by_j(block, j)
        tickers = {r["ticker"] for r in b["rows"]}
        assert "L0" not in tickers
        assert ("L2" in tickers) == (j <= 2) and ("L5" in tickers) == (j <= 5)
        assert b["n_skipped"] == (1 if j <= 4 else 0)                  # L < j kesinleşmemiş atlanan arz (G7)
        assert b["n_undetermined"] == 1                                 # sonucu olmayan FROZEN arz
        assert len(b["rows"]) == b["n_scored"] + b["n_refused"] + b["n_target_unavailable"] + b["n_pending"] + b["n_undefined"]
    assert sc.conditional_membership(realized("X", 3), 3) == sc.MEMBER
    assert sc.conditional_membership(realized("X", 2), 3) == sc.NOT_MEMBER
    assert sc.conditional_membership(realized("X", 5, n_in=2), 3) == sc.UNDETERMINED
    assert sc.conditional_membership(realized("X", 1, na_at=(1,)), 3) == sc.NOT_MEMBER   # D2 = 0 -> L < 3 (D1 NA olsa da)


def test_t5b_zero_S_j_is_undefined_not_scored():
    units = [unit("Z1", 4, S=[0.9, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])]
    block = sc.conditional_block(HAZARD, units, {})
    assert by_j(block, 2)["n_scored"] == 1
    b3 = by_j(block, 3)
    assert b3["rows"][0]["status"] == sc.ROW_UNDEFINED and (b3["n_undefined"], b3["n_scored"]) == (1, 0)
    # karşılaştırılanın S_j'si 0: yalnız o çift hücreden düşer
    rules = rule_sources({"base_km_last10": {"record_id": "k.json", "output": {"S": [0.8, 0.5] + [0.0] * 8}}})
    row = by_j(sc.conditional_block(HAZARD, [unit("Z2", 4, rules=rules)], {}), 3)["rows"][0]
    assert row["rules"]["base_km_last10"] == {"record_id": "k.json", "undefined": "S_3 = 0"}
    assert sc._cond_losses(row, "S_cond", None, "RPS", "base_km_last10") is None


# ---------------------------------------------------------------- t6 birleştirme yasağı

def test_t6_conditional_never_merges_with_unconditional_or_other_j():
    rows = by_j(sc.conditional_block(HAZARD, twelve(), {}), 1)["rows"]
    cond1 = sc.conditional_obs(1, rows, "S_cond", None, "RPS", "base_km_last10")
    assert len(cond1) == 12 and {o.scale for o in cond1} == {sc.SCALE_LIVE_CONDITIONAL} and {o.j for o in cond1} == {1}
    live = [sc.PairedObs(sc.SCALE_LIVE, f"U{i}", "2027-01", 0.1, 0.2, sc.CLASS_LATE) for i in range(12)]
    with pytest.raises(sc.ScaleMixError):
        sc.paired_metric(cond1 + live)
    rows2 = by_j(sc.conditional_block(HAZARD, twelve(), {}), 2)["rows"]
    cond2 = sc.conditional_obs(2, rows2, "S_cond", None, "RPS", "base_km_last10")
    with pytest.raises(sc.ScaleMixError, match="farklı j"):
        sc.paired_metric(cond1 + cond2)
    backtest = [sc.PairedObs(sc.SCALE_BACKTEST, "B", "2027-01", 0.1, 0.2)]
    with pytest.raises(sc.ScaleMixError):
        sc.paired_metric(cond1 + backtest)
    for other in (sc.SCALE_LIVE, sc.SCALE_BACKTEST, sc.SCALE_LIVE_CONDITIONAL):
        with pytest.raises(sc.ScaleMixError):
            sc.merge_scales({"scale": sc.SCALE_LIVE_CONDITIONAL}, {"scale": other})
    assert sc.paired_metric(cond1)["scale"] == sc.SCALE_LIVE_CONDITIONAL


# ---------------------------------------------------------------- t7 EK2 §5 şeması ve uygulama fixture'ı

def _fixture_block():
    doc = json.loads(APP_FIXTURE.read_text(encoding="utf-8"))
    return next(m["conditional"] for m in doc["models"] if "conditional" in m)


def check_ek2(block, fx):
    assert (block["schema_version"], block["title"], block["scale"]) == (fx["schema_version"], fx["title"], fx["scale"])
    assert block["schema_version"] == "borsai.scores_conditional/1" and set(fx) <= set(block)
    assert [b["j"] for b in block["by_j"]] == list(range(1, 10))
    by_keys, row_keys = set(fx["by_j"][0]), set(fx["by_j"][0]["rows"][0])
    cell_keys = set(next(c for b in fx["by_j"] for c in b["cells"]))
    for b in block["by_j"]:
        assert by_keys <= set(b)
        assert b["n_live"] + b["n_late"] == b["n_scored"]                   # EK2 §5 / §2.3 bütünlük
        if b["n_scored"] < sc.MIN_N_METRIC:
            assert b["cells"] == []
        for r in b["rows"]:
            assert row_keys <= set(r)
            if r["S_cond"] is not None:
                assert list(r["S_cond"]) == [str(k) for k in range(b["j"] + 1, 11)]
        for c in b["cells"]:
            assert cell_keys <= set(c) and c["scale"] == sc.SCALE_LIVE_CONDITIONAL
            assert c["verdict"] in sc.VERDICTS


def test_t7_block_matches_ek2_schema_and_app_fixture_field_names():
    fx = _fixture_block()
    block = sc.conditional_block(HAZARD, twelve(), {})
    check_ek2(block, fx)
    assert by_j(block, 1)["cells"], "fixture'daki hücre alanları da sınanmalı"
    json.dumps(block, allow_nan=False)                                        # scores.json'a yazılabilir


# ---------------------------------------------------------------- t8 ortak fonksiyonlar

def test_t8_metrics_are_the_shared_predict_path_functions(monkeypatch):
    src = inspect.getsource(sc)
    for name in ("def conditional_rps", "def conditional_brier", "def conditional_weights", "DAYS - j", "(10 - j)"):
        assert name not in src, name
    calls = {"rps": 0, "brier": 0, "weights": 0}
    real_rps, real_brier, real_w = pth.conditional_rps, pth.conditional_brier, pth.conditional_weights

    def rps(S, j, L):
        calls["rps"] += 1
        return real_rps(S, j, L) + 1000.0

    def brier(S, j, L, k):
        calls["brier"] += 1
        return real_brier(S, j, L, k) + 2000.0

    def weights(S, j):
        calls["weights"] += 1
        return real_w(S, j)

    monkeypatch.setattr(pth, "conditional_rps", rps)
    monkeypatch.setattr(pth, "conditional_brier", brier)
    monkeypatch.setattr(pth, "conditional_weights", weights)
    row = by_j(sc.conditional_block(HAZARD, [unit("T8", 4, S=S_DYADIC)], {}), 2)["rows"][0]
    assert row["rps_cond"] == HAND[(4, 2)][0] + 1000.0 and row["brier_10"] == HAND[(4, 2)][2] + 2000.0
    assert calls["rps"] and calls["brier"] and calls["weights"]


# ---------------------------------------------------------------- tavan-yolu ikincilleri (sentetik kayıt)

@pytest.fixture(scope="module")
def path_setup():
    params = {m: json.loads((ROOT / "models" / f"{m}.json").read_text(encoding="utf-8"))
              for m in (sc.CEILING_PATH_MAIN, sc.CEILING_PATH_ZERO)}
    main = pth.predict(params[sc.CEILING_PATH_MAIN], V15_INPUTS)
    zero = pth.predict(params[sc.CEILING_PATH_ZERO], V15_INPUTS)
    assert main["refused"] is None and zero["refused"] is None
    return params, main, zero


def path_unit(i, L, main, zero, *, mismatch=False):
    C = main["limit_path"]["C"]
    closes = [C[h - 1] if h <= L else str((Decimal(C[L - 1] if L else "25.52") * Decimal("0.93")).quantize(Decimal("0.01")))
              for h in range(1, 11)]
    if mismatch:
        closes[0] = str(Decimal(C[0]) - Decimal("0.02"))
    rules = rule_sources({sc.CEILING_PATH_ZERO: {"record_id": "z.json", "output": zero},
                          "base_train_median": {"record_id": "m.json", "output": {f"D{h}": {"return": 0.2} for h in (1, 3, 5, 10)}},
                          "base_rate": {"record_id": "r.json", "output": {f"D{h}": {"p_up": 0.9} for h in (1, 3, 5, 10)}}})
    return unit(f"CP{i:02d}", L, output=main, rules=rules, closes=closes, ipo_price="25.52", d1=f"2027-{i % 12 + 1:02d}-10")


def test_path_secondaries_only_for_h_above_j_with_shared_conditional(path_setup):
    params, main, zero = path_setup
    Ls = [1, 2, 3, 4, 5, 6, 7, 1, 2, 3, 4, 10]
    units = [path_unit(i, L, main, zero) for i, L in enumerate(Ls)]
    units[0] = path_unit(0, 1, main, zero, mismatch=True)
    block = sc.conditional_block(sc.CEILING_PATH_MAIN, units, params)
    j1 = by_j(block, 1)
    assert j1["n_scored"] == 12
    for r in j1["rows"]:
        u = next(x for x in units if x["ticker"] == r["ticker"])
        closes = [u["realized"].row(1)["close_raw"]]
        want = pth.conditional(params[sc.CEILING_PATH_MAIN], main, 1, closes)
        assert set(r["path"]) == {"limit_path_mismatch", "D3", "D5", "D10"}
        assert r["path"]["limit_path_mismatch"] == (1 if r["ticker"] == "CP00" else 0)
        for h in (3, 5, 10):
            assert r["path"][f"D{h}"]["return"] == want[f"D{h}"]["return"] and r["path"][f"D{h}"]["p_up"] == want[f"D{h}"]["p_up"]
            R = Decimal(u["realized"].row(h)["R_h"])
            assert r["path"][f"D{h}"]["abs_error"] == abs(want[f"D{h}"]["return"] - float(R))
        z = pth.conditional(params[sc.CEILING_PATH_ZERO], zero, 1, closes)
        assert r["rules"][sc.CEILING_PATH_ZERO]["path"]["D5"]["return"] == z["D5"]["return"]
        assert r["rules"]["base_train_median"]["unconditional"] is True
    got = {(c["output"], c["horizon_or_k"], c["metric"], c["rule_id"]): c for c in j1["cells"]}
    for h in ("D3", "D5", "D10"):
        assert got[("return_cond", h, "MAE", sc.CEILING_PATH_ZERO)]["label"] == "keşif"
        ref = got[("return_cond", h, "MAE", "base_train_median")]
        assert ref["label"] == "koşulsuz referans" and ref["reference_only"] is True and ref["verdict"] is None
        assert got[("p_up_cond", h, "Brier", "base_rate")]["verdict"] is None
    assert ("S_cond", None, "RPS", "ceiling_hazard_v0@INF") in got
    # h ≤ j için ikincil yok (j = 4: yalnız D5, D10; j = 5..9: yalnız D10)
    for j in range(1, 10):
        hs = {s[1] for s in sc.conditional_cell_specs(sc.CEILING_PATH_MAIN, j) if s[0] != "S_cond"}
        assert hs == {f"D{h}" for h in (3, 5, 10) if h > j}, j
        for r in by_j(block, j)["rows"]:
            assert set(r["path"]) - {"limit_path_mismatch"} == {f"D{h}" for h in (3, 5, 10) if h > j}
    # sıfır model kendisiyle karşılaştırılmaz; S kaynağı zaten sıfır model
    assert sc.CONDITIONAL_PATH_COMPARATORS[sc.CEILING_PATH_ZERO] == ()
    assert "ceiling_hazard_v0@INF" not in sc.CONDITIONAL_S_COMPARATORS[sc.CEILING_PATH_ZERO]
    check_ek2(block, _fixture_block())


def test_path_uses_shared_conditional_function(path_setup, monkeypatch):
    params, main, zero = path_setup
    seen = []
    real = pth.conditional

    def spy(p, out, j, closes):
        seen.append((p["model_id"], j))
        return real(p, out, j, closes)

    monkeypatch.setattr(pth, "conditional", spy)
    sc.conditional_block(sc.CEILING_PATH_MAIN, [path_unit(0, 4, main, zero)], params)
    assert (sc.CEILING_PATH_MAIN, 1) in seen and (sc.CEILING_PATH_ZERO, 1) in seen


# ---------------------------------------------------------------- gerçek veri: değişmezler (bugün n < 10)

@pytest.fixture(scope="module")
def scores():
    return sc.build_scores()


@pytest.mark.requires_git_history
def test_real_blocks_only_for_s_kinds_and_ek2_integrity(scores):
    fx = _fixture_block()
    for m in scores["models"]:
        assert ("conditional" in m) == (m["kind"] in sc.CONDITIONAL_KINDS), m["model_id"]
        if "conditional" not in m:
            continue
        check_ek2(m["conditional"], fx)
        for b in m["conditional"]["by_j"]:
            assert len(b["rows"]) == b["n_scored"] + b["n_refused"] + b["n_target_unavailable"] + b["n_pending"] + b["n_undefined"]
            for r in b["rows"]:
                assert r["class"] in sc.PROSPECTIVE_CLASSES
                assert (r["L"] if r["L"] is not None else r["L_at_least"]) >= b["j"]          # t5: L < j paydada yok
                live = next(x for x in m["live"]["rows"] if x["ticker"] == r["ticker"])
                assert (r["class"], r["record_id"]) == (live["class"], live["record_id"])    # t3: miras
    assert sum(m["kind"] in sc.CONDITIONAL_KINDS for m in scores["models"]) == 9 + len(fs7.frozen_faz7_ids())   # v1: hazard


@pytest.mark.requires_raw_sources
def test_real_pair_status_is_the_same_for_every_model(scores):
    states: dict[tuple[str, int], set[str]] = {}
    for m in scores["models"]:
        for b in (m.get("conditional") or {}).get("by_j", []):
            for r in b["rows"]:
                states.setdefault((r["ticker"], b["j"]), set()).add(r["target_status"])
    assert states and all(len(v) == 1 for v in states.values())


@pytest.mark.requires_git_history
def test_doc_is_the_same_from_memory_and_from_written_file(scores):
    """`main()` belgeyi bellekteki sonuçtan yazar, commit denetimi dosyadan (sıralı anahtar) üretir: ikisi aynı olmalı."""
    from borsai.provenance import pretty_json_bytes

    written = json.loads(pretty_json_bytes(scores))
    assert any(m["conditional"]["comparators"]["unconditional_reference"] for m in written["models"] if "conditional" in m)
    assert sc.render_doc(written) == sc.render_doc(scores)


@pytest.mark.requires_raw_sources
def test_real_no_conditional_cell_or_verdict_below_ten(scores):
    """K2: n < 10 olan her j'de hücre, ortalama ya da hüküm yok; satır tablosu var."""
    n_rows = 0
    for m in scores["models"]:
        for b in (m.get("conditional") or {}).get("by_j", []):
            n_rows += len(b["rows"])
            if b["n_scored"] < sc.MIN_N_METRIC:
                assert b["cells"] == []
    assert n_rows > 0
    doc = sc.render_doc(scores)
    part = doc.partition("## 6. Koşullu tavan skorları")[2]
    assert "n < 10: metrik hesaplanmaz" in part
    for word in ("geçiyor", "geçemiyor", "ayırt edilemiyor", "ortalama", "Brier =", "RPS ="):
        assert word not in part, word

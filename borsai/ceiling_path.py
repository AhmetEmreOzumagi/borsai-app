"""Tavan yolu modelleri: veri, walk-forward backtest, nihai dondurma ve koşullu (keşif) değerlendirme
(SPEC_CEILING_PATH_V0 §3, §7, §8). Tahmin matematiği borsai/predict_path.py'dedir (yalnız stdlib); bu
modül aynı fonksiyonları çağırır, yeni bir hesap yolu yoktur.

- Kapanışlar: SESSIONS dosyasının `close` sütunu Decimal olarak (sha256'sı data/data_version.json'la
  denetlenir); yalnız hücre kurulumu ve bilgi amaçlı gerçekleşen değerler için okunur.
- Backtest (§8): S_1..S_10, kaynak tavan ledger'ından (`tests/reference/macos_golden_faz1b/`, sha256'sı
  şartnamede sabit) AYNEN okunur; yeniden fit yok. Fold kümesi ve sırası kaynak ledger'ınkidir. Hücreler
  her fold'da 99 arzın hepsinden, yalnız seans tarihi < kesim (kaynak ledger'ın `prediction_date`'i: ana ve
  sıfır model T, PB varyantı B(k)) olan gözlemlerle kurulur.
- Nihai dondurma: hücreler 99 arzın tamamından (sonuç seansları ≤ 2026-08-19); seri modeli JSON'u birebir
  gömülür (`survival_model_sha256` = INDEX'teki sha256).
- Koşullu keşif (§7): Faz 1B tavan ledger'larından j = 1..9 için koşullu RPS ve Brier; yeni model değildir,
  günlüğe `kind: conditional_eval` satırıyla düşer.
"""
from __future__ import annotations

import csv
import io
import json
import statistics
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from . import metrics as mx
from . import predict_path as pth
from . import survival as sv
from .data import SESSIONS_PATH, VERSION_PATH, DataIntegrityError, Dataset, IPORow, load_pb
from .horizons import HORIZONS
from .provenance import ROOT, canonical_json, code_version, identity_hash, now_istanbul, sha256_bytes, sha256_file

STATUS_OK = "OK"
STATUS_SURVIVAL_NOT_AVAILABLE = "SURVIVAL_NOT_AVAILABLE"
OUTCOME_CUTOFF = "2026-08-19"
SOURCE_OK = "FIT_OK"
CONDITIONAL_JS = tuple(range(1, sv.DAYS))


class CeilingPathError(RuntimeError):
    pass


# ============================================================ veri

@dataclass(frozen=True)
class SessionPrice:
    date: str
    close: Decimal
    reference: Decimal
    upper: Decimal
    lower: Decimal


def load_sessions() -> dict[str, tuple[SessionPrice, ...]]:
    """SESSIONS (H99, 990 seans): ticker -> D1..D10. sha256 data_version.json'daki kaynak kaydıyla aynı olmalı."""
    version = json.loads(VERSION_PATH.read_text(encoding="utf-8"))
    rel = SESSIONS_PATH.relative_to(ROOT).as_posix()
    pinned = {s["path"]: s["sha256"] for s in version["sources"]}
    if pinned.get(rel) != sha256_file(SESSIONS_PATH):
        raise DataIntegrityError(f"{rel}: sha256 data_version.json ile aynı değil")
    by: dict[str, dict[int, SessionPrice]] = {}
    with SESSIONS_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["row_status"] != "OFFICIAL_VERIFIED" or r["conflict_status"] != "NO_CONFLICT":
                raise DataIntegrityError(f"{r['ticker']}/{r['session_number']}: seans resmi/çelişkisiz değil")
            by.setdefault(r["ticker"], {})[int(r["session_number"])] = SessionPrice(
                r["target_session_date"], Decimal(r["close"]), Decimal(r["reference_price"]), Decimal(r["upper_limit"]),
                Decimal(r["lower_limit"]))
    out = {}
    for tk, slot in by.items():
        if set(slot) != set(range(1, sv.DAYS + 1)):
            raise DataIntegrityError(f"{tk}: 10 seans yok")
        out[tk] = tuple(slot[k] for k in range(1, sv.DAYS + 1))
    return out


def path_units(rows: Sequence[IPORow], sessions: Optional[Mapping[str, Sequence[SessionPrice]]] = None) -> list[pth.PathUnit]:
    """Hücre birimleri, veri sırasıyla (first_trading_date, ticker). Baz fiyat resmi kesin arz fiyatı (ipo_price_tl)."""
    sessions = sessions if sessions is not None else load_sessions()
    units = []
    for r in rows:
        s = sessions[r.ticker]
        if tuple(x.date for x in s) != tuple(r.session_dates):
            raise DataIntegrityError(f"{r.ticker}: SESSIONS tarihleri veriyle aynı değil")
        units.append(pth.PathUnit(r.ticker, r.first_trading_date, r.ceiling_streak, Decimal(r.inputs["ipo_price_tl"]),
                                  tuple(x.close for x in s), tuple(r.session_dates)))
    return units


def realized_series(row: IPORow, sessions: Sequence[SessionPrice]) -> dict[str, Any]:
    """Gerçekleşen R_h ve Y_h, h = 1..10 (kapanışlardan; D1/D3/D5/D10 tablo değeriyle denetlenir)."""
    P = Decimal(row.inputs["ipo_price_tl"])
    R = {h: pth.ratio_minus_one(sessions[h - 1].close, P) for h in range(1, sv.DAYS + 1)}
    Y = {h: int(sessions[h - 1].close > P) for h in range(1, sv.DAYS + 1)}
    for hk in HORIZONS:
        h = int(hk[1:])
        if Y[h] != row.targets[hk].Y or abs(R[h] - row.targets[hk].R_float) > 1e-12:
            raise DataIntegrityError(f"{row.ticker}/{hk}: SESSIONS kapanışı tablo hedefiyle tutarsız")
    return {"R": R, "Y": Y}


def price_of(spec: Mapping[str, Any], dataset: Dataset) -> dict[str, Decimal]:
    """Limit yolunun arz fiyatı: ana/sıfır model `ipo_price_tl`, PB varyantı PB girdisi `ipo_price_try`."""
    field = spec["limit_path"]["price_field"]
    if field == "ipo_price_tl":
        return {r.ticker: Decimal(r.inputs["ipo_price_tl"]) for r in dataset.rows}
    pb = load_pb(dataset)
    return {t: Decimal(pb[t].fields["ipo_price_try"]) for t in pb}


# ============================================================ backtest (§8)

def ledger_columns() -> list[str]:
    cols = ["model_id", "fold_id", "ticker", "first_trading_date", "prediction_date", "survival_model_id",
            "survival_ledger_sha256", "survival_fold_status"]
    cols += [f"S_{k}" for k in range(1, sv.DAYS + 1)] + [f"P_L_{l}" for l in range(0, sv.DAYS + 1)]
    cols += ["ipo_price", "snapped_ipo_price", "tick"] + [f"C_{k}" for k in range(1, sv.DAYS + 1)]
    cols += [f"rho_{k}" for k in range(1, sv.DAYS + 1)]
    cols += [f"cells_n_Z_{m}" for m in range(1, pth.M_MAX["Z"] + 1)] + [f"cells_n_B_{m}" for m in range(1, pth.M_MAX["B"] + 1)]
    cols += ["cells_max_session_date", "cells_ipos_sha256", "status"]
    for h in range(1, sv.DAYS + 1):
        cols += [f"D{h}_{x}" for x in ("return", "mean", "p_up", "q10", "q90", "post_break_status", "pooled_cells", "n_atoms")]
    cols += [f"realized_R_{hk}" for hk in HORIZONS] + [f"realized_Y_D{h}" for h in range(1, sv.DAYS + 1)] + ["realized_L"]
    return cols


def read_source_ledger(spec: Mapping[str, Any]) -> tuple[list[dict[str, str]], str]:
    src = spec["survival_ledger"]
    raw = (ROOT / src["path"]).read_bytes()
    sha = sha256_bytes(raw)
    if sha != src["sha256"]:
        raise CeilingPathError(f"{src['path']}: sha256 {sha} != şartname {src['sha256']}")
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))
    if not rows or any(r["model_id"] != spec["survival_model_id"] for r in rows):
        raise CeilingPathError(f"{src['path']}: kaynak ledger {spec['survival_model_id']}'ninki değil")
    return rows, sha


def fold_row(spec: Mapping[str, Any], src: Mapping[str, str], src_sha: str, units: Sequence[pth.PathUnit],
             P: Decimal, row: IPORow, realized: Mapping[str, Any]) -> dict[str, Any]:
    """Bir fold'un ledger satırı (şartname §8 sütunları, bu sırayla)."""
    out: dict[str, Any] = {"model_id": spec["model_id"], "fold_id": src["fold_id"], "ticker": src["ticker"],
                           "first_trading_date": src["first_trading_date"], "prediction_date": src["prediction_date"],
                           "survival_model_id": spec["survival_model_id"], "survival_ledger_sha256": src_sha,
                           "survival_fold_status": src["status"]}
    ok_src = src["status"] == SOURCE_OK
    S = [float(src[f"S_{k}"]) for k in range(1, sv.DAYS + 1)] if ok_src else None
    P_L = sv.p_streak(S) if ok_src else None
    out.update({f"S_{k}": (S[k - 1] if S else None) for k in range(1, sv.DAYS + 1)})
    out.update({f"P_L_{l}": (P_L[l] if P_L else None) for l in range(0, sv.DAYS + 1)})
    lp = pth.limit_path(P)
    out.update({"ipo_price": str(P), "snapped_ipo_price": str(lp["snapped_ipo_price"]), "tick": str(lp["tick"])})
    out.update({f"C_{k}": str(lp["C"][k - 1]) for k in range(1, sv.DAYS + 1)})
    out.update({f"rho_{k}": lp["rho"][k - 1] for k in range(1, sv.DAYS + 1)})
    cells, info = pth.build_cells(units, cutoff=src["prediction_date"])
    out.update({f"cells_n_{g}_{m}": len(cells[(g, m)]) for g in pth.GROUPS for m in range(1, pth.M_MAX[g] + 1)})
    out.update({"cells_max_session_date": info["max_session_date"], "cells_ipos_sha256": identity_hash(info["contributors"])})
    preds = {h: pth.horizon_prediction(S, P_L, lp["scale"], lp["rho"], cells, h) for h in range(1, sv.DAYS + 1)} if ok_src else {}
    if not ok_src:
        status = STATUS_SURVIVAL_NOT_AVAILABLE
    elif all(p["post_break"]["status"] == pth.STATUS_OK for p in preds.values()):
        status = STATUS_OK
    else:
        status = pth.STATUS_POST_BREAK_INSUFFICIENT
    out["status"] = status
    for h in range(1, sv.DAYS + 1):
        p = preds.get(h)
        out.update({
            f"D{h}_return": p and p["return"], f"D{h}_mean": p and p["mean"], f"D{h}_p_up": p and p["p_up"],
            f"D{h}_q10": p and p["q10"], f"D{h}_q90": p and p["q90"],
            f"D{h}_post_break_status": p and p["post_break"]["status"],
            f"D{h}_pooled_cells": None if p is None else canonical_json(p["post_break"]["cells"]),
            f"D{h}_n_atoms": p and p["n_atoms"],
        })
    out.update({f"realized_R_{hk}": row.targets[hk].R for hk in HORIZONS})
    out.update({f"realized_Y_D{h}": realized["Y"][h] for h in range(1, sv.DAYS + 1)})
    out["realized_L"] = row.ceiling_streak
    if list(out) != ledger_columns():
        raise CeilingPathError("ledger sütunları şartnameyle aynı değil")
    return out


def backtest_ledger(spec: Mapping[str, Any], dataset: Dataset) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """(ledger satırları, günlük ek alanları). Fold kümesi ve sırası kaynak ledger'ınki."""
    src_rows, src_sha = read_source_ledger(spec)
    sessions = load_sessions()
    units = path_units(dataset.rows, sessions)
    by = dataset.by_ticker()
    prices = price_of(spec, dataset)
    ledger = []
    for src in src_rows:
        row = by[src["ticker"]]
        if src["first_trading_date"] != row.first_trading_date:
            raise CeilingPathError(f"{src['fold_id']}: ilk işlem günü veriyle aynı değil")
        ledger.append(fold_row(spec, src, src_sha, units, prices[src["ticker"]], row, realized_series(row, sessions[row.ticker])))
    return ledger, {"survival_model_id": spec["survival_model_id"], "survival_ledger": spec["survival_ledger"]["path"],
                    "survival_ledger_sha256": src_sha, "folds_total": len(src_rows)}


def _ok(r: Mapping[str, Any], h: int) -> bool:
    return r["status"] == STATUS_OK and r[f"D{h}_return"] is not None


def path_metrics(ledger: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Günlük metrikleri, ufuk başına (D1/D3/D5/D10): n, MAE, MedAE (getiri); n, Brier ([0.01, 0.99] kırpılı,
    Faz 1A tablolarıyla aynı) ve isabet (p_up > 0.5). Ek: fold durumları."""
    out: dict[str, Any] = {}
    for hk in HORIZONS:
        h = int(hk[1:])
        rows = [r for r in ledger if _ok(r, h)]
        err = [abs(r[f"D{h}_return"] - float(r[f"realized_R_{hk}"])) for r in rows]
        out[hk] = {"folds": len(ledger),
                   "return": {"n": len(rows), "mae": mx.mean_or_none(err), "median_ae": statistics.median(err) if err else None},
                   "p_up": {"n": len(rows),
                            "brier": mx.mean_or_none(mx.brier_term(r[f"D{h}_p_up"], r[f"realized_Y_D{h}"]) for r in rows),
                            "accuracy": mx.mean_or_none(float(int(r[f"D{h}_p_up"] > 0.5) == r[f"realized_Y_D{h}"]) for r in rows)}}
    statuses: dict[str, int] = {}
    for r in ledger:
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
    out["status_counts"] = dict(sorted(statuses.items()))
    return out


# ============================================================ nihai dondurma

def load_survival_model(spec: Mapping[str, Any], models_dir: Path = ROOT / "models") -> tuple[dict[str, Any], str]:
    """Dondurulmuş seri modeli (INDEX kaydı ve şartnamedeki sha256 ile aynı olmalı)."""
    index = json.loads((models_dir / "INDEX.json").read_text(encoding="utf-8"))
    entry = next((e for e in index["models"] if e["model_id"] == spec["survival_model_id"]), None)
    if entry is None:
        raise CeilingPathError(f"{spec['survival_model_id']} INDEX'te yok")
    raw = (models_dir / entry["file"]).read_bytes()
    sha = sha256_bytes(raw)
    if not sha == entry["sha256"] == spec["survival_model_sha256"]:
        raise CeilingPathError(f"{spec['survival_model_id']}: sha256 {sha} INDEX/şartname ile aynı değil")
    return json.loads(raw), sha


def fit_params(spec: Mapping[str, Any], rows: Sequence[IPORow], dataset_version: str) -> dict[str, Any]:
    """Dondurulacak parametre sözlüğü: 99 arzdan hücreler (kesim yok; sonuç seansları ≤ 2026-08-19) + gömülü seri modeli."""
    from .fit import _check_training_rows, _envelope, _survival_training_block, select_training_rows

    selected = select_training_rows(spec, rows)
    _check_training_rows(spec, selected, dataset_version)
    units = path_units(selected)
    cells, info = pth.build_cells(units, cutoff=None)
    if info["max_session_date"] > OUTCOME_CUTOFF:
        raise CeilingPathError(f"hücrede {OUTCOME_CUTOFF} sonrası seans var")
    survival, sha = load_survival_model(spec)
    training = _survival_training_block(spec, selected, dataset_version)
    training["closes_sha256"] = identity_hash(
        [f"{u.ticker}|{u.ipo_price}|{','.join(u.session_dates)}|{','.join(str(c) for c in u.closes)}" for u in units])
    training["sessions_source"] = {"path": SESSIONS_PATH.relative_to(ROOT).as_posix(), "sha256": sha256_file(SESSIONS_PATH)}
    params = _envelope(spec, selected, dataset_version, training)
    params.update({
        "horizons": {k: {"return": {"kind": "mixture_median"}, "p_up": {"kind": "mixture_p_up"}} for k in pth.HORIZON_KEYS},
        "survival_model_id": spec["survival_model_id"],
        "survival_model_sha256": sha,
        "survival_model": survival,
        "survival_training": survival["training"],
        "limit_path": {"margin": pth.MARGIN, "tick_table": pth.tick_table_json(), "upper_rounding": pth.UPPER_ROUNDING,
                       "lower_rounding": pth.LOWER_ROUNDING, "d1_base": pth.D1_BASE,
                       "price_field": spec["limit_path"]["price_field"], "rule_source": spec["limit_path"]["rule_source"]},
        "post_break": {"N_MIN": pth.N_MIN, "groups": list(pth.GROUPS), "cells": pth.cells_to_json(cells),
                       "cutoff_date": OUTCOME_CUTOFF, "max_session_date": info["max_session_date"],
                       "n_ipo": len(units), "ipos_sha256": identity_hash([u.ticker for u in units]),
                       "contributors_sha256": identity_hash(info["contributors"]), "n_obs": info["n_obs"],
                       "cell_n": {g: {str(m): len(cells[(g, m)]) for m in range(1, pth.M_MAX[g] + 1)} for g in pth.GROUPS}},
        "quantile_rule": dict(spec["quantile_rule"]),
        "feature_definitions": survival.get("feature_definitions", {}),
        "feature_ranges": survival.get("feature_ranges", {}),
        "input_policy": dict(spec["input_policy"]),
    })
    return params


def final_predictions(params: Mapping[str, Any], S: Sequence[float], P: Decimal) -> dict[int, dict[str, Any]]:
    """Backtest kodunun nihai-dondurma hesabı (§9-6 paritesi): verilen S ile 99 arzın hücrelerinden karışım.
    Hücreler JSON'dan değil, veriden yeniden kurulur."""
    from .data import load_dataset

    ds = load_dataset()
    cells, _ = pth.build_cells(path_units(ds.rows), cutoff=None)
    lp = pth.limit_path(P)
    P_L = sv.p_streak(S)
    return {h: pth.horizon_prediction(S, P_L, lp["scale"], lp["rho"], cells, h) for h in range(1, sv.DAYS + 1)}


# ============================================================ §7 koşullu keşif (H99, Faz 1B tavan ledger'ları)

CONDITIONAL_RUNS = {
    "ceiling_hazard_v0": ("ceiling_hazard_v0", ("ceiling_hazard_v0@INF", "base_km_expanding", "base_km_last10",
                                                "base_always_ceiling__ceiling")),
    "pb_ceiling_v0": ("pb_ceiling_v0", ("pb_ceiling_v0@INF", "base_km_expanding__pb_ceiling", "base_km_last10__pb_ceiling",
                                        "base_always_ceiling__pb_ceiling")),
}
CONDITIONAL_METRICS = ("rps", "brier_next", "brier_end")


def _curve(r: Mapping[str, str]) -> list[float]:
    return [float(r[f"S_{k}"]) for k in range(1, sv.DAYS + 1)]


def conditional_losses(S: Sequence[float], j: int, L: int) -> Optional[dict[str, float]]:
    """(RPS_j, Brier k = j + 1, Brier k = 10); S_j = 0 ise None (koşul tanımsız)."""
    if S[j - 1] <= 0.0:
        return None
    return {"rps": pth.conditional_rps(S, j, L), "brier_next": pth.conditional_brier(S, j, L, j + 1),
            "brier_end": pth.conditional_brier(S, j, L, sv.DAYS)}


def conditional_eval(runs: Mapping[str, Sequence[Mapping[str, str]]]) -> dict[str, Any]:
    """Model ve kurallar aynı fold'larda (ticker ile eşlenir), j = 1..9 ve L ≥ j olan arzlar; fark = model − kural.
    %95 aralık C7 yöntemi (ilk işlem ayı blokları, 4000, random.Random(20260921)); n < 10 ise aralık yok."""
    out: dict[str, Any] = {}
    for model_id, (key, comps) in CONDITIONAL_RUNS.items():
        rows = [r for r in runs[key] if r["status"] in ("FIT_OK", "RULE_OK")]
        other = {c: {r["ticker"]: r for r in runs[c] if r["status"] in ("FIT_OK", "RULE_OK")} for c in comps}
        per_j: dict[str, Any] = {}
        for j in CONDITIONAL_JS:
            use = [r for r in rows if int(r["realized_L"]) >= j]
            entry: dict[str, Any] = {"n": len(use), "model": {}, "vs": {}}
            own = [conditional_losses(_curve(r), j, int(r["realized_L"])) for r in use]
            valid = [(r, x) for r, x in zip(use, own) if x is not None]
            entry["n_undefined_model"] = len(use) - len(valid)
            for m in CONDITIONAL_METRICS:
                entry["model"][m] = mx.mean_or_none(x[m] for _, x in valid)
            for c in comps:
                pairs = []
                for r, x in valid:
                    o = other[c].get(r["ticker"])
                    y = None if o is None else conditional_losses(_curve(o), j, int(r["realized_L"]))
                    if y is not None:
                        pairs.append((r, x, y))
                cell: dict[str, Any] = {"n": len(pairs)}
                for m in CONDITIONAL_METRICS:
                    d = [x[m] - y[m] for _, x, y in pairs]
                    months = [r["first_trading_date"][:7] for r, _, _ in pairs]
                    if len(d) >= 10:
                        p = mx.paired_difference(d, months)
                        cell[m] = {"rule": mx.mean_or_none(y[m] for _, _, y in pairs), "diff": p["mean"], "ci95": p["ci95"],
                                   "n_months": p["n_months"]}
                    else:
                        cell[m] = {"rule": mx.mean_or_none(y[m] for _, _, y in pairs), "diff": mx.mean_or_none(d),
                                   "ci95": None, "n_months": len(set(months))}
                entry["vs"][c] = cell
            per_j[str(j)] = entry
        out[model_id] = {"run_key": key, "comparators": list(comps), "j": per_j}
    return out


def run_conditional_eval(runs: Mapping[str, Sequence[Mapping[str, str]]], manifest: Mapping[str, Any], *, log_path: Path,
                         context: str, spec_document: Mapping[str, str], data_version_sha256: str) -> dict[str, Any]:
    """§7 backtest tarafı: hesaplar ve günlüğe bir `conditional_eval` satırı ekler (kural 4)."""
    from .backtest import append_log

    started = now_istanbul()
    metrics = conditional_eval(runs)
    evaluated = []
    for model_id, (key, comps) in CONDITIONAL_RUNS.items():
        for k in (key, *comps):
            info = manifest["runs"][k]
            evaluated.append({"run_key": k, "model_id": info["model_id"], "plan_id": info["plan_id"],
                              "ledger_sha256": info["ledger_sha256"]})
    entry = {
        "kind": "conditional_eval",
        "context": context,
        "model_id": None,
        "description": "SPEC_CEILING_PATH_V0 §7: H99 koşullu RPS_j ve Brier (k = j + 1, k = 10), j = 1..9; yeni model değil, keşif",
        "evaluated": evaluated,
        "spec_document": spec_document["path"],
        "spec_document_sha256": sha256_file(ROOT / spec_document["path"]),
        "data_version_sha256": data_version_sha256,
        "metrics": metrics,
        "started_at": started,
        "finished_at": now_istanbul(),
        **code_version(),
    }
    append_log(log_path, entry)
    return entry

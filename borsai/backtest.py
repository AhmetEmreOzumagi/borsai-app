"""Walk-forward backtest (retrospektif terazi) ve deney günlüğü.

Planlar (borsai.specs PLAN_*; bir modelin planı şartnamesindedir, Faz 1A
modellerininki PLAN_V15):
- PLAN_V15 (aşağıda): V1.5 ve basit kurallar; v1_6_h99 ve v1_5_market20_v0 da
  birebir aynı fold'larda (SPEC_V1_6 §7, SPEC_MARKET20_V0 §8).
- PLAN_PB: aynı kural, kesim ilk talep toplama günü B(k) (SPEC_PB_V0 §6).
- PLAN_CEILING: kişi-dönem satırları, kesim T(k), f3 dolu arzlar; skorlanabilirlik
  ≥ 10 arz, ≥ 5 olay, ≥ 5 sağ kalım (SPEC_CEILING_V0 §9).
- PLAN_PB_CEILING: aynısı, kesim B(k), 99 arz (SPEC_PB_V0 §9).
- PLAN_CEILING_PATH / PLAN_PB_CEILING_PATH (Faz 4, SPEC_CEILING_PATH_V0 §8): tavan yolu modelleri; S_k
  kaynak tavan ledger'ından aynen, hücreler fold içinde walk-forward (borsai/ceiling_path.py).
- Faz 7 (SPEC_HAZARD_V1 §5): `ceiling_hazard_v1_clip` / `_real` PLAN_CEILING'de (v0 ile aynı fold'lar); `_pooled` ve `@INF`
  PLAN_CEILING_POOLED'da (test arzları H99'un f3'lü 97'si, eğitim training_table_v2'nin seans tarihi < T olan bütün PP satırları).
  Yakın dönem hücresi (ilk işlem ≥ 2024-01-01): v1 − ceiling_hazard_v0 RPS, v0 değerleri Faz 1B altın ledger'ından (sha pinli,
  yeniden koşulmaz); etiket `near_era_label`. `run_backtest_v1`, `--suite faz7`.
Basit kurallar karşılaştırıldıkları modelin planında, aynı eğitim kümesinden
koşar; her (model, plan) koşusu ayrı ledger ve ayrı günlük satırıdır.

Fold planı legacy H99 V1.5 benchmark'ıyla aynıdır
(legacy/scripts/modeling/run_historical99_frozen_v1_5_benchmark.py:
plan_historical_folds): her ufuk ve her test arzı için eğitim kümesi,
hedef seansı test arzının ilk işlem gününden KESİN önce olan arzlardır
(target_session_date < prediction_date; aynı gün, gelecek ve kendisi dışlanır).
Sıra (first_trading_date, ticker). Eğitim n'i < 10 ise fold skorlanmaz
(INSUFFICIENT_TRAINING_HISTORY). H99'da 351 skorlanabilir fold (89/88/87/87).

Basit kurallar aynı fold'larda, aynı eğitim kümesinden hesaplanır.

CLAUDE.md kural 4: `run_backtest` her koşuda günlüğe bir satır ekler (model_id,
spec sha, veri sha, metrikler, zaman, git commit). Günlük yolu zorunlu
argümandır; günlüksüz koşu yolu yoktur. Resmi koşular experiments/log.jsonl'a
yazar (`python -m borsai.backtest`); test paketi aynı kodu geçici bir günlüğe
yazarak koşar (bkz. experiments/README.md).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from . import fit as fitmod
from . import metrics as mx
from . import preprocess as pp
from . import survival as sv
from .data import Dataset, IPORow, load_dataset, load_pb
from .features import compute_features
from .horizons import HORIZONS, physical_return_bounds
from .provenance import (
    ROOT,
    canonical_json,
    code_version,
    identity_hash,
    now_istanbul,
    sha256_bytes,
    sha256_file,
)
from .rules import direction, rule_p_up, rule_return
from .specs import (
    FALL_HORIZONS,
    FAZ1A_MODEL_IDS,
    MODEL_SPECS,
    PLAN_CEILING,
    PLAN_CEILING_PATH,
    PLAN_KEYS,
    PLAN_PB,
    PLAN_PB_CEILING,
    PLAN_PB_CEILING_PATH,
    PLAN_V15,
    model_kind,
    plan_of,
    spec_sha256,
)

PLAN_ID = PLAN_V15
MIN_TRAIN_N = 10
SCORABLE = "SCORABLE"
INSUFFICIENT = "INSUFFICIENT_TRAINING_HISTORY"
DEFAULT_LOG_PATH = ROOT / "experiments" / "log.jsonl"
GOLDEN_DIR = ROOT / "tests" / "reference" / "macos_golden"
GOLDEN_FAZ1B_DIR = ROOT / "tests" / "reference" / "macos_golden_faz1b"
GOLDEN_FAZ4_DIR = ROOT / "tests" / "reference" / "macos_golden_faz4"
CEILING_PLANS = (PLAN_CEILING, PLAN_PB_CEILING)
PATH_PLANS = (PLAN_CEILING_PATH, PLAN_PB_CEILING_PATH)
RULE_OK = "RULE_OK"
CEILING_MIN_IPO, CEILING_MIN_EVENTS, CEILING_MIN_SURVIVALS = 10, 5, 5

# Faz 1B resmi koşuları: yeni modeller kendi planlarında + karşılaştırıldıkları
# basit kurallar o planlarda (SPEC_PB_V0 §7, §9; SPEC_CEILING_V0 §10).
FAZ1B_RUNS: tuple[tuple[str, str], ...] = (
    ("v1_6_h99", PLAN_V15),
    ("v1_5_market20_v0", PLAN_V15),
    ("pb_v0", PLAN_PB),
    *((m, PLAN_PB) for m in ("base_always_ceiling", "base_train_median", "base_train_mean", "base_zero", "base_rate",
                             "base_last10_rate")),
    ("ceiling_hazard_v0", PLAN_CEILING),
    ("ceiling_hazard_v0@INF", PLAN_CEILING),
    ("base_km_expanding", PLAN_CEILING),
    ("base_km_last10", PLAN_CEILING),
    ("base_always_ceiling", PLAN_CEILING),
    ("pb_ceiling_v0", PLAN_PB_CEILING),
    ("pb_ceiling_v0@INF", PLAN_PB_CEILING),
    ("base_km_expanding", PLAN_PB_CEILING),
    ("base_km_last10", PLAN_PB_CEILING),
    ("base_always_ceiling", PLAN_PB_CEILING),
)

# Faz 4 resmi koşuları (SPEC_CEILING_PATH_V0 §8): karşılaştırma ledger'ları yeniden koşulmaz (Faz 1A/1B altınları).
FAZ4_RUNS: tuple[tuple[str, str], ...] = (
    ("ceiling_path_v0", PLAN_CEILING_PATH),
    ("ceiling_path_v0@INF", PLAN_CEILING_PATH),
    ("pb_ceiling_path_v0", PLAN_PB_CEILING_PATH),
)


def run_key(model_id: str, plan_id: str) -> str:
    """Koşu kimliği: model kendi planındaysa model_id, değilse model_id__plan."""
    return model_id if plan_id == plan_of(model_id) else f"{model_id}__{PLAN_KEYS[plan_id]}"


class BacktestStop(RuntimeError):
    pass


@dataclass(frozen=True)
class Fold:
    horizon: str
    test_ticker: str
    prediction_date: str
    prediction_cutoff_date: str
    target_session_date: str
    training: tuple[str, ...]
    n_chronological: int
    status: str

    @property
    def fold_id(self) -> str:
        return f"{self.horizon}|{self.test_ticker}"


def _cutoff(prediction_date: str) -> str:
    from datetime import date, timedelta

    return (date.fromisoformat(prediction_date) - timedelta(days=1)).isoformat()


def plan_folds(dataset: Dataset) -> list[Fold]:
    rows = dataset.rows
    ordered = [r.ticker for r in rows]
    by = dataset.by_ticker()
    folds: list[Fold] = []
    for h in HORIZONS:
        for test in ordered:
            pdate = by[test].first_trading_date
            cutoff = _cutoff(pdate)
            training = tuple(t for t in ordered if by[t].targets[h].session_date < pdate)
            for t in training:
                if t == test:
                    raise BacktestStop(f"kendi kendini eğitme: {t}/{h}")
                if by[t].first_trading_date == pdate:
                    raise BacktestStop(f"aynı gün sızıntısı: {t}->{test}/{h}")
                if by[t].targets[h].session_date > cutoff:
                    raise BacktestStop(f"gelecek sızıntısı: {t}->{test}/{h}")
            folds.append(Fold(
                horizon=h, test_ticker=test, prediction_date=pdate, prediction_cutoff_date=cutoff,
                target_session_date=by[test].targets[h].session_date, training=training,
                n_chronological=sum(1 for t in ordered if by[t].first_trading_date < pdate),
                status=SCORABLE if len(training) >= MIN_TRAIN_N else INSUFFICIENT,
            ))
    return folds


def plan_folds_pb(dataset: Dataset, pb: Mapping[str, Any]) -> list[Fold]:
    """SPEC_PB_V0 §6: V1.5 kuralı, ama bilgi kesimi B(k) = ilk talep toplama günü.
    Eğitim satırı (j, h) ancak target_session_date(j, D_h) < B(k); MIN_TRAIN_N = 10."""
    rows = dataset.rows
    ordered = [r.ticker for r in rows]
    by = dataset.by_ticker()
    folds: list[Fold] = []
    for h in HORIZONS:
        for test in ordered:
            b = pb[test].first_bookbuilding_date
            cutoff = _cutoff(b)
            training = tuple(t for t in ordered if by[t].targets[h].session_date < b)
            for t in training:
                if t == test:
                    raise BacktestStop(f"kendi kendini eğitme: {t}/{h}")
                if not by[t].first_trading_date < b:
                    raise BacktestStop(f"talep toplama kesimi sızıntısı: {t}->{test}/{h}")
                if by[t].targets[h].session_date > cutoff:
                    raise BacktestStop(f"gelecek sızıntısı: {t}->{test}/{h}")
            folds.append(Fold(
                horizon=h, test_ticker=test, prediction_date=b, prediction_cutoff_date=cutoff,
                target_session_date=by[test].targets[h].session_date, training=training,
                n_chronological=sum(1 for t in ordered if by[t].first_trading_date < b),
                status=SCORABLE if len(training) >= MIN_TRAIN_N else INSUFFICIENT,
            ))
    return folds


@dataclass(frozen=True)
class CeilingFold:
    """Tavan planlarında test arzı başına tek fold (kişi-dönem eğitim kümesi)."""

    test_ticker: str
    first_trading_date: str
    cutoff_date: str             # T(k) ya da B(k); PP satırı ancak seans tarihi < cutoff
    training: tuple[str, ...]    # en az bir PP satırı olan eğitim arzları, (ftd, ticker) sırası
    n_pp_rows: int
    n_events: int
    n_survivals: int
    max_session_date: Optional[str]
    pp_sha256: str
    status: str
    horizon: str = "CEILING"
    n_oot_open: int = 0                          # Faz 7 havuz planı: eğitimdeki açık küme arzı sayısı
    filter_excluded: tuple[str, ...] = ()        # Faz 7: f3 filtre dışlaması (bu fold'da kullanılmayan birimler)

    @property
    def fold_id(self) -> str:
        return f"CEILING|{self.test_ticker}"


def plan_ceiling_folds(dataset: Dataset, plan_id: str, pb: Optional[Mapping[str, Any]] = None) -> list[CeilingFold]:
    """SPEC_CEILING_V0 §9 (PLAN_CEILING: kesim T, f3 dolu arzlar) ve SPEC_PB_V0 §9
    (PLAN_PB_CEILING: kesim B, 99 arz). Aday j: first_trading_date(j) < kesim; (j, d)
    satırı ancak seans tarihi < kesim; skorlanabilir: ≥ 10 arz, ≥ 5 olay, ≥ 5 sağ kalım."""
    if plan_id == PLAN_CEILING:
        eligible = [r for r in dataset.rows if r.inputs["total_demand_multiple"] is not None]
        cutoff_of = {r.ticker: r.first_trading_date for r in eligible}
    elif plan_id == PLAN_PB_CEILING:
        eligible = list(dataset.rows)
        cutoff_of = {r.ticker: pb[r.ticker].first_bookbuilding_date for r in eligible}
    else:
        raise BacktestStop(f"tavan planı değil: {plan_id}")
    units = {r.ticker: sv.unit_of(r) for r in eligible}
    folds: list[CeilingFold] = []
    for k in eligible:
        c = cutoff_of[k.ticker]
        candidates = [units[j.ticker] for j in eligible if j.first_trading_date < c]
        rows = sv.pp_table(candidates, c)
        training = tuple(dict.fromkeys(r.ticker for r in rows))
        if k.ticker in training:
            raise BacktestStop(f"kendi kendini eğitme: {k.ticker}")
        dates = [units[r.ticker].session_dates[r.day - 1] for r in rows]
        if any(d >= c for d in dates):
            raise BacktestStop(f"gelecek sızıntısı: {k.ticker}")
        ev = sum(r.event for r in rows)
        ok = len(training) >= CEILING_MIN_IPO and ev >= CEILING_MIN_EVENTS and len(rows) - ev >= CEILING_MIN_SURVIVALS
        folds.append(CeilingFold(
            test_ticker=k.ticker, first_trading_date=k.first_trading_date, cutoff_date=c, training=training,
            n_pp_rows=len(rows), n_events=ev, n_survivals=len(rows) - ev, max_session_date=max(dates) if dates else None,
            pp_sha256=identity_hash([f"{r.ticker}|{r.day}|{r.event}" for r in rows]),
            status=SCORABLE if ok else INSUFFICIENT,
        ))
    return folds


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def _score_table(entries) -> str:
    return canonical_json([{"hyperparameter": e.hyperparameter, "score": e.score, "fold_count": e.fold_count} for e in entries])


def _fold_identity(fold: Fold, by: Mapping[str, IPORow]) -> dict[str, Any]:
    h = fold.horizon
    test = by[fold.test_ticker]
    return {
        "fold_id": fold.fold_id,
        "horizon": h,
        "ticker": fold.test_ticker,
        "prediction_date": fold.prediction_date,
        "prediction_cutoff_date": fold.prediction_cutoff_date,
        "target_session_date": fold.target_session_date,
        "training_n": len(fold.training),
        "n_chronological_train": fold.n_chronological,
        "training_tickers_sha256": identity_hash(fold.training),
        "training_targets_sha256": identity_hash(
            [f"{t}|{by[t].targets[h].session_date}|{by[t].targets[h].R}|{by[t].targets[h].Y}" for t in fold.training]
        ),
        "ipo_price": test.inputs["ipo_price_tl"],
        "realized_return": test.targets[h].R,
        "realized_direction": test.targets[h].Y,
        "official_close": test.targets[h].close,
    }


def _fold_identity_pb(fold: Fold, by: Mapping[str, IPORow]) -> dict[str, Any]:
    ident = _fold_identity(fold, by)
    out: dict[str, Any] = {}
    for k, v in ident.items():
        out[k] = v
        if k == "ticker":
            out["first_trading_date"] = by[fold.test_ticker].first_trading_date
            out["information_cutoff"] = "first_bookbuilding_date"
    return out


def _ceiling_identity(fold: CeilingFold, by: Mapping[str, IPORow]) -> dict[str, Any]:
    test = by[fold.test_ticker]
    out: dict[str, Any] = {
        "fold_id": fold.fold_id,
        "ticker": fold.test_ticker,
        "first_trading_date": fold.first_trading_date,
        "prediction_date": fold.cutoff_date,
        "training_n_ipo": len(fold.training),
        "training_n_pp_rows": fold.n_pp_rows,
        "training_n_events": fold.n_events,
        "training_n_survivals": fold.n_survivals,
        "training_max_session_date": fold.max_session_date,
        "training_tickers_sha256": identity_hash(fold.training),
        "training_pp_sha256": fold.pp_sha256,
        "realized_L": test.ceiling_streak,
    }
    for k in range(1, sv.DAYS + 1):
        out[f"realized_close_D{k}"] = test.ceiling_close[k - 1]
    return out


def _curve_columns(prefix: str, values: Optional[Sequence[float]]) -> dict[str, Any]:
    return {f"{prefix}_{k}": (None if values is None else values[k - 1]) for k in range(1, sv.DAYS + 1)}


def _reclose_columns(rec: Mapping[str, float]) -> dict[str, Any]:
    return {f"reclose_{k}": rec[k] for k in ("n_a", "a_a", "r_a", "n_b", "a_b", "r_b")}


def _hazard_task(payload: dict[str, Any]) -> dict[str, Any]:
    """Tek tavan fold'u (alt süreçte de çalışır): λ seçimi + nihai fit + test tahmini."""
    from . import hazard as hz

    res = hz.fit_training_set(payload["units"], payload["raw"], payload["status"], cutoff=payload["cutoff"],
                              features=payload["features"], recipe=payload["recipe"], grid=payload["grid"])
    ok = res.status == hz.STATUS_FIT_OK
    pred = res.predict(payload["test_raw"], payload["test_status"]) if ok else None
    out: dict[str, Any] = {
        "status": res.status,
        "n_ipo_check": res.n_ipo,
        "n_pp_rows_check": res.n_pp_rows,
        "selected_lambda": hz.lambda_label(res.selected_lambda),
        "lambda_score_table": canonical_json(res.score_table),
        "n_lambda_not_converged": sum(1 for e in res.score_table if e["status"] != hz.SCORED),
        "columns": canonical_json(list(res.fit.columns)),
        **{f"gamma_{g}": float(res.fit.gamma[i]) for i, g in enumerate(sv.GROUP_NAMES)},
        **{f"beta_{f}": v for f, v in res.beta_by_feature().items()},
        "solver_iterations": res.fit.iterations,
        "solver_grad_max": res.fit.grad_max,
        "test_f3_clipped": None if pred is None else pred["clipped"],
        **_curve_columns("hazard", pred and pred["hazards"]),
        **_curve_columns("S", pred and pred["S"]),
        **_curve_columns("P_close", pred and pred["P_close"]),
        **_reclose_columns(res.reclose),
    }
    return out


def _run_hazard(spec: Mapping[str, Any], dataset: Dataset, folds: Sequence[CeilingFold], workers: int) -> list[dict[str, Any]]:
    from . import hazard as hz

    features = tuple(spec["features"])
    rows = list(dataset.rows)
    raw = fitmod.model_raw_features(spec, rows)[0] if features else {r.ticker: {} for r in rows}
    status = {r.ticker: r.total_demand_filter_status for r in rows}
    units = {r.ticker: sv.unit_of(r) for r in rows}
    recipe = fitmod.recipe_for(spec) if features else None
    grid = tuple(hz.lambda_parse(x) for x in spec["lambda_grid"])
    payloads = [{
        "units": [units[t] for t in f.training], "raw": {t: raw[t] for t in f.training},
        "status": {t: status[t] for t in f.training}, "cutoff": f.cutoff_date, "features": features, "recipe": recipe,
        "grid": grid, "test_raw": raw[f.test_ticker], "test_status": status[f.test_ticker],
    } for f in folds]
    if workers <= 1:
        parts = [_hazard_task(p) for p in payloads]
    else:
        ctx = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
            parts = list(pool.map(_hazard_task, payloads, chunksize=1))
    for f, part in zip(folds, parts):
        if (part.pop("n_ipo_check"), part.pop("n_pp_rows_check")) != (len(f.training), f.n_pp_rows):
            raise BacktestStop(f"{f.fold_id}: fit'in eğitim kümesi fold planıyla aynı değil")
    return parts


def _ceiling_rule_row(algorithm: str, fold: CeilingFold, units: Mapping[str, sv.Unit]) -> dict[str, Any]:
    """Tavan planında kural: Kaplan–Meier (genişleyen / son-10) ya da her zaman tavan (S_k = 1).
    Aynı PP eğitim kümesi; P_close aynı yeniden-tavan oranıyla."""
    train = [units[t] for t in fold.training]
    rows = sv.pp_table(train, fold.cutoff_date)
    if algorithm == "KM_EXPANDING":
        hazards = sv.km_hazards(rows)
    elif algorithm == "KM_LAST10":
        hazards = sv.km_hazards(rows, last_n=sv.LAST_N)
    elif algorithm == "ALWAYS_CEILING":
        hazards = [0.0] * sv.DAYS
    else:
        raise BacktestStop(f"tavan planında tanımsız kural: {algorithm}")
    S = sv.survival(hazards)
    rec = sv.reclose_counts(train, fold.cutoff_date)
    return {"status": RULE_OK, **_curve_columns("hazard", hazards), **_curve_columns("S", S),
            **_curve_columns("P_close", sv.p_close(S, rec["r_a"], rec["r_b"])), **_reclose_columns(rec)}


def _labeled_score_table(entries, kind: str) -> str:
    """V1.6/PB biçimi: INF/ZERO metin, aday durumu yazılı."""
    return canonical_json([{"hyperparameter": fitmod.hp_label(e.hyperparameter, kind), "score": e.score,
                            "fold_count": e.fold_count, "status": e.status} for e in entries])


def _v15_task(payload: dict[str, Any]) -> dict[str, Any]:
    """Tek fold (alt süreçte de çalışır). `grid`/`recipe` verilmezse V1.5'in kendisi;
    V1.5 biçimli satır Faz 1A altın ledger'ıyla bayt bayt aynıdır."""
    grid = payload.get("grid", fitmod.V1_5_GRID)
    recipe = payload.get("recipe", pp.V1_5_RECIPE)
    hf = fitmod.fit_v1_5_horizon(
        payload["order"], payload["raw"], payload["R"], payload["Y"], payload["status"],
        test_raw=payload["test_raw"], test_filter_status=payload["test_status"], grid=grid, recipe=recipe,
    )
    r, g = hf.ridge, hf.logit
    legacy = grid.legacy_format
    uses_f3 = "f3" in recipe.substantive
    lo, hi = physical_return_bounds(payload["horizon"])
    out: dict[str, Any] = {}
    if uses_f3:
        out["test_f3_missing"] = payload["test_raw"]["f3"] is None
    out.update({
        "ridge_status": r.status,
        "ridge_selected_alpha": r.selected_alpha if legacy else fitmod.hp_label(r.selected_alpha, "alpha"),
        "ridge_tuning_status": r.tuning_status,
        "ridge_inner_fold_n": r.inner_fold_n,
        "ridge_columns": canonical_json(list(r.columns)),
        "ridge_score_table": _score_table(r.score_table) if legacy else _labeled_score_table(r.score_table, "alpha"),
        "ridge_prediction": r.prediction,
        "ridge_outside_physical_bound": None if r.prediction is None else not (lo <= r.prediction <= hi),
        "logit_status": g.status,
        "logit_selected_C": g.selected_C if legacy else fitmod.hp_label(g.selected_C, "C"),
        "logit_tuning_status": g.tuning_status,
        "logit_inner_fold_n": g.inner_fold_n,
        "logit_columns": canonical_json(list(g.columns)),
        "logit_score_table": _score_table(g.score_table) if legacy else _labeled_score_table(g.score_table, "C"),
        "logit_n_class_0": g.n_class_0,
        "logit_n_class_1": g.n_class_1,
        "logit_probability": g.probability,
        "logit_predicted_class": g.predicted_class,
        "logit_fit_warnings": canonical_json(list(g.observed_fit_warnings)),
    })
    if not legacy:
        out["logit_final_fit_attempts"] = canonical_json([list(a) for a in g.final_attempts])
    if uses_f3:
        out["f3_filter_nulled_n"] = hf.filter_stats["f3_filter_nulled_n"]
        out["f3_filter_mode_ties_n"] = hf.filter_stats["f3_filter_mode_ties_n"]
    return out


def _v15_payloads(dataset: Dataset, folds: Sequence[Fold], raw: Optional[Mapping[str, Mapping[str, Any]]] = None) -> list[dict[str, Any]]:
    by = dataset.by_ticker()
    if raw is None:
        raw = {r.ticker: compute_features(**r.feature_inputs()).as_dict() for r in dataset.rows}
    status = {r.ticker: r.total_demand_filter_status for r in dataset.rows}
    payloads = []
    for f in folds:
        payloads.append({
            "horizon": f.horizon,
            "order": list(f.training),
            "raw": {t: raw[t] for t in f.training},
            "R": {t: by[t].targets[f.horizon].R_float for t in f.training},
            "Y": {t: by[t].targets[f.horizon].Y for t in f.training},
            "status": {t: status[t] for t in f.training},
            "test_raw": raw[f.test_ticker],
            "test_status": status[f.test_ticker],
        })
    return payloads


def default_workers() -> int:
    return max(1, min(10, (os.cpu_count() or 1) - 1))


def _run_v15(dataset: Dataset, folds: Sequence[Fold], workers: int) -> list[dict[str, Any]]:
    payloads = _v15_payloads(dataset, folds)
    if workers <= 1:
        return [_v15_task(p) for p in payloads]
    ctx = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
        return list(pool.map(_v15_task, payloads, chunksize=2))


def _run_linear(spec: Mapping[str, Any], dataset: Dataset, folds: Sequence[Fold], workers: int,
                raw: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """v1_6_h99, v1_5_market20_v0, pb_v0: aynı fold çekirdeği, şartnamenin ızgarası ve tarifi."""
    payloads = _v15_payloads(dataset, folds, raw=raw)
    grid, recipe = fitmod.grid_from_spec(spec), fitmod.recipe_for(spec)
    for p in payloads:
        p["grid"], p["recipe"] = grid, recipe
    if workers <= 1:
        return [_v15_task(p) for p in payloads]
    ctx = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
        return list(pool.map(_v15_task, payloads, chunksize=2))


def _rule_row(algorithm: str, fold: Fold, by: Mapping[str, IPORow]) -> dict[str, Any]:
    h = fold.horizon
    ret = rule_return(algorithm, h, [by[t].targets[h].R_float for t in fold.training])
    p = rule_p_up(algorithm, [by[t].targets[h].Y for t in fold.training])
    return {
        "rule_return": ret,
        "rule_p_up": p,
        "rule_direction": None if p is None else direction(p),
    }


@dataclass
class BacktestResult:
    model_id: str
    spec_sha256: str
    folds: list[Fold]
    ledger: list[dict[str, Any]]
    metrics: dict[str, Any]
    ledger_csv: bytes
    log_entry: dict[str, Any]


def ledger_csv_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    if not rows:
        raise BacktestStop("boş ledger yazılmaz")
    fields = list(rows[0])
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(fields)
    for r in rows:
        if list(r) != fields:
            raise BacktestStop("ledger şeması satırlar arasında kaydı")
        w.writerow([_fmt(r[k]) for k in fields])
    return buf.getvalue().encode("utf-8")


def _regression_points(ledger, value_key: str, ok) -> list[mx.RegressionPoint]:
    return [
        mx.RegressionPoint(
            ticker=r["ticker"], prediction_date=r["prediction_date"], predicted=r[value_key],
            actual=float(r["realized_return"]), ipo_price=Decimal(r["ipo_price"]), actual_close=Decimal(r["official_close"]),
        )
        for r in ledger if ok(r)
    ]


def _classification_points(ledger, p_key: str, dir_key: str, ok) -> list[mx.ClassificationPoint]:
    return [
        mx.ClassificationPoint(
            ticker=r["ticker"], prediction_date=r["prediction_date"], probability=r[p_key],
            direction=r[dir_key], actual=int(r["realized_direction"]),
        )
        for r in ledger if ok(r)
    ]


def compute_metrics(model_id: str, ledger: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Modelin kendi skorlanabilir kümesinde metrikler (pencere başına).
    Ridge + Logit: Ridge FIT_OK ve Logit FIT_OK fold'ları ayrı ayrı. Kurallar: tüm fold'lar."""
    out: dict[str, Any] = {}
    for h in HORIZONS:
        hl = [r for r in ledger if r["horizon"] == h]
        if model_kind(model_id) == "linear":
            reg = _regression_points(hl, "ridge_prediction", lambda r: r["ridge_status"] == fitmod.STATUS_FIT_OK)
            cls = _classification_points(hl, "logit_probability", "logit_predicted_class",
                                         lambda r: r["logit_status"] == fitmod.STATUS_FIT_OK)
        else:
            reg = _regression_points(hl, "rule_return", lambda r: r["rule_return"] is not None)
            cls = _classification_points(hl, "rule_p_up", "rule_direction", lambda r: r["rule_p_up"] is not None)
        out[h] = {
            "folds": len(hl),
            "return": mx.windowed(reg, mx.regression_metrics) if reg else None,
            "p_up": mx.windowed(cls, mx.classification_metrics) if cls else None,
        }
    return out


def _log_metrics(metrics: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for h, m in metrics.items():
        entry: dict[str, Any] = {"folds": m["folds"]}
        if m["return"]:
            a = m["return"]["ALL"]
            entry["return"] = {"n": a["n"], "mae": a["mae"], "median_ae": a["median_ae"]}
        if m["p_up"]:
            a = m["p_up"]["ALL"]
            entry["p_up"] = {"n": a["n"], "brier": a["brier"], "accuracy": a["accuracy"]}
        compact[h] = entry
    return compact


def append_log(log_path: Path, entry: Mapping[str, Any]) -> None:
    """Append-only: dosya yalnız sonuna yazılır, var olan satırlar okunmaz/değişmez."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(canonical_json(dict(entry)) + "\n")


def compute_ceiling_metrics(ledger: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Tavan çıktıları (SPEC_SCORING §7): RPS (birincil), S_k ve P_close_k için Brier
    (k = 1, 3, 5, 10; kırpmasız), kalibrasyon ort(S_1) ve gözlenen D1 tavan oranı."""
    rows = [r for r in ledger if r["status"] in (fitmod.STATUS_FIT_OK, RULE_OK)]
    if not rows:
        return {"n": 0}
    ks = (1, 3, 5, 10)
    S = [[r[f"S_{k}"] for k in range(1, sv.DAYS + 1)] for r in rows]
    return {
        "n": len(rows),
        "rps": mx.mean_or_none(sv.rps(s, r["realized_L"]) for s, r in zip(S, rows)),
        "brier_S": {f"k{k}": mx.mean_or_none((r[f"S_{k}"] - (1.0 if r["realized_L"] >= k else 0.0)) ** 2 for r in rows) for k in ks},
        "brier_P_close": {f"k{k}": mx.mean_or_none((r[f"P_close_{k}"] - r[f"realized_close_D{k}"]) ** 2 for r in rows) for k in ks},
        "mean_S_1": mx.mean_or_none(r["S_1"] for r in rows),
        "observed_D1_ceiling_rate": mx.mean_or_none(float(r["realized_L"] >= 1) for r in rows),
    }


def _check_run(model_id: str, plan_id: str) -> str:
    kind = model_kind(model_id)
    own = plan_of(model_id)
    algorithm = MODEL_SPECS[model_id]["algorithm"]
    if kind in ("linear", "hazard", "ceiling_path") and plan_id != own:
        raise BacktestStop(f"{model_id} yalnız kendi planında koşar ({own})")
    if kind != "ceiling_path" and plan_id in PATH_PLANS:
        raise BacktestStop(f"{model_id} tavan yolu planında koşmaz")
    if kind == "km" and plan_id not in CEILING_PLANS:
        raise BacktestStop(f"{model_id} yalnız tavan planlarında koşar")
    if kind == "rule" and plan_id in CEILING_PLANS and algorithm != "ALWAYS_CEILING":
        raise BacktestStop(f"{model_id} tavan çıktısı üretmez")
    return kind


def run_backtest(
    model_id: str,
    dataset: Dataset,
    *,
    log_path: Path,
    context: str,
    workers: Optional[int] = None,
    plan_id: Optional[str] = None,
) -> BacktestResult:
    """Bir modelin H99 walk-forward backtest'i; sonunda günlüğe bir satır ekler.
    `plan_id` verilmezse modelin kendi planı (Faz 1A modelleri için PLAN_V15)."""
    spec = MODEL_SPECS[model_id]
    plan_id = plan_id or plan_of(model_id)
    kind = _check_run(model_id, plan_id)
    if kind in ("linear", "hazard"):
        fitmod.verify_runtime()
    workers = default_workers() if workers is None else workers
    started = now_istanbul()
    by = dataset.by_ticker()
    pb = load_pb(dataset) if plan_id in (PLAN_PB, PLAN_PB_CEILING) else None
    extra: list[dict[str, Any]] = []
    entry_extra: dict[str, Any] = {}
    if plan_id in PATH_PLANS:
        from . import ceiling_path as cp

        ledger, info = cp.backtest_ledger(spec, dataset)
        folds = [r["fold_id"] for r in ledger]
        metrics = cp.path_metrics(ledger)
        log_metrics = metrics
        folds_scorable = {"CEILING_PATH": sum(1 for r in ledger if r["status"] == cp.STATUS_OK)}
        entry_extra = {k: info[k] for k in ("survival_model_id", "survival_ledger", "survival_ledger_sha256")}
    elif plan_id in CEILING_PLANS:
        folds = plan_ceiling_folds(dataset, plan_id, pb)
        scorable = [f for f in folds if f.status == SCORABLE]
        identities = [_ceiling_identity(f, by) for f in scorable]
        if kind == "hazard":
            parts = _run_hazard(spec, dataset, scorable, workers)
        else:
            units = {r.ticker: sv.unit_of(r) for r in dataset.rows}
            parts = [_ceiling_rule_row(spec["algorithm"], f, units) for f in scorable]
        ledger = [{"model_id": model_id, **ident, **part} for ident, part in zip(identities, parts)]
        metrics = compute_ceiling_metrics(ledger)
        log_metrics = metrics
        folds_scorable = {"CEILING": len(scorable)}
    else:
        folds = plan_folds(dataset) if plan_id == PLAN_V15 else plan_folds_pb(dataset, pb)
        scorable = [f for f in folds if f.status == SCORABLE]
        identities = [(_fold_identity if plan_id == PLAN_V15 else _fold_identity_pb)(f, by) for f in scorable]
        if model_id == "v1_5_h99":
            parts = _run_v15(dataset, scorable, workers)
        elif kind == "linear":
            raw, info = fitmod.model_raw_features(spec, list(dataset.rows))
            parts = _run_linear(spec, dataset, scorable, workers, raw)
            extra = [_linear_extra(spec, f, raw, info, pb) for f in scorable]
        else:
            parts = [_rule_row(spec["algorithm"], f, by) for f in scorable]
        if not extra:
            extra = [{} for _ in scorable]
        ledger = [{"model_id": model_id, **ident, **ex, **part} for ident, ex, part in zip(identities, extra, parts)]
        metrics = compute_metrics(model_id, ledger)
        log_metrics = _log_metrics(metrics)
        folds_scorable = {h: sum(1 for f in scorable if f.horizon == h) for h in HORIZONS}
    payload = ledger_csv_bytes(ledger)
    entry = {
        "kind": "backtest",
        "context": context,
        "model_id": model_id,
        "spec_sha256": spec_sha256(spec),
        "plan_id": plan_id,
        "data_version_sha256": dataset.data_version_sha256,
        "training_table_sha256": dataset.table_sha256,
        "folds_total": len(folds),
        "folds_scorable": folds_scorable,
        "ledger_sha256": sha256_bytes(payload),
        **entry_extra,
        "metrics": log_metrics,
        "started_at": started,
        "finished_at": now_istanbul(),
        **code_version(),
    }
    if "spec_document" in spec:
        entry["spec_document"] = spec["spec_document"]["path"]
        entry["spec_document_sha256"] = sha256_file(ROOT / spec["spec_document"]["path"])
    key = run_key(model_id, plan_id)
    if key != model_id:
        entry["run_key"] = key
    if kind in ("linear", "hazard"):
        entry["runtime"] = fitmod.verify_runtime()
    append_log(log_path, entry)
    return BacktestResult(model_id, entry["spec_sha256"], folds, ledger, metrics, payload, entry)


def _linear_extra(spec: Mapping[str, Any], fold: Fold, raw: Mapping[str, Mapping[str, Any]], info: Mapping[str, Any],
                  pb: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    """Test arzının modele özgü girdileri (ledger'da görünür olsun diye)."""
    t = fold.test_ticker
    if "f6" in spec["features"]:
        m = info["market20_training"][t]
        return {"test_f6": m["f6"], "test_f6_S0_date": m["S0_date"], "test_f6_S20_date": m["S20_date"]}
    if fitmod.uses_pb_features(spec):
        from .features import compute_pb_features

        f = compute_pb_features(pb[t].fields)
        return {"test_pb1": f.pb1, "test_pb2": f.pb2, "test_pb3": f.pb3, "test_pb4": f.pb4}
    return {}


def run_all(dataset: Dataset, *, log_path: Path, context: str, workers: Optional[int] = None) -> dict[str, BacktestResult]:
    """Kayıtlı her model, kendi planında."""
    return {m: run_backtest(m, dataset, log_path=log_path, context=context, workers=workers) for m in MODEL_SPECS}


def run_suite(runs: Sequence[tuple[str, str]], dataset: Dataset, *, log_path: Path, context: str,
              workers: Optional[int] = None) -> dict[str, BacktestResult]:
    """(model_id, plan_id) koşuları; anahtar run_key."""
    out: dict[str, BacktestResult] = {}
    for model_id, plan_id in runs:
        key = run_key(model_id, plan_id)
        if key in out:
            raise BacktestStop(f"tekrarlı koşu {key}")
        out[key] = run_backtest(model_id, dataset, log_path=log_path, context=context, workers=workers, plan_id=plan_id)
    return out


def golden_filename(model_id: str) -> str:
    return f"{model_id}_fold_ledger.csv"


def write_golden(results: Mapping[str, BacktestResult], out_dir: Path = GOLDEN_DIR) -> dict[str, Any]:
    """macOS altın ledger'ları. Var olan dosyanın üzerine yazmaz."""
    from .provenance import pretty_json_bytes, runtime_versions

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    for model_id, res in results.items():
        path = out_dir / golden_filename(model_id)
        if path.exists():
            raise BacktestStop(f"{path} zaten var; altın referans üzerine yazılmaz")
        path.write_bytes(res.ledger_csv)
        files[path.name] = sha256_file(path)
    manifest = {
        "description": "Faz 1A port kabulünden (testler 1-3) sonra bu makinede üretilen H99 walk-forward fold ledger'ları. Regresyon testi bunlara karşı BİREBİR (bayt) çalışır.",
        "plan_id": PLAN_ID,
        "models": {m: {"file": golden_filename(m), "spec_sha256": r.spec_sha256, "ledger_sha256": files[golden_filename(m)]}
                   for m, r in results.items()},
        "runtime": runtime_versions(),
        "machine": {"platform": _platform()},
        "created_at": now_istanbul(),
        **code_version(),
    }
    (out_dir / "MANIFEST.json").write_bytes(pretty_json_bytes(manifest))
    lines = "".join(f"{sha}  {name}\n" for name, sha in sorted(files.items()))
    (out_dir / "SHA256SUMS").write_text(lines, encoding="utf-8")
    return manifest


FAZ1B_GOLDEN_DESCRIPTION = ("Faz 1B: yeni modellerin ve karşılaştırıldıkları basit kuralların bu makinedeki H99 walk-forward fold "
                             "ledger'ları. Regresyon testi bunlara karşı BİREBİR (bayt) çalışır; docs/MODELS.md bunlardan üretilir.")
FAZ4_GOLDEN_DESCRIPTION = ("Faz 4: tavan yolu modellerinin (SPEC_CEILING_PATH_V0) bu makinedeki H99 walk-forward fold ledger'ları; "
                           "S_k Faz 1B tavan ledger'larından aynen. Regresyon testi bunlara karşı BİREBİR (bayt) çalışır; "
                           "docs/MODELS.md Faz 4 bölümü bunlardan üretilir.")


def write_golden_runs(results: Mapping[str, BacktestResult], out_dir: Path = GOLDEN_FAZ1B_DIR,
                      description: str = FAZ1B_GOLDEN_DESCRIPTION) -> dict[str, Any]:
    """Altın ledger'lar (koşu anahtarı başına bir dosya). Var olan dosyanın üzerine yazmaz;
    Faz 1A dizinine (GOLDEN_DIR) dokunmaz."""
    from .provenance import pretty_json_bytes, runtime_versions

    out_dir = Path(out_dir)
    if out_dir.resolve() == GOLDEN_DIR.resolve():
        raise BacktestStop("Faz 1A altın dizini değiştirilmez")
    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    for key, res in results.items():
        path = out_dir / golden_filename(key)
        if path.exists():
            raise BacktestStop(f"{path} zaten var; altın referans üzerine yazılmaz")
        path.write_bytes(res.ledger_csv)
        files[path.name] = sha256_file(path)
    manifest = {
        "description": description,
        "runs": {key: {"file": golden_filename(key), "model_id": r.model_id, "plan_id": r.log_entry["plan_id"],
                       "spec_sha256": r.spec_sha256, "ledger_sha256": files[golden_filename(key)]}
                 for key, r in results.items()},
        "runtime": runtime_versions(),
        "machine": {"platform": _platform()},
        "created_at": now_istanbul(),
        **code_version(),
    }
    (out_dir / "MANIFEST.json").write_bytes(pretty_json_bytes(manifest))
    lines = "".join(f"{sha}  {name}\n" for name, sha in sorted(files.items()))
    (out_dir / "SHA256SUMS").write_text(lines, encoding="utf-8")
    return manifest


def _platform() -> str:
    import platform

    return f"{platform.system()} {platform.release()} {platform.machine()} / {platform.python_implementation()} {platform.python_version()}"


# ============================================================================
# Faz 7: tavan serisi v1 (SPEC_HAZARD_V1 §3–§5, §11; KARARLAR; SPEC_DEVIATIONS J)
# ============================================================================

GOLDEN_FAZ7_DIR = ROOT / "tests" / "reference" / "macos_golden_faz7"
NEAR_ERA_START = "2024-01-01"            # §5.1: yakın dönem = ilk işlem ≥ 2024-01-01 olan fold'lar (78 fold, 22 ay bloğu)
NEAR_ERA_TOLERANCE = 0.010               # §5.1 δ
LABEL_BREAKS = "bozuyor"
LABEL_TOLERANCE = "tolerans içinde"
LABEL_UNCLEAR = "belirsiz"
V0_PUBLISHED_MEAN_RPS = 0.1503           # MODELS.md (Faz 1B), 87 fold, 4 hane
# Karşılaştırıcılar: Faz 1B altın ledger'ları (yeniden koşulmaz; sha pinli). v0'ınki şartnamedeki `976b4dcea981…`.
FAZ7_COMPARATOR_LEDGERS: dict[str, dict[str, str]] = {
    "ceiling_hazard_v0": {"path": "tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv",
                          "sha256": "976b4dcea9819160bf863873a0a3e3a639942bdfeec6f9229e015047c904665b"},
    "ceiling_hazard_v0@INF": {"path": "tests/reference/macos_golden_faz1b/ceiling_hazard_v0@INF_fold_ledger.csv",
                              "sha256": "90b610463de417c702cfae8032957aa4745aefcb4814a2745459da90bddb2f93"},
    "base_km_expanding": {"path": "tests/reference/macos_golden_faz1b/base_km_expanding_fold_ledger.csv",
                          "sha256": "ed1b8821a0c5faac6a068402d545aa67810d53d2e523f8062100cec81c45017f"},
    "base_km_last10": {"path": "tests/reference/macos_golden_faz1b/base_km_last10_fold_ledger.csv",
                       "sha256": "6d605dd02b7c1a4232a1299bac91a266cc4ee1df2e9446ce995fcea15fa7c26d"},
}
FAZ7_RUNS: tuple[str, ...] = ("ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled",
                              "ceiling_hazard_v1_pooled@INF")
POOLED_KM_RULES: tuple[tuple[str, str], ...] = (("base_km_expanding__pooled", "KM_EXPANDING"), ("base_km_last10__pooled", "KM_LAST10"))
REGIME_COLUMN = "r_pre_equal"


def near_era_label(ci: Optional[Sequence[float]]) -> str:
    """§5.1 karar kuralı (sonuçlar görülmeden, commit A): alt uç > 0 -> "bozuyor"; üst uç ≤ +0.010 -> "tolerans içinde";
    diğer -> "belirsiz" (alt = 0 dışlamaz). Aralık üretilemediyse "belirsiz"."""
    if ci is None:
        return LABEL_UNCLEAR
    lo, hi = ci
    if lo > 0.0:
        return LABEL_BREAKS
    if hi <= NEAR_ERA_TOLERANCE:
        return LABEL_TOLERANCE
    return LABEL_UNCLEAR


def read_pinned_ledger(ref: Mapping[str, str]) -> list[dict[str, str]]:
    raw = (ROOT / ref["path"]).read_bytes()
    if sha256_bytes(raw) != ref["sha256"]:
        raise BacktestStop(f"{ref['path']}: sha256 {sha256_bytes(raw)} != pin {ref['sha256']}")
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))


def _S_of(row: Mapping[str, Any]) -> list[float]:
    return [float(row[f"S_{k}"]) for k in range(1, sv.DAYS + 1)]


def ceiling_loss(metric: str, S: Sequence[float], L: int) -> float:
    """rps ya da brierK (K = 1..10): (S_K − 1[L ≥ K])², kırpmasız (SPEC_SCORING §7)."""
    if metric == "rps":
        return sv.rps(S, L)
    k = int(metric[len("brier"):])
    return (S[k - 1] - (1.0 if L >= k else 0.0)) ** 2


def _ok(row: Mapping[str, Any]) -> bool:
    return row["status"] in (fitmod.STATUS_FIT_OK, RULE_OK)


def paired_ceiling(model_rows: Sequence[Mapping[str, Any]], other_rows: Sequence[Mapping[str, Any]], *, metric: str = "rps",
                   start: Optional[str] = None, end: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Eşleşik fark = model − karşılaştırılan (negatif = model iyi), iki tarafın da skorlandığı fold'larda (ticker ile),
    [start, end) ilk işlem aralığında; %95 aralık SPEC_DEVIATIONS C7 (`metrics.paired_difference`: ilk işlem ayı blokları,
    4000 tekrar, random.Random(20260921)); n < 10 ise aralık yok."""
    other = {r["ticker"]: r for r in other_rows if _ok(r)}
    diffs, months, a, b, tickers = [], [], [], [], []
    for r in model_rows:
        t = r["first_trading_date"]
        if not _ok(r) or (start is not None and t < start) or (end is not None and t >= end) or r["ticker"] not in other:
            continue
        L = int(r["realized_L"])
        la, lb = ceiling_loss(metric, _S_of(r), L), ceiling_loss(metric, _S_of(other[r["ticker"]]), L)
        diffs.append(la - lb)
        months.append(t[:7])
        a.append(la)
        b.append(lb)
        tickers.append(r["ticker"])
    if not diffs:
        return None
    if len(diffs) >= 10 and len(set(months)) >= 6:
        res = mx.paired_difference(diffs, months)
    else:
        res = {"n": len(diffs), "n_months": len(set(months)), "mean": sum(diffs) / len(diffs), "ci95": None,
               "model_better_n": sum(1 for d in diffs if d < 0), "rule_better_n": sum(1 for d in diffs if d > 0),
               "tie_n": sum(1 for d in diffs if d == 0), "verdict": None}
    res.update(metric=metric, model_metric=sum(a) / len(a), rule_metric=sum(b) / len(b), tickers=tickers,
               tie_n_1e12=sum(1 for d in diffs if abs(d) <= 1e-12))
    return res


def near_era_cell(model_rows: Sequence[Mapping[str, Any]], v0_rows: Sequence[Mapping[str, Any]], metric: str = "rps") -> Optional[dict[str, Any]]:
    """§5.1 birincil hücre: v1 − ceiling_hazard_v0, ilk işlem ≥ 2024-01-01; etiket `near_era_label`."""
    res = paired_ceiling(model_rows, v0_rows, metric=metric, start=NEAR_ERA_START)
    if res is not None:
        res["label"] = near_era_label(res["ci95"])
    return res


def v0_mean_rps(v0_rows: Sequence[Mapping[str, Any]]) -> float:
    """§11-8: v0'ın 87 fold ortalama RPS'i altın ledger'ın S_1..S_10'ından (MODELS.md'deki 0.1503)."""
    vals = [sv.rps(_S_of(r), int(r["realized_L"])) for r in v0_rows if _ok(r)]
    return sum(vals) / len(vals)


def v1_dataset(model_id: str) -> Dataset:
    from .data import load_dataset_v2
    from .specs import FAZ7_MODEL_SPECS, PLAN_CEILING_POOLED

    return load_dataset_v2() if FAZ7_MODEL_SPECS[model_id]["plan_id"] == PLAN_CEILING_POOLED else load_dataset()


def _tufe_checked(spec: Mapping[str, Any]):
    from . import tufe

    table = tufe.load()
    pin = {"through_month": spec["deflator"]["through_month"], "prefix_sha256": spec["deflator"]["file_sha256"]}
    tufe.verify_pin(table, pin)
    return table


def v1_raw_features(spec: Mapping[str, Any], rows: Sequence[IPORow]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    """(ham özellikler, TÜFE bilgisi). f1/f2/f3 `features.compute_features`'tan (tek tanım); f1r = `predict_hazard.real_size`
    (f1, TÜFE[T − 2]) — tahminle aynı fonksiyon. TÜFE `tufe.index_for(T)` (PIT bekçisi dahil); v2 satırlarında tablonun
    tufe_index'iyle eşitlik denetlenir. f3 yoksa satırın ham değerleri yine yazılır (plan onu dışarıda bırakır)."""
    from . import tufe
    from .predict_hazard import real_size

    feats = list(spec["features"])
    table = _tufe_checked(spec) if "f1r" in feats else None
    raw: dict[str, dict[str, Any]] = {}
    info: dict[str, dict[str, str]] = {}
    for r in rows:
        f = compute_features(**r.feature_inputs())
        vals = {"f1": f.f1, "f2": f.f2, "f3": f.f3}
        if table is not None:
            t = tufe.index_for(r.first_trading_date, table)
            if getattr(r, "tufe_index", "") and (r.tufe_index, r.tufe_month) != (t["index"], t["month"]):
                raise BacktestStop(f"{r.ticker}: v2 tablosunun tufe_index/ay değeri tufe.index_for ile aynı değil")
            info[r.ticker] = {"month": t["month"], "index": t["index"], "release_date": t["release_date"]}
            vals["f1r"] = real_size(f.f1, t["index"])
        raw[r.ticker] = {k: vals[k] for k in feats}
    return raw, info


def v1_regime(rows: Sequence[IPORow]) -> dict[str, dict[str, float]]:
    """ticker -> {r_pre_equal: r}; r = predict_hazard.regime_value(alloc_regime) (v2 satırı). H99 satırları 0 olmalı."""
    from .predict_hazard import regime_value

    out = {}
    for r in rows:
        v = regime_value(r.alloc_regime)
        if r.cohort == "H99" and v != 0:
            raise BacktestStop(f"{r.ticker}: H99 satırında r = {v} (T ≥ 2023-09-22 > 2023-03-30: r = 0 olmalı)")
        out[r.ticker] = {REGIME_COLUMN: float(v)}
    return out


def plan_pooled_folds(dataset: Dataset, raw: Mapping[str, Mapping[str, Any]]) -> list[CeilingFold]:
    """PLAN_CEILING_POOLED (SPEC_HAZARD_V1 §5.1): test arzları H99'un f3'lü 97'si; aday j: f3 dolu (H99 ya da açık küme) ve
    first_trading_date(j) < T; (j, d) satırı ancak seans tarihi < T; f3'ü bu kümenin filtre moduyla boşalacak birimler dışarıda
    (`hazard.f3_filter_excluded`; SPEC_DEVIATIONS J); skorlanabilir: ≥ 10 arz, ≥ 5 olay, ≥ 5 sağ kalım."""
    from .hazard import f3_filter_excluded

    eligible = [r for r in dataset.rows if r.inputs["total_demand_multiple"] is not None]
    units = {r.ticker: sv.unit_of(r) for r in eligible}
    status = {r.ticker: r.total_demand_filter_status for r in eligible}
    cohort = {r.ticker: r.cohort for r in eligible}
    folds: list[CeilingFold] = []
    for k in eligible:
        if k.cohort != "H99":
            continue
        c = k.first_trading_date
        candidates = [units[j.ticker] for j in eligible if j.first_trading_date < c]
        rows = sv.pp_table(candidates, c)
        training = tuple(dict.fromkeys(r.ticker for r in rows))
        excluded = f3_filter_excluded(training, raw, status)
        if excluded:
            training = tuple(t for t in training if t not in excluded)
            rows = [r for r in rows if r.ticker not in excluded]
        if k.ticker in training:
            raise BacktestStop(f"kendi kendini eğitme: {k.ticker}")
        dates = [units[r.ticker].session_dates[r.day - 1] for r in rows]
        if any(d >= c for d in dates):
            raise BacktestStop(f"gelecek sızıntısı: {k.ticker}")
        ev = sum(r.event for r in rows)
        ok = len(training) >= CEILING_MIN_IPO and ev >= CEILING_MIN_EVENTS and len(rows) - ev >= CEILING_MIN_SURVIVALS
        folds.append(CeilingFold(
            test_ticker=k.ticker, first_trading_date=c, cutoff_date=c, training=training, n_pp_rows=len(rows), n_events=ev,
            n_survivals=len(rows) - ev, max_session_date=max(dates) if dates else None,
            pp_sha256=identity_hash([f"{r.ticker}|{r.day}|{r.event}" for r in rows]),
            status=SCORABLE if ok else INSUFFICIENT, n_oot_open=sum(1 for t in training if cohort[t] != "H99"),
            filter_excluded=tuple(excluded),
        ))
    return folds


def _v1_identity(fold: CeilingFold, by: Mapping[str, IPORow], pooled: bool, tufe_info: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    out = _ceiling_identity(fold, by)
    if pooled:
        out.update(training_n_oot_open=fold.n_oot_open, training_n_filter_excluded=len(fold.filter_excluded),
                   training_filter_excluded_sha256=identity_hash(fold.filter_excluded) if fold.filter_excluded else "")
    if tufe_info:
        t = tufe_info[fold.test_ticker]
        out.update(test_tufe_month=t["month"], test_tufe_index=t["index"])
    return out


def _hazard_task_v1(payload: dict[str, Any]) -> dict[str, Any]:
    """Tek v1 tavan fold'u (alt süreçte de çalışır). `_hazard_task`'ın v1 karşılığı (rejim sütunu, genel kırpma)."""
    from . import hazard as hz

    r_columns = payload["r_columns"]
    res = hz.fit_training_set(payload["units"], payload["raw"], payload["status"], cutoff=payload["cutoff"],
                              features=payload["features"], recipe=payload["recipe"], grid=payload["grid"],
                              regime=payload["regime"], r_columns=r_columns)
    ok = res.status == hz.STATUS_FIT_OK
    pred = res.predict(payload["test_raw"], payload["test_status"], payload["test_regime"]) if ok else None
    out: dict[str, Any] = {
        "status": res.status,
        "n_ipo_check": res.n_ipo,
        "n_pp_rows_check": res.n_pp_rows,
        "selected_lambda": hz.lambda_label(res.selected_lambda),
        "lambda_score_table": canonical_json(res.score_table),
        "n_lambda_not_converged": sum(1 for e in res.score_table if e["status"] != hz.SCORED),
        "columns": canonical_json(list(res.fit.columns)),
        **{f"gamma_{g}": float(res.fit.gamma[i]) for i, g in enumerate(sv.GROUP_NAMES)},
        **{f"delta_{c}": v for c, v in res.delta_by_column().items()},
        **{f"beta_{f}": v for f, v in res.beta_by_feature().items()},
        "solver_iterations": res.fit.iterations,
        "solver_grad_max": res.fit.grad_max,
    }
    if r_columns:
        out.update({f"test_{c}": payload["test_regime"][c] for c in r_columns})
    out.update({
        "test_clipped": None if pred is None else pred["clipped"],
        "test_clipped_features": None if pred is None or pred["clipped_features"] is None else canonical_json(pred["clipped_features"]),
        **_curve_columns("hazard", pred and pred["hazards"]),
        **_curve_columns("S", pred and pred["S"]),
        **_curve_columns("P_close", pred and pred["P_close"]),
        **_reclose_columns(res.reclose),
    })
    return out


def _run_hazard_v1(spec: Mapping[str, Any], dataset: Dataset, folds: Sequence[CeilingFold], workers: int,
                   raw: Mapping[str, Mapping[str, Any]], regime: Optional[Mapping[str, Mapping[str, float]]]) -> list[dict[str, Any]]:
    from . import hazard as hz

    features = tuple(spec["features"])
    rows = list(dataset.rows)
    status = {r.ticker: r.total_demand_filter_status for r in rows}
    units = {r.ticker: sv.unit_of(r) for r in rows}
    recipe = fitmod.recipe_for(spec) if features else None
    grid = tuple(hz.lambda_parse(x) for x in spec["lambda_grid"])
    r_columns = (REGIME_COLUMN,) if regime is not None else ()
    payloads = [{
        "units": [units[t] for t in f.training], "raw": {t: raw[t] for t in f.training},
        "status": {t: status[t] for t in f.training}, "cutoff": f.cutoff_date, "features": features, "recipe": recipe,
        "grid": grid, "test_raw": raw[f.test_ticker], "test_status": status[f.test_ticker],
        "regime": {t: regime[t] for t in f.training} if regime is not None else None,
        "test_regime": regime[f.test_ticker] if regime is not None else None, "r_columns": r_columns,
    } for f in folds]
    if workers <= 1:
        parts = [_hazard_task_v1(p) for p in payloads]
    else:
        ctx = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
            parts = list(pool.map(_hazard_task_v1, payloads, chunksize=1))
    for f, part in zip(folds, parts):
        if (part.pop("n_ipo_check"), part.pop("n_pp_rows_check")) != (len(f.training), f.n_pp_rows):
            raise BacktestStop(f"{f.fold_id}: fit'in eğitim kümesi fold planıyla aynı değil")
    return parts


def _tufe_pit_check(folds: Sequence[CeilingFold], tufe_info: Mapping[str, Mapping[str, str]]) -> None:
    """§3.2 backtest: eğitim arzı j'nin ve test arzının TÜFE ayının yayımı fold'un kesiminden (T) önce (sızıntı yok)."""
    for f in folds:
        for t in (*f.training, f.test_ticker):
            if not tufe_info[t]["release_date"] < f.cutoff_date:
                raise BacktestStop(f"{f.fold_id}: {t} TÜFE {tufe_info[t]['month']} yayımı {tufe_info[t]['release_date']} ≥ T")


def v1_plan(model_id: str, dataset: Dataset, raw: Mapping[str, Mapping[str, Any]]) -> list[CeilingFold]:
    from .specs import FAZ7_MODEL_SPECS, PLAN_CEILING, PLAN_CEILING_POOLED

    plan_id = FAZ7_MODEL_SPECS[model_id]["plan_id"]
    if plan_id == PLAN_CEILING:
        return plan_ceiling_folds(dataset, PLAN_CEILING)
    if plan_id == PLAN_CEILING_POOLED:
        return plan_pooled_folds(dataset, raw)
    raise BacktestStop(f"{model_id}: bilinmeyen plan {plan_id}")


@dataclass
class V1Result:
    model_id: str
    spec_sha256: str
    folds: list[CeilingFold]
    ledger: list[dict[str, Any]]
    metrics: dict[str, Any]
    ledger_csv: bytes
    log_entry: dict[str, Any]
    comparators: dict[str, tuple[list[dict[str, Any]], bytes]]      # havuz planı KM kuralları: koşu anahtarı -> (ledger, csv)


def run_backtest_v1(model_id: str, *, log_path: Path, context: str, workers: Optional[int] = None,
                    dataset: Optional[Dataset] = None) -> V1Result:
    """Faz 7 adayının (ya da kural satırının) walk-forward backtest'i; sonunda günlüğe bir `kind: backtest` satırı (kural 4).
    Havuz planında KM kuralları aynı fold'ların aynı eğitim kümelerinden hesaplanır (keşif; ayrı ledger, sha'ları bu satırda)."""
    from .specs import FAZ7_MODEL_SPECS, PLAN_CEILING_POOLED, SPEC_DOCUMENTS_FAZ7

    spec = FAZ7_MODEL_SPECS[model_id]
    runtime = fitmod.verify_runtime()
    workers = default_workers() if workers is None else workers
    started = now_istanbul()
    dataset = dataset if dataset is not None else v1_dataset(model_id)
    pooled = spec["plan_id"] == PLAN_CEILING_POOLED
    rows = list(dataset.rows)
    raw, tufe_info = v1_raw_features(spec, rows) if spec["features"] else ({r.ticker: {} for r in rows}, {})
    if pooled and not spec["features"]:           # @INF: plan (f3 filtre dışlaması dahil) modelinkiyle aynı olsun
        raw_plan = v1_raw_features(FAZ7_MODEL_SPECS[spec["parent_model_id"]], rows)[0]
    else:
        raw_plan = raw
    regime = v1_regime(rows) if "regime" in spec else None
    folds = v1_plan(model_id, dataset, raw_plan)
    scorable = [f for f in folds if f.status == SCORABLE]
    if tufe_info:
        _tufe_pit_check(scorable, tufe_info)
    by = dataset.by_ticker()
    identities = [_v1_identity(f, by, pooled, tufe_info) for f in scorable]
    parts = _run_hazard_v1(spec, dataset, scorable, workers, raw, regime)
    ledger = [{"model_id": model_id, **ident, **part} for ident, part in zip(identities, parts)]
    payload = ledger_csv_bytes(ledger)
    metrics = compute_ceiling_metrics(ledger)
    v0_rows = read_pinned_ledger(FAZ7_COMPARATOR_LEDGERS["ceiling_hazard_v0"])
    near = near_era_cell(ledger, v0_rows)
    comparators: dict[str, tuple[list[dict[str, Any]], bytes]] = {}
    if pooled and spec["features"]:              # havuz planının KM kuralları bir kez, adayın koşusunda
        units = {r.ticker: sv.unit_of(r) for r in rows}
        for key, algorithm in POOLED_KM_RULES:
            km = [{"model_id": key.split("__")[0], **_v1_identity(f, by, True, {}), **_ceiling_rule_row(algorithm, f, units)}
                  for f in scorable]
            comparators[key] = (km, ledger_csv_bytes(km))
    doc, dec = SPEC_DOCUMENTS_FAZ7["SPEC_HAZARD_V1"], SPEC_DOCUMENTS_FAZ7["KARARLAR_FAZ7"]
    entry = {
        "kind": "backtest",
        "context": context,
        "model_id": model_id,
        "spec_sha256": spec_sha256(spec),
        "plan_id": spec["plan_id"],
        "data_version_sha256": dataset.data_version_sha256,
        "training_table_sha256": dataset.table_sha256,
        "folds_total": len(folds),
        "folds_scorable": {"CEILING": len(scorable)},
        "ledger_sha256": sha256_bytes(payload),
        "near_era": None if near is None else {k: near[k] for k in ("n", "n_months", "mean", "ci95", "model_better_n",
                                                                    "rule_better_n", "tie_n", "label")},
        "evaluated": [{"run_key": k, "ledger_sha256": v["sha256"]} for k, v in FAZ7_COMPARATOR_LEDGERS.items()],
        "metrics": metrics,
        "started_at": started,
        "finished_at": now_istanbul(),
        **code_version(),
        "spec_document": doc["path"],
        "spec_document_sha256": sha256_file(ROOT / doc["path"]),
        "decisions_document": dec["path"],
        "decisions_document_sha256": sha256_file(ROOT / dec["path"]),
        "runtime": runtime,
    }
    if "deflator" in spec:
        entry["tufe"] = {"file": spec["deflator"]["file"], "through_month": spec["deflator"]["through_month"],
                         "prefix_sha256": spec["deflator"]["file_sha256"]}
    if pooled:
        entry["filter_excluded_folds"] = sum(1 for f in scorable if f.filter_excluded)
    if comparators:
        entry["comparator_ledgers"] = {k: {"ledger_sha256": sha256_bytes(v[1]), "metrics": compute_ceiling_metrics(v[0])}
                                       for k, v in comparators.items()}
    append_log(log_path, entry)
    return V1Result(model_id, entry["spec_sha256"], folds, ledger, metrics, payload, entry, comparators)


# ---------------------------------------------------------------- nihai fit önizlemesi (models/'e yazılmaz; dondurma ayrı görev)

V1_FEATURE_DEFINITIONS = {
    "f1": "arz büyüklüğü TL (borsai.features; kaynakta bildirilen ipo_size_tl, yoksa fiyat × pay); eğitim [p05, p95]'ine ham TL'de "
          "kırpılır, sonra ln, z-skor",
    "f1r": "reel arz büyüklüğü, 2025 TL: f1 / (TÜFE[T'nin ayı − 2] / 100) (TÜİK TÜFE 2025=100; borsai.predict_hazard.real_size); "
           "eğitim [p05, p95]'ine kırpılır, sonra ln, z-skor",
    "f2": "shares_offered / post_ipo_share_capital × 100 (borsai.features); eğitim [p05, p95]'ine kırpılır, z-skor",
    "f3": "total_demand_multiple (borsai.features); eğitim [p05, p95]'ine kırpılır, z-skor; yoksa RET",
}


def final_fit_v1(model_id: str, dataset: Optional[Dataset] = None, *, spec: Optional[Mapping[str, Any]] = None) -> tuple[dict[str, Any], Any]:
    """(dondurulacak parametre sözlüğü, TrainingResult). `fit._fit_survival` kalıbı + v1 alanları (family, variant, winsor,
    deflator, regime, training.cohort_counts, spec_sha256). stdlib `predict_hazard.predict` ile çalışır (§11-11).
    `spec` yalnız sentetik testler içindir (eğitim n'i ve veri sürümü sentetik veriye göre)."""
    from . import hazard as hz
    from .specs import FAZ7_MODEL_SPECS, PLAN_CEILING_POOLED

    spec = FAZ7_MODEL_SPECS[model_id] if spec is None else spec
    dataset = dataset if dataset is not None else v1_dataset(model_id)
    pooled = spec["plan_id"] == PLAN_CEILING_POOLED
    rows = [r for r in dataset.rows if r.inputs["total_demand_multiple"] is not None]
    if len(rows) != spec["training"]["n"] or dataset.data_version_sha256 != spec["training"]["data_version_sha256"]:
        raise fitmod.FitError(f"{model_id}: eğitim n'i ya da veri sürümü şartnameyle tutmuyor")
    order = [(r.first_trading_date, r.ticker) for r in rows]
    if order != sorted(order):
        raise fitmod.FitError("eğitim satırları (first_trading_date, ticker) sırasında değil")
    features = tuple(spec["features"])
    raw_all, _ = v1_raw_features(spec, rows) if features else ({r.ticker: {} for r in rows}, {})
    status = {r.ticker: r.total_demand_filter_status for r in rows}
    regime = v1_regime(rows) if "regime" in spec else None
    r_columns = (REGIME_COLUMN,) if regime is not None else ()
    recipe = fitmod.recipe_for(spec) if features else None
    grid = tuple(hz.lambda_parse(x) for x in spec["lambda_grid"])
    res = hz.fit_training_set([sv.unit_of(r) for r in rows], raw_all, status, cutoff=None, features=features, recipe=recipe,
                              grid=grid, regime=regime, r_columns=r_columns)
    if res.status != hz.STATUS_FIT_OK:
        raise fitmod.FitError(f"{model_id}: nihai hazard fit'i {res.status}")
    used = [r for r in rows if r.ticker not in res.excluded]
    block = fitmod._survival_training_block(spec, used, dataset.data_version_sha256)
    block.update(n_pp_rows=res.n_pp_rows, n_events=res.n_events, n_survivals=res.n_survivals,
                 filter_excluded=list(res.excluded), table=spec["training"].get("table", "data/training_table.csv"))
    if pooled:
        block["cohort_counts"] = {c: sum(1 for r in used if r.cohort == c) for c in ("H99", "OOT_OPEN")}
    params = fitmod._envelope(spec, used, dataset.data_version_sha256, block)
    params["runtime"] = runtime_pins_checked()
    params["horizons"] = {h: {"return": None, "p_up": None} for h in HORIZONS}
    params.update({
        "family": spec["family"],
        "variant": spec["variant"],
        "day_groups": spec["day_groups"],
        "gamma": [float(g) for g in res.fit.gamma],
        "beta": res.beta_by_feature(),
        "columns": list(res.fit.columns),
        "lambda": hz.lambda_label(res.selected_lambda),
        "lambda_score_table": res.score_table,
        "reclose_rates": res.reclose,
        "pseudo_rows": {"weight": hz.PSEUDO_WEIGHT, "z": 0, "r": 0},
        "solver": {"iterations": res.fit.iterations, "grad_max": res.fit.grad_max},
        "preprocessing": res.prepared.prep.params() if res.prepared.prep is not None else None,
        "feature_definitions": {f: V1_FEATURE_DEFINITIONS[f] for f in features},
        "feature_ranges": fitmod.feature_ranges({t: raw_all[t] for t in (r.ticker for r in used)}, features) if features else {},
        "input_policy": dict(spec["input_policy"]),
    })
    if "deflator" in spec:
        params["deflator"] = dict(spec["deflator"])
    if regime is not None:
        params["regime"] = {**spec["regime"], "delta": res.delta_by_column()[REGIME_COLUMN]}
    return params, res


def runtime_pins_checked() -> dict[str, str]:
    return fitmod.verify_runtime()


FAZ7_GOLDEN_DESCRIPTION = ("Faz 7: tavan serisi v1 adaylarının (SPEC_HAZARD_V1) bu makinedeki walk-forward fold ledger'ları (clip ve real "
                           "PLAN_CEILING'de, pooled ve @INF PLAN_CEILING_POOLED'da), havuz planının KM kuralları (keşif) ve nihai fit "
                           "önizlemeleri. Regresyon testi bunlara karşı BİREBİR (bayt) çalışır; docs/MODELS.md Faz 7 bölümü bunlardan "
                           "üretilir. Modeller DONDURULMADI; önizlemeler models/'e yazılmadı.")


def final_preview_filename(model_id: str) -> str:
    return f"{model_id}_final_fit_preview.json"


def write_golden_faz7(results: Mapping[str, V1Result], previews: Mapping[str, Mapping[str, Any]],
                      out_dir: Path = GOLDEN_FAZ7_DIR) -> dict[str, Any]:
    """Altın ledger'lar + havuz KM ledger'ları + nihai fit önizlemeleri + MANIFEST + SHA256SUMS. Üzerine yazmaz."""
    from .provenance import pretty_json_bytes, runtime_versions

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}

    def put(name: str, payload: bytes) -> None:
        path = out_dir / name
        if path.exists():
            raise BacktestStop(f"{path} zaten var; altın referans üzerine yazılmaz")
        path.write_bytes(payload)
        files[name] = sha256_file(path)

    runs: dict[str, Any] = {}
    for model_id, res in results.items():
        put(golden_filename(model_id), res.ledger_csv)
        runs[model_id] = {"file": golden_filename(model_id), "model_id": model_id, "plan_id": res.log_entry["plan_id"],
                          "spec_sha256": res.spec_sha256, "ledger_sha256": files[golden_filename(model_id)],
                          "data_version_sha256": res.log_entry["data_version_sha256"],
                          "log_entry": {"context": res.log_entry["context"], "started_at": res.log_entry["started_at"]}}
        for key, (_, payload) in res.comparators.items():
            put(golden_filename(key), payload)
            runs[key] = {"file": golden_filename(key), "model_id": key.split("__")[0], "plan_id": res.log_entry["plan_id"],
                         "ledger_sha256": files[golden_filename(key)], "computed_in_run": model_id}
    previews_out = {}
    for model_id, params in previews.items():
        put(final_preview_filename(model_id), pretty_json_bytes(dict(params)))
        previews_out[model_id] = {"file": final_preview_filename(model_id), "sha256": files[final_preview_filename(model_id)]}
    manifest = {
        "description": FAZ7_GOLDEN_DESCRIPTION,
        "runs": runs,
        "comparator_ledgers": {k: dict(v) for k, v in FAZ7_COMPARATOR_LEDGERS.items()},
        "final_fit_previews": previews_out,
        "final_fit_note": "models/'e yazılmadı; dondurma görevi bit-eşitliği created_at, code_version ve runtime dışında sınar",
        "runtime": runtime_versions(),
        "machine": {"platform": _platform()},
        "created_at": now_istanbul(),
        **code_version(),
    }
    (out_dir / "MANIFEST.json").write_bytes(pretty_json_bytes(manifest))
    (out_dir / "SHA256SUMS").write_text("".join(f"{sha}  {name}\n" for name, sha in sorted(files.items())), encoding="utf-8")
    return manifest


def run_faz7(*, log_path: Path, context: str, workers: Optional[int] = None) -> dict[str, V1Result]:
    datasets: dict[str, Dataset] = {}
    out = {}
    for model_id in FAZ7_RUNS:
        key = "v2" if "pooled" in model_id else "h99"
        if key not in datasets:
            datasets[key] = v1_dataset(model_id)
        out[model_id] = run_backtest_v1(model_id, log_path=log_path, context=context, workers=workers, dataset=datasets[key])
    return out


# ============================================================================
# Faz 7C: düşen arz modeli v0 (SPEC_C_V0 §4, §5, §11; KARARLAR_C; SPEC_DEVIATIONS K)
# ============================================================================

GOLDEN_FAZ7C_DIR = ROOT / "tests" / "reference" / "macos_golden_faz7c"
NEAR_ERA_TOLERANCE_FALL = 0.008          # §5.1 δ (V1.5'in yakın dönemde base_rate'e karşı D10 Brier kazancının ≈ beşte biri)
FALL_PRIMARY_HORIZON = "D10"
V15_PUBLISHED_D10_BRIER = 0.1883         # MODELS.md (Faz 1A), 81 fold
# Karşılaştırıcılar: Faz 1A altın ledger'ları (PLAN_V15, 99 arz; yeniden koşulmaz; sha pinli, macos_golden/MANIFEST.json ile aynı).
FAZ7C_COMPARATOR_LEDGERS: dict[str, dict[str, str]] = {
    "base_rate": {"path": "tests/reference/macos_golden/base_rate_fold_ledger.csv",
                  "sha256": "898d2d849cc21a0461c88b816338c9d64d7b93b7d4ffafe726bfd3c56d5147e2"},
    "v1_5_h99": {"path": "tests/reference/macos_golden/v1_5_h99_fold_ledger.csv",
                 "sha256": "5c56da37bf7cece261fc5472ff0a2de8e242169755afc3aefb3c6c12b7fb049b"},
}
FAZ7C_EXPLORATION_CONTEXT = "faz7c_exploration_import"


def near_era_label_fall(ci: Optional[Sequence[float]]) -> str:
    """§5.1 karar kuralı (sonuçlar görülmeden, commit A): alt uç > 0 -> "bozuyor"; üst uç ≤ +0.008 -> "tolerans içinde"; diğer
    -> "belirsiz" (alt = 0 dışlamaz). Aralık üretilemediyse "belirsiz"."""
    if ci is None:
        return LABEL_UNCLEAR
    lo, hi = ci
    if lo > 0.0:
        return LABEL_BREAKS
    if hi <= NEAR_ERA_TOLERANCE_FALL:
        return LABEL_TOLERANCE
    return LABEL_UNCLEAR


def _p_up_of(row: Mapping[str, Any]) -> Optional[float]:
    """Ledger satırının p_up'ı: Logit satırında yalnız FIT_OK, kural satırında `rule_p_up` (Faz 1A ledger biçimi ya da bellek)."""
    if "logit_status" in row:
        return float(row["logit_probability"]) if row["logit_status"] == fitmod.STATUS_FIT_OK else None
    v = row.get("rule_p_up")
    return None if v in (None, "") else float(v)


def paired_p_up(model_rows: Sequence[Mapping[str, Any]], other_rows: Sequence[Mapping[str, Any]], *, horizon: str = FALL_PRIMARY_HORIZON,
                start: Optional[str] = None, end: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Eşleşik Brier farkı = model − karşılaştırılan (negatif = model iyi), p_up = P(kapanış > arz) ile, kırpmasız (SPEC_SCORING §7),
    `horizon` fold'larında, iki tarafın da p_up'ı olan arzlarda (ticker ile), [start, end) ilk işlem aralığında (PLAN_V15 ve
    PLAN_FALL_*'da prediction_date = T). %95 aralık SPEC_DEVIATIONS C7 (`metrics.paired_difference`); n < 10 ya da < 6 ay ise yok."""
    other = {}
    for r in other_rows:
        p = _p_up_of(r) if r["horizon"] == horizon else None
        if p is not None:
            other[r["ticker"]] = p
    diffs, months, a, b, tickers = [], [], [], [], []
    for r in model_rows:
        t = r["prediction_date"]
        p = _p_up_of(r) if r["horizon"] == horizon else None
        if p is None or (start is not None and t < start) or (end is not None and t >= end) or r["ticker"] not in other:
            continue
        y = int(r["realized_direction"])
        la, lb = (p - y) ** 2, (other[r["ticker"]] - y) ** 2
        diffs.append(la - lb)
        months.append(t[:7])
        a.append(la)
        b.append(lb)
        tickers.append(r["ticker"])
    if not diffs:
        return None
    if len(diffs) >= 10 and len(set(months)) >= 6:
        res = mx.paired_difference(diffs, months)
    else:
        res = {"n": len(diffs), "n_months": len(set(months)), "mean": sum(diffs) / len(diffs), "ci95": None,
               "model_better_n": sum(1 for d in diffs if d < 0), "rule_better_n": sum(1 for d in diffs if d > 0),
               "tie_n": sum(1 for d in diffs if d == 0), "verdict": None}
    res.update(metric="brier", horizon=horizon, model_metric=sum(a) / len(a), rule_metric=sum(b) / len(b), tickers=tickers,
               tie_n_1e12=sum(1 for d in diffs if abs(d) <= 1e-12))
    return res


def near_era_cell_fall(pooled_rows: Sequence[Mapping[str, Any]], h99_rows: Sequence[Mapping[str, Any]]) -> Optional[dict[str, Any]]:
    """§5.1 birincil hücre: `fall_d10_v0_pooled − fall_d10_v0_h99`, D10 Brier, ilk işlem ≥ 2024-01-01; etiket `near_era_label_fall`."""
    res = paired_p_up(pooled_rows, h99_rows, horizon=FALL_PRIMARY_HORIZON, start=NEAR_ERA_START)
    if res is not None:
        res["label"] = near_era_label_fall(res["ci95"])
    return res


def v15_d10_brier(v15_rows: Sequence[Mapping[str, Any]]) -> tuple[int, float]:
    """§11-7: V1.5'in D10 Brier'i (Logit FIT_OK fold'ları) ledger'dan; Faz 1A raporlama kırpması [0.01, 0.99] (`metrics.brier_term`;
    bu ledger'da hiçbir p kırpılmaz, kırpmasız değer aynı). (n, Brier)."""
    pts = [(float(r["logit_probability"]), int(r["realized_direction"])) for r in v15_rows
           if r["horizon"] == "D10" and r["logit_status"] == fitmod.STATUS_FIT_OK]
    return len(pts), sum(mx.brier_term(p, y) for p, y in pts) / len(pts)


def fall_dataset(model_id: str) -> Dataset:
    from .data import load_dataset_v2
    from .specs import FAZ7C_MODEL_SPECS, PLAN_FALL_H99

    return load_dataset() if FAZ7C_MODEL_SPECS[model_id]["plan_id"] == PLAN_FALL_H99 else load_dataset_v2()


def fall_raw_features(spec: Mapping[str, Any], rows: Sequence[IPORow], add_sale: Mapping[str, Optional[str]]
                      ) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    """(ham özellikler, TÜFE bilgisi). f1r ve f3 `features.compute_features` + `predict_hazard.real_size` (TÜFE `tufe.index_for(T)`,
    PIT bekçisi dahil; v2 satırında tablonun tufe_index'iyle eşitlik denetlenir; `ceiling_hazard_v1_real` ile aynı fonksiyonlar),
    add_sale `predict_fall.additional_sale_flag` — tahminle aynı fonksiyonlar (`predict_fall.feature_values_exact`)."""
    from . import tufe
    from .predict_fall import feature_values_exact

    feats = list(spec["features"])
    table = _tufe_checked(spec) if "f1r" in feats else None
    raw: dict[str, dict[str, Any]] = {}
    info: dict[str, dict[str, str]] = {}
    for r in rows:
        f1 = f3 = idx = None
        if "f1r" in feats or "f3" in feats:
            f = compute_features(**r.feature_inputs())
            f1, f3 = f.f1, f.f3
        if table is not None:
            t = tufe.index_for(r.first_trading_date, table)
            if getattr(r, "tufe_index", "") and (r.tufe_index, r.tufe_month) != (t["index"], t["month"]):
                raise BacktestStop(f"{r.ticker}: v2 tablosunun tufe_index/ay değeri tufe.index_for ile aynı değil")
            info[r.ticker] = {"month": t["month"], "index": t["index"], "release_date": t["release_date"]}
            idx = t["index"]
        raw[r.ticker] = feature_values_exact(f1, f3, idx, add_sale.get(r.ticker), feats) if feats else {}
    return raw, info


@dataclass(frozen=True)
class FallFold(Fold):
    """PLAN_FALL_* fold'u: PLAN_V15 alanları + havuz bilgisi ve f3 filtre dışlaması (bu fold'da kullanılmayan arzlar)."""

    n_oot_open: int = 0
    filter_excluded: tuple[str, ...] = ()


def plan_fall_folds(dataset: Dataset, set_rows: Sequence[IPORow], raw_plan: Mapping[str, Mapping[str, Any]],
                    uses_f3: bool) -> list[FallFold]:
    """SPEC_C_V0 §5.1: PLAN_V15 kuralı, D5 ve D10 için. Test arzları eğitim kümesinin H99 arzları (h99 ve pooled 94, addsale 95);
    aday eğitim arzları kümenin bütün satırları (havuzda açık küme dahil): satır ancak D_h seansı test arzının T'sinden KESİN önce;
    kendisi, aynı gün ve gelecek dışlanır (durur); f3'ü bu kümenin filtre moduyla boşalacak arzlar dışarıda (J10 kuralı, K);
    eğitim n ≥ 10 değilse fold skorlanmaz."""
    from .hazard import f3_filter_excluded

    by = dataset.by_ticker()
    ordered = [r.ticker for r in set_rows]
    status = {r.ticker: r.total_demand_filter_status for r in set_rows}
    cohort = {r.ticker: getattr(r, "cohort", "H99") or "H99" for r in set_rows}
    tests = [r.ticker for r in set_rows if cohort[r.ticker] == "H99"]
    folds: list[FallFold] = []
    for h in FALL_HORIZONS:
        for test in tests:
            pdate = by[test].first_trading_date
            cutoff = _cutoff(pdate)
            training = tuple(t for t in ordered if by[t].targets[h].session_date < pdate)
            for t in training:
                if t == test:
                    raise BacktestStop(f"kendi kendini eğitme: {t}/{h}")
                if by[t].first_trading_date == pdate:
                    raise BacktestStop(f"aynı gün sızıntısı: {t}->{test}/{h}")
                if by[t].targets[h].session_date > cutoff:
                    raise BacktestStop(f"gelecek sızıntısı: {t}->{test}/{h}")
            excluded = tuple(f3_filter_excluded(training, raw_plan, status)) if uses_f3 else ()
            if excluded:
                training = tuple(t for t in training if t not in set(excluded))
            folds.append(FallFold(
                horizon=h, test_ticker=test, prediction_date=pdate, prediction_cutoff_date=cutoff,
                target_session_date=by[test].targets[h].session_date, training=training,
                n_chronological=sum(1 for t in ordered if by[t].first_trading_date < pdate),
                status=SCORABLE if len(training) >= MIN_TRAIN_N else INSUFFICIENT,
                n_oot_open=sum(1 for t in training if cohort[t] != "H99"), filter_excluded=excluded,
            ))
    return folds


def _fall_task(payload: dict[str, Any]) -> dict[str, Any]:
    """Tek D_h fold'u (alt süreçte de çalışır): `fit.fit_fall_horizon` + test tahmini."""
    hf = fitmod.fit_fall_horizon(payload["order"], payload["raw"], payload["Y"], payload["status"], recipe=payload["recipe"],
                                 grid=payload["grid"], test_raw=payload["test_raw"], test_filter_status=payload["test_status"])
    g = hf.logit
    ok = g.status == fitmod.STATUS_FIT_OK
    intercept, coef = g.intercept_coef() if ok else (None, None)
    clipped = None
    if hf.test is not None:
        clipped = canonical_json([c for c, v in hf.test["winsorized"].items() if v])
    return {
        "n_used_check": len(hf.order),
        "logit_status": g.status,
        "logit_selected_C": fitmod.hp_label(g.selected_C, "C"),
        "logit_tuning_status": g.tuning_status,
        "logit_inner_fold_n": g.inner_fold_n,
        "logit_columns": canonical_json(list(g.columns)),
        "logit_score_table": _labeled_score_table(g.score_table, "C"),
        "logit_n_class_0": g.n_class_0,
        "logit_n_class_1": g.n_class_1,
        "logit_probability": g.probability,
        "logit_predicted_class": g.predicted_class,
        "logit_fit_warnings": canonical_json(list(g.observed_fit_warnings)),
        "logit_final_fit_attempts": canonical_json([list(a) for a in g.final_attempts]),
        "logit_intercept": intercept,
        "logit_coef": None if coef is None else canonical_json(dict(zip(g.columns, coef))),
        "test_clipped_features": clipped,
        "f3_filter_mode_ties_n": hf.stats.get("f3_filter_mode_ties_n", 0),
        "inner_filter_excluded_n": hf.stats.get("inner_filter_excluded_n", 0),
        "inner_held_out_not_scored_n": hf.stats.get("inner_held_out_not_scored_n", 0),
    }


def _run_fall(spec: Mapping[str, Any], dataset: Dataset, folds: Sequence[FallFold], workers: int,
              raw: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    by = dataset.by_ticker()
    grid = fitmod.fall_grid(spec)
    recipe = fitmod.recipe_for(spec) if spec["features"] else None
    status = {r.ticker: r.total_demand_filter_status for r in dataset.rows}
    payloads = [{
        "order": list(f.training), "raw": {t: raw[t] for t in f.training}, "Y": {t: by[t].targets[f.horizon].Y for t in f.training},
        "status": {t: status[t] for t in f.training}, "recipe": recipe, "grid": grid, "test_raw": raw[f.test_ticker],
        "test_status": status[f.test_ticker],
    } for f in folds]
    if workers <= 1:
        parts = [_fall_task(p) for p in payloads]
    else:
        ctx = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
            parts = list(pool.map(_fall_task, payloads, chunksize=2))
    for f, part in zip(folds, parts):
        if part.pop("n_used_check") != len(f.training):
            raise BacktestStop(f"{f.fold_id}: fit'in eğitim kümesi fold planıyla aynı değil (plan dışlaması eksik)")
    return parts


def _fall_identity(fold: FallFold, by: Mapping[str, IPORow], raw: Mapping[str, Mapping[str, Any]],
                   tufe_info: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    out = _fold_identity(fold, by)
    test = by[fold.test_ticker]
    out.update(
        first_trading_date=test.first_trading_date,
        realized_fall_event=1 - int(test.targets[fold.horizon].Y),
        training_n_oot_open=fold.n_oot_open,
        training_n_filter_excluded=len(fold.filter_excluded),
        training_filter_excluded_sha256=identity_hash(fold.filter_excluded) if fold.filter_excluded else "",
        test_f1r_raw=None if "f1r" not in raw[fold.test_ticker] else float(raw[fold.test_ticker]["f1r"]),
        test_f3=None if "f3" not in raw[fold.test_ticker] else float(raw[fold.test_ticker]["f3"]),
        test_add_sale=None if "add_sale" not in raw[fold.test_ticker] else int(raw[fold.test_ticker]["add_sale"]),
        test_tufe_month=tufe_info[fold.test_ticker]["month"] if tufe_info else None,
        test_tufe_index=tufe_info[fold.test_ticker]["index"] if tufe_info else None,
    )
    return out


def compute_fall_metrics(ledger: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Ufuk başına (D5, D10): Logit FIT_OK fold'larında Brier (p_up, kırpmasız; SPEC_SCORING §7), log-kayıp (p ∈ [1e-6, 1 − 1e-6]),
    ortalama p_up, gözlenen yukarı oranı ve olay (y = 1 − Y_h) sayısı. Karşılaştırma değil; bağlam."""
    import math

    out: dict[str, Any] = {}
    for h in FALL_HORIZONS:
        rows = [r for r in ledger if r["horizon"] == h and _p_up_of(r) is not None]
        if not rows:
            out[h] = {"folds": sum(1 for r in ledger if r["horizon"] == h), "n": 0}
            continue
        ps = [_p_up_of(r) for r in rows]
        ys = [int(r["realized_direction"]) for r in rows]
        clip = [min(max(p, 1e-6), 1 - 1e-6) for p in ps]
        out[h] = {"folds": sum(1 for r in ledger if r["horizon"] == h), "n": len(rows),
                  "brier": sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(rows),
                  "log_loss": -sum(y * math.log(q) + (1 - y) * math.log(1 - q) for q, y in zip(clip, ys)) / len(rows),
                  "mean_p_up": sum(ps) / len(ps), "observed_up_rate": sum(ys) / len(ys), "events": len(ys) - sum(ys)}
    return out


@dataclass
class FallResult:
    model_id: str
    spec_sha256: str
    folds: list[FallFold]
    ledger: list[dict[str, Any]]
    metrics: dict[str, Any]
    ledger_csv: bytes
    log_entry: dict[str, Any]


def fall_training_rows(spec: Mapping[str, Any], dataset: Dataset, add_sale: Mapping[str, Optional[str]], *, check: bool) -> list[IPORow]:
    """Şartnamenin eğitim kümesi (`data.select_fall_training_rows`); `check` ise n, olay sayıları ve kohort sayıları şartnameyle aynı."""
    from .data import select_fall_training_rows

    rows = select_fall_training_rows(dataset, spec["training"]["set"], add_sale)
    if check:
        tr = spec["training"]
        cohorts = {c: sum(1 for r in rows if (getattr(r, "cohort", "H99") or "H99") == c) for c in ("H99", "OOT_OPEN")}
        got = (len(rows), sum(1 for r in rows if r.targets["D5"].Y == 0), sum(1 for r in rows if r.targets["D10"].Y == 0), cohorts)
        if got != (tr["n"], tr["events_D5"], tr["events_D10"], tr["cohort_counts"]) or dataset.data_version_sha256 != tr["data_version_sha256"]:
            raise BacktestStop(f"{spec['model_id']}: eğitim kümesi şartnameyle tutmuyor {got}")
    return rows


def run_backtest_fall(model_id: str, *, log_path: Path, context: str, workers: Optional[int] = None, dataset: Optional[Dataset] = None,
                      add_sale: Optional[Mapping[str, Optional[str]]] = None, spec: Optional[Mapping[str, Any]] = None,
                      h99_ledger: Optional[Sequence[Mapping[str, Any]]] = None) -> FallResult:
    """Faz 7C adayının (ya da `@ZERO` kural satırının) walk-forward backtest'i; sonunda günlüğe bir `kind: backtest` satırı (kural 4).
    `h99_ledger` verilirse (havuz koşusu) satır birincil yakın dönem hücresini (`pooled − h99`) taşır. `spec` ve `add_sale` yalnız
    sentetik testler içindir (gerçek koşuda şartname ve tablonun ek satış sütunu)."""
    from .data import additional_sale_shares
    from .specs import FAZ7C_MODEL_SPECS, SPEC_DOCUMENTS_FAZ7C

    official = spec is None
    spec = FAZ7C_MODEL_SPECS[model_id] if spec is None else spec
    runtime = fitmod.verify_runtime()
    workers = default_workers() if workers is None else workers
    started = now_istanbul()
    dataset = dataset if dataset is not None else fall_dataset(model_id)
    add_sale = add_sale if add_sale is not None else additional_sale_shares(dataset)
    rows = fall_training_rows(spec, dataset, add_sale, check=official)
    plan_spec = FAZ7C_MODEL_SPECS[spec["parent_model_id"]] if "parent_model_id" in spec else spec
    raw, tufe_info = fall_raw_features(spec, rows, add_sale)
    raw_plan = fall_raw_features(plan_spec, rows, add_sale)[0] if plan_spec is not spec else raw
    folds = plan_fall_folds(dataset, rows, raw_plan, uses_f3="f3" in plan_spec["features"])
    scorable = [f for f in folds if f.status == SCORABLE]
    for f in scorable:
        for t in (*f.training, f.test_ticker) if tufe_info else ():
            if not tufe_info[t]["release_date"] < f.prediction_date:
                raise BacktestStop(f"{f.fold_id}: {t} TÜFE {tufe_info[t]['month']} yayımı {tufe_info[t]['release_date']} ≥ T")
    by = dataset.by_ticker()
    identities = [_fall_identity(f, by, raw, tufe_info) for f in scorable]
    parts = _run_fall(spec, dataset, scorable, workers, raw)
    ledger = [{"model_id": model_id, **ident, **part} for ident, part in zip(identities, parts)]
    payload = ledger_csv_bytes(ledger)
    metrics = compute_fall_metrics(ledger)
    cmp = {k: read_pinned_ledger(v) for k, v in FAZ7C_COMPARATOR_LEDGERS.items()}
    secondary = {f"{c}|{h}": paired_p_up(ledger, cmp[c], horizon=h, start=NEAR_ERA_START) for c in cmp for h in FALL_HORIZONS}
    near = near_era_cell_fall(ledger, h99_ledger) if h99_ledger is not None else None
    keep = ("n", "n_months", "mean", "ci95", "model_better_n", "rule_better_n", "tie_n")
    doc, dec = SPEC_DOCUMENTS_FAZ7C["SPEC_C_V0"], SPEC_DOCUMENTS_FAZ7C["KARARLAR_C"]
    entry = {
        "kind": "backtest",
        "context": context,
        "model_id": model_id,
        "spec_sha256": spec_sha256(dict(spec)),
        "plan_id": spec["plan_id"],
        "data_version_sha256": dataset.data_version_sha256,
        "training_table_sha256": dataset.table_sha256,
        "folds_total": len(folds),
        "folds_scorable": {h: sum(1 for f in scorable if f.horizon == h) for h in FALL_HORIZONS},
        "ledger_sha256": sha256_bytes(payload),
        "near_era": None if near is None else {**{k: near[k] for k in keep}, "label": near["label"],
                                               "cell": "fall_d10_v0_pooled − fall_d10_v0_h99, D10 Brier, ilk işlem ≥ 2024-01-01"},
        "near_era_secondary": {k: None if v is None else {kk: v[kk] for kk in keep} for k, v in secondary.items()},
        "evaluated": [{"run_key": k, "ledger_sha256": v["sha256"]} for k, v in FAZ7C_COMPARATOR_LEDGERS.items()],
        "filter_excluded_folds": sum(1 for f in scorable if f.filter_excluded),
        "metrics": metrics,
        "started_at": started,
        "finished_at": now_istanbul(),
        **code_version(),
        "spec_document": doc["path"],
        "spec_document_sha256": sha256_file(ROOT / doc["path"]),
        "decisions_document": dec["path"],
        "decisions_document_sha256": sha256_file(ROOT / dec["path"]),
        "runtime": runtime,
    }
    if "deflator" in spec:
        entry["tufe"] = {"file": spec["deflator"]["file"], "through_month": spec["deflator"]["through_month"],
                         "prefix_sha256": spec["deflator"]["file_sha256"]}
    append_log(log_path, entry)
    return FallResult(model_id, entry["spec_sha256"], folds, ledger, metrics, payload, entry)


FALL_FEATURE_DEFINITIONS = {
    "f1r": "reel arz büyüklüğü, 2025 TL: f1 / (TÜFE[T'nin ayı − 2] / 100) (TÜİK TÜFE 2025=100; borsai.predict_hazard.real_size; "
           "ceiling_hazard_v1_real ile tek tanım); eğitim [p05, p95]'ine ham değerde kırpılır, sonra ln, z-skor",
    "f3": "total_demand_multiple (borsai.features); eğitim [p05, p95]'ine kırpılır, sonra ln, z-skor; yoksa RET",
    "add_sale": "1[additional_sale_shares > 0] (borsai.predict_fall.additional_sale_flag); z-skor; alan boşsa RET (0 varsayılmaz)",
}


def final_fit_fall(model_id: str, dataset: Optional[Dataset] = None, *, spec: Optional[Mapping[str, Any]] = None,
                   add_sale: Optional[Mapping[str, Optional[str]]] = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """(dondurulacak parametre sözlüğü, ufuk -> FallHorizonFit). Bütün eğitim kümesinde D5 ve D10 başlıkları (`fit.fit_fall_horizon`);
    JSON alanları SPEC_C_V0 §2.3. stdlib `predict_fall.predict` ile çalışır (§11-9). `spec`/`add_sale` yalnız sentetik testler içindir."""
    from .data import additional_sale_shares
    from .specs import FAZ7C_MODEL_SPECS

    official = spec is None
    spec = FAZ7C_MODEL_SPECS[model_id] if spec is None else spec
    dataset = dataset if dataset is not None else fall_dataset(model_id)
    add_sale = add_sale if add_sale is not None else additional_sale_shares(dataset)
    rows = fall_training_rows(spec, dataset, add_sale, check=official)
    if len(rows) != spec["training"]["n"] or dataset.data_version_sha256 != spec["training"]["data_version_sha256"]:
        raise fitmod.FitError(f"{model_id}: eğitim n'i ya da veri sürümü şartnameyle tutmuyor")
    features = list(spec["features"])
    raw, _ = fall_raw_features(spec, rows, add_sale)
    status = {r.ticker: r.total_demand_filter_status for r in rows}
    grid = fitmod.fall_grid(spec)
    recipe = fitmod.recipe_for(spec) if features else None
    fits = {}
    prep = None
    for h in FALL_HORIZONS:
        hf = fitmod.fit_fall_horizon([r.ticker for r in rows], raw, {r.ticker: r.targets[h].Y for r in rows}, status,
                                     recipe=recipe, grid=grid)
        if hf.logit.status != fitmod.STATUS_FIT_OK:
            raise fitmod.FitError(f"{model_id} {h}: nihai fit {hf.logit.status}")
        this = hf.final.params() if hf.final is not None else None
        if h != FALL_HORIZONS[0] and (this != prep or hf.order != fits[FALL_HORIZONS[0]].order):
            raise fitmod.FitError(f"{model_id} {h}: ön işleme ya da eğitim kümesi ufuklar arasında farklı")
        prep = this
        fits[h] = hf
    used_set = set(fits[FALL_PRIMARY_HORIZON].order)
    used = [r for r in rows if r.ticker in used_set]
    block = fitmod._training_block(spec, used, dataset.data_version_sha256)
    block.update(table=spec["training"]["table"],
                 cohort_counts={c: sum(1 for r in used if (getattr(r, "cohort", "H99") or "H99") == c) for c in ("H99", "OOT_OPEN")},
                 events_D5=sum(1 for r in used if r.targets["D5"].Y == 0), events_D10=sum(1 for r in used if r.targets["D10"].Y == 0),
                 event_definition=spec["target_definition"], filter_excluded=list(fits[FALL_PRIMARY_HORIZON].excluded))
    params = fitmod._envelope(spec, used, dataset.data_version_sha256, block)
    params["runtime"] = fitmod.verify_runtime()
    params.update({
        "family": spec["family"],
        "variant": spec["variant"],
        "target_definition": spec["target_definition"],
        "horizons": {h: fitmod.fall_head(fits[h]) for h in FALL_HORIZONS},
        "preprocessing": prep,
        "feature_definitions": {f: FALL_FEATURE_DEFINITIONS[f] for f in features},
        "feature_ranges": fitmod.feature_ranges({t: raw[t] for t in (r.ticker for r in used)}, features) if features else {},
        "input_policy": dict(spec["input_policy"]),
    })
    if "deflator" in spec:
        params["deflator"] = dict(spec["deflator"])
    return params, fits


FAZ7C_GOLDEN_DESCRIPTION = ("Faz 7C: düşen arz modeli v0 adaylarının (SPEC_C_V0) bu makinedeki walk-forward fold ledger'ları (h99 "
                            "PLAN_FALL_H99'da, pooled ve @ZERO PLAN_FALL_POOLED'da, addsale PLAN_FALL_ADDSALE'de; D5 ve D10) ve nihai "
                            "fit önizlemeleri. Regresyon testi bunlara karşı BİREBİR (bayt) çalışır; docs/MODELS.md Faz 7C bölümü "
                            "bunlardan üretilir. Modeller DONDURULMADI; önizlemeler models/'e yazılmadı.")


def write_golden_faz7c(results: Mapping[str, FallResult], previews: Mapping[str, Mapping[str, Any]],
                       out_dir: Path = GOLDEN_FAZ7C_DIR) -> dict[str, Any]:
    """Altın ledger'lar + nihai fit önizlemeleri + MANIFEST + SHA256SUMS. Üzerine yazmaz."""
    from .provenance import pretty_json_bytes, runtime_versions

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}

    def put(name: str, payload: bytes) -> None:
        path = out_dir / name
        if path.exists():
            raise BacktestStop(f"{path} zaten var; altın referans üzerine yazılmaz")
        path.write_bytes(payload)
        files[name] = sha256_file(path)

    runs: dict[str, Any] = {}
    for model_id, res in results.items():
        put(golden_filename(model_id), res.ledger_csv)
        runs[model_id] = {"file": golden_filename(model_id), "model_id": model_id, "plan_id": res.log_entry["plan_id"],
                          "spec_sha256": res.spec_sha256, "ledger_sha256": files[golden_filename(model_id)],
                          "data_version_sha256": res.log_entry["data_version_sha256"],
                          "log_entry": {"context": res.log_entry["context"], "started_at": res.log_entry["started_at"]}}
    previews_out = {}
    for model_id, params in previews.items():
        put(final_preview_filename(model_id), pretty_json_bytes(dict(params)))
        previews_out[model_id] = {"file": final_preview_filename(model_id), "sha256": files[final_preview_filename(model_id)]}
    manifest = {
        "description": FAZ7C_GOLDEN_DESCRIPTION,
        "runs": runs,
        "comparator_ledgers": {k: dict(v) for k, v in FAZ7C_COMPARATOR_LEDGERS.items()},
        "final_fit_previews": previews_out,
        "final_fit_note": "models/'e yazılmadı; dondurma görevi bit-eşitliği created_at, code_version ve runtime dışında sınar",
        "runtime": runtime_versions(),
        "machine": {"platform": _platform()},
        "created_at": now_istanbul(),
        **code_version(),
    }
    (out_dir / "MANIFEST.json").write_bytes(pretty_json_bytes(manifest))
    (out_dir / "SHA256SUMS").write_text("".join(f"{sha}  {name}\n" for name, sha in sorted(files.items())), encoding="utf-8")
    return manifest


def run_faz7c(*, log_path: Path, context: str, workers: Optional[int] = None) -> dict[str, FallResult]:
    """Dört koşu şartname sırasıyla (h99, pooled, addsale, @ZERO); havuz koşusunun satırı birincil hücreyi taşır."""
    from .specs import FAZ7C_MODEL_IDS

    datasets: dict[str, Dataset] = {}
    out: dict[str, FallResult] = {}
    for model_id in FAZ7C_MODEL_IDS:
        key = "h99" if model_id == "fall_d10_v0_h99" else "v2"
        if key not in datasets:
            datasets[key] = fall_dataset(model_id)
        h99 = out["fall_d10_v0_h99"].ledger if model_id == "fall_d10_v0_pooled" else None
        out[model_id] = run_backtest_fall(model_id, log_path=log_path, context=context, workers=workers, dataset=datasets[key],
                                          h99_ledger=h99)
    return out


# ---------------------------------------------------------------- keşif varyantları (SPEC_C_V0 §8; KARARLAR_C "Çokluk")

def exploration_entries(context: str = FAZ7C_EXPLORATION_CONTEXT, *, recorded_at: Optional[str] = None) -> list[dict[str, Any]]:
    """`docs/specs_faz7_c/ekler/denenenler.csv`'nin her satırı bir `kind: exploration` günlük satırı (özet satır değil). Satır
    alanları CSV'deki gibi metin (`variant`); dosya yolu ve sha256'sı her satırda. MODEL DEĞİLDİR: dondurulmaz, INDEX'e girmez;
    kart varyant sayacı (`scoring._n_variants_same_data`) bu satırları `data_version_sha256`'larının veri sürümünde sayar
    (keşif training_table_v2 üzerinde yapıldı: v2 veri sürümü; SPEC_DEVIATIONS K)."""
    from .specs import FAZ7C_EXPLORATION, SPEC_DOCUMENTS_FAZ7C

    src = ROOT / FAZ7C_EXPLORATION["path"]
    raw = src.read_bytes()
    if sha256_bytes(raw) != FAZ7C_EXPLORATION["sha256"]:
        raise BacktestStop(f"{FAZ7C_EXPLORATION['path']}: sha256 {sha256_bytes(raw)} != pin {FAZ7C_EXPLORATION['sha256']}")
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))
    if len(rows) != FAZ7C_EXPLORATION["n"] or len({r["id"] for r in rows}) != len(rows):
        raise BacktestStop(f"keşif dosyası {len(rows)} satır; beklenen {FAZ7C_EXPLORATION['n']} tekil id")
    at = recorded_at or now_istanbul()
    doc = SPEC_DOCUMENTS_FAZ7C["SPEC_C_V0"]
    return [{
        "kind": "exploration",
        "context": context,
        "model_id": None,
        "family": "fall_d10_v0",
        "variant_id": f"{FAZ7C_EXPLORATION['path']}#{r['id']}",
        "variant": dict(r),
        "source": FAZ7C_EXPLORATION["path"],
        "source_sha256": FAZ7C_EXPLORATION["sha256"],
        "source_commit": FAZ7C_EXPLORATION["source_commit"],
        "data_version_sha256": FAZ7C_EXPLORATION["data_version_sha256"],
        "spec_document": doc["path"],
        "spec_document_sha256": doc["sha256"],
        "note": "keşif varyantı (SPEC_C_V0 §10; sonuçlar görüldükten sonra, H99 + açık küme); model değil; dondurulmaz",
        "recorded_at": at,
    } for r in rows]


def import_exploration(log_path: Path, context: str = FAZ7C_EXPLORATION_CONTEXT) -> int:
    """Keşif satırlarını günlüğe ekler (yalnız ekleme). Aynı dosyanın satırları günlükte zaten varsa durur (tekrar içe aktarma yok)."""
    from .specs import FAZ7C_EXPLORATION

    log_path = Path(log_path)
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("source_sha256") == FAZ7C_EXPLORATION["sha256"]:
                raise BacktestStop("keşif satırları günlükte zaten var; ikinci kez eklenmez")
    entries = exploration_entries(context)
    for e in entries:
        append_log(log_path, e)
    return len(entries)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="H99 walk-forward backtest; her koşu experiments/log.jsonl'a yazılır.")
    parser.add_argument("--models", nargs="*", default=None, choices=list(MODEL_SPECS),
                        help="modeller kendi planlarında (varsayılan: Faz 1A modelleri)")
    parser.add_argument("--suite", choices=["faz1b", "faz4", "faz7", "faz7c"], default=None,
                        help="faz1b: FAZ1B_RUNS (yeni modeller + planlarındaki kurallar); faz4: FAZ4_RUNS (tavan yolu modelleri); "
                             "faz7: FAZ7_RUNS (tavan serisi v1 adayları + @INF; --write-golden ile nihai fit önizlemeleri); "
                             "faz7c: düşen arz v0 adayları + @ZERO (--write-golden ile nihai fit önizlemeleri)")
    parser.add_argument("--import-exploration", action="store_true",
                        help="Faz 7C keşif varyantlarını (docs/specs_faz7_c/ekler/denenenler.csv, 2 054 satır) günlüğe "
                             "`kind: exploration` satırları olarak ekler (bir kez)")
    parser.add_argument("--conditional-eval", action="store_true",
                        help="SPEC_CEILING_PATH_V0 §7 koşullu keşif: Faz 1B altın tavan ledger'larından; günlüğe conditional_eval satırı")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--context", default="official")
    parser.add_argument("--write-golden", action="store_true",
                        help="altın ledger yaz: Faz 1A modelleri -> macos_golden/, --suite faz1b -> macos_golden_faz1b/, "
                             "--suite faz4 -> macos_golden_faz4/")
    args = parser.parse_args(argv)
    if args.import_exploration:
        print(json.dumps({"exploration_lines": import_exploration(DEFAULT_LOG_PATH)}, ensure_ascii=False))
        return 0
    if args.suite == "faz7c":
        from .specs import FAZ7C_MODEL_IDS

        results7c = run_faz7c(log_path=DEFAULT_LOG_PATH, context=args.context, workers=args.workers)
        for key, r in results7c.items():
            print(json.dumps({"run": key, "ledger_sha256": r.log_entry["ledger_sha256"], "folds": r.log_entry["folds_scorable"],
                              "near_era": r.log_entry["near_era"]}, ensure_ascii=False))
        if args.write_golden:
            previews = {m: final_fit_fall(m)[0] for m in FAZ7C_MODEL_IDS}
            print(json.dumps(write_golden_faz7c(results7c, previews), ensure_ascii=False, indent=2))
        return 0
    if args.suite == "faz7":
        results7 = run_faz7(log_path=DEFAULT_LOG_PATH, context=args.context, workers=args.workers)
        for key, r in results7.items():
            print(json.dumps({"run": key, "ledger_sha256": r.log_entry["ledger_sha256"], "folds": r.log_entry["folds_scorable"],
                              "near_era": r.log_entry["near_era"]}, ensure_ascii=False))
        if args.write_golden:
            previews = {m: final_fit_v1(m)[0] for m in FAZ7_RUNS}
            print(json.dumps(write_golden_faz7(results7, previews), ensure_ascii=False, indent=2))
        return 0
    dataset = load_dataset()
    if args.conditional_eval:
        from . import ceiling_path as cp
        from .report_faz1b import load_runs
        from .specs import SPEC_DOCUMENTS_FAZ4

        manifest = json.loads((GOLDEN_FAZ1B_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
        entry = cp.run_conditional_eval(load_runs(), manifest, log_path=DEFAULT_LOG_PATH, context=args.context,
                                        spec_document=SPEC_DOCUMENTS_FAZ4["SPEC_CEILING_PATH_V0"],
                                        data_version_sha256=dataset.data_version_sha256)
        print(json.dumps({"kind": entry["kind"], "context": entry["context"]}, ensure_ascii=False))
        return 0
    if args.suite == "faz1b":
        results = run_suite(FAZ1B_RUNS, dataset, log_path=DEFAULT_LOG_PATH, context=args.context, workers=args.workers)
    elif args.suite == "faz4":
        results = run_suite(FAZ4_RUNS, dataset, log_path=DEFAULT_LOG_PATH, context=args.context, workers=args.workers)
    else:
        models = args.models if args.models is not None else list(FAZ1A_MODEL_IDS)
        results = {m: run_backtest(m, dataset, log_path=DEFAULT_LOG_PATH, context=args.context, workers=args.workers)
                   for m in models}
    for key, r in results.items():
        print(json.dumps({"run": key, "ledger_sha256": r.log_entry["ledger_sha256"], "folds": r.log_entry["folds_scorable"]},
                         ensure_ascii=False))
    if args.write_golden:
        if args.suite == "faz1b":
            print(json.dumps(write_golden_runs(results), ensure_ascii=False, indent=2))
        elif args.suite == "faz4":
            print(json.dumps(write_golden_runs(results, GOLDEN_FAZ4_DIR, FAZ4_GOLDEN_DESCRIPTION), ensure_ascii=False, indent=2))
        else:
            if set(results) != set(FAZ1A_MODEL_IDS):
                raise BacktestStop("Faz 1A altın referansı tüm Faz 1A modelleriyle üretilir")
            print(json.dumps(write_golden(results), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

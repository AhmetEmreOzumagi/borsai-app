"""D1 sonrası güncelleme modeli `post_d1_hazard_v0`: D1 verisi, fit (numpy), walk-forward backtest ve nihai fit
önizlemesi (SPEC_POST_D1_V0 §2, §3, §6, §12). Tahmin matematiği borsai/predict_post_d1.py'dedir (yalnız stdlib); bu
modül aynı fonksiyonları çağırır (`evaluate_d1`, `updated_hazards`, `curves`, `path_conditional`), ikinci tanım yoktur.

- D1 alanları: SESSIONS dosyasından sütun beyaz listesiyle (`load_d1_sessions`): yalnız `session_number == 1` satırlarının
  fiyat/hacim sütunları; 2..10. seanslardan yalnız `target_session_date`. `half_day` = `session_type == OPEN_HALF_DAY`,
  `halt_flag` = `security_trading_status != ACTIVE_NOT_SUSPENDED` (başka kod durur: UNKNOWN_OFFICIAL_CODE).
- D1 ön işlemesi (`fit_d1_prep`): arz düzeyinde; d1_turnover için Type-7 [p05, p95] kırpma; z-skor popülasyon std'si;
  σ = 0 olan kolon düşer (katsayı 0). Kantil/ortalama/varyans kesin Fraction, std ve z 60 haneli Decimal (f3 ile aynı).
- δ fit'i (`fit_delta`): J(δ) = −Σ_r [e ln h + (1 − e) ln(1 − h)] + (λ/2)‖δ‖², h = sigmoid(η^base + δ·u); tam Newton,
  δ0 = 0, max|∇| ≤ 1e-10, ≤ 100 yineleme, ≤ 30 yarılama, SPEC_DEVIATIONS A2 kabul kuralı; pseudo-satır yok. λ = INF:
  δ ≡ 0. λ seçimi (`select_lambda`): iç arz-bırak CV; j'nin bütün d ≥ 2 satırları dışarıda, D1 ön işlemesi kalanlardan,
  ofset değişmez; satır başına log-kayıp, h [1e-12, 1 − 1e-12]; eşitlikte en büyük λ; yakınsamayan aday çıkar, INF kalır.
- Walk-forward (§6, `backtest_ledger`): fold kümesi ve sırası Faz 1B tavan ledger'ınınki (87); L_k = 0 → NOT_APPLICABLE;
  ofset o fold'un kendi `ceiling_hazard_v0` fit'i (`hazard.fit_training_set` yeniden, deterministik; γ, β, λ ve test
  hazard'ları ledger'la |Δ| ≤ 1e-9 olmazsa durur); δ eğitim kümesi PLAN_CEILING satırlarından d ≥ 2 olanlar; ≥ 10 arz,
  ≥ 5 olay, ≥ 5 sağ kalım. `path_conditional` yalnız Faz 4 `ceiling_path_v0` fold'u OK ise, o fold'un hücreleriyle.
- Nihai fit (`fit_params`): f3 dolu ve D1 tavan kapatan 81 arz; ofset dondurulmuş models/ceiling_hazard_v0.json'dan
  `predict_hazard.linear_predictor` ile (sha256 INDEX.json'la denetlenir). models/'e YAZMAZ (dondurma ayrı görevdir,
  borsai/freeze.py `freeze_post_d1`).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np

from . import hazard as hz
from . import predict_hazard as ph
from . import predict_path as pth
from . import predict_post_d1 as pd1
from . import preprocess as pp
from . import survival as sv
from .data import SESSIONS_PATH, VERSION_PATH, DataIntegrityError, Dataset, IPORow
from .provenance import (ROOT, canonical_json, canonical_sha256, code_version, identity_hash, now_istanbul, pretty_json_bytes,
                         sha256_bytes, sha256_file)
from .specs import (MODEL_SPECS, PLAN_CEILING, PLAN_POST_D1, POST_D1_MODEL_SPECS, SCHEMA_VERSION, SPEC_DOCUMENTS_FAZ5,
                    spec_sha256)

MODEL_ID = "post_d1_hazard_v0"
SPEC = POST_D1_MODEL_SPECS[MODEL_ID]
PARENT_SPEC = MODEL_SPECS[SPEC["parent"]["model_id"]]
GOLDEN_FAZ5_DIR = ROOT / "tests" / "reference" / "macos_golden_faz5"
DEFAULT_LOG_PATH = ROOT / "experiments" / "log.jsonl"
MODELS_DIR = ROOT / "models"
OUTCOME_CUTOFF = "2026-08-19"
D1_COLUMNS = pd1.D1_COLUMNS
LAMBDA_GRID = tuple(hz.lambda_parse(x) for x in SPEC["lambda_grid"])
if LAMBDA_GRID != hz.LAMBDA_GRID:
    raise AssertionError("λ ızgarası SPEC_CEILING_V0 ile aynı değil")
MIN_IPO, MIN_EVENTS, MIN_SURVIVALS = (SPEC["scorability"][k] for k in ("min_ipo", "min_events", "min_survivals"))
PATH_HORIZONS = (3, 5, 10)
PARITY_TOL = 1e-9

STATUS_FIT_OK = "FIT_OK"
STATUS_INSUFFICIENT = "INSUFFICIENT_TRAINING_HISTORY"
STATUS_SURVIVAL_NOT_AVAILABLE = "SURVIVAL_NOT_AVAILABLE"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
STATUS_NOT_CONVERGED = "MODEL_NOT_FIT_DID_NOT_CONVERGE"
FOLD_STATUSES = (STATUS_FIT_OK, STATUS_INSUFFICIENT, STATUS_SURVIVAL_NOT_AVAILABLE, STATUS_NOT_APPLICABLE, STATUS_NOT_CONVERGED)
PATH_OK = "OK"
PATH_NOT_PRODUCED = "NOT_PRODUCED"

# ---- SESSIONS sütun beyaz listesi (§6.1-7 (i))
SESSION_KEY_COLUMNS: tuple[str, ...] = ("ticker", "session_number")
ALL_SESSION_COLUMNS: tuple[str, ...] = ("target_session_date",)
SESSION_1_FIELDS: dict[str, str] = {"open": "thb_raw_open", "high": "thb_raw_high", "low": "thb_raw_low",
                                    "close": "thb_raw_close", "volume": "thb_raw_volume",
                                    "trade_count": "thb_raw_trade_count", "upper_limit": "thm_raw_upper_limit"}
SESSION_1_STATUS_COLUMNS: tuple[str, ...] = ("session_type", "security_trading_status")
HALF_DAY_OF = {"OPEN_FULL_DAY": 0, "OPEN_HALF_DAY": 1}
HALT_OF = {"ACTIVE_NOT_SUSPENDED": 0}
UNKNOWN_OFFICIAL_CODE = "UNKNOWN_OFFICIAL_CODE"

_CTX = pp._model_ctx()


class PostD1Error(RuntimeError):
    pass


# ============================================================ D1 verisi

@dataclass(frozen=True)
class D1Row:
    """D_1 satırı: ham metin alanları ve seans durumu (SESSIONS, `session_number == 1`)."""

    ticker: str
    session_date: str
    fields_raw: dict[str, str]
    half_day: int
    halt_flag: int
    session_type: str
    trading_status: str

    def block(self) -> dict[str, Any]:
        """predict_post_d1'in `d1` girdisi (kayıt şemasının d1 bloğunun alt kümesi)."""
        return {"session_date": self.session_date, "session_h": 1, "fields_raw": dict(self.fields_raw),
                "half_day": self.half_day, "halt_flag": self.halt_flag}


def load_d1_sessions(path: Path = SESSIONS_PATH) -> tuple[dict[str, D1Row], dict[str, dict[int, str]]]:
    """(ticker -> D_1 satırı, ticker -> {seans no: tarih}). Sütun beyaz listesi: her satırda yalnız anahtar sütunlar ve
    `target_session_date`; yalnız 1. seansta SESSION_1_FIELDS ve iki durum sütunu okunur. sha256 data_version.json'la."""
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    pinned = {s["path"]: s["sha256"] for s in json.loads(VERSION_PATH.read_text(encoding="utf-8"))["sources"]}
    if pinned.get(rel) != sha256_file(path):
        raise DataIntegrityError(f"{rel}: sha256 data_version.json ile aynı değil")
    d1: dict[str, D1Row] = {}
    dates: dict[str, dict[int, str]] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            ticker, k = r["ticker"], int(r["session_number"])
            dates.setdefault(ticker, {})[k] = r["target_session_date"]
            if k != 1:
                continue
            st, ts = r["session_type"], r["security_trading_status"]
            if st not in HALF_DAY_OF or ts not in HALT_OF:
                raise DataIntegrityError(f"{UNKNOWN_OFFICIAL_CODE}: {ticker}/D1 session_type={st!r}, "
                                         f"security_trading_status={ts!r} (satır elle incelenmeli)")
            d1[ticker] = D1Row(ticker, r["target_session_date"], {name: r[col] for name, col in SESSION_1_FIELDS.items()},
                               HALF_DAY_OF[st], HALT_OF[ts], st, ts)
    return d1, dates


@dataclass(frozen=True)
class H99D1:
    row: D1Row
    values: Optional[pd1.D1Values]     # None: D1 tavanda kapanmadı (NOT_APPLICABLE)


def h99_d1(dataset: Dataset) -> dict[str, H99D1]:
    """99 arzın D_1 değerleri (`predict_post_d1.evaluate_d1`, tek tanım). Tavan etiketi training_table'la, seans tarihleri
    veriyle aynı olmalı."""
    d1, dates = load_d1_sessions()
    out: dict[str, H99D1] = {}
    for r in dataset.rows:
        if dates.get(r.ticker) != {k + 1: d for k, d in enumerate(r.session_dates)} or d1[r.ticker].session_date != r.first_trading_date:
            raise DataIntegrityError(f"{r.ticker}: SESSIONS seans tarihleri veriyle aynı değil")
        try:
            values: Optional[pd1.D1Values] = pd1.evaluate_d1(d1[r.ticker].block(), r.inputs["shares_offered"])
        except pd1.D1NotApplicable:
            values = None
        if (values is not None) != bool(r.ceiling_close[0]):
            raise DataIntegrityError(f"{r.ticker}: D_1 tavan etiketi (ham metin) training_table ceiling_close_D1 ile aynı değil")
        out[r.ticker] = H99D1(d1[r.ticker], values)
    return out


def model_inputs_of(row: IPORow) -> dict[str, Any]:
    """Listeleme öncesi kaydın `model_inputs`'unun H99 karşılığı (ana modelin girdileri)."""
    return {**row.feature_inputs(), "total_demand_filter_status": row.total_demand_filter_status}


# ============================================================ D1 ön işlemesi (arz düzeyinde, kesin)

def _z(value: Fraction, mean: Fraction, std: Decimal, col: str) -> float:
    diff = pp._frac_to_dec(value - mean, _CTX, col, "Z_NUMERATOR", "D1")
    return pp._to_float(pp._div(diff, std, _CTX, col, "Z_DIVIDE", "D1"), col, "Z_TO_BINARY64", "D1")


@dataclass(frozen=True)
class D1Prep:
    tickers: tuple[str, ...]
    p05: Fraction
    p95: Fraction
    mean: dict[str, Fraction]
    std: dict[str, Decimal]        # düşen kolon: 0
    columns: tuple[str, ...]
    dropped: tuple[str, ...]
    ranges: dict[str, dict[str, float]]

    def transform(self, feats: Mapping[str, float]) -> tuple[dict[str, float], bool]:
        """(u, d1_turnover kırpıldı mı): kesin yol (eğitim satırları ve backtest test arzı)."""
        raw = Fraction(feats["d1_turnover"])
        values = {"d1_lock": Fraction(feats["d1_lock"]), "d1_turnover": min(max(raw, self.p05), self.p95)}
        return {c: _z(values[c], self.mean[c], self.std[c], c) for c in self.columns}, values["d1_turnover"] != raw

    def params(self) -> dict[str, Any]:
        """JSON (binary64): predict_post_d1.d1_transform bunu kullanır."""
        return {"columns": list(self.columns), "clip": {"d1_turnover": {"p05": float(self.p05), "p95": float(self.p95)}},
                "mean": {c: float(self.mean[c]) for c in D1_COLUMNS},
                "std": {c: pp._to_float(self.std[c], c, "STD", "REPORTING") for c in D1_COLUMNS},
                "dropped": list(self.dropped), "n_train": len(self.tickers),
                "method": SPEC["d1_preprocessing"]["arithmetic"]}


def fit_d1_prep(feats: Mapping[str, Mapping[str, float]]) -> D1Prep:
    """Eğitim arzlarından (sözlük sırası) D1 ön işlemesi."""
    tickers = tuple(feats)
    if not tickers:
        raise PostD1Error("fit_d1_prep: boş eğitim kümesi")
    n = len(tickers)
    turn = sorted(Fraction(feats[t]["d1_turnover"]) for t in tickers)
    p05, p95 = pp.quantile_type7(turn, pp.WINSOR_P05), pp.quantile_type7(turn, pp.WINSOR_P95)
    values = {"d1_lock": [Fraction(feats[t]["d1_lock"]) for t in tickers],
              "d1_turnover": [min(max(Fraction(feats[t]["d1_turnover"]), p05), p95) for t in tickers]}
    mean: dict[str, Fraction] = {}
    std: dict[str, Decimal] = {}
    columns, dropped = [], []
    for c in D1_COLUMNS:
        mean[c] = sum(values[c], Fraction(0)) / n
        var = sum(((v - mean[c]) ** 2 for v in values[c]), Fraction(0)) / n
        if var == 0:
            std[c] = Decimal(0)
            dropped.append(c)
            continue
        std[c] = pp._sqrt(pp._frac_to_dec(var, _CTX, c, "VARIANCE_FRACTION_TO_DECIMAL", "D1"), _CTX, c, "D1")
        columns.append(c)
    ranges = {c: {"min": min(feats[t][c] for t in tickers), "max": max(feats[t][c] for t in tickers), "n": n} for c in D1_COLUMNS}
    return D1Prep(tickers, p05, p95, mean, std, tuple(columns), tuple(dropped), ranges)


# ============================================================ δ fit'i (numpy)

@dataclass
class DeltaSet:
    """δ eğitim kümesi: d ≥ 2 kişi-dönem satırı olan arzlar (sıralı), satırları, ofsetleri ve D1 özellikleri."""

    tickers: list[str]
    rows: dict[str, list[tuple[int, int]]]       # ticker -> [(gün, olay)], d ≥ 2
    eta: dict[str, list[float]]                  # ticker -> η_1..η_10 (ana model, ofset)
    feats: dict[str, dict[str, float]]           # ticker -> {d1_lock, d1_turnover}

    @property
    def n_rows(self) -> int:
        return sum(len(self.rows[t]) for t in self.tickers)

    @property
    def n_events(self) -> int:
        return sum(e for t in self.tickers for _, e in self.rows[t])


@dataclass
class DeltaFit:
    lam: float
    columns: tuple[str, ...]
    delta: np.ndarray
    status: str
    iterations: int = 0
    grad_max: float = 0.0

    def by_feature(self) -> dict[str, float]:
        """İki D1 özelliği için katsayı; düşen özellik 0."""
        got = dict(zip(self.columns, (float(d) for d in self.delta)))
        return {c: got.get(c, 0.0) for c in D1_COLUMNS}


def arrays(ds: DeltaSet, tickers: Sequence[str], prep: D1Prep) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(U, ofset, olay) satır sırasıyla; U kolonları prep.columns."""
    U: list[list[float]] = []
    o: list[float] = []
    e: list[float] = []
    for t in tickers:
        z, _ = prep.transform(ds.feats[t])
        for d, ev in ds.rows[t]:
            U.append([z[c] for c in prep.columns])
            o.append(ds.eta[t][d - 1])
            e.append(float(ev))
    return (np.array(U, dtype=np.float64).reshape(len(o), len(prep.columns)), np.array(o, dtype=np.float64),
            np.array(e, dtype=np.float64))


def objective(U: np.ndarray, o: np.ndarray, e: np.ndarray, delta: np.ndarray, lam: float) -> float:
    eta = o + (U @ delta if U.shape[1] else 0.0)
    return float(np.sum(np.logaddexp(0.0, eta) - e * eta)) + 0.5 * lam * float(delta @ delta)


def newton_offset(U: np.ndarray, o: np.ndarray, e: np.ndarray, lam: float) -> hz.SolverResult:
    """Tam Newton–Raphson (SPEC_CEILING_V0 §5 çözücüsü, ofsetli, pseudo-satırsız); δ0 = 0; adım yarılama, A2 kabul kuralı."""
    p = U.shape[1]
    theta = np.zeros(p, dtype=np.float64)
    J = objective(U, o, e, theta, lam)
    noise = len(e) * hz._EPS
    grad_max = math.inf
    for it in range(hz.MAX_ITER + 1):
        h = hz._stable_sigmoid(o + U @ theta)
        grad = U.T @ (h - e) + lam * theta
        grad_max = float(np.max(np.abs(grad)))
        if grad_max <= hz.GRAD_TOL:
            return hz.SolverResult(theta, hz.CONVERGED, it, grad_max, J)
        if it == hz.MAX_ITER or not math.isfinite(grad_max):
            break
        H = (U * (h * (1.0 - h))[:, None]).T @ U + lam * np.eye(p)
        try:
            step_dir = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            break
        step = 1.0
        for _ in range(hz.MAX_HALVINGS + 1):
            candidate = theta - step * step_dir
            J_new = objective(U, o, e, candidate, lam)
            if J_new <= J + noise * max(abs(J), 1.0):
                break
            step *= 0.5
        else:
            break
        theta, J = candidate, J_new
    return hz.SolverResult(theta, hz.STATUS_NOT_CONVERGED, it, grad_max, J)


def fit_delta(U: np.ndarray, o: np.ndarray, e: np.ndarray, lam: float, columns: Sequence[str]) -> DeltaFit:
    """λ = INF (ya da hiç kolon kalmadıysa): δ ≡ 0 kapalı biçim. Aksi halde ofsetli Newton."""
    p = len(columns)
    if lam == hz.INF or p == 0:
        return DeltaFit(lam, tuple(columns), np.zeros(p, dtype=np.float64), hz.CONVERGED)
    res = newton_offset(U, o, e, lam)
    return DeltaFit(lam, tuple(columns), res.theta.copy(), res.status, res.iterations, res.grad_max)


def row_nll(fit: DeltaFit, U: np.ndarray, o: np.ndarray, e: np.ndarray) -> np.ndarray:
    eta = o + (U @ fit.delta if U.shape[1] else 0.0)
    h = np.clip(hz._stable_sigmoid(eta), hz.H_CLIP, 1.0 - hz.H_CLIP)
    return -(e * np.log(h) + (1.0 - e) * np.log(1.0 - h))


def select_lambda(ds: DeltaSet, grid: Sequence[float] = LAMBDA_GRID) -> tuple[float, list[dict[str, Any]]]:
    """İç arz-bırak CV: her j için j'nin bütün d ≥ 2 satırları dışarıda, D1 ön işlemesi kalanlardan; ofset değişmez."""
    totals = {lam: 0.0 for lam in grid}
    failed: set[float] = set()
    n_rows = 0
    for j in ds.tickers:
        inner = [t for t in ds.tickers if t != j]
        prep = fit_d1_prep({t: ds.feats[t] for t in inner})
        U, o, e = arrays(ds, inner, prep)
        Uj, oj, ej = arrays(ds, [j], prep)
        for lam in grid:
            if lam in failed:
                continue
            fit = fit_delta(U, o, e, lam, prep.columns)
            if fit.status != hz.CONVERGED:
                failed.add(lam)
                continue
            totals[lam] += float(np.sum(row_nll(fit, Uj, oj, ej)))
        n_rows += len(ds.rows[j])
    table = []
    for lam in grid:
        if lam in failed:
            table.append({"lambda": hz.lambda_label(lam), "score": None, "status": hz.CANDIDATE_NOT_CONVERGED})
        else:
            table.append({"lambda": hz.lambda_label(lam), "score": totals[lam] / n_rows, "status": hz.SCORED})
    return hz.choose_lambda(table), table


@dataclass
class DeltaTraining:
    status: str
    selected_lambda: float
    score_table: list[dict[str, Any]]
    fit: DeltaFit
    prep: D1Prep


def fit_delta_set(ds: DeltaSet, grid: Sequence[float] = LAMBDA_GRID) -> DeltaTraining:
    """λ seçimi + nihai δ (eğitim kümesinin tamamıyla; D1 ön işlemesi bütün arzlardan)."""
    selected, table = select_lambda(ds, grid) if len(grid) > 1 else (grid[0], [])
    prep = fit_d1_prep({t: ds.feats[t] for t in ds.tickers})
    U, o, e = arrays(ds, ds.tickers, prep)
    fit = fit_delta(U, o, e, selected, prep.columns)
    return DeltaTraining(STATUS_FIT_OK if fit.status == hz.CONVERGED else STATUS_NOT_CONVERGED, selected, table, fit, prep)


def predict_with(eta: Sequence[float], feats: Mapping[str, float], training: DeltaTraining,
                 reclose: Mapping[str, float]) -> dict[str, Any]:
    """Backtest/nihai-fit tarafının tahmini: kesin D1 dönüşümü + predict_post_d1'in ortak hesabı."""
    u, clipped = training.prep.transform(feats)
    hazards = pd1.updated_hazards(eta, training.fit.by_feature(), u, training.prep.columns)
    return {**pd1.curves(hazards, reclose), "u": u, "d1_clipped": clipped}


# ============================================================ walk-forward (§6)

def ledger_columns() -> list[str]:
    cols = ["model_id", "fold_id", "ticker", "first_trading_date", "prediction_date", "training_n_ipo", "training_n_pp_rows",
            "training_n_events", "training_n_survivals", "training_max_session_date", "training_tickers_sha256",
            "training_pp_sha256", "parent_fold_status", "parent_gamma_g1", "parent_gamma_g2", "parent_gamma_g3",
            "parent_beta_f1", "parent_beta_f2", "parent_beta_f3", "parent_selected_lambda", "parent_ledger_row_sha256",
            "selected_lambda", "lambda_score_table", "n_lambda_not_converged", "columns", "delta_d1_lock",
            "delta_d1_turnover", "d1_clip_p05", "d1_clip_p95", "d1_mean_lock", "d1_std_lock", "d1_mean_turnover",
            "d1_std_turnover", "solver_iterations", "solver_grad_max", "test_d1_lock", "test_d1_turnover_ratio",
            "test_d1_turnover_clipped"]
    cols += [f"hazard_{k}" for k in range(1, sv.DAYS + 1)] + [f"S_{k}" for k in range(1, sv.DAYS + 1)]
    cols += [f"S_cond_{k}" for k in range(2, sv.DAYS + 1)]
    cols += ["path_cond_status"] + [f"path_cond_h{h}_{x}" for h in PATH_HORIZONS for x in ("median", "p_up")]
    cols += ["realized_L", "status"]
    return cols


def read_pinned_csv(ref: Mapping[str, str]) -> tuple[list[dict[str, str]], str]:
    raw = (ROOT / ref["path"]).read_bytes()
    sha = sha256_bytes(raw)
    if sha != ref["sha256"]:
        raise PostD1Error(f"{ref['path']}: sha256 {sha} != şartname/spec {ref['sha256']}")
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))), sha


def delta_set_of(res: hz.TrainingResult, feats: Mapping[str, Mapping[str, float]]) -> DeltaSet:
    """Fold'un δ eğitim kümesi: ana modelin PP satırlarından d ≥ 2 olanlar; ofset o fold'un fit'inden (eğitim z'si)."""
    rows: dict[str, list[tuple[int, int]]] = {}
    for r in res.rows:
        if r.day >= 2:
            rows.setdefault(r.ticker, []).append((r.day, r.event))
    tickers = list(rows)
    eta = {t: res.fit.linear_predictors(res.prepared.z[t]) for t in tickers}
    return DeltaSet(tickers, rows, eta, {t: dict(feats[t]) for t in tickers})


def _fold_task(payload: dict[str, Any]) -> dict[str, Any]:
    """Tek fold (alt süreçte de çalışır): ana modelin fold fit'i (ofset), δ eğitim kümesi, λ seçimi, nihai δ, test tahmini."""
    res = hz.fit_training_set(payload["units"], payload["raw"], payload["status"], cutoff=payload["cutoff"],
                              features=payload["features"], recipe=payload["recipe"], grid=payload["grid"])
    out: dict[str, Any] = {"parent_status": res.status, "parent_n_ipo": res.n_ipo, "parent_n_pp_rows": res.n_pp_rows}
    if res.status != hz.STATUS_FIT_OK:
        return out
    z_test = res.prepared.prep.transform(payload["test_raw"], payload["test_status"])["z"] if res.prepared.columns else {}
    out.update(parent_gamma=[float(g) for g in res.fit.gamma], parent_beta=res.beta_by_feature(),
               parent_lambda=hz.lambda_label(res.selected_lambda), parent_test_hazards=res.fit.hazards(z_test))
    eta_test = res.fit.linear_predictors(z_test)
    ds = delta_set_of(res, payload["feats"])
    dates = [payload["session_dates"][t][d - 1] for t in ds.tickers for d, _ in ds.rows[t]]
    d1_dates = [payload["session_dates"][t][0] for t in ds.tickers]
    events = ds.n_events
    out.update(n_ipo=len(ds.tickers), n_pp_rows=ds.n_rows, n_events=events, n_survivals=ds.n_rows - events,
               max_session_date=max(dates) if dates else None, max_d1_date=max(d1_dates) if d1_dates else None,
               tickers_sha256=identity_hash(ds.tickers),
               pp_sha256=identity_hash([f"{t}|{d}|{e}" for t in ds.tickers for d, e in ds.rows[t]]))
    if not (len(ds.tickers) >= MIN_IPO and events >= MIN_EVENTS and ds.n_rows - events >= MIN_SURVIVALS):
        out["status"] = STATUS_INSUFFICIENT
        return out
    if payload["delta_grid"] is None:      # yalnız ofset ve δ eğitim kümesi (fit yok): kabul testleri 3, 4, 8
        out.update(status=None, feats_used=ds.feats, prep=fit_d1_prep(ds.feats).params())
        return out
    training = fit_delta_set(ds, payload["delta_grid"])
    out.update(selected_lambda=hz.lambda_label(training.selected_lambda), score_table=training.score_table,
               columns=list(training.prep.columns), delta=training.fit.by_feature(), prep=training.prep.params(),
               iterations=training.fit.iterations, grad_max=training.fit.grad_max, status=training.status)
    if training.status != STATUS_FIT_OK:
        return out
    pred = predict_with(eta_test, payload["test_feats"], training, res.reclose)
    out.update(hazards=pred["hazard"], S=pred["S"], S_cond=pred["conditional_j1"]["S_cond"], test_clipped=pred["d1_clipped"])
    return out


def default_workers() -> int:
    from .backtest import default_workers as dw

    return dw()


def _row_sha(row: Mapping[str, str]) -> str:
    return canonical_sha256(dict(row))


def load_path_template(models_dir: Path = MODELS_DIR) -> dict[str, Any]:
    """Dondurulmuş ceiling_path_v0 (sha256 INDEX.json ve spec ile aynı olmalı); fold'da yalnız hücreleri değişir."""
    params, _ = load_frozen(SPEC["path_secondary"], models_dir)
    return params


def fold_path_params(template: Mapping[str, Any], cells: Mapping[tuple[str, int], Sequence[tuple[float, str]]]) -> dict[str, Any]:
    return {**template, "post_break": {**template["post_break"], "cells": pth.cells_to_json(cells)}}


def fold_path_output(price: Decimal, S: Sequence[float]) -> dict[str, Any]:
    """predict_path.predict biçiminde limit yolu (arz fiyatından; §2) ve verilen S."""
    lp = pth.limit_path(price)
    return {"refused": None, "S": list(S), "limit_path": {"ipo_price": str(price), "snapped_ipo_price": str(lp["snapped_ipo_price"]),
                                                          "tick": str(lp["tick"]), "C": [str(c) for c in lp["C"]], "rho": lp["rho"]}}


def path_cells_by_fold(dataset: Dataset, path_rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """fold_id -> o fold'un ceiling_path_v0 walk-forward hücreleri (SPEC_CEILING_PATH_V0 §8; Faz 4 ledger'ı OK ise).
    Hücre sayıları Faz 4 ledger'ıyla aynı olmalı."""
    from . import ceiling_path as cp

    units = cp.path_units(dataset.rows)
    out: dict[str, Any] = {}
    for r in path_rows:
        if r["status"] != cp.STATUS_OK:
            continue
        cells, info = pth.build_cells(units, cutoff=r["prediction_date"])
        counts = {f"cells_n_{g}_{m}": str(len(cells[(g, m)])) for g in pth.GROUPS for m in range(1, pth.M_MAX[g] + 1)}
        if any(r[k] != v for k, v in counts.items()) or (info["max_session_date"] or "") != r["cells_max_session_date"]:
            raise PostD1Error(f"{r['fold_id']}: hücreler Faz 4 ledger'ıyla aynı değil")
        out[r["fold_id"]] = cells
    return out


def path_summary(cond: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    if cond is None:
        return {"path_cond_status": PATH_NOT_PRODUCED, **{f"path_cond_h{h}_{x}": None for h in PATH_HORIZONS for x in ("median", "p_up")}}
    ok = all(cond[f"D{h}"]["status"] == pth.STATUS_OK for h in PATH_HORIZONS)
    out: dict[str, Any] = {"path_cond_status": PATH_OK if ok else pth.STATUS_POST_BREAK_INSUFFICIENT}
    for h in PATH_HORIZONS:
        out[f"path_cond_h{h}_median"] = cond[f"D{h}"]["return"]
        out[f"path_cond_h{h}_p_up"] = cond[f"D{h}"]["p_up"]
    return out


def fold_parts(dataset: Dataset, *, workers: Optional[int] = None, delta_grid: Optional[Sequence[float]] = LAMBDA_GRID,
               feats_override: Optional[Mapping[str, Mapping[str, float]]] = None) -> dict[str, Any]:
    """Uygulanabilir her fold için `_fold_task` çıktısı (fold_id -> sözlük) ve ortak girdiler. `delta_grid=None`: δ fit'i
    yapılmaz (yalnız ofset paritesi ve δ eğitim kümesi). `feats_override`: sızıntı testi için D1 özelliklerini değiştirir."""
    from . import backtest as bt
    from . import fit as fitmod

    src_rows, src_sha = read_pinned_csv(SPEC["survival_ledger"])
    folds = {f.test_ticker: f for f in bt.plan_ceiling_folds(dataset, PLAN_CEILING)}
    by = dataset.by_ticker()
    d1 = h99_d1(dataset)
    rows = list(dataset.rows)
    features = tuple(PARENT_SPEC["features"])
    raw = fitmod.model_raw_features(PARENT_SPEC, rows)[0]
    status = {r.ticker: r.total_demand_filter_status for r in rows}
    units = {r.ticker: sv.unit_of(r) for r in rows}
    recipe = fitmod.recipe_for(PARENT_SPEC)
    feats = {t: v.values.features() for t, v in d1.items() if v.values is not None}
    if feats_override:
        feats.update({t: dict(v) for t, v in feats_override.items()})
    session_dates = {r.ticker: list(r.session_dates) for r in rows}
    todo, payloads = [], []
    for src in src_rows:
        t = src["ticker"]
        f = folds[t]
        if src["model_id"] != SPEC["parent"]["model_id"] or src["first_trading_date"] != by[t].first_trading_date \
                or f.status != bt.SCORABLE or f.cutoff_date != src["prediction_date"] \
                or identity_hash(f.training) != src["training_tickers_sha256"] or f.pp_sha256 != src["training_pp_sha256"]:
            raise PostD1Error(f"{src['fold_id']}: fold planı Faz 1B ledger'ıyla aynı değil")
        if by[t].ceiling_streak < 1 or src["status"] != hz.STATUS_FIT_OK:
            continue
        todo.append(src["fold_id"])
        payloads.append({
            "units": [units[j] for j in f.training], "raw": {j: raw[j] for j in f.training},
            "status": {j: status[j] for j in f.training}, "cutoff": f.cutoff_date, "features": features, "recipe": recipe,
            "grid": hz.LAMBDA_GRID, "delta_grid": None if delta_grid is None else tuple(delta_grid),
            "test_raw": raw[t], "test_status": status[t],
            "feats": {j: feats[j] for j in f.training if j in feats}, "test_feats": feats[t],
            "session_dates": {j: session_dates[j] for j in f.training},
        })
    workers = default_workers() if workers is None else workers
    if workers <= 1:
        parts = [_fold_task(p) for p in payloads]
    else:
        ctx = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
            parts = list(pool.map(_fold_task, payloads, chunksize=1))
    return {"parts": dict(zip(todo, parts)), "src_rows": src_rows, "src_sha": src_sha, "d1": d1, "by": by}


def backtest_ledger(dataset: Dataset, *, workers: Optional[int] = None,
                    delta_grid: Sequence[float] = LAMBDA_GRID) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """(ledger satırları, günlük ek alanları). Fold kümesi ve sırası Faz 1B tavan ledger'ınınki."""
    fp = fold_parts(dataset, workers=workers, delta_grid=delta_grid)
    src_rows, src_sha, d1, by, results = fp["src_rows"], fp["src_sha"], fp["d1"], fp["by"], fp["parts"]
    path_rows, path_sha = read_pinned_csv(SPEC["path_ledger"])
    if [r["fold_id"] for r in path_rows] != [r["fold_id"] for r in src_rows]:
        raise PostD1Error("Faz 4 ceiling_path_v0 ledger'ının fold kümesi tavan ledger'ınınkiyle aynı değil")
    cells_by = path_cells_by_fold(dataset, path_rows)
    path_by = {r["fold_id"]: r for r in path_rows}
    template = load_path_template()
    ledger = []
    for src in src_rows:
        ledger.append(_ledger_row(src, results.get(src["fold_id"]), by[src["ticker"]], d1[src["ticker"]],
                                  cells_by.get(src["fold_id"]) if path_by[src["fold_id"]]["status"] == "OK" else None, template))
    info = {"survival_model_id": SPEC["parent"]["model_id"], "survival_ledger": SPEC["survival_ledger"]["path"],
            "survival_ledger_sha256": src_sha, "path_ledger": SPEC["path_ledger"]["path"], "path_ledger_sha256": path_sha,
            "sessions_file_sha256": sha256_file(SESSIONS_PATH), "folds_total": len(src_rows)}
    return ledger, info


def _parity(src: Mapping[str, str], part: Mapping[str, Any]) -> None:
    """Kabul testi 3: fold'un yeniden koşulan ana model fit'i Faz 1B ledger satırıyla |Δ| ≤ 1e-9 (γ, β, λ, test hazard'ları)."""
    got = [*part["parent_gamma"], *(part["parent_beta"][f] for f in ("f1", "f2", "f3")), *part["parent_test_hazards"]]
    want = [float(src[f"gamma_{g}"]) for g in sv.GROUP_NAMES] + [float(src[f"beta_{f}"]) for f in ("f1", "f2", "f3")] + \
           [float(src[f"hazard_{k}"]) for k in range(1, sv.DAYS + 1)]
    from .backtest import _fmt

    if _fmt(part["parent_lambda"]) != src["selected_lambda"] or len(got) != len(want) \
            or any(abs(a - b) > PARITY_TOL for a, b in zip(got, want)):
        raise PostD1Error(f"{src['fold_id']}: ofset paritesi tutmuyor (kabul testi 3)")


def _ledger_row(src: Mapping[str, str], part: Optional[Mapping[str, Any]], row: IPORow, d1: H99D1,
                cells: Optional[Mapping[tuple[str, int], Sequence[tuple[float, str]]]], template: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {k: None for k in ledger_columns()}
    out.update(model_id=MODEL_ID, fold_id=src["fold_id"], ticker=src["ticker"], first_trading_date=src["first_trading_date"],
               prediction_date=d1.row.session_date, parent_fold_status=src["status"], realized_L=row.ceiling_streak)
    if row.ceiling_streak < 1:
        out["status"] = STATUS_NOT_APPLICABLE
        return out
    if src["status"] != hz.STATUS_FIT_OK:
        out["status"] = STATUS_SURVIVAL_NOT_AVAILABLE
        return out
    if part is None or part["parent_status"] != hz.STATUS_FIT_OK:
        raise PostD1Error(f"{src['fold_id']}: ana model fold fit'i yeniden koşulamadı")
    _parity(src, part)
    if part["max_d1_date"] is not None and not part["max_d1_date"] < src["prediction_date"]:
        raise PostD1Error(f"{src['fold_id']}: eğitim arzının D1 tarihi kesimden önce değil")
    if part["max_session_date"] is not None and not part["max_session_date"] < src["prediction_date"]:
        raise PostD1Error(f"{src['fold_id']}: eğitim seansı kesimden önce değil")
    out.update(training_n_ipo=part["n_ipo"], training_n_pp_rows=part["n_pp_rows"], training_n_events=part["n_events"],
               training_n_survivals=part["n_survivals"], training_max_session_date=part["max_session_date"],
               training_tickers_sha256=part["tickers_sha256"], training_pp_sha256=part["pp_sha256"],
               parent_gamma_g1=part["parent_gamma"][0], parent_gamma_g2=part["parent_gamma"][1],
               parent_gamma_g3=part["parent_gamma"][2], parent_beta_f1=part["parent_beta"]["f1"],
               parent_beta_f2=part["parent_beta"]["f2"], parent_beta_f3=part["parent_beta"]["f3"],
               parent_selected_lambda=part["parent_lambda"], parent_ledger_row_sha256=_row_sha(src))
    if part["status"] == STATUS_INSUFFICIENT:
        out["status"] = STATUS_INSUFFICIENT
        return out
    prep = part["prep"]
    v = d1.values
    out.update(selected_lambda=part["selected_lambda"], lambda_score_table=canonical_json(part["score_table"]),
               n_lambda_not_converged=sum(1 for e in part["score_table"] if e["status"] != hz.SCORED),
               columns=canonical_json(part["columns"]), delta_d1_lock=part["delta"]["d1_lock"],
               delta_d1_turnover=part["delta"]["d1_turnover"], d1_clip_p05=prep["clip"]["d1_turnover"]["p05"],
               d1_clip_p95=prep["clip"]["d1_turnover"]["p95"], d1_mean_lock=prep["mean"]["d1_lock"],
               d1_std_lock=prep["std"]["d1_lock"], d1_mean_turnover=prep["mean"]["d1_turnover"],
               d1_std_turnover=prep["std"]["d1_turnover"], solver_iterations=part["iterations"],
               solver_grad_max=part["grad_max"], test_d1_lock=v.lock, test_d1_turnover_ratio=float(v.turnover_ratio))
    if part["status"] != STATUS_FIT_OK:
        out["status"] = part["status"]
        return out
    out["test_d1_turnover_clipped"] = part["test_clipped"]
    out.update({f"hazard_{k}": part["hazards"][k - 1] for k in range(1, sv.DAYS + 1)})
    out.update({f"S_{k}": part["S"][k - 1] for k in range(1, sv.DAYS + 1)})
    out.update({f"S_cond_{k}": part["S_cond"][str(k)] for k in range(2, sv.DAYS + 1)})
    cond = None
    if cells is not None:
        cond = pd1.path_conditional(fold_path_params(template, cells), fold_path_output(Decimal(row.inputs["ipo_price_tl"]), part["S"]),
                                    part["S"], d1.row.fields_raw["close"])
    out.update(path_summary(cond))
    out["status"] = STATUS_FIT_OK
    if list(out) != ledger_columns():
        raise PostD1Error("ledger sütunları şartnameyle aynı değil")
    return out


def compute_metrics(ledger: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Günlük metrikleri (modelin kendi FIT_OK kümesi, koşullu ölçek j = 1; ortak fonksiyonlar)."""
    from collections import Counter

    from . import metrics as mx

    ok = [r for r in ledger if r["status"] == STATUS_FIT_OK]
    S = {r["fold_id"]: [r[f"S_{k}"] for k in range(1, sv.DAYS + 1)] for r in ok}
    return {
        "scale": "backtest_conditional", "j": pd1.CONDITION_J, "n": len(ok),
        "rps_cond": mx.mean_or_none(pth.conditional_rps(S[r["fold_id"]], 1, r["realized_L"]) for r in ok),
        "brier_cond_k2": mx.mean_or_none(pth.conditional_brier(S[r["fold_id"]], 1, r["realized_L"], 2) for r in ok),
        "brier_cond_k10": mx.mean_or_none(pth.conditional_brier(S[r["fold_id"]], 1, r["realized_L"], 10) for r in ok),
        "status_counts": dict(sorted(Counter(r["status"] for r in ledger).items())),
        "lambda_counts": dict(sorted(Counter(str(r["selected_lambda"]) for r in ok).items())),
        "path_cond_status_counts": dict(sorted(Counter(r["path_cond_status"] for r in ok).items())),
    }


COMPARATOR_RUNS = ("ceiling_hazard_v0", "ceiling_hazard_v0@INF", "base_km_expanding", "base_km_last10", "base_always_ceiling__ceiling")


def evaluated_ledgers() -> list[dict[str, Any]]:
    """Karşılaştırıcı ve kuralların Faz 1B/Faz 4 altın ledger'ları (yeniden koşulmaz; sha'ları günlüğe)."""
    from .backtest import GOLDEN_FAZ1B_DIR, GOLDEN_FAZ4_DIR

    out = []
    for d, keys in ((GOLDEN_FAZ1B_DIR, COMPARATOR_RUNS), (GOLDEN_FAZ4_DIR, ("ceiling_path_v0",))):
        manifest = json.loads((d / "MANIFEST.json").read_text(encoding="utf-8"))
        for k in keys:
            info = manifest["runs"][k]
            out.append({"run_key": k, "model_id": info["model_id"], "plan_id": info["plan_id"], "ledger_sha256": info["ledger_sha256"]})
    return out


@dataclass
class PostD1Result:
    ledger: list[dict[str, Any]]
    ledger_csv: bytes
    metrics: dict[str, Any]
    log_entry: dict[str, Any]


def run_backtest(dataset: Dataset, *, log_path: Path, context: str, workers: Optional[int] = None) -> PostD1Result:
    """PLAN_POST_D1 walk-forward; sonunda günlüğe bir `kind: backtest` satırı (CLAUDE.md kural 4)."""
    from . import backtest as bt
    from . import fit as fitmod

    runtime = fitmod.verify_runtime()
    started = now_istanbul()
    ledger, info = backtest_ledger(dataset, workers=workers)
    payload = bt.ledger_csv_bytes(ledger)
    metrics = compute_metrics(ledger)
    entry = {
        "kind": "backtest",
        "context": context,
        "model_id": MODEL_ID,
        "stage": SPEC["stage"],
        "spec_sha256": spec_sha256(SPEC),
        "plan_id": PLAN_POST_D1,
        "data_version_sha256": dataset.data_version_sha256,
        "training_table_sha256": dataset.table_sha256,
        "folds_total": len(ledger),
        "folds_scorable": {"POST_D1": sum(1 for r in ledger if r["status"] == STATUS_FIT_OK)},
        "ledger_sha256": sha256_bytes(payload),
        **info,
        "evaluated": evaluated_ledgers(),
        "metrics": metrics,
        "started_at": started,
        "finished_at": now_istanbul(),
        **code_version(),
        "spec_document": SPEC["spec_document"]["path"],
        "spec_document_sha256": sha256_file(ROOT / SPEC["spec_document"]["path"]),
        "runtime": runtime,
    }
    bt.append_log(log_path, entry)
    return PostD1Result(ledger, payload, metrics, entry)


# ============================================================ nihai fit (önizleme; dondurma ayrı görev)

def load_frozen(ref: Mapping[str, str], models_dir: Path = MODELS_DIR) -> tuple[dict[str, Any], str]:
    """Dondurulmuş dosya: INDEX.json kaydı, dosya sha256'sı ve spec'teki sha256 aynı olmalı."""
    index = json.loads((Path(models_dir) / "INDEX.json").read_text(encoding="utf-8"))
    entry = next((e for e in index["models"] if e["model_id"] == ref["model_id"]), None)
    if entry is None or entry["file"] != ref["file"]:
        raise PostD1Error(f"{ref['model_id']} INDEX.json'da yok ya da dosya adı farklı")
    raw = (Path(models_dir) / entry["file"]).read_bytes()
    sha = sha256_bytes(raw)
    if not sha == entry["sha256"] == ref["sha256"]:
        raise PostD1Error(f"{ref['model_id']}: sha256 {sha} INDEX/spec ile aynı değil")
    return json.loads(raw), sha


def final_training_rows(dataset: Dataset) -> list[IPORow]:
    """H99_F3_PRESENT_L_GE_1: f3 dolu VE ceiling_close_D1 = 1 (tablo sırası)."""
    return [r for r in dataset.rows if r.inputs["total_demand_multiple"] is not None and r.ceiling_close[0] == 1]


def final_delta_set(dataset: Dataset, parent: Mapping[str, Any]) -> tuple[DeltaSet, list[IPORow], dict[str, H99D1]]:
    """Nihai fit'in δ eğitim kümesi: 81 arzın d ≥ 2 satırları (kesim yok; sonuç seansları ≤ 2026-08-19), ofset
    dondurulmuş JSON'dan `predict_hazard.linear_predictor` ile (tahmin yoluyla aynı)."""
    rows = final_training_rows(dataset)
    d1 = h99_d1(dataset)
    pp_rows: dict[str, list[tuple[int, int]]] = {}
    for r in sv.pp_table([sv.unit_of(x) for x in rows]):
        if r.day >= 2:
            pp_rows.setdefault(r.ticker, []).append((r.day, r.event))
    eta = {}
    for r in rows:
        lp = ph.linear_predictor(parent, model_inputs_of(r))
        if lp["refused"]:
            raise PostD1Error(f"{r.ticker}: ana model reddetti ({lp['refused']['code']})")
        eta[r.ticker] = lp["eta"]
    tickers = [r.ticker for r in rows if r.ticker in pp_rows]
    return DeltaSet(tickers, {t: pp_rows[t] for t in tickers}, {t: eta[t] for t in tickers},
                    {t: d1[t].values.features() for t in tickers}), rows, d1


def fit_params(dataset: Dataset, *, models_dir: Path = MODELS_DIR, grid: Sequence[float] = LAMBDA_GRID) -> dict[str, Any]:
    """Dondurulacak parametre sözlüğü (şartname §3.5). Dosyaya yazmaz."""
    from . import fit as fitmod

    spec = SPEC
    if dataset.data_version_sha256 != spec["training"]["data_version_sha256"]:
        raise PostD1Error("veri sürümü şartnameyle tutmuyor; CLAUDE.md kural 5: yeni model_id")
    parent, parent_sha = load_frozen(spec["parent"], models_dir)
    _, path_sha = load_frozen(spec["path_secondary"], models_dir)
    ds, rows, d1 = final_delta_set(dataset, parent)
    if len(rows) != spec["training"]["n"]:
        raise PostD1Error(f"eğitim n'i {len(rows)} != şartname {spec['training']['n']}")
    dates = [r.session_dates[d - 1] for r in rows for d, _ in ds.rows.get(r.ticker, [])]
    if max(dates) > OUTCOME_CUTOFF:
        raise PostD1Error(f"eğitimde {OUTCOME_CUTOFF} sonrası seans var")
    runtime = fitmod.verify_runtime()
    training = fit_delta_set(ds, grid)
    if training.status != STATUS_FIT_OK:
        raise PostD1Error(f"nihai δ fit'i {training.status}")
    tickers = [r.ticker for r in rows]
    events = ds.n_events
    block = {
        "set": spec["training"]["set"], "n": len(rows), "n_ipo": len(rows), "n_delta_ipo": len(ds.tickers),
        "n_pp_rows": ds.n_rows, "n_events": events, "n_survivals": ds.n_rows - events,
        "cutoff_date": max(d for r in rows for d in r.session_dates), "tickers": tickers,
        "tickers_sha256": identity_hash(tickers),
        "d1_fields_sha256": identity_hash([f"{t}|{d1[t].row.fields_raw['low']}|{d1[t].row.fields_raw['volume']}|"
                                           f"{d1[t].row.fields_raw['upper_limit']}|{d1[t].row.fields_raw['close']}" for t in tickers]),
        "data_version_sha256": dataset.data_version_sha256,
        "sessions_file_sha256": sha256_file(SESSIONS_PATH),
    }
    return build_params(parent=parent, parent_sha=parent_sha, path_sha=path_sha, prep=training.prep,
                        delta=training.fit.by_feature(), lam=training.selected_lambda, score_table=training.score_table,
                        solver={"iterations": training.fit.iterations, "grad_max": training.fit.grad_max},
                        training_block=block, runtime=runtime)


def build_params(*, parent: Mapping[str, Any], parent_sha: str, path_sha: str, prep: D1Prep, delta: Mapping[str, float],
                 lam: float, score_table: Sequence[Mapping[str, Any]], solver: Mapping[str, Any],
                 training_block: Mapping[str, Any], runtime: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Parametre sözlüğü (şartname §3.5): ofsetin sayıları yalnız `parent` nesnesinden (kopya alanlar + sha256), D1 ön
    işlemesi `prep`'ten, δ ve λ verilen değerlerden. `fit_params` ve testler (sabit δ) aynı kurucuyu kullanır."""
    spec = SPEC
    parent_ranges = {f: parent["feature_ranges"][f] for f in parent["features"]}
    return {
        "schema_version": SCHEMA_VERSION,
        "model_id": spec["model_id"],
        "algorithm": spec["algorithm"],
        "stage": spec["stage"],
        "description": spec["description"],
        "spec": dict(spec),
        "spec_sha256": spec_sha256(dict(spec)),
        "spec_document": {"path": spec["spec_document"]["path"], "sha256": sha256_file(ROOT / spec["spec_document"]["path"])},
        "features": list(spec["features"]),
        "parent": {"model_id": parent["model_id"], "file": spec["parent"]["file"], "sha256": parent_sha,
                   "gamma": parent["gamma"], "beta": parent["beta"],
                   "preprocessing_id": parent["preprocessing"]["preprocessing_id"]},
        "path_secondary": {"model_id": spec["path_secondary"]["model_id"], "file": spec["path_secondary"]["file"],
                           "sha256": path_sha},
        "updated_days": list(pd1.UPDATED_DAYS),
        "delta": {c: float(delta[c]) for c in D1_COLUMNS},
        "lambda": hz.lambda_label(lam),
        "lambda_score_table": [dict(e) for e in score_table],
        "solver": dict(solver),
        "d1_preprocessing": prep.params(),
        "feature_ranges": {**{c: prep.ranges[c] for c in D1_COLUMNS}, **parent_ranges},
        "training": dict(training_block),
        "horizons": {h: {"return": None, "p_up": None} for h in ("D1", "D3", "D5", "D10")},
        "input_policy": dict(spec["input_policy"]),
        "runtime": dict(runtime) if runtime is not None else None,
        "code_version": code_version(),
        "created_at": now_istanbul(),
    }


def final_predictions(dataset: Dataset, params: Mapping[str, Any], *, models_dir: Path = MODELS_DIR) -> dict[str, dict[str, Any]]:
    """Backtest kodunun nihai-model hesabı (numpy tarafı, kesin D1 dönüşümü) 81 eğitim arzında (§11-10 paritesi):
    δ ve λ `params`'tan, D1 ön işlemesi veriden yeniden."""
    parent, _ = load_frozen(SPEC["parent"], models_dir)
    ds, rows, d1 = final_delta_set(dataset, parent)
    prep = fit_d1_prep({t: ds.feats[t] for t in ds.tickers})
    delta = params["delta"]
    fit = DeltaFit(hz.lambda_parse(params["lambda"]), prep.columns, np.array([delta[c] for c in prep.columns], dtype=np.float64),
                   hz.CONVERGED)
    training = DeltaTraining(STATUS_FIT_OK, fit.lam, [], fit, prep)
    out = {}
    for r in rows:
        eta = ph.linear_predictor(parent, model_inputs_of(r))["eta"]
        out[r.ticker] = predict_with(eta, d1[r.ticker].values.features(), training, parent["reclose_rates"])
    return out


# ============================================================ altın ledger

GOLDEN_DESCRIPTION = ("Faz 5: post_d1_hazard_v0'ın (SPEC_POST_D1_V0) bu makinedeki H99 walk-forward fold ledger'ı; ofset o fold'un "
                      "ceiling_hazard_v0 fit'i (Faz 1B ledger'ıyla parite), fold kümesi Faz 1B tavan ledger'ınınki. Regresyon "
                      "testi buna karşı BİREBİR (bayt) çalışır; docs/MODELS.md Faz 5 bölümü bundan üretilir. Model DONDURULMADI.")


def golden_filename() -> str:
    return f"{MODEL_ID}_fold_ledger.csv"


FINAL_PREVIEW_FILE = f"{MODEL_ID}_final_fit_preview.json"


def write_golden(result: PostD1Result, preview: Mapping[str, Any], out_dir: Path = GOLDEN_FAZ5_DIR) -> dict[str, Any]:
    """Altın ledger + nihai fit önizlemesi + MANIFEST + SHA256SUMS. Var olan dosyanın üzerine yazmaz."""
    from .backtest import _platform
    from .provenance import runtime_versions

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    for name, payload in ((golden_filename(), result.ledger_csv), (FINAL_PREVIEW_FILE, pretty_json_bytes(dict(preview)))):
        path = out_dir / name
        if path.exists():
            raise PostD1Error(f"{path} zaten var; altın referans üzerine yazılmaz")
        path.write_bytes(payload)
        files[name] = sha256_file(path)
    manifest = {
        "description": GOLDEN_DESCRIPTION,
        "runs": {MODEL_ID: {"file": golden_filename(), "model_id": MODEL_ID, "plan_id": PLAN_POST_D1,
                            "spec_sha256": result.log_entry["spec_sha256"], "ledger_sha256": files[golden_filename()]}},
        "final_fit_preview": {"file": FINAL_PREVIEW_FILE, "sha256": files[FINAL_PREVIEW_FILE],
                              "note": "models/'e yazılmadı; dondurma görevi bit-eşitliği created_at, code_version ve runtime dışında sınar"},
        "log_entry": {"context": result.log_entry["context"], "started_at": result.log_entry["started_at"],
                      "ledger_sha256": result.log_entry["ledger_sha256"]},
        "runtime": runtime_versions(),
        "machine": {"platform": _platform()},
        "created_at": now_istanbul(),
        **code_version(),
    }
    (out_dir / "MANIFEST.json").write_bytes(pretty_json_bytes(manifest))
    (out_dir / "SHA256SUMS").write_text("".join(f"{sha}  {name}\n" for name, sha in sorted(files.items())), encoding="utf-8")
    return manifest


def main(argv: Optional[Sequence[str]] = None) -> int:
    from .data import load_dataset

    parser = argparse.ArgumentParser(description="post_d1_hazard_v0: walk-forward backtest (günlüğe yazılır) ve nihai fit önizlemesi.")
    parser.add_argument("--backtest", action="store_true", help="PLAN_POST_D1 walk-forward; experiments/log.jsonl'a satır ekler")
    parser.add_argument("--write-golden", action="store_true", help="tests/reference/macos_golden_faz5/ altına ledger + önizleme")
    parser.add_argument("--context", default="official")
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args(argv)
    if not args.backtest:
        parser.error("--backtest gerekli")
    dataset = load_dataset()
    result = run_backtest(dataset, log_path=DEFAULT_LOG_PATH, context=args.context, workers=args.workers)
    print(json.dumps({"run": MODEL_ID, "ledger_sha256": result.log_entry["ledger_sha256"],
                      "folds": result.log_entry["folds_scorable"], "metrics": result.metrics}, ensure_ascii=False))
    if args.write_golden:
        preview = fit_params(dataset)
        print(json.dumps(write_golden(result, preview), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

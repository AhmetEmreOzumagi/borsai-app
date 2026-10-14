"""Ayrık zamanlı hazard modeli: `ceiling_hazard_v0`, `pb_ceiling_v0`, Faz 7 `ceiling_hazard_v1_*` ve @INF uçları. numpy.

SPEC_CEILING_V0 §5, §12 (SPEC_PB_V0 §9 aynı kod, farklı özellik listesi ve kesim):

    logit h_d(x) = γ_{g(d)} + β·z(x),   g1 = {1}, g2 = {2, 3}, g3 = {4..10}
    J(γ, β) = −Σ_r w_r [e_r ln h_r + (1 − e_r) ln(1 − h_r)] + (λ/2)·‖β‖²

- r: gerçek PP satırları (w = 1) ve 6 pseudo-satır: her grup için z = 0'da bir
  event = 1 ve bir event = 0 satırı, w = 0.5. γ cezasız.
- Çözücü: tam Newton–Raphson; başlangıç β = 0, γ_g = logit((olay_g + 0.5)/(risk_g + 1));
  Δ = H⁻¹∇ (numpy.linalg.solve); J azalmıyorsa adım yarılanır (en çok 30 kez);
  dur: max|∇| ≤ 1e-10; 100 yinelemede durmazsa MODEL_NOT_FIT_DID_NOT_CONVERGE.
  "J azalmıyor" karşılaştırması, J'nin toplama yuvarlama sınırı (m·eps·max(|J|, 1))
  içinde yapılır (docs/SPEC_DEVIATIONS.md).
- λ = INF ya da hiç özellik kalmamışsa: β ≡ 0, γ kapalı biçim (pseudo-satırlı MLE'nin kendisi).
- λ seçimi: iç "bir arzı dışarıda bırak" CV; j'nin TÜM PP satırları dışarıda, ön işleme
  kalan arzlardan yeniden kurulur; skor = satır başına ortalama log-kayıp (h, [1e-12,
  1 − 1e-12]'ye kırpılır); en küçük skor, bit-eşit eşitlikte en büyük λ (INF en büyük).
  Bir λ'nın herhangi bir iç fit'i yakınsamazsa o λ o fold için çıkar; INF hep kalır.
- Ön işleme ARZ düzeyindedir (arz başına bir satır; borsai/preprocess.py tarifleri).

Faz 7 (SPEC_HAZARD_V1 §3.3, §4): tasarım matrisi X = [G (3 gün grubu) | R (0 ya da 1 sütun, cezasız) | Z (β, ceza λ)].
R = rejim terimi r = 1[tahsis rejimi ≠ EQUAL_DIST_20230330] (yalnız `ceiling_hazard_v1_pooled`); pseudo-satırlarda r = 0.
Newton başlangıcı γ kapalı biçim, δ = 0, β = 0. λ = INF (ya da hiç özellik yok) ve R varsa: β ≡ 0, (γ, δ) pseudo-satırlı
MLE'nin kendisi Newton ile (kapalı biçim yok). R yoksa her şey v0 ile aynı kod yolundan geçer (altın ledger'lar bayt-eşit).
f3 filtre adımı (SPEC_CEILING_V0 §4) + §7 "f3'ü boş arz eğitimde kullanılmaz" (proje sahibi kararı, SPEC_DEVIATIONS J):
bir eğitim kümesinde (iç CV dahil) f3'ü filtre moduna açıkça zıt olduğu için boşalacak birim o kümede kullanılmaz
(`f3_filter_excluded`); iç CV'de tutulan birimin f3'ü o iç eğitim kümesinin moduyla boşalıyorsa o birim skorlanmaz. H99'da
açık FILTERED durumu olmadığından v0/PB/v1_clip/v1_real'de hiç tetiklenmez.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

import numpy as np

from . import preprocess as pp
from . import survival as sv

INF = math.inf
LAMBDA_GRID: tuple[float, ...] = (0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, INF)
GRAD_TOL = 1e-10
MAX_ITER = 100
MAX_HALVINGS = 30
PSEUDO_WEIGHT = 0.5
H_CLIP = 1e-12
N_GROUPS = 3

CONVERGED = "CONVERGED"
STATUS_FIT_OK = "FIT_OK"
STATUS_NOT_CONVERGED = "MODEL_NOT_FIT_DID_NOT_CONVERGE"
CANDIDATE_NOT_CONVERGED = "CANDIDATE_NOT_CONVERGED"
SCORED = "SCORED"

_EPS = float(np.finfo(np.float64).eps)


def lambda_label(lam: float) -> Any:
    return "INF" if lam == INF else lam


def lambda_parse(value: Any) -> float:
    return INF if value == "INF" else float(value)


@dataclass
class SolverResult:
    theta: np.ndarray
    status: str
    iterations: int
    grad_max: float
    objective: float


@dataclass
class HazardFit:
    lam: float
    columns: tuple[str, ...]
    gamma: np.ndarray
    beta: np.ndarray
    status: str
    iterations: int = 0
    grad_max: float = 0.0
    delta: np.ndarray = field(default_factory=lambda: np.zeros(0))
    r_columns: tuple[str, ...] = ()

    def linear_predictors(self, z: Mapping[str, float], r: Optional[Mapping[str, float]] = None) -> list[float]:
        """η_d = γ_{g(d)} (+ δ·r) + β·z, d = 1..10 (`hazards` ile tek hesap yolu; D1 sonrası modelin fold ofseti).
        Rejim sütunu yoksa v0'ın aritmetiği aynen; varsa (γ + δ·r) + β·z (stdlib tahminle aynı sıra)."""
        lin = float(sum(b * z[c] for b, c in zip(self.beta, self.columns)))
        if not self.r_columns:
            return [float(self.gamma[sv.GROUP_OF_DAY[d]]) + lin for d in range(1, sv.DAYS + 1)]
        if r is None:
            raise ValueError("rejim terimli modelde r verilmedi")
        dr = float(sum(dl * r[c] for dl, c in zip(self.delta, self.r_columns)))
        return [float(self.gamma[sv.GROUP_OF_DAY[d]]) + dr + lin for d in range(1, sv.DAYS + 1)]

    def hazards(self, z: Mapping[str, float], r: Optional[Mapping[str, float]] = None) -> list[float]:
        return [sv.sigmoid(eta) for eta in self.linear_predictors(z, r)]


def _stable_sigmoid(eta: np.ndarray) -> np.ndarray:
    return np.exp(-np.logaddexp(0.0, -eta))


def design(groups: np.ndarray, Z: np.ndarray, R: Optional[np.ndarray] = None) -> np.ndarray:
    """X = [G | R | Z]; R None ya da 0 sütunluysa v0'ın matrisi aynen."""
    G = np.zeros((len(groups), N_GROUPS), dtype=np.float64)
    G[np.arange(len(groups)), groups] = 1.0
    if R is not None and R.shape[1]:
        return np.hstack([G, R, Z]) if Z.shape[1] else np.hstack([G, R])
    return np.hstack([G, Z]) if Z.shape[1] else G


def objective(X: np.ndarray, e: np.ndarray, w: np.ndarray, theta: np.ndarray, lam: float, n_free: int = N_GROUPS) -> float:
    """n_free: cezasız ilk sütun sayısı (γ ve varsa δ)."""
    eta = X @ theta
    value = float(np.sum(w * (np.logaddexp(0.0, eta) - e * eta)))
    beta = theta[n_free:]
    if beta.size:
        value += 0.5 * lam * float(beta @ beta)
    return value


def newton(X: np.ndarray, e: np.ndarray, w: np.ndarray, lam: float, theta0: np.ndarray, n_free: int = N_GROUPS) -> SolverResult:
    """Tam Newton–Raphson, adım yarılamalı. Dışbükey problem; ilk n_free sütun (γ, varsa δ) cezasız, β'ya λ."""
    p = X.shape[1] - n_free
    pen = np.concatenate([np.zeros(n_free), np.full(p, lam)])
    theta = theta0.astype(np.float64).copy()
    J = objective(X, e, w, theta, lam, n_free)
    noise = len(e) * _EPS
    grad_max = math.inf
    for it in range(MAX_ITER + 1):
        h = _stable_sigmoid(X @ theta)
        grad = X.T @ (w * (h - e)) + pen * theta
        grad_max = float(np.max(np.abs(grad)))
        if grad_max <= GRAD_TOL:
            return SolverResult(theta, CONVERGED, it, grad_max, J)
        if it == MAX_ITER or not math.isfinite(grad_max):
            break
        H = (X * (w * h * (1.0 - h))[:, None]).T @ X + np.diag(pen)
        try:
            delta = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            break
        step = 1.0
        for _ in range(MAX_HALVINGS + 1):
            candidate = theta - step * delta
            J_new = objective(X, e, w, candidate, lam, n_free)
            if J_new <= J + noise * max(abs(J), 1.0):
                break
            step *= 0.5
        else:
            break
        theta, J = candidate, J_new
    return SolverResult(theta, STATUS_NOT_CONVERGED, it, grad_max, J)


def fit_rows(
    groups: np.ndarray, Z: np.ndarray, events: np.ndarray, lam: float, columns: Sequence[str], *, pseudo: bool = True,
    R: Optional[np.ndarray] = None, r_columns: Sequence[str] = (),
) -> HazardFit:
    """Bir satır kümesine hazard fit'i. Z: (m, p) z-skorları, columns ile aynı sıra. R: (m, q) cezasız rejim sütunları
    (q = 0 ya da 1; pseudo-satırlarda 0). R yoksa v0 kod yolu aynen."""
    m, p = Z.shape
    q = 0 if R is None else R.shape[1]
    ev = np.bincount(groups, weights=events, minlength=N_GROUPS)
    risk = np.bincount(groups, minlength=N_GROUPS)
    gamma0 = np.array([sv.closed_form_gamma(int(ev[g]), int(risk[g])) for g in range(N_GROUPS)], dtype=np.float64)
    if q == 0:
        if pseudo and (lam == INF or p == 0):
            return HazardFit(lam, tuple(columns), gamma0, np.zeros(p), CONVERGED)
        w = np.ones(m, dtype=np.float64)
        if pseudo:
            groups = np.concatenate([groups, np.repeat(np.arange(N_GROUPS), 2)])
            events = np.concatenate([events, np.tile([1.0, 0.0], N_GROUPS)])
            w = np.concatenate([w, np.full(2 * N_GROUPS, PSEUDO_WEIGHT)])
            Z = np.vstack([Z, np.zeros((2 * N_GROUPS, p))])
        X = design(groups, Z)
        res = newton(X, events.astype(np.float64), w, 0.0 if lam == INF else lam, np.concatenate([gamma0, np.zeros(p)]))
        return HazardFit(lam, tuple(columns), res.theta[:N_GROUPS].copy(), res.theta[N_GROUPS:].copy(), res.status,
                         res.iterations, res.grad_max)
    if len(r_columns) != q:
        raise ValueError("r_columns R'nin sütun sayısıyla aynı değil")
    w = np.ones(m, dtype=np.float64)
    if pseudo:
        groups = np.concatenate([groups, np.repeat(np.arange(N_GROUPS), 2)])
        events = np.concatenate([events, np.tile([1.0, 0.0], N_GROUPS)])
        w = np.concatenate([w, np.full(2 * N_GROUPS, PSEUDO_WEIGHT)])
        Z = np.vstack([Z, np.zeros((2 * N_GROUPS, p))])
        R = np.vstack([R, np.zeros((2 * N_GROUPS, q))])
    n_free = N_GROUPS + q
    if lam == INF or p == 0:                       # β ≡ 0; (γ, δ) Newton (SPEC_HAZARD_V1 §3.3)
        X = design(groups, Z[:, :0], R)
        res = newton(X, events.astype(np.float64), w, 0.0, np.concatenate([gamma0, np.zeros(q)]), n_free)
        beta = np.zeros(p)
    else:
        X = design(groups, Z, R)
        res = newton(X, events.astype(np.float64), w, lam, np.concatenate([gamma0, np.zeros(q), np.zeros(p)]), n_free)
        beta = res.theta[n_free:].copy()
    return HazardFit(lam, tuple(columns), res.theta[:N_GROUPS].copy(), beta, res.status, res.iterations, res.grad_max,
                     delta=res.theta[N_GROUPS:n_free].copy(), r_columns=tuple(r_columns))


def row_nll(fit: HazardFit, groups: np.ndarray, Z: np.ndarray, events: np.ndarray,
            R: Optional[np.ndarray] = None) -> np.ndarray:
    if fit.r_columns:
        eta = fit.gamma[groups] + R @ fit.delta + (Z @ fit.beta if Z.shape[1] else 0.0)
    else:
        eta = fit.gamma[groups] + (Z @ fit.beta if Z.shape[1] else 0.0)
    h = np.clip(_stable_sigmoid(eta), H_CLIP, 1.0 - H_CLIP)
    return -(events * np.log(h) + (1.0 - events) * np.log(1.0 - h))


# ---------------------------------------------------------------------------
# Eğitim kümesi (fold ya da nihai fit)
# ---------------------------------------------------------------------------

@dataclass
class _Prepared:
    prep: Optional[pp.FittedPreprocessing]
    columns: tuple[str, ...]
    z: dict[str, dict[str, float]]


def _prepare(tickers: Sequence[str], raw: Mapping[str, Mapping], status: Mapping[str, Optional[str]],
             features: Sequence[str], recipe: Optional[pp.Recipe]) -> _Prepared:
    if not features:
        return _Prepared(None, (), {t: {} for t in tickers})
    prep = pp.fit_preprocessing({t: raw[t] for t in tickers}, {t: status.get(t) for t in tickers}, recipe=recipe)
    if prep.insufficient_feature_variation:
        return _Prepared(prep, (), {t: {} for t in tickers})
    return _Prepared(prep, prep.columns, {t: prep.train_matrix[t] for t in tickers})


def _arrays(rows: Sequence[sv.PPRow], z: Mapping[str, Mapping[str, float]], columns: Sequence[str]):
    groups = np.array([r.group for r in rows], dtype=np.intp)
    events = np.array([r.event for r in rows], dtype=np.float64)
    Z = np.array([[z[r.ticker][c] for c in columns] for r in rows], dtype=np.float64).reshape(len(rows), len(columns))
    return groups, Z, events


def _regime_array(rows: Sequence[sv.PPRow], regime: Optional[Mapping[str, Mapping[str, float]]],
                  r_columns: Sequence[str]) -> Optional[np.ndarray]:
    """(m, q) cezasız rejim sütunları (arz sabiti; PP satırına arzından kopya). Rejimsiz modelde None."""
    if not r_columns:
        return None
    return np.array([[float(regime[r.ticker][c]) for c in r_columns] for r in rows], dtype=np.float64).reshape(len(rows), len(r_columns))


def f3_filter_excluded(tickers: Sequence[str], raw: Mapping[str, Mapping], status: Mapping[str, Optional[str]]) -> tuple[str, ...]:
    """Bu eğitim kümesinde f3'ü ön işlemenin filtre adımında boşalacak birimler (SPEC_CEILING_V0 §4 + §7; SPEC_DEVIATIONS J):
    kümenin f3'lü birimlerinin filtre modu (`preprocess.filter_mode`) açık ve birimin durumu ona açıkça zıt. İmputasyonsuz tavan
    tariflerinde bu birimler o kümede kullanılmaz. Mod `fit_preprocessing` adım 1'inkiyle aynı küme ve kuralla hesaplanır; bu
    birimler çıkarılınca mod değişmez ve başka birim boşalmaz. f3 kullanmayan (PB, @INF) kümelerde boş."""
    present = [t for t in tickers if raw[t].get("f3") is not None]
    mode, _ = pp.filter_mode([status.get(t) for t in present])
    return tuple(t for t in present if pp.opposite_explicit_status(status.get(t), mode))


def _held_out_nulled(prepared: _Prepared, raw_j: Mapping, status_j: Optional[str]) -> bool:
    """İç CV'de tutulan birimin f3'ü iç eğitim kümesinin moduyla boşalıyor mu (`FittedPreprocessing.transform` koşulu)."""
    prep = prepared.prep
    return bool(prepared.columns and raw_j.get("f3") is not None and "f3" in prep.active_after_missingness
                and pp.opposite_explicit_status(status_j, prep.f3_filter_mode_after))


def select_lambda(
    tickers: Sequence[str], rows_by: Mapping[str, list[sv.PPRow]], raw: Mapping[str, Mapping],
    status: Mapping[str, Optional[str]], features: Sequence[str], recipe: Optional[pp.Recipe], grid: Sequence[float],
    regime: Optional[Mapping[str, Mapping[str, float]]] = None, r_columns: Sequence[str] = (),
) -> tuple[float, list[dict[str, Any]]]:
    totals = {lam: 0.0 for lam in grid}
    failed: set[float] = set()
    n_rows = 0
    for j in tickers:
        inner = [t for t in tickers if t != j]
        excluded = set(f3_filter_excluded(inner, raw, status))
        if excluded:
            inner = [t for t in inner if t not in excluded]
        prepared = _prepare(inner, raw, status, features, recipe)
        if _held_out_nulled(prepared, raw[j], status.get(j)):
            continue                                # f3'ü bu iç kümede kullanılamaz: skorlanmaz (SPEC_DEVIATIONS J)
        inner_rows = [r for t in inner for r in rows_by[t]]
        g, Z, e = _arrays(inner_rows, prepared.z, prepared.columns)
        R = _regime_array(inner_rows, regime, r_columns)
        zj = prepared.prep.transform(raw[j], status.get(j))["z"] if prepared.columns else {}
        gj, Zj, ej = _arrays(rows_by[j], {j: zj}, prepared.columns)
        Rj = _regime_array(rows_by[j], regime, r_columns)
        for lam in grid:
            if lam in failed:
                continue
            fit = fit_rows(g, Z, e, lam, prepared.columns, R=R, r_columns=r_columns) if r_columns else \
                fit_rows(g, Z, e, lam, prepared.columns)
            if fit.status != CONVERGED:
                failed.add(lam)
                continue
            totals[lam] += float(np.sum(row_nll(fit, gj, Zj, ej, Rj)))
        n_rows += len(rows_by[j])
    table = []
    for lam in grid:
        if lam in failed:
            table.append({"lambda": lambda_label(lam), "score": None, "status": CANDIDATE_NOT_CONVERGED})
        else:
            table.append({"lambda": lambda_label(lam), "score": totals[lam] / n_rows, "status": SCORED})
    return choose_lambda(table), table


def choose_lambda(table: Sequence[Mapping[str, Any]]) -> float:
    """En küçük skor; bit-eşit eşitlikte en büyük λ (INF en büyük). Yakınsamayan aday yok sayılır."""
    scored = [(lambda_parse(e["lambda"]), e["score"]) for e in table if e["status"] == SCORED]
    best = min(s for _, s in scored)
    return max(lam for lam, s in scored if s == best)


@dataclass
class TrainingResult:
    status: str
    features: tuple[str, ...]
    selected_lambda: Optional[float]
    score_table: list[dict[str, Any]]
    fit: Optional[HazardFit]
    prepared: _Prepared
    n_ipo: int
    n_pp_rows: int
    n_events: int
    n_survivals: int
    reclose: dict[str, float]
    max_session_date: Optional[str]
    rows: list[sv.PPRow] = field(default_factory=list)
    r_columns: tuple[str, ...] = ()
    excluded: tuple[str, ...] = ()               # f3 filtre dışlaması (bu kümede kullanılmayan birimler)

    def beta_by_feature(self) -> dict[str, float]:
        """Şartnamedeki her özellik için katsayı; bu fit'te düşen özellik 0."""
        got = dict(zip(self.fit.columns, (float(b) for b in self.fit.beta))) if self.fit else {}
        return {f: got.get(f, 0.0) for f in self.features}

    def delta_by_column(self) -> dict[str, float]:
        return {c: float(d) for c, d in zip(self.fit.r_columns, self.fit.delta)} if self.fit else {}

    def predict(self, test_raw: Mapping, test_status: Optional[str], test_r: Optional[Mapping[str, float]] = None) -> dict[str, Any]:
        """`clipped` = herhangi bir sütun eğitim [p05, p95]'ine kırpıldı (SPEC_HAZARD_V1 §3.1); v0/PB tarifinde kırpılan tek
        sütun f3'tür, bayrak eskisiyle aynı (Fable denetimi B1)."""
        z, clipped, clipped_features = {}, None, None
        if self.prepared.columns:
            t = self.prepared.prep.transform(test_raw, test_status)
            clipped_features = [f for f in self.prepared.columns if t["winsorized"].get(f)]
            z, clipped = t["z"], bool(clipped_features)
        hazards = self.fit.hazards(z, test_r) if self.r_columns else self.fit.hazards(z)
        S = sv.survival(hazards)
        return {"hazards": hazards, "S": S, "P_L": sv.p_streak(S),
                "P_close": sv.p_close(S, self.reclose["r_a"], self.reclose["r_b"]), "z": z, "clipped": clipped,
                "clipped_features": clipped_features}


def fit_training_set(
    units: Sequence[sv.Unit], raw: Mapping[str, Mapping], status: Mapping[str, Optional[str]], *,
    cutoff: Optional[str], features: Sequence[str], recipe: Optional[pp.Recipe], grid: Sequence[float] = LAMBDA_GRID,
    regime: Optional[Mapping[str, Mapping[str, float]]] = None, r_columns: Sequence[str] = (),
) -> TrainingResult:
    """Eğitim arzları (sıralı) -> λ seçimi + nihai fit. Kesim: PP satırı ancak seans tarihi < cutoff ise. `regime`:
    ticker -> {rejim sütunu: değer} (yalnız rejim terimli model; `r_columns` sırası). f3'ü filtreyle boşalacak birimler
    (`f3_filter_excluded`) bu kümede kullanılmaz (H99'da hiç yok; plan zaten dışarıda bırakmışsa boş)."""
    rows = sv.pp_table(units, cutoff)
    rows_by: dict[str, list[sv.PPRow]] = {}
    for r in rows:
        rows_by.setdefault(r.ticker, []).append(r)
    tickers = [u.ticker for u in units if u.ticker in rows_by]
    excluded = f3_filter_excluded(tickers, raw, status) if features else ()
    if excluded:
        units = [u for u in units if u.ticker not in excluded]
        rows = [r for r in rows if r.ticker not in excluded]
        rows_by = {t: v for t, v in rows_by.items() if t not in excluded}
        tickers = [t for t in tickers if t not in excluded]
    used_dates = [u.session_dates[r.day - 1] for u in units for r in rows_by.get(u.ticker, [])]
    n_events = sum(r.event for r in rows)
    common = dict(features=tuple(features), n_ipo=len(tickers), n_pp_rows=len(rows), n_events=n_events,
                  n_survivals=len(rows) - n_events, reclose=sv.reclose_counts([u for u in units if u.ticker in rows_by], cutoff),
                  max_session_date=max(used_dates) if used_dates else None, rows=rows)
    if len(grid) > 1:
        if r_columns:
            selected, table = select_lambda(tickers, rows_by, raw, status, features, recipe, grid, regime, r_columns)
        else:
            selected, table = select_lambda(tickers, rows_by, raw, status, features, recipe, grid)
    else:
        selected, table = grid[0], []
    prepared = _prepare(tickers, raw, status, features, recipe)
    g, Z, e = _arrays(rows, prepared.z, prepared.columns)
    if r_columns:
        fit = fit_rows(g, Z, e, selected, prepared.columns, R=_regime_array(rows, regime, r_columns), r_columns=r_columns)
    else:
        fit = fit_rows(g, Z, e, selected, prepared.columns)
    st = STATUS_FIT_OK if fit.status == CONVERGED else STATUS_NOT_CONVERGED
    return TrainingResult(status=st, selected_lambda=selected, score_table=table, fit=fit, prepared=prepared,
                          r_columns=tuple(r_columns), excluded=tuple(excluded), **common)

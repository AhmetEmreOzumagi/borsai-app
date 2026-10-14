"""Tavan yolu modelleri (SPEC_CEILING_PATH_V0): `ceiling_path_v0`, `ceiling_path_v0@INF`,
`pb_ceiling_path_v0`. Yalnız stdlib; seri bileşeni için borsai/predict_hazard.py çağrılır.

R_h'nin öngörü dağılımı (h = 1..10) ayrık atomlardır (§4):
  limit yolu atomu   (ρ_h, S_h)
  t = 0              (v, P(L = 0) / n),                     v ∈ hücre(Z, h)
  t = 1..h−1         ((C_t/P)·(1 + v) − 1, P(L = t) / n),   v ∈ hücre(B, h − t)
Nokta tahmini = karışımın MEDYANI (alt kuantil kuralı), p_up = Σ{w : r > 0}, kuantiller %10/%50/%90.

- S_k gömülü (dondurulmuş, sha'sı INDEX'le aynı) seri modelinden `predict_hazard.predict` ile gelir;
  ret ve uyarıları aynen geçer (ana model f3 yoksa F3_MISSING, PB varyantında PB ret kodları).
- Limit yolu C_h (§2): fiyat adımı tablosu, üst limit aşağı adıma (adım, yuvarlanacak değerin kendi
  seviyesinden), D1 baz fiyatı arz fiyatının HALF_UP ile adıma oturtulmuş hali. Kesin Decimal.
- Kırılma sonrası hücreler G(g, m) (§3): g ∈ {Z (t = 0), B (1 ≤ t ≤ 9)}, m = son limit-yolu gününden
  bu yana geçen seans; deterministik havuzlama merdiveni, N_MIN = 10; havuzlanan değer hedef m'nin
  fiziksel sınırına kırpılır (sınırlar kesin Decimal'den bir kez binary64'e).
- Koşullu güncelleme (§7): `conditional` (seri j. günde sürüyor) ve `conditional_after_break`
  (seri t. günde kırıldı); `conditional_rps`, `conditional_brier` (canlı koşullu skor tanımı).
Bütün karışım aritmetiği binary64; C_t/P ve kırılma sonrası getiriler Decimal'den bir kez float'a.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import (ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal, DivisionByZero,
                     Inexact, InvalidOperation, Overflow, localcontext)
from typing import Any, Mapping, Optional, Sequence

from . import predict_hazard as ph
from . import survival as sv
from .features import FeatureError, PBRefusal, parse_decimal, parse_pb_decimal

ALGORITHM = "CEILING_PATH_MIXTURE_EQ_V0"
DAYS = sv.DAYS
HORIZON_KEYS: tuple[str, ...] = tuple(f"D{h}" for h in range(1, DAYS + 1))

# §2: fiyat adımı tablosu (paylar) ve fiyat marjı; JSON'da da yazılıdır ve burada denetlenir.
MARGIN = "0.10"
TICK_TABLE: tuple[tuple[Optional[str], str], ...] = (
    ("20", "0.01"), ("50", "0.02"), ("100", "0.05"), ("250", "0.10"), ("500", "0.25"), ("1000", "0.50"),
    ("2500", "1.00"), (None, "2.50"),
)
UPPER_ROUNDING = "FLOOR_TO_TICK_AT_LIMIT_LEVEL"
LOWER_ROUNDING = "CEIL_TO_TICK_AT_LIMIT_LEVEL"
D1_BASE = "HALF_UP_TO_TICK"
PRICE_FIELDS = ("ipo_price_tl", "ipo_price_try")

# §3: kırılma sonrası hücreler.
N_MIN = 10
GROUPS: tuple[str, ...] = ("Z", "B")
M_MAX = {"Z": DAYS, "B": DAYS - 1}
QUANTILE_EPS = 1e-12
QUANTILES = {"q10": 0.1, "q50": 0.5, "q90": 0.9}

STATUS_OK = "OK"
STATUS_POST_BREAK_INSUFFICIENT = "POST_BREAK_INSUFFICIENT"
STATUS_REALIZED = "REALIZED"
STATE_STREAK_ONGOING = "STREAK_ONGOING"
STATE_AFTER_BREAK = "AFTER_BREAK"
WARN_IPO_PRICE_NOT_ON_TICK_GRID = "IPO_PRICE_NOT_ON_TICK_GRID"

_MARGIN = Decimal(MARGIN)
_TICKS = tuple((None if lim is None else Decimal(lim), Decimal(s)) for lim, s in TICK_TABLE)
# Limit aritmetiği kesin: Inexact tuzağı açık (adımlar yalnız 2 ve 5 çarpanlı; bölmeler sonlu).
_EXACT = Context(prec=60, rounding=ROUND_HALF_EVEN, traps=[InvalidOperation, DivisionByZero, Overflow, Inexact])
# Oranlar (C/P, kapanış/baz): 60 hane, sonra bir kez binary64.
_RATIO = Context(prec=60, rounding=ROUND_HALF_EVEN, traps=[InvalidOperation, DivisionByZero, Overflow])

PredictError = ph.PredictError


# ============================================================ §2 limit yolu

def tick(x: Decimal) -> Decimal:
    """x'in düştüğü fiyat seviyesinin adımı: [0.01, 20) → 0.01 … ≥ 2500 → 2.50."""
    for lim, s in _TICKS:
        if lim is None or x < lim:
            return s
    raise AssertionError("tablo sonu")  # pragma: no cover


def upper_limit(base: Decimal) -> Decimal:
    """U(b) = floor(b·1.10 / adım(b·1.10)) · adım(b·1.10): üst limit aşağı adıma."""
    with localcontext(_EXACT):
        y = base * (1 + _MARGIN)
        s = tick(y)
        return (y / s).to_integral_value(rounding=ROUND_FLOOR) * s


def lower_limit(base: Decimal) -> Decimal:
    """Lo(b) = ceil(b·0.90 / adım(b·0.90)) · adım(b·0.90): alt limit yukarı adıma (yalnız test/uygulama bilgisi)."""
    with localcontext(_EXACT):
        y = base * (1 - _MARGIN)
        s = tick(y)
        return (y / s).to_integral_value(rounding=ROUND_CEILING) * s


def snap(price: Decimal) -> Decimal:
    """D1 baz fiyatı: arz fiyatı kendi seviyesinin adımına HALF_UP ile oturtulur."""
    with localcontext(_EXACT):
        s = tick(price)
        return (price / s).to_integral_value(rounding=ROUND_HALF_UP) * s


def ratio(a: Decimal, b: Decimal) -> float:
    """float(a / b), 60 haneden bir kez binary64'e."""
    with localcontext(_RATIO):
        return float(a / b)


def ratio_minus_one(a: Decimal, b: Decimal) -> float:
    """float(a / b − 1), 60 haneden bir kez binary64'e."""
    with localcontext(_RATIO):
        return float(a / b - 1)


def limit_path(price: Decimal) -> dict[str, Any]:
    """C_0 = P; b_1 = snap(P); C_1 = U(b_1); C_k = U(C_{k−1}); ρ_k = C_k / P − 1."""
    snapped = snap(price)
    C: list[Decimal] = []
    b = snapped
    for _ in range(DAYS):
        b = upper_limit(b)
        C.append(b)
    return {"ipo_price": price, "snapped_ipo_price": snapped, "tick": tick(price), "C": C,
            "rho": [ratio_minus_one(c, price) for c in C], "scale": [ratio(c, price) for c in C]}


def rho_max(price: Decimal, snapped: Decimal, h: int) -> float:
    """Etkin üst sınır ρ_h^max = 1.1^h · snap(P)/P − 1 (§2 sınır notu)."""
    with localcontext(_RATIO):
        return float((1 + _MARGIN) ** h * snapped / price - 1)


def physical_bounds(m: int) -> tuple[float, float]:
    """(0.9^m − 1, 1.1^m − 1), kesin Decimal'den bir kez binary64'e."""
    with localcontext(_RATIO):
        return float((1 - _MARGIN) ** m - 1), float((1 + _MARGIN) ** m - 1)


def tick_table_json() -> list[dict[str, Optional[str]]]:
    return [{"below": lim, "tick": s} for lim, s in TICK_TABLE]


# ============================================================ §3 kırılma sonrası hücreler

@dataclass(frozen=True)
class PathUnit:
    """Hücre kurulumu için bir arz: seri L, arz fiyatı ve D1..D10 resmi kapanış/seans tarihi."""

    ticker: str
    first_trading_date: str
    streak: int                        # L ∈ 0..10
    ipo_price: Decimal
    closes: tuple[Decimal, ...]        # D1..D10 resmi THB kapanışı
    session_dates: tuple[str, ...]     # D1..D10


def group_of(t: int) -> str:
    return "Z" if t == 0 else "B"


def valid_cell(group: str, m: int) -> bool:
    return group in M_MAX and 1 <= m <= M_MAX[group]


def empty_cells() -> dict[tuple[str, int], list[tuple[float, str]]]:
    return {(g, m): [] for g in GROUPS for m in range(1, M_MAX[g] + 1)}


def build_cells(units: Sequence[PathUnit], cutoff: Optional[str] = None) -> tuple[dict[tuple[str, int], list[tuple[float, str]]], dict[str, Any]]:
    """§3: L = t < 10 olan her arz için m = 1..10 − t; seans(D_{t+m}) ≥ kesim ise durulur (kesin öncelik).
    G = kapanış(D_{t+m}) / baz − 1, baz = P (t = 0) ya da kapanış(D_t). Listeler (değer, ticker) artan.
    İkinci öğe: {max_session_date, contributors (unit sırası), n_obs}."""
    cells = empty_cells()
    max_date: Optional[str] = None
    contributors: list[str] = []
    for u in units:
        t = u.streak
        if t >= DAYS:
            continue
        base = u.ipo_price if t == 0 else u.closes[t - 1]
        added = False
        for m in range(1, DAYS - t + 1):
            d = u.session_dates[t + m - 1]
            if cutoff is not None and d >= cutoff:
                break
            cells[(group_of(t), m)].append((ratio_minus_one(u.closes[t + m - 1], base), u.ticker))
            max_date = d if max_date is None or d > max_date else max_date
            added = True
        if added:
            contributors.append(u.ticker)
    out = {k: sorted(v) for k, v in cells.items()}
    return out, {"max_session_date": max_date, "contributors": contributors, "n_obs": sum(len(v) for v in out.values())}


def cells_to_json(cells: Mapping[tuple[str, int], Sequence[tuple[float, str]]]) -> dict[str, dict[str, list[list[Any]]]]:
    return {g: {str(m): [[v, tk] for v, tk in cells[(g, m)]] for m in range(1, M_MAX[g] + 1)} for g in GROUPS}


def cells_from_json(doc: Mapping[str, Mapping[str, Sequence[Sequence[Any]]]]) -> dict[tuple[str, int], list[tuple[float, str]]]:
    return {(g, int(m)): [(float(v), str(tk)) for v, tk in lst] for g in GROUPS for m, lst in doc[g].items()}


@dataclass(frozen=True)
class PooledCell:
    """Hedef hücre (g, m) için merdivenin sonucu. `values` hedef m'nin sınırına kırpılmıştır;
    `origins[i]` i. değerin geldiği hücre; `sources` merdivende bakılan geçerli hücreler, sırayla."""

    group: str
    m: int
    values: tuple[float, ...]
    tickers: tuple[str, ...]
    origins: tuple[tuple[str, int], ...]
    sources: tuple[tuple[str, int], ...]
    n_clipped: int
    sufficient: bool

    @property
    def n(self) -> int:
        return len(self.values)

    @property
    def pooled(self) -> bool:
        return len(self.sources) > 1

    def as_json(self) -> dict[str, Any]:
        return {"group": self.group, "m": self.m, "n": self.n, "pooled": self.pooled,
                "sources": [[g, m] for g, m in self.sources]}


def ladder(group: str, m: int) -> list[list[tuple[str, int]]]:
    """§3 merdiveni: [kendi], [diğer grup aynı m], sonra m−1, m+1, m−2, m+2, … (her adımda iki grup, Z sonra B);
    geçersiz hücreler atlanır (Z m = 10'un B karşılığı yok)."""
    other = "B" if group == "Z" else "Z"
    steps = [[(group, m)], [(other, m)]]
    for d in range(1, DAYS):
        for mm in (m - d, m + d):
            steps.append([(g, mm) for g in GROUPS])
    return [[k for k in step if valid_cell(*k)] for step in steps]


def pool(cells: Mapping[tuple[str, int], Sequence[tuple[float, str]]], group: str, m: int, n_min: int = N_MIN) -> PooledCell:
    """Deterministik havuzlama: her adım bir hücre grubu, adım sonunda n ≥ N_MIN ise durulur. Bütün hücreler
    tükenip n < N_MIN kalırsa `sufficient = False` (POST_BREAK_INSUFFICIENT)."""
    if not valid_cell(group, m):
        raise ValueError(f"geçersiz hücre ({group}, {m})")
    gathered: list[tuple[float, str, tuple[str, int]]] = []
    sources: list[tuple[str, int]] = []
    for step in ladder(group, m):
        for key in step:
            sources.append(key)
            gathered += [(v, tk, key) for v, tk in cells.get(key, ())]
        if len(gathered) >= n_min:
            break
    lo, hi = physical_bounds(m)
    values = tuple(min(max(v, lo), hi) for v, _, _ in gathered)
    return PooledCell(group=group, m=m, values=values, tickers=tuple(tk for _, tk, _ in gathered),
                      origins=tuple(k for _, _, k in gathered), sources=tuple(sources),
                      n_clipped=sum(1 for (v, _, _), c in zip(gathered, values) if v != c),
                      sufficient=len(gathered) >= n_min)


# ============================================================ §4 karışım

def mixture_atoms(limit_atom: Optional[tuple[float, float]], parts: Sequence[tuple[int, float, Optional[float]]],
                  cells: Mapping[tuple[str, int], Sequence[tuple[float, str]]], h: int
                  ) -> tuple[list[tuple[float, float]], list[PooledCell], bool]:
    """Atom listesi (ekleme sırası): limit atomu, sonra her parça (t, toplam ağırlık, ölçek) için hücre(g(t), h − t)
    atomları; ölçek None ise atom v (t = 0), değilse ölçek·(1 + v) − 1; ağırlık toplam/n."""
    atoms: list[tuple[float, float]] = [] if limit_atom is None else [limit_atom]
    used: list[PooledCell] = []
    for t, weight, scale in parts:
        pc = pool(cells, group_of(t), h - t)
        used.append(pc)
        if not pc.sufficient:
            return atoms, used, False
        w = weight / pc.n
        atoms += [(v if scale is None else scale * (1 + v) - 1, w) for v in pc.values]
    return atoms, used, True


def summarize(atoms: Sequence[tuple[float, float]]) -> dict[str, float]:
    """Kuantil kuralı (§4): (r, ekleme sırası) artan; F ≥ q − 1e-12 sağlayan ilk atomun r'si."""
    ordered = sorted(atoms, key=lambda a: a[0])

    def q(p: float) -> float:
        cum = 0.0
        for r, w in ordered:
            cum += w
            if cum >= p - QUANTILE_EPS:
                return r
        return ordered[-1][0]

    out = {"return": q(0.5), "p_up": sum(w for r, w in ordered if r > 0), "mean": sum(r * w for r, w in ordered)}
    out.update({name: q(p) for name, p in QUANTILES.items()})
    return out


def _horizon(atoms, used, ok, *, limit_return: Optional[float], S_h: Optional[float]) -> dict[str, Any]:
    out: dict[str, Any] = {"return": None, "p_up": None, "mean": None, "q10": None, "q50": None, "q90": None}
    if ok:
        out.update(summarize(atoms))
    out.update({"limit_path_return": limit_return, "S_h": S_h, "p_limit_path": S_h, "n_atoms": len(atoms) if ok else 0,
                "post_break": {"cells": [c.as_json() for c in used],
                               "status": STATUS_OK if ok else STATUS_POST_BREAK_INSUFFICIENT}})
    return out


def horizon_prediction(S: Sequence[float], P_L: Sequence[float], scale: Sequence[float], rho: Sequence[float],
                       cells: Mapping[tuple[str, int], Sequence[tuple[float, str]]], h: int) -> dict[str, Any]:
    """Koşulsuz D_h çıktısı. scale[t − 1] = float(C_t / P)."""
    parts = [(t, P_L[t], None if t == 0 else scale[t - 1]) for t in range(h)]
    atoms, used, ok = mixture_atoms((rho[h - 1], S[h - 1]), parts, cells, h)
    return _horizon(atoms, used, ok, limit_return=rho[h - 1], S_h=S[h - 1])


# ============================================================ predict

def _check_params(params: Mapping[str, Any]) -> None:
    if not isinstance(params, Mapping):
        raise PredictError("PARAMS_INVALID", "params bir sözlük değil")
    if params.get("schema_version") not in ph.SUPPORTED_SCHEMA_VERSIONS:
        raise PredictError("SCHEMA_UNSUPPORTED", f"schema_version={params.get('schema_version')!r}")
    if params.get("algorithm") != ALGORITHM:
        raise PredictError("PARAMS_INVALID", f"tavan yolu modeli değil: {params.get('algorithm')!r}")
    surv = params.get("survival_model")
    if not isinstance(surv, Mapping) or surv.get("model_id") != params.get("survival_model_id") \
            or surv.get("algorithm") != ph.HAZARD_ALGORITHM:
        raise PredictError("PARAMS_INVALID", "gömülü seri modeli yok ya da kimliği tutmuyor")
    lp = params.get("limit_path") or {}
    if (lp.get("margin"), lp.get("tick_table"), lp.get("upper_rounding"), lp.get("d1_base")) != \
            (MARGIN, tick_table_json(), UPPER_ROUNDING, D1_BASE) or lp.get("price_field") not in PRICE_FIELDS:
        raise PredictError("PARAMS_INVALID", "limit yolu sabitleri şartnameyle aynı değil")
    pbk = params.get("post_break") or {}
    if pbk.get("N_MIN") != N_MIN or list(pbk.get("groups", [])) != list(GROUPS):
        raise PredictError("PARAMS_INVALID", "kırılma sonrası sabitleri şartnameyle aynı değil")
    cells = pbk.get("cells")
    if not isinstance(cells, Mapping) or any(set(cells.get(g, {})) != {str(m) for m in range(1, M_MAX[g] + 1)} for g in GROUPS):
        raise PredictError("PARAMS_INVALID", "hücre anahtarları Z 1..10 / B 1..9 değil")


def _price(field: str, value: Any) -> Decimal:
    """Arz fiyatı (limit yolu için). Hatalıysa etiketli ret: FeatureError (V1.5 alanı) ya da PBRefusal (PB alanı)."""
    if field == "ipo_price_try":
        p = parse_pb_decimal(value, field)
        if p <= 0:
            raise PBRefusal("PB_IDENTITY", "VALUE_POSITIVE", "arz fiyatı pozitif değil")
        return p
    p = parse_decimal(value, field)
    if p <= 0:
        raise FeatureError("INPUT_NOT_POSITIVE", field, f"pozitif olmalı: {p}")
    return p


def cells_of(params: Mapping[str, Any]) -> dict[tuple[str, int], list[tuple[float, str]]]:
    return cells_from_json(params["post_break"]["cells"])


def predict(params: Mapping[str, Any], inputs: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Dönen: {"model_id", "refused", "warnings", "clipped", "hazard", "S", "P_L", "P_close_ceiling",
    "limit_path": {ipo_price, snapped_ipo_price, tick, C, rho} | None, "D1".."D10": {...} | None}."""
    _check_params(params)
    inputs = inputs or {}
    surv = ph.predict(params["survival_model"], inputs)
    out: dict[str, Any] = {"model_id": params.get("model_id"), "refused": None, "warnings": list(surv["warnings"]),
                           "clipped": surv["clipped"], "hazard": surv["hazard"], "S": surv["S"], "P_L": surv["P_L"],
                           "P_close_ceiling": surv["P_close_ceiling"], "limit_path": None}
    for key in HORIZON_KEYS:
        out[key] = None
    if surv["refused"]:
        out["refused"] = surv["refused"]
        return out
    field = params["limit_path"]["price_field"]
    try:
        P = _price(field, inputs.get(field))
    except (FeatureError, PBRefusal) as exc:
        out.update(refused={"code": exc.code, "field": exc.field, "reason": str(exc)}, hazard=None, S=None, P_L=None,
                   P_close_ceiling=None, clipped=None)
        return out
    lp = limit_path(P)
    if lp["snapped_ipo_price"] != P:
        out["warnings"].append(ph._warn(
            WARN_IPO_PRICE_NOT_ON_TICK_GRID,
            f"arz fiyatı {P} fiyat adımı ızgarasında değil (adım {lp['tick']}); D1 baz fiyatı {lp['snapped_ipo_price']} alındı",
            field=field, value=str(P), snapped=str(lp["snapped_ipo_price"]), tick=str(lp["tick"])))
    out["limit_path"] = {"ipo_price": str(P), "snapped_ipo_price": str(lp["snapped_ipo_price"]), "tick": str(lp["tick"]),
                         "C": [str(c) for c in lp["C"]], "rho": lp["rho"]}
    cells = cells_of(params)
    for h in range(1, DAYS + 1):
        out[f"D{h}"] = horizon_prediction(surv["S"], surv["P_L"], lp["scale"], lp["rho"], cells, h)
    return out


# ============================================================ §7 koşullu güncelleme

def conditional_weights(S: Sequence[float], j: int) -> tuple[dict[int, float], dict[int, float]]:
    """(S_k / S_j, k = j+1..10; P(L = t | L ≥ j), t = j..10). S_0 = 1 (j = 0 koşulsuzdur)."""
    if not 0 <= j <= DAYS:
        raise ValueError(f"j = {j} 0..10 dışında")
    S0 = [1.0] + [float(s) for s in S]
    Sj = S0[j]
    if Sj <= 0.0:
        raise ValueError(f"S_{j} = {Sj}: koşul tanımsız")
    s_cond = {k: S0[k] / Sj for k in range(j + 1, DAYS + 1)}
    pl_cond = {t: (S0[t] - S0[t + 1]) / Sj for t in range(j, DAYS)}
    pl_cond[DAYS] = S0[DAYS] / Sj
    return s_cond, pl_cond


def conditional_rps(S: Sequence[float], j: int, L: int) -> float:
    """Koşullu RPS_j = (1/(10 − j)) Σ_{k=j+1..10} (S_k/S_j − 1[L ≥ k])²; yalnız L ≥ j, j = 0..9."""
    if L < j or j >= DAYS:
        raise ValueError("koşullu RPS yalnız L ≥ j ve j ≤ 9 için tanımlı")
    s_cond, _ = conditional_weights(S, j)
    return sum((s_cond[k] - (1.0 if L >= k else 0.0)) ** 2 for k in range(j + 1, DAYS + 1)) / (DAYS - j)


def conditional_brier(S: Sequence[float], j: int, L: int, k: int) -> float:
    """Koşullu Brier: (S_k/S_j − 1[L ≥ k])², k > j (k = j + 1 "yarın", k = 10 "sonuna kadar")."""
    if L < j or not j < k <= DAYS:
        raise ValueError("koşullu Brier yalnız L ≥ j ve j < k ≤ 10 için tanımlı")
    s_cond, _ = conditional_weights(S, j)
    return (s_cond[k] - (1.0 if L >= k else 0.0)) ** 2


def _record_path(output: Mapping[str, Any]) -> tuple[Decimal, list[Decimal], list[float]]:
    if output.get("refused") or output.get("limit_path") is None or output.get("S") is None:
        raise ValueError("koşullu güncelleme reddedilmiş ya da limit yolu olmayan kayıttan yapılamaz")
    lp = output["limit_path"]
    return Decimal(lp["ipo_price"]), [Decimal(c) for c in lp["C"]], [float(r) for r in lp["rho"]]


def _realized(close: Any, P: Decimal) -> dict[str, Any]:
    return {"status": STATUS_REALIZED, "realized_return": ratio_minus_one(Decimal(str(close)), P)}


def conditional(params: Mapping[str, Any], output: Mapping[str, Any], j: int,
                observed_closes: Sequence[Any]) -> dict[str, Any]:
    """§7 durum 1: D1..Dj tavan (j ≥ 1; j = 0 koşulsuz kayıt). `output` dondurulmuş kayıttaki bu modelin çıktısı;
    `observed_closes` resmi kapanış(D_1..D_j) (en az j tane). h ≤ j: gerçekleşen değer; h > j: koşullu karışım
    [(ρ_h, S_h/S_j)] + t = j..h−1 için hücre(g(t), h − t) atomları, ağırlık P(L = t | L ≥ j)/n; ölçek t ≤ j için
    gözlenen kapanış(D_t)/P, t > j için C_t/P. Gözlenen kapanış C_t'den farklıysa limit_path_mismatch = 1."""
    _check_params(params)
    P, C, rho = _record_path(output)
    if not 0 <= j < DAYS:
        raise ValueError("j 0..9 olmalı (j = 10: bütün ufuklar gerçekleşmiştir)")
    if len(observed_closes) < j:
        raise ValueError(f"j = {j} için {j} gözlenen kapanış gerekir")
    obs = [Decimal(str(c)) for c in observed_closes]
    S = [float(s) for s in output["S"]]
    s_cond, pl_cond = conditional_weights(S, j)
    scale = [ratio(obs[t - 1] if t <= j else C[t - 1], P) for t in range(1, DAYS + 1)]
    cells = cells_of(params)
    out: dict[str, Any] = {"state": STATE_STREAK_ONGOING, "j": j, "S_j": 1.0 if j == 0 else S[j - 1],
                           "S_cond": {str(k): v for k, v in s_cond.items()},
                           "P_L_cond": {str(t): v for t, v in pl_cond.items()},
                           "limit_path_mismatch": int(any(obs[t - 1] != C[t - 1] for t in range(1, j + 1)))}
    for h in range(1, DAYS + 1):
        if h <= j:
            out[f"D{h}"] = _realized(obs[h - 1], P)
            continue
        parts = [(t, pl_cond[t], None if t == 0 else scale[t - 1]) for t in range(j, h)]
        atoms, used, ok = mixture_atoms((rho[h - 1], s_cond[h]), parts, cells, h)
        out[f"D{h}"] = {"status": STATUS_OK if ok else STATUS_POST_BREAK_INSUFFICIENT,
                        **_horizon(atoms, used, ok, limit_return=rho[h - 1], S_h=s_cond[h])}
    return out


def conditional_after_break(params: Mapping[str, Any], output: Mapping[str, Any], t: int,
                            observed_closes: Sequence[Any]) -> dict[str, Any]:
    """§7 durum 2: seri t. günde kırıldı (L = t, 0 ≤ t ≤ 9; kapanış(D_1..D_{t+1}) gözlendi, en az t + 1 tane).
    S kısmı düşer. Gözlenen ufuklar gerçekleşen değerdir; sonraki h için atomlar (kapanış(D_t)/P)·(1 + v) − 1
    (t = 0: v), v ∈ hücre(g(t), h − t), ağırlık 1/n. Kırılmadan sonra gözlenen ek seanslar ayrıca koşullanmaz
    ("kırılma sonrası, D_t'ye koşullu")."""
    _check_params(params)
    P, C, _ = _record_path(output)
    if not 0 <= t < DAYS:
        raise ValueError("t 0..9 olmalı")
    if len(observed_closes) < t + 1:
        raise ValueError(f"L = {t} ancak kapanış(D_{t + 1}) gözlendiyse bilinir")
    obs = [Decimal(str(c)) for c in observed_closes]
    scale = None if t == 0 else ratio(obs[t - 1], P)
    cells = cells_of(params)
    out: dict[str, Any] = {"state": STATE_AFTER_BREAK, "t": t, "note": f"kırılma sonrası, D_{t}'ye koşullu",
                           "limit_path_mismatch": int(any(obs[s - 1] != C[s - 1] for s in range(1, t + 1)))}
    for h in range(1, DAYS + 1):
        if h <= len(obs):
            out[f"D{h}"] = _realized(obs[h - 1], P)
            continue
        atoms, used, ok = mixture_atoms(None, [(t, 1.0, scale)], cells, h)
        out[f"D{h}"] = {"status": STATUS_OK if ok else STATUS_POST_BREAK_INSUFFICIENT,
                        **_horizon(atoms, used, ok, limit_return=None, S_h=None)}
    return out

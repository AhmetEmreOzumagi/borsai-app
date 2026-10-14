"""Kırılma akşamı modeli `break_floor_v0` (kural satırı `break_floor_v0@ZERO`): kırılma tablosu, walk-forward backtest, karşılaştırıcılar,
nihai fit önizlemesi ve deney günlüğü (SPEC_BREAK_V0 §1–§7; KARARLAR C1–C5; docs/SPEC_DEVIATIONS.md N). numpy + scikit-learn yalnız
`fit.fit_fall_horizon` üzerinden. Tahmin matematiği borsai/predict_break.py'dedir (yalnız stdlib); bu modül aynı fonksiyonları çağırır
(`evaluate_break_day`, `structural_zero_d10`, `product_from_cells`), ikinci tanım yoktur.

- Kırılma tablosu (§7.1, `load_break_table`): SESSIONS dosyası (sha256 data_version.json'la) arz başına seans sırasıyla okunur; tavan
  etiketi Decimal(thb_raw_close) == Decimal(thm_raw_upper_limit); L ve b = L + 1. Sütun beyaz listesi (H20 kalıbı): her satırda
  anahtarlar ve `target_session_date`; D_1..D_b'de kapanış ve üst limit; D_b'de `BREAK_DAY_FIELDS` ve iki durum sütunu; D_b'den
  SONRAKİ satırlarda yalnız `thb_raw_close`, `thm_raw_lower_limit`, `target_session_date` ve yalnız etiket için (D_{b+1}, b ≤ 8 ise
  D_{b+2}). Arz fiyatı ve shares_offered training_table'dan (Dataset). Etiketler `BreakLabels`'ta ayrı tutulur; özellik kodu onları
  görmez (grep testi).
- Plan (§7.2, `plan_break_folds`): test birimi b ≤ 9 olan her arz; kesim T_k = E_b(k) = D_b(k) tarihi. Başlık h için eğitim satırı j
  ancak hedef seansı (F1: D_{b_j+1}, F2: D_{b_j+2}) < T_k (kesin). Skorlanabilirlik ≥ 10 satır, ≥ 5 olay, ≥ 5 olay-dışı.
- Fit (§4.1): başlık başına `fit.fit_fall_horizon` (V1.6 ızgarası, iç arz-bırak LOOCV Brier, `_fit_logit`, aday başına yakınsamama,
  azınlık < 2 → fallback_C); tarif `BREAK_V0_RECIPE` (b_floor, b_turnover; b_turnover eğitim [p05, p95]'ine ln ölçeğinde kırpılır;
  z-skor; imputasyon yok). Ön işleme her iç bölmede yeniden ve başlık başınadır.
- Karşılaştırıcılar (§5): `@ZERO` = fold eğitim oranı; `base_floor_by_type` = eğitimde test arzının b_floor sınıfındaki F1 oranı;
  `PRODUCT_BREAK_FLOOR` = tavan yolu durum-2 karışımından taban olasılığı, hücreler `predict_path.build_cells(units, cutoff = D_1(k))`
  (Faz 4 yükleyicisi `ceiling_path.path_units`; H27 kalıbı); Faz 4 ledger'ıyla hücre sayısı paritesi zorunludur.
- Hücreler (§5.2): eşleşik Brier farkı (kırpmasız), aylık blok bootstrap (C7); ölçek `backtest_break` (başka ölçekle birleştirilmez,
  `ScaleMixError`).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from . import fit as fitmod
from . import metrics as mx
from . import predict_break as pb
from . import predict_path as pth
from . import preprocess as pp
from .data import SESSIONS_PATH, VERSION_PATH, DataIntegrityError, Dataset
from .provenance import (ROOT, canonical_json, code_version, identity_hash, now_istanbul, pretty_json_bytes, sha256_bytes,
                         sha256_file)
from .specs import (FAZ8_MODEL_IDS, FAZ8_NEAR_ERA_START, FAZ8_RULES, FAZ8_SENSITIVITIES, PLAN_BREAK_H99, POST_BREAK_MODEL_SPECS,
                    POST_D1_MODEL_SPECS, SPEC_DOCUMENTS_FAZ8, spec_sha256)

MODEL_ID, ZERO_ID = FAZ8_MODEL_IDS
SPEC = POST_BREAK_MODEL_SPECS[MODEL_ID]
HEADS = pb.HEADS
FEATURES = pb.FEATURES
DAYS = pb.DAYS
B_MAX, F2_B_MAX = pb.B_MAX, pb.F2_B_MAX
NEAR_ERA_START = FAZ8_NEAR_ERA_START
OUTCOME_CUTOFF = "2026-08-19"
MIN_ROWS, MIN_EVENTS, MIN_NONEVENTS = (SPEC["scorability"][k] for k in ("min_rows", "min_events", "min_nonevents"))
SCALE = "backtest_break"
DEFAULT_LOG_PATH = ROOT / "experiments" / "log.jsonl"
GOLDEN_DIR = ROOT / "docs" / "faz8" / "backtest"
PARITY_TOL = 1e-12

STATUS_FIT_OK = fitmod.STATUS_FIT_OK
STATUS_INSUFFICIENT = "INSUFFICIENT_TRAINING_HISTORY"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
STATUS_SINGLE_CLASS = fitmod.STATUS_SINGLE_CLASS
STATUS_NOT_CONVERGED = "MODEL_NOT_FIT_DID_NOT_CONVERGE"
FOLD_STATUSES = (STATUS_FIT_OK, STATUS_INSUFFICIENT, STATUS_NOT_APPLICABLE, STATUS_SINGLE_CLASS, STATUS_NOT_CONVERGED)
SCORABLE = "SCORABLE"
UNIT_BREAK, UNIT_B10, UNIT_NO_BREAK = "BREAK", "B10", "NO_BREAK"


def _recipe(features: Sequence[str], winsor: Sequence[str], recipe_id: str) -> pp.Recipe:
    return pp.Recipe(recipe_id, tuple(features), indicator=False, impute=False, missingness_drop=False, winsor=tuple(winsor), log=())


# §4.1 tarifi. borsai/preprocess.py değişmedi (görev kuralı: var olan modül salt okunur; SPEC_DEVIATIONS N): tarif burada kurulur,
# eski tarifler ve altın dosyalar bayt-eşit kalır. ln özellik tanımındadır (log = ()), kırpma ln ölçeğinde.
BREAK_V0_RECIPE = _recipe(FEATURES, pb.WINSOR_FEATURES, SPEC["preprocessing_id"])
if (list(BREAK_V0_RECIPE.substantive), list(BREAK_V0_RECIPE.winsor), list(BREAK_V0_RECIPE.log)) != \
        (SPEC["features"], SPEC["preprocessing_winsor"], SPEC["preprocessing_log"]):
    raise AssertionError("BREAK_V0_RECIPE şartnameyle aynı değil")

# ---- SESSIONS sütun beyaz listesi (§7.1; H20)
SESSION_KEY_COLUMNS: tuple[str, ...] = ("ticker", "session_number")
DATE_COLUMN = "target_session_date"
STREAK_COLUMNS: dict[str, str] = {"close": "thb_raw_close", "upper_limit": "thm_raw_upper_limit"}
BREAK_DAY_FIELDS: dict[str, str] = {"open": "thb_raw_open", "high": "thb_raw_high", "low": "thb_raw_low", "close": "thb_raw_close",
                                    "volume": "thb_raw_volume", "trade_count": "thb_raw_trade_count",
                                    "reference_price": "thm_raw_reference_price", "upper_limit": "thm_raw_upper_limit",
                                    "lower_limit": "thm_raw_lower_limit"}
BREAK_DAY_STATUS_COLUMNS: tuple[str, ...] = ("session_type", "security_trading_status")
LABEL_COLUMNS: dict[str, str] = {"close": "thb_raw_close", "lower_limit": "thm_raw_lower_limit"}
AFTER_BREAK_COLUMNS = frozenset(SESSION_KEY_COLUMNS + (DATE_COLUMN,) + tuple(LABEL_COLUMNS.values()))
HALF_DAY_OF = {"OPEN_FULL_DAY": 0, "OPEN_HALF_DAY": 1}
HALT_OF = {"ACTIVE_NOT_SUSPENDED": 0}
UNKNOWN_OFFICIAL_CODE = "UNKNOWN_OFFICIAL_CODE"
NOT_SCORABLE_STREAK_NA = "NOT_SCORABLE_STREAK_NA"


class BreakError(RuntimeError):
    pass


class ScaleMixError(BreakError):
    """Backtest kırılma hücreleri (`backtest_break`) başka bir ölçekle birleştirilemez (§7.2)."""


# ============================================================ kırılma tablosu (§7.1)

@dataclass(frozen=True)
class BreakUnit:
    """Bir H99 arzı: seri, kırılma günü ve D_b alanları. Kırılmadan sonraki hiçbir seansın alanını taşımaz."""

    ticker: str
    first_trading_date: str
    ipo_price: str                     # training_table ipo_price_tl (ham metin)
    shares_offered: str                # training_table shares_offered (ham metin)
    L: int
    b: Optional[int]                   # None: seri bozulmadı (L = 10)
    status: str                        # BREAK (b ≤ 9) | B10 | NO_BREAK
    closes: tuple[str, ...]            # kapanış(D_1..D_b) ham metin (b yoksa D_1..D_10; yalnız seri ve ürün karşılaştırıcısı)
    session_dates: tuple[str, ...]     # D_1..D_10
    day: Optional[dict[str, Any]]      # D_b bloğu: predict_break.evaluate_break_day girdisi (b ≤ 10)

    @property
    def break_date(self) -> Optional[str]:
        return None if self.b is None else self.session_dates[self.b - 1]


@dataclass(frozen=True)
class BreakLabels:
    """Yalnız etiket: F1 = D_{b+1} taban kapanışı; F2 = F1 ve D_{b+2} taban. None: alt limit NA ya da hedef tanımsız."""

    y1: Optional[int]
    y1_date: Optional[str]
    y2: Optional[int]
    y2_date: Optional[str]


@dataclass
class BreakTable:
    units: list[BreakUnit]                       # tablo sırası (first_trading_date, ticker)
    labels: dict[str, BreakLabels]               # yalnız b ≤ 9
    info: dict[str, Any] = field(default_factory=dict)

    def breaks(self) -> list[BreakUnit]:
        return [u for u in self.units if u.status == UNIT_BREAK]

    def by_ticker(self) -> dict[str, BreakUnit]:
        return {u.ticker: u for u in self.units}


def _dec(text: Optional[str]) -> Optional[Decimal]:
    if text is None or str(text).strip() == "":
        return None
    try:
        return Decimal(str(text).strip())
    except ArithmeticError:
        return None


def _label(row: Mapping[str, str]) -> Optional[int]:
    """Taban etiketi (§2.1): Decimal(kapanış) == Decimal(alt limit), ham metin; alt limit yoksa/≤ 0 ise None (TARGET_LABEL_NA)."""
    lo = _dec(row[LABEL_COLUMNS["lower_limit"]])
    if lo is None or lo <= 0:
        return None
    return int(_dec(row[LABEL_COLUMNS["close"]]) == lo)


def load_break_table(dataset: Dataset, path: Path = SESSIONS_PATH) -> BreakTable:
    """Kırılma tablosu. Seri her arzda seans sırasıyla okunur ve b'de durur; b'den sonra yalnız etiket alanları okunur."""
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    pinned = {s["path"]: s["sha256"] for s in json.loads(VERSION_PATH.read_text(encoding="utf-8"))["sources"]}
    if pinned.get(rel) != sha256_file(path):
        raise DataIntegrityError(f"{rel}: sha256 data_version.json ile aynı değil")
    rows: dict[str, dict[int, Mapping[str, str]]] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            rows.setdefault(r["ticker"], {})[int(r["session_number"])] = r
    if set(rows) != set(dataset.tickers):
        raise DataIntegrityError("SESSIONS arz kümesi veriyle aynı değil")
    units: list[BreakUnit] = []
    labels: dict[str, BreakLabels] = {}
    for row in dataset.rows:
        t, s = row.ticker, rows[row.ticker]
        if set(s) != set(range(1, DAYS + 1)):
            raise DataIntegrityError(f"{t}: SESSIONS 10 seans içermiyor")
        dates = tuple(s[k][DATE_COLUMN] for k in range(1, DAYS + 1))
        if dates != tuple(row.session_dates) or dates[0] != row.first_trading_date:
            raise DataIntegrityError(f"{t}: SESSIONS seans tarihleri veriyle aynı değil")
        L, b, closes = 0, None, []
        for h in range(1, DAYS + 1):
            close, upper = _dec(s[h][STREAK_COLUMNS["close"]]), _dec(s[h][STREAK_COLUMNS["upper_limit"]])
            if upper is None or upper <= 0:
                raise DataIntegrityError(f"{NOT_SCORABLE_STREAK_NA}: {t}/D{h} üst limit yok (H99'da beklenmez)")
            if close is None or close <= 0:
                raise DataIntegrityError(f"{t}/D{h}: kapanış yok ya da ≤ 0 (H99 seansları işlem görmüştür)")
            closes.append(s[h][STREAK_COLUMNS["close"]])
            if close == upper:
                L += 1
                continue
            b = h
            break                        # b'den sonraki seansların fiyat alanları burada okunmaz
        if L != row.ceiling_streak:
            raise DataIntegrityError(f"{t}: ham metinden L = {L}, training_table ceiling_streak_L = {row.ceiling_streak}")
        day = None
        if b is not None:
            r = s[b]
            st, ts = r[BREAK_DAY_STATUS_COLUMNS[0]], r[BREAK_DAY_STATUS_COLUMNS[1]]
            if st not in HALF_DAY_OF or ts not in HALT_OF:
                raise DataIntegrityError(f"{UNKNOWN_OFFICIAL_CODE}: {t}/D{b} session_type={st!r}, security_trading_status={ts!r}")
            day = {"session_h": b, "session_date": r[DATE_COLUMN],
                   "fields_raw": {name: r[col] for name, col in BREAK_DAY_FIELDS.items()},
                   "half_day": HALF_DAY_OF[st], "halt_flag": HALT_OF[ts]}
        status = UNIT_NO_BREAK if b is None else (UNIT_B10 if b == DAYS else UNIT_BREAK)
        units.append(BreakUnit(t, row.first_trading_date, row.inputs["ipo_price_tl"], row.inputs["shares_offered"], L, b, status,
                               tuple(closes), dates, day))
        if status == UNIT_BREAK:
            y1 = _label(s[b + 1])
            y2 = y2_date = None
            if b <= F2_B_MAX:
                y2_date = s[b + 2][DATE_COLUMN]
                y2 = None if y1 is None else (0 if y1 == 0 else _label(s[b + 2]))
            labels[t] = BreakLabels(y1, s[b + 1][DATE_COLUMN], y2, y2_date)
    info = {"sessions_file": rel, "sessions_file_sha256": sha256_file(path), "data_version_sha256": dataset.data_version_sha256}
    return BreakTable(units, labels, info)


def label_of(lbl: BreakLabels, head: str) -> tuple[Optional[int], Optional[str]]:
    """(etiket, etiketin seans tarihi) — plan ve skor kodunun tek erişim noktası."""
    return (lbl.y1, lbl.y1_date) if head == "F1" else (lbl.y2, lbl.y2_date)


def break_values(table: BreakTable) -> dict[str, pb.BreakValues]:
    """b ≤ 9 arzlarının kırılma günü değerleri (`predict_break.evaluate_break_day`, tek tanım). H99'da ret beklenmez."""
    out = {}
    for u in table.breaks():
        try:
            out[u.ticker] = pb.evaluate_break_day(u.day, u.shares_offered)
        except pb.BreakRefusal as exc:
            raise BreakError(f"{u.ticker}: H99 kırılma günü reddedildi ({exc.code}); şartname H99'da 0 ret der") from exc
    return out


def raw_features(table: BreakTable, values: Mapping[str, pb.BreakValues], features: Sequence[str] = FEATURES,
                 override: Optional[Mapping[str, Mapping[str, Any]]] = None) -> dict[str, dict[str, Any]]:
    """Ön işleme girdisi: b_floor (Decimal 0/1), b_turnover (binary64 ln; tahminle aynı sayı), duyarlılıkta group_Z = 1[L = 0].
    `override`: sızıntı testi için bir arzın değerlerini değiştirir."""
    by = table.by_ticker()
    out: dict[str, dict[str, Any]] = {}
    for t, v in values.items():
        row = {"b_floor": Decimal(v.b_floor), "b_turnover": v.turnover_ln, "group_Z": Decimal(int(by[t].L == 0))}
        if override and t in override:
            row.update(override[t])
        out[t] = {f: row[f] for f in features}
    return out


# ============================================================ plan (§7.2)

@dataclass(frozen=True)
class BreakFold:
    fold_id: str
    ticker: str
    first_trading_date: str
    b: int
    break_date: str
    training: dict[str, tuple[str, ...]]          # başlık -> eğitim arzları (tablo sırası)
    status: dict[str, str]                        # başlık -> SCORABLE | INSUFFICIENT_TRAINING_HISTORY | TARGET_UNDEFINED_F2
    events: dict[str, int]
    max_label_date: dict[str, Optional[str]]


def plan_break_folds(table: BreakTable) -> list[BreakFold]:
    """Test birimi b ≤ 9 olan her arz (tablo sırası); T = D_b tarihi; başlık h için eğitim satırı ancak etiket seansı < T."""
    order = table.breaks()
    folds = []
    for k in order:
        T = k.break_date
        training, status, events, max_date = {}, {}, {}, {}
        for head in HEADS:
            if head == "F2" and k.b > F2_B_MAX:
                training[head], status[head], events[head], max_date[head] = (), pb.TARGET_UNDEFINED_F2, 0, None
                continue
            train, ys, dates = [], [], []
            for j in order:
                y, d = label_of(table.labels[j.ticker], head)
                if y is None or d is None or not d < T:
                    continue
                if j.ticker == k.ticker:
                    raise BreakError(f"kendi kendini eğitme: {k.ticker}/{head}")
                if d > OUTCOME_CUTOFF:
                    raise BreakError(f"{j.ticker}: etiket seansı {d} kesimden ({OUTCOME_CUTOFF}) sonra")
                train.append(j.ticker)
                ys.append(y)
                dates.append(d)
            n, ev = len(train), sum(ys)
            training[head], events[head], max_date[head] = tuple(train), ev, (max(dates) if dates else None)
            status[head] = SCORABLE if n >= MIN_ROWS and ev >= MIN_EVENTS and n - ev >= MIN_NONEVENTS else STATUS_INSUFFICIENT
        folds.append(BreakFold(f"{k.ticker}|{T}", k.ticker, k.first_trading_date, k.b, T, training, status, events, max_date))
    return folds


# ============================================================ fit (başlık başına; alt süreçte de çalışır)

def _status_of(logit_status: str) -> str:
    return STATUS_NOT_CONVERGED if logit_status == fitmod.STATUS_NOT_CONVERGED else logit_status


def _head_task(payload: dict[str, Any]) -> dict[str, Any]:
    """Bir başlığın fit'i (`fit.fit_fall_horizon`, V1.6) + test arzı tahmini. Test arzının etiketi argüman olarak verilemez."""
    hf = fitmod.fit_fall_horizon(payload["order"], payload["raw"], payload["Y"], {}, recipe=payload["recipe"],
                                 grid=fitmod.V1_6_GRID, test_raw=payload.get("test_raw"))
    g = hf.logit
    ok = g.status == STATUS_FIT_OK
    intercept, coef = g.intercept_coef() if ok else (None, None)
    return {
        "status": _status_of(g.status),
        "n_used": len(hf.order),
        "selected_C": fitmod.hp_label(g.selected_C, "C"),
        "tuning_status": g.tuning_status,
        "inner_fold_n": g.inner_fold_n,
        "scores": {fitmod._table_key(e.hyperparameter, "C"): e.score for e in g.score_table},
        "score_status": {fitmod._table_key(e.hyperparameter, "C"): e.status for e in g.score_table},
        "final_attempts": [list(a) for a in g.final_attempts],
        "n_class_0": g.n_class_0,
        "n_class_1": g.n_class_1,
        "columns": list(g.columns),
        "intercept": intercept,
        "coef": None if coef is None else dict(zip(g.columns, coef)),
        "p": g.probability if ok else None,
        "prep": hf.final.params() if hf.final is not None and not hf.final.insufficient_feature_variation else None,
        "test_clipped": None if hf.test is None else bool(hf.test["winsorized"].get("b_turnover", False)),
    }


def default_workers() -> int:
    from .backtest import default_workers as dw

    return dw()


def _run_tasks(payloads: Sequence[dict[str, Any]], workers: int) -> list[dict[str, Any]]:
    if workers <= 1 or len(payloads) <= 1:
        return [_head_task(p) for p in payloads]
    ctx = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
        return list(pool.map(_head_task, payloads, chunksize=2))


# ============================================================ karşılaştırıcılar

def train_rate(ys: Sequence[int]) -> Optional[float]:
    """`@ZERO`: n_1 / n (Fraction'dan bir kez binary64; Python int/int bölmesiyle bit-eşit)."""
    return None if not ys else float(Fraction(sum(ys), len(ys)))


class CellCache:
    """`predict_path.build_cells(units, cutoff = D_1(k))` kesim başına bir kez (ürünün listeleme öncesi kaydının karşılığı; §5.1)."""

    def __init__(self, path_units: Sequence[pth.PathUnit]):
        self.units = list(path_units)
        self._cache: dict[str, tuple[dict, dict]] = {}

    def get(self, cutoff: str) -> tuple[dict, dict]:
        if cutoff not in self._cache:
            self._cache[cutoff] = pth.build_cells(self.units, cutoff=cutoff)
        return self._cache[cutoff]


def cell_counts(cells: Mapping[tuple[str, int], Sequence[Any]]) -> dict[str, str]:
    return {f"cells_n_{g}_{m}": str(len(cells[(g, m)])) for g in pth.GROUPS for m in range(1, pth.M_MAX[g] + 1)}


FAZ4_PATH_LEDGER = POST_D1_MODEL_SPECS["post_d1_hazard_v0"]["path_ledger"]


def faz4_cell_parity(cache: CellCache, ref: Mapping[str, str] = FAZ4_PATH_LEDGER) -> dict[str, Any]:
    """§7.2 (vi): Faz 4 `ceiling_path_v0` ledger'ının OK fold'larında aynı kesimli hücre sayıları ve `cells_max_session_date` birebir.
    Uyuşmazlık durur. Dönen: {n_checked, tickers}."""
    raw = (ROOT / ref["path"]).read_bytes()
    if sha256_bytes(raw) != ref["sha256"]:
        raise BreakError(f"{ref['path']}: sha256 pinli değerle aynı değil")
    checked = []
    for r in csv.DictReader(io.StringIO(raw.decode("utf-8"))):
        if r["status"] != "OK":
            continue
        cells, info = cache.get(r["prediction_date"])
        if any(r[k] != v for k, v in cell_counts(cells).items()) or (info["max_session_date"] or "") != r["cells_max_session_date"]:
            raise BreakError(f"{r['fold_id']}: hücreler Faz 4 ledger'ıyla aynı değil")
        checked.append(r["ticker"])
    return {"n_checked": len(checked), "tickers": checked}


# ============================================================ ledger (§7.2; sütun sırası sabit)

LEDGER_COLUMNS: tuple[str, ...] = (
    "model_id", "fold_id", "ticker", "first_trading_date", "b", "break_date", "training_n", "training_events", "training_nonevents",
    "training_max_label_date", "training_tickers_sha256", "selected_C_F1", "inner_table_F1", "selected_C_F2", "inner_table_F2",
    "columns", "coef_floor_F1", "coef_turn_F1", "intercept_F1", "coef_floor_F2", "coef_turn_F2", "intercept_F2", "clip_p05",
    "clip_p95", "mean_floor", "std_floor", "mean_turn", "std_turn", "dropped", "test_b_floor", "test_b_turnover_ratio",
    "test_b_turnover_clipped", "test_floor_lock_allday", "test_half_day", "p_F1", "p_F2", "zero_F1", "zero_F2", "by_type_F1",
    "product_F1", "product_F2", "product_status", "cells_max_session_date", "structural_zero_D10", "realized_F1", "realized_F2",
    "status",
)


def _inner_table(fold: BreakFold, head: str, part: Optional[Mapping[str, Any]]) -> str:
    """Başlığın iç tablosu (JSON): durum, iç LOOCV skorları, nihai fit denemeleri, katsayılar ve ön işleme (F2'nin ön işlemesi ayrı
    sütun almaz; SPEC_DEVIATIONS N)."""
    base = {"status": fold.status[head] if part is None else part["status"], "n": len(fold.training[head]), "events": fold.events[head]}
    if part is not None:
        base.update({k: part[k] for k in ("tuning_status", "inner_fold_n", "scores", "score_status", "final_attempts", "columns",
                                          "intercept", "coef", "prep")})
    return canonical_json(base)


def _coef(part: Optional[Mapping[str, Any]], col: str) -> Optional[float]:
    if part is None or part["coef"] is None:
        return None
    return part["coef"].get(col, 0.0)          # düşen kolonun katsayısı 0 (dropped sütununda yazılı)


def _prep_value(part: Optional[Mapping[str, Any]], kind: str, col: str) -> Optional[float]:
    prep = None if part is None else part["prep"]
    if prep is None:
        return None
    if kind == "clip":
        w = prep["winsor"].get("b_turnover")
        return None if w is None else w[col]
    return prep[kind].get(col)


def backtest_ledger(table: BreakTable, path_units: Sequence[pth.PathUnit], *, model_id: str = MODEL_ID,
                    features: Sequence[str] = FEATURES, recipe: pp.Recipe = BREAK_V0_RECIPE, workers: Optional[int] = None,
                    override: Optional[Mapping[str, Mapping[str, Any]]] = None,
                    faz4_ref: Optional[Mapping[str, str]] = FAZ4_PATH_LEDGER) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """(ledger satırları, bilgi). Her b ≤ 9 arzı bir satır; F1 durumu `status` sütunundadır, F2'ninki `inner_table_F2`'de.
    `faz4_ref` = None yalnız sentetik testler içindir (Faz 4 hücre paritesi H99 birimleriyle anlamlıdır)."""
    workers = default_workers() if workers is None else workers
    values = break_values(table)
    raw = raw_features(table, values, features, override)
    folds = plan_break_folds(table)
    units = table.by_ticker()
    payloads, keys = [], []
    for f in folds:
        for head in HEADS:
            if f.status[head] != SCORABLE:
                continue
            Y = {t: label_of(table.labels[t], head)[0] for t in f.training[head]}
            payloads.append({"order": list(f.training[head]), "raw": {t: raw[t] for t in (*f.training[head], f.ticker)}, "Y": Y,
                             "recipe": recipe, "test_raw": raw[f.ticker]})
            keys.append((f.fold_id, head))
    parts = dict(zip(keys, _run_tasks(payloads, workers)))
    for (fid, head), part in parts.items():
        f = next(x for x in folds if x.fold_id == fid)
        if part["n_used"] != len(f.training[head]):
            raise BreakError(f"{fid}/{head}: fit'in eğitim kümesi plandan farklı")
    cache = CellCache(path_units)
    path_by = {u.ticker: u for u in path_units}
    ledger = []
    n_product_insufficient = 0
    for f in folds:
        u, v = units[f.ticker], values[f.ticker]
        p1, p2 = parts.get((f.fold_id, "F1")), parts.get((f.fold_id, "F2"))
        ys1 = [label_of(table.labels[t], "F1")[0] for t in f.training["F1"]]
        ys2 = [label_of(table.labels[t], "F2")[0] for t in f.training["F2"]]
        same = [y for t, y in zip(f.training["F1"], ys1) if values[t].b_floor == v.b_floor]
        cells, info = cache.get(u.first_trading_date)
        if info["max_session_date"] is not None and not info["max_session_date"] < u.first_trading_date:
            raise BreakError(f"{f.fold_id}: hücre gözlemi D_1(k)'dan önce değil")
        pu = path_by[f.ticker]
        if any(Decimal(c) != pu.closes[i] for i, c in enumerate(u.closes)) or Decimal(u.ipo_price) != pu.ipo_price:
            raise BreakError(f"{f.ticker}: kırılma tablosu kapanışları Faz 4 yükleyicisininkiyle aynı değil")
        prod = pb.product_from_cells(cells, u.ipo_price, u.L, u.closes)
        n_product_insufficient += prod["status"] != pb.PRODUCT_OK
        lbl = table.labels[f.ticker]
        sz = pb.structural_zero_d10(u.closes[-1], u.b, u.ipo_price)
        status = p1["status"] if p1 is not None else f.status["F1"]
        ledger.append({
            "model_id": model_id, "fold_id": f.fold_id, "ticker": f.ticker, "first_trading_date": f.first_trading_date, "b": f.b,
            "break_date": f.break_date, "training_n": len(f.training["F1"]), "training_events": f.events["F1"],
            "training_nonevents": len(f.training["F1"]) - f.events["F1"],
            "training_max_label_date": max((d for d in f.max_label_date.values() if d), default=None),
            "training_tickers_sha256": identity_hash(f.training["F1"]),
            "selected_C_F1": None if p1 is None else p1["selected_C"], "inner_table_F1": _inner_table(f, "F1", p1),
            "selected_C_F2": None if p2 is None else p2["selected_C"], "inner_table_F2": _inner_table(f, "F2", p2),
            "columns": None if p1 is None else canonical_json(p1["columns"]),
            "coef_floor_F1": _coef(p1, "b_floor"), "coef_turn_F1": _coef(p1, "b_turnover"),
            "intercept_F1": None if p1 is None else p1["intercept"],
            "coef_floor_F2": _coef(p2, "b_floor"), "coef_turn_F2": _coef(p2, "b_turnover"),
            "intercept_F2": None if p2 is None else p2["intercept"],
            "clip_p05": _prep_value(p1, "clip", "p05"), "clip_p95": _prep_value(p1, "clip", "p95"),
            "mean_floor": _prep_value(p1, "mean", "b_floor"), "std_floor": _prep_value(p1, "std", "b_floor"),
            "mean_turn": _prep_value(p1, "mean", "b_turnover"), "std_turn": _prep_value(p1, "std", "b_turnover"),
            "dropped": None if p1 is None or p1["prep"] is None else canonical_json(sorted(p1["prep"]["dropped"])),
            "test_b_floor": v.b_floor, "test_b_turnover_ratio": str(v.turnover_ratio),
            "test_b_turnover_clipped": None if p1 is None or p1["test_clipped"] is None else int(p1["test_clipped"]),
            "test_floor_lock_allday": v.floor_lock_allday, "test_half_day": v.half_day,
            "p_F1": None if p1 is None else p1["p"], "p_F2": None if p2 is None else p2["p"],
            "zero_F1": train_rate(ys1), "zero_F2": train_rate(ys2) if f.status["F2"] != pb.TARGET_UNDEFINED_F2 else None,
            "by_type_F1": train_rate(same),
            "product_F1": prod["F1"], "product_F2": prod["F2"], "product_status": prod["status"],
            "cells_max_session_date": info["max_session_date"], "structural_zero_D10": int(sz["impossible"]),
            "realized_F1": lbl.y1, "realized_F2": lbl.y2, "status": status,
        })
    for r in ledger:
        if tuple(r) != LEDGER_COLUMNS:
            raise BreakError("ledger sütun sırası şartnamedeki gibi değil")
    info = {"folds_total": len(folds), "folds_insufficient_F1": sum(f.status["F1"] == STATUS_INSUFFICIENT for f in folds),
            "folds_insufficient_F2": sum(f.status["F2"] == STATUS_INSUFFICIENT for f in folds),
            "folds_target_undefined_F2": sum(f.status["F2"] == pb.TARGET_UNDEFINED_F2 for f in folds),
            "product_insufficient": n_product_insufficient,
            "faz4_cell_parity": None if faz4_ref is None else faz4_cell_parity(cache, faz4_ref)["n_checked"]}
    return ledger, info


def _fmt(value: Any) -> str:
    from .backtest import _fmt as bt_fmt

    return bt_fmt(value)


def ledger_csv_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    from .backtest import ledger_csv_bytes as bt_ledger

    return bt_ledger(rows)


def read_ledger(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# ============================================================ hücreler (§5.2)

def _num(x: Any) -> Optional[float]:
    return None if x is None or x == "" else float(x)


def _date_ok(t: str, start: Optional[str], end: Optional[str]) -> bool:
    return (start is None or t >= start) and (end is None or t < end)


def paired_brier(rows: Sequence[Mapping[str, Any]], a: str, b: str, *, realized: str, start: Optional[str] = None,
                 end: Optional[str] = None, where: Optional[Callable[[Mapping[str, Any]], bool]] = None,
                 scale: str = SCALE) -> Optional[dict[str, Any]]:
    """Eşleşik Brier farkı (kırpmasız) = Brier(a) − Brier(b), iki değer ve gerçekleşen etiket doluysa; [start, end) ilk işlem aralığı;
    blok = ilk işlem ayı (C7). n < 10 ya da < 6 ay ise aralık yok. `scale` yalnız `backtest_break` olabilir."""
    if scale != SCALE:
        raise ScaleMixError(f"kırılma hücreleri yalnız {SCALE} ölçeğindedir: {scale}")
    diffs, months, la, lb, tickers = [], [], [], [], []
    for r in rows:
        pa, pb_, y = _num(r[a]), _num(r[b]), _num(r[realized])
        if pa is None or pb_ is None or y is None or not _date_ok(r["first_trading_date"], start, end) or (where and not where(r)):
            continue
        ea, eb = (pa - y) ** 2, (pb_ - y) ** 2
        diffs.append(ea - eb)
        months.append(r["first_trading_date"][:7])
        la.append(ea)
        lb.append(eb)
        tickers.append(r["ticker"])
    if not diffs:
        return None
    if len(diffs) >= FAZ8_RULES["ci_min_n"] and len(set(months)) >= FAZ8_RULES["ci_min_months"]:
        res = mx.paired_difference(diffs, months)
    else:
        res = {"n": len(diffs), "n_months": len(set(months)), "mean": sum(diffs) / len(diffs), "ci95": None,
               "model_better_n": sum(1 for d in diffs if d < 0), "rule_better_n": sum(1 for d in diffs if d > 0),
               "tie_n": sum(1 for d in diffs if d == 0), "verdict": None}
    res.update(scale=scale, metric="brier", a=a, b=b, a_metric=sum(la) / len(la), b_metric=sum(lb) / len(lb), tickers=tickers,
               tie_n_1e12=sum(1 for d in diffs if abs(d) <= 1e-12))
    return res


def merge_cells(*cells: Mapping[str, Any]) -> None:
    """Hücre blokları birleştirilmez (§7.2): farklı ölçek ScaleMixError; aynı ölçek de reddedilir (her hücre ayrı raporlanır)."""
    scales = {c.get("scale") for c in cells}
    if len(scales) > 1:
        raise ScaleMixError(f"iki terazi birleştirilemez: {sorted(map(str, scales))}")
    raise ScaleMixError("kırılma hücreleri birleştirilmez; her hücre ayrı raporlanır")


def _has_p1(r: Mapping[str, Any]) -> bool:
    return _num(r["p_F1"]) is not None


# (anahtar, a, b, gerçekleşen, kısıt) — §5.2 tablosu. Bilgi hücresi birincil hücrenin arzlarındadır (model F1 FIT_OK).
CELL_DEFS: dict[str, tuple[str, str, str, Optional[Callable[[Mapping[str, Any]], bool]]]] = {
    "F1_product": ("p_F1", "product_F1", "realized_F1", None),
    "F1_zero": ("p_F1", "zero_F1", "realized_F1", None),
    "F2_product": ("p_F2", "product_F2", "realized_F2", None),
    "F2_zero": ("p_F2", "zero_F2", "realized_F2", None),
    "F1_by_type": ("p_F1", "by_type_F1", "realized_F1", None),
    "info_product_zero_F1": ("product_F1", "zero_F1", "realized_F1", _has_p1),
}
PRIMARY_CELL = "F1_product"
SCOPES: dict[str, dict[str, Optional[str]]] = {"near": {"start": NEAR_ERA_START, "end": None},
                                               "2023": {"start": None, "end": NEAR_ERA_START},
                                               "all": {"start": None, "end": None}}


def compute_cells(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Optional[dict[str, Any]]]]:
    """scope -> hücre -> eşleşik fark (C7). Yakın dönem hücreleri §5.2'nin hükümlü hücreleridir; 2023 ve bütün fold'lar keşiftir."""
    return {s: {k: paired_brier(rows, a, b, realized=y, where=w, **kw) for k, (a, b, y, w) in CELL_DEFS.items()}
            for s, kw in SCOPES.items()}


def calibration(rows: Sequence[Mapping[str, Any]], head: str = "F1", *, start: Optional[str] = NEAR_ERA_START,
                end: Optional[str] = None, where: Optional[Callable[[Mapping[str, Any]], bool]] = None) -> Optional[dict[str, Any]]:
    """ort(p_h) − gözlenen y_h oranı, modelin FIT_OK fold'larında (p dolu), [start, end) ilk işlem aralığında."""
    pts = [(_num(r[f"p_{head}"]), _num(r[f"realized_{head}"])) for r in rows
           if _num(r[f"p_{head}"]) is not None and _num(r[f"realized_{head}"]) is not None
           and _date_ok(r["first_trading_date"], start, end) and (where is None or where(r))]
    if not pts:
        return None
    mp, obs = sum(p for p, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)
    return {"n": len(pts), "mean_p": mp, "observed": obs, "diff": mp - obs}


def compute_break_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Günlük için özet: başlık başına fold/FIT_OK sayısı, Brier, ortalama p, gözlenen oran (yakın dönem ve bütün)."""
    out: dict[str, Any] = {}
    for head in HEADS:
        for s in ("near", "all"):
            kw = SCOPES[s]
            pts = [(_num(r[f"p_{head}"]), _num(r[f"realized_{head}"])) for r in rows
                   if _num(r[f"p_{head}"]) is not None and _num(r[f"realized_{head}"]) is not None
                   and _date_ok(r["first_trading_date"], kw["start"], kw["end"])]
            out[f"{head}_{s}"] = {"n": len(pts)} if not pts else {
                "n": len(pts), "brier": sum((p - y) ** 2 for p, y in pts) / len(pts), "mean_p": sum(p for p, _ in pts) / len(pts),
                "observed": sum(y for _, y in pts) / len(pts)}
    out["folds"] = len(rows)
    out["statuses_F1"] = {s: sum(1 for r in rows if r["status"] == s) for s in sorted({r["status"] for r in rows})}
    return out


def _cell_summary(c: Optional[Mapping[str, Any]]) -> Optional[dict[str, Any]]:
    keep = ("n", "n_months", "mean", "ci95", "model_better_n", "rule_better_n", "tie_n", "tie_n_1e12", "a_metric", "b_metric")
    return None if c is None else {k: c[k] for k in keep}


# ============================================================ koşu ve günlük (CLAUDE.md kural 4)

@dataclass
class BreakResult:
    model_id: str
    ledger: list[dict[str, Any]]
    ledger_csv: bytes
    info: dict[str, Any]
    cells: dict[str, Any]
    metrics: dict[str, Any]
    log_entry: dict[str, Any]


def _path_units(dataset: Dataset) -> list[pth.PathUnit]:
    from . import ceiling_path as cp

    return cp.path_units(dataset.rows)


def _doc_fields() -> dict[str, str]:
    doc, dec = SPEC_DOCUMENTS_FAZ8["SPEC_BREAK_V0"], SPEC_DOCUMENTS_FAZ8["KARARLAR_FAZ8"]
    for d in (doc, dec):
        if sha256_file(ROOT / d["path"]) != d["sha256"]:
            raise BreakError(f"{d['path']}: sha256 specs.SPEC_DOCUMENTS_FAZ8 ile aynı değil (şartname değişti mi?)")
    return {"spec_document": doc["path"], "spec_document_sha256": sha256_file(ROOT / doc["path"]),
            "decisions_document": dec["path"], "decisions_document_sha256": sha256_file(ROOT / dec["path"])}


def run_backtest(dataset: Dataset, *, log_path: Path, context: str, workers: Optional[int] = None,
                 table: Optional[BreakTable] = None, path_units: Optional[Sequence[pth.PathUnit]] = None,
                 faz4_ref: Optional[Mapping[str, str]] = FAZ4_PATH_LEDGER) -> BreakResult:
    """PLAN_BREAK_H99 walk-forward; sonunda günlüğe bir `kind: backtest` satırı (CLAUDE.md kural 4). `@ZERO` kural satırının
    backtest'i aynı ledger'ın `zero_F1`/`zero_F2` sütunlarıdır (ayrı koşu ve satır yok; SPEC_DEVIATIONS N)."""
    runtime = fitmod.verify_runtime()
    started = now_istanbul()
    table = table if table is not None else load_break_table(dataset)
    path_units = path_units if path_units is not None else _path_units(dataset)
    ledger, info = backtest_ledger(table, path_units, workers=workers, faz4_ref=faz4_ref)
    payload = ledger_csv_bytes(ledger)
    rows = [{k: _fmt(v) for k, v in r.items()} for r in ledger]     # hücreler yazılan CSV ile aynı metinden
    cells = compute_cells(rows)
    metrics = compute_break_metrics(rows)
    entry = {
        "kind": "backtest",
        "context": context,
        "model_id": MODEL_ID,
        "stage": SPEC["stage"],
        "spec_sha256": spec_sha256(SPEC),
        "plan_id": PLAN_BREAK_H99,
        "data_version_sha256": dataset.data_version_sha256,
        "training_table_sha256": dataset.table_sha256,
        "sessions_file_sha256": table.info.get("sessions_file_sha256"),
        "path_cells_source": {"loader": "borsai.ceiling_path.path_units (Faz 4 yükleyicisi)", "cutoff": "D_1(k)",
                              "faz4_ledger": FAZ4_PATH_LEDGER, "faz4_cell_parity_folds": info["faz4_cell_parity"]},
        "folds_total": info["folds_total"],
        "folds_scorable": {h: sum(1 for r in ledger if _num(_fmt(r[f"p_{h}"])) is not None) for h in HEADS},
        "ledger_sha256": sha256_bytes(payload),
        "rule_rows_in_ledger": {ZERO_ID: {"spec_sha256": spec_sha256(POST_BREAK_MODEL_SPECS[ZERO_ID]),
                                          "columns": ["zero_F1", "zero_F2"]}},
        "near_era": {k: _cell_summary(v) for k, v in cells["near"].items()},
        "primary_cell": "F1 Brier, break_floor_v0 − PRODUCT_BREAK_FLOOR, ilk işlem ≥ 2024-01-01",
        "info": dict(info),
        "metrics": metrics,
        "started_at": started,
        "finished_at": now_istanbul(),
        **code_version(),
        **_doc_fields(),
        "runtime": runtime,
    }
    from .backtest import append_log

    append_log(log_path, entry)
    return BreakResult(MODEL_ID, ledger, payload, info, cells, metrics, entry)


def sensitivity_spec(name: str) -> dict[str, Any]:
    """Duyarlılığın kanonik sözlüğü (model değil): temel şartname + özellik kümesi ve kimlik."""
    sens = FAZ8_SENSITIVITIES[name]
    spec = json.loads(json.dumps(SPEC))
    spec.update({"model_id": name, "features": list(sens["features"]), "preprocessing_winsor": list(sens["winsor"]),
                 "base_model_id": MODEL_ID, "is_model": False})
    return spec


def run_sensitivity(name: str, dataset: Dataset, *, log_path: Path, context: str, ledger_file: str,
                    workers: Optional[int] = None, table: Optional[BreakTable] = None,
                    path_units: Optional[Sequence[pth.PathUnit]] = None, out_dir: Optional[Path] = None,
                    faz4_ref: Optional[Mapping[str, str]] = FAZ4_PATH_LEDGER) -> BreakResult:
    """§7.2 duyarlılığı: aynı plan, farklı özellik kümesi. Günlüğe `kind: sensitivity` (model değil; dondurulmaz, tabloya ve varyant
    sayacına girmez). Ledger `ledger_file`'a (repo köküne göre) yazılır; satır onun sha'sını taşır."""
    sens = FAZ8_SENSITIVITIES[name]
    started = now_istanbul()
    table = table if table is not None else load_break_table(dataset)
    path_units = path_units if path_units is not None else _path_units(dataset)
    recipe = _recipe(sens["features"], sens["winsor"], f"BREAK_V0_SENSITIVITY_{name.rsplit('__', 1)[-1].upper()}")
    ledger, info = backtest_ledger(table, path_units, model_id=name, features=sens["features"], recipe=recipe, workers=workers,
                                   faz4_ref=faz4_ref)
    payload = ledger_csv_bytes(ledger)
    target = (Path(out_dir) if out_dir is not None else ROOT) / ledger_file
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise BreakError(f"{target} zaten var; duyarlılık ledger'ı üzerine yazılmaz")
    target.write_bytes(payload)
    rows = [{k: _fmt(v) for k, v in r.items()} for r in ledger]
    cells = compute_cells(rows)
    metrics = compute_break_metrics(rows)
    spec = sensitivity_spec(name)
    entry = {
        "kind": "sensitivity",
        "context": context,
        "model_id": name,
        "base_model_id": MODEL_ID,
        "variant": {"features": list(sens["features"]), "winsor": list(sens["winsor"])},
        "is_model": False,
        "note": "model değil; dondurulmaz, hiçbir tabloya, skora ve varyant sayacına girmez (SPEC_BREAK_V0 §7.2)",
        "stage": SPEC["stage"],
        "plan_id": PLAN_BREAK_H99,
        "spec_sha256": spec_sha256(spec),
        "data_version_sha256": dataset.data_version_sha256,
        "training_table_sha256": dataset.table_sha256,
        "sessions_file_sha256": table.info.get("sessions_file_sha256"),
        "ledger_file": ledger_file,
        "ledger_sha256": sha256_bytes(payload),
        "near_era": {k: _cell_summary(v) for k, v in cells["near"].items()},
        "metrics": metrics,
        "started_at": started,
        "finished_at": now_istanbul(),
        **code_version(),
        **_doc_fields(),
    }
    from .backtest import append_log

    append_log(log_path, entry)
    return BreakResult(name, ledger, payload, info, cells, metrics, entry)


# ============================================================ nihai fit önizlemesi (dondurma ayrı görev)

FEATURE_DEFINITIONS = SPEC["feature_definitions"]


def training_rows(table: BreakTable, head: str) -> list[str]:
    """Nihai fit'in başlık kümesi: b ≤ 9 (F2: b ≤ 8) ve etiketi dolu arzlar, tablo sırası. Bütün etiketler ≤ 2026-08-19."""
    out = []
    for u in table.breaks():
        y, d = label_of(table.labels[u.ticker], head)
        if y is None:
            continue
        if d > OUTCOME_CUTOFF:
            raise BreakError(f"{u.ticker}: etiket seansı {d} kesimden sonra")
        out.append(u.ticker)
    return out


def break_fields_sha256(table: BreakTable, tickers: Sequence[str]) -> str:
    """82 × (ticker, b, kapanış_b, alt limit_b, hacim_b) ham metin (§4.4)."""
    by = table.by_ticker()
    return identity_hash([f"{t}|{by[t].b}|{by[t].day['fields_raw']['close']}|{by[t].day['fields_raw']['lower_limit']}|"
                          f"{by[t].day['fields_raw']['volume']}" for t in tickers])


def final_fit(model_id: str, dataset: Dataset, *, table: Optional[BreakTable] = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """(dondurulacak parametre sözlüğü, başlık -> FallHorizonFit). JSON alanları §4.4; stdlib `predict_break.predict_break` ile çalışır.
    Eğitim n'i, veri sürümü ve SESSIONS sha'sı şartnameyle tutmazsa durur."""
    table = table if table is not None else load_break_table(dataset)
    return build_params(model_id, table, dataset.data_version_sha256, check=True)


def build_params(model_id: str, table: BreakTable, data_version: str, *, check: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    """Nihai fit (`final_fit`'in gövdesi; `check=False` yalnız sentetik testler içindir)."""
    spec = POST_BREAK_MODEL_SPECS[model_id]
    values = break_values(table)
    features = list(spec["features"])
    raw = raw_features(table, values, FEATURES)
    fits, preps, tickers, events = {}, {}, {}, {}
    for head in HEADS:
        order = training_rows(table, head)
        Y = {t: label_of(table.labels[t], head)[0] for t in order}
        hf = fitmod.fit_fall_horizon(order, raw, Y, {}, recipe=BREAK_V0_RECIPE if features else None,
                                     grid=fitmod.V1_6_GRID if features else None)
        if hf.logit.status != STATUS_FIT_OK:
            raise fitmod.FitError(f"{model_id} {head}: nihai fit {hf.logit.status}")
        fits[head], tickers[head], events[head] = hf, list(hf.order), sum(Y.values())
        preps[head] = hf.final.params() if hf.final is not None else None
    tr = spec["training"]
    if check:
        if (len(tickers["F1"]), len(tickers["F2"])) != (tr["n_F1"], tr["n_F2"]) or data_version != tr["data_version_sha256"]:
            raise fitmod.FitError(f"{model_id}: eğitim n'i ya da veri sürümü şartnameyle tutmuyor")
        if table.info.get("sessions_file_sha256") != tr["sessions_file_sha256"]:
            raise fitmod.FitError(f"{model_id}: SESSIONS sha256 şartnameyle tutmuyor")
    block = {
        "set": tr["set"], "n_F1": len(tickers["F1"]), "events_F1": events["F1"], "n_F2": len(tickers["F2"]), "events_F2": events["F2"],
        "tickers_F1": tickers["F1"], "tickers_F2": tickers["F2"], "tickers_sha256": identity_hash(tickers["F1"]),
        "tickers_sha256_F2": identity_hash(tickers["F2"]),
        "cutoff_date": max(label_of(table.labels[t], h)[1] for h in HEADS for t in tickers[h]),
        "break_fields_sha256": break_fields_sha256(table, tickers["F1"]),
        "labels_sha256": identity_hash([f"{t}|{table.labels[t].y1}|{table.labels[t].y1_date}|{table.labels[t].y2}|"
                                        f"{table.labels[t].y2_date}" for t in tickers["F1"]]),
        "data_version_sha256": data_version, "sessions_file": table.info.get("sessions_file"),
        "sessions_file_sha256": table.info.get("sessions_file_sha256"),
    }
    params = fitmod._envelope(spec, [], data_version, block)
    params["runtime"] = fitmod.verify_runtime()
    by_type = {}
    for cls in (0, 1):
        ys = [label_of(table.labels[t], "F1")[0] for t in tickers["F1"] if values[t].b_floor == cls]
        by_type[str(cls)] = {"rate": train_rate(ys), "n": len(ys), "events": sum(ys)}
    params.update({
        "family": spec["family"],
        "stage": spec["stage"],
        "target_definition": spec["target_definition"],
        "event_definition": spec["event_definition"],
        "horizons": {h: {"p_floor": fitmod.fall_head(fits[h])["p_up"]} for h in HEADS},
        "preprocessing": preps if features else None,
        "feature_definitions": {f: FEATURE_DEFINITIONS[f] for f in features},
        "feature_ranges": fitmod.feature_ranges({t: raw[t] for t in tickers["F1"]}, features) if features else {},
        "comparators": {"zero": {h: train_rate([label_of(table.labels[t], h)[0] for t in tickers[h]]) for h in HEADS},
                        "by_type_F1": by_type},
        "structural_zero_rule": spec["structural_zero_rule"],
        "band_rule": spec["band_rule"],
        "regime_warning": spec["regime_warning"],
        "input_policy": dict(spec["input_policy"]),
        "spec_document": spec["spec_document"],
        "decisions_document": spec["decisions_document"],
    })
    return params, fits


def parity_rows(params: Mapping[str, Any], fits: Mapping[str, Any], table: BreakTable) -> dict[str, float]:
    """§13-9: eğitim satırlarında numpy nihai model (predict_proba, kesin z) ile stdlib `predict_break` (JSON) arasındaki en büyük
    |Δp| (başlık başına)."""
    import numpy as np

    by = table.by_ticker()
    out = {}
    for head in HEADS:
        hf = fits[head]
        worst = 0.0
        for t in hf.order:
            u = by[t]
            stdlib = pb.predict_break(params, u.day, u.shares_offered, b=u.b)[head]["p_floor"]
            if hf.logit.estimator is None:
                numpy_p = hf.logit.constant
            else:
                x = np.array([[hf.final.train_matrix[t][c] for c in hf.final.columns]], dtype=np.float64)
                numpy_p = fitmod._p1(hf.logit.estimator, x)
            worst = max(worst, abs(stdlib - numpy_p))
        out[head] = worst
    return out


# ============================================================ resmi koşu çıktıları (docs/faz8/backtest/)

GOLDEN_DESCRIPTION = ("Faz 8: break_floor_v0'ın (SPEC_BREAK_V0) bu makinedeki H99 walk-forward fold ledger'ı (zero_F1/zero_F2 sütunları "
                      "break_floor_v0@ZERO kural satırının backtest'idir), üç duyarlılığın ledger'ları (model değil) ve iki kimliğin nihai fit "
                      "önizlemeleri. docs/MODELS.md Faz 8 bölümü bunlardan üretilir. Modeller DONDURULMADI; önizlemeler models/'e yazılmadı.")
LEDGER_FILE = f"{MODEL_ID}_fold_ledger.csv"


def sensitivity_ledger_file(name: str) -> str:
    return f"docs/faz8/backtest/{name}_fold_ledger.csv"


def preview_file(model_id: str) -> str:
    return f"{model_id}_final_fit_preview.json"


def golden_available(out_dir: Path = GOLDEN_DIR) -> bool:
    return (Path(out_dir) / "MANIFEST.json").exists()


def write_golden(result: BreakResult, sensitivities: Mapping[str, BreakResult], previews: Mapping[str, Mapping[str, Any]],
                 parity: Mapping[str, Mapping[str, float]], out_dir: Path = GOLDEN_DIR) -> dict[str, Any]:
    """Ledger + önizlemeler + MANIFEST + SHA256SUMS (duyarlılık ledger'ları `run_sensitivity`'de yazılır). Var olanın üzerine yazmaz."""
    from .backtest import _platform
    from .provenance import runtime_versions

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    items = [(LEDGER_FILE, result.ledger_csv)] + [(preview_file(m), pretty_json_bytes(dict(p))) for m, p in previews.items()]
    for name, payload in items:
        path = out_dir / name
        if path.exists():
            raise BreakError(f"{path} zaten var; resmi koşu çıktısı üzerine yazılmaz")
        path.write_bytes(payload)
        files[name] = sha256_file(path)
    for name, res in sensitivities.items():
        files[Path(res.log_entry["ledger_file"]).name] = res.log_entry["ledger_sha256"]
    manifest = {
        "description": GOLDEN_DESCRIPTION,
        "runs": {MODEL_ID: {"file": LEDGER_FILE, "model_id": MODEL_ID, "plan_id": PLAN_BREAK_H99,
                            "spec_sha256": result.log_entry["spec_sha256"], "ledger_sha256": files[LEDGER_FILE]}},
        "sensitivities": {n: {"file": Path(r.log_entry["ledger_file"]).name, "spec_sha256": r.log_entry["spec_sha256"],
                              "ledger_sha256": r.log_entry["ledger_sha256"]} for n, r in sensitivities.items()},
        "final_fit_previews": {m: {"file": preview_file(m), "sha256": files[preview_file(m)], "parity_max_abs": dict(parity[m])}
                               for m in previews},
        "info": dict(result.info),
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

    parser = argparse.ArgumentParser(description="break_floor_v0: walk-forward backtest, duyarlılıklar (günlüğe yazılır) ve nihai fit "
                                                 "önizlemesi (docs/faz8/backtest/).")
    parser.add_argument("--official", action="store_true", help="resmi koşu: backtest + üç duyarlılık + önizlemeler + MANIFEST")
    parser.add_argument("--context", default="official")
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args(argv)
    if not args.official:
        parser.error("--official gerekli")
    if golden_available():
        raise BreakError(f"{GOLDEN_DIR}/MANIFEST.json zaten var; resmi koşu bir kez yapılır")
    dataset = load_dataset()
    table = load_break_table(dataset)
    units = _path_units(dataset)
    result = run_backtest(dataset, log_path=DEFAULT_LOG_PATH, context=args.context, workers=args.workers, table=table, path_units=units)
    sens = {n: run_sensitivity(n, dataset, log_path=DEFAULT_LOG_PATH, context=args.context, ledger_file=sensitivity_ledger_file(n),
                               workers=args.workers, table=table, path_units=units) for n in FAZ8_SENSITIVITIES}
    previews, parity = {}, {}
    for m in FAZ8_MODEL_IDS:
        params, fits = final_fit(m, dataset, table=table)
        previews[m], parity[m] = params, parity_rows(params, fits, table)
        if max(parity[m].values()) > PARITY_TOL:
            raise BreakError(f"{m}: numpy ↔ stdlib paritesi {parity[m]} > {PARITY_TOL}")
    manifest = write_golden(result, sens, previews, parity)
    print(json.dumps({"run": MODEL_ID, "ledger_sha256": result.log_entry["ledger_sha256"], "info": manifest["info"],
                      "parity": parity}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Eğitim verisinin yüklenmesi ve sürüm doğrulaması. Yalnız stdlib.

Ana kaynak `data/training_table.csv`. V1.5 walk-forward'u ve f1'in kaynak
değeri için tabloda olmayan iki alan, `data/data_version.json`'da hash'i
kayıtlı kaynak dosyalardan okunur (tablo değiştirilmez):

- `target_session_date` (ufuk başına D_h tarihi): TARGETS. Kesin öncelik kuralı
  bunu ister: eğitim satırı ancak target_session_date < tahmin tarihi ise girer.
- `ipo_size_tl` (kaynakta bildirilen arz büyüklüğü): MASTER. f1'in eğitim değeri
  (bkz. borsai/features.py).
- D1..D10 seans tarihleri: SESSIONS (`target_session_date`). Tavan modellerinin
  walk-forward sansürü bunu ister (SPEC_CEILING_V0 §2, §9). Fiyat sütunları okunmaz.
  Tavan etiketleri (`ceiling_close_D1..D10`, `ceiling_streak_L`) tablodan okunur.

PB girdileri (`load_pb`) data_version.json'da değildir; dosya sha256'sı burada
sabitlenir (docs/PROVENANCE.md §1 satır 9) ve her okumada denetlenir.

Yükleyici her kaynağın sha256'sını data_version.json ile karşılaştırır, ticker
kümesini, arz fiyatını, pay sayısını ve R_h/Y_h'yi kaynaklar arasında denetler.
Tutarsızlıkta durur; değer düzeltmez.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Mapping, Optional

from .horizons import HORIZONS
from .provenance import ROOT, sha256_file

TABLE_PATH = ROOT / "data" / "training_table.csv"
VERSION_PATH = ROOT / "data" / "data_version.json"
RAW_DIR = ROOT / "data" / "raw"
MASTER_PATH = RAW_DIR / "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv"
TARGETS_PATH = RAW_DIR / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv"
SESSIONS_PATH = RAW_DIR / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv"
PB_PATH = RAW_DIR / "PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv"
PB_SHA256 = "5e52d4d23b4f196ef0fd44fb6d4f4edab0ea326241288b036952c30c5e24a613"
N_SESSIONS = 10

INPUT_COLUMNS: tuple[str, ...] = (
    "ipo_price_tl",
    "shares_offered",
    "post_ipo_share_capital",
    "capital_increase_shares",
    "total_demand_multiple",
)


class DataIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class Target:
    R: str  # kaynak metni (Decimal ile okunur)
    Y: int
    session_date: str
    close: str  # resmi THB kapanışı, kaynak metni (fiyat düzeyi metrikleri için)

    @property
    def R_float(self) -> float:
        return float(self.R)


@dataclass(frozen=True)
class IPORow:
    ticker: str
    first_trading_date: str
    point_in_time_status: str
    inputs: dict  # INPUT_COLUMNS + ipo_size_tl -> kaynak metni ya da None
    total_demand_filter_status: Optional[str]
    targets: dict  # horizon -> Target
    session_dates: tuple = ()  # D1..D10 resmi seans tarihleri (SESSIONS)
    ceiling_close: tuple = ()  # D1..D10 tavan kapanışı (0/1), tablodan
    ceiling_streak: int = -1  # L: D1'den başlayan kesintisiz tavan sayısı (0..10)

    def feature_inputs(self) -> dict:
        """borsai.features.compute_features için anahtar sözcük argümanları."""
        return {**{k: self.inputs[k] for k in INPUT_COLUMNS}, "ipo_size_tl": self.inputs["ipo_size_tl"]}


@dataclass(frozen=True)
class Dataset:
    rows: tuple[IPORow, ...]
    data_version_sha256: str
    table_sha256: str
    outcome_sessions_through: str

    @property
    def tickers(self) -> tuple[str, ...]:
        return tuple(r.ticker for r in self.rows)

    def by_ticker(self) -> dict[str, IPORow]:
        return {r.ticker: r for r in self.rows}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _cell(value: str) -> Optional[str]:
    return None if value in ("", "DATA_NOT_FOUND") else value


def _flag(value: str, label: str) -> int:
    if value not in ("0", "1"):
        raise DataIntegrityError(f"{label}: 0/1 değil ({value!r})")
    return int(value)


def _session_dates(rows: list[dict[str, str]]) -> dict[str, tuple[str, ...]]:
    """ticker -> (D1..D10 target_session_date). Yalnız tarih sütunları okunur."""
    by: dict[str, dict[int, str]] = {}
    for s in rows:
        if s["row_status"] != "OFFICIAL_VERIFIED" or s["conflict_status"] != "NO_CONFLICT":
            raise DataIntegrityError(f"{s['ticker']}/{s['session_number']}: seans OFFICIAL_VERIFIED/NO_CONFLICT değil")
        k = int(s["session_number"])
        slot = by.setdefault(s["ticker"], {})
        if k in slot or not 1 <= k <= N_SESSIONS:
            raise DataIntegrityError(f"{s['ticker']}/{k}: SESSIONS'ta geçersiz ya da tekrarlı seans")
        slot[k] = s["target_session_date"]
    out: dict[str, tuple[str, ...]] = {}
    for tk, slot in by.items():
        if set(slot) != set(range(1, N_SESSIONS + 1)):
            raise DataIntegrityError(f"{tk}: SESSIONS 10 seans içermiyor")
        dates = tuple(slot[k] for k in range(1, N_SESSIONS + 1))
        if list(dates) != sorted(set(dates)):
            raise DataIntegrityError(f"{tk}: seans tarihleri kesin artan değil")
        out[tk] = dates
    return out


def load_dataset() -> Dataset:
    version = json.loads(VERSION_PATH.read_text(encoding="utf-8"))
    table_sha = sha256_file(TABLE_PATH)
    if table_sha != version["sha256"]:
        raise DataIntegrityError(f"training_table.csv sha256 {table_sha} != data_version.json {version['sha256']}")
    for src in version["sources"]:
        actual = sha256_file(ROOT / src["path"])
        if actual != src["sha256"]:
            raise DataIntegrityError(f"{src['path']} sha256 {actual} != data_version.json {src['sha256']}")
    source_paths = {src["path"] for src in version["sources"]}
    for path in (MASTER_PATH, TARGETS_PATH, SESSIONS_PATH):
        if path.relative_to(ROOT).as_posix() not in source_paths:
            raise DataIntegrityError(f"{path.name} data_version.json kaynak listesinde yok")

    table = _read_csv(TABLE_PATH)
    master = {r["ticker"]: r for r in _read_csv(MASTER_PATH)}
    targets_raw = _read_csv(TARGETS_PATH)
    sessions = _session_dates(_read_csv(SESSIONS_PATH))
    if len(table) != version["row_count"] or len({r["ticker"] for r in table}) != len(table):
        raise DataIntegrityError("tablo satır sayısı ya da ticker tekilliği tutmuyor")
    if set(master) != {r["ticker"] for r in table}:
        raise DataIntegrityError("MASTER ile tablo ticker kümesi farklı")
    order = [(r["first_trading_date"], r["ticker"]) for r in table]
    if order != sorted(order):
        raise DataIntegrityError("tablo first_trading_date, ticker sırasında değil")

    targets: dict[tuple[str, str], dict[str, str]] = {}
    for t in targets_raw:
        key = (t["ticker"], t["horizon"])
        if key in targets or t["horizon"] not in HORIZONS:
            raise DataIntegrityError(f"TARGETS'ta geçersiz ya da tekrarlı anahtar {key}")
        if t["row_status"] != "OFFICIAL_VERIFIED" or t["conflict_status"] != "NO_CONFLICT":
            raise DataIntegrityError(f"{key}: hedef OFFICIAL_VERIFIED/NO_CONFLICT değil")
        targets[key] = t

    rows: list[IPORow] = []
    max_session = ""
    for r in table:
        tk = r["ticker"]
        m = master[tk]
        if Decimal(m["ipo_price"]) != Decimal(r["ipo_price_tl"]) or Decimal(m["shares_offered"]) != Decimal(r["shares_offered"]):
            raise DataIntegrityError(f"{tk}: MASTER ile tablo arz fiyatı/pay sayısı farklı")
        if m["first_trading_date"] != r["first_trading_date"]:
            raise DataIntegrityError(f"{tk}: MASTER ile tablo ilk işlem günü farklı")
        tg: dict[str, Target] = {}
        for h in HORIZONS:
            t = targets.get((tk, h))
            if t is None:
                raise DataIntegrityError(f"{tk}/{h}: TARGETS'ta yok")
            if Decimal(t["target_return"]) != Decimal(r[f"R_{h}"]) or int(t["above_ipo_flag"]) != int(r[f"Y_{h}"]):
                raise DataIntegrityError(f"{tk}/{h}: TARGETS ile tablo R/Y farklı")
            if Decimal(t["ipo_price"]) != Decimal(r["ipo_price_tl"]):
                raise DataIntegrityError(f"{tk}/{h}: TARGETS ile tablo arz fiyatı farklı")
            session = t["target_session_date"]
            if (h == "D1" and session != r["first_trading_date"]) or (h != "D1" and session <= r["first_trading_date"]):
                raise DataIntegrityError(f"{tk}/{h}: seans tarihi ilk işlem günüyle tutarsız ({session})")
            max_session = max(max_session, session)
            tg[h] = Target(R=r[f"R_{h}"], Y=int(r[f"Y_{h}"]), session_date=session, close=t["official_close"])
        dates = sessions.get(tk)
        if dates is None or dates[0] != r["first_trading_date"]:
            raise DataIntegrityError(f"{tk}: SESSIONS D1 tarihi ilk işlem günüyle tutarsız")
        if dates[-1] > version["outcome_sessions_through"]:
            raise DataIntegrityError(f"{tk}: D10 seansı {dates[-1]} veri kesiminden sonra")
        for h, d in (("D1", 1), ("D3", 3), ("D5", 5), ("D10", 10)):
            if dates[d - 1] != tg[h].session_date:
                raise DataIntegrityError(f"{tk}/{h}: SESSIONS ile TARGETS seans tarihi farklı")
        closes = tuple(_flag(r[f"ceiling_close_D{k}"], f"{tk}.ceiling_close_D{k}") for k in range(1, N_SESSIONS + 1))
        streak = int(r["ceiling_streak_L"])
        leading = next((i for i, c in enumerate(closes) if c == 0), N_SESSIONS)
        if streak != leading:
            raise DataIntegrityError(f"{tk}: ceiling_streak_L {streak} != baştaki tavan sayısı {leading}")
        inputs = {c: _cell(r[c]) for c in INPUT_COLUMNS}
        inputs["ipo_size_tl"] = _cell(m["ipo_size_tl"])
        rows.append(
            IPORow(
                ticker=tk,
                first_trading_date=r["first_trading_date"],
                point_in_time_status=r["point_in_time_status"],
                inputs=inputs,
                total_demand_filter_status=r["total_demand_filter_status"] or None,
                targets=tg,
                session_dates=dates,
                ceiling_close=closes,
                ceiling_streak=streak,
            )
        )
    if set(sessions) != {r.ticker for r in rows}:
        raise DataIntegrityError("SESSIONS ticker kümesi tabloyla aynı değil")
    if len(targets) != len(rows) * len(HORIZONS):
        raise DataIntegrityError("TARGETS tabloda olmayan satır içeriyor")
    if max_session != version["outcome_sessions_through"]:
        raise DataIntegrityError(
            f"en son hedef seansı {max_session} != data_version.json outcome_sessions_through {version['outcome_sessions_through']}"
        )
    return Dataset(
        rows=tuple(rows),
        data_version_sha256=sha256_file(VERSION_PATH),
        table_sha256=table_sha,
        outcome_sessions_through=max_session,
    )


# ---------------------------------------------------------------------------
# Talep toplama öncesi (PB) girdileri: SPEC_PB_V0 §1
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PBRow:
    ticker: str
    first_trading_date: str
    first_bookbuilding_date: str  # B(k): PB modellerinin bilgi kesimi
    spk_publication_date: str
    price_source_semantics: str
    fields: dict  # PB_REQUIRED_FIELDS -> kaynak metni (borsai.features)


def load_pb(dataset) -> dict[str, PBRow]:
    """PB CSV'si; sha256, ticker kümesi, ilk işlem günleri ve zaman sırası denetlenir.
    `dataset`: Dataset ya da H99'un 99 IPORow'u."""
    from .features import PB_REQUIRED_FIELDS

    actual = sha256_file(PB_PATH)
    if actual != PB_SHA256:
        raise DataIntegrityError(f"{PB_PATH.name} sha256 {actual} != {PB_SHA256}")
    by = {r.ticker: r for r in getattr(dataset, "rows", dataset)}
    out: dict[str, PBRow] = {}
    for r in _read_csv(PB_PATH):
        tk = r["ticker"]
        if tk in out or tk not in by:
            raise DataIntegrityError(f"PB: tekrarlı ya da tabloda olmayan ticker {tk}")
        if r["canonical_first_trading_date"] != by[tk].first_trading_date:
            raise DataIntegrityError(f"PB {tk}: ilk işlem günü tabloyla farklı")
        if r["pit_status"] != "PASS" or not (r["spk_publication_date"] < r["first_bookbuilding_date"] < r["canonical_first_trading_date"]):
            raise DataIntegrityError(f"PB {tk}: zaman sırası SPK yayını < talep toplama < ilk işlem değil")
        out[tk] = PBRow(
            ticker=tk,
            first_trading_date=r["canonical_first_trading_date"],
            first_bookbuilding_date=r["first_bookbuilding_date"],
            spk_publication_date=r["spk_publication_date"],
            price_source_semantics=r["price_source_semantics"],
            fields={f: r[f] for f in PB_REQUIRED_FIELDS},
        )
    if set(out) != set(by):
        raise DataIntegrityError("PB ticker kümesi tabloyla aynı değil")
    return out


# ---------------------------------------------------------------------------
# Faz 7: eğitim tablosu v2 ve tahsis rejimi (SPEC_HAZARD_V1 §3.3, §3.4; docs/SPEC_DEVIATIONS.md J)
#
# data/training_table_v2.csv = H99'un 99 satırı (training_table.csv'nin 31 sütunu hücre hücre aynı) + eski kohortun açık
# kümesinin 71 üyesi (girdiler registry/oot/inputs/<T>.json'dan `registry.model_inputs` ile, sonuçlar data/outcomes_oot/<T>.csv'den
# SPEC_SCORING §3 tanımlarıyla) + ek sütunlar V2_EXTRA_COLUMNS. Kasa (SEALED) üyelerinin hiçbir dosyası okunmaz: yalnız
# `registry.is_open` üyeler dolaşılır. training_table.csv ve data_version.json dokunulmaz. Derleyici data/build_training_table_v2.py
# (ince; mantık burada, yükleyici aynı fonksiyonlarla her satırı yeniden üretip eşitliği sınar).
# ---------------------------------------------------------------------------

TABLE_V2_REL = "data/training_table_v2.csv"
VERSION_V2_REL = "data/data_version_v2.json"
TABLE_V2_PATH = ROOT / TABLE_V2_REL
VERSION_V2_PATH = ROOT / VERSION_V2_REL
BUILDER_V2_REL = "data/build_training_table_v2.py"
COHORT_H99, COHORT_OOT_OPEN = "H99", "OOT_OPEN"
V2_EXTRA_COLUMNS: tuple[str, ...] = ("ipo_size_tl", "cohort", "sale_method", "market", "alloc_regime", "alloc_regime_date",
                                     "tufe_month", "tufe_index")
OOT_PIT_STATUS = "PASS"              # derleyici: registry.inputs_pit_problems(doc) == [] (belge sha + yayım < ilk işlem günü)
_V2_H = {"D1": 1, "D3": 3, "D5": 5, "D10": 10}


def alloc_regime(regime_date: str) -> str:
    """Tahsis ve satış yöntemi rejimi, tek tanım: `registry.ALLOC_REGIMES` tarih kuralı (`registry.compute_regime_tags` ile aynı
    kural; eşdeğerlik testli). `regime_date` rejimin uygulandığı gün = talep toplama başlangıcı (SPEC_DEVIATIONS I8; H99 için
    PB kanıt dosyasının first_bookbuilding_date'i). İlk işlem günü okuması kohort etiketinden 4 üyede ayrışır, ikili r'de hiç
    (SPEC_DEVIATIONS J)."""
    from .registry import ALLOC_BEFORE, ALLOC_REGIMES

    out = ALLOC_BEFORE
    for start, name in ALLOC_REGIMES:
        if regime_date >= start:
            out = name
    return out


@dataclass(frozen=True)
class IPORowV2(IPORow):
    """IPORow + v2 ek sütunları (tahmin girdisi değil: izlenebilirlik; r `predict_hazard.regime_value(alloc_regime)`'dan)."""

    cohort: str = ""
    sale_method: str = ""
    market: str = ""
    alloc_regime: str = ""
    alloc_regime_date: str = ""
    tufe_month: str = ""
    tufe_index: str = ""


def h99_columns() -> list[str]:
    return list(json.loads(VERSION_PATH.read_text(encoding="utf-8"))["columns"])


def v2_columns() -> list[str]:
    return h99_columns() + list(V2_EXTRA_COLUMNS)


def _missing_to_empty(value: Optional[str]) -> str:
    return "" if value in (None, "", "DATA_NOT_FOUND") else value


def _h99_v2_cells(r: dict, master_row: dict, pb_row, tufe_table) -> dict[str, str]:
    from . import tufe

    cells = {c: r[c] for c in h99_columns()}
    t = tufe.index_for(r["first_trading_date"], tufe_table)
    cells.update(ipo_size_tl=_missing_to_empty(master_row["ipo_size_tl"]), cohort=COHORT_H99, sale_method="", market="",
                 alloc_regime=alloc_regime(pb_row.first_bookbuilding_date), alloc_regime_date=pb_row.first_bookbuilding_date,
                 tufe_month=t["month"], tufe_index=t["index"])
    return cells


def open_members(cohort_rows) -> list[dict[str, str]]:
    """Kohortun açık (kasa dışı) etkin üyeleri, (first_trading_date, ticker) sırasıyla. Kasa üyesi döndürülmez."""
    from . import registry as reg

    return [r for r in reg.cohort_members(cohort_rows) if reg.is_open(r["vault"])]


def _oot_v2_cells(member: dict, doc: dict, outcome_rows: list, tufe_table) -> dict[str, str]:
    """Açık üyenin v2 satırı. Sonuç: 10 seansın hepsi OK olmalı (açık küme: 710/710); L = `outcomes.streak`."""
    from . import outcomes as oc
    from . import registry as reg
    from . import tufe

    t, ftd = member["ticker"], member["first_trading_date"]
    if not reg.is_open(member["vault"]):
        raise DataIntegrityError("kasa üyesi v2 tablosuna giremez")
    f = doc["fields"]
    if doc.get("ticker") != t or f["first_trading_date"]["value"] != ftd:
        raise DataIntegrityError(f"{t}: girdi belgesi kohort satırıyla uyuşmuyor")
    mi = reg.model_inputs(doc)
    by_h = {int(r["h"]): r for r in outcome_rows}
    if sorted(by_h) != list(range(1, N_SESSIONS + 1)) or any(r["status"] != oc.STATUS_OK for r in outcome_rows):
        raise DataIntegrityError(f"{t}: sonuç dosyası 10 OK seans değil")
    if by_h[1]["session_date"] != ftd or [by_h[h]["session_date"] for h in sorted(by_h)] != sorted({r["session_date"] for r in outcome_rows}):
        raise DataIntegrityError(f"{t}: seans tarihleri D1 = ilk işlem günü ile başlamıyor ya da kesin artan değil")
    if any(Decimal(r["ipo_price"]) != Decimal(mi["ipo_price_tl"]) for r in outcome_rows):
        raise DataIntegrityError(f"{t}: sonuç dosyasının arz fiyatı girdiyle aynı değil")
    closes = [int(by_h[k]["ceiling_close"]) for k in range(1, N_SESSIONS + 1)]
    L = oc.streak(closes)
    f3 = mi["total_demand_multiple"]
    tu = tufe.index_for(ftd, tufe_table)
    regime_label = reg.parse_regime_tags(member["regime_tags"])["ALLOC_REGIME"]
    rd = f["bookbuilding_start"]["value"]
    if rd is None or alloc_regime(rd) != regime_label:
        raise DataIntegrityError(f"{t}: alloc_regime(talep toplama başlangıcı) kohort etiketiyle aynı değil")
    cells = {
        "ticker": t, "first_trading_date": ftd, "point_in_time_status": OOT_PIT_STATUS,
        "ipo_price_tl": _missing_to_empty(mi["ipo_price_tl"]), "shares_offered": _missing_to_empty(mi["shares_offered"]),
        "post_ipo_share_capital": _missing_to_empty(mi["post_ipo_share_capital"]),
        "capital_increase_shares": _missing_to_empty(mi["capital_increase_shares"]),
        "existing_share_sale_shares": _missing_to_empty(mi["existing_share_sale_shares"]),
        "total_demand_multiple": _missing_to_empty(f3),
        "total_demand_multiple_origin": (f["total_demand_multiple"].get("origin") or "") if f3 is not None else "",
        "total_demand_filter_status": _missing_to_empty(mi["total_demand_filter_status"]),
        "additional_sale_shares": _missing_to_empty(mi["additional_sale_shares"]),
        **{f"R_{h}": by_h[k]["R_h"] for h, k in _V2_H.items()},
        **{f"Y_{h}": by_h[k]["Y_h"] for h, k in _V2_H.items()},
        **{f"ceiling_close_D{k}": str(closes[k - 1]) for k in range(1, N_SESSIONS + 1)},
        "ceiling_streak_L": str(L),
        "ipo_size_tl": _missing_to_empty(mi["ipo_size_tl"]), "cohort": COHORT_OOT_OPEN, "sale_method": member["sale_method"],
        "market": member["market"], "alloc_regime": regime_label, "alloc_regime_date": rd,
        "tufe_month": tu["month"], "tufe_index": tu["index"],
    }
    if any(not cells[f"R_{h}"] or cells[f"Y_{h}"] not in ("0", "1") for h in _V2_H):
        raise DataIntegrityError(f"{t}: R_h/Y_h eksik")
    return {c: cells[c] for c in v2_columns()}


def _inputs_doc(ticker: str) -> dict:
    from . import registry as reg

    return reg.load_inputs(reg.OOT_INPUTS_DIR / f"{ticker}.json")[0]


def _open_files_sha(members, kind: str) -> str:
    """Açık üyelerin girdi (inputs) ya da sonuç (outcomes) dosyalarının birleşik sha256'sı; kod adı dosyaya yazılmaz."""
    from . import outcomes_oot as oo
    from . import registry as reg
    from .provenance import identity_hash

    paths = [(reg.OOT_INPUTS_DIR / f"{m['ticker']}.json") if kind == "inputs" else oo.outcome_path(m["ticker"]) for m in members]
    return identity_hash(sorted(f"{p.name}\t{sha256_file(p)}" for p in paths))


def build_table_v2_rows(*, check_pit: bool = True) -> list[dict[str, str]]:
    """v2 satırları, (first_trading_date, ticker) sırasıyla. `check_pit`: açık üyelerin girdi belgelerinin PIT denetimi
    (`registry.inputs_pit_problems`; kaynak belgeleri sha ile okur)."""
    from . import outcomes_oot as oo
    from . import registry as reg
    from . import tufe

    tt = tufe.load()
    h99 = load_dataset()
    master = {r["ticker"]: r for r in _read_csv(MASTER_PATH)}
    pb = load_pb(h99)
    rows = [_h99_v2_cells(r, master[r["ticker"]], pb[r["ticker"]], tt) for r in _read_csv(TABLE_PATH)]
    for m in open_members(reg.read_cohort()[1]):
        doc = _inputs_doc(m["ticker"])
        if check_pit:
            problems = reg.inputs_pit_problems(doc, root=ROOT)
            if problems:
                raise DataIntegrityError(f"{m['ticker']}: girdi PIT denetimi: {problems[:3]}")
        rows.append(_oot_v2_cells(m, doc, oo.read_outcome_oot(oo.outcome_path(m["ticker"])), tt))
    rows.sort(key=lambda r: (r["first_trading_date"], r["ticker"]))
    return rows


def table_v2_bytes(rows) -> bytes:
    import io

    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=v2_columns(), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def version_v2(table: bytes, rows) -> dict:
    """data/data_version_v2.json içeriği. Kod adı yazılmaz: açık üyelerin dosyaları birleşik sha256 ile pinlenir."""
    from . import registry as reg
    from . import tufe
    from .provenance import sha256_bytes

    members = open_members(reg.read_cohort()[1])
    cohort_raw = reg.COHORT_PATH.read_bytes()
    counts = {COHORT_H99: sum(r["cohort"] == COHORT_H99 for r in rows), COHORT_OOT_OPEN: sum(r["cohort"] == COHORT_OOT_OPEN for r in rows)}
    return {
        "table": TABLE_V2_REL,
        "sha256": sha256_bytes(table),
        "bytes": len(table),
        "row_count": len(rows),
        "column_count": len(v2_columns()),
        "columns": v2_columns(),
        "shared_columns_with": {"table": "data/training_table.csv", "n": len(h99_columns()),
                                "rule": "H99 satırlarında bu sütunlar training_table.csv ile hücre hücre aynı"},
        "cohorts": counts,
        "row_order": "first_trading_date ASC, ticker ASC",
        "encoding": "UTF-8, no BOM, LF",
        "missing_value": "empty cell",
        "first_trading_date_min": rows[0]["first_trading_date"],
        "first_trading_date_max": rows[-1]["first_trading_date"],
        "outcome_sessions_through": json.loads(VERSION_PATH.read_text(encoding="utf-8"))["outcome_sessions_through"],
        "builder": BUILDER_V2_REL,
        "builder_sha256": sha256_file(ROOT / BUILDER_V2_REL),
        "sources": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha256_file(p)}
                    for p in (TABLE_PATH, VERSION_PATH, MASTER_PATH, PB_PATH)],
        "cohort": {"path": reg.COHORT_PATH.relative_to(ROOT).as_posix(), "bytes": len(cohort_raw),
                   "prefix_sha256": sha256_bytes(cohort_raw), "rule": "append-only; ilk `bytes` baytın sha256'sı"},
        "oot_inputs": {"dir": "registry/oot/inputs", "n": len(members), "files_sha256": _open_files_sha(members, "inputs")},
        "oot_outcomes": {"dir": "data/outcomes_oot", "n": len(members), "files_sha256": _open_files_sha(members, "outcomes")},
        "tufe": tufe.pin_of(tufe.load()),
        "sealed_rows": 0,
    }


def load_dataset_v2() -> Dataset:
    """v2 tablosu: sha ve kaynak pinleri; her satır koddan (aynı fonksiyonlarla) yeniden üretilip hücre hücre eşitlenir; H99
    satırlarının 31 sütunu training_table.csv ile aynı; seans tarihleri H99 için SESSIONS (load_dataset), açık üyeler için
    data/outcomes_oot/<T>.csv. Dönen Dataset'in satırları IPORowV2."""
    from . import outcomes_oot as oo
    from . import registry as reg
    from . import tufe
    from .provenance import sha256_bytes

    version = json.loads(VERSION_V2_PATH.read_text(encoding="utf-8"))
    raw = TABLE_V2_PATH.read_bytes()
    table_sha = sha256_bytes(raw)
    if table_sha != version["sha256"] or len(raw) != version["bytes"]:
        raise DataIntegrityError(f"training_table_v2.csv sha256 {table_sha} != data_version_v2.json {version['sha256']}")
    for src in version["sources"]:
        if sha256_file(ROOT / src["path"]) != src["sha256"]:
            raise DataIntegrityError(f"{src['path']} sha256 data_version_v2.json ile aynı değil")
    cohort_raw = reg.COHORT_PATH.read_bytes()
    if sha256_bytes(cohort_raw[:version["cohort"]["bytes"]]) != version["cohort"]["prefix_sha256"]:
        raise DataIntegrityError("kohort dosyasının pinli öneki değişmiş (append-only ihlali)")
    tt = tufe.load()
    try:
        tufe.verify_pin(tt, version["tufe"])
    except tufe.TufeRefusal as exc:
        raise DataIntegrityError(str(exc)) from exc
    members = {m["ticker"]: m for m in open_members(reg.read_cohort()[1])}
    for kind in ("inputs", "outcomes"):
        if _open_files_sha(list(members.values()), kind) != version[f"oot_{kind}"]["files_sha256"]:
            raise DataIntegrityError(f"açık kümenin {kind} dosyaları data_version_v2.json ile aynı değil")
    import io

    reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    if list(reader.fieldnames or []) != v2_columns() or v2_columns() != version["columns"]:
        raise DataIntegrityError("training_table_v2.csv sütunları beklenen değil")
    table = list(reader)
    if len(table) != version["row_count"] or len({r["ticker"] for r in table}) != len(table):
        raise DataIntegrityError("v2 satır sayısı ya da ticker tekilliği tutmuyor")
    order = [(r["first_trading_date"], r["ticker"]) for r in table]
    if order != sorted(order):
        raise DataIntegrityError("v2 tablosu first_trading_date, ticker sırasında değil")
    h99 = load_dataset()
    h99_by = h99.by_ticker()
    h99_table = {r["ticker"]: r for r in _read_csv(TABLE_PATH)}
    master = {r["ticker"]: r for r in _read_csv(MASTER_PATH)}
    pb = load_pb(h99)
    if {r["ticker"] for r in table if r["cohort"] == COHORT_H99} != set(h99_by) or \
            {r["ticker"] for r in table if r["cohort"] == COHORT_OOT_OPEN} != set(members):
        raise DataIntegrityError("v2 kohort kümeleri H99 (99) ve açık küme ile aynı değil")
    rows: list[IPORowV2] = []
    for r in table:
        t = r["ticker"]
        extras = {k: r[k] for k in ("cohort", "sale_method", "market", "alloc_regime", "alloc_regime_date", "tufe_month", "tufe_index")}
        if r["cohort"] == COHORT_H99:
            if r != _h99_v2_cells(h99_table[t], master[t], pb[t], tt):
                raise DataIntegrityError(f"{t}: v2 H99 satırı training_table.csv / kaynaklardan yeniden üretilemiyor")
            base = h99_by[t]
            rows.append(IPORowV2(**{k: getattr(base, k) for k in IPORow.__dataclass_fields__}, **extras))
            continue
        outcome_rows = oo.read_outcome_oot(oo.outcome_path(t))
        if r != _oot_v2_cells(members[t], _inputs_doc(t), outcome_rows, tt):
            raise DataIntegrityError(f"{t}: v2 açık küme satırı girdi/sonuç dosyalarından yeniden üretilemiyor")
        by_h = {int(x["h"]): x for x in outcome_rows}
        inputs = {c: _cell(r[c]) for c in INPUT_COLUMNS}
        inputs["ipo_size_tl"] = _cell(r["ipo_size_tl"])
        targets = {h: Target(R=r[f"R_{h}"], Y=int(r[f"Y_{h}"]), session_date=by_h[k]["session_date"], close=by_h[k]["close_raw"])
                   for h, k in _V2_H.items()}
        rows.append(IPORowV2(
            ticker=t, first_trading_date=r["first_trading_date"], point_in_time_status=r["point_in_time_status"], inputs=inputs,
            total_demand_filter_status=r["total_demand_filter_status"] or None, targets=targets,
            session_dates=tuple(by_h[k]["session_date"] for k in range(1, N_SESSIONS + 1)),
            ceiling_close=tuple(int(r[f"ceiling_close_D{k}"]) for k in range(1, N_SESSIONS + 1)),
            ceiling_streak=int(r["ceiling_streak_L"]), **extras))
    return Dataset(rows=tuple(rows), data_version_sha256=sha256_file(VERSION_V2_PATH), table_sha256=table_sha,
                   outcome_sessions_through=h99.outcome_sessions_through)


# ---------------------------------------------------------------------------
# Faz 7C: düşen arz modeli v0 eğitim kümeleri (SPEC_C_V0 §1.3, §3.3; SPEC_DEVIATIONS K). Tablolar değişmez; ek satış alanı
# (`additional_sale_shares`) yükleyicinin okuduğu tablodan, aynı sha denetimiyle okunur (v2 yükleyici aynen: IPORow alanı eklenmez).
# ---------------------------------------------------------------------------

FALL_SETS: dict[str, dict[str, object]] = {
    "H99_F3_AS_PRESENT": {"table": "data/training_table.csv", "f3": True},
    "H99_PLUS_OOT_OPEN_F3_AS_PRESENT": {"table": TABLE_V2_REL, "f3": True},
    "H99_PLUS_OOT_OPEN_AS_PRESENT": {"table": TABLE_V2_REL, "f3": False},
}


def additional_sale_shares(dataset: Dataset) -> dict[str, Optional[str]]:
    """ticker -> `additional_sale_shares` kaynak metni (boş / DATA_NOT_FOUND -> None). Tablo, yükleyicinin sha'sıyla
    (`dataset.table_sha256`) eşleşen dosyadır (training_table.csv ya da training_table_v2.csv); ticker kümesi dataset'inkiyle aynı."""
    for path in (TABLE_PATH, TABLE_V2_PATH):
        if sha256_file(path) == dataset.table_sha256:
            break
    else:
        raise DataIntegrityError("ek satış alanı: veri kümesinin tablosu training_table.csv ya da training_table_v2.csv değil")
    rows = _read_csv(path)
    out = {r["ticker"]: _cell(r["additional_sale_shares"]) for r in rows}
    if list(out) != list(dataset.tickers):
        raise DataIntegrityError("ek satış alanı: tablo ticker sırası veri kümesiyle aynı değil")
    return out


def select_fall_training_rows(dataset: Dataset, set_name: str, additional_sale: Mapping[str, Optional[str]]) -> list[IPORow]:
    """SPEC_C_V0 §1.3 eğitim kümeleri, tablo sırasıyla: f3 dolu (gerekiyorsa) VE ek satış alanı dolu. `additional_sale`
    `additional_sale_shares(dataset)`'ten (sentetik testlerde elle)."""
    rule = FALL_SETS[set_name]
    return [r for r in dataset.rows
            if additional_sale.get(r.ticker) is not None and (not rule["f3"] or r.inputs["total_demand_multiple"] is not None)]

"""Build data/training_table.csv and data/data_version.json from data/raw/.

One row per IPO (99). Values are copied as source strings (no float transit);
missing numeric inputs (source sentinel DATA_NOT_FOUND) become empty cells.
Ceiling labels compare the official THB close with the official THM upper
limit of the same session as Decimals; no "+10%" assumption anywhere.

The builder only checks and copies. If a source invariant fails it stops;
it never repairs a value.

Usage: .venv/bin/python data/build_training_table.py
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT_TABLE = ROOT / "data" / "training_table.csv"
OUT_VERSION = ROOT / "data" / "data_version.json"

MASTER = RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv"
READINESS = RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_feature_readiness.csv"
PROVENANCE = RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_provenance.csv"
TARGETS = RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_d1_d3_d5_d10_targets.csv"
SESSIONS = RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv"

HORIZONS = ("D1", "D3", "D5", "D10")
SESSIONS_N = 10
MISSING = "DATA_NOT_FOUND"

# (output column, master column); numeric columns map DATA_NOT_FOUND -> "".
NUMERIC_INPUTS = (
    ("ipo_price_tl", "ipo_price"),
    ("shares_offered", "shares_offered"),
    ("post_ipo_share_capital", "post_ipo_share_capital"),
    ("capital_increase_shares", "capital_increase_shares"),
    ("existing_share_sale_shares", "existing_share_sale"),
    ("total_demand_multiple", "total_demand_multiple"),
)
LABEL_INPUTS = (
    ("total_demand_multiple_origin", "total_demand_multiple_origin"),
    ("total_demand_filter_status", "total_demand_filter_status"),
)
COLUMNS = (
    ["ticker", "first_trading_date", "point_in_time_status"]
    + [c for c, _ in NUMERIC_INPUTS]
    + [c for c, _ in LABEL_INPUTS]
    + ["additional_sale_shares"]
    + [f"R_{h}" for h in HORIZONS]
    + [f"Y_{h}" for h in HORIZONS]
    + [f"ceiling_close_D{k}" for k in range(1, SESSIONS_N + 1)]
    + ["ceiling_streak_L"]
)


class SourceInvariantError(RuntimeError):
    pass


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SourceInvariantError(msg)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def numeric_or_empty(value: str, where: str) -> str:
    if value == MISSING:
        return ""
    try:
        Decimal(value)
    except InvalidOperation:
        raise SourceInvariantError(f"non-numeric value {value!r} at {where}")
    return value


def build_rows() -> list[dict[str, str]]:
    master = read_csv(MASTER)
    readiness = {r["ticker"]: r for r in read_csv(READINESS)}
    provenance = {r["ticker"]: r for r in read_csv(PROVENANCE)}
    targets = read_csv(TARGETS)
    sessions = read_csv(SESSIONS)

    tickers = [r["ticker"] for r in master]
    check(len(tickers) == len(set(tickers)), "duplicate ticker in master")
    check(set(tickers) == set(readiness) == set(provenance), "ticker sets differ across pre-trade files")

    by_session: dict[str, dict[int, dict[str, str]]] = defaultdict(dict)
    for s in sessions:
        k = int(s["session_number"])
        check(k not in by_session[s["ticker"]], f"duplicate session {s['ticker']} {k}")
        by_session[s["ticker"]][k] = s
    check(set(by_session) == set(tickers), "session ticker set differs from master")

    by_target: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for t in targets:
        check(t["horizon"] not in by_target[t["ticker"]], f"duplicate target {t['ticker']} {t['horizon']}")
        by_target[t["ticker"]][t["horizon"]] = t
    check(set(by_target) == set(tickers), "target ticker set differs from master")

    rows = []
    for m in master:
        tk = m["ticker"]
        ftd = m["first_trading_date"]
        pit = provenance[tk]["point_in_time_status"]
        check(pit == readiness[tk]["point_in_time_status"], f"{tk}: point_in_time_status differs")
        check(pit in ("PASS", "UNKNOWN"), f"{tk}: point_in_time_status {pit!r}")
        check(readiness[tk]["first_trading_date"] == ftd, f"{tk}: first_trading_date differs")

        row = {"ticker": tk, "first_trading_date": ftd, "point_in_time_status": pit}
        for out, src in NUMERIC_INPUTS:
            row[out] = numeric_or_empty(m[src], f"{tk}.{src}")
        for out, src in LABEL_INPUTS:
            row[out] = m[src]
        row["additional_sale_shares"] = numeric_or_empty(m["additional_sale_shares"], f"{tk}.additional_sale_shares")

        ses = by_session[tk]
        check(sorted(ses) == list(range(1, SESSIONS_N + 1)), f"{tk}: sessions are not 1..{SESSIONS_N}")
        check(ses[1]["target_session_date"] == ftd, f"{tk}: session 1 date != first_trading_date")
        for k, s in ses.items():
            check(s["first_trading_date"] == ftd, f"{tk} D{k}: first_trading_date differs")
            check(s["row_status"] == "OFFICIAL_VERIFIED" and s["conflict_status"] == "NO_CONFLICT",
                  f"{tk} D{k}: session not OFFICIAL_VERIFIED/NO_CONFLICT")

        for h in HORIZONS:
            t = by_target[tk][h]
            s = ses[int(h[1:])]
            check(t["session_number"] == h[1:], f"{tk} {h}: session_number {t['session_number']}")
            check(t["row_status"] == "OFFICIAL_VERIFIED" and t["conflict_status"] == "NO_CONFLICT",
                  f"{tk} {h}: target not OFFICIAL_VERIFIED/NO_CONFLICT")
            check(t["target_session_date"] == s["target_session_date"], f"{tk} {h}: target date != session date")
            check(Decimal(t["official_close"]) == Decimal(s["close"]), f"{tk} {h}: target close != session close")
            check(Decimal(t["ipo_price"]) == Decimal(m["ipo_price"]), f"{tk} {h}: target ipo_price != master")
            exact = Fraction(t["official_close"]) / Fraction(t["ipo_price"]) - 1
            check(exact == Fraction(int(t["target_return_exact_numerator"]), int(t["target_return_exact_denominator"])),
                  f"{tk} {h}: exact return fraction mismatch")
            check(t["above_ipo_flag"] == ("1" if Decimal(t["official_close"]) > Decimal(t["ipo_price"]) else "0"),
                  f"{tk} {h}: above_ipo_flag inconsistent")
            row[f"R_{h}"] = t["target_return"]
            row[f"Y_{h}"] = t["above_ipo_flag"]

        streak, broken = 0, False
        for k in range(1, SESSIONS_N + 1):
            s = ses[k]
            close, upper = Decimal(s["close"]), Decimal(s["upper_limit"])
            check(close <= upper, f"{tk} D{k}: close above upper limit")
            hit = close == upper
            row[f"ceiling_close_D{k}"] = "1" if hit else "0"
            if hit and not broken:
                streak += 1
            else:
                broken = True
        row["ceiling_streak_L"] = str(streak)
        rows.append(row)

    rows.sort(key=lambda r: (r["first_trading_date"], r["ticker"]))
    return rows


def render(rows: list[dict[str, str]]) -> bytes:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def main() -> None:
    rows = build_rows()
    OUT_TABLE.write_bytes(render(rows))
    sources = [MASTER, READINESS, PROVENANCE, TARGETS, SESSIONS]
    version = {
        "table": "data/training_table.csv",
        "sha256": sha256(OUT_TABLE),
        "bytes": OUT_TABLE.stat().st_size,
        "row_count": len(rows),
        "column_count": len(COLUMNS),
        "columns": list(COLUMNS),
        "row_order": "first_trading_date ASC, ticker ASC",
        "encoding": "UTF-8, no BOM, LF",
        "missing_value": "empty cell (source sentinel DATA_NOT_FOUND)",
        "first_trading_date_min": rows[0]["first_trading_date"],
        "first_trading_date_max": rows[-1]["first_trading_date"],
        "outcome_sessions_through": max(s["target_session_date"] for s in read_csv(SESSIONS)),
        "builder": "data/build_training_table.py",
        "builder_sha256": sha256(Path(__file__).resolve()),
        "sources": [{"path": str(p.relative_to(ROOT)), "sha256": sha256(p)} for p in sources],
    }
    OUT_VERSION.write_text(json.dumps(version, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{OUT_TABLE.relative_to(ROOT)}: {len(rows)} rows, sha256 {version['sha256']}")


if __name__ == "__main__":
    main()

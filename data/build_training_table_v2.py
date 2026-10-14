"""Build data/training_table_v2.csv and data/data_version_v2.json (SPEC_HAZARD_V1 §3.4).

170 rows = H99's 99 rows (the 31 columns of data/training_table.csv copied cell for cell) + the 71 members of the old
cohort's open set (inputs from registry/oot/inputs via borsai.registry.model_inputs, outcomes from data/outcomes_oot with
SPEC_SCORING §3 definitions) + extra columns: ipo_size_tl, cohort, sale_method, market, alloc_regime, alloc_regime_date,
tufe_month, tufe_index. The row logic lives in borsai/data.py (the loader re-derives every row with the same functions).
Only open members are visited; no vault (SEALED) member file is read. data/training_table.csv, data/data_version.json and
data/build_training_table.py are not touched.

Usage: .venv/bin/python data/build_training_table_v2.py [--check]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from borsai import data as dm  # noqa: E402
from borsai.provenance import pretty_json_bytes  # noqa: E402


def build() -> tuple[bytes, bytes, int]:
    rows = dm.build_table_v2_rows(check_pit=True)
    table = dm.table_v2_bytes(rows)
    version = pretty_json_bytes(dm.version_v2(table, rows))
    return table, version, len(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="compare with the files on disk, do not write")
    args = ap.parse_args(argv)
    table, version, n = build()
    if args.check:
        same = {p.name: p.exists() and p.read_bytes() == b for p, b in ((dm.TABLE_V2_PATH, table), (dm.VERSION_V2_PATH, version))}
        print(json.dumps(same))
        return 0 if all(same.values()) else 1
    dm.TABLE_V2_PATH.write_bytes(table)
    dm.VERSION_V2_PATH.write_bytes(version)
    print(f"{dm.TABLE_V2_REL}: {n} rows, sha256 {json.loads(version)['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

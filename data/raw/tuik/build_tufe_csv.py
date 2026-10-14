"""Build data/raw/tuik/tufe_genel_2025_100.csv from the pinned TÜİK table and the bulletin release list.

Inputs (both in data/raw/tuik/, official TÜİK sources; SPEC_HAZARD_V1 §3.2, KARARLAR K3):
  - tufe_degisim_oranlari_bulten_58290.xls: "Tüketici fiyat endeksi ve değişim oranları" [2025=100], downloaded from the
    Ağustos 2026 bulletin page (sha256 pinned in the .source.json next to it);
  - tufe_bultenleri.csv: for every reference month, its own monthly bulletin (id, page, "Yayım Tarihi").

Output columns: month, index, release_date, bulletin_id, source_url, source_sha256 (one row per month, 2019-11 onward).
`index` is the table's value as text (shortest round-trip repr of the stored binary64; at most 6 decimals, checked).
`release_date` is the Europe/Istanbul date of the month's own bulletin; for months before 2026 the value was published in the
2003=100 base at that date and is given here in TÜİK's chained 2025=100 form (rescaling preserves every published rate of
change; the table's own monthly rates are checked against the levels).

The builder only checks and copies; if an invariant fails it stops. A reader for the OLE2/BIFF8 .xls format is included
(stdlib only).

Monthly append (SPEC_HAZARD_V1 §3.2: adding a month is one appended row, not a new data version). Months up to the base table's
last month (2026-08) come from the pinned base table above. Every later month m comes from the table of m's OWN bulletin,
downloaded in the browser from that bulletin page (the server answers command-line clients with 403) and stored next to
the base table as tufe_degisim_oranlari_bulten_<id>.xls + .source.json. That table must (a) end at m, (b) carry the [2025=100]
base, (c) give every earlier month exactly the value already in the CSV (no revision, no rebase, no rechaining: otherwise
stop, a new data version = new model_id) and (d) agree with its own monthly rate for m. The new row names that table
(source_url, source_sha256); existing rows stay byte-identical (borsai.tufe checks the prefix pin):

  .venv/bin/python data/raw/tuik/build_tufe_csv.py --append-month 2026-09 --bulletin-id <id> \
      --release 2026-10-05T10:00:00+03:00 --xls ~/Downloads/<downloaded table>.xls \
      --download-url '<the table's download link>' --sha256 <sha256 of the downloaded file>

The command copies the file under its canonical name, writes its .source.json, appends one line to tufe_bultenleri.csv and
one line to tufe_genel_2025_100.csv, then re-runs the full build and requires it to reproduce the new file byte for byte
(on any failure nothing is left changed). `--check` afterwards reproduces the whole file from the pinned tables.

Usage: .venv/bin/python data/raw/tuik/build_tufe_csv.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import struct
import sys
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_BULLETIN_ID = "58290"                    # Ağustos 2026 bulletin: its table gives every month FIRST_MONTH..2026-08
XLS_NAME = "tufe_degisim_oranlari_bulten_{id}.xls"
SOURCE_NAME = "tufe_degisim_oranlari_bulten_{id}.source.json"
BULLETINS_NAME = "tufe_bultenleri.csv"
OUT_NAME = "tufe_genel_2025_100.csv"
XLS = HERE / XLS_NAME.format(id=BASE_BULLETIN_ID)
XLS_SOURCE = HERE / SOURCE_NAME.format(id=BASE_BULLETIN_ID)
BULLETINS = HERE / BULLETINS_NAME
OUT = HERE / OUT_NAME
TABLE_TITLE = "Tüketici fiyat endeksi ve değişim oranları"
TABLE_BASE = "[2025=100]"
FIRST_MONTH = "2019-11"
COLUMNS = ("month", "index", "release_date", "bulletin_id", "source_url", "source_sha256")
BULLETIN_COLUMNS = ("month", "bulletin_id", "period", "release_datetime", "bulletin_url")
MONTHS_TR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
MAX_DECIMALS = 6
BASE_YEAR_TOLERANCE = Fraction(5, 100)        # SPEC_HAZARD_V1 §11-2: 2025 ortalaması 100.00 ± 0.05
MOM_TOLERANCE = 0.0051                        # tablonun 2 haneli aylık değişimi ile düzeylerden hesaplanan değişim


class SourceInvariantError(RuntimeError):
    pass


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SourceInvariantError(msg)


# ---------------------------------------------------------------- OLE2 / BIFF8 reader (stdlib)

_SIG = bytes.fromhex("D0CF11E0A1B11AE1")
_FREE, _END = 0xFFFFFFFF, 0xFFFFFFFE


def _ole_stream(data: bytes, names: tuple[str, ...] = ("Workbook", "Book")) -> bytes:
    check(data[:8] == _SIG, "not an OLE2 compound file")
    ss = 1 << struct.unpack_from("<H", data, 0x1E)[0]
    mss = 1 << struct.unpack_from("<H", data, 0x20)[0]
    n_fat, dir_start = struct.unpack_from("<II", data, 0x2C)
    mini_cutoff, minifat_start, n_minifat, difat_start, n_difat = struct.unpack_from("<IIIII", data, 0x38)

    def sector(i: int) -> bytes:
        return data[(i + 1) * ss:(i + 2) * ss]

    difat = list(struct.unpack_from("<109I", data, 0x4C))
    s = difat_start
    for _ in range(n_difat):
        entries = struct.unpack_from(f"<{ss // 4}I", sector(s))
        difat += entries[:-1]
        s = entries[-1]
    fat: list[int] = []
    for fs in [x for x in difat if x not in (_FREE, _END)][:n_fat]:
        fat += struct.unpack_from(f"<{ss // 4}I", sector(fs))

    def chain(start: int) -> bytes:
        out, i, seen = [], start, set()
        while i not in (_END, _FREE):
            check(i not in seen, "FAT loop")
            seen.add(i)
            out.append(sector(i))
            i = fat[i]
        return b"".join(out)

    directory = chain(dir_start)
    entries = []
    for k in range(len(directory) // 128):
        e = directory[k * 128:(k + 1) * 128]
        nlen = struct.unpack_from("<H", e, 0x40)[0]
        start, size = struct.unpack_from("<II", e, 0x74)
        entries.append((e[:max(nlen - 2, 0)].decode("utf-16-le"), e[0x42], start, size))
    root = next(e for e in entries if e[1] == 5)
    for name, etype, start, size in entries:
        if etype == 2 and name in names:
            if size >= mini_cutoff:
                return chain(start)[:size]
            ministream = chain(root[2])
            raw = chain(minifat_start) if n_minifat else b""
            minifat = list(struct.unpack_from(f"<{len(raw) // 4}I", raw))
            out, i = [], start
            while i not in (_END, _FREE):
                out.append(ministream[i * mss:(i + 1) * mss])
                i = minifat[i]
            return b"".join(out)[:size]
    raise SourceInvariantError(f"stream {names} not found")


def _rk(v: int) -> float:
    if v & 2:
        x = float(v >> 2 if v < 0x80000000 else (v >> 2) - (1 << 30))
    else:
        x = struct.unpack("<d", struct.pack("<Q", (v & 0xFFFFFFFC) << 32))[0]
    return x / 100 if v & 1 else x


class _Pieces:
    """SST byte source over the record and its CONTINUE records (a string may continue with a new option byte)."""

    def __init__(self, parts: list[bytes]) -> None:
        self.parts, self.i, self.pos = parts, 0, 0

    def take(self, n: int) -> bytes:
        out = b""
        while n > 0:
            p = self.parts[self.i]
            if self.pos >= len(p):
                self.i, self.pos = self.i + 1, 0
                continue
            k = min(n, len(p) - self.pos)
            out += p[self.pos:self.pos + k]
            self.pos += k
            n -= k
        return out

    def chars(self, n: int, compressed: bool) -> str:
        out = []
        while n > 0:
            if self.pos >= len(self.parts[self.i]):
                self.i += 1
                compressed = not (self.parts[self.i][0] & 1)
                self.pos = 1
            p = self.parts[self.i]
            width = 1 if compressed else 2
            k = min(n, (len(p) - self.pos) // width)
            chunk = p[self.pos:self.pos + k * width]
            out.append(chunk.decode("latin-1") if compressed else chunk.decode("utf-16-le"))
            self.pos += k * width
            n -= k
        return "".join(out)


def _sst_string(p: _Pieces) -> str:
    nchars = struct.unpack("<H", p.take(2))[0]
    flags = p.take(1)[0]
    runs = struct.unpack("<H", p.take(2))[0] if flags & 8 else 0
    ext = struct.unpack("<I", p.take(4))[0] if flags & 4 else 0
    s = p.chars(nchars, not (flags & 1))
    p.take(4 * runs)
    p.take(ext)
    return s


def _short_string(data: bytes, off: int, len_bytes: int) -> str:
    n = struct.unpack_from("<H" if len_bytes == 2 else "<B", data, off)[0]
    flags = data[off + len_bytes]
    start = off + len_bytes + 1 + (2 if flags & 8 else 0) + (4 if flags & 4 else 0)
    return data[start:start + 2 * n].decode("utf-16-le") if flags & 1 else data[start:start + n].decode("latin-1")


def read_xls(data: bytes) -> dict[str, dict[tuple[int, int], object]]:
    """{sheet: {(row, col): value}}; numbers binary64, text str. Records: BOUNDSHEET, SST (+CONTINUE), LABELSST, NUMBER, RK,
    MULRK, LABEL, FORMULA (cached result) + STRING."""
    stream = _ole_stream(data)
    recs = []
    pos = 0
    while pos + 4 <= len(stream):
        rtype, rlen = struct.unpack_from("<HH", stream, pos)
        recs.append((pos, rtype, stream[pos + 4:pos + 4 + rlen]))
        pos += 4 + rlen
    sst: list[str] = []
    sheets: list[tuple[str, int]] = []
    for idx, (_, rtype, body) in enumerate(recs):
        if rtype == 0x0085:
            sheets.append((_short_string(body, 6, 1), struct.unpack_from("<I", body, 0)[0]))
        elif rtype == 0x00FC:
            parts = [body]
            j = idx + 1
            while j < len(recs) and recs[j][1] == 0x003C:
                parts.append(recs[j][2])
                j += 1
            p = _Pieces(parts)
            _, unique = struct.unpack("<II", p.take(8))
            sst = [_sst_string(p) for _ in range(unique)]
    by_pos = {pos: k for k, (pos, _, _) in enumerate(recs)}
    out: dict[str, dict[tuple[int, int], object]] = {}
    for name, spos in sheets:
        cells: dict[tuple[int, int], object] = {}
        pending = None
        for _, rtype, body in recs[by_pos[spos] + 1:]:
            if rtype == 0x000A:
                break
            if rtype == 0x00FD:
                r, c, _, i = struct.unpack_from("<HHHI", body, 0)
                cells[(r, c)] = sst[i]
            elif rtype == 0x0203:
                r, c, _ = struct.unpack_from("<HHH", body, 0)
                cells[(r, c)] = struct.unpack_from("<d", body, 6)[0]
            elif rtype == 0x027E:
                r, c, _, v = struct.unpack_from("<HHHI", body, 0)
                cells[(r, c)] = _rk(v)
            elif rtype == 0x00BD:
                r, c0 = struct.unpack_from("<HH", body, 0)
                c1 = struct.unpack_from("<H", body, len(body) - 2)[0]
                for n, c in enumerate(range(c0, c1 + 1)):
                    cells[(r, c)] = _rk(struct.unpack_from("<I", body, 4 + 6 * n + 2)[0])
            elif rtype == 0x0204:
                r, c, _ = struct.unpack_from("<HHH", body, 0)
                cells[(r, c)] = _short_string(body, 6, 2)
            elif rtype == 0x0006:
                r, c, _ = struct.unpack_from("<HHH", body, 0)
                res = body[6:14]
                if res[6:8] == b"\xff\xff":
                    if res[0] == 0:
                        pending = (r, c)
                    else:
                        cells[(r, c)] = bool(res[2]) if res[0] == 1 else None
                else:
                    cells[(r, c)] = struct.unpack("<d", res)[0]
            elif rtype == 0x0207 and pending is not None:
                cells[pending] = _short_string(body, 0, 2)
                pending = None
        out[name] = cells
    return out


# ---------------------------------------------------------------- table -> rows

def next_month(m: str) -> str:
    y, mo = int(m[:4]), int(m[5:7]) + 1
    return f"{y + (mo > 12):04d}-{(mo - 1) % 12 + 1:02d}"


def _block(cells: dict, start_row: int, stop_row: int) -> dict[str, float]:
    out: dict[str, float] = {}
    for r in range(start_row, stop_row):
        year = cells.get((r, 0))
        if not isinstance(year, float):
            continue
        check(year == int(year), f"row {r}: year {year!r}")
        for c in range(1, 13):
            v = cells.get((r, c))
            if v is None:
                continue
            check(isinstance(v, float), f"row {r} col {c}: not a number {v!r}")
            out[f"{int(year):04d}-{c:02d}"] = v
    return out


def table_levels(data: bytes) -> tuple[dict[str, float], dict[str, float]]:
    """(index levels, table's own monthly rates of change %) from the TÜİK sheet."""
    sheets = read_xls(data)
    check(len(sheets) == 1, f"expected one sheet, got {list(sheets)}")
    cells = next(iter(sheets.values()))
    check(str(cells.get((0, 0))).startswith("Tüketici fiyat endeksi (TÜFE) ve değişim oranları"), "title row")
    check(cells.get((2, 0)) == "[2025=100]", f"base row {cells.get((2, 0))!r}")
    check(tuple(cells.get((3, c)) for c in range(1, 13)) == MONTHS_TR, "month header")
    check(str(cells.get((5, 1))).strip() == "Endeks - Index", "levels block header")
    labels = {r: str(cells.get((r, 1))) for r in range(0, 200) if isinstance(cells.get((r, 1)), str)}
    mom_row = next(r for r, t in labels.items() if t.startswith("Bir önceki aya göre değişim (%)"))
    next_block = next(r for r, t in labels.items() if r > mom_row and "(%)" in t)
    return _block(cells, 6, mom_row), _block(cells, mom_row + 1, next_block)


def index_text(v: float) -> str:
    text = repr(v)
    d = Decimal(text)
    check(float(text) == v and d > 0 and -d.as_tuple().exponent <= MAX_DECIMALS, f"index value {text}")
    return text


def read_bulletins(path: Path = BULLETINS) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        check(tuple(reader.fieldnames or ()) == BULLETIN_COLUMNS, f"bulletin columns {reader.fieldnames}")
        return list(reader)


def load_table(bulletin_id: str, here: Path = HERE) -> tuple[dict[str, float], dict[str, float], dict, str]:
    """(levels, monthly rates, source record, sha256) of the pinned table downloaded from bulletin `bulletin_id`."""
    data = (here / XLS_NAME.format(id=bulletin_id)).read_bytes()
    source = json.loads((here / SOURCE_NAME.format(id=bulletin_id)).read_text(encoding="utf-8"))
    sha = hashlib.sha256(data).hexdigest()
    check(sha == source["sha256"] and len(data) == source["bytes"], f"{bulletin_id}: xls sha256/bytes differ from the pinned source record")
    check(str(source["bulletin"]["id"]) == str(bulletin_id) and source["table_base"] == TABLE_BASE, f"{bulletin_id}: source record")
    levels, mom = table_levels(data)
    avg_2025 = sum(Fraction(index_text(levels[f"2025-{m:02d}"])) for m in range(1, 13)) / 12
    check(abs(avg_2025 - 100) <= BASE_YEAR_TOLERANCE, f"{bulletin_id}: 2025 average {float(avg_2025)} is not 100")
    months = sorted(levels)
    for a, b in zip(months, months[1:]):
        check(next_month(a) == b, f"table months not contiguous at {a} -> {b}")
        check(abs((levels[b] / levels[a] - 1) * 100 - mom[b]) <= MOM_TOLERANCE, f"{b}: level change != table's monthly rate")
    return levels, mom, source, sha


def check_bulletin(b: dict[str, str], m: str) -> datetime:
    """The month's own bulletin: period text, id/url form, release on/after the 3rd of the next month, 10:00 Istanbul, weekday."""
    year, mo = int(m[:4]), int(m[5:7])
    check(b["period"] == f"{MONTHS_TR[mo - 1]} {year}", f"{m}: bulletin period {b['period']!r}")
    check(b["bulletin_id"].isdigit() and b["bulletin_url"] == f"https://veriportali.tuik.gov.tr/tr/press/{b['bulletin_id']}",
          f"{m}: bulletin id/url")
    rel = datetime.fromisoformat(b["release_datetime"])
    check(rel.utcoffset() is not None and rel.utcoffset().total_seconds() == 3 * 3600, f"{m}: release not Istanbul time")
    check(rel.strftime("%Y-%m") == next_month(m) and rel.day >= 3 and rel.strftime("%H:%M") == "10:00" and rel.weekday() < 5,
          f"{m}: release {b['release_datetime']} is not on/after the 3rd of the following month at 10:00 on a weekday")
    return rel


def appended_row(m: str, b: dict[str, str], rows: list[dict[str, str]], levels: dict[str, float], mom: dict[str, float],
                 source: dict, sha: str) -> dict[str, str]:
    """Row for a month after the base table, from the table of its own bulletin: the table ends at m and repeats every
    earlier CSV value exactly (no revision / rebase / rechaining; otherwise a new data version is needed)."""
    check(max(levels) == m, f"{m}: the table of bulletin {b['bulletin_id']} ends at {max(levels)}, not at {m}")
    changed = [r["month"] for r in rows if r["month"] not in levels or index_text(levels[r["month"]]) != r["index"]]
    check(not changed, f"{m}: table of bulletin {b['bulletin_id']} changes earlier months {changed[:5]} (revision, rebase or "
                       "rechaining): stop, this is a new data version (new model_id), not an append")
    prev = rows[-1]["month"]
    check(abs((levels[m] / levels[prev] - 1) * 100 - mom[m]) <= MOM_TOLERANCE, f"{m}: level change != table's monthly rate")
    rel = datetime.fromisoformat(b["release_datetime"])
    return {"month": m, "index": index_text(levels[m]), "release_date": rel.date().isoformat(), "bulletin_id": b["bulletin_id"],
            "source_url": source["download_url"], "source_sha256": sha}


def build_rows(here: Path = HERE) -> list[dict[str, str]]:
    levels, _, source, sha = load_table(BASE_BULLETIN_ID, here)
    base_through = max(levels)
    bulletins = read_bulletins(here / BULLETINS_NAME)
    expect = FIRST_MONTH
    rows: list[dict[str, str]] = []
    for b in bulletins:
        m = b["month"]
        check(m == expect, f"bulletin list not contiguous: {m} (expected {expect})")
        expect = next_month(m)
        rel = check_bulletin(b, m)
        if m <= base_through:
            check(m in levels, f"{m}: not in the table")
            rows.append({"month": m, "index": index_text(levels[m]), "release_date": rel.date().isoformat(),
                         "bulletin_id": b["bulletin_id"], "source_url": source["download_url"], "source_sha256": sha})
        else:
            lv, mo, src, s = load_table(b["bulletin_id"], here)
            rows.append(appended_row(m, b, rows, lv, mo, src, s))
    check(rows and rows[-1]["month"] >= base_through, f"bulletin list must reach the base table's last month {base_through}")
    return rows


def render(rows: list[dict[str, str]]) -> bytes:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _csv_line(fields: tuple[str, ...], row: dict[str, str]) -> bytes:
    buf = io.StringIO(newline="")
    csv.DictWriter(buf, fieldnames=fields, lineterminator="\n").writerow(row)
    return buf.getvalue().encode("utf-8")


def append_month(*, month: str, bulletin_id: str, release: str, xls: Path, download_url: str, sha256: str,
                 fetched_at_utc: str | None = None, fetched_by: str = "build_tufe_csv.py --append-month",
                 here: Path = HERE) -> dict[str, str]:
    """Append month `month` (the next month after the CSV's last) from the table of its own bulletin. Validates everything in
    memory first; writes the table copy, its .source.json, one bulletin line and one CSV line; then the full build must
    reproduce the new CSV byte for byte (otherwise every write is undone)."""
    out, bl = here / OUT_NAME, here / BULLETINS_NAME
    old_out, old_bl = out.read_bytes(), bl.read_bytes()
    rows = build_rows(here)
    check(render(rows) == old_out, f"{OUT_NAME} is not reproduced by the current tables: run --check first")
    check(month == next_month(rows[-1]["month"]), f"{month}: the next month to append is {next_month(rows[-1]['month'])}")
    data = Path(xls).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    check(sha == sha256.strip().lower(), f"downloaded table sha256 {sha} != given {sha256}")
    check(download_url.startswith("https://veriportali.tuik.gov.tr/"), "download url is not TÜİK's data portal")
    year, mo = int(month[:4]), int(month[5:7])
    b = {"month": month, "bulletin_id": str(bulletin_id), "period": f"{MONTHS_TR[mo - 1]} {year}", "release_datetime": release,
         "bulletin_url": f"https://veriportali.tuik.gov.tr/tr/press/{bulletin_id}"}
    check_bulletin(b, month)
    levels, mom = table_levels(data)
    source = {"file": f"data/raw/tuik/{XLS_NAME.format(id=bulletin_id)}", "sha256": sha, "bytes": len(data),
              "source_authority": "TUIK_OFFICIAL", "table_title": TABLE_TITLE, "table_base": TABLE_BASE,
              "bulletin": {"id": int(bulletin_id), "title": f"Tüketici Fiyat Endeksi, {b['period']}", "page": b["bulletin_url"],
                           "published_at": release},
              "download_url": download_url,
              "fetched_at_utc": fetched_at_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "fetched_by": fetched_by}
    row = appended_row(month, b, rows, levels, mom, source, sha)
    new_out = old_out + _csv_line(COLUMNS, row)
    xls_path, src_path = here / XLS_NAME.format(id=bulletin_id), here / SOURCE_NAME.format(id=bulletin_id)
    check(not src_path.exists() and (not xls_path.exists() or xls_path.read_bytes() == data),
          f"{xls_path.name} / {src_path.name} already exist")
    copied = not xls_path.exists()
    try:
        if copied:
            xls_path.write_bytes(data)
        src_path.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        bl.write_bytes(old_bl + _csv_line(BULLETIN_COLUMNS, b))
        out.write_bytes(new_out)
        check(render(build_rows(here)) == new_out, "full build does not reproduce the appended file")
    except BaseException:
        out.write_bytes(old_out)
        bl.write_bytes(old_bl)
        src_path.unlink(missing_ok=True)
        if copied:
            xls_path.unlink(missing_ok=True)
        raise
    return {**row, "rows": str(new_out.count(b"\n") - 1), "file_sha256": hashlib.sha256(new_out).hexdigest()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="compare with the file on disk, do not write")
    ap.add_argument("--append-month", metavar="YYYY-MM", help="append this month from the table of its own bulletin")
    ap.add_argument("--bulletin-id", help="--append-month: the month's bulletin number (veriportali.tuik.gov.tr/tr/press/<id>)")
    ap.add_argument("--release", help="--append-month: bulletin release, e.g. 2026-10-05T10:00:00+03:00")
    ap.add_argument("--xls", type=Path, help="--append-month: the downloaded 'Tüketici fiyat endeksi ve değişim oranları' table")
    ap.add_argument("--download-url", help="--append-month: the table's download link on the bulletin page")
    ap.add_argument("--sha256", help="--append-month: sha256 of the downloaded file (recorded at download)")
    ap.add_argument("--fetched-at-utc", help="--append-month: download time, e.g. 2026-10-05T08:30:00Z (default: now)")
    ap.add_argument("--dir", type=Path, default=HERE, help=argparse.SUPPRESS)       # tests: a copy of data/raw/tuik
    args = ap.parse_args(argv)
    here = Path(args.dir)
    if args.append_month:
        missing = [n for n in ("bulletin_id", "release", "xls", "download_url", "sha256") if getattr(args, n) is None]
        if missing:
            ap.error(f"--append-month needs {', '.join('--' + n.replace('_', '-') for n in missing)}")
        res = append_month(month=args.append_month, bulletin_id=args.bulletin_id, release=args.release, xls=args.xls,
                           download_url=args.download_url, sha256=args.sha256, fetched_at_utc=args.fetched_at_utc, here=here)
        print(json.dumps(res, ensure_ascii=False))
        return 0
    out = here / OUT_NAME
    payload = render(build_rows(here))
    if args.check:
        same = out.exists() and out.read_bytes() == payload
        print(json.dumps({"file": out.name, "identical": same}))
        return 0 if same else 1
    if out.exists() and not out.read_bytes() == payload and not payload.startswith(out.read_bytes()):
        raise SourceInvariantError(f"{out.name}: existing rows would change (append-only)")
    out.write_bytes(payload)
    n_rows = payload.count(b"\n") - 1
    print(f"{out.name}: {n_rows} rows, sha256 {hashlib.sha256(payload).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

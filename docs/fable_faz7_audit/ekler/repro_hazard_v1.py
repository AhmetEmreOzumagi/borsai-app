#!/usr/bin/env python3
"""BORSAI_FAZ7_FABLE_V1_REPRO_AUDIT_20260926 — `ceiling_hazard_v1_{clip,real,pooled,pooled@INF}` ailesinin SIFIRDAN, bağımsız
yeniden üretimi (Fable). `borsai` paketi İMPORT EDİLMEZ (alt süreçte sys.modules denetimi); yalnız stdlib + numpy.

Kodlandığı şartnameler: SPEC_HAZARD_V1 §2, §3.1–§3.4, §4, §5.1, §5.4, §6.2, §12; SPEC_CEILING_V0 §2, §4, §5, §8, §9, §10, §12;
SPEC_SCORING §3, §7, §8; SPEC_DEVIATIONS A2, C7, J2 (rejim günü), J10 (f3 filtre dışlaması; proje sahibi kararı). Faz 1B/4/5
bağımsız betiklerimin parçaları (Type-7 kantil, PP tablosu, Newton, blok bootstrap) yeniden kullanıldı.

Girdiler: data/training_table.csv, MASTER (ipo_size_tl), SESSIONS (yalnız tarih sütunları), PB kanıt dosyası (first_bookbuilding_date),
data/raw/tuik/*.csv + /tmp'ye yeniden indirilmiş xls, registry/oot/records/ (kasa kümesi bellekte; yalnız açık üyelerin girdileri
kullanılır), registry/oot/inputs/<açık>.json (bookbuilding_start), data/outcomes_oot/<açık>.csv, data/training_table_v2.csv (yalnız
karşılaştırma), Faz 1B altın tavan ledger'ları (karşılaştırıcı), Faz 7 altın dizini (yalnız karşılaştırma), docs/MODELS.md ve
experiments/log.jsonl (yalnız karşılaştırma). data/outcomes/, data/raw/bist/, scores/ OKUNMAZ; kasa üyesi hiçbir dosya okunmaz
(kayıt dosyalarından yalnız `vault` alanı, kasa kümesini kurmak için). Hiçbir çıktıya kasa kodu yazılmaz.

Çıktı: stdout raporu (ekler/repro_stdout.txt), repro_output.json, repro_ledgers/*.csv (kompakt), sensitivity_runs.jsonl;
tam ledger'lar /tmp/borsai_faz7_audit/repro/ altında (geçici).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import re
import struct
import sys
import time
from collections import Counter, defaultdict
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import numpy as np

assert not any(m == "borsai" or m.startswith("borsai.") for m in sys.modules), "borsai import edilmiş!"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
assert (ROOT / "CLAUDE.md").exists(), ROOT
TMP = Path("/tmp/borsai_faz7_audit")
OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
FULL_DIR = TMP / "repro"
FULL_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "repro_ledgers").mkdir(parents=True, exist_ok=True)
RAW = ROOT / "data" / "raw"
GOLD7 = ROOT / "tests" / "reference" / "macos_golden_faz7"
GOLD1B = ROOT / "tests" / "reference" / "macos_golden_faz1b"
INF = math.inf
GRID = (0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, INF)
GRID_EXT = (0.1, 1.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0, 100.0, 300.0, 1000.0, 3000.0, 10000.0, INF)
GROUP = {1: 0, 2: 1, 3: 1, **{d: 2 for d in range(4, 11)}}
RECLOSE = {**{k: "a" for k in (2, 3, 4)}, **{k: "b" for k in range(5, 11)}}
CTX28 = Context(prec=28, rounding=ROUND_HALF_EVEN)
CTX60 = Context(prec=60, rounding=ROUND_HALF_EVEN)
TOL = 1e-9
NEAR_START = "2024-01-01"
EQUAL_DIST = "EQUAL_DIST_20230330"
ALLOC_RULE = (("2021-11-11", "THRESH100_20211111"), ("2023-03-30", EQUAL_DIST))
ALLOC_BEFORE = "PRE_20211111"
XLS_PIN = "6f7ee8e4ce7e8a7ac79a332db375c4a3179d02162a5d72f684d352aa6c70ff86"
V0_LEDGER_PIN = "976b4dcea9819160bf863873a0a3e3a639942bdfeec6f9229e015047c904665b"
MODELS = ("ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF")
CLIP, REAL, POOLED, PINF = MODELS
OUT: dict = {}
LOG: list[str] = []
T0 = time.time()


def say(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


def rd(path, enc="utf-8-sig"):
    with open(path, encoding=enc, newline="") as fh:
        return list(csv.DictReader(fh))


def ihash(items):
    return hashlib.sha256(("\n".join(items) + "\n").encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def q7(vals, p: Fraction):
    """R Type-7 kantil, kesin Fraction (SPEC_CEILING_V0 §4: Type-7 doğrusal)."""
    vals = sorted(vals)
    n = len(vals)
    if n == 1:
        return vals[0]
    h = Fraction(n - 1) * p + 1
    lo = h.numerator // h.denominator
    fr = h - lo
    if lo == n:
        return vals[-1]
    return vals[lo - 1] + fr * (vals[lo] - vals[lo - 1])


def sigmoid(x):
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def surv(h):
    out, s = [], 1.0
    for x in h:
        s *= 1 - x
        out.append(s)
    return out


def rps(S, L):
    return sum((S[k - 1] - (1.0 if L >= k else 0.0)) ** 2 for k in range(1, 11)) / 10


def month_for(T: str) -> str:
    y, m = int(T[:4]), int(T[5:7]) - 2
    if m <= 0:
        y, m = y - 1, m + 12
    return f"{y:04d}-{m:02d}"


def month_add(m: str, k: int) -> str:
    y, mo = int(m[:4]), int(m[5:7]) - 1 + k
    return f"{y + mo // 12:04d}-{mo % 12 + 1:02d}"


def alloc_regime(day: str) -> str:
    out = ALLOC_BEFORE
    for start, name in ALLOC_RULE:
        if day >= start:
            out = name
    return out


def r_of(label: str) -> int:
    return 0 if label == EQUAL_DIST else 1


def pct(num: Decimal, den: Decimal) -> Decimal:
    """f2 = pay / sermaye × 100: 28 haneli bağlam, 10 ondalık ROUND_HALF_UP, sondaki sıfırlar atılır (borsai.features tanımı, SPEC_CEILING_V0 §4)."""
    with localcontext(CTX28):
        raw = num / den * Decimal(100)
        s = format(raw.quantize(Decimal("1e-10"), rounding=ROUND_HALF_UP), "f").rstrip("0").rstrip(".")
    return Decimal(s or "0")


def size_tl(price, shares, ipo_size):
    if ipo_size not in (None, "", "DATA_NOT_FOUND"):
        return Decimal(ipo_size)
    with localcontext(CTX28):
        return Decimal(shares) * Decimal(price)


# ============================================================ 0. TÜFE (§3.2) — kendi okuyucum
def parse_tufe_csv(path):
    rows = rd(path, enc="utf-8")
    out = {}
    prev = None
    for r in rows:
        assert prev is None or r["month"] == month_add(prev, 1), ("TÜFE ay sürekliliği", prev, r["month"])
        prev = r["month"]
        out[r["month"]] = r
    return out


TUFE = parse_tufe_csv(RAW / "tuik" / "tufe_genel_2025_100.csv")
TUFE_MONTHS = list(TUFE)
BULTEN = {r["month"]: r for r in rd(RAW / "tuik" / "tufe_bultenleri.csv", enc="utf-8")}


def ole_stream(data: bytes, name="Workbook") -> bytes:
    assert data[:8] == bytes.fromhex("D0CF11E0A1B11AE1"), "OLE2 değil"
    ss = 1 << struct.unpack_from("<H", data, 0x1E)[0]
    mss = 1 << struct.unpack_from("<H", data, 0x20)[0]
    n_fat = struct.unpack_from("<I", data, 0x2C)[0]
    dir_start = struct.unpack_from("<I", data, 0x30)[0]
    cutoff = struct.unpack_from("<I", data, 0x38)[0]
    mfat_start, n_mfat, difat_start, n_difat = struct.unpack_from("<IIII", data, 0x3C)
    sec = lambda i: data[(i + 1) * ss:(i + 2) * ss]  # noqa: E731
    difat = list(struct.unpack_from("<109I", data, 0x4C))
    s = difat_start
    for _ in range(n_difat):
        ent = struct.unpack_from(f"<{ss // 4}I", sec(s))
        difat += ent[:-1]
        s = ent[-1]
    fat = []
    for f in [x for x in difat if x < 0xFFFFFFFE][:n_fat]:
        fat += struct.unpack_from(f"<{ss // 4}I", sec(f))

    def chain(start):
        out, i, seen = [], start, set()
        while i < 0xFFFFFFFE:
            assert i not in seen
            seen.add(i)
            out.append(sec(i))
            i = fat[i]
        return b"".join(out)

    d = chain(dir_start)
    entries = []
    for k in range(len(d) // 128):
        e = d[k * 128:(k + 1) * 128]
        nl = struct.unpack_from("<H", e, 0x40)[0]
        entries.append((e[:max(nl - 2, 0)].decode("utf-16-le"), e[0x42], struct.unpack_from("<I", e, 0x74)[0], struct.unpack_from("<I", e, 0x78)[0]))
    root = next(e for e in entries if e[1] == 5)
    for nm, tp, start, size in entries:
        if tp == 2 and nm in (name, "Book"):
            if size >= cutoff:
                return chain(start)[:size]
            mini = chain(root[2])
            mraw = chain(mfat_start) if n_mfat else b""
            mfat = list(struct.unpack_from(f"<{len(mraw) // 4}I", mraw))
            out, i = [], start
            while i < 0xFFFFFFFE:
                out.append(mini[i * mss:(i + 1) * mss])
                i = mfat[i]
            return b"".join(out)[:size]
    raise AssertionError("Workbook akışı yok")


def rk_value(v: int) -> float:
    if v & 2:
        x = float((v >> 2) - (1 << 30) if v & 0x80000000 else v >> 2)
    else:
        x = struct.unpack("<d", struct.pack("<Q", (v & 0xFFFFFFFC) << 32))[0]
    return x / 100 if v & 1 else x


def read_sst(parts: list[bytes]) -> list[str]:
    """SST (+CONTINUE) akışından tekil dizgeler; parça sınırında yeni seçenek baytı gelir."""
    buf, pos, pi = parts[0], 0, 0

    def need(n):
        nonlocal buf, pos, pi
        out = b""
        while n:
            if pos >= len(buf):
                pi += 1
                buf, pos = parts[pi], 0
            k = min(n, len(buf) - pos)
            out += buf[pos:pos + k]
            pos += k
            n -= k
        return out

    def chars(n, wide):
        nonlocal buf, pos, pi
        out = []
        while n:
            if pos >= len(buf):
                pi += 1
                buf, pos = parts[pi], 1
                wide = bool(parts[pi][0] & 1)
            w = 2 if wide else 1
            k = min(n, (len(buf) - pos) // w)
            ch = buf[pos:pos + k * w]
            out.append(ch.decode("utf-16-le") if wide else ch.decode("latin-1"))
            pos += k * w
            n -= k
        return "".join(out)

    total, unique = struct.unpack("<II", need(8))
    out = []
    for _ in range(unique):
        cch = struct.unpack("<H", need(2))[0]
        fl = need(1)[0]
        runs = struct.unpack("<H", need(2))[0] if fl & 8 else 0
        ext = struct.unpack("<I", need(4))[0] if fl & 4 else 0
        out.append(chars(cch, bool(fl & 1)))
        need(4 * runs)
        need(ext)
    return out


def read_xls_cells(data: bytes) -> dict[tuple[int, int], object]:
    st = ole_stream(data)
    recs, pos = [], 0
    while pos + 4 <= len(st):
        t, n = struct.unpack_from("<HH", st, pos)
        recs.append((t, st[pos + 4:pos + 4 + n]))
        pos += 4 + n
    sst = []
    for i, (t, b) in enumerate(recs):
        if t == 0xFC:
            parts = [b]
            j = i + 1
            while j < len(recs) and recs[j][0] == 0x3C:
                parts.append(recs[j][1])
                j += 1
            sst = read_sst(parts)
    cells = {}
    bofs = [i for i, (t, _) in enumerate(recs) if t == 0x809]
    assert len(bofs) >= 2, "sayfa BOF yok"
    for t, b in recs[bofs[1] + 1:]:
        if t == 0x0A:
            break
        if t == 0xFD:
            r, c, _, k = struct.unpack_from("<HHHI", b)
            cells[(r, c)] = sst[k]
        elif t == 0x203:
            r, c, _ = struct.unpack_from("<HHH", b)
            cells[(r, c)] = struct.unpack_from("<d", b, 6)[0]
        elif t == 0x27E:
            r, c, _, v = struct.unpack_from("<HHHI", b)
            cells[(r, c)] = rk_value(v)
        elif t == 0xBD:
            r, c0 = struct.unpack_from("<HH", b)
            c1 = struct.unpack_from("<H", b, len(b) - 2)[0]
            for k, c in enumerate(range(c0, c1 + 1)):
                cells[(r, c)] = rk_value(struct.unpack_from("<I", b, 4 + 6 * k + 2)[0])
        elif t == 0x204:
            r, c, _ = struct.unpack_from("<HHH", b)
            n = struct.unpack_from("<H", b, 6)[0]
            fl = b[8]
            cells[(r, c)] = b[9:9 + 2 * n].decode("utf-16-le") if fl & 1 else b[9:9 + n].decode("latin-1")
        elif t == 0x06:
            r, c, _ = struct.unpack_from("<HHH", b)
            res = b[6:14]
            if res[6:8] != b"\xff\xff":
                cells[(r, c)] = struct.unpack("<d", res)[0]
    return cells


def xls_level_blocks(cells):
    """Yıl (0. sütun, sayı) satırlarını art arda bloklara ayır; ilk blok endeks düzeyleri."""
    rows = sorted(r for (r, c) in cells if c == 0 and isinstance(cells[(r, 0)], float) and 1990 <= cells[(r, 0)] <= 2030)
    blocks, cur = [], []
    for r in rows:
        if cur and r != cur[-1] + 1:
            blocks.append(cur)
            cur = []
        cur.append(r)
    if cur:
        blocks.append(cur)
    out = []
    for blk in blocks:
        d = {}
        for r in blk:
            y = int(cells[(r, 0)])
            for c in range(1, 13):
                v = cells.get((r, c))
                if isinstance(v, float):
                    d[f"{y:04d}-{c:02d}"] = v
        out.append(d)
    return out


say("=== 1a. TÜFE (SPEC_HAZARD_V1 §3.2; KARARLAR K3) ===")
xls_path = TMP / "tufe_dl.xls"
xls_sha = sha_file(xls_path)
repo_xls_sha = sha_file(RAW / "tuik" / "tufe_degisim_oranlari_bulten_58290.xls")
say(f"[1a] indirilen tablo sha256 {xls_sha[:16]}… == PROVENANCE pini {XLS_PIN[:16]}…: {xls_sha == XLS_PIN}; repodaki xls aynı: {repo_xls_sha == XLS_PIN}")
cells = read_xls_cells(xls_path.read_bytes())
title = cells.get((0, 0))
base = cells.get((2, 0))
blocks = xls_level_blocks(cells)
levels = blocks[0]
say(f"[1a] başlık: {str(title)[:60]!r}; temel: {base!r}; blok sayısı {len(blocks)}; düzey bloğu {min(levels)}…{max(levels)} ({len(levels)} ay)")
eq = sum(1 for m, r in TUFE.items() if m in levels and float(r["index"]) == levels[m])
neq = [m for m in TUFE if m not in levels or float(r["index"] if False else TUFE[m]["index"]) != levels.get(m)]
say(f"[1a] CSV endeks == xls düzeyi (binary64 eşitliği): {eq}/{len(TUFE)}; eşit olmayan: {neq[:5]}")
avg2025 = sum(Fraction(TUFE[f"2025-{m:02d}"]["index"]) for m in range(1, 13)) / 12
avg2025_xls = sum(Fraction(levels[f"2025-{m:02d}"]) for m in range(1, 13)) / 12
say(f"[1a] 2025 ortalaması: CSV {float(avg2025):.6f}, xls {float(avg2025_xls):.6f}; |−100| ≤ 0.05: {abs(avg2025 - 100) <= Fraction(5, 100)}")
rel_ok = all(r["release_date"][:7] == month_add(m, 1) and int(r["release_date"][8:]) >= 3 for m, r in TUFE.items())
bul_ok = all(BULTEN[m]["release_datetime"][:10] == TUFE[m]["release_date"] and BULTEN[m]["bulletin_id"] == TUFE[m]["bulletin_id"] for m in TUFE)
say(f"[1a] release_date izleyen ayın ≥ 3'ü: {rel_ok}; CSV release_date == bülten listesi: {bul_ok}; aylar {TUFE_MONTHS[0]}…{TUFE_MONTHS[-1]} ({len(TUFE)})")
sample = random.Random(20260926).sample(TUFE_MONTHS, 10)
sample_ok, sample_rows = 0, []
for m in sample:
    bid = BULTEN[m]["bulletin_id"]
    api = json.loads((TMP / "bulten" / f"{bid}.json").read_text(encoding="utf-8"))["data"]
    ok = (api["date"][:10] == TUFE[m]["release_date"] and str(api["number"]) == bid and api["period"] == BULTEN[m]["period"]
          and api["date"] == BULTEN[m]["release_datetime"][:19])
    sample_ok += ok
    sample_rows.append({"month": m, "bulletin_id": bid, "file_release_date": TUFE[m]["release_date"], "api_date": api["date"],
                        "api_period": api["period"], "ok": ok})
say(f"[1a] 10 örnek ay (random.Random(20260926).sample): bülten sayfası (API) yayım tarihi == dosya: {sample_ok}/10 → "
    + ", ".join(f"{r['month']}:{r['api_date'][:10]}" for r in sample_rows))
OUT["tufe"] = {"xls_sha256": xls_sha, "xls_sha_matches_pin": xls_sha == XLS_PIN, "csv_index_equals_xls": eq, "n_months": len(TUFE),
               "avg_2025": float(avg2025), "release_rule_ok": rel_ok, "bulletin_list_ok": bul_ok, "sample": sample_rows, "sample_ok": sample_ok,
               "xls_title": str(title), "xls_base": str(base)}

# ============================================================ 1. veri: H99 (yalnız tablo + MASTER + SESSIONS tarihleri + PB kanıtı)
T99 = rd(ROOT / "data" / "training_table.csv")
MASTER = {r["ticker"]: r for r in rd(RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv")}
PBEV = {r["ticker"]: r for r in rd(RAW / "PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv")}
SESS_PATH = RAW / "HISTORICAL99_OFFICIAL_BIST_OUTCOME_V1_canonical_bist_session_outcomes.csv"
SESSD: dict[str, dict[int, str]] = defaultdict(dict)
for s in rd(SESS_PATH):
    SESSD[s["ticker"]][int(s["session_number"])] = s["target_session_date"]      # yalnız tarih sütunu okunur
assert len(T99) == 99 and all(len(SESSD[r["ticker"]]) == 10 for r in T99)


def unit_h99(r):
    t = r["ticker"]
    return {"ticker": t, "ftd": r["first_trading_date"], "L": int(r["ceiling_streak_L"]),
            "dates": [SESSD[t][k] for k in range(1, 11)], "closes": [int(r[f"ceiling_close_D{k}"]) for k in range(1, 11)],
            "price": r["ipo_price_tl"], "shares": r["shares_offered"], "post": r["post_ipo_share_capital"],
            "capinc": r["capital_increase_shares"], "f3": None if r["total_demand_multiple"] == "" else Decimal(r["total_demand_multiple"]),
            "status": r["total_demand_filter_status"] or None, "ipo_size": MASTER[t]["ipo_size_tl"], "cohort": "H99",
            "regime_date": PBEV[t]["first_bookbuilding_date"]}


UNITS: dict[str, dict] = {r["ticker"]: unit_h99(r) for r in T99}

# ---- eski kohort: kasa kümesi bellekte (kayıtlardan yalnız vault); açık üyelerin S2 kayıtları
SEALED, OPEN_REC = set(), {}
for p in sorted((ROOT / "registry" / "oot" / "records").glob("*/*.json")):
    rec = json.loads(p.read_text(encoding="utf-8"))
    if rec.get("vault") == "SEALED":
        SEALED.add(rec["ticker"])
        continue
    assert rec["record_stage"] == "OOT_PRE_LISTING"
    OPEN_REC[rec["ticker"]] = rec
say(f"[veri] eski kohort kayıtları: kasa {len(SEALED)}, açık {len(OPEN_REC)} (kasa kodları belleğe alındı, basılmaz)")
assert len(SEALED) == 64 and len(OPEN_REC) == 71
COHORT_ROWS = rd(ROOT / "registry" / "oot" / "cohort_pre_h99.csv")


def unit_open(t):
    rec = OPEN_REC[t]
    mi = rec["model_inputs"]
    inp = json.loads((ROOT / rec["inputs"]["path"]).read_text(encoding="utf-8"))
    assert hashlib.sha256((ROOT / rec["inputs"]["path"]).read_bytes()).hexdigest() == rec["inputs"]["sha256"]
    oc = rd(ROOT / "data" / "outcomes_oot" / f"{t}.csv", enc="utf-8")
    by = {int(r["h"]): r for r in oc}
    assert sorted(by) == list(range(1, 11)) and all(r["status"] == "OK" for r in oc), t
    closes_file = [int(by[k]["ceiling_close"]) for k in range(1, 11)]
    closes_mine = [int(Decimal(by[k]["close_raw"]) == Decimal(by[k]["upper_limit_raw"])) for k in range(1, 11)]   # SPEC_SCORING §3
    L = next((i for i, c in enumerate(closes_mine) if c == 0), 10)
    f3 = mi["total_demand_multiple"]
    return {"ticker": t, "ftd": rec["first_trading_date"], "L": L, "dates": [by[k]["session_date"] for k in range(1, 11)],
            "closes": closes_mine, "closes_file": closes_file, "price": mi["ipo_price_tl"], "shares": mi["shares_offered"],
            "post": mi["post_ipo_share_capital"], "capinc": mi["capital_increase_shares"], "f3": None if f3 in (None, "") else Decimal(f3),
            "status": mi["total_demand_filter_status"] or None, "ipo_size": mi["ipo_size_tl"], "cohort": "OOT_OPEN",
            "regime_label": rec["regime_tags"]["ALLOC_REGIME"], "regime_date": inp["fields"]["bookbuilding_start"]["value"],
            "ipo_price_file": {Decimal(r["ipo_price"]) for r in oc}}


for t in OPEN_REC:
    UNITS[t] = unit_open(t)
for u in UNITS.values():
    u["f1"] = size_tl(u["price"], u["shares"], u["ipo_size"])
    u["f2"] = pct(Decimal(u["shares"]), Decimal(u["post"]))
    m = month_for(u["ftd"])
    u["tufe_month"], u["tufe_index"], u["tufe_release"] = m, TUFE[m]["index"], TUFE[m]["release_date"]
    with localcontext(CTX60):
        u["f1r"] = u["f1"] / (Decimal(u["tufe_index"]) / Decimal(100))         # §3.2 f1r_raw (2025 TL)
    u["regime"] = alloc_regime(u["regime_date"])                              # J2: talep toplama başlangıcı
    u["regime_ftd"] = alloc_regime(u["ftd"])                                  # şartname lafzı: ilk işlem günü
    u["r"] = r_of(u["regime"])
ORDER = sorted(UNITS, key=lambda t: (UNITS[t]["ftd"], t))
H99 = [t for t in ORDER if UNITS[t]["cohort"] == "H99"]
OPEN = [t for t in ORDER if UNITS[t]["cohort"] == "OOT_OPEN"]
H99_F3 = [t for t in H99 if UNITS[t]["f3"] is not None]
OPEN_F3 = [t for t in OPEN if UNITS[t]["f3"] is not None]
POOL_F3 = [t for t in ORDER if UNITS[t]["f3"] is not None]
assert len(H99_F3) == 97 and len(OPEN_F3) == 68 and len(POOL_F3) == 165

# ============================================================ 1b. eğitim tablosu v2 (§3.4) — karşılaştırma
say("\n=== 1b. Eğitim tablosu v2 (§3.4, §11-1, §11-3) ===")
V2 = rd(ROOT / "data" / "training_table_v2.csv", enc="utf-8")
V2_BY = {r["ticker"]: r for r in V2}
tt_lines = (ROOT / "data" / "training_table.csv").read_bytes().decode("utf-8").splitlines()
tt_cols = tt_lines[0].split(",")
tt_line_by = {ln.split(",", 1)[0]: ln for ln in tt_lines[1:]}
v2_lines = (ROOT / "data" / "training_table_v2.csv").read_bytes().decode("utf-8").splitlines()
cell_eq = line_eq = 0
for r in V2:
    if r["cohort"] != "H99":
        continue
    src = next(x for x in T99 if x["ticker"] == r["ticker"])
    cell_eq += all(r[c] == src[c] for c in tt_cols)
    line_eq += next(ln for ln in v2_lines[1:] if ln.startswith(r["ticker"] + ",")).startswith(tt_line_by[r["ticker"]] + ",")
say(f"[1b] H99 99 satırı: {len(tt_cols)} paylaşılan sütunda hücre-eşit {cell_eq}/99; satır öneki bayt-eşit {line_eq}/99; "
    f"v2 sıra (ftd, ticker): {[r['ticker'] for r in V2] == ORDER}")
cmp_cols = {"ipo_price_tl": "price", "shares_offered": "shares", "post_ipo_share_capital": "post", "capital_increase_shares": "capinc",
            "first_trading_date": "ftd"}
mism = Counter()
for t in OPEN:
    u, r = UNITS[t], V2_BY[t]
    for col, key in cmp_cols.items():
        mism[col] += (r[col] or None) != (u[key] or None)
    mism["total_demand_multiple"] += (None if r["total_demand_multiple"] == "" else Decimal(r["total_demand_multiple"])) != u["f3"]
    mism["total_demand_filter_status"] += (r["total_demand_filter_status"] or None) != u["status"]
    mism["ipo_size_tl"] += (r["ipo_size_tl"] or None) != (u["ipo_size"] if u["ipo_size"] not in ("", "DATA_NOT_FOUND") else None)
    mism["ceiling_streak_L"] += int(r["ceiling_streak_L"]) != u["L"]
    mism["ceiling_close_D1..10"] += [int(r[f"ceiling_close_D{k}"]) for k in range(1, 11)] != u["closes"]
    mism["closes_file_vs_recomputed"] += u["closes_file"] != u["closes"]
    mism["alloc_regime(v2)"] += r["alloc_regime"] != u["regime"]
    mism["alloc_regime==kohort etiketi"] += u["regime_label"] != u["regime"]
    mism["alloc_regime_date"] += r["alloc_regime_date"] != u["regime_date"]
    mism["tufe_month"] += r["tufe_month"] != u["tufe_month"]
    mism["tufe_index"] += r["tufe_index"] != u["tufe_index"]
    mism["cohort"] += r["cohort"] != "OOT_OPEN"
    mism["ipo_price==sonuç dosyası"] += u["ipo_price_file"] != {Decimal(u["price"])}
    # f1/f2/f3 v2 girdilerinden yeniden hesap
    mism["f1(v2)"] += size_tl(r["ipo_price_tl"], r["shares_offered"], r["ipo_size_tl"]) != u["f1"]
    mism["f2(v2)"] += pct(Decimal(r["shares_offered"]), Decimal(r["post_ipo_share_capital"])) != u["f2"]
for t in H99:
    r = V2_BY[t]
    mism["H99 alloc_regime"] += r["alloc_regime"] != UNITS[t]["regime"] or r["alloc_regime"] != EQUAL_DIST
    mism["H99 tufe"] += (r["tufe_month"], r["tufe_index"]) != (UNITS[t]["tufe_month"], UNITS[t]["tufe_index"])
    mism["H99 ipo_size_tl"] += (r["ipo_size_tl"] or None) != (MASTER[t]["ipo_size_tl"] if MASTER[t]["ipo_size_tl"] not in ("", "DATA_NOT_FOUND") else None)
say("[1b] açık 71 satır, kayıt (S2 model_inputs) + sonuç dosyası + kendi f1/f2/f3/L hesabım ile uyuşmazlık sayıları: "
    + ", ".join(f"{k}: {v}" for k, v in mism.items()))
n_ftd_diff = sum(1 for t in OPEN if UNITS[t]["regime_ftd"] != UNITS[t]["regime"])
n_r_diff = sum(1 for t in OPEN if r_of(UNITS[t]["regime_ftd"]) != UNITS[t]["r"])
say(f"[1b] rejim okuması (J2): talep toplama başlangıcı vs ilk işlem günü — etiket farkı {n_ftd_diff}/71 açık, r farkı {n_r_diff}/71; "
    f"açık r=1: {sum(UNITS[t]['r'] for t in OPEN)}/71 (f3'lü {sum(UNITS[t]['r'] for t in OPEN_F3)}/68)")
# 135 üye (kasa dahil, yalnız kohort dosyasındaki etiket ve ilk işlem günü; kod basılmaz)
diff135 = r_diff135 = n135 = 0
for row in COHORT_ROWS:
    if row["status"] != "MEMBER":
        continue
    tag = dict(p.split("=", 1) for p in row["regime_tags"].split("|") if "=" in p)["ALLOC_REGIME"]
    n135 += 1
    diff135 += tag != alloc_regime(row["first_trading_date"])
    r_diff135 += r_of(tag) != r_of(alloc_regime(row["first_trading_date"]))
say(f"[1b] 135 üyede (kohort dosyası, kasa dahil, yalnız sayı): etiket ≠ alloc_regime(ilk işlem günü): {diff135}; r farkı: {r_diff135}")
Ldist = dict(sorted(Counter(UNITS[t]["L"] for t in OPEN).items()))
say(f"[1b] açık 71 L dağılımı: {Ldist} == beklenen {{0:9,1:11,2:5,3:4,4:3,5:8,6:5,7:6,8:5,9:6,10:9}}: "
    f"{Ldist == {0: 9, 1: 11, 2: 5, 3: 4, 4: 3, 5: 8, 6: 5, 7: 6, 8: 5, 9: 6, 10: 9}}")


def pp_rows(t, cutoff=None):
    u = UNITS[t]
    out = []
    for d in range(1, 11):
        if d - 1 > u["L"]:
            break
        if cutoff is not None and u["dates"][d - 1] >= cutoff:
            break
        out.append((t, d, GROUP[d], 1 if u["L"] == d - 1 else 0))
    return out


def pp_counts(tickers):
    rows = [r for t in tickers for r in pp_rows(t)]
    ev, risk = [0, 0, 0], [0, 0, 0]
    for r in rows:
        risk[r[2]] += 1
        ev[r[2]] += r[3]
    return len(rows), sum(r[3] for r in rows), list(zip(ev, risk))


c_h, c_o, c_p = pp_counts(H99_F3), pp_counts(OPEN_F3), pp_counts(POOL_F3)
say(f"[1b] PP: H99 f3'lü {c_h[0]}/{c_h[1]} (beklenen 506/83); açık f3'lü {c_o[0]}/{c_o[1]} (374/59); havuz {c_p[0]}/{c_p[1]} (880/142); "
    f"grup olay/risk {c_p[2]} (beklenen [(25,165),(31,258),(86,457)])")
say(f"[1b] açık üyelerin son seansı: {max(UNITS[t]['dates'][-1] for t in OPEN)}; ilk H99 ilk işlem: {UNITS[H99[0]]['ftd']}")
OUT["table_v2"] = {"h99_cells_equal": cell_eq, "h99_line_prefix_equal": line_eq, "open_mismatch_counts": dict(mism),
                   "regime_reading_diff_open": n_ftd_diff, "regime_r_diff_open": n_r_diff, "regime_diff_135": diff135, "r_diff_135": r_diff135,
                   "L_dist_open": Ldist, "pp": {"h99": c_h[:2], "open": c_o[:2], "pool": c_p[:2], "groups": c_p[2]}}

# ============================================================ 2. ön işleme (§3.1; SPEC_CEILING_V0 §4), fit (§4), λ seçimi (§5)
FEATS = {CLIP: ("f1", "f2", "f3"), REAL: ("f1r", "f2", "f3"), POOLED: ("f1r", "f2", "f3"), PINF: ()}
LOGCOL = {"f1", "f1r"}


def raw_of(t, feats):
    u = UNITS[t]
    return {c: Fraction(u[c]) for c in feats}


class Prep:
    """Arz düzeyi ön işleme: winsor (Type-7 [p05, p95], ham değer) -> ln (f1/f1r) -> z (nüfus std). Yalnız eğitim kümesinden."""

    def __init__(self, tickers, feats):
        self.feats = tuple(feats)
        raw = {t: raw_of(t, feats) for t in tickers}
        self.lo, self.hi = {}, {}
        for c in feats:
            vals = [raw[t][c] for t in tickers]
            self.lo[c], self.hi[c] = q7(vals, Fraction(1, 20)), q7(vals, Fraction(19, 20))
        X = {t: self._struct(raw[t]) for t in tickers}
        self.cols, self.mean, self.std = [], {}, {}
        for c in feats:
            v = np.array([X[t][c] for t in tickers], dtype=float)
            if len({X[t][c] for t in tickers}) <= 1:
                continue
            self.cols.append(c)
            self.mean[c], self.std[c] = float(v.mean()), float(v.std(ddof=0))
        self.cols = tuple(self.cols)
        self.Z = {t: self._z(X[t]) for t in tickers}

    def _struct(self, r):
        out = {}
        for c in self.feats:
            v = min(max(r[c], self.lo[c]), self.hi[c])
            out[c] = math.log(v.numerator / v.denominator) if c in LOGCOL else float(v)
        return out

    def _z(self, x):
        return np.array([(x[c] - self.mean[c]) / self.std[c] for c in self.cols])

    def transform(self, t):
        r = raw_of(t, self.feats)
        clipped = {c: not (self.lo[c] <= r[c] <= self.hi[c]) for c in self.feats}
        return self._z(self._struct(r)), clipped

    def params(self):
        return {"winsor": {c: (float(self.lo[c]), float(self.hi[c])) for c in self.feats}, "mean": dict(self.mean), "std": dict(self.std),
                "columns": list(self.cols)}


def gamma_closed(rows):
    ev, risk = np.zeros(3), np.zeros(3)
    for r in rows:
        risk[r[2]] += 1
        ev[r[2]] += r[3]
    return np.log((ev + 0.5) / (risk - ev + 0.5))


def fit_hazard(rows, Z, R, lam, p):
    """Newton, pseudo-satırlı; X = [G | R | Z]; ceza yalnız β'da (γ, δ cezasız). λ = INF: β ≡ 0; R yoksa γ kapalı biçim,
    R varsa (γ, δ) Newton. Dönen (γ, δ, β, yineleme, max|∇|)."""
    q = 0 if R is None else 1
    m = len(rows)
    g = np.array([r[2] for r in rows])
    e = np.r_[np.array([r[3] for r in rows], dtype=float), np.tile([1.0, 0.0], 3)]
    w = np.r_[np.ones(m), np.full(6, 0.5)]
    G = np.zeros((m + 6, 3))
    G[np.arange(m), g] = 1.0
    for i in range(3):
        G[m + 2 * i, i] = G[m + 2 * i + 1, i] = 1.0
    gamma0 = gamma_closed(rows)
    if lam == INF or p == 0:
        if q == 0:
            return gamma0, np.zeros(0), np.zeros(p), 0, 0.0
        X = np.hstack([G, np.r_[R, np.zeros(6)][:, None]])
        pen = np.zeros(4)
        th0 = np.r_[gamma0, 0.0]
        lam_eff = 0.0
    else:
        Zp = np.vstack([np.array([Z[r[0]] for r in rows]).reshape(m, p), np.zeros((6, p))])
        X = np.hstack([G, np.r_[R, np.zeros(6)][:, None], Zp]) if q else np.hstack([G, Zp])
        pen = np.r_[np.zeros(3 + q), np.full(p, lam)]
        th0 = np.r_[gamma0, np.zeros(q + p)]
        lam_eff = lam

    def J(th):
        eta = X @ th
        return float(np.sum(w * (np.logaddexp(0, eta) - e * eta)) + 0.5 * lam_eff * float(th[3 + q:] @ th[3 + q:]))

    th = th0.astype(float)
    it, gmax = 0, math.inf
    Jc = J(th)
    for it in range(150):
        h = 1 / (1 + np.exp(-(X @ th)))
        gr = X.T @ (w * (h - e)) + pen * th
        gmax = float(np.max(np.abs(gr)))
        if gmax <= 1e-11:
            break
        H = (X * (w * h * (1 - h))[:, None]).T @ X + np.diag(pen)
        step = np.linalg.solve(H, gr)
        t0 = 1.0
        while True:
            cand = th - t0 * step
            Jn = J(cand)
            if Jn <= Jc + (len(e) * 2.3e-16) * max(abs(Jc), 1.0) or t0 < 1e-9:      # A2: toplama yuvarlama sınırı
                break
            t0 /= 2
        th, Jc = cand, Jn
    h = 1 / (1 + np.exp(-(X @ th)))
    gmax = float(np.max(np.abs(X.T @ (w * (h - e)) + pen * th)))
    if q:
        return th[:3], th[3:4], (th[4:] if lam != INF and p else np.zeros(p)), it, gmax
    return th[:3], np.zeros(0), th[3:], it, gmax


def etas(gamma, delta, beta, z, r):
    lin = float(beta @ z) if len(beta) else 0.0
    dr = float(delta[0]) * r if len(delta) else 0.0
    return [float(gamma[GROUP[d]]) + dr + lin for d in range(1, 11)]


def filter_mode(statuses):
    usable = [s for s in statuses if s is not None]
    if not usable:
        return None
    cnt = Counter(usable)
    best = max(cnt.values())
    return sorted(s for s, c in cnt.items() if c == best)[0]


EXPLICIT = {"FILTERED", "UNFILTERED"}


def opposite(a, b):
    return a in EXPLICIT and b in EXPLICIT and a != b


def f3_excluded(tickers):
    """J10 (proje sahibi kararı): kümenin f3'lü birimlerinin filtre modu; moda açıkça zıt birimler o kümede kullanılmaz."""
    mode = filter_mode([UNITS[t]["status"] for t in tickers if UNITS[t]["f3"] is not None])
    return tuple(t for t in tickers if UNITS[t]["f3"] is not None and opposite(UNITS[t]["status"], mode)), mode


def reclose(tickers, cutoff):
    n, a = {"a": 0, "b": 0}, {"a": 0, "b": 0}
    for t in tickers:
        u = UNITS[t]
        for k in range(2, 11):
            if u["L"] < k and (cutoff is None or u["dates"][k - 1] < cutoff):
                n[RECLOSE[k]] += 1
                a[RECLOSE[k]] += u["closes"][k - 1]
    return {"n_a": n["a"], "a_a": a["a"], "r_a": (a["a"] + 0.5) / (n["a"] + 1), "n_b": n["b"], "a_b": a["b"], "r_b": (a["b"] + 0.5) / (n["b"] + 1)}


def p_close(S, rc):
    return [S[0]] + [S[k - 1] + (1 - S[k - 1]) * (rc["r_a"] if RECLOSE[k] == "a" else rc["r_b"]) for k in range(2, 11)]


def select_lambda(training, rows_by, feats, use_r, grid, j10=True):
    tot = {lam: 0.0 for lam in grid}
    n = 0
    skipped = 0
    for j in training:
        inner = [t for t in training if t != j]
        if j10:
            exc, mode = f3_excluded(inner)
            inner = [t for t in inner if t not in exc]
        else:
            mode = filter_mode([UNITS[t]["status"] for t in inner])
        if opposite(UNITS[j]["status"], mode):
            skipped += 1
            continue                                        # tutulan birimin f3'ü bu iç kümede boşalır: skorlanmaz (J10)
        prep = Prep(inner, feats)
        p = len(prep.cols)
        irows = [r for t in inner for r in rows_by[t]]
        R = np.array([UNITS[r[0]]["r"] for r in irows], dtype=float) if use_r else None
        zj, _ = prep.transform(j)
        rj = UNITS[j]["r"] if use_r else 0
        for lam in grid:
            gam, dl, bet, _, _ = fit_hazard(irows, prep.Z, R, lam, p)
            hs = [sigmoid(x) for x in etas(gam, dl, bet, zj, rj)]
            for (_, d, _, ev) in rows_by[j]:
                hh = min(max(hs[d - 1], 1e-12), 1 - 1e-12)
                tot[lam] += -(ev * math.log(hh) + (1 - ev) * math.log(1 - hh))
        n += len(rows_by[j])
    score = {lam: tot[lam] / n for lam in grid}
    best = min(score.values())
    return max(lam for lam, s in score.items() if s == best), score, skipped


def fit_set(training, rows, feats, use_r, cutoff, grid, j10=True):
    """Eğitim kümesi (dışlama sonrası, sıralı) -> λ seçimi + nihai fit + ön işleme."""
    rows_by = defaultdict(list)
    for r in rows:
        rows_by[r[0]].append(r)
    if len(grid) > 1:
        lam, score, skipped = select_lambda(training, rows_by, feats, use_r, grid, j10)
    else:
        lam, score, skipped = grid[0], {}, 0
    prep = Prep(training, feats) if feats else None
    p = len(prep.cols) if prep else 0
    R = np.array([UNITS[r[0]]["r"] for r in rows], dtype=float) if use_r else None
    gam, dl, bet, it, gmax = fit_hazard(rows, prep.Z if prep else {}, R, lam, p)
    return {"lambda": lam, "score": score, "prep": prep, "gamma": gam, "delta": dl, "beta": bet, "iters": it, "gmax": gmax,
            "reclose": reclose(training, cutoff), "skipped": skipped}


def predict(fit, t, r_test):
    prep = fit["prep"]
    if prep is not None:
        z, clipped = prep.transform(t)
    else:
        z, clipped = np.zeros(0), {}
    hz = [sigmoid(x) for x in etas(fit["gamma"], fit["delta"], fit["beta"], z, r_test)]
    S = surv(hz)
    return {"hazard": hz, "S": S, "P_close": p_close(S, fit["reclose"]), "clipped": clipped, "z": z}


# ============================================================ 3. fold planları (SPEC_CEILING_V0 §9; SPEC_HAZARD_V1 §5.1; J10)
def plan(pooled: bool, drop_open=(), j10=True):
    tests = H99_F3
    cands_all = POOL_F3 if pooled else H99_F3
    cands_all = [t for t in cands_all if t not in set(drop_open)]
    folds = []
    for k in tests:
        c = UNITS[k]["ftd"]
        cands = [j for j in cands_all if UNITS[j]["ftd"] < c]
        rows = [r for j in cands for r in pp_rows(j, c)]
        training = list(dict.fromkeys(r[0] for r in rows))
        exc, mode = ((), None)
        if pooled and j10:
            exc, mode = f3_excluded(training)
            training = [t for t in training if t not in exc]
            rows = [r for r in rows if r[0] not in exc]
        elif pooled:
            mode = filter_mode([UNITS[t]["status"] for t in training])
        assert k not in training
        dates = [UNITS[r[0]]["dates"][r[1] - 1] for r in rows]
        assert all(d < c for d in dates)
        ev = sum(r[3] for r in rows)
        ok = len(training) >= 10 and ev >= 5 and len(rows) - ev >= 5
        folds.append({"test": k, "T": c, "training": training, "rows": rows, "n_events": ev, "n_surv": len(rows) - ev,
                      "max_date": max(dates) if dates else None, "pp_sha": ihash([f"{r[0]}|{r[1]}|{r[3]}" for r in rows]),
                      "tk_sha": ihash(training), "ok": ok, "excluded": exc, "exc_sha": ihash(exc) if exc else "", "mode": mode,
                      "n_open": sum(1 for t in training if UNITS[t]["cohort"] != "H99"),
                      "n_open_censored": sum(1 for t in set(r[0] for r in rows) if UNITS[t]["cohort"] != "H99" and len(rows_of(rows, t)) < len(pp_rows(t)))})
    return folds


def rows_of(rows, t):
    return [r for r in rows if r[0] == t]


def run_model(model, folds, grid=GRID, use_r=None, feats=None, j10=True, tag=None):
    feats = FEATS[model] if feats is None else feats
    use_r = (model in (POOLED, PINF)) if use_r is None else use_r
    if model == PINF and grid == GRID:
        grid = (INF,)                                         # kural satırı: yalnız λ = INF (iç CV yok)
    ledger = []
    t0 = time.time()
    for f in folds:
        if not f["ok"]:
            continue
        fit = fit_set(f["training"], f["rows"], feats, use_r, f["T"], grid, j10)
        r_test = UNITS[f["test"]]["r"] if use_r else 0
        assert r_test == 0, "H99 test arzında r = 0 olmalı (§3.3)"
        pr = predict(fit, f["test"], r_test)
        u = UNITS[f["test"]]
        row = {"model_id": tag or model, "ticker": f["test"], "first_trading_date": f["T"], "training_n_ipo": len(f["training"]),
               "training_n_pp_rows": len(f["rows"]), "training_n_events": f["n_events"], "training_n_survivals": f["n_surv"],
               "training_max_session_date": f["max_date"], "training_tickers_sha256": f["tk_sha"], "training_pp_sha256": f["pp_sha"],
               "realized_L": u["L"], **{f"realized_close_D{k}": u["closes"][k - 1] for k in range(1, 11)},
               "training_n_oot_open": f["n_open"], "training_n_filter_excluded": len(f["excluded"]), "training_filter_excluded_sha256": f["exc_sha"],
               "filter_mode": f["mode"], "test_tufe_month": u["tufe_month"], "test_tufe_index": u["tufe_index"], "status": "FIT_OK",
               "selected_lambda": fit["lambda"], "score": fit["score"], "columns": list(fit["prep"].cols) if fit["prep"] else [],
               "gamma": [float(x) for x in fit["gamma"]], "delta": float(fit["delta"][0]) if len(fit["delta"]) else None,
               "beta": {c: float(b) for c, b in zip(fit["prep"].cols, fit["beta"])} if fit["prep"] else {},
               "iters": fit["iters"], "gmax": fit["gmax"], "test_r": r_test, "test_clipped_f3": bool(pr["clipped"].get("f3", False)),
               "test_clipped_any": any(pr["clipped"].values()), "test_clipped_features": [c for c in (fit["prep"].cols if fit["prep"] else ()) if pr["clipped"].get(c)],
               "hazard": pr["hazard"], "S": pr["S"], "P_close": pr["P_close"], "reclose": fit["reclose"], "cv_skipped": fit["skipped"],
               "prep": fit["prep"].params() if fit["prep"] else None, "z_test": [float(x) for x in pr["z"]]}
        ledger.append(row)
    say(f"[koşu] {tag or model}: {len(ledger)} fold FIT_OK, {time.time() - t0:.0f} s; λ dağılımı "
        f"{dict(Counter('INF' if r['selected_lambda'] == INF else r['selected_lambda'] for r in ledger))}")
    return ledger


def km_rule(folds, last_n=None, tag=""):
    out = []
    for f in folds:
        if not f["ok"]:
            continue
        hz = []
        for d in range(1, 11):
            day = sorted((r for r in f["rows"] if r[1] == d), key=lambda r: (UNITS[r[0]]["ftd"], r[0]))
            if last_n is not None:
                day = day[-last_n:]
            if day:
                hz.append(sum(r[3] for r in day) / len(day))
            else:
                hz.append(hz[-1])
        S = surv(hz)
        rc = reclose(f["training"], f["T"])
        u = UNITS[f["test"]]
        out.append({"model_id": tag, "ticker": f["test"], "first_trading_date": f["T"], "realized_L": u["L"], "status": "RULE_OK",
                    **{f"realized_close_D{k}": u["closes"][k - 1] for k in range(1, 11)},
                    "hazard": hz, "S": S, "P_close": p_close(S, rc), "reclose": rc, "training_n_ipo": len(f["training"]),
                    "training_n_pp_rows": len(f["rows"]), "training_n_events": f["n_events"], "training_n_survivals": f["n_surv"],
                    "training_max_session_date": f["max_date"], "training_tickers_sha256": f["tk_sha"], "training_pp_sha256": f["pp_sha"],
                    "training_n_oot_open": f["n_open"], "training_n_filter_excluded": len(f["excluded"]), "training_filter_excluded_sha256": f["exc_sha"]})
    return out


say("\n=== 1c. Fold planları ve altı ledger (§5.1, §11-7; J10) ===")
PLAN_C = plan(False)
PLAN_P = plan(True)
ok_c = [f for f in PLAN_C if f["ok"]]
ok_p = [f for f in PLAN_P if f["ok"]]
V0 = rd(GOLD1B / "ceiling_hazard_v0_fold_ledger.csv", enc="utf-8")
assert sha_file(GOLD1B / "ceiling_hazard_v0_fold_ledger.csv") == V0_LEDGER_PIN
V0_T = [r["ticker"] for r in V0]
say(f"[plan] PLAN_CEILING: {len(PLAN_C)} fold, skorlanabilir {len(ok_c)} (v0 ile aynı ticker ve sıra: {[f['test'] for f in ok_c] == V0_T}); "
    f"ilk fold {ok_c[0]['test']} {ok_c[0]['T']} (eğitim {len(ok_c[0]['training'])} arz, {ok_c[0]['n_events']} olay, {ok_c[0]['n_surv']} sağ kalım)")
say(f"[plan] PLAN_POOLED: {len(PLAN_P)} fold, skorlanabilir {len(ok_p)}; v0'ın 87'si dahil: {set(V0_T) <= {f['test'] for f in ok_p}}; "
    f"dışlamalı fold {sum(1 for f in ok_p if f['excluded'])} (dışlanan birim sayıları {sorted({len(f['excluded']) for f in ok_p if f['excluded']})}); "
    f"mod dağılımı {dict(Counter(f['mode'] for f in ok_p))}; eğitimdeki açık arz {sorted({f['n_open'] for f in ok_p})}; "
    f"açık üyesi sansürlenen fold {sum(1 for f in ok_p if f['n_open_censored'])}")
near_c = [f["test"] for f in ok_c if f["T"] >= NEAR_START]
near_p = [f["test"] for f in ok_p if f["T"] >= NEAR_START]
say(f"[plan] yakın dönem: ceiling {len(near_c)} fold ({len({UNITS[t]['ftd'][:7] for t in near_c})} ay), pooled {len(near_p)}; aynı küme: {set(near_c) == set(near_p)}")
# (ii)/(iii) sızıntı sayımları
leak = {"ceiling_max_date_lt_T": sum(1 for f in ok_c if f["max_date"] < f["T"]), "pooled_max_date_lt_T": sum(1 for f in ok_p if f["max_date"] < f["T"]),
        "pooled_open_rows_lt_T": sum(1 for f in ok_p for r in f["rows"] if UNITS[r[0]]["cohort"] != "H99" and UNITS[r[0]]["dates"][r[1] - 1] < f["T"]),
        "pooled_open_rows_total": sum(1 for f in ok_p for r in f["rows"] if UNITS[r[0]]["cohort"] != "H99"),
        "tufe_release_lt_T_train": sum(1 for f in ok_p for t in f["training"] if UNITS[t]["tufe_release"] < f["T"]),
        "tufe_train_total": sum(len(f["training"]) for f in ok_p),
        "tufe_release_lt_T_test": sum(1 for f in ok_p if UNITS[f["test"]]["tufe_release"] < f["T"]),
        "tufe_release_lt_T_170": sum(1 for t in ORDER if UNITS[t]["tufe_release"] < UNITS[t]["ftd"]),
        "excluded_only_opposite": all(all(opposite(UNITS[t]["status"], f["mode"]) for t in f["excluded"]) for f in ok_p),
        "excluded_per_fold": dict(Counter(len(f["excluded"]) for f in ok_p))}
say(f"[sızıntı] (ii) eğitim max seans < T: ceiling {leak['ceiling_max_date_lt_T']}/{len(ok_c)}, pooled {leak['pooled_max_date_lt_T']}/{len(ok_p)}; "
    f"(iii) açık küme PP satırı seans < T: {leak['pooled_open_rows_lt_T']}/{leak['pooled_open_rows_total']}; J10 dışlananlar yalnız moda zıt: {leak['excluded_only_opposite']}; "
    f"TÜFE yayımı < T: eğitim {leak['tufe_release_lt_T_train']}/{leak['tufe_train_total']}, test {leak['tufe_release_lt_T_test']}/{len(ok_p)}, 170 satır {leak['tufe_release_lt_T_170']}/170")
OUT["plan"] = {"ceiling_folds": len(ok_c), "pooled_folds": len(ok_p), "near_era": len(near_c), "excluded_folds": sum(1 for f in ok_p if f["excluded"]),
               "mode_counts": dict(Counter(f["mode"] for f in ok_p)), "leak": leak}

import os
import pickle
CACHE = FULL_DIR / "runs_cache.pkl"
USE_CACHE = os.environ.get("REPRO_CACHE") == "1" and CACHE.exists()
RUNS: dict[str, list] = {}
if USE_CACHE:
    RUNS = pickle.load(open(CACHE, "rb"))["RUNS"]
    say("[önbellek] ledger koşuları önbellekten (REPRO_CACHE=1; yalnız hata ayıklama yinelemesi)")
else:
    for m in MODELS:
        RUNS[m] = run_model(m, PLAN_P if m in (POOLED, PINF) else PLAN_C)
if not USE_CACHE:
    pickle.dump({"RUNS": dict(RUNS)}, open(CACHE, "wb"))
RUNS["base_km_expanding__pooled"] = km_rule(PLAN_P, None, "base_km_expanding")
RUNS["base_km_last10__pooled"] = km_rule(PLAN_P, 10, "base_km_last10")

# ---- karşılaştırma: altın ledger'lar
GOLD = {m: rd(GOLD7 / f"{m}_fold_ledger.csv", enc="utf-8") for m in RUNS}
MANIFEST = json.loads((GOLD7 / "MANIFEST.json").read_text(encoding="utf-8"))
SUMS = dict(line.split("  ", 1)[::-1] for line in (GOLD7 / "SHA256SUMS").read_text(encoding="utf-8").splitlines())
sha_ok = {m: sha_file(GOLD7 / f"{m}_fold_ledger.csv") == MANIFEST["runs"][m]["ledger_sha256"] == SUMS[f"{m}_fold_ledger.csv"] for m in RUNS}
say(f"[altın] ledger sha256 == MANIFEST == SHA256SUMS: {sha_ok}")


def lam_of(s):
    return INF if s == "INF" else float(s)


def compare_ledger(m, mine, gold):
    gb = {r["ticker"]: r for r in gold}
    res = {"n": len(mine), "exact_mismatch": [], "max_abs": defaultdict(float), "over_tol": [], "order_same": [r["ticker"] for r in gold] == [r["ticker"] for r in mine],
           "lambda_exact": 0, "score_max_abs": 0.0, "exact_ok": 0, "clipped_any_vs_gold_test_clipped": 0, "clipped_f3_vs_gold_test_clipped": 0}
    is_model = "S_1" in gold[0] and "selected_lambda" in gold[0]
    for r in mine:
        g = gb[r["ticker"]]
        exact = {"status": (g["status"], r["status"]), "first_trading_date": (g["first_trading_date"], r["first_trading_date"]),
                 "prediction_date": (g["prediction_date"], r["first_trading_date"]),
                 "training_n_ipo": (int(g["training_n_ipo"]), r["training_n_ipo"]), "training_n_pp_rows": (int(g["training_n_pp_rows"]), r["training_n_pp_rows"]),
                 "training_n_events": (int(g["training_n_events"]), r["training_n_events"]), "training_n_survivals": (int(g["training_n_survivals"]), r["training_n_survivals"]),
                 "training_max_session_date": (g["training_max_session_date"], r["training_max_session_date"]),
                 "training_tickers_sha256": (g["training_tickers_sha256"], r["training_tickers_sha256"]), "training_pp_sha256": (g["training_pp_sha256"], r["training_pp_sha256"]),
                 "realized_L": (int(g["realized_L"]), r["realized_L"]),
                 "realized_close": ([int(g[f"realized_close_D{k}"]) for k in range(1, 11)], [r[f"realized_close_D{k}"] for k in range(1, 11)]),
                 "reclose_n_a": (int(g["reclose_n_a"]), r["reclose"]["n_a"]), "reclose_a_a": (int(g["reclose_a_a"]), r["reclose"]["a_a"]),
                 "reclose_n_b": (int(g["reclose_n_b"]), r["reclose"]["n_b"]), "reclose_a_b": (int(g["reclose_a_b"]), r["reclose"]["a_b"])}
        if "training_n_oot_open" in g:
            exact.update(training_n_oot_open=(int(g["training_n_oot_open"]), r["training_n_oot_open"]),
                         training_n_filter_excluded=(int(g["training_n_filter_excluded"]), r["training_n_filter_excluded"]),
                         training_filter_excluded_sha256=(g["training_filter_excluded_sha256"], r["training_filter_excluded_sha256"]))
        if "test_tufe_month" in g:
            exact.update(test_tufe_month=(g["test_tufe_month"], r["test_tufe_month"]), test_tufe_index=(g["test_tufe_index"], r["test_tufe_index"]))
        num = {}
        if is_model:
            exact.update(selected_lambda=(lam_of(g["selected_lambda"]), r["selected_lambda"]), columns=(json.loads(g["columns"]), r["columns"]),
                         n_lambda_not_converged=(int(g["n_lambda_not_converged"]), 0),
                         test_clipped_features=(json.loads(g["test_clipped_features"]) if g["test_clipped_features"] else [], r["test_clipped_features"]))
            if "test_r_pre_equal" in g:
                exact["test_r_pre_equal"] = (float(g["test_r_pre_equal"]), float(r["test_r"]))
            res["lambda_exact"] += lam_of(g["selected_lambda"]) == r["selected_lambda"]
            res["clipped_any_vs_gold_test_clipped"] += (g["test_clipped"] == "TRUE") == r["test_clipped_any"]
            res["clipped_f3_vs_gold_test_clipped"] += (g["test_clipped"] == "TRUE") == r["test_clipped_f3"]
            for i, gname in enumerate(("g1", "g2", "g3")):
                num[f"gamma_{gname}"] = (float(g[f"gamma_{gname}"]), r["gamma"][i])
            for c in FEATS[m]:
                num[f"beta_{c}"] = (float(g[f"beta_{c}"]), r["beta"].get(c, 0.0))
            if "delta_r_pre_equal" in g:
                num["delta_r_pre_equal"] = (float(g["delta_r_pre_equal"]), r["delta"])
            if g["lambda_score_table"]:
                tab = {lam_of(str(e["lambda"])): e["score"] for e in json.loads(g["lambda_score_table"])}
                for lam in r["score"]:
                    res["score_max_abs"] = max(res["score_max_abs"], abs(tab[lam] - r["score"][lam]))
        for k in range(1, 11):
            num[f"hazard_{k}"] = (float(g[f"hazard_{k}"]), r["hazard"][k - 1])
            num[f"S_{k}"] = (float(g[f"S_{k}"]), r["S"][k - 1])
            num[f"P_close_{k}"] = (float(g[f"P_close_{k}"]), r["P_close"][k - 1])
        num["reclose_r_a"] = (float(g["reclose_r_a"]), r["reclose"]["r_a"])
        num["reclose_r_b"] = (float(g["reclose_r_b"]), r["reclose"]["r_b"])
        bad = [k for k, (a, b) in exact.items() if a != b]
        if bad:
            res["exact_mismatch"].append((r["ticker"], {k: exact[k] for k in bad}))
        else:
            res["exact_ok"] += 1
        for k, (a, b) in num.items():
            d = abs(a - b)
            res["max_abs"][k] = max(res["max_abs"][k], d)
            if d > TOL:
                res["over_tol"].append((r["ticker"], k, a, b))
    res["max_abs"] = dict(res["max_abs"])
    res["worst"] = max(res["max_abs"].values())
    return res


CMP = {}
for m in RUNS:
    CMP[m] = compare_ledger(m, RUNS[m], GOLD[m])
    c = CMP[m]
    extra = f"; λ birebir {c['lambda_exact']}/{c['n']}; λ skor tablosu maks|Δ| {c['score_max_abs']:.2e}" if "S_1" in GOLD[m][0] and "selected_lambda" in GOLD[m][0] else ""
    say(f"[1c] {m}: {c['n']} fold, sıra aynı {c['order_same']}; kimlik/metin sütunları birebir {c['exact_ok']}/{c['n']}{extra}; "
        f"sayısal maks|Δ| = {c['worst']:.2e} (en kötü {max(c['max_abs'], key=c['max_abs'].get)}); |Δ| > 1e-9: {len(c['over_tol'])}")
    if "selected_lambda" in GOLD[m][0]:
        say(f"      test_clipped (altın) == benim f3-kırpma {c['clipped_f3_vs_gold_test_clipped']}/{c['n']}, == herhangi-sütun kırpma "
            f"{c['clipped_any_vs_gold_test_clipped']}/{c['n']}; herhangi-sütun kırpılan fold (benim) {sum(r['test_clipped_any'] for r in RUNS[m])}, f3 kırpılan {sum(r['test_clipped_f3'] for r in RUNS[m])}")
    for x in c["exact_mismatch"][:5]:
        say("      UYUŞMAZLIK:", x)
    for x in c["over_tol"][:5]:
        say("      |Δ| > 1e-9:", x)
OUT["ledger_compare"] = {m: {k: v for k, v in c.items() if k != "over_tol"} | {"over_tol_n": len(c["over_tol"]), "over_tol_head": c["over_tol"][:10]} for m, c in CMP.items()}
OUT["golden_sha_ok"] = sha_ok

# (i) test arzı hiçbir istatistiğe girmiyor: 3 fold'da test arzının özellik ve L'si değiştirilerek fit yeniden kurulur
say("\n=== 2(i). Test arzı sızıntı sınaması (perturbasyon) ===")
pert = []
for f in (ok_c[10], ok_c[40], ok_p[60]):
    m = POOLED if f in ok_p else CLIP
    use_r = m == POOLED
    base_fit = fit_set(f["training"], f["rows"], FEATS[m], use_r, f["T"], GRID)
    u = UNITS[f["test"]]
    saved = {k: u[k] for k in ("f1", "f1r", "f2", "f3", "L", "closes")}
    u["f1"], u["f1r"], u["f2"], u["f3"], u["L"], u["closes"] = u["f1"] * 7, u["f1r"] * 7, u["f2"] + 20, u["f3"] * 5, 10 - u["L"], [1 - c for c in u["closes"]]
    alt_fit = fit_set(f["training"], f["rows"], FEATS[m], use_r, f["T"], GRID)
    u.update(saved)
    same = (alt_fit["lambda"] == base_fit["lambda"] and np.array_equal(alt_fit["gamma"], base_fit["gamma"]) and np.array_equal(alt_fit["beta"], base_fit["beta"])
            and alt_fit["prep"].params() == base_fit["prep"].params() and alt_fit["reclose"] == base_fit["reclose"] and alt_fit["score"] == base_fit["score"])
    pert.append({"model": m, "ticker": f["test"], "T": f["T"], "training_unchanged_bitwise": same})
    say(f"[2i] {m} fold {f['test']} ({f['T']}): test arzının f1/f1r/f2/f3/L/kapanışları değiştirildi → λ, γ, β, kırpma sınırları, μ/σ, reclose, CV skorları bit-eşit: {same}")
OUT["perturbation"] = pert

# ============================================================ 1d. nihai fit önizlemeleri (4)
say("\n=== 1d. Nihai fit önizlemeleri (§11-11; models/'e yazılmadı) ===")
FINAL = {}
for m in MODELS:
    pooled = m in (POOLED, PINF)
    tr = POOL_F3 if pooled else H99_F3
    exc, mode = f3_excluded(tr) if pooled else ((), None)
    tr = [t for t in tr if t not in exc]
    rows = [r for t in tr for r in pp_rows(t)]
    fit = fit_set(tr, rows, FEATS[m], pooled, None, (INF,) if m == PINF else GRID)
    FINAL[m] = {"fit": fit, "n_ipo": len(tr), "n_pp": len(rows), "n_events": sum(r[3] for r in rows), "excluded": exc, "mode": mode,
                "cohort_counts": dict(Counter(UNITS[t]["cohort"] for t in tr))}
    pv = json.loads((GOLD7 / f"{m}_final_fit_preview.json").read_text(encoding="utf-8"))
    d = {}
    d["lambda_exact"] = lam_of(str(pv["lambda"])) == fit["lambda"]
    d["gamma"] = max(abs(a - b) for a, b in zip(pv["gamma"], fit["gamma"]))
    d["beta"] = max([abs(pv["beta"][c] - float(b)) for c, b in zip(fit["prep"].cols, fit["beta"])] or [0.0]) if fit["prep"] else 0.0
    d["delta"] = abs(pv["regime"]["delta"] - float(fit["delta"][0])) if "regime" in pv else 0.0
    if fit["prep"] is not None:
        pp_ = fit["prep"].params()
        d["winsor"] = max(max(abs(pv["preprocessing"]["winsor"][c]["p05"] - pp_["winsor"][c][0]), abs(pv["preprocessing"]["winsor"][c]["p95"] - pp_["winsor"][c][1])) for c in pp_["winsor"])
        d["mean"] = max(abs(pv["preprocessing"]["mean"][c] - pp_["mean"][c]) for c in pp_["mean"])
        d["std"] = max(abs(pv["preprocessing"]["std"][c] - pp_["std"][c]) for c in pp_["std"])
        d["columns_exact"] = pv["preprocessing"]["columns"] == pp_["columns"] and pv["columns"] == pp_["columns"]
        tab = {lam_of(str(e["lambda"])): e["score"] for e in pv["lambda_score_table"]}
        d["score_table"] = max(abs(tab[l] - fit["score"][l]) for l in fit["score"])
        fr = {c: (min(float(raw_of(t, (c,))[c]) for t in tr), max(float(raw_of(t, (c,))[c]) for t in tr)) for c in FEATS[m]}
        d["feature_ranges"] = max(max(abs(pv["feature_ranges"][c]["min"] - fr[c][0]), abs(pv["feature_ranges"][c]["max"] - fr[c][1])) for c in fr)
    d["reclose"] = max(abs(pv["reclose_rates"][k] - fit["reclose"][k]) for k in ("r_a", "r_b"))
    d["reclose_counts_exact"] = all(pv["reclose_rates"][k] == fit["reclose"][k] for k in ("n_a", "a_a", "n_b", "a_b"))
    d["n_exact"] = (pv["training"]["n_ipo"], pv["training"]["n_pp_rows"], pv["training"]["n_events"]) == (len(tr), len(rows), FINAL[m]["n_events"])
    d["cohort_counts_exact"] = pv["training"].get("cohort_counts") == (FINAL[m]["cohort_counts"] if pooled else None)
    d["tickers_sha_exact"] = pv["training"].get("tickers_sha256") == ihash(tr) if "tickers_sha256" in pv["training"] else None
    d["filter_excluded_exact"] = list(pv["training"].get("filter_excluded", [])) == list(exc)
    d["worst"] = max(v for k, v in d.items() if isinstance(v, float))
    FINAL[m]["cmp"] = d
    say(f"[1d] {m}: λ {'INF' if fit['lambda'] == INF else fit['lambda']} (birebir {d['lambda_exact']}); arz/satır/olay {len(tr)}/{len(rows)}/{FINAL[m]['n_events']} "
        f"(birebir {d['n_exact']}); γ {[round(float(x), 4) for x in fit['gamma']]}; β {[round(float(b), 4) for b in fit['beta']]}; δ {round(float(fit['delta'][0]), 4) if len(fit['delta']) else '—'}; "
        f"maks|Δ| {d['worst']:.2e}; sütunlar/kohort/reclose/dışlama birebir {d.get('columns_exact', True)}/{d['cohort_counts_exact']}/{d['reclose_counts_exact']}/{d['filter_excluded_exact']}")
OUT["final_fit"] = {m: {**FINAL[m]["cmp"], "n_ipo": FINAL[m]["n_ipo"], "n_pp": FINAL[m]["n_pp"], "n_events": FINAL[m]["n_events"],
                        "lambda": ("INF" if FINAL[m]["fit"]["lambda"] == INF else FINAL[m]["fit"]["lambda"]),
                        "gamma": [float(x) for x in FINAL[m]["fit"]["gamma"]], "beta": {c: float(b) for c, b in zip(FINAL[m]["fit"]["prep"].cols, FINAL[m]["fit"]["beta"])} if FINAL[m]["fit"]["prep"] else {},
                        "delta": float(FINAL[m]["fit"]["delta"][0]) if len(FINAL[m]["fit"]["delta"]) else None,
                        "score": {("INF" if l == INF else l): s for l, s in FINAL[m]["fit"]["score"].items()},
                        "prep": FINAL[m]["fit"]["prep"].params() if FINAL[m]["fit"]["prep"] else None} for m in MODELS}

# ============================================================ 1e. MODELS.md hücreleri (§5.1, §5.4, §6.2; C7 aralığı)
say("\n=== 1e. Hücreler (§5.1 birincil, ikinciller, merdiven, keşif; C7 aralık) ===")


def boot(diffs, months, seed=20260921, reps=4000):
    by = {}
    for mo, d in zip(months, diffs):
        by.setdefault(mo, []).append(d)
    keys = list(by)
    rng = random.Random(seed)
    out = []
    for _ in range(reps):
        s = []
        for kk in rng.choices(keys, k=len(keys)):
            s += by[kk]
        out.append(sum(s) / len(s))
    out.sort()
    return out[100], out[3899]


def S_of(r):
    return r["S"] if "S" in r else [float(r[f"S_{k}"]) for k in range(1, 11)]


def loss(metric, S, L):
    if metric == "rps":
        return rps(S, L)
    k = int(metric[5:])
    return (S[k - 1] - (1.0 if L >= k else 0.0)) ** 2


def paired(model_rows, other_rows, metric="rps", start=None, end=None):
    other = {r["ticker"]: r for r in other_rows if r["status"] in ("FIT_OK", "RULE_OK")}
    diffs, months, a, b, tk = [], [], [], [], []
    for r in model_rows:
        t = r["first_trading_date"]
        if r["status"] not in ("FIT_OK", "RULE_OK") or (start and t < start) or (end and t >= end) or r["ticker"] not in other:
            continue
        L = int(r["realized_L"])
        la, lb = loss(metric, S_of(r), L), loss(metric, S_of(other[r["ticker"]]), L)
        diffs.append(la - lb)
        months.append(t[:7])
        a.append(la)
        b.append(lb)
        tk.append(r["ticker"])
    if not diffs:
        return None
    ci = list(boot(diffs, months)) if len(diffs) >= 10 and len(set(months)) >= 6 else None
    return {"n": len(diffs), "n_months": len(set(months)), "model": sum(a) / len(a), "rule": sum(b) / len(b), "mean": sum(diffs) / len(diffs), "ci95": ci,
            "wins": sum(1 for d in diffs if d < 0), "losses": sum(1 for d in diffs if d > 0), "ties": sum(1 for d in diffs if d == 0),
            "ties_1e12": sum(1 for d in diffs if abs(d) <= 1e-12), "diffs": dict(zip(tk, diffs)), "months": months}


def label(ci):
    if ci is None:
        return "belirsiz"
    lo, hi = ci
    if lo > 0:
        return "bozuyor"
    if hi <= 0.010:
        return "tolerans içinde"
    return "belirsiz"


def position(d, lo, hi):
    return "altında" if d < lo else ("üstünde" if d > hi else "aralık içinde")


CMPL = {k: rd(GOLD1B / f"{k}_fold_ledger.csv", enc="utf-8") for k in ("ceiling_hazard_v0", "ceiling_hazard_v0@INF", "base_km_expanding", "base_km_last10")}
v0_rps = [rps(S_of(r), int(r["realized_L"])) for r in CMPL["ceiling_hazard_v0"]]
say(f"[1e] v0 karşılaştırıcı ledger sha {V0_LEDGER_PIN[:12]}… pinli; 87-fold ortalama RPS {sum(v0_rps) / 87:.10f} (MODELS.md 0.1503)")
EXP62 = {CLIP: (-0.003, -0.010, 0.005, "tolerans içinde"), REAL: (-0.004, -0.015, 0.008, "tolerans içinde ya da belirsiz"),
         POOLED: (0.002, -0.010, 0.015, "belirsiz olası; bozuyor beklenmiyor"), "pooled_km": (-0.05, -0.08, -0.02, "—")}


def all_cells(runs):
    cells = {}
    for m in MODELS:
        c = paired(runs[m], CMPL["ceiling_hazard_v0"], start=NEAR_START)
        c["label"] = label(c["ci95"])
        cells[("near", m)] = c
        for k in ("base_km_expanding", "ceiling_hazard_v0@INF"):
            cells[("sec", m, k)] = paired(runs[m], CMPL[k], start=NEAR_START)
        for k in (1, 3, 5, 10):
            cells[("brier", m, k)] = paired(runs[m], CMPL["ceiling_hazard_v0"], metric=f"brier{k}", start=NEAR_START)
        cells[("2023", m)] = paired(runs[m], CMPL["ceiling_hazard_v0"], end=NEAR_START)
        cells[("all", m)] = paired(runs[m], CMPL["ceiling_hazard_v0"])
    cells[("ladder", "clip")] = cells[("near", CLIP)]
    cells[("ladder", "real")] = paired(runs[REAL], runs[CLIP], start=NEAR_START)
    cells[("ladder", "pooled")] = paired(runs[POOLED], runs[REAL], start=NEAR_START)
    for m in (POOLED, PINF):
        for key in ("base_km_expanding__pooled", "base_km_last10__pooled"):
            if key in runs:
                cells[("pkm", m, key, "near")] = paired(runs[m], runs[key], start=NEAR_START)
                cells[("pkm", m, key, "all")] = paired(runs[m], runs[key])
                cells[("pkm", m, key, "2023")] = paired(runs[m], runs[key], end=NEAR_START)
    return cells


CELLS = all_cells(RUNS)
GCELLS = all_cells({**GOLD, **{k: [{**r, "S": S_of(r)} for r in v] for k, v in GOLD.items()}})   # Opus ledger'larından aynı hesap


def fmt_cell(c):
    ci = "—" if c["ci95"] is None else f"[{c['ci95'][0]:+.4f}, {c['ci95'][1]:+.4f}]"
    return f"{c['mean']:+.4f} {ci} n={c['n']} ({c['n_months']} ay) {c['wins']}/{c['losses']}/{c['ties']}"


say("[1e] Birincil hücreler (aday − v0, RPS, ilk işlem ≥ 2024-01-01), benim ledger'larımdan:")
for m in MODELS:
    c = CELLS[("near", m)]
    e = EXP62.get(m)
    pos = position(c["mean"], e[1], e[2]) if e else "—"
    say(f"      {m}: {fmt_cell(c)} → {c['label']}; §6.2 konumu: {pos}")
say("[1e] Merdiven: " + "; ".join(f"{k}: {fmt_cell(CELLS[('ladder', k)])}" for k in ("clip", "real", "pooled")))
say("[1e] pooled − base_km_expanding (§6.2 ikincil): " + fmt_cell(CELLS[("sec", POOLED, "base_km_expanding")]) + f" → konum {position(CELLS[('sec', POOLED, 'base_km_expanding')]['mean'], -0.08, -0.02)}")

# --- Opus'un günlüğü (tam hassasiyet) ve Opus ledger'larından hesap ile karşılaştırma
LOGE = {json.loads(l)["model_id"]: json.loads(l) for l in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip() and json.loads(l).get("context") == "faz7_golden"}
cell_cmp = {}
worst_cell = 0.0
for key, c in CELLS.items():
    g = GCELLS[key]
    if c is None or g is None:
        continue
    d = max(abs(c["mean"] - g["mean"]), abs(c["model"] - g["model"]), abs(c["rule"] - g["rule"]),
            (max(abs(c["ci95"][0] - g["ci95"][0]), abs(c["ci95"][1] - g["ci95"][1])) if c["ci95"] and g["ci95"] else 0.0))
    same_counts = (c["n"], c["n_months"], c["wins"], c["losses"], c["ties"]) == (g["n"], g["n_months"], g["wins"], g["losses"], g["ties"])
    cell_cmp["|".join(map(str, key))] = {"max_abs": d, "counts_same": same_counts, "mine": {k: c[k] for k in ("mean", "ci95", "n", "n_months", "wins", "losses", "ties")},
                                         "opus_ledger": {k: g[k] for k in ("mean", "ci95", "n", "n_months", "wins", "losses", "ties")}}
    worst_cell = max(worst_cell, d)
log_cmp = {}
for m in MODELS:
    ne, c = LOGE[m]["near_era"], CELLS[("near", m)]
    log_cmp[m] = {"max_abs": max(abs(ne["mean"] - c["mean"]), abs(ne["ci95"][0] - c["ci95"][0]), abs(ne["ci95"][1] - c["ci95"][1])),
                  "counts_same": (ne["n"], ne["n_months"], ne["model_better_n"], ne["rule_better_n"], ne["tie_n"]) == (c["n"], c["n_months"], c["wins"], c["losses"], c["ties"]),
                  "label_same": ne["label"] == c["label"]}
say(f"[1e] hücreler: benim ledger'ım vs Opus ledger'ından aynı hesap — {len(cell_cmp)} hücrede maks|Δ| {worst_cell:.2e}; sayımlar aynı: "
    f"{sum(v['counts_same'] for v in cell_cmp.values())}/{len(cell_cmp)}; günlükteki near_era ile: " + ", ".join(f"{m.split('_')[-1]} {v['max_abs']:.1e}/{v['label_same']}" for m, v in log_cmp.items()))

# --- MODELS.md metniyle (basılı hassasiyet)
MD = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
SEC = MD.split("## Faz 7: tavan serisi v1")[1].split("## Faz 5: D1 sonrası")[0]
NUM = r"([+-]?\d+\.\d+)"


def md_num(s):
    return float(s.replace("−", "-").replace("+", ""))


md_checks = []


def md_check(name, pattern, vals, labels=None):
    m = re.search(pattern, SEC)
    if not m:
        md_checks.append((name, "SATIR YOK", None))
        return
    got = [md_num(x) for x in m.groups()[:len(vals)]]
    dd = max(abs(a - b) for a, b in zip(got, vals))
    ok = dd <= 5e-5 + 1e-9 and all(f"{v:+.4f}" == f"{g:+.4f}" for v, g in zip(vals, got))
    md_checks.append((name, "OK" if ok else "FARK", dd))


for m in MODELS:
    c = CELLS[("near", m)]
    if m in EXP62:
        e = EXP62[m]
        pat = rf"\| `{re.escape(m)}` \*\*\(BİRİNCİL\)\*\* \| (\d+) \((\d+)\) \| {NUM} \| {NUM} \| {NUM} \| \[{NUM}, {NUM}\] \| (\d+) / (\d+) / (\d+) .*?\| \*\*([^*]+)\*\* \|.*?\| \*\*([^*|]+)\*\* \|"
        mm = re.search(pat, SEC)
        if mm:
            g = mm.groups()
            vals = [c["model"], c["rule"], c["mean"], c["ci95"][0], c["ci95"][1]]
            got = [md_num(x) for x in g[2:7]]
            ok = all(f"{v:+.4f}" == f"{x:+.4f}" for v, x in zip(vals, got)) and (int(g[0]), int(g[1]), int(g[7]), int(g[8]), int(g[9])) == (c["n"], c["n_months"], c["wins"], c["losses"], c["ties"])
            ok = ok and g[10].strip() == c["label"] and position(c["mean"], e[1], e[2]) in g[11]
            md_checks.append((f"birincil {m}", "OK" if ok else "FARK", max(abs(a - b) for a, b in zip(vals, got))))
        else:
            md_checks.append((f"birincil {m}", "SATIR YOK", None))
    for k in ("base_km_expanding", "ceiling_hazard_v0@INF"):
        s = CELLS[("sec", m, k)]
        md_check(f"ikincil {m} − {k}", rf"\| `{re.escape(m)}` \| `{re.escape(k)}` \| RPS \| \d+ \(\d+\) \| {NUM} \| {NUM} \| {NUM} \| \[{NUM}, {NUM}\]", [s["model"], s["rule"], s["mean"], s["ci95"][0], s["ci95"][1]])
    for k in (1, 3, 5, 10):
        s = CELLS[("brier", m, k)]
        md_check(f"Brier k={k} {m}", rf"\| `{re.escape(m)}` \| `ceiling_hazard_v0` \| Brier k = {k} \| \d+ \(\d+\) \| {NUM} \| {NUM} \| {NUM} \| \[{NUM}, {NUM}\]", [s["model"], s["rule"], s["mean"], s["ci95"][0], s["ci95"][1]])
    s = CELLS[("2023", m)]
    md_check(f"keşif 2023 {m}", rf"\| `{re.escape(m)}` \| `ceiling_hazard_v0` \| 2023 fold'ları \| \d+ \(\d+\) \| {NUM} \| {NUM} \| {NUM} \|", [s["model"], s["rule"], s["mean"]])
    s = CELLS[("all", m)]
    md_check(f"keşif bütün {m}", rf"\| `{re.escape(m)}` \| `ceiling_hazard_v0` \| bütün eşleşik fold'lar \| \d+ \(\d+\) \| {NUM} \| {NUM} \| {NUM} \| \[{NUM}, {NUM}\]", [s["model"], s["rule"], s["mean"], s["ci95"][0], s["ci95"][1]])
for m in (POOLED, PINF):
    for key in ("base_km_expanding__pooled", "base_km_last10__pooled"):
        for scope, lab in (("near", "yakın dönem"), ("all", "bütün fold'lar"), ("2023", "2023 fold'ları")):
            s = CELLS[("pkm", m, key, scope)]
            vals = [s["model"], s["rule"], s["mean"]] + ([s["ci95"][0], s["ci95"][1]] if s["ci95"] else [])
            ci_pat = rf" \[{NUM}, {NUM}\]" if s["ci95"] else r" —"
            md_check(f"keşif {m} − {key} {scope}", rf"\| `{re.escape(m)}` \| `{re.escape(key)}` \(havuz planı\) \| {lab} \| \d+ \(\d+\) \| {NUM} \| {NUM} \| {NUM} \|{ci_pat}", vals)
for k, name in (("clip", "kırpmanın payı"), ("real", "deflasyonun payı"), ("pooled", "havuz \\+ rejimin payı")):
    s = CELLS[("ladder", k)]
    md_check(f"merdiven {k}", rf"- {name} \(.*?\): fark {NUM} \[{NUM}, {NUM}\], n = (\d+)", [s["mean"], s["ci95"][0], s["ci95"][1]])
s = CELLS[("near", PINF)]
md_check("kural satırı @INF − v0", rf"Kural satırı `ceiling_hazard_v1_pooled@INF` − v0 \(bilgi; aday değil\): {NUM} \[{NUM}, {NUM}\]", [s["mean"], s["ci95"][0], s["ci95"][1]])
s = CELLS[("sec", POOLED, "base_km_expanding")]
md_check("§6.2 pooled − KM", rf"`ceiling_hazard_v1_pooled` − `base_km_expanding` = {NUM} \[{NUM}, {NUM}\] \(n = \d+\); §6.2 −0.05 \[−0.08, −0.02\] → \*\*aralık içinde\*\*", [s["mean"], s["ci95"][0], s["ci95"][1]])
n_ok = sum(1 for _, st, _ in md_checks if st == "OK")
say(f"[1e] MODELS.md Faz 7 hücreleri (basılı 4 hane, aynı yuvarlama): {n_ok}/{len(md_checks)} tuttu; tutmayan: {[(n, st, d) for n, st, d in md_checks if st != 'OK']}")
# fold özeti satırları (λ dağılımı, kırpma sayıları)
fold_sum = {}
for m in MODELS:
    lam_c = Counter("INF" if r["selected_lambda"] == INF else f"{r['selected_lambda']:g}" for r in RUNS[m])
    fold_sum[m] = {"lambda": dict(lam_c), "clipped_f3": sum(r["test_clipped_f3"] for r in RUNS[m]), "clipped_any": sum(r["test_clipped_any"] for r in RUNS[m]),
                   "delta_pos": sum(1 for r in RUNS[m] if r["delta"] is not None and r["delta"] > 0), "n": len(RUNS[m])}
    mm = re.search(rf"- `{re.escape(m)}`: (\d+) fold, FIT_OK (\d+);.*?seçilen λ \(FIT_OK\): ([^;]+); test arzı kırpılan fold: (\d+)\.", SEC)
    if mm:
        fold_sum[m]["md_lambda"] = mm.group(3)
        fold_sum[m]["md_clipped"] = int(mm.group(4))
        fold_sum[m]["md_lambda_same"] = dict((k.strip(), int(v)) for k, v in (x.split(":") for x in mm.group(3).split(","))) == {k: v for k, v in lam_c.items()}
say("[1e] fold özeti: " + "; ".join(f"{m.split('_')[-1]}: λ aynı {v.get('md_lambda_same')} | MODELS.md 'kırpılan' {v.get('md_clipped')} = benim f3-kırpma {v['clipped_f3']}, herhangi-sütun {v['clipped_any']}" for m, v in fold_sum.items()))
OUT["cells"] = {"|".join(map(str, k)): ({kk: v[kk] for kk in ("n", "n_months", "model", "rule", "mean", "ci95", "wins", "losses", "ties", "ties_1e12")} | ({"label": v["label"]} if "label" in v else {}))
                for k, v in CELLS.items() if v is not None}
OUT["cells_vs_opus_ledger"] = {"worst": worst_cell, "detail": cell_cmp}
OUT["cells_vs_log"] = log_cmp
OUT["models_md"] = {"n_ok": n_ok, "n_total": len(md_checks), "checks": md_checks}
OUT["fold_summary"] = fold_sum
OUT["v0_mean_rps"] = sum(v0_rps) / 87
OUT["positions_62"] = {m: position(CELLS[("near", m)]["mean"], EXP62[m][1], EXP62[m][2]) for m in (CLIP, REAL, POOLED)}

# ============================================================ D1 / D2 iç tutarlılık (IMPL_RAPOR §8) bağımsız kurulum
say("\n=== D1/D2 iç tutarlılık (bağımsız) ===")
_saved = {t: UNITS[t]["f1r"] for t in UNITS}
for t in UNITS:
    UNITS[t]["f1r"] = UNITS[t]["f1"]                                   # D1: deflatör sabit 100 -> real ≡ clip olmalı
d1 = run_model(REAL, PLAN_C, tag="D1_real_with_f1")
for t in UNITS:
    UNITS[t]["f1r"] = _saved[t]
d1_ok = all(a["selected_lambda"] == b["selected_lambda"] and a["S"] == b["S"] for a, b in zip(d1, RUNS[CLIP]))
d1_max = max(max(abs(x - y) for x, y in zip(a["S"], b["S"])) for a, b in zip(d1, RUNS[CLIP]))
plan_h99only = plan(True, drop_open=OPEN_F3)
d2 = run_model(REAL, plan_h99only, use_r=False, tag="D2_pooled_plan_h99_only")
d2_plan_ok = [(f["test"], f["tk_sha"], f["pp_sha"]) for f in plan_h99only if f["ok"]] == [(f["test"], f["tk_sha"], f["pp_sha"]) for f in ok_c]
d2_ok = all(a["selected_lambda"] == b["selected_lambda"] and a["S"] == b["S"] for a, b in zip(d2, RUNS[REAL]))
d2_max = max(max(abs(x - y) for x, y in zip(a["S"], b["S"])) for a, b in zip(d2, RUNS[REAL]))
say(f"[D1] real (f1r := f1) ≡ clip: λ ve S bit-eşit {d1_ok} (maks|ΔS| {d1_max:.1e}); [D2] havuz planı yalnız H99 satırları + rejimsiz ≡ real: plan {d2_plan_ok}, λ ve S bit-eşit {d2_ok} (maks|ΔS| {d2_max:.1e})")
OUT["d1_d2"] = {"d1_bitwise": d1_ok, "d1_max": d1_max, "d2_plan_same": d2_plan_ok, "d2_bitwise": d2_ok, "d2_max": d2_max}

# ============================================================ 4. Tanı (model seçimine girmez)
say("\n=== 4. Tanı (bilgi; şartname değişmez) ===")
NEAR = near_c
V0B = {r["ticker"]: r for r in CMPL["ceiling_hazard_v0"]}
KMB = {r["ticker"]: r for r in CMPL["base_km_expanding"]}


def near_rows(runs_m):
    return [r for r in runs_m if r["first_trading_date"] >= NEAR_START]


def level_table(rows_by_model):
    out = {}
    for name, rows in rows_by_model.items():
        obs = {k: sum(1 for r in rows if int(r["realized_L"]) >= k) / len(rows) for k in range(1, 11)}
        mean_s = {k: sum(S_of(r)[k - 1] for r in rows) / len(rows) for k in range(1, 11)}
        base = sum(rps(S_of(r), int(r["realized_L"])) for r in rows) / len(rows)
        shifted = sum(rps([min(max(S_of(r)[k - 1] - (mean_s[k] - obs[k]), 0.0), 1.0) for k in range(1, 11)], int(r["realized_L"])) for r in rows) / len(rows)
        out[name] = {"mean_S": {k: mean_s[k] for k in (1, 3, 5, 10)}, "obs": {k: obs[k] for k in (1, 3, 5, 10)}, "rps": base, "rps_level_removed": shifted,
                     "level_share": base - shifted}
    return out


LT = level_table({"v0": [V0B[t] for t in NEAR], "km": [KMB[t] for t in NEAR], CLIP: near_rows(RUNS[CLIP]), REAL: near_rows(RUNS[REAL]), POOLED: near_rows(RUNS[POOLED]), PINF: near_rows(RUNS[PINF])})
say("[tanı] yakın dönem (78) ort. S_k / gözlenen ve düzey payı (RPS − düzey çıkarılmış RPS):")
for name, v in LT.items():
    say(f"      {name}: S_1 {v['mean_S'][1]:.3f}/{v['obs'][1]:.3f} S_3 {v['mean_S'][3]:.3f}/{v['obs'][3]:.3f} S_5 {v['mean_S'][5]:.3f}/{v['obs'][5]:.3f} S_10 {v['mean_S'][10]:.3f}/{v['obs'][10]:.3f} | "
        f"RPS {v['rps']:.4f}, düzey çıkarılınca {v['rps_level_removed']:.4f}, düzey payı {v['level_share']:+.4f}")
for m in (CLIP, REAL, POOLED):
    d_total = LT[m]["rps"] - LT["v0"]["rps"]
    d_level = LT[m]["level_share"] - LT["v0"]["level_share"]
    say(f"      {m} − v0: toplam {d_total:+.4f} = düzey {d_level:+.4f} + ayırma/şekil {d_total - d_level:+.4f}")


def brier_decomp(rows, k, bins=10):
    f = [S_of(r)[k - 1] for r in rows]
    y = [1.0 if int(r["realized_L"]) >= k else 0.0 for r in rows]
    n = len(f)
    ybar = sum(y) / n
    unc = ybar * (1 - ybar)
    rel = res = 0.0
    for b in range(bins):
        idx = [i for i in range(n) if (b / bins <= f[i] < (b + 1) / bins) or (b == bins - 1 and f[i] == 1.0)]
        if not idx:
            continue
        fb = sum(f[i] for i in idx) / len(idx)
        ob = sum(y[i] for i in idx) / len(idx)
        rel += len(idx) / n * (fb - ob) ** 2
        res += len(idx) / n * (ob - ybar) ** 2
    return {"brier": sum((a - b) ** 2 for a, b in zip(f, y)) / n, "rel": rel, "res": res, "unc": unc}


BD = {}
for k in (3, 5, 10):
    BD[k] = {name: brier_decomp(rows, k) for name, rows in (("v0", [V0B[t] for t in NEAR]), (CLIP, near_rows(RUNS[CLIP])), (REAL, near_rows(RUNS[REAL])), (POOLED, near_rows(RUNS[POOLED])))}
    say(f"[tanı] Brier k={k} (10 kutu) güvenilirlik/çözünürlük/belirsizlik: " + "; ".join(f"{n.split('_')[-1]} {v['brier']:.4f} = {v['rel']:.4f} − {v['res']:.4f} + {v['unc']:.4f}" for n, v in BD[k].items()))
YEAR = {}
for m in (CLIP, REAL, POOLED, PINF):
    c = CELLS[("near", m)]
    by = defaultdict(list)
    for t, d in c["diffs"].items():
        by[UNITS[t]["ftd"][:4]].append(d)
    YEAR[m] = {y: {"n": len(v), "mean": sum(v) / len(v), "wins": sum(1 for d in v if d < 0)} for y, v in sorted(by.items())}
    say(f"[tanı] {m} − v0 yıl kırılımı: " + "; ".join(f"{y}: n={v['n']} ort {v['mean']:+.4f} (aday iyi {v['wins']})" for y, v in YEAR[m].items()))
TOP = {}
for m in (REAL, POOLED):
    c = CELLS[("near", m)]
    top = sorted(c["diffs"].items(), key=lambda kv: -abs(kv[1]))[:10]
    TOP[m] = [{"ticker": t, "T": UNITS[t]["ftd"], "L": UNITS[t]["L"], "diff": d, "share_of_total": d / (c["mean"] * c["n"])} for t, d in top]
    say(f"[tanı] {m} en çok katkı veren 10 fold (fark, L): " + ", ".join(f"{x['ticker']} {x['T'][:7]} L={x['L']} {x['diff']:+.3f}" for x in TOP[m])
        + f"; 10'unun toplam farktaki payı {sum(x['share_of_total'] for x in TOP[m]):.0%}")
# pooled: rejim ve dönem
open_r1 = [t for t in OPEN_F3 if UNITS[t]["r"] == 1]
open_r0 = [t for t in OPEN_F3 if UNITS[t]["r"] == 0]
km_of = lambda ts: [1 - sum(1 for t in ts if UNITS[t]["L"] < k) / len(ts) if False else sum(1 for t in ts if UNITS[t]["L"] >= k) / len(ts) for k in (1, 3, 5, 10)]  # noqa: E731
say(f"[tanı] havuz: açık f3'lü 68 = r=1 {len(open_r1)} + r=0 (2023-03-30 sonrası) {len(open_r0)}; ham P(L≥k) k=1,3,5,10: r=1 {[round(x, 2) for x in km_of(open_r1)]}, "
    f"r=0 açık {[round(x, 2) for x in km_of(open_r0)]}, H99 97 {[round(x, 2) for x in km_of(H99_F3)]}, yakın dönem 78 {[round(x, 2) for x in km_of(NEAR)]}")
pf = FINAL[POOLED]["fit"]
say(f"[tanı] pooled nihai fit: γ {[round(float(x), 3) for x in pf['gamma']]}, δ {float(pf['delta'][0]):+.3f} → r=0 (canlı) gün-grubu hazard'ları "
    f"{[round(sigmoid(float(g)), 3) for g in pf['gamma']]}; v1_real nihai γ {[round(float(x), 3) for x in FINAL[REAL]['fit']['gamma']]} → {[round(sigmoid(float(g)), 3) for g in FINAL[REAL]['fit']['gamma']]}; "
    f"pooled λ skorları (3/10/30): {pf['score'][3.0]:.5f}/{pf['score'][10.0]:.5f}/{pf['score'][30.0]:.5f}")
# λ sınırı: ızgara konumu
lam_pos = Counter()
for r in RUNS[POOLED]:
    sc = r["score"]
    lam_pos[("iç nokta" if sc[3.0] > sc[10.0] < sc[30.0] else "sınır/düz")] += 1
say(f"[tanı] pooled fold'larında λ = 10 ızgarada: {dict(lam_pos)} (ızgara 0.1…1000, INF; 10 üst uç DEĞİL, iç nokta)")
# real: f1 vs f1r
ln_f1 = np.array([math.log(float(UNITS[t]["f1"])) for t in H99_F3])
ln_f1r = np.array([math.log(float(UNITS[t]["f1r"])) for t in H99_F3])
ordn = np.array([i for i, _ in enumerate(H99_F3)], dtype=float)
sp = lambda a, b: float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])  # noqa: E731
say(f"[tanı] real: H99 97'de ln f1 ↔ ln f1r Spearman {sp(ln_f1, ln_f1r):.3f}; ln f1 ↔ zaman sırası Pearson {np.corrcoef(ln_f1, ordn)[0, 1]:+.3f}, ln f1r ↔ zaman {np.corrcoef(ln_f1r, ordn)[0, 1]:+.3f}; "
    f"sd ln f1 {ln_f1.std():.3f}, sd ln f1r {ln_f1r.std():.3f}; nihai β_f1 (clip) {float(FINAL[CLIP]['fit']['beta'][0]):+.4f}, β_f1r (real) {float(FINAL[REAL]['fit']['beta'][0]):+.4f}; "
    f"fold ortalaması β: clip {np.mean([r['beta']['f1'] for r in RUNS[CLIP]]):+.3f}, real {np.mean([r['beta']['f1r'] for r in RUNS[REAL]]):+.3f}")
# clip: v0'dan fark kaynağı
cc = CELLS[("near", CLIP)]
grp = defaultdict(list)
for r in near_rows(RUNS[CLIP]):
    grp["test kırpılan" if r["test_clipped_any"] else "test kırpılmayan"].append(cc["diffs"][r["ticker"]])
say(f"[tanı] clip − v0 (78): " + "; ".join(f"{k}: n={len(v)} ort {sum(v) / len(v):+.4f}" for k, v in grp.items())
    + f"; 87 fold'da test arzı herhangi-sütun kırpılan {sum(r['test_clipped_any'] for r in RUNS[CLIP])}, yalnız f3 {sum(r['test_clipped_f3'] for r in RUNS[CLIP])}")
OUT["diagnosis"] = {"level": LT, "brier_decomp": BD, "year": YEAR, "top10": TOP, "open_r1": len(open_r1), "open_r0": len(open_r0),
                    "raw_survival": {"open_r1": km_of(open_r1), "open_r0": km_of(open_r0), "h99": km_of(H99_F3), "near": km_of(NEAR)},
                    "lambda_interior": dict(lam_pos), "real": {"spearman_f1_f1r": sp(ln_f1, ln_f1r), "corr_f1_time": float(np.corrcoef(ln_f1, ordn)[0, 1]),
                                                                "corr_f1r_time": float(np.corrcoef(ln_f1r, ordn)[0, 1]), "sd_f1": float(ln_f1.std()), "sd_f1r": float(ln_f1r.std())},
                    "clip_groups": {k: {"n": len(v), "mean": sum(v) / len(v)} for k, v in grp.items()}}

# ============================================================ 4. Duyarlılıklar (bilgi; model DEĞİL)
say("\n=== 4. Duyarlılıklar (pooled; model değil, dondurulmaz) ===")
SENS = {}
t_s = time.time()
if USE_CACHE and "SENS" in pickle.load(open(CACHE, "rb")):
    SENS = pickle.load(open(CACHE, "rb"))["SENS"]
    PLAN_P_NOJ10 = plan(True, j10=False)
    say("[önbellek] duyarlılık koşuları önbellekten")
if not SENS:
  SENS["drop_post_20230330_open"] = run_model(POOLED, plan(True, drop_open=open_r0), tag="ceiling_hazard_v1_pooled__sens_drop_post_20230330_open")
  SENS["no_regime"] = run_model(POOLED, PLAN_P, use_r=False, tag="ceiling_hazard_v1_pooled__sens_no_regime")
  SENS["lambda_grid_dense_and_extended"] = run_model(POOLED, PLAN_P, grid=GRID_EXT, tag="ceiling_hazard_v1_pooled__sens_lambda_grid_dense_and_extended")
  PLAN_P_NOJ10 = plan(True, j10=False)
  SENS["j10_exclusion_off"] = run_model(POOLED, PLAN_P_NOJ10, j10=False, tag="ceiling_hazard_v1_pooled__sens_j10_exclusion_off")
  pickle.dump({"RUNS": {k: v for k, v in RUNS.items() if k in MODELS}, "SENS": SENS}, open(CACHE, "wb"))
say(f"[duyarlılık] J10 kapalı plan: dışlamalı fold {sum(1 for f in PLAN_P_NOJ10 if f['excluded'])}; eğitimdeki açık arz {sorted({f['n_open'] for f in PLAN_P_NOJ10 if f['ok']})}; "
    f"J10 açıkken dışlamalı fold'ların yakın dönemdekileri: {sum(1 for f in ok_p if f['excluded'] and f['T'] >= NEAR_START)}/{sum(1 for f in ok_p if f['excluded'])} "
    f"(ilk/son dışlamalı T: {min(f['T'] for f in ok_p if f['excluded'])} / {max(f['T'] for f in ok_p if f['excluded'])})")
SENS_T = time.time() - t_s
sens_cells = {}
for name, rows in SENS.items():
    c = paired(rows, CMPL["ceiling_hazard_v0"], start=NEAR_START)
    c["label"] = label(c["ci95"])
    km = paired(rows, CMPL["base_km_expanding"], start=NEAR_START)
    sens_cells[name] = {"near_vs_v0": {k: c[k] for k in ("n", "n_months", "model", "rule", "mean", "ci95", "wins", "losses", "ties", "label")},
                        "near_vs_km": {k: km[k] for k in ("mean", "ci95")},
                        "lambda": dict(Counter("INF" if r["selected_lambda"] == INF else f"{r['selected_lambda']:g}" for r in rows)),
                        "n_folds": len(rows), "mean_rps_all": sum(rps(r["S"], r["realized_L"]) for r in rows) / len(rows)}
    say(f"[duyarlılık] {name}: yakın dönem − v0 {fmt_cell(c)} → {c['label']}; − KM {km['mean']:+.4f} [{km['ci95'][0]:+.4f}, {km['ci95'][1]:+.4f}]; λ {sens_cells[name]['lambda']}")
OUT["sensitivity"] = sens_cells


# ============================================================ çıktılar
def write_compact(name, rows):
    cols = ["model_id", "ticker", "first_trading_date", "realized_L", "status", "training_n_ipo", "training_n_pp_rows", "training_n_events", "selected_lambda",
            "gamma_g1", "gamma_g2", "gamma_g3", "delta", "beta", "test_clipped_any", "test_clipped_features"] + [f"S_{k}" for k in range(1, 11)]
    with open(OUT_DIR / "repro_ledgers" / f"{name}.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            lam = r.get("selected_lambda")
            w.writerow([r["model_id"], r["ticker"], r["first_trading_date"], r["realized_L"], r["status"], r["training_n_ipo"], r["training_n_pp_rows"], r["training_n_events"],
                        "" if lam is None else ("INF" if lam == INF else lam), *[repr(x) for x in r.get("gamma", ["", "", ""])], "" if r.get("delta") is None else repr(r["delta"]),
                        json.dumps(r.get("beta", {})), r.get("test_clipped_any", ""), json.dumps(r.get("test_clipped_features", [])), *[repr(x) for x in r["S"]]])


def write_full(name, rows):
    with open(FULL_DIR / f"{name}_fold_ledger.json", "w", encoding="utf-8") as fh:
        json.dump(rows, fh, default=lambda o: ("INF" if o == INF else str(o)) if not isinstance(o, (dict, list)) else o, ensure_ascii=False)


for m, rows in RUNS.items():
    write_compact(m.replace("@", "_at_") + "_repro", rows)
    write_full(m.replace("@", "_at_") + "_repro", rows)
for name, rows in SENS.items():
    write_compact(f"sens_{name}", rows)

with open(OUT_DIR / "sensitivity_runs.jsonl", "w", encoding="utf-8") as fh:
    for name, rows in SENS.items():
        base = LOGE[POOLED]
        sc = sens_cells[name]
        entry = {"kind": "sensitivity", "context": "fable_faz7_audit_sensitivity", "model_id": f"ceiling_hazard_v1_pooled__sens_{name}",
                 "base_model_id": POOLED, "spec_sha256": base["spec_sha256"], "spec_document": base["spec_document"], "spec_document_sha256": base["spec_document_sha256"],
                 "decisions_document": base["decisions_document"], "decisions_document_sha256": base["decisions_document_sha256"],
                 "plan_id": base["plan_id"] + "__SENS_" + name.upper(),
                 "variation": {"drop_post_20230330_open": "havuzdan 2023-03-30 sonrası (r = 0) açık küme arzları (15) çıkarıldı; rejim terimi aynen",
                               "no_regime": "rejim terimi yok (X = [G | Z]); havuz aynen",
                               "lambda_grid_dense_and_extended": f"λ ızgarası {[('INF' if x == INF else x) for x in GRID_EXT]} (10 çevresi yoğun, üstten 10000'e kadar)",
                               "j10_exclusion_off": "SPEC_DEVIATIONS J10 f3 filtre dışlaması kapalı: FILTERED 3 açık üye her fold'da eğitimde (iç CV'de de dışlama yok)"}[name],
                 "note": "şartname dışı; model değil; dondurulmaz; bağımsız betikle (borsai import edilmedi)",
                 "data_version_sha256": base["data_version_sha256"], "training_table_sha256": base["training_table_sha256"],
                 "folds_total": len(PLAN_P), "folds_scorable": {"CEILING": sc["n_folds"]},
                 "ledger_file": f"docs/fable_faz7_audit/ekler/repro_ledgers/sens_{name}.csv", "ledger_sha256": sha_file(OUT_DIR / "repro_ledgers" / f"sens_{name}.csv"),
                 "metrics": {"rps": sc["mean_rps_all"], "near_era_vs_ceiling_hazard_v0": sc["near_vs_v0"], "near_era_vs_base_km_expanding": sc["near_vs_km"], "lambda_counts": sc["lambda"]},
                 "evaluated": base["evaluated"], "code": "docs/fable_faz7_audit/ekler/repro_hazard_v1.py",
                 "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "seconds": round(SENS_T / 4, 1), "audit_task": "BORSAI_FAZ7_FABLE_V1_REPRO_AUDIT_20260926"}
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")

OUT["inputs_sha256"] = {str(p.relative_to(ROOT)): sha_file(p) for p in (ROOT / "data" / "training_table.csv", ROOT / "data" / "training_table_v2.csv", SESS_PATH,
                                                                          RAW / "HISTORICAL99_FROZEN_COHORT_V1_canonical_pretrade_master.csv", RAW / "tuik" / "tufe_genel_2025_100.csv",
                                                                          RAW / "tuik" / "tufe_bultenleri.csv", GOLD7 / "MANIFEST.json", ROOT / "docs" / "MODELS.md")}
OUT["inputs_sha256"].update({f"faz1b:{k}": sha_file(GOLD1B / f"{k}_fold_ledger.csv") for k in CMPL})
OUT["seconds"] = time.time() - T0
OUT["borsai_in_sys_modules"] = any(m == "borsai" or m.startswith("borsai.") for m in sys.modules)
say(f"\n[son] toplam {OUT['seconds']:.0f} s; sys.modules'ta borsai: {OUT['borsai_in_sys_modules']}")
(OUT_DIR / "repro_output.json").write_text(json.dumps(OUT, indent=1, default=lambda o: ("INF" if o == INF else str(o)), ensure_ascii=False), encoding="utf-8")
(OUT_DIR / "repro_stdout.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")

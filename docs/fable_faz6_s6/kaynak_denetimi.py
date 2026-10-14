#!/usr/bin/env python3
"""BORSAI_FAZ6_FABLE_S6_RECOMPUTE — kaynak denetimi (Faz 1 adım 4).

MANIFEST_OOT.csv'den `random.Random(20260925).sample(rows, 10)` ile 10 satır seçilir, her zip
resmi URL'den repo ve karantina dışındaki geçici dizine yeniden indirilir; sha256 pinle
karşılaştırılır; o bülten tarihine düşen açık küme üyelerinin `<T>.E` satırlarında THB için
`close_raw` ve `trade_count_raw`, THM için `upper_limit_raw` ve `reference_raw` S5 CSV'leriyle
karşılaştırılır. Yalnız açık küme kodları aranır; kasadaki kodlar hiçbir yerde okunmaz ya da
yazılmaz. Sonra geçici dosyalar silinir. Çıktı yalnız sayılardır (URL, ad, fiyat yazılmaz).
`borsai` import edilmez.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import random
import shutil
import sys
import time
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = Path("/tmp/borsai_fable_s6")
SEED = 20260925
N_SAMPLE = 10
PACE_S = 1.0

THB_FIELDS = {"close_raw": "KAPANIS FIYATI", "trade_count_raw": "TOPLAM SOZLESME SAYISI"}
THM_FIELDS = {"upper_limit_raw": "UST LIMIT FIYATI", "reference_raw": "REFERANS FIYATI"}
CODE_COL = "ISLEM  KODU"
DATE_COL = "TARIH"


def parse_bulletin(data: bytes, expected_internal: str) -> tuple[list[str], list[list[str]]]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if names != [expected_internal]:
            raise RuntimeError("zip iç dosya adı pinle uyuşmuyor")
        text = archive.read(expected_internal).decode("cp1254")
    reader = csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=";")
    records = [row for row in reader if any(cell != "" for cell in row)]
    headers, english, rows = records[0], records[1], records[2:]
    if len(headers) != len(english) or any(len(r) != len(headers) for r in rows):
        raise RuntimeError("bülten başlık/satır genişliği uyuşmuyor")
    return headers, rows


def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "BorsAi-Fable-S6-source-audit/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                return resp.read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("erişilemedi")


def main() -> int:
    with (ROOT / "data" / "raw" / "bist" / "MANIFEST_OOT.csv").open(encoding="utf-8", newline="") as f:
        manifest = list(csv.DictReader(f))
    with (ROOT / "registry" / "oot" / "cohort_pre_h99.csv").open(encoding="utf-8", newline="") as f:
        cohort = list(csv.DictReader(f))
    active: dict[str, dict] = {}
    for r in cohort:
        if r["status"] == "CANCELLED":
            active.pop(r["ticker"], None)
        else:
            active[r["ticker"]] = r
    open_set = sorted(t for t, r in active.items() if r["status"] == "MEMBER" and r["vault"] != "SEALED")

    # açık küme sonuç satırları: (tarih, tür) → [(ticker, satır)]
    by_date: dict[tuple[str, str], list[tuple[str, dict]]] = {}
    for t in open_set:
        p = ROOT / "data" / "outcomes_oot" / f"{t}.csv"
        if not p.exists():
            continue
        with p.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row["status"] != "OK":
                    continue
                for kind in ("thb", "thm"):
                    by_date.setdefault((row["session_date"], kind), []).append((t, row))

    sample = random.Random(SEED).sample(manifest, N_SAMPLE)
    TMP.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    per_row = []
    try:
        for i, m in enumerate(sample):
            if i:
                time.sleep(PACE_S)
            data = download(m["url"])
            (TMP / f"sample_{i}.zip").write_bytes(data)
            sha_ok = hashlib.sha256(data).hexdigest() == m["sha256"]
            bytes_ok = len(data) == int(m["bytes"])
            counts["n_downloaded"] += 1
            counts["n_sha_equal"] += int(sha_ok)
            counts["n_bytes_equal"] += int(bytes_ok)
            headers, rows = parse_bulletin(data, m["internal_filename"])
            idx = {h: j for j, h in enumerate(headers)}
            fields = THB_FIELDS if m["kind"] == "thb" else THM_FIELDS
            members = by_date.get((m["date"], m["kind"]), [])
            n_fields_eq = n_fields_diff = n_rows_found = n_sha_pin_eq = 0
            for t, orow in members:
                code = f"{t}.E"
                hits = [r for r in rows if r[idx[CODE_COL]] == code]
                if len(hits) != 1:
                    counts["n_member_row_not_unique"] += 1
                    continue
                r = hits[0]
                n_rows_found += 1
                if m["kind"] == "thb":
                    n_sha_pin_eq += int(orow["thb_sha256"] == m["sha256"])
                else:
                    n_sha_pin_eq += int(orow["thm_sha256"] == m["sha256"])
                for csv_field, col in fields.items():
                    if r[idx[col]] == orow[csv_field]:
                        n_fields_eq += 1
                    else:
                        n_fields_diff += 1
            counts["n_member_rows_expected"] += len(members)
            counts["n_member_rows_found"] += n_rows_found
            counts["n_fields_equal"] += n_fields_eq
            counts["n_fields_diff"] += n_fields_diff
            counts["n_outcome_sha_pin_equal"] += n_sha_pin_eq
            per_row.append({"i": i, "year": m["date"][:4], "kind": m["kind"], "sha_equal": sha_ok, "bytes_equal": bytes_ok,
                            "n_members_on_date": len(members), "n_rows_found": n_rows_found,
                            "n_fields_equal": n_fields_eq, "n_fields_diff": n_fields_diff})
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    counts["n_sampled"] = len(sample)
    counts["n_open_set"] = len(open_set)
    counts["temp_dir_removed"] = int(not TMP.exists())
    counts["borsai_imported"] = int("borsai" in sys.modules)
    out = {"task": "BORSAI_FAZ6_FABLE_S6_RECOMPUTE_20260925", "step": "kaynak_denetimi", "seed": SEED,
           "counts": dict(sorted(counts.items())), "rows": per_row}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    ok = (counts["n_sha_equal"] == N_SAMPLE and counts["n_fields_diff"] == 0
          and counts["n_member_rows_found"] == counts["n_member_rows_expected"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

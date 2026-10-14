#!/usr/bin/env python3
"""BORSAI_FAZ7_FABLE_VAULT_RECOMPUTE — kaynak denetimi (Faz 1 adım 5).

MANIFEST_OOT.csv'nin kasa açılışında eklenen satırlarından (veri satırı 915–1168; ilk 914 satır açık
kümenindir) `random.Random(20260929).sample(rows, 10)` ile 10 satır seçilir; her zip resmi URL'den
repo ve karantina dışındaki geçici dizine (/tmp/borsai_fable_vault/) yeniden indirilir; sha256 pinle
karşılaştırılır; o bülten tarihine düşen KASA üyelerinin `<T>.E` satırlarında THB için `close_raw` ve
`trade_count_raw`, THM için `upper_limit_raw` ve `reference_raw` sonuç CSV'leriyle karşılaştırılır.
TARIH alanı bağımsız çözümlenir (ISO ya da d.mm.yyyy / dd.mm.yyyy; SPEC_DEVIATIONS M14) ve satırın günü
bülten gününe eşit olmalıdır. Sonra geçici dosyalar silinir. Çıktı yalnız sayıdır (URL, ad, fiyat,
bülten adı yazılmaz). `borsai` import edilmez.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import random
import re
import shutil
import sys
import time
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = Path("/tmp/borsai_fable_vault")
SEED = 20260929
N_SAMPLE = 10
PACE_S = 1.0
FIRST_VAULT_ROW = 915  # 1 tabanlı veri satırı; 1..914 açık küme (VAULT_OPEN.json manifest_oot_before.n_rows = 914)

THB_FIELDS = {"close_raw": "KAPANIS FIYATI", "trade_count_raw": "TOPLAM SOZLESME SAYISI"}
THM_FIELDS = {"upper_limit_raw": "UST LIMIT FIYATI", "reference_raw": "REFERANS FIYATI"}
CODE_COL = "ISLEM  KODU"
DATE_COL = "TARIH"
ISO_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
DOTTED_RE = re.compile(r"^(\d{1,2})\.(\d{2})\.(\d{4})$")


def parse_tarih(text: str) -> tuple[str | None, str]:
    """TARIH → (ISO tarih | None, biçim etiketi)."""
    s = text.strip()
    m = ISO_RE.match(s)
    if m:
        return s, "ISO"
    m = DOTTED_RE.match(s)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{mo}-{int(d):02d}", "dotted_d" if len(d) == 1 else "dotted_dd"
    return None, "unknown"


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
    req = urllib.request.Request(url, headers={"User-Agent": "BorsAi-Fable-vault-source-audit/1.0"})
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
    vault_rows = manifest[FIRST_VAULT_ROW - 1:]
    with (ROOT / "registry" / "oot" / "cohort_pre_h99.csv").open(encoding="utf-8", newline="") as f:
        cohort = list(csv.DictReader(f))
    active: dict[str, dict] = {}
    for r in cohort:
        if r["status"] == "CANCELLED":
            active.pop(r["ticker"], None)
        else:
            active[r["ticker"]] = r
    sealed = sorted(t for t, r in active.items() if r["status"] == "MEMBER" and r["vault"] == "SEALED")

    by_date: dict[tuple[str, str], list[tuple[str, dict]]] = {}
    for t in sealed:
        p = ROOT / "data" / "outcomes_oot" / f"{t}.csv"
        if not p.exists():
            continue
        with p.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row["status"] != "OK":
                    continue
                for kind in ("thb", "thm"):
                    by_date.setdefault((row["session_date"], kind), []).append((t, row))

    sample = random.Random(SEED).sample(vault_rows, N_SAMPLE)
    TMP.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    per_row = []
    tarih_formats = Counter()
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
            # TARIH: bültenin bütün satırlarında biçim ve gün
            fmts = Counter()
            n_day_mismatch = 0
            for r in rows:
                iso, fmt = parse_tarih(r[idx[DATE_COL]])
                fmts[fmt] += 1
                if iso != m["date"]:
                    n_day_mismatch += 1
            tarih_formats.update(fmts)
            counts["n_bulletins_non_iso"] += int(any(k != "ISO" for k in fmts))
            counts["n_rows_day_mismatch"] += n_day_mismatch
            members = by_date.get((m["date"], m["kind"]), [])
            n_fields_eq = n_fields_diff = n_rows_found = n_sha_pin_eq = n_date_ok = 0
            for t, orow in members:
                code = f"{t}.E"
                hits = [r for r in rows if r[idx[CODE_COL]] == code]
                if len(hits) != 1:
                    counts["n_member_row_not_unique"] += 1
                    continue
                r = hits[0]
                n_rows_found += 1
                iso, _ = parse_tarih(r[idx[DATE_COL]])
                n_date_ok += int(iso == orow["session_date"] == m["date"])
                n_sha_pin_eq += int(orow[f"{m['kind']}_sha256"] == m["sha256"])
                for csv_field, col in fields.items():
                    if r[idx[col]] == orow[csv_field]:
                        n_fields_eq += 1
                    else:
                        n_fields_diff += 1
            counts["n_member_rows_expected"] += len(members)
            counts["n_member_rows_found"] += n_rows_found
            counts["n_member_rows_date_equal"] += n_date_ok
            counts["n_fields_equal"] += n_fields_eq
            counts["n_fields_diff"] += n_fields_diff
            counts["n_outcome_sha_pin_equal"] += n_sha_pin_eq
            per_row.append({"i": i, "year": m["date"][:4], "kind": m["kind"], "sha_equal": sha_ok, "bytes_equal": bytes_ok,
                            "tarih_formats": dict(fmts), "n_rows_day_mismatch": n_day_mismatch,
                            "n_members_on_date": len(members), "n_rows_found": n_rows_found, "n_rows_date_equal": n_date_ok,
                            "n_fields_equal": n_fields_eq, "n_fields_diff": n_fields_diff})
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    counts["n_sampled"] = len(sample)
    counts["n_vault_manifest_rows"] = len(vault_rows)
    counts["n_manifest_rows"] = len(manifest)
    counts["n_sealed"] = len(sealed)
    counts["temp_dir_removed"] = int(not TMP.exists())
    counts["borsai_imported"] = int("borsai" in sys.modules)
    out = {"task": "BORSAI_FAZ7_FABLE_VAULT_RECOMPUTE_20260929", "step": "kaynak_denetimi", "seed": SEED,
           "sample_from": f"MANIFEST_OOT veri satırı {FIRST_VAULT_ROW}..{len(manifest)}",
           "sample_by_year_kind": dict(sorted(Counter(f"{m['date'][:4]}|{m['kind']}" for m in sample).items())),
           "tarih_formats_total": dict(tarih_formats),
           "counts": dict(sorted(counts.items())), "rows": per_row}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    ok = (counts["n_sha_equal"] == N_SAMPLE and counts["n_fields_diff"] == 0
          and counts["n_member_rows_found"] == counts["n_member_rows_expected"]
          and counts["n_member_rows_date_equal"] == counts["n_member_rows_expected"]
          and counts["n_rows_day_mismatch"] == 0)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

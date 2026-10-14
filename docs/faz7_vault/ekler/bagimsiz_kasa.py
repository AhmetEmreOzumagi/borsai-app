#!/usr/bin/env python3
"""BORSAI_FAZ7_VAULT_OPEN M-J: kasa açılışının bağımsız ham alan denetimi. `borsai` İMPORT EDİLMEZ (yalnız stdlib); repo dışında
koşar (Faz 6 T5 betiği `docs/faz6/ekler/s3_s5_bagimsiz.py` kalıbı).

Karantinadaki THB/THM zip'lerini doğrudan açar ve YALNIZ kasa (SEALED) kodlarının `<T>.E` satırlarına bakar; başka hiçbir satır
tutulmaz. Çıktı yalnız SAYI: hiçbir kod, fiyat, getiri ya da limit yazılmaz. Betik değer içermez.

--stage d1 (VA1): registry/oot/d1_rows/<T>.json (kasa üyeleri)
  - 14 ham alan (fields_raw) ↔ D_1 zip satırı; halt_flag, ceiling_close_D1 (Decimal kapanış == üst limit), lock_consistency
  - thb/thm sha256: d1_rows ↔ karantina zip ↔ MANIFEST_OOT ↔ karantina manifesti; url, bayt, iç ad
  - D_1 kuralı: D_1 ≥ ilk işlem günü; [ilk işlem günü, D_1) sonuç takvimi seanslarında kod işlem görmemiş; D_1'de görmüş
  - açık kümenin d1_rows dosyaları `--base` commit'indekiyle bayt-eşit; kasa dosyası sayısı = kasa üye sayısı
  - MANIFEST_OOT: `--base`'teki baytlar önek (yalnız ekleme); yeni satırlar = 2 × (önceden pinli olmayan yeni D_1 tarihi); her
    yeni satırın sha'sı = karantina dosyası = karantina manifesti
  - işaret dosyası: kasa kodu yok; n_sealed = kasa üye sayısı
--stage s5 (VB): data/outcomes_oot/<T>.csv ve raw/<T>.json (kasa üyeleri)
  - close_raw, trade_count_raw, upper_limit_raw, reference_raw, halt_flag ↔ ilgili seansın zip satırı; thb/thm sha ↔ zip ↔
    MANIFEST_OOT; ceiling_close ↔ Decimal(kapanış) == Decimal(üst limit); status; h ∈ {1, 3, 5, 10} için R_h ↔ kapanış / arz
    fiyatı − 1 (|Δ| ≤ 1e-12), Y_h = 1[R > 0]
  - ham kopya ↔ zip; D_h çözümü yeniden kurulur; D_10'dan sonra okunmuş seans yok; h = 1 ↔ d1_rows D_1 ve sha'ları
  - açık kümenin sonuç ve ham kopya dosyaları `--base`'tekiyle bayt-eşit; MANIFEST_OOT `--base` öneki; her sha karantinayla eşit
Sonuç takvimi (EK1 K7): Takvim C seansları ∪ kanıtta TRADING_SESSION olan günler (kanıt dosyası doğrudan okunur).
TARIH (SPEC_DEVIATIONS M14; bu betik tarihi kendi başına çözümler, borsai'deki düzeltmeyi kopyalamaz): okunan her zip'te kod
satırının TARIH'i bülten günüdür (ISO ya da d.mm.yyyy / dd.mm.yyyy); ISO dışı TARIH'li bültende bütün satırların günü tutar ve
kapanış, sözleşme sayısı, referans, üst ve alt limit değerleri yalnız rakam ve tek noktalı ondalıktır (sözleşme tam sayı). ISO
dışı TARIH'li bültenlerin sayısı ve günleri çıktıya yazılır (değer yok).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
import zipfile
from collections import Counter
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path

SEALED = "SEALED"
THB = {"open": "ACILIS FIYATI", "high": "EN YUKSEK FIYAT", "low": "EN DUSUK FIYAT", "close": "KAPANIS FIYATI",
       "volume": "TOPLAM ISLEM ADEDI", "turnover": "TOPLAM ISLEM HACMI", "aof": "A.O.F",
       "trade_count": "TOPLAM SOZLESME SAYISI", "halt": "GECICI DURDURMA",
       "special_trade_volume": "OZEL ISLEM BILDIRIMI ISLEM ADEDI",
       "special_trade_turnover": "OZEL ISLEM BILDIRIMI ISLEM HACMI"}
THM = {"reference_price": "REFERANS FIYATI", "upper_limit": "UST LIMIT FIYATI", "lower_limit": "ALT LIMIT FIYATI"}
RAW_THB = {"close": "KAPANIS FIYATI", "trade_count": "TOPLAM SOZLESME SAYISI", "halt": "GECICI DURDURMA",
           "name": "BULTEN ADI", "group": "ENSTRUMAN GRUBU", "market": "PAZAR", "open": "ACILIS FIYATI",
           "high": "EN YUKSEK FIYAT", "low": "EN DUSUK FIYAT", "volume": "TOPLAM ISLEM ADEDI",
           "turnover": "TOPLAM ISLEM HACMI", "aof": "A.O.F", "special_volume": "OZEL ISLEM BILDIRIMI ISLEM ADEDI",
           "special_turnover": "OZEL ISLEM BILDIRIMI ISLEM HACMI"}
RAW_THM = {"reference": "REFERANS FIYATI", "upper": "UST LIMIT FIYATI", "lower": "ALT LIMIT FIYATI"}
CAL_C = "data/raw/pay_calendar_c_20200101_20230921.csv"
CAL_EVIDENCE = "data/raw/pay_calendar_c_bulletin_evidence_20200101_20230921.csv"
MANIFEST = "data/raw/bist/MANIFEST_OOT.csv"
MARKER = "registry/oot/VAULT_OPEN.json"
N, TARGET_H, MAX_SEEN = 10, (1, 3, 5, 10), 15


class Tally:
    def __init__(self):
        self.ok, self.bad = Counter(), Counter()

    def check(self, name, cond):
        (self.ok if cond else self.bad)[name] += 1
        return cond


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def dec(x):
    try:
        v = Decimal((x or "").strip())
    except InvalidOperation:
        return None
    return v if v.is_finite() else None


def read_csv(p: Path):
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def git_show(root: Path, spec: str) -> bytes:
    r = subprocess.run(["git", "-C", str(root), "show", spec], capture_output=True)
    return r.stdout if r.returncode == 0 else b""


def members(root: Path) -> dict[str, dict]:
    """Kohortun etkin MEMBER satırları (append-only: CANCELLED en son etkin satırı düşer)."""
    active = {}
    for r in read_csv(root / "registry/oot/cohort_pre_h99.csv"):
        if r["status"] == "CANCELLED":
            active.pop(r["ticker"], None)
        else:
            active[r["ticker"]] = r
    return {t: r for t, r in active.items() if r["status"] == "MEMBER"}


def zip_name(day: str, kind: str) -> str:
    return kind + day.replace("-", "") + "1"


def q_path(q: Path, day: str, kind: str) -> Path:
    return q / kind / day[:4] / (zip_name(day, kind) + ".zip")


NUMERIC = {"thb": {"KAPANIS FIYATI": r"\d+(\.\d+)?", "TOPLAM SOZLESME SAYISI": r"\d+"},
           "thm": {"REFERANS FIYATI": r"\d+(\.\d+)?", "UST LIMIT FIYATI": r"\d+(\.\d+)?", "ALT LIMIT FIYATI": r"\d+(\.\d+)?"}}


def tarih_day(value: str):
    """TARIH -> ISO gün (bu betiğin kendi çözümlemesi): YYYY-MM-DD ya da G.AA.YYYY / GG.AA.YYYY; başka biçim None."""
    from datetime import date
    iso = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value)
    dot = re.fullmatch(r"(\d{1,2})\.(\d{2})\.(\d{4})", value)
    if iso is None and dot is None:
        return None
    y, mo, d = (iso.group(1), iso.group(2), iso.group(3)) if iso else (dot.group(3), dot.group(2), dot.group(1))
    try:
        return date(int(y), int(mo), int(d)).isoformat()
    except ValueError:
        return None


def code_row(q: Path, day: str, kind: str, code: str, cache: dict):
    """(zip sha, satır sözlüğü ya da None, kodun geçme sayısı). Yalnız `code` satırı tutulur. Zip başına TARIH biçimi ve (ISO
    dışıysa) bütün satırların gün / sayısal biçim SAYILARI ayrı önbellek anahtarına ("zip", gün, tür) yazılır."""
    key = (day, kind, code)
    if key in cache:
        return cache[key]
    data = q_path(q, day, kind).read_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        if names != [zip_name(day, kind) + ".csv"]:
            raise SystemExit("zip iç dosya adı beklenen değil")
        text = z.read(names[0]).decode("cp1254")
    rows = csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=";")
    head = next(rows)
    next(rows)
    rows = [r for r in rows if any(r)]
    i, it = head.index("ISLEM  KODU"), head.index("TARIH")
    if ("zip", day, kind) not in cache:
        iso = all(len(r) > it and re.fullmatch(r"\d{4}-\d{2}-\d{2}", r[it]) for r in rows)
        facts = {"iso": iso, "bad_day": 0, "bad_num": 0}
        if not iso:
            facts["bad_day"] = sum(len(r) <= it or tarih_day(r[it]) != day for r in rows)
            facts["bad_num"] = sum(1 for r in rows for c, pat in NUMERIC[kind].items()
                                   if r[head.index(c)] != "" and not re.fullmatch(pat, r[head.index(c)]))
        cache[("zip", day, kind)] = facts
    found, n = None, 0
    for r in rows:
        if len(r) > i and r[i] == code:
            n += 1
            found = dict(zip(head, r))
    cache[key] = (sha(data), found, n)
    return cache[key]


def check_tarih(t: Tally, cache: dict) -> dict:
    """Okunan her zip'te kod satırının TARIH'i bülten günü; ISO dışı TARIH'li bültende bütün satırların günü ve sayısal biçim."""
    non_iso = sorted({(k[1], k[2]) for k, v in cache.items() if k[0] == "zip" and not v["iso"]})
    for k, v in cache.items():
        if k[0] == "zip":
            if not v["iso"]:
                t.check("ISO dışı TARIH: bütün satırlar bülten gününe çevriliyor", v["bad_day"] == 0)
                t.check("ISO dışı TARIH: sayısal alanlar kanonik biçimde", v["bad_num"] == 0)
        elif v[1] is not None:
            t.check("kod satırının TARIH'i bülten günü (bağımsız çözümleme)", tarih_day(v[1]["TARIH"]) == k[0])
    return {"iso_disi_tarih_bulteni": len(non_iso), "iso_disi_tarih_gunleri": [f"{d} {k.upper()}" for d, k in non_iso]}


def traded(row) -> bool:
    if row is None:
        return False
    tc, c = dec(row["TOPLAM SOZLESME SAYISI"]), dec(row["KAPANIS FIYATI"])
    return tc is not None and tc > 0 and c is not None and c > 0


def label(close_raw: str, upper_raw: str):
    u = dec(upper_raw)
    if u is None or u <= 0:
        return None
    return int(Decimal(close_raw) == u)


def outcome_calendar(root: Path) -> list[str]:
    sessions = {r["calendar_date"] for r in read_csv(root / CAL_C) if r["counts_as_official_session"] == "YES"}
    ev = root / CAL_EVIDENCE
    if ev.exists():
        sessions |= {r["date"] for r in read_csv(ev) if r["decision"] == "TRADING_SESSION"}
    return sorted(sessions)


def pins(root: Path, q: Path):
    man = {(r["date"], r["kind"]): r for r in read_csv(root / MANIFEST)}
    qman = {(r["date"], r["kind"]): r for r in read_csv(q / "MANIFEST.csv")}
    return man, qman


def manifest_prefix(root: Path, base: str, t: Tally) -> tuple[int, set]:
    """MANIFEST_OOT: `base`'teki baytlar önek; dönen (base satır sayısı, base anahtarları)."""
    old = git_show(root, f"{base}:{MANIFEST}")
    t.check("MANIFEST_OOT: base baytları önek (yalnız ekleme)", bool(old) and (root / MANIFEST).read_bytes().startswith(old))
    rows = list(csv.DictReader(io.StringIO(old.decode("utf-8"))))
    return len(rows), {(r["date"], r["kind"]) for r in rows}


def open_files_unchanged(root: Path, base: str, rels: list[str], t: Tally, name: str) -> int:
    n = 0
    for rel in rels:
        n += t.check(name, (root / rel).read_bytes() == git_show(root, f"{base}:{rel}"))
    return n


def stage_d1(root: Path, q: Path, t: Tally, cache: dict, base: str) -> dict:
    mem = members(root)
    sealed = {k: v for k, v in mem.items() if v["vault"] == SEALED}
    opened = {k: v for k, v in mem.items() if v["vault"] != SEALED}
    man, qman = pins(root, q)
    cal = outcome_calendar(root)
    files = sorted((root / "registry/oot/d1_rows").glob("*.json"))
    t.check("d1_rows dosyaları = kohort üyeleri", {p.stem for p in files} == set(mem))
    n_open_same = open_files_unchanged(root, base, [f"registry/oot/d1_rows/{x}.json" for x in sorted(opened)], t,
                                       "açık küme d1_rows base'tekiyle bayt-eşit")
    d1_dates, n_after, n_fields = set(), 0, 0
    for tick in sorted(sealed):
        p = root / "registry/oot/d1_rows" / f"{tick}.json"
        if not t.check("kasa üyesinin d1_rows dosyası var", p.exists()):
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        code, d1b = tick + ".E", doc["d1"]
        d1, ftd = d1b["session_date"], sealed[tick]["first_trading_date"]
        d1_dates.add(d1)
        t.check("ticker = dosya adı", doc["ticker"] == tick)
        t.check("first_trading_date = kohort", doc["first_trading_date"] == ftd)
        t.check("şema / exposure / basis / session_h",
                (doc["schema_version"], doc["exposure_class"], doc["outcome_basis"], d1b["session_h"])
                == ("borsai.oot_d1_row/1", "MACHINE_SEQUENCED", "MACHINE_EXTRACTED", 1))
        rows = {}
        for kind in ("thb", "thm"):
            zsha, row, n = code_row(q, d1, kind, code, cache)
            rows[kind] = row
            ref, m, qm = d1b[kind], man.get((d1, kind)), qman.get((d1, kind))
            t.check(f"{kind} sha: d1_rows = karantina zip", ref["sha256"] == zsha)
            t.check(f"{kind} sha: MANIFEST_OOT = karantina zip", m is not None and m["sha256"] == zsha)
            t.check(f"{kind} sha: karantina manifesti = zip", qm is not None and qm["sha256"] == zsha)
            t.check(f"{kind} url/bayt/iç ad: d1_rows = MANIFEST_OOT", m is not None and ref["url"] == m["url"]
                    and int(m["bytes"]) == q_path(q, d1, kind).stat().st_size
                    and ref["internal_filename"] == m["internal_filename"] == zip_name(d1, kind) + ".csv")
            t.check(f"{kind} satırı tam bir kez", n == 1)
        f = d1b["fields_raw"]
        t.check("fields_raw 14 alan", len(f) == 14)
        for name, col in THB.items():
            n_fields += t.check("fields_raw ↔ THB satırı", rows["thb"] is not None and f[name] == rows["thb"][col])
        for name, col in THM.items():
            n_fields += t.check("fields_raw ↔ THM satırı", rows["thm"] is not None and f[name] == rows["thm"][col])
        lab = label(rows["thb"]["KAPANIS FIYATI"], rows["thm"]["UST LIMIT FIYATI"])
        t.check("ceiling_close_D1 ↔ Decimal(kapanış) == Decimal(üst limit)", d1b["ceiling_close_D1"] == lab)
        u = dec(rows["thm"]["UST LIMIT FIYATI"])
        lc = {k: None if lab is None else dec(rows["thb"][col]) == u
              for k, col in (("open_at_U", "ACILIS FIYATI"), ("high_at_U", "EN YUKSEK FIYAT"), ("close_at_U", "KAPANIS FIYATI"))}
        t.check("lock_consistency", d1b["lock_consistency"] == lc)
        t.check("halt_flag ↔ GECICI DURDURMA", str(d1b["halt_flag"]) == rows["thb"]["GECICI DURDURMA"])
        t.check("D_1 işlem görmüş", traded(rows["thb"]))
        t.check("D_1 ≥ ilk işlem günü", d1 >= ftd)
        n_after += d1 != ftd
        before = [s for s in cal if ftd <= s < d1]
        t.check("[ilk işlem günü, D_1) sonuç takvimi seansları karantinada", all(q_path(q, s, "thb").exists() for s in before))
        t.check("[ilk işlem günü, D_1) seanslarında işlem yok",
                all(not traded(code_row(q, s, "thb", code, cache)[1]) for s in before))
    n_base, base_keys = manifest_prefix(root, base, t)
    new_keys = set(man) - base_keys
    new_dates = d1_dates - {d for d, _ in base_keys}
    t.check("MANIFEST_OOT yeni satır = 2 × önceden pinli olmayan yeni D_1", len(man) - n_base == 2 * len(new_dates)
            and new_keys == {(d, k) for d in new_dates for k in ("thb", "thm")})
    t.check("MANIFEST_OOT her yeni sha = karantina dosyası = karantina manifesti",
            all(q_path(q, d, k).exists() and sha(q_path(q, d, k).read_bytes()) == man[(d, k)]["sha256"] == qman[(d, k)]["sha256"]
                for d, k in new_keys))
    marker = (root / MARKER).read_text(encoding="utf-8") if (root / MARKER).exists() else ""
    t.check("işaret dosyası var", bool(marker))
    pattern = re.compile(r"\b(" + "|".join(sorted(sealed)) + r")\b")
    t.check("işaret dosyasında kasa kodu yok", marker != "" and not pattern.search(marker))
    t.check("işaret dosyası n_sealed = kasa üye sayısı", bool(marker) and json.loads(marker)["n_sealed"] == len(sealed))
    return {"kasa_uyesi": len(sealed), "acik_kume": len(opened), "d1_rows_dosyasi": len(files),
            "acik_d1_rows_bayt_esit": n_open_same, "kasa_farkli_D1_tarihi": len(d1_dates),
            "onceden_pinli_olmayan_yeni_D1_tarihi": len(new_dates), "manifest_oot_satiri": len(man),
            "manifest_oot_yeni_satir": len(man) - n_base, "D1_ilk_islem_gununden_sonra": n_after,
            "karsilastirilan_ham_alan": n_fields}


def stage_s5(root: Path, q: Path, t: Tally, cache: dict, base: str) -> dict:
    mem = members(root)
    sealed = {k: v for k, v in mem.items() if v["vault"] == SEALED}
    opened = {k: v for k, v in mem.items() if v["vault"] != SEALED}
    man, qman = pins(root, q)
    cal = outcome_calendar(root)
    out_dir = root / "data/outcomes_oot"
    csvs = sorted(out_dir.glob("*.csv"))
    raws = sorted((out_dir / "raw").glob("*.json"))
    t.check("sonuç dosyaları = kohort üyeleri", {p.stem for p in csvs} == set(mem) == {p.stem for p in raws})
    n_open_same = open_files_unchanged(
        root, base, [f"data/outcomes_oot/{x}.csv" for x in sorted(opened)] + [f"data/outcomes_oot/raw/{x}.json" for x in sorted(opened)],
        t, "açık küme sonuç/ham kopya base'tekiyle bayt-eşit")
    read_sessions, status, n_rows, n_fields, n_r = set(), Counter(), 0, 0, 0
    n_read_gt_resolved = n_short = 0
    for tick in sorted(sealed):
        p = out_dir / f"{tick}.csv"
        if not t.check("kasa üyesinin sonuç dosyası var", p.exists() and (out_dir / "raw" / f"{tick}.json").exists()):
            continue
        code = tick + ".E"
        rows = read_csv(p)
        raw = json.loads((out_dir / "raw" / f"{tick}.json").read_text(encoding="utf-8"))
        d1doc = json.loads((root / "registry/oot/d1_rows" / f"{tick}.json").read_text(encoding="utf-8"))
        ipo = json.loads((root / "registry/oot/inputs" / f"{tick}.json").read_text(encoding="utf-8"))
        ipo_price = ipo["fields"]["ipo_price_tl"]["value"]
        ftd = sealed[tick]["first_trading_date"]
        t.check("10 satır, h = 1…10", [r["h"] for r in rows] == [str(h) for h in range(1, N + 1)])
        t.check("outcome_basis MACHINE_EXTRACTED", {r["outcome_basis"] for r in rows} == {"MACHINE_EXTRACTED"})
        sess = raw["sessions"]
        t.check("ham kopya kodu ve basis", (raw["code"], raw["outcome_basis"], raw["ticker"]) == (code, "MACHINE_EXTRACTED", tick))
        dates = [s["session_date"] for s in sess]
        read_sessions.update(dates)
        t.check("ham kopya seansları artan ve ≥ ilk işlem günü", dates == sorted(set(dates)) and all(d >= ftd for d in dates))
        in_c = [d for d in dates if d <= cal[-1]]
        t.check("okunan seanslar ardışık sonuç takvimi seansları", in_c == [s for s in cal if s >= ftd][:len(in_c)])
        for s in sess:
            for kind, rowkey, cols in (("thb", "thb_row", RAW_THB), ("thm", "thm_row", RAW_THM)):
                zsha, zrow, n = code_row(q, s["session_date"], kind, code, cache)
                t.check(f"ham kopya {kind} sha = zip", s[f"{kind}_sha256"] == zsha)
                t.check(f"ham kopya {kind} satırı ↔ zip", (s[rowkey] is None and zrow is None) or (
                    s[rowkey] is not None and zrow is not None and n == 1
                    and all(s[rowkey][k] == zrow.get(c, "") for k, c in cols.items())))
        first = next((d for d in dates if code_row(q, d, "thb", code, cache)[1] is not None), None)
        t.check("ilk görünüş", raw["first_appearance"] == first)
        seen = [d for d in dates if first is not None and d >= first][:MAX_SEEN]
        resolved = [d for d in seen if traded(code_row(q, d, "thb", code, cache)[1])][:N]
        got = [r["session_date"] for r in rows if r["session_date"]]
        t.check("D_h çözümü yeniden kuruldu", got == resolved)
        if len(resolved) == N:
            t.check("D_10'dan sonra okunmuş seans yok", max(dates) == resolved[-1])
        else:
            n_short += 1
        n_read_gt_resolved += len(dates) > len(resolved)
        t.check("h = 1 seansı = d1_rows D_1", got[:1] == [d1doc["d1"]["session_date"]])
        for r in rows:
            n_rows += 1
            status[r["status"]] += 1
            if not r["session_date"]:
                t.check("boş satır: TARGET_UNAVAILABLE/PENDING, alanlar boş", r["status"] in ("TARGET_UNAVAILABLE", "PENDING")
                        and all(r[k] == "" for k in ("close_raw", "upper_limit_raw", "R_h", "thb_sha256", "ceiling_close")))
                continue
            d = r["session_date"]
            bsha, b, _ = code_row(q, d, "thb", code, cache)
            msha, m, _ = code_row(q, d, "thm", code, cache)
            t.check("thb/thm sha ↔ zip ↔ MANIFEST_OOT", r["thb_sha256"] == bsha == man[(d, "thb")]["sha256"]
                    and r["thm_sha256"] == msha == man[(d, "thm")]["sha256"])
            for k, col, src in (("close_raw", "KAPANIS FIYATI", b), ("trade_count_raw", "TOPLAM SOZLESME SAYISI", b),
                                ("upper_limit_raw", "UST LIMIT FIYATI", m), ("reference_raw", "REFERANS FIYATI", m)):
                n_fields += t.check(f"{k} ↔ zip", r[k] == ("" if src is None else src[col]))
            t.check("halt_flag ↔ zip", r["halt_flag"] == b["GECICI DURDURMA"])
            lab = label(b["KAPANIS FIYATI"], "" if m is None else m["UST LIMIT FIYATI"])
            t.check("ceiling_close yeniden hesap", r["ceiling_close"] == ("NA" if lab is None else str(lab)))
            t.check("status yeniden hesap", r["status"] == ("NA_LIMIT" if lab is None else "OK"))
            t.check("ipo_price = girdi", r["ipo_price"] == ipo_price)
            if int(r["h"]) in TARGET_H:
                n_r += 1
                ref = Fraction(Decimal(b["KAPANIS FIYATI"])) / Fraction(Decimal(ipo_price)) - 1
                t.check("R_h yeniden hesap |Δ| ≤ 1e-12", abs(float(Fraction(Decimal(r["R_h"])) - ref)) <= 1e-12)
                t.check("Y_h = 1[R > 0]", r["Y_h"] == str(int(ref > 0)))
            else:
                t.check("R_h/Y_h yalnız h ∈ {1,3,5,10}", r["R_h"] == r["Y_h"] == "")
        t.check("h=1 sha = d1_rows sha", rows[0]["thb_sha256"] == d1doc["d1"]["thb"]["sha256"]
                and rows[0]["thm_sha256"] == d1doc["d1"]["thm"]["sha256"])
    n_base, base_keys = manifest_prefix(root, base, t)
    t.check("MANIFEST_OOT her okunan kasa seansı pinli", all((d, k) in man for d in read_sessions for k in ("thb", "thm")))
    new_keys = set(man) - base_keys
    t.check("MANIFEST_OOT yeni satırlar = okunan kasa seanslarının pinsiz olanları",
            new_keys == {(d, k) for d in read_sessions for k in ("thb", "thm")} - base_keys)
    t.check("MANIFEST_OOT her sha = karantina dosyası = karantina manifesti",
            all(sha(q_path(q, d, k).read_bytes()) == r["sha256"] == qman[(d, k)]["sha256"] for (d, k), r in man.items()))
    return {"kasa_uyesi": len(sealed), "sonuc_dosyasi": len(csvs), "ham_kopya": len(raws), "acik_dosya_bayt_esit": n_open_same,
            "kasa_satir": n_rows, "kasa_status": dict(sorted(status.items())), "kasa_okunan_farkli_seans": len(read_sessions),
            "manifest_oot_satiri": len(man), "manifest_oot_yeni_satir": len(man) - n_base,
            "karsilastirilan_ham_alan": n_fields, "R_h_karsilastirma": n_r, "10_seansi_olmayan_kasa_uyesi": n_short,
            "okunan_gt_cozumlenen_kasa_uyesi": n_read_gt_resolved}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("d1", "s5"), required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--quarantine", type=Path, required=True)
    ap.add_argument("--base", required=True, help="açılıştan önceki commit (d1: C; s5: VA1/VA2 sonrası HEAD)")
    a = ap.parse_args()
    t, cache = Tally(), {}
    info = (stage_d1 if a.stage == "d1" else stage_s5)(a.root, a.quarantine, t, cache, a.base)
    info.update(check_tarih(t, cache))
    out = {"stage": a.stage, **info, "denetim_gecen": sum(t.ok.values()), "denetim_fark": sum(t.bad.values()),
           "fark_turleri": dict(sorted(t.bad.items())), "denetim_turu": len(set(t.ok) | set(t.bad)),
           "okunan_zip": len({(k[0], k[1]) for k in cache if k[0] != "zip"}),
           "borsai_import_edildi": any(m == "borsai" or m.startswith("borsai.") for m in sys.modules)}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if not t.bad and not out["borsai_import_edildi"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

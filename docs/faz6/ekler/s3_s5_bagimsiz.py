#!/usr/bin/env python3
"""BORSAI_FAZ6_S3_S5_EXTRACT T5: bağımsız ham alan denetimi. `borsai` İMPORT EDİLMEZ (yalnız stdlib); repo dışında koşar.

Karantinadaki THB/THM zip'lerini doğrudan açar ve YALNIZ açık küme (OPEN ∪ EXPOSED_*) kodlarının `<T>.E` satırlarına bakar;
kasadaki (SEALED) kodlarla hiçbir zip satırı aranmaz (kohort dosyasından yalnız açık küme tutulur). Çıktı yalnız SAYI: hiçbir
kod, fiyat, getiri ya da limit yazılmaz. Betik değer içermez.

--stage s3: registry/oot/d1_rows/<T>.json
  - 14 ham alan (fields_raw) ↔ D_1 zip satırı; halt_flag, ceiling_close_D1 (Decimal kapanış == üst limit), lock_consistency
  - thb/thm sha256 ↔ karantina dosyası ↔ MANIFEST_OOT ↔ karantina manifesti; url ve bayt ↔ MANIFEST_OOT
  - D_1 kuralı: D_1 ≥ ilk işlem günü; [ilk işlem günü, D_1) aralığındaki her Takvim C seansının THB'si karantinada ve kod o
    günlerde işlem görmemiş; D_1'de işlem görmüş (sözleşme > 0, kapanış > 0)
  - MANIFEST_OOT: satır = 2 × farklı D_1 tarihi; her sha karantinayla eşit
  - bülten kanıtı (EK1 K3/K4, K7): satırlar = Takvim C'nin hafta içi tam kapanışları; 200 günlerinde zip sha/bayt = pin, toplam
    sayılar (satır, `.E` satırı, sözleşme > 0 olan `.E` satırı) yeniden sayılır, karar K4'le yeniden türetilir
Sonuç takvimi (K7): Takvim C seansları ∪ kanıtta TRADING_SESSION olan günler (kanıt dosyası doğrudan okunur).
--stage s5: data/outcomes_oot/<T>.csv ve raw/<T>.json (S5 görevinin ikinci bölümü)
  - close_raw, upper_limit_raw, reference_raw, trade_count_raw, halt_flag ↔ ilgili seansın zip satırı; thb/thm sha ↔ zip ↔
    MANIFEST_OOT; ceiling_close ↔ Decimal(kapanış) == Decimal(üst limit) (limit yok/≤ 0 -> NA); status (OK / NA_LIMIT /
    TARGET_UNAVAILABLE / PENDING); h ∈ {1, 3, 5, 10} için R_h ↔ kapanış / arz fiyatı − 1 (|Δ| ≤ 1e-12), Y_h = 1[R > 0]
  - ham kopya: her okunan seansın satırı zip'le eşit; D_h çözümü (ilk görünüş, işlem gören ilk 10 seans) yeniden kurulur;
    D_10'dan sonra okunmuş seans yok
  - D_1 tutarlılığı (h = 1 ↔ d1_rows); MANIFEST_OOT: S3a satırları bayt olarak başta, toplam = 2 × okunan farklı seans
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
import sys
import zipfile
from collections import Counter
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path

OPEN_VAULTS = {"OPEN", "EXPOSED_ARCHIVE", "EXPOSED_CODEX"}
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


def open_codes(root: Path) -> dict[str, dict]:
    """Kohort dosyasından açık küme (append-only: CANCELLED en son etkin satırı düşer). Kasadaki satırlar tutulmaz."""
    active = {}
    for r in read_csv(root / "registry/oot/cohort_pre_h99.csv"):
        if r["status"] == "CANCELLED":
            active.pop(r["ticker"], None)
        else:
            active[r["ticker"]] = r
    return {t: r for t, r in active.items() if r["status"] == "MEMBER" and r["vault"] in OPEN_VAULTS}


def zip_name(day: str, kind: str) -> str:
    return kind + day.replace("-", "") + "1"


def q_path(q: Path, day: str, kind: str) -> Path:
    return q / kind / day[:4] / (zip_name(day, kind) + ".zip")


def code_row(q: Path, day: str, kind: str, code: str, cache: dict):
    """(zip sha, satır sözlüğü ya da None, kodun geçme sayısı). Yalnız `code` satırı tutulur."""
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
    i = head.index("ISLEM  KODU")
    found, n = None, 0
    for r in rows:
        if len(r) > i and r[i] == code:
            n += 1
            found = dict(zip(head, r))
    cache[key] = (sha(data), found, n)
    return cache[key]


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
    """K7: Takvim C seansları ∪ kanıtta TRADING_SESSION olan günler (2023-09-21'e kadar)."""
    sessions = {r["calendar_date"] for r in read_csv(root / CAL_C) if r["counts_as_official_session"] == "YES"}
    ev = root / CAL_EVIDENCE
    if ev.exists():
        sessions |= {r["date"] for r in read_csv(ev) if r["decision"] == "TRADING_SESSION"}
    return sorted(sessions)


def check_evidence(root: Path, q: Path, t: Tally) -> dict:
    """EK1 kanıt dosyasının bağımsız denetimi: yalnız toplam sayılar (hiçbir satır tutulmaz)."""
    ev = root / CAL_EVIDENCE
    if not t.check("kanıt dosyası var", ev.exists()):
        return {}
    from datetime import date
    closures = [r["calendar_date"] for r in read_csv(root / CAL_C)
                if date.fromisoformat(r["calendar_date"]).weekday() < 5 and r["counts_as_official_session"] != "YES"]
    rows = read_csv(ev)
    t.check("kanıt satırları = Takvim C hafta içi kapanışları", [r["date"] for r in rows] == closures)
    for r in rows:
        if r["thb_head_status"] == "404":
            t.check("kanıt 404 -> NOT_PUBLISHED, boş alanlar", r["decision"] == "NOT_PUBLISHED" and not any(
                r[k] for k in ("thb_sha256", "thb_bytes", "n_rows", "n_equity_rows", "n_equity_rows_traded")))
            continue
        data = q_path(q, r["date"], "thb").read_bytes()
        t.check("kanıt zip sha/bayt = karantina", (sha(data), str(len(data))) == (r["thb_sha256"], r["thb_bytes"]))
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            text = z.read(zip_name(r["date"], "thb") + ".csv").decode("cp1254")
        rd = csv.reader(io.StringIO(text.lstrip("\ufeff")), delimiter=";")
        head = next(rd)
        next(rd)
        ic, idt, itc = head.index("ISLEM  KODU"), head.index("TARIH"), head.index("TOPLAM SOZLESME SAYISI")
        n = n_eq = n_tr = bad_date = 0
        for row in rd:
            if not any(row):
                continue
            n += 1
            bad_date += row[idt] != r["date"]
            if row[ic].endswith(".E"):
                n_eq += 1
                v = dec(row[itc])
                n_tr += v is not None and v > 0
        t.check("kanıt sayıları yeniden sayıldı", (str(n), str(n_eq), str(n_tr)) ==
                (r["n_rows"], r["n_equity_rows"], r["n_equity_rows_traded"]) and bad_date == 0)
        want = "PUBLISHED_NO_TRADING" if n_tr == 0 else "TRADING_SESSION" if n_tr >= 50 else "DUR"
        t.check("kanıt kararı K4 ile yeniden türetildi", r["decision"] == want)
    return {"kanit_satiri": len(rows), "kanit_karar": dict(sorted(Counter(r["decision"] for r in rows).items())),
            "kanit_trading_session": [r["date"] for r in rows if r["decision"] == "TRADING_SESSION"]}


def pins(root: Path, q: Path):
    man = {(r["date"], r["kind"]): r for r in read_csv(root / "data/raw/bist/MANIFEST_OOT.csv")}
    qman = {(r["date"], r["kind"]): r for r in read_csv(q / "MANIFEST.csv")}
    return man, qman


def stage_s3(root: Path, q: Path, t: Tally, cache: dict) -> dict:
    opened = open_codes(root)
    man, qman = pins(root, q)
    cal = outcome_calendar(root)
    evidence = check_evidence(root, q, t)
    files = sorted((root / "registry/oot/d1_rows").glob("*.json"))
    t.check("d1_rows dosyası açık küme üyesi", all(p.stem in opened for p in files))
    t.check("her açık üyenin d1_rows dosyası var", {p.stem for p in files} == set(opened))
    d1_dates, n_after, n_fields, n_outside_c = set(), 0, 0, 0
    for p in files:
        doc = json.loads(p.read_text(encoding="utf-8"))
        tick, code, d1b = p.stem, p.stem + ".E", doc["d1"]
        d1, ftd = d1b["session_date"], opened[p.stem]["first_trading_date"]
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
        if d1 != ftd:
            n_after += 1
        before = [s for s in cal if ftd <= s < d1]
        t.check("[ilk işlem günü, D_1) sonuç takvimi seansları karantinada", all(q_path(q, s, "thb").exists() for s in before))
        t.check("[ilk işlem günü, D_1) seanslarında işlem yok",
                all(not traded(code_row(q, s, "thb", code, cache)[1]) for s in before))
        n_outside_c += d1 > cal[-1]
    t.check("MANIFEST_OOT satır = 2 × farklı D_1", len(man) == 2 * len(d1_dates)
            and set(man) == {(d, k) for d in d1_dates for k in ("thb", "thm")})
    t.check("MANIFEST_OOT her sha = karantina dosyası",
            all(q_path(q, d, k).exists() and sha(q_path(q, d, k).read_bytes()) == r["sha256"] for (d, k), r in man.items()))
    return {"d1_rows_dosyasi": len(files), "acik_kume": len(opened), "farkli_D1_tarihi": len(d1_dates),
            "manifest_oot_satiri": len(man), "D1_ilk_islem_gununden_sonra": n_after,
            "karsilastirilan_ham_alan": n_fields, "D1_Takvim_C_sonrasi": n_outside_c, **evidence}


def stage_s5(root: Path, q: Path, t: Tally, cache: dict, s3a: str) -> dict:
    opened = open_codes(root)
    man, qman = pins(root, q)
    cal = outcome_calendar(root)
    evidence = check_evidence(root, q, t)
    out_dir = root / "data/outcomes_oot"
    csvs = sorted(out_dir.glob("*.csv"))
    raws = sorted((out_dir / "raw").glob("*.json"))
    t.check("sonuç dosyaları = açık küme", {p.stem for p in csvs} == set(opened) == {p.stem for p in raws})
    read_sessions, status, n_rows, n_fields, n_r = set(), Counter(), 0, 0, 0
    n_read_gt_resolved = n_short = 0
    for p in csvs:
        tick = p.stem
        code = tick + ".E"
        rows = read_csv(p)
        raw = json.loads((out_dir / "raw" / f"{tick}.json").read_text(encoding="utf-8"))
        d1doc = json.loads((root / "registry/oot/d1_rows" / f"{tick}.json").read_text(encoding="utf-8"))
        ipo = json.loads((root / "registry/oot/inputs" / f"{tick}.json").read_text(encoding="utf-8"))
        ipo_price = ipo["fields"]["ipo_price_tl"]["value"]
        ftd = opened[tick]["first_trading_date"]
        t.check("10 satır, h = 1…10", [r["h"] for r in rows] == [str(h) for h in range(1, N + 1)])
        t.check("outcome_basis MACHINE_EXTRACTED", {r["outcome_basis"] for r in rows} == {"MACHINE_EXTRACTED"})
        # ham kopya ve D_h çözümü
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
        # satırlar
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
    # MANIFEST_OOT
    text = (root / "data/raw/bist/MANIFEST_OOT.csv").read_bytes()
    s3a_text = subprocess.run(["git", "-C", str(root), "show", f"{s3a}:data/raw/bist/MANIFEST_OOT.csv"], check=True,
                              capture_output=True).stdout
    t.check("MANIFEST_OOT: S3a satırları bayt olarak başta", text.startswith(s3a_text))
    t.check("MANIFEST_OOT satır = 2 × okunan farklı seans", len(man) == 2 * len(read_sessions)
            and set(man) == {(d, k) for d in read_sessions for k in ("thb", "thm")})
    t.check("MANIFEST_OOT her sha = karantina dosyası",
            all(sha(q_path(q, d, k).read_bytes()) == r["sha256"] == qman[(d, k)]["sha256"] for (d, k), r in man.items()))
    return {"sonuc_dosyasi": len(csvs), "ham_kopya": len(raws), "satir": n_rows, "status": dict(sorted(status.items())),
            "okunan_farkli_seans": len(read_sessions), "manifest_oot_satiri": len(man),
            "karsilastirilan_ham_alan": n_fields, "R_h_karsilastirma": n_r, "10_seansi_olmayan_uye": n_short,
            "okunan_gt_cozumlenen_uye": n_read_gt_resolved, **evidence}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("s3", "s5"), required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--quarantine", type=Path, required=True)
    ap.add_argument("--s3a", help="S3a commit'i (s5: MANIFEST_OOT önek denetimi)")
    a = ap.parse_args()
    t, cache = Tally(), {}
    info = stage_s3(a.root, a.quarantine, t, cache) if a.stage == "s3" else stage_s5(a.root, a.quarantine, t, cache, a.s3a)
    out = {"stage": a.stage, **info, "denetim_gecen": sum(t.ok.values()), "denetim_fark": sum(t.bad.values()),
           "fark_turleri": dict(sorted(t.bad.items())), "denetim_turu": len(set(t.ok) | set(t.bad)),
           "okunan_zip": len({(d, k) for d, k, _ in cache}),
           "borsai_import_edildi": any(m == "borsai" or m.startswith("borsai.") for m in sys.modules)}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if not t.bad and not out["borsai_import_edildi"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

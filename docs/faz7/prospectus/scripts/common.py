"""FAZ7 doğrulama ortak yardımcıları (repo dışı)."""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
from pathlib import Path

T = Path(__file__).resolve().parent.parent          # verified_faz7/_tools
V = T.parent                                         # verified_faz7
CODEX = Path.home() / "Desktop/BorsAi_codex"
REPO = Path("/Users/ahmet/Desktop/BorsAi")
PY = "/Users/ahmet/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"

FIELDS = ["distribution_method", "price_stability_planned", "price_stability_days", "issuer_lockup_days",
          "shareholder_lockup_days", "sector", "participation_index_eligible"]

MEMBERS = [r for r in csv.DictReader(open(REPO / "docs/specs_faz6/ekler/evren_listesi.csv", encoding="utf-8"))
           if r["status"] == "MEMBER"]
EV = {r["ticker"]: r for r in MEMBERS}
FTD = {r["ticker"]: dt.date.fromisoformat(r["first_trading_date"]) for r in MEMBERS}


def bb_start(r) -> dt.date:
    b = r["bookbuilding_kap"].replace(".", "/").replace(" ", "")
    ftd = FTD[r["ticker"]]
    y = int(b[-4:])
    if re.fullmatch(r"[\d-]+/\d{1,2}/\d{4}", b):
        return dt.date(y, int(b.split("/")[1]), int(b.split("/")[0].split("-")[0]))
    d0, mo = b.split("-")[0].split("/")[:2]
    s = dt.date(y, int(mo), int(d0))
    return s if s <= ftd else dt.date(y - 1, int(mo), int(d0))


def window(t: str) -> tuple[dt.date, dt.date]:
    """Listeleme öncesi arama penceresi: [min(SPK onayı − 3, talep başı − 14), ilk işlem günü − 1]."""
    r = EV[t]
    s = bb_start(r) - dt.timedelta(days=14)
    if r["approval_date_spk"]:
        s = min(s, dt.date.fromisoformat(r["approval_date_spk"]) - dt.timedelta(days=3))
    return s, FTD[t] - dt.timedelta(days=1)


def codex_all() -> dict:
    c = {}
    for b in ("B1", "B2", "B3", "B4"):
        d = json.load(open(CODEX / f"BORSAI_FAZ7_CODEX_PROSPECTUS_{b}_20260925.json"))
        for ipo in d["ipos"]:
            ipo["_batch"] = b
            c[ipo["ticker"]] = ipo
    return c


def codex_exposure() -> list:
    out = []
    for b in ("B1", "B2", "B3", "B4"):
        d = json.load(open(CODEX / f"BORSAI_FAZ7_CODEX_PROSPECTUS_{b}_20260925.json"))
        for e in d.get("exposure_log", []):
            out.append({"batch": b, **e})
    return out


def N(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def iso_kap(s: str) -> str:
    """'04.02.2020 11:25:10' -> ISO +03:00."""
    d, t = s.split(" ")
    dd, mm, yy = d.split(".")
    return f"{yy}-{mm}-{dd}T{t}+03:00"


def before_listing(published_at: str, t: str) -> bool:
    """Yayın zamanı (İstanbul) ilk işlem günü 00:00'dan önce mi."""
    p = dt.datetime.fromisoformat(published_at)
    return p < dt.datetime.combine(FTD[t], dt.time(0, 0), tzinfo=p.tzinfo)

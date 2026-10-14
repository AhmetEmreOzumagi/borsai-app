"""Mutasyon (d) sondası: sentetik piyasa yeterince uzun olduğunda ayıklayıcı kaç seans okuyor ve ham kopyaya kaç seans yazıyor?"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path.cwd())); sys.path.insert(0, str(Path.cwd() / "tests"))
import faz6_support as f6
from borsai import outcomes_oot as oo, outcomes as oc
from borsai.provenance import sha256_bytes
cal = oo.load_calendar_oot()
members = [{"ticker": "SYNA", "ftd": "2021-03-01"}]
sessions = [s for s in cal.sessions if s >= "2021-02-26"][:60]
paths = {"SYNA": f6.ceiling_path(cal.sessions, "2021-03-01", ["11.55"] * 40)}
files = f6.market(sessions, paths)
calls = []
def fetch(s, k):
    calls.append(s); return files[oc.source_url(s, k)], oo.Pin(s, k, oc.source_url(s, k), sha256_bytes(files[oc.source_url(s, k)]), 1, "", "t", oc.internal_name(s, k))
ext = oo.resolve_member("SYNA", "2021-03-01", cal, {"SYNA": "OPEN"}, fetch=fetch)
raw = oo.raw_copies(ext)
rows = oo.outcome_rows_oot(ext, "10.5", cal)
print(json.dumps({"okunan_seans": len(set(calls)), "ham_kopya_seans": len(raw["sessions"]), "d10": ext.resolution.sessions[-1].date,
                  "son_okunan": max(calls), "sonuc_satir": len(rows), "durum": sorted({r["status"] for r in rows})}))

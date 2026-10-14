"""Hijyen sayımı: rapor + ekler/1 içinde th[bm]+8 haneli tarih kalıbı ve kasa (SEALED) kodu geçişi. Kodlar yalnız bellekte; çıktıya yazılmaz."""
import csv, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sealed = {r["ticker"] for r in csv.DictReader(open(ROOT / "registry/oot/cohort_pre_h99.csv", encoding="utf-8")) if r["vault"] == "SEALED"}
files = [ROOT / "docs/fable_kitap_audit/AUDIT_1_VERI.md"] + sorted(p for p in (ROOT / "docs/fable_kitap_audit/ekler/1").rglob("*") if p.is_file() and p.name != "hijyen.txt")
pat = re.compile(r"th[bm]\d{8}")
n_pat = n_sealed = 0
for p in files:
    t = p.read_text(encoding="utf-8", errors="ignore")
    n_pat += len(pat.findall(t))
    n_sealed += sum(len(re.findall(r"\b" + re.escape(c) + r"\b", t)) for c in sealed)
out = f"dosya sayısı: {len(files)}\nth[bm]+8 hane kalıbı: {n_pat}\nkasa kodu geçişi: {n_sealed}\n"
(ROOT / "docs/fable_kitap_audit/ekler/1/hijyen.txt").write_text(out, encoding="utf-8"); print(out)

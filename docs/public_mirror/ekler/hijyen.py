#!/usr/bin/env python3
"""Rapor ve ekler hijyeni: kasa (SEALED) kodu geçişi ve th[bm]+8 hane bülten adı sayımı; koruma dosyaları karşılaştırması."""
import csv, re, glob, os, subprocess
os.chdir(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip())
rows = list(csv.DictReader(open("registry/oot/cohort_pre_h99.csv", encoding="utf-8-sig")))
sealed = {r["ticker"] for r in rows if r["vault"] == "SEALED"}
SR = re.compile(r"(?<![A-Z0-9])(?:" + "|".join(map(re.escape, sorted(sealed))) + r")(?![A-Z0-9])")
BR = re.compile(r"th[bm]\d{8}")
files = sorted(glob.glob("docs/public_mirror/**/*", recursive=True))
k = b = 0
for f in files:
    if os.path.isdir(f) or f.endswith(".pyc"):
        continue
    t = open(f, encoding="utf-8", errors="replace").read()
    k += len(SR.findall(t)); b += len(BR.findall(t))
print(f"kasa kodu geçişi: {k}")
print(f"th[bm]+8 hane bülten adı: {b}")
def body(p):
    return [l for l in open(p).read().splitlines() if not l.startswith("#")]
o, s = body("docs/public_mirror/ekler/koruma_once.txt"), body("docs/public_mirror/ekler/koruma_sonra.txt")
print("koruma önce == sonra:", o == s, f"({len(o)} satır)")

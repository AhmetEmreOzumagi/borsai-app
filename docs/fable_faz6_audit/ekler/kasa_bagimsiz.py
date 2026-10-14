#!/usr/bin/env python3
"""Kasa (vault) çekilişinin BAĞIMSIZ yeniden üretimi: `borsai` import edilmez; yalnız KARARLAR D2 ve SPEC_DEVIATIONS I4
metninden. Girdi: registry/oot/cohort_pre_h99.csv (ticker, first_trading_date, status, vault). Çıktı: ana okumanın ve
alternatif okumaların kohort dosyasındaki `vault` sütunuyla eşleşme sayıları (kod adı yazılmaz)."""
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]
COHORT = ROOT / "registry" / "oot" / "cohort_pre_h99.csv"
SEED = 20260924                                           # KARARLAR D2
EXPOSED = {"TARKM": "EXPOSED_ARCHIVE", "GIPTA": "EXPOSED_ARCHIVE", "ADGYO": "EXPOSED_ARCHIVE", "REEDR": "EXPOSED_ARCHIVE",
           "PNLSN": "EXPOSED_CODEX"}                      # KARARLAR D2 (şartname §11-5 + Codex maruziyeti)

rows = list(csv.DictReader(COHORT.open(encoding="utf-8", newline="")))
assert not any(r["status"] == "CANCELLED" for r in rows), "CANCELLED satır var; etkin satır mantığı gerekir"
members = [r for r in rows if r["status"] == "MEMBER"]
file_vault = {r["ticker"]: r["vault"] for r in members}
assert len(members) == 135


def draw(*, per_year_rng=False, rounding="floor", method="choice", sort_key="date_ticker", years="asc",
         exposed_removed=True, stratified=True, shuffle=True):
    rng = np.random.Generator(np.random.PCG64(SEED))
    out = {}
    key = (lambda r: (r["first_trading_date"], r["ticker"])) if sort_key == "date_ticker" else (lambda r: r["ticker"])
    strata = {}
    for r in sorted(members, key=key):
        if exposed_removed and r["ticker"] in EXPOSED:
            out[r["ticker"]] = EXPOSED[r["ticker"]]
            continue
        strata.setdefault(r["first_trading_date"][:4] if stratified else "ALL", []).append(r["ticker"])
    for year in sorted(strata, reverse=(years == "desc")):
        if per_year_rng:
            rng = np.random.Generator(np.random.PCG64(SEED))
        t = strata[year]
        n = len(t)
        k = n // 2 if rounding == "floor" else (n + 1) // 2
        if method == "choice":
            idx = set(int(i) for i in rng.choice(n, size=k, replace=False, shuffle=shuffle))
        elif method == "choice_array":
            idx = set(t.index(x) for x in rng.choice(np.array(t), size=k, replace=False))
        elif method == "permutation":
            idx = set(int(i) for i in rng.permutation(n)[:k])
        elif method == "shuffle_list":
            tt = list(t)
            rng.shuffle(tt)
            idx = set(t.index(x) for x in tt[:k])
        else:
            raise ValueError(method)
        for i, tk in enumerate(t):
            if not exposed_removed and tk in EXPOSED:
                out[tk] = EXPOSED[tk]
            else:
                out[tk] = "SEALED" if i in idx else "OPEN"
    return out


VARIANTS = {
    "ANA_OKUMA (D2+I4: tek PCG64(20260924), yıllar artan, tabaka içi (tarih,ticker), choice(n, n//2, replace=False), maruz kodlar önce çıkarılır)": {},
    "alt: rng.permutation(n)[:n//2]": {"method": "permutation"},
    "alt: rng.choice(dizi_ticker, n//2, replace=False)": {"method": "choice_array"},
    "alt: rng.shuffle(liste)[:n//2]": {"method": "shuffle_list"},
    "alt: choice(..., shuffle=False)": {"shuffle": False},
    "alt: tek sayıda YUKARI yuvarlama (ceil)": {"rounding": "ceil"},
    "alt: her yıl için yeni PCG64(20260924)": {"per_year_rng": True},
    "alt: tabaka içi sıra yalnız ticker": {"sort_key": "ticker"},
    "alt: yıllar azalan sırayla": {"years": "desc"},
    "alt: maruz kodlar çekilişe girer, sonra üzerine yazılır": {"exposed_removed": False},
    "alt: tabakasız (tek çekiliş, 130 aday, 65 kasa)": {"stratified": False},
}
print(f"numpy {np.__version__}; kohort {COHORT.relative_to(ROOT)}; üye {len(members)}")
for name, kw in VARIANTS.items():
    got = draw(**kw)
    match = sum(got[t] == file_vault[t] for t in file_vault)
    sealed = sum(v == "SEALED" for v in got.values())
    print(f"{match:>3}/135 eşleşme | kasa n={sealed:>2} | {name}")
counts = {}
for r in members:
    counts.setdefault(r["year"], {}).setdefault(r["vault"], 0)
    counts[r["year"]][r["vault"]] += 1
print("dosyadaki yıl × kasa sayıları:", {y: dict(sorted(c.items())) for y, c in sorted(counts.items())})
print("borsai sys.modules içinde mi:", "borsai" in sys.modules)

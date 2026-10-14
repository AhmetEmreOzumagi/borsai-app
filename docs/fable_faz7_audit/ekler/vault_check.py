#!/usr/bin/env python3
"""Kasa denetimi (madde 2-v): SEALED kod kümesi bellekte (registry/oot/records/ kayıtlarındaki `vault` alanından; kohort dosyasıyla
sayı olarak çapraz denetim); listelenen yollarda kasa kodu geçen dosya/eşleşme SAYISI basılır, kod basılmaz. Ayrıca canlı rejim
değeri (r = 0) ve tahmin yolu davranışı bir alt süreçte Opus'un stdlib tahminiyle sınanır (madde 2-iv).
Kullanım: .venv/bin/python docs/fable_faz7_audit/ekler/vault_check.py"""
import csv, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sealed, opened = set(), set()
for p in (ROOT / "registry" / "oot" / "records").glob("*/*.json"):
    r = json.loads(p.read_text(encoding="utf-8"))
    (sealed if r.get("vault") == "SEALED" else opened).add(r["ticker"])
cohort = list(csv.DictReader((ROOT / "registry" / "oot" / "cohort_pre_h99.csv").open(encoding="utf-8-sig")))
sealed_c = {r["ticker"] for r in cohort if r["vault"] == "SEALED"}
print(f"[kasa] kayıtlardan SEALED {len(sealed)}, açık {len(opened)}; kohort dosyasından SEALED {len(sealed_c)}; kümeler aynı: {sealed == sealed_c}")
pat = re.compile(r"\b(" + "|".join(sorted(sealed)) + r")\b")
TEXT = {".csv", ".json", ".jsonl", ".md", ".txt", ".py", ".sh", ".toml", ".yaml", ".yml", ".html", ".tsv"}
targets = ["data", "tests/reference/macos_golden_faz7", "docs/MODELS.md", "experiments/log.jsonl", "docs/faz7", "docs/SPEC_DEVIATIONS.md",
           "docs/fable_faz7_audit"]
total = 0
for rel in targets:
    base = ROOT / rel
    files = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in TEXT)
    n_files = n_hits = 0
    per = {}
    for p in files:
        rp = p.relative_to(ROOT).as_posix()
        if rp.startswith("docs/faz7/prospectus/"):
            continue                                                   # tanım gereği 135 üyenin hepsi geçer; görev kapsamı dışı
        hits = set(pat.findall(p.read_text(encoding="utf-8", errors="replace")))
        if rp == "data/outcomes/COMPLETENESS.csv":
            rows = list(csv.DictReader(p.open(encoding="utf-8")))
            hits_scope = {f for r in rows if r.get("first_seen", "") < "2026-08-07" for v in r.values() for f in pat.findall(v or "")}
            per[rp] = f"{len(hits)} kod (J18 istisnası: kohort penceresi dışı satırlarda {len(hits)}, pencere içinde {len(hits_scope)})"
            hits = hits_scope
        if hits:
            n_files += 1
            n_hits += len(hits)
            per.setdefault(rp, f"{len(hits)} farklı kasa kodu")
    total += n_hits
    print(f"[kasa] {rel}: taranan dosya {len(files)}, kasa kodu geçen dosya {n_files}, farklı kod eşleşmesi {n_hits}" + (f"; ayrıntı {per}" if per else ""))
print(f"[kasa] TOPLAM (J18 istisnası dışında): {total}")
open_pat = re.compile(r"\b(" + "|".join(sorted(opened)) + r")\b")
n_open_v2 = len(set(open_pat.findall((ROOT / "data" / "training_table_v2.csv").read_text(encoding="utf-8"))))
print(f"[kasa] training_table_v2.csv'de açık küme kodu sayısı: {n_open_v2}/71; kasa kodu: {len(set(pat.findall((ROOT / 'data' / 'training_table_v2.csv').read_text(encoding='utf-8'))))}")

# (iv) canlı r = 0: Opus'un stdlib tahmini önizleme JSON'uyla (alt süreç; bu betik borsai import etmez)
code = r'''
import json, sys
from borsai import predict_hazard as ph
p = json.load(open("tests/reference/macos_golden_faz7/ceiling_hazard_v1_pooled_final_fit_preview.json", encoding="utf-8"))
h99 = {"ipo_price_tl": "25.52", "shares_offered": "87500000", "post_ipo_share_capital": "312500000", "capital_increase_shares": "62500000",
       "total_demand_multiple": "6.1", "ipo_size_tl": "2233000000", "tufe_index": "120.5"}
live = ph.predict(p, h99)
pre = ph.predict(p, {**h99, "alloc_regime": "PRE_20211111"})
thr = ph.predict(p, {**h99, "alloc_regime": "THRESH100_20211111"})
eq = ph.predict(p, {**h99, "alloc_regime": "EQUAL_DIST_20230330"})
bad = ph.predict(p, {**h99, "alloc_regime": "X"})
out = {"live_r": live["regime_value_used"], "live_source": live["regime_source"], "pre_r": pre["regime_value_used"], "thresh_r": thr["regime_value_used"],
       "equal_r": eq["regime_value_used"], "equal_S_equals_live": eq["S"] == live["S"], "pre_S1_lower": pre["S"][0] < live["S"][0],
       "unknown_label_refused": bad["refused"]["code"] if bad["refused"] else None, "clipped_any_semantics": live["clipped"], "clipped_features": live["clipped_features"],
       "delta": p["regime"]["delta"], "live_value": p["regime"]["live_value"], "borsai_predict_hazard_stdlib": [m for m in ("numpy", "scipy") if m in sys.modules]}
print(json.dumps(out))
'''
res = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
print("[rejim] stdlib tahmin (Opus kodu, alt süreç):", res.stdout.strip() or res.stderr[-500:])

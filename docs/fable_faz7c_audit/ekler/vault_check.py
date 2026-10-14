#!/usr/bin/env python3
"""Kasa denetimi (BORSAI_FAZ7C_FABLE_REPRO_AUDIT adım 2-iv): SEALED kod kümesi bellekte (registry/oot/records/ kayıtlarındaki `vault`
alanından; kohort dosyasıyla yalnız sayı olarak çapraz denetim; hiçbir satır basılmaz); listelenen yollarda kasa kodu geçen dosya ve
eşleşme SAYISI basılır, kod basılmaz. Kullanım: .venv/bin/python docs/fable_faz7c_audit/ekler/vault_check.py"""
import csv, json, re, sys
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
targets = ["data", "tests/reference/macos_golden_faz7c", "docs/MODELS.md", "experiments/log.jsonl", "docs/faz7c", "docs/SPEC_DEVIATIONS.md",
           "docs/specs_faz7_c", "docs/fable_faz7c_audit", "borsai", "tests/test_faz7c_model.py", "tests/test_faz7c_backtest.py",
           "tests/test_faz7c_golden.py", "tests/faz7c_support.py"]
total = 0
for rel in targets:
    base = ROOT / rel
    files = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in TEXT)
    n_files = n_hits = 0
    per = {}
    for p in files:
        rp = p.relative_to(ROOT).as_posix()
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
# keşif satırları (kind: exploration) ayrıca: variant metinlerinde kasa kodu var mı (yalnız sayı)
n_expl = n_expl_hit = 0
for line in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines():
    e = json.loads(line)
    if e.get("kind") == "exploration":
        n_expl += 1
        n_expl_hit += bool(pat.search(json.dumps(e, ensure_ascii=False)))
print(f"[kasa] günlükteki exploration satırı {n_expl}, kasa kodu geçen {n_expl_hit}")
open_pat = re.compile(r"\b(" + "|".join(sorted(opened)) + r")\b")
for rel in ("data/training_table_v2.csv", "tests/reference/macos_golden_faz7c/fall_d10_v0_pooled_fold_ledger.csv"):
    txt = (ROOT / rel).read_text(encoding="utf-8")
    print(f"[kasa] {rel}: açık küme kodu {len(set(open_pat.findall(txt)))}/71; kasa kodu {len(set(pat.findall(txt)))}")

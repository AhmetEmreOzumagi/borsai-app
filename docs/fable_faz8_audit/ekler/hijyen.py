#!/usr/bin/env python3
"""Kasa ve hijyen taraması (BORSAI_FAZ8_FABLE_REPRO_AUDIT adım 3-vii): SEALED kasa kodu kümesi bellekte (registry'den), yalnız sayı basılır;
bülten adı kalıbı (th[bm]YYYYMMDD) ve `thb`/`thm` + 8 haneli tarih aranır. Bakılan yerler: docs/faz8/, docs/specs_faz8/, docs/MODELS.md Faz 8
bölümü, experiments/log.jsonl Faz 8 satırları, yeni testler, görev dosyası ve bu denetimin kendi dizini (docs/fable_faz8_audit/)."""
import re, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from borsai import registry as reg          # noqa: E402

_, cohort = reg.read_cohort()
sealed = sorted(r["ticker"] for r in reg.cohort_members(cohort) if r["vault"] == reg.VAULT_SEALED)
n_sealed = len(sealed)
pat_sealed = re.compile(r"\b(" + "|".join(sealed) + r")\b")
pat_bul = re.compile(r"th[bm]\s*[_-]?\s*20\d{6}", re.IGNORECASE)
pat_bul2 = re.compile(r"\bth[bm]\b.{0,40}?\b20\d{6}\b", re.IGNORECASE)
paths = [*sorted(p for p in (ROOT / "docs" / "faz8").rglob("*") if p.is_file()),
         *sorted(p for p in (ROOT / "docs" / "specs_faz8").rglob("*") if p.is_file()),
         ROOT / "borsai" / "post_break.py", ROOT / "borsai" / "predict_break.py", ROOT / "borsai" / "report_faz8.py",
         *sorted((ROOT / "tests").glob("test_faz8_*.py")), ROOT / "tests" / "faz8_support.py",
         ROOT / "docs" / "prompts" / "FAZ8_BREAK_IMPL.md", ROOT / "docs" / "prompts" / "FAZ8_FABLE_REPRO_AUDIT.md",
         *sorted(p for p in (ROOT / "docs" / "fable_faz8_audit").rglob("*") if p.is_file())]
print(f"SEALED kod sayısı (bellekte): {n_sealed}; taranan dosya: {len(paths)}")
total_sealed, total_bul, hits = 0, 0, []
for p in paths:
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = p.read_bytes().decode("utf-8", "replace")
    ns = len(set(pat_sealed.findall(text)))
    nb = len(pat_bul.findall(text)) + len(pat_bul2.findall(text))
    total_sealed += ns
    total_bul += nb
    if ns or nb:
        hits.append((p.relative_to(ROOT).as_posix(), ns, nb))
# MODELS.md Faz 8 bölümü ve günlük Faz 8 satırları
md = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8").split("## Faz 8")[1].split("## Faz 7C")[0]
ns_md, nb_md = len(set(pat_sealed.findall(md))), len(pat_bul.findall(md)) + len(pat_bul2.findall(md))
log8 = [l for l in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines() if "break_floor_v0" in l]
ns_log = len({m for l in log8 for m in pat_sealed.findall(l)})
nb_log = sum(len(pat_bul.findall(l)) + len(pat_bul2.findall(l)) for l in log8)
print(f"dosyalarda SEALED kod (ayrı kod sayısı toplamı): {total_sealed}; bülten adı kalıbı: {total_bul}")
print(f"MODELS.md Faz 8 bölümü: SEALED {ns_md}, bülten kalıbı {nb_md}; log.jsonl Faz 8 satırları ({len(log8)}): SEALED {ns_log}, bülten kalıbı {nb_log}")
print("isabetler (dosya, sealed, bülten): " + (str(hits) if hits else "yok"))
print("SONUÇ: " + ("TEMİZ" if not hits and ns_md == nb_md == ns_log == nb_log == 0 else "İSABET VAR"))

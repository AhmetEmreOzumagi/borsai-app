"""Eski (git rev) ve yeni (çalışma ağacı) skor dosyalarının farkı: hangi JSON yolları değişti (yalnız yol ve sayı basar).
Kullanım: .venv/bin/python docs/faz7_oot/ekler/skor_farki.py <repo> <rev>  (BORSAI_FAZ7_OOT_RECORDS)"""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

root, rev = Path(sys.argv[1]), sys.argv[2]


def show(path):
    return json.loads(subprocess.run(["git", "-C", str(root), "show", f"{rev}:{path}"], check=True, capture_output=True).stdout)


def walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append((path + (k,), "EKLENDİ"))
            elif k not in b:
                out.append((path + (k,), "SİLİNDİ"))
            else:
                walk(a[k], b[k], path + (k,), out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, f"liste uzunluğu {len(a)} -> {len(b)}"))
            return
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, path + (i,), out)
    elif a != b:
        out.append((path, "DEĞİŞTİ"))


for rel in ("scores/scores.json", "scores/scores_post_d1.json"):
    old = show(rel)
    new = json.loads((root / rel).read_text(encoding="utf-8"))
    print("==", rel)
    top = []
    old_m = {m["model_id"]: m for m in old["models"]}
    new_m = {m["model_id"]: m for m in new["models"]}
    for k in sorted(set(old) | set(new)):
        if k == "models":
            continue
        if k == "retro_info" and k in old:
            o_ids = [(x["model_id"], x["ticker"]) for x in old[k]]
            n_ids = [(x["model_id"], x["ticker"]) for x in new[k]]
            kept = [x for x in new[k] if (x["model_id"], x["ticker"]) in set(o_ids)]
            strip = lambda xs: [{**x, "class_evidence": {kk: vv for kk, vv in x["class_evidence"].items()  # noqa: E731
                                                         if kk not in ("outcome_ingest_commit", "checked_against",
                                                                       "outcome_ingest_basis")}} for x in xs]
            print(f"  retro_info: {len(o_ids)} -> {len(n_ids)}; eski çiftler aynı (sınıf kanıtı üretim alanları dışında): "
                  f"{strip(kept) == strip(old[k])}; yeni çiftlerin modelleri: "
                  f"{dict(Counter(x[0] for x in n_ids if x not in set(o_ids)))}")
            continue
        d = []
        walk(old.get(k), new.get(k), (k,), d) if k in old and k in new else d.append(((k,), "EKLENDİ" if k in new else "SİLİNDİ"))
        for p, what in d:
            top.append(("/".join(map(str, p)), what))
    for p, what in top:
        print("  üst:", p, what)
    changed = Counter()
    for mid, om in old_m.items():
        d = []
        walk(om, new_m[mid], (), d)
        keys = sorted({"/".join(str(x) for x in p if not isinstance(x, int)) + f" [{what}]" for p, what in d})
        for kk in keys:
            changed[kk] += 1
    print(f"  eski {len(old_m)} modelin değişen yolları (yol -> model sayısı):")
    for kk, n in sorted(changed.items()):
        print(f"    {kk}: {n}")
    print(f"  yeni modeller: {[m for m in new_m if m not in old_m]}")

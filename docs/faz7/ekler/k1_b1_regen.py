"""BORSAI_FAZ7_FREEZE_20260927, K1 (Fable denetimi B1): `hazard.TrainingResult.predict`'te `clipped` = herhangi bir sütun
(SPEC_HAZARD_V1 §3.1) düzeltmesinden sonra Faz 7 altın ledger'larının yeniden üretimi.

Sıra: (1) nihai fit önizlemeleri `final_fit_v1` ile yeniden kurulur ve eski dosyalarla (`created_at`, `code_version`, `runtime`
dışında) `==` olmalı — değilse DUR (B1 onlara dokunmaz; dosyalar değişmez). (2) Dört koşu resmi günlüğe (`experiments/log.jsonl`,
yalnız ekleme) `context = faz7_golden_b1` ile yazılır (kural 4). (3) Her ledger eskisiyle sütun sütun karşılaştırılır: `test_clipped`
dışındaki her sütun metin olarak aynı olmalı, @INF ve havuz KM ledger'ları bayt-eşit — değilse DUR (hiçbir altın dosya yazılmaz).
(4) Yeni `test_clipped` ve `test_clipped_features` Fable'ın bağımsız ledger'larıyla (`docs/fable_faz7_audit/ekler/repro_ledgers/`)
karşılaştırılır. (5) Altın dizin: ledger'lar, MANIFEST.json ve SHA256SUMS yenilenir; önizleme dosyaları bayt olarak aynen kalır.

Kullanım: PYTHONPATH=. .venv/bin/python docs/faz7/ekler/k1_b1_regen.py  (çıktı: docs/faz7/ekler/k1_b1_regen.txt)
"""
from __future__ import annotations

import csv
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from borsai import backtest as bt  # noqa: E402
from borsai.provenance import pretty_json_bytes, sha256_bytes  # noqa: E402
from borsai.specs import FAZ7_MODEL_IDS  # noqa: E402

CONTEXT = "faz7_golden_b1"
VOLATILE = ("created_at", "code_version", "runtime")
GOLDEN = bt.GOLDEN_FAZ7_DIR
REPRO = ROOT / "docs" / "fable_faz7_audit" / "ekler" / "repro_ledgers"
REPRO_NAME = {"ceiling_hazard_v1_clip": "ceiling_hazard_v1_clip_repro.csv", "ceiling_hazard_v1_real": "ceiling_hazard_v1_real_repro.csv",
              "ceiling_hazard_v1_pooled": "ceiling_hazard_v1_pooled_repro.csv",
              "ceiling_hazard_v1_pooled@INF": "ceiling_hazard_v1_pooled_at_INF_repro.csv"}
OUT = ROOT / "docs" / "faz7" / "ekler" / "k1_b1_regen.txt"


def rows_of(payload: bytes) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8"), newline=""))
    return list(reader.fieldnames or []), list(reader)


def strip(d):
    return {k: v for k, v in json.loads(pretty_json_bytes(dict(d))).items() if k not in VOLATILE}


def main() -> int:
    lines: list[str] = []
    say = lines.append
    manifest_old = json.loads((GOLDEN / "MANIFEST.json").read_text(encoding="utf-8"))
    old_bytes = {p.name: p.read_bytes() for p in GOLDEN.iterdir() if p.is_file()}
    previews = {m: json.loads(old_bytes[bt.final_preview_filename(m)]) for m in FAZ7_MODEL_IDS}

    say("# K1 · B1 altın ledger yeniden üretimi (BORSAI_FAZ7_FREEZE_20260927)")
    say("")
    say("## 1. Nihai fit önizlemeleri (B1 dokunmaz; created_at, code_version, runtime dışında ==)")
    for m in FAZ7_MODEL_IDS:
        fresh, _ = bt.final_fit_v1(m)
        same = strip(fresh) == strip(previews[m])
        say(f"- {m}: {'AYNI' if same else 'FARKLI'}")
        if not same:
            OUT.write_text("\n".join(lines) + "\nDUR: önizleme değişti\n", encoding="utf-8")
            return 2

    results = bt.run_faz7(log_path=ROOT / "experiments" / "log.jsonl", context=CONTEXT)
    say("")
    say(f"## 2. Koşular (resmi günlük, context = {CONTEXT})")
    for m, r in results.items():
        e = r.log_entry
        say(f"- {m}: started_at {e['started_at']}, ledger_sha256 {e['ledger_sha256']}, git_commit {e['git_commit'][:7]}, "
            f"borsai_dirty {e['borsai_dirty']}, borsai_source_sha256 {e['borsai_source_sha256']}")

    say("")
    say("## 3. Sütun sütun karşılaştırma (eski altın ↔ yeni koşu)")
    stop = False
    new_payloads: dict[str, bytes] = {}
    for m, r in results.items():
        new_payloads[bt.golden_filename(m)] = r.ledger_csv
        for key, (_, payload) in r.comparators.items():
            new_payloads[bt.golden_filename(key)] = payload
    for name, payload in new_payloads.items():
        old = old_bytes[name]
        if payload == old:
            say(f"- {name}: bayt-eşit (sha256 {sha256_bytes(payload)})")
            continue
        h_old, r_old = rows_of(old)
        h_new, r_new = rows_of(payload)
        if h_old != h_new or len(r_old) != len(r_new):
            say(f"- {name}: BAŞLIK YA DA SATIR SAYISI FARKLI")
            stop = True
            continue
        changed_cols = sorted({c for a, b in zip(r_old, r_new) for c in h_old if a[c] != b[c]})
        n_changed = {c: sum(1 for a, b in zip(r_old, r_new) if a[c] != b[c]) for c in changed_cols}
        flips = sorted({(a["test_clipped"], b["test_clipped"]) for a, b in zip(r_old, r_new) if a["test_clipped"] != b["test_clipped"]})
        say(f"- {name}: {len(h_old)} sütun × {len(r_old)} satır; değişen sütunlar {changed_cols} (satır {n_changed}); "
            f"geçişler {flips}; eski sha256 {sha256_bytes(old)} → yeni {sha256_bytes(payload)}")
        if changed_cols != ["test_clipped"] or flips != [("FALSE", "TRUE")]:
            stop = True
    if stop:
        say("DUR: test_clipped dışında fark var; altın dosyalar yazılmadı")
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return 3

    say("")
    say("## 4. Sayımlar ve Fable'ın bağımsız ledger'larıyla karşılaştırma (docs/fable_faz7_audit/ekler/repro_ledgers/)")
    for m in FAZ7_MODEL_IDS:
        _, rows = rows_of(results[m].ledger_csv)
        _, rep = rows_of((REPRO / REPRO_NAME[m]).read_bytes())
        by = {x["ticker"]: x for x in rep}
        any_n = sum(1 for x in rows if x["test_clipped"] == "TRUE")
        f3_n = sum(1 for x in rows if x["test_clipped_features"] and "f3" in json.loads(x["test_clipped_features"]))
        agree_any = sum(1 for x in rows if (x["test_clipped"] == "TRUE") == (by[x["ticker"]]["test_clipped_any"] == "True"))
        agree_feat = sum(1 for x in rows if json.loads(x["test_clipped_features"] or "[]") == json.loads(by[x["ticker"]]["test_clipped_features"] or "[]"))
        say(f"- {m}: fold {len(rows)}; test arzı kırpılan (herhangi bir sütun) {any_n}; f3 kırpılan {f3_n}; Fable ile test_clipped "
            f"{agree_any}/{len(rows)}, test_clipped_features {agree_feat}/{len(rows)}")

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "g"
        manifest = bt.write_golden_faz7(results, previews, out)
        for m in FAZ7_MODEL_IDS:
            name = bt.final_preview_filename(m)
            if (out / name).read_bytes() != old_bytes[name]:
                say(f"DUR: {name} yeniden yazımda bayt-eşit değil")
                OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return 4
        for p in out.iterdir():
            shutil.copyfile(p, GOLDEN / p.name)
    say("")
    say("## 5. Altın dizin (tests/reference/macos_golden_faz7/)")
    for name in sorted(p.name for p in GOLDEN.iterdir()):
        now = (GOLDEN / name).read_bytes()
        tag = "aynı" if now == old_bytes.get(name) else "YENİ"
        say(f"- {name}: {tag}, sha256 {sha256_bytes(now)}")
    say(f"- MANIFEST: git_commit {manifest['git_commit']}, borsai_dirty {manifest['borsai_dirty']}, borsai_source_sha256 "
        f"{manifest['borsai_source_sha256']} (eski: {manifest_old['git_commit'][:7]}, {manifest_old['borsai_dirty']})")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

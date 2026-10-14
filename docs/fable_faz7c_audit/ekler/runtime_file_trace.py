#!/usr/bin/env python3
"""Çalışma zamanı dosya izi (Faz 7C denetimi, madde 2-v; Faz 7 `runtime_file_trace.py` kalıbı).

Opus'un kodu `backtest.run_backtest_fall` (dört koşu, workers=1, geçici günlük, h99 ledger'ı havuz koşusuna verilir) ve
`backtest.final_fit_fall` (dört önizleme) çalışırken açılan HER dosya kaydedilir; sarmalar `borsai` import edilmeden ÖNCE kurulur.
Bu betik Opus'un kodunu ÇALIŞTIRIR (denetim); yeniden üretimin parçası değildir. Çıktı yalnız yol listeleri ve sayılar; kasa (SEALED)
kodu basılmaz: sonuç dosyası okumaları açık küme / kasa diye yalnız sayılır (kasa kümesi bellekte, kayıtlardan).
Kullanım: .venv/bin/python docs/fable_faz7c_audit/ekler/runtime_file_trace.py [çıktı dizini]"""
import builtins, io, os, sys, json, glob, time, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
OPENED: list[tuple[str, str]] = []


def _rec(path, mode):
    try:
        p = os.fspath(path)
    except TypeError:
        return
    if isinstance(p, bytes):
        p = p.decode("utf-8", "replace")
    OPENED.append((str(p), str(mode)))


_b_open, _io_open, _os_open = builtins.open, io.open, os.open


def b_open(file, mode="r", *a, **k):
    _rec(file, mode)
    return _b_open(file, mode, *a, **k)


def io_open(file, mode="r", *a, **k):
    _rec(file, mode)
    return _io_open(file, mode, *a, **k)


def os_open(path, flags, *a, **k):
    _rec(path, f"os.open flags={flags}")
    return _os_open(path, flags, *a, **k)


builtins.open = b_open
io.open = io_open
os.open = os_open

SEALED, OPEN = set(), set()
for p in glob.glob(str(ROOT / "registry" / "oot" / "records" / "*" / "*.json")):
    with _b_open(p, encoding="utf-8") as fh:
        r = json.load(fh)
    (SEALED if r.get("vault") == "SEALED" else OPEN).add(r["ticker"])
OPENED.clear()

sys.path.insert(0, str(ROOT))
t0 = time.time()
from borsai import backtest as bt                 # noqa: E402
from borsai.specs import FAZ7C_MODEL_IDS          # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="faz7c_trace_"))
log_path = tmp / "log.jsonl"
n_import = len(OPENED)
results = {}
datasets = {}
for mid in FAZ7C_MODEL_IDS:
    key = "h99" if mid == "fall_d10_v0_h99" else "v2"
    if key not in datasets:
        datasets[key] = bt.fall_dataset(mid)
    h99 = results["fall_d10_v0_h99"].ledger if mid == "fall_d10_v0_pooled" else None
    results[mid] = bt.run_backtest_fall(mid, log_path=log_path, context="fable_faz7c_trace", workers=1, dataset=datasets[key], h99_ledger=h99)
previews = {mid: bt.final_fit_fall(mid, dataset=datasets["h99" if mid == "fall_d10_v0_h99" else "v2"])[0] for mid in FAZ7C_MODEL_IDS}
elapsed = time.time() - t0

paths = {}
for p, m in OPENED:
    try:
        rp = os.path.relpath(p, ROOT)
    except ValueError:
        rp = p
    if rp.startswith(".."):
        continue                      # depo dışı (site-packages, /tmp günlük)
    paths.setdefault(rp, set()).add(m)
cats = {"data_outcomes_h99_live": 0, "data_outcomes_oot_open": 0, "data_outcomes_oot_sealed": 0, "scores": 0, "registry_records_open": 0,
        "registry_records_sealed": 0, "registry_inputs_open": 0, "registry_inputs_sealed": 0, "other": []}
for rp in sorted(paths):
    parts = rp.split("/")
    stem = Path(rp).stem
    if rp.startswith("data/outcomes/"):
        cats["data_outcomes_h99_live"] += 1
    elif rp.startswith("data/outcomes_oot/"):
        if stem in SEALED:
            cats["data_outcomes_oot_sealed"] += 1
        else:
            cats["data_outcomes_oot_open"] += 1
    elif rp.startswith("scores/"):
        cats["scores"] += 1
    elif rp.startswith("registry/oot/records/"):
        cats["registry_records_sealed" if stem.split("_")[0] in SEALED else "registry_records_open"] += 1
    elif rp.startswith("registry/oot/inputs/"):
        cats["registry_inputs_sealed" if stem in SEALED else "registry_inputs_open"] += 1
    else:
        cats["other"].append(rp)
# sonuç dosyası (outcomes_oot) sayısı açık kümeyle aynı mı
out = {"elapsed_s": round(elapsed, 1), "files_opened_total": len(paths), "opened_during_import": n_import, "categories": cats,
       "ledger_sha256": {m: bt.sha256_bytes(r.ledger_csv) for m, r in results.items()},
       "golden_sha256": {m: json.load(_b_open(ROOT / "tests" / "reference" / "macos_golden_faz7c" / "MANIFEST.json"))["runs"][m]["ledger_sha256"] for m in results},
       "near_era": results["fall_d10_v0_pooled"].log_entry["near_era"]}
out["ledgers_byte_equal_to_golden"] = out["ledger_sha256"] == out["golden_sha256"]
(OUT_DIR / "runtime_file_trace_out.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
lines = [f"[iz] süre {out['elapsed_s']} sn; depo içi açılan dosya {out['files_opened_total']} (import sırasında {n_import} kayıt)",
         f"[iz] data/outcomes/ (H99+canlı ham sonuçlar): {cats['data_outcomes_h99_live']}",
         f"[iz] data/outcomes_oot/ açık: {cats['data_outcomes_oot_open']} (beklenen 71), kasa: {cats['data_outcomes_oot_sealed']} (beklenen 0)",
         f"[iz] scores/: {cats['scores']} (beklenen 0)",
         f"[iz] registry/oot/records/ açık: {cats['registry_records_open']}, kasa: {cats['registry_records_sealed']}; registry/oot/inputs/ açık: {cats['registry_inputs_open']}, kasa: {cats['registry_inputs_sealed']}",
         f"[iz] ledger'lar altınla bayt-eşit: {out['ledgers_byte_equal_to_golden']}",
         "[iz] öteki yollar:"] + [f"    {p}  ({', '.join(sorted(paths[p]))})" for p in cats["other"]]
(OUT_DIR / "runtime_file_trace_out.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))

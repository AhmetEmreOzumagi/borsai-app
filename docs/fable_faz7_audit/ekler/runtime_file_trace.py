#!/usr/bin/env python3
"""Çalışma zamanı dosya izi (Faz 7 denetimi, madde 2-vi; Faz 4/5 `runtime_file_trace.py` kalıbı).

Opus'un kodu `backtest.run_backtest_v1` (dört koşu, workers=1, geçici günlük) ve `backtest.final_fit_v1` (pooled) çalışırken
açılan HER dosya kaydedilir; sarmalar `borsai` import edilmeden ÖNCE kurulur. Bu betik Opus'un kodunu ÇALIŞTIRIR (denetim);
yeniden üretimin parçası değildir. Çıktı yalnız yol listeleri ve sayılar; kasa (SEALED) kodu basılmaz: sonuç dosyası okumaları
açık küme / kasa diye yalnız sayılır (kasa kümesi bellekte, kayıtlardan).
Kullanım: .venv/bin/python docs/fable_faz7_audit/ekler/runtime_file_trace.py [çıktı dizini]"""
import builtins, io, os, sys, json, hashlib, time, csv, glob
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

# kasa kümesi (bellekte; yalnız sayı basılır) — kayıtlardan
SEALED = set()
OPEN = set()
for p in glob.glob(str(ROOT / "registry" / "oot" / "records" / "*" / "*.json")):
    with _b_open(p, encoding="utf-8") as fh:
        r = json.load(fh)
    (SEALED if r.get("vault") == "SEALED" else OPEN).add(r["ticker"])
OPENED.clear()

sys.path.insert(0, str(ROOT))
t0 = time.time()
from borsai import backtest as bt                 # noqa: E402
from borsai.specs import FAZ7_MODEL_IDS            # noqa: E402

CLIP, REAL, POOLED, POOLED_INF = FAZ7_MODEL_IDS
TMPLOG = Path("/tmp/borsai_faz7_audit/trace_log.jsonl")
TMPLOG.parent.mkdir(parents=True, exist_ok=True)
if TMPLOG.exists():
    TMPLOG.unlink()
marks = {"import": len(OPENED)}
datasets = {"h99": bt.v1_dataset(CLIP), "v2": bt.v1_dataset(POOLED)}
marks["datasets"] = len(OPENED)
results = {}
for m in FAZ7_MODEL_IDS:
    results[m] = bt.run_backtest_v1(m, log_path=TMPLOG, context="fable_trace", workers=1,
                                    dataset=datasets["v2" if "pooled" in m else "h99"])
    marks[m] = len(OPENED)
preview, _ = bt.final_fit_v1(POOLED, datasets["v2"])
marks["final_fit_pooled"] = len(OPENED)
GOLD = ROOT / "tests" / "reference" / "macos_golden_faz7"
same = {m: results[m].ledger_csv == (GOLD / bt.golden_filename(m)).read_bytes() for m in FAZ7_MODEL_IDS}
print(f"[iz] in-process (workers=1) ledger'lar bayt-eşit altın: {same}; {time.time() - t0:.0f} s")


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except Exception:
        return p


def classify(paths):
    """Sonuç dosyası okumalarını sınıfla; kod adı basılmaz."""
    oot_open = oot_sealed = 0
    for p in paths:
        if p.startswith("data/outcomes_oot/"):
            code = Path(p).stem
            if code in SEALED:
                oot_sealed += 1
            elif code in OPEN:
                oot_open += 1
    return oot_open, oot_sealed


def summarize(seg, name):
    reads = sorted({rel(p) for p, mode in seg if not any(x in mode for x in ("w", "a", "x", "+")) and "os.open" not in mode})
    writes = sorted({rel(p) for p, mode in seg if any(x in mode for x in ("w", "a", "x", "+")) or "os.open" in mode})
    reads_repo = [p for p in reads if not p.startswith("/")]
    print(f"== {name}: okunan repo dosyası {len(reads_repo)}, repo dışı okuma {len(reads) - len(reads_repo)}, yazma {len(writes)}")
    for p in reads_repo:
        if p.startswith("data/outcomes_oot/") or p.startswith("registry/oot/inputs/"):
            continue                                  # üye dosyaları tek tek basılmaz (aşağıda sayılır)
        print("  R", p)
    n_inputs = sum(1 for p in reads_repo if p.startswith("registry/oot/inputs/"))
    n_inputs_sealed = sum(1 for p in reads_repo if p.startswith("registry/oot/inputs/") and Path(p).stem in SEALED)
    oo, os_ = classify(reads_repo)
    print(f"  data/outcomes_oot/ okunan: açık {oo}, kasa {os_}; registry/oot/inputs/ okunan: {n_inputs} (kasa: {n_inputs_sealed})")
    for p in writes:
        print("  W", p)
    forbidden = [p for p in reads_repo if p.startswith(("data/outcomes/", "data/raw/bist", "scores/", "docs/SCORES", "registry/ipos",
                                                        "registry/records", "registry/legacy_frozen"))]
    print(f"  YASAK dizinden okuma (canlı sonuç / skor / canlı kayıt): {forbidden if forbidden else 'YOK'}; kasa sonuç dosyası: {os_}")
    return reads_repo, writes, forbidden, {"outcomes_oot_open": oo, "outcomes_oot_sealed": os_, "inputs": n_inputs,
                                           "inputs_sealed": n_inputs_sealed}


out = {}
prev = 0
for name in ("import", "datasets", *FAZ7_MODEL_IDS, "final_fit_pooled"):
    out[name] = summarize(OPENED[prev:marks[name]], name)
    prev = marks[name]
allf = [p for seg in out.values() for p in seg[2]]
sealed_reads = sum(seg[3]["outcomes_oot_sealed"] + seg[3]["inputs_sealed"] for seg in out.values())
print("TOPLAM YASAK OKUMA:", len(allf), "; KASA ÜYESİ DOSYASI OKUMA:", sealed_reads)
bad_writes = [rel(p) for p, mode in OPENED if (any(x in mode for x in ("w", "a", "x", "+")) or "os.open" in mode)
              and rel(p).startswith(("experiments/", "models/", "tests/", "data/", "docs/", "registry/", "scores/", "app/"))]
print("REPOYA YAZMA:", bad_writes if bad_writes else "YOK")
res = {"ledger_byte_equal_golden": same, "reads": {k: v[0] for k, v in out.items()}, "writes": {k: v[1] for k, v in out.items()},
       "forbidden": allf, "member_file_counts": {k: v[3] for k, v in out.items()}, "sealed_member_file_reads": sealed_reads,
       "repo_writes": bad_writes, "seconds": round(time.time() - t0)}
(OUT_DIR / "runtime_file_trace_out.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

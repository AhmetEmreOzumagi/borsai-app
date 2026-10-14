#!/usr/bin/env python3
"""Çalışma zamanı sızıntı kanıtı: Faz 4 backtest (üç koşu) ve nihai-dondurma parametre üretimi (fit_params)
çalışırken açılan HER dosyanın listesi. `builtins.open`, `io.open` ve `os.open` borsai import edilmeden ÖNCE
sarılır. Günlük, pytest'teki gibi geçici bir dizine yazılır (experiments/log.jsonl'a dokunulmaz).
Bu betik Opus'un kodunu ÇALIŞTIRIR (denetim); yeniden üretimin parçası değildir."""
import builtins, io, os, sys, json, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
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

sys.path.insert(0, str(ROOT))
tmp = Path(tempfile.mkdtemp(prefix="borsai_trace_"))
log = tmp / "log.jsonl"

from borsai import backtest as bt          # noqa: E402
from borsai import ceiling_path as cp      # noqa: E402
from borsai.data import load_dataset       # noqa: E402
from borsai.specs import FAZ4_MODEL_IDS, MODEL_SPECS  # noqa: E402
from borsai.fit import fit                 # noqa: E402

ds = load_dataset()
mark_bt = len(OPENED)
for m in FAZ4_MODEL_IDS:
    bt.run_backtest(m, ds, log_path=log, context="fable_audit_trace")
mark_fit = len(OPENED)
for m in FAZ4_MODEL_IDS:
    fit(MODEL_SPECS[m], list(ds.rows), dataset_version=ds.data_version_sha256)
mark_end = len(OPENED)


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except Exception:
        return p


def summarize(seg, name):
    reads = sorted({rel(p) for p, mode in seg if not any(x in mode for x in ("w", "a", "x", "+")) and "os.open" not in mode})
    writes = sorted({rel(p) for p, mode in seg if any(x in mode for x in ("w", "a", "x", "+")) or "os.open" in mode})
    reads_repo = [p for p in reads if not p.startswith("/")]
    print(f"== {name}: okunan repo dosyası {len(reads_repo)}, repo dışı okuma {len(reads) - len(reads_repo)}, yazma {len(writes)}")
    for p in reads_repo:
        print("  R", p)
    for p in writes:
        print("  W", p)
    forbidden = [p for p in reads_repo if p.startswith(("data/outcomes", "data/raw/bist", "scores")) or p.startswith("docs/SCORES")]
    print(f"  YASAK dizinden okuma: {forbidden if forbidden else 'YOK'}")
    return reads_repo, writes, forbidden


out = {}
out["import+load_dataset"] = summarize(OPENED[:mark_bt], "import + load_dataset")
out["backtest_faz4"] = summarize(OPENED[mark_bt:mark_fit], "backtest (3 koşu)")
out["fit_params_faz4"] = summarize(OPENED[mark_fit:mark_end], "fit_params (3 model, nihai dondurma parametreleri; repoya yazılmadı)")
allf = [p for seg in out.values() for p in seg[2]]
print("TOPLAM YASAK OKUMA:", len(allf))
print("geçici günlük satırı:", len(log.read_text().splitlines()) if log.exists() else 0, "->", tmp)
assert not any(rel(p).startswith("experiments/") for p, mode in OPENED if any(x in mode for x in ("w", "a", "+"))), "experiments/ yazıldı!"
assert not any(rel(p).startswith(("models/", "tests/", "data/", "docs/", "registry/", "scores/")) for p, mode in OPENED if any(x in mode for x in ("w", "a", "x", "+"))), "repoya yazıldı!"

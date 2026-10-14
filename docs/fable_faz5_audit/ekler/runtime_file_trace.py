#!/usr/bin/env python3
"""Çalışma zamanı sızıntı kanıtı (Faz 5): Opus'un kodu `post_d1.backtest_ledger` (workers=1, günlüğe yazmaz) ve
`post_d1.fit_params` (nihai fit önizlemesi; dosyaya yazmaz) çalışırken (1) açılan HER dosya, (2) SESSIONS dosyasından
seans numarasına göre erişilen HER sütun (erişen borsai fonksiyonuyla) kaydedilir. Sarmalar `borsai` import edilmeden
ÖNCE kurulur. Bu betik Opus'un kodunu ÇALIŞTIRIR (denetim); yeniden üretimin parçası değildir.
Kullanım: .venv/bin/python docs/fable_faz5_audit/ekler/runtime_file_trace.py [çıktı dizini]"""
import builtins, csv, io, os, sys, json, hashlib, time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
OPENED: list[tuple[str, str]] = []
COLS: dict[tuple[str, str, str], int] = defaultdict(int)     # (dosya, seans kovası, borsai fonksiyonu) -> erişim sayısı


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


def _caller():
    f = sys._getframe(2)
    while f is not None:
        fn = f.f_code.co_filename
        if "/borsai/" in fn and not fn.endswith("__init__.py"):
            return f"{Path(fn).stem}:{f.f_code.co_name}"
        f = f.f_back
    return "?"


class Tracking(dict):
    __slots__ = ("_src",)

    def __init__(self, d, src):
        super().__init__(d)
        self._src = src

    def _bucket(self):
        sn = dict.get(self, "session_number")
        return "D1" if sn == "1" else ("D2..10" if sn is not None else "-")

    def __getitem__(self, k):
        COLS[(self._src, self._bucket(), _caller())] += 0
        COLS[(self._src, self._bucket(), _caller() + "|" + str(k))] += 1
        return dict.__getitem__(self, k)

    def get(self, k, default=None):
        return self[k] if k in self else default

    def items(self):
        COLS[(self._src, self._bucket(), _caller() + "|<items()>")] += 1
        return dict.items(self)


_real_reader = csv.DictReader


class Reader(_real_reader):
    def __init__(self, f, *a, **k):
        super().__init__(f, *a, **k)
        name = getattr(f, "name", None)
        self._src = Path(name).name if isinstance(name, str) else type(f).__name__

    def __next__(self):
        return Tracking(super().__next__(), self._src)


csv.DictReader = Reader

sys.path.insert(0, str(ROOT))
t0 = time.time()
from borsai import post_d1 as pd          # noqa: E402
from borsai import backtest as bt         # noqa: E402
from borsai.data import load_dataset      # noqa: E402

ds = load_dataset()
mark_bt = len(OPENED)
cols_before = dict(COLS)
ledger, info = pd.backtest_ledger(ds, workers=1)
mark_fit = len(OPENED)
preview = pd.fit_params(ds)
mark_end = len(OPENED)
payload = bt.ledger_csv_bytes(ledger)
golden = (ROOT / "tests" / "reference" / "macos_golden_faz5" / "post_d1_hazard_v0_fold_ledger.csv").read_bytes()
print(f"[iz] in-process (workers=1) ledger bayt-eşit altın: {payload == golden}; sha256 {hashlib.sha256(payload).hexdigest()[:12]}; "
      f"nihai λ {preview['lambda']} δ {preview['delta']}; {time.time() - t0:.0f} s")


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
    forbidden = [p for p in reads_repo if p.startswith(("data/outcomes", "data/raw/bist", "scores", "docs/SCORES"))]
    print(f"  YASAK dizinden okuma: {forbidden if forbidden else 'YOK'}")
    return reads_repo, writes, forbidden


out = {}
out["import+load_dataset"] = summarize(OPENED[:mark_bt], "import + load_dataset")
out["backtest_ledger"] = summarize(OPENED[mark_bt:mark_fit], "backtest_ledger (87 fold, workers=1; günlüğe yazmaz)")
out["fit_params"] = summarize(OPENED[mark_fit:mark_end], "fit_params (nihai fit önizlemesi; dosyaya yazmaz)")
allf = [p for seg in out.values() for p in seg[2]]
print("TOPLAM YASAK OKUMA:", len(allf))
assert not any(rel(p).startswith(("experiments/", "models/", "tests/", "data/", "docs/", "registry/", "scores/")) for p, mode in OPENED
               if any(x in mode for x in ("w", "a", "x", "+"))), "repoya yazıldı!"

# SESSIONS sütun erişimi: seans kovası × borsai fonksiyonu -> sütunlar
print("\n== SESSIONS sütun erişimi (dosya: *_canonical_bist_session_outcomes.csv), seans kovasına ve okuyan fonksiyona göre")
by = defaultdict(lambda: defaultdict(set))
for (src, bucket, key), n in COLS.items():
    if "session_outcomes" not in src or "|" not in key:
        continue
    fn, col = key.split("|", 1)
    by[bucket][fn].add(col)
for bucket in ("D1", "D2..10"):
    for fn, cols in sorted(by[bucket].items()):
        print(f"  [{bucket}] {fn}: {sorted(cols)}")
d1_loader_d2 = by["D2..10"].get("post_d1:load_d1_sessions", set())
print(f"\n  D1 yükleyicisinin (post_d1:load_d1_sessions) 2..10. seanslarda eriştiği sütunlar: {sorted(d1_loader_d2)}")
price_cols = {"open", "high", "low", "close", "volume", "turnover", "aof", "trade_count", "reference_price", "upper_limit", "lower_limit",
              "thb_raw_open", "thb_raw_high", "thb_raw_low", "thb_raw_close", "thb_raw_volume", "thb_raw_turnover", "thb_raw_aof",
              "thb_raw_trade_count", "thm_raw_reference_price", "thm_raw_upper_limit", "thm_raw_lower_limit"}
print(f"  D1 yükleyicisi 2..10. seanslarda fiyat/hacim sütunu okudu mu: {bool(d1_loader_d2 & price_cols)}")
others = {fn: sorted(c & price_cols) for fn, c in by["D2..10"].items() if fn != "post_d1:load_d1_sessions" and c & price_cols}
print(f"  2..10. seans fiyat sütunlarını okuyan DİĞER okuyucular: {others}")
# diğer CSV dosyaları
print("\n== Diğer CSV dosyaları ve okuyan fonksiyonlar")
files = defaultdict(set)
for (src, bucket, key), n in COLS.items():
    if "session_outcomes" in src or "|" not in key:
        continue
    files[src].add(key.split("|", 1)[0])
for src, fns in sorted(files.items()):
    print(f"  {src}: {sorted(fns)}")
res = {"ledger_byte_equal_golden": payload == golden, "final_lambda": preview["lambda"], "final_delta": preview["delta"],
       "reads": {k: v[0] for k, v in out.items()}, "writes": {k: v[1] for k, v in out.items()}, "forbidden": allf,
       "sessions_columns": {b: {fn: sorted(c) for fn, c in fns.items()} for b, fns in by.items()},
       "d1_loader_reads_price_cols_in_sessions_2_10": bool(d1_loader_d2 & price_cols), "other_readers_price_cols_2_10": others}
(OUT_DIR / "runtime_file_trace_out.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

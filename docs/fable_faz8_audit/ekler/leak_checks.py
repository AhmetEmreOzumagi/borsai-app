#!/usr/bin/env python3
"""Sızıntı ve kesim denetimleri OPUS'UN KODUYLA (BORSAI_FAZ8_FABLE_REPRO_AUDIT adım 3-i, 3-ii, 3-iii). Bu betik `borsai`'yi
ÇALIŞTIRIR (denetim); yeniden üretimin parçası değildir. Depoya hiçbir şey yazmaz (günlük geçici dizine). Çıktı: argv[1] dizini.
- (i)   test arzının alanları değiştirilince (override) kendi fold'unun fit'i (katsayı, sabit, ön işleme, iç skorlar, @ZERO, by_type,
        ürün) bit-eşit kalır; yalnız p (ve test_* sütunları) değişir — 3 fold; sonraki fold'ların (o arzı eğitimde görenler) fit'i değişir.
- (ii)  her fold: her eğitim satırının etiket seansı < T; cells_max_session_date < D_1(k); ledger'daki training_max_label_date ve
        cells_max_session_date sütunlarıyla tutarlı.
- (iii) yükleyici beyaz listesi çalışma zamanı izi (erişim sayan DictReader) + bütün koşu boyunca açılan dosyalar (builtins.open /
        io.open / os.open sarmalı; `borsai` import edilmeden önce kurulur): data/outcomes/, data/outcomes_oot/, scores/, registry/ sayıları."""
import builtins, io, os, sys, json, csv, time, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
OPENED: list[tuple[str, str]] = []
_b_open, _io_open, _os_open = builtins.open, io.open, os.open


def _rec(path, mode):
    try:
        p = os.fspath(path)
    except TypeError:
        return
    if isinstance(p, bytes):
        p = p.decode("utf-8", "replace")
    OPENED.append((str(p), str(mode)))


def b_open(file, mode="r", *a, **k):
    _rec(file, mode)
    return _b_open(file, mode, *a, **k)


def io_open(file, mode="r", *a, **k):
    _rec(file, mode)
    return _io_open(file, mode, *a, **k)


def os_open(path, flags, *a, **k):
    _rec(path, f"os.open flags={flags}")
    return _os_open(path, flags, *a, **k)


builtins.open, io.open, os.open = b_open, io_open, os_open

# erişim sayan DictReader (H20 kalıbı) — yalnız load_break_table sırasında
ACCESS: dict[tuple[str, int], set] = {}


class Tracking(dict):
    def __getitem__(self, k):
        key = (dict.__getitem__(self, "ticker"), int(dict.__getitem__(self, "session_number")))
        ACCESS.setdefault(key, set()).add(k)
        return dict.__getitem__(self, k)

    def get(self, k, default=None):
        return self[k] if k in self else default


_real_reader = csv.DictReader


class Reader(_real_reader):
    def __next__(self):
        return Tracking(super().__next__())


sys.path.insert(0, str(ROOT))
t0 = time.time()
from borsai import post_break as pbk          # noqa: E402
from borsai import predict_break as pb        # noqa: E402
from borsai.data import load_dataset          # noqa: E402

n_import = len(OPENED)
lines = []


def say(s):
    lines.append(s)
    print(s, flush=True)


dataset = load_dataset()
csv.DictReader = Reader
table = pbk.load_break_table(dataset)
csv.DictReader = _real_reader
after, at_b, streak, after_b2 = set(), set(), set(), set()
for u in table.units:
    for h in range(1, 11):
        keys = ACCESS[(u.ticker, h)]
        if u.b is None or h < u.b:
            streak |= keys
        elif h == u.b:
            at_b |= keys
        else:
            after |= keys
            if h >= u.b + 3:
                after_b2 |= keys
say(f"[iii-beyaz liste] D_b'den SONRAKİ satırlarda erişilen anahtarlar: {sorted(after)}")
say(f"[iii-beyaz liste] D_{{b+3}}..D_10 satırlarında: {sorted(after_b2)}")
say(f"[iii-beyaz liste] seri satırlarında (h < b): {sorted(streak)}")
say(f"[iii-beyaz liste] D_b satırında: {sorted(at_b)}")
ok_wl = after == {"ticker", "session_number", "target_session_date", "thb_raw_close", "thm_raw_lower_limit"}
say(f"[iii-beyaz liste] şartname kümesiyle aynı: {ok_wl}")

units = pbk._path_units(dataset)
values = pbk.break_values(table)
folds = pbk.plan_break_folds(table)
# (ii) kesimler
bad_lbl, bad_cells, n_rows, n_cells = 0, 0, 0, 0
cache = pbk.CellCache(units)
gold = {r["ticker"]: r for r in pbk.read_ledger(ROOT / "docs" / "faz8" / "backtest" / "break_floor_v0_fold_ledger.csv")}
bad_ledger = []
for f in folds:
    T = f.break_date
    for head in pbk.HEADS:
        for t in f.training[head]:
            y, d = pbk.label_of(table.labels[t], head)
            n_rows += 1
            if not (d < T):
                bad_lbl += 1
    _, info = cache.get(f.first_trading_date)
    n_cells += 1
    if info["max_session_date"] is not None and not info["max_session_date"] < f.first_trading_date:
        bad_cells += 1
    g = gold[f.ticker]
    mx = max((d for d in f.max_label_date.values() if d), default="")
    if g["training_max_label_date"] != mx or g["cells_max_session_date"] != (info["max_session_date"] or "") or not (mx == "" or mx < T):
        bad_ledger.append(f.ticker)
say(f"[ii-kesim] eğitim satırı (F1+F2, 82 fold): {n_rows}; etiket seansı ≥ T olan: {bad_lbl}; hücre max tarihi ≥ D_1(k) olan fold: {bad_cells}/{n_cells}; "
    f"ledger sütunlarıyla tutarsız fold: {bad_ledger}")
say(f"[ii-kesim] bütün etiket tarihleri ≤ 2026-08-19: {all(l.y1_date <= '2026-08-19' and (l.y2_date is None or l.y2_date <= '2026-08-19') for l in table.labels.values())}")

# (i) test arzı: override ile 3 fold
base, _ = pbk.backtest_ledger(table, units, workers=1, faz4_ref=None)
base_by = {r["ticker"]: r for r in base}
same_as_gold = all(pbk.ledger_csv_bytes(base) == (ROOT / "docs" / "faz8" / "backtest" / "break_floor_v0_fold_ledger.csv").read_bytes() for _ in [0])
say(f"[i] temel koşu (workers=1) resmi ledger'la bayt-eşit: {same_as_gold}")
FIT_COLS = ["training_n", "training_events", "training_tickers_sha256", "selected_C_F1", "selected_C_F2", "columns", "coef_floor_F1", "coef_turn_F1",
            "intercept_F1", "coef_floor_F2", "coef_turn_F2", "intercept_F2", "clip_p05", "clip_p95", "mean_floor", "std_floor", "mean_turn", "std_turn",
            "dropped", "zero_F1", "zero_F2", "product_F1", "product_F2", "product_status", "cells_max_session_date", "realized_F1", "realized_F2", "status"]
ok_folds = [r for r in base if r["status"] == "FIT_OK"]
picks = [ok_folds[0], ok_folds[len(ok_folds) // 2], ok_folds[-1]]
res_i = []
for r in picks:
    k = r["ticker"]
    v = values[k]
    override = {k: {"b_turnover": v.turnover_ln + 3.0, "b_floor": __import__("decimal").Decimal(1 - v.b_floor)}}
    mut, _ = pbk.backtest_ledger(table, units, workers=1, override=override, faz4_ref=None)
    m = {x["ticker"]: x for x in mut}[k]
    it_b, it_m = json.loads(r["inner_table_F1"]), json.loads(m["inner_table_F1"])
    same_fit = all(r[c] == m[c] for c in FIT_COLS) and it_b["scores"] == it_m["scores"] and it_b["prep"] == it_m["prep"] and it_b["coef"] == it_m["coef"]
    by_type_same = r["by_type_F1"] == m["by_type_F1"]
    later = [x["ticker"] for x in mut if k in {t for f in folds if f.ticker == x["ticker"] for t in f.training["F1"]} and x["status"] == "FIT_OK"]
    changed_later = sum(1 for t in later if base_by[t]["coef_floor_F1"] != {x["ticker"]: x for x in mut}[t]["coef_floor_F1"])
    res_i.append({"ticker": k, "fit_bit_equal": same_fit, "p_before": r["p_F1"], "p_after": m["p_F1"], "by_type_same": by_type_same,
                  "later_folds_with_k_in_training": len(later), "later_folds_changed": changed_later})
    say(f"[i] {k}: test arzı alanları değiştirildi → fit/ön işleme/iç skorlar/@ZERO/ürün bit-eşit {same_fit}; by_type aynı {by_type_same} "
        f"(sınıf değiştiyse farklı olur); p_F1 {float(r['p_F1']):.4f} → {float(m['p_F1']):.4f}; o arzı eğitimde gören sonraki FIT_OK fold {len(later)}, "
        f"katsayısı değişen {changed_later}")

# (iii) dosya izi: nihai fit + duyarlılık koşusu da dahil (geçici günlük)
tmp = Path(tempfile.mkdtemp(prefix="faz8_trace_"))
res = pbk.run_backtest(dataset, log_path=tmp / "log.jsonl", context="fable_faz8_trace", workers=1, table=table, path_units=units)
for n in pbk.FAZ8_SENSITIVITIES:
    pbk.run_sensitivity(n, dataset, log_path=tmp / "log.jsonl", context="fable_faz8_trace", ledger_file=f"s/{n}.csv", workers=1, table=table,
                        path_units=units, out_dir=tmp)
for m in pbk.FAZ8_MODEL_IDS:
    pbk.final_fit(m, dataset, table=table)
paths = {}
for p, mo in OPENED:
    try:
        rp = os.path.relpath(p, ROOT)
    except ValueError:
        rp = p
    if rp.startswith(".."):
        continue
    paths.setdefault(rp, set()).add(mo)
cats = {"data_outcomes_live": 0, "data_outcomes_oot": 0, "scores": 0, "registry": 0, "models": 0, "other": []}
for rp in sorted(paths):
    if rp.startswith("data/outcomes/"):
        cats["data_outcomes_live"] += 1
    elif rp.startswith("data/outcomes_oot/"):
        cats["data_outcomes_oot"] += 1
    elif rp.startswith("scores/"):
        cats["scores"] += 1
    elif rp.startswith("registry/"):
        cats["registry"] += 1
    elif rp.startswith("models/"):
        cats["models"] += 1
    else:
        cats["other"].append(rp)
say(f"[iii-dosya izi] depo içi açılan dosya {len(paths)} (import sırasında {n_import} kayıt); data/outcomes/ {cats['data_outcomes_live']}, "
    f"data/outcomes_oot/ {cats['data_outcomes_oot']}, scores/ {cats['scores']}, registry/ {cats['registry']}, models/ {cats['models']}")
for rp in cats["other"]:
    say(f"    {rp}  ({', '.join(sorted(paths[rp]))})")
say(f"[iii-dosya izi] koşu ledger'ı resmi ledger'la bayt-eşit: {res.log_entry['ledger_sha256'] == '730a4e3cc75d007cf66306294a0b9c0dcc58840d82968864ab87357ee170098e'}")
say(f"[süre] {time.time() - t0:.1f} sn")
out = {"whitelist_after_break": sorted(after), "whitelist_ok": ok_wl, "cutoffs": {"rows": n_rows, "bad_labels": bad_lbl, "bad_cells": bad_cells, "bad_ledger": bad_ledger},
       "override": res_i, "files": {k: v for k, v in cats.items()}, "files_opened": sorted(paths)}
(OUT_DIR / "leak_checks_out.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
(OUT_DIR / "leak_checks_out.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

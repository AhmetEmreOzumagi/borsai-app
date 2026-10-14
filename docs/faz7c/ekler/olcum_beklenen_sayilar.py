"""BORSAI_FAZ7_C_IMPL_20260927 — görev metnindeki "beklenen sayılar" tablosunun ölçümü (SPEC_C_V0 §11).

Yalnız okur; hiçbir dosya yazmaz (çıktı stdout). Arz kodu basmaz: çıktılar sayı, sha ve tarihtir. Kasa (SEALED) üyelerinin hiçbir
dosyası açılmaz; kasa kodları yalnız `registry.cohort_members` + bekçi fonksiyonu içinde, bellekte kullanılır. Commit A'da gerçek
veride walk-forward yoktur: altın dizin yoksa B satırları "henüz yok" yazar.

Kullanım: .venv/bin/python docs/faz7c/ekler/olcum_beklenen_sayilar.py
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from borsai import backtest as bt  # noqa: E402
from borsai import predict_fall as pf  # noqa: E402
from borsai import registry as reg  # noqa: E402
from borsai.data import additional_sale_shares, load_dataset, load_dataset_v2  # noqa: E402
from borsai.features import FeatureError  # noqa: E402
from borsai.provenance import sha256_bytes, sha256_file  # noqa: E402
from borsai.specs import (FAZ7_MODEL_SPECS, FAZ7C_EXPLORATION, FAZ7C_MODEL_IDS, FAZ7C_MODEL_SPECS, H99_DATA_VERSION_SHA256,  # noqa: E402
                          SPEC_DOCUMENTS_FAZ7C, V2_DATA_VERSION_SHA256)

H99, POOLED, ADDSALE, ZERO_ROW = FAZ7C_MODEL_IDS


def _code(value):
    try:
        return pf.additional_sale_flag(value)
    except FeatureError as exc:
        return exc.code


def main() -> None:
    p = print
    h, v = load_dataset(), load_dataset_v2()
    ah, av = additional_sale_shares(h), additional_sale_shares(v)

    p("## 1. Ek satış bayrağı")
    p(f"  '0' -> {_code('0')}; '35000000' -> {_code('35000000')}; '' -> {_code('')}; None -> {_code(None)}; "
      f"'DATA_NOT_FOUND' -> {_code('DATA_NOT_FOUND')}; '-1' -> {_code('-1')}")
    h99_flags = [pf.additional_sale_flag(x) for x in ah.values() if x is not None]
    open_flags = [pf.additional_sale_flag(av[r.ticker]) for r in v.rows if r.cohort == "OOT_OPEN" and av[r.ticker] is not None]
    p(f"  bayrak = 1: H99 {sum(h99_flags)} / {len(h99_flags)} dolu alan; açık küme {sum(open_flags)} / {len(open_flags)}")

    p("## 2. Eğitim kümeleri")
    for m in (H99, POOLED, ADDSALE):
        ds, a = (h, ah) if m == H99 else (v, av)
        rows = bt.fall_training_rows(FAZ7C_MODEL_SPECS[m], ds, a, check=True)
        coh = {c: sum(1 for r in rows if (getattr(r, "cohort", "H99") or "H99") == c) for c in ("H99", "OOT_OPEN")}
        p(f"  {FAZ7C_MODEL_SPECS[m]['training']['set']}: n {len(rows)}, D10 olay {sum(r.targets['D10'].Y == 0 for r in rows)}, "
          f"D5 olay {sum(r.targets['D5'].Y == 0 for r in rows)}, kohort {coh}")

    p("## 3. Tablolar ve kasa kodu")
    v1j = json.loads((ROOT / "data" / "data_version.json").read_text(encoding="utf-8"))
    v2j = json.loads((ROOT / "data" / "data_version_v2.json").read_text(encoding="utf-8"))
    p(f"  training_table.csv {sha256_file(ROOT / 'data' / 'training_table.csv')} (data_version.json: {v1j['sha256']})")
    p(f"  training_table_v2.csv {sha256_file(ROOT / 'data' / 'training_table_v2.csv')} (data_version_v2.json: {v2j['sha256']})")
    p(f"  data_version.json {sha256_file(ROOT / 'data' / 'data_version.json')} (spec {H99_DATA_VERSION_SHA256})")
    p(f"  data_version_v2.json {sha256_file(ROOT / 'data' / 'data_version_v2.json')} (spec {V2_DATA_VERSION_SHA256})")
    st = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", "data"], cwd=ROOT, check=True,
                        capture_output=True, text=True).stdout
    p(f"  data/ çalışma ağacı değişikliği: {len(st.splitlines())} satır")
    from test_outcome_guard import _cohort_codes, cohort_code_problems

    codes, sealed = _cohort_codes()
    problems = cohort_code_problems(ROOT / "data", codes, sealed)
    p(f"  kohort bekçisi (data/, {len(sealed)} kasa kodu): {len(problems)} sorun")

    p("## 4. f1r (ceiling_hazard_v1_real / _pooled ile)")
    for m, v1 in ((H99, "ceiling_hazard_v1_real"), (POOLED, "ceiling_hazard_v1_pooled")):
        ds, a = (h, ah) if m == H99 else (v, av)
        rows = bt.fall_training_rows(FAZ7C_MODEL_SPECS[m], ds, a, check=True)
        fr = bt.fall_raw_features(FAZ7C_MODEL_SPECS[m], rows, a)[0]
        vr = bt.v1_raw_features(FAZ7_MODEL_SPECS[v1], rows)[0]
        same = sum(1 for r in rows if str(fr[r.ticker]["f1r"]) == str(vr[r.ticker]["f1r"]))
        p(f"  {m}: {same}/{len(rows)} satırda f1r ham değeri bit-eşit (Decimal metni)")

    p("## 5. @ZERO")
    params, _ = bt.final_fit_fall(ZERO_ROW)
    for hh, ev in (("D10", 39), ("D5", 29)):
        val = params["horizons"][hh]["p_up"]["value"]
        p(f"  {hh}: p_up {val!r}; float(1 − Fraction({ev}, 161)) = {float(Fraction(1) - Fraction(ev, 161))!r}; "
          f"bit-eşit {val == float(Fraction(1) - Fraction(ev, 161))}")

    p("## 6. Fold planları")
    plans = {}
    for m in FAZ7C_MODEL_IDS:
        ds, a = (h, ah) if m == H99 else (v, av)
        spec = FAZ7C_MODEL_SPECS[m]
        rows = bt.fall_training_rows(spec, ds, a, check=True)
        ps = FAZ7C_MODEL_SPECS[spec.get("parent_model_id", m)]
        raw = bt.fall_raw_features(ps, rows, a)[0]
        plans[m] = (bt.plan_fall_folds(ds, rows, raw, uses_f3="f3" in ps["features"]), ds)
    for m in FAZ7C_MODEL_IDS:
        folds, ds = plans[m]
        by = ds.by_ticker()
        for hh in ("D5", "D10"):
            fh = [f for f in folds if f.horizon == hh]
            leak = sum(1 for f in fh for t in f.training if not by[t].targets[hh].session_date < f.prediction_date)
            leak10 = sum(1 for f in fh for t in f.training if not by[t].targets["D10"].session_date < f.prediction_date)
            near = [f for f in fh if f.status == bt.SCORABLE and f.prediction_date >= bt.NEAR_ERA_START]
            p(f"  {m} {hh}: test arzı {len(fh)}, skorlanabilir {sum(f.status == bt.SCORABLE for f in fh)}, yakın dönem {len(near)} "
              f"({len({f.prediction_date[:7] for f in near})} ay), f3 dışlamalı fold {sum(bool(f.filter_excluded) for f in fh)} "
              f"(yakın dönem {sum(bool(f.filter_excluded) for f in near)}), sızıntı D_h {leak}, D10 {leak10}")
    th = [f.test_ticker for f in plans[H99][0] if f.horizon == "D10" and f.status == bt.SCORABLE and f.prediction_date >= bt.NEAR_ERA_START]
    tp = [f.test_ticker for f in plans[POOLED][0] if f.horizon == "D10" and f.status == bt.SCORABLE and f.prediction_date >= bt.NEAR_ERA_START]
    p(f"  yakın dönem D10 ticker'ları h99 = pooled: {th == tp} ({len(th)})")

    p("## 7. Karşılaştırıcılar")
    man = json.loads((ROOT / "tests" / "reference" / "macos_golden" / "MANIFEST.json").read_text(encoding="utf-8"))
    for k, ref in bt.FAZ7C_COMPARATOR_LEDGERS.items():
        p(f"  {k}: pin {ref['sha256'][:12]}…, dosya {sha256_file(ROOT / ref['path'])[:12]}…, Faz 1A MANIFEST "
          f"{man['models'][k]['ledger_sha256'][:12]}…")
    n, b = bt.v15_d10_brier(bt.read_pinned_ledger(bt.FAZ7C_COMPARATOR_LEDGERS["v1_5_h99"]))
    logged = [json.loads(x) for x in (ROOT / "experiments" / "log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    ref = next(e for e in logged if e.get("model_id") == "v1_5_h99" and e.get("kind") == "backtest")["metrics"]["D10"]["p_up"]
    p(f"  V1.5 D10 Brier ledger'dan {b!r} ({n} fold); günlük {ref['brier']!r} (n {ref['n']}); |Δ| = {abs(b - ref['brier']):.3g}")

    p("## 8. Bayt-eşitlik")
    for d in ("macos_golden", "macos_golden_faz1b", "macos_golden_faz4", "macos_golden_faz5", "macos_golden_faz7"):
        lines = (ROOT / "tests" / "reference" / d / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
        ok = sum(1 for ln in lines if sha256_file(ROOT / "tests" / "reference" / d / ln.split("  ")[1]) == ln.split("  ")[0])
        changed = subprocess.run(["git", "status", "--porcelain", "--", f"tests/reference/{d}"], cwd=ROOT, check=True,
                                 capture_output=True, text=True).stdout
        p(f"  {d}: {ok}/{len(lines)} dosya SHA256SUMS ile aynı; çalışma ağacı değişikliği {len(changed.splitlines())}")
    out = subprocess.run([sys.executable, "app/parity/gen_golden.py", "--check"], cwd=ROOT, check=True, capture_output=True,
                         text=True).stdout.strip().splitlines()[-1]
    p(f"  gen_golden --check: {out}")

    p("## 9. Günlük (commit B)")
    spec_doc = SPEC_DOCUMENTS_FAZ7C["SPEC_C_V0"]
    bl = [e for e in logged if e.get("kind") == "backtest" and e.get("model_id") in FAZ7C_MODEL_IDS]
    if not bl:
        p("  henüz yok (commit A)")
    for e in bl:
        p(f"  {e['model_id']}: context {e['context']}, spec_document_sha256 = SPEC_C_V0.md {e['spec_document_sha256'] == sha256_file(ROOT / spec_doc['path'])}, "
          f"decisions KARARLAR_C {e['decisions_document_sha256'] == SPEC_DOCUMENTS_FAZ7C['KARARLAR_C']['sha256']}, "
          f"veri sürümü {'H99' if e['data_version_sha256'] == H99_DATA_VERSION_SHA256 else 'v2'}, borsai_dirty {e['borsai_dirty']}")
    ex = [e for e in logged if e.get("kind") == "exploration"]
    raw = (ROOT / FAZ7C_EXPLORATION["path"]).read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))
    p(f"  exploration satırı {len(ex)}; kaynak sha {sorted({e['source_sha256'] for e in ex})} (dosya {sha256_bytes(raw)}); "
      f"CSV satırlarıyla aynı {[e['variant'] for e in ex] == rows if ex else '—'}")


if __name__ == "__main__":
    main()

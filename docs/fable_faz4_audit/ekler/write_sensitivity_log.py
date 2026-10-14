#!/usr/bin/env python3
"""repro_output.json'daki duyarlılık koşularını experiments/log.jsonl biçiminde
docs/fable_faz4_audit/ekler/sensitivity_runs.jsonl'a ve fold ledger CSV'lerine yazar (yalnız stdlib; borsai import yok).
Bu koşular MODEL DEĞİLDİR (kind: sensitivity); dondurulacak model şartnamedeki v0'dır."""
import csv, hashlib, io, json, os, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
head = subprocess.run(["git", "log", "-1", "--format=%H"], cwd=ROOT, env=ENV, capture_output=True, text=True, check=True).stdout.strip()
dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, env=ENV, capture_output=True, text=True, check=True).stdout.strip())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
mine = json.loads((HERE / "repro_output.json").read_text(encoding="utf-8"))
manifest = json.loads((ROOT / "tests/reference/macos_golden_faz4/MANIFEST.json").read_text(encoding="utf-8"))
now = lambda: datetime.now(timezone(timedelta(hours=3))).isoformat(timespec="seconds")
VARIANTS = {
    "v0_ref": "kontrol: şartname v0 (N_MIN = 10, Z/B, merdiven) — birebir aynı sonuç beklenir",
    "nmin5": "(i) N_MIN = 5; diğer her şey v0",
    "nmin20": "(ii) N_MIN = 20; diğer her şey v0",
    "single_group": "(iii) Z/B ayrımı yok: tek grup G(m), m = h − t; merdiven kendi m, sonra m−1, m+1, …; N_MIN = 10",
    "nearest_only": "(iv) havuzlama yok: kendi hücresi n < 10 ise aynı gruptaki en yakın yeterli m (yoksa öteki grubun en yakın yeterli m'si) tek başına kullanılır; hedef m sınırına kırpılır",
}
out_lines = []
for name, desc in VARIANTS.items():
    s = mine["sensitivity"][name]
    ledger_path = HERE / f"sens_{name}_fold_ledger.csv"   # repro_ceiling_path.py yazar
    folds = list(csv.DictReader(open(ledger_path, encoding="utf-8", newline="")))
    n_ok = sum(1 for f in folds if f["status"] == "OK")
    entry = {
        "kind": "sensitivity",
        "context": "faz4_fable_sensitivity",
        "model_id": f"ceiling_path_v0__sens_{name}",
        "base_model_id": "ceiling_path_v0",
        "variant": desc,
        "is_model": False,
        "note": "Duyarlılık koşusu; kayıtlı model değildir ve dondurulmaz. Dondurulacak model şartnamedeki v0'dır (SPEC_CEILING_PATH_V0 §3, N_MIN = 10, Z/B, merdiven).",
        "plan_id": "H99_CEILING_PATH_T_CUTOFF_REUSE_CEILING_LEDGER",
        "spec_document": "docs/specs_faz4/SPEC_CEILING_PATH_V0.md",
        "spec_document_sha256": sha(ROOT / "docs/specs_faz4/SPEC_CEILING_PATH_V0.md"),
        "spec_sha256": manifest["runs"]["ceiling_path_v0"]["spec_sha256"],
        "spec_sha256_note": "taban modelin (ceiling_path_v0) kanonik şartname hash'i; varyant `variant` alanında",
        "data_version_sha256": sha(ROOT / "data/data_version.json"),
        "training_table_sha256": sha(ROOT / "data/training_table.csv"),
        "survival_model_id": "ceiling_hazard_v0",
        "survival_ledger": "tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv",
        "survival_ledger_sha256": s["src_sha"],
        "folds_total": len(folds),
        "folds_scorable": {"CEILING_PATH": n_ok},
        "ledger_file": ledger_path.relative_to(ROOT).as_posix(),
        "ledger_sha256": sha(ledger_path),
        "metrics": {"D5": {"folds": len(folds), "return": {"n": s["primary"]["n"], "mae": s["D5_mae_own_set"]},
                           "p_up": {"n": s["primary"]["n"], "brier": s["D5_brier"]}},
                    "primary_cell": {"comparator": "base_train_median", "horizon": "D5", "output": "MAE",
                                     "diff": s["primary"]["diff"], "ci95": s["primary"]["ci"], "n": s["primary"]["n"],
                                     "n_months": s["primary"]["n_months"], "model_mae": s["primary"]["model"],
                                     "rule_mae": s["primary"]["rule"], "model_better_n": s["primary"]["model_better"],
                                     "rule_better_n": s["primary"]["rule_better"], "tie_n": s["primary"]["tie"],
                                     "bootstrap": {"method": "MONTHLY_BLOCK_BY_FIRST_TRADING_MONTH", "reps": 4000, "seed": 20260921}},
                    "status_counts": {"OK": n_ok, "POST_BREAK_INSUFFICIENT": len(folds) - n_ok}},
        "started_at": now(),
        "finished_at": now(),
        "git_commit": head,
        "borsai_dirty": dirty,
        "borsai_source_sha256": None,
        "generator": "docs/fable_faz4_audit/ekler/repro_ceiling_path.py (borsai import etmez)",
    }
    out_lines.append(json.dumps(entry, ensure_ascii=False, sort_keys=True))
(HERE / "sensitivity_runs.jsonl").write_text("\n".join(out_lines) + "\n", encoding="utf-8")
print(f"{len(out_lines)} satır yazıldı; HEAD {head[:7]} dirty={dirty}")

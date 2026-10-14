"""BORSAI_FAZ7_HAZARD_V1_IMPL_20260925 — görev metnindeki "Beklenen sayılar" tablosunun ölçümü (yalnız okur; commit B'den sonra).

Çalıştırma (depo kökünde):
    PYTHONPATH=. .venv/bin/python docs/faz7/ekler/olcum_beklenen_sayilar.py > docs/faz7/ekler/olcum_beklenen_sayilar.txt

Çıktıda arz kodu yoktur (yalnız sayılar ve dosya yolları). Kasa üyelerinin dosyaları okunmaz: kasa hakkında yalnız kohort
listesi (registry) ve `tests/test_outcome_guard.py`'nin T4 bekçi fonksiyonu kullanılır.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import date, timedelta

from borsai import backtest as bt
from borsai import data as dm
from borsai import registry as reg
from borsai import survival as sv
from borsai import tufe
from borsai.predict_hazard import regime_value
from borsai.provenance import ROOT, sha256_bytes, sha256_file

SPEC_COMMIT = "6a16c16"          # şartname commit'i (uygulamadan önce)
TASK_EXPECTED = {
    "L_open": {0: 9, 1: 11, 2: 5, 3: 4, 4: 3, 5: 8, 6: 5, 7: 6, 8: 5, 9: 6, 10: 9},
    "month_for": {"2026-09-02": "2026-07", "2026-09-25": "2026-07", "2026-10-01": "2026-08", "2020-01-06": "2019-11"},
}


def git_bytes(rev: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


def line(label: str, measured, expected, ok: bool) -> None:
    print(f"- {label}: ölçülen {measured} | beklenen {expected} | {'TUTTU' if ok else 'TUTMADI'}")


def main() -> int:
    print("# Beklenen sayılar — ölçüm")
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    print(f"HEAD {head}; şartname commit'i {SPEC_COMMIT}\n")

    # 1 ---------------------------------------------------------------- training_table_v2
    print("## training_table_v2.csv")
    rows = list(csv.DictReader(io.StringIO(dm.TABLE_V2_PATH.read_text(encoding="utf-8"), newline="")))
    line("satır", len(rows), 170, len(rows) == 170)
    line("kohort", dict(Counter(r["cohort"] for r in rows)), {"H99": 99, "OOT_OPEN": 71},
         Counter(r["cohort"] for r in rows) == {"H99": 99, "OOT_OPEN": 71})
    old_lines = dm.TABLE_PATH.read_bytes().decode("utf-8").splitlines()
    old = {x.split(",", 1)[0]: x for x in old_lines[1:]}
    cols = dm.h99_columns()
    eq = 0
    for r in rows:
        if r["cohort"] == "H99":
            buf = io.StringIO(newline="")
            csv.writer(buf, lineterminator="").writerow([r[c] for c in cols])
            eq += buf.getvalue() == old[r["ticker"]]
    line(f"H99 satırları paylaşılan {len(cols)} sütunda training_table.csv ile bayt-eşit", f"{eq}/99", "99/99", eq == 99)
    for rel in ("data/training_table.csv", "data/data_version.json", "data/build_training_table.py"):
        same = sha256_file(ROOT / rel) == sha256_bytes(git_bytes(SPEC_COMMIT, rel))
        line(f"{rel} sha256 {SPEC_COMMIT}'dakiyle aynı", f"{sha256_file(ROOT / rel)[:12]}…", "değişmez", same)
    print()

    # 2 ---------------------------------------------------------------- açık kümenin L dağılımı
    v2 = dm.load_dataset_v2()
    oot = [r for r in v2.rows if r.cohort == "OOT_OPEN"]
    dist = dict(sorted(Counter(r.ceiling_streak for r in oot).items()))
    print("## Açık kümenin L dağılımı (71 üye)")
    line("L dağılımı", dist, TASK_EXPECTED["L_open"], dist == TASK_EXPECTED["L_open"] and len(oot) == 71)
    print()

    # 3 ---------------------------------------------------------------- alloc_regime
    print("## alloc_regime")
    _, cohort_rows = reg.read_cohort()
    members = reg.cohort_members(cohort_rows)
    by = {m["ticker"]: m for m in members}
    single = sum(1 for r in v2.rows if r.alloc_regime == dm.alloc_regime(r.alloc_regime_date))
    line("v2 satırlarında alloc_regime = data.alloc_regime(talep toplama başlangıcı)", f"{single}/170", "170/170", single == 170)
    open_eq = sum(1 for r in oot if r.alloc_regime == reg.parse_regime_tags(by[r.ticker]["regime_tags"])["ALLOC_REGIME"])
    line("açık küme: kohort etiketiyle eşit", f"{open_eq}/71", "71/71", open_eq == 71)
    h99_eq = sum(1 for r in v2.rows if r.cohort == "H99" and r.alloc_regime == "EQUAL_DIST_20230330")
    line("H99: EQUAL_DIST_20230330", f"{h99_eq}/99", "99/99", h99_eq == 99)
    base = dict(first_trading_date="2021-06-01", market="ANA", sale_method="ON_EXCHANGE", ipo_price_tl="10", ipo_price_try="10",
                sessions=[(date(2021, 6, 1) + timedelta(days=i)).isoformat() for i in range(20)], vault="OPEN")
    d, n_days, n_same = date(2019, 1, 1), 0, 0
    while d <= date(2026, 12, 31):
        s = d.isoformat()
        n_days += 1
        n_same += dm.alloc_regime(s) == reg.compute_regime_tags(bookbuilding_start=s, **base)["ALLOC_REGIME"]
        d += timedelta(days=1)
    line("data.alloc_regime ≡ registry.compute_regime_tags (2019-01-01…2026-12-31, her gün)", f"{n_same}/{n_days}",
         f"{n_days}/{n_days}", n_same == n_days)
    labels = [reg.parse_regime_tags(m["regime_tags"])["ALLOC_REGIME"] for m in members]
    by_ftd = [dm.alloc_regime(m["first_trading_date"]) for m in members]
    r_same = sum(1 for a, b in zip(labels, by_ftd) if regime_value(a) == regime_value(b))
    n_lab = sum(1 for a, b in zip(labels, by_ftd) if a != b)
    print(f"- 135 kohort üyesi (yalnız kohort listesi): ilk işlem günü okumasında etiketi farklı {n_lab} (2021-11-11 sınırı); "
          f"ikili r aynı {r_same}/{len(members)} (SPEC_DEVIATIONS J2)")
    print("- 135/135 = (yukarıdaki her gün eşdeğerliği) + (tests/test_faz6_oot.py::test_real_cohort_validates_and_reproduces_from_code: "
          "kohort etiketleri compute_regime_tags(bookbuilding_start)'tan yeniden üretilir); kasa girdileri bu ölçümde okunmadı")
    print()

    # 4 ---------------------------------------------------------------- kasa kodu data/ altında
    print("## Kasa kodu (data/)")
    spec = importlib.util.spec_from_file_location("outcome_guard", ROOT / "tests" / "test_outcome_guard.py")
    guard = importlib.util.module_from_spec(spec)
    sys.modules["outcome_guard"] = guard
    spec.loader.exec_module(guard)
    codes, sealed = guard._cohort_codes()
    problems = guard.cohort_code_problems(ROOT / "data", codes, sealed)
    n_problems, n_sealed = len(problems), len(sealed)
    line(f"T4 bekçisinin bulduğu sorun (kasa {n_sealed} kod; bütün data/)", n_problems, 0, n_problems == 0)
    vault = re.compile(r"\b(" + "|".join(sealed) + r")\b")
    for rel in ("data/training_table_v2.csv", "data/data_version_v2.json", "data/build_training_table_v2.py",
                "data/raw/tuik/tufe_genel_2025_100.csv", "data/raw/tuik/tufe_bultenleri.csv", "data/raw/tuik/build_tufe_csv.py"):
        n = len(set(vault.findall((ROOT / rel).read_text(encoding="utf-8"))))
        line(f"{rel}: kasa kodu", n, 0, n == 0)
    comp = list(csv.DictReader((ROOT / guard.COMPLETENESS_REL).read_text(encoding="utf-8").splitlines()))
    known = [r for r in comp if any(vault.search(v or "") for v in r.values())]
    n_known = len(known)
    print(f"- önceden var olan istisna (SPEC_DEVIATIONS J18): {guard.COMPLETENESS_REL} {n_known} satır "
          f"(first_seen ≥ {guard.LIVE_SCOPE_START}, ipos_status {sorted({r['ipos_status'] for r in known})}); pin "
          f"{guard.KNOWN_COMPLETENESS_SEALED_ROWS}")
    print()

    # 5 ---------------------------------------------------------------- TÜFE
    print("## TÜFE (data/raw/tuik/tufe_genel_2025_100.csv)")
    table = tufe.load()
    months = list(table.months)
    contiguous = all(tufe.month_add(a, 1) == b for a, b in zip(months, months[1:]))
    line("aylar", f"{months[0]}…{months[-1]} ({len(months)} ay, kesintisiz: {contiguous})", "2019-11'den güncele kesintisiz",
         months[0] == "2019-11" and contiguous)
    avg = sum(float(table.rows[m].index) for m in months if m.startswith("2025-")) / 12
    line("2025 ortalaması", f"{avg:.4f}", "100.00 ± 0.05", abs(avg - 100) <= 0.05)
    rule = sum(1 for m in months if table.rows[m].release_date[:10] >= f"{tufe.month_add(m, 1)}-03")
    line("release_date ≥ izleyen ayın 3'ü", f"{rule}/{len(months)}", f"{len(months)}/{len(months)}", rule == len(months))
    got = {t: tufe.month_for(t) for t in TASK_EXPECTED["month_for"]}
    line("month_for örnekleri", got, TASK_EXPECTED["month_for"], got == TASK_EXPECTED["month_for"])
    pit = sum(1 for r in v2.rows if tufe.index_for(r.first_trading_date, table)["release_date"] < r.first_trading_date)
    same = sum(1 for r in v2.rows if (tufe.index_for(r.first_trading_date, table)["month"], tufe.index_for(r.first_trading_date, table)["index"])
               == (r.tufe_month, r.tufe_index))
    line("release_date < T (v2 satırları)", f"{pit}/170", "170/170", pit == 170)
    line("v2'nin tufe_month/tufe_index = tufe.index_for(T)", f"{same}/170", "170/170", same == 170)
    print(f"- dosya sha256 {table.file_sha256}; ham xls sha256 "
          f"{sha256_file(ROOT / 'data/raw/tuik/tufe_degisim_oranlari_bulten_58290.xls')}")
    print()

    # 6 ---------------------------------------------------------------- PP sayımı
    print("## PP sayımı")
    f3 = [r for r in v2.rows if r.inputs["total_demand_multiple"] is not None]
    h99 = sv.pp_table([sv.unit_of(r) for r in f3 if r.cohort == "H99"])
    op = sv.pp_table([sv.unit_of(r) for r in f3 if r.cohort == "OOT_OPEN"])
    pool = sv.pp_table([sv.unit_of(r) for r in f3])
    for label, pp, exp in (("H99 f3'lü", h99, (506, 83)), ("açık f3'lü", op, (374, 59)), ("havuz", pool, (880, 142))):
        got = (len(pp), sum(r.event for r in pp))
        line(f"{label} satır / olay", f"{got[0]} / {got[1]}", f"{exp[0]} / {exp[1]}", got == exp)
    events, risk = sv.group_counts(pool)
    groups = [f"{e}/{k}" for e, k in zip(events, risk)]
    line("havuz grup olay/risk (g1, g2, g3)", ", ".join(groups), "25/165, 31/258, 86/457", groups == ["25/165", "31/258", "86/457"])
    line("havuz arz (f3'lü)", f"{len(f3)} ({dict(Counter(r.cohort for r in f3))})", 165, len(f3) == 165)
    print()

    # 7 ---------------------------------------------------------------- fold planları (altın ledger'lardan)
    print("## Fold planları (tests/reference/macos_golden_faz7/)")
    runs = {m: bt.read_pinned_ledger({"path": f"tests/reference/macos_golden_faz7/{bt.golden_filename(m)}",
                                      "sha256": sha256_file(bt.GOLDEN_FAZ7_DIR / bt.golden_filename(m))})
            for m in ("ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF")}
    v0 = bt.read_pinned_ledger(bt.FAZ7_COMPARATOR_LEDGERS["ceiling_hazard_v0"])
    v0t = [r["ticker"] for r in v0]
    for m in ("ceiling_hazard_v1_clip", "ceiling_hazard_v1_real"):
        t = [r["ticker"] for r in runs[m]]
        line(f"{m}: fold, v0 ile aynı ticker (sıra dahil)", f"{len(t)}, {t == v0t}", "87, True", len(t) == 87 and t == v0t)
    pt = [r["ticker"] for r in runs["ceiling_hazard_v1_pooled"]]
    line("ceiling_hazard_v1_pooled: fold, 87'nin hepsini içerir", f"{len(pt)}, {set(v0t) <= set(pt)}", "97 (ölçülmedi), True",
         set(v0t) <= set(pt))
    near = {m: {r["ticker"] for r in rows if r["first_trading_date"] >= bt.NEAR_ERA_START} for m, rows in runs.items()}
    blocks = {r["first_trading_date"][:7] for r in runs["ceiling_hazard_v1_clip"] if r["ticker"] in near["ceiling_hazard_v1_clip"]}
    same_near = len({frozenset(s) for s in near.values()}) == 1
    line("yakın dönem fold / blok / dört koşuda aynı ticker'lar", f"{len(near['ceiling_hazard_v1_clip'])} / {len(blocks)} / {same_near}",
         "78 / 22 / True", len(near["ceiling_hazard_v1_clip"]) == 78 and len(blocks) == 22 and same_near)
    leak = sum(1 for rows in runs.values() for r in rows if not r["training_max_session_date"] < r["first_trading_date"])
    line("sızıntı: max(eğitim seans tarihi) ≥ T olan fold", leak, 0, leak == 0)
    print()

    # 8 ---------------------------------------------------------------- v0 karşılaştırıcısı
    print("## v0 karşılaştırıcısı")
    ref = bt.FAZ7_COMPARATOR_LEDGERS["ceiling_hazard_v0"]
    line("ledger sha256", sha256_file(ROOT / ref["path"])[:12] + "…", ref["sha256"][:12] + "…", sha256_file(ROOT / ref["path"]) == ref["sha256"])
    mean = bt.v0_mean_rps(v0)
    logged = [json.loads(x) for x in (ROOT / "experiments/log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    v0_log = next(e for e in logged if e.get("model_id") == "ceiling_hazard_v0" and e.get("context") == "faz1b_golden")
    delta = abs(mean - v0_log["metrics"]["rps"])
    line("87-fold ortalama RPS (ledger'daki S_1..S_10'dan)", f"{mean:.10f} (|Δ| günlükteki Faz 1B değerine {delta:.1e})",
         "0.1503 (|Δ| ≤ 1e-9)", round(mean, 4) == bt.V0_PUBLISHED_MEAN_RPS and delta <= 1e-9)
    print()

    # 9 ---------------------------------------------------------------- bayt-eşitlik
    print("## Bayt-eşitlik")
    for d in ("tests/reference/macos_golden", "tests/reference/macos_golden_faz1b", "tests/reference/macos_golden_faz4",
              "tests/reference/macos_golden_faz5"):
        diff = subprocess.run(["git", "diff", "--name-only", SPEC_COMMIT, "--", d], cwd=ROOT, check=True, capture_output=True,
                              text=True).stdout.split()
        n_files = len(subprocess.run(["git", "ls-files", d], cwd=ROOT, check=True, capture_output=True, text=True).stdout.split())
        line(f"{d} ({n_files} dosya) {SPEC_COMMIT}'dan beri", f"değişen {len(diff)}", "0", not diff)
    diff = subprocess.run(["git", "diff", "--name-only", SPEC_COMMIT, "--", "app/parity/golden"], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.split()
    line("app/parity/golden: değişen dosya", diff, "['app/parity/golden/MANIFEST.json'] (T2)", diff == ["app/parity/golden/MANIFEST.json"])
    chk = subprocess.run([sys.executable, "app/parity/gen_golden.py", "--check"], cwd=ROOT, check=False, capture_output=True,
                         text=True).stdout.strip().splitlines()[-1]
    got = json.loads(chk)
    line("gen_golden --check", chk, '{"checked": 25, "different": []}', got == {"checked": 25, "different": []})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

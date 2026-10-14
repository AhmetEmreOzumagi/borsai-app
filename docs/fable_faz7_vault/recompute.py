#!/usr/bin/env python3
"""BORSAI_FAZ7_FABLE_VAULT_RECOMPUTE — kasa (64 SEALED üye) için bağımsız, kör yeniden hesap.

Kurallar: `borsai` import edilmez; tanımlar şartnamelerden (SPEC_OOT_PRE_H99_V0 §2/§6, KARARLAR D5/D6,
SPEC_HAZARD_V1 §5.2/§5.5/§6.1/§6.4/§7.2/§7.3, SPEC_C_V0 §1.2/§5.2/§5.5/§6.1/§6.4, KARARLAR_C C1,
SPEC_POST_D1_V0 §4, SPEC_SCORING §2/§3/§7/§8, SPEC_DEVIATIONS I10–I13/L1/M1/M12 — HEAD'deki commit'li sürüm).
Girdiler yalnız git DAG'ı, registry/push_proofs, registry/oot/{cohort_pre_h99.csv,records,post_d1,d1_rows},
data/outcomes_oot/*.csv, data/raw/bist/MANIFEST_OOT.csv, models/INDEX.json ve scores/scores.json'un
`models[].backtest.near_era` blokları (yalnız k3 için).

Çıktı: docs/fable_faz7_vault/BAGIMSIZ.json. Ekrana yalnız sayılar; üye kodu basılmaz.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "BAGIMSIZ.json"

B_BOOT = 4000
SEED = 20260921
MIN_N = 10
MIN_BLOCKS = 6
TOL_COND = 1e-12
TIE_TOL = 0.002  # §5.5 eşitlik toleransı (her iki şartname)

OLD_MODELS = [
    "v1_5_h99", "base_always_ceiling", "base_train_median", "base_train_mean", "base_zero",
    "base_rate", "base_last10_rate", "v1_6_h99", "v1_5_market20_v0", "pb_v0",
    "ceiling_hazard_v0", "ceiling_hazard_v0@INF", "pb_ceiling_v0", "pb_ceiling_v0@INF",
    "base_km_expanding", "base_km_last10", "ceiling_path_v0", "ceiling_path_v0@INF",
    "pb_ceiling_path_v0",
]
V1_MODELS = ["ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF"]
V1_CANDIDATES = ["ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled"]
C_MODELS = ["fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO"]
C_CANDIDATES = ["fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale"]
POST_D1_MODEL = "post_d1_hazard_v0"

RETURN_MODELS = {"v1_5_h99", "v1_6_h99", "v1_5_market20_v0", "pb_v0", "ceiling_path_v0",
                 "ceiling_path_v0@INF", "pb_ceiling_path_v0", "base_always_ceiling",
                 "base_train_median", "base_train_mean", "base_zero"}
PUP_ONLY_MODELS = {"base_rate", "base_last10_rate", *C_MODELS}
HAZARD_MODELS = {"ceiling_hazard_v0", "ceiling_hazard_v0@INF", "pb_ceiling_v0",
                 "pb_ceiling_v0@INF", "base_km_expanding", "base_km_last10", *V1_MODELS}

# 8 eski birincil hücre (SPEC_OOT §6, I11) — kasada
OLD_PRIMARY_CELLS = [
    ("v1_5_h99", "MAE", "D5", "base_train_median", "comparators"),
    ("v1_6_h99", "MAE", "D10", "v1_5_h99", "model_cell"),
    ("v1_5_market20_v0", "MAE", "D5", "v1_5_h99", "model_cell"),
    ("pb_v0", "MAE", "D5", "base_train_median", "comparators"),
    ("ceiling_hazard_v0", "RPS", None, "base_km_expanding", "comparators"),
    ("pb_ceiling_v0", "RPS", None, "base_km_expanding", "comparators"),
    ("ceiling_path_v0", "MAE", "D5", "base_train_median", "comparators"),
    ("pb_ceiling_path_v0", "MAE", "D5", "base_train_median", "comparators"),
]
# v1 hücreleri (SPEC_HAZARD_V1 §5.2, §5.4): (model, metrik, karşılaştırıcı, kaynak, etiket)
V1_CELLS = []
for m in V1_CANDIDATES:
    V1_CELLS += [
        (m, "RPS", "base_km_expanding", "comparators", "birincil"),
        (m, "RPS", "ceiling_hazard_v0", "model_cell", "k2"),
        (m, "Brier_k10", "base_km_expanding", "comparators", "ikincil"),
    ]
V1_CELLS += [
    ("ceiling_hazard_v1_real", "RPS", "ceiling_hazard_v1_clip", "model_cell", "merdiven"),
    ("ceiling_hazard_v1_pooled", "RPS", "ceiling_hazard_v1_real", "model_cell", "merdiven"),
    ("ceiling_hazard_v1_pooled", "RPS", "ceiling_hazard_v1_pooled@INF", "model_cell", "merdiven"),
]
# (C) hücreleri (SPEC_C_V0 §5.2, §5.4): (model, ufuk, karşılaştırıcı, kaynak, etiket)
C_CELLS = []
for m in C_CANDIDATES:
    C_CELLS += [
        (m, "D10", "base_rate", "comparators", "birincil"),
        (m, "D10", "v1_5_h99", "model_cell", "k2"),
        (m, "D5", "base_rate", "comparators", "ikincil"),
    ]
C_CELLS += [
    ("fall_d10_v0_pooled", "D10", "fall_d10_v0_h99", "model_cell", "merdiven"),
    ("fall_d10_v0_pooled", "D10", "fall_d10_v0_pooled@ZERO", "model_cell", "merdiven"),
    ("v1_5_h99", "D10", "base_rate", "comparators", "bilgi"),
]


# ---------------------------------------------------------------- git yardımcıları
def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


@lru_cache(maxsize=None)
def is_ancestor(a: str, b: str) -> bool:
    r = subprocess.run(["git", "merge-base", "--is-ancestor", a, b], cwd=ROOT, capture_output=True)
    if r.returncode not in (0, 1):
        raise RuntimeError(f"merge-base hatası: {r.stderr.decode()}")
    return r.returncode == 0


@lru_cache(maxsize=None)
def add_commits(path: str) -> tuple[str, ...]:
    out = git("log", "--diff-filter=A", "--format=%H", "--reverse", "--", path)
    return tuple(x for x in out.splitlines() if x)


def first_add(path: str) -> str | None:
    c = add_commits(path)
    return c[0] if c else None


def dag_min(commits: list[str]) -> tuple[str | None, bool]:
    """DAG'da en erken commit: bütün diğerlerinin atası olan. Yoksa (committer tarihine göre en erken, False)."""
    cs = sorted(set(c for c in commits if c))
    if not cs:
        return None, True
    for c in cs:
        if all(c == d or is_ancestor(c, d) for d in cs):
            return c, True
    dated = sorted(cs, key=lambda c: git("show", "-s", "--format=%cI", c))
    return dated[0], False


# ---------------------------------------------------------------- push kanıtları
def load_proofs() -> list[dict]:
    proofs = []
    for p in sorted((ROOT / "registry" / "push_proofs").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        proofs.append({"file": p.name, "sha": d["proven_commit_sha"], "created_at": d["created_at"], "method": d.get("method")})
    return proofs


_PROOF_CACHE: dict[str, dict | None] = {}


def proof_for(commit: str | None, proofs: list[dict]) -> dict | None:
    """Commit'i kapsayan (kendisi ya da torunu için alınmış) en erken kanıt."""
    if commit is None:
        return None
    if commit not in _PROOF_CACHE:
        cands = [p for p in proofs if p["sha"] == commit or is_ancestor(commit, p["sha"])]
        _PROOF_CACHE[commit] = min(cands, key=lambda p: p["created_at"]) if cands else None
    return _PROOF_CACHE[commit]


# ---------------------------------------------------------------- kohort, kayıtlar, sonuçlar
def read_cohort() -> list[dict]:
    with (ROOT / "registry" / "oot" / "cohort_pre_h99.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def active_rows(rows: list[dict]) -> dict[str, dict]:
    active: dict[str, dict] = {}
    for r in rows:
        t = r["ticker"]
        if r["status"] == "CANCELLED":
            active.pop(t, None)
        else:
            active[t] = r
    return active


def active_records(dir_: Path) -> tuple[list[tuple[Path, dict]], int, int]:
    """Etkin PREDICTION kayıtları (recorded_at_utc, ad) sırasıyla; (liste, dosya sayısı, iptal sayısı)."""
    files = sorted(dir_.glob("*.json")) if dir_.exists() else []
    docs = [(p, json.loads(p.read_text(encoding="utf-8"))) for p in files]
    cancelled = {d.get("cancels") for _, d in docs if d.get("record_type") == "CANCELLATION"}
    n_cancel = sum(1 for _, d in docs if d.get("record_type") == "CANCELLATION")
    preds = [(p, d) for p, d in docs if d.get("record_type") == "PREDICTION" and p.name not in cancelled
             and hashlib.sha256(p.read_bytes()).hexdigest() not in cancelled]
    preds.sort(key=lambda pd: (pd[1].get("recorded_at_utc", ""), pd[0].name))
    return preds, len(docs), n_cancel


def record_for_model(preds: list[tuple[Path, dict]], model_id: str) -> tuple[Path | None, dict | None, dict | None]:
    """L1/L2 + I12: o modeli içeren en erken etkin kayıt; (yol, belge, model hücresi)."""
    for p, d in preds:
        for cell in d.get("models", []):
            if cell.get("model_id") == model_id:
                return p, d, cell
    return None, None, None


def read_outcomes(ticker: str) -> list[dict] | None:
    p = ROOT / "data" / "outcomes_oot" / f"{ticker}.csv"
    if not p.exists():
        return None
    with p.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if r.get("outcome_basis") != "MACHINE_EXTRACTED":
            raise RuntimeError("outcome_basis beklenmedik")
    return rows


def streak(rows: list[dict]) -> int | None:
    """L = D_1'den başlayan ardışık tavan sayısı; ilk 0'da durur; 0'dan önce NA/eksik varsa bilinmez."""
    by_h = {int(r["h"]): r for r in rows}
    L = 0
    for h in range(1, 11):
        r = by_h.get(h)
        if r is None or r["status"] != "OK":
            return None
        c = r["ceiling_close"]
        if c == "":
            return None
        if c == "1":
            L += 1
        else:
            return L
    return L


def realized_return(rows: list[dict], h: int) -> float | None:
    for r in rows:
        if int(r["h"]) == h:
            if r["status"] != "OK" or r["R_h"] == "":
                return None
            return float(Decimal(r["R_h"]))
    return None


def realized_up(rows: list[dict], h: int) -> tuple[int | None, int | None]:
    """Y_h = 1[close(D_h) > ipo_price] = 1[R_h > 0] (SPEC_SCORING §3; C1: kapanış ≤ arz → olay).
    Dönüş (R_h'den hesaplanan Y, CSV'deki Y_h sütunu)."""
    for r in rows:
        if int(r["h"]) == h:
            if r["status"] != "OK" or r["R_h"] == "":
                return None, None
            y_calc = 1 if Decimal(r["R_h"]) > 0 else 0
            y_csv = int(r["Y_h"]) if r.get("Y_h", "") != "" else None
            return y_calc, y_csv
    return None, None


def canonical_sha(path: Path) -> str:
    d = json.loads(path.read_text(encoding="utf-8"))
    return hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def manifest_pins() -> dict[tuple[str, str], dict]:
    with (ROOT / "data" / "raw" / "bist" / "MANIFEST_OOT.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    pins = {}
    for r in rows:
        key = (r["date"], r["kind"])
        if key in pins and pins[key]["sha256"] != r["sha256"]:
            raise RuntimeError("MANIFEST_OOT: aynı (tarih, tür) için farklı sha")
        pins[key] = r
    return pins


def repo_zip_dates() -> list[tuple[str, str, str]]:
    out = []
    for line in git("ls-files", "data/raw/bist").splitlines():
        name = os.path.basename(line)
        if name.endswith(".zip") and len(name) >= 12 and name[:3] in ("thb", "thm") and name[3:11].isdigit():
            d = name[3:11]
            out.append((f"{d[:4]}-{d[4:6]}-{d[6:8]}", name[:3], line))
    return out


# ---------------------------------------------------------------- metrikler
def rps(S: list[float], L: int) -> float:
    return sum((S[k - 1] - (1.0 if L >= k else 0.0)) ** 2 for k in range(1, 11)) / 10.0


def brier_k(S: list[float], L: int, k: int) -> float:
    return (S[k - 1] - (1.0 if L >= k else 0.0)) ** 2


def brier_pup(p: float, y: int) -> float:
    return (p - float(y)) ** 2


def cond_rps_j1(S_cond: dict, L: int) -> float:
    return sum((float(S_cond[str(k)]) - (1.0 if L >= k else 0.0)) ** 2 for k in range(2, 11)) / 9.0


def block_bootstrap_ci(d: list[float], blocks: list[str]) -> list[float] | None:
    if len(d) < MIN_N or len(set(blocks)) < MIN_BLOCKS:
        return None
    rng = np.random.Generator(np.random.PCG64(SEED))
    ids = sorted(set(blocks))
    by = defaultdict(list)
    for di, b in zip(d, blocks):
        by[b].append(di)
    stats = []
    for _ in range(B_BOOT):
        draw = rng.choice(ids, size=len(ids), replace=True)
        vals = np.concatenate([np.asarray(by[b], dtype=float) for b in draw])
        stats.append(float(vals.mean()))
    lo, hi = np.percentile(np.asarray(stats), [2.5, 97.5])
    return [float(lo), float(hi)]


def verdict(n: int, ci: list[float] | None) -> str | None:
    if n < 10:
        return None
    if n < 30:
        return "yetersiz örnek"
    if ci is None:
        return "aralık için yetersiz"
    if ci[1] < 0:
        return "geçiyor (zaman-dışı terazide)"
    if ci[0] > 0:
        return "geçemiyor (zaman-dışı terazide)"
    return "ayırt edilemiyor"


def cell_summary(pairs: list[dict]) -> dict:
    d = [p["d"] for p in pairs]
    blocks = [p["block"] for p in pairs]
    n = len(d)
    mean = float(np.mean(d)) if n else None
    ci = block_bootstrap_ci(d, blocks) if n else None
    by_year = defaultdict(list)
    by_regime = defaultdict(list)
    for p in pairs:
        by_year[p["block"][:4]].append(p["d"])
        by_regime[p.get("alloc_regime", "?")].append(p["d"])
    return {
        "n": n,
        "n_blocks": len(set(blocks)),
        "mean_diff": mean,
        "ci95": ci,
        "wins": sum(1 for x in d if x < 0),
        "losses": sum(1 for x in d if x > 0),
        "ties": sum(1 for x in d if x == 0),
        "mean_loss_model": float(np.mean([p["loss_model"] for p in pairs])) if n else None,
        "mean_loss_rule": float(np.mean([p["loss_rule"] for p in pairs])) if n else None,
        "verdict": verdict(n, ci),
        "by_year": {y: {"n": len(v), "mean_diff": float(np.mean(v))} for y, v in sorted(by_year.items())},
        "by_alloc_regime": {y: {"n": len(v), "mean_diff": float(np.mean(v))} for y, v in sorted(by_regime.items())},
        "pairs": pairs,
    }


def alloc_regime_of(row: dict) -> str:
    for tag in row["regime_tags"].split("|"):
        if tag.startswith("ALLOC_REGIME="):
            return tag.split("=", 1)[1]
    return "?"


# ---------------------------------------------------------------- ana akış
def main() -> int:
    head = git("rev-parse", "HEAD")
    proofs = load_proofs()
    cohort = read_cohort()
    active = active_rows(cohort)
    members = {t: r for t, r in active.items() if r["status"] == "MEMBER"}
    sealed = sorted(t for t, r in members.items() if r["vault"] == "SEALED")
    open_set = sorted(t for t, r in members.items() if r["vault"] != "SEALED")
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
    index_models = [m["model_id"] for m in index["models"]]
    assert index_models == OLD_MODELS + V1_MODELS + C_MODELS, "INDEX sırası beklenenden farklı"
    ALL_MODELS = index_models + [POST_D1_MODEL]
    counters = {
        "n_member": len(members),
        "n_out_of_scope": sum(1 for r in active.values() if r["status"] == "OUT_OF_SCOPE"),
        "n_open": len(open_set),
        "n_sealed": len(sealed),
        "n_sealed_by_year": dict(sorted(Counter(members[t]["year"] for t in sealed).items())),
        "n_sealed_by_alloc_regime": dict(sorted(Counter(alloc_regime_of(members[t]) for t in sealed).items())),
        "n_sealed_by_sale_method": dict(sorted(Counter(members[t]["sale_method"] for t in sealed).items())),
        "n_index_models": len(index_models),
    }
    pins = manifest_pins()
    zips = repo_zip_dates()

    # model commit'leri ve kanıtları
    model_commit, model_proof = {}, {}
    for m in ALL_MODELS:
        c = first_add(f"models/{m}.json")
        if c is None:
            raise RuntimeError(f"model dosyası ekleyen commit yok: {m}")
        model_commit[m] = c
        model_proof[m] = proof_for(c, proofs)

    # (model, üye) başına kayıt commit'i — bütün MEMBER'lar (kapı için); kod yazılmaz
    rec_commit_by_member_model: dict[str, dict[str, str | None]] = {}
    rec_proof_by_commit: dict[str, dict | None] = {}
    n_members_without_model_record = Counter()
    for t in members:
        preds, _, _ = active_records(ROOT / "registry" / "oot" / "records" / t)
        d = {}
        for m in index_models + ["ceiling_hazard_v0"]:
            p, _, _ = record_for_model(preds, m)
            c = first_add(str(p.relative_to(ROOT))) if p else None
            d[m] = c
            if c is None:
                n_members_without_model_record[m] += 1
            elif c not in rec_proof_by_commit:
                rec_proof_by_commit[c] = proof_for(c, proofs)
        rec_commit_by_member_model[t] = d
    gate_commit_sets = {m: sorted(set(c for t in members for c in [rec_commit_by_member_model[t][m]] if c)) for m in index_models}

    def gate_ok(model: str, ingest: str | None, ingest_proof: dict | None) -> bool:
        """L1 skor kapısı: her MEMBER için modeli içeren birincil kayıt ingest'in atası VE kanıtı ingest kanıtından önce."""
        if ingest is None or ingest_proof is None or n_members_without_model_record[model]:
            return False
        for c in gate_commit_sets[model]:
            if not (c == ingest or is_ancestor(c, ingest)):
                return False
            pr = rec_proof_by_commit.get(c)
            if pr is None or not (pr["created_at"] < ingest_proof["created_at"]):
                return False
        return True

    per_member = {}
    class_by_model = defaultdict(Counter)
    status_by_model = defaultdict(Counter)
    ingest_info = Counter()
    d1_diff_first_trading = 0
    L_dist = Counter()
    y_check = Counter()
    for t in sealed:
        row = members[t]
        preds, n_rec, n_cancel = active_records(ROOT / "registry" / "oot" / "records" / t)
        pd_preds, n_pd, n_pd_cancel = active_records(ROOT / "registry" / "oot" / "post_d1" / t)
        pd_path, pdrec = (pd_preds[0][0], pd_preds[0][1]) if pd_preds else (None, None)
        outcomes = read_outcomes(t)
        info = {"ticker": t, "year": row["year"], "alloc_regime": alloc_regime_of(row), "sale_method": row["sale_method"],
                "n_records": n_rec, "n_cancellations": n_cancel, "n_post_d1_records": n_pd, "n_post_d1_cancellations": n_pd_cancel}
        if outcomes:
            d1 = next(r["session_date"] for r in outcomes if int(r["h"]) == 1)
            d10 = max(r["session_date"] for r in outcomes if r["status"] == "OK")
            info["D_1"] = d1
            info["block"] = d1[:7]
            info["L"] = streak(outcomes)
            L_dist[info["L"]] += 1
            info["n_ok_rows"] = sum(1 for r in outcomes if r["status"] == "OK")
            info["n_target_unavailable_rows"] = sum(1 for r in outcomes if r["status"] == "TARGET_UNAVAILABLE")
            info["n_na_limit_rows"] = sum(1 for r in outcomes if r["status"] == "NA_LIMIT")
            info["n_pending_rows"] = sum(1 for r in outcomes if r["status"] == "PENDING")
            if d1 != row["first_trading_date"]:
                d1_diff_first_trading += 1
            for h in (1, 3, 5, 10):
                yc, ycsv = realized_up(outcomes, h)
                y_check["equal" if yc == ycsv else "diff"] += 1
        else:
            d1 = d10 = None
            info["L"] = None

        # sonuç girişi (I10, M1)
        cand_pre = [first_add(f"data/outcomes_oot/{t}.csv"), first_add(f"data/outcomes_oot/raw/{t}.json"),
                    first_add(f"registry/oot/d1_rows/{t}.json")]
        cand_post = [first_add(f"data/outcomes_oot/{t}.csv"), first_add(f"data/outcomes_oot/raw/{t}.json")]
        n_zip_pre = n_zip_post = 0
        if d1 and d10:
            for zd, kind, path in zips:
                if d1 <= zd <= d10:
                    n_zip_pre += 1
                    cand_pre.append(first_add(path))
                if d1 < zd <= d10:
                    n_zip_post += 1
                    cand_post.append(first_add(path))
        ingest_pre, ok_pre = dag_min([c for c in cand_pre if c])
        ingest_post, ok_post = dag_min([c for c in cand_post if c])
        ingest_proof_pre = proof_for(ingest_pre, proofs)
        ingest_proof_post = proof_for(ingest_post, proofs)
        info["ingest_pre_listing"] = ingest_pre
        info["ingest_post_d1"] = ingest_post
        info["ingest_dag_total_order"] = bool(ok_pre and ok_post)
        info["n_zip_terms"] = [n_zip_pre, n_zip_post]
        info["ingest_pre_proof_created_at"] = ingest_proof_pre["created_at"] if ingest_proof_pre else None
        info["ingest_post_proof_created_at"] = ingest_proof_post["created_at"] if ingest_proof_post else None
        ingest_info[(ingest_pre[:7] if ingest_pre else None, ingest_post[:7] if ingest_post else None)] += 1

        # sınıf ve durum: INDEX'in 27 modeli
        classes = {}
        cells = {}
        record_files = {}
        for m in index_models:
            p, rec, cell = record_for_model(preds, m)
            rec_commit = first_add(str(p.relative_to(ROOT))) if p else None
            rec_proof = proof_for(rec_commit, proofs)
            terms = {
                "model_before_ingest": bool(ingest_pre and is_ancestor(model_commit[m], ingest_pre)),
                "model_proof": model_proof[m] is not None,
                "record_before_ingest": bool(rec_commit and ingest_pre and is_ancestor(rec_commit, ingest_pre)),
                "proof_order": bool(rec_proof and ingest_proof_pre and rec_proof["created_at"] < ingest_proof_pre["created_at"]),
                "cohort_gate": gate_ok(m, ingest_pre, ingest_proof_pre),
                "ingest_committed": ingest_pre is not None,
            }
            cls = "OOT_BLIND" if all(terms.values()) else "OOT_RETRO"
            class_by_model[m][cls] += 1
            if cell is None:
                st = "SKIPPED"
            elif cell["status"] == "REFUSED":
                st = "REFUSED"
            elif cell["status"] == "NOT_APPLICABLE_REGIME":
                st = "NOT_APPLICABLE_REGIME"
            elif outcomes is None:
                st = "PENDING"
            else:
                if m in HAZARD_MODELS:
                    realized = info["L"] is not None
                    unavailable = False
                else:
                    hs = [5, 10] if m in C_MODELS else [1, 3, 5, 10]
                    realized = any(realized_return(outcomes, h) is not None for h in hs)
                    unavailable = all(any(int(r["h"]) == h and r["status"] == "TARGET_UNAVAILABLE" for r in outcomes) for h in hs)
                st = "SCORED" if realized else ("TARGET_UNAVAILABLE" if unavailable else "PENDING")
            status_by_model[m][st] += 1
            classes[m] = {"class": cls, "terms": terms, "status": st,
                          "record_file": p.name if p else None, "record_commit": rec_commit[:7] if rec_commit else None,
                          "record_proof_created_at": rec_proof["created_at"] if rec_proof else None}
            cells[m] = cell
            record_files[m] = (p, rec)
        info["classes"] = classes
        # karşılaştırıcılar: modeli içeren kaydın `comparators` bloğu boşsa (delta kaydı) üyenin ilk etkin kaydından
        comps = None
        for p, rec in preds:
            if rec.get("comparators"):
                comps = rec["comparators"]
                break
        info["_comparators"] = comps
        info["_comparators_from_first_record"] = bool(preds and preds[0][1].get("comparators"))

        # POST_D1
        pd_commit = first_add(str(pd_path.relative_to(ROOT))) if pd_path else None
        pd_proof = proof_for(pd_commit, proofs)
        extra = {"d1_rows_sha_matches_record": False, "d1_zip_pins_match_manifest": False,
                 "d1_zip_sha_matches_outcomes_h1": False, "d1_rows_before_ingest": False,
                 "base_record_is_primary": False}
        d1p = ROOT / "registry" / "oot" / "d1_rows" / f"{t}.json"
        if pdrec and d1p.exists():
            d1doc = json.loads(d1p.read_text(encoding="utf-8"))
            extra["d1_rows_sha_matches_record"] = canonical_sha(d1p) == pdrec["d1_rows"]["sha256"] and pdrec["d1_rows"]["file"] == f"registry/oot/d1_rows/{t}.json"
            dd = d1doc["d1"]["session_date"]
            extra["d1_zip_pins_match_manifest"] = all(
                (dd, k) in pins and pins[(dd, k)]["sha256"] == d1doc["d1"][k]["sha256"] and pins[(dd, k)]["url"] == d1doc["d1"][k]["url"]
                for k in ("thb", "thm"))
            if outcomes:
                h1 = next(r for r in outcomes if int(r["h"]) == 1)
                extra["d1_zip_sha_matches_outcomes_h1"] = (h1["session_date"] == dd and h1["thb_sha256"] == d1doc["d1"]["thb"]["sha256"]
                                                            and h1["thm_sha256"] == d1doc["d1"]["thm"]["sha256"])
            d1c = first_add(f"registry/oot/d1_rows/{t}.json")
            extra["d1_rows_before_ingest"] = bool(d1c and ingest_post and is_ancestor(d1c, ingest_post))
            base_p = preds[0][0] if preds else None
            extra["base_record_is_primary"] = bool(base_p and pdrec["base_record"]["file"] == str(base_p.relative_to(ROOT))
                                                   and pdrec["base_record"]["sha256"] == hashlib.sha256(base_p.read_bytes()).hexdigest())
        terms_pd = {
            "model_before_ingest": bool(ingest_post and is_ancestor(model_commit[POST_D1_MODEL], ingest_post)),
            "model_proof": model_proof[POST_D1_MODEL] is not None,
            "record_before_ingest": bool(pd_commit and ingest_post and is_ancestor(pd_commit, ingest_post)),
            "proof_order": bool(pd_proof and ingest_proof_post and pd_proof["created_at"] < ingest_proof_post["created_at"]),
            "cohort_gate": gate_ok("ceiling_hazard_v0", ingest_post, ingest_proof_post),  # L1: taban kaydın modeli
            "ingest_committed": ingest_post is not None,
            **extra,
        }
        cls_pd = "OOT_BLIND" if all(terms_pd.values()) else "OOT_RETRO"
        class_by_model[POST_D1_MODEL][cls_pd] += 1
        pcell = pdrec["models"][0] if pdrec else None
        if pcell is None:
            st = "SKIPPED"
        elif pcell["status"] == "REFUSED":
            st = "REFUSED"
        elif pcell["status"] == "NOT_APPLICABLE":
            st = "NOT_APPLICABLE:" + str((pcell.get("refusal") or {}).get("code") or (pcell.get("not_applicable") or {}).get("code"))
        elif pcell["status"] == "NOT_APPLICABLE_REGIME":
            st = "NOT_APPLICABLE_REGIME"
        elif outcomes is None or info["L"] is None:
            st = "PENDING"
        else:
            st = "SCORED"
        status_by_model[POST_D1_MODEL][st] += 1
        info["post_d1"] = {"class": cls_pd, "terms": terms_pd, "status": st, "record_commit": pd_commit[:7] if pd_commit else None,
                           "record_proof_created_at": pd_proof["created_at"] if pd_proof else None,
                           "d1_ceiling_label_in_record": (pdrec or {}).get("d1", {}).get("ceiling_close_D1")}
        info["_cells"] = cells
        info["_pdrec"] = pdrec
        info["_outcomes"] = outcomes
        per_member[t] = info

    # ---------------------------------------------------------------- hücre üreticileri
    def get_pair_inputs(t, model, comp, comp_src):
        """İki taraf da OOT_BLIND ve PREDICTED ise (model hücresi, karşılaştırıcı hücresi), aksi hâlde (None, sebep)."""
        info = per_member[t]
        if info["classes"][model]["class"] != "OOT_BLIND":
            return None, "model_not_blind"
        cell = info["_cells"][model]
        if cell is None:
            return None, "model_no_record"
        if cell["status"] != "PREDICTED":
            return None, f"model_{cell['status']}"
        if comp_src == "comparators":
            ccell = (info["_comparators"] or {}).get(comp)
            if ccell is None:
                return None, "comparator_missing"
        else:
            if info["classes"][comp]["class"] != "OOT_BLIND":
                return None, "comparator_not_blind"
            ccell = info["_cells"][comp]
            if ccell is None:
                return None, "comparator_no_record"
        if ccell["status"] != "PREDICTED":
            return None, f"comparator_{ccell['status']}"
        return (cell, ccell), None

    def base_pair(t):
        info = per_member[t]
        return {"ticker": t, "block": info["block"], "alloc_regime": info["alloc_regime"]}

    def hazard_cell(model, comp, comp_src, metric):
        pairs, excluded = [], Counter()
        for t in sealed:
            got, why = get_pair_inputs(t, model, comp, comp_src)
            if got is None:
                excluded[why] += 1
                continue
            cell, ccell = got
            L = per_member[t]["L"]
            if L is None:
                excluded["L_unknown"] += 1
                continue
            Sm, Sr = cell["output"]["S"], ccell["output"]["S"]
            if metric == "RPS":
                lm, lr = rps(Sm, L), rps(Sr, L)
            elif metric == "Brier_k10":
                lm, lr = brier_k(Sm, L, 10), brier_k(Sr, L, 10)
            else:
                raise ValueError(metric)
            pairs.append({**base_pair(t), "L": L, "S5_model": Sm[4], "S10_model": Sm[9], "loss_model": lm, "loss_rule": lr, "d": lm - lr})
        s = cell_summary(pairs)
        if pairs:
            s["calibration"] = {
                "mean_S5_model": float(np.mean([p["S5_model"] for p in pairs])),
                "observed_P_L_ge_5": float(np.mean([1.0 if p["L"] >= 5 else 0.0 for p in pairs])),
                "mean_S10_model": float(np.mean([p["S10_model"] for p in pairs])),
                "observed_P_L_ge_10": float(np.mean([1.0 if p["L"] >= 10 else 0.0 for p in pairs])),
            }
        return {"model": model, "metric": metric, "horizon": None, "comparator": comp, "comparator_source": comp_src,
                "excluded": dict(excluded), **s}

    def mae_cell(model, horizon, comp, comp_src):
        pairs, excluded = [], Counter()
        h = int(horizon[1:])
        for t in sealed:
            got, why = get_pair_inputs(t, model, comp, comp_src)
            if got is None:
                excluded[why] += 1
                continue
            cell, ccell = got
            truth = realized_return(per_member[t]["_outcomes"], h)
            if truth is None:
                excluded["target_unavailable"] += 1
                continue
            pm, pr = cell["output"][horizon]["return"], ccell["output"][horizon]["return"]
            lm, lr = abs(pm - truth), abs(pr - truth)
            pairs.append({**base_pair(t), "truth": truth, "pred_model": pm, "pred_rule": pr, "loss_model": lm, "loss_rule": lr, "d": lm - lr})
        return {"model": model, "metric": "MAE", "horizon": horizon, "comparator": comp, "comparator_source": comp_src,
                "excluded": dict(excluded), **cell_summary(pairs)}

    def pup_cell(model, horizon, comp, comp_src):
        pairs, excluded = [], Counter()
        h = int(horizon[1:])
        for t in sealed:
            got, why = get_pair_inputs(t, model, comp, comp_src)
            if got is None:
                excluded[why] += 1
                continue
            cell, ccell = got
            y, _ = realized_up(per_member[t]["_outcomes"], h)
            if y is None:
                excluded["target_unavailable"] += 1
                continue
            pm, pr = cell["output"][horizon]["p_up"], ccell["output"][horizon]["p_up"]
            lm, lr = brier_pup(pm, y), brier_pup(pr, y)
            pairs.append({**base_pair(t), "Y_h": y, "y4_event": 1 - y, "p_up_model": pm, "p_up_rule": pr, "loss_model": lm, "loss_rule": lr, "d": lm - lr})
        s = cell_summary(pairs)
        if pairs:
            s["calibration"] = {
                "mean_P_event_model": float(np.mean([1.0 - p["p_up_model"] for p in pairs])),
                "observed_event_rate": float(np.mean([p["y4_event"] for p in pairs])),
                "n_events": int(sum(p["y4_event"] for p in pairs)),
            }
        return {"model": model, "metric": "Brier_p_up", "horizon": horizon, "comparator": comp, "comparator_source": comp_src,
                "target": f"y = 1 - Y_{horizon} (kapanış ≤ arz fiyatı; C1)", "excluded": dict(excluded), **s}

    cells_out = {"old_primary": {}, "v1": {}, "c": {}, "post_d1": {}}
    for model, metric, horizon, comp, comp_src in OLD_PRIMARY_CELLS:
        key = f"{model}|{metric}{('_' + horizon) if horizon else ''}|vs|{comp}"
        cells_out["old_primary"][key] = hazard_cell(model, comp, comp_src, "RPS") if metric == "RPS" else mae_cell(model, horizon, comp, comp_src)
    for model, metric, comp, comp_src, label in V1_CELLS:
        key = f"{model}|{metric}|vs|{comp}"
        cells_out["v1"][key] = {"label": label, **hazard_cell(model, comp, comp_src, metric)}
    cells_out["v1"]["ceiling_hazard_v0|RPS|vs|base_km_expanding"] = {"label": "SPEC_HAZARD_V1 §6.1 ilk satır (= eski hücre 5)",
                                                                       **cells_out["old_primary"]["ceiling_hazard_v0|RPS|vs|base_km_expanding"]}
    for model, horizon, comp, comp_src, label in C_CELLS:
        key = f"{model}|Brier_{horizon}|vs|{comp}"
        cells_out["c"][key] = {"label": label, **pup_cell(model, horizon, comp, comp_src)}

    # POST_D1: j = 1 koşullu RPS vs ceiling_hazard_v0 koşullu (S_k / S_1, S2 kaydından)
    pairs, excluded, cond_check = [], Counter(), Counter()
    for t in sealed:
        info = per_member[t]
        pdrec = info["_pdrec"]
        if info["post_d1"]["class"] != "OOT_BLIND":
            excluded["model_not_blind"] += 1
            continue
        pcell = pdrec["models"][0]
        if pcell["status"] != "PREDICTED":
            excluded[f"model_{pcell['status']}"] += 1
            continue
        if info["classes"]["ceiling_hazard_v0"]["class"] != "OOT_BLIND":
            excluded["comparator_not_blind"] += 1
            continue
        hcell = info["_cells"]["ceiling_hazard_v0"]
        if hcell["status"] != "PREDICTED":
            excluded[f"comparator_{hcell['status']}"] += 1
            continue
        L = info["L"]
        if L is None:
            excluded["L_unknown"] += 1
            continue
        if L < 1:
            excluded["L_lt_1"] += 1
            continue
        S = hcell["output"]["S"]
        S_cond_rule = {str(k): S[k - 1] / S[0] for k in range(2, 11)}
        rec_cond = pdrec["comparators_conditional"]["ceiling_hazard_v0"]["S_cond"]
        cond_check["equal" if all(abs(S_cond_rule[k] - rec_cond[k]) <= TOL_COND for k in S_cond_rule) else "diff"] += 1
        S_cond_model = pcell["output"]["conditional_j1"]["S_cond"]
        lm, lr = cond_rps_j1(S_cond_model, L), cond_rps_j1(S_cond_rule, L)
        pairs.append({**base_pair(t), "L": L, "loss_model": lm, "loss_rule": lr, "d": lm - lr})
    cells_out["post_d1"]["post_d1_hazard_v0|RPS_cond_j1|vs|ceiling_hazard_v0_cond"] = {
        "model": POST_D1_MODEL, "metric": "RPS_cond_j1", "horizon": None, "comparator": "ceiling_hazard_v0",
        "comparator_source": "base_record S_k/S_1 (yeniden hesap; kayıttaki comparators_conditional ile eşitlik sayıldı)",
        "comparator_record_equality": dict(cond_check), "excluded": dict(excluded), **cell_summary(pairs)}

    # ---------------------------------------------------------------- seçim kuralları (§5.5 × 2); k3 scores.json near_era
    scores = json.loads((ROOT / "scores" / "scores.json").read_text(encoding="utf-8"))
    near = {}
    for m in scores["models"]:
        ne = (m.get("backtest") or {}).get("near_era")
        if ne:
            near[m["model_id"]] = {k: ne.get(k) for k in ("comparator", "metric", "diff", "ci95", "label", "n", "n_blocks", "tolerance")}

    def passes(cell):
        return cell["n"] >= 30 and cell["ci95"] is not None and cell["ci95"][1] < 0

    v1_rule = {"candidates": {}, "rule": "SPEC_HAZARD_V1 §5.5: k1 kasa birincil (RPS − base_km_expanding) 'geçiyor'; k2 RPS − ceiling_hazard_v0 aralık üst ucu < 0; k3 yakın dönem 'bozuyor' değil; uygunlar arasında kasa RPS noktası en düşük; |Δ| < 0.002 → en basit (clip < real < pooled); uygun yok → ceiling_hazard_v0"}
    for i, m in enumerate(V1_CANDIDATES):
        c1 = cells_out["v1"][f"{m}|RPS|vs|base_km_expanding"]
        c2 = cells_out["v1"][f"{m}|RPS|vs|ceiling_hazard_v0"]
        ne = near.get(m)
        k1 = passes(c1)
        k2 = c2["ci95"] is not None and c2["ci95"][1] < 0
        k3 = ne is not None and ne["label"] != "bozuyor"
        v1_rule["candidates"][m] = {"k1": k1, "k1_cell": {"n": c1["n"], "mean_diff": c1["mean_diff"], "ci95": c1["ci95"], "verdict": c1["verdict"]},
                                    "k2": k2, "k2_cell": {"n": c2["n"], "mean_diff": c2["mean_diff"], "ci95": c2["ci95"]},
                                    "k3": k3, "k3_near_era": ne, "eligible": k1 and k2 and k3,
                                    "vault_rps_point": c1["mean_loss_model"], "simplicity_rank": i}
    elig = [m for m in V1_CANDIDATES if v1_rule["candidates"][m]["eligible"]]
    if elig:
        best = min(elig, key=lambda m: v1_rule["candidates"][m]["vault_rps_point"])
        ties = [m for m in elig if abs(v1_rule["candidates"][m]["vault_rps_point"] - v1_rule["candidates"][best]["vault_rps_point"]) < TIE_TOL]
        chosen = min(ties, key=lambda m: v1_rule["candidates"][m]["simplicity_rank"])
    else:
        chosen = "ceiling_hazard_v0"
    v1_rule["eligible"] = elig
    v1_rule["result"] = chosen
    # bilgi: ortak kesişimde RPS noktaları
    common = None
    for m in V1_CANDIDATES:
        s = {p["ticker"] for p in cells_out["v1"][f"{m}|RPS|vs|base_km_expanding"]["pairs"]}
        common = s if common is None else common & s
    v1_rule["info_common_set_n"] = len(common)
    v1_rule["info_rps_points_on_common_set"] = {
        m: float(np.mean([p["loss_model"] for p in cells_out["v1"][f"{m}|RPS|vs|base_km_expanding"]["pairs"] if p["ticker"] in common]))
        for m in V1_CANDIDATES + []}
    v1_rule["info_rps_points_on_common_set"]["ceiling_hazard_v0"] = float(np.mean(
        [p["loss_model"] for p in cells_out["old_primary"]["ceiling_hazard_v0|RPS|vs|base_km_expanding"]["pairs"] if p["ticker"] in common]))
    v1_rule["info_rps_points_on_common_set"]["base_km_expanding"] = float(np.mean(
        [p["loss_rule"] for p in cells_out["old_primary"]["ceiling_hazard_v0|RPS|vs|base_km_expanding"]["pairs"] if p["ticker"] in common]))

    c_rule = {"candidates": {}, "rule": "SPEC_C_V0 §5.5: k1 kasa birincil (D10 Brier − base_rate) 'geçiyor'; k2 D10 Brier − v1_5_h99 aralık üst ucu < 0; k3 pooled: yakın dönem (pooled − h99) 'bozuyor' değil, h99/addsale: yakın dönem − base_rate aralığı tamamen 0'ın üstünde değil; uygunlar arasında kasa D10 Brier noktası en düşük; |Δ| < 0.002 → en basit (addsale < h99 < pooled); uygun yok → hiçbir (C) modeli öne çıkarılmaz"}
    simplicity = {"fall_d10_v0_addsale": 0, "fall_d10_v0_h99": 1, "fall_d10_v0_pooled": 2}
    for m in C_CANDIDATES:
        c1 = cells_out["c"][f"{m}|Brier_D10|vs|base_rate"]
        c2 = cells_out["c"][f"{m}|Brier_D10|vs|v1_5_h99"]
        ne = near.get(m)
        k1 = passes(c1)
        k2 = c2["ci95"] is not None and c2["ci95"][1] < 0
        if m == "fall_d10_v0_pooled":
            k3 = ne is not None and ne["comparator"] == "fall_d10_v0_h99" and ne["label"] != "bozuyor"
        else:
            k3 = ne is not None and ne["comparator"] == "base_rate" and ne["ci95"] is not None and not (ne["ci95"][0] > 0)
        c_rule["candidates"][m] = {"k1": k1, "k1_cell": {"n": c1["n"], "mean_diff": c1["mean_diff"], "ci95": c1["ci95"], "verdict": c1["verdict"]},
                                   "k2": k2, "k2_cell": {"n": c2["n"], "mean_diff": c2["mean_diff"], "ci95": c2["ci95"]},
                                   "k3": k3, "k3_near_era": ne, "eligible": k1 and k2 and k3,
                                   "vault_brier_d10_point": c1["mean_loss_model"], "simplicity_rank": simplicity[m]}
    elig = [m for m in C_CANDIDATES if c_rule["candidates"][m]["eligible"]]
    if elig:
        best = min(elig, key=lambda m: c_rule["candidates"][m]["vault_brier_d10_point"])
        ties = [m for m in elig if abs(c_rule["candidates"][m]["vault_brier_d10_point"] - c_rule["candidates"][best]["vault_brier_d10_point"]) < TIE_TOL]
        chosen = min(ties, key=lambda m: c_rule["candidates"][m]["simplicity_rank"])
    else:
        chosen = None
    c_rule["eligible"] = elig
    c_rule["result"] = chosen if chosen else "kasada geçen aday yok"
    common = None
    for m in C_CANDIDATES:
        s = {p["ticker"] for p in cells_out["c"][f"{m}|Brier_D10|vs|base_rate"]["pairs"]}
        common = s if common is None else common & s
    c_rule["info_common_set_n"] = len(common)
    c_rule["info_brier_points_on_common_set"] = {
        m: float(np.mean([p["loss_model"] for p in cells_out["c"][f"{m}|Brier_D10|vs|base_rate"]["pairs"] if p["ticker"] in common]))
        for m in C_CANDIDATES}
    c_rule["info_brier_points_on_common_set"]["base_rate"] = float(np.mean(
        [p["loss_rule"] for p in cells_out["c"]["fall_d10_v0_h99|Brier_D10|vs|base_rate"]["pairs"] if p["ticker"] in common]))
    c_rule["info_brier_points_on_common_set"]["v1_5_h99"] = float(np.mean(
        [p["loss_model"] for p in cells_out["c"]["v1_5_h99|Brier_D10|vs|base_rate"]["pairs"] if p["ticker"] in common]))

    # başarısızlık tanımları (bilgi; §6.4 sözcükleri)
    def fail_flags_v1(m):
        c1 = cells_out["v1"][f"{m}|RPS|vs|base_km_expanding"]
        c2 = cells_out["v1"][f"{m}|RPS|vs|ceiling_hazard_v0"]
        cal = c1.get("calibration", {})
        return {
            "a_v0dan_kotu": bool(c2["ci95"] and c2["ci95"][0] > 0),
            "b_bozuyor": bool(near.get(m) and near[m]["label"] == "bozuyor"),
            "d_duzey_kaymasi": bool(cal and abs(cal["mean_S5_model"] - cal["observed_P_L_ge_5"]) > 0.15),
            "e_beklentiden_cok_iyi": bool(c1["mean_diff"] is not None and (c1["mean_diff"] < -0.10 or (c1["ci95"] and c1["ci95"][1] < -0.06))),
        }
    v1_rule["failure_flags"] = {m: fail_flags_v1(m) for m in V1_CANDIDATES}
    v1_rule["failure_flags"]["ceiling_hazard_v1_pooled"]["c_ozellikler_bilgi_eklemiyor"] = bool(
        cells_out["v1"]["ceiling_hazard_v1_pooled|RPS|vs|ceiling_hazard_v1_pooled@INF"]["mean_diff"] >= 0)

    def fail_flags_c(m):
        c1 = cells_out["c"][f"{m}|Brier_D10|vs|base_rate"]
        cal = c1.get("calibration", {})
        return {
            "a_taban_orandan_kotu": bool(c1["ci95"] and c1["ci95"][0] > 0),
            "b_bozuyor": bool(m == "fall_d10_v0_pooled" and near.get(m) and near[m]["label"] == "bozuyor"),
            "d_duzey_kaymasi": bool(cal and abs(cal["mean_P_event_model"] - cal["observed_event_rate"]) > 0.15),
            "e_beklentiden_cok_iyi": bool(c1["mean_diff"] is not None and (c1["mean_diff"] < -0.08 or (c1["ci95"] and c1["ci95"][1] < -0.04))),
        }
    c_rule["failure_flags"] = {m: fail_flags_c(m) for m in C_CANDIDATES}
    c_rule["failure_flags"]["fall_d10_v0_addsale"]["c_ek_satis_bilgi_eklemiyor"] = bool(cells_out["c"]["fall_d10_v0_addsale|Brier_D10|vs|base_rate"]["mean_diff"] >= 0)
    c_rule["failure_flags"]["fall_d10_v0_pooled"]["c_ozellikler_bilgi_eklemiyor"] = bool(cells_out["c"]["fall_d10_v0_pooled|Brier_D10|vs|fall_d10_v0_pooled@ZERO"]["mean_diff"] >= 0)
    pdc = cells_out["post_d1"]["post_d1_hazard_v0|RPS_cond_j1|vs|ceiling_hazard_v0_cond"]
    post_d1_flags = {"M12_beklentiden_cok_iyi": bool(pdc["mean_diff"] is not None and (pdc["mean_diff"] < -0.08 or (pdc["ci95"] and pdc["ci95"][1] < -0.045)))}

    # ---------------------------------------------------------------- özet
    def strip(c):
        return {k: v for k, v in c.items() if k != "pairs"}

    out = {
        "task": "BORSAI_FAZ7_FABLE_VAULT_RECOMPUTE_20260929",
        "head": head,
        "borsai_imported": "borsai" in sys.modules,
        "definitions": {
            "class_oot": "SPEC_OOT §2 + I13 + L1: model commit'i (push kanıtlı) ve modeli içeren en erken etkin kayıt commit'i sonuç commit'inin atası; kayıt kanıtı < sonuç kanıtı; kapı model başına: her MEMBER'ın o modeli içeren kaydı ingest'in atası VE kanıtı önce. POST_D1 ek: d1_rows kanonik sha = kayıt; D_1 zip sha/URL = MANIFEST_OOT pini = sonuç h=1; base_record = üyenin ilk etkin kaydı; d1_rows commit'i ingest'in atası; kapı modeli ceiling_hazard_v0 (L1).",
            "ingest_pre_listing": "I10 + M1: min(outcomes_oot csv, raw json, d1_rows json, [D_1, D_10] tarihli repo zip'i) → VA1 beklenir",
            "ingest_post_d1": "I10 + M1: min(outcomes_oot csv, raw json, (D_1, D_10] tarihli repo zip'i); d1_rows hariç → VB beklenir",
            "primary_record": "L1/L2 + I12: o modeli içeren en erken etkin PREDICTION kaydı (eski 19 model: ilk kayıt; 8 yeni model: delta kaydı)",
            "comparators": "kural değerleri üyenin ilk etkin kaydındaki `comparators` bloğundan (donmuş H99 değerleri); delta kaydında blok boş",
            "return_point": "kayıttaki output[Dh].return (kırpılmışsa kırpılmış değer)",
            "MAE_loss": "|return − R_h|, R_h = data/outcomes_oot csv (Decimal → float)",
            "RPS": "(1/10) Σ_{k=1..10} (S_k − 1[L ≥ k])², L = ardışık ceiling_close = 1 sayısı D_1'den",
            "Brier_k10": "(S_10 − 1[L ≥ 10])²",
            "Brier_p_up": "(p_up(D_h) − Y_h)², Y_h = 1[R_h > 0] (SPEC_SCORING §3; C1: kapanış ≤ arz → y = 1 − Y_h = 1); (1 − p_up) − y ile sayısal olarak aynı",
            "RPS_cond_j1": "(1/9) Σ_{k=2..10} (S_cond_k − 1[L ≥ k])², yalnız L ≥ 1; karşılaştırıcı S_k/S_1 (S2 kaydı)",
            "diff": "model − kural (negatif = model iyi)",
            "bootstrap": f"blok = gerçekleşen D_1 ayı; ids sıralı; rng.choice(ids, size=len(ids), replace=True); B={B_BOOT}; numpy Generator(PCG64({SEED})); np.percentile linear [2.5, 97.5]; koşul n ≥ {MIN_N} ve ≥ {MIN_BLOCKS} blok",
            "verdict": "n<10 yok; 10≤n<30 'yetersiz örnek'; n≥30 aralık yok 'aralık için yetersiz'; üst<0 'geçiyor (zaman-dışı terazide)'; alt>0 'geçemiyor (zaman-dışı terazide)'; aksi 'ayırt edilemiyor'",
            "selection_point": "kasa RPS/Brier noktası = adayın kendi birincil hücre çiftlerindeki ortalama model kaybı (aday kümeleri farklı olabilir; ortak kesişim değerleri bilgi olarak ayrıca)",
            "near_era_k3": "scores/scores.json models[].backtest.near_era (bu görevden önce yazılmış; yalnız etiket/aralık okunur)",
        },
        "counters": counters,
        "gate": {
            "n_model_record_commit_sets": {m: [c[:7] for c in cs] for m, cs in gate_commit_sets.items()},
            "n_members_without_model_record": dict(n_members_without_model_record),
            "n_sealed_D1_differs_from_first_trading_date": d1_diff_first_trading,
            "n_repo_zips_in_cohort_window": sum(1 for zd, _, _ in zips if "2020-01-01" <= zd <= "2023-12-31"),
            "ingest_commit_pairs": {f"{k[0]}|{k[1]}": v for k, v in ingest_info.items()},
            "record_proof_created_at_by_commit": {c[:7]: (p or {}).get("created_at") for c, p in rec_proof_by_commit.items()},
        },
        "model_commits": {m: {"commit": c[:7], "proof_created_at": (model_proof[m] or {}).get("created_at")} for m, c in model_commit.items()},
        "L_distribution_sealed": {str(k): v for k, v in sorted(L_dist.items(), key=lambda kv: (kv[0] is None, kv[0]))},
        "Y_h_csv_vs_R_h_check": dict(y_check),
        "class_counts_total": dict(sum(class_by_model.values(), Counter())),
        "class_counts_index_27x64": dict(sum((class_by_model[m] for m in index_models), Counter())),
        "class_counts_post_d1": dict(class_by_model[POST_D1_MODEL]),
        "class_by_model": {m: dict(c) for m, c in class_by_model.items()},
        "status_by_model": {m: dict(sorted(c.items())) for m, c in status_by_model.items()},
        "status_totals_index_27x64": dict(sum((status_by_model[m] for m in index_models), Counter())),
        "cells": cells_out,
        "cells_summary": {grp: {k: strip(c) for k, c in cs.items()} for grp, cs in cells_out.items()},
        "selection_rules": {"v1": v1_rule, "c": c_rule, "post_d1_flags": post_d1_flags},
        "members": {t: {k: v for k, v in info.items() if not k.startswith("_")} for t, info in per_member.items()},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    # ekrana yalnız sayılar
    print("HEAD", head[:7], "| borsai import:", out["borsai_imported"])
    print("counters", counters)
    print("class total", out["class_counts_total"], "| INDEX 27×64", out["class_counts_index_27x64"], "| post_d1", out["class_counts_post_d1"])
    print("status INDEX totals", out["status_totals_index_27x64"])
    for m in ALL_MODELS:
        print(f"  {m:30s} class={dict(class_by_model[m])} status={dict(sorted(status_by_model[m].items()))}")
    print("gate", {k: v for k, v in out["gate"].items() if k != "n_model_record_commit_sets"})
    print("L dist", out["L_distribution_sealed"], "| Y check", out["Y_h_csv_vs_R_h_check"])
    for grp, cs in cells_out.items():
        print(f"--- {grp}")
        for key, c in cs.items():
            print(f"CELL {key}: n={c['n']} blocks={c['n_blocks']} mean_diff={c['mean_diff']!r} ci={c['ci95']} W/L/T={c['wins']}/{c['losses']}/{c['ties']} verdict={c['verdict']} excl={c['excluded']} loss_model={c['mean_loss_model']} loss_rule={c['mean_loss_rule']}")
            if c.get("calibration"):
                print("     calib", c["calibration"])
            print("     by_year", {y: (v['n'], round(v['mean_diff'], 6)) for y, v in c["by_year"].items()},
                  "| by_regime", {y: (v['n'], round(v['mean_diff'], 6)) for y, v in c["by_alloc_regime"].items()})
    print("--- selection v1:", {m: {k: v for k, v in d.items() if k in ("k1", "k2", "k3", "eligible", "vault_rps_point")} for m, d in v1_rule["candidates"].items()})
    print("    result:", v1_rule["result"], "| common n", v1_rule["info_common_set_n"], v1_rule["info_rps_points_on_common_set"])
    print("    failure flags:", v1_rule["failure_flags"])
    print("--- selection (C):", {m: {k: v for k, v in d.items() if k in ("k1", "k2", "k3", "eligible", "vault_brier_d10_point")} for m, d in c_rule["candidates"].items()})
    print("    result:", c_rule["result"], "| common n", c_rule["info_common_set_n"], c_rule["info_brier_points_on_common_set"])
    print("    failure flags:", c_rule["failure_flags"])
    print("--- post_d1 flags:", post_d1_flags)
    return 0


if __name__ == "__main__":
    sys.exit(main())

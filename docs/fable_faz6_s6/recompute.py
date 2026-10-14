#!/usr/bin/env python3
"""BORSAI_FAZ6_FABLE_S6_RECOMPUTE — eski kohort açık kümesi için bağımsız yeniden hesap.

Kurallar: `borsai` import edilmez; tanımlar şartnamelerden (SPEC_OOT_PRE_H99_V0 §2/§6,
KARARLAR D5/D6, SPEC_DEVIATIONS I10–I13/I22/I23, SPEC_SCORING §2/§3/§7/§8,
SPEC_CEILING_PATH_V0 §4/§5/§7, SPEC_POST_D1_V0 §4). Girdiler yalnız git DAG'ı,
registry/push_proofs, registry/oot/{cohort_pre_h99.csv,records,post_d1,d1_rows},
data/outcomes_oot/*.csv ve data/raw/bist/MANIFEST_OOT.csv.

Çıktı: docs/fable_faz6_s6/BAGIMSIZ.json. Kasadaki (SEALED) hiçbir kod yazılmaz.
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
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "BAGIMSIZ.json"

B_BOOT = 4000
SEED = 20260921
MIN_N = 10
MIN_BLOCKS = 6
TOL_COND = 1e-12

PRE_LISTING_MODELS = [
    "v1_5_h99", "base_always_ceiling", "base_train_median", "base_train_mean", "base_zero",
    "base_rate", "base_last10_rate", "v1_6_h99", "v1_5_market20_v0", "pb_v0",
    "ceiling_hazard_v0", "ceiling_hazard_v0@INF", "pb_ceiling_v0", "pb_ceiling_v0@INF",
    "base_km_expanding", "base_km_last10", "ceiling_path_v0", "ceiling_path_v0@INF",
    "pb_ceiling_path_v0",
]
POST_D1_MODEL = "post_d1_hazard_v0"
RETURN_MODELS = {"v1_5_h99", "v1_6_h99", "v1_5_market20_v0", "pb_v0", "ceiling_path_v0",
                 "ceiling_path_v0@INF", "pb_ceiling_path_v0", "base_always_ceiling",
                 "base_train_median", "base_train_mean", "base_zero"}
PUP_ONLY_MODELS = {"base_rate", "base_last10_rate"}
HAZARD_MODELS = {"ceiling_hazard_v0", "ceiling_hazard_v0@INF", "pb_ceiling_v0",
                 "pb_ceiling_v0@INF", "base_km_expanding", "base_km_last10"}

# 8 listeleme öncesi birincil hücre (SPEC_OOT §6, I11, SPEC_CEILING_PATH_V0 §5) + POST_D1 (SPEC_POST_D1_V0 §4)
PRIMARY_CELLS = [
    # (model, metrik, ufuk, karşılaştırıcı, karşılaştırıcı kaynağı)
    ("v1_5_h99", "MAE", "D5", "base_train_median", "comparators"),
    ("v1_6_h99", "MAE", "D10", "v1_5_h99", "model_cell"),
    ("v1_5_market20_v0", "MAE", "D5", "v1_5_h99", "model_cell"),
    ("pb_v0", "MAE", "D5", "base_train_median", "comparators"),
    ("ceiling_hazard_v0", "RPS", None, "base_km_expanding", "comparators"),
    ("pb_ceiling_v0", "RPS", None, "base_km_expanding", "comparators"),
    ("ceiling_path_v0", "MAE", "D5", "base_train_median", "comparators"),
    ("pb_ceiling_path_v0", "MAE", "D5", "base_train_median", "comparators"),
]


# ---------------------------------------------------------------- git yardımcıları
def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def is_ancestor(a: str, b: str) -> bool:
    r = subprocess.run(["git", "merge-base", "--is-ancestor", a, b], cwd=ROOT, capture_output=True)
    if r.returncode not in (0, 1):
        raise RuntimeError(f"merge-base hatası: {r.stderr.decode()}")
    return r.returncode == 0


def add_commits(path: str) -> list[str]:
    """Yolu (ya da altındaki bir dosyayı) ekleyen commit'ler, eskiden yeniye."""
    out = git("log", "--diff-filter=A", "--format=%H", "--reverse", "--", path)
    return [x for x in out.splitlines() if x]


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
        proofs.append({"file": p.name, "sha": d["proven_commit_sha"], "created_at": d["created_at"],
                       "method": d.get("method")})
    return proofs


def proof_for(commit: str, proofs: list[dict]) -> dict | None:
    """Commit'i kapsayan (kendisi ya da torunu için alınmış) en erken kanıt."""
    cands = [p for p in proofs if p["sha"] == commit or is_ancestor(commit, p["sha"])]
    if not cands:
        return None
    return min(cands, key=lambda p: p["created_at"])


# ---------------------------------------------------------------- kohort, kayıtlar, sonuçlar
def read_cohort() -> list[dict]:
    with (ROOT / "registry" / "oot" / "cohort_pre_h99.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def active_rows(rows: list[dict]) -> dict[str, dict]:
    """Ticker başına en son etkin satır (I5: CANCELLED en son etkin satırı düşürür)."""
    active: dict[str, dict] = {}
    for r in rows:
        t = r["ticker"]
        if r["status"] == "CANCELLED":
            active.pop(t, None)
        else:
            active[t] = r
    return active


def primary_record(dir_: Path) -> tuple[Path | None, dict | None, int, int]:
    """I12: en erken etkin PREDICTION kaydı. (yol, belge, kayıt sayısı, iptal sayısı)"""
    files = sorted(dir_.glob("*.json")) if dir_.exists() else []
    docs = [(p, json.loads(p.read_text(encoding="utf-8"))) for p in files]
    cancelled = {d.get("cancels") for _, d in docs if d.get("record_type") == "CANCELLATION"}
    n_cancel = sum(1 for _, d in docs if d.get("record_type") == "CANCELLATION")
    preds = [(p, d) for p, d in docs if d.get("record_type") == "PREDICTION" and p.name not in cancelled
             and hashlib.sha256(p.read_bytes()).hexdigest() not in cancelled]
    preds.sort(key=lambda pd: (pd[1].get("recorded_at_utc", ""), pd[0].name))
    if not preds:
        return None, None, len(docs), n_cancel
    return preds[0][0], preds[0][1], len(docs), n_cancel


def read_outcomes(ticker: str) -> list[dict] | None:
    p = ROOT / "data" / "outcomes_oot" / f"{ticker}.csv"
    if not p.exists():
        return None
    with p.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if r.get("outcome_basis") != "MACHINE_EXTRACTED":
            raise RuntimeError(f"{ticker}: outcome_basis beklenmedik")
    return rows


def streak(rows: list[dict]) -> int | None:
    """L = D_1'den başlayan ardışık tavan sayısı; ilk 0'da durur; 0'dan önce NA/eksik varsa bilinmez (E4)."""
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


def repo_zip_dates() -> list[tuple[str, str]]:
    """Repoda izlenen THB/THM zip'lerinin (tarih, tür) listesi; kohort penceresi terimi için."""
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
        return "geçiyor"
    if ci[0] > 0:
        return "geçemiyor"
    return "ayırt edilemiyor"


def cell_summary(pairs: list[dict]) -> dict:
    d = [p["d"] for p in pairs]
    blocks = [p["block"] for p in pairs]
    n = len(d)
    mean = float(np.mean(d)) if n else None
    ci = block_bootstrap_ci(d, blocks) if n else None
    by_year = defaultdict(list)
    for p in pairs:
        by_year[p["block"][:4]].append(p["d"])
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
        "pairs": pairs,
    }


# ---------------------------------------------------------------- ana akış
def main() -> int:
    head = git("rev-parse", "HEAD")
    proofs = load_proofs()
    cohort = read_cohort()
    active = active_rows(cohort)
    members = {t: r for t, r in active.items() if r["status"] == "MEMBER"}
    open_set = sorted(t for t, r in members.items() if r["vault"] != "SEALED")
    sealed_n = sum(1 for r in members.values() if r["vault"] == "SEALED")
    counters = {
        "n_member": len(members),
        "n_out_of_scope": sum(1 for r in active.values() if r["status"] == "OUT_OF_SCOPE"),
        "n_pending": sum(1 for r in active.values() if r["status"] == "PENDING"),
        "n_open": len(open_set),
        "n_sealed": sealed_n,
        "n_exposed_archive": sum(1 for r in members.values() if r["vault"] == "EXPOSED_ARCHIVE"),
        "n_exposed_codex": sum(1 for r in members.values() if r["vault"] == "EXPOSED_CODEX"),
        "n_open_by_year": dict(sorted(Counter(members[t]["year"] for t in open_set).items())),
    }
    pins = manifest_pins()
    zips = repo_zip_dates()

    # model commit'leri ve kanıtları
    model_commit = {}
    model_proof = {}
    for m in PRE_LISTING_MODELS + [POST_D1_MODEL]:
        c = first_add(f"models/{m}.json")
        if c is None:
            raise RuntimeError(f"model dosyası ekleyen commit yok: {m}")
        model_commit[m] = c
        model_proof[m] = proof_for(c, proofs)

    # kohort kapısı: bütün MEMBER'ların (kasa dahil) S2 kaydı commit'leri (adlar yazılmaz)
    member_record_commits = {}
    for t in members:
        p, doc, n_rec, n_cancel = primary_record(ROOT / "registry" / "oot" / "records" / t)
        if p is None:
            member_record_commits[t] = None
        else:
            member_record_commits[t] = first_add(str(p.relative_to(ROOT)))
    gate_commit_set = sorted(set(c for c in member_record_commits.values() if c))
    n_member_without_record_commit = sum(1 for c in member_record_commits.values() if c is None)

    # açık küme: kayıtlar, POST_D1, d1_rows, sonuçlar
    per_member = {}
    class_counts = Counter()
    class_by_model = defaultdict(Counter)
    status_by_model = defaultdict(Counter)
    ingest_info = Counter()
    d1_diff_first_trading = 0
    for t in open_set:
        row = members[t]
        rec_path, rec, n_rec, n_cancel = primary_record(ROOT / "registry" / "oot" / "records" / t)
        pd_path, pdrec, n_pd, n_pd_cancel = primary_record(ROOT / "registry" / "oot" / "post_d1" / t)
        outcomes = read_outcomes(t)
        info = {"ticker": t, "year": row["year"], "vault": row["vault"], "n_records": n_rec,
                "n_cancellations": n_cancel, "n_post_d1_records": n_pd}
        # sonuç tarihleri
        if outcomes:
            d1 = next(r["session_date"] for r in outcomes if int(r["h"]) == 1)
            d10 = max(r["session_date"] for r in outcomes if r["status"] == "OK")
            info["D_1"] = d1
            info["block"] = d1[:7]
            info["L"] = streak(outcomes)
            info["n_ok_rows"] = sum(1 for r in outcomes if r["status"] == "OK")
            info["n_target_unavailable_rows"] = sum(1 for r in outcomes if r["status"] == "TARGET_UNAVAILABLE")
            info["n_na_limit_rows"] = sum(1 for r in outcomes if r["status"] == "NA_LIMIT")
            info["n_pending_rows"] = sum(1 for r in outcomes if r["status"] == "PENDING")
            if d1 != row["first_trading_date"]:
                d1_diff_first_trading += 1
        else:
            d1 = d10 = None
            info["L"] = None

        # sonuç girişi (I10)
        cand_pre = [first_add(f"data/outcomes_oot/{t}.csv"), first_add(f"data/outcomes_oot/raw/{t}.json"),
                    first_add(f"registry/oot/d1_rows/{t}.json")]
        cand_post = [first_add(f"data/outcomes_oot/{t}.csv"), first_add(f"data/outcomes_oot/raw/{t}.json")]
        n_zip_terms_pre = n_zip_terms_post = 0
        if d1 and d10:
            for zd, kind, path in zips:
                if d1 <= zd <= d10:
                    n_zip_terms_pre += 1
                    cand_pre.append(first_add(path))
                if d1 < zd <= d10:
                    n_zip_terms_post += 1
                    cand_post.append(first_add(path))
        ingest_pre, ok_pre = dag_min([c for c in cand_pre if c])
        ingest_post, ok_post = dag_min([c for c in cand_post if c])
        info["ingest_pre_listing"] = ingest_pre
        info["ingest_post_d1"] = ingest_post
        info["ingest_dag_total_order"] = bool(ok_pre and ok_post)
        info["n_zip_terms"] = [n_zip_terms_pre, n_zip_terms_post]
        ingest_info[(ingest_pre[:7] if ingest_pre else None, ingest_post[:7] if ingest_post else None)] += 1

        # kohort kapısı (I13-b): bütün MEMBER S2 kayıt commit'leri sonuç commit'inin atası
        def gate_ok(ingest):
            if ingest is None or n_member_without_record_commit:
                return False
            return all(c == ingest or is_ancestor(c, ingest) for c in gate_commit_set)

        gate_pre = gate_ok(ingest_pre)
        gate_post = gate_ok(ingest_post)
        info["cohort_gate"] = [gate_pre, gate_post]

        # sınıf (listeleme öncesi 19 model)
        rec_commit = first_add(str(rec_path.relative_to(ROOT))) if rec_path else None
        rec_proof = proof_for(rec_commit, proofs) if rec_commit else None
        ingest_proof_pre = proof_for(ingest_pre, proofs) if ingest_pre else None
        info["record_commit"] = rec_commit
        info["record_proof_created_at"] = rec_proof["created_at"] if rec_proof else None
        info["ingest_pre_proof_created_at"] = ingest_proof_pre["created_at"] if ingest_proof_pre else None
        classes = {}
        cells = {m["model_id"]: m for m in rec["models"]} if rec else {}
        for m in PRE_LISTING_MODELS:
            terms = {
                "model_before_ingest": bool(ingest_pre and is_ancestor(model_commit[m], ingest_pre)),
                "model_proof": model_proof[m] is not None,
                "record_before_ingest": bool(rec_commit and ingest_pre and is_ancestor(rec_commit, ingest_pre)),
                "proof_order": bool(rec_proof and ingest_proof_pre and rec_proof["created_at"] < ingest_proof_pre["created_at"]),
                "cohort_gate": gate_pre,
                "ingest_committed": ingest_pre is not None,
            }
            cls = "OOT_BLIND" if all(terms.values()) else "OOT_RETRO"
            classes[m] = {"class": cls, "terms": terms}
            class_counts[cls] += 1
            class_by_model[m][cls] += 1
            # satır durumu (E10 kalıbı)
            cell = cells.get(m)
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
                    hs = [1, 3, 5, 10]
                    realized = any(realized_return(outcomes, h) is not None for h in hs)
                    unavailable = all(any(int(r["h"]) == h and r["status"] == "TARGET_UNAVAILABLE" for r in outcomes) for h in hs)
                st = "SCORED" if realized else ("TARGET_UNAVAILABLE" if unavailable else "PENDING")
            status_by_model[m][st] += 1
            classes[m]["status"] = st
        info["classes"] = classes

        # POST_D1 sınıfı ve durumu
        pd_commit = first_add(str(pd_path.relative_to(ROOT))) if pd_path else None
        pd_proof = proof_for(pd_commit, proofs) if pd_commit else None
        ingest_proof_post = proof_for(ingest_post, proofs) if ingest_post else None
        extra = {"d1_rows_sha_matches_record": False, "d1_zip_pins_match_manifest": False,
                 "d1_zip_sha_matches_outcomes_h1": False, "d1_rows_before_ingest": False,
                 "base_record_is_primary": False}
        d1p = ROOT / "registry" / "oot" / "d1_rows" / f"{t}.json"
        if pdrec and d1p.exists():
            d1doc = json.loads(d1p.read_text(encoding="utf-8"))
            extra["d1_rows_sha_matches_record"] = canonical_sha(d1p) == pdrec["d1_rows"]["sha256"] and pdrec["d1_rows"]["file"] == f"registry/oot/d1_rows/{t}.json"
            dd = d1doc["d1"]["session_date"]
            pin_ok = all(
                (dd, k) in pins and pins[(dd, k)]["sha256"] == d1doc["d1"][k]["sha256"] and pins[(dd, k)]["url"] == d1doc["d1"][k]["url"]
                for k in ("thb", "thm"))
            extra["d1_zip_pins_match_manifest"] = pin_ok
            if outcomes:
                h1 = next(r for r in outcomes if int(r["h"]) == 1)
                extra["d1_zip_sha_matches_outcomes_h1"] = (h1["session_date"] == dd and h1["thb_sha256"] == d1doc["d1"]["thb"]["sha256"]
                                                            and h1["thm_sha256"] == d1doc["d1"]["thm"]["sha256"])
            d1c = first_add(f"registry/oot/d1_rows/{t}.json")
            extra["d1_rows_before_ingest"] = bool(d1c and ingest_post and is_ancestor(d1c, ingest_post))
            extra["base_record_is_primary"] = bool(rec_path and pdrec["base_record"]["file"] == str(rec_path.relative_to(ROOT))
                                                   and pdrec["base_record"]["sha256"] == hashlib.sha256(rec_path.read_bytes()).hexdigest())
        terms_pd = {
            "model_before_ingest": bool(ingest_post and is_ancestor(model_commit[POST_D1_MODEL], ingest_post)),
            "model_proof": model_proof[POST_D1_MODEL] is not None,
            "record_before_ingest": bool(pd_commit and ingest_post and is_ancestor(pd_commit, ingest_post)),
            "proof_order": bool(pd_proof and ingest_proof_post and pd_proof["created_at"] < ingest_proof_post["created_at"]),
            "cohort_gate": gate_post,
            "ingest_committed": ingest_post is not None,
            **extra,
        }
        cls_pd = "OOT_BLIND" if all(terms_pd.values()) else "OOT_RETRO"
        class_counts[cls_pd] += 1
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
        info["post_d1"] = {"class": cls_pd, "terms": terms_pd, "status": st, "record_commit": pd_commit,
                           "record_proof_created_at": pd_proof["created_at"] if pd_proof else None,
                           "ingest_proof_created_at": ingest_proof_post["created_at"] if ingest_proof_post else None}
        info["_rec"] = rec
        info["_pdrec"] = pdrec
        info["_outcomes"] = outcomes
        per_member[t] = info

    # ---------------------------------------------------------------- 9 birincil hücre
    cells_out = {}
    for model, metric, horizon, comp, comp_src in PRIMARY_CELLS:
        pairs = []
        excluded = Counter()
        for t in open_set:
            info = per_member[t]
            rec, outcomes = info["_rec"], info["_outcomes"]
            if info["classes"][model]["class"] != "OOT_BLIND":
                excluded["model_not_blind"] += 1
                continue
            cell = {m["model_id"]: m for m in rec["models"]}[model]
            if cell["status"] != "PREDICTED":
                excluded[f"model_{cell['status']}"] += 1
                continue
            if comp_src == "comparators":
                ccell = rec["comparators"][comp]
            else:
                ccell = {m["model_id"]: m for m in rec["models"]}[comp]
                if info["classes"][comp]["class"] != "OOT_BLIND":
                    excluded["comparator_not_blind"] += 1
                    continue
            if ccell["status"] != "PREDICTED":
                excluded[f"comparator_{ccell['status']}"] += 1
                continue
            if metric == "MAE":
                h = int(horizon[1:])
                truth = realized_return(outcomes, h)
                if truth is None:
                    excluded["target_unavailable"] += 1
                    continue
                pm = cell["output"][horizon]["return"]
                pr = ccell["output"][horizon]["return"]
                lm, lr = abs(pm - truth), abs(pr - truth)
                pairs.append({"ticker": t, "block": info["block"], "truth": truth, "pred_model": pm, "pred_rule": pr,
                              "loss_model": lm, "loss_rule": lr, "d": lm - lr})
            else:
                L = info["L"]
                if L is None:
                    excluded["L_unknown"] += 1
                    continue
                Sm, Sr = cell["output"]["S"], ccell["output"]["S"]
                lm, lr = rps(Sm, L), rps(Sr, L)
                pairs.append({"ticker": t, "block": info["block"], "L": L, "loss_model": lm, "loss_rule": lr, "d": lm - lr})
        key = f"{model}|{metric}{('_' + horizon) if horizon else ''}|vs|{comp}"
        cells_out[key] = {"model": model, "metric": metric, "horizon": horizon, "comparator": comp,
                          "comparator_source": comp_src, "excluded": dict(excluded), **cell_summary(pairs)}

    # POST_D1: j = 1 koşullu RPS vs ceiling_hazard_v0 koşullu (S_k / S_1, S2 kaydından)
    pairs = []
    excluded = Counter()
    cond_check = Counter()
    for t in open_set:
        info = per_member[t]
        rec, pdrec, outcomes = info["_rec"], info["_pdrec"], info["_outcomes"]
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
        hcell = {m["model_id"]: m for m in rec["models"]}["ceiling_hazard_v0"]
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
        pairs.append({"ticker": t, "block": info["block"], "L": L, "loss_model": lm, "loss_rule": lr, "d": lm - lr})
    cells_out["post_d1_hazard_v0|RPS_cond_j1|vs|ceiling_hazard_v0_cond"] = {
        "model": POST_D1_MODEL, "metric": "RPS_cond_j1", "horizon": None, "comparator": "ceiling_hazard_v0",
        "comparator_source": "base_record S_k/S_1 (yeniden hesap; kayıttaki comparators_conditional ile eşitlik sayıldı)",
        "comparator_record_equality": dict(cond_check), "excluded": dict(excluded), **cell_summary(pairs)}

    # ---------------------------------------------------------------- özet
    out = {
        "task": "BORSAI_FAZ6_FABLE_S6_RECOMPUTE_20260925",
        "head": head,
        "borsai_imported": "borsai" in sys.modules,
        "definitions": {
            "class_oot": "SPEC_OOT §2 + I13: model commit'i ve birincil kayıt commit'i sonuç commit'inin atası; kayıt kanıtı < sonuç kanıtı; modelin push kanıtı var; bütün MEMBER S2 kayıtları sonuç commit'inin atası. POST_D1 ek: d1_rows kanonik sha = kayıt, D_1 zip sha = MANIFEST_OOT pini = sonuç dosyası h=1.",
            "ingest_pre_listing": "I10: min(outcomes_oot csv, raw json, d1_rows json, [D_1, D_10] tarihli repo zip'i)",
            "ingest_post_d1": "I10: min(outcomes_oot csv, raw json, (D_1, D_10] tarihli repo zip'i); d1_rows hariç",
            "primary_record": "I12: en erken etkin PREDICTION kaydı",
            "return_point": "kayıttaki output[Dh].return (kırpma uygulanmışsa kırpılmış değer; SPEC_CEILING_PATH_V0 §4: mixture medyanı)",
            "MAE_loss": "|return − R_h|, R_h = data/outcomes_oot csv (Decimal → float)",
            "RPS": "(1/10) Σ_{k=1..10} (S_k − 1[L ≥ k])², L = ardışık ceiling_close = 1 sayısı D_1'den",
            "RPS_cond_j1": "(1/9) Σ_{k=2..10} (S_cond_k − 1[L ≥ k])², yalnız L ≥ 1; karşılaştırıcı S_k/S_1",
            "diff": "model − kural (negatif = model iyi)",
            "bootstrap": f"blok = gerçekleşen D_1 ayı; ids sıralı; rng.choice(ids, size=len(ids), replace=True); B={B_BOOT}; numpy Generator(PCG64({SEED})); np.percentile linear [2.5, 97.5]; koşul n ≥ {MIN_N} ve ≥ {MIN_BLOCKS} blok",
            "verdict": "E11: n<10 null; 10≤n<30 'yetersiz örnek'; n≥30 aralık yok 'aralık için yetersiz'; aralık<0 'geçiyor'; >0 'geçemiyor'; aksi 'ayırt edilemiyor'",
        },
        "counters": counters,
        "gate": {
            "n_member_record_commits": len(gate_commit_set),
            "member_record_commits": [c[:7] for c in gate_commit_set],
            "n_member_without_record_commit": n_member_without_record_commit,
            "n_open_D1_differs_from_first_trading_date": d1_diff_first_trading,
            "n_repo_zips_in_cohort_window": sum(1 for zd, _, _ in zips if "2020-01-01" <= zd <= "2023-12-31"),
            "ingest_commit_pairs": {f"{k[0]}|{k[1]}": v for k, v in ingest_info.items()},
        },
        "model_commits": {m: {"commit": c[:7], "proof_created_at": (model_proof[m] or {}).get("created_at")} for m, c in model_commit.items()},
        "class_counts_total": dict(class_counts),
        "class_counts_pre_listing_19x71": dict(sum((class_by_model[m] for m in PRE_LISTING_MODELS), Counter())),
        "class_counts_post_d1": dict(class_by_model[POST_D1_MODEL]),
        "class_by_model": {m: dict(c) for m, c in class_by_model.items()},
        "status_by_model": {m: dict(sorted(c.items())) for m, c in status_by_model.items()},
        "status_totals_pre_listing": dict(sum((status_by_model[m] for m in PRE_LISTING_MODELS), Counter())),
        "primary_cells": cells_out,
        "members": {t: {k: v for k, v in info.items() if not k.startswith("_")} for t, info in per_member.items()},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    # ekrana yalnız özet
    print("HEAD", head[:7], "| borsai import:", out["borsai_imported"])
    print("counters", counters)
    print("class total", dict(class_counts), "| pre-listing", out["class_counts_pre_listing_19x71"], "| post_d1", out["class_counts_post_d1"])
    print("status pre-listing totals", out["status_totals_pre_listing"])
    for m in PRE_LISTING_MODELS + [POST_D1_MODEL]:
        print(f"  {m:24s} class={dict(class_by_model[m])} status={dict(sorted(status_by_model[m].items()))}")
    print("gate", {k: v for k, v in out["gate"].items()})
    for key, c in cells_out.items():
        ci = c["ci95"]
        print(f"CELL {key}: n={c['n']} blocks={c['n_blocks']} mean_diff={c['mean_diff']!r} ci={ci} W/L/T={c['wins']}/{c['losses']}/{c['ties']} verdict={c['verdict']} excluded={c['excluded']}")
        print("     by_year", {y: (v['n'], round(v['mean_diff'], 6)) for y, v in c["by_year"].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())

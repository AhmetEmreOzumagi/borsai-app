"""Canlı POST_D1 akışı (BORSAI_FAZ5_POST_D1_LIVE) test yardımcıları: L4 uçtan uca NETGL provası.

Prova geçici bir klonda koşar (`git clone --local`: commit'li HEAD); gerçek repoya hiçbir şey yazılmaz. Kod çalışma
ağacından (bu oturumun `borsai/`'si) içe aktarılır, veri ve git geçmişi klondan okunur (bütün yollar `root`/dizin
argümanıyla verilir). NETGL bu model için RETRO'dur (sonuçları model dondurulmadan önce repoya girdi); prova yalnız akışın
ve tanımların doğruluğunu gösterir, skora girmez.

Çıktı dosyası (bir kez, commit A'dan önce):

    .venv/bin/python tests/faz5_live_support.py > docs/faz5/ekler/prova_netgl.txt

Bülten adları metinde `thb_YYYY-MM-DD` biçiminde maskelenir (görev kuralı: metinde bülten adı kalıbı yazılmaz).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TICKER = "NETGL"
# D_1 akşamı, THB yayımından sonra (18:25–18:40 Istanbul, SPEC_POST_D1_V0 §7.2) ve T_open'dan önce: yerel saat değil, enjekte
PROVA_NOW = datetime(2026, 9, 17, 19, 0, 0, tzinfo=timezone(timedelta(hours=3)))
TOL = 1e-12

# §7.4 şeması (alan kümeleri birebir)
TOP_KEYS = {"schema_version", "record_type", "record_stage", "ticker", "recorded_at_utc", "recorded_at_istanbul",
            "recorded_at_basis", "code", "base_record", "d1", "d1_features", "models_index", "models", "comparators_conditional",
            "summary"}
CODE_KEYS = {"git_head", "borsai_dirty", "borsai_source_sha256"}
BASE_KEYS = {"file", "sha256", "model_inputs_sha256", "selected_by"}
D1_KEYS = {"session_date", "session_h", "half_day", "halt_flag", "thb", "thm", "fields_raw", "ceiling_close_D1", "lock_consistency"}
BULLETIN_KEYS = {"file", "sha256", "url", "http_last_modified", "downloaded_at", "internal_filename"}
FIELDS_RAW_KEYS = {"open", "high", "low", "close", "volume", "turnover", "aof", "trade_count", "halt", "special_trade_volume",
                   "special_trade_turnover", "reference_price", "upper_limit", "lower_limit"}
LOCK_KEYS = {"open_at_U", "high_at_U", "close_at_U"}
D1_FEATURE_KEYS = {"d1_lock", "d1_turnover_ratio", "d1_turnover_ln", "clipped", "z", "warnings"}
INDEX_KEYS = {"path", "sha256", "model_ids"}
MODEL_KEYS = {"model_id", "stage", "file", "params_sha256", "spec_sha256", "algorithm", "kind", "status", "refusal", "output"}
OUTPUT_KEYS = {"hazard", "S", "P_L", "P_close_ceiling", "conditional_j1", "path_conditional"}      # standart şema + j = 1
COND_KEYS = {"S_cond", "p_break_next", "P_L_cond"}
COMPARATOR_KEYS = {"record_cell_sha256", "S", "S_cond", "source"}
SUMMARY_KEYS = {"n_models", "n_predicted", "n_refused", "n_not_applicable"}


def mask(text: str) -> str:
    return re.sub(r"(th[bm])(20\d\d)(\d\d)(\d\d)1\.(zip|csv)", r"\1_\2-\3-\4.\5", text)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


def schema_problems(rec: dict[str, Any]) -> list[str]:
    out = []

    def eq(name, got, want):
        if set(got) != want:
            out.append(f"{name}: fazla {sorted(set(got) - want)}, eksik {sorted(want - set(got))}")

    eq("üst düzey", rec, TOP_KEYS)
    eq("code", rec["code"], CODE_KEYS)
    eq("base_record", rec["base_record"], BASE_KEYS)
    eq("d1", rec["d1"], D1_KEYS)
    for kind in ("thb", "thm"):
        eq(f"d1.{kind}", rec["d1"][kind], BULLETIN_KEYS)
    eq("d1.fields_raw", rec["d1"]["fields_raw"], FIELDS_RAW_KEYS)
    eq("d1.lock_consistency", rec["d1"]["lock_consistency"], LOCK_KEYS)
    eq("d1_features", rec["d1_features"], D1_FEATURE_KEYS)
    eq("models_index", rec["models_index"], INDEX_KEYS)
    for c in rec["models"]:
        eq(f"models[{c['model_id']}]", c, MODEL_KEYS)
        if not OUTPUT_KEYS <= set(c["output"]):
            out.append(f"models[{c['model_id']}].output: eksik {sorted(OUTPUT_KEYS - set(c['output']))}")
        if c["status"] == "PREDICTED":
            eq(f"models[{c['model_id']}].output.conditional_j1", c["output"]["conditional_j1"], COND_KEYS)
    eq("comparators_conditional", rec["comparators_conditional"], {"ceiling_hazard_v0", "ceiling_hazard_v0@INF",
                                                                   "base_km_expanding", "base_km_last10", "base_always_ceiling"})
    for rid, v in rec["comparators_conditional"].items():
        eq(f"comparators_conditional.{rid}", v, COMPARATOR_KEYS)
    eq("summary", rec["summary"], SUMMARY_KEYS)
    if (rec["schema_version"], rec["record_type"], rec["record_stage"]) != ("borsai.post_d1_record/1", "PREDICTION", "POST_D1"):
        out.append("şema/tür/aşama değerleri")
    if rec["base_record"]["selected_by"] != "SPEC_SCORING_6_PRIMARY_ceiling_hazard_v0_AT_POST_D1_TIME":
        out.append("base_record.selected_by")
    return out


def prova_netgl(workdir: Path) -> tuple[list[str], dict[str, Any]]:
    """L4: klonda NETGL'in pinli D_1 bülteni ve birincil listeleme öncesi kaydıyla POST_D1 kaydı -> denetimler.
    Dönen: (rapor satırları, denetim sonuçları)."""
    from borsai import freeze as fz
    from borsai import outcomes as oc
    from borsai import predict_post_d1 as pd1
    from borsai import registry as reg
    from borsai import scoring as sc

    clone = Path(workdir) / "clone"
    subprocess.run(["git", "clone", "-q", "--local", str(ROOT), str(clone)], check=True, capture_output=True)
    head = _git(clone, "rev-parse", "HEAD")
    dirs = {"models_dir": clone / "models", "records_dir": clone / "registry" / "records",
            "bist_dir": clone / "data" / "raw" / "bist", "outcomes_dir": clone / "data" / "outcomes", "root": clone}
    calendar = oc.load_calendar(bist_dir=dirs["bist_dir"])
    post_dir = clone / "registry" / "post_d1"
    facts: dict[str, Any] = {}
    L: list[str] = []
    w = L.append
    w("# L4 prova: NETGL POST_D1 kaydı, uçtan uca (geçici klon; gerçek repoya yazılmadı)")
    w("")
    w(f"klon HEAD: {head}  (git clone --local; kod bu oturumun çalışma ağacından)")
    w(f"enjekte zaman (yerel saat değil): {PROVA_NOW.isoformat()}")

    # 1. yazım: freeze --post-d1 NETGL'in çağırdığı fonksiyon, klon dizinleri ve enjekte zamanla
    path = fz.write_post_d1_record(TICKER, now=PROVA_NOW, post_dir=post_dir, calendar=calendar, **dirs)
    rec = json.loads(path.read_text(encoding="utf-8"))
    d1 = rec["d1"]["session_date"]
    t_open_at = reg.t_open(d1, calendar)
    facts.update(path=path, record=rec, d1=d1, t_open=t_open_at)
    w(f"kayıt: registry/post_d1/{TICKER}/{path.name}")
    w(f"D_1 = {d1}; D2_cal = {reg.d2_cal(d1, calendar)}; T_open = {t_open_at.isoformat()}; kayıt anı < T_open: "
      f"{PROVA_NOW < t_open_at}")
    w(f"base_record: {rec['base_record']['file']} (sha256 {rec['base_record']['sha256'][:12]}…, "
      f"{rec['base_record']['selected_by']})")
    w(f"d1: ceiling_close_D1 = {rec['d1']['ceiling_close_D1']}, lock_consistency = {rec['d1']['lock_consistency']}, "
      f"half_day = {rec['d1']['half_day']}, halt_flag = {rec['d1']['halt_flag']}")
    w(f"d1 bültenleri: {mask(rec['d1']['thb']['file'])} ({rec['d1']['thb']['sha256'][:12]}…), "
      f"{mask(rec['d1']['thm']['file'])} ({rec['d1']['thm']['sha256'][:12]}…)")
    w(f"d1_features: d1_lock = {rec['d1_features']['d1_lock']}, d1_turnover_ln = {rec['d1_features']['d1_turnover_ln']!r}, "
      f"clipped = {rec['d1_features']['clipped']}, uyarı = {len(rec['d1_features']['warnings'])}")
    w(f"summary: {rec['summary']}")

    # 2. şema §7.4 birebir
    facts["schema_problems"] = schema_problems(rec)
    w("")
    w(f"[1] kayıt şeması §7.4 birebir: {'EVET' if not facts['schema_problems'] else facts['schema_problems']}")

    # 3. model çıktısı == doğrudan predict_post_d1
    base = json.loads((clone / rec["base_record"]["file"]).read_text(encoding="utf-8"))
    idx = json.loads((clone / "models" / fz.INDEX_POST_D1_NAME).read_text(encoding="utf-8"))
    eq_all = True
    for c, e in zip(rec["models"], idx["models"]):
        params = json.loads((clone / "models" / e["file"]).read_text(encoding="utf-8"))
        parent = json.loads((clone / "models" / params["parent"]["file"]).read_text(encoding="utf-8"))
        has_path = any(x["model_id"] == params["path_secondary"]["model_id"] and x["status"] == "PREDICTED" for x in base["models"])
        path_params = json.loads((clone / "models" / params["path_secondary"]["file"]).read_text(encoding="utf-8")) if has_path else None
        direct = pd1.predict_post_d1(params, parent, base["model_inputs"],
                                     {k: rec["d1"][k] for k in ("fields_raw", "half_day", "halt_flag")}, path_params=path_params)
        same = json.loads(json.dumps(direct)) == c["output"]
        eq_all &= same
        w(f"[2] {c['model_id']}: status {c['status']}; kayıttaki çıktı == doğrudan predict_post_d1 (aynı girdi): {same}; "
          f"path_conditional {'var' if c['output']['path_conditional'] else 'null (base_record ceiling_path_v0 taşımıyor)'}")
        s_cond = c["output"]["conditional_j1"]["S_cond"]
        w(f"    S_cond[2] = {s_cond['2']!r}, S_cond[10] = {s_cond['10']!r}, p_break_next = "
          f"{c['output']['conditional_j1']['p_break_next']!r}")
    facts["model_equal"] = eq_all

    # 4. comparators_conditional kopyası vs Faz 2C scores.json j = 1 NETGL satırı
    scores = json.loads((clone / "scores" / "scores.json").read_text(encoding="utf-8"))
    haz = next(m for m in scores["models"] if m["model_id"] == "ceiling_hazard_v0")
    row = next(r for r in next(b for b in haz["conditional"]["by_j"] if b["j"] == 1)["rows"] if r["ticker"] == TICKER)
    worst = 0.0
    for rid, v in rec["comparators_conditional"].items():
        theirs = row["S_cond"] if rid == "ceiling_hazard_v0" else row["rules"][rid]["S_cond"]
        d = max(abs(v["S_cond"][k] - theirs[k]) for k in theirs)
        worst = max(worst, d)
        w(f"[3] {rid}: kopya S_cond vs Faz 2C j = 1 satırı max|Δ| = {d!r} (kaynak {v['source']})")
    parity = sc.post_d1_comparator_parity({rid: {"S_cond": v["S_cond"]} for rid, v in rec["comparators_conditional"].items()}, row)
    facts["comparator_max_abs_diff"] = worst
    w(f"    genel max|Δ| = {worst!r} ≤ 1e-12: {worst <= TOL}; scoring.post_d1_comparator_parity: {parity['status']}")

    # 5. bekçiler (commit'siz kayıt varken bülten indirme durur; commit'ten sonra yeşil)
    try:
        oc.sequence_guard("2026-09-22", root=clone)
        facts["guard_blocks_uncommitted"] = False
    except oc.SequenceRuleError:
        facts["guard_blocks_uncommitted"] = True
    w("")
    w(f"[4] sequence_guard, commit edilmemiş registry/post_d1 kaydı varken indirmeyi durdurdu: {facts['guard_blocks_uncommitted']}")
    _git(clone, "add", "--", f"registry/post_d1/{TICKER}/{path.name}")
    _git(clone, "-c", "user.name=prova", "-c", "user.email=prova@local", "commit", "-q", "-m", "prova: POST_D1 kaydı (klon)")
    rec_commit = _git(clone, "rev-parse", "HEAD")
    oc.sequence_guard("2026-09-22", root=clone)
    manifest = {(r["date"], r["kind"]): r for r in oc.read_manifest(dirs["bist_dir"])}
    facts["guards"] = {"sequence_violations": sc.sequence_violations(clone),
                       "post_d1_record_problems": reg.post_d1_record_problems(rec, manifest),
                       "outcome_order": sc.post_d1_outcome_order_violations(clone)}
    w(f"    commit'ten sonra sequence_guard geçti; sequence_violations = {facts['guards']['sequence_violations']}; "
      f"post_d1_record_problems = {facts['guards']['post_d1_record_problems']}; h ≥ 2 satır sırası = "
      f"{facts['guards']['outcome_order']}")

    # 6. sınıf (tarihlerden): klonda kayıt commit'i, push kanıtı yok (klon push edilmez)
    from borsai import push_proof as pp

    git = sc.Git(clone)
    proofs = pp.load_proofs(clone / "registry" / "push_proofs")
    entry = idx["models"][0]
    model_ev = sc.model_evidence(git, entry["file"], proofs)
    oc_commit = sc.outcome_ingest_commit_post_d1(git, TICKER, d1)
    push = sc.proof_time(git, rec_commit, proofs)
    pit = sc.inputs_pit_problems_post_d1(rec, d1, root=clone, manifest=manifest)
    cls, ev = sc.class_post_d1(git, model_ev, oc_commit, push, t_open_at, not pit, d1)
    facts.update(klass=cls, evidence=ev, pit=pit)
    w("")
    w(f"[5] model commit {str(model_ev['commit'])[:12]} (kanıt {model_ev['push_proof_created_at']}); "
      f"outcome_ingest_commit_post_d1 = {str(oc_commit)[:12]} (D_1'den sonraki ilk sonuç verisi); model atası mı: "
      f"{git.is_ancestor(model_ev['commit'], oc_commit)}")
    w(f"    kayıt commit {rec_commit[:12]} push kanıtı: {push}; inputs_pit_ok_post_d1: {not pit} {pit if pit else ''}")
    w(f"    class_post_d1 = {cls} (model_prospective {ev['model_prospective']}, record_live {ev['record_live']})")
    post = sc.build_post_d1_scores(scores, root=clone, outcomes_dir=dirs["outcomes_dir"], calendar=calendar)
    b = post["models"][0]["conditional_j1"]
    netgl = next(d for d in b["denominator"] if d["ticker"] == TICKER)
    facts["post_scores"] = post
    w(f"    scores_post_d1 (klon): NETGL aşama durumu {netgl['stage_status']}; n_scored {b['n_scored']}, n_retro {b['n_retro']}; "
      f"retro_info NETGL kayıt sayısı "
      f"{next(x for x in post['retro_info'] if x['ticker'] == TICKER)['class_evidence']['n_post_d1_records']}")
    w("")
    ok = (not facts["schema_problems"] and facts["model_equal"] and worst <= TOL and facts["guard_blocks_uncommitted"]
          and not any(facts["guards"].values()) and cls == "RETRO" and netgl["stage_status"] == "RETRO")
    facts["ok"] = ok
    w(f"SONUÇ: {'PROVA_OK' if ok else 'PROVA_KIRMIZI'}")
    return [mask(x) for x in L], facts


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="borsai_prova_") as d:
        lines, facts = prova_netgl(Path(d))
    print("\n".join(lines))
    raise SystemExit(0 if facts["ok"] else 1)

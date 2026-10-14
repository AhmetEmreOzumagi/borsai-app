#!/usr/bin/env python3
"""BORSAI_FAZ7_VAULT_SCORE_20260929 — T2 akıl-sağlığı denetimleri ve T3–T6 tabloları (yalnız okur, yalnız sayı yazar).

Okunanlar: `scores/scores_oot.json` (çalışma ağacı; `scoring --oot` çıktısı), Faz 6'nın commit'li dosyası (`cf60cea`, git show),
`scores/scores.json` (`models[].backtest.near_era`), `registry/oot/records` (yalnız birincil kaydın türü ve hücrenin ret alanı),
`registry/push_proofs`, üç salt okunur skor dosyası (sha256). Skor tanımı yok, yeni metrik yok: hücre değerleri dosyadan okunur.
Tek yeni hesap v1 kalibrasyon bilgi satırıdır (SPEC_HAZARD_V1 §5.2 "yalnız raporda"): dosyadaki satırlardan ort. S_k ve gözlenen
P(L ≥ k), `scoring.live_descriptive`'in formülüyle.

Hijyen: üye kodu, üye başına değer ve bülten adı basılmaz; küme karşılaştırmaları yalnız doğru/yanlış ve sayı yazar.

Kullanım: .venv/bin/python docs/faz7_vault/ekler/skor_denetim.py [--out docs/faz7_vault/ekler/skor_denetim.txt]
          [--before-sha <dosya>]  (skor koşusundan önce alınmış "sha256  yol" satırları; T2 bayt-eşitlik denetimi için)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FAZ6_REF = "cf60cea144856178acf0c48121c006bbffae075c"        # BORSAI_FAZ6_S6: commit'li açık küme skorları (19 model)
S2 = "1dcceff58c4399958cd12dd536cc467889070371"              # ilk kayıtlar (19 model)
R1 = "28aaa3bd5ddae7ddde52e207558ddc984c9aedf6"              # ek kayıtlar (8 model)
VA1 = "2f914dd76117babbc52f5b8853e43a891f3a53f8"             # kasa D_1 satırları: listeleme öncesi modellerin kasa ingest'i
VA2 = "5a96e25ae43051b7a599b54a42477d0a265408f7"             # kasa POST_D1 kayıtları
VB = "71b9071e894563d079a8182f91f48ba84a9bd0f9"              # kasa D_1…D_10: post_d1_hazard_v0'ın kasa ingest'i
READ_ONLY = ("scores/scores.json", "scores/scores_post_d1.json", "docs/SCORES.md")

NEW8 = ("ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF",
        "fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO")
V1 = ("ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled")
FC = ("fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale")
OLD8 = ("v1_5_h99", "v1_6_h99", "v1_5_market20_v0", "pb_v0", "ceiling_hazard_v0", "pb_ceiling_v0", "ceiling_path_v0",
        "pb_ceiling_path_v0")

# Orkestratörün tablosu (görev metni; kasa üyelerinin birincil kayıtlarından): PREDICTED, REFUSED kodları, NA sayısı, NA'daki ret alanı
_F3 = {"F3_MISSING": 2}
EXPECTED = {
    **{m: (62, _F3, 0, {}) for m in ("v1_5_h99", "v1_6_h99", "v1_5_market20_v0", "ceiling_hazard_v0", *V1)},
    **{m: (53, {"PB_IDENTITY": 6, "PB_PRICE_RANGE": 5}, 0, {}) for m in ("pb_v0", "pb_ceiling_v0")},
    "ceiling_path_v0": (60, {"F3_MISSING": 1}, 3, {"F3_MISSING": 1}),
    "pb_ceiling_path_v0": (51, {"PB_IDENTITY": 5, "PB_PRICE_RANGE": 5}, 3, {"PB_IDENTITY": 1}),
    **{m: (63, {}, 1, {}) for m in ("base_always_ceiling", "ceiling_hazard_v0@INF", "pb_ceiling_v0@INF", "ceiling_path_v0@INF",
                                    "ceiling_hazard_v1_pooled@INF")},
    **{m: (60, {"F3_MISSING": 2, "ADDITIONAL_SALE_MISSING": 2}, 0, {}) for m in ("fall_d10_v0_h99", "fall_d10_v0_pooled")},
    "fall_d10_v0_addsale": (62, {"ADDITIONAL_SALE_MISSING": 2}, 0, {}),
    **{m: (64, {}, 0, {}) for m in ("fall_d10_v0_pooled@ZERO", "base_train_median", "base_train_mean", "base_zero", "base_rate",
                                    "base_last10_rate", "base_km_expanding", "base_km_last10")},
}
assert len(EXPECTED) == 27

OUT: list[str] = []


def w(s: str = "") -> None:
    OUT.append(s)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_show(ref: str, rel: str) -> bytes:
    return subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=ROOT, check=True, capture_output=True).stdout


def canon(x) -> str:
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def f(x, nd: int = 4) -> str:
    if x is None:
        return "—"
    if x != 0 and abs(x) < 0.001:
        nd = 6
    s = f"{x:+.{nd}f}"
    return s.replace("-", "−")


def p(x, nd: int = 4) -> str:
    return "—" if x is None else f"{x:.{nd}f}"


def ci(c) -> str:
    return "—" if not c or c.get("ci95") is None else f"[{f(c['ci95'][0])}, {f(c['ci95'][1])}]"


def verdict(c) -> str:
    if c is None or c.get("diff") is None:
        return "metrik yok"
    v = c["verdict"]
    return "geçiyor (zaman-dışı terazide)" if v == "geçiyor" else v


def proofs() -> dict[str, str]:
    out = {}
    for q in (ROOT / "registry" / "push_proofs").glob("*.json"):
        d = json.loads(q.read_text(encoding="utf-8"))
        out[d["proven_commit_sha"]] = d["created_at"]
    return out


def cell(block, model_id, output, hk, metric, rule_id):
    m = next((x for x in block["models"] if x["model_id"] == model_id), None)
    if m is None:
        return None
    return next((c for c in m["cells"] if (c["output"], c["horizon_or_k"], c["metric"], c["rule_id"]) == (output, hk, metric, rule_id)),
                None)


def primary(block, model_id):
    m = next(x for x in block["models"] if x["model_id"] == model_id)
    pc = m["primary_cell"]
    if pc is None:
        return None
    return cell(block, model_id, pc["output"], pc["horizon_or_k"], pc["metric"], pc["rule_ids"][0])


def cell_line(c) -> str:
    return (f"n {c['n']} ({c['n_blocks']} blok) · model {p(c['model_value'])} · karşılaştırılan {p(c['rule_value'])} · fark "
            f"{f(c['diff'])} {ci(c)} · kazanç/kayıp/eşit {c['wins']}/{c['losses']}/{c['ties']} · {verdict(c)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "faz7_vault" / "ekler" / "skor_denetim.txt"))
    ap.add_argument("--before-sha", default=None)
    a = ap.parse_args()

    s = json.loads((ROOT / "scores" / "scores_oot.json").read_text(encoding="utf-8"))
    f6 = json.loads(git_show(FAZ6_REF, "scores/scores_oot.json"))
    near = {m["model_id"]: m["backtest"]["near_era"] for m in json.loads((ROOT / "scores" / "scores.json").read_text(encoding="utf-8"))["models"]
            if (m.get("backtest") or {}).get("near_era")}
    pr = proofs()
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, val: str) -> None:
        checks.append((name, bool(ok), val))

    sealed, total, opn = s["oot_pre_h99_sealed"], s["oot_pre_h99_all"], s["oot_pre_h99"]
    ids = [m["model_id"] for m in opn["models"]]
    old19 = [m for m in ids if m not in NEW8]

    # ---------------------------------------------------------------- kod ve dosyalar
    check("code.borsai_dirty = false", s["code"]["borsai_dirty"] is False, f"git_head {s['code']['git_head'][:7]}")
    if a.before_sha:
        before = dict(reversed(ln.split(None, 1)) for ln in Path(a.before_sha).read_text().splitlines() if ln.strip())
        before = {k.strip(): v for k, v in before.items()}
        same = [before.get(r) == sha(ROOT / r) for r in READ_ONLY]
        check("scores.json, scores_post_d1.json, SCORES.md bayt-eşit (sha256 önce = sonra)", all(same),
              ", ".join(f"{r.split('/')[-1]} {sha(ROOT / r)[:12]}" for r in READ_ONLY))
    check("anahtarlar: oot_pre_h99, _sealed, _all, post_d1, post_d1_sealed, post_d1_all",
          {"oot_pre_h99", "oot_pre_h99_sealed", "oot_pre_h99_all", "post_d1", "post_d1_sealed", "post_d1_all"} <= set(s),
          ", ".join(sorted(k for k in s if k.startswith(("oot_", "post_d1")))))

    # ---------------------------------------------------------------- oot_pre_h99_sealed
    smods = {m["model_id"]: m for m in sealed["models"]}
    check("sealed: 27 model (INDEX sırası)", [m["model_id"] for m in sealed["models"]] == ids and len(ids) == 27, str(len(smods)))
    check("sealed: kohort sayaçları n_sealed = n_in_table = 64", sealed["n_sealed"] == sealed["n_in_table"] == 64,
          f"n_sealed {sealed['n_sealed']}, n_in_table {sealed['n_in_table']}, n_member {sealed['n_member']}")
    check("sealed: retro_info boş", sealed["retro_info"] == [], str(len(sealed["retro_info"])))
    rows_ok, zero_ok, table_ok, ev_ok = [], [], [], []
    n_rows_total = 0
    for mid in ids:
        m = smods[mid]
        rows = m["rows"]
        n_rows_total += len(rows)
        rows_ok.append(len(rows) == 64 and all(r["vault"] == "SEALED" for r in rows))
        zero_ok.append(m["n_oot_retro"] == m["n_skipped"] == m["n_pending"] == m["n_target_unavailable"] == 0)
        ref = Counter(r["prediction"]["refused"]["code"] for r in rows if r["status"] == "REFUSED")
        na = [r for r in rows if r["status"] == "NOT_APPLICABLE_REGIME"]
        na_ref = Counter()
        for r in na:
            rec = json.loads((ROOT / "registry" / "oot" / "records" / r["ticker"] / r["record_id"]).read_text(encoding="utf-8"))
            c = next(x for x in rec["models"] if x["model_id"] == mid)
            if c.get("refusal"):
                na_ref[c["refusal"]["code"]] += 1
        exp = EXPECTED[mid]
        pred = len(rows) - m["n_refused"] - m["n_not_applicable_regime"]
        table_ok.append((pred, dict(ref), len(na), dict(na_ref)) == exp and m["n_scored"] == pred
                        and m["n_refused"] == sum(ref.values()) and m["n_not_applicable_regime"] == len(na))
        if not table_ok[-1]:
            w(f"  UYUŞMAZLIK {mid}: PREDICTED {pred} ret {dict(ref)} NA {len(na)} NA-ret {dict(na_ref)} n_scored {m['n_scored']}")
        want_rec, want_scope = (R1, "ONLY_MISSING_MODELS") if mid in NEW8 else (S2, None)
        for r in rows:
            e = r["class_evidence"]
            rec = json.loads((ROOT / "registry" / "oot" / "records" / r["ticker"] / r["record_id"]).read_text(encoding="utf-8"))
            ev_ok.append(r["class"] == "OOT_BLIND" and e["model_frozen_before_ingest"] and e["record_before_ingest"]
                         and e["record_proof_before_ingest_proof"] and e["cohort_gate_ok"] and e["cohort_gate_missing_n"] == 0
                         and e["record_commit"] == want_rec and e["oot_ingest_commit"] == VA1
                         and e["record_push_proof_created_at"] == pr[want_rec] and e["oot_ingest_push_proof_created_at"] == pr[VA1]
                         and e["record_push_proof_created_at"] < e["oot_ingest_push_proof_created_at"]
                         and e["model_push_proof_created_at"] is not None and e["outcome_ingest_basis"] == "COMMITTED"
                         and rec.get("record_scope") == want_scope and any(c["model_id"] == mid for c in rec["models"]))
    check("sealed: her modelde 64 satır, hepsi SEALED", all(rows_ok), f"{sum(rows_ok)}/27; toplam satır {n_rows_total}")
    check("sealed: n_oot_retro = n_skipped = n_pending = n_target_unavailable = 0", all(zero_ok), f"{sum(zero_ok)}/27")
    check("sealed: PREDICTED, REFUSED (kod) ve NOT_APPLICABLE_REGIME (ret alanı) orkestratör tablosuyla birebir; n_scored = PREDICTED",
          all(table_ok), f"{sum(table_ok)}/27")
    check("sealed: her satır OOT_BLIND; kayıt S2 (19 eski) / ek kayıt 28aaa3b (8 yeni); ingest VA1 2f914dd; kayıt kanıtı < ingest "
          "kanıtı; kohort kapısı doğru", all(ev_ok), f"{sum(ev_ok)}/{len(ev_ok)} satır; S2 {pr[S2]}, ek {pr[R1]}, VA1 {pr[VA1]}")

    # ---------------------------------------------------------------- oot_pre_h99_all
    tmods = {m["model_id"]: m for m in total["models"]}
    omods = {m["model_id"]: m for m in opn["models"]}
    check("all: tam olarak 19 eski model", sorted(tmods) == sorted(old19) and len(tmods) == 19, str(len(tmods)))
    exc = {x["model_id"]: x for x in total["excluded_models"]}
    check("all: yeni 8 model excluded_models'ta, nedeniyle (açık OOT_BLIND 0, açık OOT_RETRO 71)",
          sorted(exc) == sorted(NEW8) and all(x["reason"] and x["n_open_oot_blind"] == 0 and x["n_open_oot_retro"] == 71
                                             for x in exc.values()), str(len(exc)))
    sums = []
    for mid in old19:
        t, o, k = tmods[mid], omods[mid], smods[mid]
        cnt = all(t[c] == o[c] + k[c] for c in ("n_scored", "n_refused", "n_not_applicable_regime", "n_target_unavailable",
                                                 "n_pending", "n_skipped", "n_oot_retro"))
        rows = len(t["rows"]) == len(o["rows"]) + len(k["rows"]) == 135 and sorted(r["ticker"] for r in t["rows"]) == sorted(
            [r["ticker"] for r in o["rows"]] + [r["ticker"] for r in k["rows"]])
        cells = True
        for c in t["cells"]:
            co = cell(opn, mid, c["output"], c["horizon_or_k"], c["metric"], c["rule_id"])
            cs = cell(sealed, mid, c["output"], c["horizon_or_k"], c["metric"], c["rule_id"])
            cells &= c["n"] == (co["n"] if co else 0) + (cs["n"] if cs else 0) or (co is None or cs is None)
        pt = primary(total, mid)
        if pt is not None:
            cells &= pt["n"] == primary(opn, mid)["n"] + primary(sealed, mid)["n"]
        sums.append(cnt and rows and cells)
    check("all: her eski modelde n = açık n + kasa n (sayaçlar, satırlar, hücre n'leri)", all(sums), f"{sum(sums)}/19")
    check("all: kohort sayaçları n_in_table = 135", total["n_in_table"] == 135, str(total["n_in_table"]))

    # ---------------------------------------------------------------- oot_pre_h99 (açık küme)
    f6mods = {m["model_id"]: m for m in f6["oot_pre_h99"]["models"]}
    same19 = [canon(omods[m]) == canon(f6mods[m]) for m in old19]
    check("açık: 19 eski modelin blokları Faz 6 commit'li dosyasıyla (cf60cea) aynı (hücreler, satırlar, sayaçlar)", all(same19),
          f"{sum(same19)}/19")
    check("açık: kohort sayaçları Faz 6 ile aynı",
          canon({k: v for k, v in opn.items() if k != "models"}) == canon({k: v for k, v in f6["oot_pre_h99"].items() if k != "models"}),
          f"n_open {opn['n_open']}, n_in_table {opn['n_in_table']}")
    new_ok = [omods[m]["n_oot_retro"] == 71 and omods[m]["rows"] == [] and omods[m]["cells"] == [] and omods[m]["n_scored"] == 0
              for m in NEW8]
    check("açık: yeni 8 modelde n_oot_retro = 71, skorlanan satır 0", all(new_ok), f"{sum(new_ok)}/8")
    ri = Counter(x["model_id"] for x in s["retro_info"])
    check("açık: üst düzey retro_info yalnız yeni 8 modelin açık çiftleri (8 × 71)",
          set(ri) == set(NEW8) and all(v == 71 for v in ri.values()), f"{sum(ri.values())} çift; Faz 6: {len(f6['retro_info'])}")

    # ---------------------------------------------------------------- post_d1
    check("post_d1 (açık) commit'li dosyadakiyle aynı", canon(s["post_d1"]) == canon(f6["post_d1"]),
          f"satır {s['post_d1']['models'][0]['n_rows']}, skorlanan {s['post_d1']['models'][0]['n_scored']}")
    ps = s["post_d1_sealed"]["models"]
    pm = ps[0] if len(ps) == 1 else None
    ok = pm is not None and pm["model_id"] == "post_d1_hazard_v0" and pm["n_rows"] == len(pm["rows"]) == 47 and pm["n_scored"] == 45 \
        and pm["n_refused"] == 2 and pm["n_not_applicable"] == 17 and pm["n_oot_retro"] == pm["n_retro"] == 0 \
        and pm["n_skipped"] == pm["n_undetermined"] == pm["n_d1_label_na"] == pm["n_pending"] == pm["n_target_unavailable"] == 0 \
        and pm["n_undefined"] == 0
    check("post_d1_sealed: 47 satır (45 skorlanan + 2 ret), n_not_applicable = 17, n_oot_retro = 0, diğer payda sayaçları 0", ok,
          f"satır {pm['n_rows']}, skorlanan {pm['n_scored']}, ret {pm['n_refused']}, NA {pm['n_not_applicable']}, "
          f"OOT_RETRO {pm['n_oot_retro']}")
    refc = Counter(r["refused"]["code"] if isinstance(r.get("refused"), dict) else str(r.get("refused"))
                   for r in pm["rows"] if r["status"] == "REFUSED")
    check("post_d1_sealed: ret kodları F3_MISSING × 2", dict(refc) == {"F3_MISSING": 2}, str(dict(refc)))
    pev = [r["class"] == "OOT_BLIND" and r["class_evidence"]["record_commit"] == VA2 and r["class_evidence"]["oot_ingest_commit"] == VB
           and r["class_evidence"]["record_push_proof_created_at"] == pr[VA2]
           and r["class_evidence"]["oot_ingest_push_proof_created_at"] == pr[VB]
           and r["class_evidence"]["record_proof_before_ingest_proof"] and r["class_evidence"]["cohort_gate_ok"]
           and r["exposure_class"] == "MACHINE_SEQUENCED" for r in pm["rows"]]
    check("post_d1_sealed: her satır OOT_BLIND, MACHINE_SEQUENCED; kayıt VA2, ingest VB; kayıt kanıtı < ingest kanıtı",
          all(pev), f"{sum(pev)}/{len(pev)}; VA2 {pr[VA2]}, VB {pr[VB]}")
    po, pt_ = s["post_d1"]["models"][0], s["post_d1_all"]["models"]
    pa = pt_[0] if len(pt_) == 1 else None
    ok = pa is not None and s["post_d1_all"]["excluded_models"] == [] and all(
        pa[c] == po[c] + pm[c] for c in ("n_rows", "n_scored", "n_refused", "n_not_applicable", "n_oot_retro", "n_skipped",
                                         "n_target_unavailable", "n_pending")) and sorted(r["ticker"] for r in pa["rows"]) == sorted(
        [r["ticker"] for r in po["rows"]] + [r["ticker"] for r in pm["rows"]])
    pp = [c for c in pa["cells"] if c["label"] == "birincil"]
    ok &= len(pp) == 1 and pp[0]["n"] == 59 + 45
    check("post_d1_all = açık + kasa (sayaçlar, satırlar; birincil n = 59 + 45)", ok,
          f"satır {pa['n_rows']}, skorlanan {pa['n_scored']}, NA {pa['n_not_applicable']}, birincil n {pp[0]['n']}")

    w("BORSAI_FAZ7_VAULT_SCORE_20260929 — T2 akıl-sağlığı denetimleri (yalnız sayı; üye kodu ve üye başına değer yok)")
    w(f"Kaynak: scores/scores_oot.json (generated_at_utc {s['generated_at_utc']}; code.git_head {s['code']['git_head'][:7]}; "
      f"borsai_dirty {s['code']['borsai_dirty']}; borsai kaynak sha256 {s['code']['borsai_source_sha256'][:12]}); Faz 6 dosyası "
      f"{FAZ6_REF[:7]}.")
    w("")
    for name, ok, val in checks:
        w(f"[{'TUTTU' if ok else 'TUTMADI'}] {name} — {val}")
    n_bad = sum(not ok for _, ok, _ in checks)
    w("")
    w(f"Sonuç: {len(checks) - n_bad}/{len(checks)} denetim tuttu.")
    w("")

    # ---------------------------------------------------------------- hücre değerleri
    w("== Kasa (oot_pre_h99_sealed) birincil hücreleri ==")
    for mid in ids:
        m = smods[mid]
        c = primary(sealed, mid)
        head = f"{mid}: satır 64 · skorlanan {m['n_scored']} · ret {m['n_refused']} · rejimle uygulanamaz {m['n_not_applicable_regime']}"
        if m["primary_cell"] is None:
            w(f"{head} · birincil hücre yok (kural satırı)")
        else:
            pc = m["primary_cell"]
            w(f"{head} · {pc['output']} {pc['horizon_or_k'] or ''} {pc['metric']} − {pc['rule_ids'][0]}: {cell_line(c)}")
    c = next(x for x in pm["cells"] if x["label"] == "birincil")
    w(f"post_d1_hazard_v0 (post_d1_sealed; MACHINE_SEQUENCED): S_cond RPS j=1 − {c['rule_id']}: {cell_line(c)}")
    w("")
    w("== Kasa ilan edilmiş ikinciller (label = ikincil) ==")
    for m in sealed["models"]:
        for c in m["cells"]:
            if c["label"] == "ikincil":
                w(f"{m['model_id']} · {c['output']} {c['horizon_or_k'] or ''} {c['metric']} − {c['rule_id']}: {cell_line(c)}")
    for c in pm["cells"]:
        if c["label"] != "birincil":
            w(f"post_d1_hazard_v0 ({c['label']}) · {c['output']} {c['horizon_or_k'] or ''} {c['metric']} − {c['rule_id']}: {cell_line(c)}")
    w("")
    w("== Toplam (oot_pre_h99_all) birincil hücreleri, 19 eski model ==")
    for mid in old19:
        c = primary(total, mid)
        if c is not None:
            pc = tmods[mid]["primary_cell"]
            w(f"{mid} · {pc['output']} {pc['horizon_or_k'] or ''} {pc['metric']} − {pc['rule_ids'][0]}: {cell_line(c)}")
    c = next(x for x in pa["cells"] if x["label"] == "birincil")
    w(f"post_d1_hazard_v0 (post_d1_all): S_cond RPS j=1 − {c['rule_id']}: {cell_line(c)}")
    w("")
    w("== Kırılımlar (kasa; birincil hücre; by_year ikincil, by_regime keşif) ==")
    for mid in ids:
        m = smods[mid]
        for key in ("by_year", "by_regime"):
            for c in m.get(key, []):
                lab = "yetersiz örnek" if c["diff"] is not None and c["n"] < 30 else verdict(c)
                w(f"{mid} · {key} {c['subset']} · n {c['n']} ({c['n_blocks']} blok) · fark {f(c['diff'])} {ci(c)} · {lab}")
    w("")

    # ---------------------------------------------------------------- kalibrasyon (bilgi)
    w("== Kalibrasyon (bilgi; hüküm yok) ==")
    calib = {}
    for mid in ("ceiling_hazard_v0", *V1, "ceiling_hazard_v1_pooled@INF", "base_km_expanding"):
        use = [r for r in smods[mid]["rows"] if r["class"] == "OOT_BLIND" and r["status"] == "SCORED" and r["realized"]
               and r["realized"]["L"] is not None and "S" in r["prediction"]]
        for k in (5, 10):
            ms = statistics.mean(r["prediction"]["S"][k - 1] for r in use)
            ob = statistics.mean(1.0 if r["realized"]["L"] >= k else 0.0 for r in use)
            calib[(mid, k)] = (len(use), ms, ob)
            w(f"{mid} · ort. S_{k} {p(ms)} · gözlenen P(L ≥ {k}) {p(ob)} · fark {f(ms - ob)} · n {len(use)}")
    for mid in FC:
        for x in smods[mid].get("info", []):
            w(f"{mid} · ort. P(D10 kapanışı ≤ arz) {p(x['model_value'])} · gözlenen oran {p(x['observed'])} · fark "
              f"{f(x['model_value'] - x['observed'])} · n {x['n']}")
    w("")

    # ---------------------------------------------------------------- T3
    E = []   # (kaynak, hücre metni, beklenen, (lo, hi), c)
    km, v0 = "base_km_expanding", "ceiling_hazard_v0"
    rps = lambda mid, r: cell(sealed, mid, "S", None, "RPS", r)  # noqa: E731
    b10 = lambda mid, r: cell(sealed, mid, "S", 10, "Brier", r)  # noqa: E731
    d10 = lambda mid, r: cell(sealed, mid, "p_up", "D10", "Brier", r)  # noqa: E731
    d5 = lambda mid, r: cell(sealed, mid, "p_up", "D5", "Brier", r)  # noqa: E731
    v1rows = [
        ("`ceiling_hazard_v0` − KM (kasada)", "+0.08", (0.02, 0.14), "[+0.02, +0.14]", rps(v0, km)),
        ("`v1_clip` − KM **(birincil)**", "+0.035", (-0.02, 0.09), "[−0.02, +0.09]", rps("ceiling_hazard_v1_clip", km)),
        ("`v1_clip` − v0", "−0.04", (-0.07, -0.015), "[−0.07, −0.015]", rps("ceiling_hazard_v1_clip", v0)),
        ("`v1_clip` Brier k=10 − KM", "+0.10", (0.04, 0.16), "[+0.04, +0.16]", b10("ceiling_hazard_v1_clip", km)),
        ("`v1_real` − KM **(birincil)**", "−0.005", (-0.06, 0.05), "[−0.06, +0.05]", rps("ceiling_hazard_v1_real", km)),
        ("`v1_real` − v0", "−0.08", (-0.13, -0.03), "[−0.13, −0.03]", rps("ceiling_hazard_v1_real", v0)),
        ("`v1_real` − `v1_clip`", "−0.04", (-0.08, 0.00), "[−0.08, 0.00]", rps("ceiling_hazard_v1_real", "ceiling_hazard_v1_clip")),
        ("`v1_real` Brier k=10 − KM", "+0.04", (-0.01, 0.09), "[−0.01, +0.09]", b10("ceiling_hazard_v1_real", km)),
        ("`v1_pooled` − KM **(birincil)**", "−0.03", (-0.07, 0.01), "[−0.07, +0.01]", rps("ceiling_hazard_v1_pooled", km)),
        ("`v1_pooled` − v0", "−0.10", (-0.15, -0.05), "[−0.15, −0.05]", rps("ceiling_hazard_v1_pooled", v0)),
        ("`v1_pooled` − `v1_real`", "−0.03", (-0.06, 0.00), "[−0.06, 0.00]", rps("ceiling_hazard_v1_pooled", "ceiling_hazard_v1_real")),
        ("`v1_pooled` − `v1_pooled@INF`", "−0.01", (-0.04, 0.02), "[−0.04, +0.02]", rps("ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF")),
        ("`v1_pooled` Brier k=10 − KM", "0.00", (-0.03, 0.04), "[−0.03, +0.04]", b10("ceiling_hazard_v1_pooled", km)),
    ]
    crows = [
        ("`v1_5_h99` − `base_rate` D10 (bilgi)", "+0.010", (-0.030, 0.050), "[−0.030, +0.050]", d10("v1_5_h99", "base_rate")),
        ("`fall_d10_v0_h99` − `base_rate` **(birincil)**", "−0.020", (-0.060, 0.020), "[−0.060, +0.020]", d10("fall_d10_v0_h99", "base_rate")),
        ("`fall_d10_v0_h99` − `v1_5_h99`", "−0.030", (-0.080, 0.010), "[−0.080, +0.010]", d10("fall_d10_v0_h99", "v1_5_h99")),
        ("`fall_d10_v0_pooled` − `base_rate` **(birincil)**", "−0.030", (-0.070, 0.010), "[−0.070, +0.010]", d10("fall_d10_v0_pooled", "base_rate")),
        ("`fall_d10_v0_pooled` − `pooled@ZERO`", "−0.020", (-0.060, 0.020), "[−0.060, +0.020]", d10("fall_d10_v0_pooled", "fall_d10_v0_pooled@ZERO")),
        ("`fall_d10_v0_pooled` − `fall_d10_v0_h99`", "−0.010", (-0.035, 0.015), "[−0.035, +0.015]", d10("fall_d10_v0_pooled", "fall_d10_v0_h99")),
        ("`fall_d10_v0_addsale` − `base_rate` **(birincil)**", "−0.025", (-0.060, 0.010), "[−0.060, +0.010]", d10("fall_d10_v0_addsale", "base_rate")),
        ("`fall_d10_v0_addsale` − `v1_5_h99`", "−0.035", (-0.085, 0.010), "[−0.085, +0.010]", d10("fall_d10_v0_addsale", "v1_5_h99")),
        *((f"D5 (ikincil) `{m}` − `base_rate`", "−0.015", (-0.050, 0.020), "[−0.050, +0.020]", d5(m, "base_rate")) for m in FC),
    ]
    oldrows = [
        ("`v1_5_h99` D5 MAE − medyan", "belirsiz, hafif kötü", (-0.01, 0.04), "[−0.01, +0.04]", primary(sealed, "v1_5_h99"), " puan"),
        ("`v1_6_h99` D10 MAE − `v1_5_h99`", "≈ 0", (-0.01, 0.01), "[−0.01, +0.01]", primary(sealed, "v1_6_h99"), ""),
        ("`v1_5_market20_v0` D5 MAE − `v1_5_h99`", "≈ 0, hafif iyi", (-0.01, 0.005), "[−0.01, +0.005]", primary(sealed, "v1_5_market20_v0"), ""),
        ("`pb_v0` D5 MAE − medyan", "hafif kötü", (-0.005, 0.03), "[−0.005, +0.03]", primary(sealed, "pb_v0"), ""),
        ("`ceiling_hazard_v0` RPS − `base_km_expanding`", "belirsiz", (-0.03, 0.03), "[−0.03, +0.03]", primary(sealed, "ceiling_hazard_v0"), ""),
        ("`pb_ceiling_v0` RPS − `base_km_expanding`", "hafif kötü", (-0.02, 0.04), "[−0.02, +0.04]", primary(sealed, "pb_ceiling_v0"), ""),
        ("`ceiling_path_v0` birincil (D5 MAE − medyan)", "≈ `ceiling_hazard_v0` ile aynı işaret", (-0.03, 0.03), "[−0.03, +0.03]",
         primary(sealed, "ceiling_path_v0"), ""),
        ("`pb_ceiling_path_v0` birincil (D5 MAE − medyan)", "hafif kötü", (-0.02, 0.04), "[−0.02, +0.04]", primary(sealed, "pb_ceiling_path_v0"), ""),
    ]

    def pos(x, lo, hi):
        return "aralık içinde" if lo <= x <= hi else ("altında: beklenenden iyi" if x < lo else "üstünde: beklenenden kötü")

    def fr(x):
        return ("+" if x > 0 else ("−" if x < 0 else "")) + f"{abs(x):g}"

    w("== T3 (tablo satırları; beklenen aynen) ==")
    for title, rows in (("SPEC_HAZARD_V1 §6.1", v1rows), ("SPEC_C_V0 §6.1", crows)):
        w(f"-- {title}")
        for name, exp, (lo, hi), txt, c in rows:
            w(f"| {name} | {exp} | {txt} | {f(c['diff'])} {ci(c)}, {c['n']} | {pos(c['diff'], lo, hi)} |")
    c = next(x for x in pm["cells"] if x["label"] == "birincil")
    w("-- SPEC_DEVIATIONS M12")
    w(f"| `post_d1_hazard_v0` j = 1 koşullu RPS − `ceiling_hazard_v0` (kasa) | −0.035 | [−0.065, −0.005] | {f(c['diff'])} {ci(c)}, "
      f"{c['n']} | {pos(c['diff'], -0.065, -0.005)} |")
    w("-- SPEC_OOT_PRE_H99_V0 §8 (açık küme için yazıldı; kasa için aynı beklenti okunur)")
    for name, exp, (lo, hi), txt, c, unit in oldrows:
        extra = ""
        if unit:
            extra = f" · okuma B (puan = 0.01): [{fr(lo / 100)}, {fr(hi / 100)}] → {pos(c['diff'], lo / 100, hi / 100)}"
        w(f"| {name} | {exp} | {txt}{unit} | {f(c['diff'])} {ci(c)}, {c['n']} | {pos(c['diff'], lo, hi)}{extra} |")
    cal = calib[("ceiling_hazard_v1_pooled", 5)]
    w(f"-- kalibrasyon (bilgi): v1_pooled ort. S_5 − gözlenen = {f(cal[1] - cal[2])} (beklenen [−0.10, +0.10]) → "
      f"{pos(cal[1] - cal[2], -0.10, 0.10)}")
    x = smods["fall_d10_v0_pooled"]["info"][0]
    w(f"-- kalibrasyon (bilgi): fall pooled ort. P(y4) − gözlenen = {f(x['model_value'] - x['observed'])} (beklenen [−0.08, +0.08]) → "
      f"{pos(x['model_value'] - x['observed'], -0.08, 0.08)}")
    w("")

    # ---------------------------------------------------------------- T4
    w("== T4 (beklentiden çok iyi işaretleri) ==")
    for mid in V1:
        c = primary(sealed, mid)
        flag = c["diff"] < -0.10 or c["ci95"][1] < -0.06
        w(f"{mid}: fark {f(c['diff'])} (< −0.10? {c['diff'] < -0.10}), üst uç {f(c['ci95'][1])} (< −0.06? {c['ci95'][1] < -0.06}) → "
          f"{'İŞARET' if flag else 'işaret yok'}")
    for mid in FC:
        c = primary(sealed, mid)
        flag = c["diff"] < -0.08 or c["ci95"][1] < -0.04
        w(f"{mid}: fark {f(c['diff'])} (< −0.08? {c['diff'] < -0.08}), üst uç {f(c['ci95'][1])} (< −0.04? {c['ci95'][1] < -0.04}) → "
          f"{'İŞARET' if flag else 'işaret yok'}")
    c = next(x for x in pm["cells"] if x["label"] == "birincil")
    flag = c["diff"] < -0.08 or c["ci95"][1] < -0.045
    w(f"post_d1_hazard_v0 (kasa): fark {f(c['diff'])} (< −0.08? {c['diff'] < -0.08}), üst uç {f(c['ci95'][1])} (< −0.045? "
      f"{c['ci95'][1] < -0.045}) → {'İŞARET' if flag else 'işaret yok'}")
    w("")

    # ---------------------------------------------------------------- T5
    w("== T5 (başarısızlık tanımları) ==")
    for mid in V1:
        cv0 = rps(mid, v0)
        a_ = cv0["ci95"][0] > 0
        ne = near[mid]
        b_ = ne["ci95"][0] > 0
        n5, ms, ob = calib[(mid, 5)]
        d_ = abs(ms - ob) > 0.15
        w(f"{mid}: (a) v0'dan kötü: RPS − v0 {f(cv0['diff'])} {ci(cv0)} → {'TUTTU' if a_ else 'tutmadı'} · (b) bozuyor: yakın dönem "
          f"{f(ne['diff'])} [{f(ne['ci95'][0])}, {f(ne['ci95'][1])}] etiket {ne['label']} → {'TUTTU' if b_ else 'tutmadı'} · (d) "
          f"kalibrasyon |{p(ms)} − {p(ob)}| = {p(abs(ms - ob))} > 0.15 → {'TUTTU' if d_ else 'tutmadı'}")
    c = rps("ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF")
    w(f"ceiling_hazard_v1_pooled: (c) özellikler bilgi eklemiyor: v1_pooled − v1_pooled@INF noktası {f(c['diff'])} ≥ 0 → "
      f"{'TUTTU' if c['diff'] >= 0 else 'tutmadı'}")
    for mid in FC:
        c = primary(sealed, mid)
        a_ = c["ci95"][0] > 0
        x = smods[mid]["info"][0]
        d_ = abs(x["model_value"] - x["observed"]) > 0.15
        w(f"{mid}: (a) taban orandan kötü: {f(c['diff'])} {ci(c)} → {'TUTTU' if a_ else 'tutmadı'} · (d) kalibrasyon |"
          f"{p(x['model_value'])} − {p(x['observed'])}| = {p(abs(x['model_value'] - x['observed']))} > 0.15 → "
          f"{'TUTTU' if d_ else 'tutmadı'}")
    ne = near["fall_d10_v0_pooled"]
    w(f"fall_d10_v0_pooled: (b) bozuyor: yakın dönem pooled − h99 {f(ne['diff'])} [{f(ne['ci95'][0])}, {f(ne['ci95'][1])}] etiket "
      f"{ne['label']} → {'TUTTU' if ne['ci95'][0] > 0 else 'tutmadı'}")
    c = primary(sealed, "fall_d10_v0_addsale")
    w(f"fall_d10_v0_addsale: (c) ek satış bilgi eklemiyor: addsale − base_rate noktası {f(c['diff'])} ≥ 0 → "
      f"{'TUTTU' if c['diff'] >= 0 else 'tutmadı'}")
    c = d10("fall_d10_v0_pooled", "fall_d10_v0_pooled@ZERO")
    w(f"fall_d10_v0_pooled: (c) özellikler bilgi eklemiyor: pooled − pooled@ZERO noktası {f(c['diff'])} ≥ 0 → "
      f"{'TUTTU' if c['diff'] >= 0 else 'tutmadı'}")
    w("")

    # ---------------------------------------------------------------- T6
    w("== T6 (seçim kuralları; yalnız dosyadaki sayılar) ==")
    ok_v1 = []
    for mid in V1:
        c, cv0, ne = primary(sealed, mid), rps(mid, v0), near[mid]
        k1 = c["n"] >= 30 and c["ci95"] is not None and c["ci95"][1] < 0
        k2 = cv0["ci95"] is not None and cv0["ci95"][1] < 0
        k3 = ne["label"] != "bozuyor"
        w(f"{mid}: k1 birincil {f(c['diff'])} {ci(c)} n {c['n']} ({verdict(c)}) → {k1} · k2 RPS − v0 üst uç {f(cv0['ci95'][1])} < 0 → "
          f"{k2} · k3 yakın dönem etiketi {ne['label']} → {k3} · kasa RPS {p(c['model_value'])} · {'uygun' if k1 and k2 and k3 else 'uygun değil'}")
        if k1 and k2 and k3:
            ok_v1.append((c["model_value"], V1.index(mid), mid))
    if ok_v1:
        best = min(ok_v1)
        tied = [x for x in ok_v1 if abs(x[0] - best[0]) < 0.002]
        w(f"v1 §5.5 öneri: {min(tied, key=lambda x: x[1])[2]} (uygunlar {[x[2] for x in ok_v1]}; eşitlik |Δ| < 0.002 kümesi "
          f"{[x[2] for x in tied]})")
    else:
        w("v1 §5.5 öneri: uygun aday yok → ceiling_hazard_v0 birincil kalır")
    ok_c = []
    for mid in FC:
        c, cv, ne = primary(sealed, mid), d10(mid, "v1_5_h99"), near[mid]
        k1 = c["n"] >= 30 and c["ci95"] is not None and c["ci95"][1] < 0
        k2 = cv["ci95"] is not None and cv["ci95"][1] < 0
        if mid == "fall_d10_v0_pooled":
            k3 = ne["label"] != "bozuyor"
            k3t = f"yakın dönem pooled − h99 etiketi {ne['label']}"
        else:
            k3 = not (ne["ci95"][0] > 0)
            k3t = f"yakın dönem − base_rate [{f(ne['ci95'][0])}, {f(ne['ci95'][1])}] tamamen 0'ın üstünde değil"
        w(f"{mid}: k1 birincil {f(c['diff'])} {ci(c)} n {c['n']} ({verdict(c)}) → {k1} · k2 D10 Brier − v1_5_h99 {f(cv['diff'])} "
          f"{ci(cv)} üst uç < 0 → {k2} · k3 {k3t} → {k3} · kasa D10 Brier {p(c['model_value'])} · "
          f"{'uygun' if k1 and k2 and k3 else 'uygun değil'}")
        if k1 and k2 and k3:
            ok_c.append((c["model_value"], ("fall_d10_v0_addsale", "fall_d10_v0_h99", "fall_d10_v0_pooled").index(mid), mid))
    if ok_c:
        best = min(ok_c)
        tied = [x for x in ok_c if abs(x[0] - best[0]) < 0.002]
        w(f"(C) §5.5 öneri: {min(tied, key=lambda x: x[1])[2]} (uygunlar {[x[2] for x in ok_c]}; eşitlik kümesi {[x[2] for x in tied]})")
    else:
        w("(C) §5.5 öneri: kasada geçen aday yok")

    # ---------------------------------------------------------------- rapor tabloları (Markdown; aynı sayılar)
    md: list[str] = []
    head = "| Model | Hücre | Karşılaştırılan | n (blok) | model | karşılaştırılan | fark | %95 aralık | kazanç / kayıp / eşit | hüküm |"
    rule = "|---|---|---|---|---|---|---|---|---|---|"

    def hk(c):
        return f"{c['output']}{'' if c['horizon_or_k'] is None else ' ' + str(c['horizon_or_k'])} {c['metric']}"

    def mdrow(mid, c):
        return (f"| `{mid}` | {hk(c)} | `{c['rule_id']}` | {c['n']} ({c['n_blocks']}) | {p(c['model_value'])} | {p(c['rule_value'])} | "
                f"{f(c['diff'])} | {ci(c)} | {c['wins']} / {c['losses']} / {c['ties']} | {verdict(c)} |")

    md += ["### Kasa birincil hücreleri", "", head, rule]
    md += [mdrow(mid, primary(sealed, mid)) for mid in ids if smods[mid]["primary_cell"] is not None]
    md.append(mdrow("post_d1_hazard_v0", next(x for x in pm["cells"] if x["label"] == "birincil")).replace(
        "| S_cond RPS |", "| S_cond RPS, j = 1 (ayrı ölçek, MACHINE_SEQUENCED) |"))
    md += ["", "### Kasa satır sayaçları (64 üye; hedef oluşmadı, bekleyen, atlanan, OOT_RETRO her modelde 0)", "",
           "| Model | skorlanan | ret (kod) | rejimle uygulanamaz |", "|---|---|---|---|"]
    for mid in ids:
        m = smods[mid]
        ref = Counter(r["prediction"]["refused"]["code"] for r in m["rows"] if r["status"] == "REFUSED")
        na = Counter(r["not_applicable"]["code"] for r in m["rows"] if r["status"] == "NOT_APPLICABLE_REGIME")
        md.append(f"| `{mid}`{'' if m['primary_cell'] else ' (kural satırı)'} | {m['n_scored']} | {m['n_refused']}"
                  f"{' (' + ', '.join(f'{k} {v}' for k, v in sorted(ref.items())) + ')' if ref else ''} | {m['n_not_applicable_regime']}"
                  f"{' (' + ', '.join(f'{k} {v}' for k, v in sorted(na.items())) + ')' if na else ''} |")
    md += ["", "### Kasa ilan edilmiş ikinciller", "", head, rule]
    for m in sealed["models"]:
        md += [mdrow(m["model_id"], c) for c in m["cells"] if c["label"] == "ikincil"]
    md += ["", "### post_d1 kasa: öbür hücreler (kod etiketi parantezde)", "", head, rule]
    md += [mdrow("post_d1_hazard_v0", {**c, "metric": f"{c['metric']} ({c['label']})"}) for c in pm["cells"] if c["label"] != "birincil"]
    md += ["", "### Toplam (açık + kasa) birincil hücreleri", "", head, rule]
    md += [mdrow(mid, primary(total, mid)) for mid in old19 if tmods[mid]["primary_cell"] is not None]
    md.append(mdrow("post_d1_hazard_v0", next(x for x in pa["cells"] if x["label"] == "birincil")).replace(
        "| S_cond RPS |", "| S_cond RPS, j = 1 (post_d1_all) |"))
    md += ["", "### Açık küme birincil hücreleri (Faz 6 ile aynı; yan yana okuma için)", "", head, rule]
    md += [mdrow(mid, primary(opn, mid)) for mid in old19 if omods[mid]["primary_cell"] is not None]
    md.append(mdrow("post_d1_hazard_v0", next(x for x in po["cells"] if x["label"] == "birincil")).replace(
        "| S_cond RPS |", "| S_cond RPS, j = 1 (post_d1) |"))
    years = ["2020", "2021", "2022", "2023"]

    def brk(c):
        if c["diff"] is None:
            return f"metrik yok ({c['n']})"
        lab = "yetersiz örnek" if c["n"] < 30 else verdict(c)
        return f"{f(c['diff'])} {ci(c)} ({c['n']}; {lab})"

    md += ["", "### Kasa, ilk işlem yılı (ikincil; birincil hücre)", "", "| Model | " + " | ".join(years) + " |",
           "|---|" + "---|" * len(years)]
    for mid in ids:
        if smods[mid]["primary_cell"] is None:
            continue
        by = {c["subset"]: c for c in smods[mid]["by_year"]}
        md.append(f"| `{mid}` | " + " | ".join(brk(by[y]) if y in by else "—" for y in years) + " |")
    regs = ["SALE_ON_EXCHANGE", "OFF_EXCHANGE", "ALLOC_REGIME=PRE_20211111", "ALLOC_REGIME=THRESH100_20211111",
            "ALLOC_REGIME=EQUAL_DIST_20230330"]
    md += ["", "### Kasa, rejim alt kümeleri (keşif; birincil hücre)", "",
           "| Model | borsada satış | borsa dışı | PRE_20211111 | THRESH100_20211111 | EQUAL_DIST_20230330 |", "|---|---|---|---|---|---|"]
    for mid in ids:
        if smods[mid]["primary_cell"] is None:
            continue
        by = {c["subset"]: c for c in smods[mid]["by_regime"]}
        md.append(f"| `{mid}` | " + " | ".join(brk(by[r]) if r in by else "—" for r in regs) + " |")
    Path(a.out).with_name("skor_tablolar.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    text = "\n".join(OUT) + "\n"
    Path(a.out).write_text(text, encoding="utf-8")
    print(f"denetim: {len(checks) - n_bad}/{len(checks)} tuttu; çıktı {a.out}")
    return 0 if n_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

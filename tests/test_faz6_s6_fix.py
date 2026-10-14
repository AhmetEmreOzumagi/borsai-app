"""BORSAI_FAZ6_S6_FIX_20260925: eski kohort post_d1 bloğunun canlı `post_d1_block` tanımına uydurulması (SPEC_POST_D1_V0 §4,
§7.5; SPEC_DEVIATIONS I11, I13, I23) ve kasa hijyeni. B1: D1'i tavan kapanmayan üye satıra girmez (D1 etiketi kapısı, F1);
B2: `retro_info` yalnız açık küme çiftleri (F2); B3: path_conditional karşılaştırıcısı ceiling_path_v0 JSON'uyla (F3).

Sentetik: geçici git deposu (`test_faz6_oot.scored_repo` kalıbı: S1 + S2 + S3 + S5 commit'li, kanıtlı). Gerçek repoda
`scoring --oot` ya da `build_oot_scores` koşulmaz; gerçek sonuç dosyası açılmaz."""
from __future__ import annotations

import csv
import io
import json
import shutil
from datetime import datetime, timezone

import pytest

from borsai import freeze as fz
from borsai import outcomes_oot as oo
from borsai import predict_post_d1 as pd1
from borsai import scoring as sc
from borsai.provenance import pretty_json_bytes

import faz6_support as f6
import test_faz6_oot as t6

NOW = datetime(2026, 9, 25, 9, 0, 0, tzinfo=timezone.utc)
SEALED = "SYNZ"                                         # sentetik kasa üyesi (gerçek kasa kodu değil)
PATH_CELLS = {(o, f"D{h}", m) for o, m in (("return_cond", "MAE"), ("p_up_cond", "Brier")) for h in (3, 5, 10)}

# Küçük depo (B1): SYNA D1 tavan; SYNC D1 tavan değil (kaydı NOT_APPLICABLE); SYND D1 üst limiti yok (etiket NA, kaydı
# REFUSED D1_LIMIT_NA); SYNE D1 tavan ama POST_D1 kaydı yazılmadı; SYNZ kasada.
SMALL = [{"ticker": "SYNA", "ftd": "2021-03-01"}, {"ticker": "SYNC", "ftd": "2021-03-08"},
         {"ticker": "SYND", "ftd": "2021-03-15"}, {"ticker": "SYNE", "ftd": "2021-03-22"},
         {"ticker": SEALED, "ftd": "2021-03-02", "vault": "SEALED"}]
TAIL = ["12.10"] * 9


def _small_paths(cal):
    ceiling = t6._paths_for(cal, SMALL)
    out = {t: ceiling[t] for t in ("SYNA", "SYNE", SEALED)}
    out["SYNC"] = f6.ceiling_path(cal.sessions, "2021-03-08", ["11.00", "11.20"] + TAIL[:8],
                                  ["11.55", "12.10"] + ["13.30"] * 8)
    out["SYND"] = f6.ceiling_path(cal.sessions, "2021-03-15", ["11.55", "12.70", "12.00"] + TAIL[:7],
                                  ["", "12.70", "13.97"] + ["13.30"] * 7)
    return out


def _repo(tmp, cal, members, paths, *, no_post_d1=()):
    """S1 + S2 (kanıtlı) → S3 (D_1 satırları + eski kohort POST_D1 kayıtları, kanıtlı) → S5 commit'i (kanıtsız).
    Dönen: (kök, S3 kanıt dosyası, S5 commit'i)."""
    root = t6._pipeline_repo(tmp, cal, members)
    files = f6.market(t6._window(cal, "2021-02-26", 80), paths)
    kw = dict(root=root, qdir=tmp / "q", downloader=f6.FakeDownloader(files), prober=lambda u: False, calendar=cal)
    written = oo.extract_d1_rows(**kw)["written"]
    rd, od = root / "registry" / "oot" / "records", root / "registry" / "oot"
    for t in written:
        if t not in no_post_d1:
            fz.write_oot_post_d1_record(t, now=NOW, post_dir=od / "post_d1", d1_rows_dir=od / "d1_rows", records_dir=rd,
                                        root=root)
    c_s3 = f6.commit(root, "S3", "registry/oot/d1_rows", "registry/oot/post_d1", "data/raw/bist/MANIFEST_OOT.csv")
    s3_proof = f6.make_proof(root, c_s3, "2026-09-25T10:15:00Z")
    oo.extract_open_members(**kw)
    return root, s3_proof, f6.commit(root, "S5", "data")


@pytest.fixture(scope="module")
def cal():
    return oo.load_calendar_oot()


@pytest.fixture(scope="module")
def small_repo(tmp_path_factory, cal):
    tmp = tmp_path_factory.mktemp("s6fix_small")
    root, _, c_s5 = _repo(tmp, cal, SMALL, _small_paths(cal), no_post_d1=("SYNE",))
    f6.make_proof(root, c_s5, "2026-09-25T10:20:00Z")
    return root


@pytest.fixture(scope="module")
def large_repo(tmp_path_factory, cal):
    """12 açık üye (hepsi D1 tavan, L = 2) + 1 kasa üyesi. `retro`: S3 ve S5 kanıtsızken (sonucun ilk girişi d1_rows'u ekleyen S3
    commit'idir, I10; kanıt sırası gösterilemez -> her çift OOT_RETRO, I13); `blind`: ikisi de kanıtlı."""
    tmp = tmp_path_factory.mktemp("s6fix_large")
    root, s3_proof, c_s5 = _repo(tmp, cal, t6.SCORE_MEMBERS, t6._paths_for(cal, t6.SCORE_MEMBERS))
    keep = tmp / s3_proof.name
    s3_proof.rename(keep)
    try:
        retro = sc.build_oot_scores(root=root, now=NOW)
    finally:
        keep.rename(s3_proof)
    f6.make_proof(root, c_s5, "2026-09-25T10:20:00Z")
    return {"root": root, "tmp": tmp, "retro": retro, "blind": sc.build_oot_scores(root=root, now=NOW)}


def _post(scores):
    (m,) = scores["post_d1"]["models"]
    return m


def _cell(root, t, model_id):
    (_, rec) = oo.oot_post_d1_primary(t, root / "registry" / "oot" / "post_d1")
    return next(c for c in rec["models"] if c["model_id"] == model_id), rec


def _set_d1_label(root, t, label):
    """data/outcomes_oot/<T>.csv'de h = 1 tavan etiketini değiştirir (yalnız çalışma ağacı); eski baytları döner."""
    p = root / "data" / "outcomes_oot" / f"{t}.csv"
    old = p.read_bytes()
    rows = oo.read_outcome_oot(p)
    rows[0]["ceiling_close"] = label
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=oo.OOT_OUTCOME_COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    p.write_bytes(buf.getvalue().encode("utf-8"))
    return old


# ================================================================ T-B1: D1 etiketi kapısı (F1)

def test_b1_post_d1_block_gates_on_d1_label_like_live(small_repo):
    root = small_repo
    assert _cell(root, "SYNC", "post_d1_hazard_v0")[0]["status"] == fz.STATUS_NOT_APPLICABLE
    assert _cell(root, "SYNC", "post_d1_hazard_v0")[0]["refusal"]["code"] == pd1.NOT_APPLICABLE_D1_NOT_CEILING
    assert _cell(root, "SYND", "post_d1_hazard_v0")[0]["status"] == fz.STATUS_REFUSED
    assert oo.oot_post_d1_primary("SYNE", root / "registry" / "oot" / "post_d1") is None
    s = sc.build_oot_scores(root=root, now=NOW)                               # e79a4b7: ValueError (L < j)
    m = _post(s)
    assert [(r["ticker"], r["class"], r["status"]) for r in m["rows"]] == [("SYNA", "OOT_BLIND", "SCORED")]
    counts = {k: m[k] for k in ("n_rows", "n_scored", "n_refused", "n_not_applicable", "n_d1_label_na", "n_undetermined",
                                "n_retro", "n_no_record", "n_skipped", "n_oot_retro")}
    assert counts == {"n_rows": 1, "n_scored": 1, "n_refused": 0, "n_not_applicable": 1, "n_d1_label_na": 1,
                      "n_undetermined": 0, "n_retro": 0, "n_no_record": 1, "n_skipped": 1, "n_oot_retro": 0}
    assert m["retro_info"] == [] and m["cells"] == []                         # n = 1 < 10: hücre yok
    # listeleme öncesi 19 model etkilenmez: dört açık üye skorlanır
    v15 = next(x for x in s["oot_pre_h99"]["models"] if x["model_id"] == "v1_5_h99")
    assert [r["ticker"] for r in v15["rows"]] == ["SYNA", "SYNC", "SYND", "SYNE"]


def test_b1_undetermined_when_d1_outcome_missing(small_repo):
    """Açık üyenin sonucu yoksa (D1 etiketi bekleniyor) satır yok, n_undetermined (canlı D1_PENDING)."""
    p = small_repo / "data" / "outcomes_oot" / "SYNA.csv"
    old = p.read_bytes()
    try:
        p.unlink()
        m = _post(sc.build_oot_scores(root=small_repo, now=NOW))
    finally:
        p.write_bytes(old)
    assert m["rows"] == [] and (m["n_undetermined"], m["n_not_applicable"], m["n_d1_label_na"]) == (1, 1, 1)


# ================================================================ T-B1b: kayıt ↔ gerçekleşen D1 etiketi tutarlılığı

@pytest.mark.parametrize("ticker, label", [("SYNC", "1"),        # kayıt NOT_APPLICABLE, gerçekleşen D1 tavan
                                           ("SYNA", "0")])       # kayıt PREDICTED, gerçekleşen D1 tavan değil
def test_b1b_record_state_and_realized_d1_label_must_agree(small_repo, ticker, label):
    old = _set_d1_label(small_repo, ticker, label)
    try:
        with pytest.raises(sc.ScoringError, match="D1"):
            sc.build_oot_scores(root=small_repo, now=NOW)
    finally:
        (small_repo / "data" / "outcomes_oot" / f"{ticker}.csv").write_bytes(old)
    assert _post(sc.build_oot_scores(root=small_repo, now=NOW))["n_rows"] == 1


def test_b1b_refused_record_carries_no_d1_ceiling_claim(small_repo):
    """Ret hücresi (§12 sırası: ana model ve üst limit reddi tavan denetiminden önce) D1 tavanı hakkında hüküm taşımaz: etiket
    0 da olsa denetim çökmez; üye canlıdaki gibi n_not_applicable'a düşer."""
    old = _set_d1_label(small_repo, "SYND", "0")
    try:
        m = _post(sc.build_oot_scores(root=small_repo, now=NOW))
    finally:
        (small_repo / "data" / "outcomes_oot" / "SYND.csv").write_bytes(old)
    assert (m["n_rows"], m["n_not_applicable"], m["n_d1_label_na"]) == (1, 2, 0)


def test_b1b_label_check_only_for_the_record_of_the_same_d1_session(small_repo):
    """Kaydın D_1'i gerçekleşen D_1 değilse (başka seans) etiketler karşılaştırılmaz: etiketi 1 olan üye sınıf formülünün d1_ok
    terimiyle OOT_RETRO olur (I13), komut çökmez."""
    rpath, rec = oo.oot_post_d1_primary("SYNC", small_repo / "registry" / "oot" / "post_d1")
    old_rec, old_out = rpath.read_bytes(), _set_d1_label(small_repo, "SYNC", "1")
    try:
        rec["d1"]["session_date"] = "2021-03-09"
        rpath.write_bytes(pretty_json_bytes(rec))
        m = _post(sc.build_oot_scores(root=small_repo, now=NOW))
    finally:
        rpath.write_bytes(old_rec)
        (small_repo / "data" / "outcomes_oot" / "SYNC.csv").write_bytes(old_out)
    assert [r["ticker"] for r in m["rows"]] == ["SYNA"] and (m["n_retro"], m["n_not_applicable"]) == (1, 0)
    assert m["retro_info"][0]["ticker"] == "SYNC" and m["retro_info"][0]["class_evidence"]["extra_ok"] is False


def test_model_frozen_after_outcome_is_retro_before_the_label_gate(small_repo):
    """F4 (canlı §7.5 sırası): model push kanıtsızsa (ya da sonuçtan sonra donduysa) her açık üye RETRO, retro_info'da (kayıt
    kimliği yok), hiçbir n'e girmez; D1 etiketi kapısına gelinmez."""
    proofs = small_repo / "registry" / "push_proofs"
    keep = small_repo.parent / "proofs_keep"
    shutil.move(proofs, keep)
    try:
        m = _post(sc.build_oot_scores(root=small_repo, now=NOW))
    finally:
        shutil.move(keep, proofs)
    assert m["rows"] == [] and (m["n_retro"], m["n_oot_retro"], m["n_not_applicable"], m["n_d1_label_na"]) == (4, 4, 0, 0)
    assert [x["ticker"] for x in m["retro_info"]] == ["SYNA", "SYNC", "SYND", "SYNE"]
    assert all(x["record_id"] is None and x["class_evidence"]["model_prospective"] is False for x in m["retro_info"])


# ================================================================ T-B2: kasa kodu hiçbir çıktıda yok (F2)

def test_b2_sealed_code_absent_from_scores_oot_and_doc(large_repo):
    s = large_repo["blind"]
    assert s["oot_pre_h99"]["n_sealed"] == 1                                  # kasa bilgisi yalnız sayaçta
    out = sc.write_oot_scores(s, large_repo["tmp"] / "scores_oot.json")
    text = out.read_text(encoding="utf-8")
    assert SEALED not in text                                                  # e79a4b7: retro_info'da 19 kez
    doc = sc.render_oot_doc(json.loads(text))
    assert SEALED not in doc and "`retro_info`: 0 (model, arz)" in doc
    assert s["retro_info"] == []


def test_b2_retro_info_carries_open_set_pairs_only(large_repo):
    s = large_repo["retro"]                                                    # S3/S5 kanıtsız: her açık çift OOT_RETRO
    open_codes = [m["ticker"] for m in t6.SCORE_MEMBERS if m.get("vault") != "SEALED"]
    models = [e["model_id"] for e in json.loads((large_repo["root"] / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]]
    assert sorted((x["model_id"], x["ticker"]) for x in s["retro_info"]) == sorted((m, t) for m in models for t in open_codes)
    assert SEALED not in json.dumps(s, ensure_ascii=False)
    assert all(b["n_oot_retro"] == len(open_codes) for b in s["oot_pre_h99"]["models"])
    post = _post(s)
    assert post["rows"] == [] and [x["ticker"] for x in post["retro_info"]] == open_codes


# ================================================================ T-B3: path_conditional karşılaştırıcısı (F3)

def test_b3_path_comparator_produced_with_ceiling_path_json(large_repo):
    root = large_repo["root"]
    m = _post(large_repo["blind"])
    assert len(m["rows"]) == 12 and {r["status"] for r in m["rows"]} == {"SCORED"}
    path_params = json.loads((root / "models" / "ceiling_path_v0.json").read_text(encoding="utf-8"))
    ctx = sc.OotContext(root)
    for r in m["rows"]:
        _, rec = _cell(root, r["ticker"], "post_d1_hazard_v0")
        base = json.loads((root / rec["base_record"]["file"]).read_text(encoding="utf-8"))
        pc = next(c for c in base["models"] if c["model_id"] == "ceiling_path_v0")
        assert pc["status"] == fz.STATUS_PREDICTED
        comp = r["rules"]["ceiling_path_v0"]
        assert "not_produced" not in comp                                      # e79a4b7: {not_produced: true}
        assert comp["path"] == sc._path_part(path_params, pc["output"], 1, ctx.realized[r["ticker"]], True)
        assert all(comp["path"][h]["abs_error"] is not None for h in ("D3", "D5", "D10"))
    got = {(c["output"], c["horizon_or_k"], c["metric"]): c for c in m["cells"] if c["rule_id"] == "ceiling_path_v0"}
    assert set(got) == PATH_CELLS                                              # n ≥ 10: altı ikincil hücre
    assert all(c["n"] == 12 and c["label"] == sc.LABEL_SECONDARY and c["scale"] == sc.SCALE_OOT_POST_D1
               for c in got.values())


def test_b3_path_comparator_row_below_n_rule_has_no_cell(small_repo):
    m = _post(sc.build_oot_scores(root=small_repo, now=NOW))
    (row,) = m["rows"]
    assert "path" in row["rules"]["ceiling_path_v0"] and m["cells"] == []     # satır var, n = 1 < 10: hücre yok


def test_post_d1_model_file_sha_is_checked_like_live(small_repo):
    """F4: canlı `load_post_d1_context` gibi POST_D1 model dosyasının sha256'sı INDEX_POST_D1.json'la denetlenir."""
    e = json.loads((small_repo / "models" / fz.INDEX_POST_D1_NAME).read_text(encoding="utf-8"))["models"][0]
    p = small_repo / "models" / e["file"]
    old = p.read_bytes()
    try:
        p.write_bytes(old + b"\n")
        with pytest.raises(sc.ScoringError, match="INDEX_POST_D1"):
            sc.build_oot_scores(root=small_repo, now=NOW)
    finally:
        p.write_bytes(old)


# ================================================================ S6_RENDER: SCORES_OOT.md §6 yeni sayaçlar ve satır tanımı (I47)

def test_render_post_d1_counters_and_row_definition(small_repo):
    """§6: satır = D1 etiketi 1, kaydı olan, OOT_BLIND açık üye (ret dahil); D1'i tavan olmayan üye satır değil, paydada. Sayaç
    tablosu canlı SCORES.md'nin POST_D1 sütunlarıyla; açık küme = satır + payda sayaçları. Kalibrasyon satırı yok (I46). Üye kodu yok."""
    s = sc.build_oot_scores(root=small_repo, now=NOW)
    doc = sc.render_oot_doc(json.loads(pretty_json_bytes(s)))
    sec = doc.split("## 6. ", 1)[1].split("\n## ", 1)[0]
    assert "(ret ve uygulanamaz dahil)" not in doc
    assert "D1'i tavanda kapatan" in sec and "satır değildir" in sec and "kalibrasyon" in sec
    head = ("| Model | satır | skorlanan | ret | hedef oluşmadı | bekleyen | S_1 = 0 | D1 tavan değil | D1 etiketi NA | "
            "D1 bekleniyor | atlanan (S2 kaydı olan) | OOT_RETRO | açık küme |")
    assert head in sec
    assert "| `post_d1_hazard_v0` | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 1 (1) | 0 | 4 |" in sec
    assert "SYN" not in doc and SEALED not in doc

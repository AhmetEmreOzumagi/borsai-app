"""Sıra kuralı bekçisi (CLAUDE.md; SPEC_SCORING §5, §10-10): sonuç ancak sırayla.

2026-08-19 sonrası tarihli (ya da post-2026-08-06 bir arzın işlem gününü kapsayan) her THB/THM dosyası ve
post-08-06 her arzın `data/outcomes/<T>.csv` dosyası için, o dosyayı ekleyen commit'in ataları (a) Faz 1'in
16 model JSON'unu ekleyen commit'leri ve (b) o arzın `registry/records` kaydını ekleyen commit'i içermeli.
Commit edilmemiş dosya için aynı koşul HEAD'e karşı denetlenir. Sonradan eklenen bir model sonuçtan sonra
dondurulursa bu test kırmızı olmaz; o model o arz için RETRO'ya düşer (`borsai/scoring.py`).
POST_D1 modelleri ayrı dizindedir (models/INDEX_POST_D1.json; proje sahibi kararı 4): dizin varsa listelediği model
dosyaları commit edilmiş olmalı ve her hedef dosya modelden sonra (model atası) ya da önce (o arz RETRO) girmiş olmalı;
modelle sırasız (paralel dal) giren hedef ihlaldir (SPEC_DEVIATIONS H).

Ayrıca: bülten zip'leri yalnız data/raw/bist/ altında; yeni arzlar data/ altında yalnız sonuç dosyalarında;
sicil (registry/) hiçbir sonuç alanı taşımaz; kaynak belgeler ilk işlem gününden önce.

POST_D1 (SPEC_POST_D1_V0 §7.3, §7.4, §11-14): registry/post_d1/ altında yalnız `d1` bloğunda ve yalnız D_1 tarihli alanlar
(h ≥ 2 anahtarı ya da D_1 dışı bülten sha'sı -> kırmızı; tek tanım `registry.post_d1_record_problems`); data/outcomes'ta h ≥ 2
dolu satır, o seansın bültenini ekleyen commit'ten önce yazılamaz (`scoring.post_d1_outcome_order_violations`).

Eski kohort (Faz 6; SPEC_OOT_PRE_H99_V0 §2, KARARLAR D6): G1 registry/oot/ sonuç alanı taşımaz (d1_rows ve post_d1 yalnız D_1);
G2 her eski kohort kaydı INDEX.json'daki bütün modelleri içerir (ek kayıt: yalnız üyenin önceki etkin kayıtlarında olmayanları,
girdiler ilk kayıtla bayt-eşit; SPEC_HAZARD_V1 §7.1-3) ve model commit'lerinin torunudur; G5′ ayıklanmış sonuç dosyaları, o
commit'teki INDEX'in her modeli × kohortun her üyesi için modeli içeren birincil kaydın commit'inin torunudur ve o kaydın push
kanıtı önce gelir (model başına kapı, SPEC_HAZARD_V1 §7.3; SPEC_DEVIATIONS L); SEALED kodlar ayıklanmış hiçbir
dosyada yok; kohort penceresi tarihli hiçbir THB/THM zip'i repoda yok; kohort kodları data/ altında yalnız sonuç dosyalarında.

Kasa bekçileri iki kiplidir (SPEC_DEVIATIONS M-E; kasa durumu elle bayrakla değil işaret dosyası registry/oot/VAULT_OPEN.json
ile belirlenir): işaret yokken bugünkü iddialar aynen; işaret varken kasa kodu yalnız üye başına kasa yollarında ve ortak skor
çıktılarında, yalnız işaret commit'inde ya da sonra (`outcomes_oot.vault_hygiene_problems`); data/'nın geri kalanında (v2 dahil)
yine yasak."""
from __future__ import annotations

import csv
import json
import re
import subprocess

import pytest

from borsai import registry as reg
from borsai import scoring as sc
from borsai.provenance import ROOT

THB_THM_CUTOFF = "20260819"
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", "target", "dist"}
TEXT_SUFFIXES = {".csv", ".json", ".md", ".py", ".txt", ".toml", ".lock"}
THB_THM = re.compile(r"th[bm](20\d{6})", re.IGNORECASE)
BULLETIN_FILE = re.compile(r"^th[bm]20\d{6}1(_RAW)?\.zip$", re.IGNORECASE)
OUTCOME_KEYS = {  # gerçekleşen sonuç alan adları (girdi ya da tahmin değil)
    "close", "official_close", "kapanis", "kapanis_fiyati", "closing_price", "upper_limit", "ust_limit",
    "realized", "realized_return", "target_return", "above_ipo_flag", "ceiling_streak_L", "outcome",
    *(f"R_D{h}" for h in (1, 3, 5, 10)), *(f"Y_D{h}" for h in (1, 3, 5, 10)), *(f"ceiling_close_D{k}" for k in range(1, 11)),
}
OUTCOME_DIRS = ("data/outcomes/", "data/raw/bist/")


def repo_files():
    for p in ROOT.rglob("*"):
        if p.is_file() and not SKIP_DIRS & set(p.relative_to(ROOT).parts):
            yield p


def post_listing_tickers() -> set[str]:
    _, rows = reg.read_ipos()
    return set(reg.KNOWN_TICKERS) | {r["ticker"] for r in rows if r["status"] in reg.IPO_STATUSES}


def _git(*args, root=ROOT):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


# ---------------------------------------------------------------- sıra kuralı (gerçek repo)

def test_sequence_rule_outcomes_follow_models_and_records():
    assert sc.sequence_violations() == []


def test_sequence_rule_covers_every_post_cutoff_bulletin_and_outcome():
    """Bekçinin baktığı dosya kümesi eksiksiz: 2026-08-19 sonrası her bülten ve post-08-06 her sonuç dosyası
    sequence_violations kapsamında (kapsam dışı yol yok)."""
    for p in repo_files():
        rel = p.relative_to(ROOT).as_posix()
        if BULLETIN_FILE.match(p.name):
            assert rel.startswith("data/raw/bist/th"), rel             # bülten yalnız data/raw/bist/ altında
            assert re.fullmatch(r"data/raw/bist/th[bm]/20\d\d/th[bm]20\d{6}1\.zip", rel), rel
    outcomes = ROOT / "data" / "outcomes"
    tickers = post_listing_tickers()
    for p in outcomes.glob("*.csv") if outcomes.exists() else []:
        assert p.stem in tickers or p.name == "COMPLETENESS.csv", p


def test_text_mentions_of_post_cutoff_bulletins_follow_models():
    """2026-08-19 sonrası bir bültene metinde atıf yapan dosya da sıra kuralına uyar: onu ekleyen commit'in
    (commit edilmemişse HEAD'in) ataları Faz 1 model JSON'larını ekleyen commit'leri içerir."""
    git = sc.Git(ROOT)
    index = {e["model_id"]: e["file"] for e in json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]}
    model_commits = [git.added_commit(f"models/{index[m]}") for m in sc.faz1_model_ids()]
    assert all(model_commits)
    for p in repo_files():
        rel = p.relative_to(ROOT).as_posix()
        if p.suffix.lower() not in TEXT_SUFFIXES or rel.startswith("docs/prompts/"):
            continue
        dates = [m.group(1) for m in THB_THM.finditer(p.read_text(encoding="utf-8", errors="replace"))]
        if any(d > THB_THM_CUTOFF for d in dates):
            c = git.added_commit(rel) or git.head()
            assert all(git.is_ancestor(mc, c) for mc in model_commits), rel


def test_new_ipos_appear_in_data_only_as_outcomes():
    """Yeni arzlar data/ altında yalnız sonuç dosyalarında (data/outcomes/, data/raw/bist/) geçer; eğitim verisi
    ve H99 kaynakları onları içermez."""
    pattern = re.compile(r"\b(" + "|".join(sorted(post_listing_tickers())) + r")\b")
    for p in (ROOT / "data").rglob("*"):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES and not rel.startswith(OUTCOME_DIRS):
            assert not pattern.search(p.read_text(encoding="utf-8", errors="replace")), rel


# ---------------------------------------------------------------- §10-10 sentetik: sonuç modelden önce -> kırmızı

def _commit(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    _git("add", rel, root=root)
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", rel, root=root)


def _mini_repo(tmp_path, order):
    root = tmp_path / "repo"
    root.mkdir()
    _git("init", "-q", root=root)
    ipos = ",".join(reg.IPOS_COLUMNS) + "\nNEWCO,New Co,2026-09-01,KAP_1,FROZEN,,,2026-09-01T00:00:00+03:00\n"
    items = {
        "index": ("models/INDEX.json", json.dumps({"models": [{"model_id": "m1", "file": "m1.json"},
                                                              {"model_id": "m2", "file": "m2.json"}]})),
        "m1": ("models/m1.json", "{}"),
        "m2": ("models/m2.json", "{}"),
        "ipos": ("registry/ipos.csv", ipos),
        "record": ("registry/records/NEWCO/r.json", "{}"),
        "outcome": ("data/outcomes/NEWCO.csv", "h\n"),
        "bulletin": ("data/raw/bist/thb/2026/thb202609011.zip", "zip"),
    }
    for key in order:
        _commit(root, *items[key])
    return root


def test_10_outcome_before_model_is_red(tmp_path):
    root = _mini_repo(tmp_path, ["index", "m1", "ipos", "record", "outcome", "bulletin", "m2"])
    v = sc.sequence_violations(root, ["m1", "m2"])
    assert v and all("m2" in x for x in v) and len(v) == 2          # hem sonuç dosyası hem bülten


def test_10b_correct_order_is_green_and_later_model_is_not_bound(tmp_path):
    root = _mini_repo(tmp_path, ["index", "m1", "m2", "ipos", "record", "outcome", "bulletin"])
    assert sc.sequence_violations(root, ["m1", "m2"]) == []


def test_10c_outcome_before_record_is_red(tmp_path):
    root = _mini_repo(tmp_path, ["index", "m1", "m2", "ipos", "outcome", "record"])
    v = sc.sequence_violations(root, ["m1", "m2"])
    assert len(v) == 1 and "NEWCO tahmin kaydını" in v[0]


def test_10d_uncommitted_outcome_checked_against_head(tmp_path):
    root = _mini_repo(tmp_path, ["index", "m1", "ipos", "record"])
    (root / "models" / "m2.json").write_text("{}", encoding="utf-8")        # model commit edilmemiş
    (root / "data" / "outcomes").mkdir(parents=True)
    (root / "data" / "outcomes" / "NEWCO.csv").write_text("h\n", encoding="utf-8")
    v = sc.sequence_violations(root, ["m1", "m2"])
    assert len(v) == 1 and "m2" in v[0]


# ---------------------------------------------------------------- POST_D1 dizini (models/INDEX_POST_D1.json)

POST_INDEX = json.dumps({"schema_version": "borsai.model_index/1", "models": [{"model_id": "p", "file": "p.json"}]})


def test_10e_post_d1_model_listed_but_not_committed_is_red(tmp_path):
    root = _mini_repo(tmp_path, ["index", "m1", "m2", "ipos", "record", "outcome", "bulletin"])
    assert sc.sequence_violations(root, ["m1", "m2"]) == []
    _commit(root, "models/INDEX_POST_D1.json", POST_INDEX)                    # dizin var, model dosyası yok
    v = sc.sequence_violations(root, ["m1", "m2"])
    assert len(v) == 2 and all("POST_D1 modeli p" in x for x in v)          # hem sonuç dosyası hem bülten
    (root / "models" / "p.json").write_text("{}", encoding="utf-8")            # dosya var ama commit edilmemiş
    assert len(sc.sequence_violations(root, ["m1", "m2"])) == 2
    _commit(root, "models/p.json", "{}")
    assert sc.sequence_violations(root, ["m1", "m2"]) == []                   # sonuçlar modelden önce: RETRO, kırmızı değil


def test_10f_post_d1_model_then_outcome_is_green_parallel_branch_is_red(tmp_path):
    root = _mini_repo(tmp_path, ["index", "m1", "m2", "ipos", "record"])
    _commit(root, "models/INDEX_POST_D1.json", POST_INDEX)
    _commit(root, "models/p.json", "{}")
    _commit(root, "data/outcomes/NEWCO.csv", "h\n")
    assert sc.sequence_violations(root, ["m1", "m2"]) == []
    # paralel dal: sonuç dosyası, POST_D1 modelini görmeyen bir daldan birleşiyor
    (tmp_path / "b").mkdir()
    root2 = _mini_repo(tmp_path / "b", ["index", "m1", "m2", "ipos", "record"])
    main = _git("rev-parse", "--abbrev-ref", "HEAD", root=root2)
    _git("checkout", "-q", "-b", "side", root=root2)
    _commit(root2, "data/outcomes/NEWCO.csv", "h\n")
    _git("checkout", "-q", main, root=root2)
    _commit(root2, "models/INDEX_POST_D1.json", POST_INDEX)
    _commit(root2, "models/p.json", "{}")
    _git("-c", "user.name=t", "-c", "user.email=t@t", "merge", "-q", "--no-edit", "side", root=root2)
    v = sc.sequence_violations(root2, ["m1", "m2"])
    assert len(v) == 1 and "POST_D1 modeli p" in v[0] and "sıralı değil" in v[0]


# ---------------------------------------------------------------- POST_BREAK dizini (models/INDEX_POST_BREAK.json; K-LB-9, yalnız ekleme)

BREAK_INDEX = json.dumps({"schema_version": "borsai.model_index/1", "models": [{"model_id": "k", "file": "k.json"}]})


def test_10g_post_break_model_listed_but_not_committed_is_red(tmp_path):
    """POST_BREAK dizini POST_D1 dalıyla aynı kural: listelenen model dosyası commit edilmemişse her hedef ihlal; commit'ten sonra
    (sonuçlar modelden önce girmiş: RETRO) temiz."""
    root = _mini_repo(tmp_path, ["index", "m1", "m2", "ipos", "record", "outcome", "bulletin"])
    _commit(root, "models/INDEX_POST_BREAK.json", BREAK_INDEX)                  # dizin var, model dosyası yok
    v = sc.sequence_violations(root, ["m1", "m2"])
    assert len(v) == 2 and all("POST_BREAK modeli k" in x for x in v)        # hem sonuç dosyası hem bülten
    (root / "models" / "k.json").write_text("{}", encoding="utf-8")             # dosya var ama commit edilmemiş
    assert len(sc.sequence_violations(root, ["m1", "m2"])) == 2
    _commit(root, "models/k.json", "{}")
    assert sc.sequence_violations(root, ["m1", "m2"]) == []


def test_10h_post_break_model_then_outcome_is_green_parallel_branch_is_red(tmp_path):
    """Model → sonuç: temiz; sonuç dosyası POST_BREAK modelini görmeyen paralel bir daldan birleşirse ihlal."""
    root = _mini_repo(tmp_path, ["index", "m1", "m2", "ipos", "record"])
    _commit(root, "models/INDEX_POST_BREAK.json", BREAK_INDEX)
    _commit(root, "models/k.json", "{}")
    _commit(root, "data/outcomes/NEWCO.csv", "h\n")
    assert sc.sequence_violations(root, ["m1", "m2"]) == []
    (tmp_path / "b").mkdir()
    root2 = _mini_repo(tmp_path / "b", ["index", "m1", "m2", "ipos", "record"])
    main = _git("rev-parse", "--abbrev-ref", "HEAD", root=root2)
    _git("checkout", "-q", "-b", "side", root=root2)
    _commit(root2, "data/outcomes/NEWCO.csv", "h\n")
    _git("checkout", "-q", main, root=root2)
    _commit(root2, "models/INDEX_POST_BREAK.json", BREAK_INDEX)
    _commit(root2, "models/k.json", "{}")
    _git("-c", "user.name=t", "-c", "user.email=t@t", "merge", "-q", "--no-edit", "side", root=root2)
    v = sc.sequence_violations(root2, ["m1", "m2"])
    assert len(v) == 1 and "POST_BREAK modeli k" in v[0] and "sıralı değil" in v[0]


# ---------------------------------------------------------------- sicil ve referanslar sonuç taşımaz

def _json_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _json_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _json_keys(v)


def _csv(p):
    with p.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return set(reader.fieldnames or []), list(reader)


def test_registry_carries_no_outcome_fields():
    """registry/ (girdiler, kayıtlar, payda, legacy) hiçbir yerde sonuç alanı taşımaz. POST_D1 kayıtları (registry/post_d1/)
    tanımı gereği D_1 alanı taşır; onlar aşağıdaki §11-14 bekçisiyle denetlenir (SPEC_POST_D1_V0 §7.4)."""
    for p in (ROOT / "registry").rglob("*"):
        if p.relative_to(ROOT).as_posix().startswith(("registry/post_d1/", "registry/oot/d1_rows/", "registry/oot/post_d1/",
                                                       "registry/post_break/")):
            continue            # yalnız D_1 alanı taşırlar: kendi bekçileri (§11-14 ve eski kohort G1/G3, aşağıda)
        if p.suffix == ".json":
            keys = set(_json_keys(json.loads(p.read_text(encoding="utf-8"))))
            assert not keys & OUTCOME_KEYS, (p, keys & OUTCOME_KEYS)
        elif p.suffix == ".csv":
            header, _ = _csv(p)
            assert not header & OUTCOME_KEYS, (p, header & OUTCOME_KEYS)


ALLOWED_REFERENCE_MENTIONS = {  # PROVENANCE §4, §6: yalnız tahmin/girdi (BKRGY/INTET replay, NETGL sözleşmesi)
    "tests/reference/netgl_input_contract.json",
    "tests/reference/v1_5_macos_runtime_replay_20260911/REPLAY_REPORT.md",
    "tests/reference/v1_5_macos_runtime_replay_20260911/replay_comparison.csv",
    "tests/reference/v1_5_macos_runtime_replay_20260911/replay_stdout.json",
    "tests/reference/v1_5_macos_runtime_replay_20260911/replay_summary.json",
    "tests/reference/v1_5_macos_runtime_replay_20260911/v1_5_macos_replay_harness.py",
}


def test_reference_files_hold_no_post_listing_outcomes():
    """tests/reference'taki H99 sonuç sütunları meşrudur; yeni arzlar yalnız bilinen tahmin/girdi
    dosyalarında geçer ve o satırlarda sonuç sütunu dolu değildir."""
    tickers = post_listing_tickers()
    pattern = re.compile(r"\b(" + "|".join(sorted(tickers)) + r")\b")
    for p in (ROOT / "tests" / "reference").rglob("*"):
        if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel = p.relative_to(ROOT).as_posix()
        if pattern.search(p.read_text(encoding="utf-8", errors="replace")):
            assert rel in ALLOWED_REFERENCE_MENTIONS, rel
        if p.suffix == ".csv":
            header, rows = _csv(p)
            for r in rows:
                if r.get("ticker") in tickers:
                    assert not any(r.get(c) for c in header & OUTCOME_KEYS), (rel, r.get("ticker"))
                    assert r.get("column") not in OUTCOME_KEYS, (rel, r.get("column"))


def test_source_documents_predate_first_trading_day():
    """Kaynak belgelerin hepsi o arzın ilk işlem gününden önce yayımlandı (sonuç içeremez)."""
    for manifest in (ROOT / "registry" / "source_docs").glob("*/MANIFEST.json"):
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        t = reg.load_inputs(reg.INPUTS_DIR / f"{doc['ticker']}.json")[0]["fields"]["first_trading_date"]["value"]
        for sid, m in doc["documents"].items():
            assert reg.istanbul_date(m["published_at"]) < t, (doc["ticker"], sid)


# ---------------------------------------------------------------- POST_D1 (SPEC_POST_D1_V0 §7.3, §7.4, §11-14)

def _manifest():
    from borsai import outcomes as oc

    return {(r["date"], r["kind"]): r for r in oc.read_manifest()}


def test_post_d1_records_carry_only_d1_fields():
    """Gerçek repo: registry/post_d1/ altındaki her kayıt yalnız D_1 alanlarını, yalnız d1 bloğunda taşır; iptal kaydı hiç
    sonuç alanı taşımaz. (Bugün dizin boş: canlı akışın ilk kaydı bir sonraki arzda.)"""
    manifest = _manifest()
    for p in (ROOT / "registry" / "post_d1").rglob("*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("record_type") == "CANCELLATION":
            assert not set(_json_keys(rec)) & OUTCOME_KEYS, p
            continue
        assert rec["record_stage"] == "POST_D1" and p.parent.name == rec["ticker"], p
        assert reg.post_d1_record_problems(rec, manifest) == [], p


@pytest.mark.requires_git_history
def test_outcome_rows_h_ge_2_follow_bulletin_commits():
    """§7.3 bekçisi (gerçek repo): h ≥ 2 dolu sonuç satırı, o seansın THB ve THM'sini ekleyen commit'ten önce yazılmadı."""
    assert sc.post_d1_outcome_order_violations() == []


def _synthetic_post_d1_record():
    """Sentetik D_1 kaydı (NETGL'in pinli D_1 bülteni, gerçek MANIFEST değerleriyle; dosya yazılmaz)."""
    from borsai import outcomes as oc

    d1 = next(r for r in oc.read_outcome(oc.outcome_path("NETGL")))["session_date"]
    man = _manifest()
    ref = lambda kind: {"file": oc.local_path(d1, kind).relative_to(ROOT).as_posix(), "sha256": man[(d1, kind)]["sha256"],  # noqa: E731
                        "url": man[(d1, kind)]["url"]}
    return {"schema_version": reg.POST_D1_RECORD_SCHEMA, "record_type": "PREDICTION", "record_stage": "POST_D1",
            "ticker": "NETGL", "d1": {"session_date": d1, "session_h": 1, "thb": ref("thb"), "thm": ref("thm"),
                                      "fields_raw": {"close": "1", "upper_limit": "1"}, "ceiling_close_D1": 1},
            "models": [{"output": {"S": [0.5] * 10, "d1_features": {"ceiling_close_D1": 1},
                                   "path_conditional": {"D1": {"realized_return": 0.1}, "D3": {"return": 0.2}}}}],
            "comparators_conditional": {}}, man


def test_post_d1_guard_green_on_valid_synthetic_record():
    rec, man = _synthetic_post_d1_record()
    assert reg.post_d1_record_problems(rec, man) == []


def test_post_d1_guard_red_on_h_ge_2_key():
    rec, man = _synthetic_post_d1_record()
    rec["d1"]["ceiling_close_D2"] = 1
    assert any("h ≥ 2" in x for x in reg.post_d1_record_problems(rec, man))
    rec, man = _synthetic_post_d1_record()
    rec["models"][0]["output"]["R_D3"] = "0.1"
    assert any("h ≥ 2" in x for x in reg.post_d1_record_problems(rec, man))


def test_post_d1_guard_red_on_d1_field_outside_d1_block():
    rec, man = _synthetic_post_d1_record()
    rec["comparators_conditional"]["close"] = "1"
    assert any("d1 bloğu dışında" in x for x in reg.post_d1_record_problems(rec, man))


def test_post_d1_guard_red_on_non_d1_bulletin_sha_or_name():
    rec, man = _synthetic_post_d1_record()
    d1 = rec["d1"]["session_date"]
    other = next(k for k in sorted(man) if k[0] > d1 and k[1] == "thb")
    rec["models"][0]["note"] = man[other]["sha256"]                              # D_2+ bülteninin sha'sı
    assert any("D_1 dışı bültenin sha256" in x for x in reg.post_d1_record_problems(rec, man))
    rec, man = _synthetic_post_d1_record()
    rec["d1"]["thm"]["sha256"] = man[other]["sha256"]
    probs = reg.post_d1_record_problems(rec, man)
    assert any("pinli" in x for x in probs) and any("D_1 dışı" in x for x in probs)
    rec, man = _synthetic_post_d1_record()
    rec["d1"]["thb"]["file"] = rec["d1"]["thb"]["file"].replace(d1.replace("-", ""), other[0].replace("-", ""))
    assert any("D_1 dışı bülten atfı" in x for x in reg.post_d1_record_problems(rec, man))


def test_post_d1_outcome_row_before_bulletin_commit_is_red(tmp_path):
    """Sentetik: h = 2 dolu satır, D_2 bülteninden ÖNCE commit edilirse kırmızı; doğru sırada yeşil."""
    from borsai import outcomes as oc

    def rows(n_ok):
        head = ",".join(oc.OUTCOME_COLUMNS)
        body = []
        for h in range(1, 11):
            r = dict.fromkeys(oc.OUTCOME_COLUMNS, "")
            r.update(h=str(h), status=oc.STATUS_OK if h <= n_ok else oc.STATUS_PENDING,
                     session_date=f"2026-10-{h:02d}" if h <= n_ok else "")
            body.append(",".join(r[c] for c in oc.OUTCOME_COLUMNS))
        return head + "\n" + "\n".join(body) + "\n"

    def bulletins(root, day):
        for kind in oc.KINDS:
            _commit(root, oc.local_path(day, kind, root / "data" / "raw" / "bist").relative_to(root).as_posix(), "zip")

    for order, red in ((("b1", "o1", "b2", "o2"), False), (("b1", "o1", "o2", "b2"), True)):
        root = tmp_path / ("red" if red else "green")
        root.mkdir()
        _git("init", "-q", root=root)
        for step in order:
            if step[0] == "b":
                bulletins(root, f"2026-10-0{step[1]}")
            else:
                _commit(root, "data/outcomes/X.csv", rows(int(step[1])))
        v = sc.post_d1_outcome_order_violations(root)
        assert bool(v) == red and all("h=2" in x for x in v), (order, v)


# ---------------------------------------------------------------- POST_BREAK makine kayıtları (SPEC_BREAK_V0 §9.2; K-LB-4)

POST_BREAK_H_KEY = re.compile(r"^(?:R_D|Y_D|ceiling_close_D|realized_close_D|close_D|upper_limit_D|lower_limit_D|floor_close_D)(\d+)$")


def test_post_break_records_carry_only_d1_to_db():
    """Gerçek repo: registry/post_break/ altındaki her makine kaydı bekçiden temiz (yalnız D_1..D_b; D_b sonrası bülten adı ya da
    sha'sı yok) ve h > b sonuç anahtarı ya da sonuç sözcüğü taşımaz. `test_registry_carries_no_outcome_fields` bu dizini bu bekçiye
    bırakır (kayıt D_b'nin ham THB/THM alanlarını `break_day.fields_raw`'da taşır; §9.2)."""
    manifest = _manifest()
    for p in (ROOT / "registry" / "post_break").rglob("*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        assert (rec["record_stage"], rec["exposure_class"], p.parent.name) == ("POST_BREAK", "MACHINE_SEQUENCED", rec["ticker"]), p
        assert reg.post_break_record_problems(rec, manifest) == [], p
        keys = set(_json_keys(rec))
        b = rec["streak"]["b"]
        assert not [k for k in keys if (m := POST_BREAK_H_KEY.match(k)) and int(m.group(1)) > b], p
        assert not keys & reg.POST_BREAK_OUTCOME_WORDS, p


def _post_break_guard_cases(guard):
    """(durum, kırmızı beklenir mi, bekçinin sonucu): NETGL'in pinli bültenleriyle bellekte kurulan makine kaydı (dosya yazılmaz) ve
    mutasyonları."""
    import copy

    from borsai import freeze as fz

    base, man = fz.build_post_break_machine_record("NETGL"), _manifest()
    db = base["streak"]["break_date"]
    later = next(k for k in sorted(man) if k[0] > db and k[1] == "thm")
    out = [("temiz", False, guard(copy.deepcopy(base), man))]
    rec = copy.deepcopy(base)
    rec["models"][0]["output"][f"ceiling_close_D{base['streak']['b'] + 1}"] = 1
    out.append(("h > b anahtarı", True, guard(rec, man)))
    rec = copy.deepcopy(base)
    rec["summary"]["note"] = man[later]["sha256"]
    out.append(("D_b sonrası sha", True, guard(rec, man)))
    rec = copy.deepcopy(base)
    rec["summary"]["note"] = "data/raw/bist/thm/" + later[0][:4] + "/thm" + later[0].replace("-", "") + "1.zip"
    out.append(("D_b sonrası bülten adı", True, guard(rec, man)))
    return out


@pytest.mark.requires_raw_sources
def test_post_break_guard_red_cases_and_mutation():
    """K-LB-4: temiz kayıt yeşil; h > b anahtarı, D_b sonrası bülten sha'sı ya da adı kırmızı. Mutasyon: bekçi kapatılınca (her zaman
    boş liste) kırmızı beklenen durumlar yakalanmaz — bu test o zaman kırmızı olurdu."""
    cases = _post_break_guard_cases(reg.post_break_record_problems)
    assert all(bool(probs) == red for _, red, probs in cases), [(n, probs) for n, _, probs in cases]
    off = _post_break_guard_cases(lambda rec, man: [])
    assert [n for n, red, probs in off if bool(probs) != red] == ["h > b anahtarı", "D_b sonrası sha", "D_b sonrası bülten adı"]


# ---------------------------------------------------------------- eski kohort (Faz 6; SPEC_OOT_PRE_H99_V0 §2; KARARLAR D6)

OOT_WINDOW_END = "20231231"      # kohort penceresi (2020-01-01…2023-09-21) ve D_10'ları; arşivdeki H99 bültenleri de repoda yok


def _cohort():
    return reg.read_cohort()[1] if reg.COHORT_PATH.exists() else []


def _members():
    return reg.cohort_members(_cohort())


def test_oot_registry_carries_no_outcome_fields():
    """G1: registry/oot/ (kohort, girdiler, kaynak belge MANIFEST'leri, aday özellikler, kayıtlar) sonuç alanı taşımaz."""
    assert reg.oot_outcome_key_problems() == []


def test_oot_d1_rows_and_post_d1_records_carry_only_d1():
    """G1/G3: registry/oot/d1_rows ve post_d1 yalnız D_1 (tek tanım `registry.post_d1_record_problems`); bülten atıfları
    MANIFEST_OOT pinine eşit; POST_D1 kayıtları MACHINE_SEQUENCED."""
    from borsai import outcomes_oot as oo

    manifest = oo.read_manifest_oot()
    for p in (ROOT / "registry" / "oot" / "d1_rows").glob("*.json"):
        assert oo.d1_rows_problems(json.loads(p.read_text(encoding="utf-8")), manifest) == [], p
    man = {(r["date"], r["kind"]): r for r in manifest}
    for p in (ROOT / "registry" / "oot" / "post_d1").rglob("*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("record_type") == "CANCELLATION":
            assert not set(_json_keys(rec)) & OUTCOME_KEYS, p
            continue
        assert rec["exposure_class"] == "MACHINE_SEQUENCED" and p.parent.name == rec["ticker"], p
        assert reg.post_d1_record_problems(rec, man) == [], p


@pytest.mark.requires_git_history
def test_oot_records_hold_every_index_model_and_follow_model_commits():
    """G2: eski kohort kaydı ya tam kayıttır (kaydı ekleyen commit'teki models/INDEX.json'un bütün modelleri, sırasıyla) ya da ek
    kayıttır (`record_scope = ONLY_MISSING_MODELS`; SPEC_HAZARD_V1 §7.1-3, SPEC_DEVIATIONS L): modelleri, o commit'teki INDEX'in
    üyenin kendisinden önceki etkin kayıtlarında olmayan modelleridir (INDEX sırasıyla, en az bir), `delta_of` üyenin ilk etkin
    kaydıdır (dosya adı ve sha256) ve girdileri onunla bayt-eşittir (`freeze.oot_delta_problems`). Kayıt commit'i her model JSON
    commit'inin torunu; kayıt dosyası içerik adreslidir (yeniden yazılmaz)."""
    from borsai import freeze as fz
    from borsai.provenance import sha256_file

    git = sc.Git(ROOT)
    rd = ROOT / "registry" / "oot" / "records"
    indexes: dict = {}
    for p in sorted(rd.rglob("*.json")):
        rel = p.relative_to(ROOT).as_posix()
        rec = json.loads(p.read_text(encoding="utf-8"))
        assert p.name == fz.record_filename(p.read_bytes(), rec["recorded_at_utc"]), rel
        if rec["record_type"] == "CANCELLATION":
            continue
        c = git.added_commit(rel)
        if c not in indexes:
            indexes[c] = json.loads(git.show(c, "models/INDEX.json") if c else (ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
        index = indexes[c]
        ids = [e["model_id"] for e in index["models"]]
        got = [x["model_id"] for x in rec["models"]]
        if rec.get("record_scope") == fz.OOT_DELTA_SCOPE:
            active = sorted(fz.active_records(rec["ticker"], rd), key=lambda x: (x[1]["recorded_at_utc"], x[0].name))
            first_path, first = active[0]
            earlier = {x["model_id"] for q, r in active if (r["recorded_at_utc"], q.name) < (rec["recorded_at_utc"], p.name)
                       for x in r["models"]}
            assert got and got == [m for m in ids if m not in earlier], rel
            assert rec["delta_of"] == first_path.name and rec["delta_of_sha256"] == sha256_file(first_path), rel
            assert rec["models_index"]["model_ids"] == ids and fz.oot_delta_problems(first, rec) == [], rel
        else:
            assert got == ids, rel
        for e in index["models"]:
            mc = git.added_commit(f"models/{e['file']}")
            assert mc is not None and git.is_ancestor(mc, c or git.head()), (rel, e["model_id"])


def _extracted_files():
    base = [ROOT / "data" / "outcomes_oot", ROOT / "registry" / "oot" / "d1_rows"]
    return [p for d in base if d.exists() for p in sorted(d.rglob("*")) if p.is_file()]


@pytest.mark.requires_git_history
def test_oot_outcomes_follow_every_s2_record_and_its_push_proof():
    """G5′ (KARARLAR D6-5), model başına (SPEC_HAZARD_V1 §7.3; SPEC_DEVIATIONS L): ayıklanmış sonuç dosyasını (ve D_1 satırı
    dosyasını) ekleyen commit, O COMMIT'TEKİ models/INDEX.json'un her modeli ve kohortun her MEMBER'ı için modeli içeren birincil
    kaydın (`freeze.oot_primary_of`: en erken etkin kayıt) commit'inin torunudur; o kaydın push kanıtı vardır ve sonuç commit'inin
    kanıtından önce gelir. (Sonuçtan sonra INDEX'e giren modellerin ek kayıtları bu dosyalar için aranmaz: o modeller bu arzlarda
    formülle OOT_RETRO'dur.)"""
    from borsai import freeze as fz
    from borsai import push_proof as pp

    files = _extracted_files()
    if not files:
        return
    git = sc.Git(ROOT)
    proofs = pp.load_proofs()
    rd = ROOT / "registry" / "oot" / "records"
    active = {}
    for r in _members():
        active[r["ticker"]] = fz.active_records(r["ticker"], rd)
        assert active[r["ticker"]], "bir üyenin S2 kaydı yok ama sonuç dosyası var"
    indexes: dict = {}
    primary: dict = {}
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        added = git.added_commit(rel)
        c = added or git.head()
        if added not in indexes:
            indexes[added] = [e["model_id"] for e in json.loads(
                git.show(added, "models/INDEX.json") if added else (ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))["models"]]
        out_proof = sc.proof_time(git, added, proofs)
        for t, recs in active.items():
            for m in indexes[added]:
                if (t, m) not in primary:
                    prim = fz.oot_primary_of(recs, m)
                    primary[(t, m)] = None if prim is None else git.added_commit(prim[0].relative_to(ROOT).as_posix())
                rc = primary[(t, m)]                     # iletiler üye kodu taşımaz (kasa hijyeni)
                assert rc is not None and git.is_ancestor(rc, c), (rel, m)
                rp = sc.proof_time(git, rc, proofs)
                assert rp is not None, (rel, m, "kayıt push kanıtı yok")
                assert out_proof is None or rp < out_proof, (rel, m)


@pytest.mark.requires_git_history
def test_sealed_codes_absent_from_every_extracted_file():
    """D6-3: kasadaki (SEALED) kodların satırı hiçbir ayıklanmış dosyada, POST_D1 kaydında, MANIFEST_OOT'ta ya da eski kohort skor
    dosyalarında (varsa; S6_FIX F2) yok (ad ya da içerik). İki kip (SPEC_DEVIATIONS M-E): işaret dosyası yokken bu iddia aynen;
    işaret varken (a) kasa kodu yalnız üye başına kasa yollarında (dosya yalnız kendi üyesinin kodunu taşır) ve ortak skor
    çıktılarında, MANIFEST_OOT ve işaret dosyası kodsuz; (b) her kasa dosyası işaret dosyasını ekleyen commit'te ya da torununda
    (`outcomes_oot.vault_hygiene_problems`; iletiler yalnız sayı)."""
    from borsai import outcomes_oot as oo

    sealed = sorted(r["ticker"] for r in _members() if r["vault"] == reg.VAULT_SEALED)
    if not sealed:
        return
    if oo.vault_marker_state(ROOT).open_mode:
        problems = oo.vault_hygiene_problems(ROOT, sealed=sealed)          # yerel değişken: hata çıktısı kod basmaz
        assert problems == []
        return
    pattern = re.compile(r"\b(" + "|".join(sealed) + r")\b")
    extra = [ROOT / "data" / "raw" / "bist" / "MANIFEST_OOT.csv", ROOT / "scores" / "scores_oot.json",
             ROOT / "docs" / "SCORES_OOT.md"] + sorted((ROOT / "registry" / "oot" / "post_d1").rglob("*"))
    for p in _extracted_files() + [x for x in extra if x.is_file()]:
        rel = p.relative_to(ROOT).as_posix()
        assert not pattern.search(rel) and not pattern.search(p.read_text(encoding="utf-8", errors="replace")), rel


def test_no_cohort_window_bulletin_anywhere_in_repo():
    """D6-1: kohort penceresi (ve D_10'ları) tarihli hiçbir THB/THM zip'i ya da iç CSV'si repoda yok (hangi dizinde olursa)."""
    name = re.compile(r"^th[bm](20\d{6})1(_RAW)?\.(zip|csv)$", re.IGNORECASE)
    for p in repo_files():
        m = name.match(p.name)
        assert not (m and m.group(1) <= OOT_WINDOW_END), p.relative_to(ROOT).as_posix()


V2_TABLE_REL = "data/training_table_v2.csv"    # Faz 7 T4: açık küme kodlarını taşıyabilen tek sonuç-dışı data/ dosyası (tam yol)
UNLU_ALLOWED = {("data/raw/PREBOOKBUILD_POINT_IN_TIME_EVIDENCE_V1_1_CANONICAL_R2_99.csv", "UNLU")}
# Canlı tamlık dosyası (Faz 2B, f1f9d44; kasa çekilişinden önce): satırları 2026-08-07 ve sonrasında ilk görülen 2026
# enstrümanlarıdır, kohort penceresinin sonucu değildir. Bir satır (kapsam dışı, bedelli kalan paylar) bir kasa üyesinin kodunu
# taşır; kasa bekçisi bu dosyada yalnız first_seen ≥ LIVE_SCOPE_START satırlarını istisna sayar. Kapalı kipte (kasa işaret
# dosyası yok) sayısını pinler (yeni satır -> kırmızı, gözden geçir; SPEC_DEVIATIONS J). Açık kipte (M-E; işaret var) sayı pini
# yoktur: canlı pencerede yeni görülen mevcut pay kodları (ör. temerrüt pazarı) kasa üyesi kodlarıyla eşleşebilir; eşleşen her
# satır first_seen ≥ LIVE_SCOPE_START olmalı ve ipos.csv'de halka arz olarak geçmemeli (`completeness_sealed_problems`; SPEC_DEVIATIONS M23).
COMPLETENESS_REL = "data/outcomes/COMPLETENESS.csv"
LIVE_SCOPE_START = "2026-08-07"
KNOWN_COMPLETENESS_SEALED_ROWS = 1


def _cohort_codes() -> tuple[list[str], list[str]]:
    """(bütün kohort kodları, kasa kodları). Kasa kodları hiçbir çıktıya yazılmaz (bekçi mesajları yalnız sayı verir)."""
    codes = sorted({r["ticker"] for r in _cohort() if r["status"] != reg.COHORT_OUT_OF_SCOPE}
                   | {r["ticker"] for r in csv.DictReader(reg.UNIVERSE_PATH.open(encoding="utf-8")) if r["status"] == "MEMBER"})
    sealed = sorted(r["ticker"] for r in _members() if r["vault"] == reg.VAULT_SEALED)
    return codes, sealed


def cohort_code_problems(data_dir, codes, sealed, vault_open: bool = False) -> list[str]:
    """data/ bekçisi (T4, SPEC_DEVIATIONS J): kohort kodları yalnız sonuç dizinlerinde (data/outcomes_oot/, data/outcomes/,
    data/raw/bist/) ve `V2_TABLE_REL`'de (yalnız açık küme); kasa kodları data/'nın HİÇBİR yerinde. `data_dir` data/ kökü
    (gerçek repo ya da sentetik kopya). İstisna: H99 kaynağında DMRGD unvanındaki "UNLU" sözcüğü (ticker değil). Mesajlar
    kod adı değil yalnız sayı taşır. `vault_open` (SPEC_DEVIATIONS M-E (c); kasa işaret dosyası varken): bir kasa üyesinin KENDİ
    sonuç dosyaları (data/outcomes_oot/<T>.csv, raw/<T>.json) kendi kodunu taşıyabilir; başka her yerde (v2 dahil) kasa kodu yine
    kırmızı; COMPLETENESS istisnası aynen."""
    from pathlib import Path

    from borsai import outcomes_oot as oo

    data_dir = Path(data_dir)
    every = re.compile(r"\b(" + "|".join(codes) + r")\b")
    vault = re.compile(r"\b(" + "|".join(sealed) + r")\b") if sealed else None
    out = []
    for p in sorted(data_dir.rglob("*")):
        if not (p.is_file() and p.suffix.lower() in TEXT_SUFFIXES):
            continue
        rel = "data/" + p.relative_to(data_dir).as_posix()
        text = p.read_text(encoding="utf-8", errors="replace")
        if vault is not None:
            if rel == COMPLETENESS_REL:
                rows = list(csv.DictReader(text.splitlines()))
                hits = {f for r in rows if r.get("first_seen", "") < LIVE_SCOPE_START for v in r.values() for f in vault.findall(v or "")}
            else:
                hits = {f for f in vault.findall(text) if (rel, f) not in UNLU_ALLOWED}
                member = oo.vault_member_of(rel) if vault_open else None
                if member is not None and member in sealed:
                    hits.discard(member)                        # açık kip: üyenin kendi sonuç dosyası
            if hits:
                out.append(f"{rel}: kasa kodu ({len(hits)} farklı)")
        if not rel.startswith(OUTCOME_DIRS + ("data/outcomes_oot/",)) and rel != V2_TABLE_REL:
            n_codes = len({f for f in every.findall(text) if (rel, f) not in UNLU_ALLOWED})
            if n_codes:
                out.append(f"{rel}: kohort kodu ({n_codes} farklı) sonuç dizini ya da {V2_TABLE_REL} dışında")
    return out


@pytest.mark.requires_git_history
def test_cohort_codes_appear_in_data_only_as_outcomes():
    """`test_new_ipos_appear_in_data_only_as_outcomes` kalıbı kohort kodları için: data/ altında yalnız sonuç dizinlerinde
    (data/outcomes_oot/, data/outcomes/, data/raw/bist/); Faz 7 T4: açık küme kodları ayrıca yalnız data/training_table_v2.csv'de
    (tam yol). Yeni: kasa kodları data/'nın hiçbir yerinde (sonuç dizinleri ve v2 dahil). İstisna: DMRGD unvanındaki "UNLU".
    COMPLETENESS.csv istisnası iki kiplidir (`completeness_sealed_problems`; SPEC_DEVIATIONS M23): kapalı kipte pin 1 ve OUT_OF_SCOPE;
    açık kipte pinsiz (eşleşen satır sayısı çıktıya yazılır), ama first_seen ≥ LIVE_SCOPE_START ve ipos.csv'de halka arz değil."""
    from borsai import outcomes_oot as oo

    codes, sealed = _cohort_codes()
    vault_open = oo.vault_marker_state(ROOT).open_mode                   # M-E: kip işaret dosyasından
    problems = cohort_code_problems(ROOT / "data", codes, sealed, vault_open)   # yerel değişken: hata çıktısı kod basmaz
    assert problems == []
    if sealed and (ROOT / COMPLETENESS_REL).exists():
        rows = list(csv.DictReader((ROOT / COMPLETENESS_REL).read_text(encoding="utf-8").splitlines()))
        _, ipos_rows = reg.read_ipos()
        problems, n_known = completeness_sealed_problems(rows, sealed, ipos_rows, vault_open)
        print(f"COMPLETENESS kasa koduyla eşleşen satır: {n_known} ({'açık' if vault_open else 'kapalı'} kip)")
        assert problems == []


def completeness_sealed_problems(rows, sealed, ipos_rows, vault_open: bool) -> tuple[list[str], int]:
    """COMPLETENESS kasa-kodu istisnası, iki kipli (SPEC_DEVIATIONS M23; kip `outcomes_oot.vault_marker_state(ROOT).open_mode`).
    `rows`: COMPLETENESS satırları, `sealed`: kasa kodları, `ipos_rows`: registry/ipos.csv satırları. Dönüş: (sorunlar, kasa koduyla
    eşleşen satır sayısı); iletiler kod adı değil yalnız sayı taşır.
    Kapalı kip (işaret yok): bugünkü iddialar aynen; eşleşen satır sayısı `KNOWN_COMPLETENESS_SEALED_ROWS` ve her biri
    first_seen ≥ LIVE_SCOPE_START ile ipos_status OUT_OF_SCOPE.
    Açık kip: sayı pini yok; eşleşen her satır (a) first_seen ≥ LIVE_SCOPE_START ve (b) ipos.csv'de halka arz (`reg.IPO_STATUSES`)
    olarak geçmiyor: satırın kodu da, eşleşen kasa kodu da, satırın ipos_status'ü de halka arz değil."""
    if not sealed:
        return [], 0
    vault = re.compile(r"\b(" + "|".join(sealed) + r")\b")
    known = [r for r in rows if any(vault.search(v or "") for v in r.values())]
    out: list[str] = []
    if vault_open:
        ipo_codes = {r["ticker"] for r in ipos_rows if r["status"] in reg.IPO_STATUSES}

        def is_ipo(r) -> bool:
            codes = {r["ticker"]} | {f for v in r.values() for f in vault.findall(v or "")}
            return bool(codes & ipo_codes) or r["ipos_status"] in reg.IPO_STATUSES

        early = sum(r["first_seen"] < LIVE_SCOPE_START for r in known)
        listed = sum(is_ipo(r) for r in known)
        if early:
            out.append(f"COMPLETENESS: first_seen < {LIVE_SCOPE_START} olan kasa kodlu satır ({early})")
        if listed:
            out.append(f"COMPLETENESS: ipos.csv'de halka arz olarak geçen kodla eşleşen kasa kodlu satır ({listed})")
    else:
        if len(known) != KNOWN_COMPLETENESS_SEALED_ROWS:                        # pinli istisna; yeni satır -> gözden geçir
            out.append(f"COMPLETENESS (kapalı kip): kasa kodlu satır sayısı {len(known)} != pin {KNOWN_COMPLETENESS_SEALED_ROWS}")
        if not all(r["first_seen"] >= LIVE_SCOPE_START and r["ipos_status"] == "OUT_OF_SCOPE" for r in known):
            out.append("COMPLETENESS (kapalı kip): kasa kodlu satır first_seen ≥ başlangıç ve OUT_OF_SCOPE değil")
    return out, len(known)


def test_completeness_sealed_exception_two_mode_mutation():
    """Kabul (SPEC_DEVIATIONS M23): COMPLETENESS kasa-kodu istisnasının iki kipi sentetik satırlarla. Açık kip: live-scope'ta
    halka arz olmayan kasa kodlu satır serbest, sayısı pinsiz; first_seen < LIVE_SCOPE_START ya da ipos.csv'de halka arz olarak geçen
    kod -> kırmızı. Kapalı kip: bugünkü iddialar (pin 1, OUT_OF_SCOPE); yeni satır -> kırmızı. Kod adı çıktıya yazılmaz."""
    _, sealed = _cohort_codes()
    if not sealed:
        return
    cols = ("first_seen", "code", "ticker", "name", "instrument_group", "market", "traded_first_seen", "classification", "reason",
            "ipos_status", "ipos_first_trading_date")

    def row(first_seen, code, ipos_status="", classification="TEMERRUT_PAZARI"):
        d = dict.fromkeys(cols, "")
        d.update(first_seen=first_seen, code=f"{code}.TE", ticker=code, name=f"{code} -TEMERR", instrument_group="EQT", market="Z",
                 traded_first_seen="1", classification=classification, ipos_status=ipos_status)
        return d

    oos = row(LIVE_SCOPE_START, sealed[0], "OUT_OF_SCOPE", "IPOS_CSV")         # kapalı kipin tek pinli satırı
    buyin = [row("2026-09-24", sealed[1]), row("2026-09-25", sealed[2]), row("2026-09-25", sealed[3])]
    ipos = [{"ticker": sealed[0], "status": "OUT_OF_SCOPE"}, {"ticker": "ZZZZZ", "status": "FROZEN"}]
    # açık kip: live-scope, halka arz olmayan satırlar serbest; sayı pini yok
    assert completeness_sealed_problems([oos], sealed, ipos, True) == ([], 1)
    assert completeness_sealed_problems([oos, *buyin], sealed, ipos, True) == ([], 4)
    # first_seen < LIVE_SCOPE_START -> kırmızı
    early = row("2026-08-06", sealed[1])
    probs, n = completeness_sealed_problems([oos, *buyin, early], sealed, ipos, True)
    assert n == 5 and probs == [f"COMPLETENESS: first_seen < {LIVE_SCOPE_START} olan kasa kodlu satır (1)"]
    # ipos.csv'de halka arz olarak geçen kod -> kırmızı (satırın kodu ya da yalnız ad alanındaki eşleşme)
    ipos_listed = [*ipos, {"ticker": sealed[1], "status": "SKIPPED"}]
    probs, n = completeness_sealed_problems([oos, *buyin], sealed, ipos_listed, True)
    assert n == 4 and probs == ["COMPLETENESS: ipos.csv'de halka arz olarak geçen kodla eşleşen kasa kodlu satır (1)"]
    by_name = row("2026-09-24", "WARRANT1")
    by_name["name"] = f"{sealed[1]} -TEMERR"
    probs, _ = completeness_sealed_problems([by_name], sealed, ipos_listed, True)
    assert probs == ["COMPLETENESS: ipos.csv'de halka arz olarak geçen kodla eşleşen kasa kodlu satır (1)"]
    # satırın kendi ipos_status'ü halka arz -> kırmızı
    probs, _ = completeness_sealed_problems([row("2026-09-24", sealed[1], "FROZEN", "IPOS_CSV")], sealed, ipos, True)
    assert probs == ["COMPLETENESS: ipos.csv'de halka arz olarak geçen kodla eşleşen kasa kodlu satır (1)"]
    # kapalı kip: bugünkü iddialar aynen
    assert completeness_sealed_problems([oos], sealed, ipos, False) == ([], 1)
    probs, n = completeness_sealed_problems([oos, buyin[0]], sealed, ipos, False)           # yeni satır -> kırmızı
    assert n == 2 and probs[0] == "COMPLETENESS (kapalı kip): kasa kodlu satır sayısı 2 != pin 1" and len(probs) == 2
    probs, n = completeness_sealed_problems([buyin[0]], sealed, ipos, False)                # pin tutar ama OUT_OF_SCOPE değil
    assert n == 1 and probs == ["COMPLETENESS (kapalı kip): kasa kodlu satır first_seen ≥ başlangıç ve OUT_OF_SCOPE değil"]
    probs, n = completeness_sealed_problems([row("2026-08-06", sealed[0], "OUT_OF_SCOPE", "IPOS_CSV")], sealed, ipos, False)
    assert n == 1 and len(probs) == 1
    # kasa kodlu olmayan satır hiçbir kipte sayılmaz
    plain = row("2026-09-24", "ZZZZY")
    assert completeness_sealed_problems([plain], sealed, ipos, True) == ([], 0)
    assert completeness_sealed_problems([oos, plain], sealed, ipos, False) == ([], 1)


def test_cohort_guard_t4_mutation(tmp_path):
    """T4 mutasyonu (sentetik data/ kopyası): v2'ye bir kasa kodu eklenince kırmızı; açık küme kodu v2'de serbest, başka bir
    data/ dosyasında kırmızı; sonuç dizinindeki kasa kodu da kırmızı. Kod adı çıktıya yazılmaz."""
    codes, sealed = _cohort_codes()
    if not sealed or not (ROOT / V2_TABLE_REL).exists():
        return
    open_codes = sorted(r["ticker"] for r in _members() if reg.is_open(r["vault"]))
    d = tmp_path / "data"
    d.mkdir()
    v2 = d / "training_table_v2.csv"
    v2.write_bytes((ROOT / V2_TABLE_REL).read_bytes())
    probs = cohort_code_problems(d, codes, sealed)                          # yerel değişkenler: hata çıktısı kod basmaz
    assert probs == []                                                            # gerçek v2: açık kodlar serbest
    v2.write_bytes((ROOT / V2_TABLE_REL).read_bytes() + f"{sealed[0]},2021-01-01\n".encode("utf-8"))
    probs = cohort_code_problems(d, codes, sealed)
    assert probs == ["data/training_table_v2.csv: kasa kodu (1 farklı)"]
    v2.write_bytes((ROOT / V2_TABLE_REL).read_bytes())
    (d / "training_table_v3.csv").write_text(f"ticker\n{open_codes[0]}\n", encoding="utf-8")
    probs = cohort_code_problems(d, codes, sealed)
    assert probs == ["data/training_table_v3.csv: kohort kodu (1 farklı) sonuç dizini ya da data/training_table_v2.csv dışında"]
    (d / "training_table_v3.csv").unlink()
    (d / "outcomes_oot").mkdir()
    (d / "outcomes_oot" / "x.csv").write_text(f"h\n{sealed[-1]}\n", encoding="utf-8")
    probs = cohort_code_problems(d, codes, sealed)
    assert probs == ["data/outcomes_oot/x.csv: kasa kodu (1 farklı)"]


def test_cohort_file_is_append_only_in_history():
    """§1: kohort dosyasının her commit'li sürümü bir sonrakinin (ve çalışma kopyasının) önekidir."""
    rel = "registry/oot/cohort_pre_h99.csv"
    git = sc.Git(ROOT)
    versions = [git.show(c, rel).encode("utf-8") + b"\n" for c in git.history(rel)]
    if reg.COHORT_PATH.exists():
        versions.append(reg.COHORT_PATH.read_bytes())
    for a, b in zip(versions, versions[1:]):
        assert reg.cohort_append_only_problems(a, b) == []

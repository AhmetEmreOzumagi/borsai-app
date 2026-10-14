"""Kasanın tek seferlik açılışı (BORSAI_FAZ7_VAULT_OPEN; SPEC_DEVIATIONS M-A…M-L): M-B açılış kapısı, M-C pinli yeniden indirme ve
`VaultFetcher`, M-D işaret dosyası, M-E iki kipli kasa bekçisi ve açılış yetkisi, M-F `post_d1_sealed` / `post_d1_all`, M-G kayıt
kapsamı, M-H komutlar, M-I B kapısı.

Sentetik geçici git depolarında (gerçek kasa verisi YOK, ağ yok): zaman çizelgesi gerçek sıranın aynısıdır — modeller → S1 → S2 →
açık kümenin S3a / S3b / S5'i → ön-kayıtlı dört belge → `vault-d1` (VA1) → `vault-post-d1` (VA2) → kanıt → `vault-s5` (VB). Kodlar
sentetiktir (SYN* açık, SYK* kasa); gerçek kohort kodu hiçbir çıktıya yazılmaz. Gerçek depoda yalnız: bellek koşusu commit'li
scores_oot.json ile tam eşit (M-F; FAZ7_VAULT_SCORE T7, SPEC_DEVIATIONS M21), bu görevin yeni dosyalarında kasa kodu yok."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from borsai import freeze as fz
from borsai import outcomes as oc
from borsai import outcomes_oot as oo
from borsai import registry as reg
from borsai import scoring as sc
from borsai.provenance import ROOT, canonical_sha256, pretty_json_bytes, sha256_bytes, sha256_file

import faz6_support as f6
from conftest import GIT_HISTORY_REASON, git_history_present

# Herkese açık ayna (K-MIR-3): REAL_MARKER (M-F) içe aktarmada gerçek deponun kasa işaretini push kanıtıyla doğrular; özel repo
# geçmişi yoksa modül toplanamaz. Bu yüzden atlama modül düzeyindedir; özel repoda etkisiz.
if not git_history_present():
    pytest.skip(GIT_HISTORY_REASON, allow_module_level=True)

NOW = datetime(2026, 9, 29, 9, 0, 0, tzinfo=timezone.utc)
F3_T, NC_T, LATE_T = "SYKX", "SYKY", "SYKZ"          # kasada: f3 boş (REFUSED), D1 tavan değil (NOT_APPLICABLE), geç görünüş
CODE = re.compile(r"\bSY[NK][A-Z]\b")


@pytest.fixture(scope="module")
def cal():
    return oo.load_calendar_oot()


def _members(cal):
    days = [s for s in cal.sessions if "2021-03-01" <= s <= "2021-11-30"]
    picks = days[::7][:24]
    out = [{"ticker": f"SYN{chr(65 + i)}", "ftd": d} for i, d in enumerate(picks[0::2])]
    out += [{"ticker": f"SYK{chr(65 + i)}", "ftd": d, "vault": reg.VAULT_SEALED} for i, d in enumerate(picks[1::2])]
    out += [{"ticker": F3_T, "ftd": days[-9], "f3": None, "vault": reg.VAULT_SEALED},
            {"ticker": NC_T, "ftd": days[-6], "vault": reg.VAULT_SEALED},
            {"ticker": LATE_T, "ftd": days[-3], "vault": reg.VAULT_SEALED}]
    return out


def _paths(cal, members):
    """D1 ve D2 tavan, D3'te kırılma; NC_T'de D1 tavan değil; LATE_T ilk işlem gününden iki seans sonra görünür."""
    out = {}
    for i, m in enumerate(members):
        start = m["ftd"] if m["ticker"] != LATE_T else [s for s in cal.sessions if s > m["ftd"]][1]
        k = f"{i:02d}"
        closes = ["11.55", "12.70", f"12.{k}"] + [f"12.{k}"] * 9
        uppers = (["11.60"] if m["ticker"] == NC_T else ["11.55"]) + ["12.70", "13.97"] + ["13.30"] * 9
        out[m["ticker"]] = f6.ceiling_path(cal.sessions, start, closes, uppers)
    return out


def _proof(root, sha, t):
    f6.make_proof(root, sha, f"2026-09-{t}Z")


@pytest.fixture(scope="module")
def base(tmp_path_factory, cal):
    """Modeller → S1 → S2 → açık küme S3a / S3b / S5 → dört ön-kayıtlı belge; her commit kanıtlı, sırayla. Kasa kapalı."""
    tmp = tmp_path_factory.mktemp("faz7_vault")
    root = f6.init_repo(tmp, with_models=True)
    members = _members(cal)
    c = {"models": f6.git(root, "rev-parse", "HEAD")}
    f6.write_members(root, members, sessions=cal.sessions)
    c["s1"] = f6.commit(root, "S1", "registry/oot")
    fz.write_oot_records(root / "registry" / "oot" / "cohort_pre_h99.csv", now=datetime(2026, 9, 24, 22, 0, tzinfo=timezone.utc),
                         records_dir=root / "registry" / "oot" / "records", root=root, code_root=root)
    c["s2"] = f6.commit(root, "S2", "registry/oot/records")
    for key, t in (("models", "24T10:00:00"), ("s1", "24T10:05:00"), ("s2", "24T10:10:00")):
        _proof(root, c[key], t)
    window = [s for s in cal.sessions if s >= "2021-02-20"][:230]
    files = f6.market(window, _paths(cal, members))
    q = tmp / "q"
    kw = dict(root=root, qdir=q, downloader=f6.FakeDownloader(files), prober=lambda u: False, calendar=cal)
    oo.extract_d1_rows(**kw)
    c["s3a"] = f6.commit(root, "S3a", "registry/oot/d1_rows", "data/raw/bist/MANIFEST_OOT.csv")
    oo.s3_post_d1(root=root, now=NOW)
    c["s3b"] = f6.commit(root, "S3b", "registry/oot/post_d1")
    _proof(root, c["s3a"], "25T13:05:56")
    _proof(root, c["s3b"], "25T13:05:58")
    oo.extract_open_members(**kw)
    c["s5"] = f6.commit(root, "S5", "data")
    _proof(root, c["s5"], "25T13:45:54")
    for rel in oo.VAULT_OPENING_DOCS:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(f"sentetik ön-kayıtlı belge: {rel}\n", encoding="utf-8")
    c["docs"] = f6.commit(root, "dört belge", "docs")
    _proof(root, c["docs"], "28T19:06:01")
    return {"root": root, "q": q, "commits": c, "members": members, "files": files, "tmp": tmp}


def _clone(base, dst: Path) -> tuple[Path, Path]:
    shutil.copytree(base["root"], dst / "repo", symlinks=True)
    shutil.copytree(base["q"], dst / "q")
    return dst / "repo", dst / "q"


def _sealed(base):
    return sorted(m["ticker"] for m in base["members"] if m.get("vault") == reg.VAULT_SEALED)


def _open(base):
    return sorted(m["ticker"] for m in base["members"] if m.get("vault") != reg.VAULT_SEALED)


def _run(cmd, root, q, cal, capsys, *, downloader, head=None, proofs=None):
    heads = []
    head = head or (lambda u: heads.append(u) or {"status": 404, "content_type": "text/html", "content_length": "9"})
    rc = oo.main([cmd, "--quarantine", str(q), "--pace", "0"], root=root, downloader=downloader, head=head, calendar=cal,
                 now=NOW, proofs=proofs)
    text = capsys.readouterr().out
    out = json.loads(text)
    if out["durum"] == "TAMAM":
        assert not CODE.search(text), text                                   # çıktı yalnız sayı
    assert not re.search(r"\bSYK[A-Z]\b", text)                              # kasa kodu hiçbir çıktıda (DUR dahil)
    return rc, out, heads


def _snapshot(root: Path, rels) -> dict[str, bytes]:
    return {r: (root / r).read_bytes() for r in rels}


def _tracked(root: Path, *prefixes: str) -> list[str]:
    return f6.git(root, "ls-files", "--", *prefixes).splitlines()


# ================================================================ M-B: açılış kapısı

def test_vault_gate_requires_four_committed_unchanged_pushed_documents_and_download_gate(base, tmp_path, cal, capsys):
    root, q = _clone(base, tmp_path)
    assert oo.vault_gate_problems(root=root) == []
    ev, problems = oo.vault_docs_evidence(root)
    assert problems == [] and [d["path"] for d in ev] == list(oo.VAULT_OPENING_DOCS)
    assert {d["added_commit"] for d in ev} == {base["commits"]["docs"]} and {d["last_commit_push_proof_created_at"] for d in ev} == {
        "2026-09-28T19:06:01Z"}
    (root / "registry" / "push_proofs" / f"{base['commits']['docs']}.json").unlink()      # belgelerin kanıtı yok
    assert oo.vault_gate_problems(root=root) == [f"{d}: push kanıtı yok" for d in oo.VAULT_OPENING_DOCS]
    dl = f6.FakeDownloader(base["files"])
    with pytest.raises(oo.GateError, match="M-B"):
        oo.open_vault(root=root, qdir=q, downloader=dl)
    rc, out, heads = _run("vault-d1", root, q, cal, capsys, downloader=dl)
    assert (rc, out["hata"], dl.calls, heads) == (2, "GateError", [], [])     # hiçbir HEAD ve zip yok
    _proof(root, base["commits"]["docs"], "28T19:06:01")
    doc = root / oo.VAULT_OPENING_DOCS[2]
    doc.write_text(doc.read_text(encoding="utf-8") + "değişti\n", encoding="utf-8")   # çalışma kopyasında değişmiş
    assert oo.vault_gate_problems(root=root) == [f"{oo.VAULT_OPENING_DOCS[2]}: commit'ten sonra değişmiş"]
    f6.git(root, "checkout", "--", oo.VAULT_OPENING_DOCS[2])
    f6.git(root, "rm", "-q", "--", oo.VAULT_OPENING_DOCS[3])                  # belge commit'li değil
    f6.commit(root, "bir belge silindi", "docs")
    assert oo.vault_gate_problems(root=root) == [f"{oo.VAULT_OPENING_DOCS[3]}: commit'li değil"]
    root2, q2 = _clone(base, tmp_path / "b")                                  # belgeler tamam, indirme kapısı kapalı
    inp = root2 / "registry" / "oot" / "inputs" / "SYNA.json"
    inp.write_bytes(inp.read_bytes() + b"\n")
    assert oo.vault_docs_evidence(root2)[1] == [] and oo.vault_gate_problems(root=root2)
    rc, out, heads = _run("vault-d1", root2, q2, cal, capsys, downloader=dl)
    assert (rc, out["hata"], dl.calls, heads) == (2, "GateError", [], [])
    assert not (root2 / oo.VAULT_MARKER_REL).exists() and not any((root2 / "registry" / "oot" / "d1_rows" / f"{t}.json").exists()
                                                                    for t in _sealed(base))


# ================================================================ M-C: yeniden indirme ve VaultFetcher

def test_open_vault_redownloads_every_pin_and_stops_on_one_mismatch(base, tmp_path, cal, capsys):
    root, q = _clone(base, tmp_path)
    rows = oo.read_manifest_oot(root / oo.MANIFEST_OOT_REL)
    dl = f6.FakeDownloader(base["files"])
    fresh, stats = {}, {}
    got = oo.open_vault(root=root, qdir=q, downloader=dl, fresh=fresh, stats=stats)
    assert isinstance(got, oo.VaultUnsealed) and got.basis == oo.UNSEALED_BY_OPEN_VAULT and sorted(got) == _sealed(base)
    assert stats == {"n_manifest_rows": len(rows), "n_redownloaded": len(rows), "n_sha_equal": len(rows), "n_mismatch": 0}
    assert sorted(dl.calls) == sorted(r["url"] for r in rows) and set(fresh) == {(r["date"], r["kind"]) for r in rows}
    bad_url = rows[len(rows) // 2]["url"]
    files = {**base["files"], bad_url: base["files"][bad_url] + b"x"}          # tek uyuşmazlık
    with pytest.raises(oc.SourceChanged):
        oo.open_vault(root=root, qdir=q, downloader=f6.FakeDownloader(files))
    before = _snapshot(root, [oo.MANIFEST_OOT_REL])
    rc, out, _ = _run("vault-d1", root, q, cal, capsys, downloader=f6.FakeDownloader(files))
    assert (rc, out["hata"]) == (2, "SourceChanged")
    assert _snapshot(root, [oo.MANIFEST_OOT_REL]) == before and not (root / oo.VAULT_MARKER_REL).exists()
    assert not any((root / "registry" / "oot" / "d1_rows" / f"{t}.json").exists() for t in _sealed(base))   # hiçbir kasa dosyası


def _evidence_file(path: Path, day: str, sha: str, size: int) -> Path:
    row = {k: "" for k in oo.CAL_EVIDENCE_COLUMNS}
    row.update(date=day, source=oo.SOURCE_XU100_GAP, thb_head_status="200", thb_sha256=sha, thb_bytes=str(size), n_rows="3",
               n_equity_rows="2", n_equity_rows_traded="0", decision=oo.EV_PUBLISHED_NO_TRADING,
               checked_at_istanbul="2026-09-25T13:00:00+03:00")
    path.write_bytes(oo.evidence_bytes([row]))
    return path


def test_vault_fetcher_equal_green_and_each_mismatch_kind_red(tmp_path):
    """M-C: her zip o koşuda indirilir (aynı koşunun taze indirmesi önbellek); karantina kopyası, MANIFEST_OOT pini ve kanıt THB
    pini ile eşit olmalı; her uyuşmazlık türü tek başına DUR ve hiçbir şey yazılmaz; karantinada yoksa karantinaya yazılır."""
    day = "2021-03-01"
    data = f6.make_zip(day, "thb", [f6.thb_row("SYKA.E", "11.55")])
    other = f6.make_zip(day, "thb", [f6.thb_row("SYKA.E", "11.56")])
    url, sha = oc.source_url(day, "thb"), sha256_bytes(data)
    pin = [{"date": day, "kind": "thb", "sha256": sha}]

    def quarantine(qdir, content):
        oc._write_new(oc.local_path(day, "thb", qdir), content)
        oc._append_csv(qdir / oc.MANIFEST_NAME, oc.MANIFEST_COLUMNS, {
            "date": day, "kind": "thb", "url": url, "sha256": sha256_bytes(content), "bytes": len(content),
            "internal_filename": oc.internal_name(day, "thb"), "downloaded_at": "t0", "http_last_modified": "LM0"})
        return qdir

    ev = _evidence_file(tmp_path / "ev.csv", day, sha, len(data))
    q = quarantine(tmp_path / "q_ok", data)
    dl = f6.FakeDownloader({url: data})
    f = oo.VaultFetcher(qdir=q, downloader=dl, manifest_rows=pin, evidence_path=ev, now=NOW)
    got, p = f(day, "thb")
    assert got == data and p.sha256 == sha and (p.downloaded_at, p.http_last_modified) == ("t0", "LM0") and dl.calls == [url]
    f(day, "thb")
    assert dl.calls == [url] and (f.n_network, f.n_from_fresh) == (1, 1)     # aynı koşuda ikinci okuma: taze önbellek
    cases = {"karantina": dict(qdir=quarantine(tmp_path / "q_bad", other), manifest_rows=pin, evidence_path=ev),
             "MANIFEST_OOT": dict(qdir=quarantine(tmp_path / "q2", data), manifest_rows=[{**pin[0], "sha256": "0" * 64}],
                                  evidence_path=ev),
             "kanıt": dict(qdir=quarantine(tmp_path / "q3", data), manifest_rows=pin,
                           evidence_path=_evidence_file(tmp_path / "ev_bad.csv", day, "1" * 64, len(data)))}
    for name, kw in cases.items():
        snap = sorted((p.name, p.read_bytes()) for p in kw["qdir"].rglob("*") if p.is_file())
        with pytest.raises(oc.SourceChanged):
            oo.VaultFetcher(downloader=f6.FakeDownloader({url: data}), now=NOW, **kw)(day, "thb")
        assert sorted((p.name, p.read_bytes()) for p in kw["qdir"].rglob("*") if p.is_file()) == snap, name
    q_new = tmp_path / "q_new"                                                # karantinada yok: yazılır, pin karantina satırından
    f = oo.VaultFetcher(qdir=q_new, downloader=f6.FakeDownloader({url: data}), manifest_rows=pin, evidence_path=ev, now=NOW)
    _, p = f(day, "thb")
    assert oc.local_path(day, "thb", q_new).read_bytes() == data and f.n_quarantined == 1
    man = oc.read_manifest(q_new)
    assert len(man) == 1 and man[0]["sha256"] == sha == p.sha256 and man[0]["downloaded_at"] == p.downloaded_at
    with pytest.raises(oc.SourceChanged):                                      # artık karantinadaki kopyayla karşılaştırılır
        oo.VaultFetcher(qdir=q_new, downloader=f6.FakeDownloader({url: other}), evidence_path=None)(day, "thb")


# ================================================================ M-D, M-H: vault-d1 (VA1)

def _va1(base, dst, cal, capsys):
    root, q = _clone(base, dst)
    dl = f6.FakeDownloader(base["files"])
    rc, out, heads = _run("vault-d1", root, q, cal, capsys, downloader=dl)
    assert (rc, out["durum"]) == (0, "TAMAM"), out
    return root, q, out, dl, heads


def test_vault_d1_writes_sealed_d1_rows_pins_and_marker_and_is_rerun_safe(base, tmp_path, cal, capsys):
    root0 = base["root"]
    open_before = _snapshot(root0, [f"registry/oot/d1_rows/{t}.json" for t in _open(base)])
    man_before = (root0 / oo.MANIFEST_OOT_REL).read_bytes()
    root, q, out, dl, heads = _va1(base, tmp_path, cal, capsys)
    sealed = _sealed(base)
    rows_before = man_before.decode("utf-8").count("\n") - 1
    assert (out["n_sealed"], out["sealed_extracted"], out["written"], out["unchanged"]) == (len(sealed), len(sealed), len(sealed), 0)
    assert out["redownload"] == {"n_manifest_rows": rows_before, "n_redownloaded": rows_before, "n_sha_equal": rows_before,
                                 "n_mismatch": 0}
    assert out["d1_after_first_trading_date"] == 1 and out["documents"] == 4 and out["marker"] == "CREATED"
    assert out["manifest_rows_added"] == 2 * out["new_d1_dates_not_previously_pinned"] > 0
    assert _snapshot(root, open_before) == open_before                         # açık küme dosyaları bayt-eşit
    man = (root / oo.MANIFEST_OOT_REL).read_bytes()
    assert man.startswith(man_before)                                          # yalnız ekleme
    rows = oo.read_manifest_oot(root / oo.MANIFEST_OOT_REL)
    for r in rows[rows_before:]:
        assert sha256_file(oc.local_path(r["date"], r["kind"], q)) == r["sha256"]   # yeni sha = karantina = taze indirme
        assert r["sha256"] == sha256_bytes(base["files"][r["url"]])
    for t in sealed:
        doc = json.loads((root / "registry" / "oot" / "d1_rows" / f"{t}.json").read_text(encoding="utf-8"))
        assert oo.d1_rows_problems(doc, rows) == [] and doc["exposure_class"] == "MACHINE_SEQUENCED"
        assert doc["d1"]["session_h"] == 1 and doc["d1"]["session_date"] >= doc["first_trading_date"]
    marker = json.loads((root / oo.VAULT_MARKER_REL).read_text(encoding="utf-8"))
    assert oo.vault_marker_problems(marker, sealed) == [] and set(marker) == oo.VAULT_MARKER_KEYS
    assert marker["n_sealed"] == len(sealed) and marker["code"]["git_head"] == f6.git(root, "rev-parse", "HEAD")
    assert marker["manifest_oot_before"] == {"path": oo.MANIFEST_OOT_REL, "source": "HEAD", "sha256": sha256_bytes(man_before),
                                             "n_rows": rows_before}
    assert [d["path"] for d in marker["documents"]] == list(oo.VAULT_OPENING_DOCS)
    assert not CODE.search((root / oo.VAULT_MARKER_REL).read_text(encoding="utf-8"))   # işaret dosyasında kod yok
    assert oo.s2_gate_problems(root=root) == []                                # işaret ve d1_rows indirme kapısını kapatmaz
    snap = _snapshot(root, [oo.VAULT_MARKER_REL, oo.MANIFEST_OOT_REL] + [f"registry/oot/d1_rows/{t}.json" for t in sealed])
    rc, again, _ = _run("vault-d1", root, q, cal, capsys, downloader=f6.FakeDownloader(base["files"]))
    assert (rc, again["written"], again["unchanged"], again["marker"], again["manifest_rows_added"]) == (0, 0, len(sealed),
                                                                                                        "UNCHANGED", 0)
    assert _snapshot(root, snap) == snap                                       # yeniden koşu: dokunulmaz (zaman alanları dahil)
    m = json.loads((root / oo.VAULT_MARKER_REL).read_text(encoding="utf-8"))
    later = {**m, "opened_at_utc": "2026-09-30T00:00:00Z"}
    assert oo.write_vault_marker(later, root / oo.VAULT_MARKER_REL, sealed) == "UNCHANGED"
    with pytest.raises(oo.OotOutcomeError, match="aynı değil"):
        oo.write_vault_marker({**m, "redownload": {**m["redownload"], "n_manifest_rows": 1, "n_redownloaded": 1,
                                                   "n_sha_equal": 1}}, root / oo.VAULT_MARKER_REL, sealed)
    with pytest.raises(oo.OotOutcomeError, match="şemadan"):
        oo.write_vault_marker({**m, "note": sealed[0]}, tmp_path / "x.json", sealed)


def test_vault_d1_writes_nothing_when_a_later_member_stops(base, tmp_path, cal, capsys, monkeypatch):
    """Bütün denetimler yazımdan önce: son kasa üyesinde DUR -> hiçbir d1_rows, pin ya da işaret dosyası yazılmaz."""
    root, q = _clone(base, tmp_path)
    real = oo.resolve_member
    last = _sealed(base)[-1]

    def stop_at_last(t, *a, **kw):
        if t == last:
            raise oo.OotOutcomeError("sentetik DUR")
        return real(t, *a, **kw)

    monkeypatch.setattr(oo, "resolve_member", stop_at_last)
    man = (root / oo.MANIFEST_OOT_REL).read_bytes()
    rc, out, _ = _run("vault-d1", root, q, cal, capsys, downloader=f6.FakeDownloader(base["files"]))
    assert (rc, out["hata"]) == (2, "OotOutcomeError") and (root / oo.MANIFEST_OOT_REL).read_bytes() == man
    assert not (root / oo.VAULT_MARKER_REL).exists()
    assert sorted(p.stem for p in (root / "registry" / "oot" / "d1_rows").glob("*.json")) == _open(base)


# ================================================================ M-G, M-H: vault-post-d1 (VA2)

def _commit_va1(root):
    return f6.commit(root, "VA1", "registry/oot/d1_rows", "registry/oot/VAULT_OPEN.json", "data/raw/bist/MANIFEST_OOT.csv")


def test_vault_post_d1_needs_committed_marker_and_covers_every_sealed_member(base, tmp_path, cal, capsys):
    root, q, *_ = _va1(base, tmp_path, cal, capsys)
    sealed = _sealed(base)
    nodl = f6.FakeDownloader({})
    rc, out, heads = _run("vault-post-d1", root, q, cal, capsys, downloader=nodl)          # işaret commit'siz: DUR
    assert (rc, out["hata"], nodl.calls, heads) == (2, "GateError", [], [])
    assert not any((root / "registry" / "oot" / "post_d1" / t).exists() for t in sealed)
    c_va1 = _commit_va1(root)
    rc, out, heads = _run("vault-post-d1", root, q, cal, capsys, downloader=nodl)
    assert (rc, out["d1_rows"], out["written"], out["already_present"]) == (0, len(sealed), len(sealed), 0)
    assert out["status"] == {"NOT_APPLICABLE": 1, "PREDICTED": len(sealed) - 2, "REFUSED": 1}
    assert out["codes"] == {"NOT_APPLICABLE:D1_NOT_CEILING": 1, "REFUSED:F3_MISSING": 1} and nodl.calls == [] and heads == []
    post, rd = root / "registry" / "oot" / "post_d1", root / "registry" / "oot" / "records"
    refused_f3 = set()
    for t in sealed:
        (p, rec), = fz.active_records(t, post)
        d1doc = json.loads((root / "registry" / "oot" / "d1_rows" / f"{t}.json").read_text(encoding="utf-8"))
        assert rec["schema_version"] == "borsai.oot_post_d1_record/1" and rec["exposure_class"] == "MACHINE_SEQUENCED"
        assert rec["code"]["git_head"] == c_va1 and rec["code"]["borsai_dirty"] is False
        assert rec["d1_rows"]["sha256"] == canonical_sha256(d1doc)
        assert rec["base_record"]["file"] == fz.oot_base_record(t, rd)[0].relative_to(root).as_posix()
        if rec["models"][0]["status"] == "REFUSED" and rec["models"][0]["refusal"]["code"] == "F3_MISSING":
            refused_f3.add(t)
    s2_refused = {t for t in sealed if next(c for c in fz.oot_base_record(t, rd)[1]["models"]
                                            if c["model_id"] == "ceiling_hazard_v0")["status"] == "REFUSED"}
    assert refused_f3 == s2_refused == {F3_T}                                   # f3 REFUSED kümesi birebir
    rc, out, _ = _run("vault-post-d1", root, q, cal, capsys, downloader=nodl)
    assert (rc, out["written"], out["already_present"], out["records"]) == (0, 0, len(sealed), len(sealed))
    assert len(_tracked(root, "registry/oot/post_d1")) == len(_open(base))      # açık küme kayıtları dokunulmadı


# ================================================================ M-I: B kapısı ve vault-s5 (VB)

def _through_va2(base, dst, cal, capsys):
    root, q, *_ = _va1(base, dst, cal, capsys)
    c_va1 = _commit_va1(root)
    _run("vault-post-d1", root, q, cal, capsys, downloader=f6.FakeDownloader({}))
    c_va2 = f6.commit(root, "VA2", "registry/oot/post_d1")
    return root, q, c_va1, c_va2


def test_vault_s3_gate_requires_pushed_marker_d1_rows_and_post_d1_then_vault_s5(base, tmp_path, cal, capsys):
    root, q, c_va1, c_va2 = _through_va2(base, tmp_path, cal, capsys)
    sealed = _sealed(base)
    n = len(sealed)
    assert sorted(oo.vault_s3_gate_problems(root=root)) == sorted([
        "işaret dosyası push kanıtı yok", f"kasa d1_rows: push kanıtı yok: {n} üye", f"kasa POST_D1 kaydı: push kanıtı yok: {n} üye"])
    dl = f6.FakeDownloader(base["files"])
    rc, out, heads = _run("vault-s5", root, q, cal, capsys, downloader=dl)
    assert (rc, out["hata"], dl.calls, heads) == (2, "GateError", [], [])   # kapı kapalı: hiçbir HEAD ve zip yok
    _proof(root, c_va1, "29T12:00:00")
    assert oo.vault_s3_gate_problems(root=root) == [f"kasa POST_D1 kaydı: push kanıtı yok: {n} üye"]
    oo.vault_marker_unsealed(root)                                            # işaret kanıtlı: yetki var, B kapısı yine kapalı
    rc, out, heads = _run("vault-s5", root, q, cal, capsys, downloader=dl)
    assert (rc, out["hata"], dl.calls, heads) == (2, "GateError", [], [])
    _proof(root, c_va2, "29T12:00:02")
    assert oo.vault_s3_gate_problems(root=root) == []
    rec = next((root / "registry" / "oot" / "post_d1" / sealed[0]).glob("*.json"))      # kayıt yok -> kırmızı
    rec.rename(tmp_path / "rec.json")
    assert oo.vault_s3_gate_problems(root=root) == ["kasa üyesinin etkin POST_D1 kaydı yok: 1 üye"]
    (tmp_path / "rec.json").rename(rec)
    d1p = root / "registry" / "oot" / "d1_rows" / f"{sealed[1]}.json"
    d1p.write_bytes(d1p.read_bytes() + b"\n")
    assert oo.vault_s3_gate_problems(root=root) == ["kasa d1_rows: commit'ten sonra değişmiş: 1 üye"]
    f6.git(root, "checkout", "--", d1p.relative_to(root).as_posix())
    mk = root / oo.VAULT_MARKER_REL
    mk.write_bytes(mk.read_bytes() + b"\n")
    assert oo.vault_s3_gate_problems(root=root) == ["işaret dosyası commit'ten sonra değişmiş"]
    f6.git(root, "checkout", "--", oo.VAULT_MARKER_REL)
    assert oo.vault_s3_gate_problems(root=root) == []
    open_before = _snapshot(root, _tracked(root, "data/outcomes_oot"))
    man_before = (root / oo.MANIFEST_OOT_REL).read_bytes()
    rc, out, heads = _run("vault-s5", root, q, cal, capsys, downloader=dl)
    assert (rc, out["extracted"], out["actions"], out["n_sessions"]) == (0, n, {"CREATED": n}, {"10": n}), out
    assert out["read_more_than_resolved"] == 1 and out["row_status"] == {"OK": 10 * n} and len(heads) == 5
    assert _snapshot(root, open_before) == open_before and (root / oo.MANIFEST_OOT_REL).read_bytes().startswith(man_before)
    out_dir = root / "data" / "outcomes_oot"
    assert sorted(p.stem for p in out_dir.glob("*.csv")) == sorted(_open(base) + sealed)
    rows_all = oo.read_manifest_oot(root / oo.MANIFEST_OOT_REL)
    manifest = {(r["date"], r["kind"]): r["sha256"] for r in rows_all}
    for t in sealed:
        rows = oo.read_outcome_oot(out_dir / f"{t}.csv")
        d1doc = json.loads((root / "registry" / "oot" / "d1_rows" / f"{t}.json").read_text(encoding="utf-8"))["d1"]
        assert [r["h"] for r in rows] == [str(h) for h in range(1, 11)] and {r["outcome_basis"] for r in rows} == {"MACHINE_EXTRACTED"}
        assert rows[0]["session_date"] == d1doc["session_date"] and rows[0]["thb_sha256"] == d1doc["thb"]["sha256"]
        assert all(manifest[(r["session_date"], k)] == r[f"{k}_sha256"] for r in rows for k in ("thb", "thm"))
        raw = json.loads((out_dir / "raw" / f"{t}.json").read_text(encoding="utf-8"))
        assert max(s["session_date"] for s in raw["sessions"]) == rows[-1]["session_date"]     # D_10'dan sonra okuma yok
    for r in rows_all[man_before.decode("utf-8").count("\n") - 1:]:
        assert sha256_file(oc.local_path(r["date"], r["kind"], q)) == r["sha256"]
    snap = _snapshot(root, _tracked(root, "data") + [p.relative_to(root).as_posix() for p in out_dir.rglob("*") if p.is_file()])
    rc, again, _ = _run("vault-s5", root, q, cal, capsys, downloader=dl)
    assert (rc, again["actions"], again["manifest_rows_added"]) == (0, {"UNCHANGED": n}, 0) and _snapshot(root, snap) == snap


def test_vault_s5_stops_before_writing_when_d1_differs_from_d1_rows(base, tmp_path, cal, capsys, monkeypatch):
    root, q, c_va1, c_va2 = _through_va2(base, tmp_path, cal, capsys)
    _proof(root, c_va2, "29T12:00:02")
    monkeypatch.setattr(oo, "resolve_member", lambda *a, **kw: _shift_d1(oo_resolve(*a, **kw)))
    rc, out, _ = _run("vault-s5", root, q, cal, capsys, downloader=f6.FakeDownloader(base["files"]))
    assert (rc, out["hata"]) == (2, "OotOutcomeError") and "D_1" in out["mesaj"]
    assert sorted(p.stem for p in (root / "data" / "outcomes_oot").glob("*.csv")) == _open(base)


oo_resolve = oo.resolve_member


def _shift_d1(ext):
    """D_1'i bir seans kaydırılmış bir çözüm (d1_rows'la tutarsız ayıklamanın etkisi)."""
    import dataclasses

    res = ext.resolution
    return dataclasses.replace(ext, resolution=dataclasses.replace(res, sessions=res.sessions[1:]))


# ================================================================ M-E (d): açılış yetkisi yalnız iki yoldan

def test_sealed_rows_open_only_with_open_vault_result_or_pushed_marker(base, tmp_path, cal, capsys):
    vault = {"SYNA": reg.VAULT_OPEN, "SYKA": reg.VAULT_SEALED}
    calls = []
    for grant in ((), {"SYKA"}, frozenset({"SYKA"})):                           # düz küme yetki değil
        with pytest.raises(oo.SealedAccessError):
            oo.resolve_member("SYKA", "2021-03-02", cal, vault, unsealed=grant, fetch=lambda s, k: calls.append(s))
    assert calls == []
    with pytest.raises(ValueError):
        oo.VaultUnsealed({"SYKA"}, "ELLE")
    oo.assert_extractable("SYKA", vault, oo.VaultUnsealed({"SYKA"}, oo.UNSEALED_BY_OPEN_VAULT))
    with pytest.raises(oo.SealedAccessError):
        oo.assert_extractable("SYKA", vault, oo.VaultUnsealed({"SYKB"}, oo.UNSEALED_BY_OPEN_VAULT))
    root, q, *_ = _va1(base, tmp_path, cal, capsys)
    with pytest.raises(oo.GateError):                                          # işaret commit'siz
        oo.vault_marker_unsealed(root)
    c_va1 = _commit_va1(root)
    with pytest.raises(oo.GateError):                                          # commit'li ama push kanıtsız
        oo.vault_marker_unsealed(root)
    _proof(root, c_va1, "29T12:00:00")
    got = oo.vault_marker_unsealed(root)
    assert got.basis == oo.UNSEALED_BY_MARKER and sorted(got) == _sealed(base)
    mk = root / oo.VAULT_MARKER_REL
    mk.write_bytes(mk.read_bytes() + b"\n")
    with pytest.raises(oo.GateError):                                          # değişmiş işaret
        oo.vault_marker_unsealed(root)


# ================================================================ M-E (a)–(c): iki kipli kasa bekçisi ve mutasyonlar

def test_vault_hygiene_guard_two_modes_and_mutations(base, tmp_path, cal, capsys):
    sealed = _sealed(base)
    root, q = _clone(base, tmp_path / "closed")
    assert oo.vault_marker_state(root).open_mode is False and oo.vault_hygiene_problems(root) == []
    d1 = root / "registry" / "oot" / "d1_rows" / f"{sealed[0]}.json"
    d1.write_text('{"ticker": "%s"}\n' % sealed[0], encoding="utf-8")        # işaret yokken kasa dosyası -> kırmızı
    assert oo.vault_hygiene_problems(root) == ["kasa kodu, işaret dosyası yokken (kasa kapalı): 1 dosya"]
    d1.unlink()
    (root / "scores").mkdir(exist_ok=True)
    (root / "scores" / "scores_oot.json").write_text(json.dumps({"x": sealed[1]}), encoding="utf-8")
    assert oo.vault_hygiene_problems(root) == ["kasa kodu, işaret dosyası yokken (kasa kapalı): 1 dosya"]
    (root / "scores" / "scores_oot.json").unlink()

    root, q, *_ = _va1(base, tmp_path / "open", cal, capsys)                   # VA1 commit'siz: bekleyen commit
    assert oo.vault_marker_state(root).open_mode and oo.vault_hygiene_problems(root) == []
    c_va1 = _commit_va1(root)
    assert oo.vault_hygiene_problems(root) == []
    _run("vault-post-d1", root, q, cal, capsys, downloader=f6.FakeDownloader({}))
    assert oo.vault_hygiene_problems(root) == []
    f6.commit(root, "VA2", "registry/oot/post_d1")
    assert oo.vault_hygiene_problems(root) == []
    for rel, text, want in (                                                   # izinli yol dışında -> kırmızı
            ("data/outcomes_oot/SYNA.csv", None, "kasa kodu izinli yol dışında (üye yolu başka bir kodu taşıyor): 1"),
            (f"registry/oot/post_d1/{sealed[0]}/x.json", sealed[1], "kasa kodu izinli yol dışında (üye yolu başka bir kodu taşıyor): 1"),
            ("data/outcomes_oot/notlar.txt", sealed[0], "kasa kodu izinli yol dışında: 1"),
            (oo.MANIFEST_OOT_REL, None, "kasa kodu MANIFEST_OOT'ta ya da işaret dosyasında: 1")):
        p = root / rel
        old = p.read_bytes() if p.exists() else None
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((old or b"") + f"{text or sealed[2]}\n".encode("utf-8"))
        assert oo.vault_hygiene_problems(root) == [want], rel
        p.write_bytes(old) if old is not None else p.unlink()
    mk = root / oo.VAULT_MARKER_REL
    m = json.loads(mk.read_text(encoding="utf-8"))
    mk.write_bytes(pretty_json_bytes({**m, "rule": m["rule"] + " " + sealed[0]}))   # işaret dosyasında kod
    probs = oo.vault_hygiene_problems(root)
    assert "kasa kodu MANIFEST_OOT'ta ya da işaret dosyasında: 1" in probs and "işaret dosyası commit'ten sonra değişmiş: 1" in probs
    f6.git(root, "checkout", "--", oo.VAULT_MARKER_REL)
    assert oo.vault_hygiene_problems(root) == [] and oo.vault_marker_state(root).added_commit == c_va1

    root, q = _clone(base, tmp_path / "early")                                 # işaretten önceki commit'te kasa dosyası
    d1 = root / "registry" / "oot" / "d1_rows" / f"{sealed[0]}.json"
    d1.write_text('{"ticker": "%s"}\n' % sealed[0], encoding="utf-8")
    f6.commit(root, "erken kasa dosyası", "registry/oot/d1_rows")
    assert oo.vault_hygiene_problems(root) == ["kasa kodu, işaret dosyası yokken (kasa kapalı): 1 dosya"]
    d1.unlink()                                                               # vault-d1 dosyayı kendisi yazar (ilk koşu)
    rc, out, _ = _run("vault-d1", root, q, cal, capsys, downloader=f6.FakeDownloader(base["files"]))
    assert rc == 0
    assert oo.vault_hygiene_problems(root) == [
        "kasa dosyası işaret dosyasını ekleyen commit'ten önce (ya da işaret commit'siz iken) commit'lenmiş: 1"]
    _commit_va1(root)
    assert oo.vault_hygiene_problems(root) == [
        "kasa dosyası işaret dosyasını ekleyen commit'ten önce (ya da işaret commit'siz iken) commit'lenmiş: 1"]
    root2, _ = _clone(base, tmp_path / "shared")                               # ortak çıktının işaretten önceki sürümünde kod
    (root2 / "scores").mkdir(exist_ok=True)
    (root2 / "scores" / "scores_oot.json").write_text(json.dumps({"x": sealed[0]}), encoding="utf-8")
    f6.commit(root2, "erken skor", "scores")
    (root2 / oo.VAULT_MARKER_REL).write_bytes(mk.read_bytes())
    assert "ortak çıktının işaret commit'inden önceki bir sürümünde kasa kodu: 1" in oo.vault_hygiene_problems(root2)


def test_cohort_code_guard_two_modes(tmp_path):
    """M-E (c): data/ bekçisi (test_outcome_guard.cohort_code_problems) açık kipte kasa kodunu yalnız üyenin kendi sonuç
    dosyalarında (data/outcomes_oot/<T>.csv, raw/<T>.json) kabul eder; v2'de, başka bir sonuç dosyasında ya da data/'nın geri
    kalanında kırmızı; kapalı kipte her yerde kırmızı (bugünkü iddia)."""
    import test_outcome_guard as tog

    codes, sealed = ["SYKA", "SYKB", "SYNA"], ["SYKA", "SYKB"]
    d = tmp_path / "data"
    (d / "outcomes_oot" / "raw").mkdir(parents=True)
    (d / "outcomes_oot" / "SYKA.csv").write_text("h,ticker\n1,SYKA\n", encoding="utf-8")
    (d / "outcomes_oot" / "raw" / "SYKA.json").write_text('{"ticker": "SYKA"}\n', encoding="utf-8")
    assert tog.cohort_code_problems(d, codes, sealed) == ["data/outcomes_oot/SYKA.csv: kasa kodu (1 farklı)",
                                                          "data/outcomes_oot/raw/SYKA.json: kasa kodu (1 farklı)"]
    assert tog.cohort_code_problems(d, codes, sealed, vault_open=True) == []
    (d / "outcomes_oot" / "SYKA.csv").write_text("h,ticker\n1,SYKA\n2,SYKB\n", encoding="utf-8")        # başka üyenin kodu
    assert tog.cohort_code_problems(d, codes, sealed, vault_open=True) == ["data/outcomes_oot/SYKA.csv: kasa kodu (1 farklı)"]
    (d / "outcomes_oot" / "SYKA.csv").write_text("h,ticker\n1,SYKA\n", encoding="utf-8")
    (d / "training_table_v2.csv").write_text("ticker\nSYNA\nSYKA\n", encoding="utf-8")                    # v2'de kasa kodu
    assert tog.cohort_code_problems(d, codes, sealed, vault_open=True) == ["data/training_table_v2.csv: kasa kodu (1 farklı)"]
    (d / "training_table_v2.csv").write_text("ticker\nSYNA\n", encoding="utf-8")
    (d / "outcomes_oot" / "SYNA.csv").write_text("h,ticker\n1,SYKB\n", encoding="utf-8")                  # açık üyenin dosyasında
    assert tog.cohort_code_problems(d, codes, sealed, vault_open=True) == ["data/outcomes_oot/SYNA.csv: kasa kodu (1 farklı)"]
    (d / "outcomes_oot" / "SYNA.csv").unlink()
    (d / "raw").mkdir()
    (d / "raw" / "x.csv").write_text("SYKA\n", encoding="utf-8")                                          # data/'nın geri kalanı
    assert tog.cohort_code_problems(d, codes, sealed, vault_open=True) == [
        "data/raw/x.csv: kasa kodu (1 farklı)",
        "data/raw/x.csv: kohort kodu (1 farklı) sonuç dizini ya da data/training_table_v2.csv dışında"]


# ================================================================ M-F: post_d1_sealed / post_d1_all (sentetik)

@pytest.fixture(scope="module")
def vault_scores(base, tmp_path_factory, cal):
    tmp = tmp_path_factory.mktemp("faz7_vault_scores")
    root, q = _clone(base, tmp)
    closed = sc.build_oot_scores(root=root, now=NOW)
    kw = dict(root=root, qdir=q, downloader=f6.FakeDownloader(base["files"]), head=lambda u: {"status": 404}, calendar=cal, now=NOW,
              sleep=lambda s: None)
    oo.run_command("vault-d1", **kw)
    c_va1 = _commit_va1(root)
    oo.run_command("vault-post-d1", **kw)
    c_va2 = f6.commit(root, "VA2", "registry/oot/post_d1")
    _proof(root, c_va1, "29T12:00:00")
    _proof(root, c_va2, "29T12:00:02")
    before_vb = sc.build_oot_scores(root=root, now=NOW)
    oo.run_command("vault-s5", **kw)
    c_vb = f6.commit(root, "VB", "data")
    _proof(root, c_vb, "29T15:00:00")
    return {"root": root, "closed": closed, "before_vb": before_vb, "opened": sc.build_oot_scores(root=root, now=NOW)}


def test_post_d1_vault_keys_only_after_vault_opens_and_open_block_unchanged(vault_scores, base):
    closed, before_vb, s = vault_scores["closed"], vault_scores["before_vb"], vault_scores["opened"]
    for doc in (closed, before_vb):
        assert not {sc.OOT_POST_D1_SEALED, sc.OOT_POST_D1_ALL, sc.OOT_SUBSET_SEALED, sc.OOT_SUBSET_ALL} & set(doc)
        assert "## 10." not in sc.render_oot_doc(doc)
    canon = lambda d: pretty_json_bytes(d["post_d1"])  # noqa: E731
    assert canon(closed) == canon(before_vb) == canon(s)                       # açık küme bloğu bayt olarak aynı
    sealed, total = s[sc.OOT_POST_D1_SEALED], s[sc.OOT_POST_D1_ALL]
    assert sealed["scale"] == total["scale"] == sc.SCALE_OOT_POST_D1 and sealed["subset"] == sc.OOT_SUBSET_SEALED
    m = sealed["models"][0]
    sealed_codes = set(_sealed(base))
    assert m["model_id"] == "post_d1_hazard_v0" and {r["ticker"] for r in m["rows"]} == sealed_codes - {NC_T}
    assert {(r["class"], r["exposure_class"]) for r in m["rows"]} == {("OOT_BLIND", "MACHINE_SEQUENCED")}
    assert (m["n_scored"], m["n_refused"], m["n_not_applicable"], m["n_retro"]) == (len(sealed_codes) - 2, 1, 1, 0)
    prim = [c for c in m["cells"] if c["label"] == sc.LABEL_PRIMARY]
    assert [(c["output"], c["metric"], c["rule_id"]) for c in prim] == [("S_cond", "RPS", "ceiling_hazard_v0")]
    assert prim[0]["n"] == len(sealed_codes) - 2 and prim[0]["scale"] == sc.SCALE_OOT_POST_D1
    open_m = s["post_d1"]["models"][0]
    tm = total["models"][0]
    assert total["excluded_models"] == [] and [x["model_id"] for x in total["models"]] == ["post_d1_hazard_v0"]
    assert sorted(r["ticker"] for r in tm["rows"]) == sorted([r["ticker"] for r in open_m["rows"]] + [r["ticker"] for r in m["rows"]])
    assert tm["n_scored"] == open_m["n_scored"] + m["n_scored"] and tm["n_not_applicable"] == open_m["n_not_applicable"] + 1
    ctx = sc.OotContext(vault_scores["root"])
    fake_open = {"models": [{**open_m, "n_oot_retro": 1}]}                      # açık kümede RETRO çift -> birleştirilmez
    blocks = sc.oot_post_d1_vault_blocks(ctx, fake_open)
    assert blocks[sc.OOT_POST_D1_ALL]["models"] == [] and blocks[sc.OOT_POST_D1_ALL]["excluded_models"][0]["model_id"] == m["model_id"]
    doc = sc.render_oot_doc(json.loads(pretty_json_bytes(s)))
    assert doc == sc.render_oot_doc(s)
    assert "## 10. " + sc.OOT_POST_D1_SEALED_TITLE in doc and "## 11. " + sc.OOT_POST_D1_ALL_TITLE in doc
    assert doc.index("## 9.") < doc.index("## 10.") < doc.index("## 11.") and not CODE.search(doc)
    assert doc.partition("## 10.")[0] == sc.render_oot_doc({k: v for k, v in s.items()
                                                            if k not in (sc.OOT_POST_D1_SEALED, sc.OOT_POST_D1_ALL)}) + "\n"


# ================================================================ M-F: gerçek depo (bellek koşusu = commit'li dosya, tam eşitlik)

REAL_MARKER = oo.vault_marker_state(ROOT)
VAULT_SCORE_KEYS = {sc.OOT_POST_D1_SEALED, sc.OOT_POST_D1_ALL, sc.OOT_SUBSET_SEALED, sc.OOT_SUBSET_ALL}


def _diff_paths(a, b, path=""):
    if type(a) is not type(b):
        return {path}
    if isinstance(a, dict):
        out = set()
        for k in set(a) | set(b):
            out |= {f"{path}/{k}"} if k not in a or k not in b else _diff_paths(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return {f"{path}[len]"}
        return set().union(*(_diff_paths(x, y, f"{path}[]") for x, y in zip(a, b)))
    return set() if a == b else {path}


def scores_oot_code_problems(mem, committed, last: str) -> list[str]:
    """Bellek koşusu (`mem`) ile commit'li `scores_oot.json` (`committed`) arasındaki izin verilmeyen farklar. `last` = dosyayı en son
    yazan commit. İki kod alanı tanım gereği bugünkü koddan değil, dosyanın yazıldığı andan gelir (aynı kalıp):
    - `code.git_head`: dosyayı ekleyen commit olamaz; `last`'in atası ve ondan farklı olmalı (M21).
    - `code.borsai_source_sha256` (Faz 8, SPEC_DEVIATIONS N19; proje sahibi kararı 2026-10-01): bugünkü ağaçla eşit olmak zorunda
      değil; dosyadaki değer `last`'teki borsai/ ağacının hash'ine eşit olmalı.
    Bu ikisi doğrulandıktan sonra bellek koşusunda yalnız bu iki alan dosyadakiyle değiştirilir ve bütün belge karşılaştırılır
    (`code.borsai_dirty` dahil; eşit kalmalı)."""
    import faz7_support as fs7

    probs = []
    head = committed["code"]["git_head"]
    if head == last or f6.git(ROOT, "merge-base", head, last) != head:
        probs.append("git_head")
    if committed["code"]["borsai_source_sha256"] != fs7.borsai_tree_sha256_at(last):
        probs.append("borsai_source_sha256")
    m = json.loads(json.dumps(mem))
    m["code"]["git_head"] = head
    m["code"]["borsai_source_sha256"] = committed["code"]["borsai_source_sha256"]
    return probs + sorted(_diff_paths(m, committed))


def test_real_scores_oot_in_memory_run_equals_committed_file():
    """M-F, FAZ7_VAULT_SCORE T7 ile sıkılaştırıldı (SPEC_DEVIATIONS M21; proje sahibi kararı 2026-09-29): kasa açık (işaret VA1'de
    commit'li; kapalı kip bu depoda artık yok) ve commit'li scores_oot.json kasa skorlarıyla yazılmış (dört kasa anahtarı var).
    Bugünkü kodla bellek koşusu commit'li dosyayla TAM eşit: bütün yollar (açık küme, kasa, toplam, üç post_d1 anahtarı,
    `definitions`, `retro_info`, `code.borsai_dirty`) bayt olarak aynı; izin verilen fark yolu yok (eski `EXPECTED_DRIFT` kalktı).
    Üretim zamanı dosyadakiyle verilir. `code.git_head` tanım gereği dosyayı ekleyen commit olamaz (dosya kendi commit'ini yazamaz):
    o alan için eşitlik yerine daha dar bir bağıntı istenir — dosyayı en son değiştiren commit'in atası (ve ondan farklı),
    dolayısıyla HEAD'in de atası. `code.borsai_source_sha256` aynı kalıpla (Faz 8, SPEC_DEVIATIONS N19; proje sahibi kararı
    2026-10-01): dosyadaki değer dosyayı en son yazan commit'teki borsai/ ağacının hash'ine eşit olmalı (borsai/'ye sonradan giren
    kod bu dosyayı bayatlatmaz). İkisi doğrulandıktan sonra bellek koşusunun yalnız bu iki alanı dosyadakiyle değiştirilip bütün
    belge bayt olarak karşılaştırılır (`scores_oot_code_problems`)."""
    assert REAL_MARKER.open_mode
    committed = json.loads((ROOT / "scores" / "scores_oot.json").read_text(encoding="utf-8"))
    assert VAULT_SCORE_KEYS <= set(committed)
    last = f6.git(ROOT, "log", "-1", "--format=%H", "--", "scores/scores_oot.json")
    seen = sc.spk_corporate_action_members(ROOT / sc.SPK_EXPOSURE_REL, cohort_path=reg.COHORT_PATH)
    now = datetime.fromisoformat(committed["generated_at_utc"].replace("Z", "+00:00"))
    mem = json.loads(pretty_json_bytes(sc.build_oot_scores(root=ROOT, now=now, spk_corporate_action_seen=seen)))
    assert scores_oot_code_problems(mem, committed, last) == []
    mem["code"]["git_head"] = committed["code"]["git_head"]                     # yalnız bu iki alan; bağıntıları yukarıda
    mem["code"]["borsai_source_sha256"] = committed["code"]["borsai_source_sha256"]
    assert pretty_json_bytes(mem) == (ROOT / "scores" / "scores_oot.json").read_bytes()


def test_scores_oot_code_rule_mutations():
    """N19 kuralının mutasyonları (bellekteki kopyalar; bellek koşusu yapılmaz): kod alanları bugünkü koddan farklı olabilir ama
    dosyadaki kaynak hash'i yazıldığı commit'in ağacından sapamaz, `borsai_dirty` ve kod dışındaki her alan eşit kalmalı."""
    committed = json.loads((ROOT / "scores" / "scores_oot.json").read_text(encoding="utf-8"))
    last = f6.git(ROOT, "log", "-1", "--format=%H", "--", "scores/scores_oot.json")
    mem = json.loads(json.dumps(committed))
    mem["code"]["git_head"] = "0" * 40
    mem["code"]["borsai_source_sha256"] = "f" * 64                              # bugünkü ağaç farklı: serbest
    assert scores_oot_code_problems(mem, committed, last) == []
    bad = json.loads(json.dumps(committed))
    bad["code"]["borsai_source_sha256"] = "e" * 64                              # dosya yazıldığı ağaçtan sapıyor
    assert scores_oot_code_problems(mem, bad, last) == ["borsai_source_sha256"]
    dirty = json.loads(json.dumps(mem))
    dirty["code"]["borsai_dirty"] = not committed["code"]["borsai_dirty"]
    assert scores_oot_code_problems(dirty, committed, last) == ["/code/borsai_dirty"]
    other = json.loads(json.dumps(mem))
    other["generated_at_utc"] = "2000-01-01T00:00:00Z"
    assert scores_oot_code_problems(other, committed, last) == ["/generated_at_utc"]
    assert "git_head" in scores_oot_code_problems(mem, committed, committed["code"]["git_head"])     # dosya kendi commit'i olamaz


# ================================================================ M-H: komutlar ve hijyen

def test_vault_post_d1_and_s5_open_no_zip_without_marker(base, tmp_path, cal, capsys):
    root, q = _clone(base, tmp_path)
    for cmd in ("vault-post-d1", "vault-s5"):
        dl = f6.FakeDownloader(base["files"])
        rc, out, heads = _run(cmd, root, q, cal, capsys, downloader=dl)
        assert (rc, out["durum"], out["hata"], dl.calls, heads) == (2, "DUR", "GateError", [], []), cmd
    assert not (root / oo.VAULT_MARKER_REL).exists() and _tracked(root, "registry/oot/post_d1") == [
        p.relative_to(root).as_posix() for p in sorted((root / "registry" / "oot" / "post_d1").rglob("*.json"))]


def _real_sealed() -> list[str]:
    if not reg.COHORT_PATH.exists():
        return []
    return sorted(r["ticker"] for r in reg.cohort_members(reg.read_cohort()[1]) if r["vault"] == reg.VAULT_SEALED)


def test_new_task_files_carry_no_vault_code_or_bulletin_name():
    """Hijyen: bu görevin yeni metinlerinde (rapor, ekler, SPEC_DEVIATIONS M bölümü, testler, işaret dosyası) kasa kodu ve bülten
    adı kalıbı yok. Kod listesi yerel değişkende; hata çıktısı yalnız dosya adı ve sayı taşır."""
    sealed = _real_sealed()
    n_sealed = len(sealed)
    assert n_sealed == 64
    pattern = re.compile(r"\b(" + "|".join(sealed) + r")\b")
    dev = (ROOT / "docs" / "SPEC_DEVIATIONS.md").read_text(encoding="utf-8")
    texts = [("SPEC_DEVIATIONS M", dev.partition("\n## M.")[2]),
             *((p.name, p.read_text(encoding="utf-8")) for p in [ROOT / "tests" / "test_faz7_vault.py",
                                                                ROOT / "docs" / "prompts" / "FAZ7_VAULT_OPEN.md"]),
             *((p.relative_to(ROOT).as_posix(), p.read_text(encoding="utf-8", errors="replace"))
               for p in sorted((ROOT / "docs" / "faz7_vault").rglob("*")) if p.is_file())]
    if (ROOT / oo.VAULT_MARKER_REL).exists():
        texts.append(("işaret", (ROOT / oo.VAULT_MARKER_REL).read_text(encoding="utf-8")))
    for name, text in texts:
        n = len(set(pattern.findall(text)))
        assert n == 0, (name, n)
        assert not re.search(r"th[bm]20\d{6}", text), name


# ================================================================ M14: TARIH biçimi (proje sahibi kararı; C2)

def _zip_tarih(day: str, kind: str, rows, tarih) -> bytes:
    """f6.make_zip gibi; TARIH sütunu verilen metin(ler)le (tek dizge ya da satır başına liste)."""
    import io
    import zipfile

    head = f6.HEAD_THB if kind == "thb" else f6.HEAD_THM
    rows = list(rows)
    dates = tarih if isinstance(tarih, list) else [tarih] * len(rows)
    lines = [head, [h.lower() for h in head]] + [[d] + list(r) for d, r in zip(dates, rows)]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(oc.internal_name(day, kind), ("\n".join(";".join(r) for r in lines) + "\n").encode("cp1254"))
    return buf.getvalue()


def test_tarih_dotted_formats_accepted_iso_path_unchanged_and_other_formats_stop():
    day = "2020-06-04"
    thb = [f6.thb_row("ZZZZ.E", "5.00"), f6.thb_row("SYKA.E", "11.55", "10")]
    thm = [f6.thm_row("ZZZZ.E", "5.00", "5.50", "4.50"), f6.thm_row("SYKA.E", "10.50", "11.55", "9.45")]
    want_b = oo.extract_code_row(_zip_tarih(day, "thb", thb, day), day, "thb", "SYKA.E")
    want_m = oo.extract_code_row(_zip_tarih(day, "thm", thm, day), day, "thm", "SYKA.E")
    assert want_b.close == "11.55" and want_m.upper == "11.55"
    for text in ("4.06.2020", "04.06.2020"):                                     # iki kabul edilen noktalı biçim
        assert oo.extract_code_row(_zip_tarih(day, "thb", thb, text), day, "thb", "SYKA.E") == want_b
        assert oo.extract_code_row(_zip_tarih(day, "thm", thm, text), day, "thm", "SYKA.E") == want_m
        assert oo.bulletin_tarih_style(_zip_tarih(day, "thb", thb, text), day, "thb") == oo.TARIH_DOTTED
    assert oo.bulletin_tarih_style(_zip_tarih(day, "thb", thb, day), day, "thb") == oo.TARIH_ISO
    # ISO yolu değişmedi: başka satırın biçimi denetlenmez (bugünkü davranış), kod satırının günü birebir karşılaştırılır
    odd = [f6.thb_row("ZZZZ.E", "5,00", "1.234")] + thb[1:]
    assert oo.extract_code_row(_zip_tarih(day, "thb", odd, day), day, "thb", "SYKA.E") == want_b
    assert oo.extract_code_row(_zip_tarih(day, "thb", thb, ["2020-06-05", day]), day, "thb", "SYKA.E") == want_b
    for dates in (["2020-06-04", "2020-06-05"], [day, "04/06/2020"], [day, "4.6.2020"]):
        with pytest.raises(oo.OotOutcomeError, match="satır tarihi"):
            oo.extract_code_row(_zip_tarih(day, "thb", thb, dates), day, "thb", "SYKA.E")
    # noktalı bülten: her satır bülten gününe çevrilmeli, sayısal alanlar kanonik; aksi DUR, iletide kod ve değer yok
    stops = {"yanlış gün": (thb, ["5.06.2020", "4.06.2020"], "thb"),
             "karışık biçim": (thb, [day, "4.06.2020"], "thb"),
             "virgüllü kapanış": (odd[:1] + thb[1:], "4.06.2020", "thb"),
             "binlik ayırıcılı sözleşme": ([f6.thb_row("ZZZZ.E", "5.00", "1.234")] + thb[1:], "4.06.2020", "thb"),
             "virgüllü limit": ([f6.thm_row("ZZZZ.E", "5.00", "5,50", "4.50")] + thm[1:], "04.06.2020", "thm")}
    for name, (rows, dates, kind) in stops.items():
        with pytest.raises(oo.OotOutcomeError) as exc:
            oo.extract_code_row(_zip_tarih(day, kind, rows, dates), day, kind, "SYKA.E")
        msg = str(exc.value)
        assert "d.mm.yyyy" in msg and "DUR" in msg and "SYKA" not in msg and "ZZZZ" not in msg and "5,50" not in msg, name
    assert oo.dotted_day("4.06.2020") == oo.dotted_day("04.06.2020") == day
    assert oo.dotted_day("4.6.2020") is oo.dotted_day("31.02.2020") is oo.dotted_day("2020-06-04") is None

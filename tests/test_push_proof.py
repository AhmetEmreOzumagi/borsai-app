"""Push kanıtı (borsai/push_proof.py): dosya biçimi, yeniden yazmama, kimlik yoksa atlama,
torun commit kapsaması. Ağa çıkılmaz: GitHub yanıtı enjekte edilir."""
from __future__ import annotations

import json
import subprocess

import pytest

from borsai import push_proof as pp
from borsai.provenance import ROOT

FAZ1A = "5fa849d27c330786db928edab18888c1f888dfb5"
FAZ1B = "b09cab5"
CONFORMITY = "1869da6"
SLUG = "AhmetEmreOzumagi/borsai"
LEGACY_NETGL = ROOT / "registry" / "legacy_frozen" / "NETGL_20260916_V1_5" / "push_proof.json"


def fake_poster(created_at: str, calls: list | None = None):
    def post(slug, sha, context, description):
        if calls is not None:
            calls.append(sha)
        return {"url": f"https://api.github.com/repos/{slug}/statuses/{sha}", "id": 1, "state": "success",
                "context": context, "description": description, "created_at": created_at, "updated_at": created_at}
    return post


@pytest.mark.requires_git_history
def test_resolve_short_sha_and_slug(tmp_path):
    assert pp.resolve_sha("5fa849d") == FAZ1A
    with pytest.raises(pp.PushProofError):
        pp.resolve_sha("0000000")
    run = lambda *a: subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)  # noqa: E731
    run("init", "-q")
    for url in ("https://github.com/AhmetEmreOzumagi/borsai.git", "git@github.com:AhmetEmreOzumagi/borsai.git"):
        run("remote", "remove", "origin") if url.startswith("git@") else None
        run("remote", "add", "origin", url)
        assert pp.repo_slug(tmp_path) == SLUG
    run("remote", "set-url", "origin", "/yerel/yol")
    with pytest.raises(pp.PushProofError):
        pp.repo_slug(tmp_path)


@pytest.mark.requires_git_history
def test_proof_file_format_and_determinism(tmp_path):
    a = pp.emit(FAZ1A, out_dir=tmp_path / "a", slug=SLUG, poster=fake_poster("2026-09-22T12:00:00Z"), auth="test")
    b = pp.emit(FAZ1A, out_dir=tmp_path / "b", slug=SLUG, poster=fake_poster("2026-09-22T12:00:00Z"), auth="test")
    pa, pb = tmp_path / "a" / f"{FAZ1A}.json", tmp_path / "b" / f"{FAZ1A}.json"
    assert a["status"] == "CREATED" and a["created_at"] == "2026-09-22T12:00:00Z"
    assert pa.read_bytes() == pb.read_bytes()  # yerel saat yok: aynı yanıt aynı bayt
    doc = json.loads(pa.read_text(encoding="utf-8"))
    pp.validate_proof(doc, FAZ1A)
    assert doc["schema_version"] == pp.PROOF_SCHEMA and doc["method"] == "GITHUB_COMMIT_STATUS_CREATED_AT"
    assert doc["github_response"]["created_at"] == doc["created_at"]
    assert not any(k in json.dumps(doc) for k in ("GH_TOKEN", "Bearer"))


@pytest.mark.requires_git_history
def test_existing_proof_is_never_rewritten_and_no_request(tmp_path):
    calls: list = []
    pp.emit(FAZ1A, out_dir=tmp_path, slug=SLUG, poster=fake_poster("2026-09-22T12:00:00Z", calls), auth="test")
    before = (tmp_path / f"{FAZ1A}.json").read_bytes()
    again = pp.emit(FAZ1A, out_dir=tmp_path, slug=SLUG, poster=fake_poster("2026-09-23T12:00:00Z", calls), auth="test")
    assert again["status"] == "EXISTING" and again["created_at"] == "2026-09-22T12:00:00Z"
    assert calls == [FAZ1A]  # ikinci çağrı ağa çıkmadı
    assert (tmp_path / f"{FAZ1A}.json").read_bytes() == before


def test_invalid_responses_refused_and_nothing_written(tmp_path):
    def wrong_sha(slug, sha, context, description):
        return {"url": f"https://api.github.com/repos/{slug}/statuses/{'0' * 40}", "created_at": "2026-09-22T12:00:00Z"}

    for poster in (fake_poster("2026-09-22 12:00"), wrong_sha):
        with pytest.raises(pp.PushProofError):
            pp.emit(FAZ1A, out_dir=tmp_path, slug=SLUG, poster=poster, auth="test")
    assert list(tmp_path.glob("*.json")) == []


@pytest.mark.requires_git_history
def test_missing_auth_skips_without_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(pp, "auth_method", lambda: None)
    with pytest.raises(pp.MissingAuthError):
        pp.emit(FAZ1A, out_dir=tmp_path, slug=SLUG)
    assert list(tmp_path.glob("*")) == []
    original = pp.emit
    monkeypatch.setattr(pp, "emit", lambda ref: original(ref, out_dir=tmp_path, slug=SLUG))
    assert pp.main([FAZ1A]) == 2  # CLI: SKIPPED_NO_AUTH, çıkış kodu 2
    assert list(tmp_path.glob("*")) == []


@pytest.mark.requires_git_history
def test_earliest_proof_covers_ancestors(tmp_path):
    full_b = pp.resolve_sha(FAZ1B)
    full_c = pp.resolve_sha(CONFORMITY)
    pp.emit(full_c, out_dir=tmp_path, slug=SLUG, poster=fake_poster("2026-09-22T10:00:00Z"), auth="test")
    pp.emit(full_b, out_dir=tmp_path, slug=SLUG, poster=fake_poster("2026-09-22T11:00:00Z"), auth="test")
    proofs = pp.load_proofs(tmp_path)
    # FAZ1A her iki commit'in de atası: en erken kanıt (torun 1869da6'nın) geçerli
    assert pp.earliest_proof(FAZ1A, proofs)["proven_commit_sha"] == full_c
    # 1869da6, b09cab5'in atası değil: yalnız kendi kanıtı
    assert pp.earliest_proof(full_c, proofs)["created_at"] == "2026-09-22T10:00:00Z"
    assert pp.is_ancestor(FAZ1A, full_c) and not pp.is_ancestor(full_c, full_b)


def test_committed_proofs_are_valid():
    d = ROOT / "registry" / "push_proofs"
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        pp.validate_proof(json.loads(p.read_text(encoding="utf-8")), p.stem)


def test_same_method_as_legacy_netgl_proof():
    legacy = json.loads(LEGACY_NETGL.read_text(encoding="utf-8"))
    doc = pp.proof_document("5f70acedcd1e31cc9045ad073a0b317a5691b44e", "AhmetEmreOzumagi/borsai-halka-arz-modeli", legacy, "legacy")
    pp.validate_proof(doc)
    assert doc["created_at"] == "2026-09-16T11:32:27Z"

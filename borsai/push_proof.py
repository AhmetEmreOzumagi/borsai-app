"""Push kanıtı: bir commit'in uzak depoda bulunduğunun sunucu zaman damgalı kanıtı (SPEC_SCORING §5).

Yöntem (eski repo `scripts/modeling/emit_true_live_push_proof.py`, NETGL'de kullanıldı):
GitHub commit status API'sine `POST /repos/{owner}/{repo}/statuses/{sha}` yazılır. GitHub
bilmediği bir sha için 404 döndürür; 201 yanıtı, commit'in o anda origin'de bulunduğunun
kanıtıdır. Zaman = yanıttaki `created_at` (sunucu değeri). Yerel saat hiçbir yere yazılmaz.

Kimlik doğrulama: önce `gh api` (gh CLI oturumu), yoksa `GH_TOKEN` ortam değişkeni
(repo:status yazma yetkisi). Token argüman olarak alınmaz, basılmaz, dosyaya yazılmaz.
İkisi de yoksa `MissingAuthError`: kanıt üretilmez, dosya yazılmaz.

Çıktı: `registry/push_proofs/<sha>.json` (biçim: PROOF_SCHEMA; `github_response` alanı API
yanıtının kendisidir). Dosya varsa yeniden istek atılmaz: en erken kanıt geçerlidir, sonraki
bir status onu değiştirmez (dosya yeniden yazılmaz).

Bir commit için geçerli zaman: kendisinin ya da onu içeren (torun) bir commit'in en erken
kanıtı (`earliest_proof`; torunluk `git merge-base --is-ancestor`).

Kullanım (proje sahibi, `git push`'tan SONRA):
    .venv/bin/python -m borsai.push_proof 5fa849d b09cab5 1869da6
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from .provenance import ROOT, pretty_json_bytes

PROOFS_DIR = ROOT / "registry" / "push_proofs"
PROOF_SCHEMA = "borsai.push_proof/1"
DEFAULT_CONTEXT = "borsai/push-proof"
DEFAULT_DESCRIPTION = "commit confirmed present on origin (BorsAi push proof, SPEC_SCORING §5)"
GITHUB_API_VERSION = "2022-11-28"
USER_AGENT = "borsai-push-proof/1"
METHOD = "GITHUB_COMMIT_STATUS_CREATED_AT"

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_CREATED_AT = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

Poster = Callable[[str, str, str, str], dict[str, Any]]


class PushProofError(RuntimeError):
    """Kanıt üretilemedi; hiçbir dosya yazılmadı."""


class MissingAuthError(PushProofError):
    pass


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo_root), *args], check=True, capture_output=True, text=True).stdout.strip()


def resolve_sha(ref: str, repo_root: Path = ROOT) -> str:
    """Kısa ya da tam sha -> tam 40 haneli commit sha'sı (yerel depoda bilinmeli)."""
    try:
        sha = _git(repo_root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    except subprocess.CalledProcessError as exc:
        raise PushProofError(f"yerel depoda commit değil: {ref!r}") from exc
    if not _FULL_SHA.match(sha):
        raise PushProofError(f"beklenmeyen sha: {sha!r}")
    return sha


def repo_slug(repo_root: Path = ROOT) -> str:
    remote = _git(repo_root, "remote", "get-url", "origin")
    m = re.search(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?$", remote)
    if not m:
        raise PushProofError(f"origin GitHub adresi değil: {remote!r}")
    return f"{m.group(1)}/{m.group(2)}"


def is_ancestor(ancestor: str, descendant: str, repo_root: Path = ROOT) -> bool:
    """`git merge-base --is-ancestor` (bir commit kendisinin atasıdır)."""
    r = subprocess.run(["git", "-C", str(repo_root), "merge-base", "--is-ancestor", ancestor, descendant],
                       capture_output=True)
    if r.returncode not in (0, 1):
        raise PushProofError(f"merge-base başarısız: {ancestor} {descendant}")
    return r.returncode == 0


def _gh_available() -> bool:
    if shutil.which("gh") is None:
        return False
    return subprocess.run(["gh", "auth", "status"], capture_output=True).returncode == 0


def auth_method() -> Optional[str]:
    """'gh' | 'GH_TOKEN' | None."""
    if _gh_available():
        return "gh"
    if os.environ.get("GH_TOKEN"):
        return "GH_TOKEN"
    return None


def _post_with_gh(slug: str, sha: str, context: str, description: str) -> dict[str, Any]:
    r = subprocess.run(
        ["gh", "api", "--method", "POST", f"repos/{slug}/statuses/{sha}",
         "-H", f"X-GitHub-Api-Version: {GITHUB_API_VERSION}",
         "-f", "state=success", "-f", f"context={context}", "-f", f"description={description}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise PushProofError(f"gh api başarısız (sha={sha}): {r.stderr.strip()[:500]}")
    return json.loads(r.stdout)


def _post_with_token(slug: str, sha: str, context: str, description: str) -> dict[str, Any]:
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise MissingAuthError("GH_TOKEN yok")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{slug}/statuses/{sha}",
        data=json.dumps({"state": "success", "context": context, "description": description}).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": GITHUB_API_VERSION, "User-Agent": USER_AGENT,
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        raise PushProofError(f"GitHub HTTP {exc.code} (sha={sha}); commit origin'de değilse 404 beklenir") from exc
    except urllib.error.URLError as exc:
        raise PushProofError(f"ağ hatası: {exc.reason}") from exc
    if status != 201:
        raise PushProofError(f"beklenmeyen HTTP {status}")
    return json.loads(raw)


def default_poster() -> tuple[str, Poster]:
    method = auth_method()
    if method == "gh":
        return method, _post_with_gh
    if method == "GH_TOKEN":
        return method, _post_with_token
    raise MissingAuthError(
        "Kimlik doğrulama yok: `gh auth status` başarısız ve GH_TOKEN tanımlı değil. Kanıt üretilmedi."
    )


def proof_document(sha: str, slug: str, response: dict[str, Any], auth: str) -> dict[str, Any]:
    """Kanıt dosyasının içeriği. Yerel saat içermez: aynı yanıt aynı baytları verir."""
    created_at = response.get("created_at")
    if not isinstance(created_at, str) or not _CREATED_AT.match(created_at):
        raise PushProofError(f"yanıtta geçerli created_at yok: {created_at!r}")
    url = str(response.get("url", ""))
    if not url.endswith(f"/repos/{slug}/statuses/{sha}"):
        raise PushProofError(f"yanıt başka bir commit/depo için: {url!r}")
    return {
        "schema_version": PROOF_SCHEMA,
        "proven_commit_sha": sha,
        "repo_slug": slug,
        "method": METHOD,
        "auth": auth,
        "created_at": created_at,
        "github_status_id": response.get("id"),
        "context": response.get("context"),
        "github_response": response,
        "note": ("created_at GitHub sunucusunun değeridir; commit origin'de yoksa status POST'u 404 döner. "
                 "Kanıt, bu commit'i ve onun bütün atalarını kapsar."),
    }


def validate_proof(doc: dict[str, Any], sha: Optional[str] = None) -> None:
    """Kanıt dosyası biçim denetimi (testler ve Faz 2B sınıflaması kullanır)."""
    required = {"schema_version", "proven_commit_sha", "repo_slug", "method", "created_at", "github_response"}
    missing = required - set(doc)
    if missing:
        raise PushProofError(f"eksik alanlar: {sorted(missing)}")
    if doc["schema_version"] != PROOF_SCHEMA or doc["method"] != METHOD:
        raise PushProofError("şema/yöntem tanınmıyor")
    if not _FULL_SHA.match(doc["proven_commit_sha"]) or (sha and doc["proven_commit_sha"] != sha):
        raise PushProofError("proven_commit_sha geçersiz")
    if not _CREATED_AT.match(doc["created_at"]) or doc["github_response"].get("created_at") != doc["created_at"]:
        raise PushProofError("created_at geçersiz ya da yanıtla uyuşmuyor")
    if not str(doc["github_response"].get("url", "")).endswith(f"/statuses/{doc['proven_commit_sha']}"):
        raise PushProofError("yanıt URL'si commit'le uyuşmuyor")


def emit(ref: str, *, repo_root: Path = ROOT, out_dir: Path = PROOFS_DIR, slug: Optional[str] = None,
         poster: Optional[Poster] = None, auth: Optional[str] = None, context: str = DEFAULT_CONTEXT,
         description: str = DEFAULT_DESCRIPTION) -> dict[str, Any]:
    """Bir commit için kanıt üretir ya da var olanı döndürür (dosya varsa ağa çıkılmaz)."""
    sha = resolve_sha(ref, repo_root)
    path = out_dir / f"{sha}.json"
    if path.exists():
        doc = json.loads(path.read_text(encoding="utf-8"))
        validate_proof(doc, sha)
        return {"sha": sha, "path": str(path), "status": "EXISTING", "created_at": doc["created_at"]}
    if poster is None:
        auth, poster = default_poster()
    slug = slug or repo_slug(repo_root)
    doc = proof_document(sha, slug, poster(slug, sha, context, description), auth or "injected")
    validate_proof(doc, sha)
    out_dir.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:  # yeniden yazma yok
        fh.write(pretty_json_bytes(doc))
    return {"sha": sha, "path": str(path), "status": "CREATED", "created_at": doc["created_at"]}


def load_proofs(out_dir: Path = PROOFS_DIR) -> list[dict[str, Any]]:
    docs = []
    for p in sorted(out_dir.glob("*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        validate_proof(doc, p.stem)
        docs.append(doc)
    return docs


def earliest_proof(commit: str, proofs: Sequence[dict[str, Any]], repo_root: Path = ROOT) -> Optional[dict[str, Any]]:
    """`commit`'i kapsayan (kendisi ya da torunu için üretilmiş) en erken kanıt; yoksa None."""
    sha = resolve_sha(commit, repo_root)
    covering = [d for d in proofs if is_ancestor(sha, d["proven_commit_sha"], repo_root)]
    return min(covering, key=lambda d: d["created_at"]) if covering else None


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Commit'ler için GitHub commit status push kanıtı üretir (git push'tan sonra).")
    parser.add_argument("commits", nargs="+", help="kısa ya da tam commit sha'ları")
    args = parser.parse_args(argv)
    try:
        results = [emit(c) for c in args.commits]
    except MissingAuthError as exc:
        print(json.dumps({"status": "SKIPPED_NO_AUTH", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

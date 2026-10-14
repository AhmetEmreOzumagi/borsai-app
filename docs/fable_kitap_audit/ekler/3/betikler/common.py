"""Ortak yardımcılar — borsai import ETMEZ. Yalnız stdlib."""
from __future__ import annotations
import csv, hashlib, io, json, subprocess, zipfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING, localcontext, Context, ROUND_HALF_EVEN
from pathlib import Path
from functools import lru_cache

ROOT = Path("/Users/ahmet/Desktop/BorsAi")
IST = timezone(timedelta(hours=3))

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_file(p) -> str:
    return sha256_bytes(Path(p).read_bytes())

def identity_hash(items) -> str:
    return sha256_bytes(("\n".join(items) + "\n").encode("utf-8"))

def canonical_sha256(value) -> str:
    return sha256_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))

def read_csv(p):
    with Path(p).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))

def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def git(*args, root=ROOT) -> str:
    env = {"GIT_OPTIONAL_LOCKS": "0"}
    import os
    e = dict(os.environ); e.update(env)
    r = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True, env=e)
    return r.stdout.strip()

@lru_cache(maxsize=None)
def added_commit(rel: str, root=ROOT):
    out = git("log", "--diff-filter=A", "--format=%H", "--", rel, root=root).splitlines()
    return out[-1] if out else None

@lru_cache(maxsize=None)
def is_ancestor(a: str, b: str, root=ROOT) -> bool:
    import os
    e = dict(os.environ); e["GIT_OPTIONAL_LOCKS"] = "0"
    r = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", a, b], capture_output=True, env=e)
    if r.returncode not in (0, 1):
        raise RuntimeError(f"merge-base failed {a} {b}")
    return r.returncode == 0

def head(root=ROOT) -> str:
    return git("rev-parse", "HEAD", root=root)

def earliest(commits):
    best = None
    for c in commits:
        if c is None:
            continue
        if best is None or (c != best and is_ancestor(c, best)):
            best = c
    return best

def load_proofs(root=ROOT):
    docs = []
    for p in sorted((root / "registry" / "push_proofs").glob("*.json")):
        d = load_json(p)
        assert d["proven_commit_sha"] == p.stem
        assert d["github_response"]["created_at"] == d["created_at"]
        assert str(d["github_response"]["url"]).endswith("/statuses/" + d["proven_commit_sha"])
        docs.append(d)
    return docs

def proof_time(commit, proofs, root=ROOT):
    if commit is None:
        return None
    cov = [d["created_at"] for d in proofs if is_ancestor(commit, d["proven_commit_sha"], root)]
    return min(cov) if cov else None

def istanbul_date(ts: str) -> str:
    t = ts.replace("Z", "+00:00")
    return datetime.fromisoformat(t).astimezone(IST).date().isoformat()

def parse_instant(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

# ---------------- bülten zip okuma (stdlib) ----------------
def bulletin_path(day: str, kind: str, root=ROOT) -> Path:
    return root / "data" / "raw" / "bist" / kind / day[:4] / f"{kind}{day.replace('-', '')}1.zip"

def read_bulletin(day: str, kind: str, root=ROOT):
    """-> (sha256, headers, {code: row-dict}) ; cp1254, ';' ayracı, ilk iki satır başlık."""
    p = bulletin_path(day, kind, root)
    data = p.read_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        assert len(names) == 1, names
        text = z.read(names[0]).decode("cp1254")
    rows = [r for r in csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=";") if any(c != "" for c in r)]
    headers = rows[0]
    out = {}
    dup = set()
    for r in rows[2:]:
        assert len(r) == len(headers)
        d = dict(zip(headers, r))
        code = d["ISLEM  KODU"]
        if code in out or code in dup:
            out.pop(code, None); dup.add(code)
        else:
            out[code] = d
    return sha256_bytes(data), headers, out

# ---------------- fiyat adımı ve alt limit ----------------
TICK_TABLE = [(Decimal("20"), Decimal("0.01")), (Decimal("50"), Decimal("0.02")), (Decimal("100"), Decimal("0.05")),
              (Decimal("250"), Decimal("0.10")), (Decimal("500"), Decimal("0.25")), (Decimal("1000"), Decimal("0.50")),
              (Decimal("2500"), Decimal("1.00")), (None, Decimal("2.50"))]

def tick(x: Decimal) -> Decimal:
    for below, t in TICK_TABLE:
        if below is None or x < below:
            return t
    raise AssertionError

def lower_limit(x: Decimal) -> Decimal:
    with localcontext(Context(prec=60)):
        y = x * Decimal("0.9")
        t = tick(y)
        n = (y / t).to_integral_value(rounding=ROUND_CEILING)
        return (n * t).quantize(t)

CTX60 = Context(prec=60, rounding=ROUND_HALF_EVEN)

def sigmoid(x: float) -> float:
    import math
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)

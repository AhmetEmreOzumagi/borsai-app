"""Hash, kanonik JSON, git ve zaman damgası yardımcıları. Yalnız stdlib."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = ROOT / "borsai"

# Türkiye 2016'dan beri sabit UTC+3 (yaz saati yok).
ISTANBUL = timezone(timedelta(hours=3), name="+03:00")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def canonical_json(value: Any) -> str:
    """Sıralı anahtar, boşluksuz, UTF-8. Hash girdisi olarak kullanılır."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def pretty_json_bytes(value: Any) -> bytes:
    """Dosyaya yazılan JSON: sıralı anahtar, 2 boşluk girinti, sonda LF.
    float'lar Python repr'i ile yazılır (binary64'ün en kısa gidiş-dönüş biçimi)."""
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def identity_hash(items: Iterable[str]) -> str:
    """Legacy `_identity_hash`: sha256("\\n".join(items) + "\\n"). Fold ledger'ındaki
    training_tickers_sha256 ve training_targets_sha256 bu biçimdedir."""
    return sha256_bytes(("\n".join(items) + "\n").encode("utf-8"))


def now_istanbul() -> str:
    return datetime.now(ISTANBUL).isoformat(timespec="seconds")


def git_state(root: Path = ROOT) -> dict[str, Any]:
    """Salt-okur git sorgusu: HEAD commit'i ve çalışma kopyası kirli mi."""
    def run(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

    try:
        commit = run("rev-parse", "HEAD")
        dirty = bool(run("status", "--porcelain", "--untracked-files=no", "--", "borsai"))
        untracked = bool(run("status", "--porcelain", "--untracked-files=all", "--", "borsai"))
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "borsai_dirty": None}
    return {"commit": commit, "borsai_dirty": dirty or untracked}


def source_tree_sha256(package_dir: Path = PACKAGE_DIR) -> dict[str, Any]:
    """borsai/*.py dosyalarının içerik hash'i. Model JSON'u kodla aynı commit'e
    girdiğinden commit hash'i JSON'a yazılamaz; bu hash kodu içerikten bağlar."""
    files = sorted(p for p in package_dir.glob("*.py"))
    lines = [f"{p.name}\t{sha256_file(p)}" for p in files]
    return {
        "files": {p.name: sha256_file(p) for p in files},
        "tree_sha256": sha256_bytes(("\n".join(lines) + "\n").encode("utf-8")),
    }


def code_version() -> dict[str, Any]:
    state = git_state()
    return {
        "git_commit": state["commit"],
        "borsai_dirty": state["borsai_dirty"],
        "borsai_source_sha256": source_tree_sha256()["tree_sha256"],
    }


def runtime_versions() -> dict[str, str]:
    """Yalnız fit/backtest tarafında çağrılır (numpy/sklearn import eder)."""
    import sys

    import joblib
    import numpy
    import scipy
    import sklearn
    import threadpoolctl

    return {
        "python": ".".join(str(p) for p in sys.version_info[:3]),
        "scikit-learn": sklearn.__version__,
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "joblib": joblib.__version__,
        "threadpoolctl": threadpoolctl.__version__,
    }

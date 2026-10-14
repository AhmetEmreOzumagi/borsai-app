#!/usr/bin/env python3
"""Herkese açık ayna ağacını özel repodan üretir (FAZ9_PUBLIC_MIRROR K-MIR-1). Yalnız standart kütüphane.

Kullanım (özel repo kökünden):
    python scripts/mirror/build_mirror.py                  # ~/Desktop/BorsAi_public/ ; HEAD, temiz ağaç şart
    python scripts/mirror/build_mirror.py --out <dizin>    # başka bir çıktı dizini
    python scripts/mirror/build_mirror.py --dry-run        # yalnız sınıflama, denetim ve özet; hiçbir şey yazmaz
    python scripts/mirror/build_mirror.py --allow-dirty    # geliştirme provası: çalışma ağacı (izlenen + izlenmeyen)
                                                           # (README'deki kaynak "<sha>+kirli" yazar; yayımlanmaz)

Ne yapar:
1. HEAD'de izlenen her dosyayı `MIRROR_MANIFEST.txt` kurallarıyla sınıflar: GİRMEZ kalıbına uyan aynaya girmez (GİRMEZ önceliklidir);
   kalan her dosya bir GİRER kalıbına uymalıdır. Hiçbir kurala uymayan dosya ya da hiçbir dosyaya uymayan kural varsa durur
   (KARAR kalmaz; yeni bir dosya türü açık karar ister).
2. Çıktı dizinini boşaltır (`.git` hariç: proje sahibinin ayna klonunda yeniden üretim için) ve dosyaları HEAD'deki blob'lardan
   (`git cat-file --batch`) bayt bayt yazar; her blob'un sha'sı yeniden hesaplanıp denetlenir. Hiçbir dosyanın içeriği
   düzenlenmez. Aynaya giren bir dosya ya da `scripts/mirror/` HEAD'den farklıysa (kirli ağaç) durur.
3. `scripts/mirror/overlay/**`'ı aynı göreli yollarla üstüne yazar (README, CHANGELOG, CONTRIBUTING, iş akışı, ...). Overlay metinlerinde yalnız
   `@@KAYNAK_SHA@@` ve `@@KAYNAK_SHA7@@` yer tutucuları kaynak commit'le doldurulur. `LICENSE`, `NOTICE`, `DATA_NOTICE.md`
   overlay'de ve özel repo kökünde bayt-eşit olmalıdır.
4. Çıktı ağacını yeniden tarar ve özet basar: dosya sayısı, MB, GİRMEZ kalıbına uyan dosya (0 olmalı), `.pdf`/`.zip` (0),
   100 MB üstü (0), sembolik bağ (0), ikili dosya listesi (TÜİK `.xls` ve `docs`/`app/docs` görselleri hariç), overlay
   hijyeni (kasa kodu 0, bülten adı kalıbı 0). Denetimlerden biri tutmazsa çıkış kodu 1.

Ekrana basılan yollarda kasa (SEALED) kodları `<KASA>`, bülten adlarındaki tarih `YYYYMMDD` ile maskelidir.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MANIFEST = HERE / "MIRROR_MANIFEST.txt"
OVERLAY_REL = "scripts/mirror/overlay"
DEFAULT_OUT = Path.home() / "Desktop" / "BorsAi_public"
COHORT = ROOT / "registry" / "oot" / "cohort_pre_h99.csv"

SAME_AS_ROOT = ("LICENSE", "NOTICE", "DATA_NOTICE.md")     # overlay ile özel repo kökü bayt-eşit
PLACEHOLDER = re.compile(r"@@[A-Z0-9_]+@@")
BULLETIN = re.compile(r"th[bm]\d{8}")
MB = 1_000_000
LIMIT_HARD = 100 * MB                                      # GitHub dosya sınırı
LIMIT_WARN = 50 * MB                                       # GitHub uyarı sınırı
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".icns", ".webp", ".pdf", ".zip", ".gz", ".tar", ".7z", ".xlsx",
              ".xls", ".docx", ".pptx", ".pkl", ".joblib", ".npy", ".npz", ".parquet", ".sqlite", ".db", ".woff", ".woff2",
              ".ttf", ".otf", ".whl"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


BLOB_SIZE: dict[str, int] = {}                             # HEAD'deki blob baytları (ls-tree -l)


class MirrorError(Exception):
    pass


# ---------------------------------------------------------------- yardımcılar

def git(*args: str) -> str:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    res = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, env=env)
    if res.returncode != 0:
        raise MirrorError(f"git {' '.join(args)}: {res.stderr.decode('utf-8', 'replace').strip()}")
    return res.stdout.decode("utf-8")


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def glob_regex(pattern: str) -> re.Pattern:
    """`/` ayraçlı göreli yol kalıbı: `**` sıfır ya da daha çok dizin, `*` ve `?` tek yol parçası içinde, `[...]` karakter sınıfı."""
    out, i, n = [], 0, len(pattern)
    while i < n:
        c = pattern[i]
        if pattern.startswith("**/", i):
            out.append(r"(?:[^/]+/)*")
            i += 3
        elif pattern.startswith("**", i):
            out.append(r".*")
            i += 2
        elif c == "*":
            out.append(r"[^/]*")
            i += 1
        elif c == "?":
            out.append(r"[^/]")
            i += 1
        elif c == "[":
            j = pattern.index("]", i + 1)
            out.append("[" + pattern[i + 1:j].replace("!", "^", 1) + "]")
            i = j + 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("".join(out) + r"\Z")


def sealed_codes() -> set[str]:
    with COHORT.open(encoding="utf-8-sig", newline="") as fh:
        return {r["ticker"] for r in csv.DictReader(fh) if r.get("vault") == "SEALED"}


class Masker:
    def __init__(self, codes: set[str]):
        alt = "|".join(re.escape(c) for c in sorted(codes, key=lambda s: (-len(s), s)))
        self.code = re.compile(r"(?<![A-Z0-9])(?:" + alt + r")(?![A-Z0-9])") if codes else None

    def count(self, text: str) -> int:
        return len(self.code.findall(text)) if self.code else 0

    def __call__(self, path: str) -> str:
        p = self.code.sub("<KASA>", path) if self.code else path
        return re.sub(r"(th[bm])\d{8}", r"\1YYYYMMDD", p)


# ---------------------------------------------------------------- manifest ve sınıflama

def read_manifest(path: Path) -> list[dict]:
    rules = []
    for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 3 or parts[0] not in ("GİRER", "GİRMEZ") or not parts[1] or not parts[2].strip():
            raise MirrorError(f"{path.name}:{no}: biçim DURUM<TAB>KALIP<TAB>GEREKÇE olmalı (DURUM GİRER ya da GİRMEZ)")
        rules.append({"line": no, "status": parts[0], "pattern": parts[1], "reason": parts[2].strip(),
                      "rx": glob_regex(parts[1]), "files": 0, "bytes": 0})
    return rules


def classify(path: str, rules: list[dict]) -> tuple[str | None, dict | None]:
    for status in ("GİRMEZ", "GİRER"):
        for r in rules:
            if r["status"] == status and r["rx"].match(path):
                return status, r
    return None, None


def head_tree() -> list[tuple[str, str, str]]:
    """HEAD'de izlenen dosyalar: (mod, blob sha, yol). Yalnız düz dosya (100644/100755) kabul edilir."""
    out = []
    for entry in git("ls-tree", "-r", "-z", "-l", "--full-tree", "HEAD").split("\0"):
        if not entry:
            continue
        meta, path = entry.split("\t", 1)
        mode, kind, sha, size = meta.split()
        if kind != "blob" or mode not in ("100644", "100755"):
            raise MirrorError(f"desteklenmeyen girdi (mod {mode}, tür {kind}): {path}")
        BLOB_SIZE[path] = int(size)
        out.append((mode, sha, path))
    return out


class BlobReader:
    """`git cat-file --batch`: commit'teki baytlar (çalışma kopyası satır sonu dönüşümünden bağımsız)."""

    def __init__(self) -> None:
        env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
        self.proc = subprocess.Popen(["git", "-C", str(ROOT), "cat-file", "--batch"], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, env=env)

    def read(self, sha: str) -> bytes:
        self.proc.stdin.write(sha.encode("ascii") + b"\n")
        self.proc.stdin.flush()
        header = self.proc.stdout.readline().split()
        if len(header) != 3 or header[0].decode("ascii") != sha or header[1] != b"blob":
            raise MirrorError(f"git cat-file: beklenmeyen yanıt {header!r}")
        data = self.proc.stdout.read(int(header[2]))
        self.proc.stdout.read(1)
        return data

    def close(self) -> None:
        self.proc.stdin.close()
        self.proc.wait()


def worktree_files(tree: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    """Yalnız --allow-dirty: HEAD'deki dosyalar (silinenler hariç) + izlenmeyen, yok sayılmayan dosyalar (blob sha'sı boş: kirli)."""
    out = [t for t in tree if (ROOT / t[2]).is_file()]
    for path in git("ls-files", "-z", "--others", "--exclude-standard").split("\0"):
        if path and (ROOT / path).is_file() and not (ROOT / path).is_symlink():
            out.append(("100755" if os.access(ROOT / path, os.X_OK) else "100644", "", path))
    return sorted(out, key=lambda t: t[2])


# ---------------------------------------------------------------- çıktı dizini

def check_out_dir(out: Path) -> None:
    root = ROOT.resolve()
    o = out.resolve()
    if o == root or root in o.parents or o in root.parents or o == Path.home().resolve() or o == Path(o.anchor):
        raise MirrorError(f"çıktı dizini repo içinde, repo'nun atası ya da ev dizini olamaz: {o}")
    if not o.exists():
        return
    entries = [e.name for e in o.iterdir() if e.name != ".git"]
    if entries and not (o / "scripts" / "mirror" / "MIRROR_MANIFEST.txt").is_file():
        raise MirrorError(f"çıktı dizini boş değil ve önceki bir ayna değil (scripts/mirror/MIRROR_MANIFEST.txt yok): {o}")


def _force_remove(func, path, _exc):
    os.chmod(path, 0o700)
    func(path)


def empty_out_dir(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for e in out.iterdir():
        if e.name == ".git":
            continue
        if e.is_dir() and not e.is_symlink():
            hook = {"onexc": _force_remove} if sys.version_info >= (3, 12) else {"onerror": _force_remove}
            shutil.rmtree(e, **hook)
        else:
            e.unlink()


# ---------------------------------------------------------------- ana akış

def build(out: Path, *, dry_run: bool, allow_dirty: bool) -> dict:
    head = git("rev-parse", "HEAD").strip()
    toplevel = Path(git("rev-parse", "--show-toplevel").strip()).resolve()
    if toplevel != ROOT.resolve():
        raise MirrorError(f"betik repo kökünde değil: {toplevel} ≠ {ROOT}")
    mask = Masker(sealed_codes())
    rules = read_manifest(MANIFEST)
    tree = head_tree()
    if allow_dirty:
        tree = worktree_files(tree)

    included, excluded, unclassified = [], [], []
    for mode, sha, path in tree:
        status, rule = classify(path, rules)
        size = BLOB_SIZE[path] if sha else (ROOT / path).stat().st_size
        if rule is None:
            unclassified.append(path)
            continue
        rule["files"] += 1
        rule["bytes"] += size
        (included if status == "GİRER" else excluded).append((mode, sha, path))
    problems = [f"sınıflanmamış dosya: {mask(p)}" for p in unclassified]
    problems += [f"kural hiçbir dosyaya uymuyor: satır {r['line']} {r['status']} {r['pattern']}" for r in rules if r["files"] == 0]
    if problems:
        raise MirrorError("manifest eksik ya da bayat:\n  " + "\n  ".join(problems))

    # içerik: temiz kipte HEAD blob'ları (bayt bayt commit); kirli kipte HEAD'den gerçekten farklı (içerik olarak; satır sonu
    # normalleştirmesi sayılmaz) ya da izlenmeyen dosyalar çalışma ağacından
    changed = set(p for p in git("diff", "--name-only", "-z", "HEAD").split("\0") if p)
    changed |= set(p for p in git("ls-files", "-z", "--others", "--exclude-standard").split("\0") if p)
    dirty = sorted(p for p in changed if p.startswith("scripts/mirror/") or any(p == q for _, _, q in included))
    if dirty and not allow_dirty:
        raise MirrorError("ağaç kirli (HEAD'den farklı ya da izlenmeyen):\n  " + "\n  ".join(mask(p) for p in dirty))
    source = head if not dirty else head + "+kirli"
    source7 = head[:7] if not dirty else head[:7] + "+kirli"

    reader = BlobReader()
    try:
        def content(sha: str, path: str) -> bytes:
            if allow_dirty and (not sha or path in changed):
                return (ROOT / path).read_bytes()
            data = reader.read(sha)
            if blob_sha(data) != sha:
                raise MirrorError(f"blob sha tutmuyor: {mask(path)}")
            return data

        payload: dict[str, tuple[bytes, str]] = {path: (content(sha, path), mode) for mode, sha, path in included}
        overlay_src = [(sha, path) for _, sha, path in tree if path.startswith(OVERLAY_REL + "/")]
        overlay_rel = [path[len(OVERLAY_REL) + 1:] for _, path in overlay_src]
        overlay_raw = {rel: content(sha, path) for (sha, path), rel in zip(overlay_src, overlay_rel)}
    finally:
        reader.close()

    overrides, overlay_payload = [], {}
    for rel in overlay_rel:
        data = overlay_raw[rel]
        text = data.decode("utf-8")
        text = text.replace("@@KAYNAK_SHA@@", source).replace("@@KAYNAK_SHA7@@", source7)
        left = PLACEHOLDER.findall(text)
        if left:
            raise MirrorError(f"overlay/{rel}: tanınmayan yer tutucu {sorted(set(left))}")
        if rel in SAME_AS_ROOT and (rel not in payload or payload[rel][0] != data):
            raise MirrorError(f"overlay/{rel} özel repo kökündeki {rel} ile bayt-eşit değil")
        if rel in payload:
            overrides.append(rel)
        overlay_payload[rel] = text.encode("utf-8")

    if not dry_run:
        check_out_dir(out)
        empty_out_dir(out)
        for path, (data, mode) in payload.items():
            dst = out.joinpath(*PurePosixPath(path).parts)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            if mode == "100755":
                os.chmod(dst, 0o755)
        for rel, data in overlay_payload.items():
            dst = out.joinpath(*PurePosixPath(rel).parts)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)

    final = {p: d for p, (d, _) in payload.items()}
    final.update(overlay_payload)
    return verify(out, final, rules, excluded, overrides, overlay_rel, mask, head=head, source=source, dirty=sorted(set(dirty)),
                  dry_run=dry_run)


def verify(out: Path, final: dict[str, bytes], rules, excluded, overrides, overlay_rel, mask, *, head, source, dirty, dry_run) -> dict:
    """Çıktı ağacını (dry-run'da bellekteki kümeyi) yeniden tarar; özet sözlüğü döner."""
    if dry_run:
        files = {p: len(d) for p, d in final.items()}
        symlinks: list[str] = []
        content = final
    else:
        files, symlinks, content = {}, [], {}
        for p in sorted(out.rglob("*")):
            rel = p.relative_to(out).as_posix()
            if rel == ".git" or rel.startswith(".git/"):
                continue
            if p.is_symlink():
                symlinks.append(rel)
            elif p.is_file():
                files[rel] = p.stat().st_size
                content[rel] = p.read_bytes()
        if set(files) != set(final):
            raise MirrorError(f"çıktı kümesi beklenenden farklı: fazla {len(set(files) - set(final))}, eksik {len(set(final) - set(files))}")
        bad = [r for r in files if content[r] != final[r]]
        if bad:
            raise MirrorError(f"yazılan dosya beklenen baytlardan farklı: {len(bad)}")

    girmez_rx = [r["rx"] for r in rules if r["status"] == "GİRMEZ"]
    girmez_hit = [r for r in files if any(rx.match(r) for rx in girmez_rx)]
    pdf_zip = [r for r in files if PurePosixPath(r).suffix.lower() in (".pdf", ".zip")]
    over_hard = [r for r in files if files[r] > LIMIT_HARD]
    over_warn = sorted((r for r in files if files[r] > LIMIT_WARN), key=lambda r: -files[r])
    largest = sorted(files, key=lambda r: -files[r])[:5]

    def is_binary(rel: str) -> bool:
        return PurePosixPath(rel).suffix.lower() in BINARY_EXT or b"\0" in content[rel][:8192]

    def listed_binary(rel: str) -> bool:
        pp = PurePosixPath(rel)
        if rel.startswith("data/raw/tuik/") and pp.suffix.lower() == ".xls":
            return False
        if (rel.startswith("docs/") or rel.startswith("app/docs/")) and pp.suffix.lower() in IMAGE_EXT:
            return False
        return True

    binaries = [r for r in sorted(files) if is_binary(r)]
    binary_list = [r for r in binaries if listed_binary(r)]
    hyg_code = sum(mask.count(content[r].decode("utf-8", "replace")) for r in overlay_rel)
    hyg_bulletin = sum(len(BULLETIN.findall(content[r].decode("utf-8", "replace"))) for r in overlay_rel)

    checks = {
        "girmez_kalibina_uyan": len(girmez_hit),
        "pdf_zip": len(pdf_zip),
        "100MB_ustu": len(over_hard),
        "sembolik_bag": len(symlinks),
        "overlay_kasa_kodu": hyg_code,
        "overlay_bulten_adi": hyg_bulletin,
    }
    by_rule = {s: [{"kalip": r["pattern"], "dosya": r["files"], "MB": round(r["bytes"] / MB, 1), "gerekce": r["reason"]}
                   for r in rules if r["status"] == s] for s in ("GİRER", "GİRMEZ")}
    return {
        "kaynak_head": head,
        "kaynak_etiketi": source,
        "kirli_dosya": [mask(p) for p in dirty],
        "cikti": None if dry_run else str(out),
        "dry_run": dry_run,
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "kural": {"GİRER": sum(r["status"] == "GİRER" for r in rules), "GİRMEZ": sum(r["status"] == "GİRMEZ" for r in rules)},
        "dosya": len(files),
        "bayt": sum(files.values()),
        "MB": round(sum(files.values()) / MB, 1),
        "manifestten": len(final) - len(set(overlay_rel) - set(overrides)),
        "overlay": len(overlay_rel),
        "overlay_yerine_gecen": overrides,
        "girmez_dosya": len(excluded),
        "girmez_MB": round(sum(r["bytes"] for r in rules if r["status"] == "GİRMEZ") / MB, 1),
        "girmez_kural": by_rule["GİRMEZ"],
        "girer_kural": by_rule["GİRER"],
        "en_buyuk": [{"yol": mask(r), "MB": round(files[r] / MB, 1)} for r in largest],
        "50MB_ustu": [mask(r) for r in over_warn],
        "ikili_dosya": len(binaries),
        "ikili_liste": [mask(r) for r in binary_list],
        "denetim": checks,
        "denetim_gecti": all(v == 0 for v in checks.values()),
    }


def print_summary(s: dict) -> None:
    w = sys.stdout.write
    w(f"kaynak: {s['kaynak_etiketi']}\n")
    if s["kirli_dosya"]:
        w(f"  KİRLİ (--allow-dirty): {len(s['kirli_dosya'])} dosya HEAD'den farklı ya da izlenmiyor\n")
    w(f"çıktı: {s['cikti'] or '(dry-run: yazılmadı)'}\n")
    w(f"manifest: {s['kural']['GİRER']} GİRER + {s['kural']['GİRMEZ']} GİRMEZ kural; sha256 {s['manifest_sha256'][:12]}\n")
    w(f"ayna: {s['dosya']} dosya, {s['MB']} MB ({s['bayt']} bayt); manifestten {s['manifestten']}, overlay {s['overlay']} "
      f"(yerine geçen: {', '.join(s['overlay_yerine_gecen']) or '-'})\n")
    w(f"dışarıda: {s['girmez_dosya']} dosya, {s['girmez_MB']} MB\n")
    for r in s["girmez_kural"]:
        w(f"  GİRMEZ {r['kalip']}: {r['dosya']} dosya, {r['MB']} MB\n")
    w("en büyük: " + "; ".join(f"{x['yol']} {x['MB']} MB" for x in s["en_buyuk"]) + "\n")
    w(f"50 MB üstü: {len(s['50MB_ustu'])}\n")
    w(f"ikili dosya: {s['ikili_dosya']} (TÜİK .xls ve docs/app/docs görselleri hariç liste: {len(s['ikili_liste'])})\n")
    for r in s["ikili_liste"]:
        w(f"  {r}\n")
    w("denetim:\n")
    for k, v in s["denetim"].items():
        w(f"  {k}: {v}\n")
    w(f"SONUÇ: {'GEÇTİ' if s['denetim_gecti'] else 'KIRMIZI'}\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Herkese açık ayna ağacını üretir (FAZ9_PUBLIC_MIRROR K-MIR-1).")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"çıktı dizini (varsayılan {DEFAULT_OUT})")
    ap.add_argument("--dry-run", action="store_true", help="yalnız sınıflama, denetim ve özet; hiçbir şey yazmaz")
    ap.add_argument("--allow-dirty", action="store_true", help="geliştirme provası: çalışma kopyasını kullan, kaynak '+kirli'")
    ap.add_argument("--json", type=Path, help="özeti ayrıca bu JSON dosyasına yaz")
    a = ap.parse_args(argv)
    try:
        s = build(a.out.expanduser(), dry_run=a.dry_run, allow_dirty=a.allow_dirty)
    except MirrorError as e:
        sys.stderr.write(f"DUR: {e}\n")
        return 2
    print_summary(s)
    if a.json:
        a.json.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if s["denetim_gecti"] else 1


if __name__ == "__main__":
    sys.exit(main())

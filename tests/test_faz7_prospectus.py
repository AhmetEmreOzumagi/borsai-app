"""Faz 7 izahname alanları bekçisi (docs/prompts/FAZ7_PROSPECTUS_INTAKE.md; docs/faz7/prospectus/README.md).

Eski kohortun 135 üyesinin 7 listeleme öncesi izahname alanı (registry/oot/candidate_features_faz7/), kaynak belge MANIFEST'leri
(registry/oot/source_docs_faz7/) ve doğrulama çıktıları (docs/faz7/prospectus/) doğrulayıcının teslimiyle alındı ve
registry/oot/candidate_features_faz7/SHA256SUMS ile pinlendi. Bu dosya değer değiştirmez; tutarlılığı denetler:
(a) dosya kümeleri = evren listesindeki 135 MEMBER = registry/oot/inputs; (b) 7 alan, durum kümesi, MISSING <-> boş değer;
(c) alan başına durum sayıları (REPORT §1, sabit); (d) her dolu alanın (ve ek alıntısının) kaynağı MANIFEST'te, sha256'sı eşit,
yayın zamanı ilk işlem gününden önce; (e) SHA256SUMS bütün satırlarda tutuyor, dizinde pinsiz dosya yok; (f) sonuç alanı yok;
(g) mutasyon gösterimi geçici kopyada (repo dosyası değişmez).

Mutasyon çıktısı docs/faz7/prospectus/intake_mutation.txt'yi şu komut yeniden üretir (kopyada çalışır, repoya yazmaz):
    PYTHONPATH=.:tests .venv/bin/python tests/test_faz7_prospectus.py > docs/faz7/prospectus/intake_mutation.txt"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from borsai import registry as reg
from borsai.provenance import ROOT
from test_outcome_guard import OUTCOME_KEYS

FEAT_REL = "registry/oot/candidate_features_faz7"
MAN_REL = "registry/oot/source_docs_faz7"
DOCS_REL = "docs/faz7/prospectus"
INPUTS_REL = "registry/oot/inputs"
SUMS_NAME = "SHA256SUMS"
NEW_DIRS = (FEAT_REL, MAN_REL, DOCS_REL)
IGNORED_NAMES = {".DS_Store"}          # Finder artığı; içerik değil (.gitignore'da)

FIELDS = ("distribution_method", "price_stability_planned", "price_stability_days", "issuer_lockup_days",
          "shareholder_lockup_days", "sector", "participation_index_eligible")
STATUSES = ("VERIFIED", "CORRECTED", "FILLED", "MISSING")
EXPECTED_COUNTS = {   # docs/faz7/prospectus/REPORT.md §1 (VERIFIED, CORRECTED, FILLED, MISSING); sabit
    "distribution_method": (80, 5, 50, 0),
    "price_stability_planned": (99, 0, 36, 0),
    "price_stability_days": (93, 0, 42, 0),
    "issuer_lockup_days": (73, 3, 59, 0),
    "shareholder_lockup_days": (80, 3, 52, 0),
    "sector": (89, 0, 46, 0),
    "participation_index_eligible": (7, 0, 24, 104),
}
N_MEMBERS = 135
SHA_LINE = re.compile(r"^([0-9a-f]{64})  (\S.*)$")
RULE_PUBLICATION = "yayın zamanı ilk işlem gününden önce değil"
RULE_PIN = "sha256 tutmuyor"


def members() -> list[str]:
    """Evren listesindeki MEMBER kodları (docs/specs_faz6/ekler/evren_listesi.csv); başka sütun okunmaz."""
    with reg.UNIVERSE_PATH.open(encoding="utf-8", newline="") as fh:
        return sorted(r["ticker"] for r in csv.DictReader(fh) if r["status"] == reg.COHORT_MEMBER)


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _feature(root: Path, t: str) -> dict:
    return _json(root / FEAT_REL / f"{t}.json")


def _manifest(root: Path, t: str) -> dict:
    return _json(root / MAN_REL / t / "MANIFEST.json")


def _files(base: Path) -> list[Path]:
    return sorted(p for p in base.rglob("*") if p.is_file() and p.name not in IGNORED_NAMES)


# ---------------------------------------------------------------- (a) dosya kümeleri

def set_problems(root: Path = ROOT) -> list[str]:
    want = set(members())
    out = [] if len(want) == N_MEMBERS else [f"evren listesinde {len(want)} MEMBER var, {N_MEMBERS} bekleniyordu"]
    feat_dir, man_dir = root / FEAT_REL, root / MAN_REL
    got = {
        "özellik dosyaları": {p.stem for p in feat_dir.glob("*.json")},
        "kaynak MANIFEST dizinleri": {p.name for p in man_dir.iterdir() if p.is_dir()},
        "registry/oot/inputs": {p.stem for p in (root / INPUTS_REL).glob("*.json")},
    }
    for label, names in got.items():
        if names != want:
            out.append(f"{label}: MEMBER kümesiyle aynı değil (eksik {len(want - names)}, fazla {len(names - want)})")
    extra = sorted(p.name for p in feat_dir.iterdir() if p.name != SUMS_NAME and p.name not in IGNORED_NAMES
                   and not (p.suffix == ".json" and p.stem in want))
    if extra:
        out.append(f"{FEAT_REL}: beklenmeyen {len(extra)} dosya")
    for t in sorted(want & got["kaynak MANIFEST dizinleri"]):
        names = sorted(p.name for p in (man_dir / t).iterdir() if p.name not in IGNORED_NAMES)
        if names != ["MANIFEST.json"]:
            out.append(f"{t}: kaynak dizininde MANIFEST.json dışında dosya ya da eksik")
    for t in sorted(want & got["özellik dosyaları"]):
        if _feature(root, t).get("ticker") != t:
            out.append(f"{t}: özellik dosyasındaki ticker dosya adıyla aynı değil")
    for t in sorted(want & got["kaynak MANIFEST dizinleri"]):
        if (root / MAN_REL / t / "MANIFEST.json").is_file() and _manifest(root, t).get("ticker") != t:
            out.append(f"{t}: MANIFEST'teki ticker dizin adıyla aynı değil")
    return out


# ---------------------------------------------------------------- (b) 7 alan, durum, MISSING <-> boş değer

def field_problems(root: Path = ROOT) -> list[str]:
    out = []
    for t in members():
        fields = _feature(root, t).get("fields") or {}
        if set(fields) != set(FIELDS):
            out.append(f"{t}: alan kümesi 7 alanla aynı değil")
            continue
        for name in FIELDS:
            e = fields[name]
            status = e.get("status")
            if status not in STATUSES:
                out.append(f"{t}.{name}: durum {status!r} izinli kümede değil")
                continue
            empty = e.get("value") in (None, "")
            if (status == "MISSING") != empty:
                out.append(f"{t}.{name}: MISSING <-> boş değer kuralı bozuk (durum {status}, boş={empty})")
    return out


# ---------------------------------------------------------------- (c) durum sayıları

def status_counts(root: Path = ROOT) -> dict[str, tuple[int, ...]]:
    counts = {name: dict.fromkeys(STATUSES, 0) for name in FIELDS}
    for t in members():
        for name, e in (_feature(root, t).get("fields") or {}).items():
            if name in counts and e.get("status") in counts[name]:
                counts[name][e["status"]] += 1
    return {name: tuple(c[s] for s in STATUSES) for name, c in counts.items()}


# ---------------------------------------------------------------- (d) kaynak, sha256, yayın zamanı

def _publication_problem(published_at, first_trading: str) -> str | None:
    try:
        return None if reg.istanbul_date(published_at) < first_trading else RULE_PUBLICATION
    except (reg.RegistryError, ValueError, TypeError, AttributeError):
        return f"yayın zamanı okunamadı ({published_at!r})"


def source_problems(root: Path = ROOT) -> list[str]:
    """Dolu her alan (ve `extra_quotes` girdisi): source_id MANIFEST `documents` listesinde; source_sha256 MANIFEST sha256'sıyla
    aynı; published_at MANIFEST ile aynı ve (Europe/Istanbul tarihi) `registry/oot/inputs/<T>.json` ilk işlem gününden önce.
    Ayrıca MANIFEST'in her belgesi ilk işlem gününden önce yayımlanmıştır (kaynak belgeler sonuç içeremez)."""
    out = []
    for t in members():
        feat, man = _feature(root, t), _manifest(root, t)
        first_trading = reg.load_inputs(root / INPUTS_REL / f"{t}.json")[0]["fields"]["first_trading_date"]["value"]
        if not (feat.get("first_trading_date") == man.get("first_trading_date") == first_trading):
            out.append(f"{t}: first_trading_date özellik dosyası, MANIFEST ve girdi belgesinde aynı değil")
        docs = {d["source_id"]: d for d in man.get("documents") or []}
        if len(docs) != len(man.get("documents") or []):
            out.append(f"{t}: MANIFEST'te tekrarlanan source_id")
        for sid, d in docs.items():
            problem = _publication_problem(d.get("published_at"), first_trading)
            if problem:
                out.append(f"{t}: MANIFEST belgesi {sid}: {problem}")
        for name, e in (feat.get("fields") or {}).items():
            if e.get("status") == "MISSING":
                continue
            for label, ref in [(name, e)] + [(f"{name}.extra_quotes[{i}]", x) for i, x in enumerate(e.get("extra_quotes") or [])]:
                doc = docs.get(ref.get("source_id"))
                if doc is None:
                    out.append(f"{t}.{label}: source_id {ref.get('source_id')!r} MANIFEST belgeleri arasında yok")
                    continue
                if ref.get("source_sha256") != doc.get("sha256"):
                    out.append(f"{t}.{label}: source_sha256 MANIFEST sha256'sıyla aynı değil ({ref['source_id']})")
                if ref.get("published_at") != doc.get("published_at"):
                    out.append(f"{t}.{label}: published_at MANIFEST'tekiyle aynı değil ({ref['source_id']})")
                problem = _publication_problem(ref.get("published_at"), first_trading)
                if problem:
                    out.append(f"{t}.{label}: {problem} ({ref['source_id']})")
    return out


# ---------------------------------------------------------------- (e) SHA256SUMS pini

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin_problems(root: Path = ROOT) -> list[str]:
    """SHA256SUMS (sha256sum biçimi; yollar dosyanın kendi dizinine göreli) her satırda tutar; üç yeni dizindeki (SHA256SUMS
    hariç) hiçbir dosya pinsiz değildir, hedef dışı satır yoktur."""
    sums = root / FEAT_REL / SUMS_NAME
    if not sums.is_file():
        return [f"{FEAT_REL}/{SUMS_NAME} yok"]
    out, listed = [], {}
    for n, line in enumerate(sums.read_text(encoding="utf-8").splitlines(), 1):
        m = SHA_LINE.match(line)
        if not m:
            out.append(f"{SUMS_NAME} satır {n}: sha256sum biçimi değil")
            continue
        path = os.path.normpath(sums.parent / m.group(2))
        if path in listed:
            out.append(f"{SUMS_NAME} satır {n}: {m.group(2)} tekrarlanıyor")
        listed[path] = (m.group(1), m.group(2))
    targets = {os.path.normpath(p) for d in NEW_DIRS for p in _files(root / d)} - {os.path.normpath(sums)}
    for path in sorted(targets - set(listed)):
        out.append(f"pinsiz dosya: {os.path.relpath(path, root)}")
    for path, (digest, rel) in sorted(listed.items()):
        if path not in targets:
            out.append(f"hedef dışı satır: {rel}")
        elif _sha256(Path(path)) != digest:
            out.append(f"{RULE_PIN}: {rel}")
    return out


# ---------------------------------------------------------------- (f) sonuç alanı yok

def _keys_of(path: Path) -> set[str]:
    if path.suffix == ".json":
        return set(reg.json_keys(_json(path)))
    if path.suffix == ".jsonl":
        return {k for line in path.read_text(encoding="utf-8").splitlines() if line.strip() for k in reg.json_keys(json.loads(line))}
    if path.suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as fh:
            return set(next(csv.reader(fh), []))
    return set()


def outcome_key_problems(root: Path = ROOT) -> list[str]:
    """Üç yeni dizinde hiçbir JSON/JSONL anahtarı ya da CSV başlığı sonuç alanı adı değildir (`test_registry_carries_no_outcome_fields`
    `OUTCOME_KEYS` kümesi ve `registry.OOT_OUTCOME_KEYS`). Markdown ve düz metin okunmaz."""
    bad_names = OUTCOME_KEYS | reg.OOT_OUTCOME_KEYS
    out = []
    for d in NEW_DIRS:
        for p in _files(root / d):
            bad = _keys_of(p) & bad_names
            if bad:
                out.append(f"{p.relative_to(root).as_posix()}: sonuç alanı {sorted(bad)}")
    return out


# ---------------------------------------------------------------- gerçek repo

def test_a_file_sets_match_the_135_members():
    assert set_problems() == []
    assert len(members()) == N_MEMBERS


def test_b_seven_fields_status_and_missing_rule():
    assert field_problems() == []


def test_c_status_counts_match_report_table():
    assert status_counts() == EXPECTED_COUNTS
    assert sum(sum(v) for v in EXPECTED_COUNTS.values()) == 7 * N_MEMBERS


def test_d_sources_pinned_in_manifest_and_predate_first_trading_day():
    assert source_problems() == []


def test_e_sha256sums_pin_every_file():
    assert pin_problems() == []


def test_f_no_outcome_fields_in_new_directories():
    assert outcome_key_problems() == []


def test_no_source_pdfs_in_new_directories():
    assert [p.relative_to(ROOT).as_posix() for d in NEW_DIRS for p in _files(ROOT / d) if p.suffix.lower() == ".pdf"] == []


# ---------------------------------------------------------------- (g) mutasyon gösterimi (geçici kopya)

def mutation_report(work: Path) -> tuple[list[str], list[tuple[str, list[str], list[str]]]]:
    """Üç yeni dizini ve girdileri `work` altına kopyalar, kopyada üç mutasyon uygular (iki yayın zamanı, bir bayt); repo dosyalarına yazmaz.
    Döner: (rapor satırları, [(etiket, temel sorunlar, mutasyon sorunları)])."""
    copy = work / "copy"
    for rel in (*NEW_DIRS, INPUTS_REL):
        shutil.copytree(ROOT / rel, copy / rel)
    t = members()[0]
    feat_path, man_path = copy / FEAT_REL / f"{t}.json", copy / MAN_REL / t / "MANIFEST.json"
    checks, lines = [], []

    def restore():
        shutil.copy2(ROOT / FEAT_REL / f"{t}.json", feat_path)
        shutil.copy2(ROOT / MAN_REL / t / "MANIFEST.json", man_path)

    def record(label, base, mutated, detail, rule):
        checks.append((label, base, mutated))
        hit = next((p for p in mutated if rule in p), "-")
        lines.extend([f"{label}: {detail}", f"  temel kopya: {len(base)} sorun",
                      f"  mutasyon:    {len(mutated)} sorun; '{rule}' sorunu: {hit}"])

    base_d, base_e = source_problems(copy), pin_problems(copy)
    lines.append(f"Kopya temeli (değişmemiş): (d) {len(base_d)} sorun, (e) {len(base_e)} sorun")

    # M1a: özellik dosyasında bir kaynağın yayım zamanı ilk işlem gününe çekilir
    doc = _json(feat_path)
    entry = doc["fields"]["distribution_method"]
    pulled = f"{doc['first_trading_date']}T00:00:00+03:00"
    entry["published_at"] = pulled
    feat_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    record(f"M1a (d) {t}.distribution_method özellik dosyasında published_at ilk işlem gününe çekildi", base_d,
           source_problems(copy), f"published_at -> {pulled}", RULE_PUBLICATION)
    restore()

    # M1b: MANIFEST'te aynı kaynağın yayım zamanı ilk işlem gününe çekilir
    man = _json(man_path)
    for d in man["documents"]:
        if d["source_id"] == entry["source_id"]:
            d["published_at"] = pulled
    man_path.write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    record(f"M1b (d) {t} MANIFEST belgesinde published_at ilk işlem gününe çekildi", base_d, source_problems(copy),
           f"{entry['source_id']} published_at -> {pulled}", RULE_PUBLICATION)
    restore()

    # M2: bir özellik dosyasında tek bayt değişir ("note" anahtarı -> "Note")
    raw = bytearray(feat_path.read_bytes())
    i = raw.index(b'"note"') + 1
    raw[i] = ord("N")
    feat_path.write_bytes(bytes(raw))
    record(f"M2 (e) {t}.json içinde tek bayt değişti", base_e, pin_problems(copy), f"bayt {i}: 'n' -> 'N'", RULE_PIN)
    restore()

    after = (len(source_problems(copy)), len(pin_problems(copy)))
    lines.append(f"Geri yükleme sonrası kopya: (d) {after[0]} sorun, (e) {after[1]} sorun")
    lines.append(f"Gerçek repo (mutasyondan sonra): (d) {len(source_problems())} sorun, (e) {len(pin_problems())} sorun")
    return lines, checks


def test_g_mutations_turn_the_guard_red(tmp_path):
    lines, checks = mutation_report(tmp_path)
    assert len(checks) == 3
    for label, base, mutated in checks:
        assert base == [] and mutated, label
    assert any(RULE_PUBLICATION in p for p in checks[0][2]) and any(RULE_PUBLICATION in p for p in checks[1][2])
    assert checks[2][2] == [f"{RULE_PIN}: {members()[0]}.json"]
    assert lines[-1] == "Gerçek repo (mutasyondan sonra): (d) 0 sorun, (e) 0 sorun"
    assert source_problems() == [] and pin_problems() == []                  # repo dosyaları değişmedi


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        print("Faz 7 izahname alımı: bekçi mutasyon gösterimi (geçici kopya; repo dosyaları değişmez)")
        print("Komut: PYTHONPATH=.:tests .venv/bin/python tests/test_faz7_prospectus.py")
        print("\n".join(mutation_report(Path(d))[0]))

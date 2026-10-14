"""KITAP_AUDIT_1 Adım 8: §1.5–§1.6 sayıları, §3.13 açık noktalar, kitap/10 data/ ve registry/ yolları."""
import csv, json, os, re, subprocess, glob
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]; ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
def git(*a): return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, env=ENV).stdout.strip()
out = []; P = lambda *a: out.append(" ".join(str(x) for x in a))
P("[ÖLÇTÜM] commit sayısı (ee3796d'ye kadar):", git("rev-list", "--count", "ee3796d"), "| ilk/son commit:", git("log", "--reverse", "--format=%cI", "ee3796d").splitlines()[0], git("log", "-1", "--format=%cI", "ee3796d"))
for idx in ("INDEX.json", "INDEX_POST_D1.json", "INDEX_POST_BREAK.json"):
    j = json.load(open(ROOT / "models" / idx)); P(f"[ÖLÇTÜM] models/{idx}: {len(j['models'])} model")
P("[ÖLÇTÜM] push_proofs dosya:", len(os.listdir(ROOT / "registry/push_proofs")), "| farklı proven_commit:", len({json.load(open(p))["proven_commit_sha"] for p in (ROOT / "registry/push_proofs").glob("*.json")}))
P("[ÖLÇTÜM] records/<T>:", {d: len(os.listdir(ROOT / "registry/records" / d)) for d in sorted(os.listdir(ROOT / "registry/records"))}, "| post_break:", {d: len(os.listdir(ROOT / "registry/post_break" / d)) for d in sorted(os.listdir(ROOT / "registry/post_break"))}, "| post_d1 var:", (ROOT / "registry/post_d1").exists())
P("[ÖLÇTÜM] legacy_frozen klasör:", sorted(d for d in os.listdir(ROOT / "registry/legacy_frozen") if (ROOT / "registry/legacy_frozen" / d).is_dir()), "| dosya toplam:", sum(1 for p in (ROOT / "registry/legacy_frozen").rglob("*") if p.is_file()))
lp = json.load(open(ROOT / "registry/legacy_frozen/NETGL_20260916_V1_5/push_proof.json")); P("[ÖLÇTÜM] NETGL legacy push_proof:", {k: str(v)[:40] for k, v in lp.items() if k in ("created_at", "proven_commit_sha", "commit", "method", "status_created_at")} or list(lp.keys()))
lines = (ROOT / "experiments/log.jsonl").read_text().splitlines(); kinds = Counter(json.loads(l).get("kind") or json.loads(l).get("run_type") or json.loads(l).get("type") for l in lines)
P("[ÖLÇTÜM] experiments/log.jsonl satır:", len(lines), "| tür:", dict(kinds), "| anahtarlar:", sorted(json.loads(lines[0]).keys())[:12])
P("[ÖLÇTÜM] docs/prompts dosya:", len([p for p in (ROOT / "docs/prompts").iterdir() if p.is_file()]), "(izlenmeyen KITAP/FAZ10/TUFE dahil) | git'teki:", len([l for l in git("ls-files", "docs/prompts").splitlines()]))
P("[ÖLÇTÜM] tests/test_*.py:", len(list((ROOT / "tests").glob("test_*.py"))), "| borsai/*.py:", len(list((ROOT / "borsai").glob("*.py"))), "satır:", sum(len(p.read_text().splitlines()) for p in (ROOT / "borsai").glob("*.py")))
ipos = list(csv.DictReader(open(ROOT / "registry/ipos.csv", encoding="utf-8")))
P("[ÖLÇTÜM] ipos.csv:", len(ipos), dict(Counter(r["status"] for r in ipos)), "| OUT_OF_SCOPE nedenleri:", dict(Counter(r["skip_reason"] for r in ipos if r["status"] != "FROZEN")), "| ticker tekrarları:", [t for t, c in Counter(r["ticker"] for r in ipos).items() if c > 1])
man = list(csv.DictReader(open(ROOT / "data/raw/bist/MANIFEST.csv", encoding="utf-8")))
P("[ÖLÇTÜM] MANIFEST.csv:", len(man), dict(Counter(r["kind"] for r in man)), "bayt", sum(int(r["bytes"]) for r in man), "| indirme günü:", dict(Counter(r["downloaded_at"][:10] for r in man)))
# §1.5.1 zaman çizelgesi
for c, label in (("7cb49cf", "16 modelli kayıt"), ("f1f9d44", "ilk sonuçlar"), ("7c18c0f", "post_d1 freeze"), ("c1eb7ae", "D4-D10"), ("4d3c9a2", "break freeze"), ("7ee0027", "makine kaydı commit")):
    P(f"[ÖLÇTÜM] {label} {c}: {git('log', '-1', '--format=%cI %s', c)[:70]}")
rec = json.load(open(glob.glob(str(ROOT / "registry/records/NETGL/*.json"))[0])); P("[ÖLÇTÜM] NETGL kayıt recorded_at:", rec.get("recorded_at"), rec.get("recorded_at_basis"), "| model n:", len(rec["models"]), "| ret:", sum(1 for m in rec["models"] if m.get("refusal") or m.get("refused")))
mb = sorted(glob.glob(str(ROOT / "registry/post_break/NETGL/*.json"))); P("[ÖLÇTÜM] NETGL post_break dosya:", [Path(p).name[:30] for p in mb])
# §3.13 açık noktalar
ext = list(csv.DictReader(open(ROOT / "data/raw/pay_calendar_b_extension_20260820_20261231.csv", encoding="utf-8")))
P("[ÖLÇTÜM] §3.13: B uzatması XU100'e karşı denetlenmemiş satır:", sum("NOT_YET" in r["verification_status"] for r in ext), "| 2027 takvim dosyası var:", bool(list((ROOT / "data/raw").glob("*2027*"))),
  "| TÜFE son ay:", list(csv.DictReader(open(ROOT / "data/raw/tuik/tufe_genel_2025_100.csv")))[-1]["month"], "| ENV.md lisans sorusu:", "lisans" in (ROOT / "docs/ENV.md").read_text().lower(),
  "| SPEC_APP satır 601 'lisans':", "lisans" in ((ROOT / "docs/app/SPEC_APP.md").read_text().splitlines()[600:601] or [""])[0].lower())
# kitap/10 data/ ve registry/ yolları
txt = (ROOT / "docs/fable_kitap_audit/kitap/10_dosya_dizini.md").read_text()
paths = sorted({m for m in re.findall(r"`((?:data|registry)/[^`]+)`", txt)})
missing = []
for p in paths:
    pat = re.sub(r"<[^>]+>", "*", p).rstrip("/")
    if not (ROOT / pat).exists() and not glob.glob(str(ROOT / pat)) and not glob.glob(str(ROOT / pat) + "*"): missing.append(p)
P("[ÖLÇTÜM] kitap/10 data/ ve registry/ yol sayısı:", len(paths), "| var olmayan:", missing)
# §3.2.1 '73 satır... 59 dosya 2026-09-22, 14 dosya 2026-09-30' ve §3.10.3 'ilk koşu 5579' zaten ölçüldü; §3.9.2 31 belge ölçüldü.
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n", encoding="utf-8"); print("\n".join(out))

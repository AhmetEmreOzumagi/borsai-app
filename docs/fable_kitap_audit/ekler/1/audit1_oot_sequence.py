"""KITAP_AUDIT_1 Adım 6 (eski kohort sırası): OOT sonuç dosyalarını getiren commit'ler, OOT tahmin kayıtlarının push kanıtı, kasa açılışı.
Yalnız sayı yazılır; kasa kodları yazılmaz."""
import csv, json, os, subprocess
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
def git(*a): return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, env=ENV).stdout.strip()
def first_add(path):
    s = git("log", "--diff-filter=A", "--format=%H %cI", "--", path).strip().splitlines()
    return tuple(s[-1].split()) if s else (None, None)
def is_anc(a, b): return subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", a, b], env=ENV).returncode == 0
out = []; P = lambda *a: out.append(" ".join(str(x) for x in a))
with open(ROOT / "registry/oot/cohort_pre_h99.csv", encoding="utf-8", newline="") as fh: coh = list(csv.DictReader(fh))
members = [r for r in coh if r["status"] == "MEMBER"]
vault = {r["ticker"]: r["vault"] for r in members}
pp = {}
for f in os.listdir(ROOT / "registry/push_proofs"):
    j = json.load(open(ROOT / "registry/push_proofs" / f)); pp[j["proven_commit_sha"]] = j["created_at"]
# sonuç dosyaları
by_commit = {}
for t, v in vault.items():
    sha, dt = first_add(f"data/outcomes_oot/{t}.csv")
    by_commit.setdefault((sha, dt), Counter())["SEALED" if v == "SEALED" else "OPEN*"] += 1
for (sha, dt), c in sorted(by_commit.items(), key=lambda x: x[0][1]):
    P(f"[ÖLÇTÜM] outcomes_oot ekleyen commit {sha[:7]} {dt} {git('log','-1','--format=%s',sha)[:60]}: {dict(c)} push_proof={pp.get(sha)}")
# OOT tahmin kayıtları
rec_commits = Counter(); rec_n = 0
for t in vault:
    for f in sorted(os.listdir(ROOT / "registry/oot/records" / t)):
        sha, dt = first_add(f"registry/oot/records/{t}/{f}"); rec_commits[(sha, dt)] += 1; rec_n += 1
P("[ÖLÇTÜM] OOT kayıt dosyası n =", rec_n, "| ekleyen commit'ler:", [(s[:7], d, n, pp.get(s, "PUSH_PROOF_YOK")) for (s, d), n in sorted(rec_commits.items(), key=lambda x: x[0][1])])
# her kayıt commit'i, her sonuç commit'inin atası mı; push kanıtı created_at < sonuç commit zamanı mı
for (osha, odt) in by_commit:
    anc = all(is_anc(rs, osha) for (rs, _) in rec_commits)
    proofs_before = all(pp.get(rs, "9999") < odt.replace("+03:00", "Z") or pp.get(rs, "9999")[:19] < git("log", "-1", "--format=%cI", osha) for (rs, _) in rec_commits)
    P(f"[ÖLÇTÜM] sonuç commit {osha[:7]}: bütün kayıt commit'leri atası={anc}; kayıt push kanıtları (UTC) < sonuç commit zamanı: {[(rs[:7], pp.get(rs)) for (rs, _) in rec_commits]} vs {odt}")
# kasa işaret dosyası ve kasa sonuçları
vsha, vdt = first_add("registry/oot/VAULT_OPEN.json")
P("[ÖLÇTÜM] VAULT_OPEN.json ekleyen commit", vsha[:7], vdt, "push_proof", pp.get(vsha), "| içerik anahtarları:", list(json.load(open(ROOT / "registry/oot/VAULT_OPEN.json")).keys()))
sealed_commits = {k for k, c in by_commit.items() if c.get("SEALED")}
P("[ÖLÇTÜM] kasa (SEALED) sonuç dosyası sayısı:", sum(v == "SEALED" for v in vault.values()), "| bunları getiren commit'ler VAULT_OPEN commit'inin torunu mu:", [(s[:7], is_anc(vsha, s)) for (s, _) in sealed_commits])
# kasa kodları repoda başka yerde (docs, scores) geçiyor mu? yalnız sayı
sealed = [t for t, v in vault.items() if v == "SEALED"]
hits = Counter()
for sub in ("docs", "scores", "models", "experiments"):
    for p in (ROOT / sub).rglob("*"):
        if p.is_file() and p.suffix in (".md", ".json", ".jsonl", ".txt", ".csv"):
            try: txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception: continue
            n = sum(t in txt for t in sealed)
            if n: hits[sub] += 1
P("[ÖLÇTÜM] kasa kodlarından en az birini içeren dosya sayısı (docs/scores/models/experiments, kasa açılışından sonra beklenen):", dict(hits))
# docs/faz7 vault opening docs date
P("[ÖLÇTÜM] kohort: üye", len(members), "| kasa etiketi:", dict(Counter(vault.values())), "| yıl tabakaları (SEALED/OPEN):", {y: (sum(1 for r in members if r['year']==y and r['vault']=='SEALED'), sum(1 for r in members if r['year']==y and r['vault']!='SEALED')) for y in sorted({r['year'] for r in members})})
# diğer OOT klasör sayıları (§10)
for d in ("registry/oot/inputs", "registry/oot/records", "registry/oot/post_d1", "registry/oot/d1_rows", "registry/oot/candidate_features", "registry/oot/candidate_features_faz7", "registry/oot/source_docs", "registry/oot/source_docs_faz7", "data/outcomes_oot", "data/outcomes_oot/raw"):
    p = ROOT / d; items = [x for x in p.iterdir() if not x.name.startswith(".")] if p.exists() else []
    files = sum(1 for x in p.rglob("*") if x.is_file()) if p.exists() else 0
    P(f"[ÖLÇTÜM] {d}: var={p.exists()} öğe={len(items)} dosya(özyineli)={files}")
n_docs = sum(len(json.load(open(p))["documents"]) if isinstance(json.load(open(p)).get("documents"), list) else len(json.load(open(p))["documents"]) for p in (ROOT / "registry/oot/source_docs_faz7").glob("*/MANIFEST.json"))
P("[ÖLÇTÜM] source_docs_faz7 manifestlerdeki belge sayısı:", n_docs, "| source_docs (faz6) belge sayısı:", sum(len(json.load(open(p))["documents"]) if isinstance(json.load(open(p)).get("documents"), list) else len(json.load(open(p))["documents"]) for p in (ROOT / "registry/oot/source_docs").glob("*/MANIFEST.json")),
  "| faz6 PDF repoda:", sum(1 for p in (ROOT / "registry/oot/source_docs").rglob("*.pdf")))
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n", encoding="utf-8"); print("\n".join(out))

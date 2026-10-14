#!/usr/bin/env bash
# Sıra kanıtları (BORSAI_FAZ7_FABLE_V1_REPRO_AUDIT_20260926): yalnız okuma komutları, GIT_OPTIONAL_LOCKS=0. Çıktı: sira_kanitlari.txt
set -u
cd "$(dirname "$0")/../../.."
export GIT_OPTIONAL_LOCKS=0
echo "# Sıra kanıtları; alındığı an: $(date -u +%Y-%m-%dT%H:%M:%SZ); HEAD $(git rev-parse --short HEAD)"
echo
echo '## 1. Şartname push kanıtı < commit A zamanı'
echo '$ registry/push_proofs/6a16c160e0149fd868dd11b877b3ab050634499d.json -> created_at, proven_commit_sha, method'
python3 -c "import json; d=json.load(open('registry/push_proofs/6a16c160e0149fd868dd11b877b3ab050634499d.json')); print({k:d[k] for k in ('created_at','proven_commit_sha','method','repo_slug')})"
echo '$ TZ=UTC git log --format="%h %ci | UTC %cd | %s" --date=format-local:%Y-%m-%dT%H:%M:%SZ -6'
TZ=UTC git --no-pager log --format='%h %ci | UTC %cd | %s' --date=format-local:%Y-%m-%dT%H:%M:%SZ -6
echo '=> kanıt 2026-09-25T18:09:45Z < A (2a21a96) 2026-09-26T00:10:01Z: EVET'
echo
echo '## 2. Şartname değişmedi'
echo '$ git diff 6a16c16 f5d7609 -- docs/specs_faz7/SPEC_HAZARD_V1.md | wc -c'
git --no-pager diff 6a16c16 f5d7609 -- docs/specs_faz7/SPEC_HAZARD_V1.md | wc -c
echo '$ sha256 6a16c16 / HEAD:'
git show 6a16c16:docs/specs_faz7/SPEC_HAZARD_V1.md | shasum -a 256 | cut -c1-64
shasum -a 256 docs/specs_faz7/SPEC_HAZARD_V1.md | cut -c1-64
echo '$ git log -- docs/specs_faz7/KARARLAR.md (tek commit beklenir) ve diff 2a21a96..f5d7609 | wc -c'
git --no-pager log --format='%h %s' -- docs/specs_faz7/KARARLAR.md
git --no-pager diff 2a21a96 f5d7609 -- docs/specs_faz7/KARARLAR.md | wc -c
echo
echo '## 3. Commit A ağacında sonuç yok'
echo '$ git ls-tree -r --name-only 2a21a96 -- tests/reference/macos_golden_faz7 | wc -l'
git --no-pager ls-tree -r --name-only 2a21a96 -- tests/reference/macos_golden_faz7 | wc -l
echo '$ git show 2a21a96:docs/MODELS.md | grep -c "Faz 7"'
git --no-pager show 2a21a96:docs/MODELS.md | grep -c "Faz 7"
echo '$ git show 2a21a96:experiments/log.jsonl | grep -c faz7_golden ; grep -c ceiling_hazard_v1'
git --no-pager show 2a21a96:experiments/log.jsonl | grep -c "faz7_golden"
git --no-pager show 2a21a96:experiments/log.jsonl | grep -c "ceiling_hazard_v1"
echo '$ git show --stat 70b67d1 | grep -E "log.jsonl|MODELS.md|macos_golden_faz7" | head -4'
git --no-pager show --stat 70b67d1 | grep -E "log.jsonl|MODELS.md|macos_golden_faz7" | head -4
echo
echo '## 4. Kod ve veri sonuçtan sonra değişmedi'
echo '$ git diff 2a21a96 f5d7609 -- borsai data | wc -c'
git --no-pager diff 2a21a96 f5d7609 -- borsai data | wc -c
echo '$ git diff --stat 2a21a96 f5d7609 (B ve R commitlerinde değişen yollar)'
git --no-pager diff --stat 2a21a96 f5d7609 | tail -25
echo
echo '## 5. Günlükteki resmi koşular: git_commit, borsai_dirty, şartname belgesi sha, veri sürümü'
python3 - <<'EOF'
import json
for l in open('experiments/log.jsonl', encoding='utf-8'):
    d = json.loads(l)
    if d.get('context') == 'faz7_golden':
        print(d['model_id'], d['git_commit'][:7], 'dirty', d['borsai_dirty'], d['started_at'], 'spec_doc', d['spec_document_sha256'][:12], 'dv', d['data_version_sha256'][:12])
m = json.load(open('tests/reference/macos_golden_faz7/MANIFEST.json'))
print('MANIFEST', m['git_commit'][:7], 'dirty', m['borsai_dirty'], m['created_at'])
EOF
echo
echo '## 6. T2: app altın vektörleri ve eski altın dizinler'
echo '$ .venv/bin/python app/parity/gen_golden.py --check'
.venv/bin/python app/parity/gen_golden.py --check
echo '$ git diff --stat 6a16c16 f5d7609 -- tests/reference/macos_golden tests/reference/macos_golden_faz1b tests/reference/macos_golden_faz4 tests/reference/macos_golden_faz5 app/parity/golden'
git --no-pager diff --stat 6a16c16 f5d7609 -- tests/reference/macos_golden tests/reference/macos_golden_faz1b tests/reference/macos_golden_faz4 tests/reference/macos_golden_faz5 app/parity/golden
echo '$ git diff 6a16c16 f5d7609 -- app/parity/golden/MANIFEST.json (yalnız pin satırı)'
git --no-pager diff 6a16c16 f5d7609 -- app/parity/golden/MANIFEST.json | grep '^[-+] '
echo '$ v0 / @INF / PB tavan ledger sha256 (ilk 12) ve pinler 976b4dcea981 / 90b610463de4:'
shasum -a 256 tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv tests/reference/macos_golden_faz1b/ceiling_hazard_v0@INF_fold_ledger.csv tests/reference/macos_golden_faz1b/pb_ceiling_v0_fold_ledger.csv tests/reference/macos_golden_faz1b/pb_ceiling_v0@INF_fold_ledger.csv | cut -c1-12,65-
echo
echo '## 7. Açık küme sonuçları (S5 77b54f7) v1 kodundan (2a21a96) önce: v1 için OOT_RETRO (§7.2)'
git merge-base --is-ancestor 77b54f7 2a21a96; echo "77b54f7 ata(2a21a96) rc=$? (0 = evet)"
git merge-base --is-ancestor 2a21a96 77b54f7; echo "2a21a96 ata(77b54f7) rc=$? (1 = hayır -> frozen_ok yanlış -> OOT_RETRO)"

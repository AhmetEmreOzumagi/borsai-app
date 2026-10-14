#!/usr/bin/env bash
# Sıra kanıtları (BORSAI_FAZ7C_FABLE_REPRO_AUDIT adım 2-vi, 2-vii); yalnız okuma git komutları.
set -u
cd "$(dirname "$0")/../../.."
G="env GIT_OPTIONAL_LOCKS=0 git --no-pager"
echo "== HEAD =="; $G log --oneline -8
echo; echo "== (vi) şartname push kanıtı < A commit zamanı =="
echo "SPEC commit 4fe4e51: $($G log -1 --format='%cI' 4fe4e51)"
python3 -c "import json; d=json.load(open('registry/push_proofs/4fe4e51b1b8d369fed4f199350fcc3da6d6cfd55.json')); print('push kanıtı created_at (UTC):', d['created_at'], 'proven:', d['proven_commit_sha'][:7], 'method:', d['method'])"
echo "A commit 3c93f9c: $($G log -1 --format='%cI' 3c93f9c)  (UTC: $(TZ=UTC date -j -f '%Y-%m-%dT%H:%M:%S%z' "$($G log -1 --format='%cI' 3c93f9c | sed 's/:\([0-9][0-9]\)$/\1/')" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null))"
echo "4fe4e51 A'nın atası mı: $($G merge-base --is-ancestor 4fe4e51 3c93f9c && echo evet || echo HAYIR)"
echo "resmi koşu git_commit (günlük): $(grep '"context":"faz7c_golden"' experiments/log.jsonl | head -1 | python3 -c "import sys,json; e=json.loads(sys.stdin.readline()); print(e['git_commit'][:7], 'dirty', e['borsai_dirty'], e['started_at'])")"
echo; echo "== (vi) git diff 4fe4e51 197a741 -- SPEC_C_V0.md (bayt) =="; $G diff 4fe4e51 197a741 -- docs/specs_faz7_c/SPEC_C_V0.md | wc -c
echo "SPEC_C_V0.md sha256: $(shasum -a 256 docs/specs_faz7_c/SPEC_C_V0.md | cut -c1-16)…; KESIF.md ve ekler değişti mi (4fe4e51..HEAD): $($G diff --stat 4fe4e51 HEAD -- docs/specs_faz7_c/KESIF.md docs/specs_faz7_c/ekler | wc -l) satır"
echo; echo "== (vi) KARARLAR_C tek commit'te ve sonra değişmedi =="; $G log --oneline --follow -- docs/specs_faz7_c/KARARLAR_C.md
echo "KARARLAR_C sha256: $(shasum -a 256 docs/specs_faz7_c/KARARLAR_C.md | cut -c1-16)…; HEAD içeriği == 3c93f9c içeriği: $([ "$($G show 3c93f9c:docs/specs_faz7_c/KARARLAR_C.md | shasum -a 256)" = "$(shasum -a 256 < docs/specs_faz7_c/KARARLAR_C.md)" ] && echo evet || echo HAYIR)"
echo "KARARLAR_C için ayrı push kanıtı: $(ls registry/push_proofs | wc -l | tr -d ' ') kanıt dosyası; 3c93f9c ya da torunu için kanıt var mı: $(for f in registry/push_proofs/*.json; do s=$(python3 -c "import json;print(json.load(open('$f'))['proven_commit_sha'])"); $G merge-base --is-ancestor 3c93f9c $s 2>/dev/null && echo "$s"; done | head -1 || true)"
echo; echo "== (vi) A ağacında faz7c altın dizini, MODELS.md bölümü, günlükte faz7c satırı yok =="
echo "A: macos_golden_faz7c dosya sayısı: $($G ls-tree -r 3c93f9c --name-only | grep -c macos_golden_faz7c)"
echo "A: MODELS.md '## Faz 7C' başlığı: $($G show 3c93f9c:docs/MODELS.md | grep -c '^## Faz 7C')"
echo "A: günlükte fall_d10_v0 / exploration satırı: $($G show 3c93f9c:experiments/log.jsonl | grep -c 'fall_d10_v0\|"exploration"')"
echo "A: günlük satır sayısı $($G show 3c93f9c:experiments/log.jsonl | wc -l | tr -d ' '), HEAD $(wc -l < experiments/log.jsonl | tr -d ' ') (fark = 4 backtest + 2054 exploration = 2058?)"
echo "B (acaca2d): günlük +$($G diff --numstat 77d0ee5 acaca2d -- experiments/log.jsonl | cut -f1) satır; A2/A3'te günlük değişti mi: $($G diff --stat 3c93f9c 77d0ee5 -- experiments/log.jsonl | wc -l)"
echo; echo "== (vii) git diff 3c93f9c 197a741 -- borsai =="; $G diff --stat 3c93f9c 197a741 -- borsai
echo "A2 (1239e45) dosyaları:"; $G show --stat --format='  %h %s' 1239e45 | tail -6
echo "A3 (77d0ee5) dosyaları:"; $G show --stat --format='  %h %s' 77d0ee5 | tail -6
echo "B (acaca2d) borsai/ değişikliği: $($G diff --stat 77d0ee5 acaca2d -- borsai | wc -l) satır; R (197a741) borsai/: $($G diff --stat acaca2d 197a741 -- borsai | wc -l) satır"
echo "A2/A3 tests/ değişiklikleri:"; $G diff --stat 3c93f9c 77d0ee5 -- tests
echo; echo "== (vii) MANIFEST git_commit ve borsai kaynak sha =="
python3 -c "import json; m=json.load(open('tests/reference/macos_golden_faz7c/MANIFEST.json')); print('git_commit', m['git_commit'][:7], 'dirty', m['borsai_dirty'], 'borsai_source_sha256', m['borsai_source_sha256'][:12])"
echo; echo "== commit zamanları =="; for c in 4fe4e51 3c93f9c 1239e45 77d0ee5 acaca2d 197a741; do echo "$c $($G log -1 --format='%cI %s' $c | cut -c1-90)"; done

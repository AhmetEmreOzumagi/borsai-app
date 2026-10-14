#!/usr/bin/env bash
# Sıra, uygunluk ve CLAUDE.md eki kanıtları (BORSAI_FAZ8_FABLE_REPRO_AUDIT adım 3-iv, 3-v). Yalnız okuma git komutları.
set -u
cd "$(dirname "$0")/../../.."
export GIT_OPTIONAL_LOCKS=0
echo "# sira_kanitlari — $(date -u +%Y-%m-%dT%H:%M:%SZ); HEAD $(git rev-parse HEAD)"
echo
echo "## (iv-1) atalık zinciri 7d78d43 → 5d84e88 → fa623df → df338c2 → c84ba64"
for pair in "7d78d43 5d84e88" "5d84e88 fa623df" "fa623df df338c2" "df338c2 c84ba64"; do
  set -- $pair
  if git merge-base --is-ancestor "$1" "$2"; then echo "$1 -> $2 : ancestor YES"; else echo "$1 -> $2 : ancestor NO"; fi
done
echo "first-parent zinciri:"; git --no-pager log --format='  %h <- %p  %s' -5 | cut -c1-110
echo
echo "## (iv-2) A ağacında (fa623df) sonuç yok"
echo "docs/faz8/ içeriği (A):"; git ls-tree -r --name-only fa623df -- docs/faz8/ | sed 's/^/  /'
echo "docs/faz8/backtest/ (A): $(git ls-tree -r --name-only fa623df -- docs/faz8/backtest/ | wc -l | tr -d ' ') dosya"
echo "MODELS.md '## Faz 8' başlığı (A): $(git show fa623df:docs/MODELS.md | grep -c '^## Faz 8')"
echo "log.jsonl satır sayısı (7d78d43 / 5d84e88 / fa623df / df338c2 / c84ba64): $(git show 7d78d43:experiments/log.jsonl | wc -l | tr -d ' ') / $(git show 5d84e88:experiments/log.jsonl | wc -l | tr -d ' ') / $(git show fa623df:experiments/log.jsonl | wc -l | tr -d ' ') / $(git show df338c2:experiments/log.jsonl | wc -l | tr -d ' ') / $(git show c84ba64:experiments/log.jsonl | wc -l | tr -d ' ')"
echo "log.jsonl'da break_floor_v0 geçen satır (A / B): $(git show fa623df:experiments/log.jsonl | grep -c break_floor_v0) / $(git show df338c2:experiments/log.jsonl | grep -c break_floor_v0)"
echo "log.jsonl yalnız ekleme (A → B önek mi): $(git show fa623df:experiments/log.jsonl > /tmp/borsai_faz8_audit/logA.txt; git show df338c2:experiments/log.jsonl > /tmp/borsai_faz8_audit/logB.txt; python3 -c "import sys; a=open('/tmp/borsai_faz8_audit/logA.txt','rb').read(); b=open('/tmp/borsai_faz8_audit/logB.txt','rb').read(); print('EVET' if b.startswith(a) else 'HAYIR')")"
echo
echo "## (iv-3) şartname değişmedi"
echo "git diff 7d78d43 c84ba64 -- docs/specs_faz8/SPEC_BREAK_V0.md : '$(git diff 7d78d43 c84ba64 -- docs/specs_faz8/SPEC_BREAK_V0.md | wc -c | tr -d ' ')' bayt (0 = boş)"
echo "git diff 7d78d43 c84ba64 --stat -- docs/specs_faz8/ :"; git --no-pager diff 7d78d43 c84ba64 --stat -- docs/specs_faz8/ | sed 's/^/  /'
echo "SPEC_BREAK_V0.md sha256 @7d78d43: $(git show 7d78d43:docs/specs_faz8/SPEC_BREAK_V0.md | shasum -a 256 | cut -c1-64)"
echo "SPEC_BREAK_V0.md sha256 @HEAD   : $(shasum -a 256 docs/specs_faz8/SPEC_BREAK_V0.md | cut -c1-64)"
echo
echo "## (iv-4) KARARLAR yalnız K'de (5d84e88) ve yalnız §C"
for pair in "7d78d43 5d84e88" "5d84e88 fa623df" "fa623df df338c2" "df338c2 c84ba64"; do
  set -- $pair
  echo "  $1..$2: $(git diff $1 $2 --numstat -- docs/specs_faz8/KARARLAR.md | awk '{print "+"$1" -"$2}')"
done
echo "  K'deki değişen satırların hepsi §C tablosu/notu mu (diff'teki -/+ satırları):"
git --no-pager diff -U0 7d78d43 5d84e88 -- docs/specs_faz8/KARARLAR.md | grep '^[-+]' | grep -v '^[-+][-+]' | cut -c1-90 | sed 's/^/    /'
echo "  diff hunk başlıkları:"; git --no-pager diff -U0 7d78d43 5d84e88 -- docs/specs_faz8/KARARLAR.md | grep '^@@' | sed 's/^/    /'
echo "  §C başlığının satırı: $(grep -n '^## C\.' docs/specs_faz8/KARARLAR.md | cut -d: -f1); 'Ek notlar' satırı: $(grep -n '^Ek notlar' docs/specs_faz8/KARARLAR.md | cut -d: -f1)"
echo "KARARLAR.md sha256 @HEAD: $(shasum -a 256 docs/specs_faz8/KARARLAR.md | cut -c1-64) (specs.SPEC_DOCUMENTS_FAZ8: $(grep -A1 'KARARLAR_FAZ8' borsai/specs.py | grep -o '[0-9a-f]\{64\}'))"
echo
echo "## (iv-5) §6 kuralları (OPERATIONAL_RULES_FAZ8, FAZ8_RULES) A'da sabit, B ve R'de değişmedi"
echo "borsai/specs.py blob (A / B / R): $(git rev-parse fa623df:borsai/specs.py) / $(git rev-parse df338c2:borsai/specs.py) / $(git rev-parse c84ba64:borsai/specs.py)"
echo "OPERATIONAL_RULES_FAZ8 A'da var mı: $(git show fa623df:borsai/specs.py | grep -c 'OPERATIONAL_RULES_FAZ8: tuple')"
echo "borsai/report_faz8.py blob (A / B / R): $(git rev-parse fa623df:borsai/report_faz8.py) / $(git rev-parse df338c2:borsai/report_faz8.py) / $(git rev-parse c84ba64:borsai/report_faz8.py)"
echo
echo "## (iv-6) git diff fa623df df338c2 -- borsai (boş olmalı)"
echo "  bayt: $(git diff fa623df df338c2 -- borsai | wc -c | tr -d ' ')"
echo "  git diff fa623df c84ba64 -- borsai tests/test_faz8_break.py tests/test_faz8_model.py tests/faz8_support.py tests/test_faz8_support.py : $(git diff fa623df c84ba64 -- borsai tests/test_faz8_break.py tests/test_faz8_model.py tests/faz8_support.py tests/test_faz8_support.py | wc -c | tr -d ' ') bayt"
echo "  B'de değişen dosyalar:"; git --no-pager show --stat --format='' df338c2 | sed 's/^/    /'
echo "  R'de değişen dosyalar:"; git --no-pager show --stat --format='' c84ba64 | sed 's/^/    /'
echo
echo "## (v) CLAUDE.md eki §9.4 cümlesiyle birebir"
python3 - <<'EOF'
import re
spec = open("docs/specs_faz8/SPEC_BREAK_V0.md", encoding="utf-8").read()
m = re.search(r"^> (POST_BREAK \(kırılma akşamı\).*)$", spec, re.M)
s = m.group(1).strip()
cl = open("CLAUDE.md", encoding="utf-8").read()
i = cl.find("POST_BREAK (kırılma akşamı)")
line = cl[i:cl.find("\n", i)].strip()
print(f"  şartname §9.4 cümlesi {len(s)} karakter; CLAUDE.md satırı {len(line)} karakter; birebir: {s == line}")
print(f"  CLAUDE.md'de bu satır kural 1'in devam satırı mı (3 boşluk girinti): {cl.splitlines()[cl[:i].count(chr(10))].startswith('   POST_BREAK')}")
EOF
echo "CLAUDE.md değişimi K'de (5d84e88): $(git diff 7d78d43 5d84e88 --numstat -- CLAUDE.md | awk '{print "+"$1" -"$2}'); sonrasında: $(git diff 5d84e88 c84ba64 -- CLAUDE.md | wc -c | tr -d ' ') bayt"
echo
echo "## (vi-N19) sayaç istisnası ve kasa testi"
echo "scores/scores.json == 87434ff: $(git show 87434ff:scores/scores.json | cmp -s - scores/scores.json && echo EVET || echo HAYIR)"
echo "scores/scores_post_d1.json == 87434ff: $(git show 87434ff:scores/scores_post_d1.json | cmp -s - scores/scores_post_d1.json && echo EVET || echo HAYIR)"
echo "scores/ 87434ff'ten sonra değişti mi: $(git diff 87434ff HEAD --stat -- scores/ | wc -l | tr -d ' ') satır (0 = hayır)"
.venv/bin/python - <<'EOF'
import sys; sys.path.insert(0, "tests")
import faz8_support as fs8
from borsai.specs import H99_DATA_VERSION_SHA256
print(f"  faz8_variants(H99) = {fs8.faz8_variants(H99_DATA_VERSION_SHA256)}; duyarlılık satırı = {len(fs8.faz8_sensitivity_lines())}; scores_json_is_pre_faz8 = {fs8.scores_json_is_pre_faz8()}; scores_post_d1_is_pre_faz8 = {fs8.scores_post_d1_is_pre_faz8()}")
EOF
echo "scores_oot.json'ı son yazan commit: $(git log -1 --format=%h -- scores/scores_oot.json); dosyadaki git_head: $(python3 -c "import json;print(json.load(open('scores/scores_oot.json'))['code']['git_head'][:7])"); borsai_source_sha256 (dosya): $(python3 -c "import json;print(json.load(open('scores/scores_oot.json'))['code']['borsai_source_sha256'][:12])")"
.venv/bin/python - <<'EOF'
import sys, json, subprocess; sys.path.insert(0, "tests")
import faz7_support as fs7
last = subprocess.run(["git", "log", "-1", "--format=%H", "--", "scores/scores_oot.json"], capture_output=True, text=True).stdout.strip()
d = json.load(open("scores/scores_oot.json"))
print(f"  borsai/ ağacı hash'i @{last[:7]}: {fs7.borsai_tree_sha256_at(last)[:12]}; dosyadakiyle eşit: {fs7.borsai_tree_sha256_at(last) == d['code']['borsai_source_sha256']}")
from borsai.provenance import code_version
cv = code_version()
print(f"  bugünkü borsai_source_sha256: {cv['borsai_source_sha256'][:12]} (dosyadakinden farklı: {cv['borsai_source_sha256'] != d['code']['borsai_source_sha256']}; N19 kuralı bu farkı kabul eder)")
EOF

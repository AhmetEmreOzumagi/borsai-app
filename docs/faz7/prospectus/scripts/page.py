"""Bir belge sayfasının normalize metnini basar. Kullanım: python3 page.py T SOURCE_ID SAYFA [SAYFA2 ...]
Sayfa numarası PDF dosyasındaki 1 tabanlı sıradır (basılı sayfa numarası değil)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tlib import doc_pages, docs, norm  # noqa: E402

t, sid = sys.argv[1], sys.argv[2]
ps = doc_pages(t, sid)
if ps is None:
    print("belge/metin yok. Belgeler:", [d[0] for d in docs(t)])
    sys.exit(1)
for a in sys.argv[3:]:
    n = int(a)
    p = next((x for x in ps if x["n"] == n), None)
    if not p:
        print(f"s.{n} yok (toplam {len(ps)})")
        continue
    print(f"=== {sid} s.{n}/{len(ps)} [{p['method']}]\n{norm(p['text'])}\n")

"""distribution_method değerlerini kanonik yazıma çeker (anlam değişmez; ajanın yazımı note'ta saklanır).
Kurallar:
  - 'kurumsala <kim> (takdiriyle|kararıyla) dağıtım'  -> 'kurumsala takdire bağlı dağıtım'
  - 'yüksek başvurulu yatırımcılara'                  -> 'yüksek başvuruluya'
Kullanım: python3 normalize.py [--dry]"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import T  # noqa: E402

RULES = [
    (re.compile(r"kurumsala [^;]*?(takdiriyle|kararıyla) dağıtım"), "kurumsala takdire bağlı dağıtım"),
    (re.compile(r"yüksek başvurulu yatırımcılara"), "yüksek başvuruluya"),
]


def main():
    dry = "--dry" in sys.argv
    n = 0
    for p in sorted((T / "decisions").glob("*.json")):
        d = json.loads(p.read_text())
        f = d["fields"]["distribution_method"]
        v = f.get("value")
        if not v:
            continue
        nv = v
        for rx, rep in RULES:
            nv = rx.sub(rep, nv)
        if nv != v:
            n += 1
            print(f"{p.stem}: {v!r} -> {nv!r}")
            if not dry:
                f["value"] = nv
                f["note"] = (f.get("note") or "") + f" [yazım normalize edildi; ajan değeri: '{v}']"
                p.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    print("değişen", n)


if __name__ == "__main__":
    main()

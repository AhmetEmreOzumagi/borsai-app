"""Yerel belge metninde arama (ağ yok). Kullanım:
  python3 qfind.py T 'regex' [bağlam=250]          -> bütün belgelerde eşleşmeler
  python3 qfind.py T 'regex' ctx SOURCE_ID          -> yalnız bir belgede
Çıktıdaki metin, denetçinin karşılaştırdığı normalize metindir (boşluklar tek boşluk): alıntıyı buradan kopyala.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tlib import docs, norm, pages_of  # noqa: E402


def main():
    t, rx = sys.argv[1], sys.argv[2]
    ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 250
    only = sys.argv[4] if len(sys.argv) > 4 else None
    r = re.compile(rx, re.I)
    n = 0
    for sid, path, rec, f in docs(t):
        if only and sid != only:
            continue
        ps = pages_of(f["sha256"])
        if ps is None:
            print(f"!! {sid}: metin yok")
            continue
        for p in ps:
            txt = norm(p["text"])
            last = -1
            for m in r.finditer(txt):
                if m.start() < last:
                    continue
                a, b = max(0, m.start() - ctx), min(len(txt), m.end() + ctx)
                last = b
                print(f"--- {sid} s.{p['n']} [{p['method']}] ({rec['role']}; {rec['published_at']})\n{txt[a:b]}\n")
                n += 1
                if n >= 60:
                    print("... (60 eşleşmede kesildi; regex'i daralt)")
                    return


if __name__ == "__main__":
    main()

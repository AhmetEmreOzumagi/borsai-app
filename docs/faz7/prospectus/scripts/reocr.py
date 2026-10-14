"""Okunamayan/bozuk bir sayfayı yerelde çok ölçekli OCR ile yeniden okur (ağ yok).
Kullanım: <codex python> reocr.py T SOURCE_ID SAYFA
Daha çok harf çıkarsa sayfa metni güncellenir, eski metin alt_text olarak kalır (eski alıntılar geçerli kalır)."""
import json
import sys
from pathlib import Path

import pypdfium2 as pdfium

sys.path.insert(0, str(Path(__file__).parent))
from pdftext import OUT, _ocr1, letters  # noqa: E402
from tlib import docs  # noqa: E402

t, sid, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
f = next(d for d in docs(t) if d[0] == sid)
path, fr = f[1], f[3]
jp = OUT / f"{fr['sha256']}.json"
d = json.loads(jp.read_text())
p = next(x for x in d["pages"] if x["n"] == n)
pdf = pdfium.PdfDocument(str(path))
best, bs = p["text"], None
for sc in (1.5, 2.5, 3.0, 4.0):
    o = _ocr1(pdf, n - 1, sc)
    if letters(o) > letters(best) + 50:
        best, bs = o, sc
if bs:
    if "alt_text" not in p:
        p["alt_text"], p["alt_method"] = p["text"], p["method"]
    p["text"], p["method"] = best, "OCR"
    jp.write_text(json.dumps(d, ensure_ascii=False))
    print(f"güncellendi (ölçek {bs}, {letters(best)} harf). python3 page.py {t} {sid} {n} ile oku.")
else:
    print("daha iyi OCR bulunamadı; sayfa olduğu gibi kaldı.")

"""Önbellekte düşük verimli (<400 harf) OCR sayfalarını çok ölçekli OCR ile yeniden okur; daha iyiyse değiştirir (eskisi alt_text)."""
import glob
import json
import sys
from pathlib import Path

import pypdfium2 as pdfium

sys.path.insert(0, str(Path(__file__).parent))
from pdftext import OUT, _ocr1, letters  # noqa: E402

n = 0
for f in glob.glob(str(OUT / "*.json")):
    d = json.load(open(f))
    todo = [p for p in d["pages"] if p["method"] == "OCR" and letters(p["text"]) < 400 and not p.get("ms_tried")]
    if not todo:
        continue
    pp_ = Path(d["path"]) if Path(d["path"]).is_absolute() else Path("/Users/ahmet/Desktop/BorsAi_codex/verified_faz7") / d["path"]
    pdf = pdfium.PdfDocument(str(pp_))
    ch = 0
    for p in todo:
        p["ms_tried"] = True
        ch += 0
        best = p["text"]
        for sc in (3.0, 1.5):
            o = _ocr1(pdf, p["n"] - 1, sc)
            if letters(o) > letters(best) + 50:
                best = o
        if best is not p["text"]:
            if "alt_text" not in p:
                p["alt_text"], p["alt_method"] = p["text"], "OCR"
            p["text"] = best
            n += 1; ch += 1
    if todo:
        Path(f).write_text(json.dumps(d, ensure_ascii=False))
        print(d["path"], ch, flush=True)
print("değişen sayfa", n)

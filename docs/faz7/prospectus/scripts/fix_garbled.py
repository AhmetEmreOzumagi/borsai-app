"""Önbellekteki metinlerde bozuk metin katmanlı sayfaları OCR'la yeniden okur (eski metin alt_text olarak kalır)."""
import glob
import json
import sys
from pathlib import Path

import pypdfium2 as pdfium

sys.path.insert(0, str(Path(__file__).parent))
from pdftext import OUT, garbled, letters, ocr_page, tr_ratio  # noqa: E402

n = 0
for f in glob.glob(str(OUT / "*.json")):
    d = json.load(open(f))
    todo = [p for p in d["pages"] if p["method"] == "TEXT" and garbled(p["text"])]
    if not todo:
        continue
    pp_ = Path(d["path"]) if Path(d["path"]).is_absolute() else Path("/Users/ahmet/Desktop/BorsAi_codex/verified_faz7") / d["path"]
    pdf = pdfium.PdfDocument(str(pp_))
    for p in todo:
        o = ocr_page(pdf, p["n"] - 1)
        if tr_ratio(o) > tr_ratio(p["text"]) and letters(o) > 0.5 * letters(p["text"]):
            p["alt_text"], p["alt_method"] = p["text"], "TEXT"
            p["text"], p["method"] = o, "OCR"
            n += 1
    Path(f).write_text(json.dumps(d, ensure_ascii=False))
    print(d["path"], len(todo), flush=True)
print("değişen sayfa", n)

"""PDF -> metin (sayfa başına: metin katmanı; yoksa Apple Vision OCR). Sonuç sha256 ile önbellekte.

Kullanım: <codex python> pdftext.py PDF [PDF ...]   (çıktı: cache/text/<sha>.json)
JSON: {"sha256", "pages": [{"n", "method": "TEXT"|"OCR", "text"}]}
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium

W = Path(__file__).resolve().parent
OUT = W / "cache" / "text"
OUT.mkdir(parents=True, exist_ok=True)
OCR = W / "ocr_vision"


def letters(s: str) -> int:
    return sum(ch.isalpha() for ch in s)


def ocr_page(pdf: pdfium.PdfDocument, i: int) -> str:
    page = pdf[i]
    img = page.render(scale=3.0).to_pil()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        img.save(tf.name)
        r = subprocess.run([str(OCR), tf.name], capture_output=True, text=True, timeout=300)
    Path(tf.name).unlink(missing_ok=True)
    return r.stdout


def extract(path: Path, force_ocr: bool = False) -> dict:
    b = path.read_bytes()
    sha = hashlib.sha256(b).hexdigest()
    out = OUT / f"{sha}{'_ocr' if force_ocr else ''}.json"
    if out.exists():
        return json.loads(out.read_text())
    pages = []
    pdf = pdfium.PdfDocument(str(path))
    try:
        with pdfplumber.open(str(path)) as pp:
            for i, pg in enumerate(pp.pages):
                try:
                    t = pg.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
                except Exception:
                    t = ""
                if force_ocr or letters(t) < 40:
                    o = ocr_page(pdf, i)
                    if letters(o) > letters(t):
                        pages.append({"n": i + 1, "method": "OCR", "text": o})
                        continue
                pages.append({"n": i + 1, "method": "TEXT", "text": t})
    except Exception as e:  # bozuk metin katmanı: tamamen OCR
        pages = [{"n": i + 1, "method": "OCR", "text": ocr_page(pdf, i)} for i in range(len(pdf))]
        pages.insert(0, {"n": 0, "method": "NOTE", "text": f"pdfplumber hata: {e}"})
    doc = {"sha256": sha, "path": str(path), "pages": pages}
    out.write_text(json.dumps(doc, ensure_ascii=False))
    return doc


if __name__ == "__main__":
    force = "--ocr" in sys.argv
    for a in sys.argv[1:]:
        if a == "--ocr":
            continue
        d = extract(Path(a), force)
        print(a, d["sha256"][:12], len(d["pages"]), sum(p["method"] == "OCR" for p in d["pages"]))

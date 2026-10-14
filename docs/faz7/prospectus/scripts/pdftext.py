"""PDF -> sayfa metni (metin katmanı; harf < 40 ya da bozuk kodlamalı sayfada Apple Vision OCR, tr-TR, doğru mod).

Sonuç sha256 ile önbellekte: cache/text/<sha>.json = {"sha256", "path", "pages": [{"n", "method": "TEXT"|"OCR", "text"}]}
Kullanım: <codex python> pdftext.py [-j N] PDF [PDF ...]
"""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium

W = Path(__file__).resolve().parent.parent
OUT = W / "cache" / "text"
OUT.mkdir(parents=True, exist_ok=True)
OCR = W / "scripts" / "ocr_vision"
TMP = W / "cache" / "tmp"
TMP.mkdir(parents=True, exist_ok=True)
FUNC = re.compile(r"(?<!\w)(ve|ile|bir|için|olarak|bu|veya|olan|tarafından|halka|pay)(?!\w)", re.I)


def letters(s: str) -> int:
    return sum(ch.isalpha() for ch in s)


TRCH = re.compile(r"[ışğİŞĞ]")


def tr_ratio(t: str) -> float:
    n = letters(t)
    return len(TRCH.findall(t)) / n if n else 0.0


def garbled(t: str) -> bool:
    """Bozuk/düşük kaliteli gömülü metin katmanı: işlev sözcüğü yok ya da Türkçe harf oranı çok düşük."""
    return letters(t) > 150 and (len(FUNC.findall(t)) == 0 or (letters(t) >= 200 and tr_ratio(t) < 0.005))


def ocr_page(pdf, i: int, scale: float = 2.0) -> str:
    """Vision bazen sayfa yönünü yanlış algılayıp yalnız damga okur: düşük verimde 3.0 ve 1.5 ölçekle yeniden dener."""
    best = _ocr1(pdf, i, scale)
    for sc in (3.0, 1.5):
        if letters(best) >= 400:
            break
        o = _ocr1(pdf, i, sc)
        if letters(o) > letters(best):
            best = o
    return best


def _ocr1(pdf, i: int, scale: float) -> str:
    img = pdf[i].render(scale=scale).to_pil()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir=TMP) as tf:
        img.save(tf.name)
        r = subprocess.run([str(OCR), tf.name], capture_output=True, text=True, timeout=300)
    Path(tf.name).unlink(missing_ok=True)
    return r.stdout


def extract(path: str) -> str:
    p = Path(path)
    b = p.read_bytes()
    sha = hashlib.sha256(b).hexdigest()
    out = OUT / f"{sha}.json"
    if out.exists():
        return f"{path} cached"
    pages = []
    pdf = pdfium.PdfDocument(str(p))
    try:
        with pdfplumber.open(str(p)) as pp:
            for i, pg in enumerate(pp.pages):
                try:
                    t = pg.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
                except Exception:
                    t = ""
                if letters(t) < 40 or garbled(t):
                    o = ocr_page(pdf, i)
                    if letters(o) > letters(t) or (garbled(t) and not garbled(o)) or (garbled(t) and tr_ratio(o) > tr_ratio(t)):
                        pg_ = {"n": i + 1, "method": "OCR", "text": o}
                        if letters(t) >= 40:
                            pg_["alt_text"] = t
                            pg_["alt_method"] = "TEXT"
                        pages.append(pg_)
                        continue
                pages.append({"n": i + 1, "method": "TEXT", "text": t})
    except Exception as e:  # bozuk metin katmanı: tamamen OCR
        pages = [{"n": i + 1, "method": "OCR", "text": ocr_page(pdf, i)} for i in range(len(pdf))]
        pages.insert(0, {"n": 0, "method": "NOTE", "text": f"pdfplumber hata: {e}"})
    doc = {"sha256": sha, "path": str(p), "pages": pages}
    out.write_text(json.dumps(doc, ensure_ascii=False))
    return f"{path} pages={len(pages)} ocr={sum(x['method'] == 'OCR' for x in pages)}"


if __name__ == "__main__":
    args = sys.argv[1:]
    j = 1
    if args and args[0] == "-j":
        j = int(args[1])
        args = args[2:]
    with ProcessPoolExecutor(max_workers=j) as ex:
        for r in ex.map(extract, args):
            print(r, flush=True)

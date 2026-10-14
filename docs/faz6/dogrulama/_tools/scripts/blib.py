"""Ortak yardımcılar: metin, sayı, listeleme ayrıştırma, Codex değerleri."""
import csv
import glob
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

W = Path(__file__).resolve().parent
REPO = Path("/Users/ahmet/Desktop/BorsAi")
CODEX = Path.home() / "Desktop/BorsAi_codex"

MEMBERS = [r for r in csv.DictReader(open(REPO / "docs/specs_faz6/ekler/evren_listesi.csv", encoding="utf-8")) if r["status"] == "MEMBER"]
EV = {r["ticker"]: r for r in MEMBERS}

_TEXT = None


def _text_index():
    global _TEXT
    if _TEXT is None:
        _TEXT = {}
        for f in glob.glob(str(W / "cache/text/*.json")):
            if f.endswith("_ocr.json"):
                continue
            _TEXT[Path(f).stem] = f
    return _TEXT


def sha_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pages(path):
    s = sha_file(path)
    f = _text_index().get(s) or (str(W / f"cache/text/{s}.json") if (W / f"cache/text/{s}.json").exists() else None)
    if not f:
        return None
    return json.loads(Path(f).read_text())["pages"]


def N(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def fulltext(path) -> str | None:
    ps = pages(path)
    return None if ps is None else N(" ".join(p["text"] for p in ps))


def methods(path):
    ps = pages(path)
    return sorted({p["method"] for p in ps}) if ps else []


def tr_num(s: str) -> str:
    """Belgedeki yazım -> değer: binlik nokta atılır, ondalık virgül noktaya."""
    s = s.strip()
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", s):
        return s.replace(".", "").replace(",", ".")
    if re.fullmatch(r"\d+,\d+", s):
        return s.replace(",", ".")
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", s):  # İngilizce binlik ayırıcı
        return s.replace(",", "")
    return s


def dec(s):
    try:
        return Decimal(tr_num(str(s)))
    except (InvalidOperation, ValueError):
        return None


def iso(dmy: str) -> str:
    d, m, y = re.split(r"[./]", dmy)
    return f"{y}-{int(m):02d}-{int(d):02d}"


def parse_listing(text: str) -> dict:
    t = N(text)
    out = {}
    pats = {
        "nominal": r"İşlem Görecek Payların Nominal Tutarı \(TL\) ([\d.,]+)",
        "baz": r"Baz Fiyat \(TL\) ([\d.,]+)",
        "pazar": r"İşlem Göreceği Pazar (.+?) Uygulanacak",
        "ftd": r"İşlem Görmeye Başlayacağı Tarih (\d{1,2}/\d{1,2}/\d{4})",
        "yontem": r"Halka Arz Yöntemi (.+?) Halka Arz Tarihi",
        "arz_tarihi": r"Halka Arz Tarihi (\S+(?: ?- ?\S+)?) Açıklamalar",
        "sermaye": r"sermayesini temsil eden ((?:[\d.,]+)(?: milyon)?) TL",
        "duzeltme": r"Yapılan Açıklama Düzeltme mi\? (\S+)",
    }
    for k, p in pats.items():
        m = re.search(p, t)
        if k == "sermaye" and not m:
            m = re.search(r"((?:[\d.,]+)(?: milyon)?) TL nominal değerli sermayesini temsil eden", t)
        out[k] = m.group(1) if m else None
        if m:
            out[k + "_quote"] = m.group(0)
    return out


def bb_dates(raw: str, ftd: str):
    """'29-30/01/2020', '30/11-01/12/2020', '29-30.06.2021', '14-15-16/04/2021', '30/11/2021-01/12/2021'."""
    b = raw.replace(".", "/").replace(" ", "")
    y = int(b[-4:])
    m = re.fullmatch(r"([\d-]+)/(\d{1,2})/(\d{4})", b)
    if m:
        days = [int(x) for x in m.group(1).split("-")]
        mo = int(m.group(2))
        return f"{y}-{mo:02d}-{days[0]:02d}", f"{y}-{mo:02d}-{days[-1]:02d}"
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?-(\d{1,2})/(\d{1,2})/(\d{4})", b)
    if m:
        y0 = int(m.group(3)) if m.group(3) else (y if int(m.group(2)) <= int(m.group(5)) else y - 1)
        return f"{y0}-{int(m.group(2)):02d}-{int(m.group(1)):02d}", f"{y}-{int(m.group(5)):02d}-{int(m.group(4)):02d}"
    raise ValueError(raw)


def codex_all():
    c = {}
    for b in ("B1", "B2", "B3", "B4"):
        d = json.load(open(CODEX / f"BORSAI_FAZ6_CODEX_INPUTS_{b}_20260924.json"))
        for ipo in d["ipos"]:
            ipo["_batch"] = b
            c[ipo["ticker"]] = ipo
    return c


def tick(t):
    return json.loads((W / "tick" / f"{t}.json").read_text())

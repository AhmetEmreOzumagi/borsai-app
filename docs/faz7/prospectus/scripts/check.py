"""decisions/<T>.json denetçisi. Kullanım: python3 check.py T [T ...]

Denetler: şema; kaynak bu tickerın indirilmiş belgelerinden biri ve yayın zamanı ilk işlem gününden önce;
her alıntı (normalize) belirtilen sayfanın metninde birebir; değer biçimi (H99); değerin alıntıda görünmesi;
MISSING'de neden + bakılan yerler; Codex'in OK verdiği her alan için codex_check kararı.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import FIELDS, T, before_listing, codex_all  # noqa: E402
from tlib import docs, match_page, norm, pages_of  # noqa: E402

import os
DEC = Path(os.environ.get("DEC_DIR", str(T / "decisions")))
CX = codex_all()
VERDICTS = ("FOUND_SAME", "FOUND_DIFFERENT", "NOT_FOUND_IN_DOCS")
BOOL = ("TRUE", "FALSE")


def fold(s):
    return norm(s).replace("İ", "i").replace("I", "ı").lower()


G = r"g[üuiıïl1]{1,3}n"   # OCR: gün / güin / giin / güln
Y = r"y[ıi1l]l"          # OCR: yıl / yil / y1l


def days_rx(n: int):
    """n gün için belgede görülebilecek süre ifadeleri."""
    words = {1: "bir", 2: "iki", 3: "üç", 4: "dört", 5: "beş", 6: "altı", 9: "dokuz", 12: "on iki", 15: "on beş",
             18: "on sekiz", 24: "yirmi dört", 30: "otuz", 45: "kırk beş", 60: "altmış", 90: "doksan", 180: "yüz seksen",
             360: "üç yüz altmış", 365: "üç yüz altmış beş", 730: "yedi yüz otuz"}
    alts = [rf"{n}\s*(\([^)]*\))?\s*(takvim\s*|iş\s*)?" + G,
            rf"(?<!\d){n}\s*\({words.get(n, '@@')}\)\s*g"]   # birim damga altında: "30 (otuz) g…"
    if n in words:
        alts.append(rf"{words[n]}\s*(\([^)]*\))?\s*" + G)
    if n % 365 == 0:
        y = n // 365
        alts += [rf"(?<!\d){y}\s*(\([^)]*\))?\s*" + Y] + ([rf"{words[y]}\s*(\([^)]*\))?\s*" + Y] if y in words else [])
        alts += [rf"(?<!\d){12 * y}\s*(\([^)]*\))?\s*ay\b"] + ([rf"{words[12 * y]}\s*(\([^)]*\))?\s*ay\b"] if 12 * y in words else [])
    if n % 30 == 0 and n % 365:
        mo = n // 30
        alts += [rf"(?<!\d){mo}\s*(\([^)]*\))?\s*ay\b"] + ([rf"{words[mo]}\s*(\([^)]*\))?\s*ay\b"] if mo in words else [])
    # OCR'da rakam kaybı: "(bir) yıl", "(altı) ay", "(otuz) gün"
    if n in words:
        alts.append(rf"\({words[n]}\)\s*" + G)
    if n % 365 == 0 and n // 365 in words:
        alts.append(rf"\({words[n // 365]}\)\s*" + Y)
    if n % 30 == 0 and n % 365 and n // 30 in words:
        alts.append(rf"\({words[n // 30]}\)\s*ay\b")
    return re.compile("|".join(alts))


NEG = re.compile(r"yokt[uü]r|bulunmamakta|planlanmamakta|planlanmamış|öngörülmemekte|yapılmayacak|gerçekleştirilmeyecek|"
                 r"verilmemiştir|mevcut değil|söz konusu değil|yer almamakta|olmayacak")


def all_quotes(f):
    out = []
    if f.get("quote"):
        out.append((f.get("source_id"), f.get("page"), f["quote"]))
    for q in f.get("extra_quotes") or []:
        out.append((q.get("source_id"), q.get("page"), q.get("quote")))
    return out


def check(t):
    errs = []
    p = DEC / f"{t}.json"
    if not p.exists():
        return ["karar dosyası yok"]
    try:
        d = json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        return [f"JSON okunamadı: {e}"]
    dm = {sid: (rec, f) for sid, path, rec, f in docs(t)}
    fields = d.get("fields") or {}
    for k in FIELDS:
        if k not in fields:
            errs.append(f"{k}: alan yok")
    for k, f in fields.items():
        if k not in FIELDS:
            errs.append(f"{k}: bilinmeyen alan")
            continue
        v = f.get("value")
        if v is None:
            if not f.get("missing_reason"):
                errs.append(f"{k}: value null ama missing_reason yok")
            if not f.get("looked_at"):
                errs.append(f"{k}: value null ama looked_at (bakılan belgeler) yok")
            for sid in f.get("looked_at") or []:
                if sid not in dm and not str(sid).startswith("KAP_"):
                    errs.append(f"{k}: looked_at içinde bilinmeyen kimlik {sid}")
            continue
        if not isinstance(v, str):
            errs.append(f"{k}: value metin olmalı")
            continue
        qs = all_quotes(f)
        if not qs:
            errs.append(f"{k}: alıntı yok")
        for sid, pg, q in qs:
            if sid not in dm:
                errs.append(f"{k}: kaynak {sid} bu tickerın belgelerinde yok")
                continue
            rec, fr = dm[sid]
            if not rec.get("published_at") or not before_listing(rec["published_at"], t):
                errs.append(f"{k}: {sid} yayın zamanı {rec.get('published_at')} ilk işlem gününden önce değil")
            ps = pages_of(fr["sha256"])
            if not ps:
                errs.append(f"{k}: {sid} metni yok")
                continue
            page = next((x for x in ps if x["n"] == pg), None)
            if page is None:
                errs.append(f"{k}: {sid} s.{pg} yok")
                continue
            if not q or len(norm(q)) < 12:
                errs.append(f"{k}: alıntı çok kısa")
            elif match_page(page, q) is None:
                errs.append(f"{k}: alıntı {sid} s.{pg} metninde birebir yok: {q[:80]!r}")
        allq = fold(" ".join(q or "" for _, _, q in qs))
        if f.get("verifier_visual_check"):
            # doğrulayıcı sayfa görüntüsünü gözle kontrol etti (OCR ilgili sözcüğü kaçırdı); değer-alıntı eşleşmesi atlanır
            continue
        if k in ("price_stability_planned", "participation_index_eligible"):
            if v not in BOOL:
                errs.append(f"{k}: değer TRUE/FALSE olmalı")
        if k == "price_stability_planned":
            if "istikr" not in allq:
                errs.append(f"{k}: alıntıda 'istikrar' yok")
            if v == "FALSE" and not NEG.search(allq):
                errs.append(f"{k}: FALSE ama alıntıda olumsuzluk ifadesi yok")
        if k in ("price_stability_days", "issuer_lockup_days", "shareholder_lockup_days"):
            if not re.fullmatch(r"\d+", v):
                errs.append(f"{k}: gün sayısı tam sayı olmalı")
                continue
            n = int(v)
            if n == 0:
                if k == "price_stability_days":
                    pl = fields.get("price_stability_planned", {}).get("value")
                    if pl != "FALSE":
                        errs.append(f"{k}: 0 yalnız price_stability_planned=FALSE iken")
                elif not NEG.search(allq):
                    errs.append(f"{k}: 0 ama alıntıda 'yoktur' vb. yok")
            elif not days_rx(n).search(allq):
                errs.append(f"{k}: {n} gün alıntıda süre ifadesi olarak görünmüyor")
        if k == "distribution_method":
            if "eşit" in v.lower() and "eşit" not in allq:
                errs.append(f"{k}: değerde 'eşit' var, alıntıda yok")
            if "oransal" in v.lower() and "oransal" not in allq:
                errs.append(f"{k}: değerde 'oransal' var, alıntıda yok")
            if "tahsisat" in v.lower() and "tahsis" not in allq:
                errs.append(f"{k}: değerde 'tahsisat' var, alıntıda yok")
        if k == "participation_index_eligible" and not re.search(r"katılım|faizsiz|islam|icazet|helal", allq):
            errs.append(f"{k}: alıntıda katılım/faizsiz ifadesi yok")
        if k == "shareholder_lockup_days" and not isinstance(f.get("components"), list):
            errs.append(f"{k}: components listesi yok")
    cx = CX[t]["fields"]
    cc = d.get("codex_check") or {}
    for k in FIELDS:
        if cx.get(k, {}).get("status") == "OK":
            c = cc.get(k)
            if not c or c.get("verdict") not in VERDICTS:
                errs.append(f"codex_check.{k}: Codex OK değeri için karar (FOUND_SAME/FOUND_DIFFERENT/NOT_FOUND_IN_DOCS) yok")
            elif c["verdict"] == "FOUND_SAME" and fields.get(k, {}).get("value") is None:
                errs.append(f"codex_check.{k}: FOUND_SAME ama value null")
    return errs


if __name__ == "__main__":
    bad = 0
    for t in sys.argv[1:]:
        e = check(t)
        print(f"{t}: {'OK' if not e else 'HATA'}")
        for x in e:
            print("   -", x)
        bad += bool(e)
    sys.exit(1 if bad else 0)

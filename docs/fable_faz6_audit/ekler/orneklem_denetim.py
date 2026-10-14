#!/usr/bin/env python3
"""Girdi örneklem denetimi (adım 2): tohum 20260925, yıl tabakalı 15 üye (2020: 2, 2021: 5, 2022: 4, 2023: 4);
seçim: random.Random(20260925); yıllar artan sırada; her yılda sorted(ticker) listesinden rng.sample(k).
Her dolu girdi alanı için: (1) kaynak dosyanın sha256'sı alanın `source_sha256`'sı ve MANIFEST ile eşit; (2) yayın zamanı
(İstanbul tarihi) < ilk işlem günü; (3) alıntı (`quote`) pinli belgenin metninde (macOS PDFKit; metin katmanı yoksa Apple Vision
OCR) EXACT / NOSPACE (boşluksuz) / TOKENS (sayı ve ≥4 harfli sözcüklerin ≥ %80'i) düzeyinde bulunuyor; (4) değer alıntıda
(Türkçe sayı yazımı, tarih biçimleri); türetilmiş f3'te pay/payda alıntıları ve ROUND_HALF_UP 10 ondalık yeniden hesap;
taşınan alanlarda (DATA_NOTES §2) üç koşulun alıntıları; PB alanlarında özdeşlikler (post = pre + artırım; taban = artırım +
ortak satışı; azami = taban + ek satış). `borsai` import edilmez."""
import csv
import hashlib
import json
import random
import re
import subprocess
import sys
import unicodedata
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, getcontext
from pathlib import Path

getcontext().prec = 60
ROOT = Path(sys.argv[1]).resolve()
TOOLS = Path(sys.argv[2]).resolve()             # pdftext, pdfocr
CACHE = Path(sys.argv[3]).resolve()             # metin önbelleği
CACHE.mkdir(parents=True, exist_ok=True)
SEED = 20260925
K = {"2020": 2, "2021": 5, "2022": 4, "2023": 4}
MONTHS = "Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık".split()
CATEGORICAL = {"total_demand_filter_status"}
DATE_FIELDS = {"first_trading_date", "bookbuilding_start", "bookbuilding_end"}
PB = ("ipo_price_try", "planned_pre_ipo_capital", "planned_post_ipo_capital", "planned_capital_increase_shares",
      "planned_existing_share_sale", "planned_base_offer_shares", "planned_additional_sale_ceiling", "planned_max_offer_shares")

members = [r for r in csv.DictReader((ROOT / "registry/oot/cohort_pre_h99.csv").open(encoding="utf-8", newline=""))
           if r["status"] == "MEMBER"]
by_year = {}
for r in members:
    by_year.setdefault(r["year"], []).append(r["ticker"])
rng = random.Random(SEED)
SAMPLE = []
for y in sorted(K):
    SAMPLE += sorted(rng.sample(sorted(by_year[y]), K[y]))
print("örneklem (tohum 20260925):", SAMPLE)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def text_of(path, layer):
    key = CACHE / f"{sha(path)}.{'ocr' if 'OCR' in layer else 'txt'}"
    if key.exists():
        return key.read_text(encoding="utf-8")
    tool = TOOLS / ("pdfocr" if "OCR" in layer else "pdftext")
    out = subprocess.run([str(tool), str(path)] + (["3"] if "OCR" in layer else []), capture_output=True, text=True, check=True).stdout
    if "OCR" not in layer and len(re.sub(r"\s|=== PAGE \d+ ===", "", out)) < 40 * out.count("=== PAGE"):
        out = subprocess.run([str(TOOLS / "pdfocr"), str(path), "3"], capture_output=True, text=True, check=True).stdout
    key.write_text(out, encoding="utf-8")
    return out


def norm(s):
    s = unicodedata.normalize("NFC", s).replace("’", "'").replace("–", "-").replace("—", "-").replace("ﬁ", "fi")
    return re.sub(r"\s+", " ", s).strip()


def nospace(s):
    return re.sub(r"[\s\.\,;:'\"()\-]", "", norm(s)).lower().replace("İ", "i").replace("ı", "i")


def find_quote(quote, text):
    q, t = norm(quote), norm(text)
    if q in t:
        return "EXACT"
    if nospace(q) in nospace(t):
        return "NOSPACE"
    toks = re.findall(r"\d[\d\.,]*\d|\d|[A-Za-zÇĞİÖŞÜçğıöşü]{4,}", q)
    ts = nospace(t)
    hit = [tok for tok in toks if nospace(tok) in ts]
    frac = len(hit) / max(1, len(toks))
    return f"TOKENS {len(hit)}/{len(toks)}" if frac >= 0.8 else f"FAIL {len(hit)}/{len(toks)}"


def num_variants(v):
    d = Decimal(str(v))
    out = set()
    if d == d.to_integral_value():
        n = int(d)
        out |= {str(n), f"{n:,}".replace(",", "."), f"{n:,}", f"{n:,}".replace(",", ".") + ",00", f"{n:,}".replace(",", ".") + ".00"}
    s = format(d.normalize(), "f")
    if "." in s:
        ip, fp = s.split(".")
        for k in range(len(fp), 5):
            f = fp + "0" * (k - len(fp))
            ipd = f"{int(ip):,}".replace(",", ".") if len(ip) > 3 else ip
            out |= {f"{ip}.{f}", f"{ip},{f}", f"{ipd},{f}", f"{ipd}.{f}"}
    else:
        out |= {s + ",0", s + ",00", s + ".0", s + ".00"}
    return out


def value_in_quote(field, value, quote):
    q = norm(quote)
    if field in DATE_FIELDS:
        y, m, d = value.split("-")
        forms = [f"{d}/{m}/{y}", f"{d}.{m}.{y}", f"{int(d)}/{int(m)}/{y}", f"{d}-{m}-{y}", f"{int(d)} {MONTHS[int(m)-1]} {y}",
                 f"{d}/{m}/{y[2:]}"]
        if any(f in q for f in forms):
            return True
        return bool(re.search(rf"(^|[^\d]){int(d):02d}([^\d]|$)", q) and (f"/{m}/{y}" in q or f".{m}.{y}" in q or f"{MONTHS[int(m)-1]} {y}" in q))
    if field in CATEGORICAL:
        return True
    try:
        variants = num_variants(value)
    except Exception:                       # sayı değil (ör. fiyat aralığı "15,50-17"): metin olarak, virgül/nokta eşdeğer
        v = norm(str(value))
        variants = {v, v.replace(".", ","), v.replace(",", "."), re.sub(r"\s*-\s*", "-", v), re.sub(r"\s*-\s*", " - ", v)}
        return any(x in q or x.replace(".", ",") in q for x in variants)
    return any(re.search(rf"(^|[^\d]){re.escape(v)}([^\d]|$)", q) for v in variants)


def istanbul_date(ts):
    dt = datetime.fromisoformat(ts)
    assert dt.utcoffset() is not None
    return (dt - dt.utcoffset() + __import__("datetime").timedelta(hours=3)).strftime("%Y-%m-%d")


rows_out = []
summary = []
for t in SAMPLE:
    doc = json.load((ROOT / "registry/oot/inputs" / f"{t}.json").open(encoding="utf-8"))
    man = {d["source_id"]: d for d in json.load((ROOT / "registry/oot/source_docs" / t / "MANIFEST.json").open(encoding="utf-8"))["documents"]}
    ftd = doc["fields"]["first_trading_date"]["value"]
    f = doc["fields"]
    counts = {"dolu": 0, "boş": 0, "sha_ok": 0, "pit_ok": 0, "quote_exact": 0, "quote_loose": 0, "quote_fail": 0, "quote_yok": 0,
              "value_ok": 0, "value_fail": 0, "carry_ok": 0, "carry_fail": 0, "derived_ok": 0, "derived_fail": 0}
    notes = []
    for name, fld in f.items():
        v = fld.get("value")
        if v is None:
            counts["boş"] += 1
            notes.append(f"  {name}: BOŞ ({fld.get('missing_reason', '')[:80]})")
            continue
        counts["dolu"] += 1
        src = fld["source_id"]
        p = ROOT / fld["source_path"]
        m = man[src]
        ok_sha = sha(p) == fld["source_sha256"] == m["sha256"]
        counts["sha_ok"] += ok_sha
        pub = istanbul_date(fld["source_published_at"])
        ok_pit = pub < ftd and fld["source_published_at"] == m["published_at"]
        counts["pit_ok"] += ok_pit
        text = text_of(p, m["text_layer"])
        line = f"  {name:32s} = {str(v):>14s} | {src:22s} | sha {'OK' if ok_sha else 'FAIL'} | yayın {pub} {'<' if ok_pit else '!<'} {ftd}"
        quote = fld.get("quote")
        if quote:
            fq = find_quote(quote, text)
            if fq == "EXACT":
                counts["quote_exact"] += 1
            elif fq.startswith("FAIL"):
                counts["quote_fail"] += 1
            else:
                counts["quote_loose"] += 1
            vq = value_in_quote(name, v, quote)
            how = "alıntıda"
            if not vq and str(v) == "0" and (" - " in quote or fld.get("zero_from_statement") or "'-'" in str(fld.get("note", ""))
                                             or "'-'" in str(fld.get("formula", "")) or "'-'" in str(fld.get("locator", ""))):
                vq, how = True, "0 ← '-' hücresi/beyan"           # SPK tablosunda '-' ya da 'tamamı satıldı' beyanı: yapısal sıfır
            elif not vq and fld.get("derived") and fld.get("formula") and name in PB:
                try:
                    if name == "planned_base_offer_shares":
                        okd = Decimal(v) == Decimal(f["planned_capital_increase_shares"]["value"]) + Decimal(f["planned_existing_share_sale"]["value"])
                    elif name == "planned_max_offer_shares":
                        okd = Decimal(v) == Decimal(f["planned_base_offer_shares"]["value"]) + Decimal(f["planned_additional_sale_ceiling"]["value"])
                    elif name == "planned_post_ipo_capital":
                        okd = Decimal(v) == Decimal(f["planned_pre_ipo_capital"]["value"]) + Decimal(f["planned_capital_increase_shares"]["value"])
                    else:
                        okd = False
                except Exception:
                    okd = False
                if okd:
                    vq, how = True, "türetilmiş toplam (özdeşlik OK)"
                    counts["derived_ok"] += 1
                else:
                    counts["derived_fail"] += 1
            counts["value_ok" if vq else "value_fail"] += 1
            line += f" | alıntı {fq} | değer {how if vq else 'ALINTIDA YOK'}"
        else:
            counts["quote_yok"] += 1
            line += " | alıntı yok"
            if name in CATEGORICAL and v == "NOT_SPECIFIED":
                line += f" | 'filtre' belgede {'YOK (uyumlu)' if 'filtre' not in text.lower() else 'VAR (bak)'}"
            elif fld.get("derived") and fld.get("numerator_quote"):
                pass
        if fld.get("derived") and fld.get("numerator") is not None:
            nq, dq = find_quote(fld["numerator_quote"], text), find_quote(fld["denominator_quote"], text)
            nv = value_in_quote("x", fld["numerator"], fld["numerator_quote"]) and value_in_quote("x", fld["denominator"], fld["denominator_quote"])
            calc = (Decimal(fld["numerator"]) / Decimal(fld["denominator"])).quantize(Decimal("1e-10"), ROUND_HALF_UP)
            ok_d = not nq.startswith("FAIL") and not dq.startswith("FAIL") and nv and calc == Decimal(v)
            counts["derived_ok" if ok_d else "derived_fail"] += 1
            line += f" | türetilmiş: pay/payda alıntı {nq}/{dq}, sayılar {'alıntıda' if nv else 'YOK'}, {fld['numerator']}/{fld['denominator']} = {calc} {'==' if calc == Decimal(v) else '!='} {v}"
        elif fld.get("derived") and name in PB:
            pass   # özdeşlik denetimi aşağıda
        if fld.get("carry_rule"):
            cc = fld["carry_conditions"]
            a = cc.get("a_full_sale") or {}
            a_src = man.get(a.get("source_id"))
            a_ok = bool(a_src) and not find_quote(a["quote"], text_of(ROOT / "registry/oot/source_docs" / t / a_src["file"], a_src["text_layer"])).startswith("FAIL")
            b = cc.get("b_shares_offered_equals_planned_base", "")
            b_ok = True
            mm = re.match(r"\s*(\d+)\s*=\s*(\d+)\s*\+\s*(\d+)", str(b))
            if mm:
                b_ok = int(mm.group(1)) == int(mm.group(2)) + int(mm.group(3)) and int(mm.group(1)) == int(f["shares_offered"]["value"])
            ok_c = a_ok and b_ok
            counts["carry_ok" if ok_c else "carry_fail"] += 1
            line += f" | taşıma {fld['carry_rule']}: (a) {'OK' if a_ok else 'FAIL'} (b) {'OK' if b_ok else 'FAIL'} (c) {str(cc.get('c_no_additional_sale', cc.get('c_additional_sale_used', '')))[:50]}"
        notes.append(line)
    # PB özdeşlikleri ve V1.5 tutarlılığı
    try:
        pv = {k: Decimal(f[k]["value"]) for k in PB[1:]}
        ida = pv["planned_post_ipo_capital"] == pv["planned_pre_ipo_capital"] + pv["planned_capital_increase_shares"]
        idb = pv["planned_base_offer_shares"] == pv["planned_capital_increase_shares"] + pv["planned_existing_share_sale"]
        idc = pv["planned_max_offer_shares"] == pv["planned_base_offer_shares"] + pv["planned_additional_sale_ceiling"]
        notes.append(f"  PB özdeşlikleri: A {'OK' if ida else 'FAIL'} B {'OK' if idb else 'FAIL'} C {'OK' if idc else 'FAIL'}")
    except Exception as exc:
        notes.append(f"  PB özdeşlikleri: hesaplanamadı ({type(exc).__name__}: {str(exc)[:60]})")
    try:
        so = Decimal(f["shares_offered"]["value"])
        parts = [f[k]["value"] for k in ("capital_increase_shares", "existing_share_sale_shares", "additional_sale_shares")]
        if all(x is not None for x in parts):
            tot = sum(Decimal(x) for x in parts)
            notes.append(f"  satılan pay = artırım + ortak satışı + ek satış: {so} {'==' if tot == so else '!='} {tot}")
    except Exception as exc:
        notes.append(f"  ayrım toplamı: {exc}")
    summary.append((t, ftd, counts))
    rows_out.append(f"\n## {t} (ilk işlem {ftd}; {doc['sale_method']}, {doc['market']})\n" + "\n".join(notes))

print("\n| ticker | ilk işlem | dolu | boş | sha OK | yayın<ilk işlem | alıntı EXACT | alıntı gevşek | alıntı FAIL | alıntısız | değer alıntıda | değer YOK | taşıma OK/FAIL | türetilmiş OK/FAIL |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
tot = {}
for t, ftd, c in summary:
    for k, v in c.items():
        tot[k] = tot.get(k, 0) + v
    print(f"| {t} | {ftd} | {c['dolu']} | {c['boş']} | {c['sha_ok']} | {c['pit_ok']} | {c['quote_exact']} | {c['quote_loose']} | {c['quote_fail']} | {c['quote_yok']} | {c['value_ok']} | {c['value_fail']} | {c['carry_ok']}/{c['carry_fail']} | {c['derived_ok']}/{c['derived_fail']} |")
print(f"| **toplam** | | {tot['dolu']} | {tot['boş']} | {tot['sha_ok']} | {tot['pit_ok']} | {tot['quote_exact']} | {tot['quote_loose']} | {tot['quote_fail']} | {tot['quote_yok']} | {tot['value_ok']} | {tot['value_fail']} | {tot['carry_ok']}/{tot['carry_fail']} | {tot['derived_ok']}/{tot['derived_fail']} |")
print("\n".join(rows_out))
print("\nborsai sys.modules içinde mi:", "borsai" in sys.modules)

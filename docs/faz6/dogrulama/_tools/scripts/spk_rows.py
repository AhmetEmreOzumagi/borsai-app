"""SPK A.1 tablosu: sütunları sözcük x-koordinatlarıyla ayrıştırır (onay tarihindeki bülten).

Çıktı spk_rows.json: ticker -> {no, date, file, page, cols{...}, name_text, lines[...], footnotes}
"""
import json
import re
from pathlib import Path

import pdfplumber

W = Path(__file__).resolve().parent
match = json.loads((W / "spk_match.json").read_text())
a1 = json.loads((W / "spk_a1.json").read_text())
by_date = {}
for f, v in a1.items():
    if v.get("a1"):
        by_date.setdefault(v["date"], []).append((f, v))

NUM = re.compile(r"^(?:–|—|\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?|-|\d+,\d+-\d+,\d+|\d+(?:,\d+)?\s*-\s*\d+(?:,\d+)?)$")
COLS = ["mevcut_sermaye", "yeni_sermaye", "bedelli", "bedelsiz", "mevcut_pay_satisi", "ek_pay_satisi", "satis_fiyati"]


def norm(s):
    return re.sub(r"\s+", " ", s.replace("İ", "i").replace("I", "ı").lower())


def header_x(words, top0):
    """Başlık sözcüklerinin x-merkezleri. Sıra: Mevcut Sermaye, Yeni Sermaye, Bedelli, Bedelsiz, Mevcut Pay Satışı, Ek Pay Satışı, Satış Fiyatı."""
    hw = [w for w in words if top0 - 5 <= w["top"] <= top0 + 60]
    xs = {}
    bed = [w for w in hw if w["text"].startswith("Bedelli")]
    bsz = [w for w in hw if w["text"].startswith("Bedelsiz")]
    yeni = [w for w in hw if w["text"] == "Yeni"]
    ek = [w for w in hw if w["text"] == "Ek"]
    mev = sorted([w for w in hw if w["text"] == "Mevcut"], key=lambda w: w["x0"])
    fiy = [w for w in hw if w["text"].startswith("Fiyat")] or [w for w in hw if w["text"] == "Satış"]
    c = lambda w: (w["x0"] + w["x1"]) / 2
    if bed: xs["bedelli"] = c(bed[0])
    if bsz: xs["bedelsiz"] = c(bsz[0])
    if yeni: xs["yeni_sermaye"] = c(yeni[0])
    if ek: xs["ek_pay_satisi"] = c(ek[0]) + 15
    if len(mev) >= 2:
        xs["mevcut_sermaye"] = c(mev[0])
        xs["mevcut_pay_satisi"] = c(mev[-1])
    if fiy:
        xs["satis_fiyati"] = c(max(fiy, key=lambda w: w["x0"]))
    return xs


def main():
    out = {}
    for t, m in match.items():
        bdate = m["approval"] or (m["hits"][-1][0] if len(m["hits"]) == 1 else None)
        cands = by_date.get(bdate, [])
        if not cands:
            out[t] = {"error": "onay tarihli bülten yok"}
            continue
        f, v = cands[0]
        with pdfplumber.open(f) as pp:
            found = None
            for pi, pg in enumerate(pp.pages[:10]):
                txt = pg.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
                if "İlk Halka Arz" in txt:
                    found = (pi, pg, txt)
                    break
            if not found:
                out[t] = {"error": "A.1 sayfası yok"}
                continue
            pi, pg, txt = found
            words = pg.extract_words(x_tolerance=1.5, y_tolerance=3, keep_blank_chars=False)
            htop = min(w["top"] for w in words if w["text"] in ("Mevcut",) and w["top"] > 0)
            xs = header_x(words, htop)
            first_num_x = min(xs.values()) - 45 if xs else 200
            # isim sözcükleri (sol sütun) ve satırlar
            body = [w for w in words if w["top"] > htop + 20]
            # tablo sonu: ilk dipnot satırı "(1)" ile başlayan ve sol kenarda olan ya da "1)"
            end_top = None
            for w in sorted(body, key=lambda w: (w["top"], w["x0"])):
                if w["x0"] < 80 and re.match(r"^\(?1\)$", w["text"]):
                    end_top = w["top"]
                    break
            if end_top is None:
                end_top = 10_000
            tb = [w for w in body if w["top"] < end_top - 2]
            name_w = [w for w in tb if w["x1"] < first_num_x + 10 and not NUM.match(w["text"]) and not re.match(r"^\(\d+\)$", w["text"])]
            # isim satırlarını grupla: art arda satırlar; bir şirket unvanı "A.Ş."/"AŞ" ile biter
            lines = {}
            for w in sorted(name_w, key=lambda w: (round(w["top"]), w["x0"])):
                key = round(w["top"] / 3)
                lines.setdefault(key, []).append(w)
            name_lines = [(min(x["top"] for x in ws), max(x["bottom"] for x in ws), " ".join(x["text"] for x in ws)) for _, ws in sorted(lines.items())]
            companies, cur = [], []
            for ln in name_lines:
                cur.append(ln)
                if re.search(r"(A\.?Ş\.?|AŞ)\s*(\(\d+\))*\s*$", ln[2]) or re.search(r"A\.Ş\.", ln[2]):
                    companies.append(cur)
                    cur = []
            if cur:
                companies.append(cur)
            comp = [{"name": " ".join(l[2] for l in c), "top": c[0][0], "bottom": c[-1][1]} for c in companies]
            key = m["key"]
            k2 = norm(" ".join(m["company"].split()[:1]))
            idx = None
            for i, c in enumerate(comp):
                if key in norm(c["name"]) or norm(c["name"]).startswith(k2):
                    idx = i
                    break
            if idx is None:
                out[t] = {"error": "şirket satırı bulunamadı", "companies": [c["name"] for c in comp], "no": v["no"]}
                continue
            mids = [(c["top"] + c["bottom"]) / 2 for c in comp]
            nums = [w for w in tb if w["x0"] >= first_num_x - 10 and (NUM.match(w["text"]) or re.match(r"^\(\d+\)$", w["text"]))]
            mine = [w for w in nums if min(range(len(mids)), key=lambda i: abs((w["top"] + w["bottom"]) / 2 - mids[i])) == idx]
            cols = {}
            notes = {}
            for w in sorted(mine, key=lambda w: (w["top"], w["x0"])):
                cx = (w["x0"] + w["x1"]) / 2
                col = min(xs, key=lambda k: abs(xs[k] - cx))
                if re.match(r"^\(\d+\)$", w["text"]):
                    notes.setdefault(col, []).append(w["text"])
                    continue
                cols.setdefault(col, []).append(w["text"])
            vals = [w for w in mine if not re.match(r"^\(\d+\)$", w["text"])]
            vals.sort(key=lambda w: (w["x0"] + w["x1"]) / 2)
            merged = []
            for w in vals:
                if merged and (w["text"] in ("–", "—", "-") and merged[-1]["kind"] == "num" and re.match(r"^\d+,\d+$", merged[-1]["text"]) and abs(w["top"] - merged[-1]["top"]) < 3 and w["x0"] - merged[-1]["x1"] < 8):
                    merged[-1] = {**merged[-1], "text": merged[-1]["text"] + "-", "kind": "open"}
                    continue
                if merged and merged[-1]["kind"] == "open":
                    merged[-1] = {**merged[-1], "text": merged[-1]["text"] + w["text"], "kind": "num"}
                    continue
                merged.append({"text": w["text"], "top": w["top"], "x1": w["x1"], "kind": "num" if w["text"] not in ("-", "–", "—") else "dash"})
            ordered = [x["text"] for x in merged]
            cols_order = dict(zip(COLS, ordered)) if len(ordered) == 7 else None
            # satır metinleri (alıntı için): şirketin bandındaki extract_text satırları
            lo = min([comp[idx]["top"]] + [w["top"] for w in mine]) - 1
            hi = max([comp[idx]["bottom"]] + [w["bottom"] for w in mine]) + 1
            crop = pg.crop((0, lo, pg.width, hi))
            row_text = crop.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
            foot = txt[txt.find("\n(1)") if "\n(1)" in txt else txt.find("\n1)"):]
            out[t] = {"no": v["no"], "date": v["date"], "file": f, "url": v["url"], "sha256": v["sha256"], "page": pi + 1,
                      "name": comp[idx]["name"], "cols": cols, "ordered": ordered, "cols_order": cols_order, "notes": notes, "row_text": row_text,
                      "xs": xs, "footnotes": foot[:4000]}
    (W / "spk_rows.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(sum(1 for v in out.values() if "cols" in v), [(t, v["error"]) for t, v in out.items() if "error" in v])


main()

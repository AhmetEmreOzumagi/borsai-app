"""Ticker dosyası: belgeler, Codex değerleri, alan başına aday pasajlar. Kullanım: python3 dossier.py T [T ...]"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import EV, FIELDS, T, codex_all  # noqa: E402
from tlib import docs, norm, pages_of  # noqa: E402

OUT = T / "dossier"
OUT.mkdir(exist_ok=True)
CX = codex_all()

PAT = {
    "distribution_method": (r"(?<!kar )(?<!kâr )(?<!payı )dağıtım esas|(?<!kar )dağıtım yöntem|eşit dağıtım|oransal dağıtım|eşit olarak dağıt|oransal olarak dağıt|"
                            r"eşit esas|tahsisat ve dağıtım yapılmayaca|yatırımcı grubuna tahsisat|tahsis ve dağıtım", 7),
    "price_stability": (r"fiyat istikrar\w* işlem\w* planlan|planlanıp planlanmadığı|fiyat istikrar\w*[^.]{0,160}\d+\s*(\([^)]*\)\s*)?gün|"
                        r"istikrar\w*[^.]{0,80}zaman aralığı", 6),
    "lockup": (r"dolaşımdaki pay miktarının artırılmaması|ihraççı tarafından verilen taahhüt|ortaklar tarafından verilen taahhüt|"
               r"mevzuatı kapsamında verilen taahhüt|satmama taahh|satmayacakların|satmayacağın|satmamayı|lock[- ]?up", 8),
    "sector": (r"ana faaliyet (konusu|alan)|esas faaliyet|faaliyet konusu[^.]{0,40}(olup|dır|dir|oluşturmaktadır)|"
               r"faaliyet göstermektedir|sektöründe faaliyet", 6),
    "participation_index_eligible": (r"katılım (tüm )?endeks|katılım\s*\S*\s*endeks|faizsiz|islami|icazet|katılım finans|danışma kurulu|katılım bankacılığı ilkeler", 6),
}


STRONG = re.compile(r"eşit dağıtım|oransal dağıtım|tahsisat ve dağıtım yapılmayaca|planlanıp planlanmadığı|"
                    r"ihraççı tarafından verilen taahhüt|ortaklar tarafından verilen taahhüt|ana faaliyet konusu|"
                    r"katılım (tüm )?endeks|yer alma şartlarını|faizsiz", re.I)


SKIPDOC = re.compile(r"denetim|fiyat tespit|de[gğ]erleme|hukuk[cç]u|finansal tablo|sorumluluk beyan|esas s[oö]zle[sş]me|"
                     r"i[cç] y[oö]nerge|fon kullan", re.I)


def skipdoc(rec, f):
    return bool(SKIPDOC.search(f.get("attachment_name") or "")) or bool(SKIPDOC.search(rec.get("summary") or ""))


def snippets(t, rx, maxpages):
    r = re.compile(rx, re.I)
    hits = []
    for sid, path, rec, f in docs(t):
        if skipdoc(rec, f):
            continue
        ps = pages_of(f["sha256"])
        if not ps:
            continue
        for p in ps:
            txt = norm(p["text"])
            ms = list(r.finditer(txt))
            if not ms:
                continue
            a = max(0, ms[0].start() - 500)
            b = min(len(txt), ms[-1].end() + 900)
            if b - a > 3200:
                b = a + 3200
            score = len(ms) + 5 * len(STRONG.findall(txt))
            hits.append((rec["role"], sid, p["n"], p["method"], txt[a:b], score))
    hits.sort(key=lambda h: (-h[5]))
    return hits[:maxpages], len(hits)


def build(t):
    e = EV[t]
    cx = CX[t]
    L = [f"# {t} — {e['company']}",
         f"İlk işlem günü: **{e['first_trading_date']}** · satış yöntemi (KAP): {e['sale_method_kap']} · SPK: {e['sale_method_spk']} · "
         f"talep toplama: {e['bookbuilding_kap']} · SPK onay: {e['approval_date_spk'] or '-'}", "",
         "## Belgeler (source_id · rol · KAP yayın · sayfa · OCR sayfa · ek adı / özet)"]
    for sid, path, rec, f in docs(t):
        ps = pages_of(f["sha256"])
        n = len(ps) if ps else 0
        o = sum(1 for p in ps if p["method"] == "OCR") if ps else 0
        L.append(f"- `{sid}` · {rec['role']}{' (ek: denetim/değerleme/hukukçu vb. — kaynak olarak kullanma)' if skipdoc(rec, f) else ''} · {rec['published_at']} · {n} s. · OCR {o} · "
                 f"{(f.get('attachment_name') or '')[:60]} / {(rec.get('summary') or '').strip()[:70]}"
                 + ("" if str(path).endswith(".pdf") else f" · **PDF değil ({Path(path).suffix})**"))
    L += ["", "## Codex değerleri"]
    for k in FIELDS:
        c = cx["fields"].get(k, {})
        L.append(f"- **{k}**: status={c.get('status')} value={json.dumps(c.get('value'), ensure_ascii=False)} "
                 f"kaynak={c.get('kap_notice_id')} s.{c.get('page')} tür={c.get('source_type')}")
        if c.get("quote"):
            L.append(f"  - alıntı: {norm(str(c.get('quote')))[:300]}")
        if c.get("note"):
            L.append(f"  - not: {norm(str(c.get('note')))[:300]}")
    L += ["", "## Aday pasajlar (otomatik arama; eksik olabilir — gerekirse qfind.py ile ara)"]
    for k, (rx, mp) in PAT.items():
        hits, n = snippets(t, rx, mp)
        L.append(f"\n### {k} ({n} sayfada eşleşme; ilk {len(hits)} gösteriliyor)")
        for role, sid, pn, meth, txt, nm in hits:
            L.append(f"\n--- `{sid}` s.{pn} [{meth}] ({role})\n{txt}")
    (OUT / f"{t}.md").write_text("\n".join(L), encoding="utf-8")
    return len("\n".join(L))


if __name__ == "__main__":
    for t in sys.argv[1:]:
        print(t, build(t))

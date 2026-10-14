"""Ticker başına inceleme dosyası: dossier/<T>.md (ajan ve insan okuması için)."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from blib import EV, N, W, codex_all, fulltext, methods, pages, parse_listing, tick  # noqa: E402

OUT = W / "dossier"
OUT.mkdir(exist_ok=True)
SPK = json.loads((W / "spk_final.json").read_text())
SPKR = json.loads((W / "spk_rows.json").read_text())
CX = codex_all()
BOILER = "Yukarıdaki açıklamalarımızın"
CX_FIELDS = ["ipo_price_tl", "shares_offered", "post_ipo_share_capital", "capital_increase_shares", "existing_share_sale_shares",
             "additional_sale_shares", "includes_additional_sale", "ipo_size_tl", "total_demand_multiple",
             "investor_count", "investor_count_by_group", "retail_demand_multiple", "domestic_institutional_demand_multiple",
             "foreign_institutional_demand_multiple", "distributed_by_group", "retail_allocation_pct",
             "domestic_institutional_allocation_pct", "foreign_institutional_allocation_pct", "distribution_method", "lead_broker",
             "sector", "price_stability_planned", "price_stability_days", "issuer_lockup_days", "shareholder_lockup_days",
             "participation_index_eligible"]
KW = [r"fiyat istikrar", r"satmama|satılmayacağ|satış yapılmayacağ|satmayacağ|elden çıkarılmayacağ|taahhüt", r"ek satış|ek pay",
      r"katılım endeks|katılım finans|faizsiz|İslami", r"sektör|faaliyet konusu|faaliyet alanı", r"dağıtım|tahsis",
      r"konsorsiyum lideri|lider aracı|aracılık edecek|aracı kurum", r"talep toplama yöntemi|satış yöntemi|sabit fiyat"]


def page_text(path, limit=None):
    ps = pages(path)
    if ps is None:
        return "(METİN YOK)"
    t = "\n".join(f"[s.{p['n']} {p['method']}]\n{p['text']}" for p in ps)
    i = t.find(BOILER)
    if i > 0:
        t = t[:i]
    j = t.find("Açıklamalar")
    if 0 < j < 1500:
        t = t[j:]
    return t if limit is None or len(t) <= limit else t[:limit] + f"\n...(kısaltıldı, toplam {len(t)} karakter)"


def kw_windows(path, maxlen=20000):
    ps = pages(path)
    if ps is None:
        return "(METİN YOK)"
    full = "\n".join(f"[s.{p['n']}] " + p["text"] for p in ps)
    spans = []
    for kw in KW:
        for m in list(re.finditer(kw, full, re.I))[:4]:
            spans.append((max(0, m.start() - 300), min(len(full), m.end() + 500)))
    spans.sort()
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    out, n = [], 0
    for a, b in merged:
        seg = full[a:b]
        pg = re.findall(r"\[s\.(\d+)\]", full[:a])
        out.append(f"--- (s.{pg[-1] if pg else '?'}) …{seg}…")
        n += len(seg)
        if n > maxlen:
            out.append("...(pencereler kısaltıldı)")
            break
    return "\n".join(out)


def build(t):
    ev = EV[t]
    d = tick(t)
    cx = CX[t]
    L = [x for x in d["docs"] if x["role"] == "LISTING"][0]
    lp = parse_listing(fulltext(L["pdf"]) or "")
    s = SPK[t]
    lines = [f"# {t} — {ev['company']}", f"İlk işlem günü (KAP): {ev['first_trading_date']} · satış yöntemi: {ev['sale_method_kap']} · pazar: {ev['market']}",
             "", "## BIST listeleme bildirimi (KAP_%s, yayın %s)" % (L["id"], L["published_at"]),
             json.dumps({k: lp.get(k) for k in ("nominal", "baz", "sermaye", "ftd", "yontem", "arz_tarihi", "pazar", "duzeltme")}, ensure_ascii=False),
             "", f"## SPK bülteni {SPKR[t].get('no') or ''} A.1 satırı", json.dumps(s["cols"], ensure_ascii=False), "alıntı: " + s["quote"]]
    foot = SPKR[t].get("footnotes") or ""
    if foot:
        lines += ["dipnotlar (bültenin A.1 sonrası metni, kısaltılmış):", foot[:1800]]
    lines += ["", "## Codex değerleri (doğrulanacak)"]
    for f in CX_FIELDS:
        v = cx["fields"].get(f)
        if not v:
            continue
        lines.append(f"- {f}: {v.get('value')!r} [{v.get('status')}] kaynak={v.get('source_type')} {v.get('kap_notice_id') or v.get('source_url','')} "
                     + (f"origin={v.get('origin')} filter={v.get('filter_status')} def={v.get('definition')!r} " if f == 'total_demand_multiple' else "")
                     + f"alıntı={N(v.get('quote',''))[:220]!r}")
    lines += ["", "## Sonuç bildirimleri (listeleme öncesi)"]
    for doc in d["docs"]:
        if not doc["role"].startswith("RESULT"):
            continue
        lines += [f"### KAP_{doc['id']} · {doc['kap_title']} · yayın {doc['published_at']} · özet: {doc['summary']}",
                  f"(metin yöntemi: {','.join(methods(doc['pdf']))})", page_text(doc["pdf"], 9000)]
        for a in doc["attachments"]:
            lines.append(f"#### KAP_{doc['id']}_EK{a['n']} · {a['name']} · pdf={a['is_pdf']} · yöntem: {','.join(methods(a['path'])) if a.get('path') else '-'}")
            lines.append(page_text(a["path"], 12000) if a.get("path") else "(PDF değil)")
    lines += ["", "## TSSD (anahtar sözcük pencereleri)"]
    for doc in d["docs"]:
        if not doc["role"].startswith("TSSD"):
            continue
        lines.append(f"### KAP_{doc['id']} · {doc['kap_title']} · yayın {doc['published_at']}")
        for a in doc["attachments"]:
            lines.append(f"#### KAP_{doc['id']}_EK{a['n']} · {a['name']} · yöntem: {','.join(methods(a['path'])) if a.get('path') else '-'}")
            lines.append(kw_windows(a["path"]) if a.get("path") else "(PDF değil)")
    lines += ["", "## Diğer listeleme öncesi KAP satırları (indirilmedi)"]
    for r in d["other_rows"]:
        if "Analist Raporu" in r["subject"] or r["subject"].startswith("İzahname") or "Fiyat Tespit" in r["subject"]:
            continue
        lines.append(f"- {r['id']} {r['publish']} {r['kap_title'][:30]} | {r['subject'][:60]} | {(r['summary'] or '')[:100]}")
    (OUT / f"{t}.md").write_text("\n".join(lines))
    return len("\n".join(lines))


if __name__ == "__main__":
    import glob
    ts = sys.argv[1:] or sorted(Path(f).stem for f in glob.glob(str(W / "tick/*.json")))
    for t in ts:
        print(t, build(t))

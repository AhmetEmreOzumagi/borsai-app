"""decisions/<T>.json denetçisi. Kullanım: python3 check_decision.py T [T ...]

Denetler: şema, kaynak kimliği ticker'ın belgelerinden biri, her alıntı (whitespace normalize) belge metninde
birebir var, sayısal değer alıntıda Türkçe yazımıyla geçiyor, hesaplanan katın aritmetiği, Codex kontrol listesi tam.
"""
import json
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from blib import EV, N, W, codex_all, fulltext, tick  # noqa: E402

CX = codex_all()
SPK = json.loads((W / "spk_final.json").read_text())
RESULT_FIELDS = ["total_demand_multiple", "total_demand_filter_status", "ipo_size_tl", "capital_increase_shares",
                 "existing_share_sale_shares", "additional_sale_shares"]
CAND = ["investor_count", "investor_count_by_group", "retail_demand_multiple", "domestic_institutional_demand_multiple",
        "foreign_institutional_demand_multiple", "distributed_by_group", "retail_allocation_pct",
        "domestic_institutional_allocation_pct", "foreign_institutional_allocation_pct", "distribution_method", "lead_broker",
        "price_stability_planned", "price_stability_days", "issuer_lockup_days", "shareholder_lockup_days", "sector",
        "participation_index_eligible"]
AUX = ["full_sale_statement", "additional_sale_usage_statement"]
CODEX_FIELDS = RESULT_FIELDS[:1] + RESULT_FIELDS[2:] + CAND
ORIGINS = ("SOURCE_REPORTED", "SOURCE_REPORTED_APPROX", "CALCULATED_FROM_SOURCE_TOTALS")
FILTERS = ("NOT_SPECIFIED", "UNFILTERED", "FILTERED")
VERDICTS = ("FOUND_SAME", "FOUND_DIFFERENT", "NOT_FOUND_IN_DOCS", "NOT_APPLICABLE")


def doc_map(t):
    d = tick(t)
    m = {}
    for doc in d["docs"]:
        m[f"KAP_{doc['id']}"] = doc["pdf"]
        for a in doc["attachments"]:
            if a.get("path"):
                m[f"KAP_{doc['id']}_EK{a['n']}"] = a["path"]
    m["SPK"] = SPK[t]["file"]
    return m


def tr_forms(v: str):
    """Değerin belgede görünebilecek yazımları."""
    v = str(v)
    out = {v}
    if re.fullmatch(r"\d+(\.\d+)?", v):
        ip, _, fp = v.partition(".")
        grp = f"{int(ip):,}".replace(",", ".")
        out |= {grp + ("," + fp if fp else ""), ip + ("," + fp if fp else "")}
        out.add(f"{int(ip):,}" + ("." + fp if fp else ""))  # İngilizce binlik ayırıcı
        if fp:
            out |= {grp + "," + fp.rstrip("0"), ip + "," + fp.rstrip("0"), grp + "," + fp + "0", ip + "." + fp}
    return out


def quotes_of(f):
    q = f.get("quote")
    if q is None:
        return []
    return q if isinstance(q, list) else [q]


def check(t):
    p = W / "decisions" / f"{t}.json"
    probs = []
    if not p.exists():
        return [f"{t}: karar dosyası yok"]
    try:
        d = json.loads(p.read_text())
    except Exception as e:
        return [f"{t}: JSON bozuk: {e}"]
    dm = doc_map(t)
    texts = {}

    def txt(sid):
        if sid not in texts:
            texts[sid] = fulltext(dm[sid]) if sid in dm else None
        return texts[sid]

    fields = d.get("fields") or {}
    for name in RESULT_FIELDS + CAND + AUX:
        if name not in fields:
            probs.append(f"{name}: yok (null da olsa yazılmalı)")
    for name, f in fields.items():
        if f is None:
            if name in AUX:
                continue
            probs.append(f"{name}: null nesne; {{'value': null, 'missing_reason': ...}} yazın")
            continue
        val = f.get("value")
        if name not in AUX and val is None:
            if not f.get("missing_reason"):
                probs.append(f"{name}: value null ama missing_reason yok")
            continue
        sid = f.get("source_id")
        if sid not in dm:
            probs.append(f"{name}: source_id {sid!r} bu ticker'ın belgelerinde yok ({sorted(dm)})")
            continue
        body = txt(sid)
        if body is None:
            probs.append(f"{name}: {sid} metni yok")
            continue
        qs = quotes_of(f)
        calc = name == "total_demand_multiple" and f.get("origin") == "CALCULATED_FROM_SOURCE_TOTALS"
        if calc:
            qs = qs + [f.get("numerator_quote") or "", f.get("denominator_quote") or ""]
        if not any(qs) and not (name == "total_demand_filter_status" and val == "NOT_SPECIFIED"):
            probs.append(f"{name}: alıntı yok")
        for q in qs:
            if q and N(q) not in body:
                probs.append(f"{name}: alıntı belgede birebir yok: {q[:90]!r}")
        if name == "total_demand_multiple":
            if f.get("origin") not in ORIGINS:
                probs.append(f"{name}: origin {f.get('origin')!r}")
            if calc:
                try:
                    num, den = Decimal(f["numerator"]), Decimal(f["denominator"])
                    exp = format((num / den).quantize(Decimal("1e-10"), rounding=ROUND_HALF_UP), "f").rstrip("0").rstrip(".")
                    if exp != val:
                        probs.append(f"{name}: hesap {num}/{den} = {exp}, değer {val}")
                    for part, q in ((f["numerator"], f.get("numerator_quote", "")), (f["denominator"], f.get("denominator_quote", ""))):
                        if not any(x in q for x in tr_forms(part)):
                            probs.append(f"{name}: {part} alıntıda yok")
                except Exception as e:
                    probs.append(f"{name}: hesap alanları eksik ({e})")
            elif not any(x in " ".join(qs) for x in tr_forms(val)):
                probs.append(f"{name}: değer {val} alıntıda geçmiyor")
        elif name == "total_demand_filter_status":
            if val not in FILTERS:
                probs.append(f"{name}: {val!r}")
        elif name in ("ipo_size_tl", "capital_increase_shares", "existing_share_sale_shares", "additional_sale_shares",
                      "investor_count", "retail_demand_multiple", "domestic_institutional_demand_multiple",
                      "foreign_institutional_demand_multiple", "retail_allocation_pct", "domestic_institutional_allocation_pct",
                      "foreign_institutional_allocation_pct", "price_stability_days", "issuer_lockup_days", "shareholder_lockup_days"):
            if not isinstance(val, str) or not re.fullmatch(r"\d+(\.\d+)?", val):
                probs.append(f"{name}: değer kanonik sayı metni değil ({val!r})")
            elif not f.get("derived") and not f.get("zero_from_statement") and not any(x in " ".join(qs) for x in tr_forms(val)):
                probs.append(f"{name}: değer {val} alıntıda geçmiyor (türetildiyse derived: true + formula)")
            if f.get("derived") and not f.get("formula"):
                probs.append(f"{name}: derived ama formula yok")
    cc = d.get("codex_check") or {}
    cx = CX[t]["fields"]
    for name in CODEX_FIELDS:
        v = cx.get(name)
        if v and v.get("status") in ("OK", "PARTIAL") and v.get("value") not in ("BULUNAMADI", None, ""):
            c = cc.get(name)
            if not c or c.get("verdict") not in VERDICTS:
                probs.append(f"codex_check.{name}: eksik ya da verdict geçersiz (Codex değeri {v.get('value')!r})")
    return [f"{t}: {x}" for x in probs]


if __name__ == "__main__":
    allp = []
    for t in sys.argv[1:]:
        pr = check(t)
        allp += pr
        print(f"{t}: {'OK' if not pr else str(len(pr)) + ' sorun'}")
    for x in allp:
        print("  ", x)

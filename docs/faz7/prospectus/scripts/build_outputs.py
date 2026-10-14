"""Karar dosyalarından teslim çıktıları: candidate_features_faz7/<T>.json, source_docs/<T>/MANIFEST.json,
coverage.csv, verification_log.jsonl (geçiş 1; geçiş 2 kayıtları recheck.py'den eklenir).
Kullanım: python3 build_outputs.py"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import EV, FIELDS, MEMBERS, T, V, before_listing, codex_all  # noqa: E402
from tlib import docs, match_page, norm, pages_of  # noqa: E402

CX = codex_all()
SHA = json.loads((T / "logs" / "sha_compare.json").read_text())["tickers"]
UNIT = {"distribution_method": "", "price_stability_planned": "boolean", "price_stability_days": "gün",
        "issuer_lockup_days": "gün", "shareholder_lockup_days": "gün", "sector": "", "participation_index_eligible": "boolean"}
STYPE = {"IZAHNAME": "IZAHNAME", "TSSD": "TSSD", "BIST_BIRINCIL": "BIST_DUYURU", "IZAHNAME_DEGISIKLIK": "IZAHNAME_DEGISIKLIK",
         "KAP_DIGER": "KAP_DIGER", "KAP_SONUC": "KAP_DIGER"}


def text_layer(ps):
    if not ps:
        return "NO_TEXT"
    m = {p["method"] for p in ps if p["method"] in ("TEXT", "OCR")}
    return "+".join(sorted(m)) or "NO_TEXT"


def manifest(t):
    sc = {r["kap_notice_id"]: r for r in SHA.get(t, []) if r.get("kap_notice_id")}
    out = []
    for sid, path, rec, f in docs(t):
        ps = pages_of(f["sha256"]) if str(path).endswith(".pdf") else None
        c = sc.get(rec["id"], {})
        out.append({"source_id": sid, "file": f["file"], "type": STYPE.get(rec["role"], rec["role"]),
                    "kap_notice_id": rec["id"], "kap_notice_url": rec["page_url"], "url": f["url"],
                    "kind": f["kind"], "attachment_name": f.get("attachment_name"), "kap_summary": norm(rec.get("summary") or ""),
                    "published_at": rec["published_at"], "published_at_basis": rec["published_at_basis"],
                    "published_before_first_trading_day": bool(rec["published_at"]) and before_listing(rec["published_at"], t),
                    "accessed_at_utc": f["accessed_at_utc"], "sha256": f["sha256"], "bytes": f["bytes"],
                    "raw_java_wrapped_sha256": f.get("raw_java_wrapped_sha256"),
                    "pages": len(ps) if ps else None, "text_layer": text_layer(ps),
                    "ocr_pages": sum(1 for p in ps if p["method"] == "OCR") if ps else None,
                    "found_by": rec.get("why"),
                    "codex_cited": bool(c), "codex_sha_claim": c.get("sha_claim"),
                    "codex_local_copy_same_sha": bool(c.get("codex_local_copies_same_sha"))})
    return out


def src_attrs(t, sid, pg, dm, quote):
    rec, f = dm[sid]
    ps = pages_of(f["sha256"])
    page = next((x for x in ps if x["n"] == pg), None)
    mm = match_page(page, quote) if page else None
    return {"source_id": sid, "source_url": f["url"], "source_type": STYPE.get(rec["role"], rec["role"]),
            "kap_notice_id": rec["id"], "kap_notice_url": rec["page_url"], "published_at": rec["published_at"],
            "source_sha256": f["sha256"], "source_file": f"source_docs/{t}/{f['file']}", "page": pg,
            "ocr": mm == "OCR", "text_layer_used": mm}


def status_of(cx_ok, verdict, has_value):
    if cx_ok:
        if has_value and verdict == "FOUND_SAME":
            return "VERIFIED", "CODEX_VERIFIED", "VERIFIED"
        if has_value:
            return "CORRECTED", "CODEX_CORRECTED", "CORRECTED"
        return "MISSING", "MISSING", "UNVERIFIABLE"
    if has_value:
        return "FILLED", "CLAUDE_VERIFIER_FILLED", None
    return "MISSING", "MISSING", None


def build(t, vlog):
    dm = {sid: (rec, f) for sid, path, rec, f in docs(t)}
    dp = T / "decisions" / f"{t}.json"
    dec = json.loads(dp.read_text()) if dp.exists() else None
    cxf = CX[t]["fields"]
    fields = {}
    sources = {}
    for k in FIELDS:
        c = cxf.get(k, {})
        cx_ok = c.get("status") == "OK"
        f = (dec or {}).get("fields", {}).get(k) or {}
        verdict = ((dec or {}).get("codex_check") or {}).get(k, {}).get("verdict")
        v = f.get("value")
        st, prov, cverd = status_of(cx_ok, verdict, v is not None)
        rec = {"value": v, "unit": f.get("unit") or UNIT[k], "status": st}
        if v is not None:
            rec.update(src_attrs(t, f["source_id"], f["page"], dm, f["quote"]))
            rec["quote"] = f["quote"]
            if f.get("extra_quotes"):
                rec["extra_quotes"] = [{**src_attrs(t, q["source_id"], q["page"], dm, q["quote"]), "quote": q["quote"]}
                                       for q in f["extra_quotes"]]
            if f.get("components") is not None:
                rec["components"] = f["components"]
            rec["provenance"] = prov
            rec["note"] = f.get("note", "")
            for q in [f] + (f.get("extra_quotes") or []):
                r, fr = dm[q["source_id"]]
                sources[q["source_id"]] = {"type": STYPE.get(r["role"], r["role"]), "kap_notice_id": r["id"],
                                           "url": fr["url"], "published_at": r["published_at"], "sha256": fr["sha256"],
                                           "file": f"source_docs/{t}/{fr['file']}"}
        else:
            rec["provenance"] = "MISSING"
            rec["missing_reason"] = f.get("missing_reason") or "karar dosyası yok"
            rec["looked_at"] = f.get("looked_at") or []
            rec["note"] = f.get("note", "")
        if cx_ok:
            rec["codex_value"] = c.get("value")
            rec["codex_verdict"] = cverd
            if verdict in ("FOUND_DIFFERENT", "NOT_FOUND_IN_DOCS"):
                rec["codex_note"] = ((dec or {}).get("codex_check") or {}).get(k, {}).get("note", "")
        fields[k] = rec
        vlog.append({"pass": 1, "ticker": t, "field": k, "codex_status": c.get("status"), "codex_value": c.get("value"),
                     "codex_kap_notice_id": c.get("kap_notice_id"), "codex_page": c.get("page"),
                     "codex_published_at": c.get("published_at"), "agent_verdict": verdict, "codex_outcome": cverd,
                     "final_status": st, "final_value": v, "source_id": f.get("source_id"), "page": f.get("page"),
                     "reviewed_by": (dec or {}).get("reviewed_by")})
    doc = {"schema_version": "borsai.oot_candidate_features_faz7/1", "ticker": t, "company": EV[t]["company"],
           "first_trading_date": EV[t]["first_trading_date"],
           "note": ("FAZ7 aday özellikleri (7 alan; model girdisi DEĞİLDİR). Biçim H99 ana tablosuyla uyumlu. "
                    "Kaynaklar listeleme öncesi resmi KAP belgeleri; PDF'ler repo dışında, source_docs/<T>/MANIFEST.json URL+sha256 ile eşlenir."),
           "fields": fields, "sources": dict(sorted(sources.items()))}
    return doc


def main():
    (V / "candidate_features_faz7").mkdir(exist_ok=True)
    vlog, cov = [], []
    for m in MEMBERS:
        t = m["ticker"]
        man = manifest(t)
        (V / "source_docs" / t).mkdir(parents=True, exist_ok=True)
        (V / "source_docs" / t / "MANIFEST.json").write_text(
            json.dumps({"ticker": t, "company": EV[t]["company"], "first_trading_date": EV[t]["first_trading_date"],
                        "documents": man}, ensure_ascii=False, indent=1))
        doc = build(t, vlog)
        (V / "candidate_features_faz7" / f"{t}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1))
        cov.append({"ticker": t, **{k: doc["fields"][k]["status"] for k in FIELDS}})
    with open(V / "coverage.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["ticker"] + FIELDS)
        w.writeheader()
        w.writerows(cov)
    p2 = T / "logs" / "recheck_log.jsonl"
    extra = [json.loads(x) for x in p2.read_text().splitlines()] if p2.exists() else []
    with open(V / "verification_log.jsonl", "w", encoding="utf-8") as fh:
        for r in vlog + extra:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("yazıldı", len(cov))


if __name__ == "__main__":
    main()

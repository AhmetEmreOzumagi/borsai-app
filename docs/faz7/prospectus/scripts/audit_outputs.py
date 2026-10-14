"""Teslim çıktılarının bağımsız denetimi (karar dosyalarına değil, yazılmış JSON'lara bakar).
Her dolu alan: kaynak dosya diskte, sha256 eşleşiyor, MANIFEST'te, yayın < ilk işlem günü, alıntı(lar) o sayfanın metninde birebir.
Her dosya: 7 alan, her alanda status. Çıktı: logs/audit_result.json"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import FIELDS, MEMBERS, T, V, before_listing  # noqa: E402
from tlib import match_page, norm, pages_of  # noqa: E402

STAT = ("VERIFIED", "CORRECTED", "FILLED", "MISSING")


def main():
    res, bad = {}, 0
    shacache = {}
    for m in MEMBERS:
        t = m["ticker"]
        errs = []
        p = V / "candidate_features_faz7" / f"{t}.json"
        man = json.loads((V / "source_docs" / t / "MANIFEST.json").read_text())
        mids = {d["source_id"]: d for d in man["documents"]}
        d = json.loads(p.read_text())
        if set(d["fields"]) != set(FIELDS):
            errs.append("alan kümesi 7 alan değil")
        for k, f in d["fields"].items():
            if f.get("status") not in STAT:
                errs.append(f"{k}: status yok/geçersiz")
            if f.get("value") is None:
                if f.get("status") != "MISSING" or not f.get("missing_reason"):
                    errs.append(f"{k}: boş değer MISSING+neden değil")
                continue
            for q in [f] + (f.get("extra_quotes") or []):
                sid = q["source_id"]
                if sid not in mids:
                    errs.append(f"{k}: {sid} MANIFEST'te yok")
                    continue
                fp = V / q["source_file"]
                if fp not in shacache:
                    shacache[fp] = hashlib.sha256(fp.read_bytes()).hexdigest() if fp.exists() else None
                if shacache[fp] != q["source_sha256"] or mids[sid]["sha256"] != q["source_sha256"]:
                    errs.append(f"{k}: {sid} sha eşleşmiyor")
                if not before_listing(q["published_at"], t):
                    errs.append(f"{k}: {sid} yayın ilk işlem gününden önce değil")
                ps = pages_of(q["source_sha256"])
                pg = next((x for x in (ps or []) if x["n"] == q["page"]), None)
                mm = match_page(pg, q["quote"]) if pg else None
                if mm is None:
                    errs.append(f"{k}: alıntı {sid} s.{q['page']} metninde yok")
                elif bool(q.get("ocr")) != (mm == "OCR"):
                    errs.append(f"{k}: ocr bayrağı yanlış")
        res[t] = errs
        bad += bool(errs)
    (T / "logs" / "audit_result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"denetim: {len(res) - bad}/{len(res)} sorunsuz")
    for t, e in res.items():
        if e:
            print(t, e[:5])


if __name__ == "__main__":
    main()

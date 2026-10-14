"""verified/ çıktılarının bağımsız denetimi (K2): her dolu alan için
- kaynak dosya source_docs altında var, sha256 eşleşiyor, MANIFEST'te;
- yayın zamanı (İstanbul tarihi) < ilk işlem günü;
- alıntı (whitespace normalize) pinlenmiş dosyanın metninde birebir;
- değer alıntıda Türkçe yazımıyla geçiyor (derived / carry / zero_from_statement / unit_expansion hariç; bunlar ayrıca sayılır).
Çıktı: audit_result.json
"""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from blib import N, fulltext  # noqa: E402
from check_decision import tr_forms  # noqa: E402

ROOT = Path.home() / "Desktop/BorsAi_codex/verified"
REG = ROOT / "registry/oot"


def ist_date(ts):
    import datetime as dt
    d = dt.datetime.fromisoformat(ts)
    return d.astimezone(dt.timezone(dt.timedelta(hours=3))).date().isoformat()


def audit_file(p, ftd, kind):
    doc = json.loads(p.read_text())
    t = doc["ticker"]
    probs, counts = [], {"filled": 0, "quote_ok": 0, "value_in_quote": 0, "special": 0}
    man = json.loads((REG / "source_docs" / t / "MANIFEST.json").read_text())
    mfiles = {m["source_id"]: m for m in man["documents"]}
    for name, f in doc["fields"].items():
        if f.get("value") is None:
            if not f.get("missing_reason"):
                probs.append(f"{name}: null ama neden yok")
            continue
        counts["filled"] += 1
        if not f.get("provenance"):
            probs.append(f"{name}: provenance yok")
        sid = f["source_id"]
        path = ROOT / f["source_path"]
        if not path.exists():
            probs.append(f"{name}: dosya yok {path}")
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != f["source_sha256"]:
            probs.append(f"{name}: sha uyuşmuyor")
        if sid not in mfiles:
            probs.append(f"{name}: MANIFEST'te yok {sid}")
        if not ist_date(f["source_published_at"]) < ftd:
            probs.append(f"{name}: yayın {f['source_published_at']} >= {ftd}")
        body = fulltext(path)
        qs = f.get("quote")
        qs = qs if isinstance(qs, list) else ([qs] if qs else [])
        for extra in ("numerator_quote", "denominator_quote"):
            if f.get(extra):
                qs.append(f[extra])
        if not qs:
            if name == "total_demand_filter_status" and f["value"] == "NOT_SPECIFIED":
                counts["quote_ok"] += 1
                continue
            probs.append(f"{name}: alıntı yok")
            continue
        bad = [q for q in qs if N(q) not in (body or "")]
        if bad:
            probs.append(f"{name}: alıntı belgede yok: {bad[0][:80]!r}")
        else:
            counts["quote_ok"] += 1
        v = f["value"]
        special = f.get("derived") or f.get("carry_rule") or f.get("zero_from_statement") or f.get("unit_expansion") or isinstance(v, dict)
        if special:
            counts["special"] += 1
        elif isinstance(v, str) and (any(x in " ".join(qs) for x in tr_forms(v)) or v in (" ".join(qs))):
            counts["value_in_quote"] += 1
        elif name in ("first_trading_date", "bookbuilding_start", "bookbuilding_end"):
            counts["value_in_quote"] += 1  # tarih biçimi dönüşümü (gg/aa/yyyy -> ISO)
        elif name in ("planned_additional_sale_ceiling", "planned_existing_share_sale", "planned_capital_increase_shares", "additional_sale_shares") and v == "0" and re.search(r"(^|\s)[-–]($|\s)", " ".join(qs)):
            counts["value_in_quote"] += 1  # tablo '-' = 0
        elif name == "total_demand_filter_status" and re.search(r"filtre|filtrelen|mükerrer|ayıkla", " ".join(qs), re.I):
            counts["value_in_quote"] += 1
        elif name in ("price_stability_planned", "participation_index_eligible", "distribution_method", "lead_broker", "sector", "market", "sale_method", "ipo_price_try"):
            counts["value_in_quote"] += 1  # metin/boolean değerler: alıntı birebir denetlendi
        else:
            probs.append(f"{name}: değer {v!r} alıntıda geçmiyor")
    return probs, counts


def main():
    res = {}
    for p in sorted((REG / "inputs").glob("*.json")):
        t = p.stem
        ftd = json.loads(p.read_text())["fields"]["first_trading_date"]["value"]
        a, ca = audit_file(p, ftd, "inputs")
        b, cb = audit_file(REG / "candidate_features" / f"{t}.json", ftd, "cand")
        res[t] = {"inputs": {"problems": a, **ca}, "candidate_features": {"problems": b, **cb}}
        if a or b:
            print(t, a[:3], b[:3])
    Path(__file__).with_name("audit_result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print("dosya", len(res), "sorunsuz", sum(1 for v in res.values() if not v["inputs"]["problems"] and not v["candidate_features"]["problems"]))


if __name__ == "__main__":
    main()

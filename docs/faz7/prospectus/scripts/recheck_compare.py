"""Rastgele 10 arzın ikinci (bağımsız) kontrolünü birincisiyle karşılaştırır -> logs/recheck_log.jsonl (pass=2) + özet.
Değer karşılaştırması: aynı metin (distribution_method ve sector için doğrulayıcı elle anlamca karşılaştırır: 'semantic' sütunu)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import FIELDS, T  # noqa: E402

SAMPLE = (T / "logs" / "sample10.txt").read_text().split("\n")[1].split()


def main():
    out, n_same, n = [], 0, 0
    for t in SAMPLE:
        d1 = json.loads((T / "decisions" / f"{t}.json").read_text())
        p2 = T / "decisions2" / f"{t}.json"
        d2 = json.loads(p2.read_text()) if p2.exists() else None
        for k in FIELDS:
            v1 = d1["fields"][k].get("value")
            v2 = d2["fields"][k].get("value") if d2 else "YOK"
            same = v1 == v2
            n += 1
            n_same += same
            out.append({"pass": 2, "ticker": t, "field": k, "first_value": v1, "second_value": v2, "exact_same": same,
                        "second_source": (d2 or {}).get("fields", {}).get(k, {}).get("source_id"),
                        "second_page": (d2 or {}).get("fields", {}).get(k, {}).get("page")})
            if not same:
                print(f"{t}.{k}: 1={v1!r} | 2={v2!r}")
    (T / "logs" / "recheck_raw.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"birebir aynı: {n_same}/{n}")


if __name__ == "__main__":
    main()

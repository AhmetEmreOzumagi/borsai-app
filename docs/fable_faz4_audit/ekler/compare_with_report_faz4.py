#!/usr/bin/env python3
"""Karşılaştırma harnessi (yeniden üretimin parçası DEĞİL; Opus'un rapor kodunu çalıştırır):
1) `borsai.report_faz4`'ün 36 §6 satırı için tam hassasiyetli fark / %95 aralık / n değerlerini alır ve
   repro_output.json'daki bağımsız değerlerle |Δ| ≤ 1e-9 karşılaştırır.
2) docs/MODELS.md'deki 36 satırı (4 hane) bağımsız değerlerin aynı biçimde yuvarlanmışıyla karşılaştırır.
3) D1 beraberlik sayıları ve başarısızlık (a)-(d) hükümlerini karşılaştırır.
Hiçbir dosyaya yazmaz (stdout)."""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from borsai import report_faz4 as r4                # noqa: E402
from borsai.report_faz1b import load_runs, _s, _ci  # noqa: E402

mine = json.loads((HERE / "repro_output.json").read_text(encoding="utf-8"))
rows_mine = mine["rows36"]
runs, runs4 = load_runs(), r4.load_faz4_runs()
ev = r4.evaluate_expectations(runs, runs4)
assert len(ev) == 36 == len(rows_mine)
KIND = {"MAE": "return", "Brier": "p_up"}
mx_diff = mx_lo = mx_hi = 0.0
n_ok = 0
print("model | h | çıktı | karş. | Δfark | Δalt | Δüst | n(opus/benim) | etiket(opus/benim)")
for e, r in zip(ev, rows_mine):
    assert (e["model"], int(e["horizon"][1:]), KIND[e["output"]], e["comparator"]) == (r["model_id"], r["h"], r["kind"], r["rule"]), (e, r)
    p = e["result"]
    dd, dl, dh = abs(p["mean"] - r["diff"]), abs(p["ci95"][0] - r["ci"][0]), abs(p["ci95"][1] - r["ci"][1])
    mx_diff, mx_lo, mx_hi = max(mx_diff, dd), max(mx_lo, dl), max(mx_hi, dh)
    n_ok += int(p["n"] == r["n"] and p["n_months"] == r["n_months"] and p["model_better_n"] == r["model_better"]
                and p["rule_better_n"] == r["rule_better"] and p["tie_n"] == r["tie"])
    lab_mine = r["label"] if r["label"] != "aralıkta" else "(tuttu/tutmadı)"
    print(f"{e['model']} | {e['horizon']} | {e['output']} | {e['comparator']} | {dd:.1e} | {dl:.1e} | {dh:.1e} | {p['n']}/{r['n']} | {e['label']}/{lab_mine}")
print(f"\nMAKS |Δ| fark {mx_diff:.3e}, aralık alt {mx_lo:.3e}, üst {mx_hi:.3e}; n/ay/kazanç sayıları eşit {n_ok}/36")

# MODELS.md metniyle (4 hane)
text = (ROOT / "docs" / "MODELS.md").read_text(encoding="utf-8")
sec = text.split("### §6 beklentisi ile gerçekleşen (satır satır)")[1].split("### Başarısızlık")[0]
lines = [l for l in sec.splitlines() if l.startswith("| `")]
assert len(lines) == 36
md_ok = 0
for l, r in zip(lines, rows_mine):
    cells = [c.strip().replace("\x00", "\\|") for c in l.strip().replace("\\|", "\x00").strip("|").split("|")]
    # sütunlar: Model | Ufuk | Çıktı | Karş | Beklenen | Aralık0 | fark | %95 | n | Etiket | ifade
    fark_md, ci_md, n_md = cells[6], cells[7], cells[8]
    fark_me, ci_me, n_me = _s(r["diff"]), _ci({"ci95": r["ci"]}), str(r["n"])
    same = (fark_md == fark_me and ci_md == ci_me and n_md == n_me)
    md_ok += int(same)
    if not same:
        print("MODELS.md UYUŞMAZLIK:", cells[:4], fark_md, ci_md, n_md, "| benim:", fark_me, ci_me, n_me)
print(f"MODELS.md 36 satır (fark, aralık, n; 4 hane) birebir: {md_ok}/36")

tg = r4.too_good(ev)
print("Opus 'çok iyi' koşul sayısı:", len(tg["reasons"]), "| benim:", len(mine["much_better_conditions"]))
tie = r4.d1_tie(runs, runs4)
print("D1 beraberlik opus:", tie, "| benim:", mine["d1_tie"])
fl = r4.failures(runs, runs4)
print("Başarısızlık opus:", {k: v[0] for k, v in fl.items()}, "| benim:", {k: mine["failures"][k] for k in "abcd"})
print("kalibrasyon opus:", fl["d"][1][:2], "| benim:", (mine["failures"]["mean_p_up_3"], mine["failures"]["obs_Y3"]))

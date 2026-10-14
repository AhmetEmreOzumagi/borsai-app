"""docs/MODELS.md'nin Faz 4 bölümü: tavan yolu modelleri (SPEC_CEILING_PATH_V0).

Girdi: tests/reference/macos_golden_faz4/ (Faz 4 resmi koşularının ledger'ları), Faz 1A/1B altın ledger'ları
(karşılaştırılanlar; yeniden koşulmaz, şartname §5/§8), dondurulmuş model dosyaları, experiments/log.jsonl ve
şartnamenin §6 beklenti tablosu (dosyadan AYNEN okunur). Yeni backtest koşmaz; aynı girdilerden aynı metni üretir.

§6 satırlarının etiketi ("tuttu" / "tutmadı" / "daha iyi" / "daha kötü") ve "beklentiden çok iyi" denetimi
`OPERATIONAL_RULES_FAZ4`'teki kurallarla verilir; kurallar Faz 4 backtest sonuçları görülmeden, bu dosya
yazılırken sabitlendi ve raporda yazılıdır.
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from . import metrics as mx
from . import report_faz1b as rf
from . import survival as sv
from .backtest import FAZ4_RUNS, GOLDEN_FAZ4_DIR, golden_filename, run_key
from .horizons import HORIZONS
from .provenance import ROOT
from .specs import MODEL_SPECS, PLAN_KEYS, SPEC_DOCUMENTS_FAZ4

SPEC_PATH = ROOT / SPEC_DOCUMENTS_FAZ4["SPEC_CEILING_PATH_V0"]["path"]
MAIN, ZERO, PB = "ceiling_path_v0", "ceiling_path_v0@INF", "pb_ceiling_path_v0"
ALL_H = tuple(range(1, sv.DAYS + 1))

# Önceden ilan edilen tek birincil hücre (§5).
PRIMARY = {"model": MAIN, "horizon": "D5", "output": "MAE", "comparator": "base_train_median"}

# §6 "beklentiden çok iyi" tanımı (şartnameden sayılar aynen).
TOO_GOOD_PRIMARY_DIFF = -0.120
TOO_GOOD_PRIMARY_CI_HI = -0.060
TOO_GOOD_MARGIN = 0.03
# §6 D1 beraberlik cümlesi: "fold'ların ≥ 80/87'sinde fark bit-eşit 0 ya da |fark| < 0.001".
D1_TIE_TOL = 0.001
D1_TIE_SHARE = 80 / 87
# §6 başarısızlık tanımları.
MECH_POINT = -0.005        # (a) noktasal fark ≥ −0.005
CALIBRATION_TOL = 0.15     # (d)

# §6 "Aralık 0'ı" sütunu -> kategori. Kesin ifadeler etiketi etkiler; olasılık ifadeleri yalnız yan sütunda.
CI_CATEGORY = {
    "içerir (beraberlik)": "INCLUDES",
    "içerir": "INCLUDES",
    "dışlar (negatif)": "EXCLUDES_NEG",
    "içerir ya da pozitif dışlar": "NOT_NEG",
    "dışlayabilir (negatif)": "MAY_EXCLUDE_NEG",
    "dışlayabilir": "MAY_EXCLUDE_NEG",
    "dışlaması olası": "MAY_EXCLUDE_NEG",
    "dışlaması olası, garanti değil": "MAY_EXCLUDE_NEG",
    "büyük olasılıkla içerir": "LIKELY_INCLUDES",
}

OPERATIONAL_RULES_FAZ4 = (
    "Satırın beklenen fark aralığı [alt, üst] (\"|fark| < x\" için açık aralık (−x, x)); fark = model − karşılaştırılan, "
    "negatif = model iyi. Fark alt ucun altındaysa **daha iyi**, üst ucun üstündeyse **daha kötü**.",
    "Fark aralık içindeyse \"Aralık 0'ı\" ifadesinin kesin kısmına bakılır: \"içerir\" → %95 aralık 0'ı içermeli; "
    "\"dışlar (negatif)\" → aralığın üst ucu < 0; \"içerir ya da pozitif dışlar\" → üst uç ≥ 0; \"dışlayabilir\" / "
    "\"dışlaması olası\" → aralık 0'ı pozitif tarafta dışlamamalı (alt uç ≤ 0). Kesin kısım tutuyorsa **tuttu**, "
    "tutmuyorsa **tutmadı**.",
    "Olasılık ifadeleri (\"büyük olasılıkla içerir\", \"dışlaması olası\", \"dışlayabilir\") etiketi yalnız yukarıdaki "
    "kesin kısımlarıyla etkiler; ifadenin tamamının gerçekleşip gerçekleşmediği ayrı sütunda yazılır.",
    f"Beklentiden çok iyi (§6): birincil hücrede fark < {TOO_GOOD_PRIMARY_DIFF:.3f} ya da aralığın üst ucu < "
    f"{TOO_GOOD_PRIMARY_CI_HI:.3f}; ya da §6 tablosunun D3/D5/D10 ufuklu herhangi bir satırında (`@INF` ve PB satırları dahil) "
    f"fark < alt uç − {TOO_GOOD_MARGIN:.2f}.",
    f"D1 beraberlik cümlesi: `ceiling_path_v0` − `base_always_ceiling` D1 MAE'de fold başına fark bit-eşit 0 ya da "
    f"|fark| < {D1_TIE_TOL} olan fold'ların payı ≥ 80/87.",
    "Eşleşik küme: iki tarafın da skorlandığı test arzları (ticker ile). Karşılaştırılan ledger'lar Faz 1A/1B "
    "altınlarıdır (yeniden koşulmaz). Brier [0.01, 0.99] kırpmalı (Faz 1A tablolarıyla aynı), MAE kırpmasız.",
)

# Bağımsız yeniden üretim (§6'nın "beklentiden çok iyi" denetimi tetiklendiği için şart).
REPRO = {
    "doc": "docs/fable_faz4_audit/AUDIT.md",
    "dir": "docs/fable_faz4_audit/",
    "date": "2026-09-22",
}
# AUDIT §6-6: D10 satırlarının dipnotu (hüküm değişmez; D10 keşif hücresidir).
D10_FOOTNOTE = ("D10 dipnotu: bu ufuktaki kazanç **L = 10 arzlarında yoğunlaşıyor** (bağımsız denetim, "
                f"`{REPRO['doc']}` §6-6: 2023'ün yedi fold'unda fark −0.48'e kadar iniyor; dört L = 10 arzı toplam "
                "farkın yaklaşık üçte birini veriyor). D10 keşif hücresidir, hüküm bundan etkilenmez.")


# ---------------------------------------------------------------------------
# Veri
# ---------------------------------------------------------------------------

def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_faz4_runs(faz4_dir: Path = GOLDEN_FAZ4_DIR) -> dict[str, list[dict[str, str]]]:
    return {run_key(m, p): _read(Path(faz4_dir) / golden_filename(run_key(m, p))) for m, p in FAZ4_RUNS}


# ---------------------------------------------------------------------------
# §6 tablosu (şartname dosyasından aynen)
# ---------------------------------------------------------------------------

def _split_row(line: str) -> list[str]:
    body = line.strip().replace("\\|", "\x00")
    return [c.strip().replace("\x00", "\\|") for c in body.strip("|").split("|")]


def _plain(text: str) -> str:
    return text.replace("**", "").strip()


def parse_range(text: str) -> tuple[float, float, bool]:
    """'−0.090 … −0.020' -> (−0.09, −0.02, kapalı); '\\|fark\\| < 0.001' -> (−0.001, 0.001, açık)."""
    t = _plain(text).replace("\\|", "|").replace("−", "-")
    if t.startswith("|fark| <"):
        x = float(t.split("<")[1])
        return -x, x, True
    lo, hi = (float(p.strip()) for p in t.split("…"))
    return lo, hi, False


def expectation_rows(spec_text: Optional[str] = None) -> list[dict[str, Any]]:
    """§6 tablosunun satırları: model, ufuk, çıktı, karşılaştırılan ve aynen metinler."""
    text = spec_text if spec_text is not None else SPEC_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("| Ufuk | Çıktı | Karşılaştırılan | Beklenen fark"))
    out = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        ufuk, cikti, karsi, rng, ci, why = _split_row(line)
        if ufuk.startswith("D"):
            model, horizon, output = MAIN, ufuk, cikti
        else:
            model = {"`@INF`": ZERO, "`pb_ceiling_path_v0`": PB}[ufuk]
            horizon, output = cikti.split(" ")
        comp_text = _plain(karsi).replace("(BİRİNCİL)", "").replace("(bilgi)", "").strip()
        comparator = ZERO if comp_text == "sıfır model" else comp_text.strip("`")
        lo, hi, strict = parse_range(rng)
        out.append({"model": model, "horizon": horizon, "output": output, "comparator": comparator,
                    "raw": {"ufuk": ufuk, "cikti": cikti, "karsilastirilan": karsi, "aralik": rng, "sifir": ci, "gerekce": why},
                    "lo": lo, "hi": hi, "strict": strict, "ci_category": CI_CATEGORY[_plain(ci)],
                    "primary": "BİRİNCİL" in karsi})
    return out


# ---------------------------------------------------------------------------
# Kayıplar ve eşleşik karşılaştırma
# ---------------------------------------------------------------------------

def _h(horizon: str) -> int:
    return int(horizon[1:])


def ok_path(h: int) -> Callable:
    return lambda r: r["status"] == "OK" and r[f"D{h}_return"] != ""


def loss_path(output: str, h: int) -> Callable:
    if output == "MAE":
        return lambda r: abs(float(r[f"D{h}_return"]) - float(r[f"realized_R_D{h}"]))
    return lambda r: mx.brier_term(float(r[f"D{h}_p_up"]), int(r[f"realized_Y_D{h}"]))


def comparator_rows(model: str, comparator: str, horizon: str, output: str, runs: dict, runs4: dict
                    ) -> tuple[list[dict[str, str]], Callable, Callable]:
    """(karşılaştırılan satırları, ok, kayıp(o, model_satırı)). Hedef model satırından okunur."""
    h = _h(horizon)
    realized_R = lambda r: float(r[f"realized_R_D{h}"])  # noqa: E731
    realized_Y = lambda r: int(r[f"realized_Y_D{h}"])  # noqa: E731
    if comparator in runs4:
        other = runs4[comparator]
        return other, ok_path(h), lambda o, r: loss_path(output, h)(o)
    if comparator in ("v1_5_h99", "pb_v0"):
        other = [o for o in runs[comparator] if o["horizon"] == horizon]
        if output == "MAE":
            return other, rf.ok_ridge, lambda o, r: abs(float(o["ridge_prediction"]) - realized_R(r))
        return other, rf.ok_logit, lambda o, r: mx.brier_term(float(o["logit_probability"]), realized_Y(r))
    key = comparator + ("__pb" if model == PB else "")
    other = [o for o in runs[key] if o["horizon"] == horizon]
    if output == "MAE":
        return other, rf.ok_rule_ret, lambda o, r: abs(float(o["rule_return"]) - realized_R(r))
    return other, rf.ok_rule_p, lambda o, r: mx.brier_term(float(o["rule_p_up"]), realized_Y(r))


def compare(model: str, comparator: str, horizon: str, output: str, runs: dict, runs4: dict) -> Optional[dict[str, Any]]:
    h = _h(horizon)
    other, ok_other, loss_other = comparator_rows(model, comparator, horizon, output, runs, runs4)
    return rf.paired(runs4[model], other, loss_path(output, h), None, ok_path(h), ok_other,
                     key=lambda r: r["ticker"], other_target=loss_other)


def fold_diffs(model: str, comparator: str, horizon: str, output: str, runs: dict, runs4: dict) -> list[float]:
    h = _h(horizon)
    other, ok_other, loss_other = comparator_rows(model, comparator, horizon, output, runs, runs4)
    by = {o["ticker"]: o for o in other}
    out = []
    for r in runs4[model]:
        o = by.get(r["ticker"])
        if o is not None and ok_path(h)(r) and ok_other(o):
            out.append(loss_path(output, h)(r) - loss_other(o, r))
    return out


# ---------------------------------------------------------------------------
# Etiketler (OPERATIONAL_RULES_FAZ4)
# ---------------------------------------------------------------------------

def ci_firm_holds(category: str, ci: Sequence[float]) -> bool:
    lo, hi = ci
    return {"INCLUDES": lo <= 0.0 <= hi, "EXCLUDES_NEG": hi < 0.0, "NOT_NEG": hi >= 0.0,
            "MAY_EXCLUDE_NEG": lo <= 0.0, "LIKELY_INCLUDES": True}[category]


def ci_statement_holds(category: str, ci: Sequence[float]) -> bool:
    """İfadenin tamamı (olasılık kısmı dahil) gerçekleşti mi (yan sütun)."""
    lo, hi = ci
    return {"INCLUDES": lo <= 0.0 <= hi, "EXCLUDES_NEG": hi < 0.0, "NOT_NEG": hi >= 0.0,
            "MAY_EXCLUDE_NEG": hi < 0.0, "LIKELY_INCLUDES": lo <= 0.0 <= hi}[category]


def label(row: dict[str, Any], p: dict[str, Any]) -> str:
    d = p["mean"]
    below = d <= row["lo"] if row["strict"] else d < row["lo"]
    above = d >= row["hi"] if row["strict"] else d > row["hi"]
    if below:
        return "daha iyi"
    if above:
        return "daha kötü"
    return "tuttu" if ci_firm_holds(row["ci_category"], p["ci95"]) else "tutmadı"


def evaluate_expectations(runs: dict, runs4: dict) -> list[dict[str, Any]]:
    out = []
    for row in expectation_rows():
        p = compare(row["model"], row["comparator"], row["horizon"], row["output"], runs, runs4)
        out.append({**row, "result": p, "label": label(row, p), "ci_statement_held": ci_statement_holds(row["ci_category"], p["ci95"])})
    return out


def too_good(evaluated: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """§6 "beklentiden çok iyi": tetiklenirse dondurma yok (farklı elle sıfırdan yeniden üretim gerekir)."""
    reasons = []
    prim = next(e for e in evaluated if e["primary"])
    d, (lo, hi) = prim["result"]["mean"], prim["result"]["ci95"]
    if d < TOO_GOOD_PRIMARY_DIFF:
        reasons.append(f"birincil fark {d:+.4f} < {TOO_GOOD_PRIMARY_DIFF:.3f}")
    if hi < TOO_GOOD_PRIMARY_CI_HI:
        reasons.append(f"birincil aralığın üst ucu {hi:+.4f} < {TOO_GOOD_PRIMARY_CI_HI:.3f}")
    for e in evaluated:
        if e["horizon"] in ("D3", "D5", "D10") and e["result"]["mean"] < e["lo"] - TOO_GOOD_MARGIN:
            reasons.append(f"`{e['model']}` {e['horizon']} {e['output']} − `{e['comparator']}`: fark {e['result']['mean']:+.4f} < "
                           f"alt uç {e['lo']:+.3f} − {TOO_GOOD_MARGIN:.2f}")
    return {"triggered": bool(reasons), "reasons": reasons, "primary": prim}


def d1_tie(runs: dict, runs4: dict) -> dict[str, Any]:
    diffs = fold_diffs(MAIN, "base_always_ceiling", "D1", "MAE", runs, runs4)
    exact = sum(1 for x in diffs if x == 0.0)
    near = sum(1 for x in diffs if x == 0.0 or abs(x) < D1_TIE_TOL)
    return {"n": len(diffs), "exact": exact, "tie": near, "held": len(diffs) > 0 and near / len(diffs) >= D1_TIE_SHARE}


def _includes_zero(p: dict[str, Any]) -> bool:
    return p["ci95"][0] <= 0.0 <= p["ci95"][1]


def failures(runs: dict, runs4: dict) -> dict[str, Any]:
    """§6 başarısızlık tanımları (a)–(d); (e) yalnız prospektif."""
    a_cells = {(hk, out): compare(MAIN, ZERO, hk, out, runs, runs4) for hk in ("D3", "D5", "D10") for out in ("MAE", "Brier")}
    a = all(_includes_zero(p) and p["mean"] >= MECH_POINT for p in a_cells.values())
    b_cells = {hk: compare(ZERO, "base_train_median", hk, "MAE", runs, runs4) for hk in ("D5", "D10")}
    b = all(p["ci95"][0] > 0.0 for p in b_cells.values())
    c_cell = compare(MAIN, "base_always_ceiling", "D1", "MAE", runs, runs4)
    c = c_cell["ci95"][0] > 0.0
    rows = [r for r in runs4[MAIN] if ok_path(3)(r)]
    mean_p3 = statistics.mean(float(r["D3_p_up"]) for r in rows)
    obs_y3 = statistics.mean(int(r["realized_Y_D3"]) for r in rows)
    d = abs(mean_p3 - obs_y3) > CALIBRATION_TOL
    return {"a": (a, a_cells), "b": (b, b_cells), "c": (c, c_cell), "d": (d, (mean_p3, obs_y3, len(rows)))}


# ---------------------------------------------------------------------------
# Biçim
# ---------------------------------------------------------------------------

_f, _s, _ci, _cell = rf._f, rf._s, rf._ci, rf._cell


def _pair_line(cells: Sequence[str], p: Optional[dict[str, Any]]) -> str:
    return rf._row(list(cells), p)


def _comparison_table(w, model: str, specs: Sequence[tuple[str, str]], runs: dict, runs4: dict,
                      note: Optional[Callable[[str, str, str], str]] = None,
                      d10_note: bool = True) -> dict[tuple[str, str, str], Any]:
    got = {}
    w("| Ufuk | Çıktı | Karşılaştırılan " + rf.PAIR_HEADER)
    w("|---|---|---" + rf.PAIR_SEP)
    for hk in HORIZONS:
        for output, comp in specs:
            p = compare(model, comp, hk, output, runs, runs4)
            got[(hk, output, comp)] = p
            name = f"`{comp}`" + (note(hk, output, comp) if note else "")
            w(_pair_line([hk, output, name], p))
    if d10_note:
        w("")
        w(D10_FOOTNOTE)
    return got


def _primary_note(hk: str, output: str, comp: str) -> str:
    return " **(BİRİNCİL)**" if (hk, output, comp) == (PRIMARY["horizon"], PRIMARY["output"], PRIMARY["comparator"]) else ""


def _realized_all(rows4: Sequence[dict[str, str]]) -> dict[tuple[str, int], float]:
    """(ticker, h) -> gerçekleşen R_h, h = 1..10 (SESSIONS kapanışlarından; D1/D3/D5/D10 tabloyla denetli)."""
    from . import ceiling_path as cp
    from .data import load_dataset

    ds = load_dataset()
    sessions = cp.load_sessions()
    by = ds.by_ticker()
    out = {}
    for r in rows4:
        rs = cp.realized_series(by[r["ticker"]], sessions[r["ticker"]])
        for h in ALL_H:
            out[(r["ticker"], h)] = rs["R"][h]
    return out


def _own_table(w, rows4: Sequence[dict[str, str]]) -> None:
    realized = _realized_all(rows4)
    w("| Ufuk | n | MAE | Medyan AE | Brier | ort. p_up | gözlenen Y oranı | yön isabeti | hep-yukarı isabeti | not |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for h in ALL_H:
        rows = [r for r in rows4 if ok_path(h)(r)]
        if not rows:
            w(f"| D{h} | 0 | — | — | — | — | — | — | — | |")
            continue
        err = [abs(float(r[f"D{h}_return"]) - realized[(r["ticker"], h)]) for r in rows]
        Y = [int(r[f"realized_Y_D{h}"]) for r in rows]
        p = [float(r[f"D{h}_p_up"]) for r in rows]
        direction = statistics.mean(float(int(float(r[f"D{h}_return"]) > 0) == y) for r, y in zip(rows, Y))
        note = "" if f"D{h}" in HORIZONS else "yalnız bilgi; kural yok"
        w(f"| D{h} | {len(rows)} | {_f(statistics.mean(err))} | {_f(statistics.median(err))} | "
          f"{_f(statistics.mean(mx.brier_term(a, y) for a, y in zip(p, Y)))} | {_f(statistics.mean(p))} | {_f(statistics.mean(Y))} | "
          f"{_f(direction)} | {_f(statistics.mean(Y))} | {note} |")


def _cells_summary(w, rows4: Sequence[dict[str, str]]) -> None:
    first = rows4[0]
    Z = [int(first[f"cells_n_Z_{m}"]) for m in range(1, 11)]
    B = [int(first[f"cells_n_B_{m}"]) for m in range(1, 10)]
    statuses = Counter(r["status"] for r in rows4)
    pooled = sum(1 for r in rows4 for h in ALL_H if r[f"D{h}_pooled_cells"] and any(c["pooled"] for c in json.loads(r[f"D{h}_pooled_cells"])))
    total = sum(1 for r in rows4 for h in ALL_H if r[f"D{h}_pooled_cells"])
    leak = sum(1 for r in rows4 if r["cells_max_session_date"] and r["cells_max_session_date"] >= r["prediction_date"])
    w(f"{len(rows4)} fold (kaynak ledger'ınkiyle aynı küme ve sıra); fold durumları: "
      + ", ".join(f"{s} {n}" for s, n in sorted(statuses.items())) + f". İlk fold {first['ticker']} "
      f"(kesim {first['prediction_date']}): Z = {Z}, B = {B}. Havuzlanmış hücre kullanan (fold, ufuk): {pooled}/{total}. "
      f"Hücrede kesim ve sonrası tarihli seans olan fold: {leak}.")


def _expectation_section(w, evaluated: Sequence[dict[str, Any]], tie: dict[str, Any]) -> None:
    w("| Model | Ufuk | Çıktı | Karşılaştırılan | Beklenen fark (§6, aynen) | Aralık 0'ı (§6, aynen) | Gerçekleşen fark | "
      "%95 aralık | n | Etiket | Aralık ifadesi gerçekleşti mi |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for e in evaluated:
        p = e["result"]
        comp = "sıfır model" if e["comparator"] == ZERO and e["model"] == MAIN else f"`{e['comparator']}`"
        lab = f"**{e['label']}**" if e["primary"] else e["label"]
        w(f"| `{e['model']}` | {e['horizon']} | {e['output']} | {comp}{' **(BİRİNCİL)**' if e['primary'] else ''} | "
          f"{_cell(_plain(e['raw']['aralik']).replace(chr(92) + '|', '|'))} | {_cell(_plain(e['raw']['sifir']))} | "
          f"{_s(p['mean'])} | {_ci(p)} | {p['n']} | {lab} | {'evet' if e['ci_statement_held'] else 'hayır'} |")
    w("")
    counts = Counter(e["label"] for e in evaluated)
    w("Etiket sayıları: " + ", ".join(f"{k} {counts[k]}" for k in ("tuttu", "tutmadı", "daha iyi", "daha kötü")) + f" (toplam {len(evaluated)}).")
    w("")
    w(f"D1 beraberlik cümlesi (\"fold'ların ≥ 80/87'sinde fark bit-eşit 0 ya da |fark| < 0.001\"): {tie['n']} eşleşik fold'un "
      f"{tie['exact']}'inde fark bit-eşit 0, {tie['tie']}'inde bit-eşit 0 ya da |fark| < {D1_TIE_TOL} → "
      + ("**tuttu**" if tie["held"] else "**tutmadı**") + ".")


def _failure_section(w, fl: dict[str, Any]) -> None:
    a, a_cells = fl["a"]
    w("- **(a) Yalnız mekanik** (ana − sıfır model, {D3, D5, D10} × {MAE, Brier}; altısının hepsinde aralık 0'ı içeriyor "
      "VE noktasal fark ≥ −0.005): " + "; ".join(f"{hk} {o} {_s(p['mean'])} {_ci(p)}" for (hk, o), p in a_cells.items())
      + " → " + ("**gerçekleşti**: \"özellik bilgisi getiriye taşınmıyor; katkı yalnız mekaniktir\"" if a else "gerçekleşmedi") + ".")
    b, b_cells = fl["b"]
    w("- **(b) Mekanik eşleme katmıyor** (sıfır model − `base_train_median`, D5 VE D10 MAE aralığı tamamen 0'ın üstünde): "
      + "; ".join(f"{hk} {_s(p['mean'])} {_ci(p)}" for hk, p in b_cells.items())
      + " → " + ("**gerçekleşti**: \"limit yolu + kırılma sonrası karışım medyan kuralından kötü\"" if b else "gerçekleşmedi") + ".")
    c, c_cell = fl["c"]
    w(f"- **(c) Eşleme hatası** (ana − `base_always_ceiling` D1 MAE aralığı tamamen 0'ın üstünde): {_s(c_cell['mean'])} {_ci(c_cell)} → "
      + ("**gerçekleşti**: kod/eşleme incelemesi" if c else "gerçekleşmedi") + ".")
    d, (mp, oy, n) = fl["d"]
    w(f"- **(d) Kalibrasyon** (|ortalama p_up_3 − gözlenen Y_3 oranı| > 0.15): ort. p_up_3 {_f(mp)}, gözlenen {_f(oy)}, "
      f"|fark| {_f(abs(mp - oy))}, n = {n} → " + ("**gerçekleşti**" if d else "gerçekleşmedi") + ".")
    w("- (e) Prospektif (n ≥ 30): birincil hücre aralığı 0'ı pozitif tarafta dışlıyor → \"geçemiyor\". Canlı n = 0; hüküm yok.")


def _conditional_section(w, runs: dict) -> None:
    from . import ceiling_path as cp

    res = cp.conditional_eval(runs)
    for model_id, block in res.items():
        comps = block["comparators"]
        w("")
        w(f"`{model_id}` (koşu `{block['run_key']}`); fark = model − kural, aynı fold'lar, L ≥ j olan arzlar:")
        w("")
        w("| j | n | model RPS_j | " + " | ".join(f"− `{c}` [%95]" for c in comps) + " |")
        w("|---|---|---" + "|---" * len(comps) + "|")
        for j, e in block["j"].items():
            cells = []
            for c in comps:
                x = e["vs"][c]["rps"]
                cells.append("—" if x["diff"] is None else (f"{_s(x['diff'])} " + ("(n < 10)" if x["ci95"] is None else _ci(x))))
            w(f"| {j} | {e['n']} | {_f(e['model']['rps'])} | " + " | ".join(cells) + " |")
        w("")
        w("| j | n | model Brier k = j+1 | " + " | ".join(f"− `{c}`" for c in comps) + " | model Brier k = 10 | "
          + " | ".join(f"− `{c}`" for c in comps) + " |")
        w("|---|---|---" + "|---" * len(comps) + "|---" + "|---" * len(comps) + "|")
        for j, e in block["j"].items():
            nxt = [e["vs"][c]["brier_next"] for c in comps]
            end = [e["vs"][c]["brier_end"] for c in comps]
            fmt = lambda x: "—" if x["diff"] is None else (_s(x["diff"]) + ("" if x["ci95"] is None else f" {_ci(x)}"))  # noqa: E731
            w(f"| {j} | {e['n']} | {_f(e['model']['brier_next'])} | " + " | ".join(fmt(x) for x in nxt) + f" | "
              f"{_f(e['model']['brier_end'])} | " + " | ".join(fmt(x) for x in end) + " |")


def _frozen_section(w, models: dict[str, Any], tg: dict[str, Any]) -> None:
    frozen_ids = [m for m in (MAIN, ZERO, PB) if m in models]
    if tg["triggered"] and not frozen_ids:
        w("**Dondurulmadı.** §6: \"Beklentiden çok iyi … dondurmadan önce farklı elle sıfırdan yeniden üretim (ilk uygulamayı "
          "görmeyen ayrı oturum, yalnız bu şartnameyle; ledger'lar |Δ| ≤ 1e-9 ile eşleşmeli). Eşleşmezse fark giderilene kadar "
          "dondurma yok.\" `models/` ve `models/INDEX.json` değişmedi; bu üç model kayıtlara girmez, canlı sicilde yoktur. "
          "Yeniden üretim eşleşirse dondurma ayrı görevle yapılır (hücreler 99 arzdan, kesim 2026-08-19; bu kodun "
          "`borsai.ceiling_path.fit_params` yolu, `tests/test_faz4_ceiling_path.py`'de geçici dizine deneme dondurmasıyla sınanır).")
        return
    if tg["triggered"]:
        if len(frozen_ids) != 3:
            raise ValueError(f"çok iyi tetiklendi; üç model birlikte dondurulur, dondurulan: {frozen_ids}")
        w("**Donduruldu — §6'nın istediği bağımsız yeniden üretimden sonra.** \"Beklentiden çok iyi\" denetimi tetiklendiği "
          "için dondurma, ilk uygulamayı görmeyen ayrı bir oturumun (Fable) yalnız şartnameden, `borsai` import etmeden "
          f"yaptığı sıfırdan yeniden üretime bağlıydı. Sonuç ({REPRO['date']}, `{REPRO['doc']}`): üç ledger'ın 870 (fold × ufuk) "
          "hücresinin hepsinde return, p_up, q10, q90 ve mean için **maks |Δ| = 0** (eşik 1e-9); §6'nın 36 satırında fark, "
          "aralık uçları ve n için **Δ = 0**; sızıntı yok (her fold'da hücredeki en son seans < kesim), S_k yeniden fit "
          "edilmemiş (870/870 kaynak ledger'la aynı); hüküm üç model için **FREEZE_OK**. Duyarlılık (N_MIN 5/20, tek grup, "
          "havuzsuz): birincil fark −0.112 … −0.122, aralık üst ucu −0.070 … −0.077 — hüküm değişmiyor; dondurulan model "
          "şartnamedeki v0'dır. Dondurma temiz ağaçta yapıldı (kayıtlarda `borsai_dirty` false); JSON'lar `models/` altına, "
          "kayıtları `models/INDEX.json`'un **sonuna** eklendi, ilk 16 kayıt değişmedi. Altın ledger'lar bayt olarak "
          "korundu (yeni sütun eklenmedi): denetlenen dosyalar bunlardır.")
        w("")
    w("| model_id | Dosya sha256 (ilk 12) | Gömülü seri modeli | Seri sha256 (ilk 12) | Fiyat alanı | Hücre gözlemi | "
      "Z m = 1..10 | B m = 1..9 | Hücre kesimi |")
    w("|---|---|---|---|---|---|---|---|---|")
    index = json.loads((ROOT / "models" / "INDEX.json").read_text(encoding="utf-8"))
    sha = {e["model_id"]: e["sha256"] for e in index["models"]}
    for m in (MAIN, ZERO, PB):
        if m not in models:
            w(f"| `{m}` | dondurulmadı | | | | | | | |")
            continue
        p = models[m]
        pbk = p["post_break"]
        w(f"| `{m}` | `{sha[m][:12]}` | `{p['survival_model_id']}` | `{p['survival_model_sha256'][:12]}` | "
          f"`{p['limit_path']['price_field']}` | {pbk['n_obs']} | {[pbk['cell_n']['Z'][str(k)] for k in range(1, 11)]} | "
          f"{[pbk['cell_n']['B'][str(k)] for k in range(1, 10)]} | {pbk['cutoff_date']} ({pbk['n_ipo']} arz) |")
    w("")
    w(f"Fiyat alanı: `{PB}` limit yolunu **planlanan** fiyattan kurar (PB girdisi `ipo_price_try`, SPK onaylı "
      "izahnamedeki fiyat), kesin arz fiyatından değil (SPEC_DEVIATIONS F4, F15); ana model ve sıfır model kesin arz "
      "fiyatını (`ipo_price_tl`) kullanır. Hücrelerin baz fiyatı üç modelde de eğitim arzlarının resmi kesin arz "
      "fiyatıdır. H99'da planlanan fiyat 99/99 arzda kesin fiyata eşitti; canlıda ayrışabilir.")


def render_faz4(w, models: dict[str, Any], log_path: Path, runs: Optional[dict] = None, faz4_dir: Path = GOLDEN_FAZ4_DIR) -> None:
    runs = runs if runs is not None else rf.load_runs()
    runs4 = load_faz4_runs(faz4_dir)
    manifest = json.loads((Path(faz4_dir) / "MANIFEST.json").read_text(encoding="utf-8"))
    w("## Faz 4: tavan yolu modelleri (Fable şartnamesi, docs/specs_faz4/)")
    w("")
    w("**Terazi:** aşağıdaki her sayı **backtest**tir (retrospektif walk-forward, H99) ve **tasarıma maruzdur** (§10: grup ayrımı, "
      "N_MIN ve havuzlama sırası H99 kırılma sonrası ölçümleri görüldükten sonra seçildi); kanıt değeri düşüktür. Asıl ölçüm "
      "prospektiftir. 2026-08-06 sonrası listelenen ilk 7 arz (CITAS…NETGL) bu modeller için **RETRO**'dur; bu 7 arz için "
      "tavan yolu kaydı yazılmadı ve canlı sicilde bu modellerin satırı yoktur. \"Geçiyor\" yalnız aralık 0'ı dışlıyorsa yazılır.")
    w("")
    w(f"Şartname: `{SPEC_DOCUMENTS_FAZ4['SPEC_CEILING_PATH_V0']['path']}` (sha256 "
      f"`{SPEC_DOCUMENTS_FAZ4['SPEC_CEILING_PATH_V0']['sha256'][:12]}…`, commit 52e1567, uygulamadan önce push edildi). Üç model, "
      "yeni serbest parametre 0; seri bileşeni S_k dondurulmuş tavan modellerinden aynen (gömülü, sha'sı INDEX'le aynı).")
    w("")
    w("| Plan | Model | S_k kaynağı (Faz 1B altın ledger'ı) | Hücre kesimi |")
    w("|---|---|---|---|")
    for m, p in FAZ4_RUNS:
        spec = MODEL_SPECS[m]
        w(f"| `{p}` | `{m}` | `{spec['survival_ledger']['path'].split('/')[-1]}` (`{spec['survival_ledger']['sha256'][:12]}`) | "
          + ("B(k) ilk talep toplama günü" if spec["limit_path"]["price_field"] == "ipo_price_try" else "T ilk işlem günü") + " |")
    w("")
    w("Yöntem: fold kümesi ve sırası kaynak tavan ledger'ınınkidir; her fold'da S_1..S_10 ledger'dan okunur (yeniden fit yok), "
      "kırılma sonrası hücreler 99 arzdan yalnız seans tarihi < kesim olan gözlemlerle kurulur (§3). Tahmin = karışımın medyanı "
      "(MAE), p_up = P(R_h > 0) (Brier). Eşleşik fark = model − karşılaştırılan, iki tarafın da skorlandığı test arzları; %95 aralık "
      f"blok bootstrap (ilk işlem ayı blokları, {mx.BOOTSTRAP_REPS} tekrar, `random.Random({mx.BOOTSTRAP_SEED})`; SPEC_DEVIATIONS C7).")
    w("")
    w("Etiket kuralları (sonuçlar görülmeden kodda sabitlendi, `borsai/report_faz4.py: OPERATIONAL_RULES_FAZ4`):")
    w("")
    for rule in OPERATIONAL_RULES_FAZ4:
        w(f"- {rule}")
    w("")

    evaluated = evaluate_expectations(runs, runs4)
    tg = too_good(evaluated)
    prim = tg["primary"]["result"]
    w("### Birincil hücre")
    w("")
    w(f"`ceiling_path_v0` − `base_train_median`, D5 getiri MAE (önceden ilan edilen tek birincil hücre): **fark {_s(prim['mean'])}, "
      f"%95 aralık {_ci(prim)}, n = {prim['n']}** ({prim['n_months']} ay); model {_f(prim['model_metric'])}, kural "
      f"{_f(prim['rule_metric'])}; model iyi / kural iyi / eşit {prim['model_better_n']} / {prim['rule_better_n']} / "
      f"{prim['tie_n']}. Hüküm (backtest): {rf.VERDICT[prim['verdict']]}. §6 beklentisi −0.090 … −0.020 → "
      f"**{tg['primary']['label']}**.")
    w("")
    w("**Beklentiden çok iyi denetimi (§6):** " + ("**TETİKLENDİ** (" + str(len(tg["reasons"])) + " koşul) — "
                                                 + "; ".join(tg["reasons"]) + ". §6 gereği modeller **dondurulmadı**; "
                                                 "farklı elle sıfırdan yeniden üretim gerekir (aşağıda \"Dondurma\")."
                                                 if tg["triggered"] else "tetiklenmedi (birincil fark ≥ −0.120, aralığın üst ucu ≥ "
                                                 "−0.060; hiçbir D3/D5/D10 satırında fark alt uç − 0.03'ün altında değil)."))
    w("")
    w("### §6 beklentisi ile gerçekleşen (satır satır)")
    w("")
    _expectation_section(w, evaluated, d1_tie(runs, runs4))
    w("")
    w("### Başarısızlık tanımları (§6)")
    w("")
    _failure_section(w, failures(runs, runs4))
    w("")
    w("### `ceiling_path_v0`: bütün hücreler (§5; birincil dışındakiler keşif)")
    w("")
    _comparison_table(w, MAIN, [("MAE", "base_always_ceiling"), ("MAE", "base_train_median"), ("MAE", "v1_5_h99"), ("MAE", ZERO),
                                ("Brier", "base_rate"), ("Brier", "base_last10_rate"), ("Brier", "v1_5_h99"), ("Brier", ZERO)],
                      runs, runs4, note=_primary_note)
    w("")
    w("Kendi skorlanabilir kümesinde (h = 2, 4, 6..9 yalnız bilgi; gerçekleşen R_h SESSIONS kapanışlarından):")
    w("")
    _own_table(w, runs4[MAIN])
    w("")
    _cells_summary(w, runs4[MAIN])
    w("")
    w("### `ceiling_path_v0@INF` (sıfır model, MECHANICS_BASE)")
    w("")
    _comparison_table(w, ZERO, [("MAE", "base_train_median"), ("MAE", "base_always_ceiling"), ("Brier", "base_rate"),
                                ("Brier", "base_last10_rate")], runs, runs4)
    w("")
    _own_table(w, runs4[ZERO])
    w("")
    w("### `pb_ceiling_path_v0` (PB varyantı; kesim B(k))")
    w("")
    _comparison_table(w, PB, [("MAE", "pb_v0"), ("MAE", "base_train_median"), ("MAE", "base_always_ceiling"), ("Brier", "pb_v0"),
                              ("Brier", "base_rate"), ("Brier", "base_last10_rate")], runs, runs4)
    w("")
    w("Kurallar PB planının kendi koşularıdır (`…__pb`). Bilgi amaçlı (kesimleri farklı: B(k) ve T(k)), aynı test arzları:")
    w("")
    _comparison_table(w, PB, [("MAE", MAIN), ("MAE", ZERO), ("Brier", MAIN), ("Brier", ZERO)], runs, runs4, d10_note=False)
    w("")
    _own_table(w, runs4[PB])
    w("")
    _cells_summary(w, runs4[PB])
    w("")
    w("### Koşullu güncelleme (keşif): H99, j = 1..9")
    w("")
    w("SPEC_CEILING_PATH_V0 §7: seri j. günde sürüyorken koşullu RPS_j = (1/(10 − j)) Σ_{k>j} (S_k/S_j − 1[L ≥ k])² ve koşullu "
      "Brier (k = j + 1 \"yarın\", k = 10 \"sonuna kadar\"); Faz 1B tavan ledger'larından (yeni model değil). **Keşif, tasarıma "
      "maruz; koşulsuz tablolarla toplanmaz, farklı j'ler birleştirilmez** (aynı arz birden çok j'de bulunur). Aralık n ≥ 10 ise.")
    _conditional_section(w, runs)
    w("")
    w("### Dondurma")
    w("")
    _frozen_section(w, models, tg)
    w("")
    w("### Faz 4 koşuları ve deney günlüğü")
    w("")
    counts = rf.log_counts(log_path)
    cond = 0
    if log_path.exists():
        cond = sum(1 for x in log_path.read_text(encoding="utf-8").splitlines() if x.strip() and json.loads(x).get("kind") == "conditional_eval")
    w("| Koşu | Plan | Fold | Ledger sha256 (ilk 12) | Günlükteki koşu sayısı |")
    w("|---|---|---|---|---|")
    for m, p in FAZ4_RUNS:
        key = run_key(m, p)
        info = manifest["runs"][key]
        w(f"| `{key}` | {PLAN_KEYS[info['plan_id']]} | {len(runs4[key])} | `{info['ledger_sha256'][:12]}` | {counts[key]} |")
    w("")
    w(f"Koşullu keşif (`kind: conditional_eval`) günlük satırı: {cond}.")
    w("")
    w(f"Bu bölümün sayıları bağımsız olarak yeniden üretildi: {REPRO['date']}, ilk uygulamayı görmeyen ayrı oturum, "
      f"maks |Δ| = 0; ayrıntı ve ham çıktılar `{REPRO['dir']}`.")

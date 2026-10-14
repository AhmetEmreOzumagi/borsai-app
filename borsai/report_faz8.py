"""docs/MODELS.md'nin Faz 8 bölümü: kırılma akşamı modeli `break_floor_v0` (kural satırı `break_floor_v0@ZERO`; SPEC_BREAK_V0, KARARLAR).

Girdi: docs/faz8/backtest/ (resmi koşunun fold ledger'ı, üç duyarlılık ledger'ı, iki nihai fit önizlemesi, MANIFEST), experiments/log.jsonl
ve şartnamenin §6 beklenti tablosu (dosyadan AYNEN okunur; satır sırası ve metni denetlenir). Dizin yoksa bölüm üretilmez (commit A:
kod ve kurallar, sonuç yok).

Ölçek: Brier (kırpmasız), F1 birincil, F2 ikincil; H99 walk-forward, `scale = backtest_break`; backtest terazisi, tasarıma maruz (§12).
Canlı terazi (`live_break`, makine sıralı) bu bölümde yoktur ve hiçbir tabloda toplanmaz.

Değerlendirme kuralları (`specs.FAZ8_RULES`, `specs.OPERATIONAL_RULES_FAZ8`) bu dosya yazılırken, sonuçlar görülmeden (commit A)
sabitlendi; metin bölümde aynen yazılır (Faz 5 H16 ve Faz 7C T6 kalıbı).

Dondurma notu (BORSAI_FAZ8_FREEZE_20261002): models/INDEX_POST_BREAK.json iki kimliği listeleyince bölümün sonuna "### Dondurma"
yazılır; Fable'ın yeniden üretim sayıları `REPRO` sözlüğünde (kaynak AUDIT bölümüyle; testli), `@ZERO` hücresi ledger'dan.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from . import post_break as pbk
from .provenance import ROOT
from .specs import (FAZ8_MODEL_IDS, FAZ8_RULES, FAZ8_SENSITIVITIES, OPERATIONAL_RULES_FAZ8, POST_BREAK_MODEL_SPECS,
                    SPEC_DOCUMENTS_FAZ8)

GOLDEN_DIR = pbk.GOLDEN_DIR
SPEC_PATH = ROOT / SPEC_DOCUMENTS_FAZ8["SPEC_BREAK_V0"]["path"]
MODEL_ID, ZERO_ID = FAZ8_MODEL_IDS
R = FAZ8_RULES

POS_INSIDE, POS_BELOW, POS_ABOVE = "aralık içinde", "altında", "üstünde"
TOO_GOOD = "beklentiden çok iyi"
HELD, NOT_HELD = "tuttu", "tutmadı"
VERDICT_BACKTEST = {"MODEL_DAHA_IYI": "aralık 0'ın altında", "KURAL_DAHA_IYI": "aralık 0'ın üstünde",
                    "AYIRT_EDILEMIYOR": "aralık 0'ı içeriyor"}

# §6 "Aralık 0'ı" sütunu -> kategori (kesin kısım hükmü belirler; ifadenin tamamı ayrı sütunda).
CI_CATEGORY = {
    "dışlaması olası": "MAY_EXCLUDE_NEG",
    "dışlaması olası, garanti değil (alt uç ≤ 0)": "MAY_EXCLUDE_NEG",
    "içerir": "INCLUDES",
    "içerir ya da negatif dışlar": "NOT_POS",
    "pozitif dışlar ya da içerir (alt uç ≥ 0)": "NOT_NEG",
    "—": None,
}
CI_FIRM_TEXT = {"MAY_EXCLUDE_NEG": "alt uç ≤ 0", "INCLUDES": "alt ≤ 0 ≤ üst", "NOT_POS": "alt uç ≤ 0", "NOT_NEG": "üst uç ≥ 0"}
CI_FULL_TEXT = {"MAY_EXCLUDE_NEG": "üst uç < 0", "INCLUDES": "0'ı içerir", "NOT_POS": "alt uç ≤ 0", "NOT_NEG": "üst uç ≥ 0"}

# §6 tablosu: (Hücre, Karşılaştırılan) düz metin (yıldız ve ters tırnak atılmış) -> değerlendirici. Sıra şartnamedeki gibidir.
EXPECTED_6: tuple[tuple[str, str, dict[str, Any]], ...] = (
    ("F1 Brier (BİRİNCİL)", "PRODUCT_BREAK_FLOOR", {"kind": "diff", "cell": "F1_product", "primary": True}),
    ("F1 Brier", "@ZERO", {"kind": "diff", "cell": "F1_zero"}),
    ("F1 Brier", "base_floor_by_type", {"kind": "diff", "cell": "F1_by_type"}),
    ("F2 Brier", "PRODUCT_BREAK_FLOOR", {"kind": "diff", "cell": "F2_product"}),
    ("F2 Brier", "@ZERO", {"kind": "diff", "cell": "F2_zero"}),
    ("bilgi: PRODUCT − @ZERO (F1)", "—", {"kind": "diff", "cell": "info_product_zero_F1"}),
    ("Kalibrasyon", "ort(p_F1) − gözlenen F1 oranı", {"kind": "calibration"}),
    ("Katsayı işareti", "β_floor (F1)", {"kind": "sign_floor"}),
    ("Katsayı işareti", "β_turn (F1)", {"kind": "sign_turn"}),
    ("Seçilen C", "nihai fit F1", {"kind": "final_C"}),
    ("Seçilen C", "fold'lar F1", {"kind": "zero_share"}),
    ("n", "F1 birincil eşleşik (yakın dönem)", {"kind": "n", "cell": "F1_product", "range": R["n_F1_range"]}),
    ("n", "F2 (yakın dönem)", {"kind": "n", "cell": "F2_product", "range": R["n_F2_range"]}),
)
EXPECTED_6_HEADER = "| Hücre | Karşılaştırılan | Beklenen fark | Aralık | Aralık 0'ı | Gerekçe (kısa) |"
CELL_TITLES = {
    "F1_product": ("F1", "`PRODUCT_BREAK_FLOOR`", "BİRİNCİL"),
    "F1_zero": ("F1", "`break_floor_v0@ZERO`", "ilan edilmiş ikincil"),
    "F2_product": ("F2", "`PRODUCT_BREAK_FLOOR`", "ilan edilmiş ikincil"),
    "F2_zero": ("F2", "`break_floor_v0@ZERO`", "ilan edilmiş ikincil"),
    "F1_by_type": ("F1", "`base_floor_by_type`", "ilan edilmiş ikincil (lojistiğin payı)"),
    "info_product_zero_F1": ("F1", "`PRODUCT_BREAK_FLOOR − @ZERO`", "bilgi (ürün tek orandan kötü mü)"),
}


# ---------------------------------------------------------------------------
# §6 tablosu ve kurallar
# ---------------------------------------------------------------------------

def _plain(text: str) -> str:
    return text.replace("**", "").replace("`", "").strip()


def _num(text: str) -> float:
    return float(_plain(text).replace("−", "-").replace("+", ""))


def parse_interval(text: str) -> tuple[float, float]:
    """'[−0.140, −0.020]' -> (−0.140, −0.020)."""
    lo, hi = (_num(p) for p in _plain(text).strip("[]").split(","))
    return lo, hi


def expectation_rows(spec_text: Optional[str] = None) -> list[dict[str, Any]]:
    """§6 tablosunun 13 satırı aynen; her satır `EXPECTED_6`'daki değerlendiriciyle eşlenir (sıra ve metin denetlenir)."""
    from .report_faz4 import _split_row

    text = spec_text if spec_text is not None else SPEC_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(EXPECTED_6_HEADER)]
    if len(starts) != 1:
        raise ValueError(f"§6 tablo başlığı {len(starts)} kez bulundu")
    out = []
    for line in lines[starts[0] + 2:]:
        if not line.startswith("|"):
            break
        hucre, karsi, beklenen, aralik, sifir, gerekce = _split_row(line)
        out.append({"raw": {"hucre": hucre, "karsilastirilan": karsi, "beklenen": beklenen, "aralik": aralik, "sifir": sifir,
                            "gerekce": gerekce}})
    if len(out) != len(EXPECTED_6):
        raise ValueError(f"§6 tablosu {len(out)} satır; beklenen {len(EXPECTED_6)}")
    for row, (cell, comp, ev) in zip(out, EXPECTED_6):
        if (_plain(row["raw"]["hucre"]), _plain(row["raw"]["karsilastirilan"])) != (cell, comp):
            raise ValueError(f"§6 satırı beklenenden farklı: {row['raw']}")
        row.update(ev)
        row.setdefault("primary", False)
        row["ci_category"] = CI_CATEGORY[_plain(row["raw"]["sifir"])]
        if ev["kind"] == "diff":
            row["lo"], row["hi"] = parse_interval(row["raw"]["aralik"])
    return out


def position(d: float, lo: float, hi: float) -> str:
    """T6: farkın §6 aralığına göre yeri (kapalı aralık)."""
    if d < lo:
        return POS_BELOW
    if d > hi:
        return POS_ABOVE
    return POS_INSIDE


def position_text(pos: Optional[str]) -> str:
    if pos is None:
        return "—"
    return f"**{POS_BELOW} — {TOO_GOOD}**" if pos == POS_BELOW else f"**{pos}**"


def ci_firm_holds(category: Optional[str], ci: Optional[Sequence[float]]) -> bool:
    if category is None:
        return True
    if ci is None:
        return False
    lo, hi = ci
    return {"MAY_EXCLUDE_NEG": lo <= 0.0, "INCLUDES": lo <= 0.0 <= hi, "NOT_POS": lo <= 0.0, "NOT_NEG": hi >= 0.0}[category]


def ci_statement_holds(category: Optional[str], ci: Optional[Sequence[float]]) -> Optional[bool]:
    if category is None:
        return None
    if ci is None:
        return False
    lo, hi = ci
    return {"MAY_EXCLUDE_NEG": hi < 0.0, "INCLUDES": lo <= 0.0 <= hi, "NOT_POS": lo <= 0.0, "NOT_NEG": hi >= 0.0}[category]


def diff_label(row: Mapping[str, Any], cell: Optional[Mapping[str, Any]]) -> str:
    """Fark satırının hükmü (OPERATIONAL_RULES_FAZ8 3. madde)."""
    if cell is None:
        return "tutmadı (hücre yok)"
    d = cell["mean"]
    if d < row["lo"]:
        return "tutmadı (daha iyi)"
    if d > row["hi"]:
        return "tutmadı (daha kötü)"
    if row["ci_category"] is not None and cell.get("ci95") is None:
        return "tutmadı (aralık yok)"
    return HELD if ci_firm_holds(row["ci_category"], cell.get("ci95")) else "tutmadı (aralık)"


def too_good(cells: Mapping[str, Optional[Mapping[str, Any]]]) -> list[str]:
    """§6 "beklentiden çok iyi" tetikleri (hangileri tetiklendi)."""
    out = []
    p, z = cells.get("F1_product"), cells.get("F1_zero")
    if p is not None and p["mean"] < R["too_good_primary_diff"]:
        out.append(f"birincil fark < {R['too_good_primary_diff']:.3f}")
    if p is not None and p.get("ci95") is not None and p["ci95"][1] < R["too_good_primary_ci_hi"]:
        out.append(f"birincil aralığın üst ucu < {R['too_good_primary_ci_hi']:.3f}")
    if z is not None and z["mean"] < R["too_good_zero_diff"]:
        out.append(f"F1 − @ZERO farkı < {R['too_good_zero_diff']:.3f}")
    return out


def k1(cells: Mapping[str, Optional[Mapping[str, Any]]]) -> dict[str, Any]:
    """§8 aşama 1 ön eleme: birincil üst uç < 0 VE F1 − @ZERO üst uç < 0."""
    legs = {}
    for key, name in (("F1_product", "birincil (− ürün)"), ("F1_zero", "− @ZERO")):
        c = cells.get(key)
        legs[name] = c is not None and c.get("ci95") is not None and c["ci95"][1] < 0.0
    return {"holds": all(legs.values()), "legs": legs}


def failures(cells: Mapping[str, Optional[Mapping[str, Any]]], final_C: Any, zero_share: Optional[float],
             calib: Optional[Mapping[str, Any]]) -> dict[str, bool]:
    """§6 başarısızlık tanımları (a)–(d)."""
    z, p = cells.get("F1_zero"), cells.get("F1_product")
    zc = None if z is None else z.get("ci95")
    return {
        "a": zc is None or zc[0] <= 0.0 <= zc[1],
        "b": p is not None and p.get("ci95") is not None and p["ci95"][0] > 0.0,
        "c": final_C == "ZERO" or (zero_share is not None and zero_share >= R["fail_c_zero_share"]),
        "d": calib is not None and calib["n"] >= R["fail_d_min_n"] and abs(calib["diff"]) > R["fail_d_calibration"],
    }


FAILURE_TEXT = {"a": "basit kuraldan ayırt edilemiyor", "b": "zarar veriyor (ürünün cevabından kötü)",
                "c": "özellikler bilgi eklemiyor", "d": "düzey kayması"}


def _combine(parts: Sequence[tuple[str, bool]]) -> str:
    held = [ok for _, ok in parts]
    if all(held):
        return HELD
    if not any(held):
        return NOT_HELD
    return "kısmen (tutmayan: " + "; ".join(name for name, ok in parts if not ok) + ")"


def _C(x: Any) -> Any:
    return x if x in (None, "", "ZERO") else float(x)


def fold_signs(rows: Sequence[Mapping[str, str]], head: str = "F1") -> dict[str, Any]:
    """β işaretleri: bütün F1 FIT_OK fold'larından C ≠ ZERO ve kolonu düşmemiş olanlar (paydada); düşen ve ZERO ayrıca sayılır."""
    ok = [r for r in rows if r["status"] == pbk.STATUS_FIT_OK and r[f"p_{head}"] != ""]
    zero = [r for r in ok if r[f"selected_C_{head}"] == "ZERO"]
    out: dict[str, Any] = {"n_ok": len(ok), "n_zero": len(zero)}
    for col, key in (("b_floor", "floor"), ("b_turnover", "turn")):
        usable, dropped = [], 0
        for r in ok:
            if r[f"selected_C_{head}"] == "ZERO":
                continue
            if col not in (json.loads(r[f"inner_table_{head}"]).get("columns") or []):
                dropped += 1
                continue
            usable.append(float(r[f"coef_{key}_{head}"]))
        out[key] = {"n": len(usable), "dropped": dropped, "pos": sum(1 for v in usable if v > 0), "neg": sum(1 for v in usable if v < 0)}
    return out


def zero_share(rows: Sequence[Mapping[str, str]], start: Optional[str] = pbk.NEAR_ERA_START) -> Optional[float]:
    ok = [r for r in rows if r["status"] == pbk.STATUS_FIT_OK and r["p_F1"] != "" and (start is None or r["first_trading_date"] >= start)]
    return None if not ok else sum(1 for r in ok if r["selected_C_F1"] == "ZERO") / len(ok)


def evaluate(rows: Sequence[Mapping[str, str]], preview: Mapping[str, Any], spec_text: Optional[str] = None) -> dict[str, Any]:
    """Bütün hücreler, §6 satırlarının hükmü, başarısızlık bayrakları, k1, "çok iyi" tetikleri."""
    cells = pbk.compute_cells(rows)
    near = cells["near"]
    calib = pbk.calibration(rows, "F1")
    head = preview["horizons"]["F1"]["p_floor"]
    final_C = head.get("C")
    coef = dict(zip(head.get("columns", []), head.get("coef", [])))
    signs = fold_signs(rows)
    zs = zero_share(rows)
    out_rows = []
    for row in expectation_rows(spec_text):
        kind = row["kind"]
        res: dict[str, Any] = {**row, "cell_value": None, "position": None, "label": None, "statement": None}
        if kind == "diff":
            c = near.get(row["cell"])
            res["cell_value"] = c
            res["position"] = None if c is None else position(c["mean"], row["lo"], row["hi"])
            res["label"] = diff_label(row, c)
            res["statement"] = ci_statement_holds(row["ci_category"], None if c is None else c.get("ci95"))
        elif kind == "calibration":
            ok = calib is not None and abs(calib["diff"]) <= R["calibration_expected"]
            res["cell_value"] = calib
            res["label"] = "tutmadı (hücre yok)" if calib is None else (HELD if ok else (
                "tutmadı (model yüksek)" if calib["diff"] > 0 else "tutmadı (model düşük)"))
        elif kind == "sign_floor":
            f = signs["floor"]
            share = None if f["n"] == 0 else f["pos"] / f["n"]
            res["cell_value"] = {"final": coef.get("b_floor"), "share": share, **f}
            res["label"] = _combine([("nihai fit β_floor > 0", (coef.get("b_floor") or 0.0) > 0.0),
                                     (f"fold payı ≥ %{R['floor_sign_share'] * 100:.0f}", share is not None and share >= R["floor_sign_share"])])
        elif kind == "sign_turn":
            v = coef.get("b_turnover")
            t = signs["turn"]
            res["cell_value"] = {"final": v, "share_neg": None if t["n"] == 0 else t["neg"] / t["n"], **t}
            res["label"] = HELD if v is not None and v < 0 else ("tutmadı (> 0)" if v is not None and v > 0 else "tutmadı (= 0)")
        elif kind == "final_C":
            res["cell_value"] = {"C": final_C}
            lo, hi = R["final_C_likely"]
            if final_C == "ZERO":
                res["label"] = "tutmadı (ZERO)"
            else:
                c = float(final_C)
                res["label"] = HELD if lo <= c <= hi else ("tutmadı (daha küçük C)" if c < lo else "tutmadı (daha büyük C)")
        elif kind == "zero_share":
            res["cell_value"] = {"share": zs}
            res["label"] = "tutmadı (fold yok)" if zs is None else (HELD if zs <= R["zero_share_max"] else NOT_HELD)
        elif kind == "n":
            c = near.get(row["cell"])
            n = 0 if c is None else c["n"]
            lo, hi = row["range"]
            res["cell_value"] = {"n": n}
            res["label"] = HELD if lo <= n <= hi else ("tutmadı (az)" if n < lo else "tutmadı (çok)")
        out_rows.append(res)
    return {"cells": cells, "rows6": out_rows, "calibration": calib, "final_C": final_C, "final_coef": coef, "signs": signs,
            "zero_share": zs, "failures": failures(near, final_C, zs, calib), "k1": k1(near), "too_good": too_good(near)}


# ---------------------------------------------------------------------------
# Veri
# ---------------------------------------------------------------------------

def golden_available(out_dir: Path = GOLDEN_DIR) -> bool:
    return pbk.golden_available(out_dir)


def load_faz8(out_dir: Path = GOLDEN_DIR) -> tuple[list[dict[str, str]], dict[str, list[dict[str, str]]], dict[str, Any],
                                                    dict[str, dict[str, Any]]]:
    """(ledger satırları, duyarlılık -> ledger satırları, MANIFEST, model -> önizleme)."""
    d = Path(out_dir)
    manifest = json.loads((d / "MANIFEST.json").read_text(encoding="utf-8"))
    rows = pbk.read_ledger(d / manifest["runs"][MODEL_ID]["file"])
    sens = {n: pbk.read_ledger(d / v["file"]) for n, v in manifest["sensitivities"].items()}
    previews = {m: json.loads((d / v["file"]).read_text(encoding="utf-8")) for m, v in manifest["final_fit_previews"].items()}
    return rows, sens, manifest, previews


def _log_entries(log_path: Path) -> list[dict[str, Any]]:
    if not Path(log_path).exists():
        return []
    return [json.loads(x) for x in Path(log_path).read_text(encoding="utf-8").splitlines() if x.strip()]


# ---------------------------------------------------------------------------
# Biçim
# ---------------------------------------------------------------------------

def _f(x: Optional[float], nd: int = 4) -> str:
    return "—" if x is None else f"{x:.{nd}f}"


def _s(x: Optional[float], nd: int = 4) -> str:
    return "—" if x is None else f"{x:+.{nd}f}"


def _ci(c: Optional[Mapping[str, Any]]) -> str:
    return "—" if c is None or c.get("ci95") is None else f"[{_s(c['ci95'][0])}, {_s(c['ci95'][1])}]"


def _wlt(c: Mapping[str, Any]) -> str:
    return f"{c['model_better_n']} / {c['rule_better_n']} / {c['tie_n']} (\\|fark\\| ≤ 1e-12: {c['tie_n_1e12']})"


def _pair_cells(c: Optional[Mapping[str, Any]]) -> list[str]:
    if c is None:
        return ["0", "—", "—", "—", "—", "—"]
    return [f"{c['n']} ({c['n_months']})", _f(c["a_metric"]), _f(c["b_metric"]), _s(c["mean"]), _ci(c), _wlt(c)]


def _verdict(c: Optional[Mapping[str, Any]]) -> str:
    return VERDICT_BACKTEST.get(c and c.get("verdict"), "—")


def _row_value(r: Mapping[str, Any]) -> tuple[str, str, str]:
    """(gerçekleşen, %95 aralık, n (ay)) metinleri."""
    v = r["cell_value"]
    kind = r["kind"]
    if kind == "diff":
        return (_s(v["mean"]) if v else "—", _ci(v), f"{v['n']} ({v['n_months']})" if v else "0")
    if kind == "calibration":
        return (("—", "—", "0") if v is None else
                (f"{_s(v['diff'])} (ort p {_f(v['mean_p'])}, gözlenen {_f(v['observed'])})", "—", str(v["n"])))
    if kind == "sign_floor":
        share = "—" if v["share"] is None else f"%{100 * v['share']:.0f}"
        return (f"nihai {_s(v['final'])}; fold'larda > 0: {v['pos']}/{v['n']} ({share}; düşen {v['dropped']})", "—", str(v["n"]))
    if kind == "sign_turn":
        share = "—" if v["share_neg"] is None else f"%{100 * v['share_neg']:.0f}"
        return (f"nihai {_s(v['final'])}; fold'larda < 0: {v['neg']}/{v['n']} ({share}; düşen {v['dropped']})", "—", str(v["n"]))
    if kind == "final_C":
        return (str(v["C"]), "—", "—")
    if kind == "zero_share":
        return ("—" if v["share"] is None else f"%{100 * v['share']:.0f}", "—", "—")
    return (str(v["n"]), "—", "—")


def _statement(r: Mapping[str, Any]) -> str:
    cat = r.get("ci_category")
    if cat is None or r["kind"] != "diff":
        return "—"
    held = r["statement"]
    extra = ""
    if cat == "NOT_NEG" and r["cell_value"] is not None and r["cell_value"].get("ci95") is not None:
        extra = f"; parantez (alt uç ≥ 0): {'evet' if r['cell_value']['ci95'][0] >= 0.0 else 'hayır'}"
    return f"{CI_FULL_TEXT[cat]}: {'evet' if held else 'hayır'}{extra}"


def _fmt_C(x: Any) -> str:
    return str(x) if isinstance(x, str) else f"{float(x):g}"


def _C_sort(item: tuple[str, int]) -> float:
    return -1.0 if item[0] == "ZERO" else float(item[0])


def fold_summary(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    out: dict[str, Any] = {"n": len(rows), "statuses": dict(Counter(r["status"] for r in rows))}
    for head in ("F1", "F2"):
        ok = [r for r in rows if r[f"p_{head}"] != ""]
        near = [r for r in ok if r["first_trading_date"] >= pbk.NEAR_ERA_START]
        st = Counter(json.loads(r[f"inner_table_{head}"])["status"] for r in rows)
        out[head] = {"n_ok": len(ok), "n_near": len(near), "near_blocks": len({r["first_trading_date"][:7] for r in near}),
                     "statuses": dict(st), "C": dict(Counter(r[f"selected_C_{head}"] for r in ok)),
                     "events_near": sum(1 for r in near if r[f"realized_{head}"] == "1")}
    out["product_insufficient"] = sum(1 for r in rows if r["product_status"] != "OK")
    out["clipped"] = sum(1 for r in rows if r["test_b_turnover_clipped"] == "1")
    out["floor_dropped"] = sum(1 for r in rows if r["dropped"] not in ("", "[]"))
    out["structural_zero"] = dict(Counter(r["b"] for r in rows if r["structural_zero_D10"] == "1"))
    return out


def _log_count(entries: Sequence[Mapping[str, Any]], kind: str, model_id: str) -> int:
    return sum(1 for e in entries if e.get("kind") == kind and e.get("model_id") == model_id)


# ---------------------------------------------------------------------------
# Dondurma notu (BORSAI_FAZ8_FREEZE_20261002; Faz 5 / 7C `_frozen_section` kalıbı)
# ---------------------------------------------------------------------------

POST_BREAK_INDEX_PATH = ROOT / "models" / "INDEX_POST_BREAK.json"
# Fable'ın bağımsız yeniden üretiminin (docs/fable_faz8_audit/AUDIT.md) sayıları: anahtar -> (değer, AUDIT bölümü). Her değer o bölümün
# metninde birebir geçer (tests/test_faz8_frozen.py). `@ZERO` hücresi bu sözlükte değildir: ledger'dan hesaplanır (yukarıdaki tablo).
REPRO: dict[str, tuple[str, str]] = {
    "verdict": ("REPRO_OK", "§0"),
    "date": ("2026-10-02", "başlık"),
    "head": ("c84ba64", "başlık"),
    "max_abs": ("0.000e+00", "§0"),
    "tol": ("1e-9", "§0"),
    "cell_parity": ("87/87", "§0"),
    "mutations": ("13/13", "§6"),
    "tick_product_floor": ("0.199", "§2a"),
    "exact_product_floor": ("0.115", "§2a"),
    "tick_diff": ("−0.1611", "§2b"),
    "tick_ci": ("[−0.2193, −0.1013]", "§2b"),
    "above_floor_product": ("≈ 0.57", "§2d"),
    "above_floor_observed": ("0.12", "§2d"),
    "w_rounding": ("≈ 0.03", "§8"),
    "w_zero_cell": ("−0.028 [−0.045, −0.007]", "§8"),
    "w_beta_turn": ("+0.063", "§8"),
    "w_calib_above": ("+0.129", "§8"),
    "w_calib_floor": ("−0.086", "§8"),
    "w_calib_2025": ("+0.204 (n 16)", "§8"),
    "w_regime_start": ("2026-09-16", "§8"),
    "w_n_F2": ("52 < 55", "§8"),
}
REPRO_DIR = "docs/fable_faz8_audit/"
FREEZE_ROLE = {MODEL_ID: "model", ZERO_ID: "kural satırı ve karşılaştırıcı (`@ZERO`)"}
PROMOTION_LABEL = "ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0"


def _r(key: str) -> str:
    return REPRO[key][0]


def frozen_entries(index_path: Path = POST_BREAK_INDEX_PATH) -> list[dict[str, Any]]:
    """models/INDEX_POST_BREAK.json'daki Faz 8 kayıtları (FAZ8_MODEL_IDS sırasıyla); dosya yoksa (dondurmadan önce) boş."""
    if not Path(index_path).exists():
        return []
    index = json.loads(Path(index_path).read_text(encoding="utf-8"))
    return [e for e in index["models"] if e["model_id"] in FAZ8_MODEL_IDS]


def card_warnings() -> tuple[str, ...]:
    """Kart uyarıları (AUDIT §8 "Gösterilecek uyarılar" 1–7, kısaltılmış; sayılar aynen). Uygulama EK 5 kartı bunları kullanır."""
    return (
        f"birincil farkın büyüklüğü karşılaştırıcının zayıflığındandır (ürün taban üstü kırılmaya {_r('above_floor_product')} der; eşik "
        f"yuvarlaması {_r('w_rounding')} ekler); tek orana karşı kazanç küçük: {_r('w_zero_cell')}.",
        f"β_turn işareti beklentinin tersi ({_r('w_beta_turn')}); el değiştirme bilgi eklemiyor (duyarlılıklar, `by_type`).",
        "F2 − `@ZERO` ≈ 0: iki ardışık taban için model tek orandan ayırt edilemiyor.",
        f"kalibrasyon sınıfa göre: taban üstü kırılmada model yüksek ({_r('w_calib_above')}), taban kırılmasında düşük "
        f"({_r('w_calib_floor')}); 2025 kohortunda {_r('w_calib_2025')}.",
        f"rejim `FON_KRIZI_2026` (D_1 ≥ {_r('w_regime_start')}; bitiş açık, KARARLAR C4): önceden yazılı okuma \"model tabanı az tahmin "
        "eder\".",
        "`BAND_RULE_MISMATCH` olunca yastık rozeti gizli.",
        f"eski dönem terazisi yok (proje sahibi kararı); n F2 {_r('w_n_F2')} beklentisi.",
    )


def _frozen_section(w: Callable[[str], None], entries: Sequence[Mapping[str, Any]], near: Mapping[str, Any], k1_holds: bool) -> None:
    """Faz 8 bölümünün sonunda "### Dondurma" (yalnız INDEX_POST_BREAK iki kimliği listeleyince)."""
    if [e["model_id"] for e in entries] != list(FAZ8_MODEL_IDS):
        return
    doc = SPEC_DOCUMENTS_FAZ8["SPEC_BREAK_V0"]
    z = near.get("F1_zero")
    w("")
    w("### Dondurma")
    w("")
    w(f"**Donduruldu, bağımsız yeniden üretimden sonra.** İlk uygulamayı görmeyen ayrı bir oturum (Fable) şartnameden, `borsai` import "
      f"etmeden sıfırdan yeniden üretti ({_r('date')}, HEAD {_r('head')}): hüküm **{_r('verdict')}**; resmi ledger, üç duyarlılık "
      f"ledger'ı ve iki nihai fit önizlemesi bit-eşit, maks |Δ| = {_r('max_abs')} (eşik {_r('tol')}); Faz 4 hücre paritesi "
      f"{_r('cell_parity')}; {_r('mutations')} mutasyon kırmızı; sızıntı yok. Ayrıntı ve ham çıktılar `{REPRO_DIR}`. Donmuş dosyalar "
      "yukarıdaki nihai fit önizlemelerinin aynısıdır (`created_at`, `code_version`, `runtime` dışında `==`); dondurma temiz ağaçta "
      f"yapıldı (`borsai_dirty` false). Şartname belgesi donmuş JSON'larda `spec_document.sha256` = `{doc['sha256'][:12]}…` "
      f"(`{doc['path']}`). Yukarıdaki 'dondurulmadı' ifadeleri backtest anının kaydıdır.")
    w("")
    w("| model_id | Dosya | sha256 | Dondurma tarihi (yerel saat; kanıt push'tur) | Rol |")
    w("|---|---|---|---|---|")
    for e in entries:
        w(f"| `{e['model_id']}` | `models/{e['file']}` | `{e['sha256']}` | {e['frozen_at'][:10]} | {FREEZE_ROLE[e['model_id']]} |")
    w("")
    w("- **Dizin:** `models/INDEX_POST_BREAK.json` ayrı dizindir (iki giriş, `FAZ8_MODEL_IDS` sırası); `models/INDEX.json` ve "
      "`models/INDEX_POST_D1.json` değişmedi. Listeleme öncesi kayıt ve POST_D1 kaydı bu modelleri okumaz (`freeze.run_model` → "
      "`PARAMS_INVALID`).")
    if k1_holds:
        w(f"- **Öne çıkan durum** (§8 aşama 1): k1 sağlandı (birincil ve `@ZERO` aralıklarının üst uçları < 0). `{MODEL_ID}`'ın p_F1'i "
          f"kartta öne çıkarılabilir; etiket aynen: \"{PROMOTION_LABEL}\". `@ZERO` oranı ve ürün türevi yan yana.")
    else:
        w("- **Öne çıkan durum** (§8 aşama 1): k1 sağlanmadı; kart modeli ikincil satırda, `@ZERO` oranı ve ürün türeviyle yan yana "
          "gösterir (\"basit kuraldan ayırt edilemiyor (backtest)\").")
    w("- **Canlı:** makine sıralı (`MACHINE_SEQUENCED`), ölçek `live_break`; hiçbir ölçekle toplanmaz. Skorlama ve makine kayıt "
      "yazıcısı ayrı görevdir. Zaman kanıtı dondurma commit'inin push'udur. Bugünkü 7 arz bu model için RETRO'dur (§9.3).")
    w("- **Bilgi notları** (proje sahibi kararı, SPEC_DEVIATIONS N24; hücre tanımı değişmez):")
    w(f"  - (i) Ürün türevi kesin eşikle hesaplanır. Bir adım toleransla taban kırılmasında ürünün ortalaması {_r('tick_product_floor')} "
      f"olur (kesin eşikte {_r('exact_product_floor')}). Birincil fark {_r('tick_diff')} {_r('tick_ci')}; aralık yine 0'ın altında.")
    w(f"  - (ii) Ürün taban üstü kırılmaya {_r('above_floor_product')} der, gözlenen {_r('above_floor_observed')}'dir. Birincil farkın "
      f"büyüklüğü karşılaştırıcının zayıflığından gelir; tek orana karşı kazanç küçüktür: {_s(z and z['mean'])} {_ci(z)}.")
    w("- **Kart uyarıları** (EK 5 kullanacak; AUDIT §8, kısaltılmış):")
    for i, text in enumerate(card_warnings(), 1):
        w(f"  {i}. {text}")


def render_faz8(w: Callable[[str], None], log_path: Path, *, out_dir: Path = GOLDEN_DIR, spec_text: Optional[str] = None,
                index_path: Path = POST_BREAK_INDEX_PATH) -> None:
    """Resmi koşu dizini yoksa hiçbir şey yazmaz. Dondurma notu yalnız resmi dizinle ve INDEX_POST_BREAK iki kimliği listeleyince,
    bölümün sonunda."""
    if not golden_available(out_dir):
        return
    rows, sens, manifest, previews = load_faz8(out_dir)
    ev = evaluate(rows, previews[MODEL_ID], spec_text)
    near = ev["cells"]["near"]
    doc, dec = SPEC_DOCUMENTS_FAZ8["SPEC_BREAK_V0"], SPEC_DOCUMENTS_FAZ8["KARARLAR_FAZ8"]
    entries = _log_entries(log_path)
    fs = fold_summary(rows)
    w("## Faz 8: kırılma akşamı (Fable şartnamesi, docs/specs_faz8/)")
    w("")
    w("**Terazi ve ölçek:** aşağıdaki her sayı **backtest**tir (retrospektif walk-forward, H99'un 82 kırılma akşamı, "
      "`scale = backtest_break`) ve **tasarıma maruzdur** (hipotez \"kırılma türü sonraki günleri ayırır\" ve iki özellik H99'dan "
      "doğdu; SPEC_BREAK_V0 §12); H99 backtest'i yalnız ön elemedir. Ölçek: Brier (kırpmasız), F1 = ertesi işlem görmüş seansın "
      "kapanışı alt limitte (birincil), F2 = iki ardışık taban (ikincil). Modeller **henüz dondurulmadı** (Fable'ın sıfırdan yeniden "
      "üretiminden sonra ayrı görev; `models/INDEX_POST_BREAK.json`); canlı sicilde satırları yoktur. Canlı terazi (`live_break`, "
      "makine sıralı) ve eski dönem bu bölümde yoktur ve hiçbir tabloda toplanmaz.")
    w("")
    w(f"Şartname: `{doc['path']}` (sha256 `{doc['sha256'][:12]}…`, commit 7d78d43, uygulamadan önce) ve bağlayıcı kararlar "
      f"`{dec['path']}` (sha256 `{dec['sha256'][:12]}…`; §C proje sahibi kararları C1–C5, 2026-10-01). Olay: b = L + 1 (ilk "
      "işlem görmüş tavan-dışı kapanış), kapsam b ∈ 1..9 (L = 0 dahil, C3); kırılma akşamı = D_b'nin THB yayımı. Model: başlık "
      "başına L2-lojistik (V1.6 C ızgarası, iç arz-bırak Brier; `fit.fit_fall_horizon`), özellikler `b_floor` (kapanış == alt limit, "
      "ham metin Decimal) ve `b_turnover` (ln(hacim / arz edilen pay), eğitim [p05, p95]'ine kırpma, z-skor). Kural satırı "
      "`break_floor_v0@ZERO` (fold'un eğitim oranı). D10 ≤ arz için model yok (C1); yastık kuralı `D10_STRUCTURAL_ZERO` kod, "
      "skorlanmaz. Bant varsayımı (±%10, içe yuvarlama, D1 baz fiyatı) rev. 54'e karşı doğrulandı (`docs/faz8/BANT_DOGRULAMA.md`). "
      "Uygulama yorumları SPEC_DEVIATIONS N.")
    w("")
    w("Plan (§7.2): test birimi b ≤ 9 olan her arz; kesim T = D_b'nin tarihi; başlık h için eğitim satırı ancak hedef seansı (F1: "
      "D_{b+1}, F2: D_{b+2}) T'den kesin önce; ≥ 10 satır, ≥ 5 olay, ≥ 5 olay-dışı. Ürün karşılaştırıcısının hücreleri test arzının "
      "ilk işlem gününe kesimli (`build_cells(cutoff = D_1(k))`; ürünün listeleme öncesi kaydının karşılığı); Faz 4 ledger'ının "
      f"{manifest['info']['faz4_cell_parity']} OK fold'unda hücre sayıları birebir.")
    w("")
    w("Değerlendirme kuralları (sonuçlar görülmeden kodda sabitlendi, `borsai/specs.py: OPERATIONAL_RULES_FAZ8`, `FAZ8_RULES`, "
      "commit A):")
    w("")
    for rule in OPERATIONAL_RULES_FAZ8:
        w(f"- {rule}")
    w("")
    w("### Kartlar")
    w("")
    w("| model_id | Rol | Özellikler | Eğitim | Fold (FIT_OK: F1 / F2) | Birincil (yakın dönem) | Ön eleme (k1) | Canlı |")
    w("|---|---|---|---|---|---|---|---|")
    p = near.get("F1_product")
    primary_txt = "—" if p is None else f"{_s(p['mean'])} {_ci(p)}, n = {p['n']}"
    k1_txt = "**sağlandı**" if ev["k1"]["holds"] else "sağlanmadı (" + ", ".join(k for k, v in ev["k1"]["legs"].items() if not v) + ")"
    for m in FAZ8_MODEL_IDS:
        spec = POST_BREAK_MODEL_SPECS[m]
        tr = previews[m]["training"]
        feats = ", ".join(spec["features"]) or "— (sabit)"
        role = "model (tek)" if m == MODEL_ID else "kural satırı (C = ZERO; aday değil)"
        folds = f"{fs['F1']['n_ok']} / {fs['F2']['n_ok']}" if m == MODEL_ID else "ledger'ın zero_F1 / zero_F2 sütunları"
        w(f"| `{m}` | {role} | {feats} | {tr['set']} (F1 {tr['n_F1']} / olay {tr['events_F1']}; F2 {tr['n_F2']} / olay "
          f"{tr['events_F2']}) | {folds} | {primary_txt if m == MODEL_ID else '—'} | {k1_txt if m == MODEL_ID else '—'} | "
          "n = 0 (dondurulmadı) |")
    w("")
    w("### Birincil hücre ve `@ZERO` hücresi (yakın dönem, ilk işlem ≥ 2024-01-01)")
    w("")
    w("| Hücre | Karşılaştırılan | n (ay) | model | karş. | fark | %95 aralık | model iyi / karş. iyi / eşit | aralık |")
    w("|---|---|---|---|---|---|---|---|---|")
    for key in ("F1_product", "F1_zero"):
        head, comp, role = CELL_TITLES[key]
        w(f"| {head} Brier **({role})** | {comp} | " + " | ".join(_pair_cells(near.get(key))) + f" | {_verdict(near.get(key))} |")
    w("")
    tg = ev["too_good"]
    w("Beklentiden çok iyi (§6): " + ("**tetiklendi — " + "; ".join(tg) + "**. " if tg else "tetiklenmedi. ")
      + "Her iki durumda da dondurma bu görevde yoktur; sıradaki adım Fable'ın bu şartnameden bağımsız, sıfırdan yeniden üretimidir.")
    w("")
    fl = ev["failures"]
    w("Başarısızlık tanımları (§6): " + "; ".join(f"({k}) {FAILURE_TEXT[k]}: **{'evet' if v else 'hayır'}**" for k, v in fl.items())
      + f". Ön eleme (k1, §8): {k1_txt}.")
    w("")
    w("### İkincil ve bilgi hücreleri (aynı yakın dönem fold'ları)")
    w("")
    w("| Başlık | Karşılaştırılan | Rol | n (ay) | model / sol | karş. | fark | %95 aralık | iyi / kötü / eşit | aralık |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for key in ("F2_product", "F2_zero", "F1_by_type", "info_product_zero_F1"):
        head, comp, role = CELL_TITLES[key]
        w(f"| {head} | {comp} | {role} | " + " | ".join(_pair_cells(near.get(key))) + f" | {_verdict(near.get(key))} |")
    w("")
    w("### §6 önceden yazılmış beklenti, satır satır")
    w("")
    w("| Hücre (aynen) | Karşılaştırılan (aynen) | Beklenen (aynen) | Aralık (aynen) | Aralık 0'ı (aynen) | Gerçekleşen | %95 aralık | "
      "n | Konum (T6) | Hüküm | İfadenin tamamı |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    counts = Counter()
    for r in ev["rows6"]:
        val, ci, n = _row_value(r)
        lab = r["label"]
        counts["tuttu" if lab == HELD else "kısmen" if lab.startswith("kısmen") else "tutmadı"] += 1
        raw = r["raw"]
        w(f"| {raw['hucre']} | {raw['karsilastirilan']} | {raw['beklenen']} | {raw['aralik']} | {raw['sifir']} | {val} | {ci} | {n} | "
          f"{position_text(r['position'])} | **{lab}** | {_statement(r)} |")
    w("")
    w(f"Hüküm sayıları: tuttu {counts['tuttu']}, tutmadı {counts['tutmadı']}, kısmen {counts['kısmen']} (toplam {len(ev['rows6'])}).")
    w("")
    w("### Keşif (hüküm yok)")
    w("")
    w("| Hücre | Fold kümesi | n (ay) | model / sol | karş. | fark | %95 aralık | iyi / kötü / eşit |")
    w("|---|---|---|---|---|---|---|---|")
    for scope, name in (("2023", "2023 fold'ları"), ("all", "bütün fold'lar")):
        for key in ("F1_product", "F1_zero", "F2_product", "F2_zero"):
            head, comp, _ = CELL_TITLES[key]
            w(f"| {head} − {comp} | {name} | " + " | ".join(_pair_cells(ev["cells"][scope].get(key))) + " |")
    for name, where in (("b = 1 (L = 0)", lambda r: r["b"] == "1"), ("2 ≤ b ≤ 9", lambda r: r["b"] != "1")):
        for key in ("F1_product", "F1_zero"):
            a, b, y, _ = pbk.CELL_DEFS[key]
            c = pbk.paired_brier(rows, a, b, realized=y, where=where)
            head, comp, _ = CELL_TITLES[key]
            w(f"| {head} − {comp} | {name}, bütün yıllar | " + " | ".join(_pair_cells(c)) + " |")
    w("")
    w("Kalibrasyon (F1, modelin FIT_OK fold'ları; ort p − gözlenen):")
    w("")
    w("| Küme | n | ort p_F1 | gözlenen y_F1 | fark |")
    w("|---|---|---|---|---|")
    groups = [("yakın dönem", pbk.NEAR_ERA_START, None, None), ("2023", None, pbk.NEAR_ERA_START, None),
              ("bütün", None, None, None),
              ("bütün, b_floor = 1", None, None, lambda r: r["test_b_floor"] == "1"),
              ("bütün, b_floor = 0", None, None, lambda r: r["test_b_floor"] == "0")]
    years = sorted({r["first_trading_date"][:4] for r in rows})
    groups += [(f"ilk işlem yılı {y}", f"{y}-01-01", f"{int(y) + 1}-01-01", None) for y in years]
    for name, start, end, where in groups:
        c = pbk.calibration(rows, "F1", start=start, end=end, where=where)
        w(f"| {name} | " + ("0 | — | — | — |" if c is None else f"{c['n']} | {_f(c['mean_p'])} | {_f(c['observed'])} | {_s(c['diff'])} |"))
    w("")
    w("### Fold özeti")
    w("")
    w(f"- {fs['n']} fold (b ≤ 9; yakın dönem {sum(1 for r in rows if r['first_trading_date'] >= pbk.NEAR_ERA_START)}, 2023 "
      f"{sum(1 for r in rows if r['first_trading_date'] < pbk.NEAR_ERA_START)}); F1 durumları: "
      + ", ".join(f"{k} {v}" for k, v in sorted(fs["statuses"].items())) + ".")
    for head in ("F1", "F2"):
        s = fs[head]
        w(f"- {head}: başlık durumları " + ", ".join(f"{k} {v}" for k, v in sorted(s["statuses"].items()))
          + f"; FIT_OK {s['n_ok']} (yakın dönem {s['n_near']}, {s['near_blocks']} ay, olay {s['events_near']}); seçilen C: "
          + (", ".join(f"{_fmt_C(k)}: {v}" for k, v in sorted(s["C"].items(), key=_C_sort)) or "—") + ".")
    w(f"- Ürün karşılaştırıcısı `POST_BREAK_INSUFFICIENT`: {fs['product_insufficient']} fold. Test arzının b_turnover'ı kırpılan "
      f"fold (F1 ön işlemesi): {fs['clipped']}. b_floor ya da b_turnover sıfır varyansla düşen fold (F1): {fs['floor_dropped']}.")
    w("- Yastık kuralı (`D10_STRUCTURAL_ZERO`, bilgi; skorlanmaz): D10 ≤ arz mekanik olarak imkânsız olan kırılma akşamı "
      + ", ".join(f"b = {k}: {v}" for k, v in sorted(fs["structural_zero"].items())) + f" (toplam {sum(fs['structural_zero'].values())}).")
    w("")
    w("### Nihai fit önizlemesi (dondurulmadı)")
    w("")
    trm = previews[MODEL_ID]["training"]
    w(f"Dondurmanın kullanacağı fonksiyonla (`borsai/post_break.py: final_fit`) bütün eğitim kümesinde (F1 {trm['n_F1']} arz, F2 "
      f"{trm['n_F2']}); `models/`'e yazılmadı, dosyalar `docs/faz8/backtest/` altında. Katsayılar z-skorlu kolonlarda, p_floor = "
      "P(taban) başlığınındır. numpy nihai model ile stdlib `predict_break` eğitim satırlarında |Δp| ≤ 1e-12 (§13-9).")
    w("")
    w("| model_id | Başlık | C | sabit | katsayılar | arz / olay | kırpma [p05, p95] (ln) | parite maks \\|Δp\\| | dosya sha256 (ilk 12) |")
    w("|---|---|---|---|---|---|---|---|---|")
    for m in FAZ8_MODEL_IDS:
        pv = previews[m]
        tr = pv["training"]
        for head in ("F1", "F2"):
            hd = pv["horizons"][head]["p_floor"]
            if hd["kind"] == "constant":
                C, icpt, coef = "ZERO (kural)", f"p = {hd['value']:.6f}", "—"
            else:
                C, icpt = _fmt_C(hd["C"]), f"{hd['intercept']:+.4f}"
                coef = ", ".join(f"{c} {v:+.4f}" for c, v in zip(hd["columns"], hd["coef"])) or "—"
            prep = (pv.get("preprocessing") or {}).get(head) or {}
            wins = "; ".join(f"[{v['p05']:.6g}, {v['p95']:.6g}]" for v in prep.get("winsor", {}).values()) or "—"
            par = manifest["final_fit_previews"][m]["parity_max_abs"][head]
            w(f"| `{m}` | {head} | {C} | {icpt} | {coef} | {tr[f'n_{head}']} / {tr[f'events_{head}']} | {wins} | {par:.1e} | "
              f"`{manifest['final_fit_previews'][m]['sha256'][:12]}` |")
    by_type = previews[MODEL_ID]["comparators"]["by_type_F1"]
    w("")
    w(f"Dondurulmuş karşılaştırıcı oranları (canlıda `@ZERO` ve `by_type` bunlardır): F1 eğitim oranı "
      f"{_f(previews[MODEL_ID]['comparators']['zero']['F1'])}, F2 {_f(previews[MODEL_ID]['comparators']['zero']['F2'])}; b_floor = 1 "
      f"sınıfında {_f(by_type['1']['rate'])} ({by_type['1']['events']}/{by_type['1']['n']}), b_floor = 0 sınıfında "
      f"{_f(by_type['0']['rate'])} ({by_type['0']['events']}/{by_type['0']['n']}).")
    w("")
    w("Duyarlılıklar (§7.2: yalnız b_floor, yalnız b_turnover, + Z/B grubu): günlükte `kind: sensitivity` satırlarıdır; model değildir, "
      "bu belgeye, skora ve varyant sayacına girmez (test_experiment_log kuralı); sonuçları `docs/faz8/IMPL_RAPOR.md`'de.")
    w("")
    w("### Faz 8 koşusu ve deney günlüğü")
    w("")
    w("| Koşu | Plan | Fold | Ledger sha256 (ilk 12) | Günlükteki `kind: backtest` satırı | `kind: sensitivity` satırı |")
    w("|---|---|---|---|---|---|")
    info = manifest["runs"][MODEL_ID]
    w(f"| `{MODEL_ID}` (+ `{ZERO_ID}` sütunları) | `{info['plan_id']}` | {len(rows)} | `{info['ledger_sha256'][:12]}` | "
      f"{_log_count(entries, 'backtest', MODEL_ID)} | "
      f"{sum(_log_count(entries, 'sensitivity', n) for n in FAZ8_SENSITIVITIES)} |")
    _frozen_section(w, frozen_entries(index_path) if Path(out_dir) == GOLDEN_DIR else [], near, ev["k1"]["holds"])

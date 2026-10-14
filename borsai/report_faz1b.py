"""docs/MODELS.md'nin Faz 1B bölümü: yeni modellerin backtest'i ve şartname beklentileri.

Girdi: tests/reference/macos_golden_faz1b/ (Faz 1B resmi koşularının ledger'ları),
tests/reference/macos_golden/v1_5_h99 ledger'ı (eşleşik karşılaştırma), dondurulmuş
model dosyaları, experiments/log.jsonl. Yeni backtest koşmaz.

Beklenti tablosu: her şartnamenin "sonuç görülmeden yazılan beklenti" cümleleri AYNEN
(`EXPECTATIONS`; tests/test_report.py her alıntının şartname dosyasında birebir geçtiğini
sınar) ve yanında gerçekleşen backtest değeri. Şartnamedeki niteleyici sözcükler
("çoğu", "sık", "≈ 0", "küçük" …) sayıya `OPERATIONAL_RULES`'taki kurallarla çevrilir;
bu kurallar sonuçlar görülmeden, rapor kodu yazılırken sabitlendi ve raporda yazılıdır.
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from . import metrics as mx
from . import survival as sv
from .backtest import FAZ1B_RUNS, GOLDEN_DIR, GOLDEN_FAZ1B_DIR, golden_filename, run_key
from .horizons import HORIZONS
from .specs import FAZ1A_MODEL_IDS, MODEL_SPECS, PLAN_CEILING, PLAN_KEYS, PLAN_PB, PLAN_PB_CEILING, PLAN_V15

KS = (1, 3, 5, 10)
RETURN_RULES = ("base_always_ceiling", "base_train_median", "base_train_mean", "base_zero")
PROB_RULES = ("base_always_ceiling", "base_rate", "base_last10_rate")
OK = ("FIT_OK", "RULE_OK")
VERDICT = {
    "MODEL_DAHA_IYI": "**model geçiyor** (aralık 0'ın altında)",
    "KURAL_DAHA_IYI": "**karşılaştırılan daha iyi** (aralık 0'ın üstünde)",
    "AYIRT_EDILEMIYOR": "ayırt edilemiyor (aralık 0'ı içeriyor)",
}

# Şartnamedeki niteleyicilerin sayısal karşılığı (sonuç görülmeden sabitlendi).
MOST = 0.5          # "çoğu", "çoğunlukla", "seçilir": fold'ların > %50'si
OFTEN = 0.25        # "sık": fold'ların ≥ %25'i
EARLY_FOLDS = 20    # "erken fold": kronolojik ilk 20 skorlanabilir fold
NEAR_ZERO_MAE = 0.002   # "≈ 0" (getiri MAE farkı); SPEC_MARKET20_V0'daki |ΔMAE| sınırıyla aynı
SMALL_MAE = 0.01        # "küçük değişim" (getiri MAE farkı); SPEC_V1_6 D10 ±0.01 ile aynı ölçek
NEAR_ZERO_BRIER = 0.002  # "≈ 0" (Brier/RPS farkı)
SLIGHTLY_WORSE_BRIER = 0.01  # "hafif kötü": 0 < fark < 0.01
SMALL_GAIN_BRIER = 0.01      # "küçük kazanç": −0.01 < fark ≤ +0.002
AROUND_010 = 0.005           # "~0.10": |Brier − 0.10| ≤ 0.005

OPERATIONAL_RULES = (
    f"\"çoğu / çoğunlukla / seçilir\" = ilgili fold'ların > %{MOST * 100:.0f}'si; \"sık\" = ≥ %{OFTEN * 100:.0f}'i.",
    f"\"erken fold\" = kronolojik ilk {EARLY_FOLDS} skorlanabilir fold.",
    f"Getiri MAE farkında \"≈ 0\" = |fark| < {NEAR_ZERO_MAE}; \"küçük değişim\" = |fark| < {SMALL_MAE}.",
    f"Brier/RPS farkında \"≈ 0\" = |fark| < {NEAR_ZERO_BRIER}; \"hafif kötü\" = 0 < fark < {SLIGHTLY_WORSE_BRIER}; "
    f"\"küçük kazanç\" = −{SMALL_GAIN_BRIER} < fark ≤ +{NEAR_ZERO_BRIER}.",
    f"\"~0.10\" = |değer − 0.10| ≤ {AROUND_010}.",
    "\"ayırt edilemez / aralık 0'ı içerir\" = blok bootstrap %95 aralığı 0'ı içeriyor. \"daha kötü ya da eşit\" = aralık "
    "tamamen 0'ın altında değil (model anlamlı biçimde daha iyi değil).",
    "\"en iyi KM kuralı\" = `base_km_expanding` ve `base_km_last10`'dan eşleşik kümede ortalama RPS'i küçük olan.",
    "Çok parçalı beklentide her parça ayrı değerlendirilir; hepsi tutarsa \"tuttu\", hiçbiri tutmazsa \"tutmadı\", "
    "aksi halde \"kısmen\" ve tutmayan parça adıyla yazılır.",
)

# Şartnamelerden AYNEN alınan beklenti cümleleri.
EXPECTATIONS: dict[str, list[tuple[str, str]]] = {
    "ceiling_hazard_v0": [
        ("SPEC_CEILING_V0.md §11", "Backtest RPS farkı (model − en iyi KM kuralı): −0.005 … −0.02; blok bootstrap %95 aralığı "
         "büyük olasılıkla 0'ı içerir (V1.5 Logit'in D1 Brier farkı −0.008 [−0.028, +0.011], AUDIT §1.2-c; çözünürlük ~0.02, AUDIT §3b)."),
        ("SPEC_CEILING_V0.md §11", "En çok kazanç k = 3…5'te (azınlık 31–33); k = 1'de küçük; k = 10'da ≈ 0 ya da hafif kötü."),
        ("SPEC_CEILING_V0.md §11", "Seçilen λ çoğu fold'da 10–300; erken fold'larda INF sık."),
        ("SPEC_CEILING_V0.md §11", "Nihai fit'te işaretler: β_f3 < 0, β_f1 > 0, β_f2 > 0."),
        ("SPEC_CEILING_V0.md §11", "(c) backtest'te model `@INF` kuralından noktasal olarak kötü → \"özellikler bilgi eklemiyor\" diye yazılır."),
        ("SPEC_CEILING_V0.md §11", "(b) |ortalama S_1 − gözlenen D1 tavan oranı| > 0.15 (kalibrasyon)"),
    ],
    "pb_ceiling_v0": [
        ("SPEC_PB_V0.md §9", "Beklenti: RPS'te KM kurallarından ayırt edilemez; `ceiling_hazard_v0`'dan kötü ya da eşit."),
    ],
    "pb_v0": [
        ("SPEC_PB_V0.md §8", "D1 MAE: `base_train_median`'a YENİK ya da eşit (V1.5 bile f3'le yeniliyor: +0.0046 [+0.0015, +0.0079], "
         "AUDIT §1.2-c). D1 p_up: taban oranından ayırt edilemez."),
        ("SPEC_PB_V0.md §8", "D5/D10 MAE: medyana karşı noktasal küçük kazanç mümkün (V1.5'in −0.084 / −0.116'sının en çok üçte biri); "
         "aralık büyük olasılıkla 0'ı içerir."),
        ("SPEC_PB_V0.md §8", "V1.5'e karşı: her ufukta daha kötü ya da eşit."),
        ("SPEC_PB_V0.md §8", "Seçilen α çoğunlukla ≥ 100; D1'de INF sık."),
        ("SPEC_PB_V0.md §4", "D1'de beklenti \"ZERO ya da C ≤ 0.001 seçilir, taban oranından ayırt edilemez\""),
    ],
    "v1_5_market20_v0": [
        ("SPEC_MARKET20_V0.md §9", "8 hücrenin hepsinde V1.5'e karşı eşleşik fark aralığı 0'ı içerir; |ΔMAE| < 0.002, |ΔBrier| < 0.005."),
        ("SPEC_MARKET20_V0.md §9", "f6 katsayısının işareti pozitif (yükselen piyasa → daha yüksek getiri), büyüklüğü küçük."),
    ],
    "v1_6_h99": [
        ("SPEC_V1_6.md §8", "**D1 Ridge:** çoğu fold α ∈ {1000, 10000, INF} seçer; MAE 0.0297 ile 0.0332 arasına, yani V1.5'e eşit ya da "
         "**daha kötü** tarafa gider; medyana yenilgi sürer."),
        ("SPEC_V1_6.md §8", "**D3:** değişim ≈ 0 (V1.5 iç noktada: α = 10)."),
        ("SPEC_V1_6.md §8", "**D5:** küçük değişim."),
        ("SPEC_V1_6.md §8", "**D10 Ridge:** α ∈ {0.001, 0.01} sık seçilir; MAE değişimi ±0.01 içinde, yönü belirsiz (aşırı uyum riski)."),
        ("SPEC_V1_6.md §8", "**Logit D1:** ZERO/0.0001/0.001 sık; Brier taban oranına yaklaşır (0.0943 → ~0.10). Diğer ufuklarda |ΔBrier| < 0.005."),
        ("SPEC_V1_6.md §8", "Kenara yapışma: yeni ızgarada hiçbir ufukta tek bir uç değer fold'ların > %50'sinde seçilmemeli — "
         "INF/ZERO hariç (onlar \"model yok\" demektir ve meşru sonuçtur)."),
    ],
}

# Önceden ilan edilmiş birincil hücre ve prospektif ölçüt (SPEC_SCORING §7; ilgili şartname).
PROSPECTIVE = {
    "ceiling_hazard_v0": "Birincil: RPS; `base_km_last10` **ve** `base_km_expanding`'e karşı (SPEC_CEILING_V0 §11).",
    "pb_ceiling_v0": "Birincil: RPS; ölçüt SPEC_CEILING_V0 §11 ile aynı (SPEC_PB_V0 §9).",
    "pb_v0": "Birincil: D5 MAE, `base_train_median`'a karşı (SPEC_PB_V0 §8).",
    "v1_5_market20_v0": "Birincil: D5 MAE, `v1_5_h99`'a karşı (SPEC_MARKET20_V0 §9).",
    "v1_6_h99": "Birincil: D10 MAE, `v1_5_h99`'a karşı (SPEC_V1_6 §8).",
}


# ---------------------------------------------------------------------------
# Veri
# ---------------------------------------------------------------------------

def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_runs(faz1b_dir: Path = GOLDEN_FAZ1B_DIR) -> dict[str, list[dict[str, str]]]:
    """Faz 1B koşuları + PLAN_V15'teki Faz 1A ledger'ları (v1_5_h99 ve altı kural)."""
    out = {m: _read(GOLDEN_DIR / golden_filename(m)) for m in FAZ1A_MODEL_IDS}
    out.update({run_key(m, p): _read(Path(faz1b_dir) / golden_filename(run_key(m, p))) for m, p in FAZ1B_RUNS})
    return out


def _hp(v: str) -> Any:
    return v if v in ("INF", "ZERO", "") else float(v)


def _month(r: dict[str, str]) -> str:
    return (r.get("first_trading_date") or r["prediction_date"])[:7]


# ---------------------------------------------------------------------------
# Kayıplar ve eşleşik fark
# ---------------------------------------------------------------------------

def mae_model(r): return abs(float(r["ridge_prediction"]) - float(r["realized_return"]))  # noqa: E704
def mae_rule(r): return abs(float(r["rule_return"]) - float(r["realized_return"]))  # noqa: E704
def brier_model(r): return mx.brier_term(float(r["logit_probability"]), int(r["realized_direction"]))  # noqa: E704
def brier_rule(r): return mx.brier_term(float(r["rule_p_up"]), int(r["realized_direction"]))  # noqa: E704
def ok_ridge(r): return r["ridge_status"] == "FIT_OK"  # noqa: E704
def ok_logit(r): return r["logit_status"] == "FIT_OK"  # noqa: E704
def ok_rule_ret(r): return r["rule_return"] != ""  # noqa: E704
def ok_rule_p(r): return r["rule_p_up"] != ""  # noqa: E704
def ok_ceiling(r): return r["status"] in OK  # noqa: E704


def curve(r: dict[str, str], prefix: str = "S") -> list[float]:
    return [float(r[f"{prefix}_{k}"]) for k in range(1, sv.DAYS + 1)]


def rps(r): return sv.rps(curve(r), int(r["realized_L"]))  # noqa: E704


def s_brier(k: int) -> Callable:
    return lambda r: (float(r[f"S_{k}"]) - (1.0 if int(r["realized_L"]) >= k else 0.0)) ** 2


def pc_brier(k: int) -> Callable:
    return lambda r: (float(r[f"P_close_{k}"]) - int(r[f"realized_close_D{k}"])) ** 2


def paired(model_rows, other_rows, loss_model, loss_other, ok_model, ok_other, *,
           horizon: Optional[str] = None, key: Callable = lambda r: r["fold_id"],
           other_target: Optional[Callable] = None) -> Optional[dict[str, Any]]:
    """fark = model − karşılaştırılan, iki tarafın da skorlandığı ortak fold'larda. Hedef
    (gerçekleşen değer) modelin satırından okunur; `other_target` verilirse karşılaştırılanın
    kaybı (diğer_satır, model_satırı) ile hesaplanır."""
    other_by = {key(r): r for r in other_rows if horizon is None or r.get("horizon") == horizon}
    diffs, months, a, b = [], [], [], []
    for r in model_rows:
        if horizon is not None and r.get("horizon") != horizon:
            continue
        o = other_by.get(key(r))
        if o is None or not ok_model(r) or not ok_other(o):
            continue
        la = loss_model(r)
        lb = other_target(o, r) if other_target else loss_other(o)
        a.append(la)
        b.append(lb)
        diffs.append(la - lb)
        months.append(_month(r))
    if not diffs:
        return None
    res = mx.paired_difference(diffs, months)
    res["model_metric"] = sum(a) / len(a)
    res["rule_metric"] = sum(b) / len(b)
    return res


def _f(x: Optional[float], nd: int = 4) -> str:
    return "—" if x is None else f"{x:.{nd}f}"


def _s(x: float, nd: int = 4) -> str:
    return f"{x:+.{nd}f}"


def _pct(x: float) -> str:
    return f"%{100 * x:.0f}"


def _ci(p: dict[str, Any]) -> str:
    lo, hi = p["ci95"]
    return f"[{_s(lo)}, {_s(hi)}]"


def _row(cells: Sequence[str], p: Optional[dict[str, Any]]) -> str:
    if p is None:
        return "| " + " | ".join(list(cells) + ["0", "—", "—", "—", "—", "—", "—"]) + " |"
    return ("| " + " | ".join(list(cells) + [
        f"{p['n']} ({p['n_months']})", _f(p["model_metric"]), _f(p["rule_metric"]), _s(p["mean"]), _ci(p),
        f"{p['model_better_n']} / {p['rule_better_n']} / {p['tie_n']}", VERDICT[p["verdict"]],
    ]) + " |")


PAIR_HEADER = "| n (ay) | model | karşılaştırılan | fark | %95 aralık | model iyi / karş. iyi / eşit | hüküm |"
PAIR_SEP = "|---|---|---|---|---|---|---|"


def _includes_zero(p: dict[str, Any]) -> bool:
    return p["ci95"][0] <= 0.0 <= p["ci95"][1]


def _not_better(p: dict[str, Any]) -> bool:
    return p["ci95"][1] >= 0.0


def _cell(text: str) -> str:
    """Markdown tablo hücresi: metindeki | karakteri kaçışlanır."""
    return text.replace("|", "\\|")


def _combine(parts: Sequence[tuple[str, bool]]) -> str:
    held = [ok for _, ok in parts]
    if all(held):
        return "tuttu"
    if not any(held):
        return "tutmadı"
    return "kısmen (tutmayan: " + "; ".join(name for name, ok in parts if not ok) + ")"


# ---------------------------------------------------------------------------
# Hiperparametre dağılımları
# ---------------------------------------------------------------------------

def hp_distribution(rows, horizon: str, head: str) -> Counter:
    col, ok = ("ridge_selected_alpha", ok_ridge) if head == "ridge" else ("logit_selected_C", ok_logit)
    return Counter(_hp(r[col]) for r in rows if r["horizon"] == horizon and ok(r))


def _share(counter: Counter, values) -> float:
    total = sum(counter.values())
    return sum(counter[v] for v in values) / total if total else 0.0


def _grid(model_id: str, head: str) -> list[Any]:
    spec = MODEL_SPECS[model_id]
    return list(spec["ridge"]["alpha_grid"] if head == "ridge" else spec["logit"]["C_grid"])


def _edges(grid: Sequence[Any], head: str) -> list[Any]:
    """Sonlu uç değerler: α için en küçük ve INF'ten önceki en büyük; C için ZERO'dan sonraki en küçük ve en büyük."""
    return [grid[0], grid[-2]] if head == "ridge" else [grid[1], grid[-1]]


def _dist_table(w, rows, model_id: str) -> dict[tuple[str, str], Counter]:
    out = {}
    for head, label in (("ridge", "Ridge α"), ("logit", "Logit C")):
        grid = _grid(model_id, head)
        edges = _edges(grid, head)
        w("")
        w(f"{label} seçim dağılımı (fold sayısı; yalnız FIT_OK fold'lar). Kenar = sonlu uç değer(ler): "
          + ", ".join(str(e) for e in edges) + ".")
        w("")
        w("| Ufuk | " + " | ".join(str(g) for g in grid) + " | n | en sık sonlu uç değerin payı |")
        w("|---|" + "---|" * (len(grid) + 2))
        for h in HORIZONS:
            c = hp_distribution(rows, h, head)
            out[(h, head)] = c
            n = sum(c.values())
            edge = max((c[e] for e in edges), default=0) / n if n else 0.0
            w(f"| {h} | " + " | ".join(str(c[g]) for g in grid) + f" | {n} | {_pct(edge)} |")
    return out


# ---------------------------------------------------------------------------
# Bölümler
# ---------------------------------------------------------------------------

def _linear_rule_tables(w, model_rows, runs, rule_suffix: str) -> dict[tuple[str, str, str], Any]:
    got: dict[tuple[str, str, str], Any] = {}
    for output, rules, label, lm, lr, om, orule in (
        ("return", RETURN_RULES, "Getiri, MAE", mae_model, mae_rule, ok_ridge, ok_rule_ret),
        ("p_up", PROB_RULES, "P(kapanış > arz), Brier (skorlamada [0.01, 0.99] kırpması)", brier_model, brier_rule, ok_logit, ok_rule_p),
    ):
        w("")
        w(f"{label}: model − basit kural")
        w("")
        w("| Ufuk | Kural " + PAIR_HEADER)
        w("|---|---" + PAIR_SEP)
        for h in HORIZONS:
            for rule in rules:
                p = paired(model_rows, runs[rule + rule_suffix], lm, lr, om, orule, horizon=h)
                got[(output, h, rule)] = p
                w(_row([h, f"`{rule}`"], p))
    return got


def _vs_v15(w, model_rows, runs) -> dict[tuple[str, str], Any]:
    got = {}
    w("")
    w("| Ufuk | Çıktı " + PAIR_HEADER)
    w("|---|---" + PAIR_SEP)
    for h in HORIZONS:
        for output, lm, om in (("MAE", mae_model, ok_ridge), ("Brier", brier_model, ok_logit)):
            p = paired(model_rows, runs["v1_5_h99"], lm, lm, om, om, horizon=h)
            got[(output, h)] = p
            w(_row([h, output], p))
    return got


def _status_line(w, rows, v15_rows) -> None:
    """Fit edilemeyen fold'lar (ufuk ve durum başına), V1.5 ile yan yana."""
    def counts(rs):
        c = Counter((r["horizon"], head, r[f"{head}_status"]) for r in rs for head in ("ridge", "logit")
                    if r[f"{head}_status"] != "FIT_OK")
        return "; ".join(f"{h} {head} {st}: {n}" for (h, head, st), n in sorted(c.items(), key=lambda x: (HORIZONS.index(x[0][0]), x[0][1:]))) or "yok"
    w("")
    w(f"Fit edilemeyen fold'lar — bu model: {counts(rows)}. `v1_5_h99`: {counts(v15_rows)}.")


def _expectation_table(w, model_id: str, evaluated: Sequence[tuple[str, str]]) -> None:
    w("")
    w("| Kaynak | Şartnamedeki beklenti (aynen) | Gerçekleşen (backtest) | Tuttu mu |")
    w("|---|---|---|---|")
    if len(evaluated) != len(EXPECTATIONS[model_id]):
        raise ValueError(f"{model_id}: beklenti ve değerlendirme sayısı farklı")
    for (source, quote), (realized, verdict) in zip(EXPECTATIONS[model_id], evaluated):
        w(f"| {source} | {_cell(quote)} | {_cell(realized)} | {_cell(verdict)} |")
    w("")
    w(f"Prospektif ölçüt: {PROSPECTIVE[model_id]} Canlı n = 0: hüküm yok (SPEC_SCORING §8).")


def section_v1_6(w, runs, models) -> None:
    rows = runs["v1_6_h99"]
    w("### `v1_6_h99` (SPEC_V1_6)")
    w("")
    w("Plan: PLAN_V15 (351 fold, V1.5 ile aynı `training_tickers_sha256`). Izgara α ∈ {0.001 … 10000, INF}, "
      "C ∈ {ZERO, 0.0001 … 100}; aday başına yakınsamama.")
    w("")
    w("Eşleşik fark: `v1_6_h99` − `v1_5_h99` (ikisinin de FIT_OK olduğu fold'lar):")
    vs = _vs_v15(w, rows, runs)
    rules = _linear_rule_tables(w, rows, runs, "")
    _status_line(w, rows, runs["v1_5_h99"])
    dist = _dist_table(w, rows, "v1_6_h99")
    dropped = sum(1 for r in rows for e in json.loads(r["logit_score_table"]) if e["status"] != "SCORED")
    fallback = sum(1 for r in rows if len(json.loads(r["logit_final_fit_attempts"])) > 1)
    betae = next(r for r in rows if r["fold_id"] == "D3|BETAE")
    w("")
    w(f"Aday başına yakınsamama: {dropped} (fold, C) adayı `CANDIDATE_NOT_CONVERGED`; nihai fit'te sıradaki adaya geçilen fold: "
      f"{fallback}. D3|BETAE: Logit {betae['logit_status']}, C = {betae['logit_selected_C']}. "
      f"D3 Logit FIT_OK n = {sum(1 for r in rows if r['horizon'] == 'D3' and ok_logit(r))}.")
    frozen = models["v1_6_h99"]["horizons"]
    w("")
    w("Nihai fit (99 arz): " + "; ".join(f"{h} α = {frozen[h]['return']['alpha']}, C = {frozen[h]['p_up']['C']}" for h in HORIZONS) + ".")

    # beklentiler
    d1 = dist[("D1", "ridge")]
    mae_d1 = statistics.mean(mae_model(r) for r in rows if r["horizon"] == "D1" and ok_ridge(r))
    med = rules[("return", "D1", "base_train_median")]
    e1 = [("çoğu fold α ∈ {1000, 10000, INF}", _share(d1, (1000.0, 10000.0, "INF")) > MOST),
          ("MAE 0.0297–0.0332", 0.0297 <= round(mae_d1, 4) <= 0.0332),
          ("medyana yenilgi", med["mean"] > 0)]
    r1 = (f"α ∈ {{1000, 10000, INF}}: {_pct(_share(d1, (1000.0, 10000.0, 'INF')))} ({sum(d1.values())} fold); "
          f"MAE {_f(mae_d1)}; medyana karşı {_s(med['mean'])} {_ci(med)}")
    d3, d5, d10 = vs[("MAE", "D3")], vs[("MAE", "D5")], vs[("MAE", "D10")]
    e2 = [("≈ 0", abs(d3["mean"]) < NEAR_ZERO_MAE)]
    e3 = [("küçük", abs(d5["mean"]) < SMALL_MAE)]
    a10 = dist[("D10", "ridge")]
    e4 = [("α ∈ {0.001, 0.01} sık", _share(a10, (0.001, 0.01)) >= OFTEN), ("±0.01 içinde", abs(d10["mean"]) <= SMALL_MAE),
          ("yönü belirsiz", _includes_zero(d10))]
    c1 = dist[("D1", "logit")]
    b16 = vs[("Brier", "D1")]["model_metric"]
    others = [vs[("Brier", h)]["mean"] for h in ("D3", "D5", "D10")]
    e5 = [("ZERO/0.0001/0.001 sık", _share(c1, ("ZERO", 0.0001, 0.001)) >= OFTEN), ("Brier ~0.10", abs(b16 - 0.10) <= AROUND_010),
          ("diğer ufuklarda |ΔBrier| < 0.005", all(abs(x) < 0.005 for x in others))]
    edge_ok = []
    edge_txt = []
    for h in HORIZONS:
        for head in ("ridge", "logit"):
            c = dist[(h, head)]
            edges = _edges(_grid("v1_6_h99", head), head)
            share = max(c[e] for e in edges) / sum(c.values())
            edge_ok.append(share <= MOST)
            edge_txt.append(f"{h} {head} {_pct(share)}")
    _expectation_table(w, "v1_6_h99", [
        (r1, _combine(e1)),
        (f"D3 ΔMAE {_s(d3['mean'])} {_ci(d3)}", _combine(e2)),
        (f"D5 ΔMAE {_s(d5['mean'])} {_ci(d5)}", _combine(e3)),
        (f"α ∈ {{0.001, 0.01}}: {_pct(_share(a10, (0.001, 0.01)))}; D10 ΔMAE {_s(d10['mean'])} {_ci(d10)}", _combine(e4)),
        (f"C ∈ {{ZERO, 0.0001, 0.001}}: {_pct(_share(c1, ('ZERO', 0.0001, 0.001)))}; D1 Brier {_f(b16)} (V1.5 "
         f"{_f(vs[('Brier', 'D1')]['rule_metric'])}); D3/D5/D10 ΔBrier " + ", ".join(_s(x) for x in others), _combine(e5)),
        ("en sık sonlu uç değer payı: " + ", ".join(edge_txt), "tuttu" if all(edge_ok) else "tutmadı"),
    ])


def section_market20(w, runs, models) -> None:
    rows = runs["v1_5_market20_v0"]
    w("### `v1_5_market20_v0` (SPEC_MARKET20_V0)")
    w("")
    w("Plan: PLAN_V15 (351 fold, V1.5 ile aynı eğitim kümeleri). f6 = XU100(S0)/XU100(S20) − 1, Takvim B, ref_date = T; "
      "99/99 arzda hesaplandı, hiçbir satır düşmedi.")
    w("")
    w("Eşleşik fark: `v1_5_market20_v0` − `v1_5_h99` (8 hücre):")
    vs = _vs_v15(w, rows, runs)
    _linear_rule_tables(w, rows, runs, "")
    _status_line(w, rows, runs["v1_5_h99"])
    w("V1.5 ile aynı yakınsamama politikası (fold düzeyi) geçerlidir; eşleşik Brier karşılaştırması iki modelin de "
      "fit edildiği fold'larda yapılır.")
    m = models["v1_5_market20_v0"]
    w("")
    w("Nihai fit (99 arz) f6 katsayıları (z-skor ölçeğinde) ve f1–f5 katsayılarının ortalama mutlak değeri:")
    w("")
    w("| Ufuk | Ridge β_f6 | Ridge: f1–f5 ort. mutlak β | Logit β_f6 | Logit: f1–f5 ort. mutlak β |")
    w("|---|---|---|---|---|")
    sign_ok, small_ok = [], []
    for h in HORIZONS:
        vals = {}
        for head in ("return", "p_up"):
            coef = dict(zip(m["horizons"][h][head]["columns"], m["horizons"][h][head]["coef"]))
            vals[head] = (coef["f6"], statistics.mean(abs(coef[c]) for c in ("f1", "f2", "f3", "f4", "f5")))
            small_ok.append(abs(coef["f6"]) < vals[head][1])
        sign_ok.append(vals["return"][0] > 0)
        w(f"| {h} | {_s(vals['return'][0])} | {_f(vals['return'][1])} | {_s(vals['p_up'][0])} | {_f(vals['p_up'][1])} |")
    cells = [vs[(o, h)] for h in HORIZONS for o in ("MAE", "Brier")]
    e1 = [("aralıklar 0'ı içeriyor", all(_includes_zero(p) for p in cells)),
          ("|ΔMAE| < 0.002", all(abs(vs[("MAE", h)]["mean"]) < 0.002 for h in HORIZONS)),
          ("|ΔBrier| < 0.005", all(abs(vs[("Brier", h)]["mean"]) < 0.005 for h in HORIZONS))]
    e2 = [("işaret pozitif (getiri kafası, 4 ufuk)", all(sign_ok)), ("büyüklüğü küçük", all(small_ok))]
    _expectation_table(w, "v1_5_market20_v0", [
        ("0'ı içeren aralık: " + f"{sum(_includes_zero(p) for p in cells)}/8; ΔMAE " +
         ", ".join(f"{h} {_s(vs[('MAE', h)]['mean'])}" for h in HORIZONS) + "; ΔBrier " +
         ", ".join(f"{h} {_s(vs[('Brier', h)]['mean'])}" for h in HORIZONS), _combine(e1)),
        ("Ridge β_f6 > 0: " + f"{sum(sign_ok)}/4; |β_f6| < ort. |β_f1..f5|: {sum(small_ok)}/8 kafa", _combine(e2)),
    ])


def section_pb(w, runs, models) -> None:
    rows = runs["pb_v0"]
    w("### `pb_v0` (SPEC_PB_V0)")
    w("")
    w("Plan: PLAN_PB (kesim ilk talep toplama günü B(k)); skorlanabilir fold D1 87, D3 87, D5 87, D10 84. "
      "Kurallar aynı PB kesimiyle, aynı fold'larda. **D1 p_up bütçe üstüdür** (3 katsayı, 10 azınlık olayı; SPEC_PB_V0 §4).")
    rules = _linear_rule_tables(w, rows, runs, "__pb")
    _status_line(w, rows, runs["v1_5_h99"])
    w("")
    w("Bilgi amaçlı eşleşik karşılaştırma: `pb_v0` − `v1_5_h99`, aynı test arzı ve ufuk (eğitim kümeleri farklı: B(k) ve T(k) "
      "kesimleri); fark \"talep katının değeri\"dir (SPEC_PB_V0 §7):")
    vs = _vs_v15(w, rows, runs)
    dist = _dist_table(w, rows, "pb_v0")
    dropped = sum(1 for r in rows for e in json.loads(r["logit_score_table"]) if e["status"] != "SCORED")
    fallback = sum(1 for r in rows if len(json.loads(r["logit_final_fit_attempts"])) > 1)
    w("")
    w(f"Aday başına yakınsamama: {dropped} (fold, C) adayı `CANDIDATE_NOT_CONVERGED`; nihai fit'te sıradaki adaya geçilen "
      f"fold: {fallback}.")
    frozen = models["pb_v0"]["horizons"]
    w("")
    w("Nihai fit (99 arz): " + "; ".join(f"{h} α = {frozen[h]['return']['alpha']}, C = {frozen[h]['p_up']['C']}" for h in HORIZONS) + ".")
    med1, rate1 = rules[("return", "D1", "base_train_median")], rules[("p_up", "D1", "base_rate")]
    e1 = [("D1 MAE yenik ya da eşit", _not_better(med1)), ("D1 p_up ayırt edilemez", _includes_zero(rate1))]
    med5, med10 = rules[("return", "D5", "base_train_median")], rules[("return", "D10", "base_train_median")]
    e2 = [("D5 kazanç ≤ üçte bir", med5["mean"] >= -0.084 / 3), ("D10 kazanç ≤ üçte bir", med10["mean"] >= -0.116 / 3),
          ("aralıklar 0'ı içeriyor", _includes_zero(med5) and _includes_zero(med10))]
    e3 = [(f"{o} {h}", _not_better(vs[(o, h)])) for h in HORIZONS for o in ("MAE", "Brier")]
    alpha_all = Counter()
    for h in HORIZONS:
        alpha_all += dist[(h, "ridge")]
    ge100 = _share(alpha_all, (100.0, 1000.0, 10000.0, "INF"))
    inf_d1 = _share(dist[("D1", "ridge")], ("INF",))
    e4 = [("α ≥ 100 çoğunlukla", ge100 > MOST), ("D1'de INF sık", inf_d1 >= OFTEN)]
    c1 = _share(dist[("D1", "logit")], ("ZERO", 0.0001, 0.001))
    e5 = [("ZERO ya da C ≤ 0.001 seçilir", c1 > MOST), ("taban oranından ayırt edilemez", _includes_zero(rate1))]
    _expectation_table(w, "pb_v0", [
        (f"D1 MAE − medyan {_s(med1['mean'])} {_ci(med1)}; D1 Brier − taban oranı {_s(rate1['mean'])} {_ci(rate1)}", _combine(e1)),
        (f"D5 {_s(med5['mean'])} {_ci(med5)} (sınır −0.028); D10 {_s(med10['mean'])} {_ci(med10)} (sınır −0.0387)", _combine(e2)),
        ("aralığı tamamen 0'ın altında hücre: " + (", ".join(n for n, ok in e3 if not ok) or "yok") + "; noktasal: "
         + ", ".join(f"{o} {h} {_s(vs[(o, h)]['mean'])}" for h in HORIZONS for o in ("MAE", "Brier")), _combine(e3)),
        (f"α ≥ 100 (INF dahil): {_pct(ge100)}; D1'de INF: {_pct(inf_d1)}", _combine(e4)),
        (f"D1 C ∈ {{ZERO, 0.0001, 0.001}}: {_pct(c1)}; D1 Brier − taban oranı {_s(rate1['mean'])} {_ci(rate1)}", _combine(e5)),
    ])


def _ceiling_tables(w, runs, model_id: str, plan_suffix: str) -> dict[str, Any]:
    rows = runs[model_id]
    comps = {
        f"{model_id}@INF": runs[f"{model_id}@INF"],
        "base_km_expanding": runs["base_km_expanding" + plan_suffix],
        "base_km_last10": runs["base_km_last10" + plan_suffix],
        "base_always_ceiling": runs["base_always_ceiling__" + ("ceiling" if not plan_suffix else "pb_ceiling")],
    }
    got: dict[str, Any] = {"rps": {}}
    w("")
    w("Birincil metrik RPS = (1/10) Σ_k (S_k − 1[L ≥ k])², kırpmasız; fark = model − kural:")
    w("")
    w("| Kural " + PAIR_HEADER)
    w("|---" + PAIR_SEP)
    for name, other in comps.items():
        p = paired(rows, other, rps, rps, ok_ceiling, ok_ceiling)
        got["rps"][name] = p
        w(_row([f"`{name}`"], p))
    km = {n: got["rps"][n] for n in ("base_km_expanding", "base_km_last10")}
    best = min(km, key=lambda n: km[n]["rule_metric"])
    got["best_km"] = best
    w("")
    w(f"Gün başına Brier (S_k, kırpmasız): model − en iyi KM kuralı (`{best}`) ve model − `{model_id}@INF`:")
    w("")
    w("| k | n | model | en iyi KM | fark | %95 aralık | model | @INF | fark | %95 aralık |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    got["per_k"] = {}
    for k in range(1, sv.DAYS + 1):
        p = paired(rows, comps[best], s_brier(k), s_brier(k), ok_ceiling, ok_ceiling)
        q = paired(rows, comps[f"{model_id}@INF"], s_brier(k), s_brier(k), ok_ceiling, ok_ceiling)
        got["per_k"][k] = p
        w(f"| {k} | {p['n']} | {_f(p['model_metric'])} | {_f(p['rule_metric'])} | {_s(p['mean'])} | {_ci(p)} | "
          f"{_f(q['model_metric'])} | {_f(q['rule_metric'])} | {_s(q['mean'])} | {_ci(q)} |")
    w("")
    w("Kalibrasyon (ortalama S_k ve gözlenen P(L ≥ k), aynı fold'lar):")
    w("")
    w("| k | model ort. S_k | `base_km_expanding` | `base_km_last10` | gözlenen |")
    w("|---|---|---|---|---|")
    ok_rows = [r for r in rows if ok_ceiling(r)]
    for k in KS:
        obs = statistics.mean(1.0 if int(r["realized_L"]) >= k else 0.0 for r in ok_rows)
        w(f"| {k} | {_f(statistics.mean(float(r[f'S_{k}']) for r in ok_rows))} | "
          f"{_f(statistics.mean(float(r[f'S_{k}']) for r in comps['base_km_expanding']))} | "
          f"{_f(statistics.mean(float(r[f'S_{k}']) for r in comps['base_km_last10']))} | {_f(obs)} |")
    got["calibration_S1"] = (statistics.mean(float(r["S_1"]) for r in ok_rows),
                             statistics.mean(1.0 if int(r["realized_L"]) >= 1 else 0.0 for r in ok_rows))
    w("")
    w("İkincil çıktı P(Dk'de tavan kapanışı), Brier (kırpmasız); fark = model − karşılaştırılan:")
    w("")
    w("| k | Karşılaştırılan " + PAIR_HEADER)
    w("|---|---" + PAIR_SEP)
    for k in KS:
        for name, other in comps.items():
            w(_row([str(k), f"`{name}`"], paired(rows, other, pc_brier(k), pc_brier(k), ok_ceiling, ok_ceiling)))
        if not plan_suffix:
            h = f"D{k}"
            v15 = [r for r in runs["v1_5_h99"] if r["horizon"] == h]
            p = paired(rows, v15, pc_brier(k), None, ok_ceiling, ok_logit, key=lambda r: r["ticker"],
                       other_target=lambda o, r, k=k: (float(o["logit_probability"]) - int(r[f"realized_close_D{k}"])) ** 2)
            w(_row([str(k), "`v1_5_p_up_as_ceiling`"], p))
    lam = Counter(_hp(r["selected_lambda"]) for r in rows if ok_ceiling(r))
    early = [_hp(r["selected_lambda"]) for r in rows if ok_ceiling(r)][:EARLY_FOLDS]
    grid = [0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, "INF"]
    w("")
    w("Seçilen λ (fold sayısı): " + ", ".join(f"{g}: {lam[g]}" for g in grid) + f". İlk {EARLY_FOLDS} fold'da INF: "
      f"{sum(1 for x in early if x == 'INF')}. Yakınsamayan λ adayı: "
      f"{sum(int(r['n_lambda_not_converged']) for r in rows)}; fold durumları: "
      + ", ".join(f"{s} {n}" for s, n in sorted(Counter(r['status'] for r in rows).items())) + ".")
    got["lambda"], got["early"] = lam, early
    return got


def _final_fit_line(w, m: dict[str, Any]) -> None:
    beta = ", ".join(f"β_{f} = {_s(v)}" for f, v in m["beta"].items())
    rr = m["reclose_rates"]
    w("")
    w(f"Nihai fit ({m['training']['n_ipo']} arz, {m['training']['n_pp_rows']} risk-günü, {m['training']['n_events']} olay): "
      f"λ = {m['lambda']}; γ = [" + ", ".join(_s(g) for g in m["gamma"]) + f"]; {beta}. Yeniden-tavan oranları: "
      f"r_a = ({rr['a_a']} + 0.5)/({rr['n_a']} + 1) = {_f(rr['r_a'])}, r_b = ({rr['a_b']} + 0.5)/({rr['n_b']} + 1) = {_f(rr['r_b'])}.")


def section_ceiling(w, runs, models) -> dict[str, Any]:
    rows = runs["ceiling_hazard_v0"]
    w("### `ceiling_hazard_v0` (SPEC_CEILING_V0)")
    w("")
    ok_rows = [r for r in rows if ok_ceiling(r)]
    minority = (sum(1 for r in ok_rows if int(r["realized_L"]) < 1), sum(1 for r in ok_rows if int(r["realized_L"]) < 3),
                sum(1 for r in ok_rows if int(r["realized_L"]) >= 5), sum(1 for r in ok_rows if int(r["realized_L"]) >= 10))
    w(f"Plan: PLAN_CEILING (kesim T, f3 dolu arzlar, ≥ 10 arz / ≥ 5 olay / ≥ 5 sağ kalım): {len(rows)} fold, ilki "
      f"{rows[0]['ticker']} {rows[0]['first_trading_date']}. Test kümesinde L < 1: {minority[0]}, L < 3: {minority[1]}, "
      f"L ≥ 5: {minority[2]}, L ≥ 10: {minority[3]} (SPEC_CEILING_V0 §6: 16 / 31 / 33 / 11). Kurallar aynı fold'larda, "
      "aynı kişi-dönem eğitim kümesinden.")
    got = _ceiling_tables(w, runs, "ceiling_hazard_v0", "")
    m = models["ceiling_hazard_v0"]
    _final_fit_line(w, m)
    best = got["rps"][got["best_km"]]
    inf = got["rps"]["ceiling_hazard_v0@INF"]
    e1 = [("fark −0.005 … −0.02", -0.02 <= best["mean"] <= -0.005), ("aralık 0'ı içeriyor", _includes_zero(best))]
    per_k = {k: p["mean"] for k, p in got["per_k"].items()}
    argmax_gain = min(per_k, key=per_k.get)
    e2 = [("en çok kazanç k = 3…5", argmax_gain in (3, 4, 5)),
          ("k = 1'de küçük", -SMALL_GAIN_BRIER < per_k[1] <= NEAR_ZERO_BRIER),
          ("k = 10'da ≈ 0 ya da hafif kötü", -NEAR_ZERO_BRIER < per_k[10] < SLIGHTLY_WORSE_BRIER)]
    lam, early = got["lambda"], got["early"]
    mid = _share(lam, (10.0, 30.0, 100.0, 300.0))
    early_inf = sum(1 for x in early if x == "INF") / len(early)
    e3 = [("çoğu fold 10–300", mid > MOST), ("erken fold'larda INF sık", early_inf >= OFTEN)]
    b = m["beta"]
    e4 = [("β_f3 < 0", b["f3"] < 0), ("β_f1 > 0", b["f1"] > 0), ("β_f2 > 0", b["f2"] > 0)]
    s1, obs1 = got["calibration_S1"]
    _expectation_table(w, "ceiling_hazard_v0", [
        (f"en iyi KM `{got['best_km']}`: fark {_s(best['mean'])} {_ci(best)}, n = {best['n']}", _combine(e1)),
        ("k'ya göre Brier farkı (en iyi KM): " + ", ".join(f"k{k} {_s(v)}" for k, v in per_k.items())
         + f"; en çok kazanç k = {argmax_gain}", _combine(e2)),
        (f"λ ∈ {{10, 30, 100, 300}}: {_pct(mid)}; ilk {EARLY_FOLDS} fold'da INF: {_pct(early_inf)}", _combine(e3)),
        (", ".join(f"β_{f} = {_s(v)}" for f, v in b.items()), _combine(e4)),
        (f"RPS model − @INF = {_s(inf['mean'])} {_ci(inf)}: model @INF'ten noktasal olarak "
         + ("**kötü → özellikler bilgi eklemiyor**" if inf["mean"] > 0 else "kötü değil"),
         "başarısızlık (c) gerçekleşti" if inf["mean"] > 0 else "başarısızlık (c) gerçekleşmedi"),
        (f"backtest: ort. S_1 {_f(s1)}, gözlenen D1 tavan oranı {_f(obs1)}, |fark| = {_f(abs(s1 - obs1))}",
         "ölçüt prospektif; backtest'te " + ("aşıldı" if abs(s1 - obs1) > 0.15 else "aşılmadı")),
    ])
    return got


def section_pb_ceiling(w, runs, models) -> None:
    rows = runs["pb_ceiling_v0"]
    w("### `pb_ceiling_v0` (SPEC_PB_V0 §9)")
    w("")
    w(f"Plan: PLAN_PB_CEILING (kesim B(k), 99 arz, aynı skorlanabilirlik kuralı): **{len(rows)} skorlanabilir fold** "
      f"(şartname bu sayıyı ölçmedi; beklenen 84–89), ilki {rows[0]['ticker']} {rows[0]['first_trading_date']}.")
    got = _ceiling_tables(w, runs, "pb_ceiling_v0", "__pb_ceiling")
    _final_fit_line(w, models["pb_ceiling_v0"])
    w("")
    w("Eşleşik RPS: `pb_ceiling_v0` − `ceiling_hazard_v0`, iki modelin de skorlandığı test arzları:")
    w("")
    w("| Karşılaştırılan " + PAIR_HEADER)
    w("|---" + PAIR_SEP)
    vs_ceiling = paired(rows, runs["ceiling_hazard_v0"], rps, rps, ok_ceiling, ok_ceiling, key=lambda r: r["ticker"])
    w(_row(["`ceiling_hazard_v0`"], vs_ceiling))
    e = [("`base_km_expanding`'den ayırt edilemez", _includes_zero(got["rps"]["base_km_expanding"])),
         ("`base_km_last10`'dan ayırt edilemez", _includes_zero(got["rps"]["base_km_last10"])),
         ("`ceiling_hazard_v0`'dan kötü ya da eşit", _not_better(vs_ceiling))]
    _expectation_table(w, "pb_ceiling_v0", [
        ("RPS farkı: " + "; ".join(f"`{n}` {_s(got['rps'][n]['mean'])} {_ci(got['rps'][n])}" for n in ("base_km_expanding", "base_km_last10"))
         + f"; `ceiling_hazard_v0`'a karşı {_s(vs_ceiling['mean'])} {_ci(vs_ceiling)} (n = {vs_ceiling['n']})", _combine(e)),
    ])


def log_counts(log_path: Path) -> Counter:
    counts: Counter = Counter()
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                e = json.loads(line)
                counts[e.get("run_key", e["model_id"])] += 1
    return counts


def render_faz1b(w, models: dict[str, Any], log_path: Path, faz1b_dir: Path = GOLDEN_FAZ1B_DIR) -> None:
    runs = load_runs(faz1b_dir)
    manifest = json.loads((Path(faz1b_dir) / "MANIFEST.json").read_text(encoding="utf-8"))
    w("## Faz 1B: yeni modeller (Fable şartnameleri, docs/specs/)")
    w("")
    w("**Terazi:** aşağıdaki her sayı **backtest**tir (retrospektif walk-forward, H99). Şartnamelerin hepsi bu sonuçların "
      "**tasarıma maruz** olduğunu yazar (özellik, gün grubu ve ızgaralar H99 görülerek seçildi; market20 ayrıca eski repoda "
      "görülmüştü); kanıt değeri düşüktür. Asıl ölçüm prospektiftir ve henüz yoktur (n = 0). \"Geçiyor\" yalnız aralık 0'ı "
      "dışlıyorsa yazılır.")
    w("")
    w("Yöntem: eşleşik fark = model − karşılaştırılan, ikisinin de skorlandığı ortak fold'larda; %95 aralık yukarıdaki blok "
      f"bootstrap (ilk işlem ayı blokları, {mx.BOOTSTRAP_REPS} tekrar, `random.Random({mx.BOOTSTRAP_SEED})`). Getiri MAE; "
      "P(kapanış > arz) Brier (Faz 1A tablolarıyla aynı [0.01, 0.99] skorlama kırpması); tavan çıktıları RPS ve Brier "
      "(kırpmasız).")
    w("")
    w("| Plan | Bilgi kesimi | Kural | Kullanan |")
    w("|---|---|---|---|")
    w(f"| `{PLAN_V15}` | T (ilk işlem günü) | hedef seansı < T; n ≥ 10 | V1.5, `v1_6_h99`, `v1_5_market20_v0`, Faz 1A kuralları |")
    w(f"| `{PLAN_PB}` | B (ilk talep toplama günü) | hedef seansı < B; n ≥ 10 | `pb_v0` ve 6 kural |")
    w(f"| `{PLAN_CEILING}` | T | kişi-dönem satırı seansı < T; f3 dolu arzlar; ≥ 10 arz, ≥ 5 olay, ≥ 5 sağ kalım | "
      "`ceiling_hazard_v0`, @INF, KM kuralları, her zaman tavan |")
    w(f"| `{PLAN_PB_CEILING}` | B | aynı, 99 arz | `pb_ceiling_v0`, @INF, KM kuralları, her zaman tavan |")
    w("")
    w("Beklenti tablolarındaki niteleyicilerin sayısal karşılığı (rapor kodunda sabit, sonuçlardan önce yazıldı):")
    w("")
    for rule in OPERATIONAL_RULES:
        w(f"- {rule}")
    w("")
    for fn in (section_v1_6, section_market20, section_pb):
        fn(w, runs, models)
        w("")
    section_ceiling(w, runs, models)
    w("")
    section_pb_ceiling(w, runs, models)
    w("")
    w("### Faz 1B koşuları ve deney günlüğü")
    w("")
    counts = log_counts(log_path)
    w("| Koşu | Model | Plan | Fold | Ledger sha256 (ilk 12) | Günlükteki koşu sayısı |")
    w("|---|---|---|---|---|---|")
    for key in (run_key(m, p) for m, p in FAZ1B_RUNS):
        info = manifest["runs"][key]
        w(f"| `{key}` | `{info['model_id']}` | {PLAN_KEYS[info['plan_id']]} | {len(runs[key])} | `{info['ledger_sha256'][:12]}` | "
          f"{counts[key]} |")
    w("")
    w("\"Günlükteki koşu sayısı\": `experiments/log.jsonl`'da bu koşu anahtarının (model + plan) satır sayısı. Aynı veride "
      "bakılan her koşu sayılır (CLAUDE.md kural 4); bir koşunun ledger'ı altın ledger'la aynıysa sayı artsa da sonuç aynıdır.")

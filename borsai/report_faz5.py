"""docs/MODELS.md'nin Faz 5 bölümü: D1 sonrası güncelleme `post_d1_hazard_v0` (SPEC_POST_D1_V0).

Girdi: tests/reference/macos_golden_faz5/ (Faz 5 resmi koşusunun ledger'ı ve nihai fit önizlemesi), Faz 1B tavan
ledger'ları (karşılaştırıcı ve kurallar; yeniden koşulmaz, §6.1-7 (v)), Faz 4 `ceiling_path_v0` ledger'ı ve hücreleri
(`path_conditional` karşılaştırması), experiments/log.jsonl ve şartnamenin §5 beklenti tablosu (dosyadan AYNEN okunur).
Altın dizin yoksa bölüm üretilmez (commit A: kod ve kurallar, sonuç yok).

Ölçek: bütün hücreler **koşullu (j = 1)**, `scale = backtest_conditional`; koşulsuz tablolarla toplanmaz (`ScaleMixError`,
borsai/scoring.py `_one_scale`). Metrikler ortak fonksiyonlar: `predict_path.conditional_rps`, `conditional_brier`; aralık
SPEC_DEVIATIONS C7 (`metrics.paired_difference`: ilk işlem ayı blokları, 4000, `random.Random(20260921)`; RPS/Brier
kırpmasız; p_up Brier [0.01, 0.99]).

§5 satırlarının etiketi ve (a)–(d), "beklentiden çok iyi", canlı akış koşulu `OPERATIONAL_RULES_FAZ5`'teki kurallarla
verilir; kurallar Faz 5 backtest sonuçları görülmeden, bu dosya yazılırken (commit A) sabitlendi ve raporda yazılıdır.
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from . import metrics as mx
from . import predict_path as pth
from . import report_faz1b as rf
from . import survival as sv
from .provenance import ROOT
from .specs import PLAN_POST_D1, POST_D1_MODEL_SPECS, SPEC_DOCUMENTS_FAZ5

MODEL = "post_d1_hazard_v0"
SPEC_PATH = ROOT / SPEC_DOCUMENTS_FAZ5["SPEC_POST_D1_V0"]["path"]
SCALE = "backtest_conditional"
J = 1
GOLDEN_FAZ5_DIR = ROOT / "tests" / "reference" / "macos_golden_faz5"

# Karşılaştırılanlar (Faz 1B tavan planı koşuları; §4 tablosu). Birincil: ceiling_hazard_v0 koşullu.
PRIMARY_COMPARATOR = "ceiling_hazard_v0"
COMPARATORS: tuple[str, ...] = ("ceiling_hazard_v0", "base_km_expanding", "base_km_last10", "ceiling_hazard_v0@INF",
                                "base_always_ceiling__ceiling")
COMPARATOR_LABEL = {"ceiling_hazard_v0": "`ceiling_hazard_v0` koşullu (karşılaştırıcı)",
                    "base_km_expanding": "`base_km_expanding` koşullu", "base_km_last10": "`base_km_last10` koşullu",
                    "ceiling_hazard_v0@INF": "`ceiling_hazard_v0@INF` koşullu",
                    "base_always_ceiling__ceiling": "`base_always_ceiling` (S_cond ≡ 1)"}
METRICS: tuple[str, ...] = ("rps", "brier2", "brier10")
METRIC_LABEL = {"rps": "RPS_1 (k = 2..10)", "brier2": "Brier k = 2", "brier10": "Brier k = 10"}
EXPLORATORY_KS = tuple(range(3, sv.DAYS))       # keşif: Brier k = 3..9
PATH_HORIZONS = (3, 5, 10)
CALIBRATION_KS = (2, 3, 5, 10)

# §5 "beklentiden çok iyi" ve başarısızlık tanımlarının sayıları (şartnameden aynen).
TOO_GOOD_PRIMARY_DIFF = -0.040
TOO_GOOD_PRIMARY_CI_HI = -0.020
TOO_GOOD_BRIER2_DIFF = -0.040
FAIL_B_INF_SHARE = 0.80
FAIL_C_CALIBRATION = 0.10
FAIL_C_MIN_N = 30
CALIBRATION_EXPECTED = 0.05
EARLY_FOLDS = rf.EARLY_FOLDS        # "erken fold" = kronolojik ilk 20 (Faz 1B tanımı)
MOST = rf.MOST                      # "çoğu": > %50 (Faz 1B tanımı)
LOCK_SIGN_SHARE = 0.80
N_FOLDS_RANGE = (65, 71)
LAMBDA_FINAL_LIKELY = (10.0, 100.0)
LAMBDA_FOLD_INF_SHARE = (0.20, 0.50)

VERDICT_BACKTEST = {
    "MODEL_DAHA_IYI": "**backtest'te geçiyor (tasarıma maruz)**",
    "KURAL_DAHA_IYI": "**karşılaştırılan daha iyi** (aralık 0'ın üstünde)",
    "AYIRT_EDILEMIYOR": "ayırt edilemiyor (aralık 0'ı içeriyor)",
}

# §5 "Aralık 0'ı" sütunu -> kategori (kesin kısım etiketi etkiler; olasılık ifadeleri yalnız yan sütunda).
CI_CATEGORY = {
    "büyük olasılıkla içerir → \"ayırt edilemiyor\"": "LIKELY_INCLUDES",
    "dışlaması olası": "MAY_EXCLUDE_NEG",
    "dışlar": "EXCLUDES_NEG",
    "içerir ya da negatif dışlar; kazanç en olası bu hücrede": "NOT_POS",
    "dışlayabilir": "MAY_EXCLUDE_NEG",
    "dışlar (olası)": "MAY_EXCLUDE_NEG",
    "içerir": "INCLUDES",
    "—": None,
}

OPERATIONAL_RULES_FAZ5 = (
    "Fark satırlarında (§5 tablosunun ilk 12 satırı) beklenen fark [alt, üst] kapalı aralıktır; \"(nokta ≈ x)\" bilgi amaçlıdır, "
    "değerlendirilmez. Fark = model − karşılaştırılan, negatif = model iyi. Fark alt ucun altındaysa **tutmadı (daha iyi)**, "
    "üst ucun üstündeyse **tutmadı (daha kötü)**.",
    "Fark aralık içindeyse \"Aralık 0'ı\" ifadesinin kesin kısmına bakılır: \"içerir\" → %95 aralık 0'ı içermeli; \"dışlar\" → "
    "aralığın üst ucu < 0; \"içerir ya da negatif dışlar\" → alt uç ≤ 0 (aralık 0'ı pozitif tarafta dışlamıyor); \"dışlaması "
    "olası\" / \"dışlayabilir\" / \"dışlar (olası)\" → alt uç ≤ 0; \"büyük olasılıkla içerir\" → kesin kısım yok. Kesin kısım "
    "tutuyorsa **tuttu**, tutmuyorsa **tutmadı (aralık)**. İfadenin tamamı (olasılık kısmı dahil: \"dışlaması olası\" → üst uç "
    "< 0; \"büyük olasılıkla içerir\" → 0'ı içerir) ayrı sütunda yazılır.",
    "Kalibrasyon satırı: |ort(h_2) − gözlenen D2 kırılma oranı| ≤ 0.05 → tuttu; h_2 = ledger'daki hazard_2, gözlenen = 1[L = 1] "
    "ortalaması, modelin FIT_OK fold'larında.",
    "λ nihai fit: seçilen λ ∈ [10, 100] → tuttu; λ = INF → tuttu (\"INF olası\" dendi); diğer λ → tutmadı (daha küçük / daha "
    "büyük).",
    f"λ fold'lar (iki parça): \"erken fold'larda INF\" = kronolojik ilk {EARLY_FOLDS} FIT_OK fold'un > %{MOST * 100:.0f}'sinde INF; "
    "\"fold'ların %20–50'sinde INF\" = FIT_OK fold'larda INF payı [0.20, 0.50]. İkisi tutarsa tuttu, hiçbiri tutmazsa tutmadı, "
    "aksi halde kısmen (tutmayan parça adıyla).",
    f"δ_lock işareti (iki parça): nihai fit'te δ_lock < 0; λ < INF olan FIT_OK fold'lardan d1_lock'un düşmediklerinde "
    f"δ_lock < 0 payı ≥ %{LOCK_SIGN_SHARE * 100:.0f} (düşen fold'lar paydada değil, ayrıca sayılır). Çok parça kuralı yukarıdaki gibi.",
    "δ_turn işareti: nihai fit'te δ_turn > 0 → tuttu; aksi halde tutmadı (< 0 ya da = 0 yönüyle).",
    f"n (fold): birincil hücrenin eşleşik n'i [{N_FOLDS_RANGE[0]}, {N_FOLDS_RANGE[1]}] → tuttu.",
    "Kazanç/kayıp/eşitlik: arz başına kayıp farkının işareti; fark bit-eşit 0 ise eşitlik (MODELS.md kuralı). Eşleşik küme: iki "
    "tarafın da skorlandığı (L ≥ 1) test arzları, ticker ile; karşılaştırılanın S_1 = 0 olduğu çift o hücreden düşer.",
    f"Başarısızlık (a): birincil hücre aralığının alt ucu > 0. (b): nihai fit'te λ = INF ya da δ fit'i yapılan (FIT_OK) fold'ların "
    f"≥ %{FAIL_B_INF_SHARE * 100:.0f}'inde INF (INSUFFICIENT_TRAINING_HISTORY ve NOT_APPLICABLE paydada değil). (c): n ≥ "
    f"{FAIL_C_MIN_N} iken |ort(h_2) − gözlenen D2 kırılma oranı| > {FAIL_C_CALIBRATION}. (d): λ = INF fold'larında modelin "
    "S_cond'u aynı fold'un karşılaştırıcı S_cond'una bit-eşit değil ya da herhangi bir FIT_OK fold'da h_1 ana modelinkine "
    "(Faz 1B ledger'ı hazard_1) bit-eşit değil.",
    f"Beklentiden çok iyi (§5): birincil fark < {TOO_GOOD_PRIMARY_DIFF:.3f} ya da birincil aralığın üst ucu < "
    f"{TOO_GOOD_PRIMARY_CI_HI:.3f} ya da Brier k = 2 farkı (`ceiling_hazard_v0` koşullu) < {TOO_GOOD_BRIER2_DIFF:.3f}. Tetiklense de "
    "tetiklenmese de sıradaki adım Fable'ın sıfırdan yeniden üretimidir (ledger'lar |Δ| ≤ 1e-9).",
    "Canlı akış koşulu (proje sahibi kararı 3): (b) gerçekleşirse canlı POST_D1 akışı şimdi **kurulmaz**; λ sonlu ve (b) yoksa "
    "**kurulur**. Model her iki durumda da dondurulur (ayrı görev).",
    "\"Kazanç en olası Brier k = 2'de\" cümlesi: `ceiling_hazard_v0` koşullu karşısındaki dört hücreden (RPS_1, Brier k = 2, "
    "k = 3, k = 10) en negatif fark Brier k = 2'deyse tuttu.",
)

# Bağımsız yeniden üretim (§5 "beklentiden çok iyi" tetiklendiği için şart) ve dondurma (BORSAI_FAZ5_FREEZE_20260924).
# Bölüm yalnız `models/INDEX_POST_D1.json` bu modeli listeliyorsa yazılır; sayılar denetim raporundan (AUDIT §0).
REPRO = {
    "doc": "docs/fable_faz5_audit/AUDIT.md",
    "dir": "docs/fable_faz5_audit/",
    "date": "2026-09-24",
    "max_abs": "1.5e-11",
}
# AUDIT §5-3: k = 10 dipnotu (hüküm değişmez; model davranışı şartnamedeki v0).
K10_FOOTNOTE = ("k = 10 dipnotu: δ bütün d = 2..10'da ortak olduğundan kilit bilgisi D4–D10'a da taşınır; k = 10 hafif "
                f"kötüleşir (`{REPRO['doc']}` §5-3); gün-grubu etkileşimi yeni model_id'dir.")
POST_D1_INDEX_PATH = ROOT / "models" / "INDEX_POST_D1.json"


# ---------------------------------------------------------------------------
# Veri
# ---------------------------------------------------------------------------

def _read(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def golden_available(faz5_dir: Path = GOLDEN_FAZ5_DIR) -> bool:
    return (Path(faz5_dir) / "MANIFEST.json").exists()


def load_faz5(faz5_dir: Path = GOLDEN_FAZ5_DIR) -> tuple[list[dict[str, str]], dict[str, Any], dict[str, Any]]:
    """(ledger satırları, MANIFEST, nihai fit önizlemesi)."""
    from .post_d1 import FINAL_PREVIEW_FILE, golden_filename

    d = Path(faz5_dir)
    manifest = json.loads((d / "MANIFEST.json").read_text(encoding="utf-8"))
    return _read(d / golden_filename()), manifest, json.loads((d / FINAL_PREVIEW_FILE).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Koşullu kayıplar ve eşleşik karşılaştırma (T6 bu fonksiyonla MODELS.md j = 1 satırını yeniden üretir)
# ---------------------------------------------------------------------------

def _S(r: Mapping[str, str]) -> list[float]:
    return [float(r[f"S_{k}"]) for k in range(1, sv.DAYS + 1)]


def ok_conditional(r: Mapping[str, str]) -> bool:
    """Skorlanmış satır (model FIT_OK, kural RULE_OK) ve seri j = 1'de sürüyor (L ≥ 1)."""
    return r["status"] in ("FIT_OK", "RULE_OK") and int(r["realized_L"]) >= J


def cond_loss(metric: str, S: Sequence[float], L: int) -> Optional[float]:
    """Koşullu kayıp (ortak fonksiyonlar); S_1 = 0 ise None (koşul tanımsız, SPEC_DEVIATIONS G6)."""
    if S[J - 1] <= 0.0:
        return None
    if metric == "rps":
        return pth.conditional_rps(S, J, L)
    return pth.conditional_brier(S, J, L, int(metric[len("brier"):]))


def summarize(obs: Sequence[Any]) -> Optional[dict[str, Any]]:
    """Eşleşik fark + C7 aralığı. Gözlemler tek ölçekte olmalı (ScaleMixError)."""
    from . import scoring as sc

    if not obs:
        return None
    scale = sc._one_scale(obs)
    if scale != SCALE:
        raise sc.ScaleMixError(f"Faz 5 hücreleri yalnız {SCALE} ölçeğindedir: {scale}")
    diffs = [o.model_loss - o.rule_loss for o in obs]
    months = [o.block for o in obs]
    if len(diffs) >= 10:
        res = mx.paired_difference(diffs, months)
    else:
        res = {"n": len(diffs), "n_months": len(set(months)), "mean": sum(diffs) / len(diffs), "ci95": None,
               "model_better_n": sum(1 for d in diffs if d < 0), "rule_better_n": sum(1 for d in diffs if d > 0),
               "tie_n": sum(1 for d in diffs if d == 0), "verdict": None}
    res.update(model_metric=sum(o.model_loss for o in obs) / len(obs), rule_metric=sum(o.rule_loss for o in obs) / len(obs),
               scale=SCALE, j=J)
    return res


def conditional_obs(model_rows: Sequence[Mapping[str, str]], other_rows: Sequence[Mapping[str, str]], metric: str) -> list[Any]:
    from . import scoring as sc

    other = {r["ticker"]: r for r in other_rows if ok_conditional(r)}
    obs = []
    for r in model_rows:
        o = other.get(r["ticker"])
        if o is None or not ok_conditional(r):
            continue
        L = int(r["realized_L"])
        a, b = cond_loss(metric, _S(r), L), cond_loss(metric, _S(o), L)
        if a is None or b is None:
            continue
        obs.append(sc.PairedObs(scale=SCALE, ticker=r["ticker"], block=r["first_trading_date"][:7], model_loss=a, rule_loss=b, j=J))
    return obs


def paired_conditional(model_rows, other_rows, metric: str) -> Optional[dict[str, Any]]:
    return summarize(conditional_obs(model_rows, other_rows, metric))


def own_mean(rows: Sequence[Mapping[str, str]], metric: str) -> Optional[float]:
    vals = [cond_loss(metric, _S(r), int(r["realized_L"])) for r in rows if ok_conditional(r)]
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else None


# ---------------------------------------------------------------------------
# path_conditional (ikincil)
# ---------------------------------------------------------------------------

def path_obs(ledger: Sequence[Mapping[str, str]], comparator: Mapping[str, Mapping[int, Mapping[str, float]]],
             realized: Mapping[str, Mapping[int, Mapping[str, float]]], h: int, output: str) -> tuple[list[Any], dict[str, int]]:
    """(gözlemler, sayım). Blok null (NOT_PRODUCED) ya da hücre yetersiz satır sayılır ama skorlanmaz (§11-11)."""
    from . import scoring as sc

    counts: Counter = Counter()
    obs = []
    for r in ledger:
        if r["status"] != "FIT_OK":
            continue
        counts[r["path_cond_status"]] += 1
        own = r[f"path_cond_h{h}_{'median' if output == 'MAE' else 'p_up'}"]
        cmp = comparator.get(r["fold_id"], {}).get(h)
        if own == "" or cmp is None or cmp.get("return") is None:
            continue
        real = realized[r["ticker"]][h]
        if output == "MAE":
            a, b = abs(float(own) - real["R"]), abs(cmp["return"] - real["R"])
        else:
            a, b = mx.brier_term(float(own), real["Y"]), mx.brier_term(cmp["p_up"], real["Y"])
        obs.append(sc.PairedObs(scale=SCALE, ticker=r["ticker"], block=r["first_trading_date"][:7], model_loss=a, rule_loss=b, j=J))
    return obs, dict(counts)


def path_comparator(dataset, ledger: Sequence[Mapping[str, str]]) -> dict[str, dict[int, dict[str, float]]]:
    """`ceiling_path_v0`'ın kendi j = 1 koşullu karışımı, aynı fold'un hücreleri ve S'iyle (Faz 4 ledger'ı, yeniden fit yok)."""
    from decimal import Decimal

    from . import post_d1 as pd

    path_rows, _ = pd.read_pinned_csv(POST_D1_MODEL_SPECS[MODEL]["path_ledger"])
    cells_by = pd.path_cells_by_fold(dataset, path_rows)
    template = pd.load_path_template()
    by = dataset.by_ticker()
    d1 = pd.load_d1_sessions()[0]
    prow = {r["fold_id"]: r for r in path_rows}
    out: dict[str, dict[int, dict[str, float]]] = {}
    for r in ledger:
        if r["status"] != "FIT_OK" or r["fold_id"] not in cells_by:
            continue
        S = [float(prow[r["fold_id"]][f"S_{k}"]) for k in range(1, sv.DAYS + 1)]
        cond = pth.conditional(pd.fold_path_params(template, cells_by[r["fold_id"]]),
                               pd.fold_path_output(Decimal(by[r["ticker"]].inputs["ipo_price_tl"]), S), J,
                               [d1[r["ticker"]].fields_raw["close"]])
        out[r["fold_id"]] = {h: {"return": cond[f"D{h}"]["return"], "p_up": cond[f"D{h}"]["p_up"]} for h in PATH_HORIZONS}
    return out


def realized_of(dataset) -> dict[str, dict[int, dict[str, float]]]:
    return {r.ticker: {h: {"R": r.targets[f"D{h}"].R_float, "Y": r.targets[f"D{h}"].Y} for h in PATH_HORIZONS} for r in dataset.rows}


# ---------------------------------------------------------------------------
# §5 tablosu (şartname dosyasından aynen) ve etiketler
# ---------------------------------------------------------------------------

EXPECTED_ROWS: tuple[tuple[str, str, dict[str, Any]], ...] = (
    ("RPS_1 (BİRİNCİL)", "`ceiling_hazard_v0` koşullu", {"kind": "diff", "metric": "rps", "comparator": "ceiling_hazard_v0", "primary": True}),
    ("RPS_1", "`ceiling_hazard_v0@INF` koşullu", {"kind": "diff", "metric": "rps", "comparator": "ceiling_hazard_v0@INF"}),
    ("RPS_1", "`base_km_expanding` koşullu", {"kind": "diff", "metric": "rps", "comparator": "base_km_expanding"}),
    ("RPS_1", "`base_km_last10` koşullu", {"kind": "diff", "metric": "rps", "comparator": "base_km_last10"}),
    ("RPS_1", "her-zaman-tavan", {"kind": "diff", "metric": "rps", "comparator": "base_always_ceiling__ceiling"}),
    ("Brier k = 2", "`ceiling_hazard_v0` koşullu", {"kind": "diff", "metric": "brier2", "comparator": "ceiling_hazard_v0"}),
    ("Brier k = 2", "`@INF` koşullu", {"kind": "diff", "metric": "brier2", "comparator": "ceiling_hazard_v0@INF"}),
    ("Brier k = 2", "`base_km_last10` koşullu", {"kind": "diff", "metric": "brier2", "comparator": "base_km_last10"}),
    ("Brier k = 10", "`ceiling_hazard_v0` koşullu", {"kind": "diff", "metric": "brier10", "comparator": "ceiling_hazard_v0"}),
    ("Brier k = 3 (keşif)", "`ceiling_hazard_v0` koşullu", {"kind": "diff", "metric": "brier3", "comparator": "ceiling_hazard_v0"}),
    ("`path_conditional` h = 5 MAE", "`ceiling_path_v0` koşullu (j = 1)", {"kind": "path", "h": 5, "output": "MAE"}),
    ("`path_conditional` h = 3 p_up Brier", "`ceiling_path_v0` koşullu", {"kind": "path", "h": 3, "output": "Brier"}),
    ("Kalibrasyon", "ort(h_2) − gözlenen D2 kırılma oranı", {"kind": "calibration"}),
    ("λ", "nihai fit", {"kind": "lambda_final"}),
    ("λ", "fold'lar", {"kind": "lambda_folds"}),
    ("δ_lock işareti", "nihai fit ve λ < INF fold'ları", {"kind": "sign_lock"}),
    ("δ_turn işareti", "nihai fit", {"kind": "sign_turn"}),
    ("n (fold)", "—", {"kind": "n_folds"}),
)


def _plain(text: str) -> str:
    return text.replace("**", "").strip()


def parse_range(text: str) -> tuple[float, float]:
    """'−0.020 … +0.003 (nokta ≈ −0.008)' -> (−0.020, 0.003); parantez içi bilgi amaçlıdır."""
    t = _plain(text).split("(")[0].replace("−", "-")
    lo, hi = (float(p.strip()) for p in t.split("…"))
    return lo, hi


def expectation_rows(spec_text: Optional[str] = None) -> list[dict[str, Any]]:
    """§5 tablosunun 18 satırı, aynen; her satır `EXPECTED_ROWS`'taki değerlendiriciyle eşlenir (sıra ve metin denetlenir)."""
    from .report_faz4 import _split_row

    text = spec_text if spec_text is not None else SPEC_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("| Hücre | Karşılaştırılan | Beklenen fark (model − karş.)"))
    out = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        cell, comp, rng, ci, why = _split_row(line)
        out.append({"raw": {"hucre": cell, "karsilastirilan": comp, "beklenen": rng, "sifir": ci, "gerekce": why}})
    if len(out) != len(EXPECTED_ROWS):
        raise ValueError(f"§5 tablosu {len(out)} satır; beklenen {len(EXPECTED_ROWS)}")
    for row, (cell, comp, ev) in zip(out, EXPECTED_ROWS):
        if (_plain(row["raw"]["hucre"]), _plain(row["raw"]["karsilastirilan"])) != (cell, comp):
            raise ValueError(f"§5 satırı beklenenden farklı: {row['raw']}")
        row.update(ev)
        row.setdefault("primary", False)
        row["ci_category"] = CI_CATEGORY[_plain(row["raw"]["sifir"])]
        if ev["kind"] in ("diff", "path"):
            row["lo"], row["hi"] = parse_range(row["raw"]["beklenen"])
    return out


def ci_firm_holds(category: Optional[str], ci: Optional[Sequence[float]]) -> bool:
    if category in (None, "LIKELY_INCLUDES"):
        return True
    if ci is None:
        return False
    lo, hi = ci
    return {"INCLUDES": lo <= 0.0 <= hi, "EXCLUDES_NEG": hi < 0.0, "NOT_POS": lo <= 0.0, "MAY_EXCLUDE_NEG": lo <= 0.0}[category]


def ci_statement_holds(category: Optional[str], ci: Optional[Sequence[float]]) -> Optional[bool]:
    if category is None:
        return None
    if ci is None:
        return False
    lo, hi = ci
    return {"INCLUDES": lo <= 0.0 <= hi, "EXCLUDES_NEG": hi < 0.0, "NOT_POS": lo <= 0.0, "MAY_EXCLUDE_NEG": hi < 0.0,
            "LIKELY_INCLUDES": lo <= 0.0 <= hi}[category]


def diff_label(row: Mapping[str, Any], p: Optional[Mapping[str, Any]]) -> str:
    if p is None:
        return "tutmadı (hücre yok)"
    d = p["mean"]
    if d < row["lo"]:
        return "tutmadı (daha iyi)"
    if d > row["hi"]:
        return "tutmadı (daha kötü)"
    return "tuttu" if ci_firm_holds(row["ci_category"], p["ci95"]) else "tutmadı (aralık)"


def _combine(parts: Sequence[tuple[str, bool]]) -> str:
    held = [ok for _, ok in parts]
    if all(held):
        return "tuttu"
    if not any(held):
        return "tutmadı"
    return "kısmen (tutmayan: " + "; ".join(name for name, ok in parts if not ok) + ")"


def _lam(x: Any) -> float:
    return float("inf") if str(x) == "INF" else float(x)


def fold_summary(ledger: Sequence[Mapping[str, str]], runs: Mapping[str, Sequence[Mapping[str, str]]]) -> dict[str, Any]:
    """Fold durumları, λ dağılımı, δ işaretleri, T7 (INF fold'larında S_cond farkı), T9 ((b)'nin paydası), h_1 paritesi."""
    statuses = Counter(r["status"] for r in ledger)
    ok = [r for r in ledger if r["status"] == "FIT_OK"]
    lam = Counter(r["selected_lambda"] for r in ok)
    inf = [r for r in ok if r["selected_lambda"] == "INF"]
    early = ok[:EARLY_FOLDS]
    parent = {r["ticker"]: r for r in runs[PRIMARY_COMPARATOR]}
    t7 = []
    for r in inf:
        S_cmp, _ = pth.conditional_weights(_S(parent[r["ticker"]]), J)
        t7.append(max(abs(float(r[f"S_cond_{k}"]) - S_cmp[k]) for k in range(2, sv.DAYS + 1)))
    h1_mismatch = [r["fold_id"] for r in ok if float(r["hazard_1"]) != float(parent[r["ticker"]]["hazard_1"])]
    finite = [r for r in ok if r["selected_lambda"] != "INF"]
    lock_active = [r for r in finite if "d1_lock" in json.loads(r["columns"])]
    return {
        "n_folds": len(ledger), "statuses": dict(statuses), "n_fit_ok": len(ok), "lambda": dict(lam),
        "n_inf": len(inf), "inf_share": len(inf) / len(ok) if ok else None,
        "early_n": len(early), "early_inf": sum(1 for r in early if r["selected_lambda"] == "INF"),
        "t7_max_abs": max(t7) if t7 else None, "t7_n": len(t7), "h1_mismatch": h1_mismatch,
        "n_finite": len(finite), "lock_active": len(lock_active), "lock_dropped": len(finite) - len(lock_active),
        "lock_neg": sum(1 for r in lock_active if float(r["delta_d1_lock"]) < 0),
        "turn_neg": sum(1 for r in finite if float(r["delta_d1_turnover"]) < 0),
        "turn_pos": sum(1 for r in finite if float(r["delta_d1_turnover"]) > 0),
        "path_status": dict(Counter(r["path_cond_status"] for r in ok)),
        "insufficient": statuses.get("INSUFFICIENT_TRAINING_HISTORY", 0),
        "not_applicable": statuses.get("NOT_APPLICABLE", 0),
    }


def calibration(ledger: Sequence[Mapping[str, str]], runs: Mapping[str, Sequence[Mapping[str, str]]]) -> dict[str, Any]:
    """ort(h_2) ve gözlenen D2 kırılma oranı; ort(S_cond[k]) ve gözlenen 1[L ≥ k], k = 2, 3, 5, 10 (model ve karşılaştırıcı)."""
    ok = [r for r in ledger if r["status"] == "FIT_OK"]
    parent = {r["ticker"]: r for r in runs[PRIMARY_COMPARATOR]}
    L = [int(r["realized_L"]) for r in ok]
    out: dict[str, Any] = {"n": len(ok), "mean_h2": statistics.mean(float(r["hazard_2"]) for r in ok) if ok else None,
                           "observed_break_d2": statistics.mean(float(x == 1) for x in L) if ok else None, "k": {}}
    for k in CALIBRATION_KS:
        cmp = [pth.conditional_weights(_S(parent[r["ticker"]]), J)[0][k] for r in ok]
        out["k"][k] = {"model": statistics.mean(float(r[f"S_cond_{k}"]) for r in ok) if ok else None,
                       "comparator": statistics.mean(cmp) if cmp else None,
                       "observed": statistics.mean(float(x >= k) for x in L) if ok else None}
    out["cmp_mean_h2"] = statistics.mean(1.0 - pth.conditional_weights(_S(parent[r["ticker"]]), J)[0][2] for r in ok) if ok else None
    return out


def evaluate(ledger: Sequence[Mapping[str, str]], runs: Mapping[str, Sequence[Mapping[str, str]]],
             path_cmp: Mapping[str, Any], realized: Mapping[str, Any], preview: Mapping[str, Any],
             spec_text: Optional[str] = None) -> dict[str, Any]:
    """§5 tablosunun her satırı + (a)–(d) + çok iyi + canlı akış koşulu (OPERATIONAL_RULES_FAZ5)."""
    fs = fold_summary(ledger, runs)
    cal = calibration(ledger, runs)
    cells = {(m, c): paired_conditional(ledger, runs[c], m) for m in METRICS + ("brier3",) for c in COMPARATORS}
    path_cells = {(h, o): summarize(path_obs(ledger, path_cmp, realized, h, o)[0]) for h in PATH_HORIZONS for o in ("MAE", "Brier")}
    final_lam = _lam(preview["lambda"])
    rows = []
    for row in expectation_rows(spec_text):
        kind, res, label, held_stmt, got = row["kind"], None, None, None, ""
        if kind in ("diff", "path"):
            res = cells[(row["metric"], row["comparator"])] if kind == "diff" else path_cells[(row["h"], row["output"])]
            label, held_stmt = diff_label(row, res), ci_statement_holds(row["ci_category"], res and res["ci95"])
        elif kind == "calibration":
            d = cal["mean_h2"] - cal["observed_break_d2"]
            label = "tuttu" if abs(d) <= CALIBRATION_EXPECTED else ("tutmadı (model yüksek)" if d > 0 else "tutmadı (model düşük)")
            got = f"ort(h_2) {rf._f(cal['mean_h2'])} − gözlenen {rf._f(cal['observed_break_d2'])} = {rf._s(d)} (n = {cal['n']})"
        elif kind == "lambda_final":
            lo, hi = LAMBDA_FINAL_LIKELY
            if final_lam == float("inf"):
                label = "tuttu (INF: \"INF olası\")"
            elif lo <= final_lam <= hi:
                label = "tuttu"
            else:
                label = "tutmadı (daha küçük λ)" if final_lam < lo else "tutmadı (daha büyük λ)"
            got = f"λ = {preview['lambda']}"
        elif kind == "lambda_folds":
            share = fs["inf_share"]
            early = fs["early_inf"] / fs["early_n"] if fs["early_n"] else 0.0
            parts = [("erken fold'larda INF", early > MOST),
                     ("fold'ların %20–50'sinde INF", LAMBDA_FOLD_INF_SHARE[0] <= share <= LAMBDA_FOLD_INF_SHARE[1])]
            label = _combine(parts)
            got = (f"INF {fs['n_inf']}/{fs['n_fit_ok']} FIT_OK fold ({rf._pct(share)}); ilk {fs['early_n']} fold'da INF "
                   f"{fs['early_inf']} ({rf._pct(early)})")
        elif kind == "sign_lock":
            final_neg = preview["delta"]["d1_lock"] < 0
            share = fs["lock_neg"] / fs["lock_active"] if fs["lock_active"] else 0.0
            label = _combine([("nihai fit δ_lock < 0", final_neg), ("λ < INF fold'larının ≥ %80'inde < 0", share >= LOCK_SIGN_SHARE)])
            got = (f"nihai δ_lock = {preview['delta']['d1_lock']:+.4f}; λ < INF fold'larında < 0: {fs['lock_neg']}/{fs['lock_active']}"
                   f" (d1_lock düşen: {fs['lock_dropped']})")
        elif kind == "sign_turn":
            v = preview["delta"]["d1_turnover"]
            label = "tuttu" if v > 0 else ("tutmadı (< 0)" if v < 0 else "tutmadı (= 0)")
            got = f"nihai δ_turn = {v:+.4f}; λ < INF fold'larında > 0 / < 0: {fs['turn_pos']} / {fs['turn_neg']}"
        elif kind == "n_folds":
            n = cells[("rps", PRIMARY_COMPARATOR)]["n"] if cells[("rps", PRIMARY_COMPARATOR)] else 0
            label = "tuttu" if N_FOLDS_RANGE[0] <= n <= N_FOLDS_RANGE[1] else ("tutmadı (az)" if n < N_FOLDS_RANGE[0] else "tutmadı (çok)")
            got = f"n = {n}"
        rows.append({**row, "result": res, "label": label, "ci_statement_held": held_stmt, "got": got})
    prim = cells[("rps", PRIMARY_COMPARATOR)]
    b2 = cells[("brier2", PRIMARY_COMPARATOR)]
    reasons = []
    if prim["mean"] < TOO_GOOD_PRIMARY_DIFF:
        reasons.append(f"birincil fark {rf._s(prim['mean'])} < {TOO_GOOD_PRIMARY_DIFF:.3f}")
    if prim["ci95"][1] < TOO_GOOD_PRIMARY_CI_HI:
        reasons.append(f"birincil aralığın üst ucu {rf._s(prim['ci95'][1])} < {TOO_GOOD_PRIMARY_CI_HI:.3f}")
    if b2["mean"] < TOO_GOOD_BRIER2_DIFF:
        reasons.append(f"Brier k = 2 farkı {rf._s(b2['mean'])} < {TOO_GOOD_BRIER2_DIFF:.3f}")
    fail_b = final_lam == float("inf") or (fs["inf_share"] is not None and fs["inf_share"] >= FAIL_B_INF_SHARE)
    cal_d = cal["mean_h2"] - cal["observed_break_d2"]
    fail_d = bool(fs["h1_mismatch"]) or (fs["t7_max_abs"] is not None and fs["t7_max_abs"] != 0.0)
    gains = {m: cells[(m, PRIMARY_COMPARATOR)]["mean"] for m in ("rps", "brier2", "brier3", "brier10")}
    return {
        "rows": rows, "cells": cells, "path_cells": path_cells, "fold": fs, "calibration": cal, "primary": prim,
        "too_good": {"triggered": bool(reasons), "reasons": reasons},
        "failures": {"a": prim["ci95"][0] > 0.0, "b": fail_b, "c": cal["n"] >= FAIL_C_MIN_N and abs(cal_d) > FAIL_C_CALIBRATION,
                     "d": fail_d},
        "live_flow": "kurulmaz" if fail_b else "kurulur",
        "final_lambda": preview["lambda"],
        "gain_most_likely_brier2": min(gains, key=lambda m: gains[m]) == "brier2",
        "gains": gains,
    }


# ---------------------------------------------------------------------------
# Biçim
# ---------------------------------------------------------------------------

_f, _s, _cell, _pct = rf._f, rf._s, rf._cell, rf._pct


def _ci(p: Optional[Mapping[str, Any]]) -> str:
    return "—" if p is None or p.get("ci95") is None else rf._ci(p)


def _pair_row(cells: Sequence[str], p: Optional[Mapping[str, Any]]) -> str:
    if p is None:
        return "| " + " | ".join(list(cells) + ["0", "—", "—", "—", "—", "—", "—"]) + " |"
    verdict = VERDICT_BACKTEST[p["verdict"]] if p.get("verdict") else "n < 10: yalnız satır"
    return ("| " + " | ".join(list(cells) + [
        f"{p['n']} ({p['n_months']})", _f(p["model_metric"]), _f(p["rule_metric"]), _s(p["mean"]), _ci(p),
        f"{p['model_better_n']} / {p['rule_better_n']} / {p['tie_n']}", verdict]) + " |")


def _lambda_text(x: Any) -> str:
    return "INF" if str(x) == "INF" else f"{float(x):g}"


def render_faz5(w: Callable[[str], None], log_path: Path, *, faz5_dir: Path = GOLDEN_FAZ5_DIR, runs: Optional[dict] = None,
                dataset=None) -> None:
    """Altın dizin yoksa hiçbir şey yazmaz."""
    if not golden_available(faz5_dir):
        return
    from .data import load_dataset

    ledger, manifest, preview = load_faz5(faz5_dir)
    runs = runs if runs is not None else rf.load_runs()
    dataset = dataset if dataset is not None else load_dataset()
    ev = evaluate(ledger, runs, path_comparator(dataset, ledger), realized_of(dataset), preview)
    spec = POST_D1_MODEL_SPECS[MODEL]
    doc = SPEC_DOCUMENTS_FAZ5["SPEC_POST_D1_V0"]
    fs, cal, prim = ev["fold"], ev["calibration"], ev["primary"]
    w("## Faz 5: D1 sonrası güncelleme (Fable şartnamesi, docs/specs_faz5/)")
    w("")
    w("**Terazi ve ölçek:** aşağıdaki her sayı **backtest**tir (retrospektif walk-forward, H99) ve **tasarıma maruzdur** (§10); kanıt "
      "değeri düşüktür, asıl ölçüm prospektiftir. Bütün hücreler **koşullu ölçektedir** (\"bugün D1 tavan kapandı\", j = 1, "
      f"`scale = {SCALE}`): koşulsuz tablolarla (yukarıdaki Faz 1A/1B/4 bölümleri) **toplanmaz ve karşılaştırılmaz**. Model "
      "**dondurulmadı** (Fable'ın sıfırdan yeniden üretiminden sonra ayrı görev); canlı sicilde satırı yoktur. \"Geçiyor\" yalnız "
      "aralık 0'ı dışlıyorsa ve yalnız \"backtest'te geçiyor (tasarıma maruz)\" biçiminde yazılır.")
    w("")
    w(f"Şartname: `{doc['path']}` (sha256 `{doc['sha256'][:12]}…`, commit c20c092, push kanıtı 2026-09-24T00:44:25Z, uygulamadan "
      "önce). Model: dondurulmuş `ceiling_hazard_v0`'ın doğrusal öngörücüsü sabit ofset; d = 2..10 hazard'ına δ·u, u = z-skorlu "
      "(`d1_lock`, `d1_turnover`); h_1 ana modelden aynen; λ ∈ {0.1 … 1000, INF}, iç arz-bırak CV. λ = INF ucu karşılaştırıcının "
      "kendisidir.")
    w("")
    w(f"Plan `{PLAN_POST_D1}`: fold kümesi ve sırası Faz 1B tavan ledger'ınınki (`{spec['survival_ledger']['sha256'][:12]}`); test "
      "arzı L ≥ 1 değilse `NOT_APPLICABLE`; ofset o fold'un yeniden koşulan `ceiling_hazard_v0` fit'i (γ, β, λ ve test hazard'ları "
      "ledger'la |Δ| ≤ 1e-9, aksi halde koşu durur); δ eğitim kümesi fold'un d ≥ 2 satırları, D1 ön işlemesi fold içinde. "
      "Karşılaştırıcı ve kurallar aynı fold'un Faz 1B ledger satırından (yeniden koşulmaz). Eşleşik fark = model − karşılaştırılan, "
      f"iki tarafın da skorlandığı L ≥ 1 test arzları; %95 aralık blok bootstrap (ilk işlem ayı blokları, {mx.BOOTSTRAP_REPS} tekrar, "
      f"`random.Random({mx.BOOTSTRAP_SEED})`; SPEC_DEVIATIONS C7); koşullu RPS/Brier kırpmasız, p_up Brier [0.01, 0.99].")
    w("")
    w("Etiket kuralları (sonuçlar görülmeden kodda sabitlendi, `borsai/report_faz5.py: OPERATIONAL_RULES_FAZ5`, commit A):")
    w("")
    for rule in OPERATIONAL_RULES_FAZ5:
        w(f"- {rule}")
    w("")
    w("### Birincil hücre")
    w("")
    w(f"`{MODEL}` − `ceiling_hazard_v0` koşullu, koşullu RPS_1 (k = 2..10; önceden ilan edilen tek birincil hücre): **fark "
      f"{_s(prim['mean'])}, %95 aralık {_ci(prim)}, n = {prim['n']}** ({prim['n_months']} ay); model {_f(prim['model_metric'])}, "
      f"karşılaştırıcı {_f(prim['rule_metric'])}; model iyi / karşılaştırıcı iyi / eşit {prim['model_better_n']} / "
      f"{prim['rule_better_n']} / {prim['tie_n']}. Hüküm (backtest): {VERDICT_BACKTEST[prim['verdict']]}. §5 beklentisi "
      f"−0.020 … +0.003 → **{ev['rows'][0]['label']}**.")
    w("")
    w("### Başarısızlık tanımları (§5) ve canlı akış koşulu")
    w("")
    fl = ev["failures"]
    w(f"- **(a) D1 bilgisi zarar veriyor** (birincil aralık tamamen 0'ın üstünde): {_s(prim['mean'])} {_ci(prim)} → "
      + ("**gerçekleşti**: \"D1 sonrası model karşılaştırıcıdan kötü\"" if fl["a"] else "gerçekleşmedi") + ".")
    w(f"- **(b) D1 bilgisi eklemiyor** (nihai fit'te λ = INF, ya da δ fit'i yapılan fold'ların ≥ %80'inde INF): nihai λ = "
      f"{_lambda_text(ev['final_lambda'])}; INF {fs['n_inf']}/{fs['n_fit_ok']} FIT_OK fold ({_pct(fs['inf_share'])}); paydada "
      f"olmayanlar: INSUFFICIENT_TRAINING_HISTORY {fs['insufficient']}, NOT_APPLICABLE {fs['not_applicable']} → "
      + ("**gerçekleşti**: \"özellikler bilgi eklemiyor; model karşılaştırıcıyla özdeş\"" if fl["b"] else "gerçekleşmedi") + ".")
    w(f"- **(c) Kalibrasyon** (n ≥ 30 iken |ort(h_2) − gözlenen D2 kırılma oranı| > 0.10): ort(h_2) {_f(cal['mean_h2'])}, gözlenen "
      f"{_f(cal['observed_break_d2'])}, |fark| {_f(abs(cal['mean_h2'] - cal['observed_break_d2']))}, n = {cal['n']} → "
      + ("**gerçekleşti**: \"kalibrasyon bozuk\"" if fl["c"] else "gerçekleşmedi") + ".")
    w(f"- **(d) Parite hatası** (INF ucu karşılaştırıcıya ya da h_1 ana modele bit-eşit değil): λ = INF fold'larında maks "
      f"|S_cond − karşılaştırıcı S_cond| = {'—' if fs['t7_max_abs'] is None else repr(fs['t7_max_abs'])} ({fs['t7_n']} fold); "
      f"h_1 ≠ ana model: {len(fs['h1_mismatch'])} fold → " + ("**gerçekleşti**" if fl["d"] else "gerçekleşmedi") + ".")
    w("- (e) Prospektif (n ≥ 30): birincil aralık 0'ı pozitif tarafta dışlıyor → \"geçemiyor\". Canlı n = 0; hüküm yok.")
    w("")
    w(f"**Canlı akış koşulu (proje sahibi kararı 3): {ev['live_flow']}** — " + (
        "(b) gerçekleşti; model yine dondurulur ama canlı POST_D1 akışı şimdi kurulmaz." if fl["b"]
        else "λ sonlu ve (b) yok; canlı POST_D1 akışı (dondurma ve Fable yeniden üretiminden sonra) kurulur."))
    w("")
    w("**Beklentiden çok iyi denetimi (§5):** " + (
        "**TETİKLENDİ** (" + "; ".join(ev["too_good"]["reasons"]) + ")." if ev["too_good"]["triggered"]
        else f"tetiklenmedi (birincil fark ≥ {TOO_GOOD_PRIMARY_DIFF:.3f}, aralığın üst ucu ≥ {TOO_GOOD_PRIMARY_CI_HI:.3f}, Brier k = 2 "
             f"farkı ≥ {TOO_GOOD_BRIER2_DIFF:.3f}).")
      + " Her iki durumda da sıradaki adım Fable'ın bu şartnameden bağımsız, sıfırdan yeniden üretimidir (ledger'lar |Δ| ≤ 1e-9).")
    w("")
    w("### §5 beklentisi ile gerçekleşen (satır satır)")
    w("")
    w("| Hücre | Karşılaştırılan | Beklenen (§5, aynen) | Aralık 0'ı (§5, aynen) | Gerçekleşen | %95 aralık | n | Etiket | "
      "Aralık ifadesi gerçekleşti mi |")
    w("|---|---|---|---|---|---|---|---|---|")
    for e in ev["rows"]:
        p = e["result"]
        got = e["got"] if e["kind"] not in ("diff", "path") else ("—" if p is None else _s(p["mean"]))
        stmt = {None: "—", True: "evet", False: "hayır"}[e["ci_statement_held"]]
        lab = f"**{e['label']}**" if e["primary"] else e["label"]
        w(f"| {_cell(_plain(e['raw']['hucre']))} | {_cell(_plain(e['raw']['karsilastirilan']))} | "
          f"{_plain(e['raw']['beklenen'])} | {_plain(e['raw']['sifir'])} | {got} | "
          f"{_ci(p) if e['kind'] in ('diff', 'path') else '—'} | {p['n'] if p else ('—' if e['kind'] in ('diff', 'path') else '')} | "
          f"{lab} | {stmt} |")
    w("")
    counts = Counter(e["label"].split(" (")[0] for e in ev["rows"])
    w(f"Etiket sayıları: tuttu {counts['tuttu']}, tutmadı {counts['tutmadı']}, kısmen {counts['kısmen']} (toplam {len(ev['rows'])}).")
    w("")
    g = ev["gains"]
    w("\"Hangi hücrede kazanç en olası: **Brier k = 2**\" cümlesi (`ceiling_hazard_v0` koşullu karşısında fark): RPS_1 "
      f"{_s(g['rps'])}, Brier k = 2 {_s(g['brier2'])}, k = 3 {_s(g['brier3'])}, k = 10 {_s(g['brier10'])} → "
      + ("**tuttu**" if ev["gain_most_likely_brier2"] else "**tutmadı**") + ".")
    w("")
    w("### Bütün §4 hücreleri (koşullu ölçek, j = 1; birincil dışındakiler kural/ikincil/keşif)")
    w("")
    w("| Metrik | Karşılaştırılan " + rf.PAIR_HEADER)
    w("|---|---" + rf.PAIR_SEP)
    for m in METRICS:
        for c in COMPARATORS:
            name = COMPARATOR_LABEL[c] + (" **(BİRİNCİL)**" if (m, c) == ("rps", PRIMARY_COMPARATOR) else "")
            w(_pair_row([METRIC_LABEL[m], name], ev["cells"][(m, c)]))
    w("")
    w("Kalibrasyon (ikincil; modelin FIT_OK fold'ları, L ≥ 1): ort(h_2) model "
      f"{_f(cal['mean_h2'])} / karşılaştırıcı {_f(cal['cmp_mean_h2'])} / gözlenen D2 kırılma oranı {_f(cal['observed_break_d2'])}. "
      + "; ".join(f"k = {k}: ort(S_cond) model {_f(v['model'])} / karşılaştırıcı {_f(v['comparator'])} / gözlenen {_f(v['observed'])}"
                  for k, v in cal["k"].items()) + ".")
    w("")
    w("`path_conditional` (ikincil; `ceiling_path_v0` hücreleri ve limit yolu, S yerine bu modelin S'i; karşılaştırılan "
      "`ceiling_path_v0`'ın kendi j = 1 koşullu karışımı, aynı fold'un hücreleriyle). Fold durumları: "
      + ", ".join(f"{k} {v}" for k, v in sorted(fs["path_status"].items())) + " (NOT_PRODUCED skorlanmaz, TARGET_UNAVAILABLE değildir):")
    w("")
    w("| Ufuk | Çıktı " + rf.PAIR_HEADER)
    w("|---|---" + rf.PAIR_SEP)
    for h in PATH_HORIZONS:
        for o in ("MAE", "Brier"):
            w(_pair_row([f"D{h}", "koşullu medyan MAE" if o == "MAE" else "koşullu p_up Brier"], ev["path_cells"][(h, o)]))
    w("")
    w("Keşif: koşullu Brier k = 3..9, `ceiling_hazard_v0` koşullu karşısında:")
    w("")
    w("| k " + rf.PAIR_HEADER)
    w("|---" + rf.PAIR_SEP)
    for k in EXPLORATORY_KS:
        w(_pair_row([str(k)], paired_conditional(ledger, runs[PRIMARY_COMPARATOR], f"brier{k}")))
    w("")
    w("### Fold özeti")
    w("")
    w(f"{fs['n_folds']} fold (Faz 1B tavan ledger'ıyla aynı küme ve sıra): " + ", ".join(
        f"{s} {fs['statuses'].get(s, 0)}" for s in ("FIT_OK", "INSUFFICIENT_TRAINING_HISTORY", "NOT_APPLICABLE",
                                                     "SURVIVAL_NOT_AVAILABLE", "MODEL_NOT_FIT_DID_NOT_CONVERGE")) + ". "
      "Seçilen λ (FIT_OK fold sayısı): " + ", ".join(f"{_lambda_text(k)}: {v}" for k, v in
                                                        sorted(fs["lambda"].items(), key=lambda kv: _lam(kv[0]))) + ". "
      f"İlk {fs['early_n']} FIT_OK fold'da INF: {fs['early_inf']}. δ işaretleri (λ < INF, {fs['n_finite']} fold): δ_lock < 0 "
      f"{fs['lock_neg']}/{fs['lock_active']} (d1_lock düşen {fs['lock_dropped']}); δ_turn > 0 / < 0: {fs['turn_pos']} / {fs['turn_neg']}.")
    w("")
    w(f"T7 (λ = INF fold'ları): modelin S_cond'u ile aynı fold'un karşılaştırıcı S_cond'u arasındaki en büyük |Δ| = "
      f"{'—' if fs['t7_max_abs'] is None else repr(fs['t7_max_abs'])} ({fs['t7_n']} fold). T9 ((b)'nin paydası): δ fit'i yapılan "
      f"FIT_OK fold {fs['n_fit_ok']}; paydaya girmeyen INSUFFICIENT_TRAINING_HISTORY {fs['insufficient']}, NOT_APPLICABLE "
      f"{fs['not_applicable']}.")
    w("")
    w("### Nihai fit önizlemesi (dondurulmadı)")
    w("")
    tr, prep = preview["training"], preview["d1_preprocessing"]
    w(f"81 arz (`{tr['set']}`), δ eğitim kümesi {tr['n_delta_ipo']} arz, {tr['n_pp_rows']} satır (d ≥ 2), {tr['n_events']} olay, "
      f"{tr['n_survivals']} sağ kalım; kesim {tr['cutoff_date']}. Ofset `models/ceiling_hazard_v0.json`'dan "
      f"(`{preview['parent']['sha256'][:12]}`), `predict_hazard.linear_predictor` ile. **Seçilen λ = "
      f"{_lambda_text(preview['lambda'])}; δ_lock = {preview['delta']['d1_lock']!r}, δ_turn = {preview['delta']['d1_turnover']!r}** "
      f"(kolonlar {prep['columns']}, düşen {prep['dropped']}); d1_turnover kırpma [{prep['clip']['d1_turnover']['p05']!r}, "
      f"{prep['clip']['d1_turnover']['p95']!r}]; çözücü {preview['solver']['iterations']} yineleme, maks |∇| "
      f"{preview['solver']['grad_max']!r}. `models/`'e yazılmadı; dosya `tests/reference/macos_golden_faz5/"
      f"{manifest['final_fit_preview']['file']}` (dondurma görevi bu önizlemeyle bit-eşitliği sınar).")
    w("")
    w("| λ | iç CV skoru (satır başına log-kayıp) | durum |")
    w("|---|---|---|")
    for e in preview["lambda_score_table"]:
        w(f"| {_lambda_text(e['lambda'])} | {'—' if e['score'] is None else repr(e['score'])} | {e['status']} |")
    w("")
    w("### Faz 5 koşusu ve deney günlüğü")
    w("")
    info = manifest["runs"][MODEL]
    n_log = 0
    if Path(log_path).exists():
        n_log = sum(1 for x in Path(log_path).read_text(encoding="utf-8").splitlines()
                    if x.strip() and json.loads(x).get("model_id") == MODEL and json.loads(x)["kind"] == "backtest")
    w("| Koşu | Plan | Fold | Ledger sha256 (ilk 12) | Günlükteki koşu sayısı |")
    w("|---|---|---|---|---|")
    w(f"| `{MODEL}` | post_d1 | {len(ledger)} | `{info['ledger_sha256'][:12]}` | {n_log} |")
    _frozen_section(w, frozen_entry())


def frozen_entry(index_path: Path = POST_D1_INDEX_PATH) -> Optional[dict[str, Any]]:
    """`models/INDEX_POST_D1.json`'daki bu modelin kaydı; dosya ya da kayıt yoksa None (dondurulmadı)."""
    if not Path(index_path).exists():
        return None
    index = json.loads(Path(index_path).read_text(encoding="utf-8"))
    return next((e for e in index["models"] if e["model_id"] == MODEL), None)


def _frozen_section(w: Callable[[str], None], entry: Optional[Mapping[str, Any]]) -> None:
    if entry is None:
        return
    w("")
    w("### Dondurma")
    w("")
    w("**Donduruldu — §5'in istediği bağımsız yeniden üretimden sonra.** \"Beklentiden çok iyi\" (Brier k = 2) tetiklendiği için "
      "dondurma, ilk uygulamayı görmeyen ayrı bir oturumun (Fable) yalnız şartnameden, `borsai` import etmeden yaptığı sıfırdan "
      f"yeniden üretime bağlıydı. Sonuç ({REPRO['date']}, `{REPRO['doc']}`): 87 fold'un durumu ve seçilen λ birebir, sayısal "
      f"sütunlarda **maks |Δ| = {REPRO['max_abs']}** (eşik 1e-9); nihai fit λ = 30 birebir; §4'ün 28 hücresi ve §5'in 18 etiketi "
      "aynı; sızıntı yok; hüküm **FREEZE_OK**. Ayrıntı ve ham çıktılar "
      f"`{REPRO['dir']}`. Dondurulan model şartnamedeki v0'dır ve yukarıdaki nihai fit önizlemesinin aynısıdır (`created_at`, "
      "`code_version`, `runtime` dışında `==`); dondurma temiz ağaçta yapıldı (`borsai_dirty` false). Yukarıdaki "
      "\"dondurulmadı\" ifadeleri backtest anının kaydıdır.")
    w("")
    w(f"Donmuş dosya `models/{entry['file']}`, sha256 `{entry['sha256']}`; kaydı ayrı dizinde, `models/INDEX_POST_D1.json` "
      f"(aşama {entry['stage']}, proje sahibi kararı 4). Ofset `{entry['parent_model_id']}` (`{entry['parent_sha256'][:12]}`); "
      "`models/INDEX.json` ve listeleme öncesi 19 model dosyası değişmedi. Canlı sicilde satırı canlı POST_D1 akışı kurulunca "
      "başlar; zaman kanıtı dondurma commit'inin push'udur.")
    w("")
    w(K10_FOOTNOTE)

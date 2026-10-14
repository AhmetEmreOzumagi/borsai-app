"""docs/MODELS.md üreticisi.

Girdi: tests/reference/macos_golden/ ve tests/reference/macos_golden_faz1b/
altındaki altın fold ledger'ları (bu makinedeki resmi backtest çıktısı),
models/INDEX.json ve dondurulmuş model dosyaları, experiments/log.jsonl. Yeni
backtest koşmaz; aynı girdilerden her zaman aynı belgeyi üretir. Faz 1B bölümü
borsai/report_faz1b.py'de, Faz 4 bölümü borsai/report_faz4.py'dedir
(tests/reference/macos_golden_faz4/), Faz 5 bölümü borsai/report_faz5.py'dedir
(tests/reference/macos_golden_faz5/; dizin yoksa bölüm üretilmez). Faz 7 bölümü borsai/report_faz7.py'dedir
(tests/reference/macos_golden_faz7/; dizin yoksa üretilmez) ve Faz 4 ile Faz 5 bölümlerinin arasına yazılır
(Faz 5 bölümü belgenin sonunda biter: tests/test_faz5_frozen.py; SPEC_DEVIATIONS J). Faz 7C bölümü borsai/report_faz7c.py'dedir
(tests/reference/macos_golden_faz7c/; dizin yoksa üretilmez) ve Faz 4 ile Faz 7 bölümlerinin arasına yazılır (Faz 7 testleri Faz 7
bölümünü Faz 5 başlığına kadar keser; SPEC_DEVIATIONS K15). Faz 7 ve 7C kartlarının sayaç sütunları (varyant sayacı, (C) aile keşif
sayacı) scores/scores.json'un kartlarından okunur ve yalnız skor dosyası o kimliklerin kartını taşıyınca yazılır (SPEC_DEVIATIONS L):
skorlar yeniden üretilince bu belge de yeniden üretilir. Faz 8 bölümü borsai/report_faz8.py'dedir (docs/faz8/backtest/; dizin yoksa
üretilmez) ve Faz 4 ile Faz 7C bölümlerinin arasına yazılır (SPEC_DEVIATIONS N19).

Kullanım: .venv/bin/python -m borsai.report
"""
from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from . import metrics as mx
from .backtest import GOLDEN_DIR, GOLDEN_FAZ1B_DIR, golden_filename
from .freeze import INDEX_PATH, MODELS_DIR
from .horizons import HORIZONS, physical_return_bounds
from .provenance import ROOT, sha256_file
from .report_faz1b import render_faz1b
from .report_faz4 import render_faz4
from .report_faz5 import golden_available, render_faz5
from .report_faz7 import golden_available as faz7_available, render_faz7
from .report_faz7c import golden_available as faz7c_available, render_faz7c
from .report_faz8 import golden_available as faz8_available, render_faz8
from .specs import FAZ1A_MODEL_IDS

OUT_PATH = ROOT / "docs" / "MODELS.md"
LOG_PATH = ROOT / "experiments" / "log.jsonl"
V15B_LEDGER = ROOT / "tests" / "reference" / "v1_5_benchmark" / "HISTORICAL99_V1_5_outer_fold_prediction_ledger.csv"

RETURN_RULES = ("base_always_ceiling", "base_train_median", "base_train_mean", "base_zero")
PROB_RULES = ("base_always_ceiling", "base_rate", "base_last10_rate")
VERDICT_TEXT = {
    "MODEL_DAHA_IYI": "**V1.5 geçiyor** (aralık 0'ın altında)",
    "KURAL_DAHA_IYI": "**kural daha iyi** (aralık 0'ın üstünde)",
    "AYIRT_EDILEMIYOR": "ayırt edilemiyor (aralık 0'ı içeriyor)",
}


def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _f(v: str) -> Optional[float]:
    return None if v == "" else float(v)


def load_golden() -> dict[str, list[dict[str, str]]]:
    return {m: _read(GOLDEN_DIR / golden_filename(m)) for m in FAZ1A_MODEL_IDS}


def _abs_err(pred: float, row: dict[str, str]) -> float:
    return abs(pred - float(row["realized_return"]))


def paired(v15: list[dict[str, str]], rule: list[dict[str, str]], horizon: str, output: str) -> dict[str, Any]:
    """fark = V1.5 − kural, eşleşik fold'larda (V1.5'in o çıktı için FIT_OK olduğu fold'lar)."""
    rule_by = {r["fold_id"]: r for r in rule}
    diffs, months, mine, theirs = [], [], [], []
    for r in v15:
        if r["horizon"] != horizon:
            continue
        o = rule_by[r["fold_id"]]
        if output == "return":
            if r["ridge_status"] != "FIT_OK":
                continue
            a, b = _abs_err(float(r["ridge_prediction"]), r), _abs_err(float(o["rule_return"]), r)
        else:
            if r["logit_status"] != "FIT_OK":
                continue
            y = int(r["realized_direction"])
            a, b = mx.brier_term(float(r["logit_probability"]), y), mx.brier_term(float(o["rule_p_up"]), y)
        mine.append(a)
        theirs.append(b)
        diffs.append(a - b)
        months.append(r["prediction_date"][:7])
    res = mx.paired_difference(diffs, months)
    res["model_metric"] = sum(mine) / len(mine)
    res["rule_metric"] = sum(theirs) / len(theirs)
    return res


def _own_metrics(model_id: str, rows: list[dict[str, str]], horizon: str) -> dict[str, Any]:
    hl = [r for r in rows if r["horizon"] == horizon]
    out: dict[str, Any] = {}
    if model_id == "v1_5_h99":
        reg = [(float(r["ridge_prediction"]), r) for r in hl if r["ridge_status"] == "FIT_OK"]
        cls = [(float(r["logit_probability"]), int(r["logit_predicted_class"]), r) for r in hl if r["logit_status"] == "FIT_OK"]
    else:
        reg = [(float(r["rule_return"]), r) for r in hl if r["rule_return"] != ""]
        cls = [(float(r["rule_p_up"]), int(r["rule_direction"]), r) for r in hl if r["rule_p_up"] != ""]
    if reg:
        out["return"] = mx.regression_metrics([
            mx.RegressionPoint(r["ticker"], r["prediction_date"], p, float(r["realized_return"]),
                               Decimal(r["ipo_price"]), Decimal(r["official_close"])) for p, r in reg])
    if cls:
        out["p_up"] = mx.classification_metrics([
            mx.ClassificationPoint(r["ticker"], r["prediction_date"], p, d, int(r["realized_direction"])) for p, d, r in cls])
    return out


def port_acceptance(golden_v15: list[dict[str, str]]) -> dict[str, Any]:
    ref = {"|".join(r["fold_id"].split("|")[-2:]): r for r in _read(V15B_LEDGER)}
    out = {"folds": 0, "tickers_sha_equal": 0, "alpha_equal": 0, "C_equal": 0, "max_ridge": 0.0, "max_ridge_fold": "",
           "ridge_differ": 0, "max_logit": 0.0, "max_logit_fold": "", "logit_differ": 0, "status_differ": []}
    for r in golden_v15:
        o = ref[r["fold_id"]]
        out["folds"] += 1
        out["tickers_sha_equal"] += r["training_tickers_sha256"] == o["training_tickers_sha256"]
        out["alpha_equal"] += _f(r["ridge_selected_alpha"]) == _f(o["ridge_selected_alpha"])
        out["C_equal"] += _f(r["logit_selected_C"]) == _f(o["logistic_selected_C"])
        d = abs(float(r["ridge_prediction"]) - float(o["ridge_point_prediction_return"]))
        out["ridge_differ"] += d != 0
        if d > out["max_ridge"]:
            out["max_ridge"], out["max_ridge_fold"] = d, r["fold_id"]
        if r["logit_status"] != o["logistic_status"]:
            out["status_differ"].append(f"{r['fold_id']}: {r['logit_status']} (Windows {o['logistic_status']})")
        elif r["logit_probability"] != "":
            d = abs(float(r["logit_probability"]) - float(o["logistic_probability_above_ipo_raw"]))
            out["logit_differ"] += d != 0
            if d > out["max_logit"]:
                out["max_logit"], out["max_logit_fold"] = d, r["fold_id"]
    return out


def _fmt(x: Optional[float], nd: int = 4) -> str:
    return "—" if x is None else f"{x:.{nd}f}"


def _signed(x: float, nd: int = 4) -> str:
    return f"{x:+.{nd}f}"


def _log_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    if LOG_PATH.exists():
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                e = json.loads(line)
                counts[e["model_id"]] = counts.get(e["model_id"], 0) + 1
    return counts


def render(faz1b_dir: Path = GOLDEN_FAZ1B_DIR) -> str:
    golden = load_golden()
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    models = {e["model_id"]: json.loads((MODELS_DIR / e["file"]).read_text(encoding="utf-8")) for e in index["models"]}
    manifest = json.loads((GOLDEN_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    v15 = golden["v1_5_h99"]
    acc = port_acceptance(v15)
    logs = _log_counts()
    L: list[str] = []
    w = L.append

    w("# Modeller ve backtest sonuçları")
    w("")
    w("Bu sayfa `python -m borsai.report` ile üretilir; elle düzenlenmez. Kaynaklar: `models/INDEX.json` ve model dosyaları, "
      "`tests/reference/macos_golden/` (Faz 1A) ve `tests/reference/macos_golden_faz1b/` (Faz 1B) altındaki fold ledger'ları "
      "(bu makinedeki resmi backtest), `experiments/log.jsonl`.")
    w("")
    w("**Terazi:** buradaki bütün sayılar **backtest**tir (retrospektif walk-forward, H99, ilk işlem 2023-09-22…2026-08-06). "
      "Canlı (prospektif) skor ayrı tutulur ve henüz yoktur (n = 0). İki terazi toplanmaz (CLAUDE.md kural 3).")
    w("")
    w(f"- Veri sürümü: `data/data_version.json` sha256 `{models['v1_5_h99']['training']['data_version_sha256']}`.")
    w(f"- Eğitim kesimi (dondurulmuş modeller): en son hedef seansı {models['v1_5_h99']['training']['cutoff_date']}, n = 99 "
      "(`ceiling_hazard_v0` ve `ceiling_hazard_v0@INF`: f3'ü dolu 97 arz).")
    w(f"- Çalışma ortamı: {manifest['machine']['platform']}; " + ", ".join(f"{k} {v}" for k, v in manifest["runtime"].items()) + ".")
    w("")

    w("## Kayıtlı modeller")
    w("")
    w("| model_id | Ne yapar | Çıktı | Eğitim n | Kesim | Dosya sha256 (ilk 12) | Şartname sha256 (ilk 12) | Günlükteki koşu sayısı |")
    w("|---|---|---|---|---|---|---|---|")
    for e in index["models"]:
        m = models[e["model_id"]]
        outs = []
        h0 = m["horizons"]["D1"] if "D1" in m["horizons"] else m["horizons"]["D10"]   # düşen arz ailesi: D5, D10 (SPEC_DEVIATIONS K22)
        if h0["return"] is not None:
            outs.append("getiri")
        if h0["p_up"] is not None:
            outs.append("P(kapanış > arz)")
        if not outs:
            outs.append("tavan serisi S_k = P(L ≥ k), P(Dk tavan kapanışı)")
        w(f"| `{e['model_id']}` | {m['description']} | {', '.join(outs)} | {e['training_n']} | {e['training_cutoff_date'] or '—'} | "
          f"`{e['sha256'][:12]}` | `{e['spec_sha256'][:12]}` | {logs.get(e['model_id'], 0)} |")
    w("")
    w("\"Günlükteki koşu sayısı\": `experiments/log.jsonl`'daki backtest satırı sayısı, modelin koşulduğu bütün planlar dahil "
      "(bu belge üretildiği anda; plan başına sayılar Faz 1B bölümünün sonunda). Aynı veride bakılan her koşu sayılır "
      "(CLAUDE.md kural 4).")
    w("")

    w("### v1_5_h99 ayrıntısı")
    w("")
    m = models["v1_5_h99"]
    w("- Girdiler f1–f5 (`borsai/features.py`): " + "; ".join(f"{k}: {v}" for k, v in m["feature_definitions"].items()) + ".")
    w("- Ön işleme (`borsai/preprocess.py`, legacy V1.3): f3 fold içi p05/p95 winsor ve medyanla doldurma, f1 log, z-skor (ddof = 0). "
      f"Dondurulmuş parametreler: f3 p05 = {m['preprocessing']['winsor']['f3']['p05']!r}, p95 = {m['preprocessing']['winsor']['f3']['p95']!r}; "
      f"f3 filtre modu `{m['preprocessing']['f3_filter_mode']}` (eşitlik yok).")
    w("- Ridge (getiri) α ızgarası {0.1, 1, 10, 100}; L2-lojistik C ızgarası {0.01, 0.1, 1, 10}; iç LOOCV ile seçim (MAE / ham Brier).")
    w("")
    w("| Ufuk | α (Ridge) | C (Logit) | Logit sınıfları (0 / 1) |")
    w("|---|---|---|---|")
    for h in HORIZONS:
        hh = m["horizons"][h]
        w(f"| {h} | {hh['return']['alpha']:g} | {hh['p_up']['C']:g} | {hh['p_up']['n_class_0']} / {hh['p_up']['n_class_1']} |")
    w("")
    w("D1'de α = 100 ızgaranın üst ucu, D10'da α = 0.1 alt ucu (AUDIT §1.2-e). V1.5 referans olarak aynen korunur; "
      "ızgarası genişletilmiş bir sürüm ayrı model_id olur.")
    w("")
    w("Tahmin kuralları (`borsai/predict.py`): f3 boşsa **RET** (f5 katsayısı yalnız ALBTN ve ENDAE'den öğrenildi, AUDIT §1.2-d); "
      "f1–f4 eğitim aralığı dışındaysa uyarı; f4 = 0 kabul + \"eğitimde örneği yok\" uyarısı; getiri fiziksel sınıra "
      "[0.9^h − 1, 1.1^h − 1] kırpılır ve işaretlenir.")
    w("")

    w("## Backtest yöntemi")
    w("")
    w("- H99 walk-forward, legacy benchmark'la aynı fold planı: eğitim satırı ancak hedef seansı test arzının ilk işlem gününden "
      "kesin önceyse girer; eğitim n'i < 10 olan fold skorlanmaz. Skorlanabilir fold: D1 89, D3 88, D5 87, D10 87 (toplam 351).")
    w("- Her fold'da model yalnız o fold'un eğitim satırlarıyla yeniden fit edilir; basit kurallar aynı fold'larda aynı eğitim "
      "hedeflerinden hesaplanır.")
    w("- Getiri: MAE (R_h uzayı). Olasılık: Brier; olasılık yalnız skorlamada [0.01, 0.99]'a kırpılır. Tahmin ham (kırpılmamış) "
      "haliyle skorlanır.")
    w("- **Eşleşik fark** = V1.5 − kural, aynı fold'larda; negatif = V1.5 daha iyi. Getiri karşılaştırması V1.5 Ridge'in fit "
      "edildiği fold'larda (351/351), olasılık karşılaştırması V1.5 Logit'in fit edildiği fold'larda (D1 80, D3 80, D5 81, D10 81; "
      "tek sınıflı eğitim fold'larında Logit fit edilmez).")
    w(f"- **%95 aralık:** ilk işlem ayına göre blok bootstrap (AUDIT §1.2-c yöntemi): aylar iadeli çekilir, çekilen ayların bütün "
      f"farkları birleştirilip ortalaması alınır; {mx.BOOTSTRAP_REPS} tekrar; her karşılaştırma `random.Random({mx.BOOTSTRAP_SEED})` "
      "ile ayrı başlar. Aralık, sıralı dağılımın 100. ve 3899. elemanıdır. Yöntem AUDIT'in tablosunu 12/12 hücrede aynen üretir "
      "(`tests/test_metrics.py`). Bu test ön kayıtlı değildir; AUDIT sonuçları gördükten sonra seçmiştir.")
    w("- **\"Geçiyor\" yalnız aralık 0'ı dışlıyorsa** denir. Aralık 0'ı içeriyorsa \"ayırt edilemiyor\".")
    w("")

    w("## Eşleşik farklar: V1.5 − basit kural")
    w("")
    for output, rules, label in (("return", RETURN_RULES, "Getiri, MAE"), ("p_up", PROB_RULES, "P(kapanış > arz), Brier")):
        w(f"### {label}")
        w("")
        w("| Ufuk | Kural | n (ay) | V1.5 | Kural | Fark | %95 aralık | V1.5 iyi / kural iyi / eşit | Hüküm |")
        w("|---|---|---|---|---|---|---|---|---|")
        for h in HORIZONS:
            for rule in rules:
                p = paired(v15, golden[rule], h, output)
                lo, hi = p["ci95"]
                w(f"| {h} | `{rule}` | {p['n']} ({p['n_months']}) | {_fmt(p['model_metric'])} | {_fmt(p['rule_metric'])} | "
                  f"{_signed(p['mean'])} | [{_signed(lo)}, {_signed(hi)}] | {p['model_better_n']} / {p['rule_better_n']} / {p['tie_n']} | "
                  f"{VERDICT_TEXT[p['verdict']]} |")
        w("")

    w("## Faz 1A modellerinin kendi skorlanabilir kümesindeki metrikler")
    w("")
    w("Karşılaştırma için değil, bağlam için. Kurallar tüm skorlanabilir fold'larda, V1.5 yalnız fit edildiği fold'larda skorlanır; "
      "bu yüzden olasılık satırlarının n'i farklıdır. Karşılaştırma yukarıdaki eşleşik tablolardadır.")
    w("")
    w("| Model | Ufuk | Getiri n | MAE | Medyan AE | RMSE | Olasılık n | Brier | İsabet | Log kaybı |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for model_id in FAZ1A_MODEL_IDS:
        for h in HORIZONS:
            o = _own_metrics(model_id, golden[model_id], h)
            r, c = o.get("return"), o.get("p_up")
            w(f"| `{model_id}` | {h} | {r['n'] if r else '—'} | {_fmt(r and r['mae'])} | {_fmt(r and r['median_ae'])} | "
              f"{_fmt(r and r['rmse'])} | {c['n'] if c else '—'} | {_fmt(c and c['brier'])} | {_fmt(c and c['accuracy'])} | "
              f"{_fmt(c and c['log_loss'])} |")
    w("")
    w("İsabet tek başına okunmaz: D1'de \"her zaman yukarı\" (ALWAYS_CEILING'in yönü) de 79/89 isabet eder.")
    w("")

    w("## Port kabulü (Windows referansına karşı)")
    w("")
    w("Legacy H99 benchmark'ı Windows'ta (Python 3.12.13) üretildi. Bu makinedeki port (fold düzeyi, `tests/test_acceptance_backtest.py`):")
    w("")
    w(f"- Fold kurulumu: training_tickers_sha256 {acc['tickers_sha_equal']}/{acc['folds']} eşit.")
    w(f"- Seçilen α {acc['alpha_equal']}/{acc['folds']}, seçilen C {acc['C_equal']}/{acc['folds']} eşit.")
    w(f"- Ridge: {acc['ridge_differ']} fold'da son basamaklarda fark, maks |Δ| = {acc['max_ridge']:.3g} ({acc['max_ridge_fold']}); tolerans 1e-12.")
    w(f"- Logit p: {acc['logit_differ']} fold'da fark, maks |Δ| = {acc['max_logit']:.3g} ({acc['max_logit_fold']}); tolerans 1e-7.")
    w("- Adıyla beklenen tek sapma: " + "; ".join(acc["status_differ"]) + ". Bu makinede iç LOOCV'de lbfgs yakınsamıyor; legacy kod "
      "da burada aynı sonucu veriyor (AUDIT §1.2-b). D3 Logit n'i 81 → 80.")
    w("- Aynı makinede port ile legacy kod (legacy/ import edilerek) geliştirme sırasında 351/351 fold'da bit düzeyinde aynı "
      "çıktı; test paketi uç durumları kapsayan 12 fold'u ve ön işlemeyi her koşuda yeniden karşılaştırır "
      "(`tests/test_port_vs_legacy.py`). Bu makinedeki ledger'lar bundan sonraki regresyonun altın referansıdır (bayt eşitliği).")
    w("")

    w("## Notlar")
    w("")
    n_out = sum(1 for r in v15 if r["ridge_outside_physical_bound"] == "TRUE")
    w(f"- V1.5 Ridge backtest tahminlerinin {n_out}/351'i fiziksel sınır [0.9^h − 1, 1.1^h − 1] dışında; backtest bunları "
      "kırpmadan skorlar (legacy ile aynı). `predict` çıktıyı kırpar ve işaretler.")
    n_f3 = sum(1 for r in v15 if r["test_f3_missing"] == "TRUE")
    w(f"- Backtest'te test arzı f3'süz olan {n_f3} fold var (ALBTN ve ENDAE, her ufukta); V1.5 bunları f3 medyanı ve f5 = 1 ile "
      "tahmin etti ve skorlandı. `predict` aynı girdiyi reddeder.")
    w("- Olasılık karşılaştırmasında `base_always_ceiling`'in p_up'ı 1'dir; H99'da her eğitim fold'unda çoğunluk sınıfı 1 olduğundan "
      "legacy V1_BASE_MAJORITY ile aynı kuraldır.")
    w("- Gerçekleşen R_D1 fiyat adımı yüzünden 0.1'i çok az aşabilir (LILAK, BORLS; `docs/DATA.md`).")
    w("- Altın ledger sha256'ları: " + ", ".join(f"`{name}` `{sha[:12]}`" for name, sha in
                                                   ((golden_filename(k), v['ledger_sha256']) for k, v in manifest['models'].items())) + ".")
    w("")
    render_faz1b(w, models, LOG_PATH, faz1b_dir)
    w("")
    render_faz4(w, models, LOG_PATH)
    w("")
    if faz8_available():     # Faz 8 bölümü resmi koşu çıktılarından (commit B); Faz 4 ile Faz 7C arasında (SPEC_DEVIATIONS N19)
        render_faz8(w, LOG_PATH)
        w("")
    if faz7c_available():    # Faz 7C bölümü altın ledger'lardan (commit B); Faz 4 ile Faz 7 arasında (SPEC_DEVIATIONS K15)
        render_faz7c(w, LOG_PATH)
        w("")
    if faz7_available():     # Faz 7 bölümü altın ledger'lardan (commit B); Faz 5'ten önce (SPEC_DEVIATIONS J)
        render_faz7(w, LOG_PATH)
        w("")
    if golden_available():   # Faz 5 bölümü altın ledger'dan üretilir; yoksa (commit A) bölüm yok
        render_faz5(w, LOG_PATH)
        w("")
    return "\n".join(L)


def main() -> int:
    OUT_PATH.write_text(render(), encoding="utf-8")
    print(OUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""docs/MODELS.md'nin Faz 7 bölümü: tavan serisi v1 (`ceiling_hazard_v1_clip`, `_real`, `_pooled`, `_pooled@INF`; SPEC_HAZARD_V1).

Girdi: tests/reference/macos_golden_faz7/ (Faz 7 resmi koşusunun ledger'ları, havuz planının KM ledger'ları, nihai fit
önizlemeleri), Faz 1B tavan ledger'ları (v0, @INF, KM karşılaştırıcıları; yeniden koşulmaz, sha pinli), experiments/log.jsonl ve
şartnamenin §6.2 beklenti tablosu (dosyadan AYNEN okunur). Altın dizin yoksa bölüm üretilmez (commit A: kod ve kurallar, sonuç yok).

Ölçek: koşulsuz tavan serisi (S_k, RPS), H99 walk-forward; backtest terazisi, tasarıma maruz (§10). Kasa (§5.2) ve canlı (§5.3)
teraziler bu bölümde yoktur ve hiçbir tabloda toplanmaz.

Etiket (§5.1, `borsai.backtest.near_era_label`) ve §6.2 konum kuralı (görev kararı T6) bu dosya ve backtest.py yazılırken, sonuçlar
görülmeden (commit A) sabitlendi; `OPERATIONAL_RULES_FAZ7` metni bölümde aynen yazılır.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from . import backtest as bt
from . import report_faz1b as rf
from .provenance import ROOT
from .specs import FAZ7_MODEL_IDS, FAZ7_MODEL_SPECS, PLAN_KEYS, SPEC_DOCUMENTS_FAZ7

GOLDEN_FAZ7_DIR = bt.GOLDEN_FAZ7_DIR
INDEX_PATH = ROOT / "models" / "INDEX.json"
SCORES_PATH = ROOT / "scores" / "scores.json"
SPEC_PATH = ROOT / SPEC_DOCUMENTS_FAZ7["SPEC_HAZARD_V1"]["path"]
CANDIDATES: tuple[str, ...] = FAZ7_MODEL_IDS[:3]
RULE_ROW = FAZ7_MODEL_IDS[3]
SHORT = {"ceiling_hazard_v1_clip": "v1_clip", "ceiling_hazard_v1_real": "v1_real", "ceiling_hazard_v1_pooled": "v1_pooled",
         "ceiling_hazard_v1_pooled@INF": "v1_pooled@INF"}
LADDER_NAME = {"ceiling_hazard_v1_clip": "(a) kırpma", "ceiling_hazard_v1_real": "(b) reel büyüklük",
               "ceiling_hazard_v1_pooled": "(c) havuz + rejim", "ceiling_hazard_v1_pooled@INF": "kural satırı (λ = INF)"}
PRIMARY_COMPARATOR = "ceiling_hazard_v0"
SECONDARY_COMPARATORS: tuple[str, ...] = ("base_km_expanding", "ceiling_hazard_v0@INF")
BRIER_KS: tuple[int, ...] = (1, 3, 5, 10)
LADDER: tuple[tuple[str, str, str], ...] = (
    ("ceiling_hazard_v1_clip", "ceiling_hazard_v0", "kırpmanın payı"),
    ("ceiling_hazard_v1_real", "ceiling_hazard_v1_clip", "deflasyonun payı"),
    ("ceiling_hazard_v1_pooled", "ceiling_hazard_v1_real", "havuz + rejimin payı"),
)
POS_INSIDE, POS_BELOW, POS_ABOVE = "aralık içinde", "altında", "üstünde"
TOO_GOOD = "beklentiden çok iyi"
YEAR_2023_END = bt.NEAR_ERA_START

OPERATIONAL_RULES_FAZ7 = (
    "Birincil hücre (§5.1; her aday için bir tane): aday − `ceiling_hazard_v0`, RPS, ilk işlem ≥ 2024-01-01 olan fold'lar. v0 "
    "değerleri Faz 1B altın ledger'ından (`tests/reference/macos_golden_faz1b/ceiling_hazard_v0_fold_ledger.csv`, sha256 "
    "`976b4dcea981…`; yeniden koşulmaz), fold ticker'ıyla eşleşir; iki tarafın da FIT_OK olduğu fold'lar sayılır.",
    "Etiket (§5.1): %95 aralığın alt ucu > 0 → **bozuyor** (aday yakın dönemde v0'dan kötü); üst ucu ≤ "
    f"{bt.NEAR_ERA_TOLERANCE:+.3f} → **tolerans "
    "içinde**; diğer → **belirsiz** (alt uç = 0 dışlamaz). Aralık SPEC_DEVIATIONS C7: ilk işlem ayı blokları, 4000 tekrar, "
    "`random.Random(20260921)`; RPS ve Brier kırpmasız (`borsai/backtest.py: near_era_label`, `paired_ceiling`).",
    "§6.2 konumu (görev kararı T6): gerçekleşen fark noktası §6.2'nin beklenen aralığı [alt, üst] (kapalı) içindeyse **aralık "
    "içinde**, altındaysa **altında — beklentiden çok iyi**, üstündeyse **üstünde**. Beklentiden çok iyi olsa da olmasa da "
    "sıradaki adım Fable'ın sıfırdan yeniden üretimidir (ledger'lar |Δ| ≤ 1e-9).",
    "Kazanç/kayıp/eşitlik: fold başına kayıp farkının işareti; fark bit-eşit 0 ise eşitlik (MODELS.md kuralı); |fark| ≤ 1e-12 "
    "eşitlik sayısı ayrıca yazılır (bağımsız yeniden fit bit-eşit eşitlik üretmez).",
    "İkincil hücreler (§5.1, ilan edilmiş): aynı fold'larda aday − `base_km_expanding` (v0 planının KM ledger'ı), aday − "
    "`ceiling_hazard_v0@INF`, Brier k ∈ {1, 3, 5, 10} (aday − v0). 2023 fold'ları ve havuz planının KM kuralları keşiftir.",
    "Merdiven (§5.4; yalnız bilgi, hüküm dili yok): aynı 78 fold'da `v1_clip − v0` (kırpmanın payı), `v1_real − v1_clip` "
    "(deflasyonun payı), `v1_pooled − v1_real` (havuz + rejimin payı).",
    "Proje sahibinin sorusu (\"eski arzları eğitime katmak bugünkü tahminleri bozmaz mı?\") `ceiling_hazard_v1_pooled`'ın "
    "birincil hücresinin etiketiyle cevaplanır; `v1_clip` ve `v1_real` hücreleri \"dönüşüm yakın dönemi bozuyor mu\" sorusunun "
    "cevabıdır. H99 tasarıma maruzdur (§10); kanıt değeri prospektif teraziden düşüktür.",
    "Kasa (§5.2, tek seferlik) ve canlı (§5.3) teraziler bu bölümde yoktur: kasa, (C) şartnamesiyle birlikte ve tek seferde açılır "
    "(KARARLAR K1); canlı n dondurmadan sonra listelenen arzlarla başlar. Uygulama birincil seçimi (§5.5, KARARLAR K4) kasa "
    "sonucunu bekler.",
)

# Dondurma notu (BORSAI_FAZ7_FREEZE_20260927; Faz 5 kalıbı): models/INDEX.json dört kimliği listeleyince bölümün sonuna yazılır.
REPRO = {"date": "2026-09-26", "doc": "docs/fable_faz7_audit/AUDIT.md", "dir": "docs/fable_faz7_audit/", "commit": "eda9732",
         "max_abs": "4.3e-11"}
NOT_APP_PRIMARY = ("ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled")        # §5.5 k3: yakın dönem etiketi "bozuyor"
FREEZE_LINES: tuple[str, ...] = (
    "kasa: bekliyor ((C) şartnamesiyle birlikte açılır) — KARARLAR K1, §7.1. Eski kohortun dört modelli ikinci kayıtları "
    "(`--only-missing-models`, §7.1-3) ve model başına kapı (§7.3) kasa açılışından önce, sıradaki görevde.",
    "canlı n: dondurma commit'inden sonra listelenen arzlarla başlar; var olan 7 canlı kayıt v1 için RETRO (2026-08-18 … 09-17 "
    "arzları; kayıtları v1 hücresi taşımaz, model commit'i sonuçlarından sonra; formülle). Zaman kanıtı dondurma commit'inin push'udur.",
    "Uygulama birincili (§5.5): `ceiling_hazard_v1_real` ve `ceiling_hazard_v1_pooled` için §5.5 k3: uygulama birincili olamaz "
    "(yakın dönem etiketi \"bozuyor\"); `ceiling_hazard_v1_clip` için seçim kasa sonucunu bekler; `ceiling_hazard_v0` öne "
    "çıkarılmaya devam eder. Masaüstü uygulaması bu dört kaydı EK3'e kadar yok sayar (SPEC_DEVIATIONS J31).",
    "Canlı kayıt girdileri (SPEC_DEVIATIONS J26): real ve pooled T'nin ayı − 2'nin TÜFE'sini ister; o ay dosyada yoksa kayıt "
    "yazılmaz (aylık ekleme `docs/PROVENANCE.md` §11a; ilk gerçek ekleme Eylül 2026, Kasım arzları için); canlıda rejim r = 0.",
    "Denetim düzeltmesi (aynı model_id, J23): test arzı kırpma bayrağı herhangi bir sütunu sayar (§3.1); fold özetindeki "
    "35 / 36 / 23 bu düzeltmeden sonradır. λ notu (J29): `v1_pooled`'ın λ = 10'u ızgaranın iç noktasıdır.",
)


# §6.2 tablosunun satırları (şartnameden aynen; sıra ve metin denetlenir) -> değerlendirici.
EXPECTED_62: tuple[tuple[str, dict[str, str]], ...] = (
    ("`v1_clip`", {"model": "ceiling_hazard_v1_clip", "comparator": "ceiling_hazard_v0"}),
    ("`v1_real`", {"model": "ceiling_hazard_v1_real", "comparator": "ceiling_hazard_v0"}),
    ("`v1_pooled`", {"model": "ceiling_hazard_v1_pooled", "comparator": "ceiling_hazard_v0"}),
    ("`v1_pooled` − KM (ikincil)", {"model": "ceiling_hazard_v1_pooled", "comparator": "base_km_expanding"}),
)
EXPECTED_62_HEADER = "| Aday | Beklenen | Aralık | Beklenen etiket | Gerekçe |"


# ---------------------------------------------------------------------------
# Veri
# ---------------------------------------------------------------------------

def _read(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def golden_available(faz7_dir: Path = GOLDEN_FAZ7_DIR) -> bool:
    return (Path(faz7_dir) / "MANIFEST.json").exists()


def load_faz7(faz7_dir: Path = GOLDEN_FAZ7_DIR) -> tuple[dict[str, list[dict[str, str]]], dict[str, Any], dict[str, dict[str, Any]]]:
    """(koşu anahtarı -> ledger satırları, MANIFEST, model -> nihai fit önizlemesi)."""
    d = Path(faz7_dir)
    manifest = json.loads((d / "MANIFEST.json").read_text(encoding="utf-8"))
    runs = {k: _read(d / v["file"]) for k, v in manifest["runs"].items()}
    previews = {m: json.loads((d / v["file"]).read_text(encoding="utf-8")) for m, v in manifest["final_fit_previews"].items()}
    return runs, manifest, previews


def comparators() -> dict[str, list[dict[str, str]]]:
    """Faz 1B altın ledger'ları (sha pinli; yeniden koşulmaz)."""
    return {k: bt.read_pinned_ledger(v) for k, v in bt.FAZ7_COMPARATOR_LEDGERS.items()}


# ---------------------------------------------------------------------------
# §6.2 beklenti tablosu ve konum kuralı (T6)
# ---------------------------------------------------------------------------

def _num(text: str) -> float:
    return float(text.replace("**", "").replace("−", "-").strip())


def parse_interval(text: str) -> tuple[float, float]:
    """'[−0.010, +0.005]' -> (−0.010, 0.005)."""
    t = text.replace("**", "").strip().strip("[]").replace("−", "-")
    lo, hi = (float(p.strip()) for p in t.split(","))
    return lo, hi


def expectation_rows(spec_text: Optional[str] = None) -> list[dict[str, Any]]:
    """§6.2 tablosunun 4 satırı, aynen; her satır `EXPECTED_62`'deki değerlendiriciyle eşlenir (sıra ve metin denetlenir)."""
    from .report_faz4 import _split_row

    text = spec_text if spec_text is not None else SPEC_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(EXPECTED_62_HEADER))
    out = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        aday, beklenen, aralik, etiket, gerekce = _split_row(line)
        out.append({"raw": {"aday": aday, "beklenen": beklenen, "aralik": aralik, "etiket": etiket, "gerekce": gerekce}})
    if len(out) != len(EXPECTED_62):
        raise ValueError(f"§6.2 tablosu {len(out)} satır; beklenen {len(EXPECTED_62)}")
    for row, (aday, ev) in zip(out, EXPECTED_62):
        if row["raw"]["aday"] != aday:
            raise ValueError(f"§6.2 satırı beklenenden farklı: {row['raw']}")
        row.update(ev)
        row["point"] = _num(row["raw"]["beklenen"])
        row["lo"], row["hi"] = parse_interval(row["raw"]["aralik"])
    return out


def position(d: float, lo: float, hi: float) -> str:
    """T6: nokta tahminin §6.2 aralığına göre yeri (kapalı aralık)."""
    if d < lo:
        return POS_BELOW
    if d > hi:
        return POS_ABOVE
    return POS_INSIDE


def position_text(pos: str) -> str:
    return f"**{POS_BELOW} — {TOO_GOOD}**" if pos == POS_BELOW else f"**{pos}**"


# ---------------------------------------------------------------------------
# Hücreler
# ---------------------------------------------------------------------------

def evaluate(runs: Mapping[str, Sequence[Mapping[str, Any]]], cmp: Mapping[str, Sequence[Mapping[str, Any]]],
             spec_text: Optional[str] = None) -> dict[str, Any]:
    """Birincil hücreler, ikinciller, merdiven, §6.2 konumları, keşif hücreleri."""
    near = {m: bt.near_era_cell(runs[m], cmp[PRIMARY_COMPARATOR]) for m in FAZ7_MODEL_IDS}
    start = bt.NEAR_ERA_START
    second = {(m, c): bt.paired_ceiling(runs[m], cmp[c], start=start) for m in FAZ7_MODEL_IDS for c in SECONDARY_COMPARATORS}
    brier = {(m, k): bt.paired_ceiling(runs[m], cmp[PRIMARY_COMPARATOR], metric=f"brier{k}", start=start)
             for m in FAZ7_MODEL_IDS for k in BRIER_KS}
    ladder = {(a, b): bt.paired_ceiling(runs[a], runs[b] if b in runs else cmp[b], start=start) for a, b, _ in LADDER}
    early = {m: bt.paired_ceiling(runs[m], cmp[PRIMARY_COMPARATOR], end=YEAR_2023_END) for m in FAZ7_MODEL_IDS}
    all_folds = {m: bt.paired_ceiling(runs[m], cmp[PRIMARY_COMPARATOR]) for m in FAZ7_MODEL_IDS}
    pooled_km = {}
    for m in ("ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF"):
        for key, _ in bt.POOLED_KM_RULES:
            if key in runs:
                pooled_km[(m, key, "near")] = bt.paired_ceiling(runs[m], runs[key], start=start)
                pooled_km[(m, key, "all")] = bt.paired_ceiling(runs[m], runs[key])
                pooled_km[(m, key, "2023")] = bt.paired_ceiling(runs[m], runs[key], end=YEAR_2023_END)
    rows62 = []
    for row in expectation_rows(spec_text):
        cell = near[row["model"]] if row["comparator"] == PRIMARY_COMPARATOR else second[(row["model"], row["comparator"])]
        pos = position(cell["mean"], row["lo"], row["hi"]) if cell else None
        rows62.append({**row, "cell": cell, "position": pos})
    return {"near": near, "second": second, "brier": brier, "ladder": ladder, "early": early, "all": all_folds,
            "pooled_km": pooled_km, "rows62": rows62,
            "too_good": [r["raw"]["aday"] for r in rows62 if r["position"] == POS_BELOW]}


def fold_summary(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    ok = [r for r in rows if r["status"] == "FIT_OK"]
    lam = Counter(r["selected_lambda"] for r in ok)
    near = [r for r in ok if r["first_trading_date"] >= bt.NEAR_ERA_START]
    out = {"n": len(rows), "statuses": dict(Counter(r["status"] for r in rows)), "n_ok": len(ok), "lambda": dict(lam),
           "n_near": len(near), "near_blocks": len({r["first_trading_date"][:7] for r in near}),
           "clipped": sum(1 for r in ok if r.get("test_clipped") == "TRUE"),
           "clipped_f3": sum(1 for r in ok if r.get("test_clipped_features") and "f3" in json.loads(r["test_clipped_features"]))}
    if rows and "delta_r_pre_equal" in rows[0]:
        out["delta_pos"] = sum(1 for r in ok if float(r["delta_r_pre_equal"]) > 0)
        out["delta_neg"] = sum(1 for r in ok if float(r["delta_r_pre_equal"]) < 0)
    if rows and "training_n_filter_excluded" in rows[0]:
        out["filter_excluded_folds"] = sum(1 for r in rows if int(r["training_n_filter_excluded"]) > 0)
        out["n_oot_open"] = sorted({int(r["training_n_oot_open"]) for r in rows})
    return out


# ---------------------------------------------------------------------------
# Biçim
# ---------------------------------------------------------------------------

_f, _s, _cell = rf._f, rf._s, rf._cell
VERDICT_BACKTEST = {"MODEL_DAHA_IYI": "aralık 0'ın altında", "KURAL_DAHA_IYI": "aralık 0'ın üstünde",
                    "AYIRT_EDILEMIYOR": "aralık 0'ı içeriyor"}


def _ci(p: Optional[Mapping[str, Any]]) -> str:
    return "—" if p is None or p.get("ci95") is None else rf._ci(p)


def _wlt(p: Mapping[str, Any]) -> str:
    return f"{p['model_better_n']} / {p['rule_better_n']} / {p['tie_n']} (|fark| ≤ 1e-12: {p['tie_n_1e12']})"


def _pair_cells(p: Optional[Mapping[str, Any]]) -> list[str]:
    if p is None:
        return ["0", "—", "—", "—", "—", "—"]
    return [f"{p['n']} ({p['n_months']})", _f(p["model_metric"]), _f(p["rule_metric"]), _s(p["mean"]), _ci(p), _wlt(p)]


def _lambda_text(x: Any) -> str:
    return "INF" if str(x) == "INF" else f"{float(x):g}"


def _log_count(log_path: Path, model_id: str) -> int:
    if not Path(log_path).exists():
        return 0
    n = 0
    for line in Path(log_path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            n += e.get("kind") == "backtest" and e.get("model_id") == model_id
    return n


def scores_cards(model_ids: Sequence[str], scores_path: Path = SCORES_PATH) -> dict[str, dict[str, Any]]:
    """Kart sayaçları `scores/scores.json`'dan (SPEC_DEVIATIONS L: MODELS.md ve SCORES.md aynı sayıyı yazar; tek kaynak skor
    dosyasının kartı). Dosyada kimliklerin hepsinin kartı yoksa (skorlar bu modellerle üretilmemişken) boş sözlük: sütun yazılmaz."""
    if not Path(scores_path).exists():
        return {}
    cards = {m["model_id"]: m["card"] for m in json.loads(Path(scores_path).read_text(encoding="utf-8"))["models"]}
    return {m: cards[m] for m in model_ids} if all(m in cards for m in model_ids) else {}


def frozen_entries(index_path: Path = INDEX_PATH) -> list[dict[str, Any]]:
    """models/INDEX.json'daki Faz 7 kayıtları (FAZ7_MODEL_IDS sırasıyla); dondurmadan önce boş."""
    index = json.loads(Path(index_path).read_text(encoding="utf-8"))
    return [e for e in index["models"] if e["model_id"] in FAZ7_MODEL_IDS]


def _frozen_section(w: Callable[[str], None], entries: Sequence[Mapping[str, Any]]) -> None:
    if not entries:
        return
    w("")
    w("### Dondurma")
    w("")
    w("**Donduruldu — bağımsız yeniden üretimden sonra.** İlk uygulamayı görmeyen ayrı bir oturum (Fable) şartnameden, `borsai` "
      f"import etmeden sıfırdan yeniden üretti ({REPRO['date']}, `{REPRO['doc']}`, commit {REPRO['commit']}): altı ledger'da durum "
      f"ve seçilen λ birebir, sayılarda **maks |Δ| = {REPRO['max_abs']}** (eşik 1e-9); dört nihai fit önizlemesi ve bu bölümün "
      "52 basılı hücresi aynı; sızıntı yok; hüküm dördü için **FREEZE_OK**. §6.4 gereği dört kimlik birlikte donduruldu "
      "(etiketler dondurma kararına girmez). Donmuş dosyalar yukarıdaki nihai fit önizlemelerinin aynısıdır (`created_at`, "
      "`code_version`, `runtime` dışında `==`); dondurma temiz ağaçta yapıldı (`borsai_dirty` false). Kayıtları `models/INDEX.json`'un "
      f"**sonuna** eklendi, ilk 19 kayıt değişmedi; `models/INDEX_POST_D1.json` değişmedi. Ayrıntı ve ham çıktılar `{REPRO['dir']}`. "
      "Yukarıdaki \"dondurulmadı\" ifadeleri backtest anının kaydıdır.")
    w("")
    w("| model_id | Dosya | sha256 | Dondurma (yerel saat; kanıt push'tur) | Uygulama birincili |")
    w("|---|---|---|---|---|")
    for e in entries:
        m = e["model_id"]
        primary = "§5.5 k3: olamaz" if m in NOT_APP_PRIMARY else ("kural satırı" if m == RULE_ROW else "kasa sonucunu bekler")
        w(f"| `{m}` | `models/{e['file']}` | `{e['sha256']}` | {e['frozen_at'][:10]} | {primary} |")
    w("")
    for line in FREEZE_LINES:
        w(f"- {line}")


def render_faz7(w: Callable[[str], None], log_path: Path, *, faz7_dir: Path = GOLDEN_FAZ7_DIR,
                cmp: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None, index_path: Path = INDEX_PATH,
                scores_path: Path = SCORES_PATH) -> None:
    """Altın dizin yoksa hiçbir şey yazmaz. Dondurma notu yalnız resmi altın dizinle ve INDEX dört kimliği listeleyince. Kartlarda
    varyant sayacı sütunu yalnız `scores/scores.json` dört kimliğin kartını taşıyınca (`scores_cards`)."""
    if not golden_available(faz7_dir):
        return
    runs, manifest, previews = load_faz7(faz7_dir)
    cmp = cmp if cmp is not None else comparators()
    ev = evaluate(runs, cmp)
    doc, dec = SPEC_DOCUMENTS_FAZ7["SPEC_HAZARD_V1"], SPEC_DOCUMENTS_FAZ7["KARARLAR_FAZ7"]
    w("## Faz 7: tavan serisi v1 (Fable şartnamesi, docs/specs_faz7/)")
    w("")
    w("**Terazi ve ölçek:** aşağıdaki her sayı **backtest**tir (retrospektif walk-forward, H99 test arzları) ve **tasarıma "
      "maruzdur** (§10: gün grupları H99'dan, v0'ın H99 sonucu şartname yazılırken biliniyordu); kanıt değeri prospektif "
      "teraziden düşüktür. Ölçek koşulsuzdur (S_k, RPS; Faz 1B tavan tablolarıyla aynı ölçek, ama toplanmaz). Adaylar "
      "**henüz dondurulmadı** (Fable'ın sıfırdan yeniden üretiminden sonra ayrı görev); canlı sicilde satırları yoktur. "
      "Kasa terazisi bekliyor (KARARLAR K1: (C) şartnamesiyle birlikte, tek seferde).")
    w("")
    w(f"Şartname: `{doc['path']}` (sha256 `{doc['sha256'][:12]}…`, commit 6a16c16, push kanıtı 2026-09-25T18:09:45Z, "
      f"uygulamadan önce) ve proje sahibi kararları `{dec['path']}` (sha256 `{dec['sha256'][:12]}…`; çeliştiği yerde bağlayıcı). "
      "Adaylar iç içe bir merdivendir: (a) `ceiling_hazard_v1_clip` — f1, f2, f3 eğitim [p05, p95]'ine kırpılır; (b) "
      "`ceiling_hazard_v1_real` — f1 yerine f1r = ln(büyüklük / (TÜFE_{T−2} / 100)), TÜİK TÜFE 2025=100; (c) "
      "`ceiling_hazard_v1_pooled` — f1r + H99 ve eski kohortun açık kümesi (165 arz) + cezasız rejim terimi r = 1[tahsis rejimi ≠ "
      "EQUAL_DIST_20230330] (canlıda 0). Kural satırı `ceiling_hazard_v1_pooled@INF` (gün + rejim sabitleri). `v1_clip@INF` ve "
      "`v1_real@INF` `ceiling_hazard_v0@INF` ile bit-eşittir, ayrıca kaydedilmez. Uygulama yorumları SPEC_DEVIATIONS J.")
    w("")
    w("Planlar: `v1_clip` ve `v1_real` PLAN_CEILING'de (v0 ile aynı fold'lar ve ticker'lar); `v1_pooled` ve `@INF` "
      "PLAN_CEILING_POOLED'da (test arzları yine H99'un f3'lü 97'si; eğitim training_table_v2'nin seans tarihi < T olan bütün "
      "kişi-dönem satırları; bir eğitim kümesinde f3'ü filtre moduna açıkça zıt olan birim o kümede kullanılmaz — proje sahibi "
      "kararı, SPEC_DEVIATIONS J). Karşılaştırıcılar Faz 1B altın ledger'larından, yeniden koşulmaz.")
    w("")
    w("Etiket ve karşılaştırma kuralları (sonuçlar görülmeden kodda sabitlendi, `borsai/report_faz7.py: OPERATIONAL_RULES_FAZ7` "
      "ve `borsai/backtest.py: near_era_label`, commit A):")
    w("")
    for rule in OPERATIONAL_RULES_FAZ7:
        w(f"- {rule}")
    w("")
    w("### Kartlar")
    w("")
    cards = scores_cards(FAZ7_MODEL_IDS, scores_path) if Path(faz7_dir) == GOLDEN_FAZ7_DIR else {}
    w("| model_id | Basamak | Eğitim | Plan | Fold (FIT_OK) | Yakın dönem etiketi (birincil) | Kasa | Canlı |"
      + (" Varyant (aynı veri sürümü; `scores.json`) |" if cards else ""))
    w("|---|---|---|---|---|---|---|---|" + ("---|" if cards else ""))
    for m in FAZ7_MODEL_IDS:
        spec = FAZ7_MODEL_SPECS[m]
        fs = fold_summary(runs[m])
        label = ev["near"][m]["label"] if ev["near"][m] else "—"
        lab = f"**{label}**" if m in CANDIDATES else f"{label} (kural satırı; aday değil)"
        w(f"| `{m}` | {LADDER_NAME[m]} | {spec['training']['set']} ({spec['training']['n']}) | {PLAN_KEYS[spec['plan_id']]} | "
          f"{fs['n_ok']} | {lab} | kasa: bekliyor | n = 0 (dondurulmadı) |"
          + (f" {cards[m]['n_variants_same_data']} |" if cards else ""))
    w("")
    pooled = ev["near"]["ceiling_hazard_v1_pooled"]
    w(f"**Proje sahibinin sorusunun cevabı (yakın dönem, H99, tasarıma maruz):** `ceiling_hazard_v1_pooled` − v0 = "
      f"{_s(pooled['mean'])} {_ci(pooled)}, n = {pooled['n']} ({pooled['n_months']} ay) → **{pooled['label']}**.")
    w("")
    w("### Yakın dönem birincil hücreleri (aday − `ceiling_hazard_v0`, RPS, ilk işlem ≥ 2024-01-01) ve §6.2 konumu")
    w("")
    w("| Aday | n (ay) | aday | v0 | fark | %95 aralık | aday iyi / v0 iyi / eşit | Etiket | §6.2 beklenen (aynen) | §6.2 aralık (aynen) | "
      "§6.2 beklenen etiket (aynen) | Konum (T6) |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in ev["rows62"]:
        if r["comparator"] != PRIMARY_COMPARATOR:
            continue
        p = r["cell"]
        w(f"| `{r['model']}` **(BİRİNCİL)** | " + " | ".join(_pair_cells(p)) + f" | **{p['label']}** | {r['raw']['beklenen']} | "
          f"{r['raw']['aralik']} | {r['raw']['etiket']} | {position_text(r['position'])} |")
    w("")
    w("§6.2'nin dördüncü satırı (ikincil): " + "; ".join(
        f"`{r['model']}` − `{r['comparator']}` = {_s(r['cell']['mean'])} {_ci(r['cell'])} (n = {r['cell']['n']}); §6.2 "
        f"{r['raw']['beklenen']} {r['raw']['aralik']} → {position_text(r['position'])}"
        for r in ev["rows62"] if r["comparator"] != PRIMARY_COMPARATOR) + ".")
    w("")
    w("Beklentiden çok iyi (T6: nokta §6.2 aralığının altında): " + (
        "**" + ", ".join(ev["too_good"]) + "**. " if ev["too_good"] else "yok. ")
      + "Her iki durumda da sıradaki adım Fable'ın bu şartnameden bağımsız, sıfırdan yeniden üretimidir.")
    w("")
    w("Kural satırı `ceiling_hazard_v1_pooled@INF` − v0 (bilgi; aday değil): " + " ".join(_pair_cells(ev["near"][RULE_ROW])[3:5])
      + f", n = {ev['near'][RULE_ROW]['n']}.")
    w("")
    w("### İkincil hücreler (ilan edilmiş; aynı yakın dönem fold'ları)")
    w("")
    w("| Aday | Karşılaştırılan | Metrik | n (ay) | aday | karş. | fark | %95 aralık | aday iyi / karş. iyi / eşit | aralık |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for m in FAZ7_MODEL_IDS:
        for c in SECONDARY_COMPARATORS:
            p = ev["second"][(m, c)]
            w(f"| `{m}` | `{c}` | RPS | " + " | ".join(_pair_cells(p)) + f" | {VERDICT_BACKTEST.get(p and p['verdict'], '—')} |")
        for k in BRIER_KS:
            p = ev["brier"][(m, k)]
            w(f"| `{m}` | `{PRIMARY_COMPARATOR}` | Brier k = {k} | " + " | ".join(_pair_cells(p))
              + f" | {VERDICT_BACKTEST.get(p and p['verdict'], '—')} |")
    w("")
    w("### Merdiven (§5.4; yalnız pay, aynı yakın dönem fold'ları)")
    w("")
    for a, b, name in LADDER:
        p = ev["ladder"][(a, b)]
        w(f"- {name} (`{SHORT.get(a, a)}` − `{SHORT.get(b, b)}`): fark {_s(p['mean'])} {_ci(p)}, n = {p['n']} ({p['n_months']} ay).")
    w("")
    w("### Keşif (hüküm yok)")
    w("")
    w("| Aday | Karşılaştırılan | Fold kümesi | n (ay) | aday | karş. | fark | %95 aralık | aday iyi / karş. iyi / eşit |")
    w("|---|---|---|---|---|---|---|---|---|")
    for m in FAZ7_MODEL_IDS:
        w(f"| `{m}` | `{PRIMARY_COMPARATOR}` | 2023 fold'ları | " + " | ".join(_pair_cells(ev["early"][m])) + " |")
        w(f"| `{m}` | `{PRIMARY_COMPARATOR}` | bütün eşleşik fold'lar | " + " | ".join(_pair_cells(ev["all"][m])) + " |")
    for (m, key, scope), p in ev["pooled_km"].items():
        label = {"near": "yakın dönem", "all": "bütün fold'lar", "2023": "2023 fold'ları"}[scope]
        w(f"| `{m}` | `{key}` (havuz planı) | {label} | " + " | ".join(_pair_cells(p)) + " |")
    w("")
    w("### Fold özeti")
    w("")
    for m in FAZ7_MODEL_IDS:
        fs = fold_summary(runs[m])
        extra = ""
        if "delta_pos" in fs:
            extra += f" δ (rejim) > 0 / < 0: {fs['delta_pos']} / {fs['delta_neg']}."
        if "filter_excluded_folds" in fs:
            extra += (f" f3 filtre dışlaması olan fold: {fs['filter_excluded_folds']}; eğitimdeki açık küme arzı sayıları "
                      f"{fs['n_oot_open']}.")
        w(f"- `{m}`: {fs['n']} fold, " + ", ".join(f"{k} {v}" for k, v in sorted(fs["statuses"].items()))
          + f"; yakın dönem {fs['n_near']} FIT_OK fold ({fs['near_blocks']} ay); seçilen λ (FIT_OK): "
          + ", ".join(f"{_lambda_text(k)}: {v}" for k, v in sorted(fs["lambda"].items(), key=lambda kv: float("inf") if kv[0] == "INF" else float(kv[0])))
          + f"; test arzı kırpılan fold (herhangi bir özellik, §3.1): {fs['clipped']}"
          + (f" (f3 kırpılan: {fs['clipped_f3']})" if FAZ7_MODEL_SPECS[m]["features"] else "") + "." + extra)
    w("")
    w("### Nihai fit önizlemesi (dondurulmadı)")
    w("")
    w("Dondurmanın kullanacağı fonksiyonla (`borsai/backtest.py: final_fit_v1`) bütün eğitim kümesinde; `models/`'e yazılmadı, "
      "dosyalar `tests/reference/macos_golden_faz7/` altında (dondurma görevi bit-eşitliği `created_at`, `code_version` ve "
      "`runtime` dışında sınar).")
    w("")
    w("| model_id | λ | γ (g1, g2, g3) | β | δ (rejim) | arz / satır / olay | kırpma [p05, p95] (ham) | dosya sha256 (ilk 12) |")
    w("|---|---|---|---|---|---|---|---|")
    for m in FAZ7_MODEL_IDS:
        p = previews[m]
        tr = p["training"]
        beta = ", ".join(f"{k} {v:+.4f}" for k, v in p["beta"].items()) or "—"
        delta = f"{p['regime']['delta']:+.4f}" if "regime" in p else "—"
        wins = "; ".join(f"{k} [{v['p05']:.6g}, {v['p95']:.6g}]" for k, v in (p["preprocessing"] or {}).get("winsor", {}).items()) or "—"
        w(f"| `{m}` | {_lambda_text(p['lambda'])} | " + ", ".join(f"{g:+.4f}" for g in p["gamma"]) + f" | {beta} | {delta} | "
          f"{tr['n_ipo']} / {tr['n_pp_rows']} / {tr['n_events']} | {wins} | `{manifest['final_fit_previews'][m]['sha256'][:12]}` |")
    w("")
    w("### Faz 7 koşuları ve deney günlüğü")
    w("")
    w("| Koşu | Plan | Fold | Ledger sha256 (ilk 12) | Günlükteki koşu sayısı |")
    w("|---|---|---|---|---|")
    for key, info in manifest["runs"].items():
        n_log = _log_count(log_path, key) if key in FAZ7_MODEL_IDS else f"— (`{info['computed_in_run']}` satırında)"
        w(f"| `{key}` | {PLAN_KEYS[info['plan_id']]} | {len(runs[key])} | `{info['ledger_sha256'][:12]}` | {n_log} |")
    w("")
    w(f"v0 karşılaştırıcısının yeniden üretimi (§11-8): Faz 1B ledger'ından 87 fold ortalama RPS "
      f"{bt.v0_mean_rps(cmp[PRIMARY_COMPARATOR]):.4f} (MODELS.md'deki {bt.V0_PUBLISHED_MEAN_RPS}).")
    _frozen_section(w, frozen_entries(index_path) if Path(faz7_dir) == GOLDEN_FAZ7_DIR else [])

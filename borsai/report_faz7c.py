"""docs/MODELS.md'nin Faz 7C bölümü: düşen arz modeli v0 (`fall_d10_v0_h99`, `_pooled`, `_addsale`, kural satırı `_pooled@ZERO`;
SPEC_C_V0, KARARLAR_C).

Girdi: tests/reference/macos_golden_faz7c/ (Faz 7C resmi koşusunun D5/D10 ledger'ları ve nihai fit önizlemeleri), Faz 1A altın ledger'ları
(`base_rate`, `v1_5_h99`; PLAN_V15, 99 arz; yeniden koşulmaz, sha pinli), experiments/log.jsonl ve şartnamenin §6.2 beklenti tablosu
(dosyadan AYNEN okunur). Altın dizin yoksa bölüm üretilmez (commit A: kod ve kurallar, sonuç yok).

Ölçek: p_up = P(kapanış > arz) Brier'i (kırpmasız), D10 birincil, D5 ikincil; H99 walk-forward; backtest terazisi, tasarıma maruz
(§10: özellikler H99 + açık kümenin sonuçları görülerek seçildi). Kasa (§5.2) ve canlı (§5.3) teraziler bu bölümde yoktur ve hiçbir
tabloda toplanmaz. Düşme olasılığı = 1 − p_up; Brier ikisinde aynıdır.

Etiket (§5.1, `borsai.backtest.near_era_label_fall`, δ = `NEAR_ERA_TOLERANCE_FALL`) ve §6.2 konum kuralı (görev kararı T6) bu dosya
ve backtest.py yazılırken, sonuçlar görülmeden (commit A) sabitlendi; `OPERATIONAL_RULES_FAZ7C` metni bölümde aynen yazılır.
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
from .specs import FAZ7C_EXPLORATION, FAZ7C_MODEL_IDS, FAZ7C_MODEL_SPECS, PLAN_KEYS, SPEC_DOCUMENTS_FAZ7C

GOLDEN_FAZ7C_DIR = bt.GOLDEN_FAZ7C_DIR
INDEX_PATH = ROOT / "models" / "INDEX.json"
SPEC_PATH = ROOT / SPEC_DOCUMENTS_FAZ7C["SPEC_C_V0"]["path"]
H99, POOLED, ADDSALE, ZERO_ROW = FAZ7C_MODEL_IDS
CANDIDATES: tuple[str, ...] = FAZ7C_MODEL_IDS[:3]
SHORT = {H99: "h99", POOLED: "pooled", ADDSALE: "addsale", ZERO_ROW: "pooled@ZERO"}
ROLE = {H99: "aday (merdivenin H99 basamağı; KARARLAR_C C2)", POOLED: "aday (havuz)", ADDSALE: "aday (yalnız ek satış)",
        ZERO_ROW: "kural satırı (C = ZERO; aday değil)"}
COMPARATORS: tuple[str, ...] = ("base_rate", "v1_5_h99")
PRIMARY_H = bt.FALL_PRIMARY_HORIZON
# §5.1 ilan edilmiş ikinciller (aynı yakın dönem fold'ları): (aday, karşılaştırılan, ufuk).
DECLARED: tuple[tuple[str, str, str], ...] = tuple(
    (m, c, h) for m in CANDIDATES for c, h in (("base_rate", "D10"), ("base_rate", "D5"), ("v1_5_h99", "D10"))
) + ((POOLED, ZERO_ROW, "D10"),)
# Keşif (hüküm yok): D5'te − v1_5_h99 ve pooled − @ZERO.
EXPLORATORY: tuple[tuple[str, str, str], ...] = tuple((m, "v1_5_h99", "D5") for m in CANDIDATES) + ((POOLED, ZERO_ROW, "D5"),)
# §5.4 merdiven (yalnız pay; D10, aynı yakın dönem fold'ları): (a, b, ad) -> a − b.
LADDER: tuple[tuple[str, str, str], ...] = (
    (H99, ADDSALE, "addsale → h99 (f1r ve ln f3'ün payı; eğitim kümeleri de farklı: H99 94 / havuz 165)"),
    (POOLED, H99, "h99 → pooled (eski verinin payı)"),
    (POOLED, ZERO_ROW, "pooled@ZERO → pooled (özelliklerin payı)"),
)
SCOPE_TEXT = {"2023": "2023 fold'ları", "all": "bütün eşleşik fold'lar"}
POS_INSIDE, POS_BELOW, POS_ABOVE = "aralık içinde", "altında", "üstünde"
TOO_GOOD = "beklentiden çok iyi"
VERDICT_BACKTEST = {"MODEL_DAHA_IYI": "aralık 0'ın altında", "KURAL_DAHA_IYI": "aralık 0'ın üstünde",
                    "AYIRT_EDILEMIYOR": "aralık 0'ı içeriyor"}

OPERATIONAL_RULES_FAZ7C = (
    "Birincil hücre (§5.1; tek): `fall_d10_v0_pooled − fall_d10_v0_h99`, D10 Brier, ilk işlem ≥ 2024-01-01 olan fold'lar. Brier "
    "p_up = P(kapanış > arz) ile ve kırpmasızdır (SPEC_SCORING §7; düşme olasılığı 1 − p_up ile aynı değer); iki ledger fold "
    "ticker'ıyla eşleşir, ikisinde de Logit FIT_OK olan fold'lar sayılır.",
    "Etiket (§5.1): %95 aralığın alt ucu > 0 → **bozuyor** (eski arzları eğitime katmak yakın dönemi bozuyor); üst ucu ≤ "
    f"{bt.NEAR_ERA_TOLERANCE_FALL:+.3f} → **tolerans içinde**; diğer → **belirsiz** (alt uç = 0 dışlamaz). Aralık SPEC_DEVIATIONS "
    "C7: ilk işlem ayı blokları, 4000 tekrar, `random.Random(20260921)`; n < 10 ya da < 6 ay ise aralık yok "
    "(`borsai/backtest.py: near_era_label_fall`, `paired_p_up`).",
    "§6.2 konumu (görev kararı T6): gerçekleşen fark noktası §6.2'nin beklenen aralığı [alt, üst] (kapalı) içindeyse **aralık "
    "içinde**, altındaysa **altında — beklentiden çok iyi**, üstündeyse **üstünde**. Beklentiden çok iyi olsa da olmasa da "
    "sıradaki adım Fable'ın sıfırdan yeniden üretimidir (ledger'lar |Δ| ≤ 1e-9).",
    "Kazanç/kayıp/eşitlik: fold başına Brier farkının işareti; fark bit-eşit 0 ise eşitlik; |fark| ≤ 1e-12 eşitlik sayısı ayrıca "
    "yazılır (bağımsız yeniden fit bit-eşit eşitlik üretmez).",
    "İkincil hücreler (§5.1, ilan edilmiş; aynı fold'lar): her aday − `base_rate` (D10 ve D5), her aday − `v1_5_h99` (D10; V1.5'in "
    "p_up başlığı), `pooled − pooled@ZERO` (D10). `base_rate` ve `v1_5_h99` Faz 1A altın ledger'larındandır (PLAN_V15, 99 arz; "
    "yeniden koşulmaz, sha pinli); `fall_d10_v0_h99@ZERO` ayrıca kaydedilmez (§2). D5'te − `v1_5_h99` ve `pooled − pooled@ZERO`, "
    "2023 fold'ları ve bütün fold'lar keşiftir. Aralık dili backtest'tir (\"aralık 0'ın altında / üstünde / 0'ı içeriyor\"); "
    "SPEC_SCORING §8 hüküm sözcükleri kullanılmaz.",
    "Merdiven (§5.4; yalnız bilgi, hüküm dili yok): aynı yakın dönem D10 fold'larında `h99 − addsale` (f1r ve ln f3'ün payı), "
    "`pooled − h99` (eski verinin payı), `pooled − pooled@ZERO` (özelliklerin payı).",
    "Proje sahibinin sorusu (\"eski arzları eğitime katmak bugünkü tahmini bozar mı?\") birincil hücrenin etiketiyle cevaplanır "
    "(§6.4 (b)). H99 tasarıma maruzdur (§10): özellikler H99 ve açık kümenin sonuçları görülerek seçildi; kanıt değeri kasadan ve "
    "canlıdan düşüktür.",
    "Kasa (§5.2, tek seferlik; `ceiling_hazard_v1` ailesiyle birlikte) ve canlı (§5.3) teraziler bu bölümde yoktur. Uygulama "
    "kartı seçimi (§5.5) kasa sonucunu bekler; üç aday sonuç ne olursa olsun dondurulur ve listede kalır (KARARLAR K4).",
)

# Dondurma notu (BORSAI_FAZ7C_FREEZE_20260928; Faz 7 kalıbı): models/INDEX.json dört kimliği listeleyince bölümün sonuna yazılır.
REPRO = {"date": "2026-09-27", "doc": "docs/fable_faz7c_audit/AUDIT.md", "dir": "docs/fable_faz7c_audit/", "commit": "80670cb"}
FREEZE_ROLE = {H99: "aday; kart seçimi (§5.5) kasa sonucunu bekler", POOLED: "aday; kart seçimi (§5.5) kasa sonucunu bekler",
               ADDSALE: "aday; kart seçimi (§5.5) kasa sonucunu bekler", ZERO_ROW: "kural satırı (aday değil)"}
FREEZE_LINES: tuple[str, ...] = (
    "kasa: bekliyor (tavan serisi v1 ile birlikte tek seferde açılır) — SPEC_C_V0 §7.1. Eski kohortun (C) ek kayıtları "
    "(`--only-missing-models`, §7.1-3), model başına kapı (§7.3) ve `oot_pre_h99_sealed` kasa açılışından önce, sıradaki görevde "
    "(v1 ile birlikte).",
    "canlı n: dondurma commit'inden sonra listelenen arzlarla başlar; var olan 7 canlı kayıt (C) için RETRO (kayıtları (C) hücresi "
    "taşımaz; formülle). Zaman kanıtı dondurma commit'inin push'udur.",
    "Canlı kayıt girdileri (SPEC_DEVIATIONS K16): ek satış alanı V1.5 girdisidir, boşsa üç aday RET (KARARLAR_C C4); h99 ve pooled "
    "f3 ister (f3'süz RET, `registry.F3_MODELS`) ve T'nin ayı − 2'nin TÜFE'sini ister (ön koşul v1 ile ortak: ay dosyada yoksa kayıt "
    "yazılmaz); addsale f3 istemez, `@ZERO` girdi istemez.",
    "Uygulama birincili ve kart (§5.5, §9): seçim kasa sonucunu bekler; masaüstü uygulaması bu dört kaydı EK3'e kadar yok sayar "
    "(SPEC_DEVIATIONS K20). Skorlar bu görevde yeniden üretilmedi (K19); (C) skor hücreleri ve aile keşif sayacı (AUDIT F3) sıradaki "
    "skorlama görevinde.",
    "Denetim düzeltmeleri (aynı model_id): fold özetinin kural satırı (K17); bulgular F1–F9 SPEC_DEVIATIONS K3, K6, K9, K14, K16–K23.",
)


# §6.2 tablosunun satırları (şartnameden aynen; sıra ve metin denetlenir) -> değerlendirici. Son satır her aday için ayrı hücredir.
EXPECTED_62: tuple[tuple[str, dict[str, Any]], ...] = (
    ("`pooled − h99` **(birincil)**", {"models": (POOLED,), "comparator": H99}),
    ("`h99 − base_rate` (ikincil)", {"models": (H99,), "comparator": "base_rate"}),
    ("`pooled − base_rate` (ikincil)", {"models": (POOLED,), "comparator": "base_rate"}),
    ("`addsale − base_rate` (ikincil)", {"models": (ADDSALE,), "comparator": "base_rate"}),
    ("her aday − `v1_5_h99` (ikincil)", {"models": CANDIDATES, "comparator": "v1_5_h99"}),
)
EXPECTED_62_HEADER = "| Hücre | Beklenen | Aralık | Beklenen etiket | Gerekçe |"


# ---------------------------------------------------------------------------
# Veri
# ---------------------------------------------------------------------------

def _read(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def golden_available(faz7c_dir: Path = GOLDEN_FAZ7C_DIR) -> bool:
    return (Path(faz7c_dir) / "MANIFEST.json").exists()


def load_faz7c(faz7c_dir: Path = GOLDEN_FAZ7C_DIR) -> tuple[dict[str, list[dict[str, str]]], dict[str, Any], dict[str, dict[str, Any]]]:
    """(model -> ledger satırları, MANIFEST, model -> nihai fit önizlemesi)."""
    d = Path(faz7c_dir)
    manifest = json.loads((d / "MANIFEST.json").read_text(encoding="utf-8"))
    runs = {k: _read(d / v["file"]) for k, v in manifest["runs"].items()}
    previews = {m: json.loads((d / v["file"]).read_text(encoding="utf-8")) for m, v in manifest["final_fit_previews"].items()}
    return runs, manifest, previews


def comparators() -> dict[str, list[dict[str, str]]]:
    """Faz 1A altın ledger'ları (sha pinli; yeniden koşulmaz)."""
    return {k: bt.read_pinned_ledger(v) for k, v in bt.FAZ7C_COMPARATOR_LEDGERS.items()}


# ---------------------------------------------------------------------------
# §6.2 beklenti tablosu ve konum kuralı (T6)
# ---------------------------------------------------------------------------

def _num(text: str) -> float:
    return float(text.replace("**", "").replace("−", "-").strip())


def parse_interval(text: str) -> tuple[float, float]:
    """'[−0.015, +0.012]' -> (−0.015, 0.012)."""
    t = text.replace("**", "").strip().strip("[]").replace("−", "-")
    lo, hi = (float(p.strip()) for p in t.split(","))
    return lo, hi


def expectation_rows(spec_text: Optional[str] = None) -> list[dict[str, Any]]:
    """§6.2 tablosunun 5 satırı, aynen; her satır `EXPECTED_62`'deki değerlendiriciyle eşlenir (sıra ve metin denetlenir)."""
    from .report_faz4 import _split_row

    text = spec_text if spec_text is not None else SPEC_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(EXPECTED_62_HEADER)]
    if len(starts) != 1:
        raise ValueError(f"§6.2 tablo başlığı {len(starts)} kez bulundu")
    out = []
    for line in lines[starts[0] + 2:]:
        if not line.startswith("|"):
            break
        hucre, beklenen, aralik, etiket, gerekce = _split_row(line)
        out.append({"raw": {"hucre": hucre, "beklenen": beklenen, "aralik": aralik, "etiket": etiket, "gerekce": gerekce}})
    if len(out) != len(EXPECTED_62):
        raise ValueError(f"§6.2 tablosu {len(out)} satır; beklenen {len(EXPECTED_62)}")
    for row, (hucre, ev) in zip(out, EXPECTED_62):
        if row["raw"]["hucre"] != hucre:
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


def position_text(pos: Optional[str]) -> str:
    if pos is None:
        return "—"
    return f"**{POS_BELOW} — {TOO_GOOD}**" if pos == POS_BELOW else f"**{pos}**"


# ---------------------------------------------------------------------------
# Hücreler
# ---------------------------------------------------------------------------

def evaluate(runs: Mapping[str, Sequence[Mapping[str, Any]]], cmp: Mapping[str, Sequence[Mapping[str, Any]]],
             spec_text: Optional[str] = None) -> dict[str, Any]:
    """Birincil hücre ve etiketi, ilan edilmiş ikinciller, merdiven, §6.2 konumları, keşif hücreleri."""
    src = {**cmp, **runs}
    start = bt.NEAR_ERA_START
    near = bt.near_era_cell_fall(runs[POOLED], runs[H99])
    declared = {k: bt.paired_p_up(src[k[0]], src[k[1]], horizon=k[2], start=start) for k in DECLARED}
    exploratory = {k: bt.paired_p_up(src[k[0]], src[k[1]], horizon=k[2], start=start) for k in EXPLORATORY}
    ladder = {(a, b): bt.paired_p_up(src[a], src[b], horizon=PRIMARY_H, start=start) for a, b, _ in LADDER}
    scopes = {"2023": {"end": start}, "all": {}}
    pairs = [(POOLED, H99)] + [(m, "base_rate") for m in CANDIDATES] + [(m, "v1_5_h99") for m in CANDIDATES] + [(POOLED, ZERO_ROW)]
    other = {(a, b, PRIMARY_H, s): bt.paired_p_up(src[a], src[b], horizon=PRIMARY_H, **kw) for a, b in pairs for s, kw in scopes.items()}
    rows62 = []
    for row in expectation_rows(spec_text):
        for m in row["models"]:
            cell = near if (m, row["comparator"]) == (POOLED, H99) else declared[(m, row["comparator"], PRIMARY_H)]
            pos = position(cell["mean"], row["lo"], row["hi"]) if cell else None
            rows62.append({**row, "model": m, "cell": cell, "position": pos})
    return {"near": near, "declared": declared, "exploratory": exploratory, "ladder": ladder, "other": other, "rows62": rows62,
            "too_good": [f"`{SHORT[r['model']]} − {SHORT.get(r['comparator'], r['comparator'])}`" for r in rows62
                         if r["position"] == POS_BELOW]}


def fold_summary(rows: Sequence[Mapping[str, str]], features: Optional[Sequence[str]] = None) -> dict[str, Any]:
    """Ufuk başına fold sayımları. `features` verilir ve `add_sale` içermezse (kural satırı `@ZERO`: sütunu yoktur)
    `add_sale_dropped` None'dır ve bölüm o alanı yazmaz (Fable denetimi F5; SPEC_DEVIATIONS K17)."""
    has_add_sale = features is None or "add_sale" in features
    out: dict[str, Any] = {}
    for h in bt.FALL_HORIZONS:
        hr = [r for r in rows if r["horizon"] == h]
        ok = [r for r in hr if r["logit_status"] == "FIT_OK"]
        near = [r for r in ok if r["prediction_date"] >= bt.NEAR_ERA_START]
        out[h] = {
            "n": len(hr), "statuses": dict(Counter(r["logit_status"] for r in hr)), "n_ok": len(ok),
            "C": dict(Counter(r["logit_selected_C"] for r in ok)), "n_near": len(near),
            "near_blocks": len({r["prediction_date"][:7] for r in near}),
            "events_near": sum(1 for r in near if r["realized_direction"] == "0"),
            "filter_excluded_folds": sum(1 for r in hr if int(r["training_n_filter_excluded"]) > 0),
            "inner_excluded_folds": sum(1 for r in hr if int(r["inner_filter_excluded_n"]) > 0),
            "inner_not_scored": sum(int(r["inner_held_out_not_scored_n"]) for r in hr),
            "clipped": sum(1 for r in ok if r["test_clipped_features"] not in ("", "[]")),
            "add_sale_dropped": (sum(1 for r in ok if "add_sale" not in json.loads(r["logit_columns"])) if has_add_sale
                                 else None),
            "n_oot_open": sorted({int(r["training_n_oot_open"]) for r in hr}),
        }
    return out


def exploration_count(log_path: Path) -> int:
    """Günlükteki `kind: exploration` satırı sayısı (keşif dosyasının sha'sıyla)."""
    if not Path(log_path).exists():
        return 0
    n = 0
    for line in Path(log_path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            n += e.get("kind") == "exploration" and e.get("source_sha256") == FAZ7C_EXPLORATION["sha256"]
    return n


def _log_count(log_path: Path, model_id: str) -> int:
    if not Path(log_path).exists():
        return 0
    n = 0
    for line in Path(log_path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            n += e.get("kind") == "backtest" and e.get("model_id") == model_id
    return n


def frozen_entries(index_path: Path = INDEX_PATH) -> list[dict[str, Any]]:
    """models/INDEX.json'daki Faz 7C kayıtları (FAZ7C_MODEL_IDS sırasıyla); dondurmadan önce boş."""
    index = json.loads(Path(index_path).read_text(encoding="utf-8"))
    return [e for e in index["models"] if e["model_id"] in FAZ7C_MODEL_IDS]


# ---------------------------------------------------------------------------
# Biçim
# ---------------------------------------------------------------------------

_f, _s = rf._f, rf._s


def _ci(p: Optional[Mapping[str, Any]]) -> str:
    return "—" if p is None or p.get("ci95") is None else rf._ci(p)


def _wlt(p: Mapping[str, Any]) -> str:
    return f"{p['model_better_n']} / {p['rule_better_n']} / {p['tie_n']} (|fark| ≤ 1e-12: {p['tie_n_1e12']})"


def _pair_cells(p: Optional[Mapping[str, Any]]) -> list[str]:
    if p is None:
        return ["0", "—", "—", "—", "—", "—"]
    return [f"{p['n']} ({p['n_months']})", _f(p["model_metric"]), _f(p["rule_metric"]), _s(p["mean"]), _ci(p), _wlt(p)]


def _verdict(p: Optional[Mapping[str, Any]]) -> str:
    return VERDICT_BACKTEST.get(p and p.get("verdict"), "—")


def _fmt_C(x: Any) -> str:
    return str(x) if isinstance(x, str) else f"{float(x):g}"


def _C_sort(item: tuple[str, int]) -> float:
    return -1.0 if item[0] == "ZERO" else float(item[0])


def _frozen_section(w: Callable[[str], None], entries: Sequence[Mapping[str, Any]]) -> None:
    if not entries:
        return
    doc = SPEC_DOCUMENTS_FAZ7C["SPEC_C_V0"]
    w("")
    w("### Dondurma")
    w("")
    w("**Donduruldu — bağımsız yeniden üretimden sonra.** İlk uygulamayı görmeyen ayrı bir oturum (Fable) şartnameden, `borsai` "
      f"import etmeden sıfırdan yeniden üretti ({REPRO['date']}, `{REPRO['doc']}`, commit {REPRO['commit']}): dört modelin sekiz "
      "ledger'ı alan alan birebir, p / sabit / katsayı / iç LOOCV tablosu **maks |Δ| = 0**; dört nihai fit önizlemesi ve bu bölümün "
      "hücreleri aynı; sızıntı yok; 16/16 mutasyon kırmızı; hüküm dördü için **FREEZE_OK**. Şartname gereği dört kimlik birlikte "
      "donduruldu (yakın dönem etiketi dondurma kararına girmez). Donmuş dosyalar yukarıdaki nihai fit önizlemelerinin aynısıdır "
      "(`created_at`, `code_version`, `runtime` dışında `==`); dondurma temiz ağaçta yapıldı (`borsai_dirty` false). Kayıtları "
      "`models/INDEX.json`'un **sonuna** eklendi, ilk 23 kayıt değişmedi; `models/INDEX_POST_D1.json` değişmedi. Şartname belgesi "
      f"donmuş JSON'larda `spec.spec_document.sha256` = `{doc['sha256'][:12]}…` (`{doc['path']}`). Ayrıntı ve ham çıktılar "
      f"`{REPRO['dir']}`. Yukarıdaki \"dondurulmadı\" ifadeleri backtest anının kaydıdır.")
    w("")
    w("| model_id | Dosya | sha256 | Dondurma (yerel saat; kanıt push'tur) | Rol |")
    w("|---|---|---|---|---|")
    for e in entries:
        w(f"| `{e['model_id']}` | `models/{e['file']}` | `{e['sha256']}` | {e['frozen_at'][:10]} | {FREEZE_ROLE[e['model_id']]} |")
    w("")
    for line in FREEZE_LINES:
        w(f"- {line}")


def render_faz7c(w: Callable[[str], None], log_path: Path, *, faz7c_dir: Path = GOLDEN_FAZ7C_DIR,
                 cmp: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None, index_path: Path = INDEX_PATH,
                 scores_path: Optional[Path] = None) -> None:
    """Altın dizin yoksa hiçbir şey yazmaz. Dondurma notu yalnız resmi altın dizinle ve INDEX dört kimliği listeleyince. Kartlarda
    varyant sayacı ve aile keşif sayacı sütunları yalnız `scores/scores.json` dört kimliğin kartını taşıyınca (tek kaynak skor
    dosyası; SCORES.md aynı sayıyı yazar; SPEC_DEVIATIONS L)."""
    from .report_faz7 import SCORES_PATH, scores_cards

    if not golden_available(faz7c_dir):
        return
    runs, manifest, previews = load_faz7c(faz7c_dir)
    cmp = cmp if cmp is not None else comparators()
    ev = evaluate(runs, cmp)
    doc, dec = SPEC_DOCUMENTS_FAZ7C["SPEC_C_V0"], SPEC_DOCUMENTS_FAZ7C["KARARLAR_C"]
    w("## Faz 7C: düşen arz modeli v0 (Fable şartnamesi, docs/specs_faz7_c/)")
    w("")
    w("**Terazi ve ölçek:** aşağıdaki her sayı **backtest**tir (retrospektif walk-forward, H99 test arzları) ve **tasarıma "
      "maruzdur** (§10: özellikler H99'un ve eski kohortun açık kümesinin sonuçları görülerek, 2 054 varyant denenerek seçildi); kanıt "
      "değeri kasadan ve canlıdan düşüktür. Ölçek: p_up = P(D_h kapanışı > arz fiyatı) Brier'i (kırpmasız), D10 birincil, D5 "
      "ikincil; \"düşme olasılığı\" = 1 − p_up (Brier aynı). Adaylar **henüz dondurulmadı** (Fable'ın sıfırdan yeniden üretiminden "
      "sonra ayrı görev); canlı sicilde satırları yoktur. Kasa terazisi bekliyor (`ceiling_hazard_v1` ailesiyle birlikte, tek "
      "seferde).")
    w("")
    w(f"Şartname: `{doc['path']}` (sha256 `{doc['sha256'][:12]}…`, commit 4fe4e51, uygulamadan önce push kanıtlı) ve bağlayıcı "
      f"kararlar `{dec['path']}` (sha256 `{dec['sha256'][:12]}…`; çeliştiği yerde geçerli). Hedef y4 = 1 − Y_D10 (D10 kapanışı ≤ arz "
      "fiyatı; KARARLAR_C C1), ikincil y3 = 1 − Y_D5 (C3). Üç aday, her biri D5 ve D10 için ayrı L2-lojistik başlık (V1.6 C ızgarası, "
      "iç arz-bırak Brier; getiri başlığı yok): `fall_d10_v0_h99` — f1r (TÜFE ile reel büyüklük, `ceiling_hazard_v1_real` ile tek "
      "tanım), ln f3 (talep katı), ek satış bayrağı; H99'un 94 arzı (KARARLAR_C C2: bütçe 6.5 olay/parametre, kabul); "
      "`fall_d10_v0_pooled` — aynı özellikler, H99 + açık küme 161 arz, rejim terimi yok; `fall_d10_v0_addsale` — yalnız ek satış "
      "bayrağı, havuzun ek satış alanı dolu 165 arzı, f3 istemez. Kural satırı `fall_d10_v0_pooled@ZERO` (havuz oranı). Ek satış "
      "alanı boşsa RET (C4). Uygulama yorumları SPEC_DEVIATIONS K.")
    w("")
    w("Planlar: PLAN_V15 kuralı (ufuk başına eğitim arzı ancak D_h seansı test arzının T'sinden kesin önce; eğitim n ≥ 10). Test "
      "arzları H99'dandır: `h99` ve `pooled` aynı 94 arz, `addsale` H99'un ek satış alanı dolu 95 arzı; havuz planlarında açık "
      "küme arzları eğitimde (son seansları 2023-10-04'ten önce). İmputasyonsuz tarifte f3'ü eğitim kümesinin filtre moduna açıkça "
      "zıt olan arz o kümede kullanılmaz (SPEC_DEVIATIONS J10 kuralı aynen, K); `@ZERO` modelinin planını kullanır. Karşılaştırıcılar "
      "Faz 1A altın ledger'larından, yeniden koşulmaz.")
    w("")
    w("Etiket ve karşılaştırma kuralları (sonuçlar görülmeden kodda sabitlendi, `borsai/report_faz7c.py: OPERATIONAL_RULES_FAZ7C` "
      "ve `borsai/backtest.py: near_era_label_fall`, commit A):")
    w("")
    for rule in OPERATIONAL_RULES_FAZ7C:
        w(f"- {rule}")
    w("")
    w("### Kartlar")
    w("")
    cards = scores_cards(FAZ7C_MODEL_IDS, scores_path or SCORES_PATH) if Path(faz7c_dir) == GOLDEN_FAZ7C_DIR else {}
    w("| model_id | Rol | Özellikler | Eğitim | Plan | Fold (Logit FIT_OK: D10 / D5) | Yakın dönem etiketi (birincil) | Kasa | Canlı |"
      + (" Varyant (aynı veri sürümü; `scores.json`) | Aile keşif sayacı (`scores.json`) |" if cards else ""))
    w("|---|---|---|---|---|---|---|---|---|" + ("---|---|" if cards else ""))
    near = ev["near"]
    for m in FAZ7C_MODEL_IDS:
        spec = FAZ7C_MODEL_SPECS[m]
        fs = fold_summary(runs[m])
        tr = spec["training"]
        feats = ", ".join(spec["features"]) or "— (sabit)"
        label = f"**{near['label']}** (`pooled − h99`)" if m in (H99, POOLED) and near else "—"
        w(f"| `{m}` | {ROLE[m]} | {feats} | {tr['set']} ({tr['n']}; D10 olay {tr['events_D10']}, D5 {tr['events_D5']}) | "
          f"{PLAN_KEYS[spec['plan_id']]} | {fs['D10']['n_ok']} / {fs['D5']['n_ok']} | {label} | kasa: bekliyor | n = 0 (dondurulmadı) |"
          + (f" {cards[m]['n_variants_same_data']} | {cards[m]['n_exploration_family']} |" if cards else ""))
    w("")
    if cards:
        w(f"Kart sayaçları `scores/scores.json`'dan (SCORES.md §5.2 ile aynı sayı): varyant sayacı aynı veri sürümündeki farklı backtest "
          f"varyantları + keşif satırlarıdır; aile keşif sayacı günlükteki `kind: exploration` satırlarıdır (kaynak "
          f"`{FAZ7C_EXPLORATION['path']}`, Fable Faz 7C denetimi F3); yan yana gösterilir, toplanmaz.")
        w("")
    w(f"**Proje sahibinin sorusunun cevabı (yakın dönem, H99, tasarıma maruz):** `fall_d10_v0_pooled − fall_d10_v0_h99` (D10 Brier) = "
      f"{_s(near['mean'])} {_ci(near)}, n = {near['n']} ({near['n_months']} ay) → **{near['label']}**.")
    w("")
    w("### Yakın dönem birincil hücresi (`pooled − h99`, D10 Brier, ilk işlem ≥ 2024-01-01) ve §6.2 konumu")
    w("")
    w("| Hücre | n (ay) | pooled | h99 | fark | %95 aralık | pooled iyi / h99 iyi / eşit | Etiket | §6.2 beklenen (aynen) | "
      "§6.2 aralık (aynen) | §6.2 beklenen etiket (aynen) | Konum (T6) |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|")
    r0 = ev["rows62"][0]
    w(f"| `pooled − h99` **(BİRİNCİL)** | " + " | ".join(_pair_cells(near)) + f" | **{near['label']}** | {r0['raw']['beklenen']} | "
      f"{r0['raw']['aralik']} | {r0['raw']['etiket']} | {position_text(r0['position'])} |")
    w("")
    w("### İkincil hücreler (ilan edilmiş; aynı yakın dönem fold'ları) ve §6.2 konumu")
    w("")
    w("| Aday | Karşılaştırılan | Ufuk | n (ay) | aday | karş. | fark | %95 aralık | aday iyi / karş. iyi / eşit | aralık | §6.2 satırı | "
      "§6.2 beklenen / aralık (aynen) | Konum (T6) |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    by62 = {(r["model"], r["comparator"]): r for r in ev["rows62"][1:]}
    for (m, c, h), p in ev["declared"].items():
        r = by62.get((m, c)) if h == PRIMARY_H else None
        extra = (f"{r['raw']['hucre']} | {r['raw']['beklenen']} {r['raw']['aralik']} | {position_text(r['position'])}" if r
                 else "— | — | —")
        w(f"| `{m}` | `{c}` | {h} | " + " | ".join(_pair_cells(p)) + f" | {_verdict(p)} | {extra} |")
    w("")
    w("Beklentiden çok iyi (T6: nokta §6.2 aralığının altında): " + (
        "**" + ", ".join(ev["too_good"]) + "**. " if ev["too_good"] else "yok. ")
      + "Her iki durumda da sıradaki adım Fable'ın bu şartnameden bağımsız, sıfırdan yeniden üretimidir.")
    w("")
    w("### Merdiven (§5.4; yalnız pay, D10, aynı yakın dönem fold'ları)")
    w("")
    for a, b, name in LADDER:
        p = ev["ladder"][(a, b)]
        w(f"- {name}: `{SHORT[a]} − {SHORT[b]}` = {_s(p['mean'])} {_ci(p)}, n = {p['n']} ({p['n_months']} ay).")
    w("")
    w("### Keşif (hüküm yok)")
    w("")
    w("| Aday | Karşılaştırılan | Ufuk | Fold kümesi | n (ay) | aday | karş. | fark | %95 aralık | aday iyi / karş. iyi / eşit |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for (m, c, h), p in ev["exploratory"].items():
        w(f"| `{m}` | `{c}` | {h} | yakın dönem | " + " | ".join(_pair_cells(p)) + " |")
    for (a, b, h, s), p in ev["other"].items():
        w(f"| `{a}` | `{b}` | {h} | {SCOPE_TEXT[s]} | " + " | ".join(_pair_cells(p)) + " |")
    w("")
    w("### Fold özeti")
    w("")
    for m in FAZ7C_MODEL_IDS:
        fs = fold_summary(runs[m], FAZ7C_MODEL_SPECS[m]["features"])
        parts = []
        for h in ("D10", "D5"):
            s = fs[h]
            parts.append(
                f"{h}: {s['n']} fold, " + ", ".join(f"{k} {v}" for k, v in sorted(s["statuses"].items()))
                + f"; yakın dönem {s['n_near']} FIT_OK fold ({s['near_blocks']} ay, olay {s['events_near']}); seçilen C (FIT_OK): "
                + ", ".join(f"{_fmt_C(k)}: {v}" for k, v in sorted(s["C"].items(), key=_C_sort))
                + f"; f3 filtre dışlaması olan fold {s['filter_excluded_folds']} (iç CV'de dışlama olan fold {s['inner_excluded_folds']}, "
                f"skorlanmayan iç tutulan {s['inner_not_scored']}); test arzı kırpılan fold {s['clipped']}; "
                + ("" if s["add_sale_dropped"] is None else f"ek satış sütunu sıfır varyansla düşen fold {s['add_sale_dropped']}; ")
                + f"eğitimdeki açık küme arzı {s['n_oot_open'][0]}…{s['n_oot_open'][-1]}")
        w(f"- `{m}` — " + ". ".join(parts) + ".")
    w("")
    w("### Nihai fit önizlemesi (dondurulmadı)")
    w("")
    w("Dondurmanın kullanacağı fonksiyonla (`borsai/backtest.py: final_fit_fall`) bütün eğitim kümesinde; `models/`'e yazılmadı, "
      "dosyalar `tests/reference/macos_golden_faz7c/` altında (dondurma görevi bit-eşitliği `created_at`, `code_version` ve `runtime` "
      "dışında sınar). Katsayılar z-skorlu sütunlarda, p_up (P(kapanış > arz)) başlığınındır: pozitif katsayı düşme olasılığını azaltır.")
    w("")
    w("| model_id | Ufuk | C | sabit | katsayılar | arz / olay | kırpma [p05, p95] (ham) | f3 filtre modu | dosya sha256 (ilk 12) |")
    w("|---|---|---|---|---|---|---|---|---|")
    for m in FAZ7C_MODEL_IDS:
        p = previews[m]
        tr = p["training"]
        prep = p["preprocessing"] or {}
        wins = "; ".join(f"{k} [{v['p05']:.6g}, {v['p95']:.6g}]" for k, v in prep.get("winsor", {}).items()) or "—"
        for h in bt.FALL_HORIZONS:
            head = p["horizons"][h]["p_up"]
            if head["kind"] == "constant":
                C, icpt, coef = "ZERO (kural)", f"p_up = {head['value']:.6f}", "—"
            else:
                C, icpt = _fmt_C(head["C"]), f"{head['intercept']:+.4f}"
                coef = ", ".join(f"{c} {v:+.4f}" for c, v in zip(head["columns"], head["coef"])) or "—"
            w(f"| `{m}` | {h} | {C} | {icpt} | {coef} | {tr['n']} / {tr[f'events_{h}']} | {wins} | "
              f"{prep.get('f3_filter_mode') or '—'} | `{manifest['final_fit_previews'][m]['sha256'][:12]}` |")
    w("")
    w("### Faz 7C koşuları ve deney günlüğü")
    w("")
    w("| Koşu | Plan | Fold (D10 + D5) | Ledger sha256 (ilk 12) | Günlükteki koşu sayısı |")
    w("|---|---|---|---|---|")
    for key, info in manifest["runs"].items():
        w(f"| `{key}` | {PLAN_KEYS[info['plan_id']]} | {len(runs[key])} | `{info['ledger_sha256'][:12]}` | {_log_count(log_path, key)} |")
    w("")
    n_expl = exploration_count(log_path)
    w(f"Keşif varyantları (§10; KARARLAR_C \"Çokluk\"): `{FAZ7C_EXPLORATION['path']}` (sha256 `{FAZ7C_EXPLORATION['sha256'][:12]}…`) "
      f"günlükte {n_expl} `kind: exploration` satırı; veri sürümü v2 (`data/data_version_v2.json`), kart varyant sayacı bunları o "
      "sürümde sayar (SPEC_DEVIATIONS K). Model değildirler; dondurulmazlar.")
    w("")
    n15, b15 = bt.v15_d10_brier(cmp["v1_5_h99"])
    w(f"V1.5 karşılaştırıcısının yeniden üretimi (§11-7): Faz 1A ledger'ından D10 Brier {b15:.4f} ({n15} fold; MODELS.md'deki "
      f"{bt.V15_PUBLISHED_D10_BRIER}).")
    _frozen_section(w, frozen_entries(index_path) if Path(faz7c_dir) == GOLDEN_FAZ7C_DIR else [])
